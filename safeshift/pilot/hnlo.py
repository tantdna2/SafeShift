"""Model-specific tokenizer probing and CPU replay of bounded raw evidence.

No Qwen token IDs, vocabulary vectors or sequence likelihood approximation.
Multi-token labels qualify ONLY if their complete native continuations differ
at exactly one position, with common prefix/suffix and four distinct tokens.
"""
from decimal import Decimal, localcontext
import math

from .contract import LEVELS, parse_label

SURFACES = ('{"safety_level":"%s"}', '{"safety_level": "%s"}', '{ "safety_level": "%s" }')


def branch(sequences):
    seqs = [sequences[l] for l in LEVELS]
    if any(not s for s in seqs) or len({len(s) for s in seqs}) != 1:
        return None
    different = [i for i in range(len(seqs[0])) if len({s[i] for s in seqs}) != 1]
    if len(different) != 1:
        return None
    step = different[0]
    tokens = [s[step] for s in seqs]
    if len(set(tokens)) != 4:
        return None
    return {"step": step, "prefix": seqs[0][:step], "suffix": seqs[0][step + 1:],
            "tokens": dict(zip(LEVELS, tokens))}


def probe(tokenizer, rendered_prompt, actual_input_ids):
    """Native text boundary checked against actual processor's trailing tokens.

    Image token expansion may differ before this suffix; no GT/path in text.
    Complete candidate strings are round-tripped and boundary tokenization is
    checked, including actual BOS/chat tokens. Unsupported mappings stay evidence.
    """
    base = tokenizer.encode(rendered_prompt, add_special_tokens=False)
    tail = min(32, len(base), len(actual_input_ids))
    boundary_ok = tail >= 8 and base[-tail:] == actual_input_ids[-tail:]
    actual_tail = actual_input_ids[-tail:]
    # Already supplied input tokens cannot be retokenized when generating. Some
    # tokenizers merge the final newline with a following brace when encoding a
    # concatenated text. Build native continuation candidates separately, then
    # prove their decoding in the *fixed actual token context*. Joint-encoding
    # stability is retained as diagnostic evidence, not assumed as a prerequisite.
    context = tokenizer.decode(actual_tail, skip_special_tokens=False, clean_up_tokenization_spaces=False)
    mappings = []
    for surface in SURFACES:
        sequences, roundtrip, prefix_ok = {}, True, True
        context_prefixes, joint_stable = [], True
        for label in LEVELS:
            text = surface % label
            ids = tokenizer.encode(rendered_prompt + text, add_special_tokens=False)
            joint_stable &= ids[:len(base)] == base
            continuation = tokenizer.encode(text, add_special_tokens=False)
            sequences[label] = continuation
            roundtrip &= tokenizer.decode(continuation, skip_special_tokens=False,
                                           clean_up_tokenization_spaces=False) == text
            in_context = tokenizer.decode(actual_tail + continuation, skip_special_tokens=False,
                                          clean_up_tokenization_spaces=False)
            ok = in_context.endswith(text)
            prefix = in_context[:-len(text)] if ok else ""
            prefix_ok &= ok and prefix.startswith(context) and not prefix[len(context):].strip()
            context_prefixes.append(prefix)
        prefix_ok &= len(set(context_prefixes)) == 1
        decision = branch(sequences) if boundary_ok and prefix_ok and roundtrip else None
        mappings.append({"surface": surface, "sequences": sequences, "roundtrip": roundtrip,
                         "prefix_ok": prefix_ok, "decision": decision,
                         "joint_text_encoding_prefix_stable": joint_stable,
                         "fixed_context_decoded_prefix": context_prefixes[0]})
    return {"boundary_ok": boundary_ok, "boundary_tokens": base[-tail:],
            "actual_boundary_tokens": actual_input_ids[-tail:], "mappings": mappings,
            "standalone_labels": {l: tokenizer.encode(l, add_special_tokens=False) for l in LEVELS},
            "reason": None if any(m["decision"] for m in mappings)
            else "NO_PROVEN_COMMON_SINGLE_BRANCH_AT_NATIVE_BOUNDARY"}


def candidate_ids(token_probe):
    return sorted({t for m in token_probe["mappings"] if m["decision"]
                   for t in m["decision"]["tokens"].values()})


def hnlo(logits):
    if len(logits) != 4 or not all(math.isfinite(z) for z in logits):
        raise ValueError("FOUR_FINITE_RAW_LOGITS_REQUIRED")
    maximum = max(logits[:3])
    return (maximum - logits[3]) + math.log(math.fsum(math.exp(z - maximum) for z in logits[:3]))


def oracle(logits):
    """Independent Decimal odds sum, with shift to avoid exponent overflow."""
    with localcontext() as ctx:
        ctx.prec = 60
        values = [Decimal.from_float(float(x)) for x in logits]
        shifts = [v - values[3] for v in values[:3]]
        top = max(shifts)
        return float(top + sum((v - top).exp() for v in shifts).ln())


