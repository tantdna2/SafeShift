"""Offline fresh Qwen3 binding reconstructed from exact V4 public contracts.

No V4 grant, history, manifest or prediction is imported. Pure semantic function
bodies are kept separately with provenance. The public factory remains fenced.
"""
from copy import deepcopy
import hashlib
import math
from pathlib import Path
import time
from unittest.mock import patch

from safeshift.candidates.source import ROOT, require, snapshot_stat
from safeshift.candidates.train_inputs import discover
from safeshift.pilot.artifacts import read, safe, sha, write
from safeshift.pilot.contract import digest, PROMPT_SHA
from . import qwen_semantics as semantic

DEVICE_MAP = {"model.visual": 1, "model.language_model.embed_tokens": "cpu",
    **{f"model.language_model.layers.{i}": 0 if i < 21 else 1 for i in range(36)},
    "model.language_model.norm": 1, "model.language_model.rotary_emb": 1, "lm_head": 1}
CAPTURE = {"return_dict_in_generate": True, "output_logits": True, "output_scores": True}


def reference(repo=ROOT):
    return read(Path(repo) / "configs/fulltrain/qwen3.json")


def parser(text):
    parsed = semantic.parse_classification(text)
    return parsed.value.safety_level if parsed.success else None


def verify_transformers(module, repo=ROOT):
    require(module.__version__ == "4.57.1", "QWEN_TRANSFORMERS_VERSION")
    root = Path(module.__file__).parent
    rows = reference(repo)["transformers_sources"]
    for name, row in rows.items():
        require(sha(safe(root, name)) == row["sha256"], "QWEN_INSTALLED_SOURCE:" + name)
    return {n: r["sha256"] for n, r in rows.items()}


def verify_snapshot(snapshot, *, repo=ROOT, weights=True):
    snapshot = Path(snapshot)
    lock = reference(repo)
    require(snapshot.name == lock["model"]["revision"], "QWEN_REVISION_DIRECTORY")
    snapshot_stat(snapshot, directory=True)
    rows = lock["snapshot_files"]
    # Metadata-only admission never opens weights; full admission requires all.
    expected = {r["path"] for r in rows if weights or not r["path"].endswith(".safetensors")}
    present = set()
    for p in snapshot.iterdir():
        require(len(present) < 32, "QWEN_SNAPSHOT_MEMBER_BOUND")
        present.add(p.name)
    require(present == expected, "QWEN_EXACT_SNAPSHOT_INVENTORY")
    hashes = {}
    for row in rows:
        if row["path"] not in expected:
            continue
        p = safe(snapshot, row["path"])
        snapshot_stat(p)
        require(p.stat().st_size == row["size_bytes"], "QWEN_FILE_SIZE:" + p.name)
        expected_sha = row.get("sha256") if row["hash_algorithm"] == "git_blob_sha1" else row["expected_hash"]
        require(expected_sha and sha(p) == expected_sha, "QWEN_FILE_SHA256:" + p.name)
        hashes[p.name] = expected_sha
    if weights:
        index = read(snapshot / "model.safetensors.index.json")
        require(set(index["weight_map"].values()) == {r["path"] for r in rows if r["path"].endswith(".safetensors")},
                "QWEN_WEIGHT_INDEX_SHARDS")
    return {"model": lock["model"], "files": hashes, "weight_bytes_verified": weights,
            "deserialized_weights": False}


def checkpoint(inputs, marker_sha, repo=ROOT):
    marker = discover(Path(inputs), "fresh_checkpoint_qwen3.json")
    require(marker.stat().st_size <= 16384 and sha(marker) == marker_sha, "QWEN_CHECKPOINT_MARKER_PIN")
    lock = reference(repo)
    require(read(marker) == {"schema": "safeshift-fresh-qwen-checkpoint-v1", "model": lock["model"],
                            "inventory_sha256": digest(lock["snapshot_files"])}, "QWEN_CHECKPOINT_MARKER")
    snapshot = safe(marker.parent, "snapshot/" + lock["model"]["revision"])
    return marker, snapshot, verify_snapshot(snapshot, repo=repo)


def generation(config):
    result = deepcopy(config)
    value = result.to_dict()
    require(all(value.get(k) is None for k in ("forced_bos_token_id", "forced_eos_token_id", "forced_decoder_ids",
            "force_words_ids", "constraints")), "QWEN_NO_FORCING")
    require(value.get("num_beams", 1) == 1 and value.get("num_return_sequences", 1) == 1,
            "QWEN_GREEDY_BATCH1")
    return result


