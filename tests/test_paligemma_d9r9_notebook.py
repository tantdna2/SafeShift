"""Offline notebook contract and orchestration checks; no GPU, Hub or dataset."""

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/w2_paligemma_d9r9_kaggle.ipynb"
BASE = "180c0623149bbc7d64f5b659f6c044c39b1e1cd0"


def notebook():
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def sources():
    return ["".join(c["source"]) for c in notebook()["cells"] if c["cell_type"] == "code"]


class NotebookContractTests(unittest.TestCase):
    def test_unexecuted_notebook_structure_and_all_embedded_python_compile(self):
        nb = notebook()
        self.assertEqual((nb["nbformat"], nb["nbformat_minor"]), (4, 5))
        self.assertEqual(len({c["id"] for c in nb["cells"]}), len(nb["cells"]))
        for cell in nb["cells"]:
            if cell["cell_type"] == "code":
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])
                compile("".join(cell["source"]), cell["id"], "exec")
        for code in sources():
            for node in ast.walk(ast.parse(code)):
                if isinstance(node, ast.Assign):
                    if any(isinstance(t, ast.Name) and t.id in {"OBSERVER", "probe"} for t in node.targets):
                        compile(ast.literal_eval(node.value), "embedded", "exec")

    def test_immutable_pins_mask_cli_and_phase_order(self):
        definitions, online, runtime = sources()
        self.assertIn(BASE, definitions)
        plan = json.loads((ROOT / "configs/pre_freeze/paligemma_t4_runtime.v1.json").read_text())
        self.assertIn(plan["model_id"], definitions)
        self.assertIn(plan["model_revision"], definitions)
        self.assertIn('os.environ["CUDA_VISIBLE_DEVICES"] = "0"', definitions)
        self.assertIn('os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"', definitions)
        for tree in map(ast.parse, sources()):
            imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
            self.assertFalse(any(getattr(n, "module", "") in {"torch", "transformers"} for n in imports))
            self.assertFalse(any(a.name in {"torch", "transformers"} for n in imports
                                 for a in getattr(n, "names", [])))
        self.assertLess(online.index('"install_pins"'), online.index('"--provision"'))
        self.assertLess(online.index('"--provision"'), online.index('"--verify-only"'))
        self.assertIn('"--untracked-files=all"', definitions)
        self.assertIn('"--detach", BASE', online)
        self.assertIn('"OWNER_ATTEST_INTERNET_OFF', json.dumps(runtime))
        self.assertLess(runtime.index('OWNER_ATTEST_INTERNET_OFF is True'), runtime.index('"REAL_SMOKE"'))
        self.assertNotIn('"--provision"', runtime)
        self.assertIn('"--expected-commit", BASE', runtime)
        self.assertIn('"--venue-internet-off"', runtime)
        self.assertIn('"scripts/provision_paligemma_snapshot.py"', online)
        self.assertNotIn('"scripts/w2_paligemma_t4_smoke.py"', online)
        self.assertIn('runpy.run_path', runtime)

    def test_no_model_logic_gate_or_embedded_credentials(self):
        content = NOTEBOOK.read_text(encoding="utf-8")
        self.assertNotRegex(content, r"\b(?:hf_|ghp_|gho_|github_pat_)[A-Za-z0-9]{16,}")
        for bad in ("snapshot_download(", "from_pretrained(", "model.generate(",
                    "device_map=", "--synthetic", "external_gate.py", "getpass("):
            self.assertNotIn(bad, content)
        self.assertNotIn('"exact_runtime_verified": true', content.lower())
        self.assertIn('secret(\\"HF_TOKEN\\")', content)


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env_patch = patch.dict(os.environ)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.ns = {}
        exec(compile(sources()[0], "notebook_definitions", "exec"), self.ns)
        working = Path(self.tmp.name).resolve()
        self.ns.update(WORKING=working, WORK=working / "work", REPO=working / "work/repo",
                       SETUP=working / "work/evidence", ENV=working / "work/env",
                       PYTHON=working / "work/env/bin/python", BUNDLE=working / "d9r9_result_bundle",
                       ZIP=working / "d9r9_result_bundle.zip")
        display = ModuleType("IPython.display")
        display.FileLink = lambda path: path
        display.display = Mock()
        modules = patch.dict(sys.modules, {"IPython.display": display})
        modules.start()
        self.addCleanup(modules.stop)

    def prepare(self):
        self.ns["SETUP"].mkdir(parents=True)
        self.ns["REPO"].mkdir()

    def test_runtime_attestation_is_hard_barrier(self):
        self.prepare()
        self.ns["command"] = Mock(side_effect=AssertionError("must not execute"))
        with self.assertRaisesRegex(RuntimeError, "turn venue Internet OFF"):
            exec(sources()[2], self.ns)
        self.ns["command"].assert_not_called()
        self.assertFalse((self.ns["SETUP"] / "runtime_attempt.json").exists())

    def test_runtime_attempt_cannot_be_retried(self):
        self.prepare()
        self.ns["ONLINE_DONE"] = True
        for name in ("online_complete.json", "runtime_attempt.json"):
            (self.ns["SETUP"] / name).write_text("{}")
        self.ns["command"] = Mock(side_effect=AssertionError("must not execute"))
        code = sources()[2].replace("OWNER_ATTEST_INTERNET_OFF = False", "OWNER_ATTEST_INTERNET_OFF = True", 1)
        with self.assertRaisesRegex(RuntimeError, "no retry"):
            exec(code, self.ns)
        self.ns["command"].assert_not_called()

    def test_missing_secret_stops_without_provider_exception(self):
        module = ModuleType("kaggle_secrets")
        module.UserSecretsClient = Mock(side_effect=ValueError("credential-provider-details"))
        with patch.dict(sys.modules, {"kaggle_secrets": module}):
            with self.assertRaisesRegex(RuntimeError, "^Create a Kaggle Secret named HF_TOKEN and rerun.$"):
                self.ns["secret"]("HF_TOKEN")
        self.assertEqual(self.ns["SECRET_VALUES"], [])

    def test_runtime_environment_does_not_inherit_secrets_or_python_config(self):
        with patch.dict(os.environ, {"HF_TOKEN": "private-value", "GITHUB_TOKEN": "private-value",
                                    "PYTHONPATH": "bad-path", "HTTPS_PROXY": "private-value"}):
            env = self.ns["child_env"](offline=True)
        for key in ("HF_TOKEN", "GITHUB_TOKEN", "PYTHONPATH", "HTTPS_PROXY"):
            self.assertNotIn(key, env)
        for key, value in self.ns["OFFLINE"].items():
            self.assertEqual(env[key], value)
        self.assertEqual(env["CUDA_VISIBLE_DEVICES"], "0")

    def test_command_redacts_before_log_and_raises_on_failure(self):
        self.prepare()
        self.ns["SECRET_VALUES"].append("unit-test-secret")
        result = SimpleNamespace(returncode=1, stdout="unit-test-secret Authorization: Bearer hidden")
        with patch.object(subprocess, "run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "STOP: failing"):
                self.ns["command"](["fake"], "failing")
        log = (self.ns["SETUP"] / "failing.log").read_text()
        self.assertNotIn("unit-test-secret", log)
        self.assertNotIn("hidden", log)
        self.assertIn("[REDACTED]", log)

    def test_bundle_allowlist_preserves_raw_and_excludes_weight_and_cache(self):
        self.prepare()
        root = self.ns["REPO"] / self.ns["RUN_REL"]
        raw_dir = root / ("a" * 64)
        raw_dir.mkdir(parents=True)
        raw = b'{"decoded_text":"blue"}'
        (raw_dir / "response.raw").write_bytes(raw)
        (raw_dir / "model.safetensors").write_bytes(b"must not export")
        (root / "token.txt").write_bytes(b"must not export")
        cache = self.ns["REPO"] / self.ns["CACHE"]
        cache.mkdir(parents=True)
        (cache / "config.json").write_text("{}")
        self.ns["build_bundle"](self.ns["boundaries"]())
        with zipfile.ZipFile(self.ns["ZIP"]) as archive:
            names = archive.namelist()
            self.assertFalse(any("safetensors" in n or "token.txt" in n or "cache" in n for n in names))
            raw_name = "d9r9_result_bundle/runtime/" + "a" * 64 + "/response.raw"
            self.assertEqual(archive.read(raw_name), raw)
            checksums = json.loads(archive.read("d9r9_result_bundle/checksums.json"))
            for name, ref in checksums.items():
                data = archive.read("d9r9_result_bundle/" + name)
                self.assertEqual(hashlib.sha256(data).hexdigest(), ref["sha256"])
                self.assertEqual(len(data), ref["size_bytes"])

    def test_bundle_refuses_secret_in_raw_without_rewriting_it(self):
        self.prepare()
        root = self.ns["REPO"] / self.ns["RUN_REL"] / ("b" * 64)
        root.mkdir(parents=True)
        raw = b'{"decoded_text":"unit-test-secret"}'
        (root / "response.raw").write_bytes(raw)
        self.ns["SECRET_VALUES"].append("unit-test-secret")
        with self.assertRaisesRegex(RuntimeError, "export refused"):
            self.ns["build_bundle"]({})
        self.assertEqual((root / "response.raw").read_bytes(), raw)
        self.assertFalse(self.ns["ZIP"].exists())

    def test_evidence_path_traversal_and_size_rejected(self):
        self.prepare()
        for relative in ("../outside.json", "/outside.json", "C:/outside.json", "..\\outside"):
            with self.subTest(relative=relative), self.assertRaisesRegex(RuntimeError, "unsafe"):
                self.ns["checked_file"](self.ns["SETUP"], relative)
        path = self.ns["SETUP"] / "large.json"
        path.write_bytes(b"012345")
        self.ns["MAX_FILE"] = 5
        with self.assertRaisesRegex(RuntimeError, "oversized"):
            self.ns["checked_file"](self.ns["SETUP"], path.name)

    def test_checkout_rejects_untracked_file(self):
        self.prepare()
        with patch.object(subprocess, "check_output", side_effect=[BASE + "\n", "?? untracked\n"]):
            with self.assertRaisesRegex(RuntimeError, "clean execution checkout"):
                self.ns["clean_checkout"]()

    def test_online_fake_sequence_and_install_failure_no_provision(self):
        # Run the real cell twice in independent test cases via subTest state reset.
        for fail_install in (False, True):
            with self.subTest(fail_install=fail_install), TemporaryDirectory() as directory:
                work = Path(directory).resolve()
                self.ns.update(WORKING=work, WORK=work / "work", SETUP=work / "work/evidence",
                               REPO=work / "work/repo", BUNDLE=work / "bundle", ZIP=work / "bundle.zip")
                self.ns["ONLINE_DONE"] = False
                labels = []
                self.ns["secret"] = lambda name, **kw: "fake-secret"
                self.ns["clean_checkout"] = Mock()

                def fake_command(args, label, **kwargs):
                    labels.append(label)
                    if label == "physical_gpu":
                        return 0, "0, Tesla T4, 15360, 7.5, fake\n1, Tesla T4, 15360, 7.5, fake\n"
                    if label == "clone":
                        self.ns["REPO"].mkdir()
                        target = self.ns["REPO"] / "configs/pre_freeze"
                        target.mkdir(parents=True)
                        (target / "paligemma_t4_runtime.v1.json").write_bytes(
                            (ROOT / "configs/pre_freeze/paligemma_t4_runtime.v1.json").read_bytes())
                        (self.ns["REPO"] / "requirements-paligemma-t4.txt").write_bytes(
                            (ROOT / "requirements-paligemma-t4.txt").read_bytes())
                    if label == "install_pins" and fail_install:
                        raise RuntimeError("STOP_AND_RESEARCH_LEAD_REVIEW_REQUIRED: fake conflict")
                    if label == "process_probe":
                        return 0, '{"software":{},"hardware":{"visible_gpu_count":1}}'
                    if label == "provision":
                        self.assertEqual(kwargs["env"]["HF_TOKEN"], "fake-secret")
                    if label == "verify_online":
                        target = self.ns["REPO"] / self.ns["MANIFESTS"]
                        target.mkdir(parents=True)
                        (target / "verify_online.json").write_text(json.dumps({
                            "local_bytes_verified": True, "files": [{}] * 14,
                            "revision": self.ns["REVISION"]}))
                    return 0, ""

                self.ns["command"] = fake_command
                with patch("platform.system", return_value="Linux"), patch("platform.machine", return_value="x86_64"):
                    if fail_install:
                        with self.assertRaisesRegex(RuntimeError, "fake conflict"):
                            exec(sources()[1], self.ns)
                        self.assertNotIn("provision", labels)
                        self.assertFalse(self.ns["ONLINE_DONE"])
                    else:
                        exec(sources()[1], self.ns)
                        self.assertEqual(labels[-2:], ["provision", "verify_online"])
                        self.assertTrue(self.ns["ONLINE_DONE"])
                        self.assertNotIn("smoke", labels)

    def fake_runtime_artifacts(self, corrupt=False, failed=False):
        ns = self.ns
        root = ns["REPO"] / ns["RUN_REL"]
        root.mkdir(parents=True)
        def put(name, value):
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(value), encoding="utf-8")
        calls = []
        for index in (1, 2):
            call_id = "case_0" + str(index)
            relative = str(index) * 64 + "/response.raw"
            put(relative, {"generated_ids_full": [[1, index]], "continuation_ids": [index],
                           "decoded_text": "blue" if index == 1 else "green",
                           "decoded_with_special_tokens": "blue</s>" if index == 1 else "green</s>"})
            raw = (root / relative).read_bytes()
            ref = {"path": ns["RUN_REL"] + "/" + relative,
                   "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
            put(str(index) * 64 + "/metadata.json", {"parse_status": "NOT_ATTEMPTED",
                "call_id": call_id, "git_commit_sha": BASE})
            calls.append({"case_id": call_id, "raw": ref, "parse_status": "INVALID", "error": None})
        put("run_metadata.json", {"git_commit": BASE, "venue_internet_off_owner_attested": True})
        put("environment.json", {"software": ns["plan"]["software"], "offline_variables": ns["OFFLINE"],
            "hardware": {"visible_gpu_count": 1, "gpu_name": "Tesla T4", "compute_capability": [7, 5],
                         "total_vram_bytes": 15 * 2**30, "cuda_runtime": "12.4", "device": "cuda:0"}})
        put("snapshot_manifest.json", {"local_bytes_verified": True, "files": [{}] * 14})
        summary = {"status": "RUNTIME_INTERFACE_FAILURE" if failed else "RUNTIME_INTERFACE_PASS",
                   "calls": calls, "model_load_count": 1, "native_generate_calls": 2,
                   "memory": {"after_load": {"peak_allocated_bytes": 100, "peak_reserved_bytes": 200}},
                   "artifacts": {}}
        for path in root.rglob("*"):
            if path.is_file():
                raw = path.read_bytes()
                summary["artifacts"][path.relative_to(root).as_posix()] = {
                    "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
        put("summary.json", summary)
        put("summary.sha256.json", {"sha256": hashlib.sha256((root / "summary.json").read_bytes()).hexdigest()})
        if corrupt:
            (root / ("1" * 64) / "response.raw").write_text("corruption")
        (ns["SETUP"] / "timings.json").write_text(json.dumps({
            "measurements": [{"scope": s, "wall_seconds": 1} for s in
                             ["runner_load_including_snapshot_and_transfer", "native_generate", "native_generate"]],
            "observer_errors": [], "unfinished_spans": 0, "harness_wall_seconds": 4}))

    def test_fake_runtime_export_success_checksum_failure_and_native_failure(self):
        for corrupt, failed in ((False, False), (True, False), (False, True)):
            with self.subTest(corrupt=corrupt, failed=failed), TemporaryDirectory() as directory:
                working = Path(directory).resolve()
                self.ns.update(WORKING=working, WORK=working / "work", REPO=working / "work/repo",
                               SETUP=working / "work/evidence", BUNDLE=working / "bundle",
                               ZIP=working / "bundle.zip", ONLINE_DONE=True)
                self.prepare()
                self.ns["plan"] = json.loads((ROOT / "configs/pre_freeze/paligemma_t4_runtime.v1.json").read_text())
                (self.ns["SETUP"] / "online_complete.json").write_text("{}")
                self.ns["clean_checkout"] = Mock()
                labels = []
                def command(args, label, **kwargs):
                    labels.append(label)
                    self.assertNotIn("HF_TOKEN", kwargs["env"])
                    if label == "smoke":
                        self.fake_runtime_artifacts(corrupt=corrupt, failed=failed)
                        return (1 if failed else 0), ""
                    return 0, ""
                self.ns["command"] = command
                code = sources()[2].replace("OWNER_ATTEST_INTERNET_OFF = False", "OWNER_ATTEST_INTERNET_OFF = True", 1)
                with patch("builtins.print") as output:
                    if corrupt or failed:
                        with self.assertRaisesRegex(RuntimeError, "checksum/size mismatch" if corrupt else "runtime failed"):
                            exec(code, self.ns)
                    else:
                        exec(code, self.ns)
                    completed = any(c.args == ("D9R9_NOTEBOOK_EXECUTION_COMPLETE",) for c in output.call_args_list)
                    self.assertEqual(completed, not (corrupt or failed))
                self.assertEqual(labels, ["verify_offline", "smoke"])
                self.assertTrue(self.ns["ZIP"].exists())
                report = json.loads((self.ns["BUNDLE"] / "review_summary.json").read_text())
                self.assertEqual(report["promotion"], "NO")
                self.assertEqual(report["protocol_freeze"], "BLOCKED")
                self.assertNotIn("exact_runtime_verified", report)

    def test_timing_observer_only_records_target_spans_and_syncs(self):
        tree = ast.parse(sources()[2])
        observer = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "OBSERVER" for t in n.targets))
        function = next(n for n in ast.parse(observer).body if isinstance(n, ast.FunctionDef) and n.name == "observe")
        timer = SimpleNamespace(perf_counter=Mock(side_effect=[10.0, 11.25]))
        sync = Mock()
        scope = {"sys": SimpleNamespace(modules={"torch": SimpleNamespace(cuda=SimpleNamespace(synchronize=sync))}),
                 "time": timer, "active": {}, "measurements": [], "errors": []}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "observer", "exec"), scope)
        frame = SimpleNamespace(f_code=SimpleNamespace(co_filename="/env/transformers/generation/utils.py", co_name="generate"))
        scope["observe"](frame, "call", None)
        scope["observe"](frame, "return", None)
        self.assertEqual(scope["measurements"], [{"scope": "native_generate", "wall_seconds": 1.25}])
        self.assertEqual(sync.call_count, 2)
        self.assertEqual(scope["active"], {})
        frame.f_code.co_filename = "/env/unrelated.py"
        scope["observe"](frame, "call", None)
        self.assertEqual(sync.call_count, 2)


if __name__ == "__main__":
    unittest.main()
