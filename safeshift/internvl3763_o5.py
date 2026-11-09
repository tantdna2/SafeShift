"""Exact Owner O5 amendment. Public pinned authority, never a replacement grant.

Offline inspection validates the pinned snapshot; mutations and execution also
authenticate GitHub anew. No provider, submission, refund or migration code.
"""
from copy import deepcopy
from safeshift.candidates.source import require
from safeshift.pilot.contract import digest

MARKER = "SAFESHIFT_TRAIN3763_O5_AMENDMENT_V1"
COMMENT_ID = 6733033003
BODY_SHA256 = "e6953ebda47d83b86db0f5035244947c3a1786baa714ad615c399f3181704b9c"
DECISION_SHA256 = "a1e24efcbf2b4531177bb2a846b6a7def99f6b9a3efc3fb17c36ffe54ace9f6d"
ORIGINAL_COMMENT_ID = 6658142293
ORIGINAL_SHA256 = "1f672fb601006c7898be271e59f74fb341d7311fc60794a9ed6a332f430395c6"
SCIENCE_SHA256 = "ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50"
LOCATOR = {"comment_id": COMMENT_ID, "body_sha256": BODY_SHA256}
KIND = "O5_EXTENSION"


def authority(grant, *, reader=None, snapshot=None):
    from safeshift import internvl3763_campaign as c, internvl3763_release as old
    if snapshot is not None:
        reader = lambda path: snapshot
    value, comment = c.record(LOCATOR, MARKER, old.get if reader is None else reader)
    require(comment["user"]["login"] == old.OWNER
        and type(comment["user"]["id"]) is int and comment["user"]["id"] == 246929698
        and comment["author_association"] == "OWNER"
        and comment["issue_url"] == old.API + "/issues/180", "AUTHENTIC_OWNER_O5")
    require(digest(value) == DECISION_SHA256, "EXACT_O5_DECISION")
    require(digest(grant) == ORIGINAL_SHA256 == value["original_campaign_sha256"]
        and grant["campaign_id"] == value["campaign_id"]
        and grant["science_sha256"] == SCIENCE_SHA256 == value["science_sha256"], "O5_ORIGINAL_GRANT_SCIENCE")
    require(all(type(grant["caps"].get(k)) is int and grant["caps"][k] == v
        for k, v in value["limits_before"].items()), "O5_ORIGINAL_CAPS")
    # Store only public fields needed for later offline verification.
    evidence = {k: deepcopy(comment[k]) for k in ("id", "body", "user", "issue_url", "author_association")}
    evidence["user"] = {k: comment["user"][k] for k in ("login", "id")}
    return value, evidence


def validate_extension(event, grant, prefix, registration_sha256=None):
    require(set(event) == {"campaign_sha256", "previous", "kind", "unix", "authority", "original_locator",
        "registration_sha256", "historical_events"} and event["kind"] == KIND, "O5_EVENT_FIELDS")
    value, _ = authority(grant, snapshot=event["authority"])
    require(type(event["historical_events"]) is int and event["historical_events"] == len(prefix) == 24
        and event["previous"] == digest(prefix[-1])
        and event["campaign_sha256"] == digest(grant), "O5_EXACT_HISTORICAL_PREFIX")
    require(event["original_locator"]["comment_id"] == ORIGINAL_COMMENT_ID, "O5_ORIGINAL_LOCATOR")
    from safeshift.pilot.contract import require_hash
    require_hash(event["original_locator"]["body_sha256"])
    require_hash(event["registration_sha256"])
    if registration_sha256 is not None:
        require(event["registration_sha256"] == registration_sha256, "O5_REGISTRATION_DRIFT")
    intents = [e for e in prefix if e["kind"] == "INTENT"]
    require(all(e["request"]["execution_release"] == event["original_locator"] for e in intents),
        "O5_HISTORICAL_GRANT_LOCATOR_DRIFT")
    require(len(intents) == value["historical_jobs_at_decision"] == 7
        and sum(e["reserved_calls"] for e in intents) == value["historical_calls_at_decision"] == 7
        and sum(e["reserved_gpu_seconds"] for e in intents) == value["historical_reserved_gpu_seconds_at_decision"] == 25200,
        "O5_HISTORICAL_ACCOUNTING")
    closed = {e["intent_sha256"] for e in prefix if e["kind"] in ("COLLECTED", "ABORTED_PRE_SUBMIT")}
    require(all(digest(e) in closed for e in intents), "O5_OPEN_OR_UNKNOWN_HISTORY")
    latest = {}
    for e in prefix:
        if e["kind"] == "COLLECTED":
            for row in e["history"]["records"]:
                if row["status"] != "NOT_ATTEMPTED":
                    latest[row["ordinal"]] = row["status"]
    require(latest == {0: "SUCCESS", 1: "SUCCESS"}, "O5_ORDINAL0_1_SUCCESS_REQUIRED")
    caps = deepcopy(grant["caps"])
    caps["total_gpu_seconds"] = value["limits_after"]["total_gpu_seconds"]
    return caps


def execution(grant, request, reviewed, *, reader=None):
    """One source-bound ChatGPT release for serial resume, never per-job approval."""
    from safeshift import internvl3763_campaign as c, internvl3763_release as old
    runtime = request["bindings"]["runtime"]
    event = runtime.get("o5_extension")
    require(type(event) is dict, "O5_EXTENSION_REQUIRED")
    _, evidence = authority(grant, reader=reader)
    require(event["authority"] == evidence and event["historical_events"] == 24,
        "O5_REQUEST_AUTHORITY_DRIFT")
    require(c.load(event["original_locator"], reader=reader) == grant, "O5_AUTHENTIC_ORIGINAL_GRANT")
    require(event["campaign_sha256"] == digest(grant) and event["kind"] == KIND,
        "O5_REQUEST_EXTENSION_BINDING")
    # The pinned resource decision itself explicitly cannot release execution.
    release, comment = c.record(runtime.get("o5_execution_release"),
        "SAFESHIFT_TRAIN3763_O5_EXECUTION_V1", old.get if reader is None else reader)
    require(comment["user"]["login"] in grant["review_logins"]
        and comment["issue_url"] == old.API + "/issues/" + str(reviewed["implementation_pr"]), "O5_EXECUTION_REVIEWER")
    expected = {"campaign_sha256": digest(grant), "extension_sha256": digest(event),
        "science_sha256": grant["science_sha256"], "implementation_pr": reviewed["implementation_pr"],
        "reviewed_head": reviewed["reviewed_head"], "merged_sha": reviewed["merged_sha"],
        "source_sha256": reviewed["source_sha256"], "notebook_sha256": reviewed["notebook_sha256"],
        "status": "RELEASED_FOR_SERIAL_RESUME", "start_ordinal": 2, "test": False}
    require(digest(release) == digest(expected), "O5_SEPARATE_EXECUTION_RELEASE")
    require(request["plan"]["action"] == "resume" and request["plan"]["scheduled_ordinals"]
        and min(request["plan"]["scheduled_ordinals"]) >= 2, "O5_RESUME_FROM_ORDINAL2_ONLY")
    return event
