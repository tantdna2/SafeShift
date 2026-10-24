"""PROPOSED retrospective weighting, never an approved benchmark estimator.

Scores and labels stay at image level. Each assumed group receives total mass
one, shared equally by its members. No majority label, group score, threshold,
source identity claim, confidence interval or independence assumption is added.
"""

from collections import Counter, defaultdict
from itertools import groupby
from math import fsum, isfinite

from safeshift.data.schema import SAFETY_LEVELS


def weighted_auc(labels, scores, weights=None):
    """Weighted positive-negative concordance; exact ties receive half credit.

    Return None for empty/single-class input. This global image-pair estimand
    also compares images in different groups, including single-class groups.
    """
    labels, scores = list(labels), list(scores)
    weights = [1.0] * len(labels) if weights is None else list(weights)
    if not len(labels) == len(scores) == len(weights):
        raise ValueError("equal vector lengths required")
    if any(type(y) is not bool for y in labels):
        raise ValueError("boolean labels required")
    if any(type(x) not in (int, float) or not isfinite(x) for x in scores):
        raise ValueError("finite scores required")
    if any(type(w) not in (int, float) or not isfinite(w) or w <= 0 for w in weights):
        raise ValueError("finite positive weights required")
    positive = fsum(w for y, w in zip(labels, weights) if y)
    negative = fsum(w for y, w in zip(labels, weights) if not y)
    if not positive or not negative:
        return None
    below, contributions = 0.0, []
    for _, tied in groupby(sorted(zip(scores, labels, weights)), key=lambda x: x[0]):
        tied = list(tied)
        pos = fsum(w for _, y, w in tied if y)
        neg = fsum(w for _, y, w in tied if not y)
        contributions.append((pos / positive) * ((below + neg / 2) / negative))
        below = fsum((below, neg))
    return fsum(contributions)


def index_rows(rows, label_field):
    """Reject duplicate IDs rather than overwrite records or alter coverage."""
    result = {}
    for row in rows:
        sid = row["sample_id"]
        if not isinstance(sid, str) or not sid.strip() or sid in result:
            raise ValueError("nonempty unique sample_id required")
        if row[label_field] not in SAFETY_LEVELS:
            raise ValueError("canonical label required")
        result[sid] = row
    if not result:
        raise ValueError("nonempty cohort required")
    return result


def join_reports(metadata, reports):
    """Exact ID/label/domain join of existing TRAIN metadata and saved reports.

    Partial/non-SUCCESS reports are rejected, never silently intersected away.
    Coverage must be established before this complete-case analysis is used.
    """
    meta = index_rows(metadata, "safety_level")
    if any(r["split"] != "train" for r in meta.values()):
        raise ValueError("TRAIN metadata only")
    if not reports:
        raise ValueError("at least one saved report required")
    indexed = {}
    for model, rows in reports.items():
        table = index_rows(rows, "true_level")
        if set(table) != set(meta):
            raise ValueError("exact cohort ID equality required")
        for sid, row in table.items():
            if (row["true_level"] != meta[sid]["safety_level"]
                    or row["domain"] != meta[sid]["folder_domain"]):
                raise ValueError("label/domain mismatch")
            if row["status"] != "SUCCESS" or row["generated_label"] not in SAFETY_LEVELS:
                raise ValueError("canonical SUCCESS report required")
            if ("true_binary_label" in row and row["true_binary_label"] !=
                    ("Normal" if row["true_level"] == "Level04" else "Anomaly")):
                raise ValueError("binary ground truth mismatch")
            if any(key in row and row[key] != "True" for key in ("attempted", "persisted", "parsed")):
                raise ValueError("SUCCESS persistence/parse flags mismatch")
            try:
                score = float(row["pa3_score"])
            except (TypeError, ValueError) as exc:
                raise ValueError("finite saved score required") from exc
            if isinstance(row["pa3_score"], bool) or not isfinite(score):
                raise ValueError("finite saved score required")
        indexed[model] = table
    return meta, indexed


def components(ids, edges):
    """Deterministic transitive components of explicitly supplied assumptions."""
    ids = list(ids)
    if len(set(ids)) != len(ids):
        raise ValueError("unique component IDs required")
    parent = {sid: sid for sid in ids}

    def find(sid):
        while parent[sid] != sid:
            parent[sid] = parent[parent[sid]]
            sid = parent[sid]
        return sid

    for a, b in edges:
        if a not in parent or b not in parent or a == b:
            raise ValueError("edge requires two distinct cohort IDs")
        a, b = find(a), find(b)
        parent[max(a, b)] = min(a, b)
    return {sid: find(sid) for sid in sorted(ids)}


