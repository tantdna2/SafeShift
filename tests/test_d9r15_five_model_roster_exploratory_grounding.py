"""D9R15 governance and immutable execution boundaries; no model/data execution."""

import hashlib
from pathlib import Path
import subprocess
import unittest

from safeshift.protocol.schema import strict_json


ROOT = Path(__file__).resolve().parents[1]
BASE = "9948570820b5ed8a774b8e226b80e24055e705cf"
D9R15_MERGED = "ecab4cfa6fd844fbada232975ed4494ea719a90b"
ROSTER = "configs/pre_freeze/local_models.d9.json"
FREEZE = "configs/pre_freeze/freeze_manifest.d9.template.json"
PROVENANCE = "configs/pre_freeze/local_model_provenance.d9.json"
IDS = [
    "Qwen/Qwen3-VL-8B-Instruct",
    "Qwen/Qwen2.5-VL-3B-Instruct",
    "OpenGVLab/InternVL3-2B-hf",
    "vikhyatk/moondream2",
    "google/paligemma-3b-mix-448",
]
EXPLORATORY = {IDS[0], IDS[3], IDS[4]}


def load(path):
    return strict_json((ROOT / path).read_bytes())


def baseline(path):
    return subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT)


class D9R15RosterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = load(ROSTER)
        cls.freeze = load(FREEZE)
        cls.models = {m["model_id"]: m for m in cls.roster["primary_models"]}
        cls.track = cls.roster["exploratory_grounding_track"]

    def test_exact_five_candidates_and_unique_active_membership(self):
        for config in (self.roster, self.freeze):
            self.assertEqual([m["model_id"] for m in config["primary_models"]], IDS)
            active = config["primary_models"] + config["backups_in_order"]
            self.assertEqual(len(active), 6)
            self.assertEqual(len({m["model_id"] for m in active}), 6)
            self.assertEqual([m["model_id"] for m in active].count(IDS[4]), 1)
        self.assertTrue(all(m["classification"] == "CANDIDATE" for m in self.models.values()))
        self.assertTrue(all(m["classification_role"] == "PENDING_FINAL_GATE"
                            for m in self.freeze["primary_models"]))
        self.assertEqual(self.models[IDS[4]]["role"], "PRIMARY_5")
        self.assertEqual(self.models[IDS[4]]["research_role"], "INDEPENDENT_GOOGLE_PALIGEMMA_CONTRAST")

    def test_backup_is_smolvlm_only_and_not_activated(self):
        expected = ["HuggingFaceTB/SmolVLM2-2.2B-Instruct"]
        self.assertEqual(self.freeze["backup_order"], expected)
        for config in (self.roster, self.freeze):
            self.assertEqual([m["model_id"] for m in config["backups_in_order"]], expected)
            backup = config["backups_in_order"][0]
            self.assertEqual(backup["replacement_status"], "BACKUP_1_ONLY")
            self.assertIs(backup["activated"], False)
        self.assertEqual(self.models[IDS[4]]["historical_role"], "BACKUP_1")
        self.assertIs(self.models[IDS[4]]["backup_substitution"], False)

    def test_gate_verdicts_and_primary_participation_are_not_rescued(self):
        expected_gates = ["GATE_FAIL", "GATE_FAIL", "NOT_RUN", "PASS", "FAIL"]
        for model_id, gate in zip(IDS, expected_gates):
            m = self.models[model_id]
            self.assertEqual(m["external_gate_status"], gate)
            expected = "GATE_ELIGIBLE_PRODUCTION_ADAPTER_PENDING" if model_id == IDS[3] else "NOT_PARTICIPATING"
            self.assertEqual(m["primary_grounding_participation"], expected)
            if model_id != IDS[3]:
                self.assertEqual(m["grounding"], "NOT_PARTICIPATING")
        for model_id in (IDS[0], IDS[4]):
            self.assertEqual(self.models[model_id]["grounding_failure_reason"], "SPATIAL_GATE_FAILURE")
        self.assertEqual(self.models[IDS[2]]["grounding_failure_reason"], "NO_DOCUMENTED_GENERIC_SPATIAL_INTERFACE")
        self.assertEqual(self.models[IDS[4]]["grounding_qualification"], "FAIL")
        moon = self.models[IDS[3]]
        self.assertEqual(moon["grounding"], "PASS")
        # D9R19 implements classification only; the PASS gate still cannot
        # authorize/promote a production Call-2 grounding adapter.
        self.assertEqual(moon["production_adapter_grounding"], "UNSUPPORTED")
        self.assertEqual(moon["production_adapter_status"], "CLASSIFICATION_IMPLEMENTED_GROUNDING_NOT_QUALIFIED")
        self.assertEqual(moon["historical_official_smoke"],
                         strict_json(baseline(ROSTER))["primary_models"][3]["historical_official_smoke"])

    def test_exact_exploratory_membership_separate_from_primary_in_both_configs(self):
        for config in (self.roster, self.freeze):
            models = config["primary_models"]
            self.assertEqual({m["model_id"] for m in models
                              if m["exploratory_grounding_participation"] == "INCLUDED"}, EXPLORATORY)
            for m in models:
                self.assertEqual(m["exploratory_grounding_participation"],
                                 "INCLUDED" if m["model_id"] in EXPLORATORY else "EXCLUDED")
                self.assertEqual(m["primary_grounding_participation"],
                                 self.models[m["model_id"]]["primary_grounding_participation"])
        self.assertEqual(set(self.track["included_model_keys"]),
                         {self.models[mid]["key"] for mid in EXPLORATORY})
        self.assertEqual(set(self.track["excluded_model_keys"]),
                         {self.models[mid]["key"] for mid in (IDS[1], IDS[2])})
        self.assertEqual(self.freeze["exploratory_grounding_track"]["policy_ref"],
                         ROSTER + "#exploratory_grounding_track")

    def test_exploratory_cannot_override_gate_qualify_promote_or_tune(self):
        self.assertEqual(self.track["analysis_level"], "SECONDARY_EXPLORATORY")
        for field in ("override_gate_or_qualification", "implies_primary_rq3_participation",
                      "model_rescue", "lower_gate_or_change_threshold", "gate_rerun",
                      "output_repair", "use_results_to_promote_model",
                      "use_results_to_change_roster_after_inspecsafe",
                      "use_results_to_tune_prompt_parser_threshold", "execution_authorized"):
            self.assertIs(self.track[field], False, field)
        self.assertIs(self.track["report_separately_from_primary_rq3"], True)
        self.assertIs(self.track["separate_implementation_and_freeze_before_inspecsafe_required"], True)
        self.assertEqual(self.track["status"], "POLICY_APPROVED_IMPLEMENTATION_AND_FREEZE_PENDING")

    def test_d5_policy_and_zero_boundaries(self):
        self.assertEqual(self.track["d5_metric_definitions"], "UNCHANGED")
        self.assertEqual(self.track["future_metric_formulas"], "MAY_REUSE_D5_AFTER_SEPARATE_IMPLEMENTATION_AND_FREEZE")
        self.assertEqual(self.track["future_end_to_end_failure_policy"], "FOLLOW_EXISTING_D5_POLICY")
        for field in ("primary_nonparticipants_receive_synthetic_zero", "external_gate_artificial_zero_iou"):
            self.assertIs(self.track[field], False)
        before = strict_json(baseline(ROSTER))
        for field in ("preserved_protocol", "replacement_policy", "point_only_policy"):
            self.assertEqual(self.roster[field], before[field])

    def test_paligemma_runtime_evidence_reconciled_without_classification_qualification(self):
        m = self.models[IDS[4]]
        runtime = load(m["runtime_evidence"])
        self.assertEqual(runtime["model_id"], m["model_id"])
        self.assertEqual(runtime["immutable_revision"], m["immutable_revision"])
        self.assertEqual(runtime["real_runtime_status"], "RUNTIME_SMOKE_PASS")
        self.assertEqual(m["real_runtime_status"], runtime["real_runtime_status"])
        self.assertIs(runtime["exact_runtime_verified"], True)
        self.assertIs(m["exact_runtime_verified"], True)
        self.assertEqual((runtime["hardware"]["gpu_name"], runtime["hardware"]["visible_gpu_count"]), ("Tesla T4", 1))
        self.assertEqual(m["offline_runner_status"], "COMPLETE")
        for field in ("runtime_smoke_status", "resource_status"):
            self.assertEqual(m[field], "PASS_VALIDATED")
        self.assertEqual(m["classification_interface_status"], "PENDING_QUALIFICATION")
        self.assertEqual(m["production_adapter_status"], "NOT_QUALIFIED")
        for field in ("production_adapter_classification", "production_adapter_grounding"):
            self.assertEqual(m[field], runtime[field])

    def test_history_retains_failed_cases_no_promotion_and_hallucination(self):
        pali = load(self.models[IDS[4]]["external_gate_evidence"])
        self.assertEqual(pali["paligemma_promotion"], "NO")
        self.assertEqual(pali["paligemma_role"], "BACKUP_1")
        self.assertEqual(pali["primary_roster_count"], 4)
        self.assertIs(pali["exploratory_grounding_participation"], False)
        self.assertEqual(pali["strict_success_count"], 6)
        self.assertEqual([c["case_id"] for c in pali["cases"] if c["parse_status"] == "SCHEMA_ERROR"], ["A_2", "C_2"])
        self.assertEqual(pali["rerun_required"], "NO")
        self.assertIs(pali["parser_boundary"]["repair"], False)
        qwen = load(self.models[IDS[0]]["external_gate_evidence"])
        self.assertEqual(sum(c["parse_status"] == "SUCCESS" for c in qwen["cases"]), 5)
        negative = load(pali["negative_evidence"]["path"])["research_lead_interpretation"]["grounding_negative"]
        self.assertEqual(negative["semantics"], "SEMANTIC_HALLUCINATION_TARGET_SELECTIVITY_FAILURE")
        self.assertIs(negative["target_present"], False)
        self.assertIs(negative["semantic_repair"], False)

    def test_pre_inspecsafe_expansion_and_freeze_stays_pending(self):
        for config in (self.roster, self.freeze):
            self.assertEqual(config["protocol_freeze_commit_sha"], "PENDING")
            self.assertIs(config["inspecsafe_inference_authorized"], False)
            self.assertIs(config["inspecsafe_performance_used"], False)
            self.assertIs(config["roster_revision_before_protocol_freeze"], True)
            self.assertIs(config["roster_revision_before_inspecsafe"], True)
            link = config["primary_expansion_precommit"]
            self.assertEqual(link["status"], "ROSTER_EXPANSION_APPROVED_D9R15")
            self.assertEqual(link["resolution_decision"], "D9R15")
            self.assertIs(link["qualification_promotion"], False)
            self.assertIs(link["automatic_promotion"], False)
            self.assertIs(link["historical_promotion_contract_superseded_for_roster_membership_only"], True)
        self.assertTrue(all(v == "PENDING" for v in self.freeze["frozen_components"].values()))
        # D9R15 role dependency before the D9R18 participation decision.
        historical = strict_json(subprocess.check_output(["git", "show", f"{D9R15_MERGED}:{ROSTER}"], cwd=ROOT))
        self.assertEqual(historical["d9_checklist"]["6_final_model_roles_and_backup_substitutions"], "PENDING")

    def test_live_provenance_membership_and_only_authorized_overlay_changes(self):
        current = load(PROVENANCE)
        before = strict_json(baseline(PROVENANCE))
        revision = current["roster_revision"]
        expected = before["roster_revision"].copy()
        expected.update(
            roster_revision="D9R15_FIVE_MODEL_ROSTER_AND_EXPLORATORY_GROUNDING",
            roster_revision_reason="PRE_FREEZE_ROSTER_EXPANSION_D9R6_SOLE_PRIMARY_5_CANDIDATE",
            task="W2.6-D9R15-FIVE-MODEL-ROSTER-AND-EXPLORATORY-GROUNDING",
            base_main_sha=BASE,
            active_primary_keys=[m["key"] for m in self.roster["primary_models"]],
            active_backup_keys=[m["key"] for m in self.roster["backups_in_order"]],
            historical_record_semantics=(
                "All model/source documentary records, including their historical roster_group/order, "
                "runtime/license facts and unresolved items, remain historical evidence. Current D9R15 "
                "membership is exclusively these current active key lists and local_models.d9.json, "
                "which must agree. Historical documentary runtime wording is not the later smoke status."),
        )
        self.assertEqual(revision, expected)  # Also protects retired_keys and all other overlay fields.
        before["roster_revision"] = expected
        self.assertEqual(current, before)  # All model/source and top-level documentary facts preserved.
        marker = b'  "roster_revision": {'
        self.assertEqual((ROOT / PROVENANCE).read_bytes().replace(b"\r\n", b"\n").rsplit(marker, 1)[0],
                         baseline(PROVENANCE).replace(b"\r\n", b"\n").rsplit(marker, 1)[0])

    def test_giant_review_resolved_per_model_without_new_review(self):
        for config, field in ((self.roster, "synthetic_gate"), (self.freeze, "synthetic_external_gate")):
            self.assertEqual(config[field]["status"], "RESOLVED_CAPABILITY_AWARE")
            self.assertEqual(config[field]["qualitative_giant_box_review_procedure"],
                             "RESOLVED_PER_MODEL_SEE_MODEL_EVIDENCE")
        for model_id in (IDS[0], IDS[1], IDS[4]):
            result = load(self.models[model_id]["external_gate_evidence"])
            self.assertEqual(result["giant_box_review_status"], "NOT_REQUIRED_AFTER_AUTOMATIC_GATE_FAILURE")
            self.assertEqual(result["giant_box_reviews"], [])
        self.assertEqual(self.models[IDS[2]]["external_gate_status"], "NOT_RUN")
        moon = self.models[IDS[3]]
        self.assertEqual(moon["external_gate_status"], "PASS")
        note = (ROOT / moon["external_gate_evidence"].split("#", 1)[0]).read_text(encoding="utf-8")
        for case in ("A_1", "A_2", "B_1", "B_2", "C_1", "C_2", "D_1", "D_2"):
            self.assertIn(f"| `{case}` | `NO_GIANT` |", note)

    def test_execution_code_fixtures_and_all_historical_evidence_unchanged(self):
        # Historical D9R15 scope at its merged commit. D9R16 separately checks
        # live protected bytes and its only two authorized runner whitelist edits.
        protected = ["safeshift", "scripts", "notebooks", "prompts", "schemas",
                     "tests/fixtures", "configs", "notes/w2_qwen3_external_gate_result.md",
                     "notes/w2_paligemma_external_gate_result.md",
                     "notes/w2_paligemma_single_t4_runtime_qualification.md",
                     "notes/w2_metrics_statistics_decision_brief.md"]
        changed = subprocess.check_output(
            ["git", "diff", "--name-only", BASE, D9R15_MERGED, "--", *protected], cwd=ROOT, text=True).splitlines()
        self.assertLessEqual(set(changed), {ROSTER, FREEZE, PROVENANCE})
        # Compare the D9R14 Git content hash independently, including when staged.
        path = "configs/pre_freeze/paligemma_external_gate_result.v1.json"
        current = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
        original = baseline(path).replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(current).digest(), hashlib.sha256(original).digest())


if __name__ == "__main__":
    unittest.main()
