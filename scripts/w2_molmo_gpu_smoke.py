"""Owner-run offline Molmo2-O-7B FP32 automatic-placement runtime/interface smoke.

This harness never selects a fallback, changes the pinned runner condition, or
performs grounding.  Online snapshot provisioning is a separate command; this
process requires the offline transition before it starts.
"""

import argparse
import binascii
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shlex
import socket
import subprocess
import struct
import sys
from unittest.mock import patch
import zipfile
import zlib


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.provision_molmo2_o_snapshot import (
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
from safeshift.runners.molmo2_o import Molmo2OAdapter, Molmo2ORunner
from safeshift.runners.storage import FileRawStore


PLAN = "configs/pre_freeze/molmo_gpu_smoke.v1.json"
ARTIFACTS = "data/processed/runtime_validation/w2_molmo_gpu_smoke"
GENERATOR_VERSION = "runtime-smoke-geometry-v2-stored-png"
PROMPT_ID = "molmo-runtime-smoke-prompt-v1"
PROMPT = (
    "You are performing an interface smoke test. Inspect the image and return exactly "
    "one JSON object with one key named safety_level. Its value must be one of: "
    "Level01, Level02, Level03, Level04. Do not output markdown or any other text."
)
CASE_IDS = ["RUNTIME_SMOKE_01", "RUNTIME_SMOKE_02"]
MAX_BUNDLE_MEMBER_BYTES = 2 * 1024 * 1024
PINNED_PACKAGES = {
    "torch_distribution": "2.8.0+cu128", "torchvision": "0.23.0+cu128",
    "transformers": "4.57.1", "numpy": "2.2.6", "pillow": "12.3.0",
    "huggingface_hub": "0.36.0", "accelerate": "1.10.1", "einops": "0.8.1",
    "requests": "2.32.5", "safetensors": "0.6.2", "tokenizers": "0.22.1", "jinja2": "3.1.6",
}
# Config bytes are LF UTF-8 and checked against this pin, not just parsed values.
SMOKE_CONFIG_SHA256 = "05c3be0334a15c3b592a5fd0dbf4d9deaedfc055ecadbbee45df65c2b16b425c"
CASE_HASHES = [
    "3a0b33888342ac3008b8fefe76b4f2c9cbc4908d2200e5f592e1cd948da8184e",
    "44e1e4bc6391cab8b9187a46d18cf293ae5507832bba6503a2a22aa1e9a36c05",
]

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
        "schema_version": "molmo-gpu-smoke-plan-v1",
        "status": "PREPARED_NOT_RUN", "validation_scope": "RUNTIME_INTERFACE_ONLY",
        "scope": "SMOKE_ONLY_TECHNICAL_CONFIGURATION", "platform": "PLATFORM_NEUTRAL",
        "model_id": MODEL_ID, "revision": REVISION, "runner_version": "molmo2-o-runner-v1",
        "precision": "FP32", "quantization": "NONE", "device": {"placement": "auto"},
        "hardware": {
            "memory_gate": "OBSERVATIONAL_MEMORY_GATE", "min_vram_bytes": None,
            "min_visible_cuda_gpus": 1, "required_dtype": "torch.float32",
            "placement_policy": "ALL_PARAMETERS_ON_VISIBLE_CUDA_NO_CPU_DISK_META",
            "gpu_name_allowlist": None, "multi_gpu_validated": False,
        },
        "preprocessing": {"mode": "official_processor"},
        "loader": {"processor": "AutoProcessor", "model": "AutoModelForImageTextToText",
                   "trust_remote_code": True, "local_files_only": True},
        "software_environment": {"python": "3.11", "torch_cuda_runtime": "12.8", **PINNED_PACKAGES},
        "decoding": {"do_sample": False, "max_new_tokens": 32},
        "prompt": PROMPT, "prompt_sha256": hashlib.sha256(PROMPT.encode("utf-8")).hexdigest(),
        "number_of_calls": 2, "case_ids": CASE_IDS, "case_image_sha256": CASE_HASHES,
        "generator_version": GENERATOR_VERSION, "task": "classification",
        "claims": dict(CLAIMS), "protocol_freeze_commit_sha": "PENDING",
    }


