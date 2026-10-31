# DEC-20261031-CANDIDATE160-RECOVERY

Ngày31/10/2026, Asia/Bangkok. Nguồn: chỉ thị trực tiếp của SafeShift Owner trong
task mã nguồn “Loại bỏ cơ chế One-Shot/No-Retry” trên main mới nhất
`6252a7de91d9d98bd68a33b9bc13ae9888f2b9da`. Không có permalink chat được
cung cấp; không bịa approval ref hoặc chữ ký. Chỉ thị vận hành đã được Owner
giao; implementation ở Draft chờ ChatGPT review và Antigravity audit độc lập.
Không quyền merge, chạy GPU hoặc tiêu lượt thực nghiệm trong task này.

Quyết định này bổ sung [quyết định Owner30/10](CANDIDATE160_OWNER_DECISION_20261030.md)
và [ngoại lệ replacement1](CANDIDATE160_KAGGLE_ENV_DECISION_20261030.md).
Không sửa bytes các quyết định lịch sử. Phần cấm retry/resume và giới hạn
replacement1 của hai notebook Owner được thay bằng quản lý attempt dưới đây;
các điều kiện dữ liệu/kỹ thuật/khoa học còn lại giữ nguyên.

## Phạm vi vận hành Owner yêu cầu

- Đúng hai model InternVL3.5 HF/MiniCPM-V-4 và160 TRAIN/order hiện hành. Không
  đổi revision/checkpoint/public source hashes, C1/parser/HNLO/generation,
  metric/nhãn/protocol hoặc quyền dữ liệu. Không TEST/FULL TRAIN/ảnh bổ sung.
- Mỗi lần Save & Run All tạo run ID/attempt ID mới, có history digest, snapshot
  members SHA256, lineage và nhật ký consumption riêng. Không ghi đè, xóa hoặc
  mở lại journal cũ, kể cả lỗi load, raw write, partial hoặc UNKNOWN consumption.
- Một load/model mỗi attempt; một native call/ảnh được schedule trong attempt;
  tối đa160 calls và12 giờ tính từ đầu attempt. Lỗi kỹ thuật dừng ngay. Không
  vòng tự retry/backoff/relaunch; một lần Owner chạy notebook là một attempt.
- Mặc định `resume`: kiểm mọi lịch sử hiện có rồi chỉ schedule ảnh chưa có raw
  hoàn chỉnh/custody/parse/HNLO replay hợp lệ trong series vận hành hiện hành.
  INVALID hợp lệ cũng hoàn thành; không retry vì nhãn hoặc behavior không tốt.
  Raw hợp lệ bị ngắt trước result có thể được replay trong recovery plan mới,
  giữ nguyên journal lỗi/dở cũ. Nonfinite/replay failure không đủ completion.
- `rerun` là yêu cầu rõ chạy lại toàn bộ160 ảnh, tạo series mới. Các resume tiếp
  theo chỉ xét completion của series đó; lịch sử mọi series vẫn được giữ và
  đếm. Series được tiếp nối theo quan hệ ancestor, không theo score/label/thời
  điểm sửa file. Hai history heads độc lập làm resume BLOCKED; Owner có thể
  khởi tạo một series rerun mới giữ cả hai heads, không tự hợp nhất kết quả.
- Có thể attach saved Outputs ở phiên Kaggle mới, dạng evidence directory hoặc
  ZIP nguyên vẹn. Deduplicate bản sao theo run ID + exact snapshot hashes;
  sai checksum, thiếu ancestor, marker không có run hoặc copies mâu thuẫn chặn
  trước model load. Lịch sử không nhìn thấy không thể được suy ra tự động.
- `BLOCKED_RESERVED_NO_RETRY`, `CONSUMED`, UNKNOWN và `replacement1` cũ là
  evidence, không lệnh khóa vĩnh viễn. Mỗi lần khôi phục dùng ID mới; không sửa
  status/marker lịch sử hoặc reset số lần gọi cũ thành0.
- OS lock chặn hai tiến trình cùng workspace. Linux worker kế thừa descriptor
  để giữ khóa nếu supervisor chết trước worker. Không stale-lock deletion hoặc
  TTL tự vượt một worker còn sống. Hai Kaggle VM không shared filesystem không
  thể có distributed lock từ file local: Owner phải dừng phiên trước, không
  chạy concurrent cùng model và attach đầy đủ Outputs. Không claim exactly-once
  toàn cục hoặc phát hiện được lịch sử cố tình bỏ khỏi Inputs.

## Ranh giới khoa học

**SCIENTIFIC_RESULT_SELECTION=PENDING; pooling_allowed=false.** Resume/rerun
chỉ cung cấp dữ liệu vận hành có truy vết. Không tự dùng completion union làm
cohort khoa học, chọn first/latest/best successful result, thay baseline, gộp
metric/AUROC, loại lỗi/INVALID hoặc quyết định scientific qualification.
`INITIAL`, `RECOVERY`, `FULL_RERUN`, series/run/attempt IDs và mọi bản raw còn
riêng. Metrics sẵn có chỉ thuộc attempt đang báo cáo, không composite analysis.
Muốn dùng các lượt cho phân tích phải có quyết định khoa học mới trước áp dụng.

Giữ technical-stop/behavior-observe hiện hành; không thêm ngưỡng chất lượng.
Preflight environment-first và mọi gate hash/ABI/storage/CUDA/resources giữ
nguyên. CPU scripted tests không là Kaggle/GPU/model-fit/inference PASS.

## Trạng thái bàn giao

Một Draft PR gồm code/notebooks/builder/tests/runbook/PROJECT_STATE và bằng chứng
CPU. ChatGPT kiểm GitHub, Antigravity audit độc lập, quyền merge và xác minh
hậu merge còn PENDING; task này không gọi Antigravity hoặc merge.
