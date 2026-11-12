"""CPU synthetic continuation state machine. Socket construction is forbidden.

Native verification and historical provider/ledger transport are explicit seams
in route tests; archive integrity and authority are tested separately below.
"""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import shutil
import struct
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from scripts import train3763_continuation as c
from scripts import owner_verify_train3763_continuation as online
from safeshift.pilot.artifacts import write, read, sha, export
from safeshift.pilot.contract import digest
from test_internvl3763_campaign import fixture
from test_train3763_manual import ManualFixture


class SyntheticLedger:
    """Tiny disk-backed mirrored transport; never a production ledger fixture."""
    def __init__(self, root, grant, intent, history, custody):
        self.root, self.mirror, self.grant = root / "ledger", root / "ledger-mirror", grant
        self.history, self.custody = history, custody
        self._budget = {"caps": deepcopy(grant["caps"]), "extension": None,
            "jobs": 11, "reserved_calls": 528, "reserved_gpu_seconds": 72000}
        write(self.root / "registration.json", {"notice": "SYNTHETIC", "grant": grant})
        write(self.mirror / "registration.json", {"notice": "SYNTHETIC", "grant": grant})
        first = self.append("INTENT", request=intent["request"], reserved_calls=323, reserved_gpu_seconds=1)
        self.append("COLLECTED", intent_sha256=digest(first), sha256=custody[0]["sha256"],
            provider={"job_id": "nguynanhtn/synthetic-historical", "kernel_id": 10, "state": "COMPLETE", "version": 1})
        for n in range(32):
            self.append("SYNTHETIC_HISTORICAL", ordinal=n)
        self.append("INTENT", **{k: v for k, v in intent.items() if k not in ("previous", "kind")})

    def events(self):
        names = sorted(p.name for p in self.root.glob("journal-*.json"))
        c.require(names == sorted(p.name for p in self.mirror.glob("journal-*.json")), "MIRROR_LOSS")
        result = []
        for n, name in enumerate(names, 1):
            c.require(name == f"journal-{n:06d}.json", "GAP")
            c.require((self.root / name).read_bytes() == (self.mirror / name).read_bytes(), "DIVERGED")
            row = read(self.root / name)
            c.require(row["previous"] == (digest(result[-1]) if result else None), "CHAIN")
            result.append(row)
        return result

    def append(self, kind, **values):
        rows = self.events()
        row = {"kind": kind, "previous": digest(rows[-1]) if rows else None, "unix": time.time(), **values}
        c._pair(self.root, self.mirror, f"journal-{len(rows)+1:06d}.json", row)
        return row

    def open_intent(self):
        return self.events()[34]

    def budget(self):
        return deepcopy(self._budget)

    def histories(self):
        return deepcopy(self.history), deepcopy(self.custody)


