"""Future frozen eight-case Qwen3 gate execution; never grants automatic PASS."""

import argparse
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import platform
import re
import shlex
import subprocess
import sys
import socket
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import provision_qwen3vl_snapshot as snapshot
from scripts import w2_qwen_kaggle_smoke as smoke
from safeshift.protocol.firewall import external_path
from safeshift.protocol.gate import load_cases, evaluate_gate
from safeshift.protocol.prompts import probe_request
from safeshift.protocol.schema import parse_text, strict_json
from safeshift.runners.contracts import GenerationFailure, RunContext
from safeshift.runners.qwen3_vl import (
    BACKEND, ENVELOPE_VERSION, MODEL_ID, REVISION, Qwen3VLRunner,
)
from safeshift.runners.storage import FileRawStore

PLAN = "configs/pre_freeze/qwen3_external_gate.v1.json"
PLAN_SHA256 = "c7510570f553f3267e65f751b56193a337d3c370dd5c4db45da4d746711888c4"
MANIFEST = "configs/pre_freeze/external_gate_cases.v1.json"
PROVENANCE = "configs/pre_freeze/external_gate_cases.v1.provenance.json"
CASE_IDS = tuple(f"{group}_{n}" for group in "ABCD" for n in (1, 2))
ARTIFACTS = "data/processed/external_gate/w2_qwen3"


OFFLINE_ENV = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
               "HF_HUB_DISABLE_TELEMETRY": "1"}


def load_gate_plan(repo):
    raw = (repo / PLAN).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PLAN_SHA256:
        raise ValueError("GATE_PLAN_CHANGED")
    plan = strict_json(raw)
    runtime = smoke.load_plan(repo)
    smoke_raw = (repo / smoke.PLAN).read_bytes().replace(b"\r\n", b"\n")
    if (hashlib.sha256(smoke_raw).hexdigest() != plan["runtime_plan_sha256_lf"]
            or plan["decoding"] != runtime["decoding"]
            or plan["model_id"] != MODEL_ID or plan["model_revision"] != REVISION
            or plan["case_ids"] != list(CASE_IDS)
            or plan["resource_condition"] != {k: runtime[k] for k in plan["resource_condition"]}):
        raise ValueError("EXECUTION_PLAN_MISMATCH")
    for path, expected in plan["protected_source_sha256_lf"].items():
        raw = external_path(repo, path).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("PROTECTED_SOURCE_CHANGED")
    return plan, runtime


