"""SmolVLM2 4.51.3: shared CPU admission and production loader/processor.

Imports are deferred. CPU admission reads only reviewed public text and Hub
metadata, builds the full architecture on meta, and processes synthetic images.
"""
from contextlib import contextmanager, nullcontext
import hashlib
from pathlib import Path
import re

from .artifacts import read, sha
from .contract import GENERATION, MODELS, PROMPT_SHA

KEY = "smolvlm2"


@contextmanager
def meta_loader_context():
    import torch
    from accelerate import init_empty_weights
    # Transformers 4.51.3 explicitly relocates missing keys to CPU, even inside
    # torch.device('meta'). Accelerate's official parameter registration context
    # keeps the real loader's empty-state parameters on meta. Buffer construction
    # stays under torch's meta context. No loader method is mocked/replaced.
    with init_empty_weights(include_buffers=False), torch.device("meta"):
        yield


def verified_index(repo, snapshot):
    lock = read(Path(repo) / "configs/pilot/smol_checkpoint_metadata.json")
    if lock["revision"] != MODELS[KEY]["revision"]:
        raise ValueError("SMOL_CHECKPOINT_LOCK_REVISION")
    path = Path(snapshot) / lock["index"]["filename"]
    if sha(path) != lock["index"]["sha256"] or path.stat().st_size != lock["index"]["bytes"]:
        raise ValueError("SMOL_CHECKPOINT_INDEX_CHECKSUM")
    index = read(path)
    if (set(index["weight_map"].values()) != set(lock["weights"])
            or len(index["weight_map"]) != lock["index"]["tensor_count"]
            or index["metadata"]["total_size"] != lock["index"]["total_tensor_bytes"]):
        raise ValueError("SMOL_CHECKPOINT_INDEX_MAPPING")
    return index


def verified_sources(repo, snapshot):
    from .backend import check_source_review
    import transformers
    if transformers.__version__ != MODELS[KEY]["transformers"]:
        raise RuntimeError("SMOL_PINNED_TRANSFORMERS_REQUIRED")
    locked = check_source_review(repo, KEY)
    for name, expected in locked["files"].items():
        if sha(Path(snapshot) / name) != expected:
            raise ValueError("SMOL_REVIEWED_SOURCE_CHECKSUM:" + name)
    verified_index(repo, snapshot)
    return locked


def load_config(repo, snapshot):
    import transformers
    verified_sources(repo, snapshot)
    config = transformers.SmolVLMConfig.from_pretrained(str(snapshot), local_files_only=True)
    if (config.model_type != "smolvlm" or config.text_config.model_type != "llama"
            or config.vision_config.model_type != "smolvlm_vision"
            or config.text_config.num_hidden_layers != 24 or config.vision_config.num_hidden_layers != 27
            or config.text_config.max_position_embeddings != 8192 or config.image_token_id != 49190):
        raise ValueError("SMOL_CHECKPOINT_ARCHITECTURE")
    # Explicit AFTER deserialization, including the independently constructed
    # submodels. Legacy _flash_attn_2_enabled is inert in pinned LlamaAttention;
    # actual dispatch/configs/cached flags are checked on every constructed layer.
    for cfg in (config, config.text_config, config.vision_config):
        cfg._attn_implementation = "eager"
    return config


def attention_receipt(model):
    configs = {"outer": model.config, "model": model.model.config,
               "outer.text_config": model.config.text_config, "outer.vision_config": model.config.vision_config,
               "text": model.model.text_model.config, "vision": model.model.vision_model.config}
    classes = {}
    for prefix, layers in (("text", model.model.text_model.layers),
                           ("vision", model.model.vision_model.encoder.layers)):
        for i, layer in enumerate(layers):
            configs[f"{prefix}.{i}"] = layer.self_attn.config
            classes[f"{prefix}.{i}"] = type(layer.self_attn).__module__ + "." + type(layer.self_attn).__name__
    return {"configs": {p: {"class": type(c).__name__, "effective": c._attn_implementation,
                            "internal": c._attn_implementation_internal} for p, c in configs.items()},
            "classes": classes, "cached_flash": {"model": model.model._use_flash_attention_2,
                                                  "vision": model.model.vision_model._use_flash_attention_2}}


