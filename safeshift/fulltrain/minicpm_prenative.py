"""Generic closure of a signed MiniCPM serial that failed before native execution.

Every expectation comes from the signed reservation already held by the original
Operator (ticket, capsule value, release locator, authority-proof digest), never
from per-serial constants. The same checks therefore apply to Serial 8, 9, 10...

A closure proves only "no usable results": the supervisor sealed BLOCKED with
NO_ATTEMPT, every started stage child was reaped, no load/call claim exists, no
attempt reservation, tree or ZIP was produced. It keeps the full hold (no refund),
imports no history, and is never an authenticated provider receipt by itself:
the Owner's read-only provider closure and the final reconciliation recheck it.
"""
import math
from pathlib import Path
import re
import zipfile

from safeshift.candidates.source import require, snapshot_stat
from safeshift.pilot.artifacts import safe, sha
from safeshift.pilot.contract import digest, require_hash
from . import contract, minicpm_release as a, minicpm_ui as ui

SCHEMA = "safeshift-minicpm-pre-native-closure-v1"
PROVIDER_SCHEMA = "safeshift-minicpm-pre-native-provider-closure-v1"
DISPOSITION = "FAILED_PRE_NATIVE_NO_USABLE_RESULTS"
STAGES = a.STAGES[1:]
INVENTORY_BOUND = 4096
ARCHIVE_BOUND = 64 * 2**20
SUPERVISOR = re.compile(r"minicpm-fulltrain/supervision/[0-9a-f]{32}\.zip")
SLUG = re.compile(r"nguynanhtn/[a-z0-9](?:[a-z0-9-]{0,98}[a-z0-9])?")
CLAIM_FIELDS = {"kind", "number", "request_sha256", "ticket_sha256", "time_unix"}
LAUNCH_TIMEOUT_FAILURE = {"type": "TimeoutError", "message": "SUPERVISED_PARENT_DEADLINE_LAUNCH",
                          "stage": "launch", "category": "TECHNICAL"}


def launch_stop(request, ticket):
    return {"status": "RESTORE_TIMED_OUT_BEFORE_CHILD_DISPATCH", "staging_discarded": True,
            "request_sha256": digest(request), "ticket_sha256": digest(ticket)}


def inventory(download):
    """Bounded, symlink-free relative file list of an Owner-downloaded Output."""
    download = Path(download)
    pending, names, seen = [download], [], 0
    while pending:
        directory = pending.pop()
        snapshot_stat(directory, directory=True)
        for path in directory.iterdir():
            seen += 1
            require(seen <= INVENTORY_BOUND, "MINICPM_PRE_NATIVE_INVENTORY_BOUND")
            require(not path.is_symlink(), "MINICPM_PRE_NATIVE_INVENTORY_ALIAS")
            if path.is_dir():
                pending.append(path)
            else:
                snapshot_stat(path)
                names.append(path.relative_to(download).as_posix())
    return sorted(names)


def supervisor_only(names, run_id, attempt_id):
    """Exactly one sealed supervisor pair; no attempt reservation, tree or ZIP."""
    archives = [n for n in names if n.lower().endswith(".zip")]
    sidecars = [n for n in names if n.lower().endswith(".zip.sha256.json")]
    require(len(archives) == 1 and SUPERVISOR.fullmatch(archives[0])
        and sidecars == [archives[0] + ".sha256.json"], "MINICPM_PRE_NATIVE_SUPERVISOR_ONLY")
    run = "minicpm-fulltrain/" + run_id
    require(not any(n == run + ".zip" or n.startswith(run + "/") for n in names)
        and "minicpm-fulltrain/attempts/" + attempt_id + ".json" not in names,
        "MINICPM_PRE_NATIVE_ATTEMPT_OBSERVED")
    return archives[0]


def _json(bundle, name):
    require(name in bundle.namelist(), "MINICPM_PRE_NATIVE_RECEIPT_MISSING:" + name)
    return a.strict_json(bundle.read(name))


