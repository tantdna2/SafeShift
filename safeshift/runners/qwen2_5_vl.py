"""Pinned Qwen2.5-VL-3B offline implementation; real T4 runtime unqualified.

Use execute_call/FileRawStore for persistence before adaptation. Native libraries
are lazy and the backend is injectable. No provisioning or fallback is implemented.
Reviewed native state layout and source citations: notes/w2_qwen2_5_runner_implementation.md.
"""

from copy import deepcopy
from dataclasses import dataclass
from io import BytesIO
import json
import math
import warnings

from safeshift.protocol import PARSER_VERSION
from safeshift.protocol.schema import fields, parse_text, strict_json
from .contracts import (
    AdaptedOutput, GenerationFailure, LocalRunner, ModelIdentity, ParseStatus,
    Request, RunContext, SpatialKind, Task,
)

MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
REVISION = "66285546d2b821cf421d4f5eb2576359d3770cd3"
BACKEND = "qwen2_5_vl_transformers"
ENVELOPE_VERSION = "safeshift-qwen2-5-vl-raw-v1"
FAILURE_ENVELOPE_VERSION = "safeshift-qwen2-5-vl-failure-v1"
IDENTITY = ModelIdentity(
    MODEL_ID, REVISION,
    "configs/pre_freeze/local_model_provenance.d9.json#qwen2_5_vl_3b_instruct",
)
DECODING_KEYS = frozenset({
    "temperature", "do_sample", "top_p", "top_k", "max_new_tokens", "repetition_penalty",
})
INPUT_KEYS = frozenset({"input_ids", "attention_mask", "pixel_values", "image_grid_thw"})
REQUIRED_SOFTWARE = frozenset({"torch", "transformers", "pillow", "qwen-vl-utils", "accelerate"})


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _observe(evidence, name, value):
    """Retain observable plain values before validation; never repr runtime objects."""
    def check(item):
        if type(item) is list:
            for child in item:
                check(child)
        elif type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    raise TypeError("non-string JSON key")
                check(child)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise TypeError("not a plain JSON observation")
    try:
        check(value)
        snapshot = json.dumps(value, ensure_ascii=True, sort_keys=True,
                              separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError):
        return
    evidence[name] = snapshot


def _failure_raw(evidence, count, stage, error):
    if not evidence:
        return None
    metadata = {
        "schema_version": FAILURE_ENVELOPE_VERSION, "backend": BACKEND,
        "model_id": MODEL_ID, "model_revision": REVISION,
        "generation_observation_status": "RETURNED_NATIVE_OUTPUT",
        "input_token_count": count, "post_generation_stage": stage,
        "post_generation_error_type": type(error).__name__,
    }
    fragments = {k: json.dumps(v, ensure_ascii=True).encode("utf-8") for k, v in metadata.items()}
    fragments.update(evidence)
    return b"{" + b",".join(json.dumps(k).encode("utf-8") + b":" + fragments[k]
                            for k in sorted(fragments)) + b"}"


def _decoding(values):
    if type(values) is not dict or values.keys() - DECODING_KEYS:
        raise ValueError("unsupported decoding keys")
    for key, value in values.items():
        if key == "do_sample":
            valid = type(value) is bool
        elif key in {"top_k", "max_new_tokens"}:
            valid = type(value) is int and value >= (0 if key == "top_k" else 1)
        else:
            valid = type(value) in (int, float) and math.isfinite(value) and value > 0
            if key == "top_p":
                valid = valid and value <= 1
        if not valid:
            raise ValueError("invalid decoding value: " + key)
    return deepcopy(values)


def _ids(value):
    if type(value) is not list or any(type(v) is not int or v < 0 for v in value):
        raise ValueError("token IDs must be nonnegative integers")
    return value


@dataclass(frozen=True)
class Qwen2_5Backend:
    torch: object
    processor_factory: object
    model_factory: object
    process_vision_info: object
    software_versions: dict


def _native_backend():
    from importlib.metadata import version
    import torch
    import transformers
    import PIL
    import accelerate
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
    from qwen_vl_utils import process_vision_info

    return Qwen2_5Backend(torch, AutoProcessor, Qwen2_5_VLForConditionalGeneration,
                         process_vision_info, {
                             "torch": torch.__version__, "transformers": transformers.__version__,
                             "pillow": PIL.__version__, "accelerate": accelerate.__version__,
                             "qwen-vl-utils": version("qwen-vl-utils"),
                         })


@dataclass(frozen=True)
class PreparedInput:
    inputs: object
    input_ids: tuple[int, ...]
    condition: bytes