def verify_attention(model):
    from transformers.models.llama.modeling_llama import LlamaAttention
    from transformers.models.smolvlm.modeling_smolvlm import SmolVLMVisionAttention
    receipt = attention_receipt(model)
    try:
        for path, cfg in receipt["configs"].items():
            if cfg["effective"] != "eager" or cfg["internal"] != "eager":
                raise ValueError("SMOL_EXPLICIT_EAGER_REQUIRED:" + path)
        if any(value is not False for value in receipt["cached_flash"].values()):
            raise ValueError("SMOL_CACHED_FLASH_ATTENTION")
        for layers, cls, count in ((model.model.text_model.layers, LlamaAttention, 24),
                                   (model.model.vision_model.encoder.layers, SmolVLMVisionAttention, 27)):
            if len(layers) != count or any(type(layer.self_attn) is not cls for layer in layers):
                raise ValueError("SMOL_ATTENTION_CLASS_OR_LAYER_COVERAGE")
        if any("flash" in type(m).__name__.lower() or "sdpa" in type(m).__name__.lower()
               for m in model.modules()):
            raise ValueError("SMOL_UNEXPECTED_ATTENTION_MODULE")
    except BaseException as error:
        error.smol_attention_receipt = {"status": "FAIL", **receipt}
        raise
    return {"status": "VERIFIED_EAGER_MODULES", "text_layers": 24, "vision_layers": 27, **receipt}


def load_model(repo, snapshot, *, meta=False):
    import torch
    import transformers
    config = load_config(repo, snapshot)
    # Resolve lazy imports BEFORE entering meta: Torch's import-time dynamo
    # introspection creates CPU scalars. No loader or constructor is replaced.
    cls = transformers.SmolVLMForConditionalGeneration
    kwargs = {"config": config, "local_files_only": True, "revision": MODELS[KEY]["revision"],
              "torch_dtype": torch.float16, "attn_implementation": "eager", "use_safetensors": True}
    if meta:
        kwargs["state_dict"] = {}
    else:
        kwargs["device_map"] = {"": 0}
    with meta_loader_context() if meta else nullcontext():
        model = cls.from_pretrained(None if meta else str(snapshot), **kwargs).eval()
    receipt = verify_attention(model)
    # None/empty-state CPU loader does not read generation_config.json. Read the
    # same locked file explicitly for acceptance; real path loads it natively.
    generation = transformers.GenerationConfig.from_pretrained(str(snapshot), local_files_only=True)
    if meta:
        model.generation_config = generation
    elif any(getattr(model.generation_config, key) != getattr(generation, key)
             for key in ("bos_token_id", "eos_token_id", "pad_token_id")):
        raise ValueError("SMOL_NATIVE_GENERATION_CONFIG_MISMATCH")
    if meta:
        if (any(t.device.type != "meta" for t in (*model.parameters(), *model.buffers()))
                or any(p.is_floating_point() and p.dtype != torch.float16 for p in model.parameters())):
            raise ValueError("SMOL_META_FP16_PARAMETERS_REQUIRED")
        # Native Llama rotary buffers intentionally retain float32. Do not cast
        # them merely to satisfy a CPU assertion; GPU checks concern parameters.
        receipt["buffer_dtypes"] = {name: str(value.dtype) for name, value in model.named_buffers()}
        if set(model.state_dict()) != set(verified_index(repo, snapshot)["weight_map"]):
            raise ValueError("SMOL_META_CHECKPOINT_TENSOR_INVENTORY")
    return model, receipt


def load_processor(repo, snapshot):
    import transformers
    verified_sources(repo, snapshot)
    processor = transformers.AutoProcessor.from_pretrained(str(snapshot), local_files_only=True,
                                                           trust_remote_code=False)
    if (type(processor) is not transformers.SmolVLMProcessor or not processor.tokenizer.is_fast
            or processor.image_seq_len != 81
            or processor.tokenizer.convert_tokens_to_ids(processor.image_token) != 49190
            or len(processor.tokenizer) != 49280):
        raise ValueError("SMOL_PROCESSOR_TOKENIZER_MAPPING")
    image = processor.image_processor
    if (image.size != {"longest_edge": 1536} or image.max_image_size != {"longest_edge": 384}
            or not all(getattr(image, k) is True for k in
                       ("do_resize", "do_image_splitting", "do_pad", "do_convert_rgb", "do_normalize", "do_rescale"))):
        raise ValueError("SMOL_PINNED_NATIVE_PREPROCESSING")
    return processor


