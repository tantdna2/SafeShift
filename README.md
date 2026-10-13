# SafeShift

**SafeShift: Raw-Logit Analysis of Decision Collapse in Vision-Language Models for Multi-Domain Industrial Safety**

Điểm bắt đầu cho Seminar PA3, theo [DEC-PA3-006](DECISIONS.md#dec-pa3-006--seminar-pa3-direction-and-baseline-priority-2026-10-13).
Mục tiêu là nghiên cứu vì sao nhãn sinh của VLM phân loại mức an toàn kém,
trong khi điểm thô có thể vẫn phân biệt ảnh Normal và Anomaly. Đây là câu hỏi
nghiên cứu; chưa có kết quả PA3 chính thức được kiểm toán trong repo.

Ưu tiên **baseline Qwen2.5 và Form Review Baseline ngày 15/10/2026**.
Người dùng báo cáo `GO_PA3` cho chẩn đoán 90 TRAIN, nhưng chưa có archive bằng
chứng được kiểm toán độc lập và phiên Kaggle đã restart. Verdict commit
[KEEP_CURRENT_DIRECTION / NOT_EXECUTED](PA3_SEMINAR_DIRECTION_VERDICT.md) là
placeholder từ PREP, không xác nhận hoặc bác bỏ báo cáo đó. Quyết định chuyển
hướng của người dùng không đồng nghĩa xác minh kết quả chẩn đoán.

## Bắt đầu

1. Đọc [AGENTS.md](AGENTS.md), [ROADMAP.md](ROADMAP.md) và phần PA3 CURRENT ở đầu [TASKS.md](TASKS.md).
2. Điền [hướng dẫn Form Review Baseline 15/10](notes/pa3_baseline_review_2026-10-15.md), chỉ dùng số liệu có bằng chứng.
3. Tra [CURRENT / HISTORICAL / DEPRECATED](notes/documentation_index.md); dữ liệu local theo [data/README.md](data/README.md).
4. Ghi quyết định vào [DECISIONS.md](DECISIONS.md), bằng chứng thực nghiệm vào [EXPERIMENTS.md](EXPERIMENTS.md).

## Câu hỏi nghiên cứu đề xuất

- **RQ1 — Sụp đổ nhãn:** nhãn Level01–Level04 tập trung vào một/vài mức như thế nào,
  và lỗi tập trung ở đâu? Dùng phân bố nhãn, confusion matrix và chỉ số phụ;
  nguyên nhân là giả thuyết cần kiểm tra, không suy ra từ accuracy thấp.
- **RQ2 — Điểm thô so với nhãn sinh:** PA3 còn khả năng phân biệt Normal/Anomaly
  khi nhãn sinh kém không? So AUROC và chênh lệch trên cùng ID có điểm hợp lệ.
- **RQ3 — Miền và mô hình:** sụp đổ nhãn, AUROC và coverage khác nhau ra sao
  giữa miền và mô hình đủ điều kiện? Protocol so liên mô hình còn chờ qualification.

Hướng này thay thế nội dung Seminar D9R22 trong tài liệu hiện hành.
Protocol/config đã đóng băng và định nghĩa dataset, split, nhãn giữ nguyên.

## Kế hoạch bốn mô hình

| Mô hình | Vai trò dự kiến và điều kiện |
| --- | --- |
| Qwen2.5-VL-3B-Instruct | Baseline ưu tiên trước 15/10. Có scorer native và CPU audit; số liệu thật cần archive/audit. Revision `66285546d2b821cf421d4f5eb2576359d3770cd3`. |
| InternVL3-2B | Ứng viên tiếp theo; đích repo là `OpenGVLab/InternVL3-2B-hf`. Phải xác minh raw logits trước xử lý, vị trí/token quyết định, T1, raw capture và CPU recomputation tương đương. Qualification classification/LS1 không đủ. |
| Qwen3-VL-8B | Giữ ứng viên (`Qwen/Qwen3-VL-8B-Instruct`). Rào cản bộ nhớ: P2 T4 x2 từng OOM theo báo cáo Owner; xem [bằng chứng và giới hạn](notes/w2_d9r26_qwen3_p2_runbook.md#superseding-authority-evidence-and-validation). Chưa qualification PA3 tương đương. |
| Moondream2 | Ứng viên có điều kiện; chưa xác minh giao thức raw-logit PA3 tương đương. Nếu không đáp ứng, lập đề xuất thay thế riêng và ghi quyết định trước khi đổi roster. |

Đây là kế hoạch, không phải tuyên bố bốn mô hình đã tham gia PA3. Mỗi ứng viên
cần bằng chứng kỹ thuật, protocol tương đương và quyền chạy riêng trước khi tham gia.

## Chỉ số và cách đọc

PA3 giữ `S = logsumexp(z_Level01, z_Level02, z_Level03) - z_Level04`
tại nhánh token quyết định đã xác minh; điểm cao hơn hướng Anomaly.
Normal = Level04, Anomaly = Level01–Level03 theo giao thức chẩn đoán hiện có.
Nguồn: [native_score.py](safeshift/pa3/native/native_score.py),
[analysis.py](safeshift/pa3/native/analysis.py), [seminar_verdict.py](safeshift/pa3/native/seminar_verdict.py).

| Ưu tiên | Chỉ số |
| --- | --- |
| Chính | AUROC PA3; AUROC nhãn sinh nhị phân (Anomaly=1, Normal=0); ΔAUROC = PA3 − nhãn sinh trên cùng eligible IDs; tỷ lệ điểm hợp lệ tổng/theo lớp/theo miền; AUROC theo miền. |
| Phụ, từ nhãn sinh | Accuracy 4 mức, balanced accuracy, recall Level01, tỷ lệ báo động giả trên Normal, ma trận nhầm lẫn; ghi mẫu số và trạng thái INVALID/lỗi/ảnh chưa xử lý. |

AUROC hiện tại là score-conditional trên `SUCCESS`, ties có credit 0.5; thiếu
một lớp thì không xác định. Chẩn đoán 90 ảnh giữ macro bốn miền chính
(coal_conveyor, oil_chemical, power, tunnel); metallurgy chỉ mô tả phụ.
Coverage phải đi cùng AUROC để không che mất mẫu không có điểm. Chỉ số phụ chưa
có export/định nghĩa được review ghi N/A. **Chỉ đo accuracy/recall/báo động giả
của PA3 sau khi ngưỡng được phê duyệt riêng.**

## Bằng chứng và quyền thực thi

[Runbook 90 ảnh](notes/pa3_seminar_direction_runbook.md) có đối chiếu main
`3a52b549d623bdb4b8b6753abe3adf116bbc6100`: grant chẩn đoán đã merge, giới hạn
một lượt, không retry. Quyền gắn với source/topology đã duyệt; nhánh tài liệu này
không phải source chạy mới. Grant không chứng minh đã chạy hay kết quả PASS.
Không khởi chạy lại GPU sau restart, không mở TEST; ưu tiên tìm artifact đã lưu.

Dữ liệu gốc, weights và raw outputs không đưa vào Git. Artifact dẫn xuất ở
`data/processed/`; giữ raw logits/token IDs/output, sample ID, prompt, model/revision,
runtime, config, run/source SHA và hashes để CPU audit tái lập. Lịch sử W1, LS1,
P2/P2.1, grounding và disagreement được bảo toàn qua trang điều hướng.
