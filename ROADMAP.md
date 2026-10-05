# SafeShift roadmap

**Đề tài:** SafeShift: Benchmarking Cross-Domain Robustness and Disagreement-Aware Reliability in Vision-Language Models for Industrial Safety Assessment

**Dataset:** InspecSafe-V1.

Đây là kế hoạch nghiên cứu, không phải báo cáo kết quả. Theo prospective D9R22,
Seminar hiện tại classification-only: RQ1 giữ zero-shot robustness trên 5 miền
và đồng biến thiên với robot platform (không nhân quả); RQ2 giữ Level01–Level04,
12 Hazard Atoms primary và 7 nhóm A–G secondary exploratory. RQ3 mới là
Cross-Model Decision Consistency and Disagreement-Aware Reliability under Domain Shift,
tái sử dụng classification predictions RQ1/RQ2, không thêm inference.
Grounding được bảo lưu cho khóa luận tương lai:
`PRIMARY_SEMINAR_GROUNDING=DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE`.
Lịch sử grounding giữ nguyên; không còn là điều kiện freeze Seminar.

| Tuần | Giai đoạn | Công việc và đầu ra dự kiến |
| --- | --- | --- |
| W1 | Dataset Audit | Xác minh nguồn, quyền sử dụng, cấu trúc, schema, nhãn, split, chất lượng dữ liệu và metadata domain/evidence. Lập báo cáo audit cùng các hạn chế; chưa chạy VLM. |
| W2 | Research Protocol | Hoàn thiện classification production contract, adapters/parsers, decoding/preprocessing/precision, metric RQ1/RQ2/RQ3 mới, benchmark harness và end-to-end rehearsal trước implementation/protocol freeze. Giữ dataset/split/label và taxonomy đã duyệt. |
| W3–W4 | Baseline Reproduction | Tái lập baseline theo protocol đã chốt; lưu cấu hình, raw model outputs, kết quả đánh giá và phân tích lỗi. Chỉ bắt đầu sau khi hoàn tất audit và protocol. |
| W5–W8 | SafeShift Contribution 1 + Paper 1 Draft | Chốt Contribution 1 dựa trên bằng chứng từ audit và baseline; triển khai, đánh giá, ablation phù hợp, phân tích và soạn Paper 1. Không mặc định contribution có cải thiện trước khi đo. |

## Điều kiện chuyển giai đoạn

- W1 → W2: có báo cáo audit có thể truy vết, danh sách điểm chưa rõ và đánh giá dataset có hỗ trợ nghiên cứu cross-domain/grounding hay không.
- W2 → W3: protocol và định nghĩa metric/dataset được chấp thuận; có kế hoạch lưu artifact và raw model outputs.
- W4 → W5: có baseline tái lập được hoặc mô tả rõ trở ngại, sai khác với thiết lập tham chiếu; Contribution 1 được chốt có căn cứ.

Current scope và readiness: [D9R22 JSON](configs/pre_freeze/d9r22_seminar_scope.v1.json)
và mục D9R22 cuối `TASKS.md`; các checklist trước đó là lịch sử.
Provenance, runtime runners, classification participation và external gate history
COMPLETE không có nghĩa production-ready. Protocol freeze=PENDING;
inspecsafe_inference_authorized=false. Bốn classification participants D9R18
giữ nguyên; PaliGemma không tham gia, SmolVLM2 không kích hoạt. Không mở rộng
Seminar sang grounding hoặc bắt đầu task B trong task A.
