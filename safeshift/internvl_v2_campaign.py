"""Exact PR177 release and create-only, cross-VM campaign permits.

Only the local authenticated coordinator writes GitHub. No credential enters a VM.
No historical Issue173 permission is accepted. Unknown state always stops.
"""
import json
import hashlib
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
DELEGATION_COMMENT = 6625594194
DELEGATION_SHA256 = "52422be8930f419edb046eb709728429628f215853c41b0006a39b4e42baf77b"
DELEGATED_MODE = "OWNER_PREAUDIT_TECHNICAL_TRIAL_V1"
JOB1_FINISHED_DIGEST = "a319f767c07809e21d42367bcf158763b9c3ec380a3ccc9c739a1b8c374d829b"
_capability = None
CONTINUOUS = False
CONTINUOUS_CAMPAIGN = "internvl-v2-6626498951"
CONTINUOUS_AUTHORITY_SHA = "03407e1981f90a7b03f7ddcd0baacdec32b0f204d7a2afaf040bb17fae76240b"
HISTORICAL_REFS = {
    "j1/finished": "608c53efd43220e0c787efa61a6072912a201e55",
    "j1/launch": "9d716edc8420bcc6c2ee0f044df5a758f10fd81f",
    "j1/setup": "efc1e984e1e72c43ebc953f49efcf8f34101ba6c",
    "j1/submission": "85257bcded45c958e481cb7e119bdfc90e41a1c4",
    "j1/submitted": "3e8e6ef8395f587ed43c433a40928b859ce8bc16",
    "j1/worker": "0b1aa7127351ab8a88edaf3e42371c227d7b2878",
    "j2/finished": "3b348cea54d50796dbe888089d71d76fa6a1aff2",
    "j2/launch": "b1c4d1b976867d366a1876d007331357d5e9c0ab",
    "j2/setup": "567ab3c4d84710c699e9ce6e1bc6f6d1ddea7595",
    "j2/submission": "83109a50b532bb763da434bf3683ef8196b37a17",
    "j2/submitted": "22c21af137cbf9bc7ee40f1bf29c1742d1e05ae7",
    "j2/worker": "47dfc8f87e8c5c09d66fb765e08b8cd2c9e8c6c5",
}


def select_continuous():
    """Select a source-bound operational protocol, never confer authorization.

    Must be explicit at each process entrypoint. Historical defaults stay intact.
    There is deliberately no switch back while any capability could be active.
    """
    global CONTINUOUS, CAMPAIGN, LIMITS
    require(_capability is None, "POLICY_CHANGE_AFTER_ACTIVATION")
    CONTINUOUS = True
    CAMPAIGN = CONTINUOUS_CAMPAIGN
    LIMITS = {"jobs": None, "loads": 1, "calls": 1, "seconds": 1800, "physical_gpu_seconds": None}


def historical_preserved():
    prefix = "refs/tags/internvl-v2-6622148168/"
    rows = public_get("/git/matching-refs/tags/internvl-v2-6622148168/?cache=" + str(time.time_ns()))
    require(len(rows) == len(HISTORICAL_REFS) and
            {r["ref"]: r["object"]["sha"] for r in rows if r["object"]["type"] == "tag"} ==
            {prefix + k: v for k, v in HISTORICAL_REFS.items()}, "HISTORICAL_LEDGER_CHANGED")
    return digest(HISTORICAL_REFS)


