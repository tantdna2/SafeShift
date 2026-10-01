"""Offline documentary checks of supplied findings, not an external bundle audit."""

import hashlib
from pathlib import Path
import subprocess
import unittest

from safeshift.protocol.schema import strict_json
from safeshift.qualification.classification import evaluate


ROOT = Path(__file__).resolve().parents[1]
BASE = "3ad16f48da4f9ef5910dedede9a4ba950f268b7a"
RESULT = "configs/pre_freeze/d9r17b_e_classification_qualification_results.v1.json"
MANIFEST = "configs/pre_freeze/classification_qualification_cases.v1.json"
PLAN = "configs/pre_freeze/classification_qualification_plan.v1.json"
ROSTER = "configs/pre_freeze/local_models.d9.json"
FREEZE = "configs/pre_freeze/freeze_manifest.d9.template.json"
MANIFEST_SHA = "3b7c3ebdec0736580bbad27f782496e318372cda6c3a4f322c4cc19ca5749e92"
PLAN_SHA = "c2e8990227e7378368b986352d88fe6c9975769cdeccda346e3070d321d77160"
PROMPT_SHA = "1b6da67a979a7c5bd53af35ce9a65516761da4008a2bb6519438dbd05c687348"
EXPECTED = ["Level01", "Level01", "Level02", "Level02", "Level03", "Level03", "Level04", "Level04"]
KEYS = ["internvl3", "moondream", "paligemma", "qwen3"]
IDENTITIES = {
    "internvl3": ("OpenGVLab/InternVL3-2B-hf", "cb57a075cb75a2e6d1b668b128d48bb00ae321d2",
                  "d9r17b-internvl3-classification", "DEC-W2-D9R17B-INTERNVL3-CLASSIFICATION-QUALIFICATION-EXEC-001",
                  "2026-10-01T07:34:15.526059+00:00"),
    "moondream": ("vikhyatk/moondream2", "9a7d4024050840e001defacec2b00727e89149e6",
                  "d9r17c-moondream-classification", "DEC-W2-D9R17C-MOONDREAM-CLASSIFICATION-QUALIFICATION-EXEC-001",
                  "2026-10-01T07:42:44.055714+00:00"),
    "paligemma": ("google/paligemma-3b-mix-448", "ead2d9a35598cb89119af004f5d023b311d1c4a1",
                  "d9r17d-paligemma-classification", "DEC-W2-D9R17D-PALIGEMMA-CLASSIFICATION-QUALIFICATION-EXEC-001",
                  "2026-10-01T08:51:54.551970+00:00"),
    "qwen3": ("Qwen/Qwen3-VL-8B-Instruct", "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b",
              "d9r17e-qwen3-classification", "DEC-W2-D9R17E-QWEN3-CLASSIFICATION-QUALIFICATION-EXEC-001",
              "2026-10-01T09:04:14.041838+00:00"),
}
BUNDLES = {
    "internvl3": ("d8a0c3463f716866a04c38daf40aafccf100e1d99eba9c2f966f6c4ddd5caa3f", 59204),
    "moondream": ("3486de253fb5775d864b54b376ed9f464547b1f796a0551c525580d70366b93c", 92830),
    "paligemma": ("ffb68b11f6a62bd716a81af634ed8fdb412c641d2e4ce08aaf8f224d89092d4c", 59123),
    "qwen3": ("ff1a49b8dc7ca43ca0b401e42ca1485f24651e9da639deb0029ae2bbf6205a69", 51152),
}
RAW_HASHES = {
    "internvl3": [
        "546146a8b00d730f45bc8b7964b57ea8c0786228742642d78c406642ccfa2a4b",
        "5a0d9f2cef98aa0bb2b6c0e1fc62cac7bb8a50fc49a967a11c95260e6beb824d",
        "fa70b0aed293ce53b001c9fbde9345c3f1b43898649998600fb37edb6b691cf3",
        "36731e00bf65bb23d21bbc124b0666421d1d5b919c6f552aa6ca00cd8da1fbf2",
        "17a65e8e15c0631e5bba1216ed53ce9222b5803326abf1e8219f44156faf84ef",
        "f37be4d6f6db4bd5c530ef0ee7a6422f9aef50e5ca0f693ef15aeeeccc855759",
        "f0fe7c14c9c30a43f5b1b38206119663b4797f311e65040f7a9111e2ad5d4e29",
        "57b1b831fca141f2c6e9a3f38d8b82db7f066faecd03c070f69c60720926e57c",
    ],
    "moondream": ["2188ec33a40247a13667fde9af15bde49ae640aacf310053964d9a903286e72f"] * 8,
    "paligemma": [
        "a9a72bf4450cff50dec5c23786a745487e4a5df6f9e0e4816bbe021ba2ef45b6",
        "82f330c2a496c1ba574bcaa763e71b56d9f35ace4a8df84fdcacbe9dc08b47a1",
        "24f86b494cea04ef518e647b1afc3b3ea4fbb8b565ebdb6c6b11e6b5dc6b9c1b",
        "eaa159d4aab50b7c4d54dba494b5d784e6bcd4ae09ac7f941bfe982fc210e138",
        "c4fb1d3abfec74b4016dd997be1d01c4f2e3840ead6fb1436e4c03c2c9e7fbac",
        "205192dc6fd3f52a6527b825be6acab7f6b8b26f0e77be8b741a304eec64943a",
        "934541b578d2db70be554756ebaac7ed64dbdbd73c86a7df8075cabf64c12b97",
        "32bbe2735b8583628c26b89643d2f9c085595e6c85b61949622cdf5ef3417be1",
    ],
    "qwen3": [h for h in (
        "a46a68ebfbffe408f9f945a594c82ac40f50ae7ee5b94b2d7a0f6abf22801586",
        "455c1da7f3fa9bc0323798c2f8e1aef3aa83dde043d1eeb757ba32ec0a0eb7b3",
        "b528cb7e6bc038b5b3eef94bfe78cd83612375c3c939cb9525d0fc33c26af65a",
        "c4fc526e6035270f63b68ff415a1f53f905f7f654ad42a25aff544db81d2ab79",
    ) for _ in range(2)],
}


