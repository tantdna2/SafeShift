"""Opt-in real Linux package installation only: no models, images or CUDA calls.

Never part of the default CPU test suite. Each model gets a fresh venv. Uses the
same ordered install commands as Kaggle, including the repeated exact CUDA pins.
Large installed libraries/logs remain under ignored data/processed, not Git.
"""
import argparse
import os
from pathlib import Path
import platform
import sys

from safeshift.pilot.artifacts import sha, write
from safeshift.pilot.bootstrap import prepare_runtime
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
    receipt = {"model": args.model, "platform": platform.platform(), "controller_python": sys.version,
               "status": "NOT_COMPLETED", "gpu": "NOT_RUN", "weights": "NOT_DOWNLOADED",
               "requirements_sha256": sha(repo / f"configs/pilot/{args.model}.requirements.txt"),
               "production_prepare_runtime": True}
    try:
        python, _, runtime_receipt = prepare_runtime(repo, args.model, output, output, env)
        receipt["status"] = "ORDERED_INSTALL_AND_RUNTIME_PINS_PASS_NOT_KAGGLE"
        receipt.update(worker_python=str(python), runtime_preflight_sha256=sha(output / "runtime_preflight.json"),
                       pip_freeze_sha256=runtime_receipt["pip_freeze_sha256"])
    finally:
        write(output / "receipt.json", receipt)


if __name__ == "__main__":
    main()
