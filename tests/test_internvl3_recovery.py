"""Synthetic CPU evidence only. Native filters run in disposable Linux children."""

import ast
from contextlib import redirect_stdout
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

from safeshift.diagnostics.internvl3_recovery import bootstrap as boot, contract, orchestrate as flow, worker as child
from safeshift.diagnostics.one_click import worker
from safeshift.diagnostics.one_click.artifacts import write, sha256
from tests.test_hnlo_one_click import FakeOperations, approved as old_approved, source
from tests import test_hnlo_one_click as original_tests

ROOT = Path(__file__).resolve().parents[1]


def approved():
    value = contract.template()
    value["grant"] = old_approved()["grant"]
    value["grant"].update(attempt_id="internvl3-recovery-cpu-fake", security_boundary_change_approved=True)
    return value


class AdmissionTests(unittest.TestCase):
    def fake(self, available=False, count=1, build="12.4"):
        return SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: available, device_count=lambda: count),
                               version=SimpleNamespace(cuda=build))

    def test_three_conditions_independent_and_all_reasons_reported(self):
        for available, count, build, reasons in (
            (False, 1, "12.4", ["CUDA_UNAVAILABLE"]),
            (True, 2, "12.4", ["VISIBLE_GPU_COUNT_MISMATCH"]),
            (True, 1, "12.8", ["CUDA_BUILD_MISMATCH"]),
            (False, 0, None, ["CUDA_UNAVAILABLE", "VISIBLE_GPU_COUNT_MISMATCH", "CUDA_BUILD_MISMATCH"]),
            (True, 1, "12.4", [])):
            with self.subTest(available=available, count=count, build=build):
                result = worker.cuda_observation(self.fake(available, count, build), "internvl3")
                self.assertEqual([result[k] for k in ("is_available", "device_count", "torch_version_cuda")],
                                 [available, count, build])
                self.assertEqual(result["failure_reasons"], reasons)

    def test_exception_and_warning_do_not_hide_other_values(self):
        import warnings
        torch = self.fake()
        def bad():
            warnings.warn("synthetic CUDA initialization warning")
            raise RuntimeError("synthetic driver failure")
        torch.cuda.is_available = bad
        result = worker.cuda_observation(torch, "internvl3")
        self.assertEqual(result["device_count"], 1)
        self.assertEqual(result["torch_version_cuda"], "12.4")
        self.assertEqual(result["failure_reasons"], ["IS_AVAILABLE_ERROR"])
        self.assertEqual(result["warnings"], ["synthetic CUDA initialization warning"])

    def test_environment_persists_observations_before_failure(self):
        from safeshift.protocol.classification_policy import load_policy
        versions = load_policy(ROOT, qwen3_runtime=True)["classification"]["internvl3"]["software_versions"]
        with tempfile.TemporaryDirectory() as temp, patch("platform.system", return_value="Linux"), patch(
            "platform.machine", return_value="x86_64"), patch("platform.python_version", return_value="3.11.11"), patch(
            "importlib.metadata.version", side_effect=versions.__getitem__), patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0"}):
            with self.assertRaisesRegex(ValueError, 'EXACT_CUDA.*CUDA_UNAVAILABLE'):
                worker.environment("internvl3", ROOT, self.fake(), evidence=Path(temp))
            saved = json.loads((Path(temp) / "cuda-admission.json").read_bytes())
            self.assertFalse(saved["is_available"])
            self.assertEqual(saved["device_count"], 1)
            self.assertEqual(saved["torch_version_cuda"], "12.4")


