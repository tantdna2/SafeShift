"""Seminar-direction decision diagnostic: one predeclared 90-image TRAIN cohort.

EXPLORATORY DECISION DIAGNOSTIC — not a pilot, holdout or confirmatory benchmark.
Selection is a pure function of W1 TRAIN metadata/relations and a fixed seed;
it has no model-output input. Every real manifest/image read is gated by
access.require("seminar-diagnostic"), whose committed grant is null until a
reviewed authority-only release binds both manifest hashes. Inference reads only
the GT-free inference manifest; the cohort manifest (GT, domains, relations) is
read after the raw journal is sealed.
"""

import hashlib
import re
import subprocess
from pathlib import Path, PurePosixPath

from safeshift.ls1.artifacts import digest
from safeshift.ls1.core import LEVELS
from safeshift.ls1.experiment import open_sample
from safeshift.ls1.kaggle import attached_path
from safeshift.data.p2_execution import safe_path
from safeshift.protocol.schema import strict_json
from . import access
from .journal import Journal, run_path

MODE = access.DIAGNOSTIC["mode"]
RUN_ID = access.DIAGNOSTIC["run_id"]
SEED = "pa3-seminar-direction-2026-10-13-v1"
STRATA = (("coal_conveyor", 10), ("oil_chemical", 10), ("power", 10), ("tunnel", 10), ("metallurgy", 5))
PRIMARY = ("coal_conveyor", "oil_chemical", "power", "tunnel")
LEVEL03_FLOOR = 2
PLANNED = sum(2 * q for _, q in STRATA)
COHORT = "data/manifests/pa3_seminar_direction_cohort.v1.json"
INFERENCE = "data/manifests/pa3_seminar_direction_inference.v1.json"
LOCATOR = re.compile(r"DATA_PATH/train/Annotations/(?:Normal|Anomaly)_data/[A-Za-z0-9_-]+/([A-Za-z0-9_-]+)\.jpg")
SAMPLE_ID = re.compile(r"(coal_conveyor|oil_chemical|power|tunnel|metallurgy)-Level0[1-4]-[A-Za-z]+-[0-9]{6}-[0-9]{3}")
RULE = {
    "seed": SEED,
    "universe": "W1 historical TRAIN inventory (duplicate_leakage_audit samples split=train), "
                "folder domain/level cross-checked with dataset_validation; TEST metadata only from W1 audit",
    "ground_truth": "Original folder label: Level04=Normal; Level01/Level02/Level03=Anomaly",
    "domain": "Original folder domain (DEC-W2-D3-003); text-domain conflicts flagged, never reassigned",
    "strata_order": [d for d, _ in STRATA], "class_order": ["Normal", "Anomaly"],
    "quota_per_class": {d: q for d, q in STRATA}, "primary_domains": list(PRIMARY),
    "ranking": "ascending SHA-256(seed + '|' + sample_id) hex digest, sample_id tie-break",
    "level03_floor": "Anomaly stratum first takes up to min(2, quota) eligible Level03 by rank, "
                     "then fills the quota from all remaining eligible Anomaly by rank",
    "dependency": "At most one image per mandatory group across the cohort: transitive TRAIN exact-byte "
                  "duplicates, Normal point IDs and same-point-folder sequence pairs (cohort.candidate_groups)",
    "exclusions": "TRAIN IDs in W1 confirmed cross-split exact-byte pairs with TEST",
    "recorded_not_excluded": "Unresolved near-duplicate/source-family candidate links, prior aggregate/per-sample "
                             "exposure and folder/text domain conflicts",
    "shortage": "STOP with exact shortages and no selected IDs; no redistribution, lower N, new seed or relaxed rule",
    "inference_order": "ascending SHA-256(seed + '|order|' + sample_id), so a partial run is not domain-ordered",
    "model_output_input": False,
}


def rank(sample_id):
    return hashlib.sha256((SEED + "|" + sample_id).encode()).hexdigest(), sample_id


def order_key(sample_id):
    return hashlib.sha256((SEED + "|order|" + sample_id).encode()).hexdigest(), sample_id


def binary(level):
    return "Normal" if level == "Level04" else "Anomaly"


