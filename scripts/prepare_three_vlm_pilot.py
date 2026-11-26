"""Authorized CPU-only input preparation. No grant is created by this command.

Reads original TRAIN JPEGs only after a separate preparation grant; never TEST.
Derived private bundle stays under data/processed, never commit/upload publicly.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from collections import Counter
import uuid

from safeshift.pilot.artifacts import read, relative, safe, sha, write, write_bytes
from safeshift.pilot.contract import DATA_REVISION, LEGACY, MASTER_PATH, MASTER_SHA, SEED, digest
from safeshift.pilot.manifest import select_main, select_supplement, validate_master, validate_plan


def processed(value):
    relative(value)
    if not value.startswith("data/processed/"):
        raise ValueError("DERIVED_OUTPUT_UNDER_DATA_PROCESSED_REQUIRED")
    return safe(Path.cwd(), value)


def prepare(grant_path, dataset_root, output, qwen_path=None, mode="PILOT"):
    # This reads only a grant before any master, folder GT, image or Qwen artifact.
    grant = read(grant_path)
    if (not isinstance(grant, dict) or grant.get("schema") != "safeshift-pilot-prepare-grant-v1"
            or grant.get("mode") != mode or not grant.get("owner_approval_ref")
            or not grant.get("research_lead_review_ref") or grant.get("master_sha256") != MASTER_SHA
            or grant.get("allow_all_3763_train_image_headers_and_hashes") is not True
            or grant.get("allow_folder_gt") is not True or grant.get("allow_private_kaggle_packaging") is not True):
        raise PermissionError("BLOCKED_SEPARATE_PREPARATION_DATA_READ_GRANT_REQUIRED")
    if mode not in ("PILOT", "FULL_TRAIN"):
        raise PermissionError("MODE_REQUIRED")
    if mode == "FULL_TRAIN" and (not grant.get("full_train_explicit") or not grant.get("pilot_review_ref")):
        raise PermissionError("FULL_TRAIN_PACKAGING_LOCKED")
    relative(dataset_root)
    root = safe(Path.cwd(), dataset_root)
    output = processed(output)
    if output.exists():
        raise FileExistsError("NO_OVERWRITE_INPUT_BUNDLE")
    master_bytes = subprocess.check_output(["git", "show", f"{LEGACY}:{MASTER_PATH}"])
    if hashlib.sha256(master_bytes).hexdigest() != MASTER_SHA:
        raise ValueError("ORIGINAL_TRAIN_MASTER_CHECKSUM")
    master = validate_master(json.loads(master_bytes))
    from PIL import Image
    inventory = []
    # Exact original 3763 locators, no dataset enumeration or TEST lookup.
    for row in master:
        path = safe(root, row["image_locator"])
        if sha(path) != row["image_sha256"]:
            raise ValueError("BLOCKED_TRAIN_IMAGE_HASH:" + row["sample_id"])
        with Image.open(path) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise ValueError("BLOCKED_NON_STILL_IMAGE:" + row["sample_id"])
            width, height = image.size
            image.verify()
        inventory.append({k: row[k] for k in ("sample_id", "domain", "level", "image_locator", "image_sha256", "group")}
                         | {"width": width, "height": height, "split": "TRAIN"})
    primary = select_main(inventory) if mode == "PILOT" else sorted(inventory, key=lambda r: r["sample_id"])
    verified, verification, extra = [], None, []
    availability = "NOT_RUN/BLOCKED_NO_VERIFIED_QWEN_ARTIFACT_GRANT"
    if qwen_path:
        if grant.get("allow_qwen_verified_export") is not True or grant.get("qwen_export_sha256") != sha(qwen_path):
            raise PermissionError("QWEN_EXPORT_READ_AND_HASH_GRANT_REQUIRED")
        verification = read(qwen_path)
        if (verification.get("schema") != "safeshift-original-v4-labels-v1"
                or verification["verification"]["V4_ORIGINAL_COHORT_VERIFICATION"] != "PASS"
                or verification["verification"]["baseline_pooling_allowed"] is not False):
            raise ValueError("QWEN_ORIGINAL_EXPORT_VERIFICATION_REQUIRED")
        verified = verification["samples"]
        extra = select_supplement(verified, master, {r["sample_id"] for r in primary}) if mode == "PILOT" else []
        availability = "VERIFIED_ORIGINAL_V4_ONLY"
    by_id = {r["sample_id"]: r for r in inventory}
    extra = [by_id[r["sample_id"]] for r in extra]
    selected = primary + extra
    selected = [{**r, "image": f"images/{i:06d}.jpg"} for i, r in enumerate(selected)]
    selected_ids = {r["sample_id"] for r in selected}
    plan = {"schema": "safeshift-three-vlm-manifest-v1", "split": "TRAIN", "mode": mode,
            "master_sha256": MASTER_SHA, "data_revision": DATA_REVISION, "seed": SEED,
            "main": selected[:len(primary)], "supplement": selected[len(primary):],
            "dimension_inventory_sha256": digest(inventory), "qwen_verified": [r for r in verified if r["sample_id"] in selected_ids],
            "qwen_export_sha256": sha(qwen_path) if qwen_path else None,
            "supplement_availability": availability,
            "selection": "capped-equal-domain; largest-area + area-quartile/aspect round-robin; seeded SHA256 ties",
            "dependency": "Original group IDs retained; no independence or representative TRAIN claim"}
    validate_plan(plan, master, mode)
    output.mkdir(parents=True, exist_ok=False)
    write_bytes(output / "master_manifest.json", master_bytes)
    write(output / "dimension_inventory.json", inventory)
    write(output / "pilot_manifest.json", plan)
    write(output / "prepare_receipt.json", {"grant": grant, "legacy": LEGACY,
          "master_sha256": MASTER_SHA, "manifest_sha256": digest(plan), "read_train_n": 3763,
          "packed_n": len(selected), "no_test": True})
    write(output / "selection_summary.json", {
        "primary_n": len(primary), "supplement_n": len(extra),
        "primary_domain_by_level": {d: dict(Counter(r["level"] for r in primary if r["domain"] == d))
                                    for d in sorted({r["domain"] for r in inventory})},
        "primary_width_range": [min(r["width"] for r in primary), max(r["width"] for r in primary)],
        "primary_height_range": [min(r["height"] for r in primary), max(r["height"] for r in primary)],
        "primary_aspect_range": [min(r["width"] / r["height"] for r in primary), max(r["width"] / r["height"] for r in primary)],
        "primary_unique_groups": len({r["group"] for r in primary}), "independent_image_claim": False})
    if verification:
        write_bytes(output / "qwen_verification.json", Path(qwen_path).read_bytes())
    for row in selected:
        source, target = safe(root, row["image_locator"]), safe(output, row["image"])
        target.parent.mkdir(exist_ok=True)
        with source.open("rb") as reader, target.open("xb") as writer:
            shutil.copyfileobj(reader, writer)
        if sha(target) != row["image_sha256"]:
            raise ValueError("PACKED_COPY_CHECKSUM")
    write(output / "bundle.json", {"schema": "safeshift-private-input-v1", "manifest_sha256": digest(plan)})
    print("PREPARED", mode, len(primary), "+", len(extra), "manifest SHA256", digest(plan))
    print("No inference grant created. Lead must review IDs/distributions/thresholds and issue separate grants.")
    return plan


def main():
    parser = argparse.ArgumentParser()
    for name in ("grant", "dataset-root", "output"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--qwen-verified-export")
    parser.add_argument("--mode", choices=("PILOT", "FULL_TRAIN"), default="PILOT")
    args = parser.parse_args()
    try:
        prepare(args.grant, args.dataset_root, args.output, args.qwen_verified_export, args.mode)
    except Exception as error:
        from safeshift.pilot.runner import error_record
        failure = Path("data/processed/three_vlm_prepare_failures") / (uuid.uuid4().hex + ".json")
        write(failure, {"status": "BLOCKED", **error_record(error, "preparation"), "reduced_denominator": False})
        raise


if __name__ == "__main__":
    main()
