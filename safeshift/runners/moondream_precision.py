"""CPU-only return-value bridge for pinned Moondream prepare_crops.

The caller must finish unmodified upstream preprocessing on CPU first. This
helper cannot establish the provenance of a tensor or police a caller that
bypasses it. See the separate integration design; no upstream imports/hooks here.
"""

BRIDGE_VERSION = "moondream-post-normalization-fp16-v1"
MODEL_REVISION = "9a7d4024050840e001defacec2b00727e89149e6"
CROP_SIZE = 378
CHANNELS = 3


def post_normalization_fp16_bridge(upstream_result):
    """Validate (BF16 CPU crops, (rows, cols)); return a fresh FP16 CPU tensor.

    Only the exact native two-tuple with one plain, dense, strided Tensor and
    built-in positive integer tiling is accepted. Reject subclasses, nested/extra
    tensors, gradients, non-CPU devices, other dtypes and non-finite input/output.
    Preserve shape, crop order and tiling; do not modify input storage. Exceptions
    are terminal contract errors, never a signal to retry with another dtype.
    """
    import torch

    if type(upstream_result) is not tuple or len(upstream_result) != 2:
        raise ValueError("EXPECTED_CROPS_AND_TILING_TUPLE")
    crops, tiling = upstream_result
    if (type(tiling) is not tuple or len(tiling) != 2
            or any(type(n) is not int or n < 1 for n in tiling)):
        raise ValueError("EXPECTED_POSITIVE_INTEGER_TILING")
    # Exact type prevents Tensor subclasses from overriding conversion/dispatch.
    if type(crops) is not torch.Tensor:
        raise ValueError("EXPECTED_PLAIN_TENSOR")
    # Device check precedes every tensor arithmetic or transfer operation.
    if crops.device.type != "cpu":
        raise ValueError("CPU_INPUT_REQUIRED")
    if crops.dtype != torch.bfloat16:
        raise ValueError("BF16_INPUT_REQUIRED")
    if crops.layout != torch.strided or crops.is_nested or crops.requires_grad:
        raise ValueError("EXPECTED_DENSE_INFERENCE_CROPS")
    if tuple(crops.shape) != (1 + tiling[0] * tiling[1], CHANNELS, CROP_SIZE, CROP_SIZE):
        raise ValueError("PINNED_CROP_SHAPE_REQUIRED")
    if not torch.isfinite(crops).all().item():
        raise ValueError("NONFINITE_INPUT")

    # No device argument: a checked CPU tensor stays on CPU. Never in-place.
    converted = crops.to(dtype=torch.float16, copy=True)
    if (type(converted) is not torch.Tensor or converted.device.type != "cpu"
            or converted.dtype != torch.float16 or converted.shape != crops.shape):
        raise ValueError("INVALID_CONVERSION_RESULT")
    # Finite BF16 values can overflow FP16; do not return unusable image tensors.
    if not torch.isfinite(converted).all().item():
        raise ValueError("NONFINITE_OUTPUT")
    return converted, tiling
