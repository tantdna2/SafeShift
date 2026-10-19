"""Read only the committed inference manifest; never open a GT/full manifest."""
import hashlib
from pathlib import Path
import re

from safeshift.pa3.native import train
from safeshift.protocol.schema import strict_json

IMAGE_SHA256 = ('f26d35fdeea4bedda3ef97cb63160449b09ec1f8b48dacf3086b3a94a7f2b3e7', '6e11b76c677a22c9f57606a868f3f267cf4b5a0484b611482d6efe47c52b2e0b', '38fa44c867db861b4381b39ed951946d2f18b8389a2626afc4379c5dfbb08c9a', 'c8be484848b7b9f9d508b47c5e47dd67e5c10621cd20437bc2e742190511b480', '391d134679efcdd7c6aaf7fac68a51edbc484bb92e5c1ed6852edd5609f84a5e', 'c6491aa355aa889e6a6f4be270ce56bf2a6f99898094dea976bd123cf88c7627', '55f9a26c66fe0721e2181a5a33a2c59d745dcfab58879ca3e9f9e953b9fb2e23', '94dca0c6fca0023241e40aa9d4f7c46917ae834fc31ed83cc644944e8e6e0844')

SHARD_SHA = "37b9fae412db374c54b79bbb83aad1d0ba3029d06fe836b71952763550054f70"


def planned(repo):
    data = (Path(repo) / train.inference_path(0)).read_bytes()
    if hashlib.sha256(data).hexdigest() != SHARD_SHA:
        raise ValueError("ORIGINAL_SHARD0_BYTES_CHANGED")
    rows = train.validate_inference(strict_json(data), 0)
    if len(rows) != 941:
        raise ValueError("ORIGINAL_941_SHARD_REQUIRED")
    if tuple(r["image_sha256"] for r in rows[:8]) != IMAGE_SHA256:
        raise ValueError("PILOT_IMAGE_HASHES_CHANGED")
    return rows[:8]


def opaque_rows(rows):
    return [{"ordinal": i, "image_sha256": r["image_sha256"]} for i, r in enumerate(rows)]


def validate_opaque(rows, count=8):
    if type(rows) is not list or len(rows) != count:
        raise ValueError("EXACT_PILOT_COUNT_REQUIRED")
    for i, r in enumerate(rows):
        if (type(r) is not dict or set(r) != {"ordinal", "image_sha256"}
                or type(r["ordinal"]) is not int or r["ordinal"] != i
                or not isinstance(r["image_sha256"], str) or not re.fullmatch("[0-9a-f]{64}", r["image_sha256"])):
            raise ValueError("ORDINAL_HASH_ONLY_REQUIRED")
    if tuple(r["image_sha256"] for r in rows) != IMAGE_SHA256:
        raise ValueError("EXACT_LOCKED_EIGHT_IMAGES_REQUIRED")
    return rows
