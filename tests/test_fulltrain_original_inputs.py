"""Synthetic original-mount binding; never read private master/images or TEST."""
from contextlib import ExitStack
import copy
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock

from safeshift.candidates import fulltrain_run as journal
from safeshift.fulltrain import original_inputs as original, admission, runtime, contract
from safeshift.pilot.contract import digest
from safeshift.pilot.artifacts import read


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
                         [{"expected_size": path.stat().st_size, "deadline": limit,
                           "expected_identity": original.memory.identity(path.stat())}
                          for path in (first_path, second_path)])

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

        files = ((path, original.memory.identity(path.stat())),)
        with patch.object(original, "_verify_files", return_value=files) as bytes_gate, \
             patch.dict("sys.modules", {"PIL": SimpleNamespace(Image=SimpleNamespace(open=opener))}):
            result = original.verify_images(self.bundle, self.cohort, self.rows[:1])
            self.assertEqual(result["decode"], "PASS")
            image.load.assert_called_once()
            bytes_gate.assert_called_once_with(self.bundle, self.cohort, self.rows[:1], deadline=None)
            self.assertTrue(opener.call_args.args[0].closed)
            image.format = "PNG"
            self.assertEqual(original.verify_images(self.bundle, self.cohort, self.rows[:1])["formats"], {"PNG": 1})
            image.n_frames = 2
            with self.assertRaisesRegex(ValueError, "STILL_IMAGE"):
                original.verify_images(self.bundle, self.cohort, self.rows[:1])

    def test_decode_rejects_a_swap_before_open_and_mutation_during_pil(self):
        path = self.bundle / "sample.jpg"
        path.write_bytes(b"admitted")
        files = ((path, original.memory.identity(path.stat())),)
        replacement = path.with_suffix(".new")
        replacement.write_bytes(b"admitted")
        replacement.replace(path)
        opener = Mock()
        with patch.dict("sys.modules", {"PIL": SimpleNamespace(Image=SimpleNamespace(open=opener))}):
            with self.assertRaisesRegex(ValueError, "READONLY_FILE_CHANGED"):
                original._decode_files(files, deadline=None)
            opener.assert_not_called()
            files = ((path, original.memory.identity(path.stat())),)
            image = Mock(format="JPEG", n_frames=1, size=(1, 1))
            image.load.side_effect = lambda: path.write_bytes(b"changed size")
            opener.return_value.__enter__ = Mock(return_value=image)
            opener.return_value.__exit__ = Mock(return_value=False)
            image.convert.return_value.__enter__ = Mock(return_value=SimpleNamespace(mode="RGB"))
            image.convert.return_value.__exit__ = Mock(return_value=False)
            with self.assertRaisesRegex(ValueError, "READONLY_FILE_CHANGED"):
                original._decode_files(files, deadline=None)
            image.load.assert_called_once()

    def test_cpu_and_native_share_verified_inputs_and_independent_calls_hash(self):
        from test_fresh_fulltrain import Scripted
        from test_fresh_fulltrain_revision import RevisionTests
        from safeshift.candidates import train_runtime
        from safeshift.fulltrain import gpu_driver, preflight
        workdir = tempfile.TemporaryDirectory()
        self.addCleanup(workdir.cleanup)
        fixture = RevisionTests()
        fixture.root = Path(workdir.name)
        request = fixture.request("minicpm4")
        request.update(inputs=str(self.root), original_inputs=self.binding, marker_sha256=digest(self.binding))
        request["resource_policy"]["free_ram_mib"] = 16384
        for i, row in enumerate(self.rows):
            path = self.bundle / row["image"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(journal.synthetic_bytes(i))
        backend = Scripted(['{"safety_level":"Level04"}'])
        deadline = time.monotonic() + 300

        def decode(files, *, deadline):
            self.assertEqual([p for p, _ in files], [self.bundle / row["image"] for row in self.rows])
            self.assertEqual(len(files), 3763)
            return {"decode": "SYNTHETIC_DECODER_BOUNDARY"}

        repo = runtime.ROOT
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": ""}))
            stack.enter_context(patch.object(original.inputs, "project_master", return_value=self.cohort))
            stack.enter_context(patch.object(admission, "checkpoint_binding", return_value=(None, self.root, self.root, {})))
            stack.enter_context(patch.object(original.memory, "observe"))
            stack.enter_context(patch.object(original.memory, "resource_check", return_value={}))
            stack.enter_context(patch.object(original.memory, "reclaim"))
            stack.enter_context(patch.object(original.memory, "load_guard"))
            for name in ("software", "hardware", "cuda"):
                stack.enter_context(patch.object(admission.environment, name, return_value={}))
            bind_driver = stack.enter_context(patch.object(gpu_driver, "bind", return_value=self.root))
            stack.enter_context(patch.object(gpu_driver, "hardware", return_value={}))
            for name in ("software", "worker_cuda"):
                stack.enter_context(patch.object(train_runtime, name))
            stack.enter_context(patch.object(preflight, "cpu_native_checks", return_value={}))
            stack.enter_context(patch.object(runtime, "_native_factory", return_value=backend))
            stack.enter_context(patch.object(runtime, "validate_native_raw"))
            reader = stack.enter_context(patch.object(original.memory, "stream_readonly_sha256",
                wraps=original.memory.stream_readonly_sha256))
            decoder = stack.enter_context(patch.object(original, "_decode_files", side_effect=decode))
            for mode, expected in (("cpu", 3764), ("native", 3765)):
                reader.reset_mock()
                admission.stage(mode, request, repo, fixture.root / mode, deadline)
                self.assertEqual(reader.call_count, expected)
                self.assertEqual(sum(call.args[0] == self.master for call in reader.call_args_list), 1)
                self.assertIsNone(admission._current_original_stage(mode, request, repo, deadline))
            self.assertEqual(decoder.call_count, 2)
            self.assertEqual([call.args[0] for call in bind_driver.call_args_list],
                             [fixture.root / "native", fixture.root / "native" / "memory"])
            self.assertEqual(backend.calls, 1)
            root = Path(request["work"]) / request["plan"]["run_id"]
            self.assertEqual(read(root / "accounting.json")["samples"][0]["status"], "SUCCESS")

            reader.reset_mock()
            original.verify_images(self.bundle, self.cohort, self.rows)
            self.assertEqual(reader.call_count, 3763)
            with self.assertRaises(TypeError):
                original.verify_images(self.bundle, self.cohort, self.rows, bytes_verified=True)
            with self.assertRaises(TypeError):
                runtime._worker(request, admitted_inputs=(self.bundle, self.cohort, self.rows))

            current = admission._original_stage.set(None)
            self.addCleanup(admission._original_stage.reset, current)
            # Reuse of the actual observed inputs is scoped to the exact
            # request, projection/mapping and deadline which were verified.
            with patch.object(admission, "history_admission"):
                admitted = admission._admit_original_stage("native", request, repo, deadline)
                with self.assertRaisesRegex(ValueError, "ORIGINAL_STAGE_BINDING_CHANGED"):
                    admission._current_original_stage("native", copy.deepcopy(request), repo, deadline)
                with self.assertRaisesRegex(ValueError, "ORIGINAL_STAGE_BINDING_CHANGED"):
                    admission._current_original_stage("native", request, repo, deadline + 1)
                admitted[2][0]["image"] = admitted[2][1]["image"]
                with self.assertRaisesRegex(ValueError, "ORIGINAL_STAGE_BINDING_CHANGED"):
                    admission._current_original_stage("native", request, repo, deadline)


if __name__ == "__main__": unittest.main()
