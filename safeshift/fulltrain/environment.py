"""Explicit fresh resource policy and measurable Linux/worker checks.

No O5 defaults, authorization, weights or predictions. GPU functions are called
only by the fenced future diagnostic/worker composition, never by preparation.
"""
import importlib.metadata as metadata
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zlib

from safeshift.candidates.source import ROOT, require
from safeshift.pilot.artifacts import read, sha
from safeshift.pilot import bootstrap


def policy(key, value):
    fields = {"review_mode", "driver_versions", "free_mib_per_gpu", "free_gpu0_runtime_mib",
              "free_ram_mib", "free_scratch_mib", "free_output_mib", "scratch_probe_bytes",
              "output_probe_bytes", "max_log_bytes", "setup_seconds", "diagnostic_seconds"}
    require(key in ("qwen3", "internvl35", "minicpm4"), "RESOURCE_MODEL")
    require(type(value) is dict and set(value) == fields and value["review_mode"] == "EXTERNAL",
            "EXPLICIT_FRESH_RESOURCE_POLICY")
    require(type(value["driver_versions"]) is list and value["driver_versions"]
            and all(isinstance(x, str) and x and all(p.isdecimal() for p in x.split("."))
                    for x in value["driver_versions"]), "EXACT_APPROVED_DRIVER_LIST")
    require(type(value["free_mib_per_gpu"]) is list and len(value["free_mib_per_gpu"]) == 2,
            "TWO_PHYSICAL_GPU_BUDGETS_NO_POOLING")
    numbers = [value[n] for n in fields - {"review_mode", "driver_versions", "free_mib_per_gpu"}]
    require(all(type(n) is int and n > 0 for n in [*numbers, *value["free_mib_per_gpu"]]),
            "EXPLICIT_POSITIVE_RESOURCE_BUDGETS")
    return value


def host_memory(proc=Path("/proc/meminfo"), cgroup=Path("/sys/fs/cgroup")):
    rows = dict(line.split(":", 1) for line in proc.read_text().splitlines())
    available = int(rows["MemAvailable"].split()[0]) * 1024
    constraints = []
    found = False
    for limit, used in (("memory.max", "memory.current"),
                        ("memory/memory.limit_in_bytes", "memory/memory.usage_in_bytes")):
        if (cgroup / limit).exists():
            found = True
            text = (cgroup / limit).read_text().strip()
            if text != "max":
                remaining = max(0, int(text) - int((cgroup / used).read_text()))
                constraints.append(remaining)
                available = min(available, remaining)
    require(found, "CGROUP_MEMORY_LIMIT_UNOBSERVED")
    return {"available_bytes": available, "cgroup_remaining_bytes": constraints}


def resources(key, budgets, scratch, output):
    policy(key, budgets)
    memory = host_memory()
    require(memory["available_bytes"] >= budgets["free_ram_mib"] * 2**20, "HOST_OR_CGROUP_RAM")
    roots = [Path(scratch), Path(output)]
    devices = [p.stat().st_dev for p in roots]
    free = [shutil.disk_usage(p).free for p in roots]
    wanted = [budgets["free_scratch_mib"] * 2**20, budgets["free_output_mib"] * 2**20]
    if devices[0] == devices[1]:
        require(min(free) >= sum(wanted), "SHARED_DISK_RESERVES")
    else:
        require(all(f >= w for f, w in zip(free, wanted)), "SEPARATE_DISK_RESERVES")
    return {"memory": memory, "devices": devices, "free_bytes": free,
            "requested_reserves_bytes": wanted, "model_fit": "NOT_ESTABLISHED"}


def hardware(key, budgets):
    policy(key, budgets)
    result = subprocess.run(["nvidia-smi", "--query-gpu=index,name,memory.free,driver_version",
        "--format=csv,noheader,nounits"], capture_output=True, text=True, check=True, timeout=5)
    rows = [line.split(",") for line in result.stdout.strip().splitlines()]
    require(len(rows) == 2 and all(len(r) == 4 for r in rows), "EXACT_TWO_PHYSICAL_T4")
    observed = []
    for i, row in enumerate(rows):
        index, name, free, driver = [s.strip() for s in row]
        require(index == str(i) and name in ("Tesla T4", "NVIDIA T4"), "ORDERED_T4_IDENTITIES")
        require(driver in budgets["driver_versions"], "UNAPPROVED_DRIVER")
        require(tuple(map(int, driver.split("."))) >= (525, 60, 13), "CUDA12_DRIVER_FLOOR")
        require(int(free) >= budgets["free_mib_per_gpu"][i], "INDIVIDUAL_GPU_HEADROOM")
        observed.append({"index": i, "name": name, "free_mib": int(free), "driver": driver})
    return {"physical_gpus": observed, "cuda_initialized": False, "model_fit": "NOT_ESTABLISHED"}


