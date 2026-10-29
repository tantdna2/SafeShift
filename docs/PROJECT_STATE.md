# SafeShift — PROJECT STATE

Cập nhật: **29/10/2026 (Asia/Bangkok)**. Bản nhớ trạng thái, không phải quyền thực nghiệm.
Main đã đối chiếu GitHub/fetch: `67fc1ffc9519e068072644e0f891932fed28f463`; #137 vẫn BASE `28fdf82512577f2ed0fb435fb2c12b88e82baf2f`.
Khi mở chat mới phải kiểm GitHub lại; không coi snapshot này là live state.

## PROJECT IDENTITY

- **Đề tài:** SafeShift — Đánh giá và cải thiện độ tin cậy của quyết định nguy cơ an toàn công nghiệp bằng mô hình ngôn ngữ–thị giác.
- **Chỉ thị Owner 27/10:** không thực hiện học phần Seminar riêng, chuyển thẳng sang Khóa luận. Không tự hủy quyết định hoặc đánh dấu M3/M4/M5 đã hoàn thành.
- **Đề xuất Khóa luận đang chờ duyệt:** [Master Execution Plan duy nhất](research/THESIS_EXECUTION_PLAN_2026.md), bốn VLM ngang hàng: phân loại độc lập → kiểm tra chéo luân phiên → hợp nhất quyết định và review. Q3 là mốc lịch sử; ba vị trí khác chưa qualified. Chưa APPROVED phương pháp/metric/roster/nguồn mới.
- **HNLO:** điểm xếp hạng tương đối, feature ứng viên; không xác suất nguy cơ/confidence đã hiệu chuẩn, lợi ích triage chưa được chứng minh.

## CURRENT STATUS

