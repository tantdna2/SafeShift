"""Verify the exact Serial 8 GPU-stage incident and bind its successor.

The checks are the generic pre-native closure (``minicpm_prenative``) plus the
historical pins of this frozen V4 reservation. The sealed traceback proves
nvidia-smi exited 12. The exact container driver/allocation cause is unknown.
Version 1 provider metadata records GPU enabled on T4. The stable kernel ID,
exact notebook code, private capsule and sealed Output bind the run across renames.
"""
from copy import deepcopy

from safeshift.candidates.source import require
from safeshift.pilot.artifacts import read, safe, sha
from safeshift.pilot.contract import digest, require_hash
from . import minicpm_prenative as prenative, minicpm_release as a, minicpm_serial7 as serial7, minicpm_ui as ui

PRIMARY = "minicpm-offline-s8"
MIRROR = PRIMARY + "-mirror"
DOWNLOAD = "inspect_run_8"
FENCE = "minicpm-release-registrations/mcpm4-restart-v1-offline-post-serial7.json"
TICKET_JOB = "nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-8"
# Owner-reported slug at run time; the kernel later carried TICKET_JOB.
REPORTED_JOB = "nguynanhtn/notebook1358a4d09b"
PROVIDER_JOBS = (TICKET_JOB, REPORTED_JOB)
KERNEL_ID = 145987007
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
    names = prenative.inventory(download)
    require({n for n in names if n.lower().endswith((".zip", ".zip.sha256.json"))}
        == {ARCHIVE, ARCHIVE + ".sha256.json"}, "MINICPM_SERIAL8_SUPERVISOR_ONLY")
    require(digest(names) == INVENTORY_SHA, "MINICPM_SERIAL8_LOCAL_INVENTORY_DRIFT")
    return set(names)


def verify_supervisor(download, value, ticket, old):
    """Generic pre-native checks, then the exact historical pins."""
    inventory(download)
    local = prenative.verify_download(download, {"value": value, "ticket": ticket}, RELEASE,
        old["campaign_id"], proof_sha256=old["approvals"][a.PROOF_KEY])
    child = read(safe(download, ARCHIVE[:-4] + "/gpu/failure.json"))
    require(local["supervisor"] == ARCHIVE and local["supervisor_sha256"] == ZIP_SHA
        and local["source_sha256"] == SOURCE and local["ticket_sha256"] == TICKET_SHA
        and local["last_stage"] == "gpu" and local["child_launched"] is True
        and child["type"] == "CalledProcessError" and child["message"].startswith("Command '['nvidia-smi', ")
        and child["message"].endswith("returned non-zero exit status 12."), "MINICPM_SERIAL8_GPU_STAGE_FAILURE")
    return {**local, "event_sha256": EVENT_SHA, "failure": "NVIDIA_SMI_EXIT_12",
        "container_driver_or_allocation_cause": "UNVERIFIED", "reserved_after": dict(RESERVED)}


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
    local = verify_supervisor(download, value, ticket, old)
    return local, active, files + [safe(download, name) for name in sorted(inventory(download))]


def verify_closure(closure, local, active):
    """Owner provider export; the new authentic release pins its digest.

    The accelerator is recorded, not gated: zero native activity is proven by
    the sealed supervisor and claims, whatever the kernel's GPU setting.
    """
    from .minicpm_execution import MARKER
    files = {ui.MARKER: digest(active["value"]), MARKER: digest(active["ticket"])}
    prenative.verify_provider(closure, local, active, files)
    require(closure["provider"]["kernel_id"] == KERNEL_ID and closure["provider"]["state"] == "COMPLETE",
        "MINICPM_SERIAL8_ACTUAL_KERNEL_IDENTITY")
