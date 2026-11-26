"""One bounded CPU comparison: archived P2.1 syntax versus frozen peer HNLO.

Synthetic text/character tokens only. No model, private raw, dataset or GPU.
The P2.1 function already preserved for Qwen is compared to its exact archive;
it is never installed as the InternVL or MiniCPM parser.
"""
import ast
import copy
import inspect
import subprocess
import unittest
from unittest.mock import patch

from safeshift.candidates.source import ROOT
from safeshift.fulltrain import qwen_semantics as p21
from safeshift.pilot.contract import LEVELS, parse_label
from safeshift.pilot import hnlo
from test_pilot import raw, TextTokenizer

LEGACY = '31a04e6f7175cca818c63b4de0153246b3f3ecdb'


class FormatDecisionTests(unittest.TestCase):
    def test_p21_parser_function_matches_archived_source(self):
        archived = subprocess.check_output(['git', 'show', LEGACY + ':safeshift/protocol/p21_schema.py'], cwd=ROOT)
        original = next(n for n in ast.parse(archived).body if isinstance(n, ast.FunctionDef) and n.name == 'parse_classification')
        current = ast.parse(inspect.getsource(p21.parse_classification)).body[0]
        self.assertEqual(ast.dump(original), ast.dump(current))

    def test_exact_plain_and_single_fence_acceptance_raw_unchanged(self):
        for label in LEVELS:
            plain = '{"safety_level":"' + label + '"}'
            for opener in ('```', '```json'):
                for newline in ('\n', '\r\n'):
                    fenced = opener + newline + plain + newline + '```'
                    original = fenced.encode()
                    self.assertEqual(parse_label(plain), label)
                    self.assertIsNone(parse_label(fenced))
                    self.assertEqual(p21.parse_classification(fenced).value.safety_level, label)
                    self.assertEqual(fenced.encode(), original)
                    self.assertIsNone(parse_label(fenced))  # Historical strict status unchanged.

    def test_p21_rejects_noncanonical_and_nonwhole_response(self):
        plain = '{"safety_level":"Level03"}'
        fenced = '```json\n' + plain + '\n```'
        malformed = ('{', '{"safety_level":"Level03",}', '{"safety_level":NaN}',
            '{"safety_level":"Level03","extra":0}',
            '{"safety_level":"Level01","safety_level":"Level03"}',
            '{"safety_level":"Level05"}', '{"safety_level":"no abnormalities observed"}',
            '[]', 'Level03')
        cases = malformed + tuple('```json\n' + s + '\n```' for s in malformed) + (
            'Answer: ' + fenced, fenced + '\nExplanation', fenced + '\n' + fenced,
            plain + plain, '```json\n' + plain, '```JSON\n' + plain + '\n```',
            '```json ' + plain + '```', '````json\n' + plain + '\n````')
        for text in cases:
            with self.subTest(text=text): self.assertFalse(p21.parse_classification(text).success)

    def test_acceptance_change_alone_does_not_fix_native_hnlo(self):
        r = raw(); self.assertEqual(hnlo.replay(r, 'Level04')['status'], 'HNLO_VALIDATED')
        r['response'] = '```json\n' + r['response'] + '\n```'
        r['generated_ids'] = TextTokenizer().encode(r['response'])
        logits = r['steps'][0]['raw_candidate_logits']
        r['steps'] = [{'step':i, 'argmax':token, 'all_finite':True, 'raw_candidate_logits':dict(logits)}
                      for i,token in enumerate(r['generated_ids'])]
        r['cpu_tokenizer_replay'] = hnlo.tokenizer_replay(r, TextTokenizer())
        original = copy.deepcopy(r)
        label = p21.parse_classification(r['response']).value.safety_level
        self.assertEqual(hnlo.replay(r, label)['reason'], 'NO_VALID_GENERATED_LABEL')
        # A synthetic isolated acceptance substitution still cannot align the
        # whole fenced continuation to the frozen bare-JSON candidate surfaces.
        with patch.object(hnlo, 'parse_label', return_value=label):
            self.assertEqual(hnlo.replay(r, label)['reason'], 'ACTUAL_OUTPUT_NOT_ONE_OF_PROVEN_NATIVE_CONTINUATIONS')
        self.assertEqual(r, original)

    def test_grammar_is_not_qualified_even_when_raw_argmax_agrees(self):
        r = raw()
        r['actual_logits_processors'] = ['transformers.generation.logits_process.PrefixConstrainedLogitsProcessor']
        self.assertTrue(all(s['argmax'] == token for s,token in zip(r['steps'], r['generated_ids'])))
        result = hnlo.replay(r, 'Level04')
        self.assertEqual(result['reason'], 'NONEMPTY_OR_UNKNOWN_PROCESSORS')
        self.assertIsNone(result['hnlo'])
