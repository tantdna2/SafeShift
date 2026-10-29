"""Synthetic-only candidate160 control-plane/custody tests; never GPU evidence."""
import copy
import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.candidates import train_contract as c, train_run as run, train_runtime as rt
from safeshift.candidates.source import ROOT
from safeshift.pilot import contract as legacy
from safeshift.pilot.artifacts import export, import_archive, read, sha, verify_archive, write
from test_pilot import raw, candidates, plan


def policy():
    # Deliberately permissive SYNTHETIC TEST ONLY; never shipped as default policy.
    return {"early_behavior_after": 4, "review_after": [4], "review_wait_seconds": 0,
            "invalid_max_count": 160, "repeat_max_count": 160, "dominance_min_valid": 160,
            "dominance_max_fraction": 1, "normal_min_support": 160, "normal_fpr_max": 1,
            "anomaly_min_support": 160, "anomaly_fnr_max": 1,
            "driver_versions": ["550.0"], "free_mib_per_gpu": [14336, 1]}


def grant(key="internvl35"):
    return {"schema": "safeshift-candidate160-grant-v1", "model_key": key, "model": c.model(key),
            "base": c.BASE, "source_sha256": "c"*64, "runtime_ref": "a"*40,
            "manifest_sha256": c.MANIFEST, "inventory_sha256": c.INVENTORY,
            "config_sha256": legacy.digest(c.config(key)), "data_revision": legacy.DATA_REVISION,
            "master_sha256": legacy.MASTER_SHA, "split": "TRAIN", "max_initial_ids": 160,
            "max_native_calls": 160, "retry_sample_ids": [], "resume": False,
            **{n: "SYNTHETIC_TEST_REVIEW_ONLY" for n in ("G0", "T0", "O3", "code_review_ref",
                "manifest_review_ref", "policy_approval_ref", "runtime_approval_ref", "external_ledger_ref",
                "owner_approval_ref", "research_lead_review_ref")},
            **{n: True for n in ("allow_train_images", "allow_folder_gt", "allow_checkpoint_read", "allow_gpu",
                               "allow_raw_export", "allow_software_install", "private_custody_approved")},
            "run_id": "synthetic_" + key, "attempt_id": "synthetic_" + key + "_a1",
            "max_seconds": 600, "expires_unix": 4102444800, "policy": policy()}


def ledger(g):
    return {"schema": "safeshift-candidate160-reservation-v1", "status": "RESERVED_NOT_EXECUTED",
            **{n: g[n] for n in ("attempt_id", "run_id", "model_key", "source_sha256", "runtime_ref",
                                 "manifest_sha256", "expires_unix", "external_ledger_ref")},
            "grant_sha256": legacy.digest(g)}


def review(checkpoint, g, *args):
    return {"schema": "safeshift-candidate160-review-v1", "checkpoint_sha256": legacy.digest(checkpoint),
            **{n: g[n] for n in ("attempt_id", "run_id", "model_key", "source_sha256", "manifest_sha256")},
            "research_lead_review_ref": "SYNTHETIC_TEST_DECISION", "decision": "CONTINUE"}


def fixture(root):
    p = plan(candidates())
    p["dimension_inventory_sha256"] = c.INVENTORY
    rows = p["main"]
    for i, row in enumerate(rows):
        path = root / row["image"]
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"SYNTHETIC_BYTES_NOT_DATASET:" + str(i).encode())
        row["image_sha256"] = sha(path)
    return p, [{**r, "image": str(root/r["image"])} for r in rows]


class Scripted:
    """Only in tests: character logits, no model/processor/library inference."""
    environment = {"scope": "SYNTHETIC_TEST_NOT_GPU"}
    stage = "synthetic_generation"
    serialized_tokenizer = b'{"scope":"synthetic-character-tokenizer"}\n'

    def __init__(self, fault=None, value=None):
        self.calls, self.ids, self.fault, self.value = 0, [], fault, value

    def generate(self, image, sample):
        self.ids.append(Path(image).name)
        self.calls += 1
        write(sample / "native_call.json", {"invocation": 1, "scope": "SYNTHETIC"})
        if self.fault:
            raise self.fault
        value = copy.deepcopy(self.value if self.value is not None else raw(legacy.LEVELS[(self.calls-1) % 4]))
        value["raw_nonfinite"] = any(not s["all_finite"] for s in value["steps"])
        write(sample / "native.json", {"generated_ids": value["generated_ids"]})
        for n, step in enumerate(value["steps"]):
            write(sample / f"steps/{n:03d}.json", step)
        return value