def load(path):
    return strict_json((ROOT / path).read_bytes())


def base_bytes(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)


class FourModelClassificationResultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = load(RESULT)
        cls.runs = cls.result["runs"]

    def test_record_identity_and_scope(self):
        r = self.result
        self.assertEqual(r["schema_version"], "d9r17b-e-classification-qualification-results-v1")
        self.assertEqual(r["task"], "W2.6-D9R17B-E-FOUR-MODEL-CLASSIFICATION-QUALIFICATION-RESULTS")
        self.assertEqual(r["recording_date"], "2026-10-01")
        self.assertEqual(r["recording_base_sha"], BASE)
        self.assertEqual(r["execution_commit"], BASE)
        self.assertEqual(r["suite"], "external-classification-qualification-v1")
        self.assertEqual(r["source_kind"], "EXTERNAL_CLASSIFICATION_QUALIFICATION")
        self.assertEqual(list(self.runs), KEYS)

    def test_external_findings_are_attributed_without_codex_rehash_claim(self):
        r = self.result
        self.assertEqual(r["record_kind"], "RESEARCH_LEAD_VERIFIED_REAL_CLASSIFICATION_QUALIFICATION_RESULT")
        source = r["source"]
        self.assertEqual(source["authority"], "RESEARCH_LEAD")
        self.assertIn("Research Lead / ChatGPT directly inspected", source["recording_basis"])
        self.assertIn("did not independently inspect or rehash", source["recording_basis"])
        for key in ("independent_bundle_inspection_by_codex", "independent_bundle_rehash_by_codex",
                    "bundle_and_raw_bytes_committed"):
            self.assertIs(source[key], False, key)

    def test_exact_model_execution_authorization_and_bundle_pins(self):
        for key, run in self.runs.items():
            with self.subTest(model=key):
                self.assertEqual(tuple(run[k] for k in (
                    "model_id", "immutable_revision", "run_id", "execution_authorization", "completed_at")), IDENTITIES[key])
                self.assertEqual(run["execution_commit"], BASE)
                self.assertEqual((run["bundle_sha256"], run["bundle_size_bytes"]), BUNDLES[key])
                prospective = load(PLAN)["models"][key]
                self.assertEqual(run["model_id"], prospective["model_id"])
                self.assertEqual(run["immutable_revision"], prospective["revision"])
        self.assertEqual(self.runs["moondream"]["tokenizer_revision"], "35192e10a54e36eabe0a7cc57a2c1aab371cafc5")

    def test_exact_verdict_causes_and_absence_of_runtime_failure(self):
        verdicts = {
            "internvl3": ("FAIL", ["SEMANTIC_CLASSIFICATION_FAILURE"]),
            "moondream": ("FAIL", ["SEMANTIC_CLASSIFICATION_FAILURE"]),
            "paligemma": ("FAIL", ["INTERFACE_OR_FORMAT_FAILURE"]),
            "qwen3": ("PASS", []),
        }
        for key, run in self.runs.items():
            with self.subTest(model=key):
                self.assertEqual((run["run_status"], run["causes"]), verdicts[key])
                self.assertIsNone(run["runtime_failure"])
                self.assertIsNone(run["runtime_evidence"]["runtime_failure"])

    def test_exact_cases_observations_and_parse_status(self):
        observations = {"internvl3": EXPECTED[:6] + ["Level01"] * 2, "moondream": ["Level01"] * 8,
                        "paligemma": [None] * 8, "qwen3": EXPECTED}
        self.assertEqual([c["expected_safety_level"] for c in load(MANIFEST)["cases"]], EXPECTED)
        for key, run in self.runs.items():
            with self.subTest(model=key):
                self.assertEqual([c["case_id"] for c in run["cases"]], [f"cq_{i:02d}" for i in range(1, 9)])
                self.assertEqual([c["expected_safety_level"] for c in run["cases"]], EXPECTED)
                self.assertEqual([c["observed_canonical"] for c in run["cases"]], observations[key])
                for case in run["cases"]:
                    self.assertEqual(case["parse_status"], "INVALID" if key == "paligemma" else "SUCCESS")
                    self.assertIs(case["correct"], case["observed_canonical"] == case["expected_safety_level"])

    def test_native_outputs_are_preserved_without_reinterpretation(self):
        self.assertEqual([c["native_decoded_text"] for c in self.runs["paligemma"]["cases"]],
                         ["level01", "level01", "blue diamond", "blue diamond",
                          "yellow circle", "yellow circle", "green square", "green square"])
        for c in self.runs["paligemma"]["cases"]:
            self.assertIsNone(c["observed_canonical"])
            self.assertIs(c["correct"], False)
        for c in self.runs["moondream"]["cases"]:
            self.assertEqual(c["native_answer"], '{\n  "safety_level": "Level01"\n}')

    def test_descriptive_counts_match_cases_and_fixed_findings(self):
        exact = {"internvl3": 6, "moondream": 2, "paligemma": 0, "qwen3": 8}
        for key, run in self.runs.items():
            with self.subTest(model=key):
                success = 0 if key == "paligemma" else 8
                self.assertEqual(run["summary"], {
                    "total_cases": 8, "parse_success_count": success, "parse_invalid_count": 8 - success,
                    "exact_expected_count": exact[key],
                    "semantic_expected_match_scope": "DESCRIPTIVE_QUALIFICATION_EVIDENCE_ONLY",
                })
                self.assertEqual(len(run["cases"]), 8)
                self.assertEqual(sum(c["parse_status"] == "SUCCESS" for c in run["cases"]), success)
                self.assertEqual(sum(c["parse_status"] == "INVALID" for c in run["cases"]), 8 - success)
                self.assertEqual(sum(c["correct"] for c in run["cases"]), exact[key])

    def test_pure_prospective_verdict_agrees_without_model_or_parser_replay(self):
        cases = [(c, b"") for c in load(MANIFEST)["cases"]]
        for key, run in self.runs.items():
            rows = [{"case_id": c["case_id"], "parse_status": c["parse_status"],
                     "safety_level": c["observed_canonical"],
                     "raw_output": {"sha256": c["raw_sha256"], "size_bytes": c["raw_size_bytes"]}}
                    for c in run["cases"]]
            with self.subTest(model=key):
                for field, value in evaluate(cases, rows, runtime_failure=None).items():
                    self.assertEqual(run[field], value, field)
        self.assertEqual(self.result["prospective_contract"]["required_exact_expected_count"], 8)
        self.assertIn("8_EXACT_EXPECTED_LEVELS", load(PLAN)["pass_requires"])

    def test_exact_raw_hashes_sizes_and_image_manifest_links(self):
        sizes = {"internvl3": [5480] * 8, "moondream": [136] * 8, "qwen3": [4759] * 8,
                 "paligemma": [16382, 16382, 16376, 16376, 16380, 16380, 16374, 16374]}
        images = [c["image_sha256"] for c in load(MANIFEST)["cases"]]
        for key, run in self.runs.items():
            with self.subTest(model=key):
                self.assertEqual([c["raw_sha256"] for c in run["cases"]], RAW_HASHES[key])
                self.assertEqual([c["raw_size_bytes"] for c in run["cases"]], sizes[key])
                self.assertEqual([c["image_sha256"] for c in run["cases"]], images)

    def test_all_32_call_integrity_attestations(self):
        self.assertEqual(self.result["raw_evidence"], {
            "verification_authority": "RESEARCH_LEAD", "scope": "ALL_32_CALLS_IN_FOUR_RUNS", "call_count": 32,
            "computed_raw_sha256_matches_result": True, "computed_raw_size_matches_result": True,
            "metadata_raw_sha256_matches_actual_raw": True, "metadata_raw_size_matches_actual_raw": True,
            "metadata_parse_status_before_parser": "NOT_ATTEMPTED",
            "metadata_source_kind": "EXTERNAL_CLASSIFICATION_QUALIFICATION",
            "NOT_INSPECSAFE": True, "NOT_ACCURACY_BENCHMARK": True,
            "per_case_image_sha256_matches_prospective_manifest": True,
            "top_level_result_equals_calls_qualification_result": True,
            "top_level_result_path": "result.json", "inner_result_path": "calls/qualification_result.json",
            "artifact_path_basis": "RELATIVE_TO_EACH_EXECUTION_ATTEMPT_DIRECTORY",
        })
        self.assertEqual(sum(len(r["cases"]) for r in self.runs.values()), 32)

    def test_each_attempt_manifest_plan_and_prompt_sha(self):
        for key, run in self.runs.items():
            with self.subTest(model=key):
                self.assertEqual(run["attempt_manifest_sha256"], MANIFEST_SHA)
                self.assertEqual(run["attempt_plan_sha256"], PLAN_SHA)
                self.assertEqual(run["prompt_sha256"],
                                 "035ce849df10ef3b14982a8c9106ade8ef8e6889f1bbb7921c7dff08e98dc840"
                                 if key == "paligemma" else PROMPT_SHA)

    def test_exact_runtime_call_counts_hardware_and_precision(self):
        for key, run in self.runs.items():
            with self.subTest(model=key):
                runtime = run["runtime_evidence"]
                self.assertEqual(runtime["verification_authority"], "RESEARCH_LEAD")
                self.assertEqual(tuple(runtime[k] for k in ("model_loads", "classification_calls", "grounding_calls")), (1, 8, 0))
                count = 2 if key == "qwen3" else 1
                self.assertEqual(runtime["hardware"], {
                    "visible_gpu_count": count,
                    "gpus": [{"name": "Tesla T4", "compute_capability": [7, 5], "total_vram_bytes": 15636037632}] * count,
                })
                self.assertEqual((runtime["precision"], runtime["quantization"]), ("FP16", "NONE"))

    def test_internvl3_paligemma_snapshot_and_state_audit_summaries(self):
        for key in ("internvl3", "paligemma"):
            with self.subTest(model=key):
                runtime = self.runs[key]["runtime_evidence"]
                self.assertEqual(runtime["cuda_version"], "12.4")
                self.assertEqual(runtime["snapshot"], {"local_bytes_verified": True, "file_count": 14})
                self.assertEqual(runtime["state_audit_record_count"], 25)

    def test_moondream_snapshot_query_and_audit_summaries(self):
        runtime = self.runs["moondream"]["runtime_evidence"]
        self.assertEqual((runtime["query_call_count"], runtime["detect_call_count"]), (8, 0))
        self.assertEqual(runtime["snapshot"], {"exact_model_snapshot_verified": True,
                         "exact_tokenizer_snapshot_verified": True, "provision_online_offline_manifests_matched": True})
        self.assertEqual(runtime["state_audits"], {"record_count": 17, "valid_count": 17, "status": "VALID"})
        self.assertEqual(runtime["image_boundary_count"], 24)

    def test_qwen3_software_shards_and_two_gpu_placement(self):
        runtime = self.runs["qwen3"]["runtime_evidence"]
        self.assertEqual(runtime["cuda_version"], "12.8")
        self.assertEqual(runtime["software_versions"], {
            "python": "3.12.13", "torch": "2.10.0+cu128", "transformers": "4.57.1", "accelerate": "1.11.0",
            "huggingface_hub": "0.36.0", "safetensors": "0.6.2", "pillow": "11.3.0", "zlib": "1.2.11",
        })
        self.assertEqual(runtime["snapshot"], {"weight_shard_count": 4, "verified_weight_shard_count": 4})
        self.assertEqual(runtime["device_map"], {"gpu_indices_used": [0, 1], "cpu_placement_observed": False,
                                                "disk_placement_observed": False})

    def test_every_role_pending_no_roster_removal_backup_promotion_or_rerun(self):
        for key, run in self.runs.items():
            with self.subTest(model=key):
                self.assertEqual(run["model_role_after_run"], "PENDING_RESEARCH_LEAD_REVIEW")
                self.assertEqual(run["review_status"], "PENDING_REVIEW")
                self.assertEqual(run["classification_participation_decision"], "PENDING")
                for field in ("roster_membership_changed", "model_removed", "backup_activated",
                              "production_adapter_promoted", "automatic_rerun", "real_model_rerun"):
                    self.assertIs(run[field], False, field)

    def test_no_retry_repair_reinterpretation_or_policy_change(self):
        self.assertEqual(self.result["attempt_contract"], {
            "basis": "UNCHANGED_PROSPECTIVE_PLAN_NO_RETRY_OR_REPAIR", "retry_count": 0, "repair_count": 0,
            "alternate_prompt": False, "prompt_parser_policy_changes_within_run": False,
            "output_budget_changed": False, "output_reinterpretation": False, "lowercase_alias_or_marker_mapping": False,
        })
        for key in ("retry_count", "repair_count", "prompt_parser_policy_changes_within_run"):
            self.assertEqual(self.result["attempt_contract"][key], load(PLAN)["per_model"][key])

    def test_recording_boundaries_no_freeze_execution_or_inspecsafe_authorization(self):
        self.assertEqual(self.result["recording_boundaries"], {
            "model_execution_by_recording_agent": False, "ranking_models": False,
            "NOT_INSPECSAFE": True, "NOT_ACCURACY_BENCHMARK": True,
            "protocol_freeze": "PENDING", "inspecsafe_status": "NOT_RUN", "inspecsafe_inference_authorized": False,
            "roster_membership_changed": False, "model_removed": False, "backup_activated": False,
            "production_adapter_promoted": False, "automatic_rerun": False, "real_model_rerun": False,
            "prompt_parser_runner_runtime_protocol_changed": False,
        })

    def test_four_protected_files_are_byte_identical_to_exact_base(self):
        protected = self.result["protected_files"]
        self.assertEqual([p["path"] for p in protected], [PLAN, MANIFEST, ROSTER, FREEZE])
        for entry in protected:
            with self.subTest(path=entry["path"]):
                before = base_bytes(entry["path"])
                self.assertEqual((ROOT / entry["path"]).read_bytes(), before)
                self.assertEqual(entry["base_sha256"], hashlib.sha256(before).hexdigest())
                self.assertIs(entry["byte_unchanged_from_base"], True)

    def test_historical_prep_contract_and_hashes_remain_unchanged(self):
        contract = self.result["prospective_contract"]
        for prefix, path, sha in (("manifest", MANIFEST, MANIFEST_SHA), ("plan", PLAN, PLAN_SHA)):
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), sha)
            self.assertEqual(contract[prefix + "_path"], path)
            self.assertEqual(contract[prefix + "_sha256"], sha)
        self.assertEqual(contract["hash_basis"], "REPOSITORY_BYTES_AT_RECORDING_BASE")
        self.assertIs(contract["historical_prep_artifacts_unchanged"], True)
        self.assertEqual(contract["prep_classification_results"], "NOT_RUN")
        self.assertIs(contract["execution_authorized_in_prep"], False)
        self.assertEqual(load(PLAN)["classification_results"], "NOT_RUN")
        self.assertIs(load(PLAN)["execution_authorized_in_prep"], False)

    def test_live_roster_and_freeze_keep_all_five_candidates_and_inactive_backup(self):
        roster, freeze = load(ROSTER), load(FREEZE)
        self.assertEqual([m["model_id"] for m in roster["primary_models"]], [
            "Qwen/Qwen3-VL-8B-Instruct", "Qwen/Qwen2.5-VL-3B-Instruct", "OpenGVLab/InternVL3-2B-hf",
            "vikhyatk/moondream2", "google/paligemma-3b-mix-448",
        ])
        self.assertTrue(all(m["classification"] == "CANDIDATE" for m in roster["primary_models"]))
        self.assertEqual([m["model_id"] for m in roster["backups_in_order"]], ["HuggingFaceTB/SmolVLM2-2.2B-Instruct"])
        for document in (roster, freeze):
            self.assertEqual(document["protocol_freeze_commit_sha"], "PENDING")
            self.assertIs(document["inspecsafe_inference_authorized"], False)
            self.assertTrue(all(m["activated"] is False for m in document["backups_in_order"]))
        self.assertEqual(freeze["status"], "PENDING_PROTOCOL_FREEZE")
        self.assertTrue(all(m["classification_role"] == "PENDING_FINAL_GATE" for m in freeze["primary_models"]))

    def test_protected_implementation_and_history_unchanged(self):
        # Exact allowlist leaves every other tracked config, runtime, fixture,
        # D5/grounding document and test under the BASE preservation check.
        allowed = [RESULT, "notes/w2_d9r17b_e_classification_qualification_results.md",
                   "tests/test_d9r17b_e_classification_qualification_results.py",
                   "tests/test_qwen2_5_classification_qualification_result.py", "DECISIONS.md", "TASKS.md"]
        diff = subprocess.check_output(["git", "diff", "--no-ext-diff", "--name-only", BASE, "--", ".",
                                        *[f":(exclude){p}" for p in allowed]], cwd=ROOT, text=True)
        self.assertEqual(diff, "", diff)
        for path in ("DECISIONS.md", "TASKS.md"):
            self.assertTrue((ROOT / path).read_bytes().startswith(base_bytes(path)), path)

    def test_prior_result_guard_only_allows_the_new_documentary_artifact(self):
        path = "tests/test_qwen2_5_classification_qualification_result.py"
        before = base_bytes(path)
        old = b'*roots, f":(exclude){RESULT}"],'
        new = (b'*roots, f":(exclude){RESULT}",\n'
               b'             ":(exclude)configs/pre_freeze/d9r17b_e_classification_qualification_results.v1.json"],')
        self.assertEqual(before.count(old), 1)
        self.assertEqual((ROOT / path).read_bytes(), before.replace(old, new))


if __name__ == "__main__":
    unittest.main()
