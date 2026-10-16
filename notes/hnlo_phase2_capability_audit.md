# Giai đoạn 2 — kiểm tra khả năng HNLO của ba mô hình còn lại

- Ngày audit: 2026-10-16 (Asia/Bangkok)
- Base đã fetch từ `origin/main`: `6ad857eac448db88f5513993ec32144e3c5a64c3`

Phạm vi: source/config/tài liệu và kiểm tra hash CPU; **không inference mới,
không GPU, không tải weights, không đọc TEST/annotation**.

## Kết luận ngắn

- **Qwen3-VL-8B-Instruct — PLAUSIBLE, NOT VERIFIED:** giao diện HF có đường
  `generate`, nhưng runner hiện tại chỉ lưu token/text; chưa có T1 tokenizer hay
  raw-logit trace tại nhánh bốn nhãn.
- **InternVL3-2B-hf — PLAUSIBLE, NOT VERIFIED:** repository đã có scorer LS1
  thử nghiệm yêu cầu `output_logits=True` và tách raw logits khỏi processed scores,
  nhưng T1 thực tế và artifact GPU tương ứng chưa được kiểm toán trong hồ sơ hiện hành.
- **Moondream2 — BLOCKED trên giao diện native hiện hành; đường instrument
  PLAUSIBLE, NOT VERIFIED:** `query()` chỉ trả `answer`. Source đã pin có logits
  nội bộ trước argmax, nhưng runner không thu chúng và tokenizer mapping chưa được chứng minh.

