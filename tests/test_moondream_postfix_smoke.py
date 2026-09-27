"""Fake runner and temporary artifacts only; no GPU, download or model execution."""

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import w2_moondream_postfix_smoke as postfix
from scripts import w2_moondream_t4_smoke as smoke
from tests import test_moondream_runner_smoke as fakes


class PostfixTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.repo = Path(self.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        self.cache = self.repo / postfix.CACHE_DIR
        self.cache.mkdir(parents=True)
        self.artifact = self.repo / postfix.ARTIFACT_ROOT
        self.stack.enter_context(patch.object(postfix, "ROOT", self.repo))
        self.stack.enter_context(patch.dict(postfix.os.environ, {"CUDA_VISIBLE_DEVICES": "0"}))
        self.stack.enter_context(redirect_stdout(StringIO()))
        self.stack.enter_context(redirect_stderr(StringIO()))
        self.git = self.stack.enter_context(patch.object(
            postfix.subprocess, "check_output",
            side_effect=lambda command, **kw: "a" * 40 if command[1] == "rev-parse" else ""))
        self.runner = fakes.SmokeTests().fake_runner()
        self.factory = self.stack.enter_context(patch.object(
            postfix, "Moondream2Runner", side_effect=self.construct))
        self.argv = ["--execute-postfix-smoke", "--venue-network-disabled",
                     "--expected-commit", "a" * 40, "--run-id", "moondream-postfix-smoke-test"]

    def construct(self, *args):
        self.assertTrue((self.artifact / "ATTEMPT.json").is_file())
        self.assertTrue((self.artifact / "result.json").is_file())
        self.assertEqual(args[0], self.cache / "models--vikhyatk--moondream2" / "snapshots" / postfix.REVISION)
        self.assertEqual(args[1], self.cache / "models--moondream--starmie-v1" / "snapshots" / postfix.TOKENIZER_REVISION)
        return self.runner

    def report(self):
        return json.loads((self.artifact / "result.json").read_text())

    def assert_consumed(self):
        before = {p.relative_to(self.repo): p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}
        count = self.factory.call_count
        for run_id in (self.argv[-1], "moondream-postfix-smoke-different"):
            with self.assertRaises(FileExistsError):
                postfix.main(self.argv[:-1] + [run_id])
        self.assertEqual(self.factory.call_count, count)
        self.assertEqual(before, {p.relative_to(self.repo): p.read_bytes()
                                  for p in self.repo.rglob("*") if p.is_file()})

    def test_success_is_separate_raw_before_check_correct_provenance_no_second_attempt(self):
        # Sentinel in a disposable test repository only, never a real historical ledger.
        old = self.repo / "data/processed/moondream_t4_smoke"
        old.mkdir()
        for name in ("ATTEMPT.json", "result.json"):
            (old / name).write_bytes(b"synthetic sentinel, not runtime evidence")
        original = smoke.check_native
        def check(value, task):
            saved = list(self.artifact.glob("raw/*/response.raw"))
            self.assertEqual(len(saved), 1 if task.value == "classification" else 2)
            return original(value, task)
        with patch.object(smoke, "check_native", side_effect=check):
            self.assertEqual(postfix.main(self.argv), 0)
        report = self.report()
        self.assertEqual(report["schema_version"], "moondream-postfix-smoke-result-v1")
        self.assertEqual(report["status"], "RUNTIME_INTERFACE_PASS")
        self.assertEqual(report["historical_official_smoke"], {
            "run_id": postfix.HISTORICAL_RUN, "status": "FAIL", "attempt_consumed": True, "superseded": False})
        self.runner.initialize.assert_called_once()
        self.runner.load.assert_called_once()
        self.assertEqual([report["runtime"][k] for k in
                          ("model_load_count", "query_call_count", "detect_call_count")], [1, 1, 1])
        for path in self.artifact.glob("raw/*/metadata.json"):
            metadata = json.loads(path.read_text())
            self.assertEqual(metadata["command"], report["command"])
            self.assertEqual(json.loads(metadata["command"])[0], "scripts/w2_moondream_postfix_smoke.py")
            self.assertEqual(metadata["parse_status"], "NOT_ATTEMPTED")
            self.assertEqual(metadata["git_commit_sha"], "a" * 40)
        for path in old.iterdir():
            self.assertEqual(path.read_bytes(), b"synthetic sentinel, not runtime evidence")
        self.assert_consumed()

    def test_query_failure_preserves_partial_raw_and_consumes_attempt(self):
        self.runner = fakes.SmokeTests().fake_runner(fail="query")
        self.assertEqual(postfix.main(self.argv), 1)
        self.assertTrue(self.report()["calls"][0]["partial"])
        self.assertEqual(self.runner.evidence["detect_call_count"], 0)
        self.assert_consumed()

    def test_load_failure_consumes_attempt_without_calls(self):
        self.runner.load.side_effect = ValueError("synthetic load failure")
        self.assertEqual(postfix.main(self.argv), 1)
        self.assertEqual(self.report()["errors"][0]["stage"], "load")
        self.assertEqual(self.report()["calls"], [])
        self.assert_consumed()

    def test_interruption_consumes_attempt_even_without_report(self):
        self.runner.load.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            postfix.main(self.argv)
        self.assertEqual((self.artifact / "result.json").read_bytes(), b"")
        self.assert_consumed()

    def test_failed_state_audit_cannot_pass(self):
        self.runner.evidence["state_audits"][0] = {"status": "FAILED"}
        self.assertEqual(postfix.main(self.argv), 1)
        self.assertEqual(self.report()["errors"][0]["stage"], "final_invariants")

    def test_missing_image_boundary_cannot_pass(self):
        self.runner.evidence["image_boundaries"].pop()
        self.assertEqual(postfix.main(self.argv), 1)

    def test_wrong_call_count_cannot_pass(self):
        self.runner.evidence["query_call_count"] = 1
        self.assertEqual(postfix.main(self.argv), 1)

    def test_wrong_commit_dirty_checkout_and_missing_cache_reject_before_reservation(self):
        for head, dirty in (("b" * 40, ""), ("a" * 40, " M tracked.py"),
                            ("a" * 40, "?? untracked.py")):
            with self.subTest(head=head, dirty=dirty):
                self.git.side_effect = [head, dirty]
                with self.assertRaises(SystemExit):
                    postfix.main(self.argv)
        self.git.side_effect = ["a" * 40, ""]
        self.cache.rmdir()
        with self.assertRaises(SystemExit):
            postfix.main(self.argv)
        self.factory.assert_not_called()
        self.assertFalse(self.artifact.exists())

    def test_cli_requires_postfix_id_exact_sha_execution_and_network_flags(self):
        cases = [self.argv[1:], [a for a in self.argv if a != "--venue-network-disabled"],
                 self.argv[:-1] + [postfix.HISTORICAL_RUN], self.argv[:-1] + ["../escape"],
                 ["main" if a == "a" * 40 else a for a in self.argv]]
        for argv in cases:
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                postfix.main(argv)
        self.git.assert_not_called()
        self.factory.assert_not_called()
        self.assertFalse(self.artifact.exists())

    def test_process_visibility_mask_required(self):
        for mask in ("", "0,1", "1"):
            with patch.dict(postfix.os.environ, {"CUDA_VISIBLE_DEVICES": mask}), self.assertRaises(SystemExit):
                postfix.main(self.argv)
        self.factory.assert_not_called()
        self.assertFalse(self.artifact.exists())


if __name__ == "__main__":
    unittest.main()
