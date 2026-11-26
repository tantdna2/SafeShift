# Candidate160 batch — CPU acceptance, 30/10/2026

**CODE PASS trong phạm vi CPU đã kiểm. Execution release BLOCKED.
GPU/real weights/behavior/empirical HNLO UNVERIFIED.**
Phạm vi: hoàn thiện phần mềm trong một Draft PR sau #152 MERGED, từ main
`f79f7bddeac62e8fb8378d6798c25387f45f0f37`. Không Kaggle/GPU/download weights,
private TRAIN/GT/TEST hoặc cấp quyền thật. Đây là bằng chứng do Codex thực chạy,
không independent audit/CI hoặc scientific approval.

## Source và notebook

- Runtime commit: `04090aeb182883da25726a12cbd6371d3d6c9913`.
- Embedded source SHA256: `5189a456b62e5dbef631b712eb0b377044bc84066d6ffd190976e3ee26901e1d`.
- Notebook commit: `93e1751091891d9e68d5eb4770af739f7d982f76`.
- Protected scientific docs restored / isolated proposal commit:
  `ce72d3ef8caf6aabdd3fd9383ff0614e08243574`.
- CPU checker timeout-only commit: `a29e449035aa46360df963ec3a218eb382b584c4`.
  Sau notebook commit không thay runtime/test/builder/notebook source; đổi docs
  và ngân sách thời gian của checker CPU, không đổi experiment time cap.
- Hai notebook tái tạo đúng builder, mọi cell/payload/AST/pins/hash/runtime Git
  bytes và max160; actual CPU no-grant cell execution → BLOCKED/nonconsumed,
  ZIP/sidecar valid. Sáu notebook cũ, adapter/public/checkpoint locks #151,
  scientific protocol/config/decision log và pilot digest giữ nguyên bytes.

## Kết quả thực chạy

| Scope | Tổng | PASS | SKIP | FAIL/ERROR |
| --- | ---: | ---: | ---: | ---: |
| InternVL Windows CPU | 73 | 70 | 3 | 0/0 |
| MiniCPM Windows CPU | 73 | 70 | 3 | 0/0 |
| InternVL Linux CPU | 73 | 72 | 1 | 0/0 |
| MiniCPM Linux CPU | 73 | 72 | 1 | 0/0 |
| Exact-export full Windows | 302 | 265 | 37 | 0/0 |
| Exact-export full Linux | 302 | 270 | 32 | 0/0 |

SKIP không tính PASS. Native candidate tests có nghiệm thu riêng cho từng model;
full-suite candidate opt-ins SKIP không thay thế native receipts. Full suite còn
skip Phi/Smol native cũ/live network-pip và platform-specific checks, không nhận
là đã rerun các model cũ. Public receipts giữ chi tiết từng test/skip.

Hai stack CPython3.11.9 CPU đã pin sẵn từ #151, Windows và WSL2 Linux; public
source/tokenizer/index cache đã hash-lock, không weights hoặc dataset. Native
fixture thực kiểm environment/pip check/compiled NMS và source/loader meta/native
processor; GenerationMixin dùng scripted towers/logits, real VLM forward,
network và CUDA bị chặn. CUDA dependencies chỉ verify official metadata/pins;
không có wheel ABI/driver/T4/FP16 hoặc real checkpoint deserialization PASS.

Mỗi model có đúng160 ảnh tổng hợp (PNG RGBA17×1 dưới tên .jpg) qua native processor,
frozen generation, IDs/logits/raw-before-parse/HNLO replay và archive. Batch fixture
có sentinel GT tổng hợp đủ Normal/hazard ở mốc sớm; không đọc/chọn lại private
manifest. Hai model dùng cùng synthetic ordered plan; production vẫn bắt exact
manifest lịch sử160/order, không selector/supplement/TEST.

## Các nhánh được kiểm

- Full supervisor simulation cho cả hai model: đúng grant/ledger/source/manifest,
  CPU → simulated CUDA preledger → consumption →160 calls → accounting/ZIP/SHA;
  mọi hardware receipt mô phỏng được gắn SYNTHETIC, không GPU result.
