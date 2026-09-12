"""Validate InspecSafe-V1 triplet quality without modifying or excluding samples."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from safeshift.data.manifest import ManifestError, repository_path  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=Path("data/raw/InspecSafe-V1"))
    parser.add_argument("--output", type=Path, default=Path("data/manifests/dataset_validation.json"))
    parser.add_argument("--verify-image-data", action="store_true",
                        help="strict Base64 decode and SHA-256 comparison with each external image")
    args = parser.parse_args(argv)
    try:
        from safeshift.data.validation import validate_dataset, write_report
        dataset = repository_path(args.dataset_root, REPO_ROOT)
        output = repository_path(args.output, REPO_ROOT)
        if output.is_relative_to(dataset) or output.is_relative_to((REPO_ROOT / "data/raw").resolve()):
            raise ManifestError("output must not be inside the raw dataset")
        if output.suffix != ".json":
            raise ManifestError("output must have a .json suffix")
        report = validate_dataset(dataset, REPO_ROOT, verify_image_data=args.verify_image_data)
        write_report(report, output, REPO_ROOT)
        print(json.dumps(report["summary"], indent=2, ensure_ascii=True))
        print(f"ERROR issues: {report['errors_count']}; WARNING issues: {report['warnings_count']}")
        for key in ("regression_discrepancies", "schema_discrepancies"):
            for discrepancy in report[key]:
                print(f"RESEARCH LEAD DISCREPANCY ({key}): {discrepancy}", file=sys.stderr)
        print(f"Report: {output.relative_to(REPO_ROOT).as_posix()}")
        print(f"Audit complete: {report['audit_complete']}; exit code: {report['exit_code']}")
        return report["exit_code"]
    except ImportError:
        print("ERROR: install validation dependencies with python -m pip install -r requirements-validation.txt",
              file=sys.stderr)
        return 1
    except (ManifestError, OSError) as exc:
        reason = exc.strerror if isinstance(exc, OSError) else str(exc)
        print(f"ERROR: {reason}; audit did not complete, any previous output is stale", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
