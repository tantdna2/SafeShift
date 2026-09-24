"""Pinned Molmo2-O-7B offline contracts; real runtime remains PENDING.

Use execute_call + FileRawStore to persist raw evidence before adaptation.
ML imports are lazy; native loading requires an existing exact local snapshot.
"""

from copy import deepcopy
from dataclasses import dataclass
from io import BytesIO
import json
import math
import os
from pathlib import Path
import platform
import warnings

from safeshift.protocol import PARSER_VERSION
from safeshift.protocol.schema import fields, parse_text, strict_json
from .contracts import (
    AdaptedOutput, GenerationFailure, LocalRunner, ModelIdentity, ParseStatus,
    Request, RunContext, SpatialKind, Task,
)

MODEL_ID = "allenai/Molmo2-O-7B"
REVISION = "784410650d12be9bc086118fdefa32d2c3bced86"
BACKEND = "molmo2_o_transformers_custom"
ENVELOPE_VERSION = "safeshift-molmo2-o-raw-v1"
FAILURE_ENVELOPE_VERSION = "safeshift-molmo2-o-failure-v1"
IDENTITY = ModelIdentity(
    MODEL_ID, REVISION,
    "configs/pre_freeze/local_model_provenance.d9.json#molmo2_o_7b",
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
        # Malformed native rows can contain NaN/Inf or non-JSON values. Keep a
        # labelled diagnostic tree (never silently repair it into valid tokens).
        def diagnostic(item, depth=0):
            if depth > 64:
                return {"unrepresentable": "depth_limit"}
            if type(item) is list:
                return [diagnostic(child, depth + 1) for child in item]
            if type(item) is float and not math.isfinite(item):
                return {"nonfinite_float": str(item)}
            if item is None or type(item) in (str, int, float, bool):
                return item
            return {"unrepresentable_type": type(item).__name__}

        snapshot = json.dumps(diagnostic(value), ensure_ascii=True, allow_nan=False).encode("utf-8")
        name += "_diagnostic"
    evidence[name] = snapshot


def _failure_raw(evidence, count, stage, error, runner_version):
    metadata = {
        "schema_version": FAILURE_ENVELOPE_VERSION, "backend": BACKEND,
        "model_id": MODEL_ID, "model_revision": REVISION,
        "runner_version": runner_version,
        "generation_observation_status": "RETURNED_NATIVE_OUTPUT",
        "input_token_count": count, "post_generation_stage": stage,
        "post_generation_error_type": type(error).__name__,
    }
    fragments = {key: json.dumps(value, ensure_ascii=True).encode("utf-8")
                 for key, value in metadata.items()}
    fragments.update(evidence)
    # Independent of the success serializer, using previously captured fragments.
    return b"{" + b",".join(json.dumps(key).encode("utf-8") + b":" + fragments[key]
                            for key in sorted(fragments)) + b"}"


def _decoding(values):
    if type(values) is not dict or values.keys() - DECODING_KEYS:
        raise ValueError("unsupported decoding keys")
    if type(values.get("max_new_tokens")) is not int or values["max_new_tokens"] < 1:
        raise ValueError("max_new_tokens must be a positive integer")
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


SNAPSHOT_REPOSITORY_DIR = "models--allenai--Molmo2-O-7B"


def _validate_local_snapshot(value):
    """Validate location only. B3B must independently verify asset/weight bytes."""
    if not isinstance(value, (str, Path)):
        raise ValueError("snapshot resolver must return a local path")
    path = Path(value)
    suffix = (SNAPSHOT_REPOSITORY_DIR, "snapshots", REVISION)
    if not path.is_absolute() or tuple(path.parts[-3:]) != suffix:
        raise ValueError("snapshot must identify the exact repository and revision")
    resolved = path.resolve(strict=True)
    if not resolved.is_dir() or tuple(resolved.parts[-3:]) != suffix:
        raise ValueError("resolved snapshot has the wrong repository or revision")
    return resolved


def _offline_environment():
    # Require configuration before importing HF, whose flags are cached at import.
    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"):
        if os.environ.get(name) != "1":
            raise ValueError("native backend requires " + name + "=1 before ML imports")


def _native_offline_check():
    _offline_environment()
    from huggingface_hub import constants
    from transformers.utils import is_offline_mode
    if not constants.HF_HUB_OFFLINE or not constants.HF_HUB_DISABLE_TELEMETRY or not is_offline_mode():
        raise ValueError("HF was imported before offline configuration; restart the process")


@dataclass(frozen=True)
class MolmoBackend:
    torch: object
    processor_factory: object
    model_factory: object
    software_versions: dict
    snapshot_resolver: object
    offline_check: object = None


def _native_backend() -> MolmoBackend:
    _offline_environment()
    import torch
    import transformers
    import PIL
    from transformers import AutoProcessor, AutoModelForImageTextToText
    from huggingface_hub import snapshot_download, __version__ as hub_version

    _native_offline_check()
    if platform.python_version_tuple()[:2] != ("3", "11") or transformers.__version__ != "4.57.1":
        raise ValueError("native documentary target is Python 3.11 / Transformers 4.57.1")
    return MolmoBackend(torch, AutoProcessor, AutoModelForImageTextToText, {
        "python": platform.python_version(), "torch": torch.__version__,
        "transformers": transformers.__version__, "pillow": PIL.__version__,
        "huggingface_hub": hub_version,
    }, snapshot_download, _native_offline_check)


@dataclass(frozen=True)
class PreparedInput:
    inputs: object
    input_ids: list[int]
    condition: bytes


def _ids(value):
    if type(value) is not list or any(type(v) is not int or v < 0 for v in value):
        raise ValueError("token IDs must be nonnegative integers")
    return value


class Molmo2ORunner(LocalRunner):
    identity = IDENTITY
    version = "molmo2-o-runner-v1"
    partial_generation = "BLOCKING_GENERATE_NO_PARTIAL_GUARANTEE"
    persistent_call_state = "NO_DOCUMENTED_PERSISTENT_CALL_STATE"

    def __init__(self, *, backend_factory=_native_backend):
        self._backend_factory = backend_factory
        self._backend = None
        self._condition = None
        self._resources = None

    def _key(self, context):
        if self.identity != IDENTITY:
            raise ValueError("this runner only represents the pinned Molmo checkpoint")
        return _json_bytes({
            "model_id": self.identity.model_id, "revision": self.identity.immutable_revision,
            "runner_version": self.version, "backend": BACKEND,
            "precision": context.precision, "quantization": context.quantization,
            "device": context.device, "software_versions": context.software_versions,
            "preprocessing": context.preprocessing,
            "loader": {"trust_remote_code": True, "local_files_only": True,
                       "source": "EXACT_LOCAL_SNAPSHOT", "repository_id": MODEL_ID,
                       "revision": REVISION, "nested_loaders": "HF_OFFLINE_REQUIRED"},
        })

    def _check_condition(self, context):
        if self._backend is not None and self._backend.offline_check is not None:
            self._backend.offline_check()
        key = self._key(context)
        if self._condition is not None and self._condition != key:
            raise ValueError("execution condition changed; create a new runner lifecycle")
        return key

    def initialize(self, context: RunContext):
        key = self._check_condition(context)
        if self._backend is not None:
            return
        backend = self._backend_factory()
        if backend.offline_check is not None:
            backend.offline_check()
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
        if context.device != {"placement": "auto"}:
            raise ValueError("only documented device placement auto is implemented")
        if context.preprocessing not in ({}, {"mode": "official_processor"}):
            raise ValueError("only pinned official processor preprocessing is implemented")
        _decoding(context.decoding)
        if context.seed is not None:
            raise ValueError("seed application is not implemented")
        snapshot = _validate_local_snapshot(self._backend.snapshot_resolver(
            repo_id=MODEL_ID, revision=REVISION, local_files_only=True,
        ))
        kwargs = {"revision": REVISION, "trust_remote_code": True, "local_files_only": True,
                  "dtype": getattr(self._backend.torch, DTYPES[context.precision]), "device_map": "auto"}
        processor = self._backend.processor_factory.from_pretrained(str(snapshot), **kwargs)
        model = self._backend.model_factory.from_pretrained(str(snapshot), **kwargs)
        if _validate_local_snapshot(model.config.name_or_path) != snapshot:
            raise ValueError("model config must retain the exact local snapshot")
        if not callable(getattr(processor, "apply_chat_template", None)) or not callable(
                getattr(getattr(processor, "tokenizer", None), "decode", None)):
            raise ValueError("official processor/tokenizer interface unavailable")
        if not callable(getattr(model, "generate", None)):
            raise ValueError("native generate interface unavailable")
        self._generation_config(model)
        model.eval()
        # Publish both resources only when every check succeeds; failures are retryable.
        self._resources = (processor, model)

    @staticmethod
    def _generation_config(model):
        config = deepcopy(model.generation_config)
        if (config.num_return_sequences != 1 or config.return_dict_in_generate
                or config.output_scores or config.output_logits
                or config.output_attentions or config.output_hidden_states
                or config.cache_implementation not in (None, "dynamic")):
            raise ValueError("unsupported generation output/cache configuration")
        _json_bytes(config.to_dict())
        return config

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
                {"type": "text", "text": request.prompt},
                {"type": "image", "image": image},
            ]}]
            inputs = processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                return_dict=True, return_tensors="pt",
            )
            inputs = {name: value.to(model.device) for name, value in inputs.items()}
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
        if context.seed is not None:
            raise ValueError("seed application is not implemented")
        config = self._generation_config(model)
        effective = {**config.to_dict(), **kwargs}
        _json_bytes(effective)
        evidence = {}
        count = len(prepared.input_ids)
        returned = False
        stage = "GENERATE"
        try:
            with self._backend.torch.inference_mode():
                generated = model.generate(**prepared.inputs, generation_config=config, **kwargs)
                returned = True
                # Capture inside inference_mode, before even its __exit__ can fail.
                _observe(evidence, "input_ids", prepared.input_ids)
                _observe(evidence, "generation_kwargs", kwargs)
                _observe(evidence, "effective_generation_config", effective)
                _observe(evidence, "native_output_type", type(generated).__name__)
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
                text = processor.tokenizer.decode(
                    deepcopy(continuation), skip_special_tokens=skip,
                    clean_up_tokenization_spaces=False,
                )
                _observe(evidence, "observed_parser_decode" if skip else "observed_special_decode", text)
                if type(text) is not str:
                    raise ValueError("expected decoded text")
                return text

            stage = "DECODE_SPECIAL_TOKENS"
            special_text = decode(False)
            stage = "DECODE_FOR_PARSER"
            parser_text = decode(True)
            stage = "SERIALIZATION"
            return _json_bytes({
                "schema_version": ENVELOPE_VERSION, "backend": BACKEND,
                "model_id": MODEL_ID, "model_revision": REVISION, "runner_version": self.version,
                "input_ids": prepared.input_ids, "input_token_count": count,
                "generated_ids_full": full, "continuation_ids": continuation,
                "decoded_with_special_tokens": special_text, "decoded_for_parser": parser_text,
                "generation_kwargs": kwargs, "effective_generation_config": effective,
                "runtime": {"software_versions": deepcopy(self._backend.software_versions),
                            "precision": context.precision, "quantization": context.quantization,
                            "device": context.device, "preprocessing": context.preprocessing},
            })
        except Exception as exc:
            partial = _failure_raw(evidence, count, stage, exc, self.version) if returned else None
            raise GenerationFailure(partial_raw=partial) from None


