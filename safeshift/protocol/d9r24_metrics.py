"""Offline RQ1/RQ2/RQ3 metric contracts for the D9R24 Seminar scope.

This module consumes in-memory, already parsed classification records.  It does
not load data, images, model weights, or call a model.  ``None`` is INVALID and
is deliberately never coerced to a safety level.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import random
from statistics import median
from typing import Callable, Iterable, Mapping, Sequence

from .metrics import ClassificationInput
from .schema import Classification, HAZARDS, ParseResult, SAFETY_LEVELS

# The import above intentionally cannot import GROUPS from the historical
# metrics interface (it is not defined there).  Keep the active D6 groups local.
MODEL_IDS = ("qwen3", "qwen2_5", "internvl3", "moondream")
ORDINAL = {level: i + 1 for i, level in enumerate(SAFETY_LEVELS)}
RQ2_GROUPS = {
    "A_FIRE_AND_SMOKE": ("OPEN_FLAME", "SMOKE"),
    "B_PPE_ABSENCE": ("NO_GLOVES", "NO_HELMET", "NO_MASK"),
    "C_UNAUTHORIZED_BEHAVIOR": ("USE_MOBILE_PHONE", "SMOKING"),
    "D_ENVIRONMENTAL_SLIP_HAZARD": ("LIQUID_ON_GROUND",),
    "E_OBSTRUCTION_AND_FOREIGN_OBJECT": ("FOREIGN_OBJECT", "NONMOTORIZED_VEHICLE"),
    "F_EQUIPMENT_STATE_ANOMALY": ("DOOR_OPEN",),
    "G_PERSONNEL_FALLEN": ("PERSON_FALLEN",),
}
BOOTSTRAP_VERSION = "d9r24-domain-stratified-point-cluster-percentile-v1"
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 42


def _rate(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _finite(value: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _parse_value(value):
    """Return a canonical level or None for an explicit parse failure."""
    if isinstance(value, ParseResult):
        if not value.success:
            return None
        value = value.value
    if isinstance(value, Classification):
        value = value.safety_level
    if value is None:
        return None
    if value == "INVALID":
        # Explicit status spelling is accepted as an input marker only; it is
        # never emitted in a canonical prediction or treated as Level04.
        return None
    if type(value) is str and value in SAFETY_LEVELS:
        return value
    raise ValueError("canonical Level01-Level04 or explicit INVALID required")


def _classification_value(sample: ClassificationInput):
    return _parse_value(sample.prediction)


def _validate_unique(samples: Sequence, attr: str = "sample_id"):
    ids = [getattr(sample, attr) for sample in samples]
    if len(ids) != len(set(ids)):
        raise ValueError("one evaluation record per image required")


def _classification_counts(samples: Sequence[ClassificationInput]):
    counts = {true: {pred: 0 for pred in (*SAFETY_LEVELS, "INVALID")} for true in SAFETY_LEVELS}
    for sample in samples:
        predicted = _classification_value(sample)
        counts[sample.true_safety_level][predicted or "INVALID"] += 1
    return counts


def classification_metrics(samples: Iterable[ClassificationInput], *, required_classes=SAFETY_LEVELS) -> dict:
    """Compute D5 four-class and parse/failure-aware classification metrics."""
    rows = tuple(samples)
    _validate_unique(rows)
    if any(sample.true_safety_level not in SAFETY_LEVELS for sample in rows):
        raise ValueError("unknown ground-truth safety level")
    counts = _classification_counts(rows)
    support = {level: sum(counts[level].values()) for level in SAFETY_LEVELS}
    valid_n = sum(counts[true][pred] for true in SAFETY_LEVELS for pred in SAFETY_LEVELS)
    invalid_n = len(rows) - valid_n
    per_class = {}
    recalls = []
    f1s = []
    for level in SAFETY_LEVELS:
        true_n = support[level]
        tp = counts[level][level]
        predicted_n = sum(counts[true][level] for true in SAFETY_LEVELS)
        recall = tp / true_n if true_n else None
        precision = tp / predicted_n if predicted_n else (0.0 if true_n else None)
        f1 = (2 * tp / (true_n + predicted_n)) if (true_n + predicted_n) else None
        per_class[level] = {
            "support": true_n,
            "predicted": predicted_n,
            "true_positive": tp,
            "false_negative": true_n - tp,
            "false_positive": predicted_n - tp,
            "recall": recall,
            "precision": precision,
            "f1": f1,
        }
        if recall is not None:
            recalls.append(recall)
        if f1 is not None:
            f1s.append(f1)
    required = tuple(required_classes) if required_classes is not None else tuple(
        level for level in SAFETY_LEVELS if support[level]
    )
    if any(level not in SAFETY_LEVELS for level in required):
        raise ValueError("invalid required class")
    complete_support = all(support[level] > 0 for level in required)
    balanced_accuracy = (
        sum(per_class[level]["recall"] for level in required) / len(required)
        if required and complete_support else None
    )
    macro_f1 = (
        sum(per_class[level]["f1"] for level in required) / len(required)
        if required and complete_support else None
    )
    correct = sum(counts[level][level] for level in SAFETY_LEVELS)
    anomaly = tuple((sample, _classification_value(sample)) for sample in rows
                    if sample.true_safety_level != "Level04")
    normal = tuple((sample, _classification_value(sample)) for sample in rows
                   if sample.true_safety_level == "Level04")
    valid_anomaly = tuple((s, p) for s, p in anomaly if p is not None)
    valid_normal = tuple((s, p) for s, p in normal if p is not None)
    level01 = tuple((s, _classification_value(s)) for s in rows
                    if s.true_safety_level == "Level01")
    valid_level01 = tuple((s, p) for s, p in level01 if p is not None)
    anomaly_fnr = _rate(sum(pred == "Level04" for _, pred in valid_anomaly), len(valid_anomaly))
    anomaly_fpr = _rate(sum(pred != "Level04" for _, pred in valid_normal), len(valid_normal))
    anomaly_non_detection = _rate(
        sum(pred is None or pred == "Level04" for _, pred in anomaly), len(anomaly)
    )
    level01_recall = _rate(sum(pred == "Level01" for _, pred in valid_level01), len(valid_level01))
    level01_fnr = _rate(sum(pred != "Level01" for _, pred in valid_level01), len(valid_level01))
    level01_protection = _rate(sum(pred != "Level01" for _, pred in level01), len(level01))
    critical = {
        "level01_to_level02_or_level03": _rate(
            sum(pred in ("Level02", "Level03") for _, pred in level01), len(level01)),
        "level01_to_level04": _rate(sum(pred == "Level04" for _, pred in level01), len(level01)),
        "level01_to_level02_or_level03_parse_conditional": _rate(
            sum(pred in ("Level02", "Level03") for _, pred in valid_level01), len(valid_level01)),
        "level01_to_level04_parse_conditional": _rate(
            sum(pred == "Level04" for _, pred in valid_level01), len(valid_level01)),
    }
    confusion = {true: dict(row) for true, row in counts.items()}
    return {
        "metric_version": "d9r24-classification-v1",
        "n_images": len(rows),
        "total_n": len(rows),
        "valid_canonical_n": valid_n,
        "invalid_n": invalid_n,
        "parse_success_rate": _rate(valid_n, len(rows)),
        "invalid_output_rate": _rate(invalid_n, len(rows)),
        "evaluation_classes": list(required),
        "supported_classes": [level for level in SAFETY_LEVELS if support[level]],
        "K": sum(support[level] > 0 for level in SAFETY_LEVELS),
        "macro_scope": "FIXED_CLASS_SUPPORT" if required_classes is not None else "SUPPORTED_GT_CLASSES_DESCRIPTIVE",
        "comparability_warning": (
            "Do not directly compare domain macro metrics with different K_d; descriptive only."
            if required_classes is None and len(required) < len(SAFETY_LEVELS) else None
        ),
        "support": support,
        "balanced_accuracy": balanced_accuracy,
        "macro_f1": macro_f1,
        "raw_accuracy_descriptive": _rate(correct, len(rows)),
        "per_class": per_class,
        "confusion_matrix": confusion,
        "row_normalized_confusion_matrix": {
            true: {pred: value / support[true] if support[true] else None
                   for pred, value in row.items()}
            for true, row in confusion.items()
        },
        "prediction_distribution": {
            pred: sum(confusion[true][pred] for true in SAFETY_LEVELS)
            for pred in (*SAFETY_LEVELS, "INVALID")
        },
        "anomaly_fnr_parse_conditional": anomaly_fnr,
        "anomaly_fpr_parse_conditional": anomaly_fpr,
        "anomaly_recall_parse_conditional": _rate(
            sum(pred != "Level04" for _, pred in valid_anomaly), len(valid_anomaly)),
        "anomaly_support_n": len(anomaly),
        "anomaly_valid_n": len(valid_anomaly),
        "normal_support_n": len(normal),
        "normal_valid_n": len(valid_normal),
        "anomaly_non_detection_rate_failure_aware": anomaly_non_detection,
        "level01_recall_parse_conditional": level01_recall,
        "level01_fnr_parse_conditional": level01_fnr,
        "level01_protection_failure_failure_aware": level01_protection,
        "critical_downgrade_diagnostics": critical,
        "anomaly_to_normal_miss": {
            "parse_conditional": anomaly_fnr,
            "failure_aware": anomaly_non_detection,
        },
        "level01_critical_miss_to_level04": critical["level01_to_level04_parse_conditional"],
        "safety_level_confusion_distribution": confusion,
        "exact_safety_level_error_rate": _rate(len(rows) - correct, len(rows)),
        "invalid_is_not_a_safety_level": True,
        "status": "COMPUTED",
    }


def _spread(values: Iterable[float]) -> float | None:
    values = tuple(value for value in values if value is not None)
    return max(values) - min(values) if len(values) >= 2 else None


def rq1_metrics(samples: Iterable[ClassificationInput]) -> dict:
    """RQ1 pooled and folder_domain class-conditional diagnostics."""
    rows = tuple(samples)
    pooled = classification_metrics(rows)
    domains = {}
    for domain in sorted({sample.domain for sample in rows}):
        domain_rows = tuple(sample for sample in rows if sample.domain == domain)
        supported = tuple(level for level in SAFETY_LEVELS
                          if any(sample.true_safety_level == level for sample in domain_rows))
        domains[domain] = classification_metrics(domain_rows, required_classes=None)
        domains[domain]["supported_classes"] = list(supported)
        domains[domain]["K_d"] = len(supported)
        domains[domain]["comparability_warning"] = (
            "K_d<4: descriptive only; do not compare directly with K_d=4 domains."
            if len(supported) < len(SAFETY_LEVELS) else None
        )
        if domain == "metallurgy":
            domains[domain]["metallurgy_anomaly_policy"] = "SPARSE_SUPPORT_DESCRIPTIVE_ONLY"
    by_class = {}
    for level in SAFETY_LEVELS:
        pooled_recall = pooled["per_class"][level]["recall"]
        domain_rows = []
        for domain, summary in domains.items():
            row = summary["per_class"][level]
            recall = row["recall"]
            domain_rows.append({
                "folder_domain": domain,
                "domain": domain,
                "support_count": row["support"],
                "support": row["support"],
                "recall": recall,
                "pooled_to_domain_gap": (
                    pooled_recall - recall
                    if pooled_recall is not None and recall is not None else None
                ),
                "sparse_support_warning": domain == "metallurgy" and row["support"] <= 1,
            })
        recalls = [row["recall"] for row in domain_rows if row["recall"] is not None]
        worst = min(recalls) if recalls else None
        by_class[level] = {
            "per_folder_domain": domain_rows,
            "observed_worst_domain": worst,
            "observed_worst_domains": [
                row["folder_domain"] for row in domain_rows if row["recall"] == worst
            ],
            "domain_spread": _spread(recalls),
        }
    k4_domains = [domain for domain, summary in domains.items() if summary["K_d"] == 4]
    k4_values = [domains[domain]["balanced_accuracy"] for domain in k4_domains]
    anomaly_domains = [domain for domain, summary in domains.items()
                       if summary["anomaly_support_n"] > 0]
    anomaly_values = [domains[domain]["anomaly_recall_parse_conditional"]["value"]
                      for domain in anomaly_domains
                      if domains[domain]["anomaly_recall_parse_conditional"]["value"] is not None]
    anomaly_spread = _spread(anomaly_values)
    return {
        "metric_version": "d9r24-rq1-v1",
        "domain_policy": "D3_FOLDER_DOMAIN_WITH_UNCHANGED_MISMATCH_SENSITIVITY",
        "robot_platform_claim": "CO_VARIATION_ONLY_NO_CAUSAL_CLAIM",
        "pooled": pooled,
        "domains": domains,
        "per_class_recall_by_folder_domain": by_class,
        "support_count_by_domain": {
            domain: summary["total_n"] for domain, summary in domains.items()
        },
        "observed_worst_domain": {
            level: row["observed_worst_domains"] for level, row in by_class.items()
        },
        "domain_spread_diagnostics": {
            level: row["domain_spread"] for level, row in by_class.items()
        },
        "balanced_accuracy_domain_spread": {
            "participating_domains": k4_domains,
            "balanced_accuracy_by_domain": {
                domain: domains[domain]["balanced_accuracy"] for domain in k4_domains
            },
            "max": max(k4_values) if k4_values else None,
            "min": min(k4_values) if k4_values else None,
            "spread": _spread(k4_values),
            "status": "SECONDARY_DIAGNOSTIC_K4_ONLY",
        },
        "anomaly_recall_spread": {
            "domains_with_anomaly_support": anomaly_domains,
            "anomaly_support_by_domain": {
                domain: domains[domain]["anomaly_support_n"] for domain in anomaly_domains
            },
            "anomaly_recall_by_domain": {
                domain: domains[domain]["anomaly_recall_parse_conditional"] for domain in anomaly_domains
            },
            "spread": anomaly_spread,
            "status": "PARSE_CONDITIONAL_ANOMALY_SUPPORTED_DOMAINS_ONLY",
        },
        "metallurgy_sparse_support_warning": any(
            domain == "metallurgy" and summary.get("metallurgy_anomaly_policy") == "SPARSE_SUPPORT_DESCRIPTIVE_ONLY"
            for domain, summary in domains.items()
        ),
        "metallurgy_anomaly_methodology": (
            "SPARSE_SUPPORT_DESCRIPTIVE_ONLY" if "metallurgy" in domains else None
        ),
    }


def rq2_metrics(samples: Iterable[ClassificationInput], *, grouped: bool = False) -> dict:
    """RQ2 image-level metrics over non-additive atom/group membership strata."""
    rows = tuple(samples)
    strata = RQ2_GROUPS if grouped else {hazard: (hazard,) for hazard in HAZARDS}
    result = {}
    for name, members in strata.items():
        subset = tuple(sample for sample in rows
                       if sample.rq2_atom_memberships.intersection(members))
        metrics = classification_metrics(subset)
        metrics.update({
            "stratum": name,
            "support_n": len(subset),
            "support_warning": "SPARSE_SUPPORT" if len(subset) <= 1 else None,
            "membership_semantics": "IMAGE_LEVEL_OVERLAPPING_NON_ADDITIVE",
        })
        result[name] = metrics
    return {
        "metric_version": "d9r24-rq2-v1",
        "analysis_level": "SECONDARY_EXPLORATORY" if grouped else "PRIMARY_RQ2_STRATA",
        "prediction_unit": "IMAGE",
        "strata": result,
        "stratum_count": len(result),
        "non_additive": True,
        "counts_additive": False,
        "multi_hazard_membership_allowed": True,
        "hazard_membership_used_after_inference": True,
        "aggregation_across_strata": "FORBIDDEN",
    }


@dataclass(frozen=True)
class DisagreementSample:
    """One image's four already-parsed classification predictions."""

    sample_id: str
    true_safety_level: str
    folder_domain: str
    predictions: Mapping[str, object]
    hazard_memberships: frozenset[str] = frozenset()
    point_id: str | None = None
    parse_status: Mapping[str, str] | None = None

    def __post_init__(self):
        if type(self.sample_id) is not str or not self.sample_id:
            raise ValueError("sample_id required")
        if self.true_safety_level not in SAFETY_LEVELS:
            raise ValueError("unknown ground-truth safety level")
        if type(self.folder_domain) is not str or not self.folder_domain:
            raise ValueError("folder_domain required")
        if set(self.predictions) != set(MODEL_IDS):
            raise ValueError("exactly qwen3, qwen2_5, internvl3 and moondream required")
        normalized = {model: _parse_value(self.predictions[model]) for model in MODEL_IDS}
        if self.parse_status is not None and set(self.parse_status) != set(MODEL_IDS):
            raise ValueError("parse_status must cover all four models")
        if self.parse_status:
            for model, status in self.parse_status.items():
                if status == "SUCCESS" and normalized[model] is None:
                    raise ValueError("SUCCESS requires a canonical prediction")
                if status != "SUCCESS" and normalized[model] is not None:
                    raise ValueError("INVALID parse cannot carry a canonical prediction")
        object.__setattr__(self, "predictions", normalized)
        object.__setattr__(self, "hazard_memberships", frozenset(self.hazard_memberships))
        # point_id is optional for ordinary metric calculation. Bootstrap
        # validates it only for Normal records; there is no silent fallback.
        if self.point_id is not None and (type(self.point_id) is not str or not self.point_id):
            raise ValueError("point_id must be a non-empty string when supplied")
        if not self.hazard_memberships <= set(HAZARDS):
            raise ValueError("unknown hazard membership")


