"""Issue202 delegation and tickets. Local observations never claim provider proof.

The inherited V4 rights, finite caps, V5 failure and RAM repair remain mandatory.
Only a NEW exact-source release can delegate offline serial preparation. This
module has no signer, SDK, journal writer, network fallback or inference loop.
"""
from copy import deepcopy
import math
import re
import time

from safeshift.candidates.source import require
from safeshift.pilot.contract import digest, require_hash
from . import minicpm_release as a, minicpm_v5_incident as v5, minicpm_serial6 as serial6

SCHEMA = "safeshift-minicpm-offline-continuation-v3"
RELEASE = "SAFESHIFT_MINICPM_OFFLINE_RELEASE_V3"
TICKET = "safeshift-minicpm-offline-ticket-v3"
TRANSITION_SCHEMA = "safeshift-minicpm-offline-continuation-v4"
TRANSITION_RELEASE = "SAFESHIFT_MINICPM_OFFLINE_RELEASE_V4"
TRANSITION_TICKET = "safeshift-minicpm-offline-ticket-v4"
SERIAL9_SCHEMA = "safeshift-minicpm-offline-continuation-v5"
SERIAL9_RELEASE = "SAFESHIFT_MINICPM_OFFLINE_RELEASE_V5"
SERIAL9_TICKET = "safeshift-minicpm-offline-ticket-v5"
FINAL = "SAFESHIFT_MINICPM_OFFLINE_FINAL_V2"
RELEASE_SECONDS = 30 * 24 * 3600
ORIGINAL_SESSION = "0b1d115c-c002-44e8-b22e-087226f6dc73"
RECONCILED = "MINICPM_OFFLINE_CAMPAIGN_RECONCILED"
EXCLUDED_SESSION = "a5fa95c9-bbc0-4df2-bdc7-ecb56b098bbc"
TOOLS = ("minicpm_offline_continuation.py", "owner_verify_minicpm_offline.py",
    "minicpm_fulltrain_operator.py", "minicpm_fulltrain_recovery.py", "minicpm_v5_incident.py",
    "minicpm_v44_incident.py", "minicpm_fulltrain_transport.py", "reconcile_train3763_manual.py",
    "submit_internvl_v2.py", "generate_minicpm_fulltrain_notebook.py", "build_fresh_fulltrain_notebooks.py")


