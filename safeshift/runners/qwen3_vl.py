"""Exact Qwen3-VL-8B native runner; offline contracts, runtime unqualified.

Use execute_call + FileRawStore to preserve the envelope before adaptation.
One runner supports sequential calls under one execution condition. No downloads
are permitted by this loader: a separately provisioned pinned local cache is needed.
"""

from copy import deepcopy
from dataclasses import dataclass
from io import BytesIO
import json
import math
import re
import warnings

from safeshift.protocol import PARSER_VERSION
from safeshift.protocol.schema import fields, parse_text, strict_json
from .contracts import (
    AdaptedOutput, GenerationFailure, LocalRunner, ModelIdentity, ParseStatus,
    Request, RunContext, SpatialKind, Task,
)
from .qwen3_placement import require_context, require_loaded_state

MODEL_ID = "Qwen/Qwen3-VL-8B-Instruct"
REVISION = "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b"
BACKEND = "qwen3_vl_transformers"
ENVELOPE_VERSION = "safeshift-qwen3-vl-raw-v1"
FAILURE_ENVELOPE_VERSION = "safeshift-qwen3-vl-failure-v1"
IDENTITY = ModelIdentity(
    MODEL_ID, REVISION,
    "configs/pre_freeze/local_model_provenance.d9.json#qwen3_vl_8b_instruct",
)
DTYPES = {"FP32": "float32", "BF16": "bfloat16", "FP16": "float16"}
DECODING_KEYS = frozenset({
    "temperature", "do_sample", "top_p", "top_k", "max_new_tokens", "repetition_penalty",
})


def _json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _observe(evidence, name, value):
    """Snapshot plain JSON native values before validation or further decoding.

    Do not coerce objects with repr/str/default hooks. Escaped JSON also preserves
    an observed string containing lone surrogates without invalid UTF-8 bytes.
    An unrepresentable observation must not erase earlier serializable evidence.
    """
    def check(item):
        if type(item) is list:
            for child in item:
                check(child)
        elif type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    raise TypeError("JSON object keys must not be coerced")
                check(child)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise TypeError("native observation is not a plain JSON value")

    try:
        check(value)
        snapshot = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
                              allow_nan=False).encode("utf-8")
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
    fragments = {key: json.dumps(value, ensure_ascii=True).encode("utf-8")
                 for key, value in metadata.items()}
    fragments.update(evidence)
    # Assemble already serialized observations independently of success metadata
    # and its serializer. No exception message or unobserved placeholders.
    return b"{" + b",".join(json.dumps(key).encode("utf-8") + b":" + fragments[key]
                            for key in sorted(fragments)) + b"}"


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


@dataclass(frozen=True)
class QwenBackend:
    """Injection boundary: factories expose from_pretrained; torch supplies dtype
    objects and inference_mode. Fakes must implement these without runtime imports.
    """

    torch: object
    processor_factory: object
    model_factory: object
    software_versions: dict


def _native_backend() -> QwenBackend:
    import torch
    import transformers
    import PIL
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    return QwenBackend(torch, AutoProcessor, Qwen3VLForConditionalGeneration, {
        "torch": torch.__version__, "transformers": transformers.__version__,
        "pillow": PIL.__version__,
    })


@dataclass(frozen=True)
class PreparedInput:
    inputs: object
    input_ids: list[int]
    condition: bytes


def _ids(value):
    if type(value) is not list or any(type(v) is not int or v < 0 for v in value):
        raise ValueError("token IDs must be nonnegative integers")
    return value


