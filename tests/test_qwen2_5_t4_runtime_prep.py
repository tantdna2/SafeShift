"""Offline fake-only qualification preparation; never imports the ML stack."""

import builtins
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from safeshift.runners import qwen2_5_vl as runner_module
from safeshift.runners.qwen2_5_vl import Qwen2_5VLRunner, Qwen2_5VLAdapter
from scripts import provision_qwen2_5_snapshot as provision
from scripts import w2_qwen2_5_t4_smoke as smoke
from tests.test_qwen2_5_runner import Runtime, Tensor, context, request

ROOT = Path(__file__).resolve().parents[1]


class FakeOOM(RuntimeError):
    pass


class RuntimePrepTests(unittest.TestCase):
    def setUp(self):
        guard = provision.network_denied()
        guard.__enter__()
        self.addCleanup(guard.__exit__, None, None, None)
        original_import = builtins.__import__

        def no_ml(name, *args, **kwargs):
            if name.split('.')[0] in {'torch', 'transformers', 'accelerate', 'huggingface_hub', 'qwen_vl_utils', 'torchvision'}:
                raise AssertionError('real ML import forbidden')
            return original_import(name, *args, **kwargs)
        guard = patch('builtins.__import__', side_effect=no_ml)
        guard.start()
        self.addCleanup(guard.stop)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name).resolve()
        self.plan = provision.load_plan()
        self.runtime = Runtime()
        self.runtime.model.config.vision_config = SimpleNamespace(spatial_merge_size=2)
        self.runtime.model.config.image_token_id = 151655
        self.runtime.processor.image_processor.merge_size = 2
        self.runtime.processor.grid = [[1, 32, 32]]
        self.runtime.processor.rows = [[11] + [151655] * 256 + [22]]
        self.runner = Qwen2_5VLRunner(backend_factory=self.runtime.factory)

    def load(self):
        self.runner.initialize(context())
        self.runner.load(context())

    def run_fake(self, run_id='fake', **patches):
        for path in (provision.PLAN, 'scripts/w2_qwen2_5_t4_smoke.py',
                     'scripts/provision_qwen2_5_snapshot.py', 'safeshift/runners/qwen2_5_vl.py'):
            target = self.repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
        rt = self.runtime
        pins = self.plan['software']
        rt.factory.return_value = replace(rt.backend, software_versions={k: pins[k] for k in rt.backend.software_versions})
        rt.model.modules = lambda: iter([type(name, (), {})() for name in
            ('Qwen2_5_VLSdpaAttention', 'Qwen2_5_VLVisionSdpaAttention')])
        rt.torch.version = SimpleNamespace(cuda='12.4')
        rt.torch.cuda = SimpleNamespace(OutOfMemoryError=FakeOOM, synchronize=Mock(),
            memory_allocated=Mock(return_value=100), memory_reserved=Mock(return_value=200),
            max_memory_allocated=Mock(return_value=300), max_memory_reserved=Mock(return_value=400),
            reset_peak_memory_stats=Mock())
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, smoke.OFFLINE_ENV))
            stack.enter_context(patch.object(smoke.subprocess, 'check_output', return_value='a'*40))
            stack.enter_context(patch.object(smoke.platform, 'system', return_value='Linux'))
            stack.enter_context(patch.object(smoke.platform, 'machine', return_value='x86_64'))
            stack.enter_context(patch.object(smoke.importlib.metadata, 'distributions', return_value=[]))
            defaults = {'software_versions': Mock(return_value=pins),
                'probe_hardware': Mock(return_value={'gpu_name': 'Tesla T4', 'visible_gpu_count': 1}),
                'cached_snapshot': Mock(return_value=Path('unused')),
                'verify_snapshot': Mock(return_value={'local_bytes_verified': True, 'revision': provision.REVISION})}
            defaults.update(patches)
            for name, value in defaults.items():
                stack.enter_context(patch.object(smoke, name, value))
            return smoke.run_smoke(run_id, repo=self.repo, runner_factory=lambda: self.runner, torch_module=rt.torch)

    def test_sdpa_exact_loader_argument(self):
        self.load()
        self.assertEqual(self.runtime.model_factory.from_pretrained.call_args.kwargs['attn_implementation'], 'sdpa')

    def test_exact_processor_load_caps(self):
        self.load()
        args = self.runtime.processor_factory.from_pretrained.call_args.kwargs
        self.assertEqual((args['min_pixels'], args['max_pixels']), (200704, 1003520))
        self.assertIs(args['local_files_only'], True)
        self.assertIs(args['trust_remote_code'], False)

    def test_ambiguous_wrong_or_extra_preprocessing_blocked(self):
        for value in ({}, {'mode': 'official_processor'},
                      {**runner_module.PREPROCESSING, 'min_pixels': 1},
                      {**runner_module.PREPROCESSING, 'max_pixels': 1},
                      {**runner_module.PREPROCESSING, 'max_pixels': 1003520.0},
                      {**runner_module.PREPROCESSING, 'resized_width': 32}):
            with self.subTest(value=value), self.assertRaises(runner_module.Qwen2_5InitializeDiagnosticFailure) as raised:
                self.runner.initialize(context(preprocessing=value))
            self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_eager_native_load_rejected_no_retry(self):
        self.runtime.model.config._attn_implementation = 'eager'
        with self.assertRaises(runner_module.Qwen2_5LoadDiagnosticFailure) as raised:
            self.load()
        self.assertIsInstance(raised.exception.__cause__, ValueError)
        self.assertEqual(raised.exception.diagnostic_stage, 'MODEL_VALIDATE')
        self.assertIsNone(self.runner._resources)
        self.assertEqual(self.runtime.model_factory.from_pretrained.call_count, 1)

    def test_native_output_attentions_fallback_blocked(self):
        self.runtime.model.config.output_attentions = True
        with self.assertRaises(runner_module.Qwen2_5LoadDiagnosticFailure) as raised:
            self.load()
        self.assertIsInstance(raised.exception.__cause__, ValueError)
        self.assertEqual(raised.exception.diagnostic_stage, 'MODEL_VALIDATE')

    def test_loaded_processor_caps_checked(self):
        self.runtime.processor.image_processor.max_pixels = 999
        with self.assertRaises(runner_module.Qwen2_5LoadDiagnosticFailure) as raised:
            self.load()
        self.assertIsInstance(raised.exception.__cause__, ValueError)
        self.assertEqual(raised.exception.diagnostic_stage, 'PROCESSOR_VALIDATE')
        self.runtime.model_factory.from_pretrained.assert_not_called()

    def test_changed_processor_after_load_blocked(self):
        self.load()
        self.runtime.processor.image_processor.min_pixels = 1
        with self.assertRaises(ValueError):
            self.runner.prepare_input(request(), context())

    def test_condition_contains_sdpa_and_caps(self):
        key = json.loads(self.runner._key(context()))
        self.assertEqual(key['loader']['attn_implementation'], 'sdpa')
        self.assertEqual(key['loader']['min_pixels'], 200704)
        self.assertEqual(key['loader']['max_pixels'], 1003520)

    def test_raw_metadata_caps_and_sdpa_validated(self):
        self.load()
        raw = self.runner.generate_raw(self.runner.prepare_input(request(), context()), context())
        data = json.loads(raw)
        self.assertEqual(data['runtime']['preprocessing'], runner_module.PREPROCESSING)
        self.assertEqual(data['runtime']['attn_implementation'], 'sdpa')
        for key, wrong in (('attn_implementation', 'eager'), ('preprocessing', {})):
            tampered = deepcopy(data)
            tampered['runtime'][key] = wrong
            with self.assertRaises(ValueError):
                Qwen2_5VLAdapter().adapt(json.dumps(tampered).encode(), request().task)

    def test_identity_and_resource_policy_unchanged(self):
        self.assertEqual(self.plan['model_id'], 'Qwen/Qwen2.5-VL-3B-Instruct')
        self.assertEqual(self.plan['model_revision'], '66285546d2b821cf421d4f5eb2576359d3770cd3')
        self.assertEqual((self.plan['precision'], self.plan['quantization'], self.plan['batch_size']), ('FP16', 'NONE', 1))
        self.assertTrue(all(v == 'FORBIDDEN' for k, v in self.plan['device_policy'].items() if k != 'placement'))

    def test_documentary_pins_and_wheel_evidence(self):
        self.assertEqual(self.plan['software']['transformers'], '4.51.3')
        self.assertEqual(self.plan['software']['qwen-vl-utils'], '0.0.8')
        self.assertEqual(self.plan['qwen_vl_utils_wheel_sha256'], '2988aa08256f3d7ee6f08d7b27b004e840608b61ed36d0b32d1775be56a1639d')
        for name in self.plan['software'].keys() - {'python'}:
            evidence = self.plan['software_evidence'][name]
            self.assertRegex(evidence['wheel_sha256'], r'^[0-9a-f]{64}$')
            self.assertTrue(evidence['wheel_filename'].endswith('.whl'))

    def test_plan_modification_rejected(self):
        path = self.repo / provision.PLAN
        path.parent.mkdir(parents=True)
        path.write_text('{}')
        with self.assertRaises(ValueError):
            provision.load_plan(self.repo)

    def test_plan_hash_stable_across_windows_checkout(self):
        path = self.repo / provision.PLAN
        path.parent.mkdir(parents=True)
        path.write_bytes(json.dumps(self.plan, indent=4).replace('\n', '\r\n').encode())
        self.assertEqual(provision.load_plan(self.repo), self.plan)

    def test_provision_requests_only_exact_revision(self):
        module = SimpleNamespace(snapshot_download=Mock(return_value=Path('models--Qwen--Qwen2.5-VL-3B-Instruct/snapshots') / provision.REVISION))
        original = builtins.__import__
        with patch('builtins.__import__', side_effect=lambda name, *a, **kw: module if name == 'huggingface_hub' else original(name, *a, **kw)):
            provision.cached_snapshot(provision=True)
        args = module.snapshot_download.call_args.kwargs
        self.assertEqual(args['repo_id'], self.plan['model_id'])
        self.assertEqual(args['revision'], self.plan['model_revision'])
        self.assertIs(args['local_files_only'], False)
        self.assertEqual(set(args['allow_patterns']), {f['path'] for f in self.plan['snapshot_files']})

    def test_verify_resolver_local_files_only(self):
        module = SimpleNamespace(snapshot_download=Mock(return_value=Path('models--Qwen--Qwen2.5-VL-3B-Instruct/snapshots') / provision.REVISION))
        original = builtins.__import__
        with patch('builtins.__import__', side_effect=lambda name, *a, **kw: module if name == 'huggingface_hub' else original(name, *a, **kw)):
            provision.cached_snapshot()
        self.assertIs(module.snapshot_download.call_args.kwargs['local_files_only'], True)

    def test_verify_only_network_forbidden(self):
        with patch.object(provision, 'cached_snapshot', side_effect=lambda *a, **kw: socket.create_connection(('example.org', 443))):
            with self.assertRaisesRegex(RuntimeError, 'NETWORK_FORBIDDEN'):
                provision.provision_or_verify()

    def fake_snapshot(self):
        path = self.repo / 'models--Qwen--Qwen2.5-VL-3B-Instruct/snapshots' / provision.REVISION
        path.mkdir(parents=True)
        files = []
        for name, content, algorithm in (('config.json', b'{}', 'git_blob_sha1'), ('model.safetensors', b'FAKE-NOT-WEIGHTS', 'sha256')):
            (path / name).write_bytes(content)
            digest = hashlib.sha256(content).hexdigest() if algorithm == 'sha256' else hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
            files.append({'path': name, 'size_bytes': len(content), 'hash_algorithm': algorithm, 'expected_hash': digest})
        return path, {'snapshot_files': files}

    def test_verify_snapshot_hashes_all_files(self):
        path, plan = self.fake_snapshot()
        with patch.object(provision, 'load_plan', return_value=plan):
            result = provision.verify_snapshot(path)
        self.assertTrue(result['local_bytes_verified'])
        self.assertEqual(result['total_bytes'], 18)
        self.assertTrue(all(len(f['sha256']) == 64 for f in result['files']))

    def test_snapshot_tampering_rejected(self):
        path, plan = self.fake_snapshot()
        for name in ('config.json', 'model.safetensors'):
            previous = (path / name).read_bytes()
            (path / name).write_bytes(b'X' * len(previous))
            with patch.object(provision, 'load_plan', return_value=plan), self.assertRaises(ValueError):
                provision.verify_snapshot(path)
            (path / name).write_bytes(previous)

    def test_missing_and_extra_snapshot_files_rejected(self):
        path, plan = self.fake_snapshot()
        (path / 'extra.py').write_text('not executed')
        with patch.object(provision, 'load_plan', return_value=plan), self.assertRaises(ValueError):
            provision.verify_snapshot(path)
        (path / 'config.json').unlink()
        with patch.object(provision, 'load_plan', return_value=plan), self.assertRaises(OSError):
            provision.verify_snapshot(path)

    def test_mutable_snapshot_ref_rejected(self):
        with self.assertRaises(ValueError):
            provision.verify_snapshot(self.repo / 'snapshots/main')

    def test_snapshot_manifest_no_overwrite(self):
        path = self.repo / 'report.json'
        provision.write_json(path, {})
        with self.assertRaises(FileExistsError):
            provision.write_json(path, {})

    def test_scope_two_classification_cases_no_gate(self):
        self.assertEqual(self.plan['smoke']['case_ids'], list(smoke.CASE_IDS))
        self.assertEqual(self.plan['smoke']['task'], 'classification')
        self.assertFalse(self.plan['inspecsafe_used'])
        self.assertFalse(self.plan['inspecsafe_authorized'])
        self.assertFalse(self.plan['synthetic_gate_used'])
        self.assertEqual(self.plan['protocol_freeze_commit_sha'], 'PENDING')
        cases = smoke.generate_cases()
        self.assertEqual(len(cases), 2)
        self.assertNotEqual(cases[0][1], cases[1][1])
        self.assertTrue(all(raw.startswith(b'\x89PNG') for _, raw, _ in cases))

    def test_gpu_count_and_name_gate(self):
        cuda = SimpleNamespace(is_available=lambda: True, device_count=lambda: 1,
             get_device_properties=lambda _: SimpleNamespace(name='Tesla T4', major=7, minor=5, total_memory=16*1024**3))
        torch = SimpleNamespace(cuda=cuda, version=SimpleNamespace(cuda='12.4'))
        with patch.object(smoke.subprocess, 'run', side_effect=OSError):
            self.assertEqual(smoke.probe_hardware(torch)['visible_gpu_count'], 1)
            cuda.device_count = lambda: 2
            with self.assertRaises(ValueError): smoke.probe_hardware(torch)
            cuda.device_count = lambda: 1
            cuda.get_device_properties = lambda _: SimpleNamespace(name='A100', major=8, minor=0)
            with self.assertRaises(ValueError): smoke.probe_hardware(torch)

    def test_fake_smoke_complete_bundle_and_independence(self):
        report = self.run_fake()
        self.assertEqual(report['status'], 'RUNTIME_INTERFACE_PASS')
        self.assertEqual(report['native_generate_calls'], 2)
        self.assertTrue(all(c['state_cleared'] for c in report['calls']))
        self.assertEqual(self.runtime.model_factory.from_pretrained.call_count, 1)
        self.assertEqual(len(report['artifacts']), 9)
        for case in smoke.CASE_IDS:
            for name in ('response.raw', 'metadata.json', 'result.json'):
                self.assertIn(case + '/' + name, report['artifacts'])
        self.assertEqual(set(report['memory']), {'before_load', 'after_load', *smoke.CASE_IDS})
        self.assertEqual(self.runtime.torch.cuda.reset_peak_memory_stats.call_count, 2)
        self.assertIsNot(self.runtime.model.calls[0]['input_ids'], self.runtime.model.calls[1]['input_ids'])

    def test_smoke_no_overwrite(self):
        self.run_fake()
        with self.assertRaises(FileExistsError): self.run_fake()

    def test_wrong_environment_fails_before_load(self):
        report = self.run_fake(software_versions=Mock(return_value={}))
        self.assertEqual(report['status'], 'RUNTIME_INTERFACE_FAILURE')
        self.runtime.model_factory.from_pretrained.assert_not_called()

    def test_offline_env_missing_fails_before_import(self):
        self.run_fake('setup')
        factory = Mock(side_effect=AssertionError('must fail before backend'))
        with patch.dict(os.environ, {**smoke.OFFLINE_ENV, 'HF_HUB_OFFLINE': '0'}), \
                patch.object(smoke.subprocess, 'check_output', return_value='a'*40):
            report = smoke.run_smoke('missing-offline', repo=self.repo,
                                     runner_factory=factory, torch_module=self.runtime.torch)
        self.assertEqual(report['status'], 'RUNTIME_INTERFACE_FAILURE')
        self.assertEqual(report['failure']['stage'], 'PREFLIGHT')
        factory.assert_not_called()

    def test_custom_cache_must_match_loader_cache(self):
        self.run_fake('setup')
        with patch.dict(os.environ, {**smoke.OFFLINE_ENV, 'HF_HUB_CACHE': 'different-cache'}), \
                patch.object(smoke.subprocess, 'check_output', return_value='a'*40):
            result = smoke.run_smoke('cache-mismatch', repo=self.repo,
                                     cache_dir=self.repo / 'data/processed/cache')
        self.assertEqual(result['failure'], {'stage': 'PREFLIGHT', 'error_type': 'ValueError'})

    def test_network_attempt_during_load_fails(self):
        self.runtime.model_factory.from_pretrained.side_effect = lambda *a, **kw: socket.create_connection(('example.org', 443))
        report = self.run_fake()
        self.assertEqual(report['status'], 'RUNTIME_INTERFACE_FAILURE')
        self.assertEqual(report['native_generate_calls'], 0)

    def test_bad_snapshot_fails_before_load(self):
        report = self.run_fake(verify_snapshot=Mock(side_effect=ValueError('bad snapshot')))
        self.assertEqual(report['status'], 'RUNTIME_INTERFACE_FAILURE')
        self.runtime.model_factory.from_pretrained.assert_not_called()

    def test_placement_rejects_cpu_meta_disk_and_second_gpu(self):
        self.run_fake('setup')
        for device in ('cpu', 'meta', 'disk', 'cuda:1'):
            for items in (self.runtime.model.params, self.runtime.model.bufs):
                original = items[0].device
                items[0].device = device
                with self.assertRaises(ValueError):
                    smoke.placement_gate(self.runtime.model, self.runtime.processor, self.runtime.torch)
                items[0].device = original

    def test_placement_rejects_dtype_quantization_eager(self):
        self.run_fake('setup')
        self.runtime.model.params[0].dtype = 'torch.float32'
        with self.assertRaises(ValueError): smoke.placement_gate(self.runtime.model, self.runtime.processor, self.runtime.torch)

        self.runtime.model.params[0].dtype = 'torch.float16'
        self.runtime.model.is_quantized = True
        with self.assertRaises(ValueError): smoke.placement_gate(self.runtime.model, self.runtime.processor, self.runtime.torch)
        self.runtime.model.is_quantized = False
        self.runtime.model.config._attn_implementation = 'eager'
        with self.assertRaises(ValueError): smoke.placement_gate(self.runtime.model, self.runtime.processor, self.runtime.torch)

    def test_native_vision_eager_module_rejected(self):
        self.run_fake('setup')
        self.runtime.model.modules = lambda: iter([type('Qwen2_5_VLVisionAttention', (), {})()])
        with self.assertRaises(ValueError):
            smoke.placement_gate(self.runtime.model, self.runtime.processor, self.runtime.torch)

    def test_oom_generate_resource_failure_no_fallback(self):
        self.runtime.model.failure = FakeOOM('sensitive text')
        report = self.run_fake()
        self.assertEqual(report['status'], 'RUNTIME_RESOURCE_FAILURE')
        self.assertEqual(report['native_generate_calls'], 1)
        self.assertNotIn('sensitive text', json.dumps(report))

    def test_oom_load_resource_failure(self):
        self.runtime.model_factory.from_pretrained.side_effect = FakeOOM()
        self.assertEqual(self.run_fake()['status'], 'RUNTIME_RESOURCE_FAILURE')

    def test_prepare_oom_resource_failure(self):
        self.runner.prepare_input = Mock(side_effect=FakeOOM())
        self.assertEqual(self.run_fake()['status'], 'RUNTIME_RESOURCE_FAILURE')

    def test_post_generate_oom_preserves_raw_and_resource_status(self):
        self.runtime.processor.batch_decode = Mock(side_effect=FakeOOM())
        result = self.run_fake()
        self.assertEqual(result['status'], 'RUNTIME_RESOURCE_FAILURE')
        self.assertIn('case_01/response.raw', result['artifacts'])

    def test_invalid_classification_is_observation_not_accuracy(self):
        self.runtime.processor.text = 'unparseable'
        result = self.run_fake()
        self.assertEqual(result['status'], 'RUNTIME_INTERFACE_PASS')
        self.assertTrue(all(c['parse_status'] == 'INVALID' for c in result['calls']))

    def test_parser_exception_fails(self):
        with patch.object(smoke.Qwen2_5VLAdapter, 'adapt', side_effect=ValueError()):
            result = self.run_fake()
        self.assertEqual(result['status'], 'RUNTIME_INTERFACE_FAILURE')
        self.assertIn('case_01/response.raw', result['artifacts'])

    def test_evidence_write_failure_cannot_pass(self):
        with patch.object(smoke.CaseRawStore, 'preserve', side_effect=OSError()):
            self.assertEqual(self.run_fake()['status'], 'RUNTIME_INTERFACE_FAILURE')

    def test_invalid_run_id_and_case_path_rejected(self):
        with self.assertRaises(ValueError): smoke.run_smoke('../escape', repo=self.repo)
        store = smoke.CaseRawStore(self.repo)
        with self.assertRaises(ValueError): store._directory({'call_id': '../escape', 'sample_id': '../escape'})

    def observe(self, grid=None, *, placeholders=256):
        prepared = SimpleNamespace(inputs={
            'image_grid_thw': Tensor([[1, 32, 32]] if grid is None else grid),
            'input_ids': Tensor([[11] + [151655] * placeholders + [22]])})
        evidence = smoke.empty_visual_observation()
        smoke.observe_visual_tokens(prepared, self.runtime.model, self.runtime.processor, evidence)
        return evidence

    def test_observed_grid_is_actual_primitive_copy(self):
        evidence = self.observe([[1, 40, 32]], placeholders=320)
        self.assertEqual(evidence, {'observed_image_grid_thw': [[1, 40, 32]],
            'observed_spatial_merge_size': 2, 'observed_visual_token_count': 320,
            'observed_image_token_placeholder_count': 320})
        self.assertEqual(json.loads(json.dumps(evidence)), evidence)

    def test_grid_exact_one_by_three_shape(self):
        for grid in ([], [1, 32, 32], [[1, 32]], [[1, 32, 32, 1]],
                     [[1, 32, 32], [1, 32, 32]], [(1, 32, 32)]):
            with self.subTest(grid=grid), self.assertRaises(ValueError): self.observe(grid)

    def test_grid_positive_exact_ints_not_bool_or_float(self):
        for position in range(3):
            for value in (0, -1, True, False, 32.0, '32', None):
                grid = [[1, 32, 32]]
                grid[0][position] = value
                with self.subTest(position=position, value=value), self.assertRaises(ValueError):
                    self.observe(grid)

    def test_merge_size_read_from_both_runtime_objects_not_hardcoded(self):
        self.runtime.model.config.vision_config.spatial_merge_size = 3
        self.runtime.processor.image_processor.merge_size = 3
        evidence = self.observe([[1, 48, 60]], placeholders=320)
        self.assertEqual(evidence['observed_spatial_merge_size'], 3)
        self.assertEqual(evidence['observed_visual_token_count'], 320)

    def test_merge_size_missing_invalid_or_mismatched_rejected(self):
        for owner, field in ((self.runtime.model.config.vision_config, 'spatial_merge_size'),
                             (self.runtime.processor.image_processor, 'merge_size')):
            for value in (0, -2, True, False, 2.0, '2', None, 4):
                setattr(owner, field, value)
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.observe()
            delattr(owner, field)
            with self.assertRaises(AttributeError): self.observe()
            setattr(owner, field, 2)

    def test_nondivisible_height_and_width_rejected_before_division(self):
        for grid in ([[1, 33, 32]], [[1, 32, 33]]):
            with self.subTest(grid=grid), self.assertRaisesRegex(ValueError, 'NOT_DIVISIBLE'):
                self.observe(grid)

    def test_visual_formula_uses_temporal_dimension(self):
        # Generic source formula; the unchanged still-image runner separately enforces t=1.
        self.assertEqual(self.observe([[2, 32, 32]], placeholders=512)['observed_visual_token_count'], 512)

    def test_visual_range_inclusive_boundaries(self):
        for grid, count in (([[1, 32, 32]], 256), ([[1, 64, 80]], 1280)):
            with self.subTest(count=count):
                self.assertEqual(self.observe(grid, placeholders=count)['observed_visual_token_count'], count)

    def test_visual_range_below_and_above_rejected(self):
        for grid in ([[1, 30, 32]], [[1, 64, 82]]):
            with self.subTest(grid=grid), self.assertRaisesRegex(ValueError, 'OUTSIDE_QUALIFICATION_CAP'):
                self.observe(grid)

    def test_placeholder_mismatch_rejected(self):
        for count in (0, 255, 257):
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, 'PLACEHOLDER_COUNT_MISMATCH'):
                self.observe(placeholders=count)

    def test_image_token_id_observed_not_hardcoded(self):
        self.runtime.model.config.image_token_id = 99
        prepared = SimpleNamespace(inputs={'image_grid_thw': Tensor([[1, 32, 32]]),
                                          'input_ids': Tensor([[99] * 256])})
        evidence = {}
        smoke.observe_visual_tokens(prepared, self.runtime.model, self.runtime.processor, evidence)
        self.assertEqual(evidence['observed_image_token_placeholder_count'], 256)

    def test_image_token_id_and_input_rows_must_be_valid(self):
        for value in (True, -1, 151655.0, None):
            self.runtime.model.config.image_token_id = value
            with self.assertRaises(ValueError): self.observe()
        self.runtime.model.config.image_token_id = 151655
        for rows in ([], [[], []], [[True]], [[151655.0]], [[-1]], [[]]):
            prepared = SimpleNamespace(inputs={'image_grid_thw': Tensor([[1, 32, 32]]),
                                               'input_ids': Tensor(rows)})
            with self.assertRaises(ValueError):
                smoke.observe_visual_tokens(prepared, self.runtime.model, self.runtime.processor, {})

    def test_each_case_observed_once_without_carryover(self):
        original = self.runner.prepare_input
        grids = iter(([[1, 32, 32]], [[1, 40, 32]]))

        def prepare(request, ctx):
            self.runtime.processor.grid = next(grids)
            count = 256 if ctx.call_id == 'case_01' else 320
            self.runtime.processor.rows = [[11] + [151655] * count + [22]]
            return original(request, ctx)

        counter = Mock(side_effect=prepare)
        self.runner.prepare_input = counter
        result = self.run_fake()
        self.assertEqual(result['status'], 'RUNTIME_INTERFACE_PASS')
        self.assertEqual(counter.call_count, 2)
        self.assertEqual(len(self.runtime.processor.calls), 2)
        self.assertEqual(len(self.runtime.vision_calls), 2)
        self.assertEqual(len(self.runtime.model.calls), 2)
        self.assertEqual(result['native_generate_calls'], 2)
        self.assertEqual([c['case_id'] for c in result['calls']], ['case_01', 'case_02'])
        self.assertEqual([c['observed_image_grid_thw'] for c in result['calls']], [[[1, 32, 32]], [[1, 40, 32]]])
        self.assertEqual([c['observed_visual_token_count'] for c in result['calls']], [256, 320])
        self.assertEqual([c['observed_image_token_placeholder_count'] for c in result['calls']], [256, 320])
        persisted = json.loads((self.repo / smoke.ARTIFACTS / 'fake/summary.json').read_text())
        self.assertEqual(persisted['calls'], result['calls'])

    def test_second_prepare_failure_never_reuses_first_observation(self):
        original = self.runner.prepare_input

        def prepare(request, ctx):
            if ctx.call_id == 'case_02':
                raise ValueError('failed second preparation')
            return original(request, ctx)

        self.runner.prepare_input = Mock(side_effect=prepare)
        result = self.run_fake()
        self.assertEqual(result['status'], 'RUNTIME_INTERFACE_FAILURE')
        self.assertEqual(result['calls'][0]['observed_visual_token_count'], 256)
        for key in smoke.empty_visual_observation():
            self.assertIsNone(result['calls'][1][key])
        self.assertEqual(result['native_generate_calls'], 1)

    def test_observation_failures_are_interface_failures_before_generate(self):
        original = self.runner.prepare_input
        for index, failure in enumerate(('missing_grid', 'malformed_grid', 'merge_mismatch',
                                        'height', 'width', 'below', 'above', 'placeholders')):
            def prepare(request, ctx):
                prepared = original(request, ctx)
                if failure == 'missing_grid':
                    del prepared.inputs['image_grid_thw']
                elif failure == 'merge_mismatch':
                    self.runtime.processor.image_processor.merge_size = 3
                elif failure == 'placeholders':
                    prepared.inputs['input_ids'].data = [[11, 22]]
                else:
                    prepared.inputs['image_grid_thw'].data = {
                        'malformed_grid': [[1, True, 32]], 'height': [[1, 33, 32]],
                        'width': [[1, 32, 33]], 'below': [[1, 30, 32]],
                        'above': [[1, 64, 82]]}[failure]
                return prepared
            self.runner.prepare_input = prepare
            result = self.run_fake('invalid_' + str(index))
            self.runtime.processor.image_processor.merge_size = 2
            with self.subTest(failure=failure):
                self.assertEqual(result['status'], 'RUNTIME_INTERFACE_FAILURE')
                self.assertEqual(result['native_generate_calls'], 0)
                self.assertIsNone(result['calls'][0]['raw'])

    def test_observation_cuda_oom_retains_resource_classification(self):
        with patch.object(smoke, 'observe_visual_tokens', side_effect=FakeOOM()):
            self.assertEqual(self.run_fake()['status'], 'RUNTIME_RESOURCE_FAILURE')

    def test_obs_plan_and_all_software_pins_unchanged(self):
        expected = 'aa4fcff85d670d844025a540d85f10514919c60f6709de8be8f6be0922fd63fb'
        self.assertEqual(provision.PLAN_SHA256, expected)
        canonical = json.dumps(self.plan, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), expected)
        self.assertEqual(self.plan['software'], {'python': '3.11.11', 'torch': '2.6.0+cu124',
            'torchvision': '0.21.0+cu124', 'transformers': '4.51.3', 'qwen-vl-utils': '0.0.8',
            'accelerate': '1.6.0', 'pillow': '11.2.1', 'huggingface-hub': '0.30.2',
            'tokenizers': '0.21.1', 'safetensors': '0.5.3'})
        self.assertEqual(self.plan['attention_implementation'], 'sdpa')
        self.assertEqual(self.plan['processor'], {'mode': 'official_processor_capped',
                         'min_pixels': 200704, 'max_pixels': 1003520})
        self.assertEqual(runner_module.ENVELOPE_VERSION, 'safeshift-qwen2-5-vl-raw-v2')


if __name__ == '__main__':
    unittest.main()
