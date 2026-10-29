# SafeShift — PROJECT STATE

Cập nhật: **29/10/2026 (Asia/Bangkok)**. Bản nhớ trạng thái, không phải quyền thực nghiệm.
Main đã fetch/đối chiếu và tích hợp: `67fc1ffc9519e068072644e0f891932fed28f463`; BASE/merge-base hiện tại của #137 là main này. BASE gốc `28fdf82` giữ trong lịch sử PR.
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
| Pilot PREP: selector/bundle/notebooks, scoped authority/ledger, raw/replay/report; FULL TRAIN khóa | [#138 MERGED](https://github.com/tantdna2/SafeShift/pull/138), `843794119440dd18cca109ba345f7cefe4ec8552`; [ChatGPT hậu merge CODE PREP COMPLETE](https://github.com/tantdna2/SafeShift/pull/138#issuecomment-6460450628), không model PASS |
| Scratch/output separation và storage admission | [#139 MERGED](https://github.com/tantdna2/SafeShift/pull/139), `4693d8c1eed4e60069272b975275e6adb17905fe`; storage fix không Kaggle/model PASS |
| Worker CPython 3.12/3.11 và GPU receipt trước ledger | [#140 MERGED](https://github.com/tantdna2/SafeShift/pull/140), `064e31654fa44c5ad55fdb69159692ed69b78a77`; ensurepip issue sau đó xử lý riêng |
| Pip bootstrap không cần ensurepip | [#141 MERGED](https://github.com/tantdna2/SafeShift/pull/141), `49ab2e8832683d4ae4877291cd7a82abbc533d2b`; trạng thái/merge SHA kiểm API, không nâng thành model PASS |
| Phi checkpoint/CLIP eager attention | [#142 MERGED](https://github.com/tantdna2/SafeShift/pull/142), `f8ba79cf17fb12a9745c555a692cbb42f32be45d`; native/CPU evidence tại [audit](PHI_EAGER_ATTENTION_AUDIT_20261029.md) |
| Phi shared loader + end-to-end CPU, nguồn #143 | [#144 MERGED](https://github.com/tantdna2/SafeShift/pull/144), `a7dacd6ebb1d0bb9ee3fd2c0fb63a0a1001e90e4`; [hồ sơ](PHI_KAGGLE_END_TO_END_143.md), real a6 outcome giữ dưới đây |
| Smol native processor/deps/loader/scripted pipeline, nguồn #145 | [#146 MERGED](https://github.com/tantdna2/SafeShift/pull/146), `67fc1ffc9519e068072644e0f891932fed28f463`; [readiness](SMOL_KAGGLE_READINESS_145.md)/[CPU receipt](SMOL_CPU_RECEIPT_145.json), không nhận 205 CPU PASS là behavior thật |

## PILOT EVIDENCE — GIỮ TỪ MAIN, KHÔNG TÁI AUDIT PRIVATE ARTIFACT

- **Bundle nghiệm thu CPU 28/10:** [quyền gốc](https://github.com/tantdna2/SafeShift/pull/138#issuecomment-6460760653), 160 TRAIN IDs = 80 L04/48 L01/24 L02/8 L03, 0 bổ sung; 3.763 master TRAIN IDs/hash và mỗi input được kiểm trong hồ sơ gốc, không TEST/nhãn mới.
- Owner giữ 156 JPEG + 4 PNG mang đuôi .jpg, 159 RGB + 1 RGBA; verify/decode/RGB/hash 160/160 PASS. Manifest SHA `f1ec6a202c3bba05d91cb3c507d5aa16d9aa3ded2418fa84bd62e77c05522995`.
- Private bundle ZIP 99.398.230 bytes/166 regular files, CRC/member hashes PASS theo receipt; SHA `d57e3ee48d45c2e8b6eb06e79ce4694198c7df21883af7bfb4f375395acad0cd`. 77 nhóm lịch sử (max79), 15 kích thước, không source independence. Receipt gốc `data/processed/three_vlm_acceptance_20261028/` ngoài Git; báo cáo BLOCKED cũ giữ lịch sử, không copy private artifacts.
- **Phi a6 CONSUMED / NO_GO_FULL_TRAIN:** [ChatGPT aggregate](https://github.com/tantdna2/SafeShift/pull/144#issuecomment-6480224537), 160 native calls, 0/160 C1 valid, 8 token sequences/142 lần cùng một chuỗi, HNLO validated=0; first12 technical PASS không nhãn PASS. ZIP SHA `19b9c201bde2c018b501b5eefd4cd00f8f4f6e9b7fe92b9cd79e6a9bfcfdb161`; không tái audit ZIP/private raw ở #137.
- **Smol a2 CONSUMED / NO_GO_FULL_TRAIN:** [ChatGPT aggregate](https://github.com/tantdna2/SafeShift/pull/146#issuecomment-6485519647), 160 native calls, 107 valid đều L01/53 INVALID, 2 responses, HNLO validated=0; observed frozen-continuation mismatch không giải thích được căn nguyên collapse. ZIP SHA `b1db13f4b7d788c1afb98e1cc3e4fc1d87715a7c876a233807009ab84e32ae7b`.
- Phi a1/a2/a4/a5 CONSUMED, a3 FAILED_PRELEDGER/nonconsumed; Smol a1 lịch sử RESERVED/NOT_EXECUTED, không quyền dùng source mới. [Runbook](KAGGLE_THREE_VLM_PILOT.md)/[failure register](KAGGLE_FAILURES_AND_RELEASE_GATES.md). Không parser rescue/đổi C1/HNLO surfaces; model-vs-integration causes còn UNKNOWN.
- Gemma **BLOCKED_SOURCE_TOKENIZER_AUDIT_INCOMPLETE**, 10 config/tokenizer HTTP401, lock `files={}` giữ nguyên; chưa GPU failure/grant. Qwen/TEST/FULL_TRAIN vẫn đóng trong task này; grants cũ không chuyển thành quyền thesis.

## ACTIVE WORK

- **Task #137 hiện tại:** [chỉ thị 29/10](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6486252968), đồng bộ thiết kế ba tầng, [Kaggle failure/release gates](KAGGLE_FAILURES_AND_RELEASE_GATES.md), CPU wrapper/tests dùng builder/runtime hiện có; **PROPOSED — PENDING OWNER APPROVAL**.
- Branch `docs/thesis-execution-plan-20261027`, cùng [OPEN/DRAFT #137](https://github.com/tantdna2/SafeShift/pull/137), không branch/PR mới, không merge PR vào main/Ready for Review. Code gate mới cần audit cùng methodology.
- **OWNER_SELECTED_CANDIDATES lịch sử:** `google/gemma-3-4b-it`, `microsoft/Phi-3.5-vision-instruct`, `HuggingFaceTB/SmolVLM2-2.2B-Instruct`; ngoài Figure 6 InspecSafe gốc, chưa qualified làm ba peers. Roster M1/M2 không đổi.
- **KAGGLE_COMPATIBILITY:** Phi a6 và Smol a2 đã có real GPU evidence đúng env/envelope, không bảo đảm full run. Phi 0/160 C1 valid; Smol 107/160 valid đều Level01, 53 INVALID; cả hai HNLO validated=0, attempts CONSUMED, NO_GO_FULL_TRAIN. Gemma 10 source files 401 → BLOCKED, chưa GPU failure. [Receipts và giới hạn](KAGGLE_FAILURES_AND_RELEASE_GATES.md).
- **SCIENTIFIC_UTILITY: UNPROVEN; ROSTER/FEATURE/PRIMARY CHANGE: PENDING O1–O3/T0; NEW RUN AUTHORIZATION: NOT_GRANTED.** 2×T4 không pooled 32 GB; #137 không tải weights/chạy GPU/native model/open TEST/tạo grant.
- **CPU gate:** `scripts.check_notebook_release` kiểm exact integrated commit snapshot, reproducible six notebooks/source hashes và unittest; receipt giữ native skips/GPU gates BLOCKED. Counts/SHA thực chạy ghi PR body; không thay release notebook/config/parser/HNLO.
- **Integration:** [ChatGPT cho phép](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6487634755) merge main vào đúng branch; chỉ conflict file này, đã reconcile facts main + thesis PROPOSED. Merge commit thông thường, không rebase/force-push; HEAD/parents/tests integrated thật ghi PR body, không tự nhận audit PASS.
- **Review:** PRE-INTEGRATION SOURCE REVIEW PASS ở `68b875b` chỉ cho tích hợp, không scientific/merge/audit PASS. ChatGPT phải kiểm integrated HEAD/diff rồi audit khoa học độc lập + code gates trước merge; nếu audit đã mở, bổ sung cùng session Antigravity.
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
