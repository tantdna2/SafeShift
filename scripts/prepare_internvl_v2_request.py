"""Prepare hashed ordinal0 request from exact local historical custody, no image I/O.

Reads the checksum-pinned local historical master and an already-downloaded
original smoke archive. No Kaggle/network/weights/model or result pooling.
"""
import argparse
import json
from pathlib import Path

from safeshift.internvl_v2_runtime import source_spec
from safeshift.pilot.contract import digest
from safeshift.pilot.artifacts import write
from scripts.internvl_v2_campaign import original_recipe


def prepare(master, archive, output):
    request, _, _ = original_recipe(Path(master).read_bytes(), archive, source_spec())
    write(output, request)
    return {"request_sha256": digest(request), "image_access": "NONE",
            "scope": "LOCAL_ORIGINAL_IDENTITY_METADATA_ONLY", "model_calls": 0}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--master", type=Path, required=True)
    p.add_argument("--original-archive", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--continuous", action="store_true")
    a = p.parse_args()
    if a.continuous:
        from safeshift.internvl_v2_campaign import select_continuous
        select_continuous()
    print(json.dumps(prepare(a.master, a.original_archive, a.output), sort_keys=True))
