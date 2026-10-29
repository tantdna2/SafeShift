"""Stdlib-only supervisor. Grant -> CPU runtime -> nvidia-smi -> consume -> worker.

Notebooks call launch(..., mode='PILOT') literally. No promotion from pilot.
"""
import os
import re
import json
import errno
import hashlib
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import uuid
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .artifacts import export, import_archive, read, safe, sha, write, write_bytes
from .contract import MODELS, authorize, digest, source_digest
from .manifest import discover, load_bundle
from .report import save_reports
from .runner import error_record
from .backend import check_source_review

SCRATCH_BUDGET_BYTES = 28 * 2**30
OUTPUT_BUDGET_BYTES = 4 * 2**30
SUPPORTED_PYTHON = ((3, 11), (3, 12))
ESSENTIAL_STDLIB = ("venv", "ssl", "hashlib", "ctypes", "bz2", "lzma", "zlib", "sqlite3")
INTERPRETER_PROBE_MODULES = ESSENTIAL_STDLIB + ("ensurepip",)


def _distribution_name(value):
    return re.sub(r"[-_.]+", "-", value).lower()


def pip_bootstrap_contract(repo):
    """Validate the reviewed pip wheel source and its hash-locked requirement."""
    repo = Path(repo)
    manifest_path = repo / "configs/pilot/pip_bootstrap.json"
    requirement_path = repo / "configs/pilot/pip_bootstrap.requirements.txt"
    value = read(manifest_path)
    pin = value.get("pip", {}) if isinstance(value, dict) else {}
    parsed = urlparse(str(pin.get("url", "")))
    if (value.get("schema") != "safeshift-pip-bootstrap-v1"
            or value.get("method") != "supervisor-pip-python-local-verified-wheel"
            or value.get("controller_minimum_version") != "22.3"
            or pin.get("version") != "25.0.1"
            or pin.get("filename") != "pip-25.0.1-py3-none-any.whl"
            or not isinstance(pin.get("size_bytes"), int) or pin["size_bytes"] <= 0
            or not re.fullmatch(r"[0-9a-f]{64}", str(pin.get("sha256", "")))
            or parsed.scheme != "https" or parsed.hostname != "files.pythonhosted.org"
            or Path(parsed.path).name != pin.get("filename")
            or pin.get("provenance") != "https://pypi.org/pypi/pip/25.0.1/json"):
        raise ValueError("PINNED_PIP_BOOTSTRAP_CONTRACT_INVALID")
    expected = f"pip=={pin['version']} --hash=sha256:{pin['sha256']}"
    if requirement_path.read_text(encoding="utf-8").strip() != expected:
        raise ValueError("PINNED_PIP_BOOTSTRAP_REQUIREMENT_MISMATCH")
    return {**value, "manifest_sha256": sha(manifest_path),
            "requirements_sha256": sha(requirement_path)}


def runtime_contract(repo, key):
    """Bind the requirements text to the exact runtime-version lock."""
    repo = Path(repo)
    expected = read(repo / "configs/pilot/runtime_versions.json")[key]
    requirements = {}
    for raw in (repo / f"configs/pilot/{key}.requirements.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.count("==") != 1:
            raise ValueError("EXACT_REQUIREMENT_PIN_REQUIRED:" + line)
        name, version = line.split("==", 1)
        normalized = _distribution_name(name)
        if normalized in requirements:
            raise ValueError("DUPLICATE_REQUIREMENT_PIN:" + normalized)
        requirements[normalized] = version
    locked = {_distribution_name(name): version for name, version in expected.items()}
    if requirements != locked:
        raise ValueError("REQUIREMENTS_RUNTIME_LOCK_MISMATCH:" + key)
    if (requirements.get("torch") != "2.6.0+cu124"
            or requirements.get("torchvision") != "0.21.0+cu124"):
        raise ValueError("PINNED_CUDA_RUNTIME_CHANGED")
    return {"model_key": key, "python_policy": ["3.11", "3.12"],
            "requirements_sha256": sha(repo / f"configs/pilot/{key}.requirements.txt"),
            "runtime_versions_sha256": sha(repo / "configs/pilot/runtime_versions.json"),
            "pytorch_index": "https://download.pytorch.org/whl/cu124",
            "pins": expected, "pip_bootstrap": pip_bootstrap_contract(repo)}


def interpreter_candidates(kernel=None):
    """Prefer Kaggle's known 3.12/3.11 system interpreters, never Python 3.13."""
    ordered = [Path("/usr/bin/python3.12"), Path("/usr/bin/python3.11"),
               Path(kernel or sys.executable)]
    result = []
    for candidate in ordered:
        value = str(candidate.absolute())
        if value not in result:
            result.append(value)
    return result


def probe_interpreter(python, env=None):
    """Inspect a candidate in its own process without importing notebook packages."""
    code = r'''import importlib, json, platform, struct, sys
names = %r
modules = {}
for name in names:
    try:
        importlib.import_module(name)
        modules[name] = "PASS"
    except BaseException as error:
        modules[name] = type(error).__name__ + ": " + str(error)[:200]
print(json.dumps({"implementation": platform.python_implementation(),
 "version": list(sys.version_info[:3]), "platform": platform.system(),
 "machine": platform.machine(), "pointer_bits": struct.calcsize("P") * 8,
 "executable": sys.executable, "prefix": sys.prefix, "base_prefix": sys.base_prefix,
 "modules": modules}, sort_keys=True))''' % (INTERPRETER_PROBE_MODULES,)
    candidate = Path(python)
    receipt = {"candidate": str(candidate), "eligible": False}
    if not candidate.is_file():
        return {**receipt, "reason": "INTERPRETER_NOT_FOUND"}
    try:
        process = subprocess.run([str(candidate), "-I", "-B", "-c", code], env=env,
                                 text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 timeout=60, check=False)
        if process.returncode:
            return {**receipt, "reason": "INTERPRETER_PROBE_FAILED",
                    "returncode": process.returncode, "stderr": process.stderr[-1000:]}
        value = json.loads(process.stdout.strip().splitlines()[-1])
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired) as error:
        return {**receipt, "reason": "INTERPRETER_PROBE_FAILED",
                "error": type(error).__name__ + ": " + str(error)[:500]}
    version = tuple(value.get("version", [])[:2])
    reasons = []
    if value.get("implementation") != "CPython":
        reasons.append("CPYTHON_REQUIRED")
    if version not in SUPPORTED_PYTHON:
        reasons.append("PYTHON_311_OR_312_REQUIRED")
    if value.get("platform") != "Linux":
        reasons.append("LINUX_REQUIRED")
    if str(value.get("machine", "")).lower() not in ("x86_64", "amd64") or value.get("pointer_bits") != 64:
        reasons.append("LINUX_X86_64_REQUIRED")
    missing = [name for name in ESSENTIAL_STDLIB if value.get("modules", {}).get(name) != "PASS"]
    if missing:
        reasons.append("ESSENTIAL_STDLIB_MISSING:" + ",".join(missing))
    return {**receipt, **value, "eligible": not reasons,
            "reason": "PASS" if not reasons else ";".join(reasons),
            "ensurepip": value.get("modules", {}).get("ensurepip", "NOT_PROBED"),
            "pip_bootstrap_required": value.get("modules", {}).get("ensurepip") != "PASS"}


