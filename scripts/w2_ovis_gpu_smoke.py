"""Owner-run offline Ovis2.5-9B single-A100 runtime/interface smoke.

This harness never selects a fallback, changes the pinned runner condition, or
performs grounding.  Online snapshot provisioning is a separate command; this
process requires the offline transition before it starts.
"""

import argparse
from collections import defaultdict
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
import shlex
import socket
import subprocess
import sys
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.provision_ovis2_5_snapshot import (
    MODEL_ID,
    RESOLVED_REPOSITORY_ID,
    REVISION,
    cached_snapshot,
    sha256_file,
    verify_snapshot,
    write_json,
)
from safeshift.runners.contracts import (
    ErrorCode,
    ParseStatus,
    Request,
    RunContext,
    Task,
    execute_call,
)
from safeshift.runners.ovis2_5 import Ovis2_5Adapter, Ovis2_5Runner
from safeshift.runners.storage import FileRawStore


PLAN = "configs/pre_freeze/ovis_gpu_smoke.v1.json"
ARTIFACTS = "data/processed/runtime_validation/w2_ovis_gpu_smoke"
GENERATOR_VERSION = "runtime-smoke-geometry-v1"
PROMPT_ID = "ovis-runtime-smoke-prompt-v1"
PROMPT = (
    "You are performing an interface smoke test. Inspect the image and return exactly "
    "one JSON object with one key named safety_level. Its value must be one of: "
    "Level01, Level02, Level03, Level04. Do not output markdown or any other text."
)
CASE_IDS = ["RUNTIME_SMOKE_01", "RUNTIME_SMOKE_02"]
MIN_VRAM_BYTES = 40_000_000_000
MAX_BUNDLE_MEMBER_BYTES = 2 * 1024 * 1024
PINNED_PACKAGES = {
    "torch_distribution": "2.4.0",
    "transformers": "4.51.3",
    "numpy": "1.25.0",
    "pillow": "10.3.0",
    "flash_attn": "2.7.0.post2",
    "moviepy": "1.0.3",
}
CLAIMS = {
    "capability_pass": False,
    "grounding_pass": False,
    "accuracy_pass": False,
    "benchmark_pass": False,
    "precision_frozen": False,
    "decoding_frozen": False,
    "thinking_frozen": False,
    "protocol_frozen": False,
}


def expected_plan():
    return {
        "schema_version": "ovis-gpu-smoke-plan-v1",
        "status": "PRE_RUNTIME_VALIDATION_PLAN",
        "scope": "SMOKE_ONLY_TECHNICAL_CONFIGURATION",
        "platform": "USER_CONTROLLED_SINGLE_GPU",
        "accelerator_requirement": "NVIDIA_A100_SINGLE_MIN_40GB",
        "model_id": MODEL_ID,
        "resolved_repository_id": RESOLVED_REPOSITORY_ID,
        "revision": REVISION,
        "precision": "BF16",
        "quantization": "NONE",
        "device": {"placement": "cuda:0"},
        "hardware": {
            "visible_cuda_gpu_count": 1,
            "logical_device_index": 0,
            "gpu_name_contains": "A100",
            "min_total_memory_bytes": MIN_VRAM_BYTES,
            "min_compute_capability": [8, 0],
            "bf16_required": True,
            "reject_undersized_mig": True,
        },
        "preprocessing": {
            "mode": "official_preprocess_inputs",
            "min_pixels": 448 * 448,
            "max_pixels": 1792 * 1792,
        },
        "thinking": {
            "enable_thinking": False,
            "enable_thinking_budget": False,
        },
        "attention": "DOCUMENTED_FLASH_ATTN_RECIPE",
        "software_environment": {
            "python": "3.11",
            "torch": "2.4.0",
            "transformers": "4.51.3",
            "numpy": "1.25.0",
            "pillow": "10.3.0",
            "flash_attn": "2.7.0.post2",
            "moviepy": "1.0.3",
            "moviepy_policy": "FULL_OFFICIAL_RECIPE",
            "huggingface_hub": "RESOLVER_SELECTED_RECORD_EXACT",
        },
        "decoding": {"do_sample": False, "max_new_tokens": 32},
        "prompt": PROMPT,
        "prompt_sha256": hashlib.sha256(PROMPT.encode("utf-8")).hexdigest(),
        "case_ids": CASE_IDS,
        "generator_version": GENERATOR_VERSION,
        "task": "classification",
        "protocol_freeze_commit_sha": "PENDING",
    }


