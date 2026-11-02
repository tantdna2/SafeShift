"""Final source preparation notebooks, no Inputs, packages, GPU or inference."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from safeshift.candidates.fulltrain import MODELS
from safeshift.candidates.source import ROOT
from safeshift.pilot.artifacts import read, verify_archive
from scripts.build_candidate160_notebooks import fulltrain_notebook


class FulltrainNotebookTests(unittest.TestCase):
    def test_deterministic_builder_empty_outputs_compile_all_models(self):
        for key in MODELS:
            path = ROOT / f"notebooks/SafeShift_FULLTRAIN_PREP_{key}.ipynb"
            nb = read(path)
            expected = fulltrain_notebook(key, nb["metadata"]["safeshift"]["runtime_ref"])
            self.assertEqual(path.read_bytes(), (json.dumps(expected, indent=1, ensure_ascii=False)+"\n").encode())
            for cell in nb["cells"]:
                if cell["cell_type"] == "code":
                    self.assertEqual(cell["outputs"], [])
                    self.assertIsNone(cell["execution_count"])
                    compile("".join(cell["source"]), path.name, "exec")
            self.assertEqual(nb["metadata"]["safeshift"]["status"], "BLOCKED")

    def test_cells_execute_on_cpu_in_empty_directory_without_site_packages(self):
        for key in MODELS:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                nb = read(ROOT / f"notebooks/SafeShift_FULLTRAIN_PREP_{key}.ipynb")
                script = root / "notebook.py"
                code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
                script.write_text(code, encoding="utf-8")
                result = subprocess.run([sys.executable, "-B", "-S", str(script)], cwd=root,
                    capture_output=True, text=True, timeout=60, env={**os.environ, "PYTHONPATH": ""})
                self.assertEqual(result.returncode, 0, result.stderr)
                archives = list((root / "data/processed/fulltrain_prep").glob("*.zip"))
                self.assertEqual(len(archives), 1)
                self.assertEqual(set(verify_archive(archives[0])), {"release.json"})
                report = read(archives[0].with_suffix("") / "release.json")
                self.assertEqual(report["status"], "BLOCKED")
                self.assertFalse(report["attempt_consumed"])
                self.assertEqual(report["production_calls"], 0)
                self.assertEqual(report["levels"]["WEIGHTS_LOADED"], "NOT_RUN")

    def test_cli_prepares_same_3763_plan_without_predictions_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "prep"
            command = [sys.executable, "-B", "-m", "scripts.prepare_fulltrain", "--output", str(target),
                       "--max-calls", "160", "--max-seconds", "600"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            for key in MODELS:
                p = read(target / (key + "-plan.json"))
                self.assertEqual(len(p["samples"]), 3763)
                self.assertEqual(p["counts"], {"NOT_ATTEMPTED": 3763})
            again = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(again.returncode, 0)


if __name__ == "__main__":
    unittest.main()