def select_interpreter(env=None, candidates=None):
    probes = [probe_interpreter(path, env) for path in (candidates or interpreter_candidates())]
    for result in probes:
        if result["eligible"]:
            return Path(result["candidate"]), {"selected": result, "candidates": probes,
                                                "fallback_to_python_313": False}
    error = RuntimeError("BLOCKED_NO_QUALIFIED_PINNED_LINUX_PYTHON_311_OR_312")
    error.interpreter_probes = probes
    raise error


def fetch_pip_bootstrap(repo, scratch):
    """Fetch one exact PyPI wheel with bounded bytes and verify before execution."""
    contract = pip_bootstrap_contract(repo)
    pin = contract["pip"]
    root = Path(scratch) / "pip-bootstrap"
    root.mkdir(mode=0o700, exist_ok=False)
    target = root / pin["filename"]
    receipt = {"status": "BLOCKED", "url": pin["url"], "final_url": None,
               "filename": pin["filename"], "expected_sha256": pin["sha256"],
               "expected_size_bytes": pin["size_bytes"], "received_size_bytes": 0,
               "actual_sha256": None, "provenance": pin["provenance"]}
    digest_value = hashlib.sha256()
    received = 0
    try:
        request = Request(pin["url"], headers={"User-Agent": "SafeShift-pip-bootstrap/1"})
        with urlopen(request, timeout=120) as response, target.open("xb") as stream:
            receipt["final_url"] = response.geturl()
            if receipt["final_url"] != pin["url"] or getattr(response, "status", 200) != 200:
                raise ValueError("PINNED_PIP_BOOTSTRAP_UNEXPECTED_RESPONSE")
            content_length = response.headers.get("Content-Length")
            if content_length is not None and int(content_length) != pin["size_bytes"]:
                raise ValueError("PINNED_PIP_BOOTSTRAP_CONTENT_LENGTH_MISMATCH")
            while block := response.read(1024 * 1024):
                received += len(block)
                if received > pin["size_bytes"]:
                    raise ValueError("PINNED_PIP_BOOTSTRAP_SIZE_OVERFLOW")
                digest_value.update(block)
                stream.write(block)
            stream.flush()
            os.fsync(stream.fileno())
        receipt.update(received_size_bytes=received, actual_sha256=digest_value.hexdigest())
        if received != pin["size_bytes"] or receipt["actual_sha256"] != pin["sha256"]:
            raise ValueError("PINNED_PIP_BOOTSTRAP_CHECKSUM_MISMATCH")
        receipt["status"] = "PASS"
        return target, receipt
    except BaseException as error:
        receipt.update(received_size_bytes=received, actual_sha256=digest_value.hexdigest(),
                       error={"type": type(error).__name__, "message": str(error)[:1000],
                              "errno": getattr(error, "errno", None)})
        error.pip_bootstrap_receipt = receipt
        raise


def pip_controller_probe(env):
    """Qualify only the supervisor pip feature used to target a pip-free venv."""
    command = [str(Path(sys.executable).resolve()), "-I", "-B", "-m", "pip", "--version"]
    process = subprocess.run(command, env=env, text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=60, check=False)
    match = re.search(r"\bpip\s+(\d+)\.(\d+)(?:\.(\d+))?\b", process.stdout)
    version = tuple(map(int, match.groups(default="0"))) if match else ()
    receipt = {"command": command, "returncode": process.returncode,
               "stdout": process.stdout[-1000:], "stderr": process.stderr[-1000:],
               "controller_python": str(Path(sys.executable).resolve()),
               "controller_python_version": list(sys.version_info[:3]),
               "pip_version": ".".join(map(str, version)) if version else None,
               "method": "pip --python", "worker_package_installation": False}
    if process.returncode or version < (22, 3, 0):
        error = RuntimeError("PIP_PYTHON_BOOTSTRAP_CONTROLLER_UNAVAILABLE")
        error.pip_controller_receipt = receipt
        raise error
    return receipt


def pip_bootstrap_command(worker_python, repo, wheel):
    """Use the supervisor only as controller; install solely into worker Python."""
    return [str(Path(sys.executable).resolve()), "-I", "-B", "-m", "pip", "--isolated",
            "--python", str(worker_python), "--disable-pip-version-check", "install",
            "--no-cache-dir", "--no-index", "--find-links", str(Path(wheel).parent),
            "--only-binary=:all:", "--no-deps", "--require-hashes", "-r",
            str(Path(repo) / "configs/pilot/pip_bootstrap.requirements.txt")]


def inspect_worker_pip(python, runtime, expected_version, env):
    """Prove exact pip version and package paths are owned by the target venv."""
    code = r'''import importlib.metadata as metadata, json, pathlib, pip, sys
dist = metadata.distribution("pip")
print(json.dumps({"version": pip.__version__, "metadata_version": dist.version,
 "pip_file": str(pathlib.Path(pip.__file__).resolve()),
 "distribution_root": str(pathlib.Path(dist.locate_file("")).resolve()),
 "executable": str(pathlib.Path(sys.executable).resolve()),
 "prefix": str(pathlib.Path(sys.prefix).resolve()),
 "base_prefix": str(pathlib.Path(sys.base_prefix).resolve()),
 "python_version": list(sys.version_info[:3])}, sort_keys=True))'''
    process = subprocess.run([str(python), "-I", "-B", "-c", code], env=env, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False)
    try:
        value = json.loads(process.stdout.strip().splitlines()[-1]) if not process.returncode else {}
    except (ValueError, IndexError):
        value = {}
    root = Path(runtime).resolve()
    owned_paths = [Path(value.get(name, "")).resolve() for name in
                   ("pip_file", "distribution_root", "executable", "prefix")]
    wrong_python_path = any(re.search(r"python3\.13", str(path), re.IGNORECASE) for path in owned_paths)
    if (process.returncode or value.get("version") != expected_version
            or value.get("metadata_version") != expected_version
            or any(not path.is_relative_to(root) for path in owned_paths)
            or Path(value.get("prefix", "")).resolve() != root
            or Path(value.get("base_prefix", "")).resolve() == root
            or tuple(value.get("python_version", [])[:2]) not in SUPPORTED_PYTHON
            or wrong_python_path):
        error = RuntimeError("WORKER_PIP_IDENTITY_MISMATCH")
        error.worker_pip_receipt = {**value, "returncode": process.returncode,
                                    "stderr": process.stderr[-1000:],
                                    "python313_path_detected": wrong_python_path}
        raise error
    return {**value, "returncode": process.returncode, "python313_path_detected": False}


