"""Synthetic CPU boundaries; real pinned-source/meta rehearsal is a separate CLI."""
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from safeshift.pilot import phi_attention as a
from safeshift.pilot import bootstrap as b
from safeshift.pilot.artifacts import import_archive, read, sha, write
from safeshift.pilot.backend import NativeBackend
from safeshift.pilot.contract import MODELS
from test_pilot_bootstrap import supervisor_case

ROOT = Path(__file__).resolve().parents[1]
AUTO_MAP = {"AutoConfig": "configuration_phi3_v.Phi3VConfig",
            "AutoModelForCausalLM": "modeling_phi3_v.Phi3VForCausalLM"}


class Config:
    def __init__(self, attention="eager", **kwargs):
        self._attn_implementation_internal = attention
        self.__dict__.update(kwargs)

    @property
    def _attn_implementation(self):
        return self._attn_implementation_internal or "eager"

    @_attn_implementation.setter
    def _attn_implementation(self, value):
        self._attn_implementation_internal = value


class Phi3Attention:
    def __init__(self, config):
        self.config = config


class CLIPAttention(Phi3Attention):
    pass


def fake_model():
    config, clip = Config(num_hidden_layers=2), Config(num_hidden_layers=1)
    decoder = [NS(self_attn=Phi3Attention(config)) for _ in range(2)]
    layers = [NS(self_attn=CLIPAttention(clip))]
    vision = NS(config=clip, vision_model=NS(encoder=NS(layers=layers)))
    parts = [x.self_attn for x in decoder + layers]
    return NS(config=config, model=NS(config=config, _attn_implementation="eager", layers=decoder,
                                     vision_embed_tokens=NS(img_processor=vision)),
              named_modules=lambda: [(str(i), x) for i, x in enumerate(parts)])


@contextmanager
def fake_transformers(declared="flash_attention_2"):
    module = ModuleType("synthetic_phi_modeling")
    module.CLIP_VIT_LARGE_PATCH14_336_CONFIG = Config(None)
    module.Phi3Attention = Phi3Attention
    cls = type("Phi3VForCausalLM", (), {"__module__": module.__name__})
    original = Config(declared)
    auto = Mock(return_value=original)
    transformer = NS(__version__="4.43.3", AutoConfig=NS(from_pretrained=auto))
    dynamic = NS(get_class_from_dynamic_module=Mock(return_value=cls))
    clip = NS(CLIPAttention=CLIPAttention)
    with patch.dict(sys.modules, {module.__name__: module, "transformers": transformer,
                                 "transformers.dynamic_module_utils": dynamic,
                                 "transformers.models.clip.modeling_clip": clip}), \
            patch.object(a, "verified_sources", return_value=({}, {"auto_map": AUTO_MAP,
                                                                   "_attn_implementation": declared})):
        yield module, transformer, dynamic, original, auto


