# SafeShift — PROJECT STATE

Cập nhật **31/10/2026 (Asia/Bangkok)** trong cùng Draft PR #155, theo chỉ thị environment-first.
Main đã kiểm remote: `39ec489403753ada10f4924c4b0d6077e027f5e1`.
Đây là snapshot trạng thái, không quyền thực nghiệm; mở task mới phải kiểm GitHub lại.

## PROJECT IDENTITY

- SafeShift nghiên cứu độ tin cậy của VLM khi phân loại nguy cơ công nghiệp, kiểm tra chéo và ưu tiên người kiểm tra.
- Owner chuyển thẳng sang Khóa luận ngày 27/10; không tự đánh dấu Seminar/M3–M5 hoàn thành hoặc hủy lịch sử.
- [Kế hoạch Khóa luận](research/THESIS_EXECUTION_PLAN_2026.md) đề xuất bốn peers: phân loại độc lập → focal rotation → ensemble và review, hai endpoint cuối tách riêng.
- Thiết kế/primary/metric/final roster/nguồn mới vẫn **PROPOSED; O1–O8/T0 PENDING**. HNLO optional theo từng model, không xác suất nguy cơ hoặc confidence đã hiệu chuẩn.

## CURRENT STATUS

- **Yêu cầu environment-first 31/10 — IMPLEMENTED IN DRAFT / chưa COMPLETE.**
  [Chỉ thị Owner](https://github.com/tantdna2/SafeShift/pull/155#issuecomment-6533181366)
  được ghi append-only trong `AGENTS.md`. Cùng branch/PR155, không PR mới.
  Preflight v2 thêm inventory kernel/ABI/OS/RAM/cgroup/visibility, software
  qualification child riêng, receipt binding/đủ evidence, các mức PASS riêng,
  deadline từ đầu và final result fail-closed khi export/sidecar/cleanup lỗi.
  [Runbook](CANDIDATE160_KAGGLE.md) ghi facts OWNER_REPORTED và cách Owner chạy
  diagnostic với cùng Inputs/settings; còn thiếu bằng chứng Kaggle thực tế.
  Không đổi khoa học/model revision/metric/cohort hoặc cơ chế chống retry.
  Chưa chạy Kaggle/GPU/weights/private data/attempt hoặc merge ở Codex.
  Chỉ COMPLETE khi final HEAD được ChatGPT kiểm GitHub, Antigravity audit độc
  lập, merge được cấp quyền riêng và hậu merge xác minh quy tắc trên main.
  Các kiểm thử/bằng chứng30/10 bên dưới là snapshot cũ, không tự nâng HEAD mới.
  **CPU CODE PASS31/10:** runtime `f679e3153a1418cd521d1875cfa797b5aded8570`,
  tested snapshot `0363db4976f39f8c4249ab84a7c54986f41e1e99`;
  full Linux332 =300 PASS/32 SKIP/0 lỗi,10 notebook khớp builder;
  Windows focused43 =38 PASS/5 SKIP/0 lỗi. Hai actual worker CLI đều qua
  exact3.11.9/cu124 pins/NMS ABI/source-bound envelope +8 synthetic sizes,
  có guards cấm CUDA/weights/real-forward. Source/hash lịch sử được đối chiếu
  bằng Git objects; không sửa locks. [Receipts mới](research/evidence/candidate160_envfirst_20261031/index.json).
  LIVE_GPU_PREFLIGHT/WEIGHTS_LOADED/INFERENCE/SCIENTIFIC vẫn chưa được chứng minh
  trên Kaggle. Final HEAD mới phải được review/audit lại, không tự merge.

- **Snapshot bàn giao30/10 Candidate160 environment repair — DRAFT / chưa GPU PASS.**
  Thêm bounded Notebook Output discovery riêng cho Candidate160; giữ pilot cũ.
  CPython3.11.9 standalone20240726 đã tải/kiểm29.713.170 bytes/SHA upstream;
  venv copies cần libpython cùng SHA trong venv/lib. Preflight notebook riêng
  không execution/slot/attempt/weights/model call; receipt từng gate không suy READY.
  Ngoại lệ một replacement1 chỉ cho sealed incident InternVL checkpoint_source
  FOUND_0 có160 NOT_ATTEMPTED/attempts0/native_calls0 và consumed=false; giữ
  campaign/slot/marker cũ, chặn partial/consumed/unknown và lần thay thế thứ hai.
  [Quyết định/giới hạn](research/CANDIDATE160_KAGGLE_ENV_DECISION_20261030.md),
  [runbook](CANDIDATE160_KAGGLE.md). Bằng chứng Kaggle cũ chỉ OWNER_REPORTED;
  chưa có original private archive để xác nhận đủ điều kiện replacement.
  ChatGPT kiểm GitHub và Antigravity audit độc lập vẫn bắt buộc trước merge.
  Không GPU/private TRAIN/GT/TEST/weights hoặc merge trong task này.
  **CPU CODE PASS:** exact export `2306aecb280acfedd1dd11523f14b60f892c771f`,
  324 tests =292 PASS/32 SKIP/0 lỗi;10 notebook khớp builder. Windows focused
  13 tests =9 PASS/4 symlink SKIP;4 notebook tests PASS. Cả hai production
  CPython3.11.9/cu124 stacks qua exact pins/ABI/native meta +8 synthetic sizes.
  Native exact-export suite15/15 PASS/model, gồm160 ảnh tổng hợp/model qua
  production cu124 software với scripted logits; không model predictions thật.
  [Receipts](research/evidence/candidate160_env_20261030/index.json) và runbook
  ghi BASE-reproduced stale AGENTS assertion, correction và các giới hạn thật.

- **PR #153 MERGED**, GitHub `merged=true`, merge `fc1e454212455685e1775601ebfd6aab9535c932`.
  Owner đã trực tiếp yêu cầu bỏ thủ tục phê duyệt lặp lại cho một lượt/model
  InternVL3.5/MiniCPM-V-4, ≤160 TRAIN, dùng bundle/checkpoint Owner đã upload.
  [Record chỉ thị và phạm vi](research/CANDIDATE160_OWNER_DECISION_20261030.md),
  [runbook mới](CANDIDATE160_KAGGLE.md), [CPU acceptance](research/CANDIDATE160_OWNER_CPU_20261030.md).
  Hai notebook dùng Save & Run All làm kích hoạt, tự sinh run/attempt/slot và
  consumption log; không grant/reservation/CONTINUE thủ công hoặc approval ref giả.
  Cần ChatGPT kiểm GitHub và audit độc lập trước merge Draft PR này; task chỉ
  synthetic CPU, không GPU, real weights hoặc private TRAIN/GT/TEST.

  Technical errors/NaN/Inf/raw/custody/resources/time vẫn dừng; behavior và GT
  support chỉ ghi để review sau run vì chưa quyết định scientific thresholds.
  Đây là thay đổi chính sách dừng công khai trong PR, không silent approval.
  Giữ parser/HNLO/C1/model/checkpoint/cohort/order và mọi giới hạn160/no-retry/
  no-resume/no-overwrite. Không mở quyền bên thứ ba/TEST/FULL TRAIN/khác scope.
  Khóa fixed slot chống duplicate trong cùng output root và attached Outputs
  chuẩn; không distributed/global exactly-once cho VM mới thiếu lịch sử.
  Actual Kaggle Python/CUDA/T4/VRAM/weights/behavior/HNLO vẫn UNVERIFIED.
  **CPU CODE PASS:** exact-export310 tests =273 PASS/37 SKIP,0 failures/errors;
  native Windows67 tests/model =64 PASS/3 symlink SKIP,15/15 native PASS gồm
  đúng160 ảnh tổng hợp/model qua Owner path. Linux3/3 activation/scope/atomic
  slot PASS. [Receipts/checksum index](research/evidence/candidate160_owner_20261030/index.json).
  Tested snapshot `f427e59c90f15c5bb87db26ff1aad5e038310af8`; runtime
  `93bc2f110822c3cfd3c910da8f8adb11a0d9ac1f`; sau đó chỉ docs/receipts.

- **PR #152 MERGED**, GitHub `merged=true`, merge `f79f7bddeac62e8fb8378d6798c25387f45f0f37`.
  Gói batch #153 lịch sử **CODE PASS / execution BLOCKED** theo cơ chế cũ.
  [CPU report/receipts](research/CANDIDATE160_BATCH_CPU_20261030.md); quyền batch
  chưa duyệt, real weights/GPU/runtime/behavior UNVERIFIED.

- **PR #151 MERGED**, GitHub `merged=true`, merge `95eb4e8801ea746e1a760b9d529920bffb3c26cb`, xác minh live trong task này. Adapter CPU READY trong phạm vi #151; không cấp GPU/data/grant hoặc scientific qualification.

- **PR #150 MERGED**, merge `bbbd351e19e404f1108413578c7ed024f92e814d`, xác minh GitHub `merged=true` và origin/main trước task này. Findings CPU của #150 là baseline lịch sử; không phải kết luận về adapter mới bên dưới.

- **PR #137 MERGED**, merge `1488dcb5212164e2946a15055d1da6e8be9096d2`; [ChatGPT hậu merge PASS](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6488172066). Hoàn tất phạm vi repository/technical của #137, không scientific approval hoặc GPU readiness.
- **PR #149 MERGED**, merge `6342b15b0d70c27b28f4bcb5e53f04f6951d6171`. Shortlist report hoàn tất phạm vi tài liệu; CPU G2/G3 mới có kết quả riêng bên dưới, không scientific approval/qualification.
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

## MERGED #151 — HAI CANDIDATE, TÍCH HỢP CPU TRƯỚC KAGGLE

- **CPU READY trong phạm vi phần mềm đã kiểm thử; GPU release BLOCKED.** [Báo cáo/tái lập](research/CANDIDATE_INTEGRATION_CPU_20261029.md), [receipts](research/evidence/candidate_integration_20261029/index.json), code commit `65640ddf91bd0ce75e594c372af098ecb59194eb`, nhánh `implement/candidate-integration-20261029`, từ main sau #150. PR #151 đã merge ở SHA phía trên; các receipts dưới đây là snapshot CPU của #151, không bằng chứng GPU hoặc scientific approval.
- `safeshift/candidates/` cung cấp hai adapter với source public đúng revision, native loader/processor, C1/generation cố định, explicit eager, raw IDs trước decode và bounded raw logits. Tái dùng runner/Store/parser/replay/archive qua tests; không ghi candidate vào registry/grants của pilot cũ.
- **InternVL3.5 HF:** `OpenGVLab/InternVL3_5-4B-HF` @ `6bd4487402110ef9889ba50eb7aefeb302526fed`; native HF 4.55.4, image ID151671/256 tokens/view; 36+24 attention layers và 841 tensor keys qua native key conversion. Prefix phải khớp trước lấy continuation.
- **MiniCPM-V-4:** `openbmb/MiniCPM-V-4` @ `6f69a8235885be89608f3a71ffd40695b379e1e7`; native 4.51.3,32+27 layers/741 tensor keys. Sửa ambiguity RGB1×1 bằng trục HWC tường minh, giữ native resize/slices/normalize; dùng `generate(decode_text=False)` giữ generation contract/logits, continuation-only và hai EOS native. Native chat lỗi vẫn được tái lập, không dùng nó để classify.
- Kiểm native tensor/image plumbing với scripted towers, image bounds/shape/dtype/context, exact spatial parity, bốn nhãn/whitespace/INVALID/EOS/max64, lỗi load/decode/ENOSPC và raw-before-parse/tail/archive. Loader meta và file safetensors rỗng chỉ chứng minh phần mềm/cấu hình, không deserialization weights thật.
- Snapshot guard #150 giữ exact flat allowlist/no aliases; bổ sung kiểm dedicated remote cache trước import, implementation/version lock, checkpoint index/LFS metadata lock, protected science/source lock và verifier cho receipts. Không đổi public source lock13/15 file, CPU requirements hoặc C1.
- Mỗi model **Windows65=62 PASS+3 symlink SKIP**, **Linux65=64 PASS+1 Windows-junction SKIP**, không failure/error. Cả13 native tests PASS trên từng stack/OS. Full exact-export suite **Windows266=231 PASS+35 SKIP**, **Linux266=236 PASS+30 SKIP**; sáu notebook byte/builder/compile PASS, không execute cells. Skip details/phạm vi trong receipts; không nâng Phi/Smol native chưa rerun thành PASS. Bằng chứng do Codex thực chạy, không CI hoặc independent audit.
- Giữ pilot source digest `1d76c3a4e5cf9c5fe32d6fd94b846a2879eca268a6023ce34203794dc801d884`; sáu notebooks không sửa. Không chạy notebook, weights, inference/GPU/CUDA/Kaggle, private TRAIN/TEST/GT/archive, không cấp grant, chọn model thứ tư hoặc đổi giao thức để đạt PASS.
- **GPU release BLOCKED**: cần ChatGPT review, G0/G1 đăng ký execution release/source/runtime/grant mới; G4 Linux/CUDA isolated-child/device/memory và G5 finite first image/quality/utility/HNLO bằng quyền riêng. O1–O8/T0/O3 PENDING, peer slot3 VACANT,0 candidates qualified.
- [CPU G2/G3 lịch sử #150](research/CPU_G2_G3_CANDIDATES_20261029.md) và receipts cũ giữ nguyên: MiniCPM native1×1/chat FAIL và InternVL tổng thể BLOCKED ở code cũ. Kết quả adapter mới không sửa hồi tố findings hay reviewer status của #150.

## MERGED #152 — HAI NOTEBOOK CANDIDATE160 PREP

- **PR #152 MERGED**, merge `f79f7bddeac62e8fb8378d6798c25387f45f0f37`,
  [GitHub](https://github.com/tantdna2/SafeShift/pull/152), verified30/10/2026.
  Các bullet bên dưới là bằng chứng CPU và giới hạn tại #152; trạng thái chờ merge
  trong snapshot cũ đã được thay bởi mục này. Không chuyển grants sang source mới.

- Task Owner mới: chuẩn bị tối đa160 ảnh/model, không dataset/weights/GPU/Kaggle execution. Nhánh/worktree riêng từ đúng SHA sau #151; dừng ở **một Draft PR**.
- [Runbook](CANDIDATE160_KAGGLE.md), [biên bản CPU](research/CANDIDATE160_CPU_20261029.md); hai notebook riêng [InternVL](../notebooks/SafeShift_CANDIDATE160_internvl35.ipynb) và [MiniCPM](../notebooks/SafeShift_CANDIDATE160_minicpm4.ipynb), builder tái lập và source/ref/config pins.
- Cùng manifest lịch sử SHA `f1ec6a202c3bba05d91cb3c507d5aa16d9aa3ded2418fa84bd62e77c05522995`, đúng160 ID/order và quota80/48/24/8 theo receipt metadata công khai #138. Không mở private manifest/ảnh/TEST, không selector hoặc supplement; actual bundle bytes chưa được reverify trong task này.
- Tái dùng adapter #151, runner execute/Store/parser/HNLO/metrics/archive; giữ nguyên source runtime/pilot và sáu notebook cũ. First-image/early behavior nằm trong160, review gắn hash checkpoint; thiếu quyết định dừng/NOT_ATTEMPTED tail, no retry/resume/overwrite.
- `configs/candidate160/preparation.json` giữ grant=null, G0/T0/O3/runtime/driver/stop thresholds/mốc review PENDING. Không tự lấy numerical thresholds hoặc grants Phi/Smol/Gemma. CUDA tuple mới là PREP cần review; không claims VRAM fit hoặc quality/HNLO PASS.
- [Review ChatGPT #152](https://github.com/tantdna2/SafeShift/pull/152#issuecomment-6501983735) yêu cầu sửa metadata Phi kế thừa và provenance hai hash tại HEAD `65da8a3…`. Cùng PR đã sửa config/grant v2: tách legacy transport snapshot khỏi effective candidate; `legacy_transport_config_sha256` khác `candidate_execution_config_sha256`, đối soát raw trước parse và recovery, không đổi pilot/adapter/science/stop policy.
- Runtime #152 `820200bba7c6f5796961acb64befef0c651772b3`, notebook/release commit `c75113f4a62d8d30303269f4a8bd72fc71040c15`, source SHA `3b63d9cf92df66042cbd201861c50ab8f0cfd0b4d1a57d194493faf33c24524e`. Snapshot CPU mỗi model Windows64=61 PASS+3 SKIP, Linux64=63 PASS+1 SKIP; cả15 native tests PASS/model/OS, gồm160 scripted calls kiểm hai hash/request. Full exact-export Windows293=256 PASS+37 SKIP, Linux293=261 PASS+32 SKIP, không FAIL/ERROR; tám notebook kiểm PASS, candidate cells không grant CPU vẫn BLOCKED. Actual weights/CUDA/GPU/behavior **UNVERIFIED**; merge không nâng các bằng chứng này.
- External ledger snapshot không là chữ ký số/distributed one-shot enforcement; fresh reservation/current ledger và phương thức giao review vào saved VM cần review/approval riêng. Không vì code CPU PASS mà tự mở release.

## ACTIVE WORK — GÓI BATCH CANDIDATE160 SAU #152 (30/10/2026)

- Một nhánh/Draft PR từ đúng main `f79f7bd…`; hoàn thiện cả notebook, runtime,
  authority worksheets/checker, tests và handoff trong cùng phạm vi. Không Kaggle,
  GPU, tải weights hoặc truy cập private TRAIN/TEST trong task này.
- [Batch authority PROPOSED](research/CANDIDATE160_BATCH_DECISION_20261030.md):
  máy chỉ AUTO_CONTINUE khi Lead cho phép rõ đúng policy/execution binding và
  mọi điều kiện đạt. Missing approval chặn trước call; EXTERNAL review giữ được.
  Không giả CONTINUE, không tự duyệt chính sách khoa học hoặc numerical limits.
- Child CUDA FP16 preledger rồi kiểm lại trong worker; Linux NVIDIA/Triton pins
  đầy đủ từ official wheel metadata; RAM/cgroup/disk/GPU0 runtime headroom theo
  policy. Không đổi adapter/source/checkpoint locks #151, C1/parser/HNLO/generation,
  manifest/order160 hoặc sáu notebook cũ. Model/real weights/T4 fit còn UNVERIFIED.
- [Runbook và checklist duy nhất](CANDIDATE160_KAGGLE.md#checklist-bàn-giao-duy-nhất)
  nêu từng quyền, threshold/mốc/driver/resource limits, grants/reservations/Inputs
  thật còn thiếu. `preparation.json` giữ null/BLOCKED, không EXPERIMENT READY.
- [Nghiệm thu CPU mới](research/CANDIDATE160_BATCH_CPU_20261030.md): mỗi model
  Windows73=70 PASS+3 SKIP, Linux73=72 PASS+1 SKIP; cả15 native tests PASS/model/OS,
  gồm160 synthetic images qua native processor/generation và batch. Full immutable
  export Windows302=265 PASS+37 SKIP, Linux302=270 PASS+32 SKIP, không FAIL/ERROR.
  SKIP không tính PASS; tám notebook/source/builder/cells/archives kiểm PASS.
  Source `5189a456b62e5dbef631b712eb0b377044bc84066d6ffd190976e3ee26901e1d`,
  runtime `04090aeb182883da25726a12cbd6371d3d6c9913`. Không dùng receipts #152
  chứng nhận source mới. Dừng ở Draft PR cho ChatGPT kiểm exact HEAD và quyết
  định audit/merge; chưa independent audit, quyền thực nghiệm hoặc EXPERIMENT READY.

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

1. **ChatGPT review đúng một Draft PR batch160 mới sau #152 MERGED**: exact HEAD/diff/source/notebooks/receipts và CPU scope; không dùng CPU hoặc review adapter thay G0/G1/G4/G5 mới.
2. Sau review, cân nhắc independent methodology audit và Owner/giảng viên O1–O8/T0; O3 chốt bounded qualification sequence/attempt cap trước thực nghiệm, final roster sau evidence.
3. G0–G6 theo [runbook](KAGGLE_FAILURES_AND_RELEASE_GATES.md): CPU chỉ đúng phạm vi có receipt; real weights/CUDA, execution release và behavior/HNLO vẫn BLOCKED/NOT_RUN. G4/G5 cần quyền mới; CPU không vượt behavior gate.
4. Thiếu nguồn/GT/custody/reviewers/precision/quota hoặc không đủ 4 qualified → NO-GO thiết kế xác nhận; giảm scope cần quyết định, không mở model zoo hoặc target thay thế.

## REFERENCES / UPDATE RULES

- [AGENTS](../AGENTS.md), [README](../README.md), [ROADMAP](ROADMAP.md), [ARCHITECTURE](ARCHITECTURE.md); các snapshot premerge phải đối chiếu GitHub live.
- [Thesis plan/O1–O8](research/THESIS_EXECUTION_PLAN_2026.md), [DECISIONS](research/DECISIONS.md), [source gate](SOURCE_FEASIBILITY_GATE_20261024.md), [HISTORY](HISTORY.md).
- Cập nhật trạng thái trong cùng PR task, không PR phụ; giữ file ngắn, không raw/credentials hoặc toàn bộ chat.
- Tách DONE sản phẩm, audit/merge và khoa học/thực nghiệm. Codex không nhận Draft đã merged; ChatGPT xác minh hậu merge.
- Không sửa protocol/labels/split/metric/roster/legacy refs, không chuyển grant cũ; raw-before-parse khi có quyền chạy, derived local ở `data/processed/`, không commit weights/data.
