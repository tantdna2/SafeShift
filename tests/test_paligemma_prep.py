"""Fake/static only. No torch import, downloaded snapshot, or dataset input."""

from contextlib import ExitStack, nullcontext
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import socket
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from safeshift.runners import paligemma as pg
from safeshift.runners import paligemma_snapshot as snap
from safeshift.runners.contracts import (ErrorCode, GenerationFailure, ParseStatus,
                                        Request, RunContext, Task)
from safeshift.runners.paligemma import execute_call
from safeshift.runners.storage import FileRawStore, RawReference
from scripts import w2_paligemma_t4_smoke as smoke


class FakeOOM(RuntimeError):
    pass


class Tensor:
    def __init__(self, value=None, *, shape=None, dtype="int64", device="cuda:0"):
        self.value = value
        self.shape = shape if shape is not None else [len(value), len(value[0])]
        self.dtype, self.device = dtype, device

    def tolist(self):
        return deepcopy(self.value)


class Inputs(dict):
    def to(self, device, dtype):
        for name, tensor in self.items():
            tensor.device = device
            if name == "pixel_values":
                tensor.dtype = dtype
        return self


class Config(NS):
    def to_dict(self):
        return {k: v.to_dict() if isinstance(v, Config) else v for k, v in vars(self).items()}


class PaliGemmaProcessor:
    def __init__(self):
        self.image_processor = type("SiglipImageProcessor", (), {})()
        self.image_processor.__dict__.update(size={"height": 448, "width": 448},
            image_mean=[0.5, 0.5, 0.5], image_std=[0.5, 0.5, 0.5],
            rescale_factor=1 / 255, resample=3, do_resize=True, do_rescale=True, do_normalize=True)
        self.tokenizer = type("GemmaTokenizerFast", (), {})()
        self.image_seq_length, self.image_token_id = 1024, 257152
        self.inputs = None
        self.decode_error = None
        self.prompts, self.prepared = [], []

    def __call__(self, **kwargs):
        from PIL import Image
        assert set(kwargs) == {"text", "images", "return_tensors"}
        assert isinstance(kwargs["images"], Image.Image)
        assert type(kwargs["text"]) is str and kwargs["return_tensors"] == "pt"
        self.prompts.append(kwargs["text"])
        row = [257152] * 1024 + [2, kwargs["images"].width, 108]
        self.inputs = Inputs(input_ids=Tensor([row]), attention_mask=Tensor([[1] * len(row)]),
                             pixel_values=Tensor(shape=[1, 3, 448, 448], dtype="float32", device="cpu"))
        self.prepared.append(self.inputs)
        return self.inputs

    def decode(self, ids, **kwargs):
        if self.decode_error:
            raise self.decode_error
        assert kwargs["clean_up_tokenization_spaces"] is False
        return "<loc0000><loc0001><loc1023><loc1022> shape" + (
            "<eos>" if not kwargs["skip_special_tokens"] else "")


class PaliGemmaForConditionalGeneration:
    def __init__(self):
        self.config = Config(_attn_implementation="sdpa", model_type="paligemma", image_token_index=257152,
                             text_config=Config(_attn_implementation="sdpa"),
                             vision_config=Config(_attn_implementation="sdpa", image_size=448))
        self.generation_config = Config(eos_token_id=1)
        self.dtype, self.device, self.training = "float16", "cpu", True
        self.parameter = Tensor(shape=[1], dtype="float16")
        self.buffer = Tensor(shape=[1], dtype="float32")
        self.error = None
        self.drift = False
        self.generate_count = 0
        self.configs = []

    def to(self, device):
        self.device = device
        return self

    def eval(self):
        self.training = False
        return self

    def parameters(self):
        return iter([self.parameter])

    def buffers(self):
        return iter([self.buffer])

    def modules(self):
        return iter([self])

    def generate(self, **kwargs):
        self.generate_count += 1
        if self.error:
            raise self.error
        if self.drift:
            self.generation_config.eos_token_id = 999
        assert all(kwargs[k] == v for k, v in pg.DECODING.items())
        assert kwargs["generation_config"] is not self.generation_config
        assert kwargs["use_cache"] is False
        assert "past_key_values" not in kwargs and "cache_implementation" not in kwargs
        assert kwargs["logits_to_keep"] == 1
        self.configs.append(kwargs["generation_config"])
        return Tensor([kwargs["input_ids"].tolist()[0] + [256000, 256001, 257023, 257022, 1]])


