"""Fake-only Qwen2.5 contracts. No torch/Transformers imports or network."""

import builtins
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image, __version__ as PILLOW_VERSION

from safeshift.protocol.schema import Classification, strict_json
from safeshift.runners.contracts import (
    ErrorCode, GenerationFailure, ModelIdentity, ParseStatus, Request, RunContext,
    SpatialKind, Task, execute_call,
)
from safeshift.runners import qwen2_5_vl as module
from safeshift.runners.qwen2_5_vl import (
    BACKEND, ENVELOPE_VERSION, FAILURE_ENVELOPE_VERSION, MODEL_ID, REVISION,
    Qwen2_5Backend, Qwen2_5VLAdapter, Qwen2_5VLRunner,
)
from safeshift.runners.storage import FileRawStore

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = {'torch': 'fake-torch', 'transformers': 'fake-transformers', 'pillow': PILLOW_VERSION,
            'qwen-vl-utils': '0.0.8', 'accelerate': 'fake-accelerate'}


def context(**changes):
    return replace(RunContext(
        run_id='offline-qwen2-5-contract', call_id='a', decoding={},
        preprocessing=deepcopy(module.PREPROCESSING), precision='FP16', quantization='NONE',
        device={'placement': 'cuda:0'}, software_versions=deepcopy(VERSIONS),
        git_commit_sha='92545ff4071c7055f7003995379b4af8993b6840',
        command='python -m unittest tests.test_qwen2_5_runner -v', source_kind='handcrafted_dummy',
    ), **changes)


def image_bytes(mode='RGB'):
    with BytesIO() as stream:
        Image.new(mode, (28, 56), 63).save(stream, format='PNG')
        return stream.getvalue()


def request(**changes):
    return replace(Request(Task.CLASSIFICATION, 'tiny-synthetic', 'memory-image', image_bytes(),
                           'caller-prompt', '  Caller text: tiếng Việt\n'), **changes)


class Tensor:
    def __init__(self, data, device='cuda:0', dtype='torch.float16'):
        self.data = deepcopy(data)
        self.device = device
        self.dtype = dtype

    def tolist(self):
        return deepcopy(self.data)


class Inputs(dict):
    def to(self, device):
        for tensor in self.values():
            tensor.device = device
        return self


class Processor:
    def __init__(self):
        self.image_processor = SimpleNamespace(min_pixels=200704, max_pixels=1003520)
        self.template_calls = []
        self.calls = []
        self.decodes = []
        self.rows = [[11, 22, 33]]
        self.grid = [[1, 2, 3]]
        self.extra_inputs = {}
        self.text = '{"safety_level":"Level04"}'

    def apply_chat_template(self, messages, **kwargs):
        image = messages[0]['content'][0]['image']
        self.template_calls.append({
            'roles': [m['role'] for m in messages], 'content_count': len(messages[0]['content']),
            'prompt': messages[0]['content'][1]['text'], 'mode': image.mode, 'size': image.size,
            'pixel': image.getpixel((0, 0)), 'image': image,
            'image_keys': set(messages[0]['content'][0]), 'kwargs': kwargs,
        })
        return '<official>' + messages[0]['content'][1]['text']

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return Inputs(input_ids=Tensor(self.rows), attention_mask=Tensor([[1, 1, 1]]),
                      pixel_values=Tensor([[0.1]], dtype='torch.float32'),
                      image_grid_thw=Tensor(self.grid), **self.extra_inputs)

    def batch_decode(self, ids, **kwargs):
        self.decodes.append((deepcopy(ids), kwargs))
        return [self.text if kwargs['skip_special_tokens'] else '<control>' + self.text + '<end>']


class Config:
    def __init__(self):
        self.num_return_sequences = 1
        self.num_beams = 1
        self.return_dict_in_generate = False
        self.output_scores = False
        self.output_logits = False
        self.output_attentions = False
        self.output_hidden_states = False
        self.cache_implementation = None
        self.do_sample = True
        self.temperature = 0.7
        self.max_new_tokens = None

    def to_dict(self):
        return deepcopy(vars(self))


class Model:
    def __init__(self, runtime):
        self.runtime = runtime
        self.device = 'cuda:0'
        self.dtype = 'torch.float16'
        self.hf_device_map = {'': 'cuda:0'}
        self.config = SimpleNamespace(cache_implementation=None, _attn_implementation='sdpa')
        self.model = SimpleNamespace()  # Qwen2.5 reviewed layout differs from Qwen3.
        self.rope_deltas = None
        self.generation_config = Config()
        self.params = [Tensor([1])]
        self.bufs = [Tensor([1], dtype='torch.float32')]
        self.eval_count = 0
        self.calls = []
        self.failure = None
        self.continuation = [701, 702]
        self.returned_rows = None

    def parameters(self):
        return iter(self.params)

    def buffers(self):
        return iter(self.bufs)

    def eval(self):
        self.eval_count += 1
        return self

    def generate(self, **kwargs):
        assert self.runtime.inference_active
        assert self.rope_deltas is None
        assert getattr(self, '_cache', None) is None
        assert 'past_key_values' not in kwargs
        self.calls.append(kwargs)
        self.rope_deltas = Tensor([999])
        self._cache = object()
        kwargs['generation_config'].temperature = 9  # Only the call-local copy may mutate.
        if self.failure:
            raise self.failure
        rows = self.returned_rows
        if rows is None:
            rows = [kwargs['input_ids'].tolist()[0] + self.continuation]
        return Tensor(rows)


