"""D9R13 qualification-only adapter to existing canonical types.

No production registration, task schema, target/GT input, label inference, output
repair or qualification decision. Call only after verified raw persistence.
"""

from dataclasses import asdict
import re

from safeshift.protocol.schema import HAZARDS, parse_text, strict_json
from .contracts import AdaptedOutput, ParseStatus, SpatialKind, Task
from .paligemma import DECODING, loc_values_to_d4
from .paligemma_snapshot import MODEL_ID, REVISION

_BOX = re.compile(r"<loc([0-9]{4})>" * 4 + r" (" + "|".join(HAZARDS) + r")")


def adapt_persisted(raw, task):
    """Exact canonical JSON or native loc groups carrying exact D6 hazard IDs.

    The same unmodified canonical grounding prompt is used for all three calls.
    Native loc syntax is an acceptance candidate, not an observed capability.
    An EOS-only/empty response never becomes an empty hazards array.
    """
    task = Task(task)
    spatial = task == Task.GROUNDING
    invalid = AdaptedOutput(ParseStatus.INVALID,
                            spatial_kind=SpatialKind.MALFORMED if spatial else SpatialKind.NOT_APPLICABLE)
    try:
        obj = strict_json(raw)
        if (obj["model_id"] != MODEL_ID or obj["revision"] != REVISION
                or obj["schema_version"] != "paligemma-native-output-v1"
                or obj["decoding"] != DECODING):
            return invalid
        ids = obj["continuation_ids"]
        text = obj["decoded_text"]
        special = obj["decoded_with_special_tokens"]
        if (not isinstance(ids, list) or not ids or len(ids) > DECODING["max_new_tokens"]
                or any(type(v) is not int or v < 0 for v in ids)
                or ids[-1] != 1 or 1 in ids[:-1]
                or type(text) is not str or type(special) is not str):
            return invalid
        loc_ids = [v - 256000 for v in ids if 256000 <= v <= 257023]
        if special == text + "<eos>" and not loc_ids:
            # Reject out-of-bounds values BEFORE canonical parse_text's generic
            # D8 clamp. No PaliGemma response is ever clamped or repaired.
            value = strict_json(text)
            if spatial and isinstance(value, dict) and isinstance(value.get("hazards"), list):
                for hazard in value["hazards"]:
                    for item in hazard["evidence"]:
                        box = item["bbox"]
                        if (not isinstance(box, list) or len(box) != 4
                                or any(type(v) not in (int, float) or not 0 <= v <= 1 for v in box)):
                            return invalid
            parsed = parse_text(text, task.value)
        elif spatial and special.endswith("<eos>"):
            # Complete, fixed grammar only; no search/substrings or partial boxes.
            groups = special[:-5].split(" ; ")
            hazards, decoded_locs = [], []
            for group in groups:
                match = _BOX.fullmatch(group)
                if match is None:
                    return invalid
                locs = [int(v) for v in match.groups()[:4]]
                decoded_locs.extend(locs)
                hazards.append({"hazard_type": match.group(5),
                                "evidence": [{"bbox": loc_values_to_d4(locs)}]})
            if decoded_locs != loc_ids:
                return invalid
            import json
            parsed = parse_text(json.dumps({"hazards": hazards}), "grounding")
        else:
            return invalid
        if not parsed.success:
            return invalid
        return AdaptedOutput(ParseStatus.SUCCESS, parsed.value,
                             SpatialKind.NATIVE_BOX if spatial else SpatialKind.NOT_APPLICABLE)
    except (ValueError, TypeError, KeyError, IndexError, RecursionError):
        return invalid


def observation(persisted, task):
    """Keep raw native evidence and canonical mapping side by side for review."""
    adapted = adapt_persisted(persisted, task)
    adapted.validate(Task(task))
    canonical = asdict(adapted.value) if adapted.value is not None else None
    if canonical is not None and Task(task) == Task.GROUNDING:
        for hazard in canonical["hazards"]:
            for evidence in hazard["evidence"]:
                # Evidence.label is optional string metadata; canonical JSON
                # must omit an absent label instead of serializing null.
                if evidence.get("label") is None:
                    evidence.pop("label", None)
    return {"native_output": strict_json(persisted),
            "parse_status": adapted.parse_status.value,
            "canonical_output": canonical,
            "spatial_kind": adapted.spatial_kind.value,
            "compatible_mapping_observed": adapted.parse_status == ParseStatus.SUCCESS,
            "qualification_decision": "RESEARCH_LEAD_REVIEW_REQUIRED"}
