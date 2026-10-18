"""CPU-only source/authority tests and synthetic ELF under the actual guards."""
import ast
from contextlib import contextmanager, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.diagnostics.internvl3_driver import bootstrap as boot, contract, loader, orchestrate as flow, worker
from safeshift.diagnostics.one_click.artifacts import write, sha256
from safeshift.diagnostics.one_click.orchestrate import child_environment
from tests import test_hnlo_one_click as original_tests
from tests.test_internvl3_cuda_diagnostic import source, FakeOperations

ROOT = Path(__file__).resolve().parents[1]


def approved():
    value = contract.template()
    value["grant"] = {"approved_by": "Synthetic Lead", "role": "Research Lead", "approved_utc": "2026-10-18T00:00:00Z",
        "decision_url": "https://github.com/tantdna2/SafeShift/pull/999#synthetic",
        "independent_audit_url": "https://github.com/tantdna2/SafeShift/pull/999#synthetic-audit",
        "implementation_commit": "b" * 40, "source_payload_sha256": "c" * 64,
        "attempt_id": "internvl3-driver-check-cpu-only", **{flag: True for flag in contract.FLAGS}}
    return value


class ContractTests(unittest.TestCase):
    def test_null_old_grants_missing_flags_and_changed_scope_rejected(self):
        self.assertEqual(json.loads((ROOT / contract.AUTHORITY).read_bytes()), contract.template())
        contract.authorize(approved(), source())
        variants = [contract.template()]
        for key in approved()["grant"]:
            value = approved()
            del value["grant"][key]
            variants.append(value)
        for number in (112, 113, 114):
            for key in ("decision_url", "independent_audit_url"):
                value = approved()
                value["grant"][key] = f"https://github.com/tantdna2/SafeShift/pull/{number}#old"
                variants.append(value)
        for mutate in (
                lambda v: v["grant"].update(attempt_id="internvl3-cuda-diag-old"),
                lambda v: v["grant"].update(source_payload_sha256="f" * 64),
                lambda v: v["grant"].update(driver_loading_policy_change_approved=False),
                lambda v: v["scope"].update(driver_directory="/tmp/stubs")):
            value = approved()
            mutate(value)
            variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(PermissionError):
                contract.authorize(value, source())

    def test_all_host_loader_inputs_dropped_for_both_models(self):
        with patch.dict(os.environ, {"LD_LIBRARY_PATH": "/tmp/evil:/usr/local/nvidia/lib64", "LD_PRELOAD": "evil",
                                     "LD_AUDIT": "evil", "HF_TOKEN": "secret"}, clear=True):
            for model, visibility in (("internvl3", "0"), ("qwen3", "0,1")):
                env = child_environment(model, ROOT, "unused")
                for key in ("LD_LIBRARY_PATH", "LD_PRELOAD", "LD_AUDIT", "HF_TOKEN"):
                    self.assertNotIn(key, env)
                self.assertEqual(env["CUDA_VISIBLE_DEVICES"], visibility)

    def test_location_environment_and_preloaded_driver_rejected_before_dlopen(self):
        with self.assertRaisesRegex(PermissionError, "LOCATION_NOT_ALLOWED"):
            loader.verify_object(Path("/tmp/foreign"), "libcuda.so.1")
        with patch.dict(os.environ, {"LD_LIBRARY_PATH": ""}), patch.object(loader.ctypes, "CDLL") as call:
            with self.assertRaisesRegex(PermissionError, "SANITIZED_LOADER"):
                loader.preload()
            call.assert_not_called()
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, "read_text", return_value="libcuda.so.1"), patch.object(loader.ctypes, "CDLL") as call:
            with self.assertRaisesRegex(PermissionError, "ALREADY_LOADED"):
                loader.preload()
            call.assert_not_called()

    def test_malformed_elf_header_architecture_and_bounds_fail_closed(self):
        import struct
        header = bytearray(64)
        header[:7] = b"\x7fELF\x02\x01\x01"
        struct.pack_into("<HHI", header, 16, 3, 62, 1)
        struct.pack_into("<Q", header, 32, 4096)
        struct.pack_into("<HHH", header, 52, 64, 56, 1)
        wrong_arch = bytearray(header)
        struct.pack_into("<H", wrong_arch, 18, 183)
        for data in (b"stub", bytes(header), bytes(wrong_arch)):
            with self.subTest(data=data[:7]), self.assertRaises(PermissionError):
                loader.elf_identity(data, "libcuda.so.1")


