# SafeShift roadmap

**Đề tài:** SafeShift: Benchmarking Cross-Domain Generalization and Evidence Grounding in Vision-Language Models for Industrial Safety Assessment.

**Dataset:** InspecSafe-V1.

Đây là kế hoạch nghiên cứu, không phải báo cáo kết quả. Phạm vi domain, evidence grounding và metric phải được xác minh từ dataset rồi chốt trong research protocol.

| Tuần | Giai đoạn | Công việc và đầu ra dự kiến |
| --- | --- | --- |
| W1 | Dataset Audit | Xác minh nguồn, quyền sử dụng, cấu trúc, schema, nhãn, split, chất lượng dữ liệu và metadata domain/evidence. Lập báo cáo audit cùng các hạn chế; chưa chạy VLM. |
| W2 | Research Protocol | Chốt câu hỏi nghiên cứu, giả thuyết, định nghĩa domain, cách chia tập, metric, protocol đánh giá grounding, baseline và kế hoạch tái lập. Ghi rõ các quyết định và giới hạn dữ liệu. |
| W3–W4 | Baseline Reproduction | Tái lập baseline theo protocol đã chốt; lưu cấu hình, raw model outputs, kết quả đánh giá và phân tích lỗi. Chỉ bắt đầu sau khi hoàn tất audit và protocol. |
| W5–W8 | SafeShift Contribution 1 + Paper 1 Draft | Chốt Contribution 1 dựa trên bằng chứng từ audit và baseline; triển khai, đánh giá, ablation phù hợp, phân tích và soạn Paper 1. Không mặc định contribution có cải thiện trước khi đo. |

## Điều kiện chuyển giai đoạn

- W1 → W2: có báo cáo audit có thể truy vết, danh sách điểm chưa rõ và đánh giá dataset có hỗ trợ nghiên cứu cross-domain/grounding hay không.
- W2 → W3: protocol và định nghĩa metric/dataset được chấp thuận; có kế hoạch lưu artifact và raw model outputs.
- W4 → W5: có baseline tái lập được hoặc mô tả rõ trở ngại, sai khác với thiết lập tham chiếu; Contribution 1 được chốt có căn cứ.

Task thực thi hiện tại chỉ được chi tiết hóa cho W1 trong `TASKS.md`.
