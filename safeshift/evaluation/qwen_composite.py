"""Versioned, saved-label TRAIN composite; no inference or GT-based selection.

Archive authentication belongs to scripts.build_qwen3_composite. This module
validates the normalized handoff and computes image-weighted descriptive metrics.
"""

from collections import Counter
import hashlib
import json
from math import isfinite
import re

from safeshift.data.schema import SAFETY_LEVELS as LEVELS
from safeshift.evaluation.sensitivity import weighted_auc

PRODUCT = "QWEN3_FULL_TRAIN_COMPOSITE_V1"
PROVENANCE_FIELDS = ("run_id", "attempt_id", "model_id", "revision", "source_commit",
                     "authority_commit", "merge_commit", "source_payload_sha256",
                     "config_sha256", "archive_sha256", "manifest_sha256",
                     "samples_sha256", "result_sha256", "inference_sha256")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def index(rows):
    result = {}
    for row in rows:
        sid = row.get("sample_id")
        require(isinstance(sid, str) and bool(sid.strip()) and sid not in result,
                "nonempty unique ID required")
        result[sid] = row
    return result


def finite_score(value):
    if value is None or value == "":
        return None, "MISSING_SCORE"
    try:
        score = float(value)
    except (ValueError, TypeError, OverflowError):
        return None, "NONFINITE_OR_INVALID_SCORE"
    if isinstance(value, bool) or not isfinite(score):
        return None, "NONFINITE_OR_INVALID_SCORE"
    return score, None


def compose(master, original, recovery, sources, expected_counts):
    """Select by original status and ID only, then check GT and provenance.

    Recovery must equal the entire non-SUCCESS complement, without any overlap
    with original successes. A GT mismatch rejects the product, never selects
    an alternative prediction. Original records are returned separately intact.
    """
    meta, base, repair = map(index, (master, original, recovery))
    require(bool(meta) and set(meta) == set(base), "exact original TRAIN ID set required")
    require(Counter(r["status"] for r in original) == expected_counts,
            "original status counts mismatch")
    require(all(r["status"] in {"SUCCESS", "TECHNICAL_ERROR", "NOT_ATTEMPTED"}
                for r in original), "unexpected original status")
    missing = {sid for sid, r in base.items() if r["status"] != "SUCCESS"}
    require(set(repair) == missing, "recovery must exactly equal original non-SUCCESS IDs")
    for ledger, kind in ((original, "V4_ORIGINAL"), (recovery, "RECOVERY224")):
        for row in ledger:
            source = sources.get(row.get("source_id"), {})
            require(source.get("kind") == kind, "wrong ledger source kind")
            for key in PROVENANCE_FIELDS:
                require(bool(source.get(key)) and row.get(key) == source[key],
                        "ledger source identity mismatch: " + key)
    # Resolve membership before inspecting GT, labels or scores.
    selected = [(sid, repair[sid] if sid in missing else base[sid]) for sid in meta]
    output = []
    for sid, row in selected:
        m = meta[sid]
        require(m.get("split") == "TRAIN" and m["level"] in LEVELS,
                "canonical original TRAIN label required")
        require(isinstance(m["image_sha256"], str) and
                re.fullmatch(r"[0-9a-f]{64}", m["image_sha256"]) is not None,
                "original image SHA256 required")
        # Also validate the original failed record, not merely its replacement.
        for candidate in (base[sid], row):
            require(candidate.get("split") == "TRAIN" and
                    candidate["image_sha256"] == m["image_sha256"] and
                    candidate["true_level"] == m["level"] and candidate["domain"] == m["domain"],
                    "ID/hash/GT/domain/split mismatch")
        require(row["status"] == "SUCCESS" and row["generated_label"] in LEVELS,
                "selected canonical SUCCESS required")
        source_id = row["source_id"]
        require(source_id in sources, "unknown source configuration")
        source = sources[source_id]
        require(source["kind"] == ("RECOVERY224" if sid in missing else "V4_ORIGINAL"),
                "wrong source kind")
        for key in PROVENANCE_FIELDS:
            require(bool(source.get(key)) and row.get(key) == source[key],
                    "source identity mismatch: " + key)
        score, reason = finite_score(row.get("hnlo_score"))
        output.append({**row, "hnlo_score": score, "hnlo_unavailable_reason": reason,
                       "product_id": PRODUCT, "original_status": base[sid]["status"],
                       "original_source_id": base[sid]["source_id"],
                       "original_ordinal": base[sid]["source_ordinal"],
                       "selection_reason": "ORIGINAL_NON_SUCCESS" if sid in missing else "ORIGINAL_SUCCESS"})
    return output


def ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def metrics(rows):
    """4x5 confusion, INVALID-inclusive support, four-class and binary metrics.

    Macro-F1 averages only classes with positive GT support; a supported class
    with no positive predictions has F1=0. Empty strata return null ratios.
    """
    cm = {t: {p: 0 for p in (*LEVELS, "INVALID")} for t in LEVELS}
    for r in rows:
        t, p = r["true_level"], r["generated_label"]
        require(t in LEVELS and p in (*LEVELS, "INVALID"), "canonical metric labels required")
        cm[t][p] += 1
    support = {t: sum(cm[t].values()) for t in LEVELS}
    per_class = {}
    for t in LEVELS:
        tp, predicted = cm[t][t], sum(cm[y][t] for y in LEVELS)
        per_class[t] = {"support": support[t], "predicted_n": predicted,
                        "precision": ratio(tp, predicted), "recall": ratio(tp, support[t]),
                        "f1": ratio(2 * tp, support[t] + predicted)}
    supported = [t for t in LEVELS if support[t]]
    n, correct = len(rows), sum(cm[t][t] for t in LEVELS)
    anomaly, normal = sum(support[t] for t in LEVELS[:-1]), support["Level04"]
    tp = sum(cm[t][p] for t in LEVELS[:-1] for p in LEVELS[:-1])
    fn = sum(cm[t]["Level04"] for t in LEVELS[:-1])
    fp, tn = sum(cm["Level04"][p] for p in LEVELS[:-1]), cm["Level04"]["Level04"]
    ua, un = sum(cm[t]["INVALID"] for t in LEVELS[:-1]), cm["Level04"]["INVALID"]
    mean = lambda values: sum(values) / len(values) if values else None
    return {"planned_n": n, "confusion_4x5": cm, "support": support, "per_class": per_class,
            "invalid_n": ua + un, "accuracy": ratio(correct, n),
            "macro_f1": mean([per_class[t]["f1"]["value"] for t in supported]),
            "balanced_accuracy": mean([per_class[t]["recall"]["value"] for t in supported]),
            "macro_classes": supported,
            "binary": {"TP": tp, "FN": fn, "FP": fp, "TN": tn, "U_A": ua, "U_N": un,
                       "hazard_support": anomaly, "normal_support": normal,
                       "accuracy": ratio(tp + tn, n), "hazard_recall": ratio(tp, anomaly),
                       "specificity": ratio(tn, normal), "false_safe": ratio(fn, anomaly),
                       "false_alarm": ratio(fp, normal), "precision": ratio(tp, tp + fp),
                       "f1": ratio(2 * tp, 2 * tp + fp + fn + ua),
                       "balanced_accuracy": mean([x for x in
                           (tp / anomaly if anomaly else None, tn / normal if normal else None)
                           if x is not None])},
            "severe_false_safe": ratio(cm["Level01"]["Level04"], support["Level01"])}


def auc_report(rows):
    eligible, eligible_ids, excluded = [], [], Counter()
    for r in rows:
        score, reason = finite_score(r.get("hnlo_score"))
        if reason:
            excluded[reason] += 1
        else:
            eligible.append((r["true_level"] != "Level04", score))
            eligible_ids.append(r.get("sample_id"))
    positive = sum(y for y, _ in eligible)
    negative = len(eligible) - positive
    value = weighted_auc([y for y, _ in eligible], [s for _, s in eligible])
    return {"value": value, "status": "SAVED_SCORE_RECOMPUTED" if value is not None else "N/A",
            "reason": None if value is not None else "EMPTY_OR_ONE_CLASS",
            "planned_n": len(rows), "eligible_n": len(eligible), "excluded_by_reason": dict(excluded),
            "eligible_ids": eligible_ids,
            "positive_n": positive, "negative_n": negative, "pair_denominator": positive * negative,
            "tie_credit": 0.5, "raw_audit_performed": False}


def report(rows, sources):
    require(len(index(rows)) == len(rows), "unique metric IDs required")
    groups = {"ALL": rows}
    groups.update({"domain:" + d: [r for r in rows if r["domain"] == d]
                   for d in sorted({r["domain"] for r in rows})})
    groups.update({"level:" + t: [r for r in rows if r["true_level"] == t] for t in LEVELS})
    groups.update({"source:" + s: [r for r in rows if r["source_id"] == s] for s in sources})
    original = [r for r in rows if sources[r["source_id"]]["kind"] == "V4_ORIGINAL"]
    recovery = [r for r in rows if sources[r["source_id"]]["kind"] == "RECOVERY224"]
    hashes = Counter(r["image_sha256"] for r in rows)
    return {"product_id": PRODUCT, "evidence_level": "NEW_SAVED_REPORT_REANALYSIS",
            "label_status": "VERIFIED_COMPLETE_TRAIN_COMPOSITE",
            "planned_n": len(rows), "membership_sha256": digest([r["sample_id"] for r in rows]),
            "identity_sha256": digest([[r[k] for k in ("sample_id", "image_sha256", "true_level", "split")]
                                       for r in rows]),
            "source_counts": dict(Counter(sources[r["source_id"]]["kind"] for r in rows)),
            "duplicate_content": {"distinct_sha256": len(hashes),
                                  "duplicate_groups": sum(n > 1 for n in hashes.values()),
                                  "extra_records": sum(n - 1 for n in hashes.values())},
            "strata": {name: metrics(group) for name, group in groups.items()},
            "hnlo": {"composite": {"value": None, "status": "N/A",
                                    "reason": "CROSS_SERIES_SCALE_TOKEN_DECISION_ALIGNMENT_NOT_INDEPENDENTLY_VERIFIED",
                                    "planned_n": len(rows)},
                     "v4_original_success": auc_report(original), "recovery224": auc_report(recovery),
                     "per_source": {s: auc_report(groups["source:" + s]) for s in sources}},
            "limitations": ["Exposed TRAIN; no TEST/generalization/calibration claim",
                            "Multiple immutable execution series, not a completed single V4 run",
                            "Exact-content duplicates retained; source identity remains unverified",
                            "Saved report verification is not raw-logit audit or independent audit"]}
