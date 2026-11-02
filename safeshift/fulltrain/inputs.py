"""Exact full-cohort projection and bounded attached Input admission.

These pure checks confer no rights. Public notebook/worker entrypoints are
fenced before calling real Input admission in this preparation release.
"""
from pathlib import Path

from safeshift.candidates import fulltrain as f
from safeshift.candidates.source import require, snapshot_stat
from safeshift.candidates.train_inputs import discover
from safeshift.pilot.artifacts import read, safe, sha
from safeshift.pilot.contract import digest, require_hash

MARKER = "fresh_fulltrain_input.json"


def project_master(master_bytes, expected_projection):
    result = f.cohort(master_bytes)  # SHA256 BEFORE parse; original order, no GT output
    require(digest(result) == expected_projection, "CUSTODIAN_PROJECTION_MISMATCH")
    return result


def validate_mapping(cohort, rows):
    expected = f.validate_cohort(cohort, digest(cohort))
    require(type(rows) is list and len(rows) == f.COUNT, "FULL_IMAGE_MAPPING_REQUIRED")
    for original, row in zip(expected, rows):
        require(type(row) is dict and set(row) == {*original, "image", "width", "height"}, "IMAGE_MAPPING_FIELDS_NO_GT")
        require(all(row[n] == value for n, value in original.items()), "IMAGE_ORDER_ID_SHA_MISMATCH")
        require(row["image"] == f"images/{original['ordinal']:06d}.jpg", "OPAQUE_IMAGE_PATH_REQUIRED")
        require(all(type(row[n]) is int and row[n] > 0 for n in ("width", "height")), "IMAGE_DIMENSIONS")
    return rows


def admit(inputs, expected_marker_sha256, expected_projection_sha256):
    """Future authorized admission only; no recursive discovery or weight load."""
    require_hash(expected_marker_sha256)
    marker = discover(Path(inputs), MARKER)
    snapshot_stat(marker)
    require(marker.stat().st_size <= 16384 and sha(marker) == expected_marker_sha256, "INPUT_MARKER_PIN")
    value = read(marker)
    require(set(value) == {"schema", "master_sha256", "projection_sha256", "mapping_sha256"}
            and value["schema"] == "safeshift-fresh-input-v1", "FRESH_INPUT_MARKER")
    require(value["master_sha256"] == f.MASTER_SHA
            and value["projection_sha256"] == expected_projection_sha256, "ORIGINAL_INPUT_PIN")
    root = marker.parent
    master = safe(root, "original_train_master.json")
    require(master.stat().st_size <= 16 * 2**20, "MASTER_SIZE_BOUND")
    c = project_master(master.read_bytes(), expected_projection_sha256)
    mapping = safe(root, "image_mapping.json")
    require(mapping.stat().st_size <= 4 * 2**20 and sha(mapping) == value["mapping_sha256"], "MAPPING_PIN")
    rows = validate_mapping(c, read(mapping))
    return root, c, rows


def verify_image_bytes(root, cohort, rows):
    """Checksum every planned file before reservation; decode belongs to child."""
    validate_mapping(cohort, rows)
    for row in rows:
        path = safe(root, row["image"])
        require(sha(path) == row["image_sha256"], "IMAGE_BYTES_CHANGED")
    return {"verified_images": f.COUNT, "decode": "NOT_RUN"}
