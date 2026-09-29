"""PREP only: future owner-run, offline, exactly one T4 interface smoke."""

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import importlib.metadata
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.runners.contracts import ErrorCode, Request, RunContext, Task
from safeshift.runners.paligemma import (DECODING, PREPROCESSING, PaliGemmaRunner, execute_call,
                                       PendingPaliGemmaAdapter, VerifiedRawStore,
                                       exception_record, probe_hardware, software_versions)
from safeshift.runners.paligemma_snapshot import (CACHE, MODEL_ID, REVISION, OFFLINE_ENV,
                                                PLAN, PLAN_SHA256, load_plan, network_denied,
                                                require_offline_env, sha256_file, write_json)

ARTIFACTS = "data/processed/runtime_validation/w2_paligemma_t4_smoke"
CASE_IDS = ("case_01", "case_02")


def checkout_gate(repo, expected_commit):
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise ValueError("FULL_AUDITED_EXECUTION_COMMIT_REQUIRED")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    if head != expected_commit:
        raise ValueError("EXECUTION_COMMIT_MISMATCH")
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"],
                               cwd=repo, text=True).strip():
        raise ValueError("CLEAN_CHECKOUT_REQUIRED")
    return head


def generate_cases():
    from PIL import Image, ImageDraw
    for index, case_id in enumerate(CASE_IDS):
        # Different aspect ratios test independent image/token preparation.
        with Image.new("RGB", (64 + 64 * index, 64), "white") as image:
            draw = ImageDraw.Draw(image)
            if index == 0:
                draw.rectangle((8, 8, 40, 40), fill="blue")
            else:
                draw.ellipse((64, 16, 112, 56), fill="green")
            stream = BytesIO()
            image.save(stream, format="PNG")
            size = list(image.size)
        raw = stream.getvalue()
        yield case_id, raw, {"generator": "paligemma-smoke-shapes-v1", "size": size,
                             "sha256": hashlib.sha256(raw).hexdigest()}


def memory_observation(torch):
    torch.cuda.synchronize(0)
    return {"allocated_bytes": torch.cuda.memory_allocated(0),
            "reserved_bytes": torch.cuda.memory_reserved(0),
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(0),
            "peak_reserved_bytes": torch.cuda.max_memory_reserved(0)}


