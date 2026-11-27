"""Replay a sealed CT1 cohort, with a separate blinded evidence-review join."""

from collections import Counter
import hmac
import re

from safeshift.data.saved_reports import json_bytes, sha256
from safeshift.evaluation.ct1_contract import ARMS, LEVELS, parse, prompt_hashes
from safeshift.evaluation.full_train_benchmark import is_sha256, label_summary
from safeshift.evaluation.qwen_composite import ratio, require
from safeshift.fulltrain.qwen_semantics import fields

EXCLUSIONS_SHA256 = "49bb9515c9607487399b03feaeb8240997db56eaf2f2ac20bb477b1d25717321"
CASE_ID = re.compile(r"p-[0-9a-f]{12}")
VERDICTS = ("SUPPORTED", "CONTRADICTED", "UNVERIFIABLE")
DIMENSIONS = ("cue", "condition", "rule")
STATUSES = ("SUCCESS", "INVALID", "TECHNICAL_ERROR", "NOT_ATTEMPTED")
MODEL_ID = "Qwen/Qwen3-VL-8B-Instruct"
REVISION = "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b"


def validate_plan(plan, exclusions=None):
    fields(plan, {"kind", "arms", "cases"})
    require(plan["kind"] in ("SYNTHETIC", "TRAIN_DEVELOPMENT"), "only synthetic or TRAIN development")
    require(plan["arms"] in (["A", "E"], list(ARMS)), "only paired A/E or A/E/S")
    if plan["kind"] == "TRAIN_DEVELOPMENT":
        require(isinstance(exclusions, list) and len(exclusions) == 32
                and all(is_sha256(item) for item in exclusions)
                and sha256(json_bytes(sorted(exclusions))) == EXCLUSIONS_SHA256,
                "exact sealed exclusion set required")
    else:
        require(exclusions is None, "synthetic plan must not read private exclusions")
    require(isinstance(plan["cases"], list) and plan["cases"], "empty or invalid plan cohort")
    banned = set(exclusions or ())
    ids, hashes = set(), set()
    for row in plan["cases"]:
        fields(row, {"case_id", "image_sha256"})
        case, digest = row["case_id"], row["image_sha256"]
        require(isinstance(case, str) and CASE_ID.fullmatch(case), "opaque case ID required")
        require(is_sha256(digest) and digest not in banned, "invalid or audit-excluded image")
        require(case not in ids and digest not in hashes, "duplicate case or image")
        ids.add(case)
        hashes.add(digest)
    return ids


def replay(plan, runs, plan_sha256, exclusions=None):
    ids = validate_plan(plan, exclusions)
    fields(runs, {"plan_sha256", "model_id", "revision", "runtime_sha256", "prompt_sha256", "records"})
    require(is_sha256(plan_sha256) and runs["plan_sha256"] == plan_sha256, "different planned cohort")
    require(runs["model_id"] == MODEL_ID and runs["revision"] == REVISION
            and is_sha256(runs["runtime_sha256"]), "missing or different runtime provenance")
    require(runs["prompt_sha256"] == prompt_hashes(plan["arms"]), "wrong arm or prompt seal")
    require(isinstance(runs["records"], list), "run records must be an array")
    decoded = {}
    for row in runs["records"]:
        fields(row, {"case_id", "arm", "attempt_status", "raw_text"})
        case, arm, status, raw = (row[key] for key in ("case_id", "arm", "attempt_status", "raw_text"))
        require(isinstance(case, str) and case in ids and arm in plan["arms"], "unexpected case/arm")
        key = (case, arm)
        require(key not in decoded, "duplicate attempt for case/arm")
        if status == "RETURNED":
            require(type(raw) is str, "missing raw text for returned attempt")
            result = parse(arm, raw)
            decoded[key] = {
                "status": result.status, "level": result.level, "wrapped": result.wrapped,
                "evidence_status": result.evidence_status, "evidence": result.evidence,
            }
        else:
            require(status in ("TECHNICAL_ERROR", "NOT_ATTEMPTED") and raw is None,
                    "invalid non-returned attempt")
            decoded[key] = _missing(status)
    return {(case, arm): decoded.get((case, arm), _missing("NOT_ATTEMPTED"))
            for case in sorted(ids) for arm in plan["arms"]}