class SourceTests(unittest.TestCase):
    def test_source_checksum_and_auto_map_before_remote_execution(self):
        for defect in ("checksum", "map"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                for name in a.PHI_ATTENTION_FILES:
                    write(root / name, {"auto_map": AUTO_MAP} if name == "config.json" else {})
                if defect == "map":
                    payload = read(root / "config.json")
                    payload["auto_map"]["AutoModelForCausalLM"] = "outside/repo--model.Bad"
                    (root / "config.json").write_text(json.dumps(payload))
                hashes = {n: sha(root / n) for n in a.PHI_ATTENTION_FILES}
                if defect == "checksum":
                    (root / "modeling_phi3_v.py").write_bytes(b"SYNTHETIC_TAMPER")
                with patch("safeshift.pilot.backend.check_source_review", return_value={"files": hashes}):
                    with self.assertRaisesRegex(ValueError, "SOURCE_CHECKSUM|AUTO_MAP"):
                        with a.eager_phi(ROOT, root):
                            self.fail("Remote import must not be reached")


class ConfigTests(unittest.TestCase):
    def test_eager_and_flash_checkpoint_config_copies_and_clip_scope(self):
        for declared in ("eager", "flash_attention_2"):
            with self.subTest(declared=declared), fake_transformers(declared) as f:
                module, _, _, original, auto = f
                clip = module.CLIP_VIT_LARGE_PATCH14_336_CONFIG
                for failure in (False, True):
                    try:
                        with a.eager_phi(ROOT, "SYNTHETIC") as (cfg, _, _, receipt):
                            a.require_eager(cfg)
                            a.require_eager(module.CLIP_VIT_LARGE_PATCH14_336_CONFIG)
                            self.assertIsNot(cfg, original)
                            self.assertIsNot(module.CLIP_VIT_LARGE_PATCH14_336_CONFIG, clip)
                            self.assertEqual(receipt["deserialized_attention"], declared)
                            self.assertEqual(original._attn_implementation, declared)
                            if failure:
                                raise RuntimeError("SYNTHETIC_LOAD_FAILED")
                    except RuntimeError:
                        self.assertTrue(failure)
                    self.assertIs(module.CLIP_VIT_LARGE_PATCH14_336_CONFIG, clip)
                    self.assertIsNone(clip._attn_implementation_internal)
                self.assertEqual(auto.call_args.kwargs["attn_implementation"], "eager")
                self.assertTrue(auto.call_args.kwargs["local_files_only"])
                self.assertEqual(auto.call_args.kwargs["revision"], MODELS["phi"]["revision"])

    def test_wrong_transformers_is_blocked_before_config_import(self):
        with fake_transformers() as (_, transformer, _, _, auto):
            transformer.__version__ = "4.51.3"
            with self.assertRaisesRegex(RuntimeError, "PINNED_TRANSFORMERS"):
                with a.eager_phi(ROOT, "SYNTHETIC"):
                    self.fail()
            auto.assert_not_called()

    def test_property_default_eager_does_not_count_as_explicit_eager(self):
        with self.assertRaisesRegex(ValueError, "EXPLICIT_EAGER"):
            a.require_eager(Config(None))

    def test_native_loader_passes_config_and_preserves_gpu_fp16_crops(self):
        # Stop at model-load error: inspect the actual NativeBackend boundary.
        with fake_transformers() as (_, transformer, _, _, _), tempfile.TemporaryDirectory() as d:
            loader = Mock(side_effect=ImportError("SYNTHETIC_WEIGHT_LOAD_ERROR"))
            processor = Mock(return_value=NS())
            transformer.AutoModelForCausalLM = NS(from_pretrained=loader)
            transformer.AutoProcessor = NS(from_pretrained=processor)
            with patch.dict(sys.modules, {"torch": NS(float16="SYNTHETIC_FP16")}):
                with self.assertRaisesRegex(ImportError, "SYNTHETIC_WEIGHT_LOAD_ERROR"):
                    NativeBackend("phi", "SYNTHETIC", "C1", repo=ROOT, evidence=d)
            args = loader.call_args.kwargs
            a.require_eager(args["config"])
            self.assertEqual(args["attn_implementation"], "eager")
            self.assertEqual(args["torch_dtype"], "SYNTHETIC_FP16")
            self.assertEqual(args["device_map"], {"": 0})
            self.assertTrue(args["use_safetensors"])
            self.assertTrue(args["local_files_only"])
            self.assertEqual(args["revision"], MODELS["phi"]["revision"])
            self.assertEqual(args["code_revision"], MODELS["phi"]["revision"])
            self.assertEqual(processor.call_args.kwargs["num_crops"], 16)
            self.assertEqual(read(Path(d) / "phi_attention_config.json")["checkpoint_attention"],
                             "flash_attention_2")
            self.assertFalse((Path(d) / "phi_attention_runtime.json").exists())


class ModuleTests(unittest.TestCase):
    def verify(self, model):
        with fake_transformers():
            return a.verify_phi_attention(model, NS(Phi3Attention=Phi3Attention))

    def test_actual_eager_classes_and_full_layer_counts(self):
        result = self.verify(fake_model())
        self.assertEqual((result["decoder_layers"], result["vision_layers"]), (2, 1))

    def test_attention_config_and_coverage_drift_fail_closed(self):
        for defect in ("config", "cached", "clip", "missing_decoder", "missing_vision"):
            with self.subTest(defect=defect):
                model = fake_model()
                if defect == "config":
                    model.config._attn_implementation = "flash_attention_2"
                elif defect == "cached":
                    model.model._attn_implementation = "sdpa"
                elif defect == "clip":
                    model.model.vision_embed_tokens.img_processor.config._attn_implementation = None
                elif defect == "missing_decoder":
                    model.model.layers.pop()
                else:
                    model.model.vision_embed_tokens.img_processor.vision_model.encoder.layers.clear()
                with self.assertRaises(ValueError):
                    self.verify(model)

    def test_flash_sdpa_and_clip_fa2_are_rejected_even_as_subclasses(self):
        for name in ("Phi3FlashAttention2", "Phi3SdpaAttention", "CLIPAttentionFA2", "CLIPSdpaAttention"):
            with self.subTest(name=name):
                model = fake_model()
                layer = (model.model.layers[0] if name.startswith("Phi") else
                         model.model.vision_embed_tokens.img_processor.vision_model.encoder.layers[0])
                layer.self_attn = type(name, (type(layer.self_attn),), {})(layer.self_attn.config)
                with self.assertRaisesRegex(ValueError, "NON_EAGER"):
                    self.verify(model)

    def test_extra_flash_module_is_rejected(self):
        model = fake_model()
        model.named_modules = lambda: [("unanticipated", type("OtherFlashAttention", (), {})())]
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_ATTENTION"):
            self.verify(model)


class CpuAdmissionTests(unittest.TestCase):
    def test_probe_download_allows_only_three_reviewed_text_code_files(self):
        download = Mock(return_value="SYNTHETIC_WRONG_REVISION")
        with patch.dict(sys.modules, {"huggingface_hub": NS(snapshot_download=download)}):
            with self.assertRaisesRegex(ValueError, "SNAPSHOT_REVISION"):
                a.cpu_attention_probe(ROOT)
        self.assertEqual(download.call_args.kwargs["allow_patterns"], list(a.PHI_ATTENTION_FILES))
        self.assertEqual(download.call_args.kwargs["revision"], MODELS["phi"]["revision"])

    def test_subprocess_failure_keeps_full_cpu_evidence(self):
        failed = subprocess.CompletedProcess([], 1, "SYNTHETIC_STDOUT", "SYNTHETIC_FULL_TRACEBACK" * 200)
        with patch.object(b.subprocess, "run", return_value=failed):
            with self.assertRaises(RuntimeError) as caught:
                b.validate_runtime_environment(Path("python"), Path("venv"), ROOT, "phi", {})
        self.assertEqual(caught.exception.cpu_probe_failure["stderr"], failed.stderr)

    def test_attention_cpu_failure_exports_without_gpu_worker_or_attempt(self):
        with supervisor_case() as case:
            failure = RuntimeError("PHI_NON_EAGER_VISION_ATTENTION")
            failure.cpu_probe_failure = {"returncode": 1, "stdout": "SYNTHETIC", "stderr": "FULL_TRACEBACK"}
            with patch.object(b, "validate_runtime_environment", side_effect=failure), \
                    patch.object(b, "gpu_preflight", side_effect=AssertionError("NO_GPU")):
                out = b.launch("phi", case[4]["source_sha256"], ROOT, case[1], case[2],
                               scratch_root=case[0] / "tmp")
            self.assertFalse(read(out / "session.json")["attempt_consumed"])
            self.assertFalse((case[2] / "data/processed/three_vlm_attempts" / case[4]["attempt_id"]).exists())
            self.assertFalse(any("safeshift.pilot.runner" in cmd for cmd, _ in case[5]))
            self.assertEqual(read(out / "runtime_preflight.json")["cpu_probe_failure"], failure.cpu_probe_failure)
            recovered = import_archive(out.with_suffix(".zip"), case[0] / "recovered-attention")
            self.assertEqual(read(recovered / "runtime_preflight.json")["status"], "BLOCKED")
            self.assertEqual(len(read(recovered / "recovered_report/comparison.json")), 160)


if __name__ == "__main__":
    unittest.main()