RQ3Sample = DisagreementSample


def _coerce_disagreement(value) -> DisagreementSample:
    if isinstance(value, DisagreementSample):
        return value
    if isinstance(value, Mapping):
        if "source_family" in value:
            raise ValueError("SOURCE_FAMILY_NOT_BOOTSTRAP_CLUSTER")
        return DisagreementSample(
            sample_id=value["sample_id"],
            true_safety_level=value["true_safety_level"],
            folder_domain=value.get("folder_domain", value.get("domain")),
            predictions=value["predictions"],
            hazard_memberships=frozenset(value.get("hazard_memberships", value.get("hazards", ()))),
            point_id=value.get("point_id"),
            parse_status=value.get("parse_status"),
        )
    raise TypeError("RQ3 records must be DisagreementSample or mapping")


def _joint(rows: Sequence[DisagreementSample]) -> tuple[DisagreementSample, ...]:
    return tuple(row for row in rows if all(row.predictions[model] is not None for model in MODEL_IDS))


def _vote_pattern(predictions: Sequence[str]) -> str:
    shape = sorted(Counter(predictions).values(), reverse=True)
    return {
        (4,): "UNANIMOUS_4_0",
        (3, 1): "MAJORITY_3_1",
        (2, 1, 1): "PLURALITY_2_1_1",
        (2, 2): "TIE_2_2",
        (1, 1, 1, 1): "ALL_DIFFERENT_1_1_1_1",
    }[tuple(shape)]


