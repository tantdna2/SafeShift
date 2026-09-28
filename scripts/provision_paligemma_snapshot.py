"""Explicit provision OR offline verify-only; never invoked by the smoke process."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.runners.paligemma_snapshot import CACHE, provision_or_verify, write_json
from safeshift.runners.storage import FileRawStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--provision", action="store_true")
    modes.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cache-dir", default=CACHE)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    output = FileRawStore(ROOT, args.manifest).root
    if output.exists():
        parser.error("manifest exists; choose a new path")
    report = provision_or_verify(provision=args.provision, cache_dir=args.cache_dir)
    write_json(output, report)
    print("PINNED_SNAPSHOT_VERIFIED " + args.manifest)


if __name__ == "__main__":
    main()
