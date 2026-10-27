# Three-VLM technical PREP audit — 27/10/2026

Đây là source/CPU self-review, **không audit độc lập hoặc GPU PASS**. BASE:
`28fdf82512577f2ed0fb435fb2c12b88e82baf2f`, HEAD/file inventory/source digest cuối
ghi trong một Draft PR. Nhánh/worktree riêng từ GitHub main; workspace cũ giữ
nguyên. Không có API mở chat Codex mới trong toolset; việc cô lập thực hiện bằng
worktree mới, không tuyên bố đã tạo session UI khác.

## Nguồn lịch sử đã đọc có chọn lọc

- [HISTORY](HISTORY.md) dẫn snapshot `31a04e6f7175cca818c63b4de0153246b3f3ecdb`.
  Đọc AGENTS/README/ROADMAP/ARCHITECTURE/PROJECT_STATE/DATA_AND_ETHICS/HISTORY;
  ROADMAP/TASKS root thuộc legacy, không phục hồi chúng vào main.
- [TRAIN V4 runbook](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/hnlo_train_v4_20261019.md)
  và [Recovery224 runbook](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/qwen3_s2_recovery224_20261022.md):
  đọc cohort/inputs/backend/capture/tokenizer, native/train/seminar,
  resource_pilot/orchestrate và classification policy/C1 tại đúng snapshot.
  Master/IDs/path convention/hash pin lấy từ nguồn này; không chạy release cũ.
- Selective reuse: **chỉ prompt C1 nguyên byte** (SHA trong contract) và các
  verifier saved-report đã merge của `scripts/analyze_source_sensitivity.py`.
  Viết runner mới nhỏ, không khôi phục hệ thống 693 file, quyền cũ hoặc placement
  Qwen. Không copy code Draft #136. Không sửa #136/#137 hoặc ref legacy.