def partition_edges(metadata, field):
    groups = defaultdict(list)
    for sid, row in metadata.items():
        value = row[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError("complete nonempty grouping key required")
        groups[value].append(sid)
    return [(members[0], sid) for members in groups.values() for sid in members[1:]]


def summarize_groups(metadata, mapping):
    if set(metadata) != set(mapping):
        raise ValueError("complete grouping coverage required")
    groups = defaultdict(list)
    for sid, key in mapping.items():
        groups[key].append(metadata[sid])
    classes = Counter()
    for members in groups.values():
        positive = sum(r["safety_level"] != "Level04" for r in members)
        classes["normal_only" if not positive else
                "anomaly_only" if positive == len(members) else "mixed"] += 1
    return {
        "n_groups": len(groups),
        "singleton_groups": sum(len(g) == 1 for g in groups.values()),
        "largest_group": max(map(len, groups.values()), default=0),
        "images_in_nonsingleton_groups": sum(len(g) for g in groups.values() if len(g) > 1),
        "anomaly_only": classes["anomaly_only"], "normal_only": classes["normal_only"],
        "mixed": classes["mixed"],
        "within_group_auc_undefined_n": classes["anomaly_only"] + classes["normal_only"],
        "severity_conflict_groups": sum(len({r["safety_level"] for r in g}) > 1 for g in groups.values()),
        "cross_domain_groups": sum(len({r["folder_domain"] for r in g}) > 1 for g in groups.values()),
        "verified_independent_sources": False,
    }


def evaluate(metadata, reports, mapping, representative=None):
    """Global weights are preserved when reporting domain subsets.

    Optional lexicographic first/last representatives apply only when requested
    by the caller; they retain the selected image's original label and score.
    """
    groups = summarize_groups(metadata, mapping)
    sizes = Counter(mapping.values())
    ids = sorted(metadata)
    if representative is not None:
        if representative not in ("first", "last"):
            raise ValueError("representative must be first or last")
        members = defaultdict(list)
        for sid in ids:
            members[mapping[sid]].append(sid)
        ids = sorted(g[0 if representative == "first" else -1] for g in members.values())
    weights = {sid: 1.0 if representative else 1.0 / sizes[mapping[sid]] for sid in ids}
    strata = {}
    for domain in [None] + sorted({r["folder_domain"] for r in metadata.values()}):
        selected = [sid for sid in ids if domain is None or metadata[sid]["folder_domain"] == domain]
        labels = [metadata[sid]["safety_level"] != "Level04" for sid in selected]
        mass = [weights[sid] for sid in selected]
        aucs = {model: weighted_auc(labels, [float(rows[sid]["pa3_score"]) for sid in selected], mass)
                for model, rows in reports.items()}
        names = list(reports)
        gaps = {f"{b}_minus_{a}": None if aucs[a] is None or aucs[b] is None else aucs[b] - aucs[a]
                for i, a in enumerate(names) for b in names[i + 1:]}
        strata[domain or "ALL"] = {
            "n_images": len(selected), "anomaly_n": sum(labels), "normal_n": len(labels) - sum(labels),
            "anomaly_mass": fsum(w for y, w in zip(labels, mass) if y),
            "normal_mass": fsum(w for y, w in zip(labels, mass) if not y),
            "auroc": aucs, "gaps": gaps,
        }
    return {"group_summary": groups, "representative": representative, "strata": strata}


def exact_score_consistency(metadata, reports):
    groups = defaultdict(list)
    for sid, row in metadata.items():
        groups[row["byte_sha256"]].append(sid)
    duplicates = [g for g in groups.values() if len(g) > 1]
    result = {"n_exact_train_groups": len(duplicates), "models": {}}
    for model, rows in reports.items():
        spreads = sorted(max(float(rows[s]["pa3_score"]) for s in g)
                         - min(float(rows[s]["pa3_score"]) for s in g) for g in duplicates)
        result["models"][model] = {
            "different_score_groups": sum(x != 0 for x in spreads),
            "maximum_score_spread": max(spreads, default=None),
            "different_generated_label_groups": sum(len({rows[s]["generated_label"] for s in g}) > 1
                                                    for g in duplicates),
        }
    return result
