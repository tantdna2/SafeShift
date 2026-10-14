# PA3 Qwen2.5-VL Shard 0 NaN — root-cause analysis và diagnostic GPU tối thiểu

2026-10-14 (Asia/Bangkok). BASE `486b4af7ad1f402395b60b0c36ebfd80a74cf4de`.
Độc lập với Draft PR #101 (`0e40bd8f…`, StateGuard); không sửa/merge PR đó.
Không GPU, không nạp model thật, không chạy lại ảnh nào, không đọc TEST, không
đổi FP16/SDPA/prompt/tokenizer/revision/metric. Ảnh 85 chỉ được đọc byte/pixel
trên CPU để đối chiếu SHA-256 và miền giá trị đầu vào.

## Kết luận

**ROOT_CAUSE = SUSPECTED (mạnh), chưa CONFIRMED cho chính lượt chạy này.**
Giả thuyết dẫn đầu: tràn FP16 (|x| > 65504) trong residual stream của khối ViT
cuối Qwen2.5-VL-3B trên ảnh cụ thể → ±Inf → `merger.ln_q` (RMSNorm,
`inf · rsqrt(inf) = inf · 0 = NaN`) → NaN ở toàn bộ image token → attention lan
NaN sang mọi vị trí sau → 151.936/151.936 raw logits NaN ngay bước 0 → argmax 0
(token `!`) ở cả 32 bước. Archive không chứa activation nên không định vị được
lớp đầu tiên; cần đúng một diagnostic GPU nhỏ (bên dưới) để CONFIRM.

SafeShift **không** gọi sai API: luồng processor → `generate` khớp mã chính thức
Transformers 4.51.3 (mục 3). Lỗi thuộc numerics của model ở điều kiện FP16 đã khóa.

## 1. Bằng chứng từ archive (đọc trực tiếp, không suy diễn)

Nguồn: `PA3_TRAIN_SHARD_0_OUTPUT` (bản giải nén local của archive gốc; PR #101 đã
xác minh SHA-256 archive và 1.363 receipt).

- `sample-000084.step-00.json`: raw và processed đều `nan=151936`, `positive_inf=0`,
  `negative_inf=0`, `argmax_id=0`; `generated_token=0`. Các bước 01–31 giống hệt.
  → NaN có ngay trong forward **prefill** (logits bước 0 sinh từ prefill), không phải
  phát sinh trong decode. Không có Inf ở logits → NaN đã tồn tại trong hidden state
  cuối, không phải tràn tại `lm_head` (tràn tại `lm_head` cho ±Inf, không cho NaN).
- `sample-000083` (thành công, `metallurgy-Level04-Wheeled-001232-001`) và
  `sample-000084` có cùng `input_ids [1,1782]`, `pixel_values [4888,1176]`,
  `image_grid_thw [[1,52,94]]`. Cùng shape/dtype/mask ⇒ cùng nhánh dispatch
  SDPA/kernel ⇒ lỗi **phụ thuộc giá trị** (nội dung ảnh), không phụ thuộc shape.
- Token 0 = `!`; `generate` dùng argmax của logits (NaN ⇒ chỉ số 0). Do đó NaN nằm
  **bên trong** `model.generate`, độc lập với `summarize_tensor` của SafeShift.

## 2. Giả thuyết đã loại trừ (kèm bằng chứng)

| Giả thuyết | Kết luận | Bằng chứng |
| --- | --- | --- |
| NaN có sẵn trong ảnh/pixel values | Loại | JPEG RGB 8-bit 2560×1440, SHA `c11429a2…` khớp archive; processor 4.51.3 chỉ rescale 1/255 và chuẩn hóa mean/std CLIP (std ≠ 0) ⇒ miền [−1,792; 2,146], hữu hạn (đo CPU). |
| NaN sinh ở bước decode sau | Loại | Bước 0 đã NaN toàn bộ. |
| SafeShift ghi/tóm tắt logits sai | Loại | Token sinh ra = 0 ở cả 32 bước do chính `generate` chọn. |
| Logits processor (repetition penalty, temperature) | Loại | `output_logits` là raw trước processor; `do_sample=False`. |
| Dùng sai API Qwen | Loại | Mục 3. |
| KV cache rò giữa ảnh | Không có cơ chế | SafeShift không truyền `past_key_values`; `generate` 4.51.3 tạo `DynamicCache` mới mỗi lần. |
| `rope_deltas` cũ | Không có cơ chế | 4.51.3 tính lại `get_rope_index` khi `cache_position[0]==0` (mọi prefill); SafeShift còn đặt `None` trước mỗi lần gọi. |
| Trọng số/buffer bị biến đổi | Không có cơ chế | `inference_mode`; forward không có phép in-place lên tham số; RoPE `mrope`→`default` nên `dynamic_rope_update` không đổi `inv_freq`. |
| SDPA kernel lỗi theo shape | Loại | Ảnh 84 cùng shape/kernel chạy đúng. Vision SDPA dùng mask bool theo cửa sổ, không có hàng bị che hoàn toàn. |

