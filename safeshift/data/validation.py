"""Read-only quality audit of the audited InspecSafe triplets, one sample at a time."""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
import unicodedata
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

import PIL
from PIL import Image, ImageFile, features

from .manifest import (
    DATA_TYPES, LEVELS, W1_EXPECTED, ManifestError, image_format_from_header,
    infer_text_domain, iter_sample_candidates, repository_path, sample_metadata,
)

# References for comparison only; none of these values controls traversal/acceptance.
REGRESSION_EXPECTED = {
    **W1_EXPECTED, "Normal_data": 4013, "Anomaly_data": 1000,
    "incomplete_malformed": 0,
}
SCHEMA_EXPECTED = {"total_shapes": 37434, "unique_raw_labels": 231,
                   "unique_points": 3234, "binary_dimension_mismatch": 0,
                   "non_polygon": 0, "empty_txt": 0, "multiline_txt": 0}
COUNTS = """total_samples valid_samples samples_with_errors samples_with_warnings
clean_samples missing_files unreadable_files malformed_json invalid_utf8_txt
JPEG PNG unknown_format image_verified image_verify_failures binary_dimensions_read
binary_dimension_match binary_dimension_mismatch dimension_comparison_unavailable
total_shapes polygon_count non_polygon malformed_shapes malformed_points
malformed_polygon polygons_lt3_points polygons_lt3_unique_points zero_area_polygons
degenerate_polygon out_of_bounds_polygon invalid_labels empty_labels whitespace_labels
non_string_labels padded_labels unicode_labels empty_txt whitespace_txt multiline_txt
txt_control_characters txt_nul unknown_text_domain domain_mismatch image_path_mismatch
image_data_present image_data_absent_or_null image_data_empty image_data_skipped
image_data_checked image_data_invalid_base64 image_data_match image_data_mismatch
image_data_comparison_unavailable invalid_metadata duplicate_sample_ids
duplicate_point_ids non_consecutive_instance_sequences incomplete_malformed
structural_errors train test Normal_data Anomaly_data""".split()
# Precisely the failure classes that the existing manifest checks before emitting a row.
MANIFEST_FAILURES = {
    "invalid_metadata", "missing_files", "unreadable_files", "malformed_json",
    "invalid_dimensions", "invalid_shapes", "malformed_shapes", "non_string_labels",
    "unknown_format", "invalid_utf8_txt", "duplicate_sample_ids",
}


def _issue(sample, counts, code, severity="ERROR", *, shape_index=None, detail=None):
    issue = {"code": code, "severity": severity}
    if shape_index is not None:
        issue["shape_index"] = shape_index
    if detail is not None:
        issue["detail"] = detail
    sample["issues"].append(issue)
    counts[code] += 1


