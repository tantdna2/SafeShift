"""Synthetic CPU fixtures only: no driver library, GPU, model or network access."""
import ast
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
import ctypes
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tarfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.diagnostics.internvl3_cuda import bootstrap as boot, contract, orchestrate as flow, probes, worker
from safeshift.diagnostics.one_click.artifacts import write, sha256
from safeshift.diagnostics.one_click.orchestrate import child_environment
from tests import test_hnlo_one_click as old_tests

ROOT = Path(__file__).resolve().parents[1]


def source():
    return {"merge_commit": "a" * 40, "implementation_commit": "b" * 40,
            "payload_sha256": "c" * 64, "github_pr": {"fixture": "CPU_SYNTHETIC"}}


def approved():
    value = contract.template()
    value["grant"] = {"approved_by": "Synthetic Lead", "role": "Research Lead", "approved_utc": "2026-10-18T00:00:00Z",
        "decision_url": "https://github.com/tantdna2/SafeShift/pull/999#synthetic",
        "independent_audit_url": "https://github.com/tantdna2/SafeShift/pull/999#synthetic-audit",
        "implementation_commit": "b" * 40, "source_payload_sha256": "c" * 64,
        "attempt_id": "internvl3-cuda-diag-cpu-only", **{flag: True for flag in contract.FLAGS}}
    return value


class ContractTests(unittest.TestCase):
    def test_null_old_grants_missing_flags_reused_attempt_and_source_mismatch_rejected(self):
        contract.authorize(approved(), source())
        variants = [contract.template()]
        for key in approved()["grant"]:
            value = approved()
            del value["grant"][key]
            variants.append(value)
        for mutation in (lambda v: v["grant"].update(attempt_id="internvl3-recovery-20261018-01"),
                         lambda v: v["grant"].update(decision_url="https://github.com/tantdna2/SafeShift/pull/113#old"),
                         lambda v: v["grant"].update(source_payload_sha256="f" * 64),
                         lambda v: v["grant"].update(driver_initialization_approved=False),
                         lambda v: v["scope"].update(unguarded_cuda=True)):
            value = approved()
            mutation(value)
            variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(PermissionError):
                contract.authorize(value, source())

    def test_new_contract_has_no_model_or_data_permission_and_unchanged_boundary(self):
        value = json.loads((ROOT / contract.AUTHORITY).read_bytes())
        self.assertEqual({**value, "grant": None}, contract.template())
        self.assertFalse(any(contract.template()["scope"][key] for key in
            ("weights_download", "model_load", "inference", "dataset_access", "labels_or_gt_access", "retry", "unguarded_cuda", "security_boundary_expansion")))

    def test_environment_sanitization_is_reproduced_without_changing_it(self):
        with patch.dict(os.environ, {"LD_LIBRARY_PATH": "/synthetic/driver/lib", "LD_PRELOAD": "secret", "HF_TOKEN": "secret"}, clear=True):
            env = child_environment("internvl3", ROOT, "unused-cache")
            host = probes.environment_metadata(os.environ)
        self.assertNotIn("LD_LIBRARY_PATH", env)
        self.assertNotIn("LD_PRELOAD", env)
        self.assertNotIn("HF_TOKEN", env)
        self.assertEqual(env["CUDA_VISIBLE_DEVICES"], "0")
        self.assertEqual(host["LD_LIBRARY_PATH"]["directories"][0]["sha256"], hashlib.sha256(b"/synthetic/driver/lib").hexdigest())
        self.assertNotIn("secret", json.dumps(host))
        self.assertNotIn("/synthetic/driver/lib", json.dumps(host))


