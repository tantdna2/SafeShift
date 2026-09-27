"""Separate one-attempt post-fix Moondream smoke. PREP only; no runtime approval."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.w2_moondream_t4_smoke import fixture_bytes, run_smoke
from safeshift.runners.moondream2 import Moondream2Runner
from safeshift.runners.moondream_snapshot import REVISION, TOKENIZER_REVISION, json_bytes
from safeshift.runners.storage import FileRawStore

ARTIFACT_ROOT = "data/processed/moondream_postfix_smoke"
CACHE_DIR = "data/processed/moondream_hf"
HISTORICAL_RUN = "kaggle-t4-moondream-smoke-20260926T070217Z-4c2d43"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-postfix-smoke", action="store_true", required=True)
    parser.add_argument("--venue-network-disabled", action="store_true", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"moondream-postfix-smoke-[A-Za-z0-9_-]{1,100}", args.run_id):
        parser.error("distinct moondream-postfix-smoke- run ID required")
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_commit):
        parser.error("exact 40-character execution commit required")
    # All Git processes finish before initialize installs permanent offline denial.
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=normal"], cwd=ROOT, text=True)
    if commit != args.expected_commit or dirty.strip():
        parser.error("approved exact execution commit and clean checkout required")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        parser.error("launch a fresh process with CUDA_VISIBLE_DEVICES=0")
    content = fixture_bytes()
    cache = FileRawStore(ROOT, CACHE_DIR).root
    if not cache.is_dir():
        parser.error("existing verified cache required; no provisioning or fallback")
    store = FileRawStore(ROOT, ARTIFACT_ROOT + "/raw")
    artifact = FileRawStore(ROOT, ARTIFACT_ROOT).root
    artifact.mkdir(parents=True, exist_ok=True)
    command = json.dumps([
        "scripts/w2_moondream_postfix_smoke.py", "--execute-postfix-smoke",
        "--venue-network-disabled", "--expected-commit", commit, "--run-id", args.run_id])
    identity = {
        "scope": "POST_FIX_SMOKE_NOT_HISTORICAL_OFFICIAL_SMOKE",
        "historical_official_smoke": {"run_id": HISTORICAL_RUN, "status": "FAIL",
                                      "attempt_consumed": True, "superseded": False},
        "run_id": args.run_id, "execution_commit": commit, "command": command,
        "cuda_visible_devices": "0", "cache_dir": CACHE_DIR,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    # Fixed across run IDs. Never remove/reset, including on failure or interruption.
    # No access to the historical namespace, ledger or result.
    with (artifact / "ATTEMPT.json").open("x", encoding="utf-8") as stream:
        json.dump(identity, stream)
        stream.flush()
        os.fsync(stream.fileno())
    # Reserve output before constructing the runner; an interruption consumes the attempt.
    with (artifact / "result.json").open("xb") as stream:
        runner = Moondream2Runner(
            cache / "models--vikhyatk--moondream2" / "snapshots" / REVISION,
            cache / "models--moondream--starmie-v1" / "snapshots" / TOKENIZER_REVISION,
        )
        report = run_smoke(runner, run_id=args.run_id, execution_commit=commit,
                           store=store, image_bytes=content, command=command)
        report.update(identity)
        report["schema_version"] = "moondream-postfix-smoke-result-v1"
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        stream.write(json_bytes(report) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": report["status"], "run_id": args.run_id, "scope": report["scope"]}))
    return 0 if report["status"] == "RUNTIME_INTERFACE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
