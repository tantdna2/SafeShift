"""Pinned Moondream2 runner. PREPARED_NOT_RUNTIME_VALIDATED; no fallback."""

from importlib.metadata import version
from io import BytesIO
import hashlib
import json
import os
import platform
import struct
from pathlib import Path

from .contracts import (AdaptedOutput, GenerationFailure, LocalRunner, ModelIdentity,
                        ParseStatus, SpatialKind, Task)
from .moondream_snapshot import (
    ROOT, PLAN_PATH, MODEL_ID, REVISION, TOKENIZER_REPO, TOKENIZER_REVISION,
    deny_network_permanently, exclusive_owner, json_bytes, require_offline, verify_snapshot,
)
from .moondream_binding import (VisionBinding, load_verified_modules, require_pillow,
                               starmie_redirect)
from .moondream_precision import BRIDGE_VERSION

IDENTITY = ModelIdentity(MODEL_ID, REVISION, "configs/pre_freeze/moondream_prep_audit.v1.json")
PREPROCESSING = {"resize_backend": "PILLOW_ONLY", "bridge_version": BRIDGE_VERSION}
DECODING = {"query": {"temperature": 0, "top_p": 1.0, "max_tokens": 32, "variant": None},
            "detect": {"max_objects": 50, "variant": None}}
_load_claimed = False
PLAN_SHA256 = "387fcf1bd9abb7cb0d265ebbebabfb25f24e2518eece825b67e425e6f6d2c1a8"


def load_plan(repo=ROOT):
    plan = json.loads((Path(repo) / PLAN_PATH).read_text(encoding="utf-8"))
    if hashlib.sha256(json_bytes(plan)).hexdigest() != PLAN_SHA256:
        raise ValueError("FROZEN_RUNTIME_PLAN_CHANGED")
    bridge = json.loads((Path(repo) / "configs/pre_freeze/moondream_precision_bridge.v1.json").read_text(encoding="utf-8"))
    if hashlib.sha256(json_bytes(bridge)).hexdigest() != "5388108ce07061528218c02cf7e0788c1f0de4d80c25bd22074d3228b1846641":
        raise ValueError("PROTECTED_BRIDGE_PLAN_CHANGED")
    if (plan["model_id"] != MODEL_ID or plan["model_revision"] != REVISION
            or plan["tokenizer_repo"] != TOKENIZER_REPO or plan["tokenizer_revision"] != TOKENIZER_REVISION
            or plan["bridge_version"] != BRIDGE_VERSION or bridge["bridge_version"] != BRIDGE_VERSION
            or plan["bridge_status"] != "PREPARED_NOT_RUNTIME_VALIDATED"
            or bridge["bridge_status"] != "PREPARED_NOT_RUNTIME_VALIDATED"):
        raise ValueError("PINNED_PLAN_OR_BRIDGE_MISMATCH")
    return plan


def validate_device(metadata):
    if (metadata["cuda_available"] is not True or type(metadata["gpu_count"]) is not int
            or metadata["gpu_count"] != 1 or metadata["name"] not in {"Tesla T4", "NVIDIA T4"}
            or metadata["compute_capability"] != [7, 5]
            or type(metadata["total_memory"]) is not int
            or not 14 * 1024**3 <= metadata["total_memory"] <= 16 * 1024**3):
        raise ValueError("EXACTLY_ONE_NVIDIA_T4_16GB_CC75_REQUIRED")


def audit_model_state(model, torch, *, observations=None):
    rows = [] if observations is None else observations
    for kind, values in (("parameter", model.named_parameters()), ("buffer", model.named_buffers())):
        for name, tensor in values:
            row = {"kind": kind, "name": name, "dtype": str(tensor.dtype),
                   "device": str(tensor.device), "floating": tensor.is_floating_point()}
            rows.append(row)
            if str(tensor.device) != "cuda:0" or (tensor.is_floating_point() and tensor.dtype != torch.float16):
                raise ValueError("MODEL_STATE_DEVICE_OR_DTYPE_MISMATCH:" + name)
    if not rows or not any(r["kind"] == "parameter" and r["floating"] for r in rows):
        raise ValueError("EMPTY_MODEL_STATE_AUDIT")
    # Pinned source registers RoPE, bool mask and all KV caches as buffers.
    # Reject additional tensor attributes instead of silently inventing exceptions.
    def check_extra(value):
        if torch.is_tensor(value):
            if str(value.device) != "cuda:0" or (value.is_floating_point() and value.dtype != torch.float16):
                raise ValueError("UNREGISTERED_RUNTIME_STATE_MISMATCH")
        elif type(value) in (tuple, list):
            for child in value:
                check_extra(child)
        elif type(value) is dict:
            for child in value.values():
                check_extra(child)
    for module in model.modules():
        if getattr(module, "_hf_hook", None) is not None:
            raise ValueError("OFFLOAD_HOOK_FORBIDDEN")
        for key, value in vars(module).items():
            if key not in {"_parameters", "_buffers", "_modules"}:
                check_extra(value)
    inner = model.model
    if inner.config.text.group_size is not None or inner.config.region.group_size is not None:
        raise ValueError("QUANTIZATION_FORBIDDEN")
    for index, block in enumerate(inner.text.blocks):
        cache = block.kv_cache
        for name in ("k_cache", "v_cache"):
            tensor = getattr(cache, name)
            if str(tensor.device) != "cuda:0" or tensor.dtype != torch.float16:
                raise ValueError("KV_CACHE_DTYPE_OR_DEVICE_MISMATCH")
            rows.append({"kind": "persistent_kv_cache", "name": str(index) + "." + name,
                         "dtype": str(tensor.dtype), "device": str(tensor.device), "floating": True})
    return rows


