# Hai notebook candidate160 — biên bản CPU thực chạy

29/10/2026, Asia/Bangkok. **CODE/CPU CHECKS PASS trong phạm vi dưới đây;
execution release BLOCKED. Actual GPU/weights/behavior/HNLO UNVERIFIED.**
Kết quả do Codex thực chạy, không CI, ChatGPT-rerun hoặc independent audit.

PR #151 được kiểm GitHub `merged=true`, merge/base
`95eb4e8801ea746e1a760b9d529920bffb3c26cb`; main vẫn đúng SHA này ở lần kiểm cuối.
Nhánh mới `prep/candidate160-20261029`, worktree độc lập; không thay workspace cũ.
Không có API tạo chat Codex mới; isolation ở mức nhánh/worktree.

## Source đã thực chạy

- Runtime source commit notebook: `56898c492fde1a962237f11058f1f78bee281122`.
- Commit chứa hai notebook: `8e4a47f9a8342c518eff9c76c22445fe0118ed89`.
- Toàn bộ bốn native receipts và hai release checks ghi Git commit
  **`aae742352f647263524d5c5f1dbeb47ee5ec5d14`**. Commit này bổ sung release
  checker tám notebook; embedded runtime/test sources của bốn native lượt giữ
  nguyên trong lúc chạy, từng file có SHA trong receipts.
- Embedded candidate source SHA256:
  `471236817cb5723e73c06c186ede72208226c02f3c9bbd13ee6cc1ab193aae23`.
- Pilot source digest cũ giữ nguyên
  `1d76c3a4e5cf9c5fe32d6fd94b846a2879eca268a6023ce34203794dc801d884`.
  Adapter PR #151, C1/generation/parser/HNLO và sáu notebook cũ không thay bytes.

Không dùng self-referential notebook SHA: builder kiểm mọi payload byte bằng
`git show <runtime_ref>:<path>`, rồi commit notebooks/docs/evidence phía sau.
Git HEAD bàn giao cuối ghi PR body; sau commit nghiệm thu chỉ thêm docs/receipts
và sửa docstring checker cho đúng scope, không đổi logic runtime/tests/notebooks.
Không nhận docs commit là một lượt native mới.

## Kết quả nghiệm thu cuối

| Lượt thực chạy | Tổng | PASS | SKIP | FAIL/ERROR |
| --- | ---: | ---: | ---: | ---: |
| InternVL, isolated Windows CPU | 60 | 57 | 3 | 0/0 |
| MiniCPM, isolated Windows CPU | 60 | 57 | 3 | 0/0 |
| InternVL, isolated Linux CPU | 60 | 59 | 1 | 0/0 |
| MiniCPM, isolated Linux CPU | 60 | 59 | 1 | 0/0 |
| Exact Git export, full Windows suite | 289 | 252 | 37 | 0/0 |
| Exact Git export, full Linux suite | 289 | 257 | 32 | 0/0 |

**Cả15 native integration tests PASS cho mỗi model trên mỗi OS**, gồm hai test
mới:160 ảnh tổng hợp qua production CandidateBackend/native processor/generation
scripted/Store/parser/HNLO/report/archive; corrupt image bị chặn trước native call.
Không real VLM forward, tensor weights thật hoặc GPU. Empty/meta constructors
và file safetensors rỗng là kiểm phần mềm, không actual checkpoint validation.

Windows focused SKIP3 là real symlink tests thiếu OS permission; real junction
test PASS. Linux SKIP1 là Windows junction. Full Windows SKIP37 = candidate15,
Phi6, Smol9, live pip-bootstrap1, Windows symlink3 và Linux filesystem3. Full Linux
SKIP32 = candidate15/Phi6/Smol9/live pip1/Windows junction1. Candidate15 có receipts
native riêng bên trên; không nâng Phi/Smol/live bootstrap chưa rerun thành PASS.

Hai release checkers trả **CODE_PASS / release_status=BLOCKED**. Kiểm đúng8
notebook, cell IDs/JSON/AST/outputs/counts, mọi embedded source, builder bytes,
SHA/source inventory/config/pins và mutation checks. Candidate cells được thực
thi trên CPU trong thư mục tổng hợp, không grant; kết quả mong đợi **BLOCKED,
attempt_consumed=false**, archive/sidecar verify PASS. Không gọi là Kaggle run.
Sáu notebook lịch sử chỉ được byte/build/compile kiểm, không execute.

