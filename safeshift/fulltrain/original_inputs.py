"""Read-only binding of the already verified original Kaggle TRAIN mounts.

No image copy, renamed checkpoint, symlink view, prediction import or TEST walk.
Dataset versions are release/transport bindings, not observations from a mount.
"""
import json
import io
from pathlib import Path

from safeshift.candidates.source import require, snapshot_stat
from safeshift.candidates.train_inputs import mounts
from safeshift.pilot.artifacts import safe, relative
from safeshift.pilot.contract import digest, MASTER_SHA
from . import inputs, memory

SCHEMA = "safeshift-original-mounted-train-v1"
REFS = {"master_dataset": "nguynanhtn/safeshift-pilot-input",
        "train_dataset": "nguynanhtn/inspecsafe-v1-kaggle"}
# Version1 provider listings, rechecked for the V4-4 incident. No recursive
# fallback: the flat Master is retained for existing direct exported bundles.
MASTER_PATHS = ("master_manifest.json", "safeshift-pilot-input/master_manifest.json")
TRAIN_PATHS = ("InspecSafe-V1-Kaggle/train/DATA_PATH",)


def unique_path(mount, paths, *, directory=False):
    found = []
    for name in paths:
        path = safe(mount, name)  # also rejects dangling links and hardlinks
        if path.exists():
            snapshot_stat(path, directory=directory)
            found.append(path)
    require(len(found) == 1, "UNIQUE_ORIGINAL_CONTENT_PATH_REQUIRED")
    return found[0]


def validate_binding(binding, expected_binding_sha256, expected_projection_sha256):
    require(type(binding) is dict and set(binding) == {"schema", "master_dataset", "train_dataset",
            "master_sha256", "projection_sha256"}, "ORIGINAL_MOUNT_BINDING_FIELDS")
    require(binding["schema"] == SCHEMA and binding["master_sha256"] == MASTER_SHA,
            "ORIGINAL_MOUNT_MASTER_LOCK")
    require(digest(binding) == expected_binding_sha256
            and binding["projection_sha256"] == expected_projection_sha256, "ORIGINAL_MOUNT_BINDING_PIN")
    for name, ref in REFS.items():
        row = binding[name]
        require(type(row) is dict and set(row) == {"ref", "version", "mount"}
                and row["ref"] == ref, "EXACT_ORIGINAL_DATASET_REF")
        require(type(row["version"]) is int and row["version"] > 0, "EXACT_DATASET_VERSION_REQUIRED")
        relative(row["mount"])
        slug = ref.split("/")[1]
        require(row["mount"] in (slug, "datasets/nguynanhtn/" + slug), "EXACT_ORIGINAL_MOUNT_PATH")


def admit(root, binding, binding_sha256, projection_sha256, *, deadline=None):
    validate_binding(binding, binding_sha256, projection_sha256)
    root = Path(root).absolute()
    require(not any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
                    for p in (root, *root.parents)), "ORIGINAL_INPUT_ROOT_ALIAS")
    attached = mounts(root)  # bounded direct/nested discovery; no image/TEST walk
    for name, ref in REFS.items():
        selected = safe(root, binding[name]["mount"])
        require([p for p in attached if p.name == ref.split("/")[1]] == [selected],
                "UNIQUE_ORIGINAL_MOUNT_REQUIRED")
    master = unique_path(safe(root, binding["master_dataset"]["mount"]), MASTER_PATHS)
    size = snapshot_stat(master).st_size
    require(size <= 16 * 2**20, "ORIGINAL_MASTER_BOUND")
    with io.BytesIO() as stream:
        memory.stream_readonly_sha256(master, expected_size=size, deadline=deadline, copy_to=stream)
        raw = stream.getvalue()
    cohort = inputs.project_master(raw, projection_sha256)  # frozen SHA BEFORE parse
    originals = json.loads(raw)["samples"]
    require(len(originals) == len(cohort["samples"]) == 3763, "EXACT_ORIGINAL_3763")
    bundle = unique_path(safe(root, binding["train_dataset"]["mount"]), TRAIN_PATHS, directory=True)
    rows = []
    for row, original in zip(cohort["samples"], originals):
        locator = original["image_locator"]
        require(locator.startswith("DATA_PATH/train/Annotations/") and locator.endswith(".jpg"),
                "ORIGINAL_TRAIN_JPG_ONLY")
        require(original["sample_id"] == row["sample_id"]
                and original["image_sha256"] == row["image_sha256"], "ORIGINAL_ROW_CUSTODY")
        image = locator.removeprefix("DATA_PATH/")
        require(Path(image).stem == row["sample_id"], "ORIGINAL_MAPPING_ID_PATH")
        safe(bundle, image)
        rows.append({**row, "image": image})  # No GT/domain/label fields leave admission.
    return bundle, cohort, rows


def verify_bytes(root, cohort, rows, *, deadline=None):
    require(len(rows) == len(cohort["samples"]) == 3763, "EXACT_ORIGINAL_3763")
    for expected, row in zip(cohort["samples"], rows):
        require(set(row) == {*expected, "image"} and all(row[n] == v for n, v in expected.items()),
                "ORIGINAL_MAPPING_ORDER_ID_SHA")
        require(row["image"].startswith("train/Annotations/") and row["image"].endswith(".jpg")
                and Path(row["image"]).stem == row["sample_id"],
                "ORIGINAL_TRAIN_JPG_ONLY")
        path = safe(root, row["image"])
        size = snapshot_stat(path).st_size
        require(memory.stream_readonly_sha256(path, expected_size=size, deadline=deadline) == row["image_sha256"], "ORIGINAL_IMAGE_BYTES_CHANGED")
    return {"verified_images": len(rows), "decode": "NOT_RUN", "copied_bytes": 0}


def verify_images(root, cohort, rows, *, deadline=None):
    """Pinned child CPU image decode; SHA locks dimensions, no invented sizes."""
    verify_bytes(root, cohort, rows, deadline=deadline)
    from PIL import Image
    formats = {}
    for row in rows:
        path = safe(root, row["image"])
        size = snapshot_stat(path).st_size
        memory.check_deadline(deadline)
        with Image.open(path) as image:
            # Match the proven native PIL loader. The original TRAIN includes
            # PNG bytes with .jpg locators; the frozen SHA, not the suffix,
            # identifies the unchanged input. Never transcode or rewrite it.
            require(getattr(image, "n_frames", 1) == 1 and all(n > 0 for n in image.size),
                    "ORIGINAL_STILL_IMAGE_REQUIRED")
            image.load()
            formats[image.format] = formats.get(image.format, 0) + 1
            with image.convert("RGB") as rgb:
                require(rgb.mode == "RGB", "ORIGINAL_NATIVE_RGB_CONVERSION")
        memory.evict_readonly_file(path, expected_size=size, deadline=deadline)
    return {"verified_images": len(rows), "decode": "PASS", "formats": formats, "copied_bytes": 0}
