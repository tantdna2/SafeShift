"""Issue202 delegation and tickets. Local observations never claim provider proof.

The inherited V4 rights, finite caps, V5 failure and RAM repair remain mandatory.
Only a NEW exact-source release can delegate offline serial preparation. This
module has no signer, SDK, journal writer, network fallback or inference loop.
"""
from copy import deepcopy
import math
import re
import time

from safeshift.candidates.source import ROOT, require
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
LAUNCH_SECONDS = 2400
NATIVE_PRE_CALL_SECONDS = 900
NATIVE_SEAL_SECONDS = 300
SUPERVISOR_SEAL_SECONDS = 120
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
        | ({"serial7"} if transition else set()) | ({"serial8", "resident_gpu0_min_free_mib"} if after_serial8 else set())
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
        floor = d["resident_gpu0_min_free_mib"]
        admission = grant["scope"]["resource_policy"]["free_gpu0_runtime_mib"]
        require(type(floor) is int and min(256, admission) <= floor <= admission,
            "MINICPM_RELEASED_RESIDENT_GPU0_FLOOR")
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


def recovery_cpu_seconds(budgets):
    return max(1200, budgets["diagnostic_seconds"])


def serial22_recovery(grant):
    return "previous_source_sha256" in grant.get("continuation", {})


def recovery_stage_seconds(budgets, *, extended):
    diagnostic = budgets["diagnostic_seconds"]
    return {"admit": max(1800, diagnostic) if extended else diagnostic,
            "setup": budgets["setup_seconds"], "reclaim": diagnostic,
            "cpu": recovery_cpu_seconds(budgets), "gpu": diagnostic}


def recovery_pre_native_seconds(grant):
    extended = serial22_recovery(grant)
    return sum(recovery_stage_seconds(grant["scope"]["resource_policy"], extended=extended).values()) + (
        LAUNCH_SECONDS if extended else 0)


def recovery_overhead_seconds(grant):
    return recovery_pre_native_seconds(grant) + (
        NATIVE_PRE_CALL_SECONDS + NATIVE_SEAL_SECONDS if serial22_recovery(grant) else 0)


def require_recovery_envelope(grant, seconds):
    overhead = recovery_overhead_seconds(grant)
    sizing = grant["sizing"]
    require(seconds > overhead + sizing["export_seconds"] + sizing["first_call_seconds"],
            "MINICPM_RECOVERY_STAGE_RESERVE_CANNOT_FIT")
    return overhead


def verify_export_timing(grant, value, timing, call_seconds):
    elapsed = timing["seconds_before_supervisor_export"]
    reserve = grant["sizing"]["export_seconds"]
    tail = SUPERVISOR_SEAL_SECONDS if serial22_recovery(grant) else reserve
    require(type(elapsed) in (int, float) and math.isfinite(elapsed) and sum(call_seconds) <= elapsed
        and timing["export_reserve_seconds"] == reserve
        and elapsed + tail < value["request"]["plan"]["max_seconds"], "MINICPM_EXPORT_TIME_RESERVE_CUSTODY")
    return max(0.001, elapsed - sum(call_seconds))


def recovery_call_capacity(grant, seconds, overhead, per_call, *, measured):
    policy = grant["sizing"]
    available = seconds - overhead - policy["export_seconds"]
    if measured:
        # Retain the signed minimum time before each live call. In a batch
        # estimate it is a tail allowance, with measured latency charged per image.
        available -= policy["first_call_seconds"]
    return available // per_call


