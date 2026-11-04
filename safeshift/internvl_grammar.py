"""PROPOSED V2 grammar and CPU evidence verifier; no model runner or activation.

The native callback develops diagnostic173's trie. Full-vocabulary traces here
are synthetic qualification fixtures, not a replacement for the frozen HNLO API.
JSON null in a masked vector denotes negative infinity, never a missing raw logit.
"""
import math

from safeshift.diagnostic173_grammar import CanonicalJSONGrammar
from safeshift.pilot.contract import LEVELS, digest, parse_label
from safeshift.pilot.hnlo import branch

VERSION = "internvl35-canonical-json-grammar-v2"
HNLO_STATUS = "HNLO_NA_GRAMMAR_POLICY_V2"
PROCESSOR = "transformers.generation.logits_process.PrefixConstrainedLogitsProcessor"
MAX_TOKENS = 64
POLICY = {"do_sample": False, "num_beams": 1, "num_return_sequences": 1,
          "max_new_tokens": MAX_TOKENS, "batch_size": 1}
BINDING_KEYS = {"source_sha256", "tokenizer_sha256", "model_revision_sha256",
                "input_sha256", "prompt_sha256", "generation_sha256", "series_sha256"}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def token_ids(value, vocab, *, nonempty=False):
    require(isinstance(value, (list, tuple)), "TOKEN_SEQUENCE_REQUIRED")
    require(not nonempty or bool(value), "EMPTY_TOKEN_SEQUENCE")
    require(all(type(t) is int and 0 <= t < vocab for t in value), "TOKEN_ID_RANGE_OR_TYPE")
    return tuple(value)


class InternVLGrammarV2(CanonicalJSONGrammar):
    """Four native paths, with a proven single label decision and fixed context.

    No model loading, data I/O, or production registration. Supplying this
    callback to any future native run still requires separate execution authority.
    """

    def __init__(self, tokenizer, eos, input_ids):
        self.vocab = len(tokenizer)
        require(type(self.vocab) is int and self.vocab > 0, "VOCAB_SIZE")
        self.input_ids = token_ids(input_ids, self.vocab, nonempty=True)
        super().__init__(tokenizer, eos)
        self.paths = tuple(self.paths)
        self.texts = tuple(self.texts)
        require(len(set(self.eos)) == len(self.eos), "DUPLICATE_EOS")
        special = set(getattr(tokenizer, "all_special_ids", ()))
        require(not any(t in special for path in self.paths for t in path), "SPECIAL_CONTENT_TOKEN")
        sequences = {level: list(path) for level, path in zip(LEVELS, self.paths)}
        decision = branch(sequences)
        require(decision is not None, "COMMON_SINGLE_LABEL_BRANCH_REQUIRED")
        self.decision_step = decision["step"]
        self.decision_tokens = tuple(decision["tokens"][level] for level in LEVELS)
        self.required_tokens = len(self.paths[0]) + 1  # Include exactly one EOS.
        require(self.required_tokens <= MAX_TOKENS, "EOS_MUST_FIT_BUDGET")
        context = tokenizer.decode(list(self.input_ids), skip_special_tokens=False,
                                   clean_up_tokenization_spaces=False)
        for text, path in zip(self.texts, self.paths):
            require(tokenizer.decode(list(path), skip_special_tokens=False,
                                     clean_up_tokenization_spaces=False) == text,
                    "EXACT_CONTENT_DECODE")
            combined = tokenizer.decode(list(self.input_ids + path), skip_special_tokens=False,
                                        clean_up_tokenization_spaces=False)
            require(combined == context + text, "FIXED_INPUT_CONTEXT_CHANGED")
            for stop in self.eos:
                require(tokenizer.decode(list(path + (stop,)), skip_special_tokens=True,
                                         clean_up_tokenization_spaces=False) == text,
                        "EOS_DECODE_CHANGED")

    def allowed(self, prefix):
        return super().allowed(token_ids(prefix, self.vocab))

    def callback(self):
        def choose(batch_id, ids):
            require(type(batch_id) is int and batch_id == 0, "SINGLE_BATCH_REQUIRED")
            received = token_ids(ids.tolist(), self.vocab)
            require(received[:len(self.input_ids)] == self.input_ids, "EXACT_INPUT_PREFIX_REQUIRED")
            return self.allowed(received[len(self.input_ids):])
        return choose

    def receipt(self):
        return {"id": VERSION, "status": "PROPOSED_LABEL_ONLY", "hnlo_status": HNLO_STATUS,
                "hnlo": None, "language": list(self.texts),
                "paths_sha256": digest([list(p) for p in self.paths]),
                "input_ids_sha256": digest(list(self.input_ids)), "eos": list(self.eos),
                "path_lengths": [len(p) for p in self.paths],
                "decision_step": self.decision_step, "decision_tokens": list(self.decision_tokens),
                "required_tokens_including_eos": self.required_tokens,
                "policy": dict(POLICY), "actual_processors_required": [PROCESSOR],
                "posthoc_cleanup": False, "production_activation": False}


