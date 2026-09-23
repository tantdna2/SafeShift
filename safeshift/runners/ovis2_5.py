"""Pinned Ovis2.5-9B offline runner. Use execute_call to persist before adapting.

Importing this module never imports an ML runtime or loads remote code. The native
loader requires an already provisioned local cache at the exact immutable revision.
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

MODEL_ID = "AIDC-AI/Ovis2.5-9B"
RESOLVED_REPOSITORY_ID = "ATH-MaaS/Ovis2.5-9B"
REVISION = "d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd"
BACKEND = "ovis2_5_transformers_custom"
ENVELOPE_VERSION = "safeshift-ovis2-5-raw-v1"
FAILURE_ENVELOPE_VERSION = "safeshift-ovis2-5-failure-v1"
IDENTITY = ModelIdentity(
    MODEL_ID, REVISION,
    "configs/pre_freeze/local_model_provenance.d9.json#ovis2_5_9b",
)
MIN_PIXELS = 448 * 448
MAX_PIXELS = 1792 * 1792
DECODING_KEYS = frozenset({
    "temperature", "do_sample", "top_p", "top_k", "max_new_tokens",
    "repetition_penalty", "enable_thinking", "enable_thinking_budget",
    "thinking_budget",
})


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _observe(evidence, key, value):
    """Keep only JSON-representable observations, without coercing native values."""
    def check(item):
        if type(item) is list:
            for child in item:
                check(child)
        elif type(item) is dict:
            for name, child in item.items():
                if type(name) is not str:
                    raise TypeError("non-string evidence key")
                check(child)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise TypeError("non-JSON native evidence")

    try:
        check(value)
        evidence[key] = json.dumps(value, ensure_ascii=True, sort_keys=True,
                                   separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError):
        pass


def _failure_raw(evidence, stage, error):
    if not evidence:
        return None
    metadata = {
        "schema_version": FAILURE_ENVELOPE_VERSION,
        "backend": BACKEND, "model_id": MODEL_ID,
        "resolved_repository_id": RESOLVED_REPOSITORY_ID,
        "model_revision": REVISION,
        "generation_observation_status": "RETURNED_NATIVE_OUTPUT",
        "post_generation_stage": stage,
        "post_generation_error_type": type(error).__name__,
    }
    fragments = {key: json.dumps(value, ensure_ascii=True).encode("utf-8")
                 for key, value in metadata.items()}
    fragments.update(evidence)
    return b"{" + b",".join(json.dumps(key).encode("utf-8") + b":" + fragments[key]
                            for key in sorted(fragments)) + b"}"


def _ids(value):
    if type(value) is not list or any(type(v) is not int or v < 0 for v in value):
        raise ValueError("token IDs must be nonnegative integers")
    return value


def _decoding(values):
    if type(values) is not dict or values.keys() - DECODING_KEYS:
        raise ValueError("unsupported decoding keys")
    if type(values.get("enable_thinking")) is not bool or type(values.get("enable_thinking_budget")) is not bool:
        raise ValueError("thinking conditions must be explicit booleans")
    if type(values.get("max_new_tokens")) is not int or values["max_new_tokens"] < 1:
        raise ValueError("max_new_tokens must be a positive integer")
    for key, value in values.items():
        if key in {"enable_thinking", "enable_thinking_budget", "do_sample"}:
            valid = type(value) is bool
        elif key in {"top_k", "max_new_tokens", "thinking_budget"}:
            valid = type(value) is int and value >= (0 if key == "top_k" else 1)
        else:
            valid = type(value) in (int, float) and math.isfinite(value) and value > 0
            if key == "top_p":
                valid = valid and value <= 1
        if not valid:
            raise ValueError("invalid decoding value: " + key)
    if values["enable_thinking_budget"]:
        if not values["enable_thinking"] or "thinking_budget" not in values:
            raise ValueError("thinking budget requires enabled thinking and an explicit budget")
        if values["max_new_tokens"] <= values["thinking_budget"] + 25:
            raise ValueError("max_new_tokens must exceed thinking_budget + 25")
    elif "thinking_budget" in values:
        raise ValueError("unused thinking_budget is not permitted")
    return deepcopy(values)


def _preprocessing(values):
    if values not in ({}, {"mode": "official_preprocess_inputs"},
                      {"mode": "official_preprocess_inputs", "min_pixels": MIN_PIXELS,
                       "max_pixels": MAX_PIXELS}):
        raise ValueError("only pinned official Ovis preprocessing defaults are supported")
    return {"mode": "official_preprocess_inputs", "min_pixels": MIN_PIXELS,
            "max_pixels": MAX_PIXELS, "color_mode": "RGB"}


@dataclass(frozen=True)
class OvisBackend:
    torch: object
    model_factory: object
    software_versions: dict


def _native_backend():
    import torch
    import transformers
    import PIL
    from transformers import AutoModelForCausalLM

    return OvisBackend(torch, AutoModelForCausalLM, {
        "torch": torch.__version__, "transformers": transformers.__version__,
        "pillow": PIL.__version__,
    })


@dataclass(frozen=True)
class PreparedInput:
    input_ids_tensor: object
    pixel_values: object
    grid_thws: object
    input_ids: list[int]
    condition: bytes


class Ovis2_5Runner(LocalRunner):
    identity = IDENTITY
    version = "ovis2-5-runner-v1"
    partial_generation = "BLOCKING_GENERATE_NO_PARTIAL_GUARANTEE"
    persistent_call_state = "NO_DOCUMENTED_PERSISTENT_CALL_STATE"

    def __init__(self, *, backend_factory=_native_backend):
        self._backend_factory = backend_factory
        self._backend = None
        self._condition = None
        self._model = None

    def _key(self, context):
        if self.identity != IDENTITY:
            raise ValueError("this runner only represents the pinned Ovis checkpoint")
        return _json_bytes({
            "model_id": MODEL_ID, "resolved_repository_id": RESOLVED_REPOSITORY_ID,
            "revision": REVISION, "runner_version": self.version, "backend": BACKEND,
            "precision": context.precision, "quantization": context.quantization,
            "device": context.device, "software_versions": context.software_versions,
            "preprocessing": context.preprocessing,
            "thinking_condition": {k: context.decoding.get(k) for k in
                                   ("enable_thinking", "enable_thinking_budget", "thinking_budget")},
            "loader": {"trust_remote_code": True, "local_files_only": True},
        })

    def _check_condition(self, context):
        key = self._key(context)
        if self._condition is not None and self._condition != key:
            raise ValueError("execution condition changed; create a new runner lifecycle")
        return key

    def initialize(self, context: RunContext):
        key = self._check_condition(context)
        if self._backend is not None:
            return
        backend = self._backend_factory()
        for name, version in backend.software_versions.items():
            if context.software_versions.get(name) != version:
                raise ValueError("record actual runtime version in RunContext: " + name)
        self._backend = backend
        self._condition = key

    def load(self, context: RunContext):
        self._check_condition(context)
        if self._backend is None:
            raise RuntimeError("initialize before load")
        if self._model is not None:
            return
        if context.precision != "BF16" or context.quantization != "NONE":
            raise ValueError("only documentary BF16 and quantization NONE are supported")
        if context.device != {"placement": "cuda:0"}:
            raise ValueError("only explicit single-device cuda:0 is implemented")
        _preprocessing(context.preprocessing)
        _decoding(context.decoding)
        model = self._backend.model_factory.from_pretrained(
            MODEL_ID, revision=REVISION, trust_remote_code=True,
            local_files_only=True, torch_dtype=self._backend.torch.bfloat16,
        )
        try:
            if not callable(getattr(model, "preprocess_inputs", None)) or not callable(getattr(model, "generate", None)):
                raise ValueError("Ovis custom model interface unavailable")
            if not callable(getattr(getattr(model, "text_tokenizer", None), "decode", None)):
                raise ValueError("Ovis text tokenizer interface unavailable")
            model = model.cuda()
            model.eval()
            self._model = model
        finally:
            # A failure never publishes a partially initialized resource.
            model = None

    def _loaded(self, context):
        key = self._check_condition(context)
        if self._model is None:
            raise RuntimeError("load before preparing/generating")
        return key, self._model

    def prepare_input(self, request: Request, context: RunContext) -> PreparedInput:
        from PIL import Image

        key, model = self._loaded(context)
        decoding = _decoding(context.decoding)
        if context.seed is not None:
            raise ValueError("seed application is not implemented")
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
            input_ids, pixel_values, grid_thws = model.preprocess_inputs(
                messages=messages, min_pixels=MIN_PIXELS, max_pixels=MAX_PIXELS,
                add_generation_prompt=True,
                enable_thinking=decoding["enable_thinking"],
            )
        finally:
            image.close()
        if len(input_ids) != 1:
            raise ValueError("expected one input token row")
        ids = _ids(input_ids[0].tolist())
        if not ids:
            raise ValueError("empty input token sequence")
        return PreparedInput(input_ids.cuda(), pixel_values.cuda() if pixel_values is not None else None,
                             grid_thws.cuda() if grid_thws is not None else None, ids, key)

    def generate_raw(self, prepared: PreparedInput, context: RunContext) -> bytes:
        key, model = self._loaded(context)
        if prepared.condition != key:
            raise ValueError("prepared input belongs to another execution condition")
        kwargs = _decoding(context.decoding)
        native_config = getattr(getattr(model, "llm", None), "generation_config", None)
        if native_config is None or not callable(getattr(native_config, "to_dict", None)):
            raise ValueError("native LLM generation defaults must be inspectable")
        generation_defaults = deepcopy(native_config.to_dict())
        _json_bytes(generation_defaults)
        evidence = {}
        stage = "GENERATE"
        try:
            with self._backend.torch.inference_mode():
                try:
                    generated = model.generate(
                        inputs=prepared.input_ids_tensor,
                        pixel_values=prepared.pixel_values, grid_thws=prepared.grid_thws,
                        **kwargs,
                    )
                except Exception:
                    raise GenerationFailure(partial_raw=None) from None
                stage = "TOKEN_OBSERVATION"
                rows = generated.tolist()
                _observe(evidence, "observed_native_generated_ids", rows)
            stage = "ROW_VALIDATION"
            if type(rows) is not list or len(rows) != 1:
                raise ValueError("expected one native generated token row")
            stage = "TOKEN_VALIDATION"
            ids = _ids(rows[0])
            _observe(evidence, "native_generated_ids", ids)
            stage = "DECODE_SPECIAL_TOKENS"
            observed_special = model.text_tokenizer.decode(
                deepcopy(ids), skip_special_tokens=False,
            )
            _observe(evidence, "observed_special_decode", observed_special)
            if type(observed_special) is not str:
                raise ValueError("special-token decode must return text")
            stage = "DECODE_FOR_PARSER"
            observed_parser = model.text_tokenizer.decode(
                deepcopy(ids), skip_special_tokens=True,
            )
            _observe(evidence, "observed_parser_decode", observed_parser)
            if type(observed_parser) is not str:
                raise ValueError("parser decode must return text")
            stage = "SERIALIZATION"
            return _json_bytes({
                "schema_version": ENVELOPE_VERSION, "backend": BACKEND,
                "model_id": MODEL_ID, "resolved_repository_id": RESOLVED_REPOSITORY_ID,
                "model_revision": REVISION, "input_ids": prepared.input_ids,
                "input_token_count": len(prepared.input_ids),
                "native_generated_ids": ids,
                "decoded_with_special_tokens": observed_special,
                "decoded_for_parser": observed_parser,
                "generation_kwargs": kwargs,
                "effective_model_condition": {
                    "precision": context.precision, "quantization": context.quantization,
                    "device": context.device, "preprocessing": _preprocessing(context.preprocessing),
                    "thinking": {k: kwargs.get(k) for k in
                                 ("enable_thinking", "enable_thinking_budget", "thinking_budget")},
                    "native_llm_generation_defaults_before_call": generation_defaults,
                },
                "runtime": {"software_versions": deepcopy(self._backend.software_versions),
                            "runner_version": self.version,
                            "persistent_call_state": self.persistent_call_state},
            })
        except Exception as exc:
            if isinstance(exc, GenerationFailure):
                raise
            raise GenerationFailure(partial_raw=_failure_raw(evidence, stage, exc)) from None


_NUMBER = r"(?:0(?:\.\d+)?|1(?:\.0+)?|\.\d+|[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
_POINT = re.compile(rf"<point>\s*\(({_NUMBER}),\s*({_NUMBER})\)\s*</point>")
_BOX = re.compile(rf"<box>\s*\(({_NUMBER}),\s*({_NUMBER})\),\s*\(({_NUMBER}),\s*({_NUMBER})\)\s*</box>")


def parse_ovis_native_spatial_evidence(text):
    """Parse only complete documented tag sequences; never produce a D5 result."""
    if type(text) is not str:
        raise TypeError("native spatial text must be a string")
    source = text.strip()
    bracketed = source.startswith("[") and source.endswith("]")
    if bracketed:
        source = source[1:-1]
    result = []
    position = 0
    while position < len(source):
        gap = re.match(r"\s*", source[position:])
        position += len(gap.group())
        if position == len(source):
            break
        point = _POINT.match(source, position)
        box = _BOX.match(source, position)
        match = point or box
        if match is None:
            return []
        values = tuple(float(v) for v in match.groups())
        if any(not math.isfinite(v) or not 0 <= v < 1 for v in values):
            return []
        if box and (values[0] > values[2] or values[1] > values[3]):
            return []
        result.append({"kind": "point" if point else "box", "coordinates": list(values)})
        position = match.end()
        if bracketed:
            position += len(re.match(r"\s*", source[position:]).group())
            if position < len(source):
                if source[position] != ",":
                    return []
                position += 1
                if not source[position:].strip():
                    return []
    if bracketed and not result:
        return []
    return result


class Ovis2_5Adapter:
    version = "ovis2-5-adapter-v1"
    parser_version = ENVELOPE_VERSION + "/" + PARSER_VERSION

    def adapt(self, raw: bytes, task: Task) -> AdaptedOutput:
        if type(raw) is not bytes:
            raise TypeError("raw envelope must be bytes")
        obj = strict_json(raw.decode("utf-8"))
        fields(obj, {
            "schema_version", "backend", "model_id", "resolved_repository_id",
            "model_revision", "input_ids", "input_token_count", "native_generated_ids",
            "decoded_with_special_tokens", "decoded_for_parser", "generation_kwargs",
            "effective_model_condition", "runtime",
        })
        for key, expected in (("schema_version", ENVELOPE_VERSION), ("backend", BACKEND),
                              ("model_id", MODEL_ID),
                              ("resolved_repository_id", RESOLVED_REPOSITORY_ID),
                              ("model_revision", REVISION)):
            if obj[key] != expected:
                raise ValueError("wrong raw envelope identity/version")
        if (type(obj["input_token_count"]) is not int or obj["input_token_count"] < 1
                or _ids(obj["input_ids"]) != obj["input_ids"]
                or len(obj["input_ids"]) != obj["input_token_count"]):
            raise ValueError("invalid input tokens")
        _ids(obj["native_generated_ids"])
        if any(type(obj[k]) is not str for k in ("decoded_with_special_tokens", "decoded_for_parser")):
            raise ValueError("decoded outputs must be strings")
        _decoding(obj["generation_kwargs"])
        if any(type(obj[k]) is not dict for k in ("effective_model_condition", "runtime")):
            raise ValueError("condition/runtime metadata must be objects")
        _json_bytes(obj)
        if task == Task.GROUNDING:
            return AdaptedOutput(
                ParseStatus.UNSUPPORTED, spatial_kind=SpatialKind.NONE,
                native_evidence={
                    "interface_status": "DOCUMENTED_BOX_AND_POINT",
                    "qualification": "NOT_YET_QUALIFIED",
                    "coordinate_convention": "x_first_top_left_normalized_[0,1)",
                    "native_candidates": parse_ovis_native_spatial_evidence(obj["decoded_for_parser"]),
                },
            )
        if task != Task.CLASSIFICATION:
            raise ValueError("unsupported task")
        parsed = parse_text(obj["decoded_for_parser"], "classification")
        return AdaptedOutput(ParseStatus.SUCCESS if parsed.success else ParseStatus.INVALID, parsed.value)
