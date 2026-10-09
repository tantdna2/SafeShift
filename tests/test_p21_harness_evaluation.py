"""P2.1 integration uses generated pixels and synthetic native envelopes only."""

from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from safeshift.data.p2_execution import json_bytes, sha
from safeshift.protocol import p2_evaluation as ev
from safeshift.protocol.classification_policy import MODELS, ROOT
from safeshift.protocol.p21_schema import PARSER_VERSION
from safeshift.runners import p2_harness as h
from safeshift.runners.contracts import GenerationFailure
from tests.test_d9r23_classification_contract import native


class P21HarnessEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.artifacts = Path(self.tmp.name)
        self.sequence = 0

    def execute(self, model="internvl3", text='```json\n{"safety_level":"Level03"}\n```',
                *, version="P2.1", failure=None):
        self.sequence += 1
        run_id = f"synthetic-p21-{self.sequence}"
        raw = native(model, text)
        if model == "internvl3":
            obj = json.loads(raw)
            obj.update(run_id=run_id, call_id=h.call_identity("synthetic-a"))
            raw = json_bytes(obj)
        backend = h.ScriptedBackend([failure if failure else raw])
        root = h.rehearse(model=model, run_id=run_id, sample_ids=["synthetic-a"],
                          backend=backend, repo=ROOT, artifact_repo=self.artifacts,
                          protocol_version=version)
        return root, raw, backend

    def test_full_p21_raw_metadata_export_parity_for_every_model(self):
        for model in MODELS:
            with self.subTest(model=model):
                root, raw, backend = self.execute(model)
                directory = root / "calls" / sha(b"synthetic-a")
                self.assertEqual((directory / "response.raw").read_bytes(), raw)
                meta = json.loads((directory / "metadata.json").read_bytes())
                self.assertEqual(meta["raw_output"], meta["raw_response"])
                self.assertEqual(meta["raw_output"]["sha256"], sha(raw))
                self.assertEqual(meta["parser_version"], PARSER_VERSION)
                self.assertTrue(meta["format_wrapper_detected"])
                self.assertEqual(meta["parse_status"], "SUCCESS")
                self.assertEqual(backend.calls, 1)
                export = ev.export_predictions(root, protocol_version="P2.1")
                self.assertEqual(export["rows"][0]["safety_level"], "Level03")
                self.assertEqual(export["protocol_identity"]["protocol_id"], "P2.1")

    def test_p2_and_p21_exports_require_explicit_version(self):
        root, _, _ = self.execute()
        with self.assertRaises(ValueError):
            ev.export_predictions(root)
        root2, _, _ = self.execute(model="moondream", version="P2")
        with self.assertRaises(ValueError):
            ev.export_predictions(root2, protocol_version="P2.1")
        table = ev.export_predictions(root2)
        self.assertEqual(table["rows"][0]["parse_status"], "INVALID")
        self.assertNotIn("format_wrapper_detected", table["rows"][0])

    def test_formal_p21_alignment_rejects_mixed_historical_p2(self):
        exports = [ev.export_predictions(self.execute(model)[0], protocol_version="P2.1")
                   for model in MODELS]
        aligned = ev.align_four_models(exports, protocol_version="P2.1")
        self.assertEqual(aligned[0]["predictions"], {model: "Level03" for model in MODELS})
        with self.assertRaises(ValueError):
            ev.align_four_models(exports)
        # Separate storage so the historical run never hides an overlapping attempt.
        with tempfile.TemporaryDirectory() as historical:
            prior_storage = self.artifacts
            self.artifacts = Path(historical)
            p2 = ev.export_predictions(self.execute("qwen2_5", version="P2")[0])
            self.artifacts = prior_storage
        mixed = [p2 if item["model_key"] == "qwen2_5" else item for item in exports]
        with self.assertRaisesRegex(ValueError, "PROTOCOL_IDENTITY_MISMATCH"):
            ev.align_four_models(mixed, protocol_version="P2.1")

    def test_wrong_wrapper_metadata_is_integrity_failure(self):
        root, _, _ = self.execute()
        table = ev.export_predictions(root, protocol_version="P2.1")
        row = deepcopy(table["rows"][0])
        row["format_wrapper_detected"] = 1
        with self.assertRaises(ValueError):
            ev.prediction(row, protocol_version="P2.1")
        identity = deepcopy(table["protocol_identity"])
        identity["parser_version"] = "d9r23-native-strict-classification-v1"
        with self.assertRaises(ValueError):
            ev._validate_protocol_identity(identity, "P2.1")

    def test_generation_failure_keeps_partial_raw_and_stops_without_retry(self):
        partial = b'```json\n{"safety_level":"Level03"}'
        root, _, backend = self.execute(failure=GenerationFailure(partial_raw=partial))
        status = json.loads((root / "run_status.json").read_bytes())
        self.assertEqual(status["status"], "FAILED")
        self.assertEqual(status["samples"], {"synthetic-a": "FAILED"})
        self.assertEqual(backend.calls, 1)
        raw_path = root / "calls" / sha(b"synthetic-a") / "response.raw"
        self.assertEqual(raw_path.read_bytes(), partial)
        with self.assertRaises(ValueError):
            ev.export_predictions(root, protocol_version="P2.1")

    def test_p21_parser_never_runs_before_raw_hash_verification(self):
        root, _, _ = self.execute()
        directory = root / "calls" / sha(b"synthetic-a")
        meta = json.loads((directory / "metadata.json").read_bytes())
        (directory / "response.raw").write_bytes(b"tampered")
        with patch("safeshift.runners.p21_classification.P21NativeAdapter") as parser:
            with self.assertRaisesRegex(ValueError, "RAW_PERSISTENCE_INTEGRITY_FAILURE"):
                h.parse_stored(directory, meta["raw_response"], "internvl3", h._model("internvl3", ROOT),
                               meta["run_id"], meta["call_id"], protocol_version="P2.1")
            parser.assert_not_called()

    def test_p21_invalid_is_unclassified_and_run_is_completed(self):
        root, _, backend = self.execute(text='Prose {"safety_level":"Level03"}')
        table = ev.export_predictions(root, protocol_version="P2.1")
        self.assertEqual(table["status"], "COMPLETED")
        self.assertEqual(table["rows"][0]["parse_status"], "INVALID")
        self.assertIsNone(table["rows"][0]["safety_level"])
        self.assertEqual(backend.calls, 1)


if __name__ == "__main__":
    unittest.main()
