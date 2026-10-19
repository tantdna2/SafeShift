"""One load, ordered images, stop on first failure, keep all eight denominators."""
from pathlib import Path
import time

from safeshift.pa3.native.journal import Journal
from .capture import SampleCapture, replay
from .cohort import validate_opaque
from .resources import timed


def execute(root, rows, backend_factory, *, resources=lambda: None, observe=lambda: None,
            max_seconds=3600, clock=time.monotonic):
    validate_opaque(rows)
    root = Path(root)
    index = Journal(root / "index", create=True)
    index.write("manifest", {"samples": rows, "expected_count": 8})
    account = [{**r, "status": "NOT_ATTEMPTED", "seconds": None} for r in rows]
    start, backend, current = clock(), None, None
    try:
        resources()
        backend = timed(root / "model-load-timing.json", lambda: backend_factory(index), clock)
        for row in rows:
            i, cap = row["ordinal"], None
            current, began = i, clock()
            # Mark admission failures as measured attempts too, without inventing a native call.
            account[i].update(status="TECHNICAL_ERROR", native_call_started=False)
            try:
                if clock() - start >= max_seconds:
                    raise TimeoutError("WORKER_TIME_RESERVE_REACHED")
                resources()
                index.write(f"sample-{i:06d}.attempt", row)
                cap = SampleCapture(root / f"sample-{i:06d}", row)
                backend.generate(row, cap)
                cap.journal.seal()
                result = replay(cap.journal, backend.tokenizer)
                index.write(f"sample-{i:06d}.result", result)
                account[i]["status"] = result["status"]
                if result["status"] != "SUCCESS":
                    raise RuntimeError("SAMPLE_FAILED_STOP_NO_RETRY")
            except BaseException as error:
                if account[i]["status"] == "SUCCESS":
                    account[i]["status"] = "TECHNICAL_ERROR"
                if isinstance(error, (KeyboardInterrupt, SystemExit, TimeoutError)):
                    account[i]["status"] = "INTERRUPTED"
                account[i]["error"] = type(error).__name__
                if cap and not cap.journal.exists("seal"):
                    try:
                        cap.failure(error)
                        cap.journal.seal()
                    except (OSError, ValueError):
                        pass
                raise
            finally:
                account[i]["seconds"] = clock() - began
                account[i]["native_call_started"] = i in getattr(backend, "calls", ())
                try:
                    if cap and cap.journal.exists("complexity"):
                        account[i]["complexity"] = cap.journal.read("complexity")
                    if cap and cap.journal.exists("native"):
                        account[i]["output_tokens"] = cap.journal.read("native")["raw_steps"]
                except (OSError, ValueError):
                    account[i]["capture_integrity"] = "PARTIAL"
                try:
                    account[i]["memory"] = observe()
                except Exception as error:
                    account[i]["memory_error"] = type(error).__name__
                index.write(f"sample-{i:06d}.timing", account[i])
        index.write("finish", {"count": 8})
    except BaseException as error:
        index.write("failure", {"ordinal": current, "type": type(error).__name__, "retry": False})
    finally:
        if backend:
            try:
                backend.close()
            except BaseException as error:
                index.write("finalization-error", {"type": type(error).__name__})
        index.write("accounting", account)
        index.seal()
    return index
