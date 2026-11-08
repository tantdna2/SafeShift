"""Local packaging or explicit Operator-only provider verification; never submits."""
import argparse
import json
from pathlib import Path
import shutil
from safeshift import internvl3763_python as py
from safeshift.pilot.artifacts import write


def prepare(archive, output, license_name, redistribution_ref):
    proof = py.verify_archive(archive)  # BEFORE any upload folder is created
    py.require(license_name and redistribution_ref.strip(), "OPERATOR_LICENSE_REVIEW_REQUIRED")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    dataset = output / "dataset"
    dataset.mkdir()
    shutil.copyfile(archive, dataset / py.manifest()["filename"])
    write(dataset / py.MARKER, py.manifest())
    py.verify_directory(dataset)
    # Kaggle's CLI treats this file as upload metadata, not a dataset member.
    write(dataset / "dataset-metadata.json", {"id": py.REF.rsplit("/", 1)[0],
        "title": "SafeShift CPython 3.11.9 20240726", "licenses": [{"name": license_name}]})
    write(output / "local-proof.json", {"status": "LOCAL_BYTES_PASS_NOT_UPLOADED", **proof,
        "ref": py.REF, "license_name": license_name, "redistribution_review": redistribution_ref,
        "provider_verification": "NOT_RUN", "gpu_calls": 0})
    return {"dataset": str(dataset), "status": "LOCAL_BYTES_PASS_NOT_UPLOADED"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("describe", "prepare", "verify-provider"))
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--license-name")
    parser.add_argument("--redistribution-ref")
    args = parser.parse_args(argv)
    if args.action == "describe":
        result = {"manifest": py.manifest(), "binding": py.binding(), "provider_status": "NOT_VERIFIED"}
    elif args.action == "prepare":
        if not all((args.archive, args.output, args.license_name, args.redistribution_ref)):
            parser.error("archive/output/license-name/redistribution-ref required")
        result = prepare(args.archive, args.output, args.license_name, args.redistribution_ref)
    else:
        if args.output is None:
            parser.error("--output required")
        from safeshift import internvl3763_operator as op
        request = {"bindings": {"runtime": {"python_input": py.binding()},
            "dataset": {"dataset_sources": [py.REF]}}}
        result = op.verify_python_input(op.api(), request, args.output)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
