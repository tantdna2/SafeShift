"""Prepared final-source setup/diagnostic/native pipeline, public routes fenced.

Internal functions compose reviewed checks and are exercised with synthetic
boundaries. A later reviewed activation must authenticate O2-O6 before calling
them; a request JSON is a binding record, never an approval or authority token.
"""
import argparse
from copy import deepcopy
import os
from pathlib import Path
import sys
import time
import uuid

from safeshift.candidates.source import ROOT, require, verify_snapshot
from safeshift.candidates.loading import verify_weights
from safeshift.candidates.train_inputs import checkpoint
from safeshift.candidates.train_history import lease_key
from safeshift.candidates.train_runtime import verify_images
from safeshift.pilot.artifacts import read, sha, write, export, safe
from safeshift.pilot.contract import digest, require_hash
from safeshift.pilot.runner import error_record
from . import contract, environment, supervision, provision, inputs, runtime

REQUEST_FIELDS = {"model_key", "source_sha256", "inputs", "marker_sha256", "projection_sha256",
    "campaign", "plan", "history", "work", "scratch", "resource_policy", "repair_case",
    "checkpoint_marker_sha256", "runtime_lock", "runtime_lock_sha256", "software_input", "software_marker_sha256"}
ORIGINAL_REQUEST_FIELDS = REQUEST_FIELDS | {"original_inputs"}


def validate_request(request, repo=ROOT):
    require(type(request) is dict and set(request) in (REQUEST_FIELDS, ORIGINAL_REQUEST_FIELDS), "FRESH_SUPERVISED_REQUEST_FIELDS")
    key = request["model_key"]
    environment.policy(key, request["resource_policy"])
    require(request["source_sha256"] == digest(contract.source_manifest(repo)), "FRESH_FINAL_SOURCE")
    require(request["plan"]["identity"] == contract.native_identity(key, repo), "FRESH_NATIVE_IDENTITY")
    require(request["plan"]["history_sha256"] == digest(request["history"]), "FRESH_HISTORY_BINDING")
    for name in ("marker_sha256", "projection_sha256", "checkpoint_marker_sha256"):
        require_hash(request[name])
    runtime.check_repair_case(request["plan"], request["repair_case"])
    require(request["campaign"]["cohort_sha256"] == request["projection_sha256"], "FRESH_PROJECTION_PIN")
    if "original_inputs" in request:
        require(key == "minicpm4", "ORIGINAL_MOUNTS_MINICPM_ONLY")
        from .original_inputs import validate_binding
        validate_binding(request["original_inputs"], request["marker_sha256"], request["projection_sha256"])
    for name in ("work", "scratch", "inputs"):
        path = Path(request[name])
        require(not any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
                        for p in (path, *path.parents)), "FRESH_ROOT_ALIAS")
    work, scratch, source = (Path(request[n]).resolve() for n in ("work", "scratch", "inputs"))
    require(not (work == scratch or work.is_relative_to(scratch) or scratch.is_relative_to(work)), "SEPARATE_SCRATCH_OUTPUT_ROOTS")
    require(not any(p == source or p.is_relative_to(source) or source.is_relative_to(p) for p in (work, scratch)), "INPUT_READ_ONLY_ROOT")
    if key == "qwen3":
        require(request["runtime_lock"] is not None and digest(request["runtime_lock"]) == request["runtime_lock_sha256"],
                "QWEN_CLOSED_SOFTWARE_LOCK_MISSING_OR_CHANGED")
        require_hash(request["software_marker_sha256"])
        require(isinstance(request["software_input"], str) and request["software_input"], "QWEN_OFFLINE_SOFTWARE_INPUT_REQUIRED")
        path = Path(request["software_input"])
        require(not any(v.is_symlink() or (hasattr(v, "is_junction") and v.is_junction())
                        for v in (path, *path.parents)), "QWEN_SOFTWARE_INPUT_ALIAS")
        software = path.resolve()
        require(not any(software == p or software.is_relative_to(p) or p.is_relative_to(software)
                        for p in (work, scratch)), "SOFTWARE_INPUT_READ_ONLY_ROOT")
    else:
        require(all(request[n] is None for n in ("runtime_lock", "runtime_lock_sha256", "software_input", "software_marker_sha256")),
                "PEER_USES_EXISTING_PINNED_RUNTIME")
    return request


