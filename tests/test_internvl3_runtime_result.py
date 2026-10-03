"""Static checks for the Research Lead-supplied InternVL3 runtime record."""

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/pre_freeze"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class InternVL3RuntimeResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = load(CONFIG / "internvl3_t4_runtime_result.v1.json")
        cls.roster = load(CONFIG / "local_models.d9.json")
        cls.model = next(m for m in cls.roster["primary_models"] if m["key"] == "internvl3_2b_hf")

    def test_identity_and_research_lead_evidence(self):
        r = self.result
        self.assertEqual(r["run_id"], "internvl3-t4-smoke-20260928-01")
        self.assertEqual(r["execution_commit"], "088a7ff7f4d2c9fb6b72accc6922d02317643bdf")
        self.assertEqual(r["model_id"], "OpenGVLab/InternVL3-2B-hf")
        self.assertEqual(r["immutable_revision"], "cb57a075cb75a2e6d1b668b128d48bb00ae321d2")
        self.assertEqual(r["documentary_status"], "COMPLETE")
        self.assertEqual(r["offline_runner_status"], "COMPLETE")
        self.assertEqual(r["source"]["evidence_archive_sha256"], "e4de47ec85cc5770f97e987f282aa11eb9ea36b3cfb1c0f7e5b64ceac681a74d")
        self.assertEqual(r["source"]["summary_sha256"], "7edcd9219286bd84bde9a5453285e3e2f6cd9c7f839f2b6aa25e189f312c9edd")
        self.assertIn("Codex did not inspect", r["source"]["recording_basis"])
        self.assertFalse(r["source"]["evidence_archive_committed"])

    def test_runtime_resource_and_raw_boundaries(self):
        r = self.result
        self.assertEqual(r["status"], "RUNTIME_INTERFACE_PASS")
        self.assertEqual(r["runtime_smoke_status"], "PASS_VALIDATED")
        self.assertEqual(r["resource_status"], "PASS_VALIDATED")
        self.assertEqual(r["lifecycle"]["model_load_count"], 1)
        self.assertEqual(r["lifecycle"]["native_generate_calls"], 2)
        self.assertEqual(r["lifecycle"]["state_audits"], 8)
        self.assertTrue(r["lifecycle"]["state_audits_stable"])
        self.assertEqual(r["memory"], {"unit": "bytes", "peak_allocated_bytes": 4275527168, "peak_reserved_bytes": 4582277120})
        self.assertEqual(r["runtime_condition"], {
            "precision": "FP16", "quantization": "NONE", "batch_size": 1,
            "device": "cuda:0", "cpu_offload": False, "disk_offload": False,
            "automatic_precision_fallback": False,
            "automatic_quantization_fallback": False, "model_substitution": False})
        self.assertTrue(r["raw_evidence"]["raw_before_parse_verified"])
        self.assertEqual(r["raw_evidence"]["metadata_parse_status_before_adapter"], "NOT_ATTEMPTED")
        self.assertEqual(r["raw_evidence"]["summary_listed_artifact_count"], 11)

    def test_snapshot_and_plan(self):
        r = self.result
        self.assertEqual(r["plan_sha256"], "c2ad3137fbdba8809f2d86b75c6869955d51d462431905a7796cf109d1bf65b6")
        plan = load(ROOT / r["plan_path"])
        canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), r["plan_sha256"])
        self.assertEqual(r["snapshot_verification"]["pinned_file_count"], 14)
        self.assertTrue(r["snapshot_verification"]["local_bytes_verified"])
        self.assertTrue(r["snapshot_verification"]["exact_revision_verified"])
        self.assertIn("not byte-identical", r["snapshot_verification"]["manifest_semantics"])

    def test_grounding_ineligibility_does_not_become_gate_failure(self):
        r, m = self.result, self.model
        self.assertEqual(r["grounding_eligibility"]["grounding"], "NOT_PARTICIPATING")
        self.assertEqual(r["grounding_eligibility"]["grounding_failure_reason"], "NO_DOCUMENTED_GENERIC_SPATIAL_INTERFACE")
        self.assertEqual(r["external_gate"]["external_gate_status"], "NOT_RUN")
        self.assertEqual(r["external_gate"]["execution_status"], "NOT_RUN")
        self.assertEqual(r["external_gate"]["synthetic_gate_cases_executed"], 0)
        self.assertFalse(r["grounding_eligibility"]["point_to_box_conversion"])
        self.assertFalse(r["grounding_eligibility"]["prompt_trick"])
        self.assertFalse(r["grounding_eligibility"]["artificial_zero_iou"])
        self.assertFalse(r["grounding_eligibility"]["backup_substitution"])
        self.assertNotEqual(r["external_gate"]["external_gate_status"], "GATE_FAIL")
        self.assertEqual(m["grounding"], "NOT_PARTICIPATING")
        self.assertEqual(m["grounding_failure_reason"], "NO_DOCUMENTED_GENERIC_SPATIAL_INTERFACE")
        self.assertEqual(m["external_gate_status"], "NOT_RUN")

    def test_d9r5_decision_approves_only_the_interface_ineligible_mapping(self):
        decision = (ROOT / "DECISIONS.md").read_text(encoding="utf-8")
        record = decision.split("## D9R5 InternVL3 interface-ineligible grounding semantics", 1)[1]
        self.assertIn("grounding_failure_reason=NO_DOCUMENTED_GENERIC_SPATIAL_INTERFACE", record)
        self.assertIn("external_gate_status=NOT_RUN", record)
        self.assertIn("synthetic_gate_cases_executed=0", record)
        self.assertIn("NOT_PARTICIPATING", record)
        self.assertIn("classification remains `CANDIDATE`", record)
        self.assertIn("must not be recorded as `SPATIAL_GATE_FAILURE` or `GATE_FAIL`", record)
        self.assertIn("all four primaries executed the gate", record)

    def test_classification_adapter_and_checklist_boundaries(self):
        r, m = self.result, self.model
        self.assertEqual(r["classification_status"], "CANDIDATE")
        self.assertEqual(m["classification"], "CANDIDATE")
        self.assertEqual(r["production_adapter_status"], "NOT_QUALIFIED")
        self.assertEqual(r["production_adapter_classification"], "INVALID")
        # Preserve the runtime result's NOT_QUALIFIED/INVALID above; the current
        # D9R19 classification adapter is separately implemented, not gate rescue.
        self.assertEqual(m["production_adapter_status"], "CLASSIFICATION_IMPLEMENTED_GROUNDING_NOT_QUALIFIED")
        self.assertEqual(m["production_adapter_classification"], "IMPLEMENTED_STRICT_SYNTHETIC_VALIDATED")
        self.assertEqual(r["d9_checklist"]["2_local_self_hosted_runners"], "COMPLETE")
        self.assertEqual(r["d9_checklist"]["5_synthetic_gate_four_primary_models"], "COMPLETE")
        for key in ("3_low_variance_decoding_per_model", "4_deterministic_native_output_adapters",
                    "6_final_model_roles_and_backup_substitutions",
                    "7_freeze_prompts_schema_adapters_runner_metric_engine",
                    "8_record_protocol_freeze_commit"):
            self.assertEqual(r["d9_checklist"][key], "PENDING")
        self.assertFalse(r["inspecsafe_used"])
        self.assertFalse(r["inspecsafe_inference_authorized"])
        self.assertEqual(r["protocol_freeze_commit_sha"], "PENDING")


if __name__ == "__main__":
    unittest.main()
