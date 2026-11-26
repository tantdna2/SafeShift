"""Fresh preparation diagnostics and reusable bounded environment checks.

No defaults for O5 budgets. Measured observations are separate from supplied
receipts and from execution authority. No model weight load in this module.
"""
import os
from pathlib import Path
import shutil
import uuid

from safeshift.candidates.source import ROOT, require, snapshot_stat
from safeshift.candidates.train_preflight import environment_observation
from safeshift.candidates.fulltrain_preflight import CHECKS, inspect_receipts
from safeshift.pilot.artifacts import write, export, sha, read, verify_archive
from safeshift.pilot.contract import digest
from . import contract


def storage_probe(scratch, output, *, scratch_bytes, output_bytes):
    """Caller supplies reviewed allocation sizes; simultaneous physical writes.

    Files are exclusive and removed in finally, never a recursive cleanup.
    A small CPU test allocation does not establish a full-campaign quota.
    """
    paths = [Path(scratch), Path(output)]
    sizes = [scratch_bytes, output_bytes]
    require(all(type(n) is int and n > 0 for n in sizes), "EXPLICIT_ALLOCATION_BUDGET_REQUIRED")
    for path in paths:
        require(not any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
                        for p in (path, *path.parents)), "STORAGE_ALIAS")
        snapshot_stat(path, directory=True)
    devices = [p.stat().st_dev for p in paths]
    free = [shutil.disk_usage(p).free for p in paths]
    if devices[0] == devices[1]:
        require(min(free) >= sum(sizes), "SHARED_FILESYSTEM_CAPACITY")
    else:
        require(all(a >= n for a, n in zip(free, sizes)), "SEPARATE_FILESYSTEM_CAPACITY")
    created, results = [], []
    block = b"\xa5" * 2**20
    try:
        for directory, n in zip(paths, sizes):
            path = directory / (".fresh-probe-" + uuid.uuid4().hex)
            with path.open("xb") as stream:
                created.append(path)
                remaining = n
                while remaining:
                    written = stream.write(block[:min(len(block), remaining)])
                    require(written > 0, "ALLOCATION_SHORT_WRITE")
                    remaining -= written
                stream.flush()
                os.fsync(stream.fileno())
            info = path.stat()
            require(info.st_size == n, "ALLOCATION_SIZE")
            allocated = info.st_blocks * 512 if hasattr(info, "st_blocks") else None
            require(allocated is None or allocated >= n, "SPARSE_ALLOCATION_NOT_PROOF")
            results.append({"requested_bytes": n, "written_bytes": n, "allocated_bytes": allocated,
                            "device": info.st_dev, "fsync": True})
    finally:
        for path in created:
            path.unlink()  # Exact files owned by this invocation only.
    return {"allocations": results, "same_filesystem": devices[0] == devices[1],
            "cleanup_verified": all(not p.exists() for p in created),
            "scope": "OBSERVED_ALLOCATION_ONLY_NOT_O5_APPROVAL"}


