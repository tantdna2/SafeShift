"""CPU-only deadline, custody and three-source continuation regressions."""
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import os
import shutil
import signal
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_minicpm_fulltrain_execution as fixtures
from safeshift.candidates import fulltrain_run as journal
from safeshift.fulltrain import admission, contract, minicpm_offline as policy, minicpm_ui as ui, runtime, supervision
from safeshift.fulltrain import minicpm_execution as execution, minicpm_prenative as closure, minicpm_release as authority
from safeshift.pilot.artifacts import export, read, sha, write
from safeshift.pilot.contract import digest
from scripts import minicpm_offline_continuation as route, minicpm_offline_fast as fast, owner_verify_minicpm_offline as owner


@unittest.skipUnless(sys.platform == "linux", "Kaggle parent timer uses Linux signals")
class TimeoutCustodyTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.ExecutionTests.setUpClass.__func__)
    tearDownClass = classmethod(fixtures.ExecutionTests.tearDownClass.__func__)
    setUp = fixtures.ExecutionTests.setUp
    make_ticket = fixtures.ExecutionTests.make_ticket

    def test_authenticated_restore_timeout_seals_only_positive_pre_dispatch_evidence(self):
        download, inputs = self.root / "download", self.root / "input"
        work = download / "minicpm-fulltrain"
        request = self.value["request"]
        request.update(work=str(work), scratch=str(self.root / "scratch"))
        self.grant["continuation"] = {"previous_source_sha256": contract.PR211_SOURCE}
        proof = {"synthetic_authority_proof": True}
        self.grant["approvals"][authority.PROOF_KEY] = digest(proof)
        ticket = self.make_ticket(self.value)
        mount = inputs / self.value["capsule_ref"].split("/")[1]
        capsule_sha = write(mount / ui.MARKER, self.value)
        ticket_path = mount / execution.MARKER
        write(ticket_path, ticket | {"signature": "0" * 768})
        download.mkdir()
        claims = download / "minicpm-fulltrain-claims"

        def load(locator, *, repo, capture):
            capture.update(proof)
            return self.grant

        def restore(directory, value, staged, deadline):
            self.assertEqual(set(authority.claims_snapshot()), {"launch.json"})
            write(staged / "copy.json", {"source": "immutable capsule"})
            time.sleep(4)

        # Only live release retrieval, Kaggle path validation and restoration
        # latency are simulated. RSA, claims, timeout, ZIP and readers are real.
        with ExitStack() as stack:
            for obj, name, result in ((authority, "validate", self.grant), (ui, "validate", self.value),
                (authority, "uses_proof", True), (os, "statvfs", SimpleNamespace(f_flag=os.ST_RDONLY))):
                stack.enter_context(patch.object(obj, name, return_value=result))
            stack.enter_context(patch.object(authority, "load", side_effect=load))
            stack.enter_context(patch.object(authority, "CLAIMS", claims))
            stack.enter_context(patch.object(ui, "restore_released_history", side_effect=restore))
            stack.enter_context(patch.object(policy, "LAUNCH_SECONDS", 1))
            launch = stack.enter_context(patch.object(runtime, "launch"))
            with self.assertRaisesRegex(ValueError, "SIGNATURE_INVALID"):
                execution.run_capsule(inputs, capsule_sha, self.locator, bounded_launch=True)
            self.assertFalse(work.exists())
            self.assertFalse(claims.exists())
            ticket_path.unlink()
            write(ticket_path, ticket)
            output = execution.run_capsule(inputs, capsule_sha, self.locator, bounded_launch=True)
            launch.assert_not_called()
        self.assertFalse(list(download.glob("minicpm-history-*")))
        self.assertFalse(list(output.glob("*-process.json")))
        snapshot = download / "data/processed/fresh_fulltrain_code" / request["source_sha256"]
        for name in contract.sources():
            dest = snapshot / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(contract.ROOT / name, dest)
        active = {"value": self.value, "ticket": ticket}

        def verify(**options):
            return closure.verify_download(download, active, self.locator, self.grant["campaign_id"],
                proof_sha256=digest(proof), **options)

        local = verify(bounded_launch=True)
        self.assertEqual(local["disposition"], closure.DISPOSITION)
        self.assertEqual(local["last_stage"], "launch")
        self.assertIs(local["child_launched"], False)
        self.assertEqual(local["reserved_after"], ticket["payload"]["reserved_after"])
        with self.assertRaisesRegex(ValueError, "LAUNCH_STOP_UNVERIFIED"):
            verify()
        job = self.value["job"]
        files = {name: sha(mount / name) for name in (ui.MARKER, execution.MARKER)}
        provider = {"schema": closure.PROVIDER_SCHEMA, "local": local, "provider_job": job, "ticket_job": job,
            "provider": {"job_id": job, "kernel_id": 23, "version": 1, "state": "ERROR",
                         "notebook_code_sha256": ticket["payload"]["notebook_code_sha256"],
                         "remote_notebook_sha256": "a" * 64, "safeshift_metadata": "MATCHED"},
            "accelerator": {"enable_gpu": True, "machine_shape": None,
                            "scope": "CURRENT_KERNEL_METADATA_NOT_EXECUTION_TIME_PROOF"},
            "capsule": {"private": True, "version": 1, "files": files},
            "output": {"inventory": closure.inventory(download), "pairs": {local["supervisor"]: local["supervisor_sha256"]},
                       "sidecar_sha256": local["sidecar_sha256"], "log_sha256": "e" * 64}}
        self.assertEqual(closure.verify_provider(provider, local, active, files), provider)
        provider["provider"]["state"] = "RUNNING"
        with self.assertRaisesRegex(ValueError, "KERNEL_IDENTITY"):
            closure.verify_provider(provider, local, active, files)
        # A sealed pair and launch claim without the positive dispatch
        # receipt must still block, even with no attempt or native files.
        output.with_suffix(".zip").unlink()
        output.with_suffix(".zip.sha256.json").unlink()
        (output / "checksums.json").unlink()
        (output / "launch-stop.json").unlink()
        export(output, output.with_suffix(".zip"))
        with self.assertRaisesRegex(ValueError, "LAUNCH_STOP_UNVERIFIED"):
            verify(bounded_launch=True)

    def test_retention_or_export_timeout_preserves_sealed_attempt_and_failure_evidence(self):
        for stage in ("retention", "export"):
            with self.subTest(stage=stage), ExitStack() as stack:
                work, scratch = self.root / stage / "work", self.root / stage / "scratch"
                scratch.mkdir(parents=True)
                request = deepcopy(self.value["request"])
                request.update(inputs=str(self.root / "inputs"), work=str(work), scratch=str(scratch))
                request["plan"]["max_seconds"] = 14400
                attempt = work / request["plan"]["run_id"]
                write(attempt / "raw.json", {"preserved": stage})
                archive = attempt.with_suffix(".zip")
                before = export(attempt, archive)
                sidecar = Path(str(archive) + ".sha256.json")
                sidecar_bytes = sidecar.read_bytes()
                claims = self.root / stage / "claims"
                write(claims / "launch.json", {"time_unix": time.time()})
                active = {"grant": self.grant | {"continuation": {"previous_source_sha256": contract.PR211_SOURCE}},
                    "value": self.value, "claims": claims, "capsule_directory": self.root,
                    "locator": self.locator, "ticket": self.ticket, "context_file": str(work / "context.json")}
                for obj, name, result in ((admission, "validate_request", None), (admission.memory, "observe", None),
                    (admission.memory, "ownership", {}), (authority, "current", active),
                    (authority, "authorize", None), (authority, "claims_snapshot", {})):
                    stack.enter_context(patch.object(obj, name, return_value=result))
                stack.enter_context(patch.object(supervision, "run", side_effect=RuntimeError("SUPERVISED_CHILD_FAILURE")))
                error = TimeoutError("SUPERVISED_PARENT_DEADLINE_" + stage.upper())
                if stage == "retention":
                    stack.enter_context(patch.object(execution, "retain_sealed_trees", side_effect=error))
                    output = admission.launch_prepared(request)
                    self.assertTrue(output.with_suffix(".zip").is_file())
                    self.assertEqual(read(output / "retention_failure.json")["message"], str(error))
                    with self.assertRaisesRegex(ValueError, "UI_SUPERVISOR_BINDING"):
                        fast.verify_supervisor(output, request)
                else:
                    stack.enter_context(patch.object(execution, "retain_sealed_trees", return_value={}))

                    def interrupted_export(control, partial):
                        partial.write_bytes(b"incomplete supervisor")
                        raise error

                    stack.enter_context(patch.object(supervision, "export", side_effect=interrupted_export))
                    with self.assertRaisesRegex(TimeoutError, str(error)):
                        admission.launch_prepared(request)
                    (receipt,) = (work / "supervision").glob("*-export-failure.json")
                    self.assertEqual(read(receipt)["status"], "BLOCKED")
                    self.assertEqual(read(receipt)["failure"]["message"], str(error))
                    self.assertEqual(read(receipt)["reservation"], "KEEP")
                    self.assertFalse(list((work / "supervision").glob("*.zip")))
                    self.assertTrue(list((work / "supervision").glob("*.zip.partial")))
                self.assertEqual(read(attempt / "raw.json"), {"preserved": stage})
                self.assertEqual(sha(archive), before)
                self.assertEqual(sidecar.read_bytes(), sidecar_bytes)

    def test_owner_verifier_marks_missing_export_blocked_before_provider_call(self):
        download, output = self.root / "data/processed/download", self.root / "data/processed/verification"
        download.mkdir(parents=True)
        active = {"ticket": self.ticket, "value": self.value}
        reader = SimpleNamespace(state=lambda: {"active": active}, pre_native_local=lambda path, item:
            closure.verify_download(path, item, self.locator, self.grant["campaign_id"], bounded_launch=True))
        with patch.object(route, "ROOT", self.root), patch.object(route, "Continuation", return_value=reader), \
                patch.object(owner, "provider_closure") as verify:
            with self.assertRaisesRegex(ValueError, "MINICPM_OWNER_VERIFIER_BLOCKED"):
                owner.pre_native_closure(download, download, output, owner_performs_network=True)
            verify.assert_not_called()
        blocked = read(output / "BLOCKED.json")
        self.assertEqual(blocked["gate"], "MINICPM_PRE_NATIVE_SUPERVISOR_ONLY")
        self.assertFalse(blocked["journal_written"])


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
