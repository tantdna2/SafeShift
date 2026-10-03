"""D9R19 prospective settings, independently validated from historical evidence.

This module has no execution entry point. InspecSafe stays unauthorized. Native
model provisioning/execution remains behind existing external-only firewalls.
"""

from pathlib import Path
import json

from .schema import strict_json

POLICY_PATH = "configs/pre_freeze/production_execution_policy.d9r19.v1.json"
ROOT = Path(__file__).resolve().parents[2]


def load_policy(repo=ROOT):
    policy = strict_json((Path(repo) / POLICY_PATH).read_bytes())
    if (policy["inspecsafe_inference_authorized"] is not False
            or policy["protocol_freeze"] != "PENDING"
            or set(policy["classification"]) != {"qwen3", "qwen2_5", "internvl3", "moondream"}):
        raise ValueError("D9R19_SCOPE_VIOLATION")
    return policy


def validate_context(model, context, *, repo=ROOT):
    """Exact prospective condition, not authorization to execute on a dataset."""
    policy = load_policy(repo)
    if model not in policy["classification"]:
        raise ValueError("CLASSIFICATION_NOT_PARTICIPATING")
    entry = policy["classification"][model]
    for key in ("decoding", "preprocessing", "precision", "quantization", "device", "software_versions", "seed"):
        if json.dumps(getattr(context, key), sort_keys=True, allow_nan=False) != json.dumps(entry[key], sort_keys=True, allow_nan=False):
            raise ValueError("PROSPECTIVE_EXECUTION_CONDITION_MISMATCH:" + key)
    if context.source_kind not in {"HANDCRAFTED_RUNTIME_SMOKE", "EXTERNAL_CLASSIFICATION_QUALIFICATION", "SYNTHETIC_UNIT_TEST"}:
        raise ValueError("NO_INSPECSAFE_INFERENCE")
    return entry


def require_grounding_contract(model, *, exploratory=False):
    if exploratory:
        if model not in {"qwen3", "moondream", "paligemma"}:
            raise ValueError("EXPLORATORY_GROUNDING_EXCLUDED")
        raise ValueError("EXPLORATORY_BENCHMARK_EXECUTION_CONTRACT_BLOCKER:" + model)
    if model == "moondream":
        raise ValueError("MOONDREAM_CALL2_ORCHESTRATION_BLOCKER")
    raise ValueError("PRIMARY_GROUNDING_NOT_PARTICIPATING")
