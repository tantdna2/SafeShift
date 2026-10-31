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


def notebook(key, ref, repo=ROOT, *, preflight=False):
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
    # Reuse only byte-identical embedded code; attempts themselves are exclusive.
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
    instructions = f"""# SafeShift — {spec['id']} — Candidate160 retry/resume

**Mặc định an toàn: `candidate160_action = "technical_smoke"`.** Codex chạy đúng
notebook này trên Kaggle: một ảnh đầu tiên của manifest TRAIN160 đã khóa, một
native call, tối đa3600 giây gồm setup; không production slot/history/metrics.
Weights/C1/precision/parser/HNLO/source locks và mọi admission production giữ
nguyên. Evidence riêng `data/processed/candidate160_smoke`, ZIP + SHA256 +
`.smoke-result.json`; chỉ receipt cuối TECHNICAL_SMOKE_PASS mới chứng minh
load/inference/raw/export thật. Một ảnh không chứng minh cả160 hoặc khoa học.
Sau ChatGPT review, Antigravity audit và merge được phép, Owner đặt
`candidate160_action = "resume"` để chạy chính thức, hoặc `"rerun"` cho series
mới. Không attach smoke Outputs làm lịch sử production. Thay đổi ảnh hưởng
runtime/source/notebook phải kiểm Kaggle lại; preflight/CPU không đủ bàn giao.

**Owner kích hoạt bằng Save Version → Save & Run All.** Sau review/merge, có thể
chạy lại trong phạm vi đã giao mà không grant/reservation/CONTINUE thủ công.
Mỗi lần chạy có run ID/attempt ID riêng; tối đa160 native calls,12 giờ/lượt,
mỗi ảnh tối đa một call trong lượt. Lỗi kỹ thuật dừng lượt, không tự lặp vô hạn.
Quyết định vận hành: `docs/research/CANDIDATE160_RECOVERY_DECISION_20261031.md`.
Chưa có bằng chứng GPU/model-fit; khoa học và chọn kết quả vẫn PENDING.

Model `{spec['id']}` @ `{spec['revision']}`, Transformers `{spec['transformers']}`.
Adapter base `{BASE}`, package base `{PACKAGE_BASE}`; runtime `{ref}`.
Manifest SHA256 `{MANIFEST}`: giữ đúng160 ảnh TRAIN/thứ tự, không chọn lại ảnh,
TEST, supplement hoặc FULL TRAIN. C1/parser/HNLO/nhãn/metric/protocol không đổi.

1. Chạy notebook `SafeShift_CANDIDATE160_PREFLIGHT_{key}.ipynb` riêng trước,
   cùng Inputs/settings, Internet ON/T4 ×2. Không mở production song song.
2. Attach bundle `pilot_manifest.json` + `images/000000.jpg`…`000159.jpg` và
   checkpoint `candidate_checkpoint_{key}.json`, `source/{spec['revision']}/`,
   `weights/` đúng allowlist/index/shards SHA256. Dataset và Notebook Output
   `notebooks/<owner>/<slug>/` đều hỗ trợ.
3. Khi khôi phục phiên Kaggle mới, dừng phiên cũ trước; attach toàn bộ saved
   Outputs trước đó. Hỗ trợ directory `data/processed/candidate160/` hoặc ZIP
   evidence nguyên vẹn. Giữ cả marker/history/sidecar; không xóa hoặc sửa file.
4. Save & Run All: mặc định `resume` chỉ gọi ảnh chưa có raw/custody hợp lệ,
   kể cả sau OOM/load error/ngắt phiên. INVALID hợp lệ cũng đã hoàn thành;
   không gọi lại để tìm kết quả tốt. Raw hợp lệ chưa có result được replay
   trong recovery plan mới, không sửa lịch sử. Lịch sử thiếu/mâu thuẫn → BLOCKED.
5. Muốn chạy lại toàn bộ160 ảnh, đặt `candidate160_action = "rerun"` tại dòng
   cấu hình đầu code cell rồi Save & Run All; đó là FULL_RERUN có ID mới,
   giữ mọi lượt cũ riêng. Không đổi hashes, protocol, nguồn hoặc model revision.
6. Download ZIP + `.sha256.json` kể cả partial/lỗi, giữ private. Nếu hard kill
   chưa có ZIP, attach retained Output directory. Không chạy hai jobs cùng model
   đồng thời. OS lock chống trùng cùng workspace và worker còn sống; hai VM độc
   lập không có distributed lock, Owner phải bảo đảm phiên trước đã dừng và
   cung cấp đủ lịch sử. Không coi thiếu Inputs lịch sử là bằng chứng chưa chạy.

Raw IDs/logits/request bền vững trước parser; snapshot/call/error/attempt/hash
không bị ghi đè. `recovery_plan.json` liệt kê mọi lượt và ảnh pending/durable;
`lineage_accounting.json` chỉ đếm vận hành, không chọn hoặc gộp kết quả khoa học.
Lượt INITIAL/RECOVERY/FULL_RERUN tách riêng, scientific_selection=PENDING,
pooling_allowed=false. COMPLETED_AWAITING_REVIEW không phải qualification.

Worker CPython3.11.9/Linux x86_64, torch2.6.0+cu124/torchvision0.21.0+cu124,
CUDA12.4/FP16/eager/batch1/cuda:0; GPU1 chỉ quan sát. Provision phần mềm pinned,
không tải weights/fallback. Giữ preflight hash/decode160/ABI/driver/CUDA/RAM/
cgroup/disk,28 GiB scratch +4 GiB output trước consumption; OOM vẫn dừng.
NaN/Inf/raw/custody/resource/time errors dừng; behavior chỉ ghi nhận vì chưa có
ngưỡng khoa học: không tự đặt ngưỡng hoặc nâng scientific PASS.

Phải được ChatGPT kiểm GitHub và Antigravity audit độc lập trước merge.
CPU synthetic PASS không là Kaggle/GPU PASS. Quyền bên thứ ba và TEST vẫn đóng.
"""
    result["cells"][0]["source"] = instructions.splitlines(True)
    result["cells"][1]["source"] = code.splitlines(True)
    result["cells"][1]["id"] = "candidate160-launch"
    result["metadata"]["safeshift"] = {"mode": "CANDIDATE160_OWNER_ACTIVATED", "status": "AWAITING_INDEPENDENT_REVIEW",
        "base": BASE, "package_base": PACKAGE_BASE, "runtime_ref": ref, "model_key": key, "model": spec,
        "source_sha256": source_hash(repo), "manifest_sha256": MANIFEST,
        "config": config(key), "configuration_hashes": configuration_hashes(key),
        "max_images": 160, "gpu": "UNVERIFIED", "behavior": "UNVERIFIED"}
    if preflight:
        code = code.replace("from safeshift.candidates.train_runtime import launch_owner as launch",
                            "from safeshift.candidates.train_preflight import launch_preflight as launch")
        code = code.replace(", owner_start=True)", ")")
        code = code.replace("candidate160_code", "candidate160_preflight_code")
        code = code.replace("root.mkdir(parents=True, exist_ok=False)", "root.mkdir(parents=True, exist_ok=True)")
        result["cells"][1]["source"] = code.splitlines(True)
        result["cells"][1]["id"] = "candidate160-preflight"
        result["cells"][0]["source"] = f"""# SafeShift — {spec['id']} — preflight không tiêu lượt

Sau review/merge, attach đúng bundle160 TRAIN và checkpoint Dataset hoặc Notebook
Output `notebooks/<owner>/<slug>/`. Chọn Internet ON và T4 ×2, Run All notebook
preflight này. Có thể chạy lại; không tạo execution/Owner slot, không tải/nạp
weights và không gọi mô hình. Hash index/shards đọc từ Input; CPU native empty
meta/processor dùng ảnh tổng hợp; child CUDA FP16 chỉ là phép toán tensor.

Python3.13 kernel chỉ điều phối. Worker CPython3.11.9 tự provision từ archive
python-build-standalone20240726 đã khóa URL/size/SHA256; không cần cài thủ công.
Software pins/cu124/precision/model revision/C1/parser/HNLO giữ nguyên.
Kiểm đồng thời cấp phát thật28 GiB scratch +4 GiB output; dung lượng free không
thay thế bằng chứng cấp phát. Không có CUDA/model-fit PASS từ CPU local.

**Cách chạy diagnostic trước thực nghiệm:** tạo notebook Kaggle riêng bằng file
này, attach cùng bundle/checkpoint Inputs của run160; T4 ×2, Internet ON.
Chạy Run All/Save & Run All của preflight, không mở notebook160 cùng lúc.
Preflight đọc/hash/decode Inputs, tải software pinned, cấp phát tạm28+4 GiB và
xóa scratch thuộc session; giữ evidence trong `data/processed/candidate160_preflight`.
Không cần grant/CONTINUE hoặc approval lặp lại trong phạm vi Owner đã cấp.

Download cả **ZIP**, **ZIP.sha256.json** và **.preflight-result.json** được in.
Receipt cuối `.preflight-result.json` phải có `evidence_export=VERIFIED`;
`preflight.json` trong ZIP còn ghi export PENDING vì được seal trước export.
Thiếu receipt cuối/checksum sai/export lỗi/partial → BLOCKED, giữ mọi file.
Receipt ghi từng check PASS/BLOCKED/NOT_RUN và tách ENVIRONMENT_OBSERVED,
CPU_SOFTWARE_PASS, LIVE_GPU_PREFLIGHT_PASS, WEIGHTS_LOADED, INFERENCE_VERIFIED,
SCIENTIFIC_QUALIFIED. Ba mức cuối vẫn NOT_RUN/UNVERIFIED trong preflight.
Chỉ PRELOAD_CHECKS_PASS_MODEL_UNVERIFIED khi mọi cổng được kiểm và export xác minh;
không READY hoặc bảo đảm peak memory/quality. Không tự chạy notebook160 sau đó.
Run160 vẫn kiểm lại mọi admission trước consumption vì tài nguyên có thể đổi.
Preflight không cấp quyền replay một lượt đã consumed/unknown.

Nếu cần thông tin Kaggle thực tế, gửi status/checks/levels và lỗi từ receipt
cuối hoặc ZIP private cho người review; không publish ảnh, weights hoặc secrets.
Code/local CPU PASS không phải GPU PASS; HEAD mới vẫn cần ChatGPT kiểm GitHub
và Antigravity audit độc lập trước merge. Quy tắc mới chưa COMPLETE trên main.

Runtime `{ref}`, source SHA256 `{source_hash(repo)}`.
""".splitlines(True)
        result["metadata"]["safeshift"]["mode"] = "CANDIDATE160_NO_ATTEMPT_PREFLIGHT"
    else:
        code = code.replace("import base64, hashlib, json, pathlib, sys, zlib",
                            'import base64, hashlib, json, pathlib, sys, zlib\n    candidate160_action = "technical_smoke"  # after review/merge Owner selects "resume" or "rerun"')
        code = code.replace(", owner_start=True)", ", owner_start=True, action=candidate160_action)")
        result["cells"][1]["source"] = code.splitlines(True)
        compile(code, "candidate160_notebook", "exec")
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
        path = ROOT / f"notebooks/SafeShift_CANDIDATE160_PREFLIGHT_{key}.ipynb"
        path.write_text(json.dumps(notebook(key, args.runtime_ref, preflight=True), indent=1, ensure_ascii=False)+"\n",
                        encoding="utf-8", newline="\n")
        print(path.relative_to(ROOT))

    path = ROOT / "notebooks/SafeShift_CANDIDATE160_MINICPM4_FP32_ATTENTION_SMOKE.ipynb"
    path.write_text(json.dumps(effective_notebook(args.runtime_ref), indent=1, ensure_ascii=False)+"\n",
                    encoding="utf-8", newline="\n")
    print(path.relative_to(ROOT))

    for key in KEYS:
        suffix = "_FP32" if key == "minicpm4" else ""
        path = ROOT / f"notebooks/SafeShift_CANDIDATE160_PRODUCTION_{key}{suffix}.ipynb"
        path.write_text(json.dumps(production_notebook(key, args.runtime_ref), indent=1, ensure_ascii=False)+"\n",
                        encoding="utf-8", newline="\n")
        print(path.relative_to(ROOT))


