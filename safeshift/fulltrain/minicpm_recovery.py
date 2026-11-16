"""Owner-authorized restart: immutable retired attempts, finite scheduler policy.

Retirement is a project/result decision, never authenticated provider deletion or
measured zero calls. Real quota and new-run custody remain independent gates.
"""
from copy import deepcopy
import hashlib
import json
import time

from safeshift.candidates.source import require
from safeshift.pilot.contract import digest, require_hash
from . import minicpm_release as a, minicpm_ui as ui

SCHEMA = "safeshift-minicpm-owner-restart-snapshot-v4"
CAMPAIGNS = ("mcpm4-train3763", "mcpm4-train3763-v2", "mcpm4-train3763-v3")
CAMPAIGN = "mcpm4-train3763-owner-restart-v1"
SERIES = "fresh171-minicpm4-owner-restart-v1"
DIRECTIVE = 6918902424
EVENT_PREFIX = "SAFESHIFT_MINICPM_LIVE_V3 "
HISTORICAL = {"calls": 3000, "jobs": 3, "gpu_seconds": 86400}
JOB_SECONDS = 14400
COUNT = 3763
SOURCE_ROLES = ("source_review", "independent_audit", "merge", "postmerge")


def budget_policy(historical):
    """Finite reservation envelope, not claimed Kaggle usage or throughput.

    At most COUNT new serial jobs, each scheduling at most COUNT pending IDs.
    Holds for aborted/short jobs without refunding unused call reservations.
    Actual image calls remain <=COUNT via unchanged NOT_ATTEMPTED histories.
    Job time reuses the existing approved four-hour envelope. Each new job also
    needs its own fresh account quota; a project ceiling is never weekly quota.
    """
    require(historical == HISTORICAL, "MINICPM_EXACT_RETIRED_RESERVATIONS")
    return {"schema": "safeshift-minicpm-finite-owner-ui-budget-v1", "directive_id": DIRECTIVE,
        "basis": "COUNT_SERIAL_JOBS_TIMES_FINITE_JOB_CAPS_NO_REFUND", "original_ids": COUNT,
        "maximum_new_jobs": COUNT, "maximum_actual_native_calls": COUNT,
        "caps": {"total_calls": historical["calls"] + COUNT * COUNT,
            "total_jobs": historical["jobs"] + COUNT,
            "total_gpu_seconds": historical["gpu_seconds"] + COUNT * 2 * JOB_SECONDS,
            "job_calls": COUNT, "job_seconds": JOB_SECONDS, "physical_gpus": 2,
            "loads_per_job": 1, "archive_bytes": 7 * 2**30},
        "usage": "RESERVATIONS_NOT_BILLING_OR_WEEKLY_QUOTA", "refund": False,
        "numeric_provenance": "DERIVED_BY_REVIEWED_IMPLEMENTATION_NOT_NUMBERS_QUOTED_FROM_OWNER"}


def locator(value):
    require(type(value) is dict and set(value) == {"comment_id", "body_sha256"}
        and type(value["comment_id"]) is int and value["comment_id"] > 0, "MINICPM_RESTART_LOCATOR")
    require_hash(value["body_sha256"])


