"""Pinned native HF PaliGemma PREP runner. No qualified production parser."""

from copy import deepcopy
from dataclasses import dataclass
from functools import wraps
import hashlib
from io import BytesIO
import importlib.metadata
import json
from pathlib import Path
import platform
import re
from types import SimpleNamespace
import warnings

from .contracts import (AdaptedOutput, GenerationFailure, LocalRunner, ModelIdentity,
                        ParseStatus, SpatialKind, Task, ErrorCode,
                        execute_call as _execute_call)
from .paligemma_snapshot import (CACHE, MODEL_ID, REVISION, ROOT, json_bytes, load_plan,
                                network_denied, require_offline_env, sha256_file,
                                snapshot_path, verify_snapshot)
from .storage import FileRawStore

IDENTITY = ModelIdentity(MODEL_ID, REVISION,
                        "configs/pre_freeze/local_model_provenance.d9.json#paligemma_3b_mix_448")
PREPROCESSING = load_plan()["processor"]
DECODING = load_plan()["smoke"]["decoding"]


def software_versions():
    return {name: platform.python_version() if name == "python" else importlib.metadata.version(name)
            for name in load_plan()["software"]}


def _native_backend():
    # Called only after network denial and exact distribution checks.
    import torch
    import transformers
    from transformers import AutoProcessor, PaliGemmaForConditionalGeneration
    audit = json.loads((ROOT / "configs/pre_freeze/paligemma_source_api_audit.v1.json").read_text())
    source_root = Path(transformers.__file__).parent
    for name, evidence in audit["sources"].items():
        if "/src/transformers/" in evidence["url"]:
            relative = evidence["url"].split("/src/transformers/", 1)[1]
            if sha256_file(source_root / relative) != evidence["content_sha256"]:
                raise ValueError("AUDITED_TRANSFORMERS_SOURCE_MISMATCH: " + name)
    return SimpleNamespace(torch=torch, processor_factory=AutoProcessor,
                           model_factory=PaliGemmaForConditionalGeneration)


def probe_hardware(torch):
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise ValueError("EXACTLY_ONE_PROCESS_VISIBLE_GPU_REQUIRED")
    prop = torch.cuda.get_device_properties(0)
    if not re.fullmatch(r"(?:NVIDIA |Tesla )?T4", prop.name) or (prop.major, prop.minor) != (7, 5):
        raise ValueError("NVIDIA_T4_CC75_REQUIRED")
    if not 14 * 2**30 <= prop.total_memory <= 16 * 2**30:
        raise ValueError("T4_MEMORY_OUTSIDE_14_16_GIB")
    if torch.version.cuda != "12.4":
        raise ValueError("CUDA_BUILD_MISMATCH")
    return {"gpu_name": prop.name, "visible_gpu_count": 1, "compute_capability": [7, 5],
            "total_vram_bytes": prop.total_memory, "device": "cuda:0",
            "cuda_runtime": torch.version.cuda}


def exception_record(error, stage, torch=None):
    chain, seen = [], set()
    resource = False
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        resource |= torch is not None and isinstance(error, torch.cuda.OutOfMemoryError)
        chain.append({"type": type(error).__name__, "message": str(error)})
        error = error.__cause__ or error.__context__
    return {"stage": stage, "type": chain[0]["type"], "message": chain[0]["message"],
            "causes": chain[1:],
            "status": "RUNTIME_RESOURCE_FAILURE" if resource else "RUNTIME_INTERFACE_FAILURE"}


