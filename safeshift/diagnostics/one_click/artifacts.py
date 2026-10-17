"""Exclusive evidence export, including failed and interrupted journals."""

import hashlib
import json
import os
from pathlib import Path
import tarfile


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != data:
        raise OSError("EVIDENCE_REREAD_FAILED")


def package(evidence, output, stem):
    evidence, output = Path(evidence), Path(output)
    files = sorted(p for p in evidence.rglob("*") if p.is_file())
    if any(p.is_symlink() for p in evidence.rglob("*")):
        raise ValueError("EVIDENCE_SYMLINK_FORBIDDEN")
    manifest = {"schema": "hnlo-evidence-inventory-v1", "files": [
        {"path": p.relative_to(evidence).as_posix(), "size_bytes": p.stat().st_size, "sha256": sha256(p)}
        for p in files]}
    write(output / (stem + "_manifest.json"), manifest)
    archive = output / (stem + ".tar.gz")
    with tarfile.open(archive, "x:gz") as stream:
        for path in files:
            stream.add(path, arcname="evidence/" + path.relative_to(evidence).as_posix(), recursive=False)
        stream.add(output / (stem + "_manifest.json"), arcname="manifest.json", recursive=False)
    # Independently hash every member from the actual archive, not its source.
    with tarfile.open(archive, "r:gz") as stream:
        members = stream.getmembers()
        expected = {"evidence/" + r["path"]: r for r in manifest["files"]}
        if {m.name for m in members} != set(expected) | {"manifest.json"}:
            raise ValueError("ARCHIVE_INVENTORY_MISMATCH")
        for member in members:
            if member.name in expected:
                h = hashlib.sha256()
                reader = stream.extractfile(member)
                for block in iter(lambda: reader.read(8 * 1024 * 1024), b""):
                    h.update(block)
                row = expected[member.name]
                if h.hexdigest() != row["sha256"] or member.size != row["size_bytes"]:
                    raise ValueError("ARCHIVE_CHECKSUM_MISMATCH")
    write(output / (stem + "_sha256.json"), {"archive": archive.name, "sha256": sha256(archive),
          "status": "EXPORT_VALID", "verified_evidence_members": len(files),
          "size_bytes": archive.stat().st_size, "manifest_sha256": sha256(output / (stem + "_manifest.json"))})
    return archive


def table(rows):
    text = "| Model | Environment | T1 | Capture | Alignment | Technical HNLO | Result |\n"
    text += "|---|---|---|---|---|---|---|\n"
    for row in rows:
        values = [row.get(k, "NOT_RUN") for k in ("model", "environment", "t1", "capture", "alignment", "technical_hnlo", "result")]
        text += "| " + " | ".join(str(v).replace("|", "/").replace("\n", " ") for v in values) + " |\n"
    return text
