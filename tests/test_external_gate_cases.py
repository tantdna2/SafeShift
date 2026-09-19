"""Integrity and regeneration checks for locally drawn frozen protocol assets."""

from collections import Counter, defaultdict
import contextlib
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from safeshift.protocol.firewall import external_path
from safeshift.protocol.gate import load_cases, validate_suite
from scripts import generate_external_gate_cases as generator
from scripts.pre_freeze import main as gate_main

REPO = Path(__file__).resolve().parents[1]
MANIFEST = "configs/pre_freeze/external_gate_cases.v1.json"
PROVENANCE = "configs/pre_freeze/external_gate_cases.v1.provenance.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FrozenExternalCasesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases(REPO, MANIFEST)
        cls.manifest = json.loads((REPO / MANIFEST).read_bytes())
        cls.provenance = json.loads((REPO / PROVENANCE).read_bytes())

    def test_eight_cases_four_pairs_and_unique_paths(self):
        self.assertEqual(len(self.cases), 8)
        self.assertEqual(Counter(case.swap_group for case in self.cases),
                         {"A": 2, "B": 2, "C": 2, "D": 2})
        self.assertEqual(len({case.image_path for case in self.cases}), 8)

    def test_image_files_and_provenance_hashes(self):
        rows = self.provenance["images"]
        self.assertEqual(len(rows), 8)
        self.assertEqual({row["case_id"] for row in rows}, {case.case_id for case in self.cases})
        by_id = {row["case_id"]: row for row in rows}
        for case in self.cases:
            with self.subTest(case=case.case_id):
                row = by_id[case.case_id]
                self.assertEqual(row["image_path"], case.image_path)
                image_path = external_path(REPO, case.image_path)
                self.assertTrue(image_path.is_file())
                self.assertEqual(digest(image_path), row["sha256"])

    def test_manifest_and_generator_checksums(self):
        self.assertEqual(self.provenance["manifest_path"], MANIFEST)
        self.assertEqual(digest(REPO / MANIFEST), self.provenance["manifest_sha256"])
        self.assertEqual(self.provenance["generator_script_path"], generator.SCRIPT)
        self.assertEqual(digest(REPO / generator.SCRIPT), self.provenance["generator_script_sha256"])

    def test_only_safe_repository_relative_paths(self):
        paths = [case.image_path for case in self.cases]
        paths += [row["image_path"] for row in self.provenance["images"]]
        paths += [MANIFEST, PROVENANCE, self.provenance["generator_script_path"]]
        for value in paths:
            with self.subTest(path=value):
                path = PurePosixPath(value)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertNotIn("\\", value)
                self.assertNotIn("inspecsafe", value.casefold())
                self.assertNotIn("data/raw", value.casefold())
                self.assertTrue(external_path(REPO, value).is_relative_to(REPO))

    def test_boxes_valid_strictly_separated_and_reciprocal(self):
        groups = defaultdict(list)
        for case in self.cases:
            for box in (case.target_gt_bbox, case.distractor_gt_bbox):
                self.assertTrue(all(0 <= coordinate <= 1 for coordinate in box))
                self.assertLess(box[0], box[2])
                self.assertLess(box[1], box[3])
            a, b = case.target_gt_bbox, case.distractor_gt_bbox
            self.assertTrue(a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])
            groups[case.swap_group].append(case)
        for a, b in groups.values():
            self.assertEqual(a.target_query, b.target_query)
            self.assertEqual(a.target_gt_bbox, b.distractor_gt_bbox)
            self.assertEqual(a.distractor_gt_bbox, b.target_gt_bbox)

    def test_horizontal_vertical_and_both_diagonals(self):
        motions = set()
        for case in self.cases:
            a, b = case.target_gt_bbox, case.distractor_gt_bbox
            dx, dy = b[0] - a[0], b[1] - a[1]
            motions.add("vertical" if dx == 0 else "horizontal" if dy == 0
                        else "diagonal_positive" if dx * dy > 0 else "diagonal_negative")
        self.assertEqual(motions, {"horizontal", "vertical", "diagonal_positive", "diagonal_negative"})

    def test_actual_pixels_match_ground_truth_and_have_only_three_colors(self):
        cases = {case.case_id: case for case in self.cases}
        for row in self.provenance["images"]:
            with self.subTest(case=row["case_id"]), Image.open(REPO / row["image_path"]) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.mode, "RGB")
                self.assertEqual(image.size, (256, 256))
                self.assertEqual((row["width"], row["height"]), image.size)
                self.assertEqual(image.info, {})
                colors = {rgb for count, rgb in image.getcolors(maxcolors=4)}
                self.assertEqual(colors, {(255, 255, 255), tuple(row["target_rgb"]), tuple(row["distractor_rgb"])})
                pixels = image.load()
                for role in ("target", "distractor"):
                    rgb = tuple(row[f"{role}_rgb"])
                    points = [(x, y) for y in range(image.height) for x in range(image.width)
                              if pixels[x, y] == rgb]
                    actual = [min(x for x, y in points), min(y for x, y in points),
                              max(x for x, y in points) + 1, max(y for x, y in points) + 1]
                    self.assertEqual(actual, row[f"{role}_pixel_bbox"])
                    self.assertEqual(tuple(v / 256 for v in actual),
                                     getattr(cases[row["case_id"]], f"{role}_gt_bbox"))

    def test_regeneration_matches_all_frozen_image_and_manifest_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generator.generate(root)
            expected_files = {case.image_path for case in self.cases} | {MANIFEST}
            self.assertEqual({p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()},
                             expected_files)
            for path in expected_files:
                with self.subTest(path=path):
                    self.assertEqual(digest(root / path), digest(REPO / path))

    def test_existing_validator_and_cli_accept_frozen_suite(self):
        validate_suite(REPO, self.cases)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = gate_main(["validate-cases", "--manifest", MANIFEST])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue()),
                         {"status": "FORMAT_VALID", "case_count": 8, "live_gate": "NOT RUN"})

    def test_validator_rejects_broken_swaps_and_changed_query(self):
        original = self.cases[0]
        for broken in (replace(original, target_query="Locate the distractor."),
                       replace(original, target_gt_bbox=(0.01, 0.01, 0.1, 0.1)),
                       replace(original, target_gt_bbox=original.distractor_gt_bbox)):
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                validate_suite(REPO, (broken, *self.cases[1:]))

    def test_generator_rejects_unsafe_output_before_generation(self):
        for path in ("data/raw/forbidden", "InspecSafe-copy", "../outside", "C:/absolute"):
            with self.subTest(path=path), patch.object(generator, "generate") as generate:
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(generator.main(["--output-dir", path]), 2)
                generate.assert_not_called()

    def test_provenance_and_freeze_template_keep_scope(self):
        self.assertEqual(self.manifest["source_kind"], "synthetic")
        self.assertEqual(self.provenance["source_kind"], "synthetic")
        self.assertEqual(self.provenance["statement"], "NO_INSPECSAFE_CONTENT_USED")
        self.assertEqual(self.provenance["suite_version"], "synthetic-v1")
        self.assertEqual(self.provenance["generator_script_version"], generator.VERSION)
        self.assertEqual(self.provenance["deterministic_regeneration"]["status"], "PASS")
        self.assertTrue(self.provenance["deterministic_regeneration"]["all_image_hashes_reproduced"])
        for field in ("schema_version", "generation_command", "python_version", "pillow_version"):
            self.assertTrue(self.provenance[field])
        self.assertRegex(self.provenance["git_commit_used_to_generate"], r"^[0-9a-f]{40}$")
        template = json.loads((REPO / "configs/pre_freeze/freeze_manifest.template.json").read_bytes())
        self.assertEqual(template["external_case_manifest_sha256"], digest(REPO / MANIFEST))
        self.assertEqual(template["external_case_suite_version"], "synthetic-v1")
        self.assertEqual(template["protocol_freeze_commit_sha"], "PENDING")
        self.assertEqual(template["final_model_roles"], "PENDING")
        self.assertEqual(template["external_gate_artifacts"], {"openai": "NOT RUN", "anthropic": "NOT RUN"})


if __name__ == "__main__":
    unittest.main()
