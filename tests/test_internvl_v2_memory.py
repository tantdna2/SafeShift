"""CPU-only observations, memory lifetime and fail-closed V2 diagnostics."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from safeshift import internvl_v2_memory as memory
from safeshift.pilot.artifacts import read, write, sha
from scripts import internvl_v2 as engine


class MemoryTests(unittest.TestCase):
    def fixture(self, root):
        proc, cg = root / "proc", root / "cgroup"
        (proc / "self").mkdir(parents=True)
        cg.mkdir()
        (proc / "meminfo").write_text("MemAvailable: 33554432 kB\n")
        (proc / "self/status").write_text("Name: synthetic\nVmRSS: 65536 kB\n")
        (proc / "self/smaps_rollup").write_text("Rss: 65536 kB\nAnonymous: 32768 kB\n")
        for name, value in {"memory.current": str(4 * 2**30), "memory.max": str(32 * 2**30),
            "memory.peak": str(5 * 2**30), "memory.stat": "anon 1073741824\nfile 3221225472\n",
            "memory.events": "oom 0\noom_kill 0\n"}.items():
            (cg / name).write_text(value)
        return proc, cg

    def test_cgroup_anon_file_rss_and_gate_snapshot_are_actual_fields(self):
        with tempfile.TemporaryDirectory() as d:
            proc, cg = self.fixture(Path(d))
            value = memory.snapshot(proc, cg)
            self.assertEqual(value["status"], "OBSERVED")
            self.assertEqual(value["gate_memory"]["available_bytes"], 28 * 2**30)
            self.assertEqual(value["cgroup"]["memory.stat"]["anon"], 2**30)
            self.assertEqual(value["cgroup"]["memory.stat"]["file"], 3 * 2**30)
            self.assertEqual(value["process"]["status"]["VmRSS"], 64 * 2**20)
            (cg / "memory.max").write_text("max")
            self.assertEqual(memory.snapshot(proc, cg)["gate_memory"]["available_bytes"], 32 * 2**30)

    def test_missing_and_oversized_diagnostics_are_explicit_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); proc, cg = self.fixture(root)
            (cg / "memory.stat").unlink()
            (proc / "self/smaps_rollup").write_text("x" * 65537)
            observed = memory.snapshot(proc, cg)
            self.assertEqual(observed["status"], "INCOMPLETE")
            self.assertNotIn("memory.stat", observed["cgroup"])
            with patch.object(memory, "snapshot", return_value=observed), \
                    patch.object(memory.environment, "resources") as gate, self.assertRaisesRegex(ValueError, "INCOMPLETE"):
                memory.resource_check(root, "preload", engine.policy(), root)
            gate.assert_not_called()
            self.assertEqual(read(root / "preload-memory-failure.json")["failure_type"], "ValueError")

    def test_empty_or_malformed_required_fields_cannot_report_observed(self):
        for name, content in (("memory.stat", ""), ("memory.stat", "anon wrong\nfile 123\n"),
                              ("memory.stat", "anon -1\nfile 123\n")):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as d:
                proc, cg = self.fixture(Path(d))
                (cg / name).write_text(content)
                self.assertEqual(memory.snapshot(proc, cg)["status"], "INCOMPLETE")

    def test_exact_16gib_floor_unchanged_failure_snapshot_and_boundary(self):
        from types import SimpleNamespace as NS
        for available in (16 * 2**30 - 1, 16 * 2**30):
            with self.subTest(available=available), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                observed = {"status": "OBSERVED", "gate_memory": {"available_bytes": available}, "cgroup": {}}
                with patch.object(memory, "snapshot", return_value=observed), \
                    patch.object(memory.environment, "host_memory", return_value={"available_bytes": available}), \
                    patch.object(memory.environment.shutil, "disk_usage", return_value=NS(free=2**40)):
                    if available < 16 * 2**30:
                        with self.assertRaisesRegex(ValueError, "HOST_OR_CGROUP_RAM"):
                            memory.resource_check(root, "preload", engine.policy(), root)
                        self.assertEqual(read(root / "preload-memory-failure.json")["gate_memory"]["available_bytes"], available)
                    else:
                        result = memory.resource_check(root, "preload", engine.policy(), root)
                        self.assertEqual(result["memory"]["available_bytes"], available)

    def test_advice_requires_owned_actual_worker_prefix(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / "venv3119/lib").mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "OWNED_WORKER"):
                memory.advise_owned_venv(root, root / "other")

    @unittest.skipUnless(sys.platform == "linux", "POSIX owned-file advice")
    def test_advice_preserves_bytes_and_refuses_aliases_and_shared_hardlinks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); venv = root / "venv3119"; lib = venv / "lib"; lib.mkdir(parents=True)
            owned = lib / "owned.so"; owned.write_bytes(b"s" * (8 * 2**20))
            shared = lib / "shared.so"; os.link(owned, shared)
            with patch.object(memory.os, "posix_fadvise") as advise:
                with self.assertRaises(ValueError):
                    memory.advise_owned_venv(root, venv)
                advise.assert_not_called()
            shared.unlink()
            checksum = sha(owned)
            result = memory.advise_owned_venv(root, venv)
            self.assertEqual(result["advised_files"], 1)
            self.assertEqual(sha(owned), checksum)
            self.assertEqual(result["deleted_files"], 0)
            (lib / "alias.so").symlink_to(owned)
            with self.assertRaises(ValueError):
                memory.advise_owned_venv(root, venv)

    @unittest.skipUnless(sys.platform == "linux", "POSIX advice scan bounds")
    def test_advice_scan_limit_stops_and_does_not_delete(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); lib = root / "venv3119/lib"; lib.mkdir(parents=True)
            for i in range(3):
                (lib / str(i)).write_text("SYNTHETIC")
            with self.assertRaisesRegex(ValueError, "SCAN_LIMIT"):
                memory.advise_owned_venv(root, root / "venv3119", max_entries=1)
            self.assertEqual(len(list(lib.iterdir())), 3)

    def test_reclaim_failure_preserves_before_after_and_cannot_claim_pass(self):
        observed = {"status": "OBSERVED", "cgroup": {"memory.stat": {"file": 10}}}
        with tempfile.TemporaryDirectory() as d, patch.object(memory, "snapshot", return_value=observed), \
                patch.object(memory, "advise_owned_venv", side_effect=OSError("SYNTHETIC")), self.assertRaises(OSError):
            root = Path(d)
            try:
                engine.reclaim_owned(root, root)
            finally:
                self.assertTrue((root / "owned-advice-memory-before.json").exists())
                self.assertTrue((root / "owned-advice-memory-after.json").exists())
                self.assertFalse((root / "owned-venv-advice.json").exists())

    def test_processor_parent_snapshots_survive_timeout_and_missing_receipt(self):
        for failure in (TimeoutError("SYNTHETIC"), None):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as d, \
                    patch.object(memory, "snapshot", return_value={"status": "OBSERVED"}), \
                    patch.object(engine.supervision, "run", side_effect=failure) as supervised:
                root = Path(d)
                with self.assertRaises((TimeoutError, FileNotFoundError)):
                    engine.run_processor_check({}, root, root, root, engine.policy(), time.monotonic() + 2)
                self.assertEqual(supervised.call_args.kwargs["env"]["CUDA_VISIBLE_DEVICES"], "")
                self.assertIn("processor", supervised.call_args.args[0])
                self.assertTrue((root / "processor-parent-memory-after.json").exists())

    def test_processor_worker_failure_has_after_snapshot_no_model_load(self):
        with tempfile.TemporaryDirectory() as d, patch.object(engine.runtime, "check_source"), \
            patch.object(memory, "snapshot", return_value={"status": "OBSERVED"}), \
            patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": ""}), \
            patch.object(engine, "checkpoint", return_value=(None, None, None)), \
            patch.object(engine, "processor_check", side_effect=ValueError("SYNTHETIC")), \
            patch.object(engine.runtime, "NativeBackend") as load, self.assertRaises(ValueError):
            root = Path(d)
            try:
                engine.worker("processor", {}, root, root, root)
            finally:
                load.assert_not_called()
                self.assertTrue((root / "processor-memory-after.json").exists())
                self.assertFalse((root / "attempt.json").exists())

    def test_ram_still_low_after_isolation_never_reaches_native_attempt(self):
        from contextlib import ExitStack
        from scripts import smoke_kaggle173 as smoke
        from safeshift.fulltrain import preflight
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            root = Path(d)
            stack.enter_context(patch.object(engine.runtime, "authorize"))
            stack.enter_context(patch.object(engine.runtime, "check_source"))
            stack.enter_context(patch.object(memory, "snapshot", return_value={"status": "OBSERVED"}))
            stack.enter_context(patch.object(memory.environment, "resources", side_effect=[{}, ValueError("HOST_OR_CGROUP_RAM")]))
            for module, name in ((smoke, "bind_cuda_driver"), (smoke, "driver_check"),
                (preflight, "storage_probe"), (engine.environment, "software"), (engine.environment, "cuda"),
                (engine, "run_processor_check"), (engine, "reclaim_owned")):
                stack.enter_context(patch.object(module, name, return_value={}))
            stack.enter_context(patch.object(engine, "check_checkpoint", return_value=(root, root)))
            execute = stack.enter_context(patch.object(engine.runtime, "execute_attempt"))
            with self.assertRaisesRegex(ValueError, "HOST_OR_CGROUP_RAM"):
                engine.worker("native", {}, root, root, root, root / "missing", time.monotonic()+30)
            execute.assert_not_called()
            self.assertTrue((root / "preload-resources-memory-failure.json").exists())
            self.assertFalse((root / "attempt.json").exists())


@unittest.skipUnless(sys.platform == "linux", "Linux actual process lifetime and cgroup observations")
class LinuxLifetimeTests(unittest.TestCase):
    def test_large_anonymous_allocation_dies_with_supervised_child(self):
        from safeshift.fulltrain.supervision import run
        code = """import sys
