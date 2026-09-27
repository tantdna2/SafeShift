"""Frozen future single-T4 feasibility harness. Never run during PREP."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.runners.contracts import GenerationFailure, Request, RunContext, Task
from safeshift.runners.moondream2 import (
    DECODING, PREPROCESSING, PLAN_SHA256, Moondream2Runner, deserialize_native, load_plan,
)
from safeshift.runners.moondream_snapshot import (
    MODEL_ID, REVISION, TOKENIZER_REPO, TOKENIZER_REVISION, json_bytes,
)
from safeshift.runners.storage import FileRawStore


def fixture_bytes(repo=ROOT):
    plan = load_plan()
    content = (repo / plan["smoke_fixture_path"]).read_bytes()
    if hashlib.sha256(content).hexdigest() != plan["smoke_fixture_sha256"]:
        raise ValueError("FROZEN_SMOKE_FIXTURE_CHANGED")
    return content


def check_native(value, task):
    if type(value) is not dict:
        raise ValueError("NATIVE_DICTIONARY_REQUIRED")
    if task == Task.CLASSIFICATION:
        if type(value.get("answer")) is not str:
            raise ValueError("NATIVE_QUERY_ANSWER_REQUIRED")
    else:
        objects = value.get("objects")
        if type(objects) is not list:
            raise ValueError("NATIVE_DETECT_OBJECTS_REQUIRED")
        for box in objects:
            if type(box) is not dict or any(type(box.get(k)) not in (float, int)
                    for k in ("x_min", "y_min", "x_max", "y_max")):
                raise ValueError("NATIVE_DETECT_FIELDS_REQUIRED")
        # No bounds, origin assumption, clamping, box repair or accuracy score.


def run_smoke(runner, *, run_id, execution_commit, store, image_bytes,
              command="scripts/w2_moondream_t4_smoke.py"):
    """No retries. Caller must reserve the one-attempt ledger before entry."""
    plan = load_plan()
    report = {"schema_version": "moondream-smoke-result-v1", "run_id": run_id,
              "execution_commit": execution_commit, "plan_sha256": PLAN_SHA256,
              "model_id": MODEL_ID, "model_revision": REVISION,
              "tokenizer_repo": TOKENIZER_REPO, "tokenizer_revision": TOKENIZER_REVISION,
              "precision": "FP16", "quantization": "NONE", "offload_policy": "FORBIDDEN",
              "resize_backend": "PILLOW_ONLY", "bridge_version": plan["bridge_version"],
              "smoke_fixture_sha256": plan["smoke_fixture_sha256"], "batch_size": 1,
              "calls": [], "errors": [], "status": "FAIL", "runtime": runner.evidence,
              "peak_cuda_memory_allocated": None, "peak_cuda_memory_reserved": None}
    context = RunContext(run_id, "query", DECODING, PREPROCESSING, "FP16", "NONE",
                         {"placement": "cuda:0"}, plan["software"], execution_commit,
                         command, "HANDCRAFTED_SMOKE_ONLY")
    stage = "fixture"
    try:
        if hashlib.sha256(image_bytes).hexdigest() != plan["smoke_fixture_sha256"]:
            raise ValueError("FROZEN_SMOKE_FIXTURE_CHANGED")
        stage = "initialize"
        runner.initialize(context)
        runner.backend.torch.cuda.reset_peak_memory_stats(0)
        stage = "load"
        runner.load(context)
        for task, call_id, prompt_id, prompt in (
                (Task.CLASSIFICATION, "query", plan["smoke_query_prompt_id"], plan["smoke_query_prompt"]),
                (Task.GROUNDING, "detect", "moondream-runtime-smoke-detect-v1", plan["smoke_detect_object"])):
            context = RunContext(**{**vars(context), "call_id": call_id})
            request = Request(task, "moondream-smoke-v1", plan["smoke_fixture_path"], image_bytes,
                              prompt_id, prompt)
            provenance = {**asdict(context), **asdict(runner.identity),
                          "sample_id": request.sample_id, "input_id": request.input_id,
                          "input_sha256": plan["smoke_fixture_sha256"], "prompt": prompt,
                          "prompt_id": prompt_id, "task": task.value,
                          "plan_sha256": PLAN_SHA256, "parse_status": "NOT_ATTEMPTED",
                          "tokenizer_repo": TOKENIZER_REPO, "tokenizer_revision": TOKENIZER_REVISION,
                          "model_manifest_sha256": runner.evidence["model_manifest"]["manifest_sha256"],
                          "tokenizer_manifest_sha256": runner.evidence["tokenizer_manifest"]["manifest_sha256"]}
            stage = call_id + ".prepare_input"
            prepared = runner.prepare_input(request, context)
            stage = call_id + ".generate_raw"
            try:
                raw = runner.generate_raw(prepared, context)
            except GenerationFailure as failure:
                if failure.partial_raw is not None:
                    reference = store.preserve(failure.partial_raw, provenance)
                    report["calls"].append({"call_id": call_id, "partial": True, "raw": asdict(reference)})
                raise
            stage = call_id + ".preserve"
            reference = store.preserve(raw, provenance)
            report["calls"].append({"call_id": call_id, "partial": False, "raw": asdict(reference)})
            stage = call_id + ".native_interface_check"
            check_native(deserialize_native(raw), task)
        stage = "final_invariants"
        evidence = runner.evidence
        if (not runner.valid or not runner.binding.valid
                or evidence["model_load_count"] != 1 or evidence["query_call_count"] != 1
                or evidence["detect_call_count"] != 1 or len(report["calls"]) != 2
                or len(evidence["state_audits"]) != 5
                or any(a["status"] != "VALID" for a in evidence["state_audits"])
                or [r["boundary"] for r in evidence["image_boundaries"]] != [
                    "bridge_cpu", "transfer", "vision_consumption"] * 2):
            raise ValueError("SMOKE_INVARIANTS_FAILED")
        report["status"] = "RUNTIME_INTERFACE_PASS"
    except Exception as error:
        report["errors"].append({"stage": stage, "type": type(error).__name__,
                                 "cause_type": type(error.__cause__).__name__ if error.__cause__ else None})
    finally:
        if runner.backend is not None and runner.condition is not None:
            try:
                cuda = runner.backend.torch.cuda
                report["peak_cuda_memory_allocated"] = cuda.max_memory_allocated(0)
                report["peak_cuda_memory_reserved"] = cuda.max_memory_reserved(0)
            except Exception as error:
                report["status"] = "FAIL"
                report["errors"].append({"stage": "memory_observation", "type": type(error).__name__})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-frozen-smoke", action="store_true", required=True)
    parser.add_argument("--venue-network-disabled", action="store_true", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    # Obtain execution provenance before installing irreversible offline boundary.
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if commit != args.expected_commit or subprocess.call(["git", "diff", "--quiet", "HEAD"], cwd=ROOT):
        parser.error("approved exact execution commit and clean tracked checkout required")
    content = fixture_bytes()
    artifact = FileRawStore(ROOT, "data/processed/moondream_t4_smoke").root
    artifact.mkdir(parents=True, exist_ok=True)
    # Fixed ledger across RUN_IDs: failed/interrupted attempt cannot be retried.
    with (artifact / "ATTEMPT.json").open("x", encoding="utf-8") as stream:
        json.dump({"run_id": args.run_id, "execution_commit": commit,
                   "timestamp_utc": datetime.now(timezone.utc).isoformat()}, stream)
    cache = FileRawStore(ROOT, args.cache_dir).root
    runner = Moondream2Runner(
        cache / "models--vikhyatk--moondream2" / "snapshots" / REVISION,
        cache / "models--moondream--starmie-v1" / "snapshots" / TOKENIZER_REVISION,
    )
    report = run_smoke(runner, run_id=args.run_id, execution_commit=commit,
                       store=FileRawStore(ROOT, "data/processed/moondream_t4_smoke/raw"), image_bytes=content)
    with (artifact / "result.json").open("xb") as stream:
        stream.write(json_bytes(report) + b"\n")
    print(json.dumps({"status": report["status"], "run_id": args.run_id}))
    return 0 if report["status"] == "RUNTIME_INTERFACE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
