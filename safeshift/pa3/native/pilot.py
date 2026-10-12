"""Predeclared exploratory TRAIN pilot. Pure design; real access needs its own grant.

Input is the Task 4 custodian interchange, NOT a discovered dataset schema.
No image/directory scan or TEST read is used to construct this manifest.
"""
import hashlib
from pathlib import Path

from safeshift.protocol.schema import strict_json
from safeshift.ls1.kaggle import attached_path
from safeshift.ls1.experiment import open_sample
from ..artifacts import json_bytes
from . import access, cohort

SEED = "pa3-task5-pilot-2026-10-12-v1"
DOMAINS = ("coal_conveyor", "metallurgy", "oil_chemical", "power", "tunnel")


def propose(rows, links):
    """Select 4 Normal + 4 Anomaly per domain, one image per dependency group.

    Stop with exact shortages; no redistribution, lower N, replacement, score
    input, new seed or relaxed exclusions. Group choice uses sample-ID ranking.
    """
    indexed = cohort.validate_inventory(rows)
    if any(r["domain"] not in DOMAINS for r in rows):
        raise ValueError("UNKNOWN_DOMAIN")
    groups = cohort.candidate_groups(rows, links)
    membership = {sid: g for g in groups for sid in g["sample_ids"]}
    ranking = lambda sid: (hashlib.sha256((SEED + "|" + sid).encode()).hexdigest(), sid)
    selected, used, shortages = [], set(), {}
    for domain in DOMAINS:
        for normal in (True, False):
            eligible = sorted((sid for sid, row in indexed.items()
                if row["domain"] == domain and (row["level"] == "Level04") == normal
                and not membership[sid]["quarantine_reasons"]), key=ranking)
            chosen = []
            for sid in eligible:
                gid = membership[sid]["group_id"]
                if gid not in used:
                    used.add(gid)
                    chosen.append(sid)
                if len(chosen) == 4:
                    break
            selected.extend(chosen)
            if len(chosen) < 4:
                shortages[domain + ("/Normal" if normal else "/Anomaly")] = 4-len(chosen)
    if shortages:
        return {"status": "STOP_INSUFFICIENT_ELIGIBLE_GROUPS", "shortages": shortages,
                "seed": SEED, "selected_ids": [], "execution_authority": False}
    observed_groups = [g for g in groups if g["group_id"] in used]
    return {"schema": "pa3-pilot-manifest-v1", "status": "PROPOSED_REQUIRES_LEAD_APPROVAL",
            "seed": SEED, "inventory": rows, "links": links, "groups": groups,
            "selected_ids": selected, "planned": 40,
            "observed_ids": sorted(sid for g in observed_groups for sid in g["sample_ids"]),
            "observed_groups": sorted(used),
            "future_independent_evaluation": "FORBIDDEN_FOR_ALL_OBSERVED_IDS_AND_GROUPS",
            "execution_authority": False}


def validate(manifest):
    expected = propose(manifest["inventory"], manifest["links"])
    if expected.get("schema") != "pa3-pilot-manifest-v1" or json_bytes(expected) != json_bytes(manifest):
        raise ValueError("PILOT_MANIFEST_SELECTION_OR_EXPOSURE_MISMATCH")
    return {r["sample_id"]: r for r in manifest["inventory"]}


def checked(repo, settings, inputs):
    # Until the Lead approves the actual manifest + technical seal, this denies
    # before interpreting paths, reading metadata or loading any real image.
    access.require("pilot-train", settings, repo)
    path = attached_path(inputs, settings["pilot_manifest_input"])
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != settings["pilot_manifest_sha256"]:
        raise ValueError("PILOT_MANIFEST_CHECKSUM")
    manifest = strict_json(payload)
    indexed = validate(manifest)
    return manifest, indexed


def samples(repo, settings, inputs):
    manifest, indexed = checked(repo, settings, inputs)
    return [{k: indexed[sid][k] for k in ("sample_id", "image_locator", "image_sha256")}
            for sid in manifest["selected_ids"]]


def open_image(repo, settings, row, inputs):
    if row not in samples(repo, settings, inputs):
        raise PermissionError("IMAGE_OUTSIDE_PILOT_MANIFEST")
    # open_sample rejects path aliases/escapes and hashes before decode; no scan.
    return open_sample(row, attached_path(inputs, settings["dataset_input"]))


def metadata(repo, settings, inputs):
    manifest, indexed = checked(repo, settings, inputs)
    groups = {sid: g["group_id"] for g in manifest["groups"] for sid in g["sample_ids"]}
    return {sid: {"level": indexed[sid]["level"], "domain": indexed[sid]["domain"],
                  "group": groups[sid]} for sid in manifest["selected_ids"]}


def prior_technical(root, repo, tokenizer, trusted_seal):
    """CPU recompute real evidence, never trust a caller's PASS boolean."""
    from .journal import Journal
    from .native_audit import audit
    journal = Journal(root)
    if hashlib.sha256(journal.path("seal").read_bytes()).hexdigest() != trusted_seal:
        raise ValueError("TECHNICAL_SEAL_CHECKSUM")
    header = journal.read("manifest")
    if header["mode"] != "technical" or header["run_id"] != access.TECHNICAL["run_id"] + "-qualification":
        raise ValueError("EXACT_TECHNICAL_RUN_REQUIRED")
    from safeshift.ls1.experiment import synthetic_samples
    images = synthetic_samples()
    try:
        expected = [{k: v for k, v in r.items() if k != "image"} for r in images]
        if header["samples"] != expected:
            raise ValueError("EXACT_FOUR_SYNTHETIC_REQUIRED")
    finally:
        for r in images:
            r["image"].close()
    proof = audit(root, repo, tokenizer)
    if not proof["completed"] or len(proof["results"]) != 4 or any(r["status"] != "SUCCESS" for r in proof["results"]):
        raise ValueError("TECHNICAL_FOUR_AUDITED_SCORES_REQUIRED")
    return proof


def verify_prior(repo, settings, inputs, tokenizer):
    """Independent proof before native load, including direct scorer use."""
    import subprocess
    from safeshift.ls1.artifacts import digest
    from .journal import Journal, run_path
    access.require("pilot-train", settings, repo)
    bundle = attached_path(inputs, settings["technical_source_bundle_input"])
    if digest(bundle) != settings["technical_source_bundle_sha256"]:
        raise ValueError("TECHNICAL_SOURCE_BUNDLE_CHECKSUM")
    technical_repo = run_path(repo, settings["run_id"]).parent / (settings["run_id"] + "-technical-source")
    if not technical_repo.exists():
        subprocess.run(["git", "-c", "core.autocrlf=false", "clone", "--no-checkout",
                        str(bundle), str(technical_repo)], check=True)
        subprocess.run(["git", "-C", str(technical_repo), "-c", "core.autocrlf=false",
                        "checkout", "--detach", settings["technical_source_commit"]], check=True)
    prior_root = attached_path(inputs, settings["technical_run_input"])
    if Journal(prior_root).read("manifest")["source"]["source_commit"] != settings["technical_source_commit"]:
        raise ValueError("TECHNICAL_SOURCE_COMMIT_MISMATCH")
    return prior_technical(prior_root, technical_repo, tokenizer, settings["technical_seal_sha256"])
