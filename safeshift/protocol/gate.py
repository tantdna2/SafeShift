"""Offline external Target+Distractor sanity gate (D8 section 28).

IoU and area are diagnostics only. A near-full-image numerical boundary was
not approved: an explicit qualitative giant-box review is required for PASS.
"""

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Mapping

from .firewall import external_path
from .schema import BBox, ParseResult, ProbePrediction, bbox, fields, strict_json

CASE_SCHEMA_VERSION = "external-target-distractor-v1"


def center(box: BBox):
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def contains(box: BBox, point):
    # Boundary counts as inside, including for distractor exclusion.
    return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


def area(box: BBox):
    return (box[2] - box[0]) * (box[3] - box[1])


def intersection(a: BBox, b: BBox):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def iou(a: BBox, b: BBox):
    overlap = intersection(a, b)
    return overlap / (area(a) + area(b) - overlap)


@dataclass(frozen=True)
class ExternalCase:
    case_id: str
    image_path: str
    target_gt_bbox: BBox
    distractor_gt_bbox: BBox
    target_query: str
    swap_group: str


def validate_suite(repo: Path, cases: tuple[ExternalCase, ...]):
    if not cases:
        raise ValueError("external case suite must not be empty")
    ids, groups = set(), {}
    for case in cases:
        for value in (case.case_id, case.target_query, case.swap_group):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("case ID, query and swap group must be nonempty strings")
        if case.case_id in ids:
            raise ValueError("duplicate case ID")
        ids.add(case.case_id)
        external_path(repo, case.image_path)
        target, distractor = bbox(case.target_gt_bbox), bbox(case.distractor_gt_bbox)
        if intersection(target, distractor) != 0 or contains(target, center(distractor)):
            raise ValueError("target and distractor must be spatially separated")
        groups.setdefault(case.swap_group, []).append(case)
    for group in groups.values():
        if len({case.target_query for case in group}) != 1:
            raise ValueError("target query must remain fixed within a swap group")
        for case in group:
            # Every position needs an explicit reciprocal T/D case. This prevents
            # nominal position labels from claiming tracking without moving GT.
            if not any(other.case_id != case.case_id
                       and other.target_gt_bbox == case.distractor_gt_bbox
                       and other.distractor_gt_bbox == case.target_gt_bbox
                       and other.image_path != case.image_path for other in group):
                raise ValueError("each case requires a separate image with reciprocal target/distractor positions")


def load_cases(repo: Path, manifest_path: str) -> tuple[ExternalCase, ...]:
    path = external_path(repo, manifest_path)
    obj = strict_json(path.read_bytes())
    fields(obj, {"schema_version", "source_kind", "provenance", "cases"})
    if obj["schema_version"] != CASE_SCHEMA_VERSION:
        raise ValueError("unknown external case schema")
    if obj["source_kind"] not in ("synthetic", "open_external"):
        raise ValueError("only synthetic/open external cases are permitted")
    if not isinstance(obj["provenance"], str) or not obj["provenance"].strip():
        raise ValueError("case generation method or external source/license is required")
    if not isinstance(obj["cases"], list):
        raise ValueError("cases must be an array")
    cases = []
    for row in obj["cases"]:
        fields(row, {"case_id", "image_path", "target_gt_bbox", "distractor_gt_bbox", "target_query", "swap_group"})
        if not isinstance(row["image_path"], str):
            raise ValueError("image_path must be a relative string")
        cases.append(ExternalCase(**{**row, "target_gt_bbox": bbox(row["target_gt_bbox"]),
                                     "distractor_gt_bbox": bbox(row["distractor_gt_bbox"])}))
    result = tuple(cases)
    validate_suite(repo, result)
    return result


@dataclass(frozen=True)
class GiantBoxReview:
    status: str  # NO_GIANT, GIANT, or PENDING; no area cutoffs.
    reviewer: str
    rationale: str

    def __post_init__(self):
        if self.status not in ("NO_GIANT", "GIANT", "PENDING"):
            raise ValueError("unknown giant-box review status")
        if not isinstance(self.reviewer, str) or not isinstance(self.rationale, str):
            raise ValueError("reviewer and rationale must be strings")
        if self.status != "PENDING" and (not self.reviewer.strip() or not self.rationale.strip()):
            raise ValueError("completed qualitative review requires reviewer and rationale")


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    schema_valid: bool
    center_in_target: bool
    excludes_distractor_center: bool
    full_image: bool
    target_iou_diagnostic: float | None
    predicted_area_diagnostic: float | None
    parse_status: str
    giant_box_review: GiantBoxReview


@dataclass(frozen=True)
class GateResult:
    status: str  # PASS / FAIL / PENDING_REVIEW; not an automatic model-role mutation.
    systematic_tracking: bool
    cases: tuple[CaseResult, ...]
    errors: tuple[str, ...]


def evaluate_gate(repo: Path, cases: tuple[ExternalCase, ...],
                  predictions: Mapping[str, ParseResult],
                  reviews: Mapping[str, GiantBoxReview] | None = None) -> GateResult:
    validate_suite(repo, cases)
    reviews = reviews or {}
    ids = {case.case_id for case in cases}
    if set(predictions) - ids or set(reviews) - ids:
        raise ValueError("unknown case ID in predictions/reviews")
    rows, boxes = [], {}
    for case in cases:
        prediction = predictions.get(case.case_id)
        review = reviews.get(case.case_id, GiantBoxReview("PENDING", "", ""))
        valid = bool(prediction and prediction.success and isinstance(prediction.value, ProbePrediction))
        if valid:
            try:
                box = bbox(prediction.value.bbox)
            except ValueError:
                valid = False
        if not valid:
            rows.append(CaseResult(case.case_id, False, False, False, False, None, None,
                                   prediction.status if prediction else "MISSING_RESPONSE", review))
            continue
        boxes[case.case_id] = box
        rows.append(CaseResult(case.case_id, True, contains(case.target_gt_bbox, center(box)),
                               not contains(box, center(case.distractor_gt_bbox)), box == (0, 0, 1, 1),
                               iou(box, case.target_gt_bbox), area(box), prediction.status, review))
    tracking = len(boxes) == len(cases)
    for first, second in combinations(cases, 2):
        if first.swap_group != second.swap_group or first.target_gt_bbox == second.target_gt_bbox:
            continue
        if first.case_id not in boxes or second.case_id not in boxes:
            tracking = False
            continue
        a, b = center(boxes[first.case_id]), center(boxes[second.case_id])
        ta, tb = center(first.target_gt_bbox), center(second.target_gt_bbox)
        # Target motion in either axis must have the same sign in predictions.
        for axis in (0, 1):
            if ta[axis] != tb[axis] and (b[axis] - a[axis]) * (tb[axis] - ta[axis]) <= 0:
                tracking = False
    failed = not tracking or any(not row.schema_valid or not row.center_in_target
                                or not row.excludes_distractor_center or row.full_image
                                or row.giant_box_review.status == "GIANT" for row in rows)
    pending = any(row.giant_box_review.status == "PENDING" for row in rows)
    status = "FAIL" if failed else "PENDING_REVIEW" if pending else "PASS"
    errors = () if tracking else ("predictions do not track systematic target positions",)
    return GateResult(status, tracking, tuple(rows), errors)
