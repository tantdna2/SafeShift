"""Experimental Qwen3/InternVL capture. Production classes remain unchanged."""

from copy import deepcopy
import hashlib
import importlib
from pathlib import Path

from safeshift.ls1.runtime import NativeScorer
from safeshift.runners.qwen3_vl import Qwen3VLRunner, MODEL_ID, REVISION, _decoding
from .hnlo_capture import persist_hf

QWEN_SOURCES = {
    "generation/utils.py": "a20024b1e82ed5361a524d238d2197be5407abc91297dd9888c57e8284d63fef",
    "generation/logits_process.py": "6481506629ff6f021157e893fc64c4e7b5b06a72072771809d679387cb54a4b1",
}
CAPTURE_FLAGS = {"return_dict_in_generate": True, "output_logits": True, "output_scores": True}


def verify_qwen_sources(transformers):
    if transformers.__version__ != "4.57.1":
        raise ValueError("TRANSFORMERS_4_57_1_REQUIRED")
    root = Path(transformers.__file__).parent
    rows = []
    for name, expected in QWEN_SOURCES.items():
        content = (root / name).read_bytes()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError("QWEN_GENERATION_SOURCE_MISMATCH")
        rows.append({"path": "transformers/" + name, "sha256": expected,
                     "size_bytes": len(content), "version": "4.57.1"})
    return rows


def installed_qwen_sources():
    return verify_qwen_sources(importlib.import_module("transformers"))


def greedy(config, kwargs):
    effective = {**config.to_dict(), **kwargs}
    if (effective.get("do_sample") is not False or effective.get("num_beams", 1) != 1
            or effective.get("num_return_sequences", 1) != 1
            or effective.get("max_new_tokens") != 32):
        raise ValueError("EXACT_GREEDY_BATCH1_MAX32_REQUIRED")
    return {**kwargs, **CAPTURE_FLAGS}


class Qwen3Diagnostic:
    """Compose an already loaded audited runner; reuse placement and prepared input.

    Native load/prepare stay on Qwen3VLRunner. Only this call enables extra output.
    The future caller verifies installed sources with verify_qwen_sources first.
    """

    def __init__(self, runner, reference_tokenizer):
        if not isinstance(runner, Qwen3VLRunner):
            raise TypeError("AUDITED_QWEN3_RUNNER_REQUIRED")
        self.runner, self.reference_tokenizer, self.used = runner, reference_tokenizer, False

    def generate(self, prepared, context, capture):
        if self.used:
            raise RuntimeError("DIAGNOSTIC_NO_RETRY")
        self.used = True
        runner = self.runner
        try:
            key, (processor, model) = runner._loaded(context)
            if (prepared.condition != key or context.source_kind != "SYNTHETIC"
                    or context.software_versions.get("transformers") != "4.57.1"
                    or capture.metadata["tokenizer_revision"] != REVISION
                    or (capture.metadata["model_id"], capture.metadata["revision"]) != (MODEL_ID, REVISION)):
                raise ValueError("QWEN_DIAGNOSTIC_IDENTITY_OR_CONDITION_MISMATCH")
            from safeshift.runners.qwen3_placement import require_context, require_loaded_state
            require_context(context)
            require_loaded_state(model)
            checked = installed_qwen_sources()
            capture.write("verified-generation-source", checked)
            supplied = {r["path"]: r["sha256"] for r in capture.metadata["sources"]}
            if any(supplied.get("transformers/" + n) != h for n, h in QWEN_SOURCES.items()):
                raise ValueError("QWEN_SOURCE_RECEIPTS_REQUIRED")
            candidate_ids = capture.runtime_t1(processor.tokenizer, self.reference_tokenizer)
            config = deepcopy(model.generation_config)
            kwargs = greedy(config, _decoding(context.decoding))
            capture.write("call", {"configuration": config.to_dict(), "kwargs": kwargs,
                "input_shapes": {k: list(v.shape) for k, v in prepared.inputs.items()},
                "device_map": model.hf_device_map, "software": runner._backend.software_versions})
            runner._clear_call_state(model)
            with runner._backend.torch.inference_mode():
                output = model.generate(**prepared.inputs, generation_config=config, **kwargs)
            record = persist_hf(output, prepared.input_ids, candidate_ids, processor.tokenizer,
                                capture, config.to_dict(), kwargs)
            require_loaded_state(model)
            return record
        except BaseException as error:
            capture.failure(error)
            raise
        finally:
            if runner._resources is not None:
                runner._clear_call_state(runner._resources[1])


class InternVL3Diagnostic:
    """Reuse NativeScorer load, prepare and audits, bypass its decode-before-return.

    Construct the scorer separately through its unchanged offline pinned loader;
    never call scorer.generate, forced prefix, calibrate or Level01 guard here.
    """

    def __init__(self, scorer):
        if not isinstance(scorer, NativeScorer) or scorer.model_key != "internvl3":
            raise TypeError("INTERNVL_NATIVE_SCORER_REQUIRED")
        self.scorer, self.used = scorer, False

    def generate(self, image, capture):
        if self.used or self.scorer.failed:
            raise RuntimeError("DIAGNOSTIC_NO_RETRY")
        self.used = True
        s = self.scorer
        try:
            from safeshift.ls1.tokenizer import MODELS
            if (capture.metadata["model_id"], capture.metadata["revision"]) != MODELS["internvl3"]:
                raise ValueError("INTERNVL_DIAGNOSTIC_IDENTITY_MISMATCH")
            if capture.metadata["tokenizer_revision"] != MODELS["internvl3"][1]:
                raise ValueError("INTERNVL_TOKENIZER_REVISION_MISMATCH")
            s.validator()
            ids = capture.runtime_t1(s.tokenizer, s.processor.tokenizer)
            if hasattr(s.model, "_cache"):
                s.model._cache = None
            inputs = s.prepare(image, ())
            config = deepcopy(s.config)
            kwargs = greedy(config, deepcopy(s.condition["decoding"]))
            capture.write("call", {"configuration": config.to_dict(), "kwargs": kwargs,
                "input_shapes": {k: list(v.shape) for k, v in inputs.items()},
                "software": s.software, "snapshot": s.snapshot_receipt})
            with s.torch.inference_mode():
                output = s.model.generate(**inputs, generation_config=config, **kwargs)
            record = persist_hf(output, inputs["input_ids"][0].tolist(), ids, s.tokenizer,
                                capture, config.to_dict(), kwargs)
            s.validator()
            return record
        except BaseException as error:
            s.failed = True
            capture.failure(error)
            raise