- **M1 EFFECTIVE cấp dự án / M2 v1 FROZEN** theo [DECISIONS](research/DECISIONS.md) + hai SHA-256 + [hậu merge #135](https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6409830030). Các lời premerge/PENDING trong tài liệu cũ là snapshot; không sửa bytes M2 để đổi cờ.
- M1 successor thay đúng phần đã liệt kê của D9R22; DEC-PA3-011 lịch sử giữ PROPOSED, không duyệt toàn bộ A/C độc lập hoặc cấp quyền Khóa luận.
- PR #133/#134/#135 **MERGED**. Foundation V1/saved-score CPU có trên main. #138–#142/#144/#146 đã thêm runtime, raw custody, shared loader/native rehearsals; chưa có thesis peer/ensemble/viewer engine.
- **M3 IN_PROGRESS:** [#136 OPEN/DRAFT](https://github.com/tantdna2/SafeShift/pull/136), HEAD `b252e4cd469346c781183c69bad481ad9b69eff9`; [audit FAIL được xác nhận](https://github.com/tantdna2/SafeShift/pull/136#issuecomment-6412563251), lỗi metadata R3/R4. Chưa merge/COMPLETE; 77 tests do PR báo cáo không thay audit PASS.
- M3 chỉ được cấp CPU + fixtures SYNTHETIC. M4/artifact thật, annotation, GPU/inference/TEST và thesis execution chưa có grant từ task này. M4/M5 không được đánh dấu xong hoặc vô hiệu lịch sử.

## VERIFIED COMPLETED WORK

Chỉ ghi phần đã merge và có biên bản ChatGPT kiểm GitHub. Các test/replay được dẫn đúng người thực hiện; không nhận là đã tái chạy trong task này.

| Sản phẩm | PR / merge commit / bằng chứng hoàn tất |
| --- | --- |
| Foundation V1: records/validation, exact join, confusion/support/recall, transport interface, demo tổng hợp | [#130](https://github.com/tantdna2/SafeShift/pull/130), [`2810bee6f404a1c41cca4a2bbe45baf5ac48358a`](https://github.com/tantdna2/SafeShift/commit/2810bee6f404a1c41cca4a2bbe45baf5ac48358a); [ChatGPT hậu merge](https://github.com/tantdna2/SafeShift/pull/130#issuecomment-6380465749) |
| Source feasibility/sensitivity CPU và original V4 saved-score verification | [#131](https://github.com/tantdna2/SafeShift/pull/131), [`3bcd3535ea51e023de77417ed5f2077607d49c93`](https://github.com/tantdna2/SafeShift/commit/3bcd3535ea51e023de77417ed5f2077607d49c93); [ChatGPT hậu merge](https://github.com/tantdna2/SafeShift/pull/131#issuecomment-6394591862) |
| Hướng xuyên Seminar–Khóa luận và Master Plan M1–M8, chỉ phạm vi tài liệu | [#133](https://github.com/tantdna2/SafeShift/pull/133), [`bffc6032e65b38cb04b33520275a089d87d0d37f`](https://github.com/tantdna2/SafeShift/commit/bffc6032e65b38cb04b33520275a089d87d0d37f); [ChatGPT hậu merge](https://github.com/tantdna2/SafeShift/pull/133#issuecomment-6399480255) |
| Execution Plan M1–M8 và continuity | [#134 MERGED](https://github.com/tantdna2/SafeShift/pull/134), [`a425ab04695319a42bfdd2f89192717dddbb891b`](https://github.com/tantdna2/SafeShift/commit/a425ab04695319a42bfdd2f89192717dddbb891b); trạng thái/merge SHA kiểm trực tiếp GitHub trong task này, cùng [xác nhận ChatGPT](https://github.com/tantdna2/SafeShift/pull/134#issuecomment-6406751802) |
| M1/M2 quyết định khoa học dự án và protocol v1, chưa phải thực nghiệm | [#135 MERGED](https://github.com/tantdna2/SafeShift/pull/135), `28fdf82512577f2ed0fb435fb2c12b88e82baf2f`; [ChatGPT hậu merge/giao M3 synthetic](https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6409830030) |

## ACTIVE WORK

- **Task #137 hiện tại:** [chỉ thị 29/10](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6486252968), đồng bộ thiết kế ba tầng, [Kaggle failure/release gates](KAGGLE_FAILURES_AND_RELEASE_GATES.md), CPU wrapper/tests dùng builder/runtime hiện có; **PROPOSED — PENDING OWNER APPROVAL**.
- Branch `docs/thesis-execution-plan-20261027`, cùng [OPEN/DRAFT #137](https://github.com/tantdna2/SafeShift/pull/137), không branch/PR mới, không merge/Ready for Review. Code gate mới cần audit cùng methodology.
- **OWNER_SELECTED_CANDIDATES lịch sử:** `google/gemma-3-4b-it`, `microsoft/Phi-3.5-vision-instruct`, `HuggingFaceTB/SmolVLM2-2.2B-Instruct`; ngoài Figure 6 InspecSafe gốc, chưa qualified làm ba peers. Roster M1/M2 không đổi.
- **KAGGLE_COMPATIBILITY:** Phi a6 và Smol a2 đã có real GPU evidence đúng env/envelope, không bảo đảm full run. Phi 0/160 C1 valid; Smol 107/160 valid đều Level01, 53 INVALID; cả hai HNLO validated=0, attempts CONSUMED, NO_GO_FULL_TRAIN. Gemma 10 source files 401 → BLOCKED, chưa GPU failure. [Receipts và giới hạn](KAGGLE_FAILURES_AND_RELEASE_GATES.md).
- **SCIENTIFIC_UTILITY: UNPROVEN; ROSTER/FEATURE/PRIMARY CHANGE: PENDING O1–O3/T0; NEW RUN AUTHORIZATION: NOT_GRANTED.** 2×T4 không pooled 32 GB; #137 không tải weights/chạy GPU/native model/open TEST/tạo grant.
- **CPU gate:** `scripts.check_notebook_release` kiểm exact runtime main snapshot, reproducible six notebooks/source hashes và unittest; receipt giữ native skips/GPU gates BLOCKED. Counts/SHA thực chạy ghi PR body; không thay release notebook/config/parser/HNLO.
- **Integration BLOCKED:** merge-tree báo conflict PROJECT_STATE với main mới; chưa merge/rebase/force-push. Chờ quyền tích hợp main trong cùng branch, reconcile state rồi kiểm integrated HEAD; snapshot CODE_PASS không thay kiểm tích hợp.
- **Review:** PRE-AUDIT PASS cũ ở `6b7b3b9828a61440cb60733fe4640d9a237db0e0` không bao phủ thay đổi. ChatGPT kiểm HEAD/diff mới rồi audit khoa học độc lập + code gates trước merge; audit đang mở thì bổ sung cùng session Antigravity, không tự nhận audit PASS.
- [#147](https://github.com/tantdna2/SafeShift/issues/147) diagnostic Phi/Smol riêng chưa khép; [#148](https://github.com/tantdna2/SafeShift/issues/148) tuyển ba model **ON HOLD** đến review/audit/quyết định. Không mở longlist ở #137.
- Năm file scope: kế hoạch, PROJECT_STATE, failure runbook, wrapper và tests. Không sửa DECISIONS/M2/AGENTS, dataset/nhãn/metric đã khóa, six notebooks hoặc PR #136. BASE/HEAD/tests cuối trong PR body tránh self-reference.

## KEY DECISIONS

- Giữ đề tài PR #133, A1–A8 đã được Owner quyết định trong quyền dự án theo [nguồn thật](https://github.com/tantdna2/SafeShift/pull/134#issuecomment-6406751802); không phải chữ ký giảng viên/đổi chuẩn học phần.
- Bốn model: Qwen2.5-VL-3B-Instruct, Qwen3-VL-8B-Instruct, InternVL3-2B-hf, Moondream2.
- Owner chấp nhận bảng bốn model, định lượng ba, Moondream2 HNLO TRAIN N/A ở cấp dự án (A4). Ngoại lệ học vụ chưa xác minh; feature set Khóa luận cần quyết định riêng.
- Q25/IVL3 full 3.763; common ba model đúng 3.539 SUCCESS Q3 V4 gốc; Q3 planned 3.763 = 3.539 SUCCESS + 1 lỗi + 223 chưa chạy. Recovery224 riêng, không pooling.
- IVL3/Q3 là saved-score verification, không raw PASS mới. Metric/sensitivity v1 đúng hai hash đã được Owner duyệt; source identity/CI và các dữ liệu thiếu vẫn chưa được khắc phục.
- Các cờ PENDING/`frozen=false`/refs null trong protocol/config bất biến là snapshot trước duyệt. Hiệu lực dùng DEC-20261026-M2 + đúng hai hash + bằng chứng hậu merge/task; M3 phải từ chối chạy khi thiếu quyết định có hiệu lực hoặc sai hash.
- False-safe V4-only phải đếm đúng ID; không lấy 38 hoặc khoảng 30–38 từ composite làm số chính thức. Bất đồng suy biến trong tập triage mới là giả thuyết cần đo.
- Đề xuất H1 mới: strict-majority vs strongest single chọn D/V, planned Macro-F1 với abstain/INVALID counted, safety/cost guardrails; bốn focal review là secondary, HNLO chỉ khi qualified từng model. O1–O3 chưa duyệt; target phải nguồn/nhãn độc lập và giữ kín.

## KNOWN BLOCKERS

- B04 M2 đã khép approval + hiệu lực bằng hậu merge #135; không yêu cầu xin lại. #136 có audit FAIL riêng, không làm M2 mất hiệu lực.
- B01/B02/B05: Owner chấp nhận 12 atoms/7 nhóm BLOCKED (**19 placeholders**), continuous controls N/A, mismatch/proxy BLOCKED; giữ năm folder_domain. Không kết luận hazard strata/đối chứng chưa có/nhân quả; thiếu dữ liệu vẫn còn.
- B03: Owner chấp nhận giới hạn hash-bound saved-report/provenance chưa đủ, không nâng thành raw audit mới; recovery reference-only, V4 gốc riêng.
- B06: quyền M3 CPU SYNTHETIC đã được giao sau #135; M4/artifact thật, raw/GPU/inference/ảnh/nhãn/TEST/tài nguyên ngoài và thesis chưa được cấp bởi task này.
- O1–O8 PENDING: chuẩn học vụ/ba tầng/primary, protocol/metric/final four roster, source/GT/custody, precision/cost/stop, từng run rights, evidence study và #136. Thiếu bốn qualified hoặc nguồn độc lập → NO-GO thiết kế xác nhận; scope giảm cần Owner quyết định, không tự mở model zoo.
- Raw audit/model capability còn giới hạn; không yêu cầu raw replay mới cho mọi kết luận saved-score. Moondream2 thiếu endpoint tương thích không được âm thầm loại bỏ.

## NEXT TASK

**T0 — Ghi quyết định chuyển tiếp và hợp đồng ba tầng, sau review/audit và Owner duyệt kế hoạch.**

- Dùng §14 O1–O8 và task card T0 trong [kế hoạch mới](research/THESIS_EXECUTION_PLAN_2026.md); append chỉ quyết định thật, protocol/config thesis tách M2, numerical fields cần pilot giữ gated.
- Đây là NEXT TASK cho lộ trình đề xuất, không tự mở lại M3 hoặc sửa #136. Không GPU/annotation/TEST/target; không tự xác nhận giảng viên đồng ý.

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
