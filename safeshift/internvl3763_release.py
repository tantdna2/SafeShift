"""Exact new Owner authority and a permanent cross-machine claim protocol.

No credentials, model imports, implicit grant, retry or lease reclamation.
The service is a separately deployed non-AI authority; absence fails closed.
"""
import hashlib
import json
import re
import time
from urllib.request import Request, urlopen

from safeshift.candidates.source import require
from safeshift.pilot.contract import digest, require_hash

API = "https://api.github.com/repos/tantdna2/SafeShift"
MARKER = "SAFESHIFT_TRAIN3763_RELEASE_V1"
OWNER = "tantdna2"
SCHEMA = "safeshift-train3763-release-v1"


def get(path):
    require(path.startswith("/") and not path.startswith("//"), "RELEASE_API_PATH")
    return http(API + path, None)


def http(url, payload):
    # No redirects, application retries, credentials or unbounded responses.
    from urllib.request import build_opener, HTTPRedirectHandler
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    data = None if payload is None else json.dumps(payload, allow_nan=False).encode()
    request = Request(url, data=data, headers={"Accept": "application/json",
        "Content-Type": "application/json", "User-Agent": "SafeShift-TRAIN3763",
        "Cache-Control": "no-cache"})
    with build_opener(NoRedirect).open(request, timeout=15) as response:
        require(response.geturl() == url, "AUTHORITY_REDIRECT")
        raw = response.read(8 * 2**20 + 1)
        require(len(raw) <= 8 * 2**20, "AUTHORITY_RESPONSE_BOUND")
    def pairs(items):
        obj = {}
        for key, value in items:
            require(key not in obj, "DUPLICATE_AUTHORITY_JSON_KEY")
            obj[key] = value
        return obj
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_AUTHORITY_JSON")))


def request_hash(request):
    return digest({k: v for k, v in request.items() if k != "execution_release"})


def origin(value):
    require(type(value) is str and re.fullmatch(r"https://[A-Za-z0-9.-]+(?::[0-9]{1,5})?", value)
        and ".." not in value, "APPROVED_HTTPS_WITNESS_ORIGIN_REQUIRED")
    return value


