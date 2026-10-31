"""Synthetic safety/failure tests for the one-call engineering mode, never GPU proof."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from safeshift.candidates import train_contract as c, train_smoke as smoke, train_run as run
from safeshift.candidates import train_history as history, train_runtime as rt
from safeshift.candidates.source import ROOT
from safeshift.pilot.artifacts import read, write, export, verify_archive
from test_candidate160 import fixture, Scripted


class SmokeTests(unittest.TestCase):
    def test_exact_one_call_both_models_and_no_scientific_metrics(self):
        for key in c.KEYS:
            for fault in (None, RuntimeError("SYNTHETIC GPU OOM")):
                with self.subTest(key=key, fault=bool(fault)), tempfile.TemporaryDirectory() as d:
                    root = Path(d)
                    plan, rows = fixture(root)
                    g = smoke.execution(key, c.source_hash(), "a"*40)
                    c.authorize(g, key, g["source_sha256"], g["runtime_ref"], None)
                    native = Scripted(key=key, fault=fault)
                    output = root / "smoke"
                    output.mkdir()
                    results, reason = run.run_calls(output, plan, rows, lambda: native, g, resources=lambda: {})
                    self.assertEqual(native.calls, 1)
                    self.assertEqual(sum(v["native_calls"] for v in results.values()), 1)
                    self.assertTrue(all(v["attempts"] == 0 for v in list(results.values())[1:]))
                    self.assertEqual(bool(reason), bool(fault))
                    summary = read(output / "summary.json")
                    self.assertIsNone(summary["metrics"])
                    self.assertEqual(summary["scientific_selection"], "EXCLUDED")
                    self.assertFalse(summary["pooling_allowed"])
                    self.assertEqual(read(output / "model_load_attempt.json")["load_attempts"], 1)
                    archive = root / "smoke.zip"
                    export(output, archive)
                    verify_archive(archive)
                    self.assertFalse((root / "attempts").exists())

    def test_caps_and_configuration_cannot_be_relaxed(self):
        original = smoke.execution("internvl35", "c"*64, "a"*40)
        for name, value in (("max_native_calls", 160), ("selected_ordinals", [1]),
                            ("max_seconds", 43200), ("split", "TEST"), ("purpose", "PRODUCTION"),
                            ("schema", history.SCHEMA), ("model", {}), ("policy", {})):
            with self.subTest(name=name):
                altered = copy.deepcopy(original)
                altered[name] = value
                with self.assertRaises((ValueError, KeyError)):
                    c.authorize(altered, "internvl35", "c"*64, "a"*40, None)

    def test_load_failure_stops_before_native_call_and_cannot_be_smoke_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan, rows = fixture(root)
            output = root / "smoke"
            output.mkdir()
            g = smoke.execution("minicpm4", "c"*64, "a"*40)
            def fail():
                raise RuntimeError("SYNTHETIC LOAD FAILURE")
            results, reason = run.run_calls(output, plan, rows, fail, g, resources=lambda: {})
            self.assertIsNotNone(reason)
            self.assertEqual(sum(v["native_calls"] for v in results.values()), 0)
            archive = root / "smoke.zip"
            export(output, archive)
            with self.assertRaises((ValueError, FileNotFoundError)):
                smoke.receipt(output, archive, g)

    def test_smoke_supervisor_no_production_execution_or_reservation_on_input_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            inputs = root / "inputs"
            inputs.mkdir()
            work = root / "production"
            with patch.object(history, "collect", side_effect=AssertionError("PRODUCTION_HISTORY_FORBIDDEN")):
                out = rt.launch_owner("internvl35", c.source_hash(), ROOT, "a"*40,
                    owner_start=True, action="technical_smoke", work=work, inputs=inputs)
            self.assertEqual(out.parent, root / "production_smoke")
            self.assertTrue((out / "technical_execution.json").is_file())
            self.assertFalse((out / "owner_execution.json").exists())
            self.assertFalse(list(work.rglob("*.json")))
            self.assertEqual(read(Path(str(out) + ".smoke-result.json"))["status"], "BLOCKED_NOT_VERIFIED")
            verify_archive(Path(str(out) + ".zip"))


if __name__ == "__main__":
    unittest.main()
