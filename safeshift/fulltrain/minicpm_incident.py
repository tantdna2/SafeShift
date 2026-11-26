"""Exact V4-4 pre-native incident custody and source transition contract.

This is a technical closure, never a collected prediction, refund or permission.
The previous signed release/ticket are immutable, content-addressed history.
"""
from copy import deepcopy
import hashlib
import math
from pathlib import Path
import tempfile

from safeshift.candidates.source import require, snapshot_stat
from safeshift.pilot.artifacts import read, sha, import_archive
from safeshift.pilot.contract import digest, require_hash
from . import minicpm_release as a, minicpm_ui as ui

SCHEMA = "safeshift-minicpm-v44-source-repair-v1"
DIRECTIVE = 6922725439
PREVIOUS_GRANT = "391be7d44949383710313121de630b78b6bc4571cea443166c6561e406d64df0"
PREVIOUS_TICKET = "61c2e7fafddac01d9a09e41f866ef041b746a23fda75f186a08d43a0b6bc4946"
PREVIOUS_VALUE = "aa4c450de4fdcddb2ad4861a8cea2b76133ea1830fe3d57e19a0936e15cf6d58"
PREVIOUS_SOURCE = "4b4f6bcccaaaa1793da3240bf9f4640e7a0796c9d1b615db0a627d4965a356c9"
PREVIOUS_MERGE = "92e7af41b3102cac16609908c88688f4049b4cc1"
RESERVED = {"calls": 6763, "jobs": 4, "gpu_seconds": 115200}
JOB = "nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-4"


def source_incident(grant):
    """Explicit version dispatch; unknown/repeated transitions cannot activate."""
    from . import minicpm_v5_incident
    schema = grant['repair']['schema']
    require(schema in (SCHEMA, minicpm_v5_incident.SCHEMA), 'MINICPM_UNKNOWN_SOURCE_TRANSITION')
    if schema == minicpm_v5_incident.SCHEMA:
        return minicpm_v5_incident
    import sys
    return sys.modules[__name__]


def release_version(grant):
    if 'repair' in grant:
        return 6 if source_incident(grant).DIRECTIVE == 6937169950 else 5
    return 4


def initial_reserved(grant):
    return deepcopy(grant["repair"]["reserved_after"] if "repair" in grant else grant["recovery"]["reserved"])


def owner_record(reader, locator, issue):
    from .minicpm_recovery import locator as validate_locator
    validate_locator(locator)
    row = reader("/issues/comments/" + str(locator["comment_id"]))
    require(row["id"] == locator["comment_id"] and row["user"]["login"] == a.OWNER
        and row["user"]["id"] == a.OWNER_ID and row["issue_url"] == a.API + "/issues/" + str(issue)
        and hashlib.sha256(row["body"].encode()).hexdigest() == locator["body_sha256"], "MINICPM_REPAIR_AUTHENTIC_RECORD")
    return row


def previous_release(reader, locator):
    old = a.record(owner_record(reader, locator, 199)["body"], a.RECOVERY_MARKER)
    require(digest(old) == PREVIOUS_GRANT and old["implementation_pr"] == 199
        and old["merged_sha"] == PREVIOUS_MERGE and old["scope"]["source_sha256"] == PREVIOUS_SOURCE,
        "MINICPM_EXACT_V44_RELEASE_HISTORY")
    return old


def validate_repair(grant):
    r = grant["repair"]
    require(type(r) is dict and set(r) == {"schema", "directive", "previous_release", "previous_ticket",
        "journal_head_sha256", "closure_sha256", "reserved_after"} and r["schema"] == SCHEMA,
        "MINICPM_REPAIR_FIELDS")
    from .minicpm_recovery import locator
    locator(r["directive"]); locator(r["previous_release"])
    require(r["directive"]["comment_id"] == DIRECTIVE and r["reserved_after"] == RESERVED,
        "MINICPM_REPAIR_NO_REFUND_OR_NEW_CAMPAIGN")
    for name in ("journal_head_sha256", "closure_sha256"):
        require_hash(r[name])
    ticket = r["previous_ticket"]
    require(digest(ticket) == PREVIOUS_TICKET and ticket["payload"]["grant_sha256"] == PREVIOUS_GRANT
        and ticket["payload"]["value_sha256"] == PREVIOUS_VALUE
        and ticket["payload"]["reserved_after"] == RESERVED, "MINICPM_EXACT_V44_SIGNED_HOLD")
    a.verify_signature(grant["public_key"], ticket["payload"], ticket["signature"])