def _native_tree(value):
    # Type tags preserve every native field, IEEE float bits (including -0/NaN),
    # dictionary order and scalar types. Serialization is not semantic parsing.
    kind = type(value)
    if kind is dict:
        return ["dict", [[_native_tree(k), _native_tree(v)] for k, v in value.items()]]
    if kind is list:
        return ["list", [_native_tree(v) for v in value]]
    if kind is float:
        return ["float64", struct.pack(">d", value).hex()]
    if value is None or kind in (str, int, bool):
        return [kind.__name__, value]
    raise TypeError("UNSUPPORTED_NATIVE_TYPE")


def serialize_native(value):
    return json_bytes({"schema_version": "moondream-native-lossless-v1", "native": _native_tree(value)})


def deserialize_native(raw):
    document = json.loads(raw)
    if document["schema_version"] != "moondream-native-lossless-v1":
        raise ValueError("UNKNOWN_NATIVE_FORMAT")
    def decode(node):
        tag, value = node
        if tag == "dict":
            return {decode(k): decode(v) for k, v in value}
        if tag == "list":
            return [decode(v) for v in value]
        if tag == "float64":
            return struct.unpack(">d", bytes.fromhex(value))[0]
        if tag in {"str", "int", "bool", "NoneType"}:
            return value
        raise ValueError("UNKNOWN_NATIVE_TAG")
    return decode(document["native"])


class PendingMoondreamAdapter:
    version = "moondream-native-pending-v1"
    parser_version = "NOT_QUALIFIED"

    def adapt(self, raw, task):
        native = deserialize_native(raw)
        if task == Task.GROUNDING:
            return AdaptedOutput(ParseStatus.UNSUPPORTED, spatial_kind=SpatialKind.NONE,
                                 native_evidence=native)
        # Classification qualification/parser mapping is a separate prerequisite.
        return AdaptedOutput(ParseStatus.INVALID, native_evidence=native)


class NativeBackend:
    def __init__(self):
        require_offline()
        if platform.system() != "Linux" or platform.machine() != "x86_64":
            raise ValueError("PINNED_LINUX_X86_64_ENVIRONMENT_REQUIRED")
        import torch
        import PIL.Image
        import tokenizers
        self.torch, self.image, self.tokenizer = torch, PIL.Image, tokenizers.Tokenizer
        self.software = {name: version(name) for name in load_plan()["software"] if name != "python"}
        self.software["python"] = platform.python_version()

    def metadata(self):
        cuda = self.torch.cuda
        available, count = cuda.is_available(), cuda.device_count()
        if not available or count != 1:
            return {"cuda_available": available, "gpu_count": count, "name": None,
                    "compute_capability": None, "total_memory": None}
        props = cuda.get_device_properties(0)
        return {"cuda_available": available, "gpu_count": count, "name": props.name,
                "compute_capability": [props.major, props.minor], "total_memory": props.total_memory}

    def load(self, model_snapshot, tokenizer_snapshot):
        hf, modules = load_verified_modules(model_snapshot)
        require_pillow(modules, self.image)
        with starmie_redirect(modules["moondream"], model_snapshot, tokenizer_snapshot,
                              self.tokenizer) as redirect:
            config = hf.HfConfig.from_pretrained(str(model_snapshot), local_files_only=True,
                                               revision=REVISION)
            model = hf.HfMoondream.from_pretrained(
                str(model_snapshot), config=config, local_files_only=True,
                revision=REVISION, torch_dtype=self.torch.float16, use_safetensors=True,
                device_map=None, low_cpu_mem_usage=False,
            )
            if model.model.tokenizer is not redirect["tokenizer"]:
                raise ValueError("ACTUAL_STARMIE_INSTANCE_MISMATCH")
        # CPU allocation is load staging, never inference offload. Cast ALL state
        # before transfer; HF torch_dtype alone does not cover explicit upstream BF16.
        model = model.to(dtype=self.torch.float16).to(device="cuda:0").eval()
        model._setup_caches()
        binding = VisionBinding(model.model, modules, model_snapshot, self.torch, self.image)
        return model, binding


