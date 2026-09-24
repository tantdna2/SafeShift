"""Offline audit-summary consistency only; no external bundle or runtime access."""

import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "configs/pre_freeze"
EXECUTION = "c2a5d97945b27d16425f82592a352722ee935118"


class OvisSmokeResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads((CONFIGS / "ovis_gpu_smoke_result.v1.json").read_text(encoding="utf-8"))
        cls.plan = json.loads((CONFIGS / "ovis_gpu_smoke.v1.json").read_text(encoding="utf-8"))
        cls.provenance = json.loads((CONFIGS / "local_model_provenance.d9.json").read_text(encoding="utf-8"))
        cls.ovis = next(m for m in cls.provenance["models"] if m["model_id"] == "AIDC-AI/Ovis2.5-9B")

    def test_audit_scope_run_and_immutable_execution_identity(self):
        r = self.result
        self.assertEqual(r["schema_version"], "ovis-gpu-smoke-result-summary-v1")
        self.assertEqual(r["status"], "RUNTIME_SMOKE_PASS")
        self.assertEqual(r["validation_scope"], "RUNTIME_INTERFACE_ONLY")
        self.assertEqual(r["run_id"], "ckey-a40-ovis-20260924T042034999220552Z")
        for key in ("execution_commit", "B2B_PREP_HEAD", "git_commit", "execution_pin"):
            self.assertEqual(r[key], EXECUTION)
        self.assertTrue(r["execution_identity_verified"])
        self.assertIn("PR #26 body: RESULT_RECORDING_COMMIT", r["result_recording_commit_reference"])
        self.assertNotIn("result_recording_commit", r)  # no self-referential SHA
        self.assertEqual(r["source"]["bundle_audited_by"], "Research Lead")
        self.assertIn("not independently inspected", r["source"]["recording_basis"])

    def test_evidence_bundle_identity_members_and_retention(self):
        r = self.result
        self.assertEqual(r["evidence_bundle_filename"], "ovis_gpu_smoke_evidence.zip")
        self.assertEqual(r["evidence_bundle_sha256"],
                         "f6b4756d3e57a213e6302f3170de10c46d334865aed5735ea906647ede46ce76")
        expected = [f"calls/RUNTIME_SMOKE_0{i}/{name}" for i in (1, 2)
                    for name in ("metadata.json", "response.raw")]
        expected += ["case_manifest.json", "critical_file_verification.json",
                     "environment.json", "runtime_report.json",
                     "snapshot_verification.json", "weight_verification.json"]
        self.assertEqual(r["evidence_bundle_members"], expected)
        self.assertFalse(r["source"]["bundle_committed"])
        self.assertFalse(r["source"]["raw_runtime_artifacts_committed"])

    def test_exact_model_and_unchanged_smoke_condition(self):
        r = self.result
        self.assertEqual(r["model_id"], "AIDC-AI/Ovis2.5-9B")
        self.assertEqual(r["requested_model_id"], r["model_id"])
        self.assertEqual(r["resolved_repository_id"], "ATH-MaaS/Ovis2.5-9B")
        self.assertEqual(r["revision"], "d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd")
        self.assertEqual(r["revision"], self.ovis["immutable_revision"])
        self.assertEqual(r["runner_version"], "ovis2-5-runner-v2")
        for key in ("model_id", "resolved_repository_id", "revision", "precision",
                    "quantization", "device", "thinking", "decoding"):
            self.assertEqual(r[key], self.plan[key])
        self.assertEqual((r["precision"], r["quantization"], r["device"]),
                         ("BF16", "NONE", {"placement": "cuda:0"}))
        self.assertEqual(r["thinking"], {"enable_thinking": False, "enable_thinking_budget": False})
        self.assertEqual(r["decoding"], {"do_sample": False, "max_new_tokens": 32})

    def test_config_hash_matches_execution_git_blob_and_prompt(self):
        # Read Git object bytes, not Windows working-tree line endings or host files.
        raw = subprocess.check_output(
            ["git", "show", EXECUTION + ":" + self.result["smoke_config_path"]], cwd=ROOT)
        self.assertEqual(self.result["smoke_config_sha256"],
                         "52fc7a3a10fb47124bf51883de8017d39fde8c906ad6a150fdc880106478cb75")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.result["smoke_config_sha256"])
        self.assertEqual(json.loads(raw), self.plan)
        self.assertEqual(self.result["prompt_sha256"],
                         "681fb3f051871bd9dd52a8100816f864ceb82ea0b5ac332bb2c7a22aed6bda48")
        self.assertEqual(hashlib.sha256(self.plan["prompt"].encode()).hexdigest(),
                         self.result["prompt_sha256"])

    def test_a40_capability_hardware(self):
        h = self.result["hardware"]
        self.assertEqual(h, {
            "accelerator_requirement": "NVIDIA_SINGLE_GPU_BF16_MIN_40GB",
            "name": "NVIDIA A40", "visible_gpu_count": 1, "logical_device_index": 0,
            "total_memory_bytes": 47708110848, "nvidia_smi_memory_total_mib": 46068,
            "compute_capability": [8, 6], "bf16_supported": True,
            "driver_version": "570.195.03", "mig_mode": "N/A",
        })
        self.assertGreaterEqual(h["total_memory_bytes"], self.plan["hardware"]["min_total_memory_bytes"])
        self.assertGreaterEqual(tuple(h["compute_capability"]), (8, 0))
        self.assertEqual(h["accelerator_requirement"], self.plan["accelerator_requirement"])

    def test_software_runtime_and_build_toolkit_are_distinct(self):
        self.assertEqual(self.result["software_versions"], {
            "python": "3.11.16", "torch_distribution": "2.4.0", "torch": "2.4.0+cu121",
            "torch_cuda_runtime": "12.1", "transformers": "4.51.3", "numpy": "1.25.0",
            "pillow": "10.3.0", "flash_attn": "2.7.0.post2", "moviepy": "1.0.3",
            "huggingface_hub": "0.36.2",
        })
        self.assertEqual(self.result["environment_build_note"]["host_cuda_toolkit"], "12.4")
        self.assertEqual(self.result["environment_build_note"]["python_policy"],
                         "SAFESHIFT_SELECTED_SMOKE_ENVIRONMENT_CANDIDATE")

    def test_attention_is_eager_despite_installed_flash_attn(self):
        a = self.result["attention"]
        self.assertEqual(a["plan"], "DOCUMENTED_FLASH_ATTN_RECIPE")
        self.assertEqual(a["effective"], "eager")
        self.assertEqual(a["observations"], [
            {"source": "model.config._attn_implementation", "value": "eager"},
            {"source": "model.llm.config._attn_implementation", "value": "eager"},
        ])
        self.assertEqual(a["package_observation"], "FLASH_ATTN_PACKAGE_INSTALLED")
        self.assertEqual(a["effective_observation"], "EFFECTIVE_ATTENTION_OBSERVED_EAGER")
        for key in ("runner_override", "blocking", "flash_attention_actually_used_claim"):
            self.assertFalse(a[key])

    def test_snapshot_and_weight_verification_is_run_scoped(self):
        s = self.result["snapshot_verification"]
        self.assertTrue(s["LOCAL_SNAPSHOT_VERIFIED"])
        self.assertTrue(s["SNAPSHOT_PATH_VERIFIED"])
        self.assertEqual(s["expected_cache_suffix"],
                         "models--ATH-MaaS--Ovis2.5-9B/snapshots/" + self.result["revision"])
        self.assertEqual(s["operation"], {
            "mode": "RUNTIME_OFFLINE_REVERIFICATION", "local_files_only": True,
            "network_firewall_enabled": True, "network_violation_count_at_verification": 0,
        })
        self.assertEqual(s["component_verdicts"], {k: True for k in (
            "snapshot_path", "weight_bytes", "critical_provenance_hashes", "required_local_assets")})
        w = self.result["weight_verification"]
        self.assertTrue(w["LOCAL_WEIGHT_BYTES_VERIFIED"])
        self.assertEqual(w["scope"], "THIS_RUN_ONLY_NOT_GLOBAL_OR_FROZEN_VERIFICATION")
        self.assertEqual(len(w["files"]), 4)
        for actual, expected in zip(w["files"], self.ovis["weight_provenance"]["files"]):
            self.assertEqual(actual, {"path": expected["path"], "sha256": expected["lfs_sha256"],
                                     "size_bytes": expected["size_bytes"], "sha256_and_size_match": True})
        self.assertEqual(sum(f["size_bytes"] for f in w["files"]), 18349727512)
        self.assertFalse(self.ovis["weight_provenance"]["local_bytes_verified"])
        self.assertEqual(self.ovis["precision_quantization"]["selected_precision"], "PENDING")

    def test_critical_source_hashes_and_local_only_assets(self):
        c = self.result["critical_file_verification"]
        self.assertTrue(c["CRITICAL_PROVENANCE_HASHES_VERIFIED"])
        self.assertTrue(c["REQUIRED_LOCAL_ASSETS_PRESENT"])
        self.assertEqual([f["path"] for f in c["files"]], [
            "README.md", "config.json", "preprocessor_config.json",
            "generation_config.json", "modeling_ovis2_5.py",
        ])
        for row in c["files"]:
            self.assertEqual(row["sha256"], self.provenance["sources"][
                "ovis2_5_9b." + row["path"]]["content_sha256"])
            self.assertEqual(row["verification_status"], "VERIFIED_AGAINST_PROVENANCE")
        other = c["other_required_assets"]
        self.assertEqual(other["verification_status"], "RECORDED_LOCAL_HASH_ONLY")
        self.assertFalse(other["verified_against_provenance"])
        self.assertFalse(other["local_hashes_in_summary"])
        self.assertEqual(other["paths"], [
            "configuration_ovis2_5.py", "tokenizer_config.json", "tokenizer.json",
            "vocab.json", "merges.txt", "special_tokens_map.json", "added_tokens.json",
            "chat_template.json", "model.safetensors.index.json",
        ])

    def test_network_lifecycle_and_failure_state(self):
        r = self.result
        self.assertEqual(r["network_violation_count"], 0)
        self.assertEqual(r["native_errors"], [])
        self.assertEqual(r["notes"], [])
        for key in ("blocker", "runtime_check_failure", "rerun_of", "rerun_reason"):
            self.assertIsNone(r[key])
        self.assertFalse(r["online_retry"])
        self.assertFalse(r["fallback"])
        self.assertEqual((r["runner_instances"], r["load_lifecycles"], r["native_generate_calls"]), (1, 1, 2))
        self.assertEqual(r["call_order"], "SEQUENTIAL_CLASSIFICATION_ONLY")

    def test_two_calls_exact_hashes_and_raw_before_parse(self):
        calls = self.result["calls"]
        self.assertEqual(len(calls), 2)
        expected = [
            ("call_01", "RUNTIME_SMOKE_01",
             "eafc937f391461f0b29816f3a69654041ec77d543860705cc49a19941785a7bb",
             "5c64dcbe4cb05b1cd2b9cc06a731fee7ae761bd246607f5a86c73d878738bf5a"),
            ("call_02", "RUNTIME_SMOKE_02",
             "91b0fc7fd00e1d279c10218c4a54d922302e369ac5c5afdfa35cae618451e73a",
             "6cbf46a19ee5462369fe16ba4bcb353f438f1883ee24e2b42fa87d2b5b1dfd4f"),
        ]
        for call, values in zip(calls, expected):
            self.assertEqual(tuple(call[k] for k in (
                "call_id", "sample_id", "input_image_sha256", "metadata_sha256")), values)
            self.assertEqual(call["parse_status"], "SUCCESS")
            self.assertEqual(call["task"], "classification")
            self.assertIsNone(call["error"])
            self.assertEqual(call["metadata_size_bytes"], 2778)
            self.assertEqual(call["raw_size_bytes"], 4156)
            self.assertEqual(call["raw_sha256"],
                             "d3d0b69070ddbd8628e5a90792f1e9b5d43643837c996c85fc87aaad91b20021")
            self.assertEqual(call["raw_metadata_before_adapter"], {
                "parse_status": "NOT_ATTEMPTED", "source_kind": "HANDCRAFTED_RUNTIME_SMOKE",
                "task": "classification",
            })

    def test_identical_outputs_have_no_semantic_conclusion(self):
        calls = self.result["calls"]
        self.assertNotEqual(calls[0]["input_image_sha256"], calls[1]["input_image_sha256"])
        self.assertEqual(calls[0]["raw_sha256"], calls[1]["raw_sha256"])
        self.assertEqual(self.result["output_observation"], {
            "input_hashes_distinct": True, "raw_hashes_identical": True,
            "decoded_safety_level": "Level01", "special_token_suffix": "<|im_end|>",
            "semantic_interpretation": "NONE_RUNTIME_OBSERVATION_ONLY",
            "model_ignored_image_inference": False, "semantic_correctness_claim": False,
        })

    def test_parameter_placement_and_bf16_census(self):
        p, d = self.result["parameter_placement"], self.result["dtype_evidence"]
        totals = {"tensor_count": 840, "numel": 9174807784, "bytes": 18349615568}
        self.assertTrue(p["passed"])
        self.assertEqual(p["expected_device"], "cuda:0")
        self.assertEqual(p["distinct_parameter_devices"], ["cuda:0"])
        self.assertEqual(p["total"], totals)
        self.assertEqual(p["by_device"], {"cuda:0": totals})
        self.assertEqual(p["violations"], [])
        for key in ("cpu_offload", "meta_parameters", "multi_gpu"):
            self.assertFalse(p[key])
        self.assertTrue(d["passed"])
        self.assertEqual(d["status"], "EXPECTED_BF16_ONLY")
        self.assertEqual(d["expected_primary_dtype"], "torch.bfloat16")
        self.assertEqual(d["floating_parameter_census"], {"torch.bfloat16": totals})
        self.assertEqual(d["deviations"], {})
        self.assertFalse(d["silent_cast"])

    def test_memory_diagnostics_no_oom_or_performance_claim(self):
        m = self.result["memory_summary"]
        self.assertEqual(m["unit"], "bytes")
        self.assertFalse(m["oom_observed"])
        self.assertFalse(m["performance_claim"])
        self.assertEqual([s["stage"] for s in m["stages"]],
                         ["before_load", "after_load", "after_call_1", "after_call_2"])
        self.assertEqual(m["stages"][0], {"stage": "before_load", "free_bytes": 47428993024,
                         "total_bytes": 47708110848, "memory_allocated": 0, "memory_reserved": 0})
        self.assertEqual(m["stages"][1], {
            "stage": "after_load", "free_bytes": 28976152576, "memory_allocated": 18359789568,
            "memory_reserved": 18452840448, "max_memory_allocated": 18359789568,
            "max_memory_reserved": 18452840448,
        })
        for index in (1, 2):
            self.assertEqual(m["stages"][index + 1], {
                "stage": f"after_call_{index}", "free_bytes": 28598665216,
                "memory_allocated": 18368309248, "memory_reserved": 18763218944,
                "max_memory_allocated": 18511427584, "max_memory_reserved": 18763218944,
            })

    def test_research_claims_grounding_and_checklist_remain_pending(self):
        r = self.result
        self.assertEqual(r["claims"], {key: False for key in (
            "capability_pass", "grounding_pass", "accuracy_pass", "benchmark_pass",
            "precision_frozen", "decoding_frozen", "thinking_frozen", "protocol_frozen")})
        self.assertEqual(r["ovis_grounding"], {
            "status": "DOCUMENTED_BOX_AND_POINT", "qualification": "NOT_YET_QUALIFIED"})
        self.assertEqual(self.ovis["spatial"]["d5_box_qualification"], "NOT_YET_QUALIFIED")
        self.assertEqual(r["d9_checklist"], {"1": "COMPLETE_DOCUMENTARY",
                                           **{str(i): "PENDING" for i in range(2, 9)}})
        self.assertEqual(r["runner_progress"], {
            "qwen": {"offline": "COMPLETE", "runtime": "PASS_VALIDATED"},
            "ovis": {"offline": "COMPLETE", "runtime": "PASS_VALIDATED"},
            "molmo": "PENDING", "gemma": "PENDING",
        })
        self.assertEqual(r["protocol_freeze_commit_sha"], "PENDING")
        self.assertEqual(r["synthetic_gate"], "NOT_RUN")
        self.assertEqual(r["inspecsafe_inference"], "NOT_RUN")
        roster = json.loads((CONFIGS / "local_models.d9.json").read_text(encoding="utf-8"))
        self.assertEqual(roster["d9_checklist"]["2_local_self_hosted_runners"], "PENDING")
        self.assertIn("- [ ] **2. Runners:**", (ROOT / "TASKS.md").read_text(encoding="utf-8"))

    def test_summary_has_no_embedded_raw_envelope_or_absolute_host_paths(self):
        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertNotIn(key, {"raw_output", "decoded_for_parser", "decoded_with_special_tokens",
                                          "generated_ids_full", "continuation_ids", "image_bytes",
                                          "weights", "token", "safety_level"})
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
            elif isinstance(value, str):
                self.assertFalse(value.startswith(("/", "C:\\", "D:\\", "file://")))
        walk(self.result)


if __name__ == "__main__":
    unittest.main()
