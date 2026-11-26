"""Exact Serial 7 supervisor-only failure and the next source authority."""
from copy import deepcopy
import math
from pathlib import Path
import zipfile

from safeshift.candidates.source import require, snapshot_stat
from safeshift.pilot.artifacts import read, safe, sha
from safeshift.pilot.contract import digest, require_hash
from . import contract, minicpm_release as a, minicpm_ui as ui

JOB = "nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-7"
SOURCE = "3bd387e15d62934a396c61af71d4519c0f71df73b4bdf806d17e3de8fb09a46e"
RELEASE = {"comment_id": 6999442629, "body_sha256": "b4df795e97140bbbc529b540da4a6ac8221834bcb594505bb6873e5650b8ade9"}
MERGE = "4e091746e97bf9489676724d50d9502e6a604a40"
GRANT_SHA = "d7f44c60efc7ca76ba3a2977a62f5ab9202f3643359a018c3710e1796f435742"
TICKET_SHA = "ff86f3644cc315823dd44e4fee6c2a618ff3dbb6fece96f472454b20304370a9"
VALUE_SHA = "5b7b45ff3ee9cbfc4366b77b338a569a2aa363df49a291f1f65fff1c9581a8b3"
REGISTRATION = "80226232db6070f42a16e25219fe7731b7b1d6129dc21c641f600f2078ce41a9"
EVENT_SHA = "28379c3e4589f84a114461c7ff707a2d8b27044783378aebdfc73f1b9de3eb9c"
ARCHIVE = "minicpm-fulltrain/supervision/f92e03d5da344a9bab1baf16a1643ced.zip"
ZIP_SHA = "e189abc6e6df39804c2bd2ddf3bdd52f8d8a1485845ea136ee58068abd6daf56"
INVENTORY = "89b0e625b20c403e11fe4dcde3d12fb767359436ce4d80561d388734d1fefc74"
RESERVED = {"calls": 10726, "jobs": 7, "gpu_seconds": 201600}
TRACE = "MINICPM_LIVE_GITHUB_UNAVAILABLE_OR_RATE_LIMITED_NO_OFFLINE_BYPASS"
SCHEMA = "safeshift-minicpm-serial7-pre-native-closure-v1"
PRIMARY = "minicpm-offline-s7"
MIRROR = "minicpm-offline-s7-mirror"
FENCE = "minicpm-release-registrations/mcpm4-restart-v1-offline-post-serial6.json"


def old_release(row):
    from .minicpm_offline import RELEASE as MARKER
    old = a.record(a.owner_comment(row, RELEASE, 205)["body"], MARKER)
    require(digest(old) == GRANT_SHA and old["implementation_pr"] == 205
        and old["merged_sha"] == MERGE and old["scope"]["source_sha256"] == SOURCE,
        "MINICPM_SERIAL7_EXACT_HISTORICAL_RELEASE")
    return old


def validate_transition(grant):
    row = grant["offline"]["serial7"]
    require(type(row) is dict and set(row) == {"event_sha256", "provider_closure_sha256"}
        and row["event_sha256"] == EVENT_SHA and grant["implementation_pr"] > 206
        and grant["scope"]["source_sha256"] != SOURCE,
        "MINICPM_SERIAL8_NEW_SOURCE_OR_SERIAL7_EVENT")
    require_hash(row["provider_closure_sha256"])


def authenticate_transition(grant, reader):
    old = old_release(reader("/issues/comments/" + str(RELEASE["comment_id"])))
    for key in ("campaign_id", "public_key", "caps", "sizing", "recovery", "repair", "operator_host_sha256"):
        require(old[key] == grant[key], "MINICPM_SERIAL8_PREVIOUS_AUTHORITY_OR_BUDGET_DRIFT")
    before, after = deepcopy(old["scope"]), deepcopy(grant["scope"])
    for scope in (before, after):
        scope.pop("source_sha256")
        scope["identity"].pop("implementation_sha256")
    require(before == after, "MINICPM_SERIAL8_SCIENCE_OR_INPUT_DRIFT")


def inventory(root):
    pending, names, seen = [root], [], 0
    while pending:
        directory = pending.pop()
        snapshot_stat(directory, directory=True)
        for path in directory.iterdir():
            seen += 1
            require(seen <= 1024, "MINICPM_SERIAL7_INVENTORY_BOUND")
            if path.is_dir():
                pending.append(path)
            else:
                snapshot_stat(path)
                names.append(path.relative_to(root).as_posix())
    require(digest(sorted(names)) == INVENTORY, "MINICPM_SERIAL7_OUTPUT_INVENTORY_CHANGED")
    return set(names)


