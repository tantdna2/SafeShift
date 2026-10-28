"""Optional authorized original-V4 saved-label exporter, never Recovery224.

Reuse current main's source-verification functions from PR131, without running
its full sensitivity analysis, raw replay, images or historical inference code.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from safeshift.pilot.artifacts import read, relative, sha, write
from safeshift.pilot.contract import LEGACY, MASTER_PATH, MASTER_SHA
from safeshift.pilot.manifest import validate_master
from scripts.analyze_source_sensitivity import (RECEIPT, checked_bytes, original_s2_zip,
                                               verify_v4_cohort, verify_v4_shard)


def metadata_from_master(master):
    return {r["sample_id"]: {"sample_id": r["sample_id"], "safety_level": r["level"], "split": "train",
                            "folder_domain": r["domain"], "byte_sha256": r["image_sha256"]} for r in master}


def export_labels(grant_path, directory, s2_zip, output):
    grant = read(grant_path)
    if (grant.get("schema") != "safeshift-qwen-export-grant-v1"
            or not grant.get("owner_approval_ref") or grant.get("allow_original_v4_saved_artifacts") is not True):
        raise PermissionError("BLOCKED_QWEN_ARTIFACT_READ_GRANT_REQUIRED")
    for path in (directory, s2_zip, output):
        relative(path)
        if not path.startswith("data/processed/"):
            raise ValueError("PROCESSED_RELATIVE_PATHS_REQUIRED")
    def historical(path):
        return subprocess.check_output(["git", "show", f"{LEGACY}:{path}"])
    payload = historical(MASTER_PATH)
    if hashlib.sha256(payload).hexdigest() != MASTER_SHA:
        raise ValueError("MASTER_HASH")
    master = validate_master(json.loads(payload))
    metadata = metadata_from_master(master)
    receipt = json.loads(historical(RECEIPT))
    hashes = receipt["available_export_checks"]["inputs_sha256"]
    scope = json.loads(historical("configs/diagnostics/hnlo_train_authority.v4.json"))["scope"]
    units = {r["shard"]: r for r in scope["units"] if r["model"] == "qwen3"}
    shards = {}
    for shard in (0, 1, 2, 3):
        raw_inference = historical(f"data/manifests/pa3_full_train_shard{shard}.v1.json")
        if hashlib.sha256(raw_inference).hexdigest() != units[shard]["inference_sha256"]:
            raise ValueError("ORIGINAL_SHARD_HASH")
        inference = json.loads(raw_inference)["samples"]
        if shard == 2:
            # Requires the exact original S2 archive and all original sidecars.
            if grant.get("s2_zip_sha256") != sha(s2_zip):
                raise PermissionError("EXACT_S2_ZIP_GRANT_HASH")
            archive, result, _ = original_s2_zip(Path(s2_zip).read_bytes())
        else:
            name = f"qwen3_shard{shard}.json"
            result = json.loads(checked_bytes(Path(directory) / name, hashes[name]))
            name = result["export"]["archive"]
            relative(name)
            if "/" in name:
                raise ValueError("ORIGINAL_ARCHIVE_BASENAME_REQUIRED")
            archive = checked_bytes(Path(directory) / name, result["export"]["archive_sha256"])
        shards[shard] = verify_v4_shard(archive, result, units[shard], inference, scope, metadata)
    success, verification = verify_v4_cohort(shards, metadata)
    by_id = {r["sample_id"]: r for r in master}
    source_by_id = {r["sample_id"]: proof["archive_sha256"] for rows, proof in shards.values() for r in rows}
    rows = [{"sample_id": r["sample_id"], "ground_truth": r["true_level"], "predicted_label": r["generated_label"],
             "image_sha256": by_id[r["sample_id"]]["image_sha256"], "status": "SUCCESS", "cohort": "QWEN3_V4_ORIGINAL",
             "verified": True, "verification_ref": "PR131 saved-score verifier; receipt embedded in this export",
             "source_artifact_sha256": source_by_id[r["sample_id"]]} for r in success]
    write(output, {"schema": "safeshift-original-v4-labels-v1", "samples": rows, "verification": verification,
                   "artifact_read_approval_ref": grant["owner_approval_ref"]})


def main():
    p = argparse.ArgumentParser()
    for name in ("grant", "input-dir", "original-s2-zip", "output"):
        p.add_argument("--" + name, required=True)
    a = p.parse_args()
    export_labels(a.grant, a.input_dir, a.original_s2_zip, a.output)


if __name__ == "__main__":
    main()
