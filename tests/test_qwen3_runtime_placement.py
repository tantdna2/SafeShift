"""Synthetic Qwen3 placement/allocator checks; no model, GPU or dataset access."""

import ast
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.protocol.classification_policy import (
    ROOT, POLICY_PATH, QWEN3_AMENDMENT_PATH, load_policy,
)
from safeshift.runners import p2_bridge as bridge, p2_harness as harness
from safeshift.runners import p2_owner as owner, p2_preflight as preflight
from safeshift.runners import qwen3_placement as placement
from safeshift.runners.qwen3_vl import Qwen3VLRunner
from tests.test_qwen_runner import Runtime, request

BASE = "031958a5ce668057f763973a722a3506d73f39f0"
AUTHORITY = "configs/frozen/p2_execution_authority.v1.json"


class Qwen3RuntimePlacementTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {placement.ALLOCATOR_NAME: placement.ALLOCATOR_VALUE})
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("PYTORCH_CUDA_ALLOC_CONF", None)
        self.entry = load_policy(qwen3_runtime=True)["classification"]["qwen3"]
        self.context = bridge.context_for("qwen3", self.entry,
                                         bridge.RunIdentity("synthetic-new-id", "a" * 40, "SYNTHETIC"))

    def native(self):
        return SimpleNamespace(hf_device_map=deepcopy(self.entry["device"]["device_map"]),
            dtype="torch.float16", is_quantized=False,
            config=SimpleNamespace(quantization_config=None, _attn_implementation="sdpa"))

    def check_bridge(self, native):
        bridge._loaded_state(SimpleNamespace(_resources=(None, native)), "qwen3")

    def runner(self):
        runtime = Runtime()
        runtime.model.hf_device_map = deepcopy(self.entry["device"]["device_map"])
        runtime.model.device, runtime.model.dtype = "cuda:1", "torch.float16"
        runtime.model.config = self.native().config
        runtime.factory.return_value = replace(runtime.backend, software_versions=self.entry["software_versions"])
        return runtime, Qwen3VLRunner(backend_factory=runtime.factory)

    def test_exact_winner_load_and_native_generation_without_input_or_prompt_changes(self):
        runtime, runner = self.runner()
        runner.initialize(self.context)
        runner.load(self.context)
        self.check_bridge(runtime.model)
        kwargs = runtime.model_factory.from_pretrained.call_args.kwargs
        self.assertEqual(kwargs["device_map"], self.entry["device"]["device_map"])
        self.assertEqual(kwargs["dtype"], runtime.torch.float16)
        self.assertNotIn("attn_implementation", kwargs)  # Keep default SDPA.
        self.assertNotIn("offload_folder", kwargs)
        self.assertNotIn("quantization_config", kwargs)
        for count in (4581, 4149):
            runtime.processor.input_ids = list(range(count))
            req = request(prompt="unchanged synthetic caller text")
            raw = json.loads(runner.generate_raw(runner.prepare_input(req, self.context), self.context))
            self.assertEqual(raw["input_token_count"], count)
            self.assertEqual(raw["generation_kwargs"], {"do_sample": False, "max_new_tokens": 32})
            self.assertEqual(runtime.processor.calls[-1]["size"], (2, 3))
            self.assertEqual(runtime.processor.calls[-1]["prompt"], req.prompt)
        self.assertEqual(runtime.model_factory.from_pretrained.call_count, 1)

    def test_winning_map_has_all_36_layers_and_only_cpu_embedding(self):
        mapping = self.native().hf_device_map
        self.assertEqual(len(mapping), 41)
        self.assertEqual([name for name, device in mapping.items() if device == "cpu"],
                         ["model.language_model.embed_tokens"])
        for i in range(36):
            self.assertEqual(mapping[f"model.language_model.layers.{i}"], 0 if i <= 20 else 1)
        for name in ("model.visual", "model.language_model.norm", "model.language_model.rotary_emb", "lm_head"):
            self.assertEqual(mapping[name], 1)
        self.check_bridge(self.native())

    def test_one_layer_on_wrong_gpu_fails(self):
        for i, device in ((20, 1), (21, 0)):
            native = self.native()
            native.hf_device_map[f"model.language_model.layers.{i}"] = device
            with self.subTest(layer=i), self.assertRaisesRegex(ValueError, "EXACT_QWEN3_DEVICE_MAP"):
                self.check_bridge(native)

    def test_embedding_must_be_on_cpu(self):
        for device in (0, 1):
            native = self.native()
            native.hf_device_map[placement.EMBEDDING] = device
            with self.subTest(device=device), self.assertRaisesRegex(ValueError, "EXACT_QWEN3_DEVICE_MAP"):
                self.check_bridge(native)

    def test_every_other_module_on_cpu_fails(self):
        for name in self.native().hf_device_map:
            if name == placement.EMBEDDING:
                continue
            native = self.native()
            native.hf_device_map[name] = "cpu"
            with self.subTest(module=name), self.assertRaisesRegex(ValueError, "EXACT_QWEN3_DEVICE_MAP"):
                self.check_bridge(native)

    def test_disk_extra_missing_auto_and_bool_maps_fail(self):
        for name in self.native().hf_device_map:
            native = self.native()
            native.hf_device_map[name] = "disk"
            with self.subTest(disk_module=name), self.assertRaisesRegex(ValueError, "EXACT_QWEN3_DEVICE_MAP"):
                self.check_bridge(native)
        for mapping in (None, "auto", {**placement.DEVICE_MAP, "extra": "cpu"},
                        {**placement.DEVICE_MAP, "extra": 1},
                        {**placement.DEVICE_MAP, "lm_head": True},
                        {k: v for k, v in placement.DEVICE_MAP.items() if k != "lm_head"}):
            native = self.native()
            native.hf_device_map = mapping
            with self.subTest(mapping=mapping), self.assertRaisesRegex(ValueError, "EXACT_QWEN3_DEVICE_MAP"):
                self.check_bridge(native)

    def test_loaded_dtype_quantization_and_attention_fail_closed(self):
        for dtype in ("torch.bfloat16", "torch.float32", "torch.int8"):
            native = self.native()
            native.dtype = dtype
            with self.subTest(dtype=dtype), self.assertRaisesRegex(ValueError, "FP16_NONE_SDPA"):
                self.check_bridge(native)
        for attribute, value in (("is_quantized", True), ("quantization_config", {}),
                                 ("_attn_implementation", "flash_attention_2"),
                                 ("_attn_implementation", "eager")):
            native = self.native()
            setattr(native if attribute == "is_quantized" else native.config, attribute, value)
            with self.subTest(attribute=attribute), self.assertRaisesRegex(ValueError, "FP16_NONE_SDPA"):
                self.check_bridge(native)

    def test_invalid_explicit_context_fails_before_backend_import(self):
        contexts = [replace(self.context, precision="BF16"), replace(self.context, quantization="INT8"),
                    replace(self.context, device={"placement": "auto"}, source_kind="INSPECSAFE"),
                    replace(self.context, device={**self.context.device, "automatic_fallback": True})]
        for name, device in (("model.language_model.layers.20", 1), (placement.EMBEDDING, 0),
                             ("lm_head", "disk"), ("model.visual", "cpu")):
            mapping = deepcopy(placement.DEVICE_MAP)
            mapping[name] = device
            contexts.append(replace(self.context, device={"placement": "explicit", "device_map": mapping}))
        for context in contexts:
            runtime, runner = self.runner()
            with self.subTest(context=context.device), self.assertRaises(ValueError):
                runner.initialize(context)
            runtime.factory.assert_not_called()

    def test_wrong_loaded_map_does_not_publish_resources_or_fallback(self):
        runtime, runner = self.runner()
        runtime.model.hf_device_map["model.language_model.layers.20"] = 1
        runner.initialize(self.context)
        with self.assertRaisesRegex(ValueError, "EXACT_QWEN3_DEVICE_MAP"):
            runner.load(self.context)
        self.assertIsNone(runner._resources)
        self.assertEqual(runtime.model_factory.from_pretrained.call_count, 1)

    def test_missing_or_wrong_allocator_fails_runner_and_bridge(self):
        for value in (None, "", "expandable_segments:False", "max_split_size_mb:128",
                      "expandable_segments:True,max_split_size_mb:128"):
            with self.subTest(value=value), patch.dict(os.environ):
                if value is None:
                    os.environ.pop(placement.ALLOCATOR_NAME, None)
                else:
                    os.environ[placement.ALLOCATOR_NAME] = value
                runtime, runner = self.runner()
                with self.assertRaisesRegex(ValueError, "EXACT_QWEN3_ALLOCATOR"):
                    runner.initialize(self.context)
                runtime.factory.assert_not_called()
                with self.assertRaisesRegex(ValueError, "EXACT_QWEN3_ALLOCATOR"):
                    self.check_bridge(self.native())

    def test_runtime_allocator_gate_precedes_torch_import_or_cuda_probe(self):
        for value in (None, "expandable_segments:False"):
            with self.subTest(value=value), patch.dict(os.environ), \
                    patch.object(preflight, "require_offline_env"), \
                    patch.object(preflight, "software_observation", side_effect=AssertionError("NO_RUNTIME_PROBE")):
                if value is None:
                    os.environ.pop(placement.ALLOCATOR_NAME, None)
                else:
                    os.environ[placement.ALLOCATOR_NAME] = value
                with self.assertRaisesRegex(ValueError, "EXACT_QWEN3_ALLOCATOR"):
                    preflight.runtime_observation("qwen3")

    def test_owner_sets_allocator_before_first_torch_import_in_fresh_process(self):
        code = '''import builtins, os, sys
os.environ.pop('PYTORCH_ALLOC_CONF', None)
os.environ.pop('PYTORCH_CUDA_ALLOC_CONF', None)
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'torch', 'transformers', 'huggingface_hub', 'accelerate'}:
        assert os.environ['PYTORCH_ALLOC_CONF'] == 'expandable_segments:True'
        assert name == 'torch'
        raise AssertionError('EXPECTED_FIRST_TORCH_IMPORT')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from safeshift.runners import p2_owner as owner
assert 'torch' not in sys.modules
def observed_run(**kwargs):
    import torch
owner.production_run = observed_run
try:
    owner.main(['run', '--model', 'qwen3', '--run-id', 'synthetic-new-id',
                '--dataset-root', 'NEVER_READ', '--manifest-path', 'NEVER_READ',
                '--provenance-path', 'NEVER_READ'])
except AssertionError as exc:
    assert str(exc) == 'EXPECTED_FIRST_TORCH_IMPORT'
else:
    raise AssertionError('TORCH_IMPORT_BOUNDARY_NOT_REACHED')
'''
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True)

    def test_owner_rejects_missing_allocator_after_torch_import(self):
        with patch.dict(os.environ), patch.dict(sys.modules, {"torch": SimpleNamespace()}):
            os.environ.pop(placement.ALLOCATOR_NAME, None)
            with self.assertRaisesRegex(ValueError, "BEFORE_TORCH_IMPORT"):
                placement.configure_allocator()
            self.assertNotIn(placement.ALLOCATOR_NAME, os.environ)

    def test_owner_rejects_wrong_allocator_or_conflicting_legacy_alias(self):
        for name in (placement.ALLOCATOR_NAME, "PYTORCH_CUDA_ALLOC_CONF"):
            with self.subTest(name=name), patch.dict(os.environ):
                os.environ[name] = "expandable_segments:False"
                with self.assertRaises(ValueError):
                    placement.configure_allocator()
                self.assertEqual(os.environ[name], "expandable_segments:False")

    def test_other_models_keep_contract_and_owner_environment(self):
        original, amended = load_policy(), load_policy(qwen3_runtime=True)
        args = ["run", "--run-id", "synthetic-new-id", "--dataset-root", "NEVER_READ",
                "--manifest-path", "NEVER_READ", "--provenance-path", "NEVER_READ"]
        for model in ("qwen2_5", "internvl3", "moondream"):
            self.assertEqual(original["classification"][model], amended["classification"][model])
            self.assertEqual(harness.resolve_production_backend(model).entry, original["classification"][model])
            with self.subTest(model=model), patch.dict(os.environ), \
                    patch.object(owner, "production_run", return_value="synthetic"), redirect_stdout(io.StringIO()):
                os.environ[placement.ALLOCATOR_NAME] = "unrelated-owner-value"
                self.assertEqual(owner.main([*args, "--model", model]), 0)
                self.assertEqual(os.environ[placement.ALLOCATOR_NAME], "unrelated-owner-value")

    def test_amendment_changes_only_qwen3_runtime_fields(self):
        original, amended = load_policy(), load_policy(qwen3_runtime=True)
        old, new = original["classification"]["qwen3"], amended["classification"]["qwen3"]
        self.assertEqual({key for key in old if old[key] != new[key]},
                         {"device", "hardware_contract", "runtime_requirements"})
        self.assertEqual(new["hardware_contract"]["cpu_offload_modules"], [placement.EMBEDDING])
        self.assertFalse(new["hardware_contract"]["disk_offload"])
        self.assertFalse(new["hardware_contract"]["automatic_fallback"])
        self.assertEqual(harness.registry()["qwen3"], new)
        for path in (POLICY_PATH, AUTHORITY, "configs/pre_freeze/protocol_freeze_candidate.d9r26.v1.json",
                     "configs/pre_freeze/d9r25_harness_contract.v1.json", "configs/pre_freeze/d9r24_metric_contract.v1.json",
                     "prompts/p2_classification_c1_v1.txt"):
            expected = subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT)
            self.assertEqual((ROOT / path).read_bytes().replace(b"\r\n", b"\n"), expected, path)
        authority = json.loads((ROOT / AUTHORITY).read_bytes())
        self.assertEqual(authority["reruns"], [])
        record = json.loads((ROOT / QWEN3_AMENDMENT_PATH).read_bytes())
        self.assertFalse(record["rerun_authorized"])
        self.assertFalse(record["inspecsafe_inference_authorized"])

    def test_invalid_amendment_cannot_add_cpu_disk_fallback_or_semantic_overrides(self):
        record = json.loads((ROOT / QWEN3_AMENDMENT_PATH).read_bytes())
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            target = repo / POLICY_PATH
            target.parent.mkdir(parents=True)
            target.write_bytes((ROOT / POLICY_PATH).read_bytes())
            for field, value in (("cpu_offload_modules", [placement.EMBEDDING, "lm_head"]),
                                 ("disk_offload", True), ("automatic_fallback", True),
                                 ("allocator_env", {})):
                changed = deepcopy(record)
                changed["runtime_patch"]["hardware_contract"][field] = value
                (repo / QWEN3_AMENDMENT_PATH).write_text(json.dumps(changed), encoding="utf-8")
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, "AMENDMENT_MISMATCH"):
                    load_policy(repo, qwen3_runtime=True)
            for field, value in (("precision", "BF16"), ("quantization", "INT8"), ("decoding", {})):
                changed = deepcopy(record)
                changed["runtime_patch"][field] = value
                (repo / QWEN3_AMENDMENT_PATH).write_text(json.dumps(changed), encoding="utf-8")
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, "AMENDMENT_MISMATCH"):
                    load_policy(repo, qwen3_runtime=True)

    def test_generation_and_preprocessing_methods_preserved(self):
        path = "safeshift/runners/qwen3_vl.py"
        before = subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT)
        def methods(raw):
            cls = next(n for n in ast.parse(raw).body if isinstance(n, ast.ClassDef) and n.name == "Qwen3VLRunner")
            return {n.name: ast.dump(n) for n in cls.body if isinstance(n, ast.FunctionDef)}
        old, current = methods(before), methods((ROOT / path).read_bytes())
        for method in ("prepare_input", "generate_raw", "_clear_call_state"):
            self.assertEqual(old[method], current[method], method)

    def test_amendment_does_not_authorize_production_before_dataset_or_model_access(self):
        with patch.object(harness, "verify_dataset", side_effect=AssertionError("NO_DATASET")) as data, \
                patch.object(harness, "resolve_production_backend", side_effect=AssertionError("NO_MODEL")) as model:
            with self.assertRaisesRegex(PermissionError, harness.BLOCK):
                harness.production_run(model="qwen3", run_id="synthetic-new-id", dataset_root="NEVER_READ",
                                       manifest_path="NEVER_READ", provenance_path="NEVER_READ")
            data.assert_not_called()
            model.assert_not_called()


if __name__ == "__main__":
    unittest.main()
