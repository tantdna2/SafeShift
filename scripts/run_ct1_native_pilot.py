"""One Kaggle job for CT1. The notebook launches this controller as a subprocess."""

from argparse import ArgumentParser
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time

from safeshift.candidates.source import require
from safeshift.data.saved_reports import json_bytes, sha256, strict_json
from safeshift.evaluation.full_train_benchmark import is_sha256
from safeshift.fulltrain import ct1_native, ct1_run, environment, provision, qwen, supervision
from safeshift.fulltrain.qwen_semantics import fields
from safeshift.pilot.artifacts import export, safe, write, write_bytes

REPO = Path(__file__).resolve().parents[1]
INPUT = Path("/kaggle/input")
WORK = Path("/kaggle/working")
WALL_SECONDS = 3 * 60 * 60
PREFLIGHT_SECONDS = 90 * 60
EXPORT_RESERVE = 120


def mount_path(value, *, directory):
    p = Path(value)
    require(p.is_absolute() and p == p.resolve() and p.is_relative_to(INPUT.resolve())
            and not any(parent.is_symlink() for parent in (p, *p.parents))
            and all("test" != part.casefold() for part in p.parts), "CT1_KAGGLE_PRIVATE_INPUT_PATH")
    require(p.is_dir() if directory else p.is_file(), "CT1_MISSING_INPUT")
    if not directory:
        require(stat.S_ISREG(p.stat().st_mode) and p.stat().st_nlink == 1, "CT1_REGULAR_INPUT_REQUIRED")
    return p


def config(path):
    require(path.is_file() and path.stat().st_size <= 16384, "CT1_CONFIG_SIZE")
    value = strict_json(path.read_bytes())
    required = {"run_id", "mode", "source_commit", "source_capsule_sha256", "pilot_input",
                "plan_sha256", "checkpoint", "software_input", "software_marker_sha256",
                "approved_drivers", "observed_driver", "resume"}
    if isinstance(value, dict) and value.get("mode") == "smoke":
        required.add("operator_request_sha256")
    fields(value, required)
    require(value["mode"] in ("preflight", "pilot", "smoke"), "CT1_MODE")
    commit = value["source_commit"]
    require(isinstance(commit, str) and len(commit) == 40 and all(x in "0123456789abcdef" for x in commit),
            "CT1_EXACT_SOURCE_COMMIT")
    for key in ("source_capsule_sha256", "plan_sha256", "software_marker_sha256"):
        require(is_sha256(value[key]), "CT1_INVALID_SEAL")
    require(ct1_run.RUN_ID.fullmatch(value["run_id"]), "CT1_INVALID_RUN_ID")
    ct1_native.release_budgets(value["approved_drivers"])
    require(all(tuple(map(int, version.split("."))) >= (570, 26)
                for version in value["approved_drivers"]), "CT1_CUDA_128_GA_DRIVER_FLOOR")
    require(value["observed_driver"] in value["approved_drivers"], "CT1_OBSERVED_DRIVER_NOT_APPROVED")
    require(value["run_id"].startswith("ct1-smoke-") == (value["mode"] == "smoke"), "CT1_RUN_SCOPE")
    require(value["resume"] is None, "CT1_CROSS_VM_RESUME_BLOCKED_NO_LATEST_LEDGER_PROOF")
    return value


def require_native_admission(cfg):
    # Smoke uses the sole Operator's durable push intent. Its digest identifies
    # that request, but cannot serve as a remote anti-replay claim.
    if cfg["mode"] == "smoke":
        require(is_sha256(cfg.get("operator_request_sha256")), "CT1_SMOKE_OPERATOR_REQUEST_REQUIRED")
        return
    require(cfg["mode"] == "preflight", "CT1_NATIVE_BLOCKED_NO_TRUSTED_SINGLE_USE_ADMISSION")


def layout(cfg):
    data = mount_path(cfg["pilot_input"], directory=True)
    software = mount_path(cfg["software_input"], directory=True)
    marker = safe(software, "fresh_qwen_software.json")
    lock = strict_json(ct1_run.read_sealed(marker, cfg["software_marker_sha256"], 2**20))["runtime_lock"]
    checkpoint = mount_path(cfg["checkpoint"], directory=True)
    require(checkpoint.name == ct1_run.REVISION, "CT1_CHECKPOINT_REVISION_DIR")
    require(len({data, software, checkpoint}) == 3
            and not any(a.is_relative_to(b) for a in (data, software, checkpoint)
                        for b in (data, software, checkpoint) if a != b), "CT1_INPUT_ROLES_MUST_BE_SEPARATE")
    plan, _ = ct1_run.admit(data, cfg["plan_sha256"])
    if cfg["mode"] == "smoke":
        plan = {**plan, "cases": plan["cases"][:1]}
    return data, software, checkpoint, lock, plan


