"""Build two notebooks sharing the same source-capsule bootstrap and controller."""

from argparse import ArgumentParser
from pathlib import Path

from safeshift.data.saved_reports import strict_json
from safeshift.fulltrain.qwen_semantics import fields
from scripts.build_ct1_evidence_notebooks import notebook

ROOT = Path(__file__).resolve().parents[1]
PILOT = "SafeShift_CT1_EVIDENCE_PILOT_KAGGLE.ipynb"
PREFLIGHT = "SafeShift_CT1_EVIDENCE_PREFLIGHT_KAGGLE.ipynb"

SETTINGS = """# Template only. Render a sealed Owner notebook with --settings before running.
SOURCE = "/kaggle/input/ct1-reviewed-source"
SOURCE_COMMIT = ""
SOURCE_ZIP_SHA256 = ""
OWNER = {
    "run_id": "",  # ct1- followed by 12 lowercase hexadecimal characters. Keep for resume.
    "pilot_input": "/kaggle/input/ct1-train48",
    "plan_sha256": "",
    "checkpoint": "/kaggle/input/ct1-qwen-checkpoint/0c351dd01ed87e9c1b53cbc748cba10e6187ff3b",
    "software_input": "/kaggle/input/ct1-qwen-software",
    "software_marker_sha256": "",
    "approved_drivers": [],  # Empty admits the observed host driver at or above the CUDA 12.8 GA floor.
    "resume": None,  # {"path": "/kaggle/input/.../<run_id>.zip", "sha256": "..."}
}
"""

BOOTSTRAP = r"""import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from zipfile import ZipFile

base = Path("/kaggle/working")
input_root = Path("/kaggle/input")
root = Path(SOURCE)
assert sys.platform == "linux" and base.is_dir() and root.is_dir()
assert root.is_absolute() and root.resolve().is_relative_to(input_root)
assert not any(p.is_symlink() for p in (root, *root.parents))
assert re.fullmatch(r"[0-9a-f]{40}", SOURCE_COMMIT)
assert re.fullmatch(r"[0-9a-f]{64}", SOURCE_ZIP_SHA256)
assert re.fullmatch(r"ct1-[0-9a-f]{12}", OWNER["run_id"])
assert {p.name for p in root.iterdir()} == {"ct1-source.zip", "ct1-source.json"}
path = root / "ct1-source.zip"
marker_path = root / "ct1-source.json"
assert all(p.is_file() and not p.is_symlink() and p.stat().st_nlink == 1 for p in (path, marker_path))
assert 0 < path.stat().st_size <= 8 * 2**20 and marker_path.stat().st_size <= 2048
marker = json.loads(marker_path.read_bytes())
assert marker == {"commit": SOURCE_COMMIT, "sha256": SOURCE_ZIP_SHA256}
payload = path.read_bytes()
assert hashlib.sha256(payload).hexdigest() == SOURCE_ZIP_SHA256
repo = base / ("ct1-source-" + OWNER["run_id"])
allowed = {"scripts/run_ct1_native_pilot.py", "configs/fulltrain/qwen3.json",
           "configs/pilot/classification_c1.txt", "configs/pilot/pip_bootstrap.json"}
with ZipFile(io.BytesIO(payload)) as archive:
    files = [item for item in archive.infolist() if not item.is_dir()]
    names = {item.filename for item in files}
    assert len(files) == len(names) <= 600 and allowed <= names
    assert sum(item.file_size for item in files) <= 16 * 2**20
    for item in files:
        name = item.filename
        posix = PurePosixPath(name)
        assert not posix.is_absolute() and posix.as_posix() == name
        assert ".." not in posix.parts and ":" not in name and chr(92) not in name
        assert not stat.S_ISLNK(item.external_attr >> 16)
        assert (name.startswith("safeshift/") and name.endswith(".py")) or name in allowed
    repo.mkdir(exist_ok=False)
    for item in files:
        target = repo / item.filename
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(archive.read(item))
observed_drivers = sorted({row.split(",")[2].strip() for row in gpu_query.stdout.strip().splitlines()})
assert len(observed_drivers) == 1
assert tuple(map(int, observed_drivers[0].split("."))) >= (570, 26), "CUDA 12.8 GA driver required"
owner_values = dict(OWNER)
if not owner_values["approved_drivers"]:
    owner_values["approved_drivers"] = observed_drivers
owner_values["observed_driver"] = observed_drivers[0]
with (repo / "owner-run.json").open("x", encoding="utf-8") as stream:
    json.dump({**owner_values, "mode": MODE, "source_commit": SOURCE_COMMIT,
               "source_capsule_sha256": SOURCE_ZIP_SHA256}, stream, allow_nan=False)
clean = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL") if k in os.environ}
clean.update(PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1",
             TRANSFORMERS_OFFLINE="1", TEMP=str(base), TMP=str(base), TMPDIR=str(base))
result = subprocess.run(
    [sys.executable, "-B", "-m", "scripts.run_ct1_native_pilot", "supervise",
     "--config", str(repo / "owner-run.json"), "--job", str(base / OWNER["run_id"])],
    cwd=repo, env=clean, timeout=11100, check=False,
)
print("ZIP output:", base / (OWNER["run_id"] + ".zip"))
result.check_returncode()
"""