def load(locator, *, reader=None, now=None, for_collection=False):
    """Authenticate the live Owner comment, exact merged PR and narrow scope.

    reader/now are test dependency seams, never CLI flags or notebook settings.
    No preparation comment or caller-authored 'approved' bool can activate this.
    """
    require(type(locator) is dict and set(locator) == {"comment_id", "body_sha256"},
        "NEW_EXACT_EXECUTION_RELEASE_REQUIRED")
    require(type(locator["comment_id"]) is int and locator["comment_id"] > 0, "RELEASE_COMMENT_ID")
    require_hash(locator["body_sha256"])
    reader = get if reader is None else reader
    comment = reader("/issues/comments/" + str(locator["comment_id"]))
    require(comment["user"]["login"] == OWNER and comment["id"] == locator["comment_id"]
        and hashlib.sha256(comment["body"].encode()).hexdigest() == locator["body_sha256"],
        "AUTHENTIC_OWNER_RELEASE_REQUIRED")
    matches = re.findall(re.escape(MARKER) + r"\s*```json\s*(\{.*?\})\s*```", comment["body"], re.S)
    require(len(matches) == 1, "ONE_EXACT_RELEASE_RECORD_REQUIRED")
    grant = json.loads(matches[0])
    require(set(grant) == {"schema", "implementation_pr", "reviewed_head", "merged_sha", "runtime_commit",
        "source_sha256", "execution_request_sha256", "request_sha256", "notebook_sha256",
        "notebook_code_sha256", "job", "version", "series", "attempt", "issued_unix", "expires_unix",
        "witness", "witness_id", "caps", "predecessors", "approvals", "authorization"}, "EXACT_RELEASE_FIELDS")
    require(grant["schema"] == SCHEMA and grant["authorization"] == "GRANTED_FOR_THIS_EXACT_ATTEMPT",
        "EXPLICIT_EXECUTION_AUTHORITY_REQUIRED")
    require(type(grant["implementation_pr"]) is int and grant["implementation_pr"] > 178
        and comment["issue_url"] == API + "/issues/" + str(grant["implementation_pr"]),
        "NO_PR177_OR_PR178_PERMISSION_REUSE")
    for key in ("reviewed_head", "merged_sha", "runtime_commit"):
        require(type(grant[key]) is str and re.fullmatch(r"[a-f0-9]{40}", grant[key]), "EXACT_RELEASE_COMMIT")
    for key in ("source_sha256", "execution_request_sha256", "request_sha256", "notebook_sha256", "notebook_code_sha256"):
        require_hash(grant[key])
    pr = reader("/pulls/" + str(grant["implementation_pr"]))
    require(pr["merged"] is True and pr["head"]["sha"] == grant["reviewed_head"]
        and pr["merge_commit_sha"] == grant["merged_sha"] and pr["base"]["ref"] == "main",
        "EXACT_REVIEW_AUDIT_MERGE_REQUIRED")
    require(type(grant["approvals"]) is dict and set(grant["approvals"]) == {
        "chatgpt_review", "independent_audit", "merge", "O2", "O3", "O4", "O5", "O6"},
        "SEPARATE_APPROVAL_EVIDENCE_REQUIRED")
    for evidence in grant["approvals"].values():
        require(type(evidence) is dict and set(evidence) == {"ref", "sha256"}
            and type(evidence["ref"]) is str and evidence["ref"].startswith("https://")
            and len(evidence["ref"]) <= 1000, "APPROVAL_EVIDENCE_REFERENCE")
        require_hash(evidence["sha256"])
    for kind, evidence in grant["approvals"].items():
        match = re.fullmatch(r"https://github.com/tantdna2/SafeShift/(?:pull|issues)/([1-9][0-9]*)#issuecomment-([1-9][0-9]*)",
            evidence["ref"])
        require(match is not None and int(match[1]) == grant["implementation_pr"], "NEW_PR_APPROVAL_REFERENCE_REQUIRED")
        proof = reader("/issues/comments/" + match[2])
        require(proof["user"]["login"] == OWNER and proof["issue_url"] == comment["issue_url"]
            and hashlib.sha256(proof["body"].encode()).hexdigest() == evidence["sha256"], "AUTHENTIC_APPROVAL_ATTESTATION_REQUIRED")
        approvals = re.findall(r"SAFESHIFT_TRAIN3763_APPROVAL_V1\s*```json\s*(\{.*?\})\s*```", proof["body"], re.S)
        require(len(approvals) == 1, "STRUCTURED_SEPARATE_APPROVAL_REQUIRED")
        approval = json.loads(approvals[0])
        require(approval == {"kind": kind, "reviewed_head": grant["reviewed_head"],
            "status": "APPROVED", "scope": "TRAIN3763_EXACT_RELEASE"}, "APPROVAL_ROLE_HEAD_SCOPE_REQUIRED")
    # The Owner attests these separately issued decisions; code never issues them.
    require(type(grant["issued_unix"]) is int and type(grant["expires_unix"]) is int
        and 0 < grant["expires_unix"] - grant["issued_unix"] <= 86400
        and (for_collection or grant["issued_unix"] <= (time.time() if now is None else now) < grant["expires_unix"]),
        "RELEASE_EXPIRED_OR_INVALID_WINDOW")
    from safeshift.internvl3763 import SERIES
    require(grant["series"] == SERIES and type(grant["attempt"]) is int and 1 <= grant["attempt"] <= 3763,
        "EXACT_SERIES_ATTEMPT")
    require(re.fullmatch(r"nguynanhtn/safeshift-train3763-[a-z0-9-]+", grant["job"])
        and type(grant["version"]) is int and grant["version"] == 1, "NEW_PRIVATE_JOB_VERSION1_REQUIRED")
    origin(grant["witness"])
    require_hash(grant["witness_id"])
    caps = grant["caps"]
    require(type(caps) is dict and set(caps) == {"calls", "seconds", "loads", "physical_gpus",
        "machine_shape", "attempt_gpu_seconds", "campaign_gpu_seconds", "archive_bytes"}, "NUMERICAL_CAPS_REQUIRED")
    for key in ("calls", "seconds", "loads", "physical_gpus", "attempt_gpu_seconds", "campaign_gpu_seconds", "archive_bytes"):
        require(type(caps[key]) is int and caps[key] > 0, "INTEGER_RESOURCE_CAP_REQUIRED")
    require(1 <= caps["calls"] <= 3763 and 120 <= caps["seconds"] <= 43200
        and caps["loads"] == 1 and caps["physical_gpus"] == 2
        and caps["machine_shape"] == "NvidiaTeslaT4"
        and caps["attempt_gpu_seconds"] == caps["seconds"] * caps["physical_gpus"]
        and caps["campaign_gpu_seconds"] >= caps["attempt_gpu_seconds"]
        and caps["archive_bytes"] <= 7 * 2**30, "UNSUPPORTED_OR_UNBOUNDED_RESOURCES")
    require(type(grant["predecessors"]) is list and len(grant["predecessors"]) == grant["attempt"] - 1,
        "COMPLETE_PREDECESSOR_CHAIN_REQUIRED")
    for predecessor in grant["predecessors"]:
        require_hash(predecessor)
    return grant


