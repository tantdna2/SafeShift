"""Minimal image-level records, preserving the historical four safety labels.

Source: protocol/schema.py at 31a04e6 (see docs/ARCHITECTURE.md).
These are application records, not an InspecSafe annotation/file schema.
"""

from dataclasses import dataclass

from .validation import validate_identifier, validate_safety_level

SAFETY_LEVELS = ("Level01", "Level02", "Level03", "Level04")


@dataclass(frozen=True)
class SampleRecord:
    """One image's opaque source ID and authoritative ground-truth label."""

    sample_id: str
    true_safety_level: str

    def __post_init__(self):
        validate_identifier(self.sample_id, "sample_id")
        validate_safety_level(self.true_safety_level)


@dataclass(frozen=True)
class PredictionRecord:
    """Already parsed label; explicit None means INVALID, never Level04.

    A missing record/field is an error, not an implicit INVALID prediction.
    No parsing or inference is performed by this class.
    """

    sample_id: str
    predicted_safety_level: str | None

    def __post_init__(self):
        validate_identifier(self.sample_id, "sample_id")
        if self.predicted_safety_level is not None:
            validate_safety_level(self.predicted_safety_level)