def _work_files(download, names, archive, value, *, restored=True):
    """Only the supervisor and the signed, restored predecessor reservations may exist."""
    request = value["request"]
    campaign = digest(request["campaign"])
    lease = digest({"campaign": request["campaign"], "model": request["model_key"]})
    allowed = {"minicpm-fulltrain/attempts/active_" + lease + ".lock",
        "minicpm-fulltrain/supervisor_control/attempts/active_" + lease + ".lock",
        archive, archive + ".sha256.json"}
    if not restored:
        require(not any(name.startswith("minicpm-history-") for name in names),
                "MINICPM_PRE_NATIVE_LAUNCH_STAGING_REMAINS")
        prefix = archive[:-4] + "/"
        require(all(name in (archive, archive + ".sha256.json") or name.startswith(prefix)
            for name in names if name.startswith("minicpm-fulltrain/")), "MINICPM_PRE_NATIVE_UNKNOWN_WORK_OUTPUT")
        return
    for h, ancestor in zip(request["history"], value["ancestors"]):
        name = "minicpm-fulltrain/attempts/" + h["attempt_id"] + ".json"
        require(read_json_file(download, name) == {"plan_sha256": ancestor["plan_sha256"], "campaign_sha256": campaign},
            "MINICPM_PRE_NATIVE_ANCESTOR_RESERVATION")
        allowed.add(name)
    campaign_file = "minicpm-fulltrain/campaign.json"
    if request["history"] or campaign_file in names:
        require(read_json_file(download, campaign_file) == request["campaign"], "MINICPM_PRE_NATIVE_CAMPAIGN")
        allowed.add(campaign_file)
    loose_prefix = archive[:-4] + "/"
    require(all(name in allowed or name.startswith(loose_prefix)
        for name in names if name.startswith("minicpm-fulltrain/")), "MINICPM_PRE_NATIVE_UNKNOWN_WORK_OUTPUT")


def read_json_file(directory, name):
    path = safe(directory, name)
    require(snapshot_stat(path).st_size <= 64 * 2**20, "MINICPM_PRE_NATIVE_JSON_BOUND")
    return a.strict_json(path.read_bytes())


def _extracted(archive, bundle):
    """Loose copies, when downloaded, must be byte-identical ZIP members."""
    root = Path(str(archive)[:-4])
    if not root.exists():
        return
    members = set(bundle.namelist())
    bounded = _json(bundle, "log_exports.json") if "log_exports.json" in members else {}
    for path in (p for p in root.rglob("*") if p.is_file()):
        name = path.relative_to(root).as_posix()
        if name in members:
            require(snapshot_stat(path).st_size == bundle.getinfo(name).file_size
                and path.read_bytes() == bundle.read(name), "MINICPM_PRE_NATIVE_EXTRACTED_RECEIPT_DRIFT")
        else:
            # Only an oversized original log, exported as a bounded tail.
            require(name in bounded and sha(path) == bounded[name]["original_sha256"],
                "MINICPM_PRE_NATIVE_EXTRACTED_UNKNOWN_FILE")


def _stages(bundle, release, request_sha, source):
    """Contiguous reaped stage prefix ending at the failing stage."""
    last = release["last_stage"]
    require(last in STAGES, "MINICPM_PRE_NATIVE_LAST_STAGE")
    members = set(bundle.namelist())
    present = [s for s in STAGES if s + "-process.json" in members]
    k = STAGES.index(last)
    # A missing process receipt is ambiguous even when the supervisor saw no tree.
    require(present == list(STAGES[:k + 1]), "MINICPM_PRE_NATIVE_STAGE_PREFIX")
    require(not any(name.startswith(stage + "/") for stage in STAGES[k+1:] for name in members),
        "MINICPM_PRE_NATIVE_STAGE_AFTER_FAILURE")
    for stage in present:
        process = _json(bundle, stage + "-process.json")
        group = process.get("group_exit", {})
        require(process.get("schema") == "fresh-process-supervision-v1" and process.get("automatic_retry") is False
            and group.get("status") == "NO_LIVE_MEMBERS" and type(group.get("members")) is list
            and all(row.get("state") == "Z" for row in group["members"]),
            "MINICPM_PRE_NATIVE_UNREAPED_STAGE")
        binding = {"status": "RETURNED", "stage": stage, "request_sha256": request_sha,
                   "source_sha256": source, "native_attempt_permitted": stage == "native"}
        if stage != last:
            require((process["status"], process["returncode"]) == ("EXITED", 0)
                and _json(bundle, stage + "/stage.json") == binding, "MINICPM_PRE_NATIVE_STAGE_BINDING")
        else:
            require(process["status"] in ("CHILD_FAILURE", "HARD_DEADLINE", "LOG_BUDGET_EXCEEDED")
                and type(process["returncode"]) is int
                and (process["status"] != "CHILD_FAILURE" or process["returncode"] != 0),
                "MINICPM_PRE_NATIVE_CHILD_FAILURE")
    failure = release["failure"]
    child = stage_failure = None
    if last + "/failure.json" in members:
        child = _json(bundle, last + "/failure.json")
        stage_failure = {"type": child.get("type"), "message_sha256": digest(str(child.get("message")))}
    return {"last_stage": last, "child_launched": last in present,
            "fingerprint": {"stage": last, "supervisor_type": failure.get("type"),
                            "supervisor_message": failure.get("message"), "child": stage_failure}}


