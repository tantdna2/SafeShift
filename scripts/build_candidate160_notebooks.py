"""Deterministic candidate notebooks using the existing notebook bootstrap.

The exact runtime commit must contain every embedded byte. A subsequent commit
can contain the generated notebooks/evidence without a self-referential SHA.
"""
import argparse
import base64
import copy
import json
from pathlib import Path
import re
import subprocess
import zlib

from scripts.build_three_vlm_notebooks import notebook as legacy_notebook
from safeshift.candidates.source import ROOT, require
from safeshift.candidates.train_contract import BASE, PACKAGE_BASE, KEYS, MANIFEST, config, configuration_hashes, model, sources, source_hash
from safeshift.pilot.contract import source_digest


def notebook(key, ref, repo=ROOT):
    require(key in KEYS and re.fullmatch(r"[0-9a-f]{40}", ref), "EXACT_RUNTIME_COMMIT_REQUIRED")
    repo = Path(repo)
    payload = {p: (repo / p).read_text(encoding="utf-8") for p in sources(repo)}
    # Byte identity is checked with Git, never inferred from a caller-provided SHA.
    for name, text in payload.items():
        saved = subprocess.check_output(["git", "show", f"{ref}:{name}"], cwd=repo, stderr=subprocess.PIPE)
        require(saved == text.encode(), "RUNTIME_REF_SOURCE_MISMATCH:" + name)
    result = copy.deepcopy(legacy_notebook("phi", repo))
    code = "".join(result["cells"][1]["source"])
    old_payload = {p: (repo / p).read_text(encoding="utf-8") for p in __import__(
        "safeshift.pilot.contract", fromlist=["source_files"]).source_files(repo)}
    def packed(value):
        return base64.b64encode(zlib.compress(json.dumps(value, sort_keys=True).encode(), 9)).decode()
    code = code.replace(repr(packed(old_payload)), repr(packed(payload)))
    code = code.replace(source_digest(repo), source_hash(repo))
    code = code.replace('root.mkdir(parents=True, exist_ok=True)', 'root.mkdir(parents=True, exist_ok=False)')
    code = code.replace('pathlib.Path("/kaggle/working/data/processed/three_vlm_code")',
                        'pathlib.Path.cwd() / "data/processed/candidate160_code"')
    code = code.replace('pathlib.Path("/kaggle/working/data/processed/three_vlm_bootstrap")',
                        '(pathlib.Path.cwd() / "data/processed/candidate160_bootstrap")')
    code = code.replace("from safeshift.pilot.bootstrap import launch", "from safeshift.candidates.train_runtime import launch_owner as launch")
    code = code.replace('launch(\'phi\', expected_source_sha256, root, mode="PILOT")',
                        f'launch({key!r}, expected_source_sha256, root, {ref!r}, owner_start=True)')
    require("safeshift.pilot.bootstrap import launch" not in code and 'mode="PILOT"' not in code,
            "CANDIDATE_LAUNCH_ROUTE_REQUIRED")
    compile(code, "candidate160_notebook", "exec")
    spec = model(key)
    instructions = f"""# SafeShift — {spec['id']} — một lượt, tối đa 160 TRAIN

**Owner kích hoạt bằng Save Version → Save & Run All một lần**, sau khi PR này
được ChatGPT kiểm GitHub và audit độc lập trước merge. Không cần grant,
reservation hay file CONTINUE thủ công. Thao tác chạy notebook là yêu cầu
thực thi của Owner trong đúng phạm vi quyết định ngày 30/10/2026, ghi tại
`docs/research/CANDIDATE160_OWNER_DECISION_20261030.md`; máy không ký thay Lead.
Đây là code chưa được kiểm GPU; chất lượng thật và HNLO thực nghiệm UNVERIFIED.

Model `{spec['id']}` @ `{spec['revision']}`; Transformers `{spec['transformers']}`.
Adapter base #151 `{BASE}`; package base #153 `{PACKAGE_BASE}`.
Runtime commit `{ref}`. Cùng manifest SHA256 `{MANIFEST}` và đúng 160 ảnh TRAIN
/thứ tự lịch sử, không chọn lại, TEST, supplement hoặc FULL TRAIN.
Không chuyển quyền này sang dữ liệu bên thứ ba hoặc thí nghiệm khác.

1. Mở đúng notebook model trong một Kaggle session chưa chạy; chọn **T4 ×2**,
   Internet ON để cài software pinned. Không chạy interactive trước khi Save.
2. Attach bundle Owner đã upload: `pilot_manifest.json` và
   `images/000000.jpg` … `images/000159.jpg`.
3. Attach checkpoint đã upload: `candidate_checkpoint_{key}.json`,
   `source/{spec['revision']}/` đúng source allowlist và `weights/` đúng
   index + hai shards đã khóa SHA256. Xem `docs/CANDIDATE160_KAGGLE.md`.
4. Save Version → **Save & Run All** một lần. Không sửa cell, SHA, model,
   version hoặc input để đi qua lỗi. Không retry/resume hoặc ghi đè.
5. Download ZIP + `.sha256.json` được in ở cell cuối, kể cả lỗi/partial;
   giữ private. `COMPLETED_AWAITING_REVIEW` không phải model qualification.

Run ID/attempt ID và consumption log được tạo tự động. Khóa slot cố định theo
model/cohort chặn chạy trùng trong cùng output root, kể cả source đổi,
UUID mới hoặc lỗi admission. Không xóa khóa/rerun. Kaggle session mới không có
ledger cũ không cho phép khóa local chứng minh đã chống trùng toàn cục: Owner
chỉ tạo một saved job/model, không chạy concurrent hoặc tạo session thay thế.
Attached saved Outputs có marker ở layout chuẩn được kiểm để chặn replay.

Worker phải là CPython **3.11.9**, Linux x86_64, Torch **2.6.0+cu124**,
torchvision **0.21.0+cu124**, CUDA12.4, FP16/eager/batch1/cuda:0; GPU1 chỉ quan
sát. Không fallback Python, precision hoặc tải weights. Kiểm tất cả SHA256,
source/config/manifest, decode160 ảnh, dependencies/ABI, disk, RAM/cgroup,
CUDA/driver/T4/per-GPU VRAM và child FP16 trước consumption; kiểm lại sau đó.
Admission cần28 GiB scratch +4 GiB output (32 GiB nếu cùng filesystem).
Driver dùng compatibility floor525.60.13 thay allowlist chưa quyết định;
RAM>=4 GiB, live scratch/output>=1 GiB mỗi nơi, GPU0 headroom>=256 MiB.
Các reserve kỹ thuật không đảm bảo checkpoint thực fit; OOM vẫn dừng.

**Chính sách dừng được thay đổi công khai để reviewer đánh giá:** lỗi kỹ thuật,
NaN/Inf, mất raw/custody, thiếu tài nguyên hoặc hết12 giờ dừng ngay. INVALID,
lặp sequence, lệch nhãn và lỗi Normal/hazard được ghi để review sau lượt chạy;
chưa có ngưỡng khoa học được quyết định nên không tự đặt ngưỡng hay dừng vì
thiếu GT support ở mốc sớm. Không có file CONTINUE hoặc quyết định Lead giả.
Có thể tiêu đủ160 calls dù behavior kém; kết quả không được tự nâng thành PASS.

Raw IDs/logits/request được lưu trước parser; parser/C1/HNLO, model revision,
checkpoint và config effective/legacy hashes giữ nguyên. Ảnh chưa gọi là
NOT_ATTEMPTED. Archive chứa execution/slot/consumption log,160 accounting,
raw/checkpoints/technical decisions, behavior observations và receipts.
Không chứa ảnh/weights. Hard kill/VM loss/disk failure có thể mất ZIP hoàn chỉnh;
giữ mọi bytes còn lại và không chạy lại. CPU synthetic PASS không là GPU PASS.
"""
    result["cells"][0]["source"] = instructions.splitlines(True)
    result["cells"][1]["source"] = code.splitlines(True)
    result["cells"][1]["id"] = "candidate160-launch"
    result["metadata"]["safeshift"] = {"mode": "CANDIDATE160_OWNER_ACTIVATED", "status": "AWAITING_INDEPENDENT_REVIEW",
        "base": BASE, "package_base": PACKAGE_BASE, "runtime_ref": ref, "model_key": key, "model": spec,
        "source_sha256": source_hash(repo), "manifest_sha256": MANIFEST,
        "config": config(key), "configuration_hashes": configuration_hashes(key),
        "max_images": 160, "gpu": "UNVERIFIED", "behavior": "UNVERIFIED"}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-ref", required=True)
    args = parser.parse_args()
    for key in KEYS:
        path = ROOT / f"notebooks/SafeShift_CANDIDATE160_{key}.ipynb"
        path.write_text(json.dumps(notebook(key, args.runtime_ref), indent=1, ensure_ascii=False)+"\n",
                        encoding="utf-8", newline="\n")
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
