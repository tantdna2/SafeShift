# SafeShift — PROJECT STATE

Cập nhật **29/10/2026 (Asia/Bangkok)** trong task [#148](https://github.com/tantdna2/SafeShift/issues/148).
Main đã fetch/kiểm: `1488dcb5212164e2946a15055d1da6e8be9096d2`.
Đây là snapshot trạng thái, không quyền thực nghiệm; mở task mới phải kiểm GitHub lại.

## PROJECT IDENTITY

- SafeShift nghiên cứu độ tin cậy của VLM khi phân loại nguy cơ công nghiệp, kiểm tra chéo và ưu tiên người kiểm tra.
- Owner chuyển thẳng sang Khóa luận ngày 27/10; không tự đánh dấu Seminar/M3–M5 hoàn thành hoặc hủy lịch sử.
- [Kế hoạch Khóa luận](research/THESIS_EXECUTION_PLAN_2026.md) đề xuất bốn peers: phân loại độc lập → focal rotation → ensemble và review, hai endpoint cuối tách riêng.
- Thiết kế/primary/metric/final roster/nguồn mới vẫn **PROPOSED; O1–O8/T0 PENDING**. HNLO optional theo từng model, không xác suất nguy cơ hoặc confidence đã hiệu chuẩn.

## CURRENT STATUS

- **PR #137 MERGED**, commit main trên; [ChatGPT hậu merge PASS](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6488172066). Hoàn tất phạm vi repository/technical của #137, không scientific approval hoặc GPU readiness.
- [Issue #148 cập nhật 29/10](https://github.com/tantdna2/SafeShift/issues/148) bỏ ON HOLD **chỉ cho public research/metadata/CPU không weights và shortlist report**. Dòng #137 DRAFT/#148 ON HOLD trong các tài liệu cũ là snapshot đã bị live evidence này thay thế trong phạm vi tương ứng.
- **M1 EFFECTIVE cấp dự án / M2 v1 FROZEN** theo [DECISIONS](research/DECISIONS.md), hai SHA và [hậu merge #135](https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6409830030). Không sửa bytes protocol/config để cập nhật cờ cũ.
- DEC-PA3-011 lịch sử giữ PROPOSED; successor M1 chỉ thay phần đã được duyệt của D9R22. Grant cũ không chuyển sang thesis/model/source mới.
- **M3 IN_PROGRESS:** [#136](https://github.com/tantdna2/SafeShift/pull/136) giữ OPEN/DRAFT/audit FAIL theo hồ sơ hậu merge #137; lỗi metadata R3/R4, chưa COMPLETE. Không sửa PR này trong #148.
- [#147 OPEN](https://github.com/tantdna2/SafeShift/issues/147) đã kiểm live: chẩn đoán Phi/Smol riêng, chưa chốt model-vs-integration causes.

## VERIFIED COMPLETED WORK

| Sản phẩm đã merge | Bằng chứng và giới hạn |
| --- | --- |
| Foundation V1, saved-score/source feasibility | [#130](https://github.com/tantdna2/SafeShift/pull/130), [#131](https://github.com/tantdna2/SafeShift/pull/131); records/exact join/CPU sensitivity, không raw audit mới cho mọi model. |
| Hướng/Execution Plan và M1/M2 | [#133](https://github.com/tantdna2/SafeShift/pull/133), [#134](https://github.com/tantdna2/SafeShift/pull/134), [#135](https://github.com/tantdna2/SafeShift/pull/135); M2 hiệu lực đúng hash/scope lịch sử. |
| Pilot PREP, storage, worker runtime và pip bootstrap | [#138](https://github.com/tantdna2/SafeShift/pull/138)–[#141](https://github.com/tantdna2/SafeShift/pull/141); không đồng nghĩa behavior PASS. |
| Phi attention/shared loader, Smol native/dependency rehearsal | [#142](https://github.com/tantdna2/SafeShift/pull/142), [#144](https://github.com/tantdna2/SafeShift/pull/144), [#146](https://github.com/tantdna2/SafeShift/pull/146); actual outcomes ở dưới. |
| Thesis plan PROPOSED, failure register và CPU release checker | [#137](https://github.com/tantdna2/SafeShift/pull/137), merge `1488dcb5212164e2946a15055d1da6e8be9096d2`; [hậu merge](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6488172066). Không có thesis ensemble/triage/viewer engine đã nghiệm thu. |

Tests trước đây thuộc receipts/PR tương ứng; không nhận là đã tái chạy trong task nghiên cứu #148.

Các merge SHA, audit links và bundle receipts chi tiết vẫn được lưu trong [snapshot PROJECT_STATE tại BASE](https://github.com/tantdna2/SafeShift/blob/1488dcb5212164e2946a15055d1da6e8be9096d2/docs/PROJECT_STATE.md); snapshot đó có trạng thái #137/#148 cũ, không thay trạng thái hiện tại ở trên.

## PILOT EVIDENCE — KHÔNG TÁI AUDIT PRIVATE ARTIFACT

- Bundle lịch sử: 160 TRAIN IDs, 80 L04/48 L01/24 L02/8 L03; không TEST. [Quyền/receipt gốc](https://github.com/tantdna2/SafeShift/pull/138#issuecomment-6460760653), [runbook](KAGGLE_THREE_VLM_PILOT.md); không tái mở ZIP/GT trong #148.
- **Phi a6 CONSUMED / NO_GO_FULL_TRAIN:** [aggregate ChatGPT](https://github.com/tantdna2/SafeShift/pull/144#issuecomment-6480224537), 160 native calls, 0/160 C1 valid, 8 sequences/142 lần lặp một sequence, HNLO validated 0. first 12 technical PASS không là classification PASS.
- **Smol a2 CONSUMED / NO_GO_FULL_TRAIN:** [aggregate ChatGPT](https://github.com/tantdna2/SafeShift/pull/146#issuecomment-6485519647), 160 calls, 107 valid đều Level01, 53 INVALID, 2 responses, HNLO validated 0; frozen-continuation mismatch không giải thích căn nguyên collapse.
- Phi a1/a2/a4/a5 consumed; a3 FAILED_PRELEDGER/nonconsumed. Smol a1 RESERVED/NOT_EXECUTED lịch sử không là quyền source mới. [Incident/gate register](KAGGLE_FAILURES_AND_RELEASE_GATES.md) giữ chi tiết.
- **Gemma BLOCKED_SOURCE_TOKENIZER_AUDIT_INCOMPLETE:**10 config/tokenizer 401 ở audit cũ. #148 kiểm anonymous 7 metadata requests cũng 401; không phải GPU failure, không tự tạo lock/grant.
- `OWNER_SELECTED_CANDIDATES` Gemma/Phi/Smol ngày 27/10 là sự kiện lịch sử, chưa qualified ba peers. Không cứu parser/C1/HNLO surfaces hoặc tiêu attempt tiếp.

## ACTIVE WORK — ISSUE #148, RESEARCH ONLY

- Báo cáo [THESIS_VLM_CANDIDATE_SCREENING_20261029](research/THESIS_VLM_CANDIDATE_SCREENING_20261029.md) đã soạn, **chờ ChatGPT review trong một Draft PR**, chưa approved/merged/qualified roster.
- Đã đọc InspecSafe arXiv v2, publisher, Figure 6, Table 3, S2/S3 và repo tác giả pinned; phân biệt paper benchmark với strict C1 JSON và TRAIN lịch sử.
- Longlist **12 ứng viên** có full revisions/official sources/license/access/config, ngoài Qwen3 mốc. Shortlist nghiên cứu có điều kiện: **(1) InternVL3_5-4B-Instruct, (2) MiniCPM-V-4, (3) LLaVA-OneVision-Qwen2-7B-OV-HF**.
- **0 ứng viên mới qualified**; classification thật/peer utility/HNLO của shortlist **UNVERIFIED**, quyền execution **BLOCKED**. Không sửa official roster hoặc tự thay Qwen3.
- CPU nhẹ thực chạy: 13 Hub records; 114 source/config/card files + 9 tokenizer files đọc/hash; 123 hash checks, 69 JSON parses, 27 AST parses; 5 MiniCPM config cross-checks, token-ID checks và 2 text-stage Jinja/C1 checks. Đây không native processor/tokenizer/model PASS.
- Không cài Torch/Transformers, tải weights, inference/GPU/Kaggle/TEST/private artifacts, tạo grant/notebook hoặc sửa khoa học. Chỉ 2 file tài liệu trong PR; BASE/HEAD/validation nằm trong PR body.
- Ranking là ưu tiên kiểm chứng theo nguồn, không accuracy đã đo. T4×2 không pooled 32 GB; FP16/attention/tiles/native wrapper và per-GPU memory còn phải G2/G4/G5.
- Báo cáo so A cũ fixed-Q3+auxiliary với B peers hiện proposed; tách classifier, cross-check, fusion/review và HNLO optional; không đặt numerical thresholds hoặc phê duyệt ensemble rule.

## KEY DECISIONS / LIMITS GIỮ NGUYÊN

- Roster lịch sử: Qwen2.5-VL-3B-Instruct, Qwen3-VL-8B-Instruct, InternVL3-2B-hf, Moondream2. Shortlist #148 không thay roster này.
- Owner chấp nhận Moondream2 HNLO TRAIN N/A cấp dự án; không suy ngoại lệ học vụ hoặc thesis final selection.
- Q25/IVL3 full 3.763; Q3 V4 gốc: 3.763 planned = 3.539 SUCCESS + 1 error + 223 not attempted. Recovery 224 riêng, không pooling; common panel đúng 3.539 original IDs.
- Q3 HNLO AUROC 0,9527927338600111 là saved-score verification đúng cohort, không raw PASS mới/generalization. [Results/limitations](RESULTS_AND_LIMITATIONS.md).
- False-safe V4-only phải đếm đúng original IDs; không dùng 38 hoặc khoảng 30–38 từ composite làm số chính thức. IVL3/Q3 saved-score verification không phải raw audit mới.
- B01/B02/B05 giữ 19 placeholders (12 atoms/7 groups), continuous controls N/A, mismatch/proxy BLOCKED; giữ 5 folder_domain, không source independence/causal claim.
- B03 provenance/raw limits chưa khép bởi receipt saved-score; không yêu cầu raw replay mới ngoài quyền chỉ vì có đường dẫn artifact.
- M2 hai hash và quyết định hiệu lực giữ nguyên; PENDING/frozen=false trong bytes cũ không được sửa để đổi cờ.
- H1 strict-majority vs dev-best single, 4 focal review, metric/guardrails/multiplicity đều đề xuất chờ O1/O2/O5; target phải kín và độc lập, không TRAIN đã lộ hoặc TEST.

## NEXT STEP / BLOCKERS

1. **Dừng ở Draft PR của Issue #148 để ChatGPT trực tiếp kiểm GitHub, 12 candidates, 3 priorities và evidence.** Không merge hoặc Ready for Review tự động.
2. Sau review, cân nhắc independent methodology audit và Owner/giảng viên O1–O8/T0; O3 chốt bounded qualification sequence/attempt cap trước thực nghiệm, final roster sau evidence.
3. G0–G6 theo [runbook](KAGGLE_FAILURES_AND_RELEASE_GATES.md): native CPU/runtime chưa nghiệm thu; G4/G5 cần quyền mới. CPU metadata không vượt behavior gate.
4. Thiếu nguồn/GT/custody/reviewers/precision/quota hoặc không đủ 4 qualified → NO-GO thiết kế xác nhận; giảm scope cần quyết định, không mở model zoo hoặc target thay thế.

## REFERENCES / UPDATE RULES

- [AGENTS](../AGENTS.md), [README](../README.md), [ROADMAP](ROADMAP.md), [ARCHITECTURE](ARCHITECTURE.md); các snapshot premerge phải đối chiếu GitHub live.
- [Thesis plan/O1–O8](research/THESIS_EXECUTION_PLAN_2026.md), [DECISIONS](research/DECISIONS.md), [source gate](SOURCE_FEASIBILITY_GATE_20261024.md), [HISTORY](HISTORY.md).
- Cập nhật trạng thái trong cùng PR task, không PR phụ; giữ file ngắn, không raw/credentials hoặc toàn bộ chat.
- Tách DONE sản phẩm, audit/merge và khoa học/thực nghiệm. Codex không nhận Draft đã merged; ChatGPT xác minh hậu merge.
- Không sửa protocol/labels/split/metric/roster/legacy refs, không chuyển grant cũ; raw-before-parse khi có quyền chạy, derived local ở `data/processed/`, không commit weights/data.
