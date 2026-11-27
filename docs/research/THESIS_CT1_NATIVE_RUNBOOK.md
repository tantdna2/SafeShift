# CT1 — Pilot native Kaggle trên 48 ảnh TRAIN

**Candidate trong Draft PR #216.** CPU tổng hợp và kiểm tra bytes có thể xác
minh trước khi chạy. Khi chưa có receipt smoke của đúng source và Inputs, G4–G6
vẫn chặn phát hành. Các bước chạy pilot chỉ áp dụng sau khi các cổng này hoàn tất.

## Owner chạy khi đã duyệt đúng SHA

1. Tạo notebook **private**, import notebook pilot từ bộ bàn giao. Chọn
   **GPU T4 ×2**, tắt Internet. Trong Add Input, attach riêng bốn Input
   private chứa source capsule, pilot ảnh mù, snapshot Qwen3 và bộ
   phần mềm đã ghim. Đối chiếu các mount với bộ cấu hình đã khóa. Phần
   checkpoint chỉ trỏ đến thư mục mang đúng tên revision chứa các
   file đã khóa. Đính kèm **chỉ** thư mục `pilot-input`, bên trong có
   `plan.json`, `exclusions.json` và 48 PNG tên mù. Giữ
   `private-scoring` trên D. Không attach archive/dataset InspecSafe
   gốc, GT, annotation, TXT, checkpoint của model khác hoặc TEST.
2. Kiểm tra SHA notebook **đã render** và capsule, plan SHA, marker
   phần mềm và run ID trong biên nhận. Nếu mount thực tế khác, cập
   nhật JSON cấu hình cục bộ rồi render và kiểm SHA mới trước khi
   import. Giữ `resume: None` cho lần đầu. Driver quan sát được, tối
   thiểu 570.26 trên Linux, được khóa trong identity kể cả khi
   danh sách driver được phép có nhiều phiên bản.
   Dùng notebook preflight riêng nếu muốn kiểm môi trường với cùng
   Inputs mà không chạy model. Notebook pilot chạy lại các gate trước
   khi load và thực hiện **Save Version → Save & Run All** một lần.
3. Giữ output `<run_id>.zip` và `<run_id>.zip.sha256.json`.
   Kiểm `summary.json`, `controller-failure.json` nếu có và nguyên
   nhân trong log. Chấm `runs.json` cục bộ với công cụ CT1 và GT riêng.
   Khi lỗi, giữ mọi ZIP, sidecar, log và lịch sử job để đối soát. Nếu chỉ
   có `<run_id>-diagnostic.zip` hoặc không có ZIP, dừng. Không attach ZIP cũ,
   chạy lại notebook trên VM mới hay cấp lại lượt khi thiếu bằng chứng.
   `resume` phải là `None` và chỉ áp dụng cho lần khởi chạy đầu tiên đã được cấp.

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
Bộ đóng gói và runner cùng dùng giới hạn tối đa 2.560 pixel mỗi
chiều và 3.686.400 pixel mỗi ảnh. Bộ đóng gói chạy lại phép mở PNG
của runner trước khi đưa ảnh vào cohort.
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
- Mỗi entry ghi và fsync dưới tên tạm, rồi xuất bản record hoàn chỉnh
  bằng rename. Intent hoàn chỉnh bắt buộc trước model.generate. Giữ
  file tạm còn lại sau ngắt và coi intent tạm là lượt bất định. Nếu còn
  token hoàn chỉnh, có thể decode để đối soát mà không gọi model. Nếu call có
  thể đã xảy ra và thiếu kết quả, giữ TECHNICAL_ERROR và lượt đã đặt trước.
