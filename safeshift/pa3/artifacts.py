"""Exclusive per-file SHA-256 receipts; restricted synthetic storage only."""

import hashlib
import json
import math
import os
from pathlib import Path

from safeshift.protocol.schema import strict_json
from .policy import authorize


def pack(value):
    """Losslessly retain nonfinite mock evidence in standards-compliant JSON."""
    if type(value) is float and not math.isfinite(value):
        return {"nonfinite_float": "nan" if math.isnan(value) else "+inf" if value > 0 else "-inf"}
    if type(value) is dict:
        return {k: pack(v) for k, v in value.items()}
    if type(value) is list:
        return [pack(v) for v in value]
    return value


def unpack(value):
    if type(value) is dict:
        if set(value) == {"nonfinite_float"}:
            return {"nan": math.nan, "+inf": math.inf, "-inf": -math.inf}[value["nonfinite_float"]]
        return {k: unpack(v) for k, v in value.items()}
    if type(value) is list:
        return [unpack(v) for v in value]
    return value


def json_bytes(value):
    return (json.dumps(pack(value), sort_keys=True, allow_nan=False,
                       separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def receipt(data):
    return {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def location(repo, settings, name=None):
    settings = authorize(settings)  # precedes even Path conversion/stat
    allowed = {"manifest", "finish", "failure", "seal"}
    allowed.update(f"{i:03d}.{kind}" for i in range(len(settings["cases"]))
                   for kind in ("attempt", "raw", "result"))
    if name is not None and (type(name) is not str or name not in allowed):
        raise PermissionError("SYNTHETIC_ARTIFACT_NAME_REQUIRED")
    base = Path(repo).absolute()
    root = base / "data" / "processed" / "pa3_synthetic" / settings["run_id"]
    path = root if name is None else root / (name + ".json")
    # Reject symlinks/junctions in ancestors, files and receipt paths before reads.
    for candidate in (path, *path.parents):
        if candidate.resolve() != candidate.absolute():
            raise PermissionError("ARTIFACT_ALIAS_FORBIDDEN")
    if name is not None:
        sidecar = path.with_suffix(".sha256.json")
        if sidecar.resolve() != sidecar.absolute():
            raise PermissionError("ARTIFACT_ALIAS_FORBIDDEN")
    return path


def create(repo, settings):
    root = location(repo, settings)
    root.mkdir(parents=True, exist_ok=False)
    return root


def write(repo, settings, name, value):
    settings = authorize(settings)
    # A direct writer call is not a back door for imported model responses.
    if type(name) is str and name.endswith(".raw"):
        from .scoring import check_raw
        names = {f"{i:03d}.raw": case for i, case in enumerate(settings["cases"])}
        if name not in names:
            raise PermissionError("SYNTHETIC_ARTIFACT_NAME_REQUIRED")
        check_raw(settings, names[name], value)
    path = location(repo, settings, name)
    if path.exists() or path.with_suffix(".sha256.json").exists():
        raise FileExistsError("ARTIFACT_ALREADY_EXISTS:" + name)
    data = json_bytes(value)
    proof = receipt(data)
    for target, payload in ((path, data), (path.with_suffix(".sha256.json"), json_bytes(proof))):
        with target.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    read(repo, settings, name)  # every write is verified by rereading
    return proof


def read(repo, settings, name):
    path = location(repo, settings, name)
    proof = strict_json(path.with_suffix(".sha256.json").read_bytes())
    data = path.read_bytes()
    if receipt(data) != proof:
        raise ValueError("PA3_ARTIFACT_CHECKSUM_MISMATCH:" + name)
    return unpack(strict_json(data))


def exists(repo, settings, name):
    path = location(repo, settings, name)
    present = path.exists(), path.with_suffix(".sha256.json").exists()
    if present[0] != present[1]:
        raise ValueError("TORN_ARTIFACT_WRITE:" + name)
    return present[0]


def inventory(repo, settings):
    root = location(repo, settings)
    result = {}
    for path in sorted(root.iterdir()):
        if path.name.endswith(".sha256.json"):
            continue
        if not path.name.endswith(".json"):
            raise ValueError("UNEXPECTED_ARTIFACT")
        name = path.name[:-5]
        if name == "seal":
            continue
        read(repo, settings, name)
        result[name] = receipt(location(repo, settings, name).read_bytes())
    expected = {n + ext for n in result for ext in (".json", ".sha256.json")}
    if exists(repo, settings, "seal"):
        expected |= {"seal.json", "seal.sha256.json"}
    if {p.name for p in root.iterdir()} != expected:
        raise ValueError("PA3_ARTIFACT_INVENTORY_MISMATCH")
    return result


def seal(repo, settings):
    write(repo, settings, "seal", inventory(repo, settings))


def verify(repo, settings):
    observed = inventory(repo, settings)
    sealed = exists(repo, settings, "seal")
    if sealed and read(repo, settings, "seal") != observed:
        raise ValueError("PA3_SEAL_MISMATCH")
    return sealed