def owner_settings(settings):
    fields(settings, {"source", "source_commit", "source_zip_sha256", "owner"})
    fields(settings["owner"], {"run_id", "pilot_input", "plan_sha256", "checkpoint", "software_input",
                              "software_marker_sha256", "approved_drivers", "resume"})
    from safeshift.evaluation.full_train_benchmark import is_sha256
    from safeshift.fulltrain.ct1_run import RUN_ID
    import re
    owner = settings["owner"]
    if not (re.fullmatch(r"[0-9a-f]{40}", settings["source_commit"])
            and RUN_ID.fullmatch(owner["run_id"])
            and all(is_sha256(value) for value in
                    (settings["source_zip_sha256"], owner["plan_sha256"], owner["software_marker_sha256"]))):
        raise ValueError("sealed source and owner input identity required")
    for path in (settings["source"], owner["pilot_input"], owner["checkpoint"], owner["software_input"]):
        if not isinstance(path, str) or not path.startswith("/kaggle/input/"):
            raise ValueError("Owner Input paths must be exact Kaggle mounts")
    if owner["resume"] is not None:
        fields(owner["resume"], {"path", "sha256"})
        if not owner["resume"]["path"].startswith("/kaggle/input/") or not is_sha256(owner["resume"]["sha256"]):
            raise ValueError("exact resume Input and SHA required")
    return (f'SOURCE = {settings["source"]!r}\n'
            f'SOURCE_COMMIT = {settings["source_commit"]!r}\n'
            f'SOURCE_ZIP_SHA256 = {settings["source_zip_sha256"]!r}\n'
            f'OWNER = {owner!r}\n')


def content(mode, settings=None):
    if mode not in ("pilot", "preflight") or (mode == "preflight" and settings and settings["owner"]["resume"]):
        raise ValueError("invalid notebook mode or preflight resume")
    instructions = SETTINGS if settings is None else owner_settings(settings)
    return notebook([
        ("intro", "markdown", "# SafeShift CT1 — Kaggle " + mode + "\n"
         "Candidate tĩnh. Chỉ chạy khi Owner đã chấp thuận đúng SHA và Inputs. "
         "Đính kèm riêng source, ảnh TRAIN mù, checkpoint và phần mềm. "
         "Dùng 2×T4, tắt Internet. Chỉ attach ZIP checkpoint khi tiếp tục.\n"),
        ("gpu-observe", "code", """import subprocess
gpu_query = subprocess.run(
    ["nvidia-smi", "--query-gpu=index,name,driver_version,memory.free", "--format=csv,noheader,nounits"],
    capture_output=True, text=True, check=True, timeout=10,
)
print(gpu_query.stdout.strip())
"""),
        ("owner-settings", "code", f'MODE = "{mode}"\n' + instructions),
        ("execute", "code", BOOTSTRAP),
    ])


def main(argv=None):
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--settings", type=Path, help="exact Owner settings JSON")
    parser.add_argument("--mode", choices=("pilot", "preflight"))
    parser.add_argument("--output", type=Path, help="new configured notebook file")
    args = parser.parse_args(argv)
    if args.settings or args.mode or args.output:
        if args.check or not (args.settings and args.mode and args.output):
            parser.error("--settings, --mode and --output must be used together")
        from safeshift.pilot.artifacts import write_bytes
        payload = content(args.mode, strict_json(args.settings.read_bytes()))
        print(write_bytes(args.output, payload))
        return
    for name, mode in ((PILOT, "pilot"), (PREFLIGHT, "preflight")):
        path = ROOT / "notebooks" / name
        data = content(mode)
        if args.check:
            if path.read_bytes() != data:
                raise ValueError(f"notebook bytes mismatch: {name}")
        else:
            path.write_bytes(data)


if __name__ == "__main__":
    main()
