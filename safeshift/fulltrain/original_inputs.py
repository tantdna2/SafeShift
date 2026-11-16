"""Read-only binding of the already verified original Kaggle TRAIN mounts.

No image copy, renamed checkpoint, symlink view, prediction import or TEST walk.
Dataset versions are release/transport bindings, not observations from a mount.
"""
import json
from pathlib import Path

from safeshift.candidates.source import require, snapshot_stat
from safeshift.candidates.train_inputs import mounts
from safeshift.pilot.artifacts import safe, sha, relative
from safeshift.pilot.contract import digest, MASTER_SHA
from . import inputs

SCHEMA = "safeshift-original-mounted-train-v1"
REFS = {"master_dataset": "nguynanhtn/safeshift-pilot-input",
        "train_dataset": "nguynanhtn/inspecsafe-v1-kaggle"}


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


def admit(root, binding, binding_sha256, projection_sha256):
    validate_binding(binding, binding_sha256, projection_sha256)
    root = Path(root)
    require(not any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
                    for p in (root, *root.parents)), "ORIGINAL_INPUT_ROOT_ALIAS")
    attached = mounts(root)  # bounded direct/nested discovery; no image/TEST walk
    for name, ref in REFS.items():
        selected = safe(root, binding[name]["mount"])
        require([p for p in attached if p.name == ref.split("/")[1]] == [selected],
                "UNIQUE_ORIGINAL_MOUNT_REQUIRED")
    master = safe(root, binding["master_dataset"]["mount"] + "/master_manifest.json")
    require(snapshot_stat(master).st_size <= 16 * 2**20, "ORIGINAL_MASTER_BOUND")
    raw = master.read_bytes()
    cohort = inputs.project_master(raw, projection_sha256)  # frozen SHA BEFORE parse
    originals = json.loads(raw)["samples"]
    require(len(originals) == len(cohort["samples"]) == 3763, "EXACT_ORIGINAL_3763")
    bundle = safe(root, binding["train_dataset"]["mount"] + "/InspecSafe-V1-Kaggle/train/DATA_PATH")
    snapshot_stat(bundle, directory=True)
    rows = []
    for row, original in zip(cohort["samples"], originals):
        locator = original["image_locator"]
        require(locator.startswith("DATA_PATH/train/Annotations/") and locator.endswith(".jpg"),
                "ORIGINAL_TRAIN_JPG_ONLY")
        require(original["sample_id"] == row["sample_id"]
                and original["image_sha256"] == row["image_sha256"], "ORIGINAL_ROW_CUSTODY")
        image = locator.removeprefix("DATA_PATH/")
        safe(bundle, image)
        rows.append({**row, "image": image})  # No GT/domain/label fields leave admission.
    return bundle, cohort, rows


def verify_bytes(root, cohort, rows):
    require(len(rows) == len(cohort["samples"]) == 3763, "EXACT_ORIGINAL_3763")
    for expected, row in zip(cohort["samples"], rows):
        require(set(row) == {*expected, "image"} and all(row[n] == v for n, v in expected.items()),
                "ORIGINAL_MAPPING_ORDER_ID_SHA")
        require(row["image"].startswith("train/Annotations/") and row["image"].endswith(".jpg")
                and Path(row["image"]).stem == row["sample_id"],
                "ORIGINAL_TRAIN_JPG_ONLY")
        path = safe(root, row["image"])
        snapshot_stat(path)
        require(sha(path) == row["image_sha256"], "ORIGINAL_IMAGE_BYTES_CHANGED")
    return {"verified_images": len(rows), "decode": "NOT_RUN", "copied_bytes": 0}


def verify_images(root, cohort, rows):
    """Pinned child CPU image decode; SHA locks dimensions, no invented sizes."""
    verify_bytes(root, cohort, rows)
    from PIL import Image
    for row in rows:
        with Image.open(safe(root, row["image"])) as image:
            require(image.format == "JPEG" and getattr(image, "n_frames", 1) == 1
                    and all(n > 0 for n in image.size), "ORIGINAL_STILL_JPEG_REQUIRED")
            image.load()
    return {"verified_images": len(rows), "decode": "PASS", "copied_bytes": 0}
