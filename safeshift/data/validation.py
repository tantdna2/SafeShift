"""Strict in-memory validation without reading files or repairing values."""

from collections.abc import Iterable, Mapping
from pathlib import PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schema import PredictionRecord, SampleRecord


def validate_text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")


def validate_identifier(value: str, field: str) -> None:
    validate_text(value, field)
    if value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(f"{field} must not contain surrounding whitespace or control characters")


def validate_safety_level(value: str) -> None:
    from .schema import SAFETY_LEVELS

    if not isinstance(value, str) or value not in SAFETY_LEVELS:
        raise ValueError("expected a canonical Level01-Level04 label")


def validate_relative_path(value: str, field: str) -> None:
    """Require portable repository-relative POSIX spelling; do not touch disk."""
    validate_identifier(value, field)
    posix, windows = PurePosixPath(value), PureWindowsPath(value)
    if (posix.is_absolute() or windows.drive or windows.root or "\\" in value
            or ".." in posix.parts or posix.as_posix() != value or value == "."):
        raise ValueError(f"{field} must be a normalized repository-relative POSIX path")


def _fields(record: Mapping, required: set[str]) -> None:
    if not isinstance(record, Mapping) or set(record) != required:
        raise ValueError(f"expected exactly these fields: {sorted(required)}")


def sample_from_mapping(record: Mapping) -> "SampleRecord":
    from .schema import SampleRecord

    _fields(record, {"sample_id", "true_safety_level"})
    return SampleRecord(**record)


def prediction_from_mapping(record: Mapping) -> "PredictionRecord":
    from .schema import PredictionRecord

    _fields(record, {"sample_id", "predicted_safety_level"})
    return PredictionRecord(**record)


def _unique_records(records, record_type):
    rows = tuple(records)
    seen = set()
    for row in rows:
        if not isinstance(row, record_type):
            raise ValueError(f"expected {record_type.__name__} records")
        if row.sample_id in seen:
            raise ValueError(f"duplicate sample_id: {row.sample_id}")
        seen.add(row.sample_id)
    return rows


def validate_samples(records: Iterable["SampleRecord"]) -> tuple["SampleRecord", ...]:
    from .schema import SampleRecord

    return _unique_records(records, SampleRecord)


def validate_predictions(records: Iterable["PredictionRecord"]) -> tuple["PredictionRecord", ...]:
    from .schema import PredictionRecord

    return _unique_records(records, PredictionRecord)
