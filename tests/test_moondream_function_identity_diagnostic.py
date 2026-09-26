"""Fake/static identity observations only; never import pinned model modules."""

import ast
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from safeshift.runners import moondream_binding as binding
from scripts import w2_moondream_function_identity_diagnostic as diagnostic
from scripts.w2_moondream_load_diagnostic import redact

SOURCE = b'class MoondreamModel:\n def __init__(self):\n  raise AssertionError("construction forbidden")\n'
PREDICATES = ("is_exact_types_FunctionType", "globals_is_module_vars",
              "qualname_matches", "closure_is_none")


def fake_module():
    module = types.ModuleType("fake_moondream")
    exec(compile(SOURCE, "moondream.py", "exec", dont_inherit=True), vars(module))
    return module


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.module = fake_module()
        self.function = self.module.MoondreamModel.__init__

    def observe(self, function=None):
        return diagnostic.identity_metadata(
            self.function if function is None else function, self.module, repo=Path.cwd())

    def test_all_requested_fields_and_no_construction(self):
        result = self.observe()
        self.assertEqual(result, {
            "function_type_name": "function", "function_type_module": "builtins",
            "is_exact_types_FunctionType": True, "actual_qualname": "MoondreamModel.__init__",
            "expected_qualname": "MoondreamModel.__init__", "qualname_matches": True,
            "globals_is_module_vars": True, "closure_is_none": True, "closure_length": 0,
            "co_freevars": [], "function_module_name": "fake_moondream",
            "function_code_name": "__init__", "function_code_qualname": "MoondreamModel.__init__",
            "function_code_filename": "moondream.py",
            "function_code_filename_policy": "REPO_RELATIVE_OR_EXTERNAL_BASENAME",
            "class_dict_has_own_init": True, "class_dict_init_is_function": True,
        })

    def test_each_predicate_independently_and_original_guard_still_rejects(self):
        def factory():
            secret_cell = "DO_NOT_DUMP_CELL"
            def wrapped(self):
                return secret_cell
            return wrapped

        functions = {
            "globals_is_module_vars": types.FunctionType(self.function.__code__, {}),
            "qualname_matches": types.FunctionType(self.function.__code__, vars(self.module)),
            "closure_is_none": types.FunctionType(factory().__code__, vars(self.module),
                                                   closure=factory().__closure__),
        }
        for failed, function in functions.items():
            function.__qualname__ = "wrong" if failed == "qualname_matches" else diagnostic.EXPECTED_QUALNAME
            with self.subTest(failed=failed):
                result = self.observe(function)
                self.assertEqual({key: result[key] for key in PREDICATES},
                                 {key: key != failed for key in PREDICATES})
                with self.assertRaisesRegex(ValueError, "AUDITED_FUNCTION_IDENTITY_REQUIRED"):
                    binding.verify_function(function, self.module, "unused", "moondream.py",
                                            diagnostic.EXPECTED_QUALNAME)
                self.assertNotIn("DO_NOT_DUMP_CELL", json.dumps(result))
        result = self.observe(functions["closure_is_none"])
        self.assertEqual(result["closure_length"], 1)
        self.assertEqual(result["co_freevars"], ["secret_cell"])

    def test_nonfunction_type_false_other_predicates_independent(self):
        class Callable:
            def __call__(self):
                raise AssertionError("must not call")
        function = Callable()
        function.__globals__ = vars(self.module)
        function.__qualname__ = diagnostic.EXPECTED_QUALNAME
        function.__closure__ = None
        result = self.observe(function)
        self.assertEqual([result[key] for key in PREDICATES], [False, True, True, True])
        self.assertIsNone(result["function_code_name"])
        with patch.object(diagnostic, "verified_source", return_value=SOURCE):
            self.assertEqual(diagnostic.expected_code_metadata(function, "unused"),
                             {"expected_code_exists": True, "code_signature_matches": None})

    def test_missing_metadata_and_properties_are_not_invoked(self):
        class Callable:
            @property
            def __closure__(self):
                raise AssertionError("property forbidden")
            def __repr__(self):
                raise AssertionError("repr forbidden")
        result = self.observe(Callable())
        self.assertFalse(result["is_exact_types_FunctionType"])
        for key in ("globals_is_module_vars", "closure_is_none", "closure_length", "co_freevars"):
            self.assertIsNone(result[key])

    def test_class_ownership_and_staticmethod_descriptor_identity(self):
        parent = self.module.MoondreamModel
        self.module.MoondreamModel = type("MoondreamModel", (parent,), {})
        result = self.observe(self.module.MoondreamModel.__init__)
        self.assertFalse(result["class_dict_has_own_init"])
        self.assertFalse(result["class_dict_init_is_function"])
        self.module.MoondreamModel.__init__ = staticmethod(self.function)
        result = self.observe(self.module.MoondreamModel.__init__)
        self.assertTrue(result["class_dict_has_own_init"])
        self.assertFalse(result["class_dict_init_is_function"])

    def test_same_code_signature_as_unchanged_guard_and_mismatch(self):
        with patch.object(diagnostic, "verified_source", return_value=SOURCE), \
                patch.object(binding, "verified_source", return_value=SOURCE):
            binding.verify_function(self.function, self.module, "unused", "moondream.py",
                                    diagnostic.EXPECTED_QUALNAME)
            self.assertTrue(diagnostic.expected_code_metadata(self.function, "unused")["code_signature_matches"])
            self.function.__code__ = (lambda self: None).__code__
            self.assertFalse(diagnostic.expected_code_metadata(self.function, "unused")["code_signature_matches"])
            with self.assertRaisesRegex(ValueError, "AUDITED_BYTECODE_REQUIRED"):
                binding.verify_function(self.function, self.module, "unused", "moondream.py",
                                        diagnostic.EXPECTED_QUALNAME)

    def test_expected_code_absent_and_compile_does_not_execute_source(self):
        for source, exists in ((SOURCE + b'raise AssertionError("do not execute")\n', True),
                               (b"unrelated = 1\n", False)):
            with self.subTest(exists=exists), patch.object(diagnostic, "verified_source", return_value=source):
                result = diagnostic.expected_code_metadata(self.function, "unused")
                self.assertEqual(result["expected_code_exists"], exists)
                self.assertEqual(result["code_signature_matches"], True if exists else None)

    def test_code_filename_relative_or_external_basename_only(self):
        root = Path.cwd()
        for filename, expected in ((str(root / "data/processed/cache/moondream.py"),
                                    "data/processed/cache/moondream.py"),
                                   ("Z:/private/person/context.py", "<external>/context.py")):
            self.function.__code__ = self.function.__code__.replace(co_filename=filename)
            self.assertEqual(self.observe()["function_code_filename"], expected)

    def test_old_redaction_false_positive_characterization_without_fix(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(redact("hf_moondream.py"), "[REDACTED].py")
            self.assertEqual(redact("cache/hf_moondream.py"), "cache/[REDACTED].py")
            self.assertEqual(redact("hf_utils.py"), "[REDACTED].py")
            self.assertEqual(redact("hf_model_utils.py"), "hf_model_utils.py")
            self.assertEqual(redact("moondream.py"), "moondream.py")
            self.assertEqual(redact("hf_exampletoken"), "[REDACTED]")


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.repo = Path(self.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        self.module = fake_module()
        self.order = []
        self.git = self.stack.enter_context(patch.object(
            diagnostic.subprocess, "check_output", side_effect=self.git_result))
        self.verify = self.stack.enter_context(patch.object(diagnostic, "verify_snapshot", side_effect=self.verify_result))
        self.offline = self.stack.enter_context(patch.object(diagnostic, "deny_network_permanently",
                                                            side_effect=lambda: self.order.append("offline")))
        self.loader = self.stack.enter_context(patch.object(diagnostic, "load_verified_modules",
                                                           side_effect=self.load_result))
        self.source = self.stack.enter_context(patch.object(diagnostic, "verified_source", return_value=SOURCE))
        self.stack.enter_context(patch.object(diagnostic, "version", return_value="fake-version"))
        # Any accidental runtime entry fails the harness, including transitive imports.
        from safeshift.runners import moondream2, moondream_precision
        from scripts import w2_moondream_load_diagnostic as old
        self.forbidden = []
        for owner, name in ((moondream2, "Moondream2Runner"), (moondream2, "NativeBackend"),
                            (binding, "starmie_redirect"), (binding, "VisionBinding"),
                            (moondream_precision, "post_normalization_fp16_bridge"),
                            (old, "run_diagnostic")):
            self.forbidden.append(self.stack.enter_context(patch.object(
                owner, name, side_effect=AssertionError("forbidden runtime entry"))))

    def git_result(self, command, **kwargs):
        self.order.append("git")
        return "a" * 40 if command[1] == "rev-parse" else ""

    def verify_result(self, path, repo_id, revision):
        self.order.append("verify")
        self.assertEqual(path, self.repo / "data/processed/cache/models--vikhyatk--moondream2/snapshots" / diagnostic.REVISION)
        self.assertEqual((repo_id, revision), (diagnostic.MODEL_ID, diagnostic.REVISION))
        return {"local_bytes_verified": True, "manifest_sha256": "fake"}

    def load_result(self, path):
        self.order.append("import")
        return types.SimpleNamespace(), {"moondream": self.module}

    def run_case(self, run_id="fake-test", cache_dir="data/processed/cache"):
        result = diagnostic.run_diagnostic(repo=self.repo, cache_dir=cache_dir,
                                           run_id=run_id, expected_commit="a" * 40)
        self.assertEqual(result, json.loads((self.repo / result["artifact_path"]).read_text()))
        for forbidden in self.forbidden:
            forbidden.assert_not_called()
        return result

    def test_order_provenance_and_success_even_with_false_predicates(self):
        self.module.MoondreamModel.__init__.__qualname__ = "not_expected"
        result = self.run_case()
        self.assertEqual(self.order, ["git", "git", "verify", "offline", "import"])
        self.assertEqual(result["status"], "IDENTITY_OBSERVED")
        self.assertFalse(result["identity"]["qualname_matches"])
        self.assertTrue(result["code_signature_matches"])
        self.assertEqual(result["execution_commit"], "a" * 40)
        self.assertEqual(result["software_versions"]["torch"], "fake-version")
        self.loader.assert_called_once_with(self.verify.call_args.args[0])
        self.source.assert_called_once_with(self.verify.call_args.args[0], "moondream.py")

    def test_wrong_commit_and_dirty_tracked_or_untracked_checkout_fail_before_snapshot(self):
        for index, responses in enumerate((["b" * 40], ["a" * 40, " M code.py"],
                                            ["a" * 40, "?? injected.py"])):
            with self.subTest(index=index):
                self.git.side_effect = responses
                result = self.run_case(str(index))
                self.assertEqual(result["exception"]["stage"], "provenance")
        self.verify.assert_not_called()
        self.offline.assert_not_called()
        self.loader.assert_not_called()

    def test_missing_or_wrong_snapshot_stops_without_offline_import(self):
        for index, error in enumerate((FileNotFoundError("absent"), ValueError("PINNED_ARTIFACT_MISMATCH"))):
            self.verify.side_effect = error
            result = self.run_case(str(index))
            self.assertEqual(result["exception"]["stage"], "local_snapshot")
        self.offline.assert_not_called()
        self.loader.assert_not_called()

    def test_import_failure_never_observes_or_compiles(self):
        self.loader.side_effect = RuntimeError("DO_NOT_DUMP_EXCEPTION")
        result = self.run_case()
        self.assertEqual(result["exception"], {"stage": "verified_module_import", "type": "RuntimeError"})
        self.assertIsNone(result["identity"])
        self.source.assert_not_called()
        self.assertNotIn("DO_NOT_DUMP_EXCEPTION", json.dumps(result))

    def test_compile_failure_preserves_completed_identity_observation(self):
        self.source.side_effect = ValueError("REMOTE_SOURCE_HASH_MISMATCH")
        result = self.run_case()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["exception"]["stage"], "expected_code_comparison")
        self.assertTrue(result["identity"]["is_exact_types_FunctionType"])
        self.assertIsNone(result["expected_code_exists"])

    def test_no_globals_cell_values_credentials_or_absolute_code_path_serialized(self):
        function = self.module.MoondreamModel.__init__
        function.__globals__["private"] = "DO_NOT_DUMP_GLOBALS"
        function.__module__ = "hf_exampletoken"
        result = self.run_case()
        text = json.dumps(result)
        for forbidden in ("DO_NOT_DUMP_GLOBALS", "hf_exampletoken", str(self.repo)):
            self.assertNotIn(forbidden, text)
        self.assertEqual(result["identity"]["function_module_name"], "[REDACTED]")

    def test_separate_namespace_preserves_existing_smoke_and_diagnostic_artifacts(self):
        for existing in (False, True):
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as folder:
                self.repo = Path(folder).resolve()
                roots = [self.repo / "data/processed" / name for name in
                         ("moondream_t4_smoke", "moondream_load_diagnostic")]
                if existing:
                    for root in roots:
                        root.mkdir(parents=True)
                        (root / "report.json").write_bytes(b"original FAIL evidence")
                original_open = Path.open
                def guarded_open(path, *args, **kwargs):
                    self.assertFalse(any(path.is_relative_to(root) for root in roots))
                    self.assertNotEqual(path.name, "ATTEMPT.json")
                    return original_open(path, *args, **kwargs)
                with patch.object(Path, "open", guarded_open):
                    self.run_case()
                for root in roots:
                    if existing:
                        self.assertEqual((root / "report.json").read_bytes(), b"original FAIL evidence")
                    else:
                        self.assertFalse(root.exists())

    def test_never_overwrite_or_import_twice_on_run_id_reuse(self):
        result = self.run_case()
        before = (self.repo / result["artifact_path"]).read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_case()
        self.loader.assert_called_once()
        self.assertEqual((self.repo / result["artifact_path"]).read_bytes(), before)

    def test_paths_rejected(self):
        for run_id in ("../escape", "a/b", "a\\b", "..", "C:escape"):
            with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                self.run_case(run_id)
        result = self.run_case(cache_dir="../cache")
        self.assertEqual(result["exception"]["stage"], "local_snapshot")
        self.loader.assert_not_called()

    def test_cli_explicit_opt_in_and_exit_status(self):
        with patch.object(diagnostic, "ROOT", self.repo), patch("builtins.print"):
            for index, fail in enumerate((False, True)):
                if fail:
                    self.verify.side_effect = ValueError("missing")
                code = diagnostic.main(["--execute-identity-diagnostic", "--expected-commit", "a" * 40,
                                        "--cache-dir", "data/processed/cache", "--run-id", str(index)])
                self.assertEqual(code, int(fail))
            with self.assertRaises(SystemExit), patch("sys.stderr"):
                diagnostic.main([])

    def test_static_no_runtime_download_gpu_inference_or_guard_calls(self):
        tree = ast.parse(Path(diagnostic.__file__).read_text())
        forbidden = {"MoondreamModel", "Tokenizer", "HfMoondream", "Moondream2Runner", "NativeBackend",
                     "initialize", "load", "from_pretrained", "to", "cuda", "query", "detect",
                     "snapshot_download", "hf_hub_download", "run_smoke", "run_gate",
                     "starmie_redirect", "VisionBinding", "post_normalization_fp16_bridge", "verify_function"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else (
                    node.func.id if isinstance(node.func, ast.Name) else None)
                self.assertNotIn(name, forbidden)
        self.assertNotIn("cell_contents", Path(diagnostic.__file__).read_text())


if __name__ == "__main__":
    unittest.main()