def runtime_identity(expected_python, expected_root):
    """Called inside the selected venv; reject host/notebook site-package leakage."""
    import site
    expected_python = Path(expected_python).resolve()
    expected_root = Path(expected_root).resolve()
    actual_python = Path(sys.executable).resolve()
    actual_root = Path(sys.prefix).resolve()
    version = sys.version_info[:2]
    site_paths = [Path(p).resolve() for p in sys.path if p and ("site-packages" in p or "dist-packages" in p)]
    foreign = [str(p) for p in site_paths if not p.is_relative_to(expected_root)]
    mismatched = [p for p in sys.path if p and re.search(r"python3\.(?:[0-9]+)", p)
                  and f"python{version[0]}.{version[1]}" not in p]
    if (platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64")
            or version not in SUPPORTED_PYTHON or actual_python != expected_python
            or actual_root != expected_root or Path(sys.base_prefix).resolve() == actual_root
            or foreign or mismatched or site.getusersitepackages() in sys.path
            or os.environ.get("PYTHONNOUSERSITE") != "1"):
        raise RuntimeError("ISOLATED_WORKER_RUNTIME_IDENTITY_MISMATCH")
    return {"python": sys.version, "version": list(version), "implementation": platform.python_implementation(),
            "platform": platform.platform(), "machine": platform.machine(),
            "executable": str(actual_python), "prefix": str(actual_root),
            "base_prefix": str(Path(sys.base_prefix).resolve()), "foreign_site_packages": foreign,
            "mismatched_python_paths": mismatched, "user_site_enabled": site.ENABLE_USER_SITE,
            "notebook_kernel_executable": os.environ.get("SAFESHIFT_NOTEBOOK_PYTHON"),
            "isolated_from_notebook_python": os.environ.get("SAFESHIFT_NOTEBOOK_PYTHON") != str(actual_python)}


