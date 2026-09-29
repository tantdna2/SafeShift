"""Static and fake notebook flow; no install, provisioning, GPU or model calls."""

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch
import zipfile

from scripts import w2_paligemma_interface_qualification as q
from tests import test_paligemma_interface_qualification as harness_tests
from tests import test_paligemma_d9r9_notebook as previous

NOTEBOOK = q.ROOT / "notebooks/w2_paligemma_d9r11_interface_qualification_kaggle.ipynb"
EXECUTION = "ceb56d5174a387362e3ef6a5af3b6618123bc8a7"


def sources():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    return ["".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"]


class StaticTests(unittest.TestCase):
    def test_execution_snapshot_contains_identical_harness_and_plan(self):
        subprocess.run(["git", "merge-base", "--is-ancestor", q.BASE_SHA, EXECUTION],
                       cwd=q.ROOT, check=True, capture_output=True)
        for relative in (q.PLAN, "scripts/w2_paligemma_interface_qualification.py",
                         "safeshift/runners/paligemma.py", "safeshift/runners/paligemma_snapshot.py",
                         "safeshift/runners/storage.py", "requirements-paligemma-t4.txt"):
            committed = subprocess.check_output(["git", "show", EXECUTION + ":" + relative], cwd=q.ROOT)
            local = (q.ROOT / relative).read_bytes()
            self.assertEqual(committed.replace(b"\r\n", b"\n"), local.replace(b"\r\n", b"\n"))
        self.assertIn("/" + q.PLAN + " text eol=lf", (q.ROOT / ".gitattributes").read_text())

    def test_unexecuted_json_and_compilable_code(self):
        notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertEqual(cell["outputs"], [])
                self.assertIsNone(cell["execution_count"])
                compile("".join(cell["source"]), "notebook", "exec")
        self.assertEqual(len(sources()), 3)

    def test_exact_pins_and_no_model_logic_duplication(self):
        code = "\n".join(sources())
        for value in (EXECUTION, q.BASE_SHA, q.PLAN_SHA256, q.MODEL_ID, q.REVISION,
                      "uv==0.8.22", "3.11.11", "PCI_BUS_ID", 'CUDA_VISIBLE_DEVICES="0"',
                      "requirements-paligemma-t4.txt", "--is-ancestor", 'len(plan["snapshot_files"]) == 14'):
            self.assertIn(value, code)
        for value in ("from_pretrained", "model.generate", "synthetic-v1", "external_gate_cases",
                      "w2_paligemma_t4_smoke.py", '"classification_interface_status": "PASS"',
                      '"grounding_status": "PASS"', "classify_timing"):
            self.assertNotIn(value, code)
        offline = sources()[2]
        self.assertEqual(offline.count('"scripts/w2_paligemma_interface_qualification.py"'), 1)
        self.assertLess(offline.index("OWNER_ATTEST_INTERNET_OFF is True"), offline.index('"runtime_attempt.json"'))
        self.assertLess(offline.index('"OFFLINE_VERIFY"'), offline.index('"INTERFACE_EVIDENCE_COLLECTION"'))

    def test_reuse_d9r9_bootstrap_contract(self):
        # Same assertions as the reviewed bootstrap fix, against the new notebook.
        with patch.object(previous, "NOTEBOOK", NOTEBOOK):
            test = previous.NotebookContractTests()
            test.test_public_clone_and_hf_only_secret()
            test.test_plan_digest_and_requirement_pins_unchanged()
        tree = ast.parse(sources()[1])
        commands = {ast.literal_eval(n.args[1]): ast.unparse(n.args[0]) for n in ast.walk(tree)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "command"}
        self.assertIn("'--target', bootstrap, 'uv==0.8.22'", commands["bootstrap_uv"])
        self.assertEqual(commands["python_install"], "[uv, '--no-config', 'python', 'install', '3.11.11']")
        self.assertEqual(commands["bootstrap_uv_version"], "[uv, '--version']")
        self.assertNotIn("ensurepip", "\n".join(sources()))


class FakeFlowTests(unittest.TestCase):
    def setUp(self):
        self.rig = harness_tests.HarnessTests()
        self.rig.setUp()
        self.addCleanup(self.rig.doCleanups)
        self.ns = {}
        exec(compile(sources()[0], "definitions", "exec"), self.ns)
        repo = self.rig.repo
        self.ns.update(WORKING=repo, REPO=repo, WORK=repo / "work", SETUP=repo / "setup",
                       BUNDLE=repo / "d9r11_result_bundle", ZIP=repo / "d9r11_result_bundle.zip",
                       BASE="a" * 40, plan=q.load_plan(), ONLINE_DONE=True)
        self.ns["SETUP"].mkdir()
        self.ns["write_new"](self.ns["SETUP"] / "online_complete.json", {"complete": True})
        self.ns["clean_checkout"] = Mock()
        self.snapshot = {"local_bytes_verified": True, "revision": q.REVISION,
                         "files": q.load_plan()["snapshot_files"]}
        self.rig.verifier.return_value = self.snapshot
        for name in ("provision.json", "verify_online.json"):
            q.write_json(repo / self.ns["MANIFESTS"] / name, self.snapshot)
        display = ModuleType("IPython.display")
        display.FileLink = lambda path: path
        display.display = Mock()
        self.rig.stack.enter_context(patch.dict(sys.modules, {"IPython.display": display}))
        self.commands = []
        def command(args, label, **kwargs):
            self.commands.append((args, label, kwargs))
            self.assertNotIn("HF_TOKEN", kwargs["env"])
            self.assertEqual(kwargs["env"]["CUDA_VISIBLE_DEVICES"], "0")
            if label == "verify_offline":
                q.write_json(repo / self.ns["MANIFESTS"] / "verify_offline.json", self.snapshot)
                return 0, ""
            self.assertEqual(label, "qualification")
            result = self.rig.run_harness()
            run_root = repo / self.ns["RUN_REL"]
            (run_root / "model.safetensors").write_bytes(b"fake excluded weights")
            (run_root / "cache").mkdir()
            (run_root / "cache" / "credentials.json").write_bytes(b"fake excluded credential")
            return (0 if result["status"] == q.COMPLETE else 1), result["status"]
        self.ns["command"] = command

    def offline(self, attested=True):
        code = sources()[2]
        if attested:
            code = code.replace("OWNER_ATTEST_INTERNET_OFF = False", "OWNER_ATTEST_INTERNET_OFF = True")
        exec(compile(code, "offline", "exec"), self.ns)

    def test_barrier_no_runtime_or_attempt(self):
        with self.assertRaisesRegex(RuntimeError, "turn venue Internet OFF"):
            self.offline(False)
        self.assertEqual(self.commands, [])
        self.assertFalse((self.ns["SETUP"] / "runtime_attempt.json").exists())
        self.assertEqual(self.rig.model.generate_count, 0)

    def test_complete_fake_run_exports_exact_raw_no_weights_cache_or_secret(self):
        # Deliberately plant excluded files outside the positive allowlist.
        runtime = self.rig.repo / q.ARTIFACTS
        runtime.mkdir(parents=True)
        (runtime / "model.safetensors").write_bytes(b"fake forbidden weights")
        self.offline()
        self.assertEqual(self.rig.model.generate_count, 8)
        self.assertEqual([entry[1] for entry in self.commands], ["verify_offline", "qualification"])
        with zipfile.ZipFile(self.ns["ZIP"]) as archive:
            names = archive.namelist()
            self.assertEqual(len([n for n in names if n.endswith("response.raw")]), 8)
            self.assertFalse(any("cache" in n or "safetensors" in n for n in names))
            prefix = "d9r11_result_bundle/"
            checksums = json.loads(archive.read(prefix + "checksums.json"))
            for relative, ref in checksums.items():
                raw = archive.read(prefix + relative)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), ref["sha256"])
                self.assertEqual(len(raw), ref["size_bytes"])
            exact_plan = archive.read(prefix + "plan/paligemma_interface_qualification.v1.json")
            self.assertEqual(hashlib.sha256(exact_plan).hexdigest(), q.PLAN_SHA256)
            report = json.loads(archive.read(prefix + "review_summary.json"))
            self.assertEqual(report["status"], q.COMPLETE)
            self.assertEqual(report["classification_interface_status"], "PENDING_QUALIFICATION")
            self.assertEqual(report["grounding_status"], "PENDING_QUALIFICATION")
        with self.assertRaisesRegex(RuntimeError, "attempt already started"):
            self.offline()
        self.assertEqual(self.rig.model.generate_count, 8)

    def test_native_failure_stops_and_exports_partial_bundle(self):
        self.rig.processor.decode_error = ValueError("fake decode failure")
        with self.assertRaisesRegex(RuntimeError, "harness failed"):
            self.offline()
        self.assertEqual(self.rig.model.generate_count, 1)
        with zipfile.ZipFile(self.ns["ZIP"]) as archive:
            self.assertEqual(len([n for n in archive.namelist() if n.endswith("response.raw")]), 1)
            report = json.loads(archive.read("d9r11_result_bundle/review_summary.json"))
            self.assertEqual(report["status"], q.STOP)

    def test_secret_isolation_and_no_rewrite_of_suspected_raw(self):
        fake_secret = "credential-for-fake-test-only"
        self.ns["SECRET_VALUES"].append(fake_secret)
        with patch.dict(os.environ, HF_TOKEN=fake_secret, GITHUB_TOKEN=fake_secret):
            runtime_env = self.ns["child_env"](offline=True)
        self.assertNotIn("HF_TOKEN", runtime_env)
        self.assertNotIn("GITHUB_TOKEN", runtime_env)
        self.assertEqual(self.ns["sanitize"](fake_secret), "[REDACTED]")
        root = self.rig.repo / self.ns["RUN_REL"] / ("a" * 64)
        root.mkdir(parents=True)
        path = root / "response.raw"
        path.write_bytes(fake_secret.encode())
        with self.assertRaisesRegex(RuntimeError, "secret-like content"):
            self.ns["build_bundle"]({"status": q.STOP})
        self.assertEqual(path.read_bytes(), fake_secret.encode())
        self.assertFalse(self.ns["ZIP"].exists())

    def test_bundle_size_and_path_guards(self):
        self.ns["MAX_FILE"] = 1
        with self.assertRaisesRegex(RuntimeError, "oversized"):
            self.ns["checked_file"](self.ns["SETUP"], "online_complete.json")
        for relative in ("../outside", "/absolute", "C:/outside", "bad\\path"):
            with self.assertRaisesRegex(RuntimeError, "unsafe evidence path"):
                self.ns["checked_file"](self.ns["SETUP"], relative)


if __name__ == "__main__":
    unittest.main()
