"""Exact, retrospective label comparison for the three selected TRAIN products."""

from collections import Counter, defaultdict
from itertools import combinations
import re

from safeshift.data.schema import SAFETY_LEVELS as LEVELS
from safeshift.data.validation import validate_identifier
from safeshift.evaluation.qwen_composite import digest, index, metrics, ratio, require


SCHEMA = "safeshift-full-train-benchmark-v1"
PRODUCTS = ("qwen3", "internvl35", "minicpm")
IDENTITY = ("split", "image_sha256", "true_level", "domain")
HASH = re.compile(r"[0-9a-f]{64}")
SOURCE_FIELDS = ("run_id", "attempt_id", "model_id", "revision")
SOURCE_HASHES = ("config_sha256", "artifact_sha256")


def is_sha256(value):
    return isinstance(value, str) and HASH.fullmatch(value) is not None


def validate_cohort(cohort, planned_n):
    rows = cohort["samples"]
    metadata = index(rows)
    require(len(metadata) == planned_n and planned_n > 0, "exact planned TRAIN count required")
    for row in rows:
        validate_identifier(row["sample_id"], "sample_id")
        validate_identifier(row["domain"], "domain")
        require(row["split"] == "TRAIN" and row["true_level"] in LEVELS and
                is_sha256(row["image_sha256"]), "invalid TRAIN metadata")
    return rows, metadata


def validate_product(key, product, contract, metadata, mini_conversion_n):
    require(product["product_id"] == contract["id"] and
            is_sha256(product["source_seal_sha256"]) and
            product["source_seal_sha256"] == contract["source_seal_sha256"],
            f"{key}: product or custody seal mismatch")
    by_id = index(product["samples"])
    sources = product["sources"]
    require(set(by_id) == set(metadata), f"{key}: missing or unexpected TRAIN IDs")
    require(isinstance(sources, dict) and sources and
            {row["source_id"] for row in by_id.values()} == set(sources),
            f"{key}: exact source membership required")
    for source_id, source in sources.items():
        validate_identifier(source_id, "source_id")
        require(isinstance(source, dict) and
                all(isinstance(source.get(f), str) and source[f].strip() for f in SOURCE_FIELDS) and
                all(is_sha256(source.get(f)) for f in SOURCE_HASHES),
                f"{key}: incomplete source, revision or configuration provenance")
    conversions = 0
    strict_rows = []
    for sid, meta in metadata.items():
        row = by_id[sid]
        require(all(row[field] == meta[field] for field in IDENTITY),
                f"{key}: TRAIN identity, image SHA, GT or folder domain mismatch")
        require(row["status"] == "SUCCESS" and row["generated_label"] in LEVELS,
                f"{key}: selected product requires canonical SUCCESS for every ID")
        if key == "minicpm":
            original = row["original_status"], row["original_label"]
            same = original == ("SUCCESS", row["generated_label"])
            conversion = original == ("INVALID", None) and row["generated_label"] == "Level04"
            require(same or conversion, "MiniCPM: C1 prediction changed outside the authorized mapping")
            conversions += conversion
            strict_rows.append({**row, "status": original[0],
                                "generated_label": original[1] if same else "INVALID"})
    if key == "minicpm":
        require(conversions == mini_conversion_n, "MiniCPM: authorized conversion count mismatch")
    evidence = {"product_id": product["product_id"], "source_seal_sha256": product["source_seal_sha256"],
                "sources": sources, "source_counts": dict(Counter(row["source_id"]
                                                                  for row in by_id.values()))}
    return [by_id[sid] for sid in metadata], strict_rows, evidence


def label_summary(rows):
    result = metrics(rows)
    result["valid_label_rate"] = ratio(len(rows) - result["invalid_n"], len(rows))
    result["status_counts"] = dict(Counter(row["status"] for row in rows))
    result["binary"]["fnr"] = result["binary"]["false_safe"]
    result["binary"]["fpr"] = result["binary"]["false_alarm"]
    return result


