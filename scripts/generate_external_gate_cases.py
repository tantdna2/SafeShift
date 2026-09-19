"""Generate the fixed synthetic-v1 external cases locally; no input images/network.

Run from the repository root with the existing Pillow environment. --output-dir
is a repository-relative staging root; embedded paths remain repository-relative.
Only image and manifest bytes are reproducible; provenance records the current run.
"""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import zlib

import PIL
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from safeshift.protocol.firewall import external_path
from safeshift.protocol.gate import CASE_SCHEMA_VERSION, load_cases

VERSION = "synthetic-v1"
SCRIPT = "scripts/generate_external_gate_cases.py"
MANIFEST = "configs/pre_freeze/external_gate_cases.v1.json"
PROVENANCE = "configs/pre_freeze/external_gate_cases.v1.provenance.json"
IMAGE_DIR = "tests/fixtures/pre_freeze/frozen_external_gate"
WIDTH = HEIGHT = 256
BACKGROUND = (255, 255, 255)
# Pixel-edge bounds: xmin/ymin inclusive, xmax/ymax exclusive.
GROUPS = (
    ("A", "square", "red square", (255, 0, 0), (0, 0, 255),
     "horizontal", (32, 96, 96, 160), (160, 96, 224, 160)),
    ("B", "circle", "green circle", (0, 160, 0), (255, 128, 0),
     "vertical", (96, 32, 160, 96), (96, 160, 160, 224)),
    ("C", "triangle", "yellow triangle", (255, 224, 0), (128, 0, 160),
     "top-left_to_bottom-right", (32, 32, 96, 96), (160, 160, 224, 224)),
    ("D", "rectangle", "cyan rectangle", (0, 192, 224), (64, 64, 64),
     "top-right_to_bottom-left", (144, 40, 224, 88), (32, 168, 112, 216)),
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(obj, indent=2, ensure_ascii=True) + "\n").encode("utf-8"))