class AuthorityFlowTests(unittest.TestCase):
    def test_default_null_exact_single_model_and_pins(self):
        self.assertEqual(json.loads((ROOT / contract.AUTHORITY).read_bytes()), contract.template())
        self.assertEqual(contract.ORDER, ("internvl3",))
        self.assertEqual(list(contract.scope()["models"]), ["internvl3"])
        self.assertEqual(contract.scope()["models"]["internvl3"]["cuda_visible_devices"], "0")
        self.assertEqual(contract.scope()["load_limit_per_model"], 1)
        self.assertEqual(contract.scope()["generate_limit_per_model"], 1)

    def test_missing_security_flag_old_authority_old_attempt_and_references_denied(self):
        contract.authorize(approved(), source())
        candidates = [contract.template(), old_approved()]
        for mutate in (lambda v: v["grant"].pop("security_boundary_change_approved"),
                       lambda v: v["grant"].update(security_boundary_change_approved=False),
                       lambda v: v["grant"].update(attempt_id="hnlo-synthetic-probe-20261017-01"),
                       lambda v: v["grant"].update(decision_url="https://github.com/tantdna2/SafeShift/pull/112#old"),
                       lambda v: v["scope"]["models"].update(qwen3={}),
                       lambda v: v["grant"].update(source_payload_sha256="f" * 64)):
            value = approved()
            mutate(value)
            candidates.append(value)
        for value in candidates:
            with self.subTest(value=value), self.assertRaises(PermissionError):
                contract.authorize(value, source())
        for key in approved()["grant"]:
            value = approved()
            del value["grant"][key]
            with self.subTest(missing=key), self.assertRaises((PermissionError, KeyError)):
                contract.authorize(value, source())

    def execute(self, root, value, failure=None, session="session"):
        repo, output = root / "source", root / "output"
        repo.mkdir(exist_ok=True)
        output.mkdir(exist_ok=True)
        auth = repo / contract.AUTHORITY
        auth.parent.mkdir(parents=True, exist_ok=True)
        auth.write_text(json.dumps(value), encoding="utf-8")
        work = output / session
        work.mkdir()
        events = []
        fake = type("RecoveryFake", (FakeOperations,), {"failure": failure, "events": events})
        with redirect_stdout(io.StringIO()):
            result = flow.run(repo, work, output, source(), operations_factory=fake)
        return result, events, output, work

    def test_only_internvl3_one_call_cpu_replay_export_and_no_reuse(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result, events, output, work = self.execute(root, approved())
            self.assertEqual(result["result"], "TECHNICAL_VALID")
            self.assertEqual([e for e in events if e[0] in ("prepare", "inspect", "probe", "release", "replay")],
                             [(mode, "internvl3") for mode in ("prepare", "inspect", "probe", "release", "replay")])
            self.assertEqual(len(result["models"]), 1)
            row = result["models"][0]
            self.assertEqual((row["load_calls"], row["generate_calls"]), (1, 1))
            self.assertFalse(row["HNLO_RESEARCH_VERIFIED"])
            self.assertIn("cpu_replay_memory_after", row)
            proof = json.loads((output / (work.name + "_sha256.json")).read_bytes())
            self.assertEqual(sha256(output / (work.name + ".tar.gz")), proof["sha256"])
            with tarfile.open(output / (work.name + ".tar.gz")) as stream:
                names = stream.getnames()
                self.assertTrue(any("/raw-000.json" in name for name in names))
                self.assertTrue(any("/processed-000.json" in name for name in names))
                self.assertFalse(any("qwen3" in name for name in names))
            second, events, _, _ = self.execute(root, approved(), session="second")
            self.assertEqual(second["result"], "BLOCKED")
            self.assertFalse(events)

    def test_failures_retained_no_retry_or_second_model(self):
        for failure in ("missinggpu", "checksum", "download", "environment", "invalid", "oom", "wrongalignment", "nonfinite", "torn", "killed"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                result, events, output, work = self.execute(Path(temp), approved(), failure)
                self.assertIsNone(result["models"][0]["hnlo"])
                self.assertLessEqual(events.count(("probe", "internvl3")), 1)
                self.assertFalse(any("qwen3" in event for event in events))
                self.assertTrue((output / (work.name + ".tar.gz")).is_file())

    def test_null_or_old_grant_no_preflight_provision_or_gpu(self):
        for value in (contract.template(), old_approved()):
            with tempfile.TemporaryDirectory() as temp:
                result, events, _, _ = self.execute(Path(temp), value)
                self.assertFalse(events)
                self.assertEqual(result["gpu_probe_status"], "NOT_RUN")

    def test_each_worker_mode_rechecks_authority_before_any_cuda(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write(root / "source.json", source())
            write(root / contract.AUTHORITY, contract.template())
            for mode in ("inspect", "probe", "replay"):
                args = ["worker", "--mode", mode, "--model", "internvl3", "--cache", "data/processed/cache",
                        "--source", str(root / "source.json"), "--evidence", str(root / mode), "--capture-root", str(root)]
                with patch.object(Path, "cwd", return_value=root), patch.object(sys, "argv", args), patch.object(
                    boot, "verify_topology"), patch.object(child, "environment") as cuda:
                    self.assertEqual(child.main(), 2)
                    cuda.assert_not_called()

    def test_worker_cuda_failure_is_after_both_guards_and_persists_three_values(self):
        from safeshift.diagnostics.internvl3_recovery import network
        from safeshift.runners.internvl3_snapshot import OFFLINE_ENV
        import socket
        for mode in ("inspect", "probe"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                write(root / "source.json", source())
                write(root / contract.AUTHORITY, approved())
                events = []
                def install():
                    events.append("seccomp")
                    return {"kind": "FAKE_CPU_NO_FILTER"}
                def admission(model, repo, evidence):
                    events.append("cuda")
                    with self.assertRaisesRegex(RuntimeError, "NETWORK_FORBIDDEN"):
                        socket.getaddrinfo("synthetic.invalid", 1)
                    observed = worker.cuda_observation(AdmissionTests().fake(), model)
                    write(evidence / "cuda-admission.json", observed)
                    raise ValueError("EXACT_CUDA_BUILD_AND_VISIBLE_GPU_COUNT_REQUIRED")
                args = ["worker", "--mode", mode, "--model", "internvl3", "--cache", "data/processed/cache",
                        "--source", str(root / "source.json"), "--evidence", str(root / mode), "--capture-root", str(root)]
                with patch.object(Path, "cwd", return_value=root), patch.object(sys, "argv", args), patch.object(
                    boot, "verify_topology", side_effect=lambda *a: events.append("source")), patch.object(
                    network, "deny_inet", side_effect=install), patch.object(child, "environment", side_effect=admission), patch.dict(
                    os.environ, OFFLINE_ENV):
                    self.assertEqual(child.main(), 2)
                self.assertEqual(events, ["source", "seccomp", "cuda"])
                result = json.loads((root / mode / "result.json").read_bytes())
                self.assertEqual(result["cuda_admission"]["failure_reasons"], ["CUDA_UNAVAILABLE"])
                self.assertEqual(result["cuda_admission"]["device_count"], 1)
                self.assertEqual(result["cuda_admission"]["torch_version_cuda"], "12.4")
                self.assertEqual((result["load_calls"], result["generate_calls"]), (0, 0))

    def test_bootstrap_draft_denial_only_one_model_and_export(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(boot, "fetch_source", side_effect=PermissionError(
            "DRAFT_OR_UNMERGED_SOURCE_NO_EXECUTION")), redirect_stdout(io.StringIO()):
            result = boot.bootstrap(Path(temp))
            self.assertEqual([r["model"] for r in result["models"]], ["internvl3"])
            self.assertFalse(result["gpu_executed"])
            self.assertEqual(len(list(Path(temp).glob("*.tar.gz"))), 1)

    def test_actual_notebook_run_all_routes_only_to_recovery(self):
        notebook = json.loads((ROOT / contract.NOTEBOOK).read_bytes())
        code = "".join(next(c["source"] for c in notebook["cells"] if c["cell_type"] == "code"))
        tree = ast.parse(code)
        namespace = {"__name__": "__notebook__"}
        exec(compile(ast.Module(body=tree.body[:-1], type_ignores=[]), contract.NOTEBOOK, "exec"), namespace)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo, output = root / "source", root / "output"
            repo.mkdir(); output.mkdir()
            write(repo / contract.AUTHORITY, approved())
            namespace["fetch_source"] = lambda scratch: (repo, source())
            namespace["bootstrap"].__defaults__ = (output,)
            events = []
            fake = type("NotebookRecoveryFake", (FakeOperations,), {"failure": None, "events": events})
            original_run = flow.run
            with patch.object(flow, "run", side_effect=lambda r, w, o, s: original_run(r, w, o, s, operations_factory=fake)), redirect_stdout(io.StringIO()):
                exec(compile(ast.Module(body=tree.body[-1:], type_ignores=[]), contract.NOTEBOOK, "exec"), namespace)
            self.assertEqual(namespace["result"]["result"], "TECHNICAL_VALID")
            self.assertEqual(events.count(("probe", "internvl3")), 1)
            self.assertFalse(any("qwen3" in event for event in events))

    def test_notebook_json_ast_every_source_hash_and_history_unchanged(self):
        notebook = json.loads((ROOT / contract.NOTEBOOK).read_bytes())
        code_cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        self.assertEqual(len(code_cells), 1)
        self.assertEqual(code_cells[0]["outputs"], [])
        self.assertIsNone(code_cells[0]["execution_count"])
        code = "".join(code_cells[0]["source"])
        tree = ast.parse(code)
        compile(code, contract.NOTEBOOK, "exec")
        digest = next(n.value.value for n in tree.body if isinstance(n, ast.Assign)
                      and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "PAYLOAD_SHA256")
        lock = json.loads((ROOT / contract.LOCK).read_bytes())
        self.assertEqual(hashlib.sha256(boot.canonical(lock)).hexdigest(), digest)
        expected = (ROOT / "safeshift/diagnostics/internvl3_recovery/bootstrap.py").read_text(encoding="utf-8")
        self.assertEqual(code.replace(digest, "0" * 64), expected + "\n# The single Run All entrypoint.\nresult = bootstrap()\n")
        for row in lock["files"]:
            data = (ROOT / row["path"]).read_bytes()
            if row["path"] == contract.NOTEBOOK:
                data = boot.notebook_bytes(data)
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"], row["path"])
        for name in ("configs/diagnostics/hnlo_one_click_authority.v1.json", "configs/diagnostics/hnlo_one_click_source.v1.json",
                     "notebooks/SafeShift_HNLO_Qwen3_InternVL3_ONE_CLICK.ipynb"):
            historical = subprocess.check_output(["git", "-C", str(ROOT), "show", contract.BASE_SHA + ":" + name])
            self.assertEqual((ROOT / name).read_bytes(), historical, name)


class RecoverySourceTests(original_tests.SourceTests):
    """Reuse the real Git F1/F2/M attack fixture against the recovery trust root."""

    def setUp(self):
        for name, value in (("boot", boot), ("AUTHORITY", contract.AUTHORITY), ("LOCK", contract.LOCK)):
            replacement = patch.object(original_tests, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        super().setUp()


@unittest.skipUnless(sys.platform == "linux", "Native seccomp requires Linux CPU; never GPU evidence")
class LinuxNetworkTests(unittest.TestCase):
    def run_child(self, code):
        env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_old_native_filter_proves_unix_creation_but_connect_eperm(self):
        self.run_child('''
import socket, errno
from safeshift.diagnostics.one_click.network import deny_inet
deny_inet()
with socket.socket(socket.AF_UNIX) as s:
    try: s.connect('/tmp/safeshift-no-peer')
    except OSError as e: assert e.errno == errno.EPERM, e
    else: raise AssertionError('old connect unexpectedly permitted')
''')

    def test_old_python_guard_blocks_real_unix_connect(self):
        self.run_child('''
import socket
from safeshift.runners.internvl3_snapshot import network_denied
with network_denied(), socket.socket(socket.AF_UNIX) as s:
    try: s.connect('/tmp/safeshift-no-peer')
    except RuntimeError as e: assert str(e) == 'NETWORK_FORBIDDEN'
    else: raise AssertionError('old Python connect unexpectedly permitted')
''')

    def test_new_filter_unix_creation_connect_ex_and_stream_io_both_guards(self):
        self.run_child('''
import socket, os, tempfile
from safeshift.diagnostics.internvl3_recovery.network import deny_inet, network_denied
assert deny_inet()['unix_connect_self_test'] == 'PASS'
with tempfile.TemporaryDirectory() as tmp, network_denied():
    with socket.socket(socket.AF_UNIX) as server:
        server.bind(tmp + '/local.sock'); server.listen(2)
        for method in ('connect', 'connect_ex'):
            with socket.socket(socket.AF_UNIX) as client:
                result = getattr(client, method)(server.getsockname())
                assert result in (None, 0)
                accepted, _ = server.accept()
                with accepted:
                    os.write(client.fileno(), b'x')
                    assert os.read(accepted.fileno(), 1) == b'x'
    a, b = socket.socketpair()
    a.close(); b.close()
''')

    def test_native_forbidden_families_syscalls_x32_and_family_spoof(self):
        self.run_child('''
import ctypes, errno, socket
from safeshift.diagnostics.internvl3_recovery.network import deny_inet
deny_inet()
libc = ctypes.CDLL(None, use_errno=True)
for nr, args in [(41, (family, 1, 0)) for family in (2, 10, 17, 16, 40)] + [(53, (family, 1, 0, 0)) for family in (2, 10, 17)] + [(nr, (0, 0, 0, 0, 0, 0)) for nr in (44, 46, 307, 47, 299, 438, 101, 425, 426, 427, 272, 308, 0x40000029)]:
    ctypes.set_errno(0)
    assert libc.syscall(nr, *args) == -1 and ctypes.get_errno() == errno.EPERM, (nr, ctypes.get_errno())
# connect cannot turn the only constructible socket family into INET/INET6.
with socket.socket(socket.AF_UNIX) as s:
    for family in (2, 10):
        address = ctypes.create_string_buffer(bytes([family, 0]) + bytes(126))
        assert libc.connect(s.fileno(), address, 128) == -1
        assert ctypes.get_errno() in (errno.EINVAL, errno.EAFNOSUPPORT)
''')

    def test_python_inet_connect_connect_ex_dns_send_and_fd_receipt_denied(self):
        self.run_child('''
import socket
from safeshift.diagnostics.internvl3_recovery.network import network_denied
with network_denied():
    for family, address in ((socket.AF_INET, ('127.0.0.1', 9)), (socket.AF_INET6, ('::1', 9))):
        with socket.socket(family) as s:
            for method in ('connect', 'connect_ex'):
                try: getattr(s, method)(address)
                except RuntimeError as e: assert str(e) == 'NETWORK_FORBIDDEN'
                else: raise AssertionError(method)
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
        for call in (lambda: s.sendto(b'x', '/tmp/no-peer'), lambda: s.sendmsg([b'x']), lambda: s.recvmsg(1), lambda: s.recvmsg_into([bytearray(1)]), lambda: socket.getaddrinfo('localhost', 80), lambda: socket.create_connection(('127.0.0.1', 9))):
            try: call()
            except RuntimeError as e: assert str(e) == 'NETWORK_FORBIDDEN'
            else: raise AssertionError('Python forbidden call permitted')
''')

    def test_inherited_socket_any_family_including_stdio_rejected(self):
        for family in ("AF_INET", "AF_INET6", "AF_UNIX"):
            self.run_child('''
import socket, os
from safeshift.diagnostics.internvl3_recovery.network import deny_inet
s = socket.socket(socket.''' + family + ''')
os.dup2(s.fileno(), 0)
try: deny_inet()
except RuntimeError as e: assert str(e) == 'SECCOMP_INHERITED_SOCKET_FORBIDDEN'
else: raise AssertionError('inherited socket accepted')
''')

    def test_existing_threads_rejected_and_new_threads_descendants_inherit(self):
        self.run_child('''
import threading, socket, errno, subprocess, sys
from safeshift.diagnostics.internvl3_recovery.network import deny_inet
event = threading.Event()
thread = threading.Thread(target=event.wait); thread.start()
try:
    try: deny_inet()
    except RuntimeError as e: assert str(e) == 'SECCOMP_SINGLE_THREAD_START_REQUIRED'
    else: raise AssertionError('multithread start accepted')
finally: event.set(); thread.join()
deny_inet()
results = []
def blocked():
    try: socket.socket(socket.AF_INET)
    except OSError as e: results.append(e.errno)
thread = threading.Thread(target=blocked); thread.start(); thread.join()
assert results == [errno.EPERM]
code = 'import socket, errno\\ntry: socket.socket(socket.AF_INET6)\\nexcept OSError as e: assert e.errno == errno.EPERM\\nelse: raise AssertionError()'
assert subprocess.run([sys.executable, '-c', code], close_fds=True).returncode == 0
''')


if __name__ == "__main__":
    unittest.main()
