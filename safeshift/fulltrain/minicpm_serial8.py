"""Verify the exact Serial 8 GPU-stage incident and bind its successor."""
from copy import deepcopy
import zipfile

from safeshift.candidates.source import require, snapshot_stat
from safeshift.pilot.artifacts import read, safe, sha
from safeshift.pilot.contract import digest, require_hash
from . import contract, minicpm_release as a, minicpm_serial7 as serial7, minicpm_ui as ui

PRIMARY = "minicpm-offline-s8"
MIRROR = PRIMARY + "-mirror"
DOWNLOAD = "inspect_run_8"
FENCE = "minicpm-release-registrations/mcpm4-restart-v1-offline-post-serial7.json"
TICKET_JOB = "nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-8"
ACTUAL_JOB = "nguynanhtn/notebook1358a4d09b"
SOURCE = "5f15f4302ff21d84dab5ea087f89ad1bf38c2e113d25de9d5720e00d7eef8350"
RELEASE = {"comment_id": 7008062352, "body_sha256": "1541895fe655b6d8b64a05f80258cc370311789389913a6e7e9324550f26de0f"}
MERGE = "6f7d2f07938b20fbcebc764bc4b27f1ebfb69a6a"
GRANT_SHA = "5a17908620233986dd930db3656658409449da38dd5ad3052147d9993a0b7bd7"
REGISTRATION_SHA = "9af7ded3523fb474c9e7c4fb48b21bdcf43977ad3fcb8e4cf0d92bd9ef75fd44"
EVENT_SHA = "9abcdf610a5a6cadcefc77feb128d84a8d93b045e1b8a97b2940f6df97ee1ce8"
TICKET_SHA = "0e72e99e9f68e2ca19128b248d90093709affb4e0ab1a1365e89abadac8475ee"
ARCHIVE = "minicpm-fulltrain/supervision/df59162055cd4d97be4991f84d2b8c82.zip"
ZIP_SHA = "3b5f95188943d5af6dc4abf9b6c9431586503c77075b0fe3c311d2360d563ec8"
INVENTORY_SHA = "6947fe7b47879b125171c2ec9812e7f468f82b51f11bf610298e35b7164d41cd"
RESERVED = {"calls": 10826, "jobs": 8, "gpu_seconds": 230400}
STAGES = ("admit", "setup", "reclaim", "cpu", "gpu")


def old_release(row):
    from .minicpm_offline import TRANSITION_RELEASE
    old = a.record(a.owner_comment(row, RELEASE, 207)["body"], TRANSITION_RELEASE)
    require(digest(old) == GRANT_SHA and old["merged_sha"] == MERGE,
            "MINICPM_SERIAL8_EXACT_HISTORICAL_RELEASE")
    return old


def validate_transition(grant):
    row = grant["offline"]["serial8"]
    require(type(row) is dict and set(row) == {"event_sha256", "provider_closure_sha256"}
        and row["event_sha256"] == EVENT_SHA and grant["implementation_pr"] > 207
        and grant["merged_sha"] != MERGE and grant["scope"]["source_sha256"] != SOURCE,
        "MINICPM_SERIAL9_NEW_SOURCE_OR_SERIAL8_EVENT")
    require_hash(row["provider_closure_sha256"])


def authenticate_transition(grant, reader):
    old = old_release(reader("/issues/comments/" + str(RELEASE["comment_id"])))
    for key in ("campaign_id", "public_key", "caps", "sizing", "recovery", "repair",
                "operator_host_sha256", "provider_max_age_seconds"):
        require(old[key] == grant[key], "MINICPM_SERIAL9_PREVIOUS_AUTHORITY_OR_BUDGET_DRIFT")
    require(old["offline"]["serial7"] == grant["offline"]["serial7"], "MINICPM_SERIAL9_SERIAL7_CLOSURE_DRIFT")
    before, after = deepcopy(old["scope"]), deepcopy(grant["scope"])
    for scope in (before, after):
        scope.pop("source_sha256")
        scope["identity"].pop("implementation_sha256")
    require(before == after, "MINICPM_SERIAL9_SCIENCE_OR_INPUT_DRIFT")


def inventory(download):
    pending, names, count = [download], set(), 0
    while pending:
        directory = pending.pop()
        snapshot_stat(directory, directory=True)
        for path in directory.iterdir():
            count += 1
            require(count <= 1024, "MINICPM_SERIAL8_INVENTORY_BOUND")
            if path.is_dir():
                pending.append(path)
            else:
                snapshot_stat(path)
                names.add(path.relative_to(download).as_posix())
    require({name for name in names if name.lower().endswith((".zip", ".zip.sha256.json"))}
        == {ARCHIVE, ARCHIVE + ".sha256.json"}, "MINICPM_SERIAL8_SUPERVISOR_ONLY")
    require(digest(sorted(names)) == INVENTORY_SHA, "MINICPM_SERIAL8_LOCAL_INVENTORY_DRIFT")
    return names


