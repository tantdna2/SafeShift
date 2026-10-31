"""Explicit per-instance numerical implementation; original HF source is immutable.

Only four expressions in the hash-locked native attention method are replaced:
masked/unmasked scores, softmax, value product. Projections/normalization/query
scaling/output projection/weights stay native FP16. No global monkeypatch.
"""
from copy import deepcopy
import hashlib
import inspect
from pathlib import Path
import textwrap
from types import MethodType

from safeshift.pilot.artifacts import read, sha, write
from safeshift.pilot.contract import digest
from .source import LOCK, require

ID = "minicpm4-resampler-attention-fp32-v1"
DECISION = "docs/research/DECISIONS.md#dec-20261031-minicpm-resampler-fp32-technical-exception"
REPLACEMENTS = (
    ("torch.baddbmm(attn_mask, q_scaled, k.transpose(-2, -1))",
     "_safeshift_scores(self, q_scaled, k, attn_mask)"),
    ("torch.bmm(q_scaled, k.transpose(-2, -1))",
     "_safeshift_scores(self, q_scaled, k, None)"),
    ("softmax(attn_output_weights, dim=-1)",
     "_safeshift_probabilities(self, attn_output_weights)"),
    ("torch.bmm(attn_output_weights, v)",
     "_safeshift_values(self, attn_output_weights, v, q.dtype)"),
)


def descriptor():
    value = {"id": ID, "scope": "TECHNICAL_TRIAL_ONLY_NOT_SCIENTIFIC_BASELINE",
        "authority": DECISION, "original_resampler_sha256": read(LOCK)["minicpm4"]["files"]["resampler.py"],
        "implementation_file": "safeshift/candidates/minicpm_resampler_fp32.py",
        "implementation_file_sha256": sha(__file__), "expression_replacements": list(map(list, REPLACEMENTS)),
        "weights_dtype": "float16", "score_dtype": "float32", "softmax_dtype": "float32",
        "value_product_dtype": "float32", "return_boundary": "native q.dtype before out_proj",
        "attention": "eager", "history_policy": "NEW_ISOLATED_SMOKE_SERIES_NO_IMPORT_NO_POOLING"}
    return {**value, "implementation_sha256": digest(value)}


def configuration(base):
    value = deepcopy(base)
    value["schema"] = "safeshift-candidate160-effective-config-v1"
    effective = value["effective_candidate"]
    require(effective["model_key"] == "minicpm4", "MINICPM_ONLY_NUMERICAL_EXCEPTION")
    effective["adapter"] = "safeshift.candidates.minicpm_resampler_fp32.EffectiveBackend"
    effective["numerical_policy"] = descriptor()
    return value


def rewritten_method(native):
    path = Path(inspect.getsourcefile(native))
    require(sha(path) == descriptor()["original_resampler_sha256"], "RESAMPLER_ORIGINAL_SOURCE_HASH")
    original = textwrap.dedent(inspect.getsource(native))
    changed = original
    for before, after in REPLACEMENTS:
        require(changed.count(before) == 1, "RESAMPLER_EXACT_EXPRESSION_REQUIRED:" + before)
        changed = changed.replace(before, after)
    return original, changed


def _scores(attention, q, k, mask):
    import torch
    require(bool(torch.isfinite(q).all()) and bool(torch.isfinite(k).all()), "RESAMPLER_NONFINITE_QK")
    with torch.autocast(device_type=q.device.type, enabled=False):
        scores = (torch.bmm(q.float(), k.transpose(-2, -1).float()) if mask is None else
                  torch.baddbmm(mask.float(), q.float(), k.transpose(-2, -1).float()))
    # -Inf is the native additive mask, but +Inf/NaN are a numerical error.
    require(not bool((torch.isnan(scores) | torch.isposinf(scores)).any()), "RESAMPLER_NONFINITE_SCORES")
    attention._safeshift_numerics["scores_fp32_finite_or_negative_mask"] += 1
    return scores


def _probabilities(attention, scores):
    import torch
    with torch.autocast(device_type=scores.device.type, enabled=False):
        value = torch.softmax(scores, dim=-1, dtype=torch.float32)
    require(bool(torch.isfinite(value).all()), "RESAMPLER_NONFINITE_SOFTMAX")
    attention._safeshift_numerics["softmax_fp32_finite"] += 1
    return value


