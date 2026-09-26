"""Real CPU tensor arithmetic and local contract fakes; no model/runtime imports."""

import ast
from contextlib import ExitStack
import hashlib
import importlib
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

import torch

from safeshift.runners import moondream_precision as bridge

ROOT = Path(__file__).resolve().parents[1]
PLAN = 'configs/pre_freeze/moondream_precision_bridge.v1.json'


def synthetic_crops(tiling=(1, 1)):
    # Handcrafted repeating normalized-like BF16 values, no image or source import.
    n = (1 + tiling[0] * tiling[1]) * 3 * 378 * 378
    values = torch.linspace(-1, 1, 256, dtype=torch.float32, device='cpu').to(torch.bfloat16)
    return values.repeat((n + 255) // 256)[:n].reshape(-1, 3, 378, 378), tiling


def numerical_diagnostic():
    before, tiling = synthetic_crops()
    after, _ = bridge.post_normalization_fp16_bridge((before, tiling))
    return {
        'scope': 'SYNTHETIC_CPU_IMPLEMENTATION_DIAGNOSTIC_NOT_RESEARCH_METRIC',
        'fixture': 'float32 linspace(-1,1,256) -> BF16; repeat to (2,3,378,378)',
        'input_dtype': str(before.dtype), 'output_dtype': str(after.dtype),
        'input_device': str(before.device), 'output_device': str(after.device),
        'shape': list(after.shape), 'shape_unchanged': before.shape == after.shape,
        'input_finite': bool(torch.isfinite(before).all()),
        'output_finite': bool(torch.isfinite(after).all()),
        'max_absolute_difference_float32': (before.float() - after.float()).abs().max().item(),
        'torch_version': str(torch.__version__), 'cuda_build': torch.version.cuda,
        'python_version': sys.version.split()[0], 'seed': None,
    }


class PrecisionBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads)

    def test_bf16_cpu_to_fp16_cpu(self):
        result = bridge.post_normalization_fp16_bridge(synthetic_crops())
        self.assertEqual(result[0].dtype, torch.float16)
        self.assertEqual(result[0].device.type, 'cpu')

    def test_shape_and_tiling_preserved_multiple_tiles(self):
        crops, tiling = synthetic_crops((2, 3))
        converted, returned_tiling = bridge.post_normalization_fp16_bridge((crops, tiling))
        self.assertEqual(converted.shape, crops.shape)
        self.assertIs(returned_tiling, tiling)
        self.assertTrue(torch.equal(converted.float(), crops.float()))

    def test_input_not_mutated_and_storage_not_shared(self):
        crops, tiling = synthetic_crops()
        before = crops.clone()
        converted, _ = bridge.post_normalization_fp16_bridge((crops, tiling))
        self.assertTrue(torch.equal(crops, before))
        self.assertEqual(crops.dtype, torch.bfloat16)
        self.assertNotEqual(converted.data_ptr(), crops.data_ptr())
        converted.zero_()
        self.assertTrue(torch.equal(crops, before))

    def test_other_dtypes_rejected_without_cast(self):
        crops, tiling = synthetic_crops()
        for dtype in (torch.float16, torch.float32, torch.float64, torch.int32, torch.bool):
            with self.subTest(dtype=dtype):
                wrong = crops.to(dtype)
                with patch.object(torch.Tensor, 'to', side_effect=AssertionError('must not convert')):
                    with self.assertRaisesRegex(ValueError, 'BF16_INPUT_REQUIRED'):
                        bridge.post_normalization_fp16_bridge((wrong, tiling))

    def test_simulated_cuda_bf16_rejected_before_arithmetic(self):
        self._reject_device(torch.bfloat16, 'cuda:0')

    def test_simulated_cuda_fp16_rejected_before_arithmetic(self):
        self._reject_device(torch.float16, 'cuda:0')

    def test_simulated_other_device_rejected(self):
        self._reject_device(torch.bfloat16, 'meta')

    def _reject_device(self, dtype, name):
        crops, tiling = synthetic_crops()
        crops = crops.to(dtype)
        # Mock only device metadata on a real CPU tensor. No CUDA allocation/query.
        with patch.object(torch.Tensor, 'device', property(lambda _: torch.device(name))), \
                patch.object(torch.Tensor, 'to', side_effect=AssertionError('transfer forbidden')), \
                patch.object(torch, 'isfinite', side_effect=AssertionError('arithmetic too early')):
            with self.assertRaisesRegex(ValueError, 'CPU_INPUT_REQUIRED'):
                bridge.post_normalization_fp16_bridge((crops, tiling))

    def test_unexpected_structure_and_tensor_bypass_rejected(self):
        crops, tiling = synthetic_crops()
        for wrong in (crops, [crops, tiling], {'crops': crops, 'tiling': tiling},
                      (crops, tiling, crops), ((crops, crops), tiling), (None, tiling),
                      (crops, (1, crops)), (crops, (True, 1)), (crops, (0, 1)),
                      (crops, [1, 1]), (crops, (1.0, 1)), (crops, (1, 1, crops))):
            with self.subTest(kind=type(wrong).__name__), self.assertRaises(ValueError):
                bridge.post_normalization_fp16_bridge(wrong)

    def test_wrong_shape_rejected(self):
        for shape in ((1, 3, 378, 378), (2, 1, 378, 378), (2, 3, 1, 1), (2, 3, 378), (0,)):
            with self.subTest(shape=shape), self.assertRaisesRegex(ValueError, 'CROP_SHAPE'):
                bridge.post_normalization_fp16_bridge((torch.zeros(shape, dtype=torch.bfloat16), (1, 1)))

    def test_subclass_rejected(self):
        class UnexpectedTensor(torch.Tensor):
            pass
        crops, tiling = synthetic_crops()
        with self.assertRaisesRegex(ValueError, 'PLAIN_TENSOR'):
            bridge.post_normalization_fp16_bridge((crops.as_subclass(UnexpectedTensor), tiling))

    def test_gradients_rejected(self):
        crops, tiling = synthetic_crops()
        with self.assertRaisesRegex(ValueError, 'DENSE_INFERENCE'):
            bridge.post_normalization_fp16_bridge((crops.requires_grad_(), tiling))

    def test_sparse_rejected(self):
        crops = torch.sparse_coo_tensor(torch.zeros((4, 0), dtype=torch.long),
                                        torch.zeros(0, dtype=torch.bfloat16), (2, 3, 378, 378))
        with self.assertRaisesRegex(ValueError, 'DENSE_INFERENCE'):
            bridge.post_normalization_fp16_bridge((crops, (1, 1)))

    def test_noncontiguous_native_like_layout_accepted(self):
        crops = torch.zeros((2, 378, 378, 3), dtype=torch.bfloat16).permute(0, 3, 1, 2)
        self.assertFalse(crops.is_contiguous())
        converted, _ = bridge.post_normalization_fp16_bridge((crops, (1, 1)))
        self.assertEqual(converted.shape, crops.shape)

    def test_nan_and_infinity_rejected_before_cast(self):
        for value in (float('nan'), float('inf'), -float('inf')):
            crops, tiling = synthetic_crops()
            crops[0, 0, 0, 0] = value
            with patch.object(torch.Tensor, 'to', side_effect=AssertionError('must not cast')):
                with self.assertRaisesRegex(ValueError, 'NONFINITE_INPUT'):
                    bridge.post_normalization_fp16_bridge((crops, tiling))

    def test_fp16_overflow_rejected_no_fallback(self):
        crops, tiling = synthetic_crops()
        crops[0, 0, 0, 0] = 1e10
        self.assertTrue(torch.isfinite(crops).all())
        with self.assertRaisesRegex(ValueError, 'NONFINITE_OUTPUT'):
            bridge.post_normalization_fp16_bridge((crops, tiling))

    def test_diagnostic_is_cpu_finite_and_shape_preserving(self):
        diagnostic = numerical_diagnostic()
        self.assertEqual(diagnostic['input_dtype'], 'torch.bfloat16')
        self.assertEqual(diagnostic['output_dtype'], 'torch.float16')
        self.assertEqual(diagnostic['shape'], [2, 3, 378, 378])
        self.assertTrue(diagnostic['input_finite'] and diagnostic['output_finite'])
        # These normal BF16 fixture values are exactly representable in FP16.
        # This is not a claim for arbitrary BF16 magnitudes or upstream outputs.
        self.assertEqual(diagnostic['max_absolute_difference_float32'], 0.0)

    def test_small_bf16_can_change_numerically(self):
        crops, tiling = synthetic_crops()
        crops[0, 0, 0, 0] = 2 ** -30
        converted, _ = bridge.post_normalization_fp16_bridge((crops, tiling))
        self.assertGreater((crops.float() - converted.float()).abs().max().item(), 0)

    def test_invalid_conversion_result_rejected(self):
        crops, tiling = synthetic_crops()
        bad_results = (crops, torch.zeros((1,), dtype=torch.float16), None)
        for bad in bad_results:
            with self.subTest(kind=type(bad).__name__):
                with patch.object(torch.Tensor, 'to', return_value=bad):
                    with self.assertRaisesRegex(ValueError, 'INVALID_CONVERSION_RESULT'):
                        bridge.post_normalization_fp16_bridge((crops, tiling))

    def test_no_cuda_autocast_network_or_remote_import(self):
        crops = synthetic_crops()
        real_import = __import__

        def checked_import(name, *args, **kwargs):
            if name.split('.')[0] in {'transformers', 'huggingface_hub', 'tokenizers', 'moondream'}:
                raise AssertionError('remote/model dependency import forbidden')
            return real_import(name, *args, **kwargs)

        with ExitStack() as stack:
            for obj, name in ((torch.Tensor, 'cuda'), (torch, 'autocast'),
                              (torch.cuda, '_lazy_init'), (socket, 'create_connection'),
                              (socket.socket, 'connect')):
                stack.enter_context(patch.object(obj, name, side_effect=AssertionError('forbidden')))
            stack.enter_context(patch('builtins.__import__', side_effect=checked_import))
            stack.enter_context(patch('builtins.open', side_effect=AssertionError('no data reads')))
            importlib.reload(bridge)
            bridge.post_normalization_fp16_bridge(crops)

    def test_only_torch_import_and_explicit_dtype_only_copy(self):
        tree = ast.parse(Path(bridge.__file__).read_text(encoding='utf-8'))
        imports = [a.name for node in ast.walk(tree) if isinstance(node, ast.Import) for a in node.names]
        self.assertEqual(imports, ['torch'])
        self.assertFalse(any(isinstance(n, ast.ImportFrom) for n in ast.walk(tree)))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertFalse(any(n.func.attr in {'cuda', 'autocast', 'load', 'from_pretrained',
                                            'generate', 'query', 'detect', 'point'} for n in calls))
        casts = [n for n in calls if n.func.attr == 'to']
        self.assertEqual(len(casts), 1)
        self.assertEqual({k.arg for k in casts[0].keywords}, {'dtype', 'copy'})

    def test_local_fake_returns_only_after_normalization(self):
        events = []
        def fake_prepare():
            events.extend(['crop', 'resize', 'conversion', 'BF16 allocation', 'BF16 normalization'])
            return synthetic_crops()
        upstream = fake_prepare()
        result = bridge.post_normalization_fp16_bridge(upstream)
        events.append('bridge complete')
        self.assertEqual(events[-2:], ['BF16 normalization', 'bridge complete'])
        self.assertEqual(result[0].dtype, torch.float16)
        # No encoder or model call. Real upstream execution remains untested.

    def test_plan_matches_code_and_does_not_promote_runtime(self):
        plan = json.loads((ROOT / PLAN).read_text(encoding='utf-8'))
        self.assertEqual(plan['bridge_version'], bridge.BRIDGE_VERSION)
        self.assertEqual(plan['model_revision'], bridge.MODEL_REVISION)
        self.assertEqual(plan['crop_tensor_shape'], ['1 + rows * cols', bridge.CHANNELS,
                                                     bridge.CROP_SIZE, bridge.CROP_SIZE])
        self.assertEqual((plan['input_expected_device'], plan['input_expected_dtype'],
                          plan['output_device'], plan['output_dtype']), ('CPU', 'BF16', 'CPU', 'FP16'))
        self.assertEqual(plan['bridge_scope'], 'POST_NORMALIZATION_BF16_CPU_TO_FP16_CPU')
        self.assertEqual(plan['tokenizer_runtime_enforcement'], 'NOT_IMPLEMENTED')
        for key in ('upstream_source_modified', 'normalization_modified', 'crop_logic_modified',
                    'resize_logic_modified', 'cuda_move_performed_by_bridge', 'autocast_used',
                    'automatic_fallback', 'full_fp16_runtime_validated', 't4_smoke_run',
                    'model_inference_used', 'synthetic_gate_run', 'inspecsafe_used'):
            self.assertIs(plan[key], False)

    def test_protected_files_match_exact_base_hashes(self):
        plan = json.loads((ROOT / PLAN).read_text(encoding='utf-8'))
        for name, expected in plan['protected_repository_files_sha256'].items():
            with self.subTest(path=name):
                data = (ROOT / name).read_bytes()
                if not name.endswith('.png'):
                    data = data.replace(b'\r\n', b'\n')
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected)

    def test_pinned_source_evidence_matches_unchanged_audit(self):
        plan = json.loads((ROOT / PLAN).read_text(encoding='utf-8'))
        audit = json.loads((ROOT / plan['source_audit_reference']).read_text(encoding='utf-8'))
        for row in plan['source_files']:
            original = next(r for r in audit['artifacts'] if r['path'] == row['path'])
            self.assertEqual(row['sha256'], original['sha256'])
            self.assertEqual(row['size_bytes'], original['size_bytes'])
            self.assertEqual(original['revision'], bridge.MODEL_REVISION)


if __name__ == '__main__':
    unittest.main()
