"""Recovery-only fresh guarded process; rejects every non-PR123 worker request."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import shutil
import sys

from safeshift.pa3.native.journal import no_alias
from ..one_click.artifacts import write, sha256
from .contract import AUTHORITY, authorize, unit
from .cohort import worker_rows
from .observe import Observer, exception_record


def verify_inputs(inputs):
    """Before importing torch/CUDA: all 224 opaque filenames and full hashes."""
    inputs = no_alias(inputs)
    rows = worker_rows(json.loads(no_alias(inputs / "request.json").read_bytes()))
    if {p.name for p in inputs.iterdir()} != {"request.json"} | {f"{i:06d}.image" for i in range(224)}:
        raise ValueError("EXACT_224_STAGED_FILES_REQUIRED")
    for row in rows:
        path = no_alias(inputs / f"{row['ordinal']:06d}.image")
        if not path.is_file() or sha256(path) != row["image_sha256"]:
            raise ValueError("STAGED_IMAGE_CHECKSUM_MISMATCH")
    return rows


def execute(mode, repo, evidence, source, cache, inputs, raw):
    evidence.mkdir(parents=True, exist_ok=False)
    result = {"status": "FAILED", "mode": mode, "unit": unit(), "inference_complete": False,
              "baseline_pooling_allowed": False, "retry": False, "resume": False}
    observer, guards = None, ExitStack()
    try:
        from .bootstrap import verify_topology
        proof = verify_topology(repo, source["github_pr"], source["payload_sha256"], worker=True)
        if proof != source:
            raise PermissionError("WORKER_SOURCE_PROOF_MISMATCH")
        authorize(json.loads((repo / AUTHORITY).read_bytes()), proof)
        rows = verify_inputs(inputs)
        if "torch" in sys.modules:
            raise RuntimeError("PRE_GUARD_TORCH_IMPORT_FORBIDDEN")
        from ..one_click.network import deny_inet
        from safeshift.runners.internvl3_snapshot import network_denied
        write(evidence / "boundary.json", deny_inet())
        guards.enter_context(network_denied())
        from ..one_click.worker import environment, memory, verify_snapshot
        runtime = environment("qwen3", repo, evidence=evidence)
        write(evidence / "runtime.json", runtime)
        import torch
        if mode == "inference":
            from .backend import Backend
            from .engine import execute as execute_images
            from ..hnlo_hf import installed_qwen_sources
            write(evidence / "generation-sources.json", installed_qwen_sources())
            checkpoint = verify_snapshot("qwen3", repo, cache)
            for i in range(torch.cuda.device_count()):
                torch.cuda.reset_peak_memory_stats(i)
            observer = Observer(raw.parent / "observations", torch)
            observer.event("before_backend_construction")
            def resources():
                from .budget import RUN_RESERVE
                if sum(p.stat().st_size for p in raw.parent.glob("*.log")) > RUN_RESERVE:
                    raise OSError("RUN_LOG_RESERVE_EXCEEDED_NO_TRUNCATION")
                # Evidence + diagnostics + conservative uncompressed archive reserve.
                if shutil.disk_usage(raw.parent).free < 224 * 6 * 2**20 + 512 * 2**20:
                    raise OSError("OUTPUT_ARCHIVE_RESERVE_INSUFFICIENT")
            index = execute_images(raw, rows, 224,
                lambda journal: Backend(repo, cache, inputs, journal, source, runtime, checkpoint, observer),
                resources=resources, observer=observer)
            observer = None  # engine finalized and sealed it, including failure paths
            result["inference_complete"] = (index.exists("finish") and not index.exists("failure")
                                            and not index.exists("finalization-error"))
        result.update(status="RETURNED", memory=memory(torch))
    except BaseException as error:
        if observer:
            observer.failure(error)
        result["error"] = exception_record(error, "worker_outer")
    finally:
        if observer:
            try:
                observer.close()
            except BaseException as error:
                result["observation_finalization_error"] = {"type": type(error).__name__}
        write(evidence / "result.json", result)
        guards.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("inspect", "inference"), required=True)
    for name in ("evidence", "source", "inputs", "raw"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--cache", required=True)
    a = parser.parse_args()
    result = execute(a.mode, Path.cwd(), a.evidence, json.loads(a.source.read_bytes()), a.cache, a.inputs, a.raw)
    return 0 if result["status"] == "RETURNED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
