"""CPU-only token alignment, probability and label-free calibration logic."""

import math
import re

from safeshift.protocol.p21_schema import parse_classification, PARSER_VERSION
from safeshift.protocol.schema import SAFETY_LEVELS

LEVELS = tuple(SAFETY_LEVELS)
REFERENCE_SPEC = (("gray", 128), ("black", 0), ("white", 255))
REFERENCE_SIZE = (448, 448)


def log_softmax(values):
    values = tuple(float(x) for x in values)
    if len(values) != 4 or not all(math.isfinite(x) for x in values):
        raise ValueError("FOUR_FINITE_RAW_LOGITS_REQUIRED")
    maximum = max(values)
    shifted = tuple(x - maximum for x in values)
    normalizer = math.log(math.fsum(math.exp(x) for x in shifted))
    return [x - normalizer for x in shifted]


def distribution(values):
    logs = log_softmax(values)
    return {"log_probabilities": logs, "probabilities": [math.exp(x) for x in logs],
            "prediction": LEVELS[max(range(4), key=lambda i: logs[i])],
            "probability_scope": "CONDITIONAL_ON_FOUR_LABEL_TOKENS",
            "tie_policy": "FIRST_IN_CANONICAL_LEVEL_ORDER"}


def candidates(tokenizer, text):
    """Locate a label only AFTER strict schema validation, never rescue INVALID.

    Prove the complete response encodings differ at exactly one position.
    Unsupported multi-token branching fails closed instead of an approximation.
    """
    parsed = parse_classification(text)
    if not parsed.success:
        raise ValueError("INVALID_RESPONSE_NO_LABEL_RESCUE")
    matches = list(re.finditer(r'"Level0[1-4]"', text))
    if len(matches) != 1:
        raise ValueError("AMBIGUOUS_OR_ESCAPED_LABEL_REPRESENTATION")
    match = matches[0]
    variants = [text[:match.start() + 1] + label + text[match.end() - 1:] for label in LEVELS]
    rows = [list(tokenizer.encode(v, add_special_tokens=False)) for v in variants]
    if not rows[0] or len({len(row) for row in rows}) != 1:
        raise ValueError("UNSUPPORTED_LABEL_TOKENIZATION")
    differences = [i for i in range(len(rows[0])) if len({row[i] for row in rows}) > 1]
    if len(differences) != 1:
        raise ValueError("ONE_DECISION_TOKEN_REQUIRED")
    step = differences[0]
    ids = [row[step] for row in rows]
    if len(set(ids)) != 4 or any(type(i) is not int or i < 0 for i in ids):
        raise ValueError("FOUR_DISTINCT_TOKEN_IDS_REQUIRED")
    if any(tokenizer.decode(row, skip_special_tokens=False,
                            clean_up_tokenization_spaces=False) != v for row, v in zip(rows, variants)):
        raise ValueError("TOKENIZER_ROUNDTRIP_MISMATCH")
    return {"step": step, "token_ids": ids, "prefix_ids": rows[0][:step],
            "suffix_ids": rows[0][step + 1:], "response_ids": rows[LEVELS.index(parsed.value.safety_level)],
            "generated_label": parsed.value.safety_level, "parser_version": PARSER_VERSION,
            "format_wrapper_detected": parsed.format_wrapper_detected}


def locate_decision(tokenizer, text, continuation_ids, eos_ids):
    mapping = candidates(tokenizer, text)
    ids = list(continuation_ids)
    # One terminal EOS is generation framing, not semantic output repair.
    if ids and ids[-1] in eos_ids:
        ids = ids[:-1]
    if ids != mapping["response_ids"]:
        raise ValueError("GENERATED_TOKEN_ALIGNMENT_MISMATCH")
    step = mapping["step"]
    if continuation_ids[step] != mapping["token_ids"][LEVELS.index(mapping["generated_label"])]:
        raise ValueError("WRONG_DECISION_TOKEN_POSITION")
    return {**mapping, "eos_token_ids": list(eos_ids)}


