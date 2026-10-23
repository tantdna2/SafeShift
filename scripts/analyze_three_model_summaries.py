"""CPU arithmetic checks of supplied aggregates; never a raw-evidence audit.

Run from the repository root. Uses only the standard library. Derived metrics
describe generated labels, not decisions at a fitted PA3 threshold.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import tarfile
import zipfile
from collections import Counter
from pathlib import Path


LEVELS = ("Level01", "Level02", "Level03", "Level04")
INPUTS = Path("notes/evidence/three_model_20261023")
QWEN3_S2_FIRST_ARCHIVE_SHA256 = "2dc356fcba9fe2ce5dfc4e3dc9a45286fe5382f574c02d38d7517580e38cd920"
QWEN3_S2_DUPLICATE_RESULT_SHA256 = "6e72dd81401381de36678163a26d890e492961ad3edf8e43b8e4b0f388089708"


def qwen3_s2_provenance(result_sha256, claimed_role="SECOND_DUPLICATE_S2_DIAGNOSTIC"):
    """Identify the known duplicate by bytes, never by filename or equal counts.

    No original S2 archive is supplied in this check. An unknown result digest
    cannot establish original provenance either; that requires archive binding.
    """
    if result_sha256 != QWEN3_S2_DUPLICATE_RESULT_SHA256:
        raise ValueError("S2_RESULT_ARCHIVE_PROVENANCE_REQUIRED")
    if claimed_role != "SECOND_DUPLICATE_S2_DIAGNOSTIC":
        raise ValueError("DUPLICATE_S2_RESULT_CANNOT_BE_ORIGINAL_V4")
    return {"result_sha256": result_sha256, "role": claimed_role,
            "usage": "CONSISTENCY_ONLY",
            "original_s2_independently_verified": False,
            "counts_toward_original_v4_member_validation": False}


def close(actual, expected, name, tolerance=1e-12):
    if (not isinstance(actual, (int, float)) or isinstance(actual, bool)
            or not math.isfinite(actual) or abs(actual - expected) > tolerance):
        raise ValueError(f"INCONSISTENT_AGGREGATE: {name}")


def statistics(matrix):
    if set(matrix) != set(LEVELS):
        raise ValueError("FOUR_TRUTH_ROWS_REQUIRED")
    counts = []
    for truth in LEVELS:
        row = matrix[truth]
        if set(row) - set(LEVELS):
            raise ValueError("UNKNOWN_PREDICTION_COLUMN")
        values = [row.get(pred, 0) for pred in LEVELS]
        if any(type(n) is not int or n < 0 for n in values):
            raise ValueError("NONNEGATIVE_INTEGER_COUNTS_REQUIRED")
        counts.append(values)
    supports = [sum(row) for row in counts]
    predicted = [sum(row[j] for row in counts) for j in range(4)]
    n = sum(supports)
    if not n:
        raise ValueError("NONEMPTY_COHORT_REQUIRED")
    per_class = {}
    for j, level in enumerate(LEVELS):
        tp = counts[j][j]
        per_class[level] = {
            "support": supports[j], "predicted": predicted[j], "correct": tp,
            "precision": tp / predicted[j] if predicted[j] else None,
            "recall": tp / supports[j] if supports[j] else None,
            # Fixed-four-class convention: absent/unpredicted class has F1=0.
            "f1": 2 * tp / (supports[j] + predicted[j])
                  if supports[j] + predicted[j] else 0.0,
        }
    positive, negative = sum(supports[:3]), supports[3]
    fn, tn = sum(counts[j][3] for j in range(3)), counts[3][3]
    tp, fp = positive - fn, negative - tn
    sensitivity = tp / positive if positive else None
    specificity = tn / negative if negative else None
    ba = ((sensitivity + specificity) / 2
          if positive and negative else None)
    return {
        "n": n, "anomaly": positive, "normal": negative,
        "correct_4": sum(counts[j][j] for j in range(4)),
        "four_class_accuracy": sum(counts[j][j] for j in range(4)) / n,
        "correct_binary": tp + tn, "binary_accuracy": (tp + tn) / n,
        "macro_F1_fixed": sum(x["f1"] for x in per_class.values()) / 4,
        "balanced_acc_support": sum(x["recall"] for x in per_class.values()
                                    if x["recall"] is not None)
                                / sum(bool(s) for s in supports),
        "level01_correct": counts[0][0], "level01_n": supports[0],
        "level01_recall": per_class["Level01"]["recall"],
        "level01_to_normal": counts[0][3], "fn_anomaly": fn,
        "fp_normal": fp, "fpr_normal": fp / negative if negative else None,
        "binary": {
            "TP": tp, "FN": fn, "FP": fp, "TN": tn,
            "recall_anomaly": sensitivity, "recall_normal": specificity,
            "precision_anomaly": tp / (tp + fp) if tp + fp else None,
            "precision_normal": tn / (tn + fn) if tn + fn else None,
            "balanced_accuracy": ba,
            "f1_anomaly": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0,
            "f1_normal": 2 * tn / (2 * tn + fp + fn) if 2 * tn + fp + fn else 0,
        },
        # AUROC of a binary hard score, with half credit for ties, equals BA.
        "auroc_generated": ba,
        "prediction_distribution": dict(zip(LEVELS, predicted)),
        "per_class": per_class,
    }


def check_report(report):
    calculated = statistics(report["confusion"])
    for key in ("n", "anomaly", "normal", "correct_4", "correct_binary",
                "four_class_accuracy", "binary_accuracy", "macro_F1_fixed",
                "balanced_acc_support", "level01_correct", "level01_n",
                "level01_recall", "level01_to_normal", "fn_anomaly",
                "fp_normal", "fpr_normal", "auroc_generated"):
        close(report[key], calculated[key], key)
    for level in LEVELS:
        close(report["prediction_distribution"].get(level, 0),
              calculated["prediction_distribution"][level], level)
    if not math.isfinite(report["auroc_pa3"]) or not 0 <= report["auroc_pa3"] <= 1:
        raise ValueError("INVALID_REPORTED_AUROC")
    return calculated


def sum_matrices(matrices):
    return {t: {p: sum(m[t].get(p, 0) for m in matrices) for p in LEVELS}
            for t in LEVELS}


def read_official_confusion(payload):
    groups = {}
    for row in csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))):
        if row["method"] != "GENERATED_4CLASS_FAILURE_AWARE":
            continue
        count = int(row["count"])
        if row["generated_label"] == "INVALID" and count == 0:
            continue
        group = groups.setdefault(row["domain"], {t: {} for t in LEVELS})
        t, p = row["true_label"], row["generated_label"]
        if p in group[t]:
            raise ValueError("DUPLICATE_CONFUSION_CELL")
        group[t][p] = count
    for matrix in groups.values():
        statistics(matrix)
    return groups


def analyze(input_dir=INPUTS):
    summary = json.loads((input_dir / "SafeShift_three_model_comparison_20261023.json")
                         .read_text(encoding="utf-8-sig"))
    official_path = Path("notes/pa3_r2_cpu_completion_20261015.summary.json")
    official = json.loads(official_path.read_text(encoding="utf8"))
    confusion_bytes = (input_dir / "qwen25_official_confusion.csv").read_bytes()
    if hashlib.sha256(confusion_bytes).hexdigest() != official["report_artifacts"]["confusion.csv"]["sha256"]:
        raise ValueError("OFFICIAL_CONFUSION_HASH_MISMATCH")
    q25 = read_official_confusion(confusion_bytes)
    calculated = {name: check_report(report) for name, report in summary["metrics"].items()}
    calculated["Qwen2.5"] = statistics(q25["ALL"])
    overall = official["overall"]
    close(calculated["Qwen2.5"]["four_class_accuracy"], overall["accuracy_generated_4class"]["value"], "Q25 four")
    close(calculated["Qwen2.5"]["binary_accuracy"], overall["accuracy_generated_binary"], "Q25 binary")
    for key, expected in {"auroc": overall["auroc_pa3"]["value"],
                          "four": overall["accuracy_generated_4class"]["value"],
                          "binary": overall["accuracy_generated_binary"]}.items():
        close(summary["baseline_qwen2_5"][key], expected, "baseline " + key)
    parts = summary["metrics"]
    if sum_matrices([parts["Qwen3 V4 success"]["confusion"], parts["Qwen3 Recovery"]["confusion"]]) != parts["Qwen3 combined"]["confusion"]:
        raise ValueError("RECOVERY_ADDITION_MISMATCH")
    by_domain = {}
    for domain, reports in summary["by_domain"].items():
        by_domain[domain] = {name: check_report(report) for name, report in reports.items()}
        by_domain[domain]["qwen25"] = statistics(q25[domain])
        expected_support = official["by_domain"][domain]["level_counts"]
        for stats in by_domain[domain].values():
            if {k: v["support"] for k, v in stats["per_class"].items()} != expected_support:
                raise ValueError("DOMAIN_SUPPORT_MISMATCH")
    if set(summary["by_domain"]) != set(official["by_domain"]):
        raise ValueError("DOMAIN_SET_MISMATCH")
    for model, total in (("qwen3", "Qwen3 combined"), ("internvl3", "InternVL3")):
        if sum_matrices([reports[model]["confusion"] for reports in summary["by_domain"].values()]) != parts[total]["confusion"]:
            raise ValueError("DOMAIN_SUM_MISMATCH")
    if sum_matrices([q25[d] for d in summary["by_domain"]]) != q25["ALL"]:
        raise ValueError("Q25_DOMAIN_SUM_MISMATCH")
    csv_rows = list(csv.DictReader((input_dir / "SafeShift_three_model_metrics_20261023.csv").open(encoding="utf8", newline="")))
    if {r["domain"] for r in csv_rows} != set(summary["by_domain"]) | {"ALL"} or len(csv_rows) != 6:
        raise ValueError("CSV_DOMAIN_SET_MISMATCH")
    for row in csv_rows:
        domain = row["domain"]
        expected = overall if domain == "ALL" else official["by_domain"][domain]
        close(int(row["N"]), expected["scored"], "CSV N")
        close(int(row["Anomaly"]), expected["auroc_pa3"]["positive_n"], "CSV Anomaly")
        reports = {"Qwen2.5": {"auroc_pa3": expected["auroc_pa3"]["value"],
                               "four_class_accuracy": expected["accuracy_generated_4class"]["value"],
                               "binary_accuracy": expected["accuracy_generated_binary"]}}
        reports.update({"Qwen3": parts["Qwen3 combined"] if domain == "ALL" else summary["by_domain"][domain]["qwen3"],
                        "InternVL3": parts["InternVL3"] if domain == "ALL" else summary["by_domain"][domain]["internvl3"]})
        for model, report in reports.items():
            for column, key in (("AUROC", "auroc_pa3"), ("4class_accuracy", "four_class_accuracy"), ("binary_accuracy", "binary_accuracy")):
                close(float(row[f"{model}_{column}"]), report[key], "CSV " + model + " " + key, tolerance=5e-8)
    files = [input_dir / name for name in (
        "SafeShift_three_model_report_20261023.md",
        "SafeShift_three_model_comparison_20261023.json",
        "SafeShift_three_model_metrics_20261023.csv",
        "qwen25_official_confusion.csv")] + [official_path]
    return {"scope": "AGGREGATE_ARITHMETIC_ONLY_NOT_RAW_AUDIT",
            "summary_checks": "PASS", "models": calculated, "by_domain": by_domain,
            "constant_normal": statistics({t: {"Level04": overall["level_counts"][t]} for t in LEVELS}),
            "inputs_sha256": {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in files if p.is_file()}}


def export_rows(payload):
    """Validate saved report rows; do not replay model logits or raw journals."""
    rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
    ids = [r["sample_id"] for r in rows]
    if not rows or len(ids) != len(set(ids)):
        raise ValueError("NONEMPTY_UNIQUE_EXPORT_IDS_REQUIRED")
    for r in rows:
        if (r["status"] != "SUCCESS" or r["true_level"] not in LEVELS
                or r["generated_label"] not in LEVELS
                or not math.isfinite(float(r["pa3_score"]))):
            raise ValueError("VALID_FINITE_SUCCESS_EXPORT_REQUIRED")
    return rows


def export_matrix(rows):
    matrix = {t: {p: 0 for p in LEVELS} for t in LEVELS}
    for row in rows:
        matrix[row["true_level"]][row["generated_label"]] += 1
    return matrix


def verify_exports(directory, input_dir=INPUTS):
    """Optional check of locally supplied reports, not archive custody/authenticity.

    Expected layout is documented in the accompanying scientific report. The
    Known duplicate S2 bytes are checked only for consistency with supplied
    aggregates. They cannot confirm original S2 members, coverage or predictions.
    """
    from safeshift.ls1.evaluate import auc  # Existing, unchanged rank implementation.

    official = json.loads(Path("notes/pa3_r2_cpu_completion_20261015.summary.json").read_text(encoding="utf8"))
    summary = json.loads((input_dir / "SafeShift_three_model_comparison_20261023.json").read_text(encoding="utf8"))
    s2_payload = (directory / "qwen3_shard2.json").read_bytes()
    s2_provenance = qwen3_s2_provenance(hashlib.sha256(s2_payload).hexdigest())
    payload = (directory / "qwen25_samples.csv").read_bytes()
    if hashlib.sha256(payload).hexdigest() != official["report_artifacts"]["samples.csv"]["sha256"]:
        raise ValueError("OFFICIAL_SAMPLES_HASH_MISMATCH")
    q25 = export_rows(payload)
    truth = {r["sample_id"]: (r["true_level"], r["domain"]) for r in q25}
    close(auc([r["true_level"] != "Level04" for r in q25],
              [float(r["pa3_score"]) for r in q25]), official["overall"]["auroc_pa3"]["value"], "Q25 saved-score AUROC")
    intern, members = [], {}
    with zipfile.ZipFile(directory / "InterVL3_Output.zip") as outer:
        names = [n for n in outer.namelist() if n.endswith(".tar.gz")]
        if len(names) != 4 or len(set(names)) != 4:
            raise ValueError("FOUR_UNIQUE_INTERNVL_ARCHIVES_REQUIRED")
        for name in names:
            found = []
            with tarfile.open(fileobj=io.BytesIO(outer.read(name)), mode="r|gz") as archive:
                for member in archive:
                    if member.name == "evidence/report/samples.csv":
                        found.append(archive.extractfile(member).read())
            if len(found) != 1:
                raise ValueError("ONE_EXACT_SAMPLES_MEMBER_REQUIRED")
            intern.extend(export_rows(found[0]))
            members[name] = hashlib.sha256(found[0]).hexdigest()
    # Revalidate uniqueness across archives and exact ID/label/domain equality.
    if len({r["sample_id"] for r in intern}) != len(intern):
        raise ValueError("OVERLAPPING_INTERNVL_SHARDS")
    if {r["sample_id"]: (r["true_level"], r["domain"]) for r in intern} != truth:
        raise ValueError("EXACT_EXPORT_UNIVERSE_REQUIRED")
    if export_matrix(intern) != summary["metrics"]["InternVL3"]["confusion"]:
        raise ValueError("INTERNVL_EXPORT_CONFUSION_MISMATCH")
    for domain in [None] + list(summary["by_domain"]):
        selected = [r for r in intern if domain is None or r["domain"] == domain]
        expected = summary["metrics"]["InternVL3"] if domain is None else summary["by_domain"][domain]["internvl3"]
        close(auc([r["true_level"] != "Level04" for r in selected],
                  [float(r["pa3_score"]) for r in selected]), expected["auroc_pa3"], "InternVL saved-score AUROC")
        if export_matrix(selected) != expected["confusion"]:
            raise ValueError("INTERNVL_DOMAIN_CONFUSION_MISMATCH")
    # This union deliberately includes the DUPLICATE S2 for a diagnostic check.
    # Matching the Lead's original-V4 aggregate is NOT proof of first-run S2.
    q3ids, q3matrices, sidecar_checks, id_counts = [], [], {}, {}
    for name in [f"qwen3_shard{i}.json" for i in range(4)] + ["recovery.json"]:
        payload = s2_payload if name == "qwen3_shard2.json" else (directory / name).read_bytes()
        result = json.loads(payload)
        metrics = result["metrics"]["overall"]
        ids = metrics["auroc_pa3"]["eligible_ids"]
        if len(ids) != len(set(ids)):
            raise ValueError("DUPLICATE_QWEN3_EXPORT_ID")
        q3ids.extend(ids)
        matrix = metrics["generated_on_score_valid_ids"]["confusion_matrix"]
        if any(row.get("INVALID", 0) for row in matrix.values()):
            raise ValueError("INVALID_IN_SCORE_VALID_CONFUSION")
        q3matrices.append({t: {p: matrix[t].get(p, 0) for p in LEVELS} for t in LEVELS})
        id_counts[name] = len(ids)
        role = (s2_provenance["role"] if name == "qwen3_shard2.json"
                else "RECOVERY_SIDECAR" if name == "recovery.json" else "NON_S2_V4_SIDECAR_AS_PROVIDED")
        sidecar_checks[name] = {"role": role, "status_counts": result["coverage"]["status_counts"]}
        expected_support = {t: sum(truth[sid][0] == t for sid in ids) for t in LEVELS}
        if {t: sum(q3matrices[-1][t].values()) for t in LEVELS} != expected_support:
            raise ValueError("QWEN3_SIDECAR_CONSISTENCY_SUPPORT_MISMATCH")
    if len(q3ids) != len(set(q3ids)) or set(q3ids) != set(truth):
        raise ValueError("DISJOINT_DIAGNOSTIC_QWEN3_UNION_REQUIRED")
    for matrices, name in [(q3matrices[:4], "Qwen3 V4 success"),
                           (q3matrices[4:], "Qwen3 Recovery"),
                           (q3matrices, "Qwen3 combined")]:
        if sum_matrices(matrices) != summary["metrics"][name]["confusion"]:
            raise ValueError("QWEN3_DIAGNOSTIC_CONSISTENCY_CONFUSION_MISMATCH")
    return {"scope": "SAVED_REPORT_ROWS_AND_RESULT_SIDECARS_NOT_RAW_AUDIT",
            "same_id_label_domain_q25_internvl": len(truth),
            "qwen3_original_v4": {
                "scope": "SUPPLIED_PREVIOUSLY_REPORTED_NOT_NEWLY_MEMBER_CONFIRMED",
                "success_n_reported": summary["metrics"]["Qwen3 V4 success"]["n"],
                "combined_n_reported": summary["metrics"]["Qwen3 combined"]["n"],
                "original_s2_independently_verified": False,
                "complete_member_level_validation": False,
                "first_s2_archive_expected_sha256": QWEN3_S2_FIRST_ARCHIVE_SHA256,
                "first_s2_archive_supplied_in_this_check": False},
            "qwen3_s2_diagnostic": s2_provenance,
            "qwen3_available_sidecars_consistency": {
                "scope": "NON_S2_SIDECARS_PLUS_DUPLICATE_S2_PLUS_RECOVERY_CONSISTENCY_ONLY",
                "id_union_n": len(q3ids),
                "non_s2_v4_sidecar_id_n": sum(id_counts[f"qwen3_shard{i}.json"] for i in (0, 1, 3)),
                "duplicate_s2_id_n": id_counts["qwen3_shard2.json"],
                "recovery_id_n": id_counts["recovery.json"],
                "same_id_set_and_truth_support_vs_official_reports": True,
                "confusions_match_supplied_aggregates": True,
                "proves_original_s2_members": False,
                "sidecars": sidecar_checks},
            "internvl_saved_score_auroc_recomputed": summary["metrics"]["InternVL3"]["auroc_pa3"],
            "qwen25_saved_score_auroc_recomputed": official["overall"]["auroc_pa3"]["value"],
            "qwen3_pooled_auroc_recomputed": False,
            "internvl_report_member_sha256": members,
            "inputs_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(directory.iterdir()) if p.is_file()}}


def metadata_census(payload):
    """Describe existing TRAIN metadata without promoting regex keys to sources."""
    rows = [r for r in json.loads(payload)["samples"] if r["split"] == "train"]
    return {
        "source_sha256": hashlib.sha256(payload).hexdigest(), "n": len(rows),
        "scope": "EXISTING_AUDIT_TRAIN_METADATA_NO_NEW_IMAGE_OR_ANNOTATION_READ",
        "point_id_groups": len({r["point_id"] for r in rows}),
        "anomaly_regex_family_keys": len({r["source_family"] for r in rows
                                           if r["safety_level"] != "Level04" and r["source_family"]}),
        "normal_regex_family_keys": len({r["source_family"] for r in rows
                                          if r["safety_level"] == "Level04" and r["source_family"]}),
        "source_groups_verified_independent": False,
        "platform_by_domain": {d: dict(Counter(r["robot_platform"] for r in rows if r["folder_domain"] == d))
                               for d in sorted({r["folder_domain"] for r in rows})},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="New JSON file under data/processed/")
    parser.add_argument("--local-evidence", type=Path,
                        help="Optional staged saved reports; no raw-journal audit")
    parser.add_argument("--metadata-audit", type=Path,
                        help="Optional existing duplicate-audit JSON; TRAIN metadata census only")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(Path("data/processed").resolve()):
        parser.error("Output must stay under data/processed/")
    result = analyze()
    if args.local_evidence:
        result["available_export_checks"] = verify_exports(args.local_evidence)
    if args.metadata_audit:
        result["existing_metadata_census"] = metadata_census(args.metadata_audit.read_bytes())
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print("PASS: aggregate arithmetic; raw audit and dependence-aware CI not performed")


if __name__ == "__main__":
    main()
