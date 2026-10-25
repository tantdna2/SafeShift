# SafeShift — PROJECT STATE

Cập nhật: **26/10/2026 (Asia/Bangkok)**. Bản nhớ trạng thái, không phải quyền thực nghiệm.
Main đã fetch/đối chiếu GitHub: `bffc6032e65b38cb04b33520275a089d87d0d37f`.
Khi mở chat mới phải kiểm GitHub lại; không coi snapshot này là live state.

## PROJECT IDENTITY

- **Đề tài:** SafeShift — Đánh giá và cải thiện độ tin cậy của quyết định nguy cơ an toàn công nghiệp bằng mô hình ngôn ngữ–thị giác.
- **Seminar:** hồi cứu nhãn sinh ra, HNLO, lỗi nguy hiểm và bất đồng trên TRAIN đã phơi nhiễm.
- **Khóa luận:** kiểm chứng logistic có regularization xếp ưu tiên ảnh cần người kiểm tra bằng HNLO+bất đồng, giữ Qwen3 predictor cố định theo protocol được duyệt.
- **HNLO:** đối tượng kiểm định Seminar, feature ứng viên Khóa luận; không xác suất nguy cơ đã hiệu chuẩn, lợi ích chưa được chứng minh.

## CURRENT STATUS

- **Milestone hiện tại: M1 — chờ phê duyệt khoa học chính thức.** M2–M8 chưa hoàn tất/chưa được tài liệu này cấp quyền.
- D9R22 vẫn có hiệu lực; HNLO/DEC-PA3-011 **PROPOSED**; A/C chưa được phê duyệt.
- PR #133 hoàn thành về tài liệu và merge; không đồng nghĩa M1 PASS/protocol freeze.
- Foundation V1 + công cụ saved-score CPU đã có; chưa có hệ thống Seminar R1–R5 hoàn chỉnh, backend VLM/raw writer/triage production.
- Chặn setup/phân tích mới cho đến quyết định M1, protocol M2 và task/quyền tương ứng.

## VERIFIED COMPLETED WORK

Chỉ ghi phần đã merge và có biên bản ChatGPT kiểm GitHub. Các test/replay được dẫn đúng người thực hiện; không nhận là đã tái chạy trong task này.

