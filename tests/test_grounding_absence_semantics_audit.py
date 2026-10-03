"""G2 documentary locks and handcrafted absence failures; no model execution."""

import hashlib
from pathlib import Path
import subprocess
import unittest

from safeshift.protocol.grounding_interface_candidate import (
    NativeDetections, PALI_ABSENCE, QWEN_ABSENCE, VERSION,
    parse_paligemma, parse_qwen3,
)
from safeshift.protocol.schema import strict_json

ROOT = Path(__file__).resolve().parents[1]
BASE = "dd83c6231e5758cdb85ba84e293d4b462e38a696"
AUDIT = "configs/pre_freeze/grounding_absence_semantics_audit.v1.json"


class AbsenceSemanticsAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = strict_json((ROOT / AUDIT).read_bytes())

    def test_both_blockers_have_no_invented_native_zero_output(self):
        for model, blocker in [("qwen3", QWEN_ABSENCE), ("paligemma", PALI_ABSENCE)]:
            decision = self.audit["decisions"][model]
            self.assertEqual(decision["status"], "BLOCKED")
            self.assertEqual(decision["blocker"], blocker)
            self.assertIsNone(decision["exact_native_zero_output"])
        self.assertIsNone(self.audit["new_contract_version"])
        self.assertEqual(self.audit["retained_contract"]["version"], VERSION)

    def test_qwen_empty_arrays_stay_blocked_for_every_query(self):
        for label in ["red square", "blue circle", "object"]:
            for text in ["[]", "[ ]", "\n[\t]\r\n"]:
                with self.subTest(label=label, text=text):
                    self.assertEqual(parse_qwen3(text, label=label),
                                     NativeDetections("BLOCKED", error=QWEN_ABSENCE))

    def test_pali_empty_decode_stays_blocked_for_every_query(self):
        for label in ["red square", "blue circle", "object"]:
            self.assertEqual(parse_paligemma("", label=label),
                             NativeDetections("BLOCKED", error=PALI_ABSENCE))

    def test_blank_prose_eos_and_invalid_variants_never_become_zero(self):
        common = [None, [], {}, " ", "\n", "\t", "null", "None", "{}",
                  "No objects found.", "not present", "<eos>", "</s>",
                  "[] trailing", "```json\n[]\n```", "[", "[null]"]
        for parser, extra in [(parse_qwen3, [""]), (parse_paligemma, ["[]", "[ ]"])]:
            for raw in common + extra:
                with self.subTest(parser=parser.__name__, raw=raw):
                    result = parser(raw, label="red square")
                    self.assertEqual(result.status, "INVALID")
                    self.assertIsNone(result.detections)

    def test_partial_detection_never_becomes_successful_subset_or_zero(self):
        q = '[{"bbox_2d":[10,20,30,40],"label":"red square"},{}]'
        p = '<loc0010><loc0020><loc0030><loc0040> red square; no match'
        for parser, raw in [(parse_qwen3, q), (parse_paligemma, p)]:
            result = parser(raw, label="red square")
            self.assertEqual(result.status, "INVALID")
            self.assertIsNone(result.detections)

    def test_positive_multiple_contract_still_preserves_all_detections(self):
        q = '[{"bbox_2d":[100,200,300,400],"label":"red square"}]'
        p = '<loc0100><loc0200><loc0300><loc0400> red square'
        for parser, one, two in [(parse_qwen3, q, q[:-1] + ',' + q[1:]),
                                 (parse_paligemma, p, p + '; ' + p)]:
            single, multiple = [parser(raw, label="red square") for raw in [one, two]]
            self.assertEqual(single.status, "SUCCESS")
            self.assertEqual(multiple.status, "SUCCESS")
            self.assertEqual(multiple.detections, single.detections * 2)

    def test_plan_and_audit_cannot_authorize_qualification_or_promotion(self):
        plan = strict_json((ROOT / self.audit["retained_contract"]["plan"]).read_bytes())
        for record in [self.audit, plan]:
            self.assertEqual(record["EXECUTION_STATUS"], "NOT_RUN")
            self.assertEqual(record["MODEL_GPU_EXECUTION"], "NO")
            self.assertEqual(record["INSPECSAFE"], "NOT_RUN")
            self.assertIs(record["execution_authorized"], False)
            self.assertIs(record["promotion"], False)
            self.assertIsNone(record["qualification_verdict"])
        self.assertEqual(self.audit["qualification"], "NOT_RUN")
        for model in ["qwen3", "paligemma"]:
            self.assertEqual(plan["models"][model]["absence_semantics"],
                             self.audit["decisions"][model]["blocker"])

    def test_official_source_revisions_hashes_and_locators_are_explicit(self):
        sources = {s["id"]: s for s in self.audit["sources"]}
        self.assertEqual(len(sources), 29)
        for s in sources.values():
            self.assertRegex(s["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(s["bytes"], 0)
            self.assertTrue(s["locator"])
            self.assertFalse(s["sufficient_for_absence_resolution"])
            self.assertEqual(s["execution"], "NOT_EXECUTED_SOURCE_TEXT_ONLY")
        for key in ["qwen_eval_input", "qwen_eval_parser", "qwen_eval_serialization",
                    "qwen_finetune_preprocess", "qwen_cookbook"]:
            self.assertEqual(sources[key]["revision"], "96588727e44c78b25ba03ea03b8e12f7e64fd0da")
        for key in ["pali_train_eval_suffix", "pali_tokenize_ops", "pali_refcoco_target", "pali_decode"]:
            self.assertEqual(sources[key]["revision"], "0127fb6b337ee2a27bf4e54dea79cff176527356")
        old = strict_json((ROOT / "configs/pre_freeze/grounding_interface_sources.v2.json").read_bytes())
        for s in old["sources"]:
            self.assertEqual(sources[s["id"]]["sha256"], s["sha256"])
        for decision in self.audit["decisions"].values():
            self.assertTrue(set(decision["source_ids"]) <= sources.keys())

    def test_nine_g1_files_match_base_hashes_and_git_blobs(self):
        self.assertEqual(self.audit["base_sha"], BASE)
        self.assertEqual(len(self.audit["historical_v2_sha256"]), 9)
        for path, digest in self.audit["historical_v2_sha256"].items():
            with self.subTest(path=path):
                raw = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
                self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
                expected = subprocess.check_output(["git", "rev-parse", BASE + ":" + path], cwd=ROOT)
                actual = subprocess.check_output(["git", "hash-object", "--path=" + path, path], cwd=ROOT)
                self.assertEqual(actual, expected)

    def test_logs_append_g1_closure_without_rewriting_history(self):
        closure = "G1 merged as PR #68"
        for path in ["DECISIONS.md", "TASKS.md"]:
            original = subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT)
            current = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
            self.assertTrue(current.startswith(original), path)
            appended = current[len(original):].decode("utf-8")
            self.assertIn(closure, appended)
            self.assertIn(BASE, appended)


if __name__ == "__main__":
    unittest.main()
