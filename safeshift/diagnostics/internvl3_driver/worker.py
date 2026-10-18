"""Fresh pinned child per stage. Guards precede every library load/GPU API."""
import argparse
import json
from pathlib import Path
import sys

from ..one_click.artifacts import write
from ..internvl3_recovery.monitor import Monitor, failure
from ..internvl3_recovery.network import deny_inet, network_denied
from .contract import AUTHORITY, STAGES, authorize
from ..internvl3_cuda import probes
from ..internvl3_cuda.worker import check_environment
from .loader import preload


def execute(stage, repo, evidence, source_path):
    evidence.mkdir(parents=True, exist_ok=False)
    row = {"stage": stage, "result": "BLOCKED", "fatal": True, "load_calls": 0,
           "generate_calls": 0, "CUDA_ROOT_CAUSE_CONFIRMED": False, "CUDA_FIXED": False}
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
            if stage != "metadata":
                handles, records = preload(on_verified=lambda records: write(evidence / "driver-verified.json", records))
                row["driver_objects"] = records
                monitor.checkpoint("after_driver_preload")
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
