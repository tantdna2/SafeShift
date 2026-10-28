"""Exclusive durable writes, bounded archive verification and immutable resume."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import zipfile

from .contract import json_bytes


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def relative(name):
    if (not isinstance(name, str) or not name or "\\" in name or ":" in name
            or name.startswith("/") or any(p in ("", ".", "..") for p in name.split("/"))):
        raise ValueError("SAFE_RELATIVE_PATH_REQUIRED")
    return PurePosixPath(name)


def safe(root, name):
    relative(name)
    root = Path(root).absolute()
    p = root
    if root.is_symlink():
        raise ValueError("SYMLINK_ROOT")
    for part in name.split("/"):
        p = p / part
        if p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction()):
            raise ValueError("PATH_ALIAS")
    if not p.resolve().is_relative_to(root.resolve()):
        raise ValueError("PATH_ESCAPE")
    if p.is_file() and (p.stat().st_nlink != 1 or not stat.S_ISREG(p.stat().st_mode)):
        raise ValueError("NONREGULAR_OR_HARDLINK")
    return p


def write(path, value):
    payload = json_bytes(value)
    return write_bytes(path, payload)


def write_bytes(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(payload).hexdigest()


def read(path):
    def pairs(items):
        obj = {}
        for k, v in items:
            if k in obj:
                raise ValueError("DUPLICATE_JSON_KEY")
            obj[k] = v
        return obj
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))


def export(root, archive, log_limit=8 * 2**20):
    """Includes partial files. No images, weights or runtime in the evidence root."""
    root, archive = Path(root), Path(archive)
    paths = [p for p in root.rglob("*") if p.is_file()]
    if (root / "checksums.json").exists():
        raise FileExistsError("EVIDENCE_ALREADY_SEALED")
    members, bounded = {}, {}
    for p in paths:
        name = p.relative_to(root).as_posix()
        if p.suffix == ".log" and p.stat().st_size > log_limit:
            # Never truncate/overwrite the original evidence. Export a bounded
            # tail under a DISTINCT name with custody of the complete log hash.
            tail = p.with_name(p.name + ".tail.txt")
            with p.open("rb") as stream:
                stream.seek(-log_limit, os.SEEK_END)
                payload = stream.read(log_limit)
            tail_hash = write_bytes(tail, payload)
            bounded[name] = {"original_sha256": sha(p), "original_bytes": p.stat().st_size,
                             "exported_path": tail.relative_to(root).as_posix(),
                             "exported_sha256": tail_hash, "exported_bytes": len(payload),
                             "coverage": "TAIL_ONLY_FULL_LOG_RETAINED_IN_DIRECTORY"}
            members[tail.relative_to(root).as_posix()] = tail_hash
        else:
            members[name] = sha(p)
    if bounded:
        members["log_exports.json"] = write(root / "log_exports.json", bounded)
    if "checksums.json" in members:
        raise FileExistsError("EVIDENCE_ALREADY_SEALED")
    write(root / "checksums.json", members)
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for name in sorted([*members, "checksums.json"]):
            z.write(safe(root, name), name)
    verify_archive(archive)
    write(Path(str(archive) + ".sha256.json"), {"sha256": sha(archive), "members": len(members) + 1})
    return sha(archive)


def verify_archive(archive):
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        if (len(infos) > 1000000 or sum(i.file_size for i in infos) > 8 * 2**30
                or any(i.file_size > 64 * 2**20 for i in infos)):
            raise ValueError("ARCHIVE_LIMIT")
        names = [i.filename for i in infos]
        if len(names) != len(set(names)):
            raise ValueError("ARCHIVE_DUPLICATE")
        for i in infos:
            relative(i.filename)
            if i.is_dir() or stat.S_ISLNK(i.external_attr >> 16):
                raise ValueError("ARCHIVE_NONREGULAR")
        if "checksums.json" not in names:
            raise ValueError("ARCHIVE_CHECKSUM_MANIFEST_MISSING")
        hashes = json.loads(z.read("checksums.json"))
        if set(names) != {*hashes, "checksums.json"}:
            raise ValueError("ARCHIVE_MEMBERSHIP")
        for name, expected in hashes.items():
            if hashlib.sha256(z.read(name)).hexdigest() != expected:
                raise ValueError("ARCHIVE_CHECKSUM:" + name)
    return hashes


def import_archive(archive, destination):
    hashes = verify_archive(archive)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        for name in hashes:
            write_bytes(safe(destination, name), z.read(name))
    return destination


class Store:
    def __init__(self, root, identity, parent=None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        self.identity = identity
        self.parent = Path(parent) if parent else None
        if self.parent and read(self.parent / "identity.json") != identity:
            raise ValueError("RESUME_MODEL_CONFIG_INPUT_IDENTITY_MISMATCH")
        write(self.root / "identity.json", identity)

    def previous(self, ordinal):
        if not self.parent:
            return None
        prefix = f"samples/{ordinal:06d}/"
        path = self.parent / prefix / "result.json"
        if path.exists():
            result = read(path)
            raw_path = self.parent / prefix / "raw.json"
            if result.get("status") == "SUCCESS" and not result.get("raw_sha256"):
                raise ValueError("RESUME_SUCCESS_REQUIRES_RAW")
            if result.get("raw_sha256") and sha(raw_path) != result["raw_sha256"]:
                raise ValueError("RESUME_RAW_BINDING")
            return result
        if (self.parent / prefix / "started.json").exists():
            start = read(self.parent / prefix / "started.json")
            return {"status": "TECHNICAL_ERROR", "reason": "INTERRUPTED_ATTEMPT_CONSUMED", "attempts": start["attempts"],
                    "native_calls": start.get("prior_native_calls", 0) + int((self.parent / prefix / "native_call.json").exists())}
        return None

    def retain(self, ordinal):
        prefix = f"samples/{ordinal:06d}"
        for p in (self.parent / prefix).rglob("*"):
            if p.is_file():
                write_bytes(self.root / p.relative_to(self.parent), p.read_bytes())

    def start(self, ordinal, record):
        write(self.root / f"samples/{ordinal:06d}/started.json", record)

    def raw(self, ordinal, record):
        return write(self.root / f"samples/{ordinal:06d}/raw.json", record)

    def result(self, ordinal, record):
        write(self.root / f"samples/{ordinal:06d}/result.json", record)
