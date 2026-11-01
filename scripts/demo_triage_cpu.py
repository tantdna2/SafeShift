"""Handwritten synthetic queue comparison; no files, model calls or dependencies.

python -B -m scripts.demo_triage_cpu --budget 3 --tie-seed public-demo
The explicit seed is public demonstration material, never a production secret.
"""

import argparse
import json

from safeshift.data.schema import SampleRecord
from safeshift.data.validation import validate_samples
from safeshift.evaluation.triage import (
    ClassifiedResult, HNLOSignal, ModelResults, SourceIdentity, compare_review_queues,
)


def synthetic_inputs():
    """Invented tokens assigned independently of predictions or truth."""
    ids = tuple(f"{i:032x}" for i in range(1, 7))

    def source(name, rows):
        return ModelResults(SourceIdentity(name, "synthetic-revision", "synthetic-implementation",
                                           "synthetic-config", "synthetic-run", "synthetic-series",
                                           "synthetic-attempt"), rows)

    focal = source("synthetic-focal", (
        ClassifiedResult(ids[0], "SUCCESS", "Level04", HNLOSignal(9, True)),
        ClassifiedResult(ids[1], "SUCCESS", "Level04", HNLOSignal(2, True)),
        ClassifiedResult(ids[2], "SUCCESS", "Level04", HNLOSignal(5, True)),
        ClassifiedResult(ids[3], "INVALID"),
        ClassifiedResult(ids[4], "SUCCESS", "Level04"),
        ClassifiedResult(ids[5], "SUCCESS", "Level02", HNLOSignal(8, True)),
    ))
    peers = (
        source("synthetic-peer-a", tuple(ClassifiedResult(sid, "SUCCESS", label)
               for sid, label in zip(ids, ("Level04", "Level01", "Level03", "Level04",
                                           "Level04", "Level01")))),
        source("synthetic-peer-b", tuple(ClassifiedResult(ids[i], "SUCCESS", label)
               for i, label in ((0, "Level04"), (1, "Level02"), (2, "Level04"),
                                (3, "Level04"), (5, "Level02")))),
    )
    return ids, focal, peers


def evaluate_synthetic_queue(queue: dict, truth: tuple[SampleRecord, ...]) -> dict:
    """Post hoc fixture counts only; never feeds labels back into queue creation.

    Routed means available for review, NOT detected or corrected by a human.
    This demo has complete invented GT; production unresolved-GT evaluation and
    scientific metrics are deliberately outside this prototype.
    """
    truth = validate_samples(truth)
    by_id = {row.sample_id: row.true_safety_level for row in truth}
    if set(by_id) != {c["sample_id"] for c in queue["cases"]}:
        raise ValueError("synthetic evaluation requires exact planned GT IDs")
    false_safe = [c for c in queue["cases"]
                  if c["outputs"][0]["predicted_safety_level"] == "Level04"
                  and by_id[c["sample_id"]] != "Level04"]
    routed = [c for c in false_safe if c["selected"]]
    return {"synthetic_false_safe_count": len(false_safe),
            "routed_to_review_count": len(routed),
            "routed_via_mandatory": sum(c["category"] == "MANDATORY" for c in routed),
            "routed_via_ranking": sum(c["category"] == "RANKED" for c in routed),
            "not_routed_count": len(false_safe) - len(routed),
            "human_detection": "NOT_MEASURED", "human_correction": "NOT_MEASURED"}


def build_report(*, budget: int, tie_key: bytes) -> dict:
    ids, focal, peers = synthetic_inputs()
    comparison = compare_review_queues(ids, focal, peers, budget=budget, tie_key=tie_key)
    queues = comparison["operational"]
    # Only after every queue is constructed: separate, invented answer sheet.
    truth = tuple(SampleRecord(sid, label) for sid, label in zip(
        ids, ("Level04", "Level01", "Level02", "Level03", "Level01", "Level02")))
    return {"notice": "SYNTHETIC DEMO — NOT RESEARCH RESULT", "model_execution": False,
            "comparison": "OPERATIONAL_ARM_SPECIFIC_ELIGIBILITY",
            "queues": queues,
            "signal_control_queues": comparison["signal_control"],
            "post_hoc_fixture_counts": {mode: evaluate_synthetic_queue(queue, truth)
                                        for mode, queue in queues.items()},
            "post_hoc_signal_control_counts": {
                mode: evaluate_synthetic_queue(queue, truth)
                for mode, queue in comparison["signal_control"].items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget", type=int, required=True)
    parser.add_argument("--tie-seed", required=True, help="public synthetic seed, not a secret")
    args = parser.parse_args()
    try:
        report = build_report(budget=args.budget, tie_key=args.tie_seed.encode("utf-8"))
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False))


if __name__ == "__main__":
    main()
