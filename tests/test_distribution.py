"""Synthetic data only: aggregation, error handling, provenance and raw protection."""

import contextlib
import copy
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from safeshift.data.distribution import (
    annotation_density, aspect_ratio, audit_distribution, checked_output,
    cross_table, domain_mismatches, label_summary, missing_metadata,
    numeric_summary, rare_flags, regression_checks, resolution_summary,
    summarize_distribution, total_variation, write_report,
)
from safeshift.data.manifest import ManifestError, collect_manifest
from scripts.audit_distribution import main


def row(**kwargs):
    return {"split": "train", "data_type": "Normal_data", "folder_domain": "power",
            "text_domain": "power", "safety_level": "Level04", "robot_platform": "Wheeled",
            "image_width": 16, "image_height": 9, "num_shapes": 1,
            "object_labels": ["Synthetic"], "text_description": "SYNTHETIC_PRIVATE_TEXT", **kwargs}


class DistributionTests(unittest.TestCase):
    def test_basic_count_table(self):
        table = cross_table([row(), row(), row(split="test")], ("split", "data_type"))
        self.assertEqual(table["total"], 3)
        self.assertEqual(sum(c["count"] for c in table["cells"]), 3)
        self.assertEqual(next(c["count"] for c in table["cells"]
                              if c["split"] == "train" and c["data_type"] == "Normal_data"), 2)

    def test_three_way_table(self):
        table = cross_table([row(), row(folder_domain="tunnel")], ("split", "folder_domain", "data_type"))
        self.assertEqual(len(table["cells"]), 20)
        self.assertEqual(sum(c["count"] for c in table["cells"]), 2)
        self.assertEqual(table["row_fields"], ["split", "folder_domain"])

    def test_percentage_denominator(self):
        rows = [row(), row(), row(data_type="Anomaly_data"), row(split="test")]
        cells = cross_table(rows, ("split", "data_type"))["cells"]
        anomaly = next(c for c in cells if c["split"] == "train" and c["data_type"] == "Anomaly_data")
        self.assertEqual(anomaly["row_total"], 3)
        self.assertAlmostEqual(anomaly["row_percentage"], 100 / 3)

    def test_three_way_denominator(self):
        rows = [row(), row(data_type="Anomaly_data"), row(folder_domain="tunnel")]
        cells = cross_table(rows, ("split", "folder_domain", "data_type"))["cells"]
        cell = next(c for c in cells if c["split"] == "train" and c["folder_domain"] == "power"
                    and c["data_type"] == "Normal_data")
        self.assertEqual((cell["row_total"], cell["row_percentage"]), (2, 50))

    def test_zero_cells_and_undefined_percentage(self):
        cells = cross_table([row()], ("split", "data_type"))["cells"]
        self.assertEqual(len(cells), 4)
        for cell in cells:
            if cell["split"] == "test":
                self.assertEqual(cell["count"], 0)
                self.assertIsNone(cell["row_percentage"])

    def test_unexpected_category_and_null_retained(self):
        table = cross_table([row(text_domain=None), row(text_domain="new")], ("text_domain",))
        self.assertEqual(sum(c["count"] for c in table["cells"]), 2)
        self.assertEqual(len(table["cells"]), 7)

    def test_rare_cell_flags(self):
        expected = {0: (True, True, True), 9: (False, True, True),
                    10: (False, False, True), 29: (False, False, True), 30: (False, False, False)}
        for count, flags in expected.items():
            self.assertEqual(tuple(rare_flags(count).values()), flags)
        with self.assertRaises(ValueError):
            rare_flags(-1)

    def test_tvd_identical(self):
        self.assertEqual(total_variation({"a": 2, "b": 4}, {"a": 1, "b": 2})["tvd"], 0)

    def test_tvd_disjoint(self):
        self.assertEqual(total_variation({"a": 2}, {"b": 5})["tvd"], 1)

    def test_tvd_partial_overlap(self):
        result = total_variation({"a": 3, "b": 1}, {"a": 1, "b": 3})
        self.assertEqual(result["tvd"], .5)
        self.assertEqual(result["train_total"], 4)
        self.assertEqual(result["categories"][0]["absolute_percentage_point_difference"], 50)

    def test_tvd_empty_and_invalid(self):
        self.assertIsNone(total_variation({}, {"a": 1})["tvd"])
        with self.assertRaises(ValueError):
            total_variation({"a": -1}, {"a": 1})

    def test_resolution_counting(self):
        result = resolution_summary([row(), row(), row(image_width=4, image_height=3)])
        self.assertEqual(result["unique_resolutions"], 2)
        self.assertEqual(result["resolutions"][0]["count"], 2)
        self.assertEqual(result["resolutions"][0]["denominator"], 3)
        self.assertEqual(result["width"]["min"], 4)

    def test_aspect_ratio_grouping(self):
        self.assertEqual(aspect_ratio(1920, 1080), "16:9")
        self.assertEqual(aspect_ratio(640, 480), "4:3")
        self.assertEqual(aspect_ratio(1920, 1081), "1920:1081")
        result = resolution_summary([row(), row(image_width=4, image_height=3), row(image_width=1)])
        self.assertEqual({c["value"]: c["count"] for c in result["aspect_groups"]},
                         {"16:9": 1, "4:3": 1, "other": 1})

    def test_invalid_dimensions(self):
        for value in (0, -1, True, "16"):
            with self.assertRaises(ValueError):
                aspect_ratio(value, 9)
        self.assertEqual(resolution_summary([row(image_width=None)])["unavailable"], 1)

    def test_annotation_density(self):
        result = annotation_density([row(num_shapes=n) for n in (0, 2, 4, 10)])
        overall = result["overall"]
        self.assertEqual([overall[k] for k in ("min", "q1", "median", "mean", "q3", "max")],
                         [0, 1.5, 3, 4, 5.5, 10])
        self.assertEqual(overall["zero_shape_samples"], 1)
        self.assertEqual(overall["total_shapes"], 16)
        self.assertEqual(next(c["mean"] for c in result["by"]["data_type"]
                              if c["data_type"] == "Normal_data"), 4)

    def test_numeric_empty_singleton_and_invalid(self):
        self.assertIsNone(numeric_summary([])["median"])
        self.assertEqual(numeric_summary([3])["q1"], 3)
        with self.assertRaises(ValueError):
            numeric_summary([float("nan")])
        with self.assertRaises(ValueError):
            annotation_density([row(num_shapes=-1)])

    def test_singleton_labels(self):
        self.assertEqual(label_summary([row(object_labels=["a", "a", "b"])])["tail_labels"]["singleton"], ["b"])

    def test_long_tail_thresholds(self):
        labels = [str(n) for n in (1, 5, 6, 10, 11, 99, 100) for _ in range(n)]
        result = label_summary([row(object_labels=labels)])
        self.assertEqual(result["tail_counts"], {"singleton": 1, "le5": 2, "le10": 4, "ge100": 1})

    def test_train_only_label(self):
        result = label_summary([row(object_labels=["a", "b"]), row(split="test", object_labels=["b"])])
        self.assertEqual(result["split_labels"]["train_only"], ["a"])
        self.assertEqual(result["split_labels"]["both"], ["b"])

    def test_test_only_label(self):
        result = label_summary([row(object_labels=["a"]), row(split="test", object_labels=["b"])])
        self.assertEqual(result["split_labels"]["test_only"], ["b"])
        self.assertEqual(result["split_labels"]["very_rare_in_test_1_to_5"], ["b"])

    def test_unicode_and_raw_spelling_preserved(self):
        labels = ["出口", "Object", "object", " Object "]
        result = label_summary([row(object_labels=labels)])
        self.assertEqual(result["unique_raw_labels"], 4)
        self.assertIn("出口", json.dumps(result, ensure_ascii=False))
        self.assertEqual(set(result["tail_labels"]["singleton"]), set(labels))

    def test_duplicate_labels_are_instances(self):
        result = label_summary([row(object_labels=["x"] * 3), row(split="test", object_labels=["x"] * 2)])
        self.assertEqual(result["total_instances"], 5)
        self.assertEqual(result["split_coverage"][0]["train_count"], 3)
        self.assertEqual(result["split_coverage"][0]["test_count"], 2)

    def test_domain_label_coverage(self):
        result = label_summary([row(object_labels=["a", "b"]), row(folder_domain="tunnel", object_labels=["b"])])
        self.assertEqual(result["single_domain_labels"], ["a"])
        self.assertEqual(result["multiple_domain_labels"], ["b"])
        self.assertEqual(next(c["unique_raw_labels"] for c in result["by_domain"] if c["folder_domain"] == "power"), 2)

    def test_missing_metadata(self):
        result = missing_metadata([row(text_domain=None, object_labels=[], image_width=None),
                                   row(text_domain="unknown", text_description="", image_width=0),
                                   row(text_description="  ")])
        self.assertEqual(result["text_domain"]["null_count"], 1)
        self.assertEqual(result["text_domain"]["unknown_unparsed_count"], 2)
        self.assertEqual(result["object_labels"]["empty_count"], 1)
        self.assertEqual(result["object_labels"]["unknown_unparsed_count"], 0)
        self.assertEqual(result["image_width"]["unknown_unparsed_count"], 1)
        self.assertEqual(result["text_description"]["empty_count"], 1)
        self.assertEqual(result["text_description"]["whitespace_only_count"], 1)

    def test_domain_mismatch_matrix(self):
        rows = [row(text_domain="tunnel"), row(text_domain=None), row()]
        result = domain_mismatches(rows)
        self.assertEqual((result["count"], result["comparable_count"], result["unresolved_count"]), (1, 2, 1))
        self.assertEqual(sum(c["count"] for c in result["matrix"]["cells"]), 1)
        self.assertEqual(sum(c["count"] for c in result["detail"]["cells"]), 1)

    def test_deterministic_ordering(self):
        rows = [row(), row(split="test", object_labels=["出口", "Other"]), row(folder_domain="tunnel")]
        self.assertEqual(json.dumps(summarize_distribution(rows), ensure_ascii=False),
                         json.dumps(summarize_distribution(list(reversed(rows))), ensure_ascii=False))

    def test_no_input_mutation_or_text_export(self):
        rows = [row()]
        original = copy.deepcopy(rows)
        report = summarize_distribution(rows)
        self.assertEqual(rows, original)
        self.assertNotIn("SYNTHETIC_PRIVATE_TEXT", json.dumps(report))

    def test_regression_reports_observation_without_forcing(self):
        report = summarize_distribution([row()])
        checks = regression_checks(report)
        self.assertEqual(next(c for c in checks if c["field"] == "total"),
                         {"field": "total", "expected": 5013, "observed": 1, "matches": False})

    def test_empty_safety_ratio_is_undefined(self):
        report = summarize_distribution([])
        self.assertIsNone(report["safety"]["imbalance_ratio"])
        self.assertEqual(len(report["safety"]["absent_levels"]), 4)


class DistributionIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name).resolve()
        self.dataset = self.repo / "data/raw/InspecSafe-V1"
        for split in ("train", "test"):
            for kind in ("Normal_data", "Anomaly_data"):
                (self.dataset / split / "DATA_PATH" / split / "Annotations" / kind).mkdir(parents=True)
        directory = self.dataset / "train/DATA_PATH/train/Annotations/Normal_data/power-Level04-Wheeled-000001"
        directory.mkdir()
        stem = directory / "power-Level04-Wheeled-000001-001"
        Image.new("RGB", (16, 9), "red").save(stem.with_suffix(".jpg"), format="PNG")
        self.annotation = stem.with_suffix(".json")
        self.annotation.write_text(json.dumps({"imageWidth": 16, "imageHeight": 9,
                                              "shapes": [{"label": "出口"}, {"label": "出口"}],
                                              "imageData": "DO_NOT_EXPORT"}, ensure_ascii=False), encoding="utf-8")
        stem.with_suffix(".txt").write_text("In the power facility scene, SYNTHETIC_PRIVATE_TEXT", encoding="utf-8")
        for source in ("safeshift/data/distribution.py", "scripts/audit_distribution.py", "safeshift/data/manifest.py",
                       "requirements-validation.txt", "notes/dataset_schema.md", "notes/duplicate_leakage_audit.md",
                       "notes/visual_provenance_review.md"):
            path = self.repo / source
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic source", encoding="utf-8")

    def test_raw_immutability_and_fingerprint(self):
        before = {p.relative_to(self.repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.dataset.rglob("*") if p.is_file()}
        report = audit_distribution(self.dataset, self.repo)
        after = {p.relative_to(self.repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.dataset.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(report["input_sha256"], collect_manifest(self.dataset, self.repo).input_sha256)
        self.assertEqual(report["labels"]["total_instances"], 2)

    def test_actual_dimensions_override_annotation_and_report_discrepancy(self):
        annotation = json.loads(self.annotation.read_bytes())
        annotation["imageWidth"] = 8
        self.annotation.write_text(json.dumps(annotation), encoding="utf-8")
        report = audit_distribution(self.dataset, self.repo)
        self.assertEqual(report["resolution"]["resolutions"][0]["value"], "16x9")
        self.assertEqual(report["image_dimensions_mismatches"][0]["annotation"], [8, 9])

    def test_missing_triplet_fails_without_partial_report(self):
        self.annotation.unlink()
        with self.assertRaises(ManifestError):
            audit_distribution(self.dataset, self.repo)

    def test_output_protection(self):
        for path in (self.annotation, Path("data/raw/elsewhere.json"), Path("../escape.json"), Path("report.csv")):
            with self.assertRaises(ManifestError):
                checked_output(path, self.dataset, self.repo)

    def test_no_absolute_paths_or_raw_text_in_output(self):
        report = audit_distribution(self.dataset, self.repo)
        output = self.repo / "data/manifests/distribution.json"
        write_report(report, output, self.dataset, self.repo, runtime_seconds=0)
        data = output.read_text(encoding="utf-8")
        self.assertNotIn(str(self.repo), data)
        self.assertNotIn(self.repo.as_posix(), data)
        self.assertNotIn("SYNTHETIC_PRIVATE_TEXT", data)
        self.assertNotIn("DO_NOT_EXPORT", data)
        self.assertIn("出口", data)
        self.assertEqual(json.loads(data)["provenance"]["dataset_root"], "data/raw/InspecSafe-V1")

    def test_cli_discrepancies_and_error_keep_old_output(self):
        args = ["--dataset-root", "data/raw/InspecSafe-V1", "--output", "data/manifests/report.json"]
        with patch("scripts.audit_distribution.REPO_ROOT", self.repo), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(args), 2)
            output = self.repo / "data/manifests/report.json"
            original = output.read_bytes()
            self.annotation.unlink()
            self.assertEqual(main(args), 1)
            self.assertEqual(output.read_bytes(), original)

    def test_atomic_write_failure_keeps_old_output(self):
        output = self.repo / "data/manifests/report.json"
        output.parent.mkdir(parents=True)
        output.write_text("old", encoding="utf-8")
        with patch("safeshift.data.distribution.os.replace", side_effect=OSError("synthetic")):
            with self.assertRaises(OSError):
                write_report({}, output, self.dataset, self.repo, runtime_seconds=0)
        self.assertEqual(output.read_text(encoding="utf-8"), "old")
        self.assertEqual(list(output.parent.iterdir()), [output])


if __name__ == "__main__":
    unittest.main()
