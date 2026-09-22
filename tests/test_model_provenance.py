"""Offline documentary D9 invariants; never imports or executes a model backend."""

from datetime import datetime
from pathlib import Path
import re
import unittest
from urllib.parse import urlparse

from safeshift.protocol.schema import strict_json


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "pre_freeze"
PROVENANCE_PATH = "configs/pre_freeze/local_model_provenance.d9.json"
PRIMARY = [
    "Qwen/Qwen3-VL-8B-Instruct", "AIDC-AI/Ovis2.5-9B",
    "allenai/Molmo2-O-7B", "google/gemma-4-12B-it",
]
BACKUPS = ["google/paligemma2-10b-mix-448", "openbmb/MiniCPM-V-4.6"]
KEYS = [
    "qwen3_vl_8b_instruct", "ovis2_5_9b", "molmo2_o_7b", "gemma4_12b_it",
    "paligemma2_10b_mix_448", "minicpm_v_4_6",
]
SECTION_KEYS = {
    "key", "model_id", "roster_group", "order", "repository_url",
    "resolved_repository_id", "immutable_revision", "revision_status",
    "revision_verification", "weight_provenance", "license_access", "runtime",
    "spatial", "classification_integration", "decoding", "preprocessing",
    "precision_quantization", "partial_generation",
}


def load(name):
    return strict_json((CONFIG / name).read_bytes())