class WorkerTests(unittest.TestCase):
    def execute(self, root, value):
        write(root / contract.AUTHORITY, value)
        write(root / "source.json", source())
        return worker.execute("runtime_count", root, root / "stage", root / "source.json")

    def test_source_authority_guards_environment_preload_then_probe(self):
        events = []
        @contextmanager
        def guard(*args):
            events.append("python_guard")
            yield
        with tempfile.TemporaryDirectory() as temp, patch.object(boot, "verify_topology", side_effect=lambda *a: events.append("source") or source()), patch.object(
                worker, "deny_inet", side_effect=lambda: events.append("seccomp") or {"boundary": contract.BOUNDARY}), patch.object(
                worker, "network_denied", guard), patch.object(worker.Monitor, "checkpoint"), patch.object(
                worker, "check_environment", side_effect=lambda *a: events.append("pins") or {}), patch.object(
                worker, "preload", side_effect=lambda **kw: events.append("preload") or ([], [])), patch.object(
                worker.probes, "run_probe", side_effect=lambda *a: events.append("probe") or {"device_count_result": {"code": 35}}):
            row = self.execute(Path(temp), approved())
        self.assertEqual(events, ["source", "seccomp", "python_guard", "pins", "preload", "probe"])
        self.assertFalse(row["fatal"])
        self.assertFalse(row["CUDA_FIXED"])
        self.assertEqual(row["observation"]["device_count_result"]["code"], 35)

    def test_no_grant_or_invalid_verified_source_prevents_native_load(self):
        for value, proof in ((contract.template(), source()), (approved(), {**source(), "payload_sha256": "f" * 64})):
            with tempfile.TemporaryDirectory() as temp, patch.object(boot, "verify_topology", return_value=proof), patch.object(worker, "preload") as load, patch.object(worker, "deny_inet") as guard:
                row = self.execute(Path(temp), value)
            self.assertTrue(row["fatal"])
            load.assert_not_called()
            guard.assert_not_called()

    def test_bad_driver_is_fatal_no_api_and_evidence_survives(self):
        @contextmanager
        def guard(*args):
            yield
        with tempfile.TemporaryDirectory() as temp, patch.object(boot, "verify_topology", return_value=source()), patch.object(worker, "deny_inet", return_value={"boundary": contract.BOUNDARY}), patch.object(worker, "network_denied", guard), patch.object(worker.Monitor, "checkpoint"), patch.object(worker, "check_environment", return_value={}), patch.object(worker, "preload", side_effect=PermissionError("DRIVER_EVIDENCED_SIZE_MISMATCH")), patch.object(worker.probes, "run_probe") as probe:
            row = self.execute(Path(temp), approved())
            self.assertTrue((Path(temp) / "stage/result.json").is_file())
        self.assertTrue(row["fatal"])
        probe.assert_not_called()


