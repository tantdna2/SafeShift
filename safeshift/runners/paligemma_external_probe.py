"""Frozen external-probe parser candidate; not a production C1/B2 adapter."""

import re

from safeshift.protocol.schema import ParseResult, ProbePrediction, strict_json
from .paligemma import DECODING, loc_values_to_d4
from .paligemma_snapshot import MODEL_ID, REVISION

# Closed manifest-query -> bare-label lookup for native prompting and label checks.
# No free-form stripping, fuzzy matching or mutation of the frozen manifest.
QUERY_LABELS = {
    "Locate the red square.": "red square",
    "Locate the green circle.": "green circle",
    "Locate the yellow triangle.": "yellow triangle",
    "Locate the cyan rectangle.": "cyan rectangle",
}
LABELS = tuple(QUERY_LABELS.values())
_BOX = re.compile(r"<loc([0-9]{4})>" * 4 + r" (" + "|".join(LABELS) + r")<eos>")


def parse_probe(persisted, target_query):
    """One complete loc box + exact frozen label + EOS, only after persistence.

    Invalid output has no canonical value. A valid box with the wrong label is
    retained as native diagnostics and fails schema validation, never relabelled.
    """
    diagnostic = {"native_text": None, "decoded_text": None, "native_label": None,
                  "native_loc_values": None, "native_bbox": None,
                  "requested_label": QUERY_LABELS.get(target_query)}
    try:
        if target_query not in QUERY_LABELS:
            raise ValueError("FROZEN_QUERY_REQUIRED")
        obj = strict_json(persisted)
        diagnostic.update(native_text=obj.get("decoded_with_special_tokens"),
                          decoded_text=obj.get("decoded_text"))
        if (obj["model_id"] != MODEL_ID or obj["revision"] != REVISION
                or obj["schema_version"] != "paligemma-native-output-v1"
                or obj["decoding"] != DECODING):
            raise ValueError("NATIVE_ENVELOPE_IDENTITY")
        ids, prefix, full = obj["continuation_ids"], obj["input_token_ids"], obj["generated_ids_full"]
        if (type(ids) is not list or not 1 <= len(ids) <= DECODING["max_new_tokens"]
                or any(type(v) is not int or v < 0 for v in ids)
                or ids[-1] != 1 or 1 in ids[:-1]
                or type(prefix) is not list or not prefix
                or any(type(v) is not int or v < 0 for v in prefix)
                or type(full) is not list or len(full) != 1 or type(full[0]) is not list
                or any(type(v) is not int for v in full[0])
                or full != [prefix + ids]):
            raise ValueError("NATIVE_TOKEN_BOUNDARY")
        text = diagnostic["native_text"]
        if type(text) is not str or type(diagnostic["decoded_text"]) is not str:
            raise ValueError("NATIVE_TEXT_REQUIRED")
        match = _BOX.fullmatch(text)
        if match is None:
            raise ValueError("EXACT_SINGLE_BOX_GRAMMAR_REQUIRED")
        values = [int(v) for v in match.groups()[:4]]
        label = match.group(5)
        diagnostic.update(native_loc_values=values, native_label=label)
        if [v - 256000 for v in ids if 256000 <= v <= 257023] != values:
            raise ValueError("LOC_TEXT_TOKEN_MISMATCH")
        try:
            box = tuple(loc_values_to_d4(values))
        except ValueError:
            return ParseResult("COORDINATE_ERROR", errors=("INVALID_NATIVE_BOX_NO_REPAIR",)), diagnostic
        diagnostic["native_bbox"] = list(box)
        if label != QUERY_LABELS[target_query]:
            return ParseResult("SCHEMA_ERROR", errors=("TARGET_LABEL_MISMATCH_NO_CORRECTION",)), diagnostic
        return ParseResult("SUCCESS", ProbePrediction(box), response_schema_valid=True,
                           boxes_attempted=1, boxes_valid=1), diagnostic
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        return ParseResult("SCHEMA_ERROR", errors=("PARSER_FAIL_NO_REPAIR",)), diagnostic