def _missing(status):
    return {"status": status, "level": None, "wrapped": False, "evidence_status": None, "evidence": ()}


def blind_packet(decoded, key, plan_sha256, runs_sha256):
    require(type(key) is bytes and len(key) >= 32 and is_sha256(plan_sha256) and is_sha256(runs_sha256),
            "review key (32+ bytes) and input digests required")
    packet, token_to_case = [], {}
    for (case_id, arm), row in decoded.items():
        if arm == "A" or row["status"] != "SUCCESS":
            continue
        review_id = hmac.digest(key, f"{plan_sha256}/{runs_sha256}/{case_id}/{arm}".encode(), "sha256").hex()
        token_to_case[review_id] = (case_id, arm)
        packet.append({
            "review_id": review_id, "case_id": case_id, "evidence_status": row["evidence_status"],
            "evidence": [{k: cue[k] for k in ("cue", "region", "visibility", "condition",
                                               "condition_status", "rule_source", "rule", "rule_level")}
                         for cue in row["evidence"]],
        })
    return {"cases": sorted(packet, key=lambda entry: entry["review_id"])}, token_to_case


def _review_index(reviews, packet, token_to_case):
    if reviews is None:
        return {}
    fields(reviews, {"packet_sha256", "cases"})
    require(reviews["packet_sha256"] == sha256(json_bytes(packet)), "review packet does not match")
    require(isinstance(reviews["cases"], list), "review cases must be an array")
    items = {row["review_id"]: row for row in packet["cases"]}
    output = {}
    for review in reviews["cases"]:
        fields(review, {"review_id", "basis", "visual_level", "evidence"})
        token = review["review_id"]
        require(isinstance(token, str) and token in token_to_case
                and token_to_case[token] not in output, "unknown or duplicate review ID")
        require(review["basis"] in VERDICTS and review["visual_level"] in (*LEVELS, None),
                "invalid case verdict")
        require(isinstance(review["evidence"], list)
                and len(review["evidence"]) == len(items[token]["evidence"]),
                "review does not cover the case's submitted cues")
        for verdict in review["evidence"]:
            fields(verdict, set(DIMENSIONS))
            require(all(verdict[field] in VERDICTS for field in DIMENSIONS), "invalid cue verdict")
        output[token_to_case[token]] = review
    return output


def _truth_index(truth, plan_sha256, ids):
    fields(truth, {"plan_sha256", "cases"})
    require(truth["plan_sha256"] == plan_sha256 and isinstance(truth["cases"], list), "wrong GT bundle")
    result = {}
    for row in truth["cases"]:
        fields(row, {"case_id", "true_level"})
        case_id, label = row["case_id"], row["true_level"]
        require(isinstance(case_id, str) and case_id in ids and case_id not in result
                and label in LEVELS, "unexpected, duplicate or invalid GT")
        result[case_id] = label
    require(set(result) == ids, "GT must cover the full planned cohort")
    return result


