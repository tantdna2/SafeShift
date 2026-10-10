"""CPU-only tests for label-free LS1 calibration diagnostics and safety reporting.

All logits are synthetic. They characterise the unchanged ls1-v1 formula; they are
not observed model values, InspecSafe results or evidence of model accuracy.
"""

import json
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

from safeshift.ls1 import core, diagnostics, evaluate, experiment
from tests.test_ls1 import FakeScorer, fake_t1

ROOT = Path(__file__).resolve().parents[1]
NAMES = [name for name, _ in core.REFERENCE_SPEC]
# Synthetic "blank image looks safe" references: Level03/Level04 likely, hazards very unlikely.
SAFE_LOOKING_REFS = {"gray": [-12.0, -9.0, 0.0, -2.4], "black": [-11.0, -8.5, 0.0, -2.6],
                     "white": [-13.0, -9.5, 0.0, -2.2]}


class CharacterisationTests(unittest.TestCase):
    def test_bias_matches_official_calibrate_exactly(self):
        rng = random.Random(20261011)
        for _ in range(200):
            refs = {name: [rng.uniform(-30, 30) for _ in range(4)] for name in NAMES}
            sample = [rng.uniform(-30, 30) for _ in range(4)]
            self.assertEqual(diagnostics.reference_bias(refs)["bias"],
                             core.calibrate(sample, refs)["reference_log_bias"])

    def test_level04_margin_identity_holds_for_official_calibrate(self):
        # explain_decision raises if calibrated Level04 != (all margins exceed reference margins).
        rng = random.Random(7)
        seen = set()
        for _ in range(3000):
            refs = {name: [rng.choice((-12, -6, -2, 0, 3)) + rng.random() for _ in range(4)] for name in NAMES}
            sample = [rng.choice((-12, -6, -2, 0, 3)) + rng.random() for _ in range(4)]
            seen.add(diagnostics.explain_decision(sample, refs)["level04_reachable"])
        self.assertEqual(seen, {True, False})

    def test_safe_looking_references_turn_hazard_free_scene_into_level01(self):
        # Sample is slightly less "blank-safe" than the references, as any real scene is.
        sample = [-9.0, -7.0, 0.0, -2.6]
        result = core.calibrate(sample, SAFE_LOOKING_REFS)
        self.assertEqual(result["uncalibrated"]["prediction"], "Level03")
        self.assertEqual(result["calibrated"]["prediction"], "Level01")
        explanation = diagnostics.explain_decision(sample, SAFE_LOOKING_REFS)
        self.assertFalse(explanation["level04_reachable"])
        self.assertEqual(explanation["binding_competitor"], "Level01")
        self.assertEqual(explanation["severity_change"], 2)
        # Level04 needs log-odds over Level01 above the blank references' ~9.6.
        self.assertGreater(explanation["level04_required_log_odds"]["Level01"], 9)

    def test_level04_only_when_more_hazard_free_than_blank_references(self):
        bias = diagnostics.reference_bias(SAFE_LOOKING_REFS)["bias"]
        required = [bias[3] - bias[i] for i in range(3)]
        just_above = [0.0, 0.0, 0.0, 0.0]
        just_above[3] = max(required) + 1e-6
        just_below = [0.0, 0.0, 0.0, max(required) - 1e-6]
        self.assertEqual(core.calibrate(just_above, SAFE_LOOKING_REFS)["calibrated"]["prediction"], "Level04")
        self.assertNotEqual(core.calibrate(just_below, SAFE_LOOKING_REFS)["calibrated"]["prediction"], "Level04")

    def test_sample_equal_to_reference_mean_ties_and_tie_policy_picks_level01(self):
        bias = diagnostics.reference_bias(SAFE_LOOKING_REFS)["bias"]
        result = core.calibrate(bias, SAFE_LOOKING_REFS)
        probabilities = result["calibrated"]["probabilities"]
        self.assertTrue(all(math.isclose(p, .25, abs_tol=1e-12) for p in probabilities))
        self.assertEqual(result["calibrated"]["prediction"], "Level01")

    def test_uniform_references_change_nothing(self):
        refs = {name: [1.5] * 4 for name in NAMES}
        explanation = diagnostics.explain_decision([0.0, 1.0, 4.0, 0.0], refs)
        self.assertEqual(explanation["uncalibrated"], explanation["calibrated"])
        self.assertEqual(explanation["severity_change"], 0)

    def test_reference_validation(self):
        with self.assertRaises(ValueError):
            diagnostics.reference_bias({"gray": [0] * 4})
        with self.assertRaises(ValueError):
            diagnostics.reference_bias({name: [0, 0, math.nan, 0] for name in NAMES})