def load_plan(repo=ROOT):
    plan = json.loads((Path(repo) / PLAN).read_text(encoding="utf-8"))
    if json.dumps(plan, sort_keys=True) != json.dumps(expected_plan(), sort_keys=True):
        raise ValueError("SMOKE_PLAN_CHANGED")
    return plan


def generation_decoding(plan):
    """Build the runner condition with explicit thinking values and no temperature."""
    return {**plan["decoding"], **plan["thinking"]}


def generate_cases(repo=ROOT):
    """Return two deterministic, in-memory PNGs independent of SYNTHETIC V1."""
    from PIL import Image, ImageDraw

    result = []
    generator_hash = sha256_file(Path(repo) / "scripts/w2_ovis_gpu_smoke.py")
    for index, case_id in enumerate(CASE_IDS):
        background = (246, 246, 246) if index == 0 else (172, 172, 172)
        with Image.new("RGB", (224, 192), background) as image:
            draw = ImageDraw.Draw(image)
            if index == 0:
                draw.rectangle((18, 24, 92, 138), fill=(25, 101, 204))
                draw.ellipse((124, 59, 196, 131), fill=(232, 72, 38))
            else:
                draw.polygon([(22, 152), (88, 30), (144, 152)], fill=(144, 48, 182))
                draw.rectangle((166, 42, 205, 164), fill=(32, 194, 128))
            stream = BytesIO()
            image.save(stream, format="PNG", optimize=False, compress_level=9)
        raw = stream.getvalue()
        result.append((raw, {
            "case_id": case_id,
            "image_sha256": hashlib.sha256(raw).hexdigest(),
            "width": 224,
            "height": 192,
            "color_mode": "RGB",
            "generator_version": GENERATOR_VERSION,
            "generator_sha256": generator_hash,
        }))
    if len(result) != 2 or len({item[1]["image_sha256"] for item in result}) != 2:
        raise ValueError("SMOKE_IMAGES_MUST_BE_TWO_DISTINCT_BYTE_STREAMS")
    return result


def software_versions(torch):
    def distribution(name):
        return importlib.metadata.version(name)

    return {
        "python": platform.python_version(),
        "torch": str(torch.__version__),
        "torch_distribution": distribution("torch"),
        "torch_cuda_runtime": torch.version.cuda,
        "transformers": distribution("transformers"),
        "numpy": distribution("numpy"),
        "pillow": distribution("pillow"),
        "flash_attn": distribution("flash-attn"),
        "moviepy": distribution("moviepy"),
        "huggingface_hub": distribution("huggingface_hub"),
    }


def _base_version(value):
    return str(value).split("+", 1)[0]


def validate_software_versions(versions):
    if tuple(map(int, versions["python"].split(".")[:2])) != (3, 11):
        raise ValueError("REQUIRES_PYTHON_3_11")
    for name, expected in PINNED_PACKAGES.items():
        if versions.get(name) != expected:
            raise ValueError("PINNED_PACKAGE_VERSION_MISMATCH_" + name.upper())
    if _base_version(versions.get("torch")) != "2.4.0":
        raise ValueError("TORCH_RUNTIME_VERSION_MISMATCH")
    if not versions.get("torch_cuda_runtime"):
        raise ValueError("TORCH_CUDA_RUNTIME_NOT_RECORDED")
    if not versions.get("huggingface_hub"):
        raise ValueError("HUGGINGFACE_HUB_VERSION_NOT_RECORDED")
    return True


