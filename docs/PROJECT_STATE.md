# SafeShift — PROJECT STATE

Cập nhật **29/10/2026 (Asia/Bangkok)** trong task CPU G2/G3 sau PR #149.
Main đã kiểm GitHub/fetch/ls-remote: `6342b15b0d70c27b28f4bcb5e53f04f6951d6171`.
Đây là snapshot trạng thái, không quyền thực nghiệm; mở task mới phải kiểm GitHub lại.

## PROJECT IDENTITY

- SafeShift nghiên cứu độ tin cậy của VLM khi phân loại nguy cơ công nghiệp, kiểm tra chéo và ưu tiên người kiểm tra.
- Owner chuyển thẳng sang Khóa luận ngày 27/10; không tự đánh dấu Seminar/M3–M5 hoàn thành hoặc hủy lịch sử.
- [Kế hoạch Khóa luận](research/THESIS_EXECUTION_PLAN_2026.md) đề xuất bốn peers: phân loại độc lập → focal rotation → ensemble và review, hai endpoint cuối tách riêng.
- Thiết kế/primary/metric/final roster/nguồn mới vẫn **PROPOSED; O1–O8/T0 PENDING**. HNLO optional theo từng model, không xác suất nguy cơ hoặc confidence đã hiệu chuẩn.

## CURRENT STATUS

- **PR #137 MERGED**, merge `1488dcb5212164e2946a15055d1da6e8be9096d2`; [ChatGPT hậu merge PASS](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6488172066). Hoàn tất phạm vi repository/technical của #137, không scientific approval hoặc GPU readiness.
- **PR #149 MERGED**, merge là main đã xác minh ở trên. Shortlist report hoàn tất phạm vi tài liệu; CPU G2/G3 mới có kết quả riêng bên dưới, không scientific approval/qualification.
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
- **Gemma BLOCKED_SOURCE_TOKENIZER_AUDIT_INCOMPLETE:** 10 config/tokenizer 401 ở audit cũ. #148 kiểm anonymous 7 metadata requests cũng 401; không phải GPU failure, không tự tạo lock/grant.
- `OWNER_SELECTED_CANDIDATES` Gemma/Phi/Smol ngày 27/10 là sự kiện lịch sử, chưa qualified ba peers. Không cứu parser/C1/HNLO surfaces hoặc tiêu attempt tiếp.

## TUYỂN CHỌN #148/#149 — SNAPSHOT PHẠM VI LỊCH SỬ