def load_plan(repo=ROOT):
    path = Path(repo) / PLAN
    if sha256_file(path) != SMOKE_CONFIG_SHA256:
        raise ValueError("SMOKE_CONFIG_HASH_MISMATCH")
    plan = json.loads(path.read_text(encoding="utf-8"))
    if json.dumps(plan, sort_keys=True) != json.dumps(expected_plan(), sort_keys=True):
        raise ValueError("SMOKE_PLAN_CHANGED")
    return plan


def generation_decoding(plan):
    return dict(plan["decoding"])


def geometry_png(image):
    """RGB PNG with filter 0 and explicit DEFLATE stored blocks; no encoder drift."""
    pixels = image.tobytes()
    stride = image.width * 3
    scanlines = b"".join(b"\x00" + pixels[i:i + stride] for i in range(0, len(pixels), stride))
    compressed = bytearray(b"\x78\x01")
    for offset in range(0, len(scanlines), 65535):
        block = scanlines[offset:offset + 65535]
        compressed.append(int(offset + len(block) == len(scanlines)))
        compressed.extend(struct.pack("<HH", len(block), 65535 - len(block)))
        compressed.extend(block)
    compressed.extend(struct.pack(">I", zlib.adler32(scanlines)))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", binascii.crc32(kind + data))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", image.width, image.height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", bytes(compressed)) + chunk(b"IEND", b""))


def generate_cases(repo=ROOT):
    """Return two deterministic, in-memory PNGs independent of SYNTHETIC V1."""
    from PIL import Image, ImageDraw

    result = []
    generator_hash = sha256_file(Path(repo) / "scripts/w2_molmo_gpu_smoke.py")
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
            raw = geometry_png(image)
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
    if [item[1]["image_sha256"] for item in result] != CASE_HASHES:
        raise ValueError("CASE_IMAGE_HASH_MISMATCH")
    return result


def software_versions(torch):
    versions = {name: importlib.metadata.version("torch" if name == "torch_distribution" else name)
                for name in PINNED_PACKAGES}
    return {**versions, "python": platform.python_version(), "torch": str(torch.__version__),
            "torch_cuda_runtime": torch.version.cuda}


def validate_software_versions(versions):
    if tuple(map(int, versions["python"].split(".")[:2])) != (3, 11):
        raise ValueError("REQUIRES_PYTHON_3_11")
    for name, expected in PINNED_PACKAGES.items():
        if versions.get(name) != expected:
            raise ValueError("PINNED_PACKAGE_VERSION_MISMATCH_" + name.upper())
    if versions.get("torch") != PINNED_PACKAGES["torch_distribution"]:
        raise ValueError("TORCH_RUNTIME_VERSION_MISMATCH")
    if versions.get("torch_cuda_runtime") != "12.8":
        raise ValueError("TORCH_CUDA_RUNTIME_MISMATCH")
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
            "fp32_supported": True,  # Fundamental CUDA floating-point type.
            "bf16_supported": _bf16_support(cuda, index),
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
        "compiled_cuda_architectures": list(cuda.get_arch_list()),
        "gpus": gpus,
        "nvidia_smi_inventory": smi_rows,
        "driver_versions": sorted({row["driver_version"] for row in smi_rows}),
    }


def _bf16_support(cuda, index):
    with cuda.device(index):
        return bool(cuda.is_bf16_supported())


