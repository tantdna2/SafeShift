# CT1 — Pilot native Kaggle trên 48 ảnh TRAIN

**Candidate trong Draft PR #216.** Owner duyệt riêng một smoke do Antigravity
Operator thực hiện, dùng ledger trên D và lịch sử job Kaggle. Controller
tiếp tục chặn `pilot` trước khi đọc Inputs hoặc tạo ledger. `preflight`
không gọi model. Các bước chạy pilot bên dưới chỉ áp dụng cho bản đã phát hành
sau G4–G6 và quyền chạy pilot riêng.

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
   Một bản xuất hợp lệ cần cả ZIP và sidecar. Nếu chỉ có sidecar hoặc file
   staging `.pending`, giữ để đối soát như một lần xuất chưa hoàn tất.

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

### Smoke v1 trên Kaggle

Version 1 của `nguynanhtn/safeshift-ct1-smoke-pr216`, source `1dd92c9`,
đã thấy hai T4 với driver 580.178.04 ở notebook. Tiến trình setup đã dừng
khi `nvidia-smi` trả code 12 trong môi trường đã cô lập. Worker suy luận
chưa khởi chạy, chưa nạp weights và không gọi model. Kaggle báo
`COMPLETE` vì notebook đã xuất ZIP chẩn đoán. ZIP có SHA-256
`f4db02f500f642dc04269312ad03620b0e80671278d7f441b3401d1f9f9e80d8`.

Setup dùng lại bước tìm thư mục driver được mount và giới hạn đường dẫn
NVML trong subprocess `nvidia-smi`. Worker nạp `libcuda.so.1` từ mount đó
trước khi import Torch, rồi kiểm lại hai T4, driver, VRAM và phép thử FP16
theo ngưỡng cũ. Receipt lưu stdout/stderr có giới hạn của probe. Thay đổi
này cần xác minh native trên lượt được admission riêng. Giữ version 1 và
ZIP chẩn đoán để đối soát.

### Smoke thay thế dừng ở kiểm tra RAM

Job `nguynanhtn/safeshift-ct1-smoke-pr216-v2/1` dùng HEAD `888b3cb`.
Setup hoàn tất sau 350 giây, đã kiểm hai T4 và `pip check` báo sạch.
Bước kiểm RAM của worker dừng với `HOST_OR_CGROUP_RAM` trước khi nạp
weights. Trước setup có khoảng 29,45 GiB khả dụng. Lượt này thiếu số đo
ngay tại lần chặn nên không quy nguyên nhân cho cache hoặc OOM.
ZIP cuối có SHA-256
`4ff19393181288757dfd4b06002bf41b687075449b6b8d985106b84f8c0ccf4b`.
Summary xác nhận 0 lượt gọi và cả A/E/S `NOT_ATTEMPTED`.

Bằng chứng supervisor cho thấy hai nhóm setup/worker không còn tiến trình
sống khi được thu hồi. Receipt setup v2 ghi 31.626.194.944 byte, bằng
headroom cgroup được ghi ở thời điểm đó. Receipt không lưu riêng RAM host.
Không có memory.stat hay bộ đếm OOM tại lúc worker dừng. Các khả năng còn
mở gồm page cache do đọc wheel và ghi runtime, cấp phát ẩn danh và áp lực từ
host/cgroup. Hai lượt đều có 0 lượt gọi. Việc thiếu log từng giai đoạn không
được suy diễn thành OOM kill.

Bản sửa tích hợp chẩn đoán vào notebook smoke hiện có.

- Controller đo trước setup và trong finally sau khi supervisor trả về.
  Setup ghi theo mốc giải nén, build Python/zlib, tạo venv, cài wheel và
  pip check, kể cả khi lệnh setup lỗi. Snapshot ghi MemAvailable và các bộ
  đếm cache của host, cgroup current/max/peak/stat/events nếu có, cùng RSS
  của tiến trình đo. Sau lỗi, bản đo controller được đưa vào ZIP chẩn đoán
  ngay cả khi chưa có worker. Chỉ thu bản đo do setup ghi khi đã xác minh
  nhóm setup dừng. Khi bắt đầu nạp model, controller đo RAM mỗi 5 giây,
  tối đa 48 mẫu, và đo thêm khi supervisor thu hồi worker. Các mẫu độc lập
  với worker có thể được xuất ngay cả nếu worker bị kill. Receipt gate lưu
  các toán hạng thực dùng, ngưỡng 16 GiB, kết quả hoặc lỗi đọc.
