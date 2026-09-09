# Hướng dẫn làm việc với SafeShift

## Trước khi làm việc

- Luôn đọc `AGENTS.md`, `ROADMAP.md` và `TASKS.md` trước khi bắt đầu mỗi task.
- Xác định phạm vi task hiện tại; không sửa file không liên quan.
- Week 1 chỉ khảo sát và audit InspecSafe-V1. Chưa triển khai parser dataset hoặc chạy thí nghiệm VLM ở bước khởi tạo này.

## Tính toàn vẹn nghiên cứu

- Không tự ý thay đổi định nghĩa dataset, split, nhãn hoặc metric. Mọi đề xuất thay đổi phải được thảo luận, chấp thuận và ghi vào `DECISIONS.md` trước khi áp dụng.
- Không bịa số liệu, kết quả, schema hoặc đặc điểm dataset. Phân biệt thông tin đã kiểm chứng, giả thuyết và câu hỏi còn mở; ghi nguồn cho các nhận định.
- Giữ nguyên dữ liệu gốc. Mọi sản phẩm dẫn xuất nằm trong `data/processed/`, với quy trình tạo lại được ghi rõ.
- Sau này khi chạy VLM, phải lưu **raw model output** của từng mẫu/lần gọi trước khi parse hoặc tổng hợp; giữ liên kết với sample ID, prompt, model/version, cấu hình sinh và run ID. Không chỉ lưu nhãn hoặc điểm tổng hợp.

## Dữ liệu và Git

- Không commit InspecSafe-V1, dữ liệu thô, bản sao ảnh/video, archive dataset hoặc dữ liệu dẫn xuất dung lượng lớn, kể cả qua Git LFS.
- Không commit model checkpoints, raw model output dung lượng lớn, secrets hoặc credentials.
- Tuân thủ `.gitignore`; không dùng `git add -f` để đưa dữ liệu bị loại trừ vào Git. Kiểm tra staged diff và danh sách file trước khi commit.
- Chỉ version control code, tài liệu, test fixtures nhỏ được phép chia sẻ và manifest/figure nhỏ đã kiểm tra. Manifest không chứa dữ liệu nhúng hoặc đường dẫn tuyệt đối của máy cá nhân.

## Reproducibility và code

- Dùng relative path tính từ repository root trong code, cấu hình, manifest và tài liệu. Không hard-code đường dẫn riêng của một máy.
- Ghi nguồn/version/checksum dataset, môi trường và dependency versions, lệnh chạy, cấu hình, seed khi có ngẫu nhiên, Git commit và vị trí artifact cho mỗi lần chạy.
- Code dùng lại phải có test phù hợp, gồm các trường hợp lỗi hoặc biên có ý nghĩa; fixtures phải nhỏ, tổng hợp hoặc được phép chia sẻ, không lấy dataset thật để commit vào tests.
- Chạy các kiểm tra phù hợp với thay đổi và ghi rõ kiểm tra nào chưa chạy cùng lý do.
- Cập nhật trạng thái task theo việc thực sự hoàn thành; ghi quyết định và thí nghiệm vào đúng log, không đánh dấu hoàn tất khi chưa có bằng chứng.
