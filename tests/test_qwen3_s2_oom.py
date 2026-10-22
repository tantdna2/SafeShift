"""CPU synthetic forensics, recovery membership and unchanged backend lifecycle."""
from contextlib import nullcontext
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import weakref

from safeshift.diagnostics import qwen3_s2_oom as oom
from safeshift.diagnostics.hnlo_train import backend, capture, cohort, contract, engine
from safeshift.ls1.runtime import summarize_vector
from safeshift.pa3.native.journal import Journal
from safeshift.runners.qwen3_vl import Qwen3VLRunner
from tests.test_hnlo_train import FakeBackend, CONFIG, KWARGS
from tests.test_hnlo_capture import TOK, CANDIDATES, output
from safeshift.ls1.tokenizer import probe

ROOT = Path(__file__).resolve().parents[1]


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def proof(data):
    return {"sha256": oom.digest(data), "size_bytes": len(data)}


def journal_files(parent, values):
    files = {parent + "/" + name + ".json": encoded(value) for name, value in values.items()}
    files[parent + "/seal.json"] = encoded({name: proof(files[parent + "/" + name + ".json"])
                                                   for name in values})
    files.update({p[:-5] + ".sha256.json": encoded(proof(b)) for p, b in list(files.items())})
    return files


def fixture_files():
    files = journal_files("raw/index", {"manifest": {"samples": []}})
    files["binding.json"] = encoded({"synthetic": True})
    files.update(journal_files("custody", {"files": {p: proof(b) for p, b in files.items()}}))
    return files


def make_archive(path, files, *, extras=(), transform_manifest=lambda m: m):
    manifest = transform_manifest({"schema": "hnlo-evidence-inventory-v1", "files": [
        {"path": p, **proof(b)} for p, b in files.items()]})
    data = encoded(manifest)
    with tarfile.open(path, "w:gz") as t:
        for name, blob in [("evidence/" + p, b) for p, b in files.items()] + [("manifest.json", data)] + list(extras):
            entry = tarfile.TarInfo(name)
            entry.size = len(blob)
            t.addfile(entry, io.BytesIO(blob))
    return data


def planned_rows():
    planned = [{"sample_id": f"synthetic-{i}", "image_sha256": f"{i:064x}", "image_locator": f"unused/{i}.jpg"}
               for i in range(941)]
    rows = [{"ordinal": i, "sample_id": p["sample_id"], "attempted": i <= 717,
             "native_call_start_recorded": i <= 717, "persisted": i < 717,
             "status": "SUCCESS" if i < 717 else "TECHNICAL_ERROR" if i == 717 else "NOT_ATTEMPTED"}
            for i, p in enumerate(planned)]
    return planned, rows


class ForensicTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_archive_integrity_is_read_only_and_seals_are_verified(self):
        path = self.root / "input.tar.gz"
        manifest = make_archive(path, fixture_files())
        before = path.read_bytes()
        _, result = oom.verify_archive(path, manifest)
        self.assertEqual(result["journal_seals"], 2)
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_duplicate_extra_traversal_members_and_manifest_duplicates_rejected(self):
        for name in ("evidence/binding.json", "evidence/extra.json", "../escape.json", "C:/escape"):
            with self.subTest(name=name):
                path = self.root / "bad.tar.gz"
                manifest = make_archive(path, fixture_files(), extras=[(name, b"{}")])
                with self.assertRaises(ValueError):
                    oom.verify_archive(path, manifest)
        path = self.root / "duplicate.tar.gz"
        def duplicate(m):
            m["files"].append(m["files"][0])
            return m
        manifest = make_archive(path, fixture_files(), transform_manifest=duplicate)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_INVENTORY"):
            oom.verify_archive(path, manifest)

    def test_bad_journal_seal_sidecar_and_custody_rejected_even_with_new_outer_hashes(self):
        for name in ("raw/index/seal.json", "raw/index/manifest.sha256.json", "custody/files.json"):
            with self.subTest(name=name):
                files = fixture_files()
                if name == "custody/files.json":
                    files.update(journal_files("custody", {"files": {}}))
                else:
                    files[name] = b"{}"
                    if not name.endswith(".sha256.json"):
                        files[name[:-5] + ".sha256.json"] = encoded(proof(files[name]))
                path = self.root / "tampered.tar.gz"
                manifest = make_archive(path, files)
                with self.assertRaisesRegex(ValueError, "SEAL_MISMATCH|SIDECAR_MISMATCH|CUSTODY_MISMATCH"):
                    oom.verify_archive(path, manifest)

    def test_member_size_bound_links_missing_and_wrong_inner_manifest(self):
        files = fixture_files()
        path = self.root / "bad.tar.gz"
        manifest = make_archive(path, files)
        with patch.object(oom, "MAX_MEMBER", 2), self.assertRaisesRegex(ValueError, "INVENTORY"):
            oom.verify_archive(path, manifest)
        with tarfile.open(path, "w:gz") as t:
            entry = tarfile.TarInfo("manifest.json")
            entry.type = tarfile.SYMTYPE
            entry.linkname = "outside"
            t.addfile(entry)
        with self.assertRaisesRegex(ValueError, "REGULAR_MEMBERS"):
            oom.verify_archive(path, manifest)
        with tarfile.open(path, "w:gz") as t:
            entry = tarfile.TarInfo("manifest.json")
            entry.size = len(manifest)
            t.addfile(entry, io.BytesIO(manifest))
        with self.assertRaisesRegex(ValueError, "MISSING_ARCHIVE"):
            oom.verify_archive(path, manifest)
        make_archive(path, files)
        with self.assertRaisesRegex(ValueError, "INNER_OUTER"):
            oom.verify_archive(path, manifest + b" ")

    def test_duplicate_json_nonfinite_and_unsafe_manifest_paths(self):
        for value in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                oom.load(value)
        for name in ("a//b", "../a", "/a", "a\\b", "a/./b", "C:/a"):
            with self.assertRaises(ValueError):
                oom.relative(name)

    def test_exact_224_mapping_new_identity_and_label_free_worker_projection(self):
        planned, rows = planned_rows()
        plan = oom.recovery_plan(rows, planned, {"merge_commit": oom.RELEASE}, oom.RERUN_SHA)
        self.assertEqual([p["original_ordinal"] for p in plan["mapping"]], list(range(717, 941)))
        self.assertEqual([p["recovery_ordinal"] for p in plan["mapping"]], list(range(224)))
        self.assertEqual([p["image_sha256"] for p in plan["worker_projection"]], [p["image_sha256"] for p in planned[717:]])
        cohort.validate_opaque(plan["worker_projection"], 224)
        self.assertNotIn("sample_id", json.dumps(plan["worker_projection"]))
        self.assertNotIn("s2-a1", plan["run_id"])
        self.assertNotEqual(plan["attempt_id"], contract.unit("qwen3", 2)["attempt_id"])
        self.assertIsNone(plan["grant"])
        self.assertFalse(plan["execution_allowed"])
        self.assertFalse(plan["baseline_pooling_allowed"])
        self.assertEqual(plan["status"], "PROPOSED_NON_EXECUTABLE")
        self.assertEqual(plan["source_lock"]["mapping_sha256"], oom.canonical_digest(plan["mapping"]))
        self.assertEqual(plan["source_lock"]["worker_projection_sha256"], oom.canonical_digest(plan["worker_projection"]))
        self.assertFalse(plan["source_lock"]["execution_lock_complete"])
        self.assertIsNone(plan["source_lock"]["implementation_commit"])
        self.assertFalse(plan["audit_contract"]["implementation_reviewed"])
        self.assertIsNone(plan["authority_contract"]["grant"])

    def test_changed_status_order_exposure_and_missing_rows_fail_closed(self):
        for change in (lambda r: r.reverse(), lambda r: r.pop(), lambda r: r[717].update(status="SUCCESS"),
                       lambda r: r[718].update(attempted=True), lambda r: r[0].update(ordinal=False),
                       lambda r: r[0].update(sample_id="other")):
            planned, rows = planned_rows()
            change(rows)
            with self.assertRaises(ValueError):
                oom.recovery_plan(rows, planned, {"merge_commit": oom.RELEASE}, oom.RERUN_SHA)
        planned, rows = planned_rows()
        planned[717]["image_sha256"] = "bad"
        with self.assertRaisesRegex(ValueError, "IMAGE_HASH_REQUIRED"):
            oom.recovery_plan(rows, planned, {"merge_commit": oom.RELEASE}, oom.RERUN_SHA)

    def test_release_and_duplicate_cohort_rejected(self):
        planned, rows = planned_rows()
        with self.assertRaisesRegex(ValueError, "WRONG_RELEASE"):
            oom.recovery_plan(rows, planned, {"merge_commit": "a" * 40}, oom.RERUN_SHA)
        planned[1] = planned[0]
        with self.assertRaisesRegex(ValueError, "DUPLICATE_SAMPLE"):
            oom.recovery_plan(rows, planned, {"merge_commit": oom.RELEASE}, oom.RERUN_SHA)

    def test_receipts_result_source_and_manifest_bindings_without_ml_or_gt(self):
        planned, rows = planned_rows()
        path = self.root / (oom.STEM + ".tar.gz")
        path.write_bytes(b"SYNTHETIC_ARCHIVE_BYTES")
        sha = oom.file_digest(path)
        unit = contract.unit("qwen3", 2)
        result = {"unit": unit, "sample_journal": rows, "resources": {"coverage": "PARTIAL_SAMPLED"}}
        call = {"input_shapes": {"input_ids": [1, 3]}}
        selected = {"binding.json": {"samples": planned, "source": {"merge_commit": oom.RELEASE}, "unit": unit},
                    "result.json": deepcopy(result), "raw/index/manifest.json": {"samples": cohort.opaque_rows(planned), "expected_count": 941},
                    "raw/index/failure.json": {"ordinal": 717, "type": "OutOfMemoryError", "interrupted": False, "retry": False},
                    "raw/index/native-counts.json": {"load_calls": 1, "generate_ordinals": list(range(718)), "memory": {}},
                    "raw/sample-000717/call.json": call}
        for i in range(717):
            selected[f"raw/sample-{i:06d}/call.json"] = call
            selected[f"raw/sample-{i:06d}/native.json"] = {"raw_steps": 10}
        manifest = encoded({"files": []})
        export = {"status": "EXPORTED", "archive": path.name, "archive_sha256": sha,
                  "archive_bytes": path.stat().st_size, "manifest_sha256": oom.digest(manifest), "unit": unit}
        result["export"] = deepcopy(export)
        blob = encoded(result)
        export["result_sha256"] = oom.digest(blob)
        export_blob = encoded(export)
        values = {"_manifest": manifest, "_result": blob, "_export": export_blob,
                  "_export_sha256": encoded({"sha256": oom.digest(export_blob)}),
                  "_sha256": encoded({"archive": path.name, "sha256": sha, "size_bytes": path.stat().st_size,
                                       "status": "EXPORT_VALID", "manifest_sha256": oom.digest(manifest),
                                       "verified_evidence_members": 0})}
        for suffix, data in values.items():
            (self.root / (oom.STEM + suffix + ".json")).write_bytes(data)
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        with patch.object(oom, "RERUN_SHA", sha), patch.object(oom, "verify_archive", return_value=(selected, {"integrity": "SYNTHETIC"})), \
                patch.object(cohort, "inference", return_value=[[], [], planned]), \
                patch.object(cohort, "metadata", side_effect=AssertionError("GT_FORBIDDEN")):
            report, plan = oom.investigate(path, self.root, ROOT)
            self.assertEqual(report["coverage"], {"SUCCESS": 717, "TECHNICAL_ERROR": 1, "NOT_ATTEMPTED": 223})
            self.assertEqual(len(plan["mapping"]), 224)
            self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})
            target = self.root / (oom.STEM + "_export_sha256.json")
            target.write_bytes(encoded({"sha256": "0" * 64}))
            with self.assertRaisesRegex(ValueError, "EXPORT_RECEIPT_MISMATCH"):
                oom.investigate(path, self.root, ROOT)
            target.write_bytes(values["_export_sha256"])
            selected["binding.json"]["source"]["merge_commit"] = "a" * 40
            with self.assertRaisesRegex(ValueError, "WRONG_RELEASE"):
                oom.investigate(path, self.root, ROOT)

    def test_clean_import_does_not_import_ml_or_open_network(self):
        code = ("import sys\nfrom unittest.mock import patch\n"
                "with patch('socket.socket', side_effect=AssertionError('NETWORK_FORBIDDEN')):\n"
                " import safeshift.diagnostics.qwen3_s2_oom\n"
                "assert not ({'torch','transformers','PIL'} & set(sys.modules))")
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True, capture_output=True)

    def test_released_execution_scoring_authority_and_locks_are_byte_identical(self):
        paths = ["safeshift/diagnostics/hnlo_train/" + name + ".py" for name in
                 ("backend", "engine", "worker", "capture", "audit", "contract", "cohort", "bootstrap")]
        paths += ["safeshift/runners/qwen3_vl.py", "safeshift/runners/qwen3_placement.py",
                  "safeshift/diagnostics/hnlo_hf.py", "configs/diagnostics/hnlo_train_authority.v4.json",
                  "configs/diagnostics/hnlo_train_source.v4.json"]
        for path in paths:
            with self.subTest(path=path):
                released = subprocess.run(["git", "show", oom.RELEASE + ":" + path], cwd=ROOT,
                                          check=True, capture_output=True).stdout
                self.assertEqual((ROOT / path).read_bytes().replace(b"\r\n", b"\n"), released)


