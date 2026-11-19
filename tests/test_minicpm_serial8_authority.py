"""CPU-only GitHub request accounting, signed child gates and source transition."""
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError, URLError

import test_minicpm_fulltrain_execution as fixtures
from safeshift.fulltrain import contract, minicpm_execution as entry, minicpm_release as a
from safeshift.fulltrain import minicpm_offline as policy, minicpm_v5_incident as v5
from safeshift.fulltrain import minicpm_recovery as recovery, minicpm_serial7 as s7
from safeshift.pilot.artifacts import read, sha, write
from safeshift.pilot.contract import digest
from scripts import minicpm_offline_continuation as operator


class TransportTests(unittest.TestCase):
    def test_http_transport_refuses_without_retries_or_sensitive_error_text(self):
        for status, headers, kind in (
            (403, {"X-RateLimit-Remaining": "0"}, "RATE_LIMITED_HTTP_403"),
            (403, {"Retry-After": "60"}, "RATE_LIMITED_HTTP_403"),
            (429, {}, "RATE_LIMITED_HTTP_429"),
            (403, {}, "FORBIDDEN_HTTP_403"),
            (404, {}, "NOT_FOUND_HTTP_404"),
            (503, {}, "HTTP_ERROR_HTTP_503"),
        ):
            error = HTTPError("https://private", status, "sensitive", headers, BytesIO(b"sensitive"))
            self.check_failure(error, kind)
        self.check_failure(TimeoutError("sensitive"), "TIMEOUT")
        self.check_failure(URLError(TimeoutError("sensitive")), "TIMEOUT")
        self.check_failure(URLError(ConnectionError("sensitive")), "CONNECTION")

    def check_failure(self, error, kind):
        opener = Mock()
        opener.open.side_effect = error
        with patch("urllib.request.build_opener", return_value=opener), patch.object(Path, "is_dir", return_value=True):
            with self.assertRaisesRegex(PermissionError, "^MINICPM_LIVE_GITHUB_" + kind + "$"):
                a.github_get("/pulls/207")
        opener.open.assert_called_once()
        self.assertNotIn("Authorization", opener.open.call_args.args[0].headers)

    def test_malformed_github_content_is_blocked(self):
        for raw in (b"{", b"[]", b'{"id":1,"id":2}', b'{"message":"sensitive"}'):
            opener = MagicMock()
            response = opener.open.return_value.__enter__.return_value
            response.geturl.return_value = a.API + "/issues/comments/1"
            response.read.return_value = raw
            with patch("urllib.request.build_opener", return_value=opener), patch.object(Path, "is_dir", return_value=True):
                with self.assertRaisesRegex(PermissionError, "^MINICPM_LIVE_GITHUB_CONTENT$"):
                    a.github_get("/issues/comments/1")


