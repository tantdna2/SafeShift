"""Metadata/static preflight and lazy, measured production environment observation."""

import importlib.metadata
import platform
import zlib

from safeshift.protocol.classification_policy import ROOT, load_policy
from .internvl3_snapshot import require_offline_env


def software_observation(entry):
    return {name: (platform.python_version() if name == "python" else
                   zlib.ZLIB_RUNTIME_VERSION if name == "zlib" else importlib.metadata.version(name))
            for name in entry["software_versions"]}


def runtime_observation(model, repo=ROOT):
    """Called only after production authority; never invoked by static preflight."""
    require_offline_env()
    entry = load_policy(repo)["classification"][model]
    software = software_observation(entry)
    if software != entry["software_versions"]:
        raise ValueError("EXACT_SOFTWARE_PINS_REQUIRED")
    if (platform.system(), platform.machine()) != ("Linux", "x86_64"):
        raise ValueError("LINUX_X86_64_REQUIRED")
    import torch
    if model == "qwen3":
        from scripts.w2_qwen_kaggle_smoke import probe_hardware, require_t4_pair
        evidence = probe_hardware(torch)
        require_t4_pair(evidence)
        count = evidence["gpu_count"]
        cc = evidence["gpus"][0]["compute_capability"]
    elif model == "qwen2_5":
        from scripts.w2_qwen2_5_t4_smoke import probe_hardware
        evidence = probe_hardware(torch)
        count, cc = evidence["visible_gpu_count"], evidence["compute_capability"]
    elif model == "internvl3":
        from .internvl3 import probe_hardware
        evidence = probe_hardware(torch)
        count, cc = evidence["visible_gpu_count"], evidence["compute_capability"]
    else:
        from .moondream2 import validate_device
        available, count = torch.cuda.is_available(), torch.cuda.device_count()
        if not available or count != 1:
            raise ValueError("EXACTLY_ONE_NVIDIA_T4_REQUIRED")
        prop = torch.cuda.get_device_properties(0)
        cc = [prop.major, prop.minor]
        validate_device({"cuda_available": available, "gpu_count": count, "name": prop.name,
                         "compute_capability": cc, "total_memory": prop.total_memory})
    hardware = {"os": platform.system(), "architecture": platform.machine(), "gpu": "NVIDIA_T4",
                "visible_gpu_count": count, "compute_capability": cc, "cuda_runtime": torch.version.cuda,
                "cpu_offload": False, "disk_offload": False, "automatic_fallback": False}
    # Offload/precision flags are also enforced by native loaded-state checks;
    # no observation is returned by the bridge until those checks succeed.
    if hardware != entry["hardware_contract"]:
        raise ValueError("EXACT_HARDWARE_CONTRACT_REQUIRED")
    return {"software_versions": software, "hardware": hardware}


def static_preflight(repo=ROOT):
    from safeshift.protocol.freeze_candidate import verify_candidate
    from .p2_harness import identities, contract
    from .p2_bridge import REGISTRY, VERSION
    identities(repo)
    verify_candidate(repo)
    c = contract(repo)
    return {"status": "PROTOCOL_FREEZE_REQUIRED", "bridge_version": VERSION,
            "models": list(REGISTRY), "protocol_freeze": c["protocol_freeze"],
            "inspecsafe_inference_authorized": c["inspecsafe_inference_authorized"],
            "runtime_observation": "NOT_EXECUTED_IN_CODEX", "dataset_read": False,
            "model_load": False, "ready_to_run_inspecsafe": False}
