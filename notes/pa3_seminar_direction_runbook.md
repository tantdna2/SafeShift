# PA3 Seminar Direction — một lượt chẩn đoán GPU duy nhất (90 ảnh TRAIN)

## Đối chiếu CURRENT — 13/10/2026

Main đã xác minh `3a52b549d623bdb4b8b6753abe3adf116bbc6100` (PR #98 merged):
[authority](../configs/pa3/seminar_direction_authority.v1.json) có grant **non-null**,
max_runs=1, retry=false, TRAIN only, test_access=false. Mô tả grant-null/NOT_EXECUTED
bên dưới là snapshot PREP; không phải trạng thái release mới nhất.
Người dùng báo **GO_PA3**, phiên Kaggle đã restart, nhưng chưa có archive được
kiểm toán độc lập. Verdict commit vẫn là placeholder PREP; không có số liệu thật
được xác minh ở đây. Quyết định hướng mới: [DEC-PA3-006](../DECISIONS.md#dec-pa3-006--seminar-pa3-direction-and-baseline-priority-2026-10-13).

**Ưu tiên thu hồi artifact đã lưu và CPU audit theo mục 6; không thực hiện lại
Run All ở mục 4.** Grant không chứng minh attempt còn trống; không retry sau restart.
Quyền gắn với source/topology đã duyệt, không chuyển sang HEAD tài liệu này.
Mục 3–4 giữ làm truy vết release/chạy gốc; đề xuất chạy mới cần quyết định riêng.


Ngày: 2026-10-13 (Asia/Bangkok). BASE đã xác minh trên GitHub:
`28ab17b094da91006a785d0b694c4d035db96902`. Phạm vi: **exploratory decision
diagnostic** để Research Lead quyết định có chuyển trọng tâm Seminar sang PA3
(raw-logit anomaly discrimination) hay không. Không phải pilot, holdout,
clean/independent evaluation hay confirmatory benchmark.

**Trạng thái tại PREP (lịch sử): LOCKED.** `configs/pa3/seminar_direction_authority.v1.json`
có `"grant": null`; mọi đọc manifest/ảnh và model load đều bị từ chối
(`PA3_DIAGNOSTIC_GRANT_PENDING_RESEARCH_LEAD`). Draft PR, SETTINGS, checksum hay
receipt không cấp quyền. Không có lượt GPU nào đã chạy; verdict hiện tại là
[PA3_SEMINAR_DIRECTION_VERDICT.md](../PA3_SEMINAR_DIRECTION_VERDICT.md) =
`KEEP_CURRENT_DIRECTION / NOT_EXECUTED`.

## 1. Những gì được tái sử dụng (không viết lại)

| Thành phần | Nguồn |
|---|---|
| Scorer raw-only Qwen, raw-before-parse journal, token IDs, raw logits mỗi bước | `safeshift/pa3/native/qwen.py` (không đổi logic sinh) |
| PA3 score `logsumexp(z1,z2,z3) - z4`, SUCCESS/INVALID/TECHNICAL_ERROR | `native_score.score` |
| CPU audit / recomputation | `native_audit.audit` |
| AUROC (tie credit 0.5), endpoint, report, quantiles | `analysis.endpoint/report`, `ls1.evaluate.auc` |
| Kiểm tra technical run 4 ảnh đã PASS | `pilot.prior_technical` trên journal kỹ thuật đã niêm phong, với source `13ea2fb` của chính nó |
| Launcher OFFLINE, runtime/model archive, network deny | `kaggle.launch`, cell bootstrap y hệt notebook kỹ thuật |
| Runtime Prep / Model Prep Output | Dataset Kaggle Owner đã lưu (`pa3-runtime-input`, `pa3-model-input`) |

Technical run `pa3-qwen-technical-first` và `configs/pa3/feasibility_authority.v1.json`
(gồm `pilot: null`) **không bị sửa**; gate mới từ chối nếu file đó khác bytes tại BASE.

## 2. Cohort đã khóa (CPU, chỉ TRAIN)

Builder: `python -m safeshift.pa3.native.seminar_cohort --dataset-root data/raw/InspecSafe-V1/train --ls1-handoff <tài liệu LS1>`.
Đầu vào: W1 `duplicate_leakage_audit.json` (SHA-256 `16039f23…02d6`, kiểm tra bắt buộc),
`dataset_validation.json` (`65bfebb0…e6c3`), fingerprint `1a52f907…399c`; byte ảnh + JSON/TXT
**chỉ của 90 ảnh được chọn**. Không mở đường dẫn TEST, không decode ảnh, không model.

Quy tắc (công bố trong code `seminar.RULE`, được nhúng và kiểm tra trong manifest):

- Seed `pa3-seminar-direction-2026-10-13-v1`; xếp hạng SHA-256(seed|sample_id).
- Thứ tự cố định coal_conveyor, oil_chemical, power, tunnel (10+10 mỗi miền, nhóm chính), metallurgy (5+5, mô tả phụ); Normal trước Anomaly.
- Anomaly: lấy trước tối đa 2 Level03 hợp lệ theo rank (floor), rồi lấp đầy từ mọi Anomaly còn lại theo rank.
- Tối đa 1 ảnh mỗi mandatory group: exact-byte TRAIN, Normal point ID, cặp cùng point folder (`cohort.candidate_groups`).
- Loại 7 TRAIN ID trùng chính xác với TEST theo W1 (gồm `metallurgy-Level01-SuspendedRail-002660-001`).
- Ghi nhận nhưng không loại: near-duplicate/source-family chưa phân xử, exposure P2 toàn pool, xung đột folder/text domain.
- Thiếu quota → STOP, không xuất manifest; không hạ N, đổi seed hay nới quy tắc.

Kết quả thực tế: **90/90 ảnh qua kiểm tra path + SHA-256 + metadata, không thiếu quota.**

| Miền | Normal | Anomaly | Level của Anomaly |
|---|---:|---:|---|
| coal_conveyor | 10 | 10 | L01=6, L02=3, L03=1 |
| oil_chemical | 10 | 10 | L01=8, L02=2 |
| power | 10 | 10 | L01=4, L02=6 |
| tunnel | 10 | 10 | L01=3, L02=5, L03=2 |
| metallurgy | 5 | 5 | L01=4 (đều xung đột text-domain), L03=1 |
| Tổng | 45 | 45 | L01=25, L02=16, L03=4 |

Toàn bộ Level03 TRAIN hợp lệ được đại diện khi có thể: coal có 1, metallurgy có 1, tunnel 2/6 (floor).
Không ảnh nào trùng 10 ID LS1 trong tài liệu. 90 ảnh thuộc 42 thành phần bảo thủ; một thành
phần nối bởi cạnh near/source-family **chưa phân xử** chứa 48/90 ảnh (43/80 nhóm chính), gồm
**42/45 Anomaly** (37/40 Anomaly nhóm chính) nhưng chỉ 6 Normal. Ảnh Anomaly vì vậy có thể phụ
thuộc mạnh; bỏ thành phần này làm AUROC theo miền không xác định. Không có khoảng tin cậy đáng
bảo vệ.

| File | SHA-256 |
|---|---|
| `data/manifests/pa3_seminar_direction_cohort.v1.json` (GT, miền, quan hệ, exposure) | `83959e27c04d1cf7f90fcbef501a87fdf970c32d542b61fbecb4b75f26b38da3` |
| `data/manifests/pa3_seminar_direction_inference.v1.json` (chỉ ID/locator/hash, không GT) | `d59af02b5fe53807ee60a373aef620fae75887bceb9aced6156a82d72461ebce` |
| `data/manifests/pa3_seminar_direction_cohort_receipt.v1.json` | receipt builder, input hash, lệnh |

Inference chỉ đọc manifest GT-free; manifest cohort (nhãn) chỉ được nối **sau khi raw journal
đã niêm phong**. Sample ID/đường dẫn gốc vẫn chứa tên miền/Level của dataset; model chỉ nhận
pixel + prompt C1 cố định. Thứ tự inference = SHA-256(seed|order|ID) để lượt dừng giữa chừng
không bị lệch theo miền.

## 3. Đường chạy riêng và quyền

`mode=seminar-diagnostic`, `run_id=pa3-qwen-seminar-direction-90`, đúng 90 ảnh, 1 lượt,
batch 1, T4, FP16, SDPA, C1, Qwen2.5-VL-3B @ `66285546…`, TRAIN only, `test_access=false`,
`retry=false`. Thứ tự trong child (`seminar_workflow.execute_diagnostic`):

1. Authority (trước mọi đọc source/runtime/data).
2. Source byte-check, exact runtime/snapshot, T1 (28 biến thể).
3. CPU audit lại technical run 4 ảnh đã niêm phong với source `13ea2fb` của nó (seal + bundle hash phải khớp grant).
4. Kiểm tra tồn tại + SHA-256 của **cả 90** ảnh, không decode; sai một ảnh → dừng trước model load.
5. Niêm phong `RUN-exposure`: cả 90 ID được ghi là observed trước lần decode đầu tiên.
6. Một model load (ticket dùng một lần), một lượt qua 90 ảnh; mỗi ảnh: kiểm tra membership + byte hash trước decode,
   so pixel, ticket dùng một lần, raw output/token IDs/raw logits ghi bền trước parse; telemetry thời gian/bộ nhớ CUDA ở `RUN-telemetry`.
7. Lỗi kỹ thuật ở một ảnh → ghi bằng chứng và **dừng**; không retry, không bỏ qua ảnh.
8. Niêm phong raw → nối GT → CPU audit → `analysis.report` → chỉ số/quyết định → `RUN-report`, `RUN-verdict`
   (cả khi lỗi: verdict bảo thủ NOT_EXECUTED/INCOMPLETE).

### Điểm Research Lead phải phê duyệt (release authority-only)

Sau ChatGPT review và Antigravity audit **của chính commit đầu PR (F1)**:

1. Lead xác nhận: cohort/inference manifest + hash ở trên; quy tắc chọn mẫu; tiêu chí ở mục 5;
   phạm vi chẩn đoán với các phụ thuộc chưa xác minh đã công bố.
2. Lead cung cấp từ artifact đã lưu: `technical_seal_sha256` = SHA-256 của
   `pa3-qwen-technical-first-qualification/seal.json`; `technical_source_bundle_sha256` = SHA-256 bundle
   OFFLINE `13ea2fb` đã giữ; một chuỗi `approval` tham chiếu quyết định của Lead.
3. F1 phải là **một commit duy nhất có đúng một parent = `base`** (gate kiểm tra
   `rev-list --parents -n 1 F1 == [F1, base]`). Nếu nhánh PR có nhiều commit, gộp thành một
   commit trên `base` và review/audit lại đúng SHA đó trước khi tạo F2.
   Tạo commit F2 con trực tiếp của F1, **chỉ** sửa `configs/pa3/seminar_direction_authority.v1.json`:

```json
{
  "base": "<SHA main tại lúc merge = first parent của merge>",
  "implementation": "<SHA F1>",
  "scope": "<giữ nguyên object scope hiện có>",
  "grant": {
    "approval": "<tham chiếu quyết định Research Lead>",
    "cohort_manifest_sha256": "83959e27c04d1cf7f90fcbef501a87fdf970c32d542b61fbecb4b75f26b38da3",
    "inference_manifest_sha256": "d59af02b5fe53807ee60a373aef620fae75887bceb9aced6156a82d72461ebce",
    "technical_seal_sha256": "<64 hex>",
    "technical_source_bundle_sha256": "<64 hex>"
  }
}
```

4. Merge bằng **standard Merge Commit** (không squash/rebase); cây merge phải bằng cây F2.
   Nếu main đã tiến, dừng: cập nhật F1, review/audit lại, rồi mới F2. Gate kiểm tra topology
   BASE→F1→F2→M, F2 chỉ đổi file authority, bytes authority, file authority kỹ thuật không đổi, source sạch.
   Topology Git không phải chữ ký; Lead xác minh merge thực tế trên GitHub.

## 4. Owner chạy Kaggle đúng một lần

1. Trên Linux sạch tại merge M: `git -c core.autocrlf=false clone https://github.com/tantdna2/SafeShift.git source && cd source && git checkout --detach M && python -m safeshift.pa3.native.kaggle --bundle-source --output data/processed/pa3_seminar_release`.
   Upload `pa3_source.bundle` + `pa3_source_release.json` thành Dataset riêng tư mới (ví dụ `pa3-seminar-direction-source`).
2. Notebook mới từ `notebooks/pa3_seminar_direction_kaggle.ipynb`; GPU T4; **Internet OFF**.
3. Input: source mới; `pa3-model-input`; `pa3-runtime-input` (tái dùng); `pa3-reviewed-source` (bundle kỹ thuật `13ea2fb`);
   Dataset chứa thư mục qualification kỹ thuật đã giải nén; `InspecSafe-V1-Kaggle`. **Không** gắn prep-source.
4. SETTINGS (đường dẫn tương đối sau `/kaggle/input/`, copy từ Input panel):
   `source_commit`=M; `source_bundle_input/sha256`; `model_input`; `runtime_input`; `runtime_inventory_input/sha256`;
   `dataset_input` = thư mục TRAIN chứa `DATA_PATH/train/Annotations` (gate từ chối mọi đường dẫn có thành phần `test`);
   `cohort_manifest_sha256`, `inference_manifest_sha256`, `technical_seal_sha256`, `technical_source_bundle_sha256` = đúng grant;
   `technical_run_input` = thư mục `pa3-qwen-technical-first-qualification`; `technical_source_bundle_input`.
   Để trống mọi field khác.
5. Trước Run All, chỉ bằng File browser (không chạy code), xác nhận tồn tại
   `<dataset_input>/DATA_PATH/train/Annotations/Normal_data/coal_conveyor-Level04-SuspendedRail-001037/coal_conveyor-Level04-SuspendedRail-001037-001.jpg`
   (ảnh đầu tiên của manifest). Nếu bố cục Kaggle khác: **dừng, báo blocker**, không sửa code tại chỗ.
6. Ghi một attempt vào ledger ngoài của Lead, rồi **Run All đúng một lần**. Không chạy lại dưới bất kỳ run ID nào.
7. Tải về toàn bộ `data/processed/pa3_source/pa3-qwen-seminar-direction-90/data/processed/pa3_qwen/pa3-qwen-seminar-direction-90*`
   (run, `-launch`, `-preflight`, `-exposure`, `-telemetry`, `-tickets`, `-report`, `-verdict`, mọi `.tar.gz` + `.sha256.json`),
   `data/processed/pa3_bootstrap/pa3-qwen-seminar-direction-90*` và log Kaggle — kể cả khi thất bại. Không sửa/xóa thư mục chưa niêm phong.

## 5. Chỉ số và quy tắc quyết định (chốt trong `seminar_verdict.py` trước inference)

Bắt buộc xuất (cùng lượt, CPU, không gọi model lại): accuracy 4 mức và nhị phân (mẫu số mọi ảnh dự kiến
và chỉ ảnh có điểm), AUROC PA3, AUROC nhãn nhị phân Qwen trên **cùng eligible IDs**, Delta, confusion 4 mức,
phân bố dự đoán (Level03/Level04), coverage Normal/Anomaly, theo miền, Metallurgy riêng, bảng từng ảnh
(CSV: ID, miền, GT, dự đoán, z1..z4, S, status), baseline lớp cố định (ties 0.5), leave-one-component-out.
Không tối ưu threshold, không đảo chiều điểm, không học tham số, không đổi prompt, **không CI**.

| Tiêu chí | Ngưỡng (so sánh phân số chính xác) |
|---|---|
| C1 | Nhóm chính: ≥95% Normal và ≥95% Anomaly có PA3 hợp lệ (≥38/40 mỗi lớp) |
| C2 | Macro-domain AUROC PA3 trên 4 miền chính ≥ 0.75; miền nào không xác định → FAIL |
| C3 | Macro PA3 − macro nhãn nhị phân Qwen ≥ 0.15 |
| C4 | PA3 > nhãn nhị phân (nghiêm ngặt) ở ≥ 3/4 miền chính |
| C5 | Run hoàn tất, niêm phong; CPU audit/recompute PASS; checksum 90/90; exposure niêm phong; 0 TECHNICAL_ERROR/INTERRUPTED/UNPROCESSED/NOT_ATTEMPTED |

Tất cả đạt → `GO_PA3`; ngược lại `KEEP_CURRENT_DIRECTION` với một lý do tách bạch:
`NOT_EXECUTED`, `INCOMPLETE`, `TECHNICAL_FAIL`, `INSUFFICIENT_VALID_DATA`, `PERFORMANCE_NOT_CONVINCING`.
Metallurgy và độ nhạy chỉ mô tả, không cứu/đảo quyết định. Không mở thêm lượt GPU để đạt GO.

## 6. Kiểm tra lại trên CPU sau khi tải artifact

Tại checkout M, với tokenizer snapshot pinned (không cần weights/GPU):

```text
python -m safeshift.pa3.native.native_audit --run RUN_DIR --snapshot TOKENIZER_DIR --report RUN_DIR-report
python -m safeshift.pa3.native.seminar_verdict --run RUN_DIR --snapshot TOKENIZER_DIR --output data/processed/pa3_seminar_recheck
```

Lệnh thứ hai CPU-audit lại raw, tính lại toàn bộ chỉ số/quyết định, so byte với `RUN-report/diagnostic`
và với `PA3_SEMINAR_DIRECTION_VERDICT.md`, CSV, metrics JSON trong `RUN-verdict`. Chỉ sau đó Lead mới thay
verdict NOT_EXECUTED ở repo bằng verdict thật (PR riêng) và ghi `EXPERIMENTS.md`.

## 7. Giới hạn và blocker đã biết

- Toàn bộ 90 ảnh đã qua Qwen2.5 P2 toàn pool; thiết kế được thúc đẩy sau khi thấy P2 (kể cả TEST). Ledger exposure không đầy đủ.
- Quan hệ near-duplicate/source-family chưa phân xử (42/45 Anomaly trong một thành phần bảo thủ); không tuyên bố độc lập hay khái quát hóa; không CI.
- 10+10 ảnh mỗi miền: AUROC từng miền thô (bước 0.005), dao động lớn.
- Bố cục thư mục của Dataset `InspecSafe-V1-Kaggle` chưa được kiểm chứng từ phiên này (mục 4.5).
- Dataset Kaggle gắn kèm có cả TEST; code chỉ mở 90 locator `DATA_PATH/train/...` trong manifest.
- Hash journal là integrity, không phải authenticity; ledger ngoài của Lead mới chặn được replay ở phiên mới.
