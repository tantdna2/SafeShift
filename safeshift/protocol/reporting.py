"""Deterministic classification/disagreement report for D9R24.

The report accepts parsed in-memory records only.  It intentionally has no
dataset, image, model, GPU, or InspecSafe access.
"""

from __future__ import annotations

import json

from .d9r24_metrics import D9R24MetricEngine, rq1_metrics, rq2_metrics, rq3_metrics

REPORT_VERSION = "d9r24-report-v1"


def build_report(*, classification_samples=(), disagreement_samples=(), bootstrap_metadata=None):
    classification_samples = tuple(classification_samples)
    disagreement_samples = tuple(disagreement_samples)
    engine = D9R24MetricEngine()
    rq3 = rq3_metrics(disagreement_samples) if disagreement_samples else {
        "metric_version": "d9r24-rq3-v1", "models": ["qwen3", "qwen2_5", "internvl3", "moondream"],
        "pooled": {"status": "NO_INPUT"}, "by_folder_domain": {}, "by_hazard_atom": {},
        "by_group_secondary_exploratory": {}, "hazard_strata_non_additive": True,
        "invalid_is_not_a_safety_level": True, "additional_model_inference": False,
    }
    if classification_samples:
        rq1 = rq1_metrics(classification_samples)
        rq2_primary = rq2_metrics(classification_samples)
        rq2_secondary = rq2_metrics(classification_samples, grouped=True)
    else:
        rq1 = rq2_primary = rq2_secondary = {"status": "NO_INPUT", "metrics": None}
    pooled = rq3["pooled"]
    return {
        "report_version": REPORT_VERSION,
        "protocol_identity": {
            "scope": "d9r22_seminar_scope.v1",
            "metric_contract": "d9r24-metric-contract-v1",
            "metric_engine": engine.version,
            "classification_only": True,
            "grounding": "DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE",
        },
        "model_identities": list(rq3["models"]),
        "cohort_parse_availability": {
            "total_n": pooled.get("n", 0),
            "joint_valid_4_n": pooled.get("joint_valid_4_n", 0),
            "joint_parse_availability_rate": pooled.get("joint_parse_availability_rate"),
            "invalid_count_by_model": pooled.get("invalid_count_by_model", {}),
            "outside_joint_valid_4_n": pooled.get("outside_joint_valid_4_n", 0),
        },
        "RQ1": rq1,
        "RQ2_primary": rq2_primary,
        "RQ2_secondary_exploratory": rq2_secondary,
        "RQ3_pooled": pooled,
        "RQ3_by_domain": rq3["by_folder_domain"],
        "RQ3_by_hazard": rq3["by_hazard_atom"],
        "shared_blind_spots": pooled.get("shared_blind_spots"),
        "selective_reliability": pooled.get("selective_reliability"),
        "bootstrap_metadata": bootstrap_metadata or {"status": "NOT_COMPUTED"},
        "limitations": [
            "No model inference or InspecSafe inference is performed by this report.",
            "INVALID is not a safety level and is never mapped to Level04.",
            "Hazard atom and A-G rows overlap and are not additive.",
            "Grounding remains deferred outside the primary Seminar scope.",
            "Protocol freeze remains PENDING.",
        ],
        "inspecsafe_inference_authorized": False,
        "protocol_freeze": "PENDING",
    }


def render_json(report):
    """Serialize a report with stable ordering and no NaN/Infinity."""
    return json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"


# Short aliases used by callers that refer to the report as ``report``.
report = build_report
