# Hướng dẫn Form Review Baseline — 15/10/2026

Hướng dẫn nội dung; chưa có URL/schema Form chính thức trong task.
Đọc [README](../README.md); quyết định [DEC-PA3-006](../DECISIONS.md#dec-pa3-006--seminar-pa3-direction-and-baseline-priority-2026-10-13).

| Trường | Nội dung / bằng chứng |
| --- | --- |
| Đề tài / mục tiêu | SafeShift: Raw-Logit Analysis of Decision Collapse in Vision-Language Models for Multi-Domain Industrial Safety. So PA3 với nhãn sinh; phân tích sụp đổ nhãn và khác biệt miền. |
| Mô hình | `Qwen/Qwen2.5-VL-3B-Instruct`, revision `66285546d2b821cf421d4f5eb2576359d3770cd3`. Ba mô hình còn lại là ứng viên chưa qualification PA3 tương đương, không điền đã chạy. |
| Dataset | InspecSafe-V1; 90 TRAIN exploratory, 45 Normal/45 Anomaly theo manifest commit; không TEST/holdout. Ghi version/fingerprint/checksum từ receipt và archive, không suy từ tên dataset. |
| Setup đã khóa | C1, batch 1, T4, FP16, SDPA, greedy; không calibration/reference/threshold. Điền source SHA, bundle hash, runtime/dependency inventory, snapshot hashes, config/hardware từ archive thật, không dùng HEAD tài liệu thay source chạy. |
| Metric chính | AUROC PA3/nhãn sinh nhị phân, ΔAUROC cùng SUCCESS IDs; coverage tổng/lớp/miền; AUROC miền và macro bốn miền chính. Ghi valid counts, ties=0.5; N/A nếu thiếu lớp. |
| Metric phụ | Nhãn sinh: accuracy 4 mức, balanced accuracy, recall Level01, false-alarm rate trên Normal, confusion matrix. Ghi mẫu số/all-planned vs scored-only và lỗi. Chưa có export/định nghĩa được review: N/A. PA3 classification metrics: N/A đến khi ngưỡng được phê duyệt riêng. |
| Số liệu mô hình đã kiểm tra | **N/A — chưa có archive 90 ảnh được kiểm toán độc lập.** Không điền AUROC/accuracy/PASS từ trí nhớ hoặc GO_PA3. Sau CPU audit mới điền số kèm report/hash/source và mẫu số. |
| Trạng thái / blocker | Người dùng báo GO_PA3; Kaggle đã restart; archive chưa kiểm toán. Verdict repo KEEP_CURRENT_DIRECTION/NOT_EXECUTED là placeholder PREP. Thu hồi artifact đã lưu, không tự chạy lại GPU. |

Số liệu **đối chiếu được từ metadata commit**, không phải kết quả mô hình:
90 ID (45/45), Level01/02/03/04 = 25/16/4/45; bốn miền chính mỗi miền 10+10,
metallurgy 5+5 mô tả phụ. Nguồn: [cohort](../data/manifests/pa3_seminar_direction_cohort.v1.json),
[receipt](../data/manifests/pa3_seminar_direction_cohort_receipt.v1.json),
[inference](../data/manifests/pa3_seminar_direction_inference.v1.json).
Cohort SHA-256 `83959e27c04d1cf7f90fcbef501a87fdf970c32d542b61fbecb4b75f26b38da3`;
inference SHA-256 `d59af02b5fe53807ee60a373aef620fae75887bceb9aced6156a82d72461ebce`.
Metadata/hash không xác minh pixels/runtime hoặc hiệu năng.

Trước khi điền kết quả, thu hồi gói đầy đủ từ output/input đã lưu hoặc bản tải
xuống cũ; giữ ở `data/processed/`, ghi relative paths/hash trong [EXPERIMENTS](../EXPERIMENTS.md).
Cần raw journal/seal, token IDs/raw logits, source bundle/release, tokenizer/model
revision, runtime inventory, launch/preflight, exposure, telemetry, tickets,
report/verdict và attempt ledger. Hash authority là pin technical run trước đó,
không phải audit run 90 ảnh.

**CPU audit/recomputation** theo [runbook mục 6](pa3_seminar_direction_runbook.md#6-kiểm-tra-lại-trên-cpu-sau-khi-tải-artifact)
tại source đã duyệt khi có archive/tokenizer đúng revision; giữ report audit và
đối chiếu verdict từng byte. Task này thiếu đầu vào để audit thật.
Grant một lượt không được tái dùng sau restart.

Mẫu câu khi thiếu bằng chứng: “Baseline Qwen2.5 PA3 chờ kiểm toán archive.
GO_PA3 là báo cáo của người dùng trên 90 TRAIN, chưa có số liệu chính thức xác
minh. Không mở TEST, không chạy lại GPU; đang thu hồi raw artifacts để CPU recompute.”

Giới hạn: exposure P2; near/source-family chưa phân xử; một thành phần bảo thủ
chứa 48/90 ảnh gồm 42/45 Anomaly; xung đột miền metallurgy, Level03 hiếm.
Không CI/p-value, độc lập, cải thiện an toàn vận hành hoặc khái quát hóa TEST.
Nếu archive mất, nộp N/A và blocker trước hạn; đề xuất nghiên cứu/chạy mới xử lý
trong quyết định riêng.
