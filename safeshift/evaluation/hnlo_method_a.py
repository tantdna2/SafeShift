"""Bounded, in-memory Method A engineering verifier. No production activation.

Synthetic evidence and the separately authorized Issue165 archive bridge are
admitted. Injected decoders and seals remain trusted inputs, not attestations.
See docs/HNLO_METHOD_A.md for the custody boundary and later evidence needs.
"""
from dataclasses import dataclass
import hashlib
import math
import re
from typing import Callable

from safeshift.pilot.contract import GENERATION, LEVELS, digest, parse_label
from safeshift.pilot.hnlo import hnlo, oracle

SCHEMA = "safeshift-hnlo-method-a-v1"
SCOPE = "CPU_SYNTHETIC_ONLY"
SAVED_SCOPE = "CPU_SAVED_OFFICIAL160_ISSUE165"
MAX_TRIALS = 2_000_000  # resource bound, not a scientific threshold
ORIGIN = "outer_forward_output_before_generate_processors"


class Refusal(ValueError):
    def __init__(self, reason, status="FAIL"):
        self.reason, self.status = reason, status
        super().__init__(reason)


def need(condition, reason, status="FAIL"):
    if not condition:
        raise Refusal(reason, status)


@dataclass(frozen=True)
class Seal:
    """Expected hashes supplied separately from the untrusted evidence packet."""
    evidence_sha256: str
    tokenizer_sha256: str
    vocabulary_sha256: str


@dataclass(frozen=True)
class Decoder:
    """Trusted pure adapter: complete vocabulary (including added tokens).

    decode(ids, skip_special_tokens) must disable whitespace cleanup. The
    independent adapter must be independently implemented/reconstructed; mere
    equality of this metadata does not prove its implementation is authentic.
    """
    serialization: bytes
    vocabulary: tuple[int, ...]
    special_ids: tuple[int, ...]
    decode: Callable[[tuple[int, ...], bool], str]


@dataclass(frozen=True)
class Proof:
    decision_step: int
    sequences: tuple[tuple[int, ...], ...]  # canonical LEVELS order, no EOS
    evidence_sha256: str


class EnumerationCache:
    """Per-run, bounded memoization of exhaustive structural searches only.

    Keys include the exact trusted decoder object and every search input.
    Builder and independent verifier never share an entry. No custody, step,
    logit, numeric, or packet validation is cached. Decoders must remain pure.
    """
    def __init__(self):
        self.entries = {}
        self.hits = 0
        self.searches = 0

    def search(self, role, decoder, arguments, compute):
        key = (role, decoder, arguments)
        if key in self.entries:
            self.hits += 1
            result, refusal = self.entries[key]
            if refusal is not None:
                raise Refusal(*refusal)
            return result
        try:
            result, refusal = compute(), None
        except Refusal as error:
            result, refusal = None, (error.reason, error.status)
        self.searches += 1
        if len(self.entries) >= 32:
            self.entries.pop(next(iter(self.entries)))
        self.entries[key] = (result, refusal)
        if refusal is not None:
            raise Refusal(*refusal)
        return result


def _bounded_json(value):
    # Bound before hashing/copying; reject non-JSON objects and nonfinite values.
    remaining = 150_000
    chars = 0

    def visit(item, depth):
        nonlocal remaining, chars
        remaining -= 1
        need(remaining >= 0 and depth <= 16, "EVIDENCE_RESOURCE_BOUND", "UNAVAILABLE")
        if type(item) is str:
            chars += len(item)
            need(len(item) <= 65_536 and chars <= 2_000_000,
                 "EVIDENCE_RESOURCE_BOUND", "UNAVAILABLE")
        elif type(item) is float:
            need(math.isfinite(item), "NONFINITE_EVIDENCE")
        elif type(item) is int:
            need(abs(item) <= 2**63, "INTEGER_RANGE")
        elif item is None or type(item) is bool:
            pass
        elif type(item) in (list, dict):
            need(len(item) <= 32_768, "EVIDENCE_RESOURCE_BOUND", "UNAVAILABLE")
            if type(item) is dict:
                for key, child in item.items():
                    need(type(key) is str, "JSON_KEY_TYPE")
                    visit(key, depth + 1)
                    visit(child, depth + 1)
            else:
                for child in item:
                    visit(child, depth + 1)
        else:
            raise Refusal("EVIDENCE_TYPE")
    visit(value, 0)


