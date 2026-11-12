"""Exercise the packaged notebook and shared boundaries; synthetic CPU only."""
import base64
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zlib
from unittest.mock import patch

from safeshift.candidates.source import ROOT
from safeshift.fulltrain import contract, minicpm_notebook as entry
from safeshift.pilot.artifacts import read, sha, write, verify_archive
from safeshift.pilot.contract import digest, parse_label
from scripts.generate_minicpm_fulltrain_notebook import notebook, OUTPUT


class MiniCPMFulltrainNotebookTests(unittest.TestCase):
    def setUp(self):
        self.nb = read(ROOT / OUTPUT)

    def code(self):
        return "\n".join("".join(c["source"]) for c in self.nb["cells"] if c["cell_type"] == "code")

    def test_exact_builder_committed_payload_syntax_and_no_cell_output(self):
        meta = self.nb["metadata"]["safeshift"]
        self.assertEqual(meta["status"], "BLOCKED_NOT_LIVE_VERIFIED")
        self.assertIsNone(meta["execution_caps"])
        self.assertEqual(meta["series_id"], "fresh171-minicpm4-v1")
        self.assertEqual(meta["policy"], "LABEL_ONLY")
        self.assertEqual((ROOT / OUTPUT).read_bytes(), (json.dumps(notebook(meta["runtime_ref"]),
            indent=1, ensure_ascii=False) + "\n").encode())
        for cell in self.nb["cells"]:
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), cell.get("id", "cell"), "exec")
                self.assertEqual(cell["outputs"], [])
                self.assertIsNone(cell["execution_count"])
        encoded = re.search(r"base64\.b64decode\('([^']+)'\)", self.code()).group(1)
        payload = json.loads(zlib.decompress(base64.b64decode(encoded)))
        self.assertEqual(set(payload), set(contract.sources()))
        for name, text in payload.items():
            self.assertEqual(text.encode(), (ROOT / name).read_bytes(), name)
            if name.endswith(".py"):
                compile(text, name, "exec")
        self.assertIn("safeshift/fulltrain/runtime.py", payload)
        self.assertIn("safeshift/candidates/minicpm_resampler_fp32.py", payload)

    def test_clean_cpu_cells_repeated_without_network_tensor_model_or_input_access(self):
        guard = '''
import importlib.abc, socket, sys
class Forbidden(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('torch', 'transformers', 'PIL', 'kaggle', 'kagglehub'):
            raise AssertionError('HEAVY_OR_PROVIDER_IMPORT_FORBIDDEN:' + fullname)
sys.meta_path.insert(0, Forbidden())
def no_network(*args, **kwargs): raise AssertionError('NETWORK_FORBIDDEN')
socket.socket.connect = no_network
socket.create_connection = no_network
'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "notebook.py"
            script.write_text(guard + self.code(), encoding="utf8")
            for _ in range(2):
                child = subprocess.run([sys.executable, "-B", "-S", str(script)], cwd=root,
                    env={**os.environ, "PYTHONPATH": "", "CUDA_VISIBLE_DEVICES": ""},
                    capture_output=True, text=True, timeout=60)
                self.assertEqual(child.returncode, 0, child.stderr)
            archives = list((root / "data/processed/minicpm_fulltrain").glob("*.zip"))
            self.assertEqual(len(archives), 2)
            for archive in archives:
                self.assertIn("pipeline.json", verify_archive(archive))
                report = read(archive.with_suffix("") / "release.json")
                self.assertEqual(report["status"], "BLOCKED")
                self.assertEqual(report["native_calls"], 0)
                self.assertFalse(report["attempt_consumed"])
                self.assertFalse(report["production_ledger_written"])
                self.assertEqual(report["levels"]["WEIGHTS_LOADED"], "NOT_RUN")
                self.assertEqual(sha(archive), read(Path(str(archive) + ".sha256.json"))["sha256"])

    def test_corrupt_embedded_source_fails_before_preparation(self):
        code = self.code().replace(self.nb["metadata"]["safeshift"]["source_sha256"], "0" * 64)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.py"
            path.write_text(code, encoding="utf8")
            r = subprocess.run([sys.executable, "-B", "-S", str(path)], cwd=tmp,
                               capture_output=True, text=True, timeout=60)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("EMBEDDED_SOURCE_CORRUPT", r.stderr)
            self.assertFalse((Path(tmp) / "data/processed/minicpm_fulltrain").exists())

    def test_production_gate_precedes_request_path_hash_import_or_model(self):
        class Poison:
            def __fspath__(self): raise AssertionError("PRIVATE_IO_FORBIDDEN")
        with patch("safeshift.fulltrain.runtime.launch") as launch:
            with self.assertRaisesRegex(PermissionError, "ISSUE171_NO_GPU"):
                entry.run_request(Poison(), "invalid")
            launch.assert_not_called()

    def test_future_request_boundary_calls_shared_pipeline_and_rejects_foreign_or_corrupt(self):
        # Only this test replaces the immutable release gate. No GPU/native code
        # is run: it verifies delegation, byte pin and JSON boundary ordering.
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "request.json"
            write(p, {"model_key": "minicpm4"})
            with patch.object(contract, "authorize"), \
                 patch("safeshift.fulltrain.admission.validate_request") as admit, \
                 patch("safeshift.fulltrain.runtime.launch", return_value="shared") as launch:
                self.assertEqual(entry.run_request(p, sha(p)), "shared")
                admit.assert_called_once_with({"model_key": "minicpm4"}, ROOT)
                launch.assert_called_once_with({"model_key": "minicpm4"}, repo=ROOT)
                for content, expected in ((b'{"model_key":"qwen3"}', "MINICPM_ONLY"),
                    (b'{"model_key":"minicpm4","model_key":"minicpm4"}', "DUPLICATE_JSON_KEY")):
                    p.write_bytes(content)
                    launch.reset_mock()
                    with self.assertRaisesRegex(ValueError, expected): entry.run_request(p, sha(p))
                    launch.assert_not_called()
                with self.assertRaisesRegex(ValueError, "REQUEST_PIN"): entry.run_request(p, "f"*64)
                p.unlink()
                with self.assertRaises(FileNotFoundError): entry.run_request(p, "f"*64)

    def test_real_c1_parser_rejects_previous_notebook_rescues(self):
        for i in range(1, 5):
            valid = '{"safety_level":"Level0' + str(i) + '"}'
            self.assertEqual(parse_label(valid), "Level0" + str(i))
            for invalid in ("prose " + valid, valid + " extra", "```json\n" + valid + "\n```",
                            "The assessed level is Level0" + str(i) + ".", valid[:-1] + ',"x":0}'):
                self.assertIsNone(parse_label(invalid), invalid)
        self.assertIsNone(parse_label('{"safety_level":"Level01","safety_level":"Level04"}'))

    def test_pinned_checkpoint_sizes_hashes_and_historical_byte_receipt_match(self):
        receipt = read(ROOT / "docs/research/evidence/issue173/checkpoint-bytes-v1.json")["result"]["models"]
        lock = read(ROOT / "configs/cpu_g2_g3/checkpoint_metadata_lock.json")["minicpm4"]
        for key, count in (("minicpm4", 2), ("qwen3", 4)):
            from safeshift.verification173 import checkpoint_spec
            expected = checkpoint_spec(key)
            actual = receipt[key]
            self.assertEqual(expected["model"], actual["model"])
            shards = [n for n in expected["files"] if n.endswith(".safetensors")]
            self.assertEqual(len(shards), count)
            for n in expected["files"]:
                self.assertEqual(expected["files"][n]["sha256"], actual["files"][n]["sha256"])
                self.assertEqual(expected["files"][n]["size"], actual["files"][n]["size_bytes"])
        self.assertEqual(lock["revision"], "6f69a8235885be89608f3a71ffd40695b379e1e7")

    def test_preparation_source_mismatch_does_not_create_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "unused"
            with self.assertRaisesRegex(ValueError, "FINAL_SOURCE_MISMATCH"):
                entry.prepare("0" * 64, ROOT, "a" * 40, work=out)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
