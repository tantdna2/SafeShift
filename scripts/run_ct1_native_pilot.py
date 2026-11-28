"""One Kaggle job for CT1. The notebook launches this controller as a subprocess."""

from argparse import ArgumentParser
from contextlib import contextmanager
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from threading import Event, Thread
import time

from safeshift.candidates.source import require, snapshot_stat
from safeshift.data.saved_reports import json_bytes, sha256, strict_json
from safeshift.evaluation.full_train_benchmark import is_sha256
from safeshift.fulltrain import ct1_native, ct1_run, environment, gpu_driver, memory, provision, qwen, supervision
from safeshift.fulltrain.qwen_semantics import fields
from safeshift.pilot.artifacts import export, safe, write, write_bytes

REPO = Path(__file__).resolve().parents[1]
INPUT = Path("/kaggle/input")
WORK = Path("/kaggle/working")
WALL_SECONDS = 3 * 60 * 60
PREFLIGHT_SECONDS = 90 * 60
EXPORT_RESERVE = 120
WORKER_TELEMETRY_RESERVE = 5
LOAD_SAMPLE_LIMIT = 48
WORKER_MEMORY = "controller-worker-memory.json"
CONTROLLER_MEMORY = ("controller-before-setup-memory.json", "controller-after-setup-memory.json",
                     "controller-before-probe-memory.json", "controller-after-probe-memory.json",
                     "controller-before-worker-memory.json", WORKER_MEMORY)
SETUP_MEMORY = (
    "entry", "archives-restored", "sources-extracted", "zlib-configure-exit", "zlib-make-exit",
    "zlib-install-exit", "python-configure-exit", "python-make-exit", "python-install-exit",
    "venv-exit", "pip-bootstrap-exit", "offline-install-exit", "pip-check-exit", "exit",
)


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
    marker = safe(software, ct1_run.SOFTWARE_MARKER)
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


def require_closed_phase(root, phase):
    process = strict_json(ct1_run.read_controller_record(root, phase + "-supervisor.json"))
    require(supervision.process_group_closed(process) and process["status"] == "EXITED",
            "CT1_DEPENDENCY_GROUP_UNVERIFIED:" + phase)


def reclaim_setup(root, scratch, deadline, *, label="setup"):
    require_closed_phase(root, label)
    owned = strict_json(ct1_run.read_controller_record(root, "scratch-ownership.json"))
    memory.observe(root, label + "-reclaim-before")
    try:
        # Bounded inside the supervised worker so slow fsync cannot consume the export reserve.
        report = memory.advise_ct1_setup(scratch, owned, deadline=deadline)
    except (OSError, ValueError, TimeoutError) as error:
        report = {"status": "ADVICE_FAILED", "type": type(error).__name__,
                  "message": str(error)[:300], "effect": "ADVISORY_NOT_RAM_PROOF"}
    finally:
        memory.observe(root, label + "-reclaim-after")
    write(root / (label + "-cache-advice.json"), report)


@contextmanager
def observe_worker_load(root, *, cutoff=None):
    """Keep sampling I/O out of the hard supervisor and result directories."""
    finished = Event()
    observations = {"load_samples": []}
    result = {}

    def snapshot():
        raw = memory.snapshot()
        cgroup = raw["cgroup"]
        stat = cgroup.get("memory.stat", {})
        return {
            "monotonic": raw["monotonic"], "status": raw["status"],
            "host_mem_available_bytes": raw.get("host_mem_available_bytes"),
            "gate_memory": raw.get("gate_memory"),
            "cgroup": {name: cgroup.get(name) for name in
                       ("memory.current", "memory.max", "memory.peak", "memory.events")},
            "cgroup_usage": {name: stat.get(name) for name in
                             ("anon", "file", "inactive_file", "shmem")},
            "observer_rss_bytes": raw["process"]["status"].get("VmRSS"),
        }

    def collect():
        try:
            while len(observations["load_samples"]) < LOAD_SAMPLE_LIMIT and not finished.wait(1):
                if (root / "model-initialization-exit-memory.json").is_file():
                    break
                if (root / "model-load-start.json").is_file():
                    observation = snapshot()
                    if finished.is_set():
                        break
                    observations["load_samples"].append(observation)
                    if finished.wait(4):
                        break
            finished.wait()
            observations["after_worker"] = snapshot()
        except (OSError, ValueError, KeyError) as error:
            observations["observer_error"] = type(error).__name__

    observer = Thread(target=collect, name="ct1-ram-observer", daemon=True)
    observer.start()
    try:
        yield result
    finally:
        finished.set()
        wait = 1 if cutoff is None else min(1, max(0, cutoff - time.monotonic()))
        observer.join(timeout=wait)
        # A stalled daemon retains no file handle to an output and can never
        # publish into the result. The controller exports only this frozen copy.
        captured = dict(observations)
        result.update(captured, load_samples=tuple(captured["load_samples"]),
                      after_worker_status="OBSERVED" if "after_worker" in captured else "UNAVAILABLE")


