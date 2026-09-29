"""Exact snapshot bytes and runtime network boundary; no implicit provisioning."""

from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
from unittest.mock import patch

from .storage import FileRawStore

ROOT = Path(__file__).resolve().parents[2]
MODEL_ID = "google/paligemma-3b-mix-448"
REVISION = "ead2d9a35598cb89119af004f5d023b311d1c4a1"
PLAN = "configs/pre_freeze/paligemma_t4_runtime.v1.json"
PLAN_SHA256 = "4138071ff3fcbcf2cb16d456c01a2b3dbc42a628b0faa0d04dd6a635803b0ab7"
CACHE = "data/processed/paligemma_hf_cache"
REPOSITORY = "models--google--paligemma-3b-mix-448"
OFFLINE_ENV = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
               "HF_HUB_DISABLE_TELEMETRY": "1", "HF_HUB_ENABLE_HF_TRANSFER": "0",
               "HF_HUB_DISABLE_XET": "1"}


def json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(json_bytes(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def load_plan(repo=ROOT):
    plan = json.loads((Path(repo) / PLAN).read_text(encoding="utf-8"))
    if hashlib.sha256(json_bytes(plan)).hexdigest() != PLAN_SHA256:
        raise ValueError("QUALIFICATION_PLAN_CHANGED")
    if (plan["model_id"], plan["model_revision"]) != (MODEL_ID, REVISION):
        raise ValueError("EXACT_IDENTITY_REQUIRED")
    return plan


def block_network(*args, **kwargs):
    raise RuntimeError("NETWORK_FORBIDDEN")


@contextmanager
def network_denied():
    # Python socket/HF denial; venue Internet OFF remains a separate requirement.
    with ExitStack() as stack:
        for name in ("connect", "connect_ex", "sendto", "sendmsg"):
            if hasattr(socket.socket, name):
                stack.enter_context(patch.object(socket.socket, name, block_network))
        for name in ("create_connection", "getaddrinfo"):
            stack.enter_context(patch.object(socket, name, block_network))
        yield


def require_offline_env():
    if any(os.environ.get(k) != v for k, v in OFFLINE_ENV.items()):
        raise ValueError("SET_OFFLINE_ENV_BEFORE_PROCESS_START")


def snapshot_path(repo=ROOT, cache_dir=CACHE):
    cache = FileRawStore(Path(repo), cache_dir).root
    return cache / REPOSITORY / "snapshots" / REVISION


def verify_snapshot(snapshot, *, repo=ROOT):
    """Rehash every allowed byte against the immutable Hub inventory, offline."""
    snapshot = Path(snapshot)
    if (snapshot.name != REVISION or snapshot.parent.name != "snapshots"
            or snapshot.parent.parent.name != REPOSITORY or not snapshot.is_dir()):
        raise ValueError("EXACT_SNAPSHOT_DIRECTORY_REQUIRED")
    if snapshot.resolve() != snapshot.absolute():
        raise ValueError("SNAPSHOT_DIRECTORY_ALIAS_FORBIDDEN")
    plan = load_plan(repo)
    expected_names = {f["path"] for f in plan["snapshot_files"]}
    observed = {p.relative_to(snapshot).as_posix() for p in snapshot.rglob("*")}
    if observed != expected_names:
        raise ValueError("SNAPSHOT_INVENTORY_MISMATCH")
    files = []
    for expected in plan["snapshot_files"]:
        path = snapshot / expected["path"]
        resolved = path.resolve()
        if not (resolved.is_relative_to(snapshot)
                or resolved.is_relative_to(snapshot.parent.parent / "blobs")):
            raise ValueError("SNAPSHOT_FILE_ESCAPES_CACHE")
        size = path.stat().st_size
        sha = hashlib.sha256()
        blob = hashlib.sha1(("blob " + str(size) + "\0").encode("ascii"))
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                sha.update(block)
                blob.update(block)
        actual = sha.hexdigest() if expected["hash_algorithm"] == "sha256" else blob.hexdigest()
        if size != expected["size_bytes"] or actual != expected["expected_hash"]:
            raise ValueError("PINNED_SNAPSHOT_FILE_MISMATCH: " + expected["path"])
        files.append({**expected, "sha256": sha.hexdigest()})
    return {"model_id": MODEL_ID, "revision": REVISION, "plan_sha256": PLAN_SHA256,
            "files": files, "local_bytes_verified": True,
            "snapshot_directory": REPOSITORY + "/snapshots/" + REVISION,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()}


def provision_or_verify(*, provision=False, repo=ROOT, cache_dir=CACHE):
    snapshot = snapshot_path(repo, cache_dir)
    cache = FileRawStore(Path(repo), cache_dir).root
    if not provision:
        with network_denied():
            return verify_snapshot(snapshot, repo=repo)
    # Refuse even an interrupted provision. User must select a fresh cache.
    if cache.exists() and any(cache.iterdir()):
        raise ValueError("CACHE_NOT_EMPTY_NO_REPAIR_OR_OVERWRITE")
    from huggingface_hub import snapshot_download
    downloaded = Path(snapshot_download(
        repo_id=MODEL_ID, revision=REVISION, cache_dir=str(cache),
        allow_patterns=[f["path"] for f in load_plan(repo)["snapshot_files"]],
        local_files_only=False,
    ))
    if downloaded.absolute() != snapshot.absolute():
        raise ValueError("DOWNLOADER_RETURNED_WRONG_SNAPSHOT")
    with network_denied():
        return verify_snapshot(snapshot, repo=repo)
