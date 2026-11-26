"""One shared native Phi processor path for CPU admission and the GPU worker."""
from pathlib import Path

from .artifacts import sha


def load_processor(repo, snapshot):
    from .backend import check_source_review
    import transformers
    locked = check_source_review(repo, "phi")
    for name, expected in locked["files"].items():
        if sha(Path(snapshot) / name) != expected:
            raise ValueError("PHI_PROCESSOR_REVIEWED_SOURCE_CHECKSUM:" + name)
    processor = transformers.AutoProcessor.from_pretrained(
        str(snapshot), local_files_only=True, trust_remote_code=True,
        revision=locked["revision"], code_revision=locked["revision"], num_crops=16)
    if processor.image_processor.num_crops != 16:
        raise ValueError("PHI_NATIVE_16_CROPS_REQUIRED")
    return processor


def prepare_inputs(processor, prompt, image):
    if image.mode != "RGB" or processor.image_processor.num_crops != 16:
        raise ValueError("PHI_RGB_AND_16_CROPS_REQUIRED")
    messages = [{"role": "user", "content": "<|image_1|>\n" + prompt}]
    rendered = processor.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(rendered, [image], return_tensors="pt")
    validate_inputs(processor, inputs)
    return rendered, inputs


def validate_inputs(processor, inputs):
    import torch
    if set(inputs) != {"input_ids", "attention_mask", "pixel_values", "image_sizes"}:
        raise ValueError("PHI_NATIVE_INPUT_KEYS")
    ids, mask, pixels, sizes = (inputs[k] for k in
                               ("input_ids", "attention_mask", "pixel_values", "image_sizes"))
    if (ids.dtype != torch.int64 or ids.ndim != 2 or ids.shape[0] != 1
            or mask.dtype != torch.int64 or mask.shape != ids.shape or not bool((mask == 1).all())
            or sizes.dtype != torch.int64 or list(sizes.shape) != [1, 2]):
        raise ValueError("PHI_NATIVE_TOKEN_MASK_DIMENSION_DTYPE")
    h, w = sizes[0].tolist()
    if h <= 0 or w <= 0 or h % 336 or w % 336 or (h // 336) * (w // 336) > 16:
        raise ValueError("PHI_NATIVE_IMAGE_GRID")
    count = ((h // 336) * (w // 336) + 1) * 144 + 1 + (h // 336 + 1) * 12
    if (int((ids == -1).sum()) != count or bool((ids < -1).any())
            or bool((ids >= len(processor.tokenizer)).any())):
        raise ValueError("PHI_NATIVE_IMAGE_TOKEN_EXPANSION_OR_VOCAB")
    # 16 is the HD crop budget; native tensor includes a 17th global crop.
    if (list(pixels.shape) != [1, 17, 3, 336, 336] or pixels.dtype != torch.float32
            or not bool(torch.isfinite(pixels).all())):
        raise ValueError("PHI_NATIVE_PIXEL_SHAPE_DTYPE_FINITE")
    return {"num_crops": 16, "image_token_count": count,
            "shapes": {k: list(v.shape) for k, v in inputs.items()},
            "dtypes": {k: str(v.dtype) for k, v in inputs.items()}}


def cpu_processor_probe(repo):
    from .backend import check_source_review
    from .contract import MODELS
    from huggingface_hub import snapshot_download
    from PIL import Image
    locked = check_source_review(repo, "phi")
    snapshot = Path(snapshot_download(MODELS["phi"]["id"], revision=locked["revision"],
                                      allow_patterns=sorted(locked["files"])))
    if snapshot.name != locked["revision"]:
        raise ValueError("PHI_PROCESSOR_SNAPSHOT_REVISION")
    processor = load_processor(repo, snapshot)
    prompt = (Path(repo) / "configs/pilot/classification_c1.txt").read_text(encoding="utf-8")
    with Image.new("RGB", (336, 336), color=(40, 80, 120)) as image:
        _, inputs = prepare_inputs(processor, prompt, image)
    return {"status": "SYNTHETIC_CPU_PROCESSOR_PASS_NOT_INFERENCE",
            **validate_inputs(processor, inputs), "weights": "NOT_DOWNLOADED", "cuda": "NOT_CALLED"}


def checkpoint_metadata(repo, info):
    """Validate Hub inventory/LFS identities only, without requesting weights."""
    import re
    from .backend import check_source_review
    from .contract import MODELS
    locked = check_source_review(repo, "phi")
    if info.sha != MODELS["phi"]["revision"]:
        raise ValueError("PHI_CHECKPOINT_METADATA_REVISION")
    names = [row.rfilename for row in info.siblings]
    if len(names) != len(set(names)):
        raise ValueError("PHI_CHECKPOINT_DUPLICATE_PATH")
    if {n for n in names if n.endswith(".py")} != {n for n in locked["files"] if n.endswith(".py")}:
        raise ValueError("PHI_CHECKPOINT_UNREVIEWED_CODE")
    weights = {}
    for row in info.siblings:
        if not row.rfilename.endswith(".safetensors"):
            continue
        if not re.fullmatch(r"model-0000[12]-of-00002\.safetensors", row.rfilename):
            raise ValueError("PHI_CHECKPOINT_TWO_ORIGINAL_SHARDS_REQUIRED")
        lfs = row.lfs
        expected = lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)
        size = lfs.get("size") if isinstance(lfs, dict) else getattr(lfs, "size", None)
        if not re.fullmatch(r"[0-9a-f]{64}", str(expected)) or type(size) is not int or size <= 0:
            raise ValueError("PHI_CHECKPOINT_LFS_IDENTITY_REQUIRED")
        weights[row.rfilename] = {"sha256": expected, "bytes": size}
    if len(weights) != 2 or "model.safetensors.index.json" not in names:
        raise ValueError("PHI_CHECKPOINT_TWO_SHARDS_AND_INDEX_REQUIRED")
    return {"revision": info.sha, "shards": weights,
            "total_weight_bytes": sum(row["bytes"] for row in weights.values()),
            "weight_bytes": "NOT_REQUESTED", "verification": "HUB_METADATA_ONLY_NOT_LOCAL_WEIGHT_HASH"}


def cpu_checkpoint_probe(repo):
    from huggingface_hub import HfApi
    from .contract import MODELS
    spec = MODELS["phi"]
    return checkpoint_metadata(repo, HfApi().model_info(spec["id"], revision=spec["revision"], files_metadata=True))
