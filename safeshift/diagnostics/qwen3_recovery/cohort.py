"""Exact PR123 suffix, reconstructed from the immutable GT-free shard only."""
import hashlib
from pathlib import Path

from safeshift.pa3.native import train
from safeshift.protocol.schema import strict_json
from ..qwen3_s2_oom import ORIGINAL_SHARD_SHA, canonical_digest, NEW_RUN, NEW_ATTEMPT
from ..hnlo_train.cohort import opaque_rows, validate_opaque

MAPPING_SHA = "dddfc2d0388e97ee43b78b88f0901fc0ffc4047d2b58fd81622c8421b35c9e37"
WORKER_SHA = "b9573ef7fdc38b6b06f0600d157ccd8417084ef15475d7c05e2da050543aa426"


def inference(repo):
    data = (Path(repo) / train.inference_path(2)).read_bytes()
    if hashlib.sha256(data).hexdigest() != ORIGINAL_SHARD_SHA:
        raise ValueError("PR123_ORIGINAL_SHARD_HASH_REQUIRED")
    original = train.validate_inference(strict_json(data), 2)
    rows = original[717:941]
    mapping = [{"recovery_ordinal": i, "original_shard": 2, "original_ordinal": 717 + i,
                "sample_id": r["sample_id"], "image_sha256": r["image_sha256"],
                "prior_status": "TECHNICAL_ERROR" if i == 0 else "NOT_ATTEMPTED"}
               for i, r in enumerate(rows)]
    validate_opaque(opaque_rows(rows), 224)
    if canonical_digest(mapping) != MAPPING_SHA or canonical_digest(opaque_rows(rows)) != WORKER_SHA:
        raise ValueError("EXACT_PR123_MAPPING_AND_ORDER_REQUIRED")
    return rows, mapping


def worker_rows(rows):
    validate_opaque(rows, 224)
    if canonical_digest(rows) != WORKER_SHA:
        raise ValueError("EXACT_PR123_WORKER_HASH_REQUIRED")
    return rows