def prepare_inputs(processor, prompt, image):
    if image.mode != "RGB":
        raise ValueError("SMOL_RGB_REQUIRED")
    if hashlib.sha256(prompt.encode()).hexdigest() != PROMPT_SHA:
        raise ValueError("C1_PROMPT_CHECKSUM")
    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
    rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    if (rendered.count(processor.image_token) != 1 or rendered.count("<|im_start|>") != 1
            or not rendered.startswith("<|im_start|>User:<image>")
            or not rendered.endswith("<end_of_utterance>\nAssistant:")):
        raise ValueError("SMOL_SINGLE_IMAGE_CHAT_TEMPLATE")
    # 4.51.3's documented two-step image/chat API. Template already supplies
    # special tokens; no duplicate BOS. No resizing/crop override is introduced.
    inputs = processor(text=rendered, images=[image], return_tensors="pt", add_special_tokens=False)
    validate_inputs(processor, rendered, inputs)
    return rendered, inputs


def validate_inputs(processor, rendered, inputs):
    import torch
    if set(inputs) != {"input_ids", "attention_mask", "pixel_values", "pixel_attention_mask"}:
        raise ValueError("SMOL_NATIVE_INPUT_KEYS")
    ids, mask, pixels, pixel_mask = (inputs[k] for k in
                                    ("input_ids", "attention_mask", "pixel_values", "pixel_attention_mask"))
    if (ids.dtype != torch.int64 or ids.ndim != 2 or ids.shape[0] != 1
            or mask.dtype != torch.int64 or mask.shape != ids.shape or not bool((mask == 1).all())
            or bool((ids < 0).any()) or bool((ids >= len(processor.tokenizer)).any())):
        raise ValueError("SMOL_NATIVE_TOKEN_MASK_DTYPE_OR_VOCAB")
    if (pixels.ndim != 5 or pixels.shape[0] != 1 or list(pixels.shape[2:]) != [3, 384, 384]
            or pixels.dtype != torch.float32 or not bool(torch.isfinite(pixels).all())
            or pixel_mask.dtype != torch.int64 or list(pixel_mask.shape) != [1, pixels.shape[1], 384, 384]
            or not bool(((pixel_mask == 0) | (pixel_mask == 1)).all())
            or not bool((pixel_mask.sum(dim=(-1, -2)) > 0).all())):
        raise ValueError("SMOL_NATIVE_PIXEL_MASK_SHAPE_DTYPE_FINITE")
    image_tokens = int((ids == 49190).sum())
    if image_tokens != pixels.shape[1] * processor.image_seq_len:
        raise ValueError("SMOL_IMAGE_TOKEN_EXPANSION")
    base = processor.tokenizer.encode(rendered, add_special_tokens=False)
    start = base.index(49190)
    # All preceding template tokens and the complete assistant boundary survive
    # image expansion. This detects a duplicated beginning-of-text token too.
    if ids[0, :start].tolist() != base[:start] or ids[0, -32:].tolist() != base[-32:]:
        raise ValueError("SMOL_TOKEN_PREFIX_OR_ASSISTANT_BOUNDARY")
    if ids.shape[1] + GENERATION["max_new_tokens"] > 8192:
        raise ValueError("SMOL_NATIVE_CONTEXT_LIMIT")
    return {"image_token_id": 49190, "image_seq_len": 81, "image_tokens": image_tokens,
            "shapes": {k: list(v.shape) for k, v in inputs.items()},
            "dtypes": {k: str(v.dtype) for k, v in inputs.items()},
            "prefix_ids": ids[0, :start].tolist(), "assistant_boundary_ids": ids[0, -32:].tolist()}


