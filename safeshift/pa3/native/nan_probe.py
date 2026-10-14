"""Diagnostic-only localization of the first FP16 Inf/NaN in native Qwen2.5-VL.

Forward hooks observe and never modify tensors. The first module output holding
+/-Inf/NaN is classified and its operation recomputed in FP32 from the exact FP16
operands, which separates FP16 overflow from other causes. No PA3 label/score,
retry or recovery. ``cast_overflow_fp16`` is a Research Lead review CANDIDATE
(vLLM 78648758794e2268a3af04b1eeab2347d961d88a semantics); PA3 execution never
installs it. Any GPU run needs an APPROVED decision line in DECISIONS.md.
"""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from functools import partial
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

FP16_MAX = 65504.0
CHUNK = 1 << 24
RECOMPUTE_LIMIT = 1 << 28
# Residual adds are inline Python inside these blocks, so no hook sees them alone.
RESIDUAL_BLOCKS = {"Qwen2_5_VLVisionBlock": ("attn", "norm2", "mlp"),
                   "Qwen2_5_VLDecoderLayer": ("self_attn", "post_attention_layernorm", "mlp")}
PRIMARY_KWARGS = ("hidden_states", "inputs_embeds", "hidden_state", "x")
APPROVAL = re.compile(r"^(DEC-PA3-[A-Z0-9-]+) status: APPROVED_FOR_NAN_LOCALIZATION$", re.M)
PLAN = "configs/pre_freeze/qwen2_5_t4_runtime.v1.json"


def _floating(value, torch):
    if hasattr(value, "to_tuple"):
        value = value.to_tuple()
    if isinstance(value, (tuple, list)):
        value = value[0] if value else None
    return value if isinstance(value, torch.Tensor) and value.is_floating_point() else None


def stats(tensor, torch):
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


def require_approval(repo, decision):
    approved = set(APPROVAL.findall((Path(repo) / "DECISIONS.md").read_text(encoding="utf-8")))
    if decision not in approved:
        raise PermissionError("NAN_LOCALIZATION_REQUIRES_APPROVED_DECISION")


def parse_samples(values):
    rows = []
    for value in values:
        parts = value.split("|")
        if len(parts) != 3 or not parts[1].startswith("DATA_PATH/train/") or len(parts[2]) != 64:
            raise ValueError("EXPLICIT_TRAIN_SAMPLE_TRIPLET_REQUIRED")
        rows.append(dict(zip(("sample_id", "image_locator", "image_sha256"), parts)))
    return rows


def probe_sample(scorer, image, *, clamp):
    """Exact native prefill via generate (one new token); diagnostics, never a PA3 score."""
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
    scorer.validator()
    logits = output.logits[0].detach()
    return {"candidate_merger_clamp": clamp, "pixel_values": stats(inputs["pixel_values"], torch),
            "input_shapes": {k: list(v.shape) for k, v in inputs.items()},
            "image_grid_thw": inputs["image_grid_thw"].tolist(),
            "step0_raw_logits": stats(logits, torch), "step0_argmax_id": int(logits[0].argmax()),
            **probe.report()}, logits.cpu()


def run(args):
    from safeshift.ls1.experiment import open_sample
    from safeshift.ls1.runtime import NativeScorer
    from . import preflight
    rows = parse_samples(args.sample)
    t1, tokenizer = preflight.tokenizer_check(args.repo, args.snapshot)
    if t1["status"] != "PASS":
        raise ValueError("T1_" + t1["status"])
    scorer = NativeScorer("qwen2_5", args.snapshot, tokenizer, t1["candidate_token_ids"], repo=args.repo)
    torch = scorer.torch
    report = {"schema": "pa3-qwen-nan-probe-v1", "decision": args.decision, "pa3_scores": None,
              "timestamp_utc": datetime.now(timezone.utc).isoformat(), "hardware": scorer.hardware,
              "software": scorer.software, "snapshot": scorer.snapshot_receipt, "samples": []}
    for row in rows:
        entry = {**row, "passes": []}
        report["samples"].append(entry)
        with open_sample(row, args.dataset_root) as image:
            baseline, logits = probe_sample(scorer, image, clamp=False)
            entry["passes"].append(baseline)
            if args.candidate_clamp:
                candidate, clamped = probe_sample(scorer, image, clamp=True)
                candidate["step0_bitwise_equal_to_baseline"] = bitwise_equal(logits, clamped, torch)
                entry["passes"].append(candidate)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=1, sort_keys=True, allow_nan=False)
    return report


def launch(args):
    """Kaggle parent: reuse audited runtime/model restore, then one offline child."""
    from safeshift.ls1.kaggle import attached_path, verify_runtime_input, runtime_interpreter, restore_model
    from safeshift.runners.internvl3_snapshot import OFFLINE_ENV
    runtime_input = attached_path(args.inputs, args.runtime_input)
    verify_runtime_input(runtime_input, attached_path(args.inputs, args.runtime_inventory_input),
                         args.runtime_inventory_sha256)
    restore_repo = Path(tempfile.mkdtemp(prefix="pa3-nan-probe-runtime-"))
    (restore_repo / PLAN).parent.mkdir(parents=True)
    shutil.copyfile(args.repo / PLAN, restore_repo / PLAN)
    snapshot = restore_model(restore_repo, attached_path(args.inputs, args.model_input), "qwen2_5")
    site = attached_path(args.inputs, args.runtime_site_packages) if args.runtime_site_packages else None
    if site and not site.resolve().is_relative_to(runtime_input.resolve()):
        raise ValueError("SITE_OUTSIDE_HASH_VERIFIED_RUNTIME")
    runtime = runtime_interpreter(restore_repo, runtime_input, "qwen2_5", site)
    env = {**os.environ, **OFFLINE_ENV, "CUDA_VISIBLE_DEVICES": "0", "PYTHONPATH": str(args.repo),
           "PYTHONNOUSERSITE": "1"}
    if runtime["site_packages"]:
        env["PYTHONPATH"] += os.pathsep + runtime["site_packages"]
    env.pop("PYTHONHOME", None)
    command = [runtime["python"], "-s", "-m", "safeshift.pa3.native.nan_probe", "--repo", str(args.repo),
               "--snapshot", str(snapshot), "--decision", args.decision, "--output", str(args.output),
               "--dataset-root", str(attached_path(args.inputs, args.dataset_input))]
    command += [x for s in args.sample for x in ("--sample", s)]
    command += ["--candidate-clamp"] if args.candidate_clamp else []
    return subprocess.run(command, cwd=args.repo, env=env, check=True).returncode  # one attempt, no retry


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--decision", required=True)
    parser.add_argument("--sample", action="append", required=True, metavar="ID|LOCATOR|SHA256")
    parser.add_argument("--candidate-clamp", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--launch", action="store_true", help="Kaggle parent mode")
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--dataset-root", type=Path, help="TRAIN root containing DATA_PATH/")
    for name in ("inputs", "runtime-input", "runtime-inventory-input", "runtime-inventory-sha256",
                 "runtime-site-packages", "model-input", "dataset-input"):
        parser.add_argument("--" + name)
    args = parser.parse_args(argv)
    require_approval(args.repo, args.decision)  # before runtime, model or image access
    parse_samples(args.sample)
    if args.output.exists():
        raise FileExistsError("NAN_PROBE_OUTPUT_EXISTS_NO_OVERWRITE")
    if args.launch:
        return launch(args)
    if not (args.snapshot and args.dataset_root):
        parser.error("--snapshot and --dataset-root are required in child mode")
    return run(args)


if __name__ == "__main__":
    main()
