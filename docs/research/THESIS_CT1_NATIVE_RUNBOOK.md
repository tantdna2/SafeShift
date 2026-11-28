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
  nhóm setup dừng. Controller dùng luồng quan sát riêng để đo RAM khoảng
  mỗi 5 giây khi nạp model, tối đa 48 mẫu, và đo thêm sau khi thu hồi worker.
  Supervisor vẫn dừng worker theo deadline kể cả khi luồng quan sát bị kẹt.
  Controller niêm phong một bản ghi giới hạn trước thời gian dự trữ xuất ZIP,
  kể cả nếu worker bị kill. Ghi rõ khi thiếu số đo sau worker. Receipt gate
  lưu các toán hạng thực dùng, ngưỡng 16 GiB, kết quả hoặc lỗi đọc.
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

### Lượt sau bản thu hồi cache dừng trước khi băm checkpoint

Notebook private `safeshift-ct1-smoke-pr216-ram-candidate/1` chạy source
`f47c2a3`, run `ct1-smoke-43325b48e104`. ZIP và manifest xác minh đủ
44 mục, SHA-256
`bb28caf3dab376a8ef7172423468f784c9d64639f3700b54d417c96a63e70f3d`.
Kaggle báo COMPLETE sau khi xuất `PARTIAL_OR_BLOCKED`. Cả A/E/S đều
`NOT_ATTEMPTED`, với 0 intent và 0 lượt trả về.

| Mốc đo | Headroom cgroup | File cache | Anon |
| --- | ---: | ---: | ---: |
| Sau khi cài wheel | 10,16 GiB | 18,99 GiB | 0,27 GiB |
| Sau thu hồi cache cục bộ | 16,72 GiB | 12,61 GiB | 0,26 GiB |
| Sau các probe và trước hash | 15,84 GiB | 13,10 GiB | 0,65 GiB |

Cgroup giới hạn 30 GiB và tại cổng thiếu 166,99 MiB. Host báo còn
29,38 GiB, bộ đếm OOM bằng 0. Hai T4 báo 14.912 MiB trống mỗi GPU.
Các mốc chỉ cho biết mức tăng khoảng 909 MiB trong cả cụm probe, chưa
định lượng từng thao tác. Chưa bắt đầu băm hoặc nạp shard.

Bản sửa gom ABI, hai CUDA FP16 probe và kiểm token vào subprocess riêng
không nạp weights. Sau khi thu hồi toàn bộ nhóm probe, worker nhẹ đo lại
RAM cgroup và băm checkpoint theo khối trước khi import Torch. Chỉ khuyến
nghị kernel nhả cache cho file job sở hữu, wheel đã niêm phong và shard
đã nạp. Linux có thể bỏ qua advice. Lỗi một hint được ghi theo loại và
tệp, SHA của tất cả shard vẫn bắt buộc. Ngay trước `from_pretrained`,
đo lại VRAM từng T4 và áp dụng nguyên ngưỡng 16 GiB. Nếu phép đo sau
generate bị lỗi, vẫn lưu raw đã sinh trước parse và ghi trạng thái số
đo riêng. Nếu còn lượt chưa trả về, ZIP ghi `PARTIAL_OR_BLOCKED` ngay cả
khi worker kết thúc sạch. Giá trị RAM khi load, đỉnh VRAM và kết quả
parser A/E/S vẫn cần một lượt được duyệt riêng.

### Rà soát ranh giới ghi kết quả và giờ kết thúc của smoke

- Tính hạn controller smoke từ ô notebook đầu tiên. Controller kết thúc
  trước phút 85, dành 120 giây cuối trong khoảng đó cho ZIP. Notebook chờ
  controller tới phút 87,5. Kaggle có ngân sách 90 phút. Khoảng đệm này
  không đo được thời gian Kaggle dùng để khởi tạo container trước ô đầu.
- Ghi token, raw và kết quả parse trước số đo RAM/VRAM sau generate. Nếu
  worker bị dừng giữa token và raw, ZIP giữ token và ghi số lượt
  `durable_tokens_without_raw`. Không suy lượt trả về, chạy lại hoặc nhập
  lượt smoke vào bộ chấm từ token chưa đối soát.
- Kaggle COMPLETE đi kèm archive forensic hoặc `PARTIAL_OR_BLOCKED` vẫn
  là smoke dừng. Receipt đóng nhóm chỉ chứng minh không còn tiến trình
  ghi ledger, kể cả khi worker lỗi hoặc chạm deadline.
