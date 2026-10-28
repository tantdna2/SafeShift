# Kaggle Phi/Smol Python runtime audit — 28/10/2026

Phạm vi là sửa code chuẩn bị môi trường, không chạy GPU/inference, không phát hành
grant và không thay giao thức khoa học. BASE là
`4693d8c1eed4e60069272b975275e6adb17905fe` (merge PR #139). Source payload sau
sửa có SHA-256 `dd79ccd2e6d870f9d643afbcfea5cde596e42f75ef545bf905d0b11c90a2add0`.

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
| Isolation | Fresh CPython prefix/site-packages | `venv --copies` mới trong scratch, loại `PYTHONPATH`, `PYTHONHOME`, user site và pip config của kernel |
| Dependencies | Exact pins, index CUDA, pip report/check và log | Giữ nguyên pins/index; đối chiếu requirements với runtime lock, `pip check`, freeze, CPU native ABI smoke |
| Cache/weights/temp | Runtime và model cache ngoài evidence | Venv, pip/HF/Torch/Triton/CUDA cache, weights và temp đều dưới `/kaggle/tmp`; receipt/log ở `/kaggle/working` |
| Worker | Khởi chạy bằng interpreter vừa build | Khởi chạy bằng đúng `venv/bin/python`; worker tự kiểm `sys.executable`, `sys.prefix`, version và site-package leakage |
| Failure evidence | Log theo phase, raw/evidence giữ khi lỗi | `runtime_preflight.json`, `environment_preflight.json`, setup log/freeze hashes, supervisor failure và ZIP exclusive |
| Attempt boundary | HNLO TRAIN lịch sử ghi consumption trước manifest/resource/software | Phi/Smol chỉ ghi ledger sau mọi gate CPU: authority/source/config, bundle, storage/resume, Python, venv, dependencies và CPU ABI |

Không sao chép hệ thống build Qwen3 vào pilot. Cách mới tận dụng interpreter Kaggle
có sẵn và giữ policy Python 3.11/3.12. Nếu không có candidate đủ điều kiện hoặc
`venv`/`ensurepip` lỗi, receipt BLOCKED được lưu và Python 3.13 không bao giờ là
fallback.

## Luồng sau sửa

1. Kernel notebook chỉ giải nén source stdlib đã hash và điều phối.
2. Trước consumption: kiểm grant/binding, source lock, requirements/runtime lock,
   toàn bộ bundle, storage và resume archive.
3. Probe từng candidate trong tiến trình riêng: CPython, Linux x86_64 64-bit,
   version 3.11/3.12 và các module thiết yếu gồm `venv`/`ensurepip`.
4. Tạo venv trong scratch, kiểm pip, cài đúng CUDA wheels rồi requirements, chạy
   `pip check`, `pip freeze`, exact-version check và CPU-only torch/torchvision/
   Transformers ABI smoke. Không gọi CUDA hoặc tải weights.
5. Chỉ sau receipt PASS mới ghi ledger attempt. Sau đó mới kiểm T4 và khởi chạy
   worker bằng đúng interpreter đã qualified.
6. Worker kiểm lại runtime identity trước source/bundle/model provisioning. Model
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

- Windows Python 3.11.9: 152 tests PASS, 3 Linux-only SKIP.
- WSL Linux x86_64 Python 3.14.4: 152/152 PASS; đây là test stdlib/code path,
  không phải runtime được phép cho dependency rehearsal.
- Builder notebook deterministic và payload parity PASS; `git diff --check` PASS.
- NOT RUN: cài dependencies thật trên Linux/Kaggle Python 3.12, model weights,
  remote Phi execution, T4/CUDA, ảnh thật, inference, HNLO runtime và retention.

Gate tiếp theo sau review/merge là chạy hai environment-preflight notebook trên
Kaggle hiện tại, tải ZIP/sidecar và audit receipt. Chỉ sau PASS mới xem xét run,
attempt và grant Phi/Smol hoàn toàn mới. Không tái sử dụng a1/a2.
