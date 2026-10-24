# Kết quả lịch sử và mức bằng chứng

Các số dưới đây thuộc snapshot trước reset
[`31a04e6f7175cca818c63b4de0153246b3f3ecdb`](https://github.com/tantdna2/SafeShift/tree/31a04e6f7175cca818c63b4de0153246b3f3ecdb).
Foundation V1 chỉ đối chiếu tài liệu/code, không đọc lại artifact thật, không
chạy raw audit, saved-score recomputation hoặc thực nghiệm mô hình mới.

**Bổ sung PR #131, 24/10/2026:** [hồ sơ khả thi](SOURCE_FEASIBILITY_GATE_20261024.md)
và [receipt mới](SOURCE_FEASIBILITY_RECEIPT_20261024.json) đã hash-verify và tái
tính saved-score trên artifact được phép. Q2.5/IVL3 khớp đủ 3.763 ID–nhãn–miền;
exact weighting cho AUROC 0,825397/0,885748 so với theo ảnh 0,826656/0,886182.
Đã nối riêng Q3 S0/S1/S3 qua receipt/archive/manifest/CSV để so ba model trên
2.822 ID, cùng Recovery224 riêng; không tính toàn V4 gốc hoặc pooling. Mọi
weighting/grouping mới là **PROPOSED_EXPLORATORY**, không sửa bảng lịch sử sau
đây hoặc nâng thành raw PASS. Catalog 7 exact pairs trong visual note có
membership không khớp artifact đúng hash, được ghi riêng trong hồ sơ mới.

Nguồn chính là [báo cáo khoa học ba mô hình 23/10/2026](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/reports/three_model_scientific_analysis_20261023.md)
và [receipt mô tả phạm vi kiểm chứng](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/evidence/three_model_20261023/verification_20261023.json).
RQ1–RQ3 trong báo cáo đó theo hướng **DEC-PA3-011 PROPOSED**, không thay các RQ
D9R22 đang có hiệu lực; xem [RESEARCH_OVERVIEW](RESEARCH_OVERVIEW.md).

## Kết quả TRAIN được báo cáo

Cohort mô tả có 3.763 ảnh TRAIN: 749 Anomaly / 3.014 Normal;
support Level01/02/03/04 = 490/251/8/3.014. Anomaly là Level01–03.

| Mô hình / cohort | HNLO AUROC | Accuracy nhãn bốn mức | Mức bằng chứng lịch sử |
| --- | ---: | ---: | --- |
| Qwen2.5, PA3-R2 | 0,8266558463706973 | 130/3.763 = 3,45% | Raw audit CPU Linux PASS theo hồ sơ chính thức; đối chiếu 23/10 chỉ tái tính saved score. |
| InternVL3 | 0,8861824613751756 | 164/3.763 = 4,36% | Tái tính từ CSV saved score trong bốn tar; không phải raw-logit audit đầy đủ. |
| Qwen3, V4-success gốc | 0,952793 | Không tách trong bảng này | 3.539/3.763 SUCCESS được cung cấp; thiếu xác minh độc lập membership/score vector đầy đủ. |
| Qwen3, Recovery224 | 0,954519 | Không tách trong bảng này | 224/224 SUCCESS được báo cáo, cohort/config riêng. |
| Qwen3, bản ghép mô tả | 0,952935 | 2.932/3.763 = 77,92% | Số từ tổng hợp được cung cấp; chưa tái tính độc lập AUROC từ vector điểm gốc đầy đủ. |
| Moondream2 | Chưa có kết quả HNLO TRAIN tương thích đã audit | Chưa xác lập tại các nguồn này | Vẫn thuộc yêu cầu bốn mô hình; không bỏ hoặc tự thay endpoint. |

Nguồn Qwen2.5: [CPU completion PA3-R2](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_r2_cpu_completion_20261015.md).
Hai cách tính saved-score AUROC InternVL3 trong báo cáo cho
`0.8861824613751756` và `0.8861824613751758`; sai khác khoảng `2.2e-16` là số học,
không phải hai thí nghiệm. Những ô chưa có bằng chứng không được thay bằng số demo.

## Raw audit, saved score và provenance chưa khép

**Qwen2.5:** raw audit lịch sử tính lại 3.763/3.763 SUCCESS và AUROC trên CPU
Linux. Lần phân tích 23/10 kế thừa trạng thái đó, đối chiếu summary/CSV/checksum
và saved score, không thực hiện raw audit mới. Hạn chế Shard 1 outer receipt
và khác biệt Windows 1-ULP vẫn được giữ ở CPU completion.

**InternVL3:** saved-report recomputation xác nhận tính nhất quán số học của
score/confusion; chưa chứng minh toàn bộ chuỗi raw logits, token alignment,
runtime và integrity bằng raw replay. Không đổi nhãn mức bằng chứng thành raw PASS.

**Qwen3:** V4 gốc báo cáo 3.539 SUCCESS (94,05%), 1 TECHNICAL_ERROR và
223 NOT_ATTEMPTED. Recovery224 báo cáo 49 Anomaly/175 Normal. Sidecar S2 đã kiểm
tra thuộc lượt chạy lại trùng attempt, không phải S2 V4 đầu tiên. Archive gốc
được kỳ vọng có SHA-256
`2dc356fcba9fe2ce5dfc4e3dc9a45286fe5382f574c02d38d7517580e38cd920`
chưa được tìm thấy tại các vị trí đã kiểm tra trong báo cáo lịch sử.

Ghép các sidecar sẵn có có thể khớp 3.763 ID/support/confusion, nhưng không xác
nhận độc lập 717 ảnh S2 gốc hoặc toàn bộ 3.539 V4-success gốc. Giữ
`baseline_pooling_allowed=false`; bản ghép là mô tả xuyên cohort, không biến V4
thành baseline hoàn tất và không lấy trung bình AUROC hai cohort. Nguồn:
[báo cáo provenance đã sửa](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/reports/three_model_scientific_analysis_20261023.md),
[OOM evidence boundary](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/qwen3_s2_oom_20261022.md#source-and-evidence-boundary),
[issue #125 CONSUMED](https://github.com/tantdna2/SafeShift/issues/125#issuecomment-6354355448).

**Moondream2:** nguồn ghi Starmie T1 CPU PASS 28/28 và bằng chứng interface T4
trước đó; đây không phải kết quả HNLO TRAIN. Còn thiếu real raw-logit hook,
decision alignment, state-preservation validation và TRAIN tương thích đã audit.
Capture PREP mới có CPU giả lập; không lấy BF16/T4 làm blocker duy nhất hoặc
tuyên bố model bất khả thi. Nguồn: [T1 CPU](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/hnlo_t1_cpu_results_20261017.md),
[capture PREP](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/hnlo_raw_logit_capture_prep_20261017.md)
và báo cáo ba mô hình.

## Ý nghĩa khoa học và giới hạn

- Qwen2.5 và InternVL3 sinh nhãn Anomaly cho cả 3.014 Normal; AUROC hard label
  nhị phân là 0,5. Điểm HNLO vẫn xếp hạng được, nhưng chưa chứng minh có ngưỡng
  quyết định an toàn hoặc ưu thế so với mọi đối chứng từ generation.
- Qwen3 ghép báo cáo 14/490 Level01 → Level04, 38/749 Anomaly bị bỏ sót và
  443/3.014 Normal bị báo động. Các tỷ lệ này thuộc **nhãn sinh ra**, không phải
  FNR/FPR sau threshold HNLO. Chưa có ngưỡng HNLO được xác nhận.
- Accuracy bốn mức Qwen3 77,92% thấp hơn đối chứng luôn Level04 80,10% trong
  cohort mất cân bằng; điều đó cũng không làm đối chứng luôn Normal an toàn.
- TRAIN đã phơi nhiễm không chứng minh generalization. Duplicate xuyên split,
  phụ thuộc nguồn/chuỗi, domain/platform confounding, chỉ 8 Level03 TRAIN và
  thiếu Anomaly TEST metallurgy giới hạn suy luận. Không gọi khác biệt miền
  mô tả là kiểm định chuyển miền độc lập.
- Chưa có CI phù hợp phụ thuộc nguồn hay kiểm định chênh AUROC đủ ba mô hình;
  không gọi thứ hạng quan sát được là ưu thế thống kê hoặc nhân quả. RQ2 HNLO
  chưa có kết quả sau kiểm soát; chưa xác nhận calibration, causal hazard validity
  hoặc hoàn tất Seminar bốn mô hình.
- Prompt wrappers, tokenizer/revision, preprocessing/precision/runtime khác
  nhau. Qwen2.5 R2 clamp không gian trước vision merger ở 24/3.763 ảnh;
  Qwen3 T4×2 so với hai model T4×1. Không quy mọi chênh lệch cho kiến trúc.

Các nhận định và mẫu số ở mục này kế thừa báo cáo ba mô hình đã dẫn, không phải
phân tích mới. Demo CPU chỉ kiểm tra phần mềm trên bản ghi tổng hợp; không dùng
để bổ sung bảng khoa học. Việc còn thiếu và approval gates nằm ở
[ROADMAP](ROADMAP.md); source/release lịch sử ở [HISTORY](HISTORY.md).
