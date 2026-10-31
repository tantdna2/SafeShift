"""Synthetic CPU admission, incident and hostile archive tests; no GPU/weights."""
from contextlib import ExitStack
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.candidates import train_contract as c, train_owner as owner
from safeshift.candidates import train_inputs as inputs, train_python as provider, train_preflight as preflight
from safeshift.candidates import train_incident as incident
from safeshift.candidates.source import ROOT
from safeshift.pilot.artifacts import read, sha, write, export, verify_archive
from safeshift.pilot.contract import digest
from safeshift.pilot import manifest as historical
from test_candidate160 import fixture


def synthetic_child_evidence(name, key):
    from safeshift.candidates.train_runtime import pins
    return {"software_cpu": {"versions": pins(key), "compiled_cpu_nms": "PASS", "cuda_build": "12.4",
                             "identity": {"scope": "SYNTHETIC"}},
            "cuda_child": {"worker_cuda": "MEASURED_FP16_FUNCTIONAL", "worker_visible_gpus": 1, "scope": "SYNTHETIC"},
            "cpu_native": {"meta_loader": {"status": "EAGER_MODULES_VERIFIED"}, "synthetic_images": [{}]*8},
            "images_cpu": {"verified_images": 160},
            "live_resources": {"free_ram_mib": 8192, "free_scratch_mib": 8192, "free_output_mib": 8192}}[name]


class InputTests(unittest.TestCase):
    def test_both_models_direct_dataset_and_notebook_layouts_and_old_pilot_unchanged(self):
        for key in c.KEYS:
            for layout in ("checkpoint", "datasets/account/checkpoint", "notebooks/account/checkpoint"):
                for prefix in ("", "safeshift-pilot-input/"):
                    with self.subTest(key=key, layout=layout, prefix=prefix), tempfile.TemporaryDirectory() as d:
                        root = Path(d)
                        mount = root/layout/prefix
                        (mount/"weights").mkdir(parents=True)
                        (mount/"source"/c.model(key)["revision"]).mkdir(parents=True)
                        marker = mount/f"candidate_checkpoint_{key}.json"
                        write(marker, {"schema": "safeshift-candidate160-checkpoint-v1", "model": c.model(key)})
                        self.assertEqual(inputs.checkpoint(root, key), (marker, mount/"source"/c.model(key)["revision"], mount/"weights"))
                        if layout.startswith("notebooks/"):
                            with self.assertRaisesRegex(ValueError, "FOUND_0"):
                                historical.discover(root, marker.name)
                        else:
                            self.assertEqual(historical.discover(root, marker.name), marker)

    def test_duplicates_wrong_marker_structure_and_traversal_fail_closed(self):
        for key in c.KEYS:
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                first = root/"direct"
                first.mkdir()
                filename = f"candidate_checkpoint_{key}.json"
                write(first/filename, {"schema": "wrong", "model": c.model(key)})
                with self.assertRaisesRegex(ValueError, "OFFICIAL_CHECKPOINT_MARKER"):
                    inputs.checkpoint(root, key)
                (first/filename).write_text(json.dumps({"schema": "safeshift-candidate160-checkpoint-v1", "model": c.model(key)}))
                with self.assertRaisesRegex(ValueError, "SOURCE_AND_WEIGHTS"):
                    inputs.checkpoint(root, key)
                write(root/"notebooks/account/slug"/filename, {})
                with self.assertRaisesRegex(ValueError, "FOUND_2"):
                    inputs.discover(root, filename)
                for filename in ("../escape", "/absolute", "a/b", "a\\b", "x:y"):
                    with self.assertRaises(ValueError):
                        inputs.discover(root, filename)

    def test_bounds_and_unsupported_deep_layout(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root/"notebooks/account/slug/deeper/marker.json", {})
            with self.assertRaisesRegex(ValueError, "FOUND_0"):
                inputs.discover(root, "marker.json")
            with self.assertRaisesRegex(ValueError, "DISCOVERY_BOUND"):
                inputs.discover(root, "marker.json", limit=2)

    def test_aliases_rejected_at_every_level(self):
        for link_at in ("notebooks", "notebooks/account", "notebooks/account/slug", "notebooks/account/slug/marker.json"):
            with self.subTest(link_at=link_at), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                real = root/"real"
                real.mkdir()
                link = root/"input"/link_at
                link.parent.mkdir(parents=True)
                try:
                    link.symlink_to(real, target_is_directory=True)
                except OSError:
                    self.skipTest("symlink creation unavailable")
                with self.assertRaisesRegex(ValueError, "ALIAS"):
                    inputs.discover(root/"input", "marker.json")


