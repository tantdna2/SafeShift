"""Pinned CPU acceptance, PUBLIC source/tokenizer + synthetic fixtures, no inference.

Use an isolated Phi venv with the unchanged requirements. The snapshot directory
must contain all hash-locked public text/tokenizer files; no checkpoint required.
Receipts and explicitly synthetic ZIPs stay under data/processed, outside Git.
"""
import argparse
import os
from pathlib import Path
import platform
import sys
import unittest

from safeshift.pilot.artifacts import sha, write
from safeshift.pilot.contract import MODELS, digest, source_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--live-source-probe", action="store_true",
                        help="Also run the production public Hub metadata/source-only CPU admission; never weights")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = Path(args.output).resolve()
    if not output.is_relative_to((repo / "data/processed").resolve()):
        raise ValueError("REHEARSAL_OUTPUT_UNDER_DATA_PROCESSED_REQUIRED")
    output.mkdir(parents=True, exist_ok=False)
    source_before = source_digest(repo)
    test_before = sha(repo / "tests/test_phi_native.py")
    test_inventory = {p.name: sha(p) for p in sorted((repo / "tests").glob("test_*.py"))}
    script_before = sha(Path(__file__))
    # Some fault tests mock subprocess observations used by platform's cache.
    # Capture actual host identity before running those tests.
    actual_platform = platform.platform()
    os.environ.update(SAFESHIFT_PHI_SNAPSHOT=str(Path(args.snapshot).resolve()),
                      SAFESHIFT_PHI_REHEARSAL_ARTIFACTS=str(output / "artifacts"),
                      CUDA_VISIBLE_DEVICES="", HF_MODULES_CACHE=str(output / "modules"))
    sys.path.insert(0, str(repo / "tests"))
    from test_phi_native import NativePhiTests
    suite = unittest.defaultTestLoader.discover(str(repo / "tests"))
    with (output / "tests.log").open("x", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    live = None
    if args.live_source_probe:
        from contextlib import ExitStack
        from unittest.mock import patch
        import torch
        from safeshift.pilot.backend import cpu_software_probe
        from safeshift.pilot.diagnostics import failure_detail
        os.environ["SAFESHIFT_CPU_DIAGNOSTICS"] = str(output / "live_cpu")
        try:
            with ExitStack() as guards:
                for name in ("init", "_lazy_init", "is_available", "device_count", "get_device_capability"):
                    guards.enter_context(patch.object(torch.cuda, name, side_effect=AssertionError("REAL_CUDA_FORBIDDEN")))
                live = cpu_software_probe(repo, "phi")
        except BaseException as error:
            live = {"status": "FAIL", "error": failure_detail(error, "cpu_admission", "live_source_probe")}
    unchanged = (source_before == source_digest(repo) and test_before == sha(repo / "tests/test_phi_native.py")
                 and script_before == sha(Path(__file__))
                 and test_inventory == {p.name: sha(p) for p in sorted((repo / "tests").glob("test_*.py"))})
    qualified = result.wasSuccessful() and unchanged and (not args.live_source_probe or live.get("status") != "FAIL")
    receipt = {"schema": "safeshift-phi-cpu-acceptance-v1", "status": "PASS" if qualified else "FAIL",
               "source_test_script_unchanged_during_run": unchanged,
               "base_commit": args.base_commit, "source_sha256": source_digest(repo),
               "model_revision": MODELS["phi"]["revision"], "python": sys.version,
               "platform": actual_platform, "tests_run": result.testsRun,
               "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
               "test_source_sha256": sha(repo / "tests/test_phi_native.py"),
               "test_inventory_sha256": digest(test_inventory),
               "script_sha256": sha(Path(__file__)), "log_sha256": sha(output / "tests.log"),
               "cuda": "GUARDED_NOT_CALLED", "model_forward": "NOT_RUN",
               "checkpoint_weights": "NOT_DOWNLOADED_OR_LOADED", "kaggle_gpu": "UNVERIFIED",
               "live_source_cpu_probe": live,
               "evidence": getattr(NativePhiTests, "evidence", {})}
    write(output / "receipt.json", receipt)
    write(output / "receipt.sha256.json", {"sha256": sha(output / "receipt.json")})
    print(receipt["status"], "tests", result.testsRun, "failures", len(result.failures), "errors", len(result.errors))
    if not qualified:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
