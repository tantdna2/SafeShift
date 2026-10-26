"""Locked M2 v1 formulas on validated synthetic saved reports (CPU only)."""

from collections import Counter, defaultdict
from itertools import combinations, permutations
from math import fsum, isfinite, log

from safeshift.data.saved_reports import MODELS, NOTICE, membership, sha256, json_bytes, validate_ledger
from safeshift.data.schema import SAFETY_LEVELS, SampleRecord, PredictionRecord
from .metrics import classification_metrics
from .sensitivity import components, summarize_groups, weighted_auc

NORMAL = "Level04"


def finite_median(values):
    values = sorted(values)
    middle = len(values) // 2
    if not values:
        return None
    return values[middle] if len(values) % 2 else values[middle - 1] / 2 + values[middle] / 2


def ratio(numerator, denominator, reason="ZERO_SUPPORT"):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None,
            "status": "DEFINED" if denominator else "UNDEFINED",
            "reason": None if denominator else reason}


def auc(labels, scores, weights=None):
    weights = [1.0] * len(labels) if weights is None else weights
    value = weighted_auc(labels, scores, weights)
    pos = fsum(w for b, w in zip(labels, weights) if b)
    neg = fsum(w for b, w in zip(labels, weights) if not b)
    return {"value": value, "numerator": None if value is None else value * pos * neg,
            "denominator": pos * neg, "positive_n": sum(labels), "negative_n": len(labels) - sum(labels),
            "positive_mass": pos, "negative_mass": neg, "eligible_n": len(labels),
            "status": "DEFINED" if value is not None else "UNDEFINED",
            "reason": None if value is not None else ("EMPTY" if not labels else "ONE_CLASS")}


def eligibility(rows):
    observed = [r for r in rows if r["persisted"]]
    labels = [r for r in observed if r["generated_label"] is not None]
    scores = [r for r in observed if r["hnlo_score"] is not None]
    matched = [r for r in labels if r["hnlo_score"] is not None]
    sets = {"P": rows, "O": observed, "L": labels, "F": scores, "J": matched}
    excluded = {}
    for name, eligible in sets.items():
        ids = {r["sample_id"] for r in eligible}
        missing = [r for r in rows if r["sample_id"] not in ids]
        excluded[name] = {"n": len(missing),
                          "by_level": dict(Counter(r["true_level"] for r in missing)),
                          "by_domain": dict(Counter(r["folder_domain"] for r in missing)),
                          "by_reason": dict(Counter(r["native_status"] if not r["persisted"] else
                              "INVALID_AND_MISSING_SCORE" if r["generated_label"] is None and r["hnlo_score"] is None else
                              "INVALID" if r["generated_label"] is None else "MISSING_SCORE" for r in missing))}
    return sets, {"counts": {k: len(v) for k, v in sets.items()}, "excluded": excluded,
                  "membership": {k: membership(r["sample_id"] for r in v) for k, v in sets.items()}}


def ranking(rows, weights=None):
    sets, info = eligibility(rows)
    weights = weights or {r["sample_id"]: 1.0 for r in rows}
    def endpoint(selected, field):
        return auc([r["true_level"] != NORMAL for r in selected],
                   [field(r) for r in selected], [weights[r["sample_id"]] for r in selected])
    out = {"eligibility": info, "hnlo_F": endpoint(sets["F"], lambda r: r["hnlo_score"])}
    signals = {"hnlo": lambda r: r["hnlo_score"],
               "hard": lambda r: int(r["generated_label"] != NORMAL),
               "ordinal": lambda r: 3 - SAFETY_LEVELS.index(r["generated_label"]),
               "always_normal": lambda r: 0, "always_anomaly": lambda r: 1}
    out["paired_J"] = {name: endpoint(sets["J"], signal) for name, signal in signals.items()}
    hnlo = out["paired_J"]["hnlo"]["value"]
    out["delta"] = {}
    for control in ("hard", "ordinal", "always_normal", "always_anomaly"):
        value = out["paired_J"][control]["value"]
        out["delta"][control] = {"value": None if hnlo is None or value is None else hnlo - value,
                                 "status": "UNDEFINED" if hnlo is None or value is None else "DEFINED",
                                 "reason": "UNDEFINED_PAIRED_AUC" if hnlo is None or value is None else None,
                                 "numerator": None, "denominator": None}
    return out


