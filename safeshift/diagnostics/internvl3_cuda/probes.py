"""Bounded library/device metadata and direct API results, never a CUDA verdict.

Only run_probe's driver/runtime branches call GPU APIs. All callers must install
the unchanged recovery guards first. Static host metadata never loads a library.
"""
import ctypes
import hashlib
import importlib.metadata
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess

SONAMES = {"cuda": "libcuda.so.1", "nvml": "libnvidia-ml.so.1", "cudart": "libcudart.so.12"}
ENV_KEYS = ("LD_LIBRARY_PATH", "LD_PRELOAD", "CUDA_VISIBLE_DEVICES", "CUDA_DEVICE_ORDER",
            "NVIDIA_VISIBLE_DEVICES", "NVIDIA_DRIVER_CAPABILITIES", "PYTORCH_NVML_BASED_CUDA_CHECK")
MAX_ITEMS = 64


def error_metadata(error):
    row = {"type": type(error).__name__, "errno": getattr(error, "errno", None)}
    if re.fullmatch(r"[A-Z][A-Z0-9_]{1,96}", str(error)):
        row["reason"] = str(error)
    return row


def path_metadata(path, runtime=None):
    text = str(path)
    result = {"sha256": hashlib.sha256(os.fsencode(text)).hexdigest()}
    if runtime is not None and Path(text).is_absolute() and Path(text).is_relative_to(runtime):
        result["path"] = "<runtime>/" + Path(text).relative_to(runtime).as_posix()
    elif re.fullmatch(r"/(?:usr/(?:lib[^/]*|local/(?:cuda[^/]*|nvidia))|lib[^/]*|opt/conda|dev/nvidia[^/]*)(?:/[a-zA-Z0-9_.+/-]+)?", text):
        result["path"] = text
    result["possible_stub_or_compat"] = bool({"stubs", "compat"} & set(Path(text).parts))
    return result


def environment_metadata(env, runtime=None):
    result = {}
    for key in ENV_KEYS:
        value = env.get(key)
        row = {"present": value is not None}
        if value is not None:
            row["sha256"] = hashlib.sha256(os.fsencode(value)).hexdigest()
            if key == "LD_LIBRARY_PATH":
                parts = value.split(":")
                row.update(directories=[path_metadata(p, runtime) for p in parts[:MAX_ITEMS]],
                           truncated=len(parts) > MAX_ITEMS, empty_component="" in parts)
            elif key != "LD_PRELOAD" and re.fullmatch(r"[a-zA-Z0-9_,.:-]{0,128}", value):
                row["value"] = value
        result[key] = row
    return result


def command_output(args):
    # Read-only utilities; export only parsed rows, never stderr/whole output.
    try:
        process = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 text=True, timeout=10, check=False)
        if process.returncode != 0 or len(process.stdout) > 1024 * 1024:
            return None, {"returncode": process.returncode, "reason": "UTILITY_FAILED_OR_OUTPUT_LIMIT"}
        return process.stdout, None
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, error_metadata(error)


def linker_cache(runtime=None):
    tool = shutil.which("ldconfig") or next((p for p in ("/sbin/ldconfig", "/usr/sbin/ldconfig") if Path(p).is_file()), None)
    if not tool:
        return {"status": "UNOBSERVABLE", "entries": []}
    text, error = command_output([tool, "-p"])
    entries = []
    for line in (text or "").splitlines():
        fields = line.strip().split()
        if fields and fields[0] in SONAMES.values() and "=>" in fields:
            entries.append({"soname": fields[0], "target": path_metadata(fields[-1], runtime)})
    return {"status": "UNOBSERVABLE" if error else "OBSERVED", "entries": entries[:MAX_ITEMS],
            "truncated": len(entries) > MAX_ITEMS, "error": error}