def _entropy(predictions: Sequence[str]) -> float:
    counts = Counter(predictions)
    value = -sum((count / 4) * math.log(count / 4) for count in counts.values()) / math.log(4)
    if abs(value) < 1e-15:
        value = 0.0
    if not _finite(value) or not 0 <= value <= 1:
        raise ValueError("vote entropy outside [0,1]")
    return value


def _ordinal_disagreement(predictions: Sequence[str]) -> float:
    values = [ORDINAL[prediction] for prediction in predictions]
    value = sum(abs(left - right) for i, left in enumerate(values)
                for right in values[i + 1:]) / 6 / 3
    if not _finite(value) or not 0 <= value <= 1:
        raise ValueError("ordinal disagreement outside [0,1]")
    return value


def _kappa(left: Sequence[str], right: Sequence[str]) -> dict:
    n = len(left)
    if n == 0:
        return {"value": None, "observed_agreement": None, "expected_agreement": None, "n": 0,
                "status": "UNDEFINED_NO_JOINT_VALID_PAIRS"}
    observed = sum(a == b for a, b in zip(left, right)) / n
    left_counts, right_counts = Counter(left), Counter(right)
    expected = sum((left_counts[level] / n) * (right_counts[level] / n)
                   for level in SAFETY_LEVELS)
    if expected == 1:
        value = None
        status = "UNDEFINED_DEGENERATE_MARGINALS"
    else:
        value = (observed - expected) / (1 - expected)
        status = "COMPUTED"
    return {"value": value, "observed_agreement": observed, "expected_agreement": expected, "n": n,
            "status": status}


