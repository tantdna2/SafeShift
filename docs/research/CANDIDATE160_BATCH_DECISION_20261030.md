# DEC-20261030-CANDIDATE160-BATCH — PROPOSED / UNAPPROVED

Owner giao hoàn thiện phần mềm sau [PR #152 MERGED](https://github.com/tantdna2/SafeShift/pull/152),
merge `f79f7bddeac62e8fb8378d6798c25387f45f0f37`. Cho phép triển khai và kiểm thử
nhánh batch có điều kiện; **không phải phê duyệt thay thẩm quyền review nghiên cứu**.

Đề xuất: Research Lead có thể phê duyệt trước đúng execution binding/policy hash,
mốc first-image/early/later, numerical stop/resource/support limits và sáu điều
kiện trong `train_contract.BATCH_CONDITIONS`. Chỉ sau bản phê duyệt thật gắn
model/source/runtime/run/attempt/manifest/config, máy được ghi AUTO_CONTINUE khi
tất cả kiểm tra đạt. AUTO_CONTINUE là quyết định máy theo ủy quyền trước, không
là review CONTINUE do Lead thực hiện sau quan sát. Mọi lỗi, thiếu support hoặc
ngưỡng vi phạm → STOP, ghi evidence và NOT_ATTEMPTED; không retry/resume.

Trạng thái hiện tại: **PENDING Research Lead approval**, thresholds/mốc/driver/
resource limits và batch authorization đều chưa duyệt. External-review mode vẫn
giữ được; saved batch yêu cầu file review ngoài chưa thể tuyên bố chạy đủ160.
Mã và tests SYNTHETIC không cấp approval, G0/T0/O3, dữ liệu/GT/checkpoint/GPU/raw
export hoặc quyền tiêu attempt. Không đổi C1/parser/HNLO, cohort/order, roster,
protocol M2 hay quyết định lịch sử. Checklist phê duyệt duy nhất tại
[runbook](../CANDIDATE160_KAGGLE.md#checklist-bàn-giao-duy-nhất).
