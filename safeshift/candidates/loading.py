"""Pinned class/processor loading, explicit eager attention; no automatic downloads."""
import inspect
from contextlib import contextmanager
from pathlib import Path
from safeshift.pilot.artifacts import read, sha
from .source import LOCK, require, verify_snapshot, snapshot_stat, verify_module_cache


def checkpoint_index(path, key):
    spec = read(LOCK)[key]
    locked = read(LOCK.with_name("checkpoint_metadata_lock.json"))[key]
    require(all(locked[n] == spec[n] for n in ("id", "revision")), "CHECKPOINT_IDENTITY")
    snapshot_stat(Path(path))
    require(Path(path).stat().st_size == locked["index"]["size"] and
            sha(path) == locked["index"]["sha256"], "CHECKPOINT_INDEX_CHECKSUM")
    index = read(path)
    require(len(index["weight_map"]) == locked["index"]["tensor_count"] and
            set(index["weight_map"].values()) == set(locked["weights"]), "CHECKPOINT_INDEX_MAPPING")
    return index


def verify_weights(path, key):
    """Offline only. Metadata hashes are public LFS identities, not downloaded weights."""
    path = Path(path)
    locked = read(LOCK.with_name("checkpoint_metadata_lock.json"))[key]
    snapshot_stat(path, directory=True)
    require({p.name for p in path.iterdir()} == {*locked["weights"], locked["index"]["filename"]},
            "WEIGHTS_EXACT_ALLOWLIST")
    checkpoint_index(path / locked["index"]["filename"], key)
    for name, entry in locked["weights"].items():
        snapshot_stat(path / name)
        require((path / name).stat().st_size == entry["size"] and sha(path / name) == entry["sha256"],
                "WEIGHT_CHECKSUM:" + name)
    return locked


def load_weight_model(snapshot, key, config, model_class, weights, device):
    """Prepared offline runtime loader. Caller must hold a separate reviewed grant.

    No downloader, quantization, AutoModel re-import or attention fallback.
    This path is NOT executed by the CPU rehearsal.
    """
    import torch
    from transformers import GenerationConfig
    verify_snapshot(snapshot, key)
    verify_weights(weights, key)
    explicit_eager(config)
    model = model_class.from_pretrained(str(weights), config=config, local_files_only=True,
        torch_dtype=torch.float16, attn_implementation="eager", use_safetensors=True,
        device_map={"": device}).eval()
    receipt = verify_attention(model, key)
    model.generation_config = GenerationConfig.from_pretrained(str(snapshot), local_files_only=True)
    require(all(p.dtype == torch.float16 and p.device.type != "meta" for p in model.parameters()),
            "LOADED_FP16_PARAMETERS_REQUIRED")
    return model, receipt


def explicit_eager(config):
    for cfg in (config, getattr(config, "text_config", None), getattr(config, "vision_config", None)):
        if cfg is not None:
            cfg._attn_implementation = "eager"


@contextmanager
def meta_context():
    """Real constructor/empty-state loader only; never execute a model forward."""
    import torch
    from accelerate import init_empty_weights
    with init_empty_weights(include_buffers=False), torch.device("meta"):
        yield


def verify_attention(model, key):
    """Inspect every attention layer, not just the outer deserialized config."""
    if key == "internvl35":
        from transformers.models.qwen3.modeling_qwen3 import Qwen3Attention
        from transformers.models.internvl.modeling_internvl import InternVLVisionAttention
        groups = (("text", model.model.language_model.layers, "self_attn", Qwen3Attention, 36),
                  ("vision", model.model.vision_tower.encoder.layer, "attention", InternVLVisionAttention, 24))
    elif key == "minicpm4":
        from transformers.models.llama.modeling_llama import LlamaAttention
        import importlib
        vision_module = importlib.import_module(type(model.vpm).__module__)
        groups = (("text", model.llm.model.layers, "self_attn", LlamaAttention, 32),
                  ("vision", model.vpm.encoder.layers, "self_attn", vision_module.SiglipAttention, 27))
    else:
        raise ValueError("UNKNOWN_CANDIDATE")
    layers = {}
    require(model.config._attn_implementation == "eager", "OUTER_EAGER_REQUIRED")
    for group, blocks, attr, cls, count in groups:
        require(len(blocks) == count, "ATTENTION_LAYER_COUNT:" + group)
        for index, block in enumerate(blocks):
            attention = getattr(block, attr)
            require(type(attention) is cls, "ATTENTION_CLASS:" + group)
            cfg = getattr(attention, "config", None)
            if cfg is not None:
                require(cfg._attn_implementation == "eager", "LAYER_EAGER_REQUIRED:" + group)
            layers[f"{group}.{index}"] = type(attention).__name__
    for name, module in model.named_modules():
        cfg = getattr(module, "config", None)
        if cfg is not None and hasattr(cfg, "_attn_implementation"):
            require(cfg._attn_implementation == "eager" and cfg._attn_implementation_internal == "eager",
                    "NESTED_EAGER_REQUIRED:" + name)
        require(not any(s in type(module).__name__.lower() for s in ("flashattention", "sdpaattention")),
                "ACCELERATED_ATTENTION_FORBIDDEN:" + name)
        if hasattr(module, "_use_flash_attention_2"):
            require(module._use_flash_attention_2 is False, "CACHED_FLASH_ATTENTION:" + name)
    return {"status": "EAGER_MODULES_VERIFIED", "layers": layers}


