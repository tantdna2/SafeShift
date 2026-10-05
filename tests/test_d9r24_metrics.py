"""Synthetic offline contract tests for D9R24 metric/reporting code."""

import json
from pathlib import Path
import subprocess
import unittest

from safeshift.protocol.d9r24_metrics import (
    MODEL_IDS,
    DisagreementSample,
    bootstrap,
    bootstrap_draws,
    classification_metrics,
    percentile_ci,
    rq1_metrics,
    rq2_metrics,
    rq3_metrics,
    _kappa,
)
from safeshift.protocol.metrics import ClassificationInput
from safeshift.protocol.reporting import build_report, render_json
from safeshift.protocol.schema import Classification, ParseResult, SAFETY_LEVELS, strict_json


def cls(i, true, pred, domain="Power", atoms=(), point=None):
    parsed = ParseResult("INVALID") if pred is None else ParseResult(
        "SUCCESS", Classification(pred), response_schema_valid=True
    )
    return ClassificationInput(str(i), true, domain, point or str(i), parsed, frozenset(atoms))


def disagreement(i, true, labels, domain="Power", hazards=(), point=None):
    return DisagreementSample(
        str(i), true, domain, dict(zip(MODEL_IDS, labels)), frozenset(hazards), point
    )


class ClassificationMetricTests(unittest.TestCase):
    def test_invalid_is_false_negative_without_fake_level04(self):
        result = classification_metrics((cls(1, "Level01", None), cls(2, "Level04", "Level04")))
        self.assertEqual(result["confusion_matrix"]["Level01"]["INVALID"], 1)
        self.assertEqual(result["confusion_matrix"]["Level01"]["Level04"], 0)
        self.assertEqual(result["invalid_n"], 1)
        self.assertIsNone(result["anomaly_fnr_parse_conditional"]["value"])
        self.assertEqual(result["anomaly_non_detection_rate_failure_aware"]["value"], 1.0)

    def test_rq1_domain_support_and_rq2_overlap(self):
        rows = (
            cls(1, "Level01", "Level01", atoms=("SMOKE", "OPEN_FLAME")),
            cls(2, "Level02", "Level02", atoms=("SMOKE",)),
            cls(3, "Level04", "Level04", domain="metallurgy", atoms=("DOOR_OPEN",)),
        )
        rq1 = rq1_metrics(rows)
        self.assertIn("metallurgy", rq1["domains"])
        self.assertTrue(rq1["metallurgy_sparse_support_warning"])
        rq2 = rq2_metrics(rows)
        self.assertEqual(rq2["strata"]["SMOKE"]["support_n"], 2)
        self.assertEqual(rq2["strata"]["OPEN_FLAME"]["support_n"], 1)
        self.assertFalse(rq2["counts_additive"])

    def test_rq1_support_aware_domain_macro_and_k4_spread(self):
        rows = (
            cls("d3-1", "Level01", "Level01", "d3"),
            cls("d3-2", "Level02", "Level02", "d3"),
            cls("d3-4", "Level04", "Level04", "d3"),
            *tuple(cls(f"a-{i}", level, level, "a") for i, level in enumerate(SAFETY_LEVELS)),
            *tuple(cls(f"b-{i}", level, "Level04", "b") for i, level in enumerate(SAFETY_LEVELS)),
            cls("m-1", "Level01", "Level01", "metallurgy"),
        )
        result = rq1_metrics(rows)
        d3 = result["domains"]["d3"]
        self.assertEqual(d3["K_d"], 3)
        self.assertEqual(d3["supported_classes"], ["Level01", "Level02", "Level04"])
        self.assertIsNotNone(d3["balanced_accuracy"])
        self.assertIsNotNone(d3["macro_f1"])
        self.assertIsNotNone(d3["comparability_warning"])
        self.assertEqual(result["balanced_accuracy_domain_spread"]["participating_domains"], ["a", "b"])
        self.assertAlmostEqual(result["balanced_accuracy_domain_spread"]["spread"], .75)
        self.assertEqual(result["metallurgy_anomaly_methodology"], "SPARSE_SUPPORT_DESCRIPTIVE_ONLY")

    def test_rq1_anomaly_recall_spread_excludes_no_anomaly_domain(self):
        rows = (
            cls("a-1", "Level01", "Level01", "a"),
            cls("b-1", "Level01", "Level04", "b"),
            cls("n-1", "Level04", "Level04", "normal-only"),
        )
        spread = rq1_metrics(rows)["anomaly_recall_spread"]
        self.assertEqual(spread["domains_with_anomaly_support"], ["a", "b"])
        self.assertAlmostEqual(spread["spread"], 1.0)

    def test_rq2_exposes_explicit_empty_denominators(self):
        result = rq2_metrics((cls(1, "Level04", "Level04", atoms=("SMOKE",)),))
        row = result["strata"]["SMOKE"]
        self.assertIn("exact_safety_level_error_rate", row)
        self.assertIn("safety_level_confusion_distribution", row)
        self.assertIsNone(row["level01_recall_parse_conditional"]["value"])
        self.assertEqual(row["support_n"], 1)
        self.assertIn("parse_success_rate", row)


