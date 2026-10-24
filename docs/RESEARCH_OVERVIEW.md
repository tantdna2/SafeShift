# Phạm vi và mục tiêu khoa học

SafeShift đánh giá VLM trên ảnh kiểm tra an toàn công nghiệp, hướng tới một
Seminar có bằng chứng truy vết được và nền tảng mở rộng thành Khóa luận. Câu hỏi
thực tiễn là mô hình mắc những lỗi nào khi cảnh, miền và thành phần nhãn thay
đổi. Điểm xếp hạng, nhãn sinh ra và khả năng ra quyết định an toàn là các endpoint
khác nhau; kết quả ở một endpoint không tự chứng minh endpoint còn lại.

## Hai hướng cần phân biệt

| Nội dung | D9R22 có hiệu lực | DEC-PA3-011 / HNLO |
| --- | --- | --- |
| Thẩm quyền | `APPROVED_PROSPECTIVE_SCOPE` cho phạm vi/readiness | **PROPOSED**, chưa thay D9R22 |
| RQ1 | Độ vững phân loại zero-shot xuyên năm miền | Giá trị phân biệt của điểm nội tại so với đối chứng phù hợp |
| RQ2 | Tập trung lỗi nghiêm trọng theo 12 hazard atoms; 7 nhóm là tóm tắt phụ | Điểm có phản ánh nguy cơ hay bị chi phối bởi người, thiết bị, miền/nguồn? |
| RQ3 | Nhất quán quyết định và tín hiệu bất đồng từ dự đoán RQ1/RQ2 | Bỏ sót, báo động giả và giới hạn chuyển miền |
| Đầu vào phân tích | Nhãn phân loại đã parse; RQ3 tái dùng các dự đoán đó | Raw label logits/thông tin tương đương được chứng minh, sau kiểm tra token alignment |
| Phần chưa chốt | Hợp đồng production, metric chi tiết, implementation/protocol freeze | Phê duyệt hướng, controls, proxy, coverage, ngưỡng và protocol so sánh |

Nguồn D9R22 là
[config được phê duyệt](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/configs/pre_freeze/d9r22_seminar_scope.v1.json).
HNLO và điều kiện phê duyệt nằm trong
[DEC-PA3-011](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/DECISIONS.md#dec-pa3-011--proposed-seminar-internal-hazard-score-direction-2026-10-16)
và [hồ sơ bốn mô hình](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_four_model_seminar_scope.md).
Bảng này tóm tắt nguồn lịch sử, không tạo protocol mới hoặc cấp quyền chạy.

Theo D9R22, grounding được hoãn khỏi phạm vi Seminar chính và có thể là mở rộng
Khóa luận; việc hoãn không phải thất bại khoa học. Các nhóm metric RQ3 mới được
định danh ở config không có nghĩa đã triển khai hoặc đã chứng minh tín hiệu
reliability. Bất đồng không mặc nhiên là confidence đã hiệu chuẩn.

## Dataset và mô hình

InspecSafe-V1 có năm miền `coal_conveyor`, `metallurgy`, `oil_chemical`, `power`,
`tunnel`. Bốn nhãn chuẩn giữ nguyên thứ tự Level01 đến Level04: mức nguy hiểm
giảm dần tới Normal. Code nền tảng chỉ nhận nhãn có sẵn, không suy nhãn từ ảnh
hay sửa taxonomy. Nguồn và giới hạn ở [DATA_AND_ETHICS](DATA_AND_ETHICS.md).

Danh sách bắt buộc giữ đủ Qwen2.5-VL-3B-Instruct, Qwen3-VL-8B-Instruct,
InternVL3-2B-hf, Moondream2. Không bỏ mô hình vì thiếu kết quả hoặc tự đổi endpoint
cho mô hình không hỗ trợ raw logits; mọi phương án N/A/fallback cần duyệt riêng.

HNLO là điểm log-odds nhãn Hazard–Normal theo hồ sơ PA3. Nó không phải xác suất
nguy cơ đã hiệu chuẩn, không đo trực tiếp xác suất tai nạn và chưa có ngưỡng
vận hành được xác nhận. Foundation V1 không triển khai phép tính score này.

## Trạng thái hiện tại

Nền tảng chạy được bằng CPU trên bản ghi tổng hợp; interface mô hình mới ở mức
kiểu dữ liệu. Không có thực nghiệm mới trong Foundation V1. Những bằng chứng
TRAIN đã có thuộc source/release cũ và được phân loại theo mức kiểm chứng trong
[RESULTS_AND_LIMITATIONS](RESULTS_AND_LIMITATIONS.md).

Các hướng A/C chưa được phê duyệt. D9R22, DEC-PA3-011, roster, nhãn, split,
metric và authority thực nghiệm giữ nguyên trạng thái. Xem [ROADMAP](ROADMAP.md)
cho điều kiện phát triển tiếp; reset và Foundation V1 đều không cấp quyền GPU,
inference, mở TEST hoặc tiếp cận dữ liệu bị khóa.
