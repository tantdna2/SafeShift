"""Released Owner UI and isolated child entrypoints, using PR195's pipeline."""
import argparse
from contextlib import ExitStack, nullcontext
import os
import math
from pathlib import Path
import shutil
import tempfile
import time
import uuid

from safeshift.candidates.source import ROOT, require, snapshot_stat
from safeshift.candidates.train_inputs import discover
from safeshift.pilot.artifacts import read, write, safe, sha
from safeshift.pilot.contract import digest
from safeshift.pilot.runner import error_record
from . import minicpm_release as authority, minicpm_ui as ui

MARKER = "safeshift_minicpm_release_ticket.json"


def metadata(path, limit=64 * 2**20):
    require(snapshot_stat(path).st_size <= limit, "MINICPM_CONTEXT_METADATA_BOUND")
    return read(path)


def run_capsule(inputs, capsule_sha256, locator, *, repo=ROOT, started_unix=None, bounded_launch=False):
    started_unix = time.time() if started_unix is None else started_unix
    require(type(started_unix) in (int,float) and math.isfinite(started_unix) and started_unix <= time.time(),
        "MINICPM_NOTEBOOK_START_TIME")
    from .minicpm_offline import LAUNCH_SECONDS
    from .supervision import parent_deadline
    deadline = time.monotonic() + LAUNCH_SECONDS - (time.time() - started_unix)
    with ExitStack() as stack:
        try:
            with parent_deadline(deadline, "launch") if bounded_launch else nullcontext():
                request, context = _prepare_capsule(inputs, capsule_sha256, locator, repo, started_unix, stack, bounded_launch)
        except Exception:
            if bounded_launch:
                print("MINICPM_BLOCKED_LAUNCH_WITHOUT_RESTORE_RECEIPT_KEEP_RESERVATION", flush=True)
            raise
        if bounded_launch:
            failure_output = _restore_bounded(request, context, deadline)
            if failure_output is not None:
                return failure_output
        from .runtime import launch
        return launch(request, repo=repo)


def _prepare_capsule(inputs, capsule_sha256, locator, repo, started_unix, stack, bounded_launch):
    # Genuine authority before any Input path, request, credentials or model IO.
    from .minicpm_offline import serial22_recovery
    proof = {}
    grant = authority.load(locator, repo=repo, capture=proof)
    require(bounded_launch == serial22_recovery(grant), "MINICPM_EXACT_NOTEBOOK_LAUNCH_BUDGET")
    marker = discover(inputs, MARKER, limit=128)
    require(hasattr(os, "statvfs") and os.statvfs(marker.parent).f_flag & os.ST_RDONLY,
        "MINICPM_CAPSULE_READ_ONLY")
    envelope = metadata(marker, 128 * 2**20)
    value_marker = safe(marker.parent, ui.MARKER)
    require(sha(value_marker) == capsule_sha256, "MINICPM_RELEASE_CAPSULE_PIN")
    ticket = authority.verify_ticket(grant, envelope, metadata(value_marker), repo=repo)
    # The released launch restores and validates directly into the fresh VM
    # below. A second temporary replay would read the same signed ancestors.
    value = ui.verify_capsule(marker.parent, capsule_sha256, repo, release_ticket=True,
        replay="continuation" not in grant)
    if grant["schema"] == authority.RECOVERY_SCHEMA:
        from .minicpm_recovery import mounted_inputs
        from safeshift import internvl3763_python as py
        table = mounted_inputs(value)
        for ref, filename in ((value["capsule_ref"], MARKER), (py.REF, py.MARKER),
                              (ui.CHECKPOINT, "candidate_checkpoint_minicpm4.json")):
            found = discover(inputs, filename, limit=128)
            require(found.parent == safe(inputs, table[ref]["mount"]), "MINICPM_RECOVERY_EXACT_NESTED_INPUT")
    owner, slug, _ = value["capsule_ref"].split("/")
    require(marker.parent.relative_to(Path(inputs)).as_posix() in (slug, "datasets/" + owner + "/" + slug),
        "MINICPM_V2_CAPSULE_MOUNT")
    request = value["request"]
    work, scratch = Path(request["work"]), Path(request["scratch"])
    staged = None
    restoration_seconds = None
    if "continuation" in grant:
        require(not work.exists() and not scratch.exists(), "MINICPM_V2_FRESH_VM_WORKSPACE")
        require(time.time() < ticket["start_before_unix"], "MINICPM_STALE_PROVIDER_BEFORE_LAUNCH")
    if "continuation" in grant and not bounded_launch:
        temporary = stack.enter_context(tempfile.TemporaryDirectory(prefix="minicpm-history-", dir=work.parent))
        staged = Path(temporary) / "work"
        restoration_started = time.monotonic()
        ui.restore_history(marker.parent, value, staged)
        restoration_seconds = time.monotonic() - restoration_started
    context = stack.enter_context(authority._activated(grant, locator, envelope, value, "launch",
        repo=repo, started_unix=started_unix))
    authority.authorize(request=request)
    require(not work.exists() and not scratch.exists(), "MINICPM_V2_FRESH_VM_WORKSPACE")
    if not bounded_launch:
        if staged is None:
            ui.restore_history(marker.parent, value, work)
        elif staged.exists():
            staged.rename(work)
        work.mkdir(parents=True, exist_ok=True)
        scratch.mkdir(parents=True, exist_ok=False)
    context["history_restore_seconds"] = restoration_seconds
    context_file = work.parent / (request["plan"]["run_id"] + "-release-context.json")
    write(context_file, {"locator": locator, "ticket": envelope, "value": value})
    context["context_file"] = str(context_file)
    if authority.uses_proof(grant):
        proof_file = work.parent / (request["plan"]["run_id"] + "-authority-proof.json")
        write(proof_file, proof)
        context["proof_file"] = str(proof_file)
    context["capsule_directory"] = str(marker.parent)
    return request, context


