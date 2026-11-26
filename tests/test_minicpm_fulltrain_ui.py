"""End-to-end CPU synthetic Owner UI custody; no provider, GPU or real data."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from safeshift.fulltrain import minicpm_ui as ui, contract as c, runtime as rt, provision
from safeshift.candidates import fulltrain_run as journal
from safeshift.pilot.artifacts import write, read, sha, export
from safeshift.pilot.contract import digest, MASTER_SHA
from test_fresh_fulltrain import Scripted
from test_fresh_fulltrain_revision import budgets


class OwnerUITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cohort = journal.synthetic_cohort()
        campaign = c.campaign({k: self.cohort for k in c.planning.MODELS}, digest(self.cohort))
        binding = {"schema": "safeshift-original-mounted-train-v1", "master_sha256": MASTER_SHA,
            "projection_sha256": digest(self.cohort),
            "master_dataset": {"ref": ui.MASTER.rsplit('/',1)[0], "version": 1, "mount": "safeshift-pilot-input"},
            "train_dataset": {"ref": ui.TRAIN.rsplit('/',1)[0], "version": 1, "mount": "inspecsafe-v1-kaggle"}}
        p = c.plan(campaign, self.cohort, c.native_identity("minicpm4"), [], action="initial",
            run_id="mini-first", attempt_id="mini-first-attempt", max_calls=2, max_seconds=120)
        request = {"model_key": "minicpm4", "source_sha256": digest(c.source_manifest()),
            "inputs": "/kaggle/input", "work": "/kaggle/working/minicpm-fulltrain", "scratch": "/kaggle/temp/minicpm-fulltrain",
            "original_inputs": binding, "marker_sha256": digest(binding), "projection_sha256": digest(self.cohort),
            "campaign": campaign, "plan": p, "history": [], "resource_policy": budgets(), "repair_case": None,
            "checkpoint_marker_sha256": "b" * 64, "runtime_lock": None, "runtime_lock_sha256": None,
            "software_input": None, "software_marker_sha256": None, "python_input": ui.py.binding()}
        self.value = {"schema": ui.SCHEMA, "request": request, "cohort": self.cohort, "ancestors": [],
            "job": "nguynanhtn/synthetic-mini-1", "capsule_ref": "nguynanhtn/safeshift-minicpm-capsule-synthetic1/1",
            "input_sources": {"dataset_sources": [ui.TRAIN, ui.MASTER, ui.py.REF,
                "nguynanhtn/safeshift-minicpm-capsule-synthetic1/1"], "kernel_sources": [ui.CHECKPOINT]},
            "evidence_refs": {k: None for k in ("input_versions", "rights", "execution_release", "source_review", "independent_audit", "live_verification")}}
        self.dataset = self.root / "capsule"
        self.dataset.mkdir()
        write(self.dataset / ui.MARKER, self.value)

    def results(self, outputs=None, value=None, history_work=None):
        value = value or self.value
        request = value["request"]
        bundle = self.root / ("images-" + request["plan"]["run_id"])
        bundle.mkdir()
        for i in request["plan"]["scheduled_ordinals"]:
            (bundle / f"{i:06d}.bin").write_bytes(journal.synthetic_bytes(i))
        backend = Scripted(outputs or ['{"safety_level":"Level04"}', 'fenced INVALID'])
        attempt = rt._execute(history_work or self.root / "work", bundle, self.cohort, request["campaign"],
            request["plan"], request["history"], lambda: backend,
            image_path=lambda i: f"{i:06d}.bin", store_class=journal.BoundStore)
        control = self.root / ("supervisor-" + request["plan"]["run_id"])
        control.mkdir()
        write(control / "request.json", request)
        write(control / "release.json", {"status": "TECHNICAL_STAGES_RETURNED_NOT_RELEASE_AUTHORITY",
            "source_sha256": request["source_sha256"], "diagnostic": False, "attempt_observed": True,
            "scientific_qualified": False, "failure": None, "last_stage": "native"})
        for mode in ("admit", "setup", "cpu", "gpu", "native"):
            write(control / (mode + "-process.json"), {"status": "EXITED", "returncode": 0})
            write(control / mode / "stage.json", {"status": "RETURNED", "stage": mode,
                "request_sha256": digest(request), "source_sha256": request["source_sha256"],
                "native_attempt_permitted": mode == "native"})
        export(control, Path(str(control) + ".zip"))
        return Path(str(attempt) + ".zip"), Path(str(control) + ".zip"), backend

    def test_initial_package_complete_inputs_and_unchanged_fence(self):
        build = Mock(return_value={"cells": [], "metadata": {}})
        output = ui.package(self.value, [], self.root / "package", build)
        handoff = read(output / "handoff.json")
        self.assertEqual(handoff["status"], "CANDIDATE_RELEASE_BLOCKED")
        self.assertEqual(handoff["native_calls"], 0)
        build.assert_called_once_with(handoff["capsule_sha256"])
        self.assertEqual(ui.verify_capsule(output / "dataset", handoff["capsule_sha256"]), self.value)
        self.assertEqual(read(output / "kernel-metadata.json")["dataset_sources"], self.value["input_sources"]["dataset_sources"])
        with self.assertRaises(FileExistsError): ui.package(self.value, [], output, build)

    def test_initial_builder_uses_current_source_and_explicit_caps_without_data_reads(self):
        got = ui.initial(self.cohort, digest(self.cohort), budgets(), checkpoint_marker_sha256="b"*64,
            run_id="mini-first", attempt_id="mini-first-attempt", job=self.value["job"],
            capsule_ref=self.value["capsule_ref"], max_calls=2, max_seconds=120, nested_mounts=False)
        self.assertEqual(got, self.value)
        self.assertTrue(all(v is None for v in got["evidence_refs"].values()))
        with self.assertRaisesRegex(ValueError, "COHORT_CHECKSUM"):
            ui.initial(self.cohort, "f"*64, budgets(), checkpoint_marker_sha256="b"*64,
                run_id="r", attempt_id="a", job=self.value["job"], capsule_ref=self.value["capsule_ref"],
                max_calls=2, max_seconds=120, nested_mounts=False)

    def test_offline_python_bad_bytes_missing_duplicate_marker_and_writable_mount_block(self):
        request = deepcopy(self.value["request"])
        inputs = self.root / "inputs"; inputs.mkdir()
        request["inputs"] = str(inputs)
        with self.assertRaisesRegex(ValueError, "UNIQUE_"):
            ui.stage_python(request, self.root, self.root, {}, time.monotonic()+30)
        mount = inputs / ui.py.REF.split('/')[1]; mount.mkdir()
        write(mount / ui.py.MARKER, ui.py.manifest())
        (mount / ui.py.PAYLOAD).write_bytes(b"SYNTHETIC_CORRUPT_TRANSPORT")
        with patch.object(ui.os, "statvfs", return_value=SimpleNamespace(f_flag=0), create=True), \
             patch.object(ui.os, "ST_RDONLY", 1, create=True):
            with self.assertRaisesRegex(ValueError, "PYTHON_INPUT_READ_ONLY"):
                ui.stage_python(request, self.root, self.root, {}, time.monotonic()+30)
        with patch.object(ui.os, "statvfs", return_value=SimpleNamespace(f_flag=1), create=True), \
             patch.object(ui.os, "ST_RDONLY", 1, create=True), \
             patch.object(ui.shutil, "disk_usage", return_value=SimpleNamespace(free=32 * 2**30)):
            with self.assertRaisesRegex(ValueError, "PYTHON_INPUT_SIZE"):
                ui.stage_python(request, self.root, self.root, {}, time.monotonic()+30)
        duplicate = inputs / "duplicate"; duplicate.mkdir(); write(duplicate / ui.py.MARKER, {})
        with self.assertRaisesRegex(ValueError, "UNIQUE_"):
            ui.stage_python(request, self.root, self.root, {}, time.monotonic()+30)

    def test_public_execution_and_collection_block_before_any_path_network_or_output(self):
        class Poison:
            def __fspath__(self): raise AssertionError("PRIVATE_IO")
        with patch.object(ui, "discover") as discover:
            for call in (lambda: ui.run_capsule(Poison(), "f"*64),
                         lambda: ui.collect(Poison(), Poison(), Poison(), Poison())):
                with self.assertRaisesRegex(PermissionError, "ISSUE171_NO_GPU"): call()
            discover.assert_not_called()

    def test_strict_caps_versions_model_history_and_no_invented_authority(self):
        changes = [lambda v:v["request"].update(model_key="qwen3"),
            lambda v:v["request"]["plan"].update(max_calls=0),
            lambda v:v["request"]["plan"].update(max_seconds=0),
            lambda v:v["request"]["original_inputs"]["train_dataset"].update(version=2),
            lambda v:v["input_sources"]["kernel_sources"].append("other/checkpoint/1"),
            lambda v:v["request"]["plan"]["identity"].update(configuration_sha256="f"*64),
            lambda v:v["request"].update(python_input=None),
            lambda v:v["request"].update(history=[{}]),
            lambda v:v["request"].update(work="/kaggle/input/write"),
            lambda v:v.update(evidence_refs={"approved": True})]
        for change in changes:
            bad = deepcopy(self.value); change(bad)
            with self.subTest(change=change), self.assertRaises((ValueError, KeyError)): ui.validate(bad)

    def test_capsule_corrupt_extra_missing_or_wrong_pin_fail_closed(self):
        marker = self.dataset / ui.MARKER
        with self.assertRaisesRegex(ValueError, "UI_CAPSULE_PIN"): ui.verify_capsule(self.dataset, "f"*64)
        write(self.dataset / "extra.json", {})
        with self.assertRaisesRegex(ValueError, "UI_CAPSULE_EXACT_FILES"): ui.verify_capsule(self.dataset, sha(marker))
        with self.assertRaises(FileNotFoundError): ui.verify_capsule(self.root / "absent", "f"*64)

    def test_real_controller_export_verify_resume_package_and_empty_vm_restore(self):
        attempt, supervisor, backend = self.results()
        report = ui.verify_results(self.value, self.dataset, attempt, supervisor, self.root / "verified")
        self.assertEqual(backend.calls, 2)
        self.assertEqual(report["counts"], {"SUCCESS": 1, "INVALID": 1, "NOT_ATTEMPTED": 3761})
        self.assertFalse(report["pooling_allowed"])
        next_value = ui.next_capsule(self.value, report, run_id="mini-second", attempt_id="mini-second-attempt",
            job="nguynanhtn/synthetic-mini-2", capsule_ref="nguynanhtn/safeshift-minicpm-capsule-synthetic2/1",
            max_calls=1, max_seconds=90)
        self.assertEqual(next_value["request"]["plan"]["scheduled_ordinals"], [2])
        output = ui.package(next_value, [attempt], self.root / "next-package", lambda _: {})
        restored = self.root / "empty-vm"
        self.assertEqual(ui.restore_history(output / "dataset", next_value, restored), report["history"])
        with self.assertRaisesRegex(ValueError, "HISTORY_IMPORT_NO_OVERWRITE"):
            ui.restore_history(output / "dataset", next_value, restored)
        # Missing ancestor cannot become a legitimate resume package.
        with self.assertRaisesRegex(ValueError, "ALL_UI_ANCESTORS"):
            ui.package(next_value, [], self.root / "missing", lambda _: {})

    def test_tampered_zip_or_sidecar_and_foreign_supervisor_block_without_output(self):
        attempt, supervisor, _ = self.results()
        side = Path(str(attempt) + ".sha256.json")
        saved = side.read_bytes(); side.write_bytes(b'{"sha256":"bad","members":1}')
        with self.assertRaisesRegex(ValueError, "UI_ARCHIVE_SIDECAR"):
            ui.verify_results(self.value, self.dataset, attempt, supervisor, self.root / "bad")
        self.assertFalse((self.root / "bad").exists())
        side.write_bytes(saved)
        changed = deepcopy(self.value); changed["request"]["plan"]["run_id"] = "foreign"
        with self.assertRaises(ValueError): ui.verify_results(changed, self.dataset, attempt, supervisor, self.root / "bad2")
        with attempt.open("ab") as f: f.write(b"corrupt")
        with self.assertRaisesRegex(ValueError, "UI_ARCHIVE_SIDECAR"): ui.pair(attempt)

    def test_technical_error_preserved_and_next_turn_stops(self):
        attempt, supervisor, backend = self.results([RuntimeError("CUDA out of memory")])
        report = ui.verify_results(self.value, self.dataset, attempt, supervisor, self.root / "error-verified")
        self.assertEqual(report["continuation"], "STOP_RECONCILE_FAILURE")
        self.assertEqual(report["counts"]["TECHNICAL_ERROR"], 1)
        with self.assertRaisesRegex(ValueError, "UI_NEXT_REQUIRES"):
            ui.next_capsule(self.value, report, run_id="r", attempt_id="a", job="x", capsule_ref="x", max_calls=1,max_seconds=1)
        self.assertEqual(backend.calls, 1)

    def test_offline_python_is_selected_for_shared_setup_no_provider_fallback(self):
        output = self.root / "setup"; output.mkdir()
        scratch = self.root / "scratch"; scratch.mkdir()
        selected = scratch / "verified-python"
        request = deepcopy(self.value["request"]); request["scratch"] = str(scratch)
        with patch.object(ui, "stage_python", return_value=selected) as stage, \
             patch.object(ui.py, "selected_interpreter") as selection, \
             patch("safeshift.candidates.train_runtime.prepare_runtime", return_value=("p", {})) as inherited:
            provision.prepare(request, ui.ROOT, output, time.monotonic()+60)
        stage.assert_called_once()
        selection.assert_called_once_with(selected, scratch)
        inherited.assert_called_once()

    def test_python_binding_failure_precedes_decode(self):
        request = deepcopy(self.value["request"]); request["python_input"] = {}
        with patch.object(ui.py, "decode") as decode:
            with self.assertRaisesRegex(ValueError, "EXACT_OFFLINE_PYTHON"):
                ui.stage_python(request, self.root, self.root, {}, time.monotonic()+1)
            decode.assert_not_called()


if __name__ == "__main__":
    unittest.main()
