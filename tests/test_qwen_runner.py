"""Offline structural contracts only. All runtime objects and outputs are fake."""

import ast
import builtins
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, replace
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
    ErrorCode, GenerationFailure, ModelIdentity, ParseStatus, Participation,
    Request, RunContext, SpatialKind, Task, execute_call,
)
from safeshift.runners.qwen3_vl import (
    BACKEND, ENVELOPE_VERSION, MODEL_ID, REVISION, QwenBackend, Qwen3VLAdapter, Qwen3VLRunner,
)
from safeshift.runners.storage import FileRawStore


VERSIONS = {"torch": "fake-torch", "transformers": "fake-transformers", "pillow": PILLOW_VERSION}


def context(**changes):
    return replace(RunContext(
        run_id="offline-qwen-contract", call_id="call-a", decoding={},
        preprocessing={"mode": "official_processor"}, precision="FP32", quantization="NONE",
        device={"placement": "cpu"}, software_versions=deepcopy(VERSIONS),
        git_commit_sha="f86771d1006d93d99375fe74701215e8d8f601ee",
        command="python -m unittest tests.test_qwen_runner -v", source_kind="handcrafted_dummy",
    ), **changes)


def request(**changes):
    stream = BytesIO()
    Image.new("RGB", (2, 3), (21, 42, 63)).save(stream, format="PNG")
    return replace(Request(Task.CLASSIFICATION, "tiny-fixture", "in-memory-png",
                           stream.getvalue(), "caller-prompt", "Caller text: tiếng Việt\n"), **changes)


class Tensor:
    def __init__(self, data):
        self.data = deepcopy(data)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return Tensor(self.data[index])

    def tolist(self):
        return deepcopy(self.data)


class Inputs(dict):
    def to(self, device):
        self.device = device
        return self


class Processor:
    def __init__(self):
        self.calls = []
        self.decodes = []
        self.text = '{"safety_level":"Level04"}'
        self.failure = None
        self.input_ids = [11, 22, 33]

    def apply_chat_template(self, messages, **kwargs):
        if self.failure:
            raise self.failure
        image = messages[0]["content"][0]["image"]
        self.calls.append({"role": messages[0]["role"], "messages_count": len(messages),
                           "content_count": len(messages[0]["content"]),
                           "prompt": messages[0]["content"][1]["text"],
                           "pixel": image.getpixel((0, 0)), "size": image.size,
                           "mode": image.mode, "kwargs": kwargs})
        return Inputs(input_ids=Tensor([self.input_ids]), pixel_values=Tensor([[9]]),
                      image_grid_thw=Tensor([[1, 2, 3]]), attention_mask=Tensor([[1, 1, 1]]))

    def batch_decode(self, ids, **kwargs):
        self.decodes.append((deepcopy(ids), kwargs))
        return [self.text if kwargs["skip_special_tokens"] else "<control>" + self.text + "<end>"]


class GenerationConfig:
    def __init__(self):
        self.num_return_sequences = 1
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
    device = "cpu"
    dtype = "fake-fp32"
    hf_device_map = {"": "cpu"}

    def __init__(self, runtime):
        self.runtime = runtime
        self.model = SimpleNamespace(rope_deltas=None)
        self.generation_config = GenerationConfig()
        self.calls = []
        self.eval_count = 0
        self.failure = None
        self.continuation = [701, 702, 703]

    def eval(self):
        self.eval_count += 1
        return self

    def generate(self, **kwargs):
        assert self.runtime.inference_active
        assert self.model.rope_deltas is None
        assert getattr(self, "_cache", None) is None
        self.calls.append(kwargs)
        self.model.rope_deltas = Tensor([999])
        self._cache = object()
        kwargs["generation_config"].temperature = 19  # Must never mutate shared defaults.
        if self.failure:
            raise self.failure
        return Tensor([kwargs["input_ids"][0].tolist() + self.continuation])


class Runtime:
    def __init__(self):
        self.inference_active = False
        self.processor = Processor()
        self.model = Model(self)
        self.processor_factory = SimpleNamespace(from_pretrained=Mock(return_value=self.processor))
        self.model_factory = SimpleNamespace(from_pretrained=Mock(return_value=self.model))
        self.torch = SimpleNamespace(float32="fake-fp32", bfloat16="fake-bf16",
                                     float16="fake-fp16", inference_mode=self.inference_mode)
        self.backend = QwenBackend(self.torch, self.processor_factory, self.model_factory, VERSIONS)
        self.factory = Mock(return_value=self.backend)

    @contextmanager
    def inference_mode(self):
        self.inference_active = True
        try:
            yield
        finally:
            self.inference_active = False


