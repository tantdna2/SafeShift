# SafeShift roadmap

**Đề tài đề xuất:** SafeShift: Evaluating the Validity and Cross-Domain Reliability of Internal Hazard Scores in Vision-Language Models

**Dataset:** InspecSafe-V1.

Đây là kế hoạch cho [DEC-PA3-011 PROPOSED](DECISIONS.md#dec-pa3-011--proposed-seminar-internal-hazard-score-direction-2026-10-16),
không phải quyết định đã duyệt hoặc báo cáo kết quả bốn mô hình. RQ1 kiểm tra giá
trị phân biệt của điểm nội tại so với đầu ra sinh ra trên cùng ID; RQ2 kiểm tra
human-presence/domain/provenance confounding; RQ3 mô tả FNR/FPR và giới hạn chuyển
miền sau một quy tắc ngưỡng được phê duyệt trước. RQ3 không đưa ra bảo đảm an toàn.

Qwen2.5 là baseline đã kiểm toán trên TRAIN đã phơi nhiễm. Qwen3, InternVL3 và
Moondream2 vẫn bắt buộc nhưng khả năng cung cấp raw logits hoặc đại lượng tương
đương cho điểm nội tại chưa được xác minh. PA3 không được coi là thuật toán mới,
không được áp dụng ngầm cho mô hình khác. D9R22 và mọi kết quả lịch sử được giữ nguyên.

| Tuần | Giai đoạn | Công việc và đầu ra dự kiến |
| --- | --- | --- |
| Hoàn tất | Dataset/code provenance và Qwen baseline | Giữ nguyên audit W1 và lịch sử; CPU Linux tính lại 3.763/3.763 Qwen TRAIN raw outputs, ghi hạn chế exposure và thiếu receipt Shard 1. |
| Gate A | Phê duyệt hướng và protocol | Review DEC-PA3-011, định nghĩa common cohort/coverage/mẫu số, baseline sinh ra, covariates, dependence groups, threshold rule và điều kiện N/A. Không cấp authority bằng tài liệu. |
| Gate B | Qualification đủ bốn mô hình | Với từng mô hình, khóa revision/interface/preprocessing/precision; xác minh raw logits hoặc chứng minh đại lượng tương đương. Nếu không hỗ trợ, ghi blocker và trình phương án dự phòng để Lead duyệt. |
| Gate C | Thực thi được ủy quyền | Chạy raw-before-parse trên cùng phạm vi được duyệt; lưu run ID/config/version. GPU, labels/annotations, threshold fitting và TEST có authority riêng. |
| Phân tích | RQ1–RQ3 | RQ1 so sánh PA3/internal score với generated-label baselines trên cùng valid IDs; RQ2 phân tầng/điều chỉnh confounders đã duyệt; RQ3 báo FNR/FPR theo miền, coverage và giới hạn chuyển giao. |
| Handoff | Seminar và form giảng viên | Điền form từ số liệu đã audit; dùng N/A cho Paper/Official hoặc mô hình chưa có bằng chứng tương thích; không đặt target hiệu năng hậu nghiệm. |

## Điều kiện chuyển giai đoạn

- Gate A → B: DEC-PA3-011 và protocol so sánh được Lead phê duyệt; không thay dataset/split/label/PA3 formula ngầm.
- Gate B → C: đủ hồ sơ bốn mô hình, kể cả blocker/N/A; authority binds exact model, revision, cohort, artifacts và số lần chạy.
- Gate C → phân tích: raw output và coverage/status được kiểm toán; mọi GT join xảy ra theo scope đã duyệt.
- Phân tích → handoff: báo đủ mẫu số, valid-ID intersection, dependence/confounding và domain limitations; không suy TRAIN thành generalization.

Trước khi DEC-PA3-011 được phê duyệt, [D9R22 JSON](configs/pre_freeze/d9r22_seminar_scope.v1.json)
vẫn là scope hiệu lực; roadmap này không sửa config đó. Bốn mô hình bắt buộc giữ
nguyên. Protocol freeze=PENDING; tài liệu/PR/merge không tự cấp quyền inference.
