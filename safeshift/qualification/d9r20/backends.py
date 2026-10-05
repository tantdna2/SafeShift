"""Thin model-specific paths; no imports of model libraries until authorized load."""
from io import BytesIO


class NativeBackend:
    def __init__(self, key, candidate, snapshot, generation, seed):
        self.key, self.candidate, self.snapshot = key, candidate, snapshot
        self.generation, self.seed = generation, seed
        self.model = self.processor = self.torch = None
        self.load_attempted = False

    def load(self):
        if self.load_attempted:
            raise ValueError("ONE_LOAD_ATTEMPT_ONLY")
        self.load_attempted = True
        import torch
        import transformers
        self.torch = torch
        torch.manual_seed(self.seed)
        torch.cuda.manual_seed_all(self.seed)
        torch.cuda.reset_peak_memory_stats(0)
        kwargs = {"revision": self.candidate["revision"], "local_files_only": True,
                  "trust_remote_code": self.candidate["trust_remote_code"],
                  "torch_dtype": torch.float16, "use_safetensors": True}
        factory = getattr(transformers, self.candidate["loader"])
        # No device_map='auto', quantizer, CPU/disk offload, retry or dtype fallback.
        self.model = factory.from_pretrained(str(self.snapshot), **kwargs).to("cuda:0").eval()
        if self.key == "ovis":
            if self.model.config.name_or_path != str(self.snapshot):
                raise ValueError("OVIS_NESTED_ASSETS_NOT_LOCAL")
            self.processor = self.model.text_tokenizer
        else:
            self.processor = transformers.AutoProcessor.from_pretrained(
                str(self.snapshot), revision=self.candidate["revision"], local_files_only=True,
                trust_remote_code=self.candidate["trust_remote_code"])
        self.check_placement()

    def check_placement(self):
        torch = self.torch
        if getattr(self.model, "is_quantized", False) or getattr(self.model, "hf_device_map", None):
            raise ValueError("QUANTIZATION_OR_DEVICE_MAP_FORBIDDEN")
        count = 0
        for _, tensor in self.model.named_parameters():
            count += 1
            if str(tensor.device) != "cuda:0" or (tensor.is_floating_point() and tensor.dtype != torch.float16):
                raise ValueError("PARAMETER_PLACEMENT_OR_DTYPE")
        for _, tensor in self.model.named_buffers():
            if str(tensor.device) != "cuda:0":
                raise ValueError("BUFFER_OFFLOAD_FORBIDDEN")
        if not count:
            raise ValueError("NO_MODEL_PARAMETERS")

    def memory(self):
        if self.torch is None:
            return {"available": False}
        cuda = self.torch.cuda
        return {"allocated": cuda.memory_allocated(0), "reserved": cuda.memory_reserved(0),
                "peak_allocated": cuda.max_memory_allocated(0), "peak_reserved": cuda.max_memory_reserved(0)}

    def generate(self, image_bytes, prompt):
        from PIL import Image
        torch = self.torch
        self.check_placement()
        with Image.open(BytesIO(image_bytes)) as source:
            source.load()
            if source.size != (256, 256) or source.mode != "RGB" or source.format != "PNG":
                raise ValueError("EXACT_SYNTHETIC_RGB_IMAGE_REQUIRED")
            image = source.copy()
        kwargs = dict(self.generation)
        try:
            if self.key == "ovis":
                prep = self.candidate["preprocessing"]
                ids, pixels, grid = self.model.preprocess_inputs(
                    messages=[{"role": "user", "content": [{"type": "image", "image": image},
                                                               {"type": "text", "text": prompt}]}],
                    min_pixels=prep["min_pixels"], max_pixels=prep["max_pixels"],
                    add_generation_prompt=True, enable_thinking=False)
                inputs = {"inputs": ids.to("cuda:0"), "pixel_values": pixels.to(device="cuda:0", dtype=torch.float16),
                          "grid_thws": grid.to("cuda:0")}
                kwargs.update(enable_thinking=False, enable_thinking_budget=False)
                native_config = self.model.llm.generation_config.to_dict()
            else:
                prepared = self.processor(text=prompt, images=[image], return_tensors="pt")
                ids = prepared["input_ids"]
                inputs = {k: v.to(device="cuda:0", dtype=torch.float16) if v.is_floating_point()
                          else v.to("cuda:0") for k, v in prepared.items()}
                native_config = (self.model.text_model if self.key == "kosmos" else self.model).generation_config.to_dict()
            input_ids = ids.tolist()
            tensor_observations = {k: {"shape": list(v.shape), "dtype": str(v.dtype), "device": str(v.device)}
                                   for k, v in inputs.items()}
            with torch.inference_mode():
                generated = self.model.generate(**inputs, **kwargs)
            # No decode or output validation until this return value is persisted.
            return {"model_id": self.candidate["model_id"], "revision": self.candidate["revision"],
                    "input_ids": input_ids, "generated_ids": generated.tolist(),
                    "input_tensors": tensor_observations, "generation_kwargs": kwargs,
                    "effective_generation_defaults": native_config, "original_image_size": [256, 256]}
        finally:
            image.close()

    def decode(self, native):
        if (native["model_id"], native["revision"]) != (self.candidate["model_id"], self.candidate["revision"]):
            raise ValueError("NATIVE_IDENTITY_MISMATCH")
        rows, inputs = native["generated_ids"], native["input_ids"]
        if type(rows) is not list or len(rows) != 1 or type(inputs) is not list or len(inputs) != 1:
            raise ValueError("BATCH_ONE_REQUIRED")
        ids, prefix = rows[0], inputs[0]
        if (not ids or not prefix or any(type(v) is not int or v < 0 for v in ids)
                or any(type(v) is not int for v in prefix)):
            raise ValueError("INVALID_NATIVE_TOKEN_IDS")
        if self.key == "ovis":
            if any(v < 0 and v not in (-301, -302, -300) for v in prefix):
                raise ValueError("INVALID_OVIS_SENTINEL")
            continuation = ids  # exact Ovis implementation returns completion IDs
            tokenizer = self.processor
        else:
            if ids[:len(prefix)] != prefix or any(v < 0 for v in prefix):
                raise ValueError("GENERATED_INPUT_PREFIX_MISMATCH")
            continuation = ids[len(prefix):]
            tokenizer = self.processor.tokenizer
        eos = native["effective_generation_defaults"].get("eos_token_id")
        eos = [eos] if type(eos) is int else eos
        if not eos or any(type(v) is not int for v in eos):
            raise ValueError("UNINSPECTABLE_EOS_CONTRACT")
        termination = ("EOS" if continuation and continuation[-1] in eos
                       and not any(v in eos for v in continuation[:-1])
                       and len(continuation) <= self.generation["max_new_tokens"] else "INVALID_OR_TRUNCATED")
        return {"continuation_ids": continuation, "termination": termination,
                "text": tokenizer.decode(continuation, skip_special_tokens=True, clean_up_tokenization_spaces=False),
                "with_special_tokens": tokenizer.decode(continuation, skip_special_tokens=False, clean_up_tokenization_spaces=False)}
