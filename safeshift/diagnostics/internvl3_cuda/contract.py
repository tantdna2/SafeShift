"""A new, null-by-default diagnostic authority, independent of PRs 112/113."""
from copy import deepcopy
import re

BASE_SHA = "67d401091adfde8a17d1fa9cd89af5574dfa529a"
BRANCH = "codex/internvl3-driver-diagnostic-20261018"
AUTHORITY = "configs/diagnostics/internvl3_cuda_authority.v1.json"
LOCK = "configs/diagnostics/internvl3_cuda_source.v1.json"
NOTEBOOK = "notebooks/SafeShift_InternVL3_CUDA_DIAGNOSTIC.ipynb"
STAGES = ("metadata", "load_cuda", "load_nvml", "load_cudart", "cuinit", "runtime_count")
BOUNDARY = "SECCOMP_UNIX_CONNECT_NO_INHERITED_SOCKETS_V1_PLUS_PYTHON_GUARD"
FLAGS = ("metadata_collection_approved", "loader_probe_approved", "driver_initialization_approved",
         "runtime_count_approved", "provisioning_approved", "artifact_retention_approved",
         "unchanged_security_boundary_approved")


def template():
    return {"schema": "internvl3-cuda-diagnostic-authority-v1", "base_sha": BASE_SHA,
            "scope": {"model": "internvl3", "python": "3.11.11", "torch": "2.6.0+cu124",
                      "transformers": "4.52.4", "cuda": "12.4", "cuda_visible_devices": "0",
                      "stages": list(STAGES), "fresh_process_per_stage": True,
                      "network_boundary": BOUNDARY, "host_observation": "STATIC_METADATA_ONLY",
                      "environment_policy": "UNCHANGED_ONE_CLICK_CHILD_ENVIRONMENT",
                      "weights_download": False, "model_load": False, "inference": False,
                      "dataset_access": False, "labels_or_gt_access": False, "retry": False,
                      "unguarded_cuda": False, "security_boundary_expansion": False}, "grant": None}


def authorize(value, source):
    if {**value, "grant": None} != template():
        raise PermissionError("CUDA_DIAGNOSTIC_SCOPE_CHANGED")
    grant = value.get("grant")
    identity = {"approved_by", "role", "approved_utc", "decision_url", "independent_audit_url",
                "implementation_commit", "source_payload_sha256", "attempt_id"}
    if not isinstance(grant, dict) or set(grant) != identity | set(FLAGS):
        raise PermissionError("NEW_CUDA_DIAGNOSTIC_LEAD_GRANT_REQUIRED")
    if grant["role"] != "Research Lead" or not grant["approved_by"]:
        raise PermissionError("RESEARCH_LEAD_REQUIRED")
    if any(grant[flag] is not True for flag in FLAGS):
        raise PermissionError("ALL_DIAGNOSTIC_APPROVALS_REQUIRED")
    if not re.fullmatch(r"internvl3-cuda-diag-[a-z0-9_-]{1,18}", grant["attempt_id"]):
        raise PermissionError("FRESH_CUDA_DIAGNOSTIC_ATTEMPT_REQUIRED")
    if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", grant["approved_utc"]):
        raise PermissionError("APPROVAL_DATE_REQUIRED")
    if (grant["implementation_commit"] != source["implementation_commit"] or
            grant["source_payload_sha256"] != source["payload_sha256"]):
        raise PermissionError("DIAGNOSTIC_SOURCE_BINDING_MISMATCH")
    for key in ("decision_url", "independent_audit_url"):
        match = re.fullmatch(r"https://github.com/tantdna2/SafeShift/(?:pull|issues)/(\d+)(?:#[-a-zA-Z0-9]+)?", grant[key])
        if not match or int(match[1]) in (112, 113):
            raise PermissionError("NEW_DURABLE_DIAGNOSTIC_REVIEW_REQUIRED")
    return deepcopy(grant)
