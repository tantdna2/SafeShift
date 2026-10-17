"""New authority; no historical grant or attempt is an execution credential."""

from copy import deepcopy
import re

from ..one_click import contract as original

BASE_SHA = "cb6ae2041e71c74fa1b4943e5986158f5e1b6d83"
BRANCH = "fix/internvl3-cuda-recovery-20261017"
AUTHORITY = "configs/diagnostics/internvl3_recovery_authority.v1.json"
LOCK = "configs/diagnostics/internvl3_recovery_source.v1.json"
NOTEBOOK = "notebooks/SafeShift_InternVL3_RECOVERY_ONE_CLICK.ipynb"
ORDER = ("internvl3",)
BOUNDARY = "SECCOMP_UNIX_CONNECT_NO_INHERITED_SOCKETS_V1_PLUS_PYTHON_GUARD"


def scope():
    value = original.scope()
    value.update(models={"internvl3": deepcopy(original.MODELS["internvl3"])}, order=list(ORDER),
                 network_boundary=BOUNDARY, recovery_of_pr=112,
                 security_scope="LOCAL_AF_UNIX_CONNECT_ONLY;NO_FD_RECEIPT;NO_INET;LOCAL_PROXY_RISK_REQUIRES_APPROVAL")
    return value


def template():
    return {"schema": "internvl3-recovery-authority-v1", "base_sha": BASE_SHA,
            "scope": scope(), "grant": None}


def authorize(value, source):
    if {**value, "grant": None} != template():
        raise PermissionError("RECOVERY_AUTHORITY_SCOPE_CHANGED")
    grant = value.get("grant")
    if not isinstance(grant, dict) or grant.get("security_boundary_change_approved") is not True:
        raise PermissionError("SEPARATE_LEAD_SECURITY_BOUNDARY_APPROVAL_REQUIRED")
    # Reuse every original approval/reference/source check, without accepting its grant.
    stripped = {k: v for k, v in grant.items() if k != "security_boundary_change_approved"}
    original.authorize({**original.template(), "grant": stripped}, source)
    if not re.fullmatch(r"internvl3-recovery-[a-z0-9_-]{1,18}", grant["attempt_id"]):
        raise PermissionError("NEW_INTERNVL3_RECOVERY_ATTEMPT_ID_REQUIRED")
    historical = "https://github.com/tantdna2/SafeShift/pull/112"
    if any(grant[field].split("#")[0] == historical for field in ("decision_url", "independent_audit_url")):
        raise PermissionError("NEW_RECOVERY_DECISION_AND_AUDIT_REQUIRED")
    return deepcopy(grant)
