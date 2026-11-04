"""Released, supervised PR177 notebook/worker entrypoint. No submission code."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import threading
import time
import zipfile

from safeshift import internvl_v2_campaign as control, internvl_v2_runtime as runtime
from safeshift.candidates.source import ROOT, require
from safeshift.candidates.train_inputs import discover
from safeshift.candidates.fulltrain import cohort
from safeshift.fulltrain import provision, supervision, environment
from safeshift.pilot.artifacts import read, write, sha, safe, export, verify_archive
from safeshift.pilot.contract import digest
from scripts.verify_kaggle173_inputs import unique_mount
from scripts import internvl_v2 as engine


def original_metadata(inputs, spec):
    """Exact hashed master + original smoke identity; never opens an image/GT file.

    Only identity fields are projected from the sealed prior raw record. No label,
    prediction, generated tokens or scores enter this new experiment.
    """
    master = discover(inputs, "master_manifest.json").read_bytes()
    archive = safe(unique_mount(inputs, "safeshift-issue173-native-smoke-v5"), "issue173-smoke-20261102-v5.zip")
    return original_recipe(master, archive, spec)


def original_recipe(master, archive, spec):
    """Shared local preparation/worker identity projection; image bytes excluded."""
    first = cohort(master)["samples"][0]
    locator = json.loads(master)["samples"][0]["image_locator"]
    require(sha(archive) == control.ORIGINAL_ARCHIVE, "ORIGINAL_SMOKE_SEAL")
    verify_archive(archive)
    with zipfile.ZipFile(archive) as bundle:
        prior = json.loads(bundle.read("internvl35/sample/raw.json"))["smoke_identity"]
    require(all(prior[key] == first[key] for key in ("ordinal", "sample_id", "image_sha256")),
            "ORIGINAL_SMOKE_IDENTITY")
    recipe = {"schema": control.CAMPAIGN + "-request", "source_sha256": digest(spec),
        "master_sha256": control.MASTER_SHA, "original_archive_sha256": control.ORIGINAL_ARCHIVE,
        "ordinal": 0, "sample_id_sha256": digest(first["sample_id"]),
        "image_locator_sha256": digest(locator), "image_sha256": first["image_sha256"]}
    control.validate_request(recipe)
    return recipe, first, locator


def native_request(inputs, spec, recipe):
    observed, first, locator = original_metadata(inputs, spec)
    require(observed == recipe, "EXACT_ORIGINAL_REQUEST")
    image = safe(unique_mount(inputs, "inspecsafe-v1-kaggle"), "InspecSafe-V1-Kaggle/train/" + locator)
    require(sha(image) == recipe["image_sha256"], "ORIGINAL_IMAGE_SHA256")
    request = {"schema": runtime.IDENTITY + "-request", "identity": runtime.IDENTITY,
        "series_id": runtime.SERIES, "attempt_id": "attempt-0001", "split": "TRAIN", **first,
        "image": image.relative_to(Path(inputs)).as_posix(), "source_sha256": digest(spec), "limits": runtime.LIMITS}
    runtime.request_binding(spec, request)
    return request


def relay(path, stop):
    """Forward only bounded nonce challenges; full child logs stay private."""
    position, pending = 0, b""
    while not stop.wait(.1):
        if not path.is_file():
            continue
        with path.open("rb") as stream:
            stream.seek(position)
            chunk = stream.read(65536)
            position = stream.tell()
        pending += chunk
        lines = pending.split(b"\n")
        pending = lines.pop()
        for line in lines:
            if line.startswith(control.PREFIX.encode()) and len(line) <= 4096:
                print(line.decode("utf8"), flush=True)
        require(len(pending) <= 2**20, "RELAY_LINE_BOUND")


def worker(stage, packet, out, scratch, inputs, deadline):
    value = read(packet)
    spec = value["spec"]
    ctx = control.context(spec, value["runtime_commit"], value["slot"])
    previous = "launch" if stage == "setup" else "setup"
    parent = read(out / (previous + "-permit.json"))
    require(parent == control.remote_record(previous, value["slot"]), "PARENT_PERMIT_BINDING")
    permission = control.permit(ctx, stage, parent["nonce"])
    write(out / (stage + "-permit.json"), permission)
    if stage == "setup":
        return engine.worker("setup", spec, out, scratch, inputs)
    recipe, _, _ = original_metadata(inputs, spec)
    require(recipe == ctx["grant"]["request"], "REVIEWED_ORIGINAL_METADATA")
    write(out / "original-binding.json", recipe)
    if ctx["grant"]["mode"] == "native":
        request = native_request(inputs, spec, recipe)
        write(out / "execution-request.json", request)
        control.activate_worker(ctx, spec, permission, out)
        return engine.worker("native", spec, out, scratch, inputs, out / "execution-request.json", deadline)
    return engine.worker("preflight", spec, out, scratch, inputs)


def launch(spec, runtime_commit, *, output=Path("/kaggle/working"), scratch_parent=Path("/kaggle/temp"),
           inputs=Path("/kaggle/input")):
    ctx = control.context(spec, runtime_commit)  # Before Input, CUDA, scratch or load.
    grant = ctx["grant"]
    identity = control.job(grant["slot"]).split("/")[1]
    out, scratch = Path(output) / identity, Path(scratch_parent) / identity
    out.mkdir(parents=True, exist_ok=False)
    deadline = min(time.monotonic() + 1750, time.monotonic() + grant["expires_unix"] - time.time() - 30)
    error = None
    write(out / "source.json", spec)
    write(out / "release.json", ctx)
    # A positive local ledger is created before any subprocess. Missing != zero.
    write(out / "campaign-start.json", {"binding": ctx["binding"], "slot": grant["slot"],
        "mode": grant["mode"], "native_calls_at_start": 0, "loads_at_start": 0})
    try:
        permission = control.permit(ctx, "launch", "")
        write(out / "launch-permit.json", permission)
        scratch.mkdir(parents=True, exist_ok=False)
        budgets = engine.policy()
        write(out / "initial-resources.json", environment.resources("internvl35", budgets, scratch, out))
        packet = out / "packet.json"
        write(packet, {"spec": spec, "runtime_commit": runtime_commit, "slot": grant["slot"]})
        env = provision.clean_env(ROOT, scratch)
        for stage in ("setup", "worker"):
            python = sys.executable
            if stage == "worker":
                prepared = read(out / "runtime.json")
                python, env = prepared["python"], prepared["env"]
                env["CUDA_VISIBLE_DEVICES"] = "0"
            log = out / (stage + "-supervisor.log")
            stop = threading.Event()
            thread = threading.Thread(target=relay, args=(log, stop), daemon=True)
            thread.start()
            try:
                supervision.run([str(python), "-B", "-m", "scripts.internvl_v2_campaign",
                    "--worker", stage, "--packet", str(packet), "--output", str(out),
                    "--scratch", str(scratch), "--inputs", str(inputs), "--deadline", str(deadline)],
                    cwd=ROOT, env=env, deadline=min(deadline, time.monotonic() + budgets[
                        "setup_seconds" if stage == "setup" else "diagnostic_seconds"]),
                    log=log, receipt=out / (stage + "-supervisor.json"),
                    max_log_bytes=budgets["max_log_bytes"], watch_log_root=out)
            finally:
                stop.set()
                thread.join(timeout=1)
        require((out / ("sample/result.json" if grant["mode"] == "native" else "preflight.json")).is_file(),
                "MISSING_TERMINAL_WORKER_RESULT")
    except BaseException as failure:
        error = {"type": type(failure).__name__, "message_sha256": hashlib.sha256(str(failure).encode()).hexdigest()}
    result = runtime.summary(out, error) if grant["mode"] == "native" else {
        "status": "TECHNICAL_ERROR" if error else "LIVE_GPU_PREFLIGHT_PASS", "error": error,
        "load_reservations": 0, "weights_loaded": False, "call_reservations": 0, "native_call_markers": 0}
    result.update(campaign=control.CAMPAIGN, slot=grant["slot"], binding=ctx["binding"],
                  mode=grant["mode"], scientific_qualified=False, automatic_retry=False)
    write(out / "summary.json", result)
    # Explicit final ledger, even on a caught failure. Hard kill/failed export is UNKNOWN.
    write(out / "campaign-end.json", {"binding": ctx["binding"], "native_call_markers": result["native_call_markers"],
        "call_reservations": result["call_reservations"], "weights_loaded": result["weights_loaded"],
        "load_permit": (out / "load-permit.json").exists(), "call_permit": (out / "call-permit.json").exists()})
    checksum = export(out, Path(str(out) + ".zip"))
    return {"status": result["status"], "archive_sha256": checksum, "slot": grant["slot"],
            "weights_loaded": result["weights_loaded"], "native_call_markers": result["native_call_markers"]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--worker", choices=("setup", "worker"), required=True)
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--deadline", type=float, required=True)
    a = p.parse_args(argv)
    worker(a.worker, a.packet, a.output, a.scratch, a.inputs, a.deadline)


if __name__ == "__main__":
    main()