def _restore_bounded(request, context, deadline):
    """Restore after the authenticated launch claim and before any child dispatch."""
    from . import supervision

    work, scratch = Path(request["work"]), Path(request["scratch"])
    started = time.monotonic()
    staging = None
    try:
        with supervision.parent_deadline(deadline, "launch"):
            staging = Path(tempfile.mkdtemp(prefix="minicpm-history-", dir=work.parent))
            staged = staging / "work"
            ui.restore_released_history(context["capsule_directory"], context["value"], staged, deadline)
    except (TimeoutError, ValueError) as error:
        if time.monotonic() < deadline or str(error) not in (
                "SUPERVISED_PARENT_DEADLINE_LAUNCH", "READONLY_ADVICE_DEADLINE"):
            print("MINICPM_BLOCKED_LAUNCH_WITHOUT_RESTORE_RECEIPT_KEEP_RESERVATION", flush=True)
            raise
        return _seal_restore_timeout(request, context, staging)
    try:
        with supervision.parent_deadline(deadline, "launch_install"):
            if staged.exists():
                staged.rename(work)
            staging.rmdir()
            work.mkdir(parents=True, exist_ok=True)
            scratch.mkdir(parents=True, exist_ok=False)
    except TimeoutError:
        print("MINICPM_BLOCKED_LAUNCH_INSTALL_KEEP_RESERVATION", flush=True)
        raise
    context["history_restore_seconds"] = time.monotonic() - started
    return None


