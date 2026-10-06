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
    from .p2_harness import _git, authorize_production, identities, contract
    from .p2_bridge import REGISTRY, VERSION
    identities(repo)
    c = contract(repo)
    if c["protocol_freeze"] != "FROZEN":
        verify_candidate(repo)
        return {"status": "PROTOCOL_FREEZE_REQUIRED", "bridge_version": VERSION,
                "models": list(REGISTRY), "protocol_freeze": c["protocol_freeze"],
                "inspecsafe_inference_authorized": c["inspecsafe_inference_authorized"],
                "static_authority_declared": False, "effective_authorization": False,
                "runtime_observation": "NOT_EXECUTED", "dataset_read": False,
                "model_load": False, "ready_to_run_inspecsafe": False}
    candidate_path = c["freeze_candidate_path"]
    candidate = _git(repo, "show", f"HEAD:{candidate_path}")
    from safeshift.data.p2_execution import sha
    if sha(candidate) != c["freeze_candidate_sha256"]:
        raise ValueError("FREEZE_CANDIDATE_HASH_MISMATCH")
    try:
        head, authority = authorize_production(repo)
    except PermissionError:
        return {"status": "FINAL_MERGE_REQUIRED", "bridge_version": VERSION,
                "models": list(REGISTRY), "protocol_freeze": c["protocol_freeze"],
                "inspecsafe_inference_authorized": c["inspecsafe_inference_authorized"],
                "authority_status": "FROZEN", "static_authority_declared": True,
                "effective_authorization": False, "runtime_observation": "NOT_EXECUTED",
                "dataset_read": False, "model_load": False,
                "ready_to_run_inspecsafe": False}
    return {"status": "AUTHORIZED_FOR_OWNER_RUNTIME_PREFLIGHT", "bridge_version": VERSION,
            "models": list(REGISTRY), "protocol_freeze": c["protocol_freeze"],
            "inspecsafe_inference_authorized": c["inspecsafe_inference_authorized"],
            "authority_status": authority["status"], "static_authority_declared": True,
            "effective_authorization": True, "effective_authorization_head": head,
            "runtime_observation": "NOT_EXECUTED", "dataset_read": False,
            "model_load": False, "ready_to_run_inspecsafe": True}
