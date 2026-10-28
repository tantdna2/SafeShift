"""Stdlib-only Kaggle supervisor. Grant -> input -> GPU -> isolated env -> worker.

Notebooks call launch(..., mode='PILOT') literally. No promotion from pilot.
"""
import os
import re
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import uuid

from .artifacts import export, import_archive, read, safe, sha, write, write_bytes
from .contract import MODELS, authorize, digest, source_digest
from .manifest import discover, load_bundle
from .report import save_reports
from .runner import error_record
from .backend import check_source_review

SCRATCH_BUDGET_BYTES = 28 * 2**30
OUTPUT_BUDGET_BYTES = 4 * 2**30


def dependency_commands(python, repo, key):
    """Ordered commands shared by bootstrap and the CPU Linux install rehearsal."""
    pip = [str(python), "-m", "pip"]
    return [pip + ["install", "--disable-pip-version-check", "--no-cache-dir", "pip==25.0.1"],
            pip + ["install", "--no-cache-dir", "--index-url", "https://download.pytorch.org/whl/cu124",
                   "torch==2.6.0+cu124", "torchvision==0.21.0+cu124"],
            pip + ["install", "--no-cache-dir", "-r", str(Path(repo) / f"configs/pilot/{key}.requirements.txt")],
            pip + ["check"]]


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
        checked_scratch = checked_root(scratch_root)
        if checked_scratch.is_relative_to(work) or work.is_relative_to(checked_scratch):
            raise ValueError("SCRATCH_OUTPUT_ROOT_OVERLAP")
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


def checked_root(root):
    """Reject aliases in every existing ancestor, including the root itself."""
    root = Path(root).absolute()
    for path in (root, *root.parents):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("STORAGE_ROOT_ALIAS")
    if not root.is_dir():
        raise ValueError("STORAGE_ROOT_MISSING_OR_NOT_DIRECTORY")
    return root


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
    env = {k: v for k, v in os.environ.items() if not k.startswith("PIP_")}
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONUSERBASE", None)
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
    output = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version",
                                      "--format=csv,noheader,nounits"], text=True)
    rows = [[x.strip() for x in line.split(",")] for line in output.strip().splitlines()]
    if (len(rows) != 2 or any(len(r) != 4 or r[0] not in ("Tesla T4", "NVIDIA T4", "T4")
                             or not r[1].isdigit() or not r[2].isdigit()
                             or not 14000 <= int(r[1]) <= 17000 for r in rows)):
        raise RuntimeError("BLOCKED_EXPECTED_TWO_T4_EACH_16GB_NO_POOLED_VRAM")
    if int(rows[0][2]) < 14 * 1024:
        raise RuntimeError("BLOCKED_GPU0_FREE_BELOW_14_GIB")
    return {"physical_gpus": rows, "placement": "GPU0 only; GPU1 unused", "bf16": False,
            "flash_attention": False, "quantization": None}


def supported_runtime():
    return platform.system() == "Linux" and sys.version_info[:2] in ((3, 11), (3, 12))


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
        # Local ledger survives only while filesystem survives. External ledger
        # uniqueness is separately attested in the human-issued grant.
        write(consumption, {"run_id": grant["run_id"], "source_sha256": source_hash,
                            "session": session, "consumed_before_data": True})
        write(output / "grant.json", grant)
        stage = "source_review"
        check_source_review(repo, key)  # Gemma access alone cannot qualify an empty source lock.
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
            checked_scratch = checked_root(scratch_root)
            if checked_scratch.is_relative_to(work) or work.is_relative_to(checked_scratch):
                raise ValueError("SCRATCH_OUTPUT_ROOT_OVERLAP")
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
        stage = "hardware"
        write(output / "gpu_preflight.json", gpu_preflight())
        if not supported_runtime():
            raise RuntimeError("BLOCKED_PINNED_LINUX_PYTHON_311_OR_312_REQUIRED")
        write(output / "host.json", {"python": sys.version, "platform": platform.platform(),
              "scratch_free": shutil.disk_usage(scratch).free, "output_free": shutil.disk_usage(output).free})
        stage = "software"
        runtime = scratch / "venv"
        with (output / "setup.log").open("x", encoding="utf-8") as log:
            def call(args):
                remaining = grant["max_seconds"] - (time.monotonic() - started)
                if remaining <= 0:
                    raise TimeoutError("SETUP_TIME_CAP")
                subprocess.run(args, env=setup_env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=remaining)
            call([sys.executable, "-m", "venv", str(runtime)])
            python = runtime / "bin/python"
            for command in dependency_commands(python, repo, key):
                call(command)
        freeze = subprocess.check_output([str(python), "-m", "pip", "freeze"], text=True, env=setup_env)
        write_bytes(output / "pip_freeze.txt", freeze.encode())
        stage = "worker"
        env = setup_env.copy()
        env.update(PYTHONPATH=str(repo), CUDA_VISIBLE_DEVICES="0", TOKENIZERS_PARALLELISM="false",
                   SAFESHIFT_MODEL_CACHE=str(scratch / "model_cache"), PYTHONDONTWRITEBYTECODE="1",
                   SAFESHIFT_SUPERVISED="1")
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
            write(output / "supervisor_failure.json", {"status": "BLOCKED" if stage in ("authority", "source_review", "dataset", "storage", "hardware", "software") else "FAILED",
                                                       **error_record(error, stage)})
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
                  "supervisor_blocked": blocked, "gpu_experiment_claim": "SEE_ACTUAL_EVIDENCE_ONLY"})
        except BaseException:
            print("SESSION_RECORD_WRITE_FAILED; export still attempted.")
        archive = output.parent / (output.name + ".zip")
        try:
            checksum = export(output, archive)
            print("Download", archive.name, "and", archive.name + ".sha256.json", "SHA256", checksum)
        except BaseException as error:
            # Retain partial ZIP/directory; never pretend successful export.
            print("EXPORT_FAILED", type(error).__name__, "download retained directory/partial archive.")
    return output