def checkpoint_binding(request, repo=ROOT):
    key = request["model_key"]
    if key == "qwen3":
        from . import qwen
        marker, snapshot, receipt = qwen.checkpoint(request["inputs"], request["checkpoint_marker_sha256"], repo)
        return marker, snapshot, snapshot, receipt
    marker, snapshot, weights = checkpoint(request["inputs"], key)
    require(sha(marker) == request["checkpoint_marker_sha256"], "FRESH_CHECKPOINT_MARKER_PIN")
    source = verify_snapshot(snapshot, key)
    weights_receipt = verify_weights(weights, key)
    return marker, snapshot, weights, {"source": source, "weights": weights_receipt}


def input_binding(request):
    if "original_inputs" in request:
        from .original_inputs import admit as original
        return original(request["inputs"], request["original_inputs"], request["marker_sha256"], request["projection_sha256"])
    return inputs.admit(request["inputs"], request["marker_sha256"], request["projection_sha256"])


def input_bytes(request, bundle, cohort, rows):
    if "original_inputs" in request:
        from .original_inputs import verify_bytes
        return verify_bytes(bundle, cohort, rows)
    return inputs.verify_image_bytes(bundle, cohort, rows)


def admit(request, repo=ROOT):
    validate_request(request, repo)
    history_admission(request)
    if request["model_key"] == "qwen3":
        provision.software_input(request["software_input"], request["software_marker_sha256"], request["runtime_lock"], repo)
    bundle, cohort, rows = input_binding(request)
    p = request["plan"]
    require(p == contract.plan(request["campaign"], cohort, p["identity"], request["history"], action=p["action"],
        run_id=p["run_id"], attempt_id=p["attempt_id"], max_calls=p["max_calls"], max_seconds=p["max_seconds"], repair=p["repair"]),
        "ADMISSION_PLAN_RECOMPUTE")
    for old in request["history"]:
        root = safe(request["work"], old["run_id"])
        require(runtime.recover(root, cohort, digest(read(root / "plan.json"))) == old, "ADMISSION_HISTORY_CUSTODY")
    input_bytes(request, bundle, cohort, rows)
    marker, snapshot, weights, receipt = checkpoint_binding(request, repo)
    return bundle, cohort, rows, snapshot, weights, receipt


def history_admission(request):
    """Unknown attempts/output block before provisioning, GPU or private image IO."""
    work = Path(request["work"])
    history = request["history"]
    known = {h["attempt_id"] + ".json" for h in history}
    lock = "active_" + digest({"campaign": request["campaign"], "model": request["model_key"]}) + ".lock"
    attempts = work / "attempts"
    if attempts.exists():
        names = {p.name for p in attempts.iterdir()}
        require(names in (known, known | {lock}), "UNKNOWN_RESERVATION_BEFORE_SETUP")
        for h in history:
            value = read(safe(attempts, h["attempt_id"] + ".json"))
            require(value == {"plan_sha256": digest(read(safe(work, h["run_id"] + "/plan.json"))),
                             "campaign_sha256": digest(request["campaign"])}, "RESERVATION_CUSTODY_BEFORE_SETUP")
    else:
        require(not history, "HISTORY_RESERVATIONS_MISSING_BEFORE_SETUP")
    if (work / "campaign.json").exists():
        require(read(work / "campaign.json") == request["campaign"], "WORKSPACE_CAMPAIGN_BEFORE_SETUP")
    elif history:
        raise ValueError("WORKSPACE_CAMPAIGN_MISSING")
    allowed = {"attempts", "campaign.json", "supervision", "supervisor_control"}
    for h in history:
        allowed.update((h["run_id"], h["run_id"] + ".zip", h["run_id"] + ".zip.sha256.json"))
    if work.exists():
        for i, path in enumerate(work.iterdir()):
            require(i < len(allowed) and path.name in allowed, "UNKNOWN_OUTPUT_BEFORE_SETUP")


