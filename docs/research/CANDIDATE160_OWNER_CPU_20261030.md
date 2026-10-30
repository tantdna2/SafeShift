# Candidate160 Owner activation — CPU acceptance, 30/10/2026

Base main sau #153: `fc1e454212455685e1775601ebfd6aab9535c932`.
Phạm vi chỉ synthetic CPU, public source/tokenizer/index cache đã có và empty/meta
loader/scripted logits. Không GPU, real model forward/weights hoặc private data.
Đây là kiểm thử do Codex thực chạy, không independent audit hoặc scientific PASS.

## Source và mức bằng chứng

- Runtime: `93bc2f110822c3cfd3c910da8f8adb11a0d9ac1f`.
- Notebook + UTF-8/builder snapshot: `f427e59c90f15c5bb87db26ff1aad5e038310af8`.
- Embedded source SHA256: `b951c56e77a6e06f0c572cc514c9489efe3b664753749bbfebee16a1d14b4ead`.
- Hai configuration hashes/model không đổi so với #153; adapter/config effective,
  checkpoint/public locks, C1/parser/HNLO, pilot engine và sáu notebook cũ giữ bytes.
- Windows CPython3.11.9, hai CPU stack đã pin/cache public từ #150/#151; không
  cài mới/tải weights hoặc xem bundle thật. Native tests chặn network/CUDA và
  native VLM forward, chỉ dùng empty/meta loader, processor thật và scripted logits.
- Linux kiểm khóa dùng WSL2 CPython3.11.9, chỉ stdlib synthetic tests, không native
  qualification Linux mới. Không nâng CPU evidence thành T4/FP16/CUDA PASS.

## Kết quả thực chạy

| Scope | Tổng | PASS | SKIP | FAIL/ERROR |
| --- | ---: | ---: | ---: | ---: |
| InternVL Windows native + integration | 67 | 64 | 3 | 0/0 |
| MiniCPM Windows native + integration | 67 | 64 | 3 | 0/0 |
| Linux Owner activation/scope/atomic slot | 3 | 3 | 0 | 0/0 |
| Exact-export full Windows | 310 | 273 | 37 | 0/0 |

Exact-export full suite:874,162 giây, CODE_PASS; cả8 notebook kiểm inventory,
deterministic builder, embedded payload/SHA và AST/empty outputs. Candidate cells
thật chạy trong synthetic CPU sandbox với Inputs thiếu → BLOCKED/nonconsumed,
ZIP/sidecar valid; không phải kiểm việc thiếu grant. Full checker giữ generic
`release_status=BLOCKED` vì chỉ kiểm CPU, không cấp release hoặc thay audit trước
merge mà Owner yêu cầu. Không thêm thủ tục giấy phép Owner từ cờ checker này.

Mỗi model **15/15 native tests PASS**, gồm đúng160 ảnh tổng hợp RGBA17×1 qua
native processor/GenerationMixin/scripted logits → Owner run controller →
request/token IDs/raw/logits/config/parser/HNLO replay → ZIP/checksums.
Đây không real checkpoint forward hoặc model predictions. Native empty safetensors
fixture chỉ kiểm plumbing, không deserialize checkpoint thật.

Ba SKIP/model đều Windows không có permission tạo symlink (root/directory/file);
không tính PASS. Full suite default không bật opt-in native; các native receipts
riêng là bằng chứng thực thi cho hai model, không lấp skip Phi/Smol/live network.

Full Owner supervisor simulation kiểm cả hai model: không grant/reservation
Inputs hoặc reviewer/file CONTINUE, tự tạo execution/UUID/fixed slot/consumption,
CPU → simulated CUDA → consumption →160 calls → raw/accounting/archive, cùng
ordered synthetic plan. Hardware receipts mô phỏng gắn SYNTHETIC, không GPU result.