def guarded(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        if self.state in {"FAILED", "CLOSED"}:
            raise RuntimeError("LIFECYCLE_TERMINAL_NO_RETRY")
        self.stage = method.__name__.upper()
        try:
            return method(self, *args, **kwargs)
        except Exception as exc:
            self.failure = exception_record(exc, self.stage,
                                            self.backend.torch if self.backend else None)
            self.state = "FAILED"
            raise
    return wrapped


@dataclass(frozen=True)
class PreparedInput:
    inputs: object
    prefix: tuple
    condition: bytes
    call_id: str
    observation: dict


class VerifiedRawStore(FileRawStore):
    """Verify persisted bytes and provenance BEFORE execute_call dispatches adapter."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failure = None

    def preserve(self, raw, provenance):
        try:
            return self._preserve_verified(raw, provenance)
        except Exception as exc:
            self.failure = exception_record(exc, "RAW_PRESERVATION")
            raise

    def _preserve_verified(self, raw, provenance):
        ref = super().preserve(raw, provenance)
        path = self.repo / ref.path
        if path.stat().st_size != ref.size_bytes or sha256_file(path) != ref.sha256:
            raise ValueError("PERSISTED_RAW_HASH_OR_SIZE_MISMATCH")
        metadata = json.loads((path.parent / "metadata.json").read_text(encoding="utf-8"))
        if (metadata != {**provenance, "raw_output": {
                "path": ref.path, "sha256": ref.sha256, "size_bytes": ref.size_bytes}}):
            raise ValueError("PERSISTED_PROVENANCE_MISMATCH")
        return ref

    def save_result(self, result):
        try:
            return super().save_result(result)
        except Exception as exc:
            # Preserve the earlier raw failure if result saving also fails.
            self.failure = self.failure or exception_record(exc, "RESULT_PERSISTENCE")
            raise


class PendingPaliGemmaAdapter:
    version = "paligemma-pending-adapter-v1"
    parser_version = "PENDING_QUALIFICATION"

    def adapt(self, raw, task):
        if task == Task.GROUNDING:
            return AdaptedOutput(ParseStatus.UNSUPPORTED, spatial_kind=SpatialKind.NONE,
                                 native_evidence={"status": "PENDING_QUALIFICATION"})
        if task == Task.CLASSIFICATION:
            return AdaptedOutput(ParseStatus.INVALID,
                                 native_evidence={"status": "PENDING_QUALIFICATION"})
        raise ValueError("UNSUPPORTED_TASK")


class PaliGemmaRunner(LocalRunner):
    identity = IDENTITY
    version = "paligemma-runner-v1"

    def __init__(self, *, repo=ROOT, cache_dir=CACHE, backend_factory=_native_backend):
        self.repo, self.cache_dir = Path(repo), cache_dir
        self.backend_factory = backend_factory
        self.backend = self.resources = self.condition = self.failure = None
        self.network = None
        self.state = "NEW"
        self.stage = "NEW"
        self.model_load_count = self.native_generate_calls = 0
        self.audits, self.calls = [], set()
        self.snapshot = None

    def _condition(self, context):
        if self.identity != IDENTITY:
            raise ValueError("EXACT_MODEL_REVISION_REQUIRED")
        if (context.precision != "FP16" or context.quantization != "NONE"
                or context.device != {"placement": "cuda:0"}
                or json_bytes(context.preprocessing) != json_bytes(PREPROCESSING)
                or json_bytes(context.decoding) != json_bytes(DECODING)
                or context.seed is not None):
            raise ValueError("FP16_NONE_BATCH1_NO_OFFLOAD_NO_FALLBACK_CONTRACT")
        if context.software_versions != load_plan(self.repo)["software"]:
            raise ValueError("EXACT_SOFTWARE_PINS_REQUIRED")
        if context.source_kind not in {"HANDCRAFTED_RUNTIME_SMOKE", "EXTERNAL_CLASSIFICATION_QUALIFICATION"}:
            raise ValueError("PREP_ONLY_SYNTHETIC_RUNTIME_INPUT")
        key = json_bytes({"preprocessing": context.preprocessing, "decoding": context.decoding,
                          "software": context.software_versions, "run_id": context.run_id,
                          "git": context.git_commit_sha, "command": context.command})
        if self.condition is not None and key != self.condition:
            raise ValueError("LIFECYCLE_CONDITION_CHANGED")
        require_offline_env()
        return key

    @guarded
    def initialize(self, context):
        key = self._condition(context)
        if self.backend is not None:
            return
        self.network = network_denied()
        self.network.__enter__()
        self.stage = "SOFTWARE"
        if software_versions() != context.software_versions:
            raise ValueError("INSTALLED_SOFTWARE_PIN_MISMATCH")
        self.stage = "BACKEND_IMPORT"
        self.backend = self.backend_factory()
        self.stage = "HARDWARE"
        self.hardware = probe_hardware(self.backend.torch)
        self.condition = key
        self.state = "INITIALIZED"

    @guarded
    def load(self, context):
        self._condition(context)
        if self.resources is not None:
            return
        if self.state != "INITIALIZED":
            raise RuntimeError("INITIALIZE_BEFORE_LOAD")
        self.stage = "SNAPSHOT_VERIFY"
        path = snapshot_path(self.repo, self.cache_dir)
        self.snapshot = verify_snapshot(path, repo=self.repo)
        kwargs = {"revision": REVISION, "local_files_only": True, "trust_remote_code": False}
        self.stage = "PROCESSOR_LOAD"
        # v4.57.1 native default: slow SigLIP image processor + fast Gemma tokenizer.
        # Explicit use_fast=False would also select the slow SentencePiece tokenizer.
        processor = self.backend.processor_factory.from_pretrained(str(path), **kwargs)
        self.stage = "MODEL_LOAD"
        self.model_load_count += 1
        # CPU deserialization is not inference offload. No forward occurs until
        # the complete FP16 model and all registered buffers are on cuda:0.
        model, loading_info = self.backend.model_factory.from_pretrained(
            str(path), dtype=self.backend.torch.float16,
            attn_implementation="sdpa", use_safetensors=True, output_loading_info=True, **kwargs)
        self.stage = "WEIGHT_KEY_AUDIT"
        if any(loading_info.get(key) for key in
               ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
            raise ValueError("CHECKPOINT_WEIGHT_KEYS_MUST_LOAD_EXACTLY")
        self.stage = "DEVICE_TRANSFER"
        model.to("cuda:0")
        model.eval()
        self.resources = (processor, model)
        self.stage = "LOADED_STATE_AUDIT"
        self.baseline = self.state_audit()
        self.audits.append({"stage": "after_load", **self.baseline})
        self.state = "LOADED"

    def state_audit(self):
        processor, model = self.resources
        torch = self.backend.torch
        probe_hardware(torch)
        image = processor.image_processor
        if (type(processor).__name__ != "PaliGemmaProcessor"
                or type(processor.tokenizer).__name__ != "GemmaTokenizerFast"
                or type(image).__name__ != "SiglipImageProcessor"
                or processor.image_seq_length != 1024 or processor.image_token_id != 257152
                or image.size != {"height": 448, "width": 448}
                or image.image_mean != [0.5, 0.5, 0.5]
                or image.image_std != [0.5, 0.5, 0.5]
                or image.rescale_factor != 1 / 255 or int(image.resample) != 3
                or not all(getattr(image, name) is True for name in
                           ("do_resize", "do_rescale", "do_normalize"))):
            raise ValueError("PROCESSOR_CONTRACT_CHANGED")
        if (type(model).__name__ != "PaliGemmaForConditionalGeneration"
                or model.config.model_type != "paligemma"
                or model.config.image_token_index != 257152
                or model.config.vision_config.image_size != 448):
            raise ValueError("NATIVE_PALIGEMMA_MODEL_REQUIRED")
        if (model.training or model.dtype != torch.float16 or str(model.device) != "cuda:0"
                or getattr(model, "is_quantized", False)
                or getattr(model.config, "quantization_config", None) is not None):
            raise ValueError("MODEL_DTYPE_DEVICE_OR_QUANTIZATION")
        mapping = getattr(model, "hf_device_map", {})
        if type(mapping) is not dict or any(str(v) not in {"0", "cuda:0"} for v in mapping.values()):
            raise ValueError("OFFLOAD_OR_MULTI_DEVICE_FORBIDDEN")
        configs = (model.config, model.config.text_config, model.config.vision_config)
        for cfg in configs:
            if (cfg._attn_implementation != "sdpa" or getattr(cfg, "output_attentions", False)
                    or getattr(cfg, "cache_implementation", None) is not None):
                raise ValueError("ATTENTION_OR_CACHE_FALLBACK_FORBIDDEN")
        counts = {"parameters": 0, "buffers": 0}
        for kind, items in (("parameters", model.parameters()), ("buffers", model.buffers())):
            for item in items:
                counts[kind] += 1
                if str(item.device) != "cuda:0" or (kind == "parameters" and item.dtype != torch.float16):
                    raise ValueError("PARAMETER_OR_BUFFER_PLACEMENT_VIOLATION")
        if not counts["parameters"]:
            raise ValueError("NO_PARAMETERS")
        for module in model.modules():
            if getattr(getattr(module, "_hf_hook", None), "offload", False):
                raise ValueError("OFFLOAD_HOOK_FORBIDDEN")
            if any(getattr(module, name, None) is not None for name in
                   ("_cache", "past_key_values", "_past_key_values")):
                raise ValueError("PERSISTENT_GENERATION_CACHE_FORBIDDEN")
        if getattr(model.generation_config, "cache_implementation", None) is not None:
            raise ValueError("PERSISTENT_OR_OFFLOADED_CACHE_FORBIDDEN")
        return {**counts, "dtype": "FP16", "device": "cuda:0", "quantization": "NONE",
                "generation_config_sha256": hashlib.sha256(json_bytes(model.generation_config.to_dict())).hexdigest(),
                "model_config_sha256": hashlib.sha256(json_bytes(model.config.to_dict())).hexdigest(),
                "persistent_cache": False}

    def _stable(self, label):
        observation = self.state_audit()
        self.audits.append({"stage": label, **observation})
        if observation != self.baseline:
            raise ValueError("MODEL_STATE_DRIFT")

    def _observe_inputs(self, inputs):
        torch = self.backend.torch
        if set(inputs) != {"input_ids", "attention_mask", "pixel_values"}:
            raise ValueError("ONE_STILL_IMAGE_INPUT_KEYS_REQUIRED")
        ids = inputs["input_ids"].tolist()
        if (len(ids) != 1 or not ids[0] or len(ids[0]) > 4096
                or any(type(v) is not int or v < 0 for v in ids[0])):
            raise ValueError("BATCH1_TOKEN_CAP_REQUIRED")
        for name, value in inputs.items():
            expected = torch.float16 if name == "pixel_values" else torch.int64
            if str(value.device) != "cuda:0" or value.dtype != expected:
                raise ValueError("INPUT_DEVICE_DTYPE_BOUNDARY")
        shape = list(inputs["pixel_values"].shape)
        if (shape != [1, 3, 448, 448]
                or ids[0].count(257152) != 1024
                or list(inputs["attention_mask"].shape) != [1, len(ids[0])]):
            raise ValueError("IMAGE_TOKEN_EXPANSION_MISMATCH")
        return tuple(ids[0]), {"pixel_values_shape": shape, "pixel_values_dtype": "FP16",
                              "input_ids_dtype": "int64", "device": "cuda:0",
                              "image_token_count": ids[0].count(257152), "input_tokens": len(ids[0])}

    @guarded
    def prepare_input(self, request, context):
        from PIL import Image
        key = self._condition(context)
        if self.state not in {"LOADED", "GENERATED"} or context.call_id in self.calls:
            raise ValueError("INDEPENDENT_CALL_LIFECYCLE_REQUIRED")
        self._stable("before_prepare")
        processor, _ = self.resources
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(request.input_bytes)) as source:
                if getattr(source, "n_frames", 1) != 1:
                    raise ValueError("ONE_STILL_IMAGE_REQUIRED")
                source.load()
                image = source.convert("RGB")
        try:
            # Native processor owns image resize/normalization, BOS/image tokens/newline.
            # No chat template, URL loader, suffix/labels, or manual preprocessing.
            inputs = processor(text=request.prompt, images=image, return_tensors="pt")
            inputs = inputs.to("cuda:0", dtype=self.backend.torch.float16)
        finally:
            image.close()
        prefix, observation = self._observe_inputs(inputs)
        self.calls.add(context.call_id)
        self.state = "READY"
        return PreparedInput(inputs, prefix, key, context.call_id, observation)

    @guarded
    def generate_raw(self, prepared, context):
        key = self._condition(context)
        if (self.state != "READY" or prepared.condition != key
                or prepared.call_id != context.call_id
                or self._observe_inputs(prepared.inputs)[0] != prepared.prefix):
            raise ValueError("PREPARED_INPUT_OR_LIFECYCLE_CHANGED")
        self._stable("before_generate")
        processor, model = self.resources
        evidence = {"model_id": MODEL_ID, "revision": REVISION,
                    "schema_version": "paligemma-native-output-v1",
                    "input_token_ids": list(prepared.prefix), "input_boundary": prepared.observation,
                    "decoding": deepcopy(DECODING), "run_id": context.run_id, "call_id": context.call_id,
                    "hardware": deepcopy(self.hardware), "dtype": "FP16", "device": "cuda:0",
                    "quantization": "NONE", "generation_kwargs": {"logits_to_keep": 1}}
        try:
            self.stage = "NATIVE_GENERATE"
            self.native_generate_calls += 1
            with self.backend.torch.inference_mode():
                generated = model.generate(**prepared.inputs,
                                           generation_config=deepcopy(model.generation_config),
                                           logits_to_keep=1, **DECODING)
            self.stage = "NATIVE_TOKEN_SERIALIZATION"
            rows = generated.tolist()
            evidence["generated_ids_full"] = rows
            # Capture all native IDs before validation/decode; failures preserve them.
            json_bytes(evidence)
            if (len(rows) != 1 or any(type(v) is not int or v < 0 for v in rows[0])
                    or tuple(rows[0][:len(prepared.prefix)]) != prepared.prefix
                    or not 1 <= len(rows[0]) - len(prepared.prefix) <= 32):
                raise ValueError("NATIVE_GENERATION_OUTPUT_CONTRACT")
            continuation = rows[0][len(prepared.prefix):]
            evidence["continuation_ids"] = continuation
            self.stage = "NATIVE_DECODE"
            for skip, name in ((False, "decoded_with_special_tokens"), (True, "decoded_text")):
                evidence[name] = processor.decode(continuation, skip_special_tokens=skip,
                                                  clean_up_tokenization_spaces=False)
                if type(evidence[name]) is not str:
                    raise ValueError("NATIVE_DECODE_NOT_TEXT")
            self.stage = "POST_GENERATION_STATE_AUDIT"
            self._stable("after_generate")
            self.state = "GENERATED"
            return json_bytes(evidence)
        except Exception as exc:
            partial = json_bytes(evidence) if "generated_ids_full" in evidence else None
            raise GenerationFailure(partial_raw=partial) from exc

    def close(self):
        self.resources = self.backend = None
        if self.network is not None:
            self.network.__exit__(None, None, None)
            self.network = None
        self.state = "CLOSED"


def loc_values_to_d4(values):
    """D9R7 integer mapping only; NOT an output grammar parser/qualified adapter."""
    if (type(values) not in (tuple, list) or len(values) != 4
            or any(type(v) is not int or not 0 <= v <= 1023 for v in values)):
        raise ValueError("PARSER_FAIL_NO_REPAIR")
    y_min, x_min, y_max, x_max = values
    if y_min >= y_max or x_min >= x_max:
        raise ValueError("PARSER_FAIL_NO_REPAIR")
    return [x_min / 1024.0, y_min / 1024.0, x_max / 1024.0, y_max / 1024.0]


def execute_call(runner, adapter, store, request, context):
    """Use verified storage; persistence/parser failures terminate this lifecycle."""
    if not isinstance(store, VerifiedRawStore):
        raise TypeError("VERIFIED_RAW_STORE_REQUIRED")
    if runner.state in {"FAILED", "CLOSED"}:
        raise RuntimeError("LIFECYCLE_TERMINAL_NO_RETRY")
    try:
        result = _execute_call(runner, adapter, store, request, context)
        if result.error and result.error.code not in {
                ErrorCode.INVALID_CLASSIFICATION, ErrorCode.UNSUPPORTED_GROUNDING}:
            runner.state = "FAILED"
            runner.failure = runner.failure or store.failure or {
                "stage": result.error.stage, "type": result.error.exception_type,
                "message": result.error.code.value, "causes": [],
                "status": "RUNTIME_INTERFACE_FAILURE"}
        return result
    except Exception as exc:
        runner.state = "FAILED"
        runner.failure = runner.failure or exception_record(exc, "EXECUTE_CALL")
        raise
