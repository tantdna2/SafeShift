"""CPU mock run/audit only. No settings file, input path or model options."""

import argparse
import json
from pathlib import Path

from .audit import audit_run
from .policy import CASES, DEFAULT_CASES, authorize
from .runner import run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "audit"))
    parser.add_argument("--mode", choices=("synthetic",), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--cases", nargs="+", choices=CASES, default=list(DEFAULT_CASES))
    args = parser.parse_args(argv)
    settings = authorize({"mode": args.mode, "run_id": args.run_id,
                          "source_commit": args.source_commit, "cases": args.cases})
    repo = Path(__file__).resolve().parents[2]
    if args.action == "run":
        run(repo, settings)
    result = audit_run(repo, settings)
    print(json.dumps(result["evaluation"], indent=2, allow_nan=False))
    return 0 if result["sealed"] and result["evaluation"]["completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
