"""PA3-R2: PR #102's GPU-verified FP16 clamp immediately before visual merger."""

POLICY = "pa3-r2-pre-merger-fp16-clamp-v1"


class MergerClamp:
    def __init__(self, model, torch, record):
        self.model, self.torch, self.record = model, torch, record
        self.calls = 0

    def __enter__(self):
        self.handle = self.model.visual.merger.register_forward_pre_hook(self.hook)
        return self

    def __exit__(self, *exc):
        self.handle.remove()

    def hook(self, module, args):
        torch, x = self.torch, args[0]
        if x.dtype != torch.float16:
            raise ValueError("R2_MERGER_FP16_REQUIRED")
        finite = bool(torch.isfinite(x).all())
        counts = {"nan": 0, "positive_inf": 0, "negative_inf": 0}
        if not finite:
            counts = {"nan": int(torch.isnan(x).sum()),
                      "positive_inf": int(torch.isposinf(x).sum()),
                      "negative_inf": int(torch.isneginf(x).sum())}
        bound = torch.finfo(torch.float16).max - 1000.0
        # Exact candidate semantics: finite tensors retain object/bit identity;
        # a nonfinite tensor is clamped as a whole. NaNs remain NaNs.
        out = x if finite else x.clamp(-bound, bound)
        self.record(self.calls, {"policy": POLICY, "triggered": not finite,
            "overflow_count": counts["positive_inf"] + counts["negative_inf"],
            "input_nonfinite": counts, "shape": list(x.shape), "dtype": "float16",
            "finite_values_clipped": 0 if finite else int((torch.isfinite(x) & (x.abs() > bound)).sum()),
            "bound_before_fp16_rounding": bound})
        self.calls += 1
        return (out, *args[1:])