class HazardFreeSanityTests(unittest.TestCase):
    def test_reported_technical_pattern_fails(self):
        # Pattern reported for ls1-internvl3-technical-first: 4x Level03 -> 3x Level01, 1x Level04.
        rows = [("a", "Level03", "Level01"), ("b", "Level03", "Level01"),
                ("c", "Level03", "Level01"), ("d", "Level03", "Level04")]
        result = diagnostics.hazard_free_sanity(rows)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["calibrated_level01_or_level02"], ["a", "b", "c"])
        self.assertEqual(result["severity_escalations"], ["a", "b", "c"])

    def test_pass_requires_no_alarm_and_no_escalation(self):
        self.assertEqual(diagnostics.hazard_free_sanity([("a", "Level03", "Level04"),
                                                         ("b", "Level03", "Level03")])["status"], "PASS")
        self.assertEqual(diagnostics.hazard_free_sanity([("a", "Level04", "Level03")])["status"], "FAIL")
        self.assertEqual(diagnostics.hazard_free_sanity([("a", "Level02", "Level02")])["status"], "FAIL")

    def test_rows_validated(self):
        for rows in ([], [("a", "Level03", None)], [("a", "INVALID", "Level04")]):
            with self.assertRaises(ValueError):
                diagnostics.hazard_free_sanity(rows)


class DiagnoseRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        for name in (experiment.METHOD_PATH, "prompts/p2_classification_c1_v1.txt"):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        settings = {"model_key": "internvl3", "run_id": "diag-test", "mode": "technical",
                    "source_commit": "b" * 40, "snapshot": "fake"}
        FakeScorer.calls = 0
        self.root = experiment.run(self.repo, settings, scorer_factory=FakeScorer, tokenizer_check=fake_t1)

    def tearDown(self):
        self.temp.cleanup()

    def test_sealed_technical_run_is_diagnosed_and_fails_sanity(self):
        report = diagnostics.diagnose_run(self.root)
        self.assertEqual(report["audit"]["status"], "PASS")
        self.assertEqual(report["source_kind"], "SYNTHETIC")
        self.assertEqual(len(report["references"]), 1)
        recorded = json.loads((self.root / "results.json").read_text())
        for row, result in zip(report["samples"], recorded):
            self.assertEqual(row["calibrated"], result["modes"]["calibrated"]["prediction"])
        # Fake refs (0,1,8,0) vs samples (0,1,4,0): calibrated three-way tie resolved to Level01.
        self.assertEqual({row["calibrated"] for row in report["samples"]}, {"Level01"})
        self.assertEqual(report["hazard_free_sanity"]["status"], "FAIL")
        self.assertEqual(len(report["hazard_free_sanity"]["calibrated_level01_or_level02"]), 4)
        self.assertEqual(report["performance_claim"], "NONE_DIAGNOSTIC_ONLY")

    def test_tampered_run_is_rejected_before_diagnosis(self):
        target = next((self.root / "references").rglob("gray.raw.json"))
        target.write_bytes(target.read_bytes().replace(b"0", b"1", 1))
        with self.assertRaises(ValueError):
            diagnostics.diagnose_run(self.root)

    def test_cli_output_is_exclusive(self):
        output = self.repo / "diag.json"
        command = [sys.executable, "-m", "safeshift.ls1.diagnostics", "--run", str(self.root), "--output", str(output)]
        subprocess.run(command, cwd=ROOT, check=True, capture_output=True)
        self.assertEqual(json.loads(output.read_text())["hazard_free_sanity"]["status"], "FAIL")
        self.assertNotEqual(subprocess.run(command, cwd=ROOT, capture_output=True).returncode, 0)

    def test_import_does_not_load_ml(self):
        source = ("import sys; import safeshift.ls1.diagnostics; "
                  "assert 'torch' not in sys.modules; assert 'transformers' not in sys.modules")
        subprocess.run([sys.executable, "-c", source], cwd=ROOT, check=True)


