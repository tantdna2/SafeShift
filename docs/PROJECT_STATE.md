# SafeShift — PROJECT STATE

Cập nhật: **27/10/2026 (Asia/Bangkok)**. Bản nhớ trạng thái, không phải quyền thực nghiệm.
Main đã fetch/đối chiếu GitHub: `28fdf82512577f2ed0fb435fb2c12b88e82baf2f` (PR #135 MERGED).
Khi mở chat mới phải kiểm GitHub lại; không coi snapshot này là live state.

## PROJECT IDENTITY

- **Đề tài:** SafeShift — Đánh giá và cải thiện độ tin cậy của quyết định nguy cơ an toàn công nghiệp bằng mô hình ngôn ngữ–thị giác.
- **Seminar:** hồi cứu nhãn sinh ra, HNLO, lỗi nguy hiểm và bất đồng trên TRAIN đã phơi nhiễm.
- **Khóa luận:** kiểm chứng logistic có regularization xếp ưu tiên ảnh cần người kiểm tra bằng HNLO+bất đồng, giữ Qwen3 predictor cố định theo protocol được duyệt.
- **HNLO:** đối tượng kiểm định Seminar, feature ứng viên Khóa luận; không xác suất nguy cơ đã hiệu chuẩn, lợi ích chưa được chứng minh.

## CURRENT STATUS

- **M1:** **APPROVED khoa học dự án** tại [DEC-20261026-M1](research/DECISIONS.md); PR #135 đã merge, task pilot không tự nâng trạng thái ChatGPT xác minh hậu merge.
- **M2 v1:** **OWNER_APPROVED_FOR_PROJECT_SEMINAR**, đúng hai SHA-256 tại [DEC-20261026-M2](research/DECISIONS.md#dec-20261026-m2); PR #135 đã MERGED theo GitHub. Task pilot không sửa protocol/config/quyết định hoặc tự xác nhận hậu merge khoa học của ChatGPT.
- D9R22/successor theo đúng decision và bằng chứng hiệu lực gốc; không đổi trong task pilot. DEC-PA3-011 lịch sử giữ PROPOSED, không duyệt toàn bộ A/C độc lập.
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

- **Owner giao code PREP pilot TRAIN ba VLM:** Gemma 3 4B, Phi-3.5 Vision, SmolVLM2-2.2B; 160 main + tối đa 20 Qwen V4 false-safe, cùng exact IDs, classification và kiểm HNLO riêng từng model.
- Branch: `implement/kaggle-three-vlm-pilot-20261027`, worktree riêng từ main đầu file; không dùng Draft #136/#137 làm base, không sửa chúng.
- Ba notebook native One-Click, selector/bundle, source/config/grant gates, raw/CPU replay/report/resume và full runner locked; [runbook](KAGGLE_THREE_VLM_PILOT.md), [audit](THREE_VLM_TECHNICAL_AUDIT.md). Một Draft PR để ChatGPT review; merge/audit độc lập chờ quyền riêng.
- **Thực nghiệm NOT_RUN**: không ảnh/dataset/raw Qwen artifact/weights/GPU; public model source/tokenizer CPU only. Gemma tokenizer gated 401. Ngưỡng/manifest/HNLO contract chờ Lead duyệt; không tự cấp grant.
- BASE/HEAD chính xác và kết quả kiểm tra cuối ghi ở mô tả PR để tránh hash tự tham chiếu.
- **PR #138 audit FAIL, đang khắc phục trong cùng branch/session** theo
  [biên bản ChatGPT](https://github.com/tantdna2/SafeShift/pull/138#issuecomment-6438422457).
  Sửa admission scratch/output theo filesystem, chuyển temp/cache về working,
  giữ bằng chứng khi worker/export lỗi, chặn Gemma khi source lock chưa đủ;
  tái hiện cài thư viện Linux đúng hai bước. Bằng chứng cuối trong
  [technical audit](THREE_VLM_TECHNICAL_AUDIT.md). Không tự nâng FAIL thành audit PASS.

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

- B04 có [ChatGPT đối chiếu PASS](https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6408340899), [Owner duyệt version](https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6408943462), PR #135 đã merge. Không nâng trạng thái audit hay kiểm hiệu lực M3 trong task pilot.
- B01/B02/B05: Owner chấp nhận 12 atoms/7 nhóm BLOCKED (**19 placeholders**), continuous controls N/A, mismatch/proxy BLOCKED; giữ năm folder_domain. Không kết luận hazard strata/đối chứng chưa có/nhân quả; thiếu dữ liệu vẫn còn.
- B03: Owner chấp nhận giới hạn hash-bound saved-report/provenance chưa đủ, không nâng thành raw audit mới; recovery reference-only, V4 gốc riêng.
- B06: M3 CPU SYNTHETIC có điều kiện, chưa kích hoạt khi Draft; M4/artifact thật, raw/GPU/inference/ảnh/nhãn/TEST/tài nguyên ngoài và Khóa luận chưa cấp quyền. Học vụ/ngoại lệ chính thức chưa xác minh.
- Chưa có nguồn đánh giá độc lập/nhãn chuyên gia/target custodian/precision-events và tài nguyên được xác nhận: chặn M6/M7 xác nhận, không chặn Seminar sau các gate riêng.
- Raw audit/model capability còn giới hạn; không yêu cầu raw replay mới cho mọi kết luận saved-score. Moondream2 thiếu endpoint tương thích không được âm thầm loại bỏ.

## NEXT TASK

**ChatGPT kiểm HEAD sửa của Draft PR #138, sau đó tái audit tập trung trong cùng session Antigravity #138.**
Giữ FAIL/DRAFT tới khi được đối chiếu; chưa merge hoặc có grant Kaggle.

- Code PREP chỉ hoàn tất khi có notebook/runner/tests/docs và một Draft PR; chưa là PASS model hoặc HNLO. Không sửa/merge PR #136/#137 hoặc mở PR phụ.
- Sau review mới xét grant CPU preparation (3763 TRAIN headers/hashes/folder GT), optional original-V4 saved artifacts, rồi manifest/ngưỡng/source-bound inference grant riêng từng model. Hiện tất cả NOT_GRANTED.
- Pilot thực nghiệm DONE chỉ khi có archive thật và kết luận từng model; FULL TRAIN 3763/model là nhiệm vụ sau, cần pilot GO + ChatGPT review + Owner grant riêng; TEST đóng.

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