class MetadataTests(unittest.TestCase):
    def test_loader_cache_is_filtered_and_unavailable_tools_are_explicit(self):
        text = "libcuda.so.1 (libc6) => /usr/lib/libcuda.so.580\nlibunrelated.so (libc6) => /secret\n"
        with patch.object(probes.shutil, "which", return_value="/sbin/ldconfig"), patch.object(probes, "command_output", return_value=(text, None)):
            row = probes.linker_cache()
        self.assertEqual(len(row["entries"]), 1)
        self.assertNotIn("secret", json.dumps(row))
        with patch.object(probes.shutil, "which", return_value=None), patch.object(Path, "is_file", return_value=False):
            self.assertEqual(probes.linker_cache()["status"], "UNOBSERVABLE")

    def test_synthetic_elf_symlink_dependency_and_broken_target_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "libfixture.so.1"
            target.write_bytes(b"\x7fELFsynthetic-no-driver")
            with patch.object(probes.shutil, "which", return_value="readelf"), patch.object(probes, "command_output", return_value=("(NEEDED) Shared library: [libdependency.so.1]", None)):
                row = probes.file_metadata(target, root)
            self.assertTrue(row["elf_magic"])
            self.assertEqual(row["dynamic"]["needed"], ["libdependency.so.1"])
            self.assertEqual(row["target"]["path"], "<runtime>/libfixture.so.1")
            self.assertEqual(probes.file_metadata(root / "missing")["status"], "UNOBSERVABLE")
            if sys.platform == "linux":
                link = root / "alias.so"
                link.symlink_to(target.name)
                self.assertTrue(probes.file_metadata(link)["symlink"])
                target.unlink()
                self.assertEqual(probes.file_metadata(link)["status"], "UNOBSERVABLE")

    def test_device_permission_and_missing_nodes_are_metadata_not_access_proof(self):
        with patch.object(Path, "stat", side_effect=PermissionError(errno.EACCES, "secret")):
            rows = probes.devices(Path("/synthetic"))
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(r["error"]["errno"] == errno.EACCES for r in rows))
        self.assertNotIn("secret", json.dumps(rows))
        self.assertTrue(all("NOT_OPEN_IOCTL_OR_CGROUP_PROOF" in r["access_scope"] for r in rows))

    def test_stub_compat_path_and_loader_failure_are_reported_without_raw_error(self):
        self.assertTrue(probes.path_metadata("/usr/local/cuda/compat/libcuda.so.1")["possible_stub_or_compat"])
        with patch.object(os, "RTLD_LOCAL", 0, create=True), patch.object(os, "RTLD_NOW", 2, create=True), patch.object(probes.ctypes, "CDLL", side_effect=OSError("/secret/token: cannot open shared object file")), patch.object(probes, "mapped_libraries", return_value={}):
            handle, row = probes.load_library("cuda")
        self.assertIsNone(handle)
        self.assertEqual(row["status"], "LOAD_FAILED")
        self.assertEqual(row["loader_category"], "cannot open shared object file")
        self.assertNotIn("secret", json.dumps(row))

    def test_wrong_library_missing_symbols_is_a_functional_observation(self):
        with patch.object(os, "RTLD_LOCAL", 0, create=True), patch.object(os, "RTLD_NOW", 2, create=True), patch.object(
            probes.ctypes, "CDLL", return_value=SimpleNamespace()), patch.object(probes, "mapped_libraries", return_value={}):
            handle, row = probes.load_library("cuda")
        self.assertIsNone(handle)
        self.assertEqual(row["status"], "MISSING_REQUIRED_SYMBOL")
        self.assertFalse(row["required_symbols"]["cuInit"])


class FakeFunction:
    def __init__(self, result=0, count=None):
        self.result, self.count, self.calls = result, count, []

    def __call__(self, *args):
        self.calls.append(args)
        if self.count is not None:
            args[0]._obj.value = self.count
        return self.result


class ProbeTests(unittest.TestCase):
    def library(self, init=0, runtime=0):
        return SimpleNamespace(cuInit=FakeFunction(init), cuDeviceGetCount=FakeFunction(count=1),
                               cudaGetDeviceCount=FakeFunction(runtime, count=0 if runtime else 1))

    def test_loader_only_never_calls_cuda_or_nvml_initialization(self):
        library = self.library()
        for stage in ("load_cuda", "load_nvml", "load_cudart"):
            with patch.object(probes, "load_library", return_value=(library, {"initialization_called": False})):
                row = probes.run_probe(stage)
            self.assertFalse(row["initialization_called"])
        self.assertEqual(library.cuInit.calls, [])
        self.assertEqual(library.cudaGetDeviceCount.calls, [])

    def test_cudart_uses_the_pinned_wheel_location_without_host_search(self):
        distribution = SimpleNamespace(locate_file=lambda path: Path("/synthetic/pinned") / path)
        with patch.object(probes.importlib.metadata, "distribution", return_value=distribution) as lookup:
            self.assertEqual(probes.cudart_path().as_posix(), "/synthetic/pinned/nvidia/cuda_runtime/lib/libcudart.so.12")
        lookup.assert_called_once_with("nvidia-cuda-runtime-cu12")

    def test_original_driver_error_does_not_become_device_count_zero(self):
        library = self.library(init=803)
        with patch.object(probes, "load_library", return_value=(library, {})), patch.object(probes, "mapped_libraries", return_value={}):
            row = probes.run_probe("cuinit")
        self.assertEqual(row["initialization"]["code"], 803)
        self.assertNotIn("device_count", row)
        self.assertEqual(library.cuDeviceGetCount.calls, [])

    def test_runtime_error_preserved_and_never_substituted_by_nvml(self):
        library = self.library(runtime=35)
        with patch.object(probes, "load_library", return_value=(library, {})), patch.object(probes, "mapped_libraries", return_value={}):
            row = probes.run_probe("runtime_count")
        self.assertEqual(row["device_count_result"]["code"], 35)
        self.assertIsNone(row["device_count"])
        self.assertEqual(library.cuInit.calls, [])

    def test_successful_driver_and_runtime_counts_are_distinct_observations(self):
        for stage in ("cuinit", "runtime_count"):
            library = self.library()
            with patch.object(probes, "load_library", return_value=(library, {})), patch.object(probes, "mapped_libraries", return_value={}):
                row = probes.run_probe(stage)
            self.assertEqual(row["device_count"], 1)
            self.assertTrue(row["initialization_called"])


