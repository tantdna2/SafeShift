# SafeShift — PROJECT STATE

Cập nhật: **26/10/2026 (Asia/Bangkok)**. Bản nhớ trạng thái, không phải quyền thực nghiệm.
Main đã đối chiếu GitHub: `a425ab04695319a42bfdd2f89192717dddbb891b`.
Khi mở chat mới phải kiểm GitHub lại; không coi snapshot này là live state.

## PROJECT IDENTITY

- **Đề tài:** SafeShift — Đánh giá và cải thiện độ tin cậy của quyết định nguy cơ an toàn công nghiệp bằng mô hình ngôn ngữ–thị giác.
- **Seminar:** hồi cứu nhãn sinh ra, HNLO, lỗi nguy hiểm và bất đồng trên TRAIN đã phơi nhiễm.
- **Khóa luận:** kiểm chứng logistic có regularization xếp ưu tiên ảnh cần người kiểm tra bằng HNLO+bất đồng, giữ Qwen3 predictor cố định theo protocol được duyệt.
- **HNLO:** đối tượng kiểm định Seminar, feature ứng viên Khóa luận; không xác suất nguy cơ đã hiệu chuẩn, lợi ích chưa được chứng minh.

## CURRENT STATUS

- **M1:** **APPROVED khoa học dự án** tại [DEC-20261026-M1](research/DECISIONS.md); hiệu lực repository chờ merge và ChatGPT xác minh hậu merge.
- **M2 v1:** **OWNER_APPROVED_FOR_PROJECT_SEMINAR**, đúng hai SHA-256 tại [DEC-20261026-M2](research/DECISIONS.md#dec-20261026-m2); review độc lập/ChatGPT đối chiếu PASS, Owner đã duyệt giới hạn. Khóa hiệu lực chờ PR #135 merge + ChatGPT xác minh hậu merge; chưa COMPLETE khi Draft.
- D9R22 còn hiệu lực khi PR này Draft; successor chỉ thay phần liệt kê sau merge. DEC-PA3-011 lịch sử giữ PROPOSED; hướng tích hợp HNLO được Owner chọn, không duyệt toàn bộ A/C độc lập.
- PR #133/#134 đã merge; merge tài liệu không tự freeze M2 hoặc cấp quyền thực nghiệm.
- Foundation V1 + công cụ saved-score CPU đã có; chưa có hệ thống Seminar R1–R5 hoàn chỉnh, backend VLM/raw writer/triage production.
- **M3 CHƯA TRIỂN KHAI**; phạm vi CPU + fixture SYNTHETIC chỉ có hiệu lực sau hậu merge được ChatGPT xác minh và ChatGPT chính thức giao task M3. M4/artifact thật và Khóa luận chưa cấp quyền.

## VERIFIED COMPLETED WORK

Chỉ ghi phần đã merge và có biên bản ChatGPT kiểm GitHub. Các test/replay được dẫn đúng người thực hiện; không nhận là đã tái chạy trong task này.

| Sản phẩm | PR / merge commit / bằng chứng hoàn tất |
| --- | --- |
| Foundation V1: records/validation, exact join, confusion/support/recall, transport interface, demo tổng hợp | [#130](https://github.com/tantdna2/SafeShift/pull/130), [`2810bee6f404a1c41cca4a2bbe45baf5ac48358a`](https://github.com/tantdna2/SafeShift/commit/2810bee6f404a1c41cca4a2bbe45baf5ac48358a); [ChatGPT hậu merge](https://github.com/tantdna2/SafeShift/pull/130#issuecomment-6380465749) |
| Source feasibility/sensitivity CPU và original V4 saved-score verification | [#131](https://github.com/tantdna2/SafeShift/pull/131), [`3bcd3535ea51e023de77417ed5f2077607d49c93`](https://github.com/tantdna2/SafeShift/commit/3bcd3535ea51e023de77417ed5f2077607d49c93); [ChatGPT hậu merge](https://github.com/tantdna2/SafeShift/pull/131#issuecomment-6394591862) |
| Hướng xuyên Seminar–Khóa luận và Master Plan M1–M8, chỉ phạm vi tài liệu | [#133](https://github.com/tantdna2/SafeShift/pull/133), [`bffc6032e65b38cb04b33520275a089d87d0d37f`](https://github.com/tantdna2/SafeShift/commit/bffc6032e65b38cb04b33520275a089d87d0d37f); [ChatGPT hậu merge](https://github.com/tantdna2/SafeShift/pull/133#issuecomment-6399480255) |
| Execution Plan M1–M8 và continuity | [#134 MERGED](https://github.com/tantdna2/SafeShift/pull/134), [`a425ab04695319a42bfdd2f89192717dddbb891b`](https://github.com/tantdna2/SafeShift/commit/a425ab04695319a42bfdd2f89192717dddbb891b); trạng thái/merge SHA kiểm trực tiếp GitHub trong task này, cùng [xác nhận ChatGPT](https://github.com/tantdna2/SafeShift/pull/134#issuecomment-6406751802) |

## ACTIVE WORK

- **M1-01 + M2-01 trong một Draft PR:** hồ sơ quyết định append-only, [protocol](research/SEMINAR_PROTOCOL.md), [config v1](research/seminar_analysis_config.v1.json) và đồng bộ tài liệu hiện hành.
- Branch: `docs/m1-m2-seminar-protocol-20261026`; BASE bằng main ở đầu file.
- Trạng thái bàn giao: [PR #135](https://github.com/tantdna2/SafeShift/pull/135) **OPEN / DRAFT**, chưa merge; HEAD bổ sung quyết định/trạng thái chờ ChatGPT đối chiếu trước quyền merge.
- Phạm vi tiếp nối cùng nhiệm vụ: append quyết định M2 + cập nhật trạng thái; giữ nguyên protocol/config từng byte. Không setup M3, artifact analysis, raw replay, inference/GPU/TEST hoặc PR phụ.
- BASE/HEAD chính xác và kết quả kiểm tra cuối ghi ở mô tả PR để tránh hash tự tham chiếu.

## KEY DECISIONS

- Giữ đề tài PR #133, A1–A8 đã được Owner quyết định trong quyền dự án theo [nguồn thật](https://github.com/tantdna2/SafeShift/pull/134#issuecomment-6406751802); không phải chữ ký giảng viên/đổi chuẩn học phần.
- Bốn model: Qwen2.5-VL-3B-Instruct, Qwen3-VL-8B-Instruct, InternVL3-2B-hf, Moondream2.
- Owner chấp nhận bảng bốn model, định lượng ba, Moondream2 HNLO TRAIN N/A ở cấp dự án (A4). Ngoại lệ học vụ chưa xác minh; feature set Khóa luận cần quyết định riêng.
- Q25/IVL3 full 3.763; common ba model đúng 3.539 SUCCESS Q3 V4 gốc; Q3 planned 3.763 = 3.539 SUCCESS + 1 lỗi + 223 chưa chạy. Recovery224 riêng, không pooling.
- IVL3/Q3 là saved-score verification, không raw PASS mới. Metric/sensitivity v1 đúng hai hash đã được Owner duyệt; source identity/CI và các dữ liệu thiếu vẫn chưa được khắc phục.
- Các cờ PENDING/`frozen=false`/refs null trong protocol/config bất biến là snapshot trước duyệt. Hiệu lực dùng DEC-20261026-M2 + đúng hai hash + bằng chứng hậu merge/task; M3 phải từ chối chạy khi thiếu quyết định có hiệu lực hoặc sai hash.
- False-safe V4-only phải đếm đúng ID; không lấy 38 hoặc khoảng 30–38 từ composite làm số chính thức. Bất đồng suy biến trong tập triage mới là giả thuyết cần đo.
- H-T so cùng predictor/cohort/review budget, baseline Q3-HNLO-only và toàn chi phí model phụ; đánh giá xác nhận cần nguồn/nhãn độc lập, target giữ kín.

## KNOWN BLOCKERS

- B04 đã đáp ứng review/phê duyệt khoa học: [ChatGPT đối chiếu PASS](https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6408340899), [Owner duyệt đúng version](https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6408943462). Còn kiểm HEAD bổ sung, quyền merge và xác minh hậu merge để khóa hiệu lực repository.
- B01/B02/B05: Owner chấp nhận 12 atoms/7 nhóm BLOCKED (**19 placeholders**), continuous controls N/A, mismatch/proxy BLOCKED; giữ năm folder_domain. Không kết luận hazard strata/đối chứng chưa có/nhân quả; thiếu dữ liệu vẫn còn.
- B03: Owner chấp nhận giới hạn hash-bound saved-report/provenance chưa đủ, không nâng thành raw audit mới; recovery reference-only, V4 gốc riêng.
- B06: M3 CPU SYNTHETIC có điều kiện, chưa kích hoạt khi Draft; M4/artifact thật, raw/GPU/inference/ảnh/nhãn/TEST/tài nguyên ngoài và Khóa luận chưa cấp quyền. Học vụ/ngoại lệ chính thức chưa xác minh.
- Chưa có nguồn đánh giá độc lập/nhãn chuyên gia/target custodian/precision-events và tài nguyên được xác nhận: chặn M6/M7 xác nhận, không chặn Seminar sau các gate riêng.
- Raw audit/model capability còn giới hạn; không yêu cầu raw replay mới cho mọi kết luận saved-score. Moondream2 thiếu endpoint tương thích không được âm thầm loại bỏ.

## NEXT TASK

**M3-01 — Triển khai trọn vẹn hệ thống phân tích Seminar CPU, sau xác minh hậu merge M1/M2.**

- **Chưa được bắt đầu:** PR #135 phải merge, ChatGPT xác minh hậu merge M1/M2 và chính thức giao task M3. Phê duyệt Owner đã có, không cần khảo sát/lập kế hoạch hoặc xin lại quyết định cùng version.
- Đầu vào trực tiếp: protocol/config v1 đã review đúng hash, quyết định append-only và [Execution Plan M3](EXECUTION_PLAN.md#m3-01--hoàn-thiện-hệ-thống-phân-tích-seminar-cpu); không khảo sát/lập kế hoạch lần nữa.
- Sản phẩm M3: reader/provenance/status, metric/report R1–R5, CLI, synthetic tests/oracle, docs/config/receipt; kiểm quyết định M2 có hiệu lực + hai hash trước chạy fixture. Không đọc artifact thật hoặc triển khai GPU/backend/triage.

## IMPORTANT REFERENCES

- [Hướng nghiên cứu](research/SEMINAR_THESIS_DIRECTION_LOCK_20261025.md), [Master Plan](research/SEMINAR_THESIS_MASTER_PLAN_20261025.md), [Execution Plan](EXECUTION_PLAN.md).
- [AGENTS](../AGENTS.md), [README](../README.md), [ROADMAP](ROADMAP.md), [ARCHITECTURE](ARCHITECTURE.md), [RESEARCH_OVERVIEW](RESEARCH_OVERVIEW.md).
- [Results/limitations](RESULTS_AND_LIMITATIONS.md), [source gate](SOURCE_FEASIBILITY_GATE_20261024.md), [receipt](SOURCE_FEASIBILITY_RECEIPT_20261024.json).
- [Điều kiện hậu audit #133](https://github.com/tantdna2/SafeShift/pull/133#issuecomment-6399375594): eligible set, exact V4 errors, đủ sự kiện độc lập, chi phí/đối chứng và chuẩn giảng viên.
- [HISTORY](HISTORY.md): snapshot legacy `31a04e6f7175cca818c63b4de0153246b3f3ecdb`, refs bất biến, source locks và PR cũ; không đọc lại toàn bộ lịch sử.

## SAFETY / RESEARCH BOUNDARIES

- Không mở TEST/dữ liệu khóa, GPU/inference, annotation hoặc chạy lại release legacy khi chưa có quyền đúng phạm vi/source/run/attempt.
- Không tự đổi dataset/split/nhãn/metric/roster/quyết định; ghi quyết định mới sau duyệt, không sửa lịch sử. TRAIN phơi nhiễm không thành holdout.
- Giữ raw bất biến và raw-before-parse khi được phép inference; derived ở `data/processed/`, không commit dataset/raw/checkpoint/secrets hoặc dùng `git add -f`.
- Không tác động PR cũ/legacy refs hoặc nâng saved-score thành raw audit. Dừng task hiện tại ở đúng một Draft PR để ChatGPT kiểm GitHub.

## UPDATE RULES

- Mỗi task thay trạng thái phải cập nhật file này **trong cùng PR**, không PR phụ cho cập nhật thường kỳ; giữ khoảng tối đa 120 dòng, chỉ trạng thái hiện hành.
- Codex không ghi MERGED khi mới Draft. Sau merge, ChatGPT xác minh trực tiếp PR/merge commit/main và biên bản GitHub; đó là bằng chứng hoàn tất có thẩm quyền.
- Mở task/chat mới: đối chiếu state với GitHub thật; cập nhật facts đã kiểm chứng trong PR của task đó, giữ phần chưa kiểm là pending.
- Tách DONE sản phẩm, DONE kiểm toán/merge và DONE khoa học/thực nghiệm; không đánh dấu milestone từ việc merge.
- Không lưu nội dung chat dài, bí mật, raw data hoặc kết quả chưa kiểm chứng. Nếu chưa có biên bản hậu merge, ghi chờ xác minh.
