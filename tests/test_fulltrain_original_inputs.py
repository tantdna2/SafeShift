"""Synthetic original-mount binding; never read private master/images or TEST."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock

from safeshift.candidates import fulltrain_run as journal
from safeshift.fulltrain import original_inputs as original, admission, runtime, contract
from safeshift.pilot.contract import digest


class OriginalMountedInputsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cohort = journal.synthetic_cohort()
        self.binding = {"schema": original.SCHEMA, "master_sha256": original.MASTER_SHA,
            "projection_sha256": digest(self.cohort),
            "master_dataset": {"ref": original.REFS["master_dataset"], "version": 7,
                               "mount": "datasets/nguynanhtn/safeshift-pilot-input"},
            "train_dataset": {"ref": original.REFS["train_dataset"], "version": 9,
                              "mount": "datasets/nguynanhtn/inspecsafe-v1-kaggle"}}
        # Versions7/9 are synthetic test values, not observed Kaggle versions.
        self.rows = [{**row, "image": "train/Annotations/" + row["sample_id"] + ".jpg"}
                     for row in self.cohort["samples"]]
        self.master = self.root / self.binding["master_dataset"]["mount"] / "master_manifest.json"
        self.master.parent.mkdir(parents=True)
        self.originals = [{**row, "image_locator": "DATA_PATH/" + row["image"],
                           "level": "DO_NOT_EXPORT_GT", "domain": "SYNTHETIC"} for row in self.rows]
        self.master.write_text(json.dumps({"samples": self.originals}), encoding="utf8")
        self.bundle = self.root / self.binding["train_dataset"]["mount"] / "InspecSafe-V1-Kaggle/train/DATA_PATH"
        self.bundle.mkdir(parents=True)

    def admit(self):
        return original.admit(self.root, self.binding, digest(self.binding), digest(self.cohort))

    def test_actual_frozen_master_gate_rejects_fixture_before_images(self):
        with patch.object(original, "verify_bytes") as images:
            with self.assertRaisesRegex(ValueError, "ORIGINAL_MASTER_CHECKSUM"): self.admit()
            images.assert_not_called()

    def test_original_layout_preserves_order_ids_hash_and_excludes_gt_without_copy(self):
        with patch.object(original.inputs, "project_master", return_value=self.cohort) as project:
            bundle, cohort, rows = self.admit()
        self.assertEqual(bundle, self.bundle)
        self.assertEqual(cohort, self.cohort)
        self.assertEqual(rows, self.rows)
        project.assert_called_once_with(self.master.read_bytes(), digest(self.cohort))
        self.assertFalse(any(self.bundle.iterdir()))
        self.assertEqual(set(rows[0]), {"ordinal", "sample_id", "image_sha256", "image"})

    def test_version_ref_path_projection_and_binding_are_explicit_not_fallback(self):
        for mutate in (lambda b:b["train_dataset"].update(version=None),
                       lambda b:b["train_dataset"].update(version=True),
                       lambda b:b["train_dataset"].update(ref="tetrabot2026/inspecsafe-v1-kaggle"),
                       lambda b:b["train_dataset"].update(mount="../TEST"),
                       lambda b:b["train_dataset"].update(mount="inspecsafe-v1-kaggle/TEST"),
                       lambda b:b.update(projection_sha256="f"*64),
                       lambda b:b.update(master_sha256="f"*64)):
            bad = copy.deepcopy(self.binding); mutate(bad)
            with self.assertRaises(ValueError): original.validate_binding(bad, digest(bad), digest(self.cohort))
        with self.assertRaisesRegex(ValueError, "BINDING_PIN"):
            original.validate_binding(self.binding, "f"*64, digest(self.cohort))

    def test_duplicate_mount_is_ambiguous_even_when_bytes_could_match(self):
        (self.root / "safeshift-pilot-input").mkdir()
        with self.assertRaisesRegex(ValueError, "UNIQUE_ORIGINAL_MOUNT"):
            self.admit()

    def test_verified_kaggle_v1_nested_master_and_train_layout(self):
        # Names mirror the authenticated version1 ListDatasetFiles inventory;
        # contents remain synthetic and are not evidence of private byte PASS.
        nested = self.master.parent / "safeshift-pilot-input/master_manifest.json"
        nested.parent.mkdir()
        self.master.rename(nested)
        with patch.object(original.inputs, "project_master", return_value=self.cohort):
            self.assertEqual(self.admit(), (self.bundle, self.cohort, self.rows))

    def test_missing_unknown_duplicate_and_wrong_kind_content_roots(self):
        nested = self.master.parent / "safeshift-pilot-input/master_manifest.json"
        nested.parent.mkdir()
        nested.write_bytes(self.master.read_bytes())
        with self.assertRaisesRegex(ValueError, "UNIQUE_ORIGINAL_CONTENT"):
            self.admit()
        nested.unlink(); self.master.unlink()
        (nested.parent / "unexpected").mkdir()
        with self.assertRaisesRegex(ValueError, "UNIQUE_ORIGINAL_CONTENT"):
            self.admit()
        self.master.mkdir()
        with self.assertRaisesRegex(ValueError, "REGULAR_FILE"):
            self.admit()

    def test_train_root_has_no_fallback_to_test_or_arbitrary_depth(self):
        self.bundle.rename(self.bundle.with_name("unknown"))
        with patch.object(original.inputs, "project_master", return_value=self.cohort):
            with self.assertRaisesRegex(ValueError, "UNIQUE_ORIGINAL_CONTENT"):
                self.admit()

    def test_nested_master_hardlink_is_rejected_before_projecting(self):
        import os
        nested = self.master.parent / "safeshift-pilot-input/master_manifest.json"
        nested.parent.mkdir()
        os.link(self.master, nested)
        with patch.object(original.inputs, "project_master") as project:
            with self.assertRaises(ValueError): self.admit()
            project.assert_not_called()

    def test_locator_id_and_checksum_changes_fail_before_decode_or_call(self):
        for mutate in (lambda r:r.update(image_locator="DATA_PATH/TEST/private.jpg"),
                       lambda r:r.update(sample_id="other"), lambda r:r.update(image_sha256="f"*64)):
            rows = copy.deepcopy(self.originals); mutate(rows[0])
            self.master.write_text(json.dumps({"samples": rows}), encoding="utf8")
            with patch.object(original.inputs, "project_master", return_value=self.cohort):
                with self.assertRaises(ValueError): self.admit()

    def test_missing_changed_duplicate_or_reordered_mapping_fails_closed(self):
        with self.assertRaises(FileNotFoundError): original.verify_bytes(self.bundle, self.cohort, self.rows)
        p = self.bundle / self.rows[0]["image"]; p.parent.mkdir(parents=True); p.write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "BYTES_CHANGED"):
            original.verify_bytes(self.bundle, self.cohort, self.rows)
        for mutate in (lambda r:r.reverse(), lambda r:r.__setitem__(1, r[0]),
                       lambda r:r[0].update(image="TEST/private.jpg"), lambda r:r.pop()):
            rows = copy.deepcopy(self.rows); mutate(rows)
            with patch.object(original.memory, "stream_readonly_sha256", return_value=self.rows[0]["image_sha256"]), \
                 patch.object(original, "snapshot_stat"):
                with self.assertRaises(ValueError): original.verify_bytes(self.bundle, self.cohort, rows)

    def test_each_original_hash_uses_size_and_deadline_before_accepting(self):
        limit = 123.0
        first, second = self.rows[:2]
        first_path = self.bundle / first["image"]
        first_path.parent.mkdir(parents=True)
        first_path.write_bytes(b'a')
        second_path = self.bundle / second["image"]
        second_path.write_bytes(b'bb')
        with patch.object(original.memory, "stream_readonly_sha256",
                          side_effect=[first["image_sha256"], "corrupt"]) as reader:
            with self.assertRaisesRegex(ValueError, "BYTES_CHANGED"):
                original.verify_bytes(self.bundle, self.cohort, self.rows, deadline=limit)
        self.assertEqual([call.args[0] for call in reader.call_args_list], [first_path, second_path])
        self.assertEqual([call.kwargs for call in reader.call_args_list],
                         [{"expected_size": 1, "deadline": limit}, {"expected_size": 2, "deadline": limit}])

    def test_shared_admission_and_worker_dispatch_original_binding(self):
        request = {"original_inputs": self.binding, "inputs": self.root, "marker_sha256": digest(self.binding),
                   "projection_sha256": digest(self.cohort)}
        with patch.object(original, "admit", return_value=(self.bundle, self.cohort, self.rows)) as admit, \
             patch.object(original, "verify_bytes", return_value={"copied_bytes":0}) as check:
            self.assertEqual(admission.input_binding(request), (self.bundle, self.cohort, self.rows))
            admission.input_bytes(request, self.bundle, self.cohort, self.rows)
        admit.assert_called_once_with(self.root, self.binding, digest(self.binding), digest(self.cohort), deadline=None)
        check.assert_called_once_with(self.bundle, self.cohort, self.rows, deadline=None)
        # Direct worker keeps the exact-model/source guard before original mounts.
        with patch.object(original, "admit") as private:
            with self.assertRaises(ValueError): runtime._worker({**request, "model_key":"minicpm4"})
            private.assert_not_called()

    def test_child_decoder_matches_native_pil_rgb_even_for_png_bytes_at_jpg_locator(self):
        image = Mock(format="JPEG", n_frames=1, size=(17, 1))
        context = Mock()
        context.__enter__ = Mock(return_value=image)
        context.__exit__ = Mock(return_value=False)
        rgb = Mock(mode="RGB")
        image.convert.return_value.__enter__ = Mock(return_value=rgb)
        image.convert.return_value.__exit__ = Mock(return_value=False)
        opener = Mock(return_value=context)
        path = self.bundle / self.rows[0]["image"]
        path.parent.mkdir(parents=True)
        path.write_bytes(b"synthetic")

        with patch.object(original.memory, "evict_readonly_file", wraps=original.memory.evict_readonly_file) as advice, \
             patch.object(original, "verify_bytes") as bytes_gate, \
             patch.dict("sys.modules", {"PIL": SimpleNamespace(Image=SimpleNamespace(open=opener))}):
            result = original.verify_images(self.bundle, self.cohort, self.rows[:1])
            self.assertEqual(result["decode"], "PASS")
            image.load.assert_called_once()
            advice.assert_called_once_with(path, expected_size=9, deadline=None)
            bytes_gate.assert_called_once_with(self.bundle, self.cohort, self.rows[:1], deadline=None)
            opener.assert_called_once_with(self.bundle / self.rows[0]["image"])
            image.format = "PNG"
            self.assertEqual(original.verify_images(self.bundle, self.cohort, self.rows[:1])["formats"], {"PNG": 1})
            image.n_frames = 2
            with self.assertRaisesRegex(ValueError, "STILL_IMAGE"):
                original.verify_images(self.bundle, self.cohort, self.rows[:1])


if __name__ == "__main__": unittest.main()