class Candidate160Tests(unittest.TestCase):
    def test_public_contract_has_no_grant_thresholds_or_historical_ids(self):
        value = read(ROOT / "configs/candidate160/preparation.json")
        self.assertEqual(value["status"], "BLOCKED")
        for name in ("grant", "G0", "T0", "O3", "early_behavior_after", "invalid_max_count",
                     "repeat_max_count", "dominance_max_fraction", "driver_allowlist"):
            self.assertIsNone(value[name])
        self.assertEqual(value["manifest_sha256"], c.MANIFEST)
        self.assertEqual(set(legacy.MODELS), {"gemma", "phi", "smolvlm2"})

    def test_new_grant_ledger_source_model_rights_expiry_and_policy_bindings(self):
        for key in c.KEYS:
            g = grant(key)
            c.authorize(g, key, g["source_sha256"], g["runtime_ref"], ledger(g), now=1)
            defects = {"schema": "safeshift-pilot-grant-v1", "G0": None, "T0": "PENDING", "O3": "",
                "source_sha256": "d"*64, "model_key": "phi", "manifest_sha256": "0"*64,
                "config_sha256": "0"*64, "runtime_ref": "b"*40, "max_initial_ids": 161,
                "max_native_calls": 161, "resume": True, "retry_sample_ids": ["synthetic"],
                "allow_train_images": False, "allow_folder_gt": False, "allow_gpu": False,
                "allow_checkpoint_read": False, "policy": None, "expires_unix": 0}
            for name, value in defects.items():
                with self.subTest(key=key, name=name):
                    changed = {**g, name: value}
                    with self.assertRaises((ValueError, PermissionError)):
                        c.authorize(changed, key, g["source_sha256"], g["runtime_ref"], ledger(changed), now=1)
            for status in ("CONSUMED", "RESERVED", None):
                with self.assertRaises(ValueError):
                    c.authorize(g, key, g["source_sha256"], g["runtime_ref"], {**ledger(g), "status": status}, now=1)

    def test_missing_policy_values_not_accepted_as_zero_or_pass(self):
        for name in policy():
            p = policy()
            p[name] = None
            with self.subTest(name=name), self.assertRaises(ValueError): c.policy_check(p)
        for defect in ({"review_after": []}, {"early_behavior_after": 160}, {"dominance_max_fraction": float("nan")},
                       {"invalid_max_count": True}, {"free_mib_per_gpu": [32000]}):
            with self.assertRaises(ValueError): c.policy_check({**policy(), **defect})

    def test_manifest_exact_bytes_and_order_without_selector_or_private_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p, _ = fixture(root)
            write(root/"pilot_manifest.json", p)
            with patch.object(c, "MANIFEST", sha(root/"pilot_manifest.json")), \
                 patch("safeshift.pilot.manifest.select_main", side_effect=AssertionError("NO_RESELECTION")):
                loaded, rows = c.manifest(root)
                self.assertEqual([r["sample_id"] for r in rows], [r["sample_id"] for r in p["main"]])
                p["main"][:2] = reversed(p["main"][:2])
                (root/"pilot_manifest.json").write_text(json.dumps(p))
                with self.assertRaisesRegex(ValueError, "MANIFEST_BYTES"): c.manifest(root)

    def test_both_models_same_160_order_one_load_raw_replay_archive(self):
        orders = []
        for key in c.KEYS:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                p, rows = fixture(root)
                output = root/"evidence"
                backend = Scripted()
                factory_calls = []
                def factory():
                    factory_calls.append(1)
                    return backend
                results, reason = run.run_calls(output, p, rows, factory, grant(key), reviewer=review)
                self.assertIsNone(reason)
                self.assertEqual(backend.calls, 160)
                self.assertEqual(len(factory_calls), 1)
                self.assertTrue(all(v["status"] == "SUCCESS" and v["native_calls"] == v["attempts"] == 1
                                    for v in results.values()))
                self.assertEqual(run.recover(output, rows), results)
                orders.append(backend.ids)
                self.assertEqual(read(output/"checkpoints/001.json")["kind"], "FIRST_IMAGE_TECHNICAL")
                self.assertEqual(read(output/"checkpoints/004.json")["kind"], "EARLY_BEHAVIOR")
                write(output/"pilot_manifest.json", p)
                archive = root/"evidence.zip"
                export(output, archive)
                verify_archive(archive)
                imported = import_archive(archive, root/"imported")
                self.assertEqual(run.recover(imported, rows), results)
                self.assertEqual(read(output/"summary.json")["classification_quality"], "AWAITING_RESEARCH_LEAD_REVIEW")
                with self.assertRaises(FileExistsError):
                    run.run_calls(output, p, rows, factory, grant(key), reviewer=review)
                self.assertEqual(backend.calls, 160)
        self.assertEqual(orders[0], orders[1])
        self.assertEqual(orders[0], [f"{i:06d}.jpg" for i in range(160)])
        self.assertEqual(set(legacy.MODELS), {"gemma", "phi", "smolvlm2"})

    def test_maximum_duplicate_ids_and_161_rejected_without_factory(self):
        with tempfile.TemporaryDirectory() as d:
            p, rows = fixture(Path(d))
            for bad in (rows+rows[:1], rows[:-1], [rows[0]]*160):
                with self.assertRaises(ValueError):
                    run.run_calls(Path(d)/"out", p, bad, lambda: self.fail("MUST_NOT_LOAD"), grant())

    def test_missing_or_wrong_lead_review_stops_with_not_attempted_tail(self):
        for decision in (None, "STOP", "WRONG_HASH"):
            with self.subTest(decision=decision), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                p, rows = fixture(root)
                backend = Scripted()
                def reviewer(checkpoint, g, *args):
                    if decision is None: return None
                    value = review(checkpoint, g)
                    if decision == "STOP": value["decision"] = "STOP"
                    else: value["checkpoint_sha256"] = "0"*64
                    return value
                results, reason = run.run_calls(root/"out", p, rows, lambda: backend, grant(), reviewer=reviewer)
                self.assertEqual(backend.calls, 4)
                self.assertIsNotNone(reason)
                self.assertEqual(sum(v["status"] == "NOT_ATTEMPTED" for v in results.values()), 156)

    def test_oom_decode_import_nonfinite_invalid_raw_write_and_loss_stop(self):
        for kind in ("oom", "decode", "library", "nonfinite", "invalid", "raw_write", "ids_loss", "step_loss", "cpu_decode_mismatch"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                p, rows = fixture(root)
                value = raw()
                fault = {"oom": RuntimeError("SYNTHETIC CUDA out of memory"),
                         "decode": ValueError("SYNTHETIC decode failure"), "library": ImportError("SYNTHETIC")}.get(kind)
                if kind == "nonfinite": value["steps"][0]["all_finite"] = False
                if kind == "invalid": value["response"] = '{"safety_level":"Level01","safety_level":"Level04"}'
                if kind == "cpu_decode_mismatch": value["cpu_tokenizer_replay"]["status"] = "FAIL"
                backend = Scripted(fault=fault, value=value)
                original = backend.generate
                def generate(image, sample):
                    v = original(image, sample)
                    if kind == "ids_loss": (sample/"native.json").unlink()
                    if kind == "step_loss": (sample/"steps/000.json").unlink()
                    return v
                backend.generate = generate
                g = grant()
                g["policy"]["invalid_max_count"] = 0
                from safeshift.pilot import artifacts
                original_write = artifacts.write
                def fail(path, obj):
                    if kind == "raw_write" and Path(path).name == "raw.json":
                        raise OSError(errno.ENOSPC, "SYNTHETIC raw full")
                    return original_write(path, obj)
                with patch.object(artifacts, "write", side_effect=fail):
                    result, reason = run.run_calls(root/"out", p, rows, lambda: backend, g, reviewer=review)
                self.assertEqual(backend.calls, 1)
                self.assertIsNotNone(reason)
                self.assertEqual(sum(v["status"] == "NOT_ATTEMPTED" for v in result.values()), 159)
                if kind in ("ids_loss", "step_loss", "cpu_decode_mismatch"):
                    self.assertTrue((root/"out/calls/000000/run/samples/000000/raw.json").exists())
                export(root/"out", root/"partial.zip")
                verify_archive(root/"partial.zip")

    def test_checkpoint_or_report_write_failure_no_more_native_calls(self):
        for name in ("checkpoints/001.json", "accounting.json", "summary.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                p, rows = fixture(root)
                backend = Scripted()
                g = grant()
                original = run.write
                def fail(path, obj):
                    if Path(path).as_posix().endswith(name): raise OSError(errno.ENOSPC, "SYNTHETIC disk")
                    return original(path, obj)
                with patch.object(run, "write", side_effect=fail):
                    if name == "checkpoints/001.json":
                        _, reason = run.run_calls(root/"out", p, rows, lambda: backend, g, reviewer=review)
                        self.assertIsNotNone(reason)
                        self.assertEqual(backend.calls, 1)
                    else:
                        with self.assertRaises(OSError):
                            run.run_calls(root/"out", p, rows, lambda: backend, g, reviewer=lambda *a: None)
                        self.assertEqual(backend.calls, 4)
                self.assertEqual(sum(v["attempts"] for v in run.recover(root/"out", rows).values()), backend.calls)

    def test_repetition_dominance_false_safe_false_alarm_limits(self):
        o = {"invalid": 0, "max_identical_token_sequences": 1, "valid": 4,
             "label_counts": {"Level01": 4}, "normal_support": 2, "normal_false_alarms": 2,
             "anomaly_support": 2, "false_safe": 2}
        for changes, reason in (({"repeat_max_count": 0}, "REPEATED_TOKEN_SEQUENCE_LIMIT"),
            ({"dominance_min_valid": 4, "dominance_max_fraction": .9}, "LABEL_DOMINANCE_LIMIT"),
            ({"normal_min_support": 2, "normal_fpr_max": .9}, "NORMAL_FALSE_ALARM_LIMIT"),
            ({"anomaly_min_support": 2, "anomaly_fnr_max": .9}, "FALSE_SAFE_LIMIT")):
            self.assertEqual(run.behavior_stop(o, {**policy(), **changes}), reason)
        self.assertIsNone(run.behavior_stop(o, policy()))

    def test_time_limit_before_load_and_review_deadline(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p, rows = fixture(root)
            result, reason = run.run_calls(root/"out", p, rows, lambda: self.fail("NO_LOAD"), grant(),
                                          deadline=0, clock=lambda: 1)
            self.assertEqual(reason, "TIME_CAP_BEFORE_NEXT_CALL")
            self.assertTrue(all(v["status"] == "NOT_ATTEMPTED" for v in result.values()))
            self.assertIsNone(run.await_review({}, grant(), root/"reviews", 0))

    def test_hardware_two_t4_and_driver_free_memory_not_pooled(self):
        for text, good in (("Tesla T4, 15360, 15000, 550.0\nTesla T4, 15360, 15000, 550.0\n", True),
                           ("Tesla T4, 32768, 30000, 550.0\n", False),
                           ("Tesla T4, 15360, 12000, 550.0\nTesla T4, 15360, 15000, 550.0\n", False),
                           ("Tesla T4, 15360, 15000, 551.0\nTesla T4, 15360, 15000, 551.0\n", False)):
            with patch.object(rt.boot.subprocess, "check_output", return_value=text):
                if good: self.assertEqual(rt.hardware(policy())["cuda_validation"], "NOT_RUN")
                else:
                    with self.assertRaises((ValueError, RuntimeError)): rt.hardware(policy())

    def test_worker_cuda_actual_child_failure_not_host_pass(self):
        cuda = SimpleNamespace(is_available=lambda: False)
        with patch.object(rt, "hardware", return_value={"scope": "SYNTHETIC_HOST_OBSERVATION"}), \
             patch.dict(sys.modules, {"torch": SimpleNamespace(cuda=cuda)}), self.assertRaisesRegex(ValueError, "VISIBLE_T4"):
            rt.worker_cuda(policy())

    def test_library_pin_fault_before_torch_import(self):
        with patch.object(rt.metadata, "version", return_value="WRONG"), \
             self.assertRaisesRegex(ValueError, "DEPENDENCY_MISMATCH"):
            rt.software("internvl35", identity=False)

    def test_no_grant_not_read_private_data_model_gpu_or_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/"input").mkdir()
            with patch.object(rt, "manifest", side_effect=AssertionError("NO_PRIVATE_MANIFEST")), \
                 patch.object(rt, "verify_weights", side_effect=AssertionError("NO_WEIGHTS")), \
                 patch.object(rt, "hardware", side_effect=AssertionError("NO_GPU")), \
                 patch.object(rt, "prepare_runtime", side_effect=AssertionError("NO_INSTALL")):
                output = rt.launch("internvl35", c.source_hash(), ROOT, "a"*40,
                                   inputs=root/"input", work=root/"out")
            value = read(output/"supervisor_status.json")
            self.assertEqual(value["status"], "BLOCKED")
            self.assertFalse(value["attempt_consumed"])
            self.assertFalse((root/"out/attempts").exists())
            verify_archive(Path(str(output)+".zip"))

    def test_supervisor_cpu_simulation_preledger_failure_consumption_worker_tail_and_export(self):
        for failure in ("cpu", "hardware", "worker_timeout", "review_stop"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                mount = root/"input/private"
                mount.mkdir(parents=True)
                p, execution_rows = fixture(mount)
                write(mount/"pilot_manifest.json", p)
                (mount/"weights").mkdir()
                (mount/"source"/c.model("internvl35")["revision"]).mkdir(parents=True)
                write(mount/"candidate_checkpoint_internvl35.json", {
                    "schema": "safeshift-candidate160-checkpoint-v1", "model": c.model("internvl35")})
                manifest_hash = sha(mount/"pilot_manifest.json")
                scratch = root/"scratch"
                scratch.mkdir()
                events = []
                backend = Scripted()
                with patch.object(c, "MANIFEST", manifest_hash), patch.object(rt, "MANIFEST", manifest_hash):
                    g = grant()
                    g["source_sha256"] = c.source_hash()
                    write(mount/"grant_candidate160_internvl35.json", g)
                    write(mount/"ledger_candidate160_internvl35.json", ledger(g))
                    def process(command, **kwargs):
                        output = Path(command[command.index("--output")+1])
                        if "--check-only" in command:
                            events.append("CPU_PREFLIGHT")
                            self.assertFalse((output/"consumption.json").exists())
                            if failure == "cpu": raise ImportError("SYNTHETIC processor missing dependency")
                            write(output/"software_cpu.json", {"scope": "SIMULATED_NO_GPU"})
                        else:
                            events.append("WORKER")
                            self.assertTrue(read(output/"consumption.json")["attempt_consumed"])
                            if failure == "worker_timeout": raise subprocess.TimeoutExpired("SYNTHETIC", 1)
                            run.run_calls(output, p, execution_rows, lambda: backend, g, reviewer=lambda *a: None)
                        return SimpleNamespace(returncode=0)
                    def hardware(p):
                        events.append("HARDWARE_SIMULATION")
                        if failure == "hardware": raise RuntimeError("SYNTHETIC driver absent")
                        return {"scope": "SIMULATED_NO_GPU"}
                    with patch.object(rt, "verify_weights", return_value={"scope": "SYNTHETIC_NO_WEIGHTS"}), \
                         patch.object(rt, "stage_snapshot", return_value={"scope": "SYNTHETIC_NO_IMPORT"}), \
                         patch.object(rt.boot, "provision_scratch_root", return_value=scratch), \
                         patch.object(rt.boot, "storage_admission", return_value={"admitted": True, "scope": "SIMULATED"}), \
                         patch.object(rt, "prepare_runtime", return_value=(Path(sys.executable), {})), \
                         patch.object(rt, "hardware", side_effect=hardware), \
                         patch.object(rt.subprocess, "run", side_effect=process):
                        output = rt.launch("internvl35", g["source_sha256"], ROOT, g["runtime_ref"],
                                           inputs=root/"input", work=root/"out", scratch_root=scratch)
                    consumed = failure in ("worker_timeout", "review_stop")
                    self.assertIs(read(output/"supervisor_status.json")["attempt_consumed"], consumed)
                    accounting = read(output/"supervisor_accounting.json")
                    expected_calls = 4 if failure == "review_stop" else 0
                    self.assertEqual(backend.calls, expected_calls)
                    self.assertEqual(sum(r["status"] == "NOT_ATTEMPTED" for r in accounting), 160-expected_calls)
                    self.assertEqual(events[0], "CPU_PREFLIGHT")
                    if consumed: self.assertEqual(events, ["CPU_PREFLIGHT", "HARDWARE_SIMULATION", "WORKER"])
                    verify_archive(Path(str(output)+".zip"))

    def test_finalizer_write_failure_still_exports_and_export_failure_retains_directory(self):
        for defect in ("status_write", "export"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root/"input").mkdir()
                original_write = rt.write
                def write_fault(path, value):
                    if defect == "status_write" and Path(path).name == "supervisor_status.json":
                        raise OSError(errno.ENOSPC, "SYNTHETIC finalizer write")
                    return original_write(path, value)
                with patch.object(rt, "write", side_effect=write_fault):
                    if defect == "export":
                        with patch.object(rt, "export", side_effect=OSError("SYNTHETIC ZIP failure")), self.assertRaises(OSError):
                            rt.launch("internvl35", c.source_hash(), ROOT, "a"*40, inputs=root/"input", work=root/"out")
                        self.assertEqual(len(list((root/"out").glob("*/supervisor_failure.json"))), 1)
                    else:
                        output = rt.launch("internvl35", c.source_hash(), ROOT, "a"*40,
                                           inputs=root/"input", work=root/"out")
                        verify_archive(Path(str(output)+".zip"))
                        self.assertTrue(read(output/"finalizer_errors.json"))


if __name__ == "__main__":
    unittest.main()
