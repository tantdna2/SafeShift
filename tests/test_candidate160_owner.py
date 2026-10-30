"""Owner activation/one-shot/custody acceptance. SYNTHETIC CPU ONLY."""
import copy
import errno
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.candidates import train_contract as c, train_owner as owner, train_run as run, train_runtime as rt
from safeshift.candidates.source import ROOT
from safeshift.pilot.artifacts import export, import_archive, read, sha, verify_archive, write
from test_candidate160 import fixture, Scripted, raw


def execution(key="internvl35"):
    return owner.execution(key, c.source_hash(), "a"*40, owner_start=True)


class OwnerExecutionTests(unittest.TestCase):
    def test_owner_engineering_driver_floor_and_live_resource_limits(self):
        rows = [["Tesla T4", "15360", "15000", "535.104.05"]]*2
        with patch.object(rt.boot, "gpu_preflight", return_value={"physical_gpus": rows}):
            self.assertEqual(rt.hardware(owner.policy())["physical_gpus"], rows)
        with patch.object(rt.boot, "gpu_preflight", return_value={"physical_gpus": [
                ["Tesla T4", "15360", "15000", "520.99.99"]]*2}), self.assertRaisesRegex(ValueError, "DRIVER_TOO_OLD"):
            rt.hardware(owner.policy())
        for defect in ("ram", "disk", "gpu"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as d, \
                 patch.dict(sys.modules, {
                    "psutil": SimpleNamespace(virtual_memory=lambda: SimpleNamespace(available=(1 if defect == "ram" else 8)*2**30)),
                    "torch": SimpleNamespace(cuda=SimpleNamespace(mem_get_info=lambda _: (128*2**20, 16*2**30)))}), \
                 patch.object(rt.shutil, "disk_usage", return_value=SimpleNamespace(free=100*2**20 if defect == "disk" else 4*2**30)):
                with self.assertRaisesRegex(ValueError, "LIVE_RESOURCE_LIMIT"):
                    rt.resources(owner.policy(), d, d, gpu=defect == "gpu")

    def test_explicit_activation_distinct_schema_no_fabricated_approval(self):
        with self.assertRaisesRegex(ValueError, "OWNER_START_REQUIRED"):
            owner.execution("internvl35", "c"*64, "a"*40)
        with patch.object(rt, "launch") as launch, self.assertRaisesRegex(ValueError, "OWNER_START_REQUIRED"):
            rt.launch_owner("internvl35", "c"*64, ROOT, "a"*40)
        launch.assert_not_called()
        for key in c.KEYS:
            value = execution(key)
            self.assertEqual(c.authorize(value, key, value["source_sha256"], value["runtime_ref"], None), value)
            self.assertEqual(c.batch_check(value), owner.MODE)
            self.assertFalse(any("approval_ref" in n or n.startswith("allow_") for n in value))
            self.assertNotIn("batch_authorization", value)
            self.assertNotIn("external_ledger_ref", value)
            self.assertEqual(value["policy"]["behavior_limits"], "NOT_DECIDED_OBSERVE_ONLY")
            self.assertNotEqual(value["run_id"], execution(key)["run_id"])
            self.assertEqual(value["slot_sha256"], execution(key)["slot_sha256"])

    def test_scope_model_hash_manifest_cap_retry_resume_policy_and_time_fail_closed(self):
        for key in c.KEYS:
            original = execution(key)
            for field, replacement in (
                ("model_key", "phi"), ("model", c.model(c.KEYS[1-c.KEYS.index(key)])),
                ("source_sha256", "0"*64), ("runtime_ref", "0"*40), ("manifest_sha256", "0"*64),
                ("inventory_sha256", "0"*64), ("split", "TEST"), ("max_initial_ids", 161),
                ("max_native_calls", 161), ("retry_sample_ids", ["synthetic"]), ("resume", True),
                ("candidate_execution_config_sha256", original["legacy_transport_config_sha256"]),
                ("owner_decision_record", "https://example.invalid/approval"), ("slot_sha256", "0"*64),
                ("run_id", "copied"), ("attempt_id", "copied"), ("max_seconds", 1),
                ("expires_unix", float("nan")), ("created_unix", float("inf")),
                ("policy", {**owner.policy(), "invalid_max_count": 160}),
                ("policy", {**owner.policy(), "free_mib_per_gpu": [14336, True]})):
                value = {**copy.deepcopy(original), field: replacement}
                with self.subTest(key=key, field=field), self.assertRaises((ValueError, KeyError)):
                    c.authorize(value, key, original["source_sha256"], original["runtime_ref"], None)
            with self.assertRaises(ValueError):
                c.authorize({**original, "owner_approval_ref": "fabricated"}, key,
                            original["source_sha256"], original["runtime_ref"], None)
            with self.assertRaisesRegex(ValueError, "NOT_AN_EXTERNAL_GRANT"):
                c.authorize(original, key, original["source_sha256"], original["runtime_ref"], {})
            with self.assertRaisesRegex(ValueError, "EXPIRED"):
                owner.validate(original, key, original["source_sha256"], original["runtime_ref"], now=original["expires_unix"])

    def test_atomic_slot_blocks_concurrent_uuid_source_change_and_attached_history(self):
        for key in c.KEYS:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root/"input").mkdir()
                (root/"out").mkdir()
                def reserve(_):
                    try:
                        return owner.reserve(root/"out", execution(key), root/"input")[0]
                    except FileExistsError:
                        return None
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(reserve, range(2)))
                self.assertEqual(sum(v is not None for v in results), 1)
                changed_source = owner.execution(key, "0"*64, "b"*40, owner_start=True)
                with self.assertRaises(FileExistsError):
                    owner.reserve(root/"out", changed_source, root/"input")
                filename = next(v for v in results if v)
                record = read(root/"out/attempts"/filename)
                for layout in ("prior", "datasets/owner/prior", "saved/data/processed/candidate160/attempts"):
                    with self.subTest(layout=layout):
                        mount = root/"input"/layout
                        mount.mkdir(parents=True, exist_ok=True)
                        write(mount/filename, record)
                        with self.assertRaisesRegex(ValueError, "ATTACHED_OUTPUT"):
                            owner.reserve(root/"out", execution(key), root/"input")
                        (mount/filename).unlink()  # only this synthetic fixture
                self.assertEqual(read(root/"out/attempts"/filename), record)

    def test_owner_160_both_models_behavior_observed_without_invented_thresholds(self):
        for key in c.KEYS:
            for label in ("Level01", "INVALID_JSON"):
                with self.subTest(key=key, behavior=label), tempfile.TemporaryDirectory() as d:
                    root = Path(d)
                    plan, rows = fixture(root)
                    value = raw("Level01")
                    if label == "INVALID_JSON":
                        value["response"] = "not JSON"
                    backend = Scripted(key=key, value=value)
                    g = execution(key)
                    results, reason = run.run_calls(root/"out", plan, rows, lambda: backend, g,
                        resources=lambda: {"scope": "SYNTHETIC"},
                        reviewer=lambda *a: self.fail("OWNER_MUST_NOT_REQUEST_CONTINUE_FILE"))
                    self.assertIsNone(reason)
                    self.assertEqual(backend.calls, 160)
                    self.assertEqual(sum(v["native_calls"] for v in results.values()), 160)
                    observed = read(root/"out/behavior_observations.json")
                    self.assertEqual(observed["policy"], "OBSERVE_ONLY_NO_SCIENTIFIC_THRESHOLDS")
                    self.assertEqual(observed["observations"]["max_identical_token_sequences"], 160)
                    if label == "INVALID_JSON":
                        self.assertEqual(observed["observations"]["invalid"], 160)
                    else:
                        self.assertEqual(observed["observations"]["label_counts"], {"Level01": 160})
                    decision = read(root/"out/decisions/160.json")
                    self.assertEqual(decision["decision"], "PLAN_LIMIT_REACHED")
                    self.assertNotIn("research_lead_approval_ref", decision)
                    export(root/"out", root/"run.zip")
                    verify_archive(root/"run.zip")
                    self.assertEqual(sha(root/"run.zip"), read(root/"run.zip.sha256.json")["sha256"])
                    imported = import_archive(root/"run.zip", root/"imported")
                    self.assertEqual(run.recover(imported, rows, g), results)
                    with self.assertRaises(FileExistsError):
                        run.run_calls(root/"out", plan, rows, lambda: backend, g, resources=lambda: {})
                    self.assertEqual(backend.calls, 160)

    def test_owner_technical_failures_stop_and_account_tail_no_retry(self):
        for key in c.KEYS:
            for fault in ("oom", "nonfinite", "input", "resource", "raw", "custody", "deadline", "161", "duplicate"):
                with self.subTest(key=key, fault=fault), tempfile.TemporaryDirectory() as d:
                    root = Path(d)
                    plan, rows = fixture(root)
                    value = raw("Level01")
                    if fault == "nonfinite":
                        value["steps"][0]["all_finite"] = False
                    if fault == "input":
                        Path(rows[0]["image"]).write_bytes(b"CHANGED_SYNTHETIC")
                    backend = Scripted(key=key, value=value,
                        fault=RuntimeError("SYNTHETIC out of memory") if fault == "oom" else None)
                    g = execution(key)
                    with ExitStack() as stack:
                        if fault == "raw":
                            stack.enter_context(patch.object(run.CandidateStore, "raw", side_effect=OSError(errno.ENOSPC, "synthetic")))
                        if fault == "custody":
                            original = run.recover
                            def corrupt(*args, **kwargs):
                                result = original(*args, **kwargs)
                                if kwargs.get("start_ordinal") == 0:
                                    result[rows[0]["sample_id"]]["label"] = None
                                return result
                            stack.enter_context(patch.object(run, "recover", side_effect=corrupt))
                        def resources():
                            if fault == "resource":
                                raise OSError(errno.ENOSPC, "SYNTHETIC_RESOURCE_FAILURE")
                            return {"scope": "SYNTHETIC"}
                        if fault in ("161", "duplicate"):
                            bad = rows + [rows[0]] if fault == "161" else [rows[0]] + rows[:-1]
                            with self.assertRaisesRegex(ValueError, "EXACT_SHARED_160_PLAN"):
                                run.run_calls(root/"out", plan, bad, lambda: backend, g)
                            self.assertEqual(backend.calls, 0)
                            continue
                        result, reason = run.run_calls(root/"out", plan, rows, lambda: backend, g,
                            resources=resources, deadline=0 if fault == "deadline" else None)
                    self.assertIsNotNone(reason)
                    self.assertLessEqual(backend.calls, 1)
                    attempted = sum(v["attempts"] for v in result.values())
                    self.assertEqual(sum(v["status"] == "NOT_ATTEMPTED" for v in result.values()), 160-attempted)
                    export(root/"out", root/"partial.zip")
                    verify_archive(root/"partial.zip")

    def test_complete_owner_save_run_all_and_replay_supervisor_both_models(self):
        for key in c.KEYS:
            self.supervisor_case(key)

    def test_owner_supervisor_preflight_consumption_uncertainty_and_archive_errors(self):
        for key in c.KEYS:
            for fault in ("manifest", "checkpoint", "storage", "python", "cpu", "hardware", "cuda",
                          "authority", "slot", "consume", "worker", "export"):
                with self.subTest(key=key, fault=fault):
                    self.supervisor_case(key, fault)

    def supervisor_case(self, key, fault=None):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            mount = root/"input/private"
            mount.mkdir(parents=True)
            plan, rows = fixture(mount)
            write(mount/"pilot_manifest.json", plan)
            manifest_hash = sha(mount/"pilot_manifest.json")
            (mount/"weights").mkdir()
            (mount/"source"/c.model(key)["revision"]).mkdir(parents=True)
            write(mount/f"candidate_checkpoint_{key}.json", {
                "schema": "safeshift-candidate160-checkpoint-v1", "model": c.model(key)})
            scratch = root/"scratch"
            scratch.mkdir()
            backend = Scripted(key=key)
            events = []
            def process(command, **kwargs):
                self.assertIn("--execution", command)
                self.assertNotIn("--grant", command)
                self.assertNotIn("--ledger", command)
                output = Path(command[command.index("--output")+1])
                if "--check-only" in command:
                    events.append("CPU")
                    if fault == "cpu":
                        raise subprocess.CalledProcessError(1, "SYNTHETIC CPU/input failure")
                elif "--cuda-check-only" in command:
                    events.append("CUDA_SIMULATED")
                    if fault == "cuda":
                        raise subprocess.CalledProcessError(1, "SYNTHETIC CUDA failure")
                    write(output/"preledger_cuda.json", {"worker_cuda": "MEASURED_FP16_FUNCTIONAL", "scope": "SYNTHETIC"})
                    if fault == "authority":
                        record = read(output/"owner_execution.json")
                        record["resume"] = True
                        (output/"owner_execution.json").write_text(__import__("json").dumps(record))
                    if fault == "slot":
                        record = read(output/"owner_execution.json")
                        filename = "owner_slot_" + record["slot_sha256"] + ".json"
                        (output.parent/"attempts"/filename).write_text('{}')
                else:
                    events.append("WORKER")
                    self.assertTrue(read(output/"consumption.json")["attempt_consumed"])
                    if fault in ("worker", "export"):
                        raise subprocess.TimeoutExpired("SYNTHETIC WORKER", 1)
                    g = read(output/"owner_execution.json")
                    c.authorize(g, key, g["source_sha256"], g["runtime_ref"], None)
                    run.run_calls(output, plan, rows, lambda: backend, g,
                        resources=lambda: {"scope": "SYNTHETIC"},
                        reviewer=lambda *a: self.fail("NO_MANUAL_CONTINUE"))
                if "--check-only" in command or "--cuda-check-only" in command:
                    self.assertFalse((output/"consumption.json").exists())
                return SimpleNamespace(returncode=0)
            with ExitStack() as stack:
                stack.enter_context(patch.object(c, "MANIFEST", manifest_hash if fault != "manifest" else "0"*64))
                stack.enter_context(patch.object(rt, "MANIFEST", manifest_hash if fault != "manifest" else "0"*64))
                stack.enter_context(patch.object(rt, "verify_weights", side_effect=ValueError("SYNTHETIC HASH") if fault == "checkpoint" else None,
                                                 return_value={"scope": "SYNTHETIC_NO_WEIGHTS"}))
                stack.enter_context(patch.object(rt, "stage_snapshot", return_value={"scope": "SYNTHETIC"}))
                stack.enter_context(patch.object(rt.boot, "provision_scratch_root", return_value=scratch))
                stack.enter_context(patch.object(rt.boot, "storage_admission", return_value={"admitted": fault != "storage"}))
                stack.enter_context(patch.object(rt, "prepare_runtime", side_effect=ValueError("SYNTHETIC PYTHON") if fault == "python" else None,
                                                 return_value=(Path(sys.executable), {})))
                stack.enter_context(patch.object(rt, "hardware", side_effect=ValueError("SYNTHETIC GPU") if fault == "hardware" else None,
                                                 return_value={"scope": "SYNTHETIC_NO_GPU"}))
                stack.enter_context(patch.object(rt.subprocess, "run", side_effect=process))
                original_write = rt.write
                def write_fault(path, value):
                    if fault == "consume" and Path(path).name.endswith(".consumed.json"):
                        raise OSError(errno.ENOSPC, "SYNTHETIC CONSUMPTION UNCERTAIN")
                    return original_write(path, value)
                stack.enter_context(patch.object(rt, "write", side_effect=write_fault))
                if fault == "export":
                    stack.enter_context(patch.object(rt, "export", side_effect=OSError(errno.ENOSPC, "SYNTHETIC EXPORT")))
                    with self.assertRaises(OSError):
                        rt.launch_owner(key, c.source_hash(), ROOT, "a"*40, owner_start=True,
                                        inputs=root/"input", work=root/"out", scratch_root=scratch)
                    self.assertEqual(backend.calls, 0)
                    self.assertEqual(len(list((root/"out").glob("*/owner_consumption_log.json"))), 1)
                    return
                output = rt.launch_owner(key, c.source_hash(), ROOT, "a"*40, owner_start=True,
                                         inputs=root/"input", work=root/"out", scratch_root=scratch)
                status = read(output/"supervisor_status.json")
                consumed = None if fault == "consume" else fault in (None, "worker")
                self.assertIs(status["attempt_consumed"], consumed)
                log = read(output/"owner_consumption_log.json")
                self.assertIs(log["attempt_consumed"], consumed)
                self.assertFalse((output/"grant.json").exists())
                verify_archive(Path(str(output)+".zip"))
                if fault is None:
                    self.assertEqual(events, ["CPU", "CUDA_SIMULATED", "WORKER"])
                    self.assertEqual(backend.calls, 160)
                    self.assertEqual(read(output/"summary.json")["status"], "COMPLETED_AWAITING_REVIEW")
                    self.assertEqual(len(read(output/"supervisor_accounting.json")), 160)
                else:
                    self.assertEqual(backend.calls, 0)
                    self.assertIsNotNone(status["failure"])
                second = rt.launch_owner(key, c.source_hash(), ROOT, "a"*40, owner_start=True,
                                         inputs=root/"input", work=root/"out", scratch_root=scratch)
                self.assertEqual(read(second/"supervisor_status.json")["status"], "BLOCKED")
                self.assertEqual(read(second/"supervisor_status.json")["stage"], "authority")
                self.assertEqual(backend.calls, 160 if fault is None else 0)
                self.assertFalse((second/"owner_consumption_log.json").exists())


if __name__ == "__main__":
    unittest.main()
