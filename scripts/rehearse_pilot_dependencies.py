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
from safeshift.pilot.bootstrap import dependency_commands
from safeshift.pilot.contract import MODELS


def cpu_smoke(key):
    """Installed native library/CPU ABI only; no model construction or CUDA API."""
    import torch
    import torchvision
    import transformers
    # Real native torchvision op catches binary mismatch without a GPU or image.
    boxes = torch.tensor([[0., 0., 1., 1.], [0., 0., 2., 2.]])
    kept = torchvision.ops.nms(boxes, torch.tensor([.9, .8]), .5)
    assert kept.tolist() == [0, 1]
    assert torch.ones(2, dtype=torch.float16).sum().item() == 2.0
    model_class = (transformers.AutoModelForCausalLM if key == "phi" else
                   transformers.Gemma3ForConditionalGeneration if key == "gemma" else
                   transformers.SmolVLMForConditionalGeneration)
    return {"status": "CPU_LIBRARY_IMPORT_AND_NATIVE_OP_PASS_NOT_INFERENCE",
            "torch": torch.__version__, "torchvision": torchvision.__version__,
            "transformers": transformers.__version__, "model_api": model_class.__name__,
            "processor_api": transformers.AutoProcessor.__name__, "gpu": "NOT_RUN",
            "custom_phi_execution": "NOT_RUN", "weights": "NOT_DOWNLOADED"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", choices=tuple(MODELS), required=True)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    output = (repo / args.output).resolve()
    if not output.is_relative_to(repo / "data/processed"):
        raise ValueError("OUTPUT_MUST_BE_UNDER_DATA_PROCESSED")
    if platform.system() != "Linux" or sys.version_info[:2] not in ((3, 11), (3, 12)):
        raise RuntimeError("LINUX_PYTHON_311_OR_312_REQUIRED")
    output.mkdir(parents=True, exist_ok=False)
    temporary = output / "tmp"
    temporary.mkdir()
    env = {**os.environ, "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary),
           "CUDA_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
           "PYTHONPATH": str(repo), "PYTHONDONTWRITEBYTECODE": "1"}
    python = output / "venv/bin/python"
    commands = [[sys.executable, "-m", "venv", str(output / "venv")],
                *dependency_commands(python, repo, args.model)]
    # Metadata check uses the production function without ML imports/GPU probing.
    commands += [[str(python), "-B", "-c",
                  "import json; from safeshift.pilot.backend import check_software; "
                  f"print(json.dumps(check_software({str(repo)!r}, {args.model!r}), sort_keys=True))"],
                 [str(python), "-B", "-c",
                  "import json; from scripts.rehearse_pilot_dependencies import cpu_smoke; "
                  f"print(json.dumps(cpu_smoke({args.model!r}), sort_keys=True))"],
                 [str(python), "-m", "pip", "freeze"]]
    receipt = {"model": args.model, "platform": platform.platform(), "python": sys.version,
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