- [Draft #137](https://github.com/tantdna2/SafeShift/pull/137), HEAD
  `6b7b3b9828a61440cb60733fe4640d9a237db0e0`: tham khảo đúng ba candidates và
  P1–P4. Code task hiện tại do Owner giao; không coi bản đề xuất là run authority,
  không làm P3 auxiliary utility/triage hoặc thay roster M2.

## Exact model/source pins và khả năng hiện biết

| Key / model | Exact revision | Stack dự kiến | Bằng chứng / giới hạn |
| --- | --- | --- | --- |
| gemma / google/gemma-3-4b-it | `093f9f388b31de276ce2de164bdc2081324b9767` | torch 2.6.0+cu124, torchvision 0.21.0+cu124, Transformers 4.51.3, FP16/eager | Native Gemma3ForConditionalGeneration; public card/API đọc được, 10 config/tokenizer resources 401; actual tokenizer/config/T4 còn BLOCKED/UNVERIFIED. |
| phi / microsoft/Phi-3.5-vision-instruct | `12b77fb40b63a2c73c68243d3f767aab688a1b2a` | cùng torch; Transformers 4.43.3/tokenizers 0.19.1, FP16/eager, 16 crops single image | Remote code review có pin và checksums trước import; card cho eager nếu không có FA2. Chưa chứng minh load/generation/image envelope trên T4. |
| smolvlm2 / HuggingFaceTB/SmolVLM2-2.2B-Instruct | `482adb537c021c86670beed01cd58990d01e72e4` | cùng torch; Transformers 4.51.3/tokenizers 0.21.1, FP16/eager | Native SmolVLMForConditionalGeneration; config khai báo F32, text BF16/FA flags, không coi đó là T4 FP16 PASS; backend ghi đè dtype/attention được predeclare, giữ image processor native. |

Nguồn trực tiếp: [Gemma card](https://huggingface.co/google/gemma-3-4b-it/blob/093f9f388b31de276ce2de164bdc2081324b9767/README.md),
[Phi card](https://huggingface.co/microsoft/Phi-3.5-vision-instruct/blob/12b77fb40b63a2c73c68243d3f767aab688a1b2a/README.md),
[Smol card](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct/blob/482adb537c021c86670beed01cd58990d01e72e4/README.md).
Model card snippets BF16/FA2 hoặc auto placement không được chạy nguyên xi.
Yêu cầu pinned môi trường xem ba requirements và runtime_versions; pip check,
freeze và exact versions được kiểm/lưu trong fresh venv. Cài dependency và native
GPU ABI trên Kaggle vẫn NOT_RUN; pins không chứng minh tương thích thực thi.

Nguồn API/capture: [Gemma3 native 4.51.3](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/gemma3/modeling_gemma3.py),
[SmolVLM native 4.51.3](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/smolvlm/modeling_smolvlm.py),
[generation 4.51.3](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/generation/utils.py),
[generation 4.43.3](https://github.com/huggingface/transformers/blob/v4.43.3/src/transformers/generation/utils.py).
Outer forward trả native logits; hook chạy trước generate nhận output/processor.
Đây là khả năng theo source, không chứng minh artifact thật đã capture đúng.

Phi exact custom-code closure đã rà: `configuration_phi3_v.py`,
`modeling_phi3_v.py`, `processing_phi3_v.py`; checksums trong
[model_source_lock.json](../configs/pilot/model_source_lock.json). Review imports,
CLIP construction (local config, không tải checkpoint CLIP thứ hai), image HD
transform, eager/FA dispatch, CausalLMOutputWithPast, cache và generation input
preparation. Các setter img_features không được runner gọi; mỗi image dùng
native preparation riêng, không tái dùng ảnh trước. `sample_inference.py` cũng
hash-pin như inventory, **không import/execute** (có demo URL/requests ngoài).
Code thực thi closure không thấy network/subprocess/eval/exec ngoài API tải
snapshot; Transformers/PyTorch vẫn trusted dependencies, không sandbox custom code.
Phải có direct review/approval cho risk trước thực thi. Code lock kiểm bộ `.py`,
checksum/config auto_map trước weights/import; remote refs ra repo khác bị chặn.
Sau provisioning, local_files_only + offline và safetensors, không pickle fallback.

## Token semantics và HNLO CPU

[tokenizer_cpu_evidence.json](../configs/pilot/tokenizer_cpu_evidence.json) được
tạo từ public exact tokenizer JSON, C1 và native chat template bằng immutable
Jinja sandbox; không weights hoặc ảnh. Audit tool dùng tokenizers 0.21.1/Jinja2
3.1.6, Python 3.11.9; Phi runtime pin 0.19.1 sẽ phải probe/replay lại chính runtime,
không suy audit 0.21.1 là qualification 0.19.1. Actual image-expanded boundary,
generated alignment, dtype/finite logits, memory và real replay đều NOT_RUN.

| Model | Standalone Level01/02/03/04 IDs đã quan sát | Candidate discriminating IDs (compact C1 JSON) | Kết luận hiện tại |
| --- | --- | --- | --- |
| Phi | `[21597,29900,29896]` / `[21597,29900,29906]` / `[21597,29900,29941]` / `[21597,29900,29946]` | `29896,29906,29941,29946`, generated decision step dự kiến 9, không áp cứng lúc chạy | Có branch text-only; HNLO_UNVERIFIED |
| Smol | `[15363,32,33]` / `[15363,32,34]` / `[15363,32,35]` / `[15363,32,36]` | `33,34,35,36`, step dự kiến 7, không áp cứng lúc chạy | Có branch text-only; HNLO_UNVERIFIED |
| Gemma | Không có quyền đọc tokenizer (401) | Không bịa IDs/step | HNLO_UNVERIFIED / gated source blocker |

Cả hai nhãn có nhiều token, nên không gọi toàn nhãn là một token. Chỉ xét điểm
quyết định khi bốn native continuations cùng prefix/suffix và khác đúng một
token; generated IDs thực phải match. Joint-encode prompt+answer có thể merge
newline ở boundary; runner không retokenize input đã cấp. Nó kiểm decode của
candidate continuation trong fixed actual token context (cùng prefix, chỉ cho
phép thêm whitespace boundary giống nhau), lưu diagnostic joint-encoding và
kiểm lại bằng independent Rust tokenizer. Không đổi prompt/label/tokenizer để
tạo thuận lợi, không teacher-force thêm model call, không sequence likelihood.
Giới hạn: dạng output không thuộc ba surface JSON đã chứng minh có thể vẫn
classification SUCCESS nhưng HNLO UNALIGNED, không ép/cứu mapping.

Score chỉ từ bốn raw logits tại step đã align:
`logsumexp(z01,z02,z03)-z04`, CPU stable math so Decimal odds oracle. Finite,
sign và shift invariance có test. Năm trạng thái HNLO giữ riêng, không đổi
SUCCESS classification khi capture/replay không đạt. Full-vocab vectors không
retained; raw argmax/finite reductions là bằng chứng hạn chế được ghi rõ.

## Kiểm thử đã thực hiện và chưa thực hiện

- Windows CPU: `python -B -m unittest discover -s tests -q`: **97 PASS** tại
  checkpoint trước commit; gồm 51 existing + 46 pilot tests. Lệnh cuối/count cuối
  được ghi trong PR nếu có bổ sung sau checkpoint. Tests synthetic, không skipped
  bằng cách giấu lỗi. Existing negative CLI test in thông báo output-exists theo
  thiết kế; unittest suite trả OK.
- `python -B -m scripts.build_three_vlm_notebooks`: deterministic, ba notebooks
  cùng source digest, cell compile/payload parity, execution_count null/output rỗng.
- CPU public tokenizer audit thực chạy, script/source checksums lưu trong config;
  synthetic HNLO oracle 100 random/extreme vectors, AUROC independent pair oracle.
- Còn NOT_RUN: Linux/Kaggle native dependencies, weights/load/real-image
  preprocessing, actual T4/VRAM/latency, real tokenizer/image decision alignment,
  actual HNLO/coverage/quality, optional Qwen artifacts, manifest 160 thật, full TRAIN.
  Không tuyên bố 97 CPU tests chứng minh native pipeline T4 PASS.

## Review gates còn thiếu

ChatGPT kiểm Draft PR/HEAD và quyết định audit độc lập; Lead duyệt sampling,
thresholds, common-branch HNLO interpretation, raw-summary evidence limit,
dependencies/Phi remote-code risk, resource/retention caps và grant schema.
Sau đó mới CPU preparation được phép, review manifest/hash/rights, per-model
GPU/download/raw export grants, Owner Kaggle run. Code/CPU DONE không thay các gate.
Paired hook-off GPU overhead chưa được cấp thêm calls và sẽ báo NOT_RUN/null;
nếu cần số đo đó, cấp lượt riêng trước thực hiện, không lấy từ 540 calls ban đầu.

Skill `experimental-design` v1.5 giúp chốt panel/seed/blocking, shared cohort và
giới hạn suy luận trước kết quả; không dùng DOE helper/dependency nặng hoặc coi
model outputs trên panel phụ thuộc là độc lập. Tham khảo phần mềm/phương pháp:
Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026),
*Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*,
arXiv v2 (02/09/2026), [DOI](https://doi.org/10.48550/arXiv.2609.00065).
Không coi skill là nguồn quyền dữ liệu hoặc phê duyệt khoa học SafeShift.
