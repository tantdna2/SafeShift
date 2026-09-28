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

from safeshift.runners import internvl3 as iv
from safeshift.runners import internvl3_snapshot as snap
from safeshift.runners.contracts import (ErrorCode, GenerationFailure, ParseStatus,
                                        Request, RunContext, Task, execute_call)
from safeshift.runners.storage import FileRawStore, RawReference
from scripts import w2_internvl3_t4_smoke as smoke


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


class InternVLProcessor:
    def __init__(self):
        self.image_processor = type("GotOcr2ImageProcessorFast", (), {})()
        self.image_processor.__dict__.update(size={"height": 448, "width": 448},
            min_patches=1, max_patches=12, image_mean=[0.485, 0.456, 0.406],
            image_std=[0.229, 0.224, 0.225], rescale_factor=1 / 255, resample=3,
            do_resize=True, do_rescale=True, do_normalize=True, do_convert_rgb=True)
        self.image_seq_length, self.image_token_id = 256, 151667
        self.inputs = None
        self.decode_error = None
        self.messages = []

    def apply_chat_template(self, messages, **kwargs):
        assert kwargs == {"tokenize": False, "add_generation_prompt": True}
        self.messages.append(deepcopy(messages))
        return "<IMG_CONTEXT> describe"

    def __call__(self, **kwargs):
        assert kwargs["crop_to_patches"] is True
        assert kwargs["max_patches"] == 12 and kwargs["min_patches"] == 1
        assert len(kwargs["images"]) == 1 and kwargs["return_tensors"] == "pt"
        count = 1 if kwargs["images"][0].width == 64 else 3
        row = [1] + [151667] * (256 * count) + [2]
        self.inputs = Inputs(input_ids=Tensor([row]), attention_mask=Tensor([[1] * len(row)]),
                             pixel_values=Tensor(shape=[count, 3, 448, 448], dtype="float32", device="cpu"))
        return self.inputs

    def decode(self, ids, **kwargs):
        if self.decode_error:
            raise self.decode_error
        return "blue rectangle" + ("<|im_end|>" if not kwargs["skip_special_tokens"] else "")


