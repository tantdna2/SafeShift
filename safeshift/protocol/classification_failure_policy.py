"""D9R23 parse-failure accounting examples/consumer contract, not a D5 engine.

No BA/Macro-F1 aggregation, strata, bootstrap or RQ3 metrics are implemented.
INVALID has no class; FN accounting must not fabricate a Level04 prediction.
"""

from .schema import SAFETY_LEVELS

VERSION = "classification-invalid-d9r23-v1"


def accounting(rows):
    """Rows are (true canonical level, predicted canonical level or None=INVALID).

    Undefined rates use None. Runtime/missing-attempt failures must be tracked
    separately by the future harness; do not silently turn them into rows here.
    """
    rows = list(rows)
    for true, predicted in rows:
        if true not in SAFETY_LEVELS or (predicted is not None and predicted not in SAFETY_LEVELS):
            raise ValueError("CANONICAL_LEVEL_OR_EXPLICIT_INVALID_REQUIRED")
    valid = [(t, p) for t, p in rows if p is not None]

    def rate(numerator, denominator):
        return {"numerator": numerator, "denominator": denominator,
                "value": numerator / denominator if denominator else None}

    valid_anomaly = [(t, p) for t, p in valid if t != "Level04"]
    valid_normal = [(t, p) for t, p in valid if t == "Level04"]
    valid_l1 = [(t, p) for t, p in valid if t == "Level01"]
    anomaly = [(t, p) for t, p in rows if t != "Level04"]
    l1 = [(t, p) for t, p in rows if t == "Level01"]
    return {
        "policy_version": VERSION, "total_n": len(rows), "valid_canonical_n": len(valid),
        "invalid_n": len(rows) - len(valid), "parse_success_rate": rate(len(valid), len(rows)),
        "invalid_output_rate": rate(len(rows) - len(valid), len(rows)),
        "four_class_counts": {level: {
            "true_n": sum(t == level for t, p in rows),
            "invalid_n": sum(t == level and p is None for t, p in rows),
            "tp": sum(t == p == level for t, p in rows),
            "fn": sum(t == level and p != level for t, p in rows),
            "fp": sum(t != level and p == level for t, p in rows),
        } for level in SAFETY_LEVELS},
        "parse_conditional": {
            "anomaly_fnr": rate(sum(p == "Level04" for t, p in valid_anomaly), len(valid_anomaly)),
            "anomaly_fpr": rate(sum(p != "Level04" for t, p in valid_normal), len(valid_normal)),
            "level01_recall": rate(sum(p == "Level01" for t, p in valid_l1), len(valid_l1)),
            "level01_fnr": rate(sum(p != "Level01" for t, p in valid_l1), len(valid_l1)),
        },
        "failure_aware": {
            "anomaly_non_detection_rate": rate(sum(p is None or p == "Level04" for t, p in anomaly), len(anomaly)),
            "level01_protection_failure": rate(sum(p != "Level01" for t, p in l1), len(l1)),
        },
    }