def verify_supervisor(download, value, ticket):
    names = inventory(download)
    require({n for n in names if n.lower().endswith((".zip", ".zip.sha256.json"))}
        == {ARCHIVE, ARCHIVE + ".sha256.json"}, "MINICPM_SERIAL7_SUPERVISOR_ONLY")
    archive = safe(download, ARCHIVE)
    require(snapshot_stat(archive).st_size <= 64 * 2**20, "MINICPM_SERIAL7_ARCHIVE_BOUND")
    require(len(ui.pair(archive, ZIP_SHA)) == 59, "MINICPM_SERIAL7_ARCHIVE_MEMBERS")
    out = archive.with_suffix("")
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            path = safe(out, entry.filename)
            require(snapshot_stat(path).st_size == entry.file_size and path.read_bytes() == bundle.read(entry),
                "MINICPM_SERIAL7_EXTRACTED_RECEIPT_DRIFT")

    request = value["request"]
    require(read(out / "request.json") == request
        and read(out / "capability.json") == {"locator": RELEASE, "ticket": ticket},
        "MINICPM_SERIAL7_REQUEST_TICKET")
    release, failure = read(out / "release.json"), read(out / "failure.json")
    require(release["status"] == "BLOCKED" and release["last_stage"] == "cpu"
        and release["attempt_observed"] is False and release["diagnostic"] is False
        and release["automatic_retry"] is False and release["recovery"] == "NO_ATTEMPT"
        and release["source_sha256"] == SOURCE and release["failure"] == failure
        and failure["stage"] == "cpu" and failure["category"] == "TECHNICAL"
        and failure["message"] == "SUPERVISED_CHILD_FAILURE"
        and (out / "cpu.log").read_text(encoding="utf-8").rstrip().endswith("PermissionError: " + TRACE)
        and not (out / "cpu").exists(), "MINICPM_SERIAL7_CPU_AUTHORITY_FAILURE")
    for mode in ("admit", "setup", "reclaim", "cpu"):
        process = read(out / (mode + "-process.json"))
        require(process["schema"] == "fresh-process-supervision-v1" and process["group_kill_sent"] is True
            and process["group_exit"] == {"status": "NO_LIVE_MEMBERS", "members": []}
            and process["automatic_retry"] is False and type(process["returncode"]) is int
            and (process["status"], process["returncode"]) == (("CHILD_FAILURE", 1) if mode == "cpu" else ("EXITED", 0)),
            "MINICPM_SERIAL7_REAPED_STAGE")
        if mode != "cpu":
            require(read(out / mode / "stage.json") == {"status": "RETURNED", "stage": mode,
                "request_sha256": digest(request), "source_sha256": SOURCE, "native_attempt_permitted": False},
                "MINICPM_SERIAL7_STAGE_BINDING")
    claims = read(out / "claims.json")
    stages = ("launch", "admit", "setup", "reclaim")
    require(set(claims) == {kind + ".json" for kind in stages}, "MINICPM_SERIAL7_NO_NATIVE_OR_UNKNOWN_CLAIM")
    times = []
    for kind in stages:
        name = kind + ".json"
        row = claims[name]
        loose = safe(download, "minicpm-fulltrain-claims/mcpm4-restart-v1/7/" + name)
        require(read(loose) == row and set(row) == {"kind", "number", "request_sha256", "ticket_sha256", "time_unix"}
            and row["kind"] == kind and row["number"] == 7 and row["ticket_sha256"] == TICKET_SHA
            and row["request_sha256"] == digest(request) and type(row["time_unix"]) in (int, float)
            and math.isfinite(row["time_unix"]), "MINICPM_SERIAL7_CLAIM_BINDING")
        times.append(row["time_unix"])
    t = ticket["payload"]
    require(times == sorted(times) and t["issued_unix"] <= times[0] < t["start_before_unix"]
        and times[-1] < times[0] + request["plan"]["max_seconds"], "MINICPM_SERIAL7_CLAIM_WINDOW")
    retention = read(out / "retention.json")
    advice = read(out / "reclaim/owned-advice.json")
    available = read(out / "reclaim/post-advice-resources.json")["memory"]["available_bytes"]
    floor = request["resource_policy"]["free_ram_mib"] * 2**20
    require(retention["retained"] == [] and retention["raw_deleted"] is False
        and advice["scan_complete"] is True and advice["deleted_files"] == 0
        and available == 25758027776 and floor == 16 * 2**30,
        "MINICPM_SERIAL7_RETENTION_OR_RAM")
    return {"schema": SCHEMA, "disposition": "FAILED_PRE_NATIVE_NO_USABLE_RESULTS",
        "job": JOB, "version": 1, "source_sha256": SOURCE, "ticket_sha256": TICKET_SHA,
        "event_sha256": EVENT_SHA, "supervisor_sha256": ZIP_SHA, "claims_sha256": digest(claims),
        "supervisor_sidecar_sha256": sha(str(archive) + ".sha256.json"), "failure": TRACE,
        "available_bytes": available, "required_available_bytes": floor, "native_loads": 0,
        "native_calls": 0, "counts": {"NOT_ATTEMPTED": 3763}, "reserved_after": dict(RESERVED),
        "refund": False, "history_import": False, "provider_verification": "LOCAL_DOWNLOAD_ONLY"}


