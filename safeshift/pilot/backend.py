"""Native model adapters. Imported ML libraries only after authorization/preflight.

    One FP16 T4, eager attention, no quantization or preprocessing fallback.
    Passive outer-forward capture persists only bounded candidate logits.
"""
import hashlib
import importlib.metadata
import os
from pathlib import Path
import time
from unittest.mock import patch

from .artifacts import read, sha, write
from .contract import GENERATION, MODELS
from .hnlo import candidate_ids, probe, tokenizer_replay


def check_source_review(repo, key):
    """A valid token is access, not approval of previously unread source bytes."""
    locked = read(Path(repo) / "configs/pilot/model_source_lock.json")[key]
    spec = MODELS[key]
    if locked.get("id") != spec["id"] or locked.get("revision") != spec["revision"]:
        raise PermissionError("BLOCKED_SOURCE_REVIEW_IDENTITY_MISMATCH")
    required = {"config.json", "tokenizer.json", "tokenizer_config.json", "preprocessor_config.json"}
    if locked.get("unavailable") or not required <= set(locked.get("files", {})):
        raise PermissionError("BLOCKED_SOURCE_TOKENIZER_AUDIT_INCOMPLETE:" + key)
    return locked


def check_software(repo, key):
    expected = read(Path(repo) / "configs/pilot/runtime_versions.json")[key]
    actual = {name: importlib.metadata.version(name) for name in expected}
    if actual != expected:
        raise RuntimeError("PINNED_DEPENDENCY_MISMATCH")
    return actual


def provision(repo, key, cache, token=None):
    """No pickle weights. Inspect/reject custom-code drift BEFORE any import."""
    locked = check_source_review(repo, key)
    from huggingface_hub import HfApi, snapshot_download
    spec = MODELS[key]
    info = HfApi().model_info(spec["id"], revision=spec["revision"], files_metadata=True, token=token)
    if info.sha != spec["revision"]:
        raise ValueError("MODEL_REVISION_MISMATCH")
    names = [r.rfilename for r in info.siblings]
    executable = {n for n in names if n.endswith(".py")}
    if executable != {n for n in locked["files"] if n.endswith(".py")}:
        raise ValueError("UNREVIEWED_EXECUTABLE_CODE")
    allowed = [n for n in names if "/" not in n and n.endswith((".json", ".model", ".txt", ".py", ".safetensors"))]
    # A small config/tokenizer/code request establishes gated read access and
    # validates executable source before requesting any checkpoint bytes.
    non_weights = [n for n in allowed if not n.endswith(".safetensors")]
    snapshot = Path(snapshot_download(spec["id"], revision=spec["revision"], cache_dir=cache,
                                      allow_patterns=non_weights, token=token))
    if snapshot.name != spec["revision"]:
        raise ValueError("SNAPSHOT_REVISION")
    hashes = {}
    for name in non_weights:
        p = snapshot / name
        # HF's own cache blob symlinks are allowed only inside this cache repo.
        if not p.resolve().is_relative_to(snapshot.parent.parent.resolve()):
            raise ValueError("MODEL_CACHE_ESCAPE")
        hashes[name] = sha(p)
        if name in locked["files"] and hashes[name] != locked["files"][name]:
            raise ValueError("REVIEWED_SOURCE_CHECKSUM:" + name)
    for name in locked["files"]:
        if name.endswith((".py", ".json", ".model", ".txt")) and name not in hashes:
            raise ValueError("REVIEWED_SOURCE_MISSING:" + name)
    for name in ("config.json", "processor_config.json", "preprocessor_config.json", "tokenizer_config.json"):
        payload = read(snapshot / name) if (snapshot / name).exists() else {}
        if "--" in str(payload.get("auto_map", {})):
            raise ValueError("EXTERNAL_AUTO_MAP_FORBIDDEN")
    weights = [n for n in allowed if n.endswith(".safetensors")]
    if not weights:
        raise ValueError("OFFICIAL_SAFETENSORS_REQUIRED_NO_PICKLE_FALLBACK")
    downloaded = Path(snapshot_download(spec["id"], revision=spec["revision"], cache_dir=cache,
                                        allow_patterns=weights, token=token))
    if downloaded != snapshot:
        raise ValueError("MODEL_SNAPSHOT_CHANGED")
    for name in weights:
        p = snapshot / name
        if not p.resolve().is_relative_to(snapshot.parent.parent.resolve()):
            raise ValueError("MODEL_WEIGHT_CACHE_ESCAPE")
        hashes[name] = sha(p)
    # Verify downloaded safetensors against Hub LFS SHA, when supplied.
    for row in info.siblings:
        if row.rfilename.endswith(".safetensors"):
            expected = row.lfs.get("sha256") if isinstance(row.lfs, dict) else getattr(row.lfs, "sha256", None)
            if not expected or hashes.get(row.rfilename) != expected:
                raise ValueError("WEIGHT_LFS_CHECKSUM_REQUIRED")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    return snapshot, {"model_id": spec["id"], "revision": spec["revision"], "files": hashes,
                      "remote_code_review": locked["review_status"]}


