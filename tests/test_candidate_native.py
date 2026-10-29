"""Opt-in CPU tests: real processors/meta loaders, SCRIPTED logits, no inference."""
import copy
import errno
import os
from contextlib import ExitStack
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS, MethodType
import unittest
from unittest.mock import patch

from safeshift.pilot.artifacts import Store, read, sha, write, export, import_archive
from safeshift.pilot.contract import GENERATION, PROMPT_SHA, parse_label
from safeshift.candidates.source import ROOT, LOCK, stage_snapshot
from safeshift.candidates.loading import native_setup, load_meta_model, verify_attention, checkpoint_index
from safeshift.candidates.inputs import prepare_inputs, validate_inputs
from safeshift.candidates.backend import CandidateBackend, persist_ids, transfer_inputs
from scripts import rehearse_candidate_cpu as old

KEY = os.environ.get("SAFESHIFT_CANDIDATE_KEY")
SNAPSHOT = os.environ.get("SAFESHIFT_CANDIDATE_SNAPSHOT")


@unittest.skipUnless(KEY and SNAPSHOT, "opt-in isolated candidate CPU stack/public snapshot required")
class NativeCandidateTests(unittest.TestCase):
    evidence = {}

    @classmethod
    def setUpClass(cls):
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        cls.tmp = Path(cls.stack.enter_context(tempfile.TemporaryDirectory()))
        os.environ["HF_MODULES_CACHE"] = str(cls.tmp / "modules")
        cls.spec = read(LOCK)[KEY]
        cls.snapshot = cls.tmp / cls.spec["revision"]
        stage_snapshot(Path(SNAPSHOT), cls.snapshot, KEY)
        cls.evidence = {"environment": old.environment(KEY)}
        import torch, transformers
        from PIL import Image
        cls.torch, cls.transformers, cls.Image = torch, transformers, Image
        transformers.utils.logging.set_verbosity_error()
        old.guard(cls.stack, allow_empty_state_loader=True)
        cls.processor, cls.tokenizer, cls.config, cls.model_class = native_setup(cls.snapshot, KEY, cls.evidence)
        # Exact real classes are forbidden to forward. Only ScriptedModel below
        # can supply synthetic next-token logits to native GenerationMixin.
        cls.stack.enter_context(patch.object(cls.model_class, "forward", side_effect=AssertionError("INFERENCE_FORBIDDEN")))
        for name in ("LlamaForCausalLM", "Qwen3ForCausalLM"):
            model_class = getattr(transformers, name, None)
            if model_class:
                cls.stack.enter_context(patch.object(model_class, "forward", side_effect=AssertionError("INFERENCE_FORBIDDEN")))
        cls.prompt = (ROOT / "configs/pilot/classification_c1.txt").read_bytes().decode()

    def test_meta_loader_inventory_and_attention_faults(self):
        model, receipt = load_meta_model(self.snapshot, KEY, copy.deepcopy(self.config), self.model_class)
        index = checkpoint_index(Path(os.environ["SAFESHIFT_CANDIDATE_INDEX"]), KEY)
        keys = set(index["weight_map"])
        if KEY == "internvl35":
            mapping = model._get_key_renaming_mapping(list(keys), key_mapping=model._checkpoint_conversion_mapping)
            self.assertEqual(len(set(mapping.values())), len(keys))
            keys = set(mapping.values())
            receipt["native_checkpoint_key_conversion"] = model._checkpoint_conversion_mapping
        self.assertEqual(set(model.state_dict()), keys)
        self.evidence["meta_loader"] = {**receipt, "checkpoint_tensor_inventory": len(index["weight_map"])}
        for value in ("sdpa", "flash_attention_2", None):
            cfg = model.model.language_model.config if KEY == "internvl35" else model.llm.config
            cfg._attn_implementation = value
            with self.assertRaises(ValueError):
                verify_attention(model, KEY)
            cfg._attn_implementation = "eager"
        verify_attention(model, KEY)

    def test_native_empty_safetensors_path_loader_and_failure(self):
        """Native file loader/config plumbing, NOT real checkpoint deserialization."""
        from safetensors.torch import save_file
        from safeshift.candidates.loading import meta_context, explicit_eager
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"model.safetensors"
            save_file({}, str(path), metadata={"format": "pt"})
            config = copy.deepcopy(self.config)
            explicit_eager(config)
            with meta_context():
                model = self.model_class.from_pretrained(d, config=config, local_files_only=True,
                    torch_dtype=self.torch.float16, attn_implementation="eager", use_safetensors=True).eval()
            verify_attention(model, KEY)
            self.assertTrue(all(p.device.type == "meta" for p in model.parameters()))
            path.write_bytes(b"NOT_A_SAFETENSORS_HEADER")
            with meta_context(), self.assertRaises(Exception) as failure:
                self.model_class.from_pretrained(d, config=config, local_files_only=True,
                    torch_dtype=self.torch.float16, attn_implementation="eager", use_safetensors=True)
            self.assertNotIsInstance(failure.exception, AssertionError)
            self.evidence["native_empty_file_loader"] = {"valid_empty_file": "PASS",
                "corrupt_file_rejected": type(failure.exception).__name__, "real_weights": "NOT_TESTED"}

    def test_real_native_embedding_glue_with_scripted_towers(self):
        torch = self.torch
        cases = []
        for size in ((1, 1), (640, 480), (2048, 1536)):
            with self.Image.new("RGB", size) as image:
                rendered, inputs = prepare_inputs(self.processor, KEY, self.prompt, image)
            if KEY == "internvl35":
                from transformers.models.internvl.modeling_internvl import InternVLModel
                owner = NS(config=self.config)
                # Native CLS removal, pixel shuffle, reshape and placeholder check;
                # vision/projector predictions are explicitly synthetic tensors.
                owner.vision_tower = lambda pixel_values: NS(last_hidden_state=torch.ones(pixel_values.shape[0], 1025, 4))
                owner.pixel_shuffle = MethodType(InternVLModel.pixel_shuffle, owner)
                owner.multi_modal_projector = lambda features: torch.full((*features.shape[:2], 8), 5.0)
                features = InternVLModel.get_image_features(owner, inputs["pixel_values"])
                embeddings = torch.zeros(1, inputs["input_ids"].shape[1], 8)
                mask = InternVLModel.get_placeholder_mask(owner, inputs["input_ids"], embeddings, features)
                merged = embeddings.masked_scatter(mask, features)
                with self.assertRaises(ValueError):
                    InternVLModel.get_placeholder_mask(owner, inputs["input_ids"], embeddings, features[:, :-1])
                self.assertTrue(torch.all(merged[mask] == 5))
                self.assertTrue(torch.all(merged[~mask] == 0))
                cases.append({"size": size, "features": list(features.shape)})
            else:
                class Embedding:
                    weight = torch.zeros(1, 8)
                    def __call__(self, ids): return torch.zeros(*ids.shape, 8)
                calls = []
                def vision(pixels, patch_attention_mask, tgt_sizes):
                    self.assertEqual(pixels.shape[1:3], (3, 14))
                    self.assertEqual(patch_attention_mask.dtype, torch.bool)
                    for i, grid in enumerate(tgt_sizes):
                        self.assertEqual(int(patch_attention_mask[i].sum()), int(grid.prod()))
                    calls.append(pixels.shape[0])
                    return NS(last_hidden_state=torch.zeros(pixels.shape[0], 1, 4))
                owner = NS(config=NS(vision_batch_size=2), training=False,
                    llm=NS(model=NS(embed_tokens=Embedding()), config=NS()), vpm=vision,
                    resampler=lambda states, sizes: torch.full((states.shape[0], 64, 8), 5.0))
                merged, _ = self.model_class.get_vllm_embedding(owner, inputs)
                mask = torch.zeros_like(merged, dtype=torch.bool)
                for start, end in inputs["image_bound"][0]: mask[0, start:end] = True
                self.assertTrue(torch.all(merged[mask] == 5))
                self.assertTrue(torch.all(merged[~mask] == 0))
                self.assertEqual(sum(calls), len(inputs["pixel_values"][0]))
                bad = copy.deepcopy(inputs)
                bad["image_bound"][0][0, 1] -= 1
                # Native scatter accepts too few indices and can silently leave
                # an image placeholder unfilled. Our pre-boundary guard must stop it.
                with self.assertRaisesRegex(ValueError, "SLICE_64_QUERY_TOKENS"):
                    validate_inputs(self.processor, KEY, self.config, rendered, bad, self.prompt)
                if len(bad["image_bound"][0]) == 1:
                    malformed, _ = self.model_class.get_vllm_embedding(owner, bad)
                    self.assertFalse(torch.equal(merged, malformed))
                else:
                    with self.assertRaisesRegex(RuntimeError, "stack expects"):
                        self.model_class.get_vllm_embedding(owner, bad)
                cases.append({"size": size, "vision_batch_calls": calls, "merged_shape": list(merged.shape)})
        self.evidence["native_embedding_glue_scripted_towers"] = cases

    def spatial_image(self, size):
        import numpy as np
        w, h = size
        y, x = np.indices((h, w))
        return self.Image.fromarray(np.stack(((3*x+y)%256, (7*y+x)%256, (x+11*y)%256), axis=-1).astype("uint8"))

    def equal_tree(self, a, b):
        if isinstance(a, self.torch.Tensor):
            self.assertEqual(a.dtype, b.dtype)
            self.assertTrue(self.torch.equal(a, b))
        elif isinstance(a, dict) or hasattr(a, "keys"):
            self.assertEqual(set(a), set(b))
            for key in a:
                self.equal_tree(a[key], b[key])
        elif isinstance(a, (list, tuple)):
            self.assertEqual(len(a), len(b))
            for x, y in zip(a, b):
                self.equal_tree(x, y)
        else:
            self.assertEqual(a, b)

    def test_sizes_spatial_native_parity_and_rgb_normalization(self):
        cases = []
        for size in (*old.CASES, (1, 17), (17, 1), (3, 19), (19, 3), (14, 14), (449, 447)):
            with self.subTest(size=size), self.spatial_image(size) as image:
                rendered, inputs = prepare_inputs(self.processor, KEY, self.prompt, image)
                detail = validate_inputs(self.processor, KEY, self.config, rendered, inputs, self.prompt)
                if KEY == "internvl35" or size[1] not in (1, 3):
                    native_text, native = old.prepare(self.processor, KEY, self.prompt, image)
                    self.assertEqual(rendered, native_text)
                    self.equal_tree(inputs, native)
                    detail["native_spatial_tensor_parity"] = "EXACT"
                else:
                    with self.assertRaises(ValueError):
                        old.prepare(self.processor, KEY, self.prompt, image)
                    detail["unmodified_native_ambiguous_axis"] = "ERROR_REPRODUCED"
                cases.append({"size": list(size), **detail})
        for size in ((1, 1), (19, 3), (448, 448)):
            with self.Image.new("RGB", size, (40, 80, 120)) as image:
                _, inputs = prepare_inputs(self.processor, KEY, self.prompt, image)
                mean, std = (([.485, .456, .406], [.229, .224, .225]) if KEY == "internvl35" else ([.5]*3, [.5]*3))
                expected = (self.torch.tensor([40, 80, 120])/255 - self.torch.tensor(mean))/self.torch.tensor(std)
                pixels = inputs["pixel_values"] if KEY == "internvl35" else inputs["pixel_values"][0]
                for tensor in pixels:
                    self.assertTrue(self.torch.allclose(tensor.flatten(1).mean(1), expected, atol=1e-5))
        self.evidence["processor_cases"] = cases

    def test_input_faults_and_dtype_transfer(self):
        with self.Image.new("RGB", (64, 80)) as image:
            rendered, original = prepare_inputs(self.processor, KEY, self.prompt, image)
            for fault in ("ids", "mask", "pixels", "image_token", "context"):
                inputs, config = copy.deepcopy(original), copy.deepcopy(self.config)
                if fault == "ids": inputs["input_ids"] = inputs["input_ids"].float()
                if fault == "mask": inputs["attention_mask"][0, 0] = 0
                if fault == "pixels":
                    if KEY == "internvl35": inputs["pixel_values"] = inputs["pixel_values"].half()
                    else: inputs["pixel_values"][0][0] = inputs["pixel_values"][0][0].half()
                if fault == "image_token":
                    if KEY == "internvl35": inputs["input_ids"][inputs["input_ids"] == config.image_token_id] = 0
                    else: inputs["image_bound"][0][0, 0] = -1
                if fault == "context":
                    (config.text_config if KEY == "internvl35" else config).max_position_embeddings = 1
                with self.subTest(fault=fault), self.assertRaises(ValueError):
                    validate_inputs(self.processor, KEY, config, rendered, inputs, self.prompt)
            moved = transfer_inputs(original, "cpu", self.torch.float16)
            self.assertEqual(moved["input_ids"].dtype, original["input_ids"].dtype)
            self.assertEqual(moved["attention_mask"].dtype, original["attention_mask"].dtype)
            if KEY == "minicpm4":
                self.assertNotIn("image_sizes", moved)
                self.assertEqual(moved["image_bound"][0].dtype, original["image_bound"][0].dtype)
            with self.assertRaisesRegex(ValueError, "FROZEN_C1"):
                prepare_inputs(self.processor, KEY, self.prompt + " ", image)
        with self.Image.new("RGBA", (2, 2)) as image, self.assertRaises(ValueError):
            prepare_inputs(self.processor, KEY, self.prompt, image)

    def backend(self, text='{"safety_level":"Level04"}', *, eos=None, defect=None):
        torch, tr, tokenizer = self.torch, self.transformers, self.tokenizer
        tokens = tokenizer.encode(text, add_special_tokens=False)
        tokens += [tokenizer.eos_token_id if eos is None else eos]
        class ScriptedModel(tr.PreTrainedModel, tr.GenerationMixin):
            config_class = tr.PretrainedConfig
            def __init__(inner):
                super().__init__(tr.PretrainedConfig(is_decoder=True, vocab_size=len(tokenizer), max_position_embeddings=131072))
                inner.anchor = torch.nn.Parameter(torch.zeros(1), requires_grad=False)
                inner.calls = 0
            def prepare_inputs_for_generation(inner, input_ids, inputs_embeds=None, **kwargs):
                return {"input_ids": input_ids, "inputs_embeds": inputs_embeds, **kwargs}
            def forward(inner, input_ids=None, inputs_embeds=None, attention_mask=None, pixel_values=None,
                        past_key_values=None, use_cache=None, return_dict=None, output_attentions=None,
                        output_hidden_states=None, cache_position=None):
                if defect == "oom": raise RuntimeError("SYNTHETIC out of memory")
                token = tokens[inner.calls % len(tokens)]
                inner.calls += 1
                logits = torch.zeros(1, 1, len(tokenizer), dtype=torch.float32)
                logits[0, 0, token] = 10
                if defect == "nonfinite": logits[0, 0, 0] = float("nan")
                return tr.modeling_outputs.CausalLMOutputWithPast(logits=logits)
        llm = ScriptedModel().eval()
        llm.generation_config = tr.GenerationConfig.from_pretrained(self.snapshot, local_files_only=True)
        if KEY == "minicpm4":
            model = NS(llm=llm, generation_config=llm.generation_config, terminators=['<|im_end|>', '</s>'])
            # Actual pinned outer generate/_decode. Only the expensive embedding
            # boundary and next-token forward are scripted; no native VLM forward.
            model.generate = MethodType(self.model_class.generate, model)
            model._decode = MethodType(self.model_class._decode, model)
            model.get_vllm_embedding = lambda data: (torch.zeros(1, data["input_ids"].shape[1], 4), [])
        else:
            model = llm
        backend = CandidateBackend.__new__(CandidateBackend)
        backend.key, backend.prompt, backend.device = KEY, self.prompt, "cpu"
        backend.processor, backend.tokenizer, backend.config = self.processor, tokenizer, self.config
        backend.model = model
        backend.configure()
        backend.environment = {"model": {k: self.spec[k] for k in ("id", "revision")}, "synthetic": True}
        return backend, llm

    def call(self, root, backend):
        image_path = root / "synthetic.jpg"
        with self.Image.new("RGBA", (17, 1), (40, 80, 120, 50)) as image:
            image.save(image_path, format="PNG")
        sample = root / "sample"
        raw = backend.generate(image_path, sample)
        return raw, sample

    def test_native_generation_contract_raw_ids_logits_eos_and_decode_order(self):
        if KEY == "minicpm4":
            old_trace = old.wrapper_probe(self.model_class, self.processor, self.config, KEY)
            self.assertEqual(old_trace["status"], "FAIL")
            self.evidence["unmodified_chat_contract_failure"] = old_trace
        eos_ids = [self.tokenizer.eos_token_id] if KEY == "internvl35" else [2, 73440]
        for eos in eos_ids:
            with self.subTest(eos=eos), tempfile.TemporaryDirectory() as d:
                backend, llm = self.backend(eos=eos)
                root = Path(d)
                native_decode = self.tokenizer.decode
                def decode(ids, **kwargs):
                    if ids and ids[-1] == eos and kwargs.get("skip_special_tokens"):
                        self.assertTrue((root / "sample/native.json").exists())
                    return native_decode(ids, **kwargs)
                with patch.object(self.tokenizer, "decode", decode):
                    raw, sample = self.call(root, backend)
                self.assertEqual(parse_label(raw["response"]), "Level04")
                self.assertEqual(raw["generated_ids"][-1], eos)
                self.assertEqual(len(raw["steps"]), len(raw["generated_ids"]))
                self.assertTrue(all(s["raw_candidate_logits"] for s in raw["steps"]))
                self.assertEqual(raw["actual_logits_processors"], [])
                self.assertFalse(llm._forward_hooks)
                self.assertEqual({k: getattr(backend.generation, k) for k in GENERATION}, GENERATION)
                self.assertEqual(backend.generation.repetition_penalty, 1.0)
                self.assertEqual(raw["cpu_tokenizer_replay"]["status"], "PASS")
                returned = read(sample / "native.json")["returned_ids"][0]
                self.assertEqual(returned, raw["input_ids"] + raw["generated_ids"] if KEY == "internvl35" else raw["generated_ids"])
                self.evidence.setdefault("scripted_generation", []).append({"eos": eos, "tokens": len(raw["generated_ids"]),
                    "steps": len(raw["steps"]), "generation": backend.generation.to_dict(), "inference": "NOT_RUN"})

    def test_invalid_repetition_and_max64_are_not_rescued(self):
        for text in ('{"safety_level":"Level01","safety_level":"Level04"}', 'Level04' + ' prose'*100):
            with self.subTest(text=text[:20]), tempfile.TemporaryDirectory() as d:
                backend, _ = self.backend(text)
                raw, _ = self.call(Path(d), backend)
                self.assertIsNone(parse_label(raw["response"]))
                if text.startswith("Level04"):
                    self.assertEqual(len(raw["generated_ids"]), 64)
                    self.assertNotIn(raw["generated_ids"][-1], raw["eos_token_ids"])

    def test_four_labels_whitespace_and_existing_fifteen_raw_cases(self):
        from safeshift.pilot.contract import LEVELS
        for label in LEVELS:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as d:
                text = ' \n{"safety_level":"' + label + '"}\n'
                backend, _ = self.backend(text)
                raw, _ = self.call(Path(d), backend)
                self.assertEqual(raw["response"], text)
                self.assertEqual(parse_label(raw["response"]), label)
        with tempfile.TemporaryDirectory() as d:
            result = old.scripted_outputs(self.tokenizer, Path(d))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(len(result["cases"]), 15)
            self.evidence["existing_fifteen_raw_cases"] = result

    def test_write_failure_stops_before_decode_and_removes_hook(self):
        import safeshift.candidates.backend as adapter
        for filename in ("request.json", "native_call.json", "processors.json", "steps/000.json", "native.json"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as d:
                backend, llm = self.backend()
                real = adapter.write
                def fail(path, value):
                    if Path(path).as_posix().endswith(filename): raise OSError(errno.ENOSPC, "SYNTHETIC disk full")
                    return real(path, value)
                with patch.object(adapter, "write", fail), self.assertRaises(OSError):
                    self.call(Path(d), backend)
                self.assertFalse(llm._forward_hooks)
                if filename in ("request.json", "native_call.json"):
                    self.assertEqual(llm.calls, 0)

    def test_decode_error_retains_exact_native_ids(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            backend, llm = self.backend()
            native_decode = self.tokenizer.decode
            def fail_after_native(ids, **kwargs):
                if (root/"sample/native.json").exists():
                    raise RuntimeError("SYNTHETIC decode failure")
                return native_decode(ids, **kwargs)
            with patch.object(self.tokenizer, "decode", fail_after_native), self.assertRaisesRegex(RuntimeError, "decode failure"):
                self.call(root, backend)
            native = read(root/"sample/native.json")
            self.assertTrue(native["generated_ids"])
            self.assertFalse(llm._forward_hooks)

    def test_weight_loader_failure_uses_exact_config_and_no_fallback(self):
        import safeshift.candidates.loading as loading
        config = copy.deepcopy(self.config)
        calls = []
        class FailingLoader:
            @staticmethod
            def from_pretrained(path, **kwargs):
                calls.append(kwargs)
                raise OSError("SYNTHETIC checkpoint failure")
        # Only weight admission is doubled. No real weights/GPU are touched.
        with patch.object(loading, "verify_weights", return_value={}), self.assertRaisesRegex(OSError, "checkpoint failure"):
            loading.load_weight_model(self.snapshot, KEY, config, FailingLoader, "synthetic-weight-dir", "cpu")
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0]["local_files_only"] and calls[0]["use_safetensors"])
        self.assertEqual(calls[0]["attn_implementation"], "eager")
        self.assertEqual(calls[0]["torch_dtype"], self.torch.float16)
        self.assertEqual(config.vision_config._attn_implementation, "eager")

    def test_malformed_sequences_persist_before_rejection(self):
        torch = self.torch
        inputs = {"input_ids": torch.tensor([[7, 8]])}
        for ids in (torch.tensor([]), torch.tensor([[1.5]]), torch.tensor([[1], [2]]), torch.tensor([[]], dtype=torch.int64)):
            with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
                persist_ids(NS(sequences=ids), inputs, KEY, Path(d)/"native.json")
                self.fail("accepted malformed native return")
            # Persistence itself is checked separately, while the temporary file exists.
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"native.json"
            with self.assertRaises(ValueError):
                persist_ids(NS(sequences=torch.tensor([[9, 10, 11]])), inputs, "internvl35", path)
            self.assertEqual(read(path)["returned_ids"], [[9, 10, 11]])

    def test_existing_runner_raw_before_parse_failure_tail_and_archive(self):
        import safeshift.pilot.runner as runner
        for defect in (None, "oom", "nonfinite", "load", "raw_write"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                image = root/"synthetic.png"
                self.Image.new("RGB", (1, 1)).save(image)
                rows = [{"sample_id": str(i), "image": str(image), "image_sha256": sha(image)} for i in range(2)]
                store = Store(root/"run", {"synthetic": True, "model": self.spec["id"]})
                backend, _ = self.backend(defect=defect)
                native_generate = backend.generate
                def generate(*args):
                    llm = backend.model if KEY == "internvl35" else backend.model.llm
                    llm.calls = 0
                    raw = native_generate(*args)
                    raw["evidence_kind"] = "SYNTHETIC_SCRIPTED_LOGITS_NOT_MODEL_PREDICTIONS"
                    return raw
                backend.generate = generate
                def factory():
                    if defect == "load": raise RuntimeError("SYNTHETIC loader failure")
                    return backend
                parsed = []
                def parser(text):
                    self.assertTrue(list((store.root/"samples").glob("*/raw.json")))
                    parsed.append(text)
                    return parse_label(text)
                with ExitStack() as stack:
                    # Test-only model identity wiring. No production roster/grant change.
                    stack.enter_context(patch.dict(runner.MODELS, {KEY: {k: self.spec[k] for k in ("id", "revision")}}))
                    stack.enter_context(patch.object(runner, "settings", return_value={"synthetic": True, "generation": GENERATION}))
                    stack.enter_context(patch.object(runner, "parse_label", parser))
                    if defect == "raw_write":
                        stack.enter_context(patch.object(store, "raw", side_effect=OSError(errno.ENOSPC, "SYNTHETIC disk full")))
                    results, blocked = runner.execute(store, rows, factory,
                        {"attempt_id": "SYNTHETIC", "run_id": "SYNTHETIC"}, KEY, {"synthetic": True})
                self.assertEqual(blocked, defect is not None)
                if defect in ("oom", "load", "raw_write"):
                    self.assertFalse(parsed)
                    self.assertEqual(results["1"]["status"], "NOT_ATTEMPTED")
                elif defect == "nonfinite":
                    self.assertEqual(results["1"]["status"], "NOT_ATTEMPTED")
                else:
                    self.assertEqual([r["status"] for r in results.values()], ["SUCCESS", "SUCCESS"])
                export(store.root, root/"synthetic.zip")
                import_archive(root/"synthetic.zip", root/"imported")


if __name__ == "__main__":
    unittest.main()