Không mô hình nào trong ba mô hình được phân loại **VERIFIED HNLO**. Kết luận này
phù hợp với [DEC-PA3-011](../DECISIONS.md#dec-pa3-011--proposed-seminar-internal-hazard-score-direction-2026-10-16):
đề xuất vẫn PENDING và Qwen2.5 là mô hình duy nhất có kết quả tương thích đã audit.

## Cách dùng trạng thái

- **VERIFIED:** bằng chứng trực tiếp cho đúng revision/giao diện hoặc artifact đã audit.
- **PLAUSIBLE:** source/code cho thấy có đường thực hiện hợp lý, nhưng còn thiếu
  T1, raw trace hoặc GPU validation.
- **BLOCKED:** giao diện hiện tại không cung cấp đầu vào cần thiết nếu chưa có
  implementation/approval mới.
- **NOT VERIFIED:** chưa có bằng chứng đủ; không đồng nghĩa với bất khả thi.

HNLO chỉ tương đương khi bốn giá trị là raw logits tại **cùng một bước quyết định**,
trước softmax và trước logits processor:
`logsumexp(z_Level01,z_Level02,z_Level03) - z_Level04`. Phải chứng minh toàn bộ
response hợp lệ chỉ rẽ nhánh tại đúng một token với bốn token ID khác nhau. Xác
suất textual, processed scores hoặc likelihood của bốn chuỗi nhiều token không tự
động tương đương. Đây là cùng ràng buộc mà [scorer Qwen2.5 đã audit](../safeshift/pa3/native/native_score.py#L18-L48)
và [T1/branch proof](../safeshift/ls1/core.py#L36-L76) đang áp dụng.

## Bảng so sánh

| Mô hình | Revision và giao diện thực tế | Raw logits đúng bước quyết định | Mapping Level01–04 | HNLO tương đương | Kaggle T4 / blocker chính |
| --- | --- | --- | --- | --- | --- |
| Qwen3-VL-8B-Instruct | **VERIFIED** `Qwen/Qwen3-VL-8B-Instruct@0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`; `Qwen3VLForConditionalGeneration` + `AutoProcessor.apply_chat_template` + `model.generate` ([runner](../safeshift/runners/qwen3_vl.py#L126-L294)). | **NOT VERIFIED.** Runner gọi `generate()` nhưng không yêu cầu/serialize `output.logits`; envelope chỉ có IDs và text ([capture hiện tại](../safeshift/runners/qwen3_vl.py#L278-L344)). `return_dict_in_generate/output_logits/output_scores` là đường đề xuất, chưa chạy cho revision này. | `Level01→?`, `Level02→?`, `Level03→?`, `Level04→?` — **NOT VERIFIED**. Không được mượn IDs `16–19` của Qwen2.5. | **PLAUSIBLE, NOT VERIFIED** nếu T1 chứng minh nhánh một token và raw/processed alignment trên response C1 thực. | Runtime classification đã có bằng chứng **2×T4**; production từng OOM với pure-GPU placement. Runtime hiện dùng CPU cho riêng embedding, 21/15 lớp trên GPU0/GPU1, visual + head trên GPU1 ([runbook](w2_d9r26_qwen3_p2_runbook.md#exact-source-and-condition), [amendment](../configs/pre_freeze/qwen3_runtime_placement_amendment.v1.json)). Logit capture và memory overhead chưa được đo. |
| InternVL3-2B-hf | **VERIFIED** `OpenGVLab/InternVL3-2B-hf@cb57a075cb75a2e6d1b668b128d48bb00ae321d2`; `InternVLForConditionalGeneration`, processor dynamic tiles 448 px, rồi `model.generate` ([runner](../safeshift/runners/internvl3.py#L321-L388)). | **PLAUSIBLE.** Scorer LS1 riêng đã implement `return_dict_in_generate=True`, `output_logits=True`, `output_scores=True` và giữ hai loại điểm riêng ([code](../safeshift/ls1/runtime.py#L69-L186)); production runner vẫn đặt cả hai `false`. Chưa có raw artifact GPU được audit cho HNLO. | `Level01→?`, `Level02→?`, `Level03→?`, `Level04→?` — **NOT VERIFIED**. T1 hỗ trợ model này nhưng committed validation ghi **BLOCKED/SKIP**, không phải PASS ([T1](../safeshift/ls1/tokenizer.py#L11-L99), [validation](ls1_validation.md#readiness-and-unresolved-evidence)). | **PLAUSIBLE, NOT VERIFIED.** Về toán học là cùng HNLO nếu T1/trace PASS. Về ngữ nghĩa còn phải khóa parser/wrapper: InternVL từng sinh Markdown-fenced JSON, khiến P2 cũ INVALID và dẫn tới P2.1 thích nghi theo benchmark. | **VERIFIED runtime-interface-only** trên 1×T4, FP16, peak allocated khoảng 4.28 GB ở smoke; không OOM ([result](../configs/pre_freeze/internvl3_t4_runtime_result.v1.json)). Dynamic tiling 1–13 ảnh 448×448 và `output_logits=True` chưa được GPU-qualified cùng nhau. |
| Moondream2 | **VERIFIED** `vikhyatk/moondream2@9a7d4024050840e001defacec2b00727e89149e6`, tokenizer `moondream/starmie-v1@35192e10a54e36eabe0a7cc57a2c1aab371cafc5`; remote `HfMoondream`, native `query(image, question, reasoning=False, stream=False, settings)` ([audit](w2_moondream_runner_prep.md#native-interfaces-and-candidate-mapping), [runner](../safeshift/runners/moondream2.py#L170-L305)). | **BLOCKED qua public/native return:** runner chỉ serialize `{"answer": ...}`. Exact pinned source có `lm_head` logits trước argmax trong `_prefill_prompt`/`_decode_one_tok`, nhưng `_generate_answer` chỉ yield text ([pinned source](https://huggingface.co/vikhyatk/moondream2/blob/9a7d4024050840e001defacec2b00727e89149e6/moondream.py#L280-L321), [answer loop](https://huggingface.co/vikhyatk/moondream2/blob/9a7d4024050840e001defacec2b00727e89149e6/moondream.py#L436-L539)). Một forward hook chỉ đọc/clone output của `text.lm_head` là **PLAUSIBLE**, chưa implement/validate. | `Level01→?`, `Level02→?`, `Level03→?`, `Level04→?` — **NOT VERIFIED**. Tokenizer revision/hash đã pin, nhưng chưa có branch proof bằng `tokenizers==0.21.2`. | **BLOCKED hiện tại; instrument path PLAUSIBLE.** Chỉ được gọi HNLO sau khi chứng minh hook lấy logits trước phép gán `answer_id=-inf`, không đổi native answer/state, và T1 chứng minh nhánh một token. | Post-fix smoke **runtime interface PASS** trên 1×T4, FP16 bridge, peak allocated khoảng 4.44 GB ([record](w2_moondream_postfix_result_external_gate_prep.md#post-fix-smoke-research-lead-archive-audit)). Blocker cũ BF16 vision đã được bridge xử lý cho smoke; blocker HNLO mới là private-logit access, mapping và raw trace, không phải OOM đã quan sát. |

## Bằng chứng và giới hạn theo mô hình

### Qwen3

**VERIFIED:** revision, native class, official processor path, greedy C1 runtime
và 8/8 synthetic classification parse/exact match đã được ghi nhận; đây không
phải bằng chứng logits hay hiệu năng InspecSafe
([qualification](w2_d9r17b_e_classification_qualification_results.md#documentary-outcomes)).

**Còn thiếu:** tokenizer T1 trên exact revision; bằng chứng `output.logits` có một
tensor `[1,vocab]` cho từng generated token; candidate IDs đúng vị trí; raw values
khác/không khác processed scores được lưu rõ; nonfinite/OOM check dưới exact
T4×2 placement. Việc Qwen2.5 có cùng họ model/tokenizer không đóng các khoảng trống này.

### InternVL3

**VERIFIED:** exact snapshot và runtime single-T4 đã PASS ở phạm vi interface;
runner dùng source Transformers đã hash-pin. Eight-case classification cho thấy
8/8 parse success nhưng chỉ 6/8 exact; semantic FAIL không ngăn việc audit logits,
nhưng cũng không phải HNLO evidence
([qualification](w2_d9r17b_e_classification_qualification_results.md#documentary-outcomes)).

**Còn thiếu:** committed T1 PASS và token IDs; sealed raw trace/CPU recomputation
cho uncalibrated HNLO; xác nhận response representation nào được phép. Hồ sơ LS1
có kết quả kỹ thuật InternVL do Lead báo cáo, nhưng underlying raw artifact chưa
được kiểm toán độc lập; không nâng nó thành VERIFIED
([failure analysis](ls1_calibration_failure_analysis.md#what-remains-open-or-blocked)).

### Moondream2

**Kiểm tra cục bộ do Codex báo cáo:** các bản nguồn `moondream.py`, `text.py` và
`tokenizer.json` trong ignored audit cache đã được đối chiếu SHA-256 với metadata
đã commit trong
[`moondream_prep_audit.v1.json`](../configs/pre_freeze/moondream_prep_audit.v1.json):
`52e8d035…62e59`, `9ec56dd5…ce352` và `0512fdca…99e9c`. Các file cache không nằm
trong Git, nên bên kiểm toán độc lập chưa thể tự tính lại hash từ Git tree. Do đó,
bằng chứng độc lập hiện có chỉ xác nhận tính nhất quán của tài liệu và metadata;
không phải xác minh độc lập file nguồn, bằng chứng HNLO hay thực thi mô hình.

**Còn thiếu:** T1 branch proof; hook/trace schema; xác nhận hook clone logits trước
in-place special-token masking; raw-before-parse persistence; CPU recomputation;
GPU/state audit. Eight-case classification từng parse 8/8 nhưng dự đoán Level01
cho cả 8, nên chỉ chứng minh interface tạo canonical answer, không chứng minh score.

## Phương án dự phòng cần trình duyệt

Nếu một model không vượt capability gate:

1. Giữ model trong nghiên cứu, ghi **HNLO = N/A** cùng blocker và coverage; vẫn
   báo cáo baseline generated four-level/binary trên cùng cohort và mẫu số đã duyệt.
2. Có thể đề xuất **model-native exact-label sequence log-likelihood** khi nhãn là
   nhiều token, nhưng phải đặt tên/version riêng và công khai rằng nó **không tương
   đương HNLO**. Context, length normalization, full-vocabulary normalization và
   direction phải được chốt trước, qua quyết định mới.
3. Không dùng textual confidence, không gọi processed score là raw logit, không
   bỏ/thay model, và không đổi prompt/tokenizer/clamp sau khi xem kết quả.

Mọi fallback/N/A treatment cần Research Lead phê duyệt theo
[yêu cầu bốn mô hình](pa3_four_model_seminar_scope.md#điều-kiện-so-sánh-cần-được-xem-xét-và-phê-duyệt).

## Phép thử GPU nhỏ nhất sau khi có quyền

Trước GPU, mỗi model phải chạy CPU T1 trên tokenizer/snapshot đã pin: token hóa
28 biến thể plain/whitespace/fence, chứng minh toàn response chỉ khác một vị trí,
bốn ID phân biệt và round-trip chính xác. **T1 FAIL/BLOCKED thì không load model.**

| Mô hình | Một phép thử kỹ thuật tối thiểu, không benchmark |
| --- | --- |
| Qwen3 | 1 load trên exact runtime `2×T4 + embedding CPU`; 1 committed synthetic RGB case, exact C1, greedy/batch 1/max 32; bật `return_dict_in_generate`, `output_logits`, `output_scores`; persist IDs + candidate raw/processed values từng bước trước parse; yêu cầu canonical response, exact decision alignment, finite values và CPU HNLO recomputation bit-for-bit/tolerance policy đã predeclare. |
| InternVL3 | 1 load trên 1×T4; 1 synthetic 448×448 case; dùng exact LS1-style capture nhưng không calibration/reference; cùng các check raw/processed/alignment/persistence/CPU recomputation. Ghi tile count, input tokens, VRAM. |
| Moondream2 | 1 load trên 1×T4; T1 bằng exact Starmie tokenizer trước load; 1 native `query()` C1 với temporary read-only `text.lm_head` forward hook trả `None` và clone logits ngay khi gọi; persist hook trace + native answer; chứng minh hook được tháo, state audit không đổi, decision alignment đúng và CPU HNLO recompute. Đây là probe mới cần code review riêng. |

Chung cho cả ba: một run ID mới/model, Internet OFF sau verify, raw-before-parse,
không retry/fallback, không InspecSafe/GT/TEST/annotation. Bất kỳ response INVALID,
multi-token branch, missing step, raw/processed ambiguity, nonfinite, OOM hoặc state
drift đều dừng ở **NOT VERIFIED/BLOCKED**. Một synthetic PASS chỉ xác minh khả
năng kỹ thuật; không phải runtime production PASS, HNLO performance hay generalization.

## Blocker trước giai đoạn GPU

- Research Lead chưa phê duyệt cuối `DEC-PA3-011` hoặc giao thức/fallback.
- Chưa có T1 PASS đã được audit/commit cho bất kỳ model nào trong ba model ở
  scope HNLO này.
- Chưa có reviewed raw-logit capture cho Qwen3/Moondream; InternVL path chỉ là
  experimental scorer, không phải bằng chứng GPU đã audit.
- Mỗi probe cần authority riêng gắn model, revision, source commit, runtime,
  synthetic input, run ID và max attempts. Draft/report này không cấp quyền đó.