class Serial8AuthorityTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.ExecutionTests.setUpClass.__func__)
    tearDownClass = classmethod(fixtures.ExecutionTests.tearDownClass.__func__)
    make_ticket = fixtures.ExecutionTests.make_ticket
    fake_graph = fixtures.ExecutionTests.fake_graph

    def setUp(self):
        fixtures.ExecutionTests.setUp(self)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(a, "CLAIMS", self.root / "claims"))
        self.stack.enter_context(patch.object(recovery, "validate_recovery"))
        self.stack.enter_context(patch.object(v5, "validate_repair"))
        self.stack.enter_context(patch.object(recovery, "authenticate_recovery", side_effect=self.recovery_reads))
        self.stack.enter_context(patch.object(v5, "authenticate_repair", side_effect=self.repair_reads))
        _, old_graph = self.fake_graph()
        self.tree = old_graph["/git/trees/" + "a" * 40 + "?recursive=1"]
        self.grant.update(schema=a.RECOVERY_SCHEMA, authorization="OWNER_MINICPM_TRAIN3763_RESTART_SERIAL_UI_ONLY",
            campaign_id="synthetic", implementation_pr=207, runtime_commit="a" * 40,
            recovery={"journals": []}, repair={"schema": v5.SCHEMA, "journal_head_sha256": "e" * 64})
        self.grant["caps"].update(total_calls=15000, total_gpu_seconds=1000000)
        self.grant["expires_unix"] = self.grant["issued_unix"] + policy.RELEASE_SECONDS
        self.grant["offline"] = {
            "schema": policy.TRANSITION_SCHEMA, "decision_issue": 202, "operator_session": policy.ORIGINAL_SESSION,
            "base_journal_head_sha256": "e" * 64, "tools_sha256": digest(operator.tools_manifest()),
            "tool_blobs": operator.tool_blobs(), "unmeasured_calls": 100,
            "serial6_event_sha256": operator.serial6.EVENT_SHA, "serial6_supervisor_sha256": operator.serial6.ZIP_SHA,
            "serial7": {"event_sha256": s7.EVENT_SHA, "provider_closure_sha256": "d" * 64},
        }
        self.grant["approvals"] = {a.PROOF_KEY: "0" * 64}
        self.value.update(job="nguynanhtn/safeshift-minicpm-synthetic-8",
                          capsule_ref="nguynanhtn/safeshift-minicpm-capsule-synthetic-8/1")
        self.value["input_sources"]["dataset_sources"][-1] = self.value["capsule_ref"]
        self.graph = {}
        for number in range(20, 33):
            self.comment(number, 198, "SYNTHETIC_HISTORY", {"record": number})
        old = deepcopy(self.grant)
        old.update(implementation_pr=205, merged_sha=s7.MERGE)
        old["scope"]["source_sha256"] = s7.SOURCE
        old["offline"].update(schema=policy.SCHEMA)
        del old["offline"]["serial7"]
        s7_locator = self.comment(s7.RELEASE["comment_id"], 205, policy.RELEASE, old)
        self.stack.enter_context(patch.object(s7, "RELEASE", s7_locator))
        self.stack.enter_context(patch.object(s7, "GRANT_SHA", digest(old)))
        for number, role in enumerate(recovery.SOURCE_ROLES, 2):
            self.grant["approvals"][role] = self.comment(number, 207, a.APPROVAL,
                {"kind": role, "status": "APPROVED", "reviewed_head": self.grant["reviewed_head"],
                 "subject_sha256": a.subject(self.grant)})
        for ref in ("a" * 40, "b" * 40):
            tree = deepcopy(self.tree)
            tree["tree"].extend({"path": name, "type": "blob", "mode": "100644", "sha": blob}
                for name, blob in self.grant["offline"]["tool_blobs"].items())
            self.graph["/git/trees/" + ref + "?recursive=1"] = tree
        self.graph["/pulls/207"] = {"merged": True, "draft": False, "base": {"ref": "main"},
            "head": {"sha": "a" * 40}, "merge_commit_sha": "b" * 40}
        proof = a.collect_proof(self.grant, {"comment_id": 1}, self.graph.__getitem__)
        self.grant["approvals"][a.PROOF_KEY] = digest(proof)
        self.locator = self.comment(1, 207, policy.TRANSITION_RELEASE, self.grant)
        self.gets = Counter()
        self.stage = "launch"
        self.max_gets = 60
        self.stack.enter_context(patch.object(a, "github_get", side_effect=self.get))

    def recovery_reads(self, grant, reader, *, rights):
        for number in range(20, 29 if rights else 24):
            self.check_history(number, reader)

    def repair_reads(self, grant, reader):
        for number in range(29, 33):
            self.check_history(number, reader)

    def check_history(self, number, reader):
        path = "/issues/comments/" + str(number)
        row = self.graph[path]
        locator = {"comment_id": number, "body_sha256": hashlib.sha256(row["body"].encode()).hexdigest()}
        a.owner_comment(reader(path), locator, 198)

    def comment(self, number, issue, marker, value):
        body = marker + "\n```json\n" + json.dumps(value) + "\n```"
        self.graph["/issues/comments/" + str(number)] = {"body": body, "id": number,
            "issue_url": a.API + "/issues/" + str(issue), "user": {"id": a.OWNER_ID, "login": a.OWNER}}
        return {"comment_id": number, "body_sha256": hashlib.sha256(body.encode()).hexdigest()}

    def get(self, path):
        self.gets[self.stage] += 1
        if sum(self.gets.values()) > self.max_gets:
            raise PermissionError("MINICPM_LIVE_GITHUB_RATE_LIMITED_HTTP_403")
        return deepcopy(self.graph[path])

    def sign(self, value, previous="f" * 64):
        now = int(time.time())
        return operator.old.sign(self.key, self.public, {
            "schema": policy.TRANSITION_TICKET, "grant_sha256": digest(self.grant),
            "value_sha256": digest(value), "capsule_sha256": digest(value), "notebook_code_sha256": "a" * 64,
            "number": 8, "previous_event_sha256": previous, "reserved_before": dict(s7.RESERVED),
            "reserved_after": {"calls": 10729, "jobs": 8, "gpu_seconds": 202800}, "lineage": [],
            "issued_unix": now, "start_before_unix": now + 1800, "sizing": {"calls": 3, "seconds": 600},
            "owner_gate": {"observed_unix": now, "quota": {"used": 0, "reserved": 0, "total": 1000000},
                "job": value["job"], "version": 1, "inputs": value["input_sources"], "no_active_job": True,
                "job_absent": True, "owner_checked": True, "proof_sha256": "a" * 64},
        })

    def run_stages(self, *, fail_cpu=False):
        value = deepcopy(self.value)
        work = self.root / "work"
        value["request"]["work"] = str(work)
        control = work / "supervision" / "synthetic"
        request, context, proof_file = control / "request.json", self.root / "context.json", self.root / "proof.json"
        ticket = self.sign(value)
        proof = {}
        grant = a.load(self.locator, capture=proof)
        with patch.object(a, "bind"):  # Use temporary work root on Windows as well as Linux.
            with a._activated(grant, self.locator, ticket, value, "launch"):
                write(request, value["request"])
                write(context, {"locator": self.locator, "value": value, "ticket": ticket})
                write(proof_file, proof)
                a.current().update(context_file=str(context), proof_file=str(proof_file))
                commands = {
                    stage: entry.child_command(sys.executable, stage, request, a.ROOT, control / stage, time.monotonic() + 60)
                    for stage in a.STAGES[1:]
                }
            executed = []

            def stage(mode, req, repo, output, deadline):
                contract.authorize(request=req)
                executed.append(mode)
                write(output / "stage.json", {"status": "RETURNED", "stage": mode, "request_sha256": digest(req),
                    "source_sha256": req["source_sha256"], "native_attempt_permitted": mode == "native"})

            with patch("safeshift.fulltrain.admission.stage", side_effect=stage):
                for self.stage, argv in commands.items():
                    if fail_cpu and self.stage == "cpu":
                        self.max_gets = sum(self.gets.values()) + 1
                        with patch.object(sys, "argv", argv[3:]), self.assertRaisesRegex(PermissionError, "RATE_LIMITED"):
                            entry.main()
                        break
                    with patch.object(sys, "argv", argv[3:]):
                        entry.main()
                    write(control / (self.stage + "-process.json"), {"schema": "fresh-process-supervision-v1",
                        "status": "EXITED", "returncode": 0, "group_exit": {"status": "NO_LIVE_MEMBERS"}})
                if not fail_cpu:
                    with patch.object(sys, "argv", commands["native"][3:]), self.assertRaises(FileExistsError):
                        # Demonstrate HTTP is checked before reaching the create-only replay fence.
                        with patch.object(a, "github_get", side_effect=self.graph.__getitem__):
                            entry.main()
            claims = self.root / "claims" / "synthetic" / "8"
            self.assertFalse((claims / "load.json").exists())
            self.assertEqual(list(claims.glob("call-*.json")), [])
            self.assertEqual((claims / "cpu.json").exists(), not fail_cpu)
            return executed

    def test_all_stages_use_two_gets_each_below_anonymous_budget(self):
        self.assertEqual(self.run_stages(), list(a.STAGES[1:]))
        self.assertEqual(dict(self.gets), {"launch": 22, **dict.fromkeys(a.STAGES[1:], 2)})
        self.assertEqual(sum(self.gets.values()), 34)

    def test_cpu_http_failure_has_no_claim_and_never_fetches_later_stages(self):
        self.assertEqual(self.run_stages(fail_cpu=True), ["admit", "setup", "reclaim"])
        self.assertEqual(dict(self.gets), {"launch": 22, "admit": 2, "setup": 2, "reclaim": 2, "cpu": 2})

    def test_historical_shape_hits_61st_get_in_cpu_with_clean_60_get_budget(self):
        old = deepcopy(self.grant)
        old["offline"]["schema"] = policy.SCHEMA
        del old["offline"]["serial7"]
        old["approvals"] = {}
        for number, role in enumerate(recovery.SOURCE_ROLES, 2):
            old["approvals"][role] = self.comment(number, 207, a.APPROVAL,
                {"kind": role, "status": "APPROVED", "reviewed_head": old["reviewed_head"],
                 "subject_sha256": a.subject(old)})
        locator = self.comment(1, 207, policy.RELEASE, old)
        a.load(locator)
        for self.stage in ("admit", "setup", "reclaim"):
            a.load(locator, approvals=False)
        self.stage = "cpu"
        with self.assertRaisesRegex(PermissionError, "RATE_LIMITED"):
            a.load(locator, approvals=False)
        self.assertEqual(dict(self.gets), {"launch": 21, "admit": 10, "setup": 10, "reclaim": 10, "cpu": 10})
        self.assertEqual(sum(self.gets.values()), 61)

    def test_live_release_pr_bundle_trees_and_expiry_fail_closed(self):
        cached = {}
        a.load(self.locator, capture=cached)
        with self.assertRaisesRegex(ValueError, "PROOF_MISSING"):
            a.load(self.locator, child=True)
        with self.assertRaisesRegex(ValueError, "FULL_SOURCE_AUTHORITY"):
            a.load(self.locator, child=True, approvals=False, stage_proof=cached)
        altered = deepcopy(cached)
        altered["/issues/comments/2"]["user"]["id"] = 0
        with self.assertRaisesRegex(ValueError, "PROOF_PIN"):
            a.load(self.locator, child=True, stage_proof=altered)
        with patch.object(a, "github_get", side_effect=PermissionError("LIVE_REQUIRED")):
            with self.assertRaisesRegex(PermissionError, "LIVE_REQUIRED"):
                a.load(self.locator, child=True, stage_proof=cached)
        for path, change, reason in (
            ("/issues/comments/1", lambda r: r["user"].update(id=0), "AUTHENTIC_OWNER_RECORD"),
            ("/issues/comments/1", lambda r: r.update(body=r["body"] + "\n"), "AUTHENTIC_OWNER_RECORD"),
            ("/issues/comments/2", lambda r: r["user"].update(id=0), "AUTHENTIC_OWNER_RECORD"),
            ("/pulls/207", lambda r: r["head"].update(sha="e" * 40), "REVIEW_AUDIT_MERGE"),
            ("/git/trees/" + "a" * 40 + "?recursive=1",
             lambda r: r["tree"][0].update(sha="e" * 40), "MERGED_RUNTIME_BYTES"),
        ):
            with self.subTest(path=path, reason=reason):
                graph = deepcopy(self.graph)
                change(graph[path])
                with self.assertRaisesRegex(ValueError, reason):
                    a.load(self.locator, reader=graph.__getitem__)
        with patch.object(a.time, "time", return_value=self.grant["expires_unix"]):
            with self.assertRaisesRegex(ValueError, "AUTHORITY_EXPIRED"):
                a.load(self.locator, child=True, stage_proof=cached, reader=self.graph.__getitem__)

    def test_serial8_signed_ticket_cannot_reuse_serial7_or_change_job(self):
        ticket = self.sign(self.value)
        a.verify_ticket(self.grant, ticket, self.value)
        self.assertEqual(ticket["payload"]["reserved_before"], s7.RESERVED)
        plan = self.value["request"]["plan"]
        self.assertEqual(plan["counts"], {"NOT_ATTEMPTED": 3763})
        self.assertEqual(plan["scheduled_ordinals"][0], 0)
        other = deepcopy(self.value)
        other["job"] = other["job"][:-1] + "7"
        with self.assertRaisesRegex(ValueError, "SIGNED|TICKET_BINDING"):
            a.verify_ticket(self.grant, ticket, other)
        bad = deepcopy(ticket)
        bad["signature"] = "0" * 768
        with self.assertRaisesRegex(ValueError, "SIGNATURE_INVALID"):
            a.verify_ticket(self.grant, bad, self.value)

    def test_serial8_registration_preserves_old_fence_and_requires_provider_closure(self):
        provider = {"job_id": s7.JOB, "version": 1, "state": "COMPLETE", "kernel_id": 37,
                    "notebook_code_sha256": "a" * 64, "safeshift_metadata": "MATCHED"}
        active = {"value": self.value, "ticket": self.sign(self.value)}
        local = {"supervisor_sidecar_sha256": "f" * 64}
        closure = {"local": local, "provider": provider,
            "capsule": {"private": True, "version": 1, "files": {
                entry.ui.MARKER: digest(self.value), entry.MARKER: digest(active["ticket"])}},
            "output": {"pairs": {s7.ARCHIVE: s7.ZIP_SHA}, "sidecar_sha256": "f" * 64, "log_sha256": "d" * 64,
                "inventory": [s7.ARCHIVE, s7.ARCHIVE + ".sha256.json"]}}
        self.grant["offline"]["serial7"]["provider_closure_sha256"] = digest(closure)
        processed = self.root / "data/processed"
        (processed / "minicpm-v3-journal").mkdir(parents=True)
        with patch.object(operator, "ROOT", self.root):
            write(operator.fence(), {"frozen": "synthetic"})
            before = sha(operator.fence())
            self.stack.enter_context(patch.object(operator, "authenticate", return_value=self.grant))
            self.stack.enter_context(patch.object(operator, "require_live_transition"))
            self.stack.enter_context(patch.object(operator.old, "clean_source"))
            self.stack.enter_context(patch.object(s7, "verify_local", return_value=(local, active, [operator.fence()])))
            self.stack.enter_context(patch.object(operator, "historical", return_value={"files": {}}))
            args = (processed / "next-primary", processed / "next-mirror", self.locator, {}, self.value,
                processed / "older-closure", policy.ORIGINAL_SESSION)
            with self.assertRaisesRegex(ValueError, "CLOSURE_REQUIRED"):
                operator.Continuation.initialize(*args)
            wrong = deepcopy(closure)
            wrong["output"]["pairs"]["unexpected-attempt.zip"] = "a" * 64
            with self.assertRaisesRegex(ValueError, "CAPSULE_OR_SUPERVISOR"):
                operator.Continuation.initialize(*args, serial7_closure=wrong)
            route = operator.Continuation.initialize(*args, serial7_closure=closure)
            self.assertEqual(route.state()["counts"], {"NOT_ATTEMPTED": 3763})
            self.assertEqual(route.forecast()["next_ordinal"], 0)
            self.assertEqual(route.forecast()["reserved"], s7.RESERVED)
            self.assertTrue(route.forecast()["owner_gate_template"]["job"].endswith("-8"))
            self.assertIsNone(route.state()["active"])
            self.assertEqual(sha(operator.fence()), before)
            self.assertEqual(read(route.root / "registration.json"), read(route.mirror / "registration.json"))


if __name__ == "__main__":
    unittest.main()