- Sau khi setup thoát sạch, worker đối chiếu inode/device của scratch do
  controller tạo. Dùng lại cách MiniCPM V5 fsync rồi
  POSIX_FADV_DONTNEED trên file thường riêng của job từ 1 MiB, trong
  qwen-software/ và ct1-build-archives/. Cây được duyệt tối đa 100.000
  mục, độ sâu 64, trong deadline supervisor. Không đi theo symlink,
  hardlink hoặc cây ngoài scratch. Không xóa file, xóa cache toàn máy hay
  sửa Input. Advice có thể không thu hồi được RAM. Báo riêng lỗi advice
  và đo lại bằng gate hiện hành. Pip CT1 cài offline với cache tắt.
- Giữ gate 16 GiB ở đầu worker, kiểm lại trước hash checkpoint và ngay
  trước from_pretrained. SHA-256 kiểm đủ byte thật theo revision khóa.
  Đọc checkpoint theo khối hữu hạn và dùng advice trên đoạn vừa đọc theo
  tiền lệ InternVL V2, chỉ với phần đọc xong và đủ trang. Nếu filesystem từ
  chối advice, ghi lỗi rồi
  kiểm đủ SHA và vẫn dùng gate RAM tươi. Lưu số đo khi hash/load kết thúc
  hoặc lỗi. Giữ hai T4, FP16/SDPA, device map, giới hạn context và kiểm tra
  headroom trước từng lượt A/E/S. Sau generate, số đo RAM thấp vẫn được
  ghi kèm raw đã trả về. Gate 2 GiB tiếp tục chặn lượt tiếp theo. Mất VM
  trước khi có bằng chứng terminal
  vẫn giữ các quy tắc forensic và không cho resume qua VM.