def fake_torch():
    cuda = NS(is_available=lambda: True, device_count=lambda: 1,
              get_device_properties=lambda _: NS(name="Tesla T4", major=7, minor=5, total_memory=15 * 2**30),
              OutOfMemoryError=FakeOOM, synchronize=lambda _: None, reset_peak_memory_stats=lambda _: None)
    for method in ("memory_allocated", "memory_reserved", "max_memory_allocated", "max_memory_reserved"):
        setattr(cuda, method, lambda _: 1024)
    return NS(cuda=cuda, version=NS(cuda="12.4"), float16="float16", int64="int64", inference_mode=nullcontext)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        for path in (snap.PLAN, "configs/pre_freeze/paligemma_source_api_audit.v1.json",
                     "requirements-paligemma-t4.txt", "safeshift/runners/paligemma.py",
                     "safeshift/runners/paligemma_snapshot.py", "scripts/w2_paligemma_t4_smoke.py",
                     "scripts/provision_paligemma_snapshot.py", "safeshift/runners/contracts.py",
                     "safeshift/runners/storage.py"):
            dest = self.repo / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(snap.ROOT / path, dest)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict("os.environ", snap.OFFLINE_ENV))
        self.stack.enter_context(patch.object(pg, "software_versions", return_value=snap.load_plan()["software"]))
        self.verifier = self.stack.enter_context(patch.object(pg, "verify_snapshot", return_value={
            "local_bytes_verified": True, "revision": snap.REVISION}))
        self.torch, self.model, self.processor = fake_torch(), PaliGemmaForConditionalGeneration(), PaliGemmaProcessor()
        self.events = []

        def factory(value, label):
            def load(path, **kwargs):
                self.assertTrue(self.verifier.called)
                self.assertTrue(str(path).endswith(snap.REVISION))
                self.assertEqual(kwargs["revision"], snap.REVISION)
                self.assertIs(kwargs["trust_remote_code"], False)
                self.assertIs(kwargs["local_files_only"], True)
                with self.assertRaisesRegex(RuntimeError, "NETWORK_FORBIDDEN"):
                    socket.getaddrinfo("example.com", 443)
                self.events.append(label)
                if label == "model":
                    self.assertEqual(kwargs["dtype"], "float16")
                    self.assertEqual(kwargs["attn_implementation"], "sdpa")
                    self.assertTrue(kwargs["use_safetensors"])
                    self.assertTrue(kwargs["output_loading_info"])
                    self.assertNotIn("device_map", kwargs)
                    return value, {"missing_keys": [], "unexpected_keys": [], "mismatched_keys": [], "error_msgs": []}
                return value
            return NS(from_pretrained=Mock(side_effect=load))

        self.backend = NS(torch=self.torch, processor_factory=factory(self.processor, "processor"),
                          model_factory=factory(self.model, "model"))
        self.runner = pg.PaliGemmaRunner(repo=self.repo, backend_factory=lambda: self.backend)
        self.addCleanup(self.runner.close)
        self.ctx = RunContext("fake-run", "case_01", deepcopy(pg.DECODING), deepcopy(pg.PREPROCESSING),
                              "FP16", "NONE", {"placement": "cuda:0"}, snap.load_plan()["software"],
                              "a" * 40, "fake-static-test", "HANDCRAFTED_RUNTIME_SMOKE")
        _, raw, _ = next(smoke.generate_cases())
        self.request = Request(Task.CLASSIFICATION, "case_01", "case_01", raw, "test-prompt", "Describe.")

    def load(self):
        self.runner.initialize(self.ctx)
        self.runner.load(self.ctx)

    def test_exact_identity_and_network_before_backend(self):
        self.assertEqual(pg.MODEL_ID, "google/paligemma-3b-mix-448")
        self.assertEqual(pg.REVISION, "ead2d9a35598cb89119af004f5d023b311d1c4a1")
        def backend():
            with self.assertRaisesRegex(RuntimeError, "NETWORK_FORBIDDEN"):
                socket.create_connection(("example.com", 443))
            return self.backend
        self.runner.backend_factory = backend
        self.load()
        self.assertEqual(self.events, ["processor", "model"])
        self.assertEqual(self.runner.model_load_count, 1)

    def test_two_calls_one_load_and_independent_state(self):
        for case_id, raw, _ in smoke.generate_cases():
            request = replace(self.request, sample_id=case_id, input_id=case_id, input_bytes=raw)
            result = execute_call(self.runner, pg.PendingPaliGemmaAdapter(),
                                  pg.VerifiedRawStore(self.repo), request, replace(self.ctx, call_id=case_id))
            self.assertEqual(result.parse_status, ParseStatus.INVALID)
            self.assertEqual(result.error.code, ErrorCode.INVALID_CLASSIFICATION)
            self.assertTrue(result.raw_output)
            self.assertEqual(self.runner.state, "GENERATED")
        self.assertEqual((self.runner.model_load_count, self.runner.native_generate_calls), (1, 2))
        self.assertEqual(self.model.generate_count, 2)
        self.assertEqual(self.processor.prompts, [self.request.prompt] * 2)
        self.assertIsNot(self.processor.prepared[0], self.processor.prepared[1])
        self.assertIsNot(self.model.configs[0], self.model.configs[1])
        self.assertEqual(self.runner.baseline, self.runner.state_audit())

    def test_contract_rejects_dtype_quantization_offload_fallback_seed(self):
        bad = [replace(self.ctx, precision="BF16"), replace(self.ctx, quantization="INT8"),
               replace(self.ctx, device={"placement": "auto"}), replace(self.ctx, device={"placement": "cpu"}),
               replace(self.ctx, device={"placement": "cuda:0", "offload": True}),
               replace(self.ctx, preprocessing={**pg.PREPROCESSING, "batch_size": 2}),
               replace(self.ctx, decoding={**pg.DECODING, "fallback": True}), replace(self.ctx, seed=1),
               replace(self.ctx, software_versions={"torch": "latest"}),
               replace(self.ctx, source_kind="DATASET")]
        for context in bad:
            with self.subTest(context=context), self.assertRaises(ValueError):
                self.runner._condition(context)
        self.assertIsNone(self.runner.backend)

    def test_identity_mismatch_rejected(self):
        self.runner.identity = replace(pg.IDENTITY, immutable_revision="b" * 40)
        with self.assertRaisesRegex(ValueError, "EXACT_MODEL"):
            self.runner.initialize(self.ctx)

    def test_offline_environment_required(self):
        with patch.dict("os.environ", {"HF_HUB_OFFLINE": "0"}), self.assertRaises(ValueError):
            self.runner.initialize(self.ctx)
        self.assertEqual(self.runner.model_load_count, 0)

    def test_installed_software_mismatch_before_backend(self):
        with patch.object(pg, "software_versions", return_value={}), self.assertRaises(ValueError):
            self.runner.initialize(self.ctx)
        self.assertEqual(self.runner.failure["stage"], "SOFTWARE")

    def test_snapshot_failure_before_processor_or_model(self):
        self.verifier.side_effect = ValueError("mismatch")
        self.runner.initialize(self.ctx)
        with self.assertRaises(ValueError):
            self.runner.load(self.ctx)
        self.assertEqual(self.runner.failure["stage"], "SNAPSHOT_VERIFY")
        self.assertFalse(self.events)
        self.assertEqual(self.runner.model_load_count, 0)

    def test_load_oom_records_stage_message_cause_and_no_retry(self):
        self.backend.model_factory.from_pretrained.side_effect = FakeOOM("fake allocation failed")
        self.runner.initialize(self.ctx)
        with self.assertRaises(FakeOOM):
            self.runner.load(self.ctx)
        self.assertEqual(self.runner.failure["status"], "RUNTIME_RESOURCE_FAILURE")
        self.assertEqual(self.runner.failure["stage"], "MODEL_LOAD")
        self.assertIn("fake allocation", self.runner.failure["message"])
        with self.assertRaisesRegex(RuntimeError, "NO_RETRY"):
            self.runner.load(self.ctx)
        self.assertEqual(self.runner.model_load_count, 1)

    def test_incomplete_checkpoint_keys_fail_without_generation(self):
        self.backend.model_factory.from_pretrained.side_effect = None
        self.backend.model_factory.from_pretrained.return_value = (self.model, {"missing_keys": ["synthetic.weight"]})
        self.runner.initialize(self.ctx)
        with self.assertRaisesRegex(ValueError, "WEIGHT_KEYS"):
            self.runner.load(self.ctx)
        self.assertEqual(self.runner.failure["stage"], "WEIGHT_KEY_AUDIT")
        self.assertEqual(self.runner.native_generate_calls, 0)

    def test_generation_oom_distinct_from_interface_failure(self):
        self.load()
        self.model.error = FakeOOM("fake oom")
        prepared = self.runner.prepare_input(self.request, self.ctx)
        with self.assertRaises(GenerationFailure):
            self.runner.generate_raw(prepared, self.ctx)
        self.assertEqual(self.runner.failure["status"], "RUNTIME_RESOURCE_FAILURE")
        self.assertEqual(self.runner.failure["stage"], "NATIVE_GENERATE")
        self.assertEqual(self.runner.failure["causes"][0]["type"], "FakeOOM")
        record = pg.exception_record(ValueError("bad interface"), "PREPARE", self.torch)
        self.assertEqual(record["status"], "RUNTIME_INTERFACE_FAILURE")

    def test_decode_failure_preserves_ids_without_adapter(self):
        self.processor.decode_error = ValueError("fake decode failure")
        adapter = Mock()
        adapter.version, adapter.parser_version = "test", "test"
        result = execute_call(self.runner, adapter, pg.VerifiedRawStore(self.repo), self.request, self.ctx)
        self.assertEqual(result.error.code, ErrorCode.GENERATION_FAILURE)
        self.assertFalse(adapter.adapt.called)
        raw = json.loads((self.repo / result.raw_output.path).read_bytes())
        self.assertIn("generated_ids_full", raw)
        self.assertEqual(self.runner.failure["stage"], "NATIVE_DECODE")

    def test_state_drift_fails_with_preserved_output(self):
        self.model.drift = True
        result = execute_call(self.runner, pg.PendingPaliGemmaAdapter(), pg.VerifiedRawStore(self.repo),
                              self.request, self.ctx)
        self.assertEqual(result.error.code, ErrorCode.GENERATION_FAILURE)
        self.assertTrue(result.raw_output)
        self.assertEqual(self.runner.failure["stage"], "POST_GENERATION_STATE_AUDIT")

    def test_state_audit_rejects_offload_quantization_dtype_and_cache(self):
        self.load()
        cases = [(self.model.parameter, "device", "cpu"), (self.model.parameter, "dtype", "bfloat16"),
                 (self.model.buffer, "device", "cpu"), (self.model, "is_quantized", True),
                 (self.model, "hf_device_map", {"": "disk"}), (self.model, "_cache", object()),
                 (self.model.config.text_config, "_attn_implementation", "eager")]
        for obj, key, value in cases:
            with self.subTest(key=key), patch.object(obj, key, value, create=True), self.assertRaises(ValueError):
                self.runner.state_audit()

    def test_batch_device_dtype_and_image_token_expansion(self):
        self.load()
        prepared = self.runner.prepare_input(self.request, self.ctx)
        for name, attribute, value in [("input_ids", "value", [[1], [1]]),
                                        ("pixel_values", "dtype", "float32"),
                                        ("pixel_values", "device", "cpu"),
                                        ("pixel_values", "shape", [14, 3, 448, 448]),
                                        ("pixel_values", "shape", [2, 3, 448, 448])]:
            with self.subTest(attribute=attribute), patch.object(prepared.inputs[name], attribute, value):
                with self.assertRaises(ValueError):
                    self.runner._observe_inputs(prepared.inputs)

    def test_repeated_call_and_changed_context_rejected(self):
        self.load()
        prepared = self.runner.prepare_input(self.request, self.ctx)
        self.runner.generate_raw(prepared, self.ctx)
        with self.assertRaises(ValueError):
            self.runner._condition(replace(self.ctx, run_id="other"))
        with self.assertRaises(ValueError):
            self.runner.prepare_input(self.request, self.ctx)

    def test_raw_persistence_verified_before_adapter(self):
        owner = self
        class ObservingAdapter(pg.PendingPaliGemmaAdapter):
            def adapt(self, raw, task):
                paths = list((owner.repo / "data/processed/local_runs").rglob("response.raw"))
                owner.assertEqual(len(paths), 1)
                owner.assertEqual(paths[0].read_bytes(), raw)
                metadata = json.loads((paths[0].parent / "metadata.json").read_bytes())
                owner.assertEqual(metadata["parse_status"], "NOT_ATTEMPTED")
                owner.assertEqual(metadata["raw_output"]["sha256"], hashlib.sha256(raw).hexdigest())
                owner.assertEqual(metadata["raw_output"]["size_bytes"], len(raw))
                owner.assertEqual(metadata["immutable_revision"], snap.REVISION)
                return super().adapt(raw, task)
        result = execute_call(self.runner, ObservingAdapter(), pg.VerifiedRawStore(self.repo), self.request, self.ctx)
        self.assertEqual(result.parse_status, ParseStatus.INVALID)

    def test_corrupt_persisted_raw_prevents_adapter(self):
        original = FileRawStore.preserve
        def corrupt(store, raw, provenance):
            ref = original(store, raw, provenance)
            path = store.repo / ref.path
            path.write_bytes(b"x" * len(raw))  # same size, wrong checksum
            return ref
        adapter = Mock(version="test", parser_version="test")
        with patch.object(FileRawStore, "preserve", corrupt):
            result = execute_call(self.runner, adapter, pg.VerifiedRawStore(self.repo), self.request, self.ctx)
        self.assertEqual(result.error.code, ErrorCode.RAW_PRESERVATION_FAILURE)
        adapter.adapt.assert_not_called()
        self.assertEqual(self.runner.state, "FAILED")
        with self.assertRaisesRegex(RuntimeError, "NO_RETRY"):
            execute_call(self.runner, adapter, pg.VerifiedRawStore(self.repo), self.request,
                         replace(self.ctx, call_id="new-attempt"))
        self.assertEqual(self.runner.native_generate_calls, 1)

    def test_raw_fsync_and_reread_precede_adapter_with_complete_provenance(self):
        import os
        events = []
        fsync = os.fsync
        checksum = pg.sha256_file
        def sync(fd):
            fsync(fd)
            events.append("fsync")
        def reread(path):
            value = checksum(path)
            events.append("reread")
            return value
        owner = self
        class Adapter(pg.PendingPaliGemmaAdapter):
            def adapt(self, raw, task):
                owner.assertEqual(events, ["fsync", "fsync", "reread"])
                events.append("adapter")
                envelope = json.loads(raw)
                owner.assertEqual(envelope["hardware"]["compute_capability"], [7, 5])
                owner.assertEqual(envelope["dtype"], "FP16")
                owner.assertEqual(envelope["continuation_ids"], [256000, 256001, 257023, 257022, 1])
                owner.assertIn("<loc1023>", envelope["decoded_with_special_tokens"])
                return super().adapt(raw, task)
        with patch("safeshift.runners.storage.os.fsync", side_effect=sync), \
             patch.object(pg, "sha256_file", side_effect=reread):
            result = execute_call(self.runner, Adapter(), pg.VerifiedRawStore(self.repo), self.request, self.ctx)
        self.assertEqual(events[-1], "adapter")
        metadata = json.loads((self.repo / result.raw_output.path).with_name("metadata.json").read_bytes())
        self.assertEqual(metadata["input_sha256"], hashlib.sha256(self.request.input_bytes).hexdigest())
        self.assertEqual(metadata["prompt_sha256"], hashlib.sha256(self.request.prompt.encode()).hexdigest())
        for key in ("model_id", "immutable_revision", "git_commit_sha", "run_id", "call_id",
                    "prompt", "software_versions", "timestamp", "raw_output", "precision", "device"):
            self.assertTrue(metadata[key])

    def test_failed_fsync_and_unverified_store_never_reach_adapter(self):
        adapter = Mock(version="test", parser_version="test")
        with self.assertRaisesRegex(TypeError, "VERIFIED_RAW"):
            execute_call(self.runner, adapter, FileRawStore(self.repo), self.request, self.ctx)
        with patch("safeshift.runners.storage.os.fsync", side_effect=OSError("synthetic disk failure")):
            result = execute_call(self.runner, adapter, pg.VerifiedRawStore(self.repo), self.request, self.ctx)
        self.assertEqual(result.error.code, ErrorCode.RAW_PRESERVATION_FAILURE)
        adapter.adapt.assert_not_called()
        self.assertEqual(self.runner.state, "FAILED")

    def test_parser_exception_is_terminal_without_retry(self):
        adapter = Mock(version="test", parser_version="test")
        adapter.adapt.side_effect = ValueError("synthetic parser failure")
        result = execute_call(self.runner, adapter, pg.VerifiedRawStore(self.repo), self.request, self.ctx)
        self.assertEqual(result.error.code, ErrorCode.PARSER_FAILURE)
        self.assertTrue(result.raw_output)
        self.assertEqual(self.runner.state, "FAILED")

    def test_native_processor_contract_and_persistent_cache_are_checked(self):
        self.load()
        for obj, field, value in (
                (self.processor, "image_seq_length", 256),
                (self.processor, "image_token_id", 1),
                (self.processor.image_processor, "size", {"height": 224, "width": 224}),
                (self.processor.image_processor, "image_std", [1, 1, 1]),
                (self.model.config, "model_type", "paligemma2"),
                (self.model, "past_key_values", object()),
                (self.model, "_hf_hook", NS(offload=True)),
                (self.model.generation_config, "cache_implementation", "offloaded")):
            with self.subTest(field=field), patch.object(obj, field, value, create=True), self.assertRaises(ValueError):
                self.runner.state_audit()

    def test_url_bytes_fail_before_processor(self):
        self.load()
        request = replace(self.request, input_bytes=b"https://example.com/image.png")
        with self.assertRaises(Exception):
            self.runner.prepare_input(request, self.ctx)
        self.assertEqual(self.runner.state, "FAILED")
        self.assertEqual(self.processor.prompts, [])

    def test_multiframe_bytes_fail_before_processor(self):
        from io import BytesIO
        from PIL import Image
        stream = BytesIO()
        with Image.new("RGB", (4, 4), "red") as first, Image.new("RGB", (4, 4), "blue") as second:
            first.save(stream, format="GIF", save_all=True, append_images=[second])
        self.load()
        with self.assertRaisesRegex(ValueError, "ONE_STILL_IMAGE"):
            self.runner.prepare_input(replace(self.request, input_bytes=stream.getvalue()), self.ctx)
        self.assertEqual(self.processor.prompts, [])

    def test_venue_attestation_failure_is_saved_without_backend(self):
        with patch.object(smoke, "checkout_gate", return_value="a" * 40):
            report = smoke.run_smoke("no-attestation", expected_commit="a" * 40,
                                      venue_internet_off=False, repo=self.repo,
                                      runner_factory=Mock(side_effect=AssertionError("must not load")))
        self.assertEqual(report["failure"]["stage"], "OFFLINE_PREFLIGHT")
        self.assertEqual(report["model_load_count"], 0)

    def test_fake_end_to_end_smoke_counts_artifacts_and_pending_parser(self):
        with patch.object(smoke, "checkout_gate", return_value="a" * 40), \
             patch.object(smoke, "software_versions", return_value=self.ctx.software_versions), \
             patch.object(smoke.platform, "system", return_value="Linux"), \
             patch.object(smoke.platform, "machine", return_value="x86_64"), \
             patch.object(smoke.importlib.metadata, "distributions", return_value=[]):
            report = smoke.run_smoke("fake-smoke", expected_commit="a" * 40, venue_internet_off=True,
                                      repo=self.repo, torch_module=self.torch,
                                      runner_factory=lambda **_: self.runner)
        self.assertEqual(report["status"], "RUNTIME_INTERFACE_PASS", report.get("failure"))
        self.assertEqual(report["model_load_count"], 1)
        self.assertEqual(report["native_generate_calls"], 2)
        self.assertEqual(report["classification"], "PENDING_QUALIFICATION")
        self.assertEqual(report["grounding"], "PENDING_QUALIFICATION")
        self.assertEqual(report["protocol_freeze_commit_sha"], "PENDING")
        self.assertFalse(report["inspecsafe_used"])
        self.assertGreater(len(report["state_audits"]), 4)
        for record in report["calls"]:
            self.assertEqual(record["parse_status"], "INVALID")
            raw = self.repo / record["raw"]["path"]
            self.assertEqual(raw.stat().st_size, record["raw"]["size_bytes"])
            self.assertEqual(snap.sha256_file(raw), record["raw"]["sha256"])

    def test_smoke_preflight_failure_is_saved_without_backend(self):
        with patch.object(smoke, "checkout_gate", side_effect=ValueError("dirty checkout")):
            report = smoke.run_smoke("fake-failure", expected_commit="a" * 40,
                                      venue_internet_off=True, repo=self.repo,
                                      runner_factory=Mock(side_effect=AssertionError("must not load")))
        self.assertEqual(report["failure"]["stage"], "CHECKOUT")
        self.assertEqual(report["model_load_count"], 0)
        self.assertEqual(report["native_generate_calls"], 0)
        self.assertTrue((self.repo / smoke.ARTIFACTS / "fake-failure/summary.json").exists())

    def test_fake_smoke_generation_failure_retains_oom_evidence_and_counts(self):
        self.model.error = FakeOOM("synthetic generation OOM")
        with patch.object(smoke, "checkout_gate", return_value="a" * 40), \
             patch.object(smoke, "software_versions", return_value=self.ctx.software_versions), \
             patch.object(smoke.platform, "system", return_value="Linux"), \
             patch.object(smoke.platform, "machine", return_value="x86_64"), \
             patch.object(smoke.importlib.metadata, "distributions", return_value=[]):
            report = smoke.run_smoke("fake-oom", expected_commit="a" * 40, venue_internet_off=True,
                                      repo=self.repo, torch_module=self.torch,
                                      runner_factory=lambda **_: self.runner)
        self.assertEqual(report["status"], "RUNTIME_RESOURCE_FAILURE")
        self.assertEqual(report["failure"]["stage"], "NATIVE_GENERATE")
        self.assertEqual(report["failure"]["causes"][0]["message"], "synthetic generation OOM")
        self.assertEqual(report["model_load_count"], 1)
        self.assertEqual(report["native_generate_calls"], 1)
        self.assertEqual(len(report["calls"]), 1)


