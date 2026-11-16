"""CPU synthetic final-result reader tests; every socket is prohibited.

GitHub original qualification and full native vector replay are explicit seams.
Final certificate parsing, mirrored disk chains, actual reservation accounting,
3763 result/attempt provenance, resource ZIPs and reader validation are real code.
"""
from contextlib import ExitStack
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
import zipfile

from scripts import train3763_continuation as c
from scripts import train3763_results as results
from scripts import owner_verify_train3763_continuation as online
from safeshift.pilot.artifacts import read, write, sha
from safeshift.pilot.contract import digest
from test_internvl3763_campaign import fixture


class Ledger:
    """Synthetic disk registration; unmodified production read/append algorithms."""
    events = c.campaign.Ledger.events
    _budget = c.campaign.Ledger._budget
    budget = c.campaign.Ledger.budget
    append = c.campaign.Ledger.append
    intents = c.campaign.Ledger.intents
    open_intent = c.campaign.Ledger.open_intent
    histories = c.campaign.Ledger.histories
    summary = c.campaign.Ledger.summary

    def __init__(self, root, grant):
        self.root, self.mirror = root/"ledger", root/"ledger-mirror"
        self.grant = grant
        for path in (self.root, self.mirror):
            write(path/"registration.json", {"grant": grant, "scope": "SYNTHETIC_CPU_ONLY"})


class OfficialFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Build the finite campaign once. Each test gets private copies of its
        # immutable bytes and fresh authority/native boundary mocks.
        global CAMPAIGN_CACHE
        if CAMPAIGN_CACHE is None:
            cache = OfficialFixture()
            try:
                cache.construct()
            except BaseException:
                cache.doCleanups()
                raise
            finally:
                cache.stack.close()
            CAMPAIGN_CACHE = cache
        cls.cached = CAMPAIGN_CACHE

    def setUp(self):
        cache = self.cached
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        shutil.copytree(cache.repo, self.repo, dirs_exist_ok=True)
        self.root = self.repo/"data/processed"
        for name in ("template", "grant", "history", "by_archive", "intents", "data", "notebook", "start", "spec", "config",
                "manifest", "report", "exports", "owner", "admission"):
            setattr(self, name, deepcopy(getattr(cache, name)))
        for data in self.data.values():
            data["path"] = self.repo/data["path"].relative_to(cache.repo)
        self.ledger = Ledger.__new__(Ledger)
        self.ledger.root, self.ledger.mirror, self.ledger.grant = self.root/"ledger", self.root/"ledger-mirror", self.grant
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        for obj, name, replacement in ((c.runtime, "ROOT", self.repo), (c.runtime, "source_spec", Mock(return_value=self.spec)),
                (c.runtime, "configuration", Mock(return_value=self.config)), (c.runtime, "sealed_history", Mock(side_effect=self.sealed)),
                (c, "source_check", Mock()), (c, "authenticate", Mock(return_value={"base_head_sha256": digest(self.intents[10])})),
                (c, "baseline_owner", Mock(return_value={"kernel_id": 1011, "archive_sha256": self.data[11]["sha256"]})),
                (c, "original_handoff", Mock(return_value={"status": "SYNTHETIC_PREPARED"})), (c, "verify_local", Mock(side_effect=self.verify_local))):
            self.stack.enter_context(patch.object(obj, name, replacement))
        self.stack.enter_context(patch("socket.socket", side_effect=AssertionError("NO_NETWORK")))
        self.route = c.Continuation(self.root/"route", self.ledger)

    def construct(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.root = self.repo/"data/processed"
        self.root.mkdir(parents=True)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch("socket.socket", side_effect=AssertionError("NO_NETWORK")))
        self.template, self.grant, _ = fixture(self.root/"ledger")
        spec, config = c.runtime.source_spec(), c.runtime.configuration()
        self.spec, self.config = spec, config
        self.stack.enter_context(patch.object(c.runtime, "source_spec", return_value=spec))
        self.stack.enter_context(patch.object(c.runtime, "configuration", return_value=config))
        self.stack.enter_context(patch.object(c.runtime, "ROOT", self.repo))
        self.grant["caps"].update(total_calls=4500, total_jobs=100, total_gpu_seconds=430000, job_calls=1000, job_seconds=7200)
        self.ledger = Ledger(self.root, self.grant)
        self.cohort = self.template["bindings"]["runtime"]["execution_request"]["cohort"]
        self.history, self.by_archive, self.intents, self.data = [], {}, [], {}
        self.notebook = c.json_bytes({"cells": [{"cell_type": "code", "source": ["# SYNTHETIC_ONLY\n"]}]})
        self.start = time.time()-1000
        self.stack.enter_context(patch.object(c.runtime, "sealed_history", side_effect=self.sealed))
        self.stack.enter_context(patch.object(c, "source_check"))
        self.stack.enter_context(patch.object(c, "authenticate", side_effect=lambda *a: {"base_head_sha256": digest(self.intents[10])}))
        self.stack.enter_context(patch.object(c, "baseline_owner", side_effect=lambda *a: {"kernel_id": 1011,
            "archive_sha256": self.data[11]["sha256"]}))
        self.stack.enter_context(patch.object(c, "original_handoff", return_value={"status": "SYNTHETIC_PREPARED"}))
        self.stack.enter_context(patch.object(c, "verify_local", side_effect=self.verify_local))
        # Original35: eleven INTENTs, three aborts, seven collected jobs,
        # fourteen harmless synthetic diagnostics; original11 is still open.
        schedules = {1: (0, 1, "ABORT"), 2: (0, 1, "ABORT"), 3: (0, 1, "FAIL"),
            4: (0, 1, "PASS"), 5: (1, 1, "ABORT"), 6: (1, 1, "FAIL"), 7: (1, 1, "PASS"),
            8: (2, 1, "PASS"), 9: (3, 200, "PASS"), 10: (203, 120, "PASS"), 11: (323, 200, "PASS")}
        for number in range(1, 12):
            start, calls, outcome = schedules[number]
            request = self.request(number, start, calls, 1800 if number <= 8 else 7200)
            intent = self.ledger.append("INTENT", request=request, reserved_calls=calls,
                reserved_gpu_seconds=request["plan"]["max_seconds"]*2, unix=self.start+number)
            self.intents.append(intent)
            if number == 11:
                self.make_archive(intent, start, start+calls, "PASS")
            elif outcome == "ABORT":
                self.ledger.append("ABORTED_PRE_SUBMIT", intent_sha256=digest(intent), refund=False)
            else:
                data = self.make_archive(intent, start, start+calls if outcome == "PASS" else start, outcome)
                self.ledger.append("COLLECTED", intent_sha256=digest(intent), sha256=data["sha256"],
                    archive=str(data["path"]), plan=request["plan"], history=data["history"],
                    provider=data["proof"]["provider"], verification={"status": outcome})
                self.history.append(data["history"])
        # Put diagnostics before INTENT35, preserving exact original open head.
        rows = self.ledger.events(); last = rows.pop()
        rows += [{"kind": "SYNTHETIC_CPU_DIAGNOSTIC", "campaign_sha256": digest(self.grant), "unix": self.start+10.1+i/100}
            for i in range(13)]
        rows.append({"kind": "MEASURED", "source_sha256": digest(spec), "safe_calls": 200,
            "overhead_seconds": 2192, "per_call_seconds": 25, "campaign_sha256": digest(self.grant), "unix": self.start+10.9})
        rows.append(last)
        for index, row in enumerate(rows):
            row["previous"] = digest(rows[index-1]) if index else None
            for root in (self.ledger.root, self.ledger.mirror):
                (root/f"journal-{index+1:06d}.json").write_bytes(c.json_bytes(row))
        self.intents[-1] = rows[-1]
        self.make_archive(rows[-1], 323, 523, "PASS", replace=True)
        self.route = c.Continuation.initialize(self.root/"route", self.root/"route-mirror", self.ledger,
            {"/issues/comments/1234": {"body": "STALE_SNAPSHOT_MUST_NOT_BE_USED"}}, {})
        self.append_completion(self.intents[-1])
        for number, start in enumerate(range(523, 3763, 200), 12):
            calls = min(200, 3763-start)
            request = self.request(number, start, calls, 7200)
            intent = {"kind": "INTENT", "campaign_sha256": digest(self.grant), "previous": digest(self.route.events()[-1]),
                "request": request, "reserved_calls": calls, "reserved_gpu_seconds": 14400, "unix": self.start+number}
            self.intents.append(intent)
            self.route.append("RESERVED_OFFLINE", intent=intent)
            self.make_archive(intent, start, start+calls, "PASS")
            self.append_completion(intent)
        self.manifest = self.route.manifest()
        self.report = {"status": "ALL_ORIGINALS_VERIFIED", "manifest_sha256": digest(self.manifest), "tool_sha256": sha(online.__file__),
            "budget": self.manifest["budget"], "billing_gpu_seconds": "NOT_OBSERVED", "historical": [], "attempts": [], "aborted": []}
        for h in self.manifest["historical_attempts"]:
            number = int(h["intent"]["request"]["plan"]["attempt_id"].split("-")[-1])
            if h["outcome"]["kind"] == "ABORTED_PRE_SUBMIT":
                self.report["aborted"].append({"intent_sha256": digest(h["intent"]), "job": h["intent"]["request"]["job"],
                    "original_abort_sha256": digest(h["outcome"]), "provider_absent_at_final": True,
                    "reserved_calls": h["intent"]["reserved_calls"], "reserved_gpu_seconds": h["intent"]["reserved_gpu_seconds"]})
            else:
                self.report["historical"].append({**deepcopy(self.data[number]["proof"]), "provider_reverified": True})
        self.report["attempts"] = [deepcopy(self.data[i]["proof"]) for i in range(11, 29)]
        self.exports = {}
        self.owner = self.comment(9000, c.FINAL, {"manifest_sha256": digest(self.manifest), "report": self.report,
            "status": "APPROVED_FOR_AGGREGATE_ADMISSION"}, c.authority.OWNER)
        self.admission = self.comment(9001, c.FINAL+"_ADMISSION", {"manifest_sha256": digest(self.manifest), "owner": self.owner,
            "report_sha256": digest(self.report), "status": "RELEASED_FOR_AGGREGATE_ADMISSION"}, "synthetic-reviewer")

    def request(self, number, start, calls, seconds):
        request = deepcopy(self.template)
        p = request["plan"]
        p.update(run_id=f"synthetic180-{number}", attempt_id=f"attempt-{number}", action="initial" if not self.history else "resume",
            max_calls=calls, max_seconds=seconds, scheduled_ordinals=list(range(start, start+calls)), history_sha256=digest(self.history), samples=[])
        request.update(plan_sha256=digest(p), handoff_id=p["run_id"], job=f"nguynanhtn/safeshift-train3763-synthetic180-{number}",
            notebook_sha256=hashlib.sha256(self.notebook).hexdigest(), limits={"max_calls": calls, "job_seconds": seconds, "monitor_seconds": 900})
        binding = request["bindings"]["runtime"]
        old = binding["execution_input"]["ref"]
        binding["execution_input"]["ref"] = f"nguynanhtn/synthetic-capsule-{number}/1"
        request["bindings"]["dataset"]["dataset_sources"] = [binding["execution_input"]["ref"] if r == old else r
            for r in request["bindings"]["dataset"]["dataset_sources"]]
        execution = binding["execution_request"]
        execution.update(history=deepcopy(self.history), plan=p)
        if number != 11:
            # Full image-cohort/native verification is the explicit mocked seam.
            # Initial11 still carries the actual3763 synthetic cohort for reader joins.
            execution["cohort"] = {**execution["cohort"], "samples": []}
        request["bindings"]["dataset"]["execution_request_sha256"] = digest(execution)
        return request

    def make_archive(self, intent, start, end, status, replace=False):
        request = intent["request"]; p = request["plan"]
        number = int(p["attempt_id"].split("-")[-1])
        records = [{**self.cohort["samples"][i], "status": "INVALID" if i == 523 else "SUCCESS", "label": None if i == 523 else "Level02",
            "native_calls": 1, "attempts": 1, "raw_sha256": "f"*64, "hnlo": None, "hnlo_status": c.runtime.HNLO_STATUS} for i in range(start, end)]
        path = self.root/f"attempt-{number}.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, value in {"run/summary.json": {"status": status, "run_id": p["run_id"], "attempt_id": p["attempt_id"],
                    "model_calls": len(records), "counts": dict(Counter(r["status"] for r in records)), "records": records},
                    "run/telemetry.json": {"load_seconds": 2., "gpu_peak_allocated_bytes": 100, "gpu_peak_reserved_bytes": 200,
                        "evidence_kind": "SYNTHETIC_CPU_ONLY"}, "setup/setup-supervisor.json": {"seconds": 3.},
                    "worker-supervisor.json": {"seconds": 4.}}.items():
                z.writestr(name, c.json_bytes(value))
        Path(str(path)+".sha256.json").write_bytes(c.json_bytes({"sha256": sha(path)}))
        h = {"run_id": p["run_id"], "attempt_id": p["attempt_id"], "series_id": p["series_id"], "identity": p["identity"],
            "cohort_sha256": p["cohort_sha256"], "parent_history_sha256": p["history_sha256"], "action": p["action"],
            "records": records, "evidence_sha256": sha(path), "repair": None}
        provider = {"job_id": request["job"] if number != 8 else "nguynanhtn/synthetic-original-distinct-slug8",
            "kernel_id": 1000+number, "state": "COMPLETE", "version": 1}
        proof = {"intent_sha256": digest(intent), "archive_sha256": sha(path), "provider": provider,
            "input_bytes_verified": True, "provider_copy_verified": True,
            "capsule": {"ref": request["bindings"]["runtime"]["execution_input"]["ref"], "version": 1,
                "sha256": digest({"request": request, "campaign_intent": intent}), "request_sha256": digest(request), "intent_sha256": digest(intent)},
            "output": {"sha256": sha(path), "bytes": path.stat().st_size, "sidecar_sha256": sha(str(path)+".sha256.json"), "log_sha256": "e"*64},
            "resources": results.resources(path, intent)}
        receipt = {"status": "OFFLINE_VERIFIED_PROVISIONAL", "verification": {"status": "PASS"}, "history": h,
            "sha256": sha(path), "sidecar_sha256": sha(str(path)+".sha256.json"), "owner_receipt": {"state": "COMPLETE", "version": 1,
                "job": request["job"], "kernel_id": 1000+number, "archive_sha256": sha(path)}}
        data = {"path": path, "sha256": sha(path), "history": h, "proof": proof, "receipt": receipt}
        self.data[number] = data; self.by_archive[sha(path)] = h
        return data

    def sealed(self, path, checksum, plan):
        self.assertEqual(sha(path), checksum)
        h = self.by_archive[checksum]
        self.assertEqual(h["attempt_id"], plan["attempt_id"])
        return deepcopy(h)

    def verify_local(self, intent, grant, path, owner_receipt, **kwargs):
        data = self.data[int(intent["request"]["plan"]["attempt_id"].split("-")[-1])]
        self.assertEqual(sha(path), data["sha256"])
        return deepcopy(data["receipt"])

    def append_completion(self, intent):
        data = self.data[int(intent["request"]["plan"]["attempt_id"].split("-")[-1])]
        name = "artifacts/"+data["path"].name
        for root in (self.route.root, self.route.mirror):
            c._copy(data["path"], c.safe(root, name))
            c._copy(str(data["path"])+".sha256.json", c.safe(root, name+".sha256.json"))
        self.route.append("OFFLINE_VERIFIED_PROVISIONAL", intent_sha256=digest(intent), archive=name,
            ordinals=intent["request"]["plan"]["scheduled_ordinals"], receipt=data["receipt"])
        self.history.append(data["history"])

    def comment(self, number, marker, value, login):
        body = marker+"\n```json\n"+json.dumps(value)+"\n```"
        self.exports["/issues/comments/"+str(number)] = {"id": number, "body": body, "user": {"login": login, "id": 246929698},
            "issue_url": c.authority.API+"/issues/180"}
        return {"comment_id": number, "body_sha256": hashlib.sha256(body.encode()).hexdigest()}

    def seal(self):
        return self.route.reconcile(self.exports, self.owner, self.admission)


