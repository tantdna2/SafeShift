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
    code = code.replace("from safeshift.pilot.bootstrap import launch", "from safeshift.candidates.train_runtime import launch")
    code = code.replace('launch(\'phi\', expected_source_sha256, root, mode="PILOT")',
                        f'launch({key!r}, expected_source_sha256, root, {ref!r})')
    require("safeshift.pilot.bootstrap import launch" not in code and 'mode="PILOT"' not in code,
            "CANDIDATE_LAUNCH_ROUTE_REQUIRED")
    compile(code, "candidate160_notebook", "exec")
    spec = model(key)
    instructions = f"""# SafeShift — {spec['id']} — tối đa 160 TRAIN

**PREP / BLOCKED. GPU và behavior UNVERIFIED.** Không chạy bản PREP này trên
Kaggle trước review/release và quyền mới G0/T0/O3. Không có grant trong notebook.
Không đọc TRAIN/TEST, tải weights hoặc GPU trong task xây dựng/kiểm thử CPU.

Model `{spec['id']}` @ `{spec['revision']}`; Transformers `{spec['transformers']}`.
Adapter contract base sau PR #151 `{BASE}`; package base sau PR #152 MERGED
`{PACKAGE_BASE}`; runtime source commit `{ref}`.
Hai notebook dùng đúng manifest lịch sử SHA256 `{MANIFEST}`, cùng 160 ID/thứ tự,
80 Level04/48 Level01/24 Level02/8 Level03. Không selector, supplement hoặc TEST.

Sau phê duyệt riêng: Kaggle **T4 ×2**, Internet ON chỉ để cài software pinned.
Kernel chỉ điều phối stdlib; worker CPython **3.11.9** riêng, Torch **2.6.0+cu124**,
CUDA build **12.4**, torchvision **0.21.0+cu124**. Không tự tải/chọn Python khác.
FP16/eager/batch1/cuda:0; GPU1 chỉ quan sát, VRAM không gộp. Mọi source/config/
generation/C1/parser/processor theo PR #151; không fallback/quantize/resize cứu lỗi.
CUDA tuple là PREP, chưa có nghiệm thu GPU hoặc runtime approval.

Config v2 tách `legacy_transport_compatibility` (snapshot mô tả lịch sử, không
phải xử lý/seed thực tế) và `effective_candidate` của đúng mô hình. Grant v2 và
raw evidence bắt buộc hai hash riêng: `legacy_transport_config_sha256` và
`candidate_execution_config_sha256`. Trường frozen `raw.identity.config_sha256`
chỉ là alias hash transport; không phải hash thực thi. Notebook/raw metadata
ghi mapping này và kiểm cả hai trước parse/recovery. Không crop theo mô tả Phi.

Attach private Inputs đã duyệt, tên file duy nhất (direct mount hoặc
datasets/owner/slug; không sửa code/path/SHA):

1. Bundle lịch sử đã giải nén: `pilot_manifest.json`, `images/000000.jpg` đến
   `images/000159.jpg`. Chỉ mở sau grant mới; hash và decode trước consumption.
2. `grant_candidate160_{key}.json` + `ledger_candidate160_{key}.json`, mới và
   đúng model/source/ref/config/manifest/policy; không Phi/Smol/Gemma grant.
3. Official checkpoint đã được Owner provision riêng: marker
   `candidate_checkpoint_{key}.json`, `source/{spec['revision']}/` chứa đúng public
   allowlist, `weights/` chứa đúng index+hai safetensors shards theo lock #151.
   Notebook không downloader weights; tuyệt đối không upload data/weights công khai.

Grant schema, marker, ledger, pending policy và quyền: xem
`docs/CANDIDATE160_KAGGLE.md` trong PR này. Chưa chốt policy/driver/mốc review thì
BLOCKED trước data/weights/GPU/attempt. Không dùng các thresholds pilot cũ.
Storage dùng admission vật lý cũ 28 GiB scratch +4 GiB output; cùng filesystem cần
32 GiB free. Không bỏ cổng nếu VM chỉ có 20 GiB. Checkpoint attached read-only.

First image và các mốc behavior đều nằm trong160. Save & Run All liên tục chỉ
khả thi khi Lead duyệt rõ `review_mode=PREAPPROVED_BATCH` cùng batch authorization
đúng execution binding/policy hashes và toàn bộ continuation conditions. Máy ghi
`AUTO_CONTINUE`/`AUTO_STOP` riêng, không giả record Research Lead CONTINUE. Tại
mốc1 và các mốc đã duyệt, kiểm lại durable results/custody, behavior, support GT,
tài nguyên và hạn grant. Thiếu support ở early/later checkpoint cũng STOP.
Bất kỳ lỗi/ngưỡng vi phạm nào dừng ngay, giữ NOT_ATTEMPTED cho phần chưa gọi.

Chưa có phê duyệt batch → BLOCKED trước call; EXTERNAL mode vẫn chờ review Lead
thật và có thể dừng ở checkpoint đầu, không hứa chạy đủ160 trong Save & Run All.
Không chỉnh mode hoặc tự tạo approval để vượt cổng. Worksheets chưa ký và checker:
`python -B -m scripts.candidate160_authority --model {key} --templates data/processed/authority-{key}`.
Xem checklist duy nhất cuối `docs/CANDIDATE160_KAGGLE.md` để đủ quyền và Inputs.

Chỉ Save Version → Save & Run All **một lần** sau quyền riêng, fresh session.
Không interactive run rồi Save & Run All lần nữa; không reuse reservation/attempt.
Mỗi ảnh giữ request/native token IDs/step logits/raw trước parser và kết quả.
Child CUDA FP16 probe trước consumption, rồi kiểm lại trong worker.
RAM/cgroup, disk và GPU0 free theo policy được theo dõi từng ảnh.
NaN/Inf/OOM/lỗi raw hoặc storage dừng; JSON INVALID/repetition/label bias theo
policy đã duyệt. Mọi ảnh chưa gọi là NOT_ATTEMPTED, không SUCCESS.

Download private ZIP và `.sha256.json` được in, kể cả failure/partial. Archive có
manifest/checksums/accounting/report/checkpoint/review và runtime receipts; không
ảnh/weights. Raw HNLO chỉ VALIDATED nếu frozen replay/continuation thực khớp.
CPU scripted PASS không là GPU PASS, chất lượng thật hoặc empirical HNLO PASS.
"""
    result["cells"][0]["source"] = instructions.splitlines(True)
    result["cells"][1]["source"] = code.splitlines(True)
    result["cells"][1]["id"] = "candidate160-launch"
    result["metadata"]["safeshift"] = {"mode": "CANDIDATE160_PREP", "status": "BLOCKED",
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