class SafetyReportingTests(unittest.TestCase):
    def test_wilson_known_values(self):
        z2 = 1.959963984540054 ** 2  # closed forms at k=0 and k=n
        self.assertAlmostEqual(evaluate.wilson(0, 4)["high"], z2 / (4 + z2), places=12)
        self.assertEqual(evaluate.wilson(0, 4)["low"], 0.0)
        self.assertAlmostEqual(evaluate.wilson(2, 2)["low"], 2 / (2 + z2), places=12)
        self.assertAlmostEqual(evaluate.wilson(5, 10)["low"], 0.2365931, places=6)
        self.assertEqual(evaluate.wilson(2, 2)["high"], 1.0)
        self.assertIsNone(evaluate.wilson(0, 0))
        for bad in ((3, 2), (-1, 2), (1.0, 2), (True, 2)):
            with self.assertRaises(ValueError):
                evaluate.wilson(*bad)

    def test_alarms_misses_and_paired_transitions(self):
        refs = {name: [0.0] * 4 for name in NAMES}
        rows, gt = [], {}
        cases = (("n1", "Level04", [5, 0, 0, 0]), ("n2", "Level04", [0, 0, 0, 5]),
                 ("h1", "Level01", [0, 0, 5, 0]), ("h2", "Level01", [5, 0, 0, 0]), ("x", "Level01", None))
        for sid, truth, logits in cases:
            gt[sid] = truth
            if logits is None:
                rows.append({"sample_id": sid, "status": "INVALID", "modes": None})
                continue
            rows.append({"sample_id": sid, "status": "SUCCESS", "modes": core.calibrate(logits, refs),
                         "score": {"generated_label": core.LEVELS[logits.index(5)]}})
        rows[1]["modes"]["calibrated"]["prediction"] = "Level02"  # synthetic escalation of a true normal
        report = evaluate.report(rows, gt)
        before, after = report["modes"]["uncalibrated"], report["modes"]["calibrated"]
        self.assertEqual(before["safety_counts"]["normal_alarms"]["Level04_to_Level01"], 1)
        self.assertEqual(after["safety_counts"]["normal_alarms"]["Level04_to_Level02"], 1)
        self.assertEqual(before["safety_counts"]["level01_misses"],
                         {"Level01_to_Level02": 0, "Level01_to_Level03": 1, "Level01_to_Level04": 0,
                          "Level01_to_INVALID": 1})
        wilson01 = before["safety_counts"]["per_class_recall_wilson95"]["Level01"]
        self.assertEqual((wilson01["successes"], wilson01["n"]), (1, 3))  # INVALID stays in denominator
        self.assertEqual(report["paired_transitions_uncalibrated_to_calibrated"]["Level04"]["Level02"], 1)
        self.assertEqual(report["true_normal_severity_escalations"], ["n2"])
        # Pre-existing keys are unchanged.
        self.assertEqual(before["confusion_matrix"]["Level01"]["INVALID"], 1)
        self.assertIn("transitions_to_level04", report)


if __name__ == "__main__":
    unittest.main()
