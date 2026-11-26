"""Independent handwritten synthetic semantics; NOT a MiniCPM tokenizer audit."""
import copy
from dataclasses import replace
from decimal import Decimal, localcontext
import hashlib
import math
import random
import unittest
from unittest.mock import patch

from safeshift.evaluation import hnlo_method_a as a
from safeshift.pilot.contract import GENERATION, LEVELS, digest
from safeshift.pilot.hnlo import branch, replay


def fixture(label="Level04", *, opening=4788, leading=0, alias=False, values=None):
    # The noncanonical ID is deliberately generated without any encoder call.
    pieces = {4788: '{"', 10354: ' {"', 7: 'safety_level":"Level', 8: '"}',
              11: '01', 12: '02', 13: '03', 14: '04', 9: ' ', 2: '<eos>', 0: '<pad>',
              **{i: 'P' for i in range(100, 108)}}
    if alias:
        pieces[21] = '01'
    serialization = repr(sorted(pieces.items())).encode()
    vocabulary = tuple(pieces)

    def native(ids, skip):
        text = ''.join(pieces[t] for t in ids if not skip or t not in (0, 2))
        return text[1:] if text.startswith(' ') else text

    # Separate reference decoding algorithm, not a call to native().
    table = tuple(sorted(pieces.items()))

    def independent(ids, skip):
        result = []
        for token in ids:
            if skip and token in (0, 2):
                continue
            result.extend(next(value for key, value in table if key == token))
        if result and result[0] == ' ':
            del result[0]
        return ''.join(result)

    decoders = [a.Decoder(serialization, vocabulary, (0, 2), f) for f in (native, independent)]
    ids = [9] * leading + [opening, 7, 11 + LEVELS.index(label), 8, 2]
    inputs = list(range(100, 108))
    config = {**GENERATION, "eos_token_ids": [2], "pad_token_id": 0,
              "repetition_penalty": 1.0, "min_new_tokens": None}
    if values is None:
        values = [0., 0., 0., 0.]
        values[LEVELS.index(label)] = 2.
    logits = dict(zip(map(str, range(11, 15)), values))
    raw = {"generated_ids": ids, "input_ids": inputs, "response": native(tuple(ids), True),
           "eos_token_ids": [2], "logit_capture_boundary": "minicpm_llm_forward",
           "tokenizer_serialization_sha256": hashlib.sha256(serialization).hexdigest(),
           "capture_error": None, "raw_nonfinite": False, "actual_logits_processors": [],
           "steps": [{"step": i, "argmax": t, "all_finite": True, "origin": a.ORIGIN,
                      "raw_candidate_logits": copy.deepcopy(logits)} for i, t in enumerate(ids)]}
    provenance = {**{k: digest("synthetic-" + k) for k in
                    ("source_sha256", "descriptor_sha256", "input_sha256", "prompt_sha256")},
                  **{k: "synthetic-" + k for k in
                     ("sample_id", "run_id", "attempt_id", "series_id", "implementation_id")},
                  "configuration_sha256": digest(config),
                  "tokenizer_sha256": raw["tokenizer_serialization_sha256"],
                  "model_id": "openbmb/MiniCPM-V-4", "model_revision": "a" * 40,
                  "runtime_commit": "b" * 40}
    packet = {"schema": a.SCHEMA, "scope": a.SCOPE, "label": label,
              "provenance": provenance, "config": config, "raw": raw,
              "rendered_prompt_ids": inputs[:],
              "native": {"generated_ids": ids[:], "input_ids": inputs[:],
                         "sequence_semantics": "continuation_only_inputs_embeds"}}
    return packet, *decoders, seal(packet, decoders[0])


def seal(packet, decoder):
    # Test-only independent custody stand-in. Production must NOT self-seal raw.
    return a.Seal(digest(packet), hashlib.sha256(decoder.serialization).hexdigest(),
                  digest({"ids": sorted(decoder.vocabulary), "special_ids": sorted(decoder.special_ids)}))


def numeric_reference(values):
    # Direct high precision exponent/sum/log, unlike the shifted production oracle.
    with localcontext() as ctx:
        ctx.prec = 90
        z = [Decimal.from_float(float(v)) for v in values]
        return float(sum(v.exp() for v in z[:3]).ln() - z[3])


