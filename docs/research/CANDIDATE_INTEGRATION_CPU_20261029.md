# InternVL3.5 HF / MiniCPM-V-4 — tích hợp CPU trước Kaggle

29/10/2026, Asia/Bangkok. Phạm vi Owner giao: hoàn thiện hai adapter và kiểm thử
CPU bằng source public/ảnh tổng hợp, dừng tại **một Draft PR** để ChatGPT review.
PR #150 đã xác minh `merged=true` qua GitHub; `origin/main` khi bắt đầu là
`bbbd351e19e404f1108413578c7ed024f92e814d`. Nhánh mới
`implement/candidate-integration-20261029`; workspace cũ được giữ nguyên.
Không có công cụ tạo một phiên chat mới; công việc dùng worktree/nhánh mới.

**Trạng thái nghiệm thu cuối: CPU READY, trong phạm vi phần mềm đã kiểm thử.** Đây là nghiệm thu phần
mềm CPU, không chứng nhận GPU, inference, chất lượng phân loại hay HNLO.
Nguồn trước task: [báo cáo PR #150](CPU_G2_G3_CANDIDATES_20261029.md),
[public source lock](../../configs/cpu_g2_g3/public_source_lock.json),
[release gates](../KAGGLE_FAILURES_AND_RELEASE_GATES.md).

## Kết quả và mức bằng chứng

Code thực chạy: **`65640ddf91bd0ce75e594c372af098ecb59194eb`**. Sau commit này,
chỉ thêm tài liệu/receipts, không sửa mã để giữ kết quả cũ.

| Kiểm tra | PASS | SKIP | FAIL / ERROR |
| --- | ---: | ---: | ---: |
| InternVL, isolated Windows CPU, 65 tests | 62 | 3 | 0 / 0 |
| MiniCPM, isolated Windows CPU, 65 tests | 62 | 3 | 0 / 0 |
| InternVL, isolated Linux CPU, 65 tests | 64 | 1 | 0 / 0 |
| MiniCPM, isolated Linux CPU, 65 tests | 64 | 1 | 0 / 0 |
| Exact Git export / toàn repo Windows, 266 tests | 231 | 35 | 0 / 0 |
| Exact Git export / toàn repo Linux, 266 tests | 236 | 30 | 0 / 0 |

**Cả 13 native integration tests đều PASS cho từng mô hình trên cả hai OS.**
Windows focused SKIP = 3 real symlink tests thiếu quyền OS; junction thực PASS.
Linux focused SKIP = 1 Windows-junction test; real symlink/hardlink tests PASS.
Full suite chủ động không bật native: SKIP chung gồm 13 candidate + 6 Phi +
9 Smol + 1 network bootstrap; Windows thêm 3 symlink + 3 Linux filesystem,
Linux thêm 1 Windows junction. Candidate native có receipts riêng bên trên;
Phi/Smol native không tái kiểm trong task này.

Hai full checkers trả **CODE_PASS / release BLOCKED**, cùng xác minh byte/builder/
payload/compile của sáu notebook cũ. Không execute notebook cells. Full suite
không được dùng thay bằng chứng native hoặc cấp quyền GPU.

[Index bốn candidate receipts](evidence/candidate_integration_20261029/index.json),
[Windows release receipt](evidence/candidate_integration_20261029/release-windows.json),
[Linux release receipt](evidence/candidate_integration_20261029/release-linux.json),
[release checksums](evidence/candidate_integration_20261029/release_checksums.json).
Candidate receipts là bytes nguyên bản. Hai release receipts công khai là bản
sao chỉ che đường dẫn thư mục tạm tổng hợp trong stdout; trường `publication`
ghi hash receipt nguyên bản và đúng field bị che. Counts/results/stdout-stderr
hash gốc giữ nguyên; receipt nguyên bản bất biến nằm local ignored.

CPython **3.11.9**, Torch **2.6.0+cpu**, torchvision **0.21.0+cpu**, Accelerate
**1.6.0**, NumPy **1.26.4**, Pillow **10.4.0** trên Windows và WSL2 Linux.
Transformers/tokenizers/Hub lần lượt **4.55.4/0.21.4/0.34.4** cho InternVL và
**4.51.3/0.21.1/0.30.2** cho MiniCPM. `pip check`, freeze/pins, isolated library
paths và compiled torchvision NMS đều PASS; exact platform/freeze trong receipts.

Các counts là Codex thực chạy, không CI/independent audit hoặc ChatGPT-rerun.
Mọi test native của cả hai mô hình phải PASS mới ghi CPU READY. SKIP của test
hệ điều hành được nêu riêng; không bỏ test lỗi để đạt PASS. Receipts khóa Git
commit thực chạy, SHA từng module/script/test/config, model/revision, versions,
compiled CPU ABI, test names/results và source không đổi trong lượt chạy.

## Đường tích hợp

Code dùng lại ở `safeshift/candidates/`, tương thích interface
`generate(image_path, sample_dir)` của runner hiện có. `CandidateBackend` nhận
snapshot source riêng, thư mục weights riêng và C1; không downloader hoặc CLI
inference mới. `pilot.runner.execute`, `Store`, parser, HNLO replay và archive
writer được tái sử dụng trong tests. Chỉ test có model identity/config tổng hợp
injected tại boundary; không ghi candidate vào registry/quyền của pilot cũ.

Đăng ký vào **execution release/notebook có grant** vẫn cần model/source/runtime/
protocol được review riêng ở G0/G1. Không chuyển grant Gemma/Phi/Smol sang hai
candidate. Không tạo engine, ngưỡng behavior hoặc mẫu số thí nghiệm khác.

| Đặc điểm | InternVL3.5 HF | MiniCPM-V-4 |
| --- | --- | --- |
| Exact identity | `OpenGVLab/InternVL3_5-4B-HF` @ `6bd4487402110ef9889ba50eb7aefeb302526fed` | `openbmb/MiniCPM-V-4` @ `6f69a8235885be89608f3a71ffd40695b379e1e7` |
| Native class / Transformers | `InternVLForConditionalGeneration`, 4.55.4 | hash-locked `MiniCPMV`, 4.51.3 |
| Loader | reviewed class directly, explicit eager after deserialization | reviewed class directly, eager on Llama + vision; no AutoModel re-import |
| Attention coverage | 36 Qwen3 + 24 InternVL vision layers | 32 Llama + 27 Siglip layers |
| Image | native HF template/processor, 1–13 views, 256 tokens/view, ID **151671** | native slices/resize/normalize/patch packing; RGB axis explicit, 1–10 views, 64 tokens/view |
| Generation entry | native `.generate` with fresh frozen GenerationConfig | native `.generate(decode_text=False, stream=False)` → `_decode` → `llm.generate` |
| Native sequence | prompt IDs + continuation; verify exact prefix then slice | continuation-only from `inputs_embeds`; **never slice by prompt length** |
| Raw logit boundary | outer InternVL forward output | `llm.forward` output actually used by native `_decode` |
| Raw custody | bounded per-step logits persisted; returned IDs saved before decode; Store raw before parse | same custody, no native text cleanup or `.strip()` |

[Checkpoint metadata lock](../../configs/cpu_g2_g3/checkpoint_metadata_lock.json)
records two public safetensors shards/model, sizes and LFS SHA256, and index
SHA256. **No shard downloaded.** Index has 841 InternVL / 741 MiniCPM tensor keys.
InternVL 4.55.4 natively renames old `language_model.model`, `vision_tower`,
`multi_modal_projector`, `language_model.lm_head` prefixes; tests use its real
`_get_key_renaming_mapping`, require one-to-one mapping and full module inventory.
MiniCPM keys match directly. Names/counts do not prove actual tensor bytes/shapes.
Public API response hash is an observation receipt; mutable API counters need
not reproduce that hash. Immutable revision/index/source hashes must reproduce.

`load_meta_model` executes the real empty-state `from_pretrained` constructor;
separate test executes native file loader on an **empty synthetic safetensors**
file and rejects a corrupt header. All parameters remain meta/FP16. MiniCPM's
native `resampler.pos_embed` buffer may live on CPU; no claim that all buffers
are meta or that meta loading validates device placement. Prepared weight loader
verifies exact flat index/shard allowlist, size/SHA, safetensors-only and eager;
its actual checkpoint deserialization/device dispatch is **NOT_RUN**.

## Hai lỗi MiniCPM đã xử lý

1. **RGB 1×1 / height 1 or 3:** upstream infers a channel axis from the original
   PIL image converted to HWC array, then reuses that guess after native resize.
   A height of 1 or 3 can be mistaken for a channel count. Passing
   `input_data_format` through the native processor does not fix it: this pinned
   wrapper does not forward that kwarg to its image preprocessor.
   `minicpm_image.rgb_image_inputs` uses the known PIL RGB **channels-last** axis
   for normalization/layout conversion, calls the original slicing/resize/
   patch-packing methods, and calls the original text/image placeholder converter.
   No new resize, padding, crop, image exclusion or slice budget. Spatial color
   patterns compare every tensor/token/grid exactly with unmodified native code
   on unambiguous sizes; tiny constant RGB cases verify normalization independently.
   Original failure remains reproducible in tests; no upstream snapshot is patched.
2. **Native chat generation/raw contract:** `chat(sampling=False)` adds beam3/
   repetition1.2, filters frozen flags and forces text cleanup. The adapter calls
   the public native `generate(decode_text=False)` path that forwards a fresh
   GenerationConfig to the LLM. The frozen `GENERATION` dict is byte-for-byte
   unchanged; no logit field is removed. Native `_decode` uses terminators
   `<|im_end|>`/`</s>` (73440/2) and pad0. The adapter records these effective native
   IDs, tests both terminators, and never removes generated BOS/pad IDs from raw.
   The model's stored generation_config pad2 is not misreported as effective pad0.
   No hidden repetition penalty, beam search, output stripping or parser rescue.

These are technical corrections to meet the existing RGB/C1/generation contract.
Any later change to input envelope, preprocessing policy, C1, parser, generation
values, EOS policy, metric or scientific protocol remains **approval-required**;
this PR does not approve it. Both corrections remain subject to Draft review.

## Kiểm thử và bảo vệ bằng chứng

- 12 synthetic sizes: six PR150 sizes plus `(1,17)`, `(17,1)`, `(3,19)`, `(19,3)`,
  `(14,14)`, `(449,447)`. Spatial recipe `(3x+y,7y+x,x+11y) mod 256`, deterministic,
  no random seed. Constant RGB `(40,80,120)` normalization; RGBA PNG with `.jpg`
  extension follows content decode and RGB conversion. No dataset image/GT read.
- C1 hash `816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3`,
  exact rendered/expanded content, ID/mask dtype/range/context, image tokens,
  bounds/order and patch grids. Corrupt inputs stop before model boundary.
- Actual native image feature plumbing uses **scripted vision/projector/embedding
  outputs**, not model inference. InternVL CLS/pixel shuffle/placeholder scatter;
  MiniCPM patch masks/vision batch splitting/resampler scatter are exercised.
  MiniCPM single-view shortened bounds can silently leave a placeholder unfilled;
  multiple unequal bounds fail native stacking. Adapter rejects both beforehand.
- Native GenerationMixin receives scripted next-token logits, with real tokenizers
  and MiniCPM's real outer generate/_decode. Four labels, whitespace preservation,
  duplicate-key INVALID, repetition/max64, both EOS, all raw IDs and bounded raw
  logits. Existing 15-case Store/parser/diagnostic matrix is reused as well.
- ENOSPC at request/native-call/processors/step/native-ID writes, decode error,
  load failure/OOM/nonfinite, hook removal, raw-before-parse, NOT_ATTEMPTED tail,
  exclusive writes and partial archive/reimport. This is fault injection, not
  proof of durability under every disk failure, hard-kill or power loss.
- PR150 flat snapshot guard reused; symlink/hardlink/junction/hidden/directory/
  stale-byte guards retained. MiniCPM dedicated module cache checked **before**
  import: only reviewed Python and empty package initializers, no bytecode or
  extra entries; hashes checked again after import. No broad remote-code sandbox
  or independent security audit is claimed.
- Exact per-model CPU requirements, pip check/freeze, torchvision compiled NMS,
  pinned implementation hashes, offline/socket/CUDA/weight-loader and native
  model-forward guards. Real model forward is forbidden; only test doubles
  produce logits. Exceptions/results are kept, never upgraded to behavior PASS.
- Public receipt verifier rejects changed/missing executed source, receipt hash,
  model identity, skipped native checks, counts, scope and missing model evidence.
  Protected source lock preserves science, existing public/dependency locks and
  C1; pilot runtime/source digest remains
  `1d76c3a4e5cf9c5fe32d6fd94b846a2879eca268a6023ce34203794dc801d884`.

## Tái lập từ repository root

Use fresh output names. Dependencies/source/index/cache/artifacts stay ignored
under `data/processed/`; do not commit downloaded upstream files, images, model
output or weights. CPython **3.11.9** was used; Linux runtime installation is a
local CPU setup step, not a change to Kaggle's approved worker selection policy.

```bash
python3.11 -m venv data/processed/integration/env-internvl35
python3.11 -m venv data/processed/integration/env-minicpm4
data/processed/integration/env-internvl35/bin/python -m pip install -r configs/cpu_g2_g3/internvl35.requirements.txt
data/processed/integration/env-minicpm4/bin/python -m pip install -r configs/cpu_g2_g3/minicpm4.requirements.txt
python -B -m scripts.pilot_source_audit --models internvl35 minicpm4 --output data/processed/integration/public
python -B -m scripts.fetch_candidate_indexes --output data/processed/integration/indexes

data/processed/integration/env-internvl35/bin/python -B -m scripts.rehearse_candidate_integration --model internvl35 --snapshot data/processed/integration/public/internvl35 --index data/processed/integration/indexes/internvl35-model.safetensors.index.json --output data/processed/integration/internvl35-run1
data/processed/integration/env-minicpm4/bin/python -B -m scripts.rehearse_candidate_integration --model minicpm4 --snapshot data/processed/integration/public/minicpm4 --index data/processed/integration/indexes/minicpm4-model.safetensors.index.json --output data/processed/integration/minicpm4-run1
python -B -m unittest discover -s tests -v
python -B -m scripts.verify_candidate_evidence docs/research/evidence/candidate_integration_20261029/index.json
python -B -m scripts.check_notebook_release --runtime-ref 65640ddf91bd0ce75e594c372af098ecb59194eb --output data/processed/integration/release-run1.json
```

Windows uses `Scripts/python.exe` instead of `bin/python`. Each model runs in a
separate process and venv. The Windows rehearsal reuses the exact PR150 venvs and
public snapshots, rechecking versions/source hashes; Linux creates fresh venvs
with the same pins. Rehearsal exits nonzero on failed mandatory checks or source
mutation; receipts distinguish CPU_CHECKS_PASS from overall release BLOCKED.
No notebook cell is executed by these commands.
The new index-fetch command was also executed: exact SHA/size PASS for the
79,936-byte InternVL and 62,812-byte MiniCPM indexes; no shard request.

Linux chạy qua WSL2 trên worktree do Windows tạo. Lượt thực dùng `GIT_DIR` và
`GIT_WORK_TREE` trỏ tới metadata/worktree tương ứng qua mount WSL; không sửa `.git`
hoặc repo config. Checkout Linux thông thường không cần hai biến này. Không
hard-code đường dẫn máy trong code/config. Venv Linux dùng runtime CPython3.11.9
cục bộ, cài bằng uv0.6.17 với đúng requirements; artifact cài đặt giữ local.

Lượt phát triển không dùng làm final evidence: hai kiểm thử ban đầu sai kỳ vọng
(tên tensor InternVL trước native conversion; MiniCPM shortened-bound behavior),
đã sửa theo nguồn thật và thêm negative guard checks. MiniCPM Linux khởi động
khi installer chưa xong bị dependency gate từ chối; lần WSL đầu gặp đường dẫn
Git dạng Windows. Wrapper nay kiểm Git provenance trước tests, ghi BLOCKED nếu
thiếu. Một lần checker nhận SHA ngắn cũng bị từ chối đúng thiết kế, sau đó chạy
full40 SHA. Các failure logs được giữ local; không nhận những lượt đó là PASS.
Automatic approval review từng hết hạn mức khi kiểm WSL; sau Owner yêu cầu tiếp
tục, duyệt lệnh hoạt động lại. Không bypass approval hoặc chạy GPU để khép CPU.

## Điều kiện dừng trước GPU

**Stop at Draft PR. No GPU/Kaggle/notebook/inference, no grant, no merge.**
CPU READY, if established, applies only to this source/API/test scope.

1. ChatGPT reviews exact branch/head/diff and receipts; independent technical/
   security review if separately requested. No self-approval or self-merge.
2. G0/O1–O8/T0/O3 must settle approved model/revision, input envelope/GT rights,
   finite attempt sequence, count/time/cost and behavior stop criteria. No default
   first12/160, no fourth-model selection; peer slot3 remains VACANT.
3. G1 must register these adapters into a separately reviewed executable release,
   source-bound notebook/runtime and new authority. Existing pilot registry,
   six released notebooks and grants are unchanged. CPU acceptance is now complete
   in the tested scope; this handoff stops at adapter review, without a new notebook.
4. Linux CPU wheels are not a CUDA qualification. G4 must validate a reviewed
   CUDA/Python/library tuple and actual isolated worker driver/device initialization,
   free/per-GPU VRAM, storage and authority before any approved model load.
5. Real weight bytes/deserialization, FP16 finite outputs, actual attention execution,
   generated IDs/logits, VRAM/OOM, classification quality, peer utility and HNLO
   remain **UNVERIFIED / NOT_RUN**. They require separately authorized G4/G5 evidence.
   TRAIN/TEST, threshold selection and protocol changes are not authorized by this PR.

## Nguồn kỹ thuật chính

- [Pinned MiniCPM model code](https://huggingface.co/openbmb/MiniCPM-V-4/blob/6f69a8235885be89608f3a71ffd40695b379e1e7/modeling_minicpmv.py): `generate`, `_decode`, `get_vllm_embedding`, `chat`.
- [Pinned image processor](https://huggingface.co/openbmb/MiniCPM-V-4/blob/6f69a8235885be89608f3a71ffd40695b379e1e7/image_processing_minicpmv.py) and [processor](https://huggingface.co/openbmb/MiniCPM-V-4/blob/6f69a8235885be89608f3a71ffd40695b379e1e7/processing_minicpmv.py): RGB inference, slices and placeholder conversion. Code license Apache-2.0 per the pinned model card.
- [Native InternVL 4.55.4](https://github.com/huggingface/transformers/blob/v4.55.4/src/transformers/models/internvl/modeling_internvl.py): key conversion, image feature/mask and native generation.
- [InternVL checkpoint config](https://huggingface.co/OpenGVLab/InternVL3_5-4B-HF/blob/6bd4487402110ef9889ba50eb7aefeb302526fed/config.json), exact public source hashes and original CPU findings remain in #150.

Sources were inspected from the hash-locked local copies and pinned installed
packages. Public web rendering was unavailable for two HF pages; that did not
replace byte verification with search snippets. New Hub metadata/index GETs
succeeded at the exact revisions; no weights or authenticated request was used.