def continuous_grant(number):
    grant = comment_record(number, "INTERNVL_V2_CONTINUOUS_RELEASE_V1")
    fields = {"campaign", "reviewed_head", "runtime_commit", "manifest_sha256", "notebook_sha256",
        "notebook_code_sha256", "request", "request_sha256", "slot", "mode", "job", "version",
        "issued_unix", "expires_unix", "limits", "predecessors", "authorization_mode", "authority_comment",
        "authority_sha256", "independent_audit", "research_scientific_qualification", "quota_cap_gpu_seconds"}
    require(set(grant) == fields and number > 6626498951, "CONTINUOUS_RELEASE_FIELDS")
    require(grant["campaign"] == CAMPAIGN and grant["job"] == job(grant["slot"])
            and grant["mode"] == "native" and type(grant["version"]) is int and grant["version"] == 1
            and digest(grant["limits"]) == digest(LIMITS), "CONTINUOUS_RELEASE_IDENTITY")
    require(grant["authorization_mode"] == "OWNER_CONTINUOUS_TECHNICAL_V1"
            and grant["authority_comment"] == 6626498951 and grant["authority_sha256"] == CONTINUOUS_AUTHORITY_SHA
            and grant["independent_audit"] == "PENDING_POST_RESULT"
            and grant["research_scientific_qualification"] == "NOT_ESTABLISHED", "CONTINUOUS_OWNER_SCOPE")
    authority = public_get("/issues/comments/6626498951")
    require(authority["user"]["login"] == "tantdna2" and authority["issue_url"] == API + "/issues/177"
            and hashlib.sha256(authority["body"].encode()).hexdigest() == CONTINUOUS_AUTHORITY_SHA,
            "CONTINUOUS_OWNER_AUTHENTICATION")
    require(grant["request_sha256"] == validate_request(grant["request"]), "RELEASE_REQUEST_HASH")
    for key in ("reviewed_head", "runtime_commit"):
        require(isinstance(grant[key], str) and re.fullmatch("[0-9a-f]{40}", grant[key]), "RELEASE_HEAD")
    for key in ("manifest_sha256", "notebook_sha256", "notebook_code_sha256"):
        require_hash(grant[key])
    require(type(grant["issued_unix"]) is int and type(grant["expires_unix"]) is int
            and 0 < grant["expires_unix"] - grant["issued_unix"] <= 3600
            and grant["issued_unix"] <= time.time() < grant["expires_unix"], "RELEASE_EXPIRED_OR_TOO_LONG")
    cap = grant["quota_cap_gpu_seconds"]
    require(cap is None or (type(cap) is int and cap >= grant["slot"] * 3600), "OPTIONAL_QUOTA_CAP")
    require(type(grant["predecessors"]) is list and len(grant["predecessors"]) == grant["slot"] - 1,
            "COMPLETE_PREDECESSOR_RELEASE")
    for value in grant["predecessors"]:
        require_hash(value)
    historical_preserved()
    check_head(grant)
    return grant


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
    require(type(slot) is int and slot >= 1 and (CONTINUOUS or slot <= 3), "THREE_JOB_BUDGET")
    return "nguynanhtn/safeshift-" + CAMPAIGN + "-j" + str(slot)


def record_name(name, slot=None):
    if slot is None:
        require(not CONTINUOUS, "CONTINUOUS_REQUIRES_ATTEMPT_SPECIFIC_RECORD")
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
    return tag_record(ref, key)


def tag_record(ref, key):
    tag = public_get("/git/tags/" + ref["object"]["sha"])
    require(tag["tag"] == key and tag["object"]["type"] == "commit", "LEDGER_TAG_TYPE")
    record = json.loads(tag["message"])
    require(set(record) == {"campaign", "name", "head", "value"}
            and record["campaign"] == CAMPAIGN and record["name"] == key
            and record["head"] == tag["object"]["sha"], "LEDGER_OBJECT_BINDING")
    return record["value"]