Owner negative tests kiểm missing activation, wrong source/ref/config/model/
manifest/split/cap/retry/resume/policy/expiry/fields, concurrent slot, UUID/source
change không đổi slot, attached saved history/direct+nested layout, execution/
slot drift trước consume, manifest/checkpoint/storage/Python/CPU/GPU/CUDA failure,
consumption ENOSPC→UNKNOWN, worker timeout/export failure, input mutation/raw/
custody/nonfinite/OOM/resource/deadline,161/duplicate/no-overwrite và tail accounting.
Tests cơ chế grant/batch cũ giữ coverage quyền/stop/recovery riêng.

Owner behavior tests cố ý cho **160 INVALID** và **160 cùng một nhãn/sequence**
ở cả hai model bằng fake backend, vẫn hoàn tất và ghi đầy đủ observations. Đây
là kiểm chứng thay đổi chính sách observe-only, không khẳng định behavior đó
được scientific approval hoặc qualification. No-retry/no-resume vẫn bắt buộc.

## Receipts và tái lập

Public summaries và [checksum index](evidence/candidate160_owner_20261030/index.json)
giữ original receipt/log SHA256, source-file hashes, per-test outcomes, counts,
native source/runtime details và phạm vi. Không commit raw/output/ảnh/weights.
Native summary bỏ verbose tensor/environment path/freeze sections; counts và
test outcomes không sửa. Full summary bỏ stdout/stderr, giữ hashes và nguyên
counts/skip details, notebook checks. Original receipts/logs ở ignored
`data/processed/owner160/`.

```console
python -B -m scripts.build_candidate160_notebooks --runtime-ref 93bc2f110822c3cfd3c910da8f8adb11a0d9ac1f
<pinned-cpu-python> -B -m scripts.rehearse_candidate_integration --model internvl35 --snapshot <public-source> --index <public-index> --output data/processed/owner160/internvl-new
<pinned-cpu-python> -B -m scripts.rehearse_candidate_integration --model minicpm4 --snapshot <public-source> --index <public-index> --output data/processed/owner160/minicpm-new
python -B -m scripts.check_notebook_release --runtime-ref f427e59c90f15c5bb87db26ff1aad5e038310af8 --output data/processed/owner160/release-new.json
```

Linux targeted checks: `test_candidate160_owner.OwnerExecutionTests.` với
`test_atomic_slot_blocks_concurrent_uuid_source_change_and_attached_history`,
`test_explicit_activation_distinct_schema_no_fabricated_approval`,
`test_scope_model_hash_manifest_cap_retry_resume_policy_and_time_fail_closed`.
Chạy `python -B -m unittest` từ repo root với `PYTHONPATH=.:tests`; receipt giữ
Python/platform/source/test SHA và kết quả. Không yêu cầu WSL ở Kaggle.

Development không dùng nghiệm thu cuối: lượt Owner suite7/7 và native15/15/model
trước freeze; kiểm notebook phát hiện encoding tiếng Việt sai do shell pipe, đã
sửa UTF-8 và cả3 notebook tests PASS trên snapshot cuối. Checker từ chối short SHA
đúng hợp đồng; lượt final dùng full40 SHA, không ghi đè receipt lỗi. Linux receipt
helper ban đầu thiếu repo trong PYTHONPATH, đã sửa invocation và rerun3/3 PASS.
Các lỗi setup/QA này không phải Kaggle attempts hoặc GPU failures.

Đối soát thủ công29 protected files so base PASS; UTF-8/local links/diff-check
PASS. Không claim independent audit/CI. Các update sau snapshot chỉ docs/receipts,
không thay runtime/test/builder/notebook source đã nghiệm thu.

[Quyết định Owner/policy delta](CANDIDATE160_OWNER_DECISION_20261030.md) và
[runbook](../CANDIDATE160_KAGGLE.md) mô tả giới hạn/cách chạy. Trạng thái GPU,
VRAM thực tế, checkpoint fit, classification quality và empirical HNLO UNVERIFIED.
