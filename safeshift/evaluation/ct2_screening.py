"""Retrospective CT2 budget screening from admitted Full-TRAIN labels."""

from collections import Counter

from safeshift.data.schema import SAFETY_LEVELS as LEVELS
from safeshift.evaluation.full_train_benchmark import (
    IDENTITY, PRODUCTS, validate_cohort, validate_product,
)
from safeshift.evaluation.qwen_composite import digest, ratio, require


SCHEMA = "safeshift-ct2-screening-v1"
RESULT_STATUS = "EXPLORATORY_EXPOSED_TRAIN"
DEFAULT_SEEDS = (0, 1, 2)
NORMAL = "Level04"
HAZARD_LEVELS = LEVELS[:-1]
SEVERITY_PRIORITY = {"Level01": 3, "Level02": 2, "Level03": 1}
PEER_POLICIES = (
    ("internvl_binary", "internvl35", False),
    ("internvl_severity", "internvl35", True),
    ("minicpm_binary", "minicpm", False),
    ("minicpm_strict_c1_binary", "minicpm_strict_c1", False),
)
DEFINITIONS = {
    "eligible": "Canonical Qwen3 SUCCESS Level04 on the admitted TRAIN cohort.",
    "cost": "Simulated calls per arm: one Qwen3 call per planned ID plus one peer call "
            "per acquired eligible ID for peer arms. Each arm uses a single peer.",
    "default_model_call_caps": "N plus each of floor(0.10*N), floor(0.30*N), and eligible_n.",
    "default_review_caps": "floor(0.01*N), floor(0.05*N), and floor(0.10*N), with N planned.",
    "acquisition": "Take the first min(M - N, eligible_n) eligible IDs in the "
                   "peer-acquisition order, shared by all peer arms at the same seed and cap.",
    "order": "Ascending SHA-256 of canonical JSON [seed, purpose, sample_id], then ID "
             "on a hash collision. Purposes are peer-acquisition and review-ties.",
    "random": "Review the first effective K in review-ties order on the entire eligible set.",
    "focal_only": "Identical to random_matched at each seed because all eligible focal "
                  "labels are Level04. Reported once.",
    "peer_priority": "Rank acquired canonical hazard labels ahead of other eligible IDs. "
                     "Binary flags tie. InternVL severity orders Level01, Level02, then "
                     "Level03. Use review-ties within each priority and for fill.",
    "minicpm": "Primary peer uses the admitted V1 normalization. Strict C1 sensitivity "
               "records acquired INVALID as an abstention. The admitted INVALID-to-Level04 "
               "mapping changes coverage while preserving binary flags and review ranks.",
    "review": "Effective K is min(K, eligible_n). Each selected ID consumes one review slot. "
              "Unreviewed flags are overflow and all unreviewed eligible IDs are unresolved.",
    "evaluation": "GT Level01–03 among eligible is false-safe and GT Level01 is severe "
                  "false-safe. Capture means selected for review. Residual means unreviewed. "
                  "Precision@K uses actual unique reviews as denominator.",
    "matched_delta": "Gained and lost events compare review membership to random_matched "
                     "at the same seed and K. Net equals gained minus lost.",
    "random_expectation": "Expected captures under uniform sampling without replacement "
                          "conditional on this eligible set: effective K times event count "
                          "divided by eligible_n. Zero when eligibility is empty.",
    "scope": "Fixed exposed TRAIN, saved labels and simulated budgets. Seed variation "
             "describes allocation and tie choices on this cohort.",
}


def seeded_order(eligible_ids, seed, purpose):
    """Order IDs without consulting labels or projection row order."""
    return sorted(eligible_ids, key=lambda sid: (digest([seed, purpose, sid]), sid))


def prioritize(review_order, acquired_labels, *, severity=False):
    """Rank using only purchased labels and a precomputed GT-blind tie order."""
    priorities = SEVERITY_PRIORITY if severity else dict.fromkeys(HAZARD_LEVELS, 1)
    flags = {sid: priorities[label] for sid, label in acquired_labels.items()
             if label in priorities}
    return sorted(review_order, key=lambda sid: -flags.get(sid, 0)), len(flags)


def explicit_values(values, minimum, name):
    values = tuple(values)
    require(values and all(type(value) is int and value >= minimum for value in values),
            f"{name} must be integers >= {minimum}")
    require(len(set(values)) == len(values), f"{name} must be distinct")
    return values


def endpoint(events, support_n, reviewed, matched, eligible_n):
    total = len(events)
    captured = events & reviewed
    gained = len(captured - matched)
    lost = len((events & matched) - reviewed)
    residual = total - len(captured)
    return {
        "total_n": total,
        "captured_n": len(captured),
        "residual_n": residual,
        "total_per_gt_support": ratio(total, support_n),
        "residual_per_gt_support": ratio(residual, support_n),
        "capture_fraction": ratio(len(captured), total),
        "precision_at_k": ratio(len(captured), len(reviewed)),
        "matched_random_expected_captures": ratio(len(reviewed) * total, eligible_n or 1),
        "vs_matched_random": {"gained_n": gained, "lost_n": lost, "net_n": gained - lost},
    }


