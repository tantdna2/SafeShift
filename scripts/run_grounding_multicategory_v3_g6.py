"""G6 PaliGemma-only synthetic v3 PREP/observation CLI."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.protocol.firewall import external_path
from safeshift.runners import grounding_multicategory_v3_g6 as runtime


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=runtime.MODELS, required=True)
    parser.add_argument("--run-id", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--inspect-environment", action="store_true",
                      help="Future venue inventory; no model load, does inspect GPUs")
    mode.add_argument("--finalize", action="store_true")
    parser.add_argument("--environment")
    parser.add_argument("--authorization")
    parser.add_argument("--snapshot")
    parser.add_argument("--reviews")
    parser.add_argument("--output", help="New environment inventory JSON under data/processed/")
    args = parser.parse_args(argv)
    try:
        load = lambda path: runtime.read_json(external_path(ROOT, path)) if path else None
        if args.inspect_environment:
            runtime.require(args.run_id == runtime.RUN_IDS[args.model], "PREDECLARED_RUN_ID_REQUIRED")
            runtime.require(args.snapshot and args.output and args.output.startswith("data/processed/"),
                            "SNAPSHOT_AND_OUTPUT_REQUIRED")
            value = runtime.inspect_environment(ROOT, args.model, args.snapshot)
            target = external_path(ROOT, args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            receipt = runtime.write_bytes(target, runtime.encode(value))
            runtime.verified_read(target, receipt)
            value = {"environment_sha256": runtime.sha(runtime.encode(value)),
                     "execution_authorized": False, "QUALIFICATION_EXECUTION": "NOT_RUN"}
        elif args.finalize:
            runtime.require(args.reviews, "HUMAN_REVIEWS_REQUIRED")
            value = runtime.finalize(ROOT, args.model, args.run_id, load(args.reviews))
        elif args.execute:
            value = runtime.execute(ROOT, args.model, args.run_id, load(args.environment), load(args.authorization),
                                    ["python", "scripts/run_grounding_multicategory_v3_g6.py",
                                     *(argv if argv is not None else sys.argv[1:])])
        else:
            value = runtime.preflight(ROOT, args.model, args.run_id, load(args.environment), load(args.authorization))
        print(json.dumps(value, indent=2))
        return 0 if value.get("status") != "BLOCKED" and value.get("final_verdict") not in ("BLOCKED", "FAIL") else 2
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "error_type": type(exc).__name__, "reason": str(exc),
                          "QUALIFICATION_EXECUTION": "UNKNOWN_INSPECT_ARTIFACTS" if args.execute else "NOT_RUN",
                          "execution_authorized": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