from pathlib import Path
from safeshift.internvl_v2_memory import snapshot
from safeshift.pilot.artifacts import write
root=Path(sys.argv[1])
write(root/'child-before.json',snapshot())
data=bytearray(192*2**20)
write(root/'child-allocated.json',snapshot())
"""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            before = memory.snapshot()
            run([sys.executable, "-B", "-c", code, str(root)], cwd=engine.ROOT, env=dict(os.environ),
                deadline=time.monotonic()+15, log=root/"child.log", receipt=root/"child-supervisor.json", max_log_bytes=4096)
            child, allocated = read(root/"child-before.json"), read(root/"child-allocated.json")
            self.assertGreater(allocated["process"]["status"]["VmRSS"]-child["process"]["status"]["VmRSS"], 180*2**20)
            self.assertFalse(Path("/proc", str(allocated["pid"])).exists())
            after = memory.snapshot()
            self.assertLess(after["process"]["status"]["VmRSS"]-before["process"]["status"]["VmRSS"], 32*2**20)

    def test_actual_timeout_kills_processor_child_and_retains_partial_memory(self):
        code = """import sys,time
from pathlib import Path
from safeshift.internvl_v2_memory import snapshot
from safeshift.pilot.artifacts import write
write(Path(sys.argv[1])/'partial-memory.json',snapshot())
data=bytearray(64*2**20)
time.sleep(30)
"""
        with tempfile.TemporaryDirectory() as d, patch.object(engine, "worker_command", return_value=[sys.executable,"-B","-c",code,d]):
            root = Path(d)
            with self.assertRaisesRegex(RuntimeError, "HARD_DEADLINE"):
                engine.run_processor_check({},root,root,root,engine.policy(),time.monotonic()+1)
            partial = read(root/"partial-memory.json")
            status = Path("/proc",str(partial["pid"]),"status")
            # SIGKILL exit and PID1 reaping can lag the guardian by a few ms.
            # Require the actual address space to disappear, not PID reuse timing.
            until = time.monotonic() + 3
            while status.exists() and time.monotonic() < until:
                try:
                    text = status.read_text()
                except FileNotFoundError:
                    break
                if "VmRSS:" not in text:
                    break
                time.sleep(.01)
            if status.exists():
                self.assertNotIn("VmRSS:", status.read_text())
            self.assertTrue((root/"processor-parent-memory-after.json").exists())
            self.assertFalse((root/"processor.json").exists())


if __name__ == "__main__":
    unittest.main()
