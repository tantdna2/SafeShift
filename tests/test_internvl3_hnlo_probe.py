"""CPU-only source/release, guarded-order, full-vector and PR #115 integration."""
import ast
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.diagnostics.internvl3_hnlo import bootstrap as boot, contract, capture, driver, resources, worker
from safeshift.diagnostics.internvl3_hnlo import orchestrate as flow
from safeshift.diagnostics.one_click import worker as original_worker
from safeshift.diagnostics.one_click.artifacts import write, sha256
from safeshift.diagnostics.hnlo_capture import Capture, persist_hf
from tests import test_hnlo_one_click as old
from tests.test_hnlo_capture import TOK, CANDIDATES, metadata, output
from tests import test_internvl3_driver as pr115_tests

ROOT = Path(__file__).resolve().parents[1]


def approved():
    value = contract.template()
    value["grant"] = {**old.approved()["grant"], "attempt_id": contract.ATTEMPT_ID,
        "decision_url": "https://github.com/tantdna2/SafeShift/pull/999#synthetic",
        "independent_audit_url": "https://github.com/tantdna2/SafeShift/pull/999#synthetic-audit",
        **{flag: True for flag in contract.FLAGS}}
    return value


def probe_state():
    return {"result": "AWAITING_CPU_REPLAY", "environment": "EXACT_MATCH", "t1": "PASS_28_OF_28",
            "load_calls": 1, "generate_calls": 1, "common_fatal": False,
            "network_observation": {"security_assessment": "PARTIAL", "stop_reason": None}}


class ContractTests(unittest.TestCase):
    def test_null_exact_scope_and_new_attempt(self):
        self.assertEqual(json.loads((ROOT / contract.AUTHORITY).read_bytes()), contract.template())
        self.assertEqual(contract.ORDER, ("internvl3",))
        self.assertEqual(list(contract.scope()["models"]), ["internvl3"])
        self.assertEqual(contract.scope()["models"]["internvl3"]["cuda_visible_devices"], "0")
        self.assertEqual(contract.scope()["input_sha256"], old.scope()["input_sha256"])
        contract.authorize(approved(), old.source())

    def test_old_grants_missing_flags_mapping_and_scope_fail_closed(self):
        variants = [contract.template()]
        for flag in approved()["grant"]:
            value = approved()
            del value["grant"][flag]
            variants.append(value)
        for flag in contract.FLAGS:
            value = approved()
            value["grant"][flag] = False
            variants.append(value)
        for pr in (112, 113, 114, 115):
            for key in ("decision_url", "independent_audit_url"):
                value = approved()
                value["grant"][key] = f"https://github.com/tantdna2/SafeShift/pull/{pr}#old"
                variants.append(value)
        for mutate in (lambda v: v["scope"].update(order=["qwen3"]),
                       lambda v: v["grant"].update(attempt_id="internvl3-driver-check-used"),
                       lambda v: v["grant"].update(source_payload_sha256="f" * 64)):
            value = approved()
            mutate(value)
            variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(PermissionError):
                contract.authorize(value, old.source())


