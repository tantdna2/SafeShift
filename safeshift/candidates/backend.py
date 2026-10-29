"""Two candidate adapters, PREP only; reused pilot Store/runner own parse/custody.

No model roster change, grant, downloader, notebook or automatic execution.
Raw IDs are saved before decoding; bounded raw logits before generation processors.
"""
import hashlib
import time
from pathlib import Path
from unittest.mock import patch

from safeshift.pilot.artifacts import write, read
from safeshift.pilot.backend import native_generation_config
from safeshift.pilot.contract import GENERATION, PROMPT_SHA
from safeshift.pilot.hnlo import probe, candidate_ids, tokenizer_replay
from .inputs import prepare_inputs, validate_inputs
from .loading import native_setup, load_weight_model
from .source import LOCK, require


def generation_config(model, tokenizer, key):
    config = native_generation_config(model)
    if key == "minicpm4":
        # Pinned _decode supplies these native IDs to llm.generate. It never
        # receives chat()'s hidden beam3/repetition1.2 or decode cleanup defaults.
        ids = [tokenizer.convert_tokens_to_ids(t) for t in model.terminators]
        require(set(ids) == set(config.eos_token_id), "MINICPM_NATIVE_EOS_MISMATCH")
        require(all(isinstance(i, int) and 0 <= i < len(tokenizer) for i in ids), "EOS_IDS")
        config.eos_token_id, config.pad_token_id = ids, 0
    require(all(getattr(config, k) == v for k, v in GENERATION.items()), "FROZEN_GENERATION")
    require(config.repetition_penalty == 1.0 and config.min_new_tokens is None,
            "UNREQUESTED_GENERATION_CONSTRAINT")
    return config


def transfer_inputs(inputs, device, dtype):
    import torch
    def move(value):
        if isinstance(value, torch.Tensor):
            return value.to(device=device, dtype=dtype if value.is_floating_point() else value.dtype)
        if isinstance(value, list):
            return [move(v) for v in value]
        return value
    # MiniCPM accepts image_sizes in the processor output, not the LLM kwargs.
    return {k: move(v) for k, v in inputs.items() if k != "image_sizes"}


def persist_ids(result, inputs, key, path):
    import torch
    sequences = result.sequences
    # Save malformed shapes/IDs as received before reporting the contract error.
    received = sequences.detach().cpu().tolist()
    input_ids = inputs["input_ids"][0].tolist()
    shape_ok = sequences.ndim == 2 and sequences.shape[0] == 1
    ids = received[0] if shape_ok else []
    prefix_ok = ids[:len(input_ids)] == input_ids if key == "internvl35" else None
    generated = ids[len(input_ids):] if key == "internvl35" else ids
    write(path, {"input_ids": input_ids, "returned_ids": received, "generated_ids": generated,
                 "input_prefix_match": prefix_ok,
                 "sequence_semantics": "prompt_plus_continuation" if key == "internvl35" else "continuation_only_inputs_embeds"})
    require(shape_ok and sequences.dtype in (torch.int32, torch.int64), "NATIVE_SEQUENCE_SHAPE_DTYPE")
    if key == "internvl35":
        require(prefix_ok, "NATIVE_INPUT_PREFIX_CHANGED")
    require(1 <= len(generated) <= GENERATION["max_new_tokens"], "NATIVE_GENERATED_TOKEN_COUNT")
    return input_ids, generated


