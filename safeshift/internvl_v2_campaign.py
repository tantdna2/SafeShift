"""Exact PR177 release and create-only, cross-VM campaign permits.

Only the local authenticated coordinator writes GitHub. No credential enters a VM.
No historical Issue173 permission is accepted. Unknown state always stops.
"""
import json
import re
import secrets
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from safeshift.candidates.source import ROOT, require
from safeshift.pilot.contract import digest, MASTER_SHA, require_hash

REPO = "tantdna2/SafeShift"
API = "https://api.github.com/repos/" + REPO
BRANCH = "feat/internvl-grammar-v2-native"
CAMPAIGN = "internvl-v2-6622148168"
PREFIX = "SAFESHIFT_INTERNVL_V2_CHALLENGE "
LIMITS = {"jobs": 3, "loads": 1, "calls": 1, "seconds": 1800, "physical_gpu_seconds": 3600}
ORIGINAL_ARCHIVE = "035c4d9b0216378e23ecc812e1221d68fe451ec25a9cbc3fd8977b5794690619"
PHASES = ("launch", "setup", "worker", "load", "call")
_capability = None


def public_get(path, *, missing=False):
    request = Request(API + path, headers={"Accept": "application/vnd.github+json",
        "User-Agent": "SafeShift-PR177", "Cache-Control": "no-cache"})
    try:
        with urlopen(request, timeout=15) as response:
            require(response.geturl().startswith(API + "/"), "GITHUB_REDIRECT")
            payload = response.read(2**20 + 1)
            require(len(payload) <= 2**20, "GITHUB_RESPONSE_BOUND")
            return json.loads(payload)
    except HTTPError as error:
        if error.code == 404 and missing:
            return None
        raise RuntimeError("GITHUB_HTTP_" + str(error.code)) from None


def job(slot):
    require(type(slot) is int and 1 <= slot <= 3, "THREE_JOB_BUDGET")
    return "nguynanhtn/safeshift-" + CAMPAIGN + "-j" + str(slot)


def record_name(name, slot=None):
    if slot is None:
        require(name in ("load", "call"), "CAMPAIGN_RECORD")
        return CAMPAIGN + "/" + name
    job(slot)
    require(name in (*PHASES, "submission", "submitted", "finished"), "JOB_RECORD")
    return CAMPAIGN + "/j" + str(slot) + "/" + name


def remote_record(name, slot=None):
    key = record_name(name, slot)
    ref = public_get("/git/ref/tags/" + key + "?cache=" + str(time.time_ns()), missing=True)
    if ref is None:
        return None
    require(ref["ref"] == "refs/tags/" + key and ref["object"]["type"] == "tag", "LEDGER_REF_TYPE")
    tag = public_get("/git/tags/" + ref["object"]["sha"])
    require(tag["tag"] == key and tag["object"]["type"] == "commit", "LEDGER_TAG_TYPE")
    record = json.loads(tag["message"])
    require(set(record) == {"campaign", "name", "head", "value"}
            and record["campaign"] == CAMPAIGN and record["name"] == key
            and record["head"] == tag["object"]["sha"], "LEDGER_OBJECT_BINDING")
    return record["value"]


def github_post(path, payload):
    result = subprocess.run(["gh", "api", "--method", "POST", "repos/" + REPO + path,
        "--input", "-"], input=json.dumps(payload), text=True, encoding="utf8",
        capture_output=True, timeout=30)
    require(result.returncode == 0, "REMOTE_CREATE_FAILED_OR_UNKNOWN_NO_RETRY")
    return json.loads(result.stdout)


def create_record(name, value, head, slot=None):
    """POST annotated object, then atomically create ref; never PATCH/DELETE/retry.

    A lost ref response burns the slot. Orphan tag objects confer no permission.
    These tags leave the reviewed branch HEAD unchanged.
    """
    key = record_name(name, slot)
    require(re.fullmatch("[0-9a-f]{40}", head), "LEDGER_HEAD")
    message = json.dumps({"campaign": CAMPAIGN, "name": key, "head": head, "value": value}, sort_keys=True)
    tag = github_post("/git/tags", {"tag": key, "message": message, "object": head, "type": "commit"})
    require(re.fullmatch("[0-9a-f]{40}", tag["sha"]), "LEDGER_OBJECT_UNKNOWN")
    ref = github_post("/git/refs", {"ref": "refs/tags/" + key, "sha": tag["sha"]})
    require(ref["ref"] == "refs/tags/" + key and ref["object"]["sha"] == tag["sha"],
            "LEDGER_CREATE_UNCONFIRMED_NO_RETRY")
    return tag["sha"]


