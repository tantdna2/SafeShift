"""Stdlib fault boundaries, separate from opt-in native library integration."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from safeshift.pilot.artifacts import export, import_archive, read, sha, write_bytes
from safeshift.pilot.diagnostics import phase
from safeshift.pilot import bootstrap as b
from safeshift.pilot.contract import source_digest
from test_pilot_bootstrap import ROOT, supervisor_case
from types import SimpleNamespace as NS
from safeshift.pilot.phi_inputs import checkpoint_metadata
from safeshift.pilot.backend import check_source_review
from safeshift.pilot.contract import MODELS


class DiagnosticTests(unittest.TestCase):
    def test_cli_package_is_private_t4x2_and_never_runs_or_issues_grant(self):
        import json
        from scripts.package_phi_kaggle import package
        from scripts.build_three_vlm_notebooks import notebook
        with tempfile.TemporaryDirectory(dir=ROOT / "data/processed") as directory:
            output = Path(directory) / "package"
            value = package(output, "synthetic-owner/synthetic-kernel", "synthetic-owner/input", "synthetic-owner/grant")
            self.assertTrue(value["is_private"] and value["enable_gpu"] and value["enable_internet"])
            self.assertEqual(value["machine_shape"], "NvidiaTeslaT4")
            self.assertEqual(json.loads((output / value["code_file"]).read_bytes()), notebook("phi"))
            self.assertEqual(len(list(output.iterdir())), 2)
            with self.assertRaises(FileExistsError):
                package(output, "synthetic-owner/synthetic-kernel", "synthetic-owner/input", "synthetic-owner/grant")
            with self.assertRaises(ValueError):
                package(output, "../invalid", "synthetic-owner/input", "synthetic-owner/grant")

    def test_corrupt_notebook_payload_exports_before_import_or_consumption(self):
        import base64
        import hashlib
        import json
        import subprocess
        import sys
        from scripts.build_three_vlm_notebooks import notebook
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = "".join(notebook("phi")["cells"][1]["source"])
            checksum = source_digest(ROOT)
            code = code.replace(repr(checksum), repr("f" * 64))
            code = code.replace("/kaggle/working/data/processed/three_vlm_bootstrap", root.as_posix())
            script = root / "synthetic_notebook.py"
            script.write_text(code, encoding="utf-8")
            result = subprocess.run([sys.executable, "-B", str(script)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            archives = list(root.glob("*.zip"))
            self.assertEqual(len(archives), 1)
            recovered = import_archive(archives[0], root / "recovered")
            self.assertEqual(read(recovered / "failure.json")["constraint"], "EMBEDDED_SOURCE_CORRUPT")
            self.assertFalse(read(recovered / "failure.json")["attempt_consumed"])

    def test_checkpoint_metadata_rejects_revision_paths_missing_lfs_and_code(self):
        code = [NS(rfilename=name, lfs=None) for name in check_source_review(ROOT, "phi")["files"]]
        weights = [NS(rfilename=f"model-0000{i}-of-00002.safetensors", lfs={"sha256": "a" * 64, "size": 4000})
                   for i in (1, 2)]
        info = NS(sha=MODELS["phi"]["revision"], siblings=code + weights + [NS(rfilename="model.safetensors.index.json")])
        self.assertEqual(checkpoint_metadata(ROOT, info)["total_weight_bytes"], 8000)
        import copy
        for defect in ("revision", "path", "missing", "lfs", "code"):
            with self.subTest(defect=defect):
                bad = copy.deepcopy(info)
                if defect == "revision":
                    bad.sha = "b" * 40
                elif defect == "path":
                    bad.siblings[-2].rfilename = "../weight.safetensors"
                elif defect == "missing":
                    bad.siblings.pop()
                elif defect == "lfs":
                    bad.siblings[-2].lfs = None
                else:
                    bad.siblings.append(NS(rfilename="unknown.py"))
                with self.assertRaises(ValueError):
                    checkpoint_metadata(ROOT, bad)

    def test_constructor_failure_carries_stage_and_config_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            error = ValueError("PHI_EXPLICIT_EAGER_CONFIG_REQUIRED:vision.config")
            error.phi_attention_receipt = {"configs": {"vision.config": {"internal": "sdpa"}}}
            with self.assertRaises(ValueError):
                with phase(directory, "model_load", "phi_from_pretrained"):
                    raise error
            records = list((Path(directory) / "diagnostics").glob("*.failure.json"))
            record = read(records[0])
            self.assertEqual(record["stage"], "model_load")
            self.assertEqual(record["attention"], error.phi_attention_receipt)
            self.assertEqual(error.subcomponent, "phi_from_pretrained")

    def test_nested_phases_preserve_inner_origin_and_export_failure_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "SYNTHETIC") as caught:
                with phase(directory, "model_load", "constructor"):
                    with phase(directory, "processor_load", "native_processor"):
                        raise ValueError("SYNTHETIC")
            self.assertEqual(caught.exception.stage, "processor_load")
            self.assertEqual(caught.exception.subcomponent, "native_processor")
        with supervisor_case() as case, patch.object(b, "export", side_effect=OSError("SYNTHETIC_EXPORT_ERROR")):
            output = b.launch("phi", case[4]["source_sha256"], ROOT, case[1], case[2],
                              scratch_root=case[0] / "tmp")
            receipt = read(Path(str(output.with_suffix(".zip")) + ".export_failure.json"))
            self.assertTrue(receipt["attempt_consumed"])
            self.assertEqual(receipt["stage"], "export")

    def test_bounded_log_export_retains_full_original_and_tail_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "evidence"
            payload = b"SYNTHETIC_FULL_LOG" * 1000
            write_bytes(root / "worker.log", payload)
            original = sha(root / "worker.log")
            archive = Path(directory) / "evidence.zip"
            export(root, archive, log_limit=512)
            recovered = import_archive(archive, Path(directory) / "recovered")
            self.assertEqual(sha(root / "worker.log"), original)
            record = read(recovered / "log_exports.json")["worker.log"]
            self.assertEqual(record["original_sha256"], original)
            self.assertEqual((recovered / record["exported_path"]).read_bytes(), payload[-512:])
            self.assertEqual(sha(recovered / record["exported_path"]), record["exported_sha256"])
            with self.assertRaises(FileExistsError):
                export(root, archive)

    def test_mixed_source_grant_fails_before_dataset_or_installer(self):
        with supervisor_case() as case:
            # Existing attached grant points to the old notebook's source.
            with patch.object(b, "source_digest", return_value="f" * 64), \
                    patch.object(b, "load_bundle", side_effect=AssertionError("NO_DATA")):
                output = b.launch("phi", source_digest(ROOT), ROOT, case[1], case[2],
                                  scratch_root=case[0] / "tmp")
            self.assertFalse(read(output / "session.json")["attempt_consumed"])
            self.assertEqual(read(output / "supervisor_failure.json")["stage"], "authority")

    def test_exclusive_consumption_race_keeps_winner_no_second_worker(self):
        with supervisor_case() as case:
            native_write = b.write
            attempt = case[2] / "data/processed/three_vlm_attempts" / case[4]["attempt_id"]
            def competing_writer(path, value):
                if Path(path) == attempt:
                    native_write(path, {"SYNTHETIC_WINNER": True})
                return native_write(path, value)
            with patch.object(b, "write", competing_writer):
                output = b.launch("phi", case[4]["source_sha256"], ROOT, case[1], case[2],
                                  scratch_root=case[0] / "tmp")
            self.assertEqual(read(attempt), {"SYNTHETIC_WINNER": True})
            self.assertFalse(read(output / "session.json")["attempt_consumed"])
            self.assertFalse(any("safeshift.pilot.runner" in command for command, _ in case[5]))


if __name__ == "__main__":
    unittest.main()