def file_metadata(path, runtime=None):
    row = {"requested": path_metadata(path, runtime)}
    try:
        info = Path(path).lstat()
        target = Path(path).resolve(strict=True)
        resolved = target.stat()
        row.update(status="OBSERVED", symlink=stat.S_ISLNK(info.st_mode),
                   target=path_metadata(target, runtime), size_bytes=resolved.st_size,
                   inode=resolved.st_ino, mode=stat.S_IMODE(resolved.st_mode))
        if stat.S_ISREG(resolved.st_mode):
            with target.open("rb") as stream:
                row["elf_magic"] = stream.read(4) == b"\x7fELF"
            tool = shutil.which("readelf")
            if tool and row["elf_magic"]:
                text, error = command_output([tool, "-d", str(target)])
                row["dynamic"] = {"needed": re.findall(r"\(NEEDED\).*?\[([a-zA-Z0-9_.+-]+)\]", text or "")[:MAX_ITEMS],
                                  "search_paths": [path_metadata(v, runtime) for p in re.findall(r"\((?:RUNPATH|RPATH)\).*?\[(.*?)\]", text or "") for v in p.split(":")][:MAX_ITEMS],
                                  "error": error}
    except (OSError, RuntimeError) as error:
        row.update(status="UNOBSERVABLE", error=error_metadata(error))
    return row


def cudart_path():
    # This is the pinned wheel's actual Runtime, not a system/host substitution.
    distribution = importlib.metadata.distribution("nvidia-cuda-runtime-cu12")
    return Path(distribution.locate_file("nvidia/cuda_runtime/lib/libcudart.so.12"))


def devices(root=Path("/dev")):
    rows = []
    for name in ("nvidiactl", "nvidia0", "nvidia1", "nvidia-uvm", "nvidia-uvm-tools"):
        path = root / name
        row = {"node": name, "access_scope": "STAT_AND_ACCESS_NOT_OPEN_IOCTL_OR_CGROUP_PROOF"}
        try:
            info = path.stat()
            row.update(status="OBSERVED", character_device=stat.S_ISCHR(info.st_mode),
                       major=os.major(info.st_rdev), minor=os.minor(info.st_rdev),
                       mode=stat.S_IMODE(info.st_mode), uid=info.st_uid, gid=info.st_gid,
                       readable=os.access(path, os.R_OK), writable=os.access(path, os.W_OK))
        except OSError as error:
            row.update(status="UNOBSERVABLE", error=error_metadata(error))
        rows.append(row)
    return rows


def static_metadata(origin, runtime=None):
    cache = linker_cache(runtime)
    paths = set()
    for item in cache["entries"]:
        if "path" in item["target"]:
            paths.add(item["target"]["path"])
    directories = os.environ.get("LD_LIBRARY_PATH", "").split(":")
    directories += ["/usr/lib/x86_64-linux-gnu", "/usr/lib64", "/usr/local/nvidia/lib64", "/usr/local/cuda/lib64", "/lib/x86_64-linux-gnu"]
    for directory in directories[:MAX_ITEMS]:
        if directory and Path(directory).is_absolute():
            paths.update(str(Path(directory) / name) for name in SONAMES.values())
    try:
        paths.add(str(cudart_path()))
    except importlib.metadata.PackageNotFoundError:
        pass
    return {"origin": origin, "scope": "STATIC_ONLY_NO_LIBRARY_LOAD_OR_GPU_API", "pid": os.getpid(),
            "ppid": os.getppid(), "uid": os.getuid(), "gid": os.getgid(),
            "platform": platform.system(), "architecture": platform.machine(), "python": platform.python_version(),
            "environment": environment_metadata(os.environ, runtime), "linker_cache": cache,
            "libraries": [file_metadata(p, runtime) for p in sorted(paths)[:MAX_ITEMS]],
            "library_candidates_truncated": len(paths) > MAX_ITEMS, "devices": devices(),
            "inherited_seccomp": next((line.strip() for line in Path("/proc/self/status").read_text().splitlines() if line.startswith("Seccomp:")), "UNKNOWN")}


