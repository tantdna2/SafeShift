"""Explicit future provisioning, or network-denied verification of pinned bytes."""

import argparse
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.runners.qwen2_5_vl import MODEL_ID, REVISION
from safeshift.runners.storage import FileRawStore

PLAN = "configs/pre_freeze/qwen2_5_t4_runtime.v1.json"
PLAN_SHA256 = "aa4fcff85d670d844025a540d85f10514919c60f6709de8be8f6be0922fd63fb"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def load_plan(repo=ROOT):
    path = repo / PLAN
    plan = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if hashlib.sha256(canonical).hexdigest() != PLAN_SHA256:
        raise ValueError("QUALIFICATION_PLAN_CHANGED")
    return plan


def block_network(*args, **kwargs):
    raise RuntimeError("NETWORK_FORBIDDEN")


@contextmanager
def network_denied():
    # Python/HF HTTP paths; an external network-disabled container is recommended
    # as defense in depth. No subprocess downloads or native transfer extensions.
    with ExitStack() as stack:
        for name in ("connect", "connect_ex", "sendto", "sendmsg"):
            if hasattr(socket.socket, name):
                stack.enter_context(patch.object(socket.socket, name, block_network))
        for name in ("create_connection", "getaddrinfo"):
            stack.enter_context(patch.object(socket, name, block_network))
        yield


def cached_snapshot(cache_dir=None, *, provision=False):
    from huggingface_hub import snapshot_download
    path = Path(snapshot_download(repo_id=MODEL_ID, revision=REVISION,
                                 cache_dir=cache_dir, local_files_only=not provision,
                                 allow_patterns=[f["path"] for f in load_plan()["snapshot_files"]]))
    # Reject a mutable alias, arbitrary local directory, or different repository.
    if (path.name != REVISION or path.parent.name != "snapshots"
            or path.parent.parent.name != "models--Qwen--Qwen2.5-VL-3B-Instruct"):
        raise ValueError("EXACT_SNAPSHOT_DIRECTORY_REQUIRED")
    return path


def verify_snapshot(snapshot, *, repo=ROOT):
    """Compare every required file against authoritative pinned Hub metadata.

    LFS files use SHA-256. Regular files use the Git blob hash (including header).
    The returned manifest additionally records SHA-256 for every relevant file.
    HF cache file symlinks to blobs are normal; bytes, not link names, are checked.
    """
    snapshot = Path(snapshot)
    if (snapshot.name != REVISION or snapshot.parent.name != "snapshots"
            or snapshot.parent.parent.name != "models--Qwen--Qwen2.5-VL-3B-Instruct"):
        raise ValueError("EXACT_SNAPSHOT_DIRECTORY_REQUIRED")
    plan = load_plan(repo)
    files = []
    for expected in plan["snapshot_files"]:
        path = snapshot / expected["path"]
        size = path.stat().st_size
        sha = hashlib.sha256()
        blob = hashlib.sha1(("blob " + str(size) + "\0").encode("ascii"))
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                sha.update(block)
                blob.update(block)
        actual = sha.hexdigest() if expected["hash_algorithm"] == "sha256" else blob.hexdigest()
        if size != expected["size_bytes"] or actual != expected["expected_hash"]:
            raise ValueError("PINNED_SNAPSHOT_FILE_MISMATCH")
        files.append({**expected, "sha256": sha.hexdigest(), "verified": True})
    actual_names = {p.relative_to(snapshot).as_posix() for p in snapshot.rglob("*") if p.is_file()}
    allowed = {f["path"] for f in files} | {".gitattributes"}
    if actual_names - allowed:
        raise ValueError("UNREVIEWED_SNAPSHOT_FILES")
    return {"schema_version": "qwen2-5-snapshot-manifest-v1", "repo_id": MODEL_ID,
            "revision": REVISION, "snapshot_directory":
            "models--Qwen--Qwen2.5-VL-3B-Instruct/snapshots/" + REVISION,
            "files": files, "total_bytes": sum(f["size_bytes"] for f in files),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "plan_sha256": PLAN_SHA256, "local_bytes_verified": True}


def provision_or_verify(*, provision=False, cache_dir=None):
    if provision:
        return verify_snapshot(cached_snapshot(cache_dir, provision=True))
    with network_denied():
        return verify_snapshot(cached_snapshot(cache_dir, provision=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--provision", action="store_true")
    modes.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cache-dir", help="Repository-relative HF cache under data/processed")
    parser.add_argument("--manifest", required=True, help="New report under data/processed")
    args = parser.parse_args()
    output = FileRawStore(ROOT, args.manifest).root
    if output.exists():
        parser.error("manifest already exists; choose a new path")
    cache = FileRawStore(ROOT, args.cache_dir).root if args.cache_dir else None
    report = provision_or_verify(provision=args.provision, cache_dir=cache)
    write_json(output, report)
    print(json.dumps({"local_bytes_verified": True, "manifest": args.manifest}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