def _risk_curve(eligible: Sequence[tuple[DisagreementSample, str, float, float]], total_n: int) -> dict:
    curve = [{"sample_id": None, "eligible_relative_coverage": 0.0, "overall_coverage": 0.0, "n": 0,
              "exact_ensemble_error": None,
              "normalized_ordinal_severity_error": None,
              "safety_critical_anomaly_to_level04_failure": None}]
    exact, ordinal, critical = 0, 0.0, 0
    anomaly_seen = 0
    for index, (row, label, _, _) in enumerate(eligible, start=1):
        exact += label != row.true_safety_level
        ordinal += abs(ORDINAL[label] - ORDINAL[row.true_safety_level]) / 3
        if row.true_safety_level != "Level04":
            anomaly_seen += 1
            critical += label == "Level04"
        exact_rate = _rate(exact, index)
        ordinal_rate = _rate(ordinal, index)
        critical_rate = _rate(critical, anomaly_seen)
        curve.append({
            "sample_id": row.sample_id,
            "eligible_relative_coverage": index / len(eligible),
            "overall_coverage": index / total_n if total_n else None,
            "n": index,
            "exact_ensemble_error": exact_rate,
            "normalized_ordinal_severity_error": ordinal_rate,
            "safety_critical_anomaly_to_level04_failure": critical_rate,
        })
    if not eligible:
        return {"curve": curve, "aurc_eligible_cohort": None,
                "aurc_axis": "eligible_relative_coverage",
                "baseline_risk_at_full_eligible_coverage": None}
    aurc = 0.0
    for left, right in zip(curve, curve[1:]):
        aurc += (right["eligible_relative_coverage"] - left["eligible_relative_coverage"]) * (
            ((left["exact_ensemble_error"] or {}).get("value") or 0.0)
            + right["exact_ensemble_error"]["value"]
        ) / 2
    return {
        "curve": curve,
        "aurc_eligible_cohort": aurc,
        "aurc_axis": "eligible_relative_coverage",
        "baseline_risk_at_full_eligible_coverage": curve[-1],
    }