def authenticate_repair(grant, reader):
    r = grant["repair"]
    validate_repair(grant)
    owner_record(reader, r["directive"], 199)
    old = previous_release(reader, r["previous_release"])
    require(old["public_key"] == grant["public_key"] and old["caps"] == grant["caps"]
        and old["recovery"] == grant["recovery"], "MINICPM_REPAIR_AUTHORITY_OR_BUDGET_DRIFT")
    before, after = deepcopy(old["scope"]), deepcopy(grant["scope"])
    for scope in (before, after):
        scope.pop("source_sha256")
        scope["identity"].pop("implementation_sha256")
    require(before == after, "MINICPM_REPAIR_SCIENCE_OR_INPUT_DRIFT")


def verify_supervisor(value, ticket, archive, provider):
    """Bounded sealed proof: exact admit failure, reaped child, no native stage.

    Caller must additionally authenticate provider code/Inputs and the exhaustive
    remote inventory. A local archive alone does not establish remote custody.
    """
    require(digest(value) == PREVIOUS_VALUE and digest(ticket) == PREVIOUS_TICKET
        and value["job"] == JOB and value["request"]["source_sha256"] == PREVIOUS_SOURCE,
        "MINICPM_EXACT_V44_INCIDENT")
    require(provider["state"] in ("COMPLETE", "ERROR") and provider["job_id"] == JOB
        and provider["version"] == 1 and provider["notebook_code_sha256"] == ticket["payload"]["notebook_code_sha256"]
        and provider["safeshift_metadata"] == "MATCHED" and type(provider["kernel_id"]) is int,
        "MINICPM_V44_TERMINAL_PROVIDER")
    require(snapshot_stat(archive).st_size <= 64 * 2**20, "MINICPM_V44_ARCHIVE_BOUND")
    members = ui.pair(archive)
    expected = {"admit-process.json", "admit.log", "capability.json", "claims.json", "failure.json",
        "final_timing.json", "release.json", "request.json", "retention.json", "admit/failure.json"}
    require(set(members) == expected, "MINICPM_V44_EXACT_PRE_NATIVE_MEMBERS")
    with tempfile.TemporaryDirectory() as tmp:
        control = import_archive(archive, Path(tmp) / "supervisor")
        require(read(control / "request.json") == value["request"]
            and read(control / "capability.json")["ticket"] == ticket, "MINICPM_V44_REQUEST_TICKET")
        release = read(control / "release.json")
        failure = read(control / "failure.json")
        require(release["status"] == "BLOCKED" and release["last_stage"] == "admit"
            and release["attempt_observed"] is False and release["diagnostic"] is False
            and release["recovery"] == "NO_ATTEMPT" and release["scientific_qualified"] is False
            and release["source_sha256"] == PREVIOUS_SOURCE and release["failure"] == failure
            and failure["stage"] == "admit" and failure["category"] == "TECHNICAL"
            and failure["message"] == "SUPERVISED_CHILD_FAILURE", "MINICPM_V44_ADMIT_FAILURE_REQUIRED")
        process = read(control / "admit-process.json")
        require(process["schema"] == "fresh-process-supervision-v1" and process["status"] == "CHILD_FAILURE"
            and type(process["returncode"]) is int and process["returncode"] != 0
            and process["group_kill_sent"] is True and process["automatic_retry"] is False,
            "MINICPM_V44_REAPED_CHILD_REQUIRED")
        claims = read(control / "claims.json")
        require(set(claims) == {"launch.json", "admit.json"}, "MINICPM_V44_NO_NATIVE_OR_UNKNOWN_CLAIM")
        for name, claim in claims.items():
            require(set(claim) == {"kind", "number", "request_sha256", "ticket_sha256", "time_unix"}
                and claim["kind"] + ".json" == name and claim["number"] == 4
                and claim["request_sha256"] == digest(value["request"]) and claim["ticket_sha256"] == digest(ticket)
                and type(claim["time_unix"]) in (int, float) and math.isfinite(claim["time_unix"]),
                "MINICPM_V44_CLAIM_BINDING")
        launched = claims["launch.json"]["time_unix"]
        require(ticket["payload"]["issued_unix"] <= launched < ticket["payload"]["start_before_unix"]
            and launched <= claims["admit.json"]["time_unix"] < launched + value["request"]["plan"]["max_seconds"],
            "MINICPM_V44_CLAIM_WINDOW")
    return {"schema": SCHEMA, "disposition": "FAILED_PRE_NATIVE_NO_USABLE_RESULTS", "job": JOB, "version": 1,
        "provider": provider, "ticket_sha256": digest(ticket), "value_sha256": digest(value),
        "supervisor_sha256": sha(archive), "failure_sha256": digest(failure), "claims_sha256": digest(claims),
        "native_calls": 0, "native_evidence": "AUTHENTICATED_SUPERVISOR_ADMIT_FAILURE_AND_EXHAUSTIVE_PROVIDER_INVENTORY",
        "reserved_after": deepcopy(RESERVED), "refund": False, "history_import": False, "scientific_qualified": False}