def require_cuda_fp32(hardware):
    if not hardware.get("cuda_available"):
        raise ValueError("CUDA_NOT_AVAILABLE")
    count = hardware.get("visible_gpu_count")
    gpus = hardware.get("gpus", [])
    if type(count) is not int or count < 1 or len(gpus) != count:
        raise ValueError("REQUIRES_VISIBLE_CUDA_GPU")
    if [gpu.get("index") for gpu in gpus] != list(range(count)):
        raise ValueError("INVALID_VISIBLE_GPU_INVENTORY")
    if not hardware.get("driver_versions"):
        raise ValueError("GPU_DRIVER_NOT_RECORDED")
    for gpu in gpus:
        if not gpu.get("fp32_supported") or gpu.get("total_memory_bytes", 0) <= 0:
            raise ValueError("FP32_OR_MEMORY_OBSERVATION_MISSING")
    # No unmeasured min-VRAM threshold. Placement, dtype and OOM gate the attempt.
    return True


def memory_snapshot(torch, stage):
    gpus = []
    for index in range(torch.cuda.device_count()):
        free, total = torch.cuda.mem_get_info(index)
        gpus.append({
            "device": f"cuda:{index}", "free_bytes": int(free), "total_bytes": int(total),
            "memory_allocated": int(torch.cuda.memory_allocated(index)),
            "memory_reserved": int(torch.cuda.memory_reserved(index)),
            "max_memory_allocated": int(torch.cuda.max_memory_allocated(index)),
            "max_memory_reserved": int(torch.cuda.max_memory_reserved(index)),
        })
    return {"stage": stage, "gpus": gpus, "performance_claim": False}


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


def inspect_model_placement(model, visible_gpu_count):
    parameters = list(model.parameters())
    parameter_census = _tensor_census(parameters)
    buffer_census = _tensor_census(model.buffers())
    visible = {f"cuda:{index}" for index in range(visible_gpu_count)}
    device_map = getattr(model, "hf_device_map", None)
    observed_map = None if device_map is None else {str(k): str(v) for k, v in device_map.items()}
    destinations = set((observed_map or {}).values())
    disk = "disk" in destinations
    cpu = "cpu" in destinations or "cpu" in parameter_census["distinct_devices"]
    violations = []
    if not parameters:
        violations.append("NO_MODEL_PARAMETERS_OBSERVED")
    if any(row["device"] not in visible for row in parameter_census["tensors"]):
        violations.append("PARAMETERS_OUTSIDE_VISIBLE_CUDA")
    if "meta" in buffer_census["distinct_devices"]:
        violations.append("META_BUFFER")
    if cpu or disk or "meta" in destinations:
        violations.append("CPU_DISK_META_OFFLOAD")
    if str(model.device) not in visible:
        violations.append("MODEL_INPUT_DEVICE_OUTSIDE_VISIBLE_CUDA")
    return {
        "policy": "ALL_PARAMETERS_ON_VISIBLE_CUDA_NO_CPU_DISK_META",
        "model_device": str(model.device), "hf_device_map": observed_map,
        "visible_gpu_count": visible_gpu_count, "parameters": parameter_census,
        "buffers": buffer_census, "cpu_placement": cpu, "disk_offload_detected": disk,
        "offload_observation_basis": "HF_DEVICE_MAP_AND_PARAMETER_DEVICES",
        "cpu_parameter_count": parameter_census["by_device"].get("cpu", {}).get("tensor_count", 0),
        "meta_parameter_count": parameter_census["by_device"].get("meta", {}).get("tensor_count", 0),
        "gpu_parameter_counts": {device: parameter_census["by_device"].get(device, {}).get("tensor_count", 0)
                                 for device in sorted(visible)},
        "violations": sorted(set(violations)), "passed": not violations,
    }


def inspect_model_dtypes(model):
    floating = [parameter for parameter in model.parameters() if _is_floating(parameter)]
    census = _tensor_census(floating)
    deviations = {
        dtype: values for dtype, values in census["by_dtype"].items()
        if dtype != "torch.float32"
    }
    passed = bool(floating) and not deviations and "torch.float32" in census["by_dtype"]
    return {
        "expected_primary_dtype": "torch.float32",
        "silent_cast": False,
        "policy": "ANY_NON_FP32_FLOATING_PARAMETER_REQUIRES_BLOCKING_REVIEW",
        "floating_parameter_census": census,
        "deviations": deviations,
        "status": "EXPECTED_FP32_ONLY" if passed else "DTYPE_DEVIATION_REVIEW_REQUIRED",
        "passed": passed,
    }




