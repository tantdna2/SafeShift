"""D9R13 CPU/fake-only PREP tests; never execute a real model or runtime gate."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

from safeshift.runners.paligemma_external_probe import LABELS, QUERY_LABELS, parse_probe
from safeshift.runners.paligemma_snapshot import json_bytes
from scripts import w2_paligemma_external_gate as q
from tests import test_paligemma_prep as fakes

NOTEBOOK = q.ROOT / "notebooks/w2_paligemma_d9r13_external_gate_kaggle.ipynb"


def native(label="red square", values=(0, 1, 1023, 1022), text=None):
    ids = [256000 + v for v in values] + [42, 1]
    return json_bytes({"schema_version": "paligemma-native-output-v1",
        "model_id": q.MODEL_ID, "revision": q.REVISION, "decoding": q.DECODING,
        "input_token_ids": [2, 108], "generated_ids_full": [[2, 108] + ids],
        "continuation_ids": ids, "decoded_text": " " + label,
        "decoded_with_special_tokens": (text if text is not None else
            "".join(f"<loc{v:04d}>" for v in values) + " " + label + "<eos>")})


def sources():
    return ["".join(c["source"]) for c in json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]
            if c["cell_type"] == "code"]


class ParserTests(unittest.TestCase):
    def test_four_exact_labels_axes_and_1024(self):
        for query, label in QUERY_LABELS.items():
            result, diag = parse_probe(native(label), query)
            self.assertTrue(result.success)
            self.assertEqual(result.value.bbox, (1/1024, 0, 1022/1024, 1023/1024))
            self.assertEqual(diag["native_label"], label)

    def test_wrong_label_preserved_without_correction(self):
        result, diag = parse_probe(native("green circle"), "Locate the red square.")
        self.assertIsNone(result.value)
        self.assertIn("TARGET_LABEL_MISMATCH", result.errors[0])
        self.assertEqual(diag["native_label"], "green circle")
        self.assertIsNotNone(diag["native_bbox"])

    def test_grammar_closed_no_fuzzy_multiple_box_or_absence_repair(self):
        valid = json.loads(native())["decoded_with_special_tokens"]
        for text in ("", "none", "[]", valid + valid, valid + "\n", valid.replace("<eos>", ""),
                     valid.replace("red square", "RED SQUARE"), valid.replace("red square", "shape"),
                     valid.replace("red square", "red square extra"), " " + valid,
                     valid.replace("<loc0000>", "<loc0>")):
            with self.subTest(text=text):
                self.assertIsNone(parse_probe(native(text=text), "Locate the red square.")[0].value)

    def test_bounds_and_geometry_fail_without_clamp(self):
        for values in ((0, 0, 1024, 1023), (500, 0, 100, 999), (0, 1, 0, 10)):
            self.assertIsNone(parse_probe(native(values=values), "Locate the red square.")[0].value)

    def test_envelope_token_boundary_identity_and_text_agreement(self):
        for key, value in (("revision", "main"), ("generated_ids_full", []),
                           ("continuation_ids", [1, 42, 1]), ("input_token_ids", [True]),
                           ("continuation_ids", [42] * 33 + [1]), ("decoded_text", None)):
            obj = json.loads(native())
            obj[key] = value
            self.assertIsNone(parse_probe(json_bytes(obj), "Locate the red square.")[0].value)
        obj = json.loads(native())
        obj["decoded_with_special_tokens"] = obj["decoded_with_special_tokens"].replace("loc0001", "loc0002")
        self.assertIsNone(parse_probe(json_bytes(obj), "Locate the red square.")[0].value)
        for raw in (b"[]", b"null", b"{}", b"bad", b'{"a":1,"a":2}'):
            self.assertIsNone(parse_probe(raw, "Locate the red square.")[0].value)
        self.assertIsNone(parse_probe(native(), "red square")[0].value)


class PlanTests(unittest.TestCase):
    def test_exact_notebook_source_pin(self):
        import ast
        tree = ast.parse(sources()[0])
        pin = next(ast.literal_eval(n.value) for n in tree.body
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "BASE"
                                                       for t in n.targets))
        self.assertEqual(pin, "bcc7b7be62891c887e9509dd39688d686a1b6020")
        subprocess.run(["git", "merge-base", "--is-ancestor", q.BASE_SHA, pin],
                       cwd=q.ROOT, check=True, capture_output=True)
        paths = (q.PLAN, "scripts/w2_paligemma_external_gate.py",
                 "safeshift/runners/paligemma_external_probe.py",
                 "scripts/w2_paligemma_interface_qualification.py",
                 "scripts/w2_paligemma_t4_smoke.py", "scripts/provision_paligemma_snapshot.py",
                 "safeshift/runners/paligemma.py", "safeshift/runners/paligemma_snapshot.py",
                 "safeshift/runners/storage.py", "safeshift/runners/contracts.py",
                 "safeshift/protocol/gate.py", "safeshift/protocol/schema.py",
                 "safeshift/protocol/firewall.py", "requirements-paligemma-t4.txt",
                 q.gate_plan()["runtime_plan"], q.gate_plan()["manifest"],
                 q.gate_plan()["provenance"], q.gate_plan()["generator"],
                 q.gate_plan()["negative_evidence"]["path"])
        for path in paths:
            committed = subprocess.check_output(["git", "show", pin + ":" + path], cwd=q.ROOT)
            self.assertEqual(committed.replace(b"\r\n", b"\n"),
                             (q.ROOT / path).read_bytes().replace(b"\r\n", b"\n"), path)

    def test_exact_frozen_inputs_and_budget(self):
        from safeshift.protocol.prompts import probe_request
        p = q.gate_plan()
        cases, inputs = q.verify_suite(p)
        self.assertEqual((p["classification_calls"], p["native_generate_calls"], p["model_loads"]), (0, 8, 1))
        self.assertEqual(tuple(c.case_id for c in cases), q.CASE_IDS)
        self.assertEqual(tuple(p["parser_labels"]), LABELS)
        self.assertEqual(p["query_to_label"], QUERY_LABELS)
        self.assertFalse(p["runtime_regeneration"])
        self.assertFalse(any(p["execution"].values()))
        for case, (request, metadata) in zip(cases, inputs):
            self.assertEqual(request.input_bytes, (q.ROOT / case.image_path).read_bytes())
            self.assertEqual(request.prompt, "detect " + QUERY_LABELS[case.target_query])
            self.assertEqual(metadata["target_query"], case.target_query)
            canonical = probe_request(q.ROOT, case.image_path, case.target_query)
            self.assertTrue(canonical.prompt.startswith(case.target_query + "\n"))
            self.assertNotEqual(request.prompt, canonical.prompt)
            self.assertEqual(metadata["target_gt_bbox"], list(case.target_gt_bbox))
            self.assertEqual(metadata["distractor_gt_bbox"], list(case.distractor_gt_bbox))

    def test_frozen_sources_and_gate_unchanged(self):
        roots = ["safeshift", "schemas", "configs/pre_freeze",
                 "tests/fixtures/pre_freeze/frozen_external_gate",
                 "scripts/w2_paligemma_interface_qualification.py",
                 "notebooks/w2_paligemma_d9r11_interface_qualification_kaggle.ipynb",
                 "scripts/generate_external_gate_cases.py"]
        paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", q.BASE_SHA,
                                         "--", *roots], cwd=q.ROOT, text=True).splitlines()
        for path in paths:
            # D9R15 changes current roster overlays; dedicated D9R15 tests also
            # compare all documentary provenance content outside its overlay.
            if path in {"configs/pre_freeze/local_models.d9.json",
                        "configs/pre_freeze/local_model_provenance.d9.json",
                        "configs/pre_freeze/freeze_manifest.d9.template.json"}:
                continue
            original = subprocess.check_output(["git", "show", f"{q.BASE_SHA}:{path}"], cwd=q.ROOT)
            current = (q.ROOT / path).read_bytes()
            if not path.endswith(".png"):
                original, current = original.replace(b"\r\n", b"\n"), current.replace(b"\r\n", b"\n")
            self.assertEqual(current, original, path)


    def test_notebook_unexecuted_compiles_and_guards_runtime(self):
        nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        for c in nb["cells"]:
            if c["cell_type"] == "code":
                self.assertIsNone(c["execution_count"])
                self.assertEqual(c["outputs"], [])
                compile("".join(c["source"]), "notebook", "exec")
        setup = sources()[1]
        self.assertLess(setup.index('"verify_suite"'), setup.index('"SOFTWARE_INSTALL"'))
        self.assertLess(setup.index('"verify_suite"'), setup.index('"PROVISION"'))
        self.assertIn('provision_env["HF_TOKEN"] = hf_token', setup)
        code = "\n".join(sources())
        self.assertNotIn("model.generate", code)
        self.assertNotIn("from_pretrained", code)
        self.assertIn(q.PLAN_SHA256, code)
        self.assertIn('summary["native_generate_calls"] == 8', code)
        self.assertIn('OWNER_ATTEST_INTERNET_OFF = False', code)


class HarnessTests(unittest.TestCase):
    def setUp(self):
        fakes.RunnerTests.setUp(self)
        self.plan = q.gate_plan()
        paths = [q.PLAN, self.plan["manifest"], self.plan["provenance"], self.plan["generator"],
                 self.plan["negative_evidence"]["path"],
                 "scripts/w2_paligemma_external_gate.py", "scripts/w2_paligemma_interface_qualification.py",
                 "safeshift/protocol/gate.py", "safeshift/protocol/schema.py",
                 "safeshift/runners/paligemma_external_probe.py"]
        paths += [self.plan["image_root"] + "/" + name + ".png" for name in q.CASE_IDS]
        for name in paths:
            dest = self.repo / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(q.ROOT / name, dest)
        self.stack.enter_context(patch.dict(os.environ, CUDA_VISIBLE_DEVICES="0", CUDA_DEVICE_ORDER="PCI_BUS_ID",
            HF_TOKEN="", HUGGING_FACE_HUB_TOKEN="", GH_TOKEN="", GITHUB_TOKEN=""))
        self.stack.enter_context(patch.object(q, "checkout_gate"))
        self.stack.enter_context(patch.object(q.subprocess, "run"))
        self.stack.enter_context(patch.object(q.platform, "system", return_value="Linux"))
        self.stack.enter_context(patch.object(q.platform, "machine", return_value="x86_64"))
        self.stack.enter_context(patch.object(q, "software_versions", return_value=self.ctx.software_versions))

    def run_harness(self):
        return q.run_gate(expected_commit="a" * 40, venue_internet_off=True, repo=self.repo,
                          runner_factory=lambda **_: self.runner, torch_module=self.torch)

    def fake_valid_outputs(self):
        # Explicit mock outputs derived from GT ONLY IN CPU UNIT TESTS.
        cases, _ = q.verify_suite(self.plan, self.repo)
        def generate(**kwargs):
            case = cases[self.model.generate_count]
            self.model.generate_count += 1
            x0, y0, x1, y1 = case.target_gt_bbox
            self.fake_values = [int(v * 1024) for v in (y0, x0, y1, x1)]
            self.fake_label = QUERY_LABELS[case.target_query]
            return fakes.Tensor([kwargs["input_ids"].tolist()[0] +
                                 [256000 + v for v in self.fake_values] + [42, 1]])
        def decode(ids, **kwargs):
            return ("".join(f"<loc{v:04d}>" for v in self.fake_values) + " " + self.fake_label +
                    ("<eos>" if not kwargs["skip_special_tokens"] else ""))
        self.model.generate = generate
        self.processor.decode = decode

    def reviews(self, status="NO_GIANT"):
        q.write_json(self.repo / "data/processed/review.json", {
            case_id: {"status": status, "reviewer": "CPU_TEST_ONLY",
                      "rationale": "Mock review, not research evidence."} for case_id in q.CASE_IDS})
        return "data/processed/review.json"

    def test_eight_calls_one_load_raw_fsync_reread_before_parser(self):
        events = []
        original_fsync, original_read, original_parse = os.fsync, Path.read_bytes, q.parse_probe
        def sync(fd):
            events.append("fsync")
            return original_fsync(fd)
        def read(path):
            raw = original_read(path)
            if path.name == "response.raw":
                events.append("reread")
            return raw
        def parse(raw, query):
            self.assertEqual(events[-3:], ["fsync", "fsync", "reread"])
            events.append("parse")
            return original_parse(raw, query)
        with patch.object(os, "fsync", side_effect=sync), patch.object(Path, "read_bytes", read), \
                patch.object(q, "parse_probe", side_effect=parse):
            result = self.run_harness()
        self.assertEqual(result["status"], q.COMPLETE)
        self.assertEqual((result["model_load_count"], result["native_generate_calls"],
                          result["classification_calls"]), (1, 8, 0))
        self.assertEqual(result["paligemma_external_gate_status"], "FAIL")
        self.assertEqual(self.processor.prompts, [
            "detect red square", "detect red square",
            "detect green circle", "detect green circle",
            "detect yellow triangle", "detect yellow triangle",
            "detect cyan rectangle", "detect cyan rectangle"])
        self.assertEqual(events.count("parse"), 8)
        self.assertEqual(len({id(i) for i in self.processor.prepared}), 8)
        self.assertEqual(len({c["raw"]["path"] for c in result["calls"]}), 8)
        with self.assertRaises(FileExistsError):
            self.run_harness()
        self.assertEqual(self.model.generate_count, 8)

    def test_success_stays_pending_until_explicit_human_review(self):
        self.fake_valid_outputs()
        result = self.run_harness()
        self.assertEqual(result["status"], q.COMPLETE)
        self.assertEqual(result["paligemma_external_gate_status"], "PENDING_REVIEW")
        final = q.finalize_review(self.reviews(), repo=self.repo, expected_commit="a" * 40)
        self.assertEqual(final["paligemma_external_gate_status"], "PASS")
        self.assertFalse(final["promotion"])
        self.assertEqual(self.model.generate_count, 8)
        with self.assertRaises(FileExistsError):
            q.finalize_review("data/processed/review.json", repo=self.repo, expected_commit="a" * 40)

    def test_schema_failure_remains_fail_after_no_giant_review(self):
        self.run_harness()
        result = q.finalize_review(self.reviews(), repo=self.repo, expected_commit="a" * 40)
        self.assertEqual(result["paligemma_external_gate_status"], "FAIL")

    def test_giant_review_fails_without_new_threshold(self):
        self.fake_valid_outputs()
        self.run_harness()
        result = q.finalize_review(self.reviews("GIANT"), repo=self.repo, expected_commit="a" * 40)
        self.assertEqual(result["paligemma_external_gate_status"], "FAIL")

    def test_pending_review_rejected_without_model_call(self):
        self.run_harness()
        with self.assertRaisesRegex(ValueError, "CANNOT_BE_PENDING"):
            q.finalize_review(self.reviews("PENDING"), repo=self.repo, expected_commit="a" * 40)
        self.assertEqual(self.model.generate_count, 8)

    def test_review_rejects_changed_raw(self):
        self.run_harness()
        raw = next((self.repo / q.ARTIFACTS).rglob("response.raw"))
        raw.write_bytes(raw.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "ARTIFACT_HASH"):
            q.finalize_review(self.reviews(), repo=self.repo, expected_commit="a" * 40)

    def test_frozen_image_change_stops_before_load(self):
        path = self.repo / self.plan["image_root"] / "A_1.png"
        path.write_bytes(path.read_bytes() + b" ")
        result = self.run_harness()
        self.assertEqual(result["failure"]["stage"], "FROZEN_SUITE")
        self.assertEqual(result["model_load_count"], 0)

    def test_credentials_stop_before_load(self):
        with patch.dict(os.environ, HF_TOKEN="FAKE_TEST_SECRET"):
            result = self.run_harness()
        self.assertEqual(result["failure"]["stage"], "OFFLINE_PREFLIGHT")
        self.assertEqual(result["model_load_count"], 0)

    def test_offline_mask_required_before_load(self):
        with patch.dict(os.environ, CUDA_VISIBLE_DEVICES="0,1"):
            result = self.run_harness()
        self.assertEqual(result["failure"]["stage"], "OFFLINE_PREFLIGHT")
        self.assertEqual(result["model_load_count"], 0)

    def test_missing_human_decision_is_not_inferred(self):
        self.run_harness()
        q.write_json(self.repo / "data/processed/review.json", {})
        with self.assertRaisesRegex(ValueError, "EIGHT_EXPLICIT_HUMAN_REVIEWS"):
            q.finalize_review("data/processed/review.json", repo=self.repo, expected_commit="a" * 40)
        self.assertEqual(self.model.generate_count, 8)

    def test_corrupt_reread_stops_no_parser_no_retry(self):
        original = Path.read_bytes
        def read(path):
            raw = original(path)
            return raw + b" " if path.name == "response.raw" else raw
        with patch.object(Path, "read_bytes", read), patch.object(q, "parse_probe") as parser:
            result = self.run_harness()
        self.assertEqual(result["status"], q.STOP)
        parser.assert_not_called()
        self.assertEqual(self.model.generate_count, 1)

    def test_fsync_failure_stops_before_parser(self):
        from safeshift.runners import storage
        original = storage._write_new
        def write(path, raw):
            if path.name == "response.raw":
                with patch.object(storage.os, "fsync", side_effect=OSError("FAKE")):
                    return original(path, raw)
            return original(path, raw)
        with patch.object(storage, "_write_new", side_effect=write), patch.object(q, "parse_probe") as parser:
            result = self.run_harness()
        self.assertEqual(result["status"], q.STOP)
        parser.assert_not_called()
        self.assertEqual(self.model.generate_count, 1)

    def test_partial_failure_preserves_ids(self):
        self.processor.decode_error = ValueError("FAKE")
        with patch.object(q, "parse_probe") as parser:
            result = self.run_harness()
        self.assertEqual(result["status"], q.STOP)
        parser.assert_not_called()
        raw = next((self.repo / q.ARTIFACTS).rglob("response.raw"))
        self.assertIn("generated_ids_full", json.loads(raw.read_bytes()))
        self.assertEqual(self.model.generate_count, 1)

    def test_notebook_reviews_fake_bundle_without_auto_pass(self):
        snapshot = {"local_bytes_verified": True, "revision": q.REVISION,
                    "files": q.load_plan()["snapshot_files"]}
        self.verifier.return_value = snapshot
        self.fake_valid_outputs()
        report = self.run_harness()
        self.assertEqual(report["status"], q.COMPLETE)
        ns = {}
        exec(compile(sources()[0], "definitions", "exec"), ns)
        ns.update(REPO=self.repo, BASE="a" * 40, plan=q.load_plan())
        for name in ("provision.json", "verify_online.json", "verify_offline.json"):
            q.write_json(self.repo / ns["MANIFESTS"] / name, snapshot)
        reviewed = ns["review_runtime"](0)
        self.assertEqual(reviewed["status"], q.COMPLETE)
        self.assertEqual(reviewed["paligemma_external_gate_status"], "PENDING_REVIEW")
        self.assertEqual(reviewed["classification_interface_status"], "PENDING_QUALIFICATION")
        path = self.repo / q.ARTIFACTS / q.RUN_ID / "summary.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(RuntimeError, "summary hash mismatch"):
            ns["review_runtime"](0)


class NotebookTests(unittest.TestCase):
    def setUp(self):
        from tempfile import TemporaryDirectory
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ns = {}
        exec(compile(sources()[0], "definitions", "exec"), self.ns)
        self.ns.update(WORKING=self.root, REPO=self.root / "repo",
                       WORK=self.root / "work", SETUP=self.root / "setup",
                       BUNDLE=self.root / "bundle", ZIP=self.root / "bundle.zip",
                       ONLINE_DONE=True)
        self.ns["REPO"].mkdir()
        self.ns["SETUP"].mkdir()
        self.ns["write_new"](self.ns["SETUP"] / "online_complete.json", {"complete": True})

    def test_offline_barrier_and_no_retry_precede_runtime(self):
        from unittest.mock import Mock
        command = Mock()
        self.ns["command"] = command
        with self.assertRaisesRegex(RuntimeError, "turn venue Internet OFF"):
            exec(compile(sources()[2], "offline", "exec"), self.ns)
        command.assert_not_called()
        self.ns["write_new"](self.ns["SETUP"] / "runtime_attempt.json", {"started": True})
        with self.assertRaisesRegex(RuntimeError, "attempt already started"):
            exec(compile(sources()[2].replace("OWNER_ATTEST_INTERNET_OFF = False",
                                             "OWNER_ATTEST_INTERNET_OFF = True"), "offline", "exec"), self.ns)
        command.assert_not_called()

    def test_no_credential_in_offline_process(self):
        with patch.dict(os.environ, HF_TOKEN="FAKE_TEST_SECRET", GH_TOKEN="FAKE_TEST_SECRET",
                        GITHUB_TOKEN="FAKE_TEST_SECRET"):
            env = self.ns["child_env"](offline=True)
        for name in ("HF_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
            self.assertNotIn(name, env)
        self.assertEqual(env["HF_HUB_OFFLINE"], "1")
        self.assertEqual(env["CUDA_VISIBLE_DEVICES"], "0")

    def test_failure_bundle_keeps_partial_raw_exact_and_excludes_weights(self):
        from types import ModuleType
        from unittest.mock import Mock
        import sys
        import zipfile
        runtime = self.ns["REPO"] / self.ns["RUN_REL"]
        raw_dir = runtime / ("a" * 64)
        raw_dir.mkdir(parents=True)
        raw = b'{"partial_native_ids":[256000,1]}'
        (raw_dir / "response.raw").write_bytes(raw)
        (runtime / "A_1.png").write_bytes(b"FAKE_INPUT_BYTES")
        (runtime / "model.safetensors").write_bytes(b"FAKE_EXCLUDED_WEIGHT")
        display = ModuleType("IPython.display")
        display.FileLink = lambda path: path
        display.display = Mock()
        with patch.dict(sys.modules, {"IPython.display": display}):
            self.ns["build_bundle"]({"status": q.STOP})
        with zipfile.ZipFile(self.ns["ZIP"]) as bundle:
            prefix = "d9r13_result_bundle/"
            self.assertEqual(bundle.read(prefix + "runtime/" + "a" * 64 + "/response.raw"), raw)
            self.assertIn(prefix + "runtime/A_1.png", bundle.namelist())
            self.assertFalse(any("safetensors" in n for n in bundle.namelist()))
            inventory = json.loads(bundle.read(prefix + "checksums.json"))
            for path, ref in inventory.items():
                content = bundle.read(prefix + path)
                self.assertEqual(hashlib.sha256(content).hexdigest(), ref["sha256"])
                self.assertEqual(len(content), ref["size_bytes"])
        with self.assertRaisesRegex(RuntimeError, "bundle already exists"):
            self.ns["build_bundle"]({"status": q.STOP})

    def test_secret_export_refused_without_raw_rewrite(self):
        raw_dir = self.ns["REPO"] / self.ns["RUN_REL"] / ("a" * 64)
        raw_dir.mkdir(parents=True)
        secret = "FAKE_MEMORY_ONLY_SECRET"
        self.ns["SECRET_VALUES"].append(secret)
        raw_path = raw_dir / "response.raw"
        raw_path.write_bytes(secret.encode())
        with self.assertRaisesRegex(RuntimeError, "secret-like content"):
            self.ns["build_bundle"]({"status": q.STOP})
        self.assertEqual(raw_path.read_bytes(), secret.encode())
        self.assertFalse(self.ns["ZIP"].exists())



if __name__ == "__main__":
    unittest.main()
