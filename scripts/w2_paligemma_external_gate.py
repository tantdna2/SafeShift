"""D9R13 frozen external gate PREP. No production classification or promotion."""

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.runners.contracts import GenerationFailure, Request, RunContext, Task
from safeshift.runners.paligemma import (
    DECODING, PREPROCESSING, PaliGemmaRunner, VerifiedRawStore,
    probe_hardware, software_versions,
)
from safeshift.runners.paligemma_snapshot import (
    CACHE, MODEL_ID, REVISION, OFFLINE_ENV, load_plan, network_denied,
    require_offline_env, sha256_file, write_json,
)
from scripts.w2_paligemma_t4_smoke import checkout_gate, memory_observation
from safeshift.protocol.firewall import external_path
from safeshift.protocol.gate import load_cases, evaluate_gate, GiantBoxReview
from safeshift.protocol.schema import strict_json
from safeshift.runners.paligemma_external_probe import QUERY_LABELS, parse_probe
from scripts.w2_paligemma_interface_qualification import persist_verified

BASE_SHA = "a3192ddefbc28fe2997190819744e8f4796a6d85"
PLAN = "configs/pre_freeze/paligemma_external_gate.v1.json"
PLAN_SHA256 = "5f1db82fa8d46ccfdf1ded268fea6beac6bf323e453539b4ce63fa7004ec3cc9"
ARTIFACTS = "data/processed/external_gate/w2_paligemma"
RUN_ID = "paligemma-d9r13-external-gate-01"
CASE_IDS = tuple(f"{group}_{n}" for group in "ABCD" for n in (1, 2))
PROMPT_ID = "paligemma-frozen-external-detect-v1"
COMPLETE = "EVIDENCE_COLLECTION_COMPLETE"
STOP = "STOP_AND_RESEARCH_LEAD_REVIEW_REQUIRED"


def gate_plan(repo=ROOT):
    path = Path(repo) / PLAN
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PLAN_SHA256:
        raise ValueError("PREDECLARED_PLAN_BYTES_CHANGED")
    plan = strict_json(raw)
    if (plan["base_sha"], plan["model_id"], plan["revision"]) != (BASE_SHA, MODEL_ID, REVISION):
        raise ValueError("EXACT_BASE_MODEL_REVISION_REQUIRED")
    return plan