def _claims(download, bundle, ticket, request, campaign_id, last):
    """Create-only capability claims: no load/call; bound to this exact ticket."""
    t = ticket["payload"]
    claims = _json(bundle, "claims.json")
    allowed = ("launch",) if last == "launch" else ("launch",) + STAGES[:STAGES.index(last) + 1]
    kinds = [kind for kind in allowed if kind + ".json" in claims]
    require(set(claims) == {kind + ".json" for kind in kinds}
        and kinds and kinds in (list(allowed), list(allowed[:-1])),
        "MINICPM_PRE_NATIVE_NO_LOAD_OR_CALL_CLAIM")
    loose = safe(download, "minicpm-fulltrain-claims/" + campaign_id + "/" + str(t["number"]))
    require({p.name for p in loose.glob("*.json")} == set(claims), "MINICPM_PRE_NATIVE_LOOSE_CLAIMS")
    times = []
    for kind in kinds:
        row = claims[kind + ".json"]
        require(a.strict_json((loose / (kind + ".json")).read_bytes()) == row
            and type(row) is dict and set(row) == CLAIM_FIELDS and row["kind"] == kind
            and row["number"] == t["number"] and row["ticket_sha256"] == digest(ticket)
            and row["request_sha256"] == digest(request) and type(row["time_unix"]) in (int, float)
            and math.isfinite(row["time_unix"]), "MINICPM_PRE_NATIVE_CLAIM_BINDING")
        times.append(row["time_unix"])
    require(times == sorted(times) and t["issued_unix"] <= times[0] < t["start_before_unix"]
        and times[-1] < times[0] + request["plan"]["max_seconds"], "MINICPM_PRE_NATIVE_CLAIM_WINDOW")
    return digest(claims)


