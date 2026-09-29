"""D9R13 contract locks: pure schemas/strings and base-file checks, no gate run."""

import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import unittest

from safeshift.protocol.prompts import classification_request, grounding_request
from safeshift.protocol.schema import (
    Classification, Evidence, Grounding, HAZARDS, SAFETY_LEVELS, parse_text, strict_json,
)
from safeshift.runners.contracts import ParseStatus, Task
from safeshift.runners.paligemma import PendingPaliGemmaAdapter, loc_values_to_d4
from safeshift.runners.paligemma_interface_candidate import (
    GROUNDING_PROMPT, PRESENCE_PROMPT, parse_grounding_candidate, parse_presence_answer_candidate,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = "a3192ddefbc28fe2997190819744e8f4796a6d85"
CONFIG = ROOT / "configs/pre_freeze"
CANDIDATE = CONFIG / "paligemma_production_interface_candidate.v1.json"
# Path is only validated by prompt builders; no image is opened or generated.
IMAGE = "tests/fixtures/pre_freeze/contract-only.png"


class ProductionInterfaceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = strict_json(CANDIDATE.read_bytes())

    def test_exact_provenance_and_transcription_limits(self):
        c, p = self.c, self.c["provenance"]
        self.assertEqual(c["schema_version"], "paligemma-production-interface-candidate-v1")
        self.assertEqual(c["task_id"], "W2.6-D9R13-PALIGEMMA-PRODUCTION-INTERFACE-FREEZE-PREP")
        self.assertEqual(c["base_sha"], BASE)
        self.assertEqual(p["previous_merge_commit"], BASE)
        self.assertEqual(p["previous_task"], "D9R12_COMPLETE_PR_59_MERGED")
        self.assertEqual((c["model_id"], c["revision"]), (
            "google/paligemma-3b-mix-448", "ead2d9a35598cb89119af004f5d023b311d1c4a1"))
        expected_hashes = {
            "runtime_result": "555701224f8b745391c65e75c5ff876bc039648fa1f4da02bc96403a3112e736",
            "qualification_plan": "05e1f8f8f56af2abfd8f6fe8fb66a5f820faa3508506072adf5b850fdcdcc2fd",
        }
        for key, expected in expected_hashes.items():
            self.assertEqual(p[key + "_sha256"], expected)
            self.assertEqual(hashlib.sha256((ROOT / p[key]).read_bytes()).hexdigest(), expected)
        result = strict_json((ROOT / p["runtime_result"]).read_bytes())
        self.assertEqual(p["execution_commit"], "ceb56d5174a387362e3ef6a5af3b6618123bc8a7")
        self.assertEqual(p["execution_commit"], result["observed_evidence"]["execution_commit"])
        self.assertEqual(p["bundle_sha256"], result["source"]["bundle_sha256"])
        self.assertEqual(p["evidence_authority"], "RESEARCH_LEAD_APPROVED_TRANSCRIPTION_NOT_NEW_RUNTIME")
        self.assertFalse(p["bundle_bytes_inspected_by_codex"])
        for source in p["canonical_sources"]:
            self.assertTrue((ROOT / source.split("#")[0]).is_file())

    def test_c1_exact_existing_template_and_policy_required(self):
        c = self.c["classification"]
        policy = "SYNTHETIC CONTRACT TEXT ONLY; not an approved safety policy."
        request = classification_request(ROOT, IMAGE, policy)
        self.assertEqual(c["prompt_template"].replace("{industry_safety_policy}", policy), request.prompt)
        self.assertEqual(request.prompt_version, "p2-call1-draft-v1")
        self.assertEqual(c["variable_fields"], ["industry_safety_policy"])
        for missing in (None, "", "   "):
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                classification_request(ROOT, IMAGE, missing)
        self.assertEqual(list(inspect.signature(classification_request).parameters),
                         ["repo", "image_path", "industry_safety_policy"])
        self.assertEqual(c["policy_source"], "UNRESOLVED_EXACT_POLICY_TEXT_VERSION_AND_HASH")
        self.assertEqual(c["native_prompt_wrapper"], "UNRESOLVED_NO_AUTOMATIC_ANSWER_EN_PREFIX")

    def test_classification_is_four_class_single_label_not_binary_or_abstention(self):
        c = self.c["classification"]
        self.assertEqual(c["canonical_labels"], ["Level01", "Level02", "Level03", "Level04"])
        self.assertEqual(tuple(c["canonical_labels"]), SAFETY_LEVELS)
        self.assertTrue(c["multiclass"])
        self.assertFalse(c["multilabel"])
        self.assertFalse(c["binary_native_task"])
        self.assertIsNone(c["abstention_label"])
        for label in SAFETY_LEVELS:
            result = parse_text(json.dumps({"safety_level": label}), "classification")
            self.assertEqual(result.value, Classification(label))
        for label in ("yes", "no", "safe", "unsafe", "Level1", "level01", "ABSTAIN", None,
                      ["Level01", "Level02"]):
            result = parse_text(json.dumps({"safety_level": label}), "classification")
            self.assertFalse(result.success)
            self.assertIsNone(result.value)
        self.assertFalse(parse_text('{"safety_level":"Level01","hazards":[]}', "classification").success)
        schema = strict_json((ROOT / "schemas/canonical.schema.json").read_bytes())
        self.assertEqual(schema["$defs"]["classification"]["properties"]["safety_level"]["enum"],
                         c["canonical_labels"])

    def test_no_speculative_production_vocabulary_or_mapping(self):
        c = self.c["classification"]
        for key in ("qualified_production_prompt", "supported_production_native_grammar",
                    "native_to_canonical_mapping"):
            self.assertIsNone(c[key])
        observed = c["observed_only"]
        self.assertEqual(observed["prompt"], PRESENCE_PROMPT)
        self.assertEqual(observed["grammar"], ["yes", "no"])
        self.assertEqual(observed["mapping"], {"yes": True, "no": False})
        self.assertIsNone(observed["canonical_safety_mapping"])
        for value in ("yes", "no"):
            self.assertNotIsInstance(parse_presence_answer_candidate(value, prompt=PRESENCE_PROMPT).value,
                                     Classification)
            self.assertEqual(parse_presence_answer_candidate(value, prompt=c["prompt_template"]).parse_status,
                             ParseStatus.INVALID)

    def test_b2_exact_prompt_vocabulary_and_no_cross_call_or_gt_input(self):
        g = self.c["grounding"]
        request = grounding_request(ROOT, IMAGE)
        self.assertEqual(g["canonical_prompt_template"], request.prompt)
        self.assertEqual(g["canonical_prompt_version"], request.prompt_version)
        self.assertEqual(tuple(g["canonical_hazard_ids"]), HAZARDS)
        self.assertEqual(len(HAZARDS), 12)
        self.assertEqual(g["variable_fields"], [])
        self.assertEqual(list(inspect.signature(grounding_request).parameters),
                         ["repo", "image_path", "vocabulary"])
        with self.assertRaises(ValueError):
            grounding_request(ROOT, IMAGE, ["red square"])
        self.assertIsNone(g["production_native_prompt_template"])
        self.assertIsNone(g["native_to_hazard_mapping"])
        self.assertFalse(parse_text('{"hazards":[{"hazard_type":"red square","evidence":[]}]}',
                                    "grounding").success)

    def test_canonical_empty_unlocalized_and_multiple_are_distinct(self):
        empty = parse_text('{"hazards":[]}', "grounding")
        unlocalized = parse_text('{"hazards":[{"hazard_type":"SMOKE","evidence":[]}]}', "grounding")
        self.assertEqual(empty.value, Grounding(()))
        self.assertTrue(unlocalized.success)
        self.assertNotEqual(empty.value, unlocalized.value)
        obj = {"hazards": [
            {"hazard_type": "SMOKE", "evidence": [
                {"bbox": [0.1, 0.1, 0.2, 0.2], "label": "visible evidence"},
                {"bbox": [0.3, 0.3, 0.4, 0.4]}]},
            {"hazard_type": "OPEN_FLAME", "evidence": [{"bbox": [0.6, 0.6, 0.8, 0.8]}]},
        ]}
        result = parse_text(json.dumps(obj), "grounding")
        self.assertTrue(result.success)
        self.assertEqual(result.boxes_valid, 3)
        self.assertEqual(len(result.value.hazards), 2)
        self.assertEqual(result.value.hazards[0].evidence[0].label, "visible evidence")
        for invalid_probe in ('{}', '{"bbox":[]}', '{"hazards":[]}', '{"bbox":null}'):
            self.assertFalse(parse_text(invalid_probe, "external_probe").success)

    def test_no_native_empty_or_multiple_grammar_invention(self):
        g = self.c["grounding"]
        self.assertEqual(g["no_detection"]["canonical_no_hazard"], {"hazards": []})
        for key in ("native_grammar", "native_empty_mapping"):
            self.assertIsNone(g["no_detection"][key])
        self.assertFalse(g["no_detection"]["existing_evidence_safe_to_map_to_empty"])
        self.assertEqual(g["no_detection"]["decision"],
                         "B_ADDITIONAL_RUNTIME_QUALIFICATION_REQUIRED_UNDER_PRODUCTION_PROMPT")
        self.assertTrue(g["multiple_boxes"]["canonical_production_required"])
        self.assertFalse(g["multiple_boxes"]["native_support_enabled"])
        self.assertIsNone(g["multiple_boxes"]["native_grammar"])
        valid = "<loc0000><loc0000><loc0500><loc0500> red square<eos>"
        for text in ("", "<eos>", "none", "[]", '{"hazards":[]}', valid + valid,
                     valid[:-5] + "; " + valid):
            parsed = parse_grounding_candidate(text, prompt=GROUNDING_PROMPT)
            self.assertEqual(parsed.parse_status, ParseStatus.INVALID)
            self.assertIsNone(parsed.value)

    def test_exact_gate_requirements_and_closed_label_proposal(self):
        gate = self.c["external_gate"]
        manifest = strict_json((ROOT / gate["manifest"]).read_bytes())
        self.assertEqual(hashlib.sha256((ROOT / gate["manifest"]).read_bytes()).hexdigest(),
                         "fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379")
        self.assertEqual(gate["manifest_sha256"],
                         "fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379")
        self.assertEqual(gate["case_ids"], [c["case_id"] for c in manifest["cases"]])
        self.assertEqual(gate["exact_query_to_label_proposal"], {
            "Locate the red square.": "red square", "Locate the green circle.": "green circle",
            "Locate the yellow triangle.": "yellow triangle", "Locate the cyan rectangle.": "cyan rectangle"})
        self.assertEqual(set(gate["exact_query_to_label_proposal"]),
                         {c["target_query"] for c in manifest["cases"]})
        self.assertEqual(gate["box_count"], 1)
        self.assertEqual(gate["target_absent_cases"], 0)
        self.assertFalse(gate["multiple_boxes_required"])
        self.assertFalse(gate["classification_scored"])
        self.assertFalse(gate["query_mapping_enabled"])
        self.assertIsNone(gate["no_detection_success_representation"])
        self.assertEqual(gate["iou_and_area"], "DIAGNOSTIC_ONLY")
        self.assertIsNone(gate["iou_threshold"])
        self.assertIsNone(gate["area_threshold"])
        self.assertEqual(gate["pass_requirements"], ["valid schema/geometry", "predicted center inside target bbox",
            "predicted bbox excludes distractor center", "systematic reciprocal-swap tracking", "not full image",
            "explicit human NO_GIANT for every case"])

    def test_observed_grammar_not_expanded_to_proposed_labels_or_fuzzy_text(self):
        g = self.c["grounding"]
        self.assertEqual(g["supported_native_grammar"]["labels"], ["red square"])
        self.assertFalse(g["arbitrary_label_support_enabled"])
        template = "<loc0000><loc0000><loc0500><loc0500> {}<eos>"
        for label in ("green circle", "yellow triangle", "cyan rectangle", "Red square", "red rectangle"):
            result = parse_grounding_candidate(template.format(label), prompt=GROUNDING_PROMPT)
            self.assertEqual(result.parse_status, ParseStatus.INVALID)
        for answer in ("Yes", " yes", "no.", "safe", "unsafe", "Level01"):
            self.assertEqual(parse_presence_answer_candidate(answer, prompt=PRESENCE_PROMPT).parse_status,
                             ParseStatus.INVALID)

    def test_d4_no_clamp_rescale_or_semantic_repair(self):
        self.assertEqual(loc_values_to_d4([0, 1, 1023, 1022]), [1/1024, 0, 1022/1024, 1023/1024])
        for values in ([0, 0, 1024, 1023], [5, 0, 1, 10], [0, 0, 0, 1], [False, 0, 2, 3]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                loc_values_to_d4(values)
        # No expected-target/image/GT argument can silently erase this hallucination.
        self.assertEqual(list(inspect.signature(parse_grounding_candidate).parameters),
                         ["decoded_with_special_tokens", "prompt"])
        result = parse_grounding_candidate(
            "<loc0359><loc0366><loc0662><loc0659> red square<eos>", prompt=GROUNDING_PROMPT)
        self.assertEqual(result.parse_status, ParseStatus.SUCCESS)
        self.assertEqual(result.value, Evidence((366/1024, 359/1024, 659/1024, 662/1024), "red square"))
        for key in ("parser_ground_truth_input", "drop_hallucinated_prediction", "fuzzy_parser", "semantic_repair",
                    "clamp", "rescale_1023_to_1", "heuristic_repair", "fabricated_box", "point_to_box",
                    "artificial_zero_iou", "production_adapter_enabled"):
            self.assertIs(self.c["adapter_design"][key], False)

    def test_unresolved_features_and_conditional_minimal_cases(self):
        c = self.c
        self.assertEqual(c["classification"]["unresolved_features"],
                         ["C1_POLICY_PIN", "C1_NATIVE_PROMPT_AND_FOUR_LEVEL_OUTPUT_MAPPING"])
        self.assertEqual(c["grounding"]["unresolved_features"], ["B2_NATIVE_PROMPT_AND_HAZARD_ASSOCIATION",
            "EXACT_LABEL_GRAMMAR_BEYOND_RED_SQUARE", "NATIVE_NO_HAZARD_REPRESENTATION",
            "NATIVE_MULTIPLE_HAZARDS_AND_EVIDENCE"])
        self.assertEqual(c["external_gate"]["unresolved_features"],
                         ["EXACT_GATE_QUERY_RENDERING_REVIEW", "EXACT_LABEL_GRAMMAR_BEYOND_RED_SQUARE"])
        for section in (c, c["classification"], c["grounding"]):
            self.assertIs(section["additional_runtime_qualification_required"], True)
        runtime = c["next_runtime_design"]
        self.assertEqual(runtime["status"], "CONDITIONAL_MINIMUM_NOT_EXECUTABLE_OR_AUTHORIZED")
        self.assertEqual(runtime["minimum_case_count"], 9)
        self.assertEqual([case["id"] for case in runtime["cases"]], ["C_LEVEL01", "C_LEVEL02", "C_LEVEL03",
            "C_LEVEL04", "G_GREEN_CIRCLE", "G_YELLOW_TRIANGLE", "G_CYAN_RECTANGLE", "G_B2_MULTIPLE", "G_B2_NONE"])
        self.assertEqual([case["prompt"] for case in runtime["cases"] if "prompt" in case],
                         ["detect green circle", "detect yellow triangle", "detect cyan rectangle"])
        self.assertFalse(runtime["gate_cases_reused_for_qualification"])
        self.assertFalse(runtime["native_detect_empty_case_needed_for_gate"])
        self.assertTrue(runtime["raw_before_parser"])

    def test_pending_status_and_no_execution_or_promotion(self):
        c = self.c
        self.assertEqual(c["status"], "PREP_CONTRACT_ONLY_NOT_QUALIFIED")
        self.assertEqual(c["preserved_status"], {
            "real_runtime_status": "RUNTIME_SMOKE_PASS", "exact_runtime_verified": True,
            "classification_interface": "PENDING_QUALIFICATION", "grounding": "PENDING_QUALIFICATION",
            "external_gate": "PENDING_QUALIFICATION", "paligemma_role": "BACKUP_1",
            "primary_roster_count": 4, "protocol_freeze": "BLOCKED", "inspecsafe_authorized": False})
        self.assertEqual(c["execution"], {"gpu": False, "kaggle": False, "model": False,
                                        "provision": False, "synthetic_gate": False, "inspecsafe": False})
        for key in ("synthetic_gate_ready", "promotion", "protocol_frozen", "gate_changed",
                    "dataset_labels_metrics_scoring_changed"):
            self.assertIs(c[key], False)
        self.assertFalse(c["next_runtime_design"]["executed"])
        self.assertFalse(c["external_gate"]["executed"])
        adapter = PendingPaliGemmaAdapter()
        for task, expected in ((Task.CLASSIFICATION, ParseStatus.INVALID),
                               (Task.GROUNDING, ParseStatus.UNSUPPORTED)):
            result = adapter.adapt(b"contract-only", task)
            self.assertEqual(result.parse_status, expected)
            self.assertIsNone(result.value)

    def test_protected_authorities_runners_and_gate_assets_match_exact_base(self):
        # Read-only comparisons. No gate evaluation, image decode, model construction,
        # provisioning, or benchmark data access. Existing config/metrics cannot drift.
        roots = ["safeshift", "schemas", "configs/pre_freeze", "tests/fixtures/pre_freeze/frozen_external_gate",
                 "scripts/generate_external_gate_cases.py", "scripts/w2_qwen3_external_gate.py",
                 "scripts/w2_qwen2_5_external_gate.py", "scripts/w2_moondream_external_gate.py"]
        paths = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", BASE, "--", *roots], cwd=ROOT, text=True).splitlines()
        self.assertGreater(len(paths), 50)
        for path in paths:
            with self.subTest(path=path):
                original = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)
                current = (ROOT / path).read_bytes()
                if not path.endswith(".png"):
                    original, current = original.replace(b"\r\n", b"\n"), current.replace(b"\r\n", b"\n")
                self.assertEqual(current, original)

    def test_every_pre_freeze_json_strictly_parses(self):
        paths = sorted(CONFIG.glob("*.json"))
        self.assertIn(CANDIDATE, paths)
        for path in paths:
            with self.subTest(path=path.name):
                self.assertIsInstance(strict_json(path.read_bytes()), dict)


if __name__ == "__main__":
    unittest.main()
