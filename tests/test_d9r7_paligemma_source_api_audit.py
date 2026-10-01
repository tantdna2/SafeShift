"""Static evidence and stop-condition guards; no model/network imports."""

import unittest
import subprocess
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
SELECTED = "SOURCE_BACKED_SELECTED_PENDING_RUNTIME_QUALIFICATION"
RESOLVED = "RESOLVED_PALIGEMMA1_OFFICIAL_DETECTION"


def load(name):
    return strict_json((CONFIG / name).read_bytes())


class PaliGemmaSourceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load("paligemma_source_api_audit.v1.json")
        cls.precommit = load("paligemma_primary_expansion_precommit.v1.json")
        # Preserve historical audit membership; D9R15 tests cover the live roster.
        cls.roster = strict_json(subprocess.check_output([
            "git", "show", "9948570820b5ed8a774b8e226b80e24055e705cf:"
            "configs/pre_freeze/local_models.d9.json"], cwd=ROOT))
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
        self.assertEqual(a["status"], "DOCUMENTARY_SOURCE_BACKED_SELECTED_PENDING_RUNTIME_QUALIFICATION")
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

    def test_source_backed_grammar_is_not_exact_runtime_qualification(self):
        native = self.audit["native_coordinate_interface"]
        self.assertEqual(native["status"], SELECTED)
        self.assertEqual(native["exact_checkpoint_status"],
                         "TOKENIZER_INTERFACE_ARTIFACTS_VERIFIED_RUNTIME_PENDING_QUALIFICATION")
        self.assertEqual(native["coordinate_order"], ["y_min", "x_min", "y_max", "x_max"])
        self.assertEqual(native["four_location_token_structure"], "<loc%04d>" * 4)
        self.assertEqual(native["normalization_rule_status"], SELECTED)
        self.assertIs(native["exact_revision_runtime_verified"], False)
        self.assertEqual(native["multiple_detection_grammar"], UNVERIFIED)
        self.assertEqual(native["literal_token_format"], "<loc%04d>")
        self.assertEqual(native["literal_token_format_status"], "EXACT_CHECKPOINT_VERIFIED")
        self.assertEqual(native["integer_range"], {
            "minimum": 0, "maximum": 1023, "inclusive": True, "token_count": 1024,
        })
        self.assertEqual(native["integer_range_status"], "EXACT_CHECKPOINT_VERIFIED_TOKEN_VALUES_ONLY")
        self.assertEqual(native["coordinate_order_status"], "SOURCE_BACKED_MODEL_ID_LEVEL")
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

    def test_research_lead_resolution_preserves_segmentation_history(self):
        native = self.audit["native_coordinate_interface"]
        self.assertEqual(native["unresolved_conflicts"], [])
        self.assertEqual(native["normalization_conflict_status"], RESOLVED)
        conflict, = native["resolved_conflicts"]
        self.assertEqual(conflict["status"], "RESOLVED_BY_RESEARCH_LEAD_NARROW_DECISION")
        self.assertEqual(conflict["resolution"], RESOLVED)
        self.assertEqual(conflict["selected_divisor"], 1024.0)
        encoding = conflict["training_encoding"]
        self.assertIn("round(bbox * 1023)", encoding["operation"])
        self.assertIn("clip integer indices to [0,1023]", encoding["operation"])
        self.assertEqual(encoding["scope"], "REFCOCO_SEGMENTATION_TRAINING_ENCODING")
        self.assertEqual(encoding["detection_decoding_selection"],
                         "NOT_SELECTED_FOR_DETECTION_DECODING")
        decision = self.audit["research_lead_resolution"]
        self.assertEqual(decision["status"], "APPROVED_NARROW_RESOLUTION")
        self.assertEqual(decision["decision_record"], "DECISIONS.md")
        self.assertEqual(decision["evidence_scope"], "PALIGEMMA1_UPSTREAM_MODEL_ID_LEVEL_DETECTION")
        for field in ("before_paligemma_runtime", "before_external_gate", "before_inspecsafe"):
            self.assertIs(decision[field], True)
        self.assertIs(decision["exact_revision_runtime_verified"], False)

    def test_selected_mapping_no_clamp_or_heuristic_repair(self):
        conversion = self.audit["canonical_conversion"]
        self.assertEqual(conversion["status"], SELECTED)
        self.assertEqual(conversion["deterministic_mapping"], {
            "x_min": "loc_x_min / 1024.0", "y_min": "loc_y_min / 1024.0",
            "x_max": "loc_x_max / 1024.0", "y_max": "loc_y_max / 1024.0",
        })
        self.assertEqual(conversion["normalization_divisor"], 1024.0)
        self.assertEqual(conversion["native_order"], ["y_min", "x_min", "y_max", "x_max"])
        self.assertEqual(conversion["canonical_order"], ["x_min", "y_min", "x_max", "y_max"])
        self.assertEqual(conversion["axis_swap"], [1, 0, 3, 2])
        self.assertEqual(conversion["clamp_policy"], "NO_CLAMP")
        self.assertEqual(conversion["malformed_output_policy"], "PARSER_FAIL_NO_REPAIR")
        for field in ("heuristic_used", "point_to_box", "fabricated_box", "artificial_zero_iou",
                      "exact_revision_runtime_verified"):
            self.assertIs(conversion[field], False)

    def test_mapping_axes_and_endpoint_are_not_rescaled_to_one(self):
        # Evaluate the recorded permutation/divisor only, not a runtime parser.
        c = self.audit["canonical_conversion"]
        native = [0, 256, 768, 1023]
        mapped = [native[index] / c["normalization_divisor"] for index in c["axis_swap"]]
        self.assertEqual(mapped, [0.25, 0.0, 0.9990234375, 0.75])
        self.assertEqual(c["maximum_representable_normalized_coordinate"], 1023 / 1024)
        self.assertLess(c["maximum_representable_normalized_coordinate"], 1.0)
        self.assertEqual(c["maximum_representable_normalized_coordinate_exact"], "1023/1024")
        self.assertEqual(c["native_numerical_range"], {
            "minimum": 0, "maximum": 1023, "inclusive": True,
        })

    def test_no_selected_detection_divisor_is_1023(self):
        selected_divisors = []

        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in {"selected_divisor", "normalization_divisor",
                               "source_defined_divisor", "source_defined_detection_divisor"}:
                        selected_divisors.append(item)
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(self.audit)
        self.assertTrue(selected_divisors)
        self.assertTrue(all(value == 1024 for value in selected_divisors))

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

    def test_selected_decoder_scope_does_not_invent_exact_runtime_or_encoder(self):
        detection = self.audit["object_detection_source_pass"]
        self.assertEqual(detection["status"], RESOLVED)
        self.assertEqual(detection["encoding"]["status"], UNVERIFIED)
        self.assertEqual(detection["decoding"]["status"], "PALIGEMMA1_OFFICIAL_DETECTION_VERIFIED")
        self.assertEqual(detection["decoding"]["source_defined_divisor"], 1024)
        self.assertIs(detection["decoding"]["exact_checkpoint_revision_bound"], False)
        self.assertEqual(detection["selected_divisor"], 1024.0)
        self.assertIs(detection["exact_revision_runtime_verified"], False)
        self.assertEqual(self.audit["sources"]["google_training_encoding"]["applicability_scope"],
                         "REFCOCO_SEGMENTATION_TRAINING_ENCODING")
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
        for field in ("t4_runtime_pass", "weights_downloaded", "weight_bytes_verified",
                      "exact_revision_runtime_verified"):
            self.assertIs(runtime[field], False)

    def test_no_promotion_freeze_inspecsafe_or_gate_pass(self):
        governance = self.audit["governance"]
        self.assertEqual(governance["paligemma_role"], "BACKUP_1")
        self.assertEqual(governance["primary_roster_count"], 4)
        self.assertEqual(len(self.roster["primary_models"]), 4)
        self.assertNotIn(MODEL, [m["model_id"] for m in self.roster["primary_models"]])
        self.assertEqual(self.roster["backups_in_order"][0]["role"], "BACKUP_1")
        for field in ("promotion", "precommit_changed", "inspecsafe_authorized",
                      "runner_prep_authorized_next", "runner_prep_executed"):
            self.assertIs(governance[field], False)
        self.assertIs(governance["runner_prep_authorized_after_pr55_audit_and_merge"], True)
        self.assertEqual(governance["runner_prep_prerequisites"],
                         ["PR55_INDEPENDENT_AUDIT_PASS", "PR55_MERGED"])
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
