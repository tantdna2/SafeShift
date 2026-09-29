"""D9R12 offline transcription and parser contracts; no model or dataset access."""

from copy import deepcopy
import hashlib
from pathlib import Path
import unittest

from safeshift.protocol.schema import Classification, Evidence, strict_json
from safeshift.runners.contracts import ParseStatus, Task
from safeshift.runners.paligemma import PendingPaliGemmaAdapter
from safeshift.runners.paligemma_interface_candidate import (
    GROUNDING_PROMPT, GROUNDING_SCOPE, PRESENCE_PROMPT, PRESENCE_SCOPE,
    PresenceAnswer, parse_grounding_candidate, parse_presence_answer_candidate,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/pre_freeze"
RESULT = CONFIG / "paligemma_interface_runtime_result.v1.json"
# Independent literal transcription of the Research Lead-supplied eight outputs.
EXPECTED = [
    ("cls_a", "red_left", "yes<eos>", [3276, 1],
     "a20bd88b22666cfde037143b38a9ffc562754ebb2884c193db049dffa449234d"),
    ("cls_b", "red_small", "yes<eos>", [3276, 1],
     "61379f9a92cf7a6a8fafc2043bb49c06ef68087c2b53e2448ac309dc27206d15"),
    ("cls_c", "blue_circle", "no<eos>", [956, 1],
     "cffa9a330a3dd3d9f1f31671ab5424735d73fa95a6a6695d9991f9f7e5f02c96"),
    ("cls_d", "red_left", "yes<eos>", [3276, 1],
     "a9cdb490380303b4dc7eeaaef07c3208530d85bde32aeffd23dbb2840ff5611c"),
    ("grd_a", "red_left", "<loc0186><loc0114><loc0469><loc0403> red square<eos>",
     [256186, 256114, 256469, 256403, 3118, 7800, 1],
     "7ed98406e60f675af49362a1ed572e7611ad737c01aa8bca25a7d0ea4aa4fb4b"),
    ("grd_b", "red_right", "<loc0186><loc0586><loc0478><loc0876> red square<eos>",
     [256186, 256586, 256478, 256876, 3118, 7800, 1],
     "125dbd3f3dabfb571b81732aefdf9e2155c508c2811dea7bf171de0784efa4b6"),
    ("grd_c", "red_small", "<loc0257><loc0188><loc0402><loc0331> red square<eos>",
     [256257, 256188, 256402, 256331, 3118, 7800, 1],
     "66b7686bcb9c046927df939ed5932b0f0c34f8a4c164407cf21815cb73aa4138"),
    ("grd_d", "blue_circle", "<loc0359><loc0366><loc0662><loc0659> red square<eos>",
     [256359, 256366, 256662, 256659, 3118, 7800, 1],
     "b90fedac481d63021f7bdcabd9839c8f0a46240b749ffaca2d2be4d3b5f01b94"),
]


class EvidenceRecordTests(unittest.TestCase):
    def setUp(self):
        self.record = strict_json(RESULT.read_bytes())
        self.observed = self.record["observed_evidence"]
        self.plan = strict_json((CONFIG / "paligemma_interface_qualification.v1.json").read_bytes())

    def test_exact_provenance_and_honest_verification_authority(self):
        r, o = self.record, self.observed
        self.assertEqual(r["base_sha"], "da7a3b8098eb40edba8858791d01d30b564bcc78")
        source = r["source"]
        self.assertEqual(source["bundle_sha256"],
                         "058770516daf94a6d12501d33998ae52c7051cdab199f7973b01f59da3d1105f")
        self.assertIn("Codex did not inspect raw bundle bytes", source["recording_basis"])
        self.assertEqual(source["bundle_verification"], {
            "verified_by": "RESEARCH_LEAD", "checksummed_artifacts": 76, "size_and_sha256_matches": 76})
        for key in ("bundle_bytes_inspected_by_codex", "bundle_committed", "raw_artifacts_committed"):
            self.assertIs(source[key], False)
        self.assertEqual(o["execution_commit"], "ceb56d5174a387362e3ef6a5af3b6618123bc8a7")
        self.assertEqual(o["qualification_plan_path"], "configs/pre_freeze/paligemma_interface_qualification.v1.json")
        self.assertEqual(o["qualification_plan_sha256"],
                         "05e1f8f8f56af2abfd8f6fe8fb66a5f820faa3508506072adf5b850fdcdcc2fd")
        self.assertEqual(hashlib.sha256((ROOT / o["qualification_plan_path"]).read_bytes()).hexdigest(),
                         o["qualification_plan_sha256"])
        self.assertEqual(o["model_id"], "google/paligemma-3b-mix-448")
        self.assertEqual(o["revision"], "ead2d9a35598cb89119af004f5d023b311d1c4a1")
        self.assertEqual(o["kind"], "OBSERVED_EVIDENCE")
        self.assertEqual(o["evidence_collection_status"], "COMPLETE")

    def test_exact_runtime_and_raw_before_parser_provenance(self):
        self.assertEqual(self.observed["runtime"], {
            "python": "3.11.11", "torch": "2.6.0+cu124", "transformers": "4.57.1",
            "gpu_name": "Tesla T4", "visible_gpu_count": 1, "compute_capability": [7, 5],
            "device": "cuda:0", "precision": "FP16", "quantization": "NONE",
            "owner_internet_off_attested": True, "model_load_count": 1, "native_generate_calls": 8})
        raw = self.observed["raw_before_parser"]
        self.assertEqual(raw["status"], "PASS")
        self.assertEqual(raw["verification_authority"], "RESEARCH_LEAD")
        self.assertIn("no Codex bundle-byte inspection", raw["basis"])
        self.assertEqual(raw["documented_order"], ["native_generate", "exclusive_raw_persistence",
            "flush_fsync", "reread", "size_sha256_verification", "observation_only"])
        self.assertEqual(raw["documented_order"], self.plan["raw_contract"]["order"])
        self.assertIs(raw["d9r11_parser_executed"], False)
        self.assertEqual(raw["offline_candidate_validation_task"], "D9R12")

    def test_exact_eight_observations_hashes_ids_and_loc_tokens(self):
        calls = self.observed["observations"]
        self.assertEqual(len(calls), 8)
        for call, expected, case in zip(calls, EXPECTED, self.plan["cases"]):
            case_id, fixture, text, ids, sha = expected
            with self.subTest(case=case_id):
                self.assertEqual(call["case_id"], case_id)
                self.assertEqual(call["fixture_id"], fixture)
                self.assertEqual(call["decoded_with_special_tokens"], text)
                self.assertEqual(call["continuation_ids"], ids)
                self.assertEqual(call["raw_sha256"], sha)
                self.assertEqual(call["task_type"], case["task_type"])
                self.assertEqual(call["fixture_id"], case["fixture_id"])
                self.assertEqual(call["prompt"], self.plan["prompts"][case["prompt_id"]]["text"])
                locs = [f"<loc{v - 256000:04d}>" for v in ids if 256000 <= v <= 257023]
                self.assertEqual(call["ordered_loc_tokens"], locs)
                if case_id.startswith("cls"):
                    self.assertEqual(call["decoded_text"], text[:-5])
                else:
                    self.assertEqual(len(locs), 4)
                    self.assertTrue(text.startswith("".join(locs)))
                    self.assertNotIn("decoded_text", call)  # Not separately supplied.
        self.assertEqual(calls[3]["repeat_of"], "cls_a")

    def test_interpretation_separate_from_observations_and_pending_status(self):
        r = self.record
        interpretation = r["research_lead_interpretation"]
        self.assertEqual(interpretation["kind"], "RESEARCH_LEAD_INTERPRETATION")
        self.assertEqual(interpretation["classification"], "STABLE_YES_NO_EVIDENCE")
        self.assertEqual(interpretation["grounding_grammar"], "FOUR_LOC_TOKENS_PLUS_LABEL_PLUS_EOS")
        for key in ("production_class_vocabulary", "production_safety_semantics"):
            self.assertEqual(interpretation[key], "NOT_QUALIFIED")
        for key in ("multi_label", "abstention"):
            self.assertEqual(interpretation[key], "UNTESTED")
        self.assertEqual(interpretation["no_detection_grammar"], "NOT_ESTABLISHED")
        self.assertIs(interpretation["separate_qualification_decision_required"], True)
        self.assertEqual(r["preserved_status"], {
            "real_runtime_status": "RUNTIME_SMOKE_PASS", "exact_runtime_verified": True,
            "classification_interface": "PENDING_QUALIFICATION", "grounding": "PENDING_QUALIFICATION",
            "external_gate": "PENDING_QUALIFICATION", "paligemma_role": "BACKUP_1",
            "primary_roster_count": 4, "protocol_freeze": "BLOCKED", "inspecsafe_authorized": False})
        self.assertEqual(r["preserved_status"], self.plan["preserved_status"])
        for key in ("promotion", "synthetic_v1_executed", "inspecsafe_executed"):
            self.assertIs(r[key], False)
        self.assertEqual(r["codex_execution"], {"gpu": False, "model": False, "provision": False})
        contract = r["offline_adapter_contract"]
        self.assertEqual(contract["presence_mapping"], {"yes": True, "no": False})
        self.assertIsNone(contract["production_safety_level_mapping"])
        self.assertEqual(contract["native_order"], ["y_min", "x_min", "y_max", "x_max"])
        self.assertEqual(contract["loc_integer_range"], [0, 1023])
        self.assertEqual(contract["d4"], "[x_min/1024.0,y_min/1024.0,x_max/1024.0,y_max/1024.0]")
        for key in ("clamp", "rescale_1023_to_1", "heuristic_repair", "fabricated_box", "point_to_box",
                    "artificial_zero_iou", "syntax_success_implies_semantic_correctness", "production_adapter_enabled"):
            self.assertIs(contract[key], False)

    def test_negative_is_parseable_and_stays_a_hallucinated_prediction(self):
        call = self.observed["observations"][-1]
        original = deepcopy(call)
        result = parse_grounding_candidate(call["decoded_with_special_tokens"], prompt=call["prompt"])
        self.assertEqual(result.parse_status, ParseStatus.SUCCESS)
        self.assertEqual(result.value, Evidence((366/1024, 359/1024, 659/1024, 662/1024), "red square"))
        self.assertEqual(call, original)
        negative = self.record["research_lead_interpretation"]["grounding_negative"]
        self.assertEqual(negative["semantics"], "SEMANTIC_HALLUCINATION_TARGET_SELECTIVITY_FAILURE")
        self.assertEqual(negative["syntax"], "PARSEABLE_FOUR_LOC_PLUS_LABEL_PLUS_EOS")
        for key in ("target_present", "parser_failure", "convert_to_empty_prediction", "semantic_repair"):
            self.assertIs(negative[key], False)


class CandidateParserTests(unittest.TestCase):
    def test_all_approved_classification_answers_have_only_scoped_presence_meaning(self):
        for _, _, text, _, _ in EXPECTED[:4]:
            answer = text[:-5]
            result = parse_presence_answer_candidate(answer, prompt=PRESENCE_PROMPT)
            self.assertEqual(result.scope, PRESENCE_SCOPE)
            self.assertEqual(result.parse_status, ParseStatus.SUCCESS)
            self.assertEqual(result.value, PresenceAnswer(answer, answer == "yes"))
            self.assertNotIsInstance(result.value, Classification)
            self.assertIsNone(result.error)

    def test_classification_rejects_fuzzy_unexpected_and_non_text(self):
        for text in ("Yes", "YES", "No", " yes", "yes ", "yes\n", "yes\x00", "yesterday", "not yes",
                     "yes, there is", "no.", "true", "false", "safe", "unsafe", "Level01", "red square",
                     "yes<eos>", "no<eos>", '"yes"', "yes/no", "unknown", "", None, True, 1, [], b"yes"):
            with self.subTest(text=text):
                result = parse_presence_answer_candidate(text, prompt=PRESENCE_PROMPT)
                self.assertEqual(result.parse_status, ParseStatus.INVALID)
                self.assertIsNone(result.value)
                self.assertEqual(result.error, "INVALID_CLASSIFICATION_OUTPUT")

    def test_exact_prompt_scope_is_mandatory(self):
        for parser, text, prompt in (
                (parse_presence_answer_candidate, "yes", PRESENCE_PROMPT),
                (parse_grounding_candidate, EXPECTED[4][2], GROUNDING_PROMPT)):
            with self.assertRaises(TypeError):
                parser(text)
            for wrong in (None, "", prompt + "\n", prompt.upper(), "Is this safe?", "detect blue circle"):
                with self.subTest(parser=parser.__name__, prompt=wrong):
                    result = parser(text, prompt=wrong)
                    self.assertEqual(result.parse_status, ParseStatus.INVALID)
                    self.assertIsNone(result.value)

    def test_all_four_observed_boxes_use_native_axes_and_exact_1024_divisor(self):
        expected_boxes = [(114, 186, 403, 469), (586, 186, 876, 478),
                          (188, 257, 331, 402), (366, 359, 659, 662)]
        for observation, xyxy in zip(EXPECTED[4:], expected_boxes):
            result = parse_grounding_candidate(observation[2], prompt=GROUNDING_PROMPT)
            self.assertEqual(result.scope, GROUNDING_SCOPE)
            self.assertEqual(result.parse_status, ParseStatus.SUCCESS)
            self.assertEqual(result.value, Evidence(tuple(v/1024 for v in xyxy), "red square"))
            self.assertNotEqual(result.value.bbox, tuple(v/1023 for v in xyxy))
            self.assertIsNone(result.error)

    def test_boundary_no_rescale_no_clamp(self):
        result = parse_grounding_candidate(
            "<loc0000><loc0001><loc1023><loc1022> red square<eos>", prompt=GROUNDING_PROMPT)
        self.assertEqual(result.value.bbox, (1/1024, 0, 1022/1024, 1023/1024))
        self.assertLess(max(result.value.bbox), 1.0)
        for locs in ((0, 0, 1024, 1023), (0, 0, 1023, 9999), (-1, 0, 4, 5),
                     (8, 2, 4, 5), (1, 8, 4, 5), (1, 2, 1, 5), (1, 2, 4, 2)):
            text = "".join(f"<loc{v:04d}>" for v in locs) + " red square<eos>"
            self.assert_grounding_invalid(text)

    def assert_grounding_invalid(self, text):
        with self.subTest(text=text):
            result = parse_grounding_candidate(text, prompt=GROUNDING_PROMPT)
            self.assertEqual(result.parse_status, ParseStatus.INVALID)
            self.assertIsNone(result.value)  # Neither empty detection nor invented box.
            self.assertEqual(result.error, "PARSER_FAIL_NO_REPAIR")

    def test_malformed_or_unobserved_grammar_fails_closed_without_repair(self):
        valid = EXPECTED[4][2]
        for text in (None, b"", [], 1, "", "<eos>", "none", "[]", "no red square<eos>",
                     "(0.3,0.4)", '{"bbox":[0,0,1,1]}', "red square<eos>",
                     valid[:-5], valid + "\n", " " + valid, valid + " extra", "prefix " + valid,
                     valid + valid, valid + "; " + valid,
                     valid.replace("<loc0186>", ""), valid.replace("<loc0186>", "<loc186>"),
                     valid.replace("<loc0186>", "<loc00186>"), valid.replace("<loc0186>", "<loc0.18>"),
                     valid.replace("<loc0186>", "<loc\u0660\u0661\u0668\u0666>"),
                     valid.replace("<loc0186>", "<loc0186><loc0114>"),
                     valid.replace("><loc", "> <loc"), valid.replace(" red", "  red"),
                     valid.replace(" red", "\tred"), valid.replace(" red", "<seg001> red"),
                     valid.replace("red square", "blue circle"), valid.replace("red square", "Red square"),
                     valid.replace("<eos>", " <eos>"), valid + "<eos>"):
            self.assert_grounding_invalid(text)

    def test_production_adapter_remains_pending_for_all_observed_outputs(self):
        adapter = PendingPaliGemmaAdapter()
        for case_id, _, text, _, _ in EXPECTED:
            task = Task.CLASSIFICATION if case_id.startswith("cls") else Task.GROUNDING
            result = adapter.adapt(text.encode(), task)
            result.validate(task)
            self.assertEqual(result.parse_status,
                             ParseStatus.INVALID if task == Task.CLASSIFICATION else ParseStatus.UNSUPPORTED)
            self.assertIsNone(result.value)
            self.assertEqual(result.native_evidence, {"status": "PENDING_QUALIFICATION"})


if __name__ == "__main__":
    unittest.main()
