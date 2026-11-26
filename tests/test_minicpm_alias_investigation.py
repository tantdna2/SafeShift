"""Synthetic adversarial checks; never reads official sample artifacts."""
import copy
import math
from types import SimpleNamespace
import unittest

from scripts import investigate_minicpm_aliases as investigation
from safeshift.evaluation import hnlo_method_a as a
from test_hnlo_method_a import fixture, seal


def witness_fixture():
    # Handwritten text and token path, not copied from an official record.
    pieces = dict(enumerate(('P', 'R', 'E', ':', 'L', 'e', 'vel', '0', '!'), 10))
    pieces.update({20: 'Level04:synthetic context ', 2: '<eos>'})
    for digit, pair in enumerate(investigation.ALIASES, 1):
        pieces.update({t: str(digit) for t in pair})
    ids = list(range(10, 18)) + [investigation.ALIASES[3][1], 18, 2]
    decoder = SimpleNamespace(vocabulary=tuple(pieces), special_ids=(2,),
        decode=lambda seq, skip: ''.join(pieces[t] for t in seq if not skip or t != 2))
    raw = {'input_ids': [20], 'generated_ids': ids, 'eos_token_ids': [2],
           'response': 'PRE:Level04!', 'actual_logits_processors': [],
           'steps': [{'all_finite': True, 'vocab_size': 73448, 'argmax': t,
                      'raw_candidate_logits': {k: 0. for k in investigation.SAVED}} for t in ids]}
    return {'raw': raw, 'label': 'Level04'}, decoder


class AliasInvestigationTests(unittest.TestCase):
    def test_full_input_including_label_text_is_not_rewritten(self):
        packet, decoder = witness_fixture()
        original = copy.deepcopy(packet)
        result = investigation.alias_witness(packet, (decoder, decoder))
        self.assertTrue(result['incremental_prefix'])
        self.assertEqual(packet, original)
        self.assertNotIn('hnlo', result)

    def test_finite_processors_actual_path_and_sparse_coordinates_fail_closed(self):
        changes = [
            lambda r: r.update(actual_logits_processors=['suppress']),
            lambda r: r['steps'][8].update(all_finite=False),
            lambda r: r['steps'][8].update(argmax=0),
            lambda r: r['steps'][8]['raw_candidate_logits'].update({'1138': 1.}),
            lambda r: r['steps'].pop(),
            lambda r: r['generated_ids'].__setitem__(8, investigation.ALIASES[3][0]),
        ]
        for change in changes:
            p, d = witness_fixture()
            change(p['raw'])
            with self.subTest(change=change), self.assertRaises(ValueError):
                investigation.alias_witness(p, (d, d))

    def test_special_alias_and_context_sensitive_decoder_rejected(self):
        p, d = witness_fixture()
        d.special_ids = (2, 1138)
        with self.assertRaisesRegex(ValueError, 'TOKEN_DOMAIN'):
            investigation.alias_witness(p, (d, d))
        p, d = witness_fixture()
        original = d.decode
        d.decode = lambda ids, skip: ('WRONG' if 20 in ids and 1138 in ids else original(ids, skip))
        with self.assertRaisesRegex(ValueError, 'CONTEXT_OR_EOS'):
            investigation.alias_witness(p, (d, d))

    def test_full_vocabulary_logits_do_not_cure_method_a_ambiguity(self):
        p, n, r, _ = fixture(alias=True)
        for step in p['raw']['steps']:
            full = {str(i): -10. for i in n.vocabulary}
            full.update(step['raw_candidate_logits'])
            full[str(step['argmax'])] = 5.
            step['raw_candidate_logits'] = full
        s = seal(p, n)
        self.assertEqual(a.evaluate(p, n, r, s)['reason'], 'AMBIGUOUS_TOKEN_BRANCH')
        self.assertEqual(a.verify_unavailable(p, r, s)['reason'], 'AMBIGUOUS_TOKEN_BRANCH')
        self.assertIsNone(a.evaluate(p, n, r, s)['hnlo'])

    def test_sparse_plus_argmax_and_finite_cannot_recover_missing_alias_mass(self):
        # An identifiability counterexample, NOT an estimator or a revised HNLO.
        known = [3., 2., 1., 0.]
        completions = [known + [-10.] * 4, known + [-1., -10., -10., -10.]]
        for vector in completions:
            self.assertEqual(vector[:4], known)
            self.assertTrue(all(math.isfinite(z) for z in vector))
            self.assertEqual(max(range(8), key=vector.__getitem__), 0)
        self.assertNotEqual(sum(math.exp(z) for z in completions[0][4:]),
                            sum(math.exp(z) for z in completions[1][4:]))

    def inventory_fixture(self):
        root = 'data/processed/candidate160/'
        src = 'data/processed/candidate160_code/' + investigation.b.SOURCE_SHA + '/'
        return [root + 'synthetic/a.json', src + 'pkg/a.py',
                src + 'pkg/__pycache__/a.cpython-313.pyc'], ['a.json'], ['pkg/a.py'], 'synthetic'

    def test_inventory_exact_membership_and_source_bytecode(self):
        self.assertEqual(investigation.classify_inventory(*self.inventory_fixture()),
                         {'archive_member': 1, 'source_file': 1, 'source_bytecode': 1})

    def test_extra_json_vector_missing_member_unknown_bytecode_or_duplicate_rejected(self):
        for extra in ('data/processed/candidate160/extra_logits.json',
                      'data/processed/candidate160/synthetic/extra.json',
                      'data/processed/candidate160_code/' + investigation.b.SOURCE_SHA
                      + '/pkg/__pycache__/unknown.cpython-313.pyc'):
            args = self.inventory_fixture()
            args[0].append(extra)
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                investigation.classify_inventory(*args)
        args = self.inventory_fixture()
        args[0].append(args[0][0])
        with self.assertRaisesRegex(ValueError, 'DUPLICATE'):
            investigation.classify_inventory(*args)
        args = self.inventory_fixture()
        args[0].pop(0)
        with self.assertRaisesRegex(ValueError, 'ARCHIVE_MEMBERSHIP'):
            investigation.classify_inventory(*args)


if __name__ == '__main__':
    unittest.main()
