"""Production adapters over fake native envelopes; no model/image execution."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from safeshift.protocol.execution_policy import load_policy, validate_context, require_grounding_contract
from safeshift.runners.contracts import Task, ParseStatus, execute_call, Request, Roles, Participation
from safeshift.runners.production_classification import classification_adapter
from safeshift.runners.paligemma import PendingPaliGemmaAdapter
from safeshift.runners.moondream2 import serialize_native
from tests.test_classification_qualification import envelope, context, FakeRunner


class AdapterTests(unittest.TestCase):
    def test_four_participants_exact_levels(self):
        for model in ("qwen3", "qwen2_5", "internvl3", "moondream"):
            for level in ("Level01", "Level02", "Level03", "Level04"):
                with self.subTest(model=model, level=level):
                    result = classification_adapter(model).adapt(envelope(model, json.dumps({"safety_level": level})), Task.CLASSIFICATION)
                    result.validate(Task.CLASSIFICATION)
                    self.assertEqual(result.value.safety_level, level)

    def test_strict_no_repairs_all_four(self):
        texts = ('```json\n{"safety_level":"Level01"}\n```', '{"safety_level":"level01"}',
                 '{"safety_level":"Level01","extra":0}', '{"safety_level":"Level01","safety_level":"Level02"}',
                 'Level01', 'RED TRIANGLE', '{"safety_level":"LEVEL01"}', '{"safety_level":"Level01"} trailing')
        for model in ("qwen3", "qwen2_5", "internvl3", "moondream"):
            for text in texts:
                with self.subTest(model=model, text=text):
                    result = classification_adapter(model).adapt(envelope(model, text), Task.CLASSIFICATION)
                    self.assertEqual(result.parse_status, ParseStatus.INVALID)
                    self.assertIsNone(result.value)

    def test_internvl_exact_identity_tokens_boundary_and_calls(self):
        source = json.loads(envelope("internvl3", '{"safety_level":"Level01"}'))
        mutations = [("revision", "main"), ("model_id", "other"), ("extra", 1),
                     ("continuation_ids", [True]), ("run_id", ""), ("decoded_text", None)]
        for field, value in mutations:
            obj = deepcopy(source)
            obj[field] = value
            self.assertEqual(classification_adapter("internvl3").adapt(json.dumps(obj).encode(), Task.CLASSIFICATION).parse_status, ParseStatus.INVALID)
        adapter = classification_adapter("internvl3", run_id="other", call_id="cq_01")
        self.assertEqual(adapter.adapt(json.dumps(source).encode(), Task.CLASSIFICATION).parse_status, ParseStatus.INVALID)

    def test_moondream_exact_lossless_answer_string_only(self):
        for native in ({"answer": None}, {"answer": 1}, {"answer": "{}", "reasoning": "text"}, {"objects": []}):
            self.assertEqual(classification_adapter("moondream").adapt(serialize_native(native), Task.CLASSIFICATION).parse_status, ParseStatus.INVALID)
        good = json.loads(serialize_native({"answer": '{"safety_level":"Level01"}'}))
        good["native"][1].append(good["native"][1][0])
        self.assertEqual(classification_adapter("moondream").adapt(json.dumps(good).encode(), Task.CLASSIFICATION).parse_status, ParseStatus.INVALID)

    def test_qwen_envelope_validation_not_rewritten(self):
        for model in ("qwen3", "qwen2_5"):
            for field, value in (("model_revision", "main"), ("input_token_count", True), ("extra", 0)):
                obj = json.loads(envelope(model, '{"safety_level":"Level01"}'))
                obj[field] = value
                with self.assertRaises((ValueError, TypeError)):
                    classification_adapter(model).adapt(json.dumps(obj).encode(), Task.CLASSIFICATION)

    def test_pali_unmodified_nonparticipant(self):
        with self.assertRaisesRegex(ValueError, "NOT_PARTICIPATING"):
            classification_adapter("paligemma")
        self.assertEqual(PendingPaliGemmaAdapter().adapt(b"anything", Task.CLASSIFICATION).parse_status, ParseStatus.INVALID)

    def test_no_grounding_promotion(self):
        for model in ("internvl3", "moondream"):
            result = classification_adapter(model).adapt(b"not parsed", Task.GROUNDING)
            result.validate(Task.GROUNDING)
            self.assertEqual(result.parse_status, ParseStatus.UNSUPPORTED)

    def test_raw_persist_before_production_parser_storage_failure_blocks(self):
        from safeshift.runners.contracts import RawReference
        events = []
        raw = envelope("moondream", '{"safety_level":"Level01"}')
        class Store:
            def preserve(self, data, provenance):
                self.raw = data
                events.append("persist")
                return RawReference("data/processed/fake/raw", "a" * 64, len(data))
        class Adapter:
            version = parser_version = "fake-observer"
            def adapt(self, data, task):
                self_test.assertEqual(events, ["persist"])
                self_test.assertEqual(data, store.raw)
                events.append("parse")
                return classification_adapter("moondream").adapt(data, task)
        self_test, store = self, Store()
        runner = FakeRunner()
        request = Request(Task.CLASSIFICATION, "s", "i", b"fake", "p", "fake prompt")
        with patch.object(runner, "generate_raw", return_value=raw):
            result = execute_call(runner, Adapter(), store, request, context())
        self.assertEqual(result.parse_status, ParseStatus.SUCCESS)
        self.assertEqual(events, ["persist", "parse"])
        events.clear()
        with patch.object(store, "preserve", side_effect=OSError), patch.object(runner, "generate_raw", return_value=raw):
            result = execute_call(runner, Adapter(), store, request, context())
        self.assertEqual(events, [])
        self.assertEqual(result.error.code.value, "RAW_PRESERVATION_FAILURE")


class PolicyTests(unittest.TestCase):
    def test_exact_merged_conditions_without_semantic_selection(self):
        policy = load_policy()
        self.assertFalse(policy["semantic_scores_used_for_selection"])
        for model, row in policy["classification"].items():
            validate_context(model, context(model))
            self.assertEqual(row["max_output_tokens"], 32)
            self.assertEqual(row["precision_or_quantization"], "FP16/NONE")
            self.assertEqual(row["adapter_version"], classification_adapter(model).version)
            with self.assertRaises(ValueError):
                validate_context(model, replace(context(model), seed=42))
            with self.assertRaises(ValueError):
                validate_context(model, replace(context(model), quantization="INT8"))

    def test_no_inspecsafe_context(self):
        for model in load_policy()["classification"]:
            with self.assertRaisesRegex(ValueError, "NO_INSPECSAFE"):
                validate_context(model, replace(context(model), source_kind="INSPECSAFE"))

    def test_grounding_blockers_no_native_dispatch(self):
        with self.assertRaisesRegex(ValueError, "MOONDREAM_CALL2_ORCHESTRATION_BLOCKER"):
            require_grounding_contract("moondream")
        for model in ("qwen3", "moondream", "paligemma"):
            with self.assertRaisesRegex(ValueError, "EXPLORATORY_BENCHMARK_EXECUTION_CONTRACT_BLOCKER"):
                require_grounding_contract(model, exploratory=True)
        for model in ("qwen2_5", "internvl3"):
            with self.assertRaisesRegex(ValueError, "EXCLUDED"):
                require_grounding_contract(model, exploratory=True)


if __name__ == "__main__":
    unittest.main()
