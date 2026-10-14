"""Diagnostic-only localization of the first FP16 Inf/NaN in native Qwen2.5-VL.

Forward hooks observe and never modify tensors. The first module output holding
+/-Inf/NaN is classified and, where its operands are available, recomputed in FP32
from the exact FP16 operands. Hooks see module boundaries only: functional ops
inside a module (SDPA, RoPE, masked_scatter) and anything outside hooked modules
cannot be pinpointed and are reported ``UNRESOLVED``, never guessed. No PA3
label/score. ``cast_overflow_fp16`` is a Research Lead review CANDIDATE (vLLM
78648758794e2268a3af04b1eeab2347d961d88a semantics); PA3 execution never installs
it. Authority, durable journal and CLI: ``nan_probe_run``.
"""

import base64
from copy import deepcopy
from functools import partial
import hashlib

FP16_MAX = 65504.0
CHUNK = 1 << 24
# FP32 Linear recompute output cap: 2**26 elements = 256 MiB (ESTIMATED T4 headroom, unmeasured).
RECOMPUTE_LIMIT = 1 << 26
# Residual adds are inline Python inside these blocks, so no hook sees them alone.
RESIDUAL_BLOCKS = {"Qwen2_5_VLVisionBlock": ("attn", "norm2", "mlp"),
                   "Qwen2_5_VLDecoderLayer": ("self_attn", "post_attention_layernorm", "mlp")}
LOCALIZED_KINDS = ("MLP_RESIDUAL_ADD", "ATTENTION_RESIDUAL_ADD", "LINEAR")
PRIMARY_KWARGS = ("hidden_states", "inputs_embeds", "hidden_state", "x")


def _floating(value, torch):
    if hasattr(value, "to_tuple"):
        value = value.to_tuple()
    if isinstance(value, (tuple, list)):
        value = value[0] if value else None
    return value if isinstance(value, torch.Tensor) and value.is_floating_point() else None


def stats(tensor, torch):
    """Each int()/float() is a host sync on CUDA, so errors surface at this module."""
    if tensor is None:
        return None
    counts, absmax = [0, 0, 0], 0.0
    for chunk in tensor.detach().reshape(-1).split(CHUNK):  # bounded temporary memory
        if not chunk.numel():
            continue
        finite = torch.isfinite(chunk)
        counts[0] += int(torch.isnan(chunk).sum())
        counts[1] += int(torch.isposinf(chunk).sum())
        counts[2] += int(torch.isneginf(chunk).sum())
        absmax = max(absmax, float(torch.where(finite, chunk.abs(), torch.zeros_like(chunk)).amax()))
    return {"shape": list(tensor.shape), "dtype": str(tensor.dtype).replace("torch.", ""),
            "nan": counts[0], "positive_inf": counts[1], "negative_inf": counts[2], "finite_absmax": absmax}


def nonfinite(summary):
    return bool(summary) and any(summary[k] for k in ("nan", "positive_inf", "negative_inf"))


def _overflow(total):
    total = total.abs()
    return {"fp32_absmax": float(total.amax()), "exceeds_fp16_max": bool((total > FP16_MAX).any()),
            "elements_over_fp16_max": int((total > FP16_MAX).sum())}


def localization(origin, logits_summary):
    """FP16_OVERFLOW_LOCALIZED only with an FP32-recomputed overflow at a named op."""
    if origin is None:
        return "NO_NONFINITE" if not nonfinite(logits_summary) else "UNRESOLVED"
    recompute = origin.get("recompute")
    if origin.get("kind") in LOCALIZED_KINDS and recompute and recompute["exceeds_fp16_max"]:
        return "FP16_OVERFLOW_LOCALIZED"
    return "UNRESOLVED"


