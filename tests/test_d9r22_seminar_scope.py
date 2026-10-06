"""Offline D9R22 scope/governance checks against the exact authorized BASE."""

import ast
from functools import lru_cache
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from safeshift.protocol.schema import strict_json

ROOT = Path(__file__).resolve().parents[1]
BASE = "a227e18330b49fb8f848934da164a776bc9f6a50"
SCOPE = "configs/pre_freeze/d9r22_seminar_scope.v1.json"
NOTE = "notes/w2_d9r22_seminar_scope_redesign.md"
MATRIX = "notes/w2_d9r22_seminar_readiness.md"
TITLE = ("SafeShift: Benchmarking Cross-Domain Robustness and Disagreement-Aware "
         "Reliability in Vision-Language Models for Industrial Safety Assessment")
MODELS = ["Qwen/Qwen3-VL-8B-Instruct", "Qwen/Qwen2.5-VL-3B-Instruct",
          "OpenGVLab/InternVL3-2B-hf", "vikhyatk/moondream2"]
METRICS = ["joint_parse_availability", "unanimous_agreement", "pairwise_cohens_kappa",
           "vote_entropy", "ordinal_disagreement", "shared_blind_spots",
           "error_complementarity", "disagreement_error_association", "risk_coverage_analysis"]
ALLOWED = {SCOPE, NOTE, MATRIX, "README.md", "ROADMAP.md", "DECISIONS.md",
           "TASKS.md", "tests/test_d9r22_seminar_scope.py",
           "tests/test_d9r20_candidates.py",
           "configs/pre_freeze/production_classification_policy.d9r23.v1.json",
           "prompts/p2_classification_c1_v1.txt", "prompts/.gitattributes",
           "safeshift/protocol/classification_policy.py",
           "safeshift/protocol/classification_failure_policy.py",
           "safeshift/runners/production_classification.py",
           "notes/w2_d9r23_classification_production_contract.md",
           "tests/test_d9r23_classification_contract.py",
           "configs/pre_freeze/d9r24_metric_contract.v1.json",
           "notes/w2_d9r24_disagreement_reliability_metrics.md",
           "safeshift/protocol/d9r24_metrics.py",
           "safeshift/protocol/metrics.py",
           "safeshift/protocol/reporting.py",
           "tests/test_d9r24_metrics.py",
           "configs/pre_freeze/d9r25_harness_contract.v1.json",
           "safeshift/data/p2_execution.py", "safeshift/runners/p2_harness.py",
           "safeshift/protocol/p2_evaluation.py", "tests/test_d9r25_harness.py",
           "notes/w2_d9r25_production_harness.md",
           "configs/pre_freeze/protocol_freeze_candidate.d9r26.v1.json",
           "safeshift/protocol/freeze_candidate.py",
           "safeshift/runners/p2_bridge.py",
           "safeshift/runners/p2_preflight.py",
           "safeshift/runners/p2_owner.py",
           "safeshift/runners/internvl3.py",
           "safeshift/runners/moondream2.py",
           "notes/w2_d9r26_freeze_candidate.md",
           "notes/w2_d9r26_qwen3_p2_runbook.md",
           "notes/w2_d9r26_qwen2_5_p2_runbook.md",
           "notes/w2_d9r26_internvl3_p2_runbook.md",
           "notes/w2_d9r26_moondream_p2_runbook.md",
           "tests/test_d9r26_bridges.py",
           "tests/test_d9r26_candidate.py",
           "configs/frozen/p2_execution_authority.v1.json",
           "notes/w2_d9r27_final_freeze_authority.md",
           "tests/test_d9r27_final_freeze.py",
           "tests/test_classification_qualification.py", "tests/test_moondream_external_gate.py",
           "tests/test_moondream_runner_smoke.py", "tests/test_paligemma_external_gate.py",
           }
PENDING = ["exact_classification_production_contract",
           "production_classification_adapters_parsers",
           "exact_decoding_preprocessing_precision_freeze",
           "rq1_rq2_rq3_new_metric_implementation", "production_benchmark_harness",
           "end_to_end_rehearsal", "implementation_freeze", "protocol_freeze"]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


@lru_cache(None)
def base_checkout(path):
    # Exact configured checkout bytes, including Git's Windows line endings.
    return git("cat-file", "--filters", f"{BASE}:{path}")


def load(path):
    return strict_json((ROOT / path).read_bytes())


class SeminarScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = load(SCOPE)
        cls.paths = git("ls-tree", "-r", "--name-only", BASE).decode().splitlines()

    def assert_preserved(self, paths):
        self.assertTrue(paths, "protection must not pass vacuously")
        for path in paths:
            with self.subTest(path=path):
                # This pre-existing Windows worktree mixes LF and CRLF files.
                # Accept only the exact BASE blob or its Git checkout bytes;
                # never normalize/rewrite protected files to satisfy a test.
                actual = (ROOT / path).read_bytes()
                self.assertIn(actual, (git("show", f"{BASE}:{path}"), base_checkout(path)), path)
        # In addition to checkout bytes, check Git canonical blobs unchanged.
        self.assertEqual(git("diff", "--name-only", BASE, "--", *paths), b"")

    def test_strict_json_and_identity(self):
        d = self.scope
        self.assertEqual(d["schema_version"], "d9r22-seminar-scope-v1")
        self.assertEqual(d["task"], "W2.6-D9R22-SEMINAR-RQ3-DISAGREEMENT-REDESIGN")
        self.assertEqual(d["base_sha"], BASE)
        self.assertEqual(d["status"], "APPROVED_PROSPECTIVE_SCOPE")
        self.assertEqual(d["authority"], "RESEARCH_LEAD")
        self.assertEqual(set(d["active_rqs"]), {"RQ1", "RQ2", "RQ3"})
        for malformed in ('{"a": 1, "a": 2}', '{"a": NaN}', '{"a": Infinity}', '{} trailing'):
            with self.subTest(raw=malformed), self.assertRaises(ValueError):
                strict_json(malformed)

    def test_exact_four_participants_and_d9r18_authority(self):
        self.assertEqual(self.scope["active_models"], MODELS)
        self.assertEqual(self.scope["classification_participant_count"], 4)
        historical = load(self.scope["precedence"]["participation_authority"])
        self.assertEqual([m["model_id"] for m in historical["models"]
                          if m["classification_participation"] == "PARTICIPATING"], MODELS)
        for path in self.scope["precedence"]["historical_configs"]:
            self.assertEqual([m["model_id"] for m in load(path)["primary_models"]
                              if m["classification_participation"] == "PARTICIPATING"], MODELS)

    def test_paligemma_and_backup_not_promoted(self):
        self.assertEqual(self.scope["paligemma_classification"], "NOT_PARTICIPATING")
        for key in ("paligemma_in_primary_rq3", "smolvlm2_activated", "model_promotion"):
            self.assertIs(self.scope[key], False)
        d18 = load(self.scope["precedence"]["participation_authority"])
        self.assertEqual(d18["models"][-1]["classification_participation"], "NOT_PARTICIPATING")
        self.assertIs(d18["backup_decision"]["activated"], False)

    def test_grounding_deferred_not_failed_or_promoted(self):
        d = self.scope
        for key in ("primary_grounding", "exploratory_grounding"):
            self.assertEqual(d[key], "DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE")
        self.assertEqual(d["grounding_future_scope"], "FUTURE_THESIS_EXTENSION")
        self.assertIs(d["grounding_historical_records_preserved"], True)
        for key in ("grounding_deferral_is_scientific_failure",
                    "grounding_required_for_seminar_freeze", "grounding_blocks_active_rqs"):
            self.assertIs(d[key], False)
        self.assertEqual(d["historical_grounding_blocker_applicability"], {
            k: "NOT_ACTIVE_SEMINAR_FREEZE_BLOCKER" for k in
            ("CALL2_ORCHESTRATION_BLOCKER", "MOONDREAM_CALL2_ORCHESTRATION_BLOCKER",
             "EXPLORATORY_GROUNDING_BLOCKER")})

    def test_historical_grounding_artifacts_byte_unchanged(self):
        paths = [p for p in self.paths if p not in ALLOWED and
                 ("grounding" in p.lower() or "source_audit" in p.lower() or
                  p.startswith(("safeshift/", "prompts/", "schemas/")))]
        self.assert_preserved(paths)

    def test_d9r20_d9r21_fixtures_configs_history_byte_unchanged(self):
        paths = [p for p in self.paths if p not in ALLOWED and
                 ("d9r20" in p.lower() or "d9r21" in p.lower() or
                  p.startswith("tests/fixtures/"))]
        self.assert_preserved(paths)

    def test_d9r20_correction_changes_only_historical_guard(self):
        path = "tests/test_d9r20_candidates.py"
        before = ast.parse(git("show", f"{BASE}:{path}"))
        after = ast.parse((ROOT / path).read_bytes())
        pins = {"D9R20_BASE": "668aae839bbde91b67686d143259e07c8a89608c",
                "D9R20_IMPLEMENTATION_HEAD": "b86a3af6754ae238c08f9b5e727df7750fdebd61",
                "D9R20_MERGE_COMMIT": "7976e5c60817319481c564ca1a68f24aec270da8"}
        added = [node for node in after.body if isinstance(node, ast.Assign)
                 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in pins]
        self.assertEqual({node.targets[0].id: ast.literal_eval(node.value) for node in added}, pins)
        after.body = [node for node in after.body if node not in added]
        for tree in (before, after):
            contract = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                            and node.name == "Contracts")
            guard = next(node for node in contract.body if isinstance(node, ast.FunctionDef)
                         and node.name == "test_historical_files_and_append_only_logs")
            contract.body.remove(guard)
        self.assertEqual(ast.dump(before), ast.dump(after))

    def test_d9r20_historical_guard_enforces_pinned_range_and_rejects_tamper(self):
        from tests import test_d9r20_candidates as historical

        base, merge, implementation = (historical.D9R20_BASE, historical.D9R20_MERGE_COMMIT,
                                       historical.D9R20_IMPLEMENTATION_HEAD)
        # Only these historical reads are allowed; implicit HEAD/worktree fails.
        outputs = {
            ("git", "rev-list", "--parents", "-n", "1", merge): f"{merge} {base} {implementation}\n",
            ("git", "ls-tree", "-r", "--name-only", base): "README.md\nDECISIONS.md\nTASKS.md\n",
            ("git", "diff", "--name-only", base, merge): "DECISIONS.md\nTASKS.md\nnew.txt\n",
        }
        for path in ("DECISIONS.md", "TASKS.md"):
            outputs[("git", "show", f"{base}:{path}")] = b"original\r\n"
            outputs[("git", "show", f"{merge}:{path}")] = b"original\nappended\n"
        mutations = [None,
                     (("git", "diff", "--name-only", base, merge), "README.md\n"),
                     (("git", "rev-list", "--parents", "-n", "1", merge), f"{merge} {implementation} {base}\n")]
        mutations += [(("git", "show", f"{merge}:{path}"), b"rewritten\n")
                      for path in ("DECISIONS.md", "TASKS.md")]
        for mutation in mutations:
            responses = dict(outputs)
            if mutation:
                responses[mutation[0]] = mutation[1]
            with self.subTest(mutation=mutation), patch.object(
                    historical.subprocess, "check_output",
                    side_effect=lambda command, **kwargs: responses[tuple(command)]):
                guard = historical.Contracts().test_historical_files_and_append_only_logs
                if mutation:
                    with self.assertRaises(AssertionError):
                        guard()
                else:
                    guard()

    def test_g5_g6_and_external_result_history_byte_unchanged(self):
        paths = [p for p in self.paths if p not in ALLOWED and
                 ("g5" in p.lower() or "g6" in p.lower() or
                  (p.startswith("configs/pre_freeze/") and "result" in p))]
        self.assert_preserved(paths)

    def test_current_title_and_scope_entrypoints(self):
        self.assertEqual(self.scope["title"], TITLE)
        for path in ("README.md", "ROADMAP.md", NOTE):
            self.assertIn(TITLE, (ROOT / path).read_text(encoding="utf-8"))
        for path in ("README.md", "ROADMAP.md", MATRIX, NOTE):
            text = (ROOT / path).read_text(encoding="utf-8")
            self.assertIn("d9r22_seminar_scope.v1.json", text)
        current = (ROOT / MATRIX).read_text(encoding="utf-8")
        self.assertIn("NOT_ACTIVE_SEMINAR_FREEZE_BLOCKER", current)
        self.assertIn("protocol_freeze_commit_sha=PENDING", current)
        self.assert_preserved(["notes/w2_d9_freeze_readiness_reconciliation.md"])

    def test_rq1_semantics_unchanged(self):
        self.assertEqual(self.scope["active_rqs"]["RQ1"], {
            "status": "UNCHANGED", "name": "Zero-shot cross-domain classification robustness",
            "industrial_domain_count": 5,
            "domain_policy": "D3_FOLDER_DOMAIN_WITH_UNCHANGED_MISMATCH_SENSITIVITY",
            "robot_platform_analysis": "CO_VARIATION_ONLY", "causal_claims": False})
        self.assertIs(self.scope["dataset_split_labels_changed"], False)

    def test_rq2_semantics_and_taxonomy_unchanged(self):
        self.assertEqual(self.scope["active_rqs"]["RQ2"], {
            "status": "UNCHANGED", "name": "Safety-critical error concentration",
            "safety_levels": ["Level01", "Level02", "Level03", "Level04"],
            "primary_strata": "12_HAZARD_ATOMS",
            "secondary_summaries": "7_GROUPS_A_G_SECONDARY_EXPLORATORY",
            "prediction_unit": "IMAGE", "overlapping_stratum_counts_additive": False,
            "taxonomy_changed": False, "classification_error_metrics_changed": False})
        self.assert_preserved(["notes/w2_rq2_hierarchy_erratum_brief.md",
                               "notes/w2_grounding_census_decision_brief.md",
                               "notes/w2_metrics_statistics_decision_brief.md"])

    def test_rq3_reuses_predictions_without_extra_inference(self):
        d, r = self.scope, self.scope["active_rqs"]["RQ3"]
        self.assertEqual(r["name"], "Cross-Model Decision Consistency and Disagreement-Aware Reliability under Domain Shift")
        self.assertEqual(r["prediction_source"], "REUSE_RQ1_RQ2_CLASSIFICATION_PREDICTIONS_ONLY")
        self.assertEqual(r["analysis_strata"], ["DOMAIN", "HAZARD_STRATUM"])
        self.assertIs(d["classification_only"], True)
        for key in ("additional_model_inference_for_rq3", "training_or_finetuning",
                    "semantic_score_used_for_model_selection", "benchmark_result_used_for_model_selection",
                    "inspecsafe_threshold_tuning", "model_gpu_execution"):
            self.assertIs(d[key], False)
        for key in ("textual_confidence_used", "ensemble_as_fifth_model",
                    "threshold_selection_from_inspecsafe_outputs", "reliability_signal_established"):
            self.assertIs(r[key], False)
        self.assertIsNone(r["thresholds"])
        self.assertEqual(r["metric_families"], METRICS)
        self.assertEqual(r["metric_implementation"], "PENDING")
        self.assertEqual(r["metric_contract"], "PREDECLARED_FAMILIES_ONLY_EXACT_CONTRACT_PENDING")
        self.assertIn(r["question"], (ROOT / "DECISIONS.md").read_text(encoding="utf-8"))

    def test_authorization_and_freeze_remain_false_pending(self):
        d = self.scope
        self.assertIs(d["inspecsafe_inference_authorized"], False)
        self.assertEqual(d["inspecsafe_status"], "NOT_RUN")
        self.assertEqual(d["protocol_freeze"], "PENDING")
        self.assertEqual(d["protocol_freeze_commit_sha"], "PENDING")
        self.assertIs(d["raw_output_before_parse_required"], True)
        self.assertIs(d["next_batch_task_authorized"], False)
        self.assertIs(d["merge_authorized"], False)
        for path in d["precedence"]["historical_configs"]:
            self.assertIs(load(path)["inspecsafe_inference_authorized"], False)
            self.assertEqual(load(path)["protocol_freeze_commit_sha"], "PENDING")
            self.assert_preserved([path])

    def test_readiness_complete_evidence_is_not_production_readiness(self):
        expected = {k: "COMPLETE" for k in ("model_provenance", "runtime_runners",
                                           "classification_participation", "external_gate_history")}
        expected.update({k: "PENDING" for k in PENDING})
        self.assertEqual(self.scope["readiness"], expected)
        self.assertEqual(self.scope["next_required_tasks"], PENDING)
        self.assertIs(self.scope["precedence"]["historical_configs_are_d9r22_production_contracts"], False)

    def test_decisions_tasks_exact_append_only(self):
        for path in ("DECISIONS.md", "TASKS.md"):
            before, after = base_checkout(path), (ROOT / path).read_bytes()
            self.assertTrue(after.startswith(before), path)
            self.assertIn(b"D9R22", after[len(before):])
            # Also protect exact canonical Git history, not just checkout text.
            original = git("show", f"{BASE}:{path}")
            canonical = git("hash-object", "--path=" + path, path).decode().strip()
            self.assertNotEqual(canonical, git("rev-parse", f"{BASE}:{path}").decode().strip())
            self.assertTrue(after.replace(b"\r\n", b"\n").startswith(original))

    def test_scope_allowlist_and_no_dataset_weights_raw_outputs(self):
        changed = set(git("diff", "--name-only", BASE).decode().splitlines())
        staged = set(git("diff", "--cached", "--name-only").decode().splitlines())
        self.assertLessEqual(changed | staged, ALLOWED)
        for path in changed | staged | ALLOWED:
            self.assertTrue(Path(path).suffix in {".md", ".json", ".py", ".txt"}
                            or path.endswith(".gitattributes"))
            self.assertFalse(path.startswith(("data/", "runs/", "outputs/", "weights/")))
            self.assertLess((ROOT / path).stat().st_size, 350_000)
        # Untracked user files are deliberately outside staged/commit authority.
        # Guard every BASE file outside the explicit documentary change allowlist.
        self.assertEqual(git("diff", "--name-only", BASE, "--", ".",
                             *[":(exclude)" + p for p in ALLOWED]), b"")


if __name__ == "__main__":
    unittest.main()
