# PA3 Seminar Direction Verdict

`DIRECTION_RECOMMENDATION = KEEP_CURRENT_DIRECTION`

- Lý do: `NOT_EXECUTED`
- Run ID: `pa3-qwen-seminar-direction-90`; phạm vi: exploratory decision diagnostic, KHÔNG phải pilot, holdout hay confirmatory benchmark.
- Tiêu chí được chốt trong code trước inference; không sửa sau khi xem kết quả.

## Bằng chứng thực thi

```json
{
  "audit_integrity": null,
  "gpu_runs": 0,
  "stage": "NOT_EXECUTED_PENDING_DIAGNOSTIC_AUTHORITY"
}
```

## Cohort đã khóa

- 90 ảnh TRAIN; GT levels: Level01=25, Level02=16, Level03=4, Level04=45
- Theo miền/lớp: coal_conveyor/Normal=10, coal_conveyor/Anomaly=10, oil_chemical/Normal=10, oil_chemical/Anomaly=10, power/Normal=10, power/Anomaly=10, tunnel/Normal=10, tunnel/Anomaly=10, metallurgy/Normal=5, metallurgy/Anomaly=5
- Xung đột folder/text domain: 4 (metallurgy-Level01-SuspendedRail-002658-001, metallurgy-Level01-SuspendedRail-002659-001, metallurgy-Level01-SuspendedRail-002661-001, metallurgy-Level01-SuspendedRail-002662-001)
- Trùng 10 ID LS1 (tài liệu): 0; thành phần bảo thủ lớn nhất: 48 ảnh

## Kết quả

Không có chỉ số: lượt GPU chưa được thực thi hoặc không có ảnh nào được thử. Không ngụy tạo số liệu.


## Đối chiếu tiêu chí đã chốt

| Tiêu chí | Nội dung | Kết quả |
|---|---|---|
| C1_COVERAGE | Four primary domains: >=95% of Normal AND >=95% of Anomaly have a valid PA3 score | NOT_EVALUATED |
| C2_MACRO_AUROC | Macro-domain PA3 AUROC over the four primary domains >= 0.75 (all four defined) | NOT_EVALUATED |
| C3_MACRO_DELTA | Macro PA3 AUROC - macro Qwen generated-binary-label AUROC >= 0.15, same eligible IDs | NOT_EVALUATED |
| C4_DOMAIN_WINS | PA3 AUROC > generated-binary-label AUROC in at least 3 of 4 primary domains | NOT_EVALUATED |
| C5_TECHNICAL_INTEGRITY | Sealed completed run, CPU audit/recomputation PASS, dataset checksums 90/90, exposure sealed, zero TECHNICAL_ERROR/INTERRUPTED/UNPROCESSED/NOT_ATTEMPTED | NOT_EVALUATED |

## Lý do khoa học cho Research Lead

Lượt GPU chưa chạy (hoặc dừng trước ảnh đầu tiên). Không có bằng chứng hiệu năng; giữ hướng hiện tại.

## Giới hạn dữ liệu/nhóm/GT

- 90 ảnh TRAIN đã bị Qwen2.5 P2 xử lý toàn pool (exposure aggregate); thiết kế được thúc đẩy sau khi xem P2.
- Quan hệ near-duplicate/source-family chưa phân xử; một thành phần bảo thủ chứa phần lớn ảnh; không có tính độc lập.
- GT là nhãn thư mục gốc của benchmark; Level03 rất hiếm; Metallurgy ít Anomaly và có xung đột miền.
- 10 Normal + 10 Anomaly mỗi miền: AUROC theo miền dao động lớn; không có CI đáng bảo vệ.

## Những khẳng định chưa được phép đưa vào báo cáo Seminar

- PA3 đã được xác nhận khoa học, hoặc kết quả là confirmatory benchmark / kết quả Seminar chính thức.
- Hiệu năng khái quát hóa sang TEST, miền khác, robot khác hoặc dữ liệu ngoài 90 ảnh InspecSafe TRAIN này.
- Cohort 90 ảnh là độc lập thống kê, chưa từng quan sát, clean holdout hoặc không liên hệ với TEST.
- Bất kỳ khoảng tin cậy, p-value hoặc kiểm định ý nghĩa nào từ lượt chẩn đoán này.
- PA3 cải thiện accuracy, an toàn vận hành hoặc giảm bỏ sót nguy hiểm; không có threshold nào được chọn.
- Kết quả Metallurgy hoặc Level03 là bằng chứng riêng; cả hai chỉ mang tính mô tả.
- Calibration, ngưỡng, prompt hoặc quy tắc dự đoán mới được học hay chọn từ 90 ảnh này.
