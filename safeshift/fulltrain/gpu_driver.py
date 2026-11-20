"""Mounted host NVIDIA driver binding for the isolated MiniCPM GPU/native stages.

Serial 8 failed at the first GPU gate: the supervised child runs with
``provision.clean_env`` (no ``LD_LIBRARY_PATH``), so ``nvidia-smi`` resolved
through PATH but exited 12. CUDA was never tested in that container. Issue173 V4
measured the same exit in an isolated worker on a GPU-enabled T4 x2 kernel
(docs/KAGGLE_CHECKPOINTS_173.md). The successful InternVL Full-TRAIN worker
used the scoped binding repeated here:

* ``libcuda.so.1`` is opened by absolute path with ``RTLD_GLOBAL`` before CUDA
  initialization, so later SONAME lookups by Torch resolve to that object;
* only the ``nvidia-smi`` subprocess receives the mounted directory as
  ``LD_LIBRARY_PATH``. Python's own loader environment is never changed.

No driver installation, stub, compat fallback or gate change. Hardware gates
keep their original codes. Every observation, including the failing command's
exit code and bounded stdout/stderr, is written before an exception propagates.
"""
import ctypes
import ctypes.util
import os
from pathlib import Path
import subprocess

from safeshift.candidates.source import require
from safeshift.pilot.artifacts import sha, write

IMPLEMENTATION = "minicpm-fulltrain-scoped-host-driver-v1"
REFERENCE = "issue173-explicit-host-cuda-driver-v1"
# The same bounded host mount as the verified Issue173 worker.
DRIVER_DIRECTORIES = ("/usr/local/nvidia/lib64",)
LIBRARIES = ("libnvidia-ml.so.1", "libcuda.so.1")
QUERY = ["nvidia-smi", "--query-gpu=index,name,memory.free,driver_version", "--format=csv,noheader,nounits"]
STREAM_BYTES = 4096
_HANDLE = {}


def _elf(path):
    try:
        with Path(path).open("rb") as stream:
            return stream.read(4) == b"\x7fELF"
    except OSError:
        return False


def probe(directories=DRIVER_DIRECTORIES):
    """Observe candidate driver directories without loading anything."""
    rows = []
    for directory in directories:
        row = {"directory": directory}
        for name in LIBRARIES:
            path = Path(directory) / name
            row[name] = {"exists": path.is_file(), "elf": path.is_file() and _elf(path),
                         "resolved": str(path.resolve()) if path.is_file() else None}
        rows.append(row)
    return {"candidates": rows, "nvml_find_library": ctypes.util.find_library("nvidia-ml"),
        "loader_environment": {n: os.environ.get(n) for n in
            ("LD_LIBRARY_PATH", "LD_PRELOAD", "NVIDIA_VISIBLE_DEVICES", "NVIDIA_DRIVER_CAPABILITIES",
             "CUDA_VISIBLE_DEVICES")}}


def locate(directories=DRIVER_DIRECTORIES):
    observed = probe(directories)
    for row in observed["candidates"]:
        if all(row[name]["exists"] and row[name]["elf"] for name in LIBRARIES):
            return Path(row["directory"]), observed
    raise ValueError("SYSTEM_NVIDIA_DRIVER_MOUNT_REQUIRED")


def bind(out, *, directories=DRIVER_DIRECTORIES, loader=ctypes.CDLL):
    """Bind libcuda once per process, before any CUDA initialization."""
    out = Path(out)
    receipt = {"implementation": IMPLEMENTATION, "reference": REFERENCE, "status": "BLOCKED",
        "python_ld_library_path_changed": False, "nvml_utility_loader_scoped_to_subprocess": True,
        "cuda_initialized": False, "weights_loaded": False, "model_calls": 0}
    try:
        directory, observed = locate(directories)
        receipt["probe"] = observed
        library = directory / "libcuda.so.1"
        receipt.update(directory=str(directory), library=str(library), library_resolved=str(library.resolve()),
            library_sha256=sha(library), library_bytes=library.stat().st_size)
        key = str(library.resolve())
        if key not in _HANDLE:
            _HANDLE[key] = loader(str(library), mode=ctypes.RTLD_GLOBAL)
        receipt["status"] = "BOUND"
        return directory
    except BaseException as error:
        if "probe" not in receipt:
            receipt["probe"] = probe(directories)
        receipt["failure"] = {"type": type(error).__name__, "message": str(error)[:STREAM_BYTES]}
        raise
    finally:
        write(out / "driver-library-binding.json", receipt)


def utility_env(directory):
    """Environment for nvidia-smi only; never exported to Python or Torch."""
    directory = Path(directory)
    require((directory / "libnvidia-ml.so.1").is_file(), "SYSTEM_NVML_DRIVER_MOUNT_REQUIRED")
    return {**os.environ, "LD_LIBRARY_PATH": str(directory)}


