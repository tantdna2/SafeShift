"""Run CT2 CPU screening on admitted exposed-TRAIN label projections."""

import argparse
from pathlib import Path
import platform
import sys

from safeshift.data.saved_reports import confined, git, json_bytes, sha256, strict_json
from safeshift.evaluation.ct2_screening import DEFAULT_SEEDS, SCHEMA, screen
from safeshift.evaluation.qwen_composite import require
from scripts.benchmark_full_train import (
    CONFIG_PATH, MEMBERS, SOURCE_FILES as ADMISSION_SOURCE_FILES, load_inputs, read_config,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (*ADMISSION_SOURCE_FILES, "scripts/screen_full_train_triage.py",
                "safeshift/evaluation/ct2_screening.py", "safeshift/data/schema.py",
                "safeshift/data/validation.py", "safeshift/evaluation/sensitivity.py")
OUTPUT_FILES = ("screening.json", "receipt.json")


def ignored_projection_path(root, directory, names):
    path = confined(root, directory, ("data", "processed"))
    for name in names:
        relative = f"{directory}/{name}"
        confined(root, relative, ("data", "processed"))
        try:
            git(root, "check-ignore", "--quiet", "--", relative)
        except ValueError:
            raise ValueError("CT2 requires Git-ignored input and output files") from None
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, help="admitted directory under data/processed")
    parser.add_argument("--output-dir", required=True, help="fresh directory under data/processed")
    parser.add_argument("--model-call-cap", type=int, action="append", metavar="M",
                        help="repeatable total model calls per arm, including all focal calls")
    parser.add_argument("--review-cap", type=int, action="append", metavar="K",
                        help="repeatable cap on unique human reviews")
    parser.add_argument("--seed", type=int, action="append", help="repeatable, defaults to 0, 1, 2")
    args = parser.parse_args(argv)
    try:
        source_sha = git(ROOT, "rev-parse", "HEAD").decode().strip()
        config_bytes = git(ROOT, "show", f"{source_sha}:{CONFIG_PATH}")
        config = read_config(ROOT)
        require(config == strict_json(config_bytes),
                "benchmark config changed during screening setup")
        source_dirty = bool(git(ROOT, "status", "--porcelain", "--untracked-files=normal"))
        source_files = {name: sha256(confined(ROOT, name).read_bytes()) for name in SOURCE_FILES}
        input_path = ignored_projection_path(ROOT, args.input_dir,
                                             [f"{name}.json" for name in MEMBERS])
        output = ignored_projection_path(ROOT, args.output_dir, OUTPUT_FILES)
        require(not output.is_relative_to(input_path) and not output.exists(),
                "CT2 output must be fresh and outside the admitted input directory")
        cohort, products = load_inputs(ROOT, args.input_dir, config)
        result = screen(cohort, products, config, seeds=args.seed or DEFAULT_SEEDS,
                        model_call_caps=args.model_call_cap, review_caps=args.review_cap)
        require(git(ROOT, "rev-parse", "HEAD").decode().strip() == source_sha,
                "Git HEAD changed during screening")

        result_bytes = json_bytes(result)
        receipt = {
            "schema": f"{SCHEMA}-receipt",
            "source_sha": source_sha,
            "source_dirty": source_dirty,
            "source_files": source_files,
            "python": platform.python_version(),
            "config_sha256": sha256(config_bytes),
            "result_status": result["result_status"],
            "upstream_result_status": result["upstream_result_status"],
            "cohort_identity_sha256": result["cohort_identity_sha256"],
            "product_source_seal_sha256": result["product_source_seal_sha256"],
            "inputs": config["release"]["members"],
            "execution_args": {
                "module": "scripts.screen_full_train_triage",
                "requested": {"seed": args.seed, "model_call_cap": args.model_call_cap,
                              "review_cap": args.review_cap},
                "effective": {name: result[name] for name in
                              ("seeds", "model_call_caps", "review_caps", "planned_n", "eligible_n")},
            },
            "outputs": {"screening.json": sha256(result_bytes)},
        }
        receipt_bytes = json_bytes(receipt)
        output.mkdir(parents=True, exist_ok=False)
        for name, data in zip(OUTPUT_FILES, (result_bytes, receipt_bytes), strict=True):
            with (output / name).open("xb") as stream:
                stream.write(data)
    except (OSError, KeyError, TypeError, AttributeError):
        print("CT2 screening failed during input, provenance or output processing", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
