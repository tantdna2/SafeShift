"""Offline Ovis structural contracts: fake backend, tiny in-memory images only."""

from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

from PIL import Image, __version__ as PILLOW_VERSION

from safeshift.protocol.schema import Classification, strict_json
from safeshift.runners.contracts import (
    ErrorCode, GenerationFailure, ParseStatus, Request, RunContext, SpatialKind,
    Task, execute_call,
)
from safeshift.runners.ovis2_5 import (
    BACKEND, ENVELOPE_VERSION, FAILURE_ENVELOPE_VERSION, MODEL_ID,
    RESOLVED_REPOSITORY_ID, REVISION, Ovis2_5Adapter, Ovis2_5Runner,
    OvisBackend, _decoding, parse_ovis_native_spatial_evidence,
)
from safeshift.runners.storage import FileRawStore


VERSIONS = {"torch": "fake-torch", "transformers": "fake-transformers",
            "pillow": PILLOW_VERSION}


def context(call_id="call-1", **changes):
    return replace(RunContext(
        run_id="unit-run", call_id=call_id,
        decoding={"enable_thinking": False, "enable_thinking_budget": False,
                  "max_new_tokens": 64, "do_sample": False},
        preprocessing={"mode": "official_preprocess_inputs"},
        precision="BF16", quantization="NONE", device={"placement": "cuda:0"},
        software_versions=VERSIONS, git_commit_sha="a" * 40,
        command="python -m unittest tests.test_ovis_runner", source_kind="synthetic",
    ), **changes)


def image_bytes(animated=False):
    output = BytesIO()
    image = Image.new("RGB", (2, 2), (12, 34, 56))
    if animated:
        image.save(output, format="GIF", save_all=True,
                   append_images=[Image.new("RGB", (2, 2), (78, 90, 12))])
    else:
        image.save(output, format="PNG")
    return output.getvalue()


def request(task=Task.CLASSIFICATION, input_bytes=None):
    return Request(task, "synthetic-1", "input-1", image_bytes() if input_bytes is None else input_bytes,
                   "prompt-1", "Return the required answer.")


class Tensor:
    def __init__(self, value):
        self.value = value

    def __len__(self):
        return len(self.value)

    def __getitem__(self, index):
        return Tensor(self.value[index])

    def tolist(self):
        return self.value

    def cuda(self):
        return self


class FakeTokenizer:
    def __init__(self, owner):
        self.owner = owner

    def decode(self, ids, skip_special_tokens):
        self.owner.decode_calls.append((ids, skip_special_tokens))
        if self.owner.fail_decode is skip_special_tokens:
            raise RuntimeError("private exception message")
        return ("<think>reason</think>" if not skip_special_tokens else "") + self.owner.text


class FakeModel:
    def __init__(self):
        self.text_tokenizer = FakeTokenizer(self)
        self.llm = SimpleNamespace(generation_config=SimpleNamespace(
            to_dict=lambda: {"eos_token_id": 42, "pad_token_id": 0}))
        self.text = '{"safety_level":"Level02"}'
        self.output = [[92, 93]]
        self.fail_generate = False
        self.fail_decode = None
        self.preprocess_calls = []
        self.generate_calls = []
        self.decode_calls = []
        self.cuda_calls = 0
        self.eval_calls = 0

    def cuda(self):
        self.cuda_calls += 1
        return self

    def eval(self):
        self.eval_calls += 1
        return self

    def preprocess_inputs(self, **kwargs):
        self.preprocess_calls.append(kwargs)
        return Tensor([[11, 12, 13]]), Tensor([1]), Tensor([2])

    def generate(self, **kwargs):
        self.generate_calls.append(kwargs)
        if self.fail_generate:
            raise RuntimeError("private exception message")
        return Tensor(self.output)


class FakeFactory:
    def __init__(self):
        self.calls = []
        self.models = []
        self.fail = False
        self.missing = None

    def from_pretrained(self, model_id, **kwargs):
        self.calls.append((model_id, kwargs))
        if self.fail:
            raise RuntimeError("load failure")
        model = FakeModel()
        if self.missing:
            setattr(model, self.missing, None)
        self.models.append(model)
        return model