class NonfiniteProbe:
    """Context manager; one record per module completion in execution order."""

    def __init__(self, model, torch):
        self.model, self.torch = model, torch
        self.events, self.origin, self.handles = [], None, []
        self._block_input, self._children = {}, {}
        self._kinds = {name: type(m).__name__ for name, m in model.named_modules()}

    def __enter__(self):
        for name, module in self.model.named_modules():
            if not name:
                continue
            if type(module).__name__ in RESIDUAL_BLOCKS:
                self.handles.append(module.register_forward_pre_hook(
                    partial(self._pre, name), with_kwargs=True))
            self.handles.append(module.register_forward_hook(partial(self._post, name), with_kwargs=True))
        return self

    def __exit__(self, *exc):
        for handle in self.handles:
            handle.remove()
        self.handles, self._block_input, self._children = [], {}, {}
        return False

    def _primary(self, args, kwargs):
        if args and _floating(args[0], self.torch) is not None:
            return _floating(args[0], self.torch)
        return next((_floating(kwargs[k], self.torch) for k in PRIMARY_KWARGS
                     if _floating(kwargs.get(k), self.torch) is not None), None)

    def _pre(self, name, module, args, kwargs):
        self._block_input[name] = self._primary(args, kwargs)

    def _post(self, name, module, args, kwargs, output):
        torch = self.torch
        x, y = self._primary(args, kwargs), _floating(output, torch)
        event = {"order": len(self.events), "module": name, "class": type(module).__name__,
                 "input": stats(x, torch), "output": stats(y, torch)}
        self.events.append(event)
        parent, _, child = name.rpartition(".")
        if child in RESIDUAL_BLOCKS.get(self._kinds.get(parent), ()):
            self._children[name] = y
        if self.origin is None and nonfinite(event["output"]):
            self.origin = self._classify(name, module, event, x)
        if type(module).__name__ in RESIDUAL_BLOCKS:
            self._block_input.pop(name, None)
            for key in RESIDUAL_BLOCKS[type(module).__name__]:
                self._children.pop(f"{name}.{key}", None)

    def _residual(self, block, add):
        attn, _, mlp = RESIDUAL_BLOCKS[self._kinds[block]]
        x, a = self._block_input.get(block), self._children.get(f"{block}.{attn}")
        if x is None or a is None:
            return None
        if add == "attention":
            return _overflow(x.float() + a.float())
        m = self._children.get(f"{block}.{mlp}")
        # The model rounds the first residual to its own dtype before the second add.
        return None if m is None else _overflow((x + a).float() + m.float())

    def _classify(self, name, module, event, x):
        origin = {"event": event["order"], "module": name, "class": event["class"]}
        parent, _, child = name.rpartition(".")
        kind = self._kinds.get(parent)
        if nonfinite(event["input"]):
            if kind in RESIDUAL_BLOCKS and child == RESIDUAL_BLOCKS[kind][1]:
                return {**origin, "kind": "ATTENTION_RESIDUAL_ADD", "block": parent,
                        "recompute": self._residual(parent, "attention")}
            return {**origin, "kind": "UNHOOKED_OPERATION_BEFORE_INPUT"}
        if type(module).__name__ in RESIDUAL_BLOCKS:
            return {**origin, "kind": "MLP_RESIDUAL_ADD", "block": name,
                    "recompute": self._residual(name, "mlp")}
        if isinstance(module, self.torch.nn.Linear) and x is not None:
            if x.numel() // x.shape[-1] * module.out_features > RECOMPUTE_LIMIT:
                return {**origin, "kind": "LINEAR", "recompute": None}
            bias = None if module.bias is None else module.bias.float()
            return {**origin, "kind": "LINEAR", "recompute": _overflow(
                self.torch.nn.functional.linear(x.float(), module.weight.float(), bias))}
        has_children = any(True for _ in module.children())
        return {**origin, "kind": "INSIDE_MODULE" if has_children else "LEAF_MODULE"}

    def report(self, top=20):
        ranked = sorted((e for e in self.events if e["output"]),
                        key=lambda e: -e["output"]["finite_absmax"])[:top]
        return {"origin": self.origin, "events": self.events,
                "largest_finite_outputs": [{"module": e["module"], "finite_absmax": e["output"]["finite_absmax"],
                                            "fraction_of_fp16_max": e["output"]["finite_absmax"] / FP16_MAX}
                                           for e in ranked]}


def cast_overflow_fp16(tensor, torch, offset=1000.0):
    """CANDIDATE only: clamp FP16 +/-Inf; NaN stays NaN; finite tensors are returned unchanged."""
    if tensor.dtype != torch.float16 or bool(torch.isfinite(tensor).all()):
        return tensor
    bound = torch.finfo(torch.float16).max - offset
    return tensor.clamp(-bound, bound)


def install_merger_clamp(model, torch):
    """CANDIDATE only: clamp the final ViT residual stream before the patch merger."""
    def hook(module, args):
        return (cast_overflow_fp16(args[0], torch), *args[1:])
    return model.visual.merger.register_forward_pre_hook(hook)


def bitwise_equal(a, b, torch):
    views = {torch.float32: torch.int32, torch.float16: torch.int16, torch.float64: torch.int64}
    return (a.shape == b.shape and a.dtype == b.dtype and a.dtype in views
            and bool(torch.equal(a.view(views[a.dtype]), b.view(views[b.dtype]))))


def encode_raw(tensor):
    """Exact raw bytes (little-endian, as stored) of a CPU tensor for durable JSON."""
    data = tensor.detach().cpu().contiguous().numpy().tobytes()
    return {"dtype": str(tensor.dtype).replace("torch.", ""), "shape": list(tensor.shape),
            "sha256": hashlib.sha256(data).hexdigest(), "base64": base64.b64encode(data).decode()}


def probe_sample(scorer, image, *, clamp):
    """Exact native prefill via generate (one new token); diagnostics, never a PA3 score."""
    from safeshift.ls1.runtime import summarize_tensor
    torch, model = scorer.torch, scorer.model
    scorer.validator()
    model.rope_deltas = None
    inputs = scorer.prepare(image, ())
    kwargs = {**scorer.condition["decoding"], "max_new_tokens": 1, "do_sample": False, "num_beams": 1,
              "num_return_sequences": 1, "return_dict_in_generate": True, "output_logits": True}
    handle = install_merger_clamp(model, torch) if clamp else None
    try:
        with NonfiniteProbe(model, torch) as probe, torch.inference_mode():
            output = model.generate(**inputs, generation_config=deepcopy(scorer.config), **kwargs)
    finally:
        if handle is not None:
            handle.remove()
    logits = output.logits[0].detach()
    scorer.validator()
    summary = stats(logits, torch)
    argmax = int(logits[0].argmax())
    report = probe.report()
    return {"candidate_merger_clamp": clamp, "pixel_values": stats(inputs["pixel_values"], torch),
            "input_shapes": {k: list(v.shape) for k, v in inputs.items()},
            "image_grid_thw": inputs["image_grid_thw"].tolist(), "step0_raw_logits": summary,
            "step0_argmax_id": argmax,
            # Same reduction as archived Shard 0 step records, for reproduction fidelity checks.
            "step0_archive_comparable": summarize_tensor(logits, scorer.candidate_ids, argmax, torch),
            "localization": localization(report["origin"], summary), **report}, encode_raw(logits)
