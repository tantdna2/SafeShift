"""Proposed pilot contract, independent of locked Seminar M2 and old grants."""
import hashlib
import json
import re
from pathlib import Path

LEVELS = ("Level01", "Level02", "Level03", "Level04")
DOMAINS = ("coal_conveyor", "oil_chemical", "power", "tunnel", "metallurgy")
QUOTAS = {"Level01": 48, "Level02": 24, "Level03": 8, "Level04": 80}
SEED = "safeshift-three-vlm-pilot-20261027-v1"
LEGACY = "31a04e6f7175cca818c63b4de0153246b3f3ecdb"
MASTER_PATH = "data/manifests/pa3_full_train.v1.json"
MASTER_SHA = "a35e91fb431752dbf3b6c161f227d953d5748d69ef9f39aef613019faca33008"
DATA_REVISION = "f3cb7d3e7827c1afc1c5bfd0524257984bba46ab"
PROMPT_SHA = "816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3"
MODELS = {
    "gemma": {"id": "google/gemma-3-4b-it", "revision": "093f9f388b31de276ce2de164bdc2081324b9767",
              "transformers": "4.51.3", "attention": "eager", "remote_code": False},
    "phi": {"id": "microsoft/Phi-3.5-vision-instruct", "revision": "12b77fb40b63a2c73c68243d3f767aab688a1b2a",
            "transformers": "4.43.3", "attention": "eager", "remote_code": True},
    "smolvlm2": {"id": "HuggingFaceTB/SmolVLM2-2.2B-Instruct", "revision": "482adb537c021c86670beed01cd58990d01e72e4",
                 "transformers": "4.51.3", "attention": "eager", "remote_code": False},
}
GENERATION = {"do_sample": False, "num_beams": 1, "max_new_tokens": 64,
              "use_cache": True, "return_dict_in_generate": True,
              "output_scores": False, "output_logits": False}
# Numerical operational proposals; applying them requires exact grant approval.
THRESHOLDS = {"valid_rate_min": 0.98, "normal_fpr_red_flag": 0.95,
              "anomaly_fnr_red_flag": 0.95, "fnr_go_max": 0.20,
              "fpr_go_max": 0.50, "macro_f1_go_min": 0.40}
STATUSES = ("SUCCESS", "INVALID", "TECHNICAL_ERROR", "NOT_ATTEMPTED")
HNLO_STATUSES = ("HNLO_VALIDATED", "RAW_LOGITS_AVAILABLE_BUT_UNALIGNED", "HNLO_INCOMPATIBLE",
                 "HNLO_TECHNICAL_FAILURE", "HNLO_UNVERIFIED")


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def require_hash(value):
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value):
        raise ValueError("SHA256_REQUIRED")
    return value


def parse_label(raw):
    """Exact C1 JSON only. No regex rescue, alias, extra key or duplicate key."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("DUPLICATE_KEY")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        if type(value) is dict and set(value) == {"safety_level"} and value["safety_level"] in LEVELS:
            return value["safety_level"]
    except (ValueError, TypeError):
        pass
    return None


def settings(key):
    return {"contract": "three-vlm-train-v1", "model": MODELS[key], "dtype": "float16",
            "placement": "cuda:0", "quantization": None, "batch_size": 1,
            "generation_seed": None, "selection_seed": SEED,
            "generation": GENERATION, "prompt_sha256": PROMPT_SHA,
            "preprocessing": "pinned_native_unchanged; phi single-image num_crops=16",
            "hnlo": "passive_outer_forward_four_logits_single_branch_v1"}


def source_files(repo):
    repo = Path(repo)
    return sorted(["safeshift/__init__.py"] + [p.relative_to(repo).as_posix()
                  for folder in ("safeshift/pilot", "configs/pilot")
                  for p in (repo / folder).rglob("*") if p.is_file() and p.suffix in (".py", ".json", ".txt")])


def source_digest(repo):
    return digest({p: hashlib.sha256((Path(repo) / p).read_bytes()).hexdigest() for p in source_files(repo)})


def authorize(grant, *, model, mode, source_hash, manifest_hash, count, parent=None):
    """An external reviewed grant is evidence of scope, not a self-issued approval.

    Human approval/source audit and the external attempt ledger remain mandatory.
    Notebook never reads mode from a grant: its mode argument is always PILOT.
    """
    if not isinstance(grant, dict) or grant.get("schema") != "safeshift-pilot-grant-v1":
        raise PermissionError("BLOCKED_NO_NEW_REVIEWED_GRANT")
    if mode not in ("PILOT", "FULL_TRAIN") or grant.get("mode") != mode:
        raise PermissionError("EXACT_MODE_GRANT_REQUIRED")
    refs = ("owner_approval_ref", "research_lead_review_ref", "chatgpt_code_review_ref", "external_ledger_ref")
    if any(not isinstance(grant.get(k), str) or not grant[k].strip() for k in refs):
        raise PermissionError("APPROVAL_REVIEW_LEDGER_REQUIRED")
    for k, v in {"model_key": model, "source_sha256": source_hash, "manifest_sha256": manifest_hash,
                 "config_sha256": digest(settings(model)), "thresholds": THRESHOLDS,
                 "max_initial_ids": count, "split": "TRAIN", "data_revision": DATA_REVISION,
                 "master_sha256": MASTER_SHA}.items():
        if type(grant.get(k)) is not type(v) or grant[k] != v:
            raise PermissionError("GRANT_BINDING:" + k)
    if any(grant.get(k) is not True for k in ("allow_train_images", "allow_folder_gt", "allow_model_download",
                                            "allow_gpu", "allow_raw_export", "approve_thresholds")):
        raise PermissionError("EXPLICIT_DATA_MODEL_GPU_EXPORT_SCOPE_REQUIRED")
    if mode == "PILOT" and not 160 <= count <= 180:
        raise PermissionError("PILOT_160_PLUS_AT_MOST_20_REQUIRED")
    if mode == "FULL_TRAIN":
        if (count != 3763 or grant.get("full_train_explicit") is not True
                or not grant.get("pilot_review_ref") or grant.get("pilot_recommendation") != "GO_FULL_TRAIN_RECOMMENDED"
                or grant.get("hnlo_disposition") not in ("VALIDATED", "CLASSIFICATION_ONLY_ACCEPTED")):
            raise PermissionError("FULL_TRAIN_LOCKED_PENDING_SEPARATE_PILOT_REVIEW_AND_OWNER_GRANT")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", grant.get("run_id", "")):
        raise PermissionError("RUN_ID_REQUIRED")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", grant.get("attempt_id", "")):
        raise PermissionError("NEW_ATTEMPT_ID_REQUIRED")
    if type(grant.get("max_seconds")) is not int or not 60 <= grant["max_seconds"] <= 43200:
        raise PermissionError("EXPLICIT_TIME_CAP_REQUIRED")
    require_hash(source_hash)
    require_hash(manifest_hash)
    retries = grant.get("retry_sample_ids", [])
    if (type(retries) is not list or len(retries) != len(set(retries))
            or any(type(s) is not str for s in retries) or (retries and not grant.get("retry_approval_ref"))):
        raise PermissionError("SEPARATE_EXACT_RETRY_APPROVAL_REQUIRED")
    if parent:
        if (grant.get("resume_parent_archive_sha256") != parent
                or not grant.get("resume_approval_ref")):
            raise PermissionError("SEPARATE_ARCHIVE_RESUME_APPROVAL_REQUIRED")
    elif grant.get("resume_parent_archive_sha256"):
        raise PermissionError("RESUME_ARCHIVE_MISSING")
    return grant
