# DEC-20261030-CANDIDATE160-KAGGLE-ENV — implementation chờ review

Nguồn: task trực tiếp của SafeShift Owner ngày 30/10/2026 (Asia/Bangkok),
“SỬA MÔI TRƯỜNG KAGGLE CHO INTERNVL3.5 VÀ MINICPM-V-4”, BASE
`39ec489403753ada10f4924c4b0d6077e027f5e1` (#154). Không có permalink chat được
cung cấp; không tạo approval ref/chữ ký. Phạm vi là một Draft PR, không merge,
GPU hoặc private data; ChatGPT kiểm GitHub và Antigravity audit độc lập trước merge.

Owner báo kernel3.13.15, không có3.11.9; working còn19,50 GiB/device1794,
tmp ghi/fsync được/device56, kaggle còn khoảng1.048,77 GiB/device56. Đây là
**OWNER_REPORTED**, không phải phép đo độc lập của Codex và chưa chứng minh cấp
phát đồng thời28+4 GiB. Checkpoint đã ở Notebook Output, không cần upload lại.

## Phạm vi thay đổi môi trường

Chỉ Candidate160 thêm direct mount + `notebooks/<owner>/<slug>` bên cạnh
`datasets/<owner>/<slug>` và prefix `safeshift-pilot-input/` vốn có. Không sửa
pilot discovery hoặc source lock lịch sử. Tối đa512 entries ở các tầng định
danh cố định; không quét đệ quy. Symlink/junction/hardlink/path traversal,
marker trùng/sai, source/shard không khớp đều BLOCKED.

Khi không có CPython3.11.9 đủ điều kiện, tự tải **software runtime**, không
weights, từ python-build-standalone20240726. URL/version/size/SHA256 nằm ở
`configs/candidate160/python3119.json`; tải thực tế29.713.170 bytes, hash
`f6e955dc9ddfcad74e77abe6f439dac48ebca14b101ed7c85a5bf3206ed2c53d`
khớp `.sha256` upstream. Kiểm toàn bộ table trước giải nén, giới hạn6.000
entries/100 MiB, từ chối unsafe types/links/paths/duplicates/privilege bits;
chỉ internal symlink đến regular file được chấp nhận và tạo cuối cùng.
Không thực thi archive sai size/hash. Không fallback3.13 hoặc build Python.

Probe Linux/x86_64/CPython3.11.9 và stdlib; tạo venv `--without-pip --copies`.
PBS dùng `$ORIGIN/../lib`: sao chép và kiểm SHA256 `libpython3.11.so.1.0` vào
venv/lib rồi probe lại executable/prefix/stdlib trước bootstrap pip. Không đổi
LD_LIBRARY_PATH. Pip bootstrap25.0.1 chỉ để cài pins, sau đó pinned pip24.0/
setuptools65.5.0 như cũ. Exact distributions, pip check/freeze, CUDA build12.4,
Torch2.6.0+cu124/vision0.21.0+cu124 và compiled CPU NMS phải PASS.

Không đổi scientific config/hashes, model/revision/weights, FP16/eager/batch1/
cuda:0, cohort160/order, C1/parser/HNLO/raw-before-parse. GPU1 không pooled.

## Preflight độc lập, không reservation

Hai notebook `CANDIDATE160_PREFLIGHT_*` chỉ gọi `train_preflight`; không tạo
execution record, slot, consumed marker, model output hoặc native call. Có thể
chạy lại. Đọc attached manifest/ảnh và source/index/shard hashes; không tải/nạp
weights. Cài software pinned, kiểm ABI/native empty meta/processor với ảnh tổng
hợp, hash/decode/RGB160 ảnh trong child, RAM/cgroup, storage thật, nvidia-smi
T4×2/driver và actual isolated CUDA FP16 tensor probe. Không model forward.

Receipt từng gate PASS/BLOCKED/NOT_RUN. Chỉ `PRELOAD_CHECKS_PASS_MODEL_UNVERIFIED`
khi mọi gate PASS; không READY hoặc model-fit/quality/HNLO PASS. Allocation
được thả ngay; tài nguyên có thể thay đổi. Run160 kiểm admission lại. Preflight
không cho phép replay hoặc chứng minh không có job khác ở một VM không quan sát.

## Ngoại lệ mới cho đúng một incident chưa tiêu lượt

Đây là **thay đổi hợp đồng reservation** so với #154, trình review công khai;
không sửa hồi tố hoặc xóa `BLOCKED_RESERVED_NO_RETRY` cũ. Task Owner yêu cầu phân
tích/triển khai đường thay thế chỉ khi chắc chắn chưa tiêu; implementation chọn
ngoại lệ hẹp sau đây. Hiệu lực repository/execution vẫn sau review và merge.

Incident ID: `internvl35-checkpoint-source-found0-20261030`. Chỉ InternVL,
đúng `checkpoint_source` + ValueError
`UNIQUE_candidate_checkpoint_internvl35.json_REQUIRED_FOUND_0`. Phải có original
reservation, execution, terminal, supervisor status/failure, manifest và160
accounting trong evidence directory đã sealed đủ SHA256; tất cả bindings đồng
nhất, `attempt_consumed is False`, mỗi row NOT_ATTEMPTED/attempts0/native_calls0.
Chỉ chấp nhận flat preconsumption allowlist; thiếu/partial/checksum drift,
raw/worker/consumption artifacts, consumed/unknown, nhãn hoặc counter khác từ chối.
Checksum chỉ chứng minh tính nhất quán bytes, không xác thực tác giả từ xa.

Giữ nguyên campaign/model/revision/cohort/slot hash. Tạo UUID run/attempt **mới**
và marker riêng `owner_slot_<same-slot>.replacement1.json`, O_EXCL+fsync; marker
mới bind execution mới cùng incident, original run/attempt/source/ref và sealed
evidence hashes. Consumed/terminal filenames dùng replacement1, không ghi vào
marker cũ. Fixed replacement limit1; kể cả admission mới fail cũng không có
replacement2/retry/resume. Quét cả local và attached Notebook/Dataset Output
theo đường cố định, tổng tối đa512 history entries, không walk raw/image trees.

**Không có evidence cũ đầy đủ trong task này**: Codex chỉ kiểm bằng fixtures,
không tự khẳng định lượt Owner đủ điều kiện. Owner attach saved Output cũ cùng
checkpoint; runtime tự kiểm điều kiện, không xin approval thủ công hoặc giả grant.
Nếu saved Output mất/thiếu seal/accounting, tiếp tục BLOCKED và giữ mọi evidence.
Consumed hoặc trạng thái không rõ tuyệt đối không được thay thế. Không thay
campaign để né barrier. Khóa filesystem vẫn không phải distributed ledger:
không chạy VM song song hoặc bỏ lịch sử khi chuyển VM.

Nguồn runtime: [release20240726](https://github.com/astral-sh/python-build-standalone/releases/tag/20240726),
[runtime requirements](https://github.com/astral-sh/python-build-standalone/blob/main/docs/running.rst),
[PyTorch versions](https://pytorch.org/get-started/previous-versions/).
Các phép đo CPU và giới hạn được ghi trong [runbook](../CANDIDATE160_KAGGLE.md).