def validate_runtime_environment(python, runtime, repo, key, env):
    """Use the future worker process for identity, pin and CPU ABI checks."""
    code = ("import json; from safeshift.pilot.bootstrap import runtime_identity; "
            "from safeshift.pilot.backend import cpu_software_probe; "
            f"print(json.dumps({{'identity': runtime_identity({str(python)!r}, {str(runtime)!r}), "
            f"'software': cpu_software_probe({str(repo)!r}, {key!r})}}, sort_keys=True))")
    process = subprocess.run([str(python), "-B", "-c", code], env=env, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300, check=False)
    if process.returncode:
        error = RuntimeError("PINNED_CPU_SOFTWARE_PREFLIGHT_FAILED:" + process.stderr[-1000:])
        error.cpu_probe_failure = {"returncode": process.returncode,
                                   "stdout": process.stdout, "stderr": process.stderr}
        for name in ("stdout", "stderr"):
            payload = error.cpu_probe_failure[name].encode("utf-8", errors="replace")
            if len(payload) > 8 * 2**20:
                error.cpu_probe_failure[name + "_original_sha256"] = hashlib.sha256(payload).hexdigest()
                error.cpu_probe_failure[name + "_original_bytes"] = len(payload)
                error.cpu_probe_failure[name] = payload[-8 * 2**20:].decode("utf-8", errors="replace")
                error.cpu_probe_failure[name + "_coverage"] = "TAIL_ONLY"
        raise error
    try:
        return json.loads(process.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as error:
        raise RuntimeError("PINNED_CPU_SOFTWARE_PREFLIGHT_INVALID_RECEIPT") from error


def dependency_commands(python, repo, key):
    """Ordered commands shared by bootstrap and the CPU Linux install rehearsal."""
    pip = [str(python), "-I", "-B", "-m", "pip", "--isolated", "--disable-pip-version-check"]
    return [pip + ["install", "--no-cache-dir", "--index-url", "https://download.pytorch.org/whl/cu124",
                   "torch==2.6.0+cu124", "torchvision==0.21.0+cu124"],
            pip + ["install", "--no-cache-dir", "-r", str(Path(repo) / f"configs/pilot/{key}.requirements.txt")],
            pip + ["check"]]


def prepare_runtime(repo, key, scratch, output, setup_env, *, started=None, max_seconds=None,
                    candidates=None):
    """Create and qualify the exact worker runtime before an attempt is consumed."""
    repo, scratch, output = Path(repo), Path(scratch), Path(output)
    receipt = {"schema": "safeshift-cpu-runtime-preflight-v1", "model_key": key,
               "status": "BLOCKED", "attempt_consumed": False, "gpu": "NOT_CALLED",
               "weights": "NOT_DOWNLOADED", "stage": "runtime_contract", "steps": []}
    python = runtime = None
    try:
        receipt["contract"] = runtime_contract(repo, key)
        receipt["stage"] = "interpreter_selection"
        selected, selection = select_interpreter(setup_env, candidates)
        receipt["interpreter_selection"] = selection
        version = selection["selected"]["version"][:2]
        runtime = scratch / ("venv-py" + "".join(map(str, version)))
        python = runtime / "bin/python"
        receipt["stage"] = "venv_creation"
        with (output / "setup.log").open("xb") as log:
            def call(command, stage):
                receipt["stage"] = stage
                if started is not None and max_seconds is not None:
                    remaining = max_seconds - (time.monotonic() - started)
                    if remaining <= 0:
                        raise TimeoutError("CPU_PREFLIGHT_TIME_CAP:" + stage)
                else:
                    remaining = 7200
                began = time.monotonic()
                process = subprocess.run(command, env=setup_env, stdout=log, stderr=subprocess.STDOUT,
                                         check=False, timeout=remaining)
                receipt["steps"].append({"stage": stage, "command": list(map(str, command)),
                                         "returncode": process.returncode,
                                         "seconds": time.monotonic() - began})
                if process.returncode:
                    raise RuntimeError("CPU_RUNTIME_PREFLIGHT_COMMAND_FAILED:" + stage)
            call([str(selected), "-I", "-B", "-m", "venv", "--without-pip", "--copies", str(runtime)],
                 "venv_creation_without_pip")
            venv_probe = probe_interpreter(python, setup_env)
            receipt["venv_interpreter"] = venv_probe
            if (not venv_probe["eligible"] or Path(venv_probe.get("prefix", "")).resolve() != runtime.resolve()
                    or Path(venv_probe.get("base_prefix", "")).resolve() == runtime.resolve()):
                raise RuntimeError("CREATED_VENV_IDENTITY_MISMATCH")
            call([str(python), "-I", "-B", "-c",
                  "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('pip') is None else 9)"],
                 "venv_pip_absent_before_bootstrap")
            receipt["pip_controller"] = pip_controller_probe(setup_env)
            wheel, bootstrap_receipt = fetch_pip_bootstrap(repo, scratch)
            receipt["pip_bootstrap"] = bootstrap_receipt
            call(pip_bootstrap_command(python, repo, wheel), "pip_bootstrap_into_worker")
            receipt["worker_pip"] = inspect_worker_pip(
                python, runtime, receipt["contract"]["pip_bootstrap"]["pip"]["version"], setup_env)
            call([str(python), "-I", "-B", "-m", "pip", "--isolated", "--version"],
                 "worker_pip_version")
            for ordinal, command in enumerate(dependency_commands(python, repo, key)):
                call(command, f"dependency_{ordinal}")
            log.flush()
            os.fsync(log.fileno())
        receipt["setup_log_sha256"] = sha(output / "setup.log")
        receipt["stage"] = "pip_freeze"
        freeze = subprocess.check_output([str(python), "-I", "-B", "-m", "pip", "--isolated",
                                          "freeze", "--all"], text=True,
                                         env=setup_env, timeout=300)
        write_bytes(output / "pip_freeze.txt", freeze.encode())
        receipt["pip_freeze_sha256"] = sha(output / "pip_freeze.txt")
        receipt["stage"] = "cpu_software_probe"
        runtime_env = dict(setup_env)
        runtime_env.update(PYTHONPATH=str(repo), PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
                           SAFESHIFT_WORKER_PYTHON=str(python), SAFESHIFT_RUNTIME_ROOT=str(runtime),
                           SAFESHIFT_NOTEBOOK_PYTHON=str(Path(sys.executable).resolve()),
                           CUDA_VISIBLE_DEVICES="", SAFESHIFT_CPU_DIAGNOSTICS=str(output / "cpu_probe"))
        receipt["qualification"] = validate_runtime_environment(python, runtime, repo, key, runtime_env)
        receipt.update(status="PASS", stage="complete", selected_python=str(selected),
                       worker_python=str(python), runtime_root=str(runtime),
                       kernel_python=str(Path(sys.executable).resolve()),
                       kernel_worker_separated=Path(sys.executable).resolve() != python.resolve())
        return python, runtime_env, receipt
    except BaseException as error:
        if hasattr(error, "cpu_probe_failure"):
            receipt["cpu_probe_failure"] = error.cpu_probe_failure
        if hasattr(error, "pip_bootstrap_receipt"):
            receipt["pip_bootstrap"] = error.pip_bootstrap_receipt
        if hasattr(error, "pip_controller_receipt"):
            receipt["pip_controller"] = error.pip_controller_receipt
        if hasattr(error, "worker_pip_receipt"):
            receipt["worker_pip"] = error.worker_pip_receipt
        receipt["error"] = {"type": type(error).__name__, "message": str(error)[:2000],
                            "errno": getattr(error, "errno", None)}
        if hasattr(error, "interpreter_probes"):
            receipt["interpreter_selection"] = {"selected": None,
                                                  "candidates": error.interpreter_probes,
                                                  "fallback_to_python_313": False}
        raise
    finally:
        write(output / "runtime_preflight.json", receipt)


def filesystem_usage(path):
    """Measure the actual filesystem, including bind mounts sharing st_dev."""
    path = Path(path).resolve(strict=True)
    usage = shutil.disk_usage(path)
    mount = path
    while mount.parent != mount and not os.path.ismount(mount):
        mount = mount.parent
    return {"device": path.stat().st_dev, "mount": str(mount),
            "total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free}


def storage_admission(scratch, output, resume_bytes=0):
    """Observe each filesystem and temporarily allocate both budgets together.

    Resume allowance covers extraction, retained sample copies and their ZIP.
    Group by device so two observations never count the same free bytes twice.
    """
    paths = {"scratch": filesystem_usage(scratch), "output": filesystem_usage(output)}
    needs = {"scratch": SCRATCH_BUDGET_BYTES, "output": OUTPUT_BUDGET_BYTES + 4 * resume_bytes}
    groups = {}
    for name, observed in paths.items():
        group = groups.setdefault(observed["device"], {"roles": [], "required_bytes": 0,
                                                       "free_bytes": observed["free_bytes"]})
        group["roles"].append(name)
        group["required_bytes"] += needs[name]
        group["free_bytes"] = min(group["free_bytes"], observed["free_bytes"])
    result = {"paths": paths, "requirements_bytes": needs, "filesystems": list(groups.values()),
              "resume_uncompressed_bytes": resume_bytes, "admitted": False,
              "allocation": {}, "reason": "INSUFFICIENT_FILESYSTEM_FREE",
              "limitation": "Allocation is released immediately; quotas and free space may change. "
                            "Provider or delayed-write limits and peak usage are not guaranteed."}
    if not all(g["free_bytes"] >= g["required_bytes"] for g in groups.values()):
        return result
    probes = []
    try:
        if not hasattr(os, "posix_fallocate"):
            raise OSError("PHYSICAL_ALLOCATION_UNSUPPORTED")
        for name, path in (("scratch", scratch), ("output", output)):
            probe = Path(path) / (".allocation-probe-" + uuid.uuid4().hex)
            flags = os.O_CREAT | os.O_EXCL | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(probe, flags, 0o600)
            probes.append((fd, probe))
            os.posix_fallocate(fd, 0, needs[name])
            os.fsync(fd)
            info = os.fstat(fd)
            if info.st_size != needs[name] or (hasattr(info, "st_blocks") and info.st_blocks * 512 < needs[name]):
                raise OSError("PHYSICAL_ALLOCATION_NOT_CONFIRMED:" + name)
            result["allocation"][name] = {"requested_bytes": needs[name], "allocated_bytes": info.st_blocks * 512,
                                           "status": "ALLOCATED"}
        result["reason"] = "ALLOCATION_CHECK_PASSED_RELEASED"
        result["admitted"] = True
    except (OSError, ValueError) as error:
        result["reason"] = "ALLOCATION_CHECK_FAILED"
        result["allocation_error"] = {"type": type(error).__name__, "errno": getattr(error, "errno", None),
                                      "message": str(error)}
    finally:
        for fd, probe in reversed(probes):
            try:
                os.close(fd)
                probe.unlink()
            except OSError as error:
                result["admitted"] = False
                result["reason"] = "ALLOCATION_PROBE_CLEANUP_FAILED"
                result.setdefault("cleanup_errors", []).append(str(error))
    return result


def storage_receipt(scratch, output, resume_bytes=0):
    """Always return a failure receipt when observation or permission checks fail."""
    try:
        return storage_admission(scratch, output, resume_bytes)
    except (OSError, ValueError) as error:
        return {"admitted": False, "reason": "OBSERVATION_FAILED",
                "scratch": str(scratch), "output": str(output),
                "error": {"type": type(error).__name__, "errno": getattr(error, "errno", None),
                          "message": str(error)}}


def storage_preflight(work=None, scratch_root=None):
    """CPU-only resource check; never reads grants, inputs or calls a GPU."""
    work = Path(work or "/kaggle/working")
    scratch_root = Path(scratch_root or "/kaggle/tmp")
    session = uuid.uuid4().hex
    try:
        work = checked_root(work)
        output = safe(work, "data/processed/three_vlm_preflight/" + session)
        output.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError) as error:
        print("STORAGE_PREFLIGHT_RECEIPT", json.dumps({"admitted": False, "reason": "OUTPUT_PREPARATION_FAILED",
              "scratch_root": str(scratch_root), "output_root": str(work),
              "error": {"type": type(error).__name__, "errno": getattr(error, "errno", None),
                        "message": str(error)}}, sort_keys=True))
        return None
    scratch = None
    try:
        checked_scratch = provision_scratch_root(work, scratch_root)
        scratch, _ = prepare_scratch(checked_scratch, session)
        result = storage_receipt(scratch, output)
    except (OSError, ValueError) as error:
        result = {"admitted": False, "reason": "SCRATCH_PREPARATION_FAILED",
                  "scratch_root": str(scratch_root), "output": str(output),
                  "error": {"type": type(error).__name__, "errno": getattr(error, "errno", None),
                            "message": str(error)}}
    finally:
        if scratch is not None:
            try:
                cleanup_scratch(scratch_root, scratch, session)
            except (OSError, ValueError) as error:
                result["admitted"] = False
                result["scratch_cleanup_error"] = str(error)
    try:
        receipt_hash = write(output / "storage_preflight.json", result)
        write(output / "storage_preflight.sha256.json", {"sha256": receipt_hash})
    except OSError as error:
        result["admitted"] = False
        result["receipt_write_error"] = str(error)
        print("STORAGE_PREFLIGHT_RECEIPT", json.dumps(result, sort_keys=True))
    print("STORAGE_PREFLIGHT", "PASS" if result["admitted"] else "BLOCKED", result.get("reason"), output)
    return output


def environment_preflight(key, source_hash, repo, work=None, scratch_root=None, candidates=None):
    """Install/qualify one model runtime on CPU without a grant or attempt."""
    if key not in ("phi", "smolvlm2"):
        raise PermissionError("CPU_ENVIRONMENT_PREFLIGHT_PHI_OR_SMOL_ONLY")
    repo = Path(repo).resolve()
    work = checked_root(work or "/kaggle/working")
    scratch_root = Path(scratch_root or "/kaggle/tmp")
    session = uuid.uuid4().hex
    output = safe(work, "data/processed/three_vlm_environment_preflight/" + key + "-" + session)
    output.mkdir(parents=True, exist_ok=False)
    scratch = None
    result = {"schema": "safeshift-kaggle-environment-preflight-v1", "model_key": key,
              "status": "BLOCKED", "attempt_consumed": False, "grant_read": False,
              "dataset_read": False, "gpu": "NOT_CALLED", "weights": "NOT_DOWNLOADED",
              "source_sha256": source_hash, "stage": "source"}
    try:
        if source_digest(repo) != source_hash:
            raise PermissionError("ACTUAL_EMBEDDED_SOURCE_MISMATCH")
        check_source_review(repo, key)
        result["runtime_contract"] = runtime_contract(repo, key)
        result["stage"] = "storage"
        checked_scratch = provision_scratch_root(work, scratch_root)
        scratch, setup_env = prepare_scratch(checked_scratch, session)
        admission = storage_receipt(scratch, output)
        write(output / "storage_admission.json", admission)
        if not admission["admitted"]:
            raise OSError("BLOCKED_FILESYSTEM_COMBINED_HEADROOM_REQUIRED")
        result["stage"] = "runtime"
        _, _, runtime_receipt = prepare_runtime(repo, key, scratch, output, setup_env,
                                                candidates=candidates)
        if runtime_receipt["status"] != "PASS":
            raise RuntimeError("CPU_RUNTIME_PREFLIGHT_DID_NOT_PASS")
        result.update(status="PASS", stage="complete",
                      selected_python=runtime_receipt["selected_python"],
                      worker_python=runtime_receipt["worker_python"],
                      kernel_python=runtime_receipt["kernel_python"],
                      kernel_worker_separated=runtime_receipt["kernel_worker_separated"])
    except BaseException as error:
        result["error"] = {"type": type(error).__name__, "message": str(error)[:2000],
                           "errno": getattr(error, "errno", None)}
    finally:
        if scratch is not None:
            try:
                cleanup_scratch(scratch_root, scratch, session)
            except BaseException as error:
                result["status"] = "BLOCKED"
                result["scratch_cleanup_error"] = type(error).__name__ + ": " + str(error)[:1000]
        write(output / "environment_preflight.json", result)
        archive = output.parent / (output.name + ".zip")
        try:
            checksum = export(output, archive)
            print("ENVIRONMENT_PREFLIGHT", result["status"], key, "Download", archive.name,
                  "and", archive.name + ".sha256.json", "SHA256", checksum)
        except BaseException as error:
            print("ENVIRONMENT_PREFLIGHT_EXPORT_FAILED", type(error).__name__, output)
    return output


def checked_root(root):
    """Reject aliases in every existing ancestor, including the root itself."""
    root = Path(root).absolute()
    for path in (root, *root.parents):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("STORAGE_ROOT_ALIAS")
    if not root.is_dir():
        raise ValueError("STORAGE_ROOT_MISSING_OR_NOT_DIRECTORY")
    return root


def provision_scratch_root(work, root):
    """Validate/create only the sibling tmp root; retain it across sessions.

    Kaggle defaults bind this to /kaggle/tmp under the existing /kaggle parent.
    Explicit work/root arguments support isolated CPU tests, with the same layout.
    Never create ancestors, follow aliases, overwrite an entry or select a fallback.
    """
    work = checked_root(work)
    root = Path(root)
    if not root.is_absolute() or ".." in root.parts or root != work.parent / "tmp":
        raise ValueError("SCRATCH_ROOT_MUST_BE_SIBLING_TMP")
    parent = checked_root(work.parent)
    identity = lambda info: (info.st_dev, info.st_ino)
    parent_identity = identity(parent.lstat())
    parent_fd = root_fd = None
    try:
        if os.name == "posix":
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            parent_fd = os.open(parent, flags)
            if identity(os.fstat(parent_fd)) != parent_identity:
                raise ValueError("SCRATCH_PARENT_CHANGED")
            try:
                os.stat("tmp", dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                try:
                    os.mkdir("tmp", mode=0o700, dir_fd=parent_fd)
                except FileExistsError:
                    pass  # Concurrent creator: open/revalidate; never trust EEXIST.
            checked_root(root)
            root_fd = os.open("tmp", flags, dir_fd=parent_fd)
            root_identity = identity(os.fstat(root_fd))
        else:
            try:
                root.lstat()
            except FileNotFoundError:
                try:
                    root.mkdir(mode=0o700, exist_ok=False)
                except FileExistsError:
                    pass
            checked_root(root)
            root_identity = identity(root.lstat())
        # Detect parent replacement or a different mounted/path entry after mkdir.
        checked_root(parent)
        checked_root(root)
        if identity(parent.lstat()) != parent_identity or identity(root.lstat()) != root_identity:
            raise ValueError("SCRATCH_ROOT_OR_PARENT_CHANGED")
        if not os.access(root, os.W_OK | os.X_OK):
            raise PermissionError(errno.EACCES, "SCRATCH_ROOT_NOT_WRITABLE_OR_SEARCHABLE", str(root))
        return root
    finally:
        if root_fd is not None:
            os.close(root_fd)
        if parent_fd is not None:
            os.close(parent_fd)


def prepare_scratch(root, session):
    """Create a session-owned scratch under the explicit temporary root."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", session):
        raise ValueError("INVALID_SCRATCH_SESSION")
    root = checked_root(root)
    scratch = safe(root, "safeshift-pilot-" + session)
    scratch.mkdir(mode=0o700, exist_ok=False)
    temporary = scratch / "tmp"
    temporary.mkdir()
    # A real exclusive write verifies writability (access() alone is insufficient).
    write(scratch / "location.json", {"scope": "kaggle_tmp", "session": session})
    # The notebook kernel may be Python 3.13 with preloaded site packages. The
    # worker runtime must inherit none of its Python/pip path configuration.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("PIP_") and not k.startswith("PYTHON")}
    return scratch, {**env, "HOME": str(scratch), "TMPDIR": str(temporary), "TMP": str(temporary),
                     "TEMP": str(temporary), "HF_HOME": str(scratch / "hf_home"),
                     "HF_MODULES_CACHE": str(scratch / "hf_modules"),
                     "HF_HUB_CACHE": str(scratch / "hf_hub"),
                     "HUGGINGFACE_HUB_CACHE": str(scratch / "hf_hub"),
                     "TRANSFORMERS_CACHE": str(scratch / "hf_hub"),
                     "HF_XET_CACHE": str(scratch / "hf_xet"),
                     "HF_ASSETS_CACHE": str(scratch / "hf_assets"),
                     "XDG_CACHE_HOME": str(scratch / "xdg_cache"),
                     "TORCH_HOME": str(scratch / "torch_cache"),
                     "TRITON_CACHE_DIR": str(scratch / "triton_cache"),
                     "CUDA_CACHE_PATH": str(scratch / "cuda_cache"),
                     "PYTHONPYCACHEPREFIX": str(scratch / "pycache"),
                     "PYTHONNOUSERSITE": "1",
                     "PIP_CACHE_DIR": str(scratch / "pip_cache"),
                     "PIP_CONFIG_FILE": os.devnull, "PIP_NO_CACHE_DIR": "1"}


def cleanup_scratch(root, scratch, session):
    """Remove only this session's owned runtime/cache, never evidence or inputs.

    Scratch must not become part of Kaggle's saved outputs.
    subprocess.run has returned/killed-and-waited before the finalizer calls this.
    """
    root = checked_root(root)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", session):
        raise ValueError("INVALID_SCRATCH_SESSION")
    expected = safe(root, "safeshift-pilot-" + session)
    if Path(scratch).absolute() != expected or not expected.is_dir():
        raise ValueError("SCRATCH_CLEANUP_SCOPE_MISMATCH")
    marker = safe(expected, "location.json")
    if read(marker) != {"scope": "kaggle_tmp", "session": session}:
        raise ValueError("SCRATCH_CLEANUP_OWNERSHIP_MISMATCH")
    shutil.rmtree(expected)


def gpu_preflight():
    """Observe physical GPUs via nvidia-smi only; never initialize CUDA."""
    command = ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version",
               "--format=csv,noheader,nounits"]
    receipt = {"method": "nvidia-smi", "command": command, "status": "BLOCKED",
               "cuda_validation": "NOT_RUN", "model_execution": "NOT_RUN"}
    try:
        output = subprocess.check_output(command, text=True, stderr=subprocess.STDOUT, timeout=60)
        receipt.update(nvidia_smi_output=output, returncode=0)
        rows = [[x.strip() for x in line.split(",")] for line in output.strip().splitlines()]
        receipt["physical_gpus"] = rows
        if (len(rows) != 2 or any(len(r) != 4 or r[0] not in ("Tesla T4", "NVIDIA T4", "T4")
                                 or not r[1].isdigit() or not r[2].isdigit()
                                 or not 14000 <= int(r[1]) <= 17000 for r in rows)):
            raise RuntimeError("BLOCKED_EXPECTED_TWO_T4_EACH_16GB_NO_POOLED_VRAM")
        if int(rows[0][2]) < 14 * 1024:
            raise RuntimeError("BLOCKED_GPU0_FREE_BELOW_14_GIB")
        return {**receipt, "status": "PASS", "placement": "GPU0 only; GPU1 unused", "bf16": False,
                "flash_attention": False, "quantization": None}
    except BaseException as error:
        receipt["error"] = error_record(error, "hardware")
        receipt["returncode"] = getattr(error, "returncode", receipt.get("returncode"))
        diagnostic = getattr(error, "output", None)
        if diagnostic is not None:
            receipt["nvidia_smi_output"] = (diagnostic.decode("utf-8", errors="replace")
                                            if isinstance(diagnostic, bytes) else diagnostic)
        error.gpu_preflight_receipt = receipt
        raise


def recover_accounting(output, plan):
    """CPU supervisor accounts interrupted/torn worker records without re-inference."""
    root = output / "run"
    if (root / "results.json").exists():
        try:
            return read(root / "results.json")
        except (ValueError, OSError):
            pass
    results = {}
    for i, r in enumerate(plan["main"] + plan["supplement"]):
        sample = root / f"samples/{i:06d}"
        try:
            value = read(sample / "result.json")
        except (ValueError, OSError):
            attempted = (sample / "started.json").exists()
            try:
                start = read(sample / "started.json") if attempted else {}
            except (ValueError, OSError):
                start = {"attempt_count_uncertain": True}
            value = {"status": "TECHNICAL_ERROR" if attempted else "NOT_ATTEMPTED", "label": None,
                     "attempts": start.get("attempts", 1 if attempted else 0),
                     "attempt_count_uncertain": start.get("attempt_count_uncertain", False),
                     "native_calls": start.get("prior_native_calls", 0) + int((sample / "native_call.json").exists()),
                     "reason": "INTERRUPTED_OR_TORN_EVIDENCE" if attempted else "WORKER_NOT_REACHED",
                     "hnlo": {"status": "HNLO_UNVERIFIED", "hnlo": None}}
        results[r["sample_id"]] = value
    return results


def launch(key, source_hash, repo, inputs=None, work=None, mode="PILOT", scratch_root=None):
    """One authorized attempt; all exceptions retain/export available evidence."""
    if key not in MODELS or mode != "PILOT":
        raise PermissionError("NOTEBOOK_PILOT_ONLY_FULL_REQUIRES_SEPARATE_TASK_AND_CLI")
    repo = Path(repo).resolve()
    inputs = Path(inputs) if inputs else Path("/kaggle/input")
    work = checked_root(work or "/kaggle/working")
    scratch_root = Path(scratch_root or "/kaggle/tmp")
    session = uuid.uuid4().hex
    output = safe(work, "data/processed/three_vlm/" + key + "-" + session)
    output.mkdir(parents=True, exist_ok=False)
    stage, plan, grant, blocked, scratch = "authority", None, None, False, None
    attempt_consumed, python, runtime_env = False, None, None
    hardware_receipt = None
    started = time.monotonic()
    try:
        if source_digest(repo) != source_hash:
            raise PermissionError("ACTUAL_EMBEDDED_SOURCE_MISMATCH")
        grant_file = discover(inputs, f"grant_{key}.json")
        grant = read(grant_file)
        if not isinstance(grant, dict):
            raise PermissionError("BLOCKED_NO_NEW_REVIEWED_GRANT")
        # Permission check precedes opening TRAIN master/labels or image bytes.
        authorize(grant, model=key, mode="PILOT", source_hash=source_hash,
                  manifest_hash=grant.get("manifest_sha256"), count=grant.get("max_initial_ids"),
                  parent=grant.get("resume_parent_archive_sha256"))
        for name in ("attempt_id",):
            if not isinstance(grant.get(name), str) or not __import__("re").fullmatch("[A-Za-z0-9_-]{1,100}", grant[name]):
                raise PermissionError("NEW_ATTEMPT_ID_REQUIRED")
        if type(grant.get("max_seconds")) is not int or not 60 <= grant["max_seconds"] <= 43200:
            raise PermissionError("EXPLICIT_TIME_CAP_REQUIRED")
        consumption = work / "data/processed/three_vlm_attempts" / grant["attempt_id"]
        consumption.parent.mkdir(parents=True, exist_ok=True)
        if consumption.exists():
            raise FileExistsError("ATTEMPT_ID_ALREADY_CONSUMED")
        write(output / "grant.json", grant)
        stage = "source_review"
        source_review = check_source_review(repo, key)  # Access alone cannot qualify unread source.
        runtime_lock = runtime_contract(repo, key)
        stage = "dataset"
        bundle = discover(inputs, "bundle.json").parent
        if sha(safe(bundle, "pilot_manifest.json")) != grant["manifest_sha256"]:
            raise PermissionError("APPROVED_CANONICAL_MANIFEST_BYTES_REQUIRED_BEFORE_PARSE")
        plan, rows = load_bundle(bundle, "PILOT", verify_images=False)
        if digest(plan) != grant["manifest_sha256"] or len(rows) != grant["max_initial_ids"]:
            raise PermissionError("APPROVED_MANIFEST_BINDING")
        write(output / "pilot_manifest.json", plan)
        load_bundle(bundle, "PILOT", verify_images=True)
        write(output / "input_verification.json", {"source_sha256": source_hash, "images_verified": len(rows),
                                                   "master_membership_n": 3763, "split": "TRAIN"})
        parent, archive, resume_bytes = None, None, 0
        if grant.get("resume_parent_archive_sha256"):
            stage = "resume"
            archive = discover(inputs, f"resume_{key}.zip")
            if sha(archive) != grant["resume_parent_archive_sha256"]:
                raise ValueError("RESUME_ARCHIVE_HASH")
            import zipfile
            with zipfile.ZipFile(archive) as z:
                resume_bytes = sum(i.file_size for i in z.infolist())
        stage = "storage"
        try:
            checked_scratch = provision_scratch_root(work, scratch_root)
            scratch, setup_env = prepare_scratch(checked_scratch, session)
            admission = storage_receipt(scratch, output, resume_bytes)
        except (OSError, ValueError) as error:
            admission = {"admitted": False, "reason": "SCRATCH_PREPARATION_FAILED",
                         "scratch_root": str(scratch_root), "output": str(output),
                         "error": {"type": type(error).__name__, "errno": getattr(error, "errno", None),
                                   "message": str(error)}}
        write(output / "storage_admission.json", admission)
        if not admission["admitted"]:
            raise OSError("BLOCKED_FILESYSTEM_COMBINED_HEADROOM_REQUIRED")
        if archive:
            stage = "resume"
            parent = import_archive(archive, output / "prior")
        stage = "cpu_runtime_preflight"
        python, runtime_env, runtime_receipt = prepare_runtime(
            repo, key, scratch, output, setup_env, started=started, max_seconds=grant["max_seconds"])
        stage = "hardware"
        try:
            hardware_receipt = {**gpu_preflight(), "attempt_consumed": False}
        except BaseException as error:
            hardware_receipt = {**getattr(error, "gpu_preflight_receipt", {}),
                                "status": "BLOCKED", "attempt_consumed": False,
                                "error": error_record(error, stage)}
            write(output / "gpu_preflight.json", hardware_receipt)
            raise
        write(output / "gpu_preflight.json", hardware_receipt)
        write(output / "host.json", {"notebook_python": sys.version,
              "notebook_executable": str(Path(sys.executable).resolve()),
              "worker_python": str(python.resolve()), "platform": platform.platform(),
              "scratch_free": shutil.disk_usage(scratch).free, "output_free": shutil.disk_usage(output).free})
        write(output / "environment_preflight.json", {
            "schema": "safeshift-pre-consumption-environment-preflight-v1", "status": "PASS",
            "attempt_consumed": False, "ready_for_attempt_consumption": True,
            "model_key": key, "source_sha256": source_hash,
            "source_review": source_review["review_status"], "runtime_contract": runtime_lock,
            "manifest_sha256": digest(plan), "images_verified": len(rows),
            "storage_admission_sha256": sha(output / "storage_admission.json"),
            "runtime_preflight_sha256": sha(output / "runtime_preflight.json"),
            "gpu_preflight_sha256": sha(output / "gpu_preflight.json"),
            "selected_python": runtime_receipt["selected_python"],
            "worker_python": runtime_receipt["worker_python"],
            "kernel_python": runtime_receipt["kernel_python"],
            "kernel_worker_separated": runtime_receipt["kernel_worker_separated"],
            "resume_verified": bool(parent), "gpu": "NVIDIA_SMI_ONLY", "cuda": "NOT_CALLED",
            "weights": "NOT_DOWNLOADED"})
        stage = "attempt_consumption"
        # Local ledger survives only while the filesystem survives. Its exclusive
        # write is the formal boundary after CPU and nvidia-smi receipts are durable.
        write(consumption, {"run_id": grant["run_id"], "source_sha256": source_hash,
                            "session": session, "consumed_after_cpu_preflight": True,
                            "consumed_after_gpu_preflight": True,
                            "gpu_preflight_sha256": sha(output / "gpu_preflight.json"),
                            "environment_preflight_sha256": sha(output / "environment_preflight.json")})
        attempt_consumed = True
        stage = "worker"
        env = runtime_env.copy()
        env.update(PYTHONPATH=str(repo), CUDA_VISIBLE_DEVICES="0", TOKENIZERS_PARALLELISM="false",
                   SAFESHIFT_MODEL_CACHE=str(scratch / "model_cache"), PYTHONDONTWRITEBYTECODE="1",
                   PYTHONNOUSERSITE="1", SAFESHIFT_SUPERVISED="1")
        if key == "gemma" and not env.get("HF_TOKEN"):
            try:
                from kaggle_secrets import UserSecretsClient
                env["HF_TOKEN"] = UserSecretsClient().get_secret("HF_TOKEN")
            except Exception:
                raise PermissionError("BLOCKED_GEMMA_ACCEPT_TERMS_AND_ENABLE_HF_TOKEN_SECRET") from None
        command = [str(python), "-B", "-m", "safeshift.pilot.runner", "--repo", str(repo),
                   "--bundle", str(bundle), "--grant", str(grant_file), "--source-hash", source_hash,
                   "--output", str(output), "--mode", "PILOT"]
        if parent:
            command.extend(["--parent", str(parent)])
        remaining = grant["max_seconds"] - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("TIME_CAP_BEFORE_WORKER")
        with (output / "worker.log").open("x", encoding="utf-8") as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=remaining, check=True)
        print("Worker finished; see report, coverage and per-model conclusion. No FULL TRAIN transition.")
    except BaseException as error:
        blocked = True
        try:
            failure = {"status": "BLOCKED" if stage in ("authority", "source_review", "dataset", "storage",
                                                          "resume", "cpu_runtime_preflight", "attempt_consumption",
                                                          "hardware") else "FAILED",
                       "attempt_consumed": attempt_consumed, **error_record(error, stage)}
            if stage == "hardware" and hardware_receipt is not None:
                # Keep the observation even if its own receipt write was torn.
                failure["gpu_preflight"] = hardware_receipt
            write(output / "supervisor_failure.json", failure)
            preflight = output / "environment_preflight.json"
            if not preflight.exists() and not attempt_consumed:
                write(preflight, {"schema": "safeshift-pre-consumption-environment-preflight-v1",
                                  "status": "BLOCKED", "attempt_consumed": False,
                                  "ready_for_attempt_consumption": False, "model_key": key,
                                  "source_sha256": source_hash, "stage": stage,
                                  "error": error_record(error, stage),
                                  "gpu": "NVIDIA_SMI_ONLY" if stage == "hardware" else "NOT_CALLED",
                                  "cuda": "NOT_CALLED",
                                  "weights": "NOT_DOWNLOADED"})
        except BaseException:
            print("FAILURE_RECORD_WRITE_FAILED; existing evidence retained.")
        print("STOP:", stage, type(error).__name__, "— inspect exported evidence.")
    finally:
        if scratch is not None:
            try:
                cleanup_scratch(scratch_root, scratch, session)
            except BaseException:
                print("SCRATCH_CLEANUP_FAILED: do not publish/save entire working tree; download evidence ZIP only.")
        try:
            if plan is not None:
                # Separate fallback directory avoids overwriting torn reports.
                if not (output / "report" / f"{key}.json").exists():
                    results = recover_accounting(output, plan)
                    save_reports(output / "recovered_report", plan, {key: results}, blocked=True)
        except BaseException as error:
            print("REPORT_FAILED", type(error).__name__, "raw/partial evidence retained for export.")
        try:
            write(output / "session.json", {"session_id": session, "model_key": key, "mode": "PILOT",
                  "source_sha256": source_hash, "seconds": time.monotonic() - started,
                  "supervisor_blocked": blocked, "attempt_consumed": attempt_consumed,
                  "gpu_experiment_claim": "SEE_ACTUAL_EVIDENCE_ONLY"})
        except BaseException:
            print("SESSION_RECORD_WRITE_FAILED; export still attempted.")
        archive = output.parent / (output.name + ".zip")
        try:
            checksum = export(output, archive)
            print("Download", archive.name, "and", archive.name + ".sha256.json", "SHA256", checksum)
        except BaseException as error:
            # Retain partial ZIP/directory; never pretend successful export.
            try:
                write(Path(str(archive) + ".export_failure.json"),
                      {"attempt_consumed": attempt_consumed, **error_record(error, "export")})
            except BaseException:
                pass  # A full/read-only filesystem may prevent every new write.
            print("EXPORT_FAILED", type(error).__name__, "download retained directory/partial archive.")
    return output
