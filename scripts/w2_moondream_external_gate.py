"""One-attempt frozen native-detect gate PREP; no automatic qualification."""

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.protocol.firewall import external_path
from safeshift.protocol.gate import evaluate_gate, load_cases
from safeshift.protocol.schema import ParseResult, ProbePrediction, bbox, strict_json
from safeshift.runners.contracts import GenerationFailure, Request, RunContext, Task
from safeshift.runners.moondream2 import (
    DECODING, PREPROCESSING, PLAN_SHA256, Moondream2Runner, deserialize_native, load_plan,
)
from safeshift.runners.moondream_snapshot import (
    MODEL_ID, REVISION, TOKENIZER_REPO, TOKENIZER_REVISION, json_bytes,
)
from safeshift.runners.storage import FileRawStore, _write_new

PLAN = "configs/pre_freeze/moondream_external_gate.v1.json"
GATE_PLAN_SHA256 = "4fc2c43a0f6e7b6486bcee19f386589981487d09cb3f8e1daa0af462e14a9c7e"
MANIFEST = "configs/pre_freeze/external_gate_cases.v1.json"
PROVENANCE = "configs/pre_freeze/external_gate_cases.v1.provenance.json"
MANIFEST_SHA256 = "fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379"
PROVENANCE_SHA256 = "0b16be7408784c35bc3dc1a541f008b8086c4fa250957082a236d71ed3fe2e96"
CASE_IDS = tuple(f"{group}_{n}" for group in "ABCD" for n in (1, 2))
ARTIFACT_ROOT = "data/processed/external_gate/w2_moondream"
CACHE_DIR = "data/processed/moondream_hf"
ADAPTATION_VERSION = "moondream-external-exactly-one-xyxy1-v1"
COORDINATES = ("x_min", "y_min", "x_max", "y_max")


def load_gate_plan(repo):
    plan = strict_json(external_path(repo, PLAN).read_bytes())
    if hashlib.sha256(json_bytes(plan)).hexdigest() != GATE_PLAN_SHA256:
        raise ValueError("FROZEN_GATE_PLAN_CHANGED")
    for name, expected in plan["protected_source_sha256_lf"].items():
        raw = external_path(repo, name).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("PROTECTED_SOURCE_CHANGED")
    runtime = load_plan()  # Existing immutable runtime and bridge plan checks.
    if (plan["runtime_plan_sha256"] != PLAN_SHA256
            or plan["software"] != runtime["software"]
            or plan["detect_settings"] != DECODING["detect"]):
        raise ValueError("PINNED_RUNTIME_MISMATCH")
    return plan, runtime


