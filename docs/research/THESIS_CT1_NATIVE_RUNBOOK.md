# CT1 — Pilot native Kaggle trên 48 ảnh TRAIN

**Candidate chờ Owner.** CPU tổng hợp và kiểm tra bytes có thể xác minh
trước khi chạy. Chưa có đo trực tiếp trên Kaggle, load Qwen3 hoặc native
call. Trạng thái G4–G6 chưa được xác nhận. Đợt này chỉ dựng code,
notebook, Input và Draft PR theo yêu cầu Owner.

## Owner chạy khi đã duyệt đúng SHA

1. Tạo notebook **private**, import notebook pilot từ bộ bàn giao. Chọn
   **GPU T4 ×2**, tắt Internet. Trong Add Input, attach riêng bốn Input
   private chứa source capsule, pilot ảnh mù, snapshot Qwen3 và bộ
   phần mềm đã ghim. So đường dẫn mount thực tế với ô cấu hình. Phần
   checkpoint chỉ trỏ đến thư mục mang đúng tên revision chứa các
   file đã khóa. Đính kèm **chỉ** thư mục `pilot-input`, bên trong có
   `plan.json`, `exclusions.json` và 48 PNG tên mù. Giữ
   `private-scoring` trên D. Không attach archive/dataset InspecSafe
   gốc, GT, annotation, TXT, checkpoint của model khác hoặc TEST.
2. Kiểm tra SHA của notebook và capsule theo bảng bàn giao, plan
   SHA, marker phần mềm và run ID. Giữ `resume: None` cho lần đầu.
   Driver được ghim theo quan sát đầu job, tối thiểu 570.26 trên Linux.
   Dùng notebook preflight riêng nếu muốn kiểm môi trường với cùng
   Inputs mà không chạy model. Notebook pilot chạy lại các gate trước
   khi load và thực hiện **Save Version → Save & Run All** một lần.
3. Giữ output `<run_id>.zip` và `<run_id>.zip.sha256.json`.
   Kiểm `summary.json`, `controller-failure.json` nếu có và nguyên
   nhân trong log. Chấm `runs.json` cục bộ với công cụ CT1 và GT riêng.
   Khi lỗi, giữ tất cả checkpoint và lịch sử. Chỉ tiếp tục khi xác minh
   ZIP của lượt gần nhất, không có VM đang chạy và vẫn cùng source,
   plan, phần mềm, driver và run ID. Attach ZIP qua Input bổ sung, điền
   path và SHA ở `resume`. Nếu mất checkpoint hoặc chưa rõ có call
   xảy ra hay chưa, dừng để đối soát.