def binding(cfg, lock):
    source = sha256(json_bytes({"commit": cfg["source_commit"], "drivers": cfg["approved_drivers"],
                               "observed_driver": cfg["observed_driver"],
                               "runtime_lock": lock, "shared_max_new_tokens": ct1_native.MAX_NEW,
                               "max_input_tokens": ct1_native.MAX_INPUT, "checkpoint": qwen.reference(REPO)["model"]}))
    state = ct1_run.identity(cfg["plan_sha256"], source, cfg["source_capsule_sha256"],
                             cfg["software_marker_sha256"], cfg["run_id"], smoke=cfg.get("mode") == "smoke")
    if cfg.get("mode") == "smoke":
        state["operator_request_sha256"] = cfg["operator_request_sha256"]
    return state


def worker(args):
    cfg = config(args.config)
    require_native_admission(cfg)
    deadline = args.deadline
    root, scratch = args.job / "evidence", args.scratch
    data, software, checkpoint, lock, plan = layout(cfg)
    drivers = [cfg["observed_driver"]]
    budgets = ct1_native.release_budgets(drivers)
    if args.command == "setup":
        write(root / "before-setup.json", {
            "resources": environment.resources("qwen3", budgets, scratch, args.job),
            "physical": environment.hardware("qwen3", budgets), "native_calls": 0})
        python, _ = provision.prepare({"model_key": "qwen3", "scratch": str(scratch),
                                      "software_input": str(software), "software_marker_sha256":
                                      cfg["software_marker_sha256"], "runtime_lock": lock},
                                     REPO, args.job / "setup", deadline)
        require(python == scratch / "qwen-software/venv/bin/python", "CT1_RUNTIME_PATH")
        return
    current = ct1_native.preflight(checkpoint, REPO, lock, drivers, scratch, args.job, data, plan)
    write(root / "preflight.json", current)
    if cfg["mode"] == "preflight":
        return
    state = binding(cfg, lock)
    require(state == strict_json((root / "identity.json").read_bytes()), "CT1_RUNTIME_IDENTITY_CHANGED")
    require(strict_json((root / "resume-admission.json").read_bytes()) == {"status": "FRESH_ADMITTED"}
            and not (root / "calls").exists(), "CT1_FRESH_LEDGER_REQUIRED")
    backend = ct1_native.Backend(checkpoint, REPO)
    write(root / "model-loaded.json", {"weights_loaded": True, "device_map": qwen.DEVICE_MAP,
                                      "generation": backend.config.to_dict(),
                                      "memory": backend.failure_memory()})
    ct1_run.execute(root, plan, state, data / "images", backend, deadline)


def diagnostic_path(archive):
    return archive.with_name(archive.stem + "-diagnostic.zip")


def publish_export(root, archive):
    # Export and verify under the job directory. Publish the ZIP name last,
    # so an interruption cannot leave an ordinary result ZIP without its seal.
    staging = root.parent / "export-stage"
    staging.mkdir()
    staged_zip = staging / (archive.name + ".pending")
    export(root, staged_zip)
    staged_seal = staging / (staged_zip.name + ".sha256.json")
    os.link(staged_seal, archive.with_name(archive.name + ".sha256.json"))
    os.link(staged_zip, archive)
    staged_zip.unlink()
    staged_seal.unlink()


def export_diagnostic(root, archive, reason, *, ledger_stable=False):
    evidence = root
    omitted = []
    if not ledger_stable:
        # The worker may still be writing. Copy only bounded controller
        # records without examining the ledger, logs or worker output.
        evidence = root.parent / "diagnostic"
        evidence.mkdir()
        records = ("identity.json", "config-summary.json", "controller-failure.json", *ct1_run.PROCESS_RECEIPTS)
        for name in records:
            try:
                data = ct1_run.read_controller_record(root, name)
            except (ValueError, OSError):
                omitted.append(name)
                continue
            write_bytes(evidence / name, data)
    write(evidence / "diagnostic-status.json", {"status": "FORENSIC_ONLY",
          "reason": reason, "ledger_stable": ledger_stable, "resumable": False,
          "budget_release": False, "omitted_controller_records": omitted,
          "live_evidence": "PRESERVED_IN_PLACE" if not ledger_stable else "STOPPED_LEDGER_RETAINED"})
    publish_export(evidence, diagnostic_path(archive))


def export_job(root, archive, plan, state, mode):
    try:
        stable = ct1_run.stable_journal(root)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        export_diagnostic(root, archive, str(exc)[:2000])
        return "FORENSIC_ONLY"
    write(root / "checkpoint-stability.json", stable)
    if mode in ("pilot", "smoke"):
        try:
            require((root / "resume-admission.json").is_file(), "CT1_RESULT_ADMISSION_MISSING")
            ct1_run.reconstruct(root, plan, state, smoke=mode == "smoke")
        except (ValueError, KeyError, TypeError, OSError) as exc:
            write(root / "journal-export-failure.json",
                  {"status": "FORENSIC_ONLY", "type": type(exc).__name__, "message": str(exc)[:2000]})
            export_diagnostic(root, archive, str(exc)[:2000], ledger_stable=True)
            return "FORENSIC_ONLY"
    publish_export(root, archive)
    return "PROCESS_EXITED"