def code_hash(notebook):
    return digest([{"cell_type": c["cell_type"], "source": "".join(c["source"])}
                   for c in notebook["cells"] if c["cell_type"] == "code"])


def comment_record(number, marker):
    require(type(number) is int and number > 6622148168, "NEW_EXPLICIT_RELEASE_REQUIRED")
    comment = public_get("/issues/comments/" + str(number))
    require(comment["user"]["login"] == "tantdna2" and comment["issue_url"] == API + "/issues/177",
            "OWNER_PR177_RECORD_REQUIRED")
    matches = re.findall(re.escape(marker) + r"\s*```json\s*(\{.*?\})\s*```", comment["body"], re.S)
    require(len(matches) == 1, "EXACT_MACHINE_READABLE_RECORD_REQUIRED")
    return json.loads(matches[0])


def validate_request(request):
    require(set(request) == {"schema", "source_sha256", "master_sha256", "original_archive_sha256",
        "ordinal", "sample_id_sha256", "image_locator_sha256", "image_sha256"}, "EXACT_REQUEST_FIELDS")
    require(request["schema"] == CAMPAIGN + "-request" and type(request["ordinal"]) is int
            and request["ordinal"] == 0 and request["master_sha256"] == MASTER_SHA
            and request["original_archive_sha256"] == ORIGINAL_ARCHIVE, "ORIGINAL_TRAIN_ONLY")
    for key, value in request.items():
        if key.endswith("sha256"):
            require_hash(value)
    return digest(request)


def read_grant(number):
    grant = comment_record(number, "INTERNVL_V2_RELEASE_V1")
    require(set(grant) == {"campaign", "reviewed_head", "runtime_commit", "manifest_sha256",
        "notebook_sha256", "notebook_code_sha256", "request", "request_sha256", "slot", "mode",
        "job", "version", "issued_unix", "expires_unix", "limits", "chatgpt_review_comment",
        "antigravity_audit_comment", "predecessors"}, "EXACT_RELEASE_FIELDS")
    require(grant["campaign"] == CAMPAIGN and grant["job"] == job(grant["slot"])
            and grant["mode"] in ("preflight", "native") and type(grant["version"]) is int
            and grant["version"] == 1 and grant["limits"] == LIMITS
            and all(type(grant["limits"][k]) is int for k in LIMITS), "EXACT_CAMPAIGN_RELEASE")
    require(grant["request_sha256"] == validate_request(grant["request"]), "RELEASE_REQUEST_HASH")
    for key in ("reviewed_head", "runtime_commit"):
        require(isinstance(grant[key], str) and re.fullmatch("[0-9a-f]{40}", grant[key]), "RELEASE_HEAD")
    for key in ("manifest_sha256", "notebook_sha256", "notebook_code_sha256"):
        require_hash(grant[key])
    require(type(grant["issued_unix"]) is int and type(grant["expires_unix"]) is int
            and 0 < grant["expires_unix"] - grant["issued_unix"] <= 1800
            and grant["issued_unix"] <= time.time() < grant["expires_unix"], "RELEASE_EXPIRED_OR_TOO_LONG")
    require(grant["chatgpt_review_comment"] != grant["antigravity_audit_comment"], "INDEPENDENT_AUDIT_REQUIRED")
    for role, key in (("CHATGPT", "chatgpt_review_comment"), ("ANTIGRAVITY", "antigravity_audit_comment")):
        review = comment_record(grant[key], "INTERNVL_V2_REVIEW_V1")
        require(review == {"role": role, "head": grant["reviewed_head"],
            "request_sha256": grant["request_sha256"], "verdict": "PASS"}, "EXACT_REVIEW_AUDIT_REQUIRED")
    check_head(grant)
    require(type(grant["predecessors"]) is list and len(grant["predecessors"]) == grant["slot"] - 1,
            "COMPLETE_PREDECESSOR_RELEASE")
    for value in grant["predecessors"]:
        require_hash(value)
    return grant


def check_head(grant):
    pr = public_get("/pulls/177")
    require(pr["head"]["sha"] == grant["reviewed_head"] and pr["head"]["ref"] == BRANCH
            and pr["state"] == "open" and pr["draft"] and not pr["merged"], "REVIEWED_HEAD_CHANGED_STOP")