[Kaggle Notebooks](https://www.kaggle.com/docs/notebooks) ·
[NVIDIA CUDA 12.8](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-toolkit-release-notes/index.html)

## Cohort và ngăn rò rỉ

48 ca TRAIN development, gồm 20 Level01, 12 Level02 và 16 Normal.
Chọn theo seed cố định và phân bổ vòng giữa các miền có support. Loại
các hash lặp trong TRAIN master, nhóm cùng waypoint trong pilot và
các cặp exact xuyên split đã được ghi trong metadata lịch sử. Không
truy cập TEST. Bỏ ảnh thuộc audit 16 theo SHA của bản gốc hoặc bản mù
và kiểm thêm dHash với 16 ảnh audit và các ảnh được chọn, ngưỡng 5 bit.
dHash là sàng lọc gần trùng, chưa chứng minh độc lập nguồn. Định danh
ngẫu nhiên giữ trong gói, mức và locator gốc chỉ có trong custody
cục bộ. PNG nguồn runner giữ pixel hiển thị RGB và bỏ metadata.
Cohort đã phơi nhiễm dùng để đo kỹ thuật và phát triển, không dùng
xác nhận hiệu quả.

Runner trả JSON đọc được bằng [bộ chấm CT1](THESIS_CT1_EVIDENCE_PILOT.md).
Model nhận duy nhất ảnh và prompt của arm. C1 và parser A giữ nguyên.
Mỗi hoán vị của A/E/S có 8 ảnh. Một call mỗi cặp ảnh/arm. Matching
từng arm dùng cùng model, revision, bố trí thiết bị, tokenizer/processor,
sampling tắt, đầu vào tối đa 4.800 token và đầu ra tối đa 768 token.
Cùng trần token để so sánh. E/S có thể sinh dài hơn A. Parser áp hợp
đồng từng arm, tách INVALID và đếm riêng lượt chạm token cap. Không đổi
parser hoặc retry để cải thiện coverage. Không thu logits/HNLO ở pilot này.

## Kinh nghiệm Qwen3 và kiểm tra trước gọi

| Bằng chứng cũ | Cách xử lý tại pilot |
|---|---|
| V4 shard S2 dừng OOM, không truy ra device/phép cấp phát chính xác. Hồi cứu thấy peak cao và tác động của per-device placement. | Dùng lại map hai T4, FP16/SDPA và CPU embedding. Kiểm driver, RAM/cgroup, free trên **từng** GPU và tensor FP16 trong runtime đã pin. Reset rope/cache mỗi mẫu, batch 1, theo dõi VRAM và bộ đệm đang dùng. Chỉ giữ token thay vì raw logits từng bước. Ghi dấu mốc và thống kê VRAM trước/sau/lỗi, giữ nguyên output và dừng khi lỗi. Không suy nguyên nhân OOM đã được chứng minh. |
| Lỗi source/layout, ABI và venv trên Kaggle có thể xảy ra dù package tên đúng. | Nạp capsule theo commit và SHA, thư mục opaque theo exact allowlist. Đọc source/wheelhouse từ Inputs bất biến, build CPython 3.12.13 với zlib 1.2.11, cài offline. Xác minh toàn bộ closure, pip check, Torch cu128 và CPU NMS của torchvision, hash source Transformers 4.57.1, marker và weight shards. Không dùng host pip, remote code hoặc tải checkpoint khi chạy. |
| Dữ liệu đầu vào hoặc output thiếu có thể khiến job dừng giữa chừng. | Xác minh hash 48 ảnh, benchmark token của cả 144 prompt bằng processor CPU trước model load, đo disk theo filesystem và kiểm ghi/fsync thật. Giữ deadline, cap log và process-group supervisor. Ghi raw token trước decode và raw text trước parser. |
| Returncode cấp phiên không tự chứng minh đủ lượt. | Đếm native intent riêng, `RETURNED`, `INVALID`, `TECHNICAL_ERROR` và `NOT_ATTEMPTED`. Input payload lỗi không được thay ảnh. Hash ZIP outer và từng member. |

Nguồn lịch sử: [Qwen3 S2 OOM](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/qwen3_s2_oom_20261022.md)
· [Qwen3 Recovery224](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/qwen3_s2_recovery224_20261022.md)
· [Fresh Full-TRAIN](../FRESH_FULLTRAIN_171.md)
· [G0–G6](../KAGGLE_FAILURES_AND_RELEASE_GATES.md).

## Giới hạn tài nguyên và resume

- **144 lượt chính**, trần 3 giờ wall time trong một job. Hai T4 (16 GB class),
  tương đương tối đa 6 GPU-giờ nếu cả hai được giữ suốt job. RAM khả dụng
  trước setup tối thiểu 16 GiB, scratch 14 GiB và output 256 MiB.
  Host cần ít nhất 13.000 MiB free trên mỗi T4 trước load. Sau load,
  kiểm ngưỡng headroom trước từng call. Các mức này là guardrail vận hành,
  chưa xác nhận fit. Runtime ở scratch riêng `/tmp`, không ghi vào Kaggle
  Output. Preflight standalone chạy tối đa 90 phút và zero native calls.
- Nếu 8–30 giây/lượt và 20–40 phút cho tải/thiết lập/xuất, thời gian khoảng
  **39–112 phút**. E/S có thể dài hơn. Nếu 45 giây/lượt và 40 phút overhead,
  khoảng **148 phút**. Cap setup 40 phút, chừa 120 giây cho xuất.
  Phần mềm mount khoảng **4,19 GB** và checkpoint khoảng **17,55 GB**.
  Upload và thời gian lấy Input không nằm trong dự toán native.
- Mỗi entry có intent create-only trước model.generate, rồi returned IDs,
  raw text và parse receipt. Pending chưa bắt đầu vẫn có thể chạy khi
  tiếp tục đúng checkpoint. Intent không có kết quả đã niêm phong
  được giữ nguyên. Nếu token đã ghi, decode lại mà không gọi model.
  Nếu call có thể đã xảy ra và thiếu kết quả, giữ TECHNICAL_ERROR,
  không thử lại. Runtime/scheduler không cấp lại ngân sách từ đầu.
  Giới hạn này dựa trên một chuỗi checkpoint mới nhất được Owner quản lý.
  Hai Kaggle VM rời nhau không có khóa chung.
- Dừng có kiểm soát xuất ZIP partial nếu còn đủ cửa sổ ghi. Đây là
  checkpoint của version, không hứa cứu file nếu nền tảng hard-kill
  cả VM trước giờ xuất. Dùng receipt để đánh giá kết quả, kể cả khi
  notebook lưu được version. Giữ cả log và raw. Không tự mở TEST.

## Tái lập và handoff

```text
python -B -m unittest discover -s tests -p "test_ct1*.py" -v
python -B -m scripts.build_ct1_kaggle_notebooks --check
python -B -m scripts.prepare_ct1_native_pilot source --commit <40-hex> --output <new-source-dir>
```

Trên Windows đặt cwd, TEMP/TMP/TMPDIR và toàn bộ artifact ở D. Lệnh
`images` tạo hai thư mục runner / scoring riêng từ master đã khóa.
Lệnh `software` và `checkpoint` chỉ lấy public bytes đã pin và
không gọi inference hoặc Kaggle. Trước upload chỉ dùng bản đã có seal.
Notebook prep CPU cũ và audit PASS của commit 25558af tiếp tục là
bằng chứng trước thay đổi. Scope audit native độc lập kiểm code và fixture
CPU. Một PASS CPU không chứng minh inference, fit hoặc cải thiện metric.