def validate_recovery(grant):
    r = grant["recovery"]
    require(type(r) is dict and set(r) == {"schema", "journals", "reserved", "directive", "budget_policy"}
        and r["schema"] == SCHEMA, "MINICPM_OWNER_RESTART_SNAPSHOT")
    require(grant["campaign_id"] == CAMPAIGN and grant["scope"]["campaign"]["series"]["minicpm4"] == SERIES,
            "MINICPM_EXACT_NEW_EXECUTION_SERIES")
    locator(r["directive"])
    require(r["directive"]["comment_id"] == DIRECTIVE, "MINICPM_EXACT_OWNER_RESET_DIRECTIVE")
    require(type(r["journals"]) is list and len(r["journals"]) == 3, "MINICPM_ALL_RETIRED_JOURNALS_REQUIRED")
    totals = {"calls": 0, "jobs": 0, "gpu_seconds": 0}
    seen, paths = set(), set()
    for campaign, row in zip(CAMPAIGNS, r["journals"]):
        require(type(row) is dict and set(row) == {"campaign_id", "root", "mirror", "head_sha256", "grant_locator",
            "ticket", "job", "publication", "disposition", "evidence_sha256", "evidence", "historical_status",
            "native_calls_evidence"} and row["campaign_id"] == campaign, "MINICPM_RETIRED_LINEAGE_FIELDS")
        require(row["job"] == "nguynanhtn/safeshift-minicpm-" + campaign + "-1"
            and row["publication"] in ("RESERVED", "PUBLISH_INTENT", "PUBLISHED")
            and row["disposition"] == "RETIRED_NO_USABLE_RESULTS"
            and row["historical_status"] == "PROVIDER_UNAVAILABLE_NOT_VERIFIED_DELETED"
            and row["native_calls_evidence"] == "OWNER_REPORTED_LOCAL_LOGS_NOT_PROVIDER_VERIFIED",
                "MINICPM_NO_FABRICATED_PROVIDER_RETIREMENT")
        from safeshift.pilot.artifacts import relative
        for field in ("root", "mirror"):
            relative(row[field])
            require(row[field].startswith("data/processed/") and row[field] not in paths, "MINICPM_DISTINCT_RETIRED_PATHS")
            paths.add(row[field])
        locator(row["grant_locator"])
        require_hash(row["head_sha256"])
        require(type(row["evidence"]) is list and 1 <= len(row["evidence"]) <= 16
            and row["evidence_sha256"] == digest(row["evidence"]), "MINICPM_RETIRED_LOCAL_EVIDENCE")
        for proof in row["evidence"]:
            require(set(proof) == {"path", "sha256", "kind"} and proof["kind"] in
                ("LOCAL_LOG", "LOCAL_SEALED_SUPERVISOR", "LOCAL_SIDECAR", "LOCAL_TICKET"), "MINICPM_LOCAL_EVIDENCE_KIND")
            relative(proof["path"])
            require(proof["path"].startswith("data/processed/"), "MINICPM_LOCAL_EVIDENCE_PATH")
            require_hash(proof["sha256"])
        ticket = row["ticket"]
        require(type(ticket) is dict and set(ticket) == {"payload", "signature"}, "MINICPM_RETIRED_SIGNED_TICKET")
        a.verify_signature(grant["public_key"], ticket["payload"], ticket["signature"])
        t = ticket["payload"]
        require(t["schema"] == a.TICKET and t["number"] == 1 and digest(ticket) not in seen
            and t["reserved_before"] == {"calls": 0, "jobs": 0, "gpu_seconds": 0}
            and t["sizing"]["calls"] == 1000 and t["sizing"]["seconds"] == JOB_SECONDS
            and t["reserved_after"] == {"calls": 1000, "jobs": 1, "gpu_seconds": 2 * JOB_SECONDS},
                "MINICPM_RETIRED_BUDGET_OR_REPLAY")
        seen.add(digest(ticket))
        for k in totals:
            totals[k] += t["reserved_after"][k]
    require(r["reserved"] == totals == HISTORICAL and r["budget_policy"] == budget_policy(totals)
        and grant["caps"] == r["budget_policy"]["caps"], "MINICPM_DERIVED_BUDGET_NO_RESET_OR_UNBOUNDED_CAP")
    for name in ("master_dataset", "train_dataset"):
        row = grant["scope"]["original_inputs"][name]
        require(row["mount"] == "datasets/" + row["ref"], "MINICPM_RESTART_NESTED_BINDING")
    return r