def select(candidates, excluded):
    """Pure predeclared selection; candidates carry no score or model output."""
    ids = [c["sample_id"] for c in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("DUPLICATE_CANDIDATE_ID")
    domains = {d for d, _ in STRATA}
    for c in candidates:
        if set(c) != {"sample_id", "domain", "level", "group"} or c["level"] not in LEVELS or c["domain"] not in domains:
            raise ValueError("CANDIDATE_SCHEMA")
        if type(c["group"]) is not str or not c["group"]:
            raise ValueError("MANDATORY_GROUP_REQUIRED")
    excluded = set(excluded)
    if not excluded <= set(ids):
        raise ValueError("EXCLUSION_OUTSIDE_INVENTORY")
    used, selected, trace, shortages = set(), [], {}, {}
    for domain, quota in STRATA:
        for label in ("Normal", "Anomaly"):
            pool = sorted((c for c in candidates if c["domain"] == domain and binary(c["level"]) == label
                           and c["sample_id"] not in excluded), key=lambda c: rank(c["sample_id"]))
            chosen = []

            def take(rows, limit):
                for c in rows:
                    if len(chosen) >= limit:
                        return
                    if c["group"] not in used:
                        used.add(c["group"])
                        chosen.append(c)

            if label == "Anomaly":
                take([c for c in pool if c["level"] == "Level03"], min(LEVEL03_FLOOR, quota))
            take(pool, quota)
            key = domain + "/" + label
            trace[key] = {"quota": quota, "eligible_images": len(pool),
                          "eligible_mandatory_groups": len({c["group"] for c in pool}),
                          "eligible_level_counts": {k: sum(c["level"] == k for c in pool) for k in LEVELS},
                          "selected": len(chosen),
                          "selected_level_counts": {k: sum(c["level"] == k for c in chosen) for k in LEVELS}}
            if len(chosen) < quota:
                shortages[key] = quota - len(chosen)
            selected.extend(c["sample_id"] for c in chosen)
    if shortages:
        return {"status": "STOP_INSUFFICIENT_ELIGIBLE_GROUPS", "seed": SEED, "shortages": shortages,
                "trace": trace, "selected_ids": [], "inference_order": [], "execution_authority": False}
    return {"status": "SELECTED", "seed": SEED, "shortages": {}, "trace": trace, "selected_ids": selected,
            "inference_order": sorted(selected, key=order_key), "execution_authority": False}


def validate_inference(value):
    if (type(value) is not dict or set(value) != {"schema", "run_id", "split", "seed", "locator_root", "order_rule", "samples"}
            or value["schema"] != "pa3-seminar-direction-inference-v1" or value["run_id"] != RUN_ID
            or value["split"] != "TRAIN" or value["seed"] != SEED or value["order_rule"] != RULE["inference_order"]):
        raise ValueError("INFERENCE_MANIFEST_SCHEMA")
    samples = value["samples"]
    if type(samples) is not list or len(samples) != PLANNED:
        raise ValueError("EXACT_90_INFERENCE_SAMPLES_REQUIRED")
    for row in samples:
        if type(row) is not dict or set(row) != {"sample_id", "image_locator", "image_sha256"}:
            raise ValueError("INFERENCE_ROW_SCHEMA")
        match = LOCATOR.fullmatch(row["image_locator"]) if type(row["image_locator"]) is str else None
        if (type(row["sample_id"]) is not str or not SAMPLE_ID.fullmatch(row["sample_id"])
                or not match or match.group(1) != row["sample_id"]):
            raise ValueError("TRAIN_LOCATOR_REQUIRED")
        if type(row["image_sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", row["image_sha256"]):
            raise ValueError("IMAGE_SHA256_REQUIRED")
    ids = [r["sample_id"] for r in samples]
    if len(set(ids)) != PLANNED or len({r["image_locator"] for r in samples}) != PLANNED:
        raise ValueError("DUPLICATE_INFERENCE_SAMPLE")
    if ids != sorted(ids, key=order_key):
        raise ValueError("PREDECLARED_INFERENCE_ORDER_REQUIRED")
    return [dict(r) for r in samples]


def validate_cohort(value, inference_bytes):
    """Internal consistency of the committed GT/relations manifest."""
    inference = validate_inference(strict_json(inference_bytes))
    keys = {"schema", "run_id", "status", "scope", "split", "seed", "rule", "inputs", "exclusions",
            "selection", "inference_manifest", "inference_manifest_sha256", "samples",
            "exposure_reservation", "limitations", "execution_authority"}
    if (type(value) is not dict or set(value) != keys or value["schema"] != "pa3-seminar-direction-cohort-v1"
            or value["run_id"] != RUN_ID or value["split"] != "TRAIN" or value["seed"] != SEED
            or value["rule"] != RULE or value["execution_authority"] is not False
            or value["inference_manifest"] != INFERENCE
            or value["inference_manifest_sha256"] != hashlib.sha256(inference_bytes).hexdigest()):
        raise ValueError("COHORT_MANIFEST_SCHEMA_OR_BINDING")
    samples = value["samples"]
    if [{k: r[k] for k in ("sample_id", "image_locator", "image_sha256")} for r in samples] != inference:
        raise ValueError("COHORT_INFERENCE_PROJECTION_MISMATCH")
    if sorted(value["selection"]["selected_ids"]) != sorted(r["sample_id"] for r in samples):
        raise ValueError("COHORT_SELECTION_MISMATCH")
    excluded = set(value["exclusions"]["exact_test_duplicate_train_ids"])
    groups = [r["mandatory_group"] for r in samples]
    if len(set(groups)) != len(groups) or excluded & {r["sample_id"] for r in samples}:
        raise ValueError("DEPENDENCY_OR_EXCLUSION_VIOLATION")
    counts = {}
    for r in samples:
        if (r["level"] not in LEVELS or r["binary_class"] != binary(r["level"])
                or not r["sample_id"].startswith(r["domain"] + "-" + r["level"] + "-")
                or r["primary"] != (r["domain"] in PRIMARY)
                or any(type(r[k]) is not str or not r[k] for k in ("mandatory_group", "conservative_component"))):
            raise ValueError("COHORT_SAMPLE_GT_SCHEMA")
        key = (r["domain"], r["binary_class"])
        counts[key] = counts.get(key, 0) + 1
    if counts != {(d, c): q for d, q in STRATA for c in ("Normal", "Anomaly")}:
        raise ValueError("COHORT_QUOTA_MISMATCH")
    return {r["sample_id"]: r for r in samples}


def _bound(repo, settings, name, key):
    value = access.require(MODE, settings, repo)  # precedes every path read
    data = (Path(repo) / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != value["grant"][key]:
        raise ValueError("DIAGNOSTIC_MANIFEST_CHECKSUM:" + key)
    return data


def inference_samples(repo, settings):
    """GT-free projection used by inference; hash bound by the reviewed grant."""
    return validate_inference(strict_json(_bound(repo, settings, INFERENCE, "inference_manifest_sha256")))


def load_cohort(repo, cohort_sha256, inference_sha256):
    """Committed metadata only (no image); exact bytes named by a sealed header or receipt."""
    data = {}
    for name, expected in ((COHORT, cohort_sha256), (INFERENCE, inference_sha256)):
        data[name] = (Path(repo) / name).read_bytes()
        if hashlib.sha256(data[name]).hexdigest() != expected:
            raise ValueError("DIAGNOSTIC_MANIFEST_CHECKSUM:" + name)
    return validate_cohort(strict_json(data[COHORT]), data[INFERENCE])


def evaluation_metadata(repo, settings):
    """Post-seal GT join only: the run workflow calls this after sealing raw output."""
    grant = access.require(MODE, settings, repo)["grant"]
    return load_cohort(repo, grant["cohort_manifest_sha256"], grant["inference_manifest_sha256"])


def dataset_root(settings, inputs):
    value = settings["dataset_input"]
    if any(part.lower() == "test" for part in PurePosixPath(value).parts):
        raise PermissionError("TEST_ATTACHMENT_ROOT_FORBIDDEN")
    return attached_path(inputs, value)


def preflight_dataset(repo, settings, inputs):
    """Existence + byte SHA-256 of all 90 before model load; nothing is decoded."""
    samples = inference_samples(repo, settings)
    root = dataset_root(settings, inputs)
    rows = []
    for row in samples:
        path = safe_path(root, row["image_locator"])
        if not path.is_file():
            raise ValueError("DIAGNOSTIC_IMAGE_MISSING:" + row["sample_id"])
        if digest(path) != row["image_sha256"]:
            raise ValueError("DIAGNOSTIC_IMAGE_CHECKSUM:" + row["sample_id"])
        rows.append({"sample_id": row["sample_id"], "image_sha256": row["image_sha256"],
                     "size_bytes": path.stat().st_size})
    return {"planned": len(samples), "verified": len(rows), "decoded": False, "rows": rows}


def open_image(repo, settings, row, inputs):
    if row not in inference_samples(repo, settings):
        raise PermissionError("IMAGE_OUTSIDE_DIAGNOSTIC_MANIFEST")
    # open_sample rejects aliases/escapes and re-hashes bytes before decoding.
    return open_sample(row, dataset_root(settings, inputs))


def verify_prior(repo, settings, inputs, tokenizer):
    """CPU recompute the sealed four-image technical run against its own source."""
    from . import pilot
    grant = access.require(MODE, settings, repo)["grant"]
    commit = access.DIAGNOSTIC["technical_source_commit"]
    bundle = attached_path(inputs, settings["technical_source_bundle_input"])
    if digest(bundle) != grant["technical_source_bundle_sha256"]:
        raise ValueError("TECHNICAL_SOURCE_BUNDLE_CHECKSUM")
    technical_repo = run_path(repo, settings["run_id"]).parent / (settings["run_id"] + "-technical-source")
    if not technical_repo.exists():
        subprocess.run(["git", "-c", "core.autocrlf=false", "clone", "--no-checkout",
                        str(bundle), str(technical_repo)], check=True)
        subprocess.run(["git", "-C", str(technical_repo), "-c", "core.autocrlf=false",
                        "checkout", "--detach", commit], check=True)
    prior_root = attached_path(inputs, settings["technical_run_input"])
    if Journal(prior_root).read("manifest")["source"]["source_commit"] != commit:
        raise ValueError("TECHNICAL_SOURCE_COMMIT_MISMATCH")
    return pilot.prior_technical(prior_root, technical_repo, tokenizer, grant["technical_seal_sha256"])