def active_submissions():
    """One bounded ref snapshot; avoid re-fetching terminal history every child.

    The original job1 proof is still verified separately against its exact digest.
    Immutable tags cannot be updated by this runner. Head checks remain live.
    """
    rows = public_get("/git/matching-refs/tags/" + CAMPAIGN + "/?cache=" + str(time.time_ns()))
    require(type(rows) is list and (CONTINUOUS or len(rows) <= 32), "LEDGER_REF_SNAPSHOT_BOUND")
    refs = {}
    for row in rows:
        require(row["ref"] not in refs and row["object"]["type"] == "tag", "LEDGER_REF_SNAPSHOT_TYPE")
        refs[row["ref"]] = row
    active = []
    slots = range(1, 4)
    if CONTINUOUS:
        slots = sorted({int(re.fullmatch(re.escape("refs/tags/" + CAMPAIGN) +
            r"/j([1-9][0-9]*)/(?:submission|submitted|finished|launch|setup|worker|load|call)", name).group(1)) for name in refs})
        require(slots == list(range(1, len(slots) + 1)), "CONTINUOUS_LEDGER_GAP")
    for slot in slots:
        name = record_name("submission", slot)
        ref = refs.get("refs/tags/" + name)
        finished = "refs/tags/" + record_name("finished", slot) in refs
        require(not finished or ref is not None, "ORPHAN_FINISHED_LEDGER")
        if ref is not None and not finished:
            active.append((slot, tag_record(ref, name)))
    return active


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
    if CONTINUOUS:
        return continuous_grant(number)
    delegated = False
    try:
        grant = comment_record(number, "INTERNVL_V2_RELEASE_V1")
    except ValueError as error:
        if str(error) != "EXACT_MACHINE_READABLE_RECORD_REQUIRED":
            raise
        grant = comment_record(number, "INTERNVL_V2_DELEGATED_RELEASE_V1")
        delegated = True
    common = {"campaign", "reviewed_head", "runtime_commit", "manifest_sha256",
        "notebook_sha256", "notebook_code_sha256", "request", "request_sha256", "slot", "mode",
        "job", "version", "issued_unix", "expires_unix", "limits", "predecessors"}
    extra = {"authorization_mode", "authority_comment", "authority_sha256", "independent_audit",
             "research_scientific_qualification"} if delegated else {"chatgpt_review_comment", "antigravity_audit_comment"}
    require(set(grant) == common | extra, "EXACT_RELEASE_FIELDS")
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
    if delegated:
        require(type(number) is int and number > DELEGATION_COMMENT
                and grant["authorization_mode"] == DELEGATED_MODE
                and grant["authority_comment"] == DELEGATION_COMMENT
                and grant["authority_sha256"] == DELEGATION_SHA256
                and grant["independent_audit"] == "PENDING_POST_TRIAL"
                and grant["research_scientific_qualification"] == "NOT_ESTABLISHED"
                and (grant["slot"], grant["mode"]) in ((2, "preflight"), (3, "native")), "EXACT_OWNER_TECHNICAL_DELEGATION")
        authority = public_get("/issues/comments/" + str(DELEGATION_COMMENT))
        require(authority["user"]["login"] == "tantdna2" and authority["issue_url"] == API + "/issues/177"
                and hashlib.sha256(authority["body"].encode()).hexdigest() == DELEGATION_SHA256,
                "OWNER_DELEGATION_CHANGED_OR_WRONG_AUTHOR")
        first = remote_record("finished", 1)
        require(first is not None and digest(first) == JOB1_FINISHED_DIGEST
                and first["terminal"] == "ERROR" and first["proof"] == "ZERO_CALL_CONFIRMED"
                and first["calls"] == 0 and first["weights_loaded"] is False,
                "IMMUTABLE_JOB1_ZERO_CALL_PROOF_REQUIRED")
    else:
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
    active = active_submissions()
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
            if phase in ("load", "call") and not CONTINUOUS:
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
        if phase in ("load", "call") and not CONTINUOUS:
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
        if CONTINUOUS:
            from safeshift.pilot.artifacts import read, sha
            preflight = read(c["out"] / "internal-preflight.json")
            require(preflight["status"] == "LIVE_GPU_PREFLIGHT_PASS"
                    and preflight["source_sha256"] == digest(c["spec"])
                    and preflight["weights_loaded"] is False and preflight["original_image_read"] is False
                    and all(sha(c["out"] / k) == v for k, v in preflight["evidence"].items()),
                    "POSITIVE_INTERNAL_PREFLIGHT_BEFORE_NATIVE")
        require(action in ("load", "call") and action not in c["used"], "NATIVE_ACTION_ALREADY_USED")
        require(action != "call" or "load" in c["used"], "CALL_WITHOUT_LOAD")
        c["used"].add(action)  # An exception never restores local permission.
        granted = permit(c["ctx"], action, c["parent"])
        c["parent"] = granted["nonce"]
        write(c["out"] / (action + "-permit.json"), granted)