def effective_notebook(ref, repo=ROOT):
    """Separate one-image technical deliverable; cannot switch to full production."""
    from safeshift.candidates.minicpm_resampler_fp32 import ID, descriptor
    nb = notebook("minicpm4", ref, repo)
    code = "".join(nb["cells"][1]["source"])
    code = code.replace('candidate160_action = "technical_smoke"  # after review/merge Owner selects "resume" or "rerun"',
                        'candidate160_action = "technical_smoke_resampler_fp32_v1"  # only the authorized numerical technical trial')
    code = code.replace('action=candidate160_action)', 'action="technical_smoke_resampler_fp32_v1")')
    compile(code, "minicpm-effective-smoke", "exec")
    nb["cells"][1]["source"] = code.splitlines(True)
    nb["cells"][0]["source"] = f"""# SafeShift — MiniCPM-V-4 narrow FP32 resampler technical trial

Owner authorizes engineering verification only, not a scientific baseline or
official160-image experiment. This notebook always executes exactly the
technical action `technical_smoke_resampler_fp32_v1`; it has no full-run action.
Same locked TRAIN160 bundle/order and first original image (ordinal0), same
checkpoint/revision, FP16 weights, C1, eager, parser and HNLO. Only native
resampler score/softmax/value product compute in FP32, then cast to native
dtype before out_proj. No original source/checkpoint locks are modified.

Effective implementation `{ID}`; SHA256 `{descriptor()['implementation_sha256']}`.
One model load/one image/one native call,3600 seconds including setup. Private
evidence/ZIP/SHA256/final receipt under candidate160_smoke_resampler_fp32_v1;
separate run and series, no history import/resume/scientific metrics/pooling.
Keep all previous FP16 failure Outputs unchanged and separate. Do not attach
smoke outputs as production history. No TEST or third-party Inputs.

Attach `nguynanhtn/safeshift-pilot-input` and the original Owner MiniCPM checkpoint
Notebook Output; Internet ON/T4x2, GPU0 inference only. Codex executes bounded
real Kaggle smoke first. No model fit/finite inference PASS until final receipt
verifies actual weights/CUDA/raw/parser/HNLO handling/custody/cleanup/archive.
One-image PASS cannot establish numeric HNLO, quality or all160/long-run/rare
inputs. Keep Draft PR156 for ChatGPT review then independent audit decision;
no merge or full Owner run is authorized by this technical trial.

Runtime `{ref}`, embedded source `{source_hash(repo)}`.
""".splitlines(True)
    nb["metadata"]["safeshift"].update(mode="MINICPM_RESAMPLER_FP32_TECHNICAL_ONLY", max_images=1,
        config=config("minicpm4", implementation=ID),
        configuration_hashes=configuration_hashes("minicpm4", implementation=ID),
        effective_implementation=descriptor())
    return nb