Release checker tái dùng wrapper cũ, mở rộng hai payload inventories; trong Git
export, builder/tests được cấp Git object context chỉ để đọc exact refs từ repo
gốc. Không copy dữ liệu hoặc sửa Git metadata từ test. Trusted tests không là
OS security sandbox. Trường `notebook_cells_executed` của receipt ghi rõ scope
CPU/no-grant; docstring wrapper đã được cập nhật cho đúng phạm vi này.

## CPU environment và dữ liệu kiểm

CPython **3.11.9** trên Windows và WSL2 Linux, dùng lại isolated CPU venv/public
snapshot/index đã có của #150/#151, không cài/tải source hoặc weights mới.
Native fixture kiểm lại exact CPU requirements #151, pip check/freeze, module
ownership và compiled CPU torchvision NMS: Torch2.6.0+cpu, torchvision0.21.0+cpu,
Accelerate1.6.0, NumPy1.26.4, Pillow10.4.0. InternVL TF4.55.4/tokenizers0.21.4/
Hub0.34.4; MiniCPM TF4.51.3/tokenizers0.21.1/Hub0.30.2. Required fixture setup
failure sẽ làm suite ERROR; không skip để ghi native PASS.

CUDA requirements mới chỉ PREP: Torch2.6.0+cu124/torchvision0.21.0+cu124,
CPython3.11.9, CUDA build12.4. **Không cài/kiểm actual CUDA wheel stack hoặc driver
trong task này**; không suy CPU-wheel PASS sang CUDA-wheel ABI/GPU PASS. Notebook
tự kiểm stack thật trước consumption và kiểm CUDA child sau consumption; tuple
vẫn cần approval/runtime qualification mới.

Chỉ fixture tổng hợp xác định, không random seed:160 IDs tổng hợp, PNG RGBA17×1
với extension `.jpg`, native synthetic sizes/parity/token checks từ #151. Scripted
logits/tokenizers test bốn nhãn/whitespace/INVALID/EOS/max64; không số phân loại
thật được tạo. Cả hai model test cùng synthetic160 order. Mỗi native lượt chạy
160 calls trong test mới; control-plane test cũng chạy160/model bằng character
double, độc lập với thí nghiệm thật và không tiêu external attempt.

## Phạm vi lỗi và custody đã kiểm

- Grant/ledger mới, source/model/config/ref/manifest/rights/expiry, thiếu G0/T0/O3,
  policy null/sai, TEST/supplement/count161/duplicate ID, thứ tự manifest; không
  selector hoặc mở private inventory/master/annotation.
- Cùng160 order, một checkpoint load, call cap, first image, early behavior,
  thiếu/sai/STOP review, observation-bound CONTINUE chỉ trong synthetic fixture,
  deadline trước load và NOT_ATTEMPTED tail. No overwrite/retry/resume.
- Native CPU processor/token/attention/image tests PR #151; CUDA preflight bằng
  doubles cho hai T4, nonpooled memory, wrong driver/free memory và child failure.
  Supervisor stages CPU→hardware→consume→worker, timeout/failure/recovery được
  mô phỏng và ghi scope SYNTHETIC, không giả thành actual GPU receipt.
- OOM/import/decode, NaN/Inf handling inherited tests, INVALID/duplicate JSON,
  repetition/dominance/false-safe/false-alarm criteria, token/step custody loss,
  independent CPU decoder mismatch, raw ENOSPC/checkpoint/report/ZIP errors.
- CandidateStore lưu raw trước custody validation/parser; validation failure vẫn
  giữ raw/native evidence rồi dừng. Missing/torn raw/result không thành SUCCESS;
  supervisor phục hồi planned accounting, exclusive archive/checksums/reimport.
- Failure finalizer vẫn thử export, không overwrite torn evidence. Disk/kill/VM
  loss ngoài khả năng ghi được báo giới hạn; không bảo đảm ZIP đủ nếu hết đĩa.