class SnapshotAndStaticTests(unittest.TestCase):
    def test_d9r7_axis_permutation_divisor_and_endpoint(self):
        self.assertEqual(pg.loc_values_to_d4([128, 256, 768, 1023]),
                         [0.25, 0.125, 1023 / 1024, 0.75])
        self.assertEqual(pg.loc_values_to_d4([0, 0, 1023, 1023]),
                         [0.0, 0.0, 0.9990234375, 0.9990234375])
        self.assertLess(pg.loc_values_to_d4([0, 0, 1023, 1023])[2], 1.0)

    def test_loc_malformed_no_clamp_no_repair_or_point_box(self):
        for values in (None, "<loc0000>", {"point": [1, 2]}, [0, 0], [0, 0, 1, 1, 1],
                       [0, 0, 1024, 1023], [-1, 0, 1, 1], [False, 0, 1, 1],
                       [0.0, 0, 1, 1], [0, "0", 1, 1], [0, 0, float("nan"), 1],
                       [0, 0, 1, float("inf")], [2, 0, 1, 1], [0, 2, 1, 1],
                       [0, 0, 0, 1], [0, 0, 1, 0]):
            with self.subTest(values=values), self.assertRaisesRegex(ValueError, "PARSER_FAIL_NO_REPAIR"):
                pg.loc_values_to_d4(values)

    def test_plan_identity_and_governance_remain_pending(self):
        plan = snap.load_plan()
        self.assertEqual(plan["runner_prep_status"], "PREPARED_NOT_RUNTIME_VALIDATED")
        for key in ("runtime_qualification", "grounding", "classification_interface", "external_gate"):
            self.assertEqual(plan[key], "PENDING_QUALIFICATION")
        for key in ("exact_runtime_verified", "weights_downloaded", "local_weight_bytes_verified",
                    "inspecsafe_inference_authorized", "promotion", "gate_executed"):
            self.assertIs(plan[key], False)
        self.assertEqual(plan["paligemma_role"], "BACKUP_1")
        self.assertEqual(plan["primary_roster_count"], 4)
        self.assertEqual(plan["protocol_freeze"], "PENDING")
        self.assertTrue(plan["protocol_freeze_blocked"])
        self.assertEqual(plan["detection"]["normalization_divisor"], 1024.0)

    def test_plan_tampering_is_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / snap.PLAN
            path.parent.mkdir(parents=True)
            plan = snap.load_plan()
            plan["model_revision"] = "main"
            path.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError, "PLAN_CHANGED"):
                snap.load_plan(Path(directory))

    def test_inventory_matches_all_existing_authoritative_hashes(self):
        audit = json.loads((snap.ROOT / "configs/pre_freeze/paligemma_source_api_audit.v1.json").read_bytes())
        provenance = json.loads((snap.ROOT / "configs/pre_freeze/local_model_provenance.d9.json").read_bytes())
        entry = next(m for m in provenance["models"] if m["key"] == "paligemma_3b_mix_448")
        files = {f["path"]: f for f in snap.load_plan()["snapshot_files"]}
        self.assertEqual(len(files), 14)
        for weight in entry["weight_provenance"]["files"]:
            self.assertEqual(files[weight["path"]]["expected_hash"], weight["lfs_sha256"])
            self.assertEqual(files[weight["path"]]["size_bytes"], weight["size_bytes"])
        for name in audit["access_evidence"]["verified_files"]:
            source = audit["sources"]["exact_" + name]
            self.assertEqual(files[name]["expected_hash"], source["revision_provenance"]["hash"])
            self.assertEqual(files[name]["size_bytes"], source["size_bytes"])

    def test_explicit_provision_uses_exact_allowlist_and_no_revision_fallback(self):
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            downloader = Mock(return_value=str(snap.snapshot_path(repo)))
            with patch.dict("sys.modules", {"huggingface_hub": NS(snapshot_download=downloader)}), \
                 patch.object(snap, "load_plan", return_value=snap.load_plan()), \
                 patch.object(snap, "verify_snapshot", return_value={"verified": True}):
                self.assertTrue(snap.provision_or_verify(provision=True, repo=repo)["verified"])
                args = downloader.call_args.kwargs
                self.assertEqual(args["repo_id"], snap.MODEL_ID)
                self.assertEqual(args["revision"], snap.REVISION)
                self.assertEqual(set(args["allow_patterns"]), {f["path"] for f in snap.load_plan()["snapshot_files"]})
                downloader.side_effect = RuntimeError("synthetic access failure")
                downloader.reset_mock()
                with self.assertRaisesRegex(RuntimeError, "access failure"):
                    snap.provision_or_verify(provision=True, repo=repo)
                downloader.assert_called_once()
                self.assertEqual(downloader.call_args.kwargs["revision"], snap.REVISION)

    def test_provision_wrong_returned_revision_fails(self):
        with TemporaryDirectory() as directory:
            downloader = Mock(return_value=str(Path(directory) / "main"))
            with patch.dict("sys.modules", {"huggingface_hub": NS(snapshot_download=downloader)}), \
                 patch.object(snap, "load_plan", return_value=snap.load_plan()), \
                 self.assertRaisesRegex(ValueError, "WRONG_SNAPSHOT"):
                snap.provision_or_verify(provision=True, repo=Path(directory))

    def test_hardware_rejects_wrong_count_gpu_cc_vram_cuda(self):
        for field, value in [("count", 2), ("count", 0), ("name", "NVIDIA A100"),
                             ("major", 8), ("minor", 0), ("memory", 13 * 2**30),
                             ("memory", 17 * 2**30), ("cuda", "12.6")]:
            torch = fake_torch()
            prop = torch.cuda.get_device_properties(0)
            if field == "count":
                torch.cuda.device_count = lambda: value
            elif field == "cuda":
                torch.version.cuda = value
            else:
                setattr(prop, "total_memory" if field == "memory" else field, value)
                torch.cuda.get_device_properties = lambda _: prop
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                pg.probe_hardware(torch)
        self.assertEqual(pg.probe_hardware(fake_torch())["visible_gpu_count"], 1)

    def test_snapshot_inventory_hash_size_revision_and_extra_files(self):
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / snap.REPOSITORY / "snapshots" / snap.REVISION
            snapshot.mkdir(parents=True)
            data = {"config.json": b"{}", "weights.fixture": b"synthetic weight bytes"}
            files = []
            for name, raw in data.items():
                (snapshot / name).write_bytes(raw)
                sha = hashlib.sha256(raw).hexdigest() if name.endswith("fixture") else hashlib.sha1(
                    b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
                files.append({"path": name, "size_bytes": len(raw), "expected_hash": sha,
                              "hash_algorithm": "sha256" if name.endswith("fixture") else "git_blob_sha1"})
            with patch.object(snap, "load_plan", return_value={"snapshot_files": files}):
                with snap.network_denied():
                    self.assertTrue(snap.verify_snapshot(snapshot)["local_bytes_verified"])
                for raw in (b"xx", b"longer"):
                    (snapshot / "config.json").write_bytes(raw)
                    with self.assertRaisesRegex(ValueError, "MISMATCH"):
                        snap.verify_snapshot(snapshot)
                (snapshot / "config.json").write_bytes(b"{}")
                (snapshot / "extra.py").write_bytes(b"unreviewed")
                with self.assertRaisesRegex(ValueError, "INVENTORY"):
                    snap.verify_snapshot(snapshot)
                (snapshot / "extra.py").unlink()
                (snapshot / "config.json").unlink()
                with self.assertRaisesRegex(ValueError, "INVENTORY"):
                    snap.verify_snapshot(snapshot)
                with self.assertRaisesRegex(ValueError, "EXACT_SNAPSHOT"):
                    snap.verify_snapshot(snapshot.parent / "main")

    def test_verify_only_denies_network_and_never_imports_hub(self):
        def verify(*args, **kwargs):
            with self.assertRaisesRegex(RuntimeError, "NETWORK_FORBIDDEN"):
                socket.getaddrinfo("example.com", 443)
            return {"verified": True}
        with patch.object(snap, "verify_snapshot", side_effect=verify), \
             patch.dict("sys.modules", {"huggingface_hub": None}):
            self.assertTrue(snap.provision_or_verify()["verified"])

    def test_provision_refuses_nonempty_cache_no_silent_repair(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / snap.CACHE
            root.mkdir(parents=True)
            (root / "partial").write_bytes(b"interrupted")
            with patch.dict("sys.modules", {"huggingface_hub": None}), self.assertRaisesRegex(ValueError, "NO_REPAIR"):
                snap.provision_or_verify(provision=True, repo=Path(directory))
            self.assertEqual((root / "partial").read_bytes(), b"interrupted")

    def test_all_network_socket_paths_are_denied(self):
        with snap.network_denied():
            for function in (socket.create_connection, socket.getaddrinfo):
                with self.assertRaisesRegex(RuntimeError, "NETWORK_FORBIDDEN"):
                    function("example.com", 443)
            with socket.socket() as sock:
                for name in ("connect", "connect_ex", "sendto"):
                    with self.assertRaisesRegex(RuntimeError, "NETWORK_FORBIDDEN"):
                        getattr(sock, name)(b"fake")

    def test_pending_adapter_never_invents_coordinates_or_classification(self):
        for raw in (b"Level01", b'<box>1,2,3,4</box>', b'{"point":[1,2]}'):
            grounding = pg.PendingPaliGemmaAdapter().adapt(raw, Task.GROUNDING)
            classification = pg.PendingPaliGemmaAdapter().adapt(raw, Task.CLASSIFICATION)
            self.assertEqual(grounding.parse_status, ParseStatus.UNSUPPORTED)
            self.assertEqual(classification.parse_status, ParseStatus.INVALID)
            self.assertIsNone(grounding.value)
            self.assertIsNone(classification.value)

    def test_raw_size_mismatch_and_metadata_corruption_rejected(self):
        with TemporaryDirectory() as directory:
            store = pg.VerifiedRawStore(Path(directory))
            path = store.root / "response.raw"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"x")
            ref = RawReference(path.relative_to(store.repo).as_posix(), hashlib.sha256(b"x").hexdigest(), 2)
            with patch.object(FileRawStore, "preserve", return_value=ref), self.assertRaises(ValueError):
                store.preserve(b"x", {})
            ref = replace(ref, size_bytes=1)
            (path.parent / "metadata.json").write_text('{}')
            with patch.object(FileRawStore, "preserve", return_value=ref), self.assertRaisesRegex(ValueError, "PROVENANCE"):
                store.preserve(b"x", {})

    def test_checkout_gate_exact_sha_and_untracked_cleanliness(self):
        for expected, outputs in [("main", []), ("a" * 40, ["b" * 40]),
                                  ("a" * 40, ["a" * 40, "?? unknown-file"])]:
            with patch.object(smoke.subprocess, "check_output", side_effect=outputs), self.assertRaises(ValueError):
                smoke.checkout_gate(snap.ROOT, expected)
        with patch.object(smoke.subprocess, "check_output", side_effect=["a" * 40, ""]):
            self.assertEqual(smoke.checkout_gate(snap.ROOT, "a" * 40), "a" * 40)

    def test_plan_pins_match_requirements_and_authoritative_weight_metadata(self):
        plan = snap.load_plan()
        pins = dict(line.split("==") for line in (snap.ROOT / "requirements-paligemma-t4.txt").read_text().splitlines()
                    if "==" in line)
        self.assertEqual({k: v for k, v in plan["software"].items() if k != "python"}, pins)
        provenance = json.loads((snap.ROOT / "configs/pre_freeze/local_model_provenance.d9.json").read_bytes())
        entry = next(m for m in provenance["models"] if m["key"] == "paligemma_3b_mix_448")
        weight = next(f for f in plan["snapshot_files"] if f["path"] == "model-00001-of-00003.safetensors")
        self.assertEqual(weight["expected_hash"], entry["weight_provenance"]["files"][0]["lfs_sha256"])
        self.assertEqual(weight["size_bytes"], entry["weight_provenance"]["files"][0]["size_bytes"])
        self.assertFalse(plan["trust_remote_code"])
        self.assertEqual(plan["real_runtime_status"], "NOT_RUN")
        self.assertFalse(plan["inspecsafe_inference_authorized"])

    def test_source_has_no_dataset_input_or_runtime_downloader(self):
        runner = (snap.ROOT / "safeshift/runners/paligemma.py").read_text()
        harness = (snap.ROOT / "scripts/w2_paligemma_t4_smoke.py").read_text()
        for source in (runner, harness):
            for forbidden in ("data/raw", "InspecSafe-V1", "dataset_manifest", "snapshot_download(", "--image-path"):
                self.assertNotIn(forbidden, source)
        self.assertIn('source_kind not in {"HANDCRAFTED_RUNTIME_SMOKE", "EXTERNAL_CLASSIFICATION_QUALIFICATION"}', runner)


if __name__ == "__main__":
    unittest.main()
