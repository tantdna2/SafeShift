"""Synthetic checks; no dataset samples or model calls."""

import copy
import json
import unittest

from scripts.analyze_three_model_summaries import check_report, close, export_rows, metadata_census, statistics, sum_matrices


class AggregateChecks(unittest.TestCase):
    def setUp(self):
        self.matrix = {
            "Level01": {"Level01": 1, "Level04": 1},
            "Level02": {"Level02": 1},
            "Level03": {},
            "Level04": {"Level01": 1, "Level04": 3},
        }

    def test_class_and_binary_denominators_differ(self):
        result = statistics(self.matrix)
        self.assertEqual(result["binary"]["FN"], 1)
        self.assertEqual(result["binary"]["FP"], 1)
        self.assertEqual(result["per_class"]["Level01"]["recall"], 0.5)
        self.assertAlmostEqual(result["binary"]["recall_anomaly"], 2 / 3)
        self.assertAlmostEqual(result["auroc_generated"], (2 / 3 + 3 / 4) / 2)

    def test_constant_anomaly_is_not_perfect(self):
        result = statistics({t: {"Level01": n} for t, n in zip(self.matrix, (2, 1, 1, 4))})
        self.assertEqual(result["auroc_generated"], 0.5)
        self.assertEqual(result["fpr_normal"], 1)
        self.assertIsNone(result["binary"]["precision_normal"])

    def test_absent_class_not_zero_recall(self):
        result = statistics(self.matrix)
        self.assertIsNone(result["per_class"]["Level03"]["recall"])
        self.assertEqual(result["per_class"]["Level03"]["f1"], 0)
        self.assertAlmostEqual(result["balanced_acc_support"], (0.5 + 1 + 0.75) / 3)

    def test_single_binary_class_auc_is_undefined(self):
        matrix = {t: {} for t in self.matrix}
        matrix["Level04"] = {"Level04": 2}
        self.assertIsNone(statistics(matrix)["auroc_generated"])

    def test_reject_invalid_counts_and_columns(self):
        for value in (-1, 0.5, True):
            bad = copy.deepcopy(self.matrix)
            bad["Level01"]["Level01"] = value
            with self.assertRaises(ValueError):
                statistics(bad)
        bad = copy.deepcopy(self.matrix)
        bad["Level04"]["INVALID"] = 1
        with self.assertRaises(ValueError):
            statistics(bad)

    def test_reject_missing_truth_row_and_empty_cohort(self):
        with self.assertRaises(ValueError):
            statistics({})
        with self.assertRaises(ValueError):
            statistics({t: {} for t in self.matrix})

    def test_report_drift_rejected(self):
        report = statistics(self.matrix)
        report["confusion"] = self.matrix
        report["auroc_pa3"] = 0.8
        check_report(report)
        report["fp_normal"] += 1
        with self.assertRaises(ValueError):
            check_report(report)

    def test_nonfinite_and_tolerance(self):
        for value in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                close(value, 0.5, "test")
        close(0.12345679, 0.123456789, "rounded", 5e-8)

    def test_add_counts_not_average_rates(self):
        total = sum_matrices([self.matrix, self.matrix])
        self.assertEqual(statistics(total)["n"], 14)
        self.assertEqual(statistics(total)["binary"]["FN"], 2)

    def test_saved_export_rejects_overlap_failure_and_nonfinite(self):
        header = b"sample_id,status,true_level,generated_label,pa3_score\n"
        good = b"synthetic-a,SUCCESS,Level01,Level04,0.5\n"
        self.assertEqual(len(export_rows(header + good)), 1)
        for rows in [good + good, good.replace(b"0.5", b"nan"),
                     good.replace(b"SUCCESS", b"TECHNICAL_ERROR")]:
            with self.assertRaises(ValueError):
                export_rows(header + rows)

    def test_metadata_filters_train_and_does_not_certify_source_groups(self):
        row = {"split": "train", "point_id": "synthetic-point", "safety_level": "Level01",
               "source_family": "synthetic-key", "robot_platform": "Wheeled", "folder_domain": "power"}
        heldout = dict(row, split="test", point_id="other-point")
        result = metadata_census(json.dumps({"samples": [row, row, heldout]}).encode())
        self.assertEqual(result["n"], 2)
        self.assertEqual(result["point_id_groups"], 1)
        self.assertEqual(result["anomaly_regex_family_keys"], 1)
        self.assertFalse(result["source_groups_verified_independent"])


if __name__ == "__main__":
    unittest.main()
