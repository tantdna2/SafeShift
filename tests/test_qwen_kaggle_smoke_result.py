"""Offline consistency of the supplied audit summary, not a replay of its evidence."""

import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "configs/pre_freeze"
EXECUTION = "784c465cae5188ed6ede5673140a4a281f2ffb52"


class SmokeResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((CONFIGS / "qwen_kaggle_smoke_result.v1.json").read_text(encoding="utf-8"))
        cls.plan = json.loads((CONFIGS / "qwen_kaggle_smoke.v1.json").read_text(encoding="utf-8"))
        provenance = json.loads((CONFIGS / "local_model_provenance.d9.json").read_text(encoding="utf-8"))
        cls.qwen = next(m for m in provenance["models"] if m["model_id"] == cls.result["model_id"])

    def test_audit_source_and_execution_identity(self):
        r = self.result
        self.assertEqual(r["run_id"], "kaggle-t4x2-20260923T012029667885Z")
        self.assertEqual(r["execution_commit"], EXECUTION)
        self.assertEqual(r["source"]["evidence_bundle_sha256"],
                         "ae3e9e1002ce94bf78bb0ac856f1a7f54a48283d64db51cdb8d5eed37f6b8a69")
        self.assertEqual(r["source"]["bundle_audited_by"], "Research Lead")
        self.assertIn("not independently inspected", r["source"]["recording_basis"])
        self.assertFalse(r["source"]["bundle_committed"])
        self.assertEqual(r["status"], "RUNTIME_SMOKE_PASS")

    def test_model_and_condition_match_unchanged_plan(self):
        r = self.result
        self.assertEqual(r["model_id"], "Qwen/Qwen3-VL-8B-Instruct")
        self.assertEqual(r["immutable_revision"], "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b")
        self.assertEqual(r["immutable_revision"], self.plan["revision"])
        self.assertEqual(r["immutable_revision"], self.qwen["immutable_revision"])
        for key in ("precision", "quantization", "device", "preprocessing", "decoding"):
            self.assertEqual(r["runtime_condition"][key], self.plan[key])
        self.assertEqual(r["runtime_condition"]["precision_status"], "VALIDATED_SMOKE_RUNTIME_CANDIDATE")
        self.assertEqual(r["runtime_condition"]["attention_implementation_observed"], "sdpa")

    def test_execution_config_and_prompt_hashes(self):
        # Git blob bytes avoid Windows checkout CRLF differences. No model files read.
        raw = subprocess.check_output(["git", "show", EXECUTION + ":" + self.result["smoke_config_path"]],
                                      cwd=ROOT)
        self.assertEqual(self.result["smoke_config_sha256"],
                         "ecd34ba5a8880458734e26f2bf0932f5f820607c2b9f3233b4e092980bf79ef9")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.result["smoke_config_sha256"])
        self.assertEqual(json.loads(raw), self.plan)
        self.assertEqual(self.result["prompt_sha256"],
                         "681fb3f051871bd9dd52a8100816f864ceb82ea0b5ac332bb2c7a22aed6bda48")
        self.assertEqual(hashlib.sha256(self.plan["prompt"].encode()).hexdigest(), self.result["prompt_sha256"])

    def test_four_weight_hashes_and_sizes_match_documentary_metadata(self):
        verification = self.result["local_weight_verification"]
        self.assertTrue(verification["LOCAL_WEIGHT_BYTES_VERIFIED"])
        self.assertEqual(verification["scope"], "THIS_RUN_ONLY_NOT_GLOBAL_OR_FROZEN_VERIFICATION")
        self.assertEqual(len(verification["files"]), 4)
        for local, documentary in zip(verification["files"], self.qwen["weight_provenance"]["files"]):
            self.assertEqual(local["path"], documentary["path"])
            self.assertEqual(local["sha256"], documentary["lfs_sha256"])
            self.assertEqual(local["size_bytes"], documentary["size_bytes"])
            self.assertTrue(local["sha256_and_size_match"])
        self.assertFalse(self.qwen["weight_provenance"]["local_bytes_verified"])
        self.assertEqual(self.qwen["precision_quantization"]["selected_precision"], "PENDING")

    def test_hardware_and_placement(self):
        h = self.result["hardware"]
        self.assertEqual(h["platform"], "KAGGLE")
        self.assertEqual(h["gpu_count"], 2)
        self.assertEqual(len(h["gpus"]), 2)
        for index, gpu in enumerate(h["gpus"]):
            self.assertEqual(gpu, {"index": index, "name": "Tesla T4", "memory_total_mib": 15360,
                                   "compute_capability": [7, 5]})
        self.assertEqual(h["driver_version"], "580.159.04")
        self.assertEqual(h["torch_cuda_runtime"], "12.8")
        placement = self.result["device_map_summary"]
        self.assertFalse(placement["cpu_offload"])
        self.assertFalse(placement["disk_offload"])
        self.assertEqual(placement["visual_encoder"], "cuda:0")
        self.assertEqual(placement["lm_head"], "cuda:1")

    def test_software_and_offline_environment(self):
        self.assertEqual(self.result["software_versions"], {
            "python": "3.12.13", "torch": "2.10.0+cu128", "transformers": "4.57.1",
            "accelerate": "1.11.0", "huggingface_hub": "0.36.0", "safetensors": "0.6.2",
            "pillow": "11.3.0", "zlib": "1.2.11"})
        self.assertEqual(self.result["environment"], {
            "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1"})

    def test_two_call_lifecycle_and_raw_hashes(self):
        self.assertEqual(self.result["lifecycle"], {"same_runner_instance": True, "load_lifecycles": 1,
                         "native_generate_calls": 2, "native_errors": [], "oom_observed": False})
        calls = self.result["calls"]
        self.assertEqual([c["sample_id"] for c in calls], ["RUNTIME_SMOKE_01", "RUNTIME_SMOKE_02"])
        self.assertEqual([c["input_sha256"] for c in calls], [
            "30e703660685855a5bd957938f5711c3b67532156844ed445c3e951ee2c429cf",
            "e4b3d272a708c3c2f1ca3c98a354a4f01716ecada1dbec4e42bcdb0d11dc4b18"])
        self.assertEqual([c["metadata_sha256"] for c in calls], [
            "e851fb01a9d590c08ecf05890276f0f0ff2c3c9f805d9a1052550878fdbbe97f",
            "02038e125dc60c0d92480c7dda89f8ffa4f287dddc3ea85d8f25de1f1e425a7b"])
        for call in calls:
            self.assertEqual(call["parse_status"], "SUCCESS")
            self.assertEqual(call["metadata_parse_status_before_adapter"], "NOT_ATTEMPTED")
            for key in ("cache_state_cleared", "raw_preserved", "metadata_preserved", "artifact_hashes_match_audited_files"):
                self.assertTrue(call[key])
            self.assertEqual(call["response_raw_sha256"],
                             "6c147f887f4c762b5dfcb5909b18e1de0acc54919fb1f56d15d0d7b7491fb9a0")

    def test_memory_diagnostics(self):
        m = self.result["memory_diagnostics"]
        self.assertEqual(m["unit"], "bytes")
        self.assertEqual(m["before_load_free"], {"gpu0": 15526068224, "gpu1": 15526068224})
        self.assertEqual(m["after_load_max_allocated"], {"gpu0": 7800528384, "gpu1": 9735371264})
        self.assertEqual(m["after_call_1_max_allocated"], {"gpu0": 7845763584, "gpu1": 9777359360})
        self.assertEqual(m["after_call_2_max_allocated"], m["after_call_1_max_allocated"])

    def test_claims_grounding_and_checklist_boundaries(self):
        r = self.result
        self.assertEqual(r["validation_scope"], "RUNTIME_INTERFACE_ONLY")
        self.assertEqual(r["task"], "classification")
        self.assertEqual(r["claims"], {key: False for key in (
            "capability_pass", "grounding_pass", "benchmark_result", "accuracy_result",
            "performance_benchmark", "decoding_frozen", "precision_frozen", "protocol_frozen")})
        self.assertEqual(r["qwen_grounding"], {"status": "UNCERTAIN_REQUIRES_EXTERNAL_GATE",
                                             "qualification": "NOT_YET_QUALIFIED"})
        self.assertEqual(r["qwen_grounding"]["qualification"], self.qwen["spatial"]["d5_box_qualification"])
        self.assertEqual(r["d9_checklist"], {"1": "COMPLETE_DOCUMENTARY", **{str(i): "PENDING" for i in range(2, 9)}})
        self.assertEqual(r["protocol_freeze_commit_sha"], "PENDING")
        self.assertEqual(r["synthetic_gate"], "NOT_RUN")
        self.assertEqual(r["inspecsafe_inference"], "NOT_RUN")
        roster = json.loads((CONFIGS / "local_models.d9.json").read_text(encoding="utf-8"))
        self.assertEqual(roster["d9_checklist"]["2_local_self_hosted_runners"], "PENDING")
        tasks = (ROOT / "TASKS.md").read_text(encoding="utf-8")
        self.assertIn("- [ ] **2. Runners:**", tasks)

    def test_summary_contains_no_embedded_runtime_artifacts(self):
        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertNotIn(key, {"raw_output", "decoded_for_parser", "decoded_with_special_tokens",
                                           "generated_ids_full", "continuation_ids", "safety_level",
                                           "image_bytes", "weights", "token"})
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        walk(self.result)


if __name__ == "__main__":
    unittest.main()