class RQ3MetricTests(unittest.TestCase):
    def test_kappa_degenerate_and_known_non_degenerate_values(self):
        degenerate = _kappa(["Level01"] * 4, ["Level01"] * 4)
        self.assertIsNone(degenerate["value"])
        self.assertEqual(degenerate["expected_agreement"], 1.0)
        self.assertEqual(degenerate["status"], "UNDEFINED_DEGENERATE_MARGINALS")
        known = _kappa(["Level01", "Level01", "Level02", "Level02"],
                       ["Level01", "Level02", "Level01", "Level02"])
        self.assertAlmostEqual(known["value"], 0.0)

    def test_patterns_entropy_ordinal_and_blind_spots(self):
        rows = (
            disagreement(1, "Level01", ("Level01",) * 4),
            disagreement(2, "Level01", ("Level04",) * 4, hazards=("SMOKE",)),
            disagreement(3, "Level01", ("Level01", "Level01", "Level02", "Level03")),
            disagreement(4, "Level02", ("Level01", "Level01", "Level02", "Level02")),
            disagreement(5, "Level01", ("Level01", "Level02", "Level03", "Level04")),
        )
        pooled = rq3_metrics(rows)["pooled"]
        self.assertEqual(pooled["joint_valid_4_n"], 5)
        self.assertEqual(pooled["vote_pattern_classes"]["UNANIMOUS_4_0"]["n"], 2)
        self.assertEqual(pooled["vote_pattern_classes"]["PLURALITY_2_1_1"]["n"], 1)
        self.assertEqual(pooled["vote_pattern_classes"]["TIE_2_2"]["n"], 1)
        self.assertEqual(pooled["vote_pattern_classes"]["ALL_DIFFERENT_1_1_1_1"]["n"], 1)
        self.assertAlmostEqual(pooled["vote_entropy"]["values"][0], 0.0)
        self.assertAlmostEqual(pooled["ordinal_disagreement"]["values"][0], 0.0)
        self.assertEqual(pooled["shared_blind_spots"]["unanimous_normal_on_anomaly"]["numerator"], 1)
        self.assertEqual(pooled["shared_blind_spots"]["unanimous_normal_on_anomaly"]["denominator"], 5)
        self.assertEqual(pooled["shared_blind_spots"]["joint_anomaly_n"], 5)
        self.assertEqual(pooled["selective_reliability"]["abstention_due_tie"], 1)

    def test_invalid_is_outside_joint_and_tie_is_abstained(self):
        rows = (
            disagreement(1, "Level01", ("Level01", "Level01", "Level01", None)),
            disagreement(2, "Level01", ("Level01", "Level01", "Level02", "Level02")),
        )
        pooled = rq3_metrics(rows)["pooled"]
        self.assertEqual(pooled["joint_valid_4_n"], 1)
        self.assertEqual(pooled["invalid_count_by_model"]["moondream"], 1)
        self.assertEqual(pooled["selective_reliability"]["abstention_due_invalid"], 1)
        self.assertEqual(pooled["selective_reliability"]["abstention_due_tie"], 1)

    def test_all_different_has_no_unique_ensemble_candidate(self):
        pooled = rq3_metrics((disagreement(
            1, "Level01", ("Level01", "Level02", "Level03", "Level04")
        ),))["pooled"]
        selective = pooled["selective_reliability"]
        self.assertEqual(selective["eligible_n"], 0)
        self.assertEqual(selective["abstention_due_no_unique_winner"], 1)

    def test_input_order_does_not_change_report_or_ranking(self):
        rows = (
            disagreement(2, "Level02", ("Level02",) * 4),
            disagreement(1, "Level01", ("Level01", "Level02", "Level01", "Level02")),
        )
        left = rq3_metrics(rows)
        right = rq3_metrics(tuple(reversed(rows)))
        self.assertEqual(left, right)

    def test_risk_coverage_has_two_axes_and_anomaly_only_critical_denominator(self):
        rows = (
            disagreement("0-anomaly", "Level01", ("Level04",) * 4),
            disagreement("1-normal", "Level04", ("Level04",) * 4),
            disagreement("2-normal", "Level04", ("Level04",) * 4),
            disagreement("3-invalid", "Level01", ("Level01", "Level01", "Level01", None)),
        )
        selective = rq3_metrics(rows)["pooled"]["selective_reliability"]
        self.assertEqual(selective["eligible_n"], 3)
        self.assertAlmostEqual(selective["eligible_coverage"]["value"], .75)
        final = selective["curve"][-1]
        self.assertAlmostEqual(final["eligible_relative_coverage"], 1.0)
        self.assertAlmostEqual(final["overall_coverage"], .75)
        self.assertEqual(final["safety_critical_anomaly_to_level04_failure"]["denominator"], 1)
        self.assertEqual(final["safety_critical_anomaly_to_level04_failure"]["numerator"], 1)
        self.assertEqual(selective["aurc_axis"], "eligible_relative_coverage")

    def test_ranking_ignores_ground_truth(self):
        predictions = ("Level01", "Level01", "Level02", "Level02")
        left = (disagreement("a", "Level01", predictions), disagreement("b", "Level04", ("Level01",) * 4))
        right = (disagreement("a", "Level04", predictions), disagreement("b", "Level01", ("Level01",) * 4))
        left_ids = [point.get("sample_id") for point in rq3_metrics(left)["pooled"]["selective_reliability"]["curve"]]
        right_ids = [point.get("sample_id") for point in rq3_metrics(right)["pooled"]["selective_reliability"]["curve"]]
        self.assertEqual(left_ids, right_ids)

    def test_bootstrap_reproducible_shared_draws_and_no_nan_json(self):
        rows = (
            disagreement(1, "Level01", ("Level01",) * 4, point="p"),
            disagreement(2, "Level01", ("Level01",) * 4, point="p"),
            disagreement(3, "Level04", ("Level04",) * 4, domain="Tunnel", point="q"),
        )
        self.assertEqual(bootstrap_draws(rows), bootstrap_draws(tuple(reversed(rows))))
        ci = percentile_ci(tuple([0.5] * 2000))
        self.assertEqual(ci["ci95"], [0.5, 0.5])
        report = build_report(disagreement_samples=rows)
        rendered = render_json(report)
        self.assertEqual(report, json.loads(rendered))
        self.assertNotIn("NaN", rendered)
        self.assertNotIn("Infinity", rendered)

    def test_bootstrap_cluster_contract(self):
        with self.assertRaisesRegex(ValueError, "NORMAL_POINT_ID_REQUIRED"):
            bootstrap_draws((disagreement("normal", "Level04", ("Level04",) * 4),))
        with self.assertRaisesRegex(ValueError, "SOURCE_FAMILY_NOT_BOOTSTRAP_CLUSTER"):
            bootstrap_draws(({
                "sample_id": "normal", "true_safety_level": "Level04", "folder_domain": "Power",
                "predictions": {model: "Level04" for model in MODEL_IDS},
                "point_id": "p", "source_family": "video-1",
            },))
        anomaly_rows = (
            disagreement("a1", "Level01", ("Level01",) * 4, point="arbitrary"),
            disagreement("a2", "Level02", ("Level02",) * 4, point="arbitrary"),
            disagreement("n", "Level04", ("Level04",) * 4, point="normal-point"),
        )
        draws = bootstrap_draws(anomaly_rows)
        self.assertTrue(any(draw.count("a1") != draw.count("a2") for draw in draws))
        seen_a, seen_b = [], []
        def stat_a(rows):
            seen_a.append(tuple(row.sample_id for row in rows))
            return 1.0
        def stat_b(rows):
            seen_b.append(tuple(row.sample_id for row in rows))
            return .5
        result = bootstrap(anomaly_rows, stat_a, statistic_b=stat_b)
        self.assertEqual(seen_a, seen_b)
        self.assertEqual(result["paired_difference"]["ci95"], [.5, .5])

    def test_versioned_contract_keeps_scope_guards(self):
        root = Path(__file__).resolve().parents[1]
        contract = strict_json((root / "configs/pre_freeze/d9r24_metric_contract.v1.json").read_bytes())
        self.assertEqual(contract["schema_version"], "d9r24-metric-contract-v1")
        self.assertEqual(contract["base_sha"], "6e205a53a9ceeebbc258d3ad0be6a7ddb865501e")
        self.assertEqual(contract["classification_models"], list(MODEL_IDS))
        self.assertFalse(contract["active_grounding_dependency"])
        self.assertFalse(contract["inspecsafe_inference_authorized"])
        self.assertEqual(contract["protocol_freeze"], "PENDING")
        self.assertEqual(contract["bootstrap"]["seed"], 42)
        self.assertEqual(contract["bootstrap"]["normal_missing_point_id"], "HARD_FAIL")
        self.assertEqual(contract["bootstrap"]["anomaly_cluster"],
                         "SAMPLE_LEVEL_WITH_DEPENDENCE_LIMITATION_NO_SOURCE_FAMILY")
        self.assertEqual(contract["rq3"]["risk_coverage_axes"],
                         ["eligible_relative_coverage", "overall_coverage"])

    def test_d9r22_d9r23_scope_and_policy_are_unchanged(self):
        root = Path(__file__).resolve().parents[1]
        base = "6e205a53a9ceeebbc258d3ad0be6a7ddb865501e"
        for path in (
            "configs/pre_freeze/d9r22_seminar_scope.v1.json",
            "configs/pre_freeze/production_classification_policy.d9r23.v1.json",
            "prompts/p2_classification_c1_v1.txt",
        ):
            before = subprocess.check_output(["git", "show", f"{base}:{path}"], cwd=root)
            self.assertEqual((root / path).read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
