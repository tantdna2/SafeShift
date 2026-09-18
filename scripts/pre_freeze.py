"""Offline development entrypoint; no transport and no benchmark outputs."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from safeshift.protocol.firewall import external_path
from safeshift.protocol.gate import GiantBoxReview, evaluate_gate, load_cases
from safeshift.protocol.schema import fields, parse_text, strict_json


def main(argv=None, *, repo=REPO):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate-cases", "replay-dummy-gate"))
    parser.add_argument("--manifest", required=True, help="repository-relative external manifest")
    parser.add_argument("--responses", help="handcrafted JSON responses only; never benchmark outputs")
    args = parser.parse_args(argv)
    try:
        # Check every supplied path before opening any input, even unused options.
        external_path(repo, args.manifest)
        if args.responses:
            external_path(repo, args.responses)
        cases = load_cases(repo, args.manifest)
        if args.command == "validate-cases":
            print(json.dumps({"status": "FORMAT_VALID", "case_count": len(cases), "live_gate": "NOT RUN"}))
            return 0
        if not args.responses:
            raise ValueError("--responses is required for dummy replay")
        payload = strict_json(external_path(repo, args.responses).read_bytes())
        fields(payload, {"source_kind", "predictions", "giant_box_reviews"})
        if payload["source_kind"] != "handcrafted_dummy":
            raise ValueError("only handcrafted dummy responses are permitted")
        if not isinstance(payload["predictions"], dict) or not isinstance(payload["giant_box_reviews"], dict):
            raise ValueError("predictions and reviews must be objects keyed by case ID")
        if any(not isinstance(text, str) for text in payload["predictions"].values()):
            raise ValueError("dummy predictions must be literal, unmodified JSON text strings")
        predictions = {key: parse_text(text, "external_probe") for key, text in payload["predictions"].items()}
        reviews = {}
        for key, row in payload["giant_box_reviews"].items():
            fields(row, {"status", "reviewer", "rationale"})
            reviews[key] = GiantBoxReview(**row)
        result = evaluate_gate(repo, cases, predictions, reviews)
        print(json.dumps({"source_kind": "handcrafted_dummy", "live_gate": "NOT RUN", **asdict(result)}, indent=2))
        return 0 if result.status == "PASS" else 1
    except (ValueError, OSError, TypeError) as exc:
        print(f"PRE_FREEZE_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
