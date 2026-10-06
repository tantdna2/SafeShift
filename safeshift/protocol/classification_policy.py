"""D9R23 immutable prompt and prospective execution contract; no execution API.

Selective redesign of PR #67 execution_policy; grounding is not a dependency.
"""

import hashlib
import json
from pathlib import Path

from .schema import strict_json

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = "configs/pre_freeze/production_classification_policy.d9r23.v1.json"
PROMPT_PATH = "prompts/p2_classification_c1_v1.txt"
PROMPT_VERSION = "p2-classification-c1-v1"
PROMPT_SHA256 = "816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3"
MODELS = ("qwen3", "qwen2_5", "internvl3", "moondream")
OFFLINE_SOURCES = {"HANDCRAFTED_RUNTIME_SMOKE", "EXTERNAL_CLASSIFICATION_QUALIFICATION",
                   "SYNTHETIC_UNIT_TEST"}


def same_json(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(
        right, sort_keys=True, allow_nan=False)


def load_policy(repo=ROOT):
    policy = strict_json((Path(repo) / POLICY_PATH).read_bytes())
    if (policy["schema_version"] != "production-classification-d9r23-v1"
            or tuple(policy["classification"]) != MODELS
            or policy["classification_only"] is not True
            or policy["active_grounding_dependency"] is not False
            or policy["inspecsafe_inference_authorized"] is not False
            or policy["implementation_freeze"] != "PENDING"
            or policy["protocol_freeze"] != "PENDING"
            or policy["semantic_scores_used_for_selection"] is not False
            or policy["prompt"]["path"] != PROMPT_PATH
            or policy["prompt"]["version"] != PROMPT_VERSION
            or policy["prompt"]["sha256"] != PROMPT_SHA256):
        raise ValueError("D9R23_SCOPE_OR_PROMPT_MISMATCH")
    for entry in policy["classification"].values():
        if (entry["prompt_version"] != PROMPT_VERSION or entry["prompt_sha256"] != PROMPT_SHA256
                or entry["raw_before_parse_required"] is not True
                or entry["semantic_scores_used_for_selection"] is not False):
            raise ValueError("D9R23_MODEL_CONTRACT_MISMATCH")
    return policy


def render_prompt(model, *, repo=ROOT):
    """No GT, sample metadata, model predictions or caller policy accepted."""
    if model not in MODELS:
        raise ValueError("CLASSIFICATION_NOT_PARTICIPATING")
    load_policy(repo)
    raw = (Path(repo) / PROMPT_PATH).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROMPT_SHA256:
        raise ValueError("C1_PROMPT_HASH_MISMATCH")
    return raw.decode("utf-8")


def validate_context(model, context, hardware, *, repo=ROOT):
    """Validate recorded conditions, never authorize inference or import a backend."""
    policy = load_policy(repo)
    if model not in MODELS:
        raise ValueError("CLASSIFICATION_NOT_PARTICIPATING")
    entry = policy["classification"][model]
    if context.source_kind not in OFFLINE_SOURCES:
        raise ValueError("NO_INSPECSAFE_INFERENCE")
    for key in ("decoding", "preprocessing", "precision", "quantization", "device",
                "software_versions", "seed"):
        if not same_json(getattr(context, key), entry[key]):
            raise ValueError("PRODUCTION_CONDITION_MISMATCH:" + key)
    if not same_json(hardware, entry["hardware_contract"]):
        raise ValueError("PRODUCTION_HARDWARE_MISMATCH")
    return entry
