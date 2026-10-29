"""Bounded private diagnostics; no model/input values or credentials in receipts."""
from contextlib import contextmanager
from pathlib import Path
import time
import traceback

from .artifacts import write


def resources():
    # No torch/CUDA import or initialization. Measurements are local observations.
    try:
        import psutil
        process = psutil.Process()
        result = {"rss_bytes": process.memory_info().rss,
                  "host_available_bytes": psutil.virtual_memory().available}
        limit = Path("/sys/fs/cgroup/memory.max")
        current = Path("/sys/fs/cgroup/memory.current")
        if limit.is_file() and current.is_file():
            result.update(cgroup_limit=limit.read_text().strip(),
                          cgroup_current_bytes=int(current.read_text()))
        return result
    except (ImportError, OSError, ValueError):
        return {"status": "UNAVAILABLE"}


def failure_detail(error, stage, subcomponent):
    from .runner import error_record
    trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    # Apply the same path/token redaction to the full bounded traceback.
    clean = error_record(RuntimeError(trace), stage)["message"]
    return {**error_record(error, stage), "subcomponent": subcomponent,
            "traceback_tail": clean, "traceback_truncated": len(trace) > 2000,
            "attention": getattr(error, "phi_attention_receipt", getattr(error, "smol_attention_receipt", None))}


@contextmanager
def phase(evidence, stage, subcomponent):
    directory = Path(evidence) / "diagnostics" if evidence is not None else None
    ordinal = len(list(directory.glob("*.start.json"))) if directory else 0
    prefix = f"{ordinal:04d}-{subcomponent}"
    start = time.monotonic()
    if directory:
        write(directory / (prefix + ".start.json"),
              {"stage": stage, "subcomponent": subcomponent, "resources": resources()})
    try:
        yield
    except BaseException as error:
        error.stage = getattr(error, "stage", stage)
        error.subcomponent = getattr(error, "subcomponent", subcomponent)
        if directory:
            write(directory / (prefix + ".failure.json"),
                  {**failure_detail(error, error.stage, error.subcomponent),
                   "seconds": time.monotonic() - start, "resources": resources()})
        raise
    else:
        if directory:
            write(directory / (prefix + ".pass.json"),
                  {"stage": stage, "subcomponent": subcomponent, "status": "PASS",
                   "seconds": time.monotonic() - start, "resources": resources()})
