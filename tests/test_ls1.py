"""Synthetic-only CPU unit/integration tests. Real T1 opt-in; no model load."""

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.ls1 import core, artifacts, tokenizer, runtime, experiment, evaluate, kaggle
from safeshift.ls1.audit import audit_run

ROOT = Path(__file__).resolve().parents[1]
SPLIT_LOCK_MESSAGE = "LS1_SPLIT_EXECUTION_LOCKED_PENDING_DEC_LS1_001"


class CharTokenizer:
    def encode(self, text, add_special_tokens=False):
        return [ord(c) for c in text]

    def decode(self, ids, skip_special_tokens=False, clean_up_tokenization_spaces=False):
        return "".join(chr(i) for i in ids if not skip_special_tokens or i != 999)


TOK = CharTokenizer()
TEXT = '{"safety_level":"Level03"}'


def fake_raw(text=TEXT, label_logits=(0, 1, 4, 0), prefix=()):
    ids = [51] if prefix else TOK.encode(text) + [999]
    steps = []
    mapping = core.candidates(TOK, TEXT)
    for step, token in enumerate(ids):
        vector = [-100.0] * 1000
        vector[token] = 20.0
        if prefix or step == mapping["step"]:
            for i, value in zip(mapping["token_ids"], label_logits):
                vector[i] = value
        summary = runtime.summarize_vector(vector, mapping["token_ids"], token)
        steps.append({"step": step, "generated_token": token, "raw": summary, "processed": deepcopy(summary)})
    return {"continuation_ids": ids, "steps": steps, "decoded_text": text,
            "forced_assistant_prefix_ids": list(prefix)}


class FakeScorer:
    hardware = {"kind": "FAKE_CPU_TEST_ONLY"}
    software = {"kind": "FAKE_CPU_TEST_ONLY"}
    snapshot_receipt = {"kind": "FAKE_CPU_TEST_ONLY"}
    config = SimpleNamespace(eos_token_id=999)
    calls = 0

    def __init__(self, *args, **kwargs):
        pass

    def generate(self, image, prefix_ids=()):
        type(self).calls += 1
        return fake_raw(label_logits=(0, 1, 8, 0) if prefix_ids else (0, 1, 4, 0), prefix=prefix_ids)


def fake_t1(*args, **kwargs):
    return {"status": "PASS", "candidate_token_ids": [49, 50, 51, 52], "fixture": "FAKE_NOT_T1_EVIDENCE"}, TOK


