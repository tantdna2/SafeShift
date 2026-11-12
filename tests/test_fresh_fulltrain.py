"""Issue171 CPU synthetic regression. No images, credentials, model or GPU."""
import copy
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from contextlib import ExitStack

from safeshift.fulltrain import contract as c, runtime as rt, inputs, preflight
from safeshift.candidates import fulltrain_run as journal
from safeshift.candidates.source import ROOT
from safeshift.pilot.contract import digest
from safeshift.pilot.artifacts import read, write, sha, export


def spec(key):
    return {"model_key": key, "model_id": "synthetic/" + key, "hnlo_policy": "LABEL_ONLY",
            **{n: "a" * (40 if n == "model_revision" else 64) for n in c.planning.IDENTITY_FIELDS}}


class Scripted:
    environment = {"scope": "SYNTHETIC_ONLY"}
    stage = "generation"
    def __init__(self, outputs):
        self.outputs, self.calls = iter(outputs), 0
    def generate(self, image, sample):
        self.calls += 1
        write(sample / "native_call.json", {"invocation": 1})
        value = next(self.outputs)
        if isinstance(value, BaseException):
            raise value
        return {"response": value, "generated_ids": [1], "raw_nonfinite": False}


class FreshTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cohort = journal.synthetic_cohort()
        self.campaign = c.campaign({k: self.cohort for k in c.planning.MODELS}, digest(self.cohort))
        self.bundle = self.root / "bundle"
        self.bundle.mkdir()
        for i in range(4):
            (self.bundle / f"{i:06d}.bin").write_bytes(journal.synthetic_bytes(i))

    def plan(self, *, key="minicpm4", history=None, action="initial", name="run1", cap=3, repair=None):
        return c.plan(self.campaign, self.cohort, spec(key), history or [], action=action,
                      run_id=name, attempt_id=name + "-attempt", max_calls=cap, max_seconds=60, repair=repair)

    def execute(self, outputs, *, p=None, history=None, work=None, **kwargs):
        p = p or self.plan()
        backend = Scripted(outputs)
        factory = Mock(return_value=backend)
        root = rt.rehearse(work or self.root / "work", self.bundle, self.cohort, self.campaign,
                            p, history or [], factory, **kwargs)
        return root, rt.recover(root, self.cohort, digest(p)), backend, factory

    def test_three_full_initial_plans_no_inherited_predictions(self):
        self.assertEqual(len(set(self.campaign["series"].values())), 3)
        total = 0
        for key in c.planning.MODELS:
            p = self.plan(key=key, cap=3763)
            self.assertEqual(p["scheduled_ordinals"], list(range(3763)))
            self.assertEqual(p["counts"], {"NOT_ATTEMPTED": 3763})
            self.assertTrue(all(not r["lineage"] for r in p["samples"]))
            total += len(p["scheduled_ordinals"])
        self.assertEqual(total, 11289)

    def test_exact_paired_projection_rejects_order_sha_and_160(self):
        for mutate in (lambda x: x["samples"].reverse(), lambda x: x["samples"].pop(),
                       lambda x: x["samples"][0].update(image_sha256="f" * 64)):
            bad = copy.deepcopy(self.cohort)
            mutate(bad)
            with self.assertRaises(ValueError):
                c.campaign({"qwen3": bad, "internvl35": self.cohort, "minicpm4": self.cohort}, digest(self.cohort))
        with self.assertRaisesRegex(ValueError, "ORIGINAL_MASTER"):
            inputs.project_master(b'{"approved":true}', digest(self.cohort))

    def test_native_descriptors_keep_science_but_new_selection(self):
        for key in ("internvl35", "minicpm4"):
            identity = c.native_identity(key)
            d = c.descriptor(key)
            self.assertEqual(digest(d), identity["configuration_sha256"])
            self.assertEqual(d["selection"]["count"], 3763)
            self.assertEqual(d["historical_selection_reference_only"]["max_native_calls"], 160)
            self.assertEqual(d["effective_candidate"]["dtype"], "float16")
            self.assertNotIn("selection", d["effective_candidate"])
        self.assertEqual(c.native_identity("minicpm4")["hnlo_policy"], "LABEL_ONLY")
        self.assertEqual(c.native_identity("qwen3")["model_id"], c.QWEN["id"])
        self.assertEqual(c.descriptor("qwen3")["effective_candidate"]["generation"]["max_new_tokens"], 32)

    def test_no_public_entrypoint_reads_paths_or_accepts_approved(self):
        class Poison:
            def __fspath__(self):
                raise AssertionError("private input accessed")
        for entry in (rt.launch, rt.worker, rt.native_factory, preflight.live_preflight):
            with self.subTest(entry=entry), self.assertRaises(PermissionError):
                entry(Poison(), approved=True) if entry != rt.native_factory else entry(Poison(), Poison(), Poison())
        result = subprocess.run(rt.worker_command(sys.executable, self.root / "private.json", self.root / "out"),
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ISSUE171_NO_GPU", result.stderr)
        self.assertFalse((self.root / "out").exists())

    def test_success_invalid_error_resume_only_not_attempted(self):
        p = self.plan(cap=4)
        root, h, backend, factory = self.execute(['{"safety_level":"Level04"}', 'fenced INVALID', RuntimeError("out of memory")], p=p)
        self.assertEqual([r["status"] for r in h["records"]], ["SUCCESS", "INVALID", "TECHNICAL_ERROR", "NOT_ATTEMPTED"])
        self.assertEqual(factory.call_count, 1)
        self.assertEqual(backend.calls, 3)
        pending = self.plan(history=[h], action="resume", name="run2", cap=1)
        self.assertEqual(pending["scheduled_ordinals"], [3])
        _, resumed, calls, _ = self.execute(['{"safety_level":"Level04"}'], p=pending, history=[h])
        self.assertEqual(calls.calls, 1)
        self.assertEqual(resumed["records"][0]["sample_id"], "synthetic-0003")

    def test_foreign_series_or_identity_rejected_before_calls(self):
        _, h, _, _ = self.execute(['bad'] * 3)
        for change in (lambda x: x.update(series_id="historical-initial"),
                       lambda x: x["identity"].update(configuration_sha256="f" * 64)):
            bad = copy.deepcopy(h)
            change(bad)
            with self.assertRaisesRegex(ValueError, "FOREIGN_HISTORY"):
                self.plan(history=[bad], action="resume", name="run2")
        with self.assertRaisesRegex(ValueError, "NEW_CAMPAIGN"):
            self.plan(history=[h], action="rerun", name="run2")

    def test_partial_reservation_prevents_implicit_retry(self):
        p = self.plan()
        self.execute(['bad'] * 3, p=p)
        with self.assertRaisesRegex(ValueError, "UNRECONCILED_RESERVATION"):
            self.execute(['bad'] * 3, p=self.plan(name="new-initial"))

    def test_history_checksum_and_missing_ancestor_fail_closed(self):
        root, h, _, _ = self.execute(['bad'] * 3)
        p = self.plan(history=[h], action="resume", name="run2", cap=1)
        (root / "receipt.json").write_text('{}')
        with self.assertRaisesRegex(ValueError, "SEALED_JOURNAL_CHANGED"):
            self.execute(['bad'], p=p, history=[h])

    def test_repair_requires_outcome_fix_regression_and_cause(self):
        _, h, _, _ = self.execute(['bad'] * 3)
        repair = {"targets": {h["records"][0]["sample_id"]: digest(h["records"][0])},
                  "fix_sha256": "b" * 64, "regression_sha256": "c" * 64, "diagnosis": "synthetic format incident"}
        p = self.plan(history=[h], action="repair", name="repair1", repair=repair)
        with self.assertRaisesRegex(ValueError, "REPAIR_CAUSE"):
            self.execute(['bad'], p=p, history=[h])
        case = {"plan_sha256": digest(p), "cause_evidence_sha256": "d" * 64,
                "fix_sha256": repair["fix_sha256"], "regression_sha256": repair["regression_sha256"]}
        _, fixed, _, _ = self.execute(['still invalid'], p=p, history=[h], repair_case=case)
        self.assertEqual(fixed["records"][0]["status"], "INVALID")
        self.assertEqual(h["records"][0]["status"], "INVALID")

    def test_source_input_change_before_call_is_not_retried(self):
        p = self.plan(cap=1)
        def change():
            (self.bundle / "000000.bin").write_bytes(b"changed")
        backend = Mock()
        with self.assertRaisesRegex(ValueError, "INPUT_CHANGED"):
            rt.rehearse(self.root / "work", self.bundle, self.cohort, self.campaign, p, [], backend, before_call=change)
        backend.assert_not_called()
        self.assertTrue((self.root / "work/run1.zip").exists())

    def test_zip_import_fresh_workspace_exact_resume_and_no_overwrite(self):
        root, h, _, _ = self.execute(['bad'] * 3)
        archive = Path(str(root) + ".zip")
        work = self.root / "imported"
        imported = rt.import_history(work, archive, sha(archive), self.cohort, self.campaign, digest(self.plan()))
        self.assertEqual(imported, h)
        p = self.plan(history=[h], action="resume", name="run2", cap=1)
        _, _, backend, _ = self.execute(['bad'], p=p, history=[h], work=work)
        self.assertEqual(backend.calls, 1)
        with self.assertRaisesRegex(ValueError, "NO_OVERWRITE"):
            rt.import_history(work, archive, sha(archive), self.cohort, self.campaign, digest(self.plan()))
        with self.assertRaisesRegex(ValueError, "OUTER_ARCHIVE"):
            rt.import_history(self.root / "bad", archive, "e" * 64, self.cohort, self.campaign, digest(self.plan()))

    def test_load_failure_keeps_pending_and_failure_evidence(self):
        p = self.plan(cap=1)
        root = rt.rehearse(self.root / "work", self.bundle, self.cohort, self.campaign, p, [],
                            Mock(side_effect=ImportError("synthetic missing dependency")))
        h = journal.recover(root, self.cohort, digest(p))
        self.assertEqual(h["records"][0]["status"], "NOT_ATTEMPTED")
        self.assertTrue((root / "calls/000000/run/failure.json").exists())
        self.assertEqual(read(root / "receipt.json")["loads"], 0)

    def test_mapping_strict_no_gt_no_order_drift(self):
        rows = [{**r, "image": f"images/{r['ordinal']:06d}.jpg", "width": 1, "height": 1} for r in self.cohort["samples"]]
        inputs.validate_mapping(self.cohort, rows)
        rows[0]["label"] = "Level04"
        with self.assertRaisesRegex(ValueError, "NO_GT"):
            inputs.validate_mapping(self.cohort, rows)

    def test_marker_missing_duplicate_and_bad_pin(self):
        mounts = self.root / "inputs"
        mounts.mkdir()
        with self.assertRaisesRegex(ValueError, "UNIQUE"):
            inputs.admit(mounts, "a" * 64, digest(self.cohort))
        for name in ("one", "two"):
            d = mounts / name
            d.mkdir()
            write(d / inputs.MARKER, {"invalid": True})
        with self.assertRaisesRegex(ValueError, "FOUND_2"):
            inputs.admit(mounts, "a" * 64, digest(self.cohort))
        (mounts / "two" / inputs.MARKER).unlink()
        with self.assertRaisesRegex(ValueError, "MARKER_PIN"):
            inputs.admit(mounts, "a" * 64, digest(self.cohort))

    def test_storage_simultaneous_cleanup_repeat_and_quota_failure(self):
        for _ in range(2):
            r = preflight.storage_probe(self.root, self.bundle, scratch_bytes=4096, output_bytes=4096)
            self.assertTrue(r["cleanup_verified"])
            self.assertTrue(r["same_filesystem"])
        with patch.object(preflight.shutil, "disk_usage", return_value=type("Disk", (), {"free": 5000})()):
            with self.assertRaisesRegex(ValueError, "SHARED_FILESYSTEM"):
                preflight.storage_probe(self.root, self.bundle, scratch_bytes=4096, output_bytes=4096)
        with patch.object(preflight.os, "fsync", side_effect=OSError("synthetic quota")):
            with self.assertRaises(OSError):
                preflight.storage_probe(self.root, self.bundle, scratch_bytes=4096, output_bytes=4096)
        self.assertFalse(list(self.root.glob(".fresh-probe-*")))

    def test_native_factory_reuses_exact_candidate_and_fp32_adapter(self):
        # Mock only native external loading. The public entry is separately fenced.
        with patch("safeshift.candidates.source.verify_snapshot"), patch("safeshift.candidates.loading.verify_weights"), \
             patch("safeshift.candidates.backend.CandidateBackend") as ivl, \
             patch("safeshift.candidates.minicpm_resampler_fp32.backend") as mini:
            rt._native_factory("internvl35", self.root, self.root)
            rt._native_factory("minicpm4", self.root, self.root)
            self.assertEqual(ivl.call_count, 1)
            self.assertEqual(mini.call_count, 1)
            self.assertEqual(mini.call_args.kwargs, {"device": "cuda:0"})

    def test_all_statuses_across_shards_cover_full_plan_once(self):
        for key in c.planning.MODELS:
            history, consumed = [], []
            for n in range(4):
                p = self.plan(key=key, history=history, action="initial" if not history else "resume",
                              name=f"shard{n}", cap=1000)
                records = []
                for ordinal in p["scheduled_ordinals"]:
                    status = ("SUCCESS", "INVALID", "TECHNICAL_ERROR")[ordinal % 3]
                    r = self.cohort["samples"][ordinal]
                    records.append({"sample_id": r["sample_id"], "image_sha256": r["image_sha256"],
                        "status": status, "label": "Level04" if status == "SUCCESS" else None,
                        "attempts": 1, "native_calls": 1,
                        **({"raw_sha256": "b" * 64} if status != "TECHNICAL_ERROR" else {})})
                consumed.extend(p["scheduled_ordinals"])
                history.append({"run_id": p["run_id"], "attempt_id": p["attempt_id"], "series_id": p["series_id"],
                    "identity": p["identity"], "cohort_sha256": p["cohort_sha256"], "parent_history_sha256": digest(history),
                    "action": p["action"], "records": records, "evidence_sha256": "d" * 64, "repair": None})
            self.assertEqual(consumed, list(range(3763)))
            noop = self.plan(key=key, history=history, action="resume", name="done", cap=3763)
            self.assertEqual(noop["scheduled_ordinals"], [])
            self.assertEqual(sum(noop["counts"].values()), 3763)

    def test_torn_raw_recovery_preserves_bytes_and_native_marker_only_is_error(self):
        p = self.plan(cap=2)
        root, _, _, _ = self.execute(['{"safety_level":"Level01"}', 'bad'], p=p)
        # Copy to a new synthetic unsealed crash fixture; original sealed run stays intact.
        import shutil
        partial = self.root / "partial"
        shutil.copytree(root, partial)
        (partial / "checksums.json").unlink()
        first = partial / "calls/000000/run/samples/000000"
        raw_hash = sha(first / "raw.json")
        (first / "result.json").unlink()
        second = partial / "calls/000001/run/samples/000000"
        (second / "raw.json").unlink()
        (second / "result.json").unlink()
        h = rt.recover(partial, self.cohort, digest(p))
        self.assertEqual([r["status"] for r in h["records"]], ["SUCCESS", "TECHNICAL_ERROR"])
        self.assertEqual(sha(first / "raw.json"), raw_hash)
        self.assertEqual(h["records"][1]["reason"], "INTERRUPTED_OR_TORN_EVIDENCE")
        # Malformed raw is UNKNOWN/BLOCKED, never silently pending for retry.
        (first / "raw.json").write_text('{')
        with self.assertRaises(ValueError):
            rt.recover(partial, self.cohort, digest(p))

    def test_raw_durable_before_parser_failure(self):
        p = self.plan(cap=1)
        with patch("safeshift.pilot.runner.parse_label", side_effect=RuntimeError("synthetic parse crash")):
            root, h, _, _ = self.execute(['{"safety_level":"Level04"}'], p=p)
        self.assertTrue((root / "calls/000000/run/samples/000000/raw.json").is_file())
        self.assertEqual(h["records"][0]["status"], "TECHNICAL_ERROR")
        self.assertEqual(len(read(root / "accounting.json")["samples"]), 3763)

    def test_deadline_stops_without_load_and_time_has_no_default(self):
        p = self.plan(cap=1)
        clock = Mock(side_effect=[0, 61])
        root, h, backend, factory = self.execute([], p=p, clock=clock)
        factory.assert_not_called()
        self.assertEqual(read(root / "receipt.json")["stop"], "TIME_CAP")
        self.assertEqual(h["records"][0]["status"], "NOT_ATTEMPTED")

    def test_false_preflight_receipts_do_not_grant_execution(self):
        binding = {n: "a" * 64 for n in ("cohort_sha256", "source_sha256", "runtime_sha256", "checkpoint_sha256")}
        for name in preflight.CHECKS:
            receipt = {"binding": binding, "evidence": {"status": "PASS", "approved": True}}
            r = preflight.admit_receipts("minicpm4", binding, {name: receipt}, {name: digest(receipt)})
            self.assertEqual(r["status"], "BLOCKED")
            self.assertEqual(r["checks"][name]["status"], "BLOCKED")
            self.assertEqual(r["levels"]["WEIGHTS_LOADED"], "NOT_RUN")

    def test_native_worker_missing_source_stops_before_inputs(self):
        request = {n: None for n in ("model_key", "source_sha256", "inputs", "marker_sha256", "projection_sha256",
                "campaign", "plan", "history", "work", "scratch", "resource_policy", "repair_case")}
        request.update(model_key="minicpm4", source_sha256="f" * 64)
        with patch("safeshift.fulltrain.inputs.admit") as admission:
            with self.assertRaisesRegex(ValueError, "FINAL_NATIVE_SOURCE"):
                rt._worker(request)
            admission.assert_not_called()

    def test_peer_worker_to_native_store_parser_archive_with_scripted_boundaries(self):
        # CPU wiring proof only: all hardware, real images and model loading are
        # explicit doubles. The actual controller, NativeStore, parser and archive run.
        for key, mounted in (("internvl35", False), ("minicpm4", False), ("minicpm4", True)):
            with self.subTest(key=key, original_mounts=mounted), ExitStack() as stack:
                identity = c.native_identity(key)
                p = c.plan(self.campaign, self.cohort, identity, [], action="initial",
                    run_id="native-" + key, attempt_id="attempt-" + key, max_calls=1, max_seconds=60)
                suffix = key + ("-mounted" if mounted else "")
                bundle = self.root / suffix
                (bundle / "images").mkdir(parents=True)
                (bundle / "images/000000.jpg").write_bytes(journal.synthetic_bytes(0))
                rows = [{**row, "image": f"images/{row['ordinal']:06d}.jpg", "width": 1, "height": 1}
                        for row in self.cohort["samples"]]
                effective = c.descriptor(key)["effective_candidate"]
                from safeshift.pilot.contract import GENERATION
                prompt = (ROOT / "configs/pilot/classification_c1.txt").read_text(encoding="utf-8")
                class NativeScripted:
                    environment = {"scope": "SCRIPTED_NATIVE_BOUNDARY_NO_MODEL"}
                    stage = "generation"
                    def generate(inner, image, sample):
                        write(sample / "native_call.json", {"invocation": 1})
                        write(sample / "native.json", {"generated_ids": [1], "sequence_semantics": effective["sequence_semantics"]})
                        step = {"all_finite": True, "step": 0}
                        write(sample / "steps/000.json", step)
                        write(sample / "request.json", {"prompt": prompt,
                            "model": {n: effective["model"][n] for n in ("id", "revision")},
                            "generation": {**GENERATION, "repetition_penalty": 1.0}, "image": {"processor_mode": "RGB"},
                            "input_detail": {"tiles_including_thumbnail" if key == "internvl35" else "slices_including_global": 1}})
                        if key == "minicpm4":
                            fields = ("scores_fp32_finite_or_negative_mask", "softmax_fp32_finite", "value_product_fp32_finite_and_return_cast")
                            write(sample / "effective_numerics.json", {"implementation": effective["numerical_policy"],
                                "before": dict.fromkeys(fields, 0), "after": {**dict.fromkeys(fields, 1), "returned_dtype": "torch.float16"}})
                        return {"response": '{"safety_level":"Level03"}', "generated_ids": [1], "steps": [step],
                            "cpu_tokenizer_replay": {"status": "PASS"}, "logit_capture_boundary": effective["logits"]["boundary"]}
                stack.enter_context(patch("safeshift.fulltrain.inputs.admit", return_value=(bundle, self.cohort, rows)))
                stack.enter_context(patch("safeshift.fulltrain.inputs.verify_image_bytes"))
                stack.enter_context(patch("safeshift.candidates.train_inputs.checkpoint", return_value=(None, self.root, self.root)))
                for target in ("safeshift.candidates.source.verify_snapshot", "safeshift.candidates.loading.verify_weights",
                               "safeshift.candidates.train_runtime.software", "safeshift.candidates.train_runtime.worker_cuda",
                               "safeshift.candidates.train_runtime.resources", "safeshift.candidates.train_runtime.verify_images"):
                    stack.enter_context(patch(target))
                factory = stack.enter_context(patch.object(rt, "_native_factory", return_value=NativeScripted()))
                hnlo = stack.enter_context(patch("safeshift.pilot.hnlo.replay", return_value={"status": "SCRIPTED_ONLY", "hnlo": None}))
                request = {"model_key": key, "source_sha256": digest(c.source_manifest()), "inputs": self.root,
                    "marker_sha256": "f" * 64, "projection_sha256": digest(self.cohort), "campaign": self.campaign,
                    "plan": p, "history": [], "work": self.root / ("native-work-" + suffix), "scratch": self.root,
                    "resource_policy": {"review_mode": "EXTERNAL"}, "repair_case": None}
                if mounted:
                    from test_fresh_fulltrain_revision import budgets
                    from safeshift.fulltrain import original_inputs, admission, environment
                    binding = {"schema": original_inputs.SCHEMA, "master_sha256": original_inputs.MASTER_SHA,
                        "projection_sha256": digest(self.cohort), **{name: {"ref": ref, "version": 1,
                        "mount": ref.split("/")[1]} for name, ref in original_inputs.REFS.items()}}
                    request.update(original_inputs=binding, marker_sha256=digest(binding),
                        inputs=str(self.root / "synthetic-mounts"), scratch=str(self.root / "scratch-mounted"),
                        checkpoint_marker_sha256="a"*64, resource_policy=budgets(), runtime_lock=None,
                        runtime_lock_sha256=None, software_input=None, software_marker_sha256=None)
                    stack.enter_context(patch.object(original_inputs, "admit", return_value=(bundle, self.cohort, rows)))
                    stack.enter_context(patch.object(original_inputs, "verify_bytes"))
                    stack.enter_context(patch.object(original_inputs, "verify_images"))
                    stack.enter_context(patch.object(admission, "checkpoint_binding", return_value=(None, self.root, self.root, {})))
                    for name in ("resources", "hardware", "cuda"):
                        stack.enter_context(patch.object(environment, name))
                result = rt._worker(request)
                h = rt.recover(result, self.cohort, digest(p))
                self.assertEqual(h["records"][0]["status"], "SUCCESS")
                self.assertEqual(h["records"][0]["label"], "Level03")
                self.assertEqual(factory.call_count, 1)
                self.assertEqual(hnlo.call_count, int(key == "internvl35"))
                self.assertTrue(Path(str(result) + ".zip").is_file())


if __name__ == "__main__":
    unittest.main()