- Báo cáo [THESIS_VLM_CANDIDATE_SCREENING_20261029](research/THESIS_VLM_CANDIDATE_SCREENING_20261029.md) đã **[MERGED PR #149](https://github.com/tantdna2/SafeShift/pull/149)**, gồm bổ sung R3. Các bullet dưới đây ghi checks/quyền của task docs-only #148/#149, không nhận là native CPU status mới. [Review R1/R2](https://github.com/tantdna2/SafeShift/pull/149#issuecomment-6489345290) giữ phạm vi lịch sử; merge không tự qualified model.
- Đã đọc InspecSafe arXiv v2, publisher, Figure 6, Table 3, S2/S3 và repo tác giả pinned; phân biệt paper benchmark với strict C1 JSON và TRAIN lịch sử.
- Giữ longlist **12 ứng viên gốc**, bổ sung so sánh C01-HF và truy nguồn custom không hậu tố. Ưu tiên nghiên cứu mới: **(1) `OpenGVLab/InternVL3_5-4B-HF` @ `6bd4487402110ef9889ba50eb7aefeb302526fed`, (2) `openbmb/MiniCPM-V-4` @ `6f69a8235885be89608f3a71ffd40695b379e1e7`; vị trí 3 VACANT**.
- R1: native HF giảm remote loader/manual preprocessing/hidden decode cleanup, nhưng khác training stage với `-Instruct`; tensor/inference parity **UNVERIFIED**. CPU qualification tương lai ưu tiên source Transformers 4.55.4; không sửa lock hoặc chạy native trong lần này.
- R2: LLaVA lợi hơn Idefics3/Llama3 về FP16/parameter/KV; Idefics3 là comparator non-Qwen chính, có câu hỏi license/instruction và BF16→FP16. Cả hai cần sharding hai T4 chưa kiểm; chưa có paired hazard/shared-error evidence để chốt slot 3. Không coi khác backbone là lỗi độc lập.
- R3: InternVL3-2B-hf lịch sử đúng **164/3.763 (4,36%)**, **3.014/3.014 Normal→Anomaly**; HNLO **0,8861824613751756** là saved-score, không raw-logit PASS. CUDA SONAME lookup thất bại ở child worker, cuInit chưa gọi; không suy driver cũ hoặc bản 3.5 đã sửa. Hai bản đều native HF, ba processor/template files trùng hash; image token 151667→151671 khác.
- Giữ InternVL #1 **chỉ qualification CPU đọc nguồn/không weights**, MiniCPM #2; prior behavioral risk lớn, chưa có bằng chứng chất lượng hơn MiniCPM. **Thứ tự Kaggle PENDING O3**, không kế thừa thứ tự CPU. G2 đúng token/template/raw, G4 actual isolated-child CUDA loader, G5 GT Normal/hazard đa miền + strict C1/repetition/early stop phải được duyệt trước 160/full; thresholds/GT/grants còn PENDING.
- R3 thực kiểm: sáu public metadata/template files 2B đúng revision, HTTP200/hash khớp audit, năm JSON; ba hash chung và arithmetic aggregate được đối chiếu, không raw/GT/HNLO recomputation. R1/R2 không nghiên cứu lại.
- QA R3: 20 bảng, 21 relative links/reference definitions, sáu source links mới HTTP200; scope đúng hai docs và nội dung R1/R2 giữ nguyên. C1/protected files không đổi; checks do Codex chạy, không independent audit/CI.
- **0 ứng viên mới qualified**; classification thật/peer utility/HNLO của shortlist **UNVERIFIED**, quyền execution **BLOCKED**. Không sửa official roster hoặc tự thay Qwen3.
- CPU nhẹ ở bản trước review, **Codex-reported, không independent/CI**: 13 Hub records; 114 source/config/card files + 9 tokenizer files đọc/hash; 123 hash checks, 69 JSON parses, 27 AST parses; 5 MiniCPM config cross-checks, token-ID checks và 2 text-stage Jinja/C1 checks. Đây không native processor/tokenizer/model PASS.
- Bổ sung R1/R2 thực chạy inline: 17 pinned source hashes/HTTP200, 6 HF JSON, 8 Python AST không import; HF text-stage Jinja/C1/image-token consistency PASS. Có bảng hash/link công khai; native processor/tokenizer/model **NOT_RUN**, không independent audit. Không tạo script mới.
- QA R1/R2: 19 bảng, 21 relative links, 19 source links HTTP200; kiểm lại identity/revision/hash lịch sử và KV arithmetic PASS. C1/protected files không đổi; chỉ hai tài liệu trong diff.
- Không cài Torch/Transformers, tải weights, inference/GPU/Kaggle/TEST/private artifacts, tạo grant/notebook hoặc sửa khoa học. Chỉ 2 file tài liệu trong PR; BASE/HEAD/validation nằm trong PR body và bàn giao.
- Ranking là ưu tiên kiểm chứng theo nguồn, không accuracy đã đo. T4×2 không pooled 32 GB; FP16/attention/tiles/native wrapper và per-GPU memory còn phải G2/G4/G5.
- Báo cáo so A cũ fixed-Q3+auxiliary với B peers hiện proposed; tách classifier, cross-check, fusion/review và HNLO optional; không đặt numerical thresholds hoặc phê duyệt ensemble rule.

## ACTIVE WORK — CPU G2/G3, PUBLIC/SYNTHETIC, KHÔNG WEIGHTS

- [Báo cáo và tái lập](research/CPU_G2_G3_CANDIDATES_20261029.md), [receipts công khai nhỏ](research/evidence/cpu_g2_g3_20261029/index.json): bản sửa guard thực chạy `15c0e72993ebe44912c0b1858bc42fc28bc31315`, Codex-reported, cùng session/nhánh Draft PR #150. [ChatGPT CHANGES REQUESTED](https://github.com/tantdna2/SafeShift/pull/150#issuecomment-6492535296) tại HEAD cũ `f7318a3851c040808c140e0aab2f4c50c37bab0e`; bản sửa chờ review lại rồi independent security/technical audit, không tự nhận PASS.
- Guard mới liệt kê mọi snapshot entry, `lstat` root/files, từ chối directory/symlink/hard link/Windows reparse-junction. Không resolve root alias; bỏ recursive copytree, chỉ copy locked names không follow symlinks rồi kiểm lại source/đích trước import. Focused **18=15 PASS+3 SKIP**; root/child junction thật Windows PASS,3 real-symlink tests SKIP vì thiếu quyền OS. Lock13/15 file giữ nguyên, không tự tải nguồn phụ.
- Hai venv CPython3.11.9 Windows, Torch2.6.0+cpu/torchvision0.21.0+cpu; InternVL Transformers4.55.4 và MiniCPM4.51.3. Pins/transitives, pip check, compiled CPU ABI và actual AutoProcessor/AutoTokenizer/AutoConfig/class import **PASS**. Không constructor/weights/model loader.
- **InternVL3_5-4B-HF @ `6bd4487402110ef9889ba50eb7aefeb302526fed`: các checks CPU khả thi PASS; tổng thể BLOCKED.** Native tiling 1–13 views, image ID151671,256 tokens/view, RGB/6 sizes/PNG-RGBA→RGB, C1 byte/expanded-input và GenerationConfig construction PASS. Actual generate/weight loader/attention/GPU chưa kiểm.
- **MiniCPM-V-4 @ `6f69a8235885be89608f3a71ffd40695b379e1e7`: FAIL CPU processor/wrapper; các phần cần weights/GPU BLOCKED.** RGB1×1 gây ValueError normalization;5 sizes khác + PNG-RGBA→RGB PASS,1–10 views gồm global,64 tokens/view. Native `chat` mặc định beam3/repetition1.2; frozen kwargs chỉ giữ beam1/max64, lọc các flags khác, buộc decode text. Không sửa upstream/input policy/generation/raw API để cứu PASS.
- Mỗi stack:15 mock-ID cases qua tokenizer/Store/parser/diagnostics và5 native corrupted-input checks PASS; G3+snapshot suite **45=42 PASS+3 SKIP,0 failure/error**. Full repo **246=224 PASS+22 SKIP,0 failures/errors**; skipped15 Phi/Smol native,1 network bootstrap,3 Linux FS/allocation và3 real-symlink tests thiếu quyền OS, không gọi là PASS. MiniCPM1×1/wrapper FAIL và InternVL tổng thể BLOCKED được tái lập trên code mới; không model predictions/behavior/HNLO validation.
- Model `from_pretrained` thật/effective attention, actual continuation/raw custody/logits/HNLO, FP16/VRAM/industrial C1 quality và isolated-child driver **BLOCKED**. Windows CPU không chứng nhận Linux/CUDA tuple. Cần adapter/release review, khép MiniCPM findings, G0–G4/quyền mới và G5 panel Normal/hazard/multidomain/early stops đã duyệt trước GPU.
- Tái dùng source downloader, parser/raw writer/runner fault tests; không pipeline/production backend mới. Pilot source digest giữ `1d76c3a4e5cf9c5fe32d6fd94b846a2879eca268a6023ce34203794dc801d884`; C1/protocol/M2/labels/metrics/roster/grants/notebooks không đổi. Không weights/inference/GPU/Kaggle/private TRAIN/TEST/GT/archive. **0 candidates qualified; GPU order PENDING O3; peer slot3 VACANT.**
- Dừng tại Draft PR CPU để ChatGPT review GitHub trực tiếp; không Ready/merge hoặc tự cấp quyền tiếp theo.

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

1. **ChatGPT review lại source guard/staging và receipts mới trong Draft PR #150**, rồi handoff independent security/technical audit theo review. MiniCPM1×1/generation/raw FAIL và các mục BLOCKED giữ nguyên. #149 đã merge; hai ưu tiên nghiên cứu/slot3 trống giữ nguyên, chưa qualified. Không merge hoặc Ready for Review tự động.
2. Sau review, cân nhắc independent methodology audit và Owner/giảng viên O1–O8/T0; O3 chốt bounded qualification sequence/attempt cap trước thực nghiệm, final roster sau evidence.
3. G0–G6 theo [runbook](KAGGLE_FAILURES_AND_RELEASE_GATES.md): CPU kết quả chỉ đúng phạm vi ở trên, real weight loader/Linux/CUDA/production adapters còn BLOCKED; MiniCPM có FAIL cần review. G4/G5 cần quyền mới; CPU không vượt behavior gate.
4. Thiếu nguồn/GT/custody/reviewers/precision/quota hoặc không đủ 4 qualified → NO-GO thiết kế xác nhận; giảm scope cần quyết định, không mở model zoo hoặc target thay thế.

## REFERENCES / UPDATE RULES

- [AGENTS](../AGENTS.md), [README](../README.md), [ROADMAP](ROADMAP.md), [ARCHITECTURE](ARCHITECTURE.md); các snapshot premerge phải đối chiếu GitHub live.
- [Thesis plan/O1–O8](research/THESIS_EXECUTION_PLAN_2026.md), [DECISIONS](research/DECISIONS.md), [source gate](SOURCE_FEASIBILITY_GATE_20261024.md), [HISTORY](HISTORY.md).
- Cập nhật trạng thái trong cùng PR task, không PR phụ; giữ file ngắn, không raw/credentials hoặc toàn bộ chat.
- Tách DONE sản phẩm, audit/merge và khoa học/thực nghiệm. Codex không nhận Draft đã merged; ChatGPT xác minh hậu merge.
- Không sửa protocol/labels/split/metric/roster/legacy refs, không chuyển grant cũ; raw-before-parse khi có quyền chạy, derived local ở `data/processed/`, không commit weights/data.