class Qwen3VLRunner(LocalRunner):
    identity = IDENTITY
    version = "qwen3-vl-runner-v2"
    partial_generation = "BLOCKING_GENERATE_NO_PARTIAL_GUARANTEE"

    def __init__(self, *, backend_factory=_native_backend):
        self._backend_factory = backend_factory
        self._backend = None
        self._condition = None
        self._resources = None

    def _key(self, context):
        if self.identity != IDENTITY:
            raise ValueError("this runner only represents the pinned Qwen checkpoint")
        return _json_bytes({
            "model_id": self.identity.model_id, "revision": self.identity.immutable_revision,
            "runner_version": self.version, "backend": BACKEND,
            "precision": context.precision, "quantization": context.quantization,
            "device": context.device, "software_versions": context.software_versions,
            "preprocessing": context.preprocessing,
            "loader": {"trust_remote_code": False, "local_files_only": True},
        })

    def _check_condition(self, context):
        key = self._key(context)
        if self._condition is not None and self._condition != key:
            raise ValueError("execution condition changed; create a new runner lifecycle")
        return key

    def initialize(self, context: RunContext):
        key = self._check_condition(context)
        if context.source_kind == "INSPECSAFE" or context.device.get("placement") == "explicit":
            require_context(context)  # Before any backend/torch import.
        if self._backend is not None:
            return
        backend = self._backend_factory()
        for name, version in backend.software_versions.items():
            if context.software_versions.get(name) != version:
                raise ValueError("record actual runtime version in RunContext: " + name)
        # Publish only after successful initialization/version checks.
        self._backend = backend
        self._condition = key

    def load(self, context: RunContext):
        self._check_condition(context)
        if self._backend is None:
            raise RuntimeError("initialize before load")
        if self._resources is not None:
            return
        if context.precision not in DTYPES or context.quantization != "NONE":
            raise ValueError("explicit FP32/BF16/FP16 and quantization NONE required")
        placement = context.device.get("placement")
        explicit = placement == "explicit" or context.source_kind == "INSPECSAFE"
        if explicit:
            require_context(context)
            placement = deepcopy(context.device["device_map"])
        elif (not isinstance(placement, str)
                or not re.fullmatch(r"cpu|cuda:\d+|auto", placement)):
            raise ValueError("explicit device placement required: cpu, cuda:N or auto")
        if context.preprocessing not in ({}, {"mode": "official_processor"}):
            raise ValueError("only pinned official processor preprocessing is implemented")
        processor = model = None
        try:
            kwargs = {"revision": REVISION, "trust_remote_code": False, "local_files_only": True}
            processor = self._backend.processor_factory.from_pretrained(MODEL_ID, **kwargs)
            model = self._backend.model_factory.from_pretrained(
                MODEL_ID, **kwargs, dtype=getattr(self._backend.torch, DTYPES[context.precision]),
                device_map=placement,
            )
            model.eval()
            if explicit:
                require_loaded_state(model)
            # Native Qwen keeps per-image RoPE deltas on its inner model.
            if not hasattr(model.model, "rope_deltas"):
                raise ValueError("unrecognized native Qwen state layout")
            self._clear_call_state(model)
            config = model.generation_config
            if (config.num_return_sequences != 1 or config.return_dict_in_generate
                    or config.output_scores or config.output_logits
                    or config.output_attentions or config.output_hidden_states
                    or config.cache_implementation not in (None, "dynamic")):
                raise ValueError("unsupported generation output/cache configuration")
            _json_bytes(config.to_dict())
            self._resources = (processor, model)
        finally:
            # Failed loads publish neither processor nor model; no exception is cached.
            processor = model = None

    @staticmethod
    def _clear_call_state(model):
        model.model.rope_deltas = None
        if hasattr(model, "_cache"):
            model._cache = None

    def _loaded(self, context):
        key = self._check_condition(context)
        if self._resources is None:
            raise RuntimeError("load before preparing/generating")
        return key, self._resources

    def prepare_input(self, request: Request, context: RunContext) -> PreparedInput:
        from PIL import Image

        key, (processor, model) = self._loaded(context)
        _decoding(context.decoding)
        if context.seed is not None:
            raise ValueError("seed application is not implemented; do not record an unapplied seed")
        # In-memory decode; no path, URL, disk copy, resizing or prompt modification.
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(request.input_bytes)) as source:
                if getattr(source, "n_frames", 1) != 1:
                    raise ValueError("one still image is required")
                source.load()
                image = source.convert("RGB")
        try:
            messages = [{"role": "user", "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": request.prompt},
            ]}]
            inputs = processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                return_dict=True, return_tensors="pt",
            ).to(model.device)
        finally:
            image.close()
        if len(inputs["input_ids"]) != 1 or "past_key_values" in inputs:
            raise ValueError("one independent input without past_key_values is required")
        ids = _ids(inputs["input_ids"][0].tolist())
        if not ids:
            raise ValueError("empty input token sequence")
        return PreparedInput(inputs, ids, key)

    def generate_raw(self, prepared: PreparedInput, context: RunContext) -> bytes:
        key, (processor, model) = self._loaded(context)
        if prepared.condition != key:
            raise ValueError("prepared input belongs to another execution condition")
        kwargs = _decoding(context.decoding)
        # Pass an isolated checkpoint config so generate cannot mutate shared defaults.
        config = deepcopy(model.generation_config)
        effective = {**config.to_dict(), **kwargs}
        _json_bytes(effective)
        self._clear_call_state(model)
        evidence = {}
        count = len(prepared.input_ids)
        stage = "GENERATE"
        try:
            with self._backend.torch.inference_mode():
                try:
                    generated = model.generate(**prepared.inputs, generation_config=config, **kwargs)
                except Exception:
                    # Blocking backend has returned no observable tokens or text.
                    raise GenerationFailure(partial_raw=None) from None
                stage = "TOKEN_OBSERVATION"
                rows = generated.tolist()
                _observe(evidence, "observed_generated_ids", rows)
            stage = "ROW_VALIDATION"
            if type(rows) is not list or len(rows) != 1:
                raise ValueError("expected one generated token sequence")
            stage = "TOKEN_VALIDATION"
            full = _ids(rows[0])
            _observe(evidence, "generated_ids_full", full)
            stage = "PREFIX_VALIDATION"
            if full[:count] != prepared.input_ids:
                raise ValueError("native generation did not retain the input prefix")
            continuation = full[count:]
            _observe(evidence, "continuation_ids", continuation)

            def decode(skip):
                texts = processor.batch_decode(
                    [deepcopy(continuation)], skip_special_tokens=skip, clean_up_tokenization_spaces=False,
                )
                _observe(evidence, "observed_parser_decode" if skip else "observed_special_decode", texts)
                if len(texts) != 1 or type(texts[0]) is not str:
                    raise ValueError("expected one decoded string")
                return texts[0]

            stage = "DECODE_SPECIAL_TOKENS"
            special_text = decode(False)
            _observe(evidence, "decoded_with_special_tokens", special_text)
            stage = "DECODE_FOR_PARSER"
            parser_text = decode(True)
            _observe(evidence, "decoded_for_parser", parser_text)
            stage = "SERIALIZATION"
            return _json_bytes({
                "schema_version": ENVELOPE_VERSION, "backend": BACKEND,
                "model_id": MODEL_ID, "model_revision": REVISION,
                "input_token_count": count, "generated_ids_full": full,
                "continuation_ids": continuation,
                "decoded_with_special_tokens": special_text, "decoded_for_parser": parser_text,
                "generation_kwargs": kwargs, "effective_generation_config": effective,
                "runtime": {"software_versions": deepcopy(self._backend.software_versions),
                            "input_device": str(model.device),
                            "device_map": {str(k): str(v) for k, v in
                                           getattr(model, "hf_device_map", {}).items()},
                            "model_dtype": str(model.dtype), "runner_version": self.version},
            })
        except Exception as exc:
            raise GenerationFailure(partial_raw=_failure_raw(evidence, count, stage, exc)) from None
        finally:
            self._clear_call_state(model)


