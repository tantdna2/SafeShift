"""Local fakes/bytes only. Never import or execute downloaded model source."""

from contextlib import contextmanager, nullcontext
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, patch

from safeshift.runners import moondream2 as runner
from safeshift.runners import moondream_binding as binding
from safeshift.runners import moondream_snapshot as snapshot
from safeshift.runners.contracts import (
    GenerationFailure, ModelIdentity, Request, RunContext, Task, execute_call,
)
from safeshift.runners.storage import FileRawStore
from scripts import w2_moondream_t4_smoke as smoke
from scripts import provision_moondream_snapshot as provision

ROOT = Path(__file__).resolve().parents[1]


def context():
    return RunContext("fake-run", "fake-call", runner.DECODING, runner.PREPROCESSING,
                      "FP16", "NONE", {"placement": "cuda:0"}, runner.load_plan()["software"],
                      "a" * 40, "fake-only", "HANDCRAFTED_SMOKE_ONLY")


class Tensor:
    transfers = []

    def __init__(self, dtype="float16", device="cuda:0"):
        self.dtype, self.device, self.shape = dtype, device, (2, 3, 378, 378)

    def to(self, *, device):
        self.transfers.append((self.dtype, self.device, device))
        return Tensor(self.dtype, device)

    def is_floating_point(self):
        return self.dtype in {"float16", "bfloat16", "float32"}

    def zero_(self):
        return self


TORCH = types.SimpleNamespace(Tensor=Tensor, float16="float16", is_tensor=lambda v: type(v) is Tensor,
                              inference_mode=nullcontext)


def fake_modules():
    # Entirely handcrafted test program; not copied from upstream source.
    moon = types.ModuleType("synthetic_moon")
    exec("class MoondreamModel:\n"
         " def _run_vision_encoder(self, image):\n"
         "  result = prepare_crops(image, self.config.vision, device=self.device)\n"
         "  return self._vis_enc(result[0])\n"
         " def _vis_enc(self, crops):\n"
         "  return vision_encoder(crops)\n", vars(moon))
    events = []
    def prepare(image, config, *, device):
        events.append(("upstream_normalization_completed", device))
        return Tensor("bfloat16", "cpu"), (1, 1)
    vision = types.SimpleNamespace(prepare_crops=prepare, vision_encoder=lambda t: t)
    overlap = object()
    prepare.__globals__["overlap_crop_image"] = overlap
    image = object()
    crops = types.SimpleNamespace(HAS_VIPS=False, Image=image, overlap_crop_image=overlap)
    moon.prepare_crops, moon.vision_encoder = prepare, vision.vision_encoder
    inner = moon.MoondreamModel()
    inner.device = "cuda:0"
    inner.config = types.SimpleNamespace(vision=object())
    modules = {"moondream": moon, "vision": vision, "image_crops": crops}
    with patch.object(binding, "verify_function", side_effect=lambda f, *a: f):
        hook = binding.VisionBinding(inner, modules, "unused", TORCH, image)
    return inner, modules, hook, events


def fake_model():
    cache = types.SimpleNamespace(k_cache=Tensor(), v_cache=Tensor())
    config = types.SimpleNamespace(text=types.SimpleNamespace(group_size=None),
                                   region=types.SimpleNamespace(group_size=None))
    inner = types.SimpleNamespace(config=config, text=types.SimpleNamespace(blocks=[types.SimpleNamespace(kv_cache=cache)]))
    model = types.SimpleNamespace(model=inner)
    model.named_parameters = lambda: [("weight", Tensor())]
    model.named_buffers = lambda: [("rope", Tensor()), ("mask", Tensor("bool"))]
    model.modules = lambda: [model]
    return model


