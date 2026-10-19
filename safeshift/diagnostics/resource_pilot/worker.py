"""Fresh guarded process; no canonical IDs, label manifest or dataset locators."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import shutil
import sys

from ..one_click.artifacts import write
from .contract import AUTHORITY, authorize, unit


def execute(mode, repo, evidence, source, model, cache, inputs, raw):
    evidence.mkdir(parents=True, exist_ok=False)
    result, drivers, monitor, torch = {"status": "FAILED", "mode": mode, "full_vocab_replay": False,
        "command": {"module": "safeshift.diagnostics.resource_pilot.worker", "mode": mode,
                    "model": model, "cache": cache,
                    "input_artifact": "data/processed/resource_pilot_inputs/" + unit(model)["run_id"],
                    "raw_artifact": "evidence/raw"}}, None, None, None
    guards = ExitStack()
    try:
        from .bootstrap import verify_topology
        proof = verify_topology(repo, source["github_pr"], source["payload_sha256"], worker=True)
        if proof != source:
            raise PermissionError("WORKER_SOURCE_PROOF_MISMATCH")
        authorize(json.loads((repo / AUTHORITY).read_bytes()), proof, model)
        if "torch" in sys.modules:
            raise RuntimeError("PRE_GUARD_TORCH_IMPORT_FORBIDDEN")
        if model == "internvl3":
            from ..internvl3_recovery.network import deny_inet, network_denied
            from ..internvl3_recovery.monitor import Monitor
            from ..internvl3_cuda.worker import check_environment
            from ..internvl3_hnlo.driver import DriverSession
            boundary = deny_inet()
            monitor = Monitor(evidence)
            guards.enter_context(network_denied(monitor))
            check_environment(repo)
            drivers = DriverSession(evidence)  # unchanged PR #115, after guards
        else:
            from ..one_click.network import deny_inet
            from safeshift.runners.internvl3_snapshot import network_denied
            boundary = deny_inet()
            guards.enter_context(network_denied())
        write(evidence / "boundary.json", boundary)
        from ..one_click.worker import environment, memory, verify_snapshot
        runtime = environment(model, repo, evidence=evidence)
        write(evidence / "runtime.json", runtime)
        import torch
        if drivers:
            drivers.observe("after_cuda")
        if mode == "inference":
            from .backend import Backend
            from .engine import execute as execute_images
            from .cohort import validate_opaque
            from ..hnlo_hf import installed_qwen_sources
            from ..internvl3_hnlo.capture import verify_sources
            sources = installed_qwen_sources() if model == "qwen3" else verify_sources(repo)
            write(evidence / "generation-sources.json", sources)
            checkpoint = verify_snapshot(model, repo, cache)
            rows = json.loads((inputs / "request.json").read_bytes())
            validate_opaque(rows, unit(model)["count"])
            for i in range(torch.cuda.device_count()):
                torch.cuda.reset_peak_memory_stats(i)
            def resources():
                if shutil.disk_usage(raw.parent).free < 512 * 2**20:
                    raise OSError("OUTPUT_RESERVE_BELOW_512_MIB")
                if monitor:
                    monitor.checkpoint("sample_boundary")
            def load_backend(journal):
                backend = Backend(repo, model, cache, inputs, journal, source, runtime, checkpoint)
                if drivers:
                    drivers.observe("after_model_load")
                return backend
            index = execute_images(raw, rows, load_backend, resources=resources, observe=lambda: memory(torch))
            result["inference_complete"] = index.exists("finish") and not index.exists("finalization-error")
            if drivers:
                drivers.observe("after_inference")
        result.update(status="RETURNED", full_vocab_replay=False, memory=memory(torch))
    except BaseException as error:
        result["error"] = {"type": type(error).__name__, "errno": getattr(error, "errno", None)}
    finally:
        if torch is not None:
            try:
                result["memory"] = memory(torch)
            except Exception as error:
                result["memory_error"] = type(error).__name__
        try:
            if drivers:
                drivers.observe("final")
            if monitor:
                result["network_observation"] = monitor.finish()
        except BaseException as error:
            result.update(status="FAILED", finalization_error={"type": type(error).__name__})
        result["driver_handles_retained_through_finalization"] = drivers is not None
        write(evidence / "result.json", result)
        guards.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("inspect", "inference"), required=True)
    parser.add_argument("--model", choices=("qwen3", "internvl3"), required=True)
    for name in ("evidence", "source", "inputs", "raw"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--cache", required=True)
    a = parser.parse_args()
    result = execute(a.mode, Path.cwd(), a.evidence, json.loads(a.source.read_bytes()), a.model,
                     a.cache, a.inputs, a.raw)
    return 0 if result["status"] == "RETURNED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
