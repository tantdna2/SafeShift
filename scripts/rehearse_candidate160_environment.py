"""Linux CPU proof of the production CPython/cu124 software path, no CUDA calls.

Software downloads only. Optional snapshot is public source/tokenizer only.
The evidence directory must be new and under ignored data/processed.
"""
import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import subprocess
import sys
import time

from safeshift.candidates.source import ROOT, require, stage_snapshot
from safeshift.candidates.train_contract import KEYS, model, source_hash
from safeshift.pilot import bootstrap as boot
from safeshift.pilot.artifacts import write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", choices=KEYS, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--snapshot")
    parser.add_argument("--scratch-root", help="Explicit Linux filesystem with enough space; avoid a small tmpfs")
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    output = Path(args.output).absolute()
    require(output.is_relative_to(ROOT / "data/processed"), "IGNORED_OUTPUT_REQUIRED")
    if args.worker:
        from safeshift.candidates.train_runtime import software
        from safeshift.candidates.train_preflight import native_cpu
        from scripts.rehearse_candidate_cpu import guard
        with ExitStack() as stack:
            guard(stack, allow_empty_state_loader=True)
            receipt = software(args.key)
            write(output / "production_software_cpu.json", receipt)
            if args.snapshot:
                write(output / "production_native_cpu.json", native_cpu(args.key, Path(args.snapshot), ROOT))
        return
    output.mkdir(parents=True, exist_ok=False)
    require(args.scratch_root, "EXPLICIT_SCRATCH_ROOT_REQUIRED")
    scratch_root = Path(args.scratch_root)
    scratch_root.mkdir(parents=True, exist_ok=True)
    scratch, env = boot.prepare_scratch(scratch_root, "env-audit-" + args.key + "-" + str(os.getpid()))
    from safeshift.candidates.train_runtime import prepare_runtime
    python, env = prepare_runtime(ROOT, args.key, scratch, output, env, time.monotonic() + 7200)
    command = [str(python), "-B", "-m", "scripts.rehearse_candidate160_environment", "--worker",
               "--key", args.key, "--output", str(output)]
    if args.snapshot:
        snapshot = scratch / model(args.key)["revision"]
        stage_snapshot(Path(args.snapshot), snapshot, args.key)
        command += ["--snapshot", str(snapshot)]
    with (output / "native_cpu.log").open("xb") as log:
        subprocess.run(command, env={**env, "CUDA_VISIBLE_DEVICES": ""}, check=True, timeout=1800,
                       stdout=log, stderr=subprocess.STDOUT)
    write(output / "cpu_environment_audit.json", {"status": "CPU_SOFTWARE_PASS_GPU_UNVERIFIED",
        "source_sha256": source_hash(), "model_key": args.key, "scratch_retained_for_review": str(scratch),
        "cuda_calls": "FORBIDDEN", "weights": "FORBIDDEN", "private_data": "NOT_READ"})
    print("CPU_SOFTWARE_PASS_GPU_UNVERIFIED", args.key)


if __name__ == "__main__":
    main()
