# Candidate160 — CPU nghiệm thu sau review provenance PR #152

29/10/2026, Asia/Bangkok. Cùng Draft PR #152, theo
[review ChatGPT](https://github.com/tantdna2/SafeShift/pull/152#issuecomment-6501983735).
Không merge, grant, Kaggle, GPU, trọng số thật, suy luận VLM hoặc private TRAIN/TEST.

## Source và phạm vi sửa

- HEAD đã review: `65da8a3dfd19c7f61b3e1a48465d1db7c97bdaac`.
- Base/main: `95eb4e8801ea746e1a760b9d529920bffb3c26cb`, sau PR #151 MERGED.
- Runtime source mới: **`820200bba7c6f5796961acb64befef0c651772b3`**.
- Notebook/release commit nghiệm thu mới: **`c75113f4a62d8d30303269f4a8bd72fc71040c15`**.
- Embedded source SHA256:
  **`3b63d9cf92df66042cbd201861c50ab8f0cfd0b4d1a57d194493faf33c24524e`**.
- Sau commit nghiệm thu chỉ cập nhật docs/receipts, không đổi logic runtime/tests/
  builder/notebooks để dùng lại kết quả. HEAD bàn giao cuối ghi trong PR body.

Config v2 giữ exact `pilot.settings(key)` trong `legacy_transport_compatibility`
với scope **historical, not effective**. Phi cropping, pilot contract/selection
seed và descriptor outer-forward ở đây chỉ là tương thích transport lịch sử.
`effective_candidate` mô tả đúng native preprocessing, generation, logits boundary
và sequence semantics của từng candidate PR #151. Grant v2/Store/raw/recovery
phân biệt hai hash và từ chối trường candidate `config_sha256` mơ hồ.

Không thay nguồn khoa học đã khóa: pilot contract/runner/Store/parser/HNLO/metrics,
adapter PR #151, source/checkpoint/dependency locks, C1, nhãn, manifest160/thứ tự,
checkpoint revisions hoặc stop policy. Git blob/diff và exact function-source
comparison cho `policy_check`/`manifest` đã kiểm. Pilot source digest vẫn
`1d76c3a4e5cf9c5fe32d6fd94b846a2879eca268a6023ce34203794dc801d884`;
sáu notebook cũ giữ nguyên bytes. Không PR mới hoặc thay roster/protocol.

## Hai hash cấu hình

| Model | `legacy_transport_config_sha256` | `candidate_execution_config_sha256` |
| --- | --- | --- |
| InternVL3.5 HF | `9a6d80324c1b6f3d9d4e05ac210a5d8e6f3e6a4ac4b18dd70d75751b4cc93b7a` | `57727194e7eefe4b652bdf0b89a9675e7727866ffe4dfbc6334b0c07bda69474` |
| MiniCPM-V-4 | `5de12ffd4063e7801e2f028daace0f4e85e6eefe3cff75c00f36aa0d287aee49` | `4bbd04cb734c732ce708e3d63c07a059d02f0c5501517b11664c528e24a87b3f` |

Legacy hash = canonical digest exact frozen `pilot.settings(key)` khi enroll đúng
model. Execution hash = canonical digest toàn bộ config v2, gồm legacy snapshot
có dán nhãn và effective candidate. Không hoán đổi chúng.

Frozen runner giữ `raw.identity.config_sha256` bằng **legacy** hash. Raw thêm
`execution_release` với cả hai tên rõ scope, model/source/ref/run/attempt;
`configuration_provenance` giữ full config v2 và mapping alias. CandidateStore
lưu raw trước kiểm chứng, rồi kiểm config/hashes, request model/revision/C1/
generation/processor, native logit boundary và sequence trước parser. Recovery
kiểm lại hợp đồng và grant supervisor giữ; provenance sai không thành SUCCESS
kể cả result checksum đã được sửa khớp. Raw IDs/logits không bị ghi lại.

Native `steps[*].origin` giữ descriptor gốc về hook nói chung. Effective target
là model/`internvl_outer` cho InternVL và `model.llm`/`minicpm_llm_forward` cho
MiniCPM; không gán cơ chế pilot cũ cho candidate. [Runbook](../CANDIDATE160_KAGGLE.md)
mô tả chi tiết schema/alias và điều kiện trước thực nghiệm.

## Kết quả CPU mới

| Lượt thực chạy trên source cuối | Tổng | PASS | SKIP | FAIL/ERROR |
| --- | ---: | ---: | ---: | ---: |
| InternVL Windows CPU | 64 | 61 | 3 | 0/0 |
| MiniCPM Windows CPU | 64 | 61 | 3 | 0/0 |
| InternVL Linux CPU | 64 | 63 | 1 | 0/0 |
| MiniCPM Linux CPU | 64 | 63 | 1 | 0/0 |
| Exact Git export full Windows | 293 | 256 | 37 | 0/0 |
| Exact Git export full Linux | 293 | 261 | 32 | 0/0 |

Hai full release checkers kiểm đủ8 notebook, mọi cell/source/payload/pins/builder
bytes và source mutation, trả **CODE_PASS / release_status=BLOCKED**. Candidate
cells thật chạy CPU trong thư mục tổng hợp không grant → BLOCKED/nonconsumed,
archive/sidecar verify PASS. Sáu notebook cũ chỉ byte/build/compile kiểm.

Windows full SKIP37 = candidate15/Phi6/Smol9/live pip1 và6 platform checks;
Linux SKIP32 = candidate15/Phi6/Smol9/live pip1/Windows junction1. Candidate native
có receipts riêng; không dùng full-suite skips để suy native hoặc GPU PASS.
Focused Windows SKIP3 là real symlink tests thiếu OS permission; junction thật
PASS. Linux SKIP1 là Windows junction. Cả15 native tests PASS/model/OS, gồm160
synthetic native calls. Bốn receipts ghi source unchanged và cùng Git commit
`c75113f4a62d8d30303269f4a8bd72fc71040c15`. Các lượt trước hai guard schema cuối
được giữ như development logs, không dùng chứng minh source cuối PASS.

Không dùng [receipts tại HEAD cũ](https://github.com/tantdna2/SafeShift/tree/65da8a3dfd19c7f61b3e1a48465d1db7c97bdaac/docs/research/evidence/candidate160_20261029)
để chứng minh mã sửa PASS. Hồ sơ cũ giữ ở exact Git ref; index/receipts HEAD mới
phải có source/commit/config v2 đã thực chạy. Đây là Codex-recorded evidence,
không GitHub CI, ChatGPT-rerun hoặc independent audit.

## Regression và môi trường

Bổ sung kiểm thử cho cả hai model: snapshot lịch sử/effective tách riêng, hash
tính lại độc lập; grant thiếu/sai/hoán đổi hash, schema v1/model sai; raw alias/
release/model/source/attempt sai, metadata Phi/legacy logits, request model/
generation/crop sai, sequence drift. Tất cả bị chặn trước parse sau raw durable;
native IDs giữ nguyên và partial archive vẫn verify. Recovery từ chối provenance
sai dù raw/result file checksums đã được cập nhật khớp. Raw/native/request/Store
metadata bị thay thành kiểu JSON sai cũng thành TECHNICAL_ERROR, không làm mất
nhánh accounting/export. Hai guard schema cuối được nghiệm thu bằng receipts mới.

Mỗi lượt160 scripted native/model/OS đối soát **mọi raw** có cả hai hash đúng và
request thật với model, frozen generation flags, RGB, boundary/sequence. Chạy lại
pipeline/order/cap/review/no retry, NaN/OOM/INVALID/ENOSPC/archive và tests PR #151.
Network/CUDA/real model forward/weights bị guard; meta/empty safetensors chỉ CPU
rehearsal, không model inference hay real checkpoint validation.

CPython **3.11.9**, isolated CPU venv Windows và WSL2 Linux; public source/index
cache đã hash-lock. Native fixture kiểm CPU pins/pip check/freeze/module ownership/
compiled NMS: Torch2.6.0+cpu/torchvision0.21.0+cpu, Accelerate1.6.0, NumPy1.26.4,
Pillow10.4.0; InternVL TF4.55.4/tokenizers0.21.4/Hub0.34.4, MiniCPM TF4.51.3/
tokenizers0.21.1/Hub0.30.2. Không tải source/weights hoặc cài env mới.
CUDA wheel tuple2.6.0+cu124/0.21.0+cu124 chưa cài/nghiệm thu; không suy CPU PASS
sang GPU ABI/driver/VRAM hoặc chất lượng/HNLO thật.

## Receipts và tái lập

[Public index](evidence/candidate160_20261029/index.json) khóa SHA từng file. Bốn
candidate receipts v2 nguyên bản, có full config/hashes v2, executed-file hashes,
per-test events, Git/OS/Python/log SHA/source unchanged. Hai release receipts chỉ
che synthetic temporary paths trong stdout/stderr; giữ original receipt/log SHA,
counts/results và liệt kê fields bị che. Không private IDs/GT/ảnh, model outputs
thật hoặc credentials trong public artifacts.

Lệnh thực chạy từ root; dùng Python/cache CPU đã pin, không dataset:

```console
python -B -m scripts.build_candidate160_notebooks --runtime-ref 820200bba7c6f5796961acb64befef0c651772b3
<cpu-env-python> -B -m scripts.rehearse_candidate160 --model internvl35 --snapshot <public-snapshot> --index <index> --output data/processed/candidate160-review/internvl35-w2
<cpu-env-python> -B -m scripts.rehearse_candidate160 --model minicpm4 --snapshot <public-snapshot> --index <index> --output data/processed/candidate160-review/minicpm4-w2
python -B -m scripts.check_notebook_release --runtime-ref c75113f4a62d8d30303269f4a8bd72fc71040c15 --output data/processed/candidate160-review/release-windows-final.json
```

Linux dùng CPU venv riêng, outputs `internvl35-linux2`, `minicpm4-linux2`,
`release-linux-final.json`. WSL cần Git context explicit tới worktree/metadata do
Windows tạo, không sửa config/ref; checkout Linux thuần không cần bước đó.
Artifacts gốc ở ignored `data/processed/candidate160-review/`; đổi output name khi
tái lập, không ghi đè. Development checks không thay receipts nghiệm thu mới.

## Giới hạn

Giữ Draft PR #152, chờ ChatGPT kiểm exact new HEAD/source/receipts; chưa independent
audit hoặc merge. G0/T0/O3, fresh grant v2/ledger, policy/Lead review/runtime
approval, official checkpoint và delivery review vào saved VM vẫn BLOCKED/
UNVERIFIED. Actual bundle/checkpoint bytes, Kaggle CPython/storage, CUDA child/
driver/T4 VRAM/FP16, classification/peer utility và empirical HNLO NOT_RUN/
UNVERIFIED. Thay đổi provenance không cấp quyền data/GPU.
