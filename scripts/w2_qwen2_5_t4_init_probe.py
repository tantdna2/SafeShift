"""Future offline T4 initialize-only probe: no snapshot, model load or calls."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.provision_qwen2_5_snapshot import (
    MODEL_ID, REVISION, PLAN, PLAN_SHA256, load_plan, network_denied, sha256_file, write_json,
)
from scripts.w2_qwen2_5_t4_smoke import OFFLINE_ENV, CASE_IDS, is_oom, probe_hardware, software_versions
from safeshift.runners.qwen2_5_vl import (
    PREPROCESSING, Qwen2_5VLRunner, Qwen2_5InitializeDiagnosticFailure,
)
from safeshift.runners.contracts import RunContext
from safeshift.runners.storage import FileRawStore

ARTIFACTS = "data/processed/runtime_validation/w2_qwen2_5_t4_init_probe"


def run_probe(run_id, expected_commit, *, repo=ROOT, runner_factory=Qwen2_5VLRunner,
              torch_module=None):
    """Fake injection is test-only; CLI always uses the native lazy backend."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
        raise ValueError("INVALID_RUN_ID")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise ValueError("EXACT_EXPECTED_COMMIT_REQUIRED")
    root = FileRawStore(repo, ARTIFACTS + "/" + run_id).root
    root.mkdir(parents=True, exist_ok=False)
    command = ("python scripts/w2_qwen2_5_t4_init_probe.py --run-id " + run_id
               + " --expected-commit " + expected_commit)
    metadata = {"schema_version": "qwen2-5-init-probe-metadata-v1", "run_id": run_id,
                "started_at_utc": datetime.now(timezone.utc).isoformat(), "command": command,
                "expected_git_commit": expected_commit, "model_id": MODEL_ID,
                "model_revision": REVISION, "plan_sha256": PLAN_SHA256}
    environment = {}
    summary = {"schema_version": "qwen2-5-init-probe-summary-v1", "run_id": run_id,
               "scope": "INITIALIZE_ONLY", "status": "RUNTIME_INTERFACE_FAILURE",
               "model_load_reached": False, "native_generate_calls": 0, "calls": [],
               "inspecsafe_used": False, "synthetic_gate_used": False,
               "protocol_freeze_commit_sha": "PENDING"}
    stage = "PREFLIGHT"
    torch = None
    try:
        plan = load_plan(repo)
        metadata["git_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        if metadata["git_commit"] != expected_commit:
            raise ValueError("GIT_COMMIT_MISMATCH")
        if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"],
                                   cwd=repo, text=True).strip():
            raise ValueError("TRACKED_WORKTREE_MUST_MATCH_COMMIT")
        metadata["source_hashes"] = {p: sha256_file(repo / p) for p in
            (PLAN, "scripts/w2_qwen2_5_t4_init_probe.py", "scripts/w2_qwen2_5_t4_smoke.py",
             "scripts/provision_qwen2_5_snapshot.py", "safeshift/runners/qwen2_5_vl.py")}
        environment["offline_variables"] = {k: os.environ.get(k) for k in OFFLINE_ENV}
        if environment["offline_variables"] != OFFLINE_ENV:
            raise ValueError("SET_OFFLINE_ENV_BEFORE_PROCESS_START")
        with network_denied():
            stage = "ENVIRONMENT"
            if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
                raise ValueError("LINUX_X86_64_REQUIRED")
            if torch_module is None:
                import torch as torch_module
            torch = torch_module
            environment["software"] = software_versions(torch)
            if environment["software"] != plan["software"]:
                raise ValueError("EXACT_SOFTWARE_PINS_REQUIRED")
            environment["hardware"] = probe_hardware(torch)
            if torch.version.cuda != plan["cuda_runtime"]:
                raise ValueError("CUDA_BUILD_MISMATCH")
            # Identical smoke execution condition and first-call context fields.
            # Only command/run provenance identifies this initialize-only invocation.
            context = RunContext(run_id, CASE_IDS[0], plan["smoke"]["decoding"],
                                 dict(PREPROCESSING), "FP16", "NONE", {"placement": "cuda:0"},
                                 environment["software"], metadata["git_commit"], command,
                                 "HANDCRAFTED_RUNTIME_SMOKE")
            metadata["initialize_context"] = asdict(context)
            stage = "INITIALIZE"
            runner = runner_factory()
            runner.initialize(context)
            summary["status"] = "INITIALIZE_INTERFACE_PASS"
    except Exception as exc:
        summary["status"] = ("RUNTIME_RESOURCE_FAILURE" if torch is not None and is_oom(exc, torch)
                             else "RUNTIME_INTERFACE_FAILURE")
        summary["failure"] = {"stage": stage, "error_type": type(exc).__name__}
        if isinstance(exc, Qwen2_5InitializeDiagnosticFailure):
            summary["failure"].update(initialize_substage=exc.diagnostic_stage,
                                      underlying_error_type=exc.underlying_error_type)
    finally:
        metadata["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(root / "run_metadata.json", metadata)
        write_json(root / "environment.json", environment)
        summary["artifacts"] = {p.name: {"sha256": sha256_file(p), "size_bytes": p.stat().st_size}
                                for p in sorted(root.iterdir()) if p.is_file()}
        write_json(root / "summary.json", summary)
        with (root / "summary.json.sha256").open("x", encoding="ascii") as stream:
            stream.write(sha256_file(root / "summary.json") + "  summary.json\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-commit", required=True, help="Reviewed exact 40-character Git SHA")
    args = parser.parse_args()
    result = run_probe(args.run_id, args.expected_commit)
    print(json.dumps({"run_id": args.run_id, "status": result["status"]}))
    return 0 if result["status"] == "INITIALIZE_INTERFACE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