def tokenizer_replay(raw, cpu_tokenizer):
    """Independent Rust decoder reconstructed from serialized runtime tokenizer.

    No Transformers processor/model, weights or GPU needed for this check.
    """
    decoded = cpu_tokenizer.decode(raw["generated_ids"], skip_special_tokens=True)
    if decoded != raw["response"]:
        raise ValueError("CPU_GENERATED_DECODE_MISMATCH")
    p = raw.get("token_probe")
    if p:
        for m in p["mappings"]:
            if not m["decision"]:
                continue
            context = cpu_tokenizer.decode(p["actual_boundary_tokens"], skip_special_tokens=False)
            prefixes = []
            for label in LEVELS:
                seq = m["sequences"][label]
                if cpu_tokenizer.decode(seq, skip_special_tokens=False) != m["surface"] % label:
                    raise ValueError("CPU_CANDIDATE_DECODE_MISMATCH")
                text = cpu_tokenizer.decode(p["actual_boundary_tokens"] + seq, skip_special_tokens=False)
                expected = m["surface"] % label
                if not text.endswith(expected):
                    raise ValueError("CPU_CONTEXT_MAPPING_MISMATCH")
                prefix = text[:-len(expected)]
                if not prefix.startswith(context) or prefix[len(context):].strip():
                    raise ValueError("CPU_CONTEXT_PREFIX_CHANGED")
                prefixes.append(prefix)
            if len(set(prefixes)) != 1 or prefixes[0] != m["fixed_context_decoded_prefix"]:
                raise ValueError("CPU_FOUR_LABEL_CONTEXTS_NOT_EQUAL")
    return {"status": "PASS", "generated_decode": "MATCH", "candidate_contexts": "MATCH"}


def replay(raw, label):
    base = {"status": "HNLO_UNVERIFIED", "capture_status": "NOT_RUN", "alignment_status": "UNVERIFIED",
            "replay_status": "NOT_RUN", "hnlo": None, "reason": None}
    if raw.get("capture_error"):
        return {**base, "status": "HNLO_TECHNICAL_FAILURE", "reason": raw["capture_error"]}
    p = raw.get("token_probe")
    if not p:
        return {**base, "reason": "NO_TOKEN_PROBE"}
    tail = p.get("actual_boundary_tokens", [])
    if not tail or raw.get("input_ids", [])[-len(tail):] != tail:
        return {**base, "status": "HNLO_TECHNICAL_FAILURE", "reason": "ACTUAL_NATIVE_INPUT_BOUNDARY_CHANGED"}
    supported = [m for m in p["mappings"] if m["decision"]]
    if not supported:
        return {**base, "status": "HNLO_INCOMPATIBLE", "reason": p["reason"], "alignment_status": "INCOMPATIBLE"}
    steps, ids = raw.get("steps", []), list(raw.get("generated_ids", []))
    if not steps or len(steps) != len(ids):
        return {**base, "status": "HNLO_TECHNICAL_FAILURE", "reason": "FORWARD_GENERATION_STEP_COUNT"}
    base["capture_status"] = "RAW_LOGITS_AVAILABLE"
    if raw.get("cpu_tokenizer_replay", {}).get("status") != "PASS":
        return {**base, "status": "RAW_LOGITS_AVAILABLE_BUT_UNALIGNED", "reason": "INDEPENDENT_CPU_TOKENIZER_REPLAY_REQUIRED"}
    if raw.get("actual_logits_processors") != []:
        return {**base, "status": "RAW_LOGITS_AVAILABLE_BUT_UNALIGNED", "reason": "NONEMPTY_OR_UNKNOWN_PROCESSORS"}
    if any(s["argmax"] != token or not s["all_finite"] for s, token in zip(steps, ids)):
        return {**base, "status": "RAW_LOGITS_AVAILABLE_BUT_UNALIGNED", "reason": "RAW_GREEDY_ALIGNMENT_OR_FINITE_FAIL"}
    if label not in LEVELS or parse_label(raw["response"]) != label:
        return {**base, "status": "RAW_LOGITS_AVAILABLE_BUT_UNALIGNED", "reason": "NO_VALID_GENERATED_LABEL"}
    while ids and ids[-1] in raw.get("eos_token_ids", []):
        ids.pop()
    for m in supported:
        # Recompute mapping independently instead of trusting stored branch fields.
        d = branch(m["sequences"])
        if (d != m["decision"] or p["boundary_ok"] is not True
                or p["boundary_tokens"] != p["actual_boundary_tokens"]
                or m["roundtrip"] is not True or m["prefix_ok"] is not True):
            return {**base, "status": "HNLO_TECHNICAL_FAILURE", "reason": "TOKEN_MAPPING_PROOF_CHANGED"}
        if ids != m["sequences"][label] or raw["response"] != m["surface"] % label:
            continue
        step = steps[d["step"]]
        if step["step"] != d["step"]:
            raise ValueError("DECISION_STEP_INDEX_MISMATCH")
        logits = [step["raw_candidate_logits"][str(d["tokens"][l])] for l in LEVELS]
        try:
            score, independent = hnlo(logits), oracle(logits)
            if not math.isfinite(score) or not math.isclose(score, independent, rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError("CPU_ORACLE_FAIL")
        except (ArithmeticError, ValueError) as error:
            return {**base, "status": "HNLO_TECHNICAL_FAILURE", "reason": str(error), "replay_status": "FAIL"}
        return {**base, "status": "HNLO_VALIDATED", "alignment_status": "PASS", "replay_status": "PASS",
                "hnlo": score, "oracle_hnlo": independent, "raw_logits": dict(zip(LEVELS, logits)),
                "token_ids": d["tokens"], "decision_step": d["step"],
                "generated_label": label, "sign": "positive" if score > 0 else "negative" if score < 0 else "zero",
                "reason": None}
    return {**base, "status": "RAW_LOGITS_AVAILABLE_BUT_UNALIGNED",
            "reason": "ACTUAL_OUTPUT_NOT_ONE_OF_PROVEN_NATIVE_CONTINUATIONS"}
