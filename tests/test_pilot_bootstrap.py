"""CPU fault injection at the actual supervisor boundaries, never GPU proof."""
from contextlib import ExitStack, contextmanager
import os
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import errno
from types import SimpleNamespace
from unittest.mock import patch

from safeshift.pilot import bootstrap as b
from safeshift.pilot.artifacts import Store, export, import_archive, read, safe, sha, write
from safeshift.pilot.backend import check_source_review, provision
from safeshift.pilot.contract import digest, source_digest
from test_pilot import ROOT, grant, plan, raw
from scripts.pilot_source_audit import audit as source_audit, NoCredentialRedirect
from urllib.request import Request


GIB = 2**30
GPU = "Tesla T4, 15360, 14800, 550.90.07\nTesla T4, 15360, 14800, 550.90.07\n"


class StorageTests(unittest.TestCase):
    @unittest.skipUnless(hasattr(os, "posix_fallocate"), "Linux allocation API unavailable")
    def test_small_real_allocation_is_released(self):
        with tempfile.TemporaryDirectory() as d:
            scratch, output = Path(d) / "scratch", Path(d) / "output"
            scratch.mkdir()
            output.mkdir()
            with patch.object(b, "SCRATCH_BUDGET_BYTES", 1024 * 1024), \
                 patch.object(b, "OUTPUT_BUDGET_BYTES", 512 * 1024):
                receipt = b.storage_admission(scratch, output)
            self.assertTrue(receipt["admitted"], receipt)
            self.assertEqual(receipt["allocation"]["scratch"]["requested_bytes"], 1024 * 1024)
            self.assertEqual(list(scratch.iterdir()), [])
            self.assertEqual(list(output.iterdir()), [])

    def admission(self, devices, frees, resume=0):
        observations = [{"device": dev, "free_bytes": free * GIB}
                        for dev, free in zip(devices, frees)]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "scratch").mkdir()
            (root / "output").mkdir()
            with patch.object(b, "filesystem_usage", side_effect=observations), \
                 patch.object(b.os, "posix_fallocate", create=True), \
                 patch.object(b.os, "fsync"), \
                 patch.object(b.os, "fstat", side_effect=[SimpleNamespace(st_size=28*GIB, st_blocks=28*GIB//512),
                                                           SimpleNamespace(st_size=4*GIB+4*resume, st_blocks=(4*GIB+4*resume)//512)]):
                return b.storage_admission(root / "scratch", root / "output", resume)

    def test_shared_filesystem_requires_sum_not_two_independent_checks(self):
        self.assertFalse(self.admission((1, 1), (31, 31))["admitted"])
        r = self.admission((1, 1), (32, 32))
        self.assertTrue(r["admitted"])
        self.assertEqual(len(r["filesystems"]), 1)
        self.assertEqual(r["filesystems"][0]["required_bytes"], 32 * GIB)

    def test_same_device_different_free_observations_take_minimum(self):
        self.assertFalse(self.admission((1, 1), (40, 31))["admitted"])

    def test_distinct_mounts_need_each_own_capacity(self):
        self.assertTrue(self.admission((1, 2), (28, 4))["admitted"])
        for frees in ((27, 100), (100, 3)):
            self.assertFalse(self.admission((1, 2), frees)["admitted"])

    def test_resume_extraction_copy_archive_headroom_is_additional(self):
        self.assertFalse(self.admission((1, 1), (35, 35), GIB)["admitted"])
        self.assertTrue(self.admission((1, 1), (36, 36), GIB)["admitted"])

    def test_quota_failure_after_statvfs_pass_is_blocked_and_probe_removed(self):
        with tempfile.TemporaryDirectory() as d:
            scratch, output = Path(d) / "scratch", Path(d) / "output"
            scratch.mkdir()
            output.mkdir()
            observations = [{"device": 1, "free_bytes": 40 * GIB},
                            {"device": 2, "free_bytes": 40 * GIB}]
            with patch.object(b, "filesystem_usage", side_effect=observations), \
                 patch.object(b.os, "posix_fallocate", side_effect=OSError(errno.EDQUOT, "quota"), create=True):
                receipt = b.storage_admission(scratch, output)
            self.assertFalse(receipt["admitted"])
            self.assertEqual(receipt["reason"], "ALLOCATION_CHECK_FAILED")
            self.assertEqual(receipt["allocation_error"]["errno"], errno.EDQUOT)
            self.assertEqual(list(scratch.iterdir()), [])

    def test_second_quota_failure_releases_both_simultaneous_probes(self):
        with tempfile.TemporaryDirectory() as d:
            scratch, output = Path(d) / "scratch", Path(d) / "output"
            scratch.mkdir()
            output.mkdir()
            observations = [{"device": 1, "free_bytes": 40 * GIB},
                            {"device": 2, "free_bytes": 40 * GIB}]
            with patch.object(b, "filesystem_usage", side_effect=observations), \
                 patch.object(b.os, "posix_fallocate", side_effect=[None, OSError(errno.EDQUOT, "output quota")], create=True), \
                 patch.object(b.os, "fsync"), \
                 patch.object(b.os, "fstat", return_value=SimpleNamespace(st_size=28*GIB, st_blocks=28*GIB//512)):
                receipt = b.storage_admission(scratch, output)
            self.assertFalse(receipt["admitted"])
            self.assertEqual(receipt["allocation"]["scratch"]["status"], "ALLOCATED")
            self.assertEqual(receipt["allocation_error"]["errno"], errno.EDQUOT)
            self.assertEqual(list(scratch.iterdir()), [])
            self.assertEqual(list(output.iterdir()), [])

    def test_preflight_never_reads_grant_or_calls_subprocess(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            work, scratch = root / "working", root / "scratch"
            work.mkdir()
            scratch.mkdir()
            with patch.object(b, "storage_admission", return_value={"admitted": True, "reason": "SYNTHETIC"}), \
                 patch.object(b, "discover", side_effect=AssertionError("NO_GRANT")), \
                 patch.object(b.subprocess, "run", side_effect=AssertionError("NO_PROCESS")), \
                 patch.object(b.subprocess, "check_output", side_effect=AssertionError("NO_GPU")):
                output = b.storage_preflight(work, scratch)
            self.assertTrue(read(output / "storage_preflight.json")["admitted"])
            self.assertEqual(read(output / "storage_preflight.sha256.json")["sha256"], sha(output / "storage_preflight.json"))
            self.assertEqual(list(scratch.iterdir()), [])

    def test_output_not_writable_prints_failure_without_grant(self):
        with tempfile.TemporaryDirectory() as d, \
             patch.object(b, "safe", side_effect=PermissionError(errno.EACCES, "denied")), \
             patch("builtins.print") as printed:
            self.assertIsNone(b.storage_preflight(d, d))
            self.assertIn("OUTPUT_PREPARATION_FAILED", str(printed.call_args))

    def test_preflight_permission_failure_receipt_and_cleanup_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            work, scratch = root / "working", root / "scratch"
            work.mkdir()
            scratch.mkdir()
            with patch.object(b, "prepare_scratch", side_effect=PermissionError(errno.EACCES, "denied")):
                out = b.storage_preflight(work, scratch)
            receipt = read(out / "storage_preflight.json")
            self.assertFalse(receipt["admitted"])
            self.assertEqual(receipt["error"]["errno"], errno.EACCES)
            with patch.object(b, "storage_admission", return_value={"admitted": True, "reason": "SYNTHETIC"}), \
                 patch.object(b, "cleanup_scratch", side_effect=OSError("cleanup denied")):
                out = b.storage_preflight(work, scratch)
            receipt = read(out / "storage_preflight.json")
            self.assertFalse(receipt["admitted"])
            self.assertIn("cleanup denied", receipt["scratch_cleanup_error"])

    def test_symlink_scratch_root_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            work, scratch = root / "working", root / "scratch"
            work.mkdir()
            scratch.mkdir()
            original = Path.is_symlink
            with patch.object(Path, "is_symlink", lambda p: p == scratch or original(p)):
                out = b.storage_preflight(work, scratch)
            self.assertIn("STORAGE_ROOT_ALIAS", read(out / "storage_preflight.json")["error"]["message"])

    def test_actual_filesystem_observation_and_working_scratch(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            scratch, env = b.prepare_scratch(root, "synthetic")
            actual = b.filesystem_usage(scratch)
            self.assertEqual(actual["device"], scratch.stat().st_dev)
            self.assertGreater(actual["total_bytes"], 0)
            self.assertTrue(scratch.is_relative_to(root))
            for key in ("TMPDIR", "TMP", "TEMP", "HF_HOME", "HF_MODULES_CACHE", "XDG_CACHE_HOME", "TORCH_HOME"):
                self.assertTrue(Path(env[key]).is_relative_to(scratch))
            with self.assertRaises(FileExistsError):
                b.prepare_scratch(root, "synthetic")
            with self.assertRaises(ValueError):
                b.prepare_scratch(root, "../../escape")

    def test_real_hardlink_remains_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "source").write_bytes(b"SYNTHETIC")
            os.link(root / "source", root / "alias")
            for name in ("source", "alias"):
                with self.assertRaisesRegex(ValueError, "HARDLINK"):
                    safe(root, name)

    def test_scratch_cleanup_scope_and_evidence_survival(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            scratch, _ = b.prepare_scratch(root, "synthetic")
            evidence = root / "evidence"
            write(evidence / "raw.json", raw())
            with self.assertRaisesRegex(ValueError, "SCOPE"):
                b.cleanup_scratch(root, evidence, "synthetic")
            b.cleanup_scratch(root, scratch, "synthetic")
            self.assertFalse(scratch.exists())
            self.assertEqual(read(evidence / "raw.json"), raw())

    def test_symlink_remains_rejected_without_relaxing_mount_policy(self):
        with tempfile.TemporaryDirectory() as d, patch.object(Path, "is_symlink", return_value=True):
            with self.assertRaisesRegex(ValueError, "SYMLINK"):
                safe(d, "input")


@contextmanager
def supervisor_case(key="phi", worker=None, disk_ok=True, resume=False):
    """Only synthetic plan; intercept image reader, hardware and subprocesses."""
    with tempfile.TemporaryDirectory() as d, ExitStack() as patches:
        root = Path(d)
        inputs, work = root / "input", root / "working"
        scratch_root = root / "scratch"
        bundle = inputs / "private"
        bundle.mkdir(parents=True)
        work.mkdir()
        scratch_root.mkdir()
        p = plan()
        write(bundle / "bundle.json", {"SYNTHETIC": True})
        write(bundle / "pilot_manifest.json", p)
        g = grant(key)
        g.update(source_sha256=source_digest(ROOT), manifest_sha256=digest(p))
        if resume:
            previous = root / "previous"
            write(previous / "retained.json", {"synthetic": True})
            archive = bundle / f"resume_{key}.zip"
            g.update(resume_parent_archive_sha256=export(previous, archive), resume_approval_ref="SYNTHETIC")
        write(bundle / f"grant_{key}.json", g)
        calls = []
        def run(command, **kwargs):
            calls.append((command, kwargs))
            if "safeshift.pilot.runner" in command:
                output = Path(command[command.index("--output") + 1])
                if worker:
                    worker(output)
            return subprocess.CompletedProcess(command, 0)
        loader = patches.enter_context(patch.object(b, "load_bundle", return_value=(p, p["main"])))
        patches.enter_context(patch.object(b, "supported_runtime", return_value=True))
        patches.enter_context(patch.object(b, "storage_admission", return_value={"admitted": disk_ok, "SYNTHETIC": True}))
        patches.enter_context(patch.object(b.subprocess, "run", side_effect=run))
        patches.enter_context(patch.object(b.subprocess, "check_output", side_effect=lambda cmd, **kw: GPU if cmd[0] == "nvidia-smi" else "SYNTHETIC_FREEZE\n"))
        yield root, inputs, work, p, g, calls, loader


class SupervisorTests(unittest.TestCase):
    def launch(self, case, key="phi"):
        _, inputs, work, _, g, _, _ = case
        return b.launch(key, g["source_sha256"], ROOT, inputs, work, scratch_root=case[0] / "scratch")

    def test_real_launch_orders_cuda_install_before_requirements_and_check(self):
        with supervisor_case() as case:
            out = self.launch(case)
            commands = [c for c, _ in case[5]]
            runtime = commands[0][-1]
            expected = b.dependency_commands(Path(runtime) / "bin/python", ROOT, "phi")
            self.assertEqual(commands[1:5], expected)
            self.assertIn("https://download.pytorch.org/whl/cu124", commands[2])
            self.assertIn("torch==2.6.0+cu124", commands[2])
            self.assertIn("torchvision==0.21.0+cu124", commands[2])
            self.assertEqual(commands[4][-1], "check")
            self.assertEqual(commands[-1][-2:], ["--mode", "PILOT"])
            for _, kwargs in case[5]:
                self.assertTrue(Path(kwargs["env"]["TMPDIR"]).is_relative_to(case[0] / "scratch"))
            self.assertEqual(case[5][-1][1]["env"]["CUDA_VISIBLE_DEVICES"], "0")
            self.assertTrue(out.with_suffix(".zip").is_file())

    def test_insufficient_storage_blocks_installer_and_exports_receipt(self):
        with supervisor_case(disk_ok=False) as case:
            out = self.launch(case)
            self.assertEqual(case[5], [])
            self.assertEqual(read(out / "supervisor_failure.json")["stage"], "storage")
            self.assertFalse(read(out / "storage_admission.json")["admitted"])
            self.assertEqual(len(read(out / "recovered_report/comparison.json")), 160)
            self.assertTrue(out.with_suffix(".zip").is_file())

    def test_worker_crash_keeps_raw_and_accounts_every_id(self):
        def crash(out):
            store = Store(out / "run", {"synthetic": True})
            store.start(0, {"attempts": 1})
            store.raw(0, raw())
            raise subprocess.CalledProcessError(9, ["SYNTHETIC_WORKER"])
        with supervisor_case(worker=crash) as case:
            out = self.launch(case)
            results = b.recover_accounting(out, case[3])
            self.assertEqual(sum(r["status"] == "TECHNICAL_ERROR" for r in results.values()), 1)
            self.assertEqual(sum(r["status"] == "NOT_ATTEMPTED" for r in results.values()), 159)
            recovered = import_archive(out.with_suffix(".zip"), case[0] / "recovered")
            self.assertEqual(read(recovered / "run/samples/000000/raw.json"), raw())

    def test_archive_failure_retains_partial_zip_and_evidence(self):
        def broken_export(root, archive):
            Path(archive).write_bytes(b"SYNTHETIC_PARTIAL_ZIP")
            raise OSError("SYNTHETIC_EXPORT_DISK_FULL")
        def worker(out):
            write(out / "partial_raw.json", raw())
            raise RuntimeError("SYNTHETIC_WORKER_CRASH")
        with supervisor_case(worker=worker) as case, patch.object(b, "export", side_effect=broken_export):
            out = self.launch(case)
            self.assertEqual(read(out / "partial_raw.json"), raw())
            self.assertEqual(out.with_suffix(".zip").read_bytes(), b"SYNTHETIC_PARTIAL_ZIP")
            self.assertFalse(Path(str(out.with_suffix(".zip")) + ".sha256.json").exists())

    def test_real_export_writer_failure_keeps_sealed_sources(self):
        with supervisor_case() as case, patch("zipfile.ZipFile.write", side_effect=OSError("SYNTHETIC_ZIP_WRITE_FAILED")):
            out = self.launch(case)
            self.assertTrue((out / "checksums.json").is_file())
            self.assertTrue((out / "pilot_manifest.json").is_file())
            self.assertTrue(out.with_suffix(".zip").is_file())
            self.assertFalse(Path(str(out.with_suffix(".zip")) + ".sha256.json").exists())

    def test_scratch_cleanup_failure_does_not_suppress_export(self):
        with supervisor_case() as case, patch.object(b, "cleanup_scratch", side_effect=OSError("SYNTHETIC_CLEANUP_FAILURE")):
            out = self.launch(case)
            self.assertTrue(out.with_suffix(".zip").is_file())

    def test_session_write_failure_still_attempts_archive(self):
        actual_write = b.write
        def broken_session(path, value):
            if Path(path).name == "session.json":
                raise OSError("SYNTHETIC_SESSION_DISK_FULL")
            return actual_write(path, value)
        with supervisor_case() as case, patch.object(b, "write", side_effect=broken_session):
            out = self.launch(case)
            self.assertTrue(out.with_suffix(".zip").is_file())

    def test_failed_setup_never_launches_worker_keeps_setup_log(self):
        with supervisor_case() as case:
            with patch.object(b.subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["SYNTHETIC_PIP"])):
                out = self.launch(case)
            self.assertEqual(read(out / "supervisor_failure.json")["stage"], "software")
            self.assertTrue((out / "setup.log").is_file())
            self.assertFalse((out / "worker.log").exists())
            self.assertTrue(out.with_suffix(".zip").is_file())

    def test_disk_full_during_install_exports_failure_and_no_worker(self):
        with supervisor_case() as case:
            with patch.object(b.subprocess, "run", side_effect=OSError(errno.ENOSPC, "disk full")):
                out = self.launch(case)
            self.assertEqual(read(out / "supervisor_failure.json")["stage"], "software")
            self.assertFalse((out / "worker.log").exists())
            self.assertTrue(out.with_suffix(".zip").is_file())

    def test_attempt_reuse_does_not_overwrite_old_output(self):
        with supervisor_case() as case:
            first = self.launch(case)
            old = sha(first.with_suffix(".zip"))
            second = self.launch(case)
            self.assertNotEqual(first, second)
            self.assertEqual(sha(first.with_suffix(".zip")), old)
            self.assertEqual(read(second / "supervisor_failure.json")["stage"], "authority")
            self.assertEqual(sum("safeshift.pilot.runner" in c for c, _ in case[5]), 1)

    def test_verified_resume_preserves_previous_archive_evidence(self):
        with supervisor_case(resume=True) as case:
            out = self.launch(case)
            self.assertEqual(read(out / "prior/retained.json"), {"synthetic": True})
            self.assertIn("--parent", case[5][-1][0])

    def test_pilot_never_accepts_full_mode_even_before_io(self):
        with patch.object(Path, "mkdir", side_effect=AssertionError("IO")):
            with self.assertRaises(PermissionError):
                b.launch("phi", "a" * 64, ROOT, mode="FULL_TRAIN")

    def test_gemma_empty_review_blocks_even_with_synthetic_valid_grant(self):
        with supervisor_case(key="gemma") as case:
            out = self.launch(case, "gemma")
            case[6].assert_not_called()
            self.assertEqual(case[5], [])
            failure = read(out / "supervisor_failure.json")
            self.assertEqual(failure["stage"], "source_review")
            self.assertEqual(failure["status"], "BLOCKED")
            self.assertIn("SOURCE_TOKENIZER_AUDIT_INCOMPLETE", failure["message"])


class SourceAndGPUAdmissionTests(unittest.TestCase):
    def test_authenticated_audit_never_fetches_weights_or_saves_token(self):
        metadata = {"sha": "093f9f388b31de276ce2de164bdc2081324b9767", "siblings": [
            {"rfilename": name} for name in ("config.json", "tokenizer.json", "model.safetensors",
                                             "model.safetensors.index.json", "nested/code.py")]}
        requests = []
        class Opener:
            def open(self, request, **kwargs):
                requests.append(request)
                return io.BytesIO(json.dumps(metadata if "/api/" in request.full_url else {"synthetic": True}).encode())
        with tempfile.TemporaryDirectory() as d, patch.object(Path, "cwd", return_value=Path(d)), \
                patch("scripts.pilot_source_audit.build_opener", return_value=Opener()), \
                patch.dict(os.environ, {"HF_TOKEN": "SYNTHETIC_SECRET_NEVER_REAL"}):
            output = Path(d) / "data/processed/audit"
            r = source_audit(output, ["gemma"], authenticated=True)
            self.assertEqual(set(r["gemma"]["files"]), {"config.json", "tokenizer.json"})
            self.assertEqual(len(requests), 3)
            self.assertTrue(all(request.get_header("Authorization") for request in requests))
            self.assertNotIn("SYNTHETIC_SECRET", (output / "inventory.json").read_text())
            with self.assertRaises(FileExistsError):
                source_audit(output, ["gemma"], authenticated=True)

    def test_authenticated_audit_missing_token_has_no_io(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, "mkdir", side_effect=AssertionError("IO")):
            with self.assertRaisesRegex(PermissionError, "HF_TOKEN_ENV_REQUIRED"):
                source_audit(ROOT / "data/processed/never", ["gemma"], authenticated=True)

    def test_audit_redirect_removes_authorization(self):
        request = Request("https://huggingface.co/example", headers={"Authorization": "Bearer SYNTHETIC"})
        redirected = NoCredentialRedirect().redirect_request(
            request, None, 302, "Found", {}, "https://cdn.example.invalid/object")
        self.assertIsNone(redirected.get_header("Authorization"))

    def test_gemma_does_not_contact_hub_without_reviewed_source(self):
        with patch.dict(os.environ, {"HF_TOKEN": "SYNTHETIC_NOT_A_REAL_TOKEN"}):
            with self.assertRaisesRegex(PermissionError, "SOURCE_TOKENIZER_AUDIT_INCOMPLETE"):
                provision(ROOT, "gemma", "SYNTHETIC_NEVER_CREATED")
        for key in ("phi", "smolvlm2"):
            self.assertTrue(check_source_review(ROOT, key)["files"])

    def test_malformed_gpu_or_wrong_capacity_is_blocked(self):
        for text in ("", "Tesla T4\nTesla T4\n", GPU.replace("15360", "N/A"),
                     GPU.replace("14800", "[Not Supported]"), GPU.replace("15360", "32768"),
                     GPU.replace("Tesla T4", "FakeT4")):
            with self.subTest(text=text), patch.object(b.subprocess, "check_output", return_value=text):
                with self.assertRaisesRegex(RuntimeError, "TWO_T4"):
                    b.gpu_preflight()


if __name__ == "__main__":
    unittest.main()
