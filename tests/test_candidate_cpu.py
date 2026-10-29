"""CPU qualification guard/contract tests, public synthetic inputs only."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from safeshift.pilot.artifacts import sha, write
from safeshift.pilot.contract import GENERATION, MODELS
from scripts import rehearse_candidate_cpu as q
from scripts.pilot_source_audit import MODELS as SOURCE_MODELS


class CandidateCPUTests(unittest.TestCase):
    def test_exact_identity_does_not_enroll_production_candidates(self):
        self.assertEqual(SOURCE_MODELS["internvl35"], ("OpenGVLab/InternVL3_5-4B-HF", "6bd4487402110ef9889ba50eb7aefeb302526fed"))
        self.assertEqual(SOURCE_MODELS["minicpm4"], ("openbmb/MiniCPM-V-4", "6f69a8235885be89608f3a71ffd40695b379e1e7"))
        self.assertEqual(set(MODELS), {"gemma", "phi", "smolvlm2"})

    def test_snapshot_missing_corrupt_extra_and_weight_files_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            snapshot = root / "public"
            snapshot.mkdir()
            write(snapshot / "config.json", {"synthetic": True})
            lock = root / "lock.json"
            write(lock, {"fixture": {"files": {"config.json": sha(snapshot / "config.json")}}})
            with patch.object(q, "LOCK", lock):
                self.assertIn("files", q.verify_snapshot(snapshot, "fixture"))
                (snapshot / "config.json").write_text("changed")
                with self.assertRaisesRegex(ValueError, "CHECKSUM"):
                    q.verify_snapshot(snapshot, "fixture")
                (snapshot / "config.json").unlink()
                with self.assertRaisesRegex(ValueError, "ALLOWLIST"):
                    q.verify_snapshot(snapshot, "fixture")
                (snapshot / "model.safetensors").write_bytes(b"NOT_WEIGHTS")
                with self.assertRaisesRegex(ValueError, "ALLOWLIST"):
                    q.verify_snapshot(snapshot, "fixture")

    def test_scripted_actual_raw_writer_failure_does_not_parse(self):
        # Uses the existing engine's test rather than a second execution engine.
        from test_pilot import ArtifactAndEngineTests
        test = ArtifactAndEngineTests("test_raw_writer_error_keeps_tail_not_attempted")
        result = unittest.TestResult()
        test.run(result)
        self.assertTrue(result.wasSuccessful(), result.errors + result.failures)

    def test_generation_constants_not_mutated_by_rehearsal(self):
        expected = {"do_sample": False, "num_beams": 1, "max_new_tokens": 64,
                    "use_cache": True, "return_dict_in_generate": True,
                    "output_scores": False, "output_logits": False}
        self.assertEqual(GENERATION, expected)

    def test_source_script_has_no_model_execution_or_snapshot_download(self):
        import ast
        tree = ast.parse(Path(q.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "attr", getattr(node.func, "id", ""))
                self.assertNotIn(name, ("snapshot_download", "hf_hub_download", "forward", "generate"))


if __name__ == "__main__":
    unittest.main()