class Qwen2_5VLRunner(LocalRunner):
    identity = IDENTITY
    version = "qwen2-5-vl-runner-v1"
    partial_generation = "BLOCKING_GENERATE_NO_PARTIAL_GUARANTEE"
    persistent_call_state = "RESET_TOP_LEVEL_ROPE_DELTAS_AND_NATIVE_CACHE_PER_CALL"

    def __init__(self, *, backend_factory=_native_backend):
        self._backend_factory = backend_factory
        self._backend = None
        self._condition = None
        self._resources = None

    def _key(self, context):
        if self.identity != IDENTITY:
            raise ValueError("only the exact pinned Qwen2.5 checkpoint is supported")
        if context.precision != "FP16" or context.quantization != "NONE":
            raise ValueError("FP16 candidate and quantization NONE required; no fallback")
        if context.device != {"placement": "cuda:0"}:
            raise ValueError("only explicit single-device cuda:0; no auto/offload")
        if context.preprocessing not in ({}, {"mode": "official_processor"}):
            raise ValueError("only official processor defaults are supported")
        if context.seed is not None:
            raise ValueError("seed is not applied by this runner")
        decoding = _decoding(context.decoding)
        return _json_bytes({
            "model_id": MODEL_ID, "revision": REVISION, "runner_version": self.version,
            "precision": context.precision, "quantization": context.quantization,
            "device": context.device, "software_versions": context.software_versions,
            "preprocessing": context.preprocessing, "decoding": decoding,
            "loader": {"local_files_only": True, "trust_remote_code": False,
                       "attn_implementation": "eager", "device_map": {"": "cuda:0"}},
        })

    def _check_condition(self, context):
        key = self._key(context)
        if self._condition is not None and key != self._condition:
            raise ValueError("execution condition changed; create a new runner lifecycle")
        return key

    def initialize(self, context: RunContext):
        key = self._check_condition(context)
        if self._backend is not None:
            return
        backend = self._backend_factory()
        versions = deepcopy(backend.software_versions)
        if not REQUIRED_SOFTWARE <= versions.keys():
            raise ValueError("backend software metadata is incomplete")
        for name, version in versions.items():
            if type(version) is not str or not version or context.software_versions.get(name) != version:
                raise ValueError("record actual runtime version in RunContext: " + name)
        self._backend = Qwen2_5Backend(backend.torch, backend.processor_factory, backend.model_factory,
                                      backend.process_vision_info, versions)
        self._condition = key

    def _validate_model(self, model):
        if str(model.device) != "cuda:0" or model.dtype != self._backend.torch.float16:
            raise ValueError("model must reside on cuda:0 with FP16 parameters")
        if getattr(model, "is_quantized", False) or getattr(model.config, "quantization_config", None) is not None:
            raise ValueError("quantized model is not supported")
        device_map = getattr(model, "hf_device_map", {})
        if type(device_map) is not dict or any(str(v) not in {"cuda:0", "0"} for v in device_map.values()):
            raise ValueError("offloaded or multi-device model is forbidden")
        for parameter in model.parameters():
            if str(parameter.device) != "cuda:0" or parameter.dtype != self._backend.torch.float16:
                raise ValueError("parameter device/dtype violates FP16 single-device policy")
        for buffer in model.buffers():
            if str(buffer.device) != "cuda:0":
                raise ValueError("buffer offload is forbidden")
        # Reviewed Qwen2.5 layout, NOT Qwen3's model.model.rope_deltas.
        if not hasattr(model, "rope_deltas") or hasattr(model.model, "rope_deltas"):
            raise ValueError("unreviewed Qwen2.5 native state layout")
        if getattr(model.config, "cache_implementation", None) not in (None, "dynamic"):
            raise ValueError("unsupported model-level generation cache")

    @staticmethod
    def _validate_config(config):
        if (config.num_return_sequences != 1 or config.num_beams != 1
                or config.return_dict_in_generate or config.output_scores or config.output_logits
                or config.output_attentions or config.output_hidden_states
                or config.cache_implementation not in (None, "dynamic")):
            raise ValueError("unsupported generation output/cache configuration")
        _json_bytes(config.to_dict())

    @staticmethod
    def _clear_call_state(model):
        model.rope_deltas = None
        if hasattr(model, "_cache"):
            model._cache = None

    def load(self, context: RunContext):
        self._check_condition(context)
        if self._backend is None:
            raise RuntimeError("initialize before load")
        if self._resources is not None:
            return
        processor = model = None
        try:
            kwargs = dict(revision=REVISION, local_files_only=True, trust_remote_code=False)
            processor = self._backend.processor_factory.from_pretrained(MODEL_ID, **kwargs)
            model = self._backend.model_factory.from_pretrained(
                MODEL_ID, **kwargs, torch_dtype=self._backend.torch.float16,
                device_map={"": "cuda:0"}, attn_implementation="eager",
            )
            model.eval()
            self._validate_model(model)
            self._validate_config(model.generation_config)
            config = deepcopy(model.generation_config)
            self._clear_call_state(model)
            self._resources = (processor, model, config)
        finally:
            # All resources stay unpublished until the entire load validates.
            processor = model = None

    def _loaded(self, context):
        key = self._check_condition(context)
        if self._resources is None:
            raise RuntimeError("load before preparing/generating")
        return key, self._resources

    @staticmethod
    def _input_ids(inputs):
        if set(inputs) != INPUT_KEYS:
            raise ValueError("only one independent still-image processor input is allowed")
        rows = inputs["input_ids"].tolist()
        if type(rows) is not list or len(rows) != 1 or not _ids(rows[0]):
            raise ValueError("expected one nonempty input token row")
        grid = inputs["image_grid_thw"].tolist()
        if (type(grid) is not list or len(grid) != 1 or type(grid[0]) is not list
                or len(grid[0]) != 3 or any(type(v) is not int or v < 1 for v in grid[0])
                or grid[0][0] != 1):
            raise ValueError("expected one still-image grid")
        for tensor in inputs.values():
            if str(tensor.device) != "cuda:0":
                raise ValueError("all inputs must reside on cuda:0")
        return tuple(rows[0])

    def prepare_input(self, request: Request, context: RunContext) -> PreparedInput:
        from PIL import Image

        key, (processor, model, _) = self._loaded(context)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(request.input_bytes)) as source:
                if getattr(source, "n_frames", 1) != 1:
                    raise ValueError("exactly one still image is required")
                source.load()
                image = source.convert("RGB")
        vision_images = None
        try:
            messages = [{"role": "user", "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": request.prompt},
            ]}]
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            if type(text) is not str:
                raise ValueError("official chat template must return text")
            vision_images, videos = self._backend.process_vision_info(messages)
            if (type(vision_images) is not list or len(vision_images) != 1 or videos is not None
                    or not isinstance(vision_images[0], Image.Image)
                    or getattr(vision_images[0], "n_frames", 1) != 1):
                raise ValueError("vision utility must produce one PIL image and no video")
            inputs = processor(text=[text], images=vision_images, videos=videos,
                               padding=True, return_tensors="pt").to(model.device)
        finally:
            image.close()
            if type(vision_images) is list:
                for item in vision_images:
                    if isinstance(item, Image.Image) and item is not image:
                        item.close()
        return PreparedInput(inputs, self._input_ids(inputs), key)

    def generate_raw(self, prepared: PreparedInput, context: RunContext) -> bytes:
        key, (processor, model, checkpoint_config) = self._loaded(context)
        if prepared.condition != key or self._input_ids(prepared.inputs) != prepared.input_ids:
            raise ValueError("prepared input condition or token prefix changed")
        self._validate_model(model)
        kwargs = _decoding(context.decoding)
        config = deepcopy(checkpoint_config)
        self._validate_config(config)
        effective = {**deepcopy(config.to_dict()), **kwargs}
        _json_bytes(effective)
        self._clear_call_state(model)
        evidence = {}
        count = len(prepared.input_ids)
        stage = "GENERATE"
        try:
            with self._backend.torch.inference_mode():
                generated = model.generate(**prepared.inputs, generation_config=config, **kwargs)
                stage = "TOKEN_OBSERVATION"
                rows = generated.tolist()
                _observe(evidence, "observed_generated_ids", rows)
            stage = "ROW_VALIDATION"
            if type(rows) is not list or len(rows) != 1:
                raise ValueError("expected exactly one generated row")
            stage = "TOKEN_VALIDATION"
            full = _ids(rows[0])
            _observe(evidence, "generated_ids_full", full)
            stage = "PREFIX_VALIDATION"
            if tuple(full[:count]) != prepared.input_ids:
                raise ValueError("generated sequence must retain the full input prefix")
            continuation = full[count:]
            _observe(evidence, "continuation_ids", continuation)

            def decode(skip):
                texts = processor.batch_decode([deepcopy(continuation)], skip_special_tokens=skip,
                                               clean_up_tokenization_spaces=False)
                _observe(evidence, "observed_parser_decode" if skip else "observed_special_decode", texts)
                if type(texts) is not list or len(texts) != 1 or type(texts[0]) is not str:
                    raise ValueError("expected exactly one decoded string")
                return texts[0]

            stage = "DECODE_SPECIAL_TOKENS"
            special = decode(False)
            _observe(evidence, "decoded_with_special_tokens", special)
            stage = "DECODE_FOR_PARSER"
            parsed_text = decode(True)
            _observe(evidence, "decoded_for_parser", parsed_text)
            stage = "SERIALIZATION"
            return _json_bytes({
                "schema_version": ENVELOPE_VERSION, "backend": BACKEND,
                "model_id": MODEL_ID, "model_revision": REVISION,
                "input_token_count": count, "input_token_ids": list(prepared.input_ids),
                "generated_ids_full": full, "continuation_ids": continuation,
                "decoded_with_special_tokens": special, "decoded_for_parser": parsed_text,
                "generation_kwargs": kwargs, "effective_generation_config": effective,
                "runtime": {
                    "software_versions": deepcopy(self._backend.software_versions),
                    "model_dtype": str(model.dtype), "model_device": str(model.device),
                    "input_device": str(prepared.inputs["input_ids"].device),
                    "device_map": {str(k): str(v) for k, v in getattr(model, "hf_device_map", {}).items()},
                    "runner_version": self.version, "attn_implementation": "eager",
                    "generation_config_scope": "CHECKPOINT_SNAPSHOT_PLUS_CALLER_KWARGS_BEFORE_DISPATCH",
                },
            })
        except Exception as exc:
            raise GenerationFailure(partial_raw=_failure_raw(evidence, count, stage, exc)) from None
        finally:
            self._clear_call_state(model)


