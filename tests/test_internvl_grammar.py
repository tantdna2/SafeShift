"""Handwritten synthetic tokens/logits only; never model predictions."""
import copy
import json
import math
from pathlib import Path
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from safeshift.diagnostic173_grammar import CanonicalJSONGrammar
from safeshift.internvl_grammar import (
    BINDING_KEYS, HNLO_STATUS, POLICY, PROCESSOR, VERSION, InternVLGrammarV2,
    greedy_token, mask_logits, validate_trace,
)
from safeshift.pilot.contract import LEVELS, digest, parse_label
from safeshift.pilot.hnlo import hnlo, oracle

ROOT = Path(__file__).resolve().parents[1]


class CharacterTokenizer:
    all_special_ids = [0, 1]

    def __len__(self):
        return 128

    def encode(self, text, **kwargs):
        return list(text.encode("ascii"))

    def decode(self, ids, skip_special_tokens=False, **kwargs):
        return "".join(chr(i) for i in ids if not skip_special_tokens or i not in self.all_special_ids)


class SegmentedTokenizer(CharacterTokenizer):
    """Three synthetic BPE-like pieces; deliberately unrelated to native IDs."""
    pieces = {2: '{"safety_level":"Level', 3: '01', 4: '02', 5: '03', 6: '04', 7: '"}', 8: 'prompt'}

    def encode(self, text, **kwargs):
        return [2, 3 + LEVELS.index(parse_label(text)), 7]

    def decode(self, ids, skip_special_tokens=False, **kwargs):
        return "".join(self.pieces.get(i, "<eos>") for i in ids
                       if not skip_special_tokens or i not in self.all_special_ids)


def fixture(label=0, forced=True, tokenizer=None, eos=0):
    tokenizer = tokenizer or CharacterTokenizer()
    grammar = InternVLGrammarV2(tokenizer, [0, 1], [8])
    ids = grammar.paths[label] + (eos,)
    steps = []
    for index, token in enumerate(ids):
        logits = [-7.0] * len(tokenizer)
        logits[token] = 2.0
        if forced and index == 0:
            logits[ord('`')] = 9.0  # Off-language native preference; no GT.
        steps.append({"step": index, "prefix_ids": list(grammar.input_ids + ids[:index]),
                      "raw_logits": logits, "masked_logits": mask_logits(grammar, ids[:index], logits)})
    binding = {k: digest("SYNTHETIC_" + k) for k in BINDING_KEYS}
    trace = {"schema": VERSION + "-trace", "binding": binding,
             "grammar": grammar.receipt(), "policy": dict(POLICY),
             "actual_logits_processors": [PROCESSOR], "capture_origin": "scripted_before_processors",
             "evidence_kind": "SYNTHETIC",
             "capture_error": None, "input_ids": list(grammar.input_ids),
             "generated_ids": list(ids), "steps": steps, "response": grammar.texts[label]}
    return grammar, tokenizer, trace, binding


