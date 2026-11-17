"""Read-only CPU rehearsal on authentic Master/TRAIN copies; never runs a model.

The report proves supplied bytes and paths. Provider/version custody must be
recorded separately; neither a path name nor a report authenticates Kaggle.
"""
import argparse
from pathlib import Path
import time

from safeshift.candidates.source import require
from safeshift.pilot.artifacts import read, write, sha, safe
from safeshift.pilot.contract import digest
from safeshift.fulltrain import original_inputs as original, contract


def check(inputs, spec, *, decode=True):
    started = time.monotonic()
    inputs = Path(inputs).absolute()
    request = spec["request"]
    root, cohort, rows = original.admit(inputs, request["original_inputs"], request["marker_sha256"],
        request["projection_sha256"])
    result = original.verify_images(root, cohort, rows) if decode else original.verify_bytes(root, cohort, rows)
    master = original.unique_path(safe(inputs, request["original_inputs"]["master_dataset"]["mount"]), original.MASTER_PATHS)
    first = safe(root, rows[0]["image"])
    return {"schema": "safeshift-minicpm-real-input-rehearsal-v1", "status": "SUPPLIED_REAL_FILES_ADMISSIBLE",
        "master_relative": master.relative_to(inputs).as_posix(), "master_sha256": sha(master),
        "train_relative": root.relative_to(inputs).as_posix(), "projection_sha256": digest(cohort),
        "result": result, "first_file": {"ordinal": 0, "bytes": first.stat().st_size, "sha256": sha(first)},
        "image_bytes": sum(safe(root, row["image"]).stat().st_size for row in rows),
        "seconds": time.monotonic() - started, "model_calls": 0, "test_bytes_read": 0,
        "provider_custody": "SEPARATE_AUTHENTIC_VERSIONED_LISTING_AND_DOWNLOAD_EVIDENCE_REQUIRED",
        "gpu_model_fit": "NOT_RUN", "source_manifest_sha256": digest(contract.source_manifest())}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "spec", "output"):
        p.add_argument("--" + name, required=True, type=Path)
    args = p.parse_args()
    require(not args.output.absolute().is_relative_to(args.inputs.absolute()), "READ_ONLY_INPUT_OUTPUT_SEPARATION")
    result = check(args.inputs, read(args.spec))
    write(args.output, result)
    print(result["status"], result["result"]["verified_images"], "TRAIN files; no GPU/model")


if __name__ == "__main__":
    main()
