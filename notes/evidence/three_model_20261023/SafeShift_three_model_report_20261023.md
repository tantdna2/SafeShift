# SAFESHIFT — Phân tích so sánh ba mô hình trên 3.763 ảnh TRAIN

Báo cáo tổng hợp ngày 23-10-2026. Các chỉ số được sử dụng là dữ liệu mô tả trên TRAIN, không phải TEST độc lập. Qwen3 được tổng hợp từ 3.539 dự đoán V4 thành công và 224 dự đoán của lượt phục hồi mới; không coi đó là một lần chạy duy nhất.

## Phương pháp và nguồn

- Qwen2.5-VL-3B-Instruct: lấy kết quả từ `notes/pa3_r2_cpu_completion_20261015.md` trên GitHub, trước đó đã kiểm toán độc lập bằng CPU Linux. Bốn bản raw R2 gốc không có sẵn trong nhóm tệp hiện tại nên không tính lại trực tiếp từ bytes.
- Qwen3-VL-8B-Instruct: trích `evidence/report/samples.csv` từ `Qwen3_Output.zip` và `hnlo-qwen3-s2-recovery224-v1-20261022.tar.gz`; kiểm tra 3.763 sample_id riêng biệt và trùng tập ảnh/nhãn với InternVL3.
- InternVL3-2B-hf: trích `evidence/report/samples.csv` từ `InterVL3_Output.zip`; 3.763 sample_id riêng biệt.
- AUROC được tính trực tiếp trên toàn bộ bản ghi với nhãn bất thường = Level01/02/03 và bình thường = Level04 (không lấy trung bình AUROC từng shard). Phân loại 4 mức là so sánh nhãn sinh ra với nhãn thực, không dùng ngưỡng điểm PA3.

## So sánh toàn bộ

| Chỉ số | Qwen2.5 | Qwen3 | InternVL3 |
|---|---:|---:|---:|
| Độ phủ dự đoán | 3.763/3.763 | 3.763/3.763 | 3.763/3.763 |
| PA3 AUROC | 0.8267 | 0.9529 | 0.8862 |
| Phân loại 4 mức | 130/3763 (3.45%) | 2932/3763 (77.92%) | 164/3763 (4.36%) |
| Phân loại bất thường/bình thường | 749/3763 (19.90%) | 3282/3763 (87.22%) | 749/3763 (19.90%) |
| AUROC từ nhãn nhị phân sinh ra | 0.5000 | 0.9011 | 0.5000 |
| Nhận đúng Level01 | chưa xác định số riêng trong tệp đã truy cập | 163/490 (33.27%) | 60/490 (12.24%) |

## AUROC theo miền

| Miền | Số ảnh | Qwen2.5 | Qwen3 | InternVL3 |
|---|---:|---:|---:|---:|
| coal_conveyor | 822 | 0.8953 | 0.9319 | 0.9893 |
| metallurgy | 543 | 0.8404 | 0.8752 | 0.9415 |
| oil_chemical | 778 | 0.7549 | 0.9747 | 0.9568 |
| power | 656 | 0.8721 | 0.9854 | 0.7064 |
| tunnel | 964 | 0.8635 | 0.9836 | 0.7273 |

## Diễn giải

- Qwen3 dẫn đầu PA3 AUROC toàn bộ, cao hơn Qwen2.5 0,12628 và InternVL3 0,06675 điểm AUROC. Đây là chênh lệch quan sát được; chưa phải bằng chứng tăng hiệu quả trên TEST hay kiểm định ý nghĩa thống kê.
- Qwen3 có nhãn sinh ra hữu ích hơn hẳn: đúng 2.932/3.763 ở bốn mức và 3.282/3.763 ở nhị phân. Tuy nhiên, chỉ nhận đúng 163/490 ảnh Level01; có 14 ảnh Level01 bị gán Level04 (bình thường). Cần trình bày riêng lỗi nguy hiểm này.
- Qwen2.5 và InternVL3 đều sinh nhãn bất thường cho tất cả ảnh, gồm cả 3.014 ảnh bình thường. Bởi vậy nhãn nhị phân có AUROC = 0,5 và accuracy nhị phân = 19,9%, dù điểm PA3 liên tục vẫn sắp thứ tự bất thường/bình thường tốt hơn ngẫu nhiên.
- InternVL3 dẫn đầu về PA3 AUROC tại coal_conveyor và metallurgy; Qwen3 dẫn đầu ở oil_chemical, power và tunnel. Chỉ có 9 ảnh bất thường trong metallurgy, kết quả miền này nhạy với ít trường hợp.
- 3.014/3.763 ảnh là Level04, nên phân loại luôn Level04 cũng đạt 80,10% accuracy 4 mức; Qwen3 đạt 77,92% dù có giá trị thực ở bài toán phát hiện bất thường (87,22% nhị phân). Không đánh giá an toàn chỉ qua accuracy tổng.
- Thời gian suy luận đo được: Qwen3 15,31 giây/ảnh qua các đợt và InternVL3 2,19 giây/ảnh; Qwen3 dùng T4 ×2, InternVL3 dùng T4 ×1. Không có thời gian Qwen2.5 cùng nguồn để so tốc độ đầy đủ.
- Qwen2.5 chạy R2 có tiền xử lý clamp (giới hạn số ảnh/khung hình), Qwen3 và InternVL3 không sử dụng clamp đó; các phiên bản mô hình và môi trường khác nhau. Vì vậy các chênh lệch có thể gồm ảnh hưởng cấu hình.
- Cả ba đang được phân tích bằng ảnh TRAIN đã quan sát; chưa có TEST độc lập, khoảng tin cậy theo nhóm, hoặc đánh giá định vị bằng chứng để kết luận khả năng khái quát hay RQ grounding.

## Dữ liệu sử dụng

- Dữ liệu Qwen2.5 đã công bố trong repository: https://github.com/tantdna2/SafeShift/blob/main/notes/pa3_r2_cpu_completion_20261015.md
- Dữ liệu Qwen3 từ bốn archive trong `Qwen3_Output.zip` cùng tệp Recovery224 của Owner.
- Dữ liệu InternVL3 từ bốn archive trong `InterVL3_Output.zip` của Owner.
- Tệp máy tính tổng hợp: `SafeShift_three_model_comparison_20261023.json`; bảng CSV: `SafeShift_three_model_metrics_20261023.csv`.
