# Experiment log

W1 chưa chạy VLM. Các run được ghi nhận sau đó có nguồn evidence và phạm vi
riêng; không suy ra kết quả từ kế hoạch.

## W2.6-D9R2D-QWEN3-GATE-RESULT — existing audited run

- **Run ID / UTC date:** `kaggle-t4x2-qwen3-external-gate-20260925T175057Z-08fe69` / 2026-09-25.
- **Recording scope:** Research Lead directly inspected/rehashed the real bundle;
  this entry transcribes supplied findings only. No new execution or rerun.
- **Execution commit:** `23556cf3f0adc93b76075a3247a18dd4686ff87a`.
- **Condition and inputs:** Qwen3-VL-8B-Instruct at the unchanged exact revision,
  Kaggle T4x2, frozen eight-case synthetic-v1 suite; no InspecSafe.
  Plan: `configs/pre_freeze/qwen3_external_gate.v1.json`. No random case sampling.
- **Result:** COMPLETED / GATE_FAIL, one initialize/load, eight native generations,
  five SUCCESS, two COORDINATE_ERROR, one SCHEMA_ERROR; tracking false.
  No runtime/resource failure; OOM NOT_OBSERVED.
- **Evidence and interpretation:** [audited result note](notes/w2_qwen3_external_gate_result.md)
  and [machine-readable record](configs/pre_freeze/qwen3_external_gate_result.v1.json)
  contain bundle/summary/per-case raw hashes, model/resource/decoding pins and
  supplied observations. Bundle/raw bytes stay outside Git; the recording agent
  did not independently inspect them. Expected run artifacts follow the frozen
  harness layout under `data/processed/external_gate/w2_qwen3/<run_id>/`.
- **Outcome:** grounding NOT_PARTICIPATING / SPATIAL_GATE_FAILURE, classification
  CANDIDATE, resource anchor unchanged. No human giant review, backup substitution,
  artificial zero IoU or post-hoc repair. Global D9 gate and protocol freeze PENDING.

## W2.6-D9R2E-MOONDREAM-PREP — documentary audit, no experiment

- **Status:** STOP_FP16_SOURCE_BLOCKER_RESEARCH_LEAD_REQUIRED. Metadata/source
  capture only; no remote code executed, weights downloaded or model loaded.
- **Model / dependency:** exact Moondream `9a7d4024050840e001defacec2b00727e89149e6`;
  Starmie `35192e10a54e36eabe0a7cc57a2c1aab371cafc5`.
- **Evidence:** [audit record](configs/pre_freeze/moondream_prep_audit.v1.json),
  [source findings](notes/w2_moondream_runner_prep.md); local source captures in
  ignored `data/processed/moondream_prep/`. Hashes are observations of source
  bytes and metadata, never measurements of model performance.
- **Runtime / metrics:** NOT_RUN; no GPU, model inference, synthetic gate,
  InspecSafe or accuracy. No model run ID or raw output exists. Seed not applicable.
- **Next:** Research Lead must resolve the hard-coded BF16 vision path before
  runtime PREP can continue. No fallback and no resource/grounding promotion.

## W2.6-D9R2H-MOONDREAM-LOAD-DIAGNOSTIC-PREP — no new experiment

- Research Lead-reported previous run:
  `kaggle-t4-moondream-smoke-20260926T070217Z-4c2d43`.
  FAIL_T4_RUNTIME_INTERFACE / FAIL, load / ValueError, cause_type null;
  query/detect counts 0, empty state_audits/image_boundaries, peak CUDA memory 0.
  Snapshot verification, GPU condition and Python/dependencies reported PASS.
- Original bundle was not independently inspected here; its execution SHA was
  not supplied. Original FAIL and official ATTEMPT.json remain untouched.
- Static analysis cannot uniquely identify the exception. Separate load-only
  diagnostic **PREPARED_NOT_RUN**; no new real run ID, model outputs or metrics.
  No official smoke rerun, download, GPU, query, detect, gate or InspecSafe.
- [Static candidates, report contract and future invocation](notes/w2_moondream_load_diagnostic.md).
  Existing runner, precision bridge and frozen runtime conditions unchanged;
  no qualification or protocol-freeze promotion.

## W2.6-D9R2J-MOONDREAM-FUNCTION-IDENTITY-DIAGNOSTIC-PREP — no new experiment

- Research Lead reports exactly one real load diagnostic:
  `moondream-load-diagnostic-20260926T124352Z-d0f85ea7`, execution commit
  `b8a53ca25dad354c378591bf124e73d557a38caf`.
  FAIL / load / ValueError / `AUDITED_FUNCTION_IDENTITY_REQUIRED` at
  `verify_function(module.MoondreamModel.__init__, ...)` via `starmie_redirect`.
- Reported Python 3.11.11/software pins, single visible Tesla T4 CC 7.5 and
  model/tokenizer verification PASS; provision/verify manifests equal.
  Query/detect zero, empty state_audits/image_boundaries; no bridge or inference.
  Original evidence was not independently opened/rehashed here; no rerun.
- Separate identity-only diagnostic **PREPARED_NOT_RUN**, fake/static tests only.
  The failing identity subcondition remains **UNKNOWN**. No runtime repair,
  guard change, new real run ID, model output, metric or qualification claim.
- Existing redactor's `hf_moondream.py` -> `[REDACTED].py` false positive
  reproduced with fake strings; no shared redaction fix or artifact rewriting.
- [Contract and validation](notes/w2_moondream_function_identity_diagnostic.md).
  No real diagnostic, model construction, GPU/model execution, query/detect,
  bridge, smoke, gate, InspecSafe, download or merge.

