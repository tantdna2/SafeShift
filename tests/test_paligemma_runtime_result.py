"""Static transcription/governance checks for Research Lead-verified D9R9 evidence."""

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/pre_freeze"


class PaliGemmaRuntimeResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((CONFIG / "paligemma_t4_runtime_result.v1.json").read_text())
        cls.plan = json.loads((CONFIG / "paligemma_t4_runtime.v1.json").read_text())

    def test_research_lead_source_and_immutable_identity(self):
        r = self.result
        self.assertEqual(r["record_kind"], "RESEARCH_LEAD_VERIFIED_RUNTIME_RESULT")
        self.assertIn("Codex did not inspect", r["source"]["recording_basis"])
        self.assertEqual(r["source"]["evidence_archive_sha256"],
                         "093b03cae9e654a26268fd2f7d474f3b9de40c2b6fa98d98c5f15d0bb586ba74")
        self.assertFalse(r["source"]["evidence_archive_committed"])
        self.assertFalse(r["source"]["raw_artifacts_committed"])
        self.assertEqual(r["model_id"], "google/paligemma-3b-mix-448")
        self.assertEqual(r["immutable_revision"], "ead2d9a35598cb89119af004f5d023b311d1c4a1")
        self.assertEqual(r["execution_commit"], "180c0623149bbc7d64f5b659f6c044c39b1e1cd0")
        self.assertEqual(r["plan_path"], "configs/pre_freeze/paligemma_t4_runtime.v1.json")

    def test_plan_software_and_snapshot_match_without_rewriting_history(self):
        r, p = self.result, self.plan
        canonical = json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), r["plan_sha256"])
        self.assertEqual(r["plan_sha256"], "4138071ff3fcbcf2cb16d456c01a2b3dbc42a628b0faa0d04dd6a635803b0ab7")
        self.assertEqual(r["software"], p["software"])
        self.assertEqual(r["software_status"], "EXACT_PLAN_MATCH")
        for key in ("pinned_file_count", "online_verified_file_count", "offline_verified_file_count"):
            self.assertEqual(r["snapshot_verification"][key], 14)
        self.assertTrue(r["snapshot_verification"]["local_bytes_verified"])
        self.assertTrue(r["snapshot_verification"]["exact_revision_verified"])
        self.assertEqual(p["real_runtime_status"], "NOT_RUN")
        self.assertFalse(p["exact_runtime_verified"])

    def test_hardware_offline_and_resource_contract(self):
        r = self.result
        self.assertEqual(r["hardware"], {"platform": "KAGGLE", "gpu_name": "Tesla T4",
            "visible_gpu_count": 1, "compute_capability": [7, 5], "total_vram_bytes": 15636037632,
            "device": "cuda:0", "cuda_runtime": "12.4"})
        for key, value in r["runtime_condition"].items():
            self.assertEqual(value, self.plan[key])
        self.assertTrue(r["offline"]["owner_internet_off_attested"])
        self.assertEqual(r["offline"]["offline_env_status"], "PASS")
        self.assertEqual(r["offline"]["variables"], {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1", "HF_HUB_ENABLE_HF_TRANSFER": "0", "HF_HUB_DISABLE_XET": "1"})

    def test_raw_observations_and_expected_pending_adapters(self):
        raw = self.result["raw_evidence"]
        self.assertEqual(raw["raw_before_adapter_status"], "PASS")
        self.assertEqual(raw["metadata_parse_status_before_adapter"], "NOT_ATTEMPTED")
        self.assertEqual(raw["classification_adapter_interpretation"], "EXPECTED_PENDING")
        expected = [("case_01", "blue", [8796, 1], "d40f43c73e9dc2139cee0f32f6db0db8cc012062ef96ffad07cefe90b5706bcc"),
                    ("case_02", "green", [9740, 1], "86629348e4c3b4fbe8513d20afebb9f49b3ef46fe7b7dc55a0a3322708bd80d5")]
        self.assertEqual(len(raw["calls"]), 2)
        for call, (call_id, text, ids, sha) in zip(raw["calls"], expected):
            self.assertEqual(call["call_id"], call_id)
            self.assertEqual(call["decoded_text"], text)
            self.assertEqual(call["decoded_with_special_tokens"], text + "<eos>")
            self.assertEqual(call["continuation_ids"], ids)
            self.assertEqual(call["raw_sha256"], sha)
            self.assertEqual(call["adapter_parse_status"], "INVALID")
            self.assertEqual(call["metadata_parse_status_before_adapter"], "NOT_ATTEMPTED")
            self.assertEqual(call["observation_status"], "OBSERVED_ONLY")
            self.assertFalse(call["loc_tokens_observed"])
        self.assertFalse(self.result["native_output_interpretation"]["classification_grammar_frozen"])
        self.assertEqual(self.result["native_output_interpretation"]["no_detection_behavior"], "NOT_TESTED_OR_FROZEN")

    def test_all_observed_timings_and_memory_are_preserved(self):
        r = self.result
        self.assertEqual(r["memory"], {"unit": "bytes", "after_load_allocated_bytes": 5860761600,
            "peak_allocated_bytes": 5997785600, "peak_reserved_bytes": 6161432576})
        t = r["timings"]
        self.assertEqual(t["harness_wall_seconds"], 72.795738743)
        self.assertEqual(t["load_seconds_including_snapshot_and_transfer"], 55.543600983)
        self.assertEqual(t["call_generation_seconds"], {"case_01": 1.893213143, "case_02": 0.571769282})
        self.assertEqual([m["wall_seconds"] for m in t["measurements"]],
                         [55.543600983, 0.000652138, 1.893213143, 0.000536080, 0.571769282])
        self.assertEqual(t["observer_errors"], [])
        self.assertEqual(t["unfinished_spans"], 0)

    def test_instrumentation_error_is_not_runtime_failure_or_reload(self):
        r, finding = self.result, self.result["timing_observer_finding"]
        self.assertEqual(r["status"], "RUNTIME_INTERFACE_PASS")
        self.assertEqual(r["real_runtime_status"], "RUNTIME_SMOKE_PASS")
        self.assertTrue(r["exact_runtime_verified"])
        self.assertEqual(r["lifecycle"]["model_load_count"], 1)
        self.assertEqual(r["lifecycle"]["native_generate_calls"], 2)
        self.assertEqual(r["lifecycle"]["runner_state"], "GENERATED")
        self.assertEqual(finding["classification"], "NOTEBOOK_INSTRUMENTATION_BUG_NOT_RUNTIME_FAILURE")
        self.assertEqual(finding["actual_model_load_count"], 1)
        self.assertEqual(finding["load_span_count"], 3)
        self.assertEqual(finding["idempotent_load_reentry_seconds"], [0.000652138, 0.000536080])
        self.assertFalse(finding["scientific_contract_changed"])
        self.assertFalse(finding["rerun_performed"])

    def test_runtime_pass_does_not_promote_scientific_qualification(self):
        r = self.result
        for field in ("grounding", "classification_interface", "external_gate"):
            self.assertEqual(r[field], "PENDING_QUALIFICATION")
        self.assertEqual(r["production_adapter_classification"], "INVALID")
        self.assertEqual(r["production_adapter_grounding"], "UNSUPPORTED")
        self.assertEqual(r["paligemma_role"], "BACKUP_1")
        self.assertEqual(r["primary_roster_count"], 4)
        self.assertEqual(r["protocol_freeze"], "PENDING")
        self.assertTrue(r["protocol_freeze_blocked"])
        for field in ("promotion", "grounding_executed", "inspecsafe_inference_authorized",
                      "synthetic_gate_executed", "inspecsafe_executed"):
            self.assertFalse(r[field])
        self.assertEqual(r["codex_execution"], {"gpu": False, "model": False, "provision": False})


if __name__ == "__main__":
    unittest.main()