def normalization_impact(original, strict, normalized):
    """Track INVALID → Normal using the original status and fixed GT support."""
    converted = Counter(row["true_level"] for row in original if row["status"] == "INVALID")
    before, after = strict["binary"], normalized["binary"]
    endpoints = {
        "valid_label_rate": (strict["valid_label_rate"], normalized["valid_label_rate"]),
        "accuracy": (strict["accuracy"], normalized["accuracy"]),
        "hazard_false_safe": (before["fnr"], after["fnr"]),
        "level01_false_safe": (strict["severe_false_safe"], normalized["severe_false_safe"]),
        "hazard_missed_or_invalid": tuple(
            ratio(binary["FN"] + binary["U_A"], binary["hazard_support"])
            for binary in (before, after)),
    }
    return {
        "converted_n": sum(converted.values()),
        "converted_by_true_level": {level: converted[level] for level in LEVELS},
        "hazard_invalid_to_false_safe_n": sum(converted[level] for level in LEVELS[:-1]),
        "normal_invalid_to_true_negative_n": converted["Level04"],
        "strict_c1_invalid_n": strict["invalid_n"],
        "normalized_invalid_n": normalized["invalid_n"],
        "endpoints": {name: {"strict_c1": prior, "normalization_v1": current,
                             "change": ratio(current["numerator"] - prior["numerator"],
                                             prior["denominator"])}
                      for name, (prior, current) in endpoints.items()},
    }


def paired(left, right, *, binary=False):
    counts = Counter()
    hazard = {level: level != "Level04" for level in LEVELS}
    valid = disagreed = 0
    for a, b in zip(left, right, strict=True):
        require(a["sample_id"] == b["sample_id"], "paired row order mismatch")
        truth = a["true_level"]
        pa, pb = a["generated_label"], b["generated_label"]
        joint = "INVALID" not in (pa, pb)
        valid += joint
        if binary:
            truth, pa, pb = hazard[truth], hazard.get(pa), hazard.get(pb)
        disagreed += joint and pa != pb
        counts[(pa == truth, pb == truth)] += 1
    n = len(left)
    return {"planned_n": n, "joint_valid_n": valid, "excluded_invalid_n": n - valid,
            "label_disagreement": ratio(disagreed, valid),
            "both_correct": counts[True, True], "both_wrong": counts[False, False],
            "left_only_correct": counts[True, False], "right_only_correct": counts[False, True]}


def paired_false_safe(left, right, levels):
    counts = Counter()
    for a, b in zip(left, right, strict=True):
        require(a["sample_id"] == b["sample_id"], "paired row order mismatch")
        if a["true_level"] in levels:
            counts[a["generated_label"] == "Level04", b["generated_label"] == "Level04"] += 1
    n = sum(counts.values())
    return {
        "support_n": n,
        "both_false_safe": ratio(counts[True, True], n),
        "left_only_false_safe": ratio(counts[True, False], n),
        "right_only_false_safe": ratio(counts[False, True], n),
        "neither_false_safe": ratio(counts[False, False], n),
    }


def pair_summary(left, right, *, primary):
    result = {"four_level": paired(left, right), "binary": paired(left, right, binary=True)}
    if primary:
        result["hazard_false_safe"] = paired_false_safe(left, right, LEVELS[:-1])
        result["level01_false_safe"] = paired_false_safe(left, right, LEVELS[:1])
    return result


def worst_domains(domains):
    extractors = {
        "accuracy": (lambda m: m["accuracy"]["value"], min),
        "macro_f1": (lambda m: m["macro_f1"], min),
        "balanced_accuracy": (lambda m: m["balanced_accuracy"], min),
        "false_safe": (lambda m: m["binary"]["false_safe"]["value"], max),
        "false_alarm": (lambda m: m["binary"]["false_alarm"]["value"], max),
        "severe_false_safe": (lambda m: m["severe_false_safe"]["value"], max),
    }
    result = {}
    for name, (measure, extreme) in extractors.items():
        values = {domain: measure(metric) for domain, metric in domains.items()}
        value = extreme((v for v in values.values() if v is not None), default=None)
        result[name] = {"domains": [d for d, v in values.items() if v == value and v is not None],
                        "value": value}
    return result