def _ids(value, vocabulary, reason, maximum=32_768):
    need(type(value) is list and 0 < len(value) <= maximum, reason)
    need(all(type(t) is int and t in vocabulary for t in value), reason)
    return tuple(value)


def _decode(decoder, ids, skip=False):
    try:
        text = decoder.decode(ids, skip)
    except Exception as error:
        raise Refusal("DECODER_FAILURE", "UNAVAILABLE") from error
    need(type(text) is str and len(text) <= 65_536, "DECODE_TYPE_OR_BOUND")
    return text


def _prepare(packet, decoder, seal):
    _bounded_json(packet)
    need(packet["schema"] == SCHEMA and packet["scope"] in (SCOPE, SAVED_SCOPE),
         "SYNTHETIC_SCOPE_REQUIRED", "UNAVAILABLE")
    need(type(seal) is Seal and type(decoder) is Decoder, "TRUST_INPUT_TYPE")
    for checksum in (seal.evidence_sha256, seal.tokenizer_sha256, seal.vocabulary_sha256):
        need(type(checksum) is str and re.fullmatch(r"[0-9a-f]{64}", checksum), "SEAL_FORMAT")
    need(digest(packet) == seal.evidence_sha256, "EVIDENCE_SEAL_MISMATCH")
    need(type(decoder.serialization) is bytes and 0 < len(decoder.serialization) <= 32_000_000,
         "TOKENIZER_SERIALIZATION_REQUIRED", "UNAVAILABLE")
    need(hashlib.sha256(decoder.serialization).hexdigest() == seal.tokenizer_sha256,
         "TOKENIZER_HASH_MISMATCH")
    vocab, special = decoder.vocabulary, decoder.special_ids
    need(type(vocab) is tuple and 1 <= len(vocab) <= 131_072
         and all(type(t) is int and 0 <= t < 2**31 for t in vocab), "VOCABULARY_REQUIRED")
    need(len(set(vocab)) == len(vocab), "VOCABULARY_DUPLICATE")
    vocabulary = set(vocab)
    need(type(special) is tuple and all(type(t) is int and t in vocabulary for t in special)
         and len(set(special)) == len(special), "SPECIAL_IDS")
    need(digest({"ids": sorted(vocab), "special_ids": sorted(special)}) == seal.vocabulary_sha256,
         "VOCABULARY_SEAL_MISMATCH")
    vocabulary = set(vocab)
    provenance, config, raw, native = (packet[k] for k in ("provenance", "config", "raw", "native"))
    for key in ("source_sha256", "configuration_sha256", "descriptor_sha256", "input_sha256",
                "prompt_sha256", "tokenizer_sha256"):
        need(type(provenance[key]) is str and re.fullmatch(r"[0-9a-f]{64}", provenance[key]),
             "PROVENANCE_HASH:" + key)
    for key in ("model_revision", "runtime_commit"):
        need(type(provenance[key]) is str and re.fullmatch(r"[0-9a-f]{40}", provenance[key]),
             "PROVENANCE_REVISION:" + key)
    for key in ("sample_id", "run_id", "attempt_id", "series_id", "implementation_id"):
        need(type(provenance[key]) is str and 0 < len(provenance[key]) <= 200,
             "PROVENANCE_ID:" + key)
    need(provenance["model_id"] == "openbmb/MiniCPM-V-4", "MODEL_ID")
    need(provenance["tokenizer_sha256"] == seal.tokenizer_sha256
         == raw["tokenizer_serialization_sha256"], "TOKENIZER_PROVENANCE_MISMATCH")
    need(digest(config) == provenance["configuration_sha256"], "CONFIGURATION_HASH_MISMATCH")
    need(set(config) == set(GENERATION) | {"repetition_penalty", "min_new_tokens", "pad_token_id", "eos_token_ids"},
         "GENERATION_FIELDS_UNSUPPORTED", "UNAVAILABLE")
    # Type-sensitive equality (False != 0 as JSON) and all frozen generation settings.
    need(digest({k: config[k] for k in GENERATION}) == digest(GENERATION), "FROZEN_GENERATION")
    need(type(config["repetition_penalty"]) in (int, float)
         and config["repetition_penalty"] == 1.0 and config["min_new_tokens"] is None
         and type(config["pad_token_id"]) is int and config["pad_token_id"] == 0,
         "GENERATION_CONSTRAINTS")
    eos = _ids(config["eos_token_ids"], vocabulary, "EOS_CONFIG", 8)
    need(len(set(eos)) == len(eos) and set(eos) <= set(special), "EOS_CONFIG")
    need(_ids(raw["eos_token_ids"], vocabulary, "EOS_CONFIG_MISMATCH", 8) == eos, "EOS_CONFIG_MISMATCH")
    ids = _ids(raw["generated_ids"], vocabulary, "GENERATED_IDS", 64)
    inputs = _ids(raw["input_ids"], vocabulary, "INPUT_IDS")
    rendered = _ids(packet["rendered_prompt_ids"], vocabulary, "RENDERED_PROMPT_IDS")
    tail = min(32, len(inputs), len(rendered))
    need(tail >= 8 and inputs[-tail:] == rendered[-tail:], "ACTUAL_INPUT_BOUNDARY_CHANGED")
    need(native["sequence_semantics"] == "continuation_only_inputs_embeds"
         and _ids(native["generated_ids"], vocabulary, "NATIVE_GENERATED_IDS", 64) == ids
         and _ids(native["input_ids"], vocabulary, "NATIVE_INPUT_IDS") == inputs,
         "NATIVE_PATH_CUSTODY_MISMATCH")
    need(raw["logit_capture_boundary"] == "minicpm_llm_forward", "CAPTURE_BOUNDARY")
    need(raw["capture_error"] is None and raw["raw_nonfinite"] is False, "CAPTURE_FAILURE")
    need(raw["actual_logits_processors"] == [], "NONEMPTY_OR_UNKNOWN_PROCESSORS")
    steps = raw["steps"]
    need(type(steps) is list and len(steps) == len(ids), "FORWARD_GENERATION_STEP_COUNT")
    for i, (step, token) in enumerate(zip(steps, ids)):
        need(type(step["step"]) is int and step["step"] == i, "STEP_INDEX_MISMATCH")
        need(type(step["argmax"]) is int and step["argmax"] == token
             and step["all_finite"] is True, "RAW_GREEDY_ALIGNMENT_OR_FINITE_FAIL")
        need(step["origin"] == ORIGIN, "RAW_LOGIT_ORIGIN")
        logits = step["raw_candidate_logits"]
        need(type(logits) is dict and len(logits) <= 2048, "SPARSE_LOGIT_SCHEMA")
        for key, value in logits.items():
            need(key.isascii() and key.isdecimal() and str(int(key)) == key
                 and int(key) in vocabulary, "SPARSE_TOKEN_ID")
            need(type(value) in (int, float) and math.isfinite(value), "RAW_LOGIT_TYPE_OR_FINITE")
        if str(token) in logits:
            need(all(z <= logits[str(token)] for z in logits.values()), "SPARSE_ARGMAX_CONTRADICTION")
    # Single-sequence greedy generation stops on first EOS; no post-EOS padding.
    terminal = ids[-1] in eos
    body = ids[:-1] if terminal else ids
    need(body and not set(body).intersection(special), "INTERNAL_SPECIAL_OR_EOS")
    need(terminal or len(ids) == config["max_new_tokens"], "MISSING_TERMINAL_EOS", "UNAVAILABLE")
    need(len(body) * len(vocab) <= MAX_TRIALS, "SEARCH_RESOURCE_BOUND", "UNAVAILABLE")
    response = raw["response"]
    need(type(response) is str, "RESPONSE_TYPE")
    label = parse_label(response)
    need(label in LEVELS and packet["label"] == label, "NO_VALID_GENERATED_LABEL", "UNAVAILABLE")
    need(_decode(decoder, ids, True) == response == _decode(decoder, body), "ACTUAL_DECODE_MISMATCH")
    # Locate a literal canonical label, not an escaped/rescued interpretation.
    need(response.count(label) == 1, "LABEL_TEXT_BOUNDARY", "UNAVAILABLE")
    before, after = response.split(label)
    surfaces = tuple(before + level + after for level in LEVELS)
    need(all(parse_label(s) == l for s, l in zip(surfaces, LEVELS)), "LABEL_SURFACE")
    context = inputs[-tail:]
    context_text = _decode(decoder, context)
    actual_context = _decode(decoder, context + body)
    need(actual_context.endswith(response), "ACTUAL_CONTEXT_DECODE_MISMATCH")
    prefix = actual_context[:-len(response)]
    need(prefix.startswith(context_text) and not prefix[len(context_text):].strip(), "CONTEXT_PREFIX_CHANGED")
    return body, context, prefix, surfaces, label


