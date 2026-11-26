# SafeShift — Kaggle failures and notebook release gates

29/10/2026, Asia/Bangkok. Entrypoint bắt buộc cho người chuẩn bị/review notebook;
không cấp quyền chạy. [Chỉ thị #137](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6486252968)
yêu cầu học từ lỗi thật, giữ khoa học khóa và nghiệm thu theo tầng. Phạm vi hiện tại:
CPU/stdlib, source Git công khai, không Kaggle/weights/TEST/grant/private archives.

## Cách đọc bằng chứng

- `CONFIRMED` chỉ cơ chế/quan sát mà nguồn dẫn chứng minh; không lan sang cả model.
  `HYPOTHESIS` là giải thích cần kiểm; `UNKNOWN` là chưa đủ bằng chứng căn nguyên.
- `FAILED_PRELEDGER` = không tiêu attempt **khi receipt/ledger xác nhận**;
  `ATTEMPT_CONSUMED` không được reset dù 0 ảnh hoặc INVALID toàn bộ.
  Khi hồ sơ không đủ, consumption=`UNKNOWN`, không suy từ số calls.
- `CODE_PASS` ≠ `REAL_GPU_PASS` ≠ `CLASSIFICATION_VALID` ≠ `HNLO_VALID` ≠
  `SCIENTIFIC_UTILITY_PASS`. CLASSIFICATION_VALID nói đầu ra hợp đồng/coverage;
  không đồng nghĩa phân loại đúng. Báo counts và quality riêng, không cờ PASS chung.
- Các ZIP dưới đây được **ChatGPT/Lead kiểm theo nguồn dẫn**, không được mở/rehash
  lại trong task này. Chỉ aggregate công khai; không chép raw/GT/ảnh/token/private IDs.

## Incident register và kiểm thử đã bỏ sót

Nguồn snapshot phần mềm hiện hành là `67fc1ffc9519e068072644e0f891932fed28f463`;
nguồn lịch sử là `31a04e6f7175cca818c63b4de0153246b3f3ecdb` (xem [HISTORY](HISTORY.md)).

| MODEL / RUN | SYMPTOM | ROOT_CAUSE | FIX-OR-DECISION / STATUS | PREVENTION_GATE / test đã PASS nhưng thiếu | RECEIPT |
| --- | --- | --- | --- | --- | --- |
| Phi a2 | 0/160 inference, kernel Python 3.13 không phù hợp pinned worker | CONFIRMED: runtime admission yêu cầu qualified 3.11/3.12, không 3.13 | Worker riêng; ATTEMPT_CONSUMED theo lịch sử, không tái dùng | G2/G4 probe **interpreter thật** trước ledger; storage/two-T4 PASS không kiểm ABI Python | [Runtime audit](https://github.com/tantdna2/SafeShift/blob/67fc1ffc9519e068072644e0f891932fed28f463/docs/KAGGLE_PYTHON_RUNTIME_AUDIT_20261028.md), ZIP `de99f708f1120680028b4533a645f248e3e5ff44818ecccf7d573b7fc8525586` |
| Phi a3 | Python3.12 có venv nhưng thiếu ensurepip, chọn worker thất bại | CONFIRMED: coi ensurepip là essential và venv mặc định cần nó | `venv --without-pip --copies`, pip wheel hash-lock vào đúng interpreter; FAILED_PRELEDGER, attempt_consumed=false | G2 real fresh-venv/pip bootstrap + pip check, không chỉ import venv; metadata/storage PASS bỏ sót bootstrap | [Runtime audit](https://github.com/tantdna2/SafeShift/blob/67fc1ffc9519e068072644e0f891932fed28f463/docs/KAGGLE_PYTHON_RUNTIME_AUDIT_20261028.md), ZIP `05cc071ec11384e25c9e2187a7be89141ba351bb2c05c83a5cffe066a574b088` |
| Phi a4 | Load dùng FA2 dù kwargs yêu cầu eager | CONFIRMED trong CPU reproduction: checkpoint config/vision dispatch khác request | Shared loader/config explicit + native regression; ATTEMPT_CONSUMED | G2 production loader với config pin, mọi decoder/vision layer; kwargs/meta/import-only PASS không kiểm dispatch thật | [Phi end-to-end §incident](https://github.com/tantdna2/SafeShift/blob/67fc1ffc9519e068072644e0f891932fed28f463/docs/PHI_KAGGLE_END_TO_END_143.md) |
| Phi a5 | Hai shards load nhưng 0 ảnh; vision attention drift SDPA | CONFIRMED cơ chế CPU: AutoModel dynamic module re-exec mất patch CLIP; đối chiếu bundle giới hạn theo report | Direct reviewed shared loader; ATTEMPT_CONSUMED, fix CODE_PASS không sửa behavior a6 | G2 actual loader + class/config/provenance 32 decoder/24 vision; test constructor trước đó bỏ sót **AutoModel reload path** | [Phi end-to-end](https://github.com/tantdna2/SafeShift/blob/67fc1ffc9519e068072644e0f891932fed28f463/docs/PHI_KAGGLE_END_TO_END_143.md), ZIP `b7041c9fe174d06d34d000aee276824bc2cfb9d92698e3cdc78dcdb74a30192f` |
| Phi a6 | 160/160 real calls, 0 valid C1; max64, 8 sequences, một sequence lặp 142 lần; HNLO validated=0 | CONFIRMED format/repetition và HNLO exclusion; **UNKNOWN** model vs integration/prompt nguyên nhân | REAL_GPU_PASS trong envelope đã chạy; CLASSIFICATION_VALID=0/160, HNLO_VALID=0; CONSUMED / NO_GO_FULL_TRAIN; #147 riêng | G3 negative scripted repeat/invalid + G5 **behavior stop được duyệt**; CPU/native-scripted và first12 technical PASS đều không kiểm output model thật | [ChatGPT Phi a6](https://github.com/tantdna2/SafeShift/pull/144#issuecomment-6480224537), ZIP `19b9c201bde2c018b501b5eefd4cd00f8f4f6e9b7fe92b9cd79e6a9bfcfdb161` |
| Smol native CPU readiness #145 | Native processor ImportError, thiếu num2words/docopt | CONFIRMED CPU reproduction ở stack thật | Pin num2words 0.5.14/docopt 0.6.2, production shared path; CODE_PASS, không gọi là Kaggle failure | G2 actual processor/template + ảnh tổng hợp; import/meta/empty-weight constructor trước đó chưa thử processor đầy đủ | [Smol readiness](https://github.com/tantdna2/SafeShift/blob/67fc1ffc9519e068072644e0f891932fed28f463/docs/SMOL_KAGGLE_READINESS_145.md) |
| Smol a2 | 160 real calls; 107 valid đều Level01, 53 INVALID, chỉ 2 responses; HNLO=0 | CONFIRMED: 107 valid không khớp first-token/full continuation của frozen candidate surfaces; **UNKNOWN** căn nguyên collapse, không chứng minh bỏ qua ảnh | CONSUMED / NO_GO_FULL_TRAIN; valid format 107/160, quality không đạt; HNLO_VALID=0; không đổi surfaces hoặc strip punctuation để cứu | G3 all-level/INVALID/EOS/no-EOS/surface mismatch tests; G5 validity/diversity+GT-specific quality gate cần duyệt. 205 CPU PASS và first12 technical PASS vẫn bỏ sót behavior và actual surface | [ChatGPT Smol a2](https://github.com/tantdna2/SafeShift/pull/146#issuecomment-6485519647), ZIP `b1db13f4b7d788c1afb98e1cc3e4fc1d87715a7c876a233807009ab84e32ae7b` |
| Gemma source audit | 10 config/tokenizer resources HTTP 401; README public | CONFIRMED thiếu authenticated source evidence; trạng thái quyền tài khoản cụ thể UNKNOWN | BLOCKED_SOURCE_TOKENIZER_AUDIT_INCOMPLETE, chưa GPU failure, không tự tạo locks/grant | G2 read/hash toàn allowlist trước remote import/weights; public card/ID/revision PASS không là access PASS | [Gemma gate](https://github.com/tantdna2/SafeShift/blob/67fc1ffc9519e068072644e0f891932fed28f463/docs/SMOL_KAGGLE_READINESS_145.md#gemma-and-handoff-boundary) |
| Qwen3 pilot8 V2 dataset discovery | 0/8, không tìm được nested Kaggle mount trước image-byte/load | CONFIRMED code V2 chỉ immediate mounts; triệu chứng do Owner báo, không tự re-audit artifact | V3 bounded discovery được sửa lịch sử; source mới vẫn phải nghiệm thu; historical order consumed trước discovery | G1/G3 synthetic nested mount/ambiguous/alias + G4 read-only preflight; V2 previous test PASS **không có count trong nguồn**, bỏ sót layout `datasets/owner/slug` | [V3 evidence](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/resource_pilot8_dataset_path_v3_20261019.md) |
| Qwen3 V4 S2 / Recovery224 | OOM; toàn V4 3539/3763 SUCCESS, 1 error, 223 NOT_ATTEMPTED; recovery riêng | OOM quan sát CONFIRMED ở evidence được dẫn; allocator fragmentation/failed GPU/allocation nguyên nhân **UNKNOWN** | Không pooling recovery; attempt cũ consumed; rerun cùng identity trong forensic history không thành quyền | G2 shape/context assertions + G5 representative envelope/peak each GPU; synthetic/small resource probes không bảo đảm long-run allocator behavior, không hứa ngăn mọi OOM | [S2 forensics](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/qwen3_s2_oom_20261022.md), [V4 receipt](SOURCE_FEASIBILITY_RECEIPT_20261024.json) |
| InternVL3 guarded CUDA driver lookup, 18/10 | Driver files có nhưng SONAME load failed; no cuInit | CONFIRMED file visibility vs loader path/cache mismatch; numeric error35 không đủ kết luận driver cũ | Historical loader repair có scope riêng; diagnostic complete ≠ CUDA_PASS; không đem legacy repair vào new runtime | G4 worker thực sau isolation, driver receipt trước weights; host nvidia-smi/dependency checks không kiểm child loader. Số previous PASS không có trong receipt → UNKNOWN | [Driver audit](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/internvl3_driver_loading_20261018.md), archive `fdea5bed1b0b75edd6aee63735934c0815ad696b74bbb7de2df513de8ff017a5` |
| Qwen2.5 failed Shard0 / R2 diagnostic | FP16 nonfinite first-step logits tại merger boundary | CONFIRMED theo Lead GPU probes: nonfinite boundary và scoped mitigation trên hai trường hợp; phép toán sinh -Inf **UNRESOLVED** | R2 là experiment riêng theo decision lịch sử; không áp clamp mới ở #137/không pooling failed shard | G3 NaN/Inf custody + G5 first-image finite/stop; CPU tests không chứng minh actual activation range; previous count UNKNOWN | [R2 runbook](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_r2_runbook.md), [CPU completion](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_r2_cpu_completion_20261015.md) |
| Moondream load smoke 26/09 | ValueError tại load, 0 query/detect, thiếu message/traceback | **UNKNOWN / NOT_UNIQUELY_IDENTIFIED**; supplied run evidence, execution SHA không có trong report | Historical FAIL_T4_RUNTIME_INTERFACE giữ nguyên; diagnostic PREPARED_NOT_RUN ở tài liệu này, không nhận đã sửa | G2 production loader/provenance, G3 error chain/redaction/partial retention; snapshot/GPU/deps PASS vẫn không xác định failing load stage | [Load diagnostic](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/w2_moondream_load_diagnostic.md) |

Phi a1 chỉ có consumption trong hồ sơ đọc, không đủ symptom/root-cause để bịa thêm.
Qwen3 sequence/image-shape failures được nhắc trong chỉ thị nhưng chưa có exact
incident receipt trong tập nguồn mục tiêu đã đọc: **INSUFFICIENT_EVIDENCE**, không
ghi nguyên nhân CONFIRMED; vẫn bắt kiểm envelope/token/shape tại G2/G5. Register
không giả là toàn bộ lịch sử. #147 giữ chẩn đoán Phi/Smol riêng; #148 ON HOLD tới
khi cấu trúc/release gates được review và Owner quyết định. Không mở raw archive
chỉ vì đường dẫn/receipt tồn tại trong tài liệu này.

## Release gates G0–G6: người chịu trách nhiệm, bằng chứng, stop

| Gate | Nghiệm thu bắt buộc / fail closed | Bằng chứng và giới hạn |
| --- | --- | --- |
| G0 Science + authority | Research Lead duyệt exact protocol/method/data rights/model/revision/source/manifest/cohort/preprocess/parser/metric, counts/stop và scope run/attempt; reviewer phân biệt PROPOSED/FROZEN. Trước chuẩn bị GPU phải có grant riêng hợp lệ, ledger hiện hành; không đọc nội dung private grant ở task này | Thiếu bất kỳ quyền → BLOCKED; command CPU không tạo/validate/thay grant, không tự ký review. Pilot grant cũ không cấp thesis run |
| G1 Git + notebook | Reviewer kiểm source clean exact SHA, review diff, reproducible builder/embedded payload/metadata; compile tất cả cells/source, outputs/counts rỗng, hashes, no aliases/credentials/stale imports; Save & Run All fresh-session, không Owner edit path/SHA/cell | CLI bên dưới xuất snapshot SHA, so byte sáu notebooks từ **builder hiện có**, không exec cells. Clean exported commit không xác nhận branch hiện hành sạch hoặc merged/reviewed; reviewer kiểm riêng. Pattern secret scan có giới hạn |
| G2 Source + environment | Source allowlist hashes/remote code/checkpoint metadata, gated access kiểm không log token; fresh approved CPython/Torch/Transformers/CUDA/deps, pip check/freeze/import thực. Native loader + processor **production shared path**, synthetic portrait/landscape/1×1/large/RGB/RGBA/PNG-under-jpg; image tokens/masks/dtypes/context/prompt hash, effective attention từng decoder/vision layer | Tái dùng source/tokenizer audits và Phi/Smol rehearsals đã có. Không cài nặng/tải source tự động từ CLI stdlib. Lần này native path **NOT_RERUN / REQUIRES_PINNED_CPU_ENV**; metadata và meta không chứng minh real weights/VRAM. Smol 4.51.3/Phi 4.43.3, không tự dùng latest; no ensurepip assumption |
| G3 Failure + custody | Tái dùng tests runner/artifacts/hnlo/bootstrap/output diagnostics: all four labels/INVALID, strict duplicate/extra JSON, EOS/no-EOS/max tokens/repetition/collapse, prefix/surface mismatch, NaN/OOM/CUDA/error at load/decode/parse/write/report/export, ENOSPC/partial raw/ledger/zip/CRC/member hashes/sidecar/no overwrite | Raw phải durable trước parse; ghi known/unknown cause, redacted traceback không locals. Scripted CPU outcomes ≠ behavior thật. Native opt-ins SKIP phải hiển thị, không gọi full path PASS. ENOSPC/hard-kill có thể ngăn receipt mới; giữ bytes đã ghi, không bảo đảm archive hoàn chỉnh |
| G4 Kaggle preledger | Đúng saved VM: runtime/interpreter/isolation, storage/RAM/T4×2, GPU0 free và per-GPU memory, nguồn/inputs/grant hashes/secret access read-only, no stale cache. Repeat before ledger rồi worker checks sau ledger | **REQUIRES_AUTHORIZED_GPU/VM**; no GPU/session khác model failure. Storage/venv/source checks trước consumption nơi kỹ thuật cho phép; sau consumption mọi error giữ consumed. 2×16 GB không là 32 GB pooled |
| G5 Small real-GPU qualification | **Chỉ sau approval/grant riêng**: image envelope có quyền, staged counts/maximum duration/stop rules chốt trước; first-image → stage nhỏ behavioral → review rồi mới large. Đo raw, valid/INVALID, diversity/repetition, GT-stratified errors khi có quyền, candidate alignment nếu HNLO, memory/latency/cost | **REQUIRES_AUTHORIZED_GPU**. First12 technical không thay format/behavior; không dùng 12 hoặc 160 như số mới mặc định. Không buộc xuất đủ bốn nhãn trên batch nhỏ; collapse là cảnh báo cần support/GT và tiêu chí đã duyệt. Không retry tự động hoặc đổi parser/prompt/precision để cứu |
| G6 Release + postrun | Reviewer ký matrix theo exact hashes/versions và scope; readiness review trước grant, executable release chỉ sau **một private grant** đúng scope; sau run reconciliate planned statuses/raw, CRC/outer+member SHA/manifest/source, archive sidecar/partial evidence/consumption. Không đóng gói weights/private ảnh/GT vào public output | `READY_FOR_GPU` chỉ reviewer ghi khi G0–G4 đủ; `REAL_PILOT_PASS` chỉ G5 thật theo rule; `NO_GO` khi failed criterion; HNLO_VALIDATED và utility riêng. GPU pilot PASS không tự cho large run, cần authority riêng. No overwrite/no implicit resume |

## Một command CPU, dùng lại hệ thống hiện có

Từ repository root của PR #137 sau tích hợp, PowerShell/bash lấy full SHA HEAD (review theo đúng commit; output phải mới):

```console
python -B -m scripts.check_notebook_release --runtime-ref $(git rev-parse HEAD) --output data/processed/release_gate_20261029/integrated.json
```

Command xuất Git snapshot vào thư mục tạm, chạy chính
`scripts/build_three_vlm_notebooks.py::notebook`/`pilot.contract::source_files`
và bộ unittest của snapshot; so bytes/payload/source digest của sáu notebook.
Nó không tạo worktree/branch, không ghi sáu notebook hoặc nhập lại pipeline vào #137.
Chỉ chạy trusted reviewed repository code, không dùng như sandbox cho repo lạ.
Gỡ env opt-in native/live/pip, đặt offline/no-visible-CUDA; không gọi source probes,
native model loader/forward, tokenizer download hay Kaggle. Env này không phải OS firewall.

Exit 0 = `CODE_PASS` cho checks thực chạy, **release_status luôn BLOCKED** vì tool
không xác nhận quyền/human signatures/native environment/GPU. Exit 2 = FAIL hoặc
BLOCKED (ví dụ ref thiếu builder); receipt ghi lý do. Output phải mới; file đã có
bị từ chối. JSON ghi checker hash/runtime SHA, snapshot/source/notebook hashes,
CPU Python/platform, suite counts + skip reasons + log hashes, từng gate và limits. Không đăng raw/private
receipt; log CPU chứa fixture tổng hợp, evidence đầy đủ giữ local ignored.

Native CPU nghiệm thu dùng **rehearsal sẵn có** trong exact approved runtime checkout:
`scripts.rehearse_phi_end_to_end`, `scripts.rehearse_smol_end_to_end`, cùng
`pilot_source_audit`/`pilot_tokenizer_audit`; reviewer cung cấp snapshot public đã
hash-lock, pinned env, đúng scope trước khi chạy. Không biến chúng thành duplicate
runner mới. G5 chỉ là thiết kế trong PR này, không cài early behavior stop vào six
released notebooks hoặc đổi frozen thresholds. Issue #147 không được tự khép.

## Kết quả trước tích hợp, HEAD 68b875b, 29/10/2026

Windows / CPython 3.11.9: branch suite **68 PASS**, gồm 17 tests wrapper mới;
exact main snapshot suite **211 discovered = 192 PASS + 19 SKIP, 0 failures/errors**.
Six notebooks khớp builder/payload/source inventory và compile PASS, không chạy cells.
19 SKIP gồm 6 Phi native, 9 Smol native, 1 network/pip bootstrap và 3 Linux-only
filesystem/allocation checks. Interpreter hiện tại không cài Torch/Transformers;
không cài thêm hoặc tải source/weights để biến SKIP thành PASS. G2 native production
path chưa rerun; G3 native failure rehearsal chưa rerun; G4/G5 chưa chạy Kaggle/GPU.

Receipt local ignored: `data/processed/release_gate_20261029/final_v2.json`, SHA-256
`15b06916127dea6dbf609cce8889fb4ed5f2d0cd2892f31b0b0357b73171bed6`;
checker SHA-256 `ccffd82668b420fa5b530573b7585af81e322e426826fb4b24afa6ee78adf701`,
runtime embedded source `1d76c3a4e5cf9c5fe32d6fd94b846a2879eca268a6023ce34203794dc801d884`.
CODE_PASS chỉ phạm vi trên; release_status=BLOCKED. Bản thân receipt giữ đầy đủ
skip reasons/logs/checksums để reviewer phân biệt test đã chạy với test chỉ có code.
Các lượt phát triển wrapper trước receipt này có lỗi encoding/thiếu scratch directory
trong Git export, đã sửa ở wrapper, không sửa runtime hoặc che thành PASS; chúng
không là Kaggle attempts. Không đưa các local logs vào Git.

## Tích hợp main và bàn giao

[ChatGPT 29/10](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6487634755)
đã cho phép merge `origin/main` (`67fc1ffc9519e068072644e0f891932fed28f463`)
vào đúng branch #137 bằng merge commit. Chỉ conflict `docs/PROJECT_STATE.md`,
đã reconcile facts #138–#146/bundle/Phi a6/Smol a2 và thesis PROPOSED; không
rebase/force-push hoặc merge PR vào main. BASE/merge-base mới là main trên;
BASE gốc `28fdf82512577f2ed0fb435fb2c12b88e82baf2f` giữ trong lịch sử PR.
Kết quả trước tích hợp ở mục trên chỉ là receipt lịch sử. Phải chạy toàn suite
và command trên **chính integrated commit**; HEAD/merge parents/test counts và
receipt SHA ghi PR body để tránh self-referencing commit. PR phải chỉ có năm
paths được duyệt so latest main; protected science/runtime/notebooks giống main.
Native/GPU gaps vẫn chặn release, không được che bằng CODE_PASS.

Kết quả thực chạy, SHA và inventory cuối ghi ở PR body. ChatGPT kiểm GitHub HEAD/diff,
sau đó kiểm toán khoa học độc lập **và code gate mới** trước bất kỳ merge. Kế hoạch
ngang hàng ở [THESIS_EXECUTION_PLAN_2026](research/THESIS_EXECUTION_PLAN_2026.md)
vẫn PROPOSED; tiêu chí số và quyền ở O1–O8 chưa tự được cấp.