def verify_suite(repo):
    """Fixed paths and exact bytes, before constructing any runtime/model."""
    from PIL import Image

    for path, digest in ((MANIFEST, MANIFEST_SHA256), (PROVENANCE, PROVENANCE_SHA256)):
        if hashlib.sha256(external_path(repo, path).read_bytes()).hexdigest() != digest:
            raise ValueError("FROZEN_SUITE_HASH_MISMATCH")
    provenance = strict_json(external_path(repo, PROVENANCE).read_bytes())
    if (provenance["suite_version"] != "synthetic-v1"
            or provenance["statement"] != "NO_INSPECSAFE_CONTENT_USED"):
        raise ValueError("FROZEN_PROVENANCE_MISMATCH")
    cases = load_cases(repo, MANIFEST)
    if (tuple(c.case_id for c in cases) != CASE_IDS
            or tuple(i["case_id"] for i in provenance["images"]) != CASE_IDS):
        raise ValueError("EXACT_EIGHT_CASE_ORDER_REQUIRED")
    inputs = []
    for case, entry in zip(cases, provenance["images"]):
        expected = f"tests/fixtures/pre_freeze/frozen_external_gate/{case.case_id}.png"
        if case.image_path != expected or entry["image_path"] != expected:
            raise ValueError("FROZEN_IMAGE_PATH_REQUIRED")
        raw = external_path(repo, case.image_path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError("FROZEN_IMAGE_HASH_MISMATCH")
        with Image.open(BytesIO(raw)) as image:
            image.load()
            if image.format != "PNG" or image.size != (256, 256) or image.n_frames != 1:
                raise ValueError("FROZEN_IMAGE_GEOMETRY_REQUIRED")
        inputs.append((case, raw, entry["sha256"]))
    return cases, inputs


def adapt_native(native):
    """No GT or image input. Caller must first durably preserve lossless bytes.

    Unknown native fields are retained in raw but not interpreted. Only exactly
    one object's four named, finite numeric coordinates can become a prediction.
    """
    diagnostic = {"raw_coordinates": None, "normalized_coordinates": None,
                  "clamped": None, "coordinate_convention": "xyxy_1"}
    if type(native) is not dict or type(native.get("objects")) is not list:
        return ParseResult("SCHEMA_ERROR", errors=("NATIVE_OBJECTS_LIST_REQUIRED",)), diagnostic
    objects = native["objects"]
    if len(objects) != 1:
        return ParseResult("SCHEMA_ERROR", errors=("EXACTLY_ONE_OBJECT_REQUIRED",),
                           boxes_attempted=len(objects)), diagnostic
    obj = objects[0]
    if type(obj) is not dict or not set(COORDINATES) <= obj.keys():
        return ParseResult("SCHEMA_ERROR", errors=("FOUR_NATIVE_COORDINATE_FIELDS_REQUIRED",)), diagnostic
    coordinates = [obj[key] for key in COORDINATES]
    try:
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in coordinates):
            raise ValueError("FINITE_NUMERIC_COORDINATES_REQUIRED")
    except (ValueError, OverflowError):
        # Nonfinite/malformed values remain lossless in response.raw; never emit
        # invalid JSON or relabel them as valid/clamped numeric coordinates.
        return ParseResult("COORDINATE_ERROR", errors=("FINITE_NUMERIC_COORDINATES_REQUIRED",)), diagnostic
    diagnostic["raw_coordinates"] = coordinates
    diagnostic["clamped"] = any(v < 0 or v > 1 for v in coordinates)
    try:
        normalized = bbox(coordinates, "xyxy_1")
    except (ValueError, OverflowError):
        return ParseResult("COORDINATE_ERROR", errors=("CANONICAL_GEOMETRY_INVALID",)), diagnostic
    diagnostic["normalized_coordinates"] = normalized
    return ParseResult("SUCCESS", ProbePrediction(normalized), response_schema_valid=True,
                       boxes_attempted=1, boxes_valid=1), diagnostic


def preserve_verified(store, raw, provenance):
    reference = store.preserve(raw, provenance)
    persisted = (store.repo / reference.path).read_bytes()
    if (persisted != raw or len(persisted) != reference.size_bytes
            or hashlib.sha256(persisted).hexdigest() != reference.sha256):
        raise ValueError("RAW_PRESERVATION_MISMATCH")
    return asdict(reference), persisted