def memory(torch):
    return {"gpu0_allocated": torch.cuda.memory_allocated(0), "gpu0_reserved": torch.cuda.memory_reserved(0),
            "gpu0_peak_allocated": torch.cuda.max_memory_allocated(0),
            "gpu0_peak_reserved": torch.cuda.max_memory_reserved(0)}


class NativeBackend:
    def __init__(self, key, snapshot, prompt):
        load_start = time.perf_counter()
        import torch
        import transformers
        self.key, self.torch, self.prompt = key, torch, prompt
        spec = MODELS[key]
        kwargs = {"local_files_only": True, "trust_remote_code": spec["remote_code"],
                  "revision": spec["revision"]}
        if spec["remote_code"]:
            kwargs["code_revision"] = spec["revision"]
        self.processor = transformers.AutoProcessor.from_pretrained(
            str(snapshot), **kwargs, **({"num_crops": 16} if key == "phi" else {}))
        cls = (transformers.AutoModelForCausalLM if key == "phi" else
               transformers.Gemma3ForConditionalGeneration if key == "gemma" else
               transformers.SmolVLMForConditionalGeneration)
        self.model = cls.from_pretrained(str(snapshot), **kwargs, torch_dtype=torch.float16,
                                         device_map={"": 0}, attn_implementation="eager",
                                         use_safetensors=True).eval()
        if any(p.device.type != "cuda" or p.device.index != 0 or p.dtype != torch.float16
               for p in self.model.parameters() if p.is_floating_point()):
            raise ValueError("EXACT_FP16_SINGLE_T4_PLACEMENT_REQUIRED")
        for _, module in self.model.named_modules():
            if "FlashAttention" in type(module).__name__ or "SdpaAttention" in type(module).__name__:
                raise ValueError("UNEXPECTED_ATTENTION_IMPLEMENTATION")
        self.tokenizer = self.processor.tokenizer
        self.serialized_tokenizer = self.tokenizer.backend_tokenizer.to_str().encode() if self.tokenizer.is_fast else None
        from tokenizers import Tokenizer
        self.cpu_tokenizer = Tokenizer.from_str(self.serialized_tokenizer.decode()) if self.serialized_tokenizer else None
        # Fresh native greedy config prevents inherited forcing/suppression.
        self.generation = transformers.GenerationConfig(
            **GENERATION, bos_token_id=self.model.generation_config.bos_token_id,
            eos_token_id=self.model.generation_config.eos_token_id,
            pad_token_id=self.model.generation_config.pad_token_id)
        self.environment = {"model_class": type(self.model).__name__, "processor_class": type(self.processor).__name__,
                            "model_config": self.model.config.to_dict(),
                            "processor": self.processor.to_dict() if hasattr(self.processor, "to_dict") else {},
                            "image_processor": self.processor.image_processor.to_dict(),
                            "chat_template": self.tokenizer.chat_template if key == "phi" else self.processor.chat_template,
                            "generation": self.generation.to_dict(), "load_memory": memory(torch)}
        self.environment["load_seconds"] = time.perf_counter() - load_start

    def prepare(self, image):
        if self.key == "phi":
            messages = [{"role": "user", "content": "<|image_1|>\n" + self.prompt}]
            rendered = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self.processor(rendered, [image], return_tensors="pt")
        else:
            messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": self.prompt}]}]
            rendered = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self.processor(text=rendered, images=[image], return_tensors="pt", add_special_tokens=False)
        # Keep integer token IDs/masks and dimensions in their native dtypes.
        inputs = {k: v.to(device="cuda:0", dtype=self.torch.float16 if v.is_floating_point() else v.dtype)
                  for k, v in inputs.items()}
        return rendered, inputs

    def generate(self, image_path, sample_dir):
        from PIL import Image
        torch = self.torch
        sample_dir = Path(sample_dir)
        self.stage = "preprocessing"
        with Image.open(image_path) as original:
            if getattr(original, "n_frames", 1) != 1:
                raise ValueError("STILL_IMAGE_REQUIRED")
            original.load()
            with original.convert("RGB") as image:
                rendered, inputs = self.prepare(image)
        input_ids = inputs["input_ids"][0].tolist()
        try:
            token_probe = probe(self.tokenizer, rendered, input_ids)
            candidates = candidate_ids(token_probe)
            probe_error = None
        except Exception as error:
            token_probe, candidates = None, []
            probe_error = type(error).__name__ + ": " + str(error)
        write(sample_dir / "request.json", {"prompt": self.prompt, "rendered_prompt": rendered,
              "input_ids": input_ids, "token_probe": token_probe, "generation": self.generation.to_dict(),
              "input_shapes": {k: list(v.shape) for k, v in inputs.items()}})
        steps, errors, processors_seen = [], [], None
        overhead_seconds, overhead_allocated = 0.0, 0

        def capture(module, args, kwargs, output):
            nonlocal overhead_seconds, overhead_allocated
            start = time.perf_counter()
            before = torch.cuda.memory_allocated(0)
            try:
                last = output.logits[0, -1, :].detach()
                # Model-output logits, before generate() receives the output and
                # before any logits processor/warper. Never modify returned data.
                vals = last[candidates].float().cpu().tolist() if candidates else []
                finite = bool(torch.isfinite(last).all().item())
                step = {"step": len(steps), "raw_candidate_logits": dict(zip(map(str, candidates), vals)),
                        "argmax": int(last.argmax().item()), "all_finite": finite,
                        "dtype": str(last.dtype), "vocab_size": last.numel(),
                        "origin": "outer_forward_output_before_generate_processors"}
                overhead_allocated = max(overhead_allocated, torch.cuda.memory_allocated(0) - before,
                                         len(candidates) * 4 + last.numel())
                # Nonfinite logits remain explicit evidence, never invalid JSON floats.
                if not all(__import__("math").isfinite(x) for x in vals):
                    step["raw_candidate_logits"] = {}
                write(sample_dir / f"steps/{len(steps):03d}.json", step)
                steps.append(step)
            except OSError:
                raise  # raw evidence cannot be persisted: stop classification
            except Exception as error:
                errors.append(type(error).__name__ + ": " + str(error))
            finally:
                overhead_seconds += time.perf_counter() - start
            return None

        native_processors = self.model._get_logits_processor
        def observe_processors(*args, **kwargs):
            nonlocal processors_seen
            actual = native_processors(*args, **kwargs)
            processors_seen = [type(p).__module__ + "." + type(p).__name__ for p in actual]
            write(sample_dir / "processors.json", {"actual": processors_seen})
            return actual

        self.stage = "generation"
        torch.cuda.synchronize(0)
        torch.cuda.reset_peak_memory_stats(0)
        start = time.perf_counter()
        handle = self.model.register_forward_hook(capture, with_kwargs=True)
        try:
            with patch.object(self.model, "_get_logits_processor", observe_processors), torch.inference_mode():
                write(sample_dir / "native_call.json", {"invocation": 1, "max_new_tokens": 64})
                result = self.model.generate(**inputs, generation_config=self.generation)
            torch.cuda.synchronize(0)
        finally:
            handle.remove()
        seconds = time.perf_counter() - start
        all_ids = result.sequences[0].tolist()
        if all_ids[:len(input_ids)] != input_ids:
            raise ValueError("NATIVE_INPUT_PREFIX_CHANGED")
        generated = all_ids[len(input_ids):]
        # Durable native token IDs before first decode/parsing.
        write(sample_dir / "native.json", {"input_ids": input_ids, "generated_ids": generated})
        self.stage = "decode"
        response = self.tokenizer.decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        eos = self.generation.eos_token_id
        raw = {"response": response, "generated_ids": generated, "input_ids": input_ids, "token_probe": token_probe,
                "steps": steps, "actual_logits_processors": processors_seen,
                "eos_token_ids": eos if isinstance(eos, list) else [eos],
                "capture_error": probe_error or ("; ".join(errors) if errors else None),
                "seconds": seconds, "memory": memory(torch),
                "hnlo_overhead": {"observer_seconds": overhead_seconds,
                                  "temporary_allocated_bytes_upper_estimate": overhead_allocated,
                                  "paired_hook_off_run": "NOT_RUN_NO_EXTRA_INFERENCE_AUTHORIZED",
                                  "peak_delta_vs_hook_off": None,
                                  "method": "passive reductions+CPU/fsync time; allocator estimate, not paired total overhead"},
                "raw_nonfinite": any(not s["all_finite"] for s in steps)}
        try:
            replay_start = time.perf_counter()
            if self.serialized_tokenizer is None:
                raise ValueError("FAST_TOKENIZER_SERIALIZATION_UNAVAILABLE")
            raw["cpu_tokenizer_replay"] = tokenizer_replay(raw, self.cpu_tokenizer)
            raw["tokenizer_serialization_sha256"] = hashlib.sha256(self.serialized_tokenizer).hexdigest()
            raw["hnlo_overhead"]["cpu_tokenizer_replay_seconds"] = time.perf_counter() - replay_start
        except Exception as error:
            raw["cpu_tokenizer_replay"] = {"status": "FAIL", "reason": type(error).__name__ + ": " + str(error)}
        return raw
