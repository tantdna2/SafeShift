"""Molmo offline contracts: fake ML objects and tiny in-memory images only."""

import builtins
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image, __version__ as PILLOW_VERSION

from safeshift.protocol import PARSER_VERSION
from safeshift.protocol.schema import Classification, parse_text
from safeshift.runners import molmo2_o as molmo
from safeshift.runners.contracts import (
    ErrorCode, GenerationFailure, ParseStatus, Participation, Request, Roles,
    RunContext, SpatialKind, Task, execute_call,
)
from safeshift.runners.storage import FileRawStore


VERSIONS = {"python": "3.11.fake", "torch": "fake-torch", "transformers": "4.57.1",
            "pillow": PILLOW_VERSION, "huggingface_hub": "fake-hub"}


def context(**changes):
    return replace(RunContext(
        run_id="offline-molmo-contract", call_id="call-1",
        decoding={"max_new_tokens": 32, "do_sample": False},
        preprocessing={"mode": "official_processor"}, precision="FP32", quantization="NONE",
        device={"placement": "auto"}, software_versions=deepcopy(VERSIONS),
        git_commit_sha="8f121eda1485c5984e8f9cde6944388ac7b7c351",
        command="python -m unittest tests.test_molmo_runner -v", source_kind="handcrafted_dummy",
    ), **changes)


def image_bytes(mode="RGB", animated=False):
    stream = BytesIO()
    image = Image.new(mode, (2, 3))
    if animated:
        image.save(stream, format="GIF", save_all=True,
                   append_images=[Image.new("RGB", (2, 3), "white")])
    else:
        image.save(stream, format="PNG")
    return stream.getvalue()


def request(**changes):
    return replace(Request(Task.CLASSIFICATION, "tiny-fixture", "memory-image", image_bytes(),
                           "caller-prompt", "Caller text: tiếng Việt\n"), **changes)


class Tensor:
    def __init__(self, data):
        self.data = deepcopy(data)
        self.devices = []

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return Tensor(self.data[index])

    def tolist(self):
        return deepcopy(self.data)

    def to(self, device):
        self.devices.append(device)
        return self


class Processor:
    def __init__(self):
        self.calls = []
        self.input_ids = [[11, 22, 33]]
        self.text = '{"safety_level":"Level04"}'
        self.tokenizer = SimpleNamespace(decode=Mock(side_effect=self.decode))
        self.extra_inputs = {}

    def apply_chat_template(self, messages, **kwargs):
        image = messages[0]["content"][1]["image"]
        self.calls.append({"role": messages[0]["role"], "messages_count": len(messages),
                           "content_count": len(messages[0]["content"]),
                           "prompt": messages[0]["content"][0]["text"],
                           "mode": image.mode, "size": image.size, "kwargs": kwargs})
        return {"input_ids": Tensor(self.input_ids), "pixel_values": Tensor([[9]]),
                "image_grids": Tensor([[1, 2, 3, 4]]), **self.extra_inputs}

    def decode(self, ids, *, skip_special_tokens, clean_up_tokenization_spaces):
        return self.text if skip_special_tokens else "<control>" + self.text + "<end>"


class GenerationConfig:
    def __init__(self):
        self.num_return_sequences = 1
        self.return_dict_in_generate = False
        self.output_scores = False
        self.output_logits = False
        self.output_attentions = False
        self.output_hidden_states = False
        self.cache_implementation = None
        self.eos_token_id = 100257

    def to_dict(self):
        return deepcopy(vars(self))


class Model:
    device = "fake-device"

    def __init__(self, runtime, snapshot):
        self.runtime = runtime
        self.config = SimpleNamespace(name_or_path=str(snapshot))
        self.generation_config = GenerationConfig()
        self.eval = Mock()
        self.generate = Mock(side_effect=self.generate_impl)

    def generate_impl(self, **kwargs):
        assert self.runtime.inference_active
        assert "past_key_values" not in kwargs
        kwargs["generation_config"].eos_token_id = 999  # Must be an isolated copy.
        return Tensor([kwargs["input_ids"][0].tolist() + [701, 702]])


