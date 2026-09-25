"""Future owner-run single-T4 interface smoke. PREP supplies code, not a result."""

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
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.provision_qwen2_5_snapshot import (
    MODEL_ID, REVISION, PLAN, PLAN_SHA256, cached_snapshot, load_plan,
    network_denied, sha256_file, verify_snapshot, write_json,
)
from safeshift.runners.contracts import ErrorCode, Request, RunContext, Task, execute_call
from safeshift.runners.qwen2_5_vl import PREPROCESSING, Qwen2_5VLRunner, Qwen2_5VLAdapter
from safeshift.runners.storage import FileRawStore

ARTIFACTS = "data/processed/runtime_validation/w2_qwen2_5_t4_smoke"
CASE_IDS = ("case_01", "case_02")
OFFLINE_ENV = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
               "HF_HUB_DISABLE_TELEMETRY": "1", "HF_HUB_ENABLE_HF_TRANSFER": "0"}


class CaseRawStore(FileRawStore):
    """Keep the existing exclusive raw-before-adapter writer, with fixed case names."""

    def _directory(self, provenance):
        call_id = provenance["call_id"]
        if call_id not in CASE_IDS or provenance["sample_id"] != call_id:
            raise ValueError("UNEXPECTED_SMOKE_CASE")
        path = self.root / call_id
        self._check_path(path)
        return path


def generate_cases():
    from PIL import Image, ImageDraw
    cases = []
    for index, case in enumerate(CASE_IDS):
        with Image.new("RGB", (64, 64), "white") as image:
            draw = ImageDraw.Draw(image)
            if index == 0:
                draw.rectangle((8, 8, 40, 40), fill="blue")
            else:
                draw.ellipse((16, 16, 56, 56), fill="green")
            stream = BytesIO()
            image.save(stream, format="PNG")
        raw = stream.getvalue()
        cases.append((case, raw, {"generator": "qwen2-5-runtime-shapes-v1",
                                 "sha256": hashlib.sha256(raw).hexdigest(),
                                 "width": 64, "height": 64}))
    return cases


def software_versions(torch):
    versions = {name: importlib.metadata.version(name) for name in
                ("transformers", "torchvision", "qwen-vl-utils", "accelerate",
                 "pillow", "huggingface-hub", "tokenizers", "safetensors")}
    versions.update(python=platform.python_version(), torch=str(torch.__version__))
    return versions


def probe_hardware(torch):
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise ValueError("REQUIRES_ONE_VISIBLE_CUDA_GPU")
    prop = torch.cuda.get_device_properties(0)
    if not re.search(r"\bT4\b", prop.name) or (prop.major, prop.minor) != (7, 5):
        raise ValueError("REQUIRES_NVIDIA_T4")
    driver = None
    try:
        driver = subprocess.run(["nvidia-smi", "--query-gpu=driver_version",
                                 "--format=csv,noheader"], check=True, capture_output=True,
                                text=True, timeout=10).stdout.strip().splitlines()
    except (OSError, subprocess.SubprocessError):
        pass
    return {"gpu_name": prop.name, "visible_gpu_count": 1, "used_device": "cuda:0",
            "total_vram_bytes": prop.total_memory, "compute_capability": [7, 5],
            "torch_cuda_version": torch.version.cuda, "driver_versions": driver}


def memory_observation(torch):
    torch.cuda.synchronize(0)
    return {"allocated_bytes": torch.cuda.memory_allocated(0),
            "reserved_bytes": torch.cuda.memory_reserved(0),
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(0),
            "peak_reserved_bytes": torch.cuda.max_memory_reserved(0)}


def is_oom(error, torch):
    # GenerationFailure sanitizes messages but preserves Python exception context.
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, torch.cuda.OutOfMemoryError):
            return True
        error = error.__cause__ or error.__context__
    return False


def empty_visual_observation():
    # None means not observed/validated; never reuse a previous case's values.
    return {"observed_image_grid_thw": None, "observed_spatial_merge_size": None,
            "observed_visual_token_count": None,
            "observed_image_token_placeholder_count": None}


