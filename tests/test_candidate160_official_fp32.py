"""Owner adoption, direct-worker rejection and official recovery; synthetic only."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from safeshift.candidates import train_contract as c, train_history as h
from safeshift.candidates import train_official as p, train_owner as owner, train_runtime as rt
from safeshift.candidates import train_route as route, train_run as run
from safeshift.candidates.minicpm_resampler_fp32 import ID, descriptor
from safeshift.pilot.artifacts import export, read, sha, write
from safeshift.pilot.contract import digest
from test_candidate160 import fixture, raw
from test_candidate160_routes import EffectiveScripted, start, calls


def execution():
    return h.execution("minicpm4", "c"*64, "a"*40, {"runs": {}, **route.fields(ID)},
                       owner_start=True, implementation=ID)


class OfficialFP32Tests(unittest.TestCase):
    def test_exact_owner_decision_config_descriptor_and_raw_binding(self):
        value = execution()
        self.assertEqual(c.authorize(value, "minicpm4", "c"*64, "a"*40, None), value)
        self.assertEqual(descriptor()["implementation_sha256"], p.DESCRIPTOR_SHA256)
        self.assertEqual(digest(c.config("minicpm4", implementation=ID)), p.CONFIG_SHA256)
        self.assertEqual(value["official_numerical_approval"], p.binding("minicpm4", ID))
        self.assertIsNone(value["official_numerical_approval"]["independent_research_lead_signature"])
        self.assertEqual(run.configuration_context(value)["execution_release"]["official_numerical_approval"],
                         value["official_numerical_approval"])
        self.assertEqual(value["max_native_calls"], 160)
        self.assertEqual(value["max_seconds"], 43200)
        self.assertEqual(value["scientific_selection"], "PENDING")

    def test_wrong_model_configuration_scope_and_approval_fail_before_worker_io(self):
        mutations = [("model_key", "internvl35"), ("model", c.model("internvl35")),
                     ("effective_implementation", "future-fp32"),
                     ("candidate_execution_config_sha256", "0"*64), ("manifest_sha256", "0"*64),
                     ("split", "TEST"), ("max_initial_ids", 161), ("max_native_calls", 161),
                     ("max_seconds", 43201), ("official_numerical_approval", None),
                     ("technical_qualification", route.QUALIFICATION),
                     ("research_lead_approval_ref", "fabricated"),
                     ("official_numerical_approval", {**p.binding("minicpm4", ID), "decision_ref": "fake"})]
        for field, replacement in mutations:
            with self.subTest(field=field):
                value = execution()
                value[field] = replacement
                with patch.object(rt, "source_hash", side_effect=AssertionError("AUTHORITY_BEFORE_IO")), \
                     patch.object(rt, "software", side_effect=AssertionError("NO_SOFTWARE_OR_GPU")):
                    with self.assertRaises(ValueError):
                        rt.worker(c.ROOT, "absent", "absent", "absent", "absent", value,
                                  None, "c"*64, "a"*40, check_only=True)
        value = execution()
        del value["official_numerical_approval"]
        with self.assertRaisesRegex(ValueError, "OWNER_DECISION_BINDING"):
            c.authorize(value, "minicpm4", "c"*64, "a"*40, None)

    def test_direct_cli_does_not_accept_notebook_approval_switch_or_forged_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = execution()
            value["official_numerical_approval"]["decision_ref"] = "fake"
            write(root/"execution.json", value)
            command = rt.worker_command(sys.executable, c.ROOT, root/"out", root/"missing-bundle",
                root/"missing-source", root/"missing-weights", "c"*64, "a"*40,
                execution=root/"execution.json")
            result = subprocess.run(command, cwd=c.ROOT, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("OFFICIAL_FP32_OWNER_DECISION_BINDING", result.stderr)
            self.assertFalse((root/"out").exists())

    def test_live_descriptor_or_config_drift_blocks_before_inputs_or_reservation(self):
        for target, replacement, reason in (
            ("safeshift.candidates.minicpm_resampler_fp32.descriptor",
             {**descriptor(), "implementation_sha256": "0"*64}, "DESCRIPTOR_DRIFT"),
            ("safeshift.candidates.train_contract.config", {"changed": True}, "CONFIGURATION_DRIFT")):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temporary:
                with patch(target, return_value=replacement), \
                     patch.object(h, "collect", side_effect=AssertionError("NO_INPUTS")):
                    with self.assertRaisesRegex(ValueError, reason):
                        rt.launch("minicpm4", "c"*64, c.ROOT, "a"*40, owner_start=True,
                                  recovery_action="resume", implementation=ID, work=Path(temporary)/"out")
                self.assertFalse(list(Path(temporary).rglob("*.json")))

    def test_internvl_and_technical_authority_have_no_new_approval_field(self):
        g = h.execution("internvl35", "c"*64, "a"*40, {"runs": {}}, owner_start=True)
        c.authorize(g, "internvl35", "c"*64, "a"*40, None)
        self.assertNotIn("official_numerical_approval", g)
        self.assertEqual(g["candidate_execution_config_sha256"],
                         "71dcd6b934fed7bae76ce6bb4cbeeefe2ad0c7e570889f9cf33bb5e9858d7206")
        q = h.execution("minicpm4", "c"*64, "a"*40, {"runs": {}, **route.fields(ID, True)},
                        owner_start=True, implementation=ID, qualification=True)
        c.authorize(q, "minicpm4", "c"*64, "a"*40, None)
        self.assertNotIn("official_numerical_approval", q)
        self.assertEqual(q["max_native_calls"], 3)
        with self.assertRaisesRegex(ValueError, "REQUIRES_RECOVERY_SCHEMA"):
            c.authorize(owner.execution("minicpm4", "c"*64, "a"*40, owner_start=True, implementation=ID),
                        "minicpm4", "c"*64, "a"*40, None)

    def test_fp16_and_qualification_histories_never_supply_official_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, rows = fixture(root)
            work, inputs = root/"out", root/"input"
            work.mkdir(); inputs.mkdir()
            for implementation, qualification in ((None, False), (ID, True)):
                out, g = start(work, inputs, implementation=implementation, qualification=qualification)
                self.assertNotIn("official_numerical_approval", g)
            out, g = start(work, inputs, implementation=ID, qualification=False)
            self.assertEqual(read(out/"history_index.json")["runs"], {})
            self.assertEqual(h.recovery_plan(out, rows, g)["pending_ordinals"], list(range(160)))

    def test_official160_zip_resume_noop_keeps_invalid_raw_and_decision_custody(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan, rows = fixture(root)
            work, inputs = root/"out", root/"input"
            work.mkdir(); inputs.mkdir()
            out, g = start(work, inputs, implementation=ID, qualification=False)
            write(out/"pilot_manifest.json", plan)
            value = raw("Level02")
            value["response"] = '```json\n{"safety_level":"Level02"}\n```'
            backend = EffectiveScripted(key="minicpm4", value=value)
            results, reason = calls(out, g, plan, rows, backend)
            self.assertIsNone(reason)
            self.assertEqual(backend.calls, 160)
            self.assertEqual({v["status"] for v in results.values()}, {"INVALID"})
            self.assertTrue(all(v["hnlo"]["hnlo"] is None for v in results.values()))
            attached = inputs/"sealed-official"; attached.mkdir()
            archive = attached/(out.name+".zip")
            export(out, archive)
            checksum = sha(archive)
            fresh = root/"new"; fresh.mkdir()
            resumed, next_g = start(fresh, inputs, implementation=ID, qualification=False)
            recovery = h.recovery_plan(resumed, rows, next_g)
            self.assertEqual(recovery["pending_ordinals"], [])
            self.assertEqual(recovery["already_durable_ordinals"], list(range(160)))
            self.assertEqual(next_g["series_id"], g["series_id"])
            write(resumed/"recovery_plan.json", recovery)
            _, reason = run.run_calls(resumed, plan, rows, lambda: self.fail("NO_LOAD_ON_DURABLE_RESUME"),
                                      next_g, resources=lambda: {})
            self.assertIsNone(reason)
            self.assertFalse((resumed/"model_load_attempt.json").exists())
            self.assertEqual(sha(archive), checksum)
            binding = read(out/"configuration_binding.json")["execution_release"]
            self.assertEqual(binding["official_numerical_approval"], p.binding("minicpm4", ID))
            sample = out/"calls/000000/run/samples/000000"
            self.assertEqual(read(sample/"raw.json")["execution_release"], binding)
            self.assertEqual(read(sample/"raw.json")["response"], value["response"])
            self.assertEqual(read(sample/"effective_numerics.json")["implementation"], descriptor())

    def test_official_faults_stop_without_retry_and_remain_pending(self):
        for fault in ("load", "oom", "nonfinite"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                plan, rows = fixture(root)
                work, inputs = root/"out", root/"input"
                work.mkdir(); inputs.mkdir()
                out, g = start(work, inputs, implementation=ID, qualification=False)
                write(out/"recovery_plan.json", h.recovery_plan(out, rows, g))
                value = raw("Level02")
                if fault == "nonfinite":
                    value["steps"][0]["all_finite"] = False
                backend = EffectiveScripted(key="minicpm4", value=value,
                    fault=RuntimeError("SYNTHETIC CUDA out of memory") if fault == "oom" else None)
                loads = []
                def factory():
                    loads.append(True)
                    if fault == "load":
                        raise RuntimeError("SYNTHETIC load failure")
                    return backend
                results, reason = run.run_calls(out, plan, rows, factory, g, resources=lambda: {})
                self.assertIsNotNone(reason)
                self.assertEqual(len(loads), 1)
                self.assertEqual(backend.calls, 0 if fault == "load" else 1)
                self.assertFalse(any(v["status"] == "SUCCESS" for v in results.values()))
                next_out, next_g = start(work, inputs, implementation=ID, qualification=False)
                self.assertEqual(h.recovery_plan(next_out, rows, next_g)["pending_ordinals"], list(range(160)))

    def test_official_orphan_marker_missing_zip_and_conflicting_history_block(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work, inputs = root/"out", root/"input"
            work.mkdir(); inputs.mkdir()
            out, g = start(work, inputs, implementation=ID, qualification=False)
            attached = inputs/"old-output"; attached.mkdir()
            name = "owner_slot_" + g["slot_sha256"] + "." + g["run_id"] + ".json"
            write(attached/name, {"run_id": g["run_id"], "attempt_id": g["attempt_id"],
                                 "execution_sha256": digest(g)})
            fresh = root/"new"; fresh.mkdir()
            with self.assertRaisesRegex(ValueError, "HISTORY_MISSING_RUN_FOR_MARKER"):
                start(fresh, inputs, implementation=ID, qualification=False)
            # Contradictory copies of one run must not silently choose a history.
            marker = attached/name
            marker.unlink()
            write(attached/"owner_execution.json", {**g, "source_sha256": "d"*64})
            with self.assertRaisesRegex(ValueError, "HISTORY_CONFLICTING_RUN"):
                start(work, inputs, implementation=ID, qualification=False)


if __name__ == "__main__":
    unittest.main()