def draw_object(draw, shape, bounds, color):
    x0, y0, x1, y1 = bounds
    # Pillow includes the final pixel: subtract one to preserve pixel-edge GT.
    inclusive = (x0, y0, x1 - 1, y1 - 1)
    if shape in ("square", "rectangle"):
        draw.rectangle(inclusive, fill=color)
    elif shape == "circle":
        draw.ellipse(inclusive, fill=color)
    elif shape == "triangle":
        draw.polygon(((x0 + (x1 - x0) // 2, y0),
                      (x0, y1 - 1), (x1 - 1, y1 - 1)), fill=color)
    else:
        raise ValueError(f"unknown synthetic shape: {shape}")


def generate(output_root):
    """Write only the fixed 8 PNGs and manifest under a trusted output root."""
    # Resolve/check every destination before writing, including existing aliases.
    image_paths = {f"{group}_{position}": f"{IMAGE_DIR}/{group}_{position}.png"
                   for group, *_ in GROUPS for position in (1, 2)}
    destinations = {name: external_path(output_root, name)
                    for name in (*image_paths.values(), MANIFEST)}
    cases, images = [], []
    for group, shape, query, target_rgb, distractor_rgb, motion, first, second in GROUPS:
        for position, (target, distractor) in enumerate(((first, second), (second, first)), 1):
            case_id = f"{group}_{position}"
            image_path = image_paths[case_id]
            path = destinations[image_path]
            path.parent.mkdir(parents=True, exist_ok=True)
            with Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND) as image:
                draw = ImageDraw.Draw(image)
                draw_object(draw, shape, target, target_rgb)
                draw_object(draw, shape, distractor, distractor_rgb)
                # No resampling, antialiasing, text, timestamps or optional metadata.
                image.save(path, format="PNG", optimize=False, compress_level=9)
            normalize = lambda box: [box[0] / WIDTH, box[1] / HEIGHT,
                                     box[2] / WIDTH, box[3] / HEIGHT]
            cases.append({"case_id": case_id, "image_path": image_path,
                          "target_gt_bbox": normalize(target),
                          "distractor_gt_bbox": normalize(distractor),
                          "target_query": f"Locate the {query}.", "swap_group": group})
            images.append({"case_id": case_id, "image_path": image_path,
                           "sha256": sha256(path), "width": WIDTH, "height": HEIGHT,
                           "shape": shape, "movement": motion,
                           "target_pixel_bbox": list(target),
                           "distractor_pixel_bbox": list(distractor),
                           "target_rgb": list(target_rgb), "distractor_rgb": list(distractor_rgb)})
    write_json(destinations[MANIFEST], {
        "schema_version": CASE_SCHEMA_VERSION, "source_kind": "synthetic",
        "provenance": "Deterministic local generation by scripts/generate_external_gate_cases.py "
                      "version synthetic-v1 using fixed integer geometry and RGB colors on a white "
                      "256x256 canvas, without randomness, antialiasing or external assets. "
                      "NO_INSPECSAFE_CONTENT_USED. Pixel-edge boxes normalized by canvas dimensions; "
                      "checksums and environment: configs/pre_freeze/external_gate_cases.v1.provenance.json.",
        "cases": cases,
    })
    load_cases(output_root, MANIFEST)
    return images


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=".", help="repository-relative staging root")
    args = parser.parse_args(argv)
    try:
        output_root = external_path(REPO, args.output_dir)
        provenance_path = external_path(output_root, PROVENANCE)
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
        images = generate(output_root)
        expected = {row["image_path"]: row["sha256"] for row in images}
        expected[MANIFEST] = sha256(output_root / MANIFEST)
        # Independently render a second time, then read and hash the actual bytes.
        with tempfile.TemporaryDirectory(prefix="safeshift-synthetic-v1-") as tmp:
            generate(Path(tmp))
            reproduced = {path: sha256(Path(tmp) / path) for path in expected}
        if reproduced != expected:
            raise ValueError("deterministic regeneration hash mismatch")
        try:
            executable = Path(sys.executable).resolve().relative_to(REPO).as_posix()
        except ValueError:
            executable = "python"  # Activated external environment; never record a machine-local path.
        command = f"{executable} {SCRIPT}"
        if args.output_dir != ".":
            command += " --output-dir " + json.dumps(args.output_dir)
        write_json(provenance_path, {
            "schema_version": "external-synthetic-provenance-v1",
            "external_case_schema_version": CASE_SCHEMA_VERSION,
            "suite_version": VERSION, "source_kind": "synthetic",
            "statement": "NO_INSPECSAFE_CONTENT_USED",
            "source_description": "Only locally drawn geometric primitives; no source images, "
                                  "benchmark content, downloaded assets or provider calls.",
            "generator_script_path": SCRIPT, "generator_script_version": VERSION,
            "generator_script_sha256": sha256(REPO / SCRIPT),
            "manifest_path": MANIFEST, "manifest_sha256": expected[MANIFEST],
            "canvas": {"width": WIDTH, "height": HEIGHT, "mode": "RGB", "background_rgb": list(BACKGROUND)},
            "coordinate_convention": "Pixel-edge xyxy: xmin/ymin inclusive, xmax/ymax exclusive. "
                                     "Canonical xyxy = pixel edges divided by width/height.",
            "rendering": "Pillow integer primitives, no antialiasing/resampling; PNG optimize=False, compress_level=9; no optional metadata",
            "generation_command": command,
            "python_version": platform.python_version(), "pillow_version": PIL.__version__,
            "zlib_runtime_version": zlib.ZLIB_RUNTIME_VERSION,
            "git_commit_used_to_generate": git_commit,
            "git_commit_context": "HEAD at generation; generator may be a working-tree addition. "
                                  "The separate generator SHA-256 identifies its exact bytes.",
            "randomness": "NONE; seed not applicable",
            "deterministic_regeneration": {
                "status": "PASS", "method": "Regenerated into a fresh temporary directory and compared SHA-256 of all 8 PNGs and manifest",
                "all_image_hashes_reproduced": True, "manifest_hash_reproduced": True,
                "scope": "Verified in the recorded environment; no cross-version byte guarantee",
            },
            "images": images,
        })
        print(json.dumps({"case_count": len(images), "swap_groups": len(GROUPS),
                          "deterministic_regeneration": "PASS", "manifest_sha256": expected[MANIFEST],
                          "generator_sha256": sha256(REPO / SCRIPT), "provider_api_calls": "NO"}))
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"SYNTHETIC_GENERATION_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
