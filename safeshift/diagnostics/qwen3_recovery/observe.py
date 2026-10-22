"""Bounded scalar-only observations. No synchronization, tensor cache or locals."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
import traceback

from safeshift.pa3.native.journal import Journal
from .cohort import NEW_RUN, NEW_ATTEMPT

MAX_EVENTS = 128
MAX_BYTES = 2**20  # primary JSON; sidecars/tar headers budgeted separately


def safe_message(value):
    """Ordinary CUDA OOM messages survive verbatim; redact credentials/paths."""
    value = str(value)
    value = re.sub(r"(?i)(bearer\s+|(?:token|password|secret|api_key)\s*[=:]\s*)\S+", r"\1[REDACTED]", value)
    value = re.sub(r"\b(?:hf_|sk-)[A-Za-z0-9_-]+", "[REDACTED]", value)
    value = re.sub(r"https?://\S+|[A-Za-z]:[\\/][^\s'\"]+|(?<!\w)/(?:[^\s/]+/)+[^\s'\"]*", "[PATH_REDACTED]", value)
    return value[:4096]


def exception_record(error, stage):
    chain, seen, current = [], set(), error
    while current is not None and id(current) not in seen and len(chain) < 4:
        seen.add(id(current))
        message = safe_message(current)
        stack = []
        frames = traceback.extract_tb(current.__traceback__)
        for frame in frames[-16:]:
            path = Path(frame.filename).as_posix()
            # Never include absolute paths, source lines, locals, or image IDs.
            match = re.search(r"(?:^|/)((?:safeshift|transformers|torch|accelerate)/.+)$", path)
            stack.append({"module_path": match[1] if match else "external_module",
                          "function": frame.name, "line": frame.lineno})
        chain.append({"type": type(current).__name__, "module": type(current).__module__,
                      "message": message, "message_redacted_or_bounded": message != str(current),
                      "stack_bounded": len(frames) > 16, "stack": stack})
        current = current.__cause__ if current.__cause__ is not None else (
            None if current.__suppress_context__ else current.__context__)
    return {"stage": stage, "chain": chain, "cause_chain_bounded": current is not None, "retry": False}


def scalar_memory(torch):
    cuda, devices = torch.cuda, {}
    try:
        count = cuda.device_count()
    except BaseException as error:
        return {"devices": None, "observer_error_type": type(error).__name__}
    for i in range(count):
        row = {}
        getters = {"allocated_bytes": lambda: cuda.memory_allocated(i),
                   "reserved_bytes": lambda: cuda.memory_reserved(i),
                   "lifetime_peak_allocated_bytes": lambda: cuda.max_memory_allocated(i),
                   "lifetime_peak_reserved_bytes": lambda: cuda.max_memory_reserved(i)}
        for key, getter in getters.items():
            try:
                row[key] = int(getter())
            except BaseException as error:
                row[key] = None
                row.setdefault("unavailable", {})[key] = type(error).__name__
        try:
            free, total = cuda.mem_get_info(i)
            row.update(free_bytes=int(free), total_bytes=int(total))
        except BaseException as error:
            row.update(free_bytes=None, total_bytes=None)
            row.setdefault("unavailable", {})["mem_get_info"] = type(error).__name__
        keys = ("active_bytes.all.current", "inactive_split_bytes.all.current",
                "allocated_bytes.all.current", "reserved_bytes.all.current", "num_alloc_retries", "num_ooms")
        try:
            stats = cuda.memory_stats(i)
            row["allocator_stats"] = {k: int(stats[k]) if k in stats else None for k in keys}
        except BaseException as error:
            row["allocator_stats"] = None
            row.setdefault("unavailable", {})["allocator_stats"] = type(error).__name__
        devices[str(i)] = row
    try:
        allocator = cuda.get_allocator_backend()
    except BaseException as error:
        allocator = {"unavailable_type": type(error).__name__}
    return {"devices": devices, "allocator_backend": allocator,
            "allocator_config": os.environ.get("PYTORCH_CUDA_ALLOC_CONF"),
            "pytorch_alloc_conf": os.environ.get("PYTORCH_ALLOC_CONF"),
            "peak_scope": "LIFETIME_SINCE_PRE_LOAD_RESET", "synchronized": False}


class Observer:
    def __init__(self, root, torch):
        self.root, self.torch = Path(root), torch
        self.run = Journal(self.root / "lifecycle", create=True)
        self.journal, self.ordinal, self.stage, self.count, self.written = self.run, None, "worker_start", 0, 0
        self.run_count, self.run_written, self.failed, self.forward, self.active = 0, 0, False, 0, []

    def event(self, stage, **details):
        self.stage = stage
        value = {"run_id": NEW_RUN, "attempt_id": NEW_ATTEMPT, "recovery_ordinal": self.ordinal,
                 "original_ordinal": None if self.ordinal is None else 717 + self.ordinal,
                 "stage": stage, "utc": datetime.now(timezone.utc).isoformat(),
                 "monotonic_ns": time.monotonic_ns(), "active_native_stages": list(self.active),
                 "memory": scalar_memory(self.torch), **details}
        size = len(json.dumps(value, allow_nan=False).encode())
        if self.count >= MAX_EVENTS or self.written + size > MAX_BYTES - 65536:
            raise OSError("OBSERVATION_BUDGET_STOP_NO_TRUNCATION")
        self.journal.write(f"event-{self.count:03d}", value)
        self.count += 1
        self.written += size

    def start_sample(self, ordinal):
        if self.journal is not self.run:
            raise RuntimeError("PREVIOUS_OBSERVATIONS_NOT_SEALED")
        self.run_count, self.run_written = self.count, self.written
        self.journal = Journal(self.root / f"sample-{ordinal:06d}", create=True)
        self.ordinal, self.count, self.written, self.forward, self.failed = ordinal, 0, 0, 0, False
        self.event("sample_boundary_before_prepare")

    def finish_sample(self):
        if self.journal is self.run:
            return
        self.journal.seal()
        self.journal, self.ordinal = self.run, None
        self.count, self.written, self.failed, self.active = self.run_count, self.run_written, False, []

    def failure(self, error):
        if self.failed:
            return
        self.failed = True
        # Reserved terminal record; observing failure never replaces the exception.
        try:
            self.journal.write("failure", {"run_id": NEW_RUN, "attempt_id": NEW_ATTEMPT,
                "recovery_ordinal": self.ordinal, "original_ordinal": None if self.ordinal is None else 717 + self.ordinal,
                "utc": datetime.now(timezone.utc).isoformat(), "monotonic_ns": time.monotonic_ns(),
                "active_native_stages": list(self.active), "error": exception_record(error, self.stage),
                "memory": scalar_memory(self.torch)})
        except BaseException:
            pass  # torn bytes remain exportable; original exception propagates

    def close(self):
        self.finish_sample()
        self.event("worker_final")
        self.run.seal()

    def hooks(self, model):
        """Only metadata/scalars, return None. No output edits or tensor ownership."""
        handles = []
        def install(module, name):
            def before(native, args, kwargs):
                if name == "forward":
                    stage = "prefill" if self.forward == 0 else f"decode-{self.forward:02d}"
                    self.forward += 1
                else:
                    stage = name
                self.active.append(stage)
                specs = {k: {"shape": list(v.shape), "dtype": str(v.dtype), "device": str(v.device)}
                         for k, v in kwargs.items() if hasattr(v, "shape") and k in
                         ("input_ids", "inputs_embeds", "pixel_values", "image_grid_thw", "cache_position")}
                self.event(stage + "_before", tensors=specs)
            def after(native, args, kwargs, output):
                stage = self.active[-1]
                self.event(stage + "_after")
                self.active.pop()
            handles.append(module.register_forward_pre_hook(before, with_kwargs=True))
            # Default always_call=False leaves active stage intact when forward raises.
            handles.append(module.register_forward_hook(after, with_kwargs=True))
        try:
            install(model, "forward")
            install(model.model.visual, "vision")
        except BaseException:
            for handle in handles:
                handle.remove()
            raise
        return handles