def compare(cohort, products, config, *, mini_conversion_n=205):
    require(set(products) == set(config["products"]) == set(PRODUCTS), "exact product roster required")
    rows, metadata = validate_cohort(cohort, config["planned_n"])
    panels, provenance = {}, {}
    for key in PRODUCTS:
        panels[key], original, provenance[key] = validate_product(
            key, products[key], config["products"][key], metadata, mini_conversion_n)
        if key == "minicpm":
            panels["minicpm_c1"] = original
    strata = {}
    for index_, row in enumerate(rows):
        strata.setdefault(row["domain"], []).append(index_)
    duplicate_counts = Counter(row["image_sha256"] for row in rows)
    labels_by_hash = defaultdict(set)
    for row in rows:
        labels_by_hash[row["image_sha256"]].add(row["true_level"])
    by_model = {}
    for key, panel in panels.items():
        domains = {domain: label_summary([panel[i] for i in indices])
                   for domain, indices in sorted(strata.items())}
        by_model[key] = {"overall": label_summary(panel), "by_domain": domains,
                         "worst_domain": worst_domains(domains)}
    strict_metrics, normalized_metrics = by_model["minicpm_c1"], by_model["minicpm"]
    c1_panel = panels["minicpm_c1"]
    normalization = {
        "overall": normalization_impact(c1_panel, strict_metrics["overall"],
                                        normalized_metrics["overall"]),
        "by_domain": {domain: normalization_impact(
            [c1_panel[i] for i in indices], strict_metrics["by_domain"][domain],
            normalized_metrics["by_domain"][domain])
            for domain, indices in sorted(strata.items())},
    }
    paired_results = {}
    pairs = [*combinations(PRODUCTS, 2), ("minicpm_c1", "minicpm")]
    for left, right in pairs:
        primary = left != "minicpm_c1"
        per_domain = {}
        for domain, indices in sorted(strata.items()):
            a = [panels[left][i] for i in indices]
            b = [panels[right][i] for i in indices]
            per_domain[domain] = pair_summary(a, b, primary=primary)
        paired_results[f"{left}|{right}"] = {
            **pair_summary(panels[left], panels[right], primary=primary),
            "by_domain": per_domain,
        }
    triple_errors = Counter(
        tuple(key for key, p in zip(PRODUCTS, row, strict=True) if p["generated_label"] != p["true_level"])
        for row in zip(*(panels[key] for key in PRODUCTS), strict=True))
    return {
        "schema": SCHEMA, "cohort_role": "EXPOSED_TRAIN_RETROSPECTIVE",
        "planned_n": len(rows), "cohort_identity_sha256": digest(
            [[r["sample_id"], *(r[field] for field in IDENTITY)] for r in rows]),
        "distinct_image_sha256_n": len(duplicate_counts),
        "duplicate_content_groups": sum(count > 1 for count in duplicate_counts.values()),
        "duplicate_groups_with_conflicting_gt": sum(len(labels) > 1 for labels in labels_by_hash.values()),
        "provenance": provenance, "models": by_model, "paired": paired_results,
        "minicpm_normalization_impact": normalization,
        "four_level_error_patterns": [
            {"models_in_error": list(keys), "n": n} for keys, n in sorted(triple_errors.items())],
        "scores": {key: {"status": "N/A", "reason": product["score_limit"],
                         "AUROC": None, "AUPRC": None, "FNR_at_fixed_FPR": None,
                         "calibration": None, "risk_coverage": None}
                   for key, product in config["products"].items()},
        "inference_intervals": {"status": "N/A", "reason": "FIXED_EXPOSED_COHORT_SOURCE_CLUSTERS_UNVERIFIED"},
    }
