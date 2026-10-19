"""Fresh, source-bound pilot authority. Historical grants never authorize this scope."""
from copy import deepcopy
from datetime import datetime
import re

from ..one_click.contract import MODELS

BASE_SHA = "6d345fe11426a3c01815439081dca0a8983dd33c"
AUTHORITY = "configs/diagnostics/resource_pilot_authority.v3.json"
LOCK = "configs/diagnostics/resource_pilot_source.v3.json"
EVIDENCE = "BASELINE_SUFFICIENT_RAW_SUMMARIES_V1_PROPOSED"
FLAGS = ("train_image_read_approved", "provisioning_approved", "gpu_inference_approved",
         "descriptive_train_exception_approved", "evidence_contract_approved",
         "raw_provenance_approved", "artifact_retention_approved", "security_boundary_approved",
         "local_peer_relay_risk_accepted", "resource_and_interruption_risk_accepted",
         "cross_session_attempt_ledger_approved", "exposure_overlap_policy_approved")


def unit(model):
    if model not in MODELS:
        raise ValueError("EXACT_PILOT_MODEL_REQUIRED")
    return {"model": model, **deepcopy(MODELS[model]), "shard": 0, "ordinals": list(range(8)),
            "count": 8, "run_id": f"hnlo-pilot8-v3-{model}-s0-a1",
            "attempt_id": f"resource-pilot8-v3-{model}-20261019-a1",
            "max_attempts": 1, "max_loads": 1, "max_generate_calls": 8}


def template():
    from .cohort import SHARD_SHA, IMAGE_SHA256
    return {"schema": "resource-pilot8-authority-v1", "base_sha": BASE_SHA,
        "scope": {"decision": "DEC-PA3-017", "split": "TRAIN", "shard0_sha256": SHARD_SHA,
            "image_sha256_in_ordinal_order": list(IMAGE_SHA256), "units": [unit(m) for m in ("qwen3", "internvl3")], "labels_or_gt_access": False,
            "test_access": False, "worker_identity": "ORDINAL_HASH_ONLY", "prompt": "C1",
            "prompt_sha256": "816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3",
            "do_sample": False, "max_new_tokens": 32, "batch_size": 1,
            "clamp": None, "calibration": False, "retry": False, "resume": False,
            "forced_prefix": False, "stop_on_any_sample_failure": True,
            "evidence_contract": EVIDENCE, "full_vocab_replay": False,
            "max_worker_seconds": 3600, "exposure_policy": "RECORD_ALL_STAGING_AND_MODEL_ATTEMPTS_NO_BASELINE_DISPOSITION"},
        "grant": None}


def authorize(value, source, model):
    from .bootstrap import canonical
    if canonical({**value, "grant": None}) != canonical(template()):
        raise PermissionError("EXACT_NEW_PILOT_SCOPE_REQUIRED")
    g = value.get("grant")
    fields = {"approved_by", "role", "approved_utc", "decision_url", "independent_audit_url",
              "implementation_commit", "source_payload_sha256", "units"}
    if type(g) is not dict or set(g) != fields:
        raise PermissionError("NEW_PILOT_GRANT_REQUIRED")
    if g["role"] != "Research Lead" or not isinstance(g["approved_by"], str) or not g["approved_by"].strip():
        raise PermissionError("RESEARCH_LEAD_REQUIRED")
    try:
        datetime.strptime(g["approved_utc"], "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        raise PermissionError("VALID_APPROVAL_TIME_REQUIRED") from None
    if (g["implementation_commit"] != source["implementation_commit"]
            or g["source_payload_sha256"] != source["payload_sha256"]):
        raise PermissionError("PILOT_SOURCE_BINDING_MISMATCH")
    for key in ("decision_url", "independent_audit_url"):
        match = re.fullmatch(r"https://github.com/tantdna2/SafeShift/pull/(\d+)#[-a-zA-Z0-9]+", str(g[key]))
        if not match or int(match[1]) != source["pr_number"] or int(match[1]) <= 119:
            raise PermissionError("THIS_PILOT_PR_DECISION_AND_AUDIT_REQUIRED")
    if type(g["units"]) is not list or not 1 <= len(g["units"]) <= 2:
        raise PermissionError("EXPLICIT_MODEL_GRANTS_REQUIRED")
    seen, selected = set(), None
    for entry in g["units"]:
        if type(entry) is not dict or set(entry) != {"unit", "approvals"}:
            raise PermissionError("EXACT_MODEL_GRANT_REQUIRED")
        u = entry["unit"]
        if type(u) is not dict or canonical(u) != canonical(unit(u.get("model"))) or u["model"] in seen:
            raise PermissionError("CHANGED_OR_DUPLICATE_UNIT")
        seen.add(u["model"])
        if (type(entry["approvals"]) is not dict or set(entry["approvals"]) != set(FLAGS)
                or any(entry["approvals"][k] is not True for k in FLAGS)):
            raise PermissionError("ALL_PILOT_APPROVALS_REQUIRED")
        if u["model"] == model:
            selected = entry
    if selected is None:
        raise PermissionError("MODEL_NOT_GRANTED")
    return deepcopy(selected)