def classification(rows):
    sets, info = eligibility(rows)
    observed = sets["O"]
    result = classification_metrics([SampleRecord(r["sample_id"], r["true_level"]) for r in observed],
                                    [PredictionRecord(r["sample_id"], r["generated_label"]) for r in observed])
    c = dict.fromkeys(("TP", "FN", "FP", "TN", "U_A", "U_N"), 0)
    for r in observed:
        hazard, pred = r["true_level"] != NORMAL, r["generated_label"]
        key = ("U_A" if hazard else "U_N") if pred is None else (
            ("TP" if pred != NORMAL else "FN") if hazard else ("FP" if pred != NORMAL else "TN"))
        c[key] += 1
    a, n = c["TP"] + c["FN"] + c["U_A"], c["TN"] + c["FP"] + c["U_N"]
    result["binary_counts"] = c
    result["rates"] = {
        "accuracy4": ratio(sum(result["confusion_matrix"][l][l] for l in SAFETY_LEVELS), len(observed)),
        "accuracy_binary": ratio(c["TP"] + c["TN"], len(observed)),
        "FNR_observed": ratio(c["FN"], a), "FPR_observed": ratio(c["FP"], n),
        "recall_A": ratio(c["TP"], a), "specificity": ratio(c["TN"], n)}
    present = [l for l in SAFETY_LEVELS if result["support"][l]]
    result["macro_classes"] = present
    result["rates"]["macro_recall"] = ratio(fsum(result["per_class"][l]["recall"] for l in present), len(present))
    result["controls"] = {
        "always_normal": {"accuracy_binary": ratio(n, a + n), "FNR_observed": ratio(a, a), "FPR_observed": ratio(0, n)},
        "always_anomaly": {"accuracy_binary": ratio(a, a + n), "FNR_observed": ratio(0, a), "FPR_observed": ratio(n, n)}}
    result["eligibility"] = info
    return result


def dangerous(rows):
    observed = eligibility(rows)[0]["O"]
    anomaly = [r for r in observed if r["true_level"] != NORMAL]
    severe = [r for r in observed if r["true_level"] == "Level01"]
    l3 = [r for r in observed if r["true_level"] == "Level03"]
    row3 = {p: sum(r["generated_label"] == (None if p == "INVALID" else p) for r in l3)
            for p in (*SAFETY_LEVELS, "INVALID")}
    return {"false_safe": ratio(sum(r["generated_label"] == NORMAL for r in anomaly), len(anomaly)),
            "severe_miss": ratio(sum(r["generated_label"] == NORMAL for r in severe), len(severe)),
            "level03_support": len(l3), "level03_confusion": row3,
            "level03_errors": sum(r["generated_label"] != "Level03" for r in l3),
            "level03_invalid": row3["INVALID"]}


def completion_bounds(rows):
    observed = eligibility(rows)[0]["O"]
    missing = [r for r in rows if not r["persisted"]]
    valid = all(r["generated_label"] in SAFETY_LEVELS for r in observed)
    out = {}
    for name, predicate in (("false_safe", lambda r: r["true_level"] != NORMAL),
                            ("severe_miss", lambda r: r["true_level"] == "Level01")):
        denominator = sum(predicate(r) for r in rows)
        errors = sum(predicate(r) and r["generated_label"] == NORMAL for r in observed)
        unknown = sum(predicate(r) for r in missing)
        out[name] = {"observed_errors": errors, "missing_support": unknown, "denominator": denominator,
                     "lower": errors / denominator if valid and denominator else None,
                     "upper": (errors + unknown) / denominator if valid and denominator else None,
                     "status": "BLOCKED" if not valid else "DEFINED" if denominator else "UNDEFINED",
                     "reason": "BOUND_REQUIRES_ALL_OBSERVED_LABELS_VALID" if not valid else
                               "ZERO_SUPPORT" if not denominator else None,
                     "interpretation": "ASSUMED_COMPLETION_NOT_MEASURED_FULL_TRAIN"}
    return out