class WorkerTests(unittest.TestCase):
    def test_every_stage_reauthorizes_and_installs_both_guards_before_probes(self):
        for stage in contract.STAGES:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                write(root / contract.AUTHORITY, approved())
                write(root / "source.json", source())
                order = []
                @contextmanager
                def guard(monitor):
                    order.append("python_guard")
                    yield
                with patch.object(boot, "verify_topology", side_effect=lambda *a: order.append("source") or source()), patch.object(
                    worker, "deny_inet", side_effect=lambda: order.append("seccomp") or {"boundary": contract.BOUNDARY}), patch.object(
                    worker, "network_denied", guard), patch.object(worker.Monitor, "checkpoint"), patch.object(
                    worker, "check_environment", return_value={}), patch.object(probes, "run_probe", side_effect=lambda *a: order.append("probe") or {"fixture": "CPU"}):
                    row = worker.execute(stage, root, root / stage, root / "source.json")
                self.assertEqual(order, ["source", "seccomp", "python_guard", "probe"])
                self.assertFalse(row["fatal"])
                self.assertEqual(row["load_calls"], 0)

    def test_null_authority_prevents_guard_library_load_and_gpu_api(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write(root / contract.AUTHORITY, contract.template())
            write(root / "source.json", source())
            with patch.object(boot, "verify_topology", return_value=source()), patch.object(worker, "deny_inet") as guard, patch.object(probes, "run_probe") as probe:
                row = worker.execute("cuinit", root, root / "stage", root / "source.json")
            guard.assert_not_called()
            probe.assert_not_called()
            self.assertTrue(row["fatal"])

    def test_verified_git_identity_cannot_be_replaced_by_the_source_envelope(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write(root / contract.AUTHORITY, approved())
            write(root / "source.json", source())
            verified = {**source(), "implementation_commit": "f" * 40}
            with patch.object(boot, "verify_topology", return_value=verified), patch.object(worker, "deny_inet") as guard:
                row = worker.execute("cuinit", root, root / "stage", root / "source.json")
            self.assertTrue(row["fatal"])
            self.assertEqual(row["error"]["reason"], "DIAGNOSTIC_SOURCE_BINDING_MISMATCH")
            guard.assert_not_called()


class FakeOperations:
    events = []
    fatal_stage = None
    def __init__(self, repo, work, evidence, source_path):
        self.evidence = evidence
    def prepare(self):
        self.events.append("software_only")
    def worker(self, stage):
        self.events.append(stage)
        row = {"stage": stage, "fatal": stage == self.fatal_stage, "result": "SYNTHETIC_CPU",
               "observation": {"code": 35}, "load_calls": 0, "generate_calls": 0}
        write(self.evidence / stage / "result.json", row)
        return row


class FlowTests(unittest.TestCase):
    def run_flow(self, root, value=None, fatal=None, session="session"):
        write(root / "repo" / contract.AUTHORITY, value or approved()) if not (root / "repo" / contract.AUTHORITY).exists() else None
        output = root / "output"
        output.mkdir(exist_ok=True)
        work = output / session
        work.mkdir()
        events = []
        fake = type("IsolatedFake", (FakeOperations,), {"events": events, "fatal_stage": fatal})
        with redirect_stdout(io.StringIO()):
            result = flow.run(root / "repo", work, output, source(), operations_factory=fake)
        return result, events, work

    def test_functional_cuda_failure_does_not_hide_other_independent_stages_and_exports(self):
        with tempfile.TemporaryDirectory() as temp:
            result, events, work = self.run_flow(Path(temp))
            self.assertEqual(events, ["software_only", *contract.STAGES])
            self.assertEqual(result["result"], "DIAGNOSTICS_COMPLETED")
            self.assertFalse(result["CUDA_ROOT_CAUSE_CONFIRMED"])
            receipt = json.loads((work.parent / (work.name + "_sha256.json")).read_bytes())
            self.assertEqual(sha256(work.parent / receipt["archive"]), receipt["sha256"])

    def test_null_grant_and_second_run_all_do_not_prepare_or_probe(self):
        with tempfile.TemporaryDirectory() as temp:
            result, events, _ = self.run_flow(Path(temp), contract.template())
            self.assertEqual(events, [])
            self.assertEqual(result["result"], "BLOCKED")
        with tempfile.TemporaryDirectory() as temp:
            self.run_flow(Path(temp))
            result, events, _ = self.run_flow(Path(temp), session="second")
            self.assertEqual(events, [])
            self.assertFalse(result["gpu_initialization_attempted"])

    def test_security_failure_stops_next_stage_without_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            result, events, work = self.run_flow(Path(temp), fatal="load_cuda")
            self.assertEqual(events, ["software_only", "metadata", "load_cuda"])
            self.assertFalse(result["gpu_initialization_attempted"])
            self.assertTrue((work / "evidence/load_cuda/result.json").is_file())

    def test_export_failure_retains_partial_result_and_failure_receipt(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(flow, "package", side_effect=OSError("secret")):
            result, _, work = self.run_flow(Path(temp))
            self.assertEqual(result["result"], "EXPORT_FAILED")
            receipt = (work.parent / (work.name + "_export_failure.json")).read_text()
            self.assertNotIn("secret", receipt)
            self.assertTrue((work / "evidence/result.json").exists())

    def test_real_operations_launches_new_interpreter_for_each_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write(root / "metadata/result.json", {"fatal": False})
            write(root / "runtime_count/result.json", {"fatal": False})
            ops = flow.Operations(ROOT, root, root, root / "source.json")
            ops.python = Path("/synthetic/python3.11")
            with patch.object(flow.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run:
                ops.worker("metadata")
                ops.worker("runtime_count")
            self.assertEqual(run.call_count, 2)
            for call in run.call_args_list:
                self.assertEqual(call.args[0][0], str(Path("/synthetic/python3.11")))
                self.assertTrue(call.kwargs["close_fds"])
                self.assertEqual(call.kwargs["env"]["CUDA_VISIBLE_DEVICES"], "0")
                self.assertNotIn("LD_LIBRARY_PATH", call.kwargs["env"])


class NotebookTests(unittest.TestCase):
    def test_notebook_compiles_binds_every_source_byte_and_preserves_history(self):
        notebook = json.loads((ROOT / contract.NOTEBOOK).read_bytes())
        cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        self.assertEqual(len(cells), 1)
        code = "".join(cells[0]["source"])
        tree = ast.parse(code)
        compile(code, contract.NOTEBOOK, "exec")
        digest = next(n.value.value for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "PAYLOAD_SHA256")
        lock = json.loads((ROOT / contract.LOCK).read_bytes())
        self.assertEqual(hashlib.sha256(boot.canonical(lock)).hexdigest(), digest)
        self.assertEqual(code.replace(digest, "0" * 64), (ROOT / "safeshift/diagnostics/internvl3_cuda/bootstrap.py").read_text(encoding="utf-8") + "\n# The single Run All entrypoint.\nresult = bootstrap()\n")
        grant = json.loads((ROOT / contract.AUTHORITY).read_bytes()).get("grant")
        historical = None
        if grant:
            archive = subprocess.check_output(["git", "-C", str(ROOT), "archive", grant["implementation_commit"]])
            historical = self.enterContext(tarfile.open(fileobj=io.BytesIO(archive)))
        for row in lock["files"]:
            # Released PR #114 pins its own F1, not this subsequent repair.
            data = historical.extractfile(row["path"]).read() if historical else (ROOT / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(boot.notebook_bytes(data) if row["path"] == contract.NOTEBOOK else data).hexdigest(), row["sha256"], row["path"])
        for path in ("safeshift/diagnostics/internvl3_recovery/network.py", "safeshift/diagnostics/one_click/orchestrate.py",
                     "configs/diagnostics/internvl3_recovery_source.v1.json", "configs/diagnostics/internvl3_recovery_authority.v1.json",
                     "notebooks/SafeShift_InternVL3_RECOVERY_ONE_CLICK.ipynb"):
            self.assertEqual((ROOT / path).read_bytes(), subprocess.check_output(["git", "-C", str(ROOT), "show", contract.BASE_SHA + ":" + path]))

    def test_bootstrap_failure_exports_blocked_without_gpu(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(boot, "fetch_source", side_effect=PermissionError("secret")), redirect_stdout(io.StringIO()):
            row = boot.bootstrap(Path(temp))
            self.assertFalse(row["gpu_initialization_attempted"])
            self.assertNotIn("secret", json.dumps(row))
            self.assertEqual(len(list(Path(temp).glob("*.tar.gz"))), 1)

    def test_actual_notebook_run_all_uses_diagnostic_flow_with_cpu_doubles(self):
        notebook = json.loads((ROOT / contract.NOTEBOOK).read_bytes())
        tree = ast.parse("".join(notebook["cells"][1]["source"]))
        namespace = {"__name__": "__notebook__"}
        exec(compile(ast.Module(body=tree.body[:-1], type_ignores=[]), contract.NOTEBOOK, "exec"), namespace)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write(root / "repo" / contract.AUTHORITY, approved())
            namespace["fetch_source"] = lambda scratch: (root / "repo", source())
            namespace["bootstrap"].__defaults__ = (root,)
            original = flow.run
            fake = type("NotebookFake", (FakeOperations,), {"events": []})
            with patch.object(flow, "run", side_effect=lambda r, w, o, s: original(r, w, o, s, operations_factory=fake)), redirect_stdout(io.StringIO()):
                exec(compile(ast.Module(body=tree.body[-1:], type_ignores=[]), contract.NOTEBOOK, "exec"), namespace)
            self.assertEqual(namespace["result"]["result"], "DIAGNOSTICS_COMPLETED")
            self.assertEqual(fake.events, ["software_only", *contract.STAGES])


class SourceTests(old_tests.SourceTests):
    def setUp(self):
        for name, value in (("boot", boot), ("AUTHORITY", contract.AUTHORITY), ("LOCK", contract.LOCK)):
            replacement = patch.object(old_tests, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        super().setUp()


@unittest.skipUnless(sys.platform == "linux", "Native CPU fixtures require Linux; no CUDA implication")
class LinuxCpuTests(unittest.TestCase):
    def test_real_procfs_checkpoint_counts_closed_enumeration_descriptor(self):
        from safeshift.diagnostics.internvl3_recovery.monitor import Monitor
        with tempfile.TemporaryDirectory() as temp:
            monitor = Monitor(temp)
            monitor.checkpoint("real_cpu_procfs")
            row = json.loads((Path(temp) / "network-monitor/event-000002.json").read_bytes())
            self.assertEqual(row["errors"], [])
            self.assertEqual(row["status"], "PARTIAL")
            self.assertIn("closed_before_inspection", row)
            self.assertFalse(monitor.finish()["no_leak_claim"])

    def test_guarded_synthetic_library_demonstrates_conditional_loader_path_loss(self):
        compiler = shutil.which("cc")
        if not compiler:
            self.skipTest("C compiler unavailable for synthetic shared-library fixture")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "fixture.c").write_text("int fixture(void) { return 7; }\n")
            subprocess.run([compiler, "-shared", "-fPIC", str(root / "fixture.c"), "-o", str(root / "libfixture_driver.so.1")], check=True, capture_output=True)
            code = """import ctypes
from safeshift.diagnostics.internvl3_recovery.network import deny_inet, network_denied
deny_inet()
with network_denied():
    try:
        library = ctypes.CDLL('libfixture_driver.so.1')
        assert library.fixture() == 7
        print('SYNTHETIC_LIBRARY_LOADED')
    except OSError:
        print('SYNTHETIC_LIBRARY_MISSING')
"""
            with patch.dict(os.environ, {"LD_LIBRARY_PATH": str(root)}):
                inherited = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONDONTWRITEBYTECODE": "1"}
                sanitized = child_environment("internvl3", ROOT, "unused-cache", cpu=True)
            rows = []
            for env in (inherited, sanitized):
                process = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
                self.assertEqual(process.returncode, 0, process.stderr)
                rows.append(process.stdout.strip())
            self.assertEqual(rows, ["SYNTHETIC_LIBRARY_LOADED", "SYNTHETIC_LIBRARY_MISSING"])
