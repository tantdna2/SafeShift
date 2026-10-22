"""CPU-only per-unit audit entrypoint; no model or dataset images are loaded."""
import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--model", choices=("qwen3",), required=True)
    a = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or os.environ.get("USE_TORCH") != "0":
        raise RuntimeError("CPU_ONLY_ENVIRONMENT_REQUIRED")
    from .audit import verify_custody, evaluate
    from .contract import authorize, AUTHORITY
    from .bootstrap import verify_topology
    repo = Path.cwd()
    verify_custody(a.root)
    binding = json.loads((a.root / "binding.json").read_bytes())
    proof = verify_topology(repo, binding["source"]["github_pr"], binding["source"]["payload_sha256"])
    authorize(json.loads((repo / AUTHORITY).read_bytes()), proof)
    # Resolve only the pinned tokenizer files, without rehashing/loading weights.
    from scripts.provision_qwen3vl_snapshot import cached_snapshot
    from safeshift.runners.internvl3_snapshot import snapshot_path
    from safeshift.ls1.tokenizer import probe
    from ..hnlo_capture import ordered_t1_ids
    from transformers import AutoTokenizer
    snapshot = (snapshot_path(repo, a.cache) if a.model == "internvl3"
                else cached_snapshot(str(repo / a.cache), offline=True))
    from ..hnlo_train.tokenizer import verify
    verify(a.model, snapshot, repo)
    tokenizer = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True, trust_remote_code=False, use_fast=True)
    ordered_t1_ids(probe(tokenizer))
    result = evaluate(a.root, repo, tokenizer, source=proof)
    return 0 if result["completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