def run_smoke(run_id, *, expected_commit, venue_internet_off, repo=ROOT,
              cache_dir=CACHE, runner_factory=PaliGemmaRunner, torch_module=None):
    """Test injection is private to Python callers; CLI has no fake-backend mode."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
        raise ValueError("INVALID_RUN_ID")
    repo = Path(repo)
    store = VerifiedRawStore(repo, ARTIFACTS + "/" + run_id)
    store.root.mkdir(parents=True, exist_ok=False)
    summary = {"schema_version": "paligemma-t4-smoke-summary-v1", "run_id": run_id,
               "status": "RUNTIME_INTERFACE_FAILURE", "scope": "RUNTIME_INTERFACE_ONLY",
               "model_id": MODEL_ID, "revision": REVISION, "calls": [], "memory": {},
               "model_load_count": 0, "native_generate_calls": 0, "state_audits": [],
               "classification": "PENDING_QUALIFICATION", "grounding": "PENDING_QUALIFICATION",
               "external_gate": "PENDING_QUALIFICATION", "paligemma_role": "BACKUP_1",
               "primary_roster_count": 4, "promotion": False,
               "synthetic_gate_used": False, "inspecsafe_used": False,
               "inspecsafe_inference_authorized": False, "protocol_freeze_commit_sha": "PENDING"}
    metadata = {"started_at_utc": datetime.now(timezone.utc).isoformat(),
                "plan_sha256": PLAN_SHA256, "expected_commit": expected_commit,
                "command": ["python", "scripts/w2_paligemma_t4_smoke.py", "--run-id", run_id,
                            "--expected-commit", expected_commit, "--cache-dir", cache_dir,
                            "--venue-internet-off"], "seed": None,
                "decoding": DECODING, "preprocessing": PREPROCESSING,
                "precision": "FP16", "quantization": "NONE", "batch_size": 1,
                "cpu_offload": False, "disk_offload": False, "fallback": False,
                "venue_internet_off_owner_attested": venue_internet_off,
                "network_policy": "VENUE_OFF_PLUS_OFFLINE_ENV_PLUS_SOCKET_DENIAL"}
    environment, snapshot = {}, {"local_bytes_verified": False}
    runner = torch = None
    stage = "CHECKOUT"
    try:
        metadata["git_commit"] = checkout_gate(repo, expected_commit)
        plan = load_plan(repo)
        stage = "OFFLINE_PREFLIGHT"
        if venue_internet_off is not True:
            raise ValueError("VENUE_INTERNET_OFF_REQUIRED")
        require_offline_env()
        environment["offline_variables"] = {k: os.environ.get(k) for k in OFFLINE_ENV}
        environment["cuda_visible_devices"] = os.environ.get("CUDA_VISIBLE_DEVICES")
        metadata["source_hashes"] = {p: sha256_file(repo / p) for p in (
            PLAN, "configs/pre_freeze/paligemma_source_api_audit.v1.json", "requirements-paligemma-t4.txt",
            "safeshift/runners/paligemma.py", "safeshift/runners/paligemma_snapshot.py",
            "scripts/w2_paligemma_t4_smoke.py", "scripts/provision_paligemma_snapshot.py",
            "safeshift/runners/contracts.py", "safeshift/runners/storage.py")}
        with network_denied():
            stage = "SOFTWARE"
            environment["software"] = software_versions()
            if environment["software"] != plan["software"]:
                raise ValueError("EXACT_SOFTWARE_PINS_REQUIRED")
            if platform.system() != "Linux" or platform.machine() != "x86_64":
                raise ValueError("LINUX_X86_64_REQUIRED")
            environment["installed_distributions"] = sorted(
                [{"name": d.metadata["Name"], "version": d.version}
                 for d in importlib.metadata.distributions()], key=lambda d: d["name"] or "")
            if torch_module is None:
                import torch as torch_module
            torch = torch_module
            stage = "HARDWARE"
            environment["hardware"] = probe_hardware(torch)
            torch.cuda.reset_peak_memory_stats(0)
            summary["memory"]["before_load"] = memory_observation(torch)
            stage = "INITIALIZE"
            runner = runner_factory(repo=repo, cache_dir=cache_dir)
            context = RunContext(run_id, CASE_IDS[0], dict(DECODING), dict(PREPROCESSING),
                                 "FP16", "NONE", {"placement": "cuda:0"}, environment["software"],
                                 metadata["git_commit"], " ".join(metadata["command"]),
                                 "HANDCRAFTED_RUNTIME_SMOKE")
            runner.initialize(context)
            stage = "LOAD"
            runner.load(context)
            snapshot = runner.snapshot
            summary["memory"]["after_load"] = memory_observation(torch)
            for case_id, raw, provenance in generate_cases():
                stage = "CALL_" + case_id
                # Save the generated fixture once for reproduction; no input path option.
                with (store.root / (case_id + ".png")).open("xb") as stream:
                    stream.write(raw)
                request = Request(Task.CLASSIFICATION, case_id, case_id, raw,
                                  "paligemma-native-smoke-v1", plan["smoke"]["prompt"])
                ctx = replace(context, call_id=case_id, input_provenance=provenance)
                result = execute_call(runner, PendingPaliGemmaAdapter(), store, request, ctx)
                store.save_result(result)
                summary["calls"].append({"case_id": case_id, "parse_status": result.parse_status.value,
                    "error": asdict(result.error) if result.error else None,
                    "raw": asdict(result.raw_output) if result.raw_output else None, "input": provenance})
                summary["memory"][case_id] = memory_observation(torch)
                if (runner.failure or not result.raw_output or result.parse_status.value != "INVALID"
                        or not result.error or result.error.code != ErrorCode.INVALID_CLASSIFICATION):
                    raise RuntimeError("NATIVE_CALL_OR_RAW_PERSISTENCE_FAILED")
                path = repo / result.raw_output.path
                if (sha256_file(path) != result.raw_output.sha256
                        or path.stat().st_size != result.raw_output.size_bytes):
                    raise ValueError("POST_CALL_RAW_HASH_OR_SIZE_MISMATCH")
            stage = "FINAL_AUDIT"
            runner._stable("final")
            if runner.model_load_count != 1 or runner.native_generate_calls != 2:
                raise ValueError("ONE_LOAD_TWO_NATIVE_CALLS_REQUIRED")
            summary["status"] = "RUNTIME_INTERFACE_PASS"
    except Exception as exc:
        failure = ((runner.failure if runner else None) or store.failure
                   or exception_record(exc, stage, torch))
        summary["failure"] = failure
        summary["status"] = failure["status"]
    finally:
        if runner is not None:
            summary.update(model_load_count=runner.model_load_count,
                           native_generate_calls=runner.native_generate_calls,
                           state_audits=runner.audits, runner_state=runner.state)
            snapshot = runner.snapshot or snapshot
            runner.close()
        if torch is not None:
            try:
                summary["memory"]["final"] = memory_observation(torch)
            except Exception as exc:
                summary["memory_observation_failure"] = exception_record(exc, "FINAL_MEMORY", torch)
                if summary["status"] == "RUNTIME_INTERFACE_PASS":
                    summary["status"] = "RUNTIME_INTERFACE_FAILURE"
        metadata["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(store.root / "run_metadata.json", metadata)
        write_json(store.root / "environment.json", environment)
        write_json(store.root / "snapshot_manifest.json", snapshot)
        summary["artifacts"] = {p.relative_to(store.root).as_posix(): {
            "sha256": sha256_file(p), "size_bytes": p.stat().st_size}
            for p in sorted(store.root.rglob("*")) if p.is_file()}
        write_json(store.root / "summary.json", summary)
        write_json(store.root / "summary.sha256.json", {"sha256": sha256_file(store.root / "summary.json")})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-commit", required=True, help="Full audited execution SHA")
    parser.add_argument("--cache-dir", default=CACHE)
    parser.add_argument("--venue-internet-off", required=True, action="store_true")
    args = parser.parse_args()
    report = run_smoke(args.run_id, expected_commit=args.expected_commit,
                       venue_internet_off=args.venue_internet_off, cache_dir=args.cache_dir)
    print(report["status"])
    return 0 if report["status"] == "RUNTIME_INTERFACE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
