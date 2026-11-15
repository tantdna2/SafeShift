"""Offline packaging and gated read-only collection for MiniCPM Owner UI."""
import argparse
from pathlib import Path

from safeshift.candidates.source import ROOT
from safeshift.fulltrain import minicpm_ui as ui
from safeshift.pilot.artifacts import read, write
from scripts.generate_minicpm_fulltrain_notebook import notebook


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    plan = sub.add_parser("plan", help="CPU initial metadata from a previously sealed TRAIN projection; no image reads")
    for name in ("cohort", "resource-policy", "output"):
        plan.add_argument("--" + name, type=Path, required=True)
    for name in ("projection-sha256", "checkpoint-marker-sha256", "run-id", "attempt-id", "job", "capsule-ref"):
        plan.add_argument("--" + name, required=True)
    for name in ("max-calls", "max-seconds"):
        plan.add_argument("--" + name, required=True, type=int)
    plan.add_argument("--mount-layout", choices=("direct", "nested"), required=True)
    prepare = sub.add_parser("prepare", help="CPU metadata/history candidate; no upload or execution")
    prepare.add_argument("--spec", type=Path, required=True)
    prepare.add_argument("--ancestor", type=Path, action="append", default=[])
    prepare.add_argument("--runtime-ref", required=True)
    prepare.add_argument("--output", type=Path, required=True)
    collect = sub.add_parser("collect", help="Fenced; requires future reviewed activation before all I/O")
    collect.add_argument("--package", type=Path, required=True)
    collect.add_argument("--attempt", type=Path, required=True)
    collect.add_argument("--supervisor", type=Path, required=True)
    collect.add_argument("--output", type=Path, required=True)
    next_run = sub.add_parser("next", help="Prepare a resume spec from verified metadata; never submit")
    for name in ("spec", "verification", "output"):
        next_run.add_argument("--" + name, type=Path, required=True)
    for name in ("run-id", "attempt-id", "job", "capsule-ref"):
        next_run.add_argument("--" + name, required=True)
    for name in ("max-calls", "max-seconds"):
        next_run.add_argument("--" + name, required=True, type=int)
    args = p.parse_args()
    if args.action == "plan":
        result = ui.initial(read(args.cohort), args.projection_sha256, read(args.resource_policy),
            checkpoint_marker_sha256=args.checkpoint_marker_sha256, run_id=args.run_id, attempt_id=args.attempt_id,
            job=args.job, capsule_ref=args.capsule_ref, max_calls=args.max_calls, max_seconds=args.max_seconds,
            nested_mounts=args.mount_layout == "nested")
        write(args.output, result)
        print("INITIAL_CANDIDATE; evidence references remain missing until independently verified")
    elif args.action == "prepare":
        result = ui.package(read(args.spec), args.ancestor, args.output,
            lambda pin: notebook(args.runtime_ref, ROOT, capsule_sha256=pin))
        print(str(result) + ": CANDIDATE_RELEASE_BLOCKED; native calls=0; upload=0")
    elif args.action == "collect":
        print(ui.collect(args.package, args.attempt, args.supervisor, args.output)["status"])
    else:
        result = ui.next_capsule(read(args.spec), read(args.verification), run_id=args.run_id,
            attempt_id=args.attempt_id, job=args.job, capsule_ref=args.capsule_ref,
            max_calls=args.max_calls, max_seconds=args.max_seconds)
        write(args.output, result)
        print("RESUME_CANDIDATE; reverify complete ancestors, caps, rights and release before handoff")


if __name__ == "__main__":
    main()