def verify_download(download, active, locator, campaign_id, *, proof_sha256=None, bounded_launch=False):
    """Read-only check of an Owner download against one signed reservation."""
    download = Path(download)
    value, ticket = active["value"], active["ticket"]
    request, t = value["request"], ticket["payload"]
    plan = request["plan"]
    names = inventory(download)
    archive_name = supervisor_only(names, plan["run_id"], plan["attempt_id"])
    archive = safe(download, archive_name)
    require(snapshot_stat(archive).st_size <= ARCHIVE_BOUND, "MINICPM_PRE_NATIVE_ARCHIVE_BOUND")
    entries = ui.pair(archive)
    request_sha, source = digest(request), request["source_sha256"]
    with zipfile.ZipFile(archive) as bundle:
        _extracted(archive, bundle)
        require(_json(bundle, "request.json") == request
            and _json(bundle, "capability.json") == {"locator": locator, "ticket": ticket},
            "MINICPM_PRE_NATIVE_REQUEST_TICKET")
        release = _json(bundle, "release.json")
        require(type(release) is dict and release.get("status") == "BLOCKED"
            and release.get("attempt_observed") is False and release.get("recovery") == "NO_ATTEMPT"
            and release.get("automatic_retry") is False and release.get("diagnostic") is False
            and release.get("scientific_qualified") is False and release.get("source_sha256") == source
            and type(release.get("failure")) is dict and release["failure"] == _json(bundle, "failure.json"),
            "MINICPM_PRE_NATIVE_SEALED_BLOCKED_NO_ATTEMPT")
        members = set(bundle.namelist())
        last = release["last_stage"]
        _work_files(download, names, archive_name, value, restored=last != "launch")
        if last == "launch":
            require(bounded_launch and proof_sha256 is not None
                and members == {"request.json", "capability.json", "release.json", "failure.json", "claims.json",
                                "launch-stop.json", "checksums.json"}
                and release["failure"] == LAUNCH_TIMEOUT_FAILURE
                and _json(bundle, "launch-stop.json") == launch_stop(request, ticket),
                "MINICPM_PRE_NATIVE_LAUNCH_STOP_UNVERIFIED")
            stages = {"last_stage": last, "child_launched": False, "fingerprint": {
                "stage": last, "supervisor_type": "TimeoutError",
                "supervisor_message": LAUNCH_TIMEOUT_FAILURE["message"], "child": None}}
        else:
            require(not bounded_launch or last != "native", "MINICPM_PRE_NATIVE_NATIVE_DISPATCH_REQUIRES_RECONCILIATION")
            stages = _stages(bundle, release, request_sha, source)
            require("retention.json" in members and "retention_failure.json" not in members, "MINICPM_PRE_NATIVE_RETENTION")
            retention = _json(bundle, "retention.json")
            require(retention["status"] == "SEALED_ZIPS_IN_OUTPUT_RAW_BYTES_RETAINED_IN_SCRATCH"
                and retention["raw_deleted"] is False and
                [(row["run_id"], row["archive_sha256"]) for row in retention["retained"]] ==
                [(h["run_id"], ancestor["sha256"]) for h, ancestor in zip(request["history"], value["ancestors"])],
                "MINICPM_PRE_NATIVE_RETENTION")
        claims_sha = _claims(download, bundle, ticket, request, campaign_id, last)
    context = safe(download, plan["run_id"] + "-release-context.json")
    require(a.strict_json(context.read_bytes()) == {"locator": locator, "value": value, "ticket": ticket},
        "MINICPM_PRE_NATIVE_CONTEXT_BINDING")
    if proof_sha256 is not None:
        proof = safe(download, plan["run_id"] + "-authority-proof.json")
        require(digest(a.strict_json(proof.read_bytes())) == proof_sha256, "MINICPM_PRE_NATIVE_AUTHORITY_PROOF")
    snapshot = safe(download, "data/processed/fresh_fulltrain_code/" + source)
    require(digest(contract.source_manifest(snapshot)) == source, "MINICPM_PRE_NATIVE_RUNTIME_SOURCE_BYTES")
    pending = plan["counts"]["NOT_ATTEMPTED"]
    # The Kaggle UI can add a standalone notebook log to the downloaded
    # directory. Every file within the evidence trees must appear at the provider.
    provider_files = [name for name in names if "/" in name or not name.endswith(".log")]
    return {"schema": SCHEMA, "disposition": DISPOSITION, "number": t["number"], "ticket_job": value["job"],
        "ticket_sha256": digest(ticket), "value_sha256": digest(value), "source_sha256": source,
        "run_id": plan["run_id"], "supervisor": archive_name, "supervisor_sha256": sha(archive),
        "supervisor_members": len(entries), "sidecar_sha256": sha(str(archive) + ".sha256.json"),
        "claims_sha256": claims_sha, "inventory_sha256": digest(names),
        "provider_files_sha256": digest(provider_files), **stages,
        "native_loads": 0, "native_calls": 0, "pending_not_attempted": pending,
        "reserved_after": dict(t["reserved_after"]), "refund": False, "history_import": False,
        "provider_verification": "LOCAL_DOWNLOAD_ONLY"}


def package_files(package):
    """Hashes of every capsule file the Owner uploaded from this handoff."""
    directory = safe(package, "dataset")
    return {path.name: sha(safe(directory, path.name)) for path in directory.iterdir()}


