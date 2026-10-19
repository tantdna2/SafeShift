"""New source-bound authority; every historical execution grant is ineligible."""
from copy import deepcopy
import re

from ..one_click import contract as original

BASE_SHA = "d599aa93f57e0c5cc349f090c666e908edd7475e"
BRANCH = "prep/internvl3-hnlo-gpu-probe-20261019"
AUTHORITY = "configs/diagnostics/internvl3_hnlo_authority.v1.json"
LOCK = "configs/diagnostics/internvl3_hnlo_source.v1.json"
NOTEBOOK = "notebooks/SafeShift_InternVL3_HNLO_GPU_PROBE.ipynb"
ORDER = ("internvl3",)
BOUNDARY = "SECCOMP_UNIX_CONNECT_NO_INHERITED_SOCKETS_V1_PLUS_PYTHON_GUARD"
ATTEMPT_ID = "internvl3-hnlo-probe-20261019-01"
FLAGS = ("provisioning_approved", "gpu_probe_approved", "technical_probe_exception_approved",
         "raw_provenance_criteria_approved", "numerical_tolerance_approved",
         "artifact_retention_approved", "driver_loading_policy_change_approved",
         "unchanged_security_boundary_approved", "local_peer_relay_risk_accepted",
         "model_load_and_generation_approved")


def scope():
    value = original.scope()
    value.update(models={"internvl3": deepcopy(original.MODELS["internvl3"])}, order=list(ORDER),
                 network_boundary=BOUNDARY,
                 environment_policy="SANITIZED_ENV_POST_GUARD_FIXED_DRIVER_OBJECTS_V1",
                 driver_directory="/usr/local/nvidia/lib64", driver_version="580.178.04",
                 driver_load="VERIFIED_FD_RTLD_LOCAL_NOW",
                 cuda_before_checkpoint_provisioning=True, attempt_id=ATTEMPT_ID,
                 driver_handles="STRONG_REFERENCES_UNTIL_WORKER_EXIT",
                 full_vectors="ALL_RAW_AND_PROCESSED_STEPS_NO_TRUNCATION",
                 security_scope="LOCAL_AF_UNIX_ONLY;PARTIAL_MONITOR;NO_SECURITY_PASS_OR_NO_LEAK")
    return value


def template():
    return {"schema": "internvl3-hnlo-probe-authority-v1", "base_sha": BASE_SHA,
            "scope": scope(), "grant": None}


def authorize(value, source):
    if {**value, "grant": None} != template():
        raise PermissionError("HNLO_PROBE_AUTHORITY_SCOPE_CHANGED")
    grant = value.get("grant")
    identity = {"approved_by", "role", "approved_utc", "decision_url", "independent_audit_url",
                "implementation_commit", "source_payload_sha256", "attempt_id"}
    if not isinstance(grant, dict) or set(grant) != identity | set(FLAGS):
        raise PermissionError("NEW_HNLO_PROBE_LEAD_GRANT_REQUIRED")
    if grant["role"] != "Research Lead" or not grant["approved_by"]:
        raise PermissionError("RESEARCH_LEAD_REQUIRED")
    if any(grant[flag] is not True for flag in FLAGS):
        raise PermissionError("ALL_NEW_HNLO_PROBE_APPROVALS_REQUIRED")
    if grant["attempt_id"] != ATTEMPT_ID:
        raise PermissionError("NEW_HNLO_PROBE_ATTEMPT_REQUIRED")
    if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", grant["approved_utc"]):
        raise PermissionError("APPROVAL_DATE_REQUIRED")
    if (grant["implementation_commit"] != source["implementation_commit"] or
            grant["source_payload_sha256"] != source["payload_sha256"]):
        raise PermissionError("HNLO_PROBE_SOURCE_BINDING_MISMATCH")
    for key in ("decision_url", "independent_audit_url"):
        match = re.fullmatch(r"https://github.com/tantdna2/SafeShift/(?:pull|issues)/(\d+)(?:#[-a-zA-Z0-9]+)?", grant[key])
        if not match or int(match[1]) <= 115:
            raise PermissionError("NEW_HNLO_PROBE_REVIEW_REQUIRED")
    return deepcopy(grant)
