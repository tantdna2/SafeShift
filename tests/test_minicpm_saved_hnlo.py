"""Handwritten synthetic tests only; no official artifacts are opened."""
import copy
from collections import defaultdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from safeshift.evaluation import hnlo_method_a as a
from safeshift.evaluation import minicpm_saved_hnlo as bridge
from safeshift.pilot.contract import digest, GENERATION
from test_hnlo_method_a import fixture, seal


class MemoryArchive:
    def __init__(self, values):
        self.values = values
        self.reads = set()
        self.checksums = {k: digest(v) for k, v in values.items()}

    def json(self, path):
        self.reads.add(path)
        return copy.deepcopy(self.values[path])


def bridge_fixture():
    packet, _, _, _ = fixture()
    raw = packet['raw']
    raw['input_ids'] = [1] + raw['input_ids']
    raw['eos_token_ids'] = [73440, 2]
    for step in raw['steps']:
        step['vocab_size'] = 73448
    model = {'id': 'openbmb/MiniCPM-V-4', 'revision': bridge.REVISION}
    legacy = {'settings_snapshot': {'synthetic': True}}
    legacy_hash = digest(legacy['settings_snapshot'])
    binding = {'run_id': bridge.RUN, 'attempt_id': bridge.ATTEMPT, 'model': model,
               'legacy_transport_config_sha256': legacy_hash}
    context = {'execution_release': binding, 'configuration_contract': {'legacy_transport_compatibility': legacy}}
    identity = {**binding, 'ordinal': 0, 'sample_id': 'synthetic-0', 'input_sha256': 'a' * 64,
                'runner_manifest_sha256': 'b' * 64}
    raw.update(configuration_provenance=context, execution_release=binding,
        identity={'config_sha256': legacy_hash, 'input_sha256': 'a' * 64, 'sample_id': 'synthetic-0',
                  'run_id': bridge.RUN, 'model': model, 'manifest_sha256': 'b' * 64})
    raw['token_probe'] = {'boundary_ok': True, 'boundary_tokens': raw['input_ids'],
                          'actual_boundary_tokens': raw['input_ids']}
    generation = {**GENERATION, 'bos_token_id': 1, 'eos_token_id': [73440, 2], 'num_return_sequences': 1,
        'stop_strings': None, 'max_time': None, 'token_healing': False, 'pad_token_id': 0,
        'repetition_penalty': 1., 'min_new_tokens': None}
    prompt = 'SYNTHETIC ONLY'
    request = {'model': model, 'prompt': prompt, 'rendered_prompt': prompt,
               'input_ids': raw['input_ids'], 'token_probe': raw['token_probe'], 'generation': generation}
    native = {'input_ids': raw['input_ids'], 'generated_ids': raw['generated_ids'],
              'returned_ids': [raw['generated_ids']], 'input_prefix_match': None,
              'sequence_semantics': 'continuation_only_inputs_embeds'}
    result = {'status': 'SUCCESS', 'label': 'Level04', 'hnlo': {'hnlo': None},
              'attempts': 1, 'native_calls': 1, 'raw_sha256': digest(raw)}
    root, sample = 'calls/000000/run/', 'calls/000000/run/samples/000000/'
    values = {root + 'identity.json': identity,
              root + 'runtime.json': {'model': model, 'prompt_sha256': bridge.sha(prompt.encode()), 'generation': generation},
              sample + 'request.json': request, sample + 'native.json': native,
              sample + 'raw.json': raw, sample + 'result.json': result,
              sample + 'processors.json': {'actual': []}, sample + 'native_call.json': {'invocation': 1, 'max_new_tokens': 64}}
    values.update({sample + f'steps/{i:03d}.json': s for i, s in enumerate(raw['steps'])})
    class Tokenizer:
        def encode(self, text, add_special_tokens):
            if text != prompt or add_special_tokens:
                raise AssertionError('Must only encode rendered input, never generated response')
            class Encoded:
                ids = raw['input_ids']
            return Encoded()
    return MemoryArchive(values), {**result, 'ordinal': 0, 'sample_id': 'synthetic-0'}, {'model': model}, context, Tokenizer(), bridge.sha(prompt.encode())


