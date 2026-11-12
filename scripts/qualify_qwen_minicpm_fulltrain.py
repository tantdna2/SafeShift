"""Focused, offline CPU qualification. No model/image inference or provider use."""
import argparse
import importlib.metadata
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

from safeshift.candidates.source import ROOT
from safeshift.fulltrain import contract
from safeshift.pilot.artifacts import sha, write
from safeshift.pilot.contract import digest

SUITES = ["test_fulltrain", "test_fresh_fulltrain", "test_fresh_fulltrain_revision",
          "test_kaggle173_verification", "test_fulltrain_minicpm4_notebook"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--native-snapshot", type=Path)
    p.add_argument("--native-index", type=Path)
    args = p.parse_args()
    if bool(args.native_snapshot) != bool(args.native_index): p.error("both native source snapshot and index required")
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ.update(CUDA_VISIBLE_DEVICES="", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                      HF_HUB_DISABLE_TELEMETRY="1", PYTHONDONTWRITEBYTECODE="1")
    sys.path.insert(0, str(ROOT / "tests"))
    names = list(SUITES)
    versions = {}
    if args.native_snapshot:
        os.environ.update(SAFESHIFT_CANDIDATE_KEY="minicpm4", SAFESHIFT_CANDIDATE_SNAPSHOT=str(args.native_snapshot),
                          SAFESHIFT_CANDIDATE_INDEX=str(args.native_index), SAFESHIFT_NUMERICS_SNAPSHOT=str(args.native_snapshot))
        names += ["test_candidate_native.NativeCandidateTests", "test_minicpm_resampler_fp32.NativeResamplerTests"]
        versions = {n: importlib.metadata.version(n) for n in ("torch", "torchvision", "transformers", "tokenizers", "numpy", "Pillow")}
    network_attempts = []
    def blocked(*a, **kw):
        network_attempts.append("NETWORK_FORBIDDEN")
        raise AssertionError("NETWORK_FORBIDDEN")
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    with (args.output / "tests.log").open("x", encoding="utf8") as log, \
         patch.object(socket.socket, "connect", blocked), patch.object(socket, "create_connection", blocked):
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
    files = set(contract.sources()) | {"notebooks/SafeShift_FULLTRAIN_MINICPM4_FP32.ipynb",
        "scripts/generate_minicpm_fulltrain_notebook.py", "scripts/qualify_qwen_minicpm_fulltrain.py"}
    files |= {"tests/" + n.split(".")[0] + ".py" for n in names}
    receipt = {"scope": "CPU_SYNTHETIC_ONLY", "status": "PASS" if result.wasSuccessful() and not network_attempts else "FAIL",
        "tests": result.testsRun, "passed": passed, "failures": len(result.failures), "errors": len(result.errors),
        "skips": len(result.skipped), "skip_reasons": [reason for _, reason in result.skipped],
        "suites": names, "python": sys.version, "platform": platform.platform(), "dependencies": versions,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "tracked_dirty": bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT)),
        "source_sha256": digest(contract.source_manifest()),
        "file_sha256": {n: sha(ROOT / n) for n in sorted(files)}, "log_sha256": sha(args.output / "tests.log"),
        "network_attempts": len(network_attempts), "kaggle_submissions": 0, "gpu_used": False,
        "real_model_inference_calls": 0, "real_image_reads": 0, "production_ledger_writes": 0,
        "final_source_live_verification": "NOT_RUN", "independent_audit": "NOT_PERFORMED",
        "scientific_qualified": False, "seed": None}
    write(args.output / "receipt.json", receipt)
    print({k: receipt[k] for k in ("status", "tests", "passed", "failures", "errors", "skips")})
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
