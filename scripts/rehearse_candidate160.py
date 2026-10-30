"""Execute synthetic CPU checks and record precise per-test/source evidence."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest

from safeshift.candidates.source import ROOT, require
from safeshift.candidates.train_contract import KEYS, config, configuration_hashes, sources, source_hash
from safeshift.pilot.artifacts import sha, write
from scripts.rehearse_candidate_integration import ReceiptResult


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=KEYS)
    parser.add_argument("--snapshot")
    parser.add_argument("--index")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).absolute()
    require(output.is_relative_to(ROOT / "data/processed"), "LOCAL_OUTPUT_UNDER_DATA_PROCESSED")
    output.mkdir(parents=True, exist_ok=False)
    if args.model:
        require(args.snapshot and args.index, "PUBLIC_SNAPSHOT_AND_INDEX_REQUIRED_NO_FETCH")
        os.environ.update(SAFESHIFT_CANDIDATE_KEY=args.model,
                          SAFESHIFT_CANDIDATE_SNAPSHOT=str(Path(args.snapshot).absolute()),
                          SAFESHIFT_CANDIDATE_INDEX=str(Path(args.index).absolute()))
    os.environ.update(CUDA_VISIBLE_DEVICES="", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    names = sources() + ["scripts/build_candidate160_notebooks.py", "scripts/rehearse_candidate160.py",
        "tests/test_candidate160.py", "tests/test_candidate_native.py", "tests/test_candidate160_notebooks.py",
        "tests/test_candidate160_batch.py", "scripts/candidate160_authority.py"]
    hashes = {n: sha(ROOT/n) for n in names}
    sys.path.insert(0, str(ROOT/"tests"))
    suite = unittest.TestSuite()
    for name in ("test_candidate160", "test_candidate160_batch", "test_candidate160_notebooks",
                 "test_candidate_native", "test_candidate_cpu", "test_candidate_integration"):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    with (output/"tests.log").open("x", encoding="utf-8") as log, redirect_stdout(log), redirect_stderr(log):
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=ReceiptResult).run(suite)
    changed = hashes != {n: sha(ROOT/n) for n in names}
    receipt = {"schema": "safeshift-candidate160-cpu-evidence-v2", "model_key": args.model,
        "configuration_contracts": {key: {"hashes": configuration_hashes(key), "contract": config(key)} for key in KEYS},
        "executed_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
        "platform": platform.platform(), "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": source_hash(), "executed_files": hashes, "source_changed": changed,
        "status": "CPU_CHECKS_PASS" if result.wasSuccessful() and not changed else "CPU_CHECKS_FAIL",
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skips": len(result.skipped), "test_events": result.events, "log_sha256": sha(output/"tests.log"),
        "scope": "SYNTHETIC_CPU_SCRIPTED_NOT_MODEL_PREDICTIONS", "gpu": "NOT_CALLED",
        "weights": "NOT_DOWNLOADED_OR_LOADED", "private_train_test": "NOT_ACCESSED",
        "behavior_quality_hnlo_gpu": "UNVERIFIED", "execution_release": "BLOCKED"}
    write(output/"receipt.json", receipt)
    print(receipt["status"], result.testsRun, "tests", receipt["skips"], "skips", args.model)
    return 0 if receipt["status"] == "CPU_CHECKS_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