class InferenceMode:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class OvisTests(unittest.TestCase):
    def setUp(self):
        self.factory = FakeFactory()
        self.backend_calls = 0

        def backend():
            self.backend_calls += 1
            return OvisBackend(SimpleNamespace(bfloat16="bf16", inference_mode=InferenceMode),
                               self.factory, VERSIONS)

        self.runner = Ovis2_5Runner(backend_factory=backend)
        self.adapter = Ovis2_5Adapter()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.store = FileRawStore(self.repo)

    def loaded(self, ctx=None):
        ctx = ctx or context()
        self.runner.initialize(ctx)
        self.runner.load(ctx)
        return ctx, self.factory.models[-1]

    def raw(self, ctx=None, req=None):
        ctx, model = self.loaded(ctx)
        prepared = self.runner.prepare_input(req or request(), ctx)
        return strict_json(self.runner.generate_raw(prepared, ctx)), model

    def execute(self, ctx=None, req=None):
        return execute_call(self.runner, self.adapter, self.store,
                            req or request(), ctx or context())

    def test_identity_loader_and_redirect_provenance(self):
        self.loaded()
        self.assertEqual(MODEL_ID, "AIDC-AI/Ovis2.5-9B")
        self.assertEqual(RESOLVED_REPOSITORY_ID, "ATH-MaaS/Ovis2.5-9B")
        self.assertEqual(REVISION, "d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd")
        self.assertEqual(self.factory.calls, [(MODEL_ID, {
            "revision": REVISION, "trust_remote_code": True,
            "local_files_only": True, "torch_dtype": "bf16",
        })])

    def test_import_is_lazy(self):
        code = "import sys; import safeshift.runners.ovis2_5; assert 'torch' not in sys.modules; assert 'transformers' not in sys.modules"
        result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_lifecycle_reuses_backend_and_model(self):
        ctx, model = self.loaded()
        self.runner.initialize(ctx)
        self.runner.load(ctx)
        self.assertEqual(self.backend_calls, 1)
        self.assertEqual(len(self.factory.calls), 1)
        self.assertEqual((model.cuda_calls, model.eval_calls), (1, 1))

    def test_changed_condition_fails_without_reloading(self):
        ctx, _ = self.loaded()
        for changed in (replace(ctx, device={"placement": "cuda:1"}),
                        replace(ctx, decoding={**ctx.decoding, "enable_thinking": True}),
                        replace(ctx, software_versions={**VERSIONS, "torch": "changed"})):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    self.runner.load(changed)
        self.assertEqual(len(self.factory.calls), 1)

    def test_failed_load_is_clean_and_retryable(self):
        ctx = context()
        self.runner.initialize(ctx)
        self.factory.fail = True
        with self.assertRaises(RuntimeError):
            self.runner.load(ctx)
        self.assertIsNone(self.runner._model)
        self.factory.fail = False
        self.runner.load(ctx)
        self.assertEqual(len(self.factory.calls), 2)

    def test_interface_rejected_without_fallback(self):
        for missing in ("preprocess_inputs", "generate", "text_tokenizer"):
            with self.subTest(missing=missing):
                self.factory.missing = missing
                ctx = context()
                self.runner = Ovis2_5Runner(backend_factory=lambda: OvisBackend(
                    SimpleNamespace(bfloat16="bf16", inference_mode=InferenceMode), self.factory, VERSIONS))
                self.runner.initialize(ctx)
                with self.assertRaises(ValueError):
                    self.runner.load(ctx)
                self.assertIsNone(self.runner._model)

    def test_runtime_conditions_reject_unsupported_values(self):
        for changes in ({"precision": "FP16"}, {"quantization": "8BIT"},
                        {"device": {"placement": "auto"}},
                        {"preprocessing": {"min_pixels": 4}}):
            with self.subTest(changes=changes):
                ctx = context(**changes)
                runner = Ovis2_5Runner(backend_factory=lambda: OvisBackend(
                    SimpleNamespace(bfloat16="bf16", inference_mode=InferenceMode), self.factory, VERSIONS))
                runner.initialize(ctx)
                with self.assertRaises(ValueError):
                    runner.load(ctx)

    def test_preprocessing_exact_messages_and_thinking(self):
        ctx = context(decoding={"enable_thinking": True, "enable_thinking_budget": True,
                                "thinking_budget": 32, "max_new_tokens": 64})
        raw, model = self.raw(ctx)
        call = model.preprocess_calls[0]
        self.assertEqual(call["messages"][0]["content"][1]["text"], request().prompt)
        self.assertEqual(call["messages"][0]["content"][0]["type"], "image")
        self.assertEqual((call["min_pixels"], call["max_pixels"]), (448**2, 1792**2))
        self.assertTrue(call["add_generation_prompt"])
        self.assertTrue(call["enable_thinking"])
        self.assertTrue(model.generate_calls[0]["enable_thinking"])
        self.assertTrue(model.generate_calls[0]["enable_thinking_budget"])
        self.assertEqual(raw["generation_kwargs"]["thinking_budget"], 32)

    def test_preprocess_rejects_malformed_and_animated_images(self):
        self.loaded()
        for payload in (b"not an image", image_bytes(animated=True)):
            with self.subTest(payload=payload[:8]):
                with self.assertRaises(Exception):
                    self.runner.prepare_input(request(input_bytes=payload), context())

    def test_decoding_validation(self):
        base = context().decoding
        bad = [
            {**base, "unknown": 1}, {**base, "enable_thinking": 1},
            {**base, "max_new_tokens": 0}, {**base, "temperature": float("nan")},
            {**base, "top_p": 1.1}, {**base, "top_k": -1},
            {**base, "enable_thinking_budget": True, "thinking_budget": 3},
            {**base, "thinking_budget": 3},
            {**base, "enable_thinking": True, "enable_thinking_budget": True,
             "thinking_budget": 39},
        ]
        for item in bad:
            with self.subTest(item=item):
                with self.assertRaises(ValueError):
                    _decoding(item)

    def test_native_ids_are_not_prompt_sliced_and_raw_is_deterministic(self):
        ctx, model = self.loaded()
        prepared = self.runner.prepare_input(request(), ctx)
        raw1 = self.runner.generate_raw(prepared, ctx)
        raw2 = self.runner.generate_raw(prepared, ctx)
        self.assertEqual(raw1, raw2)
        obj = strict_json(raw1)
        self.assertEqual(obj["input_ids"], [11, 12, 13])
        self.assertEqual(obj["native_generated_ids"], [92, 93])
        self.assertEqual(obj["decoded_with_special_tokens"],
                         '<think>reason</think>{"safety_level":"Level02"}')
        self.assertEqual(obj["decoded_for_parser"], '{"safety_level":"Level02"}')
        self.assertEqual(obj["schema_version"], ENVELOPE_VERSION)
        self.assertEqual(obj["backend"], BACKEND)
        self.assertEqual(obj["resolved_repository_id"], RESOLVED_REPOSITORY_ID)
        self.assertEqual(obj["effective_model_condition"]["native_llm_generation_defaults_before_call"],
                         {"eos_token_id": 42, "pad_token_id": 0})
        self.assertEqual(model.decode_calls, [([92, 93], False), ([92, 93], True)] * 2)

    def test_generate_failure_before_return_has_no_partial(self):
        ctx, model = self.loaded()
        prepared = self.runner.prepare_input(request(), ctx)
        model.fail_generate = True
        with self.assertRaises(GenerationFailure) as caught:
            self.runner.generate_raw(prepared, ctx)
        self.assertIsNone(caught.exception.partial_raw)

    def test_post_return_failures_preserve_observed_evidence(self):
        ctx, model = self.loaded()
        prepared = self.runner.prepare_input(request(), ctx)
        cases = [([[92, "bad"]], "TOKEN_VALIDATION", False, False),
                 ([[92, 93]], "DECODE_SPECIAL_TOKENS", False, False),
                 ([[92, 93]], "DECODE_FOR_PARSER", True, True)]
        for output, stage, fail_decode, has_special in cases:
            with self.subTest(stage=stage):
                model.output = output
                model.fail_decode = fail_decode
                with self.assertRaises(GenerationFailure) as caught:
                    self.runner.generate_raw(prepared, ctx)
                partial = strict_json(caught.exception.partial_raw)
                self.assertEqual(partial["schema_version"], FAILURE_ENVELOPE_VERSION)
                self.assertEqual(partial["post_generation_stage"], stage)
                self.assertIn("observed_native_generated_ids", partial)
                self.assertEqual("observed_special_decode" in partial, has_special)
                self.assertNotIn("private exception message", caught.exception.partial_raw.decode())

    def test_post_return_shape_failure_preserves_rows(self):
        ctx, model = self.loaded()
        model.output = [[92], [93]]
        prepared = self.runner.prepare_input(request(), ctx)
        with self.assertRaises(GenerationFailure) as caught:
            self.runner.generate_raw(prepared, ctx)
        partial = strict_json(caught.exception.partial_raw)
        self.assertEqual(partial["observed_native_generated_ids"], [[92], [93]])
        self.assertEqual(partial["post_generation_stage"], "ROW_VALIDATION")

    def test_generation_failure_never_calls_adapter(self):
        ctx, model = self.loaded()
        model.fail_generate = True

        class FailIfCalled:
            version = "spy-v1"
            parser_version = "spy-v1"

            def adapt(self, *_):
                raise AssertionError("adapter must not run")

        result = execute_call(self.runner, FailIfCalled(), self.store, request(), ctx)
        self.assertEqual(result.error.code, ErrorCode.GENERATION_FAILURE)
        self.assertIsNone(result.raw_output)

    def test_structural_adapter_failure_is_parser_failure_after_raw_preservation(self):
        class BrokenAdapter:
            version = "spy-v1"
            parser_version = "spy-v1"

            def adapt(self, *_):
                raise ValueError("invalid envelope")

        result = execute_call(self.runner, BrokenAdapter(), self.store, request(), context())
        self.assertEqual(result.error.code, ErrorCode.PARSER_FAILURE)
        self.assertIsNotNone(result.raw_output)
        self.assertTrue((self.repo / result.raw_output.path).is_file())

    def test_execute_preserves_before_adapter_and_classifies(self):
        result = self.execute()
        self.assertEqual(result.parse_status, ParseStatus.SUCCESS)
        self.assertEqual(result.canonical, Classification("Level02"))
        self.assertIsNone(result.error)
        raw = (self.repo / result.raw_output.path).read_bytes()
        self.assertEqual(strict_json(raw)["native_generated_ids"], [92, 93])

    def test_invalid_classification_and_grounding_firewall(self):
        ctx, model = self.loaded()
        model.text = "invalid"
        invalid = self.execute(ctx)
        self.assertEqual(invalid.parse_status, ParseStatus.INVALID)
        self.assertEqual(invalid.error.code, ErrorCode.INVALID_CLASSIFICATION)
        model.text = "<box>(0.1,0.2),(0.8,0.9)</box>"
        grounding = self.execute(context("call-2"), request(Task.GROUNDING))
        self.assertEqual(grounding.parse_status, ParseStatus.UNSUPPORTED)
        self.assertEqual(grounding.spatial_kind, SpatialKind.NONE)
        self.assertIsNone(grounding.canonical)
        self.assertEqual(grounding.error.code, ErrorCode.UNSUPPORTED_GROUNDING)
        self.assertEqual(grounding.native_evidence["qualification"], "NOT_YET_QUALIFIED")
        self.assertEqual(grounding.native_evidence["native_candidates"][0]["kind"], "box")

    def test_adapter_rejects_invalid_envelope(self):
        obj, _ = self.raw()
        for change in ({"model_id": "other"}, {"unknown": 1},
                       {"input_token_count": 99}, {"native_generated_ids": [True]}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    self.adapter.adapt(json.dumps({**obj, **change}).encode(), Task.CLASSIFICATION)

    def test_executor_failure_and_storage_failure(self):
        ctx, model = self.loaded()
        model.fail_decode = False
        result = self.execute(ctx)
        self.assertEqual(result.error.code, ErrorCode.GENERATION_FAILURE)
        self.assertEqual(result.parse_status, ParseStatus.NOT_ATTEMPTED)
        self.assertIsNotNone(result.raw_output)
        class BrokenStore:
            def preserve(self, *_):
                raise OSError("disk unavailable")
        result = execute_call(self.runner, self.adapter, BrokenStore(), request(), context("call-2"))
        self.assertEqual(result.error.code, ErrorCode.RAW_PRESERVATION_FAILURE)

    def test_two_calls_keep_only_model_resource(self):
        first = self.execute(context("call-1"))
        second = self.execute(context("call-2"), request(Task.GROUNDING))
        self.assertIsNotNone(first.raw_output)
        self.assertIsNotNone(second.raw_output)
        self.assertEqual(len(self.factory.calls), 1)
        self.assertEqual(self.backend_calls, 1)
        self.assertEqual(set(vars(self.runner)), {"_backend_factory", "_backend", "_condition", "_model"})
        messages = [call["messages"] for call in self.factory.models[0].preprocess_calls]
        self.assertIsNot(messages[0], messages[1])

    def test_native_spatial_helper_is_strict_and_not_canonical(self):
        parse = parse_ovis_native_spatial_evidence
        self.assertEqual([item["kind"] for item in parse(
            "<point>(0.1,0.2)</point>\n<box>(0.1,0.2),(0.8,0.9)</box>")],
                         ["point", "box"])
        self.assertEqual(len(parse("[<box>(0.1,0.2),(0.8,0.9)</box>,"
                                   " <point>(0.4,0.5)</point> ]")), 2)
        for bad in ("0.1 0.2 0.8 0.9", "here <point>(0.1,0.2)</point>",
                    "<point>(-0.1,0.2)</point>", "<point>(1,0.2)</point>",
                    "<point>(nan,0.2)</point>", "<box>(0.8,0.2),(0.1,0.9)</box>",
                    "<box>(0.1,0.9),(0.8,0.2)</box>", "<point>(0.1,0.2)",
                    "[<point>(0.1,0.2)</point>,]"):
            with self.subTest(bad=bad):
                self.assertEqual(parse(bad), [])


if __name__ == "__main__":
    unittest.main()