class PlanTests(unittest.TestCase):
    def test_exact_pins_and_one_of_each(self):
        p = runner.load_plan()
        self.assertEqual((p["model_id"], p["model_revision"]), (snapshot.MODEL_ID, snapshot.REVISION))
        self.assertEqual((p["tokenizer_repo"], p["tokenizer_revision"]), (snapshot.TOKENIZER_REPO, snapshot.TOKENIZER_REVISION))
        self.assertEqual([p[k] for k in ("expected_model_loads", "expected_query_calls", "expected_detect_calls")], [1, 1, 1])
        self.assertEqual(p["resize_backend"], "PILLOW_ONLY")
        for key in ("t4_smoke_run", "model_inference_used", "synthetic_gate_run", "inspecsafe_used", "full_fp16_runtime_validated"):
            self.assertIs(p[key], False)

    def test_fixture_hash_and_separate_path(self):
        b = smoke.fixture_bytes()
        self.assertEqual(hashlib.sha256(b).hexdigest(), "aa44c8cbb27ddcdf294a32904cdf7dbbc4bebe027245ed93bd6a6dbce1d3e9cd")
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder) / runner.load_plan()["smoke_fixture_path"]
            f.parent.mkdir(parents=True)
            f.write_bytes(b + b"changed")
            with self.assertRaises(ValueError):
                smoke.fixture_bytes(Path(folder))

    def test_wrong_bridge_version_status_and_mutable_plan_rejected(self):
        p = runner.load_plan()
        for key, value in (("bridge_version", "wrong"), ("bridge_status", "PASS"),
                           ("model_revision", "main"), ("tokenizer_revision", "latest")):
            with self.subTest(key=key), patch.object(Path, "read_text", return_value=json.dumps({**p, key: value})):
                with self.assertRaises(ValueError):
                    runner.load_plan()

    def test_no_point_to_box_or_dataset_import(self):
        for path in ("safeshift/runners/moondream2.py", "safeshift/runners/moondream_binding.py",
                     "safeshift/runners/moondream_snapshot.py", "scripts/w2_moondream_t4_smoke.py",
                     "scripts/provision_moondream_snapshot.py"):
            source = (ROOT / path).read_text(encoding="utf-8").lower()
            self.assertNotIn("inspecsafe", source)
            self.assertNotIn("point_to_box", source)
            self.assertNotIn(".clamp(", source)
        p = runner.load_plan()
        for key in ("retry", "tuning", "model_substitution", "automatic_precision_fallback",
                    "automatic_quantization_fallback", "cpu_offload", "disk_offload", "device_map_auto"):
            self.assertEqual(p[key], "FORBIDDEN")


