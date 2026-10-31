"""Separate PREP release for the two reviewed adapters; no import-time enrollment.

Private approvals are externally reviewed records, not cryptographic signatures.
The public preparation contract deliberately contains no execution grant/thresholds.
"""
from contextlib import contextmanager
from collections import Counter
from copy import deepcopy
from pathlib import Path
import re
import math
import time

from safeshift.pilot import contract as pilot
from safeshift.pilot.artifacts import read, safe, sha
from .source import ROOT, LOCK, require

BASE = "95eb4e8801ea746e1a760b9d529920bffb3c26cb"
PACKAGE_BASE = "fc1e454212455685e1775601ebfd6aab9535c932"
MANIFEST = "f1ec6a202c3bba05d91cb3c507d5aa16d9aa3ded2418fa84bd62e77c05522995"
INVENTORY = "0a8a84e726e690622de311326680ecbbc4a04fa04a0a45ff14ff96412caae427"
KEYS = ("internvl35", "minicpm4")
BATCH_CONDITIONS = ["all_durable_results_recover_exactly", "no_technical_or_nonfinite_output",
                    "all_behavior_limits_pass", "approved_support_at_early_and_later_reviews",
                    "live_resource_limits_pass", "grant_and_deadline_current"]


def approval_ref(value):
    return (isinstance(value, str) and bool(value.strip())
            and value.strip().upper() not in ("PENDING", "UNAPPROVED", "BLOCKED", "NULL", "NONE"))


def batch_check(g):
    """An optional, explicit delegation. Legacy grants retain external review.

This validates an externally supplied record; it does not authenticate its author
or confer approval. The Owner must verify the cited Lead decision independently.
"""
    from .train_owner import SCHEMA, MODE, validate
    from . import train_history as history
    if g.get("schema") == history.SCHEMA:
        history.validate(g, g["model_key"], g["source_sha256"], g["runtime_ref"])
        return MODE
    if g.get("schema") == SCHEMA:
        validate(g, g["model_key"], g["source_sha256"], g["runtime_ref"])
        return MODE
    mode = g["policy"].get("review_mode", "EXTERNAL")
    require(mode in ("EXTERNAL", "PREAPPROVED_BATCH"), "REVIEW_MODE_REQUIRED")
    if mode == "EXTERNAL":
        require(g.get("batch_authorization") is None, "BATCH_AUTHORITY_WITH_EXTERNAL_MODE")
        return mode
    b = g.get("batch_authorization")
    require(type(b) is dict and b.get("schema") == "safeshift-candidate160-batch-authorization-v1",
            "BLOCKED_BATCH_NOT_APPROVED")
    require(b.get("allow_automatic_continuation") is True
            and approval_ref(b.get("research_lead_approval_ref")), "EXPLICIT_RESEARCH_LEAD_BATCH_APPROVAL_REQUIRED")
    require(b.get("policy_sha256") == pilot.digest(g["policy"])
            and b.get("execution_binding_sha256") == pilot.digest(execution_binding(g)), "BATCH_APPROVAL_BINDING")
    require(b.get("conditions") == BATCH_CONDITIONS, "EXPLICIT_BATCH_CONDITIONS_REQUIRED")
    require(1 in g["policy"]["review_after"], "BATCH_FIRST_IMAGE_REVIEW_REQUIRED")
    return mode


def model(key):
    require(key in KEYS, "ONLY_TWO_REVIEWED_CANDIDATES")
    spec = read(LOCK)[key]
    return {"id": spec["id"], "revision": spec["revision"],
            "transformers": "4.55.4" if key == "internvl35" else "4.51.3",
            "attention": "eager", "remote_code": key == "minicpm4"}


@contextmanager
def enrollment(key):
    """Process-local transport registration, restored on every exit.

The legacy executable/grant/notebook sources remain byte-identical. The shared
runner uses its existing settings/identity/parser/raw/HNLO paths with the actual
candidate identity. No grant from that legacy contract is accepted here.
"""
    require(key not in pilot.MODELS, "CANDIDATE_ALREADY_ENROLLED")
    pilot.MODELS[key] = model(key)
    try:
        yield
    finally:
        del pilot.MODELS[key]


