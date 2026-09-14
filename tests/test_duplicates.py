"""Small generated fixtures only. No real InspecSafe samples or metadata."""

import base64
import contextlib
import hashlib
import io
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageFile, PngImagePlugin

from safeshift.data.duplicates import (
    audit_duplicates, candidate_indices, dhash, embedded_hash, image_path_metadata,
    normalized_mae, pixel_sha256, write_report,
)
from safeshift.data.manifest import ManifestError
from safeshift.data.validation import validate_dataset
from scripts.audit_duplicates import main


def gradient(reverse=False):
    image = Image.new("L", (9, 8))
    image.putdata([255 - x * 25 if reverse else x * 25 for y in range(8) for x in range(9)])
    return image


class DuplicateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name).resolve()
        self.dataset = self.repo / "data/raw/InspecSafe-V1"
        for split in ("train", "test"):
            for kind in ("Normal_data", "Anomaly_data"):
                (self.dataset / split / "DATA_PATH" / split / "Annotations" / kind).mkdir(parents=True)

    def sample(self, point=1, *, split="train", instance=1, reverse=False, image=None,
               image_path=None, png_note=None, kind="Normal_data", domain="power"):
        folder = f"{domain}-Level04-Wheeled-{point:06d}"
        directory = self.dataset / split / "DATA_PATH" / split / "Annotations" / kind / folder
        directory.mkdir(exist_ok=True)
        stem = f"{folder}-{instance:03d}"
        paths = {ext: directory / f"{stem}.{ext}" for ext in ("jpg", "json", "txt")}
        image = image if image is not None else gradient(reverse)
        info = PngImagePlugin.PngInfo()
        if png_note:
            info.add_text("synthetic", png_note)
        image.save(paths["jpg"], format="PNG", pnginfo=info)
        annotation = {"imagePath": image_path or f"synthetic{point}_frame_{instance:06d}.jpg",
                      "imageData": base64.b64encode(paths["jpg"].read_bytes()).decode("ascii"),
                      "imageWidth": image.width, "imageHeight": image.height, "shapes": []}
        paths["json"].write_text(json.dumps(annotation), encoding="utf-8")
        paths["txt"].write_text("In the power facility scene, synthetic fixture.", encoding="utf-8")
        return paths

    def audit(self, **kwargs):
        return audit_duplicates(self.dataset, self.repo, **kwargs)

    def change_embedded(self, paths, value, *, remove=False):
        annotation = json.loads(paths["json"].read_bytes())
        annotation["imageData"] = value
        if remove:
            annotation.pop("imageData")
        paths["json"].write_text(json.dumps(annotation), encoding="utf-8")

    def test_no_duplicate_dataset(self):
        self.sample()
        self.sample(2, reverse=True, split="test")
        report = self.audit()
        self.assertEqual(report["summary"]["exact_byte"]["pairs"], 0)
        self.assertEqual(report["summary"]["pixel_exact"]["pairs"], 0)
        self.assertEqual(report["near_pair_evidence"], [])

    def test_byte_identical_within_train(self):
        self.sample()
        self.sample(2)
        result = self.audit()["summary"]["exact_byte"]
        self.assertEqual(result["pairs"], 1)
        self.assertEqual(result["within_train_pairs"], 1)
        self.assertEqual(result["cross_split_pairs"], 0)

    def test_byte_identical_cross_split_is_success(self):
        self.sample()
        self.sample(2, split="test")
        report = self.audit()
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["summary"]["exact_byte"]["cross_split_pairs"], 1)
        self.assertEqual(report["summary"]["exact_byte"]["different_point_cross_split_pairs"], 1)
        self.assertEqual(report["exact_pair_evidence"][0]["evidence_type"], "CONFIRMED_EXACT_BYTE")

    def test_group_size_combinations(self):
        for n in range(1, 5):
            self.sample(n, split="test" if n == 4 else "train")
            summary = self.audit()["summary"]["exact_byte"]
            with self.subTest(size=n):
                self.assertEqual(summary["pairs"], n * (n - 1) // 2)
                self.assertEqual(summary["largest_group_size"], n if n > 1 else 0)
                if n == 4:
                    self.assertEqual(summary["cross_split_pairs"], 3)
                    self.assertEqual(summary["group_size_distribution"], {"4": 1})

    def test_byte_different_pixel_exact_fixture(self):
        self.sample(png_note="first")
        self.sample(2, png_note="second", split="test")
        report = self.audit()
        a, b = report["samples"]
        self.assertNotEqual(a["byte_sha256"], b["byte_sha256"])
        self.assertEqual(a["pixel_sha256"], b["pixel_sha256"])
        self.assertEqual(report["summary"]["exact_byte"]["pairs"], 0)
        pixel = report["summary"]["pixel_exact"]
        self.assertEqual(pixel["pairs"], 1)
        self.assertEqual(pixel["byte_different_pairs"], 1)
        self.assertEqual(pixel["cross_split_pairs"], 1)
        self.assertEqual(report["exact_pair_evidence"][0]["evidence_type"], "CONFIRMED_PIXEL_EXACT")

    def test_distinct_pixels(self):
        self.assertNotEqual(pixel_sha256(gradient()), pixel_sha256(gradient(True)))

    def test_pixel_serialization_dimensions_and_rgb(self):
        image = Image.new("L", (2, 3), 40)
        expected = hashlib.sha256(struct.pack(">QQ", 2, 3) + bytes([40] * 18)).hexdigest()
        self.assertEqual(pixel_sha256(image), expected)
        self.assertNotEqual(pixel_sha256(image), pixel_sha256(Image.new("L", (3, 2), 40)))
        self.assertEqual(pixel_sha256(image), pixel_sha256(image.convert("RGB")))

    def test_exif_orientation_not_applied(self):
        image = gradient()
        expected = pixel_sha256(image)
        image.getexif()[274] = 6
        self.assertEqual(pixel_sha256(image), expected)
        self.assertEqual(dhash(image), 0)

    def test_dhash_deterministic_known_integer(self):
        self.assertEqual(dhash(gradient()), 0)
        self.assertEqual(dhash(gradient(True)), 2**64 - 1)

    def test_dhash_deterministic_between_processes(self):
        code = "from PIL import Image; from safeshift.data.duplicates import dhash; " \
               "im=Image.new('L',(9,8)); im.putdata([255-x*25 for y in range(8) for x in range(9)]); print(dhash(im))"
        root = Path(__file__).resolve().parents[1]
        results = [subprocess.check_output([sys.executable, "-c", code], cwd=root, text=True).strip() for _ in range(2)]
        self.assertEqual(results, [str(2**64 - 1)] * 2)

    def test_identical_images_distance_zero(self):
        self.assertEqual((dhash(gradient()) ^ dhash(gradient())).bit_count(), 0)

    def test_small_change_one_known_bit(self):
        image = gradient()
        image.putpixel((0, 0), 26)
        self.assertEqual(dhash(image), 1 << 63)
        self.assertEqual((dhash(image) ^ dhash(gradient())).bit_count(), 1)

    def test_hamming_threshold_filter_and_full_sweep(self):
        samples = [{"dhash": h, "split": split} for h, split in ((0, "train"), (3, "train"), (7, "test"))]
        candidates, sweep = candidate_indices(samples, 1)
        self.assertEqual(candidates, [(1, 2)])
        self.assertEqual(sweep["0"]["pairs"], 0)
        self.assertEqual(sweep["2"]["pairs"], 2)
        self.assertEqual(sweep["4"]["pairs"], 3)
        self.assertEqual(sweep["2"]["cross_split_pairs"], 1)

    def test_pair_no_double_count_and_canonical_order(self):
        for point in (3, 1, 2):
            self.sample(point)
        pairs = self.audit()["near_pair_evidence"]
        keys = [(p["sample_id_a"], p["sample_id_b"]) for p in pairs]
        self.assertEqual(len(keys), 3)
        self.assertEqual(len(set(keys)), 3)
        self.assertEqual(keys, sorted(keys))
        self.assertTrue(all(a < b for a, b in keys))

    def test_same_point_consecutive_detection(self):
        for instance in (4, 2, 1, 3):
            self.sample(instance=instance)
        report = self.audit()
        self.assertEqual(report["summary"]["sequential_reference"]["pair_count"], 3)
        self.assertEqual(report["summary"]["exact_byte"]["same_point_pairs"], 6)
        self.assertEqual(report["summary"]["sequential_reference"]["mae"]["max"], 0)

    def test_nonconsecutive_no_fake_adjacency(self):
        self.sample(instance=1)
        self.sample(instance=3)
        self.assertEqual(self.audit()["sequential_pair_evidence"], [])

    def test_adjacency_does_not_cross_point_or_split(self):
        self.sample(instance=1)
        self.sample(instance=2, split="test")
        self.sample(2, instance=2)
        self.assertEqual(self.audit()["sequential_pair_evidence"], [])

    def test_point_overlap_and_duplicate_stem_retained(self):
        self.sample()
        self.sample(split="test")
        report = self.audit()
        self.assertEqual(report["summary"]["dataset"]["total_samples"], 2)
        self.assertEqual(report["metadata_source_evidence"]["point_id_overlap"], ["000001"])
        self.assertEqual(report["summary"]["metadata"]["point_folder_identity_overlap_count"], 1)
        pair = report["exact_pair_evidence"][0]
        self.assertTrue(pair["same_point"])
        self.assertFalse(pair["same_point_folder"])
        self.assertLess((pair["sample_id_a"], pair["image_relpath_a"]), (pair["sample_id_b"], pair["image_relpath_b"]))

    def test_point_id_overlap_independent_of_folder_identity(self):
        self.sample()
        self.sample(split="test", domain="tunnel")
        summary = self.audit()["summary"]
        self.assertEqual(summary["metadata"]["point_id_overlap_count"], 1)
        self.assertEqual(summary["metadata"]["point_folder_identity_overlap_count"], 0)
        self.assertEqual(summary["exact_byte"]["cross_domain_pairs"], 1)

    def test_no_point_overlap(self):
        self.sample()
        self.sample(2, split="test")
        self.assertEqual(self.audit()["metadata_source_evidence"]["point_id_overlap"], [])

    def test_exact_image_path_cross_split(self):
        self.sample(image_path="shared_frame_000001.jpg")
        self.sample(2, split="test", image_path="shared_frame_000001.jpg")
        result = self.audit()["summary"]["metadata"]
        self.assertEqual(result["image_path"]["duplicate_groups"], 1)
        self.assertEqual(result["image_path"]["groups_spanning_splits"], 1)

    def test_windows_and_unix_separators_preserve_exact_string(self):
        win = image_path_metadata(r"C:\upstream\synthetic_frame_000001.jpg")
        unix = image_path_metadata("/upstream/synthetic_frame_000001.jpg")
        self.assertEqual(win["image_path_basename"], unix["image_path_basename"])
        self.assertEqual(win["source_family"], unix["source_family"])
        self.assertNotEqual(win["image_path_sha256"], unix["image_path_sha256"])
        self.sample(image_path=r"C:\upstream\synthetic_frame_000001.jpg")
        self.sample(2, split="test", image_path="/upstream/synthetic_frame_000001.jpg")
        result = self.audit()["summary"]["metadata"]
        self.assertEqual(result["image_path"]["duplicate_groups"], 0)
        self.assertEqual(result["image_path_basename"]["groups_spanning_splits"], 1)

    def test_source_family_conservative_parsing(self):
        a = image_path_metadata("source12_frame_000001.jpg")["source_family"]
        b = image_path_metadata("source12_frame_000002.jpg")["source_family"]
        self.assertEqual(a, b)
        self.assertEqual(a, hashlib.sha256(b"source12").hexdigest())
        self.assertNotEqual(a, image_path_metadata("source13_frame_000001.jpg")["source_family"])

    def test_unknown_source_pattern_returns_null(self):
        for value in (None, "", 3, "video123.jpg", "source_frame_1_copy.jpg", "source_FRAME_1.jpg", "_frame_1.jpg"):
            with self.subTest(value=value):
                self.assertIsNone(image_path_metadata(value)["source_family"])

    def test_source_family_cross_split_group(self):
        self.sample(image_path="source_frame_000001.jpg")
        self.sample(2, split="test", image_path="source_frame_000002.jpg")
        metadata = self.audit()["summary"]["metadata"]
        self.assertEqual(metadata["source_family"]["groups_spanning_splits"], 1)
        self.assertEqual(metadata["image_path"]["duplicate_groups"], 0)

    def test_embedded_exact_duplicates_secondary(self):
        self.sample()
        other = self.sample(2, reverse=True)
        first = next(self.dataset.rglob("*000001-001.json"))
        self.change_embedded(other, json.loads(first.read_bytes())["imageData"])
        report = self.audit()
        self.assertEqual(report["summary"]["embedded"]["pairs"], 1)
        self.assertEqual(report["summary"]["exact_byte"]["pairs"], 0)

    def test_embedded_cross_split(self):
        self.sample()
        self.sample(2, split="test")
        summary = self.audit()["summary"]["embedded"]
        self.assertEqual(summary["checked"], 2)
        self.assertEqual(summary["unique_hashes"], 1)
        self.assertEqual(summary["groups_spanning_splits"], 1)
        self.assertEqual(summary["cross_split_pairs"], 1)

    def test_invalid_base64_safe_and_not_grouped(self):
        for value in ("%%%", "YWJj\n", "data:image/png;base64,YWJj", "é"):
            with self.subTest(value=value):
                self.assertEqual(embedded_hash(value), (None, "invalid_base64"))
        a = self.sample()
        b = self.sample(2)
        self.change_embedded(a, "%%%")
        self.change_embedded(b, "%%%")
        result = self.audit()
        self.assertEqual(result["summary"]["embedded"]["invalid_base64"], 2)
        self.assertEqual(result["summary"]["embedded"]["duplicate_groups"], 0)
        self.assertEqual(result["exit_code"], 0)

    def test_missing_null_empty_wrong_type_embedded(self):
        for i, (value, remove, status) in enumerate(((None, True, "absent_or_null"), (None, False, "absent_or_null"),
                                                    ("", False, "empty"), (123, False, "invalid_type")), 1):
            paths = self.sample(i)
            self.change_embedded(paths, value, remove=remove)
        summary = self.audit()["summary"]["embedded"]
        self.assertEqual(summary["absent_or_null"], 2)
        self.assertEqual(summary["empty"], 1)
        self.assertEqual(summary["invalid_type"], 1)
        self.assertEqual(summary["checked"], 0)

    def test_raw_files_unchanged(self):
        self.sample()
        self.sample(2, split="test")
        def hashes():
            return {p.relative_to(self.repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.dataset.rglob("*") if p.is_file()}
        before = hashes()
        self.audit()
        self.assertEqual(hashes(), before)

    def test_report_no_absolute_machine_or_upstream_path(self):
        self.sample(image_path=r"C:\private\source_frame_1.jpg")
        report = self.audit()
        payload = write_report(report, Path("data/manifests/audit.json"), self.repo, runtime_seconds=1)
        text = json.dumps(payload)
        self.assertNotIn(str(self.repo), text)
        self.assertNotIn("C:", text)
        self.assertNotIn("private", text)
        self.assertEqual(payload["command"][3], "data/raw/InspecSafe-V1")

    def test_report_ordering_deterministic(self):
        self.sample(3)
        self.sample(1, split="test")
        self.sample(2)
        self.assertEqual(json.dumps(self.audit()), json.dumps(self.audit()))

    def test_fingerprint_matches_validation_serialization(self):
        self.sample()
        self.sample(2, split="test")
        self.assertEqual(self.audit()["input_sha256"], validate_dataset(self.dataset, self.repo)["input_sha256"])

    def test_mae_range_and_known_value(self):
        black = Image.new("L", (256, 256), 0)
        white = Image.new("L", (256, 256), 255)
        self.assertEqual(normalized_mae(black, black), 0)
        self.assertEqual(normalized_mae(black, white), 1)
        self.assertAlmostEqual(normalized_mae(black, Image.new("L", (256, 256), 51)), .2)
        with self.assertRaises(ValueError):
            normalized_mae(gradient(), white)

    def test_low_dhash_is_only_candidate_even_for_high_mae(self):
        self.sample(image=Image.new("L", (9, 8), 0))
        self.sample(2, split="test", image=Image.new("L", (9, 8), 255))
        pair = self.audit()["near_pair_evidence"][0]
        self.assertEqual(pair["dhash_distance"], 0)
        self.assertEqual(pair["normalized_mae"], 1)
        self.assertEqual(pair["evidence_type"], "HIGH_SIMILARITY_CANDIDATE")

    def test_empty_or_structurally_incomplete_dataset_fails(self):
        with self.assertRaises(ManifestError):
            self.audit()
        self.sample()
        (self.dataset / "test/DATA_PATH/test/Annotations/Normal_data").rmdir()
        with self.assertRaises(ManifestError):
            self.audit()

    def test_missing_triplet_fails(self):
        paths = self.sample()
        paths["txt"].unlink()
        with self.assertRaises(OSError):
            self.audit()

    def test_corrupt_image_and_json_fail(self):
        paths = self.sample()
        original = paths["jpg"].read_bytes()
        paths["jpg"].write_bytes(b"broken")
        with self.assertRaises(OSError):
            self.audit()
        paths["jpg"].write_bytes(original)
        for raw in ("{bad", "[]", "null"):
            paths["json"].write_text(raw, encoding="utf-8")
            with self.assertRaises(ManifestError):
                self.audit()

    def test_invalid_threshold_and_permissive_decode_rejected(self):
        self.sample()
        for value in (-1, 65, True, 2.5):
            with self.assertRaises(ManifestError):
                self.audit(max_hamming=value)
        with patch.object(ImageFile, "LOAD_TRUNCATED_IMAGES", True), self.assertRaises(ManifestError):
            self.audit()

    def test_output_protection_and_cli_failure_stale_output(self):
        self.sample()
        report = self.audit()
        for output in (self.dataset / "report.json", self.repo / "data/raw/report.json", Path("../escape.json"), Path("report.txt")):
            with self.assertRaises(ManifestError):
                write_report(report, output, self.repo, runtime_seconds=0)
        output = self.repo / "data/manifests/audit.json"
        output.parent.mkdir(parents=True)
        output.write_text("old", encoding="utf-8")
        with patch("scripts.audit_duplicates.REPO_ROOT", self.repo), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--dataset-root", "missing", "--output", "data/manifests/audit.json"]), 1)
        self.assertEqual(output.read_text(), "old")

    def test_cli_success_with_cross_split_findings(self):
        self.sample()
        self.sample(2, split="test")
        with patch("scripts.audit_duplicates.REPO_ROOT", self.repo), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            code = main(["--output", "data/manifests/audit.json", "--max-hamming", "8"])
        self.assertEqual(code, 0)
        report = json.loads((self.repo / "data/manifests/audit.json").read_bytes())
        self.assertEqual(report["summary"]["exact_byte"]["cross_split_pairs"], 1)


if __name__ == "__main__":
    unittest.main()
