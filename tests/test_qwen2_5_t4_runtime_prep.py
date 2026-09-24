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
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.runner.initialize(context(preprocessing=value))

    def test_eager_native_load_rejected_no_retry(self):
        self.runtime.model.config._attn_implementation = 'eager'
        with self.assertRaises(ValueError):
            self.load()
        self.assertIsNone(self.runner._resources)
        self.assertEqual(self.runtime.model_factory.from_pretrained.call_count, 1)

    def test_native_output_attentions_fallback_blocked(self):
        self.runtime.model.config.output_attentions = True
        with self.assertRaises(ValueError):
            self.load()

    def test_loaded_processor_caps_checked(self):
        self.runtime.processor.image_processor.max_pixels = 999
        with self.assertRaises(ValueError):
            self.load()
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


if __name__ == '__main__':
    unittest.main()