class FlowTests(unittest.TestCase):
    def run_flow(self, root, value=None, fatal=None, session="session"):
        repo, output = root / "repo", root / "output"
        if not (repo / contract.AUTHORITY).exists():
            write(repo / contract.AUTHORITY, value or approved())
        work = output / session
        work.mkdir(parents=True)
        fake = type("DriverFake", (FakeOperations,), {"events": [], "fatal_stage": fatal})
        with redirect_stdout(io.StringIO()):
            row = flow.run(repo, work, output, source(), operations_factory=fake)
        return row, fake.events, work

    def test_six_fresh_stages_no_weights_no_automatic_cuda_pass_and_valid_export(self):
        with tempfile.TemporaryDirectory() as temp:
            row, events, work = self.run_flow(Path(temp))
            self.assertEqual(events, ["software_only", *contract.STAGES])
            self.assertEqual(row["result"], "DIAGNOSTICS_COMPLETED")
            self.assertFalse(row["CUDA_FIXED"])
            receipt = json.loads((work.parent / "session_sha256.json").read_bytes())
            self.assertEqual(sha256(work.parent / receipt["archive"]), receipt["sha256"])

    def test_null_grant_reuse_and_fatal_stop_without_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            _, events, _ = self.run_flow(Path(temp), contract.template())
            self.assertEqual(events, [])
        with tempfile.TemporaryDirectory() as temp:
            row, events, _ = self.run_flow(Path(temp), fatal="load_cuda")
            self.assertEqual(events, ["software_only", "metadata", "load_cuda"])
            self.assertFalse(row["gpu_initialization_attempted"])
            _, events, _ = self.run_flow(Path(temp), session="again")
            self.assertEqual(events, [])

    def test_real_operations_use_new_worker_with_unchanged_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ops = flow.Operations(ROOT, root, root, root / "source.json")
            ops.python = Path("/synthetic/python")
            for stage in contract.STAGES:
                write(root / stage / "result.json", {"fatal": False})
            with patch.object(flow.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as invoke:
                for stage in contract.STAGES:
                    ops.worker(stage)
            self.assertEqual(invoke.call_count, 6)
            for call in invoke.call_args_list:
                self.assertIn("safeshift.diagnostics.internvl3_driver.worker", call.args[0])
                self.assertNotIn("LD_LIBRARY_PATH", call.kwargs["env"])
                self.assertTrue(call.kwargs["close_fds"])

    def test_export_failure_and_draft_bootstrap_preserve_evidence(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(flow, "package", side_effect=OSError("secret")):
            row, _, work = self.run_flow(Path(temp))
            self.assertEqual(row["result"], "EXPORT_FAILED")
            self.assertTrue((work.parent / "session_export_failure.json").is_file())
        with tempfile.TemporaryDirectory() as temp, patch.object(boot, "fetch_source", side_effect=PermissionError("secret")), redirect_stdout(io.StringIO()):
            row = boot.bootstrap(Path(temp))
            self.assertFalse(row["gpu_initialization_attempted"])
            self.assertNotIn("secret", json.dumps(row))


class NotebookTests(unittest.TestCase):
    def test_generated_notebook_and_every_locked_source_byte(self):
        notebook = json.loads((ROOT / contract.NOTEBOOK).read_bytes())
        cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0]["outputs"], [])
        code = "".join(cells[0]["source"])
        tree = ast.parse(code)
        digest = next(n.value.value for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "PAYLOAD_SHA256")
        lock = json.loads((ROOT / contract.LOCK).read_bytes())
        self.assertEqual(hashlib.sha256(boot.canonical(lock)).hexdigest(), digest)
        self.assertEqual(code.replace(digest, "0" * 64), (ROOT / "safeshift/diagnostics/internvl3_driver/bootstrap.py").read_text(encoding="utf-8") + "\n# The single Run All entrypoint.\nresult = bootstrap()\n")
        for row in lock["files"]:
            data = (ROOT / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(boot.notebook_bytes(data) if row["path"] == contract.NOTEBOOK else data).hexdigest(), row["sha256"], row["path"])

    def test_actual_notebook_run_all_with_cpu_operations(self):
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

    def test_historical_environment_guards_releases_and_qwen_are_byte_identical(self):
        paths = subprocess.check_output(["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", contract.BASE_SHA], text=True).splitlines()
        paths = [p for p in paths if p.startswith(("safeshift/diagnostics/one_click/", "safeshift/diagnostics/internvl3_recovery/", "safeshift/diagnostics/internvl3_cuda/")) or
                 p.startswith("configs/diagnostics/") or p.startswith("notebooks/SafeShift_") or "qwen3" in p.lower()]
        # One archive avoids spawning Git once per protected file.
        import tarfile
        archive = subprocess.check_output(["git", "-C", str(ROOT), "archive", contract.BASE_SHA])
        with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
            for path in paths:
                self.assertEqual((ROOT / path).read_bytes(), stream.extractfile(path).read(), path)