def _core_rq3(rows: Sequence[DisagreementSample]) -> dict:
    rows = tuple(sorted(rows, key=lambda row: row.sample_id))
    joint = _joint(rows)
    invalid_counts = {
        model: sum(row.predictions[model] is None for row in rows) for model in MODEL_IDS
    }
    patterns = Counter()
    entropies, ordinal_values = [], []
    unanimous_correct = unanimous_wrong = 0
    unanimous_wrong_anomaly = unanimous_l1_downgrade = unanimous_l4 = unanimous_l34 = 0
    any_wrong_unanimous = any_wrong_disagreement = 0
    unanimous_n = disagreement_n = 0
    model_errors = {model: set() for model in MODEL_IDS}
    eligible = []
    for row in joint:
        predictions = tuple(row.predictions[model] for model in MODEL_IDS)
        pattern = _vote_pattern(predictions)
        patterns[pattern] += 1
        entropy = _entropy(predictions)
        ordinal = _ordinal_disagreement(predictions)
        entropies.append(entropy)
        ordinal_values.append(ordinal)
        wrong = any(prediction != row.true_safety_level for prediction in predictions)
        for model in MODEL_IDS:
            if row.predictions[model] != row.true_safety_level:
                model_errors[model].add(row.sample_id)
        if pattern == "UNANIMOUS_4_0":
            unanimous_n += 1
            if wrong:
                unanimous_wrong += 1
                any_wrong_unanimous += 1
            else:
                unanimous_correct += 1
        else:
            disagreement_n += 1
            if wrong:
                any_wrong_disagreement += 1
        if row.true_safety_level != "Level04" and pattern == "UNANIMOUS_4_0" and predictions[0] == "Level04":
            unanimous_wrong_anomaly += 1
        if row.true_safety_level == "Level01" and pattern == "UNANIMOUS_4_0" and ORDINAL[predictions[0]] > 1:
            unanimous_l1_downgrade += 1
            if predictions[0] == "Level04":
                unanimous_l4 += 1
            if predictions[0] in ("Level03", "Level04"):
                unanimous_l34 += 1
        if pattern != "TIE_2_2":
            winning_count = Counter(predictions).most_common()
            if len(winning_count) == 1 or winning_count[0][1] > winning_count[1][1]:
                label = winning_count[0][0]
                eligible.append((row, label, ordinal, entropy))
    eligible.sort(key=lambda item: (item[2], item[3], item[0].sample_id))
    pairwise = {}
    for i, left in enumerate(MODEL_IDS):
        for right in MODEL_IDS[i + 1:]:
            pair = f"{left}__{right}"
            pairwise[pair] = _kappa(
                [row.predictions[left] for row in joint],
                [row.predictions[right] for row in joint],
            )
    entropy_distribution = {"mean": _mean(entropies), "median": median(entropies) if entropies else None,
                            "values": entropies}
    ordinal_distribution = {"mean": _mean(ordinal_values), "median": median(ordinal_values) if ordinal_values else None,
                            "values": ordinal_values}
    complementarity = {}
    for left in MODEL_IDS:
        for right in MODEL_IDS:
            if left == right:
                continue
            left_wrong = model_errors[left]
            right_wrong = model_errors[right]
            union = left_wrong | right_wrong
            complementarity[f"{left}_to_{right}"] = {
                "p_b_correct_given_a_wrong": _rate(len(left_wrong - right_wrong), len(left_wrong)),
                "double_fault_rate": _rate(len(left_wrong & right_wrong), len(joint)),
                "error_set_jaccard": _rate(len(left_wrong & right_wrong), len(union)),
            }
    association = {
        "p_any_model_wrong_given_unanimous": _rate(any_wrong_unanimous, unanimous_n),
        "p_any_model_wrong_given_any_disagreement": _rate(any_wrong_disagreement, disagreement_n),
        "error_enrichment_disagreement_vs_unanimous": (
            (any_wrong_disagreement / disagreement_n) / (any_wrong_unanimous / unanimous_n)
            if disagreement_n and unanimous_n and any_wrong_unanimous else None
        ),
        "by_vote_pattern": {},
    }
    for pattern in sorted(patterns):
        subset = tuple(row for row in joint if _vote_pattern(tuple(row.predictions[m] for m in MODEL_IDS)) == pattern)
        association["by_vote_pattern"][pattern] = {
            "n": len(subset),
            "any_model_wrong": sum(any(row.predictions[m] != row.true_safety_level for m in MODEL_IDS) for row in subset),
            "any_model_wrong_rate": _rate(
                sum(any(row.predictions[m] != row.true_safety_level for m in MODEL_IDS) for row in subset), len(subset)
            ),
        }
    risk = _risk_curve(eligible, len(rows))
    joint_anomaly_n = sum(row.true_safety_level != "Level04" for row in joint)
    joint_level01_n = sum(row.true_safety_level == "Level01" for row in joint)
    tie_n = sum(
        _vote_pattern(tuple(row.predictions[m] for m in MODEL_IDS)) == "TIE_2_2" for row in joint
    )
    no_unique_winner_n = sum(
        _vote_pattern(tuple(row.predictions[m] for m in MODEL_IDS)) == "ALL_DIFFERENT_1_1_1_1"
        for row in joint
    )
    return {
        "n": len(rows),
        "joint_valid_4_n": len(joint),
        "joint_parse_availability_rate": _rate(len(joint), len(rows)),
        "invalid_count_by_model": invalid_counts,
        "outside_joint_valid_4_n": len(rows) - len(joint),
        "unanimous_agreement": {
            "rate": _rate(patterns["UNANIMOUS_4_0"], len(joint)),
            "unanimous_correct": unanimous_correct,
            "unanimous_wrong": unanimous_wrong,
            "unanimous_wrong_rate_among_unanimous": _rate(unanimous_wrong, unanimous_n),
        },
        "pairwise_cohens_kappa": pairwise,
        "vote_entropy": entropy_distribution,
        "ordinal_disagreement": ordinal_distribution,
        "vote_pattern_classes": {
            pattern: {"n": patterns[pattern], "rate": _rate(patterns[pattern], len(joint))}
            for pattern in ("UNANIMOUS_4_0", "MAJORITY_3_1", "PLURALITY_2_1_1", "TIE_2_2", "ALL_DIFFERENT_1_1_1_1")
        },
        "shared_blind_spots": {
            "unanimous_wrong": _rate(unanimous_wrong, len(joint)),
            "unanimous_normal_on_anomaly": _rate(unanimous_wrong_anomaly, joint_anomaly_n),
            "unanimous_normal_on_anomaly_count": unanimous_wrong_anomaly,
            "joint_anomaly_n": joint_anomaly_n,
            "unanimous_level01_critical_downgrade": _rate(unanimous_l1_downgrade, joint_level01_n),
            "unanimous_level01_to_level04": _rate(unanimous_l4, joint_level01_n),
            "unanimous_level01_to_level03_or_level04": _rate(unanimous_l34, joint_level01_n),
        },
        "error_complementarity": complementarity,
        "disagreement_error_association": association,
        "selective_reliability": {
            "ranking": "ORDINAL_DISAGREEMENT_ASC_THEN_VOTE_ENTROPY_ASC_THEN_SAMPLE_ID_LEXICAL",
            "eligible_n": len(eligible),
            "eligible_coverage": _rate(len(eligible), len(rows)),
            "abstention_due_invalid": len(rows) - len(joint),
            "abstention_due_tie": tie_n,
            "abstention_due_no_unique_winner": no_unique_winner_n,
            "abstention_total": len(rows) - len(eligible),
            "ensemble_label_policy": "UNIQUE_PLURALITY_OR_MAJORITY_ONLY",
            "risk_definitions": ["exact_ensemble_error", "normalized_ordinal_severity_error",
                                  "safety_critical_anomaly_to_level04_failure"],
            **risk,
        },
        "status": "COMPUTED" if joint else "NO_JOINT_VALID_4",
    }