def checkpoint_metadata(repo, info):
    from .backend import check_source_review
    from .artifacts import relative
    locked = check_source_review(repo, KEY)
    if info.sha != locked["revision"]:
        raise ValueError("SMOL_CHECKPOINT_METADATA_REVISION")
    names = [row.rfilename for row in info.siblings]
    for name in names:
        relative(name)
    if len(names) != len(set(names)) or not set(locked["files"]) <= set(names):
        raise ValueError("SMOL_CHECKPOINT_INVENTORY")
    if any(name.endswith(".py") for name in names):
        raise ValueError("SMOL_UNREVIEWED_EXECUTABLE_CODE")
    weights = {}
    checkpoint_lock = read(Path(repo) / "configs/pilot/smol_checkpoint_metadata.json")
    if checkpoint_lock["revision"] != info.sha:
        raise ValueError("SMOL_CHECKPOINT_LOCK_REVISION")
    for row in info.siblings:
        if not row.rfilename.endswith(".safetensors"):
            continue
        if row.rfilename not in checkpoint_lock["weights"]:
            raise ValueError("SMOL_ORIGINAL_TWO_SAFETENSORS_SHARDS_REQUIRED")
        lfs = row.lfs
        value = lfs if isinstance(lfs, dict) else vars(lfs) if lfs else {}
        if not re.fullmatch(r"[0-9a-f]{64}", str(value.get("sha256"))) or type(value.get("size")) is not int or value["size"] <= 0:
            raise ValueError("SMOL_CHECKPOINT_LFS_IDENTITY_REQUIRED")
        weights[row.rfilename] = {"sha256": value["sha256"], "bytes": value["size"]}
    if weights != checkpoint_lock["weights"] or checkpoint_lock["index"]["filename"] not in names:
        raise ValueError("SMOL_TWO_SHARDS_LFS_AND_INDEX_IDENTITY_REQUIRED")
    return {"revision": info.sha, "inventory": sorted(names), "weights": weights,
            "weight_bytes": "NOT_REQUESTED", "verification": "HUB_METADATA_ONLY_NOT_LOCAL_WEIGHT_HASH"}


def cpu_probe(repo):
    from .backend import check_source_review
    from .diagnostics import phase
    from .hnlo import probe, candidate_ids
    from huggingface_hub import HfApi, snapshot_download
    from PIL import Image
    import os
    locked = check_source_review(repo, KEY)
    evidence = os.environ.get("SAFESHIFT_CPU_DIAGNOSTICS")
    with phase(evidence, "cpu_admission", "smol_checkpoint_metadata"):
        metadata = checkpoint_metadata(repo, HfApi().model_info(locked["id"], revision=locked["revision"],
                                                                files_metadata=True, token=False))
    with phase(evidence, "cpu_admission", "smol_source_hashes"):
        checkpoint_lock = read(Path(repo) / "configs/pilot/smol_checkpoint_metadata.json")
        snapshot = Path(snapshot_download(locked["id"], revision=locked["revision"],
                                          allow_patterns=sorted([*locked["files"], checkpoint_lock["index"]["filename"]]), token=False))
        if snapshot.name != locked["revision"]:
            raise ValueError("SMOL_SNAPSHOT_REVISION")
        verified_sources(repo, snapshot)
    with phase(evidence, "cpu_admission", "smol_from_pretrained_meta"):
        model, attention = load_model(repo, snapshot, meta=True)
        count = sum(p.numel() for p in model.parameters())
        generation = model.generation_config.to_dict()
        del model
    with phase(evidence, "cpu_admission", "smol_native_processor"):
        processor = load_processor(repo, snapshot)
        prompt = (Path(repo) / "configs/pilot/classification_c1.txt").read_bytes().decode()
        cases = []
        for size in ((1, 1), (640, 480), (2048, 1536)):
            with Image.new("RGB", size, color=(40, 80, 120)) as image:
                rendered, inputs = prepare_inputs(processor, prompt, image)
            mapping = probe(processor.tokenizer, rendered, inputs["input_ids"][0].tolist())
            reviewed = read(Path(repo) / "configs/pilot/tokenizer_cpu_evidence.json")["models"][KEY]
            if (not mapping["boundary_ok"] or mapping["standalone_labels"] != reviewed["standalone_labels"]
                    or candidate_ids(mapping) != candidate_ids(reviewed["text_only_probe"])):
                raise ValueError("SMOL_NATIVE_TOKEN_BRANCH_ADMISSION")
            cases.append({"synthetic_size": list(size), **validate_inputs(processor, rendered, inputs),
                          "candidate_ids": candidate_ids(mapping)})
    return {"status": "CPU_META_LOADER_AND_SYNTHETIC_PROCESSOR_PASS_NOT_INFERENCE",
            "revision": locked["revision"], "source_files": locked["files"], "checkpoint": metadata,
            "loader": "SmolVLMForConditionalGeneration.from_pretrained(None,state_dict={})",
            "attention": attention, "parameter_count": count, "fp16_parameter_bytes": count * 2,
            "memory_limit": "PARAMETER_FOOTPRINT_ONLY_NOT_PEAK_RAM_VRAM_OR_FIT_PROOF",
            "checkpoint_generation": generation, "processor_cases": cases, "prompt_sha256": PROMPT_SHA,
            "weights": "NOT_DOWNLOADED", "cuda": "NOT_CALLED", "forward": "NOT_RUN"}
