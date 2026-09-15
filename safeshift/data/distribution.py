"""Descriptive W1 distribution audit; raw labels and official samples stay intact."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from statistics import mean, median

from safeshift.data.manifest import (
    DATA_TYPES, DOMAINS, LEVELS, SPLITS, ManifestError, collect_manifest,
    repository_path,
)

CATEGORIES = {
    "split": SPLITS, "data_type": DATA_TYPES, "folder_domain": DOMAINS,
    "text_domain": DOMAINS, "safety_level": LEVELS,
    "robot_platform": ("SuspendedRail", "Wheeled"),
}
METADATA_FIELDS = (
    "folder_domain", "text_domain", "safety_level", "robot_platform",
    "image_width", "image_height", "object_labels", "text_description",
)
TABLES = (
    ("split", "data_type"), ("split", "safety_level"),
    ("split", "folder_domain"), ("split", "folder_domain", "data_type"),
    ("split", "folder_domain", "safety_level"), ("folder_domain", "safety_level"),
    ("folder_domain", "data_type"), ("robot_platform", "folder_domain"),
    ("robot_platform", "data_type"), ("folder_domain", "text_domain"),
)


def _key(value):
    return (value is not None, str(value))


def cross_table(rows, fields, categories=None):
    """Last field is the column; all preceding fields jointly define a row.

    Known categories form a Cartesian product including zeros. Observed extra
    categories/nulls are retained. Empty row percentages are undefined (None).
    """
    if not fields or len(set(fields)) != len(fields):
        raise ValueError("fields must be nonempty and distinct")
    categories = CATEGORIES if categories is None else categories
    axes = [sorted(set(categories.get(f, ())) | {r.get(f) for r in rows}, key=_key)
            for f in fields]
    counts = Counter(tuple(r.get(f) for f in fields) for r in rows)
    totals = Counter(tuple(r.get(f) for f in fields[:-1]) for r in rows)
    cells = []
    for values in product(*axes):
        count, denominator = counts[values], totals[values[:-1]]
        cells.append({**dict(zip(fields, values)), "count": count,
                      "row_total": denominator,
                      "row_percentage": 100 * count / denominator if denominator else None})
    return {"fields": list(fields), "total": len(rows),
            "row_fields": list(fields[:-1]), "column_field": fields[-1], "cells": cells}


def rare_flags(count):
    """Overlapping descriptive flags; these are not statistical decision rules."""
    if type(count) is not int or count < 0:
        raise ValueError("count must be a nonnegative integer")
    return {"zero": count == 0, "lt10": count < 10, "lt30": count < 30}


def total_variation(train, test):
    """TVD = 0.5 * sum(abs(train[k]/N_train - test[k]/N_test))."""
    if any(type(v) is not int or v < 0 for c in (train, test) for v in c.values()):
        raise ValueError("frequencies must be nonnegative integers")
    n_train, n_test = sum(train.values()), sum(test.values())
    detail = []
    for value in sorted(set(train) | set(test), key=_key):
        p = train.get(value, 0) / n_train if n_train else None
        q = test.get(value, 0) / n_test if n_test else None
        detail.append({"category": value, "train_count": train.get(value, 0),
                       "test_count": test.get(value, 0),
                       "train_percentage": None if p is None else 100 * p,
                       "test_percentage": None if q is None else 100 * q,
                       "absolute_percentage_point_difference":
                       None if p is None or q is None else 100 * abs(p - q)})
    tvd = (sum(d["absolute_percentage_point_difference"] for d in detail) / 200
           if n_train and n_test else None)
    return {"train_total": n_train, "test_total": n_test, "tvd": tvd, "categories": detail}


def numeric_summary(values):
    """Quartiles use linear interpolation at (n-1)*p, including singleton data."""
    values = sorted(values)
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError("values must be finite numbers")

    def quantile(p):
        index = (len(values) - 1) * p
        low, high = math.floor(index), math.ceil(index)
        return values[low] + (values[high] - values[low]) * (index - low)

    return {"count": len(values), "min": min(values) if values else None,
            "q1": quantile(.25) if values else None,
            "median": median(values) if values else None,
            "mean": mean(values) if values else None,
            "q3": quantile(.75) if values else None,
            "max": max(values) if values else None}


def aspect_ratio(width, height):
    if any(type(v) is not int or v <= 0 for v in (width, height)):
        raise ValueError("dimensions must be positive integers")
    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def _frequencies(counter, denominator=None):
    denominator = sum(counter.values()) if denominator is None else denominator
    return [{"value": value, "count": count, "denominator": denominator,
             "percentage": 100 * count / denominator if denominator else None}
            for value, count in sorted(counter.items(), key=lambda item: (-item[1], _key(item[0])))]


def resolution_summary(rows):
    valid = [r for r in rows if all(type(r.get(f)) is int and r[f] > 0
                                   for f in ("image_width", "image_height"))]
    resolutions = Counter(f"{r['image_width']}x{r['image_height']}" for r in valid)
    ratios = Counter(aspect_ratio(r["image_width"], r["image_height"]) for r in valid)
    return {"count": len(valid), "unavailable": len(rows) - len(valid),
            "unique_resolutions": len(resolutions), "resolutions": _frequencies(resolutions),
            "width": numeric_summary([r["image_width"] for r in valid]),
            "height": numeric_summary([r["image_height"] for r in valid]),
            "width_frequencies": _frequencies(Counter(r["image_width"] for r in valid)),
            "height_frequencies": _frequencies(Counter(r["image_height"] for r in valid)),
            "aspect_ratios": _frequencies(ratios),
            "aspect_ratio_numeric": numeric_summary([r["image_width"] / r["image_height"] for r in valid]),
            "aspect_groups": _frequencies(Counter({
                "16:9": ratios["16:9"], "4:3": ratios["4:3"],
                "other": sum(n for ratio, n in ratios.items() if ratio not in ("16:9", "4:3")),
            }))}


def annotation_density(rows):
    def stats(subset):
        values = [r["num_shapes"] for r in subset]
        if any(type(v) is not int or v < 0 for v in values):
            raise ValueError("num_shapes must be a nonnegative integer")
        return {**numeric_summary(values), "total_shapes": sum(values),
                "zero_shape_samples": values.count(0),
                "histogram": _frequencies(Counter(values))}

    return {"overall": stats(rows), "by": {
        field: [{field: value, **stats([r for r in rows if r.get(field) == value])}
                for value in sorted(set(CATEGORIES[field]) | {r.get(field) for r in rows}, key=_key)]
        for field in ("data_type", "safety_level", "folder_domain", "split")}}


def label_summary(rows):
    total, train, test = Counter(), Counter(), Counter()
    domains = {d: Counter() for d in sorted(set(DOMAINS) | {r.get("folder_domain") for r in rows}, key=_key)}
    available = 0
    for row in rows:
        labels = row.get("object_labels")
        if labels is None:
            continue
        if not isinstance(labels, list) or any(not isinstance(v, str) for v in labels):
            raise ValueError("object_labels must be a list of raw strings or None")
        available += 1
        total.update(labels)  # Deliberately count repeated labels as shape instances.
        if row.get("split") == "train":
            train.update(labels)
        if row.get("split") == "test":
            test.update(labels)
        domains[row.get("folder_domain")].update(labels)
    coverage = [{"label": label, "train_count": train[label], "test_count": test[label],
                 "appears_train": train[label] > 0, "appears_test": test[label] > 0,
                 "domains": [d for d, counts in domains.items() if counts[label]]}
                for label in sorted(total)]
    tail = {name: [label for label in sorted(total) if predicate(total[label])]
            for name, predicate in (
                ("singleton", lambda n: n == 1), ("le5", lambda n: n <= 5),
                ("le10", lambda n: n <= 10), ("ge100", lambda n: n >= 100))}
    split_sets = {
        "train_only": [c["label"] for c in coverage if c["appears_train"] and not c["appears_test"]],
        "test_only": [c["label"] for c in coverage if c["appears_test"] and not c["appears_train"]],
        "both": [c["label"] for c in coverage if c["appears_train"] and c["appears_test"]],
        "very_rare_in_test_1_to_5": [c["label"] for c in coverage if 1 <= c["test_count"] <= 5],
        "rare_in_test_1_to_10": [c["label"] for c in coverage if 1 <= c["test_count"] <= 10],
    }
    return {"samples_with_label_list": available, "total_instances": sum(total.values()),
            "unique_raw_labels": len(total), "frequencies": _frequencies(total),
            "top20": _frequencies(total)[:20], "tail_labels": tail,
            "tail_counts": {k: len(v) for k, v in tail.items()}, "split_coverage": coverage,
            "split_labels": split_sets, "split_counts": {k: len(v) for k, v in split_sets.items()},
            "single_domain_labels": [c["label"] for c in coverage if len(c["domains"]) == 1],
            "multiple_domain_labels": [c["label"] for c in coverage if len(c["domains"]) > 1],
            "by_domain": [{"folder_domain": d, "unique_raw_labels": len(counts),
                           "total_instances": sum(counts.values()), "top20": _frequencies(counts)[:20]}
                          for d, counts in domains.items()]}


def missing_metadata(rows):
    result = {}
    for field in METADATA_FIELDS:
        values = [r.get(field) for r in rows]
        null = sum(v is None for v in values)
        empty = sum(v == "" or v == [] for v in values)
        whitespace = sum(isinstance(v, str) and v != "" and not v.strip() for v in values)
        if field in CATEGORIES:
            unknown = sum(v is not None and v != "" and v not in CATEGORIES[field] for v in values)
            # The existing text parser explicitly uses None for an unparsed opening.
            if field == "text_domain":
                unknown += null
        elif field in ("image_width", "image_height"):
            unknown = sum(v is not None and v != "" and (type(v) is not int or v <= 0) for v in values)
        elif field == "object_labels":
            unknown = sum(v is not None and (not isinstance(v, list) or
                          any(not isinstance(label, str) for label in v)) for v in values)
        else:
            unknown = sum(v is not None and not isinstance(v, str) for v in values)
        result[field] = {"denominator": len(rows), "null_count": null, "empty_count": empty,
                         "whitespace_only_count": whitespace, "unknown_unparsed_count": unknown}
    return result


def domain_mismatches(rows):
    known = [r for r in rows if r.get("folder_domain") in DOMAINS and r.get("text_domain") in DOMAINS]
    mismatches = [r for r in known if r["folder_domain"] != r["text_domain"]]
    return {"count": len(mismatches), "comparable_count": len(known),
            "unresolved_count": len(rows) - len(known),
            "by": {f: cross_table(mismatches, (f,)) for f in ("split", "safety_level", "data_type")},
            "matrix": cross_table(mismatches, ("folder_domain", "text_domain")),
            "detail": cross_table(mismatches, ("split", "folder_domain", "text_domain", "safety_level", "data_type"))}


def summarize_distribution(rows):
    """Pure aggregation of typed manifest rows, without copying text into output."""
    tables = {"__".join(fields): cross_table(rows, fields) for fields in TABLES}
    marginals = {f: cross_table(rows, (f,)) for f in CATEGORIES}
    level03 = [r for r in rows if r.get("safety_level") == "Level03"]
    safety_counts = {c["safety_level"]: c["count"] for c in marginals["safety_level"]["cells"]}
    known_counts = [safety_counts[level] for level in LEVELS]
    coverage = [{**cell, "diagnostic_flags": rare_flags(cell["count"])}
                for cell in tables["split__folder_domain__data_type"]["cells"]]
    return {"total": len(rows), "marginals": marginals, "cross_tables": tables,
            "domain_type_coverage": coverage,
            "safety": {"imbalance_ratio": max(known_counts) / min(known_counts) if min(known_counts) else None,
                       "absent_levels": [level for level in LEVELS if not safety_counts[level]],
                       "level03_total": len(level03),
                       "level03_by": {f: cross_table(level03, (f,)) for f in
                                      ("split", "folder_domain", "robot_platform")},
                       "level03_domain_split": cross_table(level03, ("folder_domain", "split"))},
            "divergence": {f: total_variation(
                Counter({v: sum(r.get("split") == "train" and r.get(f) == v for r in rows)
                         for v in sorted(set(CATEGORIES[f]) | {r.get(f) for r in rows}, key=_key)}),
                Counter({v: sum(r.get("split") == "test" and r.get(f) == v for r in rows)
                         for v in sorted(set(CATEGORIES[f]) | {r.get(f) for r in rows}, key=_key)}))
                for f in ("folder_domain", "safety_level", "data_type", "robot_platform")},
            "resolution": resolution_summary(rows), "annotation": annotation_density(rows),
            "labels": label_summary(rows), "missing_metadata": missing_metadata(rows),
            "domain_mismatch": domain_mismatches(rows)}


def regression_checks(report):
    """References are compared only after aggregation; never used to set counts."""
    observed = {"total": report["total"]}
    expected = {"total": 5013, "split/train": 3763, "split/test": 1250,
                "data_type/Normal_data": 4013, "data_type/Anomaly_data": 1000}
    for field, counts in (("folder_domain", dict(zip(DOMAINS, (1121, 720, 1023, 869, 1280)))),
                          ("safety_level", dict(zip(LEVELS, (659, 326, 15, 4013))))):
        expected.update({f"{field}/{key}": value for key, value in counts.items()})
    for field, table in report["marginals"].items():
        observed.update({f"{field}/{cell[field]}": cell["count"] for cell in table["cells"]})
    for cell in report["domain_type_coverage"]:
        if cell["folder_domain"] == "metallurgy":
            observed[f"metallurgy/{cell['split']}/{cell['data_type']}"] = cell["count"]
    expected.update({"metallurgy/train/Normal_data": 534, "metallurgy/train/Anomaly_data": 9,
                     "metallurgy/test/Normal_data": 177, "metallurgy/test/Anomaly_data": 0})
    resolutions = {c["value"]: c["count"] for c in report["resolution"]["resolutions"]}
    top = {"2560x1440": 2576, "1920x1080": 2124, "1280x720": 122}
    for value, count in top.items():
        expected[f"resolution/{value}"] = count
        observed[f"resolution/{value}"] = resolutions.get(value, 0)
    expected.update({"resolution/other": 191, "total_shapes": 37434, "unique_raw_labels": 231,
                     "domain_mismatch": 36, "unknown_text_domain": 0})
    observed.update({"resolution/other": sum(n for v, n in resolutions.items() if v not in top),
                     "total_shapes": report["annotation"]["overall"]["total_shapes"],
                     "unique_raw_labels": report["labels"]["unique_raw_labels"],
                     "domain_mismatch": report["domain_mismatch"]["count"],
                     "unknown_text_domain": report["missing_metadata"]["text_domain"]["unknown_unparsed_count"]})
    return [{"field": key, "expected": expected[key], "observed": observed[key],
             "matches": expected[key] == observed[key]} for key in sorted(expected)]


def audit_distribution(dataset_root, repo_root, *, progress=None):
    from PIL import Image

    repo_root = repo_root.resolve()
    dataset_root = repository_path(dataset_root, repo_root)
    if progress:
        progress("Reading and hashing all raw triplets with the existing manifest builder...")
    manifest = collect_manifest(dataset_root, repo_root)
    if manifest.errors:
        raise ManifestError(f"manifest validation failed: {len(manifest.errors)} issues; audit incomplete")
    dimensions_mismatch = []
    for index, row in enumerate(manifest.rows, 1):
        with Image.open(repository_path(Path(row["image_relpath"]), repo_root)) as image:
            width, height = image.size
        if (width, height) != (row["image_width"], row["image_height"]):
            dimensions_mismatch.append({"sample_id": row["sample_id"],
                                        "annotation": [row["image_width"], row["image_height"]],
                                        "actual": [width, height]})
        row["image_width"], row["image_height"] = width, height
        if progress and (index % 1000 == 0 or index == len(manifest.rows)):
            progress(f"Actual image dimensions checked: {index}/{len(manifest.rows)}")
    report = summarize_distribution(manifest.rows)
    report["input_sha256"] = manifest.input_sha256
    report["image_dimensions_mismatches"] = dimensions_mismatch
    report["regression_checks"] = regression_checks(report)
    report["discrepancies"] = [check for check in report["regression_checks"] if not check["matches"]]
    if dimensions_mismatch:
        report["discrepancies"].append({"field": "actual_vs_annotation_dimensions",
                                        "expected": 0, "observed": len(dimensions_mismatch)})
    report["audit_complete"] = True
    report["exit_code"] = 2 if report["discrepancies"] else 0
    return report


def checked_output(output, dataset_root, repo_root):
    output = repository_path(output, repo_root)
    dataset = repository_path(dataset_root, repo_root)
    if output.is_relative_to(dataset) or output.is_relative_to((repo_root / "data/raw").resolve()):
        raise ManifestError("output must stay outside raw data")
    if output.suffix != ".json":
        raise ManifestError("output must have .json suffix")
    return output


def write_report(report, output, dataset_root, repo_root, *, runtime_seconds):
    from PIL import __version__ as pillow_version

    output = checked_output(output, dataset_root, repo_root)
    dataset = repository_path(dataset_root, repo_root).relative_to(repo_root).as_posix()
    output_rel = output.relative_to(repo_root).as_posix()

    def git(*args):
        try:
            return subprocess.check_output(["git", *args], cwd=repo_root, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    sources = ("safeshift/data/distribution.py", "scripts/audit_distribution.py",
               "safeshift/data/manifest.py", "requirements-validation.txt",
               "notes/dataset_schema.md", "notes/duplicate_leakage_audit.md",
               "notes/visual_provenance_review.md")
    created = datetime.now(timezone.utc)
    report = {**report, "provenance": {
        "report_version": 1, "run_id": created.strftime("distribution-%Y%m%dT%H%M%S%fZ"),
        "created_utc": created.isoformat(), "dataset": "InspecSafe-V1", "dataset_root": dataset,
        "upstream_url": None, "upstream_release": None, "archive_checksums": None,
        "input_sha256_method": "Existing collect_manifest fingerprint: SHA-256 of ASCII JSON lines "
            "[repo-relative path, full-file SHA-256] for jpg/json/txt, then [sample_id, has_other_modalities]. "
            "Traversal train/test, Normal_data/Anomaly_data, sorted point/stem. "
            "Excludes archives, Parameters and modality contents.",
        "git_commit": git("rev-parse", "HEAD"), "git_source_status": git("status", "--porcelain", "--", *sources),
        "source_sha256": {p: hashlib.sha256((repo_root / p).read_bytes()).hexdigest() for p in sources},
        "python": sys.version.split()[0], "os": platform.system(), "Pillow": pillow_version,
        "seed": None, "ordering": "deterministic; no random operations", "runtime_seconds": runtime_seconds,
        "command": ["python", "scripts/audit_distribution.py", "--dataset-root", dataset, "--output", output_rel],
        "output": output_rel,
        "methods": {"row_percentage": "100 * count / sum over last field, holding preceding fields fixed; null if zero denominator",
                    "tvd": "0.5 * sum(abs(p_train - p_test)); null if either split empty; no significance or good/bad threshold",
                    "quartiles": "linear interpolation at (n-1)*p for p=.25,.75",
                    "aspect_ratio": "exact reduced width:height fraction; no tolerance, resize or EXIF transpose",
                    "density": "num_shapes per sample, not area coverage or shapes per pixel",
                    "rare_flags": "overlapping count==0, count<10, count<30; diagnostic only",
                    "test_label_rare": "1..5 and 1..10 shape instances; absent labels reported separately",
                    "missing": "null and empty separate; unknown includes non-schema categories/invalid types; text_domain null also unparsed",
                    "labels": "raw strings unchanged; duplicate labels count as instances; no taxonomy"},
    }}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def cli_summary(report):
    """Compact console summary; full tables and raw-label coverage stay in JSON."""
    marginals = {f: {c[f]: c["count"] for c in table["cells"]}
                 for f, table in report["marginals"].items()}
    return {
        "DATASET": {"total": report["total"], **{f: marginals[f] for f in ("split", "data_type")}},
        "SAFETY": {"counts": marginals["safety_level"], **report["safety"]},
        "DOMAIN": {"counts": marginals["folder_domain"], "coverage": report["domain_type_coverage"]},
        "PLATFORM": {"counts": marginals["robot_platform"],
                     "domain_distribution": report["cross_tables"]["robot_platform__folder_domain"]},
        "RESOLUTION": {k: report["resolution"][k] for k in ("unique_resolutions", "aspect_groups", "aspect_ratios")}
            | {"top_resolutions": report["resolution"]["resolutions"][:10]},
        "ANNOTATION": {"unique_raw_labels": report["labels"]["unique_raw_labels"],
                       **{k: v for k, v in report["annotation"]["overall"].items() if k != "histogram"}},
        "LONG_TAIL": {**report["labels"]["tail_counts"], **report["labels"]["split_counts"]},
        "MISMATCH": report["domain_mismatch"]["count"],
        "MISSING_METADATA": report["missing_metadata"],
        "TRAIN_TEST_DIVERGENCE": {f: d["tvd"] for f, d in report["divergence"].items()},
        "DISCREPANCIES": report["discrepancies"],
    }
