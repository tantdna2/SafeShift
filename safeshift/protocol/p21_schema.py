"""P2.1 classification format amendment; historical P2 parsing is unchanged.

Only a plain JSON object or one whole-response Markdown JSON fence is accepted.
Removing the wrapper is a format operation on a temporary text view, never on
the persisted native output. No label extraction or semantic repair is used.
"""

from dataclasses import dataclass

from .schema import Classification, SAFETY_LEVELS, fields, strict_json

PROTOCOL_VERSION = "P2.1"
PARSER_VERSION = "p21-strict-classification-v1"


@dataclass(frozen=True)
class P21ParseResult:
    status: str
    value: Classification | None = None
    format_wrapper_detected: bool = False
    errors: tuple[str, ...] = ()

    @property
    def success(self):
        return self.status == "SUCCESS"


def parse_classification(text):
    """Accept two exact representations under one strict JSON/schema rule.

    Fence markers must occupy separate lines with exactly three backticks,
    optionally followed by lowercase json on the opening line. ASCII
    JSON whitespace may surround the complete response. CRLF and LF line
    endings are supported. A detected opening wrapper stays diagnostic even
    when its content or closing structure is invalid.
    """
    wrapped = False
    try:
        if type(text) is not str:
            raise ValueError("CLASSIFICATION_TEXT_REQUIRED")
        payload = text.strip(" \t\r\n")
        lines = payload.replace("\r\n", "\n").split("\n")
        wrapped = lines[0] in ("```", "```json")
        if wrapped:
            if len(lines) < 3 or lines[-1] != "```":
                raise ValueError("ONE_COMPLETE_JSON_FENCE_REQUIRED")
            # Any additional code fence is forbidden, even inside a JSON
            # string. The allowed safety-level object cannot contain one.
            if any("```" in line for line in lines[1:-1]):
                raise ValueError("MULTIPLE_CODE_FENCES_FORBIDDEN")
            payload = "\n".join(lines[1:-1])
        obj = strict_json(payload)
        fields(obj, {"safety_level"})
        if type(obj["safety_level"]) is not str or obj["safety_level"] not in SAFETY_LEVELS:
            raise ValueError("CANONICAL_SAFETY_LEVEL_REQUIRED")
        return P21ParseResult("SUCCESS", Classification(obj["safety_level"]), wrapped)
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
        return P21ParseResult("INVALID", format_wrapper_detected=wrapped, errors=(str(exc),))
