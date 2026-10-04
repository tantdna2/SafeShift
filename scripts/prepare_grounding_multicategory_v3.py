"""Deterministic synthetic-only v3 preparation; no model/qualification executor.

Run from repository root. The CLI verifies the manifest and never overwrites
different existing image bytes. Only ignored data/processed images are written.
"""

import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw
from scripts.generate_external_gate_cases import GROUPS, draw_object
from safeshift.protocol.firewall import external_path

VERSION = "external-grounding-multicategory-v3"
MANIFEST = "configs/pre_freeze/external_grounding_interface_cases.v3.json"
IMAGE_ROOT = "data/processed/external_grounding_multicategory_v3/images"
LABELS = ("red square", "green circle", "yellow triangle", "cyan rectangle")


def build():
    specs = []
    for group, shape, label, rgb, distractor_rgb, _, first, second in GROUPS:
        for index, (target, distractor) in enumerate(((first, second), (second, first)), 1):
            specs.append((f"{group}_{index}", "position_swap", group,
                          [(label, shape, target, rgb)], [(shape, distractor, distractor_rgb)]))
    red = lambda b: (LABELS[0], "square", b, (255, 0, 0))
    green = lambda b: (LABELS[1], "circle", b, (0, 160, 0))
    yellow = lambda b: (LABELS[2], "triangle", b, (255, 224, 0))
    cyan = lambda b: (LABELS[3], "rectangle", b, (0, 192, 224))
    specs.extend([
        ("E_red_green", "two_categories", None,
         [red((24, 32, 80, 88)), green((176, 168, 232, 224))],
         [("square", (100, 100, 156, 156), (0, 0, 255))]),
        ("F_two_red", "multiple_instance", None,
         [red((24, 32, 80, 88)), red((176, 168, 232, 224))],
         [("circle", (100, 100, 156, 156), (255, 128, 0))]),
        ("G_multi", "multiple_categories_multiple_instances", None,
         [red((16, 16, 64, 64)), red((192, 192, 240, 240)),
          green((192, 16, 240, 64)), green((16, 192, 64, 240)),
          yellow((104, 104, 152, 152))], []),
        ("H_all_four", "all_queried_categories", None,
         [red((16, 16, 64, 64)), green((192, 16, 240, 64)),
          yellow((16, 192, 64, 240)), cyan((176, 192, 240, 224))],
         [("triangle", (104, 104, 152, 152), (128, 0, 160))]),
    ])
    cases, images = [], {}
    for case_id, kind, group, targets, distractors in specs:
        with Image.new("RGB", (256, 256), (255, 255, 255)) as image:
            draw = ImageDraw.Draw(image)
            for _, shape, box, rgb in targets:
                draw_object(draw, shape, box, rgb)
            for shape, box, rgb in distractors:
                draw_object(draw, shape, box, rgb)
            stream = BytesIO()
            image.save(stream, format="PNG", optimize=False, compress_level=9)
            raw = stream.getvalue()
        path = f"{IMAGE_ROOT}/{case_id}.png"
        images[path] = raw
        cases.append({
            "case_id": case_id, "kind": kind, "swap_group": group,
            "query_labels": list(LABELS),
            "expected_counts": {label: sum(t[0] == label for t in targets) for label in LABELS},
            "targets": [{"label": label, "bbox": [v / 256 for v in box]}
                        for label, _, box, _ in targets],
            "distractor_boxes": [[v / 256 for v in box] for _, box, _ in distractors],
            "image_path": path, "image_sha256": hashlib.sha256(raw).hexdigest(),
            "image_size_bytes": len(raw),
        })
    return {"schema_version": VERSION, "source_kind": "synthetic",
            "statement": "NO_INSPECSAFE_CONTENT_USED", "canvas": [256, 256, "RGB"],
            "randomness": "NONE", "query_labels": list(LABELS), "cases": cases}, images


def materialize(repo):
    manifest, images = build()
    if manifest != json.loads((repo / MANIFEST).read_bytes()):
        raise ValueError("FROZEN_V3_MANIFEST_OR_RENDERER_MISMATCH")
    paths = {name: external_path(repo, name) for name in images}
    for name, path in paths.items():
        if path.exists() and path.read_bytes() != images[name]:
            raise ValueError("EXISTING_SYNTHETIC_IMAGE_MISMATCH")
    for name, path in paths.items():
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(images[name])
    return len(images)


if __name__ == "__main__":
    print(f"SYNTHETIC_INPUTS_PREPARED={materialize(ROOT)}; QUALIFICATION=NOT_RUN")