def run_gate(*, repo, run_id, expected_commit, venue_network_disabled,
             runner_factory=Moondream2Runner):
    """Fake factory injection is tests-only; CLI exposes no alternative inputs."""
    if not re.fullmatch(r"moondream-external-gate-[A-Za-z0-9_-]{1,100}", run_id):
        raise ValueError("DISTINCT_GATE_RUN_ID_REQUIRED")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise ValueError("EXACT_EXECUTION_COMMIT_REQUIRED")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], cwd=repo, text=True)
    if commit != expected_commit or dirty.strip():
        raise ValueError("CLEAN_EXACT_EXECUTION_COMMIT_REQUIRED")
    if not venue_network_disabled or os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("VENUE_INTERNET_OFF_AND_CUDA_MASK_0_REQUIRED")
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("LINUX_X86_64_REQUIRED")
    if platform.python_version() != "3.11.11":
        raise ValueError("PYTHON_3_11_11_REQUIRED")
    plan, runtime = load_gate_plan(repo)
    cases, inputs = verify_suite(repo)
    cache = FileRawStore(repo, CACHE_DIR).root
    if not cache.is_dir():
        raise ValueError("EXISTING_CACHE_REQUIRED_NO_PROVISIONING")
    root = FileRawStore(repo, ARTIFACT_ROOT).root
    root.mkdir(parents=True, exist_ok=True)
    command = json.dumps(["scripts/w2_moondream_external_gate.py", "--execute-frozen-gate",
                          "--venue-network-disabled", "--expected-commit", commit, "--run-id", run_id])
    identity = {"run_id": run_id, "execution_commit": commit, "command": command,
                "started_utc": datetime.now(timezone.utc).isoformat(), "attempt_consumed": True,
                "gate_plan_sha256": GATE_PLAN_SHA256, "runtime_plan_sha256": PLAN_SHA256}
    # Fixed namespace, exclusive and fsynced BEFORE runner/backend construction.
    # Failure, interruption or a different run ID never releases this ledger.
    _write_new(root / "ATTEMPT.json", json_bytes(identity))
    store = FileRawStore(repo, ARTIFACT_ROOT + "/raw")
    report = {**identity, "schema_version": "moondream-external-gate-result-v1",
              "status": "GATE_EXECUTION_FAILURE", "completed_gate": False,
              "not_attempted_case_ids": list(CASE_IDS), "calls": [], "gate": None,
              "inspecsafe_used": False, "protocol_freeze_commit_sha": "PENDING",
              "venue_network_disabled_attested": True, "cuda_visible_devices": "0",
              "gate_plan": plan, "runtime": None}
    runner, stage = None, "construct"
    # An empty result after a hard kill also cannot be mistaken for completion.
    with (root / "result.json").open("xb") as output:
        try:
            runner = runner_factory(
                cache / "models--vikhyatk--moondream2" / "snapshots" / REVISION,
                cache / "models--moondream--starmie-v1" / "snapshots" / TOKENIZER_REVISION)
            report["runtime"] = runner.evidence
            context = RunContext(run_id, CASE_IDS[0], DECODING, PREPROCESSING, "FP16", "NONE",
                                 {"placement": "cuda:0"}, runtime["software"], commit, command, "synthetic")
            stage = "initialize"
            runner.initialize(context)  # Exact software/T4 and permanent offline denial.
            cuda = runner.backend.torch.cuda
            cuda.reset_peak_memory_stats(0)
            stage = "load"
            runner.load(context)  # Full pinned snapshot verification before native load.
            predictions = {}
            for case, image_bytes, image_sha in inputs:
                row = {**asdict(case), "image_sha256": image_sha, "status": "IN_PROGRESS",
                       "raw": None, "parse_status": "NOT_ATTEMPTED"}
                report["calls"].append(row)
                report["not_attempted_case_ids"].remove(case.case_id)
                ctx = replace(context, call_id=case.case_id, input_provenance={
                    "image_sha256": image_sha, "manifest_sha256": MANIFEST_SHA256})
                # Identity transform only: no noun extraction or GT-derived query.
                request = Request(Task.GROUNDING, case.case_id, case.image_path, image_bytes,
                                  ADAPTATION_VERSION, case.target_query)
                provenance = {**asdict(ctx), **asdict(runner.identity),
                    "sample_id": case.case_id, "input_id": case.image_path,
                    "input_sha256": image_sha, "prompt": case.target_query,
                    "prompt_sha256": hashlib.sha256(case.target_query.encode()).hexdigest(),
                    "prompt_id": ADAPTATION_VERSION, "task": "external_probe_native_detect",
                    "tokenizer_repo": TOKENIZER_REPO, "tokenizer_revision": TOKENIZER_REVISION,
                    "gate_plan_sha256": GATE_PLAN_SHA256, "parse_status": "NOT_ATTEMPTED",
                    "model_manifest_sha256": runner.evidence["model_manifest"]["manifest_sha256"],
                    "tokenizer_manifest_sha256": runner.evidence["tokenizer_manifest"]["manifest_sha256"]}
                stage = "prepare"
                prepared = runner.prepare_input(request, ctx)
                stage = "native_detect"
                try:
                    raw = runner.generate_raw(prepared, ctx)
                except GenerationFailure as failure:
                    if failure.partial_raw is not None:
                        row["partial"] = True
                        row["raw"], _ = preserve_verified(store, failure.partial_raw, provenance)
                    raise
                stage = "raw_preserve"
                row["raw"], persisted = preserve_verified(store, raw, provenance)
                stage = "adapt"
                parsed, diagnostic = adapt_native(deserialize_native(persisted))
                predictions[case.case_id] = parsed
                row.update(diagnostic, status="COMPLETED", parse_status=parsed.status,
                           parse_errors=parsed.errors)
                _write_new(root / (case.case_id + ".json"), json_bytes(row))
            stage = "final_invariants"
            evidence = runner.evidence
            if (not runner.valid or not runner.binding.valid
                    or evidence["model_load_count"] != 1 or evidence["query_call_count"] != 0
                    or evidence["detect_call_count"] != 8 or len(evidence["state_audits"]) != 17
                    or any(a["status"] != "VALID" for a in evidence["state_audits"])
                    or [r["boundary"] for r in evidence["image_boundaries"]] != [
                        "bridge_cpu", "transfer", "vision_consumption"] * 8):
                raise ValueError("EIGHT_DETECT_RUNTIME_INVARIANTS_REQUIRED")
            report["peak_cuda_memory_allocated"] = cuda.max_memory_allocated(0)
            report["peak_cuda_memory_reserved"] = cuda.max_memory_reserved(0)
            stage = "evaluate"
            gate = evaluate_gate(repo, cases, predictions, reviews=None)
            report["status"] = {"FAIL": "GATE_FAIL", "PENDING_REVIEW": "GATE_PENDING_REVIEW"}[gate.status]
            report["gate"] = asdict(gate)
            report["completed_gate"] = True
            # Review packet uses frozen image paths/hashes and separate raw/normalized
            # coordinates in calls, without generating an area-based human verdict.
            _write_new(root / "giant_review.template.json", json_bytes({
                "run_id": run_id, "execution_commit": commit,
                "reviews": {c.case_id: {"status": "PENDING", "reviewer": "", "rationale": ""}
                            for c in cases}}))
        except BaseException as error:
            report.update(status="GATE_EXECUTION_FAILURE", completed_gate=False)
            report["failure"] = {"stage": stage, "type": type(error).__name__,
                "cause_type": type(error.__cause__).__name__ if error.__cause__ else None}
            if report["calls"] and report["calls"][-1]["status"] == "IN_PROGRESS":
                report["calls"][-1]["status"] = "EXECUTION_FAILURE"
            if not isinstance(error, Exception):
                raise
        finally:
            report["finished_utc"] = datetime.now(timezone.utc).isoformat()
            report["artifacts"] = {p.relative_to(root).as_posix(): {
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "size_bytes": p.stat().st_size}
                for p in sorted(root.rglob("*")) if p.is_file() and p.name != "result.json"}
            output.write(json_bytes(report) + b"\n")
            output.flush()
            os.fsync(output.fileno())
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-frozen-gate", action="store_true", required=True)
    parser.add_argument("--venue-network-disabled", action="store_true", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    report = run_gate(repo=ROOT, run_id=args.run_id, expected_commit=args.expected_commit,
                      venue_network_disabled=args.venue_network_disabled)
    print(json.dumps({"status": report["status"], "run_id": args.run_id,
                      "completed_gate": report["completed_gate"]}))
    return 0 if report["status"] == "GATE_PENDING_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
