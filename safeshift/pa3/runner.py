"""One-shot synthetic runner. No model, tokenizer or sample injection interfaces."""

from datetime import datetime, timezone
from pathlib import Path
import sys

from . import artifacts
from .policy import authorize, identity
from .scoring import raw_record, score_raw
from .synthetic import specimen


def source_provenance():
    """Hash only implementation sources, never datasets, weights or old outputs."""
    root = Path(__file__).resolve().parents[2]
    paths = sorted((root / "safeshift" / "pa3").glob("*.py"))
    paths += [root / name for name in (
        "safeshift/ls1/core.py", "safeshift/ls1/evaluate.py",
        "safeshift/protocol/schema.py", "safeshift/protocol/p21_schema.py")]
    return {p.relative_to(root).as_posix(): artifacts.receipt(p.read_bytes()) for p in paths}


def manifest(settings):
    settings = authorize(settings)
    return {"identity": identity(settings),
            "cohort": [specimen(settings, n) for n in settings["cases"]],
            "source_files": source_provenance(),
            "source_commit_scope": "caller-declared provenance; never execution authority",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "environment": {"python": sys.version, "platform": sys.platform,
                            "dependencies": "Python standard library only"},
            "command": "python -m safeshift.pa3 run --mode synthetic --run-id <id> --source-commit <sha> --cases <catalog names>",
            "artifact_root": "data/processed/pa3_synthetic/" + settings["run_id"]}


def run(repo, settings):
    settings = authorize(settings)  # before source reads, mkdir or mock execution
    header = manifest(settings)
    root = artifacts.create(repo, settings)  # no overwrite/resume, even after failure
    active = None
    try:
        artifacts.write(repo, settings, "manifest", header)
        for i, name in enumerate(settings["cases"]):
            active = i
            artifacts.write(repo, settings, f"{i:03d}.attempt", specimen(settings, name))
            artifacts.write(repo, settings, f"{i:03d}.raw", raw_record(settings, name))
            saved = artifacts.read(repo, settings, f"{i:03d}.raw")
            result = score_raw(settings, name, saved)
            artifacts.write(repo, settings, f"{i:03d}.result", result)
            if result["status"] in ("TECHNICAL_ERROR", "INTERRUPTED"):
                artifacts.write(repo, settings, "failure", {
                    "status": "STOPPED", "at_index": i, "reason": result["status"], "retry_permitted": False})
                break
        else:
            artifacts.write(repo, settings, "finish", {"status": "FINISHED", "planned": len(settings["cases"])})
    except BaseException as exc:
        if not artifacts.exists(repo, settings, "failure"):
            artifacts.write(repo, settings, "failure", {"status": "STOPPED", "at_index": active,
                            "reason": type(exc).__name__, "retry_permitted": False})
        raise
    finally:
        # Hard kill / torn write may prevent sealing; audit refuses damaged files
        # and labels an intact but unsealed journal as partial, never completed.
        artifacts.seal(repo, settings)
    return root
