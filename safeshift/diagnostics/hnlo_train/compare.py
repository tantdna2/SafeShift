"""Compare exact Qwen2.5 CPU baseline and two newly audited pooled reports."""
import argparse
import json
from pathlib import Path

from safeshift.ls1.artifacts import verify_run, write_json, seal
from .audit import baseline_rows, comparisons
from .cohort import metadata


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for model in ("qwen25", "qwen3", "internvl3"):
        p.add_argument("--" + model, type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    models = {"qwen2_5": baseline_rows(a.qwen25)}
    for name in ("qwen3", "internvl3"):
        root = getattr(a, name)
        verify_run(root)
        audit = json.loads((root / "audit.json").read_bytes())
        if audit["schema"] != "hnlo-train-pooled-audit-v1" or any(s["unit"]["model"] != name for s in audit["shards"]):
            raise ValueError("EXACT_AUDITED_MODEL_REPORT_REQUIRED")
        models[name] = audit["results"]
    # Labels have already been joined under each unit's explicit CPU authority.
    result = comparisons(models, metadata(Path.cwd()))
    a.output.mkdir(parents=True, exist_ok=False)
    write_json(a.output / "comparison.json", result)
    seal(a.output)


if __name__ == "__main__":
    main()