class ProviderTests(unittest.TestCase):
    def test_downloader_rejects_wrong_bytes_or_redirect_with_durable_failure(self):
        for fault in ("size", "hash", "redirect", "probe"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root/"out").mkdir()
                (root/"scratch").mkdir()
                lock = read(ROOT/"configs/candidate160/python3119.json")
                response = io.BytesIO(b"SYNTHETIC")
                response.geturl = lambda: "http://invalid.test/asset" if fault == "redirect" else "https://release-assets.githubusercontent.com/public/file?signature=PRIVATE_QUERY"
                if fault == "size":
                    lock["size_bytes"] = 1
                if fault == "probe":
                    lock["size_bytes"] = len(b"SYNTHETIC")
                    import hashlib
                    lock["sha256"] = hashlib.sha256(b"SYNTHETIC").hexdigest()
                with patch.object(provider, "read", return_value=lock), \
                     patch.object(provider.platform, "system", return_value="Linux"), \
                     patch.object(provider.platform, "machine", return_value="x86_64"), \
                     patch.object(provider, "urlopen", return_value=response), \
                     patch.object(provider, "extract", side_effect=ValueError("SYNTHETIC_EXTRACT_BLOCK")) if fault == "probe" else ExitStack(), \
                     self.assertRaises(ValueError):
                    provider.provision(ROOT, root/"scratch", root/"out", {}, float("inf"))
                receipt = read(root/"out/python_provider.json")
                self.assertEqual(receipt["status"], "BLOCKED")
                self.assertNotIn("PRIVATE_QUERY", json.dumps(receipt))

    def archive(self, root, entries):
        path = root/"archive.tar.gz"
        with tarfile.open(path, "w:gz") as packed:
            for name, kind, value in entries:
                item = tarfile.TarInfo(name)
                item.mode = 0o755
                if kind == "link":
                    item.type, item.linkname = tarfile.SYMTYPE, value
                elif kind == "hard":
                    item.type, item.linkname = tarfile.LNKTYPE, value
                elif kind == "fifo":
                    item.type = tarfile.FIFOTYPE
                else:
                    item.size = len(value)
                packed.addfile(item, io.BytesIO(value) if kind == "file" else None)
        lock = {"size_bytes": path.stat().st_size, "sha256": sha(path), "max_members": 20, "max_uncompressed_bytes": 100}
        return path, lock

    def test_size_hash_and_resource_bounds_before_execution(self):
        for fault in ("size_bytes", "sha256", "max_members", "max_uncompressed_bytes"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                archive, lock = self.archive(root, [("python/bin/python3.11", "file", b"SYNTHETIC")])
                lock[fault] = "0"*64 if fault == "sha256" else 0
                with self.assertRaises(ValueError):
                    provider.extract(archive, root/"extract", lock)

    def test_unsafe_tar_entries_rejected(self):
        for entries in (
            [("../escape", "file", b"x")], [("/absolute", "file", b"x")],
            [("other/bin/python3.11", "file", b"x")], [("python/x", "hard", "python/y")],
            [("python/x", "fifo", "")], [("python/x", "file", b"x"), ("python/x", "file", b"y")],
            [("python/x", "link", "/tmp/escape")], [("python/x", "link", "../../escape")],
            [("python/x", "link", "missing")],
            [("python/x", "link", "bin/python3.11"), ("python/x/escape", "file", b"x")],
        ):
            with self.subTest(entries=entries), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                archive, lock = self.archive(root, entries)
                with self.assertRaises(ValueError):
                    provider.extract(archive, root/"extract", lock)

    def test_regular_executable_and_internal_links_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            archive, lock = self.archive(root, [("python/bin/python3.11", "file", b"SYNTHETIC")])
            python, receipt = provider.extract(archive, root/"extract", lock)
            self.assertEqual(python.read_bytes(), b"SYNTHETIC")
            self.assertEqual(receipt["safe_extraction"], "PASS")
            with self.assertRaises(FileExistsError):
                provider.extract(archive, root/"extract", lock)


class PreflightTests(unittest.TestCase):
    def test_export_failure_retains_truthful_report_and_never_creates_slot(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/"input").mkdir()
            with patch.object(preflight.boot, "provision_scratch_root", side_effect=OSError("SYNTHETIC ENOSPC")), \
                 patch("safeshift.candidates.train_runtime.hardware", side_effect=RuntimeError("SYNTHETIC GPU ABSENT")), \
                 patch.object(preflight, "export", side_effect=OSError("SYNTHETIC EXPORT ENOSPC")), \
                 patch.object(owner, "reserve", side_effect=AssertionError("SLOT_FORBIDDEN")), \
                 self.assertRaises(OSError):
                preflight.launch_preflight("internvl35", c.source_hash(), ROOT, "a"*40,
                    inputs=root/"input", work=root/"out")
            report = read(next((root/"out").glob("*/preflight.json")))
            self.assertEqual(report["status"], "BLOCKED")
            self.assertFalse(report["attempt_consumed"])
            self.assertFalse(list((root/"out").glob("**/owner_slot*")))

    def test_independent_checks_partial_failures_and_never_reserves_or_calls_model(self):
        for key in c.KEYS:
            for fault in (None, "input", "checkpoint", "storage", "python", "cpu", "gpu", "cuda", "resource",
                          "package", "child_missing", "child_status", "child_source", "child_ref", "child_model", "child_incomplete",
                          "cleanup", "export", "sidecar", "images"):
                with self.subTest(key=key, fault=fault), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                    root = Path(d)
                    bundle = root/"input/notebooks/account/bundle"
                    bundle.mkdir(parents=True)
                    plan, _ = fixture(bundle)
                    write(bundle/"pilot_manifest.json", plan)
                    write(bundle/"marker", {"scope": "SYNTHETIC_CHECKPOINT_MARKER"})
                    stack.enter_context(patch.object(c, "MANIFEST", sha(bundle/"pilot_manifest.json")))
                    stack.enter_context(patch.object(preflight, "environment_observation", return_value={
                        "kernel": {"system": "Linux", "machine": "x86_64", "pointer_bits": 64, "version": "3.13.15"}, "scope": "SYNTHETIC"}))
                    scratch = root/"tmp"
                    scratch.mkdir()
                    stack.enter_context(patch.object(preflight.boot, "provision_scratch_root", return_value=scratch))
                    stack.enter_context(patch.object(preflight, "checkpoint", side_effect=ValueError("SYNTHETIC CHECKPOINT") if fault == "checkpoint" else None,
                                                     return_value=(bundle/"marker", root/"source", root/"weights")))
                    stack.enter_context(patch("safeshift.candidates.source.verify_snapshot", return_value={}))
                    stack.enter_context(patch.object(preflight, "verify_weights", return_value={}))
                    stack.enter_context(patch.object(preflight, "stage_snapshot", return_value={}))
                    stack.enter_context(patch.object(preflight.boot, "storage_admission", return_value={"admitted": fault != "storage"}))
                    from safeshift.candidates import train_runtime as rt
                    stack.enter_context(patch.object(rt, "prepare_runtime", side_effect=ValueError("SYNTHETIC PYTHON") if fault == "python" else None,
                                                     return_value=(Path("SYNTHETIC_PYTHON"), {})))
                    stack.enter_context(patch.object(rt, "hardware", side_effect=ValueError("SYNTHETIC GPU") if fault == "gpu" else None,
                                                     return_value={"scope": "SYNTHETIC_NO_GPU"}))
                    reserve = stack.enter_context(patch.object(owner, "reserve", side_effect=AssertionError("SLOT_FORBIDDEN")))
                    execution = stack.enter_context(patch.object(owner, "execution", side_effect=AssertionError("EXECUTION_FORBIDDEN")))
                    def child(command, **kwargs):
                        self.assertIn("safeshift.candidates.train_preflight", command)
                        self.assertNotIn("--execution", command)
                        output = Path(command[command.index("--output")+1])
                        suffix = "software_cpu" if "--software-only" in command else "cuda_child" if "--cuda" in command else "live_resources" if "--resources" in command else "images_cpu" if "--images" in command else "cpu_native"
                        if (fault, suffix) in (("cpu", "cpu_native"), ("cuda", "cuda_child"), ("resource", "live_resources"),
                                               ("package", "software_cpu"), ("images", "images_cpu")):
                            raise subprocess.CalledProcessError(1, "SYNTHETIC")
                        receipt = {"schema": preflight.CHILD_SCHEMA, "status": "PASS", "check": suffix,
                            "model_key": key, "source_sha256": command[command.index("--source")+1],
                            "runtime_ref": command[command.index("--ref")+1], "evidence": synthetic_child_evidence(suffix, key)}
                        if suffix == "software_cpu":
                            if fault == "child_missing":
                                return
                            for invalid, field, value in (("child_status", "status", "BLOCKED"), ("child_source", "source_sha256", "0"*64),
                                                          ("child_ref", "runtime_ref", "b"*40), ("child_model", "model_key", "wrong"),
                                                          ("child_incomplete", "evidence", {})):
                                if fault == invalid:
                                    receipt[field] = value
                        self.assertEqual(kwargs["env"]["CUDA_VISIBLE_DEVICES"], "0" if suffix == "cuda_child" else "")
                        write(output/(suffix+".json"), receipt)
                    stack.enter_context(patch.object(preflight.subprocess, "run", side_effect=child))
                    if fault == "cleanup":
                        stack.enter_context(patch.object(preflight.boot, "cleanup_scratch", side_effect=OSError("SYNTHETIC CLEANUP")))
                    if fault == "export":
                        stack.enter_context(patch.object(preflight, "export", side_effect=OSError("SYNTHETIC EXPORT")))
                    if fault == "sidecar":
                        real_export = preflight.export
                        def corrupt_export(out, archive):
                            real_export(out, archive)
                            Path(str(archive)+".sha256.json").write_text('{"sha256":"WRONG"}')
                        stack.enter_context(patch.object(preflight, "export", side_effect=corrupt_export))
                    if fault == "input":
                        (bundle/"pilot_manifest.json").unlink()
                    if fault in ("export", "sidecar"):
                        with self.assertRaises((OSError, ValueError)):
                            preflight.launch_preflight(key, c.source_hash(), ROOT, "a"*40,
                                inputs=root/"input", work=root/"out", scratch_root=scratch)
                        output = next(p for p in (root/"out").iterdir() if p.is_dir())
                    else:
                        output = preflight.launch_preflight(key, c.source_hash(), ROOT, "a"*40,
                            inputs=root/"input", work=root/"out", scratch_root=scratch)
                    report = read(Path(str(output)+".preflight-result.json"))
                    self.assertEqual(report["status"], "PRELOAD_CHECKS_PASS_MODEL_UNVERIFIED" if fault is None else "BLOCKED", report)
                    self.assertIs(report["attempt_consumed"], False)
                    self.assertEqual(report["native_calls"], 0)
                    self.assertFalse(list((root/"out").glob("**/owner_slot*")))
                    reserve.assert_not_called()
                    execution.assert_not_called()
                    self.assertEqual(report["levels"]["WEIGHTS_LOADED"], "NOT_RUN")
                    self.assertEqual(report["levels"]["INFERENCE_VERIFIED"], "NOT_RUN")
                    self.assertEqual(report["levels"]["SCIENTIFIC_QUALIFIED"], "UNVERIFIED")
                    if fault == "package" or str(fault).startswith("child_"):
                        self.assertNotEqual(report["levels"]["CPU_SOFTWARE_PASS"], "PASS")
                        self.assertEqual(report["checks"]["cuda_child"]["status"], "NOT_RUN")
                    if fault == "gpu":
                        self.assertEqual(report["checks"]["cuda_child"]["status"], "NOT_RUN")
                    if fault in ("export", "sidecar"):
                        staged = read(output/"preflight.json")
                        self.assertEqual(staged["status"], "PRELOAD_CHECKS_PASS_MODEL_UNVERIFIED")
                        self.assertTrue(staged["evidence_export"].startswith("PENDING"))
                        self.assertEqual(report["evidence_export"], "BLOCKED")
                        self.assertEqual(report["status"], "BLOCKED")
                    if fault not in ("export", "sidecar"):
                        verify_archive(Path(str(output)+".zip"))


class IncidentTests(unittest.TestCase):
    def evidence(self, root):
        directory = root/"data/processed/candidate160/internvl35-old"
        directory.mkdir(parents=True)
        plan, rows = fixture(directory)
        write(directory/"pilot_manifest.json", plan)
        checksum = sha(directory/"pilot_manifest.json")
        # fixture images are not part of the actual zero-call archive.
        for row in rows:
            Path(row["image"]).unlink()
        (directory/"images").rmdir()
        self.enterContext(patch.object(c, "MANIFEST", checksum))
        self.enterContext(patch.object(incident, "MANIFEST", checksum))
        value = owner.execution("internvl35", "a"*64, "b"*40, owner_start=True)
        reservation = {"schema": "safeshift-candidate160-owner-slot-v1", "status": "RESERVED_NO_RETRY",
                       "slot_sha256": value["slot_sha256"], "execution_sha256": digest(value),
                       "run_id": value["run_id"], "attempt_id": value["attempt_id"], "model_key": "internvl35", "manifest_sha256": checksum}
        write(directory/"owner_execution.json", value)
        failure = {"message": "UNIQUE_candidate_checkpoint_internvl35.json_REQUIRED_FOUND_0", "type": "ValueError", "stage": "checkpoint_source"}
        terminal = {**reservation, "status": "BLOCKED_RESERVED_NO_RETRY", "attempt_consumed": False, "stage": "checkpoint_source", "failure": failure}
        write(directory/"owner_consumption_log.json", terminal)
        write(directory/"supervisor_status.json", {"status": "BLOCKED", "attempt_consumed": False, "stage": "checkpoint_source",
              "failure": failure, "source_sha256": value["source_sha256"], "runtime_ref": value["runtime_ref"]})
        write(directory/"supervisor_failure.json", failure)
        write(directory/"supervisor_accounting.json", [{"ordinal": i, "sample_id": row["sample_id"], "status": "NOT_ATTEMPTED",
              "label": None, "attempts": 0, "native_calls": 0} for i, row in enumerate(rows)])
        name = "owner_slot_"+value["slot_sha256"]+".json"
        write(directory/name, reservation)
        write(root/"data/processed/candidate160/attempts"/name, reservation)
        write(directory/"checksums.json", {p.name: sha(p) for p in directory.iterdir()})
        return directory, reservation, name

    def test_one_distinct_traceable_replacement_same_campaign_and_no_replay(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            mount = root/"inputs/notebooks/account/prior"
            directory, original, name = self.evidence(mount)
            work = root/"work"
            work.mkdir()
            before = {p: sha(p) for p in directory.iterdir()}
            value = owner.execution("internvl35", "c"*64, "d"*40, owner_start=True)
            new_name, record = owner.reserve(work, value, root/"inputs")
            self.assertEqual(new_name, name.removesuffix(".json")+".replacement1.json")
            self.assertEqual(record["replacement_incident"]["original_run_id"], original["run_id"])
            self.assertEqual(record["slot_sha256"], original["slot_sha256"])
            self.assertEqual(value["campaign"], owner.CAMPAIGN)
            self.assertEqual({p: sha(p) for p in directory.iterdir()}, before)
            with self.assertRaisesRegex(ValueError, "REPLACEMENT_ALREADY_RESERVED"):
                owner.reserve(work, owner.execution("internvl35", "e"*64, "f"*40, owner_start=True), root/"inputs")

    def test_partial_tampered_consumed_unknown_or_nonzero_never_replace(self):
        for fault in ("seal", "missing", "consumed", "unknown", "calls", "attempts", "extra", "reason", "execution"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                directory, original, name = self.evidence(root/"inputs/notebooks/account/prior")
                member = "owner_consumption_log.json" if fault in ("consumed", "unknown") else "supervisor_accounting.json"
                if fault == "seal":
                    (directory/"checksums.json").unlink()
                elif fault == "missing":
                    (directory/"supervisor_status.json").unlink()
                elif fault == "extra":
                    write(directory/"consumption.json", {"attempt_consumed": True})
                else:
                    if fault in ("reason", "execution"):
                        member = "supervisor_failure.json" if fault == "reason" else "owner_execution.json"
                    record = read(directory/member)
                    if fault in ("consumed", "unknown"):
                        record["attempt_consumed"] = True if fault == "consumed" else None
                    elif fault in ("calls", "attempts"):
                        record[0]["native_calls" if fault == "calls" else "attempts"] = 1
                    elif fault == "reason":
                        record["message"] = "other failure"
                    else:
                        record["split"] = "TEST"
                    (directory/member).write_text(json.dumps(record))
                    # Reseal to check semantic contradictions as well as SHA drift.
                    checks = read(directory/"checksums.json")
                    checks[member] = sha(directory/member)
                    (directory/"checksums.json").write_text(json.dumps(checks))
                work = root/"work"
                work.mkdir()
                with self.assertRaises(ValueError):
                    owner.reserve(work, owner.execution("internvl35", "c"*64, "d"*40, owner_start=True), root/"inputs")
                self.assertFalse((work/"attempts"/name.replace(".json", ".replacement1.json")).exists())

    def test_replacement_supervisor_consumes_distinct_marker_preserves_old_and_blocks_second_run(self):
        from safeshift.candidates import train_runtime as rt, train_run as run
        from test_candidate160 import Scripted
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            root = Path(d)
            directory, original, original_name = self.evidence(root/"input/notebooks/account/prior")
            old_hashes = {p: sha(p) for p in directory.iterdir()}
            bundle = root/"input/bundle"
            bundle.mkdir()
            plan, rows = fixture(bundle)
            write(bundle/"pilot_manifest.json", plan)
            scratch = root/"scratch"
            scratch.mkdir()
            backend = Scripted(key="internvl35")
            stack.enter_context(patch.object(rt, "checkpoint", return_value=(root/"marker", root/"source", root/"weights")))
            stack.enter_context(patch.object(rt, "MANIFEST", sha(bundle/"pilot_manifest.json")))
            stack.enter_context(patch.object(rt, "verify_weights", return_value={}))
            stack.enter_context(patch.object(rt, "stage_snapshot", return_value={}))
            stack.enter_context(patch.object(rt.boot, "provision_scratch_root", return_value=scratch))
            stack.enter_context(patch.object(rt.boot, "storage_admission", return_value={"admitted": True}))
            stack.enter_context(patch.object(rt, "prepare_runtime", return_value=(Path("SYNTHETIC_PYTHON"), {})))
            stack.enter_context(patch.object(rt, "hardware", return_value={"scope": "SYNTHETIC"}))
            def child(command, **kwargs):
                output = Path(command[command.index("--output")+1])
                if "--check-only" in command:
                    return
                if "--cuda-check-only" in command:
                    write(output/"preledger_cuda.json", {"worker_cuda": "MEASURED_FP16_FUNCTIONAL", "scope": "SYNTHETIC"})
                    return
                g = read(output/"owner_execution.json")
                self.assertTrue(read(output/"consumption.json")["attempt_consumed"])
                run.run_calls(output, plan, rows, lambda: backend, g, resources=lambda: {})
            stack.enter_context(patch.object(rt.subprocess, "run", side_effect=child))
            output = rt.launch_owner("internvl35", c.source_hash(), ROOT, "a"*40, owner_start=True,
                inputs=root/"input", work=root/"out", scratch_root=scratch)
            self.assertIs(read(output/"supervisor_status.json")["attempt_consumed"], True)
            self.assertEqual(backend.calls, 160)
            new_name = original_name.removesuffix(".json")+".replacement1.json"
            self.assertTrue((root/"out/attempts"/(new_name.removesuffix(".json")+".consumed.json")).is_file())
            self.assertFalse((root/"out/attempts"/(original_name.removesuffix(".json")+".consumed.json")).exists())
            self.assertEqual({p: sha(p) for p in directory.iterdir()}, old_hashes)
            second = rt.launch_owner("internvl35", c.source_hash(), ROOT, "a"*40, owner_start=True,
                inputs=root/"input", work=root/"out", scratch_root=scratch)
            self.assertEqual(read(second/"supervisor_status.json")["status"], "BLOCKED")
            self.assertEqual(backend.calls, 160)
