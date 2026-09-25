"""Fake-only load diagnostics; existing PREP fixture supplies network/ML guards."""

from contextlib import contextmanager
import json
from unittest.mock import Mock, patch
import unittest

from safeshift.runners import qwen2_5_vl as module
from scripts import w2_qwen2_5_t4_smoke as smoke
from tests import test_qwen2_5_t4_runtime_prep as prep_tests


STAGES = ('PROCESSOR_LOAD', 'PROCESSOR_VALIDATE', 'MODEL_LOAD', 'MODEL_EVAL',
          'MODEL_VALIDATE', 'GENERATION_CONFIG_VALIDATE', 'GENERATION_CONFIG_SNAPSHOT',
          'CALL_STATE_CLEAR', 'RESOURCE_PUBLISH')
SECRET = 'hf_FAKE_SECRET_ONLY ghp_FAKE_SECRET_ONLY C:\\private-user\\secret.txt /private/token'


class OutOfMemoryError(RuntimeError):
    """Fake CUDA type injected into fake torch; no native torch imported."""


class Qwen2_5LoadDiagnosticsTests(unittest.TestCase):
    setUp = prep_tests.RuntimePrepTests.setUp
    run_fake = prep_tests.RuntimePrepTests.run_fake
    load = prep_tests.RuntimePrepTests.load

    @contextmanager
    def fail_stage(self, stage, error):
        rt = self.runtime
        targets = {
            'PROCESSOR_LOAD': (rt.processor_factory, 'from_pretrained'),
            'PROCESSOR_VALIDATE': (self.runner, '_validate_processor'),
            'MODEL_LOAD': (rt.model_factory, 'from_pretrained'),
            'MODEL_EVAL': (rt.model, 'eval'),
            'MODEL_VALIDATE': (self.runner, '_validate_model'),
            'GENERATION_CONFIG_VALIDATE': (self.runner, '_validate_config'),
            'CALL_STATE_CLEAR': (self.runner, '_clear_call_state'),
        }
        if stage == 'GENERATION_CONFIG_SNAPSHOT':
            original_copy = module.deepcopy

            def copy(value):
                if value is rt.model.generation_config:
                    raise error
                return original_copy(value)

            with patch.object(module, 'deepcopy', side_effect=copy):
                yield
        elif stage == 'RESOURCE_PUBLISH':
            # The normal assignment has no custom hook. Inject failure *before*
            # assignment to exercise its label without modifying production logic.
            original_setattr = type(self.runner).__setattr__

            def publish(instance, name, value):
                if instance is self.runner and name == '_resources' and value is not None:
                    raise error
                original_setattr(instance, name, value)

            with patch.object(type(self.runner), '__setattr__', publish):
                yield
        else:
            owner, name = targets[stage]
            with patch.object(owner, name, side_effect=error):
                yield

    def assert_load_failure(self, stage, error=None):
        error = ValueError(SECRET) if error is None else error
        with self.fail_stage(stage, error):
            result = self.run_fake(stage.lower())
        self.assertEqual(result['status'], 'RUNTIME_INTERFACE_FAILURE')
        self.assertEqual(result['failure'], {
            'stage': 'LOAD', 'error_type': 'Qwen2_5LoadDiagnosticFailure',
            'load_substage': stage, 'underlying_error_type': type(error).__name__})
        self.assertIsNone(self.runner._resources)
        self.assertEqual(result['calls'], [])
        self.assertEqual(result['native_generate_calls'], 0)
        root = self.repo / smoke.ARTIFACTS / stage.lower()
        self.assertEqual(set(result['artifacts']),
                         {'run_metadata.json', 'environment.json', 'snapshot_manifest.json'})
        self.assertFalse(list(root.rglob('response.raw')))
        self.assertFalse(list(root.rglob('result.json')))
        self.assertFalse(any((root / case).exists() for case in smoke.CASE_IDS))
        for path in root.rglob('*'):
            if path.is_file():
                content = path.read_text(encoding='utf-8')
                self.assertNotIn(SECRET, content)
                self.assertNotIn('hf_FAKE_SECRET_ONLY', content)
                self.assertNotIn('ghp_FAKE_SECRET_ONLY', content)
                self.assertNotIn('private-user', content)
                self.assertNotIn('/private/token', content)
                self.assertNotIn('Traceback', content)
                self.assertNotIn('observed_image_grid_thw', content)
        return result

    def test_initialize_failure_is_not_load_failure(self):
        with patch.object(self.runner, 'initialize', side_effect=ValueError(SECRET)):
            result = self.run_fake()
        self.assertEqual(result['failure'], {'stage': 'INITIALIZE', 'error_type': 'ValueError'})
        self.assertEqual(result['status'], 'RUNTIME_INTERFACE_FAILURE')
        self.assertEqual(result['calls'], [])
        self.assertEqual(result['native_generate_calls'], 0)
        self.runtime.processor_factory.from_pretrained.assert_not_called()
        self.assertNotIn(SECRET, json.dumps(result))

    def test_processor_load_diagnostic(self):
        self.assert_load_failure('PROCESSOR_LOAD')
        self.runtime.model_factory.from_pretrained.assert_not_called()

    def test_processor_validate_diagnostic(self):
        self.assert_load_failure('PROCESSOR_VALIDATE')
        self.runtime.model_factory.from_pretrained.assert_not_called()

    def test_model_load_diagnostic(self):
        self.assert_load_failure('MODEL_LOAD')

    def test_model_eval_diagnostic(self):
        self.assert_load_failure('MODEL_EVAL', RuntimeError(SECRET))

    def test_model_validate_diagnostic(self):
        self.assert_load_failure('MODEL_VALIDATE')

    def test_generation_config_validate_diagnostic(self):
        self.assert_load_failure('GENERATION_CONFIG_VALIDATE')

    def test_generation_config_snapshot_diagnostic(self):
        self.assert_load_failure('GENERATION_CONFIG_SNAPSHOT')

    def test_call_state_clear_diagnostic(self):
        self.assert_load_failure('CALL_STATE_CLEAR')

    def test_publication_assignment_diagnostic(self):
        self.assert_load_failure('RESOURCE_PUBLISH')

    def test_wrapper_has_only_safe_fields_and_preserves_original_cause(self):
        original = ValueError(SECRET, {'private': SECRET})
        with self.fail_stage('MODEL_LOAD', original):
            with self.assertRaises(module.Qwen2_5LoadDiagnosticFailure) as raised:
                self.load()
        diagnostic = raised.exception
        self.assertEqual(vars(diagnostic), {'diagnostic_stage': 'MODEL_LOAD',
                                           'underlying_error_type': 'ValueError'})
        self.assertEqual(diagnostic.args, ())
        self.assertEqual(str(diagnostic), '')
        self.assertNotIn(SECRET, repr(diagnostic))
        self.assertIs(diagnostic.__cause__, original)

    def test_original_str_and_repr_are_never_evaluated(self):
        class UnprintableError(ValueError):
            def __str__(self):
                raise AssertionError('must not stringify original exception')

            def __repr__(self):
                raise AssertionError('must not repr original exception')

        self.assert_load_failure('MODEL_LOAD', UnprintableError(SECRET))

    def test_wrapped_cuda_oom_all_substages_remains_resource_failure(self):
        # run_fake installs prep_tests.FakeOOM as fake torch.cuda.OutOfMemoryError.
        with patch.object(prep_tests, 'FakeOOM', OutOfMemoryError):
            for stage in STAGES:
                with self.subTest(stage=stage), self.fail_stage(stage, OutOfMemoryError(SECRET)):
                    result = self.run_fake('oom_' + stage.lower())
                self.assertEqual(result['status'], 'RUNTIME_RESOURCE_FAILURE')
                self.assertEqual(result['failure'], {
                    'stage': 'LOAD', 'error_type': 'Qwen2_5LoadDiagnosticFailure',
                    'load_substage': stage, 'underlying_error_type': 'OutOfMemoryError'})
                self.assertIsNone(self.runner._resources)
                self.assertEqual(result['native_generate_calls'], 0)
                self.assertEqual(result['calls'], [])
                self.assertNotIn(SECRET, json.dumps(result))

    def test_failed_load_explicit_retry_preserves_idempotence(self):
        self.runner.initialize(prep_tests.context())
        with self.fail_stage('CALL_STATE_CLEAR', ValueError(SECRET)):
            with self.assertRaises(module.Qwen2_5LoadDiagnosticFailure):
                self.runner.load(prep_tests.context())
        self.assertIsNone(self.runner._resources)
        self.runner.load(prep_tests.context())
        resources = self.runner._resources
        self.runner.load(prep_tests.context())
        self.assertIs(resources, self.runner._resources)
        self.assertEqual(self.runtime.processor_factory.from_pretrained.call_count, 2)
        self.assertEqual(self.runtime.model_factory.from_pretrained.call_count, 2)

    def test_successful_smoke_and_loader_arguments_unchanged(self):
        prepare = Mock(wraps=self.runner.prepare_input)
        self.runner.prepare_input = prepare
        result = self.run_fake()
        self.assertEqual(result['status'], 'RUNTIME_INTERFACE_PASS')
        self.assertNotIn('failure', result)
        self.assertEqual(prepare.call_count, 2)
        self.assertEqual(result['native_generate_calls'], 2)
        self.assertEqual(len(result['calls']), 2)
        self.assertEqual([c['observed_visual_token_count'] for c in result['calls']], [256, 256])
        self.assertEqual([c['observed_image_token_placeholder_count'] for c in result['calls']], [256, 256])
        self.assertTrue(all(c['state_cleared'] for c in result['calls']))
        self.assertFalse(result['inspecsafe_used'])
        self.assertFalse(result['synthetic_gate_used'])
        processor_kwargs = {'revision': module.REVISION, 'local_files_only': True,
                            'trust_remote_code': False, 'min_pixels': 200704, 'max_pixels': 1003520}
        self.runtime.processor_factory.from_pretrained.assert_called_once_with(module.MODEL_ID, **processor_kwargs)
        self.runtime.model_factory.from_pretrained.assert_called_once_with(module.MODEL_ID,
            revision=module.REVISION, local_files_only=True, trust_remote_code=False,
            torch_dtype='torch.float16', device_map={'': 'cuda:0'}, attn_implementation='sdpa')
        self.assertEqual(smoke.PLAN_SHA256, 'aa4fcff85d670d844025a540d85f10514919c60f6709de8be8f6be0922fd63fb')


if __name__ == '__main__':
    unittest.main()
