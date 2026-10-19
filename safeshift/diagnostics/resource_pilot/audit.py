"""Independent CPU HNLO replay with no labels, metrics or checkpoint load."""
import argparse
import json
from pathlib import Path

from safeshift.pa3.native.journal import Journal
from ..one_click.artifacts import write
from . import cohort, custody
from .capture import replay
from .contract import AUTHORITY, authorize, unit


def checked(root, repo, tokenizer):
    root, repo = Path(root), Path(repo)
    custody.verify(root)
    binding = json.loads((root / "binding.json").read_bytes())
    from .bootstrap import verify_topology
    source = binding["source"]
    if verify_topology(repo, source["github_pr"], source["payload_sha256"]) != source:
        raise ValueError("RAW_SOURCE_CHANGED")
    u = unit(binding["unit"]["model"])
    if binding["unit"] != u or binding["authority"] != json.loads((repo / AUTHORITY).read_bytes()):
        raise ValueError("RAW_UNIT_OR_AUTHORITY_CHANGED")
    authorize(binding["authority"], source, u["model"])
    planned = cohort.planned(repo)
    if binding["samples"] != planned:
        raise ValueError("ORIGINAL_ID_ORDER_OR_SHA_CHANGED")
    j = Journal(root / "raw/index")
    rows, terminal, intact = [], False, True
    if j.root.exists():
        if j.read("manifest") != {"samples": cohort.opaque_rows(planned), "expected_count": 8}:
            raise ValueError("RAW_SAMPLE_UNIVERSE_CHANGED")
        intact = j.verify()
    for i, original in enumerate(planned):
        row = {"ordinal": i, "sample_id": original["sample_id"], "image_sha256": original["image_sha256"],
               "status": "NOT_ATTEMPTED", "score": None, "seconds": None}
        name = f"sample-{i:06d}"
        try:
            if j.root.exists() and j.exists(name + ".attempt"):
                if terminal:
                    raise ValueError("ATTEMPT_AFTER_FAILURE_FORBIDDEN")
                if j.read(name + ".attempt") != cohort.opaque_rows(planned)[i]:
                    raise ValueError("ATTEMPT_HASH_CHANGED")
                cap = Journal(root / "raw" / name)
                row["status"] = "INTERRUPTED"
                if cap.verify() and cap.exists("trace"):
                    result = replay(cap, tokenizer)
                    if cap.read("identity")["image_sha256"] != original["image_sha256"] or cap.read("identity")["ordinal"] != i:
                        raise ValueError("CAPTURE_IDENTITY_CHANGED")
                    if j.exists(name + ".result") and result != j.read(name + ".result"):
                        raise ValueError("CPU_RECOMPUTATION_MISMATCH")
                    row.update(status=result["status"], score=result["score"],
                               complexity=cap.read("complexity"),
                               output_tokens=len(cap.read("trace")["continuation_ids"]))
                elif cap.exists("error"):
                    row["status"] = cap.read("error")["status"]
                else:
                    intact = False
                if j.exists(name + ".timing"):
                    row["seconds"] = j.read(name + ".timing")["seconds"]
            elif (root / "raw" / name).exists():
                raise ValueError("ORPHAN_CAPTURE")
            elif j.root.exists() and j.exists(name + ".timing"):
                timing = j.read(name + ".timing")
                row.update(status=timing["status"], seconds=timing["seconds"],
                           reason="RESOURCE_ADMISSION_FAILED_BEFORE_NATIVE_CALL")
        except (OSError, ValueError) as e:
            if isinstance(e, ValueError) and not str(e).startswith(("TORN_WRITE", "UNSEALED")):
                raise
            intact = False
            row.update(status="INTERRUPTED", score=None, error=type(e).__name__)
        terminal = terminal or row["status"] != "SUCCESS"
        rows.append(row)
    complete = (intact and all(r["status"] == "SUCCESS" for r in rows) and j.root.exists()
                and j.exists("finish") and not j.exists("failure") and not j.exists("finalization-error"))
    return {"status": "COMPLETE" if complete else "PARTIAL", "full_vocab_replay": False,
            "cpu_hnlo_replay": "PASS" if complete else "PARTIAL", "samples": rows,
            "labels_or_gt_read": False, "HNLO_RESEARCH_VERIFIED": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--model", choices=("qwen3", "internvl3"), required=True)
    p.add_argument("--cache", required=True)
    a = p.parse_args()
    repo = Path.cwd()
    custody.verify(a.root)  # first, before tokenizer construction or any parser
    from ..one_click.contract import MODELS
    from safeshift.runners.internvl3_snapshot import snapshot_path
    if a.model == "internvl3":
        snapshot = snapshot_path(repo, a.cache)
    else:
        snapshot = repo / a.cache / "models--Qwen--Qwen3-VL-8B-Instruct/snapshots" / MODELS[a.model]["revision"]
    from .tokenizer import verify
    verify(a.model, snapshot, repo)
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True, trust_remote_code=False, use_fast=True)
    report = checked(a.root, repo, tokenizer)
    write(a.root.parent / "cpu-audit.json", report)
    return 0 if report["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
