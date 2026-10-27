"""Original TRAIN identity, deterministic stratification and private bundle checks."""
from collections import Counter, defaultdict
import hashlib
from pathlib import Path
import re

from .artifacts import read, relative, safe, sha
from .contract import (DATA_REVISION, DOMAINS, LEVELS, MASTER_SHA, QUOTAS, SEED,
                       digest, require_hash)

ID_PATTERN = re.compile(r"(coal_conveyor|oil_chemical|power|tunnel|metallurgy)-(Level0[1-4])-[A-Za-z]+-[0-9]{6}-[0-9]{3}")


def validate_master(value):
    if value.get("schema") != "pa3-full-train-v1" or value.get("split") != "TRAIN":
        raise ValueError("ORIGINAL_TRAIN_MASTER_REQUIRED_NO_TEST")
    rows = value["samples"]
    if len(rows) != 3763 or len({r["sample_id"] for r in rows}) != 3763:
        raise ValueError("EXACT_3763_UNIQUE_TRAIN_IDS_REQUIRED")
    for r in rows:
        match = ID_PATTERN.fullmatch(r["sample_id"])
        loc = r["image_locator"]
        relative(loc)
        if (not match or match.groups() != (r["domain"], r["level"])
                or not loc.startswith("DATA_PATH/train/Annotations/")
                or Path(loc).stem != r["sample_id"] or not loc.endswith(".jpg")
                or ("/Normal_data/" in loc) != (r["level"] == "Level04")):
            raise ValueError("ORIGINAL_FOLDER_LABEL_DOMAIN_ID_PATH_MISMATCH")
        require_hash(r["image_sha256"])
    if Counter(r["level"] for r in rows) != {"Level01": 490, "Level02": 251, "Level03": 8, "Level04": 3014}:
        raise ValueError("ORIGINAL_TRAIN_SUPPORT_MISMATCH")
    return rows


def rank(sid, purpose="select"):
    return hashlib.sha256((SEED + "|" + purpose + "|" + sid).encode()).hexdigest(), sid


