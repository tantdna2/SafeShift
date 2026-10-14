"""Separate PA3-R2 authority and content-addressed full TRAIN manifest.

Existing TRAIN metadata is reused byte-for-byte; no dataset access or new split.
"""
import hashlib
from pathlib import Path
from safeshift.protocol.schema import strict_json
from safeshift.pa3.artifacts import json_bytes
from . import train, access, preflight
from .journal import run_path, no_alias
from .merger_clamp import POLICY

BASE = "486b4af7ad1f402395b60b0c36ebfd80a74cf4de"
AUTHORITY = "configs/pa3/r2_authority.v1.json"
FULL = "data/manifests/pa3_r2_full_train.v1.json"
MODE = "full-train-r2"
DECISION = "DEC-PA3-010"
COUNT, SIZES, SEED = train.COUNT, train.SIZES, train.SEED
HASHES = train.HASHES
SCOPE = {**train.SCOPE, "mode": MODE, "experiment": "PA3-R2", "clamp": POLICY,
         "max_new_tokens": 32}


def run_id(shard):
    train.run_id(shard)  # exact integer/range validation
    return f"pa3-qwen-r2-train-shard-{shard}"


def authority(repo, source_commit):
    import sys
    # Full committed-byte/source verification remains in launch, workflow and
    # QwenRawScorer before model/image access, as in the original TRAIN path.
    return train.authority(repo, source_commit, protocol=sys.modules[__name__])


def require(settings, repo):
    import sys
    return train.require(settings, repo, protocol=sys.modules[__name__])


def manifest(repo, expected):
    data = (Path(repo) / FULL).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("R2_MANIFEST_CHECKSUM")
    value = strict_json(data)
    if (value["schema"] != "pa3-r2-full-train-v1" or value["experiment"] != "PA3-R2"
            or value["clamp"] != POLICY or value["count"] != COUNT
            or value["execution_authority"] is not False or len(value["shards"]) != 4):
        raise ValueError("R2_MANIFEST_SCHEMA")
    if value["original_full"]["path"] != train.FULL:
        raise ValueError("R2_ORIGINAL_MANIFEST_PATH")
    return value


def inference_payload(repo, value, shard):
    entry = value["shards"][shard]
    if (entry["shard_id"] != shard or entry["run_id"] != run_id(shard)
            or entry["count"] != SIZES[shard] or entry["original_path"] != train.inference_path(shard)):
        raise ValueError("R2_SHARD_IDENTITY")
    payload = (Path(repo) / entry["original_path"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != entry["original_sha256"]:
        raise ValueError("R2_ORIGINAL_SHARD_CHECKSUM")
    original = strict_json(payload)
    train.validate_inference(original, shard)
    projected = {**original, "schema": "pa3-r2-train-inference-v1", "run_id": run_id(shard),
                 "experiment": "PA3-R2", "clamp": POLICY}
    if hashlib.sha256(json_bytes(projected)).hexdigest() != entry["inference_manifest_sha256"]:
        raise ValueError("R2_PROJECTED_SHARD_CHECKSUM")
    return projected


def inference_samples(repo, settings):
    require(settings, repo)  # deny before any manifest or data read
    value = manifest(repo, settings["full_manifest_sha256"])
    payload = inference_payload(repo, value, settings["shard_id"])
    if hashlib.sha256(json_bytes(payload)).hexdigest() != settings["inference_manifest_sha256"]:
        raise ValueError("R2_APPROVED_SHARD_CHECKSUM")
    return payload["samples"]


def load_full(repo, expected):
    value = manifest(repo, expected)
    metadata = train.load_full(repo, value["original_full"]["sha256"])
    for i in range(4):
        inference_payload(repo, value, i)
    return metadata


def preflight_dataset(repo, settings, inputs):
    from safeshift.data.p2_execution import safe_path
    from safeshift.ls1.artifacts import digest
    rows = inference_samples(repo, settings)
    root = train.seminar.dataset_root(settings, inputs)
    for row in rows:
        if digest(safe_path(root, row["image_locator"])) != row["image_sha256"]:
            raise ValueError("R2_TRAIN_IMAGE_CHECKSUM:" + row["sample_id"])
    return {"planned": len(rows), "verified": len(rows), "decoded": False, "samples": rows}


def open_image(repo, settings, row, inputs):
    from safeshift.ls1.experiment import open_sample
    if row not in inference_samples(repo, settings):
        raise PermissionError("IMAGE_OUTSIDE_R2_TRAIN_SHARD")
    return open_sample(row, train.seminar.dataset_root(settings, inputs))


def verify_prior(repo, settings, inputs, tokenizer):
    require(settings, repo)
    return train.verify_prior(repo, settings, inputs, tokenizer, require_gate=require)


def image_ticket(repo, settings, image, journal, prefix):
    rows = inference_samples(repo, settings)
    if journal.root != run_path(repo, settings["run_id"]):
        raise PermissionError("EXACT_R2_JOURNAL_REQUIRED")
    index = next((i for i in range(len(rows)) if prefix == f"sample-{i:06d}"), None)
    if index is None or journal.read(prefix + ".attempt") != rows[index]:
        raise PermissionError("R2_SAMPLE_IDENTITY")
    with open_image(repo, settings, rows[index], settings["train_inputs_root"]) as expected:
        if (image.mode, image.size, image.tobytes()) != (expected.mode, expected.size, expected.tobytes()):
            raise PermissionError("R2_IMAGE_PIXELS")
    tickets = no_alias(journal.root.parent / (journal.root.name + "-tickets"))
    tickets.mkdir(exist_ok=True)
    with (tickets / (prefix + ".ticket")).open("xb") as stream:
        stream.write(rows[index]["image_sha256"].encode())
