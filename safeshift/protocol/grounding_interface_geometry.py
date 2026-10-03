"""Pure v2 geometry diagnostics for synthetic tests, not a qualification runner.

These observations alone NEVER constitute PASS. Runtime/storage and absence
blockers and explicit human giant-box reviews remain separate mandatory gates.
"""

from .gate import area, center, contains, iou


def observe(case, parsed):
    targets, distractors = case["target_boxes"], case["distractor_boxes"]
    if parsed.status != "SUCCESS" or parsed.detections is None:
        return {"geometry_ok": False, "parse_status": parsed.status,
                "detections": None, "target_assignment": None}
    rows, assignment = [], []
    for detection in parsed.detections:
        box = detection.bbox
        matches = [i for i, target in enumerate(targets) if contains(target, center(box))]
        assignment.append(matches[0] if len(matches) == 1 else None)
        rows.append({"bbox": list(box), "label": detection.label,
                     "center_target_indices": matches,
                     "excludes_all_distractor_centers": all(
                         not contains(box, center(d)) for d in distractors),
                     "full_image": box == (0, 0, 1, 1),
                     "area_diagnostic": area(box),
                     "iou_diagnostic": [iou(box, target) for target in targets]})
    ok = (len(rows) == len(targets) and None not in assignment
          and len(set(assignment)) == len(targets)
          and all(row["label"] == case["target_label"]
                  and row["excludes_all_distractor_centers"] and not row["full_image"]
                  for row in rows))
    return {"geometry_ok": ok, "parse_status": parsed.status,
            "detections": rows, "target_assignment": assignment}


def systematic_tracking(cases, observations):
    groups = {}
    for case in cases:
        if case["swap_group"] is not None:
            groups.setdefault(case["swap_group"], []).append(case)
    if set(groups) != set("ABCD"):
        return False
    for pair in groups.values():
        if len(pair) != 2:
            return False
        first, second = pair
        if (first["target_label"] != second["target_label"]
                or first["target_boxes"] != second["distractor_boxes"]
                or second["target_boxes"] != first["distractor_boxes"]):
            return False
        values = [observations.get(c["case_id"]) for c in pair]
        if any(not v or not v["geometry_ok"] or len(v["detections"]) != 1 for v in values):
            return False
        a, b = (center(v["detections"][0]["bbox"]) for v in values)
        ta, tb = (center(c["target_boxes"][0]) for c in pair)
        if any(ta[axis] != tb[axis] and (b[axis] - a[axis]) * (tb[axis] - ta[axis]) <= 0
               for axis in (0, 1)):
            return False
    return True
