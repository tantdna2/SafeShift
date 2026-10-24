# Tìm cấu hình, manifest và source lock

BASE `cf6d4d633fd8bf5179672733211061686c7af6e9` có **102 JSON trong configs/**.
Đây là mục lục; mọi JSON và đường dẫn thực nghiệm được giữ nguyên.
Không suy tên `frozen`, main hoặc grant lịch sử thành quyền chạy lại ở HEAD mới.

## Tìm theo việc cần làm

| Việc cần tra cứu | Cấu hình / tài liệu |
| --- | --- |
| Phạm vi Seminar đang có hiệu lực | [D9R22 scope](pre_freeze/d9r22_seminar_scope.v1.json); [DEC-PA3-011](../DECISIONS.md#dec-pa3-011--proposed-seminar-internal-hazard-score-direction-2026-10-16) vẫn PROPOSED. |
| Qwen2.5 PA3-R2 | [r2_authority.v1.json](pa3/r2_authority.v1.json), [manifest R2](../data/manifests/pa3_r2_full_train.v1.json), [runbook](../notes/pa3_r2_runbook.md). |
| TRAIN V4 Qwen3/InternVL3 | [authority V4](diagnostics/hnlo_train_authority.v4.json), [source V4](diagnostics/hnlo_train_source.v4.json), [provenance V4](diagnostics/hnlo_train_provenance.v4.json), [runbook](../notes/hnlo_train_v4_20261019.md). |
| Qwen3 Recovery224 | [authority](diagnostics/qwen3_s2_recovery_authority.v1.json), [source lock](diagnostics/qwen3_s2_recovery_source.v1.json), [runbook](../notes/qwen3_s2_recovery224_20261022.md). Giữ riêng cohort và attempt. |
| One-click và InternVL3 kỹ thuật | Các cặp `hnlo_one_click_*`, `internvl3_{cuda,recovery,driver,hnlo}_*` trong [diagnostics](diagnostics/); [notebook index](../notebooks/README.md). |
| Resource pilot V1–V3 | `resource_pilot_authority.v*.json`, `resource_pilot_source.v*.json`, `resource_pilot_provenance.v1.json`; [runbook V3](../notes/resource_pilot8_dataset_path_v3_20261019.md). |
| P2/P2.1 và qualification W2 | [frozen](frozen/), [pre_freeze](pre_freeze/), [D9R27](../notes/w2_d9r27_final_freeze_authority.md), [P2.1 amendment](../notes/w2_p21_protocol_amendment.md). `pre_freeze` vẫn chứa cấu hình được tham chiếu; chưa đổi tên thư mục. |
| LS1 lịch sử | [ls1.v1.json](experiments/ls1.v1.json), [LS1 runbook](../notes/ls1_runbook.md). |

## Manifest, prompt và môi trường ở đâu

- [data/manifests](../data/manifests/): 10 JSON được theo dõi, gồm full TRAIN, bốn shard, receipt, R2 và seminar cohort/inference. Không phải dữ liệu gốc; giữ ID/order/hash/split theo hợp đồng.
- [prompts](../prompts/), [schemas](../schemas/): prompt và schema được tham chiếu bởi code/hợp đồng. Không sửa trong task điều hướng.
- Các file `requirements-*.txt` ở repository root: pin môi trường theo mô hình/tuyến kiểm tra; xem runbook tương ứng trước khi cài. Không có một file chung thay thế mọi môi trường.
- [data/README.md](../data/README.md): quy ước lưu dữ liệu local từ giai đoạn khởi tạo. Nội dung “chưa có parser” phản ánh thời điểm đó; code audit hiện có ở [safeshift/data](../safeshift/data/).

## Cách đọc ràng buộc hash

Một source lock giữ danh sách `path` và `sha256` của source thực thi; authority
gắn với source/release/run cụ thể. Bootstrap kiểm tra cả inventory, topology Git
và bytes. Thêm tài liệu ở HEAD cũng có thể làm HEAD khác inventory release.
Tái lập phải checkout đúng commit đã được duyệt, không cập nhật lock để khớp
một branch dọn tài liệu.

Ví dụ [source lock Recovery224](diagnostics/qwen3_s2_recovery_source.v1.json)
liệt kê **673 đường dẫn**; [bootstrap](../safeshift/diagnostics/qwen3_recovery/bootstrap.py)
yêu cầu đúng checkout release. README hiện khớp hash `74faf686…` trong 10 source
lock diagnostics và được giữ nguyên theo yêu cầu người dùng. Không tái sinh lock,
notebook hoặc grant trong giai đoạn 1.

Kết quả tổng hợp nhỏ nằm ở [notes/evidence](../notes/evidence/); raw outputs,
checkpoints và dataset không được thêm vào Git. Thay đổi tổ chức về sau phải qua
[bảng phụ thuộc giai đoạn 2](../notes/repository_organization_phase1_20261024.md).