| Sản phẩm | PR / merge commit / bằng chứng hoàn tất |
| --- | --- |
| Foundation V1: records/validation, exact join, confusion/support/recall, transport interface, demo tổng hợp | [#130](https://github.com/tantdna2/SafeShift/pull/130), [`2810bee6f404a1c41cca4a2bbe45baf5ac48358a`](https://github.com/tantdna2/SafeShift/commit/2810bee6f404a1c41cca4a2bbe45baf5ac48358a); [ChatGPT hậu merge](https://github.com/tantdna2/SafeShift/pull/130#issuecomment-6380465749) |
| Source feasibility/sensitivity CPU và original V4 saved-score verification | [#131](https://github.com/tantdna2/SafeShift/pull/131), [`3bcd3535ea51e023de77417ed5f2077607d49c93`](https://github.com/tantdna2/SafeShift/commit/3bcd3535ea51e023de77417ed5f2077607d49c93); [ChatGPT hậu merge](https://github.com/tantdna2/SafeShift/pull/131#issuecomment-6394591862) |
| Hướng xuyên Seminar–Khóa luận và Master Plan M1–M8, chỉ phạm vi tài liệu | [#133](https://github.com/tantdna2/SafeShift/pull/133), [`bffc6032e65b38cb04b33520275a089d87d0d37f`](https://github.com/tantdna2/SafeShift/commit/bffc6032e65b38cb04b33520275a089d87d0d37f); [ChatGPT hậu merge](https://github.com/tantdna2/SafeShift/pull/133#issuecomment-6399480255) |

## ACTIVE WORK

- **PLAN-01:** hoàn thiện Execution Plan và cơ chế continuity trong đúng hai file Markdown.
- Branch: `docs/final-execution-plan-20261026`; BASE bằng main ở đầu file.
- Trạng thái: đang chuẩn bị Draft PR; chưa merge, chưa có kiểm toán/duyệt ChatGPT cho PR này.
- Phạm vi: task cards M1–M8, hồ sơ M1, reuse/gap/setup tối thiểu, checks/cohort/authority và trạng thái dự án. Không code/setup/inference/GPU/TEST.
- BASE/HEAD chính xác và kết quả kiểm tra cuối ghi ở mô tả PR để tránh hash tự tham chiếu.

## KEY DECISIONS

- Giữ đề tài đã chọn trong PR #133; không mở lại P1/P2/P3. Lựa chọn đề xuất không tự thành quyết định khoa học.
- Bốn model: Qwen2.5-VL-3B-Instruct, Qwen3-VL-8B-Instruct, InternVL3-2B-hf, Moondream2.
- Seminar đề nghị bảng bốn model, định lượng ba; Moondream2 HNLO TRAIN N/A cần ngoại lệ Lead, **chưa được duyệt**. Feature set Khóa luận cần duyệt riêng.
- Q25/IVL3 full 3.763; common ba model đúng 3.539 SUCCESS Q3 V4 gốc; Q3 planned 3.763 = 3.539 SUCCESS + 1 lỗi + 223 chưa chạy. Recovery224 riêng, không pooling.
- IVL3/Q3 là saved-score verification, không raw PASS mới. Source identity/CI chưa được xác minh/tính; sensitivity vẫn PROPOSED_EXPLORATORY.
- False-safe V4-only phải đếm đúng ID; không lấy 38 hoặc khoảng 30–38 từ composite làm số chính thức. Bất đồng suy biến trong tập triage mới là giả thuyết cần đo.
- H-T so cùng predictor/cohort/review budget, baseline Q3-HNLO-only và toàn chi phí model phụ; đánh giá xác nhận cần nguồn/nhãn độc lập, target giữ kín.

## KNOWN BLOCKERS

- Thiếu quyết định Research Lead/giảng viên về RQ/HNLO, ngoại lệ Moondream2, N/A/control và mức đóng góp Khóa luận đủ chuẩn: chặn M1 PASS/M2.
- Chưa có protocol M2 đã duyệt và authority task setup/CPU artifact mới: chặn M3/M4; code Foundation không tự cấp quyền.
- Chưa xác minh đủ hazard map/continuous controls cho mọi ô Seminar; M2 phải khóa khả dụng/N/A có duyệt, không bịa field.
- Chưa có nguồn đánh giá độc lập/nhãn chuyên gia/target custodian/precision-events và tài nguyên được xác nhận: chặn M6/M7 xác nhận, không chặn Seminar sau các gate riêng.
- Raw audit/model capability còn giới hạn; không yêu cầu raw replay mới cho mọi kết luận saved-score. Moondream2 thiếu endpoint tương thích không được âm thầm loại bỏ.

## NEXT TASK

**M1-01 — Nhận và ghi quyết định khoa học chính thức.**

- Đầu vào: [EXECUTION_PLAN §2](EXECUTION_PLAN.md#2-hồ-sơ-m1-sẵn-để-trình-research-leadgiảng-viên), hai tài liệu PR #133, điều kiện hậu audit và thẩm quyền D9R22/DEC-PA3-011.
- Điều kiện bắt đầu: bàn giao/review kế hoạch hiện tại hoàn tất theo quy trình, task trình duyệt được giao; chỉ ghi approved khi có phản hồi thực của người có thẩm quyền.
- Sản phẩm: quyết định append-only dưới `docs/research/DECISIONS.md` (dự kiến), người duyệt/ngày/bằng chứng, approved/pending/ngoại lệ và quyền bước tiếp; cập nhật state cùng Draft PR. Hồ sơ trình duyệt đã sẵn, không thêm PR soạn brief.
- Chỉ M1 PASS mới giao M2-01; không chuyển thẳng sang setup/thực nghiệm.

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
