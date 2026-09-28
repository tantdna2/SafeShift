"""Static evidence and stop-condition guards; no model/network imports."""

import unittest
from pathlib import Path
from urllib.parse import urlparse

from safeshift.protocol.schema import strict_json


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "pre_freeze"
MODEL = "google/paligemma-3b-mix-448"
REVISION = "ead2d9a35598cb89119af004f5d023b311d1c4a1"
ACCESS = "GATED_USAGE_TERMS_ACCEPTANCE_REQUIRED"
PENDING = "PENDING_QUALIFICATION"
UNVERIFIED = "NOT_VERIFIED"


def load(name):
    return strict_json((CONFIG / name).read_bytes())


class PaliGemmaSourceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load("paligemma_source_api_audit.v1.json")
        cls.precommit = load("paligemma_primary_expansion_precommit.v1.json")
        cls.roster = load("local_models.d9.json")
        cls.provenance = next(
            m for m in load("local_model_provenance.d9.json")["models"]
            if m["key"] == "paligemma_3b_mix_448"
        )

    def test_exact_identity_no_substitution(self):
        a = self.audit
        self.assertEqual(a["record_kind"], "PALIGEMMA_SOURCE_API_AUDIT")
        self.assertEqual(a["schema_version"], "1.0")
        self.assertEqual(a["base_sha"], "d1ff06d506240df60a19cb094333c9c32e461c73")
        for record in (a, self.precommit["candidate"], self.provenance,
                       self.roster["backups_in_order"][0]):
            self.assertEqual((record["model_id"], record["immutable_revision"]),
                             (MODEL, REVISION))
        self.assertIs(a["governance"]["model_substitution"], False)
        self.assertIs(a["runtime_documentary"]["fp16_documentary_support"]
                      ["converted_revision_selected"], False)

    def test_access_block_is_not_owner_acceptance(self):
        a = self.audit
        self.assertEqual(a["access_status"], ACCESS)
        self.assertEqual(a["status"], "ACCESS_EVIDENCE_BLOCKED")
        self.assertEqual(self.precommit["qualification_status"]["access"], ACCESS)
        self.assertEqual(self.provenance["license_access"]["access_status"], ACCESS)
        access = a["access_evidence"]
        self.assertEqual(access["owner_acceptance_status"], UNVERIFIED)
        for field in ("owner_acceptance_asserted", "authentication_used",
                      "terms_accepted_by_codex"):
            self.assertIs(access[field], False)
        self.assertIs(access["dependent_work_stopped"], True)
        self.assertEqual(set(access["blocked_files"]), {
            "config.json", "preprocessor_config.json", "tokenizer_config.json",
            "special_tokens_map.json", "tokenizer.json",
        })
        for name in access["blocked_files"]:
            source = a["sources"]["blocked_" + name]
            self.assertEqual(source["http_status"], 401)
            self.assertEqual(source["url"],
                             f"https://huggingface.co/{MODEL}/resolve/{REVISION}/{name}")

    def test_loader_false_is_policy_not_exact_requirement_claim(self):
        loader = self.audit["loader"]
        self.assertEqual(loader["class"], "PaliGemmaForConditionalGeneration")
        self.assertEqual(loader["class_status"], "EXACT_CHECKPOINT_VERIFIED_METADATA_ONLY")
        self.assertEqual(loader["processor_status"], "FAMILY_LEVEL_ONLY")
        self.assertIs(loader["trust_remote_code"], False)
        self.assertEqual(loader["trust_remote_code_status"],
                         "REQUIRED_SAFESHIFT_POLICY_EXACT_REQUIREMENT_NOT_VERIFIED")
        self.assertEqual(loader["remote_code_required_by_exact_checkpoint"], UNVERIFIED)
        self.assertEqual(loader["remote_code_if_required_action"], "STOP")
        self.assertEqual(loader["status"], "ACCESS_EVIDENCE_BLOCKED")

    def test_routes_remain_family_only(self):
        for name, prompt in (("classification_route", "answer en {question}\n"),
                             ("detection_route", "detect {object}\n")):
            route = self.audit[name]
            self.assertEqual(route["status"], "FAMILY_LEVEL_ONLY")
            self.assertEqual(route["documented_prompt_form"], prompt)
            self.assertIn("NOT_VERIFIED", route["applicability_scope"])
        self.assertIs(self.audit["classification_route"]["final_safeshift_prompt_designed"], False)

    def test_exact_grammar_is_unresolved(self):
        native = self.audit["native_coordinate_interface"]
        self.assertEqual(native["status"], "PENDING_DOCUMENTARY_VERIFICATION")
        self.assertEqual(native["exact_checkpoint_status"], "ACCESS_EVIDENCE_BLOCKED")
        for field in ("literal_token_format", "coordinate_order", "integer_range",
                      "normalization_rule", "multiple_detection_grammar"):
            self.assertEqual(native[field], UNVERIFIED)
        self.assertEqual(native["empty_output_behavior"], "NOT_DOCUMENTED")
        family = native["family_level_findings"]
        self.assertIn("<loc%04d>", family["literal_token_format"]["value"])
        self.assertEqual(family["integer_range"]["value"], {
            "minimum": 0, "maximum": 1023, "inclusive": True, "token_count": 1024,
        })
        for field in ("literal_token_format", "coordinate_order", "integer_range",
                      "multiple_detection_grammar"):
            self.assertEqual(family[field]["status"], "FAMILY_LEVEL_ONLY")

    def test_conflicting_scales_are_not_resolved_by_guess(self):
        conflicts = self.audit["native_coordinate_interface"]["unresolved_conflicts"]
        self.assertEqual(len(conflicts), 1)
        conflict = conflicts[0]
        self.assertEqual(conflict["status"], "STOP_AND_RESEARCH_LEAD_REVIEW_REQUIRED")
        self.assertEqual(conflict["resolution"], "NOT_RESOLVED")
        self.assertIsNone(conflict["selected_divisor"])
        self.assertIn("* 1023", conflict["training_encoding"]["operation"])
        self.assertIn("/ 1024.0", conflict["visualization_decoding"]["operation"])
        self.assertIn("segmentation", conflict["training_encoding"]["scope"])
        self.assertIn("PaliGemma2/Keras", conflict["visualization_decoding"]["scope"])
        source = self.audit["sources"]["google_decode"]
        self.assertEqual(source["applicability_scope"], "FAMILY_LEVEL_ONLY")

    def test_no_mapping_clamp_or_heuristic_repair(self):
        conversion = self.audit["canonical_conversion"]
        self.assertEqual(conversion["status"], "BLOCKED_PENDING_DOCUMENTARY_VERIFICATION")
        self.assertEqual(conversion["deterministic_mapping"], UNVERIFIED)
        self.assertIsNone(conversion["normalization_divisor"])
        self.assertEqual(conversion["clamp_policy"], "NO_CLAMP_PROPOSED")
        self.assertEqual(conversion["malformed_output_policy"], "PROPOSED_PARSER_FAIL_NO_REPAIR")
        for field in ("heuristic_used", "point_to_box", "fabricated_box", "artificial_zero_iou"):
            self.assertIs(conversion[field], False)

    def test_preprocessing_and_tokenizer_not_inferred_from_family(self):
        image = self.audit["image_preprocessing"]
        self.assertEqual(image["expected_image_size"]["value"], [448, 448])
        for field in ("resize_crop_behavior", "image_normalization", "image_token_count"):
            self.assertEqual(image[field], UNVERIFIED)
        self.assertIs(image["preprocessing_override_proposed"], False)
        tokenizer = self.audit["tokenizer_metadata"]
        for field in ("exact_location_tokens_present", "exact_location_token_ids",
                      "exact_location_token_range"):
            self.assertEqual(tokenizer[field], UNVERIFIED)

    def test_weight_metadata_matches_existing_provenance_without_runtime_pass(self):
        runtime = self.audit["runtime_documentary"]
        weights = self.provenance["weight_provenance"]
        self.assertEqual(runtime["parameter_count"], weights["published_parameter_count"])
        self.assertEqual(runtime["selected_weight_format"], "safetensors")
        self.assertEqual(runtime["selected_tensor_dtype"], "F32")
        self.assertEqual(runtime["published_weight_files"], [
            {key: f[key] for key in ("path", "size_bytes")} for f in weights["files"]
        ])
        self.assertEqual(sum(f["size_bytes"] for f in runtime["published_weight_files"]),
                         runtime["published_safetensors_size_bytes"])
        self.assertEqual(runtime["status"], "DOCUMENTED_NOT_RUNTIME_VALIDATED")
        self.assertEqual(runtime["real_runtime_status"], PENDING)
        for field in ("t4_runtime_pass", "weights_downloaded", "weight_bytes_verified"):
            self.assertIs(runtime[field], False)

    def test_no_promotion_freeze_inspecsafe_or_gate_pass(self):
        governance = self.audit["governance"]
        self.assertEqual(governance["paligemma_role"], "BACKUP_1")
        self.assertEqual(governance["primary_roster_count"], 4)
        self.assertEqual(len(self.roster["primary_models"]), 4)
        self.assertNotIn(MODEL, [m["model_id"] for m in self.roster["primary_models"]])
        self.assertEqual(self.roster["backups_in_order"][0]["role"], "BACKUP_1")
        for field in ("promotion", "precommit_changed", "inspecsafe_authorized",
                      "runner_prep_authorized_next"):
            self.assertIs(governance[field], False)
        for field in ("runtime_status", "grounding_status", "external_gate_status"):
            self.assertEqual(governance[field], PENDING)
        self.assertEqual(governance["protocol_freeze"], "PENDING")
        for field in ("inspecsafe_used", "real_model_execution", "inspecsafe_execution"):
            self.assertIs(self.audit[field], False)
        self.assertEqual(self.precommit["status"], PENDING)
        contract = self.precommit["qualification_contract"]
        for field in ("documentary_source_interface", "real_single_t4_runtime",
                      "classification_interface", "grounding_interface", "frozen_external_gate"):
            self.assertEqual(contract[field]["status"], PENDING)
        self.assertEqual(contract["grounding_interface"]["native_output_grammar_status"],
                         "PENDING_DOCUMENTARY_VERIFICATION")

    def test_every_source_has_provenance_scope_and_limits(self):
        for name, source in self.audit["sources"].items():
            with self.subTest(source=name):
                for field in ("url", "revision_or_version", "locator", "accessed_date",
                              "applicability_scope", "limitations"):
                    self.assertTrue(source[field])
                self.assertEqual(source["accessed_date"], "2026-09-28")
                self.assertRegex(source["content_sha256"], r"^[a-f0-9]{64}$")
                url = urlparse(source["url"])
                self.assertEqual(url.scheme, "https")
                self.assertIn(url.netloc, {"huggingface.co", "raw.githubusercontent.com",
                                          "ai.google.dev"})
                if source["applicability_scope"] == "EXACT_CHECKPOINT":
                    self.assertIn(MODEL, source["url"])
                    self.assertIn(REVISION, source["url"])
                    self.assertEqual(source["revision_or_version"], REVISION)

    def test_evidence_references_resolve(self):
        sources = self.audit["sources"]

        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == "evidence":
                        self.assertTrue(item)
                        for ref in item:
                            self.assertTrue(ref in sources or (ROOT / ref).is_file(), ref)
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(self.audit)


if __name__ == "__main__":
    unittest.main()
