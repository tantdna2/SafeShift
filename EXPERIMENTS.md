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
