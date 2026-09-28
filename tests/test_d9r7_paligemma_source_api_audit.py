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

    def test_owner_confirmation_and_authenticated_access_are_separate(self):
        a = self.audit
        self.assertEqual(a["access_status"], "OWNER_CONFIRMED_TERMS_ACCEPTED_EXACT_FILES_READABLE")
        self.assertEqual(a["status"], "DOCUMENTARY_PARTIAL_NORMALIZATION_UNRESOLVED")
        # Historical/precommit records are intentionally unchanged in this PR.
        self.assertEqual(self.precommit["qualification_status"]["access"], ACCESS)
        self.assertEqual(self.provenance["license_access"]["access_status"], ACCESS)
        access = a["access_evidence"]
        self.assertEqual(access["owner_acceptance_status"], "OWNER_CONFIRMED_IN_SESSION")
        self.assertEqual(access["owner_confirmation"]["source_type"], "OWNER_USER_MESSAGE")
        for field in ("owner_acceptance_asserted_by_codex", "credential_material_recorded",
                      "terms_accepted_by_codex"):
            self.assertIs(access[field], False)
        self.assertIs(access["authentication_used"], True)
        self.assertIs(access["exact_revision_provenance_matches"], True)
        self.assertEqual(access["blocked_files"], [])
        self.assertEqual(set(access["verified_files"]), {
            "config.json", "preprocessor_config.json", "tokenizer_config.json",
            "special_tokens_map.json", "tokenizer.json",
        })
        for name in access["verified_files"]:
            source = a["sources"]["exact_" + name]
            self.assertEqual(source["http_status"], 200)
            self.assertEqual(source["url"],
                             f"https://huggingface.co/{MODEL}/resolve/{REVISION}/{name}")
            self.assertEqual(a["sources"]["blocked_" + name]["http_status"], 401)

    def test_loader_native_classes_and_remote_code_boundary(self):
        loader = self.audit["loader"]
        self.assertEqual(loader["class"], "PaliGemmaForConditionalGeneration")
        self.assertEqual(loader["class_status"], "EXACT_CHECKPOINT_VERIFIED")
        self.assertEqual(loader["model_type"], "paligemma")
        self.assertEqual(loader["processor_status"], "EXACT_CHECKPOINT_VERIFIED")
        self.assertEqual(loader["processor"], "PaliGemmaProcessor (AutoProcessor built-in mapping)")
        self.assertEqual(loader["tokenizer_class"], "GemmaTokenizer")
        self.assertIs(loader["trust_remote_code"], False)
        self.assertEqual(loader["trust_remote_code_status"],
                         "NOT_REQUIRED_DOCUMENTARY_VERIFIED")
        self.assertIs(loader["remote_code_required_by_exact_checkpoint"], False)
        self.assertEqual(loader["auto_map_present"], {
            "config.json": False, "preprocessor_config.json": False,
            "tokenizer_config.json": False,
        })
        self.assertEqual(loader["remote_code_if_required_action"],
                         "STOP_AND_RESEARCH_LEAD_REVIEW_REQUIRED")
        self.assertEqual(loader["status"], "EXACT_DOCUMENTARY_VERIFIED_NOT_RUNTIME_VALIDATED")

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
        self.assertEqual(native["exact_checkpoint_status"],
                         "TOKEN_VOCABULARY_VERIFIED_DETECTION_CONTRACT_NOT_VERIFIED")
        for field in ("coordinate_order", "normalization_rule", "multiple_detection_grammar"):
            self.assertEqual(native[field], UNVERIFIED)
        self.assertEqual(native["literal_token_format"], "<loc%04d>")
        self.assertEqual(native["literal_token_format_status"], "EXACT_CHECKPOINT_VERIFIED")
        self.assertEqual(native["integer_range"], {
            "minimum": 0, "maximum": 1023, "inclusive": True, "token_count": 1024,
        })
        self.assertEqual(native["integer_range_status"], "EXACT_CHECKPOINT_VERIFIED_TOKEN_VALUES_ONLY")
        self.assertEqual(native["coordinate_order_status"], "FAMILY_LEVEL_ONLY")
        self.assertEqual(native["multiple_detection_grammar_status"], "FAMILY_LEVEL_ONLY")
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
        self.assertEqual(conflict["resolution"], "UNRESOLVED_SCOPE_CONFLICT")
        self.assertIsNone(conflict["selected_divisor"])
        self.assertIn("* 1023", conflict["training_encoding"]["operation"])
        self.assertIn("/ 1024.0", conflict["visualization_decoding"]["operation"])
        self.assertEqual(conflict["training_encoding"]["scope"], "SEGMENTATION_ONLY")
        self.assertIn("PaliGemma2/Keras", conflict["visualization_decoding"]["scope"])
        source = self.audit["sources"]["google_decode"]
        self.assertEqual(source["applicability_scope"], "FAMILY_LEVEL_ONLY")

    def test_no_mapping_clamp_or_heuristic_repair(self):
        conversion = self.audit["canonical_conversion"]
        self.assertEqual(conversion["status"], "BLOCKED")
        self.assertEqual(conversion["deterministic_mapping"], UNVERIFIED)
        self.assertIsNone(conversion["normalization_divisor"])
        self.assertEqual(conversion["clamp_policy"], "NO_CLAMP_PROPOSED")
        self.assertEqual(conversion["malformed_output_policy"], "PROPOSED_PARSER_FAIL_NO_REPAIR")
        for field in ("heuristic_used", "point_to_box", "fabricated_box", "artificial_zero_iou"):
            self.assertIs(conversion[field], False)

    def test_preprocessing_is_exact_config_with_no_override(self):
        image = self.audit["image_preprocessing"]
        self.assertEqual(image["status"], "EXACT_CONFIG_AND_LIBRARY_SOURCE_VERIFIED")
        self.assertEqual(image["expected_image_size"]["value"], [448, 448])
        self.assertEqual(image["image_token_count"], 1024)
        self.assertEqual(image["image_token_index"], 257152)
        self.assertEqual(image["processor_settings"], {
            "do_resize": True, "size": {"height": 448, "width": 448}, "resample": 3,
            "do_convert_rgb": None, "image_processor_type": "SiglipImageProcessor",
            "image_seq_length": 1024,
        })
        norm = image["image_normalization"]
        self.assertEqual(norm["rescale_factor"], 1 / 255)
        self.assertEqual(norm["image_mean"], [0.5] * 3)
        self.assertEqual(norm["image_std"], [0.5] * 3)
        self.assertTrue(norm["do_rescale"] and norm["do_normalize"])
        self.assertIs(image["preprocessing_override_proposed"], False)

    def test_exact_location_vocabulary_is_not_added_or_special(self):
        tokenizer = self.audit["tokenizer_metadata"]
        self.assertEqual(tokenizer["status"], "EXACT_CHECKPOINT_VERIFIED")
        self.assertIs(tokenizer["exact_location_tokens_present"], True)
        self.assertEqual(tokenizer["exact_location_token_ids"], {
            "first": 256000, "last": 257023,
            "mapping": "id(<loc%04d> % i) = 256000 + i for i in 0..1023",
        })
        self.assertEqual(tokenizer["exact_location_token_range"], {
            "minimum": 0, "maximum": 1023, "count": 1024,
        })
        self.assertEqual(tokenizer["location_added_tokens_count"], 0)
        self.assertEqual(tokenizer["location_special_tokens_count"], 0)
        self.assertEqual(tokenizer["location_storage"], "tokenizer.json $.model.vocab")
        self.assertIs(tokenizer["location_token_set_and_id_mapping_exhaustively_checked"], True)
        self.assertEqual(tokenizer["image_token"], {
            "content": "<image>", "id": 257152, "added_token": True, "special": True,
        })

    def test_exact_metadata_byte_provenance(self):
        expected = {
            "config.json": (1053, "39d09eda96e3c88a80d2e9684609350a502eb7bf"),
            "preprocessor_config.json": (700, "9f8dbd7ed03f06434785e4b660c164105fd00ca1"),
            "tokenizer_config.json": (39968, "960dcec0bccc6e594d865eceb63c8078e164cfb2"),
            "special_tokens_map.json": (607, "0c18fdd94629ea652e2ef36ed9a422474ad0a8e8"),
            "tokenizer.json": (17549604, "ef6773c135b77b834de1d13c75a4c98ab7a3684ffd602d1831e1f1bf5467c563"),
        }
        for file, (size, digest) in expected.items():
            source = self.audit["sources"]["exact_" + file]
            binding = source["revision_provenance"]
            self.assertEqual(source["size_bytes"], size)
            self.assertEqual(binding["hash"], digest)
            self.assertIs(binding["matches"], True)
            self.assertEqual(binding["expected_from"], "exact_metadata")
            if file == "tokenizer.json":
                self.assertEqual(binding["method"], "lfs_sha256")
                self.assertEqual(source["content_sha256"], digest)
                self.assertIsNone(binding["repo_commit_header"])
            else:
                self.assertEqual(binding["method"], "git_blob_sha1")
                self.assertEqual(binding["repo_commit_header"], REVISION)

    def test_paligemma1_detection_decoder_does_not_invent_encoder_or_mapping(self):
        detection = self.audit["object_detection_source_pass"]
        self.assertEqual(detection["status"], "UNRESOLVED_SCOPE_CONFLICT")
        self.assertEqual(detection["encoding"]["status"], UNVERIFIED)
        self.assertEqual(detection["decoding"]["status"], "PALIGEMMA1_OFFICIAL_DETECTION_VERIFIED")
        self.assertEqual(detection["decoding"]["source_defined_divisor"], 1024)
        self.assertIs(detection["decoding"]["exact_checkpoint_revision_bound"], False)
        self.assertIsNone(detection["selected_divisor"])
        self.assertEqual(self.audit["sources"]["google_training_encoding"]["applicability_scope"],
                         "SEGMENTATION_ONLY")
        source = self.audit["sources"]["paligemma1_hf_detection"]
        self.assertIn("d914d4446a6ff8c5b3110411abca69887f035c41", source["url"])
        self.assertEqual(source["applicability_scope"], "PALIGEMMA1_OFFICIAL_DETECTION")
        self.assertEqual(self.audit["native_coordinate_interface"]["empty_output_behavior"],
                         "NOT_DOCUMENTED")

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
