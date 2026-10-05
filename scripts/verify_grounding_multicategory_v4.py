"""Read-only verification of committed synthetic v4 PNGs; never render inputs."""

from io import BytesIO
from pathlib import Path
import sys

# Verification must not create Python bytecode files either.
if __name__ == "__main__":
    sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image
from safeshift.protocol.schema import strict_json
from safeshift.qualification.d9r20.runtime import (
    GROUNDING_FIXTURES, GROUNDING_MANIFEST, digest, relative,
)

CASE_IDS = ("A_1", "A_2", "B_1", "B_2", "C_1", "C_2", "D_1", "D_2",
            "E_red_green", "F_two_red", "G_multi", "H_all_four")


def verify(repo):
    """Verify the fixed manifest and exact bytes, without writes or image overrides."""
    manifest = strict_json(relative(repo, GROUNDING_MANIFEST).read_bytes())
    if (manifest["schema_version"] != "external-grounding-multicategory-v4"
            or manifest["source_kind"] != "synthetic"
            or manifest["statement"] != "NO_INSPECSAFE_CONTENT_USED"
            or manifest["randomness"] != "NONE"
            or manifest["canvas"] != [256, 256, "RGB"]
            or [c["case_id"] for c in manifest["cases"]] != list(CASE_IDS)):
        raise ValueError("V4_MANIFEST_CONTRACT")
    for case in manifest["cases"]:
        path = relative(repo, case["image_path"], GROUNDING_FIXTURES)
        if case["image_path"] != f"{GROUNDING_FIXTURES}/{case['case_id']}.png":
            raise ValueError("SYNTHETIC_IMAGE_PATH")
        if not path.is_file():
            raise ValueError("SYNTHETIC_IMAGE_MISSING:" + case["case_id"])
        raw = path.read_bytes()
        if digest(raw) != case["image_sha256"]:
            raise ValueError("SYNTHETIC_IMAGE_HASH:" + case["case_id"])
        if len(raw) != case["image_size_bytes"]:
            raise ValueError("SYNTHETIC_IMAGE_SIZE:" + case["case_id"])
        with Image.open(BytesIO(raw)) as image:
            if image.format != "PNG" or image.size != (256, 256) or image.mode != "RGB":
                raise ValueError("SYNTHETIC_IMAGE_CANVAS:" + case["case_id"])
            image.load()
    return len(manifest["cases"])


def main():
    try:
        count = verify(ROOT)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"V4_FIXTURE_VERIFICATION=FAIL: {exc}", file=sys.stderr)
        return 2
    print(f"V4_FIXTURE_VERIFICATION=PASS; SYNTHETIC_INPUTS_VERIFIED={count}; "
          "MODEL_GPU_EXECUTION=NO; INSPECSAFE=NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
