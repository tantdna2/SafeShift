"""Environment-first negative/partial checks. All GPU/worker calls are doubles."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import platform
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

from safeshift.candidates import train_preflight as p, train_contract as c, train_runtime as rt, train_owner as owner
from safeshift.candidates.source import ROOT
from safeshift.pilot.artifacts import read, write, verify_archive
from test_candidate160_environment import synthetic_child_evidence


class PreflightAdmissionTests(unittest.TestCase):
    def assert_no_attempt(self, root):
        self.assertFalse(list(root.glob("**/owner_slot*")))
        self.assertFalse(list(root.glob("**/consumption.json")))
        for result in root.glob("*.preflight-result.json"):
            value = read(result)
            self.assertIs(value["attempt_consumed"], False)
            self.assertIs(value["owner_slot_created"], False)
            self.assertEqual(value["native_calls"], 0)

    def test_inventory_uses_stdlib_observations_and_excludes_secrets(self):
        with patch.dict(os.environ, {"HF_TOKEN": "SYNTHETIC_SECRET_NOT_TO_EXPORT", "CUDA_VISIBLE_DEVICES": "TEST_VISIBILITY"}), \
             patch.object(p.platform, "system", return_value="Linux"), \
             patch.object(p.platform, "machine", return_value="x86_64"), \
             patch.object(p.subprocess, "run", side_effect=AssertionError("NO_PROCESS_OBSERVATION")):
            value = p.environment_observation()
        self.assertEqual(value["kernel"]["version"], platform.python_version())
        self.assertEqual(value["kernel"]["pointer_bits"], struct.calcsize("P")*8)
        self.assertEqual(value["inherited_cuda_visible_devices"], "TEST_VISIBILITY")
        self.assertNotIn("SYNTHETIC_SECRET", json.dumps(value))
        self.assertEqual(value["worker"]["version"], "3.11.9")

    def test_pass_levels_distinguish_software_gpu_weights_inference_and_science(self):
        checks = {name: {"status": "NOT_RUN"} for name in p.REQUIRED}
        for name in ("environment", "runtime_setup", "software_cpu", "cpu_native"):
            checks[name]["status"] = "PASS"
        levels = p.evidence_levels(checks)
        self.assertEqual(levels["ENVIRONMENT_OBSERVED"], "PASS")
        self.assertEqual(levels["CPU_SOFTWARE_PASS"], "PASS")
        self.assertEqual(levels["LIVE_GPU_PREFLIGHT_PASS"], "NOT_RUN")
        checks["gpu_driver"]["status"] = "BLOCKED"
        self.assertEqual(p.evidence_levels(checks)["LIVE_GPU_PREFLIGHT_PASS"], "BLOCKED")
        for name in ("gpu_driver", "cuda_child"):
            checks[name]["status"] = "PASS"
        levels = p.evidence_levels(checks)
        self.assertEqual(levels["LIVE_GPU_PREFLIGHT_PASS"], "PASS")
        self.assertEqual(levels["WEIGHTS_LOADED"], "NOT_RUN")
        self.assertEqual(levels["INFERENCE_VERIFIED"], "NOT_RUN")
        self.assertEqual(levels["SCIENTIFIC_QUALIFIED"], "UNVERIFIED")

    def test_source_failure_or_expired_budget_stops_before_inputs_software_gpu(self):
        for fault in ("source", "ref", "time"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                root = Path(d)
                for target in ("manifest", "checkpoint", "environment_observation"):
                    stack.enter_context(patch.object(p, target, side_effect=AssertionError("NO_INPUT_OR_HOST_READ")))
                stack.enter_context(patch.object(rt, "prepare_runtime", side_effect=AssertionError("NO_INSTALL")))
                stack.enter_context(patch.object(rt, "hardware", side_effect=AssertionError("NO_GPU")))
                if fault == "time":
                    stack.enter_context(patch.object(owner, "MAX_SECONDS", 0))
                out = p.launch_preflight("internvl35", "0"*64 if fault == "source" else c.source_hash(), ROOT,
                    "invalid" if fault == "ref" else "a"*40, inputs=root/"absent", work=root/"out")
                report = read(Path(str(out)+".preflight-result.json"))
                self.assertEqual(report["status"], "BLOCKED")
                self.assertEqual(report["checks"]["source_binding"]["status"], "BLOCKED")
                self.assertEqual(report["checks"]["runtime_setup"]["status"], "NOT_RUN")
                verify_archive(Path(str(out)+".zip"))
                self.assert_no_attempt(root/"out")

    def test_interrupt_preserves_partial_report_and_never_continues_gpu(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with patch.object(p, "environment_observation", side_effect=KeyboardInterrupt()), \
                 patch.object(rt, "hardware", side_effect=AssertionError("NO_GPU_AFTER_INTERRUPT")), \
                 self.assertRaises(KeyboardInterrupt):
                p.launch_preflight("internvl35", c.source_hash(), ROOT, "a"*40, inputs=root/"input", work=root/"out")
            report = read(next((root/"out").glob("*.preflight-result.json")))
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["checks"]["orchestration"]["error"]["type"], "KeyboardInterrupt")
            self.assert_no_attempt(root/"out")

    def test_real_checkpoint_admission_missing_duplicate_wrong_mount_source_or_weights_blocks(self):
        for key in c.KEYS:
            for fault in ("missing", "duplicate", "mount", "source", "weights"):
                with self.subTest(key=key, fault=fault), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                    root = Path(d)
                    inputs = root/"input"
                    inputs.mkdir()
                    mount = inputs/("unsupported/account/slug" if fault == "mount" else "notebooks/account/slug")
                    (mount/"weights").mkdir(parents=True)
                    (mount/"source"/c.model(key)["revision"]).mkdir(parents=True)
                    marker = f"candidate_checkpoint_{key}.json"
                    if fault != "missing":
                        value = {"schema": "safeshift-candidate160-checkpoint-v1", "model": c.model(key)}
                        write(mount/marker, value)
                        if fault == "duplicate":
                            write(inputs/"another"/marker, value)
                    if fault == "weights":
                        stack.enter_context(patch("safeshift.candidates.source.verify_snapshot", return_value={"scope": "SYNTHETIC_SOURCE_ONLY"}))
                    stack.enter_context(patch.object(p.boot, "provision_scratch_root", side_effect=OSError("SYNTHETIC_NO_SCRATCH")))
                    stack.enter_context(patch.object(rt, "hardware", side_effect=RuntimeError("SYNTHETIC_NO_GPU")))
                    install = stack.enter_context(patch.object(rt, "prepare_runtime", side_effect=AssertionError("NO_INSTALL_FOR_INVALID_INPUT")))
                    output = p.launch_preflight(key, c.source_hash(), ROOT, "a"*40, inputs=inputs, work=root/"out")
                    result = read(Path(str(output)+".preflight-result.json"))
                    self.assertEqual(result["checks"]["checkpoint"]["status"], "BLOCKED")
                    self.assertEqual(result["status"], "BLOCKED")
                    install.assert_not_called()
                    self.assert_no_attempt(root/"out")

    def test_incomplete_child_results_cannot_establish_pass(self):
        for key in c.KEYS:
            for name in ("software_cpu", "cuda_child", "cpu_native", "images_cpu", "live_resources"):
                evidence = synthetic_child_evidence(name, key)
                self.assertEqual(p.validate_child_evidence(name, evidence, key), evidence)
                for invalid in ({}, None, {"status": "PASS"}):
                    with self.subTest(key=key, name=name), self.assertRaises((ValueError, TypeError)):
                        p.validate_child_evidence(name, invalid, key)

    def test_partial_scratch_creation_never_claims_successful_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            scratch_root = root/"tmp"
            scratch_root.mkdir()
            def partial(parent, session):
                (parent/("safeshift-pilot-"+session)).mkdir()
                raise OSError("SYNTHETIC FSYNC FAILED BEFORE OWNERSHIP MARKER")
            with patch.object(p.boot, "provision_scratch_root", return_value=scratch_root), \
                 patch.object(p.boot, "prepare_scratch", side_effect=partial), \
                 patch.object(rt, "hardware", side_effect=RuntimeError("SYNTHETIC_NO_GPU")):
                out = p.launch_preflight("internvl35", c.source_hash(), ROOT, "a"*40, inputs=root/"input", work=root/"out")
            result = read(Path(str(out)+".preflight-result.json"))
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["checks"]["scratch"]["status"], "BLOCKED")
            self.assertEqual(result["checks"]["cleanup"]["status"], "BLOCKED")
            self.assertTrue((scratch_root/("safeshift-pilot-"+out.name)).exists())
            self.assert_no_attempt(root/"out")

    def test_worker_entrypoints_bind_exact_source_and_emit_complete_scoped_receipts(self):
        for key in c.KEYS:
            for name, mode in (("software_cpu", "--software-only"), ("live_resources", "--resources"),
                               ("images_cpu", "--images"), ("cpu_native", "--snapshot"), ("cuda_child", "--cuda")):
                with self.subTest(key=key, name=name), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                    output = Path(d)
                    source = c.source_hash()
                    args = ["preflight", "--worker", "--key", key, "--repo", str(ROOT), "--output", str(output),
                            "--source", source, "--ref", "a"*40, mode]
                    if mode == "--snapshot":
                        args += [str(output/"snapshot")]
                    if mode == "--images":
                        args += ["--bundle", str(output/"bundle")]
                    stack.enter_context(patch.object(sys, "argv", args))
                    stack.enter_context(patch.dict(os.environ, {"SAFESHIFT_RUNTIME_ROOT": str(output/"runtime")}))
                    stack.enter_context(patch.object(rt, "software", return_value=synthetic_child_evidence("software_cpu", key)))
                    stack.enter_context(patch.object(rt, "worker_cuda", return_value=synthetic_child_evidence("cuda_child", key)))
                    stack.enter_context(patch.object(rt, "resources", return_value=synthetic_child_evidence("live_resources", key)))
                    stack.enter_context(patch.object(rt, "verify_images", return_value=synthetic_child_evidence("images_cpu", key)))
                    stack.enter_context(patch.object(p, "native_cpu", return_value=synthetic_child_evidence("cpu_native", key)))
                    stack.enter_context(patch.object(p, "manifest", return_value=({}, [])))
                    p.main()
                    result = read(output/(name+".json"))
                    self.assertEqual(result["schema"], p.CHILD_SCHEMA)
                    self.assertEqual(result["source_sha256"], source)
                    self.assertEqual(result["check"], name)
                    self.assertEqual(result["model_key"], key)
                    p.validate_child_evidence(name, result["evidence"], key)