def verify_provider(closure, local, active, files):
    """Shape and bindings of the Owner's read-only provider closure export."""
    from .minicpm_execution import MARKER
    value, ticket = active["value"], active["ticket"]
    require(type(closure) is dict and set(closure) == {"schema", "local", "provider", "accelerator",
        "ticket_job", "provider_job", "capsule", "output"} and closure["schema"] == PROVIDER_SCHEMA
        and closure["local"] == local and closure["ticket_job"] == value["job"],
        "MINICPM_PRE_NATIVE_OWNER_PROVIDER_CLOSURE_REQUIRED")
    provider, capsule, output = closure["provider"], closure["capsule"], closure["output"]
    job = closure["provider_job"]
    require(type(job) is str and SLUG.fullmatch(job) and provider["job_id"] == job
        and type(provider["version"]) is int and provider["version"] == 1
        and provider["state"] in ("COMPLETE", "ERROR")
        and type(provider["kernel_id"]) is int and provider["kernel_id"] > 0
        and provider["notebook_code_sha256"] == ticket["payload"]["notebook_code_sha256"]
        and provider["safeshift_metadata"] in ("MATCHED", "ABSENT_EXECUTABLE_CODE_BOUND"),
        "MINICPM_PRE_NATIVE_KERNEL_IDENTITY")
    require_hash(provider["remote_notebook_sha256"])
    accelerator = closure["accelerator"]
    require(type(accelerator) is dict and set(accelerator) == {"enable_gpu", "machine_shape", "scope"}
        and type(accelerator["enable_gpu"]) in (bool, type(None))
        and type(accelerator["machine_shape"]) in (str, type(None))
        and accelerator["scope"] == "CURRENT_KERNEL_METADATA_NOT_EXECUTION_TIME_PROOF",
        "MINICPM_PRE_NATIVE_ACCELERATOR_RECORD")
    require(capsule["private"] is True and capsule["version"] == 1 and capsule["files"] == files
        and files.get(ui.MARKER) == digest(value) and files.get(MARKER) == digest(ticket),
        "MINICPM_PRE_NATIVE_PROVIDER_CAPSULE")
    expected = {ui.MARKER, MARKER}
    for ancestor in value["ancestors"]:
        name = ancestor["file"]
        require(files.get(name) == ancestor["sha256"], "MINICPM_PRE_NATIVE_CAPSULE_ANCESTOR")
        expected.update((name, name + ".sha256.json"))
    require(set(files) == expected, "MINICPM_PRE_NATIVE_CAPSULE_FILES")
    names = output["inventory"]
    require(output["pairs"] == {local["supervisor"]: local["supervisor_sha256"]}
        and output["sidecar_sha256"] == local["sidecar_sha256"]
        and type(names) is list and len(names) <= INVENTORY_BOUND and names == sorted(set(names))
        and digest([name for name in names if "/" in name or not name.endswith(".log")]) == local["provider_files_sha256"]
        and {n for n in names if n.lower().endswith((".zip", ".zip.sha256.json"))}
            == {local["supervisor"], local["supervisor"] + ".sha256.json"},
        "MINICPM_PRE_NATIVE_PROVIDER_SUPERVISOR_ONLY")
    require_hash(output["log_sha256"])
    return closure


def same_execution(original, current):
    """Recheck immutable identity, source, capsule and Output across UI renames."""
    for key in ("schema", "local", "ticket_job", "capsule", "output"):
        require(original[key] == current[key], "MINICPM_PRE_NATIVE_PROVIDER_EVIDENCE_CHANGED")
    for observation in (original, current):
        require(observation["provider_job"] == observation["provider"]["job_id"]
            and SLUG.fullmatch(observation["provider_job"]), "MINICPM_PRE_NATIVE_KERNEL_IDENTITY")
    require({k: v for k, v in original["provider"].items() if k != "job_id"}
        == {k: v for k, v in current["provider"].items() if k != "job_id"},
        "MINICPM_PRE_NATIVE_KERNEL_CHANGED")
