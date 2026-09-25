"""Initialize/probe tests with real ML imports and network denied."""

from contextlib import contextmanager, ExitStack
import json
import os
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from safeshift.runners import qwen2_5_vl as module
from scripts import w2_qwen2_5_t4_init_probe as probe
from scripts import provision_qwen2_5_snapshot as provision
from tests import test_qwen2_5_t4_runtime_prep as prep_tests

STAGES = ('CONDITION_VALIDATE', 'BACKEND_CONSTRUCT', 'SOFTWARE_METADATA_COPY',
          'SOFTWARE_REQUIRED_KEYS_VALIDATE', 'SOFTWARE_VERSION_VALIDATE', 'BACKEND_PUBLISH')
SECRET = 'hf_FAKE_ONLY ghp_FAKE_ONLY C:\\secret-user\\private /private/auth'
COMMIT = 'a' * 40


class InitializeDiagnosticsTests(unittest.TestCase):
    setUp = prep_tests.RuntimePrepTests.setUp

    @contextmanager
    def fail_stage(self, stage, error):
        rt = self.runtime
        if stage in ('CONDITION_VALIDATE', 'BACKEND_CONSTRUCT', 'BACKEND_PUBLISH'):
            owner, name = {'CONDITION_VALIDATE': (self.runner, '_check_condition'),
                           'BACKEND_CONSTRUCT': (self.runner, '_backend_factory'),
                           'BACKEND_PUBLISH': (module, 'Qwen2_5Backend')}[stage]
            with patch.object(owner, name, side_effect=error):
                yield
        else:
            original_copy = module.deepcopy

            class BadKeys(dict):
                def keys(self):
                    raise error

            class BadVersions(dict):
                def items(self):
                    raise error

            def copy(value):
                if value is rt.backend.software_versions:
                    if stage == 'SOFTWARE_METADATA_COPY':
                        raise error
                    return BadKeys(value) if stage == 'SOFTWARE_REQUIRED_KEYS_VALIDATE' else BadVersions(value)
                return original_copy(value)

            with patch.object(module, 'deepcopy', side_effect=copy):
                yield

    def run_probe(self, run_id='probe', *, software=None, system='Linux', cuda='12.4',
                  commit=COMMIT, dirty='', offline=True, hardware=None):
        for path in (provision.PLAN, 'scripts/w2_qwen2_5_t4_init_probe.py',
                     'scripts/w2_qwen2_5_t4_smoke.py', 'scripts/provision_qwen2_5_snapshot.py',
                     'safeshift/runners/qwen2_5_vl.py'):
            dest = self.repo / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(prep_tests.ROOT / path, dest)
        # Keep exactly the same backend metadata object for targeted copy failures.
        self.runtime.backend.software_versions.update(
            {k: self.plan['software'][k] for k in self.runtime.backend.software_versions})
        self.runtime.torch.version = SimpleNamespace(cuda=cuda)
        self.runtime.torch.cuda = SimpleNamespace(OutOfMemoryError=prep_tests.FakeOOM)
        self.runner.load = Mock(side_effect=AssertionError('probe must not load'))
        self.runner.prepare_input = Mock(side_effect=AssertionError('probe must not prepare'))
        self.runner.generate_raw = Mock(side_effect=AssertionError('probe must not generate'))
        env = dict(probe.OFFLINE_ENV)
        if not offline:
            env['HF_HUB_OFFLINE'] = '0'
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, env))
            stack.enter_context(patch.object(probe.platform, 'system', return_value=system))
            stack.enter_context(patch.object(probe.platform, 'machine', return_value='x86_64'))
            stack.enter_context(patch.object(probe, 'software_versions', return_value=(self.plan['software'] if software is None else software)))
            stack.enter_context(patch.object(probe, 'probe_hardware', hardware or Mock(return_value={'gpu_name': 'Tesla T4', 'visible_gpu_count': 1})))
            stack.enter_context(patch.object(probe.subprocess, 'check_output', side_effect=[commit, dirty]))
            for name in ('cached_snapshot', 'verify_snapshot', 'provision_or_verify'):
                stack.enter_context(patch.object(provision, name, side_effect=AssertionError('snapshot forbidden')))
            result = probe.run_probe(run_id, COMMIT, repo=self.repo,
                                    runner_factory=lambda: self.runner, torch_module=self.runtime.torch)
        self.runner.load.assert_not_called()
        self.runner.prepare_input.assert_not_called()
        self.runner.generate_raw.assert_not_called()
        self.runtime.processor_factory.from_pretrained.assert_not_called()
        self.runtime.model_factory.from_pretrained.assert_not_called()
        self.assertIsNone(self.runner._resources)
        self.assertEqual(result['calls'], [])
        self.assertEqual(result['native_generate_calls'], 0)
        root = self.repo / probe.ARTIFACTS / run_id
        self.assertEqual({p.name for p in root.iterdir()},
            {'run_metadata.json', 'environment.json', 'summary.json', 'summary.json.sha256'})
        for path in root.iterdir():
            content = path.read_text(encoding='utf-8')
            for sensitive in (SECRET, 'hf_FAKE_ONLY', 'ghp_FAKE_ONLY', 'secret-user', '/private/auth', 'Traceback'):
                self.assertNotIn(sensitive, content)
        return result

    def check_stage(self, stage):
        with self.fail_stage(stage, ValueError(SECRET)):
            result = self.run_probe()
        self.assertEqual(result['status'], 'RUNTIME_INTERFACE_FAILURE')
        self.assertEqual(result['failure'], {'stage': 'INITIALIZE',
            'error_type': 'Qwen2_5InitializeDiagnosticFailure', 'initialize_substage': stage,
            'underlying_error_type': 'ValueError'})
        self.assertIsNone(self.runner._backend)
        self.assertIsNone(self.runner._condition)

    def test_condition_validate(self): self.check_stage('CONDITION_VALIDATE')

    def test_backend_construct(self): self.check_stage('BACKEND_CONSTRUCT')

    def test_software_metadata_copy(self): self.check_stage('SOFTWARE_METADATA_COPY')

    def test_software_required_keys(self): self.check_stage('SOFTWARE_REQUIRED_KEYS_VALIDATE')

    def test_software_version_validate(self): self.check_stage('SOFTWARE_VERSION_VALIDATE')

    def test_backend_publish(self): self.check_stage('BACKEND_PUBLISH')

    def test_wrapper_fields_and_cause(self):
        error = ValueError(SECRET, {'path': SECRET})
        with self.fail_stage('BACKEND_CONSTRUCT', error):
            with self.assertRaises(module.Qwen2_5InitializeDiagnosticFailure) as raised:
                self.runner.initialize(prep_tests.context())
        wrapper = raised.exception
        self.assertEqual(vars(wrapper), {'diagnostic_stage': 'BACKEND_CONSTRUCT', 'underlying_error_type': 'ValueError'})
        self.assertEqual(wrapper.args, ())
        self.assertEqual(str(wrapper), '')
        self.assertNotIn(SECRET, repr(wrapper))
        self.assertIs(wrapper.__cause__, error)

    def test_original_str_and_repr_never_used(self):
        class UnprintableError(RuntimeError):
            def __str__(self): raise AssertionError('forbidden str')
            def __repr__(self): raise AssertionError('forbidden repr')
        with self.fail_stage('BACKEND_CONSTRUCT', UnprintableError(SECRET)):
            self.assertEqual(self.run_probe()['failure']['underlying_error_type'], 'UnprintableError')

    def test_wrapped_oom_at_every_initialize_substage(self):
        for stage in STAGES:
            with self.subTest(stage=stage), self.fail_stage(stage, prep_tests.FakeOOM(SECRET)):
                result = self.run_probe('oom_' + stage.lower())
            self.assertEqual(result['status'], 'RUNTIME_RESOURCE_FAILURE')
            self.assertEqual(result['failure']['initialize_substage'], stage)
            self.assertEqual(result['failure']['underlying_error_type'], 'FakeOOM')

    def test_probe_pass_stops_at_initialize_and_matches_smoke_context(self):
        observed = Mock(wraps=self.runner.initialize)
        self.runner.initialize = observed
        result = self.run_probe()
        self.assertEqual(result['status'], 'INITIALIZE_INTERFACE_PASS')
        observed.assert_called_once()
        ctx = observed.call_args.args[0]
        expected = probe.RunContext('probe', 'case_01', self.plan['smoke']['decoding'],
            dict(module.PREPROCESSING), 'FP16', 'NONE', {'placement': 'cuda:0'},
            self.plan['software'], COMMIT, ctx.command, 'HANDCRAFTED_RUNTIME_SMOKE')
        self.assertEqual(ctx, expected)
        self.assertEqual(self.runner._condition, self.runner._key(expected))
        self.assertEqual(result['artifacts']['environment.json']['sha256'],
                         provision.sha256_file(self.repo / probe.ARTIFACTS / 'probe/environment.json'))
        root = self.repo / probe.ARTIFACTS / 'probe'
        self.assertEqual((root / 'summary.json.sha256').read_text().split()[0], provision.sha256_file(root / 'summary.json'))

    def test_exact_git_commit_required(self):
        result = self.run_probe(commit='b'*40)
        self.assertEqual(result['failure']['stage'], 'PREFLIGHT')
        self.runtime.factory.assert_not_called()

    def test_dirty_tracked_sources_blocked(self):
        self.assertEqual(self.run_probe(dirty=' M script.py')['status'], 'RUNTIME_INTERFACE_FAILURE')
        self.runtime.factory.assert_not_called()

    def test_wrong_software_blocked_before_initialize(self):
        self.assertEqual(self.run_probe(software={})['failure']['stage'], 'ENVIRONMENT')
        self.runtime.factory.assert_not_called()

    def test_wrong_platform_blocked(self):
        self.assertEqual(self.run_probe(system='Windows')['failure']['stage'], 'ENVIRONMENT')
        self.runtime.factory.assert_not_called()

    def test_wrong_cuda_build_blocked(self):
        self.assertEqual(self.run_probe(cuda='11.8')['failure']['stage'], 'ENVIRONMENT')
        self.runtime.factory.assert_not_called()

    def test_non_t4_or_multiple_gpus_blocked_by_shared_gate(self):
        self.assertEqual(self.run_probe(hardware=Mock(side_effect=ValueError()))['failure']['stage'], 'ENVIRONMENT')
        self.runtime.factory.assert_not_called()

    def test_offline_env_required(self):
        self.assertEqual(self.run_probe(offline=False)['failure']['stage'], 'PREFLIGHT')
        self.runtime.factory.assert_not_called()

    def test_network_blocked_during_initialize(self):
        import socket
        with patch.object(self.runner, '_backend_factory', side_effect=lambda: socket.create_connection(('example.org', 443))):
            result = self.run_probe()
        self.assertEqual(result['failure']['initialize_substage'], 'BACKEND_CONSTRUCT')
        self.assertEqual(result['failure']['underlying_error_type'], 'RuntimeError')

    def test_no_overwrite_and_no_mutable_commit_or_bad_run_id(self):
        self.run_probe()
        with self.assertRaises(FileExistsError): self.run_probe()
        for run_id, commit in (('../escape', COMMIT), ('valid', 'main'), ('valid', 'a'*7)):
            with self.assertRaises(ValueError): probe.run_probe(run_id, commit, repo=self.repo)

    def test_full_smoke_records_initialize_substage_not_load(self):
        with self.fail_stage('SOFTWARE_VERSION_VALIDATE', ValueError(SECRET)):
            # Keep the same metadata object so the fault targets the runner copy.
            self.runtime.backend.software_versions.update(
                {k: self.plan['software'][k] for k in self.runtime.backend.software_versions})
            with patch.object(prep_tests, 'replace', side_effect=lambda value, **kw: value):
                result = prep_tests.RuntimePrepTests.run_fake(self)
        self.assertEqual(result['failure'], {'stage': 'INITIALIZE',
            'error_type': 'Qwen2_5InitializeDiagnosticFailure',
            'initialize_substage': 'SOFTWARE_VERSION_VALIDATE', 'underlying_error_type': 'ValueError'})
        self.assertEqual(result['calls'], [])
        self.assertEqual(result['native_generate_calls'], 0)
        self.runtime.model_factory.from_pretrained.assert_not_called()


if __name__ == '__main__':
    unittest.main()
