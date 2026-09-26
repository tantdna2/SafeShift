"""Immutable local bytes and irreversible offline boundary; no model imports."""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
MODEL_ID = "vikhyatk/moondream2"
REVISION = "9a7d4024050840e001defacec2b00727e89149e6"
TOKENIZER_REPO = "moondream/starmie-v1"
TOKENIZER_REVISION = "35192e10a54e36eabe0a7cc57a2c1aab371cafc5"
AUDIT_PATH = "configs/pre_freeze/moondream_prep_audit.v1.json"
AUDIT_SHA256 = "801d68073a7f0359042a46a362baef33a71554cf9337cc4dc48aa6aadfaa588e"
PLAN_PATH = "configs/pre_freeze/moondream_t4_runtime.v1.json"
_offline = False
_owner_lock = threading.Lock()


def json_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_rows(repo_id, revision):
    if (repo_id, revision) not in {(MODEL_ID, REVISION), (TOKENIZER_REPO, TOKENIZER_REVISION)}:
        raise ValueError("IMMUTABLE_IDENTITY_REQUIRED")
    audit = json.loads((ROOT / AUDIT_PATH).read_text(encoding="utf-8"))
    if hashlib.sha256(json_bytes(audit)).hexdigest() != AUDIT_SHA256:
        raise ValueError("PROTECTED_SOURCE_AUDIT_CHANGED")
    return [r for r in audit["artifacts"] if r["repo_id"] == repo_id
            and r["revision"] == revision]


def verify_snapshot(snapshot, repo_id, revision):
    rows = artifact_rows(repo_id, revision)
    path = Path(snapshot).absolute()
    expected_repo = "models--" + repo_id.replace("/", "--")
    if (path.name != revision or path.parent.name != "snapshots"
            or path.parent.parent.name != expected_repo or path.resolve() != path):
        raise ValueError("EXACT_HF_SNAPSHOT_REQUIRED")
    names = {p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()}
    if names != {r["path"] for r in rows}:
        raise ValueError("MISSING_OR_UNREVIEWED_SNAPSHOT_FILE")
    files = []
    for row in rows:
        target = path / row["path"]
        # HF links into this repository's blobs are legitimate; no external alias.
        if not target.resolve().is_relative_to(path.parent.parent):
            raise ValueError("SNAPSHOT_FILE_ESCAPES_CACHE_REPOSITORY")
        if target.stat().st_size != row["size_bytes"] or file_sha256(target) != row["sha256"]:
            raise ValueError("PINNED_ARTIFACT_MISMATCH:" + row["path"])
        files.append({k: row[k] for k in ("path", "sha256", "size_bytes", "verification")})
    manifest = {"schema_version": "moondream-snapshot-v1", "repo_id": repo_id,
                "revision": revision, "files": files, "local_bytes_verified": True,
                "snapshot_directory": expected_repo + "/snapshots/" + revision}
    return {**manifest, "manifest_sha256": hashlib.sha256(json_bytes(manifest)).hexdigest()}


def _deny_network(event, args):
    if (event.startswith("socket.") and event != "socket.__new__"
            or event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec"}):
        raise RuntimeError("NETWORK_OR_CHILD_PROCESS_FORBIDDEN")


def deny_network_permanently():
    """Dedicated process only. Also require venue-level networking disabled.

    Python audit hooks are defense in depth, not an OS firewall for native code.
    The hook intentionally has no undo path or provisioning escape hatch.
    """
    global _offline
    if not _offline:
        for key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"):
            os.environ[key] = "1"
        os.environ["HF_HUB_DISABLE_XET"] = "1"
        sys.addaudithook(_deny_network)
        _offline = True


def require_offline():
    if not _offline or any(os.environ.get(k) != "1" for k in (
            "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY")):
        raise RuntimeError("OFFLINE_BOUNDARY_REQUIRED")


@contextmanager
def exclusive_owner():
    if (threading.current_thread() is not threading.main_thread()
            or threading.active_count() != 1 or not _owner_lock.acquire(blocking=False)):
        raise RuntimeError("CONCURRENT_OR_REENTRANT_USE_FORBIDDEN")
    try:
        yield
    finally:
        _owner_lock.release()