def stage(mode, request, repo, output, deadline):
    """Actual child implementation. Public CLI calls authorize BEFORE reading JSON."""
    validate_request(request, repo)
    require(time.monotonic() < deadline, "STAGE_DEADLINE_EXPIRED")
    output = Path(output)
    output.mkdir(exist_ok=False)
    try:
        if mode == "setup":
            admit(request, repo)  # all Input/checkpoint admission before package activity
            environment.resources(request["model_key"], request["resource_policy"], request["scratch"], request["work"])
            from .preflight import storage_probe
            budgets = request["resource_policy"]
            write(output / "allocation.json", storage_probe(request["scratch"], request["work"],
                scratch_bytes=budgets["scratch_probe_bytes"], output_bytes=budgets["output_probe_bytes"]))
            provision.prepare(request, repo, output, deadline)
        else:
            bundle, cohort, rows, snapshot, weights, checkpoint_receipt = admit(request, repo)
            write(output / "checkpoint.json", checkpoint_receipt)
            if mode == "cpu":
                require(os.environ.get("CUDA_VISIBLE_DEVICES") == "", "CPU_STAGE_HIDDEN_CUDA")
            if mode != "admit":
                write(output / "software.json", environment.software(request["model_key"], repo, request["runtime_lock"]))
            write(output / "resources.json", environment.resources(request["model_key"], request["resource_policy"],
                                                                    request["scratch"], request["work"]))
            if mode == "admit":
                pass  # bounded byte/hash/history admission before setup or no-op
            elif mode == "cpu":
                require(os.environ.get("CUDA_VISIBLE_DEVICES") == "", "CPU_STAGE_HIDDEN_CUDA")
                if "original_inputs" in request:
                    from .original_inputs import verify_images as original_images
                    write(output / "images.json", original_images(bundle, cohort, rows))
                else:
                    write(output / "images.json", verify_images(bundle, rows))
                from .preflight import cpu_native_checks
                write(output / "native_cpu.json", cpu_native_checks(request["model_key"], snapshot, repo,
                      wheel_lock=request["runtime_lock"]))
            elif mode in ("gpu", "native"):
                write(output / "physical_gpu.json", environment.hardware(request["model_key"], request["resource_policy"]))
                write(output / "worker_cuda.json", environment.cuda(request["model_key"], request["resource_policy"]))
                if mode == "native":
                    # Parent and every child recheck source/input/checkpoint/plan.
                    # Controller alone creates the immutable attempt reservation.
                    result = runtime._worker(request, repo=repo)
                    require(read(result / "receipt.json")["stop"] is None
                            and not (result / "accounting_failure.json").exists(), "NATIVE_ATTEMPT_STOPPED_REVIEW_EVIDENCE")
            else:
                raise ValueError("UNKNOWN_FRESH_STAGE")
        write(output / "stage.json", {"status": "RETURNED", "stage": mode, "request_sha256": digest(request),
            "source_sha256": request["source_sha256"], "native_attempt_permitted": mode == "native"})
    except BaseException as error:
        write(output / "failure.json", error_record(error, mode))
        raise


def command(python, mode, request_file, repo, output, deadline):
    return [str(python), "-B", "-m", "safeshift.fulltrain.admission", "--stage", mode,
            "--request", str(request_file), "--repo", str(repo), "--output", str(output), "--deadline", str(deadline)]


