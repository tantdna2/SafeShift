"""Offline LS1 reports: GT joins after scoring; no parameter fitting or RQ3."""

import math

from safeshift.protocol.d9r24_metrics import classification_metrics
from safeshift.protocol.metrics import ClassificationInput
from safeshift.protocol.schema import Classification, ParseResult
from .core import LEVELS


def auc(labels, scores):
    """Mann-Whitney rank AUROC, average ranks for ties, O(N log N)."""
    if len(labels) != len(scores) or any(type(x) is not bool for x in labels):
        raise ValueError("BINARY_AUROC_SCHEMA")
    if any(not math.isfinite(x) for x in scores):
        raise ValueError("FINITE_AUROC_SCORES_REQUIRED")
    positive = sum(labels)
    negative = len(labels) - positive
    if not positive or not negative:
        return None
    ordered = sorted(zip(scores, labels))
    rank_sum, start = 0.0, 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][0] == ordered[start][0]:
            end += 1
        rank_sum += sum(label for _, label in ordered[start:end]) * (start + 1 + end) / 2
        start = end
    return (rank_sum - positive * (positive + 1) / 2) / (positive * negative)


def anomaly_log_odds(log_probabilities):
    # Strictly monotone in 1-p(Level04), without subtraction/exp saturation.
    maximum = max(log_probabilities[:3])
    return maximum + math.log(math.fsum(math.exp(x - maximum) for x in log_probabilities[:3])) - log_probabilities[3]


def report(results, ground_truth):
    """Keep INVALID in classification denominators; AUROC is score-conditional."""
    ids = [row["sample_id"] for row in results]
    if len(ids) != len(set(ids)) or set(ids) != set(ground_truth):
        raise ValueError("EXACT_UNIQUE_GT_JOIN_REQUIRED")
    if any(gt not in LEVELS for gt in ground_truth.values()):
        raise ValueError("CANONICAL_GT_REQUIRED")
    for row in results:
        if row["status"] not in ("SUCCESS", "INVALID"):
            raise ValueError("INCOMPLETE_RUN_CANNOT_BE_EVALUATED")
        if row["status"] == "INVALID":
            if row.get("modes") is not None:
                raise ValueError("INVALID_MUST_HAVE_NO_PREDICTION")
            continue
        for mode in ("uncalibrated", "calibrated"):
            values = row["modes"][mode]
            probs = values["probabilities"]
            logs = values["log_probabilities"]
            if (values["prediction"] not in LEVELS or len(probs) != 4
                    or len(logs) != 4 or any(not math.isfinite(x) for x in logs)
                    or any(type(x) not in (float, int) or not math.isfinite(x) or not 0 <= x <= 1 for x in probs)
                    or not math.isclose(sum(probs), 1, abs_tol=1e-12)):
                raise ValueError("INVALID_SCORE_DISTRIBUTION")
    output = {"protocol": "LS1", "version": "ls1-evaluation-v1", "rq3_included": False,
              "comparison_warning": "P2, P2.1 and LS1 are distinct; no automatic historical relabelling.",
              "modes": {}}
    eligible = [row for row in results if row["status"] == "SUCCESS"]
    for mode in ("uncalibrated", "calibrated"):
        samples = []
        for row in results:
            pred = row["modes"][mode]["prediction"] if row["status"] == "SUCCESS" else None
            samples.append(ClassificationInput(row["sample_id"], ground_truth[row["sample_id"]],
                "LS1", row["sample_id"], ParseResult("SUCCESS", Classification(pred)) if pred else ParseResult("INVALID"),
                frozenset()))
        metrics = classification_metrics(samples)
        truths = [ground_truth[row["sample_id"]] for row in eligible]
        logs = [row["modes"][mode]["log_probabilities"] for row in eligible]
        per_class = {label: auc([t == label for t in truths], [p[i] for p in logs])
                     for i, label in enumerate(LEVELS)}
        metrics.update(accuracy=metrics["raw_accuracy_descriptive"],
            level01_recall_full_cohort=metrics["per_class"]["Level01"]["recall"],
            level04_recall_full_cohort=metrics["per_class"]["Level04"]["recall"],
            auroc={"scope": "SCORE_CONDITIONAL_VALID_LS1_ONLY", "eligible_n": len(eligible),
                   "excluded_invalid_n": len(results) - len(eligible), "ovr": per_class,
                   "macro_ovr": sum(per_class.values()) / 4 if all(v is not None for v in per_class.values()) else None,
                   "anomaly_vs_normal": auc([t != "Level04" for t in truths], [anomaly_log_odds(p) for p in logs]),
                   "ovr_score": "log conditional class probability, avoiding exp underflow",
                   "anomaly_score": "log odds of 1-p(Level04), avoiding saturation; no tuned threshold"})
        output["modes"][mode] = metrics
    transitions = {level: {"n": 0, "true_anomaly_n": 0, "true_level01_n": 0, "sample_ids": []}
                   for level in LEVELS[:3]}
    for row in eligible:
        before, after = (row["modes"][name]["prediction"] for name in ("uncalibrated", "calibrated"))
        if before in transitions and after == "Level04":
            item = transitions[before]
            gt = ground_truth[row["sample_id"]]
            item["n"] += 1
            item["true_anomaly_n"] += gt != "Level04"
            item["true_level01_n"] += gt == "Level01"
            item["sample_ids"].append(row["sample_id"])
    output["transitions_to_level04"] = transitions
    output["generated_label_to_level04"] = {level: [r["sample_id"] for r in eligible
        if r["score"]["generated_label"] == level and r["modes"]["calibrated"]["prediction"] == "Level04"]
        for level in LEVELS[:3]}
    return output
