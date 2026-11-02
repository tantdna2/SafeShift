"""Exact Qwen V4 semantic function bodies; no grants, datasets or calibration.

Source: 31a04e6f7175cca818c63b4de0153246b3f3ecdb, qwen3.json provenance.
P2.1 is Qwen historical parsing only; peer strict C1 remains unchanged.
"""
from dataclasses import dataclass
import json
import math
import re

SAFETY_LEVELS = LEVELS = ("Level01", "Level02", "Level03", "Level04")
PARSER_VERSION = "p21-strict-classification-v1"


def strict_json(raw: str | bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f"non-finite JSON constant: {value}")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)


def fields(value, required: set[str], optional: set[str] = frozenset()):
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - optional:
        raise ValueError(f"expected fields {sorted(required)}; optional {sorted(optional)}")


@dataclass(frozen=True)
class Classification:
    safety_level: str


@dataclass(frozen=True)
class P21ParseResult:
    status: str
    value: Classification | None = None
    format_wrapper_detected: bool = False
    errors: tuple[str, ...] = ()

    @property
    def success(self):
        return self.status == "SUCCESS"


def parse_classification(text):
    """Accept two exact representations under one strict JSON/schema rule.

    Fence markers must occupy separate lines with exactly three backticks,
    optionally followed by lowercase json on the opening line. ASCII
    JSON whitespace may surround the complete response. CRLF and LF line
    endings are supported. A detected opening wrapper stays diagnostic even
    when its content or closing structure is invalid.
    """
    wrapped = False
    try:
        if type(text) is not str:
            raise ValueError("CLASSIFICATION_TEXT_REQUIRED")
        payload = text.strip(" \t\r\n")
        lines = payload.replace("\r\n", "\n").split("\n")
        wrapped = lines[0] in ("```", "```json")
        if wrapped:
            if len(lines) < 3 or lines[-1] != "```":
                raise ValueError("ONE_COMPLETE_JSON_FENCE_REQUIRED")
            # Any additional code fence is forbidden, even inside a JSON
            # string. The allowed safety-level object cannot contain one.
            if any("```" in line for line in lines[1:-1]):
                raise ValueError("MULTIPLE_CODE_FENCES_FORBIDDEN")
            payload = "\n".join(lines[1:-1])
        obj = strict_json(payload)
        fields(obj, {"safety_level"})
        if type(obj["safety_level"]) is not str or obj["safety_level"] not in SAFETY_LEVELS:
            raise ValueError("CANONICAL_SAFETY_LEVEL_REQUIRED")
        return P21ParseResult("SUCCESS", Classification(obj["safety_level"]), wrapped)
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
        return P21ParseResult("INVALID", format_wrapper_detected=wrapped, errors=(str(exc),))


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


def probe(tokenizer):
    texts = [f'{{"safety_level":"{label}"}}' for label in LEVELS]
    templates = [lambda s: s, lambda s: " " + s + "\n", lambda s: s.replace(":", ": "),
                 lambda s: s.replace("{", "{\n  ").replace("}", "\n}"),
                 lambda s: "```json\n" + s + "\n```", lambda s: "```\r\n" + s + "\r\n```",
                 lambda s: "\t```json\n" + s.replace(":", " : ") + "\n```\n"]
    checks = []
    for transform in templates:
        for text in texts:
            variant = transform(text)
            checks.append({"text": variant, **candidates(tokenizer, variant)})
    return {"bare_label_ids": {label: tokenizer.encode(label, add_special_tokens=False) for label in LEVELS},
            "checks": checks, "candidate_token_ids": sorted({i for c in checks for i in c["token_ids"]})}


def anomaly_log_odds(log_probabilities):
    # Strictly monotone in 1-p(Level04), without subtraction/exp saturation.
    maximum = max(log_probabilities[:3])
    return maximum + math.log(math.fsum(math.exp(x - maximum) for x in log_probabilities[:3])) - log_probabilities[3]


def json_number(value):
    value = float(value)
    return value if math.isfinite(value) else ("NaN" if math.isnan(value) else "+Inf" if value > 0 else "-Inf")


def summarize_tensor(tensor, candidate_ids, generated_token, torch):
    if len(tensor.shape) != 2 or tensor.shape[0] != 1:
        raise ValueError("BATCH1_VOCAB_LOGITS_REQUIRED")
    vector = tensor[0].double()
    size = int(vector.shape[0])
    if generated_token not in range(size) or any(i not in range(size) for i in candidate_ids):
        raise ValueError("TOKEN_OUTSIDE_VOCABULARY")
    return {"vocab_size": size,
            "candidate_values": {str(i): json_number(v) for i, v in
                                 zip(candidate_ids, vector[candidate_ids].tolist())},
            "generated_value": json_number(vector[generated_token].item()),
            "argmax_id": int(vector.argmax().item()), "argmax_value": json_number(vector.max().item()),
            "logsumexp": json_number(torch.logsumexp(vector, dim=0).item()),
            "nonfinite": {"nan": int(torch.isnan(vector).sum().item()),
                          "positive_inf": int(torch.isposinf(vector).sum().item()),
                          "negative_inf": int(torch.isneginf(vector).sum().item())}}