Trạng thái giữa các ảnh: không tìm thấy đường truyền trạng thái nào trong mã
4.51.3; nhưng archive không thể chứng minh ngược trạng thái thật trên GPU. Diagnostic
bên dưới phân biệt được: nếu ảnh 85 tái hiện NaN trên model **vừa nạp mới**, ô nhiễm
trạng thái từ 84 ảnh trước không phải điều kiện cần.

## 3. Đối chiếu với Transformers 4.51.3 (wheel SHA-256 `fd3279633ceb…8a83`)

`modeling_qwen2_5_vl.py`:
- `Qwen2_5_VLVisionBlock.forward`: hai phép cộng residual FP16 thuần
  (`hidden_states + self.attn(...)`, `hidden_states + self.mlp(...)`), không clamp.
- `Qwen2RMSNorm`: upcast FP32, nhưng Inf đầu vào ⇒ NaN.
- `Qwen2_5_VLAttention` (eager) có sẵn bản vá *"Fix precision issues in Qwen2-VL
  float16 inference"* (thay Inf trong attention weights) — upstream đã biết FP16 bất
  ổn; nhánh SDPA không có bản vá này, và nó không áp dụng cho ViT.
- `ForConditionalGeneration.forward`: `pixel_values.type(self.visual.dtype)` ⇒ ViT
  chạy FP16; `rope_deltas` như mục 2.

SafeShift (`safeshift/ls1/runtime.py:96-101,137-159`, `safeshift/pa3/native/qwen.py:43-56`):
processor với `min/max_pixels` chính thức, `process_vision_info`, `generate` greedy,
batch 1, mask toàn 1 — đúng API. Không tìm thấy bug của SafeShift gây NaN.

## 4. Bằng chứng upstream độc lập