class SnapshotTests(unittest.TestCase):
    def test_wrong_repo_revision_and_alias_rejected(self):
        for repo, rev in (("other/model", snapshot.REVISION), (snapshot.MODEL_ID, "main"),
                          (snapshot.TOKENIZER_REPO, "latest"), (snapshot.TOKENIZER_REPO, "a" * 40)):
            with self.subTest(repo=repo, rev=rev), self.assertRaises(ValueError):
                snapshot.verify_snapshot("arbitrary", repo, rev)

    def test_arbitrary_directory_rejected(self):
        with self.assertRaises(ValueError):
            snapshot.verify_snapshot("arbitrary", snapshot.MODEL_ID, snapshot.REVISION)

    def test_every_audited_artifact_reused(self):
        audit = json.loads((ROOT / snapshot.AUDIT_PATH).read_text(encoding="utf-8"))
        combined = snapshot.artifact_rows(snapshot.MODEL_ID, snapshot.REVISION) + snapshot.artifact_rows(snapshot.TOKENIZER_REPO, snapshot.TOKENIZER_REVISION)
        self.assertEqual(sorted(combined, key=lambda r: (r["repo_id"], r["path"])),
                         sorted(audit["artifacts"], key=lambda r: (r["repo_id"], r["path"])))

    def test_local_bytes_hash_size_and_unreviewed_file_enforced(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "models--moondream--starmie-v1" / "snapshots" / snapshot.TOKENIZER_REVISION
            p.mkdir(parents=True)
            b = b'local synthetic tokenizer bytes'
            row = {"path": "tokenizer.json", "size_bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(), "verification": "TEST"}
            f = p / "tokenizer.json"
            f.write_bytes(b)
            with patch.object(snapshot, "artifact_rows", return_value=[row]):
                result = snapshot.verify_snapshot(p, snapshot.TOKENIZER_REPO, snapshot.TOKENIZER_REVISION)
                self.assertTrue(result["local_bytes_verified"])
                f.write_bytes(b[:-1] + b"X")
                with self.assertRaisesRegex(ValueError, "ARTIFACT_MISMATCH"):
                    snapshot.verify_snapshot(p, snapshot.TOKENIZER_REPO, snapshot.TOKENIZER_REVISION)
                f.write_bytes(b)
                (p / "evil.py").write_text("# unreviewed")
                with self.assertRaisesRegex(ValueError, "UNREVIEWED"):
                    snapshot.verify_snapshot(p, snapshot.TOKENIZER_REPO, snapshot.TOKENIZER_REVISION)

    def test_verify_only_does_not_import_hub_or_download(self):
        with patch.object(provision, "deny_network_permanently") as denied, patch.object(provision, "verify_snapshot", return_value={}) as verify:
            provision.provision_or_verify("fake-cache")
            denied.assert_called_once()
            self.assertEqual(verify.call_count, 2)

    def test_permanent_network_boundary_in_separate_local_process(self):
        code = "from safeshift.runners.moondream_snapshot import deny_network_permanently; import socket; deny_network_permanently(); socket.getaddrinfo('example.invalid', 443)"
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("NETWORK_OR_CHILD_PROCESS_FORBIDDEN", result.stderr)

    def test_load_without_offline_rejected(self):
        with patch.object(snapshot, "_offline", False), self.assertRaises(RuntimeError):
            binding.load_verified_modules("not-read")


class TokenizerTests(unittest.TestCase):
    def setUp(self):
        self.module = types.ModuleType("synthetic_constructor")
        exec('class MoondreamModel:\n def __init__(self):\n  self.tokenizer = Tokenizer.from_pretrained("moondream/starmie-v1")\n', vars(self.module))
        self.native = types.SimpleNamespace(from_file=Mock(return_value=object()))
        self.module.Tokenizer = self.native
        self.stack = []
        for target, kwargs in (("require_offline", {}), ("verify_snapshot", {"return_value": {}}),
                               ("verify_function", {"side_effect": lambda f, *a: f})):
            p = patch.object(binding, target, **kwargs)
            p.start()
            self.addCleanup(p.stop)

    def redirect(self):
        return binding.starmie_redirect(self.module, "fake", "fake", self.native)

    def test_exact_request_uses_from_file_and_actual_object_then_restores(self):
        with self.redirect() as evidence:
            obj = self.module.MoondreamModel()
            self.assertIs(obj.tokenizer, evidence["tokenizer"])
        self.assertIs(self.module.Tokenizer, self.native)
        self.assertEqual(evidence["calls"], 1)
        self.native.from_file.assert_called_once_with(str(Path("fake") / "tokenizer.json"))

    def test_unexpected_call_site_repo_or_revision_fails_and_restores(self):
        for args, kwargs in ((("other/repo",), {}), ((snapshot.TOKENIZER_REPO,), {"revision": "main"}),
                             ((snapshot.TOKENIZER_REPO,), {})):
            with self.subTest(args=args, kwargs=kwargs), self.assertRaises(ValueError):
                with self.redirect():
                    self.module.Tokenizer.from_pretrained(*args, **kwargs)
            self.assertIs(self.module.Tokenizer, self.native)

    def test_second_constructor_rejected(self):
        with self.assertRaises(ValueError):
            with self.redirect():
                self.module.MoondreamModel()
                self.module.MoondreamModel()

    def test_constructor_exception_restores(self):
        self.native.from_file.side_effect = RuntimeError("synthetic failure")
        with self.assertRaises(RuntimeError):
            with self.redirect():
                self.module.MoondreamModel()
        self.assertIs(self.module.Tokenizer, self.native)

    def test_tampered_binding_restored_and_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "RESTORATION"):
            with self.redirect():
                self.module.MoondreamModel()
                self.module.Tokenizer = object()
        self.assertIs(self.module.Tokenizer, self.native)


class VisionTests(unittest.TestCase):
    def setUp(self):
        self.inner, self.modules, self.hook, self.events = fake_modules()
        Tensor.transfers = []

    def bridge(self, result):
        self.assertEqual(self.events, [("upstream_normalization_completed", "cpu")])
        self.assertEqual(result[0].dtype, "bfloat16")
        self.assertEqual(result[1], (1, 1))
        return Tensor("float16", "cpu"), result[1]

    def test_bridge_order_entire_tuple_cpu_only_then_fp16_cuda(self):
        original = self.inner._run_vision_encoder.__func__
        global_prepare = original.__globals__["prepare_crops"]
        with patch.object(binding.precision, "post_normalization_fp16_bridge", side_effect=self.bridge) as bridge:
            with self.hook.installed():
                installed = self.inner._run_vision_encoder.__func__
                self.assertIs(installed.__code__, original.__code__)
                self.assertIsNot(installed.__globals__, original.__globals__)
                for name, value in original.__globals__.items():
                    if name != "prepare_crops":
                        self.assertIs(installed.__globals__[name], value)
                self.inner._run_vision_encoder("synthetic")
            bridge.assert_called_once()
        self.assertEqual(Tensor.transfers, [("float16", "cpu", "cuda:0")])
        self.assertIs(original.__globals__["prepare_crops"], global_prepare)
        self.assertIs(self.inner._run_vision_encoder.__func__, original)
        self.assertNotIn("_run_vision_encoder", vars(self.inner))
        self.assertNotIn("_vis_enc", vars(self.inner))
        self.assertEqual(len(self.hook.events), 3)

    def test_bad_bridge_output_never_transfers_bf16_or_fp32(self):
        for dtype, device in (("bfloat16", "cpu"), ("float32", "cpu"), ("float16", "cuda:0")):
            self.inner, self.modules, self.hook, self.events = fake_modules()
            with self.subTest(dtype=dtype, device=device), patch.object(binding.precision, "post_normalization_fp16_bridge", return_value=(Tensor(dtype, device), (1, 1))):
                with self.assertRaises(ValueError):
                    with self.hook.installed():
                        self.inner._run_vision_encoder("synthetic")
                self.assertEqual(Tensor.transfers, [])
                self.assertNotIn("_run_vision_encoder", vars(self.inner))

    def test_incorrect_transfer_result_fails_before_vision(self):
        with patch.object(binding.precision, "post_normalization_fp16_bridge", side_effect=self.bridge), \
                patch.object(Tensor, "to", return_value=Tensor("bfloat16", "cuda:0")):
            with self.assertRaisesRegex(ValueError, "FP16_IMAGE_BOUNDARY"):
                with self.hook.installed():
                    self.inner._run_vision_encoder("synthetic")
        self.assertFalse(any(e["boundary"] == "vision_consumption" for e in self.hook.events))
        self.assertFalse(self.hook.valid)

    def test_binding_restored_on_exception_and_prior_shadow_preserved(self):
        prior = self.inner._run_vision_encoder
        self.inner._run_vision_encoder = prior
        with self.assertRaisesRegex(RuntimeError, "synthetic"):
            with self.hook.installed():
                raise RuntimeError("synthetic")
        self.assertIs(self.inner._run_vision_encoder, prior)

    def test_intervening_change_invalidates_instance(self):
        with self.assertRaisesRegex(RuntimeError, "RESTORATION"):
            with self.hook.installed():
                self.inner._vis_enc = object()
        self.assertFalse(self.hook.valid)
        with self.assertRaises(ValueError):
            self.hook.check()

    def test_original_globals_and_instance_function_identity_required(self):
        self.modules["moondream"].prepare_crops = lambda *a: None
        with self.assertRaises(ValueError):
            self.hook.check()
        self.modules["moondream"].prepare_crops = self.hook.prepare
        self.inner._run_vision_encoder = types.MethodType(lambda s, i: None, self.inner)
        with self.assertRaises(ValueError):
            self.hook.check()

    def test_preconsumption_boundary_rejects_changed_tensor(self):
        with patch.object(binding.precision, "post_normalization_fp16_bridge", side_effect=self.bridge):
            with self.assertRaises(ValueError):
                with self.hook.installed():
                    self.inner._vis_enc(Tensor("bfloat16"))

    def test_pyvips_or_unknown_backend_rejected(self):
        for flag in (True, None, "Pillow"):
            self.modules["image_crops"].HAS_VIPS = flag
            with self.assertRaises(ValueError):
                self.hook.check()

    def test_exact_compiled_function_identity_without_remote_execution(self):
        module = types.ModuleType("local_test")
        source = b"def local(x):\n return x + 3\n"
        exec(source, vars(module))
        with patch.object(binding, "verified_source", return_value=source):
            binding.verify_function(module.local, module, "unused", "test.py", "local")
            module.local.__code__ = (lambda x: x - 3).__code__
            with self.assertRaises(ValueError):
                binding.verify_function(module.local, module, "unused", "test.py", "local")


class RuntimeTests(unittest.TestCase):
    def test_runner_lifecycle_one_load_and_two_calls_with_fake_backend(self):
        model = fake_model()
        model.query = Mock(return_value={"answer": "native", "extra": [1, 2]})
        model.detect = Mock(return_value={"objects": [{"x_min": -0.2, "y_min": 0.1, "x_max": 1.2, "y_max": 0.9}]})
        hook = types.SimpleNamespace(events=[], installed=nullcontext, valid=True)
        image = types.SimpleNamespace(load=Mock())
        backend = types.SimpleNamespace(
            software=context().software_versions, torch=TORCH,
            image=types.SimpleNamespace(open=Mock(return_value=image)),
            metadata=Mock(return_value={"cuda_available": True, "gpu_count": 1, "name": "Tesla T4",
                                        "compute_capability": [7, 5], "total_memory": 15 * 1024**3}),
            load=Mock(return_value=(model, hook)))
        r = runner.Moondream2Runner("fake-model", "fake-tokenizer", backend_factory=lambda: backend)
        with patch.object(runner, "deny_network_permanently"), patch.object(runner, "require_offline"), \
                patch.object(runner, "verify_snapshot", return_value={}), patch.object(runner, "_load_claimed", False):
            for task in (Task.CLASSIFICATION, Task.GROUNDING):
                r.initialize(context())
                r.load(context())
                prepared = r.prepare_input(Request(task, "s", "i", b"synthetic", "p", "prompt"), context())
                raw = r.generate_raw(prepared, context())
            backend.load.assert_called_once()
            backend.metadata.assert_called_once()
            model.query.assert_called_once()
            model.detect.assert_called_once()
            self.assertEqual(runner.deserialize_native(raw)["objects"][0]["x_min"], -0.2)
            self.assertEqual(len(r.evidence["state_audits"]), 5)
            self.assertEqual(r.evidence["model_load_count"], 1)

    def test_failed_load_invalidates_and_cannot_retry(self):
        backend = types.SimpleNamespace(load=Mock(side_effect=RuntimeError("fake load")))
        r = runner.Moondream2Runner("fake", "fake")
        r.backend = backend
        with patch.object(runner, "require_offline"), patch.object(runner, "verify_snapshot", return_value={}), \
                patch.object(runner, "_load_claimed", False):
            with self.assertRaises(RuntimeError):
                r.load(context())
            self.assertFalse(r.valid)
            with self.assertRaises(ValueError):
                r.load(context())
        backend.load.assert_called_once()

    def test_post_native_failure_retains_raw_and_invalidates(self):
        r = runner.Moondream2Runner("fake", "fake")
        r.model = fake_model()
        r.model.query = Mock(return_value={"answer": "returned before audit failure"})
        r.backend = types.SimpleNamespace(torch=TORCH)
        r.binding = types.SimpleNamespace(installed=nullcontext)
        with patch.object(runner, "require_offline"), patch.object(runner, "audit_model_state", side_effect=[[], ValueError("fake dtype")]):
            with self.assertRaises(GenerationFailure) as caught:
                r.generate_raw((Task.CLASSIFICATION, object(), "prompt"), context())
        self.assertEqual(runner.deserialize_native(caught.exception.partial_raw)["answer"], "returned before audit failure")
        self.assertFalse(r.valid)

    def test_reentrant_owner_rejected(self):
        with snapshot.exclusive_owner():
            with self.assertRaises(RuntimeError):
                with snapshot.exclusive_owner():
                    self.fail("entered twice")

    def test_concurrent_owner_rejected(self):
        errors = []
        def worker():
            try:
                with snapshot.exclusive_owner():
                    errors.append("entered")
            except RuntimeError:
                errors.append("rejected")
        t = threading.Thread(target=worker)
        t.start()
        t.join()
        self.assertEqual(errors, ["rejected"])

    def test_t4_contract_with_mock_metadata(self):
        good = {"cuda_available": True, "gpu_count": 1, "name": "Tesla T4", "compute_capability": [7, 5], "total_memory": 15 * 1024**3}
        runner.validate_device(good)
        for key, value in (("cuda_available", False), ("gpu_count", 0), ("gpu_count", 2),
                           ("name", "NVIDIA A100"), ("compute_capability", [8, 0]), ("total_memory", 24 * 1024**3)):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                runner.validate_device({**good, key: value})

    def test_identity_precision_quantization_offload_batch_and_fallback_rejected(self):
        r = runner.Moondream2Runner("unused", "unused")
        r._condition(context())
        for change in ({"precision": "BF16"}, {"precision": "FP32"}, {"quantization": "INT8"},
                       {"device": {"placement": "auto"}}, {"device": {"placement": "cuda:0", "cpu_offload": True}},
                       {"device": {"placement": "cuda:0", "disk_offload": True}},
                       {"device": {"placement": "cuda:0", "batch_size": 2}},
                       {"device": {"placement": "cuda:0", "fallback": True}}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                r._condition(replace(context(), **change))
        r.identity = ModelIdentity("wrong/model", snapshot.REVISION, "test")
        with self.assertRaises(ValueError):
            r._condition(context())
        with self.assertRaises(ValueError):
            ModelIdentity(snapshot.MODEL_ID, "main", "test")

    def test_model_parameter_buffer_cache_and_unregistered_state_audit(self):
        model = fake_model()
        self.assertTrue(runner.audit_model_state(model, TORCH))
        for kind in ("parameter", "buffer", "cache", "extra"):
            for dtype in ("bfloat16", "float32"):
                model = fake_model()
                if kind == "parameter":
                    model.named_parameters = lambda: [("bad", Tensor(dtype))]
                elif kind == "buffer":
                    model.named_buffers = lambda: [("bad", Tensor(dtype))]
                elif kind == "cache":
                    model.model.text.blocks[0].kv_cache.k_cache = Tensor(dtype)
                else:
                    model.extra = {"cache": [Tensor(dtype)]}
                with self.subTest(kind=kind, dtype=dtype), self.assertRaises(ValueError):
                    runner.audit_model_state(model, TORCH)

    def test_cpu_model_state_and_offload_hook_rejected(self):
        model = fake_model()
        model.named_buffers = lambda: [("bad", Tensor("float16", "cpu"))]
        with self.assertRaises(ValueError):
            runner.audit_model_state(model, TORCH)
        model = fake_model()
        model._hf_hook = object()
        with self.assertRaises(ValueError):
            runner.audit_model_state(model, TORCH)


class RawTests(unittest.TestCase):
    def test_lossless_native_fields_order_and_float_bits(self):
        value = {"objects": [{"x_min": -0.25, "y_min": -0.0, "x_max": 1.25, "y_max": 0.9}],
                 "extra": [True, None, 42, "text\ud800", float("inf"), float("nan")]}
        raw = runner.serialize_native(value)
        decoded = runner.deserialize_native(raw)
        self.assertEqual(raw, runner.serialize_native(decoded))
        self.assertEqual(list(value), list(decoded))
        self.assertEqual(struct.pack(">d", decoded["objects"][0]["y_min"]), struct.pack(">d", -0.0))
        self.assertEqual(decoded["objects"][0]["x_min"], -0.25)
        self.assertEqual(decoded["objects"][0]["x_max"], 1.25)

    def test_raw_preserved_and_checksummed_before_adapter(self):
        raw = runner.serialize_native({"objects": [{"x_min": -0.25, "y_min": 0.2, "x_max": 1.25, "y_max": 0.9}]})
        class FakeRunner:
            identity, version = runner.IDENTITY, "test"
            initialize = load = lambda *a: None
            prepare_input = lambda *a: None
            generate_raw = lambda *a: raw
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = FileRawStore(root)
            class Adapter(runner.PendingMoondreamAdapter):
                def adapt(self, content, task):
                    saved = list((root / "data/processed/local_runs").glob("*/response.raw"))
                    self_test.assertEqual(saved[0].read_bytes(), content)
                    return super().adapt(content, task)
            self_test = self
            result = execute_call(FakeRunner(), Adapter(), store,
                                  Request(Task.GROUNDING, "s", "i", b"local", "p", "red rectangle"), context())
            self.assertEqual(result.raw_output.sha256, hashlib.sha256(raw).hexdigest())
            self.assertEqual(result.parse_status.value, "UNSUPPORTED")
            self.assertEqual(result.native_evidence["objects"][0]["x_max"], 1.25)


class SmokeTests(unittest.TestCase):
    def fake_runner(self, *, fail=None):
        r = types.SimpleNamespace(identity=runner.IDENTITY, valid=True, condition=True,
                                  binding=types.SimpleNamespace(valid=True))
        r.evidence = {"model_load_count": 0, "query_call_count": 0, "detect_call_count": 0,
                      "model_manifest": {"manifest_sha256": "a" * 64},
                      "tokenizer_manifest": {"manifest_sha256": "b" * 64},
                      "state_audits": [{"status": "VALID", "observations": []}] * 5,
                      "image_boundaries": [{"boundary": k} for k in ["bridge_cpu", "transfer", "vision_consumption"] * 2]}
        r.backend = types.SimpleNamespace(torch=types.SimpleNamespace(cuda=types.SimpleNamespace(
            reset_peak_memory_stats=Mock(), max_memory_allocated=lambda d: 100, max_memory_reserved=lambda d: 200)))
        r.initialize = Mock()
        def load(ctx):
            r.evidence["model_load_count"] += 1
        r.load = Mock(side_effect=load)
        r.prepare_input = lambda request, ctx: request
        def generate(request, ctx):
            call = "query" if request.task == Task.CLASSIFICATION else "detect"
            r.evidence[call + "_call_count"] += 1
            if fail == call:
                raise GenerationFailure(runner.serialize_native({"partial": "visible"}))
            return runner.serialize_native({"answer": "synthetic"} if call == "query" else {"objects": []})
        r.generate_raw = generate
        return r

    def test_one_load_two_native_calls_and_persist_before_check(self):
        r = self.fake_runner()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = smoke.check_native
            def check(value, task):
                expected = 1 if task == Task.CLASSIFICATION else 2
                self.assertEqual(len(list(root.glob("data/processed/local_runs/*/response.raw"))), expected)
                original(value, task)
            with patch.object(smoke, "check_native", side_effect=check):
                report = smoke.run_smoke(r, run_id="test", execution_commit="a" * 40,
                                         store=FileRawStore(root), image_bytes=smoke.fixture_bytes())
        self.assertEqual(report["status"], "RUNTIME_INTERFACE_PASS")
        r.initialize.assert_called_once()
        r.load.assert_called_once()
        self.assertEqual((r.evidence["query_call_count"], r.evidence["detect_call_count"]), (1, 1))

    def test_either_call_failure_is_terminal_partial_raw_preserved(self):
        for failed in ("query", "detect"):
            r = self.fake_runner(fail=failed)
            with tempfile.TemporaryDirectory() as folder:
                report = smoke.run_smoke(r, run_id="test", execution_commit="a" * 40,
                                         store=FileRawStore(Path(folder)), image_bytes=smoke.fixture_bytes())
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(report["calls"][-1]["partial"])
            self.assertEqual(r.evidence[failed + "_call_count"], 1)
            if failed == "query":
                self.assertEqual(r.evidence["detect_call_count"], 0)

    def test_no_pass_from_successful_calls_without_invariants(self):
        r = self.fake_runner()
        r.evidence["image_boundaries"] = []
        with tempfile.TemporaryDirectory() as folder:
            report = smoke.run_smoke(r, run_id="test", execution_commit="a" * 40,
                                     store=FileRawStore(Path(folder)), image_bytes=smoke.fixture_bytes())
        self.assertEqual(report["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
