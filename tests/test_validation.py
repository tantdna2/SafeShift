"""Generated tiny images and synthetic annotations only; never load the real dataset."""

import base64
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageFile

from safeshift.data.manifest import ManifestError
from safeshift.data.validation import validate_dataset, write_report
from scripts.validate_dataset import main


class ValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name).resolve()
        self.dataset = self.repo / "data/raw/InspecSafe-V1"
        for split in ("train", "test"):
            for kind in ("Normal_data", "Anomaly_data"):
                (self.dataset / split / "DATA_PATH" / split / "Annotations" / kind).mkdir(parents=True)

    def sample(self, *, fmt="JPEG", instance="001", point="power-Level04-Wheeled-000001",
               split="train", kind="Normal_data", text="In the power facility scene, synthetic object."):
        directory = self.dataset / split / "DATA_PATH" / split / "Annotations" / kind / point
        directory.mkdir(exist_ok=True)
        stem = f"{point}-{instance}"
        paths = {ext: directory / f"{stem}.{ext}" for ext in ("jpg", "json", "txt")}
        with Image.new("RGB", (8, 6), (20, 80, 120)) as image:
            image.save(paths["jpg"], format=fmt)
        annotation = {"imageWidth": 8, "imageHeight": 6, "imagePath": stem + ".jpg",
                      "imageData": base64.b64encode(paths["jpg"].read_bytes()).decode("ascii"),
                      "shapes": [{"label": "Synthetic", "shape_type": "polygon",
                                  "points": [[1, 1], [5, 1], [1, 4]]}]}
        paths["json"].write_text(json.dumps(annotation), encoding="utf-8")
        paths["txt"].write_bytes(text.encode("utf-8"))
        return paths

    def change(self, paths, **changes):
        annotation = json.loads(paths["json"].read_bytes())
        annotation.update(changes)
        paths["json"].write_text(json.dumps(annotation, ensure_ascii=False), encoding="utf-8")

    def shape(self, paths, **changes):
        annotation = json.loads(paths["json"].read_bytes())
        annotation["shapes"][0].update(changes)
        self.change(paths, shapes=annotation["shapes"])

    def audit(self, verify=True):
        return validate_dataset(self.dataset, self.repo, verify_image_data=verify)

    def assert_issue(self, report, code, severity="ERROR"):
        issues = [i for s in report["samples"] for i in s["issues"]]
        self.assertTrue(any(i["code"] == code and i["severity"] == severity for i in issues), issues)

    def test_valid_jpeg(self):
        self.sample()
        report = self.audit()
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["warnings_count"], 0)
        self.assertEqual(report["summary"]["image_verified"], 1)
        self.assertEqual(report["summary"]["binary_dimension_match"], 1)
        self.assertEqual(report["summary"]["image_data_match"], 1)

    def test_valid_png_content_jpg_extension(self):
        self.sample(fmt="PNG")
        report = self.audit()
        self.assertEqual(report["summary"]["PNG"], 1)
        self.assertEqual(report["summary"]["image_verified"], 1)
        self.assertEqual(report["exit_code"], 0)
        self.assert_issue(report, "image_extension_mismatch", "WARNING")

    def test_dimension_mismatch_includes_sample_id_and_dimensions(self):
        paths = self.sample()
        self.change(paths, imageWidth=9)
        report = self.audit()
        self.assert_issue(report, "binary_dimension_mismatch", "WARNING")
        self.assertEqual(report["samples"][0]["sample_id"], paths["jpg"].stem)
        self.assertEqual(report["samples"][0]["binary_image_width"], 8)

    def test_malformed_json_and_non_object(self):
        paths = self.sample()
        for raw in (b"{bad", b"[]", b"null", b"\xff"):
            with self.subTest(raw=raw):
                paths["json"].write_bytes(raw)
                report = self.audit()
                self.assert_issue(report, "malformed_json")
                self.assertEqual(report["summary"]["image_verified"], 1)
                self.assertEqual(report["exit_code"], 2)

    def test_unknown_magic_still_checks_annotations_and_text(self):
        paths = self.sample(text="")
        paths["jpg"].write_bytes(b"not an image")
        report = self.audit()
        self.assert_issue(report, "unknown_format")
        self.assert_issue(report, "empty_txt")
        self.assertEqual(report["summary"]["total_shapes"], 1)

    def test_truncated_images(self):
        for fmt in ("JPEG", "PNG"):
            with self.subTest(fmt=fmt):
                paths = self.sample(fmt=fmt)
                paths["jpg"].write_bytes(paths["jpg"].read_bytes()[:-20])
                self.assert_issue(self.audit(), "image_verify_failures")

    def test_png_crc_damage(self):
        paths = self.sample(fmt="PNG")
        raw = bytearray(paths["jpg"].read_bytes())
        raw[-17] ^= 1
        paths["jpg"].write_bytes(raw)
        self.assert_issue(self.audit(), "image_verify_failures")

    def test_missing_each_file_and_orphan_annotations(self):
        for ext in ("jpg", "json", "txt"):
            with self.subTest(ext=ext):
                paths = self.sample()
                paths[ext].unlink()
                report = self.audit()
                self.assertEqual(report["summary"]["missing_files"], 1)
                self.assertEqual(report["summary"]["total_samples"], 1)
                self.assertEqual(report["exit_code"], 2)

    def test_unreadable_file_is_reported_without_exposing_exception_path(self):
        paths = self.sample()
        read_bytes = Path.read_bytes
        def read(path):
            if path == paths["txt"]:
                raise PermissionError(13, "synthetic failure")
            return read_bytes(path)
        with patch.object(Path, "read_bytes", read):
            report = self.audit()
        self.assert_issue(report, "unreadable_files")
        self.assertNotIn(str(self.repo), json.dumps(report))

    def test_invalid_utf8(self):
        paths = self.sample()
        paths["txt"].write_bytes(b"\xff")
        self.assert_issue(self.audit(), "invalid_utf8_txt")

    def test_empty_and_whitespace_text(self):
        for value, code in (("", "empty_txt"), (" \t\r\n ", "whitespace_txt")):
            with self.subTest(value=value):
                self.sample(text=value)
                self.assert_issue(self.audit(), code)

    def test_text_lines_controls_and_unknown_domain(self):
        self.sample(text="Unknown opening.\r\nSynthetic\x00\u200b")
        report = self.audit()
        for code in ("multiline_txt", "txt_control_characters", "txt_nul", "unknown_text_domain"):
            self.assert_issue(report, code, "WARNING")
        self.assertEqual(report["samples"][0]["txt_line_count"], 2)

    def test_domain_disagreement_preserves_both_sources(self):
        self.sample(text="In the tunnel scene, synthetic object.")
        report = self.audit()
        self.assert_issue(report, "domain_mismatch", "WARNING")
        self.assertEqual(report["samples"][0]["folder_domain"], "power")
        self.assertEqual(report["samples"][0]["text_domain"], "tunnel")

    def test_non_polygon_and_missing_type(self):
        paths = self.sample()
        for value, severity in (("rectangle", "WARNING"), (None, "ERROR"), (123, "ERROR")):
            with self.subTest(value=value):
                self.shape(paths, shape_type=value)
                self.assert_issue(self.audit(), "non_polygon", severity)

    def test_points_structure_and_numeric_finiteness(self):
        paths = self.sample()
        for points in (None, {}, "bad", [[0]], [[0, 1, 2]], [[True, 1]], [["1", 2]],
                       [[float("nan"), 1]], [[float("inf"), 2]]):
            with self.subTest(points=points):
                self.shape(paths, points=points)
                report = self.audit()
                self.assert_issue(report, "malformed_points")
                self.assertEqual(report["summary"]["malformed_polygon"], 1)
                json.dumps(report, allow_nan=False)

    def test_fewer_than_three_points(self):
        paths = self.sample()
        self.shape(paths, points=[[0, 0], [1, 1]])
        self.assert_issue(self.audit(), "polygons_lt3_points", "WARNING")

    def test_fewer_than_three_unique_points(self):
        paths = self.sample()
        self.shape(paths, points=[[0, 0], [1, 1], [0, 0]])
        self.assert_issue(self.audit(), "polygons_lt3_unique_points", "WARNING")

    def test_zero_area_and_degenerate_union(self):
        paths = self.sample()
        self.shape(paths, points=[[0, 0], [1, 1], [2, 2]])
        report = self.audit()
        self.assert_issue(report, "zero_area_polygons", "WARNING")
        self.assertEqual(report["summary"]["degenerate_polygon"], 1)
        self.shape(paths, points=[])
        report = self.audit()
        self.assertEqual(report["summary"]["degenerate_polygon"], 1)
        self.assertEqual(report["summary"]["polygons_lt3_unique_points"], 1)

    def test_out_of_bounds_and_inclusive_boundary(self):
        paths = self.sample()
        self.shape(paths, points=[[0, 0], [8, 0], [8, 6]])
        self.assertEqual(self.audit()["summary"]["out_of_bounds_polygon"], 0)
        self.shape(paths, points=[[-0.1, 0], [8, 0], [8, 6]])
        self.assert_issue(self.audit(), "out_of_bounds_polygon", "WARNING")

    def test_large_finite_coordinates_do_not_overflow(self):
        paths = self.sample()
        self.shape(paths, points=[[10**400, 0], [0, 10**400], [0, 0]])
        report = self.audit()
        self.assert_issue(report, "out_of_bounds_polygon", "WARNING")
        self.assertEqual(report["summary"]["zero_area_polygons"], 0)

    def test_invalid_labels_and_padding(self):
        paths = self.sample()
        for value, code, severity in (("", "empty_labels", "ERROR"), (" \t", "whitespace_labels", "ERROR"),
                                      (None, "non_string_labels", "ERROR"), (" Label ", "padded_labels", "WARNING")):
            with self.subTest(value=value):
                self.shape(paths, label=value)
                self.assert_issue(self.audit(), code, severity)

    def test_unicode_and_raw_label_variants_are_lossless(self):
        paths = self.sample()
        shape = {"shape_type": "polygon", "points": [[0, 0], [1, 0], [0, 1]]}
        self.change(paths, shapes=[dict(shape, label=label) for label in ("出口", "出口", "Label", "label", " Label ")])
        report = self.audit()
        self.assertEqual(report["raw_label_frequency"], {"出口": 2, "Label": 1, "label": 1, " Label ": 1})
        self.assertEqual(report["summary"]["unicode_labels"], 2)
        self.assertEqual(report["summary"]["unique_raw_labels"], 4)
        self.assertEqual(len(report["raw_label_case_whitespace_variant_candidates"]), 1)

    def test_image_path_mismatch_and_windows_basename(self):
        paths = self.sample()
        self.change(paths, imagePath="somewhere/wrong.jpg")
        self.assert_issue(self.audit(), "image_path_mismatch", "WARNING")
        self.change(paths, imagePath="C:\\source\\" + paths["jpg"].name)
        report = self.audit()
        self.assertEqual(report["summary"]["image_path_mismatch"], 0)
        self.assertNotIn("C:\\source", json.dumps(report))

    def test_invalid_base64_and_optional_verification(self):
        paths = self.sample()
        for value in ("@@@", "出口", "a", "YWJj\n"):
            with self.subTest(value=value):
                self.change(paths, imageData=value)
                self.assert_issue(self.audit(), "image_data_invalid_base64")
                self.assertEqual(self.audit(verify=False)["summary"]["image_data_skipped"], 1)

    def test_image_data_byte_mismatch(self):
        paths = self.sample()
        self.change(paths, imageData=base64.b64encode(b"different bytes").decode("ascii"))
        report = self.audit()
        self.assert_issue(report, "image_data_mismatch", "WARNING")
        self.assertEqual(report["summary"]["image_verified"], 1)
        self.assertEqual(report["exit_code"], 0)

    def test_invalid_metadata_types_and_dimensions(self):
        paths = self.sample()
        for key, value, code in (("imagePath", None, "invalid_image_path_type"),
                                  ("imageData", 3, "invalid_image_data_type"),
                                  ("shapes", {}, "invalid_shapes"), ("shapes", [3], "malformed_shapes")):
            with self.subTest(key=key):
                paths = self.sample()
                self.change(paths, **{key: value})
                self.assert_issue(self.audit(), code)
        for key in ("imageWidth", "imageHeight"):
            for value in (0, -1, True, 1.5, "8", None):
                with self.subTest(key=key, value=value):
                    paths = self.sample()
                    self.change(paths, **{key: value})
                    self.assert_issue(self.audit(), "invalid_dimensions")

    def test_absent_optional_fields_and_empty_shapes(self):
        paths = self.sample()
        self.change(paths, shapes=[])
        annotation = json.loads(paths["json"].read_bytes())
        del annotation["imageData"], annotation["imagePath"]
        paths["json"].write_text(json.dumps(annotation), encoding="utf-8")
        report = self.audit()
        self.assertEqual(report["errors_count"], 0)
        self.assertEqual(report["summary"]["image_data_absent_or_null"], 1)

    def test_multiple_instances_and_observed_cross_table(self):
        self.sample(instance="002")
        self.sample(instance="001")
        # This contradicts the real-data observed pattern, but is not a semantic error.
        self.sample(point="power-Level01-Wheeled-000002", kind="Normal_data")
        report = self.audit()
        self.assertEqual(report["summary"]["unique_points"], 2)
        self.assertEqual(report["summary"]["instance_count_distribution"]["all"], {"1": 1, "2": 1})
        self.assertEqual(report["points"][1]["instance_ids"], ["001", "002"])
        self.assertEqual(report["summary"]["data_type_x_safety_level"]["Normal_data"]["Level01"], 1)
        self.assertEqual(report["errors_count"], 0)

    def test_nonconsecutive_instance_ids(self):
        self.sample(instance="001")
        self.sample(instance="003")
        report = self.audit()
        self.assertEqual(report["summary"]["non_consecutive_instance_sequences"], 1)
        self.assertEqual(report["points"][0]["missing_instance_ids"], ["002"])
        self.assertEqual(report["summary"]["samples_with_warnings"], 2)

    def test_duplicate_ids_flag_both_samples(self):
        self.sample(split="train")
        self.sample(split="test")
        report = self.audit()
        self.assertEqual(report["summary"]["samples_with_errors"], 2)
        self.assertEqual(report["summary"]["duplicate_sample_ids"], 2)
        self.assertEqual(report["summary"]["duplicate_point_ids"], 1)

    def test_mismatched_stems_and_parent_name(self):
        paths = self.sample()
        paths["txt"].rename(paths["txt"].with_name("wrong-001.txt"))
        report = self.audit()
        self.assertEqual(report["summary"]["total_samples"], 2)
        self.assertEqual(report["summary"]["missing_files"], 3)
        self.assert_issue(report, "invalid_metadata")

    def test_deterministic_report_and_no_mutation(self):
        self.sample()
        def fingerprint():
            return {p.relative_to(self.dataset).as_posix(): (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
                    for p in self.dataset.rglob("*") if p.is_file()}
        before = fingerprint()
        first = self.audit()
        self.assertEqual(first, self.audit())
        write_report(first, self.repo / "data/processed/report.json", self.repo)
        self.assertEqual(before, fingerprint())
        self.assertNotIn("imageData", json.dumps(first))
        self.assertNotIn("synthetic object.", json.dumps(first))
        self.assertNotIn(str(self.repo), json.dumps(first))

    def test_fingerprint_changes_for_invalid_or_missing_files(self):
        paths = self.sample()
        before = self.audit()["input_sha256"]
        paths["txt"].write_bytes(b"\xff")
        second = self.audit()["input_sha256"]
        paths["txt"].unlink()
        third = self.audit()["input_sha256"]
        self.assertEqual(len({before, second, third}), 3)

    def test_layout_failure_and_empty_dataset(self):
        self.assertEqual(self.audit()["exit_code"], 1)
        self.sample()
        (self.dataset / "test/DATA_PATH/test/Annotations/Anomaly_data").rmdir()
        report = self.audit()
        self.assertFalse(report["audit_complete"])
        self.assertEqual(report["exit_code"], 1)

    def test_output_raw_protection_and_runtime_failure(self):
        self.sample()
        report = self.audit()
        with self.assertRaises(ManifestError):
            write_report(report, self.dataset / "report.json", self.repo)
        for args in (["--output", "data/raw/report.json"], ["--output", "../escape.json"],
                     ["--dataset-root", "missing"]):
            with self.subTest(args=args), patch("scripts.validate_dataset.REPO_ROOT", self.repo), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(args), 1)

    def test_cli_warning_only_and_data_error_exit_codes(self):
        paths = self.sample(fmt="PNG")
        with patch("scripts.validate_dataset.REPO_ROOT", self.repo), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--verify-image-data"]), 0)
            paths["txt"].write_bytes(b"")
            self.assertEqual(main([]), 2)
        report = json.loads((self.repo / "data/manifests/dataset_validation.json").read_bytes())
        self.assertTrue(report["regression_discrepancies"])
        self.assertEqual(report["exit_code"], 2)
        for field in ("run_id", "created_utc", "git_commit", "git_status", "python", "platform",
                      "dependencies", "command", "source_sha256", "input_sha256"):
            self.assertIn(field, report)

    def test_strict_decoder_configuration_required(self):
        self.sample()
        with patch.object(ImageFile, "LOAD_TRUNCATED_IMAGES", True), self.assertRaises(ManifestError):
            self.audit()


if __name__ == "__main__":
    unittest.main()
