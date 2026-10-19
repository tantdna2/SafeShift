"""CPU fixtures: eight generated JPEGs, bounded discovery and released Run All."""
import ast
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from PIL import Image

from safeshift.diagnostics.resource_pilot import bootstrap as boot, cohort, contract, orchestrate as flow
from safeshift.diagnostics.one_click.artifacts import write
from safeshift.pa3.native.journal import Journal
from tests.test_resource_pilot import Case, ROOT, approved, source


class DatasetPathTests(Case):
    def setUp(self):
        super().setUp()
        self.inputs = self.root / "kaggle/input"
        self.inputs.mkdir(parents=True)
        self.rows, self.jpeg = [], []
        for i in range(8):
            data = io.BytesIO()
            Image.new("RGB", (8, 8), (i * 25, 40, 90)).save(data, format="JPEG")
            raw = data.getvalue()
            with Image.open(io.BytesIO(raw)) as image:
                self.assertEqual(image.format, "JPEG")
                image.verify()
            self.jpeg.append(raw)
            self.rows.append({"sample_id": f"synthetic-{i}",
                "image_locator": f"DATA_PATH/train/Annotations/domain/synthetic-{i}.jpg",
                "image_sha256": hashlib.sha256(raw).hexdigest()})
        # Synthetic bytes replace ONLY the expected hashes within these CPU tests.
        self.enterContext(patch.object(cohort, "IMAGE_SHA256", tuple(r["image_sha256"] for r in self.rows)))

    def dataset(self, mount="original-dataset", layout="InspecSafe-V1-Kaggle/train"):
        root = self.inputs / mount / layout
        for row, raw in zip(self.rows, self.jpeg):
            p = root / row["image_locator"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
        return root

    def test_actual_kaggle_tree_and_each_legacy_layout_stage_eight_jpegs(self):
        for i, layout in enumerate(flow.TRAIN_LAYOUTS):
            with self.subTest(layout=layout):
                inputs = self.inputs
                self.inputs = inputs / str(i)
                self.inputs.mkdir()
                root = self.dataset(layout=layout)
                with patch.object(Path, "rglob", side_effect=AssertionError("RECURSION_FORBIDDEN")):
                    self.assertEqual(flow.discover_train(self.inputs), root)
                flow.check_images(root, self.rows)
                stage, receipt = self.root / f"staged-{i}", self.root / f"receipt-{i}"
                flow.stage_images(root, self.rows, stage, receipt)
                self.assertEqual([ (stage / f"{j:06d}.image").read_bytes() for j in range(8)], self.jpeg)
                journal = Journal(receipt)
                self.assertTrue(journal.verify())
                self.assertEqual(journal.read("finish"), {"count": 8})
                for j, row in enumerate(self.rows):
                    self.assertTrue(journal.exists(f"image-{j:06d}.read-start"))
                    self.assertEqual(journal.read(f"image-{j:06d}.hash")["actual"], row["image_sha256"])
                self.inputs = inputs

    def test_no_recursive_or_test_only_layout_is_accepted(self):
        self.dataset(layout="arbitrary/nesting/InspecSafe-V1-Kaggle/train")
        self.dataset("test-only", "DATA_PATH/test")
        with self.assertRaisesRegex(ValueError, "EXACTLY_ONE"):
            flow.discover_train(self.inputs)

    def test_two_mounts_or_two_layouts_are_ambiguous(self):
        for second_mount, second_layout in (("copy", "InspecSafe-V1-Kaggle/train"),
                                             ("original-dataset", "InspecSafe-V1")):
            with self.subTest(second_mount=second_mount):
                first = self.dataset()
                second = self.dataset(second_mount, second_layout)
                with self.assertRaisesRegex(ValueError, "EXACTLY_ONE"):
                    flow.discover_train(self.inputs)
                # Remove only this known synthetic tree for the next subcase.
                for row in self.rows:
                    (second / row["image_locator"]).unlink()
                (second / "DATA_PATH/train/Annotations/domain").rmdir()
                (second / "DATA_PATH/train/Annotations").rmdir()
                self.assertEqual(flow.discover_train(self.inputs), first)

    def test_unsafe_locators_wrong_type_count_or_duplicate_rejected_without_byte_reads(self):
        root = self.dataset()
        bad = ["/tmp/image.jpg", "C:/image.jpg", "DATA_PATH/train/Annotations/../../test/a.jpg",
               "DATA_PATH/train/Annotations//a.jpg", "DATA_PATH/train/Annotations/./a.jpg",
               "DATA_PATH/train/Annotations/a\\b.jpg", "DATA_PATH/test/Annotations/a.jpg",
               "DATA_PATH/train/Annotations/a.json", None]
        for locator in bad:
            rows = deepcopy(self.rows); rows[0]["image_locator"] = locator
            with self.subTest(locator=locator), patch.object(Path, "open", side_effect=AssertionError("BYTE_READ_FORBIDDEN")):
                with self.assertRaises((ValueError, PermissionError)):
                    flow.check_images(root, rows)
        rows = deepcopy(self.rows); rows[1]["image_locator"] = rows[0]["image_locator"]
        for invalid in (self.rows[:7], rows):
            with self.assertRaises(ValueError): flow.check_images(root, invalid)

    def test_missing_eighth_or_directory_fails_metadata_check_without_reading_any_image(self):
        root = self.dataset()
        p = root / self.rows[7]["image_locator"]; p.unlink()
        for directory in (False, True):
            if directory: p.mkdir()
            with patch.object(Path, "open", side_effect=AssertionError("BYTE_READ_FORBIDDEN")):
                with self.assertRaisesRegex(ValueError, "MISSING_OR_NOT_FILE"):
                    flow.check_images(root, self.rows)

    def symlink(self, target, link, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except OSError as e:
            self.skipTest(f"Host cannot create symlinks: {e.errno}")

    def test_symlink_mount_rejected_including_alias_of_valid_mount(self):
        root = self.dataset()
        self.symlink(root.parents[1], self.inputs / "alias", True)
        with self.assertRaises(ValueError): flow.discover_train(self.inputs)

    def test_symlink_train_annotations_and_input_root_rejected(self):
        root = self.dataset()
        alias = self.root / "input-alias"
        self.symlink(self.inputs, alias, True)
        with self.assertRaises(ValueError): flow.discover_train(alias)
        annotations = root / "DATA_PATH/train/Annotations"
        moved = root / "DATA_PATH/train/synthetic-original"
        annotations.rename(moved)
        self.symlink(moved, annotations, True)
        with self.assertRaises(ValueError): flow.discover_train(self.inputs)

    def test_symlink_train_root_rejected(self):
        root = self.dataset()
        moved = root.with_name("synthetic-original-train")
        root.rename(moved)
        self.symlink(moved, root, True)
        with self.assertRaises(ValueError): flow.discover_train(self.inputs)

    def test_symlink_image_or_parent_rejected_before_read(self):
        root = self.dataset()
        image = root / self.rows[0]["image_locator"]
        image.unlink()
        self.symlink(root / self.rows[1]["image_locator"], image)
        with self.assertRaises(ValueError): flow.check_images(root, self.rows)
        image.unlink(); image.write_bytes(self.jpeg[0])
        directory = image.parent
        moved = directory.with_name("synthetic-original")
        directory.rename(moved)
        self.symlink(moved, directory, True)
        with self.assertRaises(ValueError): flow.check_images(root, self.rows)

    def test_hardlinked_jpeg_rejected(self):
        root = self.dataset()
        image = root / self.rows[0]["image_locator"]
        os.link(image, self.root / "hardlink.jpg")
        with self.assertRaisesRegex(ValueError, "HARDLINK_ALIAS"):
            flow.check_images(root, self.rows)

    def test_wrong_sha_preserves_read_exposure_and_stops_at_first_mismatch(self):
        root = self.dataset()
        (root / self.rows[2]["image_locator"]).write_bytes(self.jpeg[3])
        flow.check_images(root, self.rows)  # Metadata existence is not a hash PASS.
        with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
            flow.stage_images(root, self.rows, self.root / "staged", self.root / "receipt")
        j = Journal(self.root / "receipt")
        self.assertTrue(j.verify())
        self.assertEqual(j.read("failure")["ordinal"], 2)
        self.assertTrue(j.exists("image-000002.read-start"))
        self.assertFalse(j.exists("image-000003.read-start"))

    def run_flow(self, model, fault=None, notebook=False):
        out = self.root / (model + str(fault) + str(notebook)); out.mkdir()
        repo = self.root / ("repo-" + out.name); repo.mkdir(exist_ok=True)
        write(repo / contract.AUTHORITY, contract.template() if fault == "null" else approved(model))
        events = []
        class Ops(flow.Operations):
            kaggle_inputs = self.inputs
            def preflight(inner): return {"synthetic_cpu": True}
            def gpu_memory(inner): raise AssertionError("GPU_QUERY_FORBIDDEN")
            def software(inner): events.append("software")
            def worker(inner, mode): events.append(mode); return {"status": "RETURNED"}
            def provision(inner): events.append("checkpoint")
            def audit(inner): raise AssertionError("TOKENIZER_UNAVAILABLE_BEFORE_PROVISIONING")
        class Sampler:
            def __init__(inner, *args, **kwargs): pass
            def start(inner): pass
            def finish(inner): return {"synthetic_cpu": True}
        original_run = flow.run
        def run(repo, work, output, src, selected):
            return original_run(repo, work, output, src, selected, operations_factory=Ops, sampler_factory=Sampler)
        with patch.object(cohort, "planned", return_value=self.rows), \
             patch.object(flow, "discover_train", wraps=flow.discover_train) as discovery:
            if notebook:
                name = boot.NOTEBOOK_PATHS[("qwen3", "internvl3").index(model)]
                nb = json.loads((ROOT / name).read_bytes())
                tree = ast.parse("".join(nb["cells"][1]["source"]))
                namespace = {"__name__": "synthetic_notebook"}
                exec(compile(ast.Module(body=tree.body[:-1], type_ignores=[]), name, "exec"), namespace)
                namespace["fetch_source"] = lambda work: (repo, source())
                with patch.object(flow, "run", side_effect=run), patch.object(sys, "path", list(sys.path)):
                    result = namespace["bootstrap"](model, out)
            else:
                result = run(repo, out / "work", out, source(), model)
            if fault == "null": discovery.assert_not_called()
        return result, out, events

    def test_missing_image_stops_both_released_notebook_cells_before_provisioning(self):
        root = self.dataset()
        (root / self.rows[7]["image_locator"]).unlink()
        for model in ("qwen3", "internvl3"):
            result, out, events = self.run_flow(model, notebook=True)
            self.assertEqual(events, [])
            self.assertEqual(result["error"]["type"], "ValueError")
            self.assertEqual(result["status"], "FAILED")
            self.assertEqual([r["status"] for r in result["samples"]], ["NOT_ATTEMPTED"] * 8)
            self.assertFalse(any(r["staging_read_started"] for r in result["samples"]))
            self.assertTrue((out / "data/processed/resource_pilot_attempts" / contract.unit(model)["attempt_id"] / "consumed.json").is_file())
            self.assertEqual(result["export"]["status"], "EXPORTED")

    def test_wrong_sha_stops_before_software_checkpoint_or_worker(self):
        root = self.dataset()
        (root / self.rows[0]["image_locator"]).write_bytes(b"wrong synthetic JPEG bytes")
        result, _, events = self.run_flow("qwen3")
        self.assertEqual(events, [])
        self.assertEqual(result["samples"][0]["status"], "TECHNICAL_ERROR")
        self.assertTrue(result["samples"][0]["staging_read_started"])
        self.assertFalse(result["samples"][1]["staging_read_started"])
        self.assertEqual(result["export"]["status"], "EXPORTED")

    def test_valid_eight_are_staged_before_software_with_no_gt_or_test_reads(self):
        self.dataset()
        original_open = Path.open
        def guarded_open(path, *args, **kwargs):
            if path.is_relative_to(self.inputs):
                self.assertIn(path.relative_to(flow.discover_train(self.inputs)).as_posix(),
                              {r["image_locator"] for r in self.rows})
            return original_open(path, *args, **kwargs)
        with patch.object(Path, "open", guarded_open):
            result, out, events = self.run_flow("qwen3")
        self.assertEqual(events, ["software", "inspect", "checkpoint", "inference"])
        self.assertEqual(list(result["phases_seconds"]), ["train_preflight", "preflight", "image_staging",
                         "environment_setup", "guarded_cuda_admission", "checkpoint_provision", "inference_worker"])
        preflight = json.loads((out / "work/evidence/train-preflight.json").read_bytes())
        self.assertEqual(preflight["dataset_root_relative_to_input"], "original-dataset/InspecSafe-V1-Kaggle/train")
        self.assertFalse(preflight["image_bytes_read"])

    def test_null_grant_prevents_dataset_discovery_and_image_reads(self):
        result, out, events = self.run_flow("qwen3", fault="null")
        self.assertEqual(events, [])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse((out / "data/processed/resource_pilot_attempts").exists())


class V2ReleaseTests(unittest.TestCase):
    def test_old_grant_and_pr118_urls_cannot_authorize_either_new_unit(self):
        old = json.loads((ROOT / "configs/diagnostics/resource_pilot_authority.v1.json").read_bytes())
        for model in ("qwen3", "internvl3"):
            with self.assertRaises(PermissionError): contract.authorize(old, source(), model)
            prior = next(u for u in old["scope"]["units"] if u["model"] == model)
            current = contract.unit(model)
            self.assertNotEqual(prior["run_id"], current["run_id"])
            self.assertNotEqual(prior["attempt_id"], current["attempt_id"])
            for key in ("decision_url", "independent_audit_url"):
                grant = approved(model)
                grant["grant"][key] = "https://github.com/tantdna2/SafeShift/pull/118#old"
                with self.assertRaises(PermissionError):
                    contract.authorize(grant, {**source(), "pr_number": 118}, model)

    def test_v1_artifact_bytes_and_scientific_scope_are_unchanged(self):
        paths = ["configs/diagnostics/resource_pilot_authority.v1.json",
                 "configs/diagnostics/resource_pilot_source.v1.json",
                 "configs/diagnostics/resource_pilot_provenance.v1.json",
                 "notes/resource_pilot8_20261019.md",
                 *[f"notebooks/SafeShift_HNLO_RESOURCE_PILOT8_{m}.ipynb" for m in ("qwen3", "internvl3")]]
        for path in paths:
            before = subprocess.check_output(["git", "-C", str(ROOT), "show", contract.BASE_SHA + ":" + path])
            self.assertEqual(before, (ROOT / path).read_bytes(), path)
        old = json.loads((ROOT / paths[0]).read_bytes())
        new = contract.template()
        self.assertIsNone(json.loads((ROOT / contract.AUTHORITY).read_bytes())["grant"])
        self.assertEqual({k: v for k, v in old["scope"].items() if k != "units"},
                         {k: v for k, v in new["scope"].items() if k != "units"})
        for before, after in zip(old["scope"]["units"], new["scope"]["units"]):
            self.assertEqual({k: v for k, v in before.items() if k not in ("run_id", "attempt_id")},
                             {k: v for k, v in after.items() if k not in ("run_id", "attempt_id")})


if __name__ == "__main__":
    unittest.main()