class BackendLifecycleTests(unittest.TestCase):
    def test_real_backend_success_releases_output_and_preserves_raw_replay_and_order(self):
        """Exercise actual Backend.generate via CPU doubles, not a rewritten adapter.

        Weakrefs establish Python ownership only; they cannot prove CUDA allocator
        behavior, absence of native leaks, or the OOM cause.
        """
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs_dir = root / "inputs"
            inputs_dir.mkdir()
            image_bytes = b"SYNTHETIC_NOT_AN_IMAGE"
            rows = [{"ordinal": i, "image_sha256": oom.digest(image_bytes)} for i in range(3)]
            for i in range(3):
                (inputs_dir / f"{i:06d}.image").write_bytes(image_bytes)
            refs, prepared_requests, seen_kwargs = [], [], []
            class IDs:
                shape = (1, 3)
                def __getitem__(self, i):
                    return self
                def tolist(self):
                    return [11, 22, 33]
            inputs = {"input_ids": IDs()}
            class NativeOutput(SimpleNamespace):
                pass
            config = SimpleNamespace(to_dict=lambda: deepcopy(CONFIG))
            native = SimpleNamespace(generation_config=config, model=SimpleNamespace(rope_deltas=None), _cache=None)
            def generate(**kwargs):
                self.assertIs(kwargs["input_ids"], inputs["input_ids"])
                self.assertEqual({k: v for k, v in kwargs.items() if k not in ("input_ids", "generation_config")}, KWARGS)
                seen_kwargs.append(kwargs["generation_config"].to_dict())
                out = NativeOutput(**vars(output('{"safety_level":"Level03"}', processed_delta=0)))
                refs.append(weakref.ref(out))
                return out
            native.generate = generate
            def prepare(request, context):
                self.assertEqual(request.input_bytes, image_bytes)
                self.assertEqual(request.prompt, "SYNTHETIC_PROMPT")
                prepared_requests.append(request.sample_id)
                return SimpleNamespace(inputs=inputs)
            runner = SimpleNamespace(_clear_call_state=Qwen3VLRunner._clear_call_state, prepare_input=prepare)
            def factory(index):
                b = backend.Backend.__new__(backend.Backend)
                b.inputs, b.cap, b.key, b.index, b.calls = inputs_dir, None, "qwen3", index, set()
                b.t1, b.candidates, b.tokenizer = probe(TOK), CANDIDATES, TOK
                b.runner, b.context, b.prompt, b.model = runner, object(), "SYNTHETIC_PROMPT", native
                b.policy = {"decoding": deepcopy(KWARGS)}
                b.torch = SimpleNamespace(inference_mode=nullcontext)
                # Retain native-start accounting in the injected fake model.
                def counted(**kwargs):
                    backend.record_native_call(index, b.cap, b.calls)
                    b.cap.write("raw-provenance", {"processors": []})
                    b.cap.write("stopping", {"max_length": 35, "eos_token_ids": [999]})
                    return generate(**kwargs)
                native.generate = counted
                def close():
                    self.assertIsNone(b.cap)
                    self.assertTrue(all(ref() is None for ref in refs))
                b.close = close
                return b
            def persist(out, ids, candidates, tok, cap, cfg, kw, torch):
                capture.persist(out, ids, candidates, tok, cap, cfg, kw,
                                lambda t, c, token: summarize_vector(t.data[0], c, token))
            with patch("safeshift.runners.qwen3_placement.require_loaded_state"), patch.object(backend, "persist_torch", persist):
                actual = engine.execute(root / "actual", rows, 3, factory)
            reference = engine.execute(root / "reference", rows, 3, lambda index: FakeBackend(index))
            self.assertTrue(actual.verify())
            self.assertTrue(actual.exists("finish"), actual.read("failure") if actual.exists("failure") else None)
            self.assertEqual(prepared_requests, ["0", "1", "2"])
            self.assertEqual(seen_kwargs, [CONFIG] * 3)
            for i in range(3):
                name = f"sample-{i:06d}"
                self.assertEqual(actual.read(name + ".result"), reference.read(name + ".result"))
                a, r = Journal(root / "actual" / name), Journal(root / "reference" / name)
                self.assertTrue(a.verify())
                self.assertEqual(a.read("trace"), r.read("trace"))
                with self.assertRaisesRegex(ValueError, "SEALED_JOURNAL_IMMUTABLE"):
                    a.write("late", {})


if __name__ == "__main__":
    unittest.main()
