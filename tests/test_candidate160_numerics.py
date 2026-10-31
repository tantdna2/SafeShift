"""Synthetic observation-only hook tests; no model/dataset/real GPU evidence."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from safeshift.candidates.source import ROOT
from safeshift.pilot.artifacts import read


class DiagnosticAdmissionTests(unittest.TestCase):
    def test_source_mismatch_blocks_before_model_or_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "unused"
            child = subprocess.run([sys.executable, "-B", "-m", "scripts.diagnose_candidate160_numerics",
                "--repo", str(ROOT), "--source", "0"*64, "--ref", "a"*40,
                "--worker", "--output", str(output)], cwd=ROOT, text=True, capture_output=True, timeout=60)
            self.assertNotEqual(child.returncode, 0)
            self.assertIn("DIAGNOSTIC_SOURCE_MISMATCH", child.stderr)
            self.assertFalse(output.exists())


@unittest.skipUnless(importlib.util.find_spec("torch"), "isolated torch CPU stack required")
class NumericHookTests(unittest.TestCase):
    def test_nonfinite_summary_and_empty_tensor(self):
        import torch
        from scripts.diagnose_candidate160_numerics import describe
        value = describe(torch.tensor([float("nan"), float("inf"), -float("inf"), 2.0]))
        self.assertEqual((value["nan"], value["positive_inf"], value["negative_inf"]), (1, 1, 1))
        self.assertEqual(value["finite_abs_max"], 2.0)
        self.assertEqual(describe(torch.empty(0))["finite_abs_max"], 0.0)

    def test_native_half_overflow_is_observed_without_changing_weights_or_inputs(self):
        import torch
        from scripts.diagnose_candidate160_numerics import observe_model
        with tempfile.TemporaryDirectory() as d, torch.no_grad():
            output = Path(d)
            model = torch.nn.Sequential(torch.nn.Linear(2, 2, bias=False)).half()
            model[0].weight.fill_(1)
            original = model[0].weight.clone()
            image = torch.full((1, 2), 65504., dtype=torch.float16)
            before = image.clone()
            handles = observe_model(model, output)
            try:
                with self.assertRaisesRegex(FloatingPointError, "NATIVE_NONFINITE_MODULE:0"):
                    model(image)
            finally:
                for handle in handles:
                    handle.remove()
            record = read(output / "first_nonfinite.json")
            self.assertEqual(record["output"]["positive_inf"], 2)
            self.assertEqual(record["inputs"][0]["finite_abs_max"], 65504.)
            self.assertTrue(torch.equal(model[0].weight, original))
            self.assertTrue(torch.equal(image, before))


if __name__ == "__main__":
    unittest.main()
