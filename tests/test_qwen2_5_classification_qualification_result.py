"""Offline transcription/invariant checks, not raw-bundle audit or model replay."""

from collections import Counter
import hashlib
from pathlib import Path
import subprocess
import unittest

from safeshift.protocol.schema import strict_json
from safeshift.qualification.classification import evaluate


ROOT = Path(__file__).resolve().parents[1]
BASE = "7154c6187de7d8ecc5ad4ac5d0aafb68d2d7c1ab"
RESULT = "configs/pre_freeze/qwen2_5_classification_qualification_result.v1.json"
MANIFEST = "configs/pre_freeze/classification_qualification_cases.v1.json"
PLAN = "configs/pre_freeze/classification_qualification_plan.v1.json"
RAW_LEVEL01 = "e532d76fa9108286b11484b9f307245cc8507e7cd4797b57d71b8e82a57880cd"
RAW_LEVEL03 = "e9d745289442445578867edaf046f305de870b1409c07e49e4ab67945168fcb9"


def load(path):
    return strict_json((ROOT / path).read_bytes())


def base_bytes(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)


class Qwen25ClassificationResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = load(RESULT)

    def test_exact_execution_identity_and_authorization(self):
        r = self.result
        self.assertEqual(r["schema_version"], "qwen2-5-classification-qualification-result-v1")
        self.assertEqual(r["task"], "W2.6-D9R17A-QWEN2_5-CLASSIFICATION-QUALIFICATION-RESULT")
        self.assertEqual(r["model_id"], "Qwen/Qwen2.5-VL-3B-Instruct")
        self.assertEqual(r["immutable_revision"], "66285546d2b821cf421d4f5eb2576359d3770cd3")
        self.assertEqual(r["execution_commit"], BASE)
        self.assertEqual(r["recording_base_sha"], BASE)
        self.assertEqual(r["run_id"], "d9r17a-qwen2_5-classification")
        self.assertEqual(r["execution_authorization"],
                         "DEC-W2-D9R17A-QWEN2_5-CLASSIFICATION-QUALIFICATION-EXEC-001")
        self.assertEqual(r["suite"], "external-classification-qualification-v1")
        self.assertEqual(r["source_kind"], "EXTERNAL_CLASSIFICATION_QUALIFICATION")

    def test_bundle_identity_and_recording_authority_are_explicit(self):
        r = self.result
        self.assertEqual(r["record_kind"], "RESEARCH_LEAD_VERIFIED_REAL_CLASSIFICATION_QUALIFICATION_RESULT")
        source = r["source"]
        self.assertEqual(source["authority"], "RESEARCH_LEAD")
        self.assertEqual(source["bundle_sha256"],
                         "aa30fd9b19ead3889595394eb8499699233bfceb483446e05b342b15149d72e1")
        self.assertIn("Research Lead directly inspected", source["recording_basis"])
        self.assertIn("did not independently inspect or rehash", source["recording_basis"])
        self.assertIs(source["independent_bundle_inspection_by_codex"], False)
        self.assertIs(source["bundle_and_raw_bytes_committed"], False)

    def test_semantic_failure_is_separate_from_runtime_and_role(self):
        r = self.result
        self.assertEqual(r["run_status"], "FAIL")
        self.assertEqual(r["causes"], ["SEMANTIC_CLASSIFICATION_FAILURE"])
        self.assertIsNone(r["runtime_failure"])
        self.assertEqual(r["review_status"], "PENDING_REVIEW")
        self.assertEqual(r["model_role_after_run"], "PENDING_RESEARCH_LEAD_REVIEW")
        self.assertEqual(r["classification_participation_decision"], "PENDING")
        for field in ("roster_membership_changed", "production_adapter_promoted", "automatic_rerun",
                      "real_model_rerun", "model_execution_by_recording_agent"):
            self.assertIs(r[field], False, field)

    def test_exact_ordered_cases_and_decoded_strings(self):
        cases = self.result["cases"]
        expected = ["Level01", "Level01", "Level02", "Level02", "Level03", "Level03", "Level04", "Level04"]
        observed = ["Level01", "Level01", "Level01", "Level01", "Level03", "Level01", "Level01", "Level01"]
        self.assertEqual([c["case_id"] for c in cases], [f"cq_{i:02d}" for i in range(1, 9)])
        self.assertEqual([c["expected_safety_level"] for c in cases], expected)
        self.assertEqual([c["observed_canonical"] for c in cases], observed)
        self.assertEqual([c["expected_safety_level"] for c in load(MANIFEST)["cases"]], expected)
        for case, exp, obs in zip(cases, expected, observed):
            with self.subTest(case=case["case_id"]):
                self.assertEqual(case["parse_status"], "SUCCESS")
                self.assertEqual(case["decoded_for_parser"], '{"safety_level":"' + obs + '"}')
                self.assertIs(case["correct"], exp == obs)

    def test_summary_counts_are_descriptive_and_derived_from_cases(self):
        r = self.result
        summary = r["summary"]
        self.assertEqual(summary, {
            "total_cases": 8, "format_parser_status": "SUCCESS", "parse_success_count": 8,
            "exact_expected_count": 3,
            "semantic_expected_match_scope": "DESCRIPTIVE_QUALIFICATION_EVIDENCE_ONLY",
            "observed_canonical_counts": {"Level01": 7, "Level02": 0, "Level03": 1, "Level04": 0},
        })
        self.assertEqual(len(r["cases"]), summary["total_cases"])
        self.assertEqual(sum(c["parse_status"] == "SUCCESS" for c in r["cases"]), 8)
        self.assertEqual(sum(c["correct"] for c in r["cases"]), 3)
        self.assertEqual(Counter(c["observed_canonical"] for c in r["cases"]),
                         Counter(summary["observed_canonical_counts"]))
        self.assertIs(r["NOT_ACCURACY_BENCHMARK"], True)
        self.assertIs(r["ranking_models"], False)

    def test_existing_verdict_function_agrees_without_model_or_parser_replay(self):
        # Only the pure verdict function; no fabricated envelopes or raw verification.
        cases = [(case, b"") for case in load(MANIFEST)["cases"]]
        rows = [{"case_id": c["case_id"], "parse_status": c["parse_status"],
                 "safety_level": c["observed_canonical"],
                 "raw_output": {"sha256": c["raw_sha256"], "size_bytes": c["raw_size_bytes"]}}
                for c in self.result["cases"]]
        verdict = evaluate(cases, rows, runtime_failure=None)
        for key, value in verdict.items():
            self.assertEqual(self.result[key], value, key)
        self.assertEqual(self.result["prospective_contract"]["required_exact_expected_count"], 8)
        self.assertIn("8_EXACT_EXPECTED_LEVELS", load(PLAN)["pass_requires"])

    def test_exact_raw_hashes_sizes_and_pre_parser_attestation(self):
        for c in self.result["cases"]:
            self.assertEqual(c["raw_sha256"], RAW_LEVEL03 if c["case_id"] == "cq_05" else RAW_LEVEL01)
            self.assertEqual(c["raw_size_bytes"], 7418)
        self.assertEqual(self.result["raw_evidence"], {
            "verification_authority": "RESEARCH_LEAD", "scope": "ALL_EIGHT_RAW_OUTPUTS",
            "persisted_before_parser": True, "sha256_matches_result_records": True,
            "size_matches_result_records": True, "metadata_parse_status_before_parser": "NOT_ATTEMPTED",
            "metadata_source_kind": "EXTERNAL_CLASSIFICATION_QUALIFICATION",
            "parser_repair": False, "markdown_stripping": False, "retry_count": 0, "alternate_prompt": False,
        })

    def test_exact_call_counts_hardware_and_precision(self):
        runtime = self.result["runtime_evidence"]
        self.assertEqual(runtime["verification_authority"], "RESEARCH_LEAD")
        self.assertEqual((runtime["model_loads"], runtime["classification_calls"], runtime["grounding_calls"]),
                         (1, 8, 0))
        self.assertEqual(runtime["hardware"], {
            "gpu_name": "Tesla T4", "visible_gpu_count": 1, "used_device": "cuda:0",
            "compute_capability": [7, 5], "total_vram_bytes": 15636037632, "torch_cuda_version": "12.4",
        })
        self.assertEqual((runtime["precision"], runtime["quantization"]), ("FP16", "NONE"))

    def test_exact_software_and_snapshot_pins(self):
        runtime = self.result["runtime_evidence"]
        self.assertEqual(runtime["software_versions"], {
            "python": "3.11.11", "torch": "2.6.0+cu124", "torchvision": "0.21.0+cu124",
            "transformers": "4.51.3", "qwen-vl-utils": "0.0.8", "accelerate": "1.6.0",
            "pillow": "11.2.1", "huggingface-hub": "0.30.2", "tokenizers": "0.21.1", "safetensors": "0.5.3",
        })
        snapshot = runtime["snapshot"]
        self.assertIs(snapshot["local_bytes_verified"], True)
        self.assertEqual(snapshot["scope"], "RESEARCH_LEAD_VERIFIED_EXECUTION_EVIDENCE_NOT_A_NEW_CODEX_SNAPSHOT_CHECK")
        self.assertEqual(snapshot["total_bytes"], 7520918095)
        self.assertEqual(snapshot["weight_shards"], [
            {"path": "model-00001-of-00002.safetensors",
             "sha256": "41a8895c164b4d32bae6b302f4603fcbc1797f32dafa45c7e9bcda23c6755df8"},
            {"path": "model-00002-of-00002.safetensors",
             "sha256": "365531ff8752420e89dee707b79d021fb2d6e25abafe486f080555a4fe6972e4"},
        ])

    def test_offline_claim_is_limited_to_supplied_attestation_and_guards(self):
        self.assertEqual(self.result["runtime_evidence"]["offline_evidence"], {
            "venue_internet_off": "ATTESTED_BY_EXECUTION_ATTEMPT",
            "existing_runtime_offline_environment_enforced": True,
            "existing_network_denial_guards_enforced": True,
            "scope": "EXECUTION_ATTESTATION_AND_EXISTING_RUNTIME_GUARDS_ONLY",
        })

    def test_prospective_manifest_and_plan_are_byte_unchanged(self):
        contract = self.result["prospective_contract"]
        for key, path, sha in (
            ("manifest", MANIFEST, "3b7c3ebdec0736580bbad27f782496e318372cda6c3a4f322c4cc19ca5749e92"),
            ("plan", PLAN, "c2e8990227e7378368b986352d88fe6c9975769cdeccda346e3070d321d77160"),
        ):
            raw = (ROOT / path).read_bytes()
            self.assertEqual(raw, base_bytes(path))  # No newline normalization for these byte-pinned files.
            self.assertEqual(hashlib.sha256(raw).hexdigest(), sha)
            self.assertEqual(contract[key + "_path"], path)
            self.assertEqual(contract[key + "_sha256"], sha)
        self.assertEqual(contract["hash_basis"], "REPOSITORY_BYTES_AT_RECORDING_BASE")
        self.assertIs(contract["historical_prep_artifacts_unchanged"], True)
        self.assertEqual(contract["prep_classification_results"], "NOT_RUN")
        self.assertEqual(load(PLAN)["classification_results"], "NOT_RUN")
        self.assertIs(load(PLAN)["execution_authorized_in_prep"], False)

    def test_protected_code_roster_d5_grounding_history_and_fixtures_unchanged(self):
        # Check all BASE-tracked protected files, not a self-reported preservation flag.
        # Git's canonical content comparison handles checkout EOLs on Windows;
        # the two prospective hash authorities get strict byte checks above.
        roots = ["safeshift", "scripts", "configs", "schemas", "prompts", "notebooks",
                 "tests/fixtures", "notes/w2_d9r16_classification_qualification_prep.md",
                 "notes/w2_moondream_postfix_result_external_gate_prep.md",
                 "notes/w2_qwen2_5_external_gate_result.md", "notes/w2_qwen3_external_gate_result.md",
                 "notes/w2_paligemma_external_gate_result.md", "notes/w2_metrics_statistics_decision_brief.md",
                 "notes/w2_d9_freeze_readiness_reconciliation.md"]
        diff = subprocess.check_output(
            # Historical D9R17 recording scope; D9R18 tests protect the exact live delta.
            ["git", "diff", "--no-ext-diff", "--name-only", BASE, "93e1004de311588e94356e19edf53220de13e194", "--", *roots, f":(exclude){RESULT}",
             ":(exclude)configs/pre_freeze/d9r17b_e_classification_qualification_results.v1.json"],
            cwd=ROOT, text=True)
        self.assertEqual(diff, "", diff)
        for path in ("DECISIONS.md", "TASKS.md"):
            before = base_bytes(path).replace(b"\r\n", b"\n")
            after = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
            self.assertTrue(after.startswith(before), f"{path}: history must be append-only")

    def test_live_roster_freeze_and_inspecsafe_boundaries(self):
        roster = load("configs/pre_freeze/local_models.d9.json")
        self.assertEqual([m["model_id"] for m in roster["primary_models"]], [
            "Qwen/Qwen3-VL-8B-Instruct", "Qwen/Qwen2.5-VL-3B-Instruct", "OpenGVLab/InternVL3-2B-hf",
            "vikhyatk/moondream2", "google/paligemma-3b-mix-448",
        ])
        self.assertTrue(all(m["classification"] == "CANDIDATE" for m in roster["primary_models"]))
        self.assertTrue(all(m["activated"] is False for m in roster["backups_in_order"]))
        freeze = load("configs/pre_freeze/freeze_manifest.d9.template.json")
        for document in (roster, freeze):
            self.assertEqual(document["protocol_freeze_commit_sha"], "PENDING")
            self.assertIs(document["inspecsafe_inference_authorized"], False)
        self.assertEqual(freeze["status"], "PENDING_PROTOCOL_FREEZE")
        self.assertEqual(self.result["protocol_freeze"], "PENDING")
        self.assertIs(self.result["NOT_INSPECSAFE"], True)
        self.assertEqual(self.result["inspecsafe_status"], "NOT_RUN")
        self.assertIs(self.result["inspecsafe_inference_authorized"], False)


if __name__ == "__main__":
    unittest.main()
