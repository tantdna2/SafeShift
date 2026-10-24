# Lộ trình từ Foundation V1

Lộ trình này theo dõi nền tảng và điều kiện phát triển, không phê duyệt thí nghiệm.
Task Foundation V1 lấy base `1ad17459a3db07ab84a780723317f6681b979770` sau clean
reset; yêu cầu hiện tại kết thúc ở Draft PR, chờ ChatGPT kiểm tra GitHub trực tiếp.
Không merge hoặc gọi Antigravity để chuyển sang kiểm toán độc lập trong task này.

## Nền tảng đã hoạt động

- [x] Package Python cài/import được, không runtime dependencies.
- [x] Bốn nhãn canonical, record tối thiểu, strict validation và ID duy nhất.
- [x] Exact cohort join, ma trận 4×5, support và recall gồm INVALID; mẫu số 0
  trả `None` thay vì kết quả giả.
- [x] Model input/output transport và typing interface; không concrete backend.
- [x] Demo CPU xác định trên bản ghi tổng hợp, thông báo không phải kết quả nghiên cứu.
- [x] Giữ smoke tests; thêm kiểm thử record, lỗi/biên, metric và CLI demo.
- [x] Tài liệu phân biệt phạm vi được duyệt, đề xuất, bằng chứng và giới hạn;
  liên kết lịch sử bảo toàn tại commit cụ thể.

Các ô hoàn thành là khả năng phần mềm Foundation V1, không phải hoàn thành RQ,
protocol freeze hoặc raw audit mô hình. Chi tiết lệnh/kết quả kiểm tra ghi trong
Draft PR; [ARCHITECTURE](ARCHITECTURE.md) mô tả phạm vi API.

## Việc còn thiếu

### Gói quyết định Seminar đã hoàn thành trong PR #131 (24/10/2026)

- [x] Inventory/hash-verify metadata và saved reports được phép; đối soát
  visual catalog với pair table, không sửa lịch sử.
- [x] Q2.5/IVL3 trên 3.763 ID chung; Q3 S0/S1/S3 để so ba model trên 2.822 ID,
  Recovery224 riêng; 10 biến thể/cohort, **PROPOSED**.
- [x] Code CPU, tests tổng hợp, oracle số bằng cặp/BFS; so C với D9R22,
  đánh giá A, brief giảng viên và blockers cụ thể.
- [ ] ChatGPT kiểm tra toàn bộ Draft PR; giảng viên/Research Lead quyết định
  hướng, estimand/grouping và roster. Không merge trong task này.

[Hồ sơ](SOURCE_FEASIBILITY_GATE_20261024.md) và
[receipt](SOURCE_FEASIBILITY_RECEIPT_20261024.json) ghi bằng chứng mới/giới hạn.
Các ô trên không phải hoàn tất RQ/protocol, source verification, raw audit
hoặc thí nghiệm bốn model. D9R22/DEC-PA3-011/A/C giữ nguyên thẩm quyền.

### Phần nghiên cứu và thẩm quyền vẫn còn thiếu

1. **Khép bằng chứng cũ:** tìm đúng artifact Qwen3 S2 gốc/CSV đúng hash và giữ
   riêng rerun/recovery; xử lý giới hạn receipt Qwen2.5 và audit raw/score theo
   hợp đồng từng model. Không sửa số lịch sử hoặc tự gọi consistency là raw PASS.
2. **Chốt hướng khoa học:** D9R22 tiếp tục có hiệu lực, DEC-PA3-011/HNLO vẫn
   PROPOSED, hướng A/C chưa được phê duyệt. Research Lead quyết định hướng và
   ghi append-only; không sửa quyết định cũ để khớp code mới.
3. **Chốt hợp đồng:** production schema/parser, model revisions, prompt/native
   wrapper, preprocessing, precision, decoding, failure/INVALID và coverage;
   metric RQ1/RQ2/RQ3 chi tiết, controls và comparability. Không mặc định công
   thức/token mapping của Qwen áp dụng được cho model khác.
4. **Bổ sung code có nhiệm vụ cụ thể:** dataset adapter được phép, artifact
   writer/raw-before-parse, provenance/checksum, parser và evaluation đã duyệt;
   mỗi phần có test synthetic và review. Không phục hồi toàn pipeline cũ.
5. **Hoàn tất bằng chứng bốn mô hình:** Moondream2 còn raw-logit validation/
   endpoint tương đương và TRAIN audit cho hướng HNLO. Nếu cần N/A/fallback,
   trình duyệt riêng, không bỏ/thay mô hình hoặc bịa score.

Các mục trên là việc cần làm, chưa phải quyền thực hiện chúng trong task này.
Thứ tự chi tiết còn phụ thuộc quyết định hướng và nhiệm vụ tiếp theo được giao.

## Điều kiện trước thực nghiệm

Research Lead cần phê duyệt phạm vi/protocol, dữ liệu được phép truy cập,
model/revision/source/release/run/attempt, cấu hình và execution authority cụ thể.
Hoàn tất review, rehearsal phù hợp và freeze theo hướng được chọn trước benchmark.
Grant cũ không chuyển sang Foundation V1; tên model/interface không cấp quyền GPU.

Mọi thay đổi dataset/split/nhãn/metric phải có quyết định mới được duyệt trước
áp dụng. Giữ TEST và dữ liệu bị khóa đóng khi chưa có authority. Nếu nghiên cứu
threshold/holdout, chốt development/target, dependence/exposure controls và quy
tắc ngưỡng trước xem target; không tối ưu ngưỡng trên TRAIN đã quan sát hay TEST.
Phải lưu raw trước parse, cả lỗi/run dở, báo mẫu số và coverage trung thực.

## Mở rộng thành Khóa luận

Các hướng có thể trình duyệt: đánh giá độc lập theo nguồn/nhóm, kiểm soát proxy
người/thiết bị, uncertainty theo phụ thuộc nguồn, calibration/abstention theo
protocol và grounding với nhãn phù hợp. Đây là khả năng mở rộng kiến trúc, chưa
phê duyệt A/C, DEC-PA3-011, metric hoặc split mới. Không tạo sẵn training/GPU
pipeline khi chưa có nhiệm vụ.

Nguồn thẩm quyền: [D9R22](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/configs/pre_freeze/d9r22_seminar_scope.v1.json),
[DECISIONS lịch sử](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/DECISIONS.md),
[yêu cầu bốn mô hình](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_four_model_seminar_scope.md).
Xem [HISTORY](HISTORY.md) trước khi tra code/runbook cũ; các ref bảo toàn và sáu
Draft PR cũ giữ nguyên, không merge chúng để đưa code lịch sử trở lại main.
