"""Exclusive, fsynced LS1 artifacts and exact checksum inventory."""

import hashlib
import json
import os
from pathlib import Path

from safeshift.data.p2_execution import safe_path
from safeshift.protocol.schema import strict_json


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                       separators=(",", ":")) + "\n").encode()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_new(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    receipt = {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
    if digest(path) != receipt["sha256"] or path.stat().st_size != len(raw):
        raise ValueError("ARTIFACT_WRITE_INTEGRITY_FAILURE")
    return receipt


def write_json(path, value):
    return write_new(path, json_bytes(value))


def read_verified(path, receipt):
    raw = Path(path).read_bytes()
    if len(raw) != receipt["size_bytes"] or hashlib.sha256(raw).hexdigest() != receipt["sha256"]:
        raise ValueError("ARTIFACT_READ_INTEGRITY_FAILURE")
    return strict_json(raw)


def seal(root):
    root = Path(root)
    files = {p.relative_to(root).as_posix(): {"sha256": digest(p), "size_bytes": p.stat().st_size}
             for p in sorted(root.rglob("*")) if p.is_file()}
    write_json(root / "checksums.json", files)
    verify_run(root)


def verify_run(root):
    root = Path(root)
    inventory = strict_json((root / "checksums.json").read_bytes())
    observed = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if observed != set(inventory) | {"checksums.json"}:
        raise ValueError("ARTIFACT_INVENTORY_MISMATCH")
    for name, receipt in inventory.items():
        path = safe_path(root, name)
        if digest(path) != receipt["sha256"] or path.stat().st_size != receipt["size_bytes"]:
            raise ValueError("ARTIFACT_CHECKSUM_MISMATCH:" + name)
    return inventory
