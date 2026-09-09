# W1 — Dataset Audit

Mục tiêu: khảo sát, kiểm tra và hiểu InspecSafe-V1 trước bất kỳ thí nghiệm VLM nào. Các checkbox chưa đánh dấu là việc cần làm, không phải kết quả đã có.

## 0. Khởi tạo repository

- [x] Tạo cấu trúc thư mục và tài liệu nền tảng.
- [x] Thiết lập quy tắc quản lý dữ liệu, reproducibility và `.gitignore`.

## 1. Xác minh nguồn và quyền sử dụng

- [ ] Xác định nguồn phát hành chính thức và tài liệu đi kèm InspecSafe-V1; ghi URL, ngày truy cập và version/release nếu có.
- [ ] Đọc license, điều kiện truy cập, quyền dùng/chia sẻ ảnh, annotation và ví dụ trong paper; ghi lại các ràng buộc hoặc thông tin chưa rõ.
- [ ] Ghi cách lấy dữ liệu local, tên archive và checksum nếu có; không đưa archive hoặc credentials lên Git.

## 2. Kiểm kê dữ liệu local

- [ ] Đặt dữ liệu trong `data/raw/InspecSafe-V1/` theo `data/README.md`; giữ nguyên cấu trúc gốc.
- [ ] Khảo sát cây thư mục, tài liệu, định dạng ảnh và annotation thực tế; ghi nhận encoding, quy tắc đặt tên và liên kết ảnh–annotation.
- [ ] Kiểm đếm file, kích thước, sample ID, ảnh và annotation theo split/nhãn/domain nếu các trường này tồn tại; ghi mẫu số rõ ràng cho từng thống kê.
- [ ] Ghi inventory/checksum manifest nhỏ nếu phù hợp, dùng relative path và không nhúng nội dung ảnh hoặc thông tin nhạy cảm.

## 3. Hiểu schema và ý nghĩa nhãn

- [ ] Đọc annotation mẫu và tài liệu; mô tả field, kiểu dữ liệu, giá trị thiếu và đơn vị.
- [ ] Xác minh định nghĩa nhãn an toàn/nguy cơ, multi-label nếu có, và đơn vị annotation thực tế: ảnh, đối tượng, vùng hoặc đơn vị khác.
- [ ] Xác minh sample ID, split và quy tắc ánh xạ ảnh–annotation; ghi ví dụ nhỏ chỉ khi được phép chia sẻ.
- [ ] Ghi mọi trường hợp mơ hồ cần hỏi người phụ trách; không tự diễn giải thành định nghĩa chính thức.

## 4. Kiểm tra chất lượng và nguy cơ leakage

- [ ] Kiểm tra file hỏng/không đọc được, ảnh thiếu annotation, annotation thiếu ảnh, ID trùng và giá trị không hợp lệ.
- [ ] Kiểm tra exact duplicates và near-duplicates trong/giữa split; ghi phương pháp, ngưỡng và hạn chế nếu sử dụng đối sánh gần đúng.
- [ ] Kiểm tra khả năng cùng cảnh, nguồn, video hoặc chuỗi ảnh xuất hiện ở nhiều split nếu metadata cho phép.
- [ ] Thống kê phân bố nhãn, độ phân giải, thiếu metadata và mất cân bằng; không sửa hoặc loại mẫu khỏi dữ liệu gốc.

## 5. Đánh giá khả năng nghiên cứu SafeShift

- [ ] Kiểm tra có domain metadata nào: nguồn, địa điểm, môi trường, camera hoặc loại ngành; tách field gốc khỏi domain suy luận/đề xuất.
- [ ] Đánh giá khả năng thiết kế cross-domain split và rủi ro confounding; chưa tự tạo hoặc thay split chính thức.
- [ ] Xác minh loại evidence annotation thực sự có: bounding box, mask, vùng, mô tả, hoặc không có; không mặc định dataset có nhãn grounding.
- [ ] Ghi giới hạn đánh giá evidence grounding và nhu cầu annotation bổ sung nếu có; metric để chốt ở W2.

## 6. Khảo sát trực quan và báo cáo

- [ ] Chọn mẫu khảo sát có phương pháp được ghi rõ (và seed nếu ngẫu nhiên), bao phủ nhãn/domain/split hiện có và các trường hợp lỗi.
- [ ] Xem ảnh cùng annotation để kiểm tra ý nghĩa nhãn, bối cảnh và tính nhất quán; chỉ lưu figure được phép chia sẻ.
- [ ] Viết `notes/w1_dataset_audit.md` với nguồn dữ liệu, phương pháp, thống kê đã kiểm chứng, phát hiện chất lượng, hạn chế và câu hỏi cho W2.
- [ ] Lưu figure nhỏ được phép chia sẻ trong `outputs/figures/`; giữ artifact lớn ở local.
- [ ] Ghi các lệnh, môi trường, checksum và đường dẫn artifact để người khác có thể tái lập audit; code dùng lại được bổ sung sau phải có test.
- [ ] Rà soát checklist và điều kiện chuyển giai đoạn trong `ROADMAP.md` trước khi đánh dấu W1 hoàn thành.

**Ngoài phạm vi bước khởi tạo:** code parse dataset, inference VLM, chọn metric chính thức và tuyên bố kết quả nghiên cứu.