class BridgeTests(unittest.TestCase):
    def call(self, args):
        with patch.object(bridge, 'PROMPT_SHA', args[-1]):
            return bridge.packet_for(*args[:-1])

    def test_projection_binds_original_bytes_without_mutation(self):
        args = bridge_fixture()
        original = copy.deepcopy(args[0].values)
        packet, links = self.call(args)
        self.assertEqual(args[0].values, original)
        self.assertEqual(packet['scope'], a.SAVED_SCOPE)
        self.assertEqual(packet['provenance']['configuration_sha256'], digest(packet['config']))
        self.assertIn('calls/000000/run/samples/000000/raw.json', links)
        self.assertNotIn('image', packet)
        self.assertNotIn('true_label', packet)

    def test_identity_raw_step_processors_and_prompt_tampering(self):
        changes = [
            ('calls/000000/run/identity.json', 'sample_id', 'other', 'CALL_PLANNED_ID'),
            ('calls/000000/run/samples/000000/raw.json', 'execution_release', {}, 'RAW_CONFIGURATION_BINDING'),
            ('calls/000000/run/samples/000000/native.json', 'returned_ids', [[]], 'NATIVE_TOKEN_CUSTODY'),
            ('calls/000000/run/samples/000000/processors.json', 'actual', ['changed'], 'PROCESSOR_CUSTODY'),
            ('calls/000000/run/samples/000000/steps/002.json', 'argmax', 999, 'RAW_STEP_CUSTODY'),
            ('calls/000000/run/samples/000000/request.json', 'prompt', 'changed', 'PROMPT_PIN')]
        for path, key, value, error in changes:
            args = bridge_fixture()
            args[0].values = copy.deepcopy(args[0].values)
            # Break sharing so this modifies only the separate evidence member.
            args[0].values[path] = copy.deepcopy(args[0].values[path])
            args[0].values[path][key] = value
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                self.call(args)

    def test_missing_member_and_changed_result_cannot_be_resealed(self):
        args = bridge_fixture()
        del args[0].values['calls/000000/run/samples/000000/native.json']
        with self.assertRaises(KeyError):
            self.call(args)
        args = bridge_fixture()
        args[0].checksums['calls/000000/run/samples/000000/raw.json'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'RAW_RESULT_CUSTODY'):
            self.call(args)

    def test_planned160_counts_missing_duplicates_invalid_and_no_backfill(self):
        rows = [{'ordinal': i, 'sample_id': f'synthetic-{i}', 'status': 'SUCCESS' if i < 155 else 'INVALID',
                 'hnlo': {'hnlo': None}, 'attempts': 1, 'native_calls': 1} for i in range(160)]
        bridge.check_accounting(rows)
        for change, reason in (
            (lambda q: q.pop(), 'PLANNED_ACCOUNTING'),
            (lambda q: q[0].update(sample_id=q[1]['sample_id']), 'PLANNED_ACCOUNTING'),
            (lambda q: q[159].update(status='SUCCESS'), 'ORIGINAL_COUNTS'),
            (lambda q: q[0].update(hnlo={'hnlo': 1.}), 'ORIGINAL_RESULTS_CHANGED')):
            q = copy.deepcopy(rows)
            change(q)
            with self.assertRaisesRegex(ValueError, reason):
                bridge.check_accounting(q)