def legacy_transport_snapshot(key):
    """Exact frozen runner descriptor, NOT effective candidate processing/selection."""
    if key in pilot.MODELS:
        require(pilot.MODELS[key] == model(key), "LEGACY_TRANSPORT_MODEL_DRIFT")
        return deepcopy(pilot.settings(key))
    with enrollment(key):
        return deepcopy(pilot.settings(key))


def config(key):
    transport = legacy_transport_snapshot(key)
    internvl = key == "internvl35"
    return {"schema": "safeshift-candidate160-config-v2",
            "legacy_transport_compatibility": {
                "scope": "HISTORICAL_DESCRIPTORS_ONLY_NOT_EFFECTIVE_PROCESSING_OR_SELECTION",
                "settings_snapshot": transport,
                "legacy_transport_config_sha256": pilot.digest(transport),
                "legacy_runner_hash_field": "identity.config_sha256",
                "native_step_origin_scope": "generic hooked-module descriptor; use effective_candidate.logits below"},
            "effective_candidate": {
                "base": BASE, "model_key": key, "model": model(key),
                "adapter": "safeshift.candidates.backend.CandidateBackend",
                "preprocessing": {
                    "decode": "PIL content decode; still image; RGB conversion",
                    "entrypoint": "safeshift.candidates.inputs.prepare_inputs",
                    "implementation": ("native HF InternVLProcessor template and image tiling" if internvl else
                        "MiniCPM native slicing/resize/normalization/patch packing with explicit RGB channels-last"),
                    "image_entrypoint": ("processor(text=rendered, images=image, return_tensors=pt)" if internvl else
                        "minicpm_image.rgb_image_inputs -> processor._convert_images_texts_to_inputs"),
                    "input_validation": "safeshift.candidates.inputs.validate_inputs unchanged"},
                "logits": {"boundary": "internvl_outer" if internvl else "minicpm_llm_forward",
                           "hook_target": "model" if internvl else "model.llm",
                           "timing": "forward output before generation logits processors",
                           "hnlo_replay": "safeshift.pilot.hnlo.replay unchanged"},
                "sequence_semantics": "prompt_plus_continuation" if internvl else "continuation_only_inputs_embeds",
                "generation": {
                    "frozen_overrides": deepcopy(pilot.GENERATION), "prompt_sha256": pilot.PROMPT_SHA,
                    "entrypoint": ("model.generate" if internvl else
                                   "model.generate(decode_text=False, stream=False) -> _decode -> llm.generate"),
                    "native_special_tokens": "pinned native GenerationConfig; effective IDs saved in request.json",
                    "repetition_penalty": 1.0},
                "selection": {"method": "reuse exact historical manifest bytes/order; no selector or new seed",
                              "manifest_sha256": MANIFEST, "max_native_calls": 160},
                "dtype": "float16", "attention": "eager", "quantization": None, "batch_size": 1,
                "placement": "cuda:0 only; second physical T4 observed, never pooled",
                "python": "3.11.9", "cuda_build": "12.4",
                "requirements_sha256": sha(ROOT / f"configs/candidate160/{key}.requirements.txt"),
                "adapter_source_sha256": {name: sha(ROOT / "safeshift/candidates" / name)
                                           for name in ("backend.py", "inputs.py", "loading.py", "minicpm_image.py")},
                "checkpoint_lock_sha256": sha(LOCK.with_name("checkpoint_metadata_lock.json")),
                "public_source_lock_sha256": sha(LOCK)}}


def configuration_hashes(key):
    """Two different scopes. Never substitute one digest for the other."""
    return {"legacy_transport_config_sha256": pilot.digest(legacy_transport_snapshot(key)),
            "candidate_execution_config_sha256": pilot.digest(config(key))}


