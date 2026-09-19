"""Offline Qwen route and P2 decoding validation; no credentials or transport."""

from dataclasses import dataclass, field
import os
import re

MODEL_ID = "qwen3-vl-8b-instruct"
REGION = "ap-southeast-1"
ENDPOINT_TEMPLATE = "https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
ENDPOINT_ENV = "QWEN_WORKSPACE_ENDPOINT"
WORKSPACE_ID_ENV = "QWEN_WORKSPACE_ID"
POLICY_VERSION = "qwen-singapore-instruct-temperature-zero-v1"
PENDING = "PENDING_USER_CONFIGURATION"

# DNS-label syntax is a local safety constraint, not a claim about allocated IDs.
_WORKSPACE_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_ENDPOINT = re.compile(
    r"https://(" + _WORKSPACE_LABEL + r")"
    r"\.ap-southeast-1\.maas\.aliyuncs\.com/compatible-mode/v1"
)


def validate_workspace_endpoint(endpoint: str) -> str:
    """Accept only an exact HTTPS Singapore workspace base URL; never echo input."""
    match = _ENDPOINT.fullmatch(endpoint) if isinstance(endpoint, str) else None
    if match is None or match[1] == "trial":
        raise ValueError("QWEN_ENDPOINT_INVALID: expected Singapore workspace base URL")
    return endpoint


def validate_qwen_policy(config: dict) -> None:
    """Fail closed on policy drift, inline secrets/routes and extra request knobs."""
    expected = {
        "model_id": MODEL_ID,
        "region": REGION,
        "status": "ROUTE_REGION_PINNED",
        "api_key_env": "DASHSCOPE_API_KEY",
        "endpoint_env": ENDPOINT_ENV,
        "workspace_id_env": WORKSPACE_ID_ENV,
        "workspace_endpoint": "ENVIRONMENT_ONLY",
        "workspace_endpoint_status": PENDING,
        "workspace_endpoint_requirement": "WORKSPACE_ENDPOINT_TO_BE_RESOLVED_BEFORE_FREEZE",
        "workspace_endpoint_template": ENDPOINT_TEMPLATE,
        "chat_endpoint_template": ENDPOINT_TEMPLATE + "/chat/completions",
        "http_method": "POST",
        "legacy_endpoint_fallback": False,
        "route_evidence": "DOC_VERIFIED",
        "model_availability": "DOC_VERIFIED_AVAILABLE_IN_REGION",
        "coordinate_convention": "xyxy_1000",
        "envelope_contract": "OPENAI_COMPATIBLE_CHAT_DOC_VERIFIED_NOT_LIVE_VERIFIED",
        "decoding_policy_version": POLICY_VERSION,
        "decoding_status": "FROZEN_DOC_VERIFIED",
        "decoding": {"temperature": 0},
        "other_sampling_parameters": "PROVIDER_DEFAULT_OMITTED",
        "thinking_enabled": False,
        "thinking_policy": "INSTRUCT_NON_THINKING_OMIT_THINKING_PARAMETERS",
        "precision": "UNDISCLOSED_BY_PROVIDER",
        "hosted_reproducibility": "HOSTED_BACKEND_NOT_FULLY_PINNABLE",
        "capability_evidence": "LEVEL_1_DOC_VERIFIED",
        "grounding_eligibility": "ELIGIBLE_PER_D8_ROUTE_ASSUMPTIONS",
        "live_route_verified": False,
        "documentation_access_date": "2026-09-19",
    }
    # Strict types prevent False being accepted as temperature zero, or 0 as false.
    def matches(actual, reference):
        if isinstance(reference, dict):
            return (isinstance(actual, dict) and actual.keys() == reference.keys()
                    and all(matches(actual[key], value) for key, value in reference.items()))
        if type(reference) is int:
            return type(actual) in (int, float) and actual == reference
        return type(actual) is type(reference) and actual == reference

    if not matches(config, expected):
        raise ValueError("QWEN_POLICY_INVALID: configuration differs from pinned policy")


@dataclass(frozen=True)
class QwenConfiguration:
    # Deliberately absent from repr and the CLI report; retained only in memory.
    workspace_endpoint: str | None = field(repr=False)

    def __post_init__(self):
        if self.workspace_endpoint is not None:
            validate_workspace_endpoint(self.workspace_endpoint)

    @property
    def workspace_endpoint_status(self) -> str:
        return "RESOLVED" if self.workspace_endpoint is not None else PENDING

    def report(self) -> dict:
        return {
            "model_id": MODEL_ID,
            "region": REGION,
            "workspace_endpoint_status": self.workspace_endpoint_status,
            "route_evidence": "DOC_VERIFIED",
            "model_availability": "DOC_VERIFIED_AVAILABLE_IN_REGION",
            "live_route_verified": False,
            "decoding_policy_version": POLICY_VERSION,
            "decoding": {"temperature": 0},
            "thinking_enabled": False,
            "checklist_1": "DONE" if self.workspace_endpoint is not None else PENDING,
            "checklist_2": "DONE",
            "protocol_freeze_commit_sha": "PENDING",
        }


def resolve_qwen_configuration(config: dict) -> QwenConfiguration:
    """Read only the two route env vars; never read an API key or a dotenv file.

    An explicit endpoint wins, even if invalid (no silent fallback to the ID).
    Missing variables leave the route pending; empty supplied values are errors.
    """
    validate_qwen_policy(config)
    endpoint = os.environ.get(ENDPOINT_ENV)
    if endpoint is None:
        workspace_id = os.environ.get(WORKSPACE_ID_ENV)
        if workspace_id is None:
            return QwenConfiguration(None)
        if not re.fullmatch(_WORKSPACE_LABEL, workspace_id) or workspace_id == "trial":
            raise ValueError("QWEN_WORKSPACE_ID_INVALID: expected a workspace DNS label")
        endpoint = ENDPOINT_TEMPLATE.format(WorkspaceId=workspace_id)
    return QwenConfiguration(validate_workspace_endpoint(endpoint))