class WorkerTests(unittest.TestCase):
    def run_worker(self, root, events, fail_at=None, value=None):
        write(root / contract.AUTHORITY, value or approved())
        write(root / "source.json", old.source())

        def step(name, result=None):
            def call(*args, **kwargs):
                events.append(name)
                if name == fail_at:
                    raise ValueError("SYNTHETIC_GATE_FAILED")
                return result
            return call

        @contextmanager
        def guard(*args):
            events.append("python_guard")
            try:
                yield
            finally:
                events.append("guard_exit")

        class Drivers:
            def __init__(self, evidence):
                step("driver")()
            def observe(self, stage):
                step("maps_" + stage)()

        fake_torch = SimpleNamespace(cuda=SimpleNamespace(reset_peak_memory_stats=lambda i: None))
        with patch.object(boot, "verify_topology", side_effect=step("source", old.source())), patch.object(
                worker, "deny_inet", side_effect=step("seccomp", {"boundary": contract.BOUNDARY})), patch.object(
                worker, "network_denied", guard), patch.object(worker.Monitor, "checkpoint"), patch.object(
                worker, "check_environment", side_effect=step("clean_env", {})), patch.object(
                worker, "DriverSession", Drivers), patch.object(worker, "environment", side_effect=step("cuda", {})), patch.object(
                worker, "memory", return_value={}), patch.object(worker, "probe", side_effect=step("model_probe")):
            # Inject the synthetic torch only at environment(), after the preimport gate.
            original_environment = worker.environment
            def environment(*args, **kwargs):
                result = original_environment(*args, **kwargs)
                sys.modules["torch"] = fake_torch
                return result
            with patch.object(worker, "environment", side_effect=environment):
                try:
                    return worker.execute("probe", root, root / "probe", root / "source.json", "unused", root)
                finally:
                    sys.modules.pop("torch", None)

    def test_order_and_driver_lifetime_through_guarded_finalization(self):
        events = []
        with tempfile.TemporaryDirectory() as temp:
            row = self.run_worker(Path(temp), events)
        self.assertEqual(events, ["source", "seccomp", "python_guard", "clean_env", "driver", "cuda",
                                  "maps_after_cuda", "model_probe", "maps_final", "guard_exit"])
        self.assertTrue(row["driver_handles_retained_through_finalization"])

    def test_every_early_gate_prevents_model_and_preserves_evidence(self):
        for gate in ("source", "seccomp", "clean_env", "driver", "cuda", "maps_after_cuda"):
            with self.subTest(gate=gate), tempfile.TemporaryDirectory() as temp:
                events, root = [], Path(temp)
                row = self.run_worker(root, events, fail_at=gate)
                self.assertEqual(row["result"], "FAILED")
                self.assertNotIn("model_probe", events)
                self.assertEqual((row["load_calls"], row["generate_calls"]), (0, 0))
                self.assertTrue((root / "probe/result.json").is_file())
                self.assertFalse(row["TECHNICAL_HNLO_VALID"])

    def test_null_authority_prevents_guards_driver_and_cuda(self):
        with tempfile.TemporaryDirectory() as temp:
            events = []
            row = self.run_worker(Path(temp), events, value=contract.template())
            self.assertEqual(events, ["source"])
            self.assertTrue(row["common_fatal"])

    def test_final_library_failure_revokes_technical_result(self):
        with tempfile.TemporaryDirectory() as temp:
            row = self.run_worker(Path(temp), [], fail_at="maps_final")
            self.assertEqual(row["result"], "FAILED")
            self.assertFalse(row["TECHNICAL_HNLO_VALID"])