class GrammarLanguageTests(unittest.TestCase):
    def test_exhaustive_language_equal_to_v1_with_two_tokenizations(self):
        for tokenizer in (CharacterTokenizer(), SegmentedTokenizer()):
            grammar = InternVLGrammarV2(tokenizer, [0, 1], [8])
            old = CanonicalJSONGrammar(tokenizer, [0, 1])
            pending, terminals = [()], set()
            while pending:
                prefix = pending.pop()
                self.assertEqual(grammar.allowed(prefix), old.allowed(prefix))
                for token in grammar.allowed(prefix):
                    if token in grammar.eos:
                        terminals.add(prefix)
                        self.assertIn(prefix, grammar.paths)
                    else:
                        pending.append(prefix + (token,))
            self.assertEqual(terminals, set(grammar.paths))
            self.assertEqual({parse_label(tokenizer.decode(p)) for p in terminals}, set(LEVELS))
            self.assertEqual(len(grammar.allowed(grammar.paths[0][:grammar.decision_step])), 4)

    def test_callback_binds_entire_input_and_single_batch(self):
        grammar, _, _, _ = fixture()
        callback = grammar.callback()
        ids = SimpleNamespace(tolist=lambda: [8])
        self.assertEqual(callback(0, ids), grammar.allowed(()))
        for batch in (1, -1, False):
            with self.assertRaises(ValueError):
                callback(batch, ids)
        for values in ([], [9], [8, 0], [8, ord('`')]):
            with self.assertRaises(ValueError):
                callback(0, SimpleNamespace(tolist=lambda: values))

    def test_prefix_range_type_and_post_eos_fail(self):
        grammar, _, _, _ = fixture()
        for prefix in ([True], [-1], [128], [1.0], "{", [ord('`')],
                       list(grammar.paths[0]) + [0], list(grammar.paths[0]) + [32]):
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                grammar.allowed(prefix)

    def test_eos_and_content_must_be_disjoint_and_valid(self):
        for eos in ([], [0, 0], -1, 128, True, ord('{')):
            with self.subTest(eos=eos), self.assertRaises(ValueError):
                InternVLGrammarV2(CharacterTokenizer(), eos, [8])
        t = CharacterTokenizer(); t.all_special_ids = [0, ord('{')]
        with self.assertRaises(ValueError):
            InternVLGrammarV2(t, 0, [8])

    def test_duplicate_or_empty_paths_fail(self):
        for ids in ([], [5]):
            t = CharacterTokenizer(); t.encode = lambda *a, **k: ids
            with self.assertRaisesRegex(ValueError, "FOUR_DISTINCT"):
                InternVLGrammarV2(t, 0, [8])

    def test_context_sensitive_decoder_fails(self):
        t = CharacterTokenizer(); original = t.decode
        t.decode = lambda ids, **k: original(ids, **k) + ("X" if len(ids) > 1 and ids[0] == 8 else "")
        with self.assertRaisesRegex(ValueError, "FIXED_INPUT_CONTEXT"):
            InternVLGrammarV2(t, 0, [8])

    def test_non_exact_decode_fails(self):
        t = CharacterTokenizer(); t.decode = lambda *a, **k: ' {"safety_level":"Level01"}'
        with self.assertRaises(ValueError):
            InternVLGrammarV2(t, 0, [8])

    def test_multi_position_label_decision_rejected(self):
        class TwoBranches(SegmentedTokenizer):
            def encode(self, text, **kwargs):
                token = 3 + LEVELS.index(parse_label(text))
                return [2, token, token, 7]
            def decode(self, ids, **kwargs):
                reduced = [v for i, v in enumerate(ids) if i == 0 or v != ids[i - 1]]
                return super().decode(reduced, **kwargs)
        with self.assertRaisesRegex(ValueError, "SINGLE_LABEL_BRANCH"):
            InternVLGrammarV2(TwoBranches(), 0, [8])

    def test_unequal_length_paths_rejected(self):
        class Unequal(SegmentedTokenizer):
            pieces = {**SegmentedTokenizer.pieces, 9: ''}
            def encode(self, text, **kwargs):
                tokens = super().encode(text, **kwargs)
                return tokens + ([9] if parse_label(text) == 'Level01' else [])
        with self.assertRaisesRegex(ValueError, "SINGLE_LABEL_BRANCH"):
            InternVLGrammarV2(Unequal(), 0, [8])

    def test_token_budget_includes_eos(self):
        class Long(SegmentedTokenizer):
            pieces = {**SegmentedTokenizer.pieces, 9: ''}
            def encode(self, text, **kwargs):
                return [9] * 61 + super().encode(text, **kwargs)
        with self.assertRaises(ValueError):
            InternVLGrammarV2(Long(), 0, [8])
        class Exact(Long):
            def encode(self, text, **kwargs):
                return [9] * 60 + SegmentedTokenizer.encode(self, text, **kwargs)
        self.assertEqual(InternVLGrammarV2(Exact(), 0, [8]).required_tokens, 64)