def launch_prepared(request, *, repo=ROOT, diagnostic=False):
    """Future authorized orchestrator. Never call this instead of public launch.

    Entire setup/admission/GPU/native pipeline runs in killed-on-timeout process
    groups. No retry loop; timeout retains unknown/partial evidence for custody.
    """
    validate_request(request, repo)
    request = deepcopy(request)
    for name in ("inputs", "work", "scratch"):
        request[name] = str(Path(request[name]).resolve())
    if request["software_input"] is not None:
        request["software_input"] = str(Path(request["software_input"]).resolve())
    repo, work, scratch = Path(repo).resolve(), Path(request["work"]), Path(request["scratch"])
    require(scratch.is_dir() and not any(scratch.iterdir()), "FRESH_EMPTY_OWNED_SCRATCH_REQUIRED")
    work.mkdir(parents=True, exist_ok=True)
    output = work / "supervision" / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    request_file = output / "request.json"
    write(request_file, request)
    p, budgets = request["plan"], request["resource_policy"]
    deadline = time.monotonic() + p["max_seconds"]
    python, env = sys.executable, provision.clean_env(repo, scratch)
    stage_name, failure = "setup", None
    control = work / "supervisor_control"
    control.mkdir(exist_ok=True)
    key = digest({"campaign": request["campaign"], "model": request["model_key"]})
    try:
        with lease_key(control, key) as lock_options:
            # Allocation is also supervised, inside setup child (see below),
            # so quota stalls cannot hang the notebook outside the deadline.
            modes = ("admit",) + (("setup", "cpu", "gpu") + (() if diagnostic else ("native",))
                                   if p["scheduled_ordinals"] or diagnostic else ())
            for mode in modes:
                stage_name = mode
                limit = budgets["setup_seconds"] if mode == "setup" else budgets["diagnostic_seconds"] if mode != "native" else p["max_seconds"]
                until = min(deadline, time.monotonic() + limit)
                if mode in ("gpu", "native"):
                    env["CUDA_VISIBLE_DEVICES"] = "0,1" if request["model_key"] == "qwen3" else "0"
                supervision.run(command(python, mode, request_file, repo, output / mode, until),
                    cwd=repo, env=env, deadline=until, log=output / (mode + ".log"),
                    receipt=output / (mode + "-process.json"), max_log_bytes=budgets["max_log_bytes"],
                    watch_log_root=output / mode, **lock_options)
                proof = read(output / mode / "stage.json")
                require(proof == {"status": "RETURNED", "stage": mode, "request_sha256": digest(request),
                    "source_sha256": request["source_sha256"], "native_attempt_permitted": mode == "native"}, "CHILD_STAGE_BINDING")
                if mode == "setup":
                    installed = read(output / "setup/runtime.json")
                    require(installed["request_sha256"] == digest(request), "SETUP_RUNTIME_BINDING")
                    python, env = installed["python"], installed["env"]
                    require(Path(python).resolve().is_relative_to(scratch.resolve()) and env["CUDA_VISIBLE_DEVICES"] == "", "SETUP_ISOLATED_PYTHON")
    except BaseException as error:
        failure = error_record(error, stage_name)
        write(output / "failure.json", failure)
    finally:
        attempt = safe(work, p["run_id"])
        recovery = "NO_ATTEMPT"
        if attempt.exists():
            recovery = "PARTIAL_OR_SEALED_REQUIRES_CUSTODY"
            archive = Path(str(attempt) + ".zip")
            if not archive.exists() and not (attempt / "checksums.json").exists():
                try:
                    export(attempt, archive)
                    recovery = "PARTIAL_EVIDENCE_SEALED_NOT_RETRIED"
                except BaseException as error:
                    write(output / "partial_export_failure.json", error_record(error, "partial_export"))
        write(output / "release.json", {"status": "BLOCKED" if failure else "TECHNICAL_STAGES_RETURNED_NOT_RELEASE_AUTHORITY",
            "diagnostic": diagnostic, "last_stage": stage_name, "failure": failure,
            "attempt_observed": attempt.exists(), "recovery": recovery, "automatic_retry": False,
            "scientific_qualified": False, "source_sha256": request["source_sha256"],
            "scratch_retained": True, "cleanup": "OWNER_INSPECTION_REQUIRED_NO_RECURSIVE_DELETE"})
        export(output, Path(str(output) + ".zip"))
    return output


def main():
    contract.authorize()  # before argparse, request/private I/O or CUDA imports
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("admit", "setup", "cpu", "gpu", "native"), required=True)
    for name in ("request", "repo", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--deadline", type=float, required=True)
    args = parser.parse_args()
    return stage(args.stage, read(args.request), args.repo, args.output, args.deadline)


if __name__ == "__main__":
    main()