def _seal_restore_timeout(request, context, staging):
    from . import minicpm_prenative, supervision
    from .minicpm_offline import SUPERVISOR_SEAL_SECONDS

    print("MINICPM_BLOCKED_LAUNCH_RESTORE_TIMEOUT_KEEP_RESERVATION", flush=True)
    ticket = context["ticket"]
    claims = authority.claims_snapshot()
    work, scratch = Path(request["work"]), Path(request["scratch"])
    require(set(claims) == {"launch.json"} and not work.exists() and not scratch.exists(),
            "MINICPM_BLOCKED_LAUNCH_CUSTODY_AMBIGUOUS")
    deadline = time.monotonic() + claims["launch.json"]["time_unix"] + request["plan"]["max_seconds"] - time.time()
    cleanup_failure = None
    try:
        with supervision.parent_deadline(min(time.monotonic() + SUPERVISOR_SEAL_SECONDS,
                                             deadline - SUPERVISOR_SEAL_SECONDS), "launch_cleanup"):
            if staging is not None:
                # This tree contains only staging copies of immutable capsule ancestors.
                shutil.rmtree(staging)
    except Exception as error:
        cleanup_failure = error_record(error, "launch_cleanup")
    output = work / "supervision" / uuid.uuid4().hex
    with supervision.parent_deadline(deadline - 5, "launch_receipt"):
        failure = minicpm_prenative.LAUNCH_TIMEOUT_FAILURE
        write(output / "request.json", request)
        write(output / "capability.json", {"locator": context["locator"], "ticket": ticket})
        write(output / "claims.json", claims)
        if cleanup_failure is None:
            write(output / "launch-stop.json", minicpm_prenative.launch_stop(request, ticket))
        else:
            write(output / "launch-cleanup-failure.json", cleanup_failure)
        write(output / "failure.json", failure)
        write(output / "release.json", {"status": "BLOCKED", "diagnostic": False, "last_stage": "launch",
            "failure": failure, "attempt_observed": False,
            "recovery": "NO_ATTEMPT" if cleanup_failure is None else "LAUNCH_STAGING_REQUIRES_RECONCILIATION",
            "automatic_retry": False,
            "scientific_qualified": False, "source_sha256": request["source_sha256"]})
    supervision.seal_supervisor(output, min(deadline, time.monotonic() + SUPERVISOR_SEAL_SECONDS))
    return output


def retain_sealed_trees(request, work, scratch, capsule_directory, *, ancestors=None, deadline=None):
    """Keep ZIP pairs in Output, move verified unpacked trees into scratch.

    Preserve every byte in both the immutable ZIP and retained scratch tree.
    Source/target stay within the exact owned roots, never delete unknown data.
    This prevents growing restored histories from exhausting provider file pages.
    """
    from safeshift.candidates.train_history import members
    work, scratch = Path(work).resolve(), Path(scratch).resolve()
    require(work == Path(request["work"]).resolve() and scratch == Path(request["scratch"]).resolve()
        and not work.is_relative_to(scratch) and not scratch.is_relative_to(work), "MINICPM_RETENTION_OWNED_ROOTS")
    selected = []
    for i, h in enumerate(request["history"]):
        selected.append((h["run_id"], safe(capsule_directory, f"ancestor-{i:04d}.bin"),
                         (h, ancestors[i]) if ancestors is not None else None))
    run = request["plan"]["run_id"]
    if (work / (run + ".zip")).is_file():
        selected.append((run, safe(work, run + ".zip"), None))
    target_root = safe(scratch, "sealed-output-trees")
    target_root.mkdir(exist_ok=False)
    retained = []
    for name, archive, restored in selected:
        source, target = safe(work, name), safe(target_root, name)
        require(source.is_dir() and not target.exists() and source.resolve().is_relative_to(work)
            and target.resolve().is_relative_to(scratch), "MINICPM_RETENTION_SAFE_TARGET")
        if restored is None:
            expected = ui.pair(archive)
            archive_sha = sha(archive)
            found = members(source); found.pop("checksums.json", None)
            require(found == expected, "MINICPM_RETENTION_ARCHIVE_TREE_CUSTODY")
        else:
            from .runtime import restored_history_members
            item, ancestor = restored
            expected = restored_history_members(source, item, deadline)
            archive_sha = ancestor["sha256"]
        if work.stat().st_dev != scratch.stat().st_dev:
            wanted = sum(p.stat().st_size for p in source.rglob("*") if p.is_file())
            require(shutil.disk_usage(scratch).free >= wanted + request["resource_policy"]["free_scratch_mib"] * 2**20,
                "MINICPM_RETENTION_CROSS_DEVICE_SPACE")
        # shutil.move supports separate scratch/output devices; the sealed ZIP
        # remains in Output even if a cross-device copy fails halfway through.
        shutil.move(str(source), str(target))
        after = members(target); after.pop("checksums.json", None)
        require(after == expected, "MINICPM_RETENTION_MOVED_BYTES")
        retained.append({"run_id":name,"archive_sha256":archive_sha,"members":len(expected),
            "scratch_relative":"sealed-output-trees/"+name})
    return {"status":"SEALED_ZIPS_IN_OUTPUT_RAW_BYTES_RETAINED_IN_SCRATCH", "retained":retained,
        "raw_deleted":False,"observed_unix":time.time(),"output_inventory":"ZIP_PAIRS_AND_SMALL_CONTROL_FILES"}


