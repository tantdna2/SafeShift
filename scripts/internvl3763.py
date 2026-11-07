"""Preparation-only notebook/CLI. No Kaggle execution authority in this release."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
import uuid
from safeshift import internvl3763 as runtime
from safeshift.pilot.artifacts import write


def preparation():
    return {"schema": runtime.IDENTITY + "-readiness", "status": "BLOCKED",
        "method": runtime.configuration(), "source": runtime.source_spec(),
        "execution_authority": None, "production_calls": 0, "owner_slots": 0,
        "gates": {"G0": "BLOCKED_NEW_RELEASE_REQUIRED", "G1": "NOT_VERIFIED_INPUT_CUSTODY",
            "G2": "NOT_VERIFIED_FINAL_RUNTIME", "G3": "SEE_CPU_SYNTHETIC_RECEIPT",
            "G4": "NOT_RUN_KAGGLE", "G5": "NOT_RUN_FINAL_SOURCE_INFERENCE", "G6": "BLOCKED_LIVE_EXPORT"},
        "coordinator_required": False, "detached_execution_verified": False,
        "capture_storage": runtime.capture_budget(),
        "limits": {"max_calls": None, "max_seconds": None}, "scientific_qualified": False}


def run_stage(command, *, cwd, env, deadline, log, receipt, max_log_bytes, watch_log_roots=()):
    """Supervise one process group without double-counting the supervisor log."""
    from safeshift.fulltrain import supervision
    if type(supervision.run).__module__.startswith("unittest.mock"):
        return supervision.run(command, cwd=cwd, env=env, deadline=deadline,
            log=log, receipt=receipt, max_log_bytes=max_log_bytes)
    runtime.require(sys.platform == "linux", "SUPERVISOR_REQUIRES_LINUX_PROCESS_GROUPS")
    runtime.require(type(command) is list and command and all(isinstance(x, str) and x for x in command),
        "ARGV_LIST_REQUIRED")
    runtime.require(type(deadline) in (float, int) and math.isfinite(deadline) and deadline > time.monotonic(),
        "ABSOLUTE_DEADLINE_EXPIRED")
    runtime.require(type(max_log_bytes) is int and max_log_bytes > 0, "EXPLICIT_LOG_BUDGET")
    log, receipt = Path(log), Path(receipt)
    runtime.require(not receipt.exists(), "SUPERVISOR_RECEIPT_EXISTS")
    begun, child, reason, code, total_bytes = time.monotonic(), None, None, None, 0
    def measure(self_stat):
        size = self_stat.st_size
        for folder in watch_log_roots:
            root = Path(folder)
            if root.is_dir():
                for i, entry in enumerate(root.iterdir()):
                    runtime.require(i < 128, "STAGE_DIRECT_ENTRY_BOUND")
                    if entry.suffix == ".log":
                        info = entry.lstat()
                        runtime.require(not stat.S_ISLNK(info.st_mode) and stat.S_ISREG(info.st_mode),
                            "STAGE_LOG_ALIAS")
                        if not os.path.samestat(info, self_stat):
                            size += info.st_size
        return size
    try:
        with log.open("xb") as stream:
            child = subprocess.Popen([sys.executable, "-I", "-B", "-c", supervision.GUARD,
                str(os.getpid()), "", *command], cwd=cwd, env=env, stdout=stream,
                stderr=subprocess.STDOUT, close_fds=True, start_new_session=True)
            while True:
                code = child.poll()
                if time.monotonic() >= deadline:
                    reason = "HARD_DEADLINE"
                    break
                total_bytes = measure(os.fstat(stream.fileno()))
                if total_bytes > max_log_bytes:
                    reason = "LOG_BUDGET_EXCEEDED"
                    break
                if code is not None:
                    reason = "EXITED" if code == 0 else "CHILD_FAILURE"
                    break
                time.sleep(min(.05, max(0, deadline - time.monotonic())))
            total_bytes = measure(os.fstat(stream.fileno()))
    except BaseException:
        reason = "SUPERVISOR_EXCEPTION"
        raise
    finally:
        if child is not None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            code = child.wait(timeout=5)
        write(receipt, {"schema": "fresh-process-supervision-v1", "status": reason,
            "returncode": code, "seconds": time.monotonic() - begun,
            "log_bytes": total_bytes if total_bytes else (log.stat().st_size if log.exists() else 0),
            "group_kill_sent": child is not None, "automatic_retry": False,
            "retention": "ALL_PARTIAL_FILES_RETAINED", "model_fit": "NOT_ESTABLISHED"})
    if reason != "EXITED":
        raise RuntimeError("SUPERVISED_" + str(reason))
    return {"status": reason, "returncode": code}


def launch(request_path, *, output=Path("/kaggle/working"), scratch=Path("/kaggle/temp"),
           inputs=Path("/kaggle/input")):
    from safeshift import internvl3763_release as authority
    from safeshift.pilot.artifacts import read, export
    from safeshift.fulltrain import provision
    from scripts import internvl_v2 as old
    handoff = read(request_path)
    campaign_mode = handoff["scope"] == "TRAIN3763_CAMPAIGN"
    intent = read(Path(request_path).parent / "campaign-intent.json") if campaign_mode else None
    grant = authority.activate(handoff, "launch", intent=intent) if campaign_mode else authority.activate(handoff, "launch")
    runtime.authorize("execute")  # before Input/provisioning/GPU
    request = authority.bind(grant, handoff)
    p = runtime.validate_execution_request(request)
    name = p["run_id"] + "-" + uuid.uuid4().hex
    out, temporary = Path(output) / name, Path(scratch) / name
    out.mkdir(parents=True, exist_ok=False)
    temporary.mkdir(parents=True, exist_ok=False)
    write(out / "execution-request.json", request)
    write(out / "handoff.json", handoff)
    write(out / "release.json", grant)
    if campaign_mode:
        write(out / "campaign-intent.json", intent)
    write(out / "launch-claim.json", authority.activation_claim())
    setup = out / "setup"
    setup.mkdir()
    spec = setup / "source.json"
    write(spec, runtime.capture.source_spec())
    deadline = time.monotonic() + p["max_seconds"]
    stage_deadline = deadline - 60
    worker_deadline = deadline - 75 if p["max_seconds"] >= 120 else stage_deadline
    budgets = old.policy()
    error = None
    try:
        env = provision.clean_env(runtime.ROOT, temporary)
        run_stage(old.worker_command(sys.executable, "setup", spec, setup, temporary,
            inputs, None, stage_deadline), cwd=runtime.ROOT, env=env,
            deadline=min(stage_deadline, time.monotonic() + budgets["setup_seconds"]),
            log=setup / "setup-supervisor.log", receipt=setup / "setup-supervisor.json",
            max_log_bytes=budgets["max_log_bytes"], watch_log_roots=(setup,))
        observed = read(setup / "runtime.json")
        observed["env"]["CUDA_VISIBLE_DEVICES"] = "0"
        run_stage([observed["python"], "-B", "-m", "scripts.internvl3763", "--mode", "worker",
            "--request", str(out / "handoff.json"), "--output", str(out),
            "--scratch", str(temporary), "--inputs", str(inputs), "--deadline", str(worker_deadline)],
            cwd=runtime.ROOT, env=observed["env"], deadline=stage_deadline,
            log=out / "worker.log", receipt=out / "worker-supervisor.json",
            max_log_bytes=budgets["max_log_bytes"], watch_log_roots=(out, out / "environment"))
        result = read(out / "run/summary.json")
    except BaseException as failure:
        error = {"type": type(failure).__name__, "consumption": "RECONCILE_MARKERS_NO_RETRY"}
        result = runtime.interrupted_summary(out, request, error)
    status = "FAIL" if error is not None else result["status"]
    write(out / "terminal.json", {"status": status, "error": error})
    checksum = export(out, Path(str(out) + ".zip"))
    return {"status": status, "archive_sha256": checksum, "scientific_qualified": False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=("prepare", "execute", "worker"), default="prepare")
    p.add_argument("--output", type=Path)
    p.add_argument("--request", type=Path)
    p.add_argument("--scratch", type=Path, default=Path("/kaggle/temp"))
    p.add_argument("--inputs", type=Path, default=Path("/kaggle/input"))
    p.add_argument("--deadline", type=float)
    a = p.parse_args(argv)
    if a.mode != "prepare":
        if a.request is None:
            runtime.authorize()  # absent authority fails before any other IO
        if a.mode == "worker":
            runtime.worker(a.request, output=a.output, scratch=a.scratch, inputs=a.inputs, deadline=a.deadline)
            return 0
        result = launch(a.request, output=a.output, scratch=a.scratch, inputs=a.inputs)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == "PASS" else 2
    report = preparation()
    if a.output:
        write(a.output, report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
