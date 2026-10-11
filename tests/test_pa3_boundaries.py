"""Rejection before I/O and fresh-process forbidden-operation tripwires."""

import ast
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from safeshift.pa3 import artifacts, audit, evaluate, policy, runner, scoring, synthetic
from safeshift.pa3.__main__ import main
from tests.test_pa3_synthetic import BASE, settings

ROOT = Path(__file__).resolve().parents[1]


class PathTripwire:
    def __fspath__(self):
        raise AssertionError("PATH_ACCESSED_BEFORE_DENIAL")


class BoundaryTests(unittest.TestCase):
    def entrypoints(self, s):
        trap = PathTripwire()
        return [lambda: runner.run(trap, s), lambda: runner.manifest(s),
                lambda: audit.audit_run(trap, s), lambda: artifacts.create(trap, s),
                lambda: artifacts.location(trap, s), lambda: artifacts.write(trap, s, "manifest", {}),
                lambda: artifacts.read(trap, s, "manifest"), lambda: artifacts.exists(trap, s, "manifest"),
                lambda: artifacts.inventory(trap, s), lambda: artifacts.seal(trap, s), lambda: artifacts.verify(trap, s),
                lambda: synthetic.specimen(s, "normal"), lambda: synthetic.ground_truth(s),
                lambda: synthetic.generate(s, "normal"), lambda: scoring.raw_record(s, "normal"),
                lambda: scoring.check_raw(s, "normal", {}), lambda: scoring.score_raw(s, "normal", {}),
                lambda: scoring.pending(s, "normal"), lambda: evaluate.report(s, [], {})]

    def test_all_modes_denied_at_every_entrypoint_before_paths(self):
        for mode in ("train", "test", "dev", "train-dev", "train_dev", "holdout", "train-holdout",
                     "TRAIN", "TEST", "technical", "gpu", "real", "", None):
            s = {**settings(), "mode": mode}
            for i, call in enumerate(self.entrypoints(s)):
                with self.subTest(mode=mode, entry=i), self.assertRaises(PermissionError):
                    call()

    def test_dataset_models_receipts_and_injection_denied_everywhere(self):
        for key in ("dataset_path", "dataset_root", "dataset_locator", "image", "image_locator", "samples",
                    "snapshot", "model", "model_key", "model_revision", "scorer_factory", "tokenizer",
                    "reference_scores", "calibrate", "temperature", "threshold", "protect_level01",
                    "approval", "approval_sha256", "receipt", "source_kind", "pa3_role", "split"):
            s = {**settings(), key: "not-a-real-path"}
            for i, call in enumerate(self.entrypoints(s)):
                with self.subTest(key=key, entry=i), self.assertRaises(PermissionError):
                    call()

    def test_invalid_catalog_names_duplicate_ids_and_paths(self):
        for names in (["normal", "normal"], ["train"], ["test"], ["holdout"], ["data/raw/image.jpg"], []):
            with self.subTest(names=names), self.assertRaises(PermissionError):
                runner.run(PathTripwire(), {**settings(), "cases": names})
        for run_id in ("../test", "pa3-synthetic-../train", "test", "pa3-synthetic-x/holdout"):
            with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                runner.run(PathTripwire(), {**settings(), "run_id": run_id})

    def test_artifact_paths_are_not_data_locators(self):
        for name in ("../raw", "data/raw/InspecSafe-V1", "train", "D:/model", "000.raw/../../test"):
            with self.subTest(name=name), self.assertRaises(PermissionError):
                artifacts.read(PathTripwire(), settings(), name)

    def test_direct_scoring_rejects_non_catalog_trace(self):
        s = settings("normal")
        raw = scoring.raw_record(s, "normal")
        raw["trace"]["decoded_text"] = '{"safety_level":"Level04"}'
        with self.assertRaisesRegex(PermissionError, "SYNTHETIC_TRACE"):
            scoring.score_raw(s, "normal", raw)
        with self.assertRaisesRegex(PermissionError, "SYNTHETIC_TRACE"):
            artifacts.write(PathTripwire(), s, "000.raw", raw)

    def test_cli_rejects_all_real_modes_and_input_flags(self):
        valid = ["run", "--mode", "synthetic", "--run-id", "pa3-synthetic-unit", "--source-commit", BASE]
        variants = [valid[:2] + [mode] + valid[3:] for mode in
                    ("train", "test", "dev", "train-dev", "holdout", "technical", "gpu")]
        variants += [valid + [flag, "missing-path"] for flag in
                     ("--dataset-path", "--snapshot", "--model", "--settings", "--receipt", "--repo")]
        for argv in variants:
            for action in ("run", "audit"):
                with self.subTest(argv=argv, action=action), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as err:
                        main([action] + argv[1:])
                    self.assertEqual(err.exception.code, 2)

    def test_lifecycle_raw_durable_before_parser(self):
        from safeshift.protocol.p21_schema import parse_classification
        s = settings("normal")
        with tempfile.TemporaryDirectory() as repo:
            calls = []
            def observe(frame, event, arg):
                if event == "call" and frame.f_code is parse_classification.__code__:
                    saved = artifacts.read(repo, s, "000.raw")
                    self.assertEqual(saved["trace"]["decoded_text"], '{"safety_level":"Level03"}')
                    calls.append(True)
            prior = sys.getprofile()
            sys.setprofile(observe)
            try:
                runner.run(repo, s)
            finally:
                sys.setprofile(prior)
            self.assertTrue(calls)

    def test_actual_keyboard_interrupt_leaves_auditable_raw_and_stops(self):
        s = settings("anomaly", "normal")
        with tempfile.TemporaryDirectory() as repo:
            def interrupt(frame, event, arg):
                if event == "call" and frame.f_code is scoring.score_raw.__code__:
                    sys.setprofile(None)
                    raise KeyboardInterrupt("synthetic fault injection after raw persistence")
            prior = sys.getprofile()
            sys.setprofile(interrupt)
            try:
                with self.assertRaises(KeyboardInterrupt):
                    runner.run(repo, s)
            finally:
                sys.setprofile(prior)
            result = audit.audit_run(repo, s)
            self.assertEqual(result["evaluation"]["flow"], dict(planned=2, attempted=1, persisted=1, parsed=0, scored=0))
            self.assertEqual([r["status"] for r in result["results"]], ["UNPROCESSED", "NOT_ATTEMPTED"])
            self.assertTrue(result["sealed"])
            self.assertEqual(artifacts.read(repo, s, "failure")["reason"], "KeyboardInterrupt")

    def test_directory_alias_rejected_before_artifact_read(self):
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as outside:
            link = Path(repo) / "data"
            if sys.platform == "win32":
                # A junction needs no Windows symlink privilege; both targets are
                # empty test-owned temporary directories, never repository data.
                made = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), outside], capture_output=True)
                self.assertEqual(made.returncode, 0, made.stderr.decode(errors="replace"))
            else:
                link.symlink_to(outside, target_is_directory=True)
            try:
                with self.assertRaisesRegex(PermissionError, "ALIAS"):
                    artifacts.read(repo, settings(), "manifest")
                self.assertEqual(list(Path(outside).iterdir()), [])
            finally:
                if sys.platform == "win32":
                    link.rmdir()  # removes only the test junction, not its target
                else:
                    link.unlink()

    def test_pa3_has_no_forbidden_import_or_call(self):
        allowed_ls1 = {"safeshift.ls1.core", "safeshift.ls1.evaluate"}
        allowed_symbols = {"locate_decision", "score_decision", "validate_trace", "LEVELS", "auc", "anomaly_log_odds"}
        for path in (ROOT / "safeshift/pa3").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("safeshift.ls1"):
                    self.assertIn(node.module, allowed_ls1)
                    self.assertTrue({n.name for n in node.names} <= allowed_symbols)
                if isinstance(node, ast.Call):
                    name = getattr(node.func, "id", getattr(node.func, "attr", ""))
                    self.assertNotIn(name, {"reference_scores", "calibrate", "reference_images", "NativeScorer", "dataset_samples"})

    def test_fresh_process_no_ml_network_dataset_or_calibration(self):
        code = r'''
import sys, tempfile
def guard(event, args):
    if event == "import" and args[0].split(".")[0] in {"torch", "transformers", "tokenizers", "huggingface_hub", "PIL"}:
        raise AssertionError("MODEL_DEPENDENCY_IMPORTED")
    if event.startswith("socket."):
        raise AssertionError("NETWORK_ACCESS")
    if event == "open" and isinstance(args[0], (str, bytes)):
        name = str(args[0]).replace("\\", "/").lower()
        if any(x in name for x in ("/data/raw/", "/data/manifests/", "/snapshots/", ".safetensors", ".tar.gz")):
            raise AssertionError("REAL_INPUT_ACCESS")
sys.addaudithook(guard)
def profile(frame, event, arg):
    if event == "call" and frame.f_code.co_name in {"reference_scores", "calibrate", "reference_images", "dataset_samples"}:
        raise AssertionError("FORBIDDEN_CALL")
sys.setprofile(profile)
from safeshift.pa3.runner import run
from safeshift.pa3.audit import audit_run
from safeshift.pa3.policy import CASES
for case in CASES:
    with tempfile.TemporaryDirectory() as repo:
        s = dict(mode="synthetic", run_id="pa3-synthetic-process", source_commit="a"*40, cases=[case])
        run(repo, s)
        audit_run(repo, s)
assert not any(k in sys.modules for k in ("torch", "transformers", "safeshift.ls1.runtime", "safeshift.ls1.experiment"))
print("ALL_CATALOG_CASES_GUARDED_PASS")
'''
        env = dict(os.environ, PA3_ALLOW_REAL="1", LS1_APPROVED="1", PA3_MODE="train", CUDA_VISIBLE_DEVICES="0")
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ALL_CATALOG_CASES_GUARDED_PASS", result.stdout)

    def test_ls1_train_test_and_dataset_helpers_still_locked(self):
        from safeshift.ls1.experiment import authorize, dataset_samples
        for mode in ("train", "test"):
            s = dict(model_key="qwen2_5", mode=mode, run_id="blocked", source_commit=BASE,
                     approval={"approved": True}, approval_sha256="a" * 64)
            with self.subTest(mode=mode), self.assertRaisesRegex(PermissionError, "LS1_SPLIT_EXECUTION_LOCKED"):
                authorize(s, PathTripwire())
            with self.assertRaisesRegex(PermissionError, "LS1_SPLIT_EXECUTION_LOCKED"):
                dataset_samples(s)

    def test_protected_source_bytes_equal_exact_base(self):
        names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASE,
                                         "safeshift/ls1", "configs/frozen", "safeshift/protocol", "safeshift/runners"],
                                        cwd=ROOT, text=True).splitlines()
        for name in names:
            with self.subTest(name=name):
                original = subprocess.check_output(["git", "show", BASE + ":" + name], cwd=ROOT)
                current = subprocess.check_output(["git", "hash-object", "--path=" + name, name], cwd=ROOT)
                expected = subprocess.check_output(["git", "hash-object", "--stdin"], cwd=ROOT, input=original)
                self.assertEqual(current, expected)


if __name__ == "__main__":
    unittest.main()