def mask_logits(grammar, prefix, raw_logits):
    """Independent stdlib oracle: retain allowed scores, mask all others to null."""
    require(isinstance(raw_logits, (list, tuple)) and len(raw_logits) == grammar.vocab,
            "FULL_VOCAB_RAW_REQUIRED")
    require(all(type(z) in (int, float) and math.isfinite(z) for z in raw_logits),
            "FINITE_RAW_LOGITS_REQUIRED")
    allowed = set(grammar.allowed(prefix))
    return [z if i in allowed else None for i, z in enumerate(raw_logits)]


def greedy_token(scores):
    """First-index argmax; None is the JSON representation of a masked token."""
    candidates = [i for i, z in enumerate(scores) if z is not None]
    require(bool(candidates), "NO_ALLOWED_TOKEN")
    return max(candidates, key=lambda i: scores[i])


def validate_trace(grammar, independent_decoder, trace, expected_binding):
    """Replay a complete caller-supplied trace without changing it or computing HNLO.

    This proves consistency, not authenticity or prior durable write ordering.
    Callers must verify sealed raw/source custody before parsing. Native capture
    and trusted binding creation are deliberately not implemented in this task.
    """
    require(set(expected_binding) == BINDING_KEYS, "EXACT_BINDING_REQUIRED")
    require(all(type(v) is str and len(v) == 64 and all(c in "0123456789abcdef" for c in v)
                for v in expected_binding.values()), "BINDING_SHA256_REQUIRED")
    require(trace.get("binding") == expected_binding, "BINDING_MISMATCH")
    require(trace.get("schema") == VERSION + "-trace", "TRACE_VERSION")
    require(trace.get("grammar") == grammar.receipt(), "GRAMMAR_RECEIPT_MISMATCH")
    require(trace.get("policy") == POLICY and
            all(type(trace["policy"][k]) is type(v) for k, v in POLICY.items()), "GREEDY_POLICY_REQUIRED")
    require(trace.get("actual_logits_processors") == [PROCESSOR], "EXACT_PROCESSOR_REQUIRED")
    origins = {"SYNTHETIC": "scripted_before_processors", "NATIVE": "forward_before_processors"}
    require(trace.get("evidence_kind") in origins and
            trace.get("capture_origin") == origins[trace["evidence_kind"]], "RAW_CAPTURE_ORIGIN")
    require("capture_error" in trace and trace["capture_error"] is None, "CAPTURE_ERROR")
    ids = token_ids(trace.get("generated_ids"), grammar.vocab, nonempty=True)
    require(token_ids(trace.get("input_ids"), grammar.vocab) == grammar.input_ids, "INPUT_IDS_MISMATCH")
    require(len(ids) == grammar.required_tokens and ids[-1] in grammar.eos
            and ids[:-1] in grammar.paths, "COMPLETE_PATH_AND_ONE_EOS_REQUIRED")
    steps = trace.get("steps")
    require(isinstance(steps, list) and len(steps) == len(ids), "EXACT_STEP_COUNT")
    prefix = ()
    forced = []
    for index, (token, step) in enumerate(zip(ids, steps)):
        require(type(step.get("step")) is int and step["step"] == index, "STEP_INDEX")
        require(token_ids(step.get("prefix_ids"), grammar.vocab) == grammar.input_ids + prefix,
                "STEP_PREFIX_MISMATCH")
        raw = step.get("raw_logits")
        expected = mask_logits(grammar, prefix, raw)
        masked = step.get("masked_logits")
        require(isinstance(masked, list) and len(masked) == grammar.vocab, "FULL_VOCAB_MASK_REQUIRED")
        require(all((a is None and b is None) or
                    (a is not None and type(b) in (int, float) and math.isfinite(b) and a == b)
                    for a, b in zip(expected, masked)), "MASK_OR_ALLOWED_SCORE_CHANGED")
        require(greedy_token(masked) == token, "CONSTRAINED_GREEDY_MISMATCH")
        if greedy_token(raw) != token:
            forced.append(index)
        prefix += (token,)
    context = independent_decoder.decode(list(grammar.input_ids), skip_special_tokens=False)
    for text, path in zip(grammar.texts, grammar.paths):
        require(independent_decoder.decode(list(path), skip_special_tokens=False) == text,
                "INDEPENDENT_CANDIDATE_DECODE_MISMATCH")
        require(independent_decoder.decode(list(grammar.input_ids + path), skip_special_tokens=False)
                == context + text, "INDEPENDENT_CONTEXT_MISMATCH")
    decoded = independent_decoder.decode(list(ids), skip_special_tokens=True)
    require(decoded == trace.get("response"), "INDEPENDENT_DECODE_MISMATCH")
    require(decoded == grammar.texts[grammar.paths.index(ids[:-1])], "CANONICAL_RESPONSE_REQUIRED")
    label = parse_label(decoded)
    require(label in LEVELS, "STRICT_PARSER_REQUIRED")
    return {"schema": VERSION + "-verification", "status": "TRACE_CONSISTENT",
            "evidence_kind": trace["evidence_kind"],
            "label": label, "hnlo": None, "hnlo_status": HNLO_STATUS,
            "steps": len(steps), "forced_steps": forced,
            "trace_sha256": digest(trace), "binding": dict(expected_binding),
            "scientific_equivalence": "NOT_ESTABLISHED", "production_activation": False}
