"""Run the real production --check-only subprocess in its pinned Linux stack.

No monkeypatches, CUDA, weights or forward calls. The authorized locked TRAIN
bundle is read/hash/decoded; outputs are CPU engineering evidence only.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from safeshift.candidates.source import ROOT, require
from safeshift.candidates.train_contract import KEYS, source_hash
from safeshift.candidates.train_owner import execution
from safeshift.candidates.train_runtime import worker_command
from safeshift.pilot.artifacts import read, sha, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", choices=KEYS, required=True)
    for name in ("snapshot", "bundle", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--implementation", choices=("minicpm4-resampler-attention-fp32-v1",))
    args = parser.parse_args()
    output = args.output.absolute()
    require(output.is_relative_to(ROOT / "data/processed"), "IGNORED_OUTPUT_REQUIRED")
    output.mkdir(parents=True, exist_ok=False)
    source = source_hash()
    if args.implementation:
        from safeshift.candidates.train_smoke import execution as smoke_execution
        record = smoke_execution(args.key, source, args.ref, implementation=args.implementation)
    else:
        record = execution(args.key, source, args.ref, owner_start=True)
    execution_file = output / "cpu_execution.json"
    write(execution_file, record)
    runtime = Path(sys.prefix)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "HF_", "PIP_"))}
    env.update(PYTHONPATH=str(ROOT), PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1",
               SAFESHIFT_WORKER_PYTHON=sys.executable, SAFESHIFT_RUNTIME_ROOT=str(runtime),
               HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", CUDA_VISIBLE_DEVICES="",
               TOKENIZERS_PARALLELISM="false", OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
    command = worker_command(sys.executable, ROOT, output, args.bundle.absolute(), args.snapshot.absolute(),
                             output / "ABSENT_WEIGHTS", source, args.ref, execution=execution_file) + ["--check-only"]
    with tempfile.TemporaryDirectory(prefix="candidate-cpu-cache-") as cache:
        env["HF_MODULES_CACHE"] = str(Path(cache) / "modules")
        with (output / "cpu.log").open("xb") as log:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=600, check=False)
    passed = result.returncode == 0
    if passed:
        require(read(output / "images_cpu.json")["verified_images"] == 160, "ALL_IMAGES_CHECK_REQUIRED")
        native = read(output / "native_cpu.json")
        require(native["meta_loader"]["status"] == "EAGER_MODULES_VERIFIED" and
                len(native["synthetic_images"]) == 8, "NATIVE_META_AND_PROCESSOR_REQUIRED")
    write(output / "receipt.json", {"status": "CPU_CLI_PASS" if passed else "FAIL",
        "key": args.key, "source_sha256": source, "runtime_ref": args.ref,
        "command": command, "returncode": result.returncode, "log_sha256": sha(output / "cpu.log"),
        "native_setup_mocked": False, "worker_mocked": False, "verify_snapshot_mocked": False,
        "weights": "ABSENT_NOT_LOADED", "gpu": "HIDDEN_NOT_CALLED", "inference": "NOT_RUN",
        "scope": "CPU_TECHNICAL_ONLY_NOT_A_PRODUCTION_ATTEMPT"})
    print(args.key, "CPU_CLI_PASS" if passed else "FAIL", flush=True)
    if not passed:
        print((output / "cpu.log").read_text(errors="replace")[-6000:])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