def rq3_metrics(records: Iterable[DisagreementSample | Mapping]) -> dict:
    """Compute pooled, domain and non-additive hazard-stratum RQ3 metrics."""
    rows = tuple(sorted((_coerce_disagreement(record) for record in records), key=lambda row: row.sample_id))
    _validate_unique(rows)
    pooled = _core_rq3(rows)
    by_domain = {
        domain: _core_rq3(tuple(row for row in rows if row.folder_domain == domain))
        for domain in sorted({row.folder_domain for row in rows})
    }
    by_hazard = {
        hazard: _core_rq3(tuple(row for row in rows if hazard in row.hazard_memberships))
        for hazard in HAZARDS
    }
    grouped = {
        name: _core_rq3(tuple(row for row in rows if row.hazard_memberships.intersection(members)))
        for name, members in RQ2_GROUPS.items()
    }
    return {
        "metric_version": "d9r24-rq3-v1",
        "models": list(MODEL_IDS),
        "pooled": pooled,
        "by_folder_domain": by_domain,
        "by_hazard_atom": by_hazard,
        "by_group_secondary_exploratory": grouped,
        "hazard_strata_non_additive": True,
        "invalid_is_not_a_safety_level": True,
        "additional_model_inference": False,
    }


def bootstrap_draws(records: Iterable[DisagreementSample | Mapping], *, replicates=BOOTSTRAP_REPLICATES,
                    seed=BOOTSTRAP_SEED) -> tuple[tuple[str, ...], ...]:
    """Domain-stratified draws: Normal point clusters, anomaly sample units.

    A Normal record without explicit ``point_id`` is a hard error.  Anomaly
    point-like metadata is intentionally ignored until a separately validated
    dependence protocol exists; no source-family or inferred event cluster is
    accepted here.
    """
    if replicates not in (2000, 5000) or seed != BOOTSTRAP_SEED:
        raise ValueError("D9R24 requires B=2000 (5000 convergence only), seed=42")
    rows = tuple(sorted((_coerce_disagreement(record) for record in records), key=lambda row: row.sample_id))
    _validate_unique(rows)
    if not rows:
        raise ValueError("nonempty records required")
    domains = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row.true_safety_level == "Level04":
            if not row.point_id:
                raise ValueError("NORMAL_POINT_ID_REQUIRED_FOR_BOOTSTRAP")
            cluster_key = "normal-point:" + row.point_id
        else:
            # Current anomaly dependence is unresolved.  Resample anomaly
            # images as sample-level units even if an arbitrary point_id exists.
            cluster_key = "anomaly-sample:" + row.sample_id
        domains[row.folder_domain][cluster_key].append(row.sample_id)
    rng = random.Random(seed)
    draws = []
    for _ in range(replicates):
        draw = []
        for domain in sorted(domains):
            clusters = domains[domain]
            keys = tuple(sorted(clusters))
            for _ in keys:
                draw.extend(clusters[keys[rng.randrange(len(keys))]])
        draws.append(tuple(draw))
    return tuple(draws)


