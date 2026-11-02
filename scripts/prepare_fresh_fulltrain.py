"""Export the 3 x 3763 synthetic initial plans, never data or predictions."""
import argparse
from pathlib import Path
import platform
import subprocess
import sys

from safeshift.fulltrain import contract
from safeshift.candidates.fulltrain_run import synthetic_cohort
from safeshift.candidates.source import ROOT
from safeshift.pilot.artifacts import write, export
from safeshift.pilot.contract import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-calls", type=int, required=True, help="Synthetic test parameter, NOT O5 approval")
    parser.add_argument("--max-seconds", type=int, required=True, help="Synthetic test parameter, NOT O5 approval")
    args = parser.parse_args()
    cohort = synthetic_cohort()
    campaign = contract.campaign({k: cohort for k in contract.planning.MODELS}, digest(cohort))
    plans = {}
    for key in contract.planning.MODELS:
        spec = {"model_key": key, "model_id": "synthetic/" + key, "hnlo_policy": "LABEL_ONLY",
                **{n: "a" * (40 if n == "model_revision" else 64) for n in contract.planning.IDENTITY_FIELDS}}
        plans[key] = contract.plan(campaign, cohort, spec, [], action="initial",
            run_id="synthetic-" + key, attempt_id="synthetic-" + key + "-attempt",
            max_calls=args.max_calls, max_seconds=args.max_seconds)
    args.output.mkdir(parents=True, exist_ok=False)
    write(args.output / "campaign.json", campaign)
    write(args.output / "cohort.json", cohort)
    for key, p in plans.items():
        write(args.output / (key + "-plan.json"), p)
        write(args.output / (key + "-release.json"), contract.release_report(key))
    write(args.output / "receipt.json", {"scope": "CPU_SYNTHETIC_ONLY_NOT_RESEARCH_RESULT",
        "model_calls": 0, "planned_initial_calls": 11289, "history_imports": 0,
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_manifest": contract.source_manifest(), "python": sys.version, "platform": platform.platform(),
        "dependencies": "stdlib", "randomness": "NONE", "command": ["python", "-B", "-m", "scripts.prepare_fresh_fulltrain",
            "--output", "<new-output>", "--max-calls", str(args.max_calls), "--max-seconds", str(args.max_seconds)]})
    export(args.output, Path(str(args.output) + ".zip"))
    print("SYNTHETIC plans exported; RELEASE BLOCKED; 0 model calls")


if __name__ == "__main__":
    main()
