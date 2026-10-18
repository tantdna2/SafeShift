"""Fresh recovery child; only InternVL3, independently rechecked authority/source."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import traceback
from ..one_click.artifacts import write
from ..one_click.worker import empty, environment, memory, probe, replay, verify_snapshot
from .contract import AUTHORITY, LOCK, authorize
from .monitor import Monitor, SecurityStop, ConnectionFailure, ConnectionCallFailure, failure


def monitoring_failed(state, error):
    state.update(result="FAILED", common_fatal=True, security_monitor_error=failure(error),
                 reason="NETWORK_MONITOR_STOP_OR_EVIDENCE_FAILURE", hnlo=None,
                 TECHNICAL_HNLO_VALID=False, technical_hnlo="N/A")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("inspect", "probe", "replay"), required=True)
    parser.add_argument("--model", choices=("internvl3",), required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--capture-root", type=Path, required=True)
    args = parser.parse_args()
    repo, state, started, torch = Path.cwd(), empty(args.model), time.monotonic(), None
    args.evidence.mkdir(parents=True, exist_ok=False)
    monitor = None
    try:
        from .bootstrap import verify_topology
        source = json.loads(args.source.read_bytes())
        verify_topology(repo, source["github_pr"], source["payload_sha256"])
        grant = authorize(json.loads((repo / AUTHORITY).read_bytes()), source)
        from safeshift.runners.internvl3_snapshot import require_offline_env
        from .network import network_denied
        require_offline_env()
        if "torch" in sys.modules:
            raise RuntimeError("TORCH_IMPORTED_BEFORE_NETWORK_AND_VISIBILITY_GUARDS")
        monitor = Monitor(args.evidence)
        from .network import deny_inet
        boundary = deny_inet()
        write(args.evidence / "network.json", boundary)
        monitor.event("guard_installed", source="WORKER", boundary=boundary.get("boundary", "UNSPECIFIED"))
        with network_denied(monitor):
            monitor.checkpoint("guarded_start")
            if args.mode == "replay":
                if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
                    raise RuntimeError("CPU_REPLAY_MUST_HIDE_ALL_GPUS")
                from transformers import AutoTokenizer
                # Replay only opens known local tokenizer files; never imports torch directly.
                snapshot, receipt = verify_snapshot(args.model, repo, args.cache)
                tokenizer = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True, trust_remote_code=False, use_fast=True)
                state.update(replay(args.capture_root, "hnlo-" + grant["attempt_id"] + "-" + args.model, tokenizer))
                state["result"] = "TECHNICAL_VALID" if state["TECHNICAL_HNLO_VALID"] else "N/A"
            else:
                state["runtime"] = environment(args.model, repo, evidence=args.evidence)
                monitor.checkpoint("after_cuda_admission")
                state["environment"] = "EXACT_MATCH"
                import torch
                for i in range(torch.cuda.device_count()):
                    torch.cuda.reset_peak_memory_stats(i)
                state["memory_before"] = memory(torch)
                if args.mode == "probe":
                    monitor.checkpoint("before_model_probe")
                    probe(args.model, repo, args.evidence, source, grant, args.cache, state, capture_root=args.capture_root, source_lock=LOCK)
                else:
                    state["result"] = "ENVIRONMENT_VALID"
            monitor.checkpoint("after_" + args.mode)
    except BaseException as error:
        # A caller's source line can itself contain literal secrets/payloads.
        # Monitor errors retain sanitized type/reason and journal evidence only.
        trace = (type(error).__name__ + ": " + str(error) + "\n"
                 if isinstance(error, (SecurityStop, ConnectionFailure, ConnectionCallFailure))
                 else traceback.format_exc())
        state.update(result="FAILED", error_type=type(error).__name__, reason=str(error),
                     failure_traceback=trace)
        with (args.evidence / "error.log").open("x", encoding="utf-8") as stream:
            stream.write(state["failure_traceback"])
            stream.flush()
            os.fsync(stream.fileno())
        # Unrecognized process failure is handled as shared/fatal by the parent.
        state["common_fatal"] = isinstance(error, (PermissionError, OSError)) or any(
            marker in str(error) for marker in ("SOURCE", "AUTHORITY", "CHECKSUM", "INVENTORY", "SECCOMP", "NETWORK", "AUDITED", "TORN", "SEALED"))
    finally:
        try:
            state["memory_after"] = memory(torch)
        except BaseException as error:
            state["memory_collection_error"] = type(error).__name__
        if monitor is not None:
            try:
                monitor.checkpoint("final")
            except BaseException as error:
                monitoring_failed(state, error)
            try:
                state["network_observation"] = monitor.finish()
            except BaseException as error:
                monitoring_failed(state, error)
        if (args.evidence / "cuda-admission.json").exists():
            state["cuda_admission"] = json.loads((args.evidence / "cuda-admission.json").read_bytes())
        state["elapsed_seconds"] = time.monotonic() - started
        write(args.evidence / "result.json", state)
    return 0 if state["result"] not in ("FAILED", "BLOCKED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