class Runtime:
    def __init__(self, snapshot):
        self.inference_active = False
        self.processor = Processor()
        self.model = Model(self, snapshot)
        self.processor_factory = SimpleNamespace(from_pretrained=Mock(return_value=self.processor))
        self.model_factory = SimpleNamespace(from_pretrained=Mock(return_value=self.model))
        self.resolver = Mock(return_value=str(snapshot))
        self.offline_check = Mock()
        self.torch = SimpleNamespace(float32="fake-fp32", bfloat16="fake-bf16", float16="fake-fp16",
                                     inference_mode=self.inference_mode)
        self.backend = molmo.MolmoBackend(self.torch, self.processor_factory, self.model_factory,
                                         VERSIONS, self.resolver, self.offline_check)
        self.factory = Mock(return_value=self.backend)

    @contextmanager
    def inference_mode(self):
        self.inference_active = True
        try:
            yield
        finally:
            self.inference_active = False


class MolmoRunnerTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
                       "socket.socket.sendto", "socket.getaddrinfo"):
            self.enterContext(patch(target, side_effect=AssertionError("network forbidden")))
        self.original_import = builtins.__import__

        def offline_import(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "huggingface_hub", "molmo_utils"}:
                raise AssertionError("real ML import forbidden")
            return self.original_import(name, *args, **kwargs)

        self.enterContext(patch("builtins.__import__", side_effect=offline_import))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.snapshot = self.root / molmo.SNAPSHOT_REPOSITORY_DIR / "snapshots" / molmo.REVISION
        self.snapshot.mkdir(parents=True)
        self.runtime = Runtime(self.snapshot)
        self.runner = molmo.Molmo2ORunner(backend_factory=self.runtime.factory)
        self.adapter = molmo.Molmo2OAdapter()
        self.store = FileRawStore(self.root)

    def prepared(self, ctx=None):
        ctx = ctx or context()
        self.runner.initialize(ctx)
        self.runner.load(ctx)
        return self.runner.prepare_input(request(), ctx)

    def raw(self):
        return self.runner.generate_raw(self.prepared(), context())

    def execute(self, **kwargs):
        return execute_call(self.runner, kwargs.get("adapter", self.adapter), self.store,
                            kwargs.get("req", request()), kwargs.get("ctx", context()))

    def failure(self, prepared=None):
        with self.assertRaises(GenerationFailure) as caught:
            self.runner.generate_raw(prepared or self.prepared(), context())
        raw = caught.exception.partial_raw
        self.assertIsInstance(raw, bytes)
        obj = json.loads(raw)
        self.assertEqual(obj["schema_version"], molmo.FAILURE_ENVELOPE_VERSION)
        self.assertEqual(obj["generation_observation_status"], "RETURNED_NATIVE_OUTPUT")
        self.assertNotIn("private error", raw.decode())
        return obj

    def test_import_is_lazy_in_fresh_process(self):
        script = """
import builtins, socket
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'torch', 'transformers', 'huggingface_hub', 'PIL', 'molmo_utils'}:
        raise AssertionError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
def deny(*args, **kwargs):
    raise AssertionError('network')
socket.socket.connect = socket.create_connection = socket.getaddrinfo = deny
from safeshift.runners.molmo2_o import Molmo2ORunner
Molmo2ORunner()
"""
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_exact_identity(self):
        self.assertEqual(self.runner.identity.model_id, "allenai/Molmo2-O-7B")
        self.assertEqual(self.runner.identity.immutable_revision, "784410650d12be9bc086118fdefa32d2c3bced86")
        self.assertEqual(self.runner.identity.revision_evidence,
                         "configs/pre_freeze/local_model_provenance.d9.json#molmo2_o_7b")
        self.assertEqual(self.runner.version, "molmo2-o-runner-v1")

    def test_same_exact_local_snapshot_and_loader_arguments(self):
        self.prepared()
        self.runtime.resolver.assert_called_once_with(repo_id=molmo.MODEL_ID,
                                                      revision=molmo.REVISION, local_files_only=True)
        for factory in (self.runtime.processor_factory, self.runtime.model_factory):
            factory.from_pretrained.assert_called_once_with(
                str(self.snapshot), revision=molmo.REVISION, trust_remote_code=True,
                local_files_only=True, dtype="fake-fp32", device_map="auto")

    def test_wrong_repo_revision_relative_url_and_missing_snapshot_rejected(self):
        for path in (self.root / "models--wrong--repo" / "snapshots" / molmo.REVISION,
                     self.snapshot.parent / "main", self.snapshot.parent / ("a" * 40),
                     "relative/snapshots/" + molmo.REVISION, "https://example.invalid/snapshot",
                     self.root / "missing" / molmo.SNAPSHOT_REPOSITORY_DIR / "snapshots" / molmo.REVISION):
            with self.subTest(path=str(path)), self.assertRaises((ValueError, FileNotFoundError)):
                molmo._validate_local_snapshot(path)

    def test_resolved_alias_wrong_repository_rejected(self):
        with patch.object(Path, "resolve", return_value=self.root):
            with self.assertRaisesRegex(ValueError, "resolved snapshot"):
                molmo._validate_local_snapshot(self.snapshot)

    def test_wrong_model_config_snapshot_rejected(self):
        self.runtime.model.config.name_or_path = molmo.MODEL_ID
        self.runner.initialize(context())
        with self.assertRaises(ValueError):
            self.runner.load(context())
        self.assertIsNone(self.runner._resources)

    def test_initialize_and_load_idempotent(self):
        self.prepared()
        self.prepared()
        self.runtime.factory.assert_called_once()
        self.runtime.resolver.assert_called_once()
        self.runtime.model_factory.from_pretrained.assert_called_once()
        self.runtime.model.eval.assert_called_once()

    def test_initialize_version_failure_retry_publishes_no_state(self):
        with self.assertRaisesRegex(ValueError, "actual runtime version"):
            self.runner.initialize(context(software_versions={"torch": "wrong"}))
        self.assertIsNone(self.runner._backend)
        self.assertIsNone(self.runner._condition)
        self.runner.initialize(context())
        self.assertIsNotNone(self.runner._backend)

    def test_initialize_factory_failure_retry(self):
        self.runtime.factory.side_effect = [RuntimeError("failure"), self.runtime.backend]
        with self.assertRaises(RuntimeError):
            self.runner.initialize(context())
        self.runner.initialize(context())
        self.assertEqual(self.runtime.factory.call_count, 2)

    def test_load_failure_retry(self):
        self.runtime.model_factory.from_pretrained.side_effect = [RuntimeError("failure"), self.runtime.model]
        self.runner.initialize(context())
        with self.assertRaises(RuntimeError):
            self.runner.load(context())
        self.assertIsNone(self.runner._resources)
        self.runner.load(context())
        self.assertIsNotNone(self.runner._resources)

    def test_resolver_failure_retry_without_loader_calls(self):
        self.runtime.resolver.side_effect = [FileNotFoundError(), str(self.snapshot)]
        self.runner.initialize(context())
        with self.assertRaises(FileNotFoundError):
            self.runner.load(context())
        self.runtime.model_factory.from_pretrained.assert_not_called()
        self.runner.load(context())

    def test_eval_failure_retry(self):
        self.runtime.model.eval.side_effect = [RuntimeError(), None]
        self.runner.initialize(context())
        with self.assertRaises(RuntimeError):
            self.runner.load(context())
        self.assertIsNone(self.runner._resources)
        self.runner.load(context())

    def test_changed_conditions_rejected_at_all_entry_points(self):
        prepared = self.prepared()
        for changes in ({"precision": "BF16"}, {"quantization": "INT8"},
                        {"device": {"placement": "cpu"}}, {"software_versions": {}},
                        {"preprocessing": {}}):
            ctx = context(**changes)
            for action in (lambda: self.runner.initialize(ctx), lambda: self.runner.load(ctx),
                           lambda: self.runner.prepare_input(request(), ctx),
                           lambda: self.runner.generate_raw(prepared, ctx)):
                with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "condition changed"):
                    action()

    def test_changed_identity_and_runner_version_rejected(self):
        self.prepared()
        for identity in (replace(molmo.IDENTITY, model_id="wrong"),
                         replace(molmo.IDENTITY, immutable_revision="b" * 40)):
            with patch.object(self.runner, "identity", identity), self.assertRaises(ValueError):
                self.runner.load(context())
        with patch.object(self.runner, "version", "changed"), self.assertRaises(ValueError):
            self.runner.load(context())

    def test_explicit_precision_support(self):
        for precision, dtype in (("FP32", "fake-fp32"), ("BF16", "fake-bf16"), ("FP16", "fake-fp16")):
            with self.subTest(precision=precision):
                runner = molmo.Molmo2ORunner(backend_factory=self.runtime.factory)
                ctx = context(precision=precision)
                runner.initialize(ctx)
                runner.load(ctx)
                self.assertEqual(self.runtime.model_factory.from_pretrained.call_args.kwargs["dtype"], dtype)

    def test_unsupported_precision_quantization_device_preprocessing(self):
        for changes in ({"precision": "auto"}, {"precision": "INT8"}, {"quantization": "INT4"},
                        {"device": {"placement": "cpu"}}, {"device": {"placement": "cuda:0"}},
                        {"device": {"placement": "auto", "custom_shard": True}},
                        {"preprocessing": {"resize": [224, 224]}}):
            runner = molmo.Molmo2ORunner(backend_factory=self.runtime.factory)
            ctx = context(**changes)
            runner.initialize(ctx)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                runner.load(ctx)
        self.runtime.resolver.assert_not_called()

    def test_missing_native_offline_environment_fails_before_ml_imports(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ValueError, "HF_HUB_OFFLINE"):
            molmo._native_backend()

    def test_offline_policy_rechecked_after_load(self):
        prepared = self.prepared()
        self.runtime.offline_check.side_effect = ValueError("offline flags changed")
        with self.assertRaisesRegex(ValueError, "offline flags"):
            self.runner.generate_raw(prepared, context())
        self.runtime.model.generate.assert_not_called()

    def native_stubs(self):
        """Exercise lazy native wiring using fake modules, never installed ML."""
        hub = SimpleNamespace(snapshot_download=self.runtime.resolver, __version__="fake-hub",
                              constants=SimpleNamespace(HF_HUB_OFFLINE=True, HF_HUB_DISABLE_TELEMETRY=True))
        transformers = SimpleNamespace(__version__="4.57.1",
                                       AutoProcessor=self.runtime.processor_factory,
                                       AutoModelForImageTextToText=self.runtime.model_factory)
        utils = SimpleNamespace(is_offline_mode=Mock(return_value=True))
        torch = SimpleNamespace(__version__="fake-torch")
        modules = {"torch": torch, "transformers": transformers,
                   "transformers.utils": utils, "huggingface_hub": hub}

        def fake_import(name, *args, **kwargs):
            if name in modules:
                return modules[name]
            return self.original_import(name, *args, **kwargs)

        self.enterContext(patch("builtins.__import__", side_effect=fake_import))
        self.enterContext(patch.dict(os.environ, {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                                                 "HF_HUB_DISABLE_TELEMETRY": "1"}))
        return hub, transformers, utils

    def test_native_backend_uses_documented_classes_without_loading(self):
        self.native_stubs()
        backend = molmo._native_backend()
        self.assertIs(backend.processor_factory, self.runtime.processor_factory)
        self.assertIs(backend.model_factory, self.runtime.model_factory)
        self.assertIs(backend.snapshot_resolver, self.runtime.resolver)
        self.assertEqual(backend.software_versions["transformers"], "4.57.1")
        self.runtime.resolver.assert_not_called()
        self.runtime.model_factory.from_pretrained.assert_not_called()

    def test_native_backend_rejects_stale_hf_offline_flags(self):
        hub, _, utils = self.native_stubs()
        for target, field, value in ((hub.constants, "HF_HUB_OFFLINE", False),
                                      (hub.constants, "HF_HUB_DISABLE_TELEMETRY", False),
                                      (utils, "is_offline_mode", lambda: False)):
            with patch.object(target, field, value), self.assertRaisesRegex(ValueError, "restart"):
                molmo._native_backend()

    def test_native_backend_rejects_wrong_documentary_software(self):
        _, transformers, _ = self.native_stubs()
        with patch.object(transformers, "__version__", "5.0.0"), self.assertRaisesRegex(ValueError, "4.57.1"):
            molmo._native_backend()
        with patch.object(molmo.platform, "python_version_tuple", return_value=("3", "12", "0")), \
                self.assertRaisesRegex(ValueError, "Python 3.11"):
            molmo._native_backend()

    def test_official_processor_path_rgb_prompt_and_device(self):
        self.prepared()
        prepared = self.runner.prepare_input(request(input_bytes=image_bytes("RGBA")), context())
        self.assertEqual(self.runtime.processor.calls[-1], {
            "role": "user", "messages_count": 1, "content_count": 2, "prompt": request().prompt,
            "mode": "RGB", "size": (2, 3), "kwargs": {"tokenize": True,
            "add_generation_prompt": True, "return_dict": True, "return_tensors": "pt"}})
        for tensor in prepared.inputs.values():
            self.assertEqual(tensor.devices, ["fake-device"])

    def test_multiframe_and_bad_images_rejected(self):
        self.prepared()
        for data in (image_bytes(animated=True), b"not an image"):
            with self.subTest(data=data[:10]), self.assertRaises((ValueError, OSError)):
                self.runner.prepare_input(request(input_bytes=data), context())

    def test_no_image_temp_file(self):
        self.runner.initialize(context())
        self.runner.load(context())
        req = request()
        with patch("PIL.Image.Image.save", side_effect=AssertionError("no image writes")), \
                patch("tempfile.NamedTemporaryFile", side_effect=AssertionError("no temp image")):
            self.runner.prepare_input(req, context())

    def test_bad_input_tokens_and_history_rejected(self):
        self.prepared()
        for ids in ([], [[]], [[True]], [[-1]], [[1.5]], [[1], [2]]):
            self.runtime.processor.input_ids = ids
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.runner.prepare_input(request(), context())
        self.runtime.processor.input_ids = [[11, 22, 33]]
        self.runtime.processor.extra_inputs = {"past_key_values": Tensor([9])}
        with self.assertRaisesRegex(ValueError, "independent input"):
            self.runner.prepare_input(request(), context())

    def test_two_calls_reuse_model_without_history_or_config_mutation(self):
        first = self.execute()
        second = self.execute(req=request(prompt="Second caller text"), ctx=context(call_id="call-2"))
        self.assertEqual(first.parse_status, ParseStatus.SUCCESS)
        self.assertEqual(second.parse_status, ParseStatus.SUCCESS)
        self.runtime.model_factory.from_pretrained.assert_called_once()
        self.assertEqual(self.runtime.model.generate.call_count, 2)
        self.assertEqual([c["prompt"] for c in self.runtime.processor.calls],
                         [request().prompt, "Second caller text"])
        self.assertEqual(self.runtime.model.generation_config.eos_token_id, 100257)

    def test_raw_ids_prefix_continuation_and_identity(self):
        obj = json.loads(self.raw())
        self.assertEqual(obj["input_ids"], [11, 22, 33])
        self.assertEqual(obj["generated_ids_full"], [11, 22, 33, 701, 702])
        self.assertEqual(obj["continuation_ids"], [701, 702])
        self.assertEqual(obj["input_token_count"], 3)
        self.assertEqual(obj["schema_version"], molmo.ENVELOPE_VERSION)
        self.assertEqual(obj["backend"], molmo.BACKEND)
        self.assertEqual(obj["runner_version"], self.runner.version)
        self.assertEqual(obj["model_id"], molmo.MODEL_ID)
        self.assertEqual(obj["model_revision"], molmo.REVISION)
        self.assertNotIn(str(self.root), json.dumps(obj))

    def test_both_decodes_use_only_continuation(self):
        obj = json.loads(self.raw())
        self.assertEqual(obj["decoded_for_parser"], self.runtime.processor.text)
        self.assertEqual(obj["decoded_with_special_tokens"], "<control>" + self.runtime.processor.text + "<end>")
        calls = self.runtime.processor.tokenizer.decode.call_args_list
        self.assertEqual([c.args for c in calls], [([701, 702],), ([701, 702],)])
        self.assertEqual([c.kwargs for c in calls], [
            {"skip_special_tokens": False, "clean_up_tokenization_spaces": False},
            {"skip_special_tokens": True, "clean_up_tokenization_spaces": False}])

    def test_actual_generation_kwargs_and_native_defaults_recorded(self):
        settings = {"max_new_tokens": 8, "do_sample": True, "temperature": 0.6,
                    "top_p": 0.9, "top_k": 4, "repetition_penalty": 1.1}
        ctx = context(decoding=settings)
        obj = json.loads(self.runner.generate_raw(self.prepared(ctx), ctx))
        self.assertEqual(obj["generation_kwargs"], settings)
        for key, value in settings.items():
            self.assertEqual(self.runtime.model.generate.call_args.kwargs[key], value)
        self.assertEqual(obj["effective_generation_config"]["eos_token_id"], 100257)

    def test_invalid_generation_values(self):
        bad = {"do_sample": [0, 1, "false", None], "temperature": [True, 0, -1, float("nan"), float("inf")],
               "top_p": [False, 0, 1.1, float("-inf")], "top_k": [True, -1, 1.5],
               "max_new_tokens": [False, 0, -1, 2.5], "repetition_penalty": [True, 0, float("nan")]}
        for key, values in bad.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    molmo._decoding({"max_new_tokens": 8, key: value})
        for values in ({}, {"max_new_tokens": 8, "num_beams": 2}, {"max_new_tokens": 8, "seed": 1}):
            with self.assertRaises(ValueError):
                molmo._decoding(values)

    def test_seed_rejected_in_load_prepare_and_generate(self):
        prepared = self.prepared()
        for action in (lambda: self.runner.prepare_input(request(), context(seed=0)),
                       lambda: self.runner.generate_raw(prepared, context(seed=0))):
            with self.assertRaisesRegex(ValueError, "seed"):
                action()
        runner = molmo.Molmo2ORunner(backend_factory=self.runtime.factory)
        runner.initialize(context(seed=0))
        with self.assertRaisesRegex(ValueError, "seed"):
            runner.load(context(seed=0))

    def test_foreign_prepared_condition_rejected(self):
        prepared = replace(self.prepared(), condition=b"other")
        with self.assertRaisesRegex(ValueError, "another execution condition"):
            self.runner.generate_raw(prepared, context())

    def test_unsupported_generation_output_and_cache_configs(self):
        for key, value in (("num_return_sequences", 2), ("return_dict_in_generate", True),
                           ("output_scores", True), ("cache_implementation", "static")):
            with patch.object(self.runtime.model.generation_config, key, value), self.assertRaises(ValueError):
                molmo.Molmo2ORunner._generation_config(self.runtime.model)

    def test_generate_exception_before_return_has_no_partial(self):
        self.runtime.model.generate.side_effect = RuntimeError("private error")
        prepared = self.prepared()
        with self.assertRaises(GenerationFailure) as caught:
            self.runner.generate_raw(prepared, context())
        self.assertIsNone(caught.exception.partial_raw)

    def test_oom_does_not_retry_fallback_or_reload(self):
        self.runtime.model.generate.side_effect = MemoryError("OOM")
        result = self.execute()
        self.assertEqual(result.error.code, ErrorCode.GENERATION_FAILURE)
        self.assertIsNone(result.raw_output)
        self.runtime.model.generate.assert_called_once()
        self.runtime.model_factory.from_pretrained.assert_called_once()

    def test_malformed_generated_rows_preserved(self):
        prepared = self.prepared()
        for rows in ([], [1, 2], [[1], [2]], [[11, 22, 33, -1]], [[11, 22, 33, 1.5]]):
            self.runtime.model.generate.side_effect = lambda **kw: Tensor(rows)
            with self.subTest(rows=rows):
                obj = self.failure(prepared)
                self.assertEqual(obj["observed_generated_ids"], rows)

    def test_bool_generated_ids_preserved_and_rejected(self):
        self.runtime.model.generate.side_effect = lambda **kw: Tensor([[11, 22, 33, True]])
        obj = self.failure()
        self.assertEqual(obj["observed_generated_ids"], [[11, 22, 33, True]])
        self.assertEqual(obj["post_generation_stage"], "TOKEN_VALIDATION")

    def test_nonfinite_generated_ids_have_labelled_diagnostics(self):
        prepared = self.prepared()
        for value in (float("nan"), float("inf"), float("-inf")):
            self.runtime.model.generate.side_effect = lambda **kw: Tensor([[11, 22, 33, value]])
            obj = self.failure(prepared)
            self.assertEqual(obj["observed_generated_ids_diagnostic"],
                             [[11, 22, 33, {"nonfinite_float": str(value)}]])
            self.assertNotIn("generated_ids_full", obj)

    def test_prefix_mismatch_and_short_output_not_silently_sliced(self):
        prepared = self.prepared()
        for row in ([11, 22], [99, 22, 33, 701]):
            self.runtime.model.generate.side_effect = lambda **kw: Tensor([row])
            obj = self.failure(prepared)
            self.assertEqual(obj["generated_ids_full"], row)
            self.assertNotIn("continuation_ids", obj)

    def test_tolist_failure_still_records_returned_native_output(self):
        self.runtime.model.generate.side_effect = lambda **kw: SimpleNamespace(
            tolist=Mock(side_effect=RuntimeError("private error")))
        obj = self.failure()
        self.assertEqual(obj["input_ids"], [11, 22, 33])
        self.assertEqual(obj["post_generation_stage"], "TOKEN_OBSERVATION")

    def test_decode_failures_preserve_tokens_and_prior_decode(self):
        prepared = self.prepared()
        for outputs in ([RuntimeError("private error")], ["special evidence", RuntimeError("private error")]):
            self.runtime.processor.tokenizer.decode.side_effect = outputs
            obj = self.failure(prepared)
            self.assertEqual(obj["generated_ids_full"], [11, 22, 33, 701, 702])
            self.assertEqual(obj["continuation_ids"], [701, 702])
            if len(outputs) == 2:
                self.assertEqual(obj["observed_special_decode"], "special evidence")

    def test_nonstring_decode_preserved_and_rejected(self):
        self.runtime.processor.tokenizer.decode.side_effect = [["unexpected"]]
        obj = self.failure()
        self.assertEqual(obj["observed_special_decode"], ["unexpected"])

    def test_serialization_failure_preserves_tokens_and_both_decodes(self):
        prepared = self.prepared()
        original = molmo._json_bytes

        def fail_envelope(value):
            if value.get("schema_version") == molmo.ENVELOPE_VERSION:
                raise TypeError("private error")
            return original(value)

        with patch.object(molmo, "_json_bytes", side_effect=fail_envelope):
            obj = self.failure(prepared)
        self.assertEqual(obj["post_generation_stage"], "SERIALIZATION")
        self.assertEqual(obj["observed_parser_decode"], self.runtime.processor.text)
        self.assertEqual(obj["generated_ids_full"], [11, 22, 33, 701, 702])

    def test_lone_surrogate_serialization_failure_preserves_observed_text(self):
        self.runtime.processor.text = "\ud800"
        obj = self.failure()
        self.assertEqual(obj["observed_parser_decode"], "\ud800")

    def test_raw_persisted_before_parse_text(self):
        def parse_after_preservation(text, task):
            self.assertTrue(list(self.root.rglob("*.raw")))
            return parse_text(text, task)

        with patch.object(molmo, "parse_text", side_effect=parse_after_preservation) as parser:
            result = self.execute()
        parser.assert_called_once_with(self.runtime.processor.text, "classification")
        self.assertEqual(result.canonical, Classification("Level04"))
        self.assertEqual(self.adapter.parser_version, molmo.ENVELOPE_VERSION + "/" + PARSER_VERSION)

    def test_partial_failure_persisted_without_adapter(self):
        self.runtime.processor.tokenizer.decode.side_effect = RuntimeError("private error")
        with patch.object(self.adapter, "adapt") as adapter:
            result = self.execute()
        adapter.assert_not_called()
        self.assertEqual(result.error.code, ErrorCode.GENERATION_FAILURE)
        obj = json.loads((self.root / result.raw_output.path).read_bytes())
        self.assertEqual(obj["observed_generated_ids"], [[11, 22, 33, 701, 702]])

    def test_adapter_failure_keeps_raw(self):
        with patch.object(self.adapter, "adapt", side_effect=ValueError("private error")):
            result = self.execute()
        self.assertEqual(result.error.code, ErrorCode.PARSER_FAILURE)
        self.assertTrue((self.root / result.raw_output.path).is_file())

    def test_classification_invalid_uses_existing_parser(self):
        self.runtime.processor.text = "arbitrary prose"
        result = self.execute()
        self.assertEqual(result.error.code, ErrorCode.INVALID_CLASSIFICATION)

    def test_native_points_preserved_without_box_or_canonical_success(self):
        for text in ('<points coords="1 1 500 750"/>', '<points coords="NaN Inf"/>',
                     "prose (0.5, 0.7)", '{"boxes":[[0,0,1,1]]}'):
            self.runtime.processor.text = text
            raw = self.raw()
            obj = json.loads(raw)
            self.assertEqual(obj["decoded_for_parser"], text)
            adapted = self.adapter.adapt(raw, Task.GROUNDING)  # Fake raw only; no grounding inference.
            adapted.validate(Task.GROUNDING)
            self.assertEqual(adapted.parse_status, ParseStatus.UNSUPPORTED)
            self.assertEqual(adapted.spatial_kind, SpatialKind.NONE)
            self.assertIsNone(adapted.value)
            self.assertEqual(adapted.native_evidence, {
                "interface_status": "DOCUMENTED_NATIVE_POINT", "qualification": "NOT_YET_QUALIFIED",
                "box_iou_participation": "NOT_PARTICIPATING", "native_text": text})

    def test_grounding_status_does_not_disable_classification(self):
        result = self.execute(ctx=context(roles=Roles(classification=Participation.PARTICIPATING,
                                                      grounding=Participation.NOT_PARTICIPATING)))
        self.assertEqual(result.parse_status, ParseStatus.SUCCESS)
        self.assertEqual(result.participation, Participation.PARTICIPATING)

    def test_adapter_rejects_tampered_envelope(self):
        original = json.loads(self.raw())
        for key, value in (("model_id", "wrong"), ("model_revision", "main"),
                           ("runner_version", "wrong"), ("input_token_count", True),
                           ("input_ids", [99, 22, 33]), ("continuation_ids", [True]),
                           ("generated_ids_full", [11, 22, 33, -1]),
                           ("decoded_for_parser", []), ("generation_kwargs", {"seed": 1})):
            obj = {**original, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.adapter.adapt(json.dumps(obj).encode(), Task.CLASSIFICATION)


if __name__ == "__main__":
    unittest.main()