def _evidence_summary(arm, decoded, truth, reviews):
    valid = {case: decoded[case, arm] for case in truth if decoded[case, arm]["status"] == "SUCCESS"}
    if arm == "A":
        return None
    assessed = {case: reviews[case, arm] for case in valid if (case, arm) in reviews}
    by_field = {field: Counter() for field in DIMENSIONS}
    combinations = Counter()
    for review in assessed.values():
        for row in review["evidence"]:
            for field in DIMENSIONS:
                by_field[field][row[field]] += 1
            status = ("CONTRADICTED" if "CONTRADICTED" in row.values() else
                      "UNVERIFIABLE" if "UNVERIFIABLE" in row.values() else "SUPPORTED")
            combinations[status] += 1
    basis = Counter(row["basis"] for row in assessed.values())
    agreement = Counter(
        "NO_VISUAL_LEVEL" if rev["visual_level"] is None else
        "AGREE" if rev["visual_level"] == valid[case]["level"] else "DISAGREE"
        for case, rev in assessed.items()
    )
    correct_reviewed = [case for case in assessed if valid[case]["level"] == truth[case]]
    return {
        "reviewed_per_planned": ratio(len(assessed), len(truth)),
        "reviewed_per_valid": ratio(len(assessed), len(valid)),
        "case_basis": {status: basis[status] for status in VERDICTS},
        "supported_basis_reviewed": ratio(basis["SUPPORTED"], len(assessed)),
        "supported_basis_planned": ratio(basis["SUPPORTED"], len(truth)),
        "cue_verdicts": {k: {status: counts[status] for status in VERDICTS}
                         for k, counts in by_field.items()},
        "overall_claim_verdicts": {status: combinations[status] for status in VERDICTS},
        "supported_claims_reviewed": ratio(combinations["SUPPORTED"], sum(combinations.values())),
        "unreviewed_valid_n": len(valid) - len(assessed),
        "prediction_vs_independent_visual_level": {k: agreement[k] for k in ("AGREE", "DISAGREE", "NO_VISUAL_LEVEL")},
        "correct_label_with_contradicted_basis": ratio(
            sum(assessed[case]["basis"] == "CONTRADICTED" for case in correct_reviewed), len(correct_reviewed)),
        "correct_label_with_unverifiable_basis": ratio(
            sum(assessed[case]["basis"] == "UNVERIFIABLE" for case in correct_reviewed), len(correct_reviewed)),
        "declared_evidence_status": dict(Counter(row["evidence_status"] for row in valid.values())),
    }


def _label_metrics(rows, wrapped_n):
    summary = label_summary(rows)
    matrix, support = summary["confusion_4x5"], summary["support"]
    summary["status_counts"] = {status: summary["status_counts"].get(status, 0) for status in STATUSES}
    summary["format_wrapped_valid_n"] = wrapped_n
    summary["level01_to02"] = ratio(matrix["Level01"]["Level02"], support["Level01"])
    summary["level02_to01"] = ratio(matrix["Level02"]["Level01"], support["Level02"])
    summary["overseverity"] = ratio(
        sum(matrix[truth][pred] for i, truth in enumerate(LEVELS) for pred in LEVELS[:i]),
        sum(support[level] for level in LEVELS[1:]),
    )
    binary = summary["binary"]
    summary["hazard_missed_or_unavailable"] = ratio(binary["FN"] + binary["U_A"], binary["hazard_support"])
    return summary


def score(plan, decoded, truth, plan_sha256, *, reviews=None, packet=None, token_to_case=None):
    ids = {row["case_id"] for row in plan["cases"]}
    gold = _truth_index(truth, plan_sha256, ids)
    review_rows = _review_index(reviews, packet, token_to_case)
    summaries = {}
    for arm in plan["arms"]:
        records = [decoded[case, arm] for case in gold]
        rows = [{"true_level": level, "status": row["status"], "generated_label": row["level"] or "INVALID"}
                for level, row in zip(gold.values(), records, strict=True)]
        wrapped_n = sum(row["wrapped"] and row["status"] == "SUCCESS" for row in records)
        summaries[arm] = {"labels": _label_metrics(rows, wrapped_n),
                          "evidence": _evidence_summary(arm, decoded, gold, review_rows)}
    pairs = {}
    severe = [case for case, level in gold.items() if level == "Level01"]
    comparisons = [("A", "E")]
    if "S" in plan["arms"]:
        comparisons.extend((("A", "S"), ("S", "E")))
    for left, right in comparisons:
        baseline_only = proposed_only = 0
        for case in severe:
            a, b = (decoded[case, arm]["level"] == "Level01" for arm in (left, right))
            baseline_only += a and not b
            proposed_only += b and not a
        pairs[f"{right}-{left}"] = {
            "left_only_level01_correct": baseline_only, "right_only_level01_correct": proposed_only,
            "delta_level01_recall": ratio(proposed_only - baseline_only, len(severe)),
        }
    return {"scope": plan["kind"], "arms": summaries, "paired": pairs}