def production_notebook(key, ref, repo=ROOT):
    """The delivery route defaults to bounded engineering, with portable recovery."""
    from safeshift.candidates.minicpm_resampler_fp32 import ID, descriptor
    implementation = ID if key == "minicpm4" else None
    nb = notebook(key, ref, repo)
    code = "".join(nb["cells"][1]["source"])
    code = code.replace('candidate160_action = "technical_smoke"  # after review/merge Owner selects "resume" or "rerun"',
                        'candidate160_action = "qualify"  # three fixed TRAIN cases; official FP32 stays gated')
    code = code.replace('action=candidate160_action)',
                        f'action=candidate160_action, implementation={implementation!r})')
    code += (f'\nif candidate160_action in ("qualify", "qualify_rerun"):\n'
             f'    from safeshift.candidates.train_route import verify_portable_recovery\n'
             f'    recovered = verify_portable_recovery(evidence, {key!r}, expected_source_sha256, root, {ref!r}, {implementation!r})\n'
             f'    print("Portable recovery evidence:", recovered)\n')
    compile(code, "candidate160-production-engineering", "exec")
    nb["cells"][1]["source"] = code.splitlines(True)
    nb["cells"][0]["source"] = f"""# SafeShift — {model(key)['id']} — production engineering route

Default action `qualify`: exactly three predeclared original TRAIN160 ordinals
0,15,111 (first; minimum area; maximum height/width, first ties), one load and
at most three native calls/3600 seconds. Then a fresh workspace imports only
the sealed ZIP and verifies resume is a zero-load/zero-call no-op. This tests
the production supervisor, child, controller, raw custody, portable history
and export. Scientific metrics/selection are excluded; no full160 is run.

Implementation: `{implementation or 'original-internvl35-fp16'}`.
Model/revision/checkpoint/TRAIN160/C1/parser/HNLO remain locked. FP32 MiniCPM
changes only resampler scores/softmax/value product; weights/output remain FP16.
Its official `resume`/`rerun` action is BLOCKED_PENDING_SCIENTIFIC_DECISION,
enforced before Inputs/consumption/model load, including direct worker calls.
No notebook edit or fabricated approval reference unlocks that scientific gate.
An explicit Owner/Lead decision must adopt the named arithmetic implementation
for official scientific TRAIN160, followed by reviewed activation code.

InternVL official `resume`/`rerun` remains available only after ChatGPT exact
HEAD review, independent Antigravity audit and separately authorized merge.
Owner runs full160 personally. Do not attach technical qualification/smoke
Outputs as official history. Official, technical, FP16 and FP32 have distinct
campaign/slot/config/source/series bindings; no pooling or favorable selection.

Attach the authorized pilot bundle and matching original checkpoint Output;
Internet ON/T4x2. Keep every error/partial directory/ZIP/sidecar. Fresh VM:
attach complete prior Outputs before resume; stop prior jobs first. OS locks
cover a shared workspace only, not independent Kaggle VMs.

Archive/final `.qualification-result.json` must both verify. INVALID is a
durable result; HNLO may remain unavailable. Three images do not establish
full160 memory/time/model quality or numeric HNLO.
Runtime `{ref}`; source `{source_hash(repo)}`.
""".splitlines(True)
    nb["metadata"]["safeshift"].update(mode="CANDIDATE160_PRODUCTION_ENGINEERING_V1",
        default_action="qualify", technical_ordinals=[0, 15, 111], official_fp32_scientific_gate="BLOCKED",
        config=config(key, implementation=implementation),
        configuration_hashes=configuration_hashes(key, implementation=implementation))
    if implementation:
        nb["metadata"]["safeshift"]["effective_implementation"] = descriptor()
    return nb


if __name__ == "__main__":
    main()
