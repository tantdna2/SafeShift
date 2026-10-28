# SafeShift — PROJECT STATE

Cập nhật **28/10/2026 (Asia/Bangkok)**; main GitHub `064e31654fa44c5ad55fdb69159692ed69b78a77` (PR #140 MERGED). Không phải quyền thực nghiệm.
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
| Code PREP pilot ba VLM: notebooks, selector/bundle, grants, raw/replay/report/resume; FULL TRAIN khóa | [#138 MERGED](https://github.com/tantdna2/SafeShift/pull/138), [`843794119440dd18cca109ba345f7cefe4ec8552`](https://github.com/tantdna2/SafeShift/commit/843794119440dd18cca109ba345f7cefe4ec8552); [ChatGPT hậu merge PASS](https://github.com/tantdna2/SafeShift/pull/138#issuecomment-6460450628), chỉ CODE PREPARATION COMPLETE |
| Scratch `/kaggle/tmp`, output `/kaggle/working`, storage admission/receipt 28+4 GiB | [#139 MERGED](https://github.com/tantdna2/SafeShift/pull/139), [`4693d8c1eed4e60069272b975275e6adb17905fe`](https://github.com/tantdna2/SafeShift/commit/4693d8c1eed4e60069272b975275e6adb17905fe); code storage fix, không phải Kaggle/model PASS |
| Worker CPython 3.12/3.11 và GPU receipt trước ledger | [#140 MERGED](https://github.com/tantdna2/SafeShift/pull/140), [`064e31654fa44c5ad55fdb69159692ed69b78a77`](https://github.com/tantdna2/SafeShift/commit/064e31654fa44c5ad55fdb69159692ed69b78a77); thiếu `ensurepip` vẫn là blocker sau merge, không phải Kaggle/model PASS |

## ACTIVE WORK

- **Chuẩn bị và nghiệm thu 160 ảnh TRAIN gốc: PASS**, dừng trước Kaggle; [quyền CPU](https://github.com/tantdna2/SafeShift/pull/138#issuecomment-6460760653) đã xác minh, grant local không commit.
- Dùng nguyên source main/workspace gốc, không alias/copy raw; master hash, 3.763 ID TRAIN duy nhất và từng input hash/header PASS.
- Bundle local đủ **160 ID, 80 L04 + 48 L01 + 24 L02 + 8 L03**, 0 bổ sung; selector/load PASS; manifest SHA `f1ec6a202c3bba05d91cb3c507d5aa16d9aa3ded2418fa84bd62e77c05522995`.
- Owner chấp nhận giữ nguyên **156 JPEG + 4 PNG gốc mang đuôi .jpg**; 160/160 verify/decode/RGB/hash PASS, không sửa ảnh/đuôi/nhãn/ID; nguồn có 159 RGB + 1 RGBA.
- ZIP riêng tư 99.398.230 bytes, 166 regular files, CRC/từng SHA-256 PASS; ZIP SHA `d57e3ee48d45c2e8b6eb06e79ce4694198c7df21883af7bfb4f375395acad0cd`.
- 77 nhóm lịch sử (nhóm lớn nhất 79 ảnh), 15 kích thước; không claim độc lập.
  Bằng chứng riêng tư trong workspace gốc:
  `data/processed/three_vlm_acceptance_20261028/` (receipt, PNG bindings, checksum).
  Báo cáo BLOCKED cũ giữ nguyên lịch sử; receipt mới ghi PASS theo quyết định Owner.
  Không đổi notebook/source. Qwen/TEST/FULL_TRAIN vẫn đóng.
- [Phi a1](https://github.com/tantdna2/SafeShift/pull/138#issuecomment-6463455960)
  **CONSUMED/BLOCKED tại storage** trước inference: 19,501869 GiB free / 32 GiB
  yêu cầu; 160 NOT_ATTEMPTED. Không tái sử dụng grant a1. Smol a1 RESERVED,
  NOT_EXECUTED; không chạy với working cũ. Classification NOT_RUN,
  HNLO_UNVERIFIED cho cả hai; không suy OOM hay chất lượng từ storage failure.
- **Storage fix #139 đã MERGED.** Phi a2 do Owner báo: run
  `safeshift_phi_pilot_20261028_r2`, attempt `phi_pilot_20261028_a2`, ZIP SHA
  `de99f708f1120680028b4533a645f248e3e5ff44818ecccf7d573b7fc8525586`;
  160/160 ảnh, storage 28+4 GiB và T4×2 PASS, dừng trước inference tại
  `BLOCKED_PINNED_LINUX_PYTHON_311_OR_312_REQUIRED`; 0/160 inference. a2 đã
  CONSUMED, không tái sử dụng. Kernel 3.13.15 có `/usr/bin/python3.12`.
- Phi a3 supplied ZIP SHA `05cc071ec11384e25c9e2187a7be89141ba351bb2c05c83a5cffe066a574b088`:
  CPython 3.12.3/module thiết yếu PASS, chỉ thiếu `ensurepip`; không có 3.11. PR #140
  loại candidate trước venv/package dù 160/160 ảnh/storage PASS; attempt chưa consumed.
- Follow-up Draft từ BASE `064e316`: `venv --without-pip --copies`; wheel pip 25.0.1
  khóa URL/size/SHA được `pip --python` cài local-only vào target, rồi worker kiểm
  version/path/prefix trước pins, `pip check`, freeze/CPU ABI. Python 3.13 chỉ điều
  khiển bootstrap pip, không chạy worker/cài dependency model; lỗi BLOCKED trước ledger.
- Rehearsal Windows 3.11 thật PASS; full suites Win 165/4 SKIP, Linux 168/1 SKIP,
  không phải Kaggle 3.12 PASS. Notebook Phi/Smol tạo lại; Gemma vẫn BLOCKED.
- [Hậu merge #138](https://github.com/tantdna2/SafeShift/pull/138#issuecomment-6460450628)
  thay trạng thái FAIL/DRAFT cũ bằng CODE PREP COMPLETE. Grant Phi/Smol riêng không
  nâng thành model/HNLO PASS; Gemma nằm ngoài quyền lần này.

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

**ChatGPT kiểm follow-up Draft sửa thiếu `ensurepip`.** Sau merge, chạy storage và
environment preflight CPU-only trên Kaggle Python 3.13 + `/usr/bin/python3.12`, tải
receipt/sidecar rồi audit. Chưa cấp grant/pilot; Phi/Smol cần quyết định run/attempt
được review. Không tái sử dụng Phi a1/a2 hoặc Smol a1; a3 không tự cấp quyền chạy.

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
- Không tác động PR cũ/legacy refs hoặc nâng saved-score thành raw audit. Task dữ liệu dừng ở bundle để ChatGPT kiểm, hoặc báo BLOCKED khi thiếu quyền/nguồn; không tạo PR riêng chỉ cho trạng thái.

## UPDATE RULES

- Mỗi task thay trạng thái phải cập nhật file này **trong cùng PR**, không PR phụ cho cập nhật thường kỳ; giữ khoảng tối đa 120 dòng, chỉ trạng thái hiện hành.
- Codex không ghi MERGED khi mới Draft. Sau merge, ChatGPT xác minh trực tiếp PR/merge commit/main và biên bản GitHub; đó là bằng chứng hoàn tất có thẩm quyền.
- Mở task/chat mới: đối chiếu state với GitHub thật; cập nhật facts đã kiểm chứng trong PR của task đó, giữ phần chưa kiểm là pending.
- Tách DONE sản phẩm, DONE kiểm toán/merge và DONE khoa học/thực nghiệm; không đánh dấu milestone từ việc merge.
- Không lưu nội dung chat dài, bí mật, raw data hoặc kết quả chưa kiểm chứng. Nếu chưa có biên bản hậu merge, ghi chờ xác minh.