def bind(grant, request):
    from safeshift import internvl3763 as runtime
    from safeshift.kaggle_handoff import validate_request
    validate_request(request)
    execution = request["bindings"]["runtime"]["execution_request"]
    p = runtime.validate_execution_request(execution)
    require(grant["request_sha256"] == request_hash(request)
        and request["plan"] == p
        and grant["source_sha256"] == digest(execution["source"])
        and grant["execution_request_sha256"] == digest(execution)
        and grant["notebook_sha256"] == request["notebook_sha256"]
        and grant["runtime_commit"] == request["runtime_commit"]
        and grant["merged_sha"] == request["commit_sha"]
        and grant["job"] == request["job"] and grant["version"] == request["version"]
        and grant["caps"]["calls"] == request["limits"]["max_calls"] == p["max_calls"]
        and grant["caps"]["seconds"] == request["limits"]["job_seconds"] == p["max_seconds"]
        and grant["attempt"] == len(execution["history"]) + 1,
        "EXACT_RELEASE_REQUEST_SOURCE_LIMIT_BINDING")
    return execution


class Witness:
    """One POST only. Timeout/conflict consumes or ambiguates the claim forever."""
    def __init__(self, grant, locator, *, transport=None):
        self.grant, self.locator = grant, locator
        self.transport = http if transport is None else transport
        self.base = origin(grant["witness"])

    def path(self, kind):
        require(kind in ("submit", "launch", "worker", "load", "snapshot")
            or re.fullmatch(r"call-[0-9]{6}", kind), "WITNESS_CLAIM_KIND")
        return self.base + "/v1/" + self.grant["series"] + "/" + str(self.grant["attempt"]) + "/" + kind

    def claim(self, kind, request):
        require(kind != "snapshot", "SNAPSHOT_READ_ONLY")
        value = {"release": self.locator, "request": request, "kind": kind}
        receipt = self.transport(self.path(kind), value)
        require(receipt.get("created") is True and receipt.get("claim_sha256") == digest(value)
            and receipt.get("release_sha256") == digest(self.grant)
            and receipt.get("witness_id") == self.grant["witness_id"], "CLAIM_UNCONFIRMED_NO_RETRY")
        return receipt

    def observe(self, kind):
        value = self.transport(self.path(kind), None)
        require(value.get("witness_id") == self.grant["witness_id"], "WITNESS_DATABASE_ID_DRIFT")
        return value


_active = None
_activation_claim = None


def activate(request, stage):
    global _active, _activation_claim
    require(_active is None, "CAPABILITY_ALREADY_ACTIVE")
    require(stage in ("launch", "worker"), "EXACT_ACTIVATION_PHASE_REQUIRED")
    grant = load(request.get("execution_release"))
    bind(grant, request)
    witness = Witness(grant, request["execution_release"])
    _activation_claim = witness.claim(stage, request)
    _active = (grant, witness, request, stage)
    return grant


def activation_claim():
    require(_active is not None and _activation_claim is not None, "NO_AUTHENTICATED_ACTIVATION_CLAIM")
    return _activation_claim


def authorize(stage="worker", *, ordinal=None):
    require(_active is not None, "TRAIN3763_PREPARATION_ONLY: NEW_EXECUTION_RELEASE_O2_O6_REQUIRED")
    grant, witness, request, phase = _active
    require(time.time() < grant["expires_unix"], "ACTIVE_EXECUTION_RELEASE_EXPIRED")
    require((stage == "execute" and phase == "launch")
        or (stage in ("worker", "preflight", "load", "call") and phase == "worker"), "CAPABILITY_PHASE_MISMATCH")
    if stage in ("load", "call"):
        if stage == "call":
            require(type(ordinal) is int and ordinal in request["plan"]["scheduled_ordinals"], "AUTHORIZED_CALL_ORDINAL")
        return witness.claim("load" if stage == "load" else f"call-{ordinal:06d}", request)
    require(stage in ("worker", "preflight", "execute"), "NATIVE_AUTHORIZATION_STAGE")
    return grant