def probe_hardware(torch):
    cuda = torch.cuda
    available = bool(cuda.is_available())
    count = int(cuda.device_count()) if available else 0
    gpus = []
    for index in range(count):
        properties = cuda.get_device_properties(index)
        gpus.append({
            "index": index,
            "name": str(properties.name),
            "total_memory_bytes": int(properties.total_memory),
            "compute_capability": [int(properties.major), int(properties.minor)],
        })
    smi = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,uuid,driver_version,memory.total,mig.mode.current",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    smi_rows = []
    for line in smi.strip().splitlines():
        if not line.strip():
            continue
        fields = [field.strip() for field in line.split(",", 5)]
        if len(fields) != 6:
            raise ValueError("UNEXPECTED_NVIDIA_SMI_OUTPUT")
        index, name, uuid, driver, memory, mig_mode = fields
        smi_rows.append({
            "physical_index": int(index),
            "name": name,
            "uuid": uuid,
            "driver_version": driver,
            "memory_total_mib": int(memory),
            "mig_mode": mig_mode,
        })
    return {
        "cuda_available": available,
        "visible_gpu_count": count,
        "current_device": int(cuda.current_device()) if available and count else None,
        "bf16_supported": bool(cuda.is_bf16_supported()) if available and count else False,
        "gpus": gpus,
        "nvidia_smi_inventory": smi_rows,
        "driver_versions": sorted({row["driver_version"] for row in smi_rows}),
    }


def require_single_a100(hardware):
    if not hardware.get("cuda_available"):
        raise ValueError("CUDA_NOT_AVAILABLE")
    if hardware.get("visible_gpu_count") != 1 or len(hardware.get("gpus", [])) != 1:
        raise ValueError("REQUIRES_EXACTLY_ONE_VISIBLE_CUDA_GPU")
    gpu = hardware["gpus"][0]
    if hardware.get("current_device") != 0 or gpu.get("index") != 0:
        raise ValueError("REQUIRES_LOGICAL_DEVICE_ZERO")
    if re.search("A100", gpu.get("name", ""), re.IGNORECASE) is None:
        raise ValueError("REQUIRES_NVIDIA_A100")
    if int(gpu.get("total_memory_bytes", 0)) < MIN_VRAM_BYTES:
        raise ValueError("A100_VRAM_BELOW_40GB_CLASS")
    if tuple(gpu.get("compute_capability", [])) < (8, 0):
        raise ValueError("COMPUTE_CAPABILITY_BELOW_8_0")
    if not hardware.get("bf16_supported"):
        raise ValueError("BF16_NOT_SUPPORTED")
    return True


def memory_snapshot(torch, stage):
    free, total = torch.cuda.mem_get_info(0)
    return {
        "stage": stage,
        "device": "cuda:0",
        "free_bytes": int(free),
        "total_bytes": int(total),
        "memory_allocated": int(torch.cuda.memory_allocated(0)),
        "memory_reserved": int(torch.cuda.memory_reserved(0)),
        "max_memory_allocated": int(torch.cuda.max_memory_allocated(0)),
        "max_memory_reserved": int(torch.cuda.max_memory_reserved(0)),
    }


def _is_floating(tensor):
    method = getattr(tensor, "is_floating_point", None)
    if callable(method):
        return bool(method())
    return bool(getattr(getattr(tensor, "dtype", None), "is_floating_point", False))


def _tensor_census(tensors):
    by_device = defaultdict(lambda: {"tensor_count": 0, "numel": 0, "bytes": 0})
    by_dtype = defaultdict(lambda: {"tensor_count": 0, "numel": 0, "bytes": 0})
    floating_by_device = defaultdict(lambda: {"tensor_count": 0, "numel": 0, "bytes": 0})
    total = {"tensor_count": 0, "numel": 0, "bytes": 0}
    rows = []
    for tensor in tensors:
        device = str(tensor.device)
        dtype = str(tensor.dtype)
        numel = int(tensor.numel())
        size = numel * int(tensor.element_size())
        floating = _is_floating(tensor)
        row = {"device": device, "dtype": dtype, "numel": numel,
               "bytes": size, "floating": floating}
        rows.append(row)
        for target in (total, by_device[device], by_dtype[dtype]):
            target["tensor_count"] += 1
            target["numel"] += numel
            target["bytes"] += size
        if floating:
            target = floating_by_device[device]
            target["tensor_count"] += 1
            target["numel"] += numel
            target["bytes"] += size
    return {
        "total": total,
        "distinct_devices": sorted(by_device),
        "by_device": {key: by_device[key] for key in sorted(by_device)},
        "by_dtype": {key: by_dtype[key] for key in sorted(by_dtype)},
        "floating_by_device": {
            key: floating_by_device[key] for key in sorted(floating_by_device)
        },
        "tensors": rows,
    }