def verify_supervisor(download, value, ticket):
    archive = safe(download, ARCHIVE)
    require(snapshot_stat(archive).st_size <= 64 * 2**20, "MINICPM_SERIAL8_ARCHIVE_BOUND")
    ui.pair(archive, ZIP_SHA)
    extracted = archive.with_suffix("")
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            loose = safe(extracted, entry.filename)
            require(snapshot_stat(loose).st_size == entry.file_size and loose.read_bytes() == bundle.read(entry),
                "MINICPM_SERIAL8_EXTRACTED_RECEIPT_DRIFT")

    request = value["request"]
    require(read(extracted / "request.json") == request
        and read(extracted / "capability.json") == {"locator": RELEASE, "ticket": ticket},
        "MINICPM_SERIAL8_REQUEST_TICKET")
    release = read(extracted / "release.json")
    failure = read(extracted / "gpu/failure.json")
    require(release["status"] == "BLOCKED" and release["last_stage"] == "gpu"
        and release["attempt_observed"] is False and release["automatic_retry"] is False
        and release["diagnostic"] is False and release["recovery"] == "NO_ATTEMPT"
        and release["source_sha256"] == SOURCE
        and release["failure"] == read(extracted / "failure.json")
        and release["failure"]["stage"] == "gpu" and release["failure"]["message"] == "SUPERVISED_CHILD_FAILURE"
        and failure["stage"] == "gpu" and failure["type"] == "CalledProcessError"
        and failure["message"].startswith("Command '['nvidia-smi', ")
        and failure["message"].endswith("returned non-zero exit status 12.")
        and not (extracted / "gpu/stage.json").exists(), "MINICPM_SERIAL8_GPU_STAGE_FAILURE")
    request_sha = digest(request)
    for stage in STAGES:
        process = read(extracted / (stage + "-process.json"))
        require(process["group_exit"] == {"status": "NO_LIVE_MEMBERS", "members": []}
            and process["automatic_retry"] is False
            and (process["status"], process["returncode"]) == (("CHILD_FAILURE", 1) if stage == "gpu" else ("EXITED", 0)),
            "MINICPM_SERIAL8_REAPED_STAGE")
        if stage != "gpu":
            require(read(extracted / stage / "stage.json") == {"status": "RETURNED", "stage": stage,
                "request_sha256": request_sha, "source_sha256": SOURCE, "native_attempt_permitted": False},
                "MINICPM_SERIAL8_STAGE_BINDING")
    claims = read(extracted / "claims.json")
    names = {stage + ".json" for stage in ("launch", *STAGES)}
    loose_claims = safe(download, "minicpm-fulltrain-claims/mcpm4-restart-v1/8")
    require(set(claims) == names == {path.name for path in loose_claims.glob("*.json")},
        "MINICPM_SERIAL8_NO_NATIVE_OR_UNKNOWN_CLAIM")
    times = []
    for stage in ("launch", *STAGES):
        name = stage + ".json"
        row = claims[name]
        require(row == read(safe(loose_claims, name))
            and row == {"kind": stage, "number": 8, "request_sha256": request_sha,
                "ticket_sha256": TICKET_SHA, "time_unix": row["time_unix"]},
            "MINICPM_SERIAL8_CLAIM_BINDING")
        times.append(row["time_unix"])
    t = ticket["payload"]
    require(times == sorted(times) and t["issued_unix"] <= times[0] < t["start_before_unix"]
        and times[-1] < times[0] + request["plan"]["max_seconds"], "MINICPM_SERIAL8_CLAIM_WINDOW")
    retention = read(extracted / "retention.json")
    require(retention["retained"] == [] and retention["raw_deleted"] is False, "MINICPM_SERIAL8_NO_ATTEMPT_RETENTION")
    return {"disposition": "FAILED_PRE_NATIVE_NO_USABLE_RESULTS", "ticket_job": TICKET_JOB,
        "ticket_sha256": TICKET_SHA, "source_sha256": SOURCE, "event_sha256": EVENT_SHA,
        "supervisor_sha256": ZIP_SHA, "sidecar_sha256": sha(str(archive) + ".sha256.json"),
        "claims_sha256": digest(claims), "failure": "NVIDIA_SMI_EXIT_12",
        "native_loads": 0, "native_calls": 0, "counts": {"NOT_ATTEMPTED": 3763},
        "reserved_after": dict(RESERVED), "refund": False, "history_import": False}


