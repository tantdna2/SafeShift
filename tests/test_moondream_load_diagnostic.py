"""Synthetic failures and fake backends only; no GPU or downloaded model code."""

import ast
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from safeshift.runners import moondream2 as runtime
from scripts import w2_moondream_load_diagnostic as diagnostic
from tests.test_moondream_runner_smoke import TORCH, fake_model


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.repo = Path(self.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        self.stack.enter_context(patch.object(diagnostic.subprocess, "check_output", return_value="a" * 40))
        self.stack.enter_context(patch.object(diagnostic.subprocess, "call", return_value=0))
        self.stack.enter_context(patch.object(diagnostic, "version", return_value="fake-version"))
        self.order = []
        self.model = fake_model()
        self.model.query = Mock(side_effect=AssertionError("query forbidden"))
        self.model.detect = Mock(side_effect=AssertionError("detect forbidden"))
        self.backend = types.SimpleNamespace(
            software=runtime.load_plan()["software"], torch=TORCH,
            metadata=Mock(return_value={"cuda_available": True, "gpu_count": 1, "name": "Tesla T4",
                                        "compute_capability": [7, 5], "total_memory": 15 * 1024**3}),
            load=Mock(side_effect=self.fake_load))
        self.stack.enter_context(patch.object(runtime, "deny_network_permanently",
                                             side_effect=lambda: self.order.append("offline")))
        self.stack.enter_context(patch.object(runtime, "require_offline"))
        self.stack.enter_context(patch.object(runtime, "verify_snapshot", return_value={"local_bytes_verified": True}))
        self.stack.enter_context(patch.object(runtime, "_load_claimed", False))
        self.prepare = self.stack.enter_context(patch.object(runtime.Moondream2Runner, "prepare_input",
                                                             side_effect=AssertionError("prepare forbidden")))
        self.generate = self.stack.enter_context(patch.object(runtime.Moondream2Runner, "generate_raw",
                                                              side_effect=AssertionError("generate forbidden")))
        self.factory = self.stack.enter_context(patch.object(diagnostic, "Moondream2Runner",
                                                            side_effect=self.make_runner))

    def fake_load(self, *args):
        self.order.append("backend.load")
        return self.model, types.SimpleNamespace(events=[])

    def make_runner(self, *args):
        self.runner = runtime.Moondream2Runner(*args, backend_factory=lambda: self.backend)
        for name in ("initialize", "load"):
            original = getattr(self.runner, name)
            def call(context, name=name, original=original):
                self.order.append(name)
                return original(context)
            setattr(self.runner, name, Mock(side_effect=call))
        return self.runner

    def run_case(self, run_id="unit-test"):
        report = diagnostic.run_diagnostic(repo=self.repo, cache_dir="data/processed/cache",
                                           run_id=run_id, expected_commit="a" * 40)
        self.assertEqual(report, json.loads((self.repo / report["artifact_path"]).read_text()))
        self.prepare.assert_not_called()
        self.generate.assert_not_called()
        self.model.query.assert_not_called()
        self.model.detect.assert_not_called()
        return report

    def test_success_only_initialize_load_same_runner_and_frozen_context(self):
        report = self.run_case()
        self.assertEqual(report["status"], "LOAD_ONLY_PASS")
        self.assertEqual(report["stage"], "complete")
        self.assertIsNone(report["exception"])
        self.assertEqual(self.order, ["initialize", "offline", "load", "backend.load"])
        self.runner.initialize.assert_called_once()
        self.runner.load.assert_called_once_with(self.runner.initialize.call_args.args[0])
        context = self.runner.initialize.call_args.args[0]
        self.assertEqual(context.decoding, runtime.DECODING)
        self.assertEqual(context.preprocessing, runtime.PREPROCESSING)
        self.assertEqual((context.precision, context.quantization, context.seed), ("FP16", "NONE", None))
        self.assertEqual(report["execution_commit"], "a" * 40)
        self.assertEqual(report["gpu"]["name"], "Tesla T4")
        self.assertEqual(report["software_versions"]["torch"], "fake-version")
        self.assertEqual(report["runner_evidence"]["model_load_count"], 1)
        self.assertEqual(report["runner_evidence"]["query_call_count"], 0)
        self.assertEqual(report["runner_evidence"]["detect_call_count"], 0)
        self.assertEqual(report["runner_evidence"]["image_boundaries"], [])
        args = self.factory.call_args.args
        self.assertEqual(args[0].name, diagnostic.REVISION)
        self.assertEqual(args[1].name, diagnostic.TOKENIZER_REVISION)

    def test_load_valueerror_retains_message_stage_full_traceback_and_evidence(self):
        def failing_backend(*args):
            raise ValueError("specific config failure at /local/cache/config.json")
        self.backend.load.side_effect = failing_backend
        report = self.run_case()
        self.assertEqual(report["status"], "FAIL")
        error = report["exception"]
        self.assertEqual(error["stage"], "load")
        self.assertEqual(error["type"], "ValueError")
        self.assertEqual(error["message"], "specific config failure at /local/cache/config.json")
        self.assertIsNone(error["cause_type"])
        for expected in ("failing_backend", "moondream2.py", "line ", error["message"]):
            self.assertIn(expected, error["traceback"])
        self.assertEqual(report["runner_evidence"]["state_audits"], [])
        self.assertTrue(report["runner_evidence"]["model_manifest"]["local_bytes_verified"])
        self.assertEqual(report["gpu_metadata_source"], "runner.initialize")
        self.backend.load.assert_called_once()

    def test_initialize_failure_writes_report_and_never_loads(self):
        self.backend.software = {"python": "wrong-version"}
        report = self.run_case()
        self.assertEqual(report["exception"]["stage"], "initialize")
        self.assertEqual(report["exception"]["message"], "INSTALLED_SOFTWARE_MISMATCH")
        self.runner.load.assert_not_called()
        self.backend.load.assert_not_called()
        self.assertIsNone(report["gpu"])
        self.assertEqual(report["gpu_metadata_source"], "NOT_REACHED")

    def test_cause_context_and_credentials_sanitized_without_losing_error(self):
        def failing_backend(*args):
            try:
                raise RuntimeError("token=abc-secret at /local/config.json")
            except RuntimeError as cause:
                raise ValueError("bad config Bearer test-credential hf_exampletoken") from cause
        self.backend.load.side_effect = failing_backend
        report = self.run_case()
        error = report["exception"]
        self.assertEqual(error["cause_type"], "RuntimeError")
        self.assertEqual(error["context_type"], "RuntimeError")
        self.assertIn("bad config", error["message"])
        self.assertIn("/local/config.json", error["cause_message"])
        text = json.dumps(report)
        for secret in ("abc-secret", "test-credential", "hf_exampletoken"):
            self.assertNotIn(secret, text)
        self.assertIn("direct cause", error["traceback"])

    def test_redaction_known_environment_json_values_and_url_credentials(self):
        with patch.dict("os.environ", {"TEST_API_KEY": "opaque-secret"}):
            value = diagnostic.redact('opaque-secret {"token": "two word secret"} '
                                      'https://user:password@example.invalid?api_key=abc '
                                      'path=/local/model.json')
        for secret in ("opaque-secret", "two word secret", "user:password", "api_key=abc"):
            self.assertNotIn(secret, value)
        self.assertIn("/local/model.json", value)

    def test_implicit_context_and_interrupt_also_write_failure_reports(self):
        def failing_backend(*args):
            try:
                raise ValueError("original failure")
            except ValueError:
                raise KeyboardInterrupt("interrupted")
        self.backend.load.side_effect = failing_backend
        report = self.run_case()
        self.assertEqual(report["exception"]["type"], "KeyboardInterrupt")
        self.assertEqual(report["exception"]["context_message"], "original failure")
        self.assertIn("original failure", report["exception"]["traceback"])

    def test_official_attempt_and_result_never_opened_created_or_modified(self):
        for existing in (False, True):
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as folder:
                self.repo = Path(folder).resolve()
                official = self.repo / "data/processed/moondream_t4_smoke"
                if existing:
                    official.mkdir(parents=True)
                    for name in ("ATTEMPT.json", "result.json"):
                        (official / name).write_bytes(b'{"status":"FAIL","preserve":"exact bytes"}')
                original_open = Path.open
                def guarded_open(path, *args, **kwargs):
                    self.assertFalse(path.is_relative_to(official), str(path))
                    self.assertNotEqual(path.name, "ATTEMPT.json")
                    return original_open(path, *args, **kwargs)
                # Fail before backend allocation on each invocation.
                self.backend.software = {}
                with patch.object(Path, "open", guarded_open):
                    self.run_case()
                if existing:
                    for name in ("ATTEMPT.json", "result.json"):
                        self.assertEqual((official / name).read_bytes(),
                                         b'{"status":"FAIL","preserve":"exact bytes"}')
                else:
                    self.assertFalse(official.exists())

    def test_existing_diagnostic_is_not_overwritten_or_loaded_again(self):
        self.run_case()
        with self.assertRaises(FileExistsError):
            self.run_case()
        self.factory.assert_called_once()

    def test_path_traversal_rejected_before_runtime(self):
        for run_id in ("../moondream_t4_smoke", "a/b", "a\\b", "..", "C:escape"):
            with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                self.run_case(run_id)
        self.factory.assert_not_called()

    def test_wrong_commit_produces_failure_report_without_runtime(self):
        with patch.object(diagnostic.subprocess, "check_output", return_value="b" * 40):
            report = self.run_case()
        self.assertEqual(report["exception"]["stage"], "provenance")
        self.factory.assert_not_called()

    def test_source_has_no_inference_or_official_smoke_entrypoint(self):
        tree = ast.parse(Path(diagnostic.__file__).read_text())
        forbidden = {"prepare_input", "generate_raw", "generate", "query", "detect", "run_smoke",
                     "execute_call", "snapshot_download", "hf_hub_download"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, forbidden)
            if isinstance(node, ast.Name):
                self.assertNotIn(node.id, forbidden)
        calls = [n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                 and n.func.value.id == "runner"]
        self.assertEqual(calls, ["initialize", "load"])

    def test_cli_success_without_venue_network_flag(self):
        with patch.object(diagnostic, "ROOT", self.repo), patch("builtins.print"):
            code = diagnostic.main(["--execute-load-diagnostic", "--expected-commit", "a" * 40,
                                    "--cache-dir", "data/processed/cache", "--run-id", "cli-test"])
        self.assertEqual(code, 0)
        self.assertTrue((self.repo / diagnostic.ARTIFACT_ROOT / "cli-test/report.json").exists())
        self.assertFalse((self.repo / "data/processed/moondream_t4_smoke").exists())
        self.prepare.assert_not_called()
        self.generate.assert_not_called()
        self.model.query.assert_not_called()
        self.model.detect.assert_not_called()

    def test_cli_failure_exit_and_report(self):
        self.backend.load.side_effect = ValueError("fake CLI failure")
        with patch.object(diagnostic, "ROOT", self.repo), patch("builtins.print"):
            code = diagnostic.main(["--execute-load-diagnostic", "--expected-commit", "a" * 40,
                                    "--cache-dir", "data/processed/cache", "--run-id", "cli-test"])
        self.assertEqual(code, 1)
        report = json.loads((self.repo / diagnostic.ARTIFACT_ROOT / "cli-test/report.json").read_text())
        self.assertEqual(report["exception"]["message"], "fake CLI failure")


if __name__ == "__main__":
    unittest.main()
