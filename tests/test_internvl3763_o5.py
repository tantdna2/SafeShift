"""CPU synthetic copies only: never open/mutate the private campaign or provider."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import zipfile

from safeshift import internvl3763 as runtime
from safeshift import internvl3763_campaign as c
from safeshift import internvl3763_o5 as o5
from safeshift import internvl3763_release as old
from safeshift import internvl3763_operator as op
from safeshift.kaggle_handoff import lock
from safeshift.pilot.artifacts import read, write, sha, export
from safeshift.pilot.contract import digest
from test_internvl3763_campaign import fixture

PUBLIC_BODY = runtime.ROOT / "docs/research/evidence/train3763_o5_extension_20261109/owner-decision.md"


class O5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixed_source = runtime.source_spec()
        cls.fixed_science = c.science()
        cls.fixed_identity = c.identity()

    def setUp(self):
        for obj, name, value in ((runtime, "source_spec", self.fixed_source),
                (c, "science", self.fixed_science), (c, "identity", self.fixed_identity)):
            p = patch.object(obj, name, return_value=deepcopy(value))
            p.start(); self.addCleanup(p.stop)
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.request, self.grant, self.comments = fixture(self.root / "ledger")
        self.grant["caps"].update(total_gpu_seconds=80000, job_seconds=7200,
            total_calls=4500, total_jobs=100, job_calls=1000)
        body = PUBLIC_BODY.read_text(encoding="utf8")
        value = json.JSONDecoder().raw_decode(body[body.index("{"):])[0]
        value.update(original_campaign_sha256=digest(self.grant), campaign_id=self.grant["campaign_id"])
        self.value = value
        self.original_locator = self.comment(o5.ORIGINAL_COMMENT_ID, c.MARKER, self.grant, old.OWNER, 181)
        self.locator = self.comment(o5.COMMENT_ID, o5.MARKER, value, old.OWNER, 180)
        # Explicit test-only identity seams. No CLI/operator override exists.
        for name, val in (("ORIGINAL_SHA256", digest(self.grant)), ("BODY_SHA256", self.locator["body_sha256"]),
                ("DECISION_SHA256", digest(value)), ("LOCATOR", self.locator)):
            p = patch.object(o5, name, val); p.start(); self.addCleanup(p.stop)
        p = patch.object(old, "get", side_effect=lambda path: deepcopy(self.comments[path]))
        p.start(); self.addCleanup(p.stop)
        self.ledger = c.Ledger.create(self.root / "ledger", self.root / "mirror", self.grant, self.grant["operator_id"])
        self.history = []
        # Retain real ZIP/hash/CRC/history code, synthetic summary has no model vectors.
        def verify(archive, expected, plan):
            c.require(sha(archive) == expected, "SYNTHETIC_ARCHIVE_HASH")
            with zipfile.ZipFile(archive) as z:
                c.require(z.testzip() is None, "SYNTHETIC_ARCHIVE_CRC")
                status = json.loads(z.read("run/summary.json"))["status"]
            return {"status": status, "scope": "SYNTHETIC_ONLY"}
        p = patch.object(runtime, "verify_bundle", side_effect=verify)
        p.start(); self.addCleanup(p.stop)
        for n in range(1, 8):
            request = self.next_request(n)
            with lock(self.ledger.root):
                intent = self.ledger.append("INTENT", request=request, reserved_calls=1, reserved_gpu_seconds=3600)
                if n in (1, 2, 5):
                    self.ledger.append("ABORTED_PRE_SUBMIT", intent_sha256=digest(intent), refund=False)
                    continue
                self.ledger.append("PUSH_INTENT", intent_sha256=digest(intent))
                self.ledger.append("SUBMITTED", intent_sha256=digest(intent), result={"job_id": request["job"], "version": 1})
                records = []
                if n in (4, 7):
                    ordinal = 0 if n == 4 else 1
                    records = [{**request["bindings"]["runtime"]["execution_request"]["cohort"]["samples"][ordinal],
                        "status": "SUCCESS", "label": "Level02", "attempts": 1, "native_calls": 1,
                        "hnlo": None, "hnlo_status": runtime.HNLO_STATUS, "raw_sha256": "a" * 64}]
                folder = self.root / f"export-{n}"
                write(folder / "run/summary.json", {"status": "PASS" if records else "FAIL", "records": records})
                archive = self.root / f"export-{n}.zip"; checksum = export(folder, archive)
                history = runtime.sealed_history(archive, checksum, request["plan"])
                self.history.append(history)
                self.ledger.append("COLLECTED", intent_sha256=digest(intent), archive=str(archive), sha256=checksum,
                    plan=request["plan"], history=history, provider={"state": "COMPLETE"}, verification={"status": "PASS" if records else "FAIL"})
                if n in (4, 7):
                    # Legacy source measurement cannot certify this changed runtime.
                    self.ledger.append("MEASURED", source_sha256="0" * 64, safe_calls=205,
                        overhead_seconds=640, per_call_seconds=32, minimum_seconds=7200)
        self.assertEqual(len(self.ledger.events()), 24)
        self.before = self.snapshot()

    def comment(self, number, marker, value, login, issue):
        body = marker + "\n```json\n" + json.dumps(value) + "\n```"
        self.comments[f"/issues/comments/{number}"] = {"id": number, "body": body,
            "user": {"login": login, "id": 246929698}, "author_association": "OWNER",
            "issue_url": old.API + f"/issues/{issue}"}
        return {"comment_id": number, "body_sha256": hashlib.sha256(body.encode()).hexdigest()}

    def snapshot(self):
        return {str(p.relative_to(self.root)): sha(p) for p in self.root.rglob("*") if p.is_file() and p.name != ".lock"}

    def preserved(self):
        after = self.snapshot()
        self.assertEqual({p: after[p] for p in self.before}, self.before)

    def next_request(self, n=8, calls=1, seconds=1800):
        req = deepcopy(self.request)
        rt = req["bindings"]["runtime"]
        prev = rt["execution_input"]["ref"]
        rt["execution_input"]["ref"] = f"nguynanhtn/synthetic-o5-capsule-{n}/1"
        sources = req["bindings"]["dataset"]["dataset_sources"]
        sources[sources.index(prev)] = rt["execution_input"]["ref"]
        execution = rt["execution_request"]
        plan = c.plan(execution["cohort"], self.history, action="resume" if self.history else "initial",
            run_id=f"synthetic180-{n}", attempt_id=f"attempt-{n}", max_calls=calls, max_seconds=seconds)
        execution.update(plan=plan, history=deepcopy(self.history), history_archives=[
            {"archive": f"custody/{h['evidence_sha256']}.zip", "sha256": h["evidence_sha256"],
             "plan": {"run_id": h["run_id"], "attempt_id": h["attempt_id"]}} for h in self.history])
        req.update(plan=plan, plan_sha256=digest(plan), handoff_id=f"synthetic180-{n}",
            job=f"nguynanhtn/safeshift-train3763-synthetic180-{n}", execution_release=self.original_locator,
            limits={"monitor_seconds": 900, "job_seconds": seconds, "max_calls": calls})
        req["bindings"]["dataset"]["execution_request_sha256"] = digest(execution)
        return req

    def extend(self):
        return self.ledger.extend_o5(self.original_locator)

    def released_request(self, calls=1, seconds=1800):
        event = self.ledger.budget()["extension"]
        req = self.next_request(calls=calls, seconds=seconds)
        # Real TECHNICAL_V1 + AUDIT_V1 validation, not a mocked bind.
        reviewed = self.comments["/issues/comments/2002"]
        tech = json.JSONDecoder().raw_decode(reviewed["body"][reviewed["body"].index("{"):])[0]
        tech.update(campaign_sha256=digest(self.grant), source_sha256=digest(runtime.source_spec()))
        aud = {"campaign_sha256": digest(self.grant), "reviewed_head": tech["reviewed_head"],
            "source_sha256": tech["source_sha256"], "regression_sha256": tech["regression_sha256"], "status": "PASS", "independent": True}
        tech["audit"] = self.comment(2001, "SAFESHIFT_TRAIN3763_AUDIT_V1", aud, "synthetic-auditor", 181)
        rt = req["bindings"]["runtime"]
        rt["technical_revision"] = self.comment(2002, "SAFESHIFT_TRAIN3763_TECHNICAL_V1", tech, "synthetic-reviewer", 181)
        release = {"campaign_sha256": digest(self.grant), "extension_sha256": digest(event),
            "science_sha256": self.grant["science_sha256"], "implementation_pr": tech["implementation_pr"],
            "reviewed_head": tech["reviewed_head"], "merged_sha": tech["merged_sha"],
            "source_sha256": tech["source_sha256"], "notebook_sha256": tech["notebook_sha256"],
            "status": "RELEASED_FOR_SERIAL_RESUME", "start_ordinal": 2, "test": False}
        rt.update(o5_extension=event, o5_execution_release=self.comment(3000,
            "SAFESHIFT_TRAIN3763_O5_EXECUTION_V1", release, "synthetic-reviewer", 181))
        return req

    def test_append_only_original_hash_cumulative_budget_and_offline_reopen(self):
        self.assertEqual(self.ledger.summary()["remaining_gpu_seconds"], 54800)
        event = self.extend()
        reopened = c.Ledger(self.ledger.root)
        state = reopened.summary()
        self.assertEqual(state["effective_caps"], {**self.grant["caps"], "total_gpu_seconds": 430000})
        self.assertEqual(state["campaign_sha256"], digest(self.grant))
        self.assertEqual((state["reserved_gpu_seconds"], state["remaining_gpu_seconds"], state["jobs"], state["reserved_calls"]),
            (25200, 404800, 7, 7))
        self.assertEqual(state["counts"], {"SUCCESS": 2, "NOT_ATTEMPTED": 3761})
        self.assertEqual(state["o5_extension_sha256"], digest(event))
        self.preserved()
        with self.assertRaisesRegex(ValueError, "REPLAY"):
            reopened.extend_o5(self.original_locator)

    def test_untrusted_edited_wrong_id_issue_owner_and_network_failure_never_append(self):
        original = deepcopy(self.comments[f"/issues/comments/{o5.COMMENT_ID}"])
        for field, val in (("id", 1), ("body", original["body"] + "edited"),
                ("user", {"login": "impostor", "id": 246929698}),
                ("user", {"login": old.OWNER, "id": 1}), ("author_association", "CONTRIBUTOR"),
                ("issue_url", old.API + "/issues/181")):
            with self.subTest(field=field):
                self.comments[f"/issues/comments/{o5.COMMENT_ID}"] = {**original, field: val}
                with self.assertRaises(ValueError): self.extend()
                self.assertEqual(len(self.ledger.events()), 24)
        self.comments[f"/issues/comments/{o5.COMMENT_ID}"] = original
        with patch.object(old, "get", side_effect=OSError("offline")), self.assertRaises(OSError): self.extend()
        self.preserved()

    def test_different_grant_caps_science_and_registration_cannot_use_decision(self):
        for field in ("caps", "science_sha256", "operator_id"):
            bad = deepcopy(self.grant)
            if field == "caps": bad[field]["job_seconds"] = 7201
            else: bad[field] = "changed"
            with self.subTest(field=field), self.assertRaises(ValueError): o5.authority(bad)
        event = self.extend()
        with self.assertRaisesRegex(ValueError, "REGISTRATION"):
            o5.validate_extension(event, self.grant, self.ledger.events()[:24], "f" * 64)

    def test_mirror_torn_write_blocks_then_exact_missing_copy_restore_is_readonly(self):
        real_write = c.write
        def fail(path, value):
            if Path(path) == self.ledger.mirror / "journal-000025.json": raise OSError("injected mirror loss")
            return real_write(path, value)
        with patch.object(c, "write", side_effect=fail), self.assertRaises(OSError): self.extend()
        with self.assertRaisesRegex(ValueError, "ROLLBACK_OR_LOSS"): c.Ledger(self.ledger.root)
        # Explicit recovery on synthetic copy only: retain stranded primary bytes.
        source = self.ledger.root / "journal-000025.json"
        (self.ledger.mirror / source.name).write_bytes(source.read_bytes())
        self.assertEqual(c.Ledger(self.ledger.root).summary()["effective_caps"]["total_gpu_seconds"], 430000)
        self.preserved()

    def test_corrupt_authority_gap_prefix_and_removed_extension_fail_closed(self):
        self.extend()
        path = self.ledger.root / "journal-000025.json"
        original = path.read_bytes()
        for mutate in (lambda e: e.update(previous="0" * 64), lambda e: e.update(historical_events=23),
                lambda e: e["authority"].update(body=e["authority"]["body"] + "tamper")):
            bad = json.loads(original); mutate(bad)
            for root in (self.ledger.root, self.ledger.mirror):
                (root / path.name).write_text(json.dumps(bad), encoding="utf8")
            with self.assertRaises(ValueError): c.Ledger(self.ledger.root)
        for root in (self.ledger.root, self.ledger.mirror): (root / path.name).write_bytes(original)
        req = self.released_request(); self.ledger.reserve(req)
        for root in (self.ledger.root, self.ledger.mirror): (root / path.name).unlink()
        with self.assertRaises(ValueError): c.Ledger(self.ledger.root)

    def test_parallel_extension_has_one_winner_and_no_second_budget(self):
        def run():
            try: return self.extend()["kind"]
            except (ValueError, OSError, RuntimeError): return "BLOCKED"
        with ThreadPoolExecutor(2) as pool: results = list(pool.map(lambda _: run(), range(2)))
        self.assertEqual(results.count(o5.KIND), 1)
        self.assertEqual(len(self.ledger.events()), 25)
        self.preserved()

    def test_resource_decision_alone_cannot_stage_or_activate_attempt8(self):
        self.extend()
        req = self.released_request()
        req["bindings"]["runtime"].pop("o5_execution_release")
        with self.assertRaises(ValueError): self.ledger.reserve(req)
        with patch.object(old, "_active", None), self.assertRaises(ValueError): old.activate(req, "launch", intent={})
        req["bindings"]["runtime"].pop("o5_extension")
        with self.assertRaisesRegex(ValueError, "EXTENSION_REQUIRED"): self.ledger.reserve(req)
        self.assertEqual(len(self.ledger.events()), 25)

    def test_resume_ordinal2_success_replay_source_measure_and_duplicate_reservation(self):
        self.extend(); req = self.released_request()
        self.assertEqual(req["plan"]["scheduled_ordinals"], [2])
        intent = self.ledger.reserve(req)
        self.assertEqual(intent["o5_extension_sha256"], digest(req["bindings"]["runtime"]["o5_extension"]))
        self.assertEqual(self.ledger.summary()["reserved_gpu_seconds"], 28800)
        with self.assertRaisesRegex(ValueError, "ACTIVE_INTENT"): self.ledger.reserve(req)
        with lock(self.ledger.root): self.ledger.append("ABORTED_PRE_SUBMIT", intent_sha256=digest(intent), refund=False)
        self.assertEqual(self.ledger.summary()["reserved_gpu_seconds"], 28800)
        self.preserved()

    def test_multicall_requires_current_measurement_and_job_seconds_unchanged(self):
        self.extend()
        req = self.released_request(calls=2)
        with self.assertRaisesRegex(ValueError, "MEASUREMENTS_REQUIRED"): self.ledger.reserve(req)
        req = self.released_request(seconds=7201)
        with self.assertRaisesRegex(ValueError, "JOB_CAPS"): self.ledger.reserve(req)
        with lock(self.ledger.root):
            self.ledger.append("MEASURED", source_sha256=digest(runtime.source_spec()), safe_calls=205,
                overhead_seconds=640, per_call_seconds=32, minimum_seconds=7200)
        req = self.released_request(calls=205, seconds=7200)
        self.assertEqual(c.required_job_seconds(self.ledger.events()[-1], 205), 7200)
        self.assertEqual(self.ledger.reserve(req)["reserved_gpu_seconds"], 14400)

    def test_no_reservation_above_old_or_new_total_and_no_calls_jobs_refund(self):
        self.extend()
        events = self.ledger.events()
        req = self.released_request(seconds=7200)
        extension_sha = digest(events[-1])
        # Feed synthetic chained copies to the actual cumulative accounting gate.
        for n in range(28):
            events.append({"kind": "INTENT", "request": req, "reserved_calls": 1, "reserved_gpu_seconds": 14400,
                "o5_extension_sha256": extension_sha})
        budget = self.ledger._budget(events)
        self.assertEqual(budget["reserved_gpu_seconds"], 428400)
        events.append(deepcopy(events[-1]))
        with self.assertRaisesRegex(ValueError, "BUDGET_EXCEEDED"): self.ledger._budget(events)
        for dimension in ("total_calls", "total_jobs"):
            events = self.ledger.events()
            cap_req = deepcopy(req)
            cap_req["plan"]["max_seconds"] = 120
            cap_req["plan"]["max_calls"] = 1000 if dimension == "total_calls" else 1
            future = {"kind": "INTENT", "request": cap_req,
                "reserved_calls": cap_req["plan"]["max_calls"], "reserved_gpu_seconds": 240,
                "o5_extension_sha256": extension_sha}
            n = 4 if dimension == "total_calls" else 93
            events += [deepcopy(future) for _ in range(n)]
            self.ledger._budget(events)
            events.append(deepcopy(future))
            with self.subTest(dimension=dimension), self.assertRaisesRegex(ValueError, "BUDGET_EXCEEDED"):
                self.ledger._budget(events)

    def test_fsync_failure_and_registration_byte_drift_cannot_retry_extension(self):
        with patch.object(c, "_sync_directory", side_effect=OSError("injected fsync failure")), self.assertRaises(OSError):
            self.extend()
        with self.assertRaisesRegex(ValueError, "ROLLBACK_OR_LOSS"): self.extend()
        self.preserved()
        # Whitespace-only changes are still forbidden for original registration.
        registration = self.ledger.root / "registration.json"
        registration.write_bytes(registration.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "REGISTRATION_BYTES_DRIFT"): c.Ledger(self.ledger.root)
        events = self.ledger.events()[:24]
        old_req = deepcopy(req); old_req["bindings"]["runtime"].pop("o5_extension")
        for n in range(3): events.append({"kind": "INTENT", "request": old_req, "reserved_calls": 1, "reserved_gpu_seconds": 14400})
        self.assertEqual(self.ledger._budget(events)["reserved_gpu_seconds"], 68400)
        events.append(deepcopy(events[-1]))
        with self.assertRaisesRegex(ValueError, "BUDGET_EXCEEDED"): self.ledger._budget(events)

    def test_status_forecast_cli_use_effective_cap_without_network_or_mutation(self):
        from scripts import train3763_campaign as cli
        self.extend(); before = self.snapshot()
        for action in ("status", "forecast"):
            out = io.StringIO()
            with patch.object(old, "get", side_effect=AssertionError("read-only must be offline")), redirect_stdout(out):
                self.assertEqual(cli.main([action, "--directory", str(self.ledger.root)]), 0)
            value = json.loads(out.getvalue())
            caps = value["effective_caps"] if action == "status" else value["inputs"]["caps"]
            self.assertEqual(caps["total_gpu_seconds"], 430000)
        self.assertEqual(self.snapshot(), before)

    def test_execution_release_wrong_reviewer_source_or_extension_cannot_submit(self):
        self.extend(); req = self.released_request()
        original = deepcopy(self.comments["/issues/comments/3000"])
        for change in ("reviewer", "source", "extension", "status", "test"):
            self.comments["/issues/comments/3000"] = deepcopy(original)
            if change == "reviewer": self.comments["/issues/comments/3000"]["user"]["login"] = "untrusted"
            else:
                value = json.JSONDecoder().raw_decode(original["body"][original["body"].index("{"):])[0]
                value[{"source": "source_sha256", "extension": "extension_sha256", "status": "status", "test": "test"}[change]] = True
                req["bindings"]["runtime"]["o5_execution_release"] = self.comment(3000,
                    "SAFESHIFT_TRAIN3763_O5_EXECUTION_V1", value, "synthetic-reviewer", 181)
            with self.subTest(change=change), self.assertRaises(ValueError): self.ledger.reserve(req)
        self.assertEqual(len(self.ledger.events()), 25)

    def test_custody_loss_and_extra_history_block_extension_without_writes(self):
        path = self.root / "export-7.zip"
        original = path.read_bytes(); path.write_bytes(original[:30])
        with self.assertRaises(ValueError): self.extend()
        path.write_bytes(original)
        with lock(self.ledger.root):
            self.ledger.append("MEASURED", source_sha256="0" * 64, safe_calls=205, minimum_seconds=7200)
        with self.assertRaisesRegex(ValueError, "PREFIX"): self.extend()
        self.assertEqual(len(self.ledger.events()), 25)

    def test_extension_cli_reports_no_execution_and_auth_failure_preserves_history(self):
        from scripts import train3763_campaign as cli
        locator_path = self.root / "locator.json"; write(locator_path, self.original_locator)
        out = io.StringIO()
        with redirect_stdout(out):
            cli.main(["extend-o5", "--directory", str(self.ledger.root), "--grant", str(locator_path)])
        self.assertEqual(json.loads(out.getvalue())["status"], "O5_EXTENSION_APPENDED_NO_EXECUTION")
        before = self.snapshot()
        req = self.released_request()
        with patch.object(old, "get", side_effect=OSError("GitHub unavailable")), self.assertRaises(OSError):
            self.ledger.reserve(req)
        self.assertEqual(self.snapshot(), before)


class PublicO5IdentityTests(unittest.TestCase):
    def test_real_public_decision_hash_and_structured_identity_are_pinned(self):
        body = PUBLIC_BODY.read_bytes()
        self.assertEqual(hashlib.sha256(body).hexdigest(), o5.BODY_SHA256)
        value = json.JSONDecoder().raw_decode(body.decode()[body.decode().index("{"):])[0]
        self.assertEqual(digest(value), o5.DECISION_SHA256)
        self.assertEqual(value["original_campaign_sha256"], o5.ORIGINAL_SHA256)
        self.assertEqual(value["science_sha256"], digest(c.science()))
        self.assertEqual(value["limits_after"], {**value["limits_before"], "total_gpu_seconds": 430000})


if __name__ == "__main__": unittest.main()