def validate_trace(raw):
    """Audit every returned step, including semantically INVALID responses."""
    ids = raw["continuation_ids"]
    steps = raw["steps"]
    if not ids or len(ids) != len(steps):
        raise ValueError("MISSING_GENERATION_STEP")
    for i, (token, row) in enumerate(zip(ids, steps)):
        if (row["step"] != i or row["generated_token"] != token
                or row["processed"]["argmax_id"] != token):
            raise ValueError("GENERATED_PROCESSED_ARGMAX_MISMATCH")
        if any(row["raw"]["nonfinite"].values()):
            raise ValueError("RAW_NAN_OR_INF")
        if (row["processed"]["nonfinite"]["nan"] or row["processed"]["nonfinite"]["positive_inf"]
                or not math.isfinite(row["processed"]["logsumexp"])):
            raise ValueError("PROCESSED_NAN_OR_INVALID_INF")
        processed = row["processed"]
        if processed["generated_value"] != processed["argmax_value"]:
            raise ValueError("GENERATED_VALUE_NOT_MAXIMAL")
        if (not math.isfinite(row["raw"]["logsumexp"])
                or row["raw"]["logsumexp"] < row["raw"]["argmax_value"]):
            raise ValueError("INVALID_FULL_VOCAB_NORMALIZER")


def score_decision(raw, mapping):
    """Consume durably reread raw summaries. Processed scores never feed LS1."""
    validate_trace(raw)
    ids, steps = raw["continuation_ids"], raw["steps"]
    if not 0 <= mapping["step"] < len(steps):
        raise ValueError("MISSING_DECISION_STEP")
    row = steps[mapping["step"]]
    label_ids = mapping["token_ids"]
    if ids[mapping["step"]] != label_ids[LEVELS.index(mapping["generated_label"])]:
        raise ValueError("WRONG_DECISION_TOKEN_POSITION")
    try:
        logits = [row["raw"]["candidate_values"][str(i)] for i in label_ids]
        processed = [row["processed"]["candidate_values"][str(i)] for i in label_ids]
    except KeyError as exc:
        raise ValueError("MISSING_LABEL_TOKEN") from exc
    result = distribution(logits)
    chosen = LEVELS.index(mapping["generated_label"])
    if (max(logits) > row["raw"]["argmax_value"] or row["raw"]["generated_value"] != logits[chosen]
            or row["processed"]["generated_value"] != processed[chosen]):
        raise ValueError("LABEL_VALUES_AND_VOCAB_SUMMARY_MISMATCH")
    lse = row["raw"]["logsumexp"]
    if not math.isfinite(lse) or lse < max(logits):
        raise ValueError("INVALID_FULL_VOCAB_NORMALIZER")
    return {**result, "raw_label_logits": logits, "processed_label_scores": processed,
            "full_vocab_log_probabilities": [x - lse for x in logits],
            "four_label_probability_mass": math.fsum(math.exp(x - lse) for x in logits),
            "raw_argmax_id": row["raw"]["argmax_id"],
            "processed_argmax_id": row["processed"]["argmax_id"],
            "raw_and_processed_label_scores_equal": logits == processed,
            "generated_label": mapping["generated_label"], "decision": mapping}


def reference_images():
    from PIL import Image
    return {name: Image.new("RGB", REFERENCE_SIZE, (value,) * 3) for name, value in REFERENCE_SPEC}


def calibrate(raw_logits, reference_logits, *, protect_level01=False):
    if type(protect_level01) is not bool:
        raise ValueError("BOOLEAN_GUARD_REQUIRED")
    if set(reference_logits) != {name for name, _ in REFERENCE_SPEC}:
        raise ValueError("EXACT_THREE_REFERENCES_REQUIRED")
    log_probs = [log_softmax(reference_logits[name]) for name, _ in REFERENCE_SPEC]
    # Mean log probability (geometric prior), fixed coefficient 1. No fitting.
    bias = [math.fsum(row[i] for row in log_probs) / 3 for i in range(4)]
    original = distribution(raw_logits)
    calibrated = distribution([float(raw_logits[i]) - bias[i] for i in range(4)])
    argmax = calibrated["prediction"]
    applied = protect_level01 and original["prediction"] == "Level01" and argmax != "Level01"
    if applied:
        calibrated["prediction"] = "Level01"
    return {"uncalibrated": original, "calibrated": {**calibrated, "unguarded_argmax": argmax,
            "level01_guard_applied": applied}, "reference_log_bias": bias,
            "level01_guard_enabled": protect_level01,
            "guard_limitation": "Preserves only uncalibrated LS1 Level01, not all true hazards; probabilities unchanged."}
