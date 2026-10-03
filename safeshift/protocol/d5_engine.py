"""DEC-W2-D5-005 and approved RQ2 erratum, using in-memory records only.

None means NA, never zero. No dataset paths, loaders, execution or model imports.
Support-only macro summaries are descriptive; cross-domain comparisons use
class-conditional recall. Bootstrap callers must fix the original class support.
"""

from collections import Counter
from statistics import median

from .d5_geometry import assignment, containment, iou, pointing, polygon, polygon_area, valid_box
from .metrics import METRIC_ENGINE_VERSION
from .schema import HAZARDS, SAFETY_LEVELS

# D6 brief section 11; secondary exploratory unions of IMAGE memberships.
GROUPS = {
    "A_FIRE_AND_SMOKE": ("OPEN_FLAME", "SMOKE"),
    "B_PPE_ABSENCE": ("NO_GLOVES", "NO_HELMET", "NO_MASK"),
    "C_UNAUTHORIZED_BEHAVIOR": ("USE_MOBILE_PHONE", "SMOKING"),
    "D_ENVIRONMENTAL_SLIP_HAZARD": ("LIQUID_ON_GROUND",),
    "E_OBSTRUCTION_AND_FOREIGN_OBJECT": ("FOREIGN_OBJECT", "NONMOTORIZED_VEHICLE"),
    "F_EQUIPMENT_STATE_ANOMALY": ("DOOR_OPEN",),
    "G_PERSONNEL_FALLEN": ("PERSON_FALLEN",),
}


def rate(k, n):
    return {"value": k / n if n else None, "numerator": k, "denominator": n}


def mean(values):
    return sum(values) / len(values) if values else None


def _pred(sample):
    return sample.prediction.value.safety_level if sample.prediction.success else None


def classification(samples, *, required_classes=None):
    """Missing GT classes are NA, with support-only descriptive macro metrics.

    D5 does not define a classification abstention-to-label mapping. If a Call-1
    parse fails, label-dependent metrics fail closed to NA (no invented Level04).
    The observed matrix, support, exact errors and parse rate remain available.
    """
    samples = tuple(samples)
    if any(_pred(s) is not None and _pred(s) not in SAFETY_LEVELS for s in samples):
        raise ValueError("noncanonical classification")
    support = Counter(s.true_safety_level for s in samples)
    counts = {a: {b: 0 for b in (*SAFETY_LEVELS, "INVALID")} for a in SAFETY_LEVELS}
    for s in samples:
        counts[s.true_safety_level][_pred(s) or "INVALID"] += 1
    failures = sum(not s.prediction.success for s in samples)
    per_class = {}
    for c in SAFETY_LEVELS:
        tp = counts[c][c]
        predicted = sum(counts[a][c] for a in SAFETY_LEVELS)
        n = support[c]
        per_class[c] = {"support": n, "true_positive": tp,
                        "precision": tp / predicted if predicted else 0.,
                        "recall": tp / n if n else None,
                        "f1": 2 * tp / (n + predicted) if n else None}
    classes = tuple(required_classes) if required_classes is not None else tuple(c for c in SAFETY_LEVELS if support[c])
    if not set(classes) <= set(SAFETY_LEVELS) or len(classes) != len(set(classes)):
        raise ValueError("invalid evaluation classes")
    missing = any(not support[c] for c in classes)
    ba = None if missing else mean([per_class[c]["recall"] for c in classes])
    f1 = None if missing else mean([per_class[c]["f1"] for c in classes])
    normal = support["Level04"]
    anomaly = len(samples) - normal
    anomaly_miss = sum(counts[c]["Level04"] for c in SAFETY_LEVELS[:3])
    anomaly_hit = sum(counts[c][p] for c in SAFETY_LEVELS[:3] for p in SAFETY_LEVELS[:3])
    correct = sum(counts[c][c] for c in SAFETY_LEVELS)
    result = {
        "n_images": len(samples), "K": sum(bool(support[c]) for c in SAFETY_LEVELS),
        "evaluation_classes": list(classes), "support": dict(zip(SAFETY_LEVELS, (support[c] for c in SAFETY_LEVELS))),
        "balanced_accuracy": ba, "macro_f1": f1,
        "macro_scope": "SUPPORT_ONLY_DESCRIPTIVE" if required_classes is None else "FIXED_CLASS_SUPPORT",
        "comparability_warning": "Compare macro metrics only with identical class support; RQ1 uses class recall.",
        "raw_accuracy_descriptive": rate(correct, len(samples)), "per_class": per_class,
        "anomaly_recall": rate(anomaly_hit, anomaly), "anomaly_fnr": rate(anomaly_miss, anomaly),
        "anomaly_fpr": rate(sum(counts["Level04"][c] for c in SAFETY_LEVELS[:3]), normal),
        "level01_recall": rate(counts["Level01"]["Level01"], support["Level01"]),
        "level01_fnr": rate(support["Level01"] - counts["Level01"]["Level01"], support["Level01"]),
        "critical_miss_rate": rate(counts["Level01"]["Level04"], support["Level01"]),
        "critical_downgrade_rate": rate(counts["Level01"]["Level02"] + counts["Level01"]["Level03"], support["Level01"]),
        "exact_safety_level_error_rate": rate(len(samples) - correct, len(samples)),
        "confusion_matrix": counts,
        "row_normalized_confusion_matrix": {a: {b: v / support[a] if support[a] else None
                                                for b, v in row.items()} for a, row in counts.items()},
        "prediction_distribution": {p: sum(counts[c][p] for c in SAFETY_LEVELS) for p in (*SAFETY_LEVELS, "INVALID")},
        "parse_success_rate": rate(len(samples) - failures, len(samples)), "parse_failures": failures,
        "status": "CLASSIFICATION_PARSE_FAILURE_POLICY_BLOCKER" if failures else "COMPUTED",
    }
    if failures:
        result["balanced_accuracy"] = result["macro_f1"] = None
        for c in per_class.values():
            c.update(precision=None, recall=None, f1=None)
        for key in ("raw_accuracy_descriptive", "anomaly_recall", "anomaly_fnr", "anomaly_fpr",
                    "level01_recall", "level01_fnr", "critical_miss_rate", "critical_downgrade_rate"):
            result[key]["value"] = None
            result[key]["status"] = "NA_PENDING_CLASSIFICATION_PARSE_FAILURE_POLICY"
    return result


