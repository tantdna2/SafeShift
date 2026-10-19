"""Isolated multi-image capture adapter; existing production runners stay unchanged."""
from contextlib import ExitStack
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import time

from safeshift.ls1.tokenizer import probe
from safeshift.protocol.classification_policy import load_policy, render_prompt
from ..hnlo_capture import ordered_t1_ids
from ..one_click.worker import no_forcing, verify_snapshot, memory
from .capture import persist_torch


class Backend:
    def __init__(self, repo, model_key, cache, inputs, index, source, runtime, checkpoint):
        import torch
        import transformers
        from transformers import AutoTokenizer
        self.repo, self.key, self.inputs, self.index = Path(repo), model_key, Path(inputs), index
        self.torch, self.stack, self.cap, self.calls, self.loads = torch, ExitStack(), None, set(), 0
        snapshot, receipt = checkpoint  # verified once before model load
        self.tokenizer = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True,
                                                       trust_remote_code=False, use_fast=True)
        self.t1 = probe(self.tokenizer)
        self.candidates = ordered_t1_ids(self.t1)
        self.policy = load_policy(repo, qwen3_runtime=True)["classification"][model_key]
        cls = getattr(transformers, "Qwen3VLForConditionalGeneration" if model_key == "qwen3"
                      else "InternVLForConditionalGeneration")
        load, generate = cls.from_pretrained, cls.generate
        processors, stopping = cls._get_logits_processor, cls._get_stopping_criteria

        def counted_load(*args, **kwargs):
            if self.loads:
                raise RuntimeError("SECOND_MODEL_LOAD_FORBIDDEN")
            self.loads += 1
            index.write("load-start", {"ordinal": 1})
            began, state = time.monotonic(), "FAILED"
            try:
                result = load(*args, **kwargs)
                for device in range(torch.cuda.device_count()):
                    torch.cuda.synchronize(device)
                state = "RETURNED"
            finally:
                index.write("native-load-timing", {"seconds": time.monotonic() - began, "status": state})
            index.write("load-return", {"ordinal": 1})
            return result

        def counted_generate(native, *args, **kwargs):
            if self.cap is None:
                raise RuntimeError("UNBOUND_NATIVE_CALL_FORBIDDEN")
            ordinal = self.cap.journal.read("identity")["ordinal"]
            if ordinal in self.calls:
                raise RuntimeError("SECOND_CALL_FOR_SAMPLE_FORBIDDEN")
            self.calls.add(ordinal)
            index.write(f"sample-{ordinal:06d}.native-call", {"ordinal": ordinal,
                "exposure": "NATIVE_CALL_START_RECORDED_BEFORE_INVOCATION"})
            return generate(native, *args, **kwargs)

        def observed_processors(native, *args, **kwargs):
            actual = processors(native, *args, **kwargs)
            self.cap.write("raw-provenance", {"processors": [type(p).__module__ + "." + type(p).__name__ for p in actual]})
            if actual:
                raise ValueError("EMPTY_ACTUAL_PROCESSOR_LIST_REQUIRED")
            return actual

        def observed_stopping(native, *args, **kwargs):
            actual = stopping(native, *args, **kwargs)
            if sorted(type(c).__name__ for c in actual) != ["EosTokenCriteria", "MaxLengthCriteria"]:
                raise ValueError("EXACT_NATIVE_STOPPING_CRITERIA_REQUIRED")
            maxima = [c.max_length for c in actual if type(c).__name__ == "MaxLengthCriteria"]
            eos = [c.eos_token_id.tolist() for c in actual if type(c).__name__ == "EosTokenCriteria"]
            self.cap.write("stopping", {"max_length": maxima[0], "eos_token_ids": eos[0]})
            return actual

        self.stack.enter_context(patch.object(cls, "from_pretrained", side_effect=counted_load))
        self.stack.enter_context(patch.object(cls, "generate", counted_generate))
        self.stack.enter_context(patch.object(cls, "_get_logits_processor", observed_processors))
        self.stack.enter_context(patch.object(cls, "_get_stopping_criteria", observed_stopping))
        try:
            if model_key == "internvl3":
                from safeshift.ls1.runtime import NativeScorer
                self.scorer = NativeScorer(model_key, snapshot, self.tokenizer, self.candidates, repo=repo)
                self.processor, self.model = self.scorer.processor, self.scorer.model
            else:
                from safeshift.runners.qwen3_vl import Qwen3VLRunner
                from safeshift.runners.contracts import RunContext
                self.context = RunContext(run_id="hnlo-pilot8-v1-qwen3-s0-a1", call_id="ordinal-only", source_kind="INSPECSAFE",
                    git_commit_sha=source["merge_commit"], command="hnlo-resource-pilot-worker",
                    **{k: self.policy[k] for k in ("decoding", "preprocessing", "precision", "quantization",
                                                  "device", "software_versions", "seed")})
                self.runner = Qwen3VLRunner()
                self.runner.initialize(self.context)
                self.runner.load(self.context)
                self.processor, self.model = self.runner._resources
            no_forcing(self.model.generation_config)
            if probe(self.processor.tokenizer) != self.t1:
                raise ValueError("PROCESSOR_TOKENIZER_T1_MISMATCH")
            self.prompt = render_prompt(model_key, repo=repo)
            index.write("model", {"model": model_key, "runtime": runtime, "snapshot": receipt,
                "policy": self.policy, "prompt": self.prompt, "tokenizer_t1": self.t1,
                "processor_class": type(self.processor).__name__, "model_class": type(self.model).__name__,
                "processor_config": self.processor.to_dict() if hasattr(self.processor, "to_dict") else None,
                "generation_config": self.model.generation_config.to_dict(),
                "device_map": getattr(self.model, "hf_device_map", {"": "cuda:0"}), "clamp": None})
        except BaseException:
            self.stack.close()
            raise

    def generate(self, row, cap):
        self.cap = cap
        data = (self.inputs / f"{row['ordinal']:06d}.image").read_bytes()
        import hashlib
        if hashlib.sha256(data).hexdigest() != row["image_sha256"]:
            raise ValueError("STAGED_IMAGE_CHECKSUM_MISMATCH")
        cap.write("runtime-t1", self.t1)
        if self.key == "internvl3":
            from PIL import Image
            self.scorer.validator()
            if hasattr(self.model, "_cache"):
                self.model._cache = None
            with Image.open(BytesIO(data)) as image:
                if getattr(image, "n_frames", 1) != 1:
                    raise ValueError("STILL_IMAGE_REQUIRED")
                image.load()
                rgb = image.convert("RGB")
                try:
                    inputs = self.scorer.prepare(rgb, ())
                finally:
                    rgb.close()
            validate = self.scorer.validator
        else:
            from safeshift.runners.contracts import Request, Task
            from safeshift.runners.qwen3_placement import require_loaded_state
            self.runner._clear_call_state(self.model)
            prepared = self.runner.prepare_input(Request(Task.CLASSIFICATION, str(row["ordinal"]),
                "opaque-image", data, "p2-classification-c1-v1", self.prompt), self.context)
            inputs = prepared.inputs
            validate = lambda: require_loaded_state(self.model)
        grid = inputs.get("image_grid_thw")
        cap.write("complexity", {"input_tokens": int(inputs["input_ids"].shape[1]),
            "image_patches": int(inputs["pixel_values"].shape[0]),
            "patch_unit": "448x448_tiles_including_thumbnail" if self.key == "internvl3" else "native_grid_patches",
            "image_grid_thw": grid.tolist() if grid is not None else None,
            "input_shapes": {k: list(v.shape) for k, v in inputs.items()}})
        config = deepcopy(self.model.generation_config)
        from ..hnlo_hf import greedy
        kwargs = greedy(config, deepcopy(self.policy["decoding"]))
        validate()
        cap.write("call", {"configuration": config.to_dict(), "kwargs": kwargs,
            "input_shapes": {k: list(v.shape) for k, v in inputs.items()}})
        with self.torch.inference_mode():
            output = self.model.generate(**inputs, generation_config=config, **kwargs)
        persist_torch(output, inputs["input_ids"][0].tolist(), self.candidates, self.tokenizer,
                      cap, config.to_dict(), kwargs, self.torch)
        for device in range(self.torch.cuda.device_count()):
            self.torch.cuda.synchronize(device)
        validate()
        if self.key == "qwen3":
            self.runner._clear_call_state(self.model)
        self.cap = None

    def close(self):
        self.index.write("native-counts", {"load_calls": self.loads, "generate_ordinals": sorted(self.calls),
                                           "memory": memory(self.torch)})
        self.stack.close()
