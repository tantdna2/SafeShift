"""Eight independently budgeted units, fresh source-bound authority, fail closed."""
from copy import deepcopy
from datetime import datetime
import re

from ..one_click.contract import MODELS
from .cohort import FULL_SHA, SHARD_SHA

BASE_SHA = "7dd96e083a8d409355062e6087624e306e4a5b2c"
BRANCH = "prep/hnlo-train-v4-20261019"
AUTHORITY = "configs/diagnostics/hnlo_train_authority.v4.json"
LOCK = "configs/diagnostics/hnlo_train_source.v4.json"
EVIDENCE = "BASELINE_SUFFICIENT_RAW_SUMMARIES_V1_PROPOSED"
FLAGS = ("train_image_read_approved", "provisioning_approved", "gpu_inference_approved",
         "descriptive_train_exception_approved", "evidence_contract_approved",
         "raw_provenance_approved", "artifact_retention_approved", "label_evaluation_approved",
         "security_boundary_approved", "local_peer_relay_risk_accepted",
         "resource_and_interruption_risk_accepted", "no_retry_cross_session_ledger_approved",
         "pilot_overlap_and_reexposure_approved", "cost_time_storage_approved")


def unit(model, shard):
    if model not in MODELS or type(shard) is not int or shard not in range(4):
        raise ValueError("EXACT_MODEL_AND_SHARD_REQUIRED")
    return {"model": model, **deepcopy(MODELS[model]), "shard": shard,
            "count": (941, 941, 941, 940)[shard],
            "run_id": f"hnlo-train-v4-{model}-s{shard}-a1",
            "attempt_id": f"hnlo-train-v4-{model}-s{shard}-20261019-a1",
            "inference_sha256": SHARD_SHA[shard], "max_attempts": 1, "max_loads": 1,
            "max_generate_calls": (941, 941, 941, 940)[shard]}


def scope():
    return {"decision": "DEC-PA3-018", "split": "TRAIN", "cohort_count": 3763,
            "pilot_exposure": {"release": "PR120_V3", "shard": 0, "ordinals": list(range(8)),
                "models": ["qwen3", "internvl3"], "status": "OWNER_REPORTED_8_OF_8_EACH",
                "policy": "KEEP_ALL_3763_NEW_BASELINE_CALLS_NO_PILOT_OUTPUT_REUSE",
                "new_staging_and_native_calls": "RECORD_EVERY_ATTEMPT"},
            "full_manifest_sha256": FULL_SHA, "test_access": False, "retry": False,
            "label_access": "CPU_ONLY_AFTER_RAW_CUSTODY_SEAL", "worker_identity": "ORDINAL_HASH_ONLY",
            "prompt_sha256": "816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3",
            "formula": "logsumexp(z01,z02,z03)-z04", "clamp": None,
            "evidence_contract": EVIDENCE, "max_new_tokens": 32, "batch_size": 1,
            "qwen3_runtime": "PR112_TWO_T4_CUDA128_EXPLICIT_EMBEDDING_CPU_V1",
            "qwen3_network": "PR112_SECCOMP_PLUS_PYTHON_DENIAL",
            "internvl3_runtime": "PR115_PR116_POST_GUARD_DRIVER_T4_GPU0_CUDA124",
            "internvl3_network": "PR116_AF_UNIX_MONITOR_PARTIAL_RELAY_UNOBSERVABLE",
            "driver_handles": "STRONG_REFERENCES_UNTIL_WORKER_EXIT",
            "do_sample": False, "seed": None, "threshold": None,
            "max_worker_seconds": 36000, "full_vocab_replay": False, "resume": False, "max_sample_evidence_bytes": 2 * 2**20,
            "scope": "DESCRIPTIVE_FULL_TRAIN", "units": [unit(m, s) for m in MODELS for s in range(4)]}


def template():
    return {"schema": "hnlo-full-train-authority-v1", "base_sha": BASE_SHA,
            "scope": scope(), "grant": None}


def authorize(value, source, model, shard):
    from .bootstrap import canonical
    if canonical({**value, "grant": None}) != canonical(template()):
        raise PermissionError("NEW_TRAIN_AUTHORITY_SCOPE_REQUIRED")
    grant = value.get("grant")
    fields = {"approved_by", "role", "approved_utc", "decision_url", "independent_audit_url",
              "implementation_commit", "source_payload_sha256", "units"}
    if type(grant) is not dict or set(grant) != fields:
        raise PermissionError("NEW_TRAIN_GRANT_REQUIRED")
    if grant["role"] != "Research Lead" or type(grant["approved_by"]) is not str or not grant["approved_by"].strip():
        raise PermissionError("RESEARCH_LEAD_REQUIRED")
    try:
        datetime.strptime(grant["approved_utc"], "%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        raise PermissionError("VALID_APPROVAL_UTC_REQUIRED") from None
    if (grant["implementation_commit"] != source["implementation_commit"]
            or grant["source_payload_sha256"] != source["payload_sha256"]):
        raise PermissionError("TRAIN_SOURCE_BINDING_MISMATCH")
    for key in ("decision_url", "independent_audit_url"):
        match = re.fullmatch(r"https://github.com/tantdna2/SafeShift/pull/(\d+)#[-a-zA-Z0-9]+", grant[key])
        if not match or int(match[1]) <= 120 or int(match[1]) != source["pr_number"]:
            raise PermissionError("FRESH_TRAIN_DECISION_AND_AUDIT_REQUIRED")
    if type(grant["units"]) is not list or not 1 <= len(grant["units"]) <= 8:
        raise PermissionError("EXPLICIT_UNIT_GRANTS_REQUIRED")
    selected, seen = None, set()
    for entry in grant["units"]:
        if type(entry) is not dict or set(entry) != {"unit", "approvals"}:
            raise PermissionError("EXACT_UNIT_GRANT_REQUIRED")
        u = entry["unit"]
        if type(u) is not dict:
            raise PermissionError("EXACT_UNIT_REQUIRED")
        expected = unit(u.get("model"), u.get("shard"))
        if canonical(u) != canonical(expected) or u["run_id"] in seen:
            raise PermissionError("UNIT_CHANGED_OR_DUPLICATE")
        seen.add(u["run_id"])
        if (set(entry["approvals"]) != set(FLAGS)
                or any(entry["approvals"][k] is not True for k in FLAGS)):
            raise PermissionError("ALL_UNIT_APPROVALS_REQUIRED")
        if (u["model"], u["shard"]) == (model, shard):
            selected = entry
    if selected is None:
        raise PermissionError("MODEL_SHARD_NOT_GRANTED")
    return {**deepcopy(grant), "selected": deepcopy(selected)}