- vLLM issue [#13817](https://github.com/vllm-project/vllm/issues/13817): Qwen2.5-VL-**3B**,
  `dtype=float16`, một ảnh cụ thể sinh chuỗi `!!!`; BF16 đúng; 7B/72B không lỗi.
- vLLM PR [#13968](https://github.com/vllm-project/vllm/pull/13968), commit
  `78648758794e2268a3af04b1eeab2347d961d88a` (merged 2025-02-27): *"Qwen2.5-VL-3B will
  overflow with float16 in its ViT encoder"*; mã: *"For Qwen2.5-VL-3B, float16 will
  overflow at last block for long visual tokens sequences"*; vá bằng
  `cast_overflow_tensors` (clamp ±(65504−1000) chỉ khi có Inf/NaN) trước `merger`.
- Transformers [#35151](https://github.com/huggingface/transformers/issues/35151):
  lịch sử bất ổn FP16 của Qwen2-VL trong attention eager.

Đây là bằng chứng về **cùng model, cùng dtype, cùng triệu chứng**, không phải bằng
chứng trực tiếp về activation của ảnh 85.

## 5. Tái hiện cơ chế trên CPU (mã upstream thật, trọng số tổng hợp)

`tests/test_pa3_nan_probe.py` dựng `Qwen2_5_VLForConditionalGeneration` tí hon bằng
Transformers 4.51.3/torch 2.6.0 CPU, FP16, SDPA, chạy `generate` thật:

- Tiêm một tràn tại residual MLP khối ViT cuối (mỗi toán hạng 40000, tổng 80000):
  **151.936/151.936 logits bước 0 NaN, argmax 0** — đúng chữ ký archive. NaN đầu tiên
  tại `visual.merger.ln_q`. Cùng trọng số ở FP32: hữu hạn.
- Ứng viên clamp trước merger: logits hữu hạn (FAIL trước → PASS sau).
- Không tràn: clamp **bitwise identical**; probe thụ động trên CPU (GPU: UNKNOWN, mục 6.4).
- Tràn ở khối ViT sớm (block 0): clamp **không** che, vẫn NaN toàn bộ (fail-closed).
- Probe phân biệt `MLP_RESIDUAL_ADD`, `ATTENTION_RESIDUAL_ADD`, `LINEAR`.

Giới hạn: chứng minh cơ chế và công cụ, **không** chứng minh ảnh 85 tràn ở đâu.

## 6. Diagnostic GPU tối thiểu (đề xuất DEC-PA3-009, CHƯA phê duyệt)

### 6.1 Công cụ

`python -m safeshift.pa3.native.nan_probe_run` (điều phối) + `nan_probe` (đo đạc).
Chỉ chẩn đoán: mỗi kết quả có `pa3_score: null`. Model nạp qua đúng `NativeScorer`
(kiểm tra runtime/snapshot/processor như PA3), `generate(max_new_tokens=1)` để tái
tạo đúng prefill. Forward hook chỉ quan sát, không sửa tensor. Chúng ghi từng module
theo thứ tự thực thi: số NaN/±Inf và |max| hữu hạn. Vị trí Inf/NaN đầu tiên được
phân loại và, nếu có toán hạng, tính lại bằng FP32 từ chính toán hạng FP16. Mỗi lượt
còn lưu raw logits bước 0 dạng byte nguyên vẹn (base64 + SHA-256), cùng bản tóm tắt
`summarize_tensor`, để đối chiếu với bản ghi Shard 0 trong archive.

Phạm vi bị khóa trong code (`nan_probe_run.SCOPE`) và trong file authority. Không có
tham số CLI nào để chọn ảnh:

1. `power-Level04-Wheeled-001764-002` (ảnh 85) — ca lỗi.
2. `metallurgy-Level04-Wheeled-001232-001` (ảnh 84, cùng shape) — đối chứng.

Kế hoạch cố định 4 lượt theo thứ tự: ảnh 85 baseline → ảnh 85 candidate → ảnh 84
baseline → ảnh 84 candidate. Một run ID, không retry, không ảnh NOT_ATTEMPTED, không
TEST. Việc dùng lại hai ảnh đã thử cần Lead phê duyệt. Lượt chạy không đổi trạng
thái hay mẫu số của Shard 0.

### 6.2 Authority (thay cho dòng văn bản trong DECISIONS.md)

Tái dùng đúng quy tắc PA3 đã kiểm toán (`access.authority`/`diagnostic_authority`),
với file riêng `configs/pa3/nan_probe_authority.v1.json`. Draft này có `grant: null`
và `implementation: null`, nên bị từ chối trước mọi truy cập Git, runtime, model
hay ảnh. Để mở quyền, cần:

- B = `main` đã kiểm toán, là hậu duệ của `486b4af…`.
- F1 = **một** commit triển khai đã review, cha là B (squash PR này lên B).
- F2 = commit **chỉ** sửa file authority, cha là F1; ghi `base=B`, `implementation=F1`
  và grant `{approval, decision: "DEC-PA3-009", runtime_inventory_sha256}`.
- M = merge chuẩn hai cha `[B, F2]`; `--source-commit` phải bằng HEAD bằng M.

Kiểm tra thêm: `scope` phải khớp đúng `SCOPE` trong code; tree của M phải bằng tree
của F2; byte của file authority phải bằng blob ở F2; ba file authority cũ không đổi
so với `486b4af`; working tree sạch; `preflight.source` kiểm byte đã commit và chặn
file untracked che import; `runtime_inventory_sha256` khớp grant. SHA của F1 chỉ được
ghi trong F2, sau khi F1 đã tồn tại, nên không có phụ thuộc vòng tròn.
`DECISIONS.md` không còn vai trò cấp quyền: sửa nó, sửa file authority local, hay
commit grant thường đều bị từ chối (có test).

Kiểm tra quyền được chạy ở cả tiến trình cha (`--launch`) và tiến trình con, trước
khi tạo journal, nạp model hay đọc ảnh. Ảnh chỉ được mở nếu khớp nguyên triplet đã
ghim, và SHA-256 file được kiểm trước khi decode.

Rủi ro còn lại (giống mọi authority PA3 hiện có): topology Git chứng minh tính toàn
vẹn, **không** phải chữ ký. Người có quyền ghi vẫn dựng được B→F1→F2→M. Lead phải tự
xác minh M trên `main` đã kiểm toán. Ngân sách 4 lượt được kiểm trên đĩa trong một
phiên; giữa các phiên Kaggle mới vẫn cần sổ ghi lượt chạy bên ngoài.

### 6.3 Journal bền vững và thu hồi khi Kaggle dừng bất thường

Journal: `data/processed/pa3_qwen/pa3-qwen-nan-probe-dec009/` (repo trong
`/kaggle/working` nên nằm trong Output).

- `DurableJournal`: ghi tệp tạm trong `<run>-staging/` (tạo độc quyền), fsync, rồi
  `os.link` nguyên tử vào đúng tên (thất bại nếu đã tồn tại, không ghi đè), xóa tệp
  tạm, fsync thư mục (POSIX). Payload ghi trước, receipt SHA-256 ghi sau: payload
  thiếu receipt là ghi dở, phát hiện được (`TORN_WRITE`). Tệp tạm cũ không bao giờ
  được dùng lại.
- Thứ tự: `authority` → `t1` → `model-load.attempt` (trước khi nạp) → `model` →
  với mỗi lượt i: `prefill-i.attempt` (trước prefill) → `prefill-i.result` (ngay sau)
  → `comparison` → `finish`. Lỗi được ghi vào `failure`; seal và package nằm trong
  `finally`.
- `--recover` (chỉ CPU, không cần quyền, không model/dữ liệu) phân loại từng lượt:
  `COMPLETE`, `INCOMPLETE_STARTED_NO_RESULT`, `INCOMPLETE_STARTED_INVALID_RESULT`,
  `CORRUPT_ATTEMPT_RECORD`, `NOT_STARTED`. Nó cũng báo tệp tạm sót lại, không sửa và
  không retry, rồi đóng gói `<run>.tar.gz` kèm `.sha256.json` và ghi
  `<run>-recovery.json`. Không ghi đè: chạy lại thì giữ nguyên bản cũ. Tiến trình cha
  tự gọi `recover` sau khi con kết thúc, kể cả khi con crash. Nếu toàn bộ VM bị
  giết, chạy `python -m safeshift.pa3.native.nan_probe_run --recover` trên các tệp
  đã tải từ Output.
- Run ID đã tồn tại → từ chối (không retry).

UNKNOWN: Kaggle có lưu `/kaggle/working` khi phiên bị hủy do timeout hay lỗi host
hay không chưa được kiểm chứng trong repo này. Mỗi tệp đã fsync riêng, nên phần đã
ghi xong không phụ thuộc vào bước đóng gói cuối.

### 6.4 Tài nguyên — chưa đo, không tuyên bố PASS

- **Thời gian: ESTIMATED, chưa đo.** Gồm nạp model (cùng đường với Shard 0) và 4
  prefill 1782 token. Mỗi tensor được hook tạo khoảng 4 lần đồng bộ host
  (`int()`/`float()`), khoảng 1.000 module, hai tensor mỗi module. Chi phí đồng bộ
  thực tế trên T4: UNKNOWN. Con số "< 10 phút" trước đây là ước lượng, không phải
  số đo.
- **VRAM: ESTIMATED, chưa đo.** Thống kê theo chunk 2^24 phần tử (khoảng ≤ 80 MiB tạm
  mỗi chunk FP16). Tính lại Linear bằng FP32 bị giới hạn 2^26 phần tử đầu ra
  (256 MiB), vượt thì `recompute=null` → `UNRESOLVED`. Tính lại residual ViT khoảng
  25 MiB. Headroom thật trên T4 cùng 7,5 GB trọng số: UNKNOWN. Nếu OOM, lỗi được
  ghi vào journal, không retry.
- **Đồng bộ CUDA:** lỗi CUDA bất đồng bộ có thể bị báo trễ ở module sau. Các `int()`
  sau mỗi module làm báo lỗi sớm hơn nhưng không đảm bảo tuyệt đối.
- **Tính thụ động của hook:** CPU cho thấy kết quả bitwise như khi không có hook.
  Trên GPU, hook không sửa tensor, nhưng việc chọn thuật toán cuBLAS phụ thuộc bộ
  nhớ còn trống: UNKNOWN. So sánh baseline/candidate trong cùng một phiên (đều có
  hook) là so sánh cùng điều kiện. Việc khớp với logits Shard 0 được kiểm bằng
  `step0_archive_comparable` so với bản ghi archive, không giả định.

### 6.5 Giới hạn của forward hook

Hook chỉ thấy ranh giới module. Các phép cộng residual được suy ra bằng tái dựng
từ đầu vào khối và đầu ra các module con. SDPA, RoPE, `masked_scatter`, softmax và
mọi phép toán nằm ngoài module không được quan sát trực tiếp. `localization` chỉ
nhận giá trị `FP16_OVERFLOW_LOCALIZED` khi vị trí là residual hoặc `Linear` **và**
phép tính lại FP32 thật sự vượt 65504. Mọi trường hợp khác — `INSIDE_MODULE`,
`LEAF_MODULE`, `UNHOOKED_OPERATION_BEFORE_INPUT`, `recompute=null`, NaN không do
tràn, hoặc logits NaN mà không module nào thấy — đều là **`UNRESOLVED`**, không được
kết luận nguyên nhân.

Bảng quyết định:

| Kết quả probe ảnh 85 | Ý nghĩa | Bước tiếp |
| --- | --- | --- |
| `FP16_OVERFLOW_LOCALIZED`, `MLP_RESIDUAL_ADD` tại `visual.blocks.31`; candidate hữu hạn; đối chứng bitwise bằng nhau | **CONFIRMED**: đúng lỗi vLLM #13968 | Lead quyết định áp dụng clamp (mục 7) |
| `FP16_OVERFLOW_LOCALIZED` ở khối ViT sớm hơn, residual attention hoặc `Linear` trong ViT | CONFIRMED tràn FP16, khác vị trí | Clamp trước merger không đủ (test block 0); cần đề xuất vị trí khác |
| `FP16_OVERFLOW_LOCALIZED` trong decoder LLM | CONFIRMED tràn FP16 ở LLM | Đề xuất riêng cho decoder |
| `NO_NONFINITE` trên model nạp mới | Không tái hiện | Ủng hộ phụ thuộc trạng thái/phần cứng; cần diagnostic chuỗi riêng |
| `UNRESOLVED` | Không định vị được phép toán đầu tiên | Không kết luận nguyên nhân; thiết kế probe hẹp hơn quanh vị trí đó |

### 6.6 Lệnh Kaggle (chỉ hợp lệ sau khi đã release authority; Draft này bị từ chối)

Inputs giống full-TRAIN (runtime archive + inventory, model archive, TRAIN dataset).
Repo checkout tại M trong `/kaggle/working`. Internet OFF, GPU T4.

```console
python -m safeshift.pa3.native.nan_probe_run --launch --source-commit <M> \
  --inputs /kaggle/input --runtime-input <rel> --runtime-inventory-input <rel> \
  --runtime-inventory-sha256 <sha trong grant> --model-input <rel> \
  --dataset-input <rel TRAIN root chứa DATA_PATH/>
# Sau đó, kể cả khi ô trên lỗi, thu hồi trên CPU (an toàn khi chạy lặp):
python -m safeshift.pa3.native.nan_probe_run --recover
```

Tải từ Output: `pa3-qwen-nan-probe-dec009.tar.gz` + `.sha256.json`, thư mục journal
và `pa3-qwen-nan-probe-dec009-recovery.json`.

## 7. Bản sửa ứng viên và tác động phương pháp

Ứng viên tối thiểu (chỉ khi probe ra hàng 1 của bảng): `cast_overflow_fp16` trước
`visual.merger` — đúng ngữ nghĩa vLLM: chỉ hoạt động khi tensor FP16 có ±Inf/NaN,
clamp ±64512; NaN giữ nguyên NaN; hữu hạn thì trả nguyên tensor.

- Ảnh không tràn (gồm 84 SUCCESS nếu GPU xác nhận như CPU): kết quả **bitwise không
  đổi** ⇒ không phải chạy lại, tính so sánh được giữ.
- Ảnh tràn: kênh tràn bị bão hòa ở 64512 thay vì giá trị thật (không biết được trong
  FP16). Đây là **thay đổi tính toán của model** cho đúng các ảnh đó ⇒ lệch so với
  điều kiện "FP16 native 4.51.3 nguyên bản". Nếu áp dụng: ghi DECISIONS, cờ theo mẫu
  (`vit_overflow_clamped`), báo cáo số mẫu bị clamp và AUROC có/không các mẫu đó.
- Không thay NaN bằng 0; NaN/Inf ở vị trí khác vẫn bị `RAW_NAN_OR_INF` chặn.
- Lựa chọn khác (ViT FP32, BF16 trên T4) thay đổi numerics của **mọi** ảnh ⇒ phải
  chạy lại toàn bộ; không khuyến nghị trước hạn 15/10/2026.

Chưa có bản sửa nào được nối vào luồng PA3. StateGuard (PR #101) không chữa nguyên
nhân này: tràn là hàm của (trọng số, ảnh), nên khởi động lại model không ngăn ảnh
85 tái lỗi; StateGuard chỉ còn giá trị nếu probe ra hàng "không tái hiện".

## 8. Kiểm thử đã chạy

Windows, CPU. Venv riêng: Python 3.11.9, `torch==2.6.0+cpu`, `transformers==4.51.3`
(cùng phiên bản đã khóa, bản CPU). Python hệ thống: không torch. Hồi quy chạy trên
worktree LF sạch (HEAD của PR cộng các thay đổi), vì working tree chính của máy này
có file CRLF làm `test_protected_source_bytes_equal_exact_base` FAIL giả.

Vòng sửa blocker kiểm toán (2026-10-14):

- Venv: `python -m unittest tests.test_pa3_nan_probe tests.test_pa3_nan_probe_run -v`
  → **22/22 PASS**. Gồm: 5 test upstream FP16 (tái hiện tràn, clamp FAIL trước → PASS
  sau, bitwise identity, block sớm vẫn NaN, phân biệt vị trí); phán quyết
  `UNRESOLVED`; clamp không có trong PA3 production; authority (đối chứng dương B→F1→F2→M,
  Draft từ chối trước Git/model/journal/ảnh ở cả cha và con, DECISIONS.md / sửa local /
  commit thường không tự cấp quyền, sai SHA / tree bẩn / sai binding / sửa byte /
  thiếu source proof, F2 sửa code, thêm/thay/tráo SHA ảnh, ngân sách 5, sai schema grant);
  ảnh ngoài scope và byte bị tráo bị chặn trước decode; journal (receipt, không ghi đè,
  tệp tạm cũ, checksum); ngân sách 4 lượt và thứ tự; **dừng cứng (`os._exit`) sau
  lượt 1, 2, 3** → lượt đã xong `COMPLETE`, lượt đang chạy
  `INCOMPLETE_STARTED_NO_RESULT`, phần còn lại `NOT_STARTED`, byte không đổi, package
  + SHA-256, recover lặp lại không ghi đè, không thể chạy lại; ghi dở (torn) được báo,
  không sửa; launch kiểm runtime trước khi restore, một child, gọi recover, không retry.
- Python hệ thống: `tests.test_pa3_boundaries tests.test_pa3_native tests.test_pa3_full_train
  tests.test_pa3_nan_probe tests.test_pa3_nan_probe_run` → **89 run, OK, 5 SKIP**
  (5 test cần torch).
- `tests.test_pa3_synthetic tests.test_pa3_feasibility tests.test_pa3_runtime_prep
  tests.test_pa3_seminar_direction` → 112 run, 1 FAIL, 4 SKIP. FAIL duy nhất là
  `test_committed_grant_is_null_and_prior_authority_untouched`, đã tái hiện trên BASE
  nguyên trạng — lỗi kế thừa, giống vòng trước và PR #101.
- `compileall` và `git diff --check`: PASS.
- Chưa chạy: GPU/model thật, `launch`/`recover` trên Linux/Kaggle thật, toàn bộ test
  suite repo. Thời gian, VRAM và chi phí đồng bộ CUDA: ESTIMATED/UNKNOWN (mục 6.4).
