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
Kết quả cài thư viện Linux CPU trong lần sửa audit ghi riêng bên dưới.

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
- Tại HEAD cũ còn NOT_RUN: Linux/Kaggle native dependencies, weights/load/real-image
  preprocessing, actual T4/VRAM/latency, real tokenizer/image decision alignment,
  actual HNLO/coverage/quality, optional Qwen artifacts, manifest 160 thật, full TRAIN.
  Không tuyên bố 97 CPU tests chứng minh native pipeline T4 PASS. Kết quả Linux
  dependency rehearsal của HEAD sửa được cập nhật ở phần dưới; Kaggle vẫn NOT_RUN.

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

## Sửa audit FAIL của PR #138 — 27/10/2026

Tiếp tục đúng branch/worktree/session và Draft [#138](https://github.com/tantdna2/SafeShift/pull/138),
không branch/PR mới. OLD_HEAD kiểm local và GitHub:
`5d0bbca3c10ea56b4f91b8368b692965c52a301f`; BASE giữ nguyên đầu file.
[Biên bản ChatGPT độc lập](https://github.com/tantdna2/SafeShift/pull/138#issuecomment-6438422457)
là nguồn phân loại phát hiện; lần sửa này là self-verification, **chưa thay audit
FAIL bằng independent PASS**. HEAD sửa/source digest cuối ở PR, không hash tự tham chiếu.

| Phát hiện | Xử lý trong cùng cập nhật | Giới hạn còn lại |
| --- | --- | --- |
| Không tìm thấy torch+cu124 khi chạy requirements đơn lẻ | Giữ nguyên mọi pin; dùng `dependency_commands()` chung cho bootstrap/rehearsal để kiểm đúng CUDA-index install trước rồi requirements, pip check và production `check_software()`. | Không dùng dry-run thiếu bước đầu để kết luận notebook lỗi. Kết quả Linux riêng phía dưới; Kaggle chưa chạy. |
| Scratch cố định theo temp và admission riêng 28/4 GiB | Dedicated working scratch; chuyển cả pip temp, HF/custom-code/cache; đo device/mount/free thật, gộp 32 GiB nếu cùng device, kiểm riêng nếu khác; cộng resume allowance. | Không khẳng định quota/mount Kaggle hoặc peak use. Thiếu dung lượng vẫn BLOCKED. |
| Phi 16 crops OOM | Giữ nguyên 16/FP16/eager/GPU0; first-12 và stop-on-OOM, raw/error/tail accounting. | UNVERIFIED T4 VRAM; không crop/dtype/attention fallback. |
| Gemma 401 và source lock trống | `check_source_review()` trước dataset trong supervisor/runner và trước Hub/weights trong provision; lock thiếu luôn BLOCKED, kể cả có token. Hướng dẫn audit xác thực riêng, output exclusive/redacted, không tải weights. | Access BLOCKED; source/tokenizer incomplete; HNLO_UNVERIFIED; GPU/classification NOT_RUN. Không thay lock giả bằng approval. |
| Hardlink trên mount Kaggle | Giữ nguyên `safe()`/`st_nlink == 1`; test hardlink thật trên fixture, alias/symlink rejection. | Chưa có Kaggle stat trace; false rejection là UNVERIFIED, không thêm ngoại lệ. |
| Đường worker/export, grant/resume, raw/HNLO, notebook | Test supervisor thật với boundary fault injection: installer order/env, storage failure, worker crash, ZIP writer failure, session metadata failure, attempt reuse, archive resume, Gemma fail-closed, FULL denial. Raw-before-parse kiểm đúng raw của từng ordinal. | CPU fixtures/mocks được gắn SYNTHETIC; không gọi đó là Save & Run All hoặc pilot PASS. |

Khi worker đã kết thúc/timeout, cleanup chỉ xóa scratch có đúng marker/session,
đường dẫn nằm trong working, giữ nguyên evidence/inputs/ledger. Dọn trước report/
archive để trả dung lượng runtime; dọn lỗi vẫn thử export. Lỗi ghi session/failure
receipt không ngăn export. ZIP fail giữ directory/partial ZIP, không tạo checksum
thành công giả. VM/kernel kill cứng có thể không chạy finalizer; chỉ export và
download sau phiên được cấp quyền mới xác minh retention thực.

### Tái hiện dependency đúng thứ tự, không inference

Script opt-in [rehearse_pilot_dependencies.py](../scripts/rehearse_pilot_dependencies.py)
tạo fresh venv từng model, không thuộc CPU test mặc định. Chạy trên Linux/Python
3.11 hoặc 3.12, output mới dưới `data/processed/`; cần quyền mạng/cài thư viện,
không cần hoặc tự cấp quyền dữ liệu/GPU. Cài thư viện CUDA không đồng nghĩa chạy GPU.

```console
python -B -m scripts.rehearse_pilot_dependencies --model phi --output data/processed/audit138-install-phi
python -B -m scripts.rehearse_pilot_dependencies --model gemma --output data/processed/audit138-install-gemma
python -B -m scripts.rehearse_pilot_dependencies --model smolvlm2 --output data/processed/audit138-install-smolvlm2
```

Chuỗi thực, cùng với notebook (sau tạo venv và pin pip 25.0.1):

```console
python -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu124 torch==2.6.0+cu124 torchvision==0.21.0+cu124
python -m pip install --no-cache-dir -r configs/pilot/phi.requirements.txt
python -m pip check
```

Thay key requirements tương ứng cho hai model còn lại, không thay version/index.
Requirements vẫn lặp exact CUDA pins để giữ cùng hợp đồng và tái hiện phát hiện.
Pip có thể dùng distribution exact-version đã cài ở bước trước; xem
[pip install](https://pip.pypa.io/en/stable/cli/pip_install/) và
[PyTorch previous versions](https://pytorch.org/get-started/previous-versions/).
Receipt ghi command order/exit codes/time/log hashes; runtime metadata check dùng
chính function production, freeze giữ cả NVIDIA/triton transitive dependencies.
CPU import smoke chỉ import APIs và chạy tensor FP16/NMS CPU nhỏ; không tạo model,
import Phi custom code, gọi CUDA API, tải weights, đọc ảnh hay liên hệ HF.

Môi trường tái hiện: WSL Ubuntu, CPython 3.11.13 cài riêng trong ignored workspace
bằng uv 0.8.22 (chỉ công cụ audit, không thêm vào runtime pins). Python mặc định WSL
3.14.4 không được dùng cho rehearsal. `df` quan sát `/tmp` là tmpfs ~3,9 GiB và
working trên `/mnt/d`; **đó là WSL này, không là bằng chứng mount Kaggle**.
Linux thật được cài; Windows vẫn chạy suite stdlib độc lập.

Kết quả cuối: **122 CPU tests PASS** trên Windows Python 3.11.9 (6,370 s) và
Linux Python 3.11.13 (6,655 s), 0 fail/skip. 25 tests mới cho supervisor/storage/
source audit, ngoài 97 tests trước; kiểm raw-before-parse cũ được siết tới đúng
file ordinal. Ba notebook tái tạo cùng source digest, PILOT literal/output rỗng.

[Receipt dependency](PILOT_DEPENDENCY_REHEARSAL_20261027.json) ghi bằng chứng theo
từng model, exact runtime versions, command stages/exit codes, freeze và SHA log:

- Phi và Gemma: fresh venv riêng, **cả hai lệnh install thật exit 0**, `pip check`
  trả `No broken requirements found.`, production `check_software()` khớp tất cả
  29 pins. Bước requirements nhận cả torch và torchvision local-version là
  `Requirement already satisfied`; không tái hiện lỗi thiếu `torch+cu124` theo
  chuỗi đúng này. Giữ nguyên PyTorch và mọi requirements/runtime pin.
- Smol: requirements **giống từng byte** Gemma, SHA-256
  `fc17c2ef5de2fb4224ff95c42b613c771b1da709642a9a7c49419fdc0909400c`, runtime pins
  cũng bằng nhau. Dùng venv Gemma đã cài thành công để kiểm pins/API Smol riêng,
  không thay package. Lần cài fresh venv Smol bị ngắt cùng WSL trong CUDA install,
  **không có completion receipt và không ghi PASS cho lần đó**. Bằng chứng hai bước
  của stack Smol dẫn tới Gemma qua phép đối chiếu bytes/pins, không giả là một lần
  cài Smol riêng đã hoàn tất.
- CPU smoke cho ba API chỉ kiểm import, FP16 tensor và torchvision NMS trên CPU;
  không instantiate model, không thực thi Phi remote code hoặc suy HNLO PASS.
  Với stack Gemma/Smol dùng chung để kiểm, có thể tái lập riêng Smol bằng:

```console
data/processed/audit138-install-gemma/venv/bin/python -B -c "from safeshift.pilot.backend import check_software; from scripts.rehearse_pilot_dependencies import cpu_smoke; print(check_software('.', 'smolvlm2')); print(cpu_smoke('smolvlm2'))"
```

Full logs/venvs nằm local dưới các relative paths trong receipt, bị Git ignore.
Receipt không chứa token, dataset, weights hoặc đường dẫn tuyệt đối máy cá nhân.
Đây là self-reported Linux CPU evidence để reviewer tái lập, không audit độc lập,
không chứng minh Python 3.12/Kaggle image/CUDA driver/T4 hoặc network mọi phiên.

Không weights, real TRAIN/TEST/annotations, Gemma credential hoặc GPU nào được
dùng trong lần sửa này. Kaggle/T4, native remote Phi execution, image preprocessing,
HNLO runtime/alignment/coverage/overhead và classification quality tiếp tục NOT_RUN.