class Moondream2Runner(LocalRunner):
    identity = IDENTITY
    version = "moondream2-offline-v1"

    def __init__(self, model_snapshot, tokenizer_snapshot, *, backend_factory=NativeBackend, repo=ROOT):
        self.repo = repo
        self.model_snapshot, self.tokenizer_snapshot = model_snapshot, tokenizer_snapshot
        self.backend_factory = backend_factory
        self.backend = self.model = self.binding = None
        self.condition = None
        self.valid = True
        self.pid = os.getpid()
        self.evidence = {"model_load_count": 0, "query_call_count": 0, "detect_call_count": 0,
                         "state_audits": [], "image_boundaries": []}

    def _audit_state(self, phase):
        record = {"phase": phase, "status": "FAILED", "observations": []}
        self.evidence["state_audits"].append(record)
        audit_model_state(self.model, self.backend.torch, observations=record["observations"])
        record["status"] = "VALID"

    def _condition(self, context):
        if not self.valid or self.pid != os.getpid() or self.identity != IDENTITY:
            raise ValueError("RUNNER_INVALID_OR_IDENTITY_MISMATCH")
        decoding = DECODING
        if context.source_kind == "INSPECSAFE":
            from .p2_bridge import require_production_context
            require_production_context("moondream", context, self.repo)
            decoding = {"query": DECODING["query"]}
        if (context.precision != "FP16" or context.quantization != "NONE"
                or context.device != {"placement": "cuda:0"}
                or context.preprocessing != PREPROCESSING or context.decoding != decoding
                or context.seed is not None):
            raise ValueError("EXACT_RUNTIME_CONDITION_REQUIRED_NO_FALLBACK")
        plan = load_plan(self.repo)
        if context.software_versions != plan["software"]:
            raise ValueError("EXACT_SOFTWARE_REQUIRED")
        key = json_bytes({"precision": context.precision, "quantization": context.quantization,
                          "device": context.device, "preprocessing": context.preprocessing,
                          "decoding": context.decoding, "software": context.software_versions})
        if self.condition is not None and key != self.condition:
            raise ValueError("RUNTIME_CONDITION_CHANGED")
        return key

    def initialize(self, context):
        with exclusive_owner():
            key = self._condition(context)
            if self.backend is not None:
                return
            deny_network_permanently()
            try:
                self.backend = self.backend_factory()
                if self.backend.software != context.software_versions:
                    raise ValueError("INSTALLED_SOFTWARE_MISMATCH")
                self.evidence["software_versions"] = self.backend.software
                self.evidence["gpu"] = self.backend.metadata()
                validate_device(self.evidence["gpu"])
                self.condition = key
            except BaseException:
                self.valid = False
                raise

    def load(self, context):
        global _load_claimed
        with exclusive_owner():
            self._condition(context)
            require_offline()
            if self.model is not None:
                return
            if self.backend is None or _load_claimed:
                raise RuntimeError("ONE_MODEL_LOAD_PER_DEDICATED_PROCESS_REQUIRED")
            _load_claimed = True
            try:
                self.evidence["model_manifest"] = verify_snapshot(self.model_snapshot, MODEL_ID, REVISION)
                self.evidence["tokenizer_manifest"] = verify_snapshot(self.tokenizer_snapshot, TOKENIZER_REPO, TOKENIZER_REVISION)
                self.evidence["model_load_count"] += 1
                self.model, self.binding = self.backend.load(self.model_snapshot, self.tokenizer_snapshot)
                self._audit_state("post_load")
                self.evidence["image_boundaries"] = self.binding.events
            except BaseException:
                self.valid = False
                raise

    def prepare_input(self, request, context):
        with exclusive_owner():
            self._condition(context)
            if context.source_kind == "INSPECSAFE" and request.task != Task.CLASSIFICATION:
                raise ValueError("PRODUCTION_CLASSIFICATION_ONLY")
            if self.model is None or request.task not in (Task.CLASSIFICATION, Task.GROUNDING):
                raise ValueError("LOADED_MODEL_AND_NATIVE_TASK_REQUIRED")
            # Request accepts immutable bytes, never upstream EncodedImage/history.
            image = self.backend.image.open(BytesIO(request.input_bytes))
            image.load()
            return request.task, image, request.prompt

    def generate_raw(self, prepared, context):
        with exclusive_owner():
            self._condition(context)
            require_offline()
            raw = None
            try:
                task, image, prompt = prepared
                self._audit_state("pre_native_call")
                # Clear independent-call persistent caches; fresh image encode every call.
                for block in self.model.model.text.blocks:
                    block.kv_cache.k_cache.zero_()
                    block.kv_cache.v_cache.zero_()
                with self.backend.torch.inference_mode(), self.binding.installed():
                    if task == Task.CLASSIFICATION:
                        self.evidence["query_call_count"] += 1
                        native = self.model.query(image, prompt, stream=False, settings=dict(DECODING["query"]))
                    elif task == Task.GROUNDING:
                        self.evidence["detect_call_count"] += 1
                        native = self.model.detect(image, prompt, settings=dict(DECODING["detect"]))
                    else:
                        raise ValueError("UNSUPPORTED_NATIVE_API")
                    raw = serialize_native(native)
                self._audit_state("post_native_call")
                return raw
            except BaseException as error:
                self.valid = False
                if isinstance(error, GenerationFailure):
                    raise
                # Native blocking calls expose no partial object on an internal
                # failure. Preserve a completed return if a later invariant fails.
                raise GenerationFailure(raw) from error