def validate_configuration_hashes(value, key):
    require("config_sha256" not in value, "AMBIGUOUS_CANDIDATE_CONFIG_HASH_FORBIDDEN")
    for name, expected in configuration_hashes(key).items():
        require(value.get(name) == expected, "CONFIGURATION_HASH_BINDING:" + name)


def execution_binding(grant):
    validate_configuration_hashes(grant, grant["model_key"])
    require(grant["model"] == model(grant["model_key"]), "EXECUTION_MODEL_BINDING")
    return deepcopy({name: grant[name] for name in (
        "model_key", "model", "legacy_transport_config_sha256", "candidate_execution_config_sha256",
        "source_sha256", "runtime_ref", "base", "attempt_id", "run_id", "manifest_sha256")})


def sources(repo=ROOT):
    repo = Path(repo)
    return sorted(set(pilot.source_files(repo) + [
        p.relative_to(repo).as_posix()
        for folder in ("safeshift/candidates", "configs/cpu_g2_g3", "configs/candidate160")
        for p in (repo / folder).rglob("*") if p.is_file() and p.suffix in (".py", ".json", ".txt")]))


def source_hash(repo=ROOT):
    return pilot.digest({p: sha(Path(repo) / p) for p in sources(repo)})


def policy_check(p):
    from .train_owner import MODE, policy
    if type(p) is dict and p.get("review_mode") == MODE:
        require(p == policy(), "OWNER_TECHNICAL_POLICY_DRIFT")
        return p
    require(type(p) is dict, "APPROVED_STOP_POLICY_REQUIRED")
    for n in ("early_behavior_after", "invalid_max_count", "repeat_max_count",
              "dominance_min_valid", "normal_min_support", "anomaly_min_support"):
        require(type(p.get(n)) is int and 0 <= p[n] <= 160, "POLICY_INTEGER:" + n)
    require(2 <= p["early_behavior_after"] < 160, "EARLY_REVIEW_WITHIN_160")
    require(p["repeat_max_count"] >= 1 and p["dominance_min_valid"] >= 1
            and p["normal_min_support"] >= 1 and p["anomaly_min_support"] >= 1, "POLICY_SUPPORT")
    for n in ("dominance_max_fraction", "normal_fpr_max", "anomaly_fnr_max"):
        require(type(p.get(n)) in (int, float) and 0 <= p[n] <= 1, "POLICY_FRACTION:" + n)
    reviews = p.get("review_after")
    require(type(reviews) is list and all(type(n) is int and 1 <= n < 160 for n in reviews)
            and reviews == sorted(set(reviews)) and p["early_behavior_after"] in reviews,
            "EARLY_RESEARCH_LEAD_REVIEW_REQUIRED")
    require(type(p.get("review_wait_seconds")) is int and p["review_wait_seconds"] >= 0,
            "APPROVED_REVIEW_WAIT_REQUIRED")
    require(type(p.get("driver_versions")) is list and p["driver_versions"]
            and all(isinstance(v, str) and re.fullmatch(r"[0-9]+(?:\.[0-9]+)+", v)
                    for v in p["driver_versions"]), "APPROVED_DRIVER_ALLOWLIST_REQUIRED")
    require(type(p.get("free_mib_per_gpu")) is list and len(p["free_mib_per_gpu"]) == 2
            and all(type(n) is int and n > 0 for n in p["free_mib_per_gpu"]), "PER_GPU_ADMISSION_REQUIRED")
    for n in ("free_ram_mib", "free_scratch_mib", "free_output_mib", "free_gpu0_runtime_mib"):
        require(type(p.get(n)) is int and p[n] > 0, "LIVE_RESOURCE_LIMIT_REQUIRED:" + n)
    return p