def select_main(rows):
    """Pure metadata function. No model results accepted. Returns exactly 160.

    Capped equal domain allocation within level; largest area in each occupied
    cell, then round-robin area quartile × aspect bin, seeded ties. No replacement.
    """
    ids = [r["sample_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("DUPLICATE_IDS")
    for r in rows:
        if (r["domain"] not in DOMAINS or r["level"] not in LEVELS or r.get("split") != "TRAIN"
                or any(type(r.get(k)) is not int or r[k] <= 0 for k in ("width", "height"))):
            raise ValueError("TRAIN_LABEL_DOMAIN_DIMENSIONS_REQUIRED")
    selected = []
    for level, quota in QUOTAS.items():
        pools = {d: [r for r in rows if r["domain"] == d and r["level"] == level] for d in DOMAINS}
        if sum(map(len, pools.values())) < quota:
            raise ValueError("BLOCKED_INSUFFICIENT_160:" + level)
        allocation = Counter()
        for _ in range(quota):
            available = [d for d in DOMAINS if allocation[d] < len(pools[d])]
            domain = min(available, key=lambda d: (allocation[d], rank(d, level)))
            allocation[domain] += 1
        for domain, n in allocation.items():
            pool = sorted(pools[domain], key=lambda r: (r["width"] * r["height"], rank(r["sample_id"])))
            largest = pool[-1]
            chosen = [largest]
            cells = defaultdict(list)
            for i, row in enumerate(pool):
                if row is largest:
                    continue
                ratio = row["width"] / row["height"]
                shape = 0 if ratio < .8 else 2 if ratio > 1.25 else 1
                cells[(min(3, i * 4 // len(pool)), shape)].append(row)
            for values in cells.values():
                values.sort(key=lambda r: rank(r["sample_id"]))
            while len(chosen) < n:
                for cell in sorted(cells):
                    if cells[cell] and len(chosen) < n:
                        chosen.append(cells[cell].pop(0))
            selected.extend(chosen)
    # First 12 include largest area from each represented level, then seeded order.
    sentinel = [max((r for r in selected if r["level"] == l),
                    key=lambda r: (r["width"] * r["height"], rank(r["sample_id"]))) for l in LEVELS]
    sentinel_ids = {r["sample_id"] for r in sentinel}
    return sentinel + sorted((r for r in selected if r["sample_id"] not in sentinel_ids),
                             key=lambda r: rank(r["sample_id"], "order"))


def select_supplement(verified, master, main_ids):
    """Only verified original V4 SUCCESS rows. Recovery/composite never eligible."""
    by_id = {r["sample_id"]: r for r in master}
    eligible = []
    seen = set()
    for r in verified:
        sid = r["sample_id"]
        if sid in seen or sid not in by_id:
            raise ValueError("QWEN_DUPLICATE_OR_UNKNOWN_ID")
        seen.add(sid)
        if (r.get("cohort") != "QWEN3_V4_ORIGINAL" or r.get("status") != "SUCCESS"
                or r.get("verified") is not True or not r.get("verification_ref")):
            raise ValueError("ORIGINAL_V4_VERIFICATION_REQUIRED")
        require_hash(r["source_artifact_sha256"])
        if (r["ground_truth"] != by_id[sid]["level"] or r["image_sha256"] != by_id[sid]["image_sha256"]
                or r.get("predicted_label") not in LEVELS):
            raise ValueError("QWEN_GT_INPUT_BINDING")
        if r["ground_truth"] != "Level04" and r["predicted_label"] == "Level04" and sid not in main_ids:
            eligible.append(r)
    return sorted(eligible, key=lambda r: rank(r["sample_id"], "supplement"))[:20]


def validate_plan(plan, master, mode="PILOT"):
    if (plan.get("schema") != "safeshift-three-vlm-manifest-v1" or plan.get("split") != "TRAIN"
            or plan.get("master_sha256") != MASTER_SHA or plan.get("data_revision") != DATA_REVISION
            or plan.get("mode") != mode or plan.get("seed") != SEED):
        raise ValueError("PLAN_SOURCE_SPLIT_MODE_MISMATCH")
    main, extra = plan["main"], plan["supplement"]
    if mode == "PILOT":
        if len(main) != 160 or Counter(r["level"] for r in main) != QUOTAS or len(extra) > 20:
            raise ValueError("EXACT_160_QUOTAS_AND_MAX20_REQUIRED")
    elif mode != "FULL_TRAIN" or len(main) != 3763 or extra:
        raise ValueError("EXACT_FULL_TRAIN_REQUIRED")
    rows = main + extra
    by_id = {r["sample_id"]: r for r in master}
    if len({r["sample_id"] for r in rows}) != len(rows):
        raise ValueError("PLAN_DUPLICATE_ID")
    for i, r in enumerate(rows):
        if r["sample_id"] not in by_id:
            raise ValueError("PLAN_OUTSIDE_ORIGINAL_TRAIN")
        original = by_id[r["sample_id"]]
        if any(r[k] != original[k] for k in ("level", "domain", "image_sha256", "image_locator")):
            raise ValueError("PLAN_CHANGED_ORIGINAL_METADATA")
        if r.get("image") != f"images/{i:06d}.jpg":
            raise ValueError("OPAQUE_IMAGE_ORDER_REQUIRED")
        if any(type(r.get(k)) is not int or r[k] <= 0 for k in ("width", "height")):
            raise ValueError("PLAN_DIMENSIONS_REQUIRED")
    if mode == "FULL_TRAIN" and set(by_id) != {r["sample_id"] for r in main}:
        raise ValueError("FULL_3763_MEMBERSHIP")
    if plan["qwen_verified"] or extra:
        verified = select_supplement(plan["qwen_verified"], master, {r["sample_id"] for r in main})
        if [r["sample_id"] for r in verified] != [r["sample_id"] for r in extra]:
            raise ValueError("SUPPLEMENT_MEMBERSHIP_NOT_VERIFIED")
    return rows


def load_bundle(root, mode="PILOT", verify_images=True):
    root = Path(root)
    if sha(safe(root, "master_manifest.json")) != MASTER_SHA:
        raise ValueError("ORIGINAL_MASTER_BYTES_REQUIRED")
    master = validate_master(read(root / "master_manifest.json"))
    plan = read(safe(root, "pilot_manifest.json"))
    rows = validate_plan(plan, master, mode)
    bundle = read(safe(root, "bundle.json"))
    if bundle != {"schema": "safeshift-private-input-v1", "manifest_sha256": digest(plan)}:
        raise ValueError("BUNDLE_MANIFEST_CHECKSUM")
    inventory = read(safe(root, "dimension_inventory.json"))
    if digest(inventory) != plan["dimension_inventory_sha256"] or len(inventory) != 3763:
        raise ValueError("APPROVED_DIMENSION_INVENTORY_CHECKSUM")
    by_id = {r["sample_id"]: r for r in master}
    if set(by_id) != {r["sample_id"] for r in inventory}:
        raise ValueError("DIMENSION_EXACT_TRAIN_MEMBERSHIP")
    for r in inventory:
        if any(r[k] != by_id[r["sample_id"]][k] for k in ("domain", "level", "image_locator", "image_sha256")):
            raise ValueError("DIMENSION_METADATA_CHANGED")
    if mode == "PILOT" and [r["sample_id"] for r in select_main(inventory)] != [r["sample_id"] for r in plan["main"]]:
        raise ValueError("PILOT_SELECTION_NOT_REPRODUCIBLE")
    if plan.get("qwen_export_sha256"):
        qpath = safe(root, "qwen_verification.json")
        if sha(qpath) != plan["qwen_export_sha256"]:
            raise ValueError("QWEN_EXPORT_CHECKSUM")
        q = read(qpath)
        if (q.get("schema") != "safeshift-original-v4-labels-v1"
                or q["verification"]["V4_ORIGINAL_COHORT_VERIFICATION"] != "PASS"
                or q["verification"]["baseline_pooling_allowed"] is not False):
            raise ValueError("QWEN_ORIGINAL_VERIFICATION_REQUIRED")
        chosen = select_supplement(q["samples"], master, {r["sample_id"] for r in plan["main"]})
        if [r["sample_id"] for r in chosen] != [r["sample_id"] for r in plan["supplement"]]:
            raise ValueError("QWEN_SUPPLEMENT_NOT_REPRODUCIBLE")
        selected_ids = {r["sample_id"] for r in rows}
        if plan["qwen_verified"] != [r for r in q["samples"] if r["sample_id"] in selected_ids]:
            raise ValueError("QWEN_TABLE_PROVENANCE_MISMATCH")
    elif plan["qwen_verified"] or plan["supplement"]:
        raise ValueError("QWEN_UNVERIFIED_TABLE_FORBIDDEN")
    if verify_images:
        for r in rows:
            inv = next(x for x in inventory if x["sample_id"] == r["sample_id"])
            if (r["width"], r["height"]) != (inv["width"], inv["height"]):
                raise ValueError("PLAN_DIMENSIONS_CHANGED")
            actual = sha(safe(root, r["image"]))
            if actual != r["image_sha256"]:
                raise ValueError("IMAGE_CHECKSUM:" + r["sample_id"] + " expected=" + r["image_sha256"] + " actual=" + actual)
    return plan, rows


def discover(inputs, filename, limit=512):
    """Direct Kaggle mounts and datasets/<owner>/<slug>, bounded, no rglob/TEST."""
    inputs = Path(inputs)
    mounts, visited = [], 0
    def directories(p):
        nonlocal visited
        found = []
        for entry in p.iterdir():
            visited += 1
            if visited > limit:
                raise ValueError("DISCOVERY_BOUND")
            checked = safe(inputs, entry.relative_to(inputs).as_posix())
            if checked.is_dir():
                found.append(checked)
        return sorted(found)
    for mount in directories(inputs):
        mounts.append(mount)
        if mount.name == "datasets":
            for owner in directories(mount):
                mounts.extend(directories(owner))
    found = []
    for mount in mounts:
        for prefix in ("", "safeshift-pilot-input/"):
            candidate = safe(inputs, (mount.relative_to(inputs) / (prefix + filename)).as_posix())
            if candidate.is_file():
                found.append(candidate)
    if len(found) != 1:
        raise ValueError(f"UNIQUE_{filename}_REQUIRED_FOUND_{len(found)}")
    return found[0]
