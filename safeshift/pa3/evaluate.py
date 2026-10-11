"""Synthetic-only, score-conditional AUROC and explicit coverage denominators."""

import math

from safeshift.ls1.core import LEVELS
from safeshift.ls1.evaluate import auc
from . import VERSION
from .artifacts import json_bytes
from .policy import authorize
from .scoring import raw_record, score_raw
from .synthetic import ground_truth as synthetic_gt, specimen


def report(settings, rows, ground_truth, *, completed=False):
    settings = authorize(settings)
    expected_gt = synthetic_gt(settings)
    if type(ground_truth) is not dict or ground_truth != expected_gt:
        raise ValueError("EXACT_SYNTHETIC_GT_JOIN_REQUIRED")
    ids = [r["sample_id"] for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(expected_gt):
        raise ValueError("EXACT_UNIQUE_GT_JOIN_REQUIRED")
    by_id = {r["sample_id"]: r for r in rows}
    for name in settings["cases"]:
        sample = specimen(settings, name)
        row = by_id[sample["sample_id"]]
        if any(row.get(k) != v for k, v in sample.items()):
            raise PermissionError("BUILTIN_SYNTHETIC_RESULT_REQUIRED")
        if row["status"] not in ("SUCCESS", "INVALID", "TECHNICAL_ERROR", "INTERRUPTED", "UNPROCESSED", "NOT_ATTEMPTED"):
            raise ValueError("RESULT_STATUS_REQUIRED")
        if any(type(row[k]) is not bool for k in ("attempted", "persisted", "parsed")):
            raise ValueError("BOOLEAN_FLOW_REQUIRED")
        if row["parsed"] > row["persisted"] or row["persisted"] > row["attempted"]:
            raise ValueError("RESULT_FLOW_MISMATCH")
        if row["parsed"] != (row["generated_label"] in LEVELS):
            raise ValueError("PARSED_LABEL_MISMATCH")
        if row["status"] == "SUCCESS":
            if (not row["parsed"] or row["generated_label"] not in LEVELS
                    or type(row["score"]) not in (int, float) or not math.isfinite(row["score"])):
                raise ValueError("FINITE_PARSED_SUCCESS_REQUIRED")
            if json_bytes(row) != json_bytes(score_raw(settings, name, raw_record(settings, name))):
                raise ValueError("SYNTHETIC_RAW_RESULT_REQUIRED")
        elif row["score"] is not None or row["details"] is not None:
            raise ValueError("MISSING_SCORE_MUST_STAY_NULL")
        if row["status"] == "INVALID" and (row["parsed"] or not row["persisted"] or row["generated_label"] is not None):
            raise ValueError("INVALID_MUST_NOT_BE_RESCUED")
        if row["status"] == "NOT_ATTEMPTED" and row["attempted"]:
            raise ValueError("NOT_ATTEMPTED_FLOW_MISMATCH")
        if row["status"] in ("TECHNICAL_ERROR", "INTERRUPTED") and not row["persisted"]:
            raise ValueError("ERROR_EVIDENCE_REQUIRED")
        if row["status"] == "INTERRUPTED" and row["parsed"]:
            raise ValueError("INTERRUPTED_MUST_NOT_BE_PARSED")
        if row["status"] == "UNPROCESSED" and (not row["attempted"] or row["parsed"]):
            raise ValueError("UNPROCESSED_FLOW_MISMATCH")
    if type(completed) is not bool or (completed and any(r["status"] not in ("SUCCESS", "INVALID") for r in rows)):
        raise ValueError("COMPLETED_RUN_STATUS_MISMATCH")
    eligible = [r for r in rows if r["status"] == "SUCCESS"]
    truth = [ground_truth[r["sample_id"]] != "Level04" for r in eligible]
    positive, negative = sum(truth), len(truth) - sum(truth)

    def coverage(subset):
        n = sum(r["status"] == "SUCCESS" for r in subset)
        return {"scored": n, "planned": len(subset), "fraction": n / len(subset) if subset else None,
                "reason": None if subset else "NO_PLANNED_SAMPLES"}

    return {"schema": VERSION, "source": "BUILTIN_SYNTHETIC", "completed": completed,
            "scope": "SCORE_CONDITIONAL_SYNTHETIC_ONLY" if completed else "PARTIAL_RUN_DESCRIPTIVE_ONLY",
            "flow": {"planned": len(rows), "attempted": sum(r["attempted"] for r in rows),
                     "persisted": sum(r["persisted"] for r in rows), "parsed": sum(r["parsed"] for r in rows),
                     "scored": len(eligible)},
            "status_counts": {s: sum(r["status"] == s for r in rows) for s in
                              ("SUCCESS", "INVALID", "TECHNICAL_ERROR", "INTERRUPTED", "UNPROCESSED", "NOT_ATTEMPTED")},
            "coverage": {"overall": coverage(rows),
                         "by_level": {level: coverage([r for r in rows if ground_truth[r["sample_id"]] == level]) for level in LEVELS},
                         "by_binary_class": {label: coverage([r for r in rows if (ground_truth[r["sample_id"]] != "Level04") == anomaly])
                                             for label, anomaly in (("Anomaly", True), ("Normal", False))}},
            "auroc": {"value": auc(truth, [r["score"] for r in eligible]),
                      "reason": None if positive and negative else "MISSING_SCORED_ANOMALY_OR_NORMAL_CLASS",
                      "anomaly_n": positive, "normal_n": negative, "pair_denominator": positive * negative,
                      "eligible_ids": [r["sample_id"] for r in eligible], "tie_credit": 0.5,
                      "direction": "HIGHER_IS_ANOMALY", "full_cohort_auroc_inferred": False},
            "controls_same_eligible_ids": {
                "constant_score_auroc": auc(truth, [0.0] * len(eligible)),
                "always_Level03_auroc": auc(truth, [1.0] * len(eligible)),
                "generated_binary_label_auroc": auc(truth, [float(r["generated_label"] != "Level04") for r in eligible])},
            "uncertainty": "NOT_IMPLEMENTED_PENDING_SEPARATE_APPROVAL",
            "claim": "SOFTWARE_TEST_ONLY_NO_MODEL_DISCRIMINATION_EVIDENCE"}
