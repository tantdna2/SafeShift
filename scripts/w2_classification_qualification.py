"""Future owner execution after PREP merge and separate Research Lead authorization."""

import argparse
import shlex
import sys

from safeshift.qualification.classification import MODELS
from safeshift.qualification.runtime import execute


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--research-lead-authorization", required=True)
    parser.add_argument("--venue-internet-off", action="store_true", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--cache-dir")
    args = parser.parse_args()
    report = execute(**vars(args), command=shlex.join(["python", "-m", "scripts.w2_classification_qualification", *sys.argv[1:]]))
    print(report["run_status"])
    return 0 if report["run_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
