"""Preparation-only notebook/CLI. No Kaggle execution authority in this release."""
import argparse
import json
from pathlib import Path
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


def launch(request_path, *, output=Path("/kaggle/working"), scratch=Path("/kaggle/temp"),
           inputs=Path("/kaggle/input")):
    runtime.authorize()  # before request/Input/credentials/provisioning
    from safeshift.pilot.artifacts import read, export
    from safeshift.fulltrain import provision, supervision
    from scripts import internvl_v2 as old
    request = read(request_path)
    p = runtime.validate_execution_request(request)
    name = p["run_id"] + "-" + uuid.uuid4().hex
    out, temporary = Path(output) / name, Path(scratch) / name
    out.mkdir(parents=True, exist_ok=False)
    temporary.mkdir(parents=True, exist_ok=False)
    write(out / "execution-request.json", request)
    setup = out / "setup"
    setup.mkdir()
    spec = setup / "source.json"
    write(spec, runtime.capture.source_spec())
    deadline = time.monotonic() + p["max_seconds"]
    budgets = old.policy()
    error = None
    try:
        env = provision.clean_env(runtime.ROOT, temporary)
        supervision.run(old.worker_command(sys.executable, "setup", spec, setup, temporary,
            inputs, None, deadline), cwd=runtime.ROOT, env=env,
            deadline=min(deadline, time.monotonic() + budgets["setup_seconds"]),
            log=setup / "setup.log", receipt=setup / "setup-supervisor.json", max_log_bytes=budgets["max_log_bytes"])
        observed = read(setup / "runtime.json")
        observed["env"]["CUDA_VISIBLE_DEVICES"] = "0"
        supervision.run([observed["python"], "-B", "-m", "scripts.internvl3763", "--mode", "worker",
            "--request", str(out / "execution-request.json"), "--output", str(out),
            "--scratch", str(temporary), "--inputs", str(inputs), "--deadline", str(deadline - 60)],
            cwd=runtime.ROOT, env=observed["env"], deadline=deadline - 60,
            log=out / "worker.log", receipt=out / "worker-supervisor.json", max_log_bytes=budgets["max_log_bytes"])
        result = read(out / "run/summary.json")
    except BaseException as failure:
        error = {"type": type(failure).__name__, "consumption": "RECONCILE_MARKERS_NO_RETRY"}
        result = {"status": "FAIL", "error": error}
    write(out / "terminal.json", {"status": result["status"], "error": error})
    checksum = export(out, Path(str(out) + ".zip"))
    return {"status": result["status"], "archive_sha256": checksum, "scientific_qualified": False}


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
        runtime.authorize()  # before input/output/credential/GPU access
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