def _finite_number(value):
    # Integers are finite even when too large for float conversion; bool is not a coordinate.
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _shapes(annotation, sample, counts, labels, bounds):
    shapes = annotation.get("shapes")
    if not isinstance(shapes, list):
        _issue(sample, counts, "invalid_shapes")
        return
    counts["total_shapes"] += len(shapes)
    for index, shape in enumerate(shapes):
        def issue(code, severity="ERROR", detail=None):
            _issue(sample, counts, code, severity, shape_index=index, detail=detail)

        if not isinstance(shape, dict):
            issue("malformed_shapes")
            continue
        label = shape.get("label")
        if not isinstance(label, str):
            counts["invalid_labels"] += 1
            issue("non_string_labels")
        else:
            labels[label] += 1  # Lossless raw strings, including Unicode and whitespace.
            if not label:
                counts["invalid_labels"] += 1
                issue("empty_labels")
            elif not label.strip():
                counts["invalid_labels"] += 1
                issue("whitespace_labels")
            elif label != label.strip():
                issue("padded_labels", "WARNING")
            if not label.isascii():
                counts["unicode_labels"] += 1
        shape_type = shape.get("shape_type")
        polygon = shape_type == "polygon"
        if polygon:
            counts["polygon_count"] += 1
        else:
            issue("non_polygon", "WARNING" if isinstance(shape_type, str) and shape_type else "ERROR")
        points = shape.get("points")
        if not isinstance(points, list) or any(
            not isinstance(p, list) or len(p) != 2 or not all(_finite_number(v) for v in p)
            for p in points
        ):
            issue("malformed_points")
            if polygon:
                counts["malformed_polygon"] += 1
            continue
        if not polygon:
            continue
        degenerate = False
        if len(points) < 3:
            issue("polygons_lt3_points", "WARNING")
            degenerate = True
        if len({tuple(p) for p in points}) < 3:
            issue("polygons_lt3_unique_points", "WARNING")
            degenerate = True
        # Exact rational shoelace on the parsed numbers avoids float overflow and
        # cancellation. This does not test self-intersection or semantic validity.
        rational = [(Fraction(x), Fraction(y)) for x, y in points]
        twice_area = sum(x * v - u * y for (x, y), (u, v)
                         in zip(rational, rational[1:] + rational[:1]))
        if twice_area == 0:
            issue("zero_area_polygons", "WARNING")
            degenerate = True
        counts["degenerate_polygon"] += int(degenerate)
        if bounds is not None and any(not (0 <= x <= bounds[0] and 0 <= y <= bounds[1])
                                      for x, y in points):
            issue("out_of_bounds_polygon", "WARNING")


def _image(raw, sample, counts):
    if raw is None:
        return None
    try:
        fmt = image_format_from_header(raw[:8])
    except ManifestError:
        _issue(sample, counts, "unknown_format")
        return None
    sample["image_format"] = fmt
    counts[fmt] += 1
    if fmt == "PNG":
        _issue(sample, counts, "image_extension_mismatch", "WARNING")
    dimensions = None
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with Image.open(io.BytesIO(raw)) as image:
                dimensions = image.size
                sample["binary_image_width"], sample["binary_image_height"] = dimensions
                counts["binary_dimensions_read"] += 1
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                image.load()  # A second open is required after verify().
            for warning in caught:
                _issue(sample, counts, "image_decoder_warning", "WARNING",
                       detail=warning.category.__name__)
        counts["image_verified"] += 1
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
        _issue(sample, counts, "image_verify_failures", detail=type(exc).__name__)
    return dimensions


def _annotation(raw, image_raw, sample, counts, labels, binary_dimensions, verify_image_data):
    if raw is None:
        counts["dimension_comparison_unavailable"] += 1
        return
    try:
        annotation = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError):
        _issue(sample, counts, "malformed_json")
        counts["dimension_comparison_unavailable"] += 1
        return
    if not isinstance(annotation, dict):
        _issue(sample, counts, "malformed_json", detail="top-level must be an object")
        counts["dimension_comparison_unavailable"] += 1
        return
    dims = (annotation.get("imageWidth"), annotation.get("imageHeight"))
    dims_valid = all(type(v) is int and v > 0 for v in dims)
    if not dims_valid:
        _issue(sample, counts, "invalid_dimensions")
    if dims_valid and binary_dimensions is not None:
        if dims == binary_dimensions:
            counts["binary_dimension_match"] += 1
        else:
            _issue(sample, counts, "binary_dimension_mismatch", "WARNING",
                   detail={"json_width": dims[0], "json_height": dims[1]})
    else:
        counts["dimension_comparison_unavailable"] += 1
    if "imagePath" in annotation:
        image_path = annotation["imagePath"]
        if not isinstance(image_path, str):
            _issue(sample, counts, "invalid_image_path_type")
        elif image_path.replace("\\", "/").split("/")[-1] != sample["sample_id"] + ".jpg":
            _issue(sample, counts, "image_path_mismatch", "WARNING")
    embedded = annotation.pop("imageData", None)
    if embedded is None:
        counts["image_data_absent_or_null"] += 1
    elif not isinstance(embedded, str):
        _issue(sample, counts, "invalid_image_data_type")
    else:
        counts["image_data_present"] += 1
        if not embedded:
            _issue(sample, counts, "image_data_empty", "WARNING")
        elif not verify_image_data:
            counts["image_data_skipped"] += 1
        else:
            counts["image_data_checked"] += 1
            try:
                decoded = base64.b64decode(embedded, validate=True)
            except (ValueError, binascii.Error):
                _issue(sample, counts, "image_data_invalid_base64")
            else:
                if image_raw is None:
                    counts["image_data_comparison_unavailable"] += 1
                elif hashlib.sha256(decoded).digest() == hashlib.sha256(image_raw).digest():
                    counts["image_data_match"] += 1
                else:
                    _issue(sample, counts, "image_data_mismatch", "WARNING",
                           detail="decoded bytes differ; external image remains independently audited")
                del decoded
    del embedded
    # Binary dimensions take precedence only for the bounds check, not ground truth labels.
    _shapes(annotation, sample, counts, labels,
            binary_dimensions if binary_dimensions is not None else (dims if dims_valid else None))