def publish_worker_memory(root, observations, cutoff):
    if observations is None or time.monotonic() >= cutoff:
        return
    # Seal one bounded record via a separate staging name. A timed-out write
    # cannot expose a partial observation to result/checkpoint reconstruction.
    staging = root.parent / (WORKER_MEMORY + ".pending")
    target = root / WORKER_MEMORY
    payload = json_bytes(dict(observations))
    if len(payload) > ct1_run.CONTROLLER_RECORD_BYTES:
        return
    try:
        with supervision.parent_deadline(cutoff, "ct1_worker_telemetry"):
            write_bytes(staging, payload)
            # The controller exclusively owns this name in its fresh job.
            if not target.exists():
                staging.rename(target)
    except (TimeoutError, OSError):
        pass


def worker(args):
    cfg = config(args.config)
    require_native_admission(cfg)
    deadline = args.deadline
    root, scratch = args.job / "evidence", args.scratch
    data, software, checkpoint, lock, plan = layout(cfg)
    drivers = [cfg["observed_driver"]]
    budgets = ct1_native.release_budgets(drivers)
    if args.command == "setup":
        memory.observe(root, "setup-entry")
        try:
            resources = environment.resources("qwen3", budgets, scratch, args.job,
                                              memory_receipt=root / "setup-ram-gate.json")
            driver, _ = gpu_driver.locate()
            write(root / "before-setup.json", {
                "resources": resources,
                "physical": gpu_driver.hardware("qwen3", budgets, driver, root, "setup"), "native_calls": 0})
            archive_dir = ct1_run.restore_software(software, cfg["software_marker_sha256"], lock, scratch, REPO)
            memory.observe(root, "setup-archives-restored")
            python, _ = provision.prepare({"model_key": "qwen3", "scratch": str(scratch),
                                          "software_input": str(software), "software_marker_sha256":
                                          cfg["software_marker_sha256"], "runtime_lock": lock},
                                         REPO, args.job / "setup", deadline, archive_dir=archive_dir,
                                         observe=lambda phase: memory.observe(root, "setup-" + phase))
            require(python == scratch / "qwen-software/venv/bin/python", "CT1_RUNTIME_PATH")
        finally:
            memory.observe(root, "setup-exit")
        return
    require_closed_phase(root, "setup")
    if args.command == "probe":
        reclaim_setup(root, scratch, deadline)
        ct1_native.advise_locked_files(
            software / "wheels", {r["file"]: r["size"] for r in lock["wheels"]},
            root / "wheel-cache-advice.json", deadline)
        try:
            runtime = ct1_native.probe_runtime(checkpoint, REPO, lock, drivers, scratch, args.job, data, plan)
            write(root / "runtime-probe.json", runtime)
        finally:
            memory.observe(root, "runtime-probe-exit")
        return

    reclaim_setup(root, scratch, deadline, label="probe")
    runtime = strict_json(ct1_run.read_controller_record(root, "runtime-probe.json"))
    require(runtime.get("model_calls") == 0 and runtime.get("weights_loaded") is False,
            "CT1_RUNTIME_PROBE_RECEIPT")
    checked = ct1_native.verify_checkpoint(checkpoint, REPO, drivers, root, deadline)
    write(root / "preflight.json", {**runtime, "checkpoint": checked})
    if cfg["mode"] == "preflight":
        return
    state = binding(cfg, lock)
    require(state == strict_json((root / "identity.json").read_bytes()), "CT1_RUNTIME_IDENTITY_CHANGED")
    require(strict_json((root / "resume-admission.json").read_bytes()) == {"status": "FRESH_ADMITTED"}
            and not (root / "calls").exists(), "CT1_FRESH_LEDGER_REQUIRED")
    driver = gpu_driver.bind(root)

    def before_load():
        gpu_driver.hardware("qwen3", budgets, driver, root, "worker")
        memory.ct1_ram_gate(root, "before-model-load-ram-gate", budgets["free_ram_mib"] * 2**20)
        write(root / "model-load-start.json", {"monotonic": time.monotonic()})

    memory.observe(root, "model-initialization-entry")
    try:
        backend = ct1_native.Backend(checkpoint, REPO, before_load=before_load)
    finally:
        memory.observe(root, "model-initialization-exit")
    write(root / "model-loaded.json", {"weights_loaded": True, "device_map": qwen.DEVICE_MAP,
                                      "generation": backend.config.to_dict(),
                                      "memory": backend.record_memory()})
    shards = {row["path"]: row["size_bytes"] for row in qwen.reference(REPO)["snapshot_files"]
              if row["path"].endswith(".safetensors")}
    ct1_native.advise_locked_files(checkpoint, shards, root / "loaded-weight-cache-advice.json", deadline)
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
        records = ("identity.json", "config-summary.json", "controller-failure.json",
                   *CONTROLLER_MEMORY, *ct1_run.PROCESS_RECEIPTS, "probe-supervisor.json")
        # A failed setup can be safely collected without a worker receipt, but
        # only when setup's own receipt proves its entire group was reaped.
        try:
            setup = strict_json(ct1_run.read_controller_record(root, "setup-supervisor.json"))
            if supervision.process_group_closed(setup):
                records += ("setup-ram-gate.json", *(f"setup-{phase}-memory.json" for phase in SETUP_MEMORY))
        except (ValueError, OSError):
            pass
        try:
            probe = strict_json(ct1_run.read_controller_record(root, "probe-supervisor.json"))
            if supervision.process_group_closed(probe):
                records += ("runtime-probe.json", "runtime-probe-exit-memory.json", "wheel-cache-advice.json",
                            "setup-cache-advice.json", "setup-reclaim-before-memory.json",
                            "setup-reclaim-after-memory.json", "runtime-probe/ram-gate.json",
                            "runtime-probe/before-gate-memory.json", "runtime-probe/gate-failure-memory.json",
                            "runtime-probe/driver-library-binding.json", "runtime-probe/probe-nvidia-smi.json",
                            "runtime-probe/software.json", "runtime-probe/cuda.json")
        except (ValueError, OSError):
            pass
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
            summary = strict_json(ct1_run.read_controller_record(root, "summary.json"))
        except (ValueError, KeyError, TypeError, OSError) as exc:
            write(root / "journal-export-failure.json",
                  {"status": "FORENSIC_ONLY", "type": type(exc).__name__, "message": str(exc)[:2000]})
            export_diagnostic(root, archive, str(exc)[:2000], ledger_stable=True)
            return "FORENSIC_ONLY"
    publish_export(root, archive)
    if mode in ("pilot", "smoke") and summary["returned"] != summary["planned_calls"]:
        return "PARTIAL_OR_BLOCKED"
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
    info = snapshot_stat(scratch, directory=True)
    write(root / "scratch-ownership.json", {"device": info.st_dev, "inode": info.st_ino})
    write(root / "identity.json", state)
    write(root / "config-summary.json", {"mode": cfg["mode"], "source_commit": cfg["source_commit"],
                                        "limits": budgets, "max_calls": state["max_calls"],
                                        "cross_vm_resume": "BLOCKED_NO_LATEST_LEDGER_PROOF"})
    env = provision.clean_env(REPO, scratch)
    env.update(PYTORCH_ALLOC_CONF="expandable_segments:True", CUDA_VISIBLE_DEVICES="0,1",
               TMP=str(scratch), TEMP=str(scratch), OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
    setup_cutoff = min(deadline - EXPORT_RESERVE, time.monotonic() + budgets["setup_seconds"])
    worker_memory = None
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

        memory.observe(root, "controller-before-setup")
        try:
            launch("setup", sys.executable, setup_cutoff, env)
        finally:
            memory.observe(root, "controller-after-setup")
        venv = scratch / "qwen-software/venv"
        python = venv / "bin/python"
        env.update(SAFESHIFT_WORKER_PYTHON=str(python), SAFESHIFT_RUNTIME_ROOT=str(venv))
        native_cutoff = deadline - EXPORT_RESERVE - WORKER_TELEMETRY_RESERVE
        if cfg["mode"] == "preflight":
            native_cutoff = min(native_cutoff, time.monotonic() + budgets["diagnostic_seconds"])
        probe_cutoff = min(native_cutoff, time.monotonic() + budgets["diagnostic_seconds"])
        memory.observe(root, "controller-before-probe")
        try:
            launch("probe", python, probe_cutoff, env)
        finally:
            memory.observe(root, "controller-after-probe")
        memory.observe(root, "controller-before-worker")
        with observe_worker_load(root, cutoff=deadline - EXPORT_RESERVE) as worker_memory:
            launch("worker", python, native_cutoff, env)
    except (ValueError, OSError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
        write(root / "controller-failure.json", {"type": type(exc).__name__,
              "message": str(exc)[:2000], "automatic_retry": False, "status": "PARTIAL_OR_BLOCKED"})
        # Return with an export for controlled failure, so it is retained by the
        # notebook versioner. The receipt and summary carry the actual status.
    finally:
        publish_worker_memory(root, worker_memory, deadline - EXPORT_RESERVE)
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
    parser.add_argument("command", choices=("supervise", "setup", "probe", "worker"))
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