def serialized_tokens():
    # Small handwritten BPE serialization; no real runtime vocabulary.
    pieces = {"<pad>": 0, "<eos>": 1, "\u2581hello": 2, "world": 3,
              "<0xE2>": 4, "<0x82>": 5, "<0xAC>": 6, "<0xFF>": 7,
              "<0x41>": 8, "\u2581": 9, "\u2581\u2581x": 10}
    return json.dumps({"version": "1.0", "truncation": None, "padding": None,
        "added_tokens": [{"id": i, "content": p, "single_word": False, "lstrip": False,
            "rstrip": False, "normalized": False, "special": True} for p, i in list(pieces.items())[:2]],
        "normalizer": None, "pre_tokenizer": None, "post_processor": None,
        "decoder": bridge.DECODER_SPEC,
        "model": {"type": "BPE", "dropout": None, "unk_token": None,
            "continuing_subword_prefix": None, "end_of_word_suffix": None,
            "fuse_unk": False, "byte_fallback": True, "ignore_merges": False,
            "vocab": pieces, "merges": []}}, ensure_ascii=True).encode()


class CacheTests(unittest.TestCase):
    def test_cache_equivalence_per_record_numeric_and_seals(self):
        p, n, r, s = fixture()
        c = a.EnumerationCache()
        expected = a.evaluate(p, n, r, s)
        self.assertEqual(a.evaluate(p, n, r, s, cache=c), expected)
        self.assertEqual(a.evaluate(p, n, r, s, cache=c), expected)
        self.assertEqual(c.searches, 2)
        self.assertEqual(c.hits, 2)
        q = copy.deepcopy(p)
        q['raw']['steps'][2]['raw_candidate_logits']['11'] = -10.
        changed = a.evaluate(q, n, r, seal(q, n), cache=c)
        self.assertEqual(changed['status'], 'PASS')
        self.assertNotEqual(changed['hnlo'], expected['hnlo'])
        self.assertEqual(c.searches, 2)
        self.assertEqual(a.evaluate(q, n, r, s, cache=c)['reason'], 'EVIDENCE_SEAL_MISMATCH')

    def test_cached_refusal_has_independent_full_negative_proof(self):
        p, n, r, s = fixture(alias=True)
        c = a.EnumerationCache()
        for _ in range(2):
            result = a.evaluate(p, n, r, s, cache=c)
            negative = a.verify_unavailable(p, r, s, cache=c)
            self.assertEqual(result['reason'], 'AMBIGUOUS_TOKEN_BRANCH')
            self.assertEqual(result['reason'], negative['reason'])
            self.assertIsNone(negative['hnlo'])
            self.assertEqual(negative['complete_families'][0][1][0], (11, 21))
        self.assertEqual(c.searches, 2)
        self.assertEqual(c.hits, 2)

    def test_search_key_is_sensitive_to_decoder_and_context(self):
        p, n, r, s = fixture()
        c = a.EnumerationCache()
        a.evaluate(p, n, r, s, cache=c)
        alias_p, alias_n, alias_r, alias_s = fixture(alias=True)
        self.assertEqual(a.evaluate(alias_p, alias_n, alias_r, alias_s, cache=c)['reason'],
                         'AMBIGUOUS_TOKEN_BRANCH')
        q = copy.deepcopy(p)
        q['raw']['input_ids'][0] = 101
        q['native']['input_ids'][0] = 101
        q['rendered_prompt_ids'][0] = 101
        self.assertEqual(a.evaluate(q, n, r, seal(q, n), cache=c)['status'], 'PASS')
        self.assertEqual(c.searches, 5)

    def test_cached_search_does_not_hide_missing_step_logit(self):
        p, n, r, s = fixture()
        c = a.EnumerationCache()
        self.assertEqual(a.evaluate(p, n, r, s, cache=c)['status'], 'PASS')
        del p['raw']['steps'][2]['raw_candidate_logits']['11']
        s = seal(p, n)
        self.assertEqual(a.evaluate(p, n, r, s, cache=c)['reason'], 'MISSING_DECISION_LOGITS')
        self.assertEqual(a.verify_unavailable(p, r, s, cache=c)['reason'], 'MISSING_DECISION_LOGITS')

    def test_cache_cannot_bypass_caps_and_native_custody(self):
        p, n, r, s = fixture()
        c = a.EnumerationCache()
        a.evaluate(p, n, r, s, cache=c)
        with patch.object(a, 'MAX_TRIALS', 1):
            self.assertEqual(a.evaluate(p, n, r, s, cache=c)['reason'], 'SEARCH_RESOURCE_BOUND')
        p['native']['generated_ids'][0] = 10354
        self.assertEqual(a.evaluate(p, n, r, seal(p, n), cache=c)['reason'], 'NATIVE_PATH_CUSTODY_MISMATCH')

    def test_cache_is_bounded(self):
        c = a.EnumerationCache()
        for i in range(40):
            self.assertEqual(c.search('synthetic', None, (i,), lambda: i), i)
        self.assertEqual(len(c.entries), 32)

    def test_real_scope_is_distinct_and_cannot_claim_audit(self):
        p, n, r, _ = fixture()
        p['scope'] = a.SAVED_SCOPE
        result = a.evaluate(p, n, r, seal(p, n))
        self.assertEqual(result['scope'], a.SAVED_SCOPE)
        self.assertEqual(result['qualification'], 'PENDING_INDEPENDENT_AUDIT')

    def test_negative_proof_detects_missing_and_extra_alias_independently(self):
        p, n, r, s = fixture(alias=True)
        negative = a.verify_unavailable(p, r, s)
        self.assertEqual(negative['reason'], 'AMBIGUOUS_TOKEN_BRANCH')
        p, n, r, s = fixture()
        self.assertIsNone(a.verify_unavailable(p, r, s)['reason'])


