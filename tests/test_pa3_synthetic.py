"""Task 3B: deterministic CPU fixtures only, including corrupted evidence."""

from copy import deepcopy
import math
from pathlib import Path
import tempfile
import unittest

from safeshift.pa3 import artifacts, audit, evaluate, policy, runner, scoring, synthetic

BASE = "a7146bbb2c44eb26160f26716af23a8b70260dee"


def settings(*cases):
    return {"mode": "synthetic", "run_id": "pa3-synthetic-unit", "source_commit": BASE,
            "cases": list(cases or policy.DEFAULT_CASES)}


class SyntheticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)

    def run_cases(self, *cases):
        s = settings(*cases)
        runner.run(self.repo, s)
        return audit.audit_run(self.repo, s)

    def test_score_uses_raw_not_processed(self):
        result = self.run_cases("anomaly", "normal")
        a, n = result["results"]
        expected = math.log(1 + math.e + math.exp(4))
        self.assertAlmostEqual(a["score"], expected)
        self.assertAlmostEqual(n["score"], expected - 8)
        self.assertEqual(n["generated_label"], "Level03")
        self.assertEqual(n["details"]["prediction"], "Level04")
        self.assertFalse(n["details"]["raw_and_processed_label_scores_equal"])
        self.assertEqual(result["evaluation"]["auroc"]["value"], 1)
        self.assertEqual(result["evaluation"]["controls_same_eligible_ids"]["generated_binary_label_auroc"], .5)

    def test_constant_scores_and_always_level03(self):
        result = self.run_cases("constant_anomaly", "constant_normal")
        self.assertAlmostEqual(result["results"][0]["score"], math.log(3))
        self.assertEqual(result["evaluation"]["auroc"]["value"], .5)
        self.assertTrue(all(v == .5 for v in result["evaluation"]["controls_same_eligible_ids"].values()))

    def test_low_auroc_not_reversed(self):
        result = self.run_cases("reversed_anomaly", "reversed_normal")
        self.assertEqual(result["evaluation"]["auroc"]["value"], 0)

    def test_large_common_raw_offset_preserves_log_odds(self):
        result = self.run_cases("constant_anomaly", "offset_constant")
        self.assertAlmostEqual(result["results"][1]["score"], math.log(3))
        self.assertEqual(result["results"][0]["score"], result["results"][1]["score"])

    def test_ties_pairwise_oracle(self):
        s = settings("anomaly", "normal", "level02", "constant_anomaly", "constant_normal")
        runner.run(self.repo, s)
        result = audit.audit_run(self.repo, s)
        gt = synthetic.ground_truth(s)
        positives = [r["score"] for r in result["results"] if gt[r["sample_id"]] != "Level04"]
        negatives = [r["score"] for r in result["results"] if gt[r["sample_id"]] == "Level04"]
        oracle = sum((a > b) + .5 * (a == b) for a in positives for b in negatives) / (len(positives) * len(negatives))
        self.assertEqual(result["evaluation"]["auroc"]["value"], oracle)
        self.assertEqual(result["evaluation"]["auroc"]["pair_denominator"], 6)

    def test_one_class_na_with_reason(self):
        result = self.run_cases("anomaly", "level02", "level03")["evaluation"]
        self.assertIsNone(result["auroc"]["value"])
        self.assertIsNotNone(result["auroc"]["reason"])
        self.assertEqual(result["auroc"]["pair_denominator"], 0)
        self.assertIsNone(result["coverage"]["by_binary_class"]["Normal"]["fraction"])

    def test_invalid_no_rescue_and_denominators(self):
        result = self.run_cases()
        report = result["evaluation"]
        self.assertEqual(report["flow"], dict(planned=5, attempted=5, persisted=5, parsed=4, scored=4))
        self.assertEqual(report["coverage"]["overall"]["fraction"], 4 / 5)
        self.assertEqual(report["coverage"]["by_binary_class"]["Normal"],
                         dict(scored=1, planned=2, fraction=.5, reason=None))
        self.assertEqual(report["coverage"]["by_level"]["Level03"]["planned"], 1)
        invalid = result["results"][-1]
        self.assertEqual(invalid["status"], "INVALID")
        self.assertIsNone(invalid["score"])
        self.assertIsNone(invalid["generated_label"])
        self.assertFalse(report["auroc"]["full_cohort_auroc_inferred"])

    def test_all_invalid_has_zero_coverage_not_zero_score(self):
        result = self.run_cases("invalid")["evaluation"]
        self.assertEqual(result["coverage"]["overall"]["fraction"], 0)
        self.assertIsNone(result["auroc"]["value"])
        self.assertEqual(result["flow"]["parsed"], 0)

    def test_fence_uses_existing_acceptance(self):
        result = self.run_cases("fenced")["results"][0]
        self.assertEqual(result["status"], "SUCCESS")
        self.assertTrue(result["details"]["decision"]["format_wrapper_detected"])

    def test_technical_faults_stop_without_scoring(self):
        faults = ("escaped", "alignment", "multi_token", "wrong_generated", "raw_nan", "raw_inf",
                  "raw_negative_inf", "processed_nan", "processed_inf", "missing_step", "missing_candidate", "overflow")
        for name in faults:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as repo:
                s = settings(name, "normal")
                runner.run(repo, s)
                result = audit.audit_run(repo, s)
                self.assertEqual([r["status"] for r in result["results"]], ["TECHNICAL_ERROR", "NOT_ATTEMPTED"])
                self.assertIsNone(result["results"][0]["score"])
                self.assertTrue(result["results"][0]["errors"])
                self.assertEqual(result["evaluation"]["flow"]["persisted"], 1)
                self.assertFalse(result["evaluation"]["completed"])

    def test_processed_negative_inf_mask_is_allowed(self):
        self.assertEqual(self.run_cases("processed_mask")["results"][0]["status"], "SUCCESS")

    def test_nonfinite_evidence_roundtrip_is_tagged(self):
        result = self.run_cases("raw_nan")
        raw = artifacts.read(self.repo, settings("raw_nan"), "000.raw")
        self.assertTrue(math.isnan(raw["trace"]["steps"][0]["mock_raw_vector"][0]))
        stored = artifacts.location(self.repo, settings("raw_nan"), "000.raw").read_text()
        self.assertIn('"nonfinite_float":"nan"', stored)
        self.assertNotIn(":NaN", stored)
        self.assertEqual(result["integrity"], "PASS")

    def test_runtime_error_retained_with_no_parse(self):
        result = self.run_cases("runtime_error", "normal")
        self.assertEqual(result["results"][0]["errors"], ["SYNTHETIC_RUNTIME_ERROR"])
        self.assertEqual(result["evaluation"]["flow"], dict(planned=2, attempted=1, persisted=1, parsed=0, scored=0))

    def test_interrupt_preserves_prior_results_and_unattempted(self):
        result = self.run_cases("anomaly", "interrupt", "normal")
        self.assertEqual([r["status"] for r in result["results"]], ["SUCCESS", "INTERRUPTED", "NOT_ATTEMPTED"])
        self.assertEqual(result["evaluation"]["scope"], "PARTIAL_RUN_DESCRIPTIVE_ONLY")
        self.assertTrue(result["sealed"])

    def test_finished_and_failed_runs_cannot_be_overwritten(self):
        for names in (("normal",), ("interrupt",)):
            with self.subTest(names=names), tempfile.TemporaryDirectory() as repo:
                s = settings(*names)
                root = runner.run(repo, s)
                before = {p.name: p.read_bytes() for p in root.iterdir()}
                with self.assertRaises(FileExistsError):
                    runner.run(repo, s)
                self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_raw_checksum_tamper_is_rejected(self):
        self.run_cases("normal")
        s = settings("normal")
        path = artifacts.location(self.repo, s, "000.raw")
        path.write_bytes(path.read_bytes().replace(b"Level03", b"Level04"))
        with self.assertRaisesRegex(ValueError, "CHECKSUM"):
            audit.audit_run(self.repo, s)

    def test_recompute_rejects_score_tamper_even_resealed(self):
        self.run_cases("normal")
        s = settings("normal")
        row = artifacts.read(self.repo, s, "000.result")
        row["score"] = 999.0
        self.rewrite_and_reseal(s, "000.result", row)
        with self.assertRaisesRegex(ValueError, "RECOMPUTATION"):
            audit.audit_run(self.repo, s)

    def rewrite_and_reseal(self, s, name, value):
        # Intentional test corruption, never a production write path.
        path = artifacts.location(self.repo, s, name)
        data = artifacts.json_bytes(value)
        path.write_bytes(data)
        path.with_suffix(".sha256.json").write_bytes(artifacts.json_bytes(artifacts.receipt(data)))
        seal = artifacts.location(self.repo, s, "seal")
        data = artifacts.json_bytes(artifacts.inventory(self.repo, s))
        seal.write_bytes(data)
        seal.with_suffix(".sha256.json").write_bytes(artifacts.json_bytes(artifacts.receipt(data)))

    def test_resealed_raw_cannot_impersonate_synthetic(self):
        self.run_cases("normal")
        s = settings("normal")
        raw = artifacts.read(self.repo, s, "000.raw")
        raw["specimen"]["source"] = "INSPECSAFE"
        self.rewrite_and_reseal(s, "000.raw", raw)
        with self.assertRaisesRegex(PermissionError, "SYNTHETIC"):
            audit.audit_run(self.repo, s)

    def test_changed_manifest_rejected(self):
        self.run_cases("normal")
        s = settings("normal")
        header = artifacts.read(self.repo, s, "manifest")
        header["identity"]["target_only"]["revision"] = "0" * 40
        self.rewrite_and_reseal(s, "manifest", header)
        with self.assertRaisesRegex(PermissionError, "IDENTITY"):
            audit.audit_run(self.repo, s)

    def test_unsealed_journal_after_raw_is_partial(self):
        s = settings("anomaly", "normal")
        artifacts.create(self.repo, s)
        artifacts.write(self.repo, s, "manifest", runner.manifest(s))
        artifacts.write(self.repo, s, "000.attempt", synthetic.specimen(s, "anomaly"))
        artifacts.write(self.repo, s, "000.raw", scoring.raw_record(s, "anomaly"))
        result = audit.audit_run(self.repo, s)
        self.assertFalse(result["sealed"])
        self.assertEqual(result["evaluation"]["flow"], dict(planned=2, attempted=1, persisted=1, parsed=0, scored=0))
        self.assertEqual(result["results"][0]["status"], "UNPROCESSED")

    def test_unsealed_attempt_without_raw_is_retained(self):
        s = settings("normal")
        artifacts.create(self.repo, s)
        artifacts.write(self.repo, s, "manifest", runner.manifest(s))
        artifacts.write(self.repo, s, "000.attempt", synthetic.specimen(s, "normal"))
        result = audit.audit_run(self.repo, s)
        self.assertEqual(result["evaluation"]["flow"], dict(planned=1, attempted=1, persisted=0, parsed=0, scored=0))

    def test_torn_write_fails_audit_without_repair(self):
        s = settings("normal")
        artifacts.create(self.repo, s)
        artifacts.write(self.repo, s, "manifest", runner.manifest(s))
        artifacts.location(self.repo, s, "000.attempt").write_bytes(b'{"partial":')
        with self.assertRaises((ValueError, FileNotFoundError)):
            audit.audit_run(self.repo, s)

    def test_inventory_extra_file_rejected(self):
        self.run_cases("normal")
        (artifacts.location(self.repo, settings("normal")) / "extra.json").write_text("{}")
        with self.assertRaises(PermissionError):
            audit.audit_run(self.repo, settings("normal"))

    def test_receipt_only_collision_never_writes_data(self):
        s = settings("normal")
        artifacts.create(self.repo, s)
        path = artifacts.location(self.repo, s, "manifest")
        path.with_suffix(".sha256.json").write_bytes(b"old receipt")
        with self.assertRaises(FileExistsError):
            artifacts.write(self.repo, s, "manifest", runner.manifest(s))
        self.assertFalse(path.exists())

    def test_forged_finished_flag_rejected_on_partial_run(self):
        self.run_cases("interrupt", "normal")
        s = settings("interrupt", "normal")
        artifacts.write(self.repo, s, "finish", {"status": "FINISHED", "planned": 2})
        self.rewrite_and_reseal(s, "finish", {"status": "FINISHED", "planned": 2})
        with self.assertRaisesRegex(ValueError, "FINISHED_JOURNAL"):
            audit.audit_run(self.repo, s)

    def test_unsealed_later_attempt_after_failure_rejected(self):
        s = settings("runtime_error", "normal")
        artifacts.create(self.repo, s)
        artifacts.write(self.repo, s, "manifest", runner.manifest(s))
        for i, name in enumerate(s["cases"]):
            artifacts.write(self.repo, s, f"{i:03d}.attempt", synthetic.specimen(s, name))
            artifacts.write(self.repo, s, f"{i:03d}.raw", scoring.raw_record(s, name))
            raw = artifacts.read(self.repo, s, f"{i:03d}.raw")
            artifacts.write(self.repo, s, f"{i:03d}.result", scoring.score_raw(s, name, raw))
        with self.assertRaisesRegex(ValueError, "ATTEMPT_SEQUENCE"):
            audit.audit_run(self.repo, s)

    def test_gt_missing_extra_and_wrong_labels_rejected(self):
        result = self.run_cases("anomaly", "normal")
        s = settings("anomaly", "normal")
        truth = synthetic.ground_truth(s)
        variants = ({}, {**truth, "extra": "Level01"}, {**truth, "pa3-synthetic-normal": "Level03"})
        for gt in variants:
            with self.subTest(gt=gt), self.assertRaisesRegex(ValueError, "GT_JOIN"):
                evaluate.report(s, result["results"], gt)

    def test_unique_ids_and_gt_join_by_id_not_position(self):
        result = self.run_cases("anomaly", "normal")
        s = settings("anomaly", "normal")
        rows = result["results"]
        truth = synthetic.ground_truth(s)
        self.assertEqual(evaluate.report(s, rows[::-1], truth)["auroc"]["value"], 1)
        with self.assertRaisesRegex(ValueError, "UNIQUE_GT_JOIN"):
            evaluate.report(s, [rows[0], rows[0]], truth)

    def test_evaluator_rejects_nan_inf_and_missing_score_fill(self):
        result = self.run_cases("anomaly", "invalid")
        s = settings("anomaly", "invalid")
        for value in (math.nan, math.inf, -math.inf, None, True):
            rows = deepcopy(result["results"])
            rows[0]["score"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluate.report(s, rows, synthetic.ground_truth(s))
        rows = deepcopy(result["results"])
        rows[1]["score"] = 0.0
        with self.assertRaisesRegex(ValueError, "MISSING_SCORE"):
            evaluate.report(s, rows, synthetic.ground_truth(s))

    def test_evaluator_rejects_finite_replacement_scores(self):
        result = self.run_cases("normal")
        s = settings("normal")
        result["results"][0]["score"] = 42.0
        with self.assertRaisesRegex(ValueError, "SYNTHETIC_RAW_RESULT"):
            evaluate.report(s, result["results"], synthetic.ground_truth(s))

    def test_no_calibrated_or_reference_artifacts(self):
        self.run_cases()
        root = artifacts.location(self.repo, settings())
        for path in root.glob("*.json"):
            data = path.read_text()
            self.assertNotIn('"reference_key"', data)
            self.assertNotIn('"calibrated"', data)
        self.assertFalse((root / "references").exists())


if __name__ == "__main__":
    unittest.main()
