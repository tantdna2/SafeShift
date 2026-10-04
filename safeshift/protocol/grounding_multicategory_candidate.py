"""Offline v3 positive-guaranteed candidate; NOT a production adapter.

Only consume continuations after durable raw persistence. No GT, image identity,
model calls, retries, repair, or historical-output special cases live here.
"""

from dataclasses import dataclass
import math
import re

from .schema import Evidence, strict_json

VERSION = "grounding-multicategory-candidate-v3.0"
POSITIVE_GUARANTEE_MISS = "POSITIVE_GUARANTEE_MISS"
HAZARD_QUERY_MAP = (
    ("NO_GLOVES", "person without gloves"),
    ("NO_HELMET", "person without helmet"),
    ("NO_MASK", "person without mask"),
    ("USE_MOBILE_PHONE", "person using mobile phone"),
    ("LIQUID_ON_GROUND", "liquid on ground"),
    ("SMOKING", "person smoking"),
    ("OPEN_FLAME", "open flame"),
    ("FOREIGN_OBJECT", "foreign object"),
    ("SMOKE", "smoke"),
    ("NONMOTORIZED_VEHICLE", "non-motorized vehicle"),
    ("DOOR_OPEN", "open door"),
    ("PERSON_FALLEN", "fallen person"),
)
HAZARD_LABELS = tuple(label for _, label in HAZARD_QUERY_MAP)
QWEN_PROMPT = ("Locate every instance that belongs to the following categories: "
               "'{obj_names}'. Report bbox coordinates in JSON format.")


@dataclass(frozen=True)
class NativeDetections:
    status: str
    detections: tuple[Evidence, ...] | None = None
    error: str | None = None


def query_labels(labels):
    """Require an ordered, nonempty, unique exact closed vocabulary."""
    if type(labels) not in (list, tuple) or not labels:
        raise ValueError("ORDERED_CLOSED_LABEL_SET_REQUIRED")
    for label in labels:
        if (type(label) is not str or not label or label != label.strip()
                or any(c in label for c in '\r\n\t\"\';,<>\\')
                or any(ord(c) < 32 for c in label)):
            raise ValueError("EXACT_QUERY_LABEL_REQUIRED")
    if len(set(labels)) != len(labels):
        raise ValueError("DUPLICATE_QUERY_LABEL")
    return tuple(labels)


def prompt(model, labels):
    labels = query_labels(labels)
    if model == "qwen3":
        return QWEN_PROMPT.format(obj_names=", ".join(labels))
    if model == "paligemma":
        # PaliGemmaProcessor owns the single final LF; do not append it here.
        return "detect " + " ; ".join(labels)
    raise ValueError("UNKNOWN_CANDIDATE")


def hazard_prompt(model):
    """Every prospective pool image gets exactly this full ordered query."""
    return prompt(model, HAZARD_LABELS)


def hazard_id(native_label):
    """Exact binding only; does not perform D5 scoring or drop unsupported atoms."""
    return dict((label, hazard) for hazard, label in HAZARD_QUERY_MAP)[native_label]


def _box(values, scale, maximum, order):
    if (type(values) is not list or len(values) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v)
                   or not 0 <= v <= maximum for v in values)):
        raise ValueError("INVALID_COORDINATES")
    box = tuple(values[i] / scale for i in order)
    if not (box[0] < box[2] and box[1] < box[3]):
        raise ValueError("INVALID_GEOMETRY")
    return box


def parse_qwen3_multicategory(text, allowed_labels):
    labels = query_labels(allowed_labels)
    if type(text) is not str:
        return NativeDetections("INVALID", error="TEXT_REQUIRED")
    if text == "":
        return NativeDetections(POSITIVE_GUARANTEE_MISS)
    try:
        items = strict_json(text)
        if type(items) is not list:
            raise ValueError("NATIVE_ARRAY_REQUIRED")
        if not items:
            return NativeDetections(POSITIVE_GUARANTEE_MISS)
        detections = []
        for item in items:
            if type(item) is not dict or set(item) != {"bbox_2d", "label"}:
                raise ValueError("EXACT_NATIVE_FIELDS_REQUIRED")
            if type(item["label"]) is not str or item["label"] not in labels:
                raise ValueError("EXACT_NATIVE_LABEL_REQUIRED")
            detections.append(Evidence(_box(item["bbox_2d"], 1000, 1000,
                                            (0, 1, 2, 3)), item["label"]))
        return NativeDetections("SUCCESS", tuple(detections))
    except (ValueError, TypeError, OverflowError, RecursionError):
        return NativeDetections("INVALID", error="PARSER_FAIL_NO_REPAIR")


def parse_paligemma_multicategory(text, allowed_labels):
    """Strict full-consumption subset of audited official detection grammar.

    Four ASCII loc tokens, one space, exact label; '; ' or ' ; ' separators.
    No unmatched-text salvage, EOS stripping, segmentation, or whitespace repair.
    """
    labels = query_labels(allowed_labels)
    if type(text) is not str:
        return NativeDetections("INVALID", error="TEXT_REQUIRED")
    if text == "":
        return NativeDetections(POSITIVE_GUARANTEE_MISS)
    pattern = re.compile(r"<loc([0-9]{4})>" * 4 + " (" +
                         "|".join(re.escape(label) for label in labels) + ")")
    try:
        detections = []
        for item in re.split(r" ?; ", text):
            match = pattern.fullmatch(item)
            if match is None:
                raise ValueError("EXACT_NATIVE_GRAMMAR_REQUIRED")
            values = [int(v) for v in match.groups()[:4]]
            detections.append(Evidence(_box(values, 1024, 1023, (1, 0, 3, 2)),
                                       match.group(5)))
        return NativeDetections("SUCCESS", tuple(detections))
    except ValueError:
        return NativeDetections("INVALID", error="PARSER_FAIL_NO_REPAIR")
