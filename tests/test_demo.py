"""Run the actual CLI on CPU with only standard-library imports available."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.demo_cpu import build_report, DISCLAIMER

ROOT = Path(__file__).resolve().parents[1]


class DemoTests(unittest.TestCase):
    def test_report_is_explicitly_synthetic_and_deterministic(self):
        first = build_report()
        self.assertEqual(first, build_report())
        self.assertEqual(first["notice"], "SYNTHETIC DEMO — NOT RESEARCH RESULT")
        self.assertFalse(first["model_execution"])
        self.assertEqual(first["metrics"]["n_images"], 6)
        self.assertEqual(first["metrics"]["invalid_n"], 1)
        self.assertEqual(first["metrics"]["per_class"]["Level01"]["recall"], 0.5)

    def test_module_cli_without_site_packages(self):
        result = subprocess.run([sys.executable, "-S", "-B", "-m", "scripts.demo_cpu"],
                                cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), build_report())

    def test_demo_from_empty_directory_without_external_data_or_writes(self):
        code = ("import sys,runpy; sys.path.insert(0,sys.argv[1]); "
                "runpy.run_module('scripts.demo_cpu',run_name='__main__')")
        with tempfile.TemporaryDirectory() as empty:
            result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code, str(ROOT)],
                                    cwd=empty, capture_output=True, text=True, check=False)
            self.assertEqual(list(Path(empty).iterdir()), [])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["notice"], DISCLAIMER)
