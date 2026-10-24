# Hướng dẫn làm việc với SafeShift

## Phạm vi hiện tại

- Đọc `AGENTS.md`, `README.md` và `docs/ROADMAP.md` trước mỗi task; task liên quan
  code phải đọc thêm `docs/ARCHITECTURE.md`. Task description là phạm vi công việc
  hiện tại. Root `ROADMAP.md` và `TASKS.md` thuộc lịch sử trước reset, không có trên
  main mới; tra qua `docs/HISTORY.md` khi cần, không tạo lại các log cũ.
- Foundation V1 có record/validation, phép đếm classification cơ bản, model
  transport interface và demo CPU tổng hợp. Không có dataset parser/backend hay
  quyền thực nghiệm mới. Xác định phạm vi được giao, giữ file local ngoài phạm vi.
- Sau tài liệu đầu vào, chỉ đọc module/test và nguồn hợp đồng liên quan theo
  bảng định tuyến trong ARCHITECTURE; không nạp toàn bộ 693 file lịch sử.
- Code, notebook, môi trường, test và hồ sơ nghiên cứu cũ nằm tại các ref lưu trữ
  ghi trong `docs/HISTORY.md`. Tra cứu bằng đúng commit; không nhập lại code cũ
  vào main khi chưa được review và chấp thuận.

## Bảo vệ lịch sử và thẩm quyền nghiên cứu

- Giữ bất biến nhánh `legacy/pre-reset-20261024` và annotated tag
  `safeshift-pre-reset-20261024`; không di chuyển, ghi đè hoặc force-push các ref này.
  Không viết lại lịch sử Git hoặc sửa source lock để chạy release cũ ở HEAD mới.
- D9R22 vẫn là phạm vi có hiệu lực trong hồ sơ nghiên cứu; DEC-PA3-011 vẫn
  **PROPOSED**. Hướng A/C chưa được phê duyệt. Reset không hủy quyết định đã có,
  phê duyệt hướng mới, thay đổi kết quả/AUROC hay nâng trạng thái kiểm toán.
- Quyền thực thi cũ chỉ áp dụng cho đúng source/release/run/attempt đã cấp;
  không chuyển quyền đó sang main mới. GPU, inference, đọc TEST/dữ liệu bị khóa,
  nhãn/annotation và thí nghiệm mới đều cần phạm vi và quyền cụ thể.
- Không tự thay dataset, split, nhãn, metric, protocol hoặc roster. Giữ yêu cầu
  Seminar bốn mô hình trong hồ sơ cũ; mọi thay đổi cần Research Lead duyệt và ghi
  vào log quyết định mới dưới `docs/` trước khi áp dụng, không sửa quyết định cũ.
- Phân biệt bằng chứng đã kiểm chứng, thông tin được cung cấp, giả thuyết và câu
  hỏi mở; dẫn nguồn. Không bịa kết quả hoặc coi TRAIN đã phơi nhiễm là holdout.
- Sáu Draft PR cũ được liệt kê trong `docs/HISTORY.md`; không tự sửa, đóng,
  rebase hoặc merge chúng khi làm việc trên cấu trúc mới.

## Dữ liệu và Git

- Giữ nguyên dữ liệu gốc. Sản phẩm dẫn xuất local đặt trong `data/processed/`,
  có quy trình tạo lại rõ ràng; cả `data/` được ignore mặc định trên main mới.
- Không commit dataset, ảnh/video thật, archive dữ liệu, checkpoint, raw model
  output hoặc artifact lớn, secrets hay credentials, kể cả qua Git LFS.
- Chỉ version control code, tài liệu và fixture nhỏ tổng hợp/được phép chia sẻ
  sau review. Không dùng `git add -f`; kiểm tra toàn bộ staged diff và danh sách
  file trước commit. Manifest không chứa dữ liệu nhúng hoặc đường dẫn máy cá nhân.
- Khi được phép chạy VLM, lưu raw output của từng mẫu/lần gọi **trước** parse
  hoặc tổng hợp; liên kết sample ID, prompt, model/version, cấu hình sinh và run ID.
  Giữ cả lỗi, lần chạy dở và provenance, không chỉ nhãn hoặc điểm tổng hợp.

## Code và bằng chứng kiểm tra

- Dùng đường dẫn tương đối từ repository root trong code, cấu hình và tài liệu.
- Giữ bốn nhãn canonical và quy tắc INVALID/support/recall theo nguồn lịch sử
  đã dẫn trong ARCHITECTURE. Application records/model transport mới không phải
  production schema/parser hoặc protocol freeze. Không tự bổ sung metric pending.
- Demo và tests chỉ dùng bản ghi tổng hợp, phải phân biệt rõ với kết quả thật;
  không đưa số demo vào báo cáo khoa học, không viết backend sinh dự đoán giả.
- Chỉ thêm code/module/thư mục có chức năng được giao; không tạo train.py,
  notebook GPU, inference pipeline hoặc nhập lại stub/hệ thống cũ cho đủ cấu trúc.
- Ghi nguồn/version/checksum đầu vào, môi trường/dependency versions, lệnh chạy,
  cấu hình, seed nếu có ngẫu nhiên, Git commit và vị trí artifact cho mỗi lần chạy.
- Code dùng lại cần test phù hợp, gồm lỗi/biên có ý nghĩa. Không lấy mẫu dataset
  thật làm fixture được commit; không thêm dependency khi chưa cần.
- Smoke test hiện tại: `python -B -m unittest discover -s tests -v`.
  Chạy kiểm tra phù hợp thay đổi; ghi rõ kết quả, giới hạn và kiểm tra chưa chạy
  trong PR/log. Chỉ đánh dấu hoàn thành khi có bằng chứng.
- Test lịch sử thuộc commit lưu trữ và môi trường tương ứng; không chạy chúng
  trên scaffold mới rồi kết luận hệ thống cũ lỗi.