def child_command(python, mode, request_file, repo, output, deadline):
    c = authority.current()
    require(c is not None and "context_file" in c, "MINICPM_SUPERVISED_CAPABILITY_CONTEXT")
    argv = [str(python), "-B", "-m", "safeshift.fulltrain.minicpm_execution", "--stage", mode,
        "--request", str(request_file), "--repo", str(repo), "--output", str(output), "--deadline", str(deadline),
        "--capability", c["context_file"], "--release-comment-id", str(c["locator"]["comment_id"]),
        "--release-body-sha256", c["locator"]["body_sha256"]]
    if "proof_file" in c:
        argv.extend(("--authority-proof", c["proof_file"]))
    return argv


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=authority.STAGES[1:], required=True)
    for name in ("request", "repo", "output", "capability"):
        p.add_argument("--" + name, required=True, type=Path)
    p.add_argument("--deadline", type=float, required=True)
    p.add_argument("--release-comment-id", type=int, required=True)
    p.add_argument("--release-body-sha256", required=True)
    p.add_argument("--authority-proof", type=Path)
    args = p.parse_args()
    authority_started = time.monotonic()
    locator = {"comment_id": args.release_comment_id, "body_sha256": args.release_body_sha256}
    proof = None
    if args.authority_proof is not None:
        require(snapshot_stat(args.authority_proof).st_size <= authority.PROOF_BYTES,
            "MINICPM_STAGE_AUTHORITY_PROOF_BOUND")
        proof = authority.strict_json(args.authority_proof.read_bytes())
    grant = authority.load(locator, repo=args.repo, child=True, stage_proof=proof)
    context = metadata(args.capability)
    require(set(context) == {"locator", "ticket", "value"} and context["locator"] == locator, "MINICPM_CHILD_CONTEXT")
    request = metadata(args.request, 4 * 2**20)
    require(digest(request) == digest(context["value"]["request"]), "MINICPM_CHILD_REQUEST_PIN")
    if authority.uses_proof(grant):
        directory = args.request.resolve().parent
        require(directory.parent == Path(request["work"]).resolve() / "supervision"
            and args.request.name == "request.json" and args.output.resolve() == directory / args.stage
            and math.isfinite(args.deadline) and time.monotonic() < args.deadline,
            "MINICPM_CHILD_SUPERVISOR_PATH_OR_DEADLINE")
        predecessor = authority.STAGES[authority.STAGES.index(args.stage) - 1]
        if predecessor != "launch":
            receipt = metadata(directory / (predecessor + "-process.json"), 4096)
            prior = metadata(directory / predecessor / "stage.json", 4096)
            require(receipt["schema"] == "fresh-process-supervision-v1" and receipt["status"] == "EXITED"
                and receipt["returncode"] == 0 and receipt["group_exit"]["status"] == "NO_LIVE_MEMBERS"
                and prior == {"status": "RETURNED", "stage": predecessor, "request_sha256": digest(request),
                    "source_sha256": request["source_sha256"], "native_attempt_permitted": False},
                "MINICPM_CHILD_PREDECESSOR_RETURN")
    with authority._activated(grant, locator, context["ticket"], context["value"], args.stage, repo=args.repo, child=True):
        authority.authorize(request=request)
        from .admission import stage
        if "continuation" in grant:
            return stage(args.stage, request, args.repo, args.output, args.deadline,
                authority_seconds=time.monotonic() - authority_started)
        return stage(args.stage, request, args.repo, args.output, args.deadline)


if __name__ == "__main__":
    main()