class Molmo2OAdapter:
    version = "molmo2-o-adapter-v1"
    parser_version = ENVELOPE_VERSION + "/" + PARSER_VERSION

    def adapt(self, raw: bytes, task: Task) -> AdaptedOutput:
        if type(raw) is not bytes:
            raise TypeError("raw envelope must be UTF-8 bytes")
        obj = strict_json(raw.decode("utf-8"))
        fields(obj, {
            "schema_version", "backend", "model_id", "model_revision", "runner_version", "input_ids", "input_token_count",
            "generated_ids_full", "continuation_ids", "decoded_with_special_tokens",
            "decoded_for_parser", "generation_kwargs", "effective_generation_config", "runtime",
        })
        for key, expected in (("schema_version", ENVELOPE_VERSION), ("backend", BACKEND),
                              ("model_id", MODEL_ID), ("model_revision", REVISION),
                              ("runner_version", Molmo2ORunner.version)):
            if obj[key] != expected:
                raise ValueError("wrong raw envelope identity/version")
        full, continuation = _ids(obj["generated_ids_full"]), _ids(obj["continuation_ids"])
        inputs = _ids(obj["input_ids"])
        count = obj["input_token_count"]
        if (type(count) is not int or not 0 < count == len(inputs) <= len(full)
                or full[:count] != inputs or full[count:] != continuation):
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
                native_evidence={"interface_status": "DOCUMENTED_NATIVE_POINT",
                                 "qualification": "NOT_YET_QUALIFIED",
                                 "box_iou_participation": "NOT_PARTICIPATING",
                                 "native_text": obj["decoded_for_parser"]},
            )
        if task != Task.CLASSIFICATION:
            raise ValueError("unsupported task")
        parsed = parse_text(obj["decoded_for_parser"], "classification")
        return AdaptedOutput(ParseStatus.SUCCESS if parsed.success else ParseStatus.INVALID, parsed.value)