def loaded_state(model):
    import os
    require(os.environ.get("PYTORCH_ALLOC_CONF") == "expandable_segments:True"
            and os.environ.get("PYTORCH_CUDA_ALLOC_CONF") in (None, "expandable_segments:True"), "QWEN_ALLOCATOR")
    require(digest(getattr(model, "hf_device_map", None)) == digest(DEVICE_MAP), "QWEN_EXACT_DEVICE_MAP")
    require(str(model.dtype) == "torch.float16" and not getattr(model, "is_quantized", False)
            and getattr(model.config, "quantization_config", None) is None
            and model.config._attn_implementation == "sdpa", "QWEN_FP16_SDPA_NO_QUANTIZATION")


def native_setup(snapshot, repo=ROOT):
    """Processor/tokenizer only; CPU diagnostics never call from_pretrained on weights."""
    import transformers
    verify_transformers(transformers, repo)
    processor = transformers.AutoProcessor.from_pretrained(str(snapshot), local_files_only=True, trust_remote_code=False)
    tokenizer = transformers.AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True,
                                                          trust_remote_code=False, use_fast=True)
    require(type(processor).__name__ == "Qwen3VLProcessor", "QWEN_PROCESSOR_CLASS")
    t1 = semantic.probe(tokenizer)
    require(len(t1["checks"]) == 28 and semantic.probe(processor.tokenizer) == t1, "QWEN_T1_28_PROCESSOR_PARITY")
    require(len({tuple(c["token_ids"]) for c in t1["checks"]}) == 1, "QWEN_T1_ORDERED_FOUR_IDS")
    return processor, tokenizer, t1


