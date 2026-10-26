# Phạm vi và mục tiêu khoa học

SafeShift đánh giá VLM trên ảnh kiểm tra an toàn công nghiệp, hướng tới một
Seminar có bằng chứng truy vết được và nền tảng mở rộng thành Khóa luận. Câu hỏi
thực tiễn là mô hình mắc những lỗi nào khi cảnh, miền và thành phần nhãn thay
đổi. Điểm xếp hạng, nhãn sinh ra và khả năng ra quyết định an toàn là các endpoint
khác nhau; kết quả ở một endpoint không tự chứng minh endpoint còn lại.

## Quyết định Owner và hiệu lực

Ngày 26/10/2026, Owner xác nhận tự quyết hướng trong vai trò **SafeShift Owner /
Research Lead**: [nguồn GitHub](https://github.com/tantdna2/SafeShift/pull/134#issuecomment-6406751802).
[DEC-20261026-M1](research/DECISIONS.md) ghi lựa chọn PR #133/A1–A8: Seminar hồi
cứu nhãn–HNLO–lỗi/bất đồng; Khóa luận thực nghiệm logistic HNLO+bất đồng xếp ưu
tiên kiểm tra với Q3 cố định. Không tự nhận kiến trúc mới, phê duyệt giảng viên,
thay đổi chuẩn học phần hay quyền dữ liệu/tài nguyên.

Hồ sơ successor chỉ có hiệu lực sau kiểm chứng/merge; **khi còn Draft, D9R22
vẫn có hiệu lực**. Sau merge, kế thừa lõi D9R22 và chỉ thay/bổ sung các phần
liệt kê ở quyết định mới; DEC-PA3-011 lịch sử không bị sửa thành APPROVED.
[Protocol M2](research/SEMINAR_PROTOCOL.md) và [config v1](research/seminar_analysis_config.v1.json)
đã hoàn thành về tài liệu, **chưa frozen, còn review độc lập và Owner duyệt đúng
version/N/A**. Tên đề tài được chọn là “SafeShift: Đánh giá và cải thiện độ tin
cậy của quyết định nguy cơ an toàn công nghiệp bằng mô hình ngôn ngữ–thị giác”.

## Hợp đồng lịch sử và phần được bổ sung

| Nội dung | D9R22 (kế thừa) | Successor Owner trong quyền dự án |
| --- | --- | --- |
| Thẩm quyền | `APPROVED_PROSPECTIVE_SCOPE`; còn hiệu lực trước successor merge | M1 Owner đã quyết định; hiệu lực repository chờ kiểm chứng/merge; không duyệt toàn bộ DEC-PA3-011/A/C độc lập |
| S-RQ1 | Phân loại xuyên năm miền/D3 | Nhãn sinh ra và HNLO biểu hiện khác nhau thế nào về phân loại/xếp hạng nguy cơ trên cùng ảnh? |
| S-RQ2 | Lỗi nghiêm trọng theo 12 atoms; 7 nhóm phụ, chồng lấp không cộng | Lỗi tập trung ở đâu, nhạy thế nào với missing/ảnh trùng/giả định nhóm? Hazard mapping hiện BLOCKED đúng panel. |
| S-RQ3 | Nhất quán/bất đồng, tái dùng dự đoán RQ1/RQ2 | Bất đồng và HNLO liên hệ với lỗi/false-safe hay chỉ phản ánh thiên lệch chung? Không dùng hazard AUROC thay error detection. |
| Đầu vào phân tích | Nhãn đã parse và metadata có quyền | Saved HNLO/report đúng hash/run; Q25/IVL3 3.763 và ba model cùng 3.539 Q3 V4 SUCCESS gốc; Recovery224 riêng |
| Phần chưa chốt | Production/freeze/execution không suy từ readiness | M2 review/version approval/N/A cụ thể; quyền setup/CPU artifact/raw/GPU/ảnh/nhãn/TEST riêng |

Nguồn D9R22 là
[config được phê duyệt](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/configs/pre_freeze/d9r22_seminar_scope.v1.json).
HNLO và điều kiện phê duyệt nằm trong
[DEC-PA3-011](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/DECISIONS.md#dec-pa3-011--proposed-seminar-internal-hazard-score-direction-2026-10-16)
và [hồ sơ bốn mô hình](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_four_model_seminar_scope.md).
Bảng đối chiếu này không cấp quyền chạy; công thức/denominator/cohort/ties nằm
trong protocol M2 đang chờ review, không để người triển khai tự chọn.

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
cho mô hình thiếu bằng chứng raw logits. Owner đã chấp nhận **Moondream2 HNLO
TRAIN N/A trong báo cáo định lượng Seminar cấp dự án** (A4); giữ hàng trong mọi
bảng áp dụng. Đây không là ngoại lệ học phần đã được giảng viên xác minh và
không tự duyệt feature set Khóa luận.

HNLO là điểm log-odds nhãn Hazard–Normal theo hồ sơ PA3. Nó không phải xác suất
nguy cơ đã hiệu chuẩn, không đo trực tiếp xác suất tai nạn và chưa có ngưỡng
vận hành được xác nhận. Foundation V1 không triển khai phép tính score này.

## Trạng thái hiện tại

Nền tảng chạy được bằng CPU trên bản ghi tổng hợp; interface mô hình mới ở mức
kiểu dữ liệu. Không có thực nghiệm mới trong Foundation V1. Những bằng chứng
TRAIN đã có thuộc source/release cũ và được phân loại theo mức kiểm chứng trong
[RESULTS_AND_LIMITATIONS](RESULTS_AND_LIMITATIONS.md).

M1 ghi nhận lựa chọn Owner; M2 tài liệu DONE nhưng khoa học PENDING. Hazard map,
continuous controls, mismatch/proxy mapping và một số native provenance details
còn thiếu; N/A/claim cụ thể cần chấp nhận theo protocol B01–B05. Không giả có
đủ mapping để kết luận đầy đủ S-RQ2, không gọi HNLO vượt mọi continuous control.

Khóa luận cần nguồn/nhãn chuyên gia/target giữ kín độc lập, đủ nguồn/sự kiện theo
precision plan trước target; TRAIN phơi nhiễm không thay đánh giá xác nhận.
Chuẩn học vụ, quyền dữ liệu/tài nguyên và protocol approval là các trục riêng.
Xem [PROJECT_STATE](PROJECT_STATE.md) và [ROADMAP](ROADMAP.md). Sau M1/M2 PASS,
NEXT TASK là **M3-01: hệ thống phân tích Seminar CPU trọn vẹn**; hiện chưa triển
khai hoặc được cấp setup/GPU/inference/TEST từ task tài liệu này.