def _spread(values):
    values = [v for v in values if v is not None]
    return max(values) - min(values) if len(values) >= 2 else None


def rq1(samples):
    samples = tuple(samples)
    pooled = classification(samples)
    domains = {d: classification(tuple(s for s in samples if s.domain == d))
               for d in sorted({s.domain for s in samples})}
    by_class = {}
    for c in SAFETY_LEVELS:
        rows = []
        for d, summary in domains.items():
            r = summary["per_class"][c]
            recall, pooled_recall = r["recall"], pooled["per_class"][c]["recall"]
            rows.append({"domain": d, **r,
                         "pooled_to_domain_gap": pooled_recall - recall if recall is not None and pooled_recall is not None else None,
                         "warning": "Sparse-Support / Descriptive-Only" if d == "metallurgy" and c != "Level04" else None})
        comparable = [r for r in rows if r["recall"] is not None]
        worst = min((r["recall"] for r in comparable), default=None)
        gaps = [r["pooled_to_domain_gap"] for r in rows if r["pooled_to_domain_gap"] is not None]
        by_class[c] = {"domains": rows, "domain_spread": _spread([r["recall"] for r in rows]),
                       "worst_adverse_gap": max(gaps) if gaps else None,
                       "observed_worst_domain_minimum": worst,
                       "observed_worst_domains": [r for r in comparable if r["recall"] == worst],
                       "ci_status": "ATTACH_DOMAIN_STRATIFIED_POINT_CLUSTER_BOOTSTRAP"}
    return {"pooled": pooled, "domains": domains, "class_conditional": by_class,
            "balanced_accuracy_spread_diagnostic": _spread([v["balanced_accuracy"] for v in domains.values() if v["K"] == 4]),
            "balanced_accuracy_comparable_domains": [d for d, v in domains.items() if v["K"] == 4],
            "anomaly_recall_spread_diagnostic": _spread([v["anomaly_recall"]["value"] for v in domains.values()])}


def rq2(samples, *, grouped=False):
    samples = tuple(samples)
    groups = GROUPS if grouped else {h: (h,) for h in HAZARDS}
    rows = {}
    for name, members in groups.items():
        subset = tuple(s for s in samples if s.rq2_atom_memberships.intersection(members))
        row = classification(subset)
        row["anomaly_to_normal_miss_rate"] = rate(sum(_pred(s) == "Level04" for s in subset), len(subset))
        if row["parse_failures"]:
            row["anomaly_to_normal_miss_rate"]["value"] = None
        row["warning"] = "Sparse-Support / Descriptive-Only" if set(members).intersection({"PERSON_FALLEN", "DOOR_OPEN"}) else None
        rows[name] = row
    return {"analysis_level": "SECONDARY_EXPLORATORY" if grouped else "PRIMARY_HAZARD_ATOMS",
            "prediction_unit": "IMAGE", "non_independent": True, "counts_additive": False,
            "unique_input_images": len({s.sample_id for s in samples}), "strata": rows,
            "aggregation_across_strata": "FORBIDDEN", "ci_status": "ATTACH_IMAGE_CLUSTER_BOOTSTRAP"}