class ProbabilityTests(unittest.TestCase):
    def test_uniform(self):
        self.assertEqual(core.distribution([0] * 4)["probabilities"], [.25] * 4)

    def test_translation_invariance(self):
        self.assertEqual(core.log_softmax([10000, 9999, 9998, 9997]), core.log_softmax([0, -1, -2, -3]))

    def test_extreme_finite(self):
        self.assertEqual(core.distribution([1e300, -1e300, 0, 1])["probabilities"], [1., 0., 0., 0.])

    def test_analytic(self):
        self.assertEqual(core.distribution([math.log(x) for x in (1, 2, 3, 4)])["prediction"], "Level04")
        for observed, expected in zip(core.distribution([math.log(x) for x in (1, 2, 3, 4)])["probabilities"], (.1, .2, .3, .4)):
            self.assertAlmostEqual(observed, expected)

    def test_invalid_numbers(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                core.log_softmax([value, 0, 0, 0])

    def test_wrong_number_of_classes(self):
        with self.assertRaises(ValueError):
            core.log_softmax([1, 2, 3])


class TokenTests(unittest.TestCase):
    def test_all_probe_variants(self):
        result = tokenizer.probe(TOK)
        self.assertEqual(len(result["checks"]), 28)
        self.assertEqual(result["candidate_token_ids"], [49, 50, 51, 52])

    def test_model_specific_ids(self):
        class Shifted(CharTokenizer):
            def encode(self, text, add_special_tokens=False):
                return [i + 10 for i in super().encode(text)]
            def decode(self, ids, **kwargs):
                return super().decode([i - 10 for i in ids], **kwargs)
        self.assertEqual(core.candidates(Shifted(), TEXT)["token_ids"], [59, 60, 61, 62])

    def test_eos_alignment(self):
        self.assertEqual(core.locate_decision(TOK, TEXT, TOK.encode(TEXT) + [999], [999])["generated_label"], "Level03")

    def test_wrong_token_position(self):
        with self.assertRaises(ValueError):
            core.locate_decision(TOK, TEXT, [32] + TOK.encode(TEXT), [])

    def test_internal_special_token(self):
        with self.assertRaises(ValueError):
            core.locate_decision(TOK, TEXT, TOK.encode(TEXT)[:3] + [999] + TOK.encode(TEXT)[3:], [999])

    def test_invalid_is_not_rescued(self):
        for text in ('Level03', TEXT + ' commentary', '{"safety_level":"Level05"}',
                     '{"safety_level":"Level03","extra":1}', '{"safety_level":"Level03","safety_level":"Level04"}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                core.candidates(TOK, text)

    def test_multitoken_branch_rejected(self):
        class Multi(CharTokenizer):
            def encode(self, text, add_special_tokens=False):
                return [i for c in text for i in (ord(c), ord(c))]
        with self.assertRaises(ValueError):
            core.candidates(Multi(), TEXT)

    def test_escaped_label_rejected(self):
        with self.assertRaises(ValueError):
            core.candidates(TOK, '{"safety_level":"Level0\\u0033"}')

    def test_missing_snapshot_blocked(self):
        for model in tokenizer.MODELS:
            result, tok = tokenizer.t1(model)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIsNone(tok)
            self.assertFalse(result["weights_loaded"])

    def test_wrong_revision(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            tokenizer.verify_snapshot("qwen2_5", d, tokenizer_only=True)

    def test_tampered_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / tokenizer.MODELS["qwen2_5"][1]
            root.mkdir()
            (root / "chat_template.json").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "CHECKSUM"):
                tokenizer.verify_snapshot("qwen2_5", root, tokenizer_only=True)

    def test_missing_file_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / tokenizer.MODELS["internvl3"][1]
            root.mkdir()
            result, _ = tokenizer.t1("internvl3", root)
            self.assertEqual(result["status"], "BLOCKED")


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.raw = fake_raw()
        self.mapping = core.locate_decision(TOK, TEXT, self.raw["continuation_ids"], [999])

    def test_raw_processed_are_distinct(self):
        row = self.raw["steps"][self.mapping["step"]]
        row["raw"]["candidate_values"]["52"] = 10.0
        row["raw"]["logsumexp"] = 11.0
        row["raw"]["argmax_id"] = 52
        row["raw"]["argmax_value"] = 10.0
        result = core.score_decision(self.raw, self.mapping)
        self.assertEqual(result["prediction"], "Level04")
        self.assertEqual(result["generated_label"], "Level03")
        self.assertFalse(result["raw_and_processed_label_scores_equal"])

    def test_full_vocab_mass(self):
        result = core.score_decision(self.raw, self.mapping)
        self.assertLessEqual(result["four_label_probability_mass"], 1)
        self.assertAlmostEqual(sum(result["probabilities"]), 1)

    def test_nan_inf_each_step(self):
        for key in ("nan", "positive_inf", "negative_inf"):
            with self.subTest(key=key):
                value = deepcopy(self.raw)
                value["steps"][0]["raw"]["nonfinite"][key] = 1
                with self.assertRaisesRegex(ValueError, "RAW_NAN_OR_INF"):
                    core.score_decision(value, self.mapping)

    def test_processed_negative_inf_allowed(self):
        self.raw["steps"][0]["processed"]["nonfinite"]["negative_inf"] = 10
        self.assertEqual(core.score_decision(self.raw, self.mapping)["generated_label"], "Level03")

    def test_processed_bad(self):
        self.raw["steps"][0]["processed"]["nonfinite"]["positive_inf"] = 1
        with self.assertRaises(ValueError):
            core.score_decision(self.raw, self.mapping)

    def test_wrong_generated_processed_argmax(self):
        self.raw["steps"][0]["processed"]["argmax_id"] += 1
        with self.assertRaisesRegex(ValueError, "ARGMAX"):
            core.score_decision(self.raw, self.mapping)

    def test_missing_token(self):
        del self.raw["steps"][self.mapping["step"]]["raw"]["candidate_values"]["52"]
        with self.assertRaisesRegex(ValueError, "MISSING_LABEL_TOKEN"):
            core.score_decision(self.raw, self.mapping)

    def test_missing_step(self):
        self.raw["steps"].pop()
        with self.assertRaises(ValueError):
            core.score_decision(self.raw, self.mapping)

    def test_native_capture_prefix(self):
        class Rows:
            def tolist(self):
                return [[1, 2, 3]]
        output = SimpleNamespace(sequences=Rows(), logits=[[0, 0, 0, 1]], scores=[[0, 0, 0, 1]])
        result = runtime.capture_output(output, [1, 2], [3], TOK, runtime.summarize_vector)
        self.assertEqual(result["continuation_ids"], [3])
        with self.assertRaises(ValueError):
            runtime.capture_output(output, [2, 1], [3], TOK, runtime.summarize_vector)

    def test_processed_scores_cannot_replace_missing_raw(self):
        class Rows:
            def tolist(self):
                return [[1, 2]]
        with self.assertRaises(ValueError):
            runtime.capture_output(SimpleNamespace(sequences=Rows(), logits=[], scores=[[1, 2, 3]]),
                                   [1], [2], TOK, runtime.summarize_vector)


class CalibrationTests(unittest.TestCase):
    def test_reference_exact_pixels(self):
        images = core.reference_images()
        try:
            for name, value in core.REFERENCE_SPEC:
                self.assertEqual(images[name].size, (448, 448))
                self.assertEqual(images[name].mode, "RGB")
                self.assertEqual(images[name].getextrema(), ((value, value),) * 3)
        finally:
            for image in images.values():
                image.close()

    def test_uniform_prior_no_change(self):
        result = core.calibrate([1, 2, 3, 4], {name: [0]*4 for name, _ in core.REFERENCE_SPEC})
        for a, b in zip(result["calibrated"]["probabilities"], result["uncalibrated"]["probabilities"]):
            self.assertAlmostEqual(a, b)

    def test_fixed_geometric_prior(self):
        refs = {name: [0, 0, 8, 0] for name, _ in core.REFERENCE_SPEC}
        result = core.calibrate([0, 0, 4, 1], refs)
        self.assertEqual(result["uncalibrated"]["prediction"], "Level03")
        self.assertEqual(result["calibrated"]["prediction"], "Level04")
        expected = core.distribution([0, 0, -4, 1])["probabilities"]
        for a, b in zip(result["calibrated"]["probabilities"], expected):
            self.assertAlmostEqual(a, b)

    def test_reference_missing_or_nonfinite(self):
        with self.assertRaises(ValueError):
            core.calibrate([0]*4, {"gray": [0]*4})
        with self.assertRaises(ValueError):
            core.calibrate([0]*4, {name: [math.nan]*4 for name, _ in core.REFERENCE_SPEC})

    def test_guard_preserves_only_original_level01(self):
        refs = {name: [8, 0, 0, 0] for name, _ in core.REFERENCE_SPEC}
        before = core.calibrate([4, 0, 0, 1], refs)
        protected = core.calibrate([4, 0, 0, 1], refs, protect_level01=True)
        self.assertEqual(before["calibrated"]["prediction"], "Level04")
        self.assertEqual(protected["calibrated"]["prediction"], "Level01")
        self.assertTrue(protected["calibrated"]["level01_guard_applied"])
        self.assertEqual(before["calibrated"]["probabilities"], protected["calibrated"]["probabilities"])
        missed = core.calibrate([0, 4, 0, 1], {name: [0, 8, 0, 0] for name, _ in core.REFERENCE_SPEC}, protect_level01=True)
        self.assertEqual(missed["calibrated"]["prediction"], "Level04")
        self.assertFalse(missed["calibrated"]["level01_guard_applied"])


class EvaluationTests(unittest.TestCase):
    def test_auc_ranking_survives_probability_saturation(self):
        results = []
        for sid, values in (("anomaly", [-800, -900, -1000, 0]), ("normal", [-900, -1000, -1100, 0])):
            modes = core.calibrate(values, {name: [0]*4 for name, _ in core.REFERENCE_SPEC})
            self.assertEqual(modes["uncalibrated"]["probabilities"][3], 1)
            results.append({"sample_id": sid, "status": "SUCCESS", "modes": modes, "score": {"generated_label": "Level04"}})
        result = evaluate.report(results, {"anomaly": "Level01", "normal": "Level04"})
        self.assertEqual(result["modes"]["uncalibrated"]["auroc"]["anomaly_vs_normal"], 1)

    def test_auc_ties_and_absence(self):
        self.assertEqual(evaluate.auc([False, True], [0, 1]), 1)
        self.assertEqual(evaluate.auc([False, True], [1, 0]), 0)
        self.assertEqual(evaluate.auc([False, True], [1, 1]), .5)
        self.assertIsNone(evaluate.auc([True], [1]))

    def test_metrics_invalid_and_transitions(self):
        results, gt = [], {}
        for i, level in enumerate(core.LEVELS):
            sid = str(i)
            gt[sid] = level
            values = [-2]*4
            values[i] = 4
            result = core.calibrate(values, {name: [0]*4 for name, _ in core.REFERENCE_SPEC})
            results.append({"sample_id": sid, "status": "SUCCESS", "modes": result, "score": {"generated_label": level}})
        results[0] = {"sample_id": "0", "status": "INVALID", "modes": None}
        result = evaluate.report(results, gt)
        before = result["modes"]["uncalibrated"]
        self.assertEqual(before["accuracy"]["value"], .75)
        self.assertEqual(before["balanced_accuracy"], .75)
        self.assertEqual(before["macro_f1"], .75)
        self.assertEqual(before["confusion_matrix"]["Level01"]["INVALID"], 1)
        self.assertEqual(before["anomaly_non_detection_rate_failure_aware"]["value"], 1/3)
        self.assertEqual(before["auroc"]["excluded_invalid_n"], 1)
        self.assertIsNone(before["auroc"]["ovr"]["Level01"])
        self.assertEqual(before["anomaly_fnr_parse_conditional"]["denominator"], 2)
        results[1]["modes"]["calibrated"]["prediction"] = "Level04"
        changed = evaluate.report(results, gt)
        self.assertEqual(changed["transitions_to_level04"]["Level02"]["true_anomaly_n"], 1)

    def test_missing_classes_undefined(self):
        metrics = evaluate.report([{"sample_id": "a", "status": "INVALID", "modes": None}], {"a": "Level04"})
        self.assertIsNone(metrics["modes"]["uncalibrated"]["balanced_accuracy"])
        self.assertIsNone(metrics["modes"]["uncalibrated"]["anomaly_fnr_parse_conditional"]["value"])

    def test_exact_join(self):
        with self.assertRaises(ValueError):
            evaluate.report([], {"a": "Level01"})


class ArtifactTests(unittest.TestCase):
    def test_exclusive_write_and_reread(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "raw.json"
            receipt = artifacts.write_json(path, {"test": 1})
            self.assertEqual(artifacts.read_verified(path, receipt), {"test": 1})
            with self.assertRaises(FileExistsError):
                artifacts.write_json(path, {"test": 2})
            path.write_text("{}")
            with self.assertRaises(ValueError):
                artifacts.read_verified(path, receipt)

    def test_inventory_missing_added_tampered(self):
        for mutation in ("missing", "added", "tampered"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                artifacts.write_json(root / "value.json", {})
                artifacts.seal(root)
                if mutation == "missing":
                    (root / "value.json").unlink()
                elif mutation == "added":
                    (root / "unexpected.json").write_text("{}")
                else:
                    (root / "value.json").write_text("tampered")
                with self.assertRaises(ValueError):
                    artifacts.verify_run(root)

    def test_nonfinite_never_json_nan(self):
        with self.assertRaises(ValueError):
            artifacts.json_bytes({"x": math.nan})
        self.assertEqual(runtime.json_number(-math.inf), "-Inf")


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        for name in (experiment.METHOD_PATH, "prompts/p2_classification_c1_v1.txt"):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        self.settings = {"model_key": "qwen2_5", "run_id": "unit-test", "mode": "technical",
                         "source_commit": "a"*40, "snapshot": "fake"}
        FakeScorer.calls = 0

    def tearDown(self):
        self.temp.cleanup()

    def run_fake(self, factory=FakeScorer):
        return experiment.run(self.repo, self.settings, scorer_factory=factory, tokenizer_check=fake_t1)

    def test_end_to_end_and_cpu_recomputation(self):
        # Technical mode ignores research receipt/data settings and uses only drawings.
        self.settings.update(approval_path="DO_NOT_READ", approval_sha256="a"*64,
                             dataset_root="DO_NOT_READ", manifest_path="DO_NOT_READ")
        with patch.object(experiment, "dataset_samples", side_effect=AssertionError("DATA_READ")) as dataset:
            root = self.run_fake()
        dataset.assert_not_called()
        self.assertEqual(FakeScorer.calls, 7)  # 4 samples + three refs shared for identical prefix
        self.assertEqual(audit_run(root)["status"], "PASS")
        results = json.loads((root / "results.json").read_text())
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0]["score"]["generated_label"], "Level03")
        self.assertFalse((root / "evaluation.json").exists())
        cohort = json.loads((root / "cohort.json").read_text())
        self.assertEqual(cohort["source_kind"], "SYNTHETIC")
        self.assertTrue(all(row["sample_id"].startswith("ls1-synthetic-") for row in cohort["rows"]))
        manifest = json.loads((root / "run_manifest.json").read_text())
        self.assertFalse(manifest["protect_level01"])
        self.assertNotIn("approval", manifest)
        self.assertNotIn("approval_sha256", manifest)

    def test_no_retry_or_overwrite(self):
        self.run_fake()
        with self.assertRaises(FileExistsError):
            self.run_fake()

    def test_train_and_test_gate_before_reads(self):
        for model in tokenizer.MODELS:
            for mode in ("train", "test"):
                for guard in (False, True):
                    self.settings.update(model_key=model, mode=mode, protect_level01=guard)
                    with self.subTest(model=model, mode=mode, guard=guard), \
                         patch.object(experiment, "dataset_samples", side_effect=AssertionError("DATA_READ")) as dataset, \
                         patch.object(Path, "read_bytes", side_effect=AssertionError("FILE_READ")) as read, \
                         patch.object(experiment, "digest", side_effect=AssertionError("CHECKSUM_READ")) as digest, \
                         patch.object(tokenizer, "t1", side_effect=AssertionError("TOKENIZER_LOAD")) as check, \
                         patch.object(runtime, "NativeScorer", side_effect=AssertionError("MODEL_LOAD")) as model_load:
                        with self.assertRaises(PermissionError) as error:
                            experiment.run(self.repo, self.settings, tokenizer_check=check)
                        self.assertEqual(error.exception.args, (SPLIT_LOCK_MESSAGE,))
                        for operation in (dataset, read, digest, check, model_load):
                            operation.assert_not_called()
                    self.assertFalse((self.repo / "data").exists())

    def test_direct_dataset_helper_is_locked_without_reads(self):
        for mode in ("train", "test"):
            with self.subTest(mode=mode), \
                 patch("safeshift.data.p2_execution.verify_dataset", side_effect=AssertionError("DATA_READ")) as verify, \
                 patch.object(Path, "read_bytes", side_effect=AssertionError("FILE_READ")) as read:
                with self.assertRaises(PermissionError) as error:
                    experiment.dataset_samples({"mode": mode})
                self.assertEqual(error.exception.args, (SPLIT_LOCK_MESSAGE,))
                verify.assert_not_called()
                read.assert_not_called()

    def test_authorization_validation_is_preserved(self):
        for field, value, message in (
            ("model_key", "unknown", "SUPPORTED_LS1_MODE_REQUIRED"),
            ("mode", "unknown", "SUPPORTED_LS1_MODE_REQUIRED"),
            ("run_id", "../unsafe", "SAFE_UNIQUE_RUN_ID_REQUIRED"),
            ("source_commit", "latest", "EXACT_SOURCE_COMMIT_REQUIRED"),
            ("protect_level01", "true", "BOOLEAN_GUARD_REQUIRED"),
            ("protect_level01", True, "TECHNICAL_MODE_USES_DEFAULT_NO_GUARD"),
        ):
            settings = {**self.settings, field: value}
            with self.subTest(field=field, value=value), self.assertRaises(ValueError) as error:
                experiment.authorize(settings, self.repo)
            self.assertEqual(error.exception.args, (message,))
        self.assertIsNone(experiment.authorize(self.settings, self.repo))

    def test_t1_blocked_leaves_sealed_failure_no_model(self):
        with self.assertRaises(RuntimeError):
            experiment.run(self.repo, self.settings, scorer_factory=lambda *a, **k: self.fail("MODEL_LOAD"),
                           tokenizer_check=lambda *a, **k: ({"status": "BLOCKED"}, None))
        root = self.repo / "data/processed/ls1/runs/unit-test"
        artifacts.verify_run(root)
        self.assertTrue((root / "run_failure.json").is_file())

    def test_invalid_no_scoring_or_refs(self):
        class Invalid(FakeScorer):
            def generate(self, *args, **kwargs):
                value = fake_raw()
                value["decoded_text"] = "Level03"
                return value
        root = self.run_fake(Invalid)
        result = json.loads((root / "results.json").read_text())
        self.assertTrue(all(row["status"] == "INVALID" and row["modes"] is None for row in result))
        self.assertFalse((root / "references").exists())
        self.assertEqual(audit_run(root)["status"], "PASS")

    def test_safe_stop_bad_alignment_raw_retained(self):
        class Wrong(FakeScorer):
            def generate(self, *args, **kwargs):
                value = fake_raw()
                value["continuation_ids"][0] = 1
                return value
        with self.assertRaises(RuntimeError):
            self.run_fake(Wrong)
        root = self.repo / "data/processed/ls1/runs/unit-test"
        self.assertEqual(len(list(root.rglob("response.raw.json"))), 1)
        artifacts.verify_run(root)
        with self.assertRaises(FileExistsError):
            self.run_fake(Wrong)

    def test_invalid_with_nonfinite_stops_after_raw(self):
        class Nonfinite(FakeScorer):
            def generate(self, *args, **kwargs):
                raw = fake_raw()
                raw["decoded_text"] = "INVALID"
                raw["steps"][0]["raw"]["nonfinite"]["nan"] = 1
                return raw
        with self.assertRaises(RuntimeError):
            self.run_fake(Nonfinite)
        root = self.repo / "data/processed/ls1/runs/unit-test"
        self.assertEqual(len(list(root.rglob("response.raw.json"))), 1)
        artifacts.verify_run(root)

    def test_storage_failure_prevents_parse(self):
        real_write = artifacts.write_new
        def broken(path, raw):
            if Path(path).name == "response.raw.json":
                raise OSError("SYNTHETIC_STORAGE_FAILURE")
            return real_write(path, raw)
        with patch.object(artifacts, "write_new", broken), \
             patch.object(experiment, "parse_classification", side_effect=AssertionError("PARSE_BEFORE_STORAGE")), \
             self.assertRaises(OSError):
            self.run_fake()
        artifacts.verify_run(self.repo / "data/processed/ls1/runs/unit-test")

    def test_self_created_matching_approval_cannot_unlock_either_split(self):
        path = self.repo / "approval.json"
        for model in tokenizer.MODELS:
            for mode in ("train", "test"):
                for guard in (False, True):
                    self.settings.update(model_key=model, mode=mode, protect_level01=guard,
                                         approval_path=str(path))
                    receipt = {"schema": "ls1-research-lead-approval-v1", "status": "APPROVED",
                        "approved_by": "Research Lead", "protocol": "LS1", "run_id": self.settings["run_id"],
                        "mode": mode, "source_commit": self.settings["source_commit"], "model_key": model,
                        "model_revision": tokenizer.MODELS[model][1], "prompt_sha256": experiment.PROMPT_SHA256,
                        "method_sha256": experiment.method_hash(self.repo),
                        "source_manifest_sha256": experiment.MANIFEST_SHA, "dataset_fingerprint": experiment.FINGERPRINT,
                        "protect_level01": guard, "decision_reference": "SYNTHETIC_SELF_CREATED_NOT_AUTHORITY"}
                    raw = artifacts.json_bytes(receipt)
                    path.write_bytes(raw)
                    self.settings["approval_sha256"] = artifacts.digest(path)
                    self.assertEqual(self.settings["approval_sha256"], hashlib.sha256(raw).hexdigest())
                    with self.subTest(model=model, mode=mode, guard=guard), \
                         patch.object(Path, "read_bytes", side_effect=AssertionError("APPROVAL_OR_DATA_READ")) as read, \
                         patch.object(experiment, "digest", side_effect=AssertionError("APPROVAL_SHA_READ")) as digest, \
                         patch.object(experiment, "dataset_samples", side_effect=AssertionError("DATA_READ")) as dataset, \
                         patch.object(tokenizer, "t1", side_effect=AssertionError("TOKENIZER_LOAD")) as check, \
                         patch.object(runtime, "NativeScorer", side_effect=AssertionError("MODEL_LOAD")) as model_load:
                        for action in (lambda: experiment.authorize(self.settings, self.repo),
                                       lambda: experiment.run(self.repo, self.settings, tokenizer_check=check)):
                            with self.assertRaises(PermissionError) as error:
                                action()
                            self.assertEqual(error.exception.args, (SPLIT_LOCK_MESSAGE,))
                        for operation in (read, digest, dataset, check, model_load):
                            operation.assert_not_called()
                    self.assertFalse((self.repo / "data").exists())


class KaggleTests(unittest.TestCase):
    def test_runtime_inventory_verified_before_execution(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "runtime"
            source.mkdir()
            (source / "runtime.tar").write_bytes(b"SYNTHETIC_NOT_REAL_RUNTIME")
            receipt = Path(d) / "ls1_runtime_inventory.json"
            sha = kaggle.inventory_runtime(source, receipt)
            self.assertEqual(len(kaggle.verify_runtime_input(source, receipt, sha)["files"]), 1)
            with self.assertRaises(ValueError):
                kaggle.verify_runtime_input(source, receipt, "a"*64)
            (source / "runtime.tar").write_bytes(b"modified")
            with self.assertRaises(ValueError):
                kaggle.verify_runtime_input(source, receipt, sha)

    def test_inventory_receipt_cannot_change_input(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)
            (source / "runtime.tar").write_bytes(b"SYNTHETIC")
            with self.assertRaises(ValueError):
                kaggle.inventory_runtime(source, source / "ls1_runtime_inventory.json")

    def test_launch_once_and_sealed_failure_package(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            repo, inputs = work / "repo", work / "inputs"
            repo.mkdir()
            inputs.mkdir()
            model, runtime_input = inputs / "qwen-2-model", inputs / "qwen-2-runtime"
            model.mkdir()
            runtime_input.mkdir()
            (runtime_input / "python").write_bytes(b"SYNTHETIC_NOT_EXECUTED")
            receipt_dir = inputs / "receipt"
            receipt_dir.mkdir()
            receipt = receipt_dir / "ls1_runtime_inventory.json"
            sha = kaggle.inventory_runtime(runtime_input, receipt)
            settings = {"model_key": "qwen2_5", "mode": "technical", "run_id": "fake-launch-first",
                        "source_commit": "a"*40, "internet_off_confirmed": True, "runtime_inventory_sha256": sha}
            run_root = repo / "data/processed/ls1/runs/fake-launch-first"
            def child(*args, **kwargs):
                run_root.mkdir(parents=True)
                artifacts.write_json(run_root / "run_failure.json", {"fixture": "FAKE_CHILD_FAILURE"})
                artifacts.seal(run_root)
                raise subprocess.CalledProcessError(1, "SYNTHETIC_CHILD")
            with patch.object(kaggle, "restore_model", return_value=model), \
                 patch.object(kaggle, "runtime_interpreter", return_value={"python": "FAKE", "site_packages": None, "software_versions": {}}), \
                 patch.object(kaggle.subprocess, "run", side_effect=child), self.assertRaises(subprocess.CalledProcessError):
                kaggle.launch(repo, inputs, settings)
            archive = work / "ls1-output-fake-launch-first/ls1_results.tar.gz"
            self.assertTrue(archive.is_file())
            with tarfile.open(archive) as stream:
                self.assertFalse(any(name.endswith("launch_settings.json") for name in stream.getnames()))
            with self.assertRaises(FileExistsError):
                kaggle.launch(repo, inputs, settings)

    def test_notebooks_no_outputs_compile_and_locked(self):
        for model in tokenizer.MODELS:
            path = ROOT / "notebooks" / ("ls1_" + model + "_kaggle.ipynb")
            nb = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(nb["metadata"]["kaggle"]["isInternetEnabled"])
            for cell in nb["cells"]:
                if cell["cell_type"] == "code":
                    self.assertEqual(cell["outputs"], [])
                    source = "".join(cell["source"])
                    compile(source, str(path), "exec")
            source = "\n".join("".join(c["source"]) for c in nb["cells"])
            self.assertIn('"mode": "technical"', source)
            self.assertIn(SPLIT_LOCK_MESSAGE, source)
            self.assertNotIn('"approval_sha256"', source)
            self.assertNotIn('"approval_input"', source)
            self.assertNotIn("pip install", source)

    def test_paths_and_ambiguity(self):
        with tempfile.TemporaryDirectory() as d:
            for value in ("../x", "/x", "C:/x", "a\\b"):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    kaggle.attached_path(d, value)
            with self.assertRaises(ValueError):
                kaggle.select_input(d, "", ("runtime",))

    def test_internet_confirmation_gate(self):
        settings = {"model_key": "qwen2_5", "mode": "technical", "run_id": "internet-check",
                    "source_commit": "a"*40}
        with tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(PermissionError, "^CONFIRM_KAGGLE_INTERNET_OFF$"):
            kaggle.launch(d, d, settings)

    def test_split_lock_before_approval_dataset_model_or_runtime_access(self):
        for model in tokenizer.MODELS:
            for mode in ("train", "test"):
                for internet in (False, True):
                    settings = {"model_key": model, "mode": mode, "run_id": "locked-launch",
                                "source_commit": "a"*40, "internet_off_confirmed": internet,
                                "approval_input": "DO_NOT_READ", "approval_path": "DO_NOT_READ",
                                "approval_sha256": "a"*64, "protect_level01": True,
                                "dataset_root": "DO_NOT_READ"}
                    with self.subTest(model=model, mode=mode, internet=internet), \
                         patch.object(kaggle, "attached_path", side_effect=AssertionError("ATTACHMENT_READ")) as attached, \
                         patch.object(kaggle, "select_input", side_effect=AssertionError("INPUT_READ")) as select, \
                         patch.object(kaggle, "verify_runtime_input", side_effect=AssertionError("RUNTIME_READ")) as verify, \
                         patch.object(kaggle, "restore_model", side_effect=AssertionError("MODEL_LOAD")) as restore, \
                         patch.object(kaggle, "runtime_interpreter", side_effect=AssertionError("RUNTIME_LOAD")) as interpreter, \
                         patch.object(kaggle.subprocess, "run", side_effect=AssertionError("CHILD_EXECUTION")) as child, \
                         patch.object(Path, "read_bytes", side_effect=AssertionError("FILE_READ")) as read, \
                         patch.object(Path, "mkdir", side_effect=AssertionError("ARTIFACT_WRITE")) as mkdir:
                        with self.assertRaises(PermissionError) as error:
                            kaggle.launch(ROOT, ROOT, settings)
                        self.assertEqual(error.exception.args, (SPLIT_LOCK_MESSAGE,))
                        for operation in (attached, select, verify, restore, interpreter, child, read, mkdir):
                            operation.assert_not_called()

    def test_notebook_split_lock_before_source_or_resource_reads(self):
        for model in tokenizer.MODELS:
            nb = json.loads((ROOT / "notebooks" / ("ls1_" + model + "_kaggle.ipynb")).read_text(encoding="utf-8"))
            source = "".join(next(c for c in nb["cells"] if c["id"] == "ls1-run")["source"])
            for mode in ("train", "test"):
                with self.subTest(model=model, mode=mode), \
                     patch("builtins.__import__", side_effect=AssertionError("IMPORT_BEFORE_LOCK")) as imports, \
                     patch.object(Path, "read_bytes", side_effect=AssertionError("READ_BEFORE_LOCK")) as read:
                    with self.assertRaises(PermissionError) as error:
                        exec(compile(source, "synthetic-notebook-cell", "exec"), {"SETTINGS": {"mode": mode}})
                    self.assertEqual(error.exception.args, (SPLIT_LOCK_MESSAGE,))
                    imports.assert_not_called()
                    read.assert_not_called()

    def test_missing_model_no_provision(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            kaggle.restore_model(ROOT, Path(d), "qwen2_5")

    def test_runtime_missing_no_install(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            kaggle.runtime_interpreter(ROOT, Path(d), "internvl3")

    def test_runtime_reuses_existing_python_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "bin/python3.11"
            path.parent.mkdir()
            path.write_bytes(b"SYNTHETIC_NOT_EXECUTABLE")
            result = SimpleNamespace(returncode=0, stdout=json.dumps(tokenizer.plan("qwen2_5")["software"]))
            with patch.object(kaggle.subprocess, "run", return_value=result):
                receipt = kaggle.runtime_interpreter(ROOT, root, "qwen2_5")
            self.assertEqual(receipt["python"], str(path))

    def test_source_package_only_committed_files(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            repo.mkdir()
            def git(*args):
                return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
            git("init")
            git("config", "user.email", "test@example.invalid")
            git("config", "user.name", "Synthetic Test")
            (repo / "tracked.py").write_text("pass\n")
            (repo / "ignored-model.txt").write_text("untracked dummy")
            git("add", "tracked.py")
            git("commit", "-m", "Synthetic source")
            output = Path(d) / "output"
            kaggle.bundle_source(repo, output)
            receipt = json.loads((output / "ls1_source_release.json").read_text())
            self.assertEqual(receipt["archive_sha256"], artifacts.digest(output / receipt["archive"]))
            with tarfile.open(output / receipt["archive"]) as stream:
                self.assertEqual(stream.getnames(), ["tracked.py"])


class ProtectedStateTests(unittest.TestCase):
    def test_official_tree_bytes_equal_verified_base(self):
        base = "1722f82d5ced5624e5182a3311c7e0e24fca9458"
        paths = subprocess.check_output(["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", base,
            "safeshift", "configs", "prompts", "scripts", "notebooks", "data/manifests"], text=True).splitlines()
        for name in paths:
            expected = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", base + ":" + name], text=True).strip()
            content = (ROOT / name).read_bytes()
            actual = hashlib.sha1(("blob " + str(len(content)) + "\0").encode() + content).hexdigest()
            self.assertEqual(actual, expected, "Official tracked artifact changed: " + name)

    def test_import_does_not_load_ml_or_dataset(self):
        source = ("import sys; import safeshift.ls1.core, safeshift.ls1.runtime, safeshift.ls1.tokenizer, "
                  "safeshift.ls1.experiment, safeshift.ls1.kaggle, safeshift.ls1.evaluate; "
                  "assert 'torch' not in sys.modules; assert 'transformers' not in sys.modules")
        subprocess.run([sys.executable, "-c", source], cwd=ROOT, check=True)


class RealTokenizerTests(unittest.TestCase):
    def test_real_qwen(self):
        snapshot = os.environ.get("LS1_QWEN_SNAPSHOT")
        if not snapshot:
            self.skipTest("T1 Qwen2.5 BLOCKED: no pinned snapshot supplied")
        result, tok = tokenizer.t1("qwen2_5", snapshot)
        if result["status"] == "BLOCKED":
            self.skipTest("T1 Qwen2.5 BLOCKED: " + result["reason"])
        self.assertEqual(result["status"], "PASS", result)
        self.assertIsNotNone(tok)

    def test_real_internvl(self):
        snapshot = os.environ.get("LS1_INTERNVL_SNAPSHOT")
        if not snapshot:
            self.skipTest("T1 InternVL3 BLOCKED: no pinned snapshot supplied")
        result, tok = tokenizer.t1("internvl3", snapshot)
        if result["status"] == "BLOCKED":
            self.skipTest("T1 InternVL3 BLOCKED: " + result["reason"])
        self.assertEqual(result["status"], "PASS", result)
        self.assertIsNotNone(tok)


if __name__ == "__main__":
    unittest.main()
