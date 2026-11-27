"""Prompt and output contract for the CT1 evidence pilot. No model access."""

from dataclasses import dataclass
from pathlib import Path
import re

from safeshift.data.saved_reports import checked, sha256
from safeshift.fulltrain.qwen_semantics import LEVELS, fields, parse_classification, strict_json

ROOT = Path(__file__).resolve().parents[2]
C1 = Path("configs/pilot/classification_c1.txt")
C1_SHA256 = "816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3"
ARMS = ("A", "E", "S")
SCHEMA_ID = "safeshift-ct1-evidence-v1"
TEXT_MAX = 120
MAX_CUES = 3
EVIDENCE_STATUS = ("CUE_PRESENT", "NO_VISIBLE_HAZARD", "INSUFFICIENT")
REGIONS = ("upper_left", "upper_center", "upper_right", "middle_left", "center",
           "middle_right", "lower_left", "lower_center", "lower_right", "unknown")
VISIBILITY = ("clear", "partial", "unverifiable")
CONDITIONS = ("met", "not_met", "unknown")
RULE_SOURCES = ("general", "oil_chemical", "coal_conveyor", "tunnel", "power", "metallurgy", "unknown")

C1_END = (
    'Return only one JSON object with exactly the key "safety_level" and one of the four canonical '
    'values, for example {"safety_level":"Level01"}. Do not include descriptions, explanations, code fences '
    'or additional keys.'
)
INSTRUCTIONS = {
    "E": ("First locate and describe the visible cues. For each, check the factual conditions required "
          "by the relevant C1 rule before deciding the safety level. Use only the image and the rules above."),
    "S": ("Decide the safety level using the usual C1 assessment. Then record the visible cues and "
          "related details in the requested format. Use only the image and the rules above."),
}
FORMAT = """Return exactly one JSON object. Use these keys in this order: evidence_status, evidence, safety_level.
evidence_status: CUE_PRESENT when at least one clearly or partly visible hazard cue is reported; NO_VISIBLE_HAZARD only when the image supports no visible hazard (Level04, evidence []); INSUFFICIENT when the decisive cue or context cannot be verified.
evidence: an array of zero to three objects, each with cue (what is visible), region, visibility, condition (the fact needed to apply the rule), condition_status, rule_source, rule (the relevant C1 criterion in words), and rule_level.
region: upper_left, upper_center, upper_right, middle_left, center, middle_right, lower_left, lower_center, lower_right, or unknown.
visibility: clear, partial, or unverifiable. condition_status: met, not_met, or unknown.
rule_source: general, oil_chemical, coal_conveyor, tunnel, power, metallurgy, or unknown.
rule_level: Level01, Level02, or Level03 for the cited hazard criterion, or null if no criterion can be identified. Use rule_source unknown, rule "unknown" and rule_level null together. A cited rule can have an unmet or unknown condition. Use concise nonblank text (up to 120 characters each) for cue, condition and rule.
safety_level: one of Level01, Level02, Level03, Level04, assessed under the C1 criteria above.
Separate an unknown condition from a confirmed absence. Do not assert the presence of a hazard or a missing item solely because a relevant area is cropped or obscured. Do not infer industry from hidden metadata. No surrounding commentary.
"""


@dataclass(frozen=True)
class Parsed:
    status: str
    level: str | None = None
    evidence_status: str | None = None
    evidence: tuple[dict, ...] = ()
    wrapped: bool = False
    error: str | None = None


def prompt(arm, root=ROOT):
    original = checked((root / C1).read_bytes(), C1_SHA256)
    if arm == "A":
        return original
    text = original.decode("utf-8").rstrip("\n")
    marker = text.rsplit("\n", 1)[-1]
    if marker != C1_END:
        raise ValueError("could not find the frozen C1 output instruction")
    criteria = text[: -len(marker)]
    return (criteria + INSTRUCTIONS[arm] + "\n\n" + FORMAT).encode("utf-8")


def _enum(values):
    return {"enum": list(values)}


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


