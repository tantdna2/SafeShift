"""Read-only custody of the exact Serial 6 local download and signed hold."""
from pathlib import Path
import zipfile

from safeshift.candidates.source import require, snapshot_stat
from safeshift.pilot.artifacts import read, safe, sha
from safeshift.pilot.contract import digest
from . import minicpm_release as authority, minicpm_ui as ui

JOB = "nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-6"
SOURCE = "cc0141cb3800898398d32d8114c275e0c89773a41affcd3dcd2ca2a8b86b2f95"
ARCHIVE = "minicpm-fulltrain/supervision/2f26e8db607d47f180feff588f840639.zip"
ZIP_SHA = "3d92d80065e89fe2abd22e81b4f64462121e0f0a8b2d03be986c4f5bfdd93a5c"
EVENT_SHA = "b32b8728b5848ca94c9b883c1718969aeb2891d4e3d2d3e2b950cc7c4394b200"
REGISTRATION = "07cd039900e6a5a209c35d70de9a7149b04cdfe5bf93ace92c125dfdf03414e9"
TICKET_SHA = "99085ce10341106b99e8470cc30ff25f0e5c041008436d0b6511a5f975c653b2"
INVENTORY = "5619f6a75caa10a0e21f6db4ae51685b355fd80ecf9b939f467b88bd42834b8c"
RESERVED = {"calls": 10626, "jobs": 6, "gpu_seconds": 172800}
FIRST_SERIAL = 7


def verify_local(processed):
    """Check immutable bytes, archive/extracted agreement and absence of later claims."""
    processed = Path(processed)
    files = []
    for name in ("minicpm-offline", "minicpm-offline-mirror"):
        root = safe(processed, name)
        event = safe(root, "event-000001.json")
        registration = safe(root, "registration.json")
        require(list(root.glob("event-*.json")) == [event] and sha(event) == EVENT_SHA
                and sha(registration) == REGISTRATION, "SERIAL6_EXACT_OFFLINE_PREFIX")
        files.extend((registration, event))
    fence = safe(processed, "minicpm-release-registrations/mcpm4-restart-v1-offline-v1.json")
    require(read(fence) == {"registration_sha256": REGISTRATION, "root": "data/processed/minicpm-offline"},
            "SERIAL6_ORIGINAL_REGISTRATION")
    files.append(fence)
    row = read(event)
    item = row["payload"]
    ticket, value = item["ticket"], item["value"]
    reg = read(registration)
    old = authority.record(reg["exports"]["/issues/comments/6957931785"]["body"],
                           "SAFESHIFT_MINICPM_OFFLINE_RELEASE_V2")
    require(row["kind"] == "RESERVED_OFFLINE" and row["previous"] == REGISTRATION
            and digest(ticket) == TICKET_SHA and ticket["payload"]["grant_sha256"] == digest(old)
            and ticket["payload"]["value_sha256"] == digest(value) and value["job"] == JOB
            and value["request"]["source_sha256"] == SOURCE and ticket["payload"]["reserved_after"] == RESERVED,
            "SERIAL6_TICKET_SOURCE_OR_HOLD")
    authority.verify_signature(old["public_key"], ticket["payload"], ticket["signature"])
    download = safe(processed, "inspect_run_6")
    # Exact inspected file listing also rejects an extra attempt, raw or loose claim.
    names = []
    pending = [download]
    while pending:
        parent = pending.pop()
        for entry in parent.iterdir():
            require(len(names) + len(pending) < 512, "SERIAL6_INVENTORY_BOUND")
            if entry.is_dir():
                snapshot_stat(entry, directory=True)
                pending.append(entry)
            else:
                snapshot_stat(entry)
                names.append(entry.relative_to(download).as_posix())
    require(digest(sorted(names)) == INVENTORY, "SERIAL6_LOCAL_INVENTORY_CHANGED")
    archive = safe(download, ARCHIVE)
    ui.pair(archive, ZIP_SHA)
    out = archive.with_suffix("")
    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            path = safe(out, name)
            require(path.read_bytes() == bundle.read(name), "SERIAL6_EXTRACTED_RECEIPT_CHANGED")
            files.append(path)
    files.extend((archive, Path(str(archive) + ".sha256.json")))
    context = safe(download, "mcpm4-restart-v1-6-release-context.json")
    require(read(context) == {"locator": reg["locator"], "value": value, "ticket": ticket}
            and read(out / "request.json") == value["request"]
            and read(out / "capability.json") == {"locator": reg["locator"], "ticket": ticket},
            "SERIAL6_SUPERVISOR_BINDING")
    files.append(context)
    claims = read(out / "claims.json")
    require(set(claims) == {n + ".json" for n in ("launch", "admit", "setup", "reclaim")},
            "SERIAL6_UNEXPECTED_NATIVE_CLAIM")
    for name, claim in claims.items():
        path = safe(download, "minicpm-fulltrain-claims/mcpm4-restart-v1/6/" + name)
        require(read(path) == claim and claim["ticket_sha256"] == TICKET_SHA, "SERIAL6_CLAIM_CHANGED")
        files.append(path)
    release = read(out / "release.json")
    failure = read(out / "reclaim/failure.json")
    observed = read(out / "reclaim/post-advice-before-memory.json")
    available = observed["gate_memory"]["available_bytes"]
    floor = value["request"]["resource_policy"]["free_ram_mib"] * 2**20
    require(release["last_stage"] == "reclaim" and release["status"] == "BLOCKED"
            and release["attempt_observed"] is False and release["recovery"] == "NO_ATTEMPT"
            and failure["message"] == "HOST_OR_CGROUP_RAM" and failure["type"] == "ValueError"
            and available == 14420357120 and floor == 17179869184, "SERIAL6_FAILURE_CUSTODY")
    return {"job": JOB, "source_sha256": SOURCE, "supervisor_sha256": ZIP_SHA,
            "ticket_sha256": TICKET_SHA, "event_sha256": EVENT_SHA, "last_stage": "reclaim",
            "failure": failure["message"], "available_bytes": available, "required_available_bytes": floor,
            "native_loads": 0, "native_calls": 0, "reserved_after": dict(RESERVED),
            "disposition": "FAILED_PRE_NATIVE_NO_USABLE_RESULTS",
            "provider_verification": "LOCAL_DOWNLOAD_ONLY"}, files
