# Kaggle Phi/Smol Python runtime audit — 28/10/2026

Phạm vi là sửa code chuẩn bị môi trường, không chạy GPU/inference, không phát hành
grant và không thay giao thức khoa học. BASE là
`064e31654fa44c5ad55fdb69159692ed69b78a77` (merge PR #140). Source payload của
candidate hiện tại có SHA-256
`a87b040e4800d5d97b9f586f5319f02262759a87799f3cdb407896167dacb3b8`.

## Bằng chứng đầu vào và giới hạn xác minh

Thông tin Kaggle sau do Owner cung cấp, được dùng làm reproduction target nhưng
không được chạy lại trong task code này:

- kernel CPython 3.13.15 tại `/usr/bin/python3` trên Linux x86_64;
- `/usr/bin/python3.12` có sẵn; 3.11 và 3.14 không có;
- Phi a2: run `safeshift_phi_pilot_20261028_r2`, attempt
  `phi_pilot_20261028_a2`, ZIP SHA-256
  `de99f708f1120680028b4533a645f248e3e5ff44818ecccf7d573b7fc8525586`;
  160/160 ảnh, admission 28+4 GiB và hai T4 PASS; dừng tại
  `BLOCKED_PINNED_LINUX_PYTHON_311_OR_312_REQUIRED`, 0/160 inference.
- Phi a3 do Owner cung cấp: kernel CPython 3.13.15; `/usr/bin/python3.12` là
  CPython 3.12.3 Linux x86_64; `venv`, SSL, zlib, lzma, sqlite3 và các module
  thiết yếu khác PASS, chỉ `ensurepip` trả `ModuleNotFoundError`; Python 3.11
  không tồn tại. 160/160 ảnh và storage 28+4 GiB PASS, nhưng
  `runtime_preflight.json` dừng ở
  `BLOCKED_NO_QUALIFIED_PINNED_LINUX_PYTHON_311_OR_312`. Chưa tạo venv/cài
  package; `attempt_consumed=false`. ZIP SHA-256
  `05cc071ec11384e25c9e2187a7be89141ba351bb2c05c83a5cffe066a574b088`.

Phi a1/a2 là lịch sử đã tiêu thụ, không được tái sử dụng. Task này không mở hoặc
chạy grant mới. WSL local chỉ có Linux x86_64 Python 3.14.4; không có 3.11/3.12,
vì vậy không có điều kiện hợp lệ để chạy dependency rehearsal thật trên 3.12.
Không dùng mock làm bằng chứng Kaggle và không tải/build thêm Python để lấp chỗ trống.

## Đối chiếu Qwen3 snapshot `31a04e6`

Đã đọc trực tiếp `one_click/provision.py`, `hnlo_train/orchestrate.py`,
`hnlo_train/bootstrap.py`, notebook Qwen3 shard 0 V4 và build config tại đúng
snapshot. Các nguyên tắc được áp dụng có chọn lọc:

| Trục | Qwen3 lịch sử | Phi/Smol sau sửa |
| --- | --- | --- |
| Python | Tải source CPython 3.12.13 đã khóa SHA-256 và compile prefix độc lập | Ưu tiên `/usr/bin/python3.12`, rồi 3.11 hợp lệ; kiểm tiến trình con, không chấp nhận 3.13 |
| Khi Python hệ thống không đủ | Có build recipe đã review riêng, kể cả zlib khóa cho Qwen3 | Fail closed; không tự tải/build. Chỉ đề xuất port recipe đã khóa trong review riêng nếu Kaggle 3.12 không đạt |
| Isolation | Fresh CPython prefix/site-packages | `venv --without-pip --copies` mới trong scratch; pip wheel khóa URL/size/SHA cài đúng target bằng `pip --python`; loại `PYTHONPATH`, `PYTHONHOME`, user site và pip config của kernel |
| Dependencies | Exact pins, index CUDA, pip report/check và log | Giữ nguyên pins/index; đối chiếu requirements với runtime lock, `pip check`, freeze, CPU native ABI smoke |
| Cache/weights/temp | Runtime và model cache ngoài evidence | Venv, pip/HF/Torch/Triton/CUDA cache, weights và temp đều dưới `/kaggle/tmp`; receipt/log ở `/kaggle/working` |
| Worker | Khởi chạy bằng interpreter vừa build | Khởi chạy bằng đúng `venv/bin/python`; worker tự kiểm `sys.executable`, `sys.prefix`, version và site-package leakage |
| Failure evidence | Log theo phase, raw/evidence giữ khi lỗi | `runtime_preflight.json`, `environment_preflight.json`, setup log/freeze hashes, supervisor failure và ZIP exclusive |
| Attempt boundary | HNLO TRAIN lịch sử ghi consumption trước manifest/resource/software | Phi/Smol chỉ ghi ledger sau mọi gate CPU và receipt `nvidia-smi` PASS; SHA-256 GPU receipt được bind vào ledger |

Không sao chép hệ thống build Qwen3 vào pilot. Cách mới tận dụng interpreter Kaggle
có sẵn và giữ policy Python 3.11/3.12. `ensurepip` được quan sát nhưng không còn
là điều kiện chọn interpreter: Python phải có `venv` và các module stdlib/ABI
thiết yếu, sau đó pip được bootstrap độc lập như phần dưới. Không có candidate đủ
điều kiện, controller pip không hỗ trợ cơ chế đã review, hoặc bootstrap thất bại
thì receipt BLOCKED được lưu; Python 3.13 không bao giờ là worker/fallback.

## Nguyên nhân gốc và phương án chọn

`probe_interpreter()` trước PR này xếp `ensurepip` vào `ESSENTIAL_STDLIB`, nên
3.12.3 a3 bị loại trước khi `select_interpreter()` có thể chọn nó. Chỉ bỏ điều
kiện đó vẫn sai: `prepare_runtime()` gọi `venv --copies` mặc định, và `venv` sẽ
gọi module `ensurepip`, nên vẫn thất bại trước pip/package checks.

Candidate sửa dùng luồng được tài liệu Python/pip mô tả cho môi trường không có
pip: `python3.12 -m venv --without-pip --copies`, sau đó supervisor pip có tính
năng `--python` (tối thiểu 22.3) chỉ làm controller để cài vào đúng
`venv/bin/python`. Nó không chạy như package installer trong worker và không cài
bất kỳ dependency model nào từ Python 3.13. Nguồn bootstrap là wheel PyPI
`pip-25.0.1-py3-none-any.whl`, URL trực tiếp, size 1.841.526 byte và SHA-256
`c46efd13b6aa8279f33f2864459c8ce587ea6a1a59ee20de055868d8f7688f7f` được khóa
trong source payload. Download dùng stdlib, giới hạn byte, yêu cầu URL cuối chính
xác và hash PASS trước thực thi; install dùng local-only `--no-index`,
`--require-hashes`, `--no-deps`, `--only-binary`.

Sau bootstrap, chính worker Python import/đối chiếu pip 25.0.1, executable,
`sys.prefix`, distribution root và `pip.__file__`; bất kỳ path Python 3.13/ngoài
venv đều BLOCKED. Từ đó CUDA wheels, requirements, `pip check` và `pip freeze
--all` đều chạy bằng `venv/bin/python`. Không dùng `get-pip.py` hoặc pip zipapp;
không có script Internet nào được tải rồi chạy. Build CPython chính thức theo
Qwen3 vẫn chỉ là fallback cần review riêng nếu cơ chế này không PASS trên Kaggle.
Nguồn chính thức: [Python 3.12 `venv`](https://docs.python.org/3.12/library/venv.html),
[pip `--python` cho venv không có pip](https://pip.pypa.io/en/stable/topics/python-option/),
và [PyPI JSON pip 25.0.1](https://pypi.org/pypi/pip/25.0.1/json).

## Luồng sau sửa

1. Kernel notebook chỉ giải nén source stdlib đã hash và điều phối.
2. Trước consumption: kiểm grant/binding, source lock, requirements/runtime lock,
   toàn bộ bundle, storage và resume archive.
3. Probe từng candidate trong tiến trình riêng: CPython, Linux x86_64 64-bit,
   version 3.11/3.12 và các module thiết yếu gồm `venv`, SSL/compression/sqlite;
   ghi riêng trạng thái `ensurepip`.
4. Tạo venv `--without-pip --copies`; tải/kiểm wheel pip đã khóa rồi cài vào
   target bằng supervisor `pip --python`. Xác minh pip thuộc target trước khi cài
   đúng CUDA wheels rồi requirements; chạy `pip check`, `pip freeze --all`,
   exact-version check và CPU-only torch/torchvision/
   Transformers ABI smoke. Không gọi CUDA hoặc tải weights.
5. Kiểm T4×2/GPU0 free ≥14 GiB bằng `nvidia-smi`, ghi GPU/environment receipt
   PASS rồi mới ghi ledger attempt độc quyền. Lỗi phần cứng/lệnh/ghi receipt giữ
   BLOCKED, `attempt_consumed=false`, không tạo ledger, xuất evidence/partial ZIP.
6. Worker dùng đúng interpreter đã qualified và giữ kiểm CUDA FP16 thật sau
   consumption; `nvidia-smi` không chứng minh CUDA hay model chạy được.
   Worker kiểm lại runtime identity trước source/bundle/model provisioning. Model
   snapshot, weights và Phi remote code vẫn dùng revision/source lock hiện hành.

Hai notebook `SafeShift_ENVIRONMENT_PREFLIGHT_phi.ipynb` và
`SafeShift_ENVIRONMENT_PREFLIGHT_smolvlm2.ipynb` chạy cùng code production nhưng
không đọc grant/dataset, không ghi attempt, không gọi GPU và không tải weights.
Chúng là bước One-Click bắt buộc nên chạy trên Kaggle image dự kiến trước khi một
grant mới được xem xét. PASS chỉ xác nhận môi trường CPU tại thời điểm đó.

## Giao thức bất biến

Không đổi 160 TRAIN IDs/manifest, model/revision, dependency pins, CUDA 12.4,
FP16/eager, Phi 16 crops, batch 1, greedy max64, prompt, parser, raw-first, HNLO,
metric, thresholds, nhãn hoặc giới hạn TEST/FULL TRAIN. Gemma vẫn BLOCKED bởi
source/tokenizer audit; không được mở quyền qua thay đổi runtime này.

## Kiểm thử và bằng chứng chưa có

- Rehearsal CPU thật Windows Python 3.11.9: tạo venv `--without-pip`, download
  wheel đúng URL/hash, `pip --python` cài thành công pip 25.0.1 và target identity
  PASS. Đây chỉ kiểm cơ chế bootstrap, không phải Kaggle/Linux PASS.
- Full Windows suite: 169 tests, 165 PASS + 4 platform/opt-in SKIP; opt-in real
  bootstrap ở dòng trên chạy riêng 1/1 PASS.
- Full WSL Linux Python 3.14.4: 169 tests, 168 PASS + 1 opt-in network SKIP;
  kiểm POSIX thật nhưng không phải Python version đủ điều kiện của worker.
- Tests fault-injection bao phủ thiếu bootstrap, hash sai, package install lỗi,
  rò Python 3.13, thiếu storage và lỗi ghi runtime receipt cho cả Phi/Smol.
- Builder notebook deterministic và payload parity PASS; `git diff --check` PASS.
- NOT RUN: cài dependencies thật trên Linux/Kaggle Python 3.12, model weights,
  remote Phi execution, T4/CUDA, ảnh thật, inference, HNLO runtime và retention.

Gate tiếp theo sau review/merge là chạy hai environment-preflight notebook trên
Kaggle hiện tại, tải ZIP/sidecar và audit receipt. Chỉ sau PASS mới xem xét run,
attempt và grant Phi/Smol hoàn toàn mới. Không tái sử dụng a1/a2. A3 là BLOCKED
trước consumption và không tự trở thành quyền chạy; việc định danh attempt tiếp
theo vẫn cần quyết định/grant được review, không suy từ receipt a3.

## Delta sau audit PR #140

Owner đã cung cấp phát hiện LOW trong báo cáo Antigravity
`Pasted markdown(20261028-122905).md`: HEAD `84837807ef6fcae1ef7658ef1c54fc2df3eb0cc8`
ghi ledger trước `gpu_preflight()`, gây tiêu thụ attempt nếu Kaggle cấp sai hoặc
thiếu GPU. Audit PASS được báo cho HEAD đó; delta này vẫn chờ ChatGPT kiểm và
Antigravity audit trong session cũ, không tự kế thừa PASS.

Đã chuyển quan sát `nvidia-smi` cùng receipt/host metadata lên trước ledger.
Receipt lưu raw output, return code, GPU observations và lỗi; supervisor failure
còn giữ observation nếu receipt write lỗi, partial file/ZIP không bị ghi đè.
Ledger chỉ được ghi sau receipt PASS, bind cả GPU và environment receipt hashes.
Sáu tests mới bao phủ đúng/sai/thiếu GPU, VRAM, command failure/timeout, receipt
write/torn và thứ tự CPU → GPU → receipts → ledger → worker cho Phi/Smol.
Mọi tình huống phần cứng trong tests đều mô phỏng; task không gọi GPU hoặc CUDA.