def history(request, start, end, previous, checksum):
    p = request["plan"]
    cohort = request["bindings"]["runtime"]["execution_request"]["cohort"]
    return {"run_id": p["run_id"], "attempt_id": p["attempt_id"], "series_id": p["series_id"], "identity": p["identity"],
        "cohort_sha256": digest(cohort), "parent_history_sha256": digest(previous), "action": p["action"], "repair": None,
        "evidence_sha256": checksum, "records": [{**cohort["samples"][i], "status": "SUCCESS", "label": "Level02",
            "native_calls": 1, "attempts": 1, "raw_sha256": "f"*64} for i in range(start, end)]}


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "data/processed"
        self.root.mkdir(parents=True)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch("socket.socket", side_effect=AssertionError("NO_NETWORK")))
        request, grant, _ = fixture(self.root / "ledger")
        spec, config = c.runtime.source_spec(), c.runtime.configuration()
        self.stack.enter_context(patch.object(c.runtime, "source_spec", return_value=spec))
        self.stack.enter_context(patch.object(c.runtime, "configuration", return_value=config))
        self.stack.enter_context(patch.object(c.runtime, "ROOT", Path(self.temp.name)))
        grant["caps"].update(total_calls=4500, total_jobs=100, total_gpu_seconds=430000, job_calls=1000, job_seconds=7200)
        notebook = self.root / "notebook.ipynb"
        write(notebook, {"notice": "SYNTHETIC_NOTEBOOK_NEVER_EXECUTED"})
        request["notebook"] = notebook.name
        request["notebook_sha256"] = sha(notebook)
        old = history(request, 0, 323, [], "a"*64)
        old["run_id"], old["attempt_id"], old["action"] = "synthetic180-1", "attempt-1", "initial"
        cohort = request["bindings"]["runtime"]["execution_request"]["cohort"]
        plan = c.campaign.plan(cohort, [old], action="resume", run_id="synthetic180-11", attempt_id="attempt-11", max_calls=200, max_seconds=7200)
        request.update(plan=plan, plan_sha256=digest(plan), handoff_id="synthetic180-11",
            job="nguynanhtn/safeshift-train3763-synthetic180-11", limits={"max_calls": 200, "job_seconds": 7200, "monitor_seconds": 900})
        request["bindings"]["runtime"]["execution_request"].update(history=[old], plan=plan)
        intent = {"kind": "INTENT", "request": request, "unix": time.time()-10, "campaign_sha256": digest(grant),
            "reserved_calls": 200, "reserved_gpu_seconds": 14400}
        original = self.root / "original.zip"
        original.write_bytes(b"SYNTHETIC_OLD_CUSTODY")
        write(str(original)+".sha256.json", {"sha256": sha(original)})
        old["evidence_sha256"] = sha(original)
        # Parent hashes reflect the exact immutable history bytes.
        plan = c.campaign.plan(cohort, [old], action="resume", run_id="synthetic180-11", attempt_id="attempt-11", max_calls=200, max_seconds=7200)
        plan["samples"] = []  # shrink planning-only projection at the planner seam
        request.update(plan=plan, plan_sha256=digest(plan))
        request["bindings"]["runtime"]["execution_request"].update(history=[old], plan=plan)
        request["bindings"]["dataset"]["execution_request_sha256"] = digest(request["bindings"]["runtime"]["execution_request"])
        self.ledger = SyntheticLedger(self.root, grant, intent, [old], [{"path": str(original), "sha256": sha(original), "plan": request["plan"]}])
        measured = {"safe_calls": 200, "overhead_seconds": 2192, "per_call_seconds": 25, "source_sha256": digest(plan["runtime_source"])}
        # Real migration reads the last existing MEASURED row; replace one tiny
        # historical synthetic transport row before route initialization.
        for root in (self.ledger.root, self.ledger.mirror):
            rows = self.ledger.events() if root == self.ledger.root else rows
            rows[33].update(kind="MEASURED", **measured)
        for root in (self.ledger.root, self.ledger.mirror):
            for n in (33, 34):
                if n == 34:
                    rows[n]["previous"] = digest(rows[n-1])
                (root / f"journal-{n+1:06d}.json").write_bytes(c.json_bytes(rows[n]))
        self.stack.enter_context(patch.object(c, "source_check", return_value=notebook))
        self.stack.enter_context(patch.object(c, "authenticate", side_effect=lambda *a: {"base_head_sha256": digest(self.ledger.events()[34])}))
        self.stack.enter_context(patch.object(c.campaign, "bind", side_effect=lambda g, r, **kw: r["bindings"]["runtime"]["execution_request"]))
        real_plan = c.campaign.plan
        def small_plan(*args, **kwargs):
            value = real_plan(*args, **kwargs)
            value["samples"] = []
            return value
        self.stack.enter_context(patch.object(c.campaign, "plan", side_effect=small_plan))
        self.stack.enter_context(patch.object(c, "verify_local", side_effect=self.local_verifier))
        self.stack.enter_context(patch.object(c, "archive_resources", return_value={"scope": "SYNTHETIC_NATIVE_VERIFIER_SEAM"}))
        self.stack.enter_context(patch.object(c, "original_handoff", return_value={"notice": "SYNTHETIC_PREPARED_HANDOFF"}))
        self.stack.enter_context(patch.object(c, "baseline_owner", return_value={"kernel_id": 11,
            "archive_sha256": hashlib.sha256(b"SYNTHETIC_OUTPUT_synthetic180-11").hexdigest()}))
        self.route = c.Continuation.initialize(self.root / "route", self.root / "route-mirror", self.ledger, {}, {})
        self.pre_change = {p.name: p.read_bytes() for p in self.ledger.root.glob("journal-*.json") if int(p.stem.split("-")[-1]) <= 35}

    def local_verifier(self, intent, grant, archive, evidence, **kwargs):
        c.require(sha(archive) == read(str(archive)+".sha256.json")["sha256"], "SYNTHETIC_SHA_FAIL")
        c.require(evidence["state"] == "COMPLETE", "SYNTHETIC_JOB_NOT_COMPLETE")
        p = intent["request"]["plan"]
        h = history(intent["request"], p["scheduled_ordinals"][0], p["scheduled_ordinals"][-1]+1,
            intent["request"]["bindings"]["runtime"]["execution_request"]["history"], sha(archive))
        return {"status": "OFFLINE_VERIFIED_PROVISIONAL", "verification": {"status": "PASS"}, "history": h,
            "sha256": sha(archive), "sidecar_sha256": sha(str(archive)+".sha256.json"), "owner_receipt": evidence,
            "formal_collection": "PENDING_CAMPAIGN_RECONCILIATION", "scientific_qualified": False}

    def accept(self):
        intent = self.route.state()["active"]
        archive = self.root / (intent["request"]["handoff_id"] + ".zip")
        archive.write_bytes(b"SYNTHETIC_OUTPUT_" + intent["request"]["handoff_id"].encode())
        write(str(archive)+".sha256.json", {"sha256": sha(archive)})
        evidence = {"state": "COMPLETE", "kernel_id": self.route.state()["budget"]["jobs"], "archive_sha256": sha(archive)}
        self.route.accept(archive, evidence)

    def assert_originals(self):
        for name, payload in self.pre_change.items():
            self.assertEqual((self.ledger.root / name).read_bytes(), payload)
            self.assertEqual((self.ledger.mirror / name).read_bytes(), payload)
        self.assertEqual(len(self.ledger.events()), 36)

    def test_transition35_does_not_invent_36_collected_or_37_measured(self):
        self.assertEqual(self.ledger.events()[35]["kind"], c.ADMISSION)
        self.assertEqual(self.route.state()["next_ordinal"], 323)
        self.assertIsNotNone(self.route.state()["active"])
        with self.assertRaisesRegex(ValueError, "ACTIVE_JOB"):
            self.route.stage()
        self.accept()
        self.assertEqual(self.route.state()["next_ordinal"], 523)
        self.assert_originals()

    def test_multiple_batches_restart_offline_no_release_each_attempt(self):
        for ordinal in (523, 723, 923):
            self.accept()
            self.assertEqual(self.route.state()["next_ordinal"], ordinal)
            self.route.stage()
            self.route = c.Continuation(self.route.root, self.ledger)
        self.assertEqual(self.route.state()["active"]["request"]["plan"]["scheduled_ordinals"][0], 923)
        self.assert_originals()

    def test_full_remainder_forecast_and_final_order(self):
        self.accept()
        forecast = self.route.forecast()
        self.assertEqual((forecast["remaining_images"], forecast["future_jobs"]), (3240, 17))
        self.assertEqual(forecast["calls_per_shard"], [200]*16 + [40])
        for _ in range(17):
            self.route.stage()
            self.accept()
        manifest = self.route.manifest()
        ordinals = [o for a in manifest["attempts"] for o in a["intent"]["request"]["plan"]["scheduled_ordinals"]]
        self.assertEqual(ordinals, list(range(323, 3763)))
        self.assertEqual(manifest["counts"], {"SUCCESS": 3763})
        self.assertEqual(manifest["budget"]["reserved_calls"], 3768)
        self.assertEqual(manifest["budget"]["reserved_gpu_seconds"], 316800)
        self.assertFalse(manifest["scientific_qualified"])
        with self.assertRaisesRegex(ValueError, "ALL_IMAGES_DONE"):
            self.route.stage()
        self.assert_originals()
        report = {"status": "ALL_ORIGINALS_VERIFIED", "manifest_sha256": digest(manifest), "tool_sha256": sha(online.__file__), "aborted": [],
            "budget": manifest["budget"], "billing_gpu_seconds": "NOT_OBSERVED",
            "historical": [{"archive_sha256": a["sha256"], "provider_reverified": True} for a in manifest["base_custody"]],
            "attempts": [{"intent_sha256": digest(a["intent"]), "archive_sha256": a["receipt"]["sha256"],
                "provider": {"job_id": a["intent"]["request"]["job"], "kernel_id": a["receipt"]["owner_receipt"]["kernel_id"],
                    "state": "COMPLETE", "version": 1}, "input_bytes_verified": True, "provider_copy_verified": True}
                for a in manifest["attempts"]]}
        for item, proof in zip(manifest["attempts"], report["attempts"]):
            self.add_proof(proof, item["intent"], c.safe(c.runtime.ROOT, item["archive"]))
        old_intent = self.ledger.events()[0]
        old_proof = report["historical"][0]
        old_proof.update(intent_sha256=digest(old_intent), provider={"job_id": "nguynanhtn/synthetic-historical", "state": "COMPLETE", "version": 1, "kernel_id": 10},
            input_bytes_verified=True, provider_copy_verified=True)
        self.add_proof(old_proof, old_intent, self.root/"original.zip")
        exports = {}
        def comment(number, marker, value, login):
            body = marker + "\n```json\n" + json.dumps(value) + "\n```"
            exports["/issues/comments/"+str(number)] = {"id": number, "body": body, "user": {"login": login, "id": 246929698},
                "issue_url": c.authority.API + "/issues/180"}
            return {"comment_id": number, "body_sha256": hashlib.sha256(body.encode()).hexdigest()}
        owner = comment(9900, c.FINAL, {"manifest_sha256": digest(manifest), "report": report,
            "status": "APPROVED_FOR_AGGREGATE_ADMISSION"}, c.authority.OWNER)
        admission = comment(9901, c.FINAL+"_ADMISSION", {"manifest_sha256": digest(manifest), "owner": owner,
            "report_sha256": digest(report), "status": "RELEASED_FOR_AGGREGATE_ADMISSION"}, "synthetic-reviewer")
        with self.assertRaisesRegex(ValueError, "MISSING_REAL_GITHUB"):
            self.route.reconcile({}, owner, admission)
        self.assert_originals()
        with patch.object(c.runtime, "sealed_history", return_value=self.route.registration["base_history"][0]):
            row = self.route.reconcile(exports, owner, admission)
        self.assertEqual(row["kind"], c.RECONCILED)
        self.assertEqual(row["manifest"], manifest)
        self.assertEqual(self.route.state()["formal_status"], "FINAL_EVENT_PRESENT_USE_OFFICIAL_REPORT")
        self.assertEqual(self.ledger.open_intent(), self.ledger.events()[34])
        with self.assertRaisesRegex(ValueError, "DUPLICATE_FINAL"):
            self.route.reconcile(exports, owner, admission)

    def add_proof(self, proof, intent, archive):
        request = intent["request"]
        proof["capsule"] = {"ref": request["bindings"]["runtime"]["execution_input"]["ref"], "version": 1,
            "sha256": digest({"request": request, "campaign_intent": intent}), "request_sha256": digest(request), "intent_sha256": digest(intent)}
        proof["output"] = {"sha256": sha(archive), "bytes": archive.stat().st_size,
            "sidecar_sha256": sha(str(archive)+".sha256.json"), "log_sha256": "f"*64}
        proof["resources"] = {"scope": "SYNTHETIC_NATIVE_VERIFIER_SEAM"}

    def test_manifest_before_completion_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "FULL_TRAIN"):
            self.route.manifest()

    def test_missing_zip_and_bad_sha_durably_stop(self):
        for missing in (True, False):
            # One route per failure: no retry after a failed local result.
            if not missing:
                break
            with self.assertRaises(FileNotFoundError):
                self.route.accept(self.root / "missing.zip", {"state": "COMPLETE"})
        with self.assertRaisesRegex(ValueError, "STOPPED"):
            self.route.stage()
        self.assert_originals()

    def test_bad_sha_stops_without_ordinal_advance(self):
        archive = self.root / "bad.zip"
        archive.write_bytes(b"SYNTHETIC")
        write(str(archive)+".sha256.json", {"sha256": "0"*64})
        with self.assertRaisesRegex(ValueError, "SHA_FAIL"):
            self.route.accept(archive, {"state": "COMPLETE"})
        self.assertEqual(self.route.events()[-1]["kind"], "STOPPED")
        failure = self.route.events()[-1]
        self.assertEqual(failure["reason"], "SYNTHETIC_SHA_FAIL")
        preserved = failure["forensic"][archive.name]["path"]
        self.assertEqual(sha(self.route.root/preserved), sha(archive))
        self.assertEqual(sha(self.route.mirror/preserved), sha(archive))
        self.assertTrue(archive.exists())

    def test_running_job_not_completion(self):
        archive = self.root / "running.zip"
        archive.write_bytes(b"SYNTHETIC")
        write(str(archive)+".sha256.json", {"sha256": sha(archive)})
        with self.assertRaisesRegex(ValueError, "NOT_COMPLETE"):
            self.route.accept(archive, {"state": "RUNNING"})
        self.assert_originals()

    def test_budget_exhaustion_before_creating_uploadable_artifact(self):
        self.accept()
        with patch.object(self.route, "forecast", return_value={"status": "BLOCKED_INSUFFICIENT_CAMPAIGN_CAPS"}):
            with self.assertRaisesRegex(ValueError, "CAPS"):
                self.route.stage()
        self.assertFalse((self.route.root / "handoffs").exists())

    def test_per_job_caps_source_and_expiry_fail_before_reservation(self):
        self.accept()
        before = self.route.events()
        for kwargs in ({"calls": 201}, {"seconds": 119}, {"seconds": 7201}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.route.stage(**kwargs)
        with patch.object(c, "source_check", side_effect=ValueError("SOURCE_CHANGED")), self.assertRaisesRegex(ValueError, "SOURCE_CHANGED"):
            self.route.stage()
        with patch.object(c.campaign, "validate", side_effect=ValueError("CAMPAIGN_WINDOW")), self.assertRaisesRegex(ValueError, "WINDOW"):
            self.route.stage()
        self.assertEqual(self.route.events(), before)

    def test_power_loss_after_reservation_export_same_intent_no_new_budget(self):
        self.accept()
        with patch.object(c.Continuation, "export_active", side_effect=OSError("POWER_LOSS")), self.assertRaises(OSError):
            self.route.stage()
        new = c.Continuation(self.route.root, self.ledger)
        before = new.state()["budget"]
        result = new.export_active()
        self.assertEqual(result["status"], "OFFLINE_PREPARED_NOT_UPLOADED_NOT_SUBMITTED")
        self.assertEqual(new.state()["budget"], before)
        self.assertEqual(new.export_active(), result)
        with self.assertRaisesRegex(ValueError, "ACTIVE_JOB"):
            new.stage()

    def test_duplicate_or_missing_ordinals_rejected_on_restart(self):
        self.accept()
        row = self.route.events()[0]
        row["ordinals"][-1] = row["ordinals"][-2]
        for root in (self.route.root, self.route.mirror):
            (root / "event-000001.json").write_bytes(c.json_bytes(row))
        with self.assertRaisesRegex(ValueError, "GAP_OR_DUPLICATE"):
            c.Continuation(self.route.root, self.ledger)

    def test_mirror_event_write_failure_is_fail_closed(self):
        self.accept()
        real_write = c.write
        def fail(path, value):
            if Path(path).parent == self.route.mirror and value.get("kind") == "RESERVED_OFFLINE":
                raise OSError("SYNTHETIC_FULL_DISK")
            return real_write(path, value)
        with patch.object(c, "write", side_effect=fail), self.assertRaises(OSError):
            self.route.stage()
        with self.assertRaisesRegex(ValueError, "PARTIAL_WRITE"):
            c.Continuation(self.route.root, self.ledger)
        self.assert_originals()

    def test_saved_archive_loss_or_sidecar_change_stops_schedule(self):
        self.accept()
        row = self.route.events()[0]
        (self.route.mirror / row["archive"]).unlink()
        with self.assertRaises(FileNotFoundError):
            self.route.stage()
        self.assert_originals()

    def test_original_ledger_mirror_loss_prevents_any_work(self):
        self.accept()
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_CONTINUATION_MIRROR"):
            c.Continuation.initialize(self.root/"new-route", self.root/"new-route/nested-mirror", self.ledger, {}, {})
        self.assert_originals()
        (self.ledger.mirror / "journal-000035.json").unlink()
        with self.assertRaisesRegex(ValueError, "MIRROR_LOSS"):
            self.route.stage()

    def test_original_intent_remains_open_and_no_fake_submit_measure(self):
        self.accept()
        self.route.stage()
        self.assertEqual(self.ledger.open_intent(), self.ledger.events()[34])
        self.assertEqual([e["kind"] for e in self.route.events()], ["OFFLINE_VERIFIED_PROVISIONAL", "RESERVED_OFFLINE"])
        self.assert_originals()

    def test_complete_artifact_copies_survive_crash_before_receipt(self):
        real_append = self.route.append
        def crash(kind, **values):
            if kind == "OFFLINE_VERIFIED_PROVISIONAL":
                raise KeyboardInterrupt("SYNTHETIC_POWER_LOSS")
            return real_append(kind, **values)
        with patch.object(self.route, "append", side_effect=crash), self.assertRaises(KeyboardInterrupt):
            self.accept()
        self.assertEqual(self.route.events(), [])
        intent = self.route.state()["active"]
        archive = self.root/(intent["request"]["handoff_id"]+".zip")
        self.route.accept(archive, {"state": "COMPLETE", "kernel_id": 11, "archive_sha256": sha(archive)})
        self.assertEqual(self.route.state()["next_ordinal"], 523)
        self.assert_originals()

    def test_github_disconnect_during_owner_export_keeps_production_unchanged(self):
        with patch.object(online, "load_companion", return_value=c), patch.object(c.authority, "get", side_effect=ConnectionError("https://provider.invalid/SYNTHETIC_SECRET_TOKEN")):
            with self.assertRaisesRegex(ValueError, "OWNER_AUTHORITY_EXPORT_BLOCKED:ConnectionError") as error:
                online.acquire_authority(self.ledger, {"comment_id": 9999, "body_sha256": "f"*64},
                    self.root/"owner-export-failed", owner_performs_network=True)
        self.assertNotIn("SYNTHETIC_SECRET", str(error.exception))
        self.assertTrue(error.exception.__suppress_context__)
        self.assertEqual(read(self.root/"owner-export-failed/BLOCKED.json")["status"], "BLOCKED")
        self.assert_originals()

    def test_final_ledger_mirror_error_never_reports_success(self):
        # Isolate final append transport: full end-to-end completion/admission
        # is exercised in test_full_remainder_forecast_and_final_order.
        manifest = {"attempts": [], "base_custody": [], "historical_attempts": [], "counts": {"SUCCESS": 3763}, "budget": {}}
        report = {"manifest_sha256": digest(manifest), "status": "ALL_ORIGINALS_VERIFIED", "tool_sha256": sha(online.__file__),
            "attempts": [], "historical": [], "aborted": [], "budget": {}, "billing_gpu_seconds": "NOT_OBSERVED"}
        owner = {"comment_id": 8000, "body_sha256": "a"*64}
        admission = {"comment_id": 8001, "body_sha256": "b"*64}
        def record(locator, marker, reader):
            if marker == c.FINAL:
                return {"manifest_sha256": digest(manifest), "report": report, "status": "APPROVED_FOR_AGGREGATE_ADMISSION"}, {
                    "id": 8000, "user": {"login": c.authority.OWNER, "id": 246929698}, "issue_url": c.authority.API+"/issues/180"}
            return {"manifest_sha256": digest(manifest), "owner": owner, "report_sha256": digest(report),
                "status": "RELEASED_FOR_AGGREGATE_ADMISSION"}, {"id": 8001, "user": {"login": "synthetic-reviewer"}}
        real_write = c.write
        def fail(path, value):
            if Path(path).parent == self.ledger.mirror and value.get("kind") == c.RECONCILED:
                raise OSError("SYNTHETIC_FINAL_MIRROR_FULL")
            return real_write(path, value)
        with patch.object(self.route, "manifest", return_value=manifest), patch.object(c.campaign, "record", side_effect=record), patch.object(c, "write", side_effect=fail):
            with self.assertRaises(OSError):
                self.route.reconcile({}, owner, admission)
        with self.assertRaisesRegex(ValueError, "MIRROR_LOSS"):
            self.ledger.events()

    def test_insufficient_local_disk_blocks_next_batch(self):
        with patch.object(c.shutil, "disk_usage", return_value=NS(free=0)), self.assertRaisesRegex(ValueError, "SPACE_INSUFFICIENT"):
            self.accept()
        self.assertEqual(self.route.events()[-1]["kind"], "STOPPED")
        self.assert_originals()


class LocalVerificationTests(ManualFixture):
    def receipt(self):
        return {"job": self.request["job"], "version": 1, "kernel_id": 123, "state": "COMPLETE",
            "archive_sha256": self.checksum, "no_other_job_or_version": True, "no_api_submission": True,
            "owner_downloaded_unix": int(time.time())}

    def setUp(self):
        super().setUp()
        # The inherited fixture replaces the full native inference verifier,
        # while checking actual synthetic ZIP checksums and native claim files.
        self.stack.enter_context(patch.object(c.manual, "verify_inputs_in_archive"))

    def test_quick_gate_retains_completion_as_provisional(self):
        result = c.verify_local(self.intent, self.grant, self.archive, self.receipt())
        self.assertEqual(result["status"], "OFFLINE_VERIFIED_PROVISIONAL")
        self.assertEqual(result["history"], self.history)
        self.assertFalse(result["scientific_qualified"])

    def test_incomplete_owner_proof_and_kernel_version_block(self):
        for key, value in (("state", "RUNNING"), ("version", 2), ("kernel_id", True),
                ("no_other_job_or_version", False), ("archive_sha256", "0"*64), ("owner_downloaded_unix", 1)):
            receipt = self.receipt(); receipt[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                c.verify_local(self.intent, self.grant, self.archive, receipt)

    def test_raw_native_claim_mismatch_is_not_ignored(self):
        bad = deepcopy(self.intent); bad["reserved_calls"] = 2
        with self.assertRaisesRegex(ValueError, "CUSTODY"):
            c.verify_local(bad, self.grant, self.archive, self.receipt())

    def test_missing_or_corrupt_zip_blocks(self):
        with self.assertRaises(FileNotFoundError):
            c.verify_local(self.intent, self.grant, self.root / "absent.zip", self.receipt())
        with self.archive.open("ab") as stream:
            stream.write(b"CORRUPT")
        with self.assertRaises(ValueError):
            c.verify_local(self.intent, self.grant, self.archive, self.receipt())

    def test_technical_error_or_partial_ordinal_blocks(self):
        for field, value in (("status", "TECHNICAL_ERROR"), ("native_calls", 0)):
            ancestor = deepcopy(self.history); ancestor["records"][0][field] = value
            with patch.object(c.runtime, "sealed_history", return_value=ancestor), self.assertRaisesRegex(ValueError, "SCHEDULED"):
                c.verify_local(self.intent, self.grant, self.archive, self.receipt())

    def test_each_final_capsule_and_provider_copy_is_bound(self):
        proof = {"intent_sha256": digest(self.intent), "archive_sha256": self.checksum, "provider": {
                "job_id": self.request["job"], "kernel_id": 123, "state": "COMPLETE", "version": 1},
            "input_bytes_verified": True, "provider_copy_verified": True}
        ContinuationTests.add_proof(self, proof, self.intent, self.archive)
        c.provider_proof(proof, self.intent, self.archive, job=self.request["job"], kernel_id=123)
        for field, key, value in (("capsule", "sha256", "0"*64), ("capsule", "ref", "nguynanhtn/wrong/1"),
                ("provider", "version", 2), ("provider", "kernel_id", 124), ("output", "sidecar_sha256", "0"*64)):
            bad = deepcopy(proof); bad[field][key] = value
            with self.subTest(field=field, key=key), self.assertRaises(ValueError):
                c.provider_proof(bad, self.intent, self.archive, job=self.request["job"], kernel_id=123)

    def test_owner_online_aggregator_with_mocked_service_boundaries(self):
        # This tests orchestration only. Native authenticity, GitHub and SDK
        # calls are explicit boundaries, not real provider evidence.
        notebook_bytes = c.json_bytes(self.notebook)
        self.request["notebook_sha256"] = hashlib.sha256(notebook_bytes).hexdigest()
        receipt = {"owner_receipt": self.receipt(), "sha256": self.checksum}
        manifest = {"attempts": [{"intent": self.intent, "receipt": receipt, "archive": self.archive.name}],
            "base_custody": [], "historical_attempts": [], "budget": {"reserved_gpu_seconds": 3600}}
        route = NS(manifest=lambda: deepcopy(manifest), registration={"initial_intent": self.intent,
            "github_exports": {}, "release_locator": {}, "base_count": 1}, ledger=self.ledger)
        self.client.kernels_list_with_response.return_value = NS(kernels=[NS(ref=self.request["job"])], next_page_token=None)
        provider = {"job_id": self.request["job"], "kernel_id": 123, "state": "COMPLETE", "version": 1}
        with patch.object(online, "load_companion", return_value=c), patch.object(c.runtime, "ROOT", self.root), \
                patch.object(c, "_private", side_effect=Path), patch.object(c, "source_check"), patch.object(c, "authenticate"), \
                patch.object(c.campaign, "load", return_value=self.grant), patch.object(c.campaign, "bind"), \
                patch.object(c, "verify_local", return_value=receipt), patch.object(c.subprocess, "check_output", return_value=notebook_bytes), \
                patch.object(c.manual, "observe_kernel", return_value=provider), patch.object(c.manual, "download_outputs", side_effect=self.copy_output):
            report = online.verify(route, self.root/"owner-final", owner_performs_network=True)
        self.assertEqual(report["status"], "ALL_ORIGINALS_VERIFIED")
        self.assertEqual(len(report["attempts"]), 1)
        self.assertEqual(report["attempts"][0]["provider"], provider)
        self.assertEqual(report["billing_gpu_seconds"], "NOT_OBSERVED")
        self.assertTrue((self.root/"owner-final/report.json").is_file())
        self.client.kernels_push.assert_not_called()
        route.registration["github_exports"] = {"/issues/comments/9999": {}}
        with patch.object(online, "load_companion", return_value=c), patch.object(c, "_private", side_effect=Path), \
                patch.object(c, "source_check"), patch.object(c.authority, "get", side_effect=ConnectionError("https://provider.invalid/SYNTHETIC_SIGNED_SECRET")):
            with self.assertRaisesRegex(ValueError, "OWNER_FINAL_VERIFICATION_BLOCKED:ConnectionError") as failure:
                online.verify(route, self.root/"owner-final-disconnected", owner_performs_network=True)
        self.assertNotIn("SYNTHETIC_SIGNED", str(failure.exception))
        self.assertTrue(failure.exception.__suppress_context__)
        self.assertFalse(read(self.root/"owner-final-disconnected/BLOCKED.json")["production_appended"])
        self.assertEqual(len(self.ledger.events()), 1)


class QuickCustodyTests(ManualFixture):
    """Real small ZIP/manifest/CRC/raw-custody code; synthetic metadata only."""
    def setUp(self):
        super().setUp()
        self.folder = self.root / "quick-fixture"
        shutil.copytree(self.root / "bundle", self.folder)
        self.plan = self.request["plan"]
        self.cohort = self.request["bindings"]["runtime"]["execution_request"]["cohort"]
        row = self.cohort["samples"][0]
        binding = c.runtime.trace_binding(self.plan["runtime_source"], self.plan, row, "1"*64, digest(self.plan))
        binary = struct.pack("<ff", 0., 1.)
        step = "run/samples/000000/steps/000"
        self.put(step+".f32", binary)
        self.put(step+".masked.json", {"notice": "SYNTHETIC_MASK_NUMERICAL_REPLAY_DEFERRED"})
        self.put(step+".forward.json", {"step": 0, "vocab": 2, "raw_sha256": hashlib.sha256(binary).hexdigest(),
            "origin": "forward_before_processors", "encoding": "float32-little-endian", "all_finite": True})
        from safeshift.internvl_grammar import PROCESSOR
        raw = {"binding": binding, "response": '{"safety_level":"Level02"}', "hnlo": None, "hnlo_status": c.runtime.HNLO_STATUS,
            "evidence_kind": "NATIVE", "capture_origin": "forward_before_processors", "generated_ids": [1], "logit_width": 2,
            "raw_vector_hashes": [sha(self.folder/(step+".f32"))], "masked_vector_hashes": [sha(self.folder/(step+".masked.json"))],
            "actual_logits_processors": [PROCESSOR], "policy": c.runtime.POLICY}
        self.put("run/samples/000000/raw.json", raw)
        self.put("run/samples/000000/started.json", {"row": row, "plan_sha256": digest(self.plan)})
        self.put("run/samples/000000/native_call.json", {"binding": binding})
        self.put("run/samples/000000/trace-verification.json", {"status": "TRACE_CONSISTENT", "evidence_kind": "NATIVE",
            "label": "Level02", "binding": binding})
        records = [{**sample, "status": "NOT_ATTEMPTED", "label": None, "native_calls": 0, "attempts": 0,
            "hnlo": None, "hnlo_status": c.runtime.HNLO_STATUS} for sample in self.cohort["samples"]]
        records[0].update(status="SUCCESS", label="Level02", native_calls=1, attempts=1, trace_verified=True,
            raw_sha256=sha(self.folder/"run/samples/000000/raw.json"))
        self.put("run/summary.json", {"schema": c.runtime.IDENTITY+"-result", "records": records, "scope": "PRIVATE_TRAIN_METADATA",
            "planned": 3763, "series_id": self.plan["series_id"], "run_id": self.plan["run_id"], "attempt_id": self.plan["attempt_id"],
            "plan_sha256": digest(self.plan), "source_sha256": digest(self.plan["runtime_source"]), "status": "PASS", "failure": None,
            "hnlo": None, "hnlo_status": c.runtime.HNLO_STATUS, "model_calls": 1, "counts": {"SUCCESS": 1, "NOT_ATTEMPTED": 3762}})
        for name, value in (("run/plan.json", self.plan), ("run/source.json", self.plan["runtime_source"]),
                ("run/cohort.json", self.cohort), ("run/configuration.json", c.runtime.configuration()),
                ("terminal.json", {"status": "PASS", "error": None})):
            self.put(name, value)
        for name in ("setup/setup-supervisor.json", "worker-supervisor.json"):
            self.put(name, {"status": "EXITED", "returncode": 0, "automatic_retry": False})
        self.number = 0

    def put(self, name, value):
        path = self.folder/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if type(value) is bytes else c.json_bytes(value))

    def check(self):
        (self.folder/"checksums.json").unlink(missing_ok=True)  # regenerate ONLY this synthetic fixture
        self.number += 1
        archive = self.root/f"quick-{self.number}.zip"
        checksum = export(self.folder, archive)
        return c.quick_bundle(archive, checksum, self.plan)

    def test_real_quick_validator_defers_numeric_replay(self):
        with patch.object(c.runtime, "verify_numeric_members", side_effect=AssertionError("QUICK_MUST_DEFER_NUMERIC")):
            result = self.check()
        self.assertEqual(result["model_calls"], 1)
        self.assertFalse(result["scientific_qualified"])

    def test_missing_raw_vector_despite_self_consistent_manifest_blocks(self):
        (self.folder/"run/samples/000000/steps/000.f32").unlink()
        with self.assertRaisesRegex(ValueError, "RAW_VECTOR"):
            self.check()

    def test_wrong_source_or_scientific_config_blocks(self):
        self.put("run/source.json", {"changed": True})
        with self.assertRaisesRegex(ValueError, "SOURCE_SCIENCE"):
            self.check()

    def test_extra_sample_or_duplicate_ordinal_blocks(self):
        self.put("run/samples/000001/raw.json", {"notice": "UNSCHEDULED_SYNTHETIC"})
        with self.assertRaisesRegex(ValueError, "UNPLANNED_SAMPLE"):
            self.check()

    def test_partial_worker_or_unplanned_native_call_blocks(self):
        self.put("worker-supervisor.json", {"status": "KILLED", "returncode": -9, "automatic_retry": False})
        with self.assertRaisesRegex(ValueError, "SUPERVISED_EXIT"):
            self.check()

    def test_invalid_completion_is_retained_without_parser_rescue(self):
        raw = read(self.folder/"run/samples/000000/raw.json")
        raw["response"] = "SYNTHETIC_INVALID_RESPONSE"
        self.put("run/samples/000000/raw.json", raw)
        summary = read(self.folder/"run/summary.json")
        summary["records"][0].update(status="INVALID", label=None, trace_verified=False,
            raw_sha256=sha(self.folder/"run/samples/000000/raw.json"))
        summary["counts"] = {"INVALID": 1, "NOT_ATTEMPTED": 3762}
        self.put("run/summary.json", summary)
        self.put("run/samples/000000/trace-failure.json", {"notice": "SYNTHETIC_INVALID_ALL_RAW_RETAINED"})
        self.assertEqual(self.check()["counts"]["INVALID"], 1)


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch("socket.socket", side_effect=AssertionError("NO_NETWORK")))
        self.request, self.grant, self.exports = fixture(Path(self.temp.name)/"ledger")
        config = c.runtime.configuration()
        self.request["bindings"]["checkpoint"] = {"model": config["model"], "revision": config["revision"],
            "sha256": c.campaign.identity()["checkpoint_sha256"]}
        body = (Path(c.__file__).parents[1] / "docs/research/evidence/train3763_deferred_20261112/owner-decision.md").read_text(encoding="utf-8").rstrip("\n")
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(), c.DECISION_BODY_SHA256)
        self.exports["/issues/comments/"+str(c.DECISION_ID)] = {"id": c.DECISION_ID, "user": {"login": c.authority.OWNER, "id": 246929698},
            "author_association": "OWNER", "issue_url": c.authority.API + "/issues/180", "body": body}
        self.value = {"campaign_sha256": digest(self.grant), "decision_body_sha256": c.DECISION_BODY_SHA256,
            "implementation_pr": 195, "reviewed_head": "c"*40, "merged_sha": "d"*40,
            "script_sha256": sha(c.__file__), "tools_sha256": digest(c.tool_manifest()),
            "source_sha256": digest(self.request["plan"]["runtime_source"]), "notebook_sha256": self.request["notebook_sha256"],
            "scope": "OFFLINE_SERIAL_DEFERRED_RECONCILIATION", "base_head_sha256": "e"*64, "start_ordinal": 323}
        self.value["audit"] = self.comment(9000, c.RELEASE+"_AUDIT", {"reviewed_head": "c"*40, "script_sha256": sha(c.__file__),
            "tools_sha256": digest(c.tool_manifest()), "status": "PASS", "independent": True}, "synthetic-auditor")
        self.locator = self.comment(9001, c.RELEASE, self.value, "synthetic-reviewer")
        self.exports["/pulls/195"] = {"merged": True, "base": {"ref": "main"}, "head": {"sha": "c"*40}, "merge_commit_sha": "d"*40}

    def comment(self, number, marker, value, login):
        body = marker + "\n```json\n" + json.dumps(value) + "\n```"
        self.exports["/issues/comments/"+str(number)] = {"id": number, "body": body, "user": {"login": login}, "issue_url": c.authority.API + "/issues/195"}
        return {"comment_id": number, "body_sha256": hashlib.sha256(body.encode()).hexdigest()}

    def test_one_exact_release_and_real_owner_export(self):
        self.assertEqual(c.authenticate(self.grant, self.request, self.exports, self.locator), self.value)

    def test_missing_github_offline_never_network_fallback(self):
        with self.assertRaisesRegex(ValueError, "MISSING_REAL_GITHUB"):
            c.authenticate(self.grant, self.request, {}, self.locator)

    def test_edited_decision_or_unmerged_tool_or_audit_failure(self):
        for path, mutate in (("/issues/comments/"+str(c.DECISION_ID), lambda x: x.update(body=x["body"]+"edited")),
                ("/pulls/195", lambda x: x.update(merged=False)),
                ("/issues/comments/9000", lambda x: x.update(user={"login": "wrong"}))):
            exports = deepcopy(self.exports); mutate(exports[path])
            with self.subTest(path=path), self.assertRaises(ValueError):
                c.authenticate(self.grant, self.request, exports, self.locator)

    def test_source_or_checkpoint_change_is_blocked(self):
        bad = deepcopy(self.request); bad["bindings"]["checkpoint"]["sha256"] = "0"*64
        with self.assertRaises(ValueError):
            c.authenticate(self.grant, bad, self.exports, self.locator)

    def test_external_tool_requires_owner_network_flag(self):
        with self.assertRaisesRegex(ValueError, "OWNER_MUST_PERSONALLY"):
            online.verify(None, Path(self.temp.name)/"online", owner_performs_network=False)

    def test_original_attempt11_factual_record_is_required(self):
        intent = {"request": deepcopy(self.request), "unix": time.time(), "reserved_calls": 200}
        intent["request"]["plan"]["scheduled_ordinals"] = list(range(323, 523))
        request = intent["request"]
        request["plan_sha256"] = digest(request["plan"])
        request["bindings"]["runtime"]["execution_request"]["plan"] = request["plan"]
        request["bindings"]["dataset"]["execution_request_sha256"] = digest(request["bindings"]["runtime"]["execution_request"])
        value = {"campaign_sha256": digest(self.grant), "intent_sha256": digest(intent), "request_sha256": digest(request),
            "ledger_events": 35, "ledger_head_sha256": digest(intent), "plan_sha256": digest(request["plan"]),
            "scheduled_ordinals": list(range(323, 523)), "input_sources": c.operator.input_sources(request),
            "job": request["job"], "version": 1, "mode": c.manual.SAME_SLUG, "operator": c.manual.PROVENANCE,
            "no_api_submission": True, "no_other_job_or_version": True, "archive_sha256": "f"*64, "kernel_id": 123}
        locator = self.comment(9002, c.manual.SAME_OWNER_MARKER, value, c.authority.OWNER)
        self.exports["/issues/comments/9002"].update(issue_url=c.authority.API+"/issues/180", user={"login": c.authority.OWNER, "id": 246929698})
        with patch.object(c, "BASELINE_OWNER", locator):
            self.assertEqual(c.baseline_owner(self.grant, intent, self.exports), value)
            with self.assertRaisesRegex(ValueError, "MISSING_REAL_GITHUB"):
                c.baseline_owner(self.grant, intent, {})
            bad = deepcopy(intent); bad["reserved_calls"] = 199
            with self.assertRaisesRegex(ValueError, "OWNER_FACTS"):
                c.baseline_owner(self.grant, bad, self.exports)

    def test_merge_exports_is_offline_create_only_input_preserving(self):
        original = {"/issues/comments/1": {"id": 1, "body": "SYNTHETIC"}}
        result = c.merge_exports(original, [{"id": 2, "body": "SYNTHETIC_SECOND"}])
        self.assertEqual(len(result), 2)
        self.assertEqual(len(original), 1)
        with self.assertRaisesRegex(ValueError, "CONFLICT"):
            c.merge_exports(original, [{"id": 1, "body": "CHANGED"}])

    def test_private_custody_and_partial_copy_guards(self):
        with self.assertRaisesRegex(ValueError, "PRIVATE_PROCESSED"):
            c._private(c.runtime.ROOT/"docs/forbidden-evidence")
        source, target = Path(self.temp.name)/"source", Path(self.temp.name)/"target"
        source.write_bytes(b"COMPLETE_SYNTHETIC_BYTES")
        target.write_bytes(b"PARTIAL")
        with self.assertRaisesRegex(ValueError, "CONFLICT"):
            c._copy(source, target)
        self.assertEqual(target.read_bytes(), b"PARTIAL")


if __name__ == "__main__":
    unittest.main()