class SourceTests(original_tests.SourceTests):
    def setUp(self):
        for name, value in (("boot", boot), ("AUTHORITY", contract.AUTHORITY), ("LOCK", contract.LOCK)):
            replacement = patch.object(original_tests, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        super().setUp()


@unittest.skipUnless(sys.platform == "linux" and hasattr(os, "geteuid") and os.geteuid() == 0,
                     "Native trust fixtures require Linux CPU as root (temporary /root fixtures only)")
class NativeTests(unittest.TestCase):
    cuda = "libsafeshift_fixture_cuda.so.1"
    nvml = "libsafeshift_fixture_nvml.so.1"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/root")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.objects = {}
        self.symbols = {}
        compiler = shutil.which("cc")
        self.assertIsNotNone(compiler, "C compiler required")
        source = self.root / "fixture.c"
        source.write_text('''#include <sys/socket.h>
#include <unistd.h>
#include <errno.h>
static int guarded = 0;
__attribute__((constructor)) static void check_guard(void) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    guarded = (fd == -1 && errno == EPERM);
    if (fd >= 0) close(fd);
}
int fixture(void) { return guarded ? 7 : -1; }
int cuInit(unsigned int x) { return 0; }
int cuDeviceGetCount(int *x) { *x=1; return 0; }
int nvmlInit(void) { return 0; }
int nvmlDeviceGetCount_v2(int *x) { *x=1; return 0; }
''')
        for original, name in (("libcuda.so.1", self.cuda), ("libnvidia-ml.so.1", self.nvml)):
            target = name + ".synthetic"
            output = self.root / target
            subprocess.run([compiler, "-shared", "-fPIC", "-Wl,-soname," + name, str(source), "-o", str(output)], check=True, capture_output=True)
            (self.root / name).symlink_to(target)
            self.objects[name] = (target, output.stat().st_size)
            self.symbols[name] = loader.SYMBOLS[original]
        for name, value in (("DIRECTORY", self.root), ("OBJECTS", self.objects), ("SYMBOLS", self.symbols)):
            replacement = patch.object(loader, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)

    def test_no_allowed_path_fails_but_verified_objects_enable_soname_and_native_constructor_guard(self):
        code = '''import ctypes, errno, json, os, socket, sys
from pathlib import Path
from safeshift.diagnostics.internvl3_driver import loader
from safeshift.diagnostics.internvl3_recovery.network import deny_inet, network_denied
from safeshift.diagnostics.internvl3_recovery.monitor import Monitor, SecurityStop
loader.DIRECTORY = Path(sys.argv[1])
loader.OBJECTS = {k: tuple(v) for k,v in json.loads(sys.argv[2]).items()}
loader.SYMBOLS = json.loads(sys.argv[3])
cuda, nvml = loader.OBJECTS
(loader.DIRECTORY / 'evidence').mkdir()
monitor = Monitor(loader.DIRECTORY / 'evidence')
assert deny_inet()['tsync']
with network_denied(monitor):
    monitor.checkpoint('guarded_start')
    try: ctypes.CDLL(cuda)
    except OSError: pass
    else: raise AssertionError('fixture unexpectedly found before preload')
    handles, records = loader.preload()
    assert all(r['soname_reuse'] for r in records)
    assert ctypes.CDLL(cuda).fixture() == 7
    assert ctypes.CDLL(nvml).fixture() == 7
    try: socket.getaddrinfo('synthetic.invalid', 80)
    except SecurityStop: pass
    else: raise AssertionError('Python guard disabled')
    try: socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except OSError as e: assert e.errno == errno.EPERM
    else: raise AssertionError('seccomp disabled')
assert not monitor.finish()['no_leak_claim']
print('SYNTHETIC_GUARDED_SONAME_REUSE_PASS')
'''
        process = subprocess.run([sys.executable, "-c", code, str(self.root), json.dumps(self.objects), json.dumps(self.symbols)],
                                 cwd=ROOT, env=child_environment("internvl3", ROOT, "unused", cpu=True), capture_output=True, text=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("SYNTHETIC_GUARDED_SONAME_REUSE_PASS", process.stdout)

    def test_foreign_directory_symlink_escape_alias_and_stub_rejected(self):
        directory_alias = self.root / "directory-alias"
        directory_alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(PermissionError):
            loader.trusted_directory(directory_alias)
        for path in (self.root / "foreign", Path("/usr/local/cuda/compat"), Path("/usr/local/cuda/lib64/stubs")):
            with self.subTest(path=path), self.assertRaises(PermissionError):
                loader.verify_object(path, self.cuda)
        alias = self.root / self.cuda
        for target in ("../escape.so", "stubs/" + self.objects[self.cuda][0]):
            alias.unlink()
            alias.symlink_to(target)
            with self.assertRaises(PermissionError):
                loader.verify_object(self.root, alias.name)
        alias.unlink()
        alias.write_bytes(b"stub")
        with self.assertRaises(PermissionError):
            loader.verify_object(self.root, alias.name)

    def test_writable_directory_file_and_non_root_owner_rejected(self):
        alias = self.cuda
        target = self.root / self.objects[alias][0]
        target.chmod(0o666)
        with self.assertRaises(PermissionError):
            loader.verify_object(self.root, alias)
        target.chmod(0o755)
        os.chown(target, 1000, 1000)
        with self.assertRaises(PermissionError):
            loader.verify_object(self.root, alias)
        os.chown(target, 0, 0)
        self.root.chmod(0o777)
        with self.assertRaises(PermissionError):
            loader.verify_object(self.root, alias)
        self.root.chmod(0o700)

    def test_bad_elf_soname_rpath_dependency_and_evidenced_size_rejected(self):
        target, size = self.objects[self.cuda]
        path = self.root / target
        original = path.read_bytes()
        variants = [b"stub" + original[4:], original.replace(self.cuda.encode(), self.cuda.replace("cuda", "stub").encode()),
                    original.replace(b"libc.so.6", b"evil.so.6"), original[:-1]]
        # Change a harmless DT_INIT tag to DT_RPATH without changing file size.
        import struct
        data = bytearray(original)
        phoff = struct.unpack_from("<Q", data, 32)[0]
        count = struct.unpack_from("<H", data, 56)[0]
        for i in range(count):
            header = struct.unpack_from("<IIQQQQQQ", data, phoff + i * 56)
            if header[0] == 2:
                for off in range(header[2], header[2] + header[5], 16):
                    if struct.unpack_from("<q", data, off)[0] == 12:
                        struct.pack_into("<q", data, off, 15)
                        break
        variants.append(bytes(data))
        for data in variants:
            path.write_bytes(data)
            with self.subTest(kind=data[:8]), self.assertRaises(PermissionError):
                loader.verify_object(self.root, self.cuda)
        path.write_bytes(original)
        stream, row = loader.verify_object(self.root, self.cuda)
        stream.close()
        self.assertEqual(row["sha256"], hashlib.sha256(original).hexdigest())


if __name__ == "__main__":
    unittest.main()