def supervise(args):
    cfg = config(args.config)
    require_native_admission(cfg)
    require(sys.platform == "linux" and WORK.is_dir() and args.job.parent == WORK
            and args.job.name == cfg["run_id"], "CT1_EXACT_KAGGLE_JOB_ROOT")
    deadline = time.monotonic() + (WALL_SECONDS if cfg["mode"] == "pilot" else PREFLIGHT_SECONDS)
    data, software, checkpoint, lock, plan = layout(cfg)
    budgets = ct1_native.release_budgets([cfg["observed_driver"]])
    state = binding(cfg, lock)
    root = args.job / "evidence"
    archive = WORK / (cfg["run_id"] + ".zip")
    diagnostic = diagnostic_path(archive)
    require(not any(p.exists() or Path(str(p) + ".sha256.json").exists() for p in (archive, diagnostic)),
            "CT1_EXPORT_ALREADY_PRESENT")
    args.job.mkdir(exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix=cfg["run_id"] + "-", dir="/tmp"))
    for sub in (root, args.job / "setup"):
        sub.mkdir()
    write(root / "identity.json", state)
    write(root / "config-summary.json", {"mode": cfg["mode"], "source_commit": cfg["source_commit"],
                                        "limits": budgets, "max_calls": state["max_calls"],
                                        "cross_vm_resume": "BLOCKED_NO_LATEST_LEDGER_PROOF"})
    env = provision.clean_env(REPO, scratch)
    env.update(PYTORCH_ALLOC_CONF="expandable_segments:True", CUDA_VISIBLE_DEVICES="0,1",
               TMP=str(scratch), TEMP=str(scratch), OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
    setup_cutoff = min(deadline - EXPORT_RESERVE, time.monotonic() + budgets["setup_seconds"])
    try:
        if cfg["mode"] != "preflight":
            write(root / "resume-admission.json", {"status": "FRESH_ADMITTED"})
        args_common = ["--config", str(args.config), "--job", str(args.job), "--scratch", str(scratch)]
        def launch(phase, python, cutoff, phase_env):
            command = [str(python), "-B", "-m", "scripts.run_ct1_native_pilot", phase,
                       *args_common, "--deadline", str(cutoff)]
            receipt = root / (phase + "-supervisor.json")
            report = supervision.run(command, cwd=REPO, env=phase_env, deadline=cutoff,
                log=root / (phase + ".log"), receipt=receipt,
                max_log_bytes=budgets["max_log_bytes"], watch_log_root=args.job / "setup")
            require(report["status"] == "EXITED" and report["returncode"] == 0
                    and supervision.process_group_closed(strict_json(ct1_run.read_controller_record(
                        root, receipt.name))),
                    "CT1_" + phase.upper() + "_SUPERVISOR_FAILED")

        launch("setup", sys.executable, setup_cutoff, env)
        venv = scratch / "qwen-software/venv"
        python = venv / "bin/python"
        env.update(SAFESHIFT_WORKER_PYTHON=str(python), SAFESHIFT_RUNTIME_ROOT=str(venv))
        native_cutoff = deadline - EXPORT_RESERVE
        if cfg["mode"] == "preflight":
            native_cutoff = min(native_cutoff, time.monotonic() + budgets["diagnostic_seconds"])
        launch("worker", python, native_cutoff, env)
    except (ValueError, OSError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
        write(root / "controller-failure.json", {"type": type(exc).__name__,
              "message": str(exc)[:2000], "automatic_retry": False, "status": "PARTIAL_OR_BLOCKED"})
        # Return with an export for controlled failure, so it is retained by the
        # notebook versioner. The receipt and summary carry the actual status.
    finally:
        with supervision.parent_deadline(deadline, "ct1_export"):
            outcome = export_job(root, archive, plan, state, cfg["mode"])
    failure = any((root / name).exists()
                  for name in ("controller-failure.json", "journal-export-failure.json"))
    if outcome == "FORENSIC_ONLY":
        print("FORENSIC_ONLY", diagnostic_path(archive))
    else:
        print("PARTIAL_OR_BLOCKED" if failure else outcome, archive)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("supervise", "setup", "worker"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--deadline", type=float)
    parser.add_argument("--scratch", type=Path)
    args = parser.parse_args()
    if args.command == "supervise":
        supervise(args)
    else:
        require(args.scratch is not None and args.scratch.is_dir() and args.deadline is not None
                and args.deadline > time.monotonic(), "CT1_EXPIRED_STAGE")
        worker(args)


if __name__ == "__main__":
    main()
