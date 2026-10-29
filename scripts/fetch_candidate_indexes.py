"""Fetch only the two hash-pinned public checkpoint indexes, never weight shards."""
import argparse
from pathlib import Path
from urllib.request import build_opener
from scripts.pilot_source_audit import NoCredentialRedirect
from safeshift.candidates.source import ROOT, LOCK, require
from safeshift.candidates.loading import checkpoint_index
from safeshift.pilot.artifacts import read, write_bytes


def fetch(output):
    output = Path(output).resolve()
    require(output.is_relative_to(ROOT/"data/processed"), "OUTPUT_UNDER_DATA_PROCESSED_REQUIRED")
    output.mkdir(parents=True, exist_ok=False)
    opener = build_opener(NoCredentialRedirect())
    locked = read(LOCK.with_name("checkpoint_metadata_lock.json"))
    for key in ("internvl35", "minicpm4"):
        spec = locked[key]
        public = read(LOCK)[key]
        require(all(spec[k] == public[k] for k in ("id", "revision")), "INDEX_IDENTITY")
        name = "model.safetensors.index.json"
        require(spec["index"]["filename"] == name and spec["index"]["url"] ==
                f'https://huggingface.co/{spec["id"]}/resolve/{spec["revision"]}/{name}', "INDEX_URL")
        with opener.open(spec["index"]["url"], timeout=60) as response:
            data = response.read(spec["index"]["size"] + 1)
        path = output/f"{key}-{name}"
        write_bytes(path, data)
        checkpoint_index(path, key)
        print(key, "INDEX_HASH_PASS", len(data))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    fetch(parser.parse_args().output)
