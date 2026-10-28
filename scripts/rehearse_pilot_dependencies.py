"""Opt-in real Linux package installation only: no models, images or CUDA calls.

Never part of the default CPU test suite. Each model gets a fresh venv. Uses the
same ordered install commands as Kaggle, including the repeated exact CUDA pins.
Large installed libraries/logs remain under ignored data/processed, not Git.
"""
import argparse
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from safeshift.pilot.artifacts import sha, write, write_bytes
from safeshift.pilot.bootstrap import dependency_commands, select_interpreter
from safeshift.pilot.contract import MODELS


def cpu_smoke(key):
    """Installed native library/CPU ABI only; no model construction or CUDA API."""
    from safeshift.pilot.backend import cpu_software_probe
    return cpu_software_probe(Path.cwd(), key)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", choices=tuple(MODELS), required=True)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    output = (repo / args.output).resolve()
    if not output.is_relative_to(repo / "data/processed"):
        raise ValueError("OUTPUT_MUST_BE_UNDER_DATA_PROCESSED")
    output.mkdir(parents=True, exist_ok=False)
    temporary = output / "tmp"
    temporary.mkdir()
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("PIP_") and not k.startswith("PYTHON")}
    env.update({"TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary),
           "CUDA_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
           "PYTHONPATH": str(repo), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"})
    selected, selection = select_interpreter(env)
    python = output / "venv/bin/python"
    env.update(SAFESHIFT_WORKER_PYTHON=str(python), SAFESHIFT_RUNTIME_ROOT=str(output / "venv"),
               SAFESHIFT_NOTEBOOK_PYTHON=str(Path(sys.executable).resolve()))
    commands = [[str(selected), "-I", "-B", "-m", "venv", "--copies", str(output / "venv")],
                *dependency_commands(python, repo, args.model)]
    # The same future worker verifies isolation, pins and native CPU ABI.
    commands += [[str(python), "-B", "-c",
                  "import json; from safeshift.pilot.bootstrap import runtime_identity; "
                  "from safeshift.pilot.backend import cpu_software_probe; "
                  f"print(json.dumps({{'identity': runtime_identity({str(python)!r}, {str(output / 'venv')!r}), "
                  f"'software': cpu_software_probe({str(repo)!r}, {args.model!r})}}, sort_keys=True))"],
                 [str(python), "-m", "pip", "freeze"]]
    receipt = {"model": args.model, "platform": platform.platform(), "controller_python": sys.version,
               "interpreter_selection": selection, "selected_python": str(selected),
               "status": "NOT_COMPLETED", "gpu": "NOT_RUN", "weights": "NOT_DOWNLOADED",
               "requirements_sha256": sha(repo / f"configs/pilot/{args.model}.requirements.txt"),
               "steps": []}
    try:
        for i, command in enumerate(commands):
            start = time.monotonic()
            log = output / f"step_{i:02d}.log"
            print("INSTALL_REHEARSAL", args.model, "step", i, flush=True)
            with log.open("xb") as stream:
                run = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=7200)
            receipt["steps"].append({"ordinal": i, "command": command, "returncode": run.returncode,
                                      "seconds": time.monotonic() - start, "log_sha256": sha(log)})
            if run.returncode:
                raise RuntimeError(f"INSTALL_REHEARSAL_FAILED_STEP_{i}")
        receipt["status"] = "ORDERED_INSTALL_AND_RUNTIME_PINS_PASS_NOT_KAGGLE"
        write_bytes(output / "pip_freeze.txt", (output / f"step_{len(commands)-1:02d}.log").read_bytes())
    finally:
        write(output / "receipt.json", receipt)


if __name__ == "__main__":
    main()