def verify_local(processed):
    """Read-only check of the signed reservation, mirrors and downloaded bytes."""
    from safeshift.internvl3763_operator import code_hash
    from .minicpm_execution import MARKER

    files = []
    for name in (PRIMARY, MIRROR):
        root = safe(processed, name)
        event, registration = safe(root, "event-000001.json"), safe(root, "registration.json")
        require(list(root.glob("event-*.json")) == [event] and sha(event) == EVENT_SHA
            and sha(registration) == REGISTRATION_SHA, "MINICPM_SERIAL8_EXACT_MIRRORED_PREFIX")
        files.extend((event, registration))
    fence = safe(processed, FENCE)
    require(read(fence) == {"root": "data/processed/" + PRIMARY, "registration_sha256": REGISTRATION_SHA},
        "MINICPM_SERIAL8_FENCE")
    files.append(fence)
    registration, event = map(read, (files[1], files[0]))
    active = event["payload"]
    value, ticket = active["value"], active["ticket"]
    t, request = ticket["payload"], value["request"]
    old = old_release(registration["exports"]["/issues/comments/" + str(RELEASE["comment_id"])])
    require(event["kind"] == "RESERVED_OFFLINE" and event["previous"] == t["previous_event_sha256"] == REGISTRATION_SHA
        and registration["locator"] == RELEASE and t["grant_sha256"] == digest(old)
        and digest(ticket) == TICKET_SHA and digest(value) == t["value_sha256"] == t["capsule_sha256"]
        and t["number"] == 8 and t["reserved_before"] == serial7.RESERVED and t["reserved_after"] == RESERVED
        and value["job"] == TICKET_JOB and request["source_sha256"] == SOURCE
        and request["history"] == value["ancestors"] == [] and request["plan"]["counts"] == {"NOT_ATTEMPTED": 3763},
        "MINICPM_SERIAL8_SIGNED_RESERVATION_SCOPE")
    a.verify_signature(old["public_key"], t, ticket["signature"])
    for name in (PRIMARY, MIRROR):
        root = safe(processed, name)
        package, gate = safe(root, active["package"]), safe(root, active["gate_proof"])
        notebook = safe(package, "notebook.ipynb")
        spec, envelope = safe(package, "dataset/" + ui.MARKER), safe(package, "dataset/" + MARKER)
        require(sha(gate) == t["owner_gate"]["proof_sha256"]
            and read(notebook) == active["notebook"] and code_hash(active["notebook"]) == t["notebook_code_sha256"]
            and sha(spec) == digest(value) and sha(envelope) == TICKET_SHA, "MINICPM_SERIAL8_PACKAGE_CUSTODY")
        files.extend((gate, notebook, spec, envelope, safe(package, "owner-steps.json")))

    download = safe(processed, DOWNLOAD)
    names = inventory(download)
    snapshot = safe(download, "data/processed/fresh_fulltrain_code/" + SOURCE)
    require(digest(contract.source_manifest(snapshot)) == SOURCE, "MINICPM_SERIAL8_RUNTIME_SOURCE_BYTES")
    context = safe(download, "mcpm4-restart-v1-8-release-context.json")
    proof = safe(download, "mcpm4-restart-v1-8-authority-proof.json")
    require(read(context) == {"locator": RELEASE, "value": value, "ticket": ticket}
        and digest(read(proof)) == old["approvals"][a.PROOF_KEY], "MINICPM_SERIAL8_CONTEXT_BINDING")
    return verify_supervisor(download, value, ticket), active, files + [safe(download, name) for name in sorted(names)]


def verify_no_gpu(provider):
    require(provider.get("enable_gpu") is False and provider.get("machine_shape") in (None, "", "None", "Cpu", "CPU"),
        "MINICPM_SERIAL8_PROVIDER_NO_GPU_REQUIRED")


def verify_closure(closure, local, active):
    """Check the shape of the Owner export. The new authentic release pins its digest."""
    from .minicpm_execution import MARKER

    require(type(closure) is dict and set(closure) == {"local", "provider", "capsule", "output", "ticket_slug_visibility"}
        and closure["local"] == local and closure["ticket_slug_visibility"] == "ABSENT_IN_VERIFIED_OWNER_INVENTORY",
        "MINICPM_SERIAL8_OWNER_PROVIDER_CLOSURE_REQUIRED")
    provider, capsule, output = (closure[key] for key in ("provider", "capsule", "output"))
    require(provider["job_id"] == ACTUAL_JOB and provider["job_id"] != local["ticket_job"]
        and type(provider["version"]) is int and provider["version"] == 1
        and provider["state"] in ("COMPLETE", "ERROR")
        and type(provider["kernel_id"]) is int and provider["kernel_id"] > 0
        and provider["notebook_code_sha256"] == active["ticket"]["payload"]["notebook_code_sha256"]
        and provider["safeshift_metadata"] in ("MATCHED", "ABSENT_EXECUTABLE_CODE_BOUND"),
        "MINICPM_SERIAL8_ACTUAL_KERNEL_IDENTITY")
    verify_no_gpu(provider)
    require_hash(provider["remote_notebook_sha256"])
    require(capsule["private"] is True and capsule["version"] == 1
        and capsule["files"] == {ui.MARKER: digest(active["value"]), MARKER: digest(active["ticket"])}
        and output["pairs"] == {ARCHIVE: ZIP_SHA} and output["sidecar_sha256"] == local["sidecar_sha256"],
        "MINICPM_SERIAL8_PROVIDER_CAPSULE_OR_SUPERVISOR")
    names = output["inventory"]
    require(type(names) is list and len(names) <= 1024 and names == sorted(set(names))
        and {name for name in names if name.lower().endswith((".zip", ".zip.sha256.json"))}
        == {ARCHIVE, ARCHIVE + ".sha256.json"}, "MINICPM_SERIAL8_PROVIDER_SUPERVISOR_ONLY")
    require_hash(output["log_sha256"])
