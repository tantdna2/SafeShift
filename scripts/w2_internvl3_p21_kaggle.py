"""Owner source prep/offline one-shot driver; no runtime setup on import."""

import argparse
from pathlib import Path

from safeshift.protocol.schema import strict_json
from safeshift.runners.p21_kaggle import prepare_source, run_offline


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    prep = actions.add_parser("source-prep")
    prep.add_argument("--repo", type=Path, required=True)
    prep.add_argument("--confirmation", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    run = actions.add_parser("offline-shard0")
    run.add_argument("--repo", type=Path, required=True)
    run.add_argument("--inputs", type=Path, required=True)
    run.add_argument("--settings", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.action == "source-prep":
        prepare_source(args.repo, strict_json(args.confirmation.read_bytes()), args.output)
        return 0
    summary = run_offline(args.repo, args.inputs, strict_json(args.settings.read_bytes()), args.output)
    return 0 if summary["execution_status"] == "COMPLETED" and not summary["stop_before_shards_1_3"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