class NetworkFirewall:
    def __init__(self):
        self.violation_count = 0

    def deny(self, *args, **kwargs):
        self.violation_count += 1
        raise RuntimeError("NETWORK_FORBIDDEN_DURING_MOLMO_SMOKE")


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
            if path.is_symlink() or path.resolve().parent != run_root:
                raise ValueError("UNSAFE_REPORT_EVIDENCE_PATH")
            members.append((name, path))
        elif report["status"] == "RUNTIME_SMOKE_PASS":
            raise ValueError("MISSING_PASS_REPORT")
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
    if len({name for name, _ in members}) != len(members):
        raise ValueError("DUPLICATE_BUNDLE_MEMBER")
    if report["status"] == "RUNTIME_SMOKE_PASS" and len(members) != 10:
        raise ValueError("INCOMPLETE_PASS_BUNDLE")
    archive_path = run_root / "molmo_gpu_smoke_evidence.zip"
    sidecar_path = run_root / "molmo_gpu_smoke_evidence.zip.sha256"
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
        "schema_version": "molmo-gpu-runtime-report-v1",
        "validation_scope": "RUNTIME_INTERFACE_ONLY",
        "run_id": run_id,
        "started_at_utc": _now(clock),
        "finished_at_utc": None,
        "git_commit": None,
        "execution_pin": None,
        "execution_identity_verified": False,
        "model_id": MODEL_ID,
        "requested_model_id": MODEL_ID,
        "resolved_repository_id": RESOLVED_REPOSITORY_ID,
        "revision": REVISION,
        "runner_version": None,
        "smoke_config_sha256": None,
        "prompt_sha256": None,
        "cases": [],
        "installed_distributions": [],
        "output_observation": None,
        "snapshot_verification": None,
        "custom_remote_code": {
            "trust_remote_code": True,
            "local_files_only": True,
            "snapshot_path_identity": (
                "models--allenai--Molmo2-O-7B/snapshots/" + REVISION
            ),
            "critical_source_hashes": [],
        },
        "hardware": None,
        "software_versions": {},
        "environment": {},
        "precision": "FP32",
        "quantization": "NONE",
        "device": {"placement": "auto"},
        "decoding": {"do_sample": False, "max_new_tokens": 32},
        "parameter_placement": None,
        "buffer_placement": None,
        "dtype_evidence": None,
        "memory_gate": "OBSERVATIONAL_MEMORY_GATE",
        "hardware_validated": False,
        "memory": [],
        "calls": [],
        "notes": [],
        "blocker": None,
        "runtime_check_failure": None,
        "rerun_of": rerun_of,
        "rerun_reason": rerun_reason,
        "status": "RUNTIME_SMOKE_FAIL",
        "load_lifecycles": 0,
        "initialize_lifecycles": 0,
        "grounding": {"status": "DOCUMENTED_NATIVE_POINT", "qualification": "NOT_YET_QUALIFIED",
                      "box_iou_participation": "NOT_PARTICIPATING"},
        "native_generate_calls": 0,
        "native_errors": [],
        "network_policy": "OFFLINE_ENV_AND_COUNTING_TCP_UDP_DNS_DENIAL",
        "network_violation_count": 0,
        "claims": dict(CLAIMS),
        "protocol_freeze_commit_sha": "PENDING",
        "failure_rerun_policy": "NO_AUTOMATIC_RERUN_OR_FALLBACK",
        "bundle": {
            "filename": "molmo_gpu_smoke_evidence.zip",
            "sha256_sidecar": "molmo_gpu_smoke_evidence.zip.sha256",
            "creation": "AFTER_RUNTIME_REPORT",
        },
    }


