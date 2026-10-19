"""Reuse original committed cohort bytes. Never discover or scan dataset files."""
import hashlib
from pathlib import Path

from safeshift.pa3.native import train
from safeshift.protocol.schema import strict_json

FULL_SHA = "a35e91fb431752dbf3b6c161f227d953d5748d69ef9f39aef613019faca33008"
SHARD_SHA = (
    "37b9fae412db374c54b79bbb83aad1d0ba3029d06fe836b71952763550054f70",
    "9482465485f316dbef12116c99239da1f9e868a7075c2c06281148ec0641bc10",
    "f9d2370dd5feece46c91ffe88171cb7cd5e838d3a7818000894b7f71d3829695",
    "d72046fe5265ee8896745584140c322f9fa14a11fdddd8abd40e75270d06e4c8",
)


def inference(repo):
    """No explicit GT fields. IDs/locators STILL encode labels: never send to worker."""
    shards = []
    for i, expected in enumerate(SHARD_SHA):
        payload = (Path(repo) / train.inference_path(i)).read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected:
            raise ValueError("ORIGINAL_SHARD_BYTES_CHANGED")
        shards.append(train.validate_inference(strict_json(payload), i))
    flattened = [r for shard in shards for r in shard]
    if len(flattened) != 3763 or len({r["sample_id"] for r in flattened}) != 3763:
        raise ValueError("EXACT_3763_UNIQUE_IDS_REQUIRED")
    if train.partition(flattened) != shards:
        raise ValueError("ORIGINAL_FOUR_WAY_ORDER_REQUIRED")
    return shards


def metadata(repo):
    """Evaluation only. Caller must first verify raw custody and label authority."""
    return train.load_full(repo, FULL_SHA)


def opaque_rows(rows):
    return [{"ordinal": i, "image_sha256": r["image_sha256"]} for i, r in enumerate(rows)]


def validate_opaque(rows, count):
    if type(rows) is not list or len(rows) != count:
        raise ValueError("EXACT_OPAQUE_WORKER_COUNT_REQUIRED")
    import re
    for i, row in enumerate(rows):
        if (type(row) is not dict or set(row) != {"ordinal", "image_sha256"}
                or type(row["ordinal"]) is not int or row["ordinal"] != i
                or type(row["image_sha256"]) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", row["image_sha256"])):
            raise ValueError("GT_FREE_ORDINAL_HASH_ONLY_REQUIRED")
    return rows
