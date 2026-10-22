"""Recovery-only authority; V4 grants are never consulted or accepted."""
from copy import deepcopy
from datetime import datetime
import re

from ..hnlo_train.contract import unit as baseline_unit, FLAGS as BASE_FLAGS, EVIDENCE
from .cohort import MAPPING_SHA, WORKER_SHA, NEW_RUN, NEW_ATTEMPT

BASE_SHA = "7b8d6e77ff821ac02f0c4c23cc6c1ed6ed8b0c04"
BRANCH = "implement/qwen3-s2-recovery224-20261022"
AUTHORITY = "configs/diagnostics/qwen3_s2_recovery_authority.v1.json"
LOCK = "configs/diagnostics/qwen3_s2_recovery_source.v1.json"
NOTEBOOK = "notebooks/SafeShift_QWEN3_S2_RECOVERY224_V1.ipynb"
FLAGS = BASE_FLAGS + ("recovery_cohort_only_approved", "prior_duplicate_exposure_acknowledged",
    "fresh_process_and_observer_overhead_accepted", "cross_session_attempt_reserved",
    "no_baseline_pooling_approved")


def unit():
    return {**baseline_unit("qwen3", 2), "count": 224, "run_id": NEW_RUN,
        "attempt_id": NEW_ATTEMPT, "inference_sha256": WORKER_SHA,
        "mapping_sha256": MAPPING_SHA, "original_ordinals": [717, 940],
        "max_generate_calls": 224, "cohort": "SUPPLEMENTAL_RECOVERY_NOT_V4_BASELINE"}


def template():
    return {"schema": "qwen3-s2-recovery-authority-v1", "base_sha": BASE_SHA,
        "scope": {"unit": unit(), "evidence_contract": EVIDENCE,
            "max_worker_seconds": 36000, "max_sample_evidence_bytes": 2 * 2**20,
            "max_observation_bytes_per_sample": 2**20, "max_observation_events_per_sample": 128,
            "max_new_tokens": 32, "batch_size": 1, "retry": False, "resume": False,
            "max_loads": 1, "baseline_pooling_allowed": False, "test_access": False,
            "label_access": "CPU_ONLY_AFTER_RAW_CUSTODY_AND_NEW_GRANT",
            "worker_identity": "ORDINAL_HASH_ONLY", "full_vocab_replay": False,
            "synchronized_profiling": False, "allocator_history": False,
            "peak_reset": "ONCE_BEFORE_LOAD_LIFETIME_ONLY",
            "observer": "SCALAR_MEMORY_AND_PASSIVE_NATIVE_FORWARD_HOOKS_V1"}, "grant": None}


def authorize(value, source):
    from .bootstrap import canonical
    if canonical({**value, "grant": None}) != canonical(template()):
        raise PermissionError("SEPARATE_RECOVERY_AUTHORITY_REQUIRED")
    grant = value.get("grant")
    fields = {"approved_by", "role", "approved_utc", "decision_url", "independent_audit_url",
              "implementation_commit", "source_payload_sha256", "unit", "approvals"}
    if type(grant) is not dict or set(grant) != fields:
        raise PermissionError("NEW_RECOVERY_GRANT_REQUIRED")
    if grant["role"] != "Research Lead" or type(grant["approved_by"]) is not str or not grant["approved_by"].strip():
        raise PermissionError("RESEARCH_LEAD_REQUIRED")
    try:
        datetime.strptime(grant["approved_utc"], "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        raise PermissionError("VALID_APPROVAL_UTC_REQUIRED") from None
    if (grant["implementation_commit"] != source["implementation_commit"]
            or grant["source_payload_sha256"] != source["payload_sha256"]
            or not re.fullmatch(r"[0-9a-f]{40}", grant["implementation_commit"])
            or not re.fullmatch(r"[0-9a-f]{64}", grant["source_payload_sha256"])):
        raise PermissionError("RECOVERY_SOURCE_BINDING_MISMATCH")
    for key in ("decision_url", "independent_audit_url"):
        match = re.fullmatch(r"https://github.com/tantdna2/SafeShift/pull/(\d+)#[-a-zA-Z0-9]+", grant[key])
        if not match or int(match[1]) <= 123 or int(match[1]) != source["pr_number"]:
            raise PermissionError("FRESH_RECOVERY_REVIEW_REQUIRED")
    if (canonical(grant["unit"]) != canonical(unit()) or type(grant["approvals"]) is not dict
            or set(grant["approvals"]) != set(FLAGS)
            or any(v is not True for v in grant["approvals"].values())):
        raise PermissionError("EXACT_RECOVERY_UNIT_AND_ALL_APPROVALS_REQUIRED")
    return deepcopy(grant)
