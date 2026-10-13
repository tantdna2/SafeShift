"""CPU builder for the 90-image seminar-direction cohort; run once from repo root.

python -m safeshift.pa3.native.seminar_cohort --dataset-root data/raw/InspecSafe-V1/train

Reads the hash-pinned local W1 audits (TRAIN rows; historical TEST metadata only,
no TEST path is opened) and, for the 90 selected IDs only, TRAIN image bytes plus
annotation JSON/TXT. No image decode, model, GPU or score. A failed check or a
quota shortage writes a blocker and no manifest; nothing is replaced or relaxed.
Writing manifests grants no execution right.
"""

import argparse
import hashlib
import json
import platform
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from safeshift.data.manifest import infer_text_domain
from safeshift.data.p2_execution import safe_path
from . import cohort, seminar

AUDIT_SHA256 = "16039f2302027ffe53f3bcdbfc80c762c88e823fbf303d5672030587cd9602d6"
FINGERPRINT = "1a52f9078d53bddcdcd8400486a6e22f7688c8c20dc85b481b128f94c723399c"
TRAIN_PREFIX = "data/raw/InspecSafe-V1/train/"
LS1_ID = re.compile(r"[a-z_]+-Level0[1-4]-[A-Za-z]+-[0-9]{6}-[0-9]{3}")
LIMITATIONS = [
    "Exploratory decision diagnostic only: not a pilot, holdout, clean or independent evaluation, nor a confirmatory benchmark.",
    "All TRAIN images were processed by the historical Qwen2.5 P2 full-pool run (aggregate exposure); "
    "the diagnostic was motivated after observing P2 aggregates, including TEST.",
    "Unresolved near-duplicate/source-family candidate links are recorded, not adjudicated; "
    "conservative components do not prove or disprove independence.",
    "No complete per-sample exposure ledger exists; absence of a record is not evidence of non-exposure.",
    "Metallurgy has few TRAIN Anomaly images and folder/text domain conflicts; descriptive only.",
    "TEST relationships come only from the W1 audit; no TEST file was opened to build this cohort.",
    "Ground truth is the original folder label; it is benchmark annotation, not verified real-world hazard.",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pretty(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode()


def train_inventory(audit, validation):
    if (not audit["audit_complete"] or not validation["audit_complete"]
            or audit["input_sha256"] != FINGERPRINT or validation["input_sha256"] != FINGERPRINT):
        raise ValueError("W1_AUDIT_INCOMPLETE_OR_FINGERPRINT")
    validated = {r["sample_id"]: r for r in validation["samples"]}
    rows, history = [], {}
    for h in audit["samples"]:
        if h["split"] != "train":
            continue
        v = validated[h["sample_id"]]
        if any(h[k] != v[k] for k in ("split", "folder_domain", "safety_level", "point_id")):
            raise ValueError("W1_AUDIT_VALIDATION_DISAGREE:" + h["sample_id"])
        if not h["image_relpath"].startswith(TRAIN_PREFIX):
            raise ValueError("TRAIN_RELPATH_REQUIRED:" + h["sample_id"])
        history[h["sample_id"]] = {**h, "text_domain": v["text_domain"]}
        rows.append({"sample_id": h["sample_id"], "split": "TRAIN",
                     "image_locator": h["image_relpath"][len(TRAIN_PREFIX):], "image_sha256": h["byte_sha256"],
                     "level": h["safety_level"], "domain": h["folder_domain"], "point_id": h["point_id"],
                     "exposure": "observed", "exposure_source": "P2 full-pool aggregate (pa3_execution_decision_dossier)",
                     "gt_source": "dataset_validation.json#samples/" + h["sample_id"],
                     "metadata_source": "duplicate_leakage_audit.json#samples/" + h["sample_id"],
                     "test_link": "unknown"})
    return rows, history


def relations(audit, train_ids):
    """TRAIN-TRAIN links for grouping and cross-split counts; TEST stays metadata."""
    mandatory, conservative, cross = [], [], defaultdict(Counter)

    def edge(a, b, kind, review, pointer, target):
        if a == b:
            return
        if a in train_ids and b in train_ids:
            target.append({"a": a, "b": b, "kind": kind, "review": review, "evidence": pointer})
        elif (a in train_ids) != (b in train_ids):
            cross[a if a in train_ids else b][kind] += 1

    for key, kind in (("exact_pair_evidence", "exact"), ("sequential_pair_evidence", "sequence"),
                      ("near_pair_evidence", "near_duplicate")):
        for i, p in enumerate(audit[key]):
            if kind == "near_duplicate" and p["byte_equal"]:
                continue
            pointer = f"duplicate_leakage_audit.json#{key}/{i}"
            if kind == "near_duplicate":
                edge(p["sample_id_a"], p["sample_id_b"], kind, "unresolved", pointer, conservative)
            else:
                edge(p["sample_id_a"], p["sample_id_b"], kind, "accepted", pointer, mandatory)
    families = {}
    for i, g in enumerate(audit["metadata_source_evidence"]["source_family_groups"]):
        members = [m["sample_id"] for m in g["members"]]
        pointer = f"duplicate_leakage_audit.json#metadata_source_evidence/source_family_groups/{i}"
        inside = [m for m in members if m in train_ids]
        for sid in inside:
            families[sid] = {"family_index": i, "size": len(members), "train_members": len(inside),
                             "test_members": len(members) - len(inside)}
        for sid in inside[1:]:
            edge(inside[0], sid, "source_family", "unresolved", pointer, conservative)
    return mandatory, mandatory + conservative, cross, families


def verify(root, row, history):
    """Path, byte SHA-256 and metadata for one selected TRAIN sample; no decode."""
    errors = []
    h = history[row["sample_id"]]
    if not seminar.LOCATOR.fullmatch(row["image_locator"]):
        return None, ["TRAIN_LOCATOR_PATTERN"]
    path = safe_path(root, row["image_locator"])
    if not path.is_file():
        return None, ["IMAGE_MISSING"]
    image = path.read_bytes()
    if sha(image) != row["image_sha256"]:
        errors.append("IMAGE_SHA256_MISMATCH")
    side = {}
    for suffix in (".json", ".txt"):
        other = path.with_suffix(suffix)
        if not other.is_file():
            errors.append("MISSING" + suffix.upper().replace(".", "_"))
            continue
        side[suffix] = other.read_bytes()
    parts = row["sample_id"].split("-")
    if (parts[0] != h["folder_domain"] or parts[1] != h["safety_level"] or parts[2] != h["robot_platform"]
            or parts[3] != h["point_id"] or h["data_type"] != seminar.binary(h["safety_level"]) + "_data"
            or "/" + seminar.binary(h["safety_level"]) + "_data/" not in "/" + row["image_locator"]):
        errors.append("ID_FOLDER_METADATA_MISMATCH")
    text_domain = None
    if ".json" in side:
        annotation = json.loads(side[".json"])
        if [annotation.get("imageWidth"), annotation.get("imageHeight")] != h["dimensions"]:
            errors.append("ANNOTATION_DIMENSIONS_MISMATCH")
    if ".txt" in side:
        text_domain = infer_text_domain(side[".txt"].decode("utf-8").strip())
        if text_domain != h["text_domain"]:
            errors.append("TEXT_DOMAIN_HISTORY_MISMATCH")
    return {"image_sha256": sha(image), "image_size_bytes": len(image),
            "json_sha256": sha(side[".json"]) if ".json" in side else None,
            "txt_sha256": sha(side[".txt"]) if ".txt" in side else None,
            "text_domain": text_domain}, errors


def build(audit_bytes, validation_bytes, root, ls1_text=None):
    audit, validation = json.loads(audit_bytes), json.loads(validation_bytes)
    if sha(audit_bytes) != AUDIT_SHA256:
        raise ValueError("W1_DUPLICATE_AUDIT_BYTES_CHANGED")
    rows, history = train_inventory(audit, validation)
    ids = {r["sample_id"] for r in rows}
    mandatory_links, all_links, cross, families = relations(audit, ids)
    mandatory = {sid: g["group_id"] for g in cohort.candidate_groups(rows, mandatory_links) for sid in g["sample_ids"]}
    components = cohort.candidate_groups(rows, all_links)
    component = {sid: g for g in components for sid in g["sample_ids"]}
    excluded = sorted({p["sample_id_a"] if p["split_a"] == "train" else p["sample_id_b"]
                       for p in audit["exact_pair_evidence"] if not p["same_split"]})
    ls1 = sorted(set(LS1_ID.findall(ls1_text))) if ls1_text is not None else []
    if ls1_text is not None and (len(ls1) != 10 or not set(ls1) <= ids):
        raise ValueError("LS1_DOCUMENTARY_TEN_TRAIN_IDS_REQUIRED")
    candidates = [{"sample_id": r["sample_id"], "domain": r["domain"], "level": r["level"],
                   "group": mandatory[r["sample_id"]]} for r in rows]
    selection = seminar.select(candidates, excluded)
    inputs = {"duplicate_audit": "data/manifests/duplicate_leakage_audit.json (local, gitignored)",
              "duplicate_audit_sha256": sha(audit_bytes), "validation": "data/manifests/dataset_validation.json (local, gitignored)",
              "validation_sha256": sha(validation_bytes), "w1_input_fingerprint": FINGERPRINT,
              "w1_audit_run_id": audit["run_id"], "w1_audit_git_commit": audit["git_commit"],
              "train_inventory_count": len(rows), "dataset_root": "InspecSafe-V1 train root (locators relative)",
              "ls1_documentary_sha256": sha(ls1_text.encode("utf-8")) if ls1_text is not None else None,
              "link_counts": dict(Counter(link["kind"] for link in all_links)),
              "mandatory_groups": len(set(mandatory.values())), "conservative_components": len(components)}
    if selection["status"] != "SELECTED":
        return {"status": "BLOCKED", "reason": "QUOTA_SHORTAGE", "selection": selection, "inputs": inputs}, None, None
    by_id = {r["sample_id"]: r for r in rows}
    samples, failures = [], {}
    for sid in selection["inference_order"]:
        row = by_id[sid]
        proof, errors = verify(root, row, history)
        if errors:
            failures[sid] = errors
            continue
        h, g, fam = history[sid], component[sid], families.get(sid)
        samples.append({
            "sample_id": sid, "image_locator": row["image_locator"], "image_sha256": row["image_sha256"],
            "image_size_bytes": proof["image_size_bytes"], "json_sha256": proof["json_sha256"],
            "txt_sha256": proof["txt_sha256"], "level": row["level"], "binary_class": seminar.binary(row["level"]),
            "domain": row["domain"], "primary": row["domain"] in seminar.PRIMARY,
            "text_domain": proof["text_domain"], "domain_conflict": proof["text_domain"] != row["domain"],
            "robot_platform": h["robot_platform"], "point_id": h["point_id"],
            "mandatory_group": mandatory[sid], "conservative_component": g["group_id"],
            "relations": {"conservative_component_train_size": len(g["sample_ids"]),
                          "train_near_duplicate_candidates": sum(1 for link in all_links if link["kind"] == "near_duplicate" and sid in (link["a"], link["b"])),
                          "test_near_duplicate_candidates": cross[sid]["near_duplicate"],
                          "test_sequence_pairs": cross[sid]["sequence"], "test_exact_pairs": cross[sid]["exact"],
                          "source_family": fam, "status": "UNRESOLVED_RECORDED_NOT_ADJUDICATED"},
            "exposure": {"prior_model_aggregate": "QWEN2_5_P2_FULL_POOL_REPORTED",
                         "ls1_documentary_per_sample": sid in ls1,
                         "this_diagnostic": "RESERVED_OBSERVED_BEFORE_FIRST_IMAGE_READ",
                         "ledger": "INCOMPLETE_NOT_CLEARANCE"}})
    if failures:
        return {"status": "BLOCKED", "reason": "SELECTED_SAMPLE_VERIFICATION_FAILED", "failures": failures,
                "selection": selection, "inputs": inputs}, None, None
    inference = {"schema": "pa3-seminar-direction-inference-v1", "run_id": seminar.RUN_ID, "split": "TRAIN",
                 "seed": seminar.SEED, "locator_root": "InspecSafe-V1 TRAIN root containing DATA_PATH/train/Annotations",
                 "order_rule": seminar.RULE["inference_order"],
                 "samples": [{k: s[k] for k in ("sample_id", "image_locator", "image_sha256")} for s in samples]}
    inference_bytes = pretty(inference)
    selected_groups = {s["mandatory_group"] for s in samples}
    touched = sorted({s["conservative_component"] for s in samples})
    manifest = {
        "schema": "pa3-seminar-direction-cohort-v1", "run_id": seminar.RUN_ID,
        "status": "LOCKED_PENDING_RESEARCH_LEAD_APPROVAL",
        "scope": "EXPLORATORY_DECISION_DIAGNOSTIC_NOT_PILOT_NOT_HOLDOUT_NOT_CONFIRMATORY",
        "split": "TRAIN", "seed": seminar.SEED, "rule": seminar.RULE, "inputs": inputs,
        "exclusions": {"exact_test_duplicate_train_ids": excluded,
                       "evidence": "duplicate_leakage_audit.json#exact_pair_evidence (same_split=false); notes/visual_provenance_review.md"},
        "selection": {k: selection[k] for k in ("status", "trace", "selected_ids")},
        "inference_manifest": seminar.INFERENCE, "inference_manifest_sha256": sha(inference_bytes),
        "samples": samples,
        "exposure_reservation": {
            "observed_ids": sorted(s["sample_id"] for s in samples),
            "mandatory_closure_ids": sorted(sid for sid, gid in mandatory.items() if gid in selected_groups),
            "conservative_components": [{"component": c, "train_size": len(next(g for g in components if g["group_id"] == c)["sample_ids"]),
                                         "selected": sum(s["conservative_component"] == c for s in samples)} for c in touched],
            "future_independent_evaluation": "FORBIDDEN_FOR_OBSERVED_IDS_AND_MANDATORY_CLOSURE",
            "conservative_components_note": "Related by unresolved candidate links; disclose in any later use"},
        "limitations": LIMITATIONS, "execution_authority": False}
    seminar.validate_cohort(manifest, inference_bytes)
    return {"status": "LOCKED_PENDING_RESEARCH_LEAD_APPROVAL"}, pretty(manifest), inference_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duplicate-audit", type=Path, default=Path("data/manifests/duplicate_leakage_audit.json"))
    parser.add_argument("--validation", type=Path, default=Path("data/manifests/dataset_validation.json"))
    parser.add_argument("--dataset-root", type=Path, default=Path("data/raw/InspecSafe-V1/train"))
    parser.add_argument("--ls1-handoff", type=Path, help="Optional documentary list of the 10 LS1 TRAIN IDs")
    parser.add_argument("--output", type=Path, default=Path("."), help="Repository root receiving data/manifests/")
    args = parser.parse_args()
    ls1 = args.ls1_handoff.read_text(encoding="utf-8") if args.ls1_handoff else None
    status, manifest, inference = build(args.duplicate_audit.read_bytes(), args.validation.read_bytes(),
                                        args.dataset_root, ls1)
    out = args.output / "data/manifests"
    if manifest is None:
        (out / "pa3_seminar_direction_blocker.json").write_bytes(pretty(status))
        print(json.dumps({k: status[k] for k in ("status", "reason")}))
        return 2
    for name, data in ((seminar.INFERENCE, inference), (seminar.COHORT, manifest)):
        target = args.output / name
        with target.open("xb") as stream:  # a locked manifest is never overwritten
            stream.write(data)
    receipt = {"schema": "pa3-seminar-direction-cohort-receipt-v1", "status": status["status"],
               "cohort_manifest": seminar.COHORT, "cohort_manifest_sha256": sha(manifest),
               "inference_manifest": seminar.INFERENCE, "inference_manifest_sha256": sha(inference),
               "builder_sha256": {p: sha((Path(__file__).parent / Path(p).name).read_bytes())
                                  for p in ("safeshift/pa3/native/seminar.py", "safeshift/pa3/native/seminar_cohort.py",
                                            "safeshift/pa3/native/cohort.py")},
               "python": sys.version.split()[0], "platform": platform.system(),
               "command": "python -m safeshift.pa3.native.seminar_cohort --dataset-root data/raw/InspecSafe-V1/train"
                          + (" --ls1-handoff <LS1 handoff document>" if ls1 else ""),
               "execution_authority": False}
    with (out / "pa3_seminar_direction_cohort_receipt.v1.json").open("xb") as stream:
        stream.write(pretty(receipt))
    print(json.dumps({k: receipt[k] for k in ("cohort_manifest_sha256", "inference_manifest_sha256")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
