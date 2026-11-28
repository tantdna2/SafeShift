"""CPU-only package preparation and replay for the CT1 evidence pilot."""

from argparse import ArgumentParser
import csv
import io
from pathlib import Path

from safeshift.data.saved_reports import checked, json_bytes, sha256, strict_json
from safeshift.evaluation.ct1_contract import ARMS, SCHEMA, SCHEMA_ID, prompt
from safeshift.evaluation.ct1_pilot import (
    EXCLUSIONS_SHA256, MODEL_ID, REVISION, blind_packet, replay, score, validate_plan,
)


def write_new(path, data):
    with path.open("xb") as stream:
        stream.write(data)


def prepare(output, with_control):
    arms = ARMS if with_control else ARMS[:2]
    members = {f"prompt-{arm}.txt": prompt(arm) for arm in arms}
    members["evidence.schema.json"] = json_bytes(SCHEMA)
    receipt = {
        "status": "CPU_PREP_ONLY", "native_release": "BLOCKED_PENDING_AUTHORIZED_SOURCE",
        "model_id": MODEL_ID, "revision": REVISION, "arms": arms, "schema": SCHEMA_ID,
        "files_sha256": {name: sha256(payload) for name, payload in members.items()},
    }
    output.mkdir(exist_ok=False)
    for name, payload in members.items():
        write_new(output / name, payload)
    write_new(output / "receipt.json", json_bytes(receipt))
    return receipt


def make_exclusions(key_path, lock_path, output):
    """Export only exact-content exclusions from the two preserved audit artifacts."""
    lock = strict_json(lock_path.read_bytes())
    if lock.get("phase") != "BLIND_LOCKED_BEFORE_JOIN":
        raise ValueError("invalid blind lock")
    selected = list(csv.DictReader(io.StringIO(key_path.read_bytes().decode("utf-8-sig"))))
    hashes = sorted({row["image_sha256"] for row in selected} | set(lock["image_sha256"].values()))
    data = checked(json_bytes(hashes), EXCLUSIONS_SHA256)
    write_new(output, data)


def read_json(path):
    return strict_json(path.read_bytes())


def run_replay(args):
    plan_bytes = args.plan.read_bytes()
    run_bytes = args.runs.read_bytes()
    plan_sha, runs_sha = sha256(plan_bytes), sha256(run_bytes)
    plan = strict_json(plan_bytes)
    exclusions = read_json(args.exclusions) if args.exclusions else None
    decoded = replay(plan, strict_json(run_bytes), plan_sha, exclusions)
    packet, review_tokens = (None, None)
    if args.command == "blind" or args.reviews:
        if not args.review_key:
            raise ValueError("review key is required to bind the blind packet")
        packet, review_tokens = blind_packet(decoded, args.review_key.read_bytes(), plan_sha, runs_sha)
    if args.command == "blind":
        return packet

    truth_bytes = args.truth.read_bytes()
    review_bytes = args.reviews.read_bytes() if args.reviews else None
    result = score(plan, decoded, strict_json(truth_bytes), plan_sha,
                   reviews=strict_json(review_bytes) if review_bytes is not None else None,
                   packet=packet, token_to_case=review_tokens)
    result["input_sha256"] = {
        "plan": plan_sha, "runs": runs_sha, "truth": sha256(truth_bytes),
        "review": None if review_bytes is None else sha256(review_bytes),
    }
    return result


def main(argv=None):
    parser = ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare", help="export exact prompts, schema and CPU preparation receipt")
    prep.add_argument("--with-control", action="store_true")
    exclude = commands.add_parser("exclusions", help="build the exact audit exclusion list on CPU")
    exclude.add_argument("--audit-key", type=Path, required=True)
    exclude.add_argument("--blind-lock", type=Path, required=True)
    validation = commands.add_parser("validate-plan", help="check structure and exact-content exclusions")
    validation.add_argument("--plan", type=Path, required=True)
    validation.add_argument("--exclusions", type=Path)
    blind = commands.add_parser("blind", help="produce review packet without reading GT")
    scoring = commands.add_parser("score", help="score raw runs and optional adjudicated review offline")
    scoring.add_argument("--truth", type=Path, required=True)
    scoring.add_argument("--reviews", type=Path)
    for command in (blind, scoring):
        command.add_argument("--plan", type=Path, required=True)
        command.add_argument("--runs", type=Path, required=True)
        command.add_argument("--exclusions", type=Path)
        command.add_argument("--review-key", type=Path)
    for command in (prep, exclude, validation, blind, scoring):
        command.add_argument("--output", type=Path, required=True, help="fresh file or directory")
    args = parser.parse_args(argv)
    if args.command == "prepare":
        prepare(args.output, args.with_control)
    elif args.command == "exclusions":
        make_exclusions(args.audit_key, args.blind_lock, args.output)
    elif args.command == "validate-plan":
        raw = args.plan.read_bytes()
        plan = strict_json(raw)
        ids = validate_plan(plan, read_json(args.exclusions) if args.exclusions else None)
        write_new(args.output, json_bytes({"scope": plan["kind"], "planned_n": len(ids),
                                          "plan_sha256": sha256(raw), "status": "CPU_PLAN_VALIDATED"}))
    else:
        write_new(args.output, json_bytes(run_replay(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())