"""Smol/Gemma CPU fault boundaries with synthetic fixtures and no ML imports."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import zipfile

from safeshift.pilot import bootstrap as b
from safeshift.pilot.artifacts import export, import_archive, read, sha, write, write_bytes
from safeshift.pilot.backend import check_source_review
from safeshift.pilot.contract import MODELS, source_digest
from safeshift.pilot.output_diagnostics import summarize
from safeshift.pilot.runner import error_record
from safeshift.pilot import runner
from safeshift.pilot.contract import digest, json_bytes
from safeshift.pilot.smol import checkpoint_metadata, verified_index
from test_pilot_bootstrap import ROOT, supervisor_case


class SmolEvidenceTests(unittest.TestCase):
    def test_index_checksum_and_mapping_corruption_block_without_model_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index_path = root / "snapshot/model.safetensors.index.json"
            index = {"metadata": {"total_size": 8}, "weight_map": {
                "a.weight": "model-00001-of-00002.safetensors", "b.weight": "model-00002-of-00002.safetensors"}}
            write(index_path, index)
            lock = {"revision": MODELS["smolvlm2"]["revision"], "index": {
                "filename": index_path.name, "sha256": sha(index_path), "bytes": index_path.stat().st_size,
                "tensor_count": 2, "total_tensor_bytes": 8}, "weights": {value: {} for value in index["weight_map"].values()}}
            write(root / "configs/pilot/smol_checkpoint_metadata.json", lock)
            self.assertEqual(verified_index(root, index_path.parent), index)
            for defect in ("checksum", "mapping"):
                bad = copy.deepcopy(index)
                bad["weight_map"]["a.weight"] = "unreviewed.safetensors"
                index_path.write_bytes(__import__("safeshift.pilot.contract", fromlist=["json_bytes"]).json_bytes(bad))
                if defect == "mapping":
                    lock["index"].update(sha256=sha(index_path), bytes=index_path.stat().st_size)
                    (root / "configs/pilot/smol_checkpoint_metadata.json").write_bytes(
                        __import__("safeshift.pilot.contract", fromlist=["json_bytes"]).json_bytes(lock))
                with self.subTest(defect=defect), self.assertRaises(ValueError):
                    verified_index(root, index_path.parent)

    def test_checkpoint_revision_inventory_lfs_no_weight_request(self):
        sources = [NS(rfilename=name, lfs=None) for name in check_source_review(ROOT, "smolvlm2")["files"]]
        lock = read(ROOT / "configs/pilot/smol_checkpoint_metadata.json")
        weights = [NS(rfilename=name, lfs={"sha256": value["sha256"], "size": value["bytes"]})
                   for name, value in lock["weights"].items()]
        info = NS(sha=MODELS["smolvlm2"]["revision"], siblings=sources + [NS(rfilename=lock["index"]["filename"])] + weights)
        self.assertEqual(checkpoint_metadata(ROOT, info)["weight_bytes"], "NOT_REQUESTED")
        for defect in ("revision", "lfs", "missing", "duplicate", "code", "escape", "source"):
            bad = copy.deepcopy(info)
            if defect == "revision":
                bad.sha = "f" * 40
            elif defect == "lfs":
                bad.siblings[-1].lfs = None
            elif defect == "missing":
                bad.siblings.pop()
            elif defect == "duplicate":
                bad.siblings.append(copy.deepcopy(bad.siblings[0]))
            elif defect == "code":
                bad.siblings.append(NS(rfilename="unreviewed.py"))
            elif defect == "escape":
                bad.siblings[-1].rfilename = "../model.safetensors"
            else:
                bad.siblings.pop(0)
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                checkpoint_metadata(ROOT, bad)

    def test_gemma_stays_blocked_and_unauthenticated_401_is_access_error(self):
        with self.assertRaisesRegex(PermissionError, "BLOCKED_SOURCE_TOKENIZER_AUDIT_INCOMPLETE:gemma"):
            check_source_review(ROOT, "gemma")
        locked = read(ROOT / "configs/pilot/model_source_lock.json")["gemma"]
        self.assertEqual(locked["files"], {})
        self.assertEqual(len(locked["unavailable"]), 10)
        error = HTTPError("https://huggingface.co/synthetic", 401, "Unauthorized", {}, None)
        self.assertEqual(error_record(error, "source_audit")["category"], "ACCESS")

    def test_native_cpu_failure_is_exported_before_hardware_or_ledger(self):
        for part in ("source_hashes", "from_pretrained_meta", "native_processor", "checkpoint_metadata"):
            error = RuntimeError("SYNTHETIC_SMOL_ADMISSION_FAILURE")
            error.subcomponent = "smol_" + part
            with self.subTest(part=part), supervisor_case(key="smolvlm2") as case, \
                    patch.object(b, "validate_runtime_environment", side_effect=error), \
                    patch.object(b, "gpu_preflight", side_effect=AssertionError("NO_GPU")):
                out = b.launch("smolvlm2", case[4]["source_sha256"], ROOT, case[1], case[2], scratch_root=case[0] / "tmp")
                self.assertFalse(read(out / "session.json")["attempt_consumed"])
                self.assertFalse((case[2] / "data/processed/three_vlm_attempts" / case[4]["attempt_id"]).exists())
                self.assertEqual(read(out / "runtime_preflight.json")["status"], "BLOCKED")
                imported = import_archive(out.with_suffix(".zip"), case[0] / "saved_outputs")
                self.assertTrue((imported / "runtime_preflight.json").is_file())
                self.assertFalse(any("safeshift.pilot.runner" in cmd for cmd, _ in case[5]))

    def test_report_failure_has_worker_phase_and_export_failure_keeps_consumption(self):
        with supervisor_case(key="smolvlm2") as case:
            root, inputs, _, plan, grant, _, _ = case
            results = {r["sample_id"]: {"status": "NOT_ATTEMPTED", "attempts": 0} for r in plan["main"]}
            with patch.dict("os.environ", {"SAFESHIFT_WORKER_PYTHON": "synthetic", "SAFESHIFT_RUNTIME_ROOT": "synthetic"}), \
                    patch.object(b, "runtime_identity", return_value={"SYNTHETIC": True}), \
                    patch.object(runner, "load_bundle", return_value=(plan, plan["main"])), \
                    patch.object(runner, "execute", return_value=(results, True)), \
                    patch.object(runner, "save_reports", side_effect=OSError("SYNTHETIC_REPORT_IO")):
                with self.assertRaisesRegex(OSError, "REPORT_IO") as caught:
                    runner.run(ROOT, inputs / "private", grant, grant["source_sha256"], root / "worker")
            self.assertEqual(caught.exception.stage, "report")
            receipt = next((root / "worker/diagnostics").glob("*.failure.json"))
            self.assertEqual(read(receipt)["subcomponent"], "planned_id_reports")
            export(root / "worker", root / "partial-worker.zip")
            import_archive(root / "partial-worker.zip", root / "saved-worker-outputs")
        with supervisor_case(key="smolvlm2") as case, patch.object(b, "export", side_effect=OSError("SYNTHETIC_EXPORT_IO")):
            out = b.launch("smolvlm2", case[4]["source_sha256"], ROOT, case[1], case[2], scratch_root=case[0] / "tmp")
            failure = read(Path(str(out.with_suffix(".zip")) + ".export_failure.json"))
            self.assertTrue(failure["attempt_consumed"])
            self.assertEqual(failure["stage"], "export")

    def test_smol_duplicate_missing_wrong_grant_and_stale_attempt_before_consumption(self):
        for defect in ("duplicate", "missing", "wrong_model", "old_source", "attempt", "missing_bundle"):
            with self.subTest(defect=defect), supervisor_case(key="smolvlm2") as case:
                root, inputs, work, _, grant, calls, _ = case
                attached = inputs / "private/grant_smolvlm2.json"
                if defect == "duplicate":
                    write(inputs / "second/grant_smolvlm2.json", grant)
                elif defect == "missing":
                    attached.unlink()
                elif defect in ("wrong_model", "old_source"):
                    value = {**grant, **({"model_key": "phi"} if defect == "wrong_model" else {"source_sha256": "f" * 64})}
                    attached.write_bytes(json_bytes(value))
                elif defect == "attempt":
                    write(work / "data/processed/three_vlm_attempts" / grant["attempt_id"], {"SYNTHETIC_ALREADY_CONSUMED": True})
                else:
                    (inputs / "private/bundle.json").unlink()
                out = b.launch("smolvlm2", grant["source_sha256"], ROOT, inputs, work, scratch_root=root / "tmp")
                self.assertFalse(read(out / "session.json")["attempt_consumed"])
                self.assertFalse(calls)
                self.assertTrue(out.with_suffix(".zip").exists())

    def test_partial_zip_rejected_and_descriptive_diagnostics_do_not_repair_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i in range(12):
                write(root / f"evidence/run/samples/{i:06d}/raw.json",
                      {"generated_ids": [1, 2, 3], "response": "Level04", "eos_token_ids": [3]})
            before = {p: sha(p) for p in (root / "evidence").rglob("raw.json")}
            summary = summarize(root / "evidence/run")
            self.assertEqual((summary["strict_json_invalid"], summary["unique_token_sequences"]), (12, 1))
            self.assertEqual(before, {p: sha(p) for p in before})
            archive = root / "evidence.zip"
            export(root / "evidence", archive)
            write_bytes(root / "partial.zip", archive.read_bytes()[:200])
            with self.assertRaises(zipfile.BadZipFile):
                import_archive(root / "partial.zip", root / "bad_saved_outputs")
            from scripts.diagnose_pilot_outputs import diagnose
            with patch("scripts.diagnose_pilot_outputs.processed", return_value=root / "summary.json"):
                actual = diagnose(archive, "data/processed/summary.json")
            self.assertEqual(actual["largest_identical_token_sequence_n"], 12)
            self.assertEqual(read(root / "summary.json.sha256.json")["sha256"], sha(root / "summary.json"))
            Path(str(archive) + ".sha256.json").write_text('{"sha256":"' + 'f' * 64 + '"}')
            with self.assertRaisesRegex(ValueError, "EXTERNAL_SIDECAR"):
                diagnose(archive, "data/processed/unused.json")


if __name__ == "__main__":
    unittest.main()