def run_smoke(run_id, *, repo=ROOT, rerun_of=None, rerun_reason=None,
              runner_factory=Molmo2ORunner, torch_module=None, clock=None):
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
        stage = "EXECUTION_IDENTITY"
        report["execution_pin"] = os.environ.get("B3B_PREP_HEAD")
        safe_environment_names = (
            "B3B_PREP_HEAD",
            "HF_HUB_OFFLINE",
            "TRANSFORMERS_OFFLINE",
            "HF_HUB_DISABLE_TELEMETRY",
            "CUDA_VISIBLE_DEVICES",
            "PYTORCH_CUDA_ALLOC_CONF",
        )
        report["environment"] = {
            name: os.environ.get(name) for name in safe_environment_names
        }
        report["git_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip()
        if report["execution_pin"] is None:
            raise ValueError("B3B_PREP_HEAD_REQUIRED")
        if re.fullmatch(r"[0-9a-f]{40}", report["execution_pin"]) is None:
            raise ValueError("B3B_PREP_HEAD_INVALID")
        if report["git_commit"] != report["execution_pin"]:
            raise ValueError("EXECUTION_COMMIT_MISMATCH")
        tracked_changes = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo, text=True,
        ).strip()
        if tracked_changes:
            raise ValueError("TRACKED_WORKTREE_DIRTY")
        committed_plan = subprocess.check_output(["git", "show", "HEAD:" + PLAN], cwd=repo)
        if hashlib.sha256(committed_plan).hexdigest() != report["smoke_config_sha256"]:
            raise ValueError("COMMITTED_CONFIG_HASH_MISMATCH")
        report["execution_identity_verified"] = True
        stage = "OFFLINE_PREFLIGHT"
        if any(os.environ.get(name) != "1" for name in (
            "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"
        )):
            raise ValueError("SET_ALL_OFFLINE_VARIABLES_BEFORE_PROCESS_START")
        with patch.object(socket.socket, "connect", firewall.deny), \
                patch.object(socket.socket, "connect_ex", firewall.deny), \
                patch.object(socket.socket, "sendto", firewall.deny), \
                patch.object(socket, "create_connection", firewall.deny), \
                patch.object(socket, "getaddrinfo", firewall.deny):
            stage = "SOFTWARE_PREFLIGHT"
            if torch_module is None:
                import torch as torch_module
            torch = torch_module
            report["software_versions"] = software_versions(torch)
            validate_software_versions(report["software_versions"])
            report["installed_distributions"] = sorted(
                [{"name": d.metadata["Name"], "version": d.version} for d in importlib.metadata.distributions()],
                key=lambda d: d["name"].lower(),
            )
            stage = "GPU_PREFLIGHT"
            report["hardware"] = probe_hardware(torch)
            require_cuda_fp32(report["hardware"])
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
                "schema_version": "molmo-runtime-smoke-cases-v1",
                "generator_version": GENERATOR_VERSION,
                "cases": report["cases"],
                "generated_image_binaries_persisted": False,
                "semantic_accuracy_use": False,
            })
            for device_index in range(report["hardware"]["visible_gpu_count"]):
                torch.cuda.reset_peak_memory_stats(device_index)
            report["memory"].append(memory_snapshot(torch, "before_load"))
            runner = runner_factory()
            adapter = Molmo2OAdapter()
            report["runner_version"] = runner.version
            store = FileRawStore(repo, ARTIFACTS + "/" + run_id + "/raw")
            if (runner.identity.model_id != MODEL_ID or runner.identity.immutable_revision != REVISION
                    or runner.version != plan["runner_version"]):
                raise ValueError("RUNNER_IDENTITY_MISMATCH")
            original_initialize = runner.initialize
            original_load = runner.load
            initialized = False

            def observed_initialize(context):
                nonlocal initialized
                if not initialized:
                    original_initialize(context)
                    initialized = True
                    report["initialize_lifecycles"] += 1
                else:
                    runner._check_condition(context)

            runner.initialize = observed_initialize
            loaded_model = None

            def observed_load(context):
                nonlocal loaded_model
                if firewall.violation_count:
                    raise ValueError("NETWORK_VIOLATION")
                if loaded_model is not None:
                    runner._check_condition(context)
                    if runner._resources[1] is not loaded_model:
                        raise ValueError("MODEL_RELOADED_BETWEEN_CALLS")
                    return
                try:
                    original_load(context)
                except Exception as exc:
                    report["native_errors"].append({
                        "stage": "load", "exception_type": type(exc).__name__
                    })
                    raise
                model = runner._resources[1] if runner._resources is not None else None
                if model is None:
                    raise ValueError("RUNNER_DID_NOT_PUBLISH_MODEL")
                if Path(model.config.name_or_path).resolve() != Path(snapshot).resolve():
                    raise ValueError("LOADED_SNAPSHOT_DIFFERS_FROM_VERIFIED_SNAPSHOT")
                loaded_model = model
                report["load_lifecycles"] += 1
                report["memory"].append(memory_snapshot(torch, "after_load"))
                placement = inspect_model_placement(model, report["hardware"]["visible_gpu_count"])
                report["parameter_placement"] = {
                    key: value for key, value in placement.items() if key != "buffers"
                }
                report["buffer_placement"] = placement["buffers"]
                report["dtype_evidence"] = inspect_model_dtypes(model)
                if not placement["passed"]:
                    report["runtime_check_failure"] = "PARAMETER_PLACEMENT_VIOLATION"
                    raise ValueError("PARAMETER_PLACEMENT_VIOLATION")
                if not report["dtype_evidence"]["passed"]:
                    report["runtime_check_failure"] = "DTYPE_DEVIATION_REVIEW_REQUIRED"
                    raise ValueError("DTYPE_DEVIATION_REVIEW_REQUIRED")
                native_generate = model.generate

                def observed_generate(*args, **kwargs):
                    if firewall.violation_count:
                        raise ValueError("NETWORK_VIOLATION")
                    if report["native_generate_calls"] >= 2:
                        report["native_errors"].append({"stage": "generate", "code": "THIRD_CALL_FORBIDDEN"})
                        raise ValueError("THIRD_CALL_FORBIDDEN")
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
            if len(cases) != 2 or [metadata["case_id"] for _, metadata in cases] != CASE_IDS:
                raise ValueError("EXACT_TWO_CASES_REQUIRED")
            for index, (image_bytes, case_metadata) in enumerate(cases, 1):
                if firewall.violation_count:
                    raise ValueError("NETWORK_VIOLATION")
                command = ["python", "scripts/w2_molmo_gpu_smoke.py", "--run-id", run_id]
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
                and report["initialize_lifecycles"] == 1
                and report["native_generate_calls"] == 2
                and not report["native_errors"]
                and report["parameter_placement"]["passed"]
                and report["dtype_evidence"]["passed"]
                and len(report["memory"]) == 4
                and all(call["parse_status"] in {"SUCCESS", "INVALID"}
                        for call in report["calls"])
            ):
                report["status"] = "RUNTIME_SMOKE_PASS"
            if len(report["calls"]) == 2 and all(call["raw_output"] for call in report["calls"]):
                report["output_observation"] = {
                    "status": "RUNTIME_OBSERVATION",
                    "input_hashes_distinct": len({case["image_sha256"] for case in report["cases"]}) == 2,
                    "raw_hashes_identical": report["calls"][0]["raw_output"]["sha256"] == report["calls"][1]["raw_output"]["sha256"],
                    "semantic_interpretation": "NONE",
                }
    except Exception as exc:
        report["status"] = "RUNTIME_SMOKE_FAIL"
        if report["blocker"] is None:
            report["blocker"] = {
                "stage": stage,
                "exception_type": type(exc).__name__,
                "code": str(exc) if type(exc) is ValueError and re.fullmatch(r"[A-Z0-9_]+", str(exc)) else "RUNTIME_EXCEPTION",
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
            "schema_version": "molmo-gpu-smoke-environment-v1",
            "hardware": report["hardware"],
            "software_versions": report["software_versions"],
            "installed_distributions": report["installed_distributions"],
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