def observe_visual_tokens(prepared, model, processor, evidence):
    """Inspect the existing prepared tensors once; no preprocessing or generation.

    Contract: Transformers 4.51.3, 5f4ecf2d9f867a1255131d2461d75793c0cf1db2.
    Validated primitive observations survive subsequent contract failures.
    """
    grid = prepared.inputs["image_grid_thw"].tolist()
    if (type(grid) is not list or len(grid) != 1 or type(grid[0]) is not list
            or len(grid[0]) != 3 or any(type(v) is not int or v <= 0 for v in grid[0])):
        raise ValueError("INVALID_IMAGE_GRID_THW")
    t, h, w = grid[0]
    evidence["observed_image_grid_thw"] = [[t, h, w]]
    model_merge = model.config.vision_config.spatial_merge_size
    processor_merge = processor.image_processor.merge_size
    if (type(model_merge) is not int or model_merge <= 0
            or type(processor_merge) is not int or processor_merge <= 0
            or model_merge != processor_merge):
        raise ValueError("INVALID_OR_MISMATCHED_SPATIAL_MERGE_SIZE")
    evidence["observed_spatial_merge_size"] = model_merge
    if h % model_merge or w % model_merge:
        raise ValueError("IMAGE_GRID_NOT_DIVISIBLE_BY_MERGE_SIZE")
    count = t * (h // model_merge) * (w // model_merge)
    evidence["observed_visual_token_count"] = count
    if not 256 <= count <= 1280:
        raise ValueError("VISUAL_TOKEN_COUNT_OUTSIDE_QUALIFICATION_CAP")
    image_token_id = model.config.image_token_id
    if type(image_token_id) is not int or image_token_id < 0:
        raise ValueError("INVALID_IMAGE_TOKEN_ID")
    rows = prepared.inputs["input_ids"].tolist()
    if (type(rows) is not list or len(rows) != 1 or type(rows[0]) is not list
            or not rows[0] or any(type(v) is not int or v < 0 for v in rows[0])):
        raise ValueError("INVALID_PREPARED_INPUT_TOKEN_IDS")
    placeholders = rows[0].count(image_token_id)
    evidence["observed_image_token_placeholder_count"] = placeholders
    if placeholders != count:
        raise ValueError("IMAGE_TOKEN_PLACEHOLDER_COUNT_MISMATCH")


def placement_gate(model, processor, torch):
    counts = {"parameters": 0, "buffers": 0}
    for kind, items in (("parameters", model.parameters()), ("buffers", model.buffers())):
        for item in items:
            counts[kind] += 1
            if str(item.device) != "cuda:0":
                raise ValueError("OFFLOAD_OR_OTHER_DEVICE_FORBIDDEN")
            if kind == "parameters" and item.dtype != torch.float16:
                raise ValueError("FP16_PARAMETERS_REQUIRED")
    if not counts["parameters"]:
        raise ValueError("NO_MODEL_PARAMETERS")
    mapping = getattr(model, "hf_device_map", {})
    if (type(mapping) is not dict or any(str(v) not in ("0", "cuda:0") for v in mapping.values())
            or getattr(model, "is_quantized", False)
            or getattr(model.config, "quantization_config", None) is not None):
        raise ValueError("QUANTIZATION_OR_OFFLOAD_FORBIDDEN")
    if model.config._attn_implementation != "sdpa" or getattr(model.config, "output_attentions", False):
        raise ValueError("SDPA_ONLY")
    attention_classes = [type(m).__name__ for m in model.modules() if "Attention" in type(m).__name__]
    if (set(attention_classes) != {"Qwen2_5_VLSdpaAttention", "Qwen2_5_VLVisionSdpaAttention"}):
        raise ValueError("UNREVIEWED_NATIVE_ATTENTION_IMPLEMENTATION")
    Qwen2_5VLRunner._validate_processor(processor)
    return {**counts, "all_parameters_and_buffers": "cuda:0", "parameter_dtype": "FP16",
            "quantization": "NONE", "attention_classes": sorted(set(attention_classes)),
            "device_map": {str(k): str(v) for k, v in mapping.items()},
            "preprocessing": dict(PREPROCESSING)}


def run_smoke(run_id, *, repo=ROOT, cache_dir=None, runner_factory=Qwen2_5VLRunner,
              torch_module=None):
    """Injection points are for offline tests; CLI never substitutes a fake backend."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
        raise ValueError("INVALID_RUN_ID")
    root = FileRawStore(repo, ARTIFACTS + "/" + run_id).root
    root.mkdir(parents=True, exist_ok=False)
    summary = {"schema_version": "qwen2-5-t4-smoke-summary-v1", "run_id": run_id,
               "status": "RUNTIME_INTERFACE_FAILURE", "scope": "RUNTIME_INTERFACE_ONLY",
               "model_id": MODEL_ID, "model_revision": REVISION,
               "calls": [], "native_generate_calls": 0, "native_errors": [], "memory": {},
               "inspecsafe_used": False, "synthetic_gate_used": False,
               "protocol_freeze_commit_sha": "PENDING", "artifacts": {}}
    environment = {}
    snapshot = {"local_bytes_verified": False}
    metadata = {"run_id": run_id, "started_at_utc": datetime.now(timezone.utc).isoformat(),
                "plan_sha256": PLAN_SHA256, "model_id": MODEL_ID, "model_revision": REVISION,
                "command": "python scripts/w2_qwen2_5_t4_smoke.py --run-id " + run_id,
                "attention_implementation": "sdpa", "preprocessing": dict(PREPROCESSING),
                "precision": "FP16", "quantization": "NONE", "batch_size": 1,
                "network_policy": "OFFLINE_ENV_AND_SOCKET_DENIAL", "source_hashes": {}}
    stage = "PREFLIGHT"
    torch = None
    try:
        plan = load_plan(repo)
        metadata["git_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        for path in (PLAN, "scripts/w2_qwen2_5_t4_smoke.py", "scripts/provision_qwen2_5_snapshot.py",
                     "safeshift/runners/qwen2_5_vl.py"):
            metadata["source_hashes"][path] = sha256_file(repo / path)
        environment["offline_variables"] = {k: os.environ.get(k) for k in OFFLINE_ENV}
        if environment["offline_variables"] != OFFLINE_ENV:
            raise ValueError("SET_OFFLINE_ENV_BEFORE_PROCESS_START")
        if cache_dir is not None and Path(os.environ.get("HF_HUB_CACHE", "")).resolve() != Path(cache_dir).resolve():
            raise ValueError("CUSTOM_CACHE_REQUIRES_MATCHING_HF_HUB_CACHE_BEFORE_START")
        with network_denied():
            stage = "ENVIRONMENT"
            if torch_module is None:
                import torch as torch_module
            torch = torch_module
            environment["software"] = software_versions(torch)
            if environment["software"] != plan["software"]:
                raise ValueError("EXACT_SOFTWARE_PINS_REQUIRED")
            if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
                raise ValueError("LINUX_X86_64_REQUIRED")
            environment["installed_distributions"] = sorted(
                [{"name": d.metadata["Name"], "version": d.version}
                 for d in importlib.metadata.distributions()], key=lambda d: d["name"] or "")
            environment["hardware"] = probe_hardware(torch)
            if torch.version.cuda != plan["cuda_runtime"]:
                raise ValueError("CUDA_BUILD_MISMATCH")
            stage = "SNAPSHOT"
            snapshot = verify_snapshot(cached_snapshot(cache_dir), repo=repo)
            stage = "LOAD"
            runner = runner_factory()
            store = CaseRawStore(repo, ARTIFACTS + "/" + run_id)
            summary["memory"]["before_load"] = memory_observation(torch)
            context = RunContext(run_id, CASE_IDS[0], plan["smoke"]["decoding"],
                                 dict(PREPROCESSING), "FP16", "NONE", {"placement": "cuda:0"},
                                 environment["software"], metadata["git_commit"], metadata["command"],
                                 "HANDCRAFTED_RUNTIME_SMOKE")
            runner.initialize(context)
            runner.load(context)
            processor, model, _ = runner._resources
            summary["memory"]["after_load"] = memory_observation(torch)
            summary["placement"] = placement_gate(model, processor, torch)
            native_generate = model.generate
            original_prepare = runner.prepare_input
            original_generate_raw = runner.generate_raw
            visual_observations = {}

            def observed_generate_raw(*args, **kwargs):
                try:
                    return original_generate_raw(*args, **kwargs)
                except Exception as exc:
                    if is_oom(exc, torch):
                        summary["native_errors"].append({"error_type": type(exc).__name__,
                                                        "resource_failure": True})
                    raise

            def observed_prepare(request, context):
                try:
                    case_id = context.call_id
                    if (case_id not in CASE_IDS or request.sample_id != case_id
                            or case_id in visual_observations):
                        raise ValueError("UNEXPECTED_OR_DUPLICATE_PREPARE_CASE")
                    evidence = empty_visual_observation()
                    visual_observations[case_id] = evidence
                    prepared = original_prepare(request, context)
                    observe_visual_tokens(prepared, model, processor, evidence)
                    return prepared
                except Exception as exc:
                    summary["native_errors"].append({"error_type": type(exc).__name__,
                        "resource_failure": isinstance(exc, torch.cuda.OutOfMemoryError)})
                    raise

            def observed_generate(*args, **kwargs):
                summary["native_generate_calls"] += 1
                try:
                    return native_generate(*args, **kwargs)
                except Exception as exc:
                    summary["native_errors"].append({"error_type": type(exc).__name__,
                        "resource_failure": isinstance(exc, torch.cuda.OutOfMemoryError)})
                    raise

            model.generate = observed_generate
            runner.prepare_input = observed_prepare
            runner.generate_raw = observed_generate_raw
            stage = "CALLS"
            try:
                for case, raw, provenance in generate_cases():
                    from dataclasses import replace
                    ctx = replace(context, call_id=case, input_provenance=provenance)
                    request = Request(Task.CLASSIFICATION, case, case, raw,
                                      "qwen2-5-interface-prompt-v1", plan["smoke"]["prompt"])
                    torch.cuda.reset_peak_memory_stats(0)
                    result = execute_call(runner, Qwen2_5VLAdapter(), store, request, ctx)
                    store.save_result(result)
                    summary["memory"][case] = memory_observation(torch)
                    state_cleared = model.rope_deltas is None and getattr(model, "_cache", None) is None
                    summary["calls"].append({"case_id": case, "parse_status": result.parse_status.value,
                        **visual_observations.get(case, empty_visual_observation()),
                        "error": asdict(result.error) if result.error else None,
                        "raw": asdict(result.raw_output) if result.raw_output else None,
                        "state_cleared": state_cleared, "input": provenance})
                    if (runner._resources[1] is not model or not state_cleared
                            or not result.raw_output
                            or result.parse_status.value not in ("SUCCESS", "INVALID")
                            or (result.error and result.error.code != ErrorCode.INVALID_CLASSIFICATION)):
                        raise ValueError("CALL_INTERFACE_FAILURE")
                    if sha256_file(repo / result.raw_output.path) != result.raw_output.sha256:
                        raise ValueError("RAW_PERSISTENCE_HASH_MISMATCH")
                    placement_gate(model, processor, torch)
            finally:
                model.generate = native_generate
                runner.prepare_input = original_prepare
                runner.generate_raw = original_generate_raw
            if len(summary["calls"]) != 2 or summary["native_generate_calls"] != 2 or summary["native_errors"]:
                raise ValueError("EXACTLY_TWO_INDEPENDENT_CALLS_REQUIRED")
            summary["status"] = "RUNTIME_INTERFACE_PASS"
    except Exception as exc:
        resource_failure = torch is not None and is_oom(exc, torch)
        resource_failure |= any(e["resource_failure"] for e in summary["native_errors"])
        summary["status"] = "RUNTIME_RESOURCE_FAILURE" if resource_failure else "RUNTIME_INTERFACE_FAILURE"
        summary["failure"] = {"stage": stage, "error_type": type(exc).__name__}
    finally:
        metadata["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(root / "run_metadata.json", metadata)
        write_json(root / "environment.json", environment)
        write_json(root / "snapshot_manifest.json", snapshot)
        summary["artifacts"] = {p.relative_to(root).as_posix(): {"sha256": sha256_file(p),
                                  "size_bytes": p.stat().st_size}
                                for p in sorted(root.rglob("*")) if p.is_file()}
        write_json(root / "summary.json", summary)
        with (root / "summary.json.sha256").open("x", encoding="ascii") as stream:
            stream.write(sha256_file(root / "summary.json") + "  summary.json\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--cache-dir", help="Repository-relative cache under data/processed")
    args = parser.parse_args()
    cache = FileRawStore(ROOT, args.cache_dir).root if args.cache_dir else None
    report = run_smoke(args.run_id, cache_dir=cache)
    print(json.dumps({"run_id": args.run_id, "status": report["status"]}))
    return 0 if report["status"] == "RUNTIME_INTERFACE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
