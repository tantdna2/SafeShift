"""Strict source-backed native subsets, fixed before any candidate output exists."""
import math
import re

from safeshift.protocol.schema import parse_text, strict_json

NUMBER = r"(?:0|[1-9]\d*)(?:\.\d+)?"
OVIS_BOX = rf"<box>\s*\(({NUMBER}),\s*({NUMBER})\),\s*\(({NUMBER}),\s*({NUMBER})\)\s*</box>"
PATCH_PAIR = r"<patch_index_(\d{4})><patch_index_(\d{4})>"
MULTI = "</delimiter_of_multi_objects/>"


def coordinates(values, *, exclusive=False):
    if not isinstance(values, (list, tuple)) or len(values) != 4:
        raise ValueError("FOUR_COORDINATES_REQUIRED")
    if any(type(v) not in (int, float) or not math.isfinite(v) or
           not (0 <= v < 1 if exclusive else 0 <= v <= 1) for v in values):
        raise ValueError("COORDINATE_RANGE")
    x0, y0, x1, y1 = values
    if not (x0 < x1 and y0 < y1):
        raise ValueError("COORDINATE_ORDER_OR_DEGENERATE")
    return list(map(float, values))  # identity [0,1) -> [0,1]; no clamp/reorder


def classification(text):
    result = parse_text(text, "classification")
    if not result.success:
        raise ValueError("STRICT_CLASSIFICATION_JSON_REQUIRED")
    return {"safety_level": result.value.safety_level}


def ovis(text, target):
    # Ref tag is optional on native answer, but if present must exactly bind target.
    prefix = f"<ref>{target}</ref>"
    if text.startswith(prefix):
        text = text[len(prefix):]
    box = re.fullmatch(OVIS_BOX, text)
    if box:
        matches = [box]
    else:
        grammar = rf"\[\s*{OVIS_BOX}(?:\s*,\s*{OVIS_BOX})*\s*\]"
        if not re.fullmatch(grammar, text):
            raise ValueError("OVIS_NATIVE_GRAMMAR")
        matches = list(re.finditer(OVIS_BOX, text))
    return [{"label": target, "bbox": coordinates([float(v) for v in m.groups()], exclusive=True)}
            for m in matches]


def plamo(text, target):
    # Both documented grammars are declared prospectively; neither salvages prose.
    if text.startswith("["):
        return [{"label": target, "bbox": coordinates(strict_json(text))}]
    rows = []
    for line in text.split("\n"):
        if not line.startswith(target + "["):
            raise ValueError("PLAMO_EXACT_LABEL_LINE_REQUIRED")
        rows.append({"label": target, "bbox": coordinates(strict_json(line[len(target):]))})
    if not rows:
        raise ValueError("NO_DOCUMENTED_ABSENCE")
    return rows


def patch_box(ul, lr):
    """Equivalent to Transformers 4.57.1 patch_index_to_coordinate (32x32).

    Same-row/column, including same-cell, uses cell edges; otherwise centers.
    Additional strict input/range/D4 validation never repairs reversed corners.
    """
    if type(ul) is not int or type(lr) is not int or not (0 <= ul <= 1023 and 0 <= lr <= 1023):
        raise ValueError("PATCH_INDEX_RANGE")
    x0, y0, x1, y1 = ul % 32, ul // 32, lr % 32, lr // 32
    if x0 == x1 or y0 == y1:
        values = (x0 / 32, y0 / 32, (x1 + 1) / 32, (y1 + 1) / 32)
    else:
        values = ((x0 + .5) / 32, (y0 + .5) / 32, (x1 + .5) / 32, (y1 + .5) / 32)
    return coordinates(values)


def kosmos(text, target):
    # Runtime removes the verified input token prefix BEFORE decoding, not by
    # matching text. Target phrase is then prompt-bound, as in official REC.
    prefix = f"<phrase>{target}</phrase>"
    if text.startswith(prefix):
        text = text[len(prefix):]
    grammar = rf"<object>{PATCH_PAIR}(?:{re.escape(MULTI)}{PATCH_PAIR})*</object>"
    if not re.fullmatch(grammar, text):
        raise ValueError("KOSMOS_NATIVE_GRAMMAR")
    return [{"label": target, "bbox": patch_box(int(a), int(b))}
            for a, b in re.findall(PATCH_PAIR, text)]


PARSERS = {"ovis": ovis, "plamo": plamo, "kosmos": kosmos}
