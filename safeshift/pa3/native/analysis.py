"""PA3 descriptive evaluator and proposed whole-group uncertainty engine.

No threshold fitting, score reversal, decision rule or automatic H1 claim.
"""

import math
import random
from collections import Counter, defaultdict

from safeshift.ls1.core import LEVELS
from safeshift.ls1.evaluate import auc, anomaly_log_odds
from . import access
from .native_score import STATUSES


def validate(rows, metadata, completed):
    ids = [r["sample_id"] for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(metadata):
        raise ValueError("EXACT_UNIQUE_GT_JOIN_REQUIRED")
    for sid, meta in metadata.items():
        if set(meta) != {"level", "domain", "group"} or meta["level"] not in LEVELS:
            raise ValueError("CANONICAL_GT_SCHEMA_REQUIRED")
        if any(type(meta[k]) is not str or not meta[k] for k in ("domain", "group")):
            raise ValueError("DOMAIN_GROUP_REQUIRED")
    for row in rows:
        if row["status"] not in STATUSES:
            raise ValueError("UNKNOWN_RESULT_STATUS")
        if any(type(row[k]) is not bool for k in ("attempted", "persisted", "parsed")):
            raise ValueError("BOOLEAN_FLOW_REQUIRED")
        if row["persisted"] and not row["attempted"] or row["parsed"] and not row["persisted"]:
            raise ValueError("FLOW_ORDER_MISMATCH")
        if row["status"] == "SUCCESS":
            if not all(row[k] for k in ("attempted", "persisted", "parsed")):
                raise ValueError("SCORED_WITHOUT_VALID_FLOW")
            details = row["details"]
            logs = details["log_probabilities"]
            if len(logs) != 4 or any(not math.isfinite(v) for v in logs):
                raise ValueError("FINITE_FOUR_LOG_PROBABILITIES_REQUIRED")
            if (not math.isfinite(row["score"]) or row["score"] != anomaly_log_odds(logs)
                    or row["generated_label"] not in LEVELS):
                raise ValueError("SCORE_OR_LABEL_MISMATCH")
        elif row["score"] is not None or row["details"] is not None:
            raise ValueError("UNSCORED_MUST_REMAIN_MISSING")
    if completed and any(r["status"] not in {"SUCCESS", "INVALID"} for r in rows):
        raise ValueError("INCOMPLETE_RUN_CANNOT_BE_COMPLETED")


def endpoint(rows, metadata, score_key=None, positive=None):
    eligible = [r for r in rows if r["status"] == "SUCCESS"]
    truth = [(metadata[r["sample_id"]]["level"] != "Level04") if positive is None
             else metadata[r["sample_id"]]["level"] == positive for r in eligible]
    scores = [r["score"] if score_key is None else score_key(r) for r in eligible]
    n1, n0 = sum(truth), len(truth) - sum(truth)
    return {"value": auc(truth, scores), "reason": None if n1 and n0 else "MISSING_SCORED_CLASS",
            "positive_n": n1, "negative_n": n0, "pair_denominator": n1 * n0,
            "eligible_ids": [r["sample_id"] for r in eligible], "tie_credit": 0.5}


def summary(rows, metadata):
    eligible = [r for r in rows if r["status"] == "SUCCESS"]
    supports = Counter(metadata[r["sample_id"]]["level"] for r in rows)
    return {"planned": len(rows), "attempted": sum(r["attempted"] for r in rows),
            "persisted": sum(r["persisted"] for r in rows), "parsed": sum(r["parsed"] for r in rows),
            "scored": len(eligible), "coverage": len(eligible)/len(rows) if rows else None,
            "coverage_reason": None if rows else "NO_PLANNED_SAMPLES",
            "status_counts": {s: sum(r["status"] == s for r in rows) for s in STATUSES},
            "level_counts": {k: supports[k] for k in LEVELS},
            "anomaly_n": sum(v for k, v in supports.items() if k != "Level04"),
            "normal_n": supports["Level04"],
            "groups": len({metadata[r["sample_id"]]["group"] for r in rows}),
            "scored_groups": len({metadata[r["sample_id"]]["group"] for r in eligible}),
            "auroc": endpoint(rows, metadata)}


def quantiles(values):
    if not values:
        return {"n": 0, "min": None, "median": None, "max": None}
    values = sorted(values)
    n = len(values)
    return {"n": n, "min": values[0], "median": (values[(n-1)//2] + values[n//2])/2,
            "max": values[-1]}


def report(rows, metadata, *, completed=False):
    validate(rows, metadata, completed)
    eligible = [r for r in rows if r["status"] == "SUCCESS"]
    overall = summary(rows, metadata)
    level = {k: summary([r for r in rows if metadata[r["sample_id"]]["level"] == k], metadata) for k in LEVELS}
    domain = {d: summary([r for r in rows if metadata[r["sample_id"]]["domain"] == d], metadata)
              for d in sorted({m["domain"] for m in metadata.values()})}
    binary = {label: summary([r for r in rows if (metadata[r["sample_id"]]["level"] != "Level04") == yes], metadata)
              for label, yes in (("Anomaly", True), ("Normal", False))}
    ovr = {k: endpoint(rows, metadata, lambda r, i=i: r["details"]["log_probabilities"][i], k)
           for i, k in enumerate(LEVELS)}
    pairwise = {k: endpoint([r for r in rows if metadata[r["sample_id"]]["level"] in (k, "Level04")],
                           metadata, lambda r, i=i: r["details"]["raw_label_logits"][i] - r["details"]["raw_label_logits"][3], k)
                for i, k in enumerate(LEVELS[:3])}
    controls = {"constant": endpoint(rows, metadata, lambda r: 0.0),
                "always_Level03": endpoint(rows, metadata, lambda r: 1.0),
                "generated_binary_label": endpoint(rows, metadata, lambda r: float(r["generated_label"] != "Level04"))}
    confusion = {}
    for kind in ("generated", "raw_argmax"):
        table = {k: {p: 0 for p in (*LEVELS, "INVALID", "TECHNICAL_ERROR", "INTERRUPTED", "UNPROCESSED", "NOT_ATTEMPTED")}
                 for k in LEVELS}
        for row in rows:
            pred = row["status"]
            if row["status"] == "SUCCESS":
                pred = row["generated_label"] if kind == "generated" else row["details"]["prediction"]
            table[metadata[row["sample_id"]]["level"]][pred] += 1
        confusion[kind] = table
    distributions = {}
    for key in sorted({(m["level"], m["domain"]) for m in metadata.values()}):
        selected = [r for r in eligible if (metadata[r["sample_id"]]["level"], metadata[r["sample_id"]]["domain"]) == key]
        distributions["|".join(key)] = {
            "s": quantiles([r["score"] for r in selected]),
            "log_probabilities": {k: quantiles([r["details"]["log_probabilities"][i] for r in selected]) for i, k in enumerate(LEVELS)},
            "margins_vs_Level04": {k: quantiles([r["details"]["raw_label_logits"][i] - r["details"]["raw_label_logits"][3] for r in selected]) for i, k in enumerate(LEVELS[:3])},
            "four_label_mass": quantiles([r["details"]["four_label_probability_mass"] for r in selected]),
            "four_label_log_mass": quantiles([r["details"]["four_label_log_mass"] for r in selected])}
    prefixes = defaultdict(list)
    for row in rows:
        key = "UNSCORED"
        if row["details"]:
            mapping = row["details"]["decision"]
            key = str(mapping["prefix_ids"]) + "|wrapper=" + str(mapping["format_wrapper_detected"])
        prefixes[key].append(row)
    full_pairs = overall["anomaly_n"] * overall["normal_n"]
    observed_pairs = overall["auroc"]["pair_denominator"]
    wins = (overall["auroc"]["value"] or 0) * observed_pairs
    bounds = ([wins/full_pairs, (wins+full_pairs-observed_pairs)/full_pairs]
              if completed and full_pairs else None)
    domain_values = [s["auroc"]["value"] for s in domain.values() if s["auroc"]["value"] is not None]
    ovr_values = [ovr[k]["value"] for k in LEVELS]
    return {"schema": "pa3-evaluation-v1", "completed": completed,
            "scope": "SCORE_CONDITIONAL_DESCRIPTIVE" if completed else "PARTIAL_RUN_DESCRIPTIVE_ONLY",
            "direction": "HIGHER_IS_ANOMALY", "confirmatory_conclusion": "BLOCKED_PENDING_RESEARCH_LEAD",
            "overall": overall, "by_level": level, "by_binary_class": binary, "by_domain": domain,
            "macro_domain_auroc": sum(domain_values)/len(domain_values) if domain_values else None,
            "macro_domain_K": len(domain_values), "ovr": ovr,
            "four_class_macro_ovr": sum(ovr_values)/4 if all(v is not None for v in ovr_values) else None,
            "pairs_vs_Level04": pairwise, "Level03_scope": "EXPLORATORY_ALWAYS",
            "generated_Level03": summary([r for r in rows if r["generated_label"] == "Level03"], metadata),
            "controls_same_eligible_ids": controls, "confusion": confusion,
            "safety_counts": {kind: {"Level01_misses": sum(v for k, v in table["Level01"].items() if k != "Level01"),
                                      "Level01_n": level["Level01"]["planned"],
                                      "Normal_to_Level01_or_Level02": table["Level04"]["Level01"] + table["Level04"]["Level02"],
                                      "Normal_n": level["Level04"]["planned"]} for kind, table in confusion.items()},
            "score_distributions": distributions, "by_prefix_format": {k: summary(v, metadata) for k, v in prefixes.items()},
            "raw_processed_different": sum(not r["details"]["raw_and_processed_label_scores_equal"] for r in eligible),
            "raw_global_argmax_differs_from_processed": sum(r["details"]["raw_argmax_id"] != r["details"]["processed_argmax_id"] for r in eligible),
            "prediction_counts": {kind: dict(Counter(r["generated_label"] if kind == "generated" else r["details"]["prediction"] for r in eligible))
                                  for kind in ("generated", "raw_argmax")},
            "raw_label_ties": sum(r["details"]["raw_label_logits"].count(max(r["details"]["raw_label_logits"])) > 1 for r in eligible),
            "leave_one_group_out": {g: endpoint([r for r in rows if metadata[r["sample_id"]]["group"] != g], metadata)
                                     for g in sorted({m["group"] for m in metadata.values()})},
            "completion_bounds_not_ci": bounds, "completion_bounds_reason": None if bounds else "INCOMPLETE_OR_NO_FULL_COHORT_PAIRS",
            "limitations": ["Generated-prefix and parse-valid selection", "Prior exposure and domain confounding",
                            "Group IDs do not prove independence", "No accuracy or safety improvement claim"]}


def grouped_bootstrap(rows, metadata, *, draws, seed, confidence, confirmatory=False):
    """Candidate algorithm, explicitly supplied parameters; shared paired draws.

    Sample whole components within domain; all cross-domain components share
    a mixed-domain stratum. Carry missing eligibility, image weighting and all
    repeated occurrences. This is NOT the frozen D9R24 bootstrap.
    """
    if confirmatory:
        access.require("statistics")
    validate(rows, metadata, False)
    if type(draws) is not int or draws < 1 or type(seed) is not int or not 0 < confidence < 1:
        raise ValueError("EXPLICIT_BOOTSTRAP_PARAMETERS_REQUIRED")
    groups, strata = defaultdict(list), defaultdict(list)
    for row in rows:
        groups[metadata[row["sample_id"]]["group"]].append(row)
    for g, members in sorted(groups.items()):
        domains = {metadata[r["sample_id"]]["domain"] for r in members}
        strata[("domain", next(iter(domains))) if len(domains) == 1 else ("mixed-domain",)].append(g)
    rng = random.Random(seed)
    values, contrasts, coverages, missing = [], [], [], 0
    for _ in range(draws):
        sample = [r for keys in strata.values() for _ in keys for r in groups[rng.choice(keys)]]
        primary = endpoint(sample, metadata)["value"]
        coverages.append(sum(r["status"] == "SUCCESS" for r in sample)/len(sample) if sample else 0)
        if primary is None:
            missing += 1
            continue
        hard = endpoint(sample, metadata, lambda r: float(r["generated_label"] != "Level04"))["value"]
        values.append(primary)
        contrasts.append(primary-hard)

    def interval(v):
        if not v:
            return None
        v = sorted(v)
        def q(p):
            x = (len(v)-1)*p
            a, b = math.floor(x), math.ceil(x)
            return v[a] + (v[b]-v[a])*(x-a)
        return [q((1-confidence)/2), q((1+confidence)/2)]

    return {"scope": "PROPOSED_EXPLORATORY_NOT_CONFIRMATORY", "draws": draws, "seed": seed,
            "confidence": confidence, "valid_draws": len(values), "invalid_draws": missing,
            "invalid_reason": "MISSING_SCORED_CLASS", "valid_fraction": len(values)/draws,
            "percentile_interval": interval(values), "paired_raw_minus_generated_interval": interval(contrasts),
            "coverage_draws": quantiles(coverages), "group_count": len(groups),
            "groups_by_binary_class": {label: len({metadata[r["sample_id"]]["group"] for r in rows
                                        if r["status"] == "SUCCESS" and (metadata[r["sample_id"]]["level"] != "Level04") == yes})
                                       for label, yes in (("Anomaly", True), ("Normal", False))},
            "stratum_group_counts": {str(k): len(v) for k, v in strata.items()},
            "decision_thresholds": "NOT_FROZEN_NO_AUTOMATIC_CONCLUSION"}