def _matches(decoder, sequence, context, prefix, surfaces, terminal):
    text = _decode(decoder, sequence)
    if text not in surfaces:
        return None
    index = surfaces.index(text)
    # No standalone-decoding equivalence shortcut at the native boundary.
    if (_decode(decoder, context + sequence) != prefix + text
            or _decode(decoder, sequence + terminal, True) != text):
        return None
    return index


def _builder_search(decoder, body, context, prefix, surfaces, terminal):
    families = []
    for position in range(len(body)):
        matches = [[] for _ in LEVELS]
        for token in sorted(set(decoder.vocabulary) - set(decoder.special_ids)):
            sequence = body[:position] + (token,) + body[position + 1:]
            index = _matches(decoder, sequence, context, prefix, surfaces, terminal)
            if index is not None:
                matches[index].append(sequence)
        if all(matches):
            need(all(len(m) == 1 for m in matches), "AMBIGUOUS_TOKEN_BRANCH", "UNAVAILABLE")
            families.append((position, tuple(m[0] for m in matches)))
    need(len(families) == 1, "AMBIGUOUS_DECISION_STEP" if families else "NO_SINGLE_TOKEN_FAMILY", "UNAVAILABLE")
    return families[0]


def _search(role, function, decoder, arguments, cache):
    if cache is None:
        return function(decoder, *arguments)
    need(type(cache) is EnumerationCache, "CACHE_TYPE")
    return cache.search(role, decoder, arguments, lambda: function(decoder, *arguments))