def percentile_ci(values: Iterable[float | None], *, paired=False) -> dict:
    values = tuple(values)
    if len(values) not in (2000, 5000):
        raise ValueError("D9R24 replicate count required")
    if any(value is not None and not _finite(value) for value in values):
        raise ValueError("finite metric values or None required")
    valid = sorted(value for value in values if value is not None)
    if not valid:
        ci = None
    else:
        def quantile(p):
            position = (len(valid) - 1) * p
            low, high = math.floor(position), math.ceil(position)
            return valid[low] + (valid[high] - valid[low]) * (position - low)
        ci = [quantile(.025), quantile(.975)]
    return {
        "ci95": ci,
        "B": len(values),
        "seed": BOOTSTRAP_SEED,
        "valid_replicates": len(valid),
        "valid_paired_replicates": len(valid) if paired else None,
        "valid_fraction": len(valid) / len(values),
        "method": "DOMAIN_STRATIFIED_POINT_CLUSTER_PERCENTILE",
        "version": BOOTSTRAP_VERSION,
        "stratification": "FOLDER_DOMAIN_ONLY",
        "normal_cluster": "point_id (logical folder, not verified physical site)",
        "anomaly_policy": "ANOMALY_SAMPLE_LEVEL_RESAMPLING_WITH_DEPENDENCE_LIMITATION",
        "cluster": "NORMAL:point_id; ANOMALY:sample_id",
        "missing_class_replicate": "NA",
    }


