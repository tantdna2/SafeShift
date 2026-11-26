"""Reproduce candidate CPU integration evidence; no weights, GPU or inference."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import unittest

from safeshift.candidates.source import ROOT, LOCK, require
from safeshift.pilot.artifacts import read, sha, write
from safeshift.pilot.contract import source_digest
from safeshift.pilot.runner import error_record


def evidence_sources():
    return sorted({"scripts/rehearse_candidate_cpu.py", "scripts/rehearse_candidate_integration.py",
                   "scripts/pilot_source_audit.py", "scripts/fetch_candidate_indexes.py",
                   "tests/test_pilot.py", "tests/test_phi_evidence.py", "tests/test_smol_evidence.py",
                   "scripts/verify_candidate_evidence.py",
                   *[p.relative_to(ROOT).as_posix() for folder, pattern in
                     (("safeshift/candidates", "*.py"), ("configs/cpu_g2_g3", "*"), ("tests", "test_candidate*.py"))
                     for p in (ROOT/folder).glob(pattern) if p.is_file()]})


class ReceiptResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.events.append({"test": test.id(), "status": "PASS"})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.events.append({"test": test.id(), "status": "SKIP", "reason": reason})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.events.append({"test": test.id(), "status": "FAIL", "error": error_record(err[1], "unittest")})

    def addError(self, test, err):
        super().addError(test, err)
        self.events.append({"test": test.id(), "status": "ERROR", "error": error_record(err[1], "unittest")})

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.events.append({"test": subtest.id(), "status": "FAIL", "error": error_record(err[1], "subtest")})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", choices=("internvl35", "minicpm4"), required=True)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--index", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    output = Path(args.output).resolve()
    require(output.is_relative_to(ROOT/"data/processed"), "OUTPUT_UNDER_DATA_PROCESSED_REQUIRED")
    output.mkdir(parents=True, exist_ok=False)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                                         stderr=subprocess.PIPE).strip()
        require(__import__("re").fullmatch(r"[0-9a-f]{40}", commit), "GIT_COMMIT_REQUIRED")
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        write(output/"preflight_failure.json", {"status": "BLOCKED", "stage": "git_provenance",
            "error": error_record(error, "git_provenance"), "native_checks": "NOT_RUN"})
        print("BLOCKED: Git provenance unavailable; inspect preflight_failure.json")
        return 2
    os.environ.update(SAFESHIFT_CANDIDATE_KEY=args.model,
        SAFESHIFT_CANDIDATE_SNAPSHOT=str(Path(args.snapshot).absolute()),
        SAFESHIFT_CANDIDATE_INDEX=str(Path(args.index).absolute()),
        HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", CUDA_VISIBLE_DEVICES="")
    files = {name: sha(ROOT/name) for name in evidence_sources()}
    pilot = source_digest(ROOT)
    sys.path.insert(0, str(ROOT/"tests"))
    suite = unittest.TestSuite()
    for name in ("test_candidate_native", "test_candidate_cpu", "test_candidate_integration",
                 "test_pilot.ParserTests", "test_pilot.ArtifactAndEngineTests", "test_phi_evidence", "test_smol_evidence"):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    with (output/"tests.log").open("x", encoding="utf-8") as log:
        from contextlib import redirect_stdout, redirect_stderr
        with redirect_stdout(log), redirect_stderr(log):
            result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=ReceiptResult).run(suite)
    from test_candidate_native import NativeCandidateTests
    unchanged = files == {name: sha(ROOT/name) for name in files} and pilot == source_digest(ROOT)
    passed = result.wasSuccessful() and unchanged and bool(NativeCandidateTests.evidence.get("scripted_generation"))
    receipt = {"schema": "safeshift-candidate-integration-cpu-v1", "model_key": args.model,
        "model": {k: read(LOCK)[args.model][k] for k in ("id", "revision")},
        "executed_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "source_sha256": files, "pilot_source_sha256": pilot, "sources_unchanged_during_run": unchanged,
        "status": "CPU_CHECKS_PASS" if passed else "BLOCKED", "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped),
        "test_events": result.events, "checks": NativeCandidateTests.evidence,
        "full_local_log_sha256": sha(output/"tests.log"),
        "evidence_kind": "SYNTHETIC_SCRIPTED_LOGITS_META_LOADER_NOT_MODEL_PREDICTIONS",
        "weights": "NOT_DOWNLOADED_OR_DESERIALIZED", "inference": "NOT_RUN", "gpu": "NOT_CALLED",
        "cuda_vram_quality_hnlo": "UNVERIFIED", "scientific_approval": "NOT_GRANTED"}
    write(output/"receipt.json", receipt)
    write(output/"receipt.sha256.json", {"sha256": sha(output/"receipt.json")})
    print(args.model, receipt["status"], result.testsRun, "tests", len(result.skipped), "skips")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