def verify_suite(plan, repo=ROOT):
    """Read the existing frozen bytes only; never import/run the generator."""
    from io import BytesIO
    from PIL import Image
    repo = Path(repo)
    for path, digest in ((plan["manifest"], plan["manifest_sha256"]),
                         (plan["provenance"], plan["provenance_sha256"]),
                         (plan["generator"], plan["generator_sha256"]),
                         (plan["negative_evidence"]["path"], plan["negative_evidence"]["sha256"])):
        if sha256_file(external_path(repo, path)) != digest:
            raise ValueError("FROZEN_AUTHORITY_HASH_MISMATCH")
    provenance = strict_json(external_path(repo, plan["provenance"]).read_bytes())
    if (provenance["suite_version"] != "synthetic-v1"
            or provenance["statement"] != "NO_INSPECSAFE_CONTENT_USED"
            or provenance["manifest_path"] != plan["manifest"]
            or provenance["manifest_sha256"] != plan["manifest_sha256"]):
        raise ValueError("FROZEN_PROVENANCE_MISMATCH")
    cases = load_cases(repo, plan["manifest"])
    if (tuple(c.case_id for c in cases) != CASE_IDS or plan["case_ids"] != list(CASE_IDS)
            or [i["case_id"] for i in provenance["images"]] != list(CASE_IDS)):
        raise ValueError("EXACT_EIGHT_FROZEN_CASES_REQUIRED")
    inputs = []
    for case, entry in zip(cases, provenance["images"]):
        expected = plan["image_root"] + "/" + case.case_id + ".png"
        if case.image_path != expected or entry["image_path"] != expected:
            raise ValueError("FROZEN_IMAGE_PATH_MISMATCH")
        if case.target_query not in QUERY_LABELS:
            raise ValueError("FROZEN_TARGET_QUERY_REQUIRED")
        raw = external_path(repo, case.image_path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError("FROZEN_IMAGE_HASH_MISMATCH")
        with Image.open(BytesIO(raw)) as image:
            image.load()
            if (image.format != "PNG" or image.size != (256, 256)
                    or getattr(image, "n_frames", 1) != 1):
                raise ValueError("FROZEN_IMAGE_GEOMETRY_MISMATCH")
        # Literal prefix only. E.g. 'detect Locate the green circle.'.
        request = Request(Task.GROUNDING, case.case_id, case.image_path, raw,
                          PROMPT_ID, "detect " + case.target_query)
        metadata = {**asdict(case), "image_sha256": entry["sha256"],
                    "target_gt_bbox": list(case.target_gt_bbox),
                    "distractor_gt_bbox": list(case.distractor_gt_bbox),
                    "manifest_sha256": plan["manifest_sha256"], "source_kind": "synthetic",
                    "prompt": request.prompt, "prompt_version": PROMPT_ID,
                    "prompt_sha256": hashlib.sha256(request.prompt.encode()).hexdigest()}
        inputs.append((request, metadata))
    return cases, inputs


def collect_case(runner, store, request, context, fixture, torch):
    provenance = {
        **asdict(context), "sample_id": request.sample_id, "task_type": request.task.value,
        "model_id": MODEL_ID, "revision": REVISION, "runner_version": runner.version,
        "prompt_id": request.prompt_id, "prompt": request.prompt,
        "prompt_sha256": hashlib.sha256(request.prompt.encode("utf-8")).hexdigest(),
        "input_sha256": hashlib.sha256(request.input_bytes).hexdigest(),
        "fixture": fixture, "plan_sha256": PLAN_SHA256, "parse_status": "NOT_ATTEMPTED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    result = {"case_id": context.call_id, "task_type": request.task.value,
              "prompt": request.prompt, "fixture": fixture, "raw": None,
              "status": STOP, "timing": {}, "observation": None}
    started = time.perf_counter()
    stage = "PREPARE_INPUT"
    try:
        prepared = runner.prepare_input(request, context)
        torch.cuda.synchronize(0)
        generation_started = time.perf_counter()
        stage = "NATIVE_GENERATE"
        try:
            raw = runner.generate_raw(prepared, context)
        except GenerationFailure as exc:
            if exc.partial_raw is not None:
                ref, _ = persist_verified(store, exc.partial_raw, provenance)
                result["raw"] = asdict(ref)
            raise
        # Persist before adapter, JSON deserialization or timing postprocessing.
        stage = "RAW_PERSISTENCE"
        ref, persisted = persist_verified(store, raw, provenance)
        result["raw"] = asdict(ref)
        torch.cuda.synchronize(0)
        result["timing"]["generate_audit_persist_sync_seconds"] = time.perf_counter() - generation_started
        stage = "CANONICAL_ADAPTER"
        parsed, diagnostic = parse_probe(persisted, fixture["target_query"])
        result.update(observation=diagnostic, parser_status=parsed.status,
                      parser_errors=list(parsed.errors),
                      predicted_bbox=list(parsed.value.bbox) if parsed.success else None)
        result["status"] = COMPLETE
    except Exception as exc:
        # Do not serialize arbitrary exception messages/environments into evidence.
        result["failure"] = {"stage": stage, "type": type(exc).__name__}
        raise
    finally:
        result["timing"]["case_wall_seconds"] = time.perf_counter() - started
        write_json(store.root / (context.call_id + ".json"), result)
    return result, parsed


def run_gate(*, expected_commit, venue_internet_off, repo=ROOT,
                      cache_dir=CACHE, runner_factory=PaliGemmaRunner, torch_module=None):
    """One fixed attempt; injection exists for fake tests, not as a CLI option."""
    repo = Path(repo)
    store = VerifiedRawStore(repo, ARTIFACTS + "/" + RUN_ID)
    store.root.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": "paligemma-frozen-external-gate-evidence-v1", "run_id": RUN_ID,
              "status": STOP, "plan_path": PLAN, "plan_sha256": PLAN_SHA256,
              "base_sha": BASE_SHA, "execution_commit": expected_commit,
              "model_id": MODEL_ID, "revision": REVISION,
              "calls": [], "model_load_count": 0, "native_generate_calls": 0,
              "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "classification_calls": 0, "classification_interface_status": "PENDING_QUALIFICATION",
              "paligemma_external_gate_status": "NOT_RUN", "promotion": False}
    runner = None
    stage = "CHECKOUT"
    try:
        checkout_gate(repo, expected_commit)
        subprocess.run(["git", "merge-base", "--is-ancestor", BASE_SHA, expected_commit],
                       cwd=repo, check=True, capture_output=True)
        stage = "PLAN"
        plan = gate_plan(repo)
        stage = "FROZEN_SUITE"
        frozen_cases, inputs = verify_suite(plan, repo)
        runtime = load_plan(repo)
        report["preserved_status"] = plan["preserved_status"]
        report["interpretation"] = plan["interpretation"]
        write_json(store.root / "gate_plan.json", plan)
        report["source_hashes"] = {p: sha256_file(repo / p) for p in (
            PLAN, plan["runtime_plan"], "requirements-paligemma-t4.txt",
            "safeshift/runners/paligemma.py", "safeshift/runners/paligemma_snapshot.py",
            "safeshift/runners/storage.py", "scripts/w2_paligemma_external_gate.py",
            "scripts/w2_paligemma_interface_qualification.py",
            "safeshift/protocol/gate.py", "safeshift/protocol/schema.py",
            "safeshift/runners/paligemma_external_probe.py",
            plan["manifest"], plan["provenance"], plan["generator"], plan["negative_evidence"]["path"])}
        stage = "OFFLINE_PREFLIGHT"
        if venue_internet_off is not True:
            raise ValueError("OWNER_INTERNET_OFF_REQUIRED")
        require_offline_env()
        if (os.environ.get("CUDA_VISIBLE_DEVICES") != "0"
                or os.environ.get("CUDA_DEVICE_ORDER") != "PCI_BUS_ID"):
            raise ValueError("SINGLE_VISIBLE_T4_MASK_REQUIRED_BEFORE_IMPORT")
        if any(os.environ.get(k) for k in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN")):
            raise ValueError("CREDENTIAL_FREE_RUNTIME_REQUIRED")
        report["offline"] = {"owner_attested_internet_off": True, "variables": dict(OFFLINE_ENV),
                             "socket_denial": True, "cuda_visible_devices": "0",
                             "cuda_device_order": "PCI_BUS_ID"}
        with network_denied():
            stage = "SOFTWARE_HARDWARE"
            report["software"] = software_versions()
            if report["software"] != runtime["software"]:
                raise ValueError("EXACT_SOFTWARE_REQUIRED")
            if platform.system() != "Linux" or platform.machine() != "x86_64":
                raise ValueError("LINUX_X86_64_REQUIRED")
            if torch_module is None:
                import torch as torch_module
            report["hardware"] = probe_hardware(torch_module)
            torch_module.cuda.reset_peak_memory_stats(0)
            stage = "FIXTURES"
            manifest = []
            for request, metadata in inputs:
                manifest.append(metadata)
                with (store.root / (request.sample_id + ".png")).open("xb") as stream:
                    stream.write(request.input_bytes)
                    stream.flush()
                    os.fsync(stream.fileno())
            write_json(store.root / "fixture_manifest.json", manifest)
            command = ("python scripts/w2_paligemma_external_gate.py --expected-commit "
                       + expected_commit + " --cache-dir " + cache_dir + " --venue-internet-off")
            context = RunContext(RUN_ID, CASE_IDS[0], dict(DECODING),
                                 dict(PREPROCESSING), "FP16", "NONE", {"placement": "cuda:0"},
                                 report["software"], expected_commit, command,
                                 "HANDCRAFTED_RUNTIME_SMOKE")
            # Retain the audited runner's narrow source-kind allowlist. Actual
            # qualification scope/fixture provenance is explicit in every record.
            report["command"] = command
            report["seed"] = None
            runner = runner_factory(repo=repo, cache_dir=cache_dir)
            stage = "INITIALIZE_LOAD"
            started = time.perf_counter()
            runner.initialize(context)
            runner.load(context)
            torch_module.cuda.synchronize(0)
            report["initialize_load_seconds"] = time.perf_counter() - started
            predictions = {}
            for request, metadata in inputs:
                stage = request.sample_id
                ctx = replace(context, call_id=request.sample_id, input_provenance=metadata)
                result, parsed = collect_case(runner, store, request, ctx, metadata, torch_module)
                result["result_path"] = request.sample_id + ".json"
                report["calls"].append(result)
                predictions[request.sample_id] = parsed
            stage = "CANONICAL_GATE"
            gate = evaluate_gate(repo, frozen_cases, predictions, reviews=None)
            report["gate"] = asdict(gate)
            report["paligemma_external_gate_status"] = gate.status
            report["negative_evidence"] = plan["negative_evidence"]
            for call, metrics in zip(report["calls"], gate.cases):
                call["gate_result"] = asdict(metrics)
            write_json(store.root / "gate.json", asdict(gate))
            write_json(store.root / "human_review_template.json", {
                case_id: {"status": "PENDING", "reviewer": "", "rationale": ""}
                for case_id in CASE_IDS})
            stage = "FINAL_AUDIT"
            runner._stable("qualification_final")
            if runner.model_load_count != 1 or runner.native_generate_calls != 8:
                raise ValueError("ONE_LOAD_EIGHT_CALLS_REQUIRED")
            report["memory"] = memory_observation(torch_module)
            report["status"] = COMPLETE
    except Exception as exc:
        report["failure"] = {"stage": stage, "type": type(exc).__name__}
    finally:
        if runner is not None:
            report.update(model_load_count=runner.model_load_count,
                          native_generate_calls=runner.native_generate_calls,
                          state_audits=runner.audits, runner_state=runner.state,
                          snapshot=runner.snapshot)
            runner.close()
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        report["artifacts"] = {p.relative_to(store.root).as_posix(): {
            "sha256": sha256_file(p), "size_bytes": p.stat().st_size}
            for p in sorted(store.root.rglob("*")) if p.is_file()}
        write_json(store.root / "summary.json", report)
        write_json(store.root / "summary.sha256.json", {"sha256": sha256_file(store.root / "summary.json")})
    return report


def finalize_review(review_file, *, expected_commit, repo=ROOT):
    """No model/GPU access. Recheck raw bytes and score explicit human reviews.

    A separate final artifact preserves the original runtime report and outputs.
    No automatic reviewer, giant-box threshold, retry or role promotion.
    """
    repo = Path(repo)
    checkout_gate(repo, expected_commit)
    plan = gate_plan(repo)
    cases, inputs = verify_suite(plan, repo)
    root = repo / ARTIFACTS / RUN_ID
    raw_summary = (root / "summary.json").read_bytes()
    if hashlib.sha256(raw_summary).hexdigest() != strict_json(
            (root / "summary.sha256.json").read_bytes())["sha256"]:
        raise ValueError("SUMMARY_HASH_MISMATCH")
    summary = strict_json(raw_summary)
    if (summary["status"] != COMPLETE or summary["execution_commit"] != expected_commit
            or summary["plan_sha256"] != PLAN_SHA256
            or summary["model_load_count"] != 1 or summary["native_generate_calls"] != 8
            or summary["classification_calls"] != 0
            or summary["model_id"] != MODEL_ID or summary["revision"] != REVISION
            or summary["run_id"] != RUN_ID or summary["promotion"] is not False
            or [c["case_id"] for c in summary["calls"]] != list(CASE_IDS)):
        raise ValueError("COMPLETE_EXACT_GATE_EVIDENCE_REQUIRED")
    for relative, ref in summary["artifacts"].items():
        path = external_path(root, relative)
        if path.stat().st_size != ref["size_bytes"] or sha256_file(path) != ref["sha256"]:
            raise ValueError("RUNTIME_ARTIFACT_HASH_MISMATCH")
    decisions_path = external_path(repo, review_file)
    decisions = strict_json(decisions_path.read_bytes())
    if set(decisions) != set(CASE_IDS):
        raise ValueError("EIGHT_EXPLICIT_HUMAN_REVIEWS_REQUIRED")
    reviews = {key: GiantBoxReview(**value) for key, value in decisions.items()}
    if any(r.status == "PENDING" for r in reviews.values()):
        raise ValueError("FINAL_REVIEW_CANNOT_BE_PENDING")
    predictions = {}
    seen = set()
    for case, call, (request, _) in zip(cases, summary["calls"], inputs):
        ref = call["raw"]
        if (not ref["path"].startswith(ARTIFACTS + "/" + RUN_ID + "/")
                or ref["path"] in seen):
            raise ValueError("RAW_OUTSIDE_FIXED_RUN")
        seen.add(ref["path"])
        raw = external_path(repo, ref["path"]).read_bytes()
        if len(raw) != ref["size_bytes"] or hashlib.sha256(raw).hexdigest() != ref["sha256"]:
            raise ValueError("RAW_HASH_MISMATCH")
        if call["prompt"] != request.prompt or call["fixture"]["target_query"] != case.target_query:
            raise ValueError("REQUEST_PROVENANCE_MISMATCH")
        metadata = strict_json(external_path(repo, str(Path(ref["path"]).parent /
                                                       "metadata.json").replace("\\", "/")).read_bytes())
        if (metadata["raw_output"] != ref or metadata["run_id"] != RUN_ID
                or metadata["call_id"] != case.case_id or metadata["sample_id"] != case.case_id
                or metadata["git_commit_sha"] != expected_commit
                or metadata["prompt"] != request.prompt or metadata["parse_status"] != "NOT_ATTEMPTED"
                or metadata["input_sha256"] != hashlib.sha256(request.input_bytes).hexdigest()):
            raise ValueError("RAW_PROVENANCE_MISMATCH")
        parsed, _ = parse_probe(raw, case.target_query)
        predictions[case.case_id] = parsed
    gate = evaluate_gate(repo, cases, predictions, reviews=reviews)
    if gate.status not in {"PASS", "FAIL"}:
        raise ValueError("EXPLICIT_FINAL_REVIEW_REQUIRED")
    result = {"paligemma_external_gate_status": gate.status, "gate": asdict(gate),
              "execution_commit": expected_commit, "runtime_summary_sha256": hashlib.sha256(raw_summary).hexdigest(),
              "human_review_file": review_file, "human_review_sha256": sha256_file(decisions_path),
              "human_reviews": decisions, "negative_evidence": plan["negative_evidence"],
              "model_load_count": 1, "native_generate_calls": 8, "cases": 8,
              "classification_interface_status": "PENDING_QUALIFICATION", "promotion": False}
    write_json(root / "final_gate_review.json", result)
    write_json(root / "final_gate_review.sha256.json", {"sha256": sha256_file(root / "final_gate_review.json")})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-commit")
    parser.add_argument("--verify-suite", action="store_true")
    parser.add_argument("--review-file", help="Repository-relative explicit human decisions; no inference")
    parser.add_argument("--cache-dir", default=CACHE)
    parser.add_argument("--venue-internet-off", action="store_true")
    args = parser.parse_args()
    if args.verify_suite:
        try:
            verify_suite(gate_plan())
        except (ValueError, KeyError, OSError) as exc:
            print(STOP + ": " + str(exc))
            return 1
        print("FROZEN_EIGHT_CASE_INPUTS_VERIFIED")
        return 0
    if args.review_file:
        if not args.expected_commit:
            parser.error("--expected-commit required for review")
        report = finalize_review(args.review_file, expected_commit=args.expected_commit)
        print("PALIGEMMA_EXTERNAL_GATE_STATUS: " + report["paligemma_external_gate_status"])
        return 0
    if not args.expected_commit or not args.venue_internet_off:
        parser.error("--expected-commit and --venue-internet-off are required for runtime")
    report = run_gate(expected_commit=args.expected_commit,
                               venue_internet_off=args.venue_internet_off, cache_dir=args.cache_dir)
    print(report["status"])
    return 0 if report["status"] == COMPLETE else 1


if __name__ == "__main__":
    raise SystemExit(main())
