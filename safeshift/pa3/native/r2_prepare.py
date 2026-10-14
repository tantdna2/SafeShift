"""CPU-only PA3-R2 manifest derivation and post-approval notebook release."""
import argparse
import hashlib
import json
from pathlib import Path
from . import r2, train, preflight
from ..artifacts import json_bytes


def build_manifest(repo):
    repo = Path(repo)
    original = (repo / train.FULL).read_bytes()
    shards = [(repo / train.inference_path(i)).read_bytes() for i in range(4)]
    train.validate_full(json.loads(original), shards)
    entries = []
    for i, payload in enumerate(shards):
        projected = {**json.loads(payload), "schema": "pa3-r2-train-inference-v1",
                     "run_id": r2.run_id(i), "experiment": "PA3-R2", "clamp": r2.POLICY}
        entries.append({"shard_id": i, "run_id": r2.run_id(i), "count": r2.SIZES[i],
                        "original_path": train.inference_path(i),
                        "original_sha256": hashlib.sha256(payload).hexdigest(),
                        "inference_manifest_sha256": hashlib.sha256(json_bytes(projected)).hexdigest()})
    return {"schema": "pa3-r2-full-train-v1", "experiment": "PA3-R2", "clamp": r2.POLICY,
            "count": r2.COUNT, "execution_authority": False,
            "original_full": {"path": train.FULL, "sha256": hashlib.sha256(original).hexdigest()},
            "shards": entries}


def release(repo, output):
    """Only after audited F2/M. Never fills or modifies an authority grant."""
    from .kaggle import bundle_source
    repo, output = Path(repo), Path(output)
    sha = preflight.git(repo, "rev-parse", "HEAD").decode()
    value = r2.authority(repo, sha)  # Draft denied before writes
    grant = value["grant"]
    r2.load_full(repo, grant["full_manifest_sha256"])
    manifest = r2.manifest(repo, grant["full_manifest_sha256"])
    if any(grant["shards"][i]["inference_manifest_sha256"] != manifest["shards"][i]["inference_manifest_sha256"]
           for i in range(4)):
        raise ValueError("R2_RELEASE_GRANT_MANIFEST_MISMATCH")
    proof = bundle_source(repo, output)
    locked = {"source_commit": sha, "source_bundle_sha256": proof["bundle_sha256"]}
    for i in range(4):
        nb = json.loads((repo / "notebooks/pa3_r2_full_train_kaggle.ipynb").read_bytes())
        nb["cells"][1]["source"] = [f"SHARD_ID = {i}\n", "LOCKED = " + repr(locked) + "\n"]
        (output / f"PA3_R2_SHARD_{i}.ipynb").write_bytes(json_bytes(nb))
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release", action="store_true")
    args = parser.parse_args()
    if args.release:
        release(args.repo, args.output)
    else:
        with args.output.open("xb") as stream:
            stream.write(json_bytes(build_manifest(args.repo)))
