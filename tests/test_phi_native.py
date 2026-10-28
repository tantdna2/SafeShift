"""Opt-in pinned CPU integration; scripted logits are NOT research predictions.

SAFESHIFT_PHI_SNAPSHOT points to the reviewed PUBLIC text/tokenizer files only.
No checkpoint data, actual model forward, CUDA, dataset, or grant is used.
"""
from contextlib import ExitStack
import copy
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from safeshift.pilot.artifacts import Store, export, import_archive, read, sha, write, write_bytes
from safeshift.pilot.backend import NativeBackend, check_software
from safeshift.pilot.contract import GENERATION, MODELS, digest, parse_label, settings, source_digest
from safeshift.pilot.hnlo import replay
from safeshift.pilot.phi_attention import (attention_receipt, cpu_attention_probe, eager_phi, load_phi,
                                          verify_phi_attention)
from safeshift.pilot.phi_inputs import (cpu_processor_probe, load_processor, prepare_inputs, validate_inputs)
from safeshift.pilot.report import save_reports
from safeshift.pilot.runner import execute, identity

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = os.environ.get("SAFESHIFT_PHI_SNAPSHOT")


@unittest.skipUnless(SNAPSHOT, "Opt-in pinned Phi public-source CPU rehearsal; no weights")
class NativePhiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        import transformers
        from PIL import Image
        cls.torch, cls.transformers, cls.Image = torch, transformers, Image
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        cls.tmp = Path(cls.stack.enter_context(tempfile.TemporaryDirectory()))
        cls.snapshot = cls.tmp / MODELS["phi"]["revision"]
        cls.snapshot.mkdir()
        from safeshift.pilot.backend import check_source_review
        locked = check_source_review(ROOT, "phi")
        for name, checksum in locked["files"].items():
            if sha(Path(SNAPSHOT) / name) != checksum:
                raise ValueError("REHEARSAL_SOURCE_HASH:" + name)
            shutil.copyfile(Path(SNAPSHOT) / name, cls.snapshot / name)
        cls.versions = check_software(ROOT, "phi")
        cls.evidence = {"versions": cls.versions, "synthetic_only": True}
        # Any actual CUDA query/initialization, model forward or SDPA fails here.
        for name in ("init", "_lazy_init", "is_available", "device_count", "get_device_capability",
                     "synchronize", "memory_allocated", "memory_reserved", "max_memory_allocated",
                     "max_memory_reserved", "reset_peak_memory_stats"):
            cls.stack.enter_context(patch.object(torch.cuda, name, side_effect=AssertionError("REAL_CUDA_FORBIDDEN")))
        cls.stack.enter_context(patch.object(torch.nn.functional, "scaled_dot_product_attention",
                                            side_effect=AssertionError("SDPA_FORBIDDEN")))
        cls.stack.enter_context(patch.object(torch, "load", side_effect=AssertionError("PICKLE_WEIGHTS_FORBIDDEN")))
        transformers.utils.logging.set_verbosity_error()
        cls.processor = load_processor(ROOT, cls.snapshot)
        cls.prompt = (ROOT / "configs/pilot/classification_c1.txt").read_text(encoding="utf-8")

    def test_a4_and_a5_real_loader_before_after(self):
        torch = self.torch
        default_dtype = torch.get_default_dtype()
        self.addCleanup(torch.set_default_dtype, default_dtype)
        from safetensors.torch import save_file
        # Empty safetensors is a loader fixture. No trained/random weights or
        # actual forward; all 4B parameters and buffers stay metadata on meta.
        save_file({}, str(self.snapshot / "model.safetensors"), metadata={"format": "pt"})
        with eager_phi(ROOT, self.snapshot) as (config, cls, module, receipt):
            original = type(config).from_dict(read(self.snapshot / "config.json"), attn_implementation="eager")
            self.assertEqual(original._attn_implementation, "flash_attention_2")
            with torch.device("meta"), self.assertRaisesRegex(ImportError, "flash_attn"):
                cls.from_pretrained(None, config=original, state_dict={}, torch_dtype=torch.float16)
            # BASE's exact AutoModel route re-executes modeling_phi3_v, discards
            # the scoped CLIP constant, and selects CLIPSdpaAttention.
            with torch.device("meta"):
                broken = self.transformers.AutoModelForCausalLM.from_pretrained(
                    str(self.snapshot), config=config, local_files_only=True, trust_remote_code=True,
                    torch_dtype=torch.float16, attn_implementation="eager", use_safetensors=True)
            observed = attention_receipt(broken)
            self.assertEqual(observed["configs"]["model.config"]["internal"], "eager")
            self.assertEqual(observed["configs"]["model.model.vision_embed_tokens.img_processor.config"]["internal"], "sdpa")
            with self.assertRaisesRegex(ValueError, "EXPLICIT_EAGER.*img_processor.config") as caught:
                verify_phi_attention(broken, module)
            self.assertIn("vision.0.self_attn", caught.exception.phi_attention_receipt["classes"])
            self.evidence["a5_before"] = caught.exception.phi_attention_receipt
            self.evidence["a4_before"] = {"checkpoint_deserialized": original._attn_implementation,
                                          "failure": "ImportError: flash_attn required"}
        with eager_phi(ROOT, self.snapshot) as (config, cls, module, _):
            # Fixed production class, real loader, real file/config path, no
            # substituted loader methods. Device dispatch is separately unverified.
            fixed = load_phi(cls, config, self.snapshot, meta=True)
            verified = verify_phi_attention(fixed, module)
            self.assertEqual((verified["decoder_layers"], verified["vision_layers"]), (32, 24))
            self.evidence["loader_after"] = verified
            self.assertTrue(all(t.device.type == "meta" for t in (*fixed.parameters(), *fixed.buffers())))
            for value in (None, "sdpa", "flash_attention_2"):
                with self.subTest(internal=value):
                    fixed.model.vision_embed_tokens.img_processor.config._attn_implementation = value
                    with self.assertRaises(ValueError):
                        verify_phi_attention(fixed, module)
            fixed.model.vision_embed_tokens.img_processor.config._attn_implementation = "eager"
            with patch.object(cls, "forward", side_effect=AssertionError("ACTUAL_FORWARD_FORBIDDEN")), \
                    patch("huggingface_hub.snapshot_download", return_value=str(self.snapshot)):
                admission = cpu_attention_probe(ROOT)
            self.assertIn("FROM_PRETRAINED_PASS", admission["status"])
            self.evidence["cpu_attention_admission"] = admission

    def test_cpu_admission_processor_and_shapes_and_token_boundaries(self):
        with patch("huggingface_hub.snapshot_download", return_value=str(self.snapshot)) as download:
            receipt = cpu_processor_probe(ROOT)
        self.assertEqual(receipt["num_crops"], 16)
        self.evidence["cpu_processor_admission"] = receipt
        self.assertFalse(any("safetensors" in p for p in download.call_args.kwargs["allow_patterns"]))
        for size in ((1, 1), (336, 336), (640, 480), (200, 1200), (1200, 200)):
            with self.subTest(size=size), self.Image.new("RGB", size) as image:
                rendered, inputs = prepare_inputs(self.processor, self.prompt, image)
                validate_inputs(self.processor, inputs)
                from safeshift.pilot.hnlo import probe, candidate_ids
                mapping = probe(self.processor.tokenizer, rendered, inputs["input_ids"][0].tolist())
                self.assertTrue(mapping["boundary_ok"])
                self.assertGreaterEqual(len(candidate_ids(mapping)), 4)
                self.assertIn("<|assistant|>", rendered)
        for field in ("input_ids", "pixel_values", "image_sizes", "attention_mask"):
            with self.subTest(field=field), self.Image.new("RGB", (336, 336)) as image:
                _, inputs = prepare_inputs(self.processor, self.prompt, image)
                inputs[field] = inputs[field].float() if field != "pixel_values" else inputs[field].half()
                with self.assertRaises(ValueError):
                    validate_inputs(self.processor, inputs)
        with self.Image.new("RGBA", (64, 80)) as image, self.assertRaises(ValueError):
            prepare_inputs(self.processor, self.prompt, image)

    def backend(self, text='{"safety_level":"Level04"}', defect=None):
        """Only the model/hardware boundary is synthetic; native generate runs.

        Scripted next-token logits test the observer/generation contract without
        model inference. No fake backend is added to the production package.
        """
        torch, transformers = self.torch, self.transformers
        tokenizer = self.processor.tokenizer
        ids = tokenizer.encode(text, add_special_tokens=False) + [tokenizer.eos_token_id]
        class ScriptedModel(transformers.PreTrainedModel):
            config_class = transformers.PretrainedConfig
            def __init__(inner):
                super().__init__(transformers.PretrainedConfig(is_decoder=True, vocab_size=len(tokenizer),
                                 max_position_embeddings=131072))
                inner.anchor = torch.nn.Parameter(torch.zeros(1), requires_grad=False)
                inner.calls = 0
            def prepare_inputs_for_generation(inner, input_ids, **kwargs):
                return {"input_ids": input_ids, **kwargs}
            def forward(inner, input_ids, attention_mask=None, pixel_values=None, image_sizes=None,
                        past_key_values=None, use_cache=None, return_dict=None, output_attentions=None,
                        output_hidden_states=None, cache_position=None):
                if defect == "oom":
                    raise RuntimeError("SYNTHETIC out of memory")
                token = ids[inner.calls % len(ids)]
                inner.calls += 1
                logits = torch.zeros(1, 1, len(tokenizer), dtype=torch.float16)
                logits[0, 0, token] = 10
                if defect == "nonfinite":
                    logits[0, 0, 0] = float("nan")
                return transformers.modeling_outputs.CausalLMOutputWithPast(logits=logits)
        backend = NativeBackend.__new__(NativeBackend)
        backend.key, backend.prompt, backend.processor, backend.tokenizer = "phi", self.prompt, self.processor, tokenizer
        backend.model = ScriptedModel().eval()
        backend.environment = {"SYNTHETIC_CPU_TEST_NOT_RESEARCH": True, "model_boundary": "SCRIPTED_LOGITS"}
        backend.serialized_tokenizer = tokenizer.backend_tokenizer.to_str().encode()
        from tokenizers import Tokenizer
        backend.cpu_tokenizer = Tokenizer.from_str(backend.serialized_tokenizer.decode())
        backend.generation = transformers.GenerationConfig(**GENERATION, bos_token_id=tokenizer.bos_token_id,
                                                         eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.eos_token_id)
        # Explicit hardware double: real torch.cuda is forbidden in setUpClass.
        cuda = NS(**{k: (lambda *a, **kw: 0) for k in
                     ("memory_allocated", "memory_reserved", "max_memory_allocated", "max_memory_reserved",
                      "synchronize", "reset_peak_memory_stats")})
        backend.torch = NS(cuda=cuda, float16=torch.float16, isfinite=torch.isfinite,
                           inference_mode=torch.inference_mode)
        if defect == "prefix":
            native = backend.model.generate
            def corrupt(*args, **kwargs):
                result = native(*args, **kwargs)
                result.sequences[0, 0] = 123
                return result
            backend.model.generate = corrupt
        return backend

    def cpu_transfer(self):
        native = self.torch.Tensor.to
        def transfer(tensor, *args, **kwargs):
            if kwargs.get("device") == "cuda:0":
                self.assertIn(kwargs["dtype"], (self.torch.float16, self.torch.int64))
                kwargs["device"] = "cpu"
            return native(tensor, *args, **kwargs)
        return patch.object(self.torch.Tensor, "to", transfer)

    def run_case(self, root, text='{"safety_level":"Level04"}', defect=None, n=1):
        from test_pilot import plan, grant
        p, g = plan(), grant("phi")
        backend = self.backend(text, defect)
        image_path = root / "synthetic.jpg"
        # PNG bytes with a .jpg suffix; RGBA conversion follows production path.
        with self.Image.new("RGBA", (64, 80), color=(10, 20, 30, 128)) as image:
            image.save(image_path, format="PNG")
        rows = [{**r, "image": str(image_path), "image_sha256": sha(image_path)} for r in p["main"]]
        p["main"] = rows
        g.update(source_sha256=source_digest(ROOT), manifest_sha256=digest(p))
        write(root / "pilot_manifest.json", p)
        write(root / "grant.json", g)
        write_bytes(root / "tokenizer/runtime_tokenizer.json", backend.serialized_tokenizer)
        # Only run n images; remaining rows keep normal planned accounting.
        store = Store(root / "run", identity("phi", p, rows, g["source_sha256"], g["run_id"]))
        calls = 0
        native = backend.generate
        def bounded(*args):
            nonlocal calls
            if calls == n:
                raise TimeoutError("SYNTHETIC_BOUNDARY_STOP")
            calls += 1
            backend.model.calls = 0
            return native(*args)
        backend.generate = bounded
        with self.cpu_transfer():
            results, blocked = execute(store, rows, lambda: backend, g, "phi", p)
        image_path.unlink()  # synthetic image is not part of evidence ZIP
        failure = read(store.root / "failure.json") if (store.root / "failure.json").exists() else None
        save_reports(root / "report", p, {"phi": results}, blocked, {"phi": failure})
        return results, backend

    def test_production_first12_raw_hnlo_report_zip_and_independent_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "evidence"
            root.mkdir()
            results, backend = self.run_case(root, n=160)
            self.assertEqual(sum(r["status"] == "SUCCESS" for r in results.values()), 160)
            self.assertTrue(all(r["hnlo"]["status"] == "HNLO_VALIDATED" for r in results.values()))
            self.assertTrue((root / "run/early12.json").is_file())
            raw = read(root / "run/samples/000000/raw.json")
            self.assertEqual(replay(raw, parse_label(raw["response"]))["status"], "HNLO_VALIDATED")
            self.assertEqual(read(root / "run/samples/000000/request.json")["image"]["decoded_format"], "PNG")
            self.assertEqual(raw["actual_logits_processors"], [])
            self.assertFalse(backend.model._forward_hooks)
            archive = Path(directory) / "synthetic.zip"
            export(root, archive)
            imported = import_archive(archive, Path(directory) / "imported")
            self.assertEqual(read(imported / "report/phi.json")["primary"]["SUCCESS"], 160)
            from scripts.report_three_vlm_pilot import combine_archives
            # Replay the actual saved native/request/step/tokenizer provenance.
            output = ROOT / "data/processed" / ("phi-native-replay-" + root.parent.name)
            with patch("scripts.report_three_vlm_pilot.processed", return_value=output):
                reports = combine_archives({"phi": archive}, output)
            self.assertEqual(reports["phi"]["primary"]["hnlo"]["validated_n"], 160)
            shutil.rmtree(output)
            self.evidence["synthetic_pipeline"] = {
                "planned": 160, "scripted_calls": 160, "raw_records": 160,
                "hnlo_replay_validated": 160, "first12": "PASS", "native_generate": "TRANSFORMERS_4.43.3",
                "image_decode": "SYNTHETIC_RGBA_PNG_WITH_JPG_SUFFIX", "zip_sha256": sha(archive),
                "archive_import_and_report_cli_replay": "PASS", "research_result": False}
            retain = os.environ.get("SAFESHIFT_PHI_REHEARSAL_ARTIFACTS")
            if retain:
                destination = Path(retain)
                destination.mkdir(parents=True, exist_ok=False)
                shutil.copyfile(archive, destination / "synthetic.zip")
                shutil.copyfile(Path(str(archive) + ".sha256.json"), destination / "synthetic.zip.sha256.json")

    def test_generation_failures_stop_raw_and_tail_accounting(self):
        for defect in ("oom", "prefix", "nonfinite"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                results, backend = self.run_case(root, defect=defect)
                self.assertEqual(sum(r["status"] == "NOT_ATTEMPTED" for r in results.values()), 159)
                self.assertFalse(backend.model._forward_hooks)
                sample = root / "run/samples/000000"
                self.assertTrue((sample / "native_call.json").is_file())
                if defect == "prefix":
                    self.assertFalse(read(sample / "native.json")["input_prefix_match"])
                if defect == "oom":
                    self.assertEqual(read(root / "run/failure.json")["category"], "OOM")

    def test_invalid_and_hnlo_failure_do_not_rescue_or_change_label(self):
        with tempfile.TemporaryDirectory() as directory:
            results, _ = self.run_case(Path(directory), text="not json")
            self.assertEqual(next(iter(results.values()))["status"], "INVALID")

    def test_first12_failure_and_capture_io_keep_native_custody(self):
        for defect in ("early12", "capture_io", "decode"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                if defect == "early12":
                    results, _ = self.run_case(root, n=12)
                    self.assertEqual(sum(r["status"] == "SUCCESS" for r in results.values()), 12)
                    self.assertEqual(sum(r["status"] == "NOT_ATTEMPTED" for r in results.values()), 147)
                    self.assertTrue((root / "run/early12.json").exists())
                else:
                    import safeshift.pilot.backend as module
                    if defect == "capture_io":
                        native_write = module.write
                        def full(path, value):
                            if Path(path).parent.name == "steps":
                                raise OSError("SYNTHETIC_ENOSPC")
                            return native_write(path, value)
                        context = patch.object(module, "write", full)
                    else:
                        native_decode = self.processor.tokenizer.decode
                        def fail_decode(ids, *args, **kwargs):
                            # Probe uses skip_special_tokens=False; fail only
                            # the native response decode after native.json.
                            if kwargs.get("skip_special_tokens"):
                                raise ValueError("SYNTHETIC_RESPONSE_DECODE_ERROR")
                            return native_decode(ids, *args, **kwargs)
                        context = patch.object(self.processor.tokenizer, "decode", fail_decode)
                    with context:
                        results, _ = self.run_case(root)
                    self.assertEqual(next(iter(results.values()))["status"], "TECHNICAL_ERROR")
                    self.assertEqual(sum(r["status"] == "NOT_ATTEMPTED" for r in results.values()), 159)
                    if defect == "decode":
                        self.assertTrue((root / "run/samples/000000/native.json").exists())


if __name__ == "__main__":
    unittest.main()
