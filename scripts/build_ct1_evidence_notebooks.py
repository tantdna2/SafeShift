"""Build the CT1 pilot preparation and CPU preflight notebooks deterministically."""

from argparse import ArgumentParser
from pathlib import Path

from safeshift.data.saved_reports import json_bytes

ROOT = Path(__file__).resolve().parents[1]
PILOT = "SafeShift_CT1_EVIDENCE_PILOT_PREP.ipynb"
PREFLIGHT = "SafeShift_CT1_EVIDENCE_CPU_PREFLIGHT.ipynb"

SETUP = """from pathlib import Path
import os
import sys

repo = Path(os.environ.get("SAFESHIFT_CT1_REPO", ".")).resolve(strict=True)
assert (repo / "scripts/ct1_pilot.py").is_file(), "Set SAFESHIFT_CT1_REPO to the reviewed checkout"
assert sys.version_info >= (3, 11), "Python 3.11+ required for CPU preparation"
if os.name == "nt" and repo.drive.upper() != "D:":
    raise ValueError("SafeShift workspace must be on D:")
workspace = Path(os.environ.get("SAFESHIFT_CT1_OUTPUT_ROOT", repo / "data/processed")).resolve()
if os.name == "nt" and workspace.drive.upper() != "D:":
    raise ValueError("SafeShift output must be on D:")
workspace.mkdir(parents=True, exist_ok=True)
offline_env = {**os.environ, "TMPDIR": str(workspace), "TEMP": str(workspace),
               "TMP": str(workspace), "PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1",
               "TRANSFORMERS_OFFLINE": "1", "CUDA_VISIBLE_DEVICES": ""}
"""

PILOT_TEST = """import subprocess

subprocess.run(
    [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_ct1_pilot.py", "-v"],
    cwd=repo, env=offline_env, check=True,
)
"""
PILOT_PREPARE = """bundle = workspace / "ct1-notebook-prep"
subprocess.run(
    [sys.executable, "-B", "-m", "scripts.ct1_pilot", "prepare",
     "--with-control", "--output", str(bundle)],
    cwd=repo, env=offline_env, check=True,
)
print(bundle / "receipt.json")
"""

PROBE = """import hashlib
from importlib import metadata
import json
import platform
import shutil
import tempfile

c1 = (repo / "configs/pilot/classification_c1.txt").read_bytes()
assert hashlib.sha256(c1).hexdigest() == "816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3"
with tempfile.TemporaryDirectory(prefix="ct1-probe-", dir=workspace) as scratch:
    test_file = Path(scratch) / "bounded-write.bin"
    block = bytes(64 * 1024)
    with test_file.open("xb") as stream:
        stream.write(block)
        stream.flush()
        os.fsync(stream.fileno())
    assert test_file.read_bytes() == block

packages = {}
for package in ("torch", "transformers", "accelerate", "Pillow"):
    try:
        packages[package] = metadata.version(package)
    except metadata.PackageNotFoundError:
        packages[package] = None

receipt = {
    "status": "CPU_ENVIRONMENT_OBSERVED", "release_status": "BLOCKED",
    "platform": platform.system(), "machine": platform.machine(),
    "python": platform.python_version(), "abi": sys.implementation.cache_tag,
    "package_metadata": packages, "scratch_free_bytes": shutil.disk_usage(workspace).free,
    "bounded_fsync_probe_bytes": len(block), "input_check": "NOT_RUN",
    "weights": "NOT_OPENED", "gpu": "NOT_RUN", "native_calls": 0,
}
with (workspace / "ct1-cpu-preflight.json").open("x", encoding="utf-8") as stream:
    json.dump(receipt, stream, indent=2, allow_nan=False)
    stream.write("\\n")
print(receipt)
"""


def notebook(cells):
    payload = []
    for name, kind, source in cells:
        cell = {"id": name, "cell_type": kind, "metadata": {}, "source": source.splitlines(keepends=True)}
        if kind == "code":
            compile(source, name, "exec")
            cell.update(execution_count=None, outputs=[])
        payload.append(cell)
    return json_bytes({"nbformat": 4, "nbformat_minor": 5, "cells": payload,
                       "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                                   "name": "python3"}}})


def notebooks():
    return {
        PILOT: notebook([
            ("intro", "markdown", "# SafeShift CT1 — Chuẩn bị pilot A/E/S\n"
             "Ô chạy được chỉ kiểm fixtures và xuất prompt/schema trên CPU. "
             "Notebook đang BLOCKED cho chạy model. Chạy CPU_PREFLIGHT trước.\n"),
            ("workspace", "code", SETUP),
            ("tests", "code", PILOT_TEST),
            ("bundle", "code", PILOT_PREPARE),
            ("next", "markdown", "## Trước pilot\n"
             "Theo docs/research/THESIS_CT1_EVIDENCE_PILOT.md. Khóa cohort TRAIN development, "
             "miền, nhóm nguồn và quyền ở bộ chấm riêng. Image request gồm ảnh dưới định danh mù "
             "và prompt cố định. Giữ GT/annotation ngoài môi trường runner. Native release "
             "cần notebook/runner đã duyệt theo đúng source, quyền kỹ thuật và grant pilot riêng.\n"),
        ]),
        PREFLIGHT: notebook([
            ("intro", "markdown", "# SafeShift CT1 — Preflight CPU cục bộ\n"
             "Chỉ kiểm C1, metadata gói Python và ghi/đọc/xóa scratch 64 KiB. "
             "Không cài dependency, đọc dataset/weights, gọi GPU, Kaggle hoặc tiêu lượt model. "
             "Ghi một receipt mới tại SAFESHIFT_CT1_OUTPUT_ROOT.\n"),
            ("workspace", "code", SETUP),
            ("probe", "code", PROBE),
            ("gates", "markdown", "## Điều kiện live còn thiếu\n"
             "Xác minh Input marker duy nhất, source/model/processor/weights hash và quyền. "
             "Kiểm cgroup/RAM, disk/quota, GPU/driver/CUDA/FP16 child và map 2×T4 trong môi trường "
             "được cấp quyền. Đo tải weights, synthetic/approved first-call và export trước pilot. "
             "Xem docs/KAGGLE_FAILURES_AND_RELEASE_GATES.md.\n"),
        ]),
    }


def main(argv=None):
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed notebook bytes")
    args = parser.parse_args(argv)
    for name, payload in notebooks().items():
        path = ROOT / "notebooks" / name
        if args.check:
            if path.read_bytes() != payload:
                raise ValueError(f"notebook differs from generator: {name}")
        else:
            path.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())