def walk(value):
    """Yield nested keys/values, including records inside arrays."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


class ModelProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = load("local_model_provenance.d9.json")
        cls.roster = load("local_models.d9.json")
        cls.freeze = load("freeze_manifest.d9.template.json")
        cls.models = cls.spec["models"]
        cls.sources = cls.spec["sources"]

    def test_six_exact_ids_and_primary_backup_order(self):
        self.assertEqual([m["model_id"] for m in self.models], PRIMARY + BACKUPS)
        self.assertEqual([m["key"] for m in self.models], KEYS)
        self.assertEqual([m["roster_group"] for m in self.models], ["primary"] * 4 + ["backup"] * 2)
        self.assertEqual([m["order"] for m in self.models], [1, 2, 3, 4, 1, 2])

    def test_roster_consistency_across_all_three_configs(self):
        self.assertEqual([m["model_id"] for m in self.roster["primary_models"]], PRIMARY)
        self.assertEqual([m["model_id"] for m in self.freeze["primary_models"]], PRIMARY)
        self.assertEqual([m["model_id"] for m in self.roster["backups_in_order"]], BACKUPS)
        self.assertEqual(self.freeze["backup_order"], BACKUPS)
        for config in (self.roster, self.freeze):
            self.assertEqual(config["model_provenance_config"], PROVENANCE_PATH)
            for entry in config["primary_models"] + config.get("backups_in_order", []):
                spec = next(m for m in self.models if m["model_id"] == entry["model_id"])
                self.assertEqual(entry["immutable_revision"], spec["immutable_revision"])
                self.assertEqual(entry["provenance_key"], spec["key"])
                self.assertEqual(entry["revision_status"], "VERIFIED_DOCUMENTARY")

    def test_immutable_revisions_are_full_hugging_face_commit_sha(self):
        for model in self.models:
            with self.subTest(model=model["model_id"]):
                self.assertRegex(model["immutable_revision"], r"\A[0-9a-f]{40}\Z")
                self.assertNotIn(model["immutable_revision"].lower(), {"main", "master", "latest", "pending"})
                self.assertEqual(model["revision_status"], "VERIFIED_DOCUMENTARY")

    def test_every_revision_has_matching_official_metadata_and_utc(self):
        for model in self.models:
            verification = model["revision_verification"]
            self.assertIn("compare $.sha", verification["method"])
            when = datetime.fromisoformat(verification["accessed_at_utc"])
            self.assertIsNotNone(when.utcoffset())
            self.assertEqual(when.utcoffset().total_seconds(), 0)
            refs = verification["evidence"]
            self.assertEqual(len(refs), 2)
            first, pinned = (self.sources[ref] for ref in refs)
            self.assertEqual(first["url"], "https://huggingface.co/api/models/" + model["model_id"])
            self.assertEqual(pinned["url"], first["url"] + "/revision/" + model["immutable_revision"] + "?blobs=true")
            self.assertEqual(pinned["accessed_at_utc"], verification["accessed_at_utc"])
            for source in (first, pinned):
                self.assertRegex(source["response_sha256"], r"\A[0-9a-f]{64}\Z")

    def test_sources_are_official_and_resolvable_offline(self):
        allowed = {"huggingface.co", "github.com", "raw.githubusercontent.com", "ai.google.dev"}
        for source in self.sources.values():
            parsed = urlparse(source["url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertIn(parsed.hostname, allowed)
            self.assertTrue(source["locator"])
            self.assertTrue(source["accessed_at_utc"])
        for key, value in walk(self.spec):
            if key == "evidence":
                for identifier in value:
                    self.assertIn(identifier, self.sources)

    def test_every_factual_section_has_evidence(self):
        sections = SECTION_KEYS - {
            "key", "model_id", "roster_group", "order", "repository_url",
            "resolved_repository_id", "immutable_revision", "revision_status",
        }
        for model in self.models:
            for section in sections:
                with self.subTest(model=model["key"], section=section):
                    self.assertTrue(model[section]["evidence"])

    def test_weight_provenance_is_metadata_only_and_complete(self):
        for model, expected_count in zip(self.models, [4, 4, 7, 1, 4, 1]):
            provenance = model["weight_provenance"]
            self.assertEqual(provenance["status"], "VERIFIED_DOCUMENTARY_METADATA_ONLY")
            self.assertIs(provenance["downloaded"], False)
            self.assertIs(provenance["local_bytes_verified"], False)
            self.assertEqual(len(provenance["files"]), expected_count)
            for file in provenance["files"]:
                self.assertRegex(file["lfs_sha256"], r"\A[0-9a-f]{64}\Z")
                self.assertGreater(file["size_bytes"], 0)
                self.assertEqual(Path(file["path"]).name, file["path"])
                self.assertTrue(file["path"].endswith(".safetensors"))
            self.assertEqual(provenance["published_tensor_dtypes"], ["F32"] if model["key"] == "molmo2_o_7b" else ["BF16"])

    def test_license_access_fields_are_separate_and_required(self):
        required = {"repository_license", "access_status", "gated", "requires_accept_terms",
                    "owner_acceptance_status", "additional_model_card_conditions",
                    "training_data_licensing_caveat", "intended_use_warning", "evidence"}
        for model in self.models:
            record = model["license_access"]
            self.assertLessEqual(required, record.keys())
            self.assertTrue(all(record[k] for k in required - {"gated", "requires_accept_terms"}))
            self.assertEqual(record["repository_license"], "gemma" if model["roster_group"] == "backup" and model["order"] == 1 else "apache-2.0")

    def test_ovis_redirect_preserves_d9_identity(self):
        model = self.models[1]
        self.assertEqual(model["model_id"], "AIDC-AI/Ovis2.5-9B")
        self.assertEqual(model["resolved_repository_id"], "ATH-MaaS/Ovis2.5-9B")
        self.assertEqual(self.sources["ovis2_5_9b.api"]["resolved_url"],
                         "https://huggingface.co/api/models/ATH-MaaS/Ovis2.5-9B")

    def test_molmo_apache_and_training_data_caveat_both_retained(self):
        record = self.models[2]["license_access"]
        self.assertEqual(record["repository_license"], "apache-2.0")
        self.assertIn("academic and non-commercial research", record["training_data_licensing_caveat"])
        self.assertIn("Responsible Use", record["additional_model_card_conditions"])
        self.assertIn("unresolved", record["intended_use_warning"])

    def test_paligemma_gate_and_terms_are_not_model_failure(self):
        record = self.models[4]["license_access"]
        self.assertEqual(record["repository_license"], "gemma")
        self.assertEqual(record["gated"], "manual")
        self.assertIs(record["requires_accept_terms"], True)
        self.assertEqual(record["access_status"], "ACCESS_REQUIRES_USER_ACCEPTANCE")
        self.assertEqual(record["owner_acceptance_status"], "NOT_VERIFIED")
        self.assertIn("research purposes", record["additional_model_card_conditions"])
        self.assertEqual(record["terms_url"], "https://ai.google.dev/gemma/terms")
        self.assertEqual(self.roster["backups_in_order"][0]["replacement_status"], "BACKUP_1_ONLY")

    def test_documentary_completion_never_sets_protocol_freeze(self):
        self.assertEqual(self.spec["status"], "VERIFIED_DOCUMENTARY_NOT_PROTOCOL_FROZEN")
        for config in (self.spec, self.roster, self.freeze):
            self.assertEqual(config["protocol_freeze_commit_sha"], "PENDING")
            self.assertIs(config["inspecsafe_inference_authorized"], False)
            for key, value in walk(config):
                if key == "protocol_freeze_commit_sha":
                    self.assertEqual(value, "PENDING")
                if key.endswith("status") and isinstance(value, str):
                    self.assertNotIn(value, {"PROTOCOL_FROZEN", "FROZEN", "VALIDATED"})

    def test_only_checklist_one_is_complete(self):
        checklist = self.roster["d9_checklist"]
        self.assertEqual(len(checklist), 8)
        for key, status in checklist.items():
            self.assertEqual(status, "COMPLETE" if key.startswith("1_") else "PENDING")
        self.assertTrue(all(v == "PENDING" for v in self.freeze["frozen_components"].values()))

    def test_runtime_specs_have_required_unvalidated_interface_fields(self):
        required = {"status", "framework", "transformers_support", "model_class", "processor_class",
                    "trust_remote_code", "documented_dtype", "device_mapping", "package_requirements",
                    "preprocessing_entry_point", "generation_entry_point", "evidence"}
        self.assertEqual(self.spec["runtime_validation_status"], "PENDING")
        for model in self.models:
            runtime = model["runtime"]
            self.assertLessEqual(required, runtime.keys())
            self.assertEqual(runtime["status"], "DOCUMENTED_NOT_RUNTIME_VALIDATED")
            self.assertTrue(runtime["package_requirements"])
        self.assertEqual([m["runtime"]["trust_remote_code"] for m in self.models],
                         [False, True, True, False, False, False])
        self.assertIn("Gemma4Unified", self.models[3]["runtime"]["model_class"])
        self.assertIn("MiniCPMV4_6", self.models[5]["runtime"]["model_class"])

    def test_spatial_classifications_and_unqualified_d5(self):
        self.assertEqual([m["spatial"]["status"] for m in self.models], [
            "UNCERTAIN_REQUIRES_EXTERNAL_GATE", "DOCUMENTED_BOX_AND_POINT", "DOCUMENTED_NATIVE_POINT",
            "UNCERTAIN_REQUIRES_EXTERNAL_GATE", "DOCUMENTED_NATIVE_BOX", "NO_DOCUMENTED_GENERIC_SPATIAL_INTERFACE",
        ])
        required = {"native_output_format", "coordinate_convention", "normalization_range",
                    "coordinate_origin", "bbox_ordering", "point_representation", "evidence"}
        for model in self.models:
            self.assertLessEqual(required, model["spatial"].keys())
            self.assertEqual(model["spatial"]["d5_box_qualification"], "NOT_YET_QUALIFIED")

    def test_ovis_exact_spatial_convention(self):
        spatial = self.models[1]["spatial"]
        self.assertEqual(spatial["normalization_range"], "[0,1)")
        self.assertEqual(spatial["coordinate_origin"], "top-left (0,0)")
        self.assertIn("<box>(x1,y1),(x2,y2)</box>", spatial["native_output_format"])
        self.assertEqual(spatial["point_representation"], "<point>(x,y)</point>")

    def test_official_coordinate_conflict_is_not_silently_resolved(self):
        self.assertIn("UNRESOLVED", self.models[0]["spatial"]["bbox_ordering"])
        self.assertIn("NOT_ESTABLISHED_FOR_EXACT_8B", self.models[0]["spatial"]["normalization_range"])
        self.assertIn("not transferred", self.models[0]["spatial"]["native_output_format"])
        conflict = next(i for i in self.spec["unresolved_items"] if i["id"] == "QWEN_BBOX_ORDER")
        self.assertEqual(conflict["status"], "UNRESOLVED")
        self.assertEqual(conflict["evidence"], ["qwen_grounding"])

    def test_classification_contract_keeps_existing_canonical_parser(self):
        for model in self.models:
            contract = model["classification_integration"]
            self.assertEqual(contract["status"], "SPECIFIED_NOT_QUALIFIED")
            self.assertEqual(contract["canonical_schema"], "schemas/canonical.schema.json")
            self.assertEqual(contract["canonical_parser"], 'safeshift.protocol.schema.parse_text(text, "classification")')
            self.assertTrue(contract["native_output_extraction"])
        self.assertIn("Do not subtract input length", self.models[1]["classification_integration"]["native_output_extraction"])

    def test_decoding_inventory_does_not_select_or_freeze_policy(self):
        self.assertEqual(self.spec["decoding_freeze_status"], "PENDING")
        for model in self.models:
            decoding = model["decoding"]
            self.assertEqual(decoding["status"], "SUPPORTED_DECODING_INVENTORY")
            self.assertEqual(decoding["policy_status"], "PENDING")
            self.assertEqual(decoding["selected_parameters"], {})
            self.assertEqual(set(decoding["parameters"]), {
                "temperature", "do_sample", "top_p", "top_k", "max_new_tokens", "repetition_penalty",
            })
            self.assertIn("runtime", decoding["seed_controls"])
        for model in self.freeze["primary_models"]:
            self.assertEqual(model["decoding_policy_id"], "PENDING")

    def test_preprocessing_remains_official_and_not_runtime_validated(self):
        required = {"official_processor", "resize_behavior", "image_token_handling",
                    "chat_template", "special_image_marker", "evidence"}
        for model in self.models:
            self.assertLessEqual(required, model["preprocessing"].keys())
            self.assertEqual(model["preprocessing"]["status"], "DOCUMENTED_NOT_RUNTIME_VALIDATED")
        for model in self.freeze["primary_models"]:
            self.assertEqual(model["preprocessing_id"], "PENDING")

    def test_precision_inventory_is_not_an_execution_selection(self):
        for model in self.models:
            inventory = model["precision_quantization"]
            self.assertLessEqual({"FP32", "BF16", "FP16", "8_bit", "4_bit", "AWQ", "GPTQ", "GGUF"}, inventory.keys())
            self.assertEqual(inventory["status"], "DOCUMENTED_NOT_RUNTIME_VALIDATED")
            self.assertEqual(inventory["selected_precision"], "PENDING")
            self.assertEqual(inventory["selected_quantization"], "PENDING")

    def test_final_roles_and_backup_activation_are_unchanged(self):
        self.assertEqual(self.spec["final_roles_status"], "PENDING")
        self.assertTrue(all(m["classification"] == "CANDIDATE" for m in self.roster["primary_models"]))
        self.assertTrue(all(m["classification_role"] == "PENDING_FINAL_GATE" for m in self.freeze["primary_models"]))
        self.assertEqual([m["replacement_status"] for m in self.roster["backups_in_order"]], ["BACKUP_1_ONLY", "BACKUP_2_ONLY"])
        for config in (self.roster, self.freeze):
            self.assertIs(config["point_only_policy"]["fabricate_boxes_from_points"], False)
            self.assertIs(config["point_only_policy"]["approved_d5_native_point_only_track"], False)
        policy = self.roster["replacement_policy"]["on_grounding_only_failure_with_valid_parseable_classification"]
        self.assertIs(policy["activate_backup_substitution"], False)
        self.assertIs(policy["assign_artificial_zero_iou"], False)

    def test_gate_stays_not_run_and_manifest_hash_unchanged(self):
        self.assertEqual(self.roster["synthetic_gate"]["status"], "NOT_RUN_FOR_D9_MODELS")
        self.assertEqual(self.freeze["synthetic_external_gate"]["status"], "PENDING_D9_MODEL_EXECUTION")
        for gate in (self.roster["synthetic_gate"], self.freeze["synthetic_external_gate"]):
            self.assertEqual(gate["manifest_sha256"], "fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379")

    def test_no_score_selection_or_inspecsafe_derived_metadata(self):
        # Fixed field allowlists prevent hiding a selection result in new fields.
        for model in self.models:
            self.assertEqual(set(model), SECTION_KEYS)
        for config in (self.spec, self.roster, self.freeze):
            for key, value in walk(config):
                self.assertIsNone(re.search(r"score|benchmark_result|selection_metric|inspecsafe_derived|sample_prediction", key, re.I), key)
                if key == "selection_basis":
                    self.assertEqual(value, "RESEARCH_VALUE_BEFORE_COMPUTE; NO_INSPECSAFE_PERFORMANCE_USED")
                if isinstance(value, str):
                    self.assertNotIn("data/raw/", value)
                    self.assertNotRegex(value, r"\b[A-Za-z]:[\\/]")

    def test_partial_output_inventory_does_not_promise_unavailable_bytes(self):
        for model in self.models:
            partial = model["partial_generation"]
            self.assertEqual(partial["blocking_generate"], "NO_PARTIAL_RETURN_GUARANTEE_ON_EXCEPTION")
            self.assertIn("GenerationFailure(partial_raw=...)", partial["contract"])
            self.assertIn("partial_raw=None", partial["contract"])
        self.assertIn("BudgetAwareTextStreamer", self.models[1]["partial_generation"]["streaming"])
        self.assertIn("incompatible", self.models[1]["partial_generation"]["streaming"])

    def test_repository_json_is_strict_and_status_docs_consistent(self):
        for path in CONFIG.glob("*.json"):
            strict_json(path.read_bytes())
        task = (ROOT / "TASKS.md").read_text(encoding="utf-8")
        self.assertIn("- [x] **1. Model provenance:**", task)
        for number in range(2, 9):
            self.assertIn(f"- [ ] **{number}.", task)
        note = (ROOT / "notes/w2_model_provenance_runner_spec.md").read_text(encoding="utf-8")
        self.assertIn("AC-A — Idempotent initialize/load", note)
        self.assertIn("AC-B — Partial generation evidence", note)
        self.assertIn("protocol_freeze_commit_sha = PENDING", note)


if __name__ == "__main__":
    unittest.main()
