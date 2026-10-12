"""Pure candidate cohort tooling and separately locked real-data adapters.

This is an internal interchange schema, NOT a claim about InspecSafe metadata.
Custodian provenance, reviewed links, exposure completeness and allocation must
be approved separately. A deterministic partition does not prove independence.
"""

import hashlib
import math
import re
from collections import defaultdict
from pathlib import Path

from safeshift.ls1.core import LEVELS
from safeshift.protocol.schema import strict_json
from . import access
from ..artifacts import json_bytes
from .journal import safe_relative

FIELDS = {"sample_id", "split", "image_locator", "image_sha256", "level", "domain", "point_id",
          "exposure", "exposure_source", "gt_source", "metadata_source", "test_link"}


def validate_inventory(rows):
    if type(rows) is not list or not rows:
        raise ValueError("NONEMPTY_METADATA_INVENTORY_REQUIRED")
    ids, locators = set(), set()
    for row in rows:
        if type(row) is not dict or set(row) != FIELDS:
            raise ValueError("INTERNAL_METADATA_SCHEMA_MISMATCH")
        for key in ("sample_id", "domain", "exposure_source", "gt_source", "metadata_source"):
            if type(row[key]) is not str or not row[key].strip():
                raise ValueError("METADATA_PROVENANCE_REQUIRED:" + key)
        if row["sample_id"] in ids or row["image_locator"] in locators:
            raise ValueError("DUPLICATE_SAMPLE_OR_LOCATOR")
        ids.add(row["sample_id"])
        locators.add(row["image_locator"])
        if row["split"] != "TRAIN":
            raise ValueError("TRAIN_ONLY_METADATA_TEST_FORBIDDEN")
        if row["level"] not in LEVELS or row["exposure"] not in {"unseen", "observed", "unknown"}:
            raise ValueError("GT_OR_EXPOSURE_INVALID")
        if row["test_link"] not in {"none_verified", "observed_test", "unknown"}:
            raise ValueError("TEST_RELATION_EVIDENCE_REQUIRED")
        if row["point_id"] is not None and (type(row["point_id"]) is not str or not row["point_id"]):
            raise ValueError("POINT_ID_INVALID")
        if row["level"] == "Level04" and not row["point_id"]:
            raise ValueError("NORMAL_POINT_ID_REQUIRED")
        safe_relative(row["image_locator"])
        if type(row["image_sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", row["image_sha256"]):
            raise ValueError("IMAGE_SHA256_REQUIRED")
    return {r["sample_id"]: r for r in rows}


def candidate_groups(rows, links):
    """Proposal: transitive exact/Normal-point/reviewed-link components.

    Unknown candidate relationships join conservatively and quarantine the
    entire component. No near-duplicate distance threshold is selected here.
    """
    indexed = validate_inventory(rows)
    parent = {i: i for i in indexed}
    uncertain = set()

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    hashes, points = {}, {}
    for row in rows:
        sid, sha = row["sample_id"], row["image_sha256"]
        if sha in hashes:
            union(sid, hashes[sha])
        hashes[sha] = sid
        if row["level"] == "Level04":
            key = row["point_id"]
            if key in points:
                union(sid, points[key])
            points[key] = sid
    for link in links:
        if (set(link) != {"a", "b", "kind", "review", "evidence"}
                or link["a"] not in indexed or link["b"] not in indexed
                or link["a"] == link["b"] or not link["evidence"]
                or link["kind"] not in {"exact", "sequence", "scene", "source_family", "near_duplicate"}
                or link["review"] not in {"accepted", "rejected", "unresolved"}):
            raise ValueError("RELATION_PROVENANCE_OR_MEMBERSHIP_INVALID")
        if link["review"] != "rejected":
            union(link["a"], link["b"])
        if link["review"] == "unresolved":
            uncertain.update((link["a"], link["b"]))
    members = defaultdict(list)
    for sid in sorted(indexed):
        members[find(sid)].append(sid)
    groups = []
    for ids in members.values():
        reasons = set()
        for sid in ids:
            row = indexed[sid]
            if row["exposure"] != "unseen":
                reasons.add("exposure_" + row["exposure"])
            if row["test_link"] != "none_verified":
                reasons.add("test_link_" + row["test_link"])
            if sid in uncertain:
                reasons.add("unresolved_relation")
        domains = sorted({indexed[i]["domain"] for i in ids})
        classes = sorted({"Normal" if indexed[i]["level"] == "Level04" else "Anomaly" for i in ids})
        groups.append({"group_id": hashlib.sha256(json_bytes(ids)).hexdigest(), "sample_ids": ids,
                       "domains": domains, "binary_classes": classes, "quarantine_reasons": sorted(reasons)})
    return sorted(groups, key=lambda g: g["group_id"])


def candidate_allocation(groups, *, salt, dev_fraction):
    """Explicit proposal parameters; no defaults, no automatic protocol freeze."""
    if not isinstance(salt, str) or not salt or type(dev_fraction) not in (int, float) or not 0 < dev_fraction < 1:
        raise ValueError("EXPLICIT_PROPOSED_ALLOCATION_REQUIRED")
    strata, result = defaultdict(list), {}
    for g in groups:
        gid = g["group_id"]
        if gid in result:
            raise ValueError("DUPLICATE_GROUP")
        result[gid] = "QUARANTINE"
        if not g["quarantine_reasons"]:
            domain = tuple(g["domains"]) if len(g["domains"]) == 1 else ("mixed-domain",)
            label = tuple(g["binary_classes"]) if len(g["binary_classes"]) == 1 else ("mixed-label",)
            strata[(domain, label)].append(gid)
    for ids in strata.values():
        if len(ids) < 2:
            continue
        ordered = sorted(ids, key=lambda i: hashlib.sha256((salt + "|" + i).encode()).hexdigest())
        n = math.floor(len(ids) * dev_fraction)
        for i, gid in enumerate(ordered):
            result[gid] = "TRAIN-dev" if i < n else "TRAIN-holdout"
    return {"status": "PROPOSED_NOT_AUTHORITY_NOT_INDEPENDENCE", "salt": salt,
            "dev_fraction": dev_fraction, "assignment": result}


def validate_overlay(rows, groups, allocation):
    indexed = validate_inventory(rows)
    membership = {}
    for group in groups:
        ids = group["sample_ids"]
        if not ids or ids != sorted(set(ids)) or group["group_id"] != hashlib.sha256(json_bytes(ids)).hexdigest():
            raise ValueError("GROUP_ID_MEMBERSHIP_MISMATCH")
        for sid in ids:
            if sid not in indexed or sid in membership:
                raise ValueError("GROUP_OVERLAP_OR_UNKNOWN_ID")
            membership[sid] = group["group_id"]
        role = allocation["assignment"].get(group["group_id"])
        if role not in {"QUARANTINE", "TRAIN-dev", "TRAIN-holdout"}:
            raise ValueError("COHORT_ROLE_INVALID")
        if group["quarantine_reasons"] and role != "QUARANTINE":
            raise ValueError("EXPOSED_GROUP_ALLOCATED")
        if role != "QUARANTINE" and any(indexed[i]["exposure"] != "unseen" or
                                        indexed[i]["test_link"] != "none_verified" for i in ids):
            raise ValueError("EXPOSURE_LEDGER_ALLOCATION_MISMATCH")
    if set(membership) != set(indexed) or set(allocation["assignment"]) != set(membership.values()):
        raise ValueError("EXACT_COHORT_MEMBERSHIP_REQUIRED")
    # Duplicate and Normal-point relationships must never cross assigned groups.
    mandatory = candidate_groups(rows, [])
    for g in mandatory:
        if len({membership[i] for i in g["sample_ids"]}) != 1:
            raise ValueError("MANDATORY_RELATION_SPLIT")
    return membership


def _plan_path(repo, settings, inputs):
    if inputs is not None:
        from safeshift.ls1.kaggle import attached_path
        return attached_path(inputs, settings["cohort_plan_input"])
    return Path(repo) / safe_relative(settings["cohort_plan"])


def _checked_plan(repo, settings, inputs=None):
    access.require(settings["mode"], settings)
    access.require("metadata", settings)  # before converting or reading any data path
    path = _plan_path(repo, settings, inputs)
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != settings["cohort_plan_sha256"]:
        raise ValueError("COHORT_PLAN_CHECKSUM_MISMATCH")
    plan = strict_json(data)
    expected = candidate_groups(plan["inventory"], plan["links"])
    if expected != plan["groups"]:
        raise ValueError("COHORT_GROUP_GRAPH_MISMATCH")
    membership = validate_overlay(plan["inventory"], plan["groups"], plan["allocation"])
    return plan, membership


def load_plan(repo, settings, inputs=None):
    plan, membership = _checked_plan(repo, settings, inputs)
    # A future audited authority must bind this exact plan/hash and algorithm.
    role = {"train-dev": "TRAIN-dev", "train-holdout": "TRAIN-holdout"}.get(settings["mode"])
    if role is None:
        raise PermissionError("TRAIN_COHORT_MODE_REQUIRED")
    selected = [r for r in plan["inventory"]
                if plan["allocation"]["assignment"][membership[r["sample_id"]]] == role]
    if not selected:
        raise ValueError("EMPTY_AUTHORIZED_COHORT")
    samples = [{k: r[k] for k in ("sample_id", "image_locator", "image_sha256")} for r in selected]
    # Ground truth stays out of the scorer. Evaluation joins only after sealing.
    return samples


def open_image(repo, settings, row, inputs=None):
    access.require(settings["mode"], settings)
    access.require("images", settings)
    planned = load_plan(repo, settings, inputs)
    if row not in planned:
        raise PermissionError("IMAGE_OUTSIDE_EXACT_PLANNED_COHORT")
    from safeshift.ls1.experiment import open_sample
    if inputs is not None:
        from safeshift.ls1.kaggle import attached_path
        root = attached_path(inputs, settings["dataset_input"])
    else:
        root = Path(repo) / safe_relative(settings["dataset_root"])
    return open_sample(row, root)


def evaluation_metadata(repo, settings, ids, inputs=None):
    access.require(settings["mode"], settings)
    access.require("metadata", settings)
    plan, membership = _checked_plan(repo, settings, inputs)
    role = {"train-dev": "TRAIN-dev", "train-holdout": "TRAIN-holdout"}.get(settings["mode"])
    planned_ids = {r["sample_id"] for r in plan["inventory"]
                   if plan["allocation"]["assignment"][membership[r["sample_id"]]] == role}
    if not role or set(ids) != planned_ids:
        raise ValueError("EVALUATION_COHORT_MISMATCH")
    selected = {r["sample_id"]: {"level": r["level"], "domain": r["domain"], "group": membership[r["sample_id"]]}
                for r in plan["inventory"] if r["sample_id"] in ids}
    if set(selected) != set(ids):
        raise ValueError("EXACT_GT_JOIN_REQUIRED")
    return selected
