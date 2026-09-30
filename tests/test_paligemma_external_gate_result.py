"""Offline audit transcription checks; no model, parser or real gate replay."""

from collections import Counter
import hashlib
from pathlib import Path
import subprocess
import unittest

from safeshift.protocol.schema import strict_json


ROOT = Path(__file__).resolve().parents[1]
BASE = "0b5d5b77106920738569d3b80b982ed231f3b645"
RESULT = "configs/pre_freeze/paligemma_external_gate_result.v1.json"
ROSTER = "configs/pre_freeze/local_models.d9.json"
NATIVE = {
    "A_2": "<loc0386><loc0639><loc0639><loc0895> red square ; <loc0384><loc0134><loc0634><loc0390> red square<eos>",
    "C_2": "<loc0634><loc0641><loc0895><loc0895> yellow triangle ; <loc0124><loc0128><loc0382><loc0384> yellow triangle<eos>",
}


def load(path):
    return strict_json((ROOT / path).read_bytes())


class PaliGemmaExternalGateResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = load(RESULT)
        # The merged D9R14 resolution remains historical, including promotion NO.
        # D9R15's live roster design is asserted separately without altering it.
        cls.roster = strict_json(subprocess.check_output([
            "git", "show", "9948570820b5ed8a774b8e226b80e24055e705cf:" + ROSTER], cwd=ROOT))

    def test_exact_identity_and_research_lead_audit(self):
        r = self.result
        self.assertEqual(r["record_kind"], "RESEARCH_LEAD_AUDITED_REAL_GATE_RESULT")
        self.assertEqual(r["model_id"], "google/paligemma-3b-mix-448")
        self.assertEqual(r["model_revision"], "ead2d9a35598cb89119af004f5d023b311d1c4a1")
        self.assertEqual(r["recording_base_sha"], BASE)
        self.assertEqual(r["execution_commit"], "bcc7b7be62891c887e9509dd39688d686a1b6020")
        self.assertEqual(r["bundle_name"], "d9r13_result_bundle.zip")
        self.assertEqual(r["bundle_sha256"], "68271facab4e9b272eb4cf5b19e0a5e0c5767e5b008bdfe09ae0ae43c8332ecd")
        source = r["source"]
        self.assertEqual(source["bundle_inspected_and_rehashed_by"], "RESEARCH_LEAD")
        self.assertIn("did not independently inspect or rehash", source["recording_basis"])
        self.assertEqual(source["checksums_file"], "checksums.json")
        self.assertEqual((source["artifact_count"], source["sha256_and_size_matches"]), (87, 87))
        self.assertIs(source["bundle_and_raw_bytes_committed"], False)

    def test_frozen_authority_hashes_and_mapping(self):
        r = self.result
        for name, expected in (
            ("gate_plan", "c3b5fb2a1df79f3476e3775fccefbe2f767edab453ba2a238742c4c5f89d4387"),
            ("manifest", "fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379"),
            ("provenance", "0b16be7408784c35bc3dc1a541f008b8086c4fa250957082a236d71ed3fe2e96"),
        ):
            with self.subTest(authority=name):
                self.assertEqual(r[name + "_sha256"], expected)
                self.assertEqual(hashlib.sha256((ROOT / r[name + "_path"]).read_bytes()).hexdigest(), expected)
        self.assertEqual(r["parser_boundary"], {
            "native_order": ["y_min", "x_min", "y_max", "x_max"],
            "native_coordinate_range": [0, 1023],
            "canonical_mapping": "[x_min/1024.0,y_min/1024.0,x_max/1024.0,y_max/1024.0]",
            "clamp": False, "repair": False, "select_first_box": False,
            "drop_extra_detections": False,
        })
        plan = load(r["gate_plan_path"])
        self.assertEqual(plan["canonical_mapping"], r["parser_boundary"]["canonical_mapping"])

    def test_exact_eight_case_outcomes_and_counts(self):
        r = self.result
        expected = [(case, "SCHEMA_ERROR" if case in NATIVE else "SUCCESS")
                    for case in ("A_1", "A_2", "B_1", "B_2", "C_1", "C_2", "D_1", "D_2")]
        self.assertEqual([(c["case_id"], c["parse_status"]) for c in r["cases"]], expected)
        self.assertEqual(Counter(c["parse_status"] for c in r["cases"]),
                         {"SUCCESS": 6, "SCHEMA_ERROR": 2})
        self.assertEqual((r["strict_success_count"], r["canonical_parsed_bbox_count"],
                          r["schema_error_count"]), (6, 6, 2))

    def test_multidetection_evidence_is_exact_and_unrepaired(self):
        for case in self.result["cases"]:
            if case["case_id"] in NATIVE:
                self.assertEqual(case["native_output"], NATIVE[case["case_id"]])
                self.assertEqual(case["detection_count"], 2)
                self.assertEqual(case["parser_outcome"], "PARSER_FAIL_NO_REPAIR")
                self.assertEqual(case["failure_kind"], "MODEL_OUTPUT_SCHEMA_FAILURE_NOT_RUNTIME_ERROR")
                self.assertIsNone(case["parsed_bbox"])

    def test_diagnostics_do_not_invent_boxes_thresholds_or_zero_ious(self):
        r = self.result
        self.assertEqual(r["success_iou_diagnostic_range"], {
            "minimum_approx": 0.921, "maximum_approx": 0.977,
            "scope": "SIX_SUCCESS_CASES_ONLY",
        })
        self.assertEqual(r["iou_usage"], "DIAGNOSTIC_ONLY")
        self.assertIsNone(r["iou_threshold"])
        self.assertIs(r["artificial_zero_iou"], False)
        for case in r["cases"]:
            self.assertNotIn("target_iou_diagnostic", case)
            self.assertNotIn("raw_sha256", case)
            if case["parse_status"] == "SUCCESS":
                self.assertEqual(set(case), {"case_id", "parse_status"})
        self.assertIn("not reconstructed or invented", r["evidence_limits"])

    def test_completed_runtime_and_gate_failure(self):
        r = self.result
        self.assertEqual(r["runtime"], {
            "accelerator": "Tesla T4", "accelerator_count": 1, "model_load_count": 1,
            "native_generate_calls": 8, "classification_calls": 0,
            "internet": "OFF", "raw_before_parser": "VERIFIED",
        })
        self.assertEqual(r["execution_status"], "COMPLETED")
        self.assertEqual(r["status"], "GATE_FAIL")
        self.assertEqual(r["automatic_gate_status"], "FAIL")
        self.assertIs(r["systematic_tracking"], False)
        self.assertEqual(r["gate_errors"], ["predictions do not track systematic target positions"])

    def test_exact_resolution_without_rerun_review_or_promotion(self):
        r = self.result
        for key, expected in {
            "paligemma_external_gate_status": "FAIL", "grounding_qualification": "FAIL",
            "rerun_required": "NO", "human_giant_box_review_required_for_decision": "NO",
            "paligemma_promotion": "NO", "classification_interface_status": "PENDING_QUALIFICATION",
            "giant_box_review_status": "NOT_REQUIRED_AFTER_AUTOMATIC_GATE_FAILURE",
            "giant_box_reviews": [], "paligemma_role": "BACKUP_1", "primary_roster_count": 4,
        }.items():
            self.assertEqual(r[key], expected)
        self.assertIs(r["exploratory_grounding_participation"], False)
        self.assertEqual(r["recording_task_execution"], dict.fromkeys((
            "model_rerun", "gpu", "gate_rerun", "inspecsafe", "human_giant_box_review",
            "output_repair", "token_budget_increase", "protocol_change"), False))
        self.assertEqual(r["inspecsafe_status"], "NOT_RUN")
        self.assertIs(r["inspecsafe_inference_authorized"], False)
        self.assertEqual(r["protocol_freeze_commit_sha"], "PENDING")
        self.assertIs(r["protocol_freeze_blocked"], True)

    def test_roster_changes_are_only_result_fields_and_preserve_policy(self):
        before = strict_json(subprocess.check_output(["git", "show", BASE + ":" + ROSTER], cwd=ROOT))
        expected = before["backups_in_order"][0]
        expected.update(
            external_gate_status="FAIL", external_gate_evidence=RESULT,
            grounding_qualification="FAIL", classification_interface_status="PENDING_QUALIFICATION",
            paligemma_promotion="NO", rerun_required="NO",
            human_giant_box_review_required_for_decision="NO", artificial_zero_iou=False,
        )
        self.assertEqual(self.roster, before)
        self.assertEqual(len(self.roster["primary_models"]), 4)
        self.assertEqual(expected["role"], "BACKUP_1")
        self.assertEqual(expected["model_id"], self.result["model_id"])
        self.assertEqual(expected["immutable_revision"], self.result["model_revision"])
        self.assertEqual(load(expected["external_gate_evidence"]), self.result)

    def test_d9r11_negative_finding_is_preserved(self):
        negative = self.result["negative_evidence"]
        self.assertEqual(negative["case_id"], "grd_d")
        self.assertIn("target-absent case hallucinated a parseable red-square detection", negative["finding"])
        self.assertEqual(negative["sha256"], "555701224f8b745391c65e75c5ff876bc039648fa1f4da02bc96403a3112e736")
        self.assertEqual(hashlib.sha256((ROOT / negative["path"]).read_bytes()).hexdigest(), negative["sha256"])

    def test_production_code_fixtures_and_historical_contracts_unchanged(self):
        protected = ["safeshift", "scripts", "notebooks", "prompts", "schemas",
                     "tests/fixtures", "configs/pre_freeze"]
        changed = subprocess.check_output(
            ["git", "diff", "--name-only", BASE, "--", *protected], cwd=ROOT,
            text=True).splitlines()
        # Only current roster/template policy may change after D9R14.
        # D9R15 tests additionally pin RESULT and all evidence against its BASE.
        self.assertLessEqual(set(changed), {ROSTER, RESULT,
                                          "configs/pre_freeze/freeze_manifest.d9.template.json"})


if __name__ == "__main__":
    unittest.main()