def evaluate_arm(review_ids, matched, events, *, n, eligible_n, review_cap,
                 peer_name=None, acquired_labels=None, flag_n=0):
    reviewed = set(review_ids[:review_cap])
    labels = Counter(acquired_labels.values()) if acquired_labels is not None else Counter()
    acquired_n = labels.total()
    return {
        "model_calls": {"qwen3": n, "peer": acquired_n, "total": n + acquired_n},
        "peer": peer_name,
        "eligible_unqueried_n": eligible_n - acquired_n,
        "acquired_peer_normal_n": labels[NORMAL],
        "acquired_peer_abstention_n": labels["INVALID"],
        "workload": {
            "unique_reviews_n": len(reviewed),
            "reviews_per_planned": ratio(len(reviewed), n),
            "unused_review_slots_n": review_cap - len(reviewed),
            "acquired_hazard_flags_n": flag_n,
            "flag_overflow_n": max(flag_n - len(reviewed), 0),
            "fill_reviews_n": max(len(reviewed) - flag_n, 0),
            "unresolved_eligible_n": eligible_n - len(reviewed),
        },
        **{name: endpoint(ids, support, reviewed, matched, eligible_n)
           for name, (ids, support) in events.items()},
    }


def screen(cohort, products, config, *, seeds=DEFAULT_SEEDS, model_call_caps=None,
           review_caps=None, mini_conversion_n=205):
    """Validate the standard projections and return aggregate budgets and outcomes."""
    require(set(products) == set(config["products"]) == set(PRODUCTS),
            "exact product roster required")
    rows, metadata = validate_cohort(cohort, config["planned_n"])
    panels, product_seals = {}, {}
    for key in PRODUCTS:
        panel, strict_c1, provenance = validate_product(
            key, products[key], config["products"][key], metadata, mini_conversion_n)
        panels[key] = {row["sample_id"]: row["generated_label"] for row in panel}
        product_seals[key] = provenance["source_seal_sha256"]
        if key == "minicpm":
            panels["minicpm_strict_c1"] = {
                row["sample_id"]: row["generated_label"] for row in strict_c1}

    eligible = {sid for sid, label in panels["qwen3"].items() if label == NORMAL}
    n, eligible_n = len(rows), len(eligible)
    seeds = explicit_values(seeds, 0, "seeds")
    if model_call_caps is None:
        model_call_caps = dict.fromkeys(n + k for k in (n // 10, 3 * n // 10, eligible_n))
    if review_caps is None:
        review_caps = dict.fromkeys(n * percent // 100 for percent in (1, 5, 10))
    model_call_caps = explicit_values(model_call_caps, n, "model-call caps")
    review_caps = explicit_values(review_caps, 0, "review caps")

    outcomes = []
    for seed in seeds:
        acquisition_order = seeded_order(eligible, seed, "peer-acquisition")
        review_order = seeded_order(eligible, seed, "review-ties")
        for model_call_cap in model_call_caps:
            acquired = acquisition_order[:model_call_cap - n]
            rankings = {"random_matched": (review_order, None, None, 0)}
            for policy, peer, severity in PEER_POLICIES:
                labels = {sid: panels[peer][sid] for sid in acquired}
                order, flag_n = prioritize(review_order, labels, severity=severity)
                rankings[policy] = (order, peer, labels, flag_n)
            for review_cap in review_caps:
                outcomes.append((seed, model_call_cap, review_cap, rankings))

    # All rankings are fixed before evaluation uses GT.
    events = {}
    for name, levels in (("false_safe", HAZARD_LEVELS), ("severe_false_safe", ("Level01",))):
        gt_ids = {row["sample_id"] for row in rows if row["true_level"] in levels}
        events[name] = (gt_ids & eligible, len(gt_ids))
    cells = []
    for seed, model_call_cap, review_cap, rankings in outcomes:
        matched = set(rankings["random_matched"][0][:review_cap])
        arms = {
            policy: evaluate_arm(order, matched, events, n=n, eligible_n=eligible_n,
                                 review_cap=review_cap, peer_name=peer,
                                 acquired_labels=labels, flag_n=flag_n)
            for policy, (order, peer, labels, flag_n) in rankings.items()
        }
        cells.append({"seed": seed, "model_call_cap": model_call_cap,
                      "review_cap": review_cap, "arms": arms})

    return {
        "schema": SCHEMA,
        "result_status": RESULT_STATUS,
        "upstream_result_status": config["release"]["result_status"],
        "new_model_calls_n": 0,
        "planned_n": n,
        "eligible_n": eligible_n,
        "eligible_per_planned": ratio(eligible_n, n),
        "seeds": seeds,
        "model_call_caps": model_call_caps,
        "review_caps": review_caps,
        "cohort_identity_sha256": digest(
            [[row["sample_id"], *(row[field] for field in IDENTITY)] for row in rows]),
        "product_source_seal_sha256": product_seals,
        "definitions": DEFINITIONS,
        "focal_only_baseline": {"same_selection_as": "random_matched"},
        "cells": cells,
    }
