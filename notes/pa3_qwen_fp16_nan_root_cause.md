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
- Không tràn: clamp **bitwise identical**; probe là thụ động (bitwise như không hook).
- Tràn ở khối ViT sớm (block 0): clamp **không** che, vẫn NaN toàn bộ (fail-closed).
- Probe phân biệt `MLP_RESIDUAL_ADD`, `ATTENTION_RESIDUAL_ADD`, `LINEAR`.

Giới hạn: chứng minh cơ chế và công cụ, **không** chứng minh ảnh 85 tràn ở đâu.

## 6. Diagnostic GPU tối thiểu (đề xuất DEC-PA3-009, CHƯA phê duyệt)

`python -m safeshift.pa3.native.nan_probe` — chỉ chẩn đoán, `pa3_scores=null`.
Nạp model qua đúng `NativeScorer` (kiểm tra runtime/snapshot/processor như PA3),
`generate(max_new_tokens=1)` để tái tạo đúng prefill; forward hooks chỉ quan sát
(không sửa tensor), ghi mọi module theo thứ tự thực thi: số NaN/±Inf, |max| hữu hạn;
phân loại vị trí xuất hiện Inf/NaN đầu tiên; tính lại vị trí đó bằng FP32 từ chính
toán hạng FP16 để chứng minh có/không vượt 65504. Tùy chọn `--candidate-clamp` chạy
thêm một lượt với clamp trước merger và so sánh bitwise logits bước 0.

Phạm vi đề xuất (cần Lead phê duyệt dùng lại ảnh đã thử; không tạo điểm PA3, không
đổi trạng thái/mẫu số của Shard 0):

1. `power-Level04-Wheeled-001764-002` (ảnh 85) — ca lỗi.
2. `metallurgy-Level04-Wheeled-001232-001` (ảnh 84, cùng shape) — đối chứng.

Tổng 4 lượt prefill (2 ảnh × {baseline, candidate}) trong 1 phiên Kaggle T4, model
nạp mới; ước tính < 10 phút gồm nạp model. Không dùng ảnh NOT_ATTEMPTED, không TEST.

Bảng quyết định:

| Kết quả probe ảnh 85 | Ý nghĩa | Bước tiếp |
| --- | --- | --- |
| `MLP_RESIDUAL_ADD` tại `visual.blocks.31`, FP32 > 65504; candidate hữu hạn; đối chứng bitwise bằng nhau | **CONFIRMED**: đúng lỗi vLLM #13968 | Lead quyết định áp dụng clamp (mục 7) |
| Tràn ở khối ViT sớm hơn / `ATTENTION_RESIDUAL_ADD` / `LINEAR` trong ViT | CONFIRMED tràn FP16, khác vị trí | Clamp trước merger không đủ (test block 0); cần đề xuất vị trí khác |
| Tràn trong decoder LLM | CONFIRMED tràn FP16 ở LLM | Đề xuất riêng cho decoder |
| `origin=null`, logits hữu hạn trên model nạp mới | Không tái hiện | Ủng hộ phụ thuộc trạng thái/phần cứng; cần diagnostic chuỗi riêng |
| `INSIDE_MODULE` / `UNHOOKED_OPERATION_BEFORE_INPUT` | Phép toán không có module (SDPA, RoPE…) | Probe hẹp hơn quanh vị trí đó |

Lệnh Kaggle (Inputs giống full-TRAIN: runtime archive + inventory, model archive,
TRAIN dataset; repo checkout tại commit được duyệt; Internet OFF, GPU T4):

```console
python -m safeshift.pa3.native.nan_probe --launch --inputs /kaggle/input \
  --runtime-input <rel> --runtime-inventory-input <rel> --runtime-inventory-sha256 <sha> \
  --model-input <rel> --dataset-input <rel TRAIN root chứa DATA_PATH/> --decision DEC-PA3-009 \
  --sample "power-Level04-Wheeled-001764-002|DATA_PATH/train/Annotations/Normal_data/power-Level04-Wheeled-001764/power-Level04-Wheeled-001764-002.jpg|c11429a2c00fde564fe7e909c3f8d24f1a6cec6775087d52c0cc4c476bd4cb65" \
  --sample "metallurgy-Level04-Wheeled-001232-001|DATA_PATH/train/Annotations/Normal_data/metallurgy-Level04-Wheeled-001232/metallurgy-Level04-Wheeled-001232-001.jpg|a142dc0d75c9d57466b8295400501f4865dc1c6a4598e98463593684bf04a726" \
  --candidate-clamp --output /kaggle/working/pa3_nan_probe_dec009.json
```

Gate: lệnh từ chối chạy (trước khi chạm runtime/model/ảnh) trừ khi `DECISIONS.md`
tại commit đang checkout có đúng dòng `DEC-PA3-009 status: APPROVED_FOR_NAN_LOCALIZATION`.
Commit này chỉ ghi `PROPOSED_NOT_APPROVED`. Output không ghi đè, một lần chạy, không retry.

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
(cùng phiên bản đã khóa, bản CPU). Python hệ thống: không torch.

- Venv: `python -m unittest tests.test_pa3_nan_probe -v` → **9/9 PASS**
  (4 gate/launch + 5 upstream-model).
- Python hệ thống, worktree LF sạch tại BASE + 2 file mới:
  `tests.test_pa3_boundaries tests.test_pa3_native tests.test_pa3_full_train tests.test_pa3_nan_probe`
  → **76 run, OK, 5 SKIP** (5 test upstream cần torch).
- Cùng worktree: `tests.test_pa3_synthetic tests.test_pa3_feasibility tests.test_pa3_runtime_prep
  tests.test_pa3_seminar_direction` → 112 run, 1 FAIL, 4 SKIP. FAIL duy nhất
  `test_committed_grant_is_null_and_prior_authority_untouched` tái hiện trên BASE
  nguyên trạng (không có file mới) — lỗi kế thừa, cũng được PR #101 báo.
- Lưu ý môi trường: working tree chính của máy này có file CRLF trong khi blob BASE
  là LF, khiến `test_protected_source_bytes_equal_exact_base` FAIL giả ở đó; vì vậy
  hồi quy được chạy trên worktree LF sạch.
- Chưa chạy: GPU/model thật, toàn bộ test suite repo, `launch` trên Linux/Kaggle thật.