def load_meta_model(snapshot, key, config, model_class):
    """Exercise native from_pretrained with an empty state, no weight file/forward.

    This is a loader/config/module rehearsal, never a weight-deserialization test.
    Runtime loading remains gated on a separately reviewed checkpoint and grant.
    """
    import torch
    from transformers import GenerationConfig
    verify_snapshot(snapshot, key)
    explicit_eager(config)
    with meta_context():
        model = model_class.from_pretrained(None, config=config, state_dict={},
            local_files_only=True, torch_dtype=torch.float16, attn_implementation="eager").eval()
    model.generation_config = GenerationConfig.from_pretrained(str(snapshot), local_files_only=True)
    require(all(p.device.type == "meta" and p.dtype == torch.float16 for p in model.parameters()),
            "META_FP16_PARAMETERS_REQUIRED")
    receipt = verify_attention(model, key)
    receipt.update(scope="EMPTY_STATE_META_LOADER_NOT_WEIGHTS_OR_INFERENCE",
                   parameters=sum(p.numel() for p in model.parameters()),
                   buffer_devices={n: str(b.device) for n, b in model.named_buffers()})
    return model, receipt

def native_setup(snapshot, key, evidence):
    import importlib.metadata
    import os
    import sys
    from unittest.mock import patch
    spec = verify_snapshot(Path(snapshot), key)
    versions = {"internvl35": "4.55.4", "minicpm4": "4.51.3"}
    require(importlib.metadata.version("transformers") == versions[key], "PINNED_TRANSFORMERS_REQUIRED")
    if key == "minicpm4":
        require(Path(snapshot).name == spec["revision"], "REVISION_NAMED_STAGED_SOURCE_REQUIRED")
        from transformers.dynamic_module_utils import HF_MODULES_CACHE
        require("HF_MODULES_CACHE" in os.environ and Path(HF_MODULES_CACHE).absolute() ==
                Path(os.environ["HF_MODULES_CACHE"]).absolute(), "DEDICATED_REMOTE_CACHE_REQUIRED")
        verify_module_cache(HF_MODULES_CACHE, spec)
        with patch.object(sys, "dont_write_bytecode", True):
            result = _native_setup(snapshot, key, evidence)
        verify_module_cache(HF_MODULES_CACHE, spec)
        return result
    return _native_setup(snapshot, key, evidence)


def _native_setup(snapshot, key, evidence):
    verify_snapshot(snapshot, key)
    import transformers
    opts = dict(local_files_only=True, trust_remote_code=key == "minicpm4")
    spec = read(LOCK)[key]
    opts.update(revision=spec["revision"], code_revision=spec["revision"])
    processor = transformers.AutoProcessor.from_pretrained(str(snapshot), **opts)
    tokenizer = transformers.AutoTokenizer.from_pretrained(str(snapshot), **opts)
    config = transformers.AutoConfig.from_pretrained(str(snapshot), **opts)
    require(processor.tokenizer.get_vocab() == tokenizer.get_vocab(), "TOKENIZER_PROCESSOR_VOCAB_MISMATCH")
    if key == "internvl35":
        from transformers.models.auto.modeling_auto import MODEL_FOR_IMAGE_TEXT_TO_TEXT_MAPPING
        model_class = MODEL_FOR_IMAGE_TEXT_TO_TEXT_MAPPING[type(config)]
    else:
        from transformers.dynamic_module_utils import get_class_from_dynamic_module
        model_class = get_class_from_dynamic_module(config.auto_map["AutoModel"], str(snapshot),
                                                    local_files_only=True, revision=spec["revision"],
                                                    code_revision=spec["revision"])
    # Import and map the real class. Do not instantiate it or claim weight loading.
    evidence["native_classes"] = {name: type(obj).__name__ for name, obj in
                                  (("processor", processor), ("tokenizer", tokenizer), ("config", config))}
    evidence["native_classes"]["model_import_only"] = model_class.__name__
    evidence["trust_remote_code"] = opts["trust_remote_code"]
    fields = (("crop_to_patches", "min_patches", "max_patches", "do_convert_rgb")
              if key == "internvl35" else
              ("max_slice_nums", "scale_resolution", "patch_size", "image_feature_size", "use_image_id", "slice_mode"))
    evidence["native_image_config"] = {name: getattr(processor.image_processor, name) for name in fields}
    evidence["implementation_sha256"] = {}
    for obj in (type(processor), type(processor.image_processor), type(tokenizer), model_class):
        evidence["implementation_sha256"][obj.__name__] = sha(inspect.getfile(obj))
    require(evidence["implementation_sha256"] == read(LOCK.with_name("implementation_lock.json"))[key],
            "PINNED_IMPLEMENTATION_HASH_MISMATCH")
    if key == "minicpm4":
        import sys
        prefix = model_class.__module__.rsplit(".", 1)[0]
        for name, module in list(sys.modules.items()):
            if name.startswith(prefix + ".") and getattr(module, "__file__", None):
                filename = Path(module.__file__).name
                require(filename in spec["files"] and sha(module.__file__) == spec["files"][filename],
                        "IMPORTED_REMOTE_SOURCE_MISMATCH:" + filename)
    return processor, tokenizer, config, model_class
