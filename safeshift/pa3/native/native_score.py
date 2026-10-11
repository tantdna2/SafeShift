"""CPU recomputation; only original raw logits enter PA3 scores."""

import math

from safeshift.ls1.core import locate_decision, score_decision, validate_trace
from safeshift.ls1.evaluate import anomaly_log_odds
from safeshift.protocol.p21_schema import parse_classification

STATUSES = ("SUCCESS", "INVALID", "TECHNICAL_ERROR", "INTERRUPTED", "UNPROCESSED", "NOT_ATTEMPTED")


def pending(sample_id, *, attempted=False, persisted=False):
    return {"sample_id": sample_id, "status": "UNPROCESSED" if attempted else "NOT_ATTEMPTED",
            "attempted": attempted, "persisted": persisted, "parsed": False,
            "score": None, "details": None, "generated_label": None, "errors": []}


def score(sample_id, raw, tokenizer):
    result = pending(sample_id, attempted=True, persisted=True)
    parsed = parse_classification(raw["decoded_text"])
    result.update(parsed=parsed.success,
                  generated_label=parsed.value.safety_level if parsed.success else None)
    try:
        validate_trace(raw)
        if raw["forced_assistant_prefix_ids"]:
            raise ValueError("FORCED_PREFIX_FORBIDDEN")
        if tokenizer.decode(raw["continuation_ids"], skip_special_tokens=True,
                            clean_up_tokenization_spaces=False) != raw["decoded_text"]:
            raise ValueError("RAW_TEXT_TOKEN_MISMATCH")
        if not parsed.success:
            result.update(status="INVALID", errors=list(parsed.errors))
            return result
        eos = raw["generation_config"]["eos_token_id"]
        mapping = locate_decision(tokenizer, raw["decoded_text"], raw["continuation_ids"],
                                  eos if type(eos) is list else [eos])
        details = score_decision(raw, mapping)
        value = anomaly_log_odds(details["log_probabilities"])
        if not math.isfinite(value) or any(not math.isfinite(x) for x in details["log_probabilities"]):
            raise ValueError("NONFINITE_PA3_SCORE")
        # Log mass remains informative when exp(log_mass) underflows to zero.
        z = details["raw_label_logits"]
        m = max(z)
        details["four_label_log_mass"] = (m - raw["steps"][mapping["step"]]["raw"]["logsumexp"]
                                            + math.log(math.fsum(math.exp(x-m) for x in z)))
        result.update(status="SUCCESS", score=value, details=details)
    except (ValueError, KeyError, TypeError, IndexError, OverflowError) as exc:
        result.update(status="TECHNICAL_ERROR", errors=[str(exc)])
    return result
