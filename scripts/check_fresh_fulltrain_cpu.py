"""Reproducible stdlib suite receipt for Issue171; no native opt-ins or GPU.

Run in an immutable Git export for final evidence. Output must be new.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pattern", default="test*.py")
    args = parser.parse_args()
    for name in tuple(os.environ):
        if name.startswith("SAFESHIFT_"):
            del os.environ[name]  # Disable optional native/download suites, no credential output.
    os.environ.update(CUDA_VISIBLE_DEVICES="", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    args.output.mkdir(parents=True, exist_ok=False)
    began = time.monotonic()
    from safeshift.fulltrain.contract import ROOT, source_manifest
    command = ["python", "-B", "-m", "scripts.check_fresh_fulltrain_cpu",
               "--pattern", args.pattern, "--output", "<new-output>"]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern=args.pattern)
    log = args.output / "unittest.log"
    with log.open("x", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    value = {"schema": "safeshift-fresh-cpu-receipt-v1", "source_commit": head,
        "source_manifest": source_manifest(), "command": command, "python": sys.version,
        "platform": platform.platform(), "dependencies": "stdlib; native opt-ins disabled",
        "randomness": "NONE", "tests_run": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "skipped": [{"test": str(t), "reason": r} for t, r in result.skipped],
        "passed": result.testsRun - len(result.skipped) - len(result.failures) - len(result.errors),
        "seconds": time.monotonic() - began, "status": "PASS" if result.wasSuccessful() else "FAIL",
        "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(), "scope": "CPU_SYNTHETIC_ONLY",
        "gpu_calls": 0, "real_inference": "NOT_RUN", "release": "BLOCKED"}
    (args.output / "receipt.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: value[k] for k in ("status", "tests_run", "passed", "failures", "errors", "seconds", "log_sha256")}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
