"""Reproducible CPU-only receipt for TRAIN3763 and durable operations."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest
from safeshift import internvl3763 as runtime
from safeshift.pilot.artifacts import sha, write


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--native", action="store_true")
    p.add_argument("--packages", type=Path, action="append", default=[])
    a = p.parse_args(argv)
    a.output.mkdir(parents=True, exist_ok=False)
    os.environ.update(CUDA_VISIBLE_DEVICES="", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    for path in a.packages:
        sys.path.insert(0, str(path.resolve()))
    sys.path.insert(0, str(runtime.ROOT / "tests"))
    os.environ["SAFESHIFT3763_NATIVE_CPU"] = "1" if a.native else "0"
    dependencies = {}
    if a.native:
        dependencies = {name: importlib.metadata.version(name) for name in
            ("torch", "torchvision", "transformers", "tokenizers", "numpy", "Pillow")}
    names = ["test_internvl3763", "test_internvl3763_execution", "test_internvl3763_campaign", "test_internvl3763_capsule", "test_internvl3763_versions", "test_internvl3763_e2e", "test_internvl3763_python", "test_kaggle_handoff", "test_fulltrain", "test_internvl_grammar", "test_kaggle173_verification"]
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    with (a.output / "tests.log").open("x", encoding="utf8") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    receipt = {"schema": runtime.IDENTITY + "-cpu-receipt", "status": "PASS" if result.wasSuccessful() else "FAIL",
        "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skips": len(result.skipped), "test_suites": names,
        "skip_reasons": [reason for _, reason in result.skipped],
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=runtime.ROOT, text=True).strip(),
        "tracked_dirty": bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=runtime.ROOT)),
        "source": runtime.source_spec(), "python": sys.version, "platform": platform.platform(),
        "dependencies": dependencies, "log_sha256": sha(a.output / "tests.log"),
        "tests_sha256": {name: sha(runtime.ROOT / name) for name in
            ("tests/test_internvl3763.py", "tests/test_internvl3763_execution.py", "tests/test_internvl3763_campaign.py",
             "tests/test_internvl3763_capsule.py", "tests/test_internvl3763_versions.py", "tests/test_internvl3763_e2e.py",
             "tests/test_internvl3763_python.py",
             "tests/test_internvl3763_notebook.py", "tests/test_kaggle_handoff.py", "scripts/qualify_internvl3763.py")},
        "seed": None, "randomness": "NONE", "scope": "CPU_SYNTHETIC_ONLY",
        "command": ["python", "-B", "-m", "scripts.qualify_internvl3763", "--output", "<new-output>"]
            + (["--native", "--packages", "<local-pinned-public-software>"] if a.native else []),
        "kaggle_submissions": 0, "real_model_inference_calls": 0, "real_image_reads": 0,
        "final_source_live_verification": "NOT_RUN", "scientific_qualified": False,
        "independent_audit": "NOT_PERFORMED"}
    write(a.output / "receipt.json", receipt)
    print(json.dumps({k: receipt[k] for k in ("status", "tests", "failures", "errors", "skips")}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
