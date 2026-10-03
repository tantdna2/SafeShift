"""D9R18 decision boundaries, live overlays and immutable historical bytes; offline only."""

import copy
from functools import lru_cache
from pathlib import Path
import subprocess
import unittest

from safeshift.protocol.schema import strict_json

ROOT = Path(__file__).resolve().parents[1]
BASE = "93e1004de311588e94356e19edf53220de13e194"
D9R18_MERGED = "5538064e6ea015f8c15475d488064cae95461cd0"
ART = "configs/pre_freeze/d9r18_final_participation_decision.v1.json"
ROSTER = "configs/pre_freeze/local_models.d9.json"
FREEZE = "configs/pre_freeze/freeze_manifest.d9.template.json"
A = "configs/pre_freeze/qwen2_5_classification_qualification_result.v1.json"
BE = "configs/pre_freeze/d9r17b_e_classification_qualification_results.v1.json"
PLAN = "configs/pre_freeze/classification_qualification_plan.v1.json"
CASES = "configs/pre_freeze/classification_qualification_cases.v1.json"
NOTE = "notes/w2_d9r18_final_participation_decision.md"
MATRIX = "notes/w2_d9_freeze_readiness_reconciliation.md"
ROLE_STATE = "ROLE_DECISION_COMPLETE_ADAPTER_QUALIFICATION_PENDING"
IDS = ["Qwen/Qwen3-VL-8B-Instruct", "Qwen/Qwen2.5-VL-3B-Instruct",
       "OpenGVLab/InternVL3-2B-hf", "vikhyatk/moondream2", "google/paligemma-3b-mix-448"]
ALLOWED = {ART, ROSTER, FREEZE, NOTE, MATRIX, "DECISIONS.md", "TASKS.md",
           "tests/test_d9r18_final_participation_decision.py",
           "tests/test_d9r17b_e_classification_qualification_results.py",
           "tests/test_qwen2_5_classification_qualification_result.py",
           "tests/test_d9r15_five_model_roster_exploratory_grounding.py",
           "tests/test_d9_t4_roster_revision.py", "tests/test_model_provenance.py",
           "tests/test_qwen3_external_gate_result.py", "tests/test_qwen2_5_external_gate_result.py",
           "tests/test_classification_qualification.py"}


def load(path):
    return strict_json((ROOT / path).read_bytes())


def milestone(path):
    """D9R18-only implementation assertions; D9R19 guards the live delta separately."""
    return strict_json(subprocess.check_output(["git", "show", f"{D9R18_MERGED}:{path}"], cwd=ROOT))


@lru_cache(None)
def base_bytes(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)


def checkout_base_bytes(path):
    # Apply Git's configured checkout representation, not ad-hoc normalization.
    return subprocess.check_output(["git", "cat-file", "--filters", f"{BASE}:{path}"], cwd=ROOT)


class FinalParticipationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = load(ART)
        cls.models = cls.decision["models"]

    def test_authority_and_review_overlay(self):
        d = self.decision
        self.assertEqual(d["base_sha"], BASE)
        self.assertEqual(d["authority"], "RESEARCH_LEAD")
        self.assertEqual(d["task"], "W2.6-D9R18-FINAL-PARTICIPATION-AND-ROLES")
        self.assertEqual(d["decision_date"], "2026-10-02")
        self.assertEqual(d["review_status"], "RESEARCH_LEAD_DECISION_RECORDED")
        self.assertIn("PENDING_REVIEW", d["supersession_scope"])
        self.assertEqual(load(A)["review_status"], "PENDING_REVIEW")
        self.assertTrue(all(r["review_status"] == "PENDING_REVIEW" for r in load(BE)["runs"].values()))

    def test_exact_four_classification_participants_in_all_current_views(self):
        self.assertEqual(self.decision["classification_participant_count"], 4)
        for models in (self.models, load(ROSTER)["primary_models"], load(FREEZE)["primary_models"]):
            self.assertEqual([m["model_id"] for m in models], IDS)
            self.assertEqual([m["classification_participation"] for m in models],
                             ["PARTICIPATING"] * 4 + ["NOT_PARTICIPATING"])

    def test_qualification_references_revisions_verdicts_and_counts_match_evidence(self):
        for model, key, exact in zip(self.models, ("qwen3", "qwen2_5", "internvl3", "moondream", "paligemma"), (8, 3, 6, 2, 0)):
            with self.subTest(model=key):
                expected_ref = A if key == "qwen2_5" else BE + "#/runs/" + key
                self.assertEqual(model["qualification_result_reference"], expected_ref)
                run = load(A) if key == "qwen2_5" else load(BE)["runs"][key]
                for field in ("model_id", "immutable_revision"):
                    self.assertEqual(model[field], run[field])
                self.assertEqual(model["classification_qualification_verdict"], run["run_status"])
                self.assertEqual(model["classification_qualification_causes"], run["causes"])
                self.assertEqual(model["exact_expected_count"], exact)
                for field in ("parse_success_count", "exact_expected_count", "total_cases"):
                    self.assertEqual(model[field], run["summary"][field])

    def test_semantic_failure_is_not_a_performance_filter(self):
        self.assertIs(self.decision["semantic_qualification_used_as_performance_filter"], False)
        for model in self.models[1:4]:
            self.assertEqual(model["classification_qualification_verdict"], "FAIL")
            self.assertEqual(model["classification_qualification_causes"], ["SEMANTIC_CLASSIFICATION_FAILURE"])
            self.assertEqual(model["parse_success_count"], 8)
            self.assertEqual(model["classification_participation"], "PARTICIPATING")
            self.assertIn("not a performance filter", model["decision_reason"])

    def test_paligemma_interface_blocker_not_reinterpreted(self):
        model = self.models[-1]
        self.assertEqual(model["classification_qualification_causes"], ["INTERFACE_OR_FORMAT_FAILURE"])
        self.assertEqual(model["parse_success_count"], 0)
        self.assertEqual(model["classification_participation"], "NOT_PARTICIPATING")
        cases = load(BE)["runs"]["paligemma"]["cases"]
        self.assertEqual(len(cases), 8)
        self.assertTrue(all(c["parse_status"] == "INVALID" and c["observed_canonical"] is None for c in cases))

    def test_five_primary_members_unchanged(self):
        self.assertEqual(self.decision["primary_research_roster_count"], 5)
        self.assertIs(self.decision["roster_membership_changed"], False)
        self.assertTrue(all(m["roster_membership"] == "PRIMARY_RESEARCH_ROSTER_MEMBER" for m in self.models))
        for path in (ROSTER, FREEZE):
            old, new = strict_json(base_bytes(path)), load(path)
            for field in ("model_id", "immutable_revision", "role"):
                self.assertEqual([m[field] for m in old["primary_models"]], [m[field] for m in new["primary_models"]])
            self.assertEqual(new["primary_models"][-1]["role"], "PRIMARY_5")

    def test_smolvlm_inactive_and_replacement_policy_unchanged(self):
        for path in (ROSTER, FREEZE):
            backups = load(path)["backups_in_order"]
            self.assertEqual(backups, strict_json(base_bytes(path))["backups_in_order"])
            self.assertEqual([b["model_id"] for b in backups], ["HuggingFaceTB/SmolVLM2-2.2B-Instruct"])
            self.assertIs(backups[0]["activated"], False)
        self.assertEqual(load(ROSTER)["replacement_policy"], strict_json(base_bytes(ROSTER))["replacement_policy"])
        self.assertIs(self.decision["backup_decision"]["activated"], False)
        self.assertIn("NO_ACTIVATION_IN_D9R18_ONLY", self.decision["backup_decision"]["scope"])

    def test_d9r18_primary_grounding_and_production_adapters_unchanged(self):
        expected = ["NOT_PARTICIPATING"] * 3 + ["GATE_ELIGIBLE_PRODUCTION_ADAPTER_PENDING", "NOT_PARTICIPATING"]
        self.assertEqual([m["primary_grounding_participation"] for m in self.models], expected)
        for path in (ROSTER, FREEZE):
            for old, new in zip(strict_json(base_bytes(path))["primary_models"], milestone(path)["primary_models"]):
                for field in old:
                    if "grounding" in field or "gate" in field or field.startswith("production_adapter"):
                        self.assertEqual(new[field], old[field], (path, field))
        moon = milestone(ROSTER)["primary_models"][3]
        self.assertEqual(moon["external_gate_status"], "PASS")
        self.assertEqual(moon["production_adapter_status"], "NOT_QUALIFIED")

    def test_exact_exploratory_roles_and_no_override(self):
        expected = ["INCLUDED", "EXCLUDED", "EXCLUDED", "INCLUDED", "INCLUDED"]
        for models in (self.models, load(ROSTER)["primary_models"], load(FREEZE)["primary_models"]):
            self.assertEqual([m["exploratory_grounding_participation"] for m in models], expected)
        for path in (ROSTER, FREEZE):
            self.assertEqual(load(path)["exploratory_grounding_track"], strict_json(base_bytes(path))["exploratory_grounding_track"])
        self.assertIs(self.decision["exploratory_qualification_override"], False)

    def test_d9r17_results_byte_identical(self):
        for path in (A, BE):
            # Preserve both exact BASE checkout bytes (CRLF on this Windows
            # checkout) and the repository blob; never rewrite result files.
            self.assertEqual((ROOT / path).read_bytes(), checkout_base_bytes(path), path)
            actual = subprocess.check_output(["git", "hash-object", "--path=" + path, path], cwd=ROOT)
            expected = subprocess.check_output(["git", "rev-parse", f"{BASE}:{path}"], cwd=ROOT)
            self.assertEqual(actual, expected, path)

    def test_d9r16_plan_cases_and_fixtures_byte_identical(self):
        paths = [PLAN, CASES] + subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", BASE, "tests/fixtures/pre_freeze/classification_qualification_v1"],
            cwd=ROOT, text=True).splitlines()
        self.assertEqual(len(paths), 10)
        for path in paths:
            self.assertEqual((ROOT / path).read_bytes(), base_bytes(path), path)

    def test_d9r18_only_explicit_decision_documentation_and_test_files_change(self):
        changed = subprocess.check_output(["git", "diff", "--name-only", BASE, D9R18_MERGED], cwd=ROOT, text=True).splitlines()
        self.assertLessEqual(set(changed), ALLOWED)
        # Covers the exact D9R18 milestone; D9R19 is authorized to implement code.
        self.assertFalse(any(p.startswith(("safeshift/", "scripts/", "prompts/", "schemas/", "notebooks/", "data/")) for p in changed))

    def test_freeze_and_inspecsafe_remain_pending_unauthorized(self):
        for doc in (self.decision, load(ROSTER), load(FREEZE)):
            self.assertEqual(doc["protocol_freeze_commit_sha"], "PENDING")
            self.assertIs(doc["inspecsafe_inference_authorized"], False)
        self.assertEqual(self.decision["protocol_freeze"], "PENDING")
        self.assertIs(self.decision["NOT_INSPECSAFE"], True)
        self.assertEqual(self.decision["inspecsafe_status"], "NOT_RUN")
        self.assertTrue(all(v == "PENDING" for v in load(FREEZE)["frozen_components"].values()))

    def test_no_execution_rerun_repair_removal_or_activation(self):
        for field in ("model_rerun", "model_execution", "prompt_repair", "parser_repair", "backup_activated"):
            self.assertIs(self.decision[field], False)
        for model in self.models:
            for field in ("model_rerun", "prompt_repair", "parser_repair", "roster_removed", "backup_activated"):
                self.assertIs(model[field], False)

    def test_decisions_tasks_append_only_and_reconcile_pending_review(self):
        for path in ("DECISIONS.md", "TASKS.md"):
            before, after = checkout_base_bytes(path), (ROOT / path).read_bytes()
            self.assertTrue(after.startswith(before), path)
            appended = after[len(before):].decode("utf-8")
            for text in ("D9R18", "PENDING_REVIEW", "NOT_PARTICIPATING", "semantic FAIL", "SmolVLM2", "unauthorized", "PENDING"):
                self.assertIn(text, appended)

    def test_checklist_retains_adapter_dependency(self):
        expected = strict_json(base_bytes(ROSTER))["d9_checklist"]
        expected["6_final_model_roles_and_backup_substitutions"] = ROLE_STATE
        self.assertEqual(load(ROSTER)["d9_checklist"], expected)
        self.assertEqual(self.decision["d9_checklist"], expected)
        self.assertIn("#4", self.decision["final_roles_remaining_blocker"])
        self.assertIn(ROLE_STATE, (ROOT / MATRIX).read_text(encoding="utf-8"))

    def test_d9r18_overlays_have_only_exact_authorized_semantic_delta(self):
        for path in (ROSTER, FREEZE):
            expected = copy.deepcopy(strict_json(base_bytes(path)))
            expected["final_participation_decision"] = ART
            expected["classification_state_semantics"] = self.decision["legacy_field_semantics"]
            self.assertIn("not current participation or qualification", expected["classification_state_semantics"])
            for old, model in zip(expected["primary_models"], self.models):
                for field in ("classification_participation", "classification_qualification_verdict", "qualification_result_reference"):
                    old[field] = model[field]
            if path == ROSTER:
                expected["d9_checklist"]["6_final_model_roles_and_backup_substitutions"] = ROLE_STATE
                expected["final_roles_remaining_blocker"] = self.decision["final_roles_remaining_blocker"]
            else:
                expected["current_status_overlay"]["task"] = self.decision["task"]
                expected["current_status_overlay"]["semantics"] = (
                    "D9R18 final classification participation: four participants; PaliGemma excluded for interface/format failure, five-member roster unchanged. Grounding/exploratory roles unchanged. Role decision complete; production adapter qualification (#4), implementation and protocol freeze pending.")
            self.assertEqual(milestone(path), expected, path)


if __name__ == "__main__":
    unittest.main()
