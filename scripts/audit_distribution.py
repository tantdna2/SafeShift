"""Audit distribution and imbalance without changing InspecSafe-V1."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from safeshift.data.distribution import (  # noqa: E402
    audit_distribution, checked_output, cli_summary, write_report,
)
from safeshift.data.manifest import ManifestError  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=Path("data/raw/InspecSafe-V1"))
    parser.add_argument("--output", type=Path, default=Path("data/manifests/distribution_imbalance_audit.json"))
    args = parser.parse_args(argv)
    try:
        output = checked_output(args.output, args.dataset_root, REPO_ROOT)
        started = time.perf_counter()
        report = audit_distribution(args.dataset_root, REPO_ROOT,
                                    progress=lambda message: print(message, file=sys.stderr, flush=True))
        write_report(report, output, args.dataset_root, REPO_ROOT,
                     runtime_seconds=time.perf_counter() - started)
        print(json.dumps(cli_summary(report), indent=2, ensure_ascii=True))
        print(f"Input fingerprint: {report['input_sha256']}")
        print(f"Report: {output.relative_to(REPO_ROOT).as_posix()}")
        print(f"Audit complete: True; exit code: {report['exit_code']}")
        return report["exit_code"]
    except ImportError:
        print("ERROR: install requirements-validation.txt; audit incomplete", file=sys.stderr)
        return 1
    except (ManifestError, OSError, ValueError, SyntaxError, RecursionError) as exc:
        print(f"ERROR: {type(exc).__name__}; audit incomplete; previous output, if any, is stale",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
