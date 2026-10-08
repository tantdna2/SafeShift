"""Thin owner entrypoint; metadata preflight never initializes a model."""

import argparse
import json
from pathlib import Path

from safeshift.protocol.classification_policy import ROOT, MODELS
from .p2_preflight import static_preflight
from .p2_harness import production_run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--repo", type=Path, default=ROOT)
    run = sub.add_parser("run")
    run.add_argument("--repo", type=Path, default=ROOT)
    run.add_argument("--model", choices=MODELS, required=True)
    for name in ("run-id", "dataset-root", "manifest-path", "provenance-path"):
        run.add_argument("--" + name, required=True)
    run.add_argument("--shard-count", type=int, default=1)
    run.add_argument("--shard-index", type=int, default=0)
    args = vars(parser.parse_args(argv))
    action = args.pop("action")
    if action == "preflight":
        try:
            result = static_preflight(**args)
        except (PermissionError, ValueError) as exc:
            print("FINAL_MERGE_REQUIRED: " + str(exc))
            return 2
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result.get("effective_authorization") else 2
    try:
        if args["model"] == "qwen3":
            from .qwen3_placement import configure_allocator
            configure_allocator()
        result = production_run(**args)
    except PermissionError as exc:
        print("PROTOCOL_FREEZE_REQUIRED: " + str(exc))
        return 2
    except ValueError as exc:
        print("P2_RUNTIME_PREFLIGHT_FAILED: " + str(exc))
        return 2
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
