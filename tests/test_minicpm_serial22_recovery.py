"""CPU-only deadline, custody and three-source continuation regressions."""
from copy import deepcopy
from pathlib import Path
import os
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from safeshift.candidates import fulltrain_run as journal
from safeshift.fulltrain import admission, contract, minicpm_offline as policy, minicpm_ui as ui, runtime, supervision
from safeshift.pilot.artifacts import export, write
from safeshift.pilot.contract import digest
from scripts import minicpm_offline_continuation as route


class Serial22RecoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.budgets = {"setup_seconds": 1800, "diagnostic_seconds": 600}
        self.grant = {"scope": {"resource_policy": self.budgets, "source_sha256": "c" * 64},
            "caps": {"job_seconds": 14400, "job_calls": 3763, "total_calls": 20000,
                     "total_jobs": 100, "total_gpu_seconds": 1000000},
            "sizing": {"export_seconds": 600, "first_call_seconds": 30, "safety_milli": 1500},
            "offline": {"unmeasured_calls": 100},
            "expires_unix": int(time.time()) + 30000, "provider_max_age_seconds": 3600,
            "continuation": {"previous_source_sha256": contract.PR211_SOURCE, "first_serial": 23,
                             "pr211_call_bound": None}}
        self.reserved = {"calls": 11000, "jobs": 22, "gpu_seconds": 600000}

    def test_stage_caps_share_job_deadline_and_admit_can_return_after_600(self):
        request = {"resource_policy": self.budgets, "original_inputs": {}, "model_key": "minicpm4",
                   "plan": {"max_seconds": 14400}}
        active = {"grant": self.grant}
        stage_caps = {"admit": 1800, "setup": 1800, "reclaim": 600, "cpu": 1200, "gpu": 600}
        for mode, cap in stage_caps.items():
            self.assertEqual(admission.stage_deadline(mode, request, 14400, active, now=2400), 2400 + cap)
        for mode in (*stage_caps, "native"):
            self.assertEqual(admission.stage_deadline(mode, request, 14400, active, now=13799), 13800)
        self.assertEqual(policy.recovery_pre_native_seconds(self.grant), 8400)
        self.assertEqual(policy.recovery_overhead_seconds(self.grant), 9600)
        # Exercise admit at 1,401 simulated seconds, with inputs stubbed at their boundaries.
        deadline = admission.stage_deadline("admit", request, 14400, active, now=2400)
        request["source_sha256"] = "c" * 64
        output = self.root / "admit"
        active["value"] = {"ancestors": []}
        with patch.object(admission, "validate_request"), patch.object(admission.memory, "observe"), \
                patch.object(admission.memory, "resource_check", return_value={}), \
                patch("safeshift.fulltrain.minicpm_release.current", return_value=active), \
                patch.object(admission, "_admit", return_value=((None, None, None, None, None, {}), ())) as admit, \
                patch.object(time, "monotonic", return_value=3801):
            admission.stage("admit", request, contract.ROOT, output, deadline)
        self.assertTrue((output / "stage.json").exists())
        self.assertFalse(admit.call_args.kwargs["replay"])
        self.assertEqual(admit.call_args.kwargs["restored_history"], [])

    def test_full_batch_requires_approved_telemetry_quota_and_time(self):
        def proposal(limit):
            return policy.proposal(self.grant, 669, self.reserved,
                {"observed_unix": int(time.time()), "quota": {"used": 0, "reserved": 0, "total": 2 * limit}})

        with self.assertRaisesRegex(ValueError, "STAGE_RESERVE_CANNOT_FIT"):
            proposal(10230)
        self.assertEqual(proposal(14400)["calls"], 100)
        self.grant["continuation"]["pr211_call_bound"] = {
            "telemetry_sha256": "a" * 64, "overhead_seconds": 7200, "call_seconds": 6}
        self.assertEqual(proposal(14400)["calls"], 669)
        self.assertEqual(proposal(12000)["calls"], 295)
        self.grant["continuation"]["pr211_call_bound"]["call_seconds"] = 7
        self.assertEqual(proposal(14400)["calls"], 595)

    @unittest.skipUnless(sys.platform == "linux", "Kaggle parent timer uses Linux signals")
    def test_parent_deadline_interrupts_blocked_io_and_restores_alarm(self):
        handler = signal.getsignal(signal.SIGALRM)
        with self.assertRaisesRegex(TimeoutError, "SUPERVISED_PARENT_DEADLINE_LAUNCH"):
            with supervision.parent_deadline(time.monotonic() + 0.03, "launch"):
                time.sleep(0.5)
        self.assertEqual(signal.getsignal(signal.SIGALRM), handler)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0, 0))

    def test_restore_and_recheck_12_ancestors_and_preserve_669_ordinals(self):
        cohort = journal.synthetic_cohort()
        cohort_sha = digest(cohort)
        campaign = contract.campaign(dict.fromkeys(contract.planning.MODELS, cohort), cohort_sha)
        identity = contract.native_identity("minicpm4")
        history, ancestors = [], []
        capsule = self.root / "capsule"
        capsule.mkdir()
        for i in range(12):
            source = self.root / ("attempt-" + str(i))
            run_id = source.name
            generation = contract.V5_SOURCE if i < 10 else contract.PR211_SOURCE
            ancestor_identity = {**identity, "implementation_sha256": generation}
            records = []
            for sample in cohort["samples"][258*i:min(258*(i+1), 3094)]:
                invalid = sample["ordinal"] < 147
                records.append({"sample_id": sample["sample_id"], "image_sha256": sample["image_sha256"],
                    "status": "INVALID" if invalid else "SUCCESS", "label": None if invalid else "Level04",
                    "raw_sha256": "a" * 64, "native_calls": 1, "attempts": 1})
            plan = {"synthetic_serial": i, "identity": ancestor_identity}
            write(source / "plan.json", plan)
            write(source / "campaign.json", campaign)
            write(source / "history.json", history)
            write(source / "raw.json", records)
            h = {"run_id": run_id, "attempt_id": run_id + "-reservation", "identity": ancestor_identity,
                 "series_id": campaign["series"]["minicpm4"], "cohort_sha256": cohort_sha,
                 "parent_history_sha256": digest(history), "action": "resume" if i else "initial",
                 "records": records, "evidence_sha256": digest(runtime.members(source)), "repair": None}
            file = f"ancestor-{i:04d}.bin"
            ancestors.append({"file": file, "sha256": export(source, capsule / file), "plan_sha256": digest(plan)})
            history.append(h)

        def planned(chain):
            return contract.plan(campaign, cohort, identity, chain, action="resume", run_id="serial-23",
                                 attempt_id="serial-23-attempt", max_calls=669, max_seconds=14400)

        next_plan = planned(history)
        self.assertEqual(next_plan["counts"], {"SUCCESS": 2947, "INVALID": 147, "NOT_ATTEMPTED": 669})
        self.assertEqual(next_plan["scheduled_ordinals"], list(range(3094, 3763)))
        self.assertEqual(next_plan["history_sha256"], digest(history))
        final_records = [{**history[0]["records"][-1], "sample_id": sample["sample_id"],
            "image_sha256": sample["image_sha256"]} for sample in cohort["samples"][3094:]]
        last = {**history[-1], "identity": identity, "parent_history_sha256": digest(history),
            "records": final_records, "run_id": "serial-23", "attempt_id": "serial-23-attempt"}
        final_view = contract.history_view([*history, last], identity, action="resume")
        checked = contract.planning.checked_history(final_view, cohort["samples"], cohort_sha, digest(final_view))
        self.assertEqual(sum(len(item["records"]) for item in checked), 3763)
        bad = deepcopy(history)
        bad[-1]["identity"]["implementation_sha256"] = "d" * 64
        with self.assertRaisesRegex(ValueError, "FOREIGN_HISTORY"):
            planned(bad)
        bad[-1]["identity"]["implementation_sha256"] = contract.V5_SOURCE
        with self.assertRaisesRegex(ValueError, "FOREIGN_HISTORY"):
            planned(bad)
        value = {"request": {"history": history, "campaign": campaign}, "ancestors": ancestors, "cohort": cohort}
        work = self.root / "work"
        deadline = time.monotonic() + 120
        # Synthetic history records stand in for native results. The actual
        # ZIP checks, install, file hashes and planner run against real bytes.
        with patch.object(runtime, "recover", side_effect=history) as replay:
            self.assertEqual(ui.restore_released_history(capsule, value, work, deadline), history)
            self.assertEqual(replay.call_count, 12)
            admission.history_admission(value["request"] | {"work": str(work), "model_key": "minicpm4"})
            runtime.verify_restored_history(work, history, ancestors, deadline)
            self.assertEqual(replay.call_count, 12)
        raw = work / history[-1]["run_id"] / "raw.json"
        stat = raw.stat()
        raw.write_bytes(raw.read_bytes().replace(b"SUCCESS", b"INVALID", 1))
        os.utime(raw, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        with self.assertRaisesRegex(ValueError, "HISTORY_EVIDENCE_CHANGED"):
            runtime.verify_restored_history(work, history, ancestors, deadline)

    def test_cutover_requires_settled_prefix_and_final_checks_all_release_exports(self):
        registered = {"scope": {"source_sha256": contract.V5_SOURCE}}
        old = {"scope": {"source_sha256": contract.PR211_SOURCE}, "continuation": {"first_serial": 20, "prefix_number": 22}}
        current = {"scope": {"source_sha256": "c" * 64}, "continuation": self.grant["continuation"]}
        reader = route.Continuation.__new__(route.Continuation)
        reader.root = self.root
        reader.grant = registered
        reader.registration = {"locator": "v5", "exports": {"v5": 1}}
        reader.historical_repo = self.root / "v5"
        reader.previous_runtime = self.root / "pr211", "pr211", {"pr211": 2}
        reader.previous_authority = old, "pr211", self.root / "pr211"
        reader.runtime_grant = current
        reader.runtime_locator = "current"
        reader.runtime_exports = {"current": 3}
        for serial, expected in ((19, registered), (20, old), (22, old), (23, current), (24, current)):
            self.assertEqual(reader.authority_for({"ticket": {"payload": {"number": serial}}})[0], expected)
        self.assertEqual(reader.release_export_paths(), {"v5", "pr211", "current"})
        with patch.object(route, "authenticate", side_effect=[registered, old, current]) as auth:
            reader.verify_release_exports({"v5": 1, "pr211": 2, "current": 3})
        self.assertEqual([call.args[0] for call in auth.call_args_list], ["v5", "pr211", "current"])
        reader.runtime_grant = None
        for serial in (22, 23):
            with patch.object(reader, "state", return_value={"active": {"serial": serial}}), \
                    self.assertRaisesRegex(ValueError, "SETTLED_PREFIX"):
                reader.runtime_proposal()
        reader.runtime_grant = current
        with self.assertRaisesRegex(ValueError, "FROZEN_V5_CHECKOUT_REQUIRED"):
            reader.runtime_proposal()

    def test_current_release_authenticates_both_predecessors_and_binds_pr211_grant(self):
        reader = route.Continuation.__new__(route.Continuation)
        reader.registration = {"locator": "v5", "exports": {}}
        identity = contract.native_identity("minicpm4")
        base = deepcopy(self.grant)
        base.pop("continuation")
        base.update(dict.fromkeys(("schema", "authorization", "campaign_id", "public_key",
            "operator_host_sha256", "provider_max_age_seconds", "recovery", "repair"), "fixture"))
        base["scope"].update(source_sha256=contract.V5_SOURCE, identity=identity | {
            "implementation_sha256": contract.V5_SOURCE})
        previous = deepcopy(base)
        previous["scope"].update(source_sha256=contract.PR211_SOURCE, identity=identity | {
            "implementation_sha256": contract.PR211_SOURCE})
        previous["continuation"] = {"first_serial": 20, "prefix_number": 22,
            "previous_grant_sha256": digest(base), "registration_sha256": digest(reader.registration)}
        current = deepcopy(previous)
        current["scope"].update(source_sha256=identity["implementation_sha256"], identity=identity)
        current["continuation"] = self.grant["continuation"] | {"prefix_number": 28,
            "previous_grant_sha256": digest(previous), "registration_sha256": digest(reader.registration)}
        previous_args = self.root / "pr211", "pr211", {}
        grants = {"v5": base, "pr211": previous, "current": current}
        with patch.object(route, "authenticate", side_effect=lambda loc, *_, **__: grants[loc]) as authenticate:
            reader.load_authority(self.root / "v5", ("current", {}), previous_args)
            self.assertEqual(reader.authority_for({"ticket": {"payload": {"number": 22}}})[0], previous)
            self.assertEqual(reader.authority_for({"ticket": {"payload": {"number": 23}}})[0], current)
            self.assertEqual([call.kwargs.get("repo") for call in authenticate.call_args_list],
                             [self.root / "v5", self.root / "pr211", None])
            with self.assertRaisesRegex(ValueError, "PREVIOUS_RUNTIME_RELEASE_REQUIRED"):
                reader.load_authority(self.root / "v5", ("current", {}))
            current["continuation"]["previous_grant_sha256"] = digest(base)
            with self.assertRaisesRegex(ValueError, "TRANSITION_BINDING"):
                reader.load_authority(self.root / "v5", ("current", {}), previous_args)
            current["continuation"]["previous_grant_sha256"] = digest(previous)
            current["caps"]["job_seconds"] += 1
            with self.assertRaisesRegex(ValueError, "TRANSITION_SCOPE"):
                reader.load_authority(self.root / "v5", ("current", {}), previous_args)


if __name__ == "__main__":
    unittest.main()