class FakeModel:
    def __init__(self):
        self.config = Config(_attn_implementation="sdpa",
                             text_config=Config(_attn_implementation="sdpa"),
                             vision_config=Config(_attn_implementation="sdpa"))
        self.generation_config = Config(eos_token_id=151645)
        self.model = NS(language_model=NS(rotary_emb=NS(
            rope_type="dynamic", max_seq_len_cached=32768, original_max_seq_len=32768,
            inv_freq=Tensor([1.0], shape=[1], dtype="float32"), attention_scaling=1.0)))
        self.dtype, self.device, self.training = "float16", "cpu", True
        self.parameter = Tensor(shape=[1], dtype="float16")
        self.buffer = Tensor(shape=[1], dtype="float32")
        self.error = None
        self.drift = False
        self.generate_count = 0

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
            self.model.language_model.rotary_emb.max_seq_len_cached = 40000
        assert all(kwargs[k] == v for k, v in iv.DECODING.items())
        assert kwargs["generation_config"] is not self.generation_config
        return Tensor([kwargs["input_ids"].tolist()[0] + [7, 151645]])


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
        for path in (snap.PLAN, "configs/pre_freeze/internvl3_source_audit.v1.json",
                     "requirements-internvl3-t4.txt", "safeshift/runners/internvl3.py",
                     "safeshift/runners/internvl3_snapshot.py", "scripts/w2_internvl3_t4_smoke.py",
                     "scripts/provision_internvl3_snapshot.py", "safeshift/runners/contracts.py",
                     "safeshift/runners/storage.py"):
            dest = self.repo / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(snap.ROOT / path, dest)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict("os.environ", snap.OFFLINE_ENV))
        self.stack.enter_context(patch.object(iv, "software_versions", return_value=snap.load_plan()["software"]))
        self.verifier = self.stack.enter_context(patch.object(iv, "verify_snapshot", return_value={
            "local_bytes_verified": True, "revision": snap.REVISION}))
        self.torch, self.model, self.processor = fake_torch(), FakeModel(), InternVLProcessor()
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
                    self.assertEqual(kwargs["torch_dtype"], "float16")
                    self.assertEqual(kwargs["attn_implementation"], "sdpa")
                    self.assertTrue(kwargs["use_safetensors"])
                    self.assertTrue(kwargs["output_loading_info"])
                    self.assertNotIn("device_map", kwargs)
                    return value, {"missing_keys": [], "unexpected_keys": [], "mismatched_keys": [], "error_msgs": []}
                return value
            return NS(from_pretrained=Mock(side_effect=load))

        self.backend = NS(torch=self.torch, processor_factory=factory(self.processor, "processor"),
                          model_factory=factory(self.model, "model"))
        self.runner = iv.InternVL3Runner(repo=self.repo, backend_factory=lambda: self.backend)
        self.addCleanup(self.runner.close)
        self.ctx = RunContext("fake-run", "case_01", deepcopy(iv.DECODING), deepcopy(iv.PREPROCESSING),
                              "FP16", "NONE", {"placement": "cuda:0"}, snap.load_plan()["software"],
                              "a" * 40, "fake-static-test", "HANDCRAFTED_RUNTIME_SMOKE")
        _, raw, _ = next(smoke.generate_cases())
        self.request = Request(Task.CLASSIFICATION, "case_01", "case_01", raw, "test-prompt", "Describe.")

    def load(self):
        self.runner.initialize(self.ctx)
        self.runner.load(self.ctx)

    def test_exact_identity_and_network_before_backend(self):
        self.assertEqual(iv.MODEL_ID, "OpenGVLab/InternVL3-2B-hf")
        self.assertEqual(iv.REVISION, "cb57a075cb75a2e6d1b668b128d48bb00ae321d2")
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
            result = execute_call(self.runner, iv.PendingInternVL3Adapter(),
                                  iv.VerifiedRawStore(self.repo), request, replace(self.ctx, call_id=case_id))
            self.assertEqual(result.parse_status, ParseStatus.INVALID)
            self.assertEqual(result.error.code, ErrorCode.INVALID_CLASSIFICATION)
            self.assertTrue(result.raw_output)
            self.assertEqual(self.runner.state, "GENERATED")
        self.assertEqual((self.runner.model_load_count, self.runner.native_generate_calls), (1, 2))
        self.assertEqual(self.model.generate_count, 2)
        self.assertEqual(len(self.processor.messages), 2)
        self.assertTrue(all(len(messages) == 1 for messages in self.processor.messages))
        self.assertEqual(self.runner.baseline, self.runner.state_audit())

    def test_contract_rejects_dtype_quantization_offload_fallback_seed(self):
        bad = [replace(self.ctx, precision="BF16"), replace(self.ctx, quantization="INT8"),
               replace(self.ctx, device={"placement": "auto"}), replace(self.ctx, device={"placement": "cpu"}),
               replace(self.ctx, device={"placement": "cuda:0", "offload": True}),
               replace(self.ctx, preprocessing={**iv.PREPROCESSING, "batch_size": 2}),
               replace(self.ctx, decoding={**iv.DECODING, "fallback": True}), replace(self.ctx, seed=1),
               replace(self.ctx, software_versions={"torch": "latest"}),
               replace(self.ctx, source_kind="DATASET")]
        for context in bad:
            with self.subTest(context=context), self.assertRaises(ValueError):
                self.runner._condition(context)
        self.assertIsNone(self.runner.backend)

    def test_identity_mismatch_rejected(self):
        self.runner.identity = replace(iv.IDENTITY, immutable_revision="b" * 40)
        with self.assertRaisesRegex(ValueError, "EXACT_MODEL"):
            self.runner.initialize(self.ctx)

    def test_offline_environment_required(self):
        with patch.dict("os.environ", {"HF_HUB_OFFLINE": "0"}), self.assertRaises(ValueError):
            self.runner.initialize(self.ctx)
        self.assertEqual(self.runner.model_load_count, 0)

    def test_installed_software_mismatch_before_backend(self):
        with patch.object(iv, "software_versions", return_value={}), self.assertRaises(ValueError):
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
        record = iv.exception_record(ValueError("bad interface"), "PREPARE", self.torch)
        self.assertEqual(record["status"], "RUNTIME_INTERFACE_FAILURE")

    def test_decode_failure_preserves_ids_without_adapter(self):
        self.processor.decode_error = ValueError("fake decode failure")
        adapter = Mock()
        adapter.version, adapter.parser_version = "test", "test"
        result = execute_call(self.runner, adapter, iv.VerifiedRawStore(self.repo), self.request, self.ctx)
        self.assertEqual(result.error.code, ErrorCode.GENERATION_FAILURE)
        self.assertFalse(adapter.adapt.called)
        raw = json.loads((self.repo / result.raw_output.path).read_bytes())
        self.assertIn("generated_ids_full", raw)
        self.assertEqual(self.runner.failure["stage"], "NATIVE_DECODE")

    def test_state_drift_fails_with_preserved_output(self):
        self.model.drift = True
        result = execute_call(self.runner, iv.PendingInternVL3Adapter(), iv.VerifiedRawStore(self.repo),
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
        class ObservingAdapter(iv.PendingInternVL3Adapter):
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
        result = execute_call(self.runner, ObservingAdapter(), iv.VerifiedRawStore(self.repo), self.request, self.ctx)
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
            result = execute_call(self.runner, adapter, iv.VerifiedRawStore(self.repo), self.request, self.ctx)
        self.assertEqual(result.error.code, ErrorCode.RAW_PRESERVATION_FAILURE)
        adapter.adapt.assert_not_called()

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
        self.assertEqual(report["classification"], "CANDIDATE")
        self.assertEqual(report["grounding"], "NOT_YET_DOCUMENTARILY_QUALIFIED")
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
                iv.probe_hardware(torch)
        self.assertEqual(iv.probe_hardware(fake_torch())["visible_gpu_count"], 1)

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
            grounding = iv.PendingInternVL3Adapter().adapt(raw, Task.GROUNDING)
            classification = iv.PendingInternVL3Adapter().adapt(raw, Task.CLASSIFICATION)
            self.assertEqual(grounding.parse_status, ParseStatus.UNSUPPORTED)
            self.assertEqual(classification.parse_status, ParseStatus.INVALID)
            self.assertIsNone(grounding.value)
            self.assertIsNone(classification.value)

    def test_raw_size_mismatch_and_metadata_corruption_rejected(self):
        with TemporaryDirectory() as directory:
            store = iv.VerifiedRawStore(Path(directory))
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
        pins = dict(line.split("==") for line in (snap.ROOT / "requirements-internvl3-t4.txt").read_text().splitlines()
                    if "==" in line)
        self.assertEqual({k: v for k, v in plan["software"].items() if k != "python"}, pins)
        provenance = json.loads((snap.ROOT / "configs/pre_freeze/local_model_provenance.d9.json").read_bytes())
        entry = next(m for m in provenance["models"] if m["key"] == "internvl3_2b_hf")
        weight = next(f for f in plan["snapshot_files"] if f["path"] == "model.safetensors")
        self.assertEqual(weight["expected_hash"], entry["weight_provenance"]["files"][0]["lfs_sha256"])
        self.assertEqual(weight["size_bytes"], entry["weight_provenance"]["files"][0]["size_bytes"])
        self.assertFalse(plan["trust_remote_code"])
        self.assertEqual(plan["real_runtime_status"], "NOT_RUN")
        self.assertFalse(plan["inspecsafe_inference_authorized"])

    def test_source_has_no_dataset_input_or_runtime_downloader(self):
        runner = (snap.ROOT / "safeshift/runners/internvl3.py").read_text()
        harness = (snap.ROOT / "scripts/w2_internvl3_t4_smoke.py").read_text()
        for source in (runner, harness):
            for forbidden in ("data/raw", "InspecSafe-V1", "dataset_manifest", "snapshot_download(", "--image-path"):
                self.assertNotIn(forbidden, source)
        self.assertIn('source_kind != "HANDCRAFTED_RUNTIME_SMOKE"', runner)


if __name__ == "__main__":
    unittest.main()