- [Qwen3 Issue173](../KAGGLE_CHECKPOINTS_173.md#qwen-actual-inference-pass-remaining-peer-continuation)
  đo 4.555.481.088 → 18.531.954.688 byte sau thu hồi cache và hoàn tất một
  lượt Qwen trên hai T4. CT1 dùng wheel mount trực tiếp, nên không có bản
  sao wheelhouse lớn của Issue173 để xóa. MiniCPM V5 có bằng chứng hồi phục
  trong một môi trường khác. InternVL V2 đã chạy với thu hồi page cache
  khi hash. G4–G6 cần bằng
  chứng native từ một lượt được Owner duyệt riêng. Nếu gate RAM tiếp tục
  chặn, dùng receipt mới để phân biệt host với cgroup và so
  file/anon/inactive_file trước khi cân nhắc thay đổi điều kiện chạy.

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
  đối soát, dùng đuôi `-diagnostic.zip` và ghi rõ lỗi tái dựng. Các receipt
  qua đường dẫn alias, không phải file thường, quá giới hạn hoặc thay đổi
  khi đọc bị bỏ khỏi bản sao chẩn đoán. Tên ZIP kết quả chỉ công bố sau khi
  bản staging đã qua xác minh và sidecar đã được ghi.
- ZIP và SHA chỉ xác minh nội dung của một snapshot. Hai VM Kaggle không
  có khóa hoặc bằng chứng chung về snapshot mới nhất. Runner hiện từ chối
  mọi yêu cầu resume qua VM mới trước khi đọc Inputs hoặc mở ngân sách. Một
  marker local cũng không thể phân biệt lần đầu và lần chạy lại sau khi VM
  cũ mất. Riêng smoke dùng admission của Operator đã được Owner duyệt.
  Khi VM mất hoặc ZIP bị cắt, có thể không còn gì để thu thập. Giữ nguyên
  mọi lượt đã đặt trước hoặc chưa đối soát. TEST tiếp tục khóa.

## Vận chuyển Input và upload của Owner

Kaggle giải nén `ct1-source.zip` cả khi nằm trong TAR. Bản sửa lưu ba archive
theo canonical Base64 ở các file `*-base64.bin`. Notebook kiểm kích thước,
Base64 và SHA-256 gốc trước khi mở ZIP nguồn. Setup child phục hồi hai archive
Python/zlib vào scratch riêng, đối chiếu kích thước và SHA trước khi chạy
provision. Wheel vẫn nằm dưới `wheels/` và được kiểm đủ tên, kích thước, SHA
theo lock. Không copy wheelhouse sang VM scratch. Marker phần mềm giữ nguyên.
Runner chỉ nhận đúng bốn mount đã khóa ở root cũ hoặc
`/kaggle/input/datasets/nguynanhtn/` và chặn mount trùng.

Giữ `nguynanhtn/ct1-train48/1` và `nguynanhtn/ct1-qwen-checkpoint/1` đã xác
minh byte. Từ gốc repo, dùng `python -B -m scripts.prepare_ct1_native_pilot transport`
với `--commit`, `--software-input`, `--software-marker-sha256` và `--output`
để chuẩn bị hai thư mục riêng. Biên nhận nằm ngoài hai thư mục upload.

Owner trực tiếp upload Dataset và Notebook. Antigravity chỉ chuẩn bị và xác
minh read-only phiên bản private, danh mục file, byte/SHA toàn bộ wheel và
archive, code notebook cùng thiết lập sau upload. Dùng **Quick Save** để
xác minh notebook mà chưa thực thi. Không dùng CLI `submit` thay Owner nếu
nó gửi lại code notebook. Việc chạy chờ xác minh đường admission phù hợp
với chỉ thị upload của Owner.

## Smoke kỹ thuật trên đúng runtime

- Một job private, Internet tắt, hai T4, tối đa 90 phút wall time (tối đa
  3 GPU-giờ). Dùng cùng source capsule, checkpoint revision, software và gói
  TRAIN mù đã niêm phong. Runner kiểm đủ 48 ảnh rồi chỉ chạy ảnh đầu tiên theo
  plan, mỗi cấu hình A/E/S một lượt. Tối đa 3 lượt, không retry và không mở GT,
  annotation, nhãn thư mục hoặc TEST.
- `scripts.submit_ct1_smoke` gọi cùng builder cho smoke, gắn request SHA
  và run ID dạng `ct1-smoke-<12 hex>`. Smoke đi qua cùng setup, preflight, tải weights, model,
  ngân sách token, parser và đường xuất ZIP. Kiểm 2 T4/VRAM trước và sau load/call,
  latency theo arm, 3 intent và 3 raw trước parse, trạng thái parse từng arm,
  log, kết thúc process group, ZIP và SHA outer/từng member. Đối chiếu cả
  INVALID nếu có. Software/preflight/VM RUNNING riêng lẻ chưa xác nhận smoke.
- Thư mục và ZIP smoke có run ID riêng, dùng `smoke-runs.json` và dấu scope
  riêng. Bộ chấm nghiên cứu không nhận output này. Không đưa ba lượt smoke vào
  144 lượt chính, không dùng smoke để suy luận chất lượng hoặc độ bền của toàn
  pilot. Chỉ chạy khi xác minh quyền, các mount private đúng phiên bản,
  kết nối Kaggle, hai T4 và quota còn đủ.

### Một Operator và một job

- Operator giữ một thư mục ledger cố định `data/processed/ct1-native-operator/pr216-smoke`
  dưới gốc dự án Windows trên D. Request cục bộ gồm `settings` nguồn/mount
  khóa như builder, `inputs` gồm bốn role `source/pilot_input/checkpoint/software_input`
  ánh xạ tới ref private `owner/slug/version`, `kaggle_owner` đã xác minh và
  `data_authority_ref` dẫn quyền dữ liệu. Request SHA nằm trong notebook và
  evidence identity. Không ghi GT, annotation, token hoặc ảnh vào request.
- Dùng `python -B -m scripts.submit_ct1_smoke prepare --request <request.json> --notebook-output <smoke.ipynb>`
  trên D để chuẩn bị notebook. Khi đúng source, notebook SHA và bốn Inputs đã
  được xác minh, Operator đối soát lịch sử job và quota. Đường `submit` cũ
  giữ lock OS qua một POST và ghi độc quyền, fsync `PUSH_INTENT` trước POST,
  nhưng POST cũng upload code notebook. Khi chỉ thị Owner upload còn áp
  dụng, agent không dùng đường đó. Tên notebook cố định
  `safeshift-ct1-smoke-pr216`.
- Khi lỗi, mất phản hồi hoặc trạng thái chưa rõ, giữ intent và đối soát read-only
  cùng job ref/version. Không gửi lại, đổi slug, xóa ledger hay cấp lại lượt.
  Khóa và ledger chặn phát lại qua công cụ trên D. Kiểm soát bằng quy trình
  là chỉ Operator sử dụng quyền submit, giữ custody, không Run thủ công hoặc
  từ máy khác. Request SHA nhận diện request, không phải claim dùng một lần
  của Kaggle. Hai VM không chia sẻ khóa ledger.

[Tiền lệ Operator và PUSH_INTENT của TRAIN3763](../TRAIN3763_CAMPAIGN.md#historical-pr181-implementation-contract-and-acceptance)

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