def verify_local(processed):
    """Verify original mirrors, fence, signed ticket, notebook and local output."""
    from safeshift.internvl3763_operator import code_hash
    from .minicpm_execution import MARKER
    from .minicpm_serial6 import RESERVED as PREVIOUS_HOLD

    primary, mirror = (safe(processed, name) for name in (PRIMARY, MIRROR))
    files = []
    for root in (primary, mirror):
        event, registration = safe(root, "event-000001.json"), safe(root, "registration.json")
        require(list(root.glob("event-*.json")) == [event] and sha(event) == EVENT_SHA
            and sha(registration) == REGISTRATION, "MINICPM_SERIAL7_EXACT_MIRRORED_PREFIX")
        files.extend((event, registration))
    fence = safe(processed, FENCE)
    require(read(fence) == {"root": "data/processed/" + PRIMARY, "registration_sha256": REGISTRATION},
        "MINICPM_SERIAL7_FENCE")
    files.append(fence)
    reg = read(primary / "registration.json")
    row = read(primary / "event-000001.json")
    active = row["payload"]
    value, ticket = active["value"], active["ticket"]
    t = ticket["payload"]
    old = old_release(reg["exports"]["/issues/comments/" + str(RELEASE["comment_id"])])
    require(row["kind"] == "RESERVED_OFFLINE" and row["previous"] == t["previous_event_sha256"] == REGISTRATION
        and reg["locator"] == RELEASE and t["grant_sha256"] == digest(old)
        and digest(ticket) == TICKET_SHA and digest(value) == t["value_sha256"] == t["capsule_sha256"] == VALUE_SHA
        and t["number"] == 7 and t["reserved_before"] == PREVIOUS_HOLD and t["reserved_after"] == RESERVED
        and value["job"] == JOB and value["request"]["source_sha256"] == SOURCE
        and value["request"]["history"] == value["ancestors"] == []
        and value["request"]["plan"]["counts"] == {"NOT_ATTEMPTED": 3763},
        "MINICPM_SERIAL7_SIGNED_RESERVATION_SCOPE")
    a.verify_signature(old["public_key"], t, ticket["signature"])
    for root in (primary, mirror):
        gate = safe(root, active["gate_proof"])
        require(sha(gate) == t["owner_gate"]["proof_sha256"], "MINICPM_SERIAL7_GATE_PROOF")
        package = safe(root, active["package"])
        nb = safe(package, "notebook.ipynb")
        require(read(nb) == active["notebook"] and code_hash(read(nb)) == t["notebook_code_sha256"],
            "MINICPM_SERIAL7_NOTEBOOK_CUSTODY")
        spec, envelope = safe(package, "dataset/" + ui.MARKER), safe(package, "dataset/" + MARKER)
        require(sha(spec) == VALUE_SHA and sha(envelope) == TICKET_SHA, "MINICPM_SERIAL7_CAPSULE_CUSTODY")
        files.extend((gate, nb, spec, envelope, safe(package, "owner-steps.json")))
    download = safe(processed, "inspect_run_7")
    snapshot = safe(download, "data/processed/fresh_fulltrain_code/" + SOURCE)
    require(digest(contract.source_manifest(snapshot)) == SOURCE, "MINICPM_SERIAL7_RUNTIME_SOURCE_BYTES")
    context = safe(download, "mcpm4-restart-v1-7-release-context.json")
    require(read(context) == {"locator": RELEASE, "value": value, "ticket": ticket}, "MINICPM_SERIAL7_CONTEXT_BINDING")
    report = verify_supervisor(download, value, ticket)
    files.extend(safe(download, name) for name in sorted(inventory(download)))
    return report, active, files


def verify_closure(report, local, active):
    """Replay the exact provider evidence that a fresh Owner release must pin."""
    require(type(report) is dict and set(report) == {"local", "provider", "capsule", "output"},
        "MINICPM_SERIAL7_PROVIDER_CLOSURE_REQUIRED")
    provider, capsule, output = report["provider"], report["capsule"], report["output"]
    value, ticket = active["value"], active["ticket"]
    require(report["local"] == local and provider["job_id"] == JOB and type(provider["version"]) is int
        and provider["version"] == 1 and provider["state"] in ("COMPLETE", "ERROR")
        and type(provider["kernel_id"]) is int and provider["kernel_id"] > 0
        and provider["notebook_code_sha256"] == ticket["payload"]["notebook_code_sha256"]
        and provider["safeshift_metadata"] == "MATCHED", "MINICPM_SERIAL7_PROVIDER_JOB_OR_NOTEBOOK")
    from .minicpm_execution import MARKER
    require(capsule["private"] is True and capsule["version"] == 1
        and capsule["files"] == {ui.MARKER: digest(value), MARKER: digest(ticket)}
        and output["pairs"] == {ARCHIVE: ZIP_SHA}
        and output["sidecar_sha256"] == local["supervisor_sidecar_sha256"],
        "MINICPM_SERIAL7_PROVIDER_CAPSULE_OR_SUPERVISOR")
    names = output["inventory"]
    require(type(names) is list and len(names) <= 1024 and names == sorted(set(names))
        and {name for name in names if name.lower().endswith((".zip", ".zip.sha256.json"))}
            == {ARCHIVE, ARCHIVE + ".sha256.json"}, "MINICPM_SERIAL7_PROVIDER_INVENTORY")
    require_hash(output["log_sha256"])