def kappa(left, right, binary=False):
    if len(left) != len(right) or any(x not in SAFETY_LEVELS for x in left + right):
        raise ValueError("equal canonical vote vectors required")
    labels = [False, True] if binary else list(SAFETY_LEVELS)
    if binary:
        left, right = [x != NORMAL for x in left], [x != NORMAL for x in right]
    n = len(left)
    agreement = ratio(sum(a == b for a, b in zip(left, right)), n, "EMPTY")
    expected = sum(left.count(l) * right.count(l) for l in labels) / n**2 if n else None
    value = None if expected is None or expected == 1 else (agreement["value"] - expected) / (1 - expected)
    return {"value": value, "observed_agreement": agreement, "expected_agreement": expected,
            "matrix": [[sum(a == x and b == y for a, b in zip(left, right)) for y in labels] for x in labels],
            "status": "DEFINED" if value is not None else "UNDEFINED",
            "reason": "EMPTY" if not n else "EXPECTED_AGREEMENT_ONE" if expected == 1 else None,
            "numerator": None if expected is None else agreement["value"] - expected,
            "denominator": None if expected is None else 1 - expected}


def vote_signals(votes):
    if len(votes) < 2 or any(v not in SAFETY_LEVELS for v in votes):
        raise ValueError("at least two canonical votes required")
    def entropy(values, k):
        return -fsum((c / len(values)) * log(c / len(values)) for c in Counter(values).values()) / log(k)
    pairs = list(combinations(votes, 2))
    return {"H4": entropy(votes, 4), "H2": entropy([v != NORMAL for v in votes], 2),
            "D": fsum(abs(SAFETY_LEVELS.index(a) - SAFETY_LEVELS.index(b)) / 3 for a, b in pairs) / len(pairs)}


def risk_coverage(scores, errors, false_safe, anomalies):
    if not len(scores) == len(errors) == len(false_safe) == len(anomalies):
        raise ValueError("equal curve vector lengths required")
    # Reuse strict numeric/boolean validation, without selecting any threshold.
    weighted_auc(errors, scores)
    if any(type(b) is not bool for b in false_safe + anomalies):
        raise ValueError("boolean curve targets required")
    n, support = len(scores), sum(anomalies)
    out = [{"threshold": None, "retained_n": 0, "coverage": 0.0 if n else None,
            "risk4": ratio(0, 0, "EMPTY_RETAINED"), "residual_FS": ratio(0, support),
            "reason": None if n else "EMPTY_PANEL"}]
    ordered = sorted(zip(scores, errors, false_safe))
    k = e = fs = 0
    from itertools import groupby
    for threshold, group in groupby(ordered, key=lambda item: item[0]):
        block = list(group)
        k += len(block)
        e += sum(x[1] for x in block)
        fs += sum(x[2] for x in block)
        out.append({"threshold": threshold, "retained_n": k, "coverage": k / n,
                    "risk4": ratio(e, k), "residual_FS": ratio(fs, support), "reason": None})
    return out