class Qwen3VLAdapter:
    version = "qwen3-vl-adapter-v1"
    parser_version = ENVELOPE_VERSION + "/" + PARSER_VERSION

    def adapt(self, raw: bytes, task: Task) -> AdaptedOutput:
        if type(raw) is not bytes:
            raise TypeError("raw envelope must be UTF-8 bytes")
        obj = strict_json(raw.decode("utf-8"))
        fields(obj, {
            "schema_version", "backend", "model_id", "model_revision", "input_token_count",
            "generated_ids_full", "continuation_ids", "decoded_with_special_tokens",
            "decoded_for_parser", "generation_kwargs", "effective_generation_config", "runtime",
        })
        for key, expected in (("schema_version", ENVELOPE_VERSION), ("backend", BACKEND),
                              ("model_id", MODEL_ID), ("model_revision", REVISION)):
            if obj[key] != expected:
                raise ValueError("wrong raw envelope identity/version")
        full, continuation = _ids(obj["generated_ids_full"]), _ids(obj["continuation_ids"])
        count = obj["input_token_count"]
        if type(count) is not int or not 0 < count <= len(full) or full[count:] != continuation:
            raise ValueError("inconsistent continuation tokens")
        if any(type(obj[k]) is not str for k in ("decoded_with_special_tokens", "decoded_for_parser")):
            raise ValueError("decoded outputs must be strings")
        _decoding(obj["generation_kwargs"])
        if any(type(obj[k]) is not dict for k in ("effective_generation_config", "runtime")):
            raise ValueError("generation/runtime metadata must be objects")
        _json_bytes(obj)  # Also rejects overflow-to-infinity JSON numeric literals.
        if task == Task.GROUNDING:
            return AdaptedOutput(
                ParseStatus.UNSUPPORTED, spatial_kind=SpatialKind.NONE,
                native_evidence={"interface_status": "NOT_YET_QUALIFIED",
                                 "reason": "UNCERTAIN_REQUIRES_EXTERNAL_GATE"},
            )
        if task != Task.CLASSIFICATION:
            raise ValueError("unsupported task")
        parsed = parse_text(obj["decoded_for_parser"], "classification")
        return AdaptedOutput(ParseStatus.SUCCESS if parsed.success else ParseStatus.INVALID, parsed.value)