def context(spec, runtime_commit, slot=None):
    from safeshift.internvl_v2_runtime import check_source
    check_source(spec)
    active = [(i, remote_record("submission", i)) for i in range(1, 4)]
    active = [(i, r) for i, r in active if r is not None and remote_record("finished", i) is None]
    require(len(active) == 1, "REVIEW_HOLD_EXACTLY_ONE_ACTIVE_SUBMISSION")
    number, submission = active[0]
    require(slot is None or number == slot, "ACTIVE_JOB_MISMATCH")
    grant = read_grant(submission["approval_comment"])
    require(grant == submission["grant"] and grant["slot"] == number
            and grant["runtime_commit"] == runtime_commit
            and grant["manifest_sha256"] == digest(spec["manifest"])
            and grant["request"]["source_sha256"] == digest(spec), "SOURCE_RELEASE_BINDING")
    return {"grant": grant, "binding": digest(grant), "approval_comment": submission["approval_comment"]}


def permit(ctx, phase, parent_nonce, *, emit=print):
    grant = ctx["grant"]
    phases = PHASES if grant["mode"] == "native" else PHASES[:3]
    require(phase in phases, "NO_NATIVE_PREFLIGHT_PERMIT")
    challenge = {"campaign": CAMPAIGN, "slot": grant["slot"], "binding": ctx["binding"],
                 "phase": phase, "nonce": secrets.token_hex(32), "parent_nonce": parent_nonce}
    require(remote_record(phase, grant["slot"]) is None, "PHASE_ALREADY_RESERVED_NO_REPLAY")
    emit(PREFIX + json.dumps(challenge, sort_keys=True), flush=True)
    deadline = min(time.monotonic() + 240, time.monotonic() + grant["expires_unix"] - time.time())
    while time.monotonic() < deadline:
        record = remote_record(phase, grant["slot"])
        if record is not None:
            require(record == challenge, "NONCE_MISMATCH_NO_REPLAY")
            if phase in ("load", "call"):
                require(remote_record(phase) == challenge, "GLOBAL_CAMPAIGN_PERMIT")
            check_head(grant)
            require(time.time() < grant["expires_unix"], "RELEASE_EXPIRED")
            return challenge
        time.sleep(min(10, max(0, deadline - time.monotonic())))
    raise TimeoutError("PERMIT_TIMEOUT_NO_RETRY")


class Coordinator:
    def __init__(self, grant):
        self.grant, self.accepted = grant, {}

    def accept(self, challenge):
        g = self.grant
        require(set(challenge) == {"campaign", "slot", "binding", "phase", "nonce", "parent_nonce"}, "CHALLENGE_FIELDS")
        phases = PHASES if g["mode"] == "native" else PHASES[:3]
        phase = challenge["phase"]
        require(challenge["campaign"] == CAMPAIGN and challenge["slot"] == g["slot"]
                and challenge["binding"] == digest(g) and phase in phases, "CHALLENGE_BINDING")
        require(re.fullmatch("[0-9a-f]{64}", challenge["nonce"]), "CHALLENGE_NONCE")
        if phase in self.accepted:
            require(self.accepted[phase] == challenge, "DUPLICATE_VM_NO_PERMIT")
            return
        require(phase == phases[len(self.accepted)], "PHASE_ORDER")
        parent = "" if phase == "launch" else self.accepted[phases[phases.index(phase)-1]]["nonce"]
        require(challenge["parent_nonce"] == parent, "PHASE_PARENT_NONCE")
        require(time.time() < g["expires_unix"], "RELEASE_EXPIRED")
        check_head(g)
        if phase in ("load", "call"):
            create_record(phase, challenge, g["reviewed_head"])
        create_record(phase, challenge, g["reviewed_head"], g["slot"])
        self.accepted[phase] = challenge


def activate_worker(ctx, spec, permission, out):
    global _capability
    require(_capability is None and ctx["grant"]["mode"] == "native"
            and permission.get("phase") == "worker" and permission.get("binding") == ctx["binding"]
            and permission == remote_record("worker", ctx["grant"]["slot"]), "NATIVE_WORKER_PERMIT")
    _capability = {"ctx": ctx, "spec": spec, "parent": permission["nonce"], "used": set(), "out": out}


def authorize(action=None):
    from safeshift.internvl_v2_runtime import check_source
    from safeshift.pilot.artifacts import write
    c = _capability
    if c is None:
        raise PermissionError("V2_EXECUTION_NOT_AUTHORIZED_EXACT_RUN_RELEASE_REQUIRED")
    g = c["ctx"]["grant"]
    require(time.time() < g["expires_unix"], "RELEASE_EXPIRED")
    check_source(c["spec"])
    if action is not None:
        require(action in ("load", "call") and action not in c["used"], "NATIVE_ACTION_ALREADY_USED")
        require(action != "call" or "load" in c["used"], "CALL_WITHOUT_LOAD")
        c["used"].add(action)  # An exception never restores local permission.
        granted = permit(c["ctx"], action, c["parent"])
        c["parent"] = granted["nonce"]
        write(c["out"] / (action + "-permit.json"), granted)
