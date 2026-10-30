"""Batch delegation and runtime failure tests; SYNTHETIC ONLY, no real approval."""
import copy
import errno
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.candidates import train_contract as c, train_run as run, train_runtime as rt
from safeshift.pilot.artifacts import read, write, export, verify_archive, import_archive, sha
from safeshift.pilot.contract import digest
from scripts.candidate160_authority import worksheet
from test_candidate160 import fixture, grant, ledger, batch_grant, Scripted, raw


class Candidate160BatchTests(unittest.TestCase):
    def test_unsigned_worksheets_have_all_bindings_and_no_approval(self):
        for key in c.KEYS:
            g, reservation, batch = worksheet(key, "a"*40, c.source_hash())
            self.assertEqual(g["model"], c.model(key))
            self.assertTrue(all(v is None for v in g["policy"].values()))
            self.assertIsNone(batch["allow_automatic_continuation"])
            self.assertIsNone(reservation["status"])
            with self.assertRaises(ValueError):
                c.authorize(g, key, g["source_sha256"], g["runtime_ref"], reservation)

    def test_missing_wrong_stale_or_cross_model_batch_delegation_blocks_before_load(self):
        for key in c.KEYS:
            original = batch_grant(key)
            variants = []
            for name, value in (("allow_automatic_continuation", False), ("allow_automatic_continuation", None),
                ("research_lead_approval_ref", "PENDING"), ("policy_sha256", "0"*64),
                ("execution_binding_sha256", "0"*64), ("conditions", [])):
                g = copy.deepcopy(original)
                g["batch_authorization"][name] = value
                variants.append(g)
            variants.append({**original, "batch_authorization": None})
            variants.append({**original, "batch_authorization": batch_grant(c.KEYS[1-c.KEYS.index(key)])["batch_authorization"]})
            for g in variants:
                with self.subTest(key=key, authority=g["batch_authorization"]):
                    with self.assertRaises(ValueError):
                        c.authorize(g, key, g["source_sha256"], g["runtime_ref"], ledger(g))
                    with tempfile.TemporaryDirectory() as d:
                        p, rows = fixture(Path(d))
                        with self.assertRaises(ValueError):
                            run.run_calls(Path(d)/"out", p, rows, lambda: self.fail("NO_LOAD"), g)

    def test_preapproved_batch_both_models_160_no_external_reviewer_archive_roundtrip(self):
        orders = []
        for key in c.KEYS:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                p, rows = fixture(root, staged=True)
                g = batch_grant(key)
                c.authorize(g, key, g["source_sha256"], g["runtime_ref"], ledger(g))
                backend = Scripted(key=key)
                results, reason = run.run_calls(root/"out", p, rows, lambda: backend, g,
                    resources=lambda: {"scope": "SYNTHETIC_RESOURCE_OK"}, reviewer=lambda *a: self.fail("NO_EXTERNAL_REVIEW"))
                self.assertIsNone(reason)
                self.assertEqual(backend.calls, 160)
                orders.append(backend.ids)
                for n in g["policy"]["review_after"]:
                    decision = read(root/f"out/decisions/{n:03d}.json")
                    self.assertEqual(decision["decision"], "AUTO_CONTINUE")
                    self.assertTrue(all(decision["checks"].values()))
                    self.assertEqual(decision["grant_sha256"], digest(g))
                    self.assertNotIn("research_lead_review_ref", decision)
                export(root/"out", root/"run.zip")
                self.assertEqual(read(root/"run.zip.sha256.json")["sha256"], sha(root/"run.zip"))
                verify_archive(root/"run.zip")
                dest = import_archive(root/"run.zip", root/"imported")
                self.assertEqual(run.recover(dest, rows, g), results)
                with self.assertRaises(FileExistsError):
                    run.run_calls(root/"out", p, rows, lambda: backend, g, resources=lambda: {})
                self.assertEqual(backend.calls, 160)
        self.assertEqual(orders[0], orders[1])

    def test_complete_supervisor_batch_save_run_all_simulation_both_models(self):
        from safeshift.candidates.source import ROOT
        import sys
        for key in c.KEYS:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                mount = root/"input/private"
                mount.mkdir(parents=True)
                p, rows = fixture(mount, staged=True)
                write(mount/"pilot_manifest.json", p)
                manifest_hash = sha(mount/"pilot_manifest.json")
                (mount/"weights").mkdir()
                (mount/"source"/c.model(key)["revision"]).mkdir(parents=True)
                write(mount/f"candidate_checkpoint_{key}.json", {
                    "schema": "safeshift-candidate160-checkpoint-v1", "model": c.model(key)})
                scratch = root/"scratch"
                scratch.mkdir()
                with patch.object(c, "MANIFEST", manifest_hash), patch.object(rt, "MANIFEST", manifest_hash):
                    g = batch_grant(key)
                    g["source_sha256"] = c.source_hash()
                    g["batch_authorization"]["execution_binding_sha256"] = digest(c.execution_binding(g))
                    write(mount/f"grant_candidate160_{key}.json", g)
                    write(mount/f"ledger_candidate160_{key}.json", ledger(g))
                    backend = Scripted(key=key)
                    events = []
                    def process(command, **kwargs):
                        output = Path(command[command.index("--output")+1])
                        if "--check-only" in command:
                            events.append("CPU")
                            self.assertFalse((output/"consumption.json").exists())
                        elif "--cuda-check-only" in command:
                            events.append("CUDA_SIMULATION_NOT_GPU")
                            self.assertFalse((output/"consumption.json").exists())
                            write(output/"preledger_cuda.json", {"worker_cuda": "MEASURED_FP16_FUNCTIONAL", "scope": "SYNTHETIC"})
                        else:
                            events.append("WORKER")
                            self.assertTrue(read(output/"consumption.json")["attempt_consumed"])
                            run.run_calls(output, p, rows, lambda: backend, g, resources=lambda: {"scope": "SYNTHETIC"},
                                reviewer=lambda *a: self.fail("NO_EXTERNAL_REVIEW"))
                        return SimpleNamespace(returncode=0)
                    with patch.object(rt, "verify_weights", return_value={"scope": "SYNTHETIC_NO_WEIGHTS"}), \
                         patch.object(rt, "stage_snapshot", return_value={"scope": "SYNTHETIC"}), \
                         patch.object(rt.boot, "provision_scratch_root", return_value=scratch), \
                         patch.object(rt.boot, "storage_admission", return_value={"admitted": True, "scope": "SYNTHETIC"}), \
                         patch.object(rt, "prepare_runtime", return_value=(Path(sys.executable), {})), \
                         patch.object(rt, "hardware", return_value={"scope": "SYNTHETIC_NO_GPU"}), \
                         patch.object(rt.subprocess, "run", side_effect=process):
                        output = rt.launch(key, g["source_sha256"], ROOT, g["runtime_ref"],
                                           inputs=root/"input", work=root/"out", scratch_root=scratch)
                    self.assertEqual(events, ["CPU", "CUDA_SIMULATION_NOT_GPU", "WORKER"])
                    self.assertIsNone(read(output/"supervisor_status.json")["failure"])
                    self.assertEqual(backend.calls, 160)
                    self.assertEqual(read(output/"summary.json")["status"], "COMPLETED_AWAITING_REVIEW")
                    self.assertEqual(len(read(output/"supervisor_accounting.json")), 160)
                    verify_archive(Path(str(output)+".zip"))
                    self.assertEqual(sha(Path(str(output)+".zip")), read(Path(str(output)+".zip.sha256.json"))["sha256"])

    def test_batch_stops_for_behavior_nonfinite_oom_and_resource_loss_both_models(self):
        for key in c.KEYS:
            for defect in ("json", "repeat", "bias", "nonfinite", "oom", "disk", "ram", "custody", "support"):
                with self.subTest(key=key, defect=defect), tempfile.TemporaryDirectory() as d:
                    root = Path(d)
                    p, rows = fixture(root, staged=True)
                    g = batch_grant(key)
                    value = raw("Level01")
                    if defect == "json":
                        value["response"] = "broken JSON"
                        g["policy"]["invalid_max_count"] = 0
                    if defect == "repeat": g["policy"]["repeat_max_count"] = 1
                    if defect == "bias": g["policy"].update(dominance_min_valid=2, dominance_max_fraction=.9)
                    if defect == "nonfinite": value["steps"][0]["all_finite"] = False
                    if defect == "support": g["policy"]["normal_min_support"] = 160
                    g["batch_authorization"]["policy_sha256"] = digest(g["policy"])
                    backend = Scripted(key=key, value=value, fault=RuntimeError("SYNTHETIC CUDA out of memory") if defect == "oom" else None)
                    observations = []
                    def resources():
                        observations.append(1)
                        if len(observations) > 1 and defect in ("disk", "ram"):
                            raise OSError(errno.ENOSPC, "SYNTHETIC " + defect)
                        return {"scope": "SYNTHETIC"}
                    recover = run.recover
                    def recovery(*args):
                        result = recover(*args)
                        if defect == "custody":
                            result[rows[0]["sample_id"]].update(status="TECHNICAL_ERROR", label=None,
                                hnlo={"status": "HNLO_UNVERIFIED", "hnlo": None})
                        return result
                    with patch.object(run, "recover", side_effect=recovery):
                        results, reason = run.run_calls(root/"out", p, rows, lambda: backend, g, resources=resources,
                            reviewer=lambda *a: self.fail("NO_EXTERNAL_REVIEW"))
                    self.assertIsNotNone(reason)
                    self.assertLessEqual(backend.calls, 4)
                    attempted = sum(v["attempts"] for v in results.values())
                    self.assertLessEqual(backend.calls, attempted)
                    self.assertEqual(sum(v["status"] == "NOT_ATTEMPTED" for v in results.values()), 160-attempted)
                    self.assertEqual(read(root/"out/controller_decision.json")["decision"], "STOP")
                    export(root/"out", root/"partial.zip")
                    verify_archive(root/"partial.zip")

    def test_runtime_resource_observer_checks_independent_disk_ram_and_gpu_limits(self):
        p = grant()["policy"]
        with tempfile.TemporaryDirectory() as d, patch.dict(sys.modules, {"psutil": SimpleNamespace(virtual_memory=lambda: SimpleNamespace(available=2**30))}), \
             patch.object(rt.shutil, "disk_usage", return_value=SimpleNamespace(free=2**30)):
            self.assertGreater(rt.resources(p, d, d)["free_ram_mib"], 0)
            with self.assertRaisesRegex(ValueError, "LIVE_RESOURCE_LIMIT"):
                rt.resources({**p, "free_output_mib": 2**40}, d, d)

    def test_unlocked_library_rejected_before_any_native_import(self):
        for key in c.KEYS:
            pins = rt.pins(key)
            distributions = [SimpleNamespace(metadata={"Name": n}, version=v) for n, v in pins.items()]
            distributions.append(SimpleNamespace(metadata={"Name": "UNAPPROVED_LIBRARY"}, version="1"))
            with patch.object(rt.metadata, "version", side_effect=pins.__getitem__), \
                 patch.object(rt.metadata, "distributions", return_value=distributions), \
                 self.assertRaisesRegex(ValueError, "UNLOCKED_INSTALLED"):
                rt.software(key, identity=False)

    def test_driver_below_cuda12_floor_rejected_even_if_allowlisted(self):
        p = grant()["policy"]
        p["driver_versions"] = ["520.99.99"]
        with patch.object(rt.boot, "gpu_preflight", return_value={"physical_gpus": [
            ["Tesla T4", "15360", "15000", "520.99.99"], ["Tesla T4", "15360", "15000", "520.99.99"]]}), \
             self.assertRaisesRegex(ValueError, "DRIVER_TOO_OLD"):
            rt.hardware(p)

    def test_exact_3119_interpreter_detection_no_version_fallback(self):
        from safeshift.candidates.source import ROOT
        for version, allowed in (([3, 11, 9], True), ([3, 11, 10], False), ([3, 12, 0], False)):
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                with patch.object(rt.boot, "interpreter_candidates", return_value=[root/"python"]), \
                     patch.object(rt.boot, "probe_interpreter", return_value={"eligible": True, "version": version}), \
                     patch.object(rt.boot, "pip_controller_probe", side_effect=RuntimeError("SYNTHETIC_SELECTED_3119")), \
                     patch.object(rt.subprocess, "run"):
                    with self.assertRaisesRegex((RuntimeError, ValueError), "SELECTED_3119" if allowed else "3119_NOT_FOUND"):
                        rt.prepare_runtime(ROOT, "internvl35", root/"scratch", root, {}, float("inf"))


if __name__ == "__main__":
    unittest.main()