class DecoderTests(unittest.TestCase):
    def test_python_decoder_exact_chain_boundaries_and_utf8(self):
        decoder = bridge.ReferenceDecoder(serialized_tokens())
        cases = [((2, 3), False, 'helloworld'), ((3, 2), False, 'world hello'),
                 ((4, 5, 6), False, '\u20ac'), ((7, 8), False, '\ufffd\ufffd'),
                 ((7, 3, 8), False, '\ufffdworldA'), ((0, 2, 1), True, 'hello'),
                 ((9, 9, 3), False, ' world'), ((10,), False, ' x'),
                 ((4, 1, 5, 6), True, '\u20ac')]
        for ids, skip, expected in cases:
            self.assertEqual(decoder.decode(ids, skip), expected)

    def test_unknown_decoder_and_added_token_conflict_fail_closed(self):
        t = json.loads(serialized_tokens())
        t['decoder']['decoders'][-1]['start'] = 2
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_RUNTIME_DECODER'):
            bridge.ReferenceDecoder(json.dumps(t).encode())
        t = json.loads(serialized_tokens())
        t['added_tokens'][0]['content'] = 'replacement'
        with self.assertRaisesRegex(ValueError, 'ADDED_TOKEN_CONFLICT'):
            bridge.ReferenceDecoder(json.dumps(t).encode())

    def test_runtime_rust_vs_python_full_small_vocabulary_and_contexts(self):
        try:
            import tokenizers
        except ImportError:
            self.skipTest('optional pinned tokenizers 0.21.1 not installed')
        if tokenizers.__version__ != '0.21.1':
            self.skipTest('requires pinned tokenizers 0.21.1')
        _, native, reference = bridge.decoders(serialized_tokens())
        # Exhaustive ordered triples exercise invalid/valid UTF-8 buffering,
        # mixed special tokens, contextual whitespace and single-space stripping.
        for x in native.vocabulary:
            for y in native.vocabulary:
                for z in native.vocabulary:
                    for skip in (False, True):
                        self.assertEqual(native.decode((x, y, z), skip), reference.decode((x, y, z), skip))

    def test_three_numeric_formulas_extremes(self):
        for values in ([1., 2., 3., 4.], [1000., 999., -999., -1000.], [-1000.] * 4):
            expected = bridge.independent_numeric(values)
            self.assertAlmostEqual(a.hnlo(values), expected, places=10)
            self.assertAlmostEqual(a.oracle(values), expected, places=10)


