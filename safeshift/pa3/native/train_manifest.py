"""CPU-only full TRAIN builder; no TEST file/model/score access or execution grant."""
import argparse
import os
from collections import Counter
from pathlib import Path

from safeshift.ls1.artifacts import json_bytes, write_json, write_new
from safeshift.protocol.schema import strict_json
from . import cohort, seminar_cohort as existing, train, preflight

VALIDATION_SHA = "65bfebb0e4081ea2575dd0a7fa21e69fb1e2b19026ee47bb35788dd18427e6c3"


def build(audit_bytes, validation_bytes, root):
    root = Path(os.path.abspath(root))  # normalize '..'; safe_path still rejects symlinks/junctions
    if existing.sha(audit_bytes) != existing.AUDIT_SHA256 or existing.sha(validation_bytes) != VALIDATION_SHA:
        raise ValueError("EXACT_W1_AUDIT_BYTES_REQUIRED")
    audit, validation = strict_json(audit_bytes), strict_json(validation_bytes)
    rows, history = existing.train_inventory(audit, validation)
    if len(rows) != train.COUNT or len({r["sample_id"] for r in rows}) != train.COUNT:
        raise ValueError("EXACT_3763_TRAIN_IDS_REQUIRED")
    # TRAIN tree only: extra or missing images also fail, without scanning TEST.
    disk = {p.relative_to(root).as_posix() for p in (Path(root) / "DATA_PATH/train/Annotations").rglob("*.jpg")}
    if disk != {r["image_locator"] for r in rows}:
        raise ValueError("TRAIN_DISK_INVENTORY_MISMATCH")
    ids = {r["sample_id"] for r in rows}
    _, links, cross, _ = existing.relations(audit, ids)
    groups = {sid: g["group_id"] for g in cohort.candidate_groups(rows, links) for sid in g["sample_ids"]}
    verified = []
    for row in sorted(rows, key=lambda r: r["sample_id"]):
        proof, errors = existing.verify(root, row, history)
        if errors:
            raise ValueError("TRAIN_VERIFICATION_FAILED:" + row["sample_id"] + ":" + ",".join(errors))
        verified.append({**{k: row[k] for k in ("sample_id", "image_locator", "image_sha256", "level", "domain")},
                         **proof, "binary_class": existing.seminar.binary(row["level"]), "group": groups[row["sample_id"]],
                         "test_exact_pairs_historical": cross[row["sample_id"]]["exact"]})
    inference = []
    for i, members in enumerate(train.partition(verified)):
        inference.append(json_bytes({"schema": "pa3-full-train-inference-v1", "split": "TRAIN", "seed": train.SEED,
            "shard_id": i, "run_id": train.run_id(i),
            "samples": [{k: r[k] for k in ("sample_id", "image_locator", "image_sha256")} for r in members]}))
    manifest = {"schema": "pa3-full-train-v1", "split": "TRAIN", "seed": train.SEED,
        "execution_authority": False, "samples": verified,
        "shards": [{"shard_id": i, "run_id": train.run_id(i), "count": train.SIZES[i],
                    "path": train.inference_path(i), "sha256": existing.sha(data)} for i, data in enumerate(inference)],
        "provenance": {"duplicate_audit_sha256": existing.sha(audit_bytes), "validation_sha256": existing.sha(validation_bytes),
                       "w1_input_fingerprint": existing.FINGERPRINT, "w1_git_commit": audit["git_commit"],
                       "w1_run_id": audit["run_id"], "ground_truth": "Original folder level/domain; Level04 Normal, Level01-03 Anomaly"},
        "counts": {"total": len(verified), "by_level": dict(Counter(r["level"] for r in verified)),
                   "by_domain": dict(Counter(r["domain"] for r in verified))},
        "limitations": ["Descriptive full TRAIN benchmark; all original IDs retained, including historical cross-split exact duplicates.",
                        "Prior Qwen P2 full-pool exposure and 90-image PA3 diagnostic; no independent holdout claim.",
                        "Dependencies, domain confounding and text-domain conflicts remain; no CI or threshold.",
                        "Shards are execution partitions, never a replacement dataset split. TEST bytes were not read."]}
    train.validate_full(manifest, inference)
    return json_bytes(manifest), inference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duplicate-audit", type=Path, default=Path("data/manifests/duplicate_leakage_audit.json"))
    parser.add_argument("--validation", type=Path, default=Path("data/manifests/dataset_validation.json"))
    parser.add_argument("--dataset-root", type=Path, default=Path("data/raw/InspecSafe-V1/train"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/pa3_full_train_manifests"))
    args = parser.parse_args()
    manifest, shards = build(args.duplicate_audit.read_bytes(), args.validation.read_bytes(), args.dataset_root)
    args.output.mkdir(parents=True, exist_ok=False)
    write_new(args.output / Path(train.FULL).name, manifest)
    for i, payload in enumerate(shards):
        write_new(args.output / Path(train.inference_path(i)).name, payload)
    receipt = {"schema": "pa3-full-train-builder-receipt-v1", "manifest_sha256": existing.sha(manifest),
               "shard_sha256": [existing.sha(s) for s in shards], "verified": train.COUNT, "test_reads": 0,
               "builder_source_commit": preflight.git(Path(__file__).resolve().parents[3], "rev-parse", "HEAD").decode(),
               "builder_sha256": {p: existing.sha((Path(__file__).parent / p).read_bytes())
                                  for p in ("train.py", "train_manifest.py", "seminar_cohort.py", "cohort.py")},
               "command": "python -m safeshift.pa3.native.train_manifest", "execution_authority": False}
    write_json(args.output / "pa3_full_train_receipt.v1.json", receipt)
    print({"verified": train.COUNT, "manifest_sha256": receipt["manifest_sha256"], "shard_sizes": train.SIZES})


if __name__ == "__main__":
    main()