class Runtime:
    def __init__(self):
        self.inference_active = False
        self.processor = Processor()
        self.model = Model(self)
        self.processor_factory = SimpleNamespace(from_pretrained=Mock(return_value=self.processor))
        self.model_factory = SimpleNamespace(from_pretrained=Mock(return_value=self.model))
        self.vision_calls = []
        self.vision = Mock(side_effect=self.process_vision_info)
        self.torch = SimpleNamespace(float16='torch.float16', inference_mode=self.inference_mode)
        self.backend = Qwen2_5Backend(self.torch, self.processor_factory, self.model_factory,
                                    self.vision, deepcopy(VERSIONS))
        self.factory = Mock(return_value=self.backend)

    def process_vision_info(self, messages):
        self.vision_calls.append(messages)
        return [messages[0]['content'][0]['image'].copy()], None

    @contextmanager
    def inference_mode(self):
        self.inference_active = True
        try:
            yield
        finally:
            self.inference_active = False


class Qwen2_5RunnerTests(unittest.TestCase):
    def setUp(self):
        for target in ('socket.socket.connect', 'socket.socket.connect_ex', 'socket.create_connection'):
            guard = patch(target, side_effect=AssertionError('network forbidden'))
            guard.start()
            self.addCleanup(guard.stop)
        original_import = builtins.__import__

        def offline_import(name, *args, **kwargs):
            if name.split('.')[0] in {'torch', 'transformers', 'accelerate', 'qwen_vl_utils', 'huggingface_hub'}:
                raise ImportError('real ML library forbidden in offline test')
            return original_import(name, *args, **kwargs)
        guard = patch('builtins.__import__', side_effect=offline_import)
        guard.start()
        self.addCleanup(guard.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.store = FileRawStore(self.repo)
        self.runtime = Runtime()
        self.runner = Qwen2_5VLRunner(backend_factory=self.runtime.factory)
        self.adapter = Qwen2_5VLAdapter()

    def execute(self, *, ctx=None, req=None, adapter=None, store=None):
        return execute_call(self.runner, adapter or self.adapter, store or self.store,
                            req or request(), ctx or context())

    def generate(self, ctx=None, req=None):
        ctx = ctx or context()
        self.runner.initialize(ctx)
        self.runner.load(ctx)
        return self.runner.generate_raw(self.runner.prepare_input(req or request(), ctx), ctx)

    def raw(self, result):
        return (self.repo / result.raw_output.path).read_bytes()

    def failure_evidence(self):
        with patch.object(self.adapter, 'adapt') as adapt:
            result = self.execute()
            adapt.assert_not_called()
        self.assertEqual(result.error.code, ErrorCode.GENERATION_FAILURE)
        self.assertIsNotNone(result.raw_output)
        self.assertIsNone(result.canonical)
        obj = strict_json(self.raw(result))
        self.assertEqual(obj['schema_version'], FAILURE_ENVELOPE_VERSION)
        self.assertEqual(obj['model_revision'], REVISION)
        self.assertEqual(obj['model_id'], MODEL_ID)
        self.assertNotIn('private-secret', self.raw(result).decode())
        return obj

    def test_exact_model_identity(self):
        self.assertEqual(self.runner.identity.model_id, 'Qwen/Qwen2.5-VL-3B-Instruct')

    def test_exact_revision_matches_provenance(self):
        p = strict_json((ROOT / 'configs/pre_freeze/local_model_provenance.d9.json').read_bytes())
        m = next(m for m in p['models'] if m['key'] == 'qwen2_5_vl_3b_instruct')
        self.assertEqual(self.runner.identity.immutable_revision, '66285546d2b821cf421d4f5eb2576359d3770cd3')
        self.assertEqual(m['immutable_revision'], REVISION)

    def test_provenance_evidence_path(self):
        self.assertEqual(self.runner.identity.revision_evidence,
                         'configs/pre_freeze/local_model_provenance.d9.json#qwen2_5_vl_3b_instruct')

    def test_constructor_is_lazy_and_backend_injectable(self):
        self.runtime.factory.assert_not_called()
        self.assertIsNone(self.execute().error)
        self.runtime.factory.assert_called_once_with()

    def test_module_import_without_ml_libraries(self):
        code = '''import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'torch', 'transformers', 'accelerate', 'qwen_vl_utils', 'PIL'}:
        raise AssertionError('eager import: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from safeshift.runners.qwen2_5_vl import Qwen2_5VLRunner
Qwen2_5VLRunner()
'''
        result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_initialize_idempotent(self):
        self.runner.initialize(context())
        self.runner.initialize(context(call_id='b'))
        self.runtime.factory.assert_called_once()
        self.runtime.model_factory.from_pretrained.assert_not_called()

    def test_load_idempotent_across_calls(self):
        self.assertIsNone(self.execute().error)
        self.assertIsNone(self.execute(ctx=context(call_id='b')).error)
        self.runtime.processor_factory.from_pretrained.assert_called_once()
        self.runtime.model_factory.from_pretrained.assert_called_once()
        self.assertEqual(self.runtime.model.eval_count, 1)

    def test_wrong_precision_rejected_before_backend_creation(self):
        for precision in ('BF16', 'FP32', 'auto', 'PENDING'):
            with self.subTest(precision=precision), self.assertRaises(module.Qwen2_5InitializeDiagnosticFailure) as raised:
                self.runner.initialize(context(precision=precision))
            self.assertIsInstance(raised.exception.__cause__, ValueError)
        self.runtime.factory.assert_not_called()

    def test_quantization_rejected(self):
        for q in ('4bit', '8bit', 'AWQ', 'GPTQ', None):
            with self.subTest(q=q), self.assertRaises(module.Qwen2_5InitializeDiagnosticFailure) as raised:
                self.runner.initialize(context(quantization=q))
            self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_offload_auto_cpu_and_multidevice_requests_rejected(self):
        for device in ({}, {'placement': 'auto'}, {'placement': 'cpu'}, {'placement': 'disk'},
                       {'placement': 'cuda:1'}, {'placement': 'cuda:0', 'offload': True},
                       {'placement': {'': 'cuda:0', 'layer': 'cpu'}}):
            with self.subTest(device=device), self.assertRaises(module.Qwen2_5InitializeDiagnosticFailure) as raised:
                self.runner.initialize(context(device=device))
            self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_software_version_mismatch_rejected(self):
        for name in VERSIONS:
            with self.subTest(name=name):
                result = self.execute(ctx=context(software_versions={**VERSIONS, name: 'wrong'}))
                self.assertEqual(result.error.code, ErrorCode.INITIALIZATION_FAILURE)
                self.assertIsNone(self.runner._backend)

    def test_backend_must_report_all_loader_libraries(self):
        del self.runtime.backend.software_versions['accelerate']
        self.assertEqual(self.execute().error.code, ErrorCode.INITIALIZATION_FAILURE)

    def test_local_files_only_on_both_factories(self):
        self.generate()
        for factory in (self.runtime.processor_factory, self.runtime.model_factory):
            self.assertIs(factory.from_pretrained.call_args.kwargs['local_files_only'], True)

    def test_trust_remote_code_false_on_both_factories(self):
        self.generate()
        for factory in (self.runtime.processor_factory, self.runtime.model_factory):
            self.assertIs(factory.from_pretrained.call_args.kwargs['trust_remote_code'], False)

    def test_model_and_processor_exact_pin(self):
        self.generate()
        for factory in (self.runtime.processor_factory, self.runtime.model_factory):
            self.assertEqual(factory.from_pretrained.call_args.args, (MODEL_ID,))
            self.assertEqual(factory.from_pretrained.call_args.kwargs['revision'], REVISION)

    def test_native_backend_wiring_uses_mock_imports_only(self):
        previous = builtins.__import__
        modules = {
            'torch': SimpleNamespace(**vars(self.runtime.torch), __version__=VERSIONS['torch']),
            'transformers': SimpleNamespace(__version__=VERSIONS['transformers'],
                                           AutoProcessor=self.runtime.processor_factory,
                                           Qwen2_5_VLForConditionalGeneration=self.runtime.model_factory),
            'accelerate': SimpleNamespace(__version__=VERSIONS['accelerate']),
            'qwen_vl_utils': SimpleNamespace(process_vision_info=self.runtime.vision),
        }
        def importer(name, *args, **kwargs):
            return modules[name] if name in modules else previous(name, *args, **kwargs)
        self.runner = Qwen2_5VLRunner()
        with patch('builtins.__import__', side_effect=importer), \
                patch('importlib.metadata.version', return_value='0.0.8') as version:
            self.assertIsNone(self.execute().error)
            version.assert_called_once_with('qwen-vl-utils')

    def test_fp16_explicit_single_device_no_flash_requirement(self):
        self.generate()
        kwargs = self.runtime.model_factory.from_pretrained.call_args.kwargs
        self.assertEqual(kwargs['torch_dtype'], 'torch.float16')
        self.assertEqual(kwargs['device_map'], {'': 'cuda:0'})
        self.assertEqual(kwargs['attn_implementation'], 'sdpa')
        self.assertNotIn('quantization_config', kwargs)

    def test_failed_model_load_publishes_nothing_and_retry_is_explicit(self):
        self.runtime.model_factory.from_pretrained.side_effect = [RuntimeError('private-secret'), self.runtime.model]
        first = self.execute()
        self.assertEqual(first.error.code, ErrorCode.MODEL_LOAD_FAILURE)
        self.assertIsNone(self.runner._resources)
        self.assertIsNone(first.raw_output)
        self.assertEqual(self.runtime.model_factory.from_pretrained.call_count, 1)
        self.assertIsNone(self.execute(ctx=context(call_id='b')).error)
        self.assertEqual(self.runtime.processor_factory.from_pretrained.call_count, 2)

    def test_processor_failure_never_attempts_model(self):
        self.runtime.processor_factory.from_pretrained.side_effect = RuntimeError()
        self.assertEqual(self.execute().error.code, ErrorCode.MODEL_LOAD_FAILURE)
        self.assertIsNone(self.runner._resources)
        self.runtime.model_factory.from_pretrained.assert_not_called()

    def test_failed_initialize_retries_without_cached_error(self):
        self.runtime.factory.side_effect = [ImportError(), self.runtime.backend]
        self.assertEqual(self.execute().error.code, ErrorCode.INITIALIZATION_FAILURE)
        self.assertIsNone(self.runner._condition)
        self.assertIsNone(self.execute(ctx=context(call_id='b')).error)

    def test_postload_failure_does_not_publish_resources(self):
        self.runtime.model.hf_device_map['layer'] = 'cpu'
        self.assertEqual(self.execute().error.code, ErrorCode.MODEL_LOAD_FAILURE)
        self.assertIsNone(self.runner._resources)
        del self.runtime.model.hf_device_map['layer']
        self.assertIsNone(self.execute(ctx=context(call_id='b')).error)

    def test_actual_parameter_buffer_dtype_and_device_enforced(self):
        changes = [('dtype', 'torch.bfloat16'), ('device', 'cpu')]
        for field, value in changes:
            with self.subTest(field=field):
                self.runtime.model.params[0] = Tensor([1])
                setattr(self.runtime.model.params[0], field, value)
                self.assertEqual(self.execute().error.code, ErrorCode.MODEL_LOAD_FAILURE)
                self.assertIsNone(self.runner._resources)
        self.runtime.model.params[0] = Tensor([1])
        self.runtime.model.bufs[0].device = 'cpu'
        self.assertEqual(self.execute().error.code, ErrorCode.MODEL_LOAD_FAILURE)

    def test_quantized_loaded_model_rejected(self):
        self.runtime.model.is_quantized = True
        self.assertEqual(self.execute().error.code, ErrorCode.MODEL_LOAD_FAILURE)

    def test_unreviewed_qwen3_state_layout_rejected(self):
        del self.runtime.model.rope_deltas
        self.runtime.model.model.rope_deltas = None
        self.assertEqual(self.execute().error.code, ErrorCode.MODEL_LOAD_FAILURE)

    def test_still_image_rgb_conversion(self):
        self.generate(req=request(input_bytes=image_bytes('L')))
        call = self.runtime.processor.template_calls[0]
        self.assertEqual(call['mode'], 'RGB')
        self.assertEqual(call['pixel'], (63, 63, 63))

    def test_malformed_image_rejected(self):
        for value in (b'', b'not-an-image', b'https://example.invalid/image.png'):
            with self.subTest(value=value):
                self.assertEqual(self.execute(req=request(input_bytes=value)).error.code,
                                 ErrorCode.PREPROCESSING_FAILURE)
        self.assertEqual(self.runtime.model.calls, [])

    def test_multiframe_image_rejected(self):
        stream = BytesIO()
        Image.new('RGB', (2, 2), 'red').save(stream, format='GIF', save_all=True,
                                            append_images=[Image.new('RGB', (2, 2), 'blue')])
        self.assertEqual(self.execute(req=request(input_bytes=stream.getvalue())).error.code,
                         ErrorCode.PREPROCESSING_FAILURE)
        self.runtime.vision.assert_not_called()

    def test_prompt_preserved_exactly(self):
        prompt = ' \n{"test": "Tiếng Việt"}\n Do not add instructions.  '
        self.generate(req=request(prompt=prompt))
        self.assertEqual(self.runtime.processor.template_calls[0]['prompt'], prompt)

    def test_no_system_history_or_extra_message_content(self):
        self.generate()
        call = self.runtime.processor.template_calls[0]
        self.assertEqual(call['roles'], ['user'])
        self.assertEqual(call['content_count'], 2)
        self.assertEqual(call['image_keys'], {'type', 'image'})

    def test_official_two_stage_qwen2_5_preprocessing(self):
        self.generate()
        self.assertEqual(self.runtime.processor.template_calls[0]['kwargs'],
                         {'tokenize': False, 'add_generation_prompt': True})
        self.runtime.vision.assert_called_once()
        args = self.runtime.processor.calls[0]
        self.assertEqual(args['text'], ['<official>' + request().prompt])
        self.assertEqual(len(args['images']), 1)
        self.assertIsInstance(args['images'][0], Image.Image)
        self.assertIsNone(args['videos'])
        self.assertEqual(args['padding'], True)
        self.assertEqual(args['return_tensors'], 'pt')
        self.assertEqual(set(args), {'text', 'images', 'videos', 'padding', 'return_tensors'})

    def test_no_manual_resize_or_exif_transpose(self):
        req = request()
        with patch.object(Image.Image, 'resize', side_effect=AssertionError('manual resize forbidden')), \
                patch('PIL.ImageOps.exif_transpose', side_effect=AssertionError('EXIF transform forbidden')):
            self.generate(req=req)
        self.assertEqual(self.runtime.processor.template_calls[0]['size'], (28, 56))

    def test_no_pixel_overrides(self):
        for p in ({'min_pixels': 1}, {'mode': 'official_processor', 'max_pixels': 4096}):
            with self.assertRaises(module.Qwen2_5InitializeDiagnosticFailure) as raised:
                self.runner.initialize(context(preprocessing=p))
            self.assertIsInstance(raised.exception.__cause__, ValueError)
        self.runtime.factory.assert_not_called()

    def test_vision_utils_cannot_return_video_or_multiple_images(self):
        image = Image.new('RGB', (2, 2))
        self.addCleanup(image.close)
        for value in (([image, image], None), ([image], []), (None, None), (['url'], None)):
            with self.subTest(value=value):
                self.runtime.vision.side_effect = None
                self.runtime.vision.return_value = value
                self.assertEqual(self.execute().error.code, ErrorCode.PREPROCESSING_FAILURE)
        self.assertEqual(self.runtime.model.calls, [])

    def test_image_decode_is_memory_only(self):
        req = request()
        original = Image.open
        def image_open(source, *args, **kwargs):
            self.assertIsInstance(source, BytesIO)
            return original(source, *args, **kwargs)
        with patch.object(Image, 'open', side_effect=image_open):
            self.generate(req=req)

    def test_past_key_values_and_extra_processor_fields_blocked(self):
        for key in ('past_key_values', 'cache_position', 'pixel_values_videos', 'generation_config'):
            self.runtime.processor.extra_inputs = {key: Tensor([1])}
            self.assertEqual(self.execute().error.code, ErrorCode.PREPROCESSING_FAILURE)
        self.assertEqual(self.runtime.model.calls, [])

    def test_changed_execution_condition_blocked(self):
        self.generate()
        changes = [dict(decoding={'max_new_tokens': 2}), dict(software_versions={**VERSIONS, 'driver': 'new'}),
                   dict(preprocessing={}), dict(precision='BF16'), dict(device={'placement': 'auto'})]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(module.Qwen2_5InitializeDiagnosticFailure) as raised:
                self.runner.initialize(context(**change))
            self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_identity_cannot_be_reassigned(self):
        self.runner.identity = ModelIdentity('synthetic/other')
        with self.assertRaises(module.Qwen2_5InitializeDiagnosticFailure) as raised:
            self.runner.initialize(context())
        self.assertIsInstance(raised.exception.__cause__, ValueError)
        self.runtime.factory.assert_not_called()

    def test_decoding_values_preserved_without_invented_defaults(self):
        values = dict(temperature=0.6, do_sample=True, top_p=0.8, top_k=0,
                      max_new_tokens=20, repetition_penalty=1.1)
        obj = strict_json(self.generate(context(decoding=values)))
        self.assertEqual(obj['generation_kwargs'], values)
        call = self.runtime.model.calls[0]
        self.assertEqual({k: call[k] for k in values}, values)
        self.assertEqual(obj['effective_generation_config']['temperature'], 0.6)

    def test_empty_decoding_uses_isolated_checkpoint_snapshot(self):
        raw = strict_json(self.generate())
        self.assertEqual(raw['generation_kwargs'], {})
        self.assertEqual(set(self.runtime.model.calls[0]), module.INPUT_KEYS | {'generation_config'})
        self.assertEqual(raw['effective_generation_config']['temperature'], 0.7)
        self.assertEqual(self.runtime.model.generation_config.temperature, 0.7)
        self.assertEqual(self.runner._resources[2].temperature, 0.7)

    def test_decoding_whitelist_types_and_ranges(self):
        cases = [{'seed': 1}, {'past_key_values': []}, {'temperature': 0}, {'temperature': float('inf')},
                 {'temperature': float('nan')}, {'temperature': True}, {'top_p': 1.1}, {'top_p': 0},
                 {'top_k': -1}, {'top_k': True}, {'max_new_tokens': 0}, {'max_new_tokens': 1.5},
                 {'do_sample': 'false'}, {'repetition_penalty': -1}, {'num_return_sequences': 2}]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(module.Qwen2_5InitializeDiagnosticFailure) as raised:
                self.runner.initialize(context(decoding=values))
            self.assertIsInstance(raised.exception.__cause__, ValueError)
        self.runtime.factory.assert_not_called()

    def test_unapplied_seed_rejected_even_on_direct_generation(self):
        self.generate()
        with self.assertRaises(module.Qwen2_5InitializeDiagnosticFailure) as raised:
            self.runner.initialize(context(seed=7))
        self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_one_generated_row_required_with_observable_partial(self):
        for rows in ([], [[11, 22, 33], [11, 22, 33]], [11, 22, 33]):
            with self.subTest(rows=rows):
                self.runtime.model.returned_rows = rows
                with self.assertRaises(GenerationFailure) as raised:
                    self.generate()
                self.assertEqual(strict_json(raised.exception.partial_raw)['observed_generated_ids'], rows)

    def test_input_token_rows_validated(self):
        for rows in ([], [[]], [[True]], [[-1]], [[1.5]], [[1], [2]], [1, 2]):
            with self.subTest(rows=rows):
                self.runtime.processor.rows = rows
                self.assertEqual(self.execute().error.code, ErrorCode.PREPROCESSING_FAILURE)

    def test_one_still_grid_required(self):
        for grid in ([[2, 3, 4]], [[1, 2, 3], [1, 2, 3]], [[True, 2, 3]], [[1, 0, 3]]):
            self.runtime.processor.grid = grid
            self.assertEqual(self.execute().error.code, ErrorCode.PREPROCESSING_FAILURE)

    def test_prefix_validation_before_decode(self):
        self.runtime.model.returned_rows = [[11, 88, 33, 701]]
        obj = self.failure_evidence()
        self.assertEqual(obj['generated_ids_full'], [11, 88, 33, 701])
        self.assertEqual(obj['post_generation_stage'], 'PREFIX_VALIDATION')
        self.assertEqual(self.runtime.processor.decodes, [])

    def test_continuation_trim_and_prefix_record(self):
        obj = strict_json(self.generate())
        self.assertEqual(obj['input_token_count'], 3)
        self.assertEqual(obj['input_token_ids'], [11, 22, 33])
        self.assertEqual(obj['generated_ids_full'], [11, 22, 33, 701, 702])
        self.assertEqual(obj['continuation_ids'], [701, 702])

    def test_empty_continuation_is_preserved(self):
        self.runtime.model.continuation = []
        self.runtime.processor.rows = [[9]]
        self.assertEqual(strict_json(self.generate())['continuation_ids'], [])

    def test_both_decodes_preserved_without_whitespace_cleanup(self):
        text = ' \n{"safety_level":"Level01"}\n '
        self.runtime.processor.text = text
        obj = strict_json(self.generate())
        self.assertEqual(obj['decoded_for_parser'], text)
        self.assertEqual(obj['decoded_with_special_tokens'], '<control>' + text + '<end>')
        self.assertEqual(self.runtime.processor.decodes, [
            ([[701, 702]], {'skip_special_tokens': False, 'clean_up_tokenization_spaces': False}),
            ([[701, 702]], {'skip_special_tokens': True, 'clean_up_tokenization_spaces': False})])

    def test_raw_envelope_strict_utf8_version_and_identity(self):
        raw = self.generate()
        self.assertIs(type(raw), bytes)
        obj = strict_json(raw.decode('utf-8'))
        self.assertEqual(obj['schema_version'], ENVELOPE_VERSION)
        self.assertEqual(obj['backend'], BACKEND)
        self.assertEqual(obj['model_id'], MODEL_ID)
        self.assertEqual(obj['model_revision'], REVISION)
        self.assertEqual(raw, module._json_bytes(obj))

    def test_runtime_and_generation_metadata_present(self):
        obj = strict_json(self.generate())
        runtime = obj['runtime']
        self.assertEqual(runtime['software_versions'], VERSIONS)
        self.assertEqual(runtime['runner_version'], self.runner.version)
        self.assertEqual(runtime['model_dtype'], 'torch.float16')
        self.assertEqual(runtime['input_device'], 'cuda:0')
        self.assertEqual(runtime['model_device'], 'cuda:0')
        self.assertEqual(runtime['device_map'], {'': 'cuda:0'})
        self.assertIn('effective_generation_config', obj)

    def test_classification_success_calls_existing_parser_with_parser_text_only(self):
        with patch.object(module, 'parse_text', wraps=module.parse_text) as parser:
            result = self.execute()
        self.assertEqual(result.parse_status, ParseStatus.SUCCESS)
        self.assertIsInstance(result.canonical, Classification)
        parser.assert_called_once_with(self.runtime.processor.text, 'classification')

    def test_invalid_classification_returns_invalid_no_correction(self):
        self.runtime.processor.text = '{"safety_level":"Level99"}'
        result = self.execute()
        self.assertEqual(result.parse_status, ParseStatus.INVALID)
        self.assertIsNone(result.canonical)
        self.assertEqual(strict_json(self.raw(result))['decoded_for_parser'], self.runtime.processor.text)

    def test_grounding_always_unsupported_with_no_point_to_box(self):
        for text in ('{"bbox":[0,0,1,1]}', '<point>(300,400)</point>', '{"safety_level":"Level01"}'):
            with self.subTest(text=text), patch.object(module, 'parse_text') as parser:
                self.runtime.processor.text = text
                result = self.adapter.adapt(self.generate(), Task.GROUNDING)
                parser.assert_not_called()
                self.assertEqual(result.parse_status, ParseStatus.UNSUPPORTED)
                self.assertEqual(result.spatial_kind, SpatialKind.NONE)
                self.assertIsNone(result.value)
                self.assertEqual(result.native_evidence, {
                    'interface_status': 'DOCUMENTED_BOX_AND_POINT_PENDING_SYNTHETIC_GATE',
                    'd5_box_qualification': 'NOT_YET_QUALIFIED',
                    'reason': 'COORDINATE_OUTPUT_ADAPTER_NOT_YET_FROZEN'})

    def test_raw_store_writes_before_adapter(self):
        wrapped = self.adapter.adapt
        def adapt(raw, task):
            files = list(self.repo.rglob('response.raw'))
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].read_bytes(), raw)
            metadata = strict_json(files[0].with_name('metadata.json').read_bytes())
            self.assertEqual(metadata['parse_status'], 'NOT_ATTEMPTED')
            return wrapped(raw, task)
        with patch.object(self.adapter, 'adapt', side_effect=adapt):
            self.assertIsNone(self.execute().error)

    def test_storage_failure_blocks_parser(self):
        with patch.object(self.store, 'preserve', side_effect=OSError()), patch.object(self.adapter, 'adapt') as adapt:
            self.assertEqual(self.execute().error.code, ErrorCode.RAW_PRESERVATION_FAILURE)
            adapt.assert_not_called()

    def test_postgenerate_decode_failure_preserves_tokens_and_first_decode(self):
        self.runtime.processor.batch_decode = Mock(side_effect=[['<answer>'], RuntimeError('private-secret')])
        obj = self.failure_evidence()
        self.assertEqual(obj['continuation_ids'], [701, 702])
        self.assertEqual(obj['decoded_with_special_tokens'], '<answer>')
        self.assertNotIn('decoded_for_parser', obj)

    def test_generate_failure_before_output_has_no_partial_raw(self):
        self.runtime.model.failure = RuntimeError('private-secret')
        with self.assertRaises(GenerationFailure) as raised:
            self.generate()
        self.assertIsNone(raised.exception.partial_raw)
        self.assertEqual(str(raised.exception), 'generation failed')
        self.assertIsNone(self.runtime.model.rope_deltas)
        self.assertIsNone(self.runtime.model._cache)

    def test_tolist_failure_does_not_fabricate_observation(self):
        self.runtime.model.generate = Mock(return_value=SimpleNamespace(tolist=Mock(side_effect=RuntimeError())))
        with self.assertRaises(GenerationFailure) as raised:
            self.generate()
        self.assertIsNone(raised.exception.partial_raw)

    def test_malformed_decode_structure_preserves_observed_output(self):
        self.runtime.processor.batch_decode = Mock(return_value=[7, 'text'])
        obj = self.failure_evidence()
        self.assertEqual(obj['observed_special_decode'], [7, 'text'])

    def test_unserializable_decode_keeps_prior_token_evidence(self):
        self.runtime.processor.batch_decode = Mock(return_value=[object()])
        obj = self.failure_evidence()
        self.assertEqual(obj['continuation_ids'], [701, 702])
        self.assertNotIn('observed_special_decode', obj)

    def test_success_serialization_failure_preserves_all_observations(self):
        original = module._json_bytes
        def fail(value):
            if isinstance(value, dict) and value.get('schema_version') == ENVELOPE_VERSION:
                raise ValueError('private-secret')
            return original(value)
        with patch.object(module, '_json_bytes', side_effect=fail):
            obj = self.failure_evidence()
        self.assertEqual(obj['decoded_for_parser'], self.runtime.processor.text)

    def test_lone_surrogate_is_preserved_in_failure_json_escape(self):
        self.runtime.processor.text = '\ud800'
        obj = self.failure_evidence()
        self.assertEqual(obj['decoded_for_parser'], '\ud800')

    def test_sequential_calls_independent_and_no_output_carryover(self):
        first = self.generate(req=request(prompt='first request'))
        self.runtime.processor.text = '{"safety_level":"Level01"}'
        second = self.generate(context(call_id='b'), request(prompt='second request'))
        self.assertNotEqual(first, second)
        self.assertEqual([c['prompt'] for c in self.runtime.processor.template_calls],
                         ['first request', 'second request'])
        one, two = self.runtime.model.calls
        self.assertIsNot(one['input_ids'], two['input_ids'])
        self.assertIsNot(one['generation_config'], two['generation_config'])
        self.assertNotIn('past_key_values', two)
        self.assertIsNone(self.runtime.model.rope_deltas)
        self.assertIsNone(self.runtime.model._cache)
        self.assertEqual(self.runtime.model.generation_config.temperature, 0.7)
        self.assertEqual(set(vars(self.runner)), {'_backend_factory', '_backend', '_condition', '_resources'})

    def test_failed_generation_does_not_contaminate_next_call(self):
        self.runtime.model.failure = RuntimeError()
        self.assertEqual(self.execute().error.code, ErrorCode.GENERATION_FAILURE)
        self.runtime.model.failure = None
        self.assertIsNone(self.execute(ctx=context(call_id='b')).error)

    def test_state_cleared_after_decode_failure(self):
        self.runtime.processor.batch_decode = Mock(side_effect=RuntimeError())
        self.failure_evidence()
        self.assertIsNone(self.runtime.model.rope_deltas)
        self.assertIsNone(self.runtime.model._cache)

    def test_prepared_tokens_cannot_be_mutated_between_prepare_generate(self):
        ctx = context()
        self.runner.initialize(ctx)
        self.runner.load(ctx)
        prepared = self.runner.prepare_input(request(), ctx)
        prepared.inputs['input_ids'].data[0][0] = 99
        with self.assertRaises(ValueError):
            self.runner.generate_raw(prepared, ctx)
        self.assertEqual(self.runtime.model.calls, [])

    def test_extra_outputs_beams_and_persistent_cache_rejected(self):
        for field, value in [('num_return_sequences', 2), ('num_beams', 2), ('return_dict_in_generate', True),
                             ('output_scores', True), ('output_logits', True), ('cache_implementation', 'static')]:
            with self.subTest(field=field):
                self.runtime.model.generation_config = Config()
                setattr(self.runtime.model.generation_config, field, value)
                self.assertEqual(self.execute().error.code, ErrorCode.MODEL_LOAD_FAILURE)
                self.assertIsNone(self.runner._resources)

    def test_adapter_rejects_wrong_identity_prefix_and_runtime(self):
        valid = strict_json(self.generate())
        cases = [('model_revision', 'main'), ('model_id', 'Qwen/Qwen3-VL-8B-Instruct'),
                 ('schema_version', 'unknown'), ('input_token_count', True), ('input_token_ids', [1]),
                 ('continuation_ids', [0]), ('runtime', {}), ('generated_ids_full', [True]),
                 ('decoded_for_parser', []), ('effective_generation_config', [])]
        for key, value in cases:
            obj = {**valid, key: value}
            with self.subTest(key=key), patch.object(module, 'parse_text') as parser:
                with self.assertRaises(ValueError):
                    self.adapter.adapt(module._json_bytes(obj), Task.CLASSIFICATION)
                parser.assert_not_called()

    def test_adapter_rejects_nonutf8_duplicates_nonfinite_and_extra_fields(self):
        raw = self.generate()
        for bad in (b'\xff', b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}',
                    raw[:-1] + b',"extra":1}'):
            with self.subTest(bad=bad[:20]), self.assertRaises((ValueError, UnicodeError)):
                self.adapter.adapt(bad, Task.CLASSIFICATION)
        with self.assertRaises(TypeError):
            self.adapter.adapt(raw.decode(), Task.CLASSIFICATION)

    def test_failure_envelope_cannot_be_semantically_parsed(self):
        self.runtime.model.returned_rows = [[2]]
        with self.assertRaises(GenerationFailure) as raised:
            self.generate()
        with self.assertRaises(ValueError):
            self.adapter.adapt(raised.exception.partial_raw, Task.GROUNDING)

    def test_lifecycle_requires_initialize_and_load(self):
        with self.assertRaises(RuntimeError):
            self.runner.load(context())
        with self.assertRaises(RuntimeError):
            self.runner.prepare_input(request(), context())


if __name__ == '__main__':
    unittest.main()