def _text(raw, sample, counts, line_counts):
    if raw is None:
        return
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        _issue(sample, counts, "invalid_utf8_txt")
        return
    lines = len(text.splitlines())
    sample["txt_line_count"] = lines
    line_counts[str(lines)] += 1
    if not text:
        _issue(sample, counts, "empty_txt")
    elif not text.strip():
        _issue(sample, counts, "whitespace_txt")
    if lines > 1:
        _issue(sample, counts, "multiline_txt", "WARNING")
    controls = sorted({f"U+{ord(c):04X}" for c in text
                       if unicodedata.category(c) in ("Cc", "Cf") and c not in "\t\r\n"})
    if controls:
        _issue(sample, counts, "txt_control_characters", "WARNING", detail=controls)
    if "\x00" in text:
        _issue(sample, counts, "txt_nul", "WARNING")
    domain = infer_text_domain(text)
    sample["text_domain"] = domain
    if domain is None:
        _issue(sample, counts, "unknown_text_domain", "WARNING")
    elif sample.get("folder_domain") is not None and domain != sample["folder_domain"]:
        _issue(sample, counts, "domain_mismatch", "WARNING")


def validate_dataset(dataset_root: Path, repo_root: Path, *, verify_image_data=False):
    """Return a deterministic report body. No output writes, filtering, or raw mutation.

    Missing/unreadable individual files are sample errors; traversal/layout failures
    mark the audit incomplete. A filesystem traversal exception propagates to CLI.
    """
    if ImageFile.LOAD_TRUNCATED_IMAGES:
        raise ManifestError("strict image decoding requires LOAD_TRUNCATED_IMAGES=False")
    repo_root = repo_root.resolve()
    dataset_root = repository_path(dataset_root, repo_root)
    counts = Counter({key: 0 for key in COUNTS})
    labels, line_counts = Counter(), Counter()
    samples, structural_issues = [], []
    fingerprint = hashlib.sha256()
    points, ids = {}, defaultdict(list)
    cross_table = {kind: Counter({level: 0 for level in LEVELS}) for kind in DATA_TYPES}

    def structural(path, reason):
        structural_issues.append({"path": path.relative_to(repo_root).as_posix(),
                                  "severity": "ERROR", "code": "structural_error", "detail": reason})
        counts["structural_errors"] += 1

    for point_dir, stem, split, data_type in iter_sample_candidates(dataset_root, repo_root, structural):
        point_rel = point_dir.relative_to(repo_root).as_posix()
        sample = {"sample_id": stem, "point_folder": point_rel, "split": split,
                  "data_type": data_type, "issues": []}
        counts["total_samples"] += 1
        counts[split] += 1
        counts[data_type] += 1
        point = points.setdefault(point_rel, {"point_folder": point_rel, "split": split,
                                             "data_type": data_type, "instance_ids": [], "samples": []})
        point["samples"].append(sample)
        try:
            metadata = sample_metadata(point_dir, stem, split=split, data_type=data_type)
        except ManifestError as exc:
            _issue(sample, counts, "invalid_metadata", detail=str(exc))
        else:
            sample.update(metadata)
            sample["instance_id"] = stem[-3:]
            point["instance_ids"].append(stem[-3:])
            point["point_id"] = metadata["point_id"]
            cross_table[data_type][metadata["safety_level"]] += 1
        ids[stem].append(sample)
        raw = {}
        # Each candidate contributes three records, even when missing or unreadable.
        for ext in ("jpg", "json", "txt"):
            path = point_dir / f"{stem}.{ext}"
            repository_path(path, repo_root)
            try:
                raw[ext] = path.read_bytes()
                digest = hashlib.sha256(raw[ext]).hexdigest()
            except FileNotFoundError:
                raw[ext], digest = None, "MISSING"
                _issue(sample, counts, "missing_files", detail={"extension": ext})
            except OSError as exc:
                raw[ext], digest = None, "UNREADABLE"
                _issue(sample, counts, "unreadable_files", detail={"extension": ext, "errno": exc.errno})
            record = [path.relative_to(repo_root).as_posix(), digest]
            fingerprint.update(json.dumps(record, ensure_ascii=True).encode("ascii") + b"\n")
        dimensions = _image(raw["jpg"], sample, counts)
        _annotation(raw["json"], raw["jpg"], sample, counts, labels, dimensions, verify_image_data)
        _text(raw["txt"], sample, counts, line_counts)
        del raw
        samples.append(sample)
    if not samples:
        structural(dataset_root, "no sample candidates found")
    for duplicates in ids.values():
        if len(duplicates) > 1:
            for sample in duplicates:
                _issue(sample, counts, "duplicate_sample_ids")

    point_ids = defaultdict(list)
    distributions = defaultdict(Counter)
    for point in points.values():
        members = point.pop("samples")
        point["instance_ids"].sort()
        point["instance_count"] = len(members)
        integers = [int(value) for value in point["instance_ids"]]
        point["missing_instance_ids"] = [f"{i:03d}" for i in range(1, max(integers, default=0) + 1)
                                          if i not in integers]
        point["non_consecutive"] = bool(integers) and integers != list(range(1, len(integers) + 1))
        if point["non_consecutive"]:
            counts["non_consecutive_instance_sequences"] += 1
            for member in members:
                _issue(member, counts, "instance_sequence_warning", "WARNING")
        if "point_id" in point:
            point_ids[point["point_id"]].append(point["point_folder"])
        for key in ("all", point["data_type"], f"{point['split']}/{point['data_type']}"):
            distributions[key][str(len(members))] += 1
    duplicate_points = {key: paths for key, paths in sorted(point_ids.items()) if len(paths) > 1}
    counts["duplicate_point_ids"] = len(duplicate_points)
    for sample in samples:
        if sample.get("point_id") in duplicate_points:
            _issue(sample, counts, "point_id_reused", "WARNING")
        severities = {issue["severity"] for issue in sample["issues"]}
        counts["samples_with_errors"] += "ERROR" in severities
        counts["samples_with_warnings"] += "WARNING" in severities
        counts["valid_samples"] += "ERROR" not in severities
        counts["clean_samples"] += not severities
        counts["incomplete_malformed"] += any(i["code"] in MANIFEST_FAILURES for i in sample["issues"])
    counts["unique_points"] = len(points)
    counts["unique_point_ids"] = len(point_ids)
    counts["unique_raw_labels"] = len(labels)
    # Candidate variants only: never change the raw frequency keys or assign classes.
    variants = defaultdict(list)
    for label in sorted(labels):
        variants[label.strip().casefold()].append(label)
    summary = dict(counts)
    summary["data_type_x_safety_level"] = {key: dict(value) for key, value in cross_table.items()}
    summary["instance_count_distribution"] = {key: dict(sorted(value.items()))
                                               for key, value in sorted(distributions.items())}
    summary["txt_line_count_distribution"] = dict(sorted(line_counts.items()))
    all_issues = structural_issues + [i for sample in samples for i in sample["issues"]]
    error_count = sum(i["severity"] == "ERROR" for i in all_issues)
    warning_count = sum(i["severity"] == "WARNING" for i in all_issues)
    def discrepancies(expected):
        return [{"field": key, "expected": value, "observed": summary[key]}
                for key, value in expected.items() if summary[key] != value]

    return {
        "report_version": 1, "audit_complete": not structural_issues,
        "exit_code": 1 if structural_issues else (2 if error_count else 0),
        "dataset_root": dataset_root.relative_to(repo_root).as_posix(),
        "validation_options": {"verify_image_data": verify_image_data, "image_verify": True,
                               "image_decode": True, "allow_truncated_images": False,
                               "polygon_bounds": "0 <= x <= binary width; 0 <= y <= binary height; JSON fallback",
                               "polygon_area": "exact rational shoelace; zero means exactly zero"},
        "input_sha256": fingerprint.hexdigest(),
        "input_sha256_method": "SHA-256 of ASCII JSON lines [repo-relative path, SHA-256 of full bytes "
            "or MISSING/UNREADABLE]. Order: train/test, Normal_data/Anomaly_data, sorted points/stems, "
            "jpg/json/txt. Covers candidate triplets only; excludes archives/modalities. "
            "Different serialization from manifest fingerprint; do not compare directly.",
        "summary": summary, "errors_count": error_count, "warnings_count": warning_count,
        "regression_discrepancies": discrepancies(REGRESSION_EXPECTED),
        "schema_discrepancies": discrepancies(SCHEMA_EXPECTED),
        "raw_label_frequency": dict(sorted(labels.items())),
        "raw_label_case_whitespace_variant_candidates": [values for values in variants.values() if len(values) > 1],
        "structural_issues": structural_issues, "duplicate_point_ids": duplicate_points,
        "points": list(points.values()), "samples": samples,
    }


