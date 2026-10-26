# Lộ trình từ Foundation V1

Lộ trình này theo dõi nền tảng và điều kiện phát triển, không phê duyệt thí nghiệm.
Task Foundation V1 lấy base `1ad17459a3db07ab84a780723317f6681b979770` sau clean
reset; yêu cầu hiện tại kết thúc ở Draft PR, chờ ChatGPT kiểm tra GitHub trực tiếp.
Không merge hoặc gọi Antigravity để chuyển sang kiểm toán độc lập trong task này.

## Cập nhật M1/M2 — 26/10/2026

- [PR #134](https://github.com/tantdna2/SafeShift/pull/134) đã **MERGED**, commit
  `a425ab04695319a42bfdd2f89192717dddbb891b`; không còn Draft.
- [Chỉ thị Owner](https://github.com/tantdna2/SafeShift/pull/134#issuecomment-6406751802)
  cho ghi M1 và soạn M2 trong một Draft PR. [Quyết định append-only](research/DECISIONS.md)
  ghi A1–A8 trong quyền SafeShift Owner/Research Lead; successor chỉ có hiệu lực
  sau kiểm chứng/merge, trước đó D9R22 còn hiệu lực. Không sửa lịch sử.
- [Protocol M2](research/SEMINAR_PROTOCOL.md)/[config v1](research/seminar_analysis_config.v1.json)
  **DONE tài liệu / PENDING khoa học**, cần review độc lập, Owner duyệt version
  và N/A/claim B01–B05; không tự freeze từ quyết định M1.
- Moondream2 N/A đã được Owner chấp nhận cho định lượng Seminar **cấp dự án**,
  đủ roster bốn model. Chưa xác minh ngoại lệ/chuẩn học vụ của giảng viên.
- NEXT TASK sau M1/M2 PASS: **M3-01 triển khai trọn hệ thống phân tích CPU**,
  reader/metrics/CLI/tests/config/docs; chưa triển khai M3 trong task này.
  M4 vẫn cần grant artifact riêng. Không mở task khảo sát/kế hoạch phụ.

Phần Foundation và gói #131 dưới đây là snapshot bằng chứng đã hoàn thành;
các lời chờ quyết định trước 26/10 được cập nhật bằng mục này và PROJECT_STATE.

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
- [x] **25/10:** ZIP S2 gốc CRC/hash/sidecars PASS; đủ bốn V4 shard, planned
  3.763 và 3.539 SUCCESS/1 lỗi/223 chưa chạy; saved AUROC khớp lịch sử.
- [x] Thêm cohort ba model/3.539 SUCCESS gốc và 10 biến thể; giữ 30 cũ,
  Recovery224 riêng. 51 tests tổng hợp và 110 AUROC gộp qua oracle độc lập PASS.
- [x] Code CPU, tests tổng hợp, oracle số bằng cặp/BFS; so C với D9R22,
  đánh giá A, brief giảng viên và blockers cụ thể.
- [x] PR #131 đã merge; [bằng chứng hậu merge](https://github.com/tantdna2/SafeShift/pull/131#issuecomment-6394591862).
  Hướng/estimand do Owner quyết định tại M1; metric/grouping v1 còn review M2.

[Hồ sơ](SOURCE_FEASIBILITY_GATE_20261024.md) và
[receipt](SOURCE_FEASIBILITY_RECEIPT_20261024.json) ghi bằng chứng mới/giới hạn.
Các ô trên không phải hoàn tất RQ/protocol, source verification, raw audit
hoặc thí nghiệm bốn model. Thay đổi phạm vi M1 và điều kiện hiệu lực ở mục cập
nhật trên; không nâng evidence của #131 hay duyệt toàn bộ hướng A/C.

### Phần nghiên cứu và thẩm quyền vẫn còn thiếu

1. **Khép phần raw/receipt còn thiếu:** Qwen3 S2 gốc và full V4 saved-score đã
   khép 25/10, giữ rerun/recovery riêng. Còn raw replay theo hợp đồng model và
   quyền cụ thể, giới hạn outer receipt Qwen2.5. Không sửa lịch sử hoặc gọi
   archive/saved-score verification là raw PASS.
2. **Hiệu lực M1:** quyết định Owner đã được ghi append-only, chờ kiểm chứng/
   merge successor. Phạm vi HNLO tích hợp được chọn; chuẩn học vụ chưa xác minh.
3. **Review hợp đồng M2:** protocol/config đã có công thức/eligibility/denominator,
   model/run/cohort và C01–C10; cần review độc lập và quyết định đúng version.
   Hazard map/control/mismatch/provenance thiếu được chặn riêng, N/A/claim chưa
   tự approved. Không mặc định token mapping Qwen áp cho model khác.
4. **Bổ sung code có nhiệm vụ cụ thể:** dataset adapter được phép, artifact
   writer/raw-before-parse, provenance/checksum, parser và evaluation đã duyệt;
   mỗi phần có test synthetic và review. Không phục hồi toàn pipeline cũ.
5. **Giữ đủ bốn mô hình:** Moondream2 còn thiếu raw-logit validation/endpoint
   tương đương và TRAIN audit; ngoại lệ N/A cấp dự án đã được Owner chấp nhận
   cho Seminar. Không bỏ/thay model, bịa score hoặc suy ngoại lệ sang Khóa luận.

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

Owner đã chọn nghiên cứu thực nghiệm logistic HNLO+bất đồng xếp ưu tiên kiểm
tra với Q3 cố định, baseline/ablation công bằng và toàn bộ chi phí VLM phụ.
Xác nhận cần nguồn độc lập, nhãn chuyên gia mù VLM, target kín, đủ nguồn/sự kiện
theo precision plan khóa trước target. Chưa có quyền/nguồn/tài nguyên hay chuẩn
học vụ được xác minh. NO-GO dữ liệu chặn xác nhận; không dùng TRAIN chia lại
hoặc TEST thay thế. Không tạo training/GPU/triage pipeline trong task M1/M2.

Nguồn thẩm quyền: [D9R22](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/configs/pre_freeze/d9r22_seminar_scope.v1.json),
[DECISIONS lịch sử](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/DECISIONS.md),
[yêu cầu bốn mô hình](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_four_model_seminar_scope.md).
Xem [HISTORY](HISTORY.md) trước khi tra code/runbook cũ; các ref bảo toàn và sáu
Draft PR cũ giữ nguyên, không merge chúng để đưa code lịch sử trở lại main.
