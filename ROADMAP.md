# SafeShift roadmap — PA3 CURRENT

**Đề tài:** SafeShift: Raw-Logit Analysis of Decision Collapse in Vision-Language Models for Multi-Domain Industrial Safety

Hướng theo [DEC-PA3-006](DECISIONS.md#dec-pa3-006--seminar-pa3-direction-and-baseline-priority-2026-10-13).
Đây là kế hoạch, không phải kết quả. Dataset vẫn là InspecSafe-V1;
giữ split/nhãn, công thức PA3, C1 và contract đã đóng băng.
[README](README.md) là điểm bắt đầu; [TASKS](TASKS.md) ghi việc đã làm/còn thiếu.

| Hạn / giai đoạn | Ưu tiên | Điều kiện / đầu ra |
| --- | --- | --- |
| 13–14/10/2026 | Thu hồi bằng chứng Qwen2.5 | Tìm archive/raw journal 90 TRAIN, source/runtime/model inventories, seals, hashes, telemetry và ledger đã lưu; CPU audit/recompute tại source đã duyệt. Không chạy lại GPU. |
| **15/10/2026** | **Form Review Baseline Qwen2.5-VL-3B-Instruct** | Điền [form guide](notes/pa3_baseline_review_2026-10-15.md), số liệu kiểm toán hoặc N/A kèm blocker. GO_PA3 chưa đủ bằng chứng; 90 TRAIN không phải baseline confirmatory. |
| Sau baseline | Xác minh InternVL3-2B | Review raw extraction, token alignment/T1, journal, CPU recomputation tương đương; chỉ lên kế hoạch chạy khi đủ điều kiện và có quyền riêng. |
| Sau qualification | So miền và mô hình | Giữ Qwen3-VL-8B với rào cản tài nguyên; Moondream2 có điều kiện, đề xuất thay thế riêng nếu không tương đương. Không mặc định cả bốn chạy được. |
| Phân tích / viết | RQ1 nhãn; RQ2 raw vs generated; RQ3 miền/mô hình | AUROC PA3/nhãn sinh, ΔAUROC, coverage, AUROC miền là chính; nguyên nhân còn là giả thuyết nếu thiếu bằng chứng. |

Điều kiện công bố baseline số: raw-before-parse, source/revision/config và checksum,
audit/recompute, cohort/GT join và mẫu số; nêu exposure/phụ thuộc. Nếu thiếu archive
trước hạn, nộp N/A và blocker, không suy số liệu từ verdict người dùng báo cáo.

90 ảnh là exploratory TRAIN đã có exposure P2, near/source-family chưa phân xử
và phụ thuộc lớn; không holdout độc lập, không CI/p-value, không suy TEST.
Macro chẩn đoán giữ bốn miền chính; metallurgy mô tả phụ. Ngưỡng phân loại PA3,
cohort đánh giá chính thức và protocol đa mô hình cần quyết định riêng trước
áp dụng; deadline không tạo quyền chạy hoặc quyền mở TEST.

Kế hoạch W1–W8/D9R22 trước đây là HISTORICAL; audit W1 vẫn là nguồn nền.
Grounding/disagreement không còn mục tiêu chính của Seminar PA3. Lịch sử,
frozen config và quyền được giữ; xem [phân loại tài liệu](notes/documentation_index.md).