def write_report(report, output: Path, repo_root: Path):
    """Attach provenance and atomically write a report outside raw data."""
    repo_root = repo_root.resolve()
    output = repository_path(output, repo_root)
    dataset_root = repository_path(Path(report["dataset_root"]), repo_root)
    raw_root = (repo_root / "data/raw").resolve()
    if output.is_relative_to(dataset_root) or output.is_relative_to(raw_root):
        raise ManifestError("output must not be inside the raw dataset")
    if output.suffix != ".json":
        raise ManifestError("output must have a .json suffix")

    def git(*args):
        try:
            return subprocess.check_output(["git", *args], cwd=repo_root, text=True,
                                           encoding="utf-8", stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    sources = ("safeshift/data/validation.py", "safeshift/data/manifest.py", "scripts/validate_dataset.py",
               "requirements-validation.txt", "notes/dataset_schema.md", "notes/manifest_builder.md")
    created = datetime.now(timezone.utc)
    command = ["python", "scripts/validate_dataset.py", "--dataset-root", report["dataset_root"],
               "--output", output.relative_to(repo_root).as_posix()]
    if report["validation_options"]["verify_image_data"]:
        command.append("--verify-image-data")
    payload = {**report, "run_id": created.strftime("validation-%Y%m%dT%H%M%S%fZ"),
               "created_utc": created.isoformat(), "git_commit": git("rev-parse", "HEAD"),
               "git_status": git("status", "--porcelain"), "python": sys.version.split()[0],
               "platform": platform.platform(), "dependencies": {"Pillow": PIL.__version__,
                    "libjpeg": features.version_codec("jpg"), "zlib": features.version_codec("zlib")},
               "command": command, "seed": None, "dataset": "InspecSafe-V1",
               "upstream_release": None, "upstream_url": None, "archive_checksums": None,
               "source": "local extracted dataset; notes/dataset_schema.md",
               "source_sha256": {name: hashlib.sha256((repo_root / name).read_bytes()).hexdigest()
                                  for name in sources if (repo_root / name).is_file()}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return payload
