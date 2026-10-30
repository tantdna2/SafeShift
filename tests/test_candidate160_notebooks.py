"""All cells/payload/pins and real no-grant CPU execution of both notebooks."""
import ast
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zlib

from safeshift.candidates.source import ROOT
from safeshift.candidates.train_contract import BASE, KEYS, MANIFEST, config, configuration_hashes, sources, source_hash
from safeshift.pilot.artifacts import read, verify_archive
from safeshift.pilot.contract import source_digest
from scripts.build_candidate160_notebooks import notebook


class Candidate160NotebookTests(unittest.TestCase):
    def test_all_cells_embedded_sources_sha_pins_and_deterministic_builder(self):
        payloads = []
        for key in KEYS:
            path = ROOT/f"notebooks/SafeShift_CANDIDATE160_{key}.ipynb"
            nb = read(path)
            meta = nb["metadata"]["safeshift"]
            self.assertEqual(meta["base"], BASE)
            self.assertEqual(meta["manifest_sha256"], MANIFEST)
            self.assertEqual(meta["source_sha256"], source_hash())
            self.assertEqual(meta["status"], "AWAITING_INDEPENDENT_REVIEW")
            self.assertEqual(meta["max_images"], 160)
            self.assertEqual(meta["config"], config(key))
            self.assertEqual(meta["configuration_hashes"], configuration_hashes(key))
            self.assertNotIn("transport", meta["config"])
            effective = json.dumps(meta["config"]["effective_candidate"])
            self.assertNotIn("num_crops", effective)
            self.assertNotIn("passive_outer_forward_four_logits_single_branch_v1", effective)
            expected = json.dumps(notebook(key, meta["runtime_ref"]), indent=1, ensure_ascii=False)+"\n"
            self.assertEqual(path.read_bytes(), expected.encode())
            code = ""
            for cell in nb["cells"]:
                if cell["cell_type"] != "code": continue
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])
                text = "".join(cell["source"])
                compile(text, path.name+":"+cell["id"], "exec")
                code += text
            tree = ast.parse(code)
            encodings = [node.args[0].value for node in ast.walk(tree) if isinstance(node, ast.Call)
                         and isinstance(node.func, ast.Attribute) and node.func.attr == "b64decode"]
            self.assertEqual(len(encodings), 1)
            payload = json.loads(zlib.decompress(base64.b64decode(encodings[0])))
            self.assertEqual(set(payload), set(sources()))
            for name, text in payload.items():
                self.assertEqual(text.encode(), (ROOT/name).read_bytes(), name)
                if name.endswith(".py"): compile(text, name, "exec")
                if name.endswith(".json"): json.loads(text)
            payloads.append(payload)
            self.assertIn(f"launch({key!r}, expected_source_sha256, root, {meta['runtime_ref']!r}, owner_start=True)", code)
            self.assertIn("launch_owner as launch", code)
            instructions = "".join(nb["cells"][0]["source"])
            self.assertIn("Save & Run All", instructions)
            self.assertIn("không tự đặt ngưỡng", instructions)
            self.assertNotIn("from safeshift.pilot.bootstrap import launch", code)
            self.assertIn("exist_ok=False", code)
        self.assertEqual(payloads[0], payloads[1])
        self.assertEqual(source_digest(ROOT), "1d76c3a4e5cf9c5fe32d6fd94b846a2879eca268a6023ce34203794dc801d884")

    def test_execute_every_cell_cpu_without_grant_produces_verified_blocked_archive(self):
        for key in KEYS:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                nb = read(ROOT/f"notebooks/SafeShift_CANDIDATE160_{key}.ipynb")
                code = "\n".join("".join(cell["source"]) for cell in nb["cells"] if cell["cell_type"] == "code")
                script = root/"execute_cells.py"
                # No real hardware command in a CPU notebook rehearsal, even if
                # WSL happens to expose the host nvidia-smi executable.
                guarded = ('from unittest.mock import patch\n'
                           'with patch("subprocess.check_output", side_effect=AssertionError("GPU_OBSERVATION_FORBIDDEN_IN_CPU_TEST")):\n'
                           + textwrap.indent(code, '    '))
                script.write_text(guarded, encoding="utf-8")
                process = subprocess.run([sys.executable, "-I", "-B", str(script)], cwd=root,
                    env={**os.environ, "CUDA_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
                    text=True, capture_output=True, timeout=60)
                self.assertEqual(process.returncode, 0, process.stderr)
                archives = list((root/"data/processed/candidate160").glob("*.zip"))
                self.assertEqual(len(archives), 1)
                verify_archive(archives[0])
                status = next((root/"data/processed/candidate160").glob("*/supervisor_status.json"))
                record = read(status)
                self.assertEqual(record["status"], "BLOCKED")
                self.assertFalse(record["attempt_consumed"])
                self.assertEqual(record["accounting"], "NOT_READ_NO_DATA_AUTHORITY")
                self.assertFalse((status.parent/"worker_cuda.json").exists())
                # Same extraction cannot be overwritten, even before another launch.
                again = subprocess.run([sys.executable, "-I", "-B", str(script)], cwd=root,
                                       text=True, capture_output=True, timeout=60)
                self.assertNotEqual(again.returncode, 0)

    def test_wrong_runtime_ref_and_uncommitted_source_are_rejected(self):
        for key in KEYS:
            with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                notebook(key, BASE)

    def test_preflight_builder_cells_and_repeatable_blocked_execution_without_slots(self):
        for key in KEYS:
            nb = read(ROOT/f"notebooks/SafeShift_CANDIDATE160_PREFLIGHT_{key}.ipynb")
            meta = nb["metadata"]["safeshift"]
            self.assertEqual(meta["mode"], "CANDIDATE160_NO_ATTEMPT_PREFLIGHT")
            self.assertEqual(nb, notebook(key, meta["runtime_ref"], preflight=True))
            code = "\n".join("".join(cell["source"]) for cell in nb["cells"] if cell["cell_type"] == "code")
            compile(code, "preflight", "exec")
            self.assertIn("launch_preflight as launch", code)
            self.assertNotIn("launch_owner as launch", code)
            self.assertNotIn("owner_start=True", code)
            with self.subTest(key=key), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                script = root/"preflight.py"
                guarded = ('from unittest.mock import patch\n'
                           'with patch("subprocess.check_output", side_effect=AssertionError("GPU_OBSERVATION_FORBIDDEN_IN_CPU_TEST")):\n'
                           + textwrap.indent(code, '    '))
                script.write_text(guarded, encoding="utf-8")
                for _ in range(2):
                    process = subprocess.run([sys.executable, "-I", "-B", str(script)], cwd=root,
                        env={**os.environ, "CUDA_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1"},
                        text=True, capture_output=True, timeout=60)
                    self.assertEqual(process.returncode, 0, process.stderr)
                reports = list((root/"data/processed/candidate160_preflight").glob("*/preflight.json"))
                self.assertEqual(len(reports), 2)
                for path in reports:
                    report = read(path)
                    self.assertEqual(report["status"], "BLOCKED")
                    self.assertIs(report["attempt_consumed"], False)
                    self.assertIs(report["owner_slot_created"], False)
                    self.assertEqual(report["native_calls"], 0)
                    verify_archive(Path(str(path.parent)+".zip"))
                self.assertFalse(list(root.glob("**/owner_slot*")))
                self.assertFalse(list(root.glob("**/consumption.json")))


if __name__ == "__main__":
    unittest.main()
