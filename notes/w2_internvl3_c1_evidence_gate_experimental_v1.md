# InternVL3 C1 Evidence Gate — EXPERIMENTAL v1

Ngày: 2026-10-10. Trạng thái: prompt thử nghiệm riêng, chưa được cấp quyền
thay thế C1 trong benchmark P2/P2.1. BASE:
`d93a1fc0b529a832da887a69687cf7d209a8aacd`.

**Quan sát được báo cáo:** Theo yêu cầu của Research Lead trong task này,
InternVL3-2B-hf có xu hướng dự đoán nhiều `Level03`, kể cả cảnh công nghiệp
bình thường. Trong chẩn đoán trên ảnh tổng hợp ngoài InspecSafe, C1 gốc thường
trả `Level03`; yêu cầu xác minh nguy cơ nhìn thấy trước khi phân loại đã cho
`Level04` trên các ảnh bình thường trong bài thử, còn ảnh cháy trả `Level01`.
Đây là báo cáo của Research Lead; task không nhận hoặc kiểm tra raw outputs,
số lượng mẫu, provenance ảnh hay cấu hình của các lần chẩn đoán đó. Không suy
ra tỷ lệ cải thiện hay kết quả trên toàn bộ InspecSafe. Động cơ thay đổi có
liên quan đến hành vi benchmark đã được quan sát; không tuyên bố đề xuất này
hoàn toàn độc lập với benchmark.

**Giả thuyết:** Yêu cầu ít nhất một nguy cơ cụ thể thực sự nhìn thấy trước khi
chọn `Level01`–`Level03` có thể giảm việc coi thiết bị hoặc hoạt động bình thường
là nguy cơ. Chưa biết tác động lên ảnh thực tế, nguy cơ nhỏ/khó thấy, thiếu PPE,
khả năng bỏ sót nguy cơ hay hành vi của mô hình khác.

**Thay đổi:** [Prompt thử nghiệm](../prompts/p2_classification_c1_evidence_gate_experimental_v1.txt)
chỉ thêm bước xác minh trước phân loại: không suy đoán nguy cơ không nhìn thấy;
không có nguy cơ quan sát được thì chọn `Level04`; có nguy cơ thì áp dụng bảng
5 ngành của C1. Bước này không xuất giải thích. Giữ nguyên 4 định nghĩa, bảng
ngành, ánh xạ nhãn và đầu ra duy nhất `{"safety_level":"Level01"}` (giá trị
được chọn trong `Level01`–`Level04`). Không thêm ví dụ ảnh. Cơ sở thiết kế C1:
[decision brief, §12.2](w2_model_prompt_interface_decision_brief.md).
C1 chính thức vẫn có SHA-256
`816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3`
và được [classification policy](../safeshift/protocol/classification_policy.py)
chọn. Không nối prompt thử nghiệm vào runner hoặc sửa authority v4, execution
plan, run ID, parser, weights, preprocessing, decoding hay kết quả lịch sử.

**Kiểm tra tiếp theo (đề xuất, chưa chạy):** Sau khi Research Lead duyệt kế hoạch
chẩn đoán riêng, chọn trước một bộ ảnh thực tế có quyền sử dụng, nguồn/checksum
rõ ràng, ngoài InspecSafe và không trùng dữ liệu benchmark. Bao gồm cảnh bình
thường cùng nguy cơ ở các ngành/mức độ, kể cả nguy cơ khó thấy; khóa nhãn do
người đánh giá xác định theo bảng C1 trước khi xem dự đoán. So sánh cặp C1 gốc
và bản thử nghiệm trên cùng ảnh, weights, preprocessing, decoding, parser và
môi trường. Lưu raw output trước parse, liên kết sample ID, prompt/version/hash,
model/revision, cấu hình, seed, Git SHA và run ID riêng; artifacts local dưới
`data/processed/`, không trộn với các run P2/P2.1 lịch sử. Kiểm tra báo động giả,
bỏ sót theo mức độ/ngành, tính hợp lệ JSON và độ ổn định; không tối ưu bằng
bất kỳ ảnh InspecSafe nào.

**Điều kiện xem xét:** Research Lead cần xem bằng chứng ảnh thực tế ngoài
InspecSafe có thể tái lập, trade-off báo động giả/bỏ sót và tiêu chí chấp nhận
được chốt trước khi chạy. Nếu đề xuất áp dụng, cần ghi quyết định vào
`DECISIONS.md`, một giao thức mới có version/hash, đánh giá tính công bằng của
prompt chung cho các mô hình, kế hoạch đánh giá mới và quyền chạy riêng.
Không dùng authority P2.1 hiện tại để chạy prompt này hoặc viết lại kết quả cũ.

Task này chỉ kiểm tra tĩnh và hồi quy synthetic/local Git. Không tải model,
chạy GPU hoặc đọc/chạy InspecSafe; chưa có bằng chứng hiệu quả thực tế.