def _participation(samples):
    states = {s.participation == "PARTICIPATING" for s in samples}
    if len(states) > 1:
        raise ValueError("do not mix participants and nonparticipants")
    return not states or True in states


def _boxes(sample):
    if not sample.prediction.success:
        return ()
    hazards = sample.prediction.value.hazards
    if any(h.hazard_type not in HAZARDS for h in hazards):
        raise ValueError("unknown predicted hazard")
    boxes = tuple((h.hazard_type, valid_box(e.bbox)) for h in hazards for e in h.evidence)
    if (sample.prediction.boxes_attempted != len(boxes)
            or sample.prediction.boxes_valid != len(boxes)):
        raise ValueError("successful response box counts must match canonical evidence")
    return boxes


def _weights(atoms, boxes):
    return [[max(iou(box, valid_box(r.derived_bbox)) for r in atom.candidate_regions)
             if hazard == atom.hazard_type else None for hazard, box in boxes] for atom in atoms]


def _psr(samples):
    for s in samples:
        p = s.prediction
        if (type(p.boxes_valid) is not int or p.boxes_valid < 0
                or p.boxes_attempted is not None and (type(p.boxes_attempted) is not int or p.boxes_attempted < p.boxes_valid)):
            raise ValueError("nonnegative, consistent integer box parse counts required")
    attempted = sum(s.prediction.boxes_attempted or 0 for s in samples)
    valid = sum(s.prediction.boxes_valid for s in samples)
    if valid > attempted:
        raise ValueError("inconsistent box parse counts")
    return {"PSR_response": rate(sum(s.prediction.response_schema_valid for s in samples), len(samples)),
            "PSR_box": rate(valid, attempted),
            "responses_without_box_denominator": sum(s.prediction.boxes_attempted is None for s in samples)}


