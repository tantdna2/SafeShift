"""P2.1 format and durable raw regressions: synthetic native envelopes only."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from safeshift.protocol import classification_policy as policy
from safeshift.protocol import p21_schema as p21
from safeshift.protocol.schema import parse_text, strict_json
from safeshift.qualification.classification import CandidateAdapter
from safeshift.runners import production_classification as production
from safeshift.runners.contracts import ParseStatus, RunContext, Task
from safeshift.runners.p21_classification import P21NativeAdapter
from safeshift.runners.storage import FileRawStore
from tests.test_classification_qualification import envelope

ROOT = Path(__file__).resolve().parents[1]
BASE = "f0b5ea775b3c5bbe5e8618ba1372e59b8b8e150f"
PLAIN = '{"safety_level":"Level03"}'
FENCED = "```json\n" + PLAIN + "\n```"


def native(model, text):
    raw = envelope(model, text)
    if model == "qwen3":
        obj = strict_json(raw)
        obj["runtime"]["software_versions"] = policy.load_policy()["classification"][model]["software_versions"]
        raw = json.dumps(obj).encode("utf-8")
    return raw


class P21FormatTests(unittest.TestCase):
    def assert_invalid(self, texts):
        for text in texts:
            with self.subTest(text=text):
                result = p21.parse_classification(text)
                self.assertEqual(result.status, "INVALID")
                self.assertIsNone(result.value)

    def test_plain_json_all_four_canonical_values(self):
        for level in ("Level01", "Level02", "Level03", "Level04"):
            result = p21.parse_classification(' \t\r\n{"safety_level":"' + level + '"}\n')
            self.assertEqual((result.status, result.value.safety_level), ("SUCCESS", level))
            self.assertIs(result.format_wrapper_detected, False)

    def test_exact_single_fence_json_or_unlabelled_and_crlf(self):
        for opener in ("```", "```json"):
            for newline in ("\n", "\r\n"):
                result = p21.parse_classification(" \n" + opener + newline + PLAIN + newline + "```\t\n")
                self.assertEqual((result.status, result.value.safety_level), ("SUCCESS", "Level03"))
                self.assertIs(result.format_wrapper_detected, True)

    def test_no_canonical_value_is_invalid(self):
        self.assert_invalid(("", "Level03", "Level three", "no abnormalities observed",
                             "{}", '"Level03"', "null", "[]", "```json\n\n```"))

    def test_explanation_before_or_after_is_invalid(self):
        self.assert_invalid(("Answer: " + PLAIN, PLAIN + " trailing", "Explanation\n" + FENCED,
                             FENCED + "\nExplanation", "```json\n" + PLAIN + "\n```\nMore"))

    def test_multiple_fences_or_json_objects_are_invalid(self):
        self.assert_invalid((FENCED + "\n" + FENCED,
                             "```json\n" + PLAIN + "\n```\n```\n{}\n```",
                             PLAIN + "\n" + PLAIN,
                             "```json\n" + PLAIN + "\n" + PLAIN + "\n```"))

    def test_wrong_fence_language_missing_newlines_or_markers_are_invalid(self):
        self.assert_invalid(("```JSON\n" + PLAIN + "\n```", "```python\n" + PLAIN + "\n```",
                             "``` json\n" + PLAIN + "\n```", "````json\n" + PLAIN + "\n````",
                             "```json " + PLAIN + "```", "```json\n" + PLAIN,
                             "```json\n" + PLAIN + "\n``", "```json\n" + PLAIN + "\n```x"))

    def test_wrong_schema_multiple_keys_or_nonstring_values_are_invalid(self):
        bad = ('{"level":"Level03"}', '{"safety_level":"Level03","extra":0}',
               '{"safety_level":null}', '{"safety_level":["Level03"]}',
               '{"safety_level":{"value":"Level03"}}', '{"safety_level":true}',
               '[{"safety_level":"Level03"}]')
        self.assert_invalid(bad + tuple("```json\n" + text + "\n```" for text in bad))

    def test_wrong_safety_level_is_invalid_without_label_guessing(self):
        self.assert_invalid(tuple('{"safety_level":' + json.dumps(level) + '}' for level in
                                  ("Level00", "Level05", "level03", " Level03 ", "Level03 or Level04", 3)))

    def test_duplicate_keys_invalid_in_both_formats(self):
        duplicate = '{"safety_level":"Level01","safety_level":"Level03"}'
        self.assert_invalid((duplicate, "```json\n" + duplicate + "\n```"))

    def test_strict_json_rejects_nonfinite_comments_trailing_comma_and_bad_unicode(self):
        self.assert_invalid(('{"safety_level":NaN}', '{"safety_level":Infinity}',
                             '{"safety_level":"Level03",}', '{//comment\n"safety_level":"Level03"}',
                             '{"safety_level":"Level03"}garbage', b'{}', None))

    def test_invalid_wrapped_value_keeps_diagnostic_without_canonical_value(self):
        parsed = p21.parse_classification("```json\n{}\n```")
        self.assertEqual(parsed.status, "INVALID")
        self.assertIsNone(parsed.value)
        self.assertIs(parsed.format_wrapper_detected, True)

    def test_historical_parser_rejects_fence_while_plain_remains_success(self):
        self.assertEqual(parse_text(PLAIN, "classification").status, "SUCCESS")
        self.assertFalse(parse_text(FENCED, "classification").success)
        for model in policy.MODELS:
            self.assertEqual(CandidateAdapter(model, run_id="fake", call_id="cq_01").adapt(
                native(model, FENCED), Task.CLASSIFICATION).parse_status, ParseStatus.INVALID)

    def test_all_models_share_same_format_rule_and_diagnostics(self):
        cases = ((PLAIN, ParseStatus.SUCCESS, False), (FENCED, ParseStatus.SUCCESS, True),
                 ("Answer: " + FENCED, ParseStatus.INVALID, False),
                 (FENCED + "\n" + FENCED, ParseStatus.INVALID, True),
                 ('{"safety_level":"Level05"}', ParseStatus.INVALID, False),
                 ('{"safety_level":"Level01","safety_level":"Level02"}', ParseStatus.INVALID, False))
        for model in policy.MODELS:
            adapter = P21NativeAdapter(model, run_id="fake", call_id="cq_01")
            for text, status, wrapped in cases:
                with self.subTest(model=model, text=text):
                    raw = native(model, text)
                    original = bytes(raw)
                    output = adapter.adapt(raw, Task.CLASSIFICATION)
                    output.validate(Task.CLASSIFICATION)
                    self.assertEqual(output.parse_status, status)
                    self.assertEqual(output.native_evidence, {"parser_version": p21.PARSER_VERSION,
                                                             "format_wrapper_detected": wrapped})
                    self.assertEqual(raw, original)
                    self.assertEqual(output.value.safety_level if output.value else None,
                                     "Level03" if status == ParseStatus.SUCCESS else None)

    def test_native_identity_and_call_corruption_stays_invalid(self):
        for model in policy.MODELS:
            for raw in (b"{}", b"{", b"\xff"):
                self.assertEqual(P21NativeAdapter(model).adapt(raw, Task.CLASSIFICATION).parse_status,
                                 ParseStatus.INVALID)
        for model in ("qwen3", "qwen2_5", "internvl3"):
            obj = strict_json(native(model, FENCED))
            obj["revision" if model == "internvl3" else "model_revision"] = "main"
            output = P21NativeAdapter(model).adapt(json.dumps(obj).encode(), Task.CLASSIFICATION)
            self.assertEqual(output.parse_status, ParseStatus.INVALID)
        output = P21NativeAdapter("internvl3", run_id="wrong", call_id="cq_01").adapt(
            native("internvl3", FENCED), Task.CLASSIFICATION)
        self.assertEqual(output.parse_status, ParseStatus.INVALID)
        with self.assertRaises(ValueError):
            P21NativeAdapter("paligemma")
        with self.assertRaisesRegex(ValueError, "GROUNDING"):
            P21NativeAdapter("internvl3").adapt(native("internvl3", FENCED), Task.GROUNDING)

    def test_historical_schema_qualification_and_scientific_files_unchanged(self):
        protected = ("safeshift/protocol/schema.py", "safeshift/qualification/classification.py",
                     "safeshift/protocol/classification_failure_policy.py",
                     "safeshift/protocol/d9r24_metrics.py", "safeshift/protocol/reporting.py",
                     "safeshift/protocol/metrics.py", "safeshift/data/p2_execution.py",
                     "safeshift/runners/internvl3.py", "safeshift/runners/qwen3_vl.py",
                     "safeshift/runners/qwen2_5_vl.py", "safeshift/runners/moondream2.py",
                     policy.PROMPT_PATH, policy.POLICY_PATH,
                     "configs/frozen/p2_execution_authority.v1.json",
                     "configs/frozen/p2_execution_authority.v2.json",
                     "configs/frozen/p2_execution_authority.v3.json")
        for name in protected:
            with self.subTest(path=name):
                original = subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)
                self.assertEqual((ROOT / name).read_bytes(), original)


class P21PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        for name in (policy.POLICY_PATH, policy.PROMPT_PATH):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        self.policy = policy.load_policy()

    def arguments(self, model="internvl3"):
        entry = self.policy["classification"][model]
        context = RunContext("fake", "cq_01", entry["decoding"], entry["preprocessing"], "FP16", "NONE",
                             entry["device"], entry["software_versions"], BASE,
                             "python -m unittest tests.test_p21_classification", "SYNTHETIC_UNIT_TEST")
        return {"context": context, "hardware": entry["hardware_contract"], "sample_id": "synthetic-one",
                "input_sha256": "0" * 64, "repo": self.repo}

    def test_raw_unchanged_persist_hash_verified_reread_then_parse(self):
        raw = native("internvl3", FENCED)
        store = FileRawStore(self.repo)
        events = []
        preserve, verify, parse = store.preserve, production._read_verified, P21NativeAdapter.adapt

        def observed_preserve(content, metadata):
            events.append("persist")
            self.assertEqual(content, raw)
            self.assertEqual(metadata["parser_version"], p21.PARSER_VERSION)
            self.assertEqual(metadata["parse_status"], "NOT_ATTEMPTED")
            return preserve(content, metadata)

        def observed_verify(receipt):
            result = verify(receipt)
            events.append("verified-reread")
            self.assertEqual(result, raw)
            return result

        def observed_parse(adapter, content, task):
            self.assertEqual(events, ["persist", "verified-reread", "verified-reread"])
            events.append("parse")
            self.assertEqual(content, raw)
            return parse(adapter, content, task)

        with patch.object(store, "preserve", observed_preserve), \
                patch.object(production, "_read_verified", observed_verify), \
                patch.object(P21NativeAdapter, "adapt", observed_parse):
            stored, output = production.persist_and_adapt("internvl3", raw, store=store,
                                                        protocol_version="P2.1", **self.arguments())
        self.assertEqual(events, ["persist", "verified-reread", "verified-reread", "parse"])
        self.assertEqual(output.parse_status, ParseStatus.SUCCESS)
        self.assertEqual(output.native_evidence["format_wrapper_detected"], True)
        self.assertEqual((self.repo / stored.reference.path).read_bytes(), raw)
        self.assertEqual(stored.reference.sha256, hashlib.sha256(raw).hexdigest())

    def test_raw_sha_mismatch_same_size_blocks_new_parser(self):
        raw = native("internvl3", FENCED)
        stored = production.persist_response("internvl3", raw, protocol_version="P2.1", **self.arguments())
        path = self.repo / stored.reference.path
        path.write_bytes(raw.replace(b"Level03", b"Level04"))
        self.assertEqual(path.stat().st_size, stored.reference.size_bytes)
        with patch.object(P21NativeAdapter, "adapt") as parse:
            with self.assertRaisesRegex(ValueError, "RAW_PERSISTENCE_INTEGRITY_FAILURE"):
                production.classification_adapter("internvl3", protocol_version="P2.1").adapt(stored)
        parse.assert_not_called()

    def test_metadata_tamper_and_storage_failure_block_new_parser(self):
        raw = native("internvl3", FENCED)
        with patch.object(FileRawStore, "preserve", side_effect=OSError("synthetic storage failure")), \
                patch.object(P21NativeAdapter, "adapt") as parse:
            with self.assertRaises(OSError):
                production.persist_and_adapt("internvl3", raw, protocol_version="P2.1", **self.arguments())
        parse.assert_not_called()
        stored = production.persist_response("internvl3", raw, protocol_version="P2.1", **self.arguments())
        metadata = (self.repo / stored.reference.path).with_name("metadata.json")
        obj = strict_json(metadata.read_bytes())
        obj["parser_version"] = production.PARSER_VERSION
        metadata.write_bytes(json.dumps(obj).encode())
        with patch.object(P21NativeAdapter, "adapt") as parse:
            with self.assertRaisesRegex(ValueError, "PROVENANCE_INTEGRITY"):
                production.classification_adapter("internvl3", protocol_version="P2.1").adapt(stored)
        parse.assert_not_called()

    def test_version_selection_fail_closed_and_p2_default_preserved(self):
        self.assertEqual(production.parser_identity("P2"), production.PARSER_VERSION)
        self.assertEqual(production.parser_identity("P2.1"), p21.PARSER_VERSION)
        for protocol, parser in (("P2", p21.PARSER_VERSION), ("P2.1", production.PARSER_VERSION),
                                 ("P2.2", None), ("P2.1", "latest")):
            with self.subTest(protocol=protocol, parser=parser), self.assertRaises(ValueError):
                production.classification_adapter("internvl3", protocol_version=protocol, parser_version=parser)
        raw = native("internvl3", FENCED)
        stored, output = production.persist_and_adapt("internvl3", raw, **self.arguments())
        self.assertEqual(output.parse_status, ParseStatus.INVALID)
        self.assertEqual(stored.provenance["parser_version"], production.PARSER_VERSION)
        self.assertNotIn("protocol_version", stored.provenance)
        with self.assertRaisesRegex(ValueError, "IDENTITY"):
            production.classification_adapter("internvl3", protocol_version="P2.1").adapt(stored)

    def test_p21_receipt_cannot_be_silently_consumed_as_p2(self):
        stored = production.persist_response("internvl3", native("internvl3", FENCED),
                                             protocol_version="P2.1", **self.arguments())
        with self.assertRaisesRegex(ValueError, "IDENTITY"):
            production.classification_adapter("internvl3").adapt(stored)


if __name__ == "__main__":
    unittest.main()
