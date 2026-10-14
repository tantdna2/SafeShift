"""Conservative post-NaN state evidence; no inference, reload or authority grant.

Fingerprint all parameters, buffers (including nonpersistent buffers), direct
tensor attributes, module scalar metadata and effective model/generation config.
Only the reviewed top-level RoPE/KV caches may be discarded. Matching state is
a bounded state check, not proof that a GPU kernel will produce finite outputs.
"""
import hashlib
import math
import re

from ..artifacts import json_bytes


VERSION = "pa3-state-guard-v1"


def _plain(value):
    if type(value) is float:
        return math.isfinite(value)
    if value is None or type(value) in (bool, int, str):
        return True
    if type(value) in (list, tuple):
        return all(_plain(v) for v in value)
    if type(value) is dict:
        return all(type(k) is str and _plain(v) for k, v in value.items())
    return False


def snapshot(scorer):
    """Bound CPU copies to one tensor chunk; never copy a checkpoint to disk."""
    torch, model = scorer.torch, scorer.model
    torch.cuda.synchronize()  # asynchronous CUDA failure must not authorize more work
    scorer.validator()
    tensors = [("parameter:" + k, v) for k, v in model.named_parameters()]
    if not tensors:
        raise ValueError("EMPTY_PARAMETER_STATE")
    tensors += [("buffer:" + k, v) for k, v in model.named_buffers()]
    modules = []
    for name, module in model.named_modules():
        if module.training:
            raise ValueError("MODEL_NOT_IN_EVAL")
        attributes = {}
        for key, value in vars(module).items():
            if name == "" and key in {"rope_deltas", "_cache"}:
                continue
            if key in {"_parameters", "_buffers", "_modules"}:
                continue  # inventoried recursively by the named_* APIs above
            if torch.is_tensor(value):
                tensors.append(("attribute:" + name + ":" + key, value))
            elif _plain(value):
                attributes[key] = value
            elif key == "config" and hasattr(value, "to_dict"):
                attributes[key] = value.to_dict()
                if not _plain(attributes[key]):
                    raise ValueError("UNREVIEWED_MODULE_CONFIG")
            elif key == "_non_persistent_buffers_set" and type(value) is set and all(type(v) is str for v in value):
                attributes[key] = sorted(value)
            else:
                # Do not silently ignore hooks, closures or opaque mutable state.
                # A pinned version/finite tensors alone cannot certify these.
                raise ValueError("UNREVIEWED_PERSISTENT_ATTRIBUTE:" + name + ":" + key)
        modules.append([name, type(module).__module__, type(module).__name__, attributes])
    digest = hashlib.sha256()
    for name, tensor in sorted(tensors, key=lambda pair: pair[0]):
        digest.update(json_bytes([name, list(tensor.shape), str(tensor.dtype), str(tensor.device)]))
        # Registered model tensors must be contiguous; no hidden full-size clone.
        if not tensor.is_contiguous():
            raise ValueError("UNREVIEWED_NONCONTIGUOUS_STATE")
        flat = tensor.detach().view(-1)
        for start in range(0, flat.numel(), 1048576):
            chunk = flat[start:start + 1048576].cpu()
            if not torch.isfinite(chunk).all().item():
                raise ValueError("NONFINITE_PERSISTENT_STATE:" + name)
            digest.update(chunk.view(torch.uint8).numpy().tobytes())
    metadata = {"modules": modules, "model_config": model.config.to_dict(),
        "generation_config": model.generation_config.to_dict(),
        "effective_generation_config": scorer.config.to_dict(), "condition": scorer.condition}
    if not _plain(metadata):
        raise ValueError("UNREVIEWED_STATE_METADATA")
    digest.update(json_bytes(metadata))
    torch.cuda.synchronize()
    return {"sha256": digest.hexdigest(), "tensor_count": len(tensors), "all_finite": True}


def permits(baseline, evidence, sample_id):
    """Shared strict evidence check for orchestration and independent journal audit."""
    state = baseline.get("state")
    return (set(baseline) == {"schema", "status", "state", "reason"}
        and baseline["schema"] == VERSION and baseline["status"] == "RECORDED"
        and baseline["reason"] is None and type(state) is dict
        and set(state) == {"sha256", "tensor_count", "all_finite"}
        and type(state["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", state["sha256"]) is not None
        and type(state["tensor_count"]) is int and state["tensor_count"] > 0 and state["all_finite"] is True
        and set(evidence) == {"schema", "sample_id", "status", "before", "after", "cache_cleared", "reason"}
        and evidence["schema"] == VERSION and evidence["sample_id"] == sample_id
        and evidence["status"] == "STATE_MATCH" and evidence["reason"] is None
        and evidence["before"] == state and evidence["after"] == state
        and evidence["cache_cleared"] is True)


class StateGuard:
    def __init__(self, scorer, journal):
        self.scorer, self.journal = scorer, journal
        failure = None
        try:
            state = snapshot(scorer)
            status, reason = "RECORDED", None
        except Exception as exc:
            state, status, reason = None, "UNAVAILABLE", type(exc).__name__ + ":" + str(exc)
            # Missing/unreviewed introspection disables recovery. Numerical,
            # runtime and validator faults must stop even the first model call.
            if not (isinstance(exc, AttributeError) or
                    isinstance(exc, ValueError) and str(exc).startswith("UNREVIEWED_")):
                failure = exc
        self.baseline = journal.write("state-baseline", {
            "schema": VERSION, "status": status, "state": state, "reason": reason})
        if failure is not None:
            scorer.failed = True
            raise ValueError("MODEL_STATE_BASELINE_FAILED") from failure

    def after_nonfinite(self, sample, prefix):
        scorer = self.scorer
        already_failed = scorer.failed
        scorer.failed = True
        evidence = {"schema": VERSION, "sample_id": sample["sample_id"], "status": "BLOCKED",
                    "before": self.baseline["state"], "after": None,
                    "cache_cleared": False, "reason": "STATE_NOT_PROVEN"}
        try:
            if already_failed or self.baseline["status"] != "RECORDED":
                raise ValueError("NO_HEALTHY_BASELINE_OR_TERMINAL_SCORER")
            if self.journal.read("state-baseline") != self.baseline:
                raise ValueError("STATE_BASELINE_CHANGED")
            scorer.torch.cuda.synchronize()
            # Same Qwen2.5 locations already cleared before each native call.
            scorer.validator()
            scorer.model.rope_deltas = None
            if hasattr(scorer.model, "_cache"):
                scorer.model._cache = None
            evidence["cache_cleared"] = (scorer.model.rope_deltas is None
                                         and getattr(scorer.model, "_cache", None) is None)
            evidence["after"] = snapshot(scorer)
            if not evidence["cache_cleared"] or evidence["after"] != self.baseline["state"]:
                raise ValueError("PERSISTENT_STATE_CHANGED")
            evidence.update(status="STATE_MATCH", reason=None)
        except Exception as exc:
            evidence["reason"] = type(exc).__name__ + ":" + str(exc)
        # Any inability to persist/reread proof is terminal, including interrupts.
        scorer.failed = True
        evidence = self.journal.write(prefix + ".state", evidence)
        allowed = permits(self.baseline, evidence, sample["sample_id"])
        if allowed:
            scorer.failed = False
        return allowed