class MethodATests(unittest.TestCase):
    def reject(self, packet, native, independent, expected, *, original_seal=None):
        result = a.evaluate(packet, native, independent, original_seal or seal(packet, native))
        self.assertNotEqual(result["status"], "PASS", result)
        self.assertIsNone(result["hnlo"])
        self.assertIn(expected, result["reason"])
        self.assertNotIn("raw_logits", result)
        return result

    def test_all_labels_noncanonical_path_and_independent_numeric(self):
        for label in LEVELS:
            with self.subTest(label=label):
                p, n, r, s = fixture(label)
                proof = a.build_proof(p, n, s)
                self.assertEqual(proof.decision_step, 2)
                self.assertEqual(proof.sequences, tuple((4788, 7, t, 8) for t in range(11, 15)))
                result = a.evaluate(p, n, r, s)
                self.assertEqual(result["status"], "PASS", result)
                self.assertEqual(result["qualification"], "REAL_MINICPM_UNVERIFIED")
                self.assertAlmostEqual(result["hnlo"], numeric_reference(list(result["raw_logits"].values())), places=12)
                self.assertEqual(a.verify_proof(p, proof, r, s), result)

    def test_4788_10354_same_standalone_not_interchangeable(self):
        p, n, r, s = fixture()
        self.assertEqual(n.decode((4788,), False), n.decode((10354,), False))
        self.assertNotEqual(n.decode((100, 4788), False), n.decode((100, 10354), False))
        proof = a.build_proof(p, n, s)
        wrong = replace(proof, sequences=tuple((10354,) + row[1:] for row in proof.sequences))
        result = a.evaluate(p, n, r, s, proof=wrong)
        self.assertIsNone(result["hnlo"])
        self.assertEqual(result["reason"], "SUPPLIED_PROOF_MISMATCH")

    def test_old_replay_still_rejects_noncanonical_path(self):
        p, n, r, s = fixture()
        old = copy.deepcopy(p["raw"])
        seqs = {l: [10354, 7, 11 + i, 8] for i, l in enumerate(LEVELS)}
        old["token_probe"] = {"actual_boundary_tokens": p["raw"]["input_ids"],
            "boundary_tokens": p["raw"]["input_ids"], "boundary_ok": True,
            "mappings": [{"sequences": seqs, "decision": branch(seqs), "roundtrip": True,
                          "prefix_ok": True, "surface": '{"safety_level":"%s"}'}]}
        old["cpu_tokenizer_replay"] = {"status": "PASS"}
        self.assertEqual(replay(old, "Level04")["reason"], "ACTUAL_OUTPUT_NOT_ONE_OF_PROVEN_NATIVE_CONTINUATIONS")
        self.assertEqual(a.evaluate(p, n, r, s)["status"], "PASS")

    def test_canonical_path_is_a_distinct_valid_family(self):
        p, n, r, s = fixture(opening=10354)
        self.assertEqual(a.evaluate(p, n, r, s)["status"], "PASS")
        self.assertEqual(a.build_proof(p, n, s).sequences[0][0], 10354)

    def test_offsets_whitespace_and_max_length_without_eos(self):
        for leading in (0, 1, 3, 59, 60):
            p, n, r, _ = fixture(leading=leading)
            if leading == 60:
                p["raw"]["generated_ids"].pop()
                p["raw"]["steps"].pop()
                p["native"]["generated_ids"].pop()
            result = a.evaluate(p, n, r, seal(p, n))
            self.assertEqual(result["status"], "PASS", result)
            self.assertEqual(result["decision_step"], leading + 2)

    def test_exhaustive_alias_search_includes_tokens_missing_from_logits(self):
        p, n, r, s = fixture(alias=True)
        self.assertNotIn("21", p["raw"]["steps"][2]["raw_candidate_logits"])
        self.reject(p, n, r, "AMBIGUOUS_TOKEN_BRANCH")

    def test_independent_decoder_finds_alias_omitted_by_builder(self):
        p, n, r, _ = fixture(alias=True)
        original = n.decode
        n = replace(n, decode=lambda ids, skip: "not JSON" if 21 in ids else original(ids, skip))
        self.reject(p, n, r, "INDEPENDENT_TOKEN_AMBIGUITY")

    def test_multiple_decision_steps_are_ambiguous(self):
        p, n, r, _ = fixture()
        # Deliberately context-dependent toy semantics: either position can carry
        # a complete four-way decision. Neither is selected by score or order.
        def override(original):
            def decode(ids, skip):
                if ids[-1:] == (2,) and skip:
                    return decode(ids[:-1], skip)
                if len(ids) >= 4 and ids[-4] == 4788 and ids[-2] == 14 and ids[-1] in (11, 12, 13):
                    return original(ids[:-1] + (8,), skip).replace("Level04", LEVELS[ids[-1] - 11])
                return original(ids, skip)
            return decode
        n, r = replace(n, decode=override(n.decode)), replace(r, decode=override(r.decode))
        self.reject(p, n, r, "AMBIGUOUS_DECISION_STEP")

    def test_context_dependent_candidate_decode_mismatch(self):
        p, n, r, _ = fixture()
        def broken(original):
            return lambda ids, skip: original(ids, skip) + ("x" if ids[:1] == (100,) and 11 in ids else "")
        n, r = replace(n, decode=broken(n.decode)), replace(r, decode=broken(r.decode))
        self.reject(p, n, r, "NO_SINGLE_TOKEN_FAMILY")

    def test_independent_context_mismatch(self):
        p, n, r, _ = fixture()
        original = r.decode
        r = replace(r, decode=lambda ids, skip: original(ids, skip) + ("x" if ids[:1] == (100,) and 11 in ids else ""))
        self.reject(p, n, r, "INDEPENDENT_BRANCH_DECODE")

    def test_candidate_eos_decode_must_also_preserve_surface(self):
        p, n, r, _ = fixture()
        def broken(original):
            return lambda ids, skip: original(ids, skip) + ("extra" if skip and ids[-1:] == (2,) and 11 in ids else "")
        self.reject(p, replace(n, decode=broken(n.decode)), replace(r, decode=broken(r.decode)), "NO_SINGLE_TOKEN_FAMILY")

    def test_prefix_specific_logits_cannot_be_substituted_under_old_seal(self):
        p, n, r, s = fixture(values=[1., 2., 3., 4.])
        q, n2, r2, s2 = fixture(opening=10354, values=[-3., -2., -1., 10.])
        first, second = a.evaluate(p, n, r, s), a.evaluate(q, n2, r2, s2)
        self.assertEqual((first["status"], second["status"]), ("PASS", "PASS"))
        self.assertNotEqual(first["hnlo"], second["hnlo"])
        p["raw"]["steps"][2] = copy.deepcopy(q["raw"]["steps"][2])
        self.reject(p, n, r, "EVIDENCE_SEAL_MISMATCH", original_seal=s)

    def test_equal_surface_different_lengths_are_not_retokenized(self):
        p, n, r, s = fixture()
        proof = a.build_proof(p, n, s)
        # Both decode with the same leading-space strip, but are not equal IDs.
        long = (9,) + proof.sequences[0]
        self.assertEqual(n.decode(long, False), n.decode(proof.sequences[0], False))
        with self.assertRaisesRegex(a.Refusal, "PROOF_SEQUENCE_SHAPE"):
            a.verify_proof(p, replace(proof, sequences=(long,) + proof.sequences[1:]), r, s)

    def test_two_token_branch_and_merged_token_crossing_label_boundary(self):
        p, n, r, s = fixture()
        proof = a.build_proof(p, n, s)
        wrong = tuple((10354 if i == 0 else 4788,) + row[1:] for i, row in enumerate(proof.sequences))
        with self.assertRaisesRegex(a.Refusal, "PROOF_NOT_SINGLE_BRANCH"):
            a.verify_proof(p, replace(proof, sequences=wrong), r, s)
        # Synthetic IDs can contain the label and closing punctuation together;
        # qualify by full sequence decoding, never by a guessed token text span.
        def merged(original):
            def decode(ids, skip):
                expanded = []
                for token in ids:
                    expanded.extend((token, 8) if token in (11, 12, 13, 14) else (token,))
                return original(tuple(expanded), skip)
            return decode
        n, r = replace(n, decode=merged(n.decode)), replace(r, decode=merged(r.decode))
        for target in (p["raw"], p["native"]):
            target["generated_ids"].remove(8)
        p["raw"]["steps"].pop(3)
        p["raw"]["steps"][-1]["step"] = 3
        result = a.evaluate(p, n, r, seal(p, n))
        self.assertEqual(result["status"], "PASS", result)

    def test_independent_enumeration_of_expected_family(self):
        p, n, r, s = fixture()
        actual = tuple(p["raw"]["generated_ids"][:-1])
        expected = set()
        # Test oracle directly constructs the four known surfaces, with no
        # production branch finder, parser, _matches or candidate builder.
        for d in range(len(actual)):
            lists = [[] for _ in range(4)]
            for token in r.vocabulary:
                candidate = actual[:d] + (token,) + actual[d + 1:]
                for i in range(4):
                    text = '{"safety_level":"Level0' + str(i + 1) + '"}'
                    if (r.decode(candidate, False) == text
                            and r.decode(tuple(range(100, 108)) + candidate, False) == 'P' * 8 + text):
                        lists[i].append(candidate)
            if all(len(v) == 1 for v in lists):
                expected.add((d, tuple(v[0] for v in lists)))
        proof = a.build_proof(p, n, s)
        self.assertEqual(expected, {(proof.decision_step, proof.sequences)})

    def test_no_family_and_escaped_label(self):
        p, n, r, _ = fixture()
        # A decoder that cannot produce Level02 from any single substitution.
        def missing(original):
            return lambda ids, skip: original(ids, skip).replace("Level02", "Level99")
        self.reject(p, replace(n, decode=missing(n.decode)), replace(r, decode=missing(r.decode)), "NO_SINGLE_TOKEN_FAMILY")
        p["raw"]["response"] = '{"safety_level":"Level0\\u0034"}'
        self.reject(p, n, r, "ACTUAL_DECODE_MISMATCH")

    def test_proof_tampering_verifier_recomputes_all_fields(self):
        p, n, r, s = fixture()
        proof = a.build_proof(p, n, s)
        mutations = [replace(proof, decision_step=1), replace(proof, decision_step=True),
                     replace(proof, evidence_sha256="0" * 64),
                     replace(proof, sequences=proof.sequences[::-1]),
                     replace(proof, sequences=tuple((10354,) + x[1:] for x in proof.sequences)),
                     replace(proof, sequences=tuple(x[:-1] + (9,) for x in proof.sequences)),
                     replace(proof, sequences=(proof.sequences[0] + (9,),) + proof.sequences[1:]),
                     replace(proof, sequences=(proof.sequences[0][:-1],) + proof.sequences[1:]),
                     replace(proof, sequences=(proof.sequences[0],) * 4)]
        for wrong in mutations:
            with self.subTest(proof=wrong), self.assertRaises(a.Refusal):
                a.verify_proof(p, wrong, r, s)

    def test_missing_sparse_logits_never_borrow_from_another_step(self):
        for key in ("11", "12", "13", "14"):
            p, n, r, _ = fixture()
            del p["raw"]["steps"][2]["raw_candidate_logits"][key]
            self.reject(p, n, r, "MISSING_DECISION_LOGITS")

    def test_logit_origin_step_order_processors_and_finite(self):
        mutations = [lambda p: p["raw"]["steps"][0].update(step=1),
                     lambda p: p["raw"]["steps"].reverse(),
                     lambda p: p["raw"]["steps"].pop(),
                     lambda p: p["raw"]["steps"][0].update(argmax=10354),
                     lambda p: p["raw"]["steps"][0].update(all_finite=False),
                     lambda p: p["raw"]["steps"][0].update(origin="processed_scores"),
                     lambda p: p["raw"].update(actual_logits_processors=["ForceEOS"]),
                     lambda p: p["raw"].update(actual_logits_processors=None),
                     lambda p: p["raw"].update(logit_capture_boundary="another_forward"),
                     lambda p: p["raw"].update(capture_error="failed")]
        for mutate in mutations:
            p, n, r, _ = fixture()
            mutate(p)
            self.reject(p, n, r, "")

    def test_false_eos_internal_special_duplicate_terminal_and_missing(self):
        for ids in ([4788, 2, 14, 8, 2], [4788, 0, 14, 8, 2],
                    [4788, 7, 14, 8, 2, 2], [4788, 7, 14, 8], [4788, 7, 14, 8, 2, 0]):
            p, n, r, _ = fixture()
            p["raw"]["generated_ids"] = list(ids)
            p["native"]["generated_ids"] = list(ids)
            step = p["raw"]["steps"][0]
            p["raw"]["steps"] = [{**step, "step": i, "argmax": t} for i, t in enumerate(ids)]
            self.reject(p, n, r, "")

    def test_eos_config_and_input_boundary(self):
        for mutate, reason in [
            (lambda p: p["raw"].update(eos_token_ids=[0]), "EOS_CONFIG_MISMATCH"),
            (lambda p: p["rendered_prompt_ids"].__setitem__(-1, 100), "ACTUAL_INPUT_BOUNDARY_CHANGED"),
            (lambda p: p["native"]["generated_ids"].__setitem__(0, 10354), "NATIVE_PATH_CUSTODY_MISMATCH"),
            (lambda p: p["native"].update(sequence_semantics="prompt_plus_continuation"), "NATIVE_PATH_CUSTODY_MISMATCH")]:
            p, n, r, _ = fixture()
            mutate(p)
            self.reject(p, n, r, reason)

    def test_invalid_json_labels_fences_duplicates_extra_text(self):
        for response in ('INVALID', '{"safety_level":"Level05"}',
                         '{"safety_level":"Level04","safety_level":"Level04"}',
                         '```json\n{"safety_level":"Level04"}\n```',
                         '{"safety_level":"Level04"} extra',
                         '{"safety_level":"Level04","explanation":"ok"}'):
            p, n, r, _ = fixture()
            p["raw"]["response"] = response
            self.reject(p, n, r, "NO_VALID_GENERATED_LABEL")
        p, n, r, _ = fixture()
        p["label"] = None
        self.reject(p, n, r, "NO_VALID_GENERATED_LABEL")

    def test_nan_inf_bool_strings_and_noncanonical_logit_keys(self):
        for value in (math.nan, math.inf, -math.inf, True, "1.0", None):
            p, n, r, s = fixture()
            p["raw"]["steps"][2]["raw_candidate_logits"]["11"] = value
            result = a.evaluate(p, n, r, s if type(value) is float else seal(p, n))
            self.assertIsNone(result["hnlo"])
            self.assertNotEqual(result["status"], "PASS")
        for key in ("011", "-1", "11.0", "999", "١١"):
            p, n, r, _ = fixture()
            p["raw"]["steps"][2]["raw_candidate_logits"][key] = 1.
            self.reject(p, n, r, "SPARSE_TOKEN_ID")

    def test_sparse_argmax_contradiction(self):
        p, n, r, _ = fixture()
        p["raw"]["steps"][2]["raw_candidate_logits"]["11"] = 100.
        self.reject(p, n, r, "SPARSE_ARGMAX_CONTRADICTION")

    def test_seals_block_rehashed_forged_provenance_configs_and_paths(self):
        for key in ("source_sha256", "input_sha256", "descriptor_sha256", "prompt_sha256",
                    "configuration_sha256", "tokenizer_sha256", "run_id", "attempt_id", "series_id",
                    "implementation_id", "model_revision", "runtime_commit"):
            p, n, r, s = fixture()
            p["provenance"][key] = "c" * len(p["provenance"][key])
            self.reject(p, n, r, "EVIDENCE_SEAL_MISMATCH", original_seal=s)
        p, n, r, s = fixture()
        p["raw"]["generated_ids"][0] = 10354
        p["native"]["generated_ids"][0] = 10354
        p["raw"]["steps"][0]["argmax"] = 10354
        self.reject(p, n, r, "EVIDENCE_SEAL_MISMATCH", original_seal=s)

    def test_generation_and_tokenizer_integrity_checks(self):
        p, n, r, _ = fixture()
        p["config"]["do_sample"] = True
        p["provenance"]["configuration_sha256"] = digest(p["config"])
        self.reject(p, n, r, "FROZEN_GENERATION")
        p, n, r, s = fixture()
        self.reject(p, replace(n, serialization=b"wrong"), r, "TOKENIZER_HASH_MISMATCH", original_seal=s)
        self.reject(p, n, replace(r, vocabulary=r.vocabulary[:-1]), "VOCABULARY_SEAL_MISMATCH", original_seal=s)
        p["provenance"]["tokenizer_sha256"] = "0" * 64
        self.reject(p, n, r, "TOKENIZER_PROVENANCE_MISMATCH")

    def test_native_and_eos_ids_require_integers_not_equal_floats(self):
        for section, key in (("native", "generated_ids"), ("native", "input_ids"), ("raw", "eos_token_ids")):
            p, n, r, _ = fixture()
            p[section][key][0] = float(p[section][key][0])
            self.reject(p, n, r, "")

    def test_unrecognized_generation_controls_are_not_ignored(self):
        p, n, r, _ = fixture()
        p["config"]["forced_eos_token_id"] = 2
        p["provenance"]["configuration_sha256"] = digest(p["config"])
        self.reject(p, n, r, "GENERATION_FIELDS_UNSUPPORTED")

    def test_missing_fields_malformed_and_real_scope(self):
        for key in ("schema", "config", "raw", "native", "provenance", "rendered_prompt_ids"):
            p, n, r, _ = fixture()
            del p[key]
            self.reject(p, n, r, "MISSING_EVIDENCE")
        p, n, r, _ = fixture()
        p["scope"] = "REAL_TRAIN160"
        self.reject(p, n, r, "SYNTHETIC_SCOPE_REQUIRED")
        p["raw"] = object()
        self.assertIsNone(a.evaluate(p, n, r, None)["hnlo"])

    def test_decoder_failure_and_independence_required(self):
        p, n, r, s = fixture()
        self.assertEqual(a.evaluate(p, n, n, s)["reason"], "INDEPENDENT_DECODER_REQUIRED")
        def fail(ids, skip):
            raise RuntimeError("synthetic")
        self.assertEqual(a.evaluate(p, n, replace(r, decode=fail), s)["reason"], "DECODER_FAILURE")

    def test_deterministic_order_no_mutation_no_io(self):
        p, n, r, s = fixture()
        before = copy.deepcopy(p)
        with patch("builtins.open", side_effect=AssertionError("NO_IO")), \
             patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
             patch("subprocess.Popen", side_effect=AssertionError("NO_PROCESS")):
            first = a.evaluate(p, n, r, s)
            second = a.evaluate(p, replace(n, vocabulary=n.vocabulary[::-1]), r, s)
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(first, second)
        self.assertEqual(p, before)
        first["token_ids"]["Level01"] = -1
        self.assertEqual(a.evaluate(p, n, r, s), second)

    def test_numeric_extremes_shifts_and_random_oracle(self):
        rng = random.Random(163)
        vectors = [[0.] * 4, [1e38] * 4, [-1000., -1001., -999., 1000.],
                   [1000., 1001., 999., -1000.]]
        vectors += [[rng.uniform(-1000, 1000) for _ in range(4)] for _ in range(30)]
        for values in vectors:
            label = LEVELS[max(range(4), key=lambda i: values[i])]
            p, n, r, s = fixture(label, values=values)
            result = a.evaluate(p, n, r, s)
            self.assertEqual(result["status"], "PASS", result)
            expected = math.log(3) if values == [1e38] * 4 else numeric_reference(values)
            self.assertAlmostEqual(result["hnlo"], expected, places=10)
            if max(abs(x) for x in values) < 1e4:
                q, n2, r2, s2 = fixture(label, values=[v + 1e4 for v in values])
                self.assertAlmostEqual(a.evaluate(q, n2, r2, s2)["hnlo"], result["hnlo"], places=9)

    def test_numeric_oracle_mismatch_is_fail_closed(self):
        p, n, r, s = fixture()
        with patch.object(a, "oracle", return_value=999.):
            self.assertEqual(a.evaluate(p, n, r, s)["reason"], "CPU_ORACLE_FAIL")

    def test_resource_bounds_and_malformed_token_types(self):
        p, n, r, s = fixture()
        with patch.object(a, "MAX_TRIALS", 1):
            self.assertEqual(a.evaluate(p, n, r, s)["reason"], "SEARCH_RESOURCE_BOUND")
        for token in (True, -1, "4788", 99999):
            p, n, r, _ = fixture()
            p["raw"]["generated_ids"][0] = token
            self.reject(p, n, r, "GENERATED_IDS")
        p, n, r, _ = fixture()
        p["raw"]["response"] = 'x' * 65_537
        self.assertEqual(a.evaluate(p, n, r, None)["reason"], "EVIDENCE_RESOURCE_BOUND")


if __name__ == "__main__":
    unittest.main()