def mapped_libraries(runtime=None):
    paths = set()
    try:
        for line in Path("/proc/self/maps").read_text().splitlines():
            fields = line.split(maxsplit=5)
            if len(fields) == 6 and any(name in Path(fields[5]).name for name in ("libcuda", "libnvidia-ml", "libcudart")):
                paths.add(fields[5])
        return {"status": "OBSERVED", "paths": [path_metadata(p, runtime) for p in sorted(paths)[:MAX_ITEMS]]}
    except OSError as error:
        return {"status": "UNOBSERVABLE", "error": error_metadata(error)}


def load_library(kind, runtime=None):
    path = str(cudart_path()) if kind == "cudart" else SONAMES[kind]
    row = {"kind": kind, "requested": path_metadata(path, runtime), "initialization_called": False}
    try:
        handle = ctypes.CDLL(path, mode=os.RTLD_LOCAL | os.RTLD_NOW, use_errno=True)
        row["status"] = "LOADED"
        names = {"cuda": ("cuInit", "cuDeviceGetCount"), "nvml": ("nvmlInit", "nvmlDeviceGetCount_v2"),
                 "cudart": ("cudaGetDeviceCount",)}[kind]
        row["required_symbols"] = {name: hasattr(handle, name) for name in names}
        if not all(row["required_symbols"].values()):
            row["status"], handle = "MISSING_REQUIRED_SYMBOL", None
    except OSError as error:
        handle = None
        # dlerror can contain arbitrary paths. Retain a category, not raw text.
        text = str(error)
        category = next((s for s in ("undefined symbol", "cannot open shared object file", "wrong ELF class", "version") if s in text), "OTHER_LOADER_ERROR")
        row.update(status="LOAD_FAILED", error=error_metadata(error), loader_category=category)
    row["mapped_libraries"] = mapped_libraries(runtime)
    return handle, row


def api_result(handle, name, args, argtypes):
    function = getattr(handle, name)
    function.argtypes, function.restype = argtypes, ctypes.c_int
    ctypes.set_errno(0)
    code = int(function(*args))
    return {"api": name, "code": code, "errno_after_call": ctypes.get_errno(),
            "errno_scope": "NOT_A_SYSCALL_TRACE_OR_CUDA_ERROR_SUBSTITUTE"}


def run_probe(stage, runtime=None):
    from .contract import STAGES
    if stage not in STAGES:
        raise ValueError("UNKNOWN_DIAGNOSTIC_STAGE")
    if stage == "metadata":
        return static_metadata("GUARDED_WORKER", runtime)
    kind = {"load_cuda": "cuda", "load_nvml": "nvml", "load_cudart": "cudart",
            "cuinit": "cuda", "runtime_count": "cudart"}[stage]
    handle, row = load_library(kind, runtime)
    if handle is None or stage.startswith("load_"):
        return row
    if stage == "cuinit":
        result = api_result(handle, "cuInit", (0,), [ctypes.c_uint])
        row.update(initialization_called=True, initialization=result)
        if result["code"] == 0:
            count = ctypes.c_int(-1)
            result = api_result(handle, "cuDeviceGetCount", (ctypes.byref(count),), [ctypes.POINTER(ctypes.c_int)])
            row.update(device_count_result=result, device_count=count.value if result["code"] == 0 else None)
    elif stage == "runtime_count":
        count = ctypes.c_int(-1)
        result = api_result(handle, "cudaGetDeviceCount", (ctypes.byref(count),), [ctypes.POINTER(ctypes.c_int)])
        row.update(initialization_called=True, device_count_result=result,
                   device_count=count.value if result["code"] == 0 else None)
    else:
        raise ValueError("UNKNOWN_DIAGNOSTIC_STAGE")
    row["mapped_libraries"] = mapped_libraries(runtime)
    return row