def cpu_native_checks(key, snapshot, repo=ROOT, *, wheel_lock=None):
    """Explicit opt-in in an already pinned public-source CPU environment.

    Uses the production loader on empty/meta weights and synthetic images.
    This function never provisions packages, reads private images or uses GPU.
    """
    from safeshift.candidates.train_runtime import software
    from safeshift.candidates.train_preflight import native_cpu
    from safeshift.candidates import minicpm_resampler_fp32 as numerical
    from safeshift.candidates.source import verify_snapshot
    require(os.environ.get("CUDA_VISIBLE_DEVICES") == "", "CPU_PREFLIGHT_REQUIRES_HIDDEN_CUDA")
    if key == "qwen3":
        from . import environment, qwen
        versions = environment.software(key, repo, wheel_lock)
        processor, tokenizer, probe = qwen.native_setup(snapshot, repo)
        # No meta model or forward needed to validate the actual native processor.
        from PIL import Image
        prompt = (Path(repo) / "configs/pilot/classification_c1.txt").read_text(encoding="utf-8")
        with Image.new("RGB", (448, 448), (128, 128, 128)) as image:
            result = processor.apply_chat_template([{"role": "user", "content": [
                {"type": "image", "image": image}, {"type": "text", "text": prompt}]}], tokenize=True,
                add_generation_prompt=True, return_dict=True, return_tensors="pt")
        require(len(result["input_ids"]) == 1 and all(v.device.type == "cpu" for v in result.values()), "QWEN_CPU_PROCESSOR_OUTPUT")
        return {"software": versions, "tokenizer_t1": probe, "shapes": {k: list(v.shape) for k, v in result.items()},
                "weights_loaded": False, "model_calls": 0, "source": "PUBLIC_PINNED_NATIVE_PROCESSOR"}
    verify_snapshot(snapshot, key)
    versions = software(key)
    native = native_cpu(key, snapshot, repo, implementation=numerical.ID if key == "minicpm4" else None)
    return {"software": versions, "native": native, "weights_loaded": False, "model_calls": 0}


def admit_receipts(key, binding, receipts, hashes):
    result = inspect_receipts(key, binding, receipts, hashes)
    # Keep new authority/campaign semantics; old receipt inspector is structural.
    result.update(runtime_binding="NEW_FRESH_RELEASE_REQUIRED", native=contract.descriptor(key),
                  historical_predictions_required=False)
    return result


def live_preflight(*args, **kwargs):
    # Real Input/provision/GPU diagnostics have not been authorized in this PR.
    contract.authorize()
    from .admission import launch_prepared
    return launch_prepared(*args, diagnostic=True, **kwargs)


def prepare(key, expected_source_sha256, repo, runtime_ref, *, work=None, kind="PREPARATION"):
    """Stdlib-only, repeatable notebook action, no Input or credentials accessed."""
    require(kind in ("PREPARATION", "DIAGNOSTIC"), "PREPARATION_MODE")
    inventory = contract.source_manifest(repo)
    require(digest(inventory) == expected_source_sha256, "FINAL_SOURCE_MISMATCH")
    output = Path(work or Path.cwd() / "data/processed/fresh_fulltrain") / (key + "-" + uuid.uuid4().hex)
    output.mkdir(parents=True, exist_ok=False)
    report = contract.release_report(key)
    report.update(source_sha256=expected_source_sha256, runtime_ref=runtime_ref, kind=kind,
                  attempt_consumed=False, owner_slot_created=False, native_calls=0,
                  measured_checks={n: {"status": "NOT_RUN"} for n in CHECKS},
                  side_effects=["write fresh preparation directory and ZIP/SHA256 only"],
                  caps="O5_PENDING_NO_EXECUTION_DEFAULTS")
    try:
        observed = environment_observation()
        # Shared observation records candidate worker REQUIREMENTS, not observations.
        if key == "qwen3":
            observed["worker"] = {"status": "NOT_MEASURED", "python_required": "3.12.13", "zlib_required": "1.2.11"}
            observed["physical_gpu_count_required"] = 2
            observed["worker_cuda_visible_devices_required"] = "0,1"
        report["measured_checks"]["environment"] = {"status": "PASS", "evidence": observed}
        report["levels"]["ENVIRONMENT_OBSERVED"] = "PASS"
        report["measured_checks"]["source_binding"] = {"status": "PASS", "source_sha256": expected_source_sha256}
        write(output / "environment.json", observed)
        write(output / "source_manifest.json", inventory)
        write(output / "native_contract.json", contract.descriptor(key))
    finally:
        write(output / "release.json", report)
        archive = Path(str(output) + ".zip")
        export(output, archive)
        verify_archive(archive)
        require(read(Path(str(archive) + ".sha256.json"))["sha256"] == sha(archive), "EXPORT_SIDECAR")
    return output
