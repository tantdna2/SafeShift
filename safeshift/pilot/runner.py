"""Bounded, stop-on-technical-error engine, separately invoked FULL_TRAIN path."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from .artifacts import Store, read, safe, sha, write, write_bytes
from .contract import MODELS, PROMPT_SHA, authorize, digest, parse_label, settings, source_digest
from .hnlo import replay
from .manifest import load_bundle
from .report import save_reports


def error_record(error, stage):
    message = re.sub(r"hf_[A-Za-z0-9]+", "[REDACTED_TOKEN]", str(error))
    message = re.sub(r"(?:[A-Za-z]:[\\/]|/)(?:[^\s:'\"]+[\\/])+[^\s:'\"]*", "[PATH]", message)
    message = message[:2000]
    name = type(error).__name__
    category = ("ACCESS" if isinstance(error, PermissionError) or getattr(getattr(error, "response", None), "status_code", None) in (401, 403) else
                "OOM" if "out of memory" in str(error).lower() or "OutOfMemory" in name else
                "PREPROCESSING" if stage == "preprocessing" else
                "LIBRARY" if isinstance(error, (ImportError, AttributeError, TypeError)) else "TECHNICAL")
    return {"type": name, "message": message, "stage": stage, "category": category}


def identity(key, plan, rows, source_hash, run_id):
    return {"model_key": key, "model": MODELS[key], "run_id": run_id,
            "manifest_sha256": digest(plan), "config_sha256": digest(settings(key)),
            "source_sha256": source_hash,
            "inputs": [{"sample_id": r["sample_id"], "sha256": r["image_sha256"]} for r in rows]}


def execute(store, rows, backend_factory, grant, key, plan, time_budget=None):
    """Dependency injection exists for CPU tests; production always NativeBackend."""
    results, pending = {}, []
    for i, row in enumerate(rows):
        previous = store.previous(i)
        if previous:
            if previous["status"] == "SUCCESS":
                raw = read(store.parent / f"samples/{i:06d}/raw.json")
                if (parse_label(raw["response"]) != previous["label"]
                        or replay(raw, previous["label"]) != previous["hnlo"]):
                    raise ValueError("RESUME_CLASSIFICATION_OR_HNLO_REPLAY_MISMATCH")
                store.retain(i)
                results[row["sample_id"]] = previous
                continue
            # INVALID/error/interrupted calls are consumed. Never retry implicitly.
            if row["sample_id"] not in grant.get("retry_sample_ids", []):
                store.retain(i)
                results[row["sample_id"]] = previous
                continue
            if previous.get("attempts", 1) >= 2:
                raise PermissionError("AT_MOST_ONE_EXPLICIT_RETRY_PER_ID_IN_V1")
        pending.append((i, row, previous))
    if not set(grant.get("retry_sample_ids", [])) <= {r["sample_id"] for _, r, p in pending if p}:
        raise PermissionError("RETRY_IDS_MUST_BE_PREVIOUSLY_FAILED_PLANNED_IDS")
    started = time.monotonic()
    backend, blocked, active = None, False, None
    try:
        if pending:
            backend = backend_factory()
            write(store.root / "runtime.json", backend.environment)
        for i, row, previous in pending:
            if shutil.disk_usage(store.root).free < 2**30:
                blocked = True
                write(store.root / "stop.json", {"reason": "OUTPUT_FREE_BELOW_1GIB_KEEP_EXPORT_RESERVE", "ordinal": i})
                break
            if time_budget is not None and time.monotonic() - started >= time_budget:
                blocked = True
                write(store.root / "stop.json", {"reason": "TIME_BUDGET_STOP_BEFORE_NEXT_CALL", "ordinal": i})
                break
            active = (i, row, previous)
            attempts = previous.get("attempts", 1) + 1 if previous else 1
            store.start(i, {"sample_id": row["sample_id"], "input_sha256": row["image_sha256"],
                            "attempts": attempts, "attempt_id": grant["attempt_id"],
                            "prior_native_calls": previous.get("native_calls", 0) if previous else 0,
                            "is_retry": previous is not None, "wall_time_unix": time.time()})
            sample_start = time.monotonic()
            value = backend.generate(row["image"], store.root / f"samples/{i:06d}")
            value["identity"] = {"sample_id": row["sample_id"], "run_id": grant["run_id"],
                                 "input_sha256": row["image_sha256"], "model": MODELS[key],
                                 "config_sha256": digest(settings(key)), "manifest_sha256": digest(plan)}
            raw_hash = store.raw(i, value)  # durable before parse/HNLO/report
            label = parse_label(value["response"])
            try:
                h = replay(value, label)
            except Exception as error:
                h = {"status": "HNLO_TECHNICAL_FAILURE", "hnlo": None,
                     "reason": error_record(error, "hnlo_replay"), "replay_status": "FAIL"}
            result = {"status": "SUCCESS" if label else "INVALID", "label": label,
                      "raw_sha256": raw_hash, "attempts": attempts,
                      "native_calls": (previous.get("native_calls", 0) if previous else 0) + 1,
                      "hnlo": h, "seconds": time.monotonic() - sample_start,
                      "generation_seconds": value.get("seconds"), "memory": value.get("memory"),
                      "hnlo_overhead": value.get("hnlo_overhead"), "raw_nonfinite": value.get("raw_nonfinite", False)}
            store.result(i, result)
            results[row["sample_id"]] = result
            active = None
            # HNLO incompatibility/failure never changes a successful classification.
            # Nonfinite model output itself blocks further calls as unreliable.
            if value.get("raw_nonfinite"):
                blocked = True
                write(store.root / "stop.json", {"reason": "NONFINITE_RAW_MODEL_OUTPUT", "ordinal": i})
                break
            if i == 11:
                write(store.root / "early12.json", {"completed_ordinals": list(range(12)),
                      "extra_inference_calls": 0, "technical_gate": "PASS",
                      "hnlo_probe": "SEE_PER_SAMPLE_EVIDENCE; classification continues independently"})
    except BaseException as error:
        blocked = True
        e = error_record(error, getattr(backend, "stage", "model_load"))
        write(store.root / "failure.json", e)
        if active:
            i, row, previous = active
            native = int((store.root / f"samples/{i:06d}/native_call.json").exists())
            result = {"status": "TECHNICAL_ERROR", "label": None,
                      "attempts": previous.get("attempts", 1) + 1 if previous else 1,
                      "native_calls": (previous.get("native_calls", 0) if previous else 0) + native,
                      "error_category": e["category"], "error": e,
                      "hnlo": {"status": "HNLO_UNVERIFIED", "hnlo": None, "reason": "CLASSIFICATION_FAILED"}}
            # A torn result is never overwritten; finalizer accounts it as error.
            if not (store.root / f"samples/{i:06d}/result.json").exists():
                store.result(i, result)
            results[row["sample_id"]] = result
    finally:
        for r in rows:
            results.setdefault(r["sample_id"], {"status": "NOT_ATTEMPTED", "label": None, "attempts": 0, "native_calls": 0,
                                               "hnlo": {"status": "HNLO_UNVERIFIED", "hnlo": None, "reason": "NOT_ATTEMPTED"}})
        write(store.root / "results.json", results)
    return results, blocked


def run(repo, bundle, grant, source_hash, output, mode="PILOT", parent=None):
    run_start = time.monotonic()
    from .backend import NativeBackend, check_software, check_source_review, provision
    from .bootstrap import runtime_identity
    repo, output, bundle = Path(repo), Path(output), Path(bundle)
    key = grant["model_key"]
    expected_python = os.environ.get("SAFESHIFT_WORKER_PYTHON")
    expected_root = os.environ.get("SAFESHIFT_RUNTIME_ROOT")
    if not expected_python or not expected_root:
        raise RuntimeError("SUPERVISED_WORKER_RUNTIME_BINDING_REQUIRED")
    write(output / "worker_runtime_identity.json", runtime_identity(expected_python, expected_root))
    if source_digest(repo) != source_hash:
        raise PermissionError("ACTUAL_RUNTIME_SOURCE_MISMATCH")
    authorize(grant, model=key, mode=mode, source_hash=source_hash, manifest_hash=grant.get("manifest_sha256"),
              count=grant.get("max_initial_ids"), parent=grant.get("resume_parent_archive_sha256") if parent else None)
    check_source_review(repo, key)
    if sha(safe(bundle, "pilot_manifest.json")) != grant["manifest_sha256"]:
        raise PermissionError("APPROVED_CANONICAL_MANIFEST_BYTES_REQUIRED_BEFORE_PARSE")
    plan, rows = load_bundle(bundle, mode, verify_images=False)
    authorize(grant, model=key, mode=mode, source_hash=source_hash, manifest_hash=digest(plan),
              count=len(rows), parent=grant.get("resume_parent_archive_sha256") if parent else None)
    for name, value in (("pilot_manifest.json", plan), ("grant.json", grant)):
        path = output / name
        if path.exists():
            if read(path) != value:
                raise ValueError("EXISTING_RUN_BINDING_CHANGED:" + name)
        else:
            write(path, value)
    load_bundle(bundle, mode, verify_images=True)
    prompt = (repo / "configs/pilot/classification_c1.txt").read_bytes()
    if hashlib.sha256(prompt).hexdigest() != PROMPT_SHA:
        raise ValueError("C1_PROMPT_CHECKSUM")
    store = Store(output / "run", identity(key, plan, rows, source_hash, grant["run_id"]),
                  Path(parent) / "run" if parent else None)
    tokenizer_file = output / "tokenizer/runtime_tokenizer.json"
    if parent and (Path(parent) / "tokenizer/runtime_tokenizer.json").exists():
        write_bytes(tokenizer_file, (Path(parent) / "tokenizer/runtime_tokenizer.json").read_bytes())
    # Input bytes already verified. Worker receives only opaque paths; no GT.
    execution_rows = [{**r, "image": str(bundle / r["image"])} for r in rows]
    def factory():
        from .bootstrap import gpu_preflight
        write(output / "worker_gpu_preflight.json", gpu_preflight())
        import torch
        if torch.cuda.device_count() != 1 or torch.cuda.get_device_capability(0) != (7, 5):
            raise ValueError("ONE_VISIBLE_T4_COMPUTE_75_REQUIRED")
        if not torch.cuda.is_available() or float(torch.ones(1, device="cuda:0", dtype=torch.float16).sum().item()) != 1.0:
            raise RuntimeError("CUDA_FP16_FUNCTIONAL_ADMISSION_FAILED_BEFORE_WEIGHTS")
        versions = check_software(repo, key)
        write(output / "versions.json", versions)
        from PIL import Image
        for row in rows:
            with Image.open(bundle / row["image"]) as image:
                if image.size != (row["width"], row["height"]) or getattr(image, "n_frames", 1) != 1:
                    raise ValueError("ACTUAL_IMAGE_DIMENSIONS_OR_STILL_IMAGE_MISMATCH")
                image.verify()
        # HF_TOKEN provided by Kaggle Secrets via supervisor, never persisted.
        cache = os.environ.get("SAFESHIFT_MODEL_CACHE", str(repo / "data/processed/three_vlm_model_cache"))
        provision_start = time.monotonic()
        snapshot, receipt = provision(repo, key, cache, os_token())
        receipt["provision_seconds"] = time.monotonic() - provision_start
        write(output / "model_snapshot.json", receipt)
        backend = NativeBackend(key, snapshot, prompt.decode())
        if backend.serialized_tokenizer:
            if tokenizer_file.exists():
                if tokenizer_file.read_bytes() != backend.serialized_tokenizer:
                    raise ValueError("RESUME_NATIVE_TOKENIZER_SERIALIZATION_CHANGED")
            else:
                write_bytes(tokenizer_file, backend.serialized_tokenizer)
        return backend
    results, blocked = execute(store, execution_rows, factory, grant, key, plan, grant["max_seconds"])
    failure = read(store.root / "failure.json") if (store.root / "failure.json").exists() else None
    timing = {"worker_total_seconds": time.monotonic() - run_start,
              "runtime": read(store.root / "runtime.json") if (store.root / "runtime.json").exists() else None,
              "checkpoint": read(output / "model_snapshot.json") if (output / "model_snapshot.json").exists() else None}
    save_reports(output / "report", plan, {key: results}, blocked, {key: failure}, {key: timing})
    return results


def os_token():
    import os
    return os.environ.get("HF_TOKEN")


def main():
    p = argparse.ArgumentParser()
    for name in ("repo", "bundle", "grant", "source-hash", "output"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--parent")
    p.add_argument("--resume-archive")
    # FULL_TRAIN is only reachable by a separate explicit invocation and grant.
    p.add_argument("--mode", choices=("PILOT", "FULL_TRAIN"), default="PILOT")
    a = p.parse_args()
    output = Path(a.output)
    supervised = bool(__import__("os").environ.get("SAFESHIFT_SUPERVISED"))
    if output.exists() and not supervised:
        raise FileExistsError("NEW_OUTPUT_DIRECTORY_REQUIRED_NO_OVERWRITE")
    if a.parent and not supervised:
        raise PermissionError("CLI_RESUME_REQUIRES_VERIFIED_ARCHIVE_NOT_DIRECTORY")
    if a.resume_archive and (supervised or a.parent):
        raise PermissionError("ONE_RESUME_MECHANISM_ONLY")
    grant = read(a.grant)
    if supervised:
        run(a.repo, a.bundle, grant, a.source_hash, output, a.mode, a.parent)
        return
    started = time.monotonic()
    try:
        if source_digest(a.repo) != a.source_hash:
            raise PermissionError("ACTUAL_RUNTIME_SOURCE_MISMATCH")
        authorize(grant, model=grant["model_key"], mode=a.mode, source_hash=a.source_hash,
                  manifest_hash=grant.get("manifest_sha256"), count=grant.get("max_initial_ids"),
                  parent=grant.get("resume_parent_archive_sha256") if a.resume_archive else None)
        write(Path(a.repo) / "data/processed/three_vlm_attempts" / grant["attempt_id"],
              {"run_id": grant["run_id"], "source_sha256": a.source_hash, "consumed_before_data": True})
        if a.resume_archive:
            from .artifacts import import_archive
            if source_digest(a.repo) != a.source_hash:
                raise PermissionError("ACTUAL_RUNTIME_SOURCE_MISMATCH")
            authorize(grant, model=grant["model_key"], mode=a.mode, source_hash=a.source_hash,
                      manifest_hash=grant.get("manifest_sha256"), count=grant.get("max_initial_ids"),
                      parent=grant.get("resume_parent_archive_sha256"))
            if sha(a.resume_archive) != grant["resume_parent_archive_sha256"]:
                raise ValueError("RESUME_ARCHIVE_HASH")
            a.parent = import_archive(a.resume_archive, output / "prior")
        output.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "SAFESHIFT_SUPERVISED": "1", "CUDA_VISIBLE_DEVICES": "0"}
        env.update(SAFESHIFT_WORKER_PYTHON=str(Path(sys.executable).resolve()),
                   SAFESHIFT_RUNTIME_ROOT=str(Path(sys.prefix).resolve()),
                   SAFESHIFT_NOTEBOOK_PYTHON=str(Path(sys.executable).resolve()),
                   PYTHONNOUSERSITE="1")
        command = [sys.executable, "-B", "-m", "safeshift.pilot.runner", "--repo", a.repo,
                   "--bundle", a.bundle, "--grant", a.grant, "--source-hash", a.source_hash,
                   "--output", str(output), "--mode", a.mode]
        if a.parent:
            command += ["--parent", str(a.parent)]
        remaining = grant["max_seconds"] - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError("CLI_TIME_CAP_BEFORE_WORKER")
        with (output / "worker.log").open("x", encoding="utf-8") as log:
            subprocess.run(command, env=env, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=remaining)
    except BaseException as error:
        if output.exists():
            write(output / "cli_supervisor_failure.json", error_record(error, "cli_supervisor"))
        raise
    finally:
        # Worker invoked by notebook supervisor: supervisor owns the outer export.
        # Explicit CLI/FULL invocation also gets a durable archive, including failure.
        if output.exists():
            from .artifacts import export
            if (output / "pilot_manifest.json").exists() and not (output / "report").exists():
                from .bootstrap import recover_accounting
                plan = read(output / "pilot_manifest.json")
                save_reports(output / "recovered_report", plan,
                             {grant["model_key"]: recover_accounting(output, plan)}, blocked=True)
            export(output, Path(str(output) + ".zip"))


if __name__ == "__main__":
    main()