def disagreement(tables, ids, models, planned_n):
    ids = sorted(ids)
    joint = [sid for sid in ids if all(tables[m][sid]["persisted"] and
             tables[m][sid]["generated_label"] is not None for m in models)]
    combinations_missing = Counter("|".join(m + ":" + (tables[m][s]["native_status"] if not tables[m][s]["persisted"]
        else "INVALID" if tables[m][s]["generated_label"] is None else "VALID") for m in models) for s in ids)
    votes = {s: [tables[m][s]["generated_label"] for m in models] for s in joint}
    signals = {s: vote_signals(v) for s, v in votes.items()}
    errors = {m: {s: tables[m][s]["generated_label"] != tables[m][s]["true_level"] for s in joint} for m in models}
    fs = {m: {s: tables[m][s]["true_level"] != NORMAL and tables[m][s]["generated_label"] == NORMAL for s in joint} for m in models}
    binary_errors = {m: {s: (tables[m][s]["generated_label"] != NORMAL) != (tables[m][s]["true_level"] != NORMAL)
                         for s in joint} for m in models}
    severe = {m: {s: tables[m][s]["true_level"] == "Level01" and tables[m][s]["generated_label"] == NORMAL
                  for s in joint} for m in models}
    anomaly_n = sum(tables[models[0]][s]["true_level"] != NORMAL for s in joint)
    all_errors = sum(all(errors[m][s] for m in models) for s in joint)
    out = {"models": models, "panel_n": len(ids), "joint_ids": joint, "membership_sha256": membership(joint),
           "joint_parse": ratio(len(joint), len(ids), "EMPTY"), "joint_to_parent_planned": ratio(len(joint), planned_n),
           "missing_invalid_combinations": dict(sorted(combinations_missing.items())),
           "unanimous4": ratio(sum(len(set(v)) == 1 for v in votes.values()), len(joint), "EMPTY"),
           "unanimous2": ratio(sum(len({x != NORMAL for x in v}) == 1 for v in votes.values()), len(joint), "EMPTY"),
           "pairwise": {}, "signals": signals, "errors4": errors, "errors_binary": binary_errors,
           "false_safe": fs, "severe_miss": severe,
           "shared_all_error": ratio(all_errors, len(joint)),
           "shared_false_safe": ratio(sum(all(fs[m][s] for m in models) for s in joint), anomaly_n),
           "unanimous_wrong4": ratio(sum(len(set(votes[s])) == 1 and all(errors[m][s] for m in models) for s in joint), len(joint)),
           "complementarity": {}}
    for a, b in combinations(models, 2):
        left, right = [tables[a][s]["generated_label"] for s in joint], [tables[b][s]["generated_label"] for s in joint]
        out["pairwise"][a + "|" + b] = {"kappa4": kappa(left, right), "kappa2": kappa(left, right, True)}
    for a, b in permutations(models, 2):
        only_a = sum(errors[a][s] and not errors[b][s] for s in joint)
        out["complementarity"][a + "->" + b] = {**ratio(only_a, sum(errors[a].values())),
            "both_wrong": sum(errors[a][s] and errors[b][s] for s in joint), "only_first_wrong": only_a,
            "only_second_wrong": sum(errors[b][s] and not errors[a][s] for s in joint)}
    if "qwen3" not in models:
        return out
    q3 = tables["qwen3"]
    b04 = [s for s in joint if q3[s]["generated_label"] == NORMAL]
    matched = [s for s in b04 if q3[s]["hnlo_score"] is not None]
    out["B04"] = {"ids": b04, "matched_signal_ids": matched, "e4_equals_eFS": True,
                   "membership_sha256": membership(b04), "matched_membership_sha256": membership(matched)}
    out["association"] = {}
    for panel, selected, names in (("joint", joint, ("H4", "H2", "D")),
                                   ("B04", b04, ("H4", "H2", "D")),
                                   ("B04_matched", matched, ("H4", "H2", "D", "HNLO_Q3"))):
        panel_result = {"ids": selected, "membership_sha256": membership(selected),
                        "panel_to_planned": ratio(len(selected), planned_n), "signals": {}}
        for name in names:
            score = [q3[s]["hnlo_score"] if name == "HNLO_Q3" else signals[s][name] for s in selected]
            e, f = [errors["qwen3"][s] for s in selected], [fs["qwen3"][s] for s in selected]
            a = [q3[s]["true_level"] != NORMAL for s in selected]
            panel_result["signals"][name] = {"distinct_scores": len(set(score)),
                "min": min(score, default=None), "max": max(score, default=None),
                "error4_auc": auc(e, score), "false_safe_auc": auc(f, score)}
            if panel != "B04":  # curves share all signals' eligible IDs as locked in section 6
                panel_result["signals"][name]["risk_coverage"] = risk_coverage(score, e, f, a)
        out["association"][panel] = panel_result
    out["hnlo_true_predicted_binary"] = {}
    for true_a in (False, True):
        for pred_a in (False, True):
            selected = [s for s in joint if q3[s]["hnlo_score"] is not None and
                        (q3[s]["true_level"] != NORMAL) == true_a and (q3[s]["generated_label"] != NORMAL) == pred_a]
            values = [q3[s]["hnlo_score"] for s in selected]
            out["hnlo_true_predicted_binary"][f"true_{int(true_a)}_pred_{int(pred_a)}"] = {
                "n": len(values), "min": min(values, default=None), "median": finite_median(values),
                "max": max(values, default=None), "reason": None if values else "EMPTY"}
    out["hnlo_global_error_detection"] = {"status": "NOT_IN_V1", "value": None, "reason": "NO_APPROVED_DIRECTION"}
    return out


