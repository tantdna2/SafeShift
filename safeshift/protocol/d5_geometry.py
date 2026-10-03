"""Deterministic geometry and optimal bipartite matching; no model dependencies."""

import math


def valid_box(box):
    if (len(box) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in box)
            or not 0 <= box[0] < box[2] <= 1 or not 0 <= box[1] < box[3] <= 1):
        raise ValueError("finite normalized xyxy required; no coordinate repair")
    return tuple(box)


def area(box):
    return (box[2] - box[0]) * (box[3] - box[1])


def iou(a, b):
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0, min(a[3], b[3]) - max(a[1], b[1]))
    return intersection / (area(a) + area(b) - intersection)


def polygon(region):
    if region.coordinate_frame not in {"original_pixels", "normalized"}:
        raise ValueError("explicit original_pixels or normalized frame required")
    if region.image_width <= 0 or region.image_height <= 0:
        raise ValueError("positive image dimensions required")
    points = region.original_polygon
    if len(points) < 3 or any(len(p) != 2 or any(
            type(v) not in (int, float) or not math.isfinite(v) for v in p) for p in points):
        raise ValueError("finite original polygon required")
    if region.coordinate_frame == "original_pixels":
        points = tuple((x / region.image_width, y / region.image_height) for x, y in points)
    if any(not 0 <= v <= 1 for p in points for v in p) or polygon_area(points) <= 0:
        raise ValueError("nondegenerate polygon inside image required")
    return points


def polygon_area(points):
    return abs(sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(points, points[1:] + points[:1]))) / 2


def contains(point, points):
    """Ray crossing, with boundary included; uses the original polygon."""
    x, y = point
    inside = False
    for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1]):
        cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
        if abs(cross) <= 1e-14 and min(ax, bx) <= x <= max(ax, bx) and min(ay, by) <= y <= max(ay, by):
            return True
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            inside = not inside
    return inside


def pointing(box, regions):
    center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
    return any(contains(center, polygon(r)) for r in regions)


def containment(box, region):
    """Polygon/box intersection area divided by predicted area (D5 decision §12)."""
    points = list(polygon(region))
    for axis, bound, lower in ((0, box[0], True), (0, box[2], False),
                               (1, box[1], True), (1, box[3], False)):
        clipped = []
        for a, b in zip(points, points[1:] + points[:1]):
            ina = a[axis] >= bound if lower else a[axis] <= bound
            inb = b[axis] >= bound if lower else b[axis] <= bound
            if ina != inb:
                t = (bound - a[axis]) / (b[axis] - a[axis])
                clipped.append(tuple(a[k] + t * (b[k] - a[k]) for k in (0, 1)))
            if inb:
                clipped.append(b)
        points = clipped
    return polygon_area(points) / area(box)


def assignment(weights, *, threshold=None):
    """Rows=GT atoms, columns=predictions; None forbids a cross-class edge.

    Hungarian assignment with one dummy per row. Mode A maximizes total IoU.
    Mode B adds n+1 per valid edge, dominating every possible IoU tie-break.
    Stable iteration order resolves otherwise equal optima deterministically.
    """
    if threshold not in (None, .25, .5):
        raise ValueError("only prospectively approved thresholds")
    n = len(weights)
    if not n:
        return ()
    p = len(weights[0])
    if any(len(row) != p for row in weights):
        raise ValueError("rectangular weights required")
    for row in weights:
        if any(w is not None and (type(w) not in (float, int) or not math.isfinite(w) or not 0 <= w <= 1) for w in row):
            raise ValueError("finite IoU edge required")
    allowed = lambda w: w is not None and (threshold is None or w >= threshold)
    costs = [[-(w + (n + 1 if threshold is not None else 0)) if allowed(w)
              else float(n + 2) for w in row] + [0.] * n for row in weights]
    m = p + n
    u, v, match, way = [0.] * (n + 1), [0.] * (m + 1), [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        match[0] = i
        j0 = 0
        minimum, used = [math.inf] * (m + 1), [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = match[j0], math.inf, 0
            for j in range(1, m + 1):
                if not used[j]:
                    cur = costs[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minimum[j]:
                        minimum[j], way[j] = cur, j0
                    if minimum[j] < delta:
                        delta, j1 = minimum[j], j
            for j in range(m + 1):
                if used[j]:
                    u[match[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            j0 = j1
            if match[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            match[j0] = match[j1]
            j0 = j1
    return tuple(sorted((match[j] - 1, j - 1, weights[match[j] - 1][j - 1])
                        for j in range(1, p + 1) if match[j] and allowed(weights[match[j] - 1][j - 1])))