def build_proof(packet, decoder, seal, *, cache=None):
    """Exhaustive single-token substitution; never encode/retokenize the output.

    Raises Refusal for missing, ambiguous or contradictory evidence. Search is
    over the complete sealed vocabulary, NOT just saved sparse logit keys.
    """
    body, context, prefix, surfaces, label = _prepare(packet, decoder, seal)
    terminal = tuple(packet["raw"]["generated_ids"][len(body):])
    position, sequences = _search("builder", _builder_search, decoder,
                                 (body, context, prefix, surfaces, terminal), cache)
    return Proof(position, sequences, seal.evidence_sha256)


def _verifier_search(decoder, body, context, prefix, surfaces, terminal):
    alternatives = {}
    for token in sorted(set(decoder.vocabulary) - set(decoder.special_ids)):
        for position in range(len(body)):
            candidate = list(body)
            candidate[position] = token
            index = _matches(decoder, tuple(candidate), context, prefix, surfaces, terminal)
            if index is not None:
                alternatives.setdefault(position, {}).setdefault(index, set()).add(token)
    return tuple((p, tuple(tuple(sorted(labels[i])) for i in range(4)))
                 for p, labels in sorted(alternatives.items()) if set(labels) == set(range(4)))


def verify_unavailable(packet, decoder, seal, *, cache=None):
    """Independently enumerate all positions even when the builder refuses.

    This is negative evidence only. It cannot produce a numeric HNLO or select
    an alias by availability of its sparse coordinate.
    """
    body, context, prefix, surfaces, label = _prepare(packet, decoder, seal)
    terminal = tuple(packet["raw"]["generated_ids"][len(body):])
    complete = _search("verifier", _verifier_search, decoder,
                       (body, context, prefix, surfaces, terminal), cache)
    if any(any(len(tokens) != 1 for tokens in labels) for _, labels in complete):
        reason = "AMBIGUOUS_TOKEN_BRANCH"
    elif len(complete) != 1:
        reason = "AMBIGUOUS_DECISION_STEP" if complete else "NO_SINGLE_TOKEN_FAMILY"
    else:
        step, labels = complete[0]
        reason = "MISSING_DECISION_LOGITS" if any(str(t[0]) not in
            packet["raw"]["steps"][step]["raw_candidate_logits"] for t in labels) else None
    return {"reason": reason, "complete_families": complete, "hnlo": None}


