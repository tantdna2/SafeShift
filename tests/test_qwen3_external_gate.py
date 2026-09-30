"""Frozen gate PREP tests: fake native backend, no ML imports or network."""

from contextlib import ExitStack
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts import w2_qwen3_external_gate as gate
from safeshift.protocol.gate import GiantBoxReview, evaluate_gate
from tests import test_qwen_kaggle_smoke_harness as smoke_tests

ROOT = Path(__file__).resolve().parents[1]
class FakeOOM(RuntimeError):
    pass


COMMIT = '90f36354e16eb66192692b526912e79c2981cce3'


class ExternalGatePrepTests(unittest.TestCase):
    def setUp(self):
        smoke_tests.SmokeTests.setUp(self)  # Fake runtime plus network/native-import guards.
        # Replay the historical gate contract in a temporary repository. Only
        # documentary provenance's current membership overlay changed in D9R15.
        self.gate_plan = json.loads((ROOT / gate.PLAN).read_bytes())
        paths = [gate.PLAN, gate.MANIFEST, gate.PROVENANCE, gate.smoke.PLAN,
                 *self.gate_plan['protected_source_sha256_lf']]
        paths += [f'tests/fixtures/pre_freeze/frozen_external_gate/{c}.png' for c in gate.CASE_IDS]
        for path in paths:
            target = self.repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
        provenance = 'configs/pre_freeze/local_model_provenance.d9.json'
        (self.repo / provenance).write_bytes(subprocess.check_output(
            ['git', 'show', '9948570820b5ed8a774b8e226b80e24055e705cf:' + provenance], cwd=ROOT))
        self.gate_plan, self.plan = gate.load_gate_plan(self.repo)
        self.cases = gate.load_cases(self.repo, gate.MANIFEST)
        self.texts = {c.case_id: json.dumps({'bbox': c.target_gt_bbox}) for c in self.cases}
        pins = self.gate_plan['software']
        rt = self.runtime
        rt.factory.return_value = replace(rt.backend, software_versions={k: pins[k] for k in rt.backend.software_versions})
        rt.torch.version = SimpleNamespace(cuda=pins['cuda_runtime'])
        rt.torch.cuda = SimpleNamespace(OutOfMemoryError=FakeOOM, reset_peak_memory_stats=Mock())
        self.software = dict(pins)
        self.hardware = smoke_tests.hardware()
        self.git_commit = COMMIT
        self.git_status = ''
        self.env = {**gate.OFFLINE_ENV, 'KAGGLE_KERNEL_RUN_TYPE': 'Interactive'}
        original = self.runner.prepare_input

        def prepare(request, context):
            rt.processor.text = self.texts[context.call_id]
            return original(request, context)
        self.runner.prepare_input = Mock(side_effect=prepare)
        self.runner.load = Mock(wraps=self.runner.load)
        self.runner.initialize = Mock(wraps=self.runner.initialize)
        self.factory = Mock(return_value=self.runner)

    def run_fake(self, name='fake', plan_override=None, snapshot_error=None,
                 weights_verified=True, configs_verified=True):
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, self.env))
            stack.enter_context(patch.object(gate.subprocess, 'check_output',
                side_effect=lambda args, **kw: self.git_commit if args[1] == 'rev-parse' else self.git_status))
            stack.enter_context(patch.object(gate.platform, 'system', return_value='Linux'))
            stack.enter_context(patch.object(gate.platform, 'machine', return_value='x86_64'))
            stack.enter_context(patch.object(gate.smoke, 'software_versions', return_value=self.software))
            stack.enter_context(patch.object(gate.smoke, 'probe_hardware', return_value=self.hardware))
            stack.enter_context(patch.object(gate.smoke, 'memory_snapshot', return_value={'gpus': []}))
            stack.enter_context(patch.object(gate.snapshot, 'cached_snapshot', return_value=Path('unused')))
            stack.enter_context(patch.object(gate, 'verify_snapshot', side_effect=snapshot_error,
                return_value={'LOCAL_WEIGHT_BYTES_VERIFIED': weights_verified,
                              'config_bytes_verified': configs_verified, 'revision': gate.REVISION}))
            if plan_override is not None:
                stack.enter_context(patch.object(gate, 'load_gate_plan', return_value=(plan_override, self.plan)))
            return gate.run_gate(name, COMMIT, repo=self.repo, runner_factory=self.factory,
                                 torch_module=self.runtime.torch)

    def alter_manifest(self, change):
        path = self.repo / gate.MANIFEST
        value = json.loads(path.read_bytes())
        change(value)
        path.write_text(json.dumps(value), encoding='utf-8')
        plan = deepcopy(self.gate_plan)
        plan['manifest_sha256'] = gate.snapshot.sha256_file(path)
        path = self.repo / gate.PROVENANCE
        value = json.loads(path.read_bytes())
        value['manifest_sha256'] = plan['manifest_sha256']
        path.write_text(json.dumps(value), encoding='utf-8')
        plan['provenance_sha256'] = gate.snapshot.sha256_file(path)
        return plan

    def assert_before_load(self, result):
        self.assertEqual(result['status'], 'GATE_EXECUTION_FAILURE')
        self.factory.assert_not_called()
        self.runner.load.assert_not_called()
        self.assertEqual(result['native_generate_calls'], 0)

    def test_exact_order_one_lifecycle_eight_prepares_and_native_generates(self):
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_PENDING_REVIEW')
        self.assertEqual([c['case_id'] for c in result['calls']], list(gate.CASE_IDS))
        self.assertEqual(len(self.runtime.model.calls), 8)
        self.assertEqual(result['native_generate_calls'], 8)
        self.assertEqual(self.runner.prepare_input.call_count, 8)
        self.runner.load.assert_called_once()
        self.runner.initialize.assert_called_once()
        self.factory.assert_called_once()
        self.runtime.model_factory.from_pretrained.assert_called_once()
        self.assertEqual(result['not_attempted_case_ids'], [])

    def test_historical_verifier_still_rejects_current_provenance_overlay(self):
        provenance = 'configs/pre_freeze/local_model_provenance.d9.json'
        shutil.copyfile(ROOT / provenance, self.repo / provenance)
        with self.assertRaisesRegex(ValueError, 'PROTECTED_SOURCE_CHANGED'):
            gate.load_gate_plan(self.repo)

    def test_seven_cases_fail_before_load(self):
        plan = self.alter_manifest(lambda m: m['cases'].pop())
        self.assert_before_load(self.run_fake(plan_override=plan))

    def test_manifest_tampering_fails_before_load(self):
        with (self.repo / gate.MANIFEST).open('ab') as f:
            f.write(b' ')
        self.assert_before_load(self.run_fake())

    def test_provenance_tampering_fails_before_load(self):
        with (self.repo / gate.PROVENANCE).open('ab') as f:
            f.write(b' ')
        self.assert_before_load(self.run_fake())

    def test_image_hash_tampering_fails_before_load(self):
        with (self.repo / self.cases[0].image_path).open('ab') as f:
            f.write(b' ')
        self.assert_before_load(self.run_fake())

    def test_reciprocal_swap_violation_fails_before_load(self):
        plan = self.alter_manifest(lambda m: m['cases'][1].update(target_gt_bbox=[0.6, 0.3, 0.8, 0.6]))
        self.assert_before_load(self.run_fake(plan_override=plan))

    def test_wrong_order_fails_before_load(self):
        plan = self.alter_manifest(lambda m: m['cases'].reverse())
        self.assert_before_load(self.run_fake(plan_override=plan))

    def test_ninth_case_rejected_before_load(self):
        plan = self.alter_manifest(lambda m: m['cases'].append({**m['cases'][0], 'case_id': 'A_3'}))
        self.assert_before_load(self.run_fake(plan_override=plan))

    def test_second_native_call_in_same_case_blocked_without_dispatch(self):
        original = self.runner.generate_raw
        def double(prepared, ctx):
            original(prepared, ctx)
            return original(prepared, ctx)
        self.runner.generate_raw = double
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_EXECUTION_FAILURE')
        self.assertEqual(len(self.runtime.model.calls), 1)
        self.assertEqual(result['native_generate_calls'], 1)

    def test_raw_and_hash_durable_before_envelope_extraction_and_parse(self):
        original_extract, original_parse = gate.parser_text, gate.parse_text
        seen = []
        def extract(raw):
            case = gate.CASE_IDS[len(seen)]
            directory = self.repo / gate.ARTIFACTS / 'fake' / case
            self.assertEqual((directory / 'response.raw').read_bytes(), raw)
            metadata = json.loads((directory / 'metadata.json').read_bytes())
            self.assertEqual(metadata['parse_status'], 'NOT_ATTEMPTED')
            self.assertEqual(metadata['raw_output']['sha256'], hashlib.sha256(raw).hexdigest())
            seen.append(case)
            return original_extract(raw)
        def parse(text, task):
            self.assertEqual(len(seen), self.runner.prepare_input.call_count)
            self.assertEqual(task, 'external_probe')
            return original_parse(text, task)
        with patch.object(gate, 'parser_text', side_effect=extract), patch.object(gate, 'parse_text', side_effect=parse):
            self.assertEqual(self.run_fake()['status'], 'GATE_PENDING_REVIEW')
        self.assertEqual(seen, list(gate.CASE_IDS))

    def test_fenced_json_remains_invalid_without_repair(self):
        text = '```json\n' + self.texts['A_1'] + '\n```'
        self.texts['A_1'] = text
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_FAIL')
        self.assertEqual(result['calls'][0]['parse_status'], 'JSON_ERROR')
        self.assertEqual(result['calls'][0]['decoded_for_parser'], text)
        self.assertIsNone(result['calls'][0]['parsed_bbox'])
        self.assertEqual(result['native_generate_calls'], 8)

    def test_valid_strict_boxes_parse_and_all_automatic_checks_wait_for_review(self):
        result = self.run_fake()
        self.assertTrue(result['gate']['systematic_tracking'])
        self.assertEqual(result['status'], 'GATE_PENDING_REVIEW')
        for row in result['gate']['cases']:
            self.assertTrue(row['schema_valid'])
            self.assertTrue(row['center_in_target'])
            self.assertTrue(row['excludes_distractor_center'])
            self.assertFalse(row['full_image'])
            self.assertEqual(row['giant_box_review']['status'], 'PENDING')

    def test_center_outside_target_fails(self):
        self.texts['A_1'] = '{"bbox":[0,0,0.1,0.1]}'
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_FAIL')
        self.assertFalse(result['gate']['cases'][0]['center_in_target'])

    def test_distractor_center_included_fails(self):
        self.texts['A_1'] = '{"bbox":[0,0.375,0.76,0.625]}'
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_FAIL')
        self.assertFalse(result['gate']['cases'][0]['excludes_distractor_center'])

    def test_full_image_fails(self):
        self.texts['A_1'] = '{"bbox":[0,0,1,1]}'
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_FAIL')
        self.assertTrue(result['gate']['cases'][0]['full_image'])

    def test_wrong_swap_tracking_fails(self):
        self.texts['A_1'], self.texts['A_2'] = self.texts['A_2'], self.texts['A_1']
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_FAIL')
        self.assertFalse(result['gate']['systematic_tracking'])

    def test_tiny_iou_is_diagnostic_only(self):
        self.texts['A_1'] = '{"bbox":[0.2499,0.4999,0.2501,0.5001]}'
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_PENDING_REVIEW')
        self.assertLess(result['gate']['cases'][0]['target_iou_diagnostic'], 0.000001)

    def test_large_area_waits_for_human_not_numeric_threshold(self):
        # Center remains on target boundary, and distractor center is excluded.
        self.texts['A_1'] = '{"bbox":[0,0,0.74,1]}'
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_PENDING_REVIEW')
        self.assertEqual(result['gate']['cases'][0]['predicted_area_diagnostic'], 0.74)

    def test_coordinate_order_is_not_repaired(self):
        self.texts['A_1'] = '{"bbox":[0.4,0.6,0.1,0.2]}'
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_FAIL')
        self.assertEqual(result['calls'][0]['parse_status'], 'COORDINATE_ERROR')

    def test_production_adapter_not_called(self):
        with patch('safeshift.runners.qwen3_vl.Qwen3VLAdapter.adapt', side_effect=AssertionError('forbidden')):
            self.assertEqual(self.run_fake()['status'], 'GATE_PENDING_REVIEW')

    def test_inspecsafe_path_fails_before_model(self):
        plan = self.alter_manifest(lambda m: m['cases'][0].update(image_path='data/raw/InspecSafe-V1/a.png'))
        self.assert_before_load(self.run_fake(plan_override=plan))

    def test_network_denied_inside_generation(self):
        original = self.runtime.model.generate
        def generate(**kwargs):
            with self.assertRaises(RuntimeError):
                socket.create_connection(('example.com', 443))
            return original(**kwargs)
        self.runtime.model.generate = generate
        self.assertEqual(self.run_fake()['status'], 'GATE_PENDING_REVIEW')

    def test_oom_safe_failure_no_retry_no_fabricated_raw(self):
        self.runtime.model.failure = FakeOOM('/private/token=secret')
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_EXECUTION_FAILURE')
        self.assertTrue(result['failure']['resource_failure'])
        self.assertEqual(result['native_generate_calls'], 1)
        self.assertEqual(len(result['calls']), 1)
        self.assertEqual(result['not_attempted_case_ids'], list(gate.CASE_IDS[1:]))
        self.assertIsNone(result['calls'][0]['raw'])
        root = self.repo / gate.ARTIFACTS / 'fake'
        self.assertFalse(list(root.rglob('response.raw')))
        for path in root.rglob('*.json'):
            self.assertNotIn('/private/token=secret', path.read_text())

    def test_post_generate_partial_raw_preserved(self):
        self.runtime.processor.batch_decode = Mock(side_effect=ValueError('/private/secret'))
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_EXECUTION_FAILURE')
        self.assertIsNotNone(result['calls'][0]['raw'])
        path = self.repo / result['calls'][0]['raw']['path']
        self.assertTrue(path.exists())
        self.assertNotIn('/private/secret', path.read_text())
        self.assertEqual(result['calls'][0]['parse_status'], 'NOT_ATTEMPTED')
        self.assertEqual(result['native_generate_calls'], 1)

    def test_no_overwrite(self):
        self.run_fake()
        with self.assertRaises(FileExistsError):
            self.run_fake()

    def test_decoding_and_prompt_pins_unchanged(self):
        self.assertEqual(self.gate_plan['decoding'], {'do_sample': False, 'max_new_tokens': 32})
        self.assertEqual(self.gate_plan['decoding'], self.plan['decoding'])
        result = self.run_fake()
        for call, case in zip(result['calls'], self.cases):
            prompt = gate.probe_request(self.repo, case.image_path, case.target_query)
            self.assertEqual(call['prompt_sha256'], prompt.prompt_sha256)
            self.assertEqual(call['prompt_version'], 'external-target-draft-v1')
        for call in self.runtime.model.calls:
            self.assertIs(call['do_sample'], False)
            self.assertEqual(call['max_new_tokens'], 32)

    def test_mutated_gate_plan_rejected(self):
        path = self.repo / gate.PLAN
        value = json.loads(path.read_bytes())
        value['decoding']['max_new_tokens'] = 64
        path.write_text(json.dumps(value), encoding='utf-8')
        self.assert_before_load(self.run_fake())

    def test_protected_production_source_mutation_rejected(self):
        path = self.repo / 'safeshift/runners/qwen3_vl.py'
        path.write_text(path.read_text() + '\n# altered\n', encoding='utf-8')
        self.assert_before_load(self.run_fake())

    def test_explicit_eight_human_reviews_required_by_existing_evaluator(self):
        predictions = {c.case_id: gate.parse_text(self.texts[c.case_id], 'external_probe') for c in self.cases}
        reviews = {c.case_id: GiantBoxReview('NO_GIANT', 'fake-auditor', 'test only') for c in self.cases}
        self.assertEqual(evaluate_gate(self.repo, self.cases, predictions, reviews).status, 'PASS')
        del reviews['D_2']
        self.assertEqual(evaluate_gate(self.repo, self.cases, predictions, reviews).status, 'PENDING_REVIEW')

    def test_snapshot_failure_prevents_load(self):
        result = self.run_fake(snapshot_error=ValueError('private-snapshot-path'))
        self.assert_before_load(result)
        self.assertEqual(result['failure']['stage'], 'SNAPSHOT')

    def test_cuda_mismatch_prevents_load(self):
        self.software['cuda_runtime'] = 'wrong'
        self.assert_before_load(self.run_fake())

    def test_wrong_image_dimensions_fail_even_with_matching_hash(self):
        from PIL import Image
        path = self.repo / self.cases[0].image_path
        Image.new('RGB', (128, 128)).save(path)
        p = self.repo / gate.PROVENANCE
        provenance = json.loads(p.read_bytes())
        provenance['images'][0]['sha256'] = gate.snapshot.sha256_file(path)
        p.write_text(json.dumps(provenance), encoding='utf-8')
        plan = deepcopy(self.gate_plan)
        plan['provenance_sha256'] = gate.snapshot.sha256_file(p)
        self.assert_before_load(self.run_fake(plan_override=plan))

    def test_non_oom_failure_is_interface_failure_and_sanitized(self):
        self.runtime.model.failure = ValueError('secret-path-and-token')
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_EXECUTION_FAILURE')
        self.assertFalse(result['failure']['resource_failure'])
        self.assertEqual(result['native_generate_calls'], 1)
        self.assertNotIn('secret-path-and-token', json.dumps(result))

    def test_harness_cannot_emit_pass_even_if_evaluator_unexpectedly_returns_pass(self):
        original = gate.evaluate_gate
        def unexpected(*args, **kwargs):
            self.assertIsNone(kwargs['reviews'])
            return replace(original(*args, **kwargs), status='PASS')
        with patch.object(gate, 'evaluate_gate', side_effect=unexpected):
            self.assertEqual(self.run_fake()['status'], 'GATE_EXECUTION_FAILURE')

    def test_raw_persistence_failure_prevents_parse_and_rerun(self):
        with patch.object(gate.GateRawStore, 'preserve', side_effect=OSError('private-path')), \
                patch.object(gate, 'parse_text') as parse:
            result = self.run_fake()
        parse.assert_not_called()
        self.assertEqual(result['status'], 'GATE_EXECUTION_FAILURE')
        self.assertEqual(result['failure']['stage'], 'RAW_PRESERVE')
        self.assertEqual(result['native_generate_calls'], 1)

    def test_native_model_identity_and_resource_arguments_unchanged(self):
        self.run_fake()
        args = self.runtime.model_factory.from_pretrained.call_args
        self.assertEqual(args.args, (gate.MODEL_ID,))
        self.assertEqual(args.kwargs['revision'], gate.REVISION)
        self.assertNotIn('attn_implementation', args.kwargs)
        self.assertEqual(args.kwargs['dtype'], 'fake-fp16')
        self.assertEqual(args.kwargs['device_map'], 'auto')
        self.assertIs(args.kwargs['local_files_only'], True)
        self.assertIs(args.kwargs['trust_remote_code'], False)
        self.assertNotIn('quantization_config', args.kwargs)
        p = self.runtime.processor_factory.from_pretrained.call_args.kwargs
        self.assertEqual(p, {'revision': gate.REVISION, 'local_files_only': True, 'trust_remote_code': False})

    def test_wrong_execution_commit_prevents_load(self):
        self.git_commit = 'a' * 40
        self.assert_before_load(self.run_fake())

    def test_dirty_tracked_or_untracked_files_prevent_load(self):
        for i, status in enumerate((' M scripts/example.py', '?? unexpected.py')):
            with self.subTest(status=status):
                self.git_status = status
                self.assert_before_load(self.run_fake(name=f'dirty-{i}'))

    def test_each_offline_variable_required_before_load(self):
        for i, key in enumerate(gate.OFFLINE_ENV):
            with self.subTest(key=key):
                self.env[key] = '0'
                self.assert_before_load(self.run_fake(name=f'offline-{i}'))
                self.env[key] = '1'

    def test_kaggle_environment_required(self):
        self.env['KAGGLE_KERNEL_RUN_TYPE'] = ''
        self.assert_before_load(self.run_fake())

    def test_wrong_gpu_count_or_type_prevents_load(self):
        for i, names in enumerate(((), ('Tesla T4',), ('Tesla T4',) * 3, ('Tesla T4', 'A100'))):
            with self.subTest(names=names):
                self.hardware = smoke_tests.hardware(names)
                self.assert_before_load(self.run_fake(name=f'hardware-{i}'))

    def test_every_software_pin_checked_before_load(self):
        for i, key in enumerate(self.gate_plan['software']):
            with self.subTest(key=key):
                self.software = {**self.gate_plan['software'], key: 'wrong'}
                self.assert_before_load(self.run_fake(name=f'software-{i}'))

    def test_weight_hash_mismatch_prevents_load(self):
        self.assert_before_load(self.run_fake(weights_verified=False))

    def test_snapshot_config_hash_mismatch_prevents_load(self):
        self.assert_before_load(self.run_fake(configs_verified=False))

    def test_wrong_raw_envelope_identity_prevents_parse(self):
        original = self.runner.generate_raw
        def wrong_identity(prepared, ctx):
            value = json.loads(original(prepared, ctx))
            value['model_revision'] = 'a' * 40
            return json.dumps(value).encode()
        self.runner.generate_raw = wrong_identity
        with patch.object(gate, 'parse_text') as parse:
            result = self.run_fake()
        parse.assert_not_called()
        self.assertEqual(result['status'], 'GATE_EXECUTION_FAILURE')
        self.assertIsNotNone(result['calls'][0]['raw'])
        self.assertEqual(result['native_generate_calls'], 1)

    def test_smoke_plan_mutation_prevents_load(self):
        path = self.repo / gate.smoke.PLAN
        value = json.loads(path.read_bytes())
        value['device']['placement'] = 'cuda:0'
        path.write_text(json.dumps(value), encoding='utf-8')
        self.assert_before_load(self.run_fake())

    def test_prompt_hash_checked_before_load(self):
        plan = deepcopy(self.gate_plan)
        plan['prompt_sha256']['A_1'] = '0' * 64
        self.assert_before_load(self.run_fake(plan_override=plan))

    def test_corrupt_persisted_raw_prevents_extraction_and_parse(self):
        preserve = gate.GateRawStore.preserve
        def corrupt(store, raw, provenance):
            ref = preserve(store, raw, provenance)
            (store.repo / ref.path).write_bytes(b'corrupt')
            return ref
        with patch.object(gate.GateRawStore, 'preserve', corrupt), \
                patch.object(gate, 'parser_text') as extract, patch.object(gate, 'parse_text') as parse:
            result = self.run_fake()
        extract.assert_not_called()
        parse.assert_not_called()
        self.assertEqual(result['status'], 'GATE_EXECUTION_FAILURE')
        self.assertEqual(result['native_generate_calls'], 1)

    def test_raw_metadata_failure_prevents_parse(self):
        from safeshift.runners import storage
        original = storage._write_new
        def fail_metadata(path, content):
            if path.name == 'metadata.json':
                raise OSError('secret-path')
            return original(path, content)
        with patch.object(storage, '_write_new', side_effect=fail_metadata), \
                patch.object(gate, 'parse_text') as parse:
            result = self.run_fake()
        parse.assert_not_called()
        self.assertEqual(result['status'], 'GATE_EXECUTION_FAILURE')
        self.assertEqual(result['native_generate_calls'], 1)
        self.assertTrue((self.repo / gate.ARTIFACTS / 'fake/A_1/response.raw').exists())
        self.assertNotIn('secret-path', json.dumps(result))

    def test_ninth_native_call_blocked_at_last_case(self):
        original = self.runner.generate_raw
        def extra(prepared, ctx):
            raw = original(prepared, ctx)
            if ctx.call_id == 'D_2':
                return original(prepared, ctx)
            return raw
        self.runner.generate_raw = extra
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_EXECUTION_FAILURE')
        self.assertEqual(len(self.runtime.model.calls), 8)
        self.assertEqual(result['native_generate_calls'], 8)

    def test_second_case_native_failure_stops_without_retry(self):
        original = self.runtime.model.generate
        def fail_second(**kwargs):
            if self.runtime.model.calls:
                raise ValueError('private-second-call')
            return original(**kwargs)
        self.runtime.model.generate = fail_second
        result = self.run_fake()
        self.assertEqual(result['status'], 'GATE_EXECUTION_FAILURE')
        self.assertEqual(result['native_generate_calls'], 2)
        self.assertEqual(result['not_attempted_case_ids'], list(gate.CASE_IDS[2:]))
        self.assertIsNotNone(result['calls'][0]['raw'])
        self.assertIsNone(result['calls'][1]['raw'])
        self.assertNotIn('private-second-call', json.dumps(result))

    def test_existing_evaluator_and_case_loader_reused(self):
        from safeshift.protocol import gate as evaluator
        self.assertIs(gate.load_cases, evaluator.load_cases)
        self.assertIs(gate.evaluate_gate, evaluator.evaluate_gate)
        with patch.object(gate, 'evaluate_gate', wraps=evaluator.evaluate_gate) as evaluate:
            self.assertEqual(self.run_fake()['status'], 'GATE_PENDING_REVIEW')
        evaluate.assert_called_once()
        self.assertIsNone(evaluate.call_args.kwargs['reviews'])

    def test_json_and_field_repairs_are_absent(self):
        invalid = ('{"box":[0.125,0.375,0.375,0.625]}',
                   'prefix {"bbox":[0.125,0.375,0.375,0.625]} suffix',
                   '{"bbox":[0.125,0.375,0.375,0.625],}',
                   '{"bbox":[0,0,1,1],"bbox":[0.125,0.375,0.375,0.625]}')
        for i, text in enumerate(invalid):
            with self.subTest(text=text):
                self.texts['A_1'] = text
                result = self.run_fake(name=f'invalid-{i}')
                self.assertEqual(result['status'], 'GATE_FAIL')
                self.assertEqual(result['calls'][0]['decoded_for_parser'], text)
                self.assertIsNone(result['calls'][0]['parsed_bbox'])

    def test_parser_receives_native_coordinates_without_conversion(self):
        original = gate.parse_text
        text = '{"bbox":[125,375,375,625]}'
        self.texts['A_1'] = text
        with patch.object(gate, 'parse_text', wraps=original) as parse:
            result = self.run_fake()
        self.assertEqual(parse.call_args_list[0].args, (text, 'external_probe'))
        self.assertEqual(parse.call_args_list[0].kwargs, {})
        self.assertEqual(result['calls'][0]['parse_status'], 'COORDINATE_ERROR')

    def test_snapshot_config_hashes_and_revision_verified(self):
        directory = self.repo / gate.REVISION
        directory.mkdir()
        plan = deepcopy(self.gate_plan)
        for name in plan['snapshot_config_sha256']:
            raw = ('synthetic ' + name).encode()
            (directory / name).write_bytes(raw)
            plan['snapshot_config_sha256'][name] = hashlib.sha256(raw).hexdigest()
        with patch.object(gate.snapshot, 'verify_weights', return_value={'LOCAL_WEIGHT_BYTES_VERIFIED': True}):
            self.assertTrue(gate.verify_snapshot(directory, self.repo, plan)['config_bytes_verified'])
            (directory / 'generation_config.json').write_bytes(b'changed')
            self.assertFalse(gate.verify_snapshot(directory, self.repo, plan)['config_bytes_verified'])
            with self.assertRaises(ValueError):
                gate.verify_snapshot(self.repo, self.repo, plan)

    def test_initialize_and_load_failures_sanitized_without_retry(self):
        self.runner.initialize.side_effect = ValueError('secret-init')
        result = self.run_fake(name='init-failure')
        self.runner.load.assert_not_called()
        self.assertEqual(result['initialize_calls'], 1)
        self.assertEqual(result['load_calls'], 0)
        self.assertNotIn('secret-init', json.dumps(result))
        self.runner.initialize.side_effect = None
        self.runner.load.side_effect = ValueError('secret-load')
        result = self.run_fake(name='load-failure')
        self.assertEqual(result['status'], 'GATE_EXECUTION_FAILURE')
        self.assertEqual(result['load_calls'], 1)
        self.assertEqual(result['native_generate_calls'], 0)
        self.assertNotIn('secret-load', json.dumps(result))



if __name__ == '__main__':
    unittest.main()