def group_variants(meta, near_edges, variants):
    ids = sorted(meta)
    def partition(field, allow_empty=False):
        groups = defaultdict(list)
        for sid in ids:
            value = meta[sid][field]
            if value in (None, "") and allow_empty:
                continue
            if not isinstance(value, str) or not value.strip():
                raise ValueError("invalid grouping key")
            groups[value].append(sid)
        return [(g[0], s) for g in groups.values() for s in g[1:]]
    exact = partition("byte_sha256")
    if components(ids, exact) != components(ids, partition("pixel_sha256")):
        raise ValueError("byte/pixel partition mismatch")
    edges = {"exact": exact, "point": partition("point_id", True), "family": partition("source_family", True), "near8": []}
    for a, b, distance in near_edges:
        if type(distance) is not int or distance < 0 or a == b:
            raise ValueError("invalid saved near edge")
        if a in meta and b in meta and distance <= 8:
            edges["near8"].append((a, b))
    result = {}
    for variant in variants:
        keys = [] if variant == "image" else ["exact"] if variant.startswith("exact_representative_") else variant.split("_")
        mapping = components(ids, [e for k in keys for e in edges[k]])
        sizes = Counter(mapping.values())
        weights = {s: 1 / sizes[mapping[s]] for s in ids}
        if variant.startswith("exact_representative_"):
            groups = defaultdict(list)
            for s in ids:
                groups[mapping[s]].append(s)
            weights = {g[0 if variant.endswith("first") else -1]: 1.0 for g in groups.values()}
        result[variant] = (mapping, weights)
    return result


def sensitivity(meta, tables, ids, models, near_edges, config):
    subset = {s: meta[s] for s in sorted(ids)}
    result = {}
    for variant, (mapping, weights) in group_variants(subset, near_edges, config["sensitivity"]["variants"]).items():
        legacy_meta = {s: {**r, "safety_level": r["true_level"]} for s, r in subset.items()}
        strata = {}
        for domain in ["ALL", *config["domains"]]:
            selected = [s for s in sorted(weights) if domain == "ALL" or meta[s]["folder_domain"] == domain]
            strata[domain] = {"n_images": len(selected), "membership_sha256": membership(selected),
                             "models": {m: ranking([tables[m][s] for s in selected], weights) for m in models}}
            strata[domain]["models"]["moondream2"] = na_model()
        result[variant] = {"group_summary": summarize_groups(legacy_meta, mapping), "weights": weights,
                           "mapping": mapping, "strata": strata}
    exact = defaultdict(list)
    for s, r in subset.items():
        exact[r["byte_sha256"]].append(s)
    consistency = []
    for key, group in sorted(exact.items()):
        if len(group) < 2:
            continue
        per_model = {}
        for model in models:
            rows = [tables[model][s] for s in group]
            scores = [r["hnlo_score"] for r in rows if r["hnlo_score"] is not None]
            spread = max(scores) - min(scores) if scores else None
            per_model[model] = {"score_available_n": len(scores),
                "score_spread": spread if spread is None or isfinite(spread) else None,
                "score_spread_reason": "NO_SCORES" if spread is None else "NUMERIC_OVERFLOW" if not isfinite(spread) else None,
                "distinct_generated_labels": len({r["generated_label"] for r in rows}),
                "within_group_hazard_auc": ranking(rows)["hnlo_F"]}
        per_model["moondream2"] = na_model()
        consistency.append({"byte_sha256": key, "ids": sorted(group), "models": per_model})
    return {"variants": result, "exact_consistency": consistency}


