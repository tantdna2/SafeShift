# SafeShift roadmap

**Đề tài đề xuất:** SafeShift: Evaluating the Validity and Cross-Domain Reliability of Internal Hazard Scores in Vision-Language Models

**Dataset:** InspecSafe-V1.

Đây là thứ tự triển khai Seminar được Research Lead lựa chọn để xem xét theo
[DEC-PA3-011 PROPOSED](DECISIONS.md#dec-pa3-011--proposed-seminar-internal-hazard-score-direction-2026-10-16),
không phải protocol đã phê duyệt hoặc quyền thực thi. Hazard–Normal Label Log-Odds
Score (HNLO) là tên dùng trong phần trình bày nghiên cứu cho phép tính được hồ sơ
kỹ thuật lịch sử gọi là PA3. Bốn mô hình bắt buộc là Qwen2.5-VL-3B-Instruct,
Qwen3-VL-8B-Instruct, InternVL3-2B-hf và Moondream2.

| # | Trạng thái | Giai đoạn | Điều kiện và đầu ra |
| ---: | --- | --- | --- |
| 1 | **COMPLETE** | Baseline Qwen2.5 | Đã kiểm toán 3.763/3.763 ảnh TRAIN; HNLO AUROC = 0,8266558463706973; CPU audit PASS. Đây là bằng chứng mô tả trên TRAIN đã phơi nhiễm, không phải kết quả khái quát hóa. |
| 2 | **NEXT** | Capability audit (kiểm tra khả năng kỹ thuật) | Chỉ đọc tài liệu, mã nguồn và kiểm tra CPU cho Qwen3-VL-8B-Instruct, InternVL3-2B-hf và Moondream2: xác minh revision, logits, token mapping, khả năng tính HNLO tương đương, trở ngại GPU và phương án dự phòng cần trình duyệt. Chưa chạy inference mới và không truy cập dữ liệu bị khóa. |
| 3 | **PENDING** | Phê duyệt hướng và giao thức RQ1–RQ3 | Research Lead phê duyệt chính thức DEC-PA3-011 và chốt đối chứng công bằng, dữ liệu chung, coverage, nguồn nhãn, xử lý yếu tố gây nhiễu, quy tắc chọn ngưỡng cùng phương án dự phòng cho mô hình không hỗ trợ HNLO. Quyền thực thi được xem xét riêng. |
| 4 | **PENDING** | GPU validation kỹ thuật tối thiểu | Thực hiện thử nghiệm GPU kỹ thuật nhỏ nhất cho từng mô hình, chỉ sau khi có quyền cụ thể và hoàn tất kiểm toán các thay đổi liên quan. |
| 5 | **PENDING** | Thí nghiệm bốn mô hình | Thực hiện thí nghiệm trên cả bốn mô hình trong phạm vi dữ liệu đã được phê duyệt; lưu raw output, cấu hình, log, kết quả và bằng chứng kiểm toán độc lập. |
| 6 | **PENDING** | Phân tích RQ1–RQ3 | RQ1: giá trị phân biệt và đối chứng công bằng. RQ2: dấu hiệu gây nhiễu. RQ3: tỷ lệ bỏ sót, báo động giả và giới hạn chuyển miền. Báo cáo mẫu số, coverage, dữ liệu phụ thuộc và kết quả không xác định. |
| 7 | **PENDING** | Tổng hợp Seminar | Tổng hợp bảng kết quả, biểu đồ, phân tích lỗi, báo cáo và slide Seminar; từ bằng chứng đã kiểm toán, đề xuất hướng phát triển khóa luận. |

## Điều kiện chuyển giai đoạn

- Giai đoạn 2 → 3: hoàn tất hồ sơ capability của ba mô hình còn lại, nêu rõ
  blocker GPU và mọi phương án fallback; không coi CPU/source audit là GPU PASS.
- Giai đoạn 3 → 4: DEC-PA3-011 và giao thức so sánh được Research Lead phê duyệt;
  mỗi GPU validation vẫn cần authority riêng gắn với model, revision và phạm vi.
- Giai đoạn 4 → 5: từng mô hình có kết quả validation được kiểm toán hoặc phương
  án fallback/N/A được phê duyệt; phạm vi dữ liệu và quyền chạy đã được chốt.
- Giai đoạn 5 → 6: raw output và provenance của đủ bốn mô hình được lưu trước khi
  parse/tổng hợp; coverage, lỗi và trạng thái kiểm toán được đối soát.
- Giai đoạn 6 → 7: kết quả RQ1–RQ3 báo cáo đủ mẫu số, phụ thuộc, yếu tố gây nhiễu,
  giới hạn chuyển miền và trường hợp không xác định; không suy TRAIN thành
  generalization.

DEC-PA3-011 vẫn **PROPOSED**. Trước khi được phê duyệt, [D9R22 JSON](configs/pre_freeze/d9r22_seminar_scope.v1.json)
vẫn là phạm vi có hiệu lực. Roadmap này không cấp quyền inference, GPU, TEST,
annotation, lựa chọn ngưỡng hay protocol freeze; các giai đoạn **PENDING** chưa
được xem là hoàn tất.