class GrammarTraceTests(unittest.TestCase):
    def test_all_labels_forced_and_unforced_multiple_eos_deterministic(self):
        for t in (CharacterTokenizer(), SegmentedTokenizer()):
            for label in range(4):
                for forced in (False, True):
                    for eos in (0, 1):
                        g, tokenizer, trace, binding = fixture(label, forced, t, eos)
                        original = copy.deepcopy(trace)
                        result = validate_trace(g, tokenizer, trace, binding)
                        self.assertEqual(result['label'], LEVELS[label])
                        self.assertEqual(result['forced_steps'], [0] if forced else [])
                        self.assertEqual(result['hnlo_status'], HNLO_STATUS)
                        self.assertIsNone(result['hnlo'])
                        self.assertEqual(result, validate_trace(g, tokenizer, json.loads(json.dumps(trace)), binding))
                        self.assertEqual(trace, original)

    def test_wrong_binding_version_or_grammar_rejected(self):
        for key, value in (("binding", {}), ("schema", "old"), ("grammar", {})):
            g, t, trace, b = fixture(); trace[key] = value
            with self.assertRaises(ValueError): validate_trace(g, t, trace, b)
        g, t, trace, b = fixture()
        for wrong in ({}, {**b, "source_sha256": "x" * 64}):
            with self.assertRaises(ValueError): validate_trace(g, t, trace, wrong)

    def test_config_and_processor_alterations_fail(self):
        for key, value in (("do_sample", True), ("num_beams", 2), ("batch_size", 2),
                           ("max_new_tokens", 63), ("num_return_sequences", True)):
            g, t, trace, b = fixture(); trace['policy'][key] = value
            with self.assertRaises(ValueError): validate_trace(g, t, trace, b)
        for processors in ([], None, [PROCESSOR, 'temperature'], ['unknown']):
            g, t, trace, b = fixture(); trace['actual_logits_processors'] = processors
            with self.assertRaises(ValueError): validate_trace(g, t, trace, b)

    def test_capture_error_or_processed_origin_fails(self):
        for key, value in (("capture_error", "interrupted"), ("capture_origin", "output_scores"),
                           ("evidence_kind", "NATIVE"), ("evidence_kind", "UNKNOWN")):
            g, t, trace, b = fixture(); trace[key] = value
            with self.assertRaises(ValueError): validate_trace(g, t, trace, b)

    def test_nonfinite_raw_and_wrong_vocab_fail(self):
        for value in (float('nan'), float('inf'), -float('inf'), None, True):
            g, t, trace, b = fixture(); trace['steps'][0]['raw_logits'][9] = value
            with self.assertRaises(ValueError): validate_trace(g, t, trace, b)
        g, t, trace, b = fixture(); trace['steps'][0]['raw_logits'].pop()
        with self.assertRaises(ValueError): validate_trace(g, t, trace, b)

    def test_masked_nonlanguage_or_modified_allowed_scores_fail(self):
        for pos, value in ((9, 0.0), (ord('{'), 0.0), (ord('{'), None), (9, float('nan'))):
            g, t, trace, b = fixture(); trace['steps'][0]['masked_logits'][pos] = value
            with self.assertRaisesRegex(ValueError, "MASK_OR_ALLOWED"):
                validate_trace(g, t, trace, b)

    def test_wrong_step_or_history_fails(self):
        for key, value in (("step", 1), ("step", False), ("prefix_ids", [9])):
            g, t, trace, b = fixture(); trace['steps'][0][key] = value
            with self.assertRaises(ValueError): validate_trace(g, t, trace, b)
        g, t, trace, b = fixture(); trace['steps'].pop()
        with self.assertRaises(ValueError): validate_trace(g, t, trace, b)

    def test_truncation_early_eos_duplicate_eos_extra_prose_fail(self):
        g, t, baseline, b = fixture()
        ids = baseline['generated_ids']
        for changed in (ids[:-1], [0] + ids[1:], ids + [0], ids + [32], [], ids[:-2] + [0]):
            trace = copy.deepcopy(baseline); trace['generated_ids'] = changed
            with self.assertRaises(ValueError): validate_trace(g, t, trace, b)
        for changed in (baseline['response'] + ' explanation', '```json\n' + baseline['response'] + '\n```'):
            trace = copy.deepcopy(baseline); trace['response'] = changed
            with self.assertRaises(ValueError): validate_trace(g, t, trace, b)

    def test_independent_decode_mismatch_fails(self):
        g, t, trace, b = fixture(); t.decode = lambda *a, **k: 'wrong'
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_.*DECODE"):
            validate_trace(g, t, trace, b)

    def test_wrong_greedy_label_is_not_rescued(self):
        g, t, trace, b = fixture()
        step = trace['steps'][g.decision_step]
        step['raw_logits'][g.decision_tokens[3]] = 99
        step['masked_logits'][g.decision_tokens[3]] = 99
        with self.assertRaisesRegex(ValueError, "GREEDY_MISMATCH"):
            validate_trace(g, t, trace, b)

    def test_ties_resolve_first_token_id_and_no_label_override(self):
        g, t, trace, b = fixture(forced=False)
        step = trace['steps'][g.decision_step]
        for token in g.decision_tokens:
            step['raw_logits'][token] = step['masked_logits'][token] = 2.0
        self.assertEqual(validate_trace(g, t, trace, b)['label'], 'Level01')
        self.assertEqual(greedy_token([None, 3.0, 3.0]), 1)