## W2.6-D9R2L-MOONDREAM-POSTFIX-SMOKE-PREP — no new experiment

- Research Lead reports `moondream-load-diagnostic-20260927T014821Z-b3c87faa`:
  LOAD_ONLY_PASS, complete, exit 0, exception null, load count 1, state audit VALID,
  query/detect 0; exactly one visible Tesla T4 CC 7.5, Python 3.11.11/exact pins,
  provision == verify manifests, execution `a6f5c012437bf8f404924e8dfb19a11536a92d77`.
  Original bundle not independently inspected here.
- Historical `kaggle-t4-moondream-smoke-20260926T070217Z-4c2d43` remains FAIL /
  consumed before successful load. Its ledger/result are not reset or replaced.
- Separate post-fix smoke **PREPARED_NOT_RUN**, independent one-attempt ledger;
  fake/static tests only, no new real run ID, raw model outputs or metrics.
- [Contract, future commands and validation](notes/w2_moondream_postfix_smoke_prep.md).
  No GPU/model execution, download, real smoke, external gate, InspecSafe or merge.

## W2.6-D9R2M — post-fix smoke result and external gate PREP

- **Reported completed smoke:** Research Lead checked archive for
  `moondream-postfix-smoke-20260927T022150Z-1b8def87`, execution commit
  `9bc5509ecffcb9d7b2faa4a023cd76bd358e2723`: `RUNTIME_INTERFACE_PASS`, exit 0,
  one load/query/detect, 5/5 VALID state audits, two correct boundary triples,
  13/13 recorded SHA-256 entries verified. This PR does not independently rehash
  the archive or run the smoke again.
- Native query/detect feasibility **PASS**; CPU FP16 -> CUDA FP16 -> vision
  consumption FP16 bridge successfully exercised for both calls. Exactly one
  visible Tesla T4 CC 7.5, 15636037632 bytes, host T4 x2, mask 0, Internet OFF;
  peak allocated/reserved 4436097536/4513071104 bytes.
- Historical official smoke stays **FAIL / consumed / not superseded**.
  Grounding qualification and protocol freeze remain **PENDING**.
- Separate eight-case native-detect external gate **PREPARED_NOT_RUN**; unchanged
  synthetic-v1 suite, canonical evaluator, explicit human giant-box review and
  fixed one-attempt ledger. No new real run ID, raw model output or gate metric.
- [Full reported query/bbox, provenance, frozen rules and validation](notes/w2_moondream_postfix_result_external_gate_prep.md).
  **NO REAL RUNTIME EXECUTION** in this task; no model/GPU/download/gate,
  InspecSafe, training, model selection or merge.

## W2.6-D9R2N-MOONDREAM-EXTERNAL-GATE-RESULT-RECORD — existing run, final human review

- **Run ID / UTC date:** `moondream-external-gate-20260928T013533Z-d9a1c46b` / 2026-09-28.
- **Execution commit / recording base:** `c801c899a1b63831175ea47d1d77d77f11f8e115`.
- **Source:** Research Lead/user-confirmed runtime findings and human review;
  no independent archive inspection, visual review or evaluator rerun here.
- **Existing artifact:** `GATE_PENDING_REVIEW`, `completed_gate=true`,
  `model_load_count=1`, `query_call_count=0`, `detect_call_count=8`;
  17/17 state audits VALID, 24/24 image boundaries in order,
  `systematic_tracking=true`, all eight cases completed.
- **Human review / final result:** A_1, A_2, B_1, B_2, C_1, C_2, D_1, D_2 each
  **NO_GIANT**. External gate **PASS**; grounding qualification **PASS**.
  Original runtime artifact status remains unchanged.
- **Preserved history:** Post-fix runtime interface **PASS** already recorded;
  historical official smoke **FAIL / consumed / superseded=false** unchanged.
- **Provenance and limits:** [Final review record](notes/w2_moondream_postfix_result_external_gate_prep.md#d9r2n--external-gate-final-human-review-record)
  links the existing gate contract and artifact layout. No new runtime outputs,
  dataset metrics or freeze claim. **NO REAL RUNTIME EXECUTION** in this task.

## Template

- **Run ID và ngày:** <ID; YYYY-MM-DD>
- **Trạng thái:** <planned / running / completed / failed>
- **Câu hỏi hoặc mục đích:** <nội dung>
- **Protocol / decision liên quan:** <relative path hoặc ID>
- **Git commit và thay đổi chưa commit:** <hash; mô tả nếu có>
- **Dataset, version, checksum và split:** <nguồn và định danh chính xác>
- **Manifest / sample IDs:** <relative path>
- **Môi trường:** <OS, runtime, dependency versions, hardware>
- **Model và revision:** <định danh; nếu dùng model>
- **Prompt / cấu hình / preprocessing:** <relative path và version>
- **Seed và thiết lập deterministic:** <giá trị hoặc không áp dụng, kèm lý do>
- **Lệnh tái lập:** <lệnh chạy từ repository root>
- **Raw model outputs:** <relative path; bắt buộc cho lần chạy VLM, liên kết tới từng sample/lần gọi>
- **Logs và artifacts:** <relative paths>
- **Metric và phiên bản định nghĩa:** <tham chiếu protocol đã chốt; không tự thay đổi>
- **Kết quả thực đo:** <chỉ điền sau khi chạy; mẫu số, đơn vị, độ bất định nếu có>
- **Lỗi, mẫu thất bại và sai khác với protocol:** <ghi đầy đủ, không âm thầm bỏ mẫu>
- **Phân tích và giới hạn:** <phân biệt quan sát với diễn giải>
- **Bước tiếp theo:** <nội dung>