def inspect_model_placement(model):
    parameters = list(model.parameters())
    buffers = list(model.buffers())
    parameter_census = _tensor_census(parameters)
    buffer_census = _tensor_census(buffers)
    violations = []
    if not parameters:
        violations.append("NO_MODEL_PARAMETERS_OBSERVED")
    for row in parameter_census["tensors"]:
        if row["device"] == "meta":
            violations.append("META_PARAMETER")
        elif row["floating"] and row["device"] != "cuda:0":
            violations.append("FLOATING_PARAMETER_OUTSIDE_CUDA_0")
    if "meta" in buffer_census["distinct_devices"]:
        violations.append("META_BUFFER")
    return {
        "expected_parameter_device": "cuda:0",
        "parameters": parameter_census,
        "buffers": buffer_census,
        "violations": sorted(set(violations)),
        "passed": not violations,
    }


def inspect_model_dtypes(model):
    floating = [parameter for parameter in model.parameters() if _is_floating(parameter)]
    census = _tensor_census(floating)
    deviations = {
        dtype: values for dtype, values in census["by_dtype"].items()
        if dtype != "torch.bfloat16"
    }
    passed = bool(floating) and not deviations and "torch.bfloat16" in census["by_dtype"]
    return {
        "expected_primary_dtype": "torch.bfloat16",
        "policy": "ANY_NON_BF16_FLOATING_PARAMETER_REQUIRES_BLOCKING_REVIEW",
        "floating_parameter_census": census,
        "deviations": deviations,
        "status": "EXPECTED_BF16_ONLY" if passed else "DTYPE_DEVIATION_REVIEW_REQUIRED",
        "passed": passed,
    }


def inspect_attention(model):
    observations = []
    for label, owner in (("model.config", getattr(model, "config", None)),
                         ("model.llm.config", getattr(getattr(model, "llm", None), "config", None))):
        if owner is None:
            continue
        for attribute in ("_attn_implementation", "attn_implementation"):
            value = getattr(owner, attribute, None)
            if value is not None:
                observations.append({"source": label + "." + attribute, "value": str(value)})
    return {
        "plan": "DOCUMENTED_FLASH_ATTN_RECIPE",
        "runner_override": False,
        "effective": observations[0]["value"] if observations else "UNKNOWN_OBSERVED",
        "observations": observations,
    }


class NetworkFirewall:
    def __init__(self):
        self.violation_count = 0

    def deny(self, *args, **kwargs):
        self.violation_count += 1
        raise RuntimeError("NETWORK_FORBIDDEN_DURING_OVIS_SMOKE")


def parser_outcome_allowed(result):
    if result.parse_status == ParseStatus.SUCCESS:
        return result.error is None
    return (
        result.parse_status == ParseStatus.INVALID
        and result.error is not None
        and result.error.code == ErrorCode.INVALID_CLASSIFICATION
    )


def _file_record(repo, path):
    path = Path(path)
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(Path(repo).resolve()):
        raise ValueError("EVIDENCE_PATH_OUTSIDE_REPOSITORY")
    return {
        "path": resolved.relative_to(Path(repo).resolve()).as_posix(),
        "sha256": sha256_file(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def _zip_bytes(path):
    data = Path(path).read_bytes()
    if len(data) > MAX_BUNDLE_MEMBER_BYTES:
        raise ValueError("EVIDENCE_MEMBER_TOO_LARGE")
    return data


def create_evidence_bundle(run_root, repo=ROOT):
    """Create a deterministic allowlisted ZIP plus an external SHA-256 sidecar."""
    repo = Path(repo).resolve()
    run_root = Path(run_root).resolve(strict=True)
    if not run_root.is_relative_to(repo / "data" / "processed"):
        raise ValueError("RUN_ROOT_OUTSIDE_DATA_PROCESSED")
    report = json.loads((run_root / "runtime_report.json").read_text(encoding="utf-8"))
    members = []
    for name in (
        "runtime_report.json",
        "environment.json",
        "snapshot_verification.json",
        "weight_verification.json",
        "critical_file_verification.json",
        "case_manifest.json",
    ):
        path = run_root / name
        if path.is_file():
            members.append((name, path))
    for call in report.get("calls", []):
        sample_id = call.get("sample_id")
        if sample_id not in CASE_IDS:
            raise ValueError("UNEXPECTED_CASE_IN_REPORT")
        for key, basename in (("raw_output", "response.raw"), ("metadata", "metadata.json")):
            record = call.get(key)
            if not record:
                continue
            path = (repo / record["path"]).resolve(strict=True)
            if not path.is_relative_to(run_root) or path.name != basename:
                raise ValueError("UNSAFE_CALL_EVIDENCE_PATH")
            if sha256_file(path) != record["sha256"]:
                raise ValueError("CALL_EVIDENCE_HASH_MISMATCH")
            members.append((f"calls/{sample_id}/{basename}", path))
    archive_path = run_root / "ovis_gpu_smoke_evidence.zip"
    sidecar_path = run_root / "ovis_gpu_smoke_evidence.zip.sha256"
    with archive_path.open("xb") as output:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=9) as archive:
            for archive_name, path in sorted(members):
                info = zipfile.ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, _zip_bytes(path))
    digest = sha256_file(archive_path)
    with sidecar_path.open("x", encoding="ascii", newline="\n") as stream:
        stream.write(digest + "  " + archive_path.name + "\n")
    return {
        "path": archive_path.relative_to(repo).as_posix(),
        "sha256": digest,
        "size_bytes": archive_path.stat().st_size,
        "sidecar": sidecar_path.relative_to(repo).as_posix(),
        "members": [name for name, _ in sorted(members)],
    }


