"""Separate load-only observability. Run only in a fresh, dedicated process."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.runners.contracts import RunContext
from safeshift.runners.moondream2 import (
    DECODING, PREPROCESSING, PLAN_SHA256, Moondream2Runner, load_plan,
)
from safeshift.runners.moondream_snapshot import (
    MODEL_ID, REVISION, TOKENIZER_REPO, TOKENIZER_REVISION,
)
from safeshift.runners.storage import FileRawStore

ARTIFACT_ROOT = "data/processed/moondream_load_diagnostic"
PREVIOUS_RUN = "kaggle-t4-moondream-smoke-20260926T070217Z-4c2d43"


def redact(text):
    """Keep diagnostic messages/paths; remove credential values, never dump locals."""
    for key, value in os.environ.items():
        if value and re.search(r"TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY", key, re.I):
            text = text.replace(value, "[REDACTED]")
    text = re.sub(r"\b(?:hf_[A-Za-z0-9]+|gh[pousr]_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+)\b",
                  "[REDACTED]", text)
    text = re.sub(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+", r"\1 [REDACTED]", text)
    text = re.sub(r"(?i)(https?://)[^\s/@]+:[^\s/@]+@", r"\1[REDACTED]@", text)
    return re.sub(
        r"(?i)(\b(?:[\w-]*token|api[_-]?key|password|secret|credential|signature)"
        r"[\"']?\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s&,;\)\]}]+)",
        r"\1[REDACTED]", text,
    )


def sanitized(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {redact(k): sanitized(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitized(v) for v in value]
    return value


def exception_record(error, stage):
    cause = error.__cause__
    context = error.__context__
    return {"stage": stage, "type": type(error).__name__, "message": str(error),
            "cause_type": type(cause).__name__ if cause is not None else None,
            "cause_message": str(cause) if cause is not None else None,
            "context_type": type(context).__name__ if context is not None else None,
            "context_message": str(context) if context is not None else None,
            "suppress_context": error.__suppress_context__,
            "traceback": "".join(traceback.format_exception(error))}


def run_diagnostic(*, repo, cache_dir, run_id, expected_commit):
    # Fixed namespace and single path component; no caller-selected output file.
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", run_id):
        raise ValueError("DIAGNOSTIC_RUN_ID_MUST_BE_A_SINGLE_SAFE_COMPONENT")
    directory = FileRawStore(repo, ARTIFACT_ROOT + "/" + run_id).root
    directory.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": "moondream-load-diagnostic-v1", "run_id": run_id,
              "scope": "LOAD_ONLY_DIAGNOSTIC_NOT_OFFICIAL_SMOKE_OR_QUALIFICATION",
              "previous_smoke_run_id": PREVIOUS_RUN, "status": "FAIL",
              "stage": "provenance", "exception": None, "runner_evidence": {},
              "execution_commit": None, "expected_commit": expected_commit,
              "software_versions": {}, "gpu": None,
              "gpu_metadata_source": "NOT_REACHED",
              "system": {"system": platform.system(), "machine": platform.machine()},
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "plan_sha256": PLAN_SHA256, "model_id": MODEL_ID, "model_revision": REVISION,
              "tokenizer_repo": TOKENIZER_REPO, "tokenizer_revision": TOKENIZER_REVISION,
              "precision": "FP16", "quantization": "NONE", "batch_size": 1,
              "preprocessing": PREPROCESSING,
              "network_policy": "UNCHANGED_RUNNER_OFFLINE_AND_PERMANENT_NETWORK_DENIAL",
              "artifact_path": directory.relative_to(repo.resolve()).as_posix() + "/report.json"}
    runner = None
    # Reserve a writable report before touching the runtime. Never overwrite.
    with (directory / "report.json").open("x", encoding="utf-8") as stream:
        try:
            # Git subprocesses must finish before initialize installs network denial.
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
            report["execution_commit"] = commit
            if (not re.fullmatch(r"[0-9a-f]{40}", commit) or commit != expected_commit
                    or subprocess.call(["git", "diff", "--quiet", "HEAD"], cwd=repo)):
                raise ValueError("EXACT_EXECUTION_COMMIT_AND_CLEAN_TRACKED_CHECKOUT_REQUIRED")
            report["stage"] = "configuration"
            plan = load_plan()
            cache = FileRawStore(repo, cache_dir).root
            command = ["scripts/w2_moondream_load_diagnostic.py", "--execute-load-diagnostic",
                       "--expected-commit", commit, "--cache-dir", cache_dir, "--run-id", run_id]
            context = RunContext(run_id, "load-only", DECODING, PREPROCESSING, "FP16", "NONE",
                                 {"placement": "cuda:0"}, plan["software"], commit,
                                 json.dumps(command), "LOAD_ONLY_DIAGNOSTIC")
            report["context"] = asdict(context)
            report["stage"] = "software_metadata"
            report["software_versions"]["python"] = platform.python_version()
            for name in plan["software"]:
                if name != "python":
                    try:
                        report["software_versions"][name] = version(name)
                    except PackageNotFoundError:
                        report["software_versions"][name] = None
            report["stage"] = "runner_construction"
            runner = Moondream2Runner(
                cache / "models--vikhyatk--moondream2" / "snapshots" / REVISION,
                cache / "models--moondream--starmie-v1" / "snapshots" / TOKENIZER_REVISION,
            )
            report["stage"] = "initialize"
            runner.initialize(context)
            report["stage"] = "load"
            runner.load(context)
            report["stage"] = "complete"
            report["status"] = "LOAD_ONLY_PASS"
        except BaseException as error:
            report["exception"] = exception_record(error, report["stage"])
        finally:
            if runner is not None:
                report["runner_evidence"] = runner.evidence
                report["gpu"] = runner.evidence.get("gpu")
                if report["gpu"] is not None:
                    report["gpu_metadata_source"] = "runner.initialize"
            report["finished_utc"] = datetime.now(timezone.utc).isoformat()
            report = sanitized(report)
            json.dump(report, stream, indent=2, ensure_ascii=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-load-diagnostic", action="store_true", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    report = run_diagnostic(repo=ROOT, cache_dir=args.cache_dir, run_id=args.run_id,
                            expected_commit=args.expected_commit)
    print(json.dumps({k: report[k] for k in ("status", "stage", "artifact_path")}))
    return 0 if report["status"] == "LOAD_ONLY_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
