"""Versioned MiniCPM authority and signed, finite Owner-UI reservations.

No offline export, environment variable or caller's approved flag is authority.
Root trust is a fresh HTTPS Owner record: historical PR198 or reviewed PR199 UI restart.
The Owner-approved public key delegates only bounded serial capsule preparation;
the corresponding private key never enters Kaggle. RSA verification is the
fixed SHA256/3072-bit RSASSA-PKCS1-v1_5 operation in RFC8017,8.2.2/9.2.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
import time

from safeshift.candidates.source import ROOT, require, snapshot_stat
from safeshift.pilot.artifacts import read, write, safe
from safeshift.pilot.contract import digest, json_bytes, require_hash
from . import contract

SCHEMA = "safeshift-minicpm-fulltrain-release-v2"
MARKER = "SAFESHIFT_MINICPM_FULLTRAIN_RELEASE_V2"
APPROVAL = "SAFESHIFT_MINICPM_FULLTRAIN_APPROVAL_V2"
TICKET = "safeshift-minicpm-serial-ticket-v2"
RECOVERY_SCHEMA = "safeshift-minicpm-owner-ui-restart-release-v4"
RECOVERY_MARKER = "SAFESHIFT_MINICPM_OWNER_UI_RESTART_RELEASE_V4"
RECOVERY_TICKET = "safeshift-minicpm-owner-ui-restart-ticket-v4"
OWNER = "tantdna2"
OWNER_ID = 246929698
API = "https://api.github.com/repos/tantdna2/SafeShift"
ROLES = ("source_review", "independent_audit", "merge", "postmerge", "O2", "O3", "O4", "O5", "O6")
STAGES = ("launch", "admit", "setup", "reclaim", "cpu", "gpu", "native")
CLAIMS = Path("/kaggle/working/minicpm-fulltrain-claims")
_active = ContextVar("minicpm_release_context", default=None)


def github_get(path):
    """Official HTTPS, no redirects/retry/cache. Credentials never enter evidence.

    Local operations may reuse the existing gh login; Kaggle uses anonymous
    public-repository reads unless an explicit environment secret is provisioned.
    No credential is persisted or propagated into the isolated worker environment.
    """
    from urllib.request import Request, build_opener, HTTPRedirectHandler
    require(type(path) is str and (re.fullmatch(r"/(?:issues/comments|pulls)/[1-9][0-9]*", path)
        or re.fullmatch(r"/git/trees/[0-9a-f]{40}\?recursive=1", path)), "MINICPM_OFFICIAL_GITHUB_PATH")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token is None and not Path("/kaggle").is_dir():
        try:
            result = subprocess.run(["gh", "auth", "token", "--hostname", "github.com"],
                capture_output=True, timeout=5)
            if result.returncode == 0:
                token = result.stdout.decode().strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    headers = {"Accept":"application/vnd.github+json", "User-Agent":"SafeShift-MiniCPM-V2", "Cache-Control":"no-cache"}
    if token:
        require(len(token) <= 4096 and all(33 <= ord(c) < 127 for c in token), "MINICPM_INVALID_GITHUB_CREDENTIAL")
        headers["Authorization"] = "Bearer " + token
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs): return None
    url = API + path
    try:
        with build_opener(NoRedirect).open(Request(url, headers=headers), timeout=15) as response:
            require(response.geturl() == url, "MINICPM_AUTHORITY_REDIRECT")
            raw = response.read(8 * 2**20 + 1)
        require(len(raw) <= 8 * 2**20, "MINICPM_AUTHORITY_RESPONSE_BOUND")
        return strict_json(raw)
    except Exception:
        raise PermissionError("MINICPM_LIVE_GITHUB_UNAVAILABLE_OR_RATE_LIMITED_NO_OFFLINE_BYPASS") from None


def strict_json(raw):
    def pairs(items):
        obj = {}
        for key, value in items:
            require(key not in obj, "MINICPM_DUPLICATE_AUTHORITY_KEY")
            obj[key] = value
        return obj
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("MINICPM_NONFINITE_AUTHORITY")))


def public_key(value):
    require(type(value) is dict and set(value) == {"n_hex", "e"} and value["e"] == 65537
        and type(value["e"]) is int and type(value["n_hex"]) is str
        and re.fullmatch(r"[89a-f][0-9a-f]{767}", value["n_hex"]), "MINICPM_RSA3072_PUBLIC_KEY")
    require(int(value["n_hex"], 16) % 2 == 1, "MINICPM_RSA_ODD_MODULUS")
    return value


def verify_signature(key, payload, signature):
    public_key(key)
    require(type(signature) is str and re.fullmatch(r"[0-9a-f]{768}", signature), "MINICPM_SIGNATURE_SIZE")
    n, s = int(key["n_hex"], 16), int(signature, 16)
    require(s < n, "MINICPM_SIGNATURE_RANGE")
    encoded = pow(s, key["e"], n).to_bytes(384, "big")
    # Strict full encoded-message comparison; no ASN.1 parser/padding recovery.
    tail = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(json_bytes(payload)).digest()
    expected = b"\x00\x01" + b"\xff" * (384 - len(tail) - 3) + b"\x00" + tail
    require(hmac.compare_digest(encoded, expected), "MINICPM_SIGNATURE_INVALID")


def subject(grant):
    return digest({k: v for k, v in grant.items() if k != "approvals"})


def scope(value):
    r = value["request"]
    return deepcopy({k: r[k] for k in ("model_key", "source_sha256", "projection_sha256", "campaign",
        "original_inputs", "checkpoint_marker_sha256", "python_input", "resource_policy")}) | {"identity": deepcopy(r["plan"]["identity"])}


def validate(grant, *, repo=ROOT):
    fields = {"schema", "authorization", "campaign_id", "implementation_pr", "reviewed_head", "merged_sha",
        "runtime_commit", "scope", "public_key", "operator_host_sha256", "caps", "sizing", "issued_unix",
        "expires_unix", "provider_max_age_seconds", "approvals"}
    recovery = type(grant) is dict and grant.get("schema") == RECOVERY_SCHEMA
    repair = recovery and "repair" in grant
    offline = recovery and "offline" in grant
    require(type(grant) is dict and set(grant) == fields | ({"recovery"} if recovery else set()) | ({"repair"} if repair else set()) | ({"offline"} if offline else set())
        and (recovery and grant["authorization"] == "OWNER_MINICPM_TRAIN3763_RESTART_SERIAL_UI_ONLY"
             or not recovery and grant["schema"] == SCHEMA
             and grant["authorization"] == "OWNER_MINICPM_TRAIN3763_SERIAL_UI_ONLY"), "MINICPM_V2_EXPLICIT_AUTHORITY")
    contract.planning.token(grant["campaign_id"])
    require(type(grant["implementation_pr"]) is int and ((grant["implementation_pr"] > 199 if repair else grant["implementation_pr"] == 199) if recovery
        else grant["implementation_pr"] == 198), "MINICPM_REVIEWED_IMPLEMENTATION_PR")
    for field in ("runtime_commit", "reviewed_head", "merged_sha"):
        require(type(grant[field]) is str and re.fullmatch(r"[0-9a-f]{40}", grant[field]), "MINICPM_EXACT_RELEASE_COMMIT")
    public_key(grant["public_key"])
    require_hash(grant["operator_host_sha256"])
    s = grant["scope"]
    require(type(s) is dict and set(s) == {"model_key", "source_sha256", "projection_sha256", "campaign",
        "original_inputs", "checkpoint_marker_sha256", "python_input", "resource_policy", "identity"}
        and s["model_key"] == "minicpm4" and s["source_sha256"] == digest(contract.source_manifest(repo))
        and s["identity"] == contract.native_identity("minicpm4", repo), "MINICPM_REVIEWED_NATIVE_SOURCE")
    for name in ("projection_sha256", "checkpoint_marker_sha256"):
        require_hash(s[name])
    from .original_inputs import validate_binding
    validate_binding(s["original_inputs"], digest(s["original_inputs"]), s["projection_sha256"])
    from safeshift import internvl3763_python as py
    require(s["python_input"] == py.binding(), "MINICPM_RELEASE_PYTHON_INPUT")
    from .environment import policy
    policy("minicpm4", s["resource_policy"])
    caps = grant["caps"]
    require(type(caps) is dict and set(caps) == {"total_calls", "total_jobs", "total_gpu_seconds", "job_calls",
        "job_seconds", "physical_gpus", "loads_per_job", "archive_bytes"}
        and all(type(n) is int and n > 0 for n in caps.values()), "MINICPM_FINITE_CAPS")
    require(caps["total_calls"] >= 3763 and caps["job_calls"] <= 3763 and caps["job_seconds"] <= 43200
        and caps["total_jobs"] <= (3766 if recovery else 512)
        and caps["physical_gpus"] == 2 and caps["loads_per_job"] == 1 and caps["archive_bytes"] <= 7 * 2**30,
        "MINICPM_RESOURCE_SCOPE")
    for field in ("issued_unix", "expires_unix", "provider_max_age_seconds"):
        require(type(grant[field]) is int and grant[field] > 0, "MINICPM_RELEASE_TIME")
    require(grant["issued_unix"] < grant["expires_unix"] and grant["provider_max_age_seconds"] <= 3600,
        "MINICPM_FINITE_WINDOW")
    from .minicpm_sizing import validate_policy
    validate_policy(grant["sizing"], caps["job_seconds"])
    from .minicpm_recovery import SOURCE_ROLES
    require(type(grant["approvals"]) is dict and set(grant["approvals"]) == set(SOURCE_ROLES if recovery else ROLES),
            "MINICPM_O2_O6_AND_SOURCE_APPROVALS")
    if recovery:
        from .minicpm_recovery import validate_recovery
        validate_recovery(grant)
    if repair:
        from .minicpm_incident import source_incident
        source_incident(grant).validate_repair(grant)
    if offline:
        from .minicpm_offline import validate_delegation
        validate_delegation(grant)
    return grant


def load(locator, *, repo=ROOT, collection=False, reader=None, approvals=True):
    """Fresh official GitHub evidence. No CLI transport override or offline mode.

    Children may use the signed operator delegation after parent full validation;
    they still recheck the live Owner record and exact merged PR (two HTTPS GETs).
    Only the signed-ticket child entry uses approvals=False.
    """
    reader = github_get if reader is None else reader
    def fetch(loc, issue):
        require(type(loc) is dict and set(loc) == {"comment_id", "body_sha256"}
            and type(loc["comment_id"]) is int and loc["comment_id"] > 0, "MINICPM_V2_LOCATOR")
        require_hash(loc["body_sha256"])
        value = raw if loc == locator else reader("/issues/comments/" + str(loc["comment_id"]))
        require(value["id"] == loc["comment_id"] and value["user"]["login"] == OWNER
            and value["user"]["id"] == OWNER_ID and value["issue_url"] == API + "/issues/" + str(issue)
            and hashlib.sha256(value["body"].encode()).hexdigest() == loc["body_sha256"], "MINICPM_AUTHENTIC_OWNER_RECORD")
        return value
    # Locate only; authenticate author/body/issue below before trusting the record.
    require(type(locator) is dict and type(locator.get("comment_id")) is int, "MINICPM_V2_LOCATOR")
    raw = reader("/issues/comments/" + str(locator["comment_id"]))
    from .minicpm_offline import RELEASE as OFFLINE_RELEASE
    marker = OFFLINE_RELEASE if OFFLINE_RELEASE in raw["body"] else RECOVERY_MARKER if RECOVERY_MARKER in raw["body"] else MARKER
    proposed = record(raw["body"], marker)
    issue = proposed.get("implementation_pr")
    owner = fetch(locator, issue)
    grant = validate(record(owner["body"], marker), repo=repo)
    require((marker == OFFLINE_RELEASE) == ("offline" in grant), "MINICPM_EXPLICIT_OFFLINE_RELEASE_MARKER")
    pr = reader("/pulls/" + str(issue))
    require(pr["merged"] is True and pr["draft"] is False and pr["base"]["ref"] == "main"
        and pr["head"]["sha"] == grant["reviewed_head"] and pr["merge_commit_sha"] == grant["merged_sha"],
        "MINICPM_EXPANDED_REVIEW_AUDIT_MERGE_REQUIRED")
    if approvals:
        seen = {owner["id"]}
        for kind, loc in grant["approvals"].items():
            proof = fetch(loc, issue)
            require(proof["id"] not in seen, "MINICPM_SEPARATE_APPROVAL_RECORD")
            seen.add(proof["id"])
            require(record(proof["body"], APPROVAL) == {"kind": kind, "status": "APPROVED",
                "reviewed_head": grant["reviewed_head"], "subject_sha256": subject(grant)}, "MINICPM_APPROVAL_SOURCE_SCOPE")
        # Genuine source trees bind every embedded runtime byte at runtime,
        # reviewed and merged commits; a copied comment cannot approve new code.
        expected = {}
        for name in contract.sources(repo):
            raw = (Path(repo) / name).read_bytes()
            expected[name] = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if "offline" in grant:
            # Operator tools are outside the Kaggle runtime payload. Their
            # authentic release pins Git blob IDs; the local companion also
            # recomputes every SHA256/blob against its own reviewed bytes.
            expected.update(grant["offline"]["tool_blobs"])
        for ref in set((grant["runtime_commit"], grant["reviewed_head"], grant["merged_sha"])):
            tree = reader("/git/trees/" + ref + "?recursive=1")
            require(tree.get("truncated") is False and type(tree.get("tree")) is list and len(tree["tree"]) <= 20000,
                "MINICPM_COMPLETE_RELEASE_TREE")
            blobs = {v["path"]: v for v in tree["tree"]}
            require(all(name in blobs and blobs[name]["type"] == "blob" and blobs[name]["mode"] == "100644"
                and blobs[name]["sha"] == checksum for name, checksum in expected.items()), "MINICPM_MERGED_RUNTIME_BYTES")
    if grant["schema"] == RECOVERY_SCHEMA:
        from .minicpm_recovery import authenticate_recovery
        authenticate_recovery(grant, reader, rights=approvals)
    if "repair" in grant:
        from .minicpm_incident import source_incident
        source_incident(grant).authenticate_repair(grant, reader)
    now = time.time()
    require(collection or grant["issued_unix"] <= now < grant["expires_unix"], "MINICPM_AUTHORITY_EXPIRED")
    return grant


def record(body, marker):
    matches = re.findall(re.escape(marker) + r"\s*```json\s*(\{.*?\})\s*```", body, re.S)
    require(len(matches) == 1, "MINICPM_ONE_AUTHORITY_RECORD")
    return strict_json(matches[0])


def sync_directory(root):
    if os.name != "nt":
        descriptor = os.open(root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def bind(grant, value):
    from .minicpm_ui import validate as validate_spec
    validate_spec(value)
    require(digest(scope(value)) == digest(grant["scope"]), "MINICPM_TICKET_SCIENCE_SOURCE_INPUT_DRIFT")
    require(value["cohort"]["scope"] == "PRIVATE_TRAIN_METADATA", "MINICPM_NO_SYNTHETIC_PRODUCTION")
    p, caps = value["request"]["plan"], grant["caps"]
    require(p["max_calls"] <= caps["job_calls"] and p["max_seconds"] <= caps["job_seconds"]
        and p["scheduled_ordinals"], "MINICPM_JOB_FINITE_LIMITS")


def verify_ticket(grant, envelope, value, *, collection=False):
    if "offline" in grant:
        from .minicpm_offline import verify_ticket as verify_offline
        return verify_offline(grant, envelope, value, collection=collection)
    require(type(envelope) is dict and set(envelope) == {"payload", "signature"}, "MINICPM_SIGNED_TICKET_REQUIRED")
    t = envelope["payload"]
    verify_signature(grant["public_key"], t, envelope["signature"])
    recovery = grant["schema"] == RECOVERY_SCHEMA
    require(type(t) is dict and set(t) == {"schema", "grant_sha256", "value_sha256", "capsule_sha256",
        "notebook_code_sha256", "number", "previous_event_sha256", "reserved_before", "reserved_after",
        "issued_unix", "start_before_unix", "provider", "sizing"} and t["schema"] == (RECOVERY_TICKET if recovery else TICKET)
        and t["grant_sha256"] == digest(grant) and t["value_sha256"] == digest(value)
        and t["capsule_sha256"] == digest(value), "MINICPM_TICKET_BINDING")
    bind(grant, value)
    from .minicpm_incident import initial_reserved
    offset = initial_reserved(grant)["jobs"] if recovery else 0
    require(type(t["number"]) is int and t["number"] == offset + len(value["ancestors"]) + 1, "MINICPM_SERIAL_NUMBER")
    if recovery:
        require(len(value["ancestors"]) == len(value["request"]["history"]), "MINICPM_RECOVERY_COMPLETE_HISTORY")
    require_hash(t["previous_event_sha256"])
    require_hash(t["notebook_code_sha256"])
    p, caps = value["request"]["plan"], grant["caps"]
    prefix = "nguynanhtn/safeshift-minicpm-" + grant["campaign_id"] + "-"
    require(value["job"] == prefix + str(t["number"]), "MINICPM_EXACT_SERIAL_JOB")
    before, after = t["reserved_before"], t["reserved_after"]
    require(set(before) == set(after) == {"calls", "jobs", "gpu_seconds"}
        and all(type(n) is int and n >= 0 for n in [*before.values(), *after.values()])
        and before["jobs"] == t["number"] - 1, "MINICPM_RESERVATION_ACCOUNTING")
    require(after == {"calls": before["calls"] + p["max_calls"], "jobs": before["jobs"] + 1,
        "gpu_seconds": before["gpu_seconds"] + 2 * p["max_seconds"]}
        and all(after[k] <= caps["total_" + k] for k in after), "MINICPM_CAPS_NO_REFUND")
    # A finite campaign cannot silently strand its remaining IDs by reserving
    # all call/job capacity in a proposal that can cover fewer pending samples.
    remaining = max(0, p["counts"]["NOT_ATTEMPTED"] - p["max_calls"])
    require(remaining <= min(caps["total_calls"] - after["calls"],
        (caps["total_jobs"] - after["jobs"]) * caps["job_calls"]), "MINICPM_REMAINING_COVERAGE_CAPACITY")
    for field in ("issued_unix", "start_before_unix"):
        require(type(t[field]) is int, "MINICPM_TICKET_TIME")
    provider = t["provider"]
    from .minicpm_incident import release_version
    ram_repair = 'repair' in grant and release_version(grant) == 6
    require(type(provider) is dict and set(provider) == {"observed_unix", "quota", "input_versions",
        "prior_jobs", "job_absent", "owned_sha256"} | ({"current_account_safety"} if recovery else set())
        | ({"technical_predecessor"} if "repair" in grant else set())
        | ({'technical_history'} if ram_repair else set()), "MINICPM_PROVIDER_EVIDENCE")
    if "repair" in grant:
        from .minicpm_incident import source_incident
        JOB = source_incident(grant).JOB
        previous = provider["technical_predecessor"]
        require(set(previous) == {"job", "version", "state", "kernel_id"} and previous["job"] == JOB
            and previous["version"] == 1 and previous["state"] in ("COMPLETE", "ERROR")
            and type(previous["kernel_id"]) is int, "MINICPM_REPAIR_TERMINAL_PREDECESSOR")
        if ram_repair:
            from .minicpm_incident import JOB as v44_job
            require(type(provider['technical_history']) is list and len(provider['technical_history']) == 1,
                    'MINICPM_V5_ALL_TECHNICAL_HOLDS_REQUIRED')
            row = provider['technical_history'][0]
            require(set(row) == {'job', 'version', 'state', 'kernel_id'} and row['job'] == v44_job
                    and row['version'] == 1 and row['state'] in ('COMPLETE', 'ERROR')
                    and type(row['kernel_id']) is int, 'MINICPM_V5_V44_TERMINAL_REQUIRED')
    quota = provider["quota"]
    require(set(quota) == {"used", "reserved", "total"} and all(type(n) is int and n >= 0 for n in quota.values())
        and quota["reserved"] == 0 and quota["total"] - quota["used"] >= 2 * p["max_seconds"]
        and provider["job_absent"] is True, "MINICPM_PROVIDER_QUOTA_OR_OUTSTANDING_VM")
    require(type(provider["observed_unix"]) is int and t["issued_unix"] >= provider["observed_unix"]
        and t["start_before_unix"] == provider["observed_unix"] + grant["provider_max_age_seconds"]
        and grant["issued_unix"] <= t["issued_unix"] < t["start_before_unix"]
        and t["start_before_unix"] + p["max_seconds"] <= grant["expires_unix"], "MINICPM_PROVIDER_FRESH_WINDOW")
    expected = [*value["input_sources"]["dataset_sources"][:-1], *value["input_sources"]["kernel_sources"]]
    require(set(provider["input_versions"]) == set(expected), "MINICPM_PROVIDER_VERSION_SET")
    for ref, row in provider["input_versions"].items():
        require(digest(row) == digest({"ref": ref, "version": int(ref.rsplit("/", 1)[1]), "private": True}),
            "MINICPM_PROVIDER_PRIVATE_VERSION")
    if recovery:
        safety = provider["current_account_safety"]
        require(type(safety) is dict and set(safety) == {"retired_visibility", "quota", "owned_sha256", "observed_unix",
            "historical_provider_custody"} and safety["historical_provider_custody"] == "NOT_AUTHENTICATED_BY_RETIREMENT"
            and safety["owned_sha256"] == provider["owned_sha256"] and type(safety["observed_unix"]) is int
            and safety["observed_unix"] <= provider["observed_unix"] <= t["issued_unix"]
            and provider["observed_unix"] - safety["observed_unix"] <= grant["provider_max_age_seconds"],
                "MINICPM_CURRENT_ACCOUNT_SAFETY_PROOF")
        q = safety["quota"]
        require(set(q) == {"used", "reserved", "total"} and all(type(v) is int and v >= 0 for v in q.values())
            and q["reserved"] == 0 and q["used"] <= q["total"], "MINICPM_ACTIVE_SESSION_PROOF")
        require(type(safety["retired_visibility"]) is list and len(safety["retired_visibility"]) == 3,
                "MINICPM_RETIRED_CURRENT_VISIBILITY")
        for original, observed in zip(grant["recovery"]["journals"], safety["retired_visibility"]):
            require(type(observed) is dict and observed.get("job") == original["job"] and (
                observed == {"job": original["job"], "visibility": "NOT_VISIBLE_NOW_NOT_VERIFIED_DELETED"}
                or set(observed) == {"job", "visibility", "current_state"} and observed["visibility"] == "VISIBLE"
                and observed["current_state"] in ("COMPLETE", "ERROR", "CANCELLED")), "MINICPM_RETIRED_ACTIVE_OR_FALSE_DELETION")
        prior = provider["prior_jobs"]
        require(type(prior) is list and len(prior) == len(value["ancestors"]), "MINICPM_RECOVERY_PROVIDER_LINEAGE")
        expected_before = initial_reserved(grant)
        for i, row in enumerate(prior, offset + 1):
            require(set(row) == {"job", "version", "state", "kernel_id", "ticket"}
                and row["job"] == prefix + str(i) and row["version"] == 1 and row["state"] == "COMPLETE",
                    "MINICPM_PENDING_ONLY_PROVIDER_LINEAGE")
            old = row["ticket"]
            verify_signature(grant["public_key"], old["payload"], old["signature"])
            p_old = old["payload"]
            require(p_old["grant_sha256"] == digest(grant) and p_old["schema"] == RECOVERY_TICKET
                and p_old["number"] == i and p_old["reserved_before"] == expected_before
                and p_old["reserved_after"] == {"calls": expected_before["calls"] + p_old["sizing"]["calls"],
                    "jobs": expected_before["jobs"] + 1,
                    "gpu_seconds": expected_before["gpu_seconds"] + 2 * p_old["sizing"]["seconds"]},
                    "MINICPM_PENDING_ONLY_NO_BUDGET_RESET")
            expected_before = p_old["reserved_after"]
        require(t["reserved_before"] == expected_before, "MINICPM_RECOVERY_NO_HISTORY_OR_BUDGET_RESET")
    else:
        require(type(provider["prior_jobs"]) is list and len(provider["prior_jobs"]) == t["number"] - 1 and all(
            row["job"] == prefix + str(i) and row["version"] == 1 and row["state"] == "COMPLETE"
            for i, row in enumerate(provider["prior_jobs"], 1)), "MINICPM_PRIOR_PROVIDER_TERMINAL")
    require(t["sizing"]["calls"] == p["max_calls"] and t["sizing"]["seconds"] == p["max_seconds"], "MINICPM_SIGNED_SIZING")
    require_hash(provider["owned_sha256"])
    if not collection:
        require(t["issued_unix"] <= time.time() < grant["expires_unix"], "MINICPM_TICKET_EXPIRED")
    return t


def current():
    return _active.get()


class GuardedBackend:
    """Authorize the existing adapter immediately before generate, after start.

    No output/precision/parser transformation and no alternative model backend.
    """
    def __init__(self, backend, ordinal):
        self.backend, self.ordinal = backend, ordinal

    def __getattr__(self, name):
        return getattr(self.backend, name)

    def generate(self, image, evidence):
        authorize("call", ordinal=self.ordinal)
        c = current()
        if c["grant"]["schema"] == RECOVERY_SCHEMA:
            from unittest.mock import patch
            from .minicpm_recovery import native_started
            # Observe precisely model.generate, after unchanged backend image
            # decode/processor/transfer and native_call.json durable write.
            model = self.backend.model
            native_generate = model.generate
            row = c["value"]["cohort"]["samples"][self.ordinal]
            def observed_generate(*args, **kwargs):
                from . import memory
                memory.resource_check(c['value']['request'], evidence, 'before-model-generate')
                native_started(self.ordinal, row["sample_id"], row["image_sha256"])
                return native_generate(*args, **kwargs)
            with patch.object(model, "generate", observed_generate):
                return self.backend.generate(image, evidence)
        return self.backend.generate(image, evidence)


def claim(kind):
    c = current()
    require(c is not None, "MINICPM_NO_ACTIVE_CAPABILITY")
    root, ticket, request = c["claims"], c["ticket"]["payload"], c["value"]["request"]
    from safeshift.candidates.train_history import lease_key
    with lease_key(root, digest({"scope": TICKET, "ticket": digest(c["ticket"])})):
        if kind in STAGES[1:]:
            require((root / (STAGES[STAGES.index(kind) - 1] + ".json")).is_file(), "MINICPM_PARENT_STAGE_CLAIM")
        elif kind == "load":
            require((root / "native.json").is_file(), "MINICPM_LOAD_NATIVE_PHASE")
        elif kind.startswith("call-"):
            i = int(kind[5:])
            require((root / "load.json").is_file(), "MINICPM_CALL_REQUIRES_LOAD")
            previous = list(root.glob("call-*.json"))
            require(len(previous) < len(request["plan"]["scheduled_ordinals"])
                and i == request["plan"]["scheduled_ordinals"][len(previous)], "MINICPM_ORDERED_CALL_NO_REPLAY")
        else:
            require(kind == "launch", "MINICPM_CLAIM_KIND")
        receipt = {"kind": kind, "ticket_sha256": digest(c["ticket"]), "request_sha256": digest(request),
            "number": ticket["number"], "time_unix": c["started_unix"] if kind == "launch" else time.time()}
        write(root / (kind + ".json"), receipt)
        sync_directory(root)
        return receipt


def authorize(kind=None, *, request=None, ordinal=None):
    c = current()
    if c is None:
        raise PermissionError("ISSUE171_NO_GPU_INFERENCE_PRIVATE_INPUT: RELEASE_O2_O6_G0_G6_BLOCKED")
    require(request is None or digest(request) == digest(c["value"]["request"]), "MINICPM_CAPABILITY_REQUEST")
    r = c["value"]["request"]
    launch = read(c["claims"] / "launch.json")
    require(time.time() < min(c["grant"]["expires_unix"], launch["time_unix"] + r["plan"]["max_seconds"]),
        "MINICPM_ACTIVE_DEADLINE")
    require(c["phase"] == "native" or kind not in ("load", "call"), "MINICPM_NATIVE_PHASE_ONLY")
    if kind == "load":
        return claim("load")
    if kind == "call":
        require(type(ordinal) is int and ordinal in r["plan"]["scheduled_ordinals"], "MINICPM_AUTHORIZED_ORDINAL")
        return claim(f"call-{ordinal:06d}")
    return c["grant"]


@contextmanager
def activate(locator, envelope, value, phase, *, repo=ROOT, child=False):
    began = time.time()
    grant = load(locator, repo=repo, approvals=not child)
    with _activated(grant, locator, envelope, value, phase, repo=repo, child=child,
                    started_unix=began if phase == "launch" else None) as context:
        yield context


@contextmanager
def _activated(grant, locator, envelope, value, phase, *, repo=ROOT, child=False, started_unix=None):
    """Internal composition after live authentication; never exposed as a CLI."""
    require(current() is None and phase in STAGES and (phase == "launch") != child, "MINICPM_CAPABILITY_PHASE")
    validate(grant, repo=repo)
    ticket = verify_ticket(grant, envelope, value)
    root = safe(CLAIMS, grant["campaign_id"] + "/" + str(ticket["number"]))
    if phase == "launch":
        require(time.time() < ticket["start_before_unix"], "MINICPM_STALE_PROVIDER_BEFORE_LAUNCH")
        started_unix = time.time() if started_unix is None else started_unix
        require(type(started_unix) in (int,float) and ticket["issued_unix"] <= started_unix <= time.time(),
            "MINICPM_START_INCLUDES_BOOTSTRAP_AUTHORITY_AND_HISTORY")
        root.mkdir(parents=True, exist_ok=False)
        (root / "attempts").mkdir()
    else:
        snapshot_stat(root, directory=True)
        launch = read(root / "launch.json")
        require(launch["ticket_sha256"] == digest(envelope)
            and launch["request_sha256"] == digest(value["request"]), "MINICPM_CHILD_LAUNCH_BINDING")
    token = _active.set({"grant": grant, "ticket": envelope, "value": value, "phase": phase, "claims": root,
                         "locator": locator, "repo": str(repo), "started_unix":started_unix})
    try:
        claim(phase)
        yield current()
    finally:
        _active.reset(token)


def claims_snapshot():
    c = current()
    require(c is not None, "MINICPM_NO_CAPABILITY_SNAPSHOT")
    return {p.name: read(p) for p in sorted(c["claims"].glob("*.json"))}