def authenticate_recovery(grant, reader, *, rights=True):
    """One new Owner decision and fresh source approvals, no budget-comment loop."""
    r = validate_recovery(grant)
    def fetch(loc, issue):
        locator(loc)
        row = reader("/issues/comments/" + str(loc["comment_id"]))
        require(row["id"] == loc["comment_id"] and row["user"]["login"] == a.OWNER
            and row["user"]["id"] == a.OWNER_ID and row["issue_url"] == a.API + "/issues/" + str(issue)
            and hashlib.sha256(row["body"].encode()).hexdigest() == loc["body_sha256"], "MINICPM_AUTHENTIC_RESTART_RECORD")
        return row
    fetch(r["directive"], 199)
    old = None
    for row in r["journals"]:
        old = a.record(fetch(row["grant_locator"], 198)["body"], a.MARKER)
        require(old["schema"] == a.SCHEMA and old["authorization"] == "OWNER_MINICPM_TRAIN3763_SERIAL_UI_ONLY"
            and old["campaign_id"] == row["campaign_id"] and old["public_key"] == grant["public_key"]
            and old["merged_sha"] == "507e9817b91054fa7af324c6a915c35d56b5acf1"
            and old["scope"]["source_sha256"] == "7c76a2c331aef2383e9d8f2fe236f0c4302cabb587a759925b5d3dadae206b5c"
            and digest(old) == row["ticket"]["payload"]["grant_sha256"], "MINICPM_ORIGINAL_AUTHENTIC_GRANT")
        previous, current = deepcopy(old["scope"]), deepcopy(grant["scope"])
        for s in (previous, current):
            s.pop("source_sha256")
            s["identity"].pop("implementation_sha256")
            s["campaign"]["series"]["minicpm4"] = "OWNER_RESTART_ONLY_SERIES_PROVENANCE_CHANGE"
            for name in ("master_dataset", "train_dataset"):
                s["original_inputs"][name].pop("mount")
        require(previous == current, "MINICPM_OWNER_RESTART_SCIENCE_DRIFT")
    if rights:
        for role in ("O2", "O3", "O4", "O5", "O6"):
            proof = fetch(old["approvals"][role], 198)
            require(a.record(proof["body"], a.APPROVAL) == {"kind": role, "status": "APPROVED",
                "reviewed_head": old["reviewed_head"], "subject_sha256": a.subject(old)}, "MINICPM_ORIGINAL_RIGHTS_SCOPE")


def mounted_inputs(value):
    """Exact five nested mount roots, not recursive discovery or path guessing."""
    ui.validate(value)
    table = {}
    for kind, refs in value["input_sources"].items():
        for ref in refs:
            owner, slug, version = ref.split("/")
            table[ref] = {"mount": ("notebooks/" if kind == "kernel_sources" else "datasets/") + owner + "/" + slug,
                          "version": int(version)}
    for name in ("master_dataset", "train_dataset"):
        row = value["request"]["original_inputs"][name]
        require(row["mount"] == table[row["ref"] + "/" + str(row["version"])]["mount"],
                "MINICPM_RECOVERY_NESTED_BINDING_REQUIRED")
    require(len(table) == 5, "MINICPM_RECOVERY_FIVE_INPUTS")
    return table


def event_record(kind, **details):
    c = a.current()
    if c is None:
        return
    return {"kind": kind, "ticket_sha256": digest(c["ticket"]),
        "request_sha256": digest(c["value"]["request"]), "source_sha256": c["value"]["request"]["source_sha256"],
        "time_unix": time.time(), **details}


def emit(kind, **details):
    record = event_record(kind, **details)
    if record is None:
        return
    print(EVENT_PREFIX + json.dumps(record, sort_keys=True, separators=(",", ":")), flush=True)
    return record


def native_started(ordinal, sample_id, image_sha256):
    """Called at the actual model.generate boundary after image prep/model load."""
    c = a.current()
    require(c is not None and c["phase"] == "native", "MINICPM_NATIVE_OBSERVATION_CAPABILITY")
    from safeshift.pilot.artifacts import read, write
    claim = read(c["claims"] / f"call-{ordinal:06d}.json")
    require(claim["ticket_sha256"] == digest(c["ticket"]), "MINICPM_NATIVE_OBSERVATION_CLAIM")
    row = c["value"]["cohort"]["samples"][ordinal]
    require(row["sample_id"] == sample_id and row["image_sha256"] == image_sha256,
            "MINICPM_NATIVE_OBSERVATION_TRAIN_ID_SHA")
    receipt = event_record("native_generate_started", ordinal=ordinal, sample_id=sample_id,
        image_sha256=image_sha256, claim=claim, model_loaded=True)
    write(c["claims"] / f"generate-{ordinal:06d}.json", {"kind": f"generate-{ordinal:06d}",
        "ticket_sha256": digest(c["ticket"]), "request_sha256": digest(c["value"]["request"]),
        "number": c["ticket"]["payload"]["number"], "time_unix": receipt["time_unix"], "observation": receipt})
    a.sync_directory(c["claims"])
    print(EVENT_PREFIX + json.dumps(receipt, sort_keys=True, separators=(",", ":")), flush=True)
    return receipt