class GrammarScienceTests(unittest.TestCase):
    def test_qualifier_rejects_corrupt_public_source_before_loading(self):
        from scripts.qualify_internvl_grammar import native_check
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            (source / 'tokenizer.json').write_text('{}')
            with patch('urllib.request.urlopen') as network:
                with self.assertRaisesRegex(ValueError, 'PUBLIC_TOKENIZER_HASH_MISMATCH'):
                    native_check(source, source, fetch=False)
                network.assert_not_called()

    def test_evidence_writer_is_create_only_and_strict_json(self):
        from scripts.qualify_internvl_grammar import save
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'receipt.json'
            save(target, {'kind': 'SYNTHETIC', 'hnlo': None})
            saved = target.read_bytes()
            with self.assertRaises(FileExistsError): save(target, {'changed': True})
            self.assertEqual(target.read_bytes(), saved)
            with self.assertRaises(ValueError): save(Path(temp) / 'nonfinite.json', {'z': float('nan')})

    def test_descriptor_matches_implementation_and_has_no_authority(self):
        import hashlib
        descriptor = json.loads((ROOT / 'configs/grammar/internvl35_v2.json').read_text())
        g, _, _, _ = fixture()
        self.assertEqual(descriptor['id'], VERSION)
        for key in ('language', 'policy', 'hnlo', 'hnlo_status', 'actual_logits_processors_required'):
            actual_key = 'actual_processors_required' if key == 'actual_logits_processors_required' else key
            self.assertEqual(descriptor[key], g.receipt()[actual_key])
        self.assertEqual(descriptor['prompt_sha256'], hashlib.sha256((ROOT / descriptor['prompt']).read_bytes()).hexdigest())
        self.assertIsNone(descriptor['execution_authority'])
        self.assertIsNone(descriptor['scientific_approval'])
        self.assertFalse(descriptor['production_activation'])

    def test_same_prefix_mask_normalizer_cancels(self):
        # Independent normalized probability oracle, including off-label mass.
        for z in ([0, 0, 0, 2], [2, 2, 2, 0], [-3.5, 1.0, 4.0, 2.0]):
            for other in ([], [5.0, -5.0]):
                values = list(z) + other
                total = math.fsum(math.exp(x) for x in values)
                p = [math.exp(x) / total for x in z]
                self.assertAlmostEqual(math.log(sum(p[:3]) / p[3]), hnlo(z), places=12)
                self.assertAlmostEqual(oracle(z), hnlo(z), places=12)

    def test_forced_prefix_counterexample_changes_sign(self):
        hu, hg = hnlo([0, 0, 0, 2]), hnlo([2, 2, 2, 0])
        self.assertLess(hu, 0); self.assertGreater(hg, 0)
        self.assertAlmostEqual(hg - hu, 4.0)

    def test_temperature_or_missing_label_invalidates_equivalence(self):
        z = [1, 2, 3, 4]
        self.assertNotAlmostEqual(hnlo(z), hnlo([x / 2 for x in z]))
        self.assertNotAlmostEqual(math.log(math.exp(1) + math.exp(2)) - 4, hnlo(z))
        with self.assertRaises(ValueError): hnlo([1, 2, 3, -float('inf')])

    def test_local_masking_not_global_sequence_conditioning(self):
        # Two allowed first tokens, same raw mass; different allowed suffix mass.
        # Local forced suffixes give 1/2 each; global conditioning gives 1/10,9/10.
        local_a = .5
        global_a = (.5 * .1) / (.5 * .1 + .5 * .9)
        self.assertNotAlmostEqual(local_a, global_a)

    def test_existing_hnlo_still_rejects_grammar_even_if_raw_greedy_matches(self):
        from test_pilot import raw
        from safeshift.pilot.hnlo import replay
        evidence = raw(); evidence['actual_logits_processors'] = [PROCESSOR]
        result = replay(evidence, 'Level04')
        self.assertEqual(result['reason'], 'NONEMPTY_OR_UNKNOWN_PROCESSORS')
        self.assertIsNone(result['hnlo'])

    def test_prior_receipt_and_ledger_crosslink_without_private_raw_reads(self):
        root = ROOT / 'docs/research/evidence/issue173/diagnostics'
        r = json.loads((root / 'issue173-diag-intern-grammar-v2.json').read_text())
        ledger = json.loads((ROOT / 'configs/issue173/diagnostic_custody.json').read_text())
        entry = next(a for a in ledger['attempts'] if a['identity'] == r['result']['identity'])
        self.assertEqual(entry['archive_sha256'], r['archive_sha256'])
        self.assertEqual(entry['source_commit'], r['result']['source_commit'])
        self.assertEqual(r['result']['calls'], 1)
        call = r['calls'][0]
        self.assertEqual(call['actual_logits_processors'], [PROCESSOR])
        self.assertEqual(call['finite_steps'], call['generated_token_steps'])
        self.assertEqual(call['native_matches_unprocessed_argmax_steps'], 10)
        self.assertEqual(call['grammar']['path_lengths'], [9] * 4)
        self.assertEqual(call['hnlo'], 'NOT_COMPUTED_DIAGNOSTIC_LABEL_ONLY')
        self.assertNotEqual(call['grammar']['id'], VERSION)


if __name__ == '__main__':
    unittest.main()
