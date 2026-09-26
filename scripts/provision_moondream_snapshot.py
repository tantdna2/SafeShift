"""Future explicit provisioning; verify-only never downloads or executes code."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.runners.moondream_snapshot import (
    MODEL_ID, REVISION, TOKENIZER_REPO, TOKENIZER_REVISION, artifact_rows,
    deny_network_permanently, verify_snapshot,
)
from safeshift.runners.storage import FileRawStore


def provision_or_verify(cache, *, provision=False):
    if not provision:
        deny_network_permanently()
    manifests = []
    for repo, revision in ((MODEL_ID, REVISION), (TOKENIZER_REPO, TOKENIZER_REVISION)):
        expected = Path(cache) / ("models--" + repo.replace("/", "--")) / "snapshots" / revision
        if provision:
            from huggingface_hub import snapshot_download
            actual = Path(snapshot_download(repo_id=repo, revision=revision, cache_dir=str(cache),
                                           allow_patterns=[r["path"] for r in artifact_rows(repo, revision)]))
            if actual.absolute() != expected.absolute():
                raise ValueError("UNEXPECTED_SNAPSHOT_PATH")
        manifests.append(verify_snapshot(expected, repo, revision))
    return {"schema_version": "moondream-provisioning-v1", "snapshots": manifests}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--provision", action="store_true")
    modes.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    cache = FileRawStore(ROOT, args.cache_dir).root
    output = FileRawStore(ROOT, args.manifest).root
    if output.exists():
        parser.error("manifest already exists")
    report = provision_or_verify(cache, provision=args.provision)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
