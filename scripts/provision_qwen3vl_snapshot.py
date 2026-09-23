"""Explicit online provisioning / offline byte verification, never model execution."""

import argparse
import hashlib
import json
from pathlib import Path

MODEL_ID = "Qwen/Qwen3-VL-8B-Instruct"
REVISION = "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b"
PROVENANCE = "configs/pre_freeze/local_model_provenance.d9.json"
ROOT = Path(__file__).resolve().parents[1]


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


def weight_files(repo=ROOT):
    data = json.loads((repo / PROVENANCE).read_text(encoding="utf-8"))
    model = next(m for m in data["models"] if m["model_id"] == MODEL_ID)
    if model["immutable_revision"] != REVISION:
        raise ValueError("PROVENANCE_REVISION_MISMATCH")
    files = model["weight_provenance"]["files"]
    expected = {f"model-{i:05d}-of-00004.safetensors" for i in range(1, 5)}
    if {f["path"] for f in files} != expected or len(files) != 4:
        raise ValueError("EXPECTED_FOUR_SHARDS")
    return files


def verify_weights(snapshot, files):
    """Stream each local shard; a report is returned even for absent/corrupt bytes."""
    observations = []
    for item in files:
        path = Path(snapshot) / item["path"]
        row = {"path": item["path"], "expected_sha256": item["lfs_sha256"],
               "expected_size_bytes": item["size_bytes"], "sha256": None,
               "size_bytes": None, "verified": False}
        try:
            row.update(sha256=sha256_file(path), size_bytes=path.stat().st_size)
            row["verified"] = (row["sha256"] == row["expected_sha256"]
                               and row["size_bytes"] == row["expected_size_bytes"])
        except OSError as exc:
            row["error_type"] = type(exc).__name__
        observations.append(row)
    return {"schema_version": "qwen-local-weight-verification-v1",
            "model_id": MODEL_ID, "revision": REVISION, "files": observations,
            "LOCAL_WEIGHT_BYTES_VERIFIED": len(observations) == 4
            and all(r["verified"] for r in observations)}


def cached_snapshot(cache_dir=None, *, offline=True):
    from huggingface_hub import snapshot_download

    return Path(snapshot_download(repo_id=MODEL_ID, revision=REVISION,
                                  cache_dir=cache_dir, local_files_only=offline))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cache-dir", help="Optional repository-relative HF hub cache")
    parser.add_argument("--report", required=True,
                        help="New repository-relative path under data/processed/")
    args = parser.parse_args()
    # Reuse the storage boundary's path validation, without creating raw artifacts.
    import sys
    sys.path.insert(0, str(ROOT))
    from safeshift.runners.storage import FileRawStore
    output = FileRawStore(ROOT, args.report).root
    if output.exists():
        parser.error("report exists; every attempt requires a new report path")
    cache = None
    if args.cache_dir:
        cache = FileRawStore(ROOT, args.cache_dir).root
    report = {"schema_version": "qwen-local-weight-verification-v1",
              "model_id": MODEL_ID, "revision": REVISION,
              "LOCAL_WEIGHT_BYTES_VERIFIED": False, "files": []}
    try:
        snapshot = cached_snapshot(cache, offline=args.verify_only)
        report = verify_weights(snapshot, weight_files())
    except Exception as exc:
        report["error_type"] = type(exc).__name__
    write_json(output, report)
    print(json.dumps({"LOCAL_WEIGHT_BYTES_VERIFIED": report["LOCAL_WEIGHT_BYTES_VERIFIED"],
                      "report": args.report}))
    return 0 if report["LOCAL_WEIGHT_BYTES_VERIFIED"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