def cuda(key, budgets):
    policy(key, budgets)
    count, visible, build = (2, "0,1", "12.8") if key == "qwen3" else (1, "0", "12.4")
    require(os.environ.get("CUDA_VISIBLE_DEVICES") == visible, "WORKER_GPU_VISIBILITY")
    import torch
    require(torch.version.cuda == build and torch.cuda.is_available()
            and torch.cuda.device_count() == count, "WORKER_CUDA_BUILD_COUNT")
    gpus = []
    for i in range(count):
        require(torch.cuda.get_device_capability(i) == (7, 5), "WORKER_T4_CAPABILITY")
        free, total = torch.cuda.mem_get_info(i)
        required = budgets["free_mib_per_gpu"][i]
        if i == 0:
            required = max(required, budgets["free_gpu0_runtime_mib"])
        require(free >= required * 2**20, "WORKER_INDIVIDUAL_GPU_MEMORY")
        tensor = torch.ones(1, device=f"cuda:{i}", dtype=torch.float16)
        require(float(tensor.sum().item()) == 1., "WORKER_FP16_PROBE")
        del tensor
        torch.cuda.synchronize(i)
        gpus.append({"index": i, "free_bytes": free, "total_bytes": total})
    return {"gpus": gpus, "fp16": "MEASURED", "weights_loaded": False, "model_fit": "NOT_ESTABLISHED"}


def software(key, repo=ROOT, wheel_lock=None):
    if key != "qwen3":
        from safeshift.candidates.train_runtime import software as checked
        return checked(key)
    from .qwen import reference, verify_transformers
    lock = reference(repo)
    expected = lock["software"]
    require(os.environ.get("PYTORCH_ALLOC_CONF") == "expandable_segments:True"
            and os.environ.get("PYTORCH_CUDA_ALLOC_CONF") in (None, "expandable_segments:True"), "QWEN_PREIMPORT_ALLOCATOR")
    identity = bootstrap.runtime_identity(os.environ["SAFESHIFT_WORKER_PYTHON"], os.environ["SAFESHIFT_RUNTIME_ROOT"])
    require(platform.python_version() == expected["python"], "QWEN_PYTHON31213")
    require(zlib.ZLIB_VERSION == zlib.ZLIB_RUNTIME_VERSION == expected["zlib"], "QWEN_ZLIB_COMPILED_RUNTIME")
    normalize = lambda n: n.lower().replace("_", "-").replace(".", "-")
    installed = {normalize(d.metadata["Name"]): d.version for d in metadata.distributions()}
    require(type(wheel_lock) is dict and set(wheel_lock) == {"versions", "wheels"}, "QWEN_CLOSED_WHEEL_LOCK_REQUIRED")
    require(installed == wheel_lock["versions"], "QWEN_UNLOCKED_OR_MISSING_DEPENDENCY")
    require(all(installed.get(normalize(n)) == v for n, v in expected.items() if n not in ("python", "zlib")),
            "QWEN_PINNED_DEPENDENCY_MISMATCH")
    import torch, torchvision, transformers
    for module in (torch, torchvision, transformers):
        require(Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()), "QWEN_FOREIGN_LIBRARY")
    require(torch.version.cuda == "12.8", "QWEN_CUDA_BUILD")
    from torchvision.ops import nms
    require(nms(torch.tensor([[0., 0., 1., 1.]]), torch.tensor([1.]), .5).tolist() == [0], "QWEN_COMPILED_NMS_ABI")
    return {"identity": identity, "versions": installed, "sources": verify_transformers(transformers, repo),
            "cuda_build": torch.version.cuda, "compiled_cpu_nms": "PASS", "weights_loaded": False}
