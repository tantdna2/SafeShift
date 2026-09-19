"""Canonical P2 records and strict deterministic validation (D4/D8)."""

from dataclasses import dataclass
import json
import math
from typing import Literal

SAFETY_LEVELS = ("Level01", "Level02", "Level03", "Level04")
# D6, notes/w2_grounding_census_decision_brief.md section 5.2; order preserved.
HAZARDS = (
    "NO_GLOVES", "NO_HELMET", "NO_MASK", "USE_MOBILE_PHONE",
    "LIQUID_ON_GROUND", "SMOKING", "OPEN_FLAME", "FOREIGN_OBJECT",
    "SMOKE", "NONMOTORIZED_VEHICLE", "DOOR_OPEN", "PERSON_FALLEN",
)
Task = Literal["classification", "grounding", "external_probe"]
BBox = tuple[float, float, float, float]


def strict_json(raw: str | bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f"non-finite JSON constant: {value}")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)


def bbox(value, convention: str = "xyxy_1") -> BBox:
    """D8 normalization: reorder, scale, clamp, then validate strict geometry."""
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError("bbox must contain exactly four numbers")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in value):
        raise ValueError("bbox coordinates must be finite numbers, not booleans or strings")
    if convention not in ("xyxy_1", "xyxy_1000", "yxyx_1000"):
        raise ValueError("unknown coordinate convention")
    scale = 1 if convention == "xyxy_1" else 1000
    order = (1, 0, 3, 2) if convention == "yxyx_1000" else (0, 1, 2, 3)
    x0, y0, x1, y1 = (min(1.0, max(0.0, value[i] / scale)) for i in order)
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise ValueError("bbox must satisfy 0 <= xmin < xmax <= 1 and 0 <= ymin < ymax <= 1")
    return x0, y0, x1, y1


def fields(value, required: set[str], optional: set[str] = frozenset()):
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - optional:
        raise ValueError(f"expected fields {sorted(required)}; optional {sorted(optional)}")


@dataclass(frozen=True)
class Evidence:
    bbox: BBox
    label: str | None = None


@dataclass(frozen=True)
class Hazard:
    hazard_type: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class Classification:
    safety_level: str


@dataclass(frozen=True)
class Grounding:
    hazards: tuple[Hazard, ...]


@dataclass(frozen=True)
class ProbePrediction:
    bbox: BBox


@dataclass(frozen=True)
class ParseResult:
    status: str
    value: Classification | Grounding | ProbePrediction | None = None
    errors: tuple[str, ...] = ()
    response_schema_valid: bool = False
    boxes_attempted: int | None = None
    boxes_valid: int = 0
    # Diagnostic only: never substitute these for a failed response in E2E.
    diagnostic_evidence: tuple[Evidence, ...] = ()
    raw_artifact: str | None = None

    @property
    def success(self) -> bool:
        return self.status == "SUCCESS"


def parse_text(text: str, task: Task, convention: str = "xyxy_1") -> ParseResult:
    """Parse one JSON object with D8 bbox normalization; no regex or label repair."""
    if task not in ("classification", "grounding", "external_probe"):
        raise ValueError("unknown task")
    try:
        obj = strict_json(text)
    except (ValueError, UnicodeError, RecursionError) as exc:
        return ParseResult("JSON_ERROR", errors=(str(exc),))
    try:
        if task == "classification":
            fields(obj, {"safety_level"})
            if obj["safety_level"] not in SAFETY_LEVELS:
                raise ValueError("unknown safety_level")
            return ParseResult("SUCCESS", Classification(obj["safety_level"]), response_schema_valid=True)
        if task == "external_probe":
            fields(obj, {"bbox"})
            items = [(None, [{"bbox": obj["bbox"]}])]
        else:
            fields(obj, {"hazards"})
            if not isinstance(obj["hazards"], list):
                raise ValueError("hazards must be an array")
            items = []
            for hazard in obj["hazards"]:
                fields(hazard, {"hazard_type", "evidence"})
                if hazard["hazard_type"] not in HAZARDS:
                    raise ValueError("hazard_type outside approved closed vocabulary")
                if not isinstance(hazard["evidence"], list):
                    raise ValueError("evidence must be an array")
                items.append((hazard["hazard_type"], hazard["evidence"]))
        for _, evidence in items:
            for item in evidence:
                fields(item, {"bbox"}, {"label"})
                if "label" in item and not isinstance(item["label"], str):
                    raise ValueError("label must be a string")
    except (ValueError, TypeError) as exc:
        return ParseResult("SCHEMA_ERROR", errors=(str(exc),))

    errors, valid, hazards = [], [], []
    attempted = sum(len(evidence) for _, evidence in items)
    for hazard_type, evidence in items:
        parsed = []
        for i, item in enumerate(evidence):
            try:
                parsed.append(Evidence(bbox(item["bbox"], convention), item.get("label")))
            except (ValueError, OverflowError) as exc:
                errors.append(f"{hazard_type or 'probe'} evidence[{i}]: {exc}")
        valid.extend(parsed)
        if hazard_type is not None:
            hazards.append(Hazard(hazard_type, tuple(parsed)))
    if errors:
        return ParseResult("COORDINATE_ERROR", errors=tuple(errors), response_schema_valid=True,
                           boxes_attempted=attempted, boxes_valid=len(valid), diagnostic_evidence=tuple(valid))
    value = ProbePrediction(valid[0].bbox) if task == "external_probe" else Grounding(tuple(hazards))
    return ParseResult("SUCCESS", value, response_schema_valid=True,
                       boxes_attempted=attempted, boxes_valid=len(valid), diagnostic_evidence=tuple(valid))
