"""Complete planned-ID accounting and descriptive, unweighted pilot metrics."""
from collections import Counter
import csv
import io
import math
from statistics import median

from .artifacts import write, write_bytes
from .contract import DOMAINS, HNLO_STATUSES, LEVELS, MODELS, STATUSES, THRESHOLDS


def ratio(n, d):
    return n / d if d else None


def auc(pairs):
    """Rank-sum AUROC with 0.5 ties, no assumed independent observations."""
    ordered = sorted(pairs, key=lambda r: r[1])
    positives = sum(y for y, _ in pairs)
    negatives = len(pairs) - positives
    if not positives or not negatives:
        return None
    ranks, index = 0.0, 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        ranks += sum(y for y, _ in ordered[index:end]) * (index + 1 + end) / 2
        index = end
    return (ranks - positives * (positives + 1) / 2) / (positives * negatives)


def measurements(rows, results):
    counts = Counter(results[r["sample_id"]]["status"] for r in rows)
    if set(counts) - set(STATUSES):
        raise ValueError("UNKNOWN_CLASSIFICATION_STATUS")
    confusion = {l: {p: 0 for p in (*LEVELS, "INVALID")} for l in LEVELS}
    distribution = Counter()
    hnlo_counts = Counter()
    h_capture, h_alignment, h_replay = Counter(), Counter(), Counter()
    errors = Counter()
    times, peaks, scores, overhead = [], [], [], []
    attempted = retries = tp = tn = fp = fn = 0
    missing = Counter()
    for row in rows:
        value = results[row["sample_id"]]
        status, pred = value["status"], value.get("label")
        if (status == "SUCCESS") != (pred in LEVELS):
            raise ValueError("STATUS_LABEL_INCONSISTENCY")
        confusion[row["level"]][pred if status == "SUCCESS" else "INVALID"] += 1
        attempted += int(value.get("attempts", 0) > 0)
        retries += max(0, value.get("attempts", 0) - 1)
        distribution[pred if status == "SUCCESS" else status] += 1
        h = value.get("hnlo", {})
        hstatus = h.get("status", "HNLO_UNVERIFIED")
        if hstatus not in HNLO_STATUSES:
            raise ValueError("UNKNOWN_HNLO_STATUS")
        hnlo_counts[hstatus] += 1
        h_capture[h.get("capture_status", "NOT_RUN")] += 1
        h_alignment[h.get("alignment_status", "UNVERIFIED")] += 1
        h_replay[h.get("replay_status", "NOT_RUN")] += 1
        if hstatus == "HNLO_VALIDATED":
            score = h["hnlo"]
            if status != "SUCCESS" or not math.isfinite(score) or h.get("replay_status") != "PASS":
                raise ValueError("HNLO_REPLAY_REQUIRED")
            scores.append((row["level"] != "Level04", score))
        if status != "SUCCESS":
            missing["normal" if row["level"] == "Level04" else "anomaly"] += 1
        elif row["level"] == "Level04":
            tn += pred == "Level04"
            fp += pred != "Level04"
        else:
            fn += pred == "Level04"
            tp += pred != "Level04"
        if value.get("error_category"):
            errors[value["error_category"]] += 1
        if value.get("seconds") is not None:
            times.append(value["seconds"])
        if value.get("memory"):
            peaks.append(value["memory"]["gpu0_peak_allocated"])
        if value.get("hnlo_overhead"):
            overhead.append(value["hnlo_overhead"]["observer_seconds"])
    support = {l: sum(confusion[l].values()) for l in LEVELS}
    per_class = {}
    for l in LEVELS:
        diagonal = confusion[l][l]
        predicted_n = sum(confusion[t][l] for t in LEVELS)
        per_class[l] = {"support": support[l], "recall": ratio(diagonal, support[l]),
                        "precision": ratio(diagonal, predicted_n),
                        "f1": ratio(2 * diagonal, support[l] + predicted_n)}
    f1s = [v["f1"] for v in per_class.values() if v["support"]]
    recalls = [v["recall"] for v in per_class.values() if v["support"]]
    correct = sum(confusion[l][l] for l in LEVELS)
    return {"planned": len(rows), "attempted": attempted, "SUCCESS": counts["SUCCESS"],
            "INVALID": counts["INVALID"], "ERROR": counts["TECHNICAL_ERROR"],
            "NOT_ATTEMPTED": counts["NOT_ATTEMPTED"], "retry_calls": retries,
            "total_native_attempts": sum(results[r["sample_id"]].get("native_calls", 0) for r in rows),
            "coverage": ratio(attempted, len(rows)), "valid_rate_planned": ratio(counts["SUCCESS"], len(rows)),
            "valid_rate_attempted": ratio(counts["SUCCESS"], attempted),
            "confusion_4x5": confusion, "support": support, "per_class": per_class,
            "unavailable_column": "INVALID includes invalid output, technical error and unattempted; counts above separate them",
            "accuracy_planned": ratio(correct, len(rows)), "accuracy_valid_only": ratio(correct, counts["SUCCESS"]),
            "macro_f1_supported_classes": sum(f1s) / len(f1s) if f1s else None,
            "balanced_accuracy_supported_classes": sum(recalls) / len(recalls) if recalls else None,
            "macro_classes_included": [l for l in LEVELS if support[l]],
            "binary": {"TP": tp, "TN": tn, "FP": fp, "FN": fn,
                       "FNR_valid": ratio(fn, tp + fn), "FPR_valid": ratio(fp, tn + fp),
                       "FNR_denominator": tp + fn, "FPR_denominator": tn + fp,
                       "unavailable_anomaly": missing["anomaly"], "unavailable_normal": missing["normal"],
                       "FNR_planned_bounds": [ratio(fn, tp + fn + missing["anomaly"]),
                                              ratio(fn + missing["anomaly"], tp + fn + missing["anomaly"])],
                       "FPR_planned_bounds": [ratio(fp, tn + fp + missing["normal"]),
                                              ratio(fp + missing["normal"], tn + fp + missing["normal"])]},
            "predicted_distribution": dict(distribution), "error_categories": dict(errors),
            "timing": {"per_image_seconds": times, "sum_seconds": sum(times),
                       "median_seconds": median(times) if times else None,
                       "p95_seconds": sorted(times)[max(0, math.ceil(.95 * len(times)) - 1)] if times else None},
            "peak_allocated_vram_gpu0": max(peaks) if peaks else None,
            "peak_reserved_vram_gpu0": max((results[r["sample_id"]]["memory"]["gpu0_peak_reserved"]
                                            for r in rows if results[r["sample_id"]].get("memory")), default=None),
            "gpu1": {"inference_placement": "UNUSED", "peak_vram": None, "reason": "GPU1 not visible to worker"},
            "nonfinite_output_n": sum(bool(results[r["sample_id"]].get("raw_nonfinite")) for r in rows),
            "hnlo": {"status_counts": dict(hnlo_counts), "validated_n": len(scores),
                     "capture_status_counts": dict(h_capture), "alignment_status_counts": dict(h_alignment),
                     "replay_status_counts": dict(h_replay),
                     "coverage_planned": ratio(len(scores), len(rows)), "descriptive_auroc": auc(scores),
                     "auroc_positive_n": sum(y for y, _ in scores), "auroc_negative_n": sum(not y for y, _ in scores),
                     "observer_seconds": sum(overhead),
                     "capture_temporary_bytes_upper_estimate": max(((results[r["sample_id"]].get("hnlo_overhead") or {}).get("temporary_allocated_bytes_upper_estimate", 0) for r in rows), default=0),
                     "paired_gpu_overhead": None,
                     "paired_gpu_overhead_reason": "No additional hook-off inference granted"}}


