"""Candidate image/token checks, shared with the PR150 CPU probe."""
import hashlib
from safeshift.pilot.contract import GENERATION, PROMPT_SHA
from .source import require

def prepare_inputs(processor, key, prompt, image):
    """Single RGB image, exact C1 and checkpoint template; no resizing rescue."""
    require(image.mode == "RGB" and min(image.size) > 0, "RGB_NONEMPTY_REQUIRED")
    require(hashlib.sha256(prompt.encode()).hexdigest() == PROMPT_SHA, "FROZEN_C1_SHA")
    if key == "internvl35":
        messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
        rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=rendered, images=image, return_tensors="pt")
    elif key == "minicpm4":
        messages = [{"role": "user", "content": "(<image>./</image>)\n" + prompt}]
        rendered = processor.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        # The pinned processor ignores image input_data_format kwargs. Use its
        # native slicing, normalization and patch packing with known PIL RGB HWC.
        from .minicpm_image import rgb_image_inputs
        images = rgb_image_inputs(processor.image_processor, image)
        inputs = processor._convert_images_texts_to_inputs(images, [rendered], max_length=None,
                                                          return_tensors="pt")
    else:
        raise ValueError("UNKNOWN_CANDIDATE")
    require(rendered.count(prompt) == 1, "C1_NOT_PRESERVED_ONCE")
    require("system" not in rendered and "<think>" not in rendered, "HIDDEN_SYSTEM_OR_THINKING")
    return rendered, inputs


def validate_inputs(processor, key, config, rendered, inputs, prompt):
    import torch
    ids, mask = inputs["input_ids"], inputs["attention_mask"]
    require(ids.ndim == 2 and ids.shape[0] == 1 and ids.dtype in (torch.int32, torch.int64), "INPUT_IDS_DTYPE_SHAPE")
    require(mask.shape == ids.shape and mask.dtype in (torch.bool, torch.int32, torch.int64)
            and bool((mask == 1).all()), "ATTENTION_MASK")
    require(bool((ids >= 0).all()) and bool((ids < len(processor.tokenizer)).all()), "VOCAB_RANGE")
    decoded = processor.tokenizer.decode(ids[0].tolist(), skip_special_tokens=False,
                                        clean_up_tokenization_spaces=False)
    require(decoded.count(prompt) == 1, "EXPANDED_INPUT_C1_TRUNCATED_OR_CHANGED")
    require(ids.shape[1] + GENERATION["max_new_tokens"] <=
            (config.text_config.max_position_embeddings if key == "internvl35" else config.max_position_embeddings),
            "CONTEXT_OVERFLOW")
    pixels = inputs["pixel_values"]
    if key == "internvl35":
        require(config.image_token_id == 151671, "EXACT_4B_HF_IMAGE_TOKEN")
        require(processor.image_seq_length == 256, "NATIVE_256_TOKENS_PER_TILE")
        count = int((ids == config.image_token_id).sum())
        require(pixels.ndim == 4 and list(pixels.shape[1:]) == [3, 448, 448], "INTERNVL_TILES")
        require(1 <= pixels.shape[0] <= 13 and count == pixels.shape[0] * 256, "IMAGE_TOKEN_TILE_COUNT")
        tensors = [pixels]
        detail = {"tiles_including_thumbnail": pixels.shape[0], "image_tokens": count,
                  "pixel_shapes": [list(pixels.shape)]}
    else:
        ip = processor.image_processor
        require((ip.image_feature_size, ip.patch_size, ip.max_slice_nums, ip.scale_resolution, ip.use_image_id) ==
                (config.query_num, config.patch_size, config.slice_config.max_slice_nums,
                 config.slice_config.scale_resolution, config.use_image_id), "MINICPM_CONFIG_PROCESSOR_DRIFT")
        require(ip.slice_mode == config.slice_mode, "MINICPM_SLICE_MODE_DRIFT")
        tensors = pixels[0]
        bounds = inputs["image_bound"][0]
        require(bounds.ndim == 2 and bounds.shape[1] == 2 and bounds.dtype in (torch.int32, torch.int64),
                "IMAGE_BOUNDS_DTYPE_SHAPE")
        require(bool((bounds[:, 0] >= 0).all()) and bool((bounds[:, 1] <= ids.shape[1]).all()),
                "IMAGE_BOUNDS_RANGE")
        require(bool((bounds[1:, 0] >= bounds[:-1, 1]).all()), "IMAGE_BOUNDS_ORDER")
        require(len(tensors) == len(bounds) and 1 <= len(tensors) <= 10, "SLICE_BOUND_COUNT")
        require(all(int(end - start) == 64 for start, end in bounds), "SLICE_64_QUERY_TOKENS")
        require(all(int((ids[0, start:end] == processor.tokenizer.unk_id).sum()) == 64
                    for start, end in bounds), "SLICE_PLACEHOLDER_IDS")
        require(len(inputs["tgt_sizes"][0]) == len(tensors), "PATCH_GRID_COUNT")
        for tensor, grid in zip(tensors, inputs["tgt_sizes"][0]):
            require(grid.shape == (2,) and grid.dtype in (torch.int32, torch.int64)
                    and bool((grid > 0).all()), "PATCH_GRID_DTYPE_RANGE")
            require(tensor.ndim == 3 and tensor.shape[:2] == (3, 14)
                    and tensor.numel() == 3 * int(grid.prod()) * 14**2,
                    "PIXEL_PATCH_GRID")
        detail = {"slices_including_global": len(tensors), "image_tokens": len(tensors) * 64,
                  "pixel_shapes": [list(t.shape) for t in tensors],
                  "patch_grids": inputs["tgt_sizes"][0].tolist()}
    require(all(t.device.type == "cpu" and t.dtype == torch.float32 and bool(torch.isfinite(t).all())
                for t in tensors), "PIXELS_CPU_FLOAT32_FINITE")
    return {**detail, "input_length": ids.shape[1], "ids_dtype": str(ids.dtype),
            "mask_dtype": str(mask.dtype), "rendered_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
            "input_ids_sha256": hashlib.sha256(ids.cpu().numpy().tobytes()).hexdigest()}
