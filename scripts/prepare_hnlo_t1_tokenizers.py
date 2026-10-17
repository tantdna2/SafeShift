"""Prepare only the pinned tokenizer bytes needed by the three-model HNLO T1.

This is an explicitly online preparation step.  It never requests model weight
paths and refuses common weight/checkpoint suffixes.  The resulting resource
tree belongs under ignored ``data/processed``; only its small manifest may be
copied into Git after review.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from safeshift.ls1.tokenizer import TOKENIZER_FILES, plan
from safeshift.runners.moondream_snapshot import (
    AUDIT_PATH,
    TOKENIZER_REPO,
    TOKENIZER_REVISION,
    artifact_rows,
)

QWEN_REPO = "Qwen/Qwen3-VL-8B-Instruct"
QWEN_REVISION = "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b"
QWEN_FILES = (
    "chat_template.json",
    "config.json",
    "merges.txt",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
)
FORBIDDEN_SUFFIXES = (".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".gguf")
MAX_TOKENIZER_FILE_BYTES = 128 * 1024 * 1024
USER_AGENT = "SafeShift-HNLO-T1-tokenizer-only/1.0"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha1(path):
    path = Path(path)
    size = path.stat().st_size
    digest = hashlib.sha1(("blob " + str(size) + "\0").encode("ascii"))
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(url):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=60) as response:
        length = response.headers.get("Content-Length")
        if length is not None and int(length) > MAX_TOKENIZER_FILE_BYTES:
            raise ValueError("RESOURCE_EXCEEDS_TOKENIZER_ONLY_LIMIT")
        data = response.read(MAX_TOKENIZER_FILE_BYTES + 1)
        if len(data) > MAX_TOKENIZER_FILE_BYTES:
            raise ValueError("RESOURCE_EXCEEDS_TOKENIZER_ONLY_LIMIT")
        return data, response.geturl()


def safe_relative_file(path):
    value = PurePosixPath(path)
    if value.is_absolute() or ".." in value.parts or value.name != path:
        raise ValueError("FLAT_SAFE_RESOURCE_PATH_REQUIRED")
    if value.suffix.lower() in FORBIDDEN_SUFFIXES:
        raise ValueError("MODEL_WEIGHT_DOWNLOAD_FORBIDDEN")
    return value.name


def qwen_inventory(metadata):
    value = json.loads(metadata)
    if value.get("sha") != QWEN_REVISION or value.get("id") != QWEN_REPO:
        raise ValueError("QWEN_IMMUTABLE_REVISION_MISMATCH")
    siblings = {row["rfilename"]: row for row in value.get("siblings", [])}
    if not set(QWEN_FILES) <= siblings.keys():
        raise ValueError("QWEN_TOKENIZER_INVENTORY_INCOMPLETE")
    rows = []
    for name in QWEN_FILES:
        safe_relative_file(name)
        source = siblings[name]
        size = source.get("size")
        if type(size) is not int or not 0 < size <= MAX_TOKENIZER_FILE_BYTES:
            raise ValueError("QWEN_TOKENIZER_SIZE_MISSING_OR_INVALID:" + name)
        lfs = source.get("lfs")
        rows.append({
            "path": name,
            "size_bytes": size,
            "official_hash_algorithm": "sha256" if lfs else "git_blob_sha1",
            "official_hash": (lfs.get("sha256") if lfs else source.get("blobId")),
        })
    if any(not row["official_hash"] for row in rows):
        raise ValueError("QWEN_OFFICIAL_FILE_HASH_MISSING")
    return rows


def resource_url(repo_id, revision, path):
    encoded_repo = "/".join(quote(part, safe="") for part in repo_id.split("/"))
    return f"https://huggingface.co/{encoded_repo}/resolve/{revision}/{quote(path, safe='/')}"


def validate_file(path, expected):
    path = Path(path)
    if not path.is_file() or path.stat().st_size != expected["size_bytes"]:
        return False
    if expected["official_hash_algorithm"] == "sha256":
        return sha256_file(path) == expected["official_hash"]
    if expected["official_hash_algorithm"] == "git_blob_sha1":
        return git_blob_sha1(path) == expected["official_hash"]
    raise ValueError("UNKNOWN_OFFICIAL_HASH_ALGORITHM")


def materialize(snapshot, repo_id, revision, rows):
    snapshot = Path(snapshot)
    if snapshot.name != revision:
        raise ValueError("REVISION_NAMED_SNAPSHOT_REQUIRED")
    snapshot.mkdir(parents=True, exist_ok=True)
    evidence = []
    for expected in rows:
        name = safe_relative_file(expected["path"])
        target = snapshot / name
        url = resource_url(repo_id, revision, name)
        acquisition = "REUSED_LOCAL_VERIFIED_BYTES"
        if not validate_file(target, expected):
            if target.exists():
                raise ValueError("EXISTING_RESOURCE_FAILED_PIN:" + name)
            data, _ = fetch(url)
            if len(data) != expected["size_bytes"]:
                raise ValueError("DOWNLOADED_SIZE_MISMATCH:" + name)
            temporary = target.with_name(target.name + ".part")
            with temporary.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if not validate_file(temporary, expected):
                raise ValueError("DOWNLOADED_HASH_MISMATCH:" + name)
            os.replace(temporary, target)
            acquisition = "DOWNLOADED_EXACT_REVISION"
        evidence.append({
            **expected,
            "sha256": sha256_file(target),
            "git_blob_sha1": git_blob_sha1(target),
            "source_url": url,
            "acquisition": acquisition,
        })
    observed = {item.name for item in snapshot.iterdir() if item.is_file()}
    if observed != {row["path"] for row in rows}:
        raise ValueError("TOKENIZER_SNAPSHOT_INVENTORY_MISMATCH")
    return evidence


def internvl_rows():
    rows = []
    for item in plan("internvl3", ROOT)["snapshot_files"]:
        if item["path"] not in TOKENIZER_FILES:
            continue
        rows.append({
            "path": item["path"],
            "size_bytes": item["size_bytes"],
            "official_hash_algorithm": item["hash_algorithm"],
            "official_hash": item["expected_hash"],
        })
    return rows


def moondream_rows():
    return [{
        "path": row["path"],
        "size_bytes": row["size_bytes"],
        "official_hash_algorithm": "sha256",
        "official_hash": row["sha256"],
    } for row in artifact_rows(TOKENIZER_REPO, TOKENIZER_REVISION)]


def write_json_exclusive(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_root
    if output.is_absolute():
        try:
            output = output.resolve().relative_to(ROOT.resolve())
        except ValueError as exc:
            raise ValueError("OUTPUT_MUST_BE_REPOSITORY_RELATIVE") from exc
    output = ROOT / output
    manifest_path = output / "resource_manifest.json"
    if manifest_path.exists():
        raise FileExistsError("RESOURCE_MANIFEST_ALREADY_EXISTS")

    metadata_url = (
        f"https://huggingface.co/api/models/{QWEN_REPO}/revision/"
        f"{QWEN_REVISION}?blobs=true"
    )
    metadata, _ = fetch(metadata_url)
    metadata_path = output / "metadata" / "qwen3_revision_api.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("xb") as stream:
        stream.write(metadata)
        stream.flush()
        os.fsync(stream.fileno())

    models = []
    specifications = (
        ("qwen3", QWEN_REPO, QWEN_REVISION, qwen_inventory(metadata)),
        ("internvl3", "OpenGVLab/InternVL3-2B-hf",
         "cb57a075cb75a2e6d1b668b128d48bb00ae321d2", internvl_rows()),
        ("moondream2", TOKENIZER_REPO, TOKENIZER_REVISION, moondream_rows()),
    )
    for model_key, repo_id, revision, rows in specifications:
        snapshot = output / "snapshots" / model_key / revision
        files = materialize(snapshot, repo_id, revision, rows)
        models.append({
            "model_key": model_key,
            "repo_id": repo_id,
            "revision": revision,
            "snapshot_directory": f"snapshots/{model_key}/{revision}",
            "files": files,
        })

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    manifest = {
        "schema_version": "safeshift-hnlo-t1-tokenizer-resources-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_git_commit": commit,
        "qwen_metadata": {
            "url": metadata_url,
            "sha256": hashlib.sha256(metadata).hexdigest(),
            "size_bytes": len(metadata),
            "local_path": "metadata/qwen3_revision_api.json",
        },
        "existing_pin_sources": {
            "internvl3": "configs/pre_freeze/internvl3_t4_runtime.v1.json",
            "moondream2": AUDIT_PATH,
        },
        "models": models,
        "weights_downloaded": False,
        "model_inference_used": False,
        "gpu_used": False,
    }
    write_json_exclusive(manifest_path, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