def na_model():
    return {"model_id": "moondream2", "value": None, "status": "N/A",
            "reason": "NO_AUDITED_COMPATIBLE_HNLO_TRAIN_RUN", "authority": "DEC-20261026-M1:A4",
            "course_exception_verified": False}


def analyze(metadata, reports, near_edges, config):
    meta, tables = validate_ledger(metadata, reports, config)
    full = sorted(meta)
    common = [s for s in full if tables["qwen3"][s]["native_status"] == "SUCCESS"]
    missing = sorted(set(full) - set(common))
    # Names identify protocol roles, never claim the toy fixture has 3763/3539 images.
    cohorts = {"T3763": full, "V3539": common, "M224": missing}
    members = {k: {"notice": NOTICE, "ids": v, "n": len(v), "membership_sha256": membership(v),
                    "protocol_expected_real_n_NOT_VALIDATED": config["cohorts"][k]["expected_n"]}
               for k, v in cohorts.items()}
    members["REC224"] = {"notice": NOTICE, "status": "REFERENCE_ONLY", "ids": None,
                         "baseline_pooling_allowed": False, "reanalyze_enabled": False}
    r1, ledger, r2, r3, r4 = [], [], {}, {}, {}
    for cohort in ("T3763", "V3539"):
        ids = cohorts[cohort]
        models = config["cohorts"][cohort]["models"]
        r2[cohort], r3[cohort] = {}, {}
        for model in MODELS:
            for s in ids:
                r = tables[model][s]
                ledger.append({"notice": NOTICE, "cohort_id": cohort, **r})
        for domain in ["ALL", *config["domains"]]:
            selected = [s for s in ids if domain == "ALL" or meta[s]["folder_domain"] == domain]
            r2[cohort][domain], r3[cohort][domain] = {}, {}
            for model in MODELS:
                rows = [tables[model][s] for s in selected]
                sets, info = eligibility(rows)
                observed = len(sets["O"])
                invalid = observed - len(sets["L"])
                r1.append({"notice": NOTICE, "cohort_id": cohort, "model_id": model, "stratum": domain,
                    "planned_n": len(rows), "attempted_n": sum(r["attempted"] for r in rows),
                    **{s: sum(r["native_status"] == s for r in rows) for s in ("SUCCESS", "TECHNICAL_ERROR", "NOT_ATTEMPTED")},
                    "observed_n": observed, "label_valid_n": len(sets["L"]), "score_valid_n": len(sets["F"]),
                    "matched_n": len(sets["J"]), "invalid_n": invalid, "missing_score_n": observed - len(sets["F"]),
                    "output_coverage": ratio(observed, len(rows)), "label_coverage": ratio(len(sets["L"]), len(rows)),
                    "score_coverage": ratio(len(sets["F"]), len(rows)), "invalid_rate": ratio(invalid, observed),
                    "attempt_coverage": ratio(sum(r["attempted"] for r in rows), len(rows)),
                    "exclusions": info["excluded"], "membership_sha256": membership(selected),
                    "run_refs": sorted({r["run_id"] for r in rows}),
                    "input_refs": sorted({r["input_ref"] for r in rows}),
                    "provenance": [dict(zip(("revision", "release", "run_id", "attempt_id", "source_commit", "config_sha256"), identity))
                                   for identity in sorted({tuple(r[k] for k in ("revision", "release", "run_id", "attempt_id", "source_commit", "config_sha256")) for r in rows})],
                    "evidence_level": "SYNTHETIC", "status": "SYNTHETIC"})
                if model in models:
                    r2[cohort][domain][model] = {"classification": classification(rows), "ranking": ranking(rows)}
                    r3[cohort][domain][model] = dangerous(rows)
            r1.append({"notice": NOTICE, "cohort_id": cohort, "stratum": domain, **na_model(),
                       "planned_n": None, "observed_n": None, "membership_sha256": membership([]), "evidence_level": "N/A"})
            r2[cohort][domain]["moondream2"] = na_model()
            r3[cohort][domain]["moondream2"] = na_model()
    r1.append({"notice": NOTICE, "cohort_id": "REC224", "model_id": "qwen3", "stratum": "ALL",
               "status": "REFERENCE_ONLY", "reason": "RECOVERY_NOT_REANALYZED_OR_POOLED", "planned_n": None,
               "observed_n": None, "evidence_level": "N/A", "membership_sha256": membership([])})
    r3["completion_bounds"] = {d: completion_bounds([tables["qwen3"][s] for s in full
        if d == "ALL" or meta[s]["folder_domain"] == d]) for d in ["ALL", *config["domains"]]}
    r3["missing_composition"] = {d: {l: sum(meta[s]["true_level"] == l and
        (d == "ALL" or meta[s]["folder_domain"] == d) for s in missing) for l in SAFETY_LEVELS}
        for d in ["ALL", *config["domains"]]}
    r3["sensitivity"] = {c: sensitivity(meta, tables, cohorts[c], config["cohorts"][c]["models"], near_edges, config)
                         for c in ("T3763", "V3539")}
    r3["B01"] = [{"placeholder_id": f"atom_{i + 1:02d}" if i < 12 else f"group_{chr(65 + i - 12)}",
                  "status": "BLOCKED", "value": None, "reason": "B01_NO_AUTHORIZED_SAMPLE_HAZARD_MAP"} for i in range(19)]
    r3["B05"] = {"status": "BLOCKED", "value": None, "reason": "MISMATCH_PROXY_MAPPING_UNAVAILABLE"}
    for panel in config["disagreement_panels"]:
        r4[panel["id"]] = {}
        for domain in ["ALL", *config["domains"]]:
            ids = [s for s in cohorts[panel["cohort"]] if domain == "ALL" or meta[s]["folder_domain"] == domain]
            planned_n = sum(domain == "ALL" or r["folder_domain"] == domain for r in meta.values())
            r4[panel["id"]][domain] = disagreement(tables, ids, panel["models"], planned_n)
    r4["moondream2"] = na_model()
    r2["B02"] = {"status": "N/A", "value": None, "reason": "CONTINUOUS_LOGIT_CONTROLS_NOT_AVAILABLE"}
    return {"notice": NOTICE, "memberships": members, "ledger": ledger, "R1": r1, "R2": r2, "R3": r3, "R4": r4}