class CandidateBackend:
    """Offline integration API. Production runner enrollment requires a new release."""
    def __init__(self, key, snapshot, weights, prompt, *, device="cuda:0"):
        require(hashlib.sha256(prompt.encode()).hexdigest() == PROMPT_SHA, "FROZEN_C1_SHA")
        self.key, self.prompt, self.device = key, prompt, device
        self.stage = "model_load"
        evidence = {}
        self.processor, self.tokenizer, self.config, cls = native_setup(Path(snapshot), key, evidence)
        self.model, attention = load_weight_model(snapshot, key, self.config, cls, weights, device)
        self.configure()
        self.environment = {"model": {k: read(LOCK)[key][k] for k in ("id", "revision")},
                            "native": evidence, "attention": attention,
                            "generation": self.generation.to_dict(), "prompt_sha256": PROMPT_SHA}

    def configure(self):
        import torch
        from tokenizers import Tokenizer
        self.dtype = torch.float16
        self.generation = generation_config(self.model, self.tokenizer, self.key)
        self.serialized_tokenizer = self.tokenizer.backend_tokenizer.to_str().encode()
        self.cpu_tokenizer = Tokenizer.from_str(self.serialized_tokenizer.decode())

    def generate(self, image_path, sample_dir):
        import torch
        from PIL import Image
        sample_dir = Path(sample_dir)
        self.stage = "preprocessing"
        with Image.open(image_path) as original:
            require(getattr(original, "n_frames", 1) == 1, "STILL_IMAGE_REQUIRED")
            original.load()
            image_info = {"decoded_format": original.format, "source_mode": original.mode,
                          "size": list(original.size), "processor_mode": "RGB"}
            with original.convert("RGB") as image:
                rendered, inputs = prepare_inputs(self.processor, self.key, self.prompt, image)
                detail = validate_inputs(self.processor, self.key, self.config, rendered, inputs, self.prompt)
        input_ids = inputs["input_ids"][0].tolist()
        token_probe, candidates, probe_error = None, [], None
        try:
            token_probe = probe(self.tokenizer, rendered, input_ids)
            candidates = candidate_ids(token_probe)
        except Exception as error:
            probe_error = type(error).__name__ + ": " + str(error)
        write(sample_dir / "request.json", {"prompt": self.prompt, "rendered_prompt": rendered,
            "input_ids": input_ids, "generation": self.generation.to_dict(), "input_detail": detail,
            "token_probe": token_probe, "image": image_info, "model": self.environment["model"]})
        inputs = transfer_inputs(inputs, self.device, self.dtype)
        target = self.model if self.key == "internvl35" else self.model.llm
        steps, processors_seen = [], None

        def capture(module, args, kwargs, output):
            last = output.logits[0, -1, :].detach()
            finite = bool(torch.isfinite(last).all())
            step = {"step": len(steps), "raw_candidate_logits":
                    dict(zip(map(str, candidates), last[candidates].float().cpu().tolist())) if finite else {},
                    "argmax": int(last.argmax()), "all_finite": finite,
                    "dtype": str(last.dtype), "vocab_size": last.numel(),
                    "origin": "outer_forward_output_before_generate_processors"}
            write(sample_dir / f"steps/{len(steps):03d}.json", step)
            steps.append(step)

        native_processors = target._get_logits_processor
        def observe(*args, **kwargs):
            nonlocal processors_seen
            actual = native_processors(*args, **kwargs)
            processors_seen = [type(p).__module__ + "." + type(p).__name__ for p in actual]
            write(sample_dir / "processors.json", {"actual": processors_seen})
            return actual

        self.stage = "generation"
        start = time.perf_counter()
        handle = target.register_forward_hook(capture, with_kwargs=True)
        try:
            with patch.object(target, "_get_logits_processor", observe), torch.inference_mode():
                write(sample_dir / "native_call.json", {"invocation": 1, "max_new_tokens": 64})
                if self.key == "internvl35":
                    result = self.model.generate(**inputs, generation_config=self.generation)
                else:
                    result = self.model.generate(**inputs, tokenizer=self.tokenizer, decode_text=False,
                                                 stream=False, generation_config=self.generation)
        finally:
            handle.remove()
        seconds = time.perf_counter() - start
        input_ids, generated = persist_ids(result, inputs, self.key, sample_dir / "native.json")
        require(all(0 <= i < len(self.tokenizer) for i in generated), "NATIVE_TOKEN_VOCAB_RANGE")
        require(len(steps) == len(generated), "RAW_LOGIT_STEP_COUNT")
        self.stage = "decode"
        response = self.tokenizer.decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        eos = self.generation.eos_token_id
        raw = {"response": response, "generated_ids": generated, "input_ids": input_ids,
            "eos_token_ids": eos if isinstance(eos, list) else [eos],
            "token_probe": token_probe, "steps": steps, "capture_error": probe_error,
            "actual_logits_processors": processors_seen, "seconds": seconds,
            "raw_nonfinite": any(not step["all_finite"] for step in steps),
            "logit_capture_boundary": "internvl_outer" if self.key == "internvl35" else "minicpm_llm_forward",
            "tokenizer_serialization_sha256": hashlib.sha256(self.serialized_tokenizer).hexdigest()}
        try:
            raw["cpu_tokenizer_replay"] = tokenizer_replay(raw, self.cpu_tokenizer)
        except Exception as error:
            raw["cpu_tokenizer_replay"] = {"status": "FAIL", "reason": type(error).__name__ + ": " + str(error)}
        return raw