class ArchiveTests(unittest.TestCase):
    def make_archive(self, root, *, bad_member=False, duplicate=False):
        path = Path(root) / 'synthetic.zip'
        data = {'owner_execution.json': b'{"synthetic":true}',
                'pilot_manifest.json': b'NOT JSON: GT MUST NEVER BE PARSED'}
        checksums = {n: bridge.sha(v) for n, v in data.items()}
        if bad_member:
            checksums['owner_execution.json'] = '0' * 64
        with zipfile.ZipFile(path, 'w') as z:
            for n, v in data.items():
                z.writestr(n, v)
            z.writestr('checksums.json', json.dumps(checksums))
            if duplicate:
                z.writestr('owner_execution.json', b'{}')
        checksum = bridge.file_sha(path)
        Path(str(path) + '.sha256.json').write_text(json.dumps({'sha256': checksum, 'members': 3 + duplicate}))
        return path, checksum

    def test_seal_before_semantic_read_and_immutable_source(self):
        with tempfile.TemporaryDirectory() as root:
            path, checksum = self.make_archive(root)
            original = path.read_bytes()
            archive = bridge.SealedArchive(path, checksum)
            try:
                self.assertEqual(archive.json('owner_execution.json'), {'synthetic': True})
                for name in ('pilot_manifest.json', 'image.jpg', '../raw.json', 'worker.log'):
                    with self.assertRaisesRegex(ValueError, 'SEMANTIC_READ_OUT_OF_SCOPE'):
                        archive.read(name)
            finally:
                archive.close()
            self.assertEqual(path.read_bytes(), original)

    def test_tampered_outer_and_member_and_sidecar(self):
        with tempfile.TemporaryDirectory() as root:
            path, checksum = self.make_archive(root, bad_member=True)
            with self.assertRaisesRegex(ValueError, 'MEMBER_SHA256_MISMATCH'):
                bridge.SealedArchive(path, checksum)
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_SHA256_MISMATCH'):
                bridge.SealedArchive(path, 'f' * 64)
            Path(str(path) + '.sha256.json').write_text(json.dumps({'sha256': 'f' * 64, 'members': 3}))
            with self.assertRaisesRegex(ValueError, 'SIDECAR_SHA256_MISMATCH'):
                bridge.SealedArchive(path, checksum)

    def test_duplicate_members_and_duplicate_json_fail(self):
        with tempfile.TemporaryDirectory() as root:
            path, checksum = self.make_archive(root, duplicate=True)
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_MEMBERSHIP'):
                bridge.SealedArchive(path, checksum)
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_JSON_KEY'):
            bridge.strict_json('{"a":1,"a":2}')
        with self.assertRaisesRegex(ValueError, 'NONFINITE_JSON'):
            bridge.strict_json('{"a":NaN}')

    def test_cli_exclusive_output_and_no_private_fields_in_public_projection(self):
        from scripts.verify_minicpm_saved_hnlo import write_new, public_projection
        summary = defaultdict(lambda: 0, {'sample_id': 'PRIVATE_SENTINEL', 'raw': 'PRIVATE_SENTINEL',
            'packet': 'PRIVATE_SENTINEL', 'semantic_members_read': ['PRIVATE_SENTINEL'], 'result': 'NO'})
        public = public_projection(summary)
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(public))
        self.assertEqual(public['result'], 'NO')
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'receipt.json'
            write_new(path, {'synthetic': True})
            with self.assertRaises(FileExistsError):
                write_new(path, {'overwrite': True})
            self.assertEqual(json.loads(path.read_text()), {'synthetic': True})


if __name__ == '__main__':
    unittest.main()
