# Phi eager attention repair — CPU/source audit, 29/10/2026

BASE/main: `49ab2e8832683d4ae4877291cd7a82abbc533d2b` (PR #141 merge,
fetch + GitHub API đối chiếu). Nhánh `fix/phi-eager-attention-20261029`, worktree
riêng; toolset không mở được session Codex UI mới. Một Draft PR, không merge.
Đây là self-review kỹ thuật, không audit độc lập hoặc Kaggle/model PASS.

Owner cung cấp Phi r4/a4: Python 3.12/bootstrap/torch/Transformers, 160 ảnh,
storage, T4×2 và checkpoint đúng revision tải thành công; `model_load` ImportError
yêu cầu `flash_attn`, 0/160 inference, `attempt_consumed=true`. Chưa có archive,
receipt/checksum a4 trong task để kiểm độc lập. Giữ nguyên lịch sử, **không tái
dùng a4**; không tạo grant/run/attempt mới hoặc sửa evidence cũ.

## Nguyên nhân đã kiểm bằng source và reproduction thật

1. [Config Phi đúng revision](https://huggingface.co/microsoft/Phi-3.5-vision-instruct/blob/12b77fb40b63a2c73c68243d3f767aab688a1b2a/config.json)
   khai báo `_attn_implementation=flash_attention_2`. Remote
   [Phi3VConfig](https://huggingface.co/microsoft/Phi-3.5-vision-instruct/blob/12b77fb40b63a2c73c68243d3f767aab688a1b2a/configuration_phi3_v.py)
   chuyển các kwargs còn lại cho `PretrainedConfig`.
2. [Auto factory 4.43.3, L524–531](https://github.com/huggingface/transformers/blob/v4.43.3/src/transformers/models/auto/auto_factory.py#L524)
   gọi AutoConfig với `return_unused_kwargs=True`. Trong
   [configuration_utils L769–772](https://github.com/huggingface/transformers/blob/v4.43.3/src/transformers/configuration_utils.py#L769),
   `from_dict()` pop tham số eager vào `attn_implementation` trước constructor.
   Constructor L357 đặt internal eager; vòng kwargs L372–377 sau đó gán trường
   private từ JSON, qua setter L419–421, trở lại **flash_attention_2**. Eager đã
   bị consume, không còn trong unused kwargs gửi tiếp cho model loader.
3. [modeling_utils L3781–3788](https://github.com/huggingface/transformers/blob/v4.43.3/src/transformers/modeling_utils.py#L3781)
   auto-dispatch trước khi dựng model; nhánh FA2 L1521 gọi kiểm thư viện và ném
   ImportError khi thiếu flash_attn. Không phải bằng chứng weights hỏng/OOM.
   Việc remote module thử import flash_attn trong try/except không phải blocker
   này: ImportError optional đó đã được remote source bắt lại.
4. [Remote modeling Phi L139–149/L1120–1131](https://huggingface.co/microsoft/Phi-3.5-vision-instruct/blob/12b77fb40b63a2c73c68243d3f767aab688a1b2a/modeling_phi3_v.py)
   chọn decoder theo config, nhưng tạo CLIP từ constant config **độc lập**.
   [CLIP 4.43.3](https://github.com/huggingface/transformers/blob/v4.43.3/src/transformers/models/clip/modeling_clip.py#L496)
   hỗ trợ SDPA. Internal attention `None` của constant khiến dispatcher chọn SDPA,
   kể cả khi Phi ngoài đã eager; reproduction CPU xác nhận riêng nhánh này.

## Sửa và các điều kiện fail-closed

`pilot/phi_attention.py` là helper dùng chung cho preflight và NativeBackend:
kiểm hash ba file/auto_map trước remote import; đọc AutoConfig local-only đúng
revision, copy rồi gán property `_attn_implementation="eager"` **sau deserialize**.
Truyền config object tường minh cùng eager vào AutoModel, nên model loader không
đọc lại JSON để quyết định attention. Không sửa config/checkpoint trên đĩa.

Copy constant CLIP, gán eager tường minh và thay tham chiếu constant **chỉ trong
context nạp**, khôi phục cả khi lỗi. Remote code/kiến trúc/preprocessing giữ
nguyên; model giữ config copy đã eager sau context. Không monkeypatch attention
forward hoặc capability checks. Sau nạp, kiểm config/internal/cached mode, đúng
lớp eager của từng decoder/vision layer và quét module FA/SDPA bổ sung. Lớp
`CLIPAttentionFA2` cũng bị chặn, dù tên này lọt qua check tên cũ.

CPU ABI probe của runtime Phi nay tải **chỉ** `config.json`,
`configuration_phi3_v.py`, `modeling_phi3_v.py`, kiểm nguyên source lock, rồi
dựng full skeleton meta FP16 và kiểm 32 decoder + 24 vision eager. Không weights,
CUDA, image, forward, logits hoặc prediction. Đây có thực thi remote constructor
đã review trên CPU; không còn ghi `custom_phi_execution=NOT_RUN` cho gate này.
Sai hash/config/import/lớp hoặc không còn meta đều BLOCKED trước nvidia-smi/ledger.

Success receipt nằm trong `runtime_preflight.json` →
`qualification.software.phi_attention`, được bind gián tiếp qua các receipt hash
environment/ledger. Failure giữ đầy đủ stdout/stderr CPU trong runtime receipt;
export/sidecar/checksum và 160-row NOT_ATTEMPTED accounting vẫn hoạt động.
Loader thật ghi `phi_attention_config.json` trước load và
`phi_attention_runtime.json` sau verify; lỗi load vẫn giữ receipt trước đó.
Raw-before-parse, seals, resume/retry và fail-closed không bị nới lỏng.

Giữ nguyên model revision `12b77fb40b63a2c73c68243d3f767aab688a1b2a`, safetensors,
FP16, GPU0, 16 crops, generation/C1/HNLO, data/split/labels/metrics/thresholds,
requirements/runtime pins và model source lock. Không cài FA2/đổi thư viện,
không chạm weights, grant hoặc protocol M2. Payload mới:
`850bc40eb4b40cc359ce87d56b1f86a790f0ea67990b8e263ea4e36c2e64dfa1`.
Cả sáu notebook được tạo lại bằng builder vì dùng chung embedded payload.
Gemma vẫn BLOCKED; grant/source cũ không cấp quyền cho payload mới.

## Kiểm chứng đã chạy

- `python -B -m unittest discover -s tests -p test_phi_attention.py -v`:
  **12/12 PASS**, không skip. Synthetic tests: eager/FA JSON, copy/context rollback,
  pin/hash/auto_map drift, loader config + FP16/GPU0/16 crops, FA/SDPA/CLIP FA2,
  layer coverage, raw CPU diagnostics, block trước GPU/worker/attempt, archive replay.
- `python -B -m unittest discover -s tests -v`: Windows CPython 3.11.9,
  **181 tests: 177 PASS, 4 SKIP** (3 Linux-only + 1 opt-in pip/network rehearsal).
- Cùng lệnh trên WSL Linux x86_64 CPython 3.11.13: **181 tests: 180 PASS,
  1 SKIP** (opt-in pip/network rehearsal). Không chạy lại bootstrap install cũ.
- `python -B -m scripts.build_three_vlm_notebooks`: PASS; full suites kiểm
  notebook deterministic, embedded hashes và outputs rỗng. `git diff --check`: PASS.
- [Rehearsal CLI](../scripts/rehearse_phi_attention.py) trên môi trường Phi đã có,
  không cài package mới: torch **2.6.0+cu124**, Transformers **4.43.3**,
  Python **3.11.13**. [Receipt](PHI_EAGER_ATTENTION_CPU_RECEIPT_20261029.json) và
  [SHA-256 sidecar](PHI_EAGER_ATTENTION_CPU_RECEIPT_20261029.sha256.json) ghi
  source digest, script hash, BASE và ba hash upstream (khớp source lock).
  Config công khai được tải trực tiếp đúng revision, không weights; CPU helper
  production dùng source-only download double local, **không coi là live Hub
  snapshot_download/Kaggle network qualification**.

Tái tạo sau khi tải đúng ba file public vào ignored
`data/processed/phi_attention_audit/upstream/`, giữ nguyên dependency pins:

```console
python -B -m scripts.rehearse_phi_attention --snapshot data/processed/phi_attention_audit/upstream --output data/processed/phi_attention_audit/rehearsal.json --base-commit 49ab2e8832683d4ae4877291cd7a82abbc533d2b
```

Rehearsal dùng config class/Transformers thật: cả eager và FA2 JSON đều tạo đủ
32 `Phi3Attention` + 24 `CLIPAttention` sau sửa; FA2 trước sửa tái hiện ImportError,
kwarg eager mất khỏi unused kwargs. Guard chặn CUDA initialization/query,
weights load, model forward, Flash/SDPA constructors và SDPA functional;
mọi parameter/buffer ở meta, floating dtype FP16. Ba text source hashes trước/sau
không đổi; không claim đã hash hay nạp checkpoint weights ở rehearsal.

## Chưa kiểm chứng

Kaggle Python 3.12 preflight mới, live source-only Hub/cache, nạp weights thật
FP16/GPU0 trên T4, peak RAM/VRAM/disk, 16-crop feasibility, generation/raw/HNLO và
classification 160 ảnh đều **NOT RUN / UNVERIFIED** cho bản sửa. Không suy eager
CPU PASS thành Kaggle PASS. Review Draft trước; mọi pilot sau đó cần quyền mới
bind source/release và attempt mới, không dùng lại a4.
