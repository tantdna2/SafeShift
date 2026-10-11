"""Raw-only LS1 primitives, gated to exact built-in synthetic evidence."""

import math

from safeshift.ls1.core import locate_decision, score_decision, validate_trace
from safeshift.ls1.evaluate import anomaly_log_odds
from safeshift.protocol.p21_schema import parse_classification
from .artifacts import json_bytes
from .policy import identity, require_case
from .synthetic import MockTokenizer, generate, specimen, summarize


def pending(settings, name, *, attempted=False, persisted=False):
    require_case(settings, name)
    return {**specimen(settings, name), "status": "UNPROCESSED" if attempted else "NOT_ATTEMPTED",
            "attempted": attempted, "persisted": persisted, "parsed": False,
            "score": None, "details": None, "generated_label": None, "errors": []}


def raw_record(settings, name):
    require_case(settings, name)
    return {"identity": identity(settings), **generate(settings, name)}


def check_raw(settings, name, raw):
    require_case(settings, name)
    if json_bytes(raw) != json_bytes(raw_record(settings, name)):
        raise PermissionError("EXACT_BUILTIN_SYNTHETIC_TRACE_REQUIRED")


def score_raw(settings, name, raw):
    """Caller must persist/reread first. Also safe for direct CPU diagnostic calls."""
    require_case(settings, name)
    check_raw(settings, name, raw)
    result = pending(settings, name, attempted=True, persisted=True)
    if raw["error"] is not None:
        result.update(status="INTERRUPTED" if name == "interrupt" else "TECHNICAL_ERROR",
                      errors=[raw["error"]])
        return result
    trace = raw["trace"]
    parsed = parse_classification(trace["decoded_text"])
    result["parsed"] = parsed.success
    result["generated_label"] = parsed.value.safety_level if parsed.success else None
    try:
        validate_trace(trace)
        for row in trace["steps"]:
            for kind in ("raw", "processed"):
                expected = summarize(row["mock_" + kind + "_vector"], row["generated_token"])
                if json_bytes(row[kind]) != json_bytes(expected):
                    raise ValueError("MOCK_FULL_VOCAB_SUMMARY_MISMATCH")
        if not parsed.success:
            result.update(status="INVALID", errors=list(parsed.errors))
            return result
        mapping = locate_decision(MockTokenizer(double=trace["mock_double_tokens"]),
                                  trace["decoded_text"], trace["continuation_ids"], trace["eos_token_ids"])
        details = score_decision(trace, mapping)
        # Common log-normalization cancels algebraically in LSE(z1,z2,z3)-z4.
        # This LS1 primitive avoids losing log(3) to a huge common raw offset.
        # No learned temperature, reference subtraction or processed logits.
        score = anomaly_log_odds(details["log_probabilities"])
        if not math.isfinite(score) or any(not math.isfinite(v) for v in details["log_probabilities"]):
            raise ValueError("NONFINITE_PA3_SCORE")
        result.update(status="SUCCESS", score=score, details=details)
    except (ValueError, KeyError, TypeError, IndexError, OverflowError) as exc:
        result.update(status="TECHNICAL_ERROR", errors=[str(exc)])
    return result
