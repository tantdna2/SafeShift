"""Generate only synthetic inputs for prospective qualification; no execution.

From repository root: python scripts/prepare_grounding_interface_v2.py
Images remain ignored under data/processed; the checked-in manifest is verified,
never rewritten by the CLI. Pillow/PNG versions are pinned in the PREP plan.
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

VERSION = "external-grounding-interface-v2"
MANIFEST = "configs/pre_freeze/external_grounding_interface_cases.v2.json"
IMAGE_ROOT = "data/processed/external_grounding_interface_v2/images"


def build():
    """Return ten synthetic records and PNG bytes; no filesystem/input reads."""
    specs = []
    for group, shape, label, rgb, distractor_rgb, _, first, second in GROUPS:
        for index, (target, distractor) in enumerate(((first, second), (second, first)), 1):
            specs.append((f"{group}_{index}", "position_swap", label, group,
                          [(shape, target, rgb)], [(shape, distractor, distractor_rgb)]))
    specs.extend([
        ("E_absent", "target_absent", "red square", None, [],
         [("square", (32, 96, 96, 160), (0, 0, 255)),
          ("circle", (160, 96, 224, 160), (0, 160, 0))]),
        ("F_multiple", "multiple_instance", "red square", None,
         [("square", (24, 32, 80, 88), (255, 0, 0)),
          ("square", (176, 168, 232, 224), (255, 0, 0))],
         [("square", (100, 100, 156, 156), (0, 0, 255))]),
    ])
    cases, images = [], {}
    for case_id, kind, label, group, targets, distractors in specs:
        with Image.new("RGB", (256, 256), (255, 255, 255)) as image:
            draw = ImageDraw.Draw(image)
            for shape, box, rgb in targets + distractors:
                draw_object(draw, shape, box, rgb)
            stream = BytesIO()
            image.save(stream, format="PNG", optimize=False, compress_level=9)
            raw = stream.getvalue()
        path = f"{IMAGE_ROOT}/{case_id}.png"
        images[path] = raw
        cases.append({
            "case_id": case_id, "kind": kind, "target_label": label,
            "swap_group": group, "image_path": path,
            "image_sha256": hashlib.sha256(raw).hexdigest(), "image_size_bytes": len(raw),
            "target_boxes": [[v / 256 for v in box] for _, box, _ in targets],
            "distractor_boxes": [[v / 256 for v in box] for _, box, _ in distractors],
            "objects": [{"role": role, "shape": shape, "pixel_edge_xyxy": list(box),
                         "rgb": list(rgb)}
                        for role, objects in (("target", targets), ("distractor", distractors))
                        for shape, box, rgb in objects],
        })
    return {"schema_version": VERSION, "source_kind": "synthetic",
            "statement": "NO_INSPECSAFE_CONTENT_USED", "canvas": [256, 256, "RGB"],
            "randomness": "NONE", "cases": cases}, images


def materialize(repo):
    manifest, images = build()
    expected = json.loads((repo / MANIFEST).read_bytes())
    if manifest != expected:
        raise ValueError("FROZEN_V2_MANIFEST_OR_RENDERER_MISMATCH")
    # Validate all destinations/old bytes before any write; never overwrite.
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
    print(f"SYNTHETIC_INPUTS_PREPARED={materialize(ROOT)}; EXECUTION_STATUS=NOT_RUN; "
          "MODEL_GPU_EXECUTION=NO; INSPECSAFE=NOT_RUN")
