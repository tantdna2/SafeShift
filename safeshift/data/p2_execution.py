"""P2 manifest verification and label-free projection. No model dependencies.

The W1 fingerprint has a historical repo-relative namespace. Physical dataset
roots may move, but that namespace and the W1 traversal/serialization do not.
Annotations are hashed as bytes, never decoded for model input.
"""

import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath, PureWindowsPath

from .manifest import FIELDS, DOMAINS, LEVELS, SPLITS, DATA_TYPES
from safeshift.protocol.schema import strict_json

COUNT = 5013
FINGERPRINT = "7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5"
MANIFEST_SHA = "3025edb985d947cbcfe3e397b37aed505e2305b32ece46663d46115c28568577"
NAMESPACE = "data/raw/InspecSafe-V1"
EXECUTION_FIELDS = {"sample_id", "image_locator", "image_sha256"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True,
                       allow_nan=False, separators=(",", ":")) + "\n").encode()


def safe_path(root, locator):
    if type(locator) is not str or not locator or "\\" in locator:
        raise ValueError("UNSAFE_LOCATOR")
    rel = PurePosixPath(locator)
    if (rel.is_absolute() or PureWindowsPath(locator).drive or ":" in locator
            or any(p in ("", ".", "..") for p in locator.split("/"))):
        raise ValueError("UNSAFE_LOCATOR")
    root = Path(root).absolute()
    path = root / locator
    # Reject root aliases as well as descendants (including Windows junctions).
    for node in (root, *root.parents, path, *path.parents):
        if node.is_symlink() or node.resolve() != node:
            raise ValueError("UNSAFE_ALIAS")
    if not path.resolve().is_relative_to(root):
        raise ValueError("UNSAFE_LOCATOR")
    return path


def execution_records(records):
    """Reject injected evaluation fields rather than merely ignore them."""
    rows = tuple(dict(row) for row in records)
    ids = []
    for row in rows:
        if set(row) != EXECUTION_FIELDS:
            raise ValueError("LABEL_FREE_EXECUTION_SCHEMA_REQUIRED")
        if type(row["sample_id"]) is not str or not row["sample_id"]:
            raise ValueError("SAMPLE_ID_REQUIRED")
        digest = row["image_sha256"]
        if type(digest) is not str or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("IMAGE_SHA256_REQUIRED")
        ids.append(row["sample_id"])
    if len(ids) != len(set(ids)):
        raise ValueError("DUPLICATE_SAMPLE_ID")
    return tuple(sorted(rows, key=lambda row: row["sample_id"]))


def verify_dataset(dataset_root, manifest_path, provenance_path):
    """Owner-invoked preflight: verify full source before backend load.

    This API reads dataset bytes; it is never invoked by the current blocked
    production entrypoint or by default tests on a real dataset.
    """
    raw = Path(manifest_path).read_bytes()
    provenance = strict_json(Path(provenance_path).read_bytes())
    if provenance.get("dataset") != "InspecSafe-V1" or provenance.get("input_sha256") != FINGERPRINT:
        raise ValueError("DATASET_FINGERPRINT_MISMATCH")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    if tuple(reader.fieldnames or ()) != FIELDS:
        raise ValueError("DATASET_SCHEMA_MISMATCH")
    rows = list(reader)
    if len(rows) != COUNT:
        raise ValueError("DATASET_COUNT_MISMATCH")
    if len({row["sample_id"] for row in rows}) != len(rows):
        raise ValueError("DUPLICATE_SAMPLE_ID")
    if sha(raw) != MANIFEST_SHA or provenance.get("output_sha256") != sha(raw):
        raise ValueError("SOURCE_MANIFEST_HASH_MISMATCH")
    # Pin original labels/splits/metadata through the exact W1 CSV hash.
    fingerprint = hashlib.sha256()
    projected = []
    seen_paths = set()
    def ordering(row):
        return (SPLITS.index(row["split"]), DATA_TYPES.index(row["data_type"]),
                PurePosixPath(row["image_relpath"]).parent.name, row["sample_id"])
    for row in sorted(rows, key=ordering):
        if (set(row) != set(FIELDS) or row["folder_domain"] not in DOMAINS
                or row["safety_level"] not in LEVELS or not row["point_id"]):
            raise ValueError("DATASET_SCHEMA_MISMATCH")
        image_hash = None
        for key in ("image_relpath", "json_relpath", "txt_relpath"):
            legacy = row[key]
            if not legacy.startswith(NAMESPACE + "/") or legacy in seen_paths:
                raise ValueError("DATASET_LOCATOR_MISMATCH")
            seen_paths.add(legacy)
            local = legacy[len(NAMESPACE) + 1:]
            path = safe_path(dataset_root, local)
            content = path.read_bytes()
            digest = sha(content)
            fingerprint.update(json.dumps([legacy, digest], ensure_ascii=True).encode("ascii") + b"\n")
            if key == "image_relpath":
                image_hash = digest
                image_locator = local
        point = PurePosixPath(image_locator).parent.name
        modality_dir = f'{row["split"]}/DATA_PATH/{row["split"]}/Other_modalities/{point}'
        modality = any(safe_path(dataset_root, f"{modality_dir}/{point}-{suffix}").is_file()
                       for suffix in ("visible.mp4", "infrared.mp4", "sensor.txt", "audio.wav"))
        if strict_json(row["has_other_modalities"]) is not modality:
            raise ValueError("MODALITY_PRESENCE_MISMATCH")
        fingerprint.update(json.dumps([row["sample_id"], modality]).encode("ascii") + b"\n")
        projected.append({"sample_id": row["sample_id"], "image_locator": image_locator,
                          "image_sha256": image_hash})
    if fingerprint.hexdigest() != FINGERPRINT:
        raise ValueError("DATASET_FINGERPRINT_MISMATCH")
    return execution_records(projected), sha(raw)


def shard(records, shard_count, shard_index, source_manifest_sha256):
    rows = execution_records(records)
    if (type(shard_count) is not int or type(shard_index) is not int
            or shard_count < 1 or not 0 <= shard_index < shard_count):
        raise ValueError("INVALID_SHARD")
    selected = rows[shard_index::shard_count]
    manifest = {"shard_algorithm_version": "sample-id-lexical-modulo-v1",
                "shard_count": shard_count, "shard_index": shard_index,
                "ordered_sample_ids": [row["sample_id"] for row in selected],
                "cohort_sample_ids": [row["sample_id"] for row in rows],
                "source_manifest_sha256": source_manifest_sha256}
    return selected, {**manifest, "shard_manifest_sha256": sha(json_bytes(manifest))}
