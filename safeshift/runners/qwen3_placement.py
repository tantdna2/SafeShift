"""Exact prospective P2 Qwen3 placement; no torch import or fallback."""

from copy import deepcopy
import json
import os
import sys

RUNTIME_ID = "qwen3-t4x2-embedding-cpu-v1"
EMBEDDING = "model.language_model.embed_tokens"
ALLOCATOR_NAME = "PYTORCH_ALLOC_CONF"
ALLOCATOR_VALUE = "expandable_segments:True"
DEVICE_MAP = {
    "model.visual": 1,
    EMBEDDING: "cpu",
    **{f"model.language_model.layers.{i}": 0 for i in range(21)},
    **{f"model.language_model.layers.{i}": 1 for i in range(21, 36)},
    "model.language_model.norm": 1,
    "model.language_model.rotary_emb": 1,
    "lm_head": 1,
}


def device_contract():
    return {"placement": "explicit", "device_map": deepcopy(DEVICE_MAP)}


def require_device_map(mapping):
    # JSON comparison distinguishes bool from int and rejects extra/missing keys.
    if (type(mapping) is not dict
            or json.dumps(mapping, sort_keys=True, allow_nan=False)
            != json.dumps(DEVICE_MAP, sort_keys=True)):
        raise ValueError("EXACT_QWEN3_DEVICE_MAP_REQUIRED")


def require_allocator():
    if os.environ.get(ALLOCATOR_NAME) != ALLOCATOR_VALUE:
        raise ValueError("EXACT_QWEN3_ALLOCATOR_REQUIRED")
    # Do not let the legacy alias introduce an ambiguous allocator contract.
    if os.environ.get("PYTORCH_CUDA_ALLOC_CONF") not in (None, ALLOCATOR_VALUE):
        raise ValueError("CONFLICTING_QWEN3_ALLOCATOR_ALIAS")


def configure_allocator():
    """Owner CLI startup only. Never change allocator settings after torch import."""
    if ALLOCATOR_NAME not in os.environ:
        if "torch" in sys.modules:
            raise ValueError("SET_QWEN3_ALLOCATOR_BEFORE_TORCH_IMPORT")
        if os.environ.get("PYTORCH_CUDA_ALLOC_CONF") not in (None, ALLOCATOR_VALUE):
            raise ValueError("CONFLICTING_QWEN3_ALLOCATOR_ALIAS")
        os.environ[ALLOCATOR_NAME] = ALLOCATOR_VALUE
    require_allocator()


def require_context(context):
    if (context.device != device_contract()
            or type(context.device) is not dict):
        raise ValueError("EXACT_QWEN3_DEVICE_MAP_REQUIRED")
    require_device_map(context.device["device_map"])
    if context.precision != "FP16" or context.quantization != "NONE":
        raise ValueError("QWEN3_FP16_NONE_REQUIRED")
    require_allocator()


def require_loaded_state(native):
    require_allocator()
    require_device_map(getattr(native, "hf_device_map", None))
    if (str(native.dtype) != "torch.float16"
            or getattr(native, "is_quantized", False)
            or getattr(native.config, "quantization_config", None) is not None
            or getattr(native.config, "_attn_implementation", None) != "sdpa"):
        raise ValueError("QWEN3_NATIVE_FP16_NONE_SDPA_REQUIRED")