def bootstrap(records: Iterable[DisagreementSample | Mapping], statistic: Callable,
              *, statistic_b: Callable | None = None, replicates=BOOTSTRAP_REPLICATES) -> dict:
    """Run a deterministic bootstrap; paired statistics share exactly the same draws."""
    rows = tuple(sorted((_coerce_disagreement(record) for record in records), key=lambda row: row.sample_id))
    by_id = {row.sample_id: row for row in rows}
    draws = bootstrap_draws(rows, replicates=replicates)
    a = tuple(statistic(tuple(by_id[sample_id] for sample_id in draw)) for draw in draws)
    result = {
        "a": percentile_ci(a),
        "draws_sha256": hashlib.sha256(json.dumps(draws, separators=(",", ":")).encode()).hexdigest(),
    }
    if statistic_b is not None:
        b = tuple(statistic_b(tuple(by_id[sample_id] for sample_id in draw)) for draw in draws)
        difference = tuple(x - y if x is not None and y is not None else None for x, y in zip(a, b))
        result.update(b=percentile_ci(b), paired_difference=percentile_ci(difference, paired=True))
    return result


class D9R24MetricEngine:
    """Small object facade used by reporting and future benchmark harnesses."""

    version = "d9r24-metric-engine-v1"

    def classification(self, samples):
        return classification_metrics(samples)

    def rq1(self, samples):
        return rq1_metrics(samples)

    def rq2(self, samples, *, grouped=False):
        return rq2_metrics(samples, grouped=grouped)

    def rq3(self, records):
        return rq3_metrics(records)


# Functional names mirror the D5 consumer interface while keeping the active
# D9R24 implementation separate from historical grounding code.
classification = classification_metrics
rq1 = rq1_metrics
rq2 = rq2_metrics
rq3 = rq3_metrics
compute_classification_metrics = classification_metrics
compute_rq1 = rq1_metrics
compute_rq2 = rq2_metrics
compute_rq3 = rq3_metrics
