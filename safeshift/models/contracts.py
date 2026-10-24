"""Model-neutral transport interfaces, not production prompt/decoding contracts.

    Paths refer to artifacts persisted by a future authorized runner. Validation
    checks their spelling only; it neither creates nor verifies those artifacts.
"""

from dataclasses import dataclass
from typing import Protocol

from safeshift.data.validation import validate_identifier, validate_relative_path, validate_text


@dataclass(frozen=True)
class ModelInput:
    sample_id: str
    image_path: str
    prompt: str

    def __post_init__(self):
        validate_identifier(self.sample_id, "sample_id")
        validate_relative_path(self.image_path, "image_path")
        validate_text(self.prompt, "prompt")


@dataclass(frozen=True)
class ModelOutput:
    """Receipt references after raw output and configuration have been persisted.

    No parsed prediction/score is substituted for the raw output artifact.
    Runner must enforce input/output ID linkage and raw-before-parse ordering.
    """

    sample_id: str
    run_id: str
    model_id: str
    model_revision: str
    raw_output_path: str
    prompt_path: str
    generation_config_path: str

    def __post_init__(self):
        for field in ("sample_id", "run_id", "model_id", "model_revision"):
            validate_identifier(getattr(self, field), field)
        for field in ("raw_output_path", "prompt_path", "generation_config_path"):
            validate_relative_path(getattr(self, field), field)


class VisionLanguageModel(Protocol):
    """Type interface only. No concrete implementation ships in Foundation V1."""

    def generate(self, request: ModelInput) -> ModelOutput: ...
