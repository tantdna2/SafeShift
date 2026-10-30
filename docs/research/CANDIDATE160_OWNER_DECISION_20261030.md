# DEC-20261030-CANDIDATE160-OWNER — chỉ thị Owner, implementation chờ audit

- Ngày: **30/10/2026, Asia/Bangkok**. Người quyết định: SafeShift Owner trong
  task trực tiếp của cuộc hội thoại này. Codex ghi lại, không tự phê duyệt khoa học.
- Nguồn: task “ĐƠN GIẢN HÓA CHẠY KAGGLE SAFESHIFT”, base main sau #153
  `fc1e454212455685e1775601ebfd6aab9535c932`; GitHub #153 merged=true đã kiểm.
  Không có permalink của chat được cung cấp; không bịa approval URL/ref/chữ ký.
- Nguồn GitHub: [bản ghi chỉ thị Owner tại PR #153](https://github.com/tantdna2/SafeShift/pull/153#issuecomment-6516812967).
  Đây là bản ghi chỉ thị Owner do ChatGPT chuyển lên GitHub, không phải chữ ký
  phê duyệt của giảng viên, Research Lead hoặc bên thứ ba; không xác nhận quyền
  pháp lý bên ngoài hay nghiệm thu học vụ.
- Chỉ thị trực tiếp: “Owner đã trực tiếp yêu cầu không tiếp tục quy trình hỏi
  phê duyệt thủ công lặp lại cho các lượt chạy thuộc quyền của Owner.”
  Owner yêu cầu triển khai cơ chế chủ động kích hoạt, tự sinh định danh/consumption
  log và chống trùng; Save & Run All không cần CONTINUE thủ công.
- Phạm vi: đúng InternVL3.5 HF và MiniCPM-V-4 đã khóa revision, mỗi model một
  lượt ≤160 ảnh TRAIN theo manifest/order lịch sử, dataset/checkpoint Owner đã
  upload. Không retry/resume/overwrite, không đổi model/version/dataset/nhãn/
  parser/C1/HNLO. SHA/Python/CUDA/GPU/VRAM/storage/input/raw/archive giữ bắt buộc.
- Không suy quyền với dữ liệu/tài nguyên bên thứ ba, TEST, annotation mới,
  thí nghiệm khác, FULL TRAIN hoặc quyết định khoa học/academic chưa có.
  G0/T0/O3/Lead refs của cơ chế cũ không được giả tạo; log mới chỉ ghi việc Owner
  kích hoạt trong phạm vi này. Chưa xác minh độc lập quyền pháp lý của upload.
- Thay thế **chỉ thủ tục lặp lại của hai notebook Owner này** trong proposal
  batch #153: không grant/reservation file riêng, external approval refs, batch
  delegation hoặc checkpoint CONTINUE do người dùng đưa vào. Luồng cũ còn giữ
  cho compatibility; không sửa hồi tố quyết định/protocol/config đã khóa.
- Điều kiện triển khai: đúng **một Draft PR**, dừng chờ ChatGPT kiểm GitHub và
  audit độc lập trước merge. Không chạy GPU hoặc dùng private data trong task này.
  Chỉ thị Owner đã có; implementation chưa đồng nghĩa audit PASS hoặc GPU PASS.

## Thay đổi chính sách dừng được trình review, không tự duyệt scientific limits

Owner chưa quyết định numerical INVALID/repetition/dominance/FPR/FNR/support
thresholds của proposal #153. Implementation không phát minh các giá trị đó và
không đặt tất cả bằng160/1 để giả thành approval. Luồng Owner ghi behavior mỗi
ảnh và review sau lượt chạy; **không dừng vì behavior/support**. Technical errors,
NaN/Inf, raw/custody/replay failure, resources/deadline vẫn dừng ngay.
Behavior collapse có thể tiêu đủ160 calls; COMPLETED không là model qualification.
Đây là thay đổi thực sự so với #153, phải được mô tả trong PR để Owner/reviewer
đánh giá trước merge, không phải tuyên bố Owner đã duyệt một threshold mới.

Engineering settings mới, công khai để reviewer đánh giá: CUDA12 Linux driver
floor525.60.13 + actual child probe thay allowlist chưa quyết định; live RAM/cgroup
4GiB, scratch/output1GiB mỗi nơi, GPU0 free256MiB sau load; supervisor deadline12h.
Giữ disk admission28+4GiB và GPU0 pre-load14GiB. Không là scientific thresholds
hoặc bảo đảm checkpoint fit; actual hardware/checkpoint vẫn UNVERIFIED.

## Nhật ký và giới hạn chống trùng

`owner_execution` là schema riêng không có quyền/approval giả. Save & Run All
là kích hoạt, máy sinh UUID và slot cố định campaign/model/revision/cohort,
exclusive create+fsync trước private inputs; không release kể cả preflight fail.
Consumption không chắc chắn ghi UNKNOWN/do-not-retry. Ledger và terminal log
tự ghi, không cần Owner ký/cập nhật permission record lặp lại.

Khóa bảo vệ cùng output root và lịch sử saved Outputs được attach theo layout
chuẩn. Không distributed lock hoặc chứng thực người bấm nút: Kaggle VM mới
không lịch sử hoặc concurrent VM có thể vượt phạm vi quan sát filesystem.
Owner chỉ tạo một saved job/model, không xóa marker/tạo session thay thế/retry.
Không tuyên bố global exactly-once. Dữ liệu/checkpoint/raw không đưa vào Git.

[Runbook](../CANDIDATE160_KAGGLE.md) và
[CPU acceptance](CANDIDATE160_OWNER_CPU_20261030.md) ghi implementation/tests;
M1/M2/DECISIONS lịch sử giữ nguyên bytes.
