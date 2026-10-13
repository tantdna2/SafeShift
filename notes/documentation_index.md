# Điều hướng tài liệu SafeShift

Đọc [README](../README.md) trước. Phân loại tại BASE
`3a52b549d623bdb4b8b6753abe3adf116bbc6100`, hướng PA3 ngày 13/10/2026.
Phân loại vai trò tài liệu không thay đổi authority hoặc xóa bằng chứng.

| Nhóm | Tài liệu / quy tắc bao phủ |
| --- | --- |
| **CURRENT** — hướng và việc đang làm | [README](../README.md), [ROADMAP](../ROADMAP.md), [AGENTS](../AGENTS.md), [Form Baseline 15/10](pa3_baseline_review_2026-10-15.md), trang này và [validation PR](pa3_seminar_redirect_validation.md). |
| **CURRENT** — log có lịch sử append-only | [TASKS](../TASKS.md), [DECISIONS](../DECISIONS.md), [EXPERIMENTS](../EXPERIMENTS.md): đọc overlay PA3/DEC-PA3-006 trước. Mục cũ ghi CURRENT/Draft/PENDING là snapshot theo ngày, không suy thành trạng thái hôm nay. |
| **CURRENT** — nguồn nền dữ liệu | [data/README](../data/README.md); note W1: `w1_dataset_audit`, `dataset_schema`, `dataset_validation`, `distribution_imbalance_audit`, `duplicate_leakage_audit`, `manifest_builder`, `research_feasibility_audit`, `source_license_audit`, `visual_provenance_review` (`notes/*.md`). Giữ nguồn/giới hạn của từng nhận định. |
| **CURRENT** — chẩn đoán và thu hồi bằng chứng | [runbook 90 TRAIN](pa3_seminar_direction_runbook.md) có overlay main; [placeholder verdict](../PA3_SEMINAR_DIRECTION_VERDICT.md) được bảo toàn, chưa là kết quả thật. Code `safeshift/pa3/native/`, notebook `notebooks/pa3_seminar_direction_kaggle.ipynb`: chỉ tra cứu/CPU audit trong task này. |
| **HISTORICAL** — PA3 preparation | Mọi `notes/pa3_*.md` còn lại: proposal, dossier, synthetic/native preparation, artifact guide, Task 5/6 runbook/validation. Truy vết kỹ thuật theo ngày/source, đối chiếu quyền hiện tại trước khi dùng trạng thái LOCKED/PENDING/PASS. |
| **HISTORICAL** — hướng cũ | Mọi `notes/w2_*.md`, `notes/ls1_*.md` còn lại: protocol briefs, qualification/runtime/grounding, D9R22 disagreement, P2/P2.1 và LS1. Không suy participation PA3 từ qualification cũ; code/config giữ để tái tạo và kiểm quyền. |
| **DEPRECATED** — điểm bắt đầu hiện hành | [pre_freeze_implementation.md](pre_freeze_implementation.md): hướng dẫn D8/pre-freeze được thay bằng README PA3. Giữ file làm lịch sử kỹ thuật và giữ liên kết cũ. |

Quy tắc bao phủ Markdown được track ở BASE và tài liệu mới của PR;
file untracked của người dùng không được phân loại hoặc đưa vào PR.
Không di chuyển hàng loạt. **File xóa: không có** — chưa chứng minh được file
vừa dư thừa, không tham chiếu/import/test, vừa không là bằng chứng nghiên cứu.