def direct_grounding(samples):
    samples = tuple(samples)
    if not _participation(samples):
        return {"participation": "NOT_PARTICIPATING", "metrics": None}
    values, conditional, pointing_values, covariates = [], [], [], []
    per_hazard = {h: {"gt": 0, "predicted": 0, "tp@0.25": 0, "tp@0.50": 0} for h in HAZARDS}
    thresholds = {t: {"tp": 0, "cgi_samples": 0, "cgi_atoms": 0, "correct_samples": 0, "correct_atoms": 0} for t in (.25, .5)}
    frequency = Counter(a.hazard_type for s in samples for a in s.direct_atoms)
    missing_cgi = 0
    diagnostic_unavailable = 0
    for s in samples:
        atoms, boxes = s.direct_atoms, _boxes(s)
        if any(h not in HAZARDS for h, _ in boxes):
            raise ValueError("unknown predicted hazard")
        weights = _weights(atoms, boxes)
        mode_a = assignment(weights)
        matched = {j: (p, score) for j, p, score in mode_a}
        values.extend(matched[j][1] if j in matched else 0. for j in range(len(atoms)))
        # Keep the COMPLETE prediction list, including unmatched claims. GT
        # support exclusions never become a filter over predicted-box counts.
        direct_boxes = [(p, box) for p, (_, box) in enumerate(boxes)]
        diagnostic_boxes = boxes if s.prediction.success else tuple(
            (h.hazard_type, valid_box(e.bbox)) for h in s.diagnostic_hazards for e in h.evidence)
        diagnostic_matches = mode_a if s.prediction.success else assignment(_weights(atoms, diagnostic_boxes))
        score_by_prediction = {p: score for _, p, score in diagnostic_matches}
        conditional.extend(score_by_prediction.get(p, 0.) for p in range(len(diagnostic_boxes)))
        if not s.prediction.success and s.prediction.boxes_valid and not s.diagnostic_hazards:
            # Existing ParseResult loses hazard identity for diagnostic_evidence.
            # Never fabricate that identity from free-text Evidence.label.
            diagnostic_unavailable += s.prediction.boxes_valid
        for j, atom in enumerate(atoms):
            per_hazard[atom.hazard_type]["gt"] += 1
            pointing_values.append(bool(j in matched and pointing(boxes[matched[j][0]][1], atom.candidate_regions)))
            covariates.append({"sample_id": s.sample_id, "atom_id": atom.atom_id,
                               "hazard_type": atom.hazard_type,
                               "AtomSize": max(polygon_area(polygon(r)) for r in atom.candidate_regions),
                               "candidate_region_count": len(atom.candidate_regions),
                               "hazard_frequency_N": frequency[atom.hazard_type]})
        for p, _ in direct_boxes:
            per_hazard[boxes[p][0]]["predicted"] += 1
        if atoms and s.classification_correct is None:
            missing_cgi += 1
        for threshold, aggregate in thresholds.items():
            mode_b = assignment(weights, threshold=threshold)
            aggregate["tp"] += len(mode_b)
            for j, _, _ in mode_b:
                per_hazard[atoms[j].hazard_type][f"tp@{threshold:.2f}"] += 1
            if atoms and s.classification_correct is True:
                aggregate["correct_samples"] += 1
                aggregate["correct_atoms"] += len(atoms)
                aggregate["cgi_samples"] += not mode_b
                aggregate["cgi_atoms"] += len(atoms) - len(mode_b)
    n, predicted = len(values), sum(r["predicted"] for r in per_hazard.values())
    # A failed response receives no E2E matches. Retain every attempted box in
    # precision's denominator when known; unknown counts must not inflate it.
    failed_boxes = sum(s.prediction.boxes_attempted or 0 for s in samples if not s.prediction.success)
    unknown_box_counts = sum(s.prediction.boxes_attempted is None for s in samples if not s.prediction.success)
    predicted += failed_boxes
    threshold_results = {}
    for t, a in thresholds.items():
        row = {"Hit": rate(a["tp"], n), "evidence_precision": rate(a["tp"], predicted),
               "evidence_recall": rate(a["tp"], n), "evidence_f1": rate(2 * a["tp"], predicted + n),
               "CGI_zero_grounding": rate(a["cgi_samples"], a["correct_samples"]),
               "CGI_atom": rate(a["cgi_atoms"], a["correct_atoms"])}
        if missing_cgi:
            row["CGI_zero_grounding"]["value"] = row["CGI_atom"]["value"] = None
        if unknown_box_counts:
            row["evidence_precision"]["value"] = row["evidence_f1"]["value"] = None
        row["per_hazard"] = {h: {"evidence_precision": rate(r[f"tp@{t:.2f}"], r["predicted"]),
                                  "evidence_recall": rate(r[f"tp@{t:.2f}"], r["gt"]),
                                  "evidence_f1": rate(2 * r[f"tp@{t:.2f}"], r["predicted"] + r["gt"])}
                             for h, r in per_hazard.items()}
        if any(not s.prediction.success for s in samples):
            # Failed native envelopes may not retain class identities for every
            # attempted item. Do not silently omit those from per-hazard precision.
            for hazard in row["per_hazard"].values():
                hazard["evidence_precision"]["value"] = hazard["evidence_f1"]["value"] = None
        threshold_results[f"@{t:.2f}"] = row
    return {"participation": "PARTICIPATING", "track": "DIRECT_RQ3_A", "n_atoms": n,
            "end_to_end_mean_iou": mean(values), "median_iou": median(values) if values else None,
            "parse_conditional_mean_iou": None if diagnostic_unavailable else mean(conditional),
            "parse_conditional_n_boxes": len(conditional), "diagnostic_boxes_without_hazard_identity": diagnostic_unavailable,
            "pointing_hit": rate(sum(pointing_values), n), "thresholds": threshold_results,
            "missing_classification_correctness": missing_cgi,
            "failed_response_attempted_boxes": failed_boxes, "unknown_failed_box_counts": unknown_box_counts,
            "unsupported_atoms_excluded": sum(len(s.unsupported_atoms) for s in samples),
            "covariates": covariates, "annotation_relative": True, "unmatched_is_hallucination": False,
            **_psr(samples)}


def weak_proxy(samples):
    samples = tuple(samples)
    if not _participation(samples):
        return {"participation": "NOT_PARTICIPATING", "metrics": None}
    hits, containments, single_hits, single_containments = [], [], [], []
    for s in samples:
        boxes = _boxes(s)
        for atom in s.weak_proxy_atoms:
            candidates = [b for h, b in boxes if h == atom.hazard_type]
            hit = any(pointing(b, atom.candidate_regions) for b in candidates)
            contained = max((containment(b, r) for b in candidates for r in atom.candidate_regions), default=0.)
            hits.append(hit)
            containments.append(contained)
            if len({r.region_id for r in atom.candidate_regions}) == 1:
                single_hits.append(hit)
                single_containments.append(contained)
    return {"participation": "PARTICIPATING", "track": "WEAK_PROXY_RQ3_B", "identity_agnostic": True,
            "true_grounding_accuracy": False, "center_in_proxy_PLC": rate(sum(hits), len(hits)),
            "box_containment_diagnostic": mean(containments),
            "single_person_proxy_subset": {"center_in_proxy_PLC": rate(sum(single_hits), len(single_hits)),
                                           "box_containment_diagnostic": mean(single_containments)},
            "unsupported_atoms_excluded": sum(len(s.unsupported_atoms) for s in samples), **_psr(samples)}


class D5MetricEngine:
    version = METRIC_ENGINE_VERSION
    classification = staticmethod(classification)
    rq1 = staticmethod(rq1)
    rq2 = staticmethod(rq2)
    direct_grounding = staticmethod(direct_grounding)
    weak_proxy = staticmethod(weak_proxy)