class OfficialResultsTests(OfficialFixture):
    def test_before_release_closed_even_when_all_local_outputs_exist(self):
        before = self.ledger.events()
        self.assertEqual(self.route.state()["next_ordinal"], 3763)
        with self.assertRaisesRegex(ValueError, "OFFICIAL_FINAL_RECONCILIATION_REQUIRED"):
            self.route.official_report()
        self.assertEqual(self.ledger.events(), before)

    def test_full_official_coverage_budget_invalid_and_legacy_separation(self):
        old = self.ledger.summary()
        self.seal()
        before = self.ledger.events()
        report = self.route.official_report()
        self.assertEqual(report["status"], "OFFICIAL_RECONCILED_RESULTS")
        self.assertEqual([r["ordinal"] for r in report["records"]], list(range(3763)))
        self.assertEqual(report["counts"], {"SUCCESS": 3762, "INVALID": 1})
        self.assertIsNone(report["records"][523]["record"]["label"])
        self.assertEqual(report["records"][523]["lineage"][0]["attempt_id"], "attempt-12")
        self.assertEqual(report["budget"]["deferred_reservations"], {"jobs": 17, "reserved_calls": 3240, "reserved_gpu_seconds": 244800})
        self.assertEqual((report["budget"]["jobs"], report["budget"]["reserved_calls"], report["budget"]["reserved_gpu_seconds"]), (28, 3768, 316800))
        self.assertEqual(report["budget"]["remaining_gpu_seconds"], 113200)
        self.assertEqual(len(report["attempts"]), 28)
        self.assertEqual(report["observed_resources"]["aborted_before_submit"], 3)
        self.assertEqual(report["observed_resources"]["actual_model_calls"]["observed_sum"], 3763)
        self.assertEqual(report["budget"]["billing_gpu_seconds"], "NOT_OBSERVED")
        self.assertEqual(self.ledger.summary()["counts"], old["counts"])
        self.assertEqual(self.ledger.budget()["reserved_calls"], 528)
        self.assertIsNotNone(self.ledger.open_intent())
        self.assertEqual(self.ledger.events(), before)

    def test_wrong_owner_export_or_missing_admission_never_appends(self):
        for principal in ("unknown", "synthetic-reviewer"):
            bad = deepcopy(self.exports); bad["/issues/comments/9000"]["user"]["login"] = principal
            with self.assertRaisesRegex(ValueError, "AUTHENTIC_AGGREGATE_OWNER"):
                self.route.reconcile(bad, self.owner, self.admission)
        bad = deepcopy(self.exports); del bad["/issues/comments/9001"]
        with self.assertRaisesRegex(ValueError, "MISSING_REAL_GITHUB"):
            self.route.reconcile(bad, self.owner, self.admission)
        self.assertEqual(len(self.ledger.events()), 36)

    def test_final_report_mutation_even_with_rechained_mirrors_is_rejected(self):
        self.seal()
        row = self.ledger.events()[-1]
        row["report"]["budget"]["reserved_gpu_seconds"] = 1
        for root in (self.ledger.root, self.ledger.mirror):
            (root/"journal-000037.json").write_bytes(c.json_bytes(row))
        with self.assertRaisesRegex(ValueError, "OFFICIAL_SEALED_REPORT_DRIFT"):
            self.route.official_report()

    def test_archive_or_mirror_mutation_blocks_official_read(self):
        self.seal()
        with (self.route.mirror/"artifacts/attempt-28.zip").open("ab") as f:
            f.write(b"TAMPER")
        with self.assertRaisesRegex(ValueError, "ARCHIVE_LOST_OR_CHANGED"):
            self.route.official_report()

    def test_late_native_failure_never_creates_a_formal_event(self):
        original = self.verify_local
        def late(intent, *args, **kwargs):
            if intent["request"]["plan"]["attempt_id"] == "attempt-28":
                raise ValueError("SYNTHETIC_DELAYED_TRACE_FAILURE")
            return original(intent, *args, **kwargs)
        with patch.object(c, "verify_local", side_effect=late), self.assertRaisesRegex(ValueError, "DELAYED_TRACE"):
            self.seal()
        self.assertEqual(len(self.ledger.events()), 36)

    def test_authenticated_account_record_cannot_override_raw_resource_evidence(self):
        state, forged = self.route.state(), deepcopy(self.manifest)
        state["budget"]["reserved_gpu_seconds"] = forged["budget"]["reserved_gpu_seconds"] = 1
        with self.assertRaisesRegex(ValueError, "OFFICIAL_TOTAL_BUDGET_DRIFT"):
            results._reservations(self.route, forged, state)
        self.report["attempts"][-1]["resources"]["actual_model_calls"] = 0
        self.owner = self.comment(9000, c.FINAL, {"manifest_sha256": digest(self.manifest), "report": self.report,
            "status": "APPROVED_FOR_AGGREGATE_ADMISSION"}, c.authority.OWNER)
        self.admission = self.comment(9001, c.FINAL+"_ADMISSION", {"manifest_sha256": digest(self.manifest), "owner": self.owner,
            "report_sha256": digest(self.report), "status": "RELEASED_FOR_AGGREGATE_ADMISSION"}, "synthetic-reviewer")
        with self.assertRaisesRegex(ValueError, "FINAL_RESOURCE_PROOF_DRIFT"):
            self.seal()
        self.assertEqual(len(self.ledger.events()), 36)

    def test_wrong_authorized_admission_principal_or_body_is_not_a_release(self):
        bad = deepcopy(self.exports)
        bad["/issues/comments/9001"]["user"]["login"] = "untrusted-snapshot"
        with self.assertRaisesRegex(ValueError, "AGGREGATE_REVIEWER_RELEASE"):
            self.route.reconcile(bad, self.owner, self.admission)
        bad = deepcopy(self.exports); bad["/issues/comments/9001"]["body"] += "edited"
        with self.assertRaisesRegex(ValueError, "COMMENT_HASH_ID_DRIFT"):
            self.route.reconcile(bad, self.owner, self.admission)
        self.assertEqual(len(self.ledger.events()), 36)

    def test_nonfinite_resource_and_missing_observations_are_never_zero_filled(self):
        rows = [{"resources": {"setup_seconds": None, "worker_seconds": 2., "load_seconds": None, "actual_model_calls": 0}}]
        observed = results._observed(rows)
        self.assertIsNone(observed["setup_seconds"]["observed_sum"])
        self.assertEqual(observed["setup_seconds"]["missing_attempts"], 1)
        rows[0]["resources"]["worker_seconds"] = float("nan")
        with self.assertRaisesRegex(ValueError, "NONFINITE_RESOURCE"):
            results._observed(rows)


