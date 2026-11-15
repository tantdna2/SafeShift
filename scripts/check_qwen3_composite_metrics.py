"""Independent count/Fraction and positive-negative-pair oracle for saved products.

No imports from the composite implementation. This checks arithmetic, not source
authenticity or scientific/independent-audit approval. Use the sealed reader too.
"""

import argparse
from collections import Counter
import csv
from fractions import Fraction
import hashlib
import json
from math import isfinite
from pathlib import Path

LEVELS = ("Level01", "Level02", "Level03", "Level04")


def check(directory):
    with (directory / "samples.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert all(r["status"] == "SUCCESS" and r["generated_label"] in LEVELS for r in rows)
    saved = json.loads((directory / "metrics.json").read_bytes())
    checks = 0

    def equal(actual, expected):
        nonlocal checks
        if expected is None:
            assert actual is None, (actual, expected)
        elif isinstance(expected, Fraction):
            assert actual is not None and abs(actual - float(expected)) <= 1e-12, (actual, expected)
        else:
            assert actual == expected, (actual, expected)
        checks += 1

    def ratio(num, den):
        return Fraction(num, den) if den else None

    for name, m in saved["strata"].items():
        group = rows if name == "ALL" else [r for r in rows if
            r[{"domain": "domain", "level": "true_level", "source": "source_id"}[name.split(":", 1)[0]]]
            == name.split(":", 1)[1]]
        counts = Counter((r["true_level"], r["generated_label"]) for r in group)
        equal(m["planned_n"], len(group))
        for t in LEVELS:
            for p in (*LEVELS, "INVALID"):
                equal(m["confusion_4x5"][t][p], counts[t, p])
        f1s, recalls = [], []
        for t in LEVELS:
            support = sum(r["true_level"] == t for r in group)
            predicted = sum(r["generated_label"] == t for r in group)
            tp = counts[t, t]
            equal(m["support"][t], support)
            for key, numerator, denominator in (("precision", tp, predicted), ("recall", tp, support),
                                                 ("f1", 2 * tp, support + predicted)):
                equal(m["per_class"][t][key]["value"], ratio(numerator, denominator))
            if support:
                f1s.append(Fraction(2 * tp, support + predicted))
                recalls.append(Fraction(tp, support))
        equal(m["macro_f1"], sum(f1s) / len(f1s) if f1s else None)
        equal(m["balanced_accuracy"], sum(recalls) / len(recalls) if recalls else None)
        equal(m["accuracy"]["value"], ratio(sum(counts[t, t] for t in LEVELS), len(group)))
        b = Counter()
        for r in group:
            a, p = r["true_level"] != "Level04", r["generated_label"] != "Level04"
            b[("TP" if p else "FN") if a else ("FP" if p else "TN")] += 1
        for key in ("TP", "FN", "FP", "TN"):
            equal(m["binary"][key], b[key])
        for key, numerator, denominator in (
            ("false_safe", b["FN"], b["TP"] + b["FN"]),
            ("false_alarm", b["FP"], b["FP"] + b["TN"]),
            ("hazard_recall", b["TP"], b["TP"] + b["FN"]),
            ("specificity", b["TN"], b["FP"] + b["TN"]),
            ("accuracy", b["TP"] + b["TN"], len(group)),
            ("precision", b["TP"], b["TP"] + b["FP"]),
            ("f1", 2 * b["TP"], 2 * b["TP"] + b["FP"] + b["FN"]),
        ):
            equal(m["binary"][key]["numerator"], numerator)
            equal(m["binary"][key]["denominator"], denominator)
            equal(m["binary"][key]["value"], ratio(numerator, denominator))
    # Only within the two authorized score cohorts; never compute composite AUC.
    for cohort in ("v4_original_success", "recovery224"):
        group = [r for r in rows if (r["selection_reason"] == "ORIGINAL_NON_SUCCESS") == (cohort == "recovery224")]
        scored = []
        for r in group:
            try:
                value = float(r["hnlo_score"])
            except ValueError:
                continue
            if isfinite(value):
                scored.append((r["true_level"] != "Level04", value))
        positives = [s for y, s in scored if y]
        negatives = [s for y, s in scored if not y]
        equal(saved["hnlo"][cohort]["eligible_n"], len(scored))
        twice_concordance = sum(2 if a > b else int(a == b) for a in positives for b in negatives)
        equal(saved["hnlo"][cohort]["value"], ratio(twice_concordance, 2 * len(positives) * len(negatives)))
    equal(saved["hnlo"]["composite"]["value"], None)
    return {"status": "PASS_INDEPENDENT_NUMERICAL_ORACLE_NOT_EXTERNAL_AUDIT", "checks": checks,
            "strata": len(saved["strata"]), "rows": len(rows), "dependencies": [],
            "inputs_sha256": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                              for name in ("samples.csv", "metrics.json")}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--product-dir", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    result = check(args.product_dir)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, sort_keys=True, indent=2)
        f.write("\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
