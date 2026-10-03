"""D9R19G1 offline candidates, never registered as production adapters.

Inputs are exact tokenizer-decoded continuations AFTER durable raw-envelope
preservation. No model, storage, GT, case ID or historical result is consulted.
Source pins and deliberately strict subsets are in the D9R19G1 PREP note.
"""

from dataclasses import dataclass
import math
import re

from .schema import Evidence, strict_json

VERSION = "grounding-interface-candidate-v2.0"
QWEN_ABSENCE = "QWEN3_ABSENCE_SEMANTICS_BLOCKER"
PALI_ABSENCE = "PALIGEMMA_ABSENCE_SEMANTICS_BLOCKER"
QWEN_PROMPT_ID = "qwen3-native-every-instance-v2.0"
PALI_PROMPT_ID = "paligemma-native-detect-v2.0"
QWEN_PROMPT = ('Locate every instance that belongs to the following categories: '
               '"{label}". Report bbox coordinates in JSON format.')


@dataclass(frozen=True)
class NativeDetections:
    status: str
    # None is invalid/blocked; an empty tuple must never substitute for failure.
    detections: tuple[Evidence, ...] | None = None
    error: str | None = None


def _label(label):
    # Future exact query labels can be supplied without inventing hazard aliases.
    if (type(label) is not str or not label or label != label.strip()
            or any(c in label for c in '\r\n\t";<>\\')
            or any(ord(c) < 32 for c in label)):
        raise ValueError("EXACT_QUERY_LABEL_REQUIRED")


def prompt(model, label):
    _label(label)
    if model == "qwen3":
        return QWEN_PROMPT.format(label=label)
    if model == "paligemma":
        # Pass this payload to PaliGemmaProcessor; it appends exactly one LF.
        return "detect " + label
    raise ValueError("UNKNOWN_CANDIDATE")


def _box(values, scale, maximum, order):
    if (type(values) is not list or len(values) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v)
                   or not 0 <= v <= maximum for v in values)):
        raise ValueError("INVALID_COORDINATES")
    result = tuple(values[i] / scale for i in order)
    if not (result[0] < result[2] and result[1] < result[3]):
        raise ValueError("INVALID_GEOMETRY")
    return result


def parse_qwen3(text, *, label):
    """Exact JSON array of {bbox_2d, label}; fixed /1000, no fencing/repair."""
    _label(label)
    if type(text) is not str:
        return NativeDetections("INVALID", error="TEXT_REQUIRED")
    try:
        items = strict_json(text)
        if type(items) is not list:
            raise ValueError("NATIVE_ARRAY_REQUIRED")
        if not items:
            return NativeDetections("BLOCKED", error=QWEN_ABSENCE)
        detections = []
        for item in items:
            if type(item) is not dict or set(item) != {"bbox_2d", "label"}:
                raise ValueError("EXACT_NATIVE_FIELDS_REQUIRED")
            if item["label"] != label:
                raise ValueError("EXACT_NATIVE_LABEL_REQUIRED")
            detections.append(Evidence(_box(item["bbox_2d"], 1000, 1000,
                                            (0, 1, 2, 3)), item["label"]))
        return NativeDetections("SUCCESS", tuple(detections))
    except (ValueError, TypeError, OverflowError, RecursionError):
        return NativeDetections("INVALID", error="PARSER_FAIL_NO_REPAIR")


def parse_paligemma(text, *, label):
    """Exact detection-only subset of official extract_objs grammar.

    Four adjacent ASCII loc tokens, one space, exact label; detections separated
    by '; ' or ' ; '. No segmentation, prefix/suffix prose or trailing separator.
    Use decoded_text (special tokens skipped by tokenizer, cleanup disabled).
    Never strip EOS/whitespace here, salvage regex matches or rename labels.
    """
    _label(label)
    if type(text) is not str:
        return NativeDetections("INVALID", error="TEXT_REQUIRED")
    if text == "":
        return NativeDetections("BLOCKED", error=PALI_ABSENCE)
    pattern = re.compile(r"<loc([0-9]{4})>" * 4 + " " + re.escape(label))
    detections = []
    try:
        for item in re.split(r" ?; ", text):
            match = pattern.fullmatch(item)
            if match is None:
                raise ValueError("EXACT_NATIVE_GRAMMAR_REQUIRED")
            values = [int(v) for v in match.groups()]
            detections.append(Evidence(_box(values, 1024, 1023, (1, 0, 3, 2)), label))
        return NativeDetections("SUCCESS", tuple(detections))
    except ValueError:
        return NativeDetections("INVALID", error="PARSER_FAIL_NO_REPAIR")