def verify_proof(packet, proof, decoder, seal, *, cache=None):
    """Rebuild structure and exhaustively check uniqueness with a second decoder.

    Does not invoke build_proof or trust its decision/prefix/suffix. Returns a
    derived synthetic receipt; never mutates a stored result or production raw.
    """
    body, context, prefix, surfaces, label = _prepare(packet, decoder, seal)
    terminal = tuple(packet["raw"]["generated_ids"][len(body):])
    need(type(proof) is Proof and proof.evidence_sha256 == seal.evidence_sha256, "PROOF_EVIDENCE_BINDING")
    seqs = proof.sequences
    need(type(seqs) is tuple and len(seqs) == 4
         and all(type(s) is tuple and len(s) == len(body)
                 and all(type(t) is int for t in s) for s in seqs), "PROOF_SEQUENCE_SHAPE")
    differences = [i for i in range(len(body)) if len({s[i] for s in seqs}) > 1]
    need(len(differences) == 1, "PROOF_NOT_SINGLE_BRANCH")
    d = differences[0]
    need(type(proof.decision_step) is int and proof.decision_step == d, "PROOF_DECISION_STEP")
    need(len({s[d] for s in seqs}) == 4 and seqs[LEVELS.index(label)] == body, "PROOF_ACTUAL_PATH")
    for index, sequence in enumerate(seqs):
        need(sequence[:d] == body[:d] and sequence[d + 1:] == body[d + 1:], "PROOF_PREFIX_SUFFIX")
        need(_matches(decoder, sequence, context, prefix, surfaces, terminal) == index, "INDEPENDENT_BRANCH_DECODE")
    # Independently collect (position, label) -> token sets, including alternatives
    # omitted by the builder. Do not use its candidate list as the search domain.
    complete = dict(_search("verifier", _verifier_search, decoder,
                           (body, context, prefix, surfaces, terminal), cache))
    need(set(complete) == {d}, "INDEPENDENT_DECISION_AMBIGUITY", "UNAVAILABLE")
    need(all(complete[d][i] == (seqs[i][d],) for i in range(4)), "INDEPENDENT_TOKEN_AMBIGUITY", "UNAVAILABLE")
    step = packet["raw"]["steps"][d]
    keys = [str(s[d]) for s in seqs]
    need(all(k in step["raw_candidate_logits"] for k in keys), "MISSING_DECISION_LOGITS", "UNAVAILABLE")
    values = [step["raw_candidate_logits"][k] for k in keys]
    score, independent = hnlo(values), oracle(values)
    need(math.isfinite(score) and math.isfinite(independent)
         and math.isclose(score, independent, rel_tol=1e-10, abs_tol=1e-10), "CPU_ORACLE_FAIL")
    result = {"schema": SCHEMA, "scope": packet["scope"], "status": "PASS", "reason": None,
              "qualification": "PENDING_INDEPENDENT_AUDIT" if packet["scope"] == SAVED_SCOPE else "REAL_MINICPM_UNVERIFIED", "hnlo": score, "oracle_hnlo": independent,
              "decision_step": d, "token_ids": dict(zip(LEVELS, (s[d] for s in seqs))),
              "raw_logits": dict(zip(LEVELS, values)), "generated_label": label,
              "evidence_sha256": seal.evidence_sha256, "tokenizer_sha256": seal.tokenizer_sha256,
              "vocabulary_sha256": seal.vocabulary_sha256,
              "proof_sha256": digest({"step": d, "sequences": seqs, "evidence": seal.evidence_sha256})}
    return {**result, "receipt_sha256": digest(result)}


def evaluate(packet, native_decoder, independent_decoder, seal, *, proof=None, cache=None):
    """Fail-closed entrypoint. Rejections always carry hnlo=None, never a score."""
    try:
        need(native_decoder is not independent_decoder
             and native_decoder.decode is not independent_decoder.decode, "INDEPENDENT_DECODER_REQUIRED", "UNAVAILABLE")
        built = build_proof(packet, native_decoder, seal, cache=cache)
        if proof is not None:
            need(proof == built, "SUPPLIED_PROOF_MISMATCH")
        return verify_proof(packet, built, independent_decoder, seal, cache=cache)
    except Refusal as error:
        status, reason = error.status, error.reason
    except (KeyError, IndexError) as error:
        status, reason = "UNAVAILABLE", "MISSING_EVIDENCE:" + str(error)
    except (TypeError, ValueError, ArithmeticError, AttributeError):
        status, reason = "FAIL", "MALFORMED_EVIDENCE_OR_NUMERIC_FAILURE"
    scope = packet.get("scope", SCOPE) if type(packet) is dict else SCOPE
    return {"schema": SCHEMA, "scope": scope, "status": status, "reason": reason,
            "qualification": "REAL_MINICPM_UNVERIFIED", "hnlo": None}