class QwenBackend:
    def __init__(self, snapshot, *, repo=ROOT):
        import torch, transformers
        self.stage = "model_load"
        self.snapshot, self.repo = Path(snapshot), Path(repo)
        self.receipt = verify_snapshot(snapshot, repo=repo)
        self.processor, self.tokenizer, self.t1 = native_setup(snapshot, repo)
        require(sha(self.repo / "configs/pilot/classification_c1.txt") == PROMPT_SHA, "QWEN_C1")
        self.prompt = (self.repo / "configs/pilot/classification_c1.txt").read_text(encoding="utf-8")
        self.model = transformers.Qwen3VLForConditionalGeneration.from_pretrained(str(snapshot),
            local_files_only=True, trust_remote_code=False, dtype=torch.float16, device_map=deepcopy(DEVICE_MAP))
        self.model.eval()
        loaded_state(self.model)
        require(hasattr(self.model.model, "rope_deltas"), "QWEN_NATIVE_ROPE_LAYOUT")
        self.config = generation(self.model.generation_config)
        self.environment = {"model": reference(repo)["model"], "checkpoint": self.receipt,
            "source": verify_transformers(transformers, repo), "generation": self.config.to_dict(),
            "device_map": DEVICE_MAP, "prompt_sha256": PROMPT_SHA, "tokenizer_t1": self.t1}

    def generate(self, image_path, sample_dir):
        import torch
        from PIL import Image
        from tokenizers import Tokenizer
        sample = Path(sample_dir)
        self.stage = "preprocessing"
        loaded_state(self.model)
        self.model.model.rope_deltas = None
        if hasattr(self.model, "_cache"):
            self.model._cache = None
        with Image.open(image_path) as original:
            require(getattr(original, "n_frames", 1) == 1, "QWEN_STILL_IMAGE")
            original.load()
            with original.convert("RGB") as rgb:
                messages = [{"role": "user", "content": [{"type": "image", "image": rgb},
                                                          {"type": "text", "text": self.prompt}]}]
                inputs = self.processor.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                                            return_dict=True, return_tensors="pt").to(self.model.device)
        require(len(inputs["input_ids"]) == 1 and "past_key_values" not in inputs, "QWEN_INDEPENDENT_BATCH1")
        ids = inputs["input_ids"][0].tolist()
        require(ids and all(type(i) is int and i >= 0 for i in ids), "QWEN_INPUT_IDS")
        config = generation(self.config)
        kwargs = {"do_sample": False, "max_new_tokens": 32, **CAPTURE}
        write(sample / "request.json", {"input_ids": ids, "prompt": self.prompt, "tokenizer_t1": self.t1,
            "config": config.to_dict(), "kwargs": kwargs, "shapes": {n: list(v.shape) for n, v in inputs.items()}})
        processors = self.model._get_logits_processor
        stopping = self.model._get_stopping_criteria
        def observe_processors(*args, **kw):
            actual = processors(*args, **kw)
            write(sample / "processors.json", {"actual": [type(p).__module__ + "." + type(p).__name__ for p in actual]})
            require(not actual, "QWEN_EMPTY_ACTUAL_PROCESSORS")
            return actual
        def observe_stopping(*args, **kw):
            actual = stopping(*args, **kw)
            require(sorted(type(c).__name__ for c in actual) == ["EosTokenCriteria", "MaxLengthCriteria"], "QWEN_NATIVE_STOPPING")
            value = {"max_length": next(c.max_length for c in actual if type(c).__name__ == "MaxLengthCriteria"),
                     "eos_token_ids": next(c.eos_token_id.tolist() for c in actual if type(c).__name__ == "EosTokenCriteria")}
            write(sample / "stopping.json", value)
            return actual
        self.stage = "generation"
        began = time.monotonic()
        try:
            with patch.object(self.model, "_get_logits_processor", observe_processors), \
                 patch.object(self.model, "_get_stopping_criteria", observe_stopping), torch.inference_mode():
                write(sample / "native_call.json", {"invocation": 1, "max_new_tokens": 32})
                output = self.model.generate(**inputs, generation_config=config, **kwargs)
            # IDs and EVERY returned raw/processed reduction are durable BEFORE decode/parse.
            returned = output.sequences.detach().cpu().tolist()
            write(sample / "native.json", {"returned_ids": returned, "input_ids": ids,
                "raw_count": len(output.logits or ()), "processed_count": len(output.scores or ())})
            require(len(returned) == 1 and returned[0][:len(ids)] == ids, "QWEN_PREFIX")
            generated = returned[0][len(ids):]
            candidates = self.t1["checks"][0]["token_ids"]
            summaries = {"raw": [], "processed": []}
            for kind, tensors in (("raw", output.logits or ()), ("processed", output.scores or ())):
                for i, tensor in enumerate(tensors):
                    require(i < len(generated), "QWEN_ORPHAN_TENSOR")
                    summary = semantic.summarize_tensor(tensor, candidates, generated[i], torch)
                    write(sample / f"{kind}/{i:03d}.json", summary)
                    summaries[kind].append(summary)
            require(1 <= len(generated) <= 32 and len(summaries["raw"]) == len(summaries["processed"]) == len(generated),
                    "QWEN_ALL_RAW_PROCESSED_STEPS")
            self.stage = "decode"
            response = self.tokenizer.decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=False)
            trace = {"continuation_ids": generated, "decoded_text": response,
                     "steps": [{"step": i, "generated_token": token, **{k: summaries[k][i] for k in summaries}}
                               for i, token in enumerate(generated)]}
            write(sample / "trace.json", trace)
            eos = config.eos_token_id if type(config.eos_token_id) is list else [config.eos_token_id]
            cpu = Tokenizer.from_file(str(self.snapshot / "tokenizer.json"))
            require(cpu.decode(generated, skip_special_tokens=True) == response, "QWEN_INDEPENDENT_TOKENIZER_DECODE")
            mapping, alignment_error = None, None
            try:
                mapping = semantic.locate_decision(self.tokenizer, response, generated, eos)
                # Independent tokenizer implementation must reconstruct the same full candidate strings.
                from types import SimpleNamespace
                decoder = SimpleNamespace(encode=lambda s, add_special_tokens=False: cpu.encode(s, add_special_tokens=False).ids,
                    decode=lambda seq, skip_special_tokens=False, **kw: cpu.decode(seq, skip_special_tokens=skip_special_tokens))
                require(semantic.locate_decision(decoder, response, generated, eos) == mapping, "QWEN_CPU_MAPPING_PARITY")
            except (ValueError, KeyError, TypeError, IndexError) as error:
                mapping, alignment_error = None, type(error).__name__ + ": " + str(error)
            record = {"response": response, "input_ids": ids, "generated_ids": generated, "trace": trace,
                "mapping": mapping, "alignment_error": alignment_error, "eos_token_ids": eos,
                "tokenizer_t1": self.t1, "cpu_tokenizer_replay": {"status": "PASS", "mapping": mapping is not None},
                "tokenizer_file_sha256": sha(self.snapshot / "tokenizer.json"),
                "raw_nonfinite": any(any(s["nonfinite"].values()) for s in summaries["raw"]),
                "seconds": time.monotonic() - began, "logit_capture_boundary": "qwen_native_returned_raw_and_processed_v4"}
            loaded_state(self.model)
            return record
        finally:
            self.model.model.rope_deltas = None
            if hasattr(self.model, "_cache"):
                self.model._cache = None