TEXT = {"type": "string", "minLength": 1, "maxLength": TEXT_MAX, "pattern": r"\S"}
ITEM = _object({
    "cue": TEXT, "region": _enum(REGIONS), "visibility": _enum(VISIBILITY), "condition": TEXT,
    "condition_status": _enum(CONDITIONS), "rule_source": _enum(RULE_SOURCES),
    "rule": TEXT, "rule_level": _enum((*LEVELS[:3], None)),
})
ITEM["allOf"] = [{
    "if": {"properties": {"rule_source": {"const": "unknown"}}},
    "then": {"properties": {"rule": {"const": "unknown"}, "rule_level": {"const": None}}},
    "else": {"properties": {"rule": {"not": {"const": "unknown"}}, "rule_level": _enum(LEVELS[:3])}},
}]
SCHEMA = _object({
    "evidence_status": _enum(EVIDENCE_STATUS),
    "evidence": {"type": "array", "maxItems": MAX_CUES, "items": ITEM},
    "safety_level": _enum(LEVELS),
})
SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
SCHEMA["allOf"] = [
    {"if": {"properties": {"evidence_status": {"const": "NO_VISIBLE_HAZARD"}}},
     "then": {"properties": {"safety_level": {"const": "Level04"}, "evidence": {"maxItems": 0}}}},
    {"if": {"properties": {"evidence_status": {"const": "CUE_PRESENT"}}},
     "then": {"properties": {"evidence": {"contains": {
         "properties": {"visibility": _enum(VISIBILITY[:2])}
     }}}}},
]


def _validate_entry(item):
    fields(item, set(ITEM["required"]))
    for key, schema in ITEM["properties"].items():
        value = item[key]
        if "enum" in schema:
            if value not in schema["enum"]:
                raise ValueError(f"invalid {key}")
        elif not isinstance(value, str) or not re.search(r"\S", value) or len(value) > TEXT_MAX:
            raise ValueError(f"invalid {key}")
    if item["rule_source"] == "unknown":
        if item["rule"] != "unknown" or item["rule_level"] is not None:
            raise ValueError("unknown rule source requires an unknown rule and null rule level")
    elif item["rule"] == "unknown" or item["rule_level"] is None:
        raise ValueError("known rule source requires a criterion and level")


def parse(arm, text):
    if arm == "A":
        result = parse_classification(text)
        return Parsed(result.status, result.value.safety_level if result.success else None,
                      wrapped=result.format_wrapper_detected, error=result.errors[0] if result.errors else None)
    if arm not in ARMS:
        raise ValueError("unknown CT1 arm")
    wrapped = False
    try:
        if type(text) is not str:
            raise ValueError("output must be text")
        payload = text.strip(" \t\r\n")
        lines = payload.replace("\r\n", "\n").split("\n")
        wrapped = lines[0] in ("\x60\x60\x60", "\x60\x60\x60json")
        if wrapped:
            if len(lines) < 3 or lines[-1] != "\x60\x60\x60" or any("\x60\x60\x60" in row for row in lines[1:-1]):
                raise ValueError("one complete JSON fence required")
            payload = "\n".join(lines[1:-1])
        result = strict_json(payload)
        fields(result, set(SCHEMA["required"]))
        level, status, entries = result["safety_level"], result["evidence_status"], result["evidence"]
        if level not in LEVELS or status not in EVIDENCE_STATUS:
            raise ValueError("invalid classification or evidence status")
        if not isinstance(entries, list) or len(entries) > MAX_CUES:
            raise ValueError("invalid evidence list")
        for entry in entries:
            _validate_entry(entry)
        if status == "NO_VISIBLE_HAZARD" and (entries or level != "Level04"):
            raise ValueError("no visible hazard requires Level04 and an empty list")
        if status == "CUE_PRESENT" and not any(e["visibility"] in VISIBILITY[:2] for e in entries):
            raise ValueError("cue present requires an at least partly visible cue")
        return Parsed("SUCCESS", level, status, tuple(entries), wrapped)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        return Parsed("INVALID", wrapped=wrapped, error=str(exc))


def prompt_hashes(arms):
    return {arm: sha256(prompt(arm)) for arm in arms}