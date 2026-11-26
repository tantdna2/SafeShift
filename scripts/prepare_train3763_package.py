"""Prepare a release-free private Input package; never upload or submit."""
import argparse
import json
from pathlib import Path
from safeshift.kaggle_handoff import validate_request, private_root
from safeshift.internvl3763 import validate_execution_request
from safeshift.internvl3763_operator import input_sources
from safeshift.pilot.artifacts import read, write
from safeshift.candidates.source import require


def package(request, comment_id):
    validate_request(request)
    require(request["scope"] == "TRAIN3763_EXECUTION_CANDIDATE" and request["execution_release"] is None,
        "UNAUTHORIZED_CANDIDATE_PACKAGE_ONLY")
    require(type(comment_id) is int and comment_id > 0, "RESERVED_OWNER_COMMENT_ID_REQUIRED")
    validate_execution_request(request["bindings"]["runtime"]["execution_request"])
    input_sources(request)
    return {"request": request, "release_comment_id": comment_id}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--release-comment", type=int, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    root = private_root(args.directory)
    root.mkdir(parents=True, exist_ok=False)
    checksum = write(root / "safeshift_train3763_execution.json", package(read(args.request), args.release_comment))
    print(json.dumps({"status": "BLOCKED_PENDING_EXACT_EXECUTION_RELEASE", "package_sha256": checksum,
        "uploaded": False, "submitted": False}))


if __name__ == "__main__":
    main()
