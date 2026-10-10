"""Independent batch-one native HF LS1 scorer. Never calls production runners."""

from copy import deepcopy
from datetime import datetime, timezone
import math
import platform
from types import SimpleNamespace

from safeshift.protocol.classification_policy import load_policy, render_prompt
from .tokenizer import MODELS, plan, versions, verify_snapshot


def json_number(value):
    value = float(value)
    return value if math.isfinite(value) else ("NaN" if math.isnan(value) else "+Inf" if value > 0 else "-Inf")


def summarize_vector(values, candidate_ids, generated_token):
    """CPU reference implementation for tests; native path uses torch reductions."""
    values = list(map(float, values))
    if not values or generated_token not in range(len(values)) or any(i not in range(len(values)) for i in candidate_ids):
        raise ValueError("TOKEN_OUTSIDE_VOCABULARY")
    counts = {"nan": sum(math.isnan(x) for x in values),
              "positive_inf": sum(x == math.inf for x in values),
              "negative_inf": sum(x == -math.inf for x in values)}
    maximum = max(values)
    normalizer = (maximum + math.log(math.fsum(math.exp(x - maximum) for x in values))
                  if math.isfinite(maximum) and not counts["nan"] else maximum)
    return {"vocab_size": len(values), "candidate_values": {str(i): json_number(values[i]) for i in candidate_ids},
            "generated_value": json_number(values[generated_token]), "argmax_id": values.index(maximum),
            "argmax_value": json_number(maximum), "logsumexp": json_number(normalizer), "nonfinite": counts}


def summarize_tensor(tensor, candidate_ids, generated_token, torch):
    if len(tensor.shape) != 2 or tensor.shape[0] != 1:
        raise ValueError("BATCH1_VOCAB_LOGITS_REQUIRED")
    vector = tensor[0].double()
    size = int(vector.shape[0])
    if generated_token not in range(size) or any(i not in range(size) for i in candidate_ids):
        raise ValueError("TOKEN_OUTSIDE_VOCABULARY")
    return {"vocab_size": size,
            "candidate_values": {str(i): json_number(v) for i, v in
                                 zip(candidate_ids, vector[candidate_ids].tolist())},
            "generated_value": json_number(vector[generated_token].item()),
            "argmax_id": int(vector.argmax().item()), "argmax_value": json_number(vector.max().item()),
            "logsumexp": json_number(torch.logsumexp(vector, dim=0).item()),
            "nonfinite": {"nan": int(torch.isnan(vector).sum().item()),
                          "positive_inf": int(torch.isposinf(vector).sum().item()),
                          "negative_inf": int(torch.isneginf(vector).sum().item())}}


def capture_output(output, input_ids, candidate_ids, tokenizer, summarize):
    rows = output.sequences.tolist()
    if len(rows) != 1 or rows[0][:len(input_ids)] != list(input_ids):
        raise ValueError("NATIVE_GENERATION_PREFIX_MISMATCH")
    continuation = rows[0][len(input_ids):]
    if not continuation or len(continuation) != len(output.logits) or len(continuation) != len(output.scores):
        raise ValueError("RAW_LOGITS_AND_PROCESSED_SCORES_REQUIRED_EACH_STEP")
    return {"version": "ls1-native-raw-v1", "input_ids": list(input_ids), "continuation_ids": continuation,
            "decoded_text": tokenizer.decode(continuation, skip_special_tokens=True,
                                             clean_up_tokenization_spaces=False),
            "candidate_token_ids": list(candidate_ids),
            "steps": [{"step": i, "generated_token": token,
                       "raw": summarize(raw, candidate_ids, token),
                       "processed": summarize(processed, candidate_ids, token)}
                      for i, (token, raw, processed) in enumerate(zip(continuation, output.logits, output.scores))]}