- Thiếu/sai quyền, ledger/expiry/hash/source/checkpoint/manifest/token/request;
  batch không được Lead cho phép, copy delegation khác model/attempt/policy:
  fail closed, không tự tải/fallback hoặc retry.
- Prior delegation hợp lệ tổng hợp: không gọi external reviewer/file drop;
  first/early/later checks/recovered custody/support/resources/current deadline
  đều phải đạt mới AUTO_CONTINUE. Không dùng schema Lead CONTINUE giả.
- JSON INVALID, repeat, dominance, false-safe/false-alarm theo policy; nonfinite,
  OOM/load/decode/library/token/raw write/custody/ENOSPC/checkpoint/report/export
  failure, thiếu GT support, time cap, NOT_ATTEMPTED tail,161/duplicate/overwrite.
- Reimport archive/member SHA/CRC/outer sidecar và recover exact raw/native/request/
  configuration/HNLO/accounting; retain partial evidence khi dừng. Export failure
  vẫn giữ directory/bytes, không hứa ZIP hợp lệ khi thiết bị không ghi được.
- Interpreter exact3.11.9, không fallback minor/patch; extra unlocked dependency
  bị chặn trước native import; driver allowlist không vượt CUDA12 compatibility
  floor; per-GPU admission và live RAM/cgroup/scratch/output/headroom riêng.

Development runs không dùng làm nghiệm thu: fixture ban đầu thiếu early Normal
support nên STOP đúng; đã sửa fixture tổng hợp, giữ ca thiếu support riêng. Full
Linux trên notebook commit phát hiện append vào protected scientific log; log
đã phục hồi nguyên bytes, proposal tách riêng. Windows checker cũ timeout600s
trên suite fsync lớn; tăng riêng CPU-check budget1800s, rerun không đổi run caps.
Không coi các lượt lỗi/timeout này là PASS hoặc Kaggle attempts.

## Tái lập và receipts

[Evidence index/checksums](evidence/candidate160_batch_20261030/index.json) khóa
receipts nguyên bản native và release receipts có che synthetic temporary paths.
Release receipt giữ original receipt SHA, stdout/stderr SHA, counts/results và
liệt kê fields được che; không thay numerical evidence hoặc source identity.
Mọi source/test file hash khai báo trong native receipt không đổi trong lượt chạy.
Các thay đổi Git giữa các lượt là docs/checker time budget như liệt kê ở trên;
final full checker dùng exported immutable commit, không worktree suy đoán.

```console
python -B -m scripts.build_candidate160_notebooks --runtime-ref 04090aeb182883da25726a12cbd6371d3d6c9913
<pinned-cpu-python> -B -m scripts.rehearse_candidate160 --model internvl35 --snapshot <public-source> --index <public-index> --output data/processed/candidate160-batch-final/internvl35-new
<pinned-cpu-python> -B -m scripts.rehearse_candidate160 --model minicpm4 --snapshot <public-source> --index <public-index> --output data/processed/candidate160-batch-final/minicpm4-new
python -B -m scripts.check_notebook_release --runtime-ref a29e449035aa46360df963ec3a218eb382b584c4 --output data/processed/candidate160-batch-final/release-new.json
```

Linux full receipt dùng `ce72d3e…` với cùng runtime/tests/notebook bytes, trước
timeout-only checker adjustment. WSL cần Git context explicit tới worktree/metadata
do Windows tạo; Linux checkout thông thường không cần. Local logs/receipts gốc
ở ignored `data/processed/candidate160-batch-final/`, không ghi đè receipts cũ.

[Runbook/checklist duy nhất](../CANDIDATE160_KAGGLE.md#checklist-bàn-giao-duy-nhất)
liệt kê G0/T0/O3, prior batch delegation, policy/runtime/resource/driver approval,
fresh grant/reservation, private historical bundle và official checkpoint Input
còn thiếu. Chỉ chuẩn bị/code acceptance; không EXPERIMENT READY hoặc tự merge.
