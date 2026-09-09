"""Tiny synthetic triplets exercise validation and lossless serialization."""

import contextlib
import csv
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from safeshift.data.manifest import (
    FIELDS, ManifestError, TEXT_OPENINGS, collect_manifest, infer_text_domain,
    repository_path, write_manifest,
    write_provenance,
)
from scripts.build_manifest import main


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name).resolve()
        self.dataset = self.repo / "data/raw/InspecSafe-V1"
        for split in ("train", "test"):
            for data_type in ("Normal_data", "Anomaly_data"):
                (self.dataset / split / "DATA_PATH" / split / "Annotations" / data_type).mkdir(parents=True)

    def sample(self, *, point="power-Level04-Wheeled-000001", instance="001",
               split="train", data_type="Normal_data", text=None, labels=None,
               image=b"\xff\xd8\xff\xe0synthetic-header-only", width=2, height=3):
        directory = self.dataset / split / "DATA_PATH" / split / "Annotations" / data_type / point
        directory.mkdir(exist_ok=True)
        stem = f"{point}-{instance}"
        (directory / f"{stem}.jpg").write_bytes(image)
        (directory / f"{stem}.json").write_text(json.dumps({
            "imageWidth": width, "imageHeight": height,
            "shapes": [{"label": label} for label in (["Synthetic Object"] if labels is None else labels)],
            "imageData": "SYNTHETIC_BASE64_DO_NOT_EXPORT",
        }, ensure_ascii=False), encoding="utf-8")
        (directory / f"{stem}.txt").write_bytes((
            "In the power facility scene, a synthetic object stands here." if text is None else text
        ).encode("utf-8"))
        return directory, stem

    def collect(self):
        return collect_manifest(self.dataset, self.repo)

    def test_valid_sample(self):
        _, stem = self.sample()
        result = self.collect()
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.rows), 1)
        row = result.rows[0]
        self.assertEqual(set(row), set(FIELDS))
        self.assertEqual(row["sample_id"], stem)
        for key, expected in {
            "point_id": "000001", "instance_id": "001", "split": "train",
            "data_type": "Normal_data", "folder_domain": "power", "text_domain": "power",
            "safety_level": "Level04", "safety_level_int": 4, "robot_platform": "Wheeled",
            "image_width": 2, "image_height": 3, "image_format": "JPEG", "num_shapes": 1,
        }.items():
            self.assertEqual(row[key], expected)
        self.assertIs(row["domain_mismatch"], False)
        self.assertIs(row["has_other_modalities"], False)
        for key in ("image_relpath", "json_relpath", "txt_relpath"):
            self.assertFalse(Path(row[key]).is_absolute())
            self.assertNotIn("\\", row[key])

    def test_malformed_folder(self):
        self.sample(point="bad-folder")
        result = self.collect()
        self.assertEqual(result.incomplete_malformed, 1)
        self.assertIn("malformed folder name", result.errors[0])

    def test_missing_each_triplet_member_including_orphan_annotations(self):
        directory, stem = self.sample()
        for suffix in ("txt", "json", "jpg"):
            with self.subTest(suffix=suffix):
                path = directory / f"{stem}.{suffix}"
                original = path.read_bytes()
                path.unlink()
                result = self.collect()
                self.assertEqual(result.incomplete_malformed, 1)
                self.assertIn(f"missing {suffix}", result.errors[0])
                path.write_bytes(original)

    def test_mismatched_stems(self):
        directory, stem = self.sample()
        (directory / f"{stem}.txt").rename(directory / f"{directory.name}-002.txt")
        result = self.collect()
        self.assertEqual(len(result.rows), 0)
        self.assertEqual(result.discovered_samples, 2)
        self.assertEqual(result.incomplete_malformed, 2)
        self.assertTrue(all("triplet stems must match" in error for error in result.errors))

    def test_triplet_stem_must_match_parent(self):
        directory, stem = self.sample()
        for suffix in ("jpg", "json", "txt"):
            (directory / f"{stem}.{suffix}").rename(directory / f"power-Level04-Wheeled-000002-001.{suffix}")
        self.assertIn("sample stem does not match", self.collect().errors[0])

    def test_png_with_jpg_extension(self):
        # Signature identification does not claim to decode image pixels.
        self.sample(image=b"\x89PNG\r\n\x1a\nsynthetic-header-only")
        result = self.collect()
        self.assertFalse(result.errors)
        self.assertEqual(result.rows[0]["image_format"], "PNG")
        self.assertEqual(result.summary()["PNG"], 1)

    def test_unknown_text_domain_and_later_keywords(self):
        for text in ("Unknown scene. In the power scenario, an object exists.",
                     "In the tunnel-like scene, there is a power cabinet.",
                     "In the power scenarioX, a synthetic object stands.", ""):
            with self.subTest(text=text):
                self.sample(text=text)
                row = self.collect().rows[0]
                self.assertIsNone(row["text_domain"])
                self.assertIsNone(row["domain_mismatch"])

    def test_all_documented_openings(self):
        for domain, openings in TEXT_OPENINGS.items():
            for opening in openings:
                with self.subTest(opening=opening):
                    self.assertEqual(infer_text_domain(opening + " synthetic details."), domain)
                    self.assertIsNone(infer_text_domain("Uncertain. " + opening))

    def test_domain_mismatch_does_not_choose_ground_truth(self):
        self.sample(text="In the oil, gas, and chemical plant scene, a utility tunnel exists.")
        row = self.collect().rows[0]
        self.assertEqual(row["folder_domain"], "power")
        self.assertEqual(row["text_domain"], "oil_chemical")
        self.assertIs(row["domain_mismatch"], True)

    def test_unicode_and_duplicate_raw_labels(self):
        labels = ["出口", "  Raw Label  ", "出口", "Repeated", "Repeated"]
        self.sample(labels=labels)
        row = self.collect().rows[0]
        self.assertEqual(row["object_labels"], labels)
        self.assertEqual(row["num_shapes"], len(labels))

    def test_lossless_csv_roundtrip(self):
        text = '\ufeff  Unknown opening, "quoted".\r\nSecond line\rThird line\n  '
        labels = ["出口", 'Label, with "quote"', "出口"]
        self.sample(text=text, labels=labels)
        result = self.collect()
        self.assertEqual(result.rows[0]["text_description"], text)
        output = self.repo / "data/manifests/test.csv"
        write_manifest(result, output)
        with output.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["text_description"], text)
        self.assertEqual(json.loads(rows[0]["object_labels"]), labels)
        self.assertIsNone(json.loads(rows[0]["text_domain"]))
        self.assertIsNone(json.loads(rows[0]["domain_mismatch"]))
        self.assertEqual(rows[0]["point_id"], "000001")
        self.assertNotIn("imageData", output.read_text(encoding="utf-8"))
        self.assertNotIn("SYNTHETIC_BASE64", output.read_text(encoding="utf-8"))

    def test_invalid_json(self):
        directory, stem = self.sample()
        for content in ("{broken", "[]", "null"):
            with self.subTest(content=content):
                (directory / f"{stem}.json").write_text(content, encoding="utf-8")
                result = self.collect()
                self.assertEqual(result.incomplete_malformed, 1)
                self.assertIn("JSON", result.errors[0])

    def test_invalid_dimensions(self):
        for key in ("width", "height"):
            for value in (None, 0, -1, True, 2.5, "12"):
                with self.subTest(key=key, value=value):
                    self.sample(**{key: value})
                    result = self.collect()
                    self.assertEqual(result.incomplete_malformed, 1)
                    self.assertIn("positive integer", result.errors[0])

    def test_invalid_shapes_and_empty_shapes(self):
        directory, stem = self.sample(labels=[])
        self.assertEqual(self.collect().rows[0]["num_shapes"], 0)
        for shapes in (None, {}, [None], [{}], [{"label": 123}]):
            with self.subTest(shapes=shapes):
                (directory / f"{stem}.json").write_text(json.dumps({
                    "shapes": shapes, "imageWidth": 1, "imageHeight": 1,
                }), encoding="utf-8")
                self.assertEqual(self.collect().incomplete_malformed, 1)

    def test_bad_magic_and_invalid_utf8(self):
        directory, stem = self.sample(image=b"not an image")
        self.assertIn("magic bytes", self.collect().errors[0])
        self.sample()
        (directory / f"{stem}.txt").write_bytes(b"\xff")
        self.assertIn("UTF-8", self.collect().errors[0])

    def test_multiple_instances_and_modalities_presence(self):
        directory, _ = self.sample(instance="002")
        self.sample(instance="001")
        modality_dir = directory.parents[2] / "Other_modalities" / directory.name
        modality_dir.mkdir(parents=True)
        self.assertFalse(self.collect().rows[0]["has_other_modalities"])
        (modality_dir / f"{directory.name}-sensor.txt").write_text("synthetic")
        result = self.collect()
        self.assertEqual([row["instance_id"] for row in result.rows], ["001", "002"])
        self.assertTrue(all(row["has_other_modalities"] for row in result.rows))

    def test_duplicate_sample_id(self):
        self.sample(split="train")
        self.sample(split="test")
        self.assertIn("duplicate sample_id", self.collect().errors[0])

    def test_missing_layout_and_unexpected_entries(self):
        missing = self.dataset / "test/DATA_PATH/test/Annotations/Anomaly_data"
        missing.rmdir()
        result = self.collect()
        self.assertTrue(any("missing data_type directory" in error for error in result.errors))
        missing.mkdir()
        directory, _ = self.sample()
        (directory / "unexpected.bin").write_bytes(b"unexpected")
        self.assertTrue(self.collect().errors)

    def test_failed_build_preserves_existing_output(self):
        directory, stem = self.sample()
        (directory / f"{stem}.txt").unlink()
        output = self.repo / "existing.csv"
        output.write_bytes(b"previous valid manifest")
        with self.assertRaises(ManifestError):
            write_manifest(self.collect(), output)
        self.assertEqual(output.read_bytes(), b"previous valid manifest")

    def test_fingerprint_and_csv_are_deterministic_and_sensitive_to_input(self):
        self.sample()
        first, second = self.collect(), self.collect()
        self.assertEqual(first.input_sha256, second.input_sha256)
        output = self.repo / "test.csv"
        write_manifest(first, output)
        before = output.read_bytes()
        write_manifest(second, output)
        self.assertEqual(before, output.read_bytes())
        self.sample(text="Changed synthetic content")
        self.assertNotEqual(first.input_sha256, self.collect().input_sha256)

    def test_path_outside_repository_rejected(self):
        with self.assertRaises(ManifestError):
            repository_path(Path("../escape.csv"), self.repo)

    def test_cli_reports_discrepancy_without_forcing_counts(self):
        self.sample()
        output = io.StringIO()
        errors = io.StringIO()
        with patch("scripts.build_manifest.REPO_ROOT", self.repo), \
             patch("scripts.build_manifest.write_provenance") as provenance, \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = main([])
        self.assertEqual(status, 2)
        self.assertIn('"total_samples": 1', output.getvalue())
        self.assertIn("W1 DISCREPANCY: total_samples: expected 5013, observed 1", errors.getvalue())
        self.assertTrue((self.repo / "data/manifests/dataset_manifest.csv").is_file())
        provenance.assert_called_once()

    def test_cli_errors_and_raw_output_protection(self):
        directory, stem = self.sample()
        (directory / f"{stem}.json").unlink()
        for args in ([], ["--output", "data/raw/unsafe.csv"]):
            with self.subTest(args=args), patch("scripts.build_manifest.REPO_ROOT", self.repo), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(main(args), 1)
                self.assertIn("ERROR:", errors.getvalue())
        self.assertFalse((self.repo / "data/manifests/dataset_manifest.csv").exists())

    def test_empty_dataset_cannot_publish(self):
        result = self.collect()
        self.assertIn("no sample candidates found", result.errors[0])
        with self.assertRaises(ManifestError):
            write_manifest(result, self.repo / "empty.csv")

    def test_provenance_covers_artifact_and_source_bytes(self):
        self.sample()
        for name in ("safeshift/data/manifest.py", "scripts/build_manifest.py", "notes/dataset_schema.md"):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic source", encoding="utf-8")
        result = self.collect()
        output = self.repo / "manifest.csv"
        write_manifest(result, output)
        write_provenance(result, self.dataset, output, self.repo)
        provenance = json.loads(output.with_suffix(".provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["input_sha256"], result.input_sha256)
        self.assertEqual(provenance["output_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
        self.assertEqual(provenance["source_sha256"]["scripts/build_manifest.py"],
                         hashlib.sha256(b"synthetic source").hexdigest())
        self.assertEqual(provenance["dataset_root"], "data/raw/InspecSafe-V1")
        self.assertEqual(provenance["output"], "manifest.csv")
        self.assertEqual(provenance["summary"]["total_samples"], 1)


if __name__ == "__main__":
    unittest.main()
