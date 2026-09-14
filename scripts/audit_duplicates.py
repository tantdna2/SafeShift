"""Audit exact, pixel and perceptual image overlap without changing InspecSafe-V1."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from safeshift.data.manifest import ManifestError  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=Path("data/raw/InspecSafe-V1"))
    parser.add_argument("--output", type=Path, default=Path("data/manifests/duplicate_leakage_audit.json"))
    parser.add_argument("--max-hamming", type=int, default=8)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 1
    try:
        from safeshift.data.duplicates import audit_duplicates, checked_output, write_report
        output = checked_output(args.output, args.dataset_root, REPO_ROOT)
        started = time.perf_counter()
        report = audit_duplicates(args.dataset_root, REPO_ROOT, max_hamming=args.max_hamming,
                                  progress=lambda message: print(message, file=sys.stderr, flush=True))
        elapsed = time.perf_counter() - started
        write_report(report, output, REPO_ROOT, runtime_seconds=elapsed)
        print(json.dumps(report["summary"], indent=2, ensure_ascii=True))
        print(f"Input fingerprint: {report['input_sha256']}")
        print(f"Audit runtime: {elapsed:.3f} seconds (excludes JSON publication)")
        print(f"Report: {output.relative_to(REPO_ROOT).as_posix()}")
        print("Audit complete: True; exit code: 0")
        return 0
    except ImportError:
        print("ERROR: install requirements-validation.txt; audit incomplete", file=sys.stderr)
        return 1
    except (ManifestError, OSError, ValueError, SyntaxError, RecursionError) as exc:
        # Never echo decoder/OS messages that can contain absolute machine paths or input metadata.
        print(f"ERROR: {type(exc).__name__}; audit incomplete; previous output, if any, is stale", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