def _values(attention, probabilities, v, dtype):
    import torch
    require(bool(torch.isfinite(v).all()), "RESAMPLER_NONFINITE_VALUE_INPUT")
    with torch.autocast(device_type=v.device.type, enabled=False):
        product = torch.bmm(probabilities.float(), v.float())
    require(bool(torch.isfinite(product).all()), "RESAMPLER_NONFINITE_VALUE_PRODUCT")
    result = product.to(dtype=dtype)
    require(bool(torch.isfinite(result).all()), "RESAMPLER_NONFINITE_RETURN_CAST")
    attention._safeshift_numerics["value_product_fp32_finite_and_return_cast"] += 1
    attention._safeshift_numerics["returned_dtype"] = str(result.dtype)
    return result


def install_attention(attention):
    """Bind only this locked attention instance; useful for small native CPU tests."""
    require(not attention.training and "multi_head_attention_forward" not in attention.__dict__,
            "RESAMPLER_EVAL_UNMODIFIED_INSTANCE_REQUIRED")
    native = type(attention).multi_head_attention_forward
    original, changed = rewritten_method(native)
    namespace = dict(native.__globals__)
    namespace.update(_safeshift_scores=_scores, _safeshift_probabilities=_probabilities, _safeshift_values=_values)
    exec(compile(changed, "<safeshift:" + ID + ">", "exec"), namespace)
    derived = namespace[native.__name__]
    signature = inspect.signature(native)
    def effective(this, *args, **kwargs):
        bound = signature.bind(this, *args, **kwargs)
        bound.apply_defaults()
        require(bound.arguments["need_weights"] is True and bound.arguments["training"] is False
                and bound.arguments["dropout_p"] == 0.0, "RESAMPLER_EAGER_EVAL_ZERO_DROPOUT_REQUIRED")
        return derived(this, *args, **kwargs)
    attention._safeshift_numerics = {"scores_fp32_finite_or_negative_mask": 0, "softmax_fp32_finite": 0,
        "value_product_fp32_finite_and_return_cast": 0, "returned_dtype": None}
    attention.multi_head_attention_forward = MethodType(effective, attention)
    return {"descriptor": descriptor(), "native_method_sha256": hashlib.sha256(original.encode()).hexdigest(),
            "derived_method_sha256": hashlib.sha256(changed.encode()).hexdigest()}


def install(model):
    """Bind a declared derived method; never change a class, source file or parameter."""
    import torch
    from .loading import verify_attention
    identity = {name: (id(p), p.dtype, p.device, p.data_ptr()) for name, p in model.named_parameters()}
    require(all(p.dtype == torch.float16 for p in model.parameters()), "EFFECTIVE_WEIGHTS_MUST_REMAIN_FP16")
    receipt = install_attention(model.resampler.attn)
    require(identity == {name: (id(p), p.dtype, p.device, p.data_ptr()) for name, p in model.named_parameters()},
            "EFFECTIVE_INSTALL_CHANGED_PARAMETERS")
    return {**receipt,
            "parameter_count": sum(p.numel() for p in model.parameters()), "all_parameter_dtypes": ["float16"],
            "parameter_identity_preserved": True, "native_attention_verification": verify_attention(model, "minicpm4")}


def backend(key, snapshot, weights, prompt, *, device):
    # The unchanged backend owns loading/raw capture/tokenizer/generation.
    from .backend import CandidateBackend
    require(key == "minicpm4", "MINICPM_ONLY_NUMERICAL_EXCEPTION")
    class EffectiveBackend(CandidateBackend):
        def __init__(self):
            super().__init__(key, snapshot, weights, prompt, device=device)
            self.environment["effective_implementation"] = install(self.model)

        def generate(self, image_path, sample_dir):
            before = dict(self.model.resampler.attn._safeshift_numerics)
            try:
                return super().generate(image_path, sample_dir)
            finally:
                write(Path(sample_dir) / "effective_numerics.json", {
                    "implementation": descriptor(), "before": before,
                    "after": dict(self.model.resampler.attn._safeshift_numerics)})
    return EffectiveBackend()