class PipelineTests(unittest.TestCase):
    def test_weights_only_after_successful_cuda_inspect(self):
        for mode, result, calls in (("inspect", "FAILED", 0), ("inspect", "ENVIRONMENT_VALID", 1), ("probe", "AWAITING_CPU_REPLAY", 0)):
            with self.subTest(mode=mode, result=result), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                ops = flow.Operations(ROOT, root, root, root / "source.json", approved()["grant"])
                ops.pythons["internvl3"] = Path("synthetic-python")
                with patch.object(flow.OriginalOperations, "worker", return_value={"result": result, "common_fatal": False}), patch.object(flow, "invoke") as invoke:
                    ops.worker(mode, "internvl3")
                self.assertEqual(invoke.call_count, calls)
                if calls:
                    self.assertEqual(invoke.call_args.kwargs["env"]["CUDA_VISIBLE_DEVICES"], "")
                    self.assertNotIn("LD_LIBRARY_PATH", invoke.call_args.kwargs["env"])

    def test_prepare_only_builds_software(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ops = flow.Operations(ROOT, root, root, root / "source.json", approved()["grant"])
            with patch.object(flow, "build_environment", return_value=Path("synthetic-python")), patch.object(flow, "invoke") as invoke:
                result = ops.prepare("internvl3")
            self.assertIn("CHECKPOINT_NOT_DOWNLOADED", result["status"])
            invoke.assert_not_called()
            with self.assertRaises(PermissionError):
                ops.prepare("qwen3")

    def execute(self, root, failure=None, session="session"):
        repo, out = root / "repo", root / "out"
        repo.mkdir(exist_ok=True)
        out.mkdir(exist_ok=True)
        if not (repo / contract.AUTHORITY).exists():
            write(repo / contract.AUTHORITY, approved())
        work = out / session
        work.mkdir()
        events = []
        fake = type("CPUFake", (old.FakeOperations,), {"events": events, "failure": failure})
        with redirect_stdout(io.StringIO()):
            result = flow.run(repo, work, out, old.source(), operations_factory=fake)
        return result, events, work, out

    def test_single_model_export_and_same_filesystem_rerun_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result, events, work, out = self.execute(root)
            self.assertEqual(result["result"], "TECHNICAL_VALID")
            self.assertEqual([e for e in events if e[0] == "probe"], [("probe", "internvl3")])
            self.assertFalse(result["HNLO_RESEARCH_VERIFIED"])
            receipt = json.loads((out / "session_sha256.json").read_bytes())
            self.assertEqual(sha256(out / "session.tar.gz"), receipt["sha256"])
            result, events, _, _ = self.execute(root, session="second")
            self.assertEqual(result["result"], "BLOCKED")
            self.assertFalse(events)

    def test_invalid_oom_killed_torn_and_checksum_keep_evidence(self):
        for failure in ("invalid", "oom", "killed", "torn", "checksum"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                result, events, work, out = self.execute(Path(temp), failure)
                self.assertNotEqual(result["result"], "TECHNICAL_VALID")
                self.assertFalse(result["models"][0]["TECHNICAL_HNLO_VALID"])
                self.assertTrue((out / "session.tar.gz").is_file())
                self.assertLessEqual(sum(e[0] == "probe" for e in events), 1)


class CaptureReplayTests(unittest.TestCase):
    def test_official_generation_source_checksum_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audit = {"sources": {}}
            write(root / "configs/pre_freeze/internvl3_source_audit.v1.json", audit)
            source_dir = root / "installed/generation"
            source_dir.mkdir(parents=True)
            (source_dir / "utils.py").write_bytes(b"changed")
            write(root / "configs/diagnostics/internvl3_hnlo_generation_sources.v1.json", {
                "transformers_version": "4.52.4", "files": [{"path": "generation/utils.py", "size_bytes": 7, "sha256": "f" * 64}]})
            with patch.dict(sys.modules, {"transformers": SimpleNamespace(__version__="4.52.4", __file__=str(root / "installed/__init__.py"))}), self.assertRaisesRegex(ValueError, "SOURCE_CHECKSUM"):
                capture.verify_sources(root)

    def fixture(self, root, text=None, mutate=None, max_length=35):
        cap = Capture(root, metadata("internvl3"))
        cap.runtime_t1(TOK)
        cap.write("raw-provenance", {"processors": [], "criterion": "EMPTY_ACTUAL_PROCESSOR_LIST_WITH_PINNED_GREEDY_GENERATION_SOURCE"})
        cap.write("stopping-criteria", {"classes": ["MaxLengthCriteria", "EosTokenCriteria"]})
        cap.write("actual-stopping-details", [
            {"class": "transformers.generation.stopping_criteria.MaxLengthCriteria", "max_length": max_length, "eos_token_id": None},
            {"class": "transformers.generation.stopping_criteria.EosTokenCriteria", "max_length": None, "eos_token_id": [999]}])
        native = output() if text is None else output(text)
        if mutate:
            mutate(native)
        persist_hf(native, [11, 22, 33], CANDIDATES, TOK, cap, {"eos_token_id": 999}, {"do_sample": False})
        cap.journal.seal()
        return cap

    def test_saved_vectors_cpu_replay_and_actual_prerequisites(self):
        with tempfile.TemporaryDirectory() as temp:
            cap = self.fixture(Path(temp))
            result = capture.replay(Path(temp), cap.metadata["run_id"], TOK, probe_state())
            self.assertTrue(result["TECHNICAL_HNLO_VALID"])
            self.assertFalse(result["HNLO_RESEARCH_VERIFIED"])
            for key, value in (("t1", "FAIL"), ("load_calls", 0), ("generate_calls", 2), ("common_fatal", True)):
                state = probe_state()
                state[key] = value
                with self.assertRaisesRegex(ValueError, "PREREQUISITES"):
                    capture.replay(Path(temp), cap.metadata["run_id"], TOK, state)

    def test_raw_and_processed_saved_before_decode_even_when_decode_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            cap = Capture(Path(temp), metadata("internvl3"))
            native = output()
            class FailingTokenizer:
                def decode(self, *args, **kwargs):
                    for kind in ("raw", "processed"):
                        for i in range(len(native.logits)):
                            cap.journal.read(f"{kind}-{i:03d}")
                    raise ValueError("SYNTHETIC_DECODE_FAILURE")
            with self.assertRaisesRegex(ValueError, "DECODE_FAILURE"):
                persist_hf(native, [11, 22, 33], CANDIDATES, FailingTokenizer(), cap, {"eos_token_id": 999}, {})
            self.assertTrue(cap.journal.exists("raw-000"))

    def test_invalid_raw_checksum_or_token_mapping_cannot_become_hnlo(self):
        for kind in ("invalid", "checksum", "mapping"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                cap = self.fixture(root, "invalid response" if kind == "invalid" else None)
                if kind == "invalid":
                    row = capture.replay(root, cap.metadata["run_id"], TOK, probe_state())
                    self.assertFalse(row["TECHNICAL_HNLO_VALID"])
                    self.assertIsNone(row["hnlo"])
                elif kind == "checksum":
                    cap.journal.path("raw-000").write_text("{}")
                    with self.assertRaisesRegex(ValueError, "CHECKSUM"):
                        capture.replay(root, cap.metadata["run_id"], TOK, probe_state())
                else:
                    from tests.test_hnlo_capture import LabelTokenizer
                    with self.assertRaisesRegex(ValueError, "TOKENIZER_T1"):
                        capture.replay(root, cap.metadata["run_id"], LabelTokenizer(), probe_state())

    def test_resource_budget_and_invalid_dimension_fail_before_load(self):
        plan = resources.budget()
        self.assertEqual(plan["scalar_count"], 12_800_000)
        self.assertLess(plan["required_output_free_bytes"], 4 * 2**30)
        for vocab in (0, True, 200001):
            with self.assertRaises(ValueError):
                resources.budget(vocab)
        with patch.object(resources.shutil, "disk_usage", return_value=SimpleNamespace(free=1)), patch.object(
                Path, "read_text", return_value="MemAvailable: 999999999 kB\n"):
            with self.assertRaisesRegex(OSError, "STORAGE_INSUFFICIENT"):
                resources.require_resources(ROOT)

    def test_wrong_effective_stopping_length_cannot_pass_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            cap = self.fixture(Path(temp), max_length=36)
            with self.assertRaisesRegex(ValueError, "STOPPING_SETTINGS"):
                capture.replay(Path(temp), cap.metadata["run_id"], TOK, probe_state())

    def test_effective_stopping_observer_and_single_native_call_limits(self):
        class MaxLengthCriteria:
            max_length = 35
        class EosTokenCriteria:
            eos_token_id = SimpleNamespace(tolist=lambda: [999])
        class Model:
            @classmethod
            def from_pretrained(cls, *args, **kwargs):
                return cls()
            def generate(self):
                self._get_logits_processor()
                self._get_stopping_criteria()
                return "UNCHANGED"
            def _get_logits_processor(self):
                return []
            def _get_stopping_criteria(self):
                return [MaxLengthCriteria(), EosTokenCriteria()]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cap, state = Capture(root, metadata("internvl3")), original_worker.empty("internvl3")
            with patch.dict(sys.modules, {"transformers": SimpleNamespace(InternVLForConditionalGeneration=Model)}), capture.count_native(root / "native", state, cap):
                model = Model.from_pretrained("NO_WEIGHTS")
                self.assertEqual(model.generate(), "UNCHANGED")
                for call in (lambda: Model.from_pretrained("NO_WEIGHTS"), model.generate):
                    with self.assertRaisesRegex(RuntimeError, "SECOND_"):
                        call()
            self.assertEqual((state["load_calls"], state["generate_calls"]), (1, 1))
            details = cap.journal.read("actual-stopping-details")
            self.assertEqual(details[0]["max_length"], 35)
            self.assertEqual(details[1]["eos_token_id"], [999])


class SourceTests(old.SourceTests):
    def setUp(self):
        for name, value in (("boot", boot), ("AUTHORITY", contract.AUTHORITY), ("LOCK", contract.LOCK)):
            replacement = patch.object(old, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        super().setUp()


class NotebookTests(unittest.TestCase):
    def test_actual_single_cell_run_all_with_cpu_operations(self):
        notebook = json.loads((ROOT / contract.NOTEBOOK).read_bytes())
        tree = ast.parse("".join(notebook["cells"][1]["source"]))
        namespace = {"__name__": "__notebook__"}
        exec(compile(ast.Module(body=tree.body[:-1], type_ignores=[]), contract.NOTEBOOK, "exec"), namespace)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write(root / "repo" / contract.AUTHORITY, approved())
            namespace["fetch_source"] = lambda scratch: (root / "repo", old.source())
            namespace["bootstrap"].__defaults__ = (root,)
            original = flow.run
            fake = type("NotebookCPUFake", (old.FakeOperations,), {"events": []})
            with patch.object(flow, "run", side_effect=lambda r,w,o,s: original(r,w,o,s,operations_factory=fake)), redirect_stdout(io.StringIO()):
                exec(compile(ast.Module(body=tree.body[-1:], type_ignores=[]), contract.NOTEBOOK, "exec"), namespace)
            self.assertEqual(namespace["result"]["result"], "TECHNICAL_VALID")

    def test_single_cell_source_lock_and_bootstrap_failure_export(self):
        notebook = json.loads((ROOT / contract.NOTEBOOK).read_bytes())
        cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        self.assertEqual(len(cells), 1)
        code = "".join(cells[0]["source"])
        ast.parse(code)
        lock = json.loads((ROOT / contract.LOCK).read_bytes())
        payload = hashlib.sha256(boot.canonical(lock)).hexdigest()
        self.assertIn(payload, code)
        self.assertEqual(code.replace(payload, "0" * 64), (ROOT / "safeshift/diagnostics/internvl3_hnlo/bootstrap.py").read_text(encoding="utf-8") + "\n# The single Run All entrypoint.\nresult = bootstrap()\n")
        for row in lock["files"]:
            data = (ROOT / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(boot.notebook_bytes(data) if row["path"] == contract.NOTEBOOK else data).hexdigest(), row["sha256"], row["path"])
        with tempfile.TemporaryDirectory() as temp, patch.object(boot, "fetch_source", side_effect=PermissionError("synthetic")), redirect_stdout(io.StringIO()):
            result = boot.bootstrap(Path(temp))
            self.assertFalse(result["HNLO_RESEARCH_VERIFIED"])
            proof_path = next(Path(temp).glob("*_sha256.json"))
            proof = json.loads(proof_path.read_bytes())
            self.assertEqual(sha256(Path(temp) / proof["archive"]), proof["sha256"])
            self.assertEqual(sha256(next(Path(temp).glob("*_manifest.json"))), proof["manifest_sha256"])

    def test_historical_production_and_releases_byte_identical(self):
        archive = subprocess.check_output(["git", "-C", str(ROOT), "archive", contract.BASE_SHA])
        with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
            for member in stream.getmembers():
                if member.isfile() and member.name not in ("TASKS.md", "DECISIONS.md"):
                    self.assertEqual((ROOT / member.name).read_bytes(), stream.extractfile(member).read(), member.name)


@unittest.skipUnless(sys.platform == "linux" and hasattr(os, "geteuid") and os.geteuid() == 0,
                     "Actual guarded ELF fixtures require Linux root; no GPU APIs")
class NativeIntegrationTests(pr115_tests.NativeTests):
    def test_new_session_uses_real_pr115_loader_under_real_guards(self):
        # A CPU-only synthetic Runtime lookalike, never a real CUDA library.
        foreign_runtime = self.root / "libcudart.so.12.synthetic"
        subprocess.run(["cc", "-shared", "-fPIC", "-Wl,-soname,libcudart.so.12", str(self.root / "fixture.c"),
                        "-o", str(foreign_runtime)], check=True, capture_output=True)
        code = '''import ctypes, gc, json, os, sys
from pathlib import Path
from safeshift.diagnostics.internvl3_driver import loader
from safeshift.diagnostics.internvl3_hnlo import driver
from safeshift.diagnostics.internvl3_recovery.network import deny_inet, network_denied
from safeshift.diagnostics.internvl3_recovery.monitor import Monitor
loader.DIRECTORY = Path(sys.argv[1])
loader.OBJECTS = {k: tuple(v) for k,v in json.loads(sys.argv[2]).items()}
loader.SYMBOLS = json.loads(sys.argv[3])
evidence = loader.DIRECTORY / 'new-worker'
evidence.mkdir()
assert driver.preload is loader.preload
assert deny_inet()['tsync']
monitor = Monitor(evidence)
with network_denied(monitor):
    monitor.checkpoint('guarded_start')
    driver.cudart_path = lambda: loader.DIRECTORY / next(iter(loader.OBJECTS.values()))[0]
    session = driver.DriverSession(evidence)
    assert len(session.handles) == 4
    assert all(h.fixture() == 7 for h in session.handles)
    session.observe('after_cuda')
    del session
    gc.collect()
    assert driver._SESSIONS[-1].handles[0].fixture() == 7
    driver._SESSIONS[-1].observe('after_model_load')
    driver._SESSIONS[-1].observe('after_generate')
    foreign = ctypes.CDLL(sys.argv[4])
    assert foreign.fixture() == 7
    try:
        driver._SESSIONS[-1].observe('foreign_runtime')
    except PermissionError as error:
        assert str(error) == 'UNPINNED_CUDA_RUNTIME_MAPPING'
    else:
        raise AssertionError('foreign Runtime mapping was accepted')
    monitor.checkpoint('final')
assert monitor.finish()['security_assessment'] == 'PARTIAL'
print('REAL_PR115_LOADER_NEW_SESSION_LIFETIME_PASS_NO_GPU')
'''
        process = subprocess.run([sys.executable, "-c", code, str(self.root), json.dumps(self.objects), json.dumps(self.symbols), str(foreign_runtime)],
            cwd=ROOT, env=old.flow.child_environment("internvl3", ROOT, "unused", cpu=True), capture_output=True, text=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("REAL_PR115_LOADER_NEW_SESSION_LIFETIME_PASS_NO_GPU", process.stdout)


if __name__ == "__main__":
    unittest.main()