def long_rows(report_id, content, context):
    """Stable key-based rows; structured arrays remain in JSON with trace paths.

    Context includes explicit eligibility/provenance. Numeric leaves that are
    counts stay counts (no invented denominator); ratios carry their own units.
    """
    result = []
    def walk(value, path, inherited=None):
        if isinstance(value, dict):
            if "value" in value and "status" in value:
                add(value, path)
            else:
                for key in sorted(value):
                    walk(value[key], path + [str(key)], value if "status" in value else inherited)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, path + [str(i)], inherited)
        elif type(value) in (int, float) or value is None:
            status = "DEFINED" if value is not None else "UNDEFINED"
            reason = None if value is not None else "NOT_AVAILABLE_IN_CONTEXT"
            if value is None and inherited and inherited.get("status") in ("BLOCKED", "N/A", "UNDEFINED", "NOT_IN_V1"):
                status, reason = inherited["status"], inherited.get("reason") or reason
            add({"value": value, "status": status, "reason": reason}, path)

    def add(value, path):
        key = [report_id, *path]
        result.append({**context, "notice": NOTICE, "output_id": report_id,
                       "row_id": report_id + "_" + sha256(json_bytes(key))[:20],
                       "metric_id": "/".join(path), "signal_id": next((p for p in path if p in ("H4", "H2", "D", "HNLO_Q3", "hnlo", "hard", "ordinal")), ""),
                       "variant_id": context.get("variant_id", ""),
                       "numerator": value.get("numerator"), "denominator": value.get("denominator"),
                       "value": value["value"], "status": value["status"], "reason": value.get("reason"),
                       "positive_n": value.get("positive_n"), "negative_n": value.get("negative_n"),
                       "eligible_n": value.get("eligible_n", context.get("eligible_n")),
                       "json_pointer": "/" + "/".join(p.replace("~", "~0").replace("/", "~1") for p in path)})
    walk(content, [])
    return result
