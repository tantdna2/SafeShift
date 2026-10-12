"""Independent CPU audit. No torch, model load, references or dataset loader."""

import argparse
import json
import re
from pathlib import Path

from safeshift.ls1.tokenizer import probe
from safeshift.protocol.classification_policy import load_policy, render_prompt
from . import preflight
from ..artifacts import json_bytes
from .journal import Journal
from .native_score import pending, score


def audit(root, repo, tokenizer):
    journal = Journal(root)
    sealed = journal.verify()
    header = journal.read("manifest")
    current = preflight.source(repo, header["source"]["source_commit"])
    if json_bytes(current) != json_bytes(header["source"]):
        raise ValueError("SOURCE_PROVENANCE_MISMATCH")
    if header["schema"] != "pa3-qwen-run-v1" or header["prompt"] != render_prompt("qwen2_5", repo=repo):
        raise ValueError("METHOD_OR_PROMPT_MISMATCH")
    plan = preflight.plan("qwen2_5", repo)
    if (header["model"], header["revision"]) != (plan["model_id"], plan["model_revision"]):
        raise ValueError("MODEL_REVISION_MISMATCH")
    samples = header["samples"]
    ids = [r["sample_id"] for r in samples]
    if len(ids) != len(set(ids)):
        raise ValueError("DUPLICATE_COHORT_ID")
    evidence = journal.read("t1")
    observed = probe(tokenizer)
    if evidence["status"] != "PASS" or any(evidence[k] != v for k, v in observed.items()):
        raise ValueError("T1_EVIDENCE_MISMATCH")
    model = journal.read("model")
    runtime = journal.read("runtime")
    if (model["software"] != preflight.plan("qwen2_5", repo)["software"]
            or model["snapshot"] != runtime["snapshot"] or model["software"] != runtime["software"]
            or model["precision"] != "FP16" or model["attention"] != "sdpa"
            or model["quantization"] != "NONE" or model["prompt"] != header["prompt"]):
        raise ValueError("RUNTIME_MODEL_PROVENANCE_MISMATCH")
    hardware = model["hardware"]
    if (not re.fullmatch(r"(?:NVIDIA |Tesla )?T4", hardware["gpu_name"])
            or hardware["compute_capability"] != [7, 5] or hardware["visible_gpu_count"] != 1
            or hardware["cuda_runtime"] != "12.4" or hardware["device"] != "cuda:0"
            or not 14*2**30 <= hardware["total_vram_bytes"] <= 16*2**30):
        raise ValueError("T4_RUNTIME_EVIDENCE_MISMATCH")
    expected_generation = {**load_policy(repo)["classification"]["qwen2_5"]["decoding"],
                           "max_new_tokens": 32, "do_sample": False, "num_beams": 1,
                           "num_return_sequences": 1, "return_dict_in_generate": True,
                           "output_logits": True, "output_scores": True}
    results, stopped = [], False
    allowed = {"manifest", "source", "runtime", "t1", "model", "finish", "failure", "qualification", "seal"}
    for i, sample in enumerate(samples):
        prefix = f"sample-{i:06d}"
        allowed.update(prefix + "." + k for k in ("attempt", "native", "raw", "result", "error"))
        allowed.update(prefix + f".step-{s:02d}" for s in range(32))
        attempted = journal.exists(prefix + ".attempt")
        persisted = journal.exists(prefix + ".raw")
        calculated = journal.exists(prefix + ".result")
        if not attempted and any(journal.exists(prefix + "." + kind) for kind in ("native", "error")):
            raise ValueError("ORPHAN_NATIVE_RECORD")
        if not journal.exists(prefix + ".native") and any(journal.exists(prefix + f".step-{s:02d}") for s in range(32)):
            raise ValueError("ORPHAN_NATIVE_STEP")
        if (persisted and not attempted) or (calculated and not persisted) or (attempted and stopped):
            raise ValueError("ATTEMPT_SEQUENCE_MISMATCH")
        if attempted and journal.read(prefix + ".attempt") != sample:
            raise ValueError("ATTEMPT_IDENTITY_MISMATCH")
        row = pending(sample["sample_id"], attempted=attempted, persisted=persisted)
        if persisted:
            raw, native = journal.read(prefix + ".raw"), journal.read(prefix + ".native")
            grid = native["image_grid_thw"]
            if (len(grid) != 1 or len(grid[0]) != 3 or grid[0][0] != 1
                    or not 256 <= grid[0][1]*grid[0][2]//4 <= 1280
                    or native["input_shapes"]["input_ids"] != [1, len(raw["input_ids"])]) :
                raise ValueError("NATIVE_INPUT_SHAPE_MISMATCH")
            if (native["sequences"] != [raw["input_ids"] + raw["continuation_ids"]]
                    or native["input_ids"] != raw["input_ids"]
                    or raw["generation_kwargs"] != expected_generation
                    or native["generation_kwargs"] != expected_generation
                    or native["generation_config"] != raw["generation_config"]
                    or raw["generation_config"] != model["generation_config"]
                    or raw["candidate_token_ids"] != evidence["candidate_token_ids"]
                    or not 1 <= len(raw["steps"]) <= 32
                    or native["raw_steps"] != len(raw["steps"])
                    or native["processed_steps"] != len(raw["steps"])):
                raise ValueError("NATIVE_RAW_CONTRACT_MISMATCH")
            for s, step in enumerate(raw["steps"]):
                if json_bytes(journal.read(prefix + f".step-{s:02d}")) != json_bytes(step):
                    raise ValueError("RAW_STEP_MISMATCH")
            if any(journal.exists(prefix + f".step-{s:02d}") for s in range(len(raw["steps"]), 32)):
                raise ValueError("EXTRA_NATIVE_STEP")
            if calculated:
                row = score(sample["sample_id"], raw, tokenizer)
                if json_bytes(row) != json_bytes(journal.read(prefix + ".result")):
                    raise ValueError("CPU_RECOMPUTATION_MISMATCH")
        if journal.exists(prefix + ".error"):
            error = journal.read(prefix + ".error")
            if calculated or error["status"] not in {"TECHNICAL_ERROR", "INTERRUPTED"}:
                raise ValueError("ERROR_SEQUENCE_MISMATCH")
            row.update(status=error["status"], errors=[error["exception_type"]])
        stopped = not calculated or row["status"] == "TECHNICAL_ERROR"
        results.append(row)
    if set(journal.inventory()) - allowed:
        raise ValueError("UNKNOWN_RUN_RECORD")
    finish, failure = journal.exists("finish"), journal.exists("failure")
    if finish and (failure or stopped or journal.read("finish") != {"planned": len(samples), "status": "FINISHED"}):
        raise ValueError("FINISH_STATE_MISMATCH")
    if sealed and not (finish or failure):
        raise ValueError("TERMINAL_RECORD_MISSING")
    if failure and journal.read("failure").get("retry_permitted") is not False:
        raise ValueError("FAILURE_RETRY_POLICY_MISMATCH")
    return {"integrity": "PASS", "sealed": sealed, "completed": sealed and finish,
            "results": results, "scope": "CPU_RECOMPUTATION_NOT_EXECUTION_AUTHORITY",
            "limitations": "Local hashes cannot prove external authenticity or recover a deleted unsealed tail."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--report", type=Path, help="Optional sealed report journal; independently recompute its evaluation")
    args = parser.parse_args()
    evidence, tokenizer = preflight.tokenizer_check(args.repo, args.snapshot)
    if evidence["status"] != "PASS":
        print(json.dumps(evidence))
        return 2
    result = audit(args.run, args.repo, tokenizer)
    if args.report:
        reporting = Journal(args.report)
        if not reporting.verify():
            raise ValueError("SEALED_REPORT_REQUIRED")
        from .analysis import report
        recomputed = report(result["results"], reporting.read("metadata"), completed=result["completed"])
        if json_bytes(recomputed) != json_bytes(reporting.read("evaluation")):
            raise ValueError("EVALUATION_RECOMPUTATION_MISMATCH")
        result["evaluation_integrity"] = "PASS"
    print(json.dumps(result, allow_nan=False, indent=2))
    return 0 if result["completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
