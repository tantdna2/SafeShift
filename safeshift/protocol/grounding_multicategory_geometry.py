"""Pure synthetic v3 observations; never award qualification PASS.

Geometry uses the existing center/distractor principle, with exact per-label
counts and bijections. IoU is diagnostic only. Human review remains mandatory.
"""

from .gate import area, center, contains, iou


def observe(case, parsed):
    labels, targets = case["query_labels"], case["targets"]
    expected = {label: sum(t["label"] == label for t in targets) for label in labels}
    if not targets or expected != case["expected_counts"]:
        raise ValueError("POSITIVE_CASE_WITH_EXACT_COUNTS_REQUIRED")
    if parsed.status != "SUCCESS" or not parsed.detections:
        return {"geometry_ok": False, "parse_status": parsed.status,
                "detections": None, "target_assignment": None,
                "expected_counts": expected, "predicted_counts": None}
    counts = {label: 0 for label in labels}
    rows, assignment = [], []
    for detection in parsed.detections:
        box, label = detection.bbox, detection.label
        if label in counts:
            counts[label] += 1
        matches = [i for i, target in enumerate(targets)
                   if label == target["label"] and contains(target["bbox"], center(box))]
        assignment.append(matches[0] if len(matches) == 1 else None)
        rows.append({"bbox": list(box), "label": label,
                     "center_target_indices": matches,
                     "excludes_all_distractor_centers": all(
                         not contains(box, center(d)) for d in case["distractor_boxes"]),
                     "full_image": tuple(box) == (0, 0, 1, 1),
                     "area_diagnostic": area(box),
                     "iou_diagnostic": [iou(box, t["bbox"]) for t in targets]})
    ok = (counts == expected and len(rows) == len(targets)
          and None not in assignment and len(set(assignment)) == len(targets)
          and all(r["excludes_all_distractor_centers"] and not r["full_image"]
                  for r in rows))
    return {"geometry_ok": ok, "parse_status": parsed.status,
            "detections": rows, "target_assignment": assignment,
            "expected_counts": expected, "predicted_counts": counts}


def systematic_tracking(cases, observations):
    groups = {}
    for case in cases:
        if case["swap_group"] is not None:
            groups.setdefault(case["swap_group"], []).append(case)
    if set(groups) != set("ABCD"):
        return False
    for pair in groups.values():
        if len(pair) != 2 or any(len(c["targets"]) != 1 for c in pair):
            return False
        first, second = pair
        a, b = first["targets"][0], second["targets"][0]
        if (a["label"] != b["label"] or [a["bbox"]] != second["distractor_boxes"]
                or [b["bbox"]] != first["distractor_boxes"]):
            return False
        values = [observations.get(c["case_id"]) for c in pair]
        if any(not v or not v["geometry_ok"] or len(v["detections"]) != 1 for v in values):
            return False
        pa, pb = (center(v["detections"][0]["bbox"]) for v in values)
        ta, tb = center(a["bbox"]), center(b["bbox"])
        if any(ta[i] != tb[i] and (pb[i] - pa[i]) * (tb[i] - ta[i]) <= 0
               for i in (0, 1)):
            return False
    return True