class QwenRunnerTests(unittest.TestCase):
    def setUp(self):
        # Fail immediately on accidental network or real ML import in every test.
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
            guard = patch(target, side_effect=AssertionError("network forbidden in offline tests"))
            guard.start()
            self.addCleanup(guard.stop)
        original_import = builtins.__import__

        def offline_import(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "huggingface_hub", "qwen_vl_utils"}:
                raise ImportError("real runtime import forbidden in offline test")
            return original_import(name, *args, **kwargs)

        guard = patch("builtins.__import__", side_effect=offline_import)
        guard.start()
        self.addCleanup(guard.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.store = FileRawStore(self.repo)
        self.runtime = Runtime()
        self.runner = Qwen3VLRunner(backend_factory=self.runtime.factory)
        self.adapter = Qwen3VLAdapter()

    def execute(self, *, ctx=None, req=None, adapter=None, store=None):
        return execute_call(self.runner, adapter or self.adapter, store or self.store,
                            req or request(), ctx or context())

    def raw(self, result):
        return (self.repo / result.raw_output.path).read_bytes()

    def generate(self, ctx=None, req=None):
        ctx = ctx or context()
        self.runner.initialize(ctx)
        self.runner.load(ctx)
        return self.runner.generate_raw(self.runner.prepare_input(req or request(), ctx), ctx)

    def test_exact_identity_matches_b0(self):
        record = strict_json(Path("configs/pre_freeze/local_model_provenance.d9.json").read_bytes())
        qwen = record["models"][0]
        self.assertEqual(self.runner.identity.model_id, "Qwen/Qwen3-VL-8B-Instruct")
        self.assertEqual(self.runner.identity.immutable_revision, "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b")
        self.assertEqual(qwen["immutable_revision"], self.runner.identity.immutable_revision)

    def test_both_factories_pin_revision_and_disable_remote_code_and_network(self):
        self.generate()
        for factory in (self.runtime.processor_factory, self.runtime.model_factory):
            args, kwargs = factory.from_pretrained.call_args
            self.assertEqual(args, (MODEL_ID,))
            self.assertEqual(kwargs["revision"], REVISION)
            self.assertIs(kwargs["trust_remote_code"], False)
            self.assertIs(kwargs["local_files_only"], True)

    def test_initialize_is_idempotent_and_does_not_load(self):
        self.runner.initialize(context())
        self.runner.initialize(context(call_id="b"))
        self.runtime.factory.assert_called_once_with()
        self.runtime.model_factory.from_pretrained.assert_not_called()

    def test_load_idempotent_across_execute_calls(self):
        self.assertIsNone(self.execute().error)
        self.assertIsNone(self.execute(ctx=context(call_id="b")).error)
        self.runtime.factory.assert_called_once_with()
        self.runtime.processor_factory.from_pretrained.assert_called_once()
        self.runtime.model_factory.from_pretrained.assert_called_once()
        self.assertEqual(self.runtime.model.eval_count, 1)

    def test_changed_conditions_require_new_lifecycle(self):
        self.generate()
        cases = [dict(precision="BF16"), dict(quantization="4-bit"),
                 dict(device={"placement": "cuda:7"}), dict(software_versions={**VERSIONS, "driver": "new"}),
                 dict(preprocessing={"mode": "different"})]
        for changes in cases:
            with self.subTest(changes=changes):
                for method in (self.runner.initialize, self.runner.load):
                    with self.assertRaisesRegex(ValueError, "new runner lifecycle"):
                        method(context(**changes))
        self.runtime.model_factory.from_pretrained.assert_called_once()

    def test_in_place_context_mutation_does_not_mutate_cached_key(self):
        ctx = context()
        self.generate(ctx)
        ctx.device["placement"] = "cuda:3"
        with self.assertRaisesRegex(ValueError, "condition changed"):
            self.runner.initialize(ctx)

    def test_identity_cannot_be_changed_to_another_checkpoint(self):
        self.runner.identity = ModelIdentity("synthetic/other")
        with self.assertRaises(ValueError):
            self.runner.initialize(context())
        self.runtime.factory.assert_not_called()

    def test_failed_initialization_can_retry_cleanly(self):
        self.runtime.factory.side_effect = [ImportError(), self.runtime.backend]
        self.assertEqual(self.execute().error.code, ErrorCode.INITIALIZATION_FAILURE)
        self.assertIsNone(self.runner._backend)
        self.assertIsNone(self.execute(ctx=context(call_id="b")).error)
        self.assertEqual(self.runtime.factory.call_count, 2)

    def test_failed_model_load_can_retry_without_partial_resource_publication(self):
        self.runtime.model_factory.from_pretrained.side_effect = [RuntimeError(), self.runtime.model]
        result = self.execute()
        self.assertEqual(result.error.code, ErrorCode.MODEL_LOAD_FAILURE)
        self.assertIsNone(self.runner._resources)
        self.assertIsNone(result.raw_output)
        self.assertEqual(self.runtime.model_factory.from_pretrained.call_count, 1)
        self.assertIsNone(self.execute(ctx=context(call_id="b")).error)
        self.assertEqual(self.runtime.processor_factory.from_pretrained.call_count, 2)
        self.assertEqual(self.runtime.model_factory.from_pretrained.call_count, 2)

    def test_processor_load_error_has_no_model_attempt(self):
        self.runtime.processor_factory.from_pretrained.side_effect = RuntimeError()
        self.assertEqual(self.execute().error.code, ErrorCode.MODEL_LOAD_FAILURE)
        self.runtime.model_factory.from_pretrained.assert_not_called()
        self.assertIsNone(self.runner._resources)

    def test_post_load_validation_error_does_not_mark_loaded(self):
        self.runtime.model.generation_config.cache_implementation = "static"
        self.assertEqual(self.execute().error.code, ErrorCode.MODEL_LOAD_FAILURE)
        self.assertIsNone(self.runner._resources)
        self.runtime.model.generation_config.cache_implementation = None
        self.assertIsNone(self.execute(ctx=context(call_id="b")).error)

    def test_versions_must_match_recorded_runtime(self):
        result = self.execute(ctx=context(software_versions={"torch": "wrong"}))
        self.assertEqual(result.error.code, ErrorCode.INITIALIZATION_FAILURE)
        self.assertIsNone(self.runner._backend)
        self.runtime.processor_factory.from_pretrained.assert_not_called()

    def test_default_backend_selects_native_classes_using_mock_imports_only(self):
        previous_import = builtins.__import__
        fake_torch = SimpleNamespace(**vars(self.runtime.torch), __version__=VERSIONS["torch"])
        fake_transformers = SimpleNamespace(
            __version__=VERSIONS["transformers"],
            AutoProcessor=self.runtime.processor_factory,
            Qwen3VLForConditionalGeneration=self.runtime.model_factory,
        )

        def mock_import(name, *args, **kwargs):
            if name == "torch":
                return fake_torch
            if name == "transformers":
                return fake_transformers
            return previous_import(name, *args, **kwargs)

        self.runner = Qwen3VLRunner()
        with patch("builtins.__import__", side_effect=mock_import):
            self.assertIsNone(self.execute().error)
        self.runtime.model_factory.from_pretrained.assert_called_once()
        self.runtime.processor_factory.from_pretrained.assert_called_once()

    def test_prompt_and_image_are_supplied_by_this_request(self):
        req = request()
        self.generate(req=req)
        call = self.runtime.processor.calls[0]
        self.assertEqual(call["prompt"], req.prompt)
        self.assertEqual(call["pixel"], (21, 42, 63))
        self.assertEqual(call["size"], (2, 3))
        self.assertEqual(call["mode"], "RGB")
        self.assertEqual((call["role"], call["messages_count"], call["content_count"]), ("user", 1, 2))

    def test_official_chat_template_arguments(self):
        self.generate()
        self.assertEqual(self.runtime.processor.calls[0]["kwargs"], {
            "tokenize": True, "add_generation_prompt": True, "return_dict": True, "return_tensors": "pt",
        })

    def test_prepared_input_objects_are_passed_to_generate_without_replacement(self):
        ctx = context()
        self.runner.initialize(ctx)
        self.runner.load(ctx)
        prepared = self.runner.prepare_input(request(), ctx)
        self.runner.generate_raw(prepared, ctx)
        for key, value in prepared.inputs.items():
            self.assertIs(self.runtime.model.calls[0][key], value)
        self.assertEqual(prepared.inputs.device, self.runtime.model.device)

    def test_decoding_kwargs_are_exact_caller_values(self):
        values = dict(do_sample=True, temperature=0.61, top_p=0.83, top_k=17,
                      max_new_tokens=29, repetition_penalty=1.02)
        obj = strict_json(self.generate(context(decoding=values)))
        actual = self.runtime.model.calls[0]
        self.assertEqual({key: actual[key] for key in values}, values)
        self.assertEqual(obj["generation_kwargs"], values)
        self.assertEqual(obj["effective_generation_config"]["temperature"], 0.61)

    def test_no_decoding_defaults_silently_added(self):
        obj = strict_json(self.generate())
        actual = self.runtime.model.calls[0]
        self.assertEqual(set(actual), {"input_ids", "pixel_values", "image_grid_thw", "attention_mask",
                                      "generation_config"})
        self.assertEqual(obj["generation_kwargs"], {})
        self.assertEqual(obj["effective_generation_config"]["temperature"], 0.7)
        self.assertIsNone(obj["effective_generation_config"]["max_new_tokens"])
        self.assertEqual(self.runtime.model.generation_config.temperature, 0.7)

    def test_unsupported_or_invalid_decoding_fails_before_generation(self):
        for values in ({"seed": 3}, {"past_key_values": []}, {"streamer": "x"}, {"presence_penalty": 1},
                       {"temperature": 0}, {"top_p": 2}, {"top_k": True}, {"do_sample": "false"},
                       {"max_new_tokens": 0}, {"temperature": float("nan")}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.generate(context(decoding=values))
        self.assertEqual(self.runtime.model.calls, [])

    def test_unapplied_seed_rejected(self):
        self.assertEqual(self.execute(ctx=context(seed=7)).error.code, ErrorCode.PREPROCESSING_FAILURE)
        self.assertEqual(self.runtime.model.calls, [])

    def test_full_and_continuation_ids_and_input_length_preserved(self):
        obj = strict_json(self.generate())
        self.assertEqual(obj["generated_ids_full"], [11, 22, 33, 701, 702, 703])
        self.assertEqual(obj["continuation_ids"], [701, 702, 703])
        self.assertEqual(obj["input_token_count"], 3)

    def test_variable_input_length_and_empty_continuation(self):
        self.runtime.processor.input_ids = [8]
        self.runtime.model.continuation = []
        obj = strict_json(self.generate())
        self.assertEqual(obj["input_token_count"], 1)
        self.assertEqual(obj["generated_ids_full"], [8])
        self.assertEqual(obj["continuation_ids"], [])

    def test_decode_retains_special_tokens_and_exact_parser_text(self):
        self.runtime.processor.text = ' \n{"safety_level": "Level04"}\t tiếng Việt'
        obj = strict_json(self.generate())
        self.assertEqual(obj["decoded_for_parser"], self.runtime.processor.text)
        self.assertEqual(obj["decoded_with_special_tokens"],
                         "<control>" + self.runtime.processor.text + "<end>")
        self.assertEqual(self.runtime.processor.decodes, [
            ([[701, 702, 703]], {"skip_special_tokens": False, "clean_up_tokenization_spaces": False}),
            ([[701, 702, 703]], {"skip_special_tokens": True, "clean_up_tokenization_spaces": False}),
        ])

    def test_raw_envelope_is_deterministic_strict_utf8_json_bytes(self):
        self.runtime.processor.text = "tiếng Việt\n"
        first = self.generate()
        self.assertIs(type(first), bytes)
        self.assertEqual(first, self.generate())
        obj = strict_json(first.decode("utf-8"))
        self.assertEqual(first, json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                         allow_nan=False, separators=(",", ":")).encode("utf-8"))
        self.assertEqual(obj["schema_version"], ENVELOPE_VERSION)
        self.assertEqual(obj["backend"], BACKEND)

    def test_file_raw_store_preserves_raw_and_metadata_before_adapter(self):
        def adapt(raw, task):
            files = list(self.repo.glob("data/processed/local_runs/*/response.raw"))
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].read_bytes(), raw)
            metadata = strict_json(files[0].with_name("metadata.json").read_bytes())
            self.assertEqual(metadata["parse_status"], "NOT_ATTEMPTED")
            self.assertEqual(metadata["immutable_revision"], REVISION)
            return Qwen3VLAdapter().adapt(raw, task)
        with patch.object(self.adapter, "adapt", side_effect=adapt) as spy:
            self.assertIsNone(self.execute().error)
            spy.assert_called_once()

    def test_storage_failure_prevents_adapter(self):
        with patch.object(self.store, "preserve", side_effect=OSError()), patch.object(self.adapter, "adapt") as spy:
            self.assertEqual(self.execute().error.code, ErrorCode.RAW_PRESERVATION_FAILURE)
            spy.assert_not_called()

    def test_valid_classification_uses_existing_parser_and_type(self):
        from safeshift.protocol.schema import parse_text
        with patch("safeshift.runners.qwen3_vl.parse_text", wraps=parse_text) as spy:
            result = self.execute()
            self.assertEqual(result.parse_status, ParseStatus.SUCCESS)
            self.assertEqual(result.canonical, Classification("Level04"))
            self.assertEqual(result.participation, Participation.PENDING)
            spy.assert_called_once_with(self.runtime.processor.text, "classification")

    def test_invalid_classification_is_not_repaired(self):
        for index, text in enumerate(('```json\n{"safety_level":"Level04"}\n```',
                                      '{"safety_level":"unknown"}', '{"safety_level":"Level04",}',
                                      '<control>{"safety_level":"Level04"}',
                                      '{"safety_level":"Level04","safety_level":"Level01"}')):
            with self.subTest(text=text):
                self.runtime.processor.text = text
                result = self.execute(ctx=context(call_id=str(index)))
                self.assertEqual(result.parse_status, ParseStatus.INVALID)
                self.assertEqual(result.error.code, ErrorCode.INVALID_CLASSIFICATION)
                self.assertEqual(strict_json(self.raw(result))["decoded_for_parser"], text)

    def test_grounding_is_unqualified_regardless_of_text(self):
        for index, text in enumerate(('malformed', '{"point_2d":[20,80]}',
                                     '{"bbox_2d":[0,0,1000,1000]}', '{"hazards":[]}')):
            self.runtime.processor.text = text
            with patch("safeshift.runners.qwen3_vl.parse_text") as spy:
                result = self.execute(ctx=context(call_id=str(index)), req=request(task=Task.GROUNDING))
                spy.assert_not_called()
            self.assertEqual(result.parse_status, ParseStatus.UNSUPPORTED)
            self.assertEqual(result.spatial_kind, SpatialKind.NONE)
            self.assertEqual(result.error.code, ErrorCode.UNSUPPORTED_GROUNDING)
            self.assertEqual(result.native_evidence["interface_status"], "NOT_YET_QUALIFIED")
            self.assertIsNone(result.canonical)
            self.assertEqual(result.participation, Participation.PENDING)
            self.assertFalse({"iou", "score", "bbox"} & asdict(result).keys())
            self.assertEqual(strict_json(self.raw(result))["decoded_for_parser"], text)

    def test_envelope_errors_map_to_parser_failure_after_preservation(self):
        with patch.object(self.runner, "generate_raw", return_value=b'{"bad_envelope":true}'):
            result = self.execute()
        self.assertEqual(result.parse_status, ParseStatus.FAILED)
        self.assertEqual(result.error.code, ErrorCode.PARSER_FAILURE)
        self.assertEqual(self.raw(result), b'{"bad_envelope":true}')

    def test_adapter_rejects_inconsistent_envelope_fields(self):
        obj = strict_json(self.generate())
        for key, value in (("schema_version", "future"), ("backend", "other"), ("model_id", "other"),
                           ("model_revision", "main"), ("input_token_count", True),
                           ("input_token_count", 99), ("continuation_ids", [9]),
                           ("generated_ids_full", [True]), ("decoded_for_parser", []),
                           ("runtime", []), ("effective_generation_config", [])):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.adapter.adapt(json.dumps({**obj, key: value}).encode(), Task.CLASSIFICATION)

    def test_adapter_rejects_duplicate_nonfinite_non_utf8_and_extra_fields(self):
        obj = strict_json(self.generate())
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'\xff',
                    json.dumps({**obj, "extra": 1}).encode(),
                    json.dumps({**obj, "runtime": {"x": float("inf")}}).encode()):
            with self.subTest(raw=raw[:50]), self.assertRaises((ValueError, UnicodeError)):
                self.adapter.adapt(raw, Task.CLASSIFICATION)

    def test_blocking_generation_failure_invents_no_partial(self):
        self.runtime.model.failure = RuntimeError("invented text is not model output")
        with self.assertRaises(GenerationFailure) as caught:
            self.generate()
        self.assertIsNone(caught.exception.partial_raw)
        self.assertNotIn("invented", str(caught.exception))

    def test_generation_failure_maps_without_storage_or_parser_retry(self):
        self.runtime.model.failure = RuntimeError()
        with patch.object(self.adapter, "adapt") as adapter, patch.object(self.store, "preserve") as store:
            result = self.execute()
        self.assertEqual(result.error.code, ErrorCode.GENERATION_FAILURE)
        self.assertEqual(result.parse_status, ParseStatus.NOT_ATTEMPTED)
        self.assertIsNone(result.raw_output)
        self.assertEqual(len(self.runtime.model.calls), 1)
        adapter.assert_not_called()
        store.assert_not_called()

    def test_generation_failure_does_not_contaminate_later_call(self):
        self.runtime.model.failure = RuntimeError()
        self.execute()
        self.assertIsNone(self.runtime.model.model.rope_deltas)
        self.assertIsNone(self.runtime.model._cache)
        self.runtime.model.failure = None
        self.assertIsNone(self.execute(ctx=context(call_id="b")).error)
        self.runtime.model_factory.from_pretrained.assert_called_once()

    def test_two_calls_have_no_history_image_state_or_config_mutation(self):
        state_keys = set(vars(self.runner))
        self.generate(req=request(prompt="call A"))
        self.runtime.model.continuation = [888]
        self.runtime.processor.input_ids = [44, 55]
        obj = strict_json(self.generate(req=request(prompt="call B")))
        self.assertEqual(obj["generated_ids_full"], [44, 55, 888])
        self.assertEqual([c["prompt"] for c in self.runtime.processor.calls], ["call A", "call B"])
        self.assertEqual(set(vars(self.runner)), state_keys)
        self.assertIsNone(self.runtime.model.model.rope_deltas)
        self.assertIsNone(self.runtime.model._cache)
        for call in self.runtime.model.calls:
            self.assertNotIn("past_key_values", call)
        self.assertIsNot(self.runtime.model.calls[0]["generation_config"],
                         self.runtime.model.calls[1]["generation_config"])

    def test_invalid_image_maps_to_preprocessing_failure(self):
        result = self.execute(req=request(input_bytes=b"not an image"))
        self.assertEqual(result.error.code, ErrorCode.PREPROCESSING_FAILURE)
        self.assertEqual(self.runtime.model.calls, [])
        self.assertIsNone(result.raw_output)

    def test_processor_exception_maps_to_preprocessing_failure(self):
        self.runtime.processor.failure = RuntimeError()
        self.assertEqual(self.execute().error.code, ErrorCode.PREPROCESSING_FAILURE)
        self.assertEqual(self.runtime.model.calls, [])

    def test_preprocessing_error_does_not_contaminate_next_call(self):
        self.runtime.processor.failure = RuntimeError()
        self.execute()
        self.runtime.processor.failure = None
        self.assertIsNone(self.execute(ctx=context(call_id="b")).error)
        self.runtime.model_factory.from_pretrained.assert_called_once()

    def test_decode_error_still_clears_native_per_image_state(self):
        with patch.object(self.runtime.processor, "batch_decode", side_effect=RuntimeError()):
            result = self.execute()
        self.assertEqual(result.error.code, ErrorCode.GENERATION_FAILURE)
        self.assertIsNone(self.runtime.model.model.rope_deltas)
        self.assertIsNone(self.runtime.model._cache)
        self.assertIsNone(self.execute(ctx=context(call_id="b")).error)

    def test_decompression_bomb_warning_fails_preprocessing(self):
        with patch.object(Image, "MAX_IMAGE_PIXELS", 4):
            result = self.execute()
        self.assertEqual(result.error.code, ErrorCode.PREPROCESSING_FAILURE)
        self.assertEqual(self.runtime.model.calls, [])

    def test_image_bytes_do_not_require_filesystem(self):
        req = request()
        with patch("builtins.open", side_effect=AssertionError("no disk input")):
            self.generate(req=req)

    def test_animated_image_rejected(self):
        stream = BytesIO()
        Image.new("RGB", (2, 2), "red").save(stream, format="GIF", save_all=True,
                                             append_images=[Image.new("RGB", (2, 2), "blue")])
        result = self.execute(req=request(input_bytes=stream.getvalue()))
        self.assertEqual(result.error.code, ErrorCode.PREPROCESSING_FAILURE)

    def test_precision_mapping_and_explicit_placement(self):
        for precision, dtype in (("FP32", "fake-fp32"), ("FP16", "fake-fp16"), ("BF16", "fake-bf16")):
            runtime = Runtime()
            runner = Qwen3VLRunner(backend_factory=runtime.factory)
            ctx = context(precision=precision, device={"placement": "cuda:7"})
            runner.initialize(ctx)
            runner.load(ctx)
            self.assertEqual(runtime.model_factory.from_pretrained.call_args.kwargs["dtype"], dtype)
            self.assertEqual(runtime.model_factory.from_pretrained.call_args.kwargs["device_map"], "cuda:7")

    def test_pending_or_unsupported_precision_quantization_or_device_fail(self):
        for changes in (dict(precision="PENDING"), dict(precision="auto"), dict(quantization="PENDING"),
                        dict(quantization="4-bit"), dict(device={"kind": "unspecified"}),
                        dict(preprocessing={"resize": 64})):
            runtime = Runtime()
            runner = Qwen3VLRunner(backend_factory=runtime.factory)
            ctx = context(**changes)
            runner.initialize(ctx)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                runner.load(ctx)
            runtime.processor_factory.from_pretrained.assert_not_called()

    def test_auto_placement_is_explicitly_forwarded_and_actual_device_recorded(self):
        obj = strict_json(self.generate(context(device={"placement": "auto"})))
        self.assertEqual(self.runtime.model_factory.from_pretrained.call_args.kwargs["device_map"], "auto")
        self.assertEqual(obj["runtime"]["device_map"], {"": "cpu"})

    def test_extra_generation_outputs_are_explicitly_rejected(self):
        for field, value in (("num_return_sequences", 2), ("return_dict_in_generate", True),
                             ("output_scores", True), ("output_logits", True),
                             ("output_attentions", True), ("output_hidden_states", True)):
            runtime = Runtime()
            setattr(runtime.model.generation_config, field, value)
            runner = Qwen3VLRunner(backend_factory=runtime.factory)
            runner.initialize(context())
            with self.subTest(field=field), self.assertRaises(ValueError):
                runner.load(context())
            self.assertIsNone(runner._resources)

    def test_lifecycle_methods_fail_if_resources_not_ready(self):
        with self.assertRaises(RuntimeError):
            self.runner.load(context())
        with self.assertRaises(RuntimeError):
            self.runner.prepare_input(request(), context())

    def test_runtime_and_w2_6a_provenance_record_condition(self):
        result = self.execute()
        obj = strict_json(self.raw(result))
        for key in ("device", "precision", "quantization", "software_versions"):
            self.assertEqual(result.provenance[key], getattr(context(), key))
        self.assertEqual(obj["runtime"]["software_versions"], VERSIONS)
        self.assertEqual(obj["runtime"]["input_device"], "cpu")
        self.assertEqual(obj["runtime"]["runner_version"], self.runner.version)
        self.assertEqual(result.provenance["immutable_revision"], REVISION)

    def test_import_and_fake_execution_do_not_require_ml_packages(self):
        script = '''
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'torch', 'transformers', 'huggingface_hub', 'qwen_vl_utils'}:
        raise AssertionError('unexpected ML import')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from safeshift.runners.qwen3_vl import Qwen3VLRunner
Qwen3VLRunner(backend_factory=lambda: None)
'''
        completed = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIsNone(self.execute().error)

    def test_native_import_failure_maps_to_initialization(self):
        self.runner = Qwen3VLRunner()
        result = self.execute()
        self.assertEqual(result.error.code, ErrorCode.INITIALIZATION_FAILURE)
        self.assertIsNone(result.raw_output)

    def test_no_dataset_provider_metric_or_backup_dependencies(self):
        source = Path("safeshift/runners/qwen3_vl.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any("metrics" in (name or "") or "provider" in (name or "") for name in imports))
        for forbidden in ("InspecSafe", "inspecsafe", "data/raw", "backup", "235B", "dashscope"):
            self.assertNotIn(forbidden, source)

    def test_incorrect_backend_prefix_fails_without_semantic_parse(self):
        with patch.object(self.runtime.model, "generate", return_value=Tensor([[9, 8, 7]])):
            result = self.execute()
        self.assertEqual(result.error.code, ErrorCode.GENERATION_FAILURE)
        self.assertIsNone(result.raw_output)


if __name__ == "__main__":
    unittest.main()