def _text(value):
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    return str(value or "")[:STREAM_BYTES]


def query(directory, out, label, *, run=subprocess.run):
    """Run the exact original query with the scoped loader; keep failing streams."""
    receipt = {"label": label, "command": list(QUERY), "status": "BLOCKED",
        "utility_only_loader_override": {"LD_LIBRARY_PATH": str(directory)}}
    try:
        result = run(list(QUERY), capture_output=True, text=True, check=True, timeout=5,
            env=utility_env(directory))
        receipt.update(status="RETURNED", returncode=result.returncode, stdout=_text(result.stdout))
        return result.stdout
    except subprocess.CalledProcessError as error:
        receipt.update(returncode=error.returncode, stdout=_text(error.stdout), stderr=_text(error.stderr))
        raise
    except subprocess.TimeoutExpired as error:
        receipt.update(returncode=None, timeout_seconds=error.timeout, stdout=_text(error.stdout),
            stderr=_text(error.stderr))
        raise
    except BaseException as error:
        receipt["failure"] = {"type": type(error).__name__, "message": str(error)[:STREAM_BYTES]}
        raise
    finally:
        write(Path(out) / (label + "-nvidia-smi.json"), receipt)


def rows(stdout, budgets, *, headroom=(0, 1)):
    """Same validation and codes as environment.hardware; headroom per index."""
    parsed = [line.split(",") for line in stdout.strip().splitlines()]
    require(len(parsed) == 2 and all(len(r) == 4 for r in parsed), "EXACT_TWO_PHYSICAL_T4")
    observed = []
    for i, row in enumerate(parsed):
        index, name, free, driver = [s.strip() for s in row]
        require(index == str(i) and name in ("Tesla T4", "NVIDIA T4"), "ORDERED_T4_IDENTITIES")
        require(driver in budgets["driver_versions"], "UNAPPROVED_DRIVER")
        require(tuple(map(int, driver.split("."))) >= (525, 60, 13), "CUDA12_DRIVER_FLOOR")
        if i in headroom:
            require(int(free) >= budgets["free_mib_per_gpu"][i], "INDIVIDUAL_GPU_HEADROOM")
        observed.append({"index": i, "name": name, "free_mib": int(free), "driver": driver})
    return observed


def hardware(key, budgets, directory, out, label="gpu", *, run=subprocess.run):
    """Pre-load physical gate: exact two T4s, approved driver, both headrooms."""
    from .environment import policy
    policy(key, budgets)
    observed = rows(query(directory, out, label, run=run), budgets)
    return {"physical_gpus": observed, "cuda_initialized": False, "model_fit": "NOT_ESTABLISHED",
        "driver_binding": IMPLEMENTATION}


def loaded(key, budgets, directory, out, label, resident_floor, *, run=subprocess.run, torch_module=None):
    """Per-call health after the single model load on visible GPU0.

    Pre-load headroom on GPU0 cannot hold once the FP16 weights are resident, so
    the full gate stays before load (as in the successful MiniCPM 3-image and
    InternVL Full-TRAIN runs). Here identity/order/driver, unused GPU1 headroom,
    single visible T4 and a functional FP16 probe are rechecked and GPU0 free
    memory is recorded as evidence. RAM/disk gates are separate and unchanged.
    """
    from .environment import policy
    policy(key, budgets)
    require(os.environ.get("CUDA_VISIBLE_DEVICES") == "0", "WORKER_GPU_VISIBILITY")
    observed = rows(query(directory, out, label, run=run), budgets, headroom=(1,))
    if torch_module is None:
        import torch as torch_module
    torch = torch_module
    require(torch.version.cuda == "12.4" and torch.cuda.is_available() and torch.cuda.device_count() == 1
        and torch.cuda.get_device_capability(0) == (7, 5), "ISOLATED_SINGLE_VISIBLE_T4_REQUIRED")
    free, total = torch.cuda.mem_get_info(0)
    write(Path(out) / (label + "-resident-memory.json"), {"free_bytes": free, "total_bytes": total,
        "physical_gpu0_free_mib": observed[0]["free_mib"], "required_free_mib": resident_floor})
    require(free >= resident_floor * 2**20 and observed[0]["free_mib"] >= resident_floor,
        "MINICPM_RESIDENT_GPU0_HEADROOM")
    test = torch.ones(1, device="cuda:0", dtype=torch.float16)
    require(float(test.sum().item()) == 1.0, "WORKER_CUDA_FP16_FUNCTIONAL_FAILURE")
    del test
    torch.cuda.synchronize(0)
    return {"physical_gpus": observed, "gpu0_free_bytes": free, "gpu0_total_bytes": total,
        "resident_gpu0_min_free_mib": resident_floor, "driver_binding": IMPLEMENTATION}