def _now(clock=None):
    value = (clock or (lambda: datetime.now(timezone.utc)))()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("CLOCK_MUST_BE_TIMEZONE_AWARE")
    return value.astimezone(timezone.utc).isoformat()


def _initial_report(run_id, rerun_of, rerun_reason, clock=None):
    return {
        "schema_version": "ovis-gpu-runtime-report-v1",
        "run_id": run_id,
        "started_at_utc": _now(clock),
        "finished_at_utc": None,
        "git_commit": None,
        "model_id": MODEL_ID,
        "requested_model_id": MODEL_ID,
        "resolved_repository_id": RESOLVED_REPOSITORY_ID,
        "revision": REVISION,
        "runner_version": None,
        "smoke_config_sha256": None,
        "prompt_sha256": None,
        "cases": [],
        "snapshot_verification": None,
        "custom_remote_code": {
            "trust_remote_code": True,
            "local_files_only": True,
            "snapshot_path_identity": (
                "models--ATH-MaaS--Ovis2.5-9B/snapshots/" + REVISION
            ),
            "critical_source_hashes": [],
        },
        "hardware": None,
        "software_versions": {},
        "environment": {},
        "precision": "BF16",
        "quantization": "NONE",
        "device": {"placement": "cuda:0"},
        "thinking": {"enable_thinking": False, "enable_thinking_budget": False},
        "decoding": {"do_sample": False, "max_new_tokens": 32},
        "attention": {
            "plan": "DOCUMENTED_FLASH_ATTN_RECIPE",
            "runner_override": False,
            "effective": "NOT_OBSERVED_MODEL_NOT_LOADED",
            "observations": [],
        },
        "parameter_placement": None,
        "buffer_placement": None,
        "dtype_evidence": None,
        "memory": [],
        "calls": [],
        "notes": [],
        "blocker": None,
        "runtime_check_failure": None,
        "rerun_of": rerun_of,
        "rerun_reason": rerun_reason,
        "status": "RUNTIME_SMOKE_FAIL",
        "load_lifecycles": 0,
        "native_generate_calls": 0,
        "native_errors": [],
        "network_policy": "OFFLINE_ENV_AND_COUNTING_SOCKET_CONNECTION_DENIAL",
        "network_violation_count": 0,
        "claims": dict(CLAIMS),
        "protocol_freeze_commit_sha": "PENDING",
        "failure_rerun_policy": "NO_AUTOMATIC_RERUN_OR_FALLBACK",
        "bundle": {
            "filename": "ovis_gpu_smoke_evidence.zip",
            "sha256_sidecar": "ovis_gpu_smoke_evidence.zip.sha256",
            "creation": "AFTER_RUNTIME_REPORT",
        },
    }


