"""Pinned Phi/CLIP eager configuration, shared by CPU admission and real loading.

Only in-memory config copies change. Checkpoint and remote source bytes stay intact.
No ML import, download or device initialization happens at module import time.
"""
from contextlib import contextmanager, nullcontext
from copy import deepcopy
import importlib
from pathlib import Path
from unittest.mock import patch

from .artifacts import read, sha
from .contract import MODELS

PHI_ATTENTION_FILES = ("config.json", "configuration_phi3_v.py", "modeling_phi3_v.py")


def verified_sources(repo, snapshot):
    from .backend import check_source_review
    locked = check_source_review(repo, "phi")
    snapshot = Path(snapshot)
    hashes = {name: sha(snapshot / name) for name in PHI_ATTENTION_FILES}
    if any(hashes[name] != locked["files"][name] for name in hashes):
        raise ValueError("PHI_ATTENTION_SOURCE_CHECKSUM")
    payload = read(snapshot / "config.json")
    if payload.get("auto_map") != {
            "AutoConfig": "configuration_phi3_v.Phi3VConfig",
            "AutoModelForCausalLM": "modeling_phi3_v.Phi3VForCausalLM"}:
        raise ValueError("PHI_ATTENTION_AUTO_MAP")
    return hashes, payload


def require_eager(config, path="config"):
    # The public to_dict() omits this private state in Transformers 4.43.3.
    if (config._attn_implementation != "eager"
            or config._attn_implementation_internal != "eager"):
        error = ValueError("PHI_EXPLICIT_EAGER_CONFIG_REQUIRED:" + path)
        error.subcomponent = path
        raise error


@contextmanager
def eager_phi(repo, snapshot):
    """Yield explicit config/model class and a receipt, before reading any weights."""
    hashes, payload = verified_sources(repo, snapshot)  # Before any remote import.
    import transformers
    from transformers.dynamic_module_utils import get_class_from_dynamic_module
    spec = MODELS["phi"]
    if transformers.__version__ != spec["transformers"]:
        raise RuntimeError("PHI_PINNED_TRANSFORMERS_REQUIRED")
    kwargs = {"local_files_only": True, "trust_remote_code": True,
              "revision": spec["revision"], "code_revision": spec["revision"]}
    config = transformers.AutoConfig.from_pretrained(str(snapshot), **kwargs,
                                                       attn_implementation="eager")
    observed = config._attn_implementation
    config = deepcopy(config)
    # from_dict() consumes the kwarg first, then JSON's private setter overwrites
    # it. Set the property AFTER deserialization and pass the config explicitly.
    config._attn_implementation = "eager"
    require_eager(config)
    model_class = get_class_from_dynamic_module(payload["auto_map"]["AutoModelForCausalLM"],
                                                str(snapshot), **kwargs)
    module = importlib.import_module(model_class.__module__)
    # Phi constructs CLIP from this independent module constant, not Phi's config.
    # Leaving its internal value None makes Transformers auto-select SDPA.
    clip = deepcopy(module.CLIP_VIT_LARGE_PATCH14_336_CONFIG)
    clip._attn_implementation = "eager"
    require_eager(clip)
    receipt = {"schema": "safeshift-phi-eager-v1", "revision": spec["revision"],
               "transformers": transformers.__version__, "source_files": hashes,
               "checkpoint_attention": payload.get("_attn_implementation"),
               "deserialized_attention": observed, "requested_attention": "eager",
               "effective_phi_attention": config._attn_implementation,
               "effective_clip_attention": clip._attn_implementation,
               "checkpoint_modified": False}
    with patch.object(module, "CLIP_VIT_LARGE_PATCH14_336_CONFIG", clip):
        yield config, model_class, module, receipt


def attention_receipt(model):
    """Observe every config before enforcing constraints, including failure state."""
    configs = {"model.config": model.config, "model.model.config": model.model.config}
    vision = model.model.vision_embed_tokens.img_processor
    configs["model.model.vision_embed_tokens.img_processor.config"] = vision.config
    classes = {}
    for prefix, layers in (("decoder", model.model.layers),
                           ("vision", vision.vision_model.encoder.layers)):
        for index, layer in enumerate(layers):
            path = f"{prefix}.{index}.self_attn"
            configs[path + ".config"] = layer.self_attn.config
            classes[path] = type(layer.self_attn).__module__ + "." + type(layer.self_attn).__name__
    return {"configs": {path: {"class": type(cfg).__name__,
                              "effective": cfg._attn_implementation,
                              "internal": cfg._attn_implementation_internal}
                        for path, cfg in configs.items()},
            "cached_phi": model.model._attn_implementation, "classes": classes}