def authorize(g, key, source, ref, ledger, now=None):
    from .train_owner import SCHEMA, validate
    from . import train_history as history
    if type(g) is dict and g.get("schema") == history.SCHEMA:
        require(ledger is None, "OWNER_EXECUTION_IS_NOT_AN_EXTERNAL_GRANT")
        return history.validate(g, key, source, ref, now=now)
    if type(g) is dict and g.get("schema") == SCHEMA:
        require(ledger is None, "OWNER_EXECUTION_IS_NOT_AN_EXTERNAL_GRANT")
        return validate(g, key, source, ref, now=now)
    require(type(g) is dict and g.get("schema") == "safeshift-candidate160-grant-v2",
            "BLOCKED_NO_NEW_CANDIDATE_GRANT")
    validate_configuration_hashes(g, key)
    expected = {"model_key": key, "model": model(key), "source_sha256": source,
                "runtime_ref": ref, "base": BASE, "manifest_sha256": MANIFEST,
                "inventory_sha256": INVENTORY, **configuration_hashes(key),
                "data_revision": pilot.DATA_REVISION, "master_sha256": pilot.MASTER_SHA,
                "split": "TRAIN", "max_initial_ids": 160, "max_native_calls": 160,
                "retry_sample_ids": [], "resume": False}
    for n, value in expected.items():
        require(type(g.get(n)) is type(value) and g[n] == value, "GRANT_BINDING:" + n)
    for n in ("G0", "T0", "O3", "code_review_ref", "manifest_review_ref", "policy_approval_ref",
              "runtime_approval_ref", "external_ledger_ref", "owner_approval_ref", "research_lead_review_ref"):
        require(approval_ref(g.get(n)), "APPROVAL_REQUIRED:" + n)
    for n in ("allow_train_images", "allow_folder_gt", "allow_checkpoint_read", "allow_gpu",
              "allow_raw_export", "allow_software_install", "private_custody_approved"):
        require(g.get(n) is True, "EXPLICIT_PERMISSION:" + n)
    for n in ("run_id", "attempt_id"):
        require(isinstance(g.get(n), str) and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", g[n]), "IDENTITY:" + n)
    require(type(g.get("max_seconds")) is int and 0 < g["max_seconds"] <= 43200, "TIME_CAP_REQUIRED")
    now = time.time() if now is None else now
    require(type(g.get("expires_unix")) in (int, float) and math.isfinite(g["expires_unix"])
            and now < g["expires_unix"], "EXPIRED_GRANT")
    policy_check(g.get("policy"))
    batch_check(g)
    require(type(ledger) is dict and ledger == {
        "schema": "safeshift-candidate160-reservation-v1", "status": "RESERVED_NOT_EXECUTED",
        "attempt_id": g["attempt_id"], "run_id": g["run_id"], "model_key": key,
        "grant_sha256": pilot.digest(g), "source_sha256": source, "runtime_ref": ref,
        "manifest_sha256": MANIFEST, "expires_unix": g["expires_unix"],
        "external_ledger_ref": g["external_ledger_ref"]}, "EXACT_FRESH_EXTERNAL_RESERVATION_REQUIRED")
    return g


def manifest(bundle):
    """Read only after fresh scope approval; never run select_main/load_bundle.

Exact historical manifest bytes authenticate membership AND order. No inventory,
master, annotation or TEST reads are needed to select or reconstruct this cohort.
"""
    path = safe(bundle, "pilot_manifest.json")
    require(sha(path) == MANIFEST, "HISTORICAL_160_MANIFEST_BYTES_REQUIRED")
    plan = read(path)
    rows = plan["main"]
    require(plan["split"] == "TRAIN" and plan["mode"] == "PILOT"
            and plan["master_sha256"] == pilot.MASTER_SHA and plan["data_revision"] == pilot.DATA_REVISION
            and plan["dimension_inventory_sha256"] == INVENTORY and not plan["supplement"]
            and not plan["qwen_verified"] and len(rows) == len({r["sample_id"] for r in rows}) == 160
            and Counter(r["level"] for r in rows) == pilot.QUOTAS, "EXACT_ORIGINAL_TRAIN_160_REQUIRED")
    for i, row in enumerate(rows):
        require(row["image"] == f"images/{i:06d}.jpg", "MANIFEST_ORDER")
    return plan, rows