class Qwen2_5VLAdapter:
    version = "qwen2-5-vl-adapter-v1"
    parser_version = ENVELOPE_VERSION + "/" + PARSER_VERSION

    def adapt(self, raw: bytes, task: Task) -> AdaptedOutput:
        if type(raw) is not bytes:
            raise TypeError("raw envelope must be strict UTF-8 JSON bytes")
        obj = strict_json(raw.decode("utf-8"))
        fields(obj, {
            "schema_version", "backend", "model_id", "model_revision", "input_token_count",
            "input_token_ids", "generated_ids_full", "continuation_ids", "decoded_with_special_tokens",
            "decoded_for_parser", "generation_kwargs", "effective_generation_config", "runtime",
        })
        for key, value in (("schema_version", ENVELOPE_VERSION), ("backend", BACKEND),
                           ("model_id", MODEL_ID), ("model_revision", REVISION)):
            if obj[key] != value:
                raise ValueError("wrong envelope identity or version")
        prefix, full, continuation = [_ids(obj[k]) for k in
                                      ("input_token_ids", "generated_ids_full", "continuation_ids")]
        count = obj["input_token_count"]
        if (type(count) is not int or count < 1 or count != len(prefix)
                or full[:count] != prefix or full[count:] != continuation):
            raise ValueError("inconsistent prefix/continuation evidence")
        if any(type(obj[k]) is not str for k in ("decoded_with_special_tokens", "decoded_for_parser")):
            raise ValueError("decoded outputs must be strings")
        kwargs = _decoding(obj["generation_kwargs"])
        effective = obj["effective_generation_config"]
        if type(effective) is not dict or any(effective.get(k) != v for k, v in kwargs.items()):
            raise ValueError("inconsistent generation metadata")
        runtime = obj["runtime"]
        fields(runtime, {"software_versions", "model_dtype", "model_device", "input_device", "device_map",
                         "runner_version", "attn_implementation", "generation_config_scope"})
        versions = runtime["software_versions"]
        if (type(versions) is not dict or not REQUIRED_SOFTWARE <= versions.keys()
                or any(type(v) is not str or not v for v in versions.values())
                or runtime["runner_version"] != Qwen2_5VLRunner.version
                or runtime["model_dtype"] != "torch.float16"
                or runtime["model_device"] != "cuda:0" or runtime["input_device"] != "cuda:0"
                or runtime["attn_implementation"] != "eager"
                or runtime["generation_config_scope"] != "CHECKPOINT_SNAPSHOT_PLUS_CALLER_KWARGS_BEFORE_DISPATCH"
                or type(runtime["device_map"]) is not dict
                or any(v not in ("cuda:0", "0") for v in runtime["device_map"].values())):
            raise ValueError("invalid runtime metadata")
        _json_bytes(obj)
        if task == Task.GROUNDING:
            return AdaptedOutput(ParseStatus.UNSUPPORTED, spatial_kind=SpatialKind.NONE,
                                 native_evidence={
                                     "interface_status": "DOCUMENTED_BOX_AND_POINT_PENDING_SYNTHETIC_GATE",
                                     "d5_box_qualification": "NOT_YET_QUALIFIED",
                                     "reason": "COORDINATE_OUTPUT_ADAPTER_NOT_YET_FROZEN",
                                 })
        if task != Task.CLASSIFICATION:
            raise ValueError("unsupported task")
        parsed = parse_text(obj["decoded_for_parser"], "classification")
        return AdaptedOutput(ParseStatus.SUCCESS if parsed.success else ParseStatus.INVALID, parsed.value)