- Controller chỉ đóng dấu ledger sau khi hai receipt ghi nhận đã chờ tiến
  trình chính thoát và không thấy thành viên còn sống trong process group.
  Nếu còn tiến trình sống, cleanup không xác minh được, hoặc thiếu receipt,
  controller giữ nguyên thư mục đang viết và chỉ xuất ZIP chẩn đoán với
  các receipt đã có. ZIP này không chứa ledger hoặc kết quả có thể dùng
  làm checkpoint. Nếu đã xác minh dừng nhưng ledger hỏng, ZIP chỉ phục vụ
  đối soát và ghi rõ lỗi tái dựng.
- ZIP và SHA chỉ xác minh nội dung của một snapshot. Hai VM Kaggle không
  có khóa hoặc bằng chứng chung về snapshot mới nhất. Runner hiện từ chối
  mọi yêu cầu resume qua VM mới trước khi đọc Inputs hoặc mở ngân sách. Khi
  VM mất hoặc ZIP bị cắt, có thể không còn gì để thu thập. Giữ nguyên lượt
  đã đặt trước hoặc chưa đối soát, không làm mới bằng cách chạy lại notebook
  với `resume: None`. TEST tiếp tục khóa.

## Smoke kỹ thuật trên đúng runtime

- Một job private, Internet tắt, hai T4, tối đa 90 phút wall time (tối đa
  3 GPU-giờ). Dùng cùng source capsule, checkpoint revision, software và gói
  TRAIN mù đã niêm phong. Runner kiểm đủ 48 ảnh rồi chỉ chạy ảnh đầu tiên theo
  plan, mỗi cấu hình A/E/S một lượt. Tối đa 3 lượt, không retry và không mở GT,
  annotation, nhãn thư mục hoặc TEST.
- Render bằng cùng builder với `--mode smoke` và run ID dạng
  `ct1-smoke-<12 hex>`. Smoke đi qua cùng setup, preflight, tải weights, model,
  ngân sách token, parser và đường xuất ZIP. Kiểm 2 T4/VRAM trước và sau load/call,
  latency theo arm, 3 intent và 3 raw trước parse, trạng thái parse từng arm,
  log, kết thúc process group, ZIP và SHA outer/từng member. Đối chiếu cả
  INVALID nếu có. Software/preflight/VM RUNNING riêng lẻ chưa xác nhận smoke.
- Thư mục và ZIP smoke có run ID riêng, dùng `smoke-runs.json` và dấu scope
  riêng. Bộ chấm nghiên cứu không nhận output này. Không đưa ba lượt smoke vào
  144 lượt chính, không dùng smoke để suy luận chất lượng hoặc độ bền của toàn
  pilot. Chỉ chạy khi xác minh quyền, các mount private đúng phiên bản,
  kết nối Kaggle, hai T4 và quota còn đủ.

## Tái lập và handoff

```text
python -B -m unittest discover -s tests -p "test_ct1*.py" -v
python -B -m scripts.build_ct1_kaggle_notebooks --check
python -B -m scripts.prepare_ct1_native_pilot source --commit <40-hex> --output <new-source-dir>
python -B -m scripts.build_ct1_kaggle_notebooks --settings <sealed-settings.json> --mode pilot --output <new-owner-notebook.ipynb>
```

Cấu hình JSON cần được giữ cùng SHA notebook đã render. Notebook template
trong Git phục vụ tái lập. Bộ bàn giao cung cấp SHA riêng của từng notebook
đã render và SHA cấu hình tương ứng. Không chỉnh trực tiếp ô notebook sau
khi chốt SHA.

Trên Windows đặt cwd, TEMP/TMP/TMPDIR và toàn bộ artifact ở D. Lệnh
`images` tạo hai thư mục runner / scoring riêng từ master đã khóa.
Lệnh `software` và `checkpoint` chỉ lấy public bytes đã pin và
không gọi inference hoặc Kaggle. Trước upload chỉ dùng bản đã có seal.
Notebook prep CPU cũ và audit PASS của commit 25558af tiếp tục là
bằng chứng trước thay đổi. Scope audit native độc lập kiểm code và fixture
CPU. Một PASS CPU không chứng minh inference, fit hoặc cải thiện metric.
