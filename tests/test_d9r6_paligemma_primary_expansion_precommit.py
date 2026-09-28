"""Static governance guards for the D9R6 PaliGemma expansion precommit."""

import hashlib
import json
import unittest
from pathlib import Path

from safeshift.protocol.schema import strict_json


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "pre_freeze"
RECORD_PATH = CONFIG / "paligemma_primary_expansion_precommit.v1.json"
MODEL_KEY = "paligemma_3b_mix_448"
MODEL_ID = "google/paligemma-3b-mix-448"
REVISION = "ead2d9a35598cb89119af004f5d023b311d1c4a1"
MANIFEST = "configs/pre_freeze/external_gate_cases.v1.json"
MANIFEST_SHA = "fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379"
EXPANSION_SCOPE = (
    "CURRENT_FOUR_PRIMARY_CANDIDATES_PLUS_PRESPECIFIED_PRIMARY_EXPANSION_CANDIDATE_"
    "AND_ANY_ACTIVATED_BACKUP"
)


def load(path):
    return strict_json(path.read_bytes())


class D9R6PaliGemmaExpansionPrecommitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = load(RECORD_PATH)
        cls.roster = load(CONFIG / "local_models.d9.json")
        cls.freeze = load(CONFIG / "freeze_manifest.d9.template.json")
        cls.provenance = load(CONFIG / "local_model_provenance.d9.json")

    def test_exact_candidate_identity_and_revision(self):
        candidate = self.record["candidate"]
        self.assertEqual(
            (candidate["key"], candidate["model_id"], candidate["immutable_revision"]),
            (MODEL_KEY, MODEL_ID, REVISION),
        )
        self.assertEqual(candidate["current_role"], "BACKUP_1")
        self.assertEqual(candidate["intended_role_if_qualified"], "PRIMARY_5")

    def test_primary_roster_and_backup_order_are_unchanged(self):
        self.assertEqual(len(self.roster["primary_models"]), 4)
        self.assertEqual(len(self.freeze["primary_models"]), 4)
        backup = self.roster["backups_in_order"][0]
        self.assertEqual((backup["key"], backup["model_id"], backup["role"]),
                         (MODEL_KEY, MODEL_ID, "BACKUP_1"))
        self.assertEqual(
            [(m["model_id"], m["immutable_revision"]) for m in self.roster["backups_in_order"]],
            [(m["model_id"], m["immutable_revision"]) for m in self.freeze["backups_in_order"]],
        )
        self.assertEqual(self.freeze["backup_order"][0], MODEL_ID)

    def test_precommit_pending_and_inspecsafe_freeze_guards(self):
        self.assertEqual(self.record["status"], "PENDING_QUALIFICATION")
        self.assertEqual(self.roster["primary_expansion_precommit"], {
            "status": "PENDING_QUALIFICATION",
            "candidate_key": MODEL_KEY,
            "record_path": "configs/pre_freeze/paligemma_primary_expansion_precommit.v1.json",
            "promotion_requires_separate_review_pr_audit": True,
            "automatic_promotion": False,
        })
        self.assertFalse(self.record["decision_timing"]["inspecsafe_performance_used"])
        for config in (self.roster, self.freeze):
            self.assertEqual(config["protocol_freeze_commit_sha"], "PENDING")
            self.assertIs(config["inspecsafe_inference_authorized"], False)
            self.assertIs(config["inspecsafe_performance_used"], False)

    def test_contract_does_not_record_runtime_or_grounding_pass(self):
        contract = self.record["qualification_contract"]
        self.assertEqual(contract["access_terms"]["status"], "GATED_USAGE_TERMS_ACCEPTANCE_REQUIRED")
        self.assertEqual(contract["real_single_t4_runtime"]["status"], "PENDING_QUALIFICATION")
        self.assertEqual(contract["classification_interface"]["status"], "PENDING_QUALIFICATION")
        self.assertEqual(contract["grounding_interface"]["status"], "PENDING_QUALIFICATION")
        self.assertEqual(contract["frozen_external_gate"]["status"], "PENDING_QUALIFICATION")
        grounding = contract["grounding_interface"]
        self.assertEqual(grounding["native_output_grammar_status"], "PENDING_DOCUMENTARY_VERIFICATION")
        self.assertEqual(grounding["candidate_native_output_grammar_to_verify"],
                         "<loc y_min><loc x_min><loc y_max><loc x_max>")
        self.assertTrue(grounding["deterministic_conversion_required"])
        self.assertEqual(grounding["deterministic_conversion_status"], "PENDING_QUALIFICATION")
        self.assertNotIn("native_output_grammar", grounding)
        statuses = []

        def collect(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == "status":
                        statuses.append(item)
                    collect(item)
            elif isinstance(value, list):
                for item in value:
                    collect(item)

        collect(self.record)
        self.assertNotIn("PASS", statuses)

    def test_grounding_candidate_aligns_with_unqualified_provenance(self):
        summary = self.record["selection_basis"]["summary"]
        self.assertIn("object-detection", summary)
        self.assertIn("PENDING_DOCUMENTARY_VERIFICATION", summary)
        self.assertIn("not an established fact", summary)
        spatial = next(m for m in self.provenance["models"] if m["key"] == MODEL_KEY)["spatial"]
        self.assertEqual(spatial["d5_box_qualification"], "NOT_YET_QUALIFIED")
        self.assertIn("object detection", spatial["documented_capability"].lower())
        self.assertIn("native coordinate grammar", spatial["documented_capability"].lower())
        self.assertIn("not established", spatial["documented_capability"].lower())

    def test_frozen_gate_manifest_and_scope_are_exact(self):
        self.assertEqual(self.record["qualification_contract"]["frozen_external_gate"]["manifest"], MANIFEST)
        self.assertEqual(self.record["qualification_contract"]["frozen_external_gate"]["manifest_sha256"], MANIFEST_SHA)
        self.assertTrue(self.record["qualification_contract"]["frozen_external_gate"]["cases_unchanged"])
        self.assertTrue(self.record["qualification_contract"]["frozen_external_gate"]["gate_semantics_unchanged"])
        self.assertEqual(self.roster["synthetic_gate"]["manifest"], MANIFEST)
        self.assertEqual(self.freeze["synthetic_external_gate"]["manifest"], MANIFEST)
        self.assertEqual(self.roster["synthetic_gate"]["manifest_sha256"], MANIFEST_SHA)
        self.assertEqual(self.freeze["synthetic_external_gate"]["manifest_sha256"], MANIFEST_SHA)
        self.assertEqual(self.roster["synthetic_gate"]["eligibility_review_scope"], EXPANSION_SCOPE)
        self.assertEqual(self.freeze["synthetic_external_gate"]["eligibility_review_scope"], EXPANSION_SCOPE)
        self.assertEqual(hashlib.sha256((ROOT / MANIFEST).read_bytes()).hexdigest(),
                         "fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379")

    def test_checklist_preserves_current_four_primary_resolution(self):
        self.assertEqual(self.roster["d9_checklist"], {
            "1_model_revisions_and_license_provenance": "COMPLETE",
            "2_local_self_hosted_runners": "COMPLETE",
            "3_low_variance_decoding_per_model": "PENDING",
            "4_deterministic_native_output_adapters": "PENDING",
            "5_synthetic_gate_four_primary_models": "COMPLETE",
            "6_final_model_roles_and_backup_substitutions": "PENDING",
            "7_freeze_prompts_schema_adapters_runner_metric_engine": "PENDING",
            "8_record_protocol_freeze_commit": "PENDING",
        })

    def test_freeze_template_cannot_resolve_expansion_candidate(self):
        link = self.freeze["primary_expansion_precommit"]
        self.assertEqual(link["status"], "PENDING_QUALIFICATION")
        self.assertEqual(link["candidate_key"], MODEL_KEY)
        self.assertFalse(link["resolved_for_freeze"])
        self.assertTrue(link["resolution_required_before_protocol_freeze"])
        self.assertFalse(link["automatic_promotion"])
        self.assertNotIn(MODEL_ID, [m["model_id"] for m in self.freeze["primary_models"]])

    def test_provenance_identity_matches_record(self):
        provenance = next(m for m in self.provenance["models"] if m["key"] == MODEL_KEY)
        candidate = self.record["candidate"]
        self.assertEqual(provenance["model_id"], candidate["model_id"])
        self.assertEqual(provenance["immutable_revision"], candidate["immutable_revision"])
        self.assertEqual(provenance["roster_group"], "backup")
        self.assertEqual(provenance["order"], 1)

    def test_no_automatic_florence_or_replacement_fallback(self):
        self.assertFalse(self.record["promotion_rule"]["automatic_promotion"])
        self.assertFalse(self.record["promotion_rule"]["automatic_alternate_candidate"])
        self.assertTrue(self.record["promotion_rule"]["future_alternate_requires_new_research_lead_decision"])
        self.assertFalse(self.roster["primary_expansion_precommit"]["automatic_promotion"])
        self.assertNotIn("Florence", json.dumps(self.roster))
        self.assertNotIn("florence", json.dumps(self.freeze).lower())


if __name__ == "__main__":
    unittest.main()
