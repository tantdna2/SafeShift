"""Synthetic schema, validation and future model transport contract checks."""

from dataclasses import FrozenInstanceError
import unittest

from safeshift.data.schema import PredictionRecord, SAFETY_LEVELS, SampleRecord
from safeshift.data.validation import (
    prediction_from_mapping, sample_from_mapping, validate_predictions, validate_samples,
)
from safeshift.models.contracts import ModelInput, ModelOutput


class RecordTests(unittest.TestCase):
    def test_historical_label_order_and_round_trip(self):
        self.assertEqual(SAFETY_LEVELS, ("Level01", "Level02", "Level03", "Level04"))
        for level in SAFETY_LEVELS:
            self.assertEqual(sample_from_mapping({"sample_id": "synthetic-1", "true_safety_level": level}),
                             SampleRecord("synthetic-1", level))

    def test_no_label_coercion_or_repair(self):
        for level in (None, True, 1, 1.0, [], {}, "Level1", "level01", "Level01 ", "INVALID"):
            with self.subTest(level=level), self.assertRaises(ValueError):
                SampleRecord("synthetic-1", level)
            if level is not None:
                with self.subTest(prediction=level), self.assertRaises(ValueError):
                    PredictionRecord("synthetic-1", level)

    def test_invalid_requires_explicit_none(self):
        row = prediction_from_mapping({"sample_id": "synthetic-1", "predicted_safety_level": None})
        self.assertIsNone(row.predicted_safety_level)
        with self.assertRaises(ValueError):
            prediction_from_mapping({"sample_id": "synthetic-1"})

    def test_missing_extra_or_non_mapping_fields(self):
        for record in (None, [], {}, {"sample_id": "synthetic-1"},
                       {"true_safety_level": "Level01"},
                       {"sample_id": "synthetic-1", "true_safety_level": "Level01", "split": "train"}):
            with self.subTest(record=record), self.assertRaises(ValueError):
                sample_from_mapping(record)
        with self.assertRaises(ValueError):
            prediction_from_mapping({"sample_id": "synthetic-1", "predicted_safety_level": None, "score": 1})

    def test_identifiers_are_nonempty_strings_without_silent_normalization(self):
        for sid in (None, True, 1, [], {}, "", "  ", " a", "a ", "a\nb", "a\x00b"):
            for record_type, label in ((SampleRecord, "Level01"), (PredictionRecord, None)):
                with self.subTest(sid=sid, record_type=record_type), self.assertRaises(ValueError):
                    record_type(sid, label)

    def test_duplicates_rejected_for_truth_and_predictions(self):
        for validator, first, second in (
            (validate_samples, SampleRecord("s", "Level01"), SampleRecord("s", "Level04")),
            (validate_predictions, PredictionRecord("s", "Level01"), PredictionRecord("s", None)),
        ):
            for rows in ((first, first), (first, second)):
                with self.subTest(validator=validator, rows=rows), self.assertRaisesRegex(ValueError, "duplicate"):
                    validator(iter(rows))

    def test_collection_types_and_empty_input(self):
        self.assertEqual(validate_samples(iter(())), ())
        self.assertEqual(validate_predictions([]), ())
        with self.assertRaises(ValueError):
            validate_samples([{"sample_id": "s", "true_safety_level": "Level01"}])
        with self.assertRaises(ValueError):
            validate_predictions([SampleRecord("s", "Level01")])

    def test_records_are_immutable(self):
        sample = SampleRecord("synthetic-1", "Level01")
        with self.assertRaises(FrozenInstanceError):
            sample.true_safety_level = "Level04"


class ModelContractTests(unittest.TestCase):
    def test_input_contract_does_not_open_image(self):
        row = ModelInput("synthetic-1", "data/processed/synthetic/missing.jpg", "line one\nline two")
        self.assertEqual(row.sample_id, "synthetic-1")

    def test_output_contract_carries_raw_and_configuration_references(self):
        output = ModelOutput("synthetic-1", "run-synthetic", "example/model", "revision-1",
                             "data/processed/run/raw.json", "data/processed/run/prompt.txt",
                             "data/processed/run/generation.json")
        self.assertEqual(output.model_revision, "revision-1")
        with self.assertRaises(ValueError):
            ModelOutput("synthetic-1", "run-synthetic", "example/model", "",
                        "raw.json", "prompt.txt", "generation.json")
        with self.assertRaises(ValueError):
            ModelOutput("synthetic-1", "run-synthetic", "example/model", "revision-1",
                        "../raw.json", "prompt.txt", "generation.json")

    def test_nonportable_or_escaping_paths_rejected(self):
        for path in (None, "", ".", "..", "../image.jpg", "data/../image.jpg", "/image.jpg",
                     "C:/image.jpg", "C:image.jpg", "\\\\server\\share\\image.jpg",
                     "data\\image.jpg", "./image.jpg", "data//image.jpg", "data/image.jpg/"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                ModelInput("synthetic-1", path, "classify")

    def test_missing_or_invalid_input_fields(self):
        with self.assertRaises(TypeError):
            ModelInput("synthetic-1", "synthetic.jpg")
        for prompt in (None, 1, "", "   "):
            with self.subTest(prompt=prompt), self.assertRaises(ValueError):
                ModelInput("synthetic-1", "synthetic.jpg", prompt)
