"""Synthetic provider/CLI tests; never import Kaggle or load model weights."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
import zipfile
from unittest.mock import Mock, patch

from safeshift import kaggle_handoff as h
from safeshift.pilot.artifacts import write, read, sha
from scripts import rehearse_kaggle_handoff as fixture


class HandoffTests(unittest.TestCase):
    def setUp(self):
        parent = h.ROOT / "data/processed/handoff-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "session"
        self.session = h.prepare(self.root, fixture.request("synthetic-test"))
        fixture.advance(self.root, "RUNNING")

    def operate(self, action, operator=None):
        with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")):
            return h.operate(h.Session(self.root), operator or fixture.SyntheticOperator(self.root),
                action, clock=lambda: 2, sleep=lambda _: None) if action == "collect" else h.operate(
                h.Session(self.root), operator or fixture.SyntheticOperator(self.root), action,
                clock=iter([0, 2]).__next__, sleep=lambda _: None)

    def test_running_stop_reopen_terminal_collection_and_codex_acceptance(self):
        first = self.operate("start")
        self.assertEqual(first["status"], "RUNNING_UNVERIFIED")
        self.assertFalse(list(self.root.glob("collection-*")))
        self.assertFalse(first["job_cancelled"])
        fixture.advance(self.root, "COMPLETE")
        final = self.operate("collect")
        self.assertEqual((final["status"], final["verification"]["model_calls"]), ("PASS", 0))
        self.assertEqual(h.accept_report(h.Session(self.root)), final)
        self.assertEqual(len([e for e in self.session.events() if e["status"] == "SUBMISSION_INTENT"]), 1)

    def test_user_message_does_not_override_real_running_status(self):
        self.operate("start")
        op = fixture.SyntheticOperator(self.root)
        op.download = Mock(side_effect=AssertionError("NO_DOWNLOAD_WHILE_RUNNING"))
        self.assertEqual(self.operate("collect", op)["status"], "RUNNING_UNVERIFIED")
        op.download.assert_not_called()

    def test_terminal_error_preserves_artifacts_and_reports_fail(self):
        fixture.advance(self.root, "ERROR")
        result = self.operate("start")
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["evidence"])
        self.assertEqual(result["terminal"], "ERROR")
        self.assertEqual(h.accept_report(h.Session(self.root))["status"], "FAIL")

    def test_unknown_submit_crash_blocks_replay_but_allows_read_only_reconciliation(self):
        op = fixture.SyntheticOperator(self.root)
        op.submit = Mock(side_effect=TimeoutError("SUBMIT_UNKNOWN"))
        self.assertEqual(self.operate("start", op)["status"], "BLOCKED")
        op.submit.reset_mock()
        self.assertEqual(self.operate("start", op)["status"], "BLOCKED")
        op.submit.assert_not_called()
        fixture.advance(self.root, "COMPLETE")
        self.assertEqual(self.operate("collect")["status"], "PASS")

    def test_duplicate_start_unknown_status_remote_version_source_all_block(self):
        self.operate("start")
        op = fixture.SyntheticOperator(self.root)
        op.submit = Mock(side_effect=AssertionError("NO_RESUBMIT"))
        self.assertEqual(self.operate("start", op)["status"], "BLOCKED")
        fixture.advance(self.root, "UNKNOWN")
        self.assertEqual(self.operate("collect")["status"], "BLOCKED")
        op.identity = lambda r: {"job_id": r["job"], "version": 2, "notebook_sha256": r["notebook_sha256"]}
        self.assertEqual(self.operate("collect", op)["status"], "BLOCKED")

    def test_failed_or_missing_verifier_never_passes_and_partial_files_survive(self):
        fixture.advance(self.root, "COMPLETE")
        op = fixture.SyntheticOperator(self.root)
        op.verify = Mock(side_effect=ValueError("CRC_MISMATCH"))
        self.assertEqual(self.operate("start", op)["status"], "BLOCKED")
        partial = list(self.root.glob("collection-*/synthetic.zip"))
        self.assertEqual(len(partial), 1)
        self.assertEqual(self.operate("collect")["status"], "PASS")
        self.assertTrue(partial[0].is_file())

    def test_codex_rejects_evidence_mutation(self):
        fixture.advance(self.root, "COMPLETE")
        result = self.operate("start")
        next(iter(result["evidence"]))
        target = self.root / next(iter(result["evidence"]))
        target.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "EVIDENCE_DRIFT"):
            h.accept_report(h.Session(self.root))

    def test_actual_sidecar_crc_or_member_corruption_is_blocked_and_preserved(self):
        for defect in ("sidecar", "crc", "member"):
            with self.subTest(defect=defect):
                root = Path(self.tmp.name) / defect
                session = h.prepare(root, fixture.request("synthetic-" + defect))
                fixture.advance(root, "COMPLETE")
                op = fixture.SyntheticOperator(root)
                download = op.download
                def corrupt(request, destination):
                    download(request, destination)
                    archive = destination / "synthetic.zip"
                    sidecar = Path(str(archive) + ".sha256.json")
                    if defect == "sidecar":
                        sidecar.write_text(json.dumps({"sha256": "0"*64}), encoding="utf8")
                    elif defect == "member":
                        with zipfile.ZipFile(archive, "a") as z:
                            z.writestr("extra.json", "{}")
                        sidecar.write_text(json.dumps({"sha256": sha(archive)}), encoding="utf8")
                    else:
                        with zipfile.ZipFile(archive) as z:
                            info = z.getinfo("worker.log")
                        payload = bytearray(archive.read_bytes())
                        offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
                        payload[offset + info.compress_size // 2] ^= 0x10
                        archive.write_bytes(payload)
                        sidecar.write_text(json.dumps({"sha256": sha(archive)}), encoding="utf8")
                op.download = corrupt
                report = h.operate(session, op, "start")
                self.assertEqual(report["status"], "BLOCKED")
                self.assertTrue(list(root.glob("collection-*/synthetic.zip")))

    def test_request_coordinator_test_split_paths_and_caps_fail_closed(self):
        for key, value in (("coordinator_required", True), ("scope", "TEST"), ("version", True),
                ("notebook", "../private"), ("commit_sha", "main"), ("plan_sha256", "0"*64)):
            bad = copy.deepcopy(self.session.request); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                h.validate_request(bad)
        bad = copy.deepcopy(self.session.request); bad["limits"]["monitor_seconds"] = 901
        with self.assertRaises(ValueError):
            h.validate_request(bad)

    def test_production_adapter_blocks_before_sdk_and_credentials(self):
        with patch.dict(sys.modules, {"kaggle": None}):
            self.assertEqual(self.operate("start", h.Train3763Operator())["status"], "BLOCKED")
        self.assertFalse(any(e["status"] == "SUBMISSION_INTENT" for e in self.session.events()))

    def test_chain_mutation_missing_event_and_duplicate_prepare(self):
        with self.assertRaises(FileExistsError):
            h.prepare(self.root, self.session.request)
        self.session.event("OBSERVED")
        path = self.root / "event-00002.json"
        row = read(path); row["previous"] = "0" * 64
        path.write_text(json.dumps(row), encoding="utf8")
        with self.assertRaisesRegex(ValueError, "CHAIN"):
            self.session.events()

    def test_lock_rejects_second_operator_and_releases(self):
        with h.lock(self.root):
            with self.assertRaises(RuntimeError):
                with h.lock(self.root):
                    self.fail("LOCK_BYPASS")
        with h.lock(self.root):
            pass

    def fake_agy(self, argv, **kwargs):
        if argv == ["agy", "--version"]:
            return NS(returncode=0, stdout="1.5.0\n")
        resume = "--conversation" in argv
        self.operate("collect" if resume else "start")
        payload = {"status": "SUCCESS", "conversation_id": "11111111-1111-1111-1111-111111111111", "response": "done"}
        kwargs["stdout"].write(json.dumps(payload).encode())
        return NS(returncode=0)

    def test_json_conversation_persisted_and_explicitly_resumed_after_reopening(self):
        self.assertEqual(h.invoke_agy(self.session, run=self.fake_agy)["status"], "RUNNING_UNVERIFIED")
        self.assertEqual(h.Session(self.root).conversation(), "11111111-1111-1111-1111-111111111111")
        fixture.advance(self.root, "COMPLETE")
        seen = []
        def run(argv, **kwargs):
            seen.append(argv)
            return self.fake_agy(argv, **kwargs)
        report = h.invoke_agy(h.Session(self.root), resume=True, run=run)
        self.assertEqual(report["status"], "PASS")
        self.assertIn("--conversation", seen[-1])
        self.assertEqual(report["conversation_id"], self.session.conversation())
        h.accept_report(self.session)
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            h.invoke_agy(self.session, run=run)

    def test_cli_timeout_blocks_no_automatic_new_conversation_or_submit(self):
        def run(argv, **kwargs):
            if "--version" in argv:
                return NS(returncode=0, stdout="1.5.0")
            raise subprocess.TimeoutExpired(argv, 1)
        result = h.invoke_agy(self.session, run=run)
        self.assertEqual(result["status"], "BLOCKED")
        with self.assertRaises(ValueError):
            h.invoke_agy(self.session, resume=True, run=run)
        self.assertIsNone(self.session.conversation())

    def test_success_envelope_with_denied_action_is_blocked_even_after_step(self):
        def run(argv, **kwargs):
            if "--version" in argv:
                return NS(returncode=0, stdout="1.5.0")
            self.operate("start")
            kwargs["stdout"].write(json.dumps({"status": "SUCCESS",
                "conversation_id": "11111111-1111-1111-1111-111111111111",
                "denied_actions": [{"action": "command"}]}).encode())
            return NS(returncode=0)
        result = h.invoke_agy(self.session, run=run)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason_code"], "AGY_PERMISSION_DENIED")
        self.assertIsNotNone(self.session.conversation())
        self.assertTrue(any(e["status"] == "SUBMITTED" for e in self.session.events()))

    def test_success_envelope_without_fresh_step_cannot_reuse_old_report(self):
        h.invoke_agy(self.session, run=self.fake_agy)
        def run(argv, **kwargs):
            if "--version" in argv:
                return NS(returncode=0, stdout="1.5.0")
            kwargs["stdout"].write(json.dumps({"status": "SUCCESS",
                "conversation_id": self.session.conversation()}).encode())
            return NS(returncode=0)
        result = h.invoke_agy(self.session, resume=True, run=run)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason_code"], "AGY_SUCCESS_WITHOUT_FRESH_OPERATION_REPORT")

    def test_concurrent_ai_turn_and_read_only_recovery(self):
        with h.lock(self.root, "agy.lock"), self.assertRaises(RuntimeError):
            h.invoke_agy(self.session, run=self.fake_agy)
        # No conversation after a crash: recover creates a new read-only turn.
        self.operate("start")
        fixture.advance(self.root, "COMPLETE")
        def run(argv, **kwargs):
            if "--version" in argv:
                return NS(returncode=0, stdout="1.5.0")
            self.assertNotIn("--conversation", argv)
            self.assertIn("--action collect --synthetic", argv[argv.index("-p")+1])
            self.operate("collect")
            kwargs["stdout"].write(json.dumps({"status": "SUCCESS",
                "conversation_id": "22222222-2222-2222-2222-222222222222"}).encode())
            return NS(returncode=0)
        self.assertEqual(h.invoke_agy(self.session, resume=True, recover=True, run=run)["status"], "PASS")
        # Even if a prior conversation ID was recorded, explicit recover=True starts a fresh read-only collect turn.
        def recover_turn(argv, **kwargs):
            if "--version" in argv:
                return NS(returncode=0, stdout="1.5.0")
            self.assertNotIn("--conversation", argv)
            self.operate("collect")
            kwargs["stdout"].write(json.dumps({"status": "SUCCESS",
                "conversation_id": "33333333-3333-3333-3333-333333333333"}).encode())
            return NS(returncode=0)
        self.assertEqual(h.invoke_agy(h.Session(self.root), resume=True, recover=True, run=recover_turn)["status"], "PASS")

    def test_per_turn_permission_is_exact_command_and_no_global_permission_bypass(self):
        h.invoke_agy(self.session, run=self.fake_agy)
        settings = read(self.root / "agy-001.settings.json")
        rule = settings["permissions"]["allow"][-1]
        self.assertTrue(rule.startswith("command(regex:^python"))
        self.assertTrue(rule.endswith("$)"))
        self.assertNotIn("toolPermission", settings)
        self.assertNotIn("command(*)", rule)

    def test_process_exit_recovery_with_no_live_agent(self):
        cmd = [sys.executable, "-B", "-m", "scripts.kaggle_handoff", "step",
            "--directory", str(self.root), "--synthetic", "--action"]
        first = subprocess.run(cmd + ["start"], cwd=h.ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(first.stdout)["status"], "RUNNING_UNVERIFIED")
        fixture.advance(self.root, "COMPLETE")
        second = subprocess.run(cmd + ["collect"], cwd=h.ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