def replay(raw, label):
    semantic.validate_trace(raw["trace"])
    require(raw["response"] == raw["trace"]["decoded_text"] and raw["generated_ids"] == raw["trace"]["continuation_ids"],
            "QWEN_TRACE_IDENTITY")
    if label is None:
        return {"status": "HNLO_UNVERIFIED", "hnlo": None, "reason": "INVALID_CLASSIFICATION"}
    mapping = raw["mapping"]
    require(mapping and mapping["generated_label"] == label and raw["cpu_tokenizer_replay"] == {"status": "PASS", "mapping": True},
            "QWEN_PROVEN_ALIGNMENT_REQUIRED")
    continuation = raw["generated_ids"]
    trimmed = continuation[:-1] if continuation[-1] in raw["eos_token_ids"] else continuation
    require(trimmed == mapping["response_ids"], "QWEN_REPLAY_TOKEN_ALIGNMENT")
    details = semantic.score_decision(raw["trace"], mapping)
    value = semantic.anomaly_log_odds(details["log_probabilities"])
    require(math.isfinite(value) and all(math.isfinite(x) for x in details["log_probabilities"]), "QWEN_NONFINITE_HNLO")
    z = details["raw_label_logits"]
    maximum = max(z)
    details["four_label_log_mass"] = (maximum - raw["trace"]["steps"][mapping["step"]]["raw"]["logsumexp"]
                                      + math.log(math.fsum(math.exp(x - maximum) for x in z)))
    return {"status": "HNLO_VALIDATED", "hnlo": value, "details": details, "replay_status": "PASS",
            "method": "UNCHANGED_V4_RAW_LOG_ODDS"}


def validate_raw(sample, raw, spec, repo=ROOT):
    from .contract import descriptor
    require(spec["configuration_sha256"] == digest(descriptor("qwen3")), "QWEN_CONFIGURATION_DRIFT")
    require(read(sample / "native_call.json") == {"invocation": 1, "max_new_tokens": 32}, "QWEN_CALL_MARKER")
    request, native = read(sample / "request.json"), read(sample / "native.json")
    require(read(sample / "trace.json") == raw["trace"] and raw["response"] == raw["trace"]["decoded_text"], "QWEN_TRACE_CUSTODY")
    require(native["returned_ids"] == [raw["input_ids"] + raw["generated_ids"]]
            and request["input_ids"] == native["input_ids"] == raw["input_ids"], "QWEN_NATIVE_IDS_CUSTODY")
    require(native["raw_count"] == native["processed_count"] == len(raw["generated_ids"]), "QWEN_COUNT_CUSTODY")
    require(request["kwargs"] == {"do_sample": False, "max_new_tokens": 32, **CAPTURE}
            and hashlib.sha256(request["prompt"].encode()).hexdigest() == PROMPT_SHA, "QWEN_CALL_CONFIG")
    config = request["config"]
    require(config.get("num_beams", 1) == config.get("num_return_sequences", 1) == 1
            and all(config.get(n) is None for n in ("forced_bos_token_id", "forced_eos_token_id", "forced_decoder_ids",
                                                    "force_words_ids", "constraints")), "QWEN_RAW_NO_FORCING")
    eos = config["eos_token_id"] if type(config["eos_token_id"]) is list else [config["eos_token_id"]]
    require(eos == raw["eos_token_ids"] and 1 <= len(raw["generated_ids"]) <= 32, "QWEN_RAW_EOS_LENGTH")
    require(read(sample / "processors.json") == {"actual": []}, "QWEN_PROCESSOR_CUSTODY")
    require(read(sample / "stopping.json") == {"max_length": len(raw["input_ids"]) + 32,
            "eos_token_ids": raw["eos_token_ids"]}, "QWEN_STOPPING_CUSTODY")
    lock = reference(repo)
    tokenizer_sha = next(r["sha256"] for r in lock["snapshot_files"] if r["path"] == "tokenizer.json")
    require(raw["tokenizer_file_sha256"] == tokenizer_sha and raw["tokenizer_t1"] == request["tokenizer_t1"], "QWEN_TOKENIZER_CUSTODY")
    require(len(raw["trace"]["steps"]) == len(raw["generated_ids"])
            and raw["trace"]["continuation_ids"] == raw["generated_ids"], "QWEN_RAW_TRACE_LENGTH")
    require(raw["logit_capture_boundary"] == "qwen_native_returned_raw_and_processed_v4", "QWEN_RAW_BOUNDARY")
    for i, row in enumerate(raw["trace"]["steps"]):
        for kind in ("raw", "processed"):
            require(read(sample / f"{kind}/{i:03d}.json") == row[kind], "QWEN_SUMMARY_CUSTODY")
    # Invalid/nonfinite evidence remains durable; replay failures are never fabricated scores.
