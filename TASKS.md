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

- [x] Đặt dữ liệu trong `data/raw/InspecSafe-V1/` theo `data/README.md`; giữ nguyên cấu trúc gốc.
- [x] Khảo sát cây thư mục, tài liệu, định dạng ảnh và annotation thực tế; ghi nhận encoding, quy tắc đặt tên và liên kết ảnh–annotation.
- [x] Kiểm đếm file, kích thước, sample ID, ảnh và annotation theo split/nhãn/domain nếu các trường này tồn tại; ghi mẫu số rõ ràng cho từng thống kê.
- [x] Xây dựng Dataset Manifest Builder với validation và tests synthetic; tạo CSV/checksum local dùng relative path, không nhúng ảnh. Đã hoàn thiện 24 opening theo audit bổ sung; kiểm chứng 5.013 rows và 29 tests pass, unknown_text_domain = 0, domain_mismatch = 36, ma trận domain khớp audit và full run exit 0, không có discrepancy. Lệnh, kết quả và giới hạn: `notes/manifest_builder.md`. CSV chứa toàn văn TXT nên giữ local, không commit.

## 3. Hiểu schema và ý nghĩa nhãn

- [x] Đọc annotation mẫu và tài liệu; mô tả field, kiểu dữ liệu, giá trị thiếu và đơn vị.
- [x] Xác minh định nghĩa nhãn an toàn/nguy cơ, multi-label nếu có, và đơn vị annotation thực tế: ảnh, đối tượng, vùng hoặc đơn vị khác.
- [x] Xác minh sample ID, split và quy tắc ánh xạ ảnh–annotation; ghi ví dụ nhỏ chỉ khi được phép chia sẻ.
- [x] Ghi mọi trường hợp mơ hồ cần hỏi người phụ trách; không tự diễn giải thành định nghĩa chính thức.

## 4. Kiểm tra chất lượng và nguy cơ leakage

- [x] Kiểm tra file hỏng/không đọc được, ảnh thiếu annotation, annotation thiếu ảnh, ID trùng và giá trị không hợp lệ. Validation W1 Bước 3: 66/66 tests synthetic pass; full 5.013 samples, verify/decode ảnh và kiểm tra imageData, exit 0, không ERROR. Có 309 polygon vượt bounds, 5.013 imagePath mismatch và 94 imageData byte mismatch được giữ WARNING; không sửa/loại mẫu. Kết quả, provenance và discrepancies tài liệu: `notes/dataset_validation.md`; JSON chi tiết giữ local.
- [x] Kiểm tra exact duplicates và near-duplicates trong/giữa split; ghi phương pháp, ngưỡng và hạn chế nếu sử dụng đối sánh gần đúng. W1 Bước 4: full 5.013 samples, exit 0, fingerprint khớp validation; 107/107 tests pass. Có 53 byte/pixel-exact pairs, gồm 7 cross-split; dHash <=8 có 833 cross-split pairs (7 exact + 826 nonexact candidates). Methods, MAE/consecutive calibration, limitations và W2 review: `notes/duplicate_leakage_audit.md`; full pair report giữ local, không sửa/loại mẫu.
- [x] Kiểm tra khả năng cùng cảnh, nguồn, video hoặc chuỗi ảnh xuất hiện ở nhiều split nếu metadata cho phép. Đã audit toàn bộ 5.013 imagePath strings/basenames và strict embedded imageData; point-ID overlap = 0, imagePath/basename duplicate groups = 0, có 12 cross-split source-family candidate groups theo regex hẹp. Targeted visual & provenance review (Bước 5) xác nhận STRONG EVIDENCE rò rỉ chuỗi video và góc máy robot xuyên split; tài liệu chi tiết: `notes/duplicate_leakage_audit.md` và `notes/visual_provenance_review.md`.
- [ ] Thống kê phân bố nhãn, độ phân giải, thiếu metadata và mất cân bằng; không sửa hoặc loại mẫu khỏi dữ liệu gốc.

## 5. Đánh giá khả năng nghiên cứu SafeShift

- [ ] Kiểm tra có domain metadata nào: nguồn, địa điểm, môi trường, camera hoặc loại ngành; tách field gốc khỏi domain suy luận/đề xuất.
- [ ] Đánh giá khả năng thiết kế cross-domain split và rủi ro confounding; chưa tự tạo hoặc thay split chính thức.
- [ ] Xác minh loại evidence annotation thực sự có: bounding box, mask, vùng, mô tả, hoặc không có; không mặc định dataset có nhãn grounding.
- [ ] Ghi giới hạn đánh giá evidence grounding và nhu cầu annotation bổ sung nếu có; metric để chốt ở W2.

## 6. Khảo sát trực quan và báo cáo

- [x] Chọn mẫu khảo sát có phương pháp được ghi rõ (và seed nếu ngẫu nhiên), bao phủ nhãn/domain/split hiện có và các trường hợp lỗi. W1 Bước 5: chọn mẫu khảo sát có phương pháp gồm toàn bộ 7 cross-split exact pairs, 12 cross-split source families (bao trùm 1.000 mẫu Anomaly), và 50 candidate pairs phân tầng (Top 20 dHash/MAE, 15 Same-Family, 10 Different-Family, 5 Domain-Coverage). Tài liệu: `notes/visual_provenance_review.md`.
- [x] Xem ảnh cùng annotation để kiểm tra ý nghĩa nhãn, bối cảnh và tính nhất quán; chỉ lưu figure được phép chia sẻ. W1 Bước 5: hoàn thành quy trình blind-first visual review cho 7 exact pairs (phát hiện xung đột nhãn trực tiếp Cấp 1 vs Cấp 2, metallurgy vs oil_chemical, găng tay vs hút thuốc), 12 source families (cắt chuỗi video liên tục ~25% test / ~75% train), và 50 near candidates (Normal waypoint cố định vs Anomaly video slicing). Bằng chứng đầy đủ: `notes/visual_provenance_review.md`.
- [ ] Viết `notes/w1_dataset_audit.md` với nguồn dữ liệu, phương pháp, thống kê đã kiểm chứng, phát hiện chất lượng, hạn chế và câu hỏi cho W2.
- [ ] Lưu figure nhỏ được phép chia sẻ trong `outputs/figures/`; giữ artifact lớn ở local.
- [ ] Ghi các lệnh, môi trường, checksum và đường dẫn artifact để người khác có thể tái lập audit; code dùng lại được bổ sung sau phải có test.
- [ ] Rà soát checklist và điều kiện chuyển giai đoạn trong `ROADMAP.md` trước khi đánh dấu W1 hoàn thành.

**Ngoài phạm vi bước khởi tạo:** code parse dataset, inference VLM, chọn metric chính thức và tuyên bố kết quả nghiên cứu.