class NativeScorer:
    """One terminal lifecycle, one loaded model, fresh native cache per call."""

    def __init__(self, model_key, snapshot, tokenizer, candidate_ids, *, repo):
        self.model_key, self.repo = model_key, repo
        self.tokenizer, self.candidate_ids = tokenizer, candidate_ids
        self.failed = False
        self.condition = load_policy(repo)["classification"][model_key]
        expected = plan(model_key, repo)["software"]
        actual = versions(expected)
        if actual != expected or platform.system() != "Linux" or platform.machine() != "x86_64":
            raise ValueError("EXACT_LINUX_RUNTIME_REQUIRED_NO_INSTALL_OR_FALLBACK")
        self.snapshot_receipt = verify_snapshot(model_key, snapshot, repo=repo)
        import torch
        from transformers import AutoProcessor
        from safeshift.runners.internvl3 import probe_hardware
        self.torch = torch
        self.hardware = probe_hardware(torch)
        kwargs = {"local_files_only": True, "trust_remote_code": False, "revision": MODELS[model_key][1]}
        if model_key == "qwen2_5":
            from safeshift.runners.qwen2_5_vl import _native_backend, Qwen2_5VLRunner
            backend = _native_backend()
            self.process_vision_info = backend.process_vision_info
            self.processor = AutoProcessor.from_pretrained(str(snapshot), min_pixels=200704, max_pixels=1003520, **kwargs)
            self.model, info = backend.model_factory.from_pretrained(
                str(snapshot), torch_dtype=torch.float16, device_map={"": "cuda:0"},
                attn_implementation="sdpa", output_loading_info=True, **kwargs)
            self.validator = lambda: (Qwen2_5VLRunner._validate_processor(self.processor),
                Qwen2_5VLRunner._validate_model(SimpleNamespace(_backend=SimpleNamespace(torch=torch)), self.model))
        else:
            from safeshift.runners.internvl3 import _native_backend, InternVL3Runner
            backend = _native_backend()  # checks exact audited HF source checksums
            self.processor = AutoProcessor.from_pretrained(str(snapshot), use_fast=True, **kwargs)
            self.model, info = backend.model_factory.from_pretrained(
                str(snapshot), torch_dtype=torch.float16, attn_implementation="sdpa",
                output_loading_info=True, use_safetensors=True, **kwargs)
            self.model.to("cuda:0")
            audit = InternVL3Runner(repo=repo)
            audit.backend, audit.resources = backend, (self.processor, self.model)
            self.validator = audit.state_audit
        if any(info.get(k) for k in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
            raise ValueError("EXACT_CHECKPOINT_WEIGHT_KEYS_REQUIRED")
        self.model.eval()
        self.validator()
        cfg = self.model.generation_config
        # Checkpoint sampling defaults are overridden by the recorded greedy
        # policy. They are not evidence that effective do_sample is true.
        if cfg.num_beams != 1 or cfg.num_return_sequences != 1:
            raise ValueError("GREEDY_BATCH1_REQUIRED")
        if cfg.cache_implementation not in (None, "dynamic"):
            raise ValueError("UNREVIEWED_GENERATION_CACHE")
        self.config = deepcopy(cfg)
        self.software = actual
        self.prompt = render_prompt(model_key, repo=repo)

    def prepare(self, image, prefix_ids):
        torch = self.torch
        messages = [{"role": "user", "content": [{"type": "image", "image": image},
                    {"type": "text", "text": self.prompt}]}]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        if self.model_key == "qwen2_5":
            images, videos = self.process_vision_info(messages)
            if len(images) != 1 or videos is not None:
                raise ValueError("ONE_STILL_IMAGE_REQUIRED")
            try:
                inputs = self.processor(text=[text], images=images, videos=None, padding=True, return_tensors="pt").to("cuda:0")
            finally:
                for item in images:
                    if item is not image:
                        item.close()
            expected_keys = {"input_ids", "attention_mask", "pixel_values", "image_grid_thw"}
            grid = inputs["image_grid_thw"].tolist()
            if len(grid) != 1 or grid[0][0] != 1 or not 256 <= grid[0][1] * grid[0][2] // 4 <= 1280:
                raise ValueError("QWEN_STILL_IMAGE_VISUAL_TOKEN_CAP")
        else:
            inputs = self.processor(text=[text], images=[image], return_tensors="pt",
                                    crop_to_patches=True, min_patches=1, max_patches=12).to("cuda:0", dtype=torch.float16)
            expected_keys = {"input_ids", "attention_mask", "pixel_values"}
            shape = list(inputs["pixel_values"].shape)
            if (len(shape) != 4 or shape[1:] != [3, 448, 448] or not 1 <= shape[0] <= 13
                    or inputs["input_ids"][0].tolist().count(151667) != 256 * shape[0]):
                raise ValueError("INTERNVL_TILE_TOKEN_MISMATCH")
        if set(inputs) != expected_keys or inputs["input_ids"].shape[0] != 1:
            raise ValueError("BATCH1_INPUT_KEYS_REQUIRED")
        if prefix_ids:
            extra = torch.tensor([prefix_ids], device="cuda:0", dtype=torch.int64)
            inputs["input_ids"] = torch.cat([inputs["input_ids"], extra], dim=1)
            inputs["attention_mask"] = torch.cat([inputs["attention_mask"], torch.ones_like(extra)], dim=1)
        if self.model_key == "internvl3" and inputs["input_ids"].shape[1] > 4096:
            raise ValueError("INTERNVL_INPUT_TOKEN_CAP")
        if any(str(v.device) != "cuda:0" for v in inputs.values()):
            raise ValueError("INPUT_DEVICE_MISMATCH")
        return inputs

    def generate(self, image, prefix_ids=()):
        if self.failed:
            raise RuntimeError("FAILED_SCORER_NO_RETRY")
        try:
            self.validator()
            if hasattr(self.model, "rope_deltas"):
                self.model.rope_deltas = None
            if hasattr(self.model, "_cache"):
                self.model._cache = None
            inputs = self.prepare(image, prefix_ids)
            config = deepcopy(self.config)
            settings = {**self.condition["decoding"], "max_new_tokens": 1 if prefix_ids else 32,
                        "do_sample": False, "num_beams": 1, "num_return_sequences": 1,
                        "return_dict_in_generate": True, "output_logits": True, "output_scores": True}
            with self.torch.inference_mode():
                output = self.model.generate(**inputs, generation_config=config, **settings)
            # Full tensors exist only during this call. Retain sufficient raw values
            # and full-vocab reductions for scoring/selection audit, not 40MB/sample.
            record = capture_output(output, inputs["input_ids"][0].tolist(), self.candidate_ids,
                self.tokenizer, lambda x, ids, token: summarize_tensor(x, ids, token, self.torch))
            record.update(generation_config=config.to_dict(), generation_kwargs=settings,
                          forced_assistant_prefix_ids=list(prefix_ids),
                          timestamp_utc=datetime.now(timezone.utc).isoformat())
            self.validator()
            return record
        except BaseException:
            self.failed = True
            raise
