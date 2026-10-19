"""Conservative admission for existing lossless JSON full-vector capture/export."""
import json
from pathlib import Path
import shutil

# A planning ceiling, NOT a claim about checkpoint vocabulary. Verified config
# supplies the actual dimension; larger checkpoints stop rather than lose vectors.
VOCAB_CEILING = 200_000
STEPS = 32
KINDS = 2
JSON_BYTES_PER_SCALAR = 64  # exceeds native FP16/FP32 scalar JSON representation


def budget(vocab=VOCAB_CEILING):
    if type(vocab) is not int or not 1 <= vocab <= VOCAB_CEILING:
        raise ValueError("FULL_VECTOR_VOCAB_RESOURCE_BOUND_EXCEEDED")
    scalars = vocab * STEPS * KINDS
    vector_json = scalars * JSON_BYTES_PER_SCALAR
    return {"vocab_size": vocab, "max_steps": STEPS, "kinds": KINDS,
            "float32_tensor_bytes": scalars * 4, "scalar_count": scalars,
            "vector_json_upper_bytes": vector_json,
            # Original capture, evidence copy, worst-case archive and transient
            # serialization/export headroom. No compression gain is assumed.
            "required_output_free_bytes": 4 * vector_json + 512 * 2**20,
            "required_available_ram_bytes": 24 * 2**30,
            "policy": "STOP_BEFORE_LOAD_IF_INSUFFICIENT;NEVER_TRUNCATE"}


def require_resources(output, *, snapshot=None):
    vocab = VOCAB_CEILING
    if snapshot is not None:
        # Caller has already verified the complete pinned checkpoint inventory.
        config = json.loads((Path(snapshot) / "config.json").read_bytes())
        vocab = config["text_config"]["vocab_size"]
    row = budget(vocab)
    row["output_free_bytes"] = shutil.disk_usage(output).free
    info = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    row["available_ram_bytes"] = int(info["MemAvailable"].strip().split()[0]) * 1024
    if row["output_free_bytes"] < row["required_output_free_bytes"]:
        raise OSError("FULL_VECTOR_OUTPUT_STORAGE_INSUFFICIENT")
    if row["available_ram_bytes"] < row["required_available_ram_bytes"]:
        raise OSError("FULL_VECTOR_HOST_RAM_INSUFFICIENT")
    return row
