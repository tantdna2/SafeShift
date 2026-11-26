"""Handwritten sealed fixture -> provenance adapter -> T2; no data/file inputs."""

import argparse
from dataclasses import asdict
import hashlib
import json

from safeshift.evaluation.triage import compare_review_queues
from safeshift.evaluation.triage_adapter import adapt_synthetic_bundle, fixture_sha256


# Assigned before handwritten predictions; not hashes of labels/filenames/domain.
IDS = tuple(f"{n:032x}" for n in range(1, 5))
CASES = ("complete", "missing_row", "missing_model", "invalid", "technical_error",
         "not_attempted", "focal_invalid", "hnlo_missing", "hnlo_ineligible")


def synthetic_bundle(case="complete"):
    """Original fictional saved results, including explicit failure variants.

    No actual model revision, source receipt, approval, inference or GT is used.
    The adapter independently pins the final content of each example in source.
    """
    if case not in CASES:
        raise ValueError("unknown synthetic case")
    inputs = [{"sample_id": sid, "content": f"handwritten synthetic input {n}"}
              for n, sid in enumerate(IDS)]
    samples = [{"sample_id": item["sample_id"],
                "input_sha256": hashlib.sha256(item["content"].encode()).hexdigest()}
               for item in inputs]
    reports, evidence = [], []
    labels = (("Level04", "Level04", "Level04", "Level01"),
              ("Level03", "Level02", "Level04", "Level01"),
              ("Level04", "Level01", "Level04", "Level04"))
    for index, model in enumerate(("qwen3", "internvl35", "minicpm4")):
        identity = dict(model_id="synthetic-" + model,
                        model_revision="fixture-revision-" + model + "-v1",
                        implementation_id="fixture-impl-" + model + "-v1",
                        configuration_id="fixture-config-" + model + "-v1",
                        run_id="fixture-run-" + model,
                        series_id="fixture-series-" + model,
                        attempt_id="fixture-attempt-1")
        rows = []
        for n, sid in enumerate(IDS):
            status, label = "SUCCESS", labels[index][n]
            h = None
            if index == 0 and n < 3:
                score = (9, 2, 1)[n]
                if n == 0 and case in ("hnlo_missing", "hnlo_ineligible", "focal_invalid"):
                    h = {"state": "INELIGIBLE" if case == "hnlo_ineligible" else "MISSING",
                         "value": score if case == "hnlo_ineligible" else None,
                         "evidence_sha256": None}
                else:
                    proof = {"sample_id": sid, "identity": dict(identity),
                             "input_sha256": samples[n]["input_sha256"], "value": score,
                             "qualification": "SYNTHETIC_UPSTREAM_VALIDATED"}
                    evidence.append(proof)
                    h = {"state": "VALID", "value": score, "evidence_sha256": fixture_sha256(proof)}
            if index == 0 and n == 0 and case == "focal_invalid":
                status, label = "INVALID", None
            if index == 2 and n == 0:
                status = {"invalid": "INVALID", "technical_error": "TECHNICAL_ERROR",
                          "not_attempted": "NOT_ATTEMPTED"}.get(case, status)
                if status != "SUCCESS":
                    label = None
                if case == "missing_row":
                    continue
            rows.append({"sample_id": sid, "identity": dict(identity),
                         "input_sha256": samples[n]["input_sha256"], "status": status,
                         "predicted_safety_level": label, "hnlo": h})
        reports.append({"source_id": "fixture-source-" + model, "identity": identity,
                        "planned_ids": list(IDS),
                        "rows": [] if case == "missing_model" and index == 2 else rows})
    sources = [{"source_id": r["source_id"], "role": "focal" if n == 0 else "peer",
                "identity": dict(r["identity"]), "report_sha256": fixture_sha256(r)}
               for n, r in enumerate(reports)]
    manifest = {"schema": "safeshift-t3-synthetic-v1", "planned_ids": list(IDS),
                "samples": samples, "sources": sources}
    selection = {"selection_id": "fixture-selection-" + case,
                 "authority_id": "fictional-fixture-custodian-not-real-approval",
                 "rule": "EXPLICIT_FIXTURE_SELECTION_NO_POOLING",
                 "manifest_sha256": fixture_sha256(manifest),
                 "entries": [{k: v for k, v in spec.items() if k != "role"} for spec in sources]}
    return {"manifest": manifest, "inputs": inputs, "reports": reports,
            "selection": selection, "evidence": evidence}


def build_report(*, case, budget, tie_key):
    adapted = adapt_synthetic_bundle(synthetic_bundle(case))
    queues = compare_review_queues(adapted.planned_ids, adapted.focal, adapted.peers,
                                   budget=budget, tie_key=tie_key)
    return {"notice": "SYNTHETIC DEMO - NOT RESEARCH RESULT", "fixture_case": case,
            "real_data_activation": "UNAVAILABLE", "model_execution": False,
            "provenance": {k: v for k, v in asdict(adapted).items()
                           if k not in ("planned_ids", "focal", "peers")}, **queues}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, default="complete")
    parser.add_argument("--budget", required=True, type=int)
    parser.add_argument("--tie-seed", required=True, help="Public synthetic demo seed only")
    args = parser.parse_args()
    try:
        report = build_report(case=args.case, budget=args.budget, tie_key=args.tie_seed.encode())
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
