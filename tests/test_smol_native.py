"""Opt-in SmolVLM2 4.51.3 CPU integration; scripted logits are NOT research predictions.

SAFESHIFT_SMOL_SNAPSHOT points to the reviewed PUBLIC text/tokenizer files only.
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
from safeshift.pilot.backend import NativeBackend, check_software, native_generation_config
from safeshift.pilot.contract import GENERATION, MODELS, digest, parse_label, settings, source_digest
from safeshift.pilot.hnlo import replay
from safeshift.pilot.smol import (load_processor, prepare_inputs, validate_inputs, load_model,
                                   verify_attention, cpu_probe, checkpoint_metadata, meta_loader_context)
from safeshift.pilot.report import save_reports
from safeshift.pilot.runner import execute, identity
from safeshift.pilot.output_diagnostics import summarize

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = os.environ.get("SAFESHIFT_SMOL_SNAPSHOT")


@unittest.skipUnless(SNAPSHOT, "opt-in hash-locked Smol public source/tokenizer snapshot required")
class NativeSmolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch, transformers
        from PIL import Image
        cls.torch, cls.transformers, cls.Image = torch, transformers, Image
        torch.set_num_threads(2)
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        cls.tmp = Path(cls.stack.enter_context(tempfile.TemporaryDirectory()))
        cls.snapshot = cls.tmp / MODELS["smolvlm2"]["revision"]
        cls.snapshot.mkdir()
        from safeshift.pilot.backend import check_source_review
        locked = check_source_review(ROOT, "smolvlm2")
        for name, checksum in locked["files"].items():
            if sha(Path(SNAPSHOT) / name) != checksum:
                raise ValueError("REHEARSAL_SOURCE_HASH:" + name)
            shutil.copyfile(Path(SNAPSHOT) / name, cls.snapshot / name)
        index_lock = read(ROOT / "configs/pilot/smol_checkpoint_metadata.json")["index"]
        self_index = Path(SNAPSHOT) / index_lock["filename"]
        if sha(self_index) != index_lock["sha256"]:
            raise ValueError("REHEARSAL_INDEX_HASH")
        shutil.copyfile(self_index, cls.snapshot / index_lock["filename"])
        cls.evidence = {"versions": check_software(ROOT, "smolvlm2"), "synthetic_only": True}
        for name in ("init", "_lazy_init", "is_available", "device_count", "get_device_capability",
                     "synchronize", "memory_allocated", "memory_reserved", "max_memory_allocated",
                     "max_memory_reserved", "reset_peak_memory_stats"):
            cls.stack.enter_context(patch.object(torch.cuda, name, side_effect=AssertionError("REAL_CUDA_FORBIDDEN")))
        cls.stack.enter_context(patch.object(torch.nn.functional, "scaled_dot_product_attention",
                                            side_effect=AssertionError("SDPA_FORBIDDEN")))
        cls.stack.enter_context(patch.object(torch, "load", side_effect=AssertionError("PICKLE_WEIGHTS_FORBIDDEN")))
        cls.stack.enter_context(patch.object(transformers.SmolVLMForConditionalGeneration, "forward",
                                            side_effect=AssertionError("REAL_MODEL_FORWARD_FORBIDDEN")))
        transformers.utils.logging.set_verbosity_error()
        cls.processor = load_processor(ROOT, cls.snapshot)
        cls.prompt = (ROOT / "configs/pilot/classification_c1.txt").read_bytes().decode()

    def test_real_loader_original_checkpoint_and_nested_attention(self):
        torch, transformers = self.torch, self.transformers
        model_class = transformers.SmolVLMForConditionalGeneration
        # Check official Auto mapping, no switch of class/revision.
        from transformers.models.auto.modeling_auto import MODEL_FOR_IMAGE_TEXT_TO_TEXT_MAPPING
        self.assertIs(MODEL_FOR_IMAGE_TEXT_TO_TEXT_MAPPING[transformers.SmolVLMConfig], model_class)
        with patch.object(model_class, "forward", side_effect=AssertionError("ACTUAL_FORWARD_FORBIDDEN")):
            model, receipt = load_model(ROOT, self.snapshot, meta=True)
        self.assertEqual((receipt["text_layers"], receipt["vision_layers"]), (24, 27))
        self.assertEqual(sum(p.numel() for p in model.parameters()), 2246784880)
        self.assertEqual(model.generation_config.eos_token_id, self.processor.tokenizer.eos_token_id)
        self.evidence["real_loader"] = receipt
        self.evidence["parameter_count"] = 2246784880
        from safetensors.torch import save_file
        save_file({}, str(self.snapshot / "model.safetensors"), metadata={"format": "pt"})
        # Exact BASE native class/file-deserialization path, replacing ONLY the
        # checkpoint with an empty safetensors fixture and omitting CUDA dispatch.
        with meta_loader_context():
            path_model = model_class.from_pretrained(str(self.snapshot), local_files_only=True,
                trust_remote_code=False, revision=MODELS["smolvlm2"]["revision"],
                torch_dtype=torch.float16, attn_implementation="eager", use_safetensors=True)
        self.evidence["original_path_empty_safetensors"] = verify_attention(path_model)
        self.assertTrue(all(t.device.type == "meta" for t in (*path_model.parameters(), *path_model.buffers())))
        original = read(self.snapshot / "config.json")
        self.assertTrue(original["text_config"]["_flash_attn_2_enabled"])
        for cfg in (model.config, model.model.text_model.config, model.model.vision_model.config):
            for value in (None, "sdpa", "flash_attention_2"):
                cfg._attn_implementation = value
                with self.assertRaises(ValueError):
                    verify_attention(model)
            cfg._attn_implementation = "eager"
        for obj in (model.model, model.model.vision_model):
            obj._use_flash_attention_2 = True
            with self.assertRaises(ValueError):
                verify_attention(model)
            obj._use_flash_attention_2 = False
        # Reproduce native loader's implicit SDPA path (Phi a5 analogue), then
        # confirm our strict check rejects it; no constructor/loader substitute.
        config = transformers.SmolVLMConfig.from_pretrained(self.snapshot, local_files_only=True)
        with meta_loader_context():
            implicit = model_class.from_pretrained(None, config=config, state_dict={}, torch_dtype=torch.float16)
        with self.assertRaises(ValueError):
            verify_attention(implicit)
        self.evidence["implicit_sdpa_rejected"] = True
        # Phi a4 analogue: serialized FA request cannot require flash-attn in
        # our eager path. Reproduce the pre-constructor native failure itself.
        config._attn_implementation = "flash_attention_2"
        with patch("transformers.modeling_utils.is_flash_attn_2_available", return_value=False), \
                meta_loader_context(), self.assertRaisesRegex(ImportError, "FlashAttention|flash_attn"):
            model_class.from_pretrained(None, config=config, state_dict={}, torch_dtype=torch.float16)
        self.evidence["implicit_flash_import_error_reproduced"] = True

    def test_native_processor_shapes_tokens_prompt_and_corruption(self):
        cases = []
        for size in ((1, 1), (384, 384), (640, 480), (2048, 1536), (200, 1200), (1200, 200)):
            with self.subTest(size=size), self.Image.new("RGB", size) as image:
                rendered, inputs = prepare_inputs(self.processor, self.prompt, image)
                cases.append({"size": list(size), **validate_inputs(self.processor, rendered, inputs)})
                from safeshift.pilot.hnlo import probe, candidate_ids
                mapping = probe(self.processor.tokenizer, rendered, inputs["input_ids"][0].tolist())
                self.assertTrue(mapping["boundary_ok"])
                self.assertEqual(candidate_ids(mapping), [33, 34, 35, 36])
        self.evidence["processor_cases"] = cases
        for field in ("input_ids", "attention_mask", "pixel_values", "pixel_attention_mask"):
            with self.subTest(field=field), self.Image.new("RGB", (64, 80)) as image:
                rendered, inputs = prepare_inputs(self.processor, self.prompt, image)
                inputs[field] = inputs[field].float() if field != "pixel_values" else inputs[field].half()
                with self.assertRaises(ValueError):
                    validate_inputs(self.processor, rendered, inputs)
        with self.Image.new("RGB", (64, 80)) as image:
            with self.assertRaisesRegex(ValueError, "PROMPT_CHECKSUM"):
                prepare_inputs(self.processor, self.prompt + " changed", image)
            rendered, inputs = prepare_inputs(self.processor, self.prompt, image)
            inputs["input_ids"][0, 0] = 0
            with self.assertRaisesRegex(ValueError, "TOKEN_PREFIX"):
                validate_inputs(self.processor, rendered, inputs)
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
        class ScriptedModel(transformers.PreTrainedModel, transformers.GenerationMixin):
            config_class = transformers.PretrainedConfig
            def __init__(inner):
                super().__init__(transformers.PretrainedConfig(is_decoder=True, vocab_size=len(tokenizer),
                                 max_position_embeddings=131072))
                inner.config.text_config = transformers.PretrainedConfig(max_position_embeddings=8192)
                inner.anchor = torch.nn.Parameter(torch.zeros(1), requires_grad=False)
                inner.calls = 0
            def prepare_inputs_for_generation(inner, input_ids, **kwargs):
                return {"input_ids": input_ids, **kwargs}
            def forward(inner, input_ids, attention_mask=None, pixel_values=None, image_sizes=None,
                        pixel_attention_mask=None, past_key_values=None, use_cache=None, return_dict=None, output_attentions=None,
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
        backend.key, backend.prompt, backend.processor, backend.tokenizer = "smolvlm2", self.prompt, self.processor, tokenizer
        backend.model = ScriptedModel().eval()
        backend.environment = {"SYNTHETIC_CPU_TEST_NOT_RESEARCH": True, "model_boundary": "SCRIPTED_LOGITS"}
        backend.serialized_tokenizer = tokenizer.backend_tokenizer.to_str().encode()
        from tokenizers import Tokenizer
        backend.cpu_tokenizer = Tokenizer.from_str(backend.serialized_tokenizer.decode())
        backend.model.generation_config = transformers.GenerationConfig.from_pretrained(self.snapshot, local_files_only=True)
        backend.generation = native_generation_config(backend.model)
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
        p, g = plan(), grant("smolvlm2")
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
        store = Store(root / "run", identity("smolvlm2", p, rows, g["source_sha256"], g["run_id"]))
        calls = 0
        native = backend.generate
        def bounded(*args):
            nonlocal calls
            if calls == n:
                raise TimeoutError("SYNTHETIC_BOUNDARY_STOP")
            calls += 1
            backend.model.calls = 0
            value = native(*args)
            value["evidence_kind"] = "SYNTHETIC_SCRIPTED_LOGITS_NOT_MODEL_PREDICTIONS"
            return value
        backend.generate = bounded
        with self.cpu_transfer():
            results, blocked = execute(store, rows, lambda: backend, g, "smolvlm2", p)
        image_path.unlink()  # synthetic image is not part of evidence ZIP
        failure = read(store.root / "failure.json") if (store.root / "failure.json").exists() else None
        save_reports(root / "report", p, {"smolvlm2": results}, blocked, {"smolvlm2": failure},
                     {"smolvlm2": backend.environment})
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
            self.assertEqual(read(Path(str(archive) + ".sha256.json"))["sha256"], sha(archive))
            imported = import_archive(archive, Path(directory) / "imported")
            self.assertEqual(read(imported / "report/smolvlm2.json")["primary"]["SUCCESS"], 160)
            from scripts.report_three_vlm_pilot import combine_archives
            # Replay the actual saved native/request/step/tokenizer provenance.
            output = ROOT / "data/processed" / ("smol-native-replay-" + root.parent.name)
            with patch("scripts.report_three_vlm_pilot.processed", return_value=output):
                reports = combine_archives({"smolvlm2": archive}, output)
            self.assertEqual(reports["smolvlm2"]["primary"]["hnlo"]["validated_n"], 160)
            shutil.rmtree(output)
            self.evidence["synthetic_pipeline"] = {
                "planned": 160, "scripted_calls": 160, "raw_records": 160,
                "hnlo_replay_validated": 160, "first12": "PASS", "native_generate": "TRANSFORMERS_4.51.3",
                "image_decode": "SYNTHETIC_RGBA_PNG_WITH_JPG_SUFFIX", "zip_sha256": sha(archive),
                "archive_import_and_report_cli_replay": "PASS", "research_result": False}
            retain = os.environ.get("SAFESHIFT_SMOL_REHEARSAL_ARTIFACTS")
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
        # Phi a6 analogue: label-looking prefix followed by unrelated prose,
        # reaches native max64 without EOS. Preserve every generated token;
        # neither strict parsing nor HNLO may rescue the leading Level04.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results, _ = self.run_case(root, text="Level04" + " unrelated prose" * 100)
            raw = read(root / "run/samples/000000/raw.json")
            self.assertEqual(len(raw["generated_ids"]), 64)
            self.assertNotIn(raw["generated_ids"][-1], raw["eos_token_ids"])
            first = next(iter(results.values()))
            self.assertEqual(first["status"], "INVALID")
            self.assertNotEqual(first["hnlo"]["status"], "HNLO_VALIDATED")
            self.assertEqual(summarize(root / "run")["at_max64_n"], 1)
            self.evidence["a6_max64_synthetic"] = {"calls": 1, "generated_tokens": 64,
                "eos_reached": False, "strict_label": None, "hnlo_validated": False,
                "scripted_logits_not_prediction": True}

    def test_a6_invalid_repetition_160_is_diagnostic_and_first12_stays_technical(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "evidence"
            root.mkdir()
            results, _ = self.run_case(root, text="Level04", n=160)
            self.assertEqual(sum(r["status"] == "INVALID" for r in results.values()), 160)
            self.assertFalse(any(r["hnlo"]["status"] == "HNLO_VALIDATED" for r in results.values()))
            self.assertEqual(read(root / "run/early12.json")["technical_gate"], "PASS")
            diagnostic = summarize(root / "run")
            self.assertEqual((diagnostic["strict_json_invalid"], diagnostic["largest_identical_token_sequence_n"]), (160, 160))
            self.assertEqual(diagnostic["explicit_synthetic_raw_records"], 160)
            self.assertEqual(read(root / "report/smolvlm2.json")["conclusion"]["classification_status"], "TECHNICAL_FAIL")
            write(root / "output_diagnostics.json", diagnostic)
            archive = Path(directory) / "invalid-synthetic.zip"
            export(root, archive)
            import_archive(archive, Path(directory) / "recovered")
            self.evidence["a6_invalid_synthetic"] = {"calls": 160, "valid_json": 0,
                "hnlo_validated": 0, "first12_technical_gate": "PASS_UNCHANGED_NOT_QUALITY_ACCEPTANCE",
                "diagnostic": diagnostic, "zip_sha256": sha(archive), "research_result": False}
            retain = os.environ.get("SAFESHIFT_SMOL_REHEARSAL_ARTIFACTS")
            if retain:
                target = Path(retain).with_name("invalid-artifacts")
                target.mkdir(parents=True, exist_ok=False)
                shutil.copyfile(archive, target / "synthetic.zip")
                shutil.copyfile(Path(str(archive) + ".sha256.json"), target / "synthetic.zip.sha256.json")

    def test_independent_tokenizer_mismatch_and_raw_before_parser(self):
        native_backend = self.backend
        def mismatched(*args, **kwargs):
            backend = native_backend(*args, **kwargs)
            backend.cpu_tokenizer = NS(decode=lambda *a, **k: "MISMATCH")
            return backend
        with tempfile.TemporaryDirectory() as directory, patch.object(self, "backend", mismatched):
            results, _ = self.run_case(Path(directory))
            first = next(iter(results.values()))
            self.assertEqual(first["status"], "SUCCESS")
            self.assertEqual(first["hnlo"]["status"], "RAW_LOGITS_AVAILABLE_BUT_UNALIGNED")
            self.assertEqual(first["hnlo"]["reason"], "INDEPENDENT_CPU_TOKENIZER_REPLAY_REQUIRED")
        import safeshift.pilot.runner as runner
        native_parse = runner.parse_label
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def check_custody(text):
                self.assertTrue((root / "run/samples/000000/raw.json").is_file())
                return native_parse(text)
            with patch.object(runner, "parse_label", check_custody):
                self.run_case(root)

    def test_all_four_labels_and_three_surfaces_use_actual_native_branch(self):
        from safeshift.pilot.hnlo import SURFACES
        from safeshift.pilot.contract import LEVELS
        for surface in SURFACES:
            for label in LEVELS:
                with self.subTest(surface=surface, label=label), tempfile.TemporaryDirectory() as directory:
                    values, _ = self.run_case(Path(directory), text=surface % label)
                    first = next(iter(values.values()))
                    self.assertEqual(first["label"], label)
                    self.assertEqual(first["hnlo"]["status"], "HNLO_VALIDATED")

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
