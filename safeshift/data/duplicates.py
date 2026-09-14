"""Read-only image identity and split-overlap audit; similarity is only a candidate.

External images are primary. JSON imagePath and embedded bytes are secondary.
No labels, splits or raw files are modified. Only Pillow and stdlib are required.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import os
import platform
import re
import statistics
import struct
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from functools import lru_cache
from itertools import combinations
from pathlib import Path

import PIL
from PIL import Image, ImageChops, ImageFile, features

from .manifest import ManifestError, iter_sample_candidates, repository_path, sample_metadata

THRESHOLDS = (0, 2, 4, 6, 8)
RESAMPLING = Image.Resampling.LANCZOS
SOURCE_PATTERN = re.compile(r"(?P<family>.+)_frame_(?P<counter>[0-9]+)\.(?:jpg|jpeg|png)")
METHODS = {
    "byte_hash": "SHA-256 of full external image file bytes",
    "pixel_hash": "SHA-256 of struct.pack('>QQ', width, height) followed by row-major "
                  "RGB bytes from Pillow convert('RGB'); no resize, EXIF transpose or ICC transform",
    "dhash": "Pillow convert('L'), resize((9,8), Resampling.LANCZOS); row-major "
             "left > right comparisons; first comparison is bit 63; XOR.bit_count() distance",
    "mae": "Pillow convert('L'), resize((256,256), Resampling.LANCZOS); "
           "sum(abs(a-b))/(256*256*255); no EXIF transpose, alignment or aspect-ratio preservation",
    "source_family": "case-sensitive fullmatch on separator-independent imagePath basename: "
                     + SOURCE_PATTERN.pattern + "; family retains all prefix digits; SHA-256 UTF-8 key; "
                     "unknown=null; candidate only, not an official video ID",
    "input_fingerprint": "SHA-256 of ASCII JSON lines [repo-relative path, full-file SHA-256], "
                         "ensure_ascii=True, default separators, newline after every record. "
                         "Order: train/test, Normal_data/Anomaly_data, sorted points/stems, jpg/json/txt. "
                         "Same as successful validation fingerprint; excludes archives/modalities.",
}


def dhash(image):
    """Return a reproducible 64-bit integer; equal neighbors produce a zero bit."""
    with image.convert("L") as gray, gray.resize((9, 8), RESAMPLING) as small:
        pixels = small.tobytes()
    value = 0
    for y in range(8):
        for x in range(8):
            value = (value << 1) | (pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return value


def pixel_sha256(image):
    with image.convert("RGB") as rgb:
        digest = hashlib.sha256(struct.pack(">QQ", *rgb.size))
        digest.update(rgb.tobytes())
    return digest.hexdigest()


def normalized_mae(a, b):
    """MAE for two already prepared 256x256 grayscale representations."""
    if a.mode != "L" or b.mode != "L" or a.size != (256, 256) or b.size != (256, 256):
        raise ValueError("MAE requires two 256x256 L images")
    with ImageChops.difference(a, b) as difference:
        return sum(value * count for value, count in enumerate(difference.histogram())) / (65536 * 255)


def image_path_metadata(value):
    """Hash the untouched full string; never export upstream absolute paths."""
    if not isinstance(value, str) or not value:
        return {"image_path_sha256": None, "image_path_basename": None, "source_family": None}
    basename = value.replace("\\", "/").split("/")[-1]
    match = SOURCE_PATTERN.fullmatch(basename)
    return {
        "image_path_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        "image_path_basename": basename or None,
        "source_family": hashlib.sha256(match["family"].encode("utf-8")).hexdigest() if match else None,
    }


def embedded_hash(value):
    """Strict decode of one sample, returning no decoded payload."""
    if value is None:
        return None, "absent_or_null"
    if not isinstance(value, str):
        return None, "invalid_type"
    if not value:
        return None, "empty"
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        return None, "invalid_base64"
    return hashlib.sha256(decoded).hexdigest(), "checked"


def sample_key(sample):
    # A repeated stem across splits remains auditable (point leakage), not discarded.
    return sample["sample_id"], sample["image_relpath"]


def pair_record(a, b, mae=None):
    a, b = sorted((a, b), key=sample_key)
    byte_equal = a["byte_sha256"] == b["byte_sha256"]
    pixel_equal = a["pixel_sha256"] == b["pixel_sha256"]
    record = {f"{key}_{side}": sample[key] for side, sample in (("a", a), ("b", b))
              for key in ("sample_id", "image_relpath", "split", "folder_domain", "point_id", "dimensions")}
    record.update(
        same_split=a["split"] == b["split"], same_point=a["point_id"] == b["point_id"],
        same_point_folder=a["point_folder"] == b["point_folder"],
        same_domain=a["folder_domain"] == b["folder_domain"], byte_equal=byte_equal,
        pixel_equal=pixel_equal, dhash_distance=(a["dhash"] ^ b["dhash"]).bit_count(),
        normalized_mae=mae,
        evidence_type=("CONFIRMED_EXACT_BYTE" if byte_equal else
                       "CONFIRMED_PIXEL_EXACT" if pixel_equal else "HIGH_SIMILARITY_CANDIDATE"),
    )
    return record


def pair_counts(pairs):
    counts = Counter({key: 0 for key in (
        "pairs", "within_train_pairs", "within_test_pairs", "cross_split_pairs", "cross_domain_pairs",
        "same_point_pairs", "different_point_pairs", "different_point_cross_split_pairs",
        "same_point_cross_split_pairs", "byte_different_pairs")})
    for p in pairs:
        counts["pairs"] += 1
        counts["within_train_pairs"] += p["same_split"] and p["split_a"] == "train"
        counts["within_test_pairs"] += p["same_split"] and p["split_a"] == "test"
        counts["cross_split_pairs"] += not p["same_split"]
        counts["cross_domain_pairs"] += not p["same_domain"]
        counts["same_point_pairs"] += p["same_point"]
        counts["different_point_pairs"] += not p["same_point"]
        counts["different_point_cross_split_pairs"] += not p["same_point"] and not p["same_split"]
        counts["same_point_cross_split_pairs"] += p["same_point"] and not p["same_split"]
        counts["byte_different_pairs"] += not p["byte_equal"]
    return dict(counts)


def duplicate_groups(samples, key):
    buckets = defaultdict(list)
    for sample in sorted(samples, key=sample_key):
        if sample.get(key) is not None:
            buckets[sample[key]].append(sample)
    groups = []
    for digest, members in sorted(buckets.items()):
        if len(members) < 2:
            continue
        train = sum(s["split"] == "train" for s in members)
        groups.append({"key": digest, "size": len(members),
                       "members": [{"sample_id": s["sample_id"], "image_relpath": s["image_relpath"]}
                                   for s in members],
                       "pair_count": len(members) * (len(members) - 1) // 2,
                       "cross_split_pairs": train * (len(members) - train),
                       "spans_splits": len({s["split"] for s in members}) > 1,
                       "spans_domains": len({s["folder_domain"] for s in members}) > 1,
                       "spans_point_ids": len({s["point_id"] for s in members}) > 1})
    summary = {"unique_hashes": len(buckets), "duplicate_groups": len(groups),
               "duplicate_samples": sum(g["size"] for g in groups),
               "group_size_distribution": dict(sorted(Counter(str(g["size"]) for g in groups).items())),
               "largest_group_size": max((g["size"] for g in groups), default=0),
               "groups_spanning_splits": sum(g["spans_splits"] for g in groups),
               "groups_spanning_domains": sum(g["spans_domains"] for g in groups),
               "groups_spanning_point_ids": sum(g["spans_point_ids"] for g in groups),
               "pairs": sum(g["pair_count"] for g in groups),
               "cross_split_pairs": sum(g["cross_split_pairs"] for g in groups)}
    return summary, groups


def consecutive_pairs(samples):
    """Adjacent 001/002, 002/003, 003/004 in the same actual Normal point folder."""
    points = defaultdict(dict)
    for i, sample in enumerate(samples):
        if sample["data_type"] == "Normal_data":
            points[sample["point_folder"]][sample["instance_id"]] = i
    pairs = []
    for members in points.values():
        for instance in (1, 2, 3):
            if f"{instance:03d}" in members and f"{instance + 1:03d}" in members:
                pairs.append(tuple(sorted((members[f"{instance:03d}"], members[f"{instance + 1:03d}"]))))
    return sorted(pairs)


def distribution(values, *, integer=False):
    values = list(values)
    result = {"count": len(values), "min": min(values) if values else None,
              "median": statistics.median(values) if values else None,
              "mean": statistics.mean(values) if values else None,
              "max": max(values) if values else None}
    if integer:
        result["histogram"] = {str(k): v for k, v in sorted(Counter(values).items())}
    else:
        # Fixed bins [0,.05), ..., [.95,1], no data-dependent thresholds.
        counts = Counter(min(int(v * 20), 19) for v in values)
        result["histogram_0_05_bins"] = [counts[i] for i in range(20)]
    return result


def similarity_summary(pairs):
    return {"pair_count": len(pairs),
            "dhash": distribution((p["dhash_distance"] for p in pairs), integer=True),
            "mae": distribution(p["normalized_mae"] for p in pairs)}


def candidate_indices(samples, max_hamming):
    """Brute-force unordered pairs. Sweep always covers 0/2/4/6/8, independently of pool cutoff."""
    all_hist, cross_hist = Counter(), Counter()
    candidates = []
    for i, a in enumerate(samples):
        for j in range(i + 1, len(samples)):
            b = samples[j]
            distance = (a["dhash"] ^ b["dhash"]).bit_count()
            all_hist[distance] += 1
            if a["split"] != b["split"]:
                cross_hist[distance] += 1
            if distance <= max_hamming:
                candidates.append((i, j))
    sweep = {str(t): {"pairs": sum(n for d, n in all_hist.items() if d <= t),
                      "cross_split_pairs": sum(n for d, n in cross_hist.items() if d <= t)} for t in THRESHOLDS}
    return candidates, sweep


def audit_duplicates(dataset_root, repo_root, *, max_hamming=8, progress=None):
    """Deterministic report body; fail closed if primary evidence cannot be audited.

    Missing/invalid optional imageData is reported explicitly, not silently dropped.
    Runtime and run-specific provenance are attached only by the report writer.
    """
    if type(max_hamming) is not int or not 0 <= max_hamming <= 64:
        raise ManifestError("max_hamming must be an integer in [0, 64]")
    if ImageFile.LOAD_TRUNCATED_IMAGES:
        raise ManifestError("strict image decoding requires LOAD_TRUNCATED_IMAGES=False")
    repo_root = repo_root.resolve()
    dataset_root = repository_path(dataset_root, repo_root)
    fingerprint = hashlib.sha256()
    samples, issues = [], []

    def structural(path, reason):
        raise ManifestError(f"{path.relative_to(repo_root).as_posix()}: {reason}")

    for point, stem, split, kind in iter_sample_candidates(dataset_root, repo_root, structural):
        metadata = sample_metadata(point, stem, split=split, data_type=kind)
        sample = {"sample_id": stem, **metadata, "instance_id": stem[-3:], "split": split,
                  "data_type": kind, "point_folder": point.relative_to(repo_root).as_posix()}
        for ext in ("jpg", "json", "txt"):
            path = repository_path(point / f"{stem}.{ext}", repo_root)
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            relpath = path.relative_to(repo_root).as_posix()
            fingerprint.update(json.dumps([relpath, digest], ensure_ascii=True).encode("ascii") + b"\n")
            if ext == "jpg":
                sample.update(image_relpath=relpath, byte_sha256=digest)
                try:
                    with Image.open(io.BytesIO(raw)) as image:
                        image.load()
                        sample.update(dimensions=list(image.size), pixel_sha256=pixel_sha256(image), dhash=dhash(image))
                except Image.DecompressionBombError as exc:
                    raise ManifestError("external image exceeds Pillow decoding safety limit") from exc
            elif ext == "json":
                sample["json_relpath"] = relpath
                try:
                    annotation = json.loads(raw)
                except (ValueError, UnicodeError, RecursionError) as exc:
                    raise ManifestError("annotation JSON cannot be parsed") from exc
                if not isinstance(annotation, dict):
                    raise ManifestError("annotation JSON must be an object")
                value = annotation.get("imagePath")
                sample["image_path_status"] = ("checked" if isinstance(value, str) and value else
                                               "absent_or_null" if value is None else "invalid_or_empty")
                sample.update(image_path_metadata(value))
                sample["embedded_sha256"], sample["embedded_status"] = embedded_hash(annotation.pop("imageData", None))
                if sample["embedded_status"] != "checked":
                    issues.append({"sample_id": stem, "json_relpath": relpath,
                                   "code": "image_data_" + sample["embedded_status"]})
                del annotation, value
            del raw
        samples.append(sample)
        if progress and len(samples) % 250 == 0:
            progress(f"Fingerprinted {len(samples)} samples")
    if not samples:
        raise ManifestError("no sample candidates found")
    samples.sort(key=sample_key)
    if progress:
        progress(f"Comparing {len(samples) * (len(samples)-1)//2} unordered dHash pairs")
    near_indices, sweep = candidate_indices(samples, max_hamming)
    sequential_indices = consecutive_pairs(samples)
    exact_indices = set()
    group_summaries, groups = {}, {}
    for name, key in (("exact_byte", "byte_sha256"), ("pixel_exact", "pixel_sha256"),
                      ("embedded", "embedded_sha256"), ("image_path", "image_path_sha256"),
                      ("image_path_basename", "image_path_basename"), ("source_family", "source_family")):
        group_summaries[name], groups[name] = duplicate_groups(samples, key)
        if name in ("exact_byte", "pixel_exact"):
            buckets = defaultdict(list)
            for i, sample in enumerate(samples):
                buckets[sample[key]].append(i)
            for bucket in buckets.values():
                exact_indices.update(combinations(bucket, 2))

    # Only 32 small L images (2 MiB) can remain cached; full decoded images close immediately.
    @lru_cache(maxsize=32)
    def comparison(i):
        sample = samples[i]
        path = repository_path(Path(sample["image_relpath"]), repo_root)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != sample["byte_sha256"]:
            raise ManifestError("external image changed during candidate verification")
        with Image.open(io.BytesIO(raw)) as image, image.convert("L") as gray:
            return gray.resize((256, 256), RESAMPLING)

    records = {}
    verify_indices = sorted(set(near_indices) | exact_indices | set(sequential_indices))
    if progress:
        progress(f"Verifying MAE for {len(verify_indices)} pairs; candidate pool={len(near_indices)}")
    try:
        for n, (i, j) in enumerate(verify_indices, 1):
            records[i, j] = pair_record(samples[i], samples[j], normalized_mae(comparison(i), comparison(j)))
            if progress and n % 1000 == 0:
                progress(f"Verified {n}/{len(verify_indices)} pairs")
    finally:
        comparison.cache_clear()
    near = [records[p] for p in near_indices]
    exact = [records[p] for p in sorted(exact_indices)]
    sequential = [records[p] for p in sequential_indices]
    for name, flag in (("exact_byte", "byte_equal"), ("pixel_exact", "pixel_equal")):
        group_summaries[name].update(pair_counts(p for p in exact if p[flag]))
    point_sets = {split: {s["point_id"] for s in samples if s["split"] == split} for split in ("train", "test")}
    folder_sets = {split: {Path(s["point_folder"]).name for s in samples if s["split"] == split}
                   for split in ("train", "test")}
    overlap = sorted(point_sets["train"] & point_sets["test"])
    folder_overlap = sorted(folder_sets["train"] & folder_sets["test"])
    embedded_status = Counter(s["embedded_status"] for s in samples)
    group_summaries["embedded"].update({status: embedded_status[status] for status in
                                      ("checked", "absent_or_null", "empty", "invalid_type", "invalid_base64")})
    group_summaries["embedded"]["bytes_differ_from_external"] = sum(
        s["embedded_sha256"] is not None and s["embedded_sha256"] != s["byte_sha256"] for s in samples)
    metadata_summary = {name: group_summaries[name] for name in ("image_path", "image_path_basename", "source_family")}
    metadata_summary.update(point_id_overlap_count=len(overlap), point_folder_identity_overlap_count=len(folder_overlap),
                            image_path_status=dict(sorted(Counter(s["image_path_status"] for s in samples).items())),
                            source_family_matched_samples=sum(s["source_family"] is not None for s in samples),
                            source_family_unknown_samples=sum(s["source_family"] is None for s in samples))
    near_summary = {"max_hamming": max_hamming, "threshold_sweep": sweep, **pair_counts(near),
                    "nonexact_candidate_pairs": sum(not p["byte_equal"] and not p["pixel_equal"] for p in near),
                    "different_point_same_split": similarity_summary([p for p in near if not p["same_point"] and p["same_split"]]),
                    "different_point_cross_split": similarity_summary([p for p in near if not p["same_point"] and not p["same_split"]])}
    return {
        "report_version": 1, "audit_complete": True, "exit_code": 0,
        "dataset_root": dataset_root.relative_to(repo_root).as_posix(), "max_hamming": max_hamming,
        "input_sha256": fingerprint.hexdigest(), "methods": METHODS,
        "summary": {"dataset": {"total_samples": len(samples),
                                **{split: sum(s["split"] == split for s in samples) for split in ("train", "test")},
                                "unordered_pairs_compared": len(samples) * (len(samples)-1)//2},
                    "exact_byte": group_summaries["exact_byte"], "pixel_exact": group_summaries["pixel_exact"],
                    "near": near_summary, "sequential_reference": similarity_summary(sequential),
                    "metadata": metadata_summary, "embedded": group_summaries["embedded"]},
        "exact_duplicate_groups": groups["exact_byte"], "pixel_duplicate_groups": groups["pixel_exact"],
        "exact_pair_evidence": exact, "near_pair_evidence": near, "sequential_pair_evidence": sequential,
        "metadata_source_evidence": {"evidence_type": "METADATA_SOURCE_CANDIDATE",
                                     "point_id_overlap": overlap, "point_folder_identity_overlap": folder_overlap,
                                     **{name + "_groups": groups[name] for name in
                                        ("image_path", "image_path_basename", "source_family")}},
        "embedded_image_evidence": {"role": "secondary provenance; not canonical external image identity",
                                    "groups": groups["embedded"], "issues": issues},
        "samples": samples,
    }


def checked_output(output, dataset_root, repo_root):
    repo_root = repo_root.resolve()
    output = repository_path(output, repo_root)
    dataset_root = repository_path(dataset_root, repo_root)
    if output.is_relative_to(dataset_root) or output.is_relative_to((repo_root / "data/raw").resolve()):
        raise ManifestError("output must not be inside the raw dataset")
    if output.suffix != ".json":
        raise ManifestError("output must have a .json suffix")
    return output


def write_report(report, output, repo_root, *, runtime_seconds):
    """Atomic local report with portable provenance; no upstream full paths exported."""
    repo_root = repo_root.resolve()
    output = checked_output(output, Path(report["dataset_root"]), repo_root)

    def git(*args):
        try:
            return subprocess.check_output(["git", *args], cwd=repo_root, text=True, encoding="utf-8",
                                           stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    created = datetime.now(timezone.utc)
    sources = ("safeshift/data/duplicates.py", "safeshift/data/manifest.py", "scripts/audit_duplicates.py",
               "requirements-validation.txt", "tests/test_duplicates.py")
    payload = {**report, "run_id": created.strftime("duplicates-%Y%m%dT%H%M%S%fZ"),
               "created_utc": created.isoformat(), "git_commit": git("rev-parse", "HEAD"),
               "git_status": git("status", "--porcelain"), "python": sys.version.split()[0],
               "platform": platform.platform(), "dependencies": {"Pillow": PIL.__version__,
                    "libjpeg": features.version_codec("jpg"), "zlib": features.version_codec("zlib")},
               "runtime_seconds": runtime_seconds,
               "runtime_definition": "audit wall time, excluding report serialization/publication",
               "command": ["python", "scripts/audit_duplicates.py", "--dataset-root", report["dataset_root"],
                           "--output", output.relative_to(repo_root).as_posix(), "--max-hamming", str(report["max_hamming"])],
               "seed": None, "dataset": "InspecSafe-V1", "upstream_release": None, "upstream_url": None,
               "archive_checksums": None, "source": "local extracted dataset; notes/dataset_schema.md",
               "source_sha256": {name: hashlib.sha256((repo_root / name).read_bytes()).hexdigest()
                                 for name in sources if (repo_root / name).is_file()}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=output.parent,
                                         delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=True, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return payload
