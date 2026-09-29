"""D9R13 CPU/fake-only compatibility checks; no real model/GPU/gate execution."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

from safeshift.protocol.prompts import classification_request, grounding_request
from safeshift.protocol.schema import SAFETY_LEVELS, parse_text
from safeshift.runners.contracts import ParseStatus, Task
from safeshift.runners.paligemma_compatibility import adapt_persisted, observation
from safeshift.runners.paligemma_snapshot import json_bytes
from scripts import w2_paligemma_canonical_compatibility as q
from tests import test_paligemma_prep as fakes

NOTEBOOK = q.ROOT / "notebooks/w2_paligemma_d9r13_canonical_compatibility_kaggle.ipynb"


def native(text, ids=None, special=None):
    return json_bytes({"schema_version": "paligemma-native-output-v1",
        "model_id": q.MODEL_ID, "revision": q.REVISION, "decoding": q.DECODING,
        "continuation_ids": [42, 1] if ids is None else ids,
        "decoded_text": text, "decoded_with_special_tokens": text + "<eos>" if special is None else special})


def loc(label="SMOKE", values=(0, 1, 1023, 1022)):
    text = "".join(f"<loc{v:04d}>" for v in values) + " " + label + "<eos>"
    return native(" " + label, [256000 + v for v in values] + [1], text)


def sources():
    return ["".join(c["source"]) for c in json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]
            if c["cell_type"] == "code"]


class AdapterTests(unittest.TestCase):
    def test_serialized_canonical_output_round_trips_without_null_label(self):
        for raw, task in ((loc(), Task.GROUNDING),
                          (native('{"hazards":[]}'), Task.GROUNDING),
                          (native('{"safety_level":"Level01"}'), Task.CLASSIFICATION)):
            result = observation(raw, task)
            canonical = json.dumps(result["canonical_output"])
            self.assertTrue(parse_text(canonical, task.value).success)
            self.assertNotIn('"label": null', canonical)

    def test_four_exact_levels_and_reject_repair(self):
        for level in SAFETY_LEVELS:
            value = adapt_persisted(native(json.dumps({"safety_level": level})), Task.CLASSIFICATION)
            self.assertEqual(asdict(value.value), {"safety_level": level})
        for text in ('yes', 'no', 'Level01', '{"safety_level":"level01"}',
                     '{"safety_level":"Level01","hazards":[]}', '{"safety_level":1}',
                     '{"safety_level":"Level01","safety_level":"Level02"}',
                     '```json\n{"safety_level":"Level01"}\n```'):
            self.assertIsNone(adapt_persisted(native(text), Task.CLASSIFICATION).value)

    def test_two_d6_labels_native_axes_and_1024(self):
        for label in ("SMOKE", "OPEN_FLAME"):
            result = adapt_persisted(loc(label), Task.GROUNDING)
            self.assertEqual(result.parse_status, ParseStatus.SUCCESS)
            self.assertEqual(result.value.hazards[0].hazard_type, label)
            self.assertEqual(result.value.hazards[0].evidence[0].bbox,
                             (1/1024, 0, 1022/1024, 1023/1024))
        for label in ("red square", "smoke", "Fire", "SMOKE ", "SMOKE extra"):
            self.assertIsNone(adapt_persisted(loc(label), Task.GROUNDING).value)

    def test_invalid_geometry_and_tokens_never_repaired(self):
        for coords in ((1, 0, 0, 100), (0, 0, 1024, 1023), (0, 0, 0, 20)):
            self.assertIsNone(adapt_persisted(loc(values=coords), Task.GROUNDING).value)
        envelope = json.loads(loc())
        envelope["continuation_ids"][0] += 1
        self.assertIsNone(adapt_persisted(json_bytes(envelope), Task.GROUNDING).value)
        for ids in ([42], [1, 42, 1], [True, 1], [42] * 33 + [1]):
            self.assertIsNone(adapt_persisted(native('{"hazards":[]}', ids), Task.GROUNDING).value)

    def test_json_bounds_precheck_prevents_canonical_clamp(self):
        for box in ([-.1, 0, .8, .9], [0, 0, 1.1, .9], [False, 0, .8, .9],
                    [0, 0, .8, float("nan")], [.8, 0, .2, .9]):
            text = json.dumps({"hazards": [{"hazard_type": "SMOKE", "evidence": [{"bbox": box}]}]})
            self.assertIsNone(adapt_persisted(native(text), Task.GROUNDING).value)
        text = '{"hazards":[{"hazard_type":"SMOKE","evidence":[{"bbox":[0,0,1,1]}]}]}'
        self.assertEqual(adapt_persisted(native(text), Task.GROUNDING).value.hazards[0].hazard_type, "SMOKE")

    def test_negative_retains_hallucination_and_only_explicit_empty_is_empty(self):
        self.assertEqual(adapt_persisted(native('{"hazards":[]}'), Task.GROUNDING).value.hazards, ())
        self.assertEqual(adapt_persisted(loc(), Task.GROUNDING).value.hazards[0].hazard_type, "SMOKE")
        for text in ("", "none", "no hazards", "[]"):
            self.assertIsNone(adapt_persisted(native(text), Task.GROUNDING).value)
        # Special-token deletion must not turn a spatial response into classification JSON.
        self.assertIsNone(adapt_persisted(native('{"safety_level":"Level01"}',
            [256000, 1], '{"safety_level":"Level01"}<loc0000><eos>'), Task.CLASSIFICATION).value)

    def test_wrong_model_duplicate_or_incomplete_envelope(self):
        for raw in (b'{}', b'[]', b'null', b'not json'):
            self.assertIsNone(adapt_persisted(raw, Task.GROUNDING).value)
        obj = json.loads(loc())
        obj["revision"] = "main"
        self.assertIsNone(adapt_persisted(json_bytes(obj), Task.GROUNDING).value)


class PlanTests(unittest.TestCase):
    def test_exact_notebook_execution_source_pin(self):
        import ast
        tree = ast.parse(sources()[0])
        pin = next(ast.literal_eval(n.value) for n in tree.body
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "BASE"
                                                       for t in n.targets))
        self.assertEqual(pin, "ea8d60bd89463015ebcd427ac931c2d48ad4042e")
        subprocess.run(["git", "merge-base", "--is-ancestor", q.BASE_SHA, pin],
                       cwd=q.ROOT, check=True, capture_output=True)
        for path in (q.PLAN, "scripts/w2_paligemma_canonical_compatibility.py",
                     "scripts/w2_paligemma_interface_qualification.py",
                     "safeshift/runners/paligemma_compatibility.py",
                     "safeshift/protocol/prompts.py", "safeshift/protocol/schema.py",
                     "safeshift/runners/paligemma.py", "safeshift/runners/paligemma_snapshot.py",
                     "safeshift/runners/storage.py", "requirements-paligemma-t4.txt"):
            committed = subprocess.check_output(["git", "show", pin + ":" + path], cwd=q.ROOT)
            self.assertEqual(committed.replace(b"\r\n", b"\n"),
                             (q.ROOT / path).read_bytes().replace(b"\r\n", b"\n"), path)

    def test_exact_budget_and_missing_inputs_are_honest(self):
        p = q.qualification_plan()
        self.assertEqual((p["classification_calls"], p["grounding_calls"],
                          p["total_calls"], p["model_loads"]), (4, 3, 7, 1))
        self.assertFalse(p["multiple_hazard_required"])
        self.assertTrue(p["no_hazard_included"])
        self.assertIsNone(p["industry_safety_policy"])
        self.assertTrue(all(c["image_path"] is None for c in p["cases"]))
        with self.assertRaisesRegex(ValueError, "APPROVED_PRODUCTION_POLICY"):
            q.prepared_cases(p)
        self.assertFalse(p["synthetic_gate_ready"])
        self.assertFalse(any(p["execution"].values()))

    def test_frozen_sources_and_gate_unchanged(self):
        roots = ["safeshift", "schemas", "configs/pre_freeze",
                 "tests/fixtures/pre_freeze/frozen_external_gate",
                 "scripts/w2_paligemma_interface_qualification.py",
                 "notebooks/w2_paligemma_d9r11_interface_qualification_kaggle.ipynb",
                 "scripts/generate_external_gate_cases.py"]
        paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", q.BASE_SHA,
                                         "--", *roots], cwd=q.ROOT, text=True).splitlines()
        for path in paths:
            original = subprocess.check_output(["git", "show", f"{q.BASE_SHA}:{path}"], cwd=q.ROOT)
            current = (q.ROOT / path).read_bytes()
            if not path.endswith(".png"):
                original, current = original.replace(b"\r\n", b"\n"), current.replace(b"\r\n", b"\n")
            self.assertEqual(current, original, path)

    def test_notebook_unexecuted_compiles_and_stops_before_provision(self):
        nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        for c in nb["cells"]:
            if c["cell_type"] == "code":
                self.assertIsNone(c["execution_count"])
                self.assertEqual(c["outputs"], [])
                compile("".join(c["source"]), "notebook", "exec")
        setup = sources()[1]
        self.assertLess(setup.index('"validate_inputs"'), setup.index('"SOFTWARE_INSTALL"'))
        self.assertLess(setup.index('"validate_inputs"'), setup.index('"PROVISION"'))
        self.assertIn('provision_env["HF_TOKEN"] = hf_token', setup)
        code = "\n".join(sources())
        self.assertNotIn("model.generate", code)
        self.assertNotIn("from_pretrained", code)
        self.assertIn(q.PLAN_SHA256, code)
        self.assertIn('summary["native_generate_calls"] == 7', code)
        self.assertIn('OWNER_ATTEST_INTERNET_OFF = False', code)


class HarnessTests(unittest.TestCase):
    def setUp(self):
        fakes.RunnerTests.setUp(self)
        for name in (q.PLAN, "scripts/w2_paligemma_canonical_compatibility.py",
                     "scripts/w2_paligemma_interface_qualification.py",
                     "safeshift/protocol/prompts.py", "safeshift/protocol/schema.py",
                     "safeshift/runners/paligemma_compatibility.py"):
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
        self.plan = deepcopy(q.qualification_plan())
        # TEMPORARY TEST INPUTS ONLY. Not canonical runtime fixtures or research labels.
        policy = b"CPU UNIT TEST MARKER; NOT A PRODUCTION POLICY"
        (self.repo / "policy.txt").write_bytes(policy)
        self.plan["industry_safety_policy"] = {"path": "policy.txt",
            "sha256": hashlib.sha256(policy).hexdigest(), "source": "UNIT_TEST_ONLY"}
        from PIL import Image
        for i, case in enumerate(self.plan["cases"]):
            stream = BytesIO()
            Image.new("RGB", (4, 4), (i * 30, 10, 20)).save(stream, format="PNG")
            raw = stream.getvalue()
            case.update(image_path=f"case_{i}.png", image_sha256=hashlib.sha256(raw).hexdigest(),
                        source="UNIT_TEST_ONLY", approval_reference="FAKE_TEST_ONLY")
            (self.repo / case["image_path"]).write_bytes(raw)
        self.stack.enter_context(patch.object(q, "qualification_plan", return_value=self.plan))

    def run_harness(self):
        return q.run_qualification(expected_commit="a" * 40, venue_internet_off=True, repo=self.repo,
                                   runner_factory=lambda **_: self.runner, torch_module=self.torch)

    def test_seven_calls_one_load_exact_builders_and_raw_before_parser(self):
        events = []
        original_fsync, original_read, original_observe = os.fsync, Path.read_bytes, q.observation
        def sync(fd):
            events.append("fsync")
            return original_fsync(fd)
        def read(path):
            raw = original_read(path)
            if path.name == "response.raw":
                events.append("reread")
            return raw
        def observe(raw, task):
            self.assertEqual(events[-3:], ["fsync", "fsync", "reread"])
            events.append("parse")
            return original_observe(raw, task)
        with patch.object(os, "fsync", side_effect=sync), patch.object(Path, "read_bytes", read), \
                patch.object(q, "observation", side_effect=observe):
            result = self.run_harness()
        self.assertEqual(result["status"], q.COMPLETE)
        self.assertEqual((result["model_load_count"], result["native_generate_calls"]), (1, 7))
        requests = q.prepared_cases(self.plan, self.repo)
        self.assertEqual(self.processor.prompts, [r.prompt for r, _ in requests])
        self.assertEqual(events.count("parse"), 7)
        self.assertEqual(len({id(i) for i in self.processor.prepared}), 7)
        self.assertEqual(len({c["raw"]["path"] for c in result["calls"]}), 7)
        self.assertFalse(result["compatibility_review"]["CLASSIFICATION_COMPATIBLE"]["all_cases_map_fail_closed"])
        with self.assertRaises(FileExistsError):
            self.run_harness()
        self.assertEqual(self.model.generate_count, 7)

    def test_builders_get_no_expected_labels_or_previous_outputs(self):
        requests = q.prepared_cases(self.plan, self.repo)
        for i, (r, _) in enumerate(requests):
            expected = (classification_request(self.repo, r.input_id, (self.repo / "policy.txt").read_text())
                        if i < 4 else grounding_request(self.repo, r.input_id))
            self.assertEqual(r.prompt, expected.prompt)
        self.assertEqual(len({r.prompt for r, _ in requests[4:]}), 1)

    def test_notebook_reviews_complete_fake_evidence_without_model_pass(self):
        snapshot = {"local_bytes_verified": True, "revision": q.REVISION,
                    "files": q.load_plan()["snapshot_files"]}
        self.verifier.return_value = snapshot
        report = self.run_harness()
        self.assertEqual(report["status"], q.COMPLETE)
        ns = {}
        exec(compile(sources()[0], "definitions", "exec"), ns)
        ns.update(REPO=self.repo, BASE="a" * 40, plan=q.load_plan())
        for name in ("provision.json", "verify_online.json", "verify_offline.json"):
            q.write_json(self.repo / ns["MANIFESTS"] / name, snapshot)
        reviewed = ns["review_runtime"](0)
        self.assertEqual(reviewed["status"], q.COMPLETE)
        self.assertEqual(reviewed["classification_interface_status"], "PENDING_QUALIFICATION")
        self.assertEqual(reviewed["grounding_status"], "PENDING_QUALIFICATION")
        self.assertFalse(reviewed["compatibility_review"]["GROUNDING_COMPATIBLE"]["all_cases_map_fail_closed"])
        path = self.repo / q.ARTIFACTS / q.RUN_ID / "summary.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(RuntimeError, "summary hash mismatch"):
            ns["review_runtime"](0)

    def test_missing_inputs_stop_before_backend_or_load(self):
        self.plan["industry_safety_policy"] = None
        with patch.object(q, "probe_hardware") as probe:
            result = self.run_harness()
        self.assertEqual(result["status"], q.STOP)
        self.assertEqual(result["failure"]["stage"], "APPROVED_CANONICAL_INPUTS")
        self.assertEqual(result["native_generate_calls"], 0)
        self.assertEqual(result["model_load_count"], 0)
        probe.assert_not_called()

    def test_input_hash_or_firewall_failure(self):
        self.plan["cases"][0]["image_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
            q.prepared_cases(self.plan, self.repo)
        self.plan["cases"][0]["image_path"] = "data/raw/forbidden.png"
        with self.assertRaises(ValueError):
            q.prepared_cases(self.plan, self.repo)

    def test_corrupt_reread_stops_no_parser_no_retry(self):
        original = Path.read_bytes
        def read(path):
            raw = original(path)
            return raw + b" " if path.name == "response.raw" else raw
        with patch.object(Path, "read_bytes", read), patch.object(q, "observation") as observer:
            result = self.run_harness()
        self.assertEqual(result["status"], q.STOP)
        observer.assert_not_called()
        self.assertEqual(self.model.generate_count, 1)

    def test_fsync_failure_stops_before_parser(self):
        from safeshift.runners import storage
        original = storage._write_new
        def write(path, raw):
            if path.name == "response.raw":
                with patch.object(storage.os, "fsync", side_effect=OSError("FAKE")):
                    return original(path, raw)
            return original(path, raw)
        with patch.object(storage, "_write_new", side_effect=write), patch.object(q, "observation") as parser:
            result = self.run_harness()
        self.assertEqual(result["status"], q.STOP)
        parser.assert_not_called()
        self.assertEqual(self.model.generate_count, 1)

    def test_partial_failure_preserves_ids(self):
        self.processor.decode_error = ValueError("FAKE")
        with patch.object(q, "observation") as parser:
            result = self.run_harness()
        self.assertEqual(result["status"], q.STOP)
        parser.assert_not_called()
        raw = next((self.repo / q.ARTIFACTS).rglob("response.raw"))
        self.assertIn("generated_ids_full", json.loads(raw.read_bytes()))
        self.assertEqual(self.model.generate_count, 1)


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
        (runtime / "C_LEVEL01.input").write_bytes(b"FAKE_INPUT_BYTES")
        (runtime / "model.safetensors").write_bytes(b"FAKE_EXCLUDED_WEIGHT")
        display = ModuleType("IPython.display")
        display.FileLink = lambda path: path
        display.display = Mock()
        with patch.dict(sys.modules, {"IPython.display": display}):
            self.ns["build_bundle"]({"status": q.STOP})
        with zipfile.ZipFile(self.ns["ZIP"]) as bundle:
            prefix = "d9r13_result_bundle/"
            self.assertEqual(bundle.read(prefix + "runtime/" + "a" * 64 + "/response.raw"), raw)
            self.assertIn(prefix + "runtime/C_LEVEL01.input", bundle.namelist())
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
