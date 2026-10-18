"""Fresh pinned child per stage. Guards precede every library load/GPU API."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys

from ..one_click.artifacts import write
from ..internvl3_recovery.monitor import Monitor, failure
from ..internvl3_recovery.network import deny_inet, network_denied
from .contract import AUTHORITY, STAGES, authorize
from . import probes


def check_environment(repo):
    from safeshift.protocol.classification_policy import load_policy
    import zlib
    expected = load_policy(repo, qwen3_runtime=True)["classification"]["internvl3"]["software_versions"]
    actual = {k: platform.python_version() if k == "python" else zlib.ZLIB_RUNTIME_VERSION if k == "zlib"
              else importlib.metadata.version(k) for k in expected}
    if actual != expected or platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("EXACT_PINNED_INTERNVL3_ENVIRONMENT_REQUIRED")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("UNCHANGED_CUDA_VISIBILITY_REQUIRED")
    from safeshift.runners.internvl3_snapshot import require_offline_env
    require_offline_env()
    if "torch" in sys.modules:
        raise RuntimeError("DIAGNOSTIC_MUST_NOT_IMPORT_TORCH")
    return {"expected": expected, "actual": actual}


def execute(stage, repo, evidence, source_path):
    evidence.mkdir(parents=True, exist_ok=False)
    row = {"stage": stage, "result": "BLOCKED", "fatal": True, "load_calls": 0,
           "generate_calls": 0, "CUDA_ROOT_CAUSE_CONFIRMED": False}
    monitor = None
    try:
        from .bootstrap import verify_topology
        source = json.loads(source_path.read_bytes())
        proof = verify_topology(repo, source["github_pr"], source["payload_sha256"])
        authorize(json.loads((repo / AUTHORITY).read_bytes()), proof)
        if stage not in STAGES or "torch" in sys.modules:
            raise PermissionError("DIAGNOSTIC_STAGE_OR_PREIMPORT_FORBIDDEN")
        monitor = Monitor(evidence)
        boundary = deny_inet()
        write(evidence / "network.json", boundary)
        monitor.event("guard_installed", source="CUDA_DIAGNOSTIC", boundary=boundary["boundary"])
        with network_denied(monitor):
            monitor.checkpoint("guarded_start")
            row["environment"] = check_environment(repo)
            row["observation"] = probes.run_probe(stage, Path(sys.executable).resolve().parents[2])
            monitor.checkpoint("after_diagnostic")
            row.update(result="OBSERVED", fatal=False)
    except BaseException as error:
        # No raw dlerror, command line, environment, path or source traceback.
        row["error"] = probes.error_metadata(error)
    finally:
        if monitor is not None:
            try:
                monitor.checkpoint("final")
                row["network_observation"] = monitor.finish()
            except BaseException as error:
                row.update(result="BLOCKED", fatal=True, monitor_error=failure(error))
        write(evidence / "result.json", row)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.stage, Path.cwd(), args.evidence, args.source)
    return 2 if result["fatal"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