def verify_phi_attention(model, module):
    observed = attention_receipt(model)
    try:
        return {**_verify_phi_attention(model, module), "observed": observed}
    except BaseException as error:
        error.phi_attention_receipt = {"status": "FAIL", **observed,
                                       "failed_constraint": str(error)}
        raise


def _verify_phi_attention(model, module):
    """Check actual language AND vision modules, not just the loading kwarg."""
    from transformers.models.clip.modeling_clip import CLIPAttention
    require_eager(model.config, "model.config")
    require_eager(model.model.config, "model.model.config")
    if model.model._attn_implementation != "eager":
        raise ValueError("PHI_CACHED_ATTENTION_NOT_EAGER")
    decoder = list(model.model.layers)
    vision = model.model.vision_embed_tokens.img_processor
    require_eager(vision.config, "model.model.vision_embed_tokens.img_processor.config")
    layers = list(vision.vision_model.encoder.layers)
    if (len(decoder) != model.config.num_hidden_layers
            or len(layers) != vision.config.num_hidden_layers or not decoder or not layers):
        raise ValueError("PHI_ATTENTION_LAYER_COVERAGE")
    for index, layer in enumerate(decoder):
        if type(layer.self_attn) is not module.Phi3Attention:
            raise ValueError("PHI_NON_EAGER_DECODER_ATTENTION")
        require_eager(layer.self_attn.config, f"decoder.{index}.self_attn.config")
    for index, layer in enumerate(layers):
        if type(layer.self_attn) is not CLIPAttention:
            raise ValueError("PHI_NON_EAGER_VISION_ATTENTION")
        require_eager(layer.self_attn.config, f"vision.{index}.self_attn.config")
    for _, part in model.named_modules():
        name = type(part).__name__.lower()
        if "flash" in name or "sdpa" in name or "attentionfa2" in name:
            raise ValueError("PHI_UNEXPECTED_ATTENTION_MODULE:" + type(part).__name__)
    return {"status": "VERIFIED_EAGER_MODULES", "decoder_layers": len(decoder),
            "vision_layers": len(layers), "decoder_class": module.Phi3Attention.__name__,
            "vision_class": CLIPAttention.__name__}


def load_phi(model_class, config, snapshot=None, *, meta=False):
    """Shared real loader. Auto-only code_revision/trust kwargs end at resolution.

    The reviewed dynamic class is already resolved by eager_phi. Passing
    code_revision to this class would leak it into Phi's __init__ in 4.43.3.
    """
    import torch
    if snapshot is None and not meta:
        raise ValueError("PHI_PRODUCTION_SNAPSHOT_REQUIRED")
    kwargs = {"config": config, "local_files_only": True, "revision": MODELS["phi"]["revision"],
              "torch_dtype": torch.float16, "attn_implementation": "eager", "use_safetensors": True}
    if meta:
        kwargs["state_dict"] = {}
    else:
        kwargs["device_map"] = {"": 0}
    with torch.device("meta") if meta else nullcontext():
        return model_class.from_pretrained(str(snapshot) if snapshot is not None else None, **kwargs)


def cpu_attention_probe(repo):
    """Config/code only; build a full meta skeleton, without weights/CUDA/forward."""
    from .backend import check_source_review
    check_source_review(repo, "phi")
    from huggingface_hub import snapshot_download
    spec = MODELS["phi"]
    snapshot = Path(snapshot_download(spec["id"], revision=spec["revision"],
                                      allow_patterns=list(PHI_ATTENTION_FILES)))
    if snapshot.name != spec["revision"]:
        raise ValueError("PHI_ATTENTION_SNAPSHOT_REVISION")
    import torch
    with eager_phi(repo, snapshot) as (config, cls, module, receipt):
        # Exercise the REAL loader, not _from_config. None + an empty state_dict
        # is the documented no-checkpoint input. No tensor data is allocated.
        model = load_phi(cls, config, meta=True)
        receipt["modules"] = verify_phi_attention(model, module)
        receipt["parameter_count"] = sum(p.numel() for p in model.parameters())
        receipt["fp16_parameter_bytes"] = receipt["parameter_count"] * 2
        receipt["memory_limit"] = "PARAMETER_FOOTPRINT_ONLY_NOT_PEAK_RAM_VRAM_OR_FIT_PROOF"
        if any(t.device.type != "meta" for t in (*model.parameters(), *model.buffers())):
            raise ValueError("PHI_CPU_PROBE_MUST_REMAIN_META_ONLY")
    return {**receipt, "status": "CPU_META_FROM_PRETRAINED_PASS_NOT_WEIGHT_LOAD",
            "loader": "reviewed_remote_class.from_pretrained(None,state_dict={})",
            "weights": "NOT_DOWNLOADED", "cuda": "NOT_CALLED", "forward": "NOT_RUN"}
