"""One-image engineering execution, isolated from every production series.

Uses the unchanged full manifest, checkpoint, C1, precision, parser and HNLO.
No production history import/reservation, pooling, result selection or retry.
"""
from copy import deepcopy
import math
from pathlib import Path
import re
import time

from safeshift.pilot.artifacts import read, sha, verify_archive
from safeshift.pilot.contract import digest
from .source import require
from . import train_owner as owner

SCHEMA = "safeshift-candidate160-technical-smoke-v1"
DIRECTIVE = "https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6539523161"
MAX_SECONDS = 3600


def execution(key, source, ref):
    value = owner.execution(key, source, ref, owner_start=True)
    value.update(schema=SCHEMA, activation="CODEX_BOUNDED_TECHNICAL_SMOKE",
        owner_decision_record=DIRECTIVE, campaign="technical-smoke-20261031",
        purpose="ENGINEERING_ONLY_EXCLUDED_FROM_SCIENTIFIC_RESULTS", selected_ordinals=[0],
        selection_reason="First image in the unchanged locked TRAIN160 order; initial minimal technical check",
        max_native_calls=1, max_seconds=MAX_SECONDS, expires_unix=value["created_unix"] + MAX_SECONDS,
        run_id=value["run_id"].replace("owner_", "smoke_", 1),
        attempt_id=value["attempt_id"].replace("owner_", "smoke_", 1))
    return value


def validate(value, key, source, ref, *, now=None):
    require(type(value) is dict and value.get("schema") == SCHEMA, "TECHNICAL_SMOKE_SCHEMA")
    expected = execution(key, source, ref)
    require(set(value) == set(expected), "TECHNICAL_SMOKE_FIELDS")
    for name in expected.keys() - {"run_id", "attempt_id", "created_unix", "expires_unix"}:
        require(type(value[name]) is type(expected[name]) and digest(value[name]) == digest(expected[name]),
                "TECHNICAL_SMOKE_BINDING:" + name)
    require(isinstance(value["run_id"], str) and re.fullmatch(f"smoke_{key}_[0-9a-f]{{32}}", value["run_id"])
            and value["attempt_id"] == value["run_id"] + "_a1", "TECHNICAL_SMOKE_IDS")
    now = time.time() if now is None else now
    require(all(type(value[n]) in (int, float) and math.isfinite(value[n])
                for n in ("created_unix", "expires_unix")) and
            value["created_unix"] <= now < value["expires_unix"] == value["created_unix"] + MAX_SECONDS,
            "TECHNICAL_SMOKE_TIME_CAP")
    return value


def selection(rows, grant):
    validate(grant, grant["model_key"], grant["source_sha256"], grant["runtime_ref"])
    return {"purpose": grant["purpose"], "max_images": 1, "max_native_calls": 1,
        "max_seconds": MAX_SECONDS, "manifest_sha256": grant["manifest_sha256"],
        "reason": grant["selection_reason"],
        "samples": [{"ordinal": i, **{n: rows[i][n] for n in
            ("sample_id", "image_sha256", "width", "height")}} for i in grant["selected_ordinals"]]}


def receipt(output, archive, grant):
    """A zero exit code or preflight cannot establish a real smoke PASS."""
    from .train_run import recover, native_custody
    output, archive = Path(output), Path(archive)
    verify_archive(archive)
    require(read(Path(str(archive) + ".sha256.json"))["sha256"] == sha(archive), "SMOKE_ZIP_SIDECAR")
    supervisor = read(output / "supervisor_status.json")
    require(supervisor["failure"] is None and supervisor["attempt_consumed"] is True,
            "SMOKE_SUPERVISOR_FAILURE")
    require(not (output / "finalizer_errors.json").exists() and
            read(output / "cleanup.json")["status"] == "OWNED_SCRATCH_REMOVED", "SMOKE_CLEANUP_REQUIRED")
    require(read(output / "model_load_attempt.json")["load_attempts"] == 1, "SMOKE_ONE_LOAD_REQUIRED")
    hardware = read(output / "worker_cuda.json")
    require(hardware["worker_cuda"] == "MEASURED_FP16_FUNCTIONAL" and hardware["worker_visible_gpus"] == 1,
            "SMOKE_REAL_GPU_REQUIRED")
    summary = read(output / "summary.json")
    require(summary["status"] == "COMPLETED_AWAITING_REVIEW" and summary["metrics"] is None,
            "SMOKE_CONTROLLER_FAILURE")
    rows = read(output / "pilot_manifest.json")["main"]
    results = recover(output, rows, grant)
    require(sum(r["native_calls"] for r in results.values()) == 1, "SMOKE_EXACT_ONE_NATIVE_CALL")
    require(results[rows[0]["sample_id"]]["status"] in ("SUCCESS", "INVALID"), "SMOKE_DURABLE_RESULT_REQUIRED")
    run = output / "calls/000000/run"
    runtime = read(run / "runtime.json")
    require(runtime["native"]["implementation_sha256"] and
            runtime["attention"]["status"] == "EAGER_MODULES_VERIFIED", "SMOKE_NATIVE_LOADED_MODEL_REQUIRED")
    raw_path = run / "samples/000000/raw.json"
    raw = read(raw_path)
    native_custody(raw_path.parent, raw)
    require(raw.get("raw_nonfinite") is False and
            results[rows[0]["sample_id"]]["hnlo"].get("replay_status") != "FAIL", "SMOKE_RAW_HNLO_FAILURE")
    return {"schema": "safeshift-kaggle-technical-smoke-receipt-v1", "status": "TECHNICAL_SMOKE_PASS",
        "run_id": grant["run_id"], "attempt_id": grant["attempt_id"], "model": grant["model"],
        "source_sha256": grant["source_sha256"], "runtime_ref": grant["runtime_ref"],
        "configuration": {n: grant[n] for n in ("legacy_transport_config_sha256", "candidate_execution_config_sha256")},
        "selection": selection(rows, grant), "weights_loaded": True, "native_calls": 1,
        "real_inference": True, "gpu": hardware, "raw_sha256": sha(raw_path),
        "archive_sha256": sha(archive), "hnlo": deepcopy(results[rows[0]["sample_id"]]["hnlo"]),
        "scientific_qualification": "NOT_CLAIMED", "production_history_modified": False,
        "limitations": "One image only; full160, rare sizes and long-run peak VRAM/time remain unverified"}