def verify_suite(repo, plan):
    """Only fixed frozen paths; validate all bytes before any backend/model load."""
    from PIL import Image

    for path, expected in ((MANIFEST, plan["manifest_sha256"]),
                           (PROVENANCE, plan["provenance_sha256"])):
        if snapshot.sha256_file(external_path(repo, path)) != expected:
            raise ValueError("FROZEN_SUITE_HASH_MISMATCH")
    provenance = strict_json((repo / PROVENANCE).read_bytes())
    if (provenance["suite_version"] != "synthetic-v1"
            or provenance["statement"] != "NO_INSPECSAFE_CONTENT_USED"
            or provenance["manifest_path"] != MANIFEST
            or provenance["manifest_sha256"] != plan["manifest_sha256"]):
        raise ValueError("FROZEN_PROVENANCE_MISMATCH")
    cases = load_cases(repo, MANIFEST)  # Includes reciprocal swap validation.
    if tuple(c.case_id for c in cases) != CASE_IDS:
        raise ValueError("EXACT_EIGHT_CASE_ORDER_REQUIRED")
    if [i["case_id"] for i in provenance["images"]] != list(CASE_IDS):
        raise ValueError("EXACT_EIGHT_IMAGE_RECORDS_REQUIRED")
    prepared = []
    for case, entry in zip(cases, provenance["images"]):
        expected_path = f"tests/fixtures/pre_freeze/frozen_external_gate/{case.case_id}.png"
        if (case.image_path != expected_path or entry["image_path"] != expected_path
                or case.swap_group != case.case_id[0]):
            raise ValueError("FROZEN_IMAGE_PATH_OR_GROUP_MISMATCH")
        raw = external_path(repo, case.image_path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError("FROZEN_IMAGE_HASH_MISMATCH")
        with Image.open(BytesIO(raw)) as image:
            image.load()
            if (image.format != "PNG" or image.size != (256, 256)
                    or getattr(image, "n_frames", 1) != 1
                    or (entry["width"], entry["height"]) != (256, 256)):
                raise ValueError("FROZEN_IMAGE_DIMENSIONS_MISMATCH")
        prompt = probe_request(repo, case.image_path, case.target_query)
        if (prompt.prompt_version != plan["prompt_version"]
                or prompt.prompt_sha256 != plan["prompt_sha256"][case.case_id]):
            raise ValueError("FROZEN_PROMPT_MISMATCH")
        prepared.append((case, raw, prompt, entry["sha256"]))
    return cases, prepared


@dataclass(frozen=True)
class ProbeInput:
    """Harness input for task-agnostic runner primitives, not a production adapter request."""
    input_bytes: bytes
    prompt: str
    task: str = "external_probe"


class GateRawStore(FileRawStore):
    def _directory(self, provenance):
        case = provenance["call_id"]
        if case not in CASE_IDS or provenance["sample_id"] != case:
            raise ValueError("UNEXPECTED_GATE_CASE")
        path = self.root / case
        self._check_path(path)
        return path


def parser_text(raw):
    """Extract only the native parser decode, after durable raw preservation."""
    obj = strict_json(raw.decode("utf-8"))
    for key, expected in (("schema_version", ENVELOPE_VERSION), ("backend", BACKEND),
                          ("model_id", MODEL_ID), ("model_revision", REVISION)):
        if obj.get(key) != expected:
            raise ValueError("RAW_ENVELOPE_IDENTITY_MISMATCH")
    text = obj["decoded_for_parser"]
    if type(text) is not str:
        raise ValueError("RAW_DECODE_MUST_BE_STRING")
    return text


def safe_failure(exc, stage, torch):
    # The runner suppresses native exceptions, so capture OOM at model.generate too.
    oom_type = getattr(getattr(torch, "cuda", None), "OutOfMemoryError", ())
    return {"stage": stage, "error_type": type(exc).__name__,
            "resource_failure": isinstance(exc, oom_type)}


def placement_observation(model):
    mapping, notes = smoke.inspect_device_map(model.hf_device_map)
    attention = getattr(model.config, "_attn_implementation", None)
    if attention == "flash_attention_2":
        raise ValueError("FLASH_ATTENTION_2_FORBIDDEN")
    return {"device_map": mapping, "notes": notes, "attention_observed": attention}


def verify_snapshot(path, repo, plan):
    """Reuse Qwen3 shard checks; also verify its already documented config hashes."""
    if Path(path).name != REVISION:
        raise ValueError("SNAPSHOT_REVISION_MISMATCH")
    result = snapshot.verify_weights(path, snapshot.weight_files(repo))
    result["config_files"] = [
        {"path": name, "expected_sha256": digest,
         "sha256": snapshot.sha256_file(Path(path) / name)}
        for name, digest in plan["snapshot_config_sha256"].items()
    ]
    result["config_bytes_verified"] = all(
        row["sha256"] == row["expected_sha256"] for row in result["config_files"])
    return result


def preserve_verified(store, raw, provenance):
    reference = asdict(store.preserve(raw, provenance))
    persisted = (store.repo / reference["path"]).read_bytes()
    if (persisted != raw or hashlib.sha256(persisted).hexdigest() != reference["sha256"]
            or len(persisted) != reference["size_bytes"]):
        raise ValueError("RAW_HASH_MISMATCH")
    return reference, persisted


def run_gate(run_id, expected_commit, *, repo=ROOT, cache_dir=None,
             runner_factory=Qwen3VLRunner, torch_module=None):
    """Test injection only; CLI supplies neither fake runner nor alternative cases."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
        raise ValueError("INVALID_RUN_ID")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise ValueError("EXACT_COMMIT_REQUIRED")
    store = GateRawStore(repo, ARTIFACTS + "/" + run_id)
    root = store.root
    root.mkdir(parents=True, exist_ok=False)
    summary = {"schema_version": "qwen3-external-gate-summary-v1", "run_id": run_id,
               "status": "GATE_EXECUTION_FAILURE", "calls": [], "native_generate_calls": 0,
               "initialize_calls": 0, "load_calls": 0,
               "native_errors": [], "not_attempted_case_ids": list(CASE_IDS),
               "inspecsafe_used": False, "protocol_freeze_commit_sha": "PENDING"}
    metadata = {"run_id": run_id, "expected_git_commit": expected_commit,
                "model_id": MODEL_ID, "model_revision": REVISION,
                "gate_plan_sha256": PLAN_SHA256,
                "started_at_utc": datetime.now(timezone.utc).isoformat()}
    environment, verified_snapshot = {}, {}
    stage, torch = "PREFLIGHT", None
    try:
        plan, runtime = load_gate_plan(repo)
        cases, inputs = verify_suite(repo, plan)
        metadata["frozen_inputs"] = [{"case_id": case.case_id, "image_path": case.image_path,
            "image_sha256": image_sha, "width": 256, "height": 256,
            "target_query": case.target_query, "prompt_sha256": prompt.prompt_sha256,
            "target_gt_bbox": case.target_gt_bbox, "distractor_gt_bbox": case.distractor_gt_bbox}
            for case, _, prompt, image_sha in inputs]
        metadata.update(gate_plan=plan, resource_condition=plan["resource_condition"],
                        runtime_plan_sha256_lf=plan["runtime_plan_sha256_lf"])
        metadata["git_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        if (metadata["git_commit"] != expected_commit or subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=all"], cwd=repo, text=True).strip()):
            raise ValueError("CLEAN_EXACT_EXECUTION_COMMIT_REQUIRED")
        environment["offline_variables"] = {k: os.environ.get(k) for k in OFFLINE_ENV}
        if environment["offline_variables"] != OFFLINE_ENV:
            raise ValueError("OFFLINE_ENV_REQUIRED")
        if cache_dir is not None and Path(os.environ.get("HF_HUB_CACHE", "")).resolve() != Path(cache_dir).resolve():
            raise ValueError("CUSTOM_CACHE_MUST_MATCH_HF_HUB_CACHE")
        with patch.object(socket.socket, "connect", smoke.block_network), \
                patch.object(socket.socket, "connect_ex", smoke.block_network), \
                patch.object(socket, "create_connection", smoke.block_network):
            stage = "ENVIRONMENT"
            if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
                raise ValueError("LINUX_X86_64_REQUIRED")
            if not os.environ.get("KAGGLE_KERNEL_RUN_TYPE"):
                raise ValueError("KAGGLE_ENVIRONMENT_REQUIRED")
            environment["platform"] = "KAGGLE"
            if torch_module is None:
                import torch as torch_module
            torch = torch_module
            environment["software"] = smoke.software_versions(torch)
            if environment["software"] != plan["software"]:
                raise ValueError("EXACT_SOFTWARE_AND_CUDA_REQUIRED")
            environment["hardware"] = smoke.probe_hardware(torch)
            smoke.require_t4_pair(environment["hardware"])
            stage = "SNAPSHOT"
            verified_snapshot = verify_snapshot(
                snapshot.cached_snapshot(cache_dir, offline=True), repo, plan)
            if not (verified_snapshot["LOCAL_WEIGHT_BYTES_VERIFIED"]
                    and verified_snapshot["config_bytes_verified"]):
                raise ValueError("LOCAL_WEIGHT_HASH_MISMATCH")
            stage = "INITIALIZE"
            runner = runner_factory()
            command = "python scripts/w2_qwen3_external_gate.py --run-id " + run_id + " --expected-commit " + expected_commit
            if cache_dir is not None:
                command += " --cache-dir " + shlex.quote(Path(cache_dir).resolve().relative_to(repo.resolve()).as_posix())
            context = RunContext(run_id, CASE_IDS[0], plan["decoding"], runtime["preprocessing"],
                                 runtime["precision"], runtime["quantization"], runtime["device"], environment["software"],
                                 expected_commit, command, "synthetic")
            metadata["command"] = command
            summary["initialize_calls"] += 1
            runner.initialize(context)
            summary["memory_before_load"] = smoke.memory_snapshot(torch, stage)
            stage = "LOAD"
            summary["load_calls"] += 1
            runner.load(context)
            processor, model = runner._resources
            summary["memory_after_load"] = smoke.memory_snapshot(torch, stage)
            summary["placement"] = placement_observation(model)
            native_generate = model.generate
            active_case, dispatched = None, set()

            def counted_generate(*args, **kwargs):
                if len(dispatched) >= 8 or active_case != CASE_IDS[len(dispatched)] or active_case in dispatched:
                    raise ValueError("EXACTLY_ONE_NATIVE_GENERATE_PER_CASE")
                dispatched.add(active_case)
                summary["native_generate_calls"] += 1
                try:
                    return native_generate(*args, **kwargs)
                except Exception as exc:
                    summary["native_errors"].append({"case_id": active_case,
                        **safe_failure(exc, "NATIVE_GENERATE", torch)})
                    raise

            model.generate = counted_generate
            predictions = {}
            try:
                for case, image_bytes, prompt, image_sha in inputs:
                    active_case = case.case_id
                    row = {"case_id": active_case, "target_gt_bbox": case.target_gt_bbox,
                           "distractor_gt_bbox": case.distractor_gt_bbox, "swap_group": case.swap_group,
                           "image_path": case.image_path, "image_sha256": image_sha,
                           "prompt_version": prompt.prompt_version, "prompt_sha256": prompt.prompt_sha256,
                           "parse_status": "NOT_ATTEMPTED", "raw": None}
                    summary["calls"].append(row)
                    summary["not_attempted_case_ids"].remove(active_case)
                    ctx = replace(context, call_id=active_case, input_provenance={
                        "image_sha256": image_sha, "manifest_sha256": plan["manifest_sha256"]})
                    provenance = {**asdict(ctx), "sample_id": active_case, "model_id": MODEL_ID,
                                  "model_revision": REVISION, "task": "external_probe",
                                  "prompt_version": prompt.prompt_version, "prompt_sha256": prompt.prompt_sha256,
                                  "prompt": prompt.prompt, "gate_plan_sha256": PLAN_SHA256, "parse_status": "NOT_ATTEMPTED"}
                    for gpu in range(2):
                        torch.cuda.reset_peak_memory_stats(gpu)
                    stage = "PREPARE"
                    prepared = runner.prepare_input(ProbeInput(image_bytes, prompt.prompt), ctx)
                    stage = "GENERATE"
                    try:
                        raw = runner.generate_raw(prepared, ctx)
                    except GenerationFailure as exc:
                        if exc.partial_raw is not None:
                            stage = "RAW_PRESERVE"
                            row["raw"], _ = preserve_verified(store, exc.partial_raw, provenance)
                            stage = "GENERATE"
                        raise
                    stage = "RAW_PRESERVE"
                    row["raw"], persisted = preserve_verified(store, raw, provenance)
                    stage = "PARSE"
                    row["decoded_for_parser"] = parser_text(persisted)
                    parsed = parse_text(row["decoded_for_parser"], "external_probe")
                    predictions[active_case] = parsed
                    row.update(parse_status=parsed.status, parsed_bbox=parsed.value.bbox if parsed.success else None)
                    row["memory"] = smoke.memory_snapshot(torch, stage)
                    if (runner._resources[1] is not model or model.model.rope_deltas is not None
                            or getattr(model, "_cache", None) is not None):
                        raise ValueError("INDEPENDENT_CALL_STATE_REQUIRED")
                    placement_observation(model)
                    snapshot.write_json(root / active_case / "result.json", row)
            finally:
                model.generate = native_generate
            if (dispatched != set(CASE_IDS) or summary["native_generate_calls"] != 8
                    or summary["initialize_calls"] != 1 or summary["load_calls"] != 1
                    or summary["native_errors"]):
                raise ValueError("EIGHT_NATIVE_CALLS_REQUIRED")
            stage = "EVALUATE"
            gate = evaluate_gate(repo, cases, predictions, reviews=None)
            # No review import/automatic NO_GIANT. A separate human audit is required.
            summary["status"] = {"FAIL": "GATE_FAIL", "PENDING_REVIEW": "GATE_PENDING_REVIEW"}[gate.status]
            summary["gate"] = asdict(gate)
    except Exception as exc:
        summary["failure"] = safe_failure(exc, stage, torch)
        summary["failure"]["resource_failure"] |= any(
            row["resource_failure"] for row in summary["native_errors"])
        if summary["calls"] and stage in {"PREPARE", "GENERATE", "RAW_PRESERVE", "PARSE"}:
            summary["calls"][-1]["failure"] = summary["failure"]
    finally:
        metadata["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        snapshot.write_json(root / "run_metadata.json", metadata)
        snapshot.write_json(root / "environment.json", environment)
        snapshot.write_json(root / "snapshot_manifest.json", verified_snapshot)
        summary["artifacts"] = {p.relative_to(root).as_posix(): {"sha256": snapshot.sha256_file(p),
                                   "size_bytes": p.stat().st_size}
                                for p in sorted(root.rglob("*")) if p.is_file()}
        snapshot.write_json(root / "summary.json", summary)
        with (root / "summary.json.sha256").open("x", encoding="ascii") as stream:
            stream.write(snapshot.sha256_file(root / "summary.json") + "  summary.json\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--cache-dir", help="Repository-relative existing cache under data/processed")
    args = parser.parse_args()
    cache = FileRawStore(ROOT, args.cache_dir).root if args.cache_dir else None
    result = run_gate(args.run_id, args.expected_commit, cache_dir=cache)
    print(json.dumps({"run_id": args.run_id, "status": result["status"]}))
    return 0 if result["status"] == "GATE_PENDING_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