def verdict(metrics, *, preflight_blocked=False, failure=None):
    if metrics["attempted"] == 0:
        if failure and failure["category"] != "ACCESS":
            return {"classification_status": "TECHNICAL_FAIL", "recommendation": "NO_GO_FULL_TRAIN",
                    "reason": failure, "quality_flags": [], "hnlo_role": "UNVERIFIED"}
        return {"classification_status": "INCONCLUSIVE/BLOCKED", "recommendation": "INCONCLUSIVE/BLOCKED",
                "reason": "NO_REAL_CLASSIFICATION_EVIDENCE", "quality_flags": [], "hnlo_role": "UNVERIFIED"}
    technical = (not preflight_blocked and metrics["attempted"] == metrics["planned"]
                 and metrics["ERROR"] == 0 and metrics["valid_rate_planned"] >= THRESHOLDS["valid_rate_min"])
    technical = technical and metrics["nonfinite_output_n"] == 0
    b = metrics["binary"]
    flags = []
    if b["FPR_valid"] is not None and b["FPR_valid"] >= THRESHOLDS["normal_fpr_red_flag"]:
        flags.append("QUALITY_RED_FLAG:ALMOST_ALL_NORMAL_PREDICTED_ANOMALY_Q25_IVL3_PATHOLOGY")
    if b["FNR_valid"] is not None and b["FNR_valid"] >= THRESHOLDS["anomaly_fnr_red_flag"]:
        flags.append("QUALITY_RED_FLAG:ALMOST_ALL_ANOMALY_PREDICTED_NORMAL")
    evaluable = b["FPR_valid"] is not None and b["FNR_valid"] is not None
    go = (technical and evaluable and not flags and b["FNR_valid"] <= THRESHOLDS["fnr_go_max"]
          and b["FPR_valid"] <= THRESHOLDS["fpr_go_max"]
          and metrics["macro_f1_supported_classes"] >= THRESHOLDS["macro_f1_go_min"])
    role = ("HNLO_RESEARCH_CANDIDATE" if metrics["hnlo"]["validated_n"] == metrics["SUCCESS"]
            and metrics["SUCCESS"] > 0 else "CLASSIFICATION_ONLY_OR_PARTIAL_HNLO_REQUIRES_REVIEW")
    return {"classification_status": "TECHNICAL_PASS" if technical else "TECHNICAL_FAIL",
            "recommendation": "GO_FULL_TRAIN_RECOMMENDED" if go else
                              "NO_GO_FULL_TRAIN" if not technical or flags or evaluable else "INCONCLUSIVE/BLOCKED",
            "quality_flags": flags, "hnlo_role": role, "thresholds": THRESHOLDS,
            "scope": "Operational screening recommendation only; no generalization or statistical improvement claim"}


