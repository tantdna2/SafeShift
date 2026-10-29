"""CPU fault injection at the actual supervisor boundaries, never GPU proof."""
from contextlib import ExitStack, contextmanager
import hashlib
import os
import io
import json
from pathlib import Path
import subprocess
import sys
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


def python_probe(path, version=(3, 12, 12), *, eligible=True, missing=()):
    modules = {name: ("ModuleNotFoundError" if name in missing else "PASS")
               for name in b.INTERPRETER_PROBE_MODULES}
    essential_missing = tuple(name for name in missing if name in b.ESSENTIAL_STDLIB)
    return {"candidate": str(path), "eligible": eligible and not essential_missing,
            "reason": "PASS" if eligible and not essential_missing
                      else "ESSENTIAL_STDLIB_MISSING:" + ",".join(essential_missing),
            "implementation": "CPython", "version": list(version), "platform": "Linux",
            "machine": "x86_64", "pointer_bits": 64, "executable": str(path),
            "prefix": str(Path(path).parent.parent), "base_prefix": "/usr",
            "modules": modules, "ensurepip": modules["ensurepip"],
            "pip_bootstrap_required": modules["ensurepip"] != "PASS"}


class InterpreterSelectionTests(unittest.TestCase):
    def test_python313_kernel_selects_independent_python312(self):
        candidates = ["/usr/bin/python3.12", "/usr/bin/python3.11", "/usr/bin/python3"]
        def probe(path, env=None):
            if str(path).endswith("3.12"):
                return python_probe(path)
            if str(path).endswith("3.11"):
                return {"candidate": str(path), "eligible": False, "reason": "INTERPRETER_NOT_FOUND"}
            return python_probe(path, (3, 13, 15), eligible=False)
        with patch.object(b, "probe_interpreter", side_effect=probe):
            selected, receipt = b.select_interpreter(candidates=candidates)
        self.assertEqual(selected, Path("/usr/bin/python3.12"))
        self.assertEqual(receipt["selected"]["version"][:2], [3, 12])
        self.assertFalse(receipt["fallback_to_python_313"])

    def test_python312_then_python311_are_allowed_in_policy_order(self):
        for available, expected in (({"/usr/bin/python3.12", "/usr/bin/python3.11"}, "python3.12"),
                                    ({"/usr/bin/python3.11"}, "python3.11")):
            def probe(path, env=None, available=available):
                return python_probe(path, (3, 12, 1) if str(path).endswith("3.12") else (3, 11, 9)) \
                    if str(path) in available else {"candidate": str(path), "eligible": False,
                                                    "reason": "INTERPRETER_NOT_FOUND"}
            with self.subTest(available=available), patch.object(b, "probe_interpreter", side_effect=probe):
                selected, _ = b.select_interpreter(candidates=["/usr/bin/python3.12", "/usr/bin/python3.11"])
                self.assertEqual(selected.name, expected)

    def test_missing_ensurepip_keeps_python312_eligible_for_locked_bootstrap(self):
        def probe(path, env=None):
            if str(path).endswith("3.12"):
                return python_probe(path, (3, 12, 3), missing=("ensurepip",))
            return python_probe(path, (3, 11, 9))
        with patch.object(b, "probe_interpreter", side_effect=probe):
            selected, receipt = b.select_interpreter(candidates=["/usr/bin/python3.12", "/usr/bin/python3.11"])
        self.assertEqual(selected.name, "python3.12")
        self.assertEqual(receipt["selected"]["ensurepip"], "ModuleNotFoundError")
        self.assertTrue(receipt["selected"]["pip_bootstrap_required"])

    def test_missing_venv_still_rejects_python312(self):
        def probe(path, env=None):
            return python_probe(path, missing=("venv",)) if str(path).endswith("3.12") \
                else python_probe(path, (3, 11, 9))
        with patch.object(b, "probe_interpreter", side_effect=probe):
            selected, receipt = b.select_interpreter(candidates=["/usr/bin/python3.12", "/usr/bin/python3.11"])
        self.assertEqual(selected.name, "python3.11")
        self.assertIn("ESSENTIAL_STDLIB_MISSING:venv", receipt["candidates"][0]["reason"])

    def test_missing_and_wrong_version_fail_closed_without_python313(self):
        values = [{"candidate": "/missing", "eligible": False, "reason": "INTERPRETER_NOT_FOUND"},
                  python_probe("/usr/bin/python3", (3, 13, 15), eligible=False)]
        with patch.object(b, "probe_interpreter", side_effect=values):
            with self.assertRaisesRegex(RuntimeError, "NO_QUALIFIED") as caught:
                b.select_interpreter(candidates=["/missing", "/usr/bin/python3"])
        self.assertEqual(len(caught.exception.interpreter_probes), 2)
        self.assertFalse(any(v["eligible"] for v in caught.exception.interpreter_probes))

    def test_requirements_and_runtime_lock_match_for_phi_and_smol(self):
        for key in ("phi", "smolvlm2"):
            value = b.runtime_contract(ROOT, key)
            self.assertEqual(value["pins"]["torch"], "2.6.0+cu124")
            self.assertEqual(value["pins"]["torchvision"], "0.21.0+cu124")
            self.assertEqual(value["python_policy"], ["3.11", "3.12"])
            self.assertEqual(value["pip_bootstrap"]["pip"]["version"], "25.0.1")
            self.assertEqual(value["pip_bootstrap"]["method"],
                             "supervisor-pip-python-local-verified-wheel")

    def test_runtime_lock_or_requirement_source_drift_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            config = repo / "configs/pilot"
            config.mkdir(parents=True)
            (config / "runtime_versions.json").write_bytes((ROOT / "configs/pilot/runtime_versions.json").read_bytes())
            text = (ROOT / "configs/pilot/phi.requirements.txt").read_text(encoding="utf-8")
            (config / "phi.requirements.txt").write_text(text.replace("transformers==4.43.3",
                                                                       "transformers==4.51.3"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "RUNTIME_LOCK_MISMATCH"):
                b.runtime_contract(repo, "phi")


class PipBootstrapTests(unittest.TestCase):
    def bootstrap_pin(self, payload=b"SYNTHETIC_VERIFIED_PIP_WHEEL"):
        return {"pip": {"url": "https://files.pythonhosted.org/synthetic.whl",
                        "filename": "synthetic.whl", "sha256": hashlib.sha256(payload).hexdigest(),
                        "size_bytes": len(payload), "provenance": "https://pypi.org/synthetic"}}

    def response(self, payload, url):
        stream = io.BytesIO(payload)
        stream.status = 200
        stream.geturl = lambda: url
        stream.headers = {"Content-Length": str(len(payload))}
        return stream

    def test_verified_exact_wheel_is_persisted_for_local_only_install(self):
        payload = b"SYNTHETIC_VERIFIED_PIP_WHEEL"
        pin = self.bootstrap_pin(payload)
        with tempfile.TemporaryDirectory() as d, \
                patch.object(b, "pip_bootstrap_contract", return_value=pin), \
                patch.object(b, "urlopen", return_value=self.response(payload, pin["pip"]["url"])):
            wheel, receipt = b.fetch_pip_bootstrap(ROOT, d)
            self.assertEqual(wheel.read_bytes(), payload)
            self.assertEqual(receipt["status"], "PASS")
            self.assertEqual(receipt["actual_sha256"], pin["pip"]["sha256"])

    def test_wrong_pip_wheel_hash_blocks_with_actual_and_expected_evidence(self):
        payload = b"SYNTHETIC_TAMPERED_PIP_WHEEL"
        pin = self.bootstrap_pin(b"SYNTHETIC_EXPECTED_PIP_WHEEL")
        pin["pip"]["size_bytes"] = len(payload)
        with tempfile.TemporaryDirectory() as d, \
                patch.object(b, "pip_bootstrap_contract", return_value=pin), \
                patch.object(b, "urlopen", return_value=self.response(payload, pin["pip"]["url"])):
            with self.assertRaisesRegex(ValueError, "CHECKSUM_MISMATCH") as caught:
                b.fetch_pip_bootstrap(ROOT, d)
        receipt = caught.exception.pip_bootstrap_receipt
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertEqual(receipt["expected_sha256"], pin["pip"]["sha256"])
        self.assertEqual(receipt["actual_sha256"], hashlib.sha256(payload).hexdigest())

    def test_bootstrap_command_targets_worker_and_never_resolves_an_index(self):
        command = b.pip_bootstrap_command("/scratch/venv/bin/python", ROOT, "/scratch/wheel/pip.whl")
        self.assertEqual(Path(command[0]).resolve(), Path(sys.executable).resolve())
        self.assertEqual(command[command.index("--python") + 1], "/scratch/venv/bin/python")
        for option in ("--isolated", "--no-index", "--require-hashes", "--no-deps"):
            self.assertIn(option, command)

    def test_worker_pip_identity_rejects_python313_path_leakage(self):
        with tempfile.TemporaryDirectory() as d:
            runtime = Path(d) / "venv-py312"
            value = {"version": "25.0.1", "metadata_version": "25.0.1",
                     "pip_file": "/kernel/python3.13/site-packages/pip/__init__.py",
                     "distribution_root": str(runtime / "lib/python3.12/site-packages"),
                     "executable": str(runtime / "bin/python"), "prefix": str(runtime),
                     "base_prefix": "/usr", "python_version": [3, 12, 3]}
            process = subprocess.CompletedProcess([], 0, json.dumps(value) + "\n", "")
            with patch.object(b.subprocess, "run", return_value=process), \
                    self.assertRaisesRegex(RuntimeError, "WORKER_PIP_IDENTITY_MISMATCH") as caught:
                b.inspect_worker_pip(runtime / "bin/python", runtime, "25.0.1", {})
        self.assertTrue(caught.exception.worker_pip_receipt["python313_path_detected"])

    @unittest.skipUnless(os.environ.get("SAFESHIFT_REAL_PIP_BOOTSTRAP") == "1",
                         "opt-in real network/venv pip --python rehearsal")
    def test_real_verified_wheel_bootstraps_pip_free_venv(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            runtime = root / "venv"
            subprocess.run([sys.executable, "-I", "-B", "-m", "venv", "--without-pip", "--copies",
                            str(runtime)], check=True)
            worker = runtime / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            wheel, receipt = b.fetch_pip_bootstrap(ROOT, root)
            self.assertEqual(receipt["status"], "PASS")
            controller = b.pip_controller_probe(dict(os.environ))
            self.assertGreaterEqual(tuple(map(int, controller["pip_version"].split(".")))[:2], (22, 3))
            subprocess.run(b.pip_bootstrap_command(worker, ROOT, wheel), check=True)
            inspected = b.inspect_worker_pip(worker, runtime, "25.0.1", dict(os.environ))
            self.assertFalse(inspected["python313_path_detected"])


class ScratchRootTests(unittest.TestCase):
    def test_absent_root_created_under_existing_parent_with_restrictive_mode(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            work = parent / "working"
            work.mkdir()
            root = parent / "tmp"
            self.assertEqual(b.provision_scratch_root(work, root), root)
            self.assertTrue(root.is_dir())
            self.assertEqual(list(root.iterdir()), [])
            if os.name == "posix":
                self.assertEqual(root.stat().st_mode & 0o777, 0o700)

    def test_existing_root_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            work, root = parent / "working", parent / "tmp"
            work.mkdir()
            root.mkdir()
            write(root / "other-session.json", {"SYNTHETIC": True})
            before = root.stat()
            self.assertEqual(b.provision_scratch_root(work, root), root)
            self.assertEqual(root.stat().st_ino, before.st_ino)
            self.assertEqual(root.stat().st_mode, before.st_mode)
            self.assertTrue((root / "other-session.json").is_file())

    def test_concurrent_eexist_revalidates_directory_and_rejects_file(self):
        for directory in (True, False):
            with self.subTest(directory=directory), tempfile.TemporaryDirectory() as d:
                parent = Path(d)
                work, root = parent / "working", parent / "tmp"
                work.mkdir()
                original = os.mkdir
                def concurrent(path, mode=0o777, *, dir_fd=None):
                    if directory:
                        if dir_fd is None:
                            original(path, mode)
                        else:
                            original(path, mode, dir_fd=dir_fd)
                    else:
                        root.write_bytes(b"SYNTHETIC_CONCURRENT_FILE")
                    raise FileExistsError(errno.EEXIST, "concurrent creator")
                with patch.object(b.os, "mkdir", side_effect=concurrent):
                    if directory:
                        self.assertEqual(b.provision_scratch_root(work, root), root)
                    else:
                        with self.assertRaisesRegex(ValueError, "NOT_DIRECTORY"):
                            b.provision_scratch_root(work, root)

    def test_denied_creation_and_invalid_roots_create_no_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            work, root = parent / "working", parent / "tmp"
            work.mkdir()
            with patch.object(b.os, "mkdir", side_effect=PermissionError(errno.EACCES, "denied")):
                with self.assertRaises(PermissionError):
                    b.provision_scratch_root(work, root)
            for invalid in (Path("tmp"), parent / "other", work / "tmp", parent / "other/../tmp", work):
                with self.subTest(root=str(invalid)), self.assertRaisesRegex(ValueError, "SIBLING_TMP"):
                    b.provision_scratch_root(work, invalid)
            self.assertEqual(list(parent.iterdir()), [work])

    def test_parent_alias_and_existing_nondirectory_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            work, root = parent / "working", parent / "tmp"
            work.mkdir()
            original = Path.is_symlink
            with patch.object(Path, "is_symlink", lambda p: p == parent or original(p)):
                with self.assertRaisesRegex(ValueError, "ALIAS"):
                    b.provision_scratch_root(work, root)
            self.assertFalse(root.exists())
            root.write_bytes(b"SYNTHETIC_FILE")
            with self.assertRaisesRegex(ValueError, "NOT_DIRECTORY"):
                b.provision_scratch_root(work, root)
            self.assertEqual(root.read_bytes(), b"SYNTHETIC_FILE")

    @unittest.skipUnless(os.name == "posix", "real directory symlink requires Linux")
    def test_real_root_and_parent_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            work, root, target = parent / "working", parent / "tmp", parent / "target"
            work.mkdir()
            target.mkdir()
            root.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "ALIAS"):
                b.provision_scratch_root(work, root)
            alias = parent / "alias"
            alias.symlink_to(parent, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "ALIAS"):
                b.provision_scratch_root(alias / "working", alias / "tmp")
            self.assertEqual(list(target.iterdir()), [])

    @unittest.skipUnless(os.name == "posix", "directory descriptor check requires Linux")
    def test_parent_or_root_identity_mismatch_fails_closed(self):
        for changed in ("parent", "root"):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as d:
                parent = Path(d)
                work, root = parent / "working", parent / "tmp"
                work.mkdir()
                root.mkdir()
                original = os.fstat
                calls = []
                def mismatch(fd):
                    info = original(fd)
                    calls.append(fd)
                    if (changed == "parent" and len(calls) == 1) or (changed == "root" and len(calls) == 2):
                        return SimpleNamespace(st_dev=info.st_dev + 1, st_ino=info.st_ino)
                    return info
                with patch.object(b.os, "fstat", side_effect=mismatch):
                    with self.assertRaisesRegex(ValueError, "CHANGED"):
                        b.provision_scratch_root(work, root)

    def test_missing_root_preflight_shared_filesystem_blocks_with_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            work, root = parent / "working", parent / "tmp"
            work.mkdir()
            observation = {"device": 1, "free_bytes": int(19.5 * GIB)}
            with patch.object(b, "filesystem_usage", return_value=observation), \
                 patch.object(b.subprocess, "run", side_effect=AssertionError("NO_WORKER")):
                out = b.storage_preflight(work, root)
            receipt = read(out / "storage_preflight.json")
            self.assertFalse(receipt["admitted"])
            self.assertEqual(receipt["reason"], "INSUFFICIENT_FILESYSTEM_FREE")
            self.assertEqual(receipt["filesystems"][0]["required_bytes"], 32 * GIB)
            self.assertEqual(list(root.iterdir()), [])

    def test_missing_root_creation_denied_retains_preflight_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            work, root = parent / "working", parent / "tmp"
            work.mkdir()
            original = os.mkdir
            def denied(path, mode=0o777, *, dir_fd=None):
                if path == "tmp" or Path(path) == root:
                    raise PermissionError(errno.EACCES, "root creation denied")
                return original(path, mode) if dir_fd is None else original(path, mode, dir_fd=dir_fd)
            with patch.object(b.os, "mkdir", side_effect=denied):
                out = b.storage_preflight(work, root)
            receipt = read(out / "storage_preflight.json")
            self.assertFalse(receipt["admitted"])
            self.assertEqual(receipt["error"]["errno"], errno.EACCES)
            self.assertFalse(root.exists())

    def test_existing_root_without_write_or_search_permission_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            work, root = parent / "working", parent / "tmp"
            work.mkdir()
            root.mkdir()
            with patch.object(b.os, "access", return_value=False):
                with self.assertRaises(PermissionError):
                    b.provision_scratch_root(work, root)

    def test_new_root_cleanup_failure_keeps_receipt_and_owned_session(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            work, root = parent / "working", parent / "tmp"
            work.mkdir()
            with patch.object(b, "storage_admission", return_value={"admitted": True, "reason": "SYNTHETIC"}), \
                 patch.object(b, "cleanup_scratch", side_effect=OSError("cleanup denied")):
                out = b.storage_preflight(work, root)
            receipt = read(out / "storage_preflight.json")
            self.assertFalse(receipt["admitted"])
            self.assertIn("cleanup denied", receipt["scratch_cleanup_error"])
            sessions = list(root.iterdir())
            self.assertEqual(len(sessions), 1)
            self.assertEqual(read(sessions[0] / "location.json")["scope"], "kaggle_tmp")


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
            work, scratch = root / "working", root / "tmp"
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

    def test_environment_preflight_consumes_no_grant_attempt_or_gpu(self):
        for key in ("phi", "smolvlm2"):
            with self.subTest(model=key), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                work, scratch = root / "working", root / "tmp"
                work.mkdir()
                scratch.mkdir()
                runtime_receipt = {"status": "PASS", "selected_python": "/usr/bin/python3.12",
                                   "worker_python": str(scratch / "venv-py312/bin/python"),
                                   "kernel_python": "/usr/bin/python3", "kernel_worker_separated": True}
                with patch.object(b, "storage_admission", return_value={"admitted": True, "reason": "SYNTHETIC"}), \
                     patch.object(b, "prepare_runtime", return_value=(Path(runtime_receipt["worker_python"]), {}, runtime_receipt)), \
                     patch.object(b, "discover", side_effect=AssertionError("NO_GRANT_OR_DATA")), \
                     patch.object(b, "gpu_preflight", side_effect=AssertionError("NO_GPU")):
                    output = b.environment_preflight(key, source_digest(ROOT), ROOT, work, scratch)
                receipt = read(output / "environment_preflight.json")
                self.assertEqual(receipt["status"], "PASS")
                self.assertFalse(receipt["attempt_consumed"])
                self.assertFalse(receipt["grant_read"])
                self.assertEqual(receipt["gpu"], "NOT_CALLED")
                self.assertFalse((work / "data/processed/three_vlm_attempts").exists())
                self.assertTrue(output.with_suffix(".zip").is_file())
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
            work, scratch = root / "working", root / "tmp"
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
            work, scratch = root / "working", root / "tmp"
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

    def test_scratch_environment_drops_notebook_python_paths(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {
                "PYTHONPATH": "/notebook/python3.13/site-packages",
                "PYTHONHOME": "/notebook/python3.13", "PYTHONUSERBASE": "/notebook/user"}):
            scratch, env = b.prepare_scratch(d, "isolated")
            self.assertNotIn("PYTHONPATH", env)
            self.assertNotIn("PYTHONHOME", env)
            self.assertNotIn("PYTHONUSERBASE", env)
            self.assertEqual(env["PYTHONNOUSERSITE"], "1")
            b.cleanup_scratch(d, scratch, "isolated")

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
        scratch_root = root / "tmp"
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
        def interpreter_probe(python, env=None):
            candidate = Path(python)
            in_venv = candidate.name == "python" and candidate.parent.name == "bin"
            prefix = candidate.parent.parent if in_venv else Path("/synthetic/cpython312")
            return {"candidate": str(candidate), "eligible": True, "reason": "PASS",
                    "implementation": "CPython", "version": [3, 12, 12], "platform": "Linux",
                    "machine": "x86_64", "pointer_bits": 64, "executable": str(candidate),
                    "prefix": str(prefix), "base_prefix": "/synthetic/base-python312",
                    "modules": {name: ("ModuleNotFoundError" if name == "ensurepip" else "PASS")
                                for name in b.INTERPRETER_PROBE_MODULES},
                    "ensurepip": "ModuleNotFoundError", "pip_bootstrap_required": True}
        loader = patches.enter_context(patch.object(b, "load_bundle", return_value=(p, p["main"])))
        patches.enter_context(patch.object(b, "interpreter_candidates", return_value=[sys.executable]))
        patches.enter_context(patch.object(b, "probe_interpreter", side_effect=interpreter_probe))
        patches.enter_context(patch.object(b, "pip_controller_probe", return_value={
            "pip_version": "25.0.1", "method": "pip --python", "worker_package_installation": False}))
        patches.enter_context(patch.object(b, "fetch_pip_bootstrap", side_effect=lambda repo, scratch: (
            Path(scratch) / "pip-bootstrap/pip-25.0.1-py3-none-any.whl",
            {"status": "PASS", "actual_sha256": "a" * 64, "expected_sha256": "a" * 64})))
        patches.enter_context(patch.object(b, "inspect_worker_pip", return_value={
            "version": "25.0.1", "metadata_version": "25.0.1", "python_version": [3, 12, 12],
            "python313_path_detected": False}))
        patches.enter_context(patch.object(b, "validate_runtime_environment", return_value={
            "identity": {"version": [3, 12], "isolated_from_notebook_python": True},
            "software": {"status": "SYNTHETIC_CPU_ABI_PASS"}}))
        patches.enter_context(patch.object(b, "storage_admission", return_value={"admitted": disk_ok, "SYNTHETIC": True}))
        patches.enter_context(patch.object(b.subprocess, "run", side_effect=run))
        patches.enter_context(patch.object(b.subprocess, "check_output", side_effect=lambda cmd, **kw: GPU if cmd[0] == "nvidia-smi" else "SYNTHETIC_FREEZE\n"))
        yield root, inputs, work, p, g, calls, loader


class SupervisorTests(unittest.TestCase):
    def launch(self, case, key="phi"):
        _, inputs, work, _, g, _, _ = case
        return b.launch(key, g["source_sha256"], ROOT, inputs, work, scratch_root=case[0] / "tmp")

    def test_pilot_creates_missing_root_using_shared_provisioner(self):
        for key in ("phi", "smolvlm2"):
            with self.subTest(model=key), supervisor_case(key=key) as case:
                root = case[0] / "tmp"
                root.rmdir()  # Empty synthetic fixture, never a runtime root.
                with patch.object(b, "provision_scratch_root", wraps=b.provision_scratch_root) as provision:
                    out = self.launch(case, key)
                provision.assert_called_once_with(case[2], root)
                self.assertTrue(root.is_dir())
                self.assertEqual(list(root.iterdir()), [])
                self.assertTrue(out.with_suffix(".zip").is_file())
                worker = next(cmd for cmd, _ in case[5] if "safeshift.pilot.runner" in cmd)
                requirement_install = next(cmd for cmd, _ in case[5]
                                           if any(Path(str(part)).name == f"{key}.requirements.txt"
                                                  for part in cmd))
                self.assertEqual(Path(requirement_install[-1]).name, f"{key}.requirements.txt")
                self.assertEqual(worker[0], read(out / "runtime_preflight.json")["worker_python"])

    def test_real_launch_orders_cuda_install_before_requirements_and_check(self):
        with supervisor_case() as case:
            out = self.launch(case)
            commands = [c for c, _ in case[5]]
            runtime = commands[0][-1]
            expected = b.dependency_commands(Path(runtime) / "bin/python", ROOT, "phi")
            self.assertEqual(commands[4:7], expected)
            self.assertEqual(commands[0][0], sys.executable)
            self.assertEqual(commands[0][1:8],
                             ["-I", "-B", "-m", "venv", "--without-pip", "--copies", runtime])
            self.assertIn("find_spec('pip') is None", commands[1][-1])
            self.assertEqual(Path(commands[2][0]).resolve(), Path(sys.executable).resolve())
            self.assertEqual(commands[2][commands[2].index("--python") + 1], str(Path(runtime) / "bin/python"))
            self.assertIn("--no-index", commands[2])
            self.assertEqual(commands[3][-2:], ["--isolated", "--version"])
            self.assertIn("https://download.pytorch.org/whl/cu124", commands[4])
            self.assertIn("torch==2.6.0+cu124", commands[4])
            self.assertIn("torchvision==0.21.0+cu124", commands[4])
            self.assertEqual(commands[6][-1], "check")
            self.assertEqual(commands[-1][-2:], ["--mode", "PILOT"])
            for _, kwargs in case[5]:
                self.assertTrue(Path(kwargs["env"]["TMPDIR"]).is_relative_to(case[0] / "tmp"))
            self.assertEqual(case[5][-1][1]["env"]["CUDA_VISIBLE_DEVICES"], "0")
            runtime_receipt = read(out / "runtime_preflight.json")
            self.assertEqual(case[5][-1][1]["env"]["SAFESHIFT_WORKER_PYTHON"],
                             runtime_receipt["worker_python"])
            self.assertEqual(case[5][-1][1]["env"]["SAFESHIFT_RUNTIME_ROOT"],
                             runtime_receipt["runtime_root"])
            self.assertEqual(runtime_receipt["status"], "PASS")
            self.assertFalse(runtime_receipt["attempt_consumed"])
            self.assertTrue(runtime_receipt["interpreter_selection"]["selected"]["pip_bootstrap_required"])
            self.assertEqual(runtime_receipt["pip_bootstrap"]["status"], "PASS")
            self.assertEqual(runtime_receipt["worker_pip"]["version"], "25.0.1")
            self.assertTrue(read(out / "environment_preflight.json")["ready_for_attempt_consumption"])
            ledger = case[2] / "data/processed/three_vlm_attempts" / case[4]["attempt_id"]
            self.assertTrue(read(ledger)["consumed_after_cpu_preflight"])
            self.assertTrue(out.with_suffix(".zip").is_file())

    def test_insufficient_storage_blocks_installer_and_exports_receipt(self):
        with supervisor_case(disk_ok=False) as case:
            out = self.launch(case)
            self.assertEqual(case[5], [])
            self.assertEqual(read(out / "supervisor_failure.json")["stage"], "storage")
            self.assertFalse(read(out / "storage_admission.json")["admitted"])
            self.assertEqual(len(read(out / "recovered_report/comparison.json")), 160)
            self.assertTrue(out.with_suffix(".zip").is_file())

    def assert_hardware_blocked_without_consumption(self, case, out):
        failure = read(out / "supervisor_failure.json")
        self.assertEqual((failure["status"], failure["stage"]), ("BLOCKED", "hardware"))
        self.assertFalse(failure["attempt_consumed"])
        self.assertFalse(read(out / "session.json")["attempt_consumed"])
        self.assertFalse((case[2] / "data/processed/three_vlm_attempts" / case[4]["attempt_id"]).exists())
        environment = read(out / "environment_preflight.json")
        self.assertEqual(environment["status"], "BLOCKED")
        self.assertFalse(environment["ready_for_attempt_consumption"])
        self.assertEqual(environment["cuda"], "NOT_CALLED")
        self.assertEqual(read(out / "runtime_preflight.json")["status"], "PASS")
        self.assertFalse(any("safeshift.pilot.runner" in command for command, _ in case[5]))
        self.assertFalse((out / "worker.log").exists())
        self.assertEqual(len(read(out / "recovered_report/comparison.json")), 160)
        self.assertTrue(out.with_suffix(".zip").is_file())
        return import_archive(out.with_suffix(".zip"), case[0] / "recovered")

    def check_hardware_failure(self, *, observation=None, error=None):
        with supervisor_case() as case:
            def query(command, **kwargs):
                if command[0] == "nvidia-smi":
                    if error is not None:
                        raise error
                    return observation
                return "SYNTHETIC_FREEZE\n"
            with patch.object(b.subprocess, "check_output", side_effect=query):
                out = self.launch(case)
            recovered = self.assert_hardware_blocked_without_consumption(case, out)
            receipt = read(recovered / "gpu_preflight.json")
            self.assertEqual(receipt["status"], "BLOCKED")
            self.assertFalse(receipt["attempt_consumed"])
            self.assertEqual(receipt["method"], "nvidia-smi")
            self.assertEqual(receipt["cuda_validation"], "NOT_RUN")
            self.assertEqual(receipt["model_execution"], "NOT_RUN")
            if error is None:
                self.assertEqual(receipt["nvidia_smi_output"], observation)
            else:
                self.assertEqual(receipt["error"]["type"], type(error).__name__)
            return receipt

    def test_missing_gpu_blocks_without_consuming_attempt(self):
        for observation in ("", GPU.splitlines(True)[0]):
            with self.subTest(observation=observation):
                self.check_hardware_failure(observation=observation)

    def test_wrong_gpu_blocks_without_consuming_attempt(self):
        self.check_hardware_failure(observation=GPU.replace("Tesla T4", "NVIDIA P100"))

    def test_gpu0_insufficient_vram_blocks_without_consuming_attempt(self):
        receipt = self.check_hardware_failure(observation=GPU.replace("14800", "14335", 1))
        self.assertEqual(receipt["physical_gpus"][0][2], "14335")
        self.assertIn("GPU0_FREE_BELOW_14_GIB", receipt["error"]["message"])

    def test_nvidia_smi_command_errors_block_and_preserve_diagnostics(self):
        errors = (FileNotFoundError(errno.ENOENT, "SYNTHETIC_NVIDIA_SMI_MISSING"),
                  subprocess.CalledProcessError(9, ["nvidia-smi"], output="SYNTHETIC_DRIVER_FAILURE\n"),
                  subprocess.TimeoutExpired(["nvidia-smi"], 60, output=b"SYNTHETIC_TIMEOUT\n"))
        for error in errors:
            with self.subTest(error=type(error).__name__):
                receipt = self.check_hardware_failure(error=error)
                self.assertEqual(receipt["returncode"], getattr(error, "returncode", None))
                if getattr(error, "output", None) is not None:
                    expected = error.output.decode() if isinstance(error.output, bytes) else error.output
                    self.assertEqual(receipt["nvidia_smi_output"], expected)

    def test_gpu_receipt_write_failure_blocks_and_retains_partial_evidence(self):
        actual_write = b.write
        for partial in (False, True):
            with self.subTest(partial=partial), supervisor_case() as case:
                def fail_receipt(path, value):
                    if Path(path).name == "gpu_preflight.json":
                        if partial:
                            Path(path).write_bytes(b'SYNTHETIC_TORN_RECEIPT')
                        raise OSError(errno.ENOSPC, "SYNTHETIC_GPU_RECEIPT_WRITE_FAILURE")
                    return actual_write(path, value)
                with patch.object(b, "write", side_effect=fail_receipt):
                    out = self.launch(case)
                recovered = self.assert_hardware_blocked_without_consumption(case, out)
                failure = read(recovered / "supervisor_failure.json")
                self.assertIn("GPU_RECEIPT_WRITE_FAILURE", failure["message"])
                self.assertEqual(failure["gpu_preflight"]["nvidia_smi_output"], GPU)
                self.assertEqual(failure["gpu_preflight"]["status"], "PASS")
                if partial:
                    self.assertEqual((recovered / "gpu_preflight.json").read_bytes(), b'SYNTHETIC_TORN_RECEIPT')
                else:
                    self.assertFalse((recovered / "gpu_preflight.json").exists())

    def test_cpu_then_hardware_receipts_then_exclusive_ledger_then_worker(self):
        actual_write = b.write
        for key in ("phi", "smolvlm2"):
            with self.subTest(model=key), supervisor_case(key=key) as case:
                events = []
                ledger = case[2] / "data/processed/three_vlm_attempts" / case[4]["attempt_id"]
                def observed_write(path, value):
                    result = actual_write(path, value)
                    name = "ledger" if Path(path) == ledger else Path(path).name
                    if name in ("runtime_preflight.json", "gpu_preflight.json", "environment_preflight.json", "ledger"):
                        events.append(name)
                    return result
                def query(command, **kwargs):
                    if command[0] == "nvidia-smi":
                        self.assertFalse(ledger.exists())
                        self.assertEqual(events, ["runtime_preflight.json"])
                        events.append("nvidia-smi")
                        return GPU
                    return "SYNTHETIC_FREEZE\n"
                def worker(out):
                    self.assertTrue(ledger.is_file())
                    self.assertEqual(read(out / "gpu_preflight.json")["status"], "PASS")
                    self.assertFalse(read(out / "gpu_preflight.json")["attempt_consumed"])
                    events.append("worker")
                # The fixture's process boundary invokes only this synthetic callback.
                original_run = b.subprocess.run.side_effect
                def process(command, **kwargs):
                    if "safeshift.pilot.runner" in command:
                        worker(Path(command[command.index("--output") + 1]))
                    return original_run(command, **kwargs)
                with patch.object(b, "write", side_effect=observed_write), \
                     patch.object(b.subprocess, "check_output", side_effect=query), \
                     patch.object(b.subprocess, "run", side_effect=process):
                    out = self.launch(case, key)
                self.assertEqual(events, ["runtime_preflight.json", "nvidia-smi", "gpu_preflight.json",
                                          "environment_preflight.json", "ledger", "worker"])
                consumption = read(ledger)
                self.assertTrue(consumption["consumed_after_gpu_preflight"])
                self.assertEqual(consumption["gpu_preflight_sha256"], sha(out / "gpu_preflight.json"))
                self.assertEqual(read(out / "environment_preflight.json")["gpu_preflight_sha256"],
                                 consumption["gpu_preflight_sha256"])
                self.assertTrue(read(out / "session.json")["attempt_consumed"])

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
            failure = read(out / "supervisor_failure.json")
            self.assertEqual(failure["stage"], "cpu_runtime_preflight")
            self.assertFalse(failure["attempt_consumed"])
            self.assertTrue((out / "setup.log").is_file())
            self.assertFalse((out / "worker.log").exists())
            self.assertEqual(read(out / "environment_preflight.json")["status"], "BLOCKED")
            self.assertEqual(read(out / "runtime_preflight.json")["status"], "BLOCKED")
            self.assertFalse((case[2] / "data/processed/three_vlm_attempts" / case[4]["attempt_id"]).exists())
            self.assertTrue(out.with_suffix(".zip").is_file())

    def test_disk_full_during_install_exports_failure_and_no_worker(self):
        with supervisor_case() as case:
            with patch.object(b.subprocess, "run", side_effect=OSError(errno.ENOSPC, "disk full")):
                out = self.launch(case)
            self.assertEqual(read(out / "supervisor_failure.json")["stage"], "cpu_runtime_preflight")
            self.assertFalse(read(out / "supervisor_failure.json")["attempt_consumed"])
            self.assertFalse((out / "worker.log").exists())
            self.assertFalse((case[2] / "data/processed/three_vlm_attempts" / case[4]["attempt_id"]).exists())
            self.assertTrue(out.with_suffix(".zip").is_file())

    def test_missing_pip_bootstrap_blocks_both_models_with_evidence(self):
        for key in ("phi", "smolvlm2"):
            with self.subTest(model=key), supervisor_case(key=key) as case:
                error = FileNotFoundError(errno.ENOENT, "SYNTHETIC_BOOTSTRAP_SOURCE_MISSING")
                error.pip_bootstrap_receipt = {"status": "BLOCKED", "expected_sha256": "a" * 64,
                                               "actual_sha256": None, "received_size_bytes": 0}
                with patch.object(b, "fetch_pip_bootstrap", side_effect=error):
                    out = self.launch(case, key)
                receipt = read(out / "runtime_preflight.json")
                self.assertEqual(receipt["status"], "BLOCKED")
                self.assertFalse(receipt["attempt_consumed"])
                self.assertEqual(receipt["pip_bootstrap"]["status"], "BLOCKED")
                self.assertFalse((case[2] / "data/processed/three_vlm_attempts" /
                                  case[4]["attempt_id"]).exists())
                self.assertTrue(out.with_suffix(".zip").is_file())

    def test_wrong_bootstrap_hash_blocks_before_dependency_install(self):
        with supervisor_case() as case:
            error = ValueError("PINNED_PIP_BOOTSTRAP_CHECKSUM_MISMATCH")
            error.pip_bootstrap_receipt = {"status": "BLOCKED", "expected_sha256": "a" * 64,
                                           "actual_sha256": "b" * 64, "received_size_bytes": 1841526}
            with patch.object(b, "fetch_pip_bootstrap", side_effect=error):
                out = self.launch(case)
            receipt = read(out / "runtime_preflight.json")
            self.assertEqual(receipt["pip_bootstrap"]["actual_sha256"], "b" * 64)
            self.assertEqual(receipt["error"]["message"], "PINNED_PIP_BOOTSTRAP_CHECKSUM_MISMATCH")
            self.assertFalse(any("torch==2.6.0+cu124" in command for command, _ in case[5]))

    def test_dependency_install_failure_blocks_before_ledger(self):
        with supervisor_case() as case:
            original = b.subprocess.run.side_effect
            def process(command, **kwargs):
                if "torch==2.6.0+cu124" in command:
                    return subprocess.CompletedProcess(command, 7)
                return original(command, **kwargs)
            with patch.object(b.subprocess, "run", side_effect=process):
                out = self.launch(case)
            self.assertEqual(read(out / "runtime_preflight.json")["stage"], "dependency_0")
            self.assertFalse(read(out / "supervisor_failure.json")["attempt_consumed"])
            self.assertFalse((case[2] / "data/processed/three_vlm_attempts" /
                              case[4]["attempt_id"]).exists())

    def test_python313_worker_pip_leak_blocks_before_ledger(self):
        with supervisor_case() as case:
            error = RuntimeError("WORKER_PIP_IDENTITY_MISMATCH")
            error.worker_pip_receipt = {"version": "25.0.1",
                                        "pip_file": "/kernel/python3.13/site-packages/pip/__init__.py",
                                        "python313_path_detected": True}
            with patch.object(b, "inspect_worker_pip", side_effect=error):
                out = self.launch(case)
            receipt = read(out / "runtime_preflight.json")
            self.assertTrue(receipt["worker_pip"]["python313_path_detected"])
            self.assertFalse(read(out / "supervisor_failure.json")["attempt_consumed"])
            self.assertFalse((case[2] / "data/processed/three_vlm_attempts" /
                              case[4]["attempt_id"]).exists())

    def test_runtime_receipt_write_failure_blocks_and_still_exports(self):
        actual_write = b.write
        with supervisor_case() as case:
            def fail_runtime_receipt(path, value):
                if Path(path).name == "runtime_preflight.json":
                    raise OSError(errno.ENOSPC, "SYNTHETIC_RUNTIME_RECEIPT_WRITE_FAILURE")
                return actual_write(path, value)
            with patch.object(b, "write", side_effect=fail_runtime_receipt):
                out = self.launch(case)
            self.assertFalse((out / "runtime_preflight.json").exists())
            self.assertEqual(read(out / "supervisor_failure.json")["stage"], "cpu_runtime_preflight")
            self.assertFalse(read(out / "supervisor_failure.json")["attempt_consumed"])
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