def verify_ticket(grant, envelope, value, *, collection=False, repo=ROOT):
    validate_delegation(grant)
    require(type(envelope) is dict and set(envelope) == {"payload", "signature"}, "MINICPM_SIGNED_OFFLINE_TICKET")
    t = envelope["payload"]
    a.verify_signature(grant["public_key"], t, envelope["signature"])
    closable = grant["offline"]["schema"] == SERIAL9_SCHEMA
    require(type(t) is dict and set(t) == {"schema", "grant_sha256", "value_sha256", "capsule_sha256",
        "notebook_code_sha256", "number", "previous_event_sha256", "reserved_before", "reserved_after",
        "issued_unix", "start_before_unix", "owner_gate", "sizing", "lineage"} | ({"closures"} if closable else set())
        and t["schema"] == ticket_schema(grant)
        and t["grant_sha256"] == digest(grant)
        and t["value_sha256"] == t["capsule_sha256"] == digest(value), "MINICPM_OFFLINE_TICKET_BINDING")
    if repo == ROOT:
        a.bind(grant, value)
    else:
        a.bind(grant, value, repo=repo)
    require_hash(t["notebook_code_sha256"]); require_hash(t["previous_event_sha256"])
    p, caps = value["request"]["plan"], grant["caps"]
    closures = t["closures"] if closable else []
    require(type(closures) is list, "MINICPM_OFFLINE_PRE_NATIVE_CLOSURES")
    require(type(t["number"]) is int and t["number"] == first_serial(grant) + len(value["ancestors"]) + len(closures)
        and value["job"] == "nguynanhtn/safeshift-minicpm-" + grant["campaign_id"] + "-" + str(t["number"]),
        "MINICPM_OFFLINE_SERIAL7_NO_REPLAY")
    if "continuation" in grant:
        require(t["number"] >= grant["continuation"]["first_serial"], "MINICPM_SOURCE_TRANSITION_SERIAL")
        require_recovery_envelope(grant, p["max_seconds"])
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
    for entry, history in zip(t["lineage"], value["request"]["history"]):
        require(type(entry) is dict and set(entry) == {"number", "ticket_sha256", "history_sha256",
            "owner_receipt_sha256", "reserved_after"} and entry["history_sha256"] == digest(history),
            "MINICPM_OFFLINE_LINEAGE_ORDER")
        for k in ("ticket_sha256", "owner_receipt_sha256"): require_hash(entry[k])
        if serial22_recovery(grant):
            from . import contract
            require(type(entry["number"]) is int, "MINICPM_OFFLINE_LINEAGE_ORDER")
            source = contract.V5_SOURCE if entry["number"] < 20 else contract.PR211_SOURCE
            if entry["number"] >= grant["continuation"]["first_serial"]:
                source = grant["scope"]["source_sha256"]
            require(history["identity"]["implementation_sha256"] == source, "MINICPM_HISTORY_SERIAL_SOURCE")
    for entry in closures:
        require(type(entry) is dict and set(entry) == {"number", "ticket_sha256", "closure_sha256",
            "local_sha256", "fingerprint_sha256", "reserved_after"}, "MINICPM_OFFLINE_PRE_NATIVE_CLOSURE_FIELDS")
        for k in ("ticket_sha256", "closure_sha256", "local_sha256", "fingerprint_sha256"): require_hash(entry[k])
    # Completed and pre-native-closed serials form ONE contiguous numbered hold
    # chain: every closed job keeps its full reservation, nothing is refunded.
    require(all(type(e["number"]) is int for e in t["lineage"] + closures)
        and [e["number"] for e in closures] == sorted(e["number"] for e in closures), "MINICPM_OFFLINE_LINEAGE_ORDER")
    merged = sorted(t["lineage"] + closures, key=lambda entry: entry["number"])
    require([entry["number"] for entry in merged] == list(range(first_serial(grant), first_serial(grant) + len(merged)))
        and [e["number"] for e in t["lineage"]] == sorted(e["number"] for e in t["lineage"]),
        "MINICPM_OFFLINE_LINEAGE_ORDER")
    for entry in merged:
        after = entry["reserved_after"]
        amounts(before, after, caps)
        before = after
    require(t["reserved_before"] == before, "MINICPM_OFFLINE_NO_HOLD_RESET")
    amounts(before, t["reserved_after"], caps, calls=p["max_calls"], seconds=p["max_seconds"])
    require(t["sizing"]["calls"] == p["max_calls"] and t["sizing"]["seconds"] == p["max_seconds"],
        "MINICPM_OFFLINE_SIGNED_LIMITS")
    if serial22_recovery(grant):
        sizing = t["sizing"]
        floor = recovery_overhead_seconds(grant)
        first_call = grant["sizing"]["first_call_seconds"]
        approved = grant["continuation"]["pr211_call_bound"]
        overhead, per_call = sizing["overhead_bound_seconds"], sizing["per_call_estimate_seconds"]
        status = sizing["status"]
        measured = status in ("OWNER_APPROVED_PR211_ESTIMATE", "MEASURED_SAME_SOURCE_ESTIMATE_NOT_POPULATION_GUARANTEE")
        require(type(overhead) is int and overhead >= floor and type(per_call) is int and per_call > 0
            and (measured or per_call >= first_call) and p["max_calls"] <= recovery_call_capacity(
                grant, p["max_seconds"], overhead, per_call, measured=measured),
            "MINICPM_RECOVERY_SIGNED_CALL_BUDGET")
        if status == "OWNER_APPROVED_PR211_ESTIMATE":
            require(approved is not None and overhead >= approved["overhead_seconds"]
                and per_call >= approved["call_seconds"] and sizing["throughput_source"] == approved["telemetry_sha256"],
                "MINICPM_RECOVERY_APPROVED_TIMING_BOUND")
        elif measured:
            require(any(entry["number"] >= grant["continuation"]["first_serial"] for entry in t["lineage"]),
                    "MINICPM_MEASURED_SOURCE_LINEAGE_REQUIRED")
        else:
            require(p["max_calls"] <= grant["offline"]["unmeasured_calls"], "MINICPM_UNMEASURED_RELEASE_CAP")
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
    from .minicpm_sizing import measured_bounds, propose
    extended = serial22_recovery(grant)
    p = propose(grant, pending, reserved, {"quota": gate["quota"], "observed_unix": gate["observed_unix"]},
                None if extended else telemetry)
    overhead = require_recovery_envelope(grant, p["seconds"]) if "continuation" in grant else 0
    if extended:
        approved = grant["continuation"]["pr211_call_bound"]
        observed, per_call = measured_bounds(grant, telemetry, grant["scope"]["source_sha256"]) if telemetry else (0, 0)
        if per_call:
            p["status"] = "MEASURED_SAME_SOURCE_ESTIMATE_NOT_POPULATION_GUARANTEE"
        elif approved is not None:
            observed, per_call = max(observed, approved["overhead_seconds"]), approved["call_seconds"]
            p["status"] = "OWNER_APPROVED_PR211_ESTIMATE"
            p["throughput_source"] = approved["telemetry_sha256"]
        measured = per_call > 0
        p["overhead_bound_seconds"] = max(overhead, observed)
        p["per_call_estimate_seconds"] = per_call or grant["sizing"]["first_call_seconds"]
        p["calls"] = min(p["calls"], recovery_call_capacity(grant, p["seconds"],
            p["overhead_bound_seconds"], p["per_call_estimate_seconds"], measured=measured))
        if not measured:
            p["calls"] = min(p["calls"], grant["offline"]["unmeasured_calls"])
            p["status"] = "UNMEASURED_CONSERVATIVE_CAP_NOT_THROUGHPUT"
        require(p["calls"] > 0, "MINICPM_RECOVERY_CALL_BUDGET_CANNOT_FIT")
        return p
    if telemetry is None:
        p["calls"] = min(p["calls"], grant["offline"]["unmeasured_calls"],
            (p["seconds"] - overhead - grant["sizing"]["export_seconds"]) // grant["sizing"]["first_call_seconds"])
        require(p["calls"] > 0, "MINICPM_OFFLINE_INITIAL_ENVELOPE")
        p["status"] = "UNMEASURED_CONSERVATIVE_CAP_NOT_THROUGHPUT"
    return p
