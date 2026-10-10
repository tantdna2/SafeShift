"""Label-free CPU diagnostics for the ls1-v1 reference calibration.

Explains recorded decisions only. It never changes a prediction, fits a
parameter, reads ground truth or opens dataset images.

For unguarded calibrated logits ``z - b`` (``b`` = mean reference log-softmax), Level04
wins exactly when ``z[3] - z[i] > b[3] - b[i]`` for every other class ``i``
(strict, because ties go to the earlier canonical class). ``b[3] - b[i]`` is
the mean reference Level04-vs-class-i log-odds at the same forced prefix.
This score identity does not establish how safe an image looks to the model.
For any finite bias, logits ``z = b + [0, 0, 0, delta]`` with ``delta > 0``
select Level04 after calibration; its frequency on unseen scenes is unmeasured.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

from safeshift.data.p2_execution import safe_path
from safeshift.protocol.schema import strict_json
from .artifacts import json_bytes, read_verified, verify_run, write_json
from .audit import audit_run
from .core import LEVELS, REFERENCE_SPEC, calibrate, log_softmax

SEVERITY = {"Level01": 3, "Level02": 2, "Level03": 1, "Level04": 0}
HAZARD_FREE_RULE = ("A label-free correction must not raise an input that is hazard-free "
                    "by construction to Level01/Level02, nor increase its severity relative "
                    "to the uncalibrated LS1 decision. Declared 2026-10-11 after the first "
                    "technical run was observed; disclosed as post hoc.")


def reference_bias(reference_logits):
    """Per-reference log-softmax, the ls1-v1 bias and Level04 margins it imposes."""
    names = [name for name, _ in REFERENCE_SPEC]
    if set(reference_logits) != set(names):
        raise ValueError("EXACT_THREE_REFERENCES_REQUIRED")
    logs = {name: log_softmax(reference_logits[name]) for name in names}
    # Same expression and order as core.calibrate; equality is tested.
    bias = [math.fsum(logs[name][i] for name in names) / 3 for i in range(4)]
    return {"reference_log_probabilities": logs,
            "reference_predictions": {name: LEVELS[max(range(4), key=lambda i: logs[name][i])]
                                      for name in names},
            "bias": bias,
            "per_class_reference_spread": [max(logs[n][i] for n in names) - min(logs[n][i] for n in names)
                                           for i in range(4)],
            "level04_required_log_odds": {LEVELS[i]: bias[3] - bias[i] for i in range(3)}}


def explain_decision(raw_logits, reference_logits):
    """Why the calibrated decision is (not) Level04, using the official calibrate()."""
    modes = calibrate(raw_logits, reference_logits, protect_level01=False)
    reference = reference_bias(reference_logits)
    if reference["bias"] != modes["reference_log_bias"]:
        raise ValueError("REFERENCE_BIAS_RECOMPUTATION_MISMATCH")
    z = [float(x) for x in raw_logits]
    observed = {LEVELS[i]: z[3] - z[i] for i in range(3)}
    required = reference["level04_required_log_odds"]
    deficit = {label: required[label] - observed[label] for label in observed}
    before = modes["uncalibrated"]["prediction"]
    after = modes["calibrated"]["prediction"]
    reachable = after == "Level04"
    # Algebraic identity; only floating near-ties (|deficit| <= 1e-9) may disagree.
    if (reachable != all(value < 0 for value in deficit.values())
            and min(abs(value) for value in deficit.values()) > 1e-9):
        raise ValueError("LEVEL04_MARGIN_IDENTITY_VIOLATED")
    return {"uncalibrated": before, "calibrated": after,
            "severity_change": SEVERITY[after] - SEVERITY[before],
            "sample_level04_log_odds": observed,
            "level04_required_log_odds": required,
            "level04_deficit": deficit,
            "level04_reachable": reachable,
            "binding_competitor": max(deficit, key=lambda label: deficit[label])}


def hazard_free_sanity(rows):
    """rows: (sample_id, uncalibrated, calibrated) for inputs hazard-free by construction."""
    rows = list(rows)
    if not rows or any(u not in SEVERITY or c not in SEVERITY for _, u, c in rows):
        raise ValueError("HAZARD_FREE_ROWS_REQUIRED")
    alarms = [sid for sid, _, calibrated in rows if calibrated in ("Level01", "Level02")]
    escalations = [sid for sid, before, after in rows if SEVERITY[after] > SEVERITY[before]]
    return {"rule": HAZARD_FREE_RULE, "status": "FAIL" if alarms or escalations else "PASS",
            "n": len(rows), "calibrated_level01_or_level02": alarms, "severity_escalations": escalations,
            "limitation": ("Synthetic drawings are not industrial scenes. PASS would not show benefit; "
                           "FAIL shows the correction alarms on known hazard-free input.")}


def diagnose_run(root):
    """Diagnose a sealed LS1 run after the existing checksum/recomputation audit."""
    root = Path(root).absolute()
    audit = audit_run(root)
    inventory = verify_run(root)
    cohort = strict_json((root / "cohort.json").read_bytes())
    results = strict_json((root / "results.json").read_bytes())
    references, samples, sanity_rows = {}, [], []
    for result in results:
        row = {"sample_id": result["sample_id"], "status": result["status"]}
        if result["status"] == "SUCCESS":
            mapping = result["score"]["decision"]
            key = hashlib.sha256(json_bytes(mapping["prefix_ids"])).hexdigest()
            if key not in references:
                logits = {}
                for name, _ in REFERENCE_SPEC:
                    locator = "references/" + key + "/" + name + ".raw.json"
                    raw = read_verified(safe_path(root, locator), inventory[locator])
                    logits[name] = [raw["steps"][0]["raw"]["candidate_values"][str(i)]
                                    for i in mapping["token_ids"]]
                references[key] = {"logits": logits, **reference_bias(logits)}
            explanation = explain_decision(result["score"]["raw_label_logits"], references[key]["logits"])
            if (explanation["uncalibrated"] != result["modes"]["uncalibrated"]["prediction"]
                    or explanation["calibrated"] != result["modes"]["calibrated"]["prediction"]):
                raise ValueError("RECORDED_PREDICTION_MISMATCH")
            row.update(reference_key=key, generated_label=result["score"]["generated_label"], **explanation)
            sanity_rows.append((result["sample_id"], explanation["uncalibrated"], explanation["calibrated"]))
        samples.append(row)
    # Apply this post-hoc rule only to the known hazard-free technical drawings.
    synthetic = cohort["source_kind"] == "SYNTHETIC"
    return {"protocol": "LS1", "kind": "LS1_CALIBRATION_DIAGNOSTICS_LABEL_FREE",
            "audit": audit, "source_kind": cohort["source_kind"], "references": references,
            "samples": samples,
            "hazard_free_sanity": hazard_free_sanity(sanity_rows) if synthetic and sanity_rows else None,
            "performance_claim": "NONE_DIAGNOSTIC_ONLY"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = diagnose_run(args.run)
    if args.output:
        write_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
