"""Owner-run, offline T4x2 technical smoke. No capability scores or fallback."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import socket
import shlex
import subprocess
import sys
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.provision_qwen3vl_snapshot import (
    MODEL_ID, REVISION, cached_snapshot, sha256_file, verify_weights, weight_files, write_json,
)
from safeshift.runners.contracts import ErrorCode, Request, RunContext, Task, execute_call
from safeshift.runners.qwen3_vl import Qwen3VLRunner, Qwen3VLAdapter
from safeshift.runners.storage import FileRawStore

PLAN = "configs/pre_freeze/qwen_kaggle_smoke.v1.json"
ARTIFACTS = "data/processed/runtime_validation/w2_qwen_kaggle_smoke"
GENERATOR_VERSION = "runtime-smoke-geometry-v1"
PROMPT = ("You are performing an interface smoke test. Inspect the image and return exactly "
          "one JSON object with one key named safety_level. Its value must be one of: "
          "Level01, Level02, Level03, Level04. Do not output markdown or any other text.")
CASE_IDS = ["RUNTIME_SMOKE_01", "RUNTIME_SMOKE_02"]


def expected_plan():
    return {"schema_version": "qwen-kaggle-smoke-plan-v1",
            "status": "PRE_RUNTIME_VALIDATION_PLAN",
            "scope": "SMOKE_ONLY_TECHNICAL_CONFIGURATION", "platform": "KAGGLE",
            "accelerator": "T4_X2", "model_id": MODEL_ID, "revision": REVISION,
            "precision": "FP16", "quantization": "NONE", "device": {"placement": "auto"},
            "preprocessing": {"mode": "official_processor"},
            "attention": "native_default", "transformers": "4.57.1",
            "decoding": {"do_sample": False, "max_new_tokens": 32},
            "prompt": PROMPT, "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(),
            "case_ids": CASE_IDS, "generator_version": GENERATOR_VERSION,
            "protocol_freeze_commit_sha": "PENDING"}


def load_plan(repo=ROOT):
    plan = json.loads((repo / PLAN).read_text(encoding="utf-8"))
    # Exact equality prevents CLI overrides, extra inputs, and opportunistic tuning.
    if json.dumps(plan, sort_keys=True) != json.dumps(expected_plan(), sort_keys=True):
        raise ValueError("SMOKE_PLAN_CHANGED")
    return plan


def generate_cases(repo=ROOT):
    from PIL import Image, ImageDraw

    provenance = json.loads((repo / "configs/pre_freeze/external_gate_cases.v1.provenance.json")
                            .read_text(encoding="utf-8"))
    gate_hashes = {i["sha256"] for i in provenance["images"]}
    if len(gate_hashes) != 8:
        raise ValueError("EXPECTED_EIGHT_SYNTHETIC_V1_HASHES")
    cases = []
    for index, sample in enumerate(CASE_IDS):
        with Image.new("RGB", (224, 192), "white" if index == 0 else (160, 160, 160)) as image:
            draw = ImageDraw.Draw(image)
            if index == 0:
                draw.rectangle((17, 23, 91, 137), fill=(27, 99, 203))
                draw.ellipse((123, 58, 195, 130), fill=(231, 71, 37))
            else:
                draw.polygon([(21, 151), (87, 29), (143, 151)], fill=(143, 47, 181))
                draw.rectangle((165, 41, 204, 163), fill=(31, 193, 127))
            stream = BytesIO()
            image.save(stream, format="PNG", optimize=False, compress_level=9)
        raw = stream.getvalue()
        digest = hashlib.sha256(raw).hexdigest()
        if digest in gate_hashes:
            raise ValueError("SYNTHETIC_V1_HASH_COLLISION")
        cases.append((raw, {"sample_id": sample, "sha256": digest, "width": 224,
                            "height": 192, "generator_version": GENERATOR_VERSION,
                            "generator_sha256": sha256_file(repo / "scripts/w2_qwen_kaggle_smoke.py")}))
    if len({meta["sha256"] for _, meta in cases}) != 2:
        raise ValueError("SMOKE_IMAGES_NOT_DISTINCT")
    return cases


def probe_hardware(torch):
    query = subprocess.run(["nvidia-smi", "--query-gpu=name,uuid,driver_version,memory.total",
                            "--format=csv,noheader,nounits"], check=True,
                           capture_output=True, text=True).stdout
    rows = []
    for line in query.strip().splitlines():
        name, uuid, driver, memory = [v.strip() for v in line.split(",")]
        rows.append({"name": name, "uuid": uuid, "driver_version": driver,
                     "memory_total_mib": int(memory)})
    gpus = []
    for i in range(torch.cuda.device_count()):
        properties = torch.cuda.get_device_properties(i)
        gpus.append({"index": i, "name": properties.name,
                     "total_memory_bytes": properties.total_memory,
                     "compute_capability": [properties.major, properties.minor]})
    return {"nvidia_smi": rows, "cuda_available": torch.cuda.is_available(),
            "gpu_count": len(gpus), "gpus": gpus}


def require_t4_pair(hardware):
    if not hardware["cuda_available"] or hardware["gpu_count"] != 2:
        raise ValueError("REQUIRES_TWO_CUDA_GPUS")
    for rows in (hardware["gpus"], hardware["nvidia_smi"]):
        if len(rows) != 2 or any(not re.search(r"\bT4\b", r["name"]) for r in rows):
            raise ValueError("REQUIRES_TWO_T4_GPUS")
    if any(g["compute_capability"] != [7, 5] for g in hardware["gpus"]):
        raise ValueError("T4_COMPUTE_CAPABILITY_MISMATCH")


def software_versions(torch):
    versions = {name: importlib.metadata.version(name) for name in
                ("transformers", "accelerate", "huggingface_hub", "safetensors", "pillow")}
    versions.update(python=platform.python_version(), torch=str(torch.__version__),
                    cuda_runtime=torch.version.cuda, zlib=zlib.ZLIB_RUNTIME_VERSION)
    return versions


def memory_snapshot(torch, stage):
    rows = []
    for i in range(2):
        free, total = torch.cuda.mem_get_info(i)
        rows.append({"gpu": i, "free_bytes": free, "total_bytes": total,
                     "max_memory_allocated": torch.cuda.max_memory_allocated(i),
                     "max_memory_reserved": torch.cuda.max_memory_reserved(i)})
    return {"stage": stage, "gpus": rows}


def inspect_device_map(mapping):
    normalized = {str(k): (f"cuda:{v}" if type(v) is int or str(v).isdigit() else str(v))
                  for k, v in mapping.items()}
    devices = set(normalized.values())
    if not devices or "disk" in devices:
        raise ValueError("DISK_OFFLOAD_OR_MISSING_DEVICE_MAP")
    if not devices <= {"cuda:0", "cuda:1", "cpu"} or not devices & {"cuda:0", "cuda:1"}:
        raise ValueError("UNEXPECTED_DEVICE_PLACEMENT")
    notes = []
    if "cpu" in devices:
        notes.append("RUNTIME_NOTE_CPU_OFFLOAD")
    if not {"cuda:0", "cuda:1"} <= devices:
        notes.append("RUNTIME_NOTE_BOTH_GPUS_NOT_USED_REVIEW_REQUIRED")
    return normalized, notes


def block_network(*args, **kwargs):
    raise RuntimeError("NETWORK_FORBIDDEN_DURING_SMOKE")


def run_smoke(run_id, *, repo=ROOT, rerun_of=None, rerun_reason=None,
              runner_factory=Qwen3VLRunner, torch_module=None):
    """Injection points are offline tests only; CLI always uses the real runner."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
        raise ValueError("INVALID_RUN_ID")
    if bool(rerun_of) != bool(rerun_reason):
        raise ValueError("RERUN_REQUIRES_PREVIOUS_ID_AND_REASON")
    root = FileRawStore(repo, ARTIFACTS + "/" + run_id).root
    if root.parent.exists() and any(root.parent.glob("*/runtime_report.json")) and not rerun_of:
        raise ValueError("EXISTING_ATTEMPT_REQUIRES_RERUN_ID_AND_REASON")
    root.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": "qwen-kaggle-runtime-report-v1", "run_id": run_id,
              "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "git_commit": None, "model_id": MODEL_ID, "revision": REVISION,
              "smoke_config_sha256": None, "prompt_sha256": None, "images": [],
              "weight_verification": None, "hardware": None, "software_versions": {},
              "environment": {}, "precision": "FP16", "quantization": "NONE",
              "decoding": {"do_sample": False, "max_new_tokens": 32}, "device_map": {},
              "normalized_device_map": {}, "attention_implementation": None,
              "memory": [], "calls": [], "notes": [], "blocker": None,
              "rerun_of": rerun_of, "rerun_reason": rerun_reason,
              "status": "RUNTIME_SMOKE_FAIL", "protocol_freeze_commit_sha": "PENDING",
              "load_lifecycles": 0, "native_generate_calls": 0, "native_errors": [],
              "runtime_check_failure": None,
              "network_policy": "OFFLINE_ENV_AND_SOCKET_CONNECTION_DENIAL"}
    stage = "PLAN"
    try:
        plan = load_plan(repo)
        report["smoke_config_sha256"] = sha256_file(repo / PLAN)
        report["prompt_sha256"] = plan["prompt_sha256"]
        report["git_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        # Fail before importing the ML stack or resolving the local snapshot.
        stage = "OFFLINE_PREFLIGHT"
        report["environment"] = {k: os.environ.get(k) for k in
                                 ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "CUDA_VISIBLE_DEVICES",
                                  "HF_HUB_DISABLE_TELEMETRY", "PYTORCH_CUDA_ALLOC_CONF")}
        if any(os.environ.get(k) != "1" for k in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")):
            raise ValueError("SET_OFFLINE_VARIABLES_BEFORE_PROCESS_START")
        with patch.object(socket.socket, "connect", block_network), \
                patch.object(socket.socket, "connect_ex", block_network), \
                patch.object(socket, "create_connection", block_network):
            stage = "ENVIRONMENT_PREFLIGHT"
            if torch_module is None:
                import torch as torch_module
            torch = torch_module
            report["software_versions"] = software_versions(torch)
            if report["software_versions"]["transformers"] != "4.57.1":
                raise ValueError("REQUIRES_TRANSFORMERS_4_57_1")
            report["hardware"] = probe_hardware(torch)
            require_t4_pair(report["hardware"])
            stage = "LOCAL_WEIGHT_VERIFICATION"
            verification = verify_weights(cached_snapshot(), weight_files(repo))
            report["weight_verification"] = verification
            write_json(root / "weight_verification.json", verification)
            if not verification["LOCAL_WEIGHT_BYTES_VERIFIED"]:
                raise ValueError("LOCAL_WEIGHT_HASH_MISMATCH")
            cases = generate_cases(repo)
            report["images"] = [meta for _, meta in cases]
            for raw, meta in cases:
                (root / (meta["sample_id"] + ".png")).write_bytes(raw)
            for i in range(2):
                torch.cuda.reset_peak_memory_stats(i)
            report["memory"].append(memory_snapshot(torch, "before_load"))
            runner = runner_factory()
            store = FileRawStore(repo, ARTIFACTS + "/" + run_id + "/raw")
            original_load = runner.load
            loaded_model = None

            def observed_load(context):
                nonlocal loaded_model
                try:
                    original_load(context)
                except Exception as exc:
                    report["native_errors"].append({"stage": "load", "exception_type": type(exc).__name__})
                    raise
                model = runner._resources[1]  # Read-only inspection of the real runner lifecycle.
                if loaded_model is not None:
                    if model is not loaded_model:
                        raise ValueError("MODEL_RELOADED_BETWEEN_CALLS")
                    return
                loaded_model = model
                report["load_lifecycles"] += 1
                report["device_map"] = {str(k): str(v) for k, v in model.hf_device_map.items()}
                report["memory"].append(memory_snapshot(torch, "after_load"))
                try:
                    normalized, notes = inspect_device_map(model.hf_device_map)
                except ValueError as exc:
                    report["runtime_check_failure"] = str(exc)
                    raise
                report["normalized_device_map"] = normalized
                report["notes"].extend(notes)
                attention = getattr(model.config, "_attn_implementation", None)
                report["attention_implementation"] = attention
                if attention == "flash_attention_2":
                    report["runtime_check_failure"] = "FLASH_ATTENTION_2_FORBIDDEN"
                    raise ValueError("FLASH_ATTENTION_2_FORBIDDEN")
                native_generate = model.generate

                def observed_generate(*args, **kwargs):
                    # Only instrumentation: the runner remains the sole caller.
                    report["native_generate_calls"] += 1
                    try:
                        return native_generate(*args, **kwargs)
                    except Exception as exc:
                        report["native_errors"].append({"call_number": report["native_generate_calls"],
                                                        "exception_type": type(exc).__name__})
                        raise

                model.generate = observed_generate

            runner.load = observed_load
            stage = "EXECUTE_CALL"
            for index, (raw, meta) in enumerate(cases, 1):
                command = ["python", "scripts/w2_qwen_kaggle_smoke.py", "--run-id", run_id]
                if rerun_of:
                    command.extend(["--rerun-of", rerun_of, "--rerun-reason", rerun_reason])
                context = RunContext(run_id, f"call_{index:02d}", plan["decoding"],
                                     plan["preprocessing"], plan["precision"], plan["quantization"],
                                     plan["device"], report["software_versions"], report["git_commit"],
                                     shlex.join(command),
                                     "HANDCRAFTED_RUNTIME_SMOKE", input_provenance=meta)
                request = Request(Task.CLASSIFICATION, meta["sample_id"], meta["sample_id"],
                                  raw, "runtime-smoke-prompt-v1", plan["prompt"])
                result = execute_call(runner, Qwen3VLAdapter(), store, request, context)
                row = {"call_id": context.call_id, "sample_id": request.sample_id,
                       "parse_status": result.parse_status.value,
                       "error": asdict(result.error) if result.error else None,
                       "model_revision": REVISION, "runner_version": runner.version,
                       "raw_output": None, "metadata": None,
                       "cache_state_cleared": loaded_model is not None
                       and loaded_model.model.rope_deltas is None
                       and getattr(loaded_model, "_cache", None) is None}
                report["calls"].append(row)
                if result.raw_output:
                    path = repo / result.raw_output.path
                    row["raw_output"] = {"path": result.raw_output.path, "sha256": sha256_file(path)}
                    metadata = path.with_name("metadata.json")
                    row["metadata"] = {"path": metadata.relative_to(repo).as_posix(),
                                       "sha256": sha256_file(metadata)}
                store.save_result(result)
                report["memory"].append(memory_snapshot(torch, f"after_call_{index}"))
                if result.error and result.error.code == ErrorCode.INVALID_CLASSIFICATION:
                    report["notes"].append("CLASSIFICATION_PARSE_INVALID")
                elif result.error is not None:
                    report["blocker"] = {**asdict(result.error),
                                         "runtime_check_failure": report["runtime_check_failure"],
                                         "native_errors": report["native_errors"]}
                    break
                if not row["raw_output"] or not row["cache_state_cleared"]:
                    raise ValueError("RAW_EVIDENCE_OR_CACHE_CLEANUP_MISSING")
            if (len(report["calls"]) == 2 and report["blocker"] is None
                    and report["native_generate_calls"] == 2 and not report["native_errors"]
                    and all(call["parse_status"] in {"SUCCESS", "INVALID"}
                            for call in report["calls"])):
                report["status"] = "RUNTIME_SMOKE_PASS"
    except Exception as exc:
        report["blocker"] = {"stage": stage, "exception_type": type(exc).__name__,
                             "code": str(exc) if type(exc) is ValueError else "RUNTIME_EXCEPTION"}
    finally:
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(root / "environment_summary.json", {
            "hardware": report["hardware"], "software_versions": report["software_versions"],
            "environment": report["environment"]})
        write_json(root / "runtime_report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--rerun-of")
    parser.add_argument("--rerun-reason")
    args = parser.parse_args()
    report = run_smoke(args.run_id, rerun_of=args.rerun_of, rerun_reason=args.rerun_reason)
    print(json.dumps({k: report[k] for k in ("run_id", "status", "blocker", "notes")}))
    return 0 if report["status"] == "RUNTIME_SMOKE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