def run_smoke(run_id, *, repo=ROOT, rerun_of=None, rerun_reason=None,
              runner_factory=Ovis2_5Runner, torch_module=None, clock=None):
    """Run the fixed smoke. Injection points exist only for offline unit tests."""
    repo = Path(repo)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
        raise ValueError("INVALID_RUN_ID")
    if bool(rerun_of) != bool(rerun_reason):
        raise ValueError("RERUN_REQUIRES_PREVIOUS_ID_AND_REASON")
    if rerun_of and not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", rerun_of):
        raise ValueError("INVALID_RERUN_ID")
    root = FileRawStore(repo, ARTIFACTS + "/" + run_id).root
    if root.parent.exists() and any(root.parent.glob("*/runtime_report.json")) and not rerun_of:
        raise ValueError("EXISTING_ATTEMPT_REQUIRES_RERUN_ID_AND_REASON")
    root.mkdir(parents=True, exist_ok=False)
    report = _initial_report(run_id, rerun_of, rerun_reason, clock)
    firewall = NetworkFirewall()
    stage = "PLAN"
    try:
        plan = load_plan(repo)
        report["smoke_config_sha256"] = sha256_file(repo / PLAN)
        report["prompt_sha256"] = plan["prompt_sha256"]
        report["git_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip()
        stage = "OFFLINE_PREFLIGHT"
        safe_environment_names = (
            "HF_HUB_OFFLINE",
            "TRANSFORMERS_OFFLINE",
            "HF_HUB_DISABLE_TELEMETRY",
            "CUDA_VISIBLE_DEVICES",
            "PYTORCH_CUDA_ALLOC_CONF",
        )
        report["environment"] = {
            name: os.environ.get(name) for name in safe_environment_names
        }
        if any(os.environ.get(name) != "1" for name in (
            "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"
        )):
            raise ValueError("SET_ALL_OFFLINE_VARIABLES_BEFORE_PROCESS_START")
        with patch.object(socket.socket, "connect", firewall.deny), \
                patch.object(socket.socket, "connect_ex", firewall.deny), \
                patch.object(socket, "create_connection", firewall.deny):
            stage = "SOFTWARE_PREFLIGHT"
            if torch_module is None:
                import torch as torch_module
            torch = torch_module
            report["software_versions"] = software_versions(torch)
            validate_software_versions(report["software_versions"])
            stage = "GPU_PREFLIGHT"
            report["hardware"] = probe_hardware(torch)
            require_single_a100(report["hardware"])
            stage = "LOCAL_SNAPSHOT_VERIFICATION"
            snapshot = cached_snapshot(offline=True)
            verification = verify_snapshot(snapshot, repo)
            report["snapshot_verification"] = {
                "passed": verification["LOCAL_SNAPSHOT_VERIFIED"],
                "path_identity": verification["snapshot"]["expected_cache_suffix"],
                "weight_bytes_verified": verification["weights"]["LOCAL_WEIGHT_BYTES_VERIFIED"],
                "critical_hashes_verified": verification["critical_files"][
                    "CRITICAL_PROVENANCE_HASHES_VERIFIED"
                ],
                "required_local_assets_present": verification["critical_files"][
                    "REQUIRED_LOCAL_ASSETS_PRESENT"
                ],
            }
            verification_operation = {
                "mode": "RUNTIME_OFFLINE_REVERIFICATION",
                "local_files_only": True,
                "network_firewall_enabled": True,
                "network_violation_count_at_verification": firewall.violation_count,
            }
            write_json(root / "snapshot_verification.json", {
                **verification["snapshot"],
                "component_verdicts": {
                    "snapshot_path": verification["snapshot"]["SNAPSHOT_PATH_VERIFIED"],
                    "weight_bytes": verification["weights"]["LOCAL_WEIGHT_BYTES_VERIFIED"],
                    "critical_provenance_hashes": verification["critical_files"][
                        "CRITICAL_PROVENANCE_HASHES_VERIFIED"
                    ],
                    "required_local_assets": verification["critical_files"][
                        "REQUIRED_LOCAL_ASSETS_PRESENT"
                    ],
                },
                "LOCAL_SNAPSHOT_VERIFIED": verification["LOCAL_SNAPSHOT_VERIFIED"],
                "operation": verification_operation,
            })
            write_json(root / "weight_verification.json", {
                **verification["weights"], "operation": verification_operation,
            })
            write_json(root / "critical_file_verification.json", {
                **verification["critical_files"], "operation": verification_operation,
            })
            report["custom_remote_code"]["critical_source_hashes"] = [
                {
                    "path": row["path"],
                    "sha256": row["sha256"],
                    "verification_status": row["verification_status"],
                }
                for row in verification["critical_files"]["files"]
                if row["verification_basis"] == "PROVENANCE_SHA256"
            ]
            if not verification["LOCAL_SNAPSHOT_VERIFIED"]:
                raise ValueError("LOCAL_SNAPSHOT_VERIFICATION_FAILED")
            stage = "CASE_GENERATION"
            cases = generate_cases(repo)
            report["cases"] = [metadata for _, metadata in cases]
            write_json(root / "case_manifest.json", {
                "schema_version": "ovis-runtime-smoke-cases-v1",
                "generator_version": GENERATOR_VERSION,
                "cases": report["cases"],
                "generated_image_binaries_persisted": False,
                "semantic_accuracy_use": False,
            })
            torch.cuda.reset_peak_memory_stats(0)
            report["memory"].append(memory_snapshot(torch, "before_load"))
            runner = runner_factory()
            adapter = Ovis2_5Adapter()
            report["runner_version"] = runner.version
            store = FileRawStore(repo, ARTIFACTS + "/" + run_id + "/raw")
            original_load = runner.load
            loaded_model = None

            def observed_load(context):
                nonlocal loaded_model
                try:
                    original_load(context)
                except Exception as exc:
                    report["native_errors"].append({
                        "stage": "load", "exception_type": type(exc).__name__
                    })
                    raise
                model = runner._model
                if model is None:
                    raise ValueError("RUNNER_DID_NOT_PUBLISH_MODEL")
                if loaded_model is not None:
                    if model is not loaded_model:
                        raise ValueError("MODEL_RELOADED_BETWEEN_CALLS")
                    return
                loaded_model = model
                report["load_lifecycles"] += 1
                report["memory"].append(memory_snapshot(torch, "after_load"))
                placement = inspect_model_placement(model)
                report["parameter_placement"] = {
                    key: value for key, value in placement.items() if key != "buffers"
                }
                report["buffer_placement"] = placement["buffers"]
                report["dtype_evidence"] = inspect_model_dtypes(model)
                report["attention"] = inspect_attention(model)
                if not placement["passed"]:
                    report["runtime_check_failure"] = "PARAMETER_PLACEMENT_VIOLATION"
                    raise ValueError("PARAMETER_PLACEMENT_VIOLATION")
                if not report["dtype_evidence"]["passed"]:
                    report["runtime_check_failure"] = "DTYPE_DEVIATION_REVIEW_REQUIRED"
                    raise ValueError("DTYPE_DEVIATION_REVIEW_REQUIRED")
                native_generate = model.generate

                def observed_generate(*args, **kwargs):
                    report["native_generate_calls"] += 1
                    try:
                        return native_generate(*args, **kwargs)
                    except Exception as exc:
                        report["native_errors"].append({
                            "call_number": report["native_generate_calls"],
                            "exception_type": type(exc).__name__,
                            "oom": "OutOfMemory" in type(exc).__name__,
                        })
                        raise

                model.generate = observed_generate

            runner.load = observed_load
            stage = "EXECUTE_CALL"
            for index, (image_bytes, case_metadata) in enumerate(cases, 1):
                command = ["python", "scripts/w2_ovis_gpu_smoke.py", "--run-id", run_id]
                if rerun_of:
                    command.extend([
                        "--rerun-of", rerun_of,
                        "--rerun-reason", rerun_reason,
                    ])
                context = RunContext(
                    run_id=run_id,
                    call_id=f"call_{index:02d}",
                    decoding=generation_decoding(plan),
                    preprocessing=plan["preprocessing"],
                    precision=plan["precision"],
                    quantization=plan["quantization"],
                    device=plan["device"],
                    software_versions=report["software_versions"],
                    git_commit_sha=report["git_commit"],
                    command=shlex.join(command),
                    source_kind="HANDCRAFTED_RUNTIME_SMOKE",
                    input_provenance=case_metadata,
                )
                request = Request(
                    Task.CLASSIFICATION,
                    case_metadata["case_id"],
                    case_metadata["case_id"],
                    image_bytes,
                    PROMPT_ID,
                    plan["prompt"],
                )
                result = execute_call(runner, adapter, store, request, context)
                row = {
                    "call_id": context.call_id,
                    "sample_id": request.sample_id,
                    "task": request.task.value,
                    "parse_status": result.parse_status.value,
                    "error": asdict(result.error) if result.error else None,
                    "model_revision": REVISION,
                    "runner_version": runner.version,
                    "raw_output": None,
                    "metadata": None,
                }
                report["calls"].append(row)
                if result.raw_output:
                    raw_path = repo / result.raw_output.path
                    if sha256_file(raw_path) != result.raw_output.sha256:
                        raise ValueError("RAW_REFERENCE_HASH_MISMATCH")
                    row["raw_output"] = _file_record(repo, raw_path)
                    metadata_path = raw_path.with_name("metadata.json")
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                    if metadata.get("parse_status") != "NOT_ATTEMPTED":
                        raise ValueError("RAW_METADATA_MUST_PRECEDE_ADAPTER")
                    if metadata.get("task") != "classification":
                        raise ValueError("ONLY_CLASSIFICATION_IS_ALLOWED")
                    row["metadata"] = _file_record(repo, metadata_path)
                store.save_result(result)
                report["memory"].append(memory_snapshot(torch, f"after_call_{index}"))
                if result.error and result.error.code == ErrorCode.INVALID_CLASSIFICATION:
                    report["notes"].append("CLASSIFICATION_PARSE_INVALID_NONBLOCKING")
                if not parser_outcome_allowed(result):
                    report["blocker"] = {
                        "stage": "execute_call",
                        "code": result.error.code.value if result.error else "DISALLOWED_PARSE_STATUS",
                        "error": asdict(result.error) if result.error else None,
                        "parse_status": result.parse_status.value,
                        "runtime_check_failure": report["runtime_check_failure"],
                        "native_errors": report["native_errors"],
                    }
                    break
                if not row["raw_output"] or not row["metadata"]:
                    raise ValueError("RAW_AND_METADATA_EVIDENCE_REQUIRED")
            report["network_violation_count"] = firewall.violation_count
            if firewall.violation_count:
                raise ValueError("NETWORK_VIOLATION")
            if (
                len(report["calls"]) == 2
                and report["blocker"] is None
                and report["load_lifecycles"] == 1
                and report["native_generate_calls"] == 2
                and not report["native_errors"]
                and report["parameter_placement"]["passed"]
                and report["dtype_evidence"]["passed"]
                and len(report["memory"]) == 4
                and all(call["parse_status"] in {"SUCCESS", "INVALID"}
                        for call in report["calls"])
            ):
                report["status"] = "RUNTIME_SMOKE_PASS"
    except Exception as exc:
        if report["blocker"] is None:
            report["blocker"] = {
                "stage": stage,
                "exception_type": type(exc).__name__,
                "code": str(exc) if type(exc) is ValueError else "RUNTIME_EXCEPTION",
            }
    finally:
        report["network_violation_count"] = firewall.violation_count
        if firewall.violation_count and report["status"] == "RUNTIME_SMOKE_PASS":
            report["status"] = "RUNTIME_SMOKE_FAIL"
            report["blocker"] = {
                "stage": "NETWORK_FIREWALL",
                "exception_type": "RuntimeError",
                "code": "NETWORK_VIOLATION",
            }
        report["finished_at_utc"] = _now(clock)
        write_json(root / "environment.json", {
            "schema_version": "ovis-gpu-smoke-environment-v1",
            "hardware": report["hardware"],
            "software_versions": report["software_versions"],
            "environment": report["environment"],
            "network_policy": report["network_policy"],
            "network_violation_count": report["network_violation_count"],
        })
        write_json(root / "runtime_report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--rerun-of")
    parser.add_argument("--rerun-reason")
    args = parser.parse_args()
    report = run_smoke(
        args.run_id,
        rerun_of=args.rerun_of,
        rerun_reason=args.rerun_reason,
    )
    bundle = None
    bundle_error = None
    try:
        bundle = create_evidence_bundle(
            ROOT / ARTIFACTS / args.run_id,
            ROOT,
        )
    except Exception as exc:
        bundle_error = {"exception_type": type(exc).__name__}
    print(json.dumps({
        "run_id": report["run_id"],
        "status": report["status"],
        "blocker": report["blocker"],
        "notes": report["notes"],
        "bundle": bundle,
        "bundle_error": bundle_error,
    }, sort_keys=True))
    return 0 if report["status"] == "RUNTIME_SMOKE_PASS" and bundle is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