- Accelerate 1.11.0 có thể đưa trọng số embedding đang offload trên CPU
  tới thiết bị thực thi theo từng forward. Giữ nguyên device map đã khóa.
  Đo đỉnh VRAM từng GPU và thời gian thật từng arm để phân biệt chi phí
  offload với các lỗi kỹ thuật còn lại. CPU audit chưa xác nhận mức đỉnh
  hoặc tốc độ này ở 768 token.
- Sau khi native worker tạo processor, nếu phép đo ban đầu dưới 16 GiB,
  thử nhả cache runtime một lần trong scratch của job. Sau đó đo lại
  nguyên ngưỡng RAM và VRAM từng T4 trước load. Advice không cấp quyền hoặc
  bảo đảm kernel sẽ thu hồi đủ RAM.

### Smoke sau khi nạp checkpoint chạm hạn giờ

Lượt `ct1-smoke-a44b40fd71fa` tại `c0a9db6` qua RAM 16 GiB và GPU,
băm checkpoint khoảng 102 giây, hoàn tất shard đầu sau 39m02s rồi dừng
theo hạn mà chưa có intent. ZIP 66 mục đã xác minh với SHA-256
`66ed69314aaa3afcfb14b03d0af24c3d16ea58764a47b91c493b6ca8969f8e0c`.
Đọc shard qua mmap, cast sang FP16 và chuyển tensor chưa được đo riêng.

- Smoke dùng một bản snapshot scratch có ownership của job. Stage ghi
  thông tin mount, loại filesystem và dung lượng trước/sau, từ chối bộ
  nhớ như tmpfs và giữ 14 GiB scratch, 256 MiB Output cùng biên 2 GiB
  ngoài checkpoint. Ghi đồng bộ từng khoảng và chỉ advice trang đã ghi
  trên file tạm do job sở hữu. Hash input trong lúc copy rồi mở lại và
  hash toàn bộ file đích. Kiểm inode, kích thước và thời điểm sửa trước
  khi load. Giữ snapshot tạm trong VM qua khi worker kết thúc.
- Setup, runtime probe, stage, so I/O và native worker dùng process group
  riêng. Stage tối đa 600 giây. Probe bốn mẫu 4 MiB trên hai đường có
  tối đa 30 giây, ghi rõ cache chưa chuẩn hóa. Probe có thể chủ động
  bỏ mẫu chưa bắt đầu rồi kết thúc sạch. Timeout cưỡng bức, lỗi I/O
  hoặc sai SHA của mẫu so sánh dừng trước load.
  Controller dùng pipe nonblocking để xác nhận model-loaded trong tối đa
  900 giây kể từ khi mở native worker gồm khởi tạo processor và load,
  luôn nằm trong cutoff tổng. Chừa export reserve hiện có.
- RAM admission CT1 lấy min giữa host và cgroup v2 nhìn thấy gồm
  các ancestor. Giữ ngưỡng trước load 16 GiB và 13.000 MiB từng T4. Giữ
  mẫu đầu và mẫu gần nhất trong pha load, số đếm file/anon/fault và
  số liệu process khi đọc được. Sau load ghi peak theo GPU; từng slot
  lưu thời gian chuẩn bị, generate và đến lúc có raw/parse. Dừng mở
  intent khi cửa sổ còn lại thấp hơn 120 giây hoặc 120% lượt dài nhất
  quan sát được, lấy mức lớn hơn. Đây là giới hạn vận hành, không phải
  đảm bảo slot tiếp theo xong trong khoảng đó.
- Khi stage/probe có lỗi, chỉ xuất receipt thuộc group đã đóng. Dừng
  hay mất VM không cấp lại lượt. Notebook smoke private, Internet Off,
  T4 ×2, một ảnh × A/E/S, tối đa 3 lượt, không retry. Owner upload source
  và notebook mới rồi Quick Save để Operator đối chiếu. Admission
  dựa trên đúng SHA/phiên bản và quyền đã cấp. Cap controller từ cell
  đầu khác giới hạn thời gian chờ/lưu Output của provider.
- CPU kiểm toàn bộ custody, loader ingress và hồi quy; xác nhận native
  còn chờ Owner chạy. Ba lượt smoke không đủ để lập phân vị latency
  hay mở pilot. Pilot 48 ảnh/144 lượt và TEST tiếp tục khóa.

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
  với chỉ thị upload của Owner. Đường Owner UI hiện render bằng
  `prepare` với trường request `owner_ui_slug`, khóa đúng ref riêng và phiên bản
  chạy v2 sau Quick Save v1. Kiểm code và bốn Input trước khi Owner chạy
  v2. SDK submit từ chối request Owner UI trước khi tạo ledger.

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
