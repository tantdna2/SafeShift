"""D9R12 offline string parsers; not registered as production adapters.

Inputs are the approved decoded fields after raw preservation. This module does
not load models, read bundles, qualify interfaces or evaluate target presence.
SUCCESS means candidate syntax only, including a hallucinated negative-case box.
"""

from dataclasses import dataclass
import re

from safeshift.protocol.schema import Evidence
from .contracts import ParseStatus
from .paligemma import loc_values_to_d4

PRESENCE_PROMPT = "answer en Is there a red square in the image?"
GROUNDING_PROMPT = "detect red square"
PRESENCE_SCOPE = "PRESENCE_QUERY_CANDIDATE"
GROUNDING_SCOPE = "SINGLE_RED_SQUARE_GROUNDING_CANDIDATE"
_GROUNDING = re.compile(r"<loc([0-9]{4})>" * 4 + r" red square<eos>")


@dataclass(frozen=True)
class PresenceAnswer:
    """Explicit yes/no presence mapping, unrelated to production safety levels."""

    answer: str
    present: bool


@dataclass(frozen=True)
class CandidateParseResult:
    """Separate from production AdaptedOutput/Classification and metric inputs."""

    scope: str
    parse_status: ParseStatus
    value: PresenceAnswer | Evidence | None = None
    error: str | None = None


def parse_presence_answer_candidate(decoded_text, *, prompt):
    """Exact decoded_text yes/no only; no EOS, case or whitespace normalization."""
    if (type(prompt) is not str or prompt != PRESENCE_PROMPT
            or type(decoded_text) is not str or decoded_text not in ("yes", "no")):
        return CandidateParseResult(PRESENCE_SCOPE, ParseStatus.INVALID,
                                    error="INVALID_CLASSIFICATION_OUTPUT")
    return CandidateParseResult(PRESENCE_SCOPE, ParseStatus.SUCCESS,
                                PresenceAnswer(decoded_text, decoded_text == "yes"))


def parse_grounding_candidate(decoded_with_special_tokens, *, prompt):
    """One observed label, four ASCII loc integers and EOS; no empty grammar.

    No fixture/expected-target argument: semantic correctness cannot alter parsing.
    D4 Evidence retains the label without inventing a production hazard class.
    """
    if (type(prompt) is not str or prompt != GROUNDING_PROMPT
            or type(decoded_with_special_tokens) is not str):
        return CandidateParseResult(GROUNDING_SCOPE, ParseStatus.INVALID,
                                    error="PARSER_FAIL_NO_REPAIR")
    match = _GROUNDING.fullmatch(decoded_with_special_tokens)
    if match is not None:
        try:
            box = loc_values_to_d4([int(v) for v in match.groups()])
        except ValueError:
            pass
        else:
            return CandidateParseResult(GROUNDING_SCOPE, ParseStatus.SUCCESS,
                                        Evidence(tuple(box), "red square"))
    return CandidateParseResult(GROUNDING_SCOPE, ParseStatus.INVALID,
                                error="PARSER_FAIL_NO_REPAIR")