def model_report(plan, results, blocked=False, failure=None):
    rows = plan["main"] + plan["supplement"]
    if set(results) != {r["sample_id"] for r in rows}:
        raise ValueError("EXACT_PLANNED_ID_REPORT_REQUIRED")
    primary = measurements(plan["main"], results)
    supplement = measurements(plan["supplement"], results)
    supplement["selected_qwen_false_safe_n"] = len(plan["supplement"])
    supplement["new_anomaly_detected_n"] = sum(results[r["sample_id"]].get("label") in LEVELS[:3] for r in plan["supplement"])
    supplement["also_false_safe_ids"] = [r["sample_id"] for r in plan["supplement"] if results[r["sample_id"]].get("label") == "Level04"]
    return {"schema": "safeshift-pilot-report-v1", "mode": plan["mode"], "primary": primary,
            "per_domain": {d: measurements([r for r in plan["main"] if r["domain"] == d], results) for d in DOMAINS},
            "supplement": supplement, "supplement_availability": plan["supplement_availability"],
            "pipeline_failure": failure,
            "conclusion": verdict(primary, preflight_blocked=blocked, failure=failure),
            "limitations": ["Stratified nonproportional exposed TRAIN; unweighted accuracy is not a TRAIN population estimate.",
                            "Small class/domain supports; correlated frames/duplicates; no independent-sample CI asserted.",
                            "Primary 4x5 includes every planned row; unavailable categories have separate counts.",
                            "Error-selected Qwen supplement is separate and cannot estimate population gains.",
                            "HNLO AUROC uses only validated rows; coverage and both class supports are explicit.",
                            "No raw Qwen replay, no historical-cohort confirmatory comparison, no TEST."]}


def combined(plan, by_model):
    rows, output = plan["main"] + plan["supplement"], []
    expected = {r["sample_id"] for r in rows}
    qwen = {r["sample_id"]: r for r in plan["qwen_verified"]}
    for key, results in by_model.items():
        if key not in MODELS or set(results) != expected:
            raise ValueError("THREE_MODEL_EXACT_SHARED_MANIFEST_REQUIRED")
    for i, r in enumerate(rows):
        row = {"sample_id": r["sample_id"], "domain": r["domain"], "ground_truth": r["level"],
               "cohort": "primary" if i < len(plan["main"]) else "qwen_false_safe_supplement",
               "qwen3_label_if_verified": qwen.get(r["sample_id"], {}).get("predicted_label"), "status": {}}
        for key in MODELS:
            result = by_model.get(key, {}).get(r["sample_id"], {"status": "NOT_ATTEMPTED"})
            row[key] = result.get("label") or result["status"]
            row["status"][key] = result["status"]
        output.append(row)
    return output


def save_reports(root, plan, by_model, blocked=False, failures=None, runtime=None):
    from pathlib import Path
    root = Path(root)
    table = combined(plan, by_model)
    write(root / "comparison.json", table)
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=list(table[0]))
    writer.writeheader()
    for row in table:
        writer.writerow({**row, "status": str(row["status"])})
    write_bytes(root / "comparison.csv", text.getvalue().encode("utf-8"))
    reports = {}
    for key in MODELS:
        results = by_model.get(key, {r["sample_id"]: {"status": "NOT_ATTEMPTED", "attempts": 0} for r in plan["main"] + plan["supplement"]})
        reports[key] = model_report(plan, results, blocked, (failures or {}).get(key))
        reports[key]["runtime"] = (runtime or {}).get(key, {"status": "NOT_RUN_OR_NO_RUNTIME_EVIDENCE"})
        write(root / f"{key}.json", reports[key])
    return reports
