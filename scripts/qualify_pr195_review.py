"""CPU-only F1/F2 review validation, with one independent receipt per suite."""
import argparse
import importlib.metadata
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from safeshift.candidates.source import ROOT
from safeshift.fulltrain import contract
from safeshift.pilot.artifacts import sha, write
from safeshift.pilot.contract import digest

GROUPS = {
    "notebooks": ["test_fresh_fulltrain_notebooks", "test_fulltrain_notebooks", "test_fulltrain_minicpm4_notebook"],
    "core": ["test_fulltrain", "test_fresh_fulltrain", "test_fresh_fulltrain_revision",
             "test_fulltrain_original_inputs", "test_minicpm_fulltrain_ui"],
    "operator": ["test_minicpm_ui_transport", "test_train3763_manual", "test_internvl3763_python"],
    "main": ["test_qwen_composite", "test_train3763_continuation", "test_train3763_results"],
    "linux": ["test_fresh_fulltrain_revision.SupervisionTests",
              "test_internvl3763_python.PythonInputTests.test_current_mount_layout_wrong_owner_and_symlink_alias"],
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--group", choices=GROUPS, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ.update(CUDA_VISIBLE_DEVICES="", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1", PYTHONDONTWRITEBYTECODE="1")
    sys.path.insert(0, str(ROOT / "tests"))
    files = set(contract.sources()) | {"scripts/locked_fulltrain_notebooks.py", "scripts/build_fresh_fulltrain_notebooks.py",
        "scripts/qualify_pr195_review.py", "tests/frozen_internvl_snapshot.py"}
    files |= {"tests/" + n.split('.')[0] + ".py" for n in GROUPS[args.group]}
    before = {name: sha(ROOT / name) for name in sorted(files)}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dependencies = {}
    if args.group == "operator":
        dependencies = {n: importlib.metadata.version(n) for n in ("kaggle", "kagglesdk", "requests", "urllib3")}
    failures = False
    for i, name in enumerate(GROUPS[args.group]):
        output = args.output / f"{i+1:02d}-{name.split('.')[0]}"
        output.mkdir()
        attempts = []
        def blocked(*a, **kw):
            attempts.append("NETWORK_FORBIDDEN")
            raise AssertionError("NETWORK_FORBIDDEN")
        started = time.monotonic()
        with patch.object(socket.socket, "connect", blocked), patch.object(socket, "create_connection", blocked):
            suite = unittest.defaultTestLoader.loadTestsFromName(name)
            with (output / "tests.log").open("x", encoding="utf8") as log:
                result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        receipt = {"suite": name, "group": args.group, "status": "PASS" if result.wasSuccessful() and not attempts else "FAIL",
            "tests": result.testsRun, "passed": result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
            "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped),
            "skip_reasons": [reason for _, reason in result.skipped], "seconds": time.monotonic()-started,
            "tested_commit": head, "main": "89088dbc57d629933ab1462171019cd0125c2869",
            "python": sys.version, "platform": platform.platform(), "dependencies": dependencies,
            "source_sha256": digest(contract.source_manifest()), "file_sha256": before,
            "log_sha256": sha(output / "tests.log"), "network_attempts": len(attempts),
            "scope": "CPU_SYNTHETIC_ONLY", "gpu_used": False, "real_model_inference_calls": 0,
            "private_image_reads": 0, "production_ledger_writes": 0, "live_verification": "NOT_RUN"}
        after = {n: sha(ROOT / n) for n in before}
        receipt["tested_files_unchanged"] = before == after
        receipt["head_unchanged"] = head == subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        if not receipt["tested_files_unchanged"] or not receipt["head_unchanged"]:
            receipt["status"] = "FAIL"
        write(output / "receipt.json", receipt)
        print({k:receipt[k] for k in ("suite", "status", "tests", "passed", "failures", "errors", "skips")}, flush=True)
        failures |= receipt["status"] != "PASS"
    return int(failures)


if __name__ == "__main__":
    raise SystemExit(main())
