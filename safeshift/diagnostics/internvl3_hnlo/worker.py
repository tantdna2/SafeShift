"""Fresh guarded worker: authorize -> guards -> driver -> CUDA -> checkpoint."""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import re
import sys
import time

from ..one_click.artifacts import write
from ..one_click.worker import empty, environment, memory, verify_snapshot
from ..internvl3_cuda.worker import check_environment
from ..internvl3_recovery.monitor import Monitor, failure
from ..internvl3_recovery.network import deny_inet, network_denied
from .contract import AUTHORITY, authorize
from .driver import DriverSession
from .capture import probe, replay


def safe_failure(error):
    row = failure(error)
    category = str(error).split(":", 1)[0]
    if re.fullmatch(r"[A-Z][A-Z0-9_]{1,96}", category):
        row["reason"] = category
    return row


def execute(mode, repo, evidence, source_path, cache, capture_root):
    evidence.mkdir(parents=True, exist_ok=False)
    state, started, torch, drivers, monitor = empty("internvl3"), time.monotonic(), None, None, None
    guards = ExitStack()
    try:
        state["stage"] = "SOURCE_AUTHORITY"
        from .bootstrap import verify_topology
        source = json.loads(source_path.read_bytes())
        proof = verify_topology(repo, source["github_pr"], source["payload_sha256"])
        if proof != source:
            raise PermissionError("WORKER_SOURCE_PROOF_MISMATCH")
        grant = authorize(json.loads((repo / AUTHORITY).read_bytes()), proof)
        if mode not in ("inspect", "probe", "replay") or "torch" in sys.modules:
            raise PermissionError("MODE_OR_PRE_GUARD_TORCH_IMPORT_FORBIDDEN")
        state["stage"] = "GUARDS"
        boundary = deny_inet()
        write(evidence / "network.json", boundary)
        monitor = Monitor(evidence)
        guards.enter_context(network_denied(monitor))
        # Hold the Python guard through exception handling and final observations.
        monitor.event("guard_installed", source="INTERNVL3_HNLO", boundary=boundary["boundary"])
        monitor.checkpoint("guarded_start")
        if mode == "replay":
            state["stage"] = "CPU_REPLAY"
            from safeshift.runners.internvl3_snapshot import require_offline_env
            require_offline_env()
            if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
                raise RuntimeError("CPU_REPLAY_MUST_HIDE_ALL_GPUS")
            from transformers import AutoTokenizer
            snapshot, _ = verify_snapshot("internvl3", repo, cache)
            tokenizer = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True, trust_remote_code=False, use_fast=True)
            previous = json.loads((evidence.parent / "probe/result.json").read_bytes())
            state.update(replay(capture_root, "hnlo-" + grant["attempt_id"] + "-internvl3", tokenizer, previous))
            state["result"] = "TECHNICAL_VALID" if state["TECHNICAL_HNLO_VALID"] else "N/A"
        else:
            state["stage"] = "SANITIZED_ENVIRONMENT"
            state["sanitized_environment"] = check_environment(repo)
            state["stage"] = "DRIVER"
            drivers = DriverSession(evidence)
            monitor.checkpoint("after_driver_preload")
            # torch is imported for the first time here; PR #115 handles stay
            # strongly referenced through all CUDA, load/generate and finalization.
            state["stage"] = "CUDA"
            state["runtime"] = environment("internvl3", repo, evidence=evidence)
            state["environment"] = "EXACT_MATCH"
            import torch
            drivers.observe("after_cuda")
            monitor.checkpoint("after_cuda_admission")
            torch.cuda.reset_peak_memory_stats(0)
            state["memory_before"] = memory(torch)
            if mode == "probe":
                state["stage"] = "CHECKPOINT_AND_CAPTURE"
                probe(repo, evidence, source, grant, cache, state, capture_root, drivers)
            else:
                state["result"] = "ENVIRONMENT_VALID"
        monitor.checkpoint("after_" + mode)
    except BaseException as error:
        state.update(result="FAILED", common_fatal=True, error=safe_failure(error),
                     reason=safe_failure(error).get("reason", type(error).__name__),
                     hnlo=None, technical_hnlo="N/A", TECHNICAL_HNLO_VALID=False)
        # Do not persist arbitrary path/endpoint/secret-bearing exception strings.
        write(evidence / "error.json", safe_failure(error))
    finally:
        try:
            if drivers is not None:
                drivers.observe("final")
            if torch is not None:
                state["memory_after"] = memory(torch)
            if monitor is not None:
                monitor.checkpoint("final")
        except BaseException as error:
            state.update(result="FAILED", common_fatal=True, finalization_error=failure(error),
                         hnlo=None, technical_hnlo="N/A", TECHNICAL_HNLO_VALID=False)
        if monitor is not None:
            try:
                state["network_observation"] = monitor.finish()
            except BaseException as error:
                state.update(result="FAILED", common_fatal=True, monitor_error=failure(error),
                             hnlo=None, technical_hnlo="N/A", TECHNICAL_HNLO_VALID=False)
        state["elapsed_seconds"] = time.monotonic() - started
        state["driver_handles_retained_through_finalization"] = drivers is not None
        write(evidence / "result.json", state)
        guards.close()
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("inspect", "probe", "replay"), required=True)
    parser.add_argument("--model", choices=("internvl3",), required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--capture-root", type=Path, required=True)
    args = parser.parse_args()
    row = execute(args.mode, Path.cwd(), args.evidence, args.source, args.cache, args.capture_root)
    return 2 if row["result"] == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