Các lượt phát triển không là nghiệm thu cuối: lần full đầu thiếu ignored scratch
`data/processed/` cho test cũ; một raw fault injection nhắm sai hàm ghi; fixture
MiniCPM tách lớp làm dedicated HF module cache stale. Đã sửa test/fixture, không
relax source admission hoặc adapter. Builder từng từ chối ref nhập sai và tests
đã bắt source/payload thay đổi khi development run còn mở; các lượt đó không
được nhận PASS hoặc dùng làm kết quả thật. Logs phát triển giữ local ignored.

## Receipts và tái lập

[Public index + SHA từng receipt](evidence/candidate160_20261029/index.json).
Bốn native receipts là bytes nguyên bản, có per-test events, executed-file hashes,
log hash, OS/Python/Git, source unchanged và scope. Hai release receipts là bản
sao **chỉ che temporary synthetic paths** trong stdout/stderr; `publication`
giữ original receipt SHA và đúng fields bị che. Counts/results/log hashes gốc
giữ nguyên. Không ảnh/private IDs/GT/token outputs hoặc trọng số trong receipts.

Lệnh thực chạy, từ root; `<cpu-env-python>` là Python của CPU requirements #151,
`<public-snapshot>`/`<index>` là caches public đã kiểm hash, không dataset:

```console
python -B -m scripts.build_candidate160_notebooks --runtime-ref 56898c492fde1a962237f11058f1f78bee281122
<cpu-env-python> -B -m scripts.rehearse_candidate160 --model internvl35 --snapshot <public-snapshot> --index <index> --output data/processed/candidate160/internvl35-w2
<cpu-env-python> -B -m scripts.rehearse_candidate160 --model minicpm4 --snapshot <public-snapshot> --index <index> --output data/processed/candidate160/minicpm4-w2
python -B -m scripts.check_notebook_release --runtime-ref aae742352f647263524d5c5f1dbeb47ee5ec5d14 --output data/processed/candidate160/release-windows.json
```

Linux dùng venv CPU riêng cùng requirements, outputs `internvl35-linux2`,
`minicpm4-linux2`, `release-linux.json`; không Windows venv trong Linux. WSL cần
explicit Git context tới metadata/worktree tương ứng vì `.git` của worktree do
Windows tạo dùng path Windows; không sửa config/ref. Checkout Linux thuần không
cần bước đó. Lượt Linux ban đầu bị sandbox từ chối WSL service, sau escalation
được phép đã chạy; không bypass quyền hoặc dùng GPU để khép CPU.

Các output names phía trên đã tồn tại: tái lập dùng tên output mới. Biên bản này
chỉ ghi relative paths, không hard-code machine paths. Log và receipt gốc nằm
ignored `data/processed/candidate160/`; receipts công khai có hashes trong index.

## BLOCKED / UNVERIFIED còn lại

1. ChatGPT direct review exact Draft PR HEAD/diff/receipts; independent audit khi
   được yêu cầu riêng; không tự merge hoặc ký review.
2. G0/T0/O3 và các scope liên quan, manifest reuse approval mới cho hai model,
   numerical stop/behavior/review stages/time/driver/VRAM, runtime tuple và quyền
   private data/checkpoint/GPU/export. Tất cả chưa chốt giữ null/BLOCKED.
3. Current external ledger/fresh saved-VM reservation; snapshot attach và marker
   local không là cryptographic/distributed one-shot enforcement. Phương thức
   cung cấp quyết định Lead vào saved Kaggle VM **UNVERIFIED**, không vượt gate.
4. Actual bundle/checkpoint bytes trên Kaggle, CPython3.11.9 availability, storage,
   worker CUDA/driver/isolation/T4 VRAM, real checkpoint deserialize/placement,
   finite FP16 outputs, classification quality/peer utility và empirical HNLO
   **NOT_RUN/UNVERIFIED**. Không weights/data/Kaggle/GPU được thực hiện ở task này.

[Runbook cấu hình/authority/retention](../CANDIDATE160_KAGGLE.md) mô tả các điều
kiện trước khi chạy thật. Trần160 không là quyền tự động hoặc cam kết chạy đủ160.
