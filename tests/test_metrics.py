"""Classification invariants including INVALID and exact sample joins."""

import unittest

from safeshift.data.schema import PredictionRecord, SAFETY_LEVELS, SampleRecord
from safeshift.evaluation.metrics import classification_metrics


class ClassificationTests(unittest.TestCase):
    def test_counts_recall_and_invalid_full_denominator(self):
        truths = ("Level01", "Level01", "Level01", "Level02", "Level03", "Level04", "Level04")
        labels = ("Level01", None, "Level04", "Level01", "Level03", "Level02", "Level04")
        samples = [SampleRecord(f"synthetic-{i}", level) for i, level in enumerate(truths)]
        predictions = [PredictionRecord(f"synthetic-{i}", level) for i, level in enumerate(labels)]
        result = classification_metrics(iter(samples), reversed(predictions))
        self.assertEqual(result["n_images"], 7)
        self.assertEqual(result["valid_canonical_n"], 6)
        self.assertEqual(result["invalid_n"], 1)
        self.assertEqual(result["support"], {"Level01": 3, "Level02": 1, "Level03": 1, "Level04": 2})
        self.assertEqual(result["confusion_matrix"]["Level01"],
                         {"Level01": 1, "Level02": 0, "Level03": 0, "Level04": 1, "INVALID": 1})
        self.assertAlmostEqual(result["per_class"]["Level01"]["recall"], 1 / 3)
        self.assertEqual(result["per_class"]["Level02"]["recall"], 0)
        self.assertEqual(result["per_class"]["Level03"]["recall"], 1)
        self.assertEqual(result["per_class"]["Level04"]["recall"], 0.5)
        self.assertEqual(sum(sum(row.values()) for row in result["confusion_matrix"].values()), 7)

    def test_empty_cohort_has_undefined_recall(self):
        result = classification_metrics([], [])
        self.assertEqual((result["n_images"], result["invalid_n"]), (0, 0))
        self.assertTrue(all(n == 0 for n in result["support"].values()))
        self.assertTrue(all(row["recall"] is None for row in result["per_class"].values()))

    def test_all_invalid_is_never_normal_or_excluded(self):
        result = classification_metrics([SampleRecord("s", "Level04")], [PredictionRecord("s", None)])
        self.assertEqual(result["confusion_matrix"]["Level04"]["INVALID"], 1)
        self.assertEqual(result["confusion_matrix"]["Level04"]["Level04"], 0)
        self.assertEqual(result["per_class"]["Level04"]["recall"], 0)
        self.assertIsNone(result["per_class"]["Level01"]["recall"])
        self.assertEqual(result["valid_canonical_n"], 0)

    def test_perfect_predictions_and_all_class_support(self):
        result = classification_metrics([SampleRecord(level, level) for level in SAFETY_LEVELS],
                                        [PredictionRecord(level, level) for level in SAFETY_LEVELS])
        self.assertEqual(result["invalid_n"], 0)
        self.assertTrue(all(row["recall"] == 1 for row in result["per_class"].values()))

    def test_missing_extra_and_wrong_ids_are_errors(self):
        for predictions in ([], [PredictionRecord("other", "Level01")],
                            [PredictionRecord("s", "Level01"), PredictionRecord("extra", None)]):
            with self.subTest(predictions=predictions), self.assertRaisesRegex(ValueError, "exact"):
                classification_metrics([SampleRecord("s", "Level01")], predictions)
        with self.assertRaises(ValueError):
            classification_metrics([], [PredictionRecord("extra", None)])

    def test_duplicates_cannot_inflate_support_or_overwrite_predictions(self):
        sample, prediction = SampleRecord("s", "Level01"), PredictionRecord("s", "Level01")
        for samples, predictions in (([sample, sample], [prediction]),
                                     ([sample], [prediction, PredictionRecord("s", "Level04")])):
            with self.subTest(samples=samples, predictions=predictions), self.assertRaises(ValueError):
                classification_metrics(samples, predictions)

    def test_repeated_calls_do_not_share_counts(self):
        result = classification_metrics([SampleRecord("s", "Level01")], [PredictionRecord("s", None)])
        result["confusion_matrix"]["Level01"]["INVALID"] = 99
        empty = classification_metrics([], [])
        self.assertEqual(empty["confusion_matrix"]["Level01"]["INVALID"], 0)
