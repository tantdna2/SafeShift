# PA3: yêu cầu Seminar đủ bốn mô hình

Ngày ghi nhận: 2026-10-15. Nguồn: yêu cầu trực tiếp của Research Lead trong
phiên làm việc chuẩn bị kiểm toán CPU PA3-R2; đây là yêu cầu nghiên cứu lâu dài.

## Phạm vi bắt buộc

Kết quả Seminar cuối cùng phải đánh giá **đủ cả bốn mô hình**:

| Mô hình | Vai trò / việc cần chứng minh cho PA3 |
| --- | --- |
| Qwen2.5-VL-3B-Instruct | Baseline; PA3-R2 TRAIN cần kiểm toán độc lập đầy đủ. |
| Qwen3-VL-8B-Instruct | Thành phần bắt buộc; kiểm tra khả năng lấy raw logits và ánh xạ token. |
| InternVL3-2B-hf | Thành phần bắt buộc; kiểm tra khả năng lấy raw logits và ánh xạ token. |
| Moondream2 | Thành phần bắt buộc; kiểm tra giao diện điểm số có thể truy vết. |

Qwen2.5 chỉ là mốc so sánh ban đầu, không đại diện cho toàn bộ nghiên cứu và
không đủ để hoàn tất Seminar. Lead báo cáo 3.763/3.763 ảnh TRAIN thành công,
AUROC PA3 sơ bộ 0.8267. Đây là số liệu được cung cấp ở thời điểm ghi nhận yêu cầu.
Kiểm toán tiếp theo đã [PASS trên CPU Linux](pa3_r2_cpu_completion_20261015.md):
3.763/3.763 SUCCESS được tính lại từ raw output, AUROC gộp độc lập
**0.8266558463706973**. AUROC nhãn Qwen nhị phân là **0.5**; không đồng nhất
khả năng xếp hạng điểm PA3 với chất lượng nhãn sinh ra. Handoff
[BLOCKED trước đó](pa3_r2_cpu_audit_20261015.md) được giữ làm lịch sử.
Kết quả TRAIN đã phơi nhiễm không chứng minh khả năng khái quát hóa.

## Điều kiện so sánh cần được xem xét và phê duyệt

- [ ] Với **từng** mô hình, ghi model/revision, giao diện native, tokenizer,
  bước quyết định, thứ tự nhãn và khả năng lưu raw logits trước chuẩn hóa,
  trước các logits processor. Lưu raw output cùng sample ID, prompt, cấu hình
  và run ID trước parse/tổng hợp; không mặc định API hay tokenizer tương thích Qwen.
- [ ] Nếu dùng thông tin tương đương, chứng minh quan hệ toán học với điểm số
  và khả năng tính lại. Xác suất nhãn sinh ra, điểm đã qua processor hoặc chuỗi
  trả lời đơn thuần không tự động được xem là tương đương raw logits của PA3.
- [ ] Thiết kế so sánh công bằng trên cùng phạm vi dữ liệu/ID, split và nhãn đã
  được duyệt; cùng tiêu chí đánh giá, chiều điểm, quy tắc INVALID/coverage và
  mẫu số. Báo cáo cả giao các ID hợp lệ khi so sánh cặp và coverage trên toàn
  bộ tập dự kiến; không âm thầm loại các mẫu lỗi để cải thiện kết quả.
- [ ] Ghi khác biệt prompt/interface, preprocessing, precision, ngân sách sinh,
  clamp và runtime của mỗi mô hình; xác định trước control và giới hạn so sánh.
  Không tự áp dụng clamp Qwen hoặc công thức token của Qwen cho mô hình khác.
- [ ] Nếu một mô hình không hỗ trợ PA3, báo cáo trở ngại và bằng chứng, rồi đề
  xuất cách đánh giá hợp lệ (ví dụ các metric nhãn sinh ra đã được duyệt trên
  cùng cohort, hoặc endpoint tương đương được chứng minh). Research Lead phải
  duyệt thay đổi trước khi áp dụng; không âm thầm bỏ hay thay mô hình, không
  gắn nhãn “PA3” cho điểm chưa chứng minh tương đương.
- [ ] Thiết kế đánh giá khả năng khái quát hóa với provenance/exposure, phụ thuộc
  mẫu và domain/platform confounding được xử lý minh bạch; việc dùng holdout
  hoặc TEST cần quyết định và quyền thực thi riêng. Không tự chia lại dữ liệu.

## Ranh giới quyết định

Research Lead đã chọn hướng internal hazard score để **chuẩn bị chốt**; hướng này
được ghi tại `DEC-PA3-011` với trạng thái **PROPOSED**. Nó chưa thay thế phạm vi
D9R22 cho đến khi hoàn tất review/approval của PR. Phê duyệt cuối phải được ghi
append-only; mọi thay đổi protocol/metric/split và authority thực thi vẫn tách riêng.

Ghi chú này không cấp quyền GPU, gọi mô hình, inference mới, mở TEST hoặc thay
đổi công thức PA3, dữ liệu, nhãn hay kết quả lịch sử. README/RQ được cập nhật như
nội dung **đề xuất**, không phải protocol đã freeze. Bàn giao qua Draft PR để
ChatGPT kiểm tra trực tiếp trên GitHub; không merge hoặc tự chuyển sang Antigravity.

Đối chiếu: [runbook PA3-R2](pa3_r2_runbook.md),
[quyết định lịch sử](../DECISIONS.md), [công việc đang hoạt động](../TASKS.md).