def validate_delegation(grant):
    d = grant["offline"]
    transition = a.uses_proof(grant)
    after_serial8 = d.get("schema") == SERIAL9_SCHEMA
    require(type(d) is dict and set(d) == {"schema", "decision_issue", "operator_session",
        "base_journal_head_sha256", "tools_sha256", "tool_blobs", "unmeasured_calls", "serial6_event_sha256", "serial6_supervisor_sha256"}
        | ({"serial7"} if transition else set()) | ({"serial8"} if after_serial8 else set())
        and d["schema"] in (SCHEMA, TRANSITION_SCHEMA, SERIAL9_SCHEMA) and d["decision_issue"] == 202
        and grant["schema"] == a.RECOVERY_SCHEMA and grant["implementation_pr"] > 204
        and grant["scope"]["source_sha256"] != serial6.SOURCE
        and d["serial6_event_sha256"] == serial6.EVENT_SHA and d["serial6_supervisor_sha256"] == serial6.ZIP_SHA
        and grant["repair"]["schema"] == v5.SCHEMA, "MINICPM_NEW_OFFLINE_AUTHORITY_REQUIRED")
    require(type(d["operator_session"]) is str and re.fullmatch(
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", d["operator_session"])
        and d["operator_session"] == ORIGINAL_SESSION, "MINICPM_ORIGINAL_OPERATOR_SESSION_REQUIRED")
    for name in ("base_journal_head_sha256", "tools_sha256"):
        require_hash(d[name])
    require(type(d["tool_blobs"]) is dict and set(d["tool_blobs"]) == {"scripts/"+name for name in TOOLS}
        and all(type(h) is str and re.fullmatch(r"[0-9a-f]{40}", h) for h in d["tool_blobs"].values()),
        "MINICPM_EXACT_REVIEWED_TOOL_BLOBS")
    require(d["base_journal_head_sha256"] == grant["repair"]["journal_head_sha256"],
        "MINICPM_OFFLINE_EXACT_PRE_SERIAL6_HEAD")
    require(type(d["unmeasured_calls"]) is int and d["unmeasured_calls"] == 100,
        "MINICPM_EXPLICIT_CONSERVATIVE_INITIAL_CAP")
    require(type(grant["issued_unix"]) is int and grant["issued_unix"] > 0
        and type(grant["expires_unix"]) is int
        and grant["expires_unix"] == grant["issued_unix"] + RELEASE_SECONDS,
        "MINICPM_OFFLINE_EXACT_30_DAY_RELEASE")
    require(0 < grant["caps"]["job_seconds"] <= 4 * 3600, "MINICPM_OFFLINE_FOUR_HOUR_JOB_CAP")
    if transition:
        from . import minicpm_serial7
        minicpm_serial7.validate_transition(grant)
    if after_serial8:
        from . import minicpm_serial8
        minicpm_serial8.validate_transition(grant)
    return d


def first_serial(grant):
    return {TRANSITION_SCHEMA: 8, SERIAL9_SCHEMA: 9}.get(grant["offline"]["schema"], serial6.FIRST_SERIAL)


def ticket_schema(grant):
    return {SCHEMA: TICKET, TRANSITION_SCHEMA: TRANSITION_TICKET, SERIAL9_SCHEMA: SERIAL9_TICKET}[grant["offline"]["schema"]]


def initial_hold(grant):
    if grant["offline"]["schema"] == SERIAL9_SCHEMA:
        from .minicpm_serial8 import RESERVED
        return deepcopy(RESERVED)
    if a.uses_proof(grant):
        from .minicpm_serial7 import RESERVED
        return deepcopy(RESERVED)
    return deepcopy(serial6.RESERVED)


def number(n, *, integer=False):
    require(type(n) is int if integer else type(n) in (int, float) and math.isfinite(n),
        "MINICPM_OFFLINE_FINITE_NUMBER")
    require(n >= 0, "MINICPM_OFFLINE_NONNEGATIVE_NUMBER")
    return n


def owner_gate(grant, gate, value, *, now=None):
    """Owner UI observations, not an authenticated remote provider receipt."""
    require(type(gate) is dict and set(gate) == {"observed_unix", "quota", "job", "version",
        "inputs", "no_active_job", "job_absent", "owner_checked", "proof_sha256"}, "MINICPM_OWNER_UI_GATE_FIELDS")
    now = time.time() if now is None else now
    number(gate["observed_unix"], integer=True)
    require(gate["observed_unix"] <= now < gate["observed_unix"] + grant["provider_max_age_seconds"]
        and gate["job"] == value["job"] and type(gate["version"]) is int and gate["version"] == 1
        and gate["inputs"] == value["input_sources"] and gate["no_active_job"] is True
        and gate["job_absent"] is True and gate["owner_checked"] is True, "MINICPM_FRESH_OWNER_QUOTA_INPUT_GATE")
    require_hash(gate["proof_sha256"])
    q = gate["quota"]
    require(type(q) is dict and set(q) == {"used", "reserved", "total"}, "MINICPM_OWNER_QUOTA_FIELDS")
    for n in q.values(): number(n, integer=True)
    require(q["used"] <= q["total"] and q["reserved"] == 0, "MINICPM_OWNER_ACTIVE_QUOTA_STOP")
    return gate


def terminal(receipt, value, attempt_sha, supervisor_sha):
    require(type(receipt) is dict and set(receipt) == {"job", "version", "kernel_id", "state",
        "archive_sha256", "supervisor_sha256", "owner_downloaded_unix", "no_other_job_or_version",
        "no_api_submission", "proof_sha256"}, "MINICPM_TERMINAL_OWNER_RECEIPT_REQUIRED")
    require(receipt["job"] == value["job"] and type(receipt["version"]) is int and receipt["version"] == 1
        and type(receipt["kernel_id"]) is int and receipt["kernel_id"] > 0 and receipt["state"] == "COMPLETE"
        and receipt["archive_sha256"] == attempt_sha and receipt["supervisor_sha256"] == supervisor_sha
        and receipt["no_other_job_or_version"] is True and receipt["no_api_submission"] is True,
        "MINICPM_TERMINAL_HASH_VERSION_OR_AMBIGUITY_STOP")
    number(receipt["owner_downloaded_unix"])
    require(0 < receipt["owner_downloaded_unix"] <= time.time(), "MINICPM_OWNER_DOWNLOAD_TIME")
    require_hash(receipt["proof_sha256"])
    return receipt


def verify_ticket(grant, envelope, value, *, collection=False):
    validate_delegation(grant)
    require(type(envelope) is dict and set(envelope) == {"payload", "signature"}, "MINICPM_SIGNED_OFFLINE_TICKET")
    t = envelope["payload"]
    a.verify_signature(grant["public_key"], t, envelope["signature"])
    require(type(t) is dict and set(t) == {"schema", "grant_sha256", "value_sha256", "capsule_sha256",
        "notebook_code_sha256", "number", "previous_event_sha256", "reserved_before", "reserved_after",
        "issued_unix", "start_before_unix", "owner_gate", "sizing", "lineage"}
        and t["schema"] == ticket_schema(grant)
        and t["grant_sha256"] == digest(grant)
        and t["value_sha256"] == t["capsule_sha256"] == digest(value), "MINICPM_OFFLINE_TICKET_BINDING")
    a.bind(grant, value)
    require_hash(t["notebook_code_sha256"]); require_hash(t["previous_event_sha256"])
    p, caps = value["request"]["plan"], grant["caps"]
    require(type(t["number"]) is int and t["number"] == first_serial(grant) + len(value["ancestors"])
        and value["job"] == "nguynanhtn/safeshift-minicpm-" + grant["campaign_id"] + "-" + str(t["number"]),
        "MINICPM_OFFLINE_SERIAL7_NO_REPLAY")
    if grant["offline"]["schema"] == SERIAL9_SCHEMA:
        require(value["capsule_ref"] == "nguynanhtn/safeshift-minicpm-capsule-"
            + grant["campaign_id"] + "-" + str(t["number"]) + "/1", "MINICPM_SERIAL9_FRESH_CAPSULE_REQUIRED")
    require(type(t["lineage"]) is list and len(t["lineage"]) == len(value["request"]["history"]),
        "MINICPM_OFFLINE_ALL_PREDECESSORS")
    before = initial_hold(grant)
    if a.uses_proof(grant) and not t["lineage"]:
        require(value["ancestors"] == value["request"]["history"] == []
            and p["action"] == "initial" and p["counts"] == {"NOT_ATTEMPTED": 3763}
            and p["scheduled_ordinals"][0] == 0, "MINICPM_SERIAL8_EMPTY_HISTORY")
    for i, (entry, history) in enumerate(zip(t["lineage"], value["request"]["history"]), first_serial(grant)):
        require(set(entry) == {"number", "ticket_sha256", "history_sha256", "owner_receipt_sha256", "reserved_after"}
            and entry["number"] == i and entry["history_sha256"] == digest(history), "MINICPM_OFFLINE_LINEAGE_ORDER")
        for k in ("ticket_sha256", "owner_receipt_sha256"): require_hash(entry[k])
        after = entry["reserved_after"]
        amounts(before, after, caps)
        before = after
    require(t["reserved_before"] == before, "MINICPM_OFFLINE_NO_HOLD_RESET")
    amounts(before, t["reserved_after"], caps, calls=p["max_calls"], seconds=p["max_seconds"])
    require(t["sizing"]["calls"] == p["max_calls"] and t["sizing"]["seconds"] == p["max_seconds"],
        "MINICPM_OFFLINE_SIGNED_LIMITS")
    if not t["lineage"]:
        require(p["max_calls"] <= min(grant["offline"]["unmeasured_calls"],
            (p["max_seconds"]-grant["sizing"]["export_seconds"]) // grant["sizing"]["first_call_seconds"]),
            "MINICPM_UNMEASURED_RELEASE_CAP")
    gate = owner_gate(grant, t["owner_gate"], value, now=t["issued_unix"])
    for n in (t["issued_unix"], t["start_before_unix"]): number(n, integer=True)
    require(grant["issued_unix"] <= t["issued_unix"] < t["start_before_unix"]
        == gate["observed_unix"] + grant["provider_max_age_seconds"]
        and t["start_before_unix"] + p["max_seconds"] <= grant["expires_unix"]
        and 2 * p["max_seconds"] <= gate["quota"]["total"] - gate["quota"]["used"],
        "MINICPM_OFFLINE_EXPIRY_OR_QUOTA")
    remaining = p["counts"]["NOT_ATTEMPTED"] - p["max_calls"]
    require(remaining <= min(caps["total_calls"] - t["reserved_after"]["calls"],
        (caps["total_jobs"] - t["reserved_after"]["jobs"]) * caps["job_calls"]), "MINICPM_OFFLINE_REMAINDER_CAPACITY")
    if not collection:
        require(t["issued_unix"] <= time.time() < grant["expires_unix"],
            "MINICPM_OFFLINE_TICKET_EXPIRED")
    return t


def amounts(before, after, caps, *, calls=None, seconds=None):
    require(type(before) is dict and type(after) is dict and set(before) == set(after) == {"calls", "jobs", "gpu_seconds"},
        "MINICPM_OFFLINE_RESERVATION_FIELDS")
    for n in [*before.values(), *after.values()]: number(n, integer=True)
    dc, ds = after["calls"] - before["calls"], after["gpu_seconds"] - before["gpu_seconds"]
    require(after["jobs"] == before["jobs"] + 1 and 0 < dc <= caps["job_calls"]
        and 0 < ds <= 2 * caps["job_seconds"] and ds % 2 == 0
        and (calls is None or dc == calls) and (seconds is None or ds == 2 * seconds)
        and all(after[k] <= caps["total_" + k] for k in after), "MINICPM_OFFLINE_NO_REFUND_OR_CAP_CHANGE")


def proposal(grant, pending, reserved, gate, telemetry=None):
    from .minicpm_sizing import propose
    p = propose(grant, pending, reserved, {"quota": gate["quota"], "observed_unix": gate["observed_unix"]}, telemetry)
    if telemetry is None:
        p["calls"] = min(p["calls"], grant["offline"]["unmeasured_calls"],
            (p["seconds"] - grant["sizing"]["export_seconds"]) // grant["sizing"]["first_call_seconds"])
        require(p["calls"] > 0, "MINICPM_OFFLINE_INITIAL_ENVELOPE")
        p["status"] = "UNMEASURED_CONSERVATIVE_CAP_NOT_THROUGHPUT"
    return p
