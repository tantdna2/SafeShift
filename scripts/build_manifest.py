"""Build the audited InspecSafe-V1 CSV from repository-relative paths."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from safeshift.data.manifest import (  # noqa: E402
    ManifestError, collect_manifest, repository_path, write_manifest, write_provenance,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=Path("data/raw/InspecSafe-V1"))
    parser.add_argument("--output", type=Path, default=Path("data/manifests/dataset_manifest.csv"))
    args = parser.parse_args(argv)
    try:
        dataset_root = repository_path(args.dataset_root, REPO_ROOT)
        output = repository_path(args.output, REPO_ROOT)
        if output.is_relative_to(dataset_root) or output.is_relative_to(REPO_ROOT / "data/raw"):
            raise ManifestError("output must not be inside the raw dataset")
        if output.suffix != ".csv":
            raise ManifestError("output must have a .csv suffix")
        result = collect_manifest(dataset_root, REPO_ROOT)
        print(json.dumps(result.summary(), indent=2))
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        for discrepancy in result.discrepancies():
            print(f"W1 DISCREPANCY: {discrepancy}", file=sys.stderr)
        if result.errors:
            print("ERROR: validation failed; manifest not written", file=sys.stderr)
            return 1
        write_manifest(result, output)
        write_provenance(result, dataset_root, output, REPO_ROOT)
        print(f"Manifest written: {output.relative_to(REPO_ROOT).as_posix()}")
        return 2 if result.discrepancies() else 0
    except (ManifestError, OSError) as exc:
        reason = exc.strerror if isinstance(exc, OSError) else str(exc)
        print(f"ERROR: {reason}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
