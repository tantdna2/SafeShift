"""Label-free per-unit lifecycle; injectable backend permits CPU-only tests."""
from pathlib import Path
import time

from safeshift.pa3.native.journal import Journal
from .capture import SampleCapture, replay
from .cohort import validate_opaque
from ..resource_pilot.resources import timed
from ..one_click.artifacts import write


def execute(root, rows, expected_count, backend_factory, *, resources=lambda: None,
            max_seconds=36000, clock=time.monotonic):
    """At most one load and one call/ordinal. Every early stop preserves the tail."""
    validate_opaque(rows, expected_count)
    root = Path(root)
    journal = Journal(root / "index", create=True)
    journal.write("manifest", {"samples": rows, "expected_count": expected_count})
    start, backend, stopped = clock(), None, False
    try:
        resources()
        backend = timed(root / "model-load-timing.json", lambda: backend_factory(journal))  # exactly one construction; no reload
        for row in rows:
            ordinal, cap = row["ordinal"], None
            name = f"sample-{ordinal:06d}"
            began = time.monotonic()
            try:
                if clock() - start >= max_seconds:
                    raise TimeoutError("WORKER_TIME_RESERVE_REACHED")
                resources()
                journal.write(name + ".attempt", row)
                cap = SampleCapture(root / name, row)
                backend.generate(row, cap)
                cap.journal.seal()  # before parser, alignment or scalar calculation
                result = replay(cap.journal, backend.tokenizer)
                journal.write(name + ".result", result)
                if result["status"] == "TECHNICAL_ERROR":
                    raise RuntimeError("TECHNICAL_SAMPLE_STOP_NO_RETRY")
                # INVALID is immutable; continue to the next original ordinal.
            except BaseException as error:
                if cap is not None and not cap.journal.exists("seal"):
                    try:
                        cap.failure(error)
                        cap.journal.seal()
                    except (OSError, ValueError):
                        pass  # torn bytes remain; never invent a successful seal
                journal.write("failure", {"ordinal": ordinal, "type": type(error).__name__,
                    "interrupted": isinstance(error, (KeyboardInterrupt, SystemExit, TimeoutError)), "retry": False})
                stopped = True
                break
            finally:
                write(root / "timings" / f"{ordinal:06d}.json", {"ordinal": ordinal, "seconds": time.monotonic() - began})
        if not stopped:
            journal.write("finish", {"count": expected_count})
    except BaseException as error:
        failure = {"ordinal": None, "type": type(error).__name__,
                   "interrupted": isinstance(error, (KeyboardInterrupt, SystemExit)), "retry": False}
        if journal.exists("failure"):
            write(root / "lifecycle-error.json", failure)
        else:
            journal.write("failure", failure)
    finally:
        if backend is not None:
            try:
                backend.close()
            except BaseException as error:
                journal.write("finalization-error", {"type": type(error).__name__})
        journal.seal()
    return journal
