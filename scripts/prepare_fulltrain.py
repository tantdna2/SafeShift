"""Prepare Issue167 synthetic plans and blocked release receipts; no inference."""
import argparse
from pathlib import Path
import platform
import subprocess
import sys

from safeshift.candidates.fulltrain import MODELS, plan, release_report, same_cohort
from safeshift.candidates.fulltrain_run import synthetic_cohort
from safeshift.pilot.artifacts import export, write
from safeshift.pilot.contract import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-calls", type=int, required=True, help="Synthetic scheduling cap, not an O5 decision")
    parser.add_argument("--max-seconds", type=int, required=True, help="Synthetic scheduling cap, not a real run grant")
    args = parser.parse_args()
    cohort = synthetic_cohort()
    plans = {key: plan(cohort, digest(cohort), {"model_key": key, "model_id": "synthetic/" + key,
        "model_revision": "a"*40, "hnlo_policy": "LABEL_ONLY",
        **{n: "a"*64 for n in ("implementation_sha256", "configuration_sha256", "prompt_sha256", "parser_sha256",
                               "generation_sha256", "preprocessing_sha256", "checkpoint_sha256", "runtime_sha256")}},
        [], digest([]), action="initial", series_id="synthetic-series", run_id="synthetic-" + key,
        attempt_id="synthetic-" + key + "-attempt", max_calls=args.max_calls, max_seconds=args.max_seconds) for key in MODELS}
    same_cohort({key: cohort for key in MODELS})
    args.output.mkdir(parents=True, exist_ok=False)
    write(args.output / "cohort.json", cohort)
    for key in MODELS:
        write(args.output / (key + "-plan.json"), plans[key])
        write(args.output / (key + "-release.json"), release_report(key))
    write(args.output / "receipt.json", {"scope": "SYNTHETIC_ONLY_NOT_RESEARCH_RESULT", "model_calls": 0,
        "planned_ids_per_candidate": 3763, "scientific_selection": "PENDING", "pooling_allowed": False,
        "python": sys.version, "platform": platform.platform(), "dependencies": "stdlib", "randomness": "NONE",
        "command": ["python", "-B", "-m", "scripts.prepare_fulltrain", "--output", args.output.as_posix(),
                    "--max-calls", str(args.max_calls), "--max-seconds", str(args.max_seconds)],
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()})
    checksum = export(args.output, Path(str(args.output) + ".zip"))
    print("SYNTHETIC PLAN ONLY; real execution BLOCKED; archive SHA256=" + checksum)


if __name__ == "__main__":
    main()