class FinalProviderVerificationTests(OfficialFixture):
    def run_owner_verifier(self, destination, *, fail_last=False):
        calls = {"observe": [], "capsule": [], "download": [], "github": []}
        all_data = [self.data[i] for i in range(1, 29) if i not in (1, 2, 5)]
        by_job = {d["proof"]["provider"]["job_id"]: d for d in all_data}
        client = Mock()
        client.kernels_list_with_response.return_value = NS(kernels=[NS(ref=k) for k in by_job], next_page_token=None)
        def get(path):
            calls["github"].append(path)
            return {"body": "SYNTHETIC_FRESH_PLATFORM_RESPONSE"}
        def observe(client, job, version, notebook, sources, **kw):
            calls["observe"].append((job, version, kw.get("kernel_id"), sources))
            if fail_last and job == self.data[28]["proof"]["provider"]["job_id"]:
                raise ValueError("SYNTHETIC_LATE_PROVIDER_VERSION_CHANGED")
            self.assertEqual(version, 1)
            return deepcopy(by_job[job]["proof"]["provider"])
        def capsule(client, request, intent, folder):
            calls["capsule"].append((request["job"], request["bindings"]["runtime"]["execution_input"]["ref"], digest(intent)))
            return deepcopy(self.data[int(request["plan"]["attempt_id"].split("-")[-1])]["proof"]["capsule"])
        def download(client, job, version, archive, checksum, folder):
            calls["download"].append((job, version, checksum))
            shutil.copyfile(archive, folder/Path(archive).name)
            shutil.copyfile(str(archive)+".sha256.json", str(folder/Path(archive).name)+".sha256.json")
            return deepcopy(by_job[job]["proof"]["output"])
        with patch.object(online, "load_companion", return_value=c), patch.object(c.authority, "get", side_effect=get), \
                patch.object(c.operator, "api", return_value=client), patch.object(c.campaign, "load", return_value=self.grant), \
                patch.object(c.campaign, "bind"), patch.object(c.subprocess, "check_output", return_value=self.notebook), \
                patch.object(c.manual, "observe_kernel", side_effect=observe), patch.object(c.operator, "verify_execution_input", side_effect=capsule), \
                patch.object(c.manual, "download_outputs", side_effect=download):
            if fail_last:
                with self.assertRaisesRegex(ValueError, "OWNER_FINAL_VERIFICATION_BLOCKED:ValueError"):
                    online.verify(self.route, destination, owner_performs_network=True)
                report = None
            else:
                report = online.verify(self.route, destination, owner_performs_network=True)
            self.assertEqual(c.authenticate.call_args.args[2], {"/issues/comments/1234": {"body": "SYNTHETIC_FRESH_PLATFORM_RESPONSE"}})
        client.kernels_push.assert_not_called()
        return report, calls

    def test_all_historical_and_deferred_providers_versions_capsules_are_exercised(self):
        report, calls = self.run_owner_verifier(self.root/"remote-evidence")
        self.assertEqual((len(report["historical"]), len(report["attempts"]), len(report["aborted"])), (7, 18, 3))
        self.assertEqual(len(calls["observe"]), 50)  # real helper queried before and after every one of25 jobs
        self.assertEqual(len(calls["capsule"]), 25)
        self.assertEqual(len(calls["download"]), 25)
        self.assertEqual(calls["github"], ["/issues/comments/1234"])
        self.assertEqual({x[0] for x in calls["download"]}, {d["proof"]["provider"]["job_id"] for i,d in self.data.items() if i not in (1,2,5)})
        self.assertTrue(all(version == 1 for _,version,_ in calls["download"]))
        for job, ref, intent_sha in calls["capsule"]:
            n = int(job.split("-")[-1])
            self.assertEqual(ref, f"nguynanhtn/synthetic-capsule-{n}/1")
            self.assertEqual(intent_sha, digest(self.intents[n-1]))
        self.assertEqual(len(self.ledger.events()), 36)

    def test_failure_at_last_provider_preserves_proofs_without_success_or_append(self):
        directory = self.root/"remote-delayed-failure"
        _, calls = self.run_owner_verifier(directory, fail_last=True)
        self.assertGreater(len(calls["download"]), 20)
        self.assertFalse((directory/"report.json").exists())
        self.assertEqual(read(directory/"BLOCKED.json")["status"], "BLOCKED")
        self.assertTrue((directory/"historical-1/proof.json").is_file())
        self.assertEqual(len(self.ledger.events()), 36)
        with self.assertRaisesRegex(ValueError, "FINAL_RECONCILIATION_REQUIRED"):
            self.route.official_report()


CAMPAIGN_CACHE = None


def tearDownModule():
    if CAMPAIGN_CACHE is not None:
        CAMPAIGN_CACHE.doCleanups()


if __name__ == "__main__":
    unittest.main()
