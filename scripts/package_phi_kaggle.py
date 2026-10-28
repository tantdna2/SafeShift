"""Prepare private Kaggle CLI files locally; never call Kaggle or start a run.

Release preparer supplies approved account/input identifiers. This tool neither
issues nor edits a grant. Owner can instead upload the unchanged notebook in UI.
"""
import argparse
from pathlib import Path
import re

from safeshift.pilot.artifacts import write, write_bytes
from scripts.build_three_vlm_notebooks import ROOT, notebook


def package(output, kernel_id, input_dataset, grant_dataset):
    slugs = (kernel_id, input_dataset, grant_dataset)
    if any(not re.fullmatch(r"[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+", value) for value in slugs):
        raise ValueError("APPROVED_OWNER_SLUG_REQUIRED")
    if input_dataset == grant_dataset:
        raise ValueError("SEPARATE_PRIVATE_INPUT_AND_GRANT_DATASETS_REQUIRED")
    import json
    output = Path(output)
    if not output.resolve().is_relative_to((ROOT / "data/processed").resolve()):
        raise ValueError("LOCAL_PACKAGE_UNDER_DATA_PROCESSED_REQUIRED")
    output.mkdir(parents=True, exist_ok=False)
    filename = "SafeShift_TRAIN_PILOT_phi.ipynb"
    write_bytes(output / filename, (json.dumps(notebook("phi"), indent=1, ensure_ascii=False) + "\n").encode())
    metadata = {"id": kernel_id, "title": "SafeShift Phi TRAIN Pilot", "code_file": filename,
                "language": "python", "kernel_type": "notebook", "is_private": True,
                "enable_internet": True, "enable_gpu": True, "machine_shape": "NvidiaTeslaT4",
                "dataset_sources": [input_dataset, grant_dataset], "competition_sources": [],
                "kernel_sources": [], "model_sources": []}
    write(output / "kernel-metadata.json", metadata)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "kernel-id", "input-dataset", "grant-dataset"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    package(args.output, args.kernel_id, args.input_dataset, args.grant_dataset)
    print("Prepared local files only. No Kaggle API or run was invoked.")


if __name__ == "__main__":
    main()
