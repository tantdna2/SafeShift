# SafeShift — Benchmark First trên Full-TRAIN

**PROVISIONAL_PRE_FINAL_ADMISSION.** Đã đo cả ba sản phẩm trên cùng
**3.763 TRAIN ID** đã phơi nhiễm của InspecSafe-V1, gồm 749 Hazard
(Level01–03) và 3.014 Normal (Level04). MiniCPM strict C1 là sensitivity.
Các hệ thống có version, mô hình, cấu hình và hậu xử lý khác nhau.
So sánh giữ nguyên giao thức đánh giá, cohort và mẫu số. Kết quả mô tả
các sản phẩm nhãn đã lưu, trong phạm vi TRAIN hồi cứu.
[Chỉ thị Owner](https://github.com/tantdna2/SafeShift/pull/136#issuecomment-7206868367),
[quyết định và phạm vi](DECISIONS.md#dec-20261127-owner-retrospective-benchmark-authority).

## Xác minh đầu vào

| Đầu vào | Bằng chứng đã kiểm |
| --- | --- |
| Cohort và Qwen3 | Dùng lại hai projection đã kiểm. Manifest Qwen3 SHA256 `7e7793073eb639a2d0bd22e84c11cd773be7fdb86e7e1f5f59e3baf0dd0c98de` gồm 3.539 V4 SUCCESS và đúng 224 Recovery224. Kiểm 3.763 ID, image SHA256, split, GT, domain. [Hợp đồng Qwen3](QWEN3_FULL_TRAIN_COMPOSITE_V1.md). |
| InternVL3.5 | Kiểm bytes và chuỗi hash của 36 event lịch sử và 35 event continuation cùng mirror. Manifest continuation SHA256 `8bd91408bcac1510aec15f70428e973b1c7c3e72a64272f7d35dc2c330c0e947`. 23 attempt có kết quả trong 28 attempt ghi nhận. Đối chiếu archive, sidecar, per-record raw hash và exact provenance với audit cục bộ cho đủ 3.763 SUCCESS. Attempt 23 dùng ZIP `217f685b…` từ event 25. Hai lượt kiểm tạo projection và biên bản trùng byte. Manifest bàn giao `6c043c753f1c9bda037df4da10ff18217ab6dd7c7638f03834de7055f031063c` niêm phong script, projection và receipt. [Phạm vi đối soát InternVL](../TRAIN3763_DEFERRED_RECONCILIATION.md). |
| MiniCPM V1 và C1 | Tái tạo bản dẫn xuất từ hai custody local bằng normalizer đã duyệt của PR #214. Receipt `385ceddb799e735e3eecea04457f3a178996e29992e69265762a5031a6cb1fbd` và cả bốn member khớp byte; còn nguyên 13 nguồn và status/label C1. Chiếu ảnh/ID vào cohort bằng tất cả 3.763 record, không chọn dự đoán theo GT. [Hợp đồng normalization](MINICPM_FULLTRAIN_NORMALIZATION_V1.md), [hậu kiểm #214](https://github.com/tantdna2/SafeShift/pull/214#issuecomment-7184951265). |

Bốn projection ghim đúng SHA256 và kích thước trong
[cấu hình benchmark](../../configs/analysis/full_train_benchmark.v1.json).
Join dùng exact ID, hash ảnh, split, GT và folder domain. GT chỉ tham gia
đánh giá sau khi chọn nguồn. Toàn bộ 3.763 ID được giữ, với 3.719 SHA256 ảnh
phân biệt. Chứng từ cục bộ và niêm phong này phục vụ đọc lại label products.
Final Admission, provider history và phê duyệt học vụ nằm ở các quy trình riêng.

InspecSafe-V1 của Liu và cộng sự tại revision `f3cb7d3e` công bố theo CC BY 4.0.
Giữ nguyên GT và split gốc. Chỉ thống kê gộp vào Git; bản ghi, raw, ảnh và
projection giữ trong custody cục bộ. [InspecSafe-V1](https://huggingface.co/datasets/Tetrabot2026/InspecSafe-V1/tree/f3cb7d3e7827c1afc1c5bfd0524257984bba46ab),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
[bài báo dữ liệu](https://doi.org/10.1038/s41597-026-07796-x).

## Kết quả đo trên TRAIN

FNR là tỷ lệ Hazard bị dự đoán thành Normal. FPR là tỷ lệ Normal bị dự đoán
thành Hazard. Severe miss là Level01 bị dự đoán thành Normal. C1 giữ INVALID
trong mẫu số planned và support của GT, với U_A/U_N riêng. Macro-F1 và
Balanced Accuracy theo miền dùng các lớp có GT support. Mẫu số miền khác
nhau đáng kể, như 9 Hazard và 8 Level01 trong luyện kim.

### Tổng thể

| Sản phẩm | Hợp lệ/planned | Accuracy | Macro-F1 | Balanced accuracy |
| --- | --- | --- | --- | --- |
| Qwen3 Composite V1 | 3763/3763 | 77,92% (2932/3763) | 45,32% | 64,49% |
| InternVL3.5 Grammar V2 | 3763/3763 | 46,90% (1765/3763) | 33,90% | 50,60% |
| MiniCPM Normalization V1 | 3763/3763 | 81,13% (3053/3763) | 41,52% | 46,74% |
| MiniCPM strict C1 | 3558/3763 | 75,68% (2848/3763) | 40,59% | 45,04% |

| Sản phẩm | Hazard Recall | Hazard Precision | Binary F1 | FNR | FPR | Severe miss | U_A/U_N |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3 Composite V1 | 94,93% (711/749) | 61,61% (711/1154) | 74,72% | 5,07% (38/749) | 14,70% (443/3014) | 2,86% (14/490) | 0/0 |
| InternVL3.5 Grammar V2 | 97,33% (729/749) | 32,24% (729/2261) | 48,44% | 2,67% (20/749) | 50,83% (1532/3014) | 0,82% (4/490) | 0/0 |
| MiniCPM Normalization V1 | 63,68% (477/749) | 74,88% (477/637) | 68,83% | 36,32% (272/749) | 5,31% (160/3014) | 30,00% (147/490) | 0/0 |
| MiniCPM strict C1 | 63,68% (477/749) | 74,88% (477/637) | 68,83% | 36,32% (272/749) | 5,31% (160/3014) | 30,00% (147/490) | 0/205 |

### Metric theo lớp

| Sản phẩm | GT | Support | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- |
| Qwen3 Composite V1 | Level01 | 490 | 60,59% | 33,27% | 42,95% |
| Qwen3 Composite V1 | Level02 | 251 | 29,56% | 76,89% | 42,70% |
| Qwen3 Composite V1 | Level03 | 8 | 2,16% | 62,50% | 4,17% |
| Qwen3 Composite V1 | Level04 | 3014 | 98,54% | 85,30% | 91,45% |
| InternVL3.5 Grammar V2 | Level01 | 490 | 42,04% | 21,02% | 28,03% |
| InternVL3.5 Grammar V2 | Level02 | 251 | 29,26% | 69,72% | 41,22% |
| InternVL3.5 Grammar V2 | Level03 | 8 | 0,35% | 62,50% | 0,70% |
| InternVL3.5 Grammar V2 | Level04 | 3014 | 98,67% | 49,17% | 65,63% |
| MiniCPM Normalization V1 | Level01 | 490 | 82,76% | 24,49% | 37,80% |
| MiniCPM Normalization V1 | Level02 | 251 | 36,89% | 30,28% | 33,26% |
| MiniCPM Normalization V1 | Level03 | 8 | 1,05% | 37,50% | 2,04% |
| MiniCPM Normalization V1 | Level04 | 3014 | 91,30% | 94,69% | 92,96% |
| MiniCPM strict C1 | Level01 | 490 | 82,76% | 24,49% | 37,80% |
| MiniCPM strict C1 | Level02 | 251 | 36,89% | 30,28% | 33,26% |
| MiniCPM strict C1 | Level03 | 8 | 1,05% | 37,50% | 2,04% |
| MiniCPM strict C1 | Level04 | 3014 | 90,69% | 87,89% | 89,27% |

### Ma trận nhầm lẫn

**Qwen3 Composite V1**

| GT / Dự đoán | Level01 | Level02 | Level03 | Level04 | INVALID |
| --- | --- | --- | --- | --- | --- |
| Level01 | 163 | 303 | 10 | 14 | 0 |
| Level02 | 2 | 193 | 32 | 24 | 0 |
| Level03 | 0 | 3 | 5 | 0 | 0 |
| Level04 | 104 | 154 | 185 | 2571 | 0 |

**InternVL3.5 Grammar V2**

| GT / Dự đoán | Level01 | Level02 | Level03 | Level04 | INVALID |
| --- | --- | --- | --- | --- | --- |
| Level01 | 103 | 339 | 44 | 4 | 0 |
| Level02 | 1 | 175 | 59 | 16 | 0 |
| Level03 | 0 | 3 | 5 | 0 | 0 |
| Level04 | 141 | 81 | 1310 | 1482 | 0 |

**MiniCPM Normalization V1**

| GT / Dự đoán | Level01 | Level02 | Level03 | Level04 | INVALID |
| --- | --- | --- | --- | --- | --- |
| Level01 | 120 | 128 | 95 | 147 | 0 |
| Level02 | 1 | 76 | 54 | 120 | 0 |
| Level03 | 0 | 0 | 3 | 5 | 0 |
| Level04 | 24 | 2 | 134 | 2854 | 0 |

**MiniCPM strict C1**

| GT / Dự đoán | Level01 | Level02 | Level03 | Level04 | INVALID |
| --- | --- | --- | --- | --- | --- |
| Level01 | 120 | 128 | 95 | 147 | 0 |
| Level02 | 1 | 76 | 54 | 120 | 0 |
| Level03 | 0 | 0 | 3 | 5 | 0 |
| Level04 | 24 | 2 | 134 | 2649 | 205 |

### Theo miền

| Miền | Sản phẩm | N | Accuracy | Macro-F1 | Balanced accuracy | FNR | FPR | Severe miss |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| coal_conveyor | Qwen3 Composite V1 | 822 | 73,48% | 45,13% | 75,42% | 1/172 | 135/650 | 1/109 |
| coal_conveyor | InternVL3.5 Grammar V2 | 822 | 38,81% | 32,82% | 62,38% | 0/172 | 410/650 | 0/109 |
| coal_conveyor | MiniCPM Normalization V1 | 822 | 75,55% | 45,32% | 66,91% | 21/172 | 90/650 | 5/109 |
| metallurgy | Qwen3 Composite V1 | 543 | 76,43% | 29,12% | 25,91% | 1/9 | 119/534 | 1/8 |
| metallurgy | InternVL3.5 Grammar V2 | 543 | 12,52% | 8,22% | 8,35% | 0/9 | 467/534 | 0/8 |
| metallurgy | MiniCPM Normalization V1 | 543 | 88,58% | 33,38% | 63,30% | 1/9 | 54/534 | 1/8 |
| oil_chemical | Qwen3 Composite V1 | 778 | 71,72% | 54,40% | 54,83% | 15/287 | 38/491 | 12/239 |
| oil_chemical | InternVL3.5 Grammar V2 | 778 | 35,86% | 33,97% | 26,91% | 4/287 | 269/491 | 3/239 |
| oil_chemical | MiniCPM Normalization V1 | 778 | 70,44% | 46,40% | 43,81% | 81/287 | 12/491 | 58/239 |
| power | Qwen3 Composite V1 | 656 | 93,14% | 81,45% | 76,47% | 19/81 | 16/575 | 0/31 |
| power | InternVL3.5 Grammar V2 | 656 | 84,76% | 73,01% | 69,00% | 12/81 | 68/575 | 0/31 |
| power | MiniCPM Normalization V1 | 656 | 90,55% | 60,64% | 52,93% | 47/81 | 4/575 | 10/31 |
| tunnel | Qwen3 Composite V1 | 964 | 77,18% | 48,78% | 66,98% | 2/200 | 135/764 | 0/103 |
| tunnel | InternVL3.5 Grammar V2 | 964 | 56,33% | 40,08% | 56,30% | 4/200 | 318/764 | 1/103 |
| tunnel | MiniCPM Normalization V1 | 964 | 83,92% | 42,73% | 40,58% | 122/200 | 0/764 | 73/103 |

### So sánh cặp trên cùng ID

| Cặp | Mức | Bất đồng | Cùng đúng | Cùng sai | Chỉ trái đúng | Chỉ phải đúng |
| --- | --- | --- | --- | --- | --- | --- |
| InternVL3.5 Grammar V2 / MiniCPM Normalization V1 | 4 lớp | 47,44% (1785/3763) | 1651 | 596 | 114 | 1402 |
| InternVL3.5 Grammar V2 / MiniCPM Normalization V1 | Hazard/Normal | 43,16% (1624/3763) | 1959 | 180 | 252 | 1372 |
| Qwen3 Composite V1 / InternVL3.5 Grammar V2 | 4 lớp | 38,27% (1440/3763) | 1728 | 794 | 1204 | 37 |
| Qwen3 Composite V1 / InternVL3.5 Grammar V2 | Hazard/Normal | 30,80% (1159/3763) | 2167 | 437 | 1115 | 44 |
| Qwen3 Composite V1 / MiniCPM Normalization V1 | 4 lớp | 19,45% (732/3763) | 2745 | 523 | 187 | 308 |
| Qwen3 Composite V1 / MiniCPM Normalization V1 | Hazard/Normal | 14,91% (561/3763) | 3026 | 176 | 256 | 305 |

| Cặp | GT | Support | Cùng false-safe | Chỉ trái false-safe | Chỉ phải false-safe |
| --- | --- | --- | --- | --- | --- |
| InternVL3.5 Grammar V2 / MiniCPM Normalization V1 | Hazard | 749 | 20 | 0 | 252 |
| InternVL3.5 Grammar V2 / MiniCPM Normalization V1 | Level01 | 490 | 4 | 0 | 143 |
| Qwen3 Composite V1 / InternVL3.5 Grammar V2 | Hazard | 749 | 15 | 23 | 5 |
| Qwen3 Composite V1 / InternVL3.5 Grammar V2 | Level01 | 490 | 1 | 13 | 3 |
| Qwen3 Composite V1 / MiniCPM Normalization V1 | Hazard | 749 | 35 | 3 | 237 |
| Qwen3 Composite V1 / MiniCPM Normalization V1 | Level01 | 490 | 12 | 2 | 135 |

### Độ nhạy MiniCPM strict C1 → V1

| Endpoint | Strict C1 | V1 | Chênh lệch |
| --- | --- | --- | --- |
| accuracy | 75,68% (2848/3763) | 81,13% (3053/3763) | 5,45% (205/3763) |
| hazard_false_safe | 36,32% (272/749) | 36,32% (272/749) | 0,00% (0/749) |
| hazard_missed_or_invalid | 36,32% (272/749) | 36,32% (272/749) | 0,00% (0/749) |
| level01_false_safe | 30,00% (147/490) | 30,00% (147/490) | 0,00% (0/490) |
| valid_label_rate | 94,55% (3558/3763) | 100,00% (3763/3763) | 5,45% (205/3763) |

## Điểm yếu và cơ chế lỗi

- **Qwen3.** Macro-F1 và Balanced Accuracy cao nhất trong ba sản phẩm. Accuracy
  77,92% thấp hơn mốc luôn đoán Normal (80,10%), với Hazard Recall 94,93% so với
  0 ở mốc đó. Hạ Level01 thành Level02 **303/490** lần. Precision Level03 là
  5/232. Điện chiếm 19/38 false-safe, còn dầu và hóa chất chiếm 12/14 severe
  miss. Điện có FNR cao nhất (19/81), luyện kim có Macro-F1 thấp nhất (29,12%).
- **InternVL3.5.** FNR 20/749 và severe miss 4/490 thấp nhất, đi kèm FPR
  1.532/3.014. Ô Normal → Level03 có **1.310** ca, chiếm 85,51% FP.
  Level03 precision là 5/1.418. Level01 → Level02 có 339/490 ca. Luyện kim
  có Macro-F1 8,22%, FPR 467/534. Điện có FNR cao nhất (12/81).
- **MiniCPM V1.** Accuracy 81,13% cao nhất và FPR 160/3.014 thấp nhất, trong
  khi FNR **272/749** và severe miss **147/490** cao nhất. Đường hầm có
  FNR 122/200, severe miss 73/103 và FPR 0/764. Điện có FNR 47/81.
  Macro-F1 thấp nhất trong luyện kim (33,38%).
- **Cơ chế đã xác minh.** Cả **205/205** conversion là GT Level04, gồm điện
  114, đường hầm 64, dầu và hóa chất 26, luyện kim 1, băng tải than 0. Mọi
  ca chuyển từ INVALID sang true negative. Tăng **205/3.763**, tức 5,45 điểm
  phần trăm cho độ phủ và accuracy, giảm U_N từ 205 xuống 0. FNR, FPR và
  severe miss giữ nguyên theo mẫu số cố định. Việc kiểm GT diễn ra sau
  normalization. Không suy độ thuần 205/205 sang dữ liệu mới.
  [Cách xác nhận lỗi định dạng gốc](MINICPM_FULLTRAIN_INVALID_REVIEW_20261126.md).

Phân bố GT Normal 3.014/3.763 và Level03 8/3.763 cho thấy mất cân bằng thực
tế. Bảng nhầm lẫn xác nhận hiện tượng hạ severity, dự đoán Level03 quá nhiều
và bỏ sót theo miền. Các giả thuyết còn mở gồm lệch ranh giới phân loại,
ảnh hưởng của grammar/prompt hoặc resampler, dịch chuyển giữa nguồn, và
shortcut do người hoặc thiết bị xuất hiện. Folder domain và nhãn đầu ra
chưa cô lập được những nguyên nhân đó. Danh sách riêng chọn 60 ID theo quy
tắc hash cố định trong từng nhóm/miền, gồm các ca bỏ sót chung, ba nhóm lỗi
trọng tâm và ca đúng đối chứng. Chưa review ảnh hay lý do thị giác.

## Bổ trợ và giới hạn của kết hợp

InternVL phát hiện **23/38** false-safe và **13/14** severe miss của Qwen3.
Qwen3 phát hiện **5/20** false-safe của InternVL. Hai hệ cùng bỏ sót 15 Hazard,
gồm một Level01. Cả 20 ca InternVL bỏ sót cũng bị MiniCPM bỏ sót. MiniCPM
phát hiện 3/38 false-safe của Qwen3, trong khi sửa được 302 báo động giả của
Qwen3 ở mặt nhãn nhị phân. Đây là giao nhau theo ID, chưa đo khả năng chọn
trước ca nào để sửa dưới một budget thực tế.

Có 1.630 ID cả ba đúng bốn lớp và **507** ID cả ba sai, trong đó 15 ca Hazard
đều thành Normal. Quy tắc đa số 2/3 yêu cầu hai dự đoán trùng. Khi tính
thiếu nhãn vào planned, đa số không trọng số
đúng trên tối đa **2.864/3.763 = 76,11%**, thấp hơn Qwen3 và MiniCPM. Đó là
cận từ tập ca có ít nhất hai nhãn đúng theo GT. Một hệ chọn nhãn khi không có
đa số phải đánh giá riêng. Đối với nhị phân, gộp cảnh báo Qwen3 và InternVL
theo OR sẽ giữ 15 false-safe nhưng có 1.553/3.014 FP (51,53%). Đây là hệ quả
từ giao các nhãn đã lưu, chưa triển khai ensemble hay rule vận hành.

## Hướng nghiên cứu trình Owner

| Vấn đề và bằng chứng | Hướng ứng viên theo rubric | Cách chứng minh và guardrail |
| --- | --- | --- |
| Lớp hiếm và chênh lệch miền. Level03 có 8 GT, luyện kim có 9 Hazard, đường hầm có 122/200 MiniCPM false-safe. | **CV-A/D** hỗ trợ CT1 và CT2. Kiểm nhóm hiếm, mapping nguồn và shortcut bằng cohort development/validation đủ quyền. Cân nhắc sampling cân miền sau khi biết support và nguồn. | E3 đo worst-domain FNR, severe miss, Macro-F1, support và kết quả âm. Giữ split đánh giá tự nhiên và chỉ dùng CI bootstrap khi xác định được cluster độc lập phù hợp. |
| Qwen3 và InternVL hạ Level01 nhiều. InternVL dự đoán Level03 cho 1.310 Normal. | **CV-B/D (CT1)** và **CV-B/C (CT2)**. Audit mapping trước, sau đó đối chứng có kiểm soát một yếu tố như cách biểu thị severity, prompt grounding hoặc grammar. | E1 cùng protocol, E2 ablation từng yếu tố, E4 ca trước–sau. Metric chính ứng viên là severe miss/FNR và recall Level01; guardrail FPR, Macro-F1, valid rate, latency, chi phí. |
| InternVL bổ trợ hướng phát hiện Qwen3 false-safe, nhưng FPR tổng cao. MiniCPM giảm một số cảnh báo giả, nhưng có nhiều false-safe. | **CV-C (CT2)**. Cân nhắc dùng tín hiệu bất đồng để chuyển ca cho người kiểm tra dưới budget, so với baseline đơn mô hình, random hoặc đối chứng điểm hợp lệ. | E1 paired, E2 tắt từng tín hiệu, E3 overload và miền xấu nhất. Báo capture severe miss theo budget, số ca chuyển sai, coverage, latency và chi phí. Kết quả đa số và OR là đối chứng mô tả. |
| Điểm nội tại chưa đồng nhất giữa các nguồn. | **CV-B/C (CT1/CT2)**. Chỉ xét calibration/threshold tuning khi có score đúng nghĩa và validation độc lập. | Đăng ký trước mục tiêu xác suất và operating point. Đo Brier/reliability, AUPRC hoặc FNR@fixed FPR tùy estimand; không dùng accuracy đơn lẻ hoặc fit trên TRAIN này. |
| 205 conversion MiniCPM truy vết được và 507 lỗi chung cần xem lại. | **CV-C/D (CT3)**. Cân nhắc viewer truy nguồn lỗi, hiển thị provenance và cờ thiếu bằng chứng có thật. | E4 phân biệt lỗi nhãn với lỗi lý do; E5 giữ audit trail. Thử task-based với người kiểm tra có quyền, đo độ chính xác, thời gian và workload. Chỉ đo IoU khi có vùng GT được duyệt. |

Codex và Antigravity Neon Medium độc lập đối chiếu các lỗi và bổ trợ từ số
liệu đã đo. Cả hai ưu tiên false-safe và severity với FPR làm guardrail,
giới hạn suy luận từ lớp hiếm và nguồn chưa độc lập. Phản biện đề xuất dùng
bổ trợ bất đối xứng để xây dựng đối chứng triage. Báo cáo xếp ứng viên đó
vào CV-C theo rubric giảng viên và giữ CV-A cho dữ liệu/phân phối. Hai bên
đồng thuận về số liệu. Giữ các ứng viên chưa triển khai cho Owner chốt sau
phản biện. [Rubric E1–E5 và điều kiện thực nghiệm](THESIS_EXECUTION_PLAN_2026.md).

## Điểm, độ bất định và tái lập

Cả ba sản phẩm không có đầu vào score chung hợp lệ. AUROC, AUPRC,
FNR@fixed FPR, calibration và risk–coverage cấp sản phẩm là **N/A**. Qwen3
giữ hai AUROC mô tả theo nguồn (V4 0,952793 trên 3.539 SUCCESS và Recovery
0,954519 trên 224), với giới hạn tương thích nên không pooling. Chỉ số
mô tả cohort cố định được báo kèm support; chưa có CI suy rộng do chưa có
source clusters độc lập và có nhóm trùng ảnh. TEST vẫn đóng.
[Giới hạn score Qwen3](QWEN3_FULL_TRAIN_COMPOSITE_V1.md#separate-hnlo-compatibility-gate).

Run thật trên Windows, Python 3.11.9, chuẩn thư viện Python. Source
`cba568ef1ea8a97ff6a547da832423af7de46f5a` sạch. Receipt SHA256
`2bad440a45e94d1df8e8ec8cc4dcbfe0d7473ebf0c730027786ae3aa2220d0b0`.
Benchmark JSON SHA256
`88e9bfe00201c09a7aba72c8cb2dbe2568cdf070bad8219cf167a2e6c595c50e`.
Cohort identity SHA256
`9427251782a0f4e0403f2f681ad9d6bda54431253826df51be0c2599fab69471`.
Bộ kiểm số học riêng thực hiện **3.204 đối chiếu**, gồm confusion, metric
lớp/miền, paired safety và 205 conversion.

```console
python -B -m scripts.benchmark_full_train --input-dir data/processed/full-train-benchmark-v1/provisional-inputs-v1 --output-dir data/processed/full-train-benchmark-v1/replay-01
python -B -m unittest discover -s tests -p test_full_train_benchmark.py -v
```

Các projection có bốn JSON riêng theo [hợp đồng CLI](../../scripts/benchmark_full_train.py)
và receipt từ Qwen3, InternVL hoặc MiniCPM. Mỗi source cần run, attempt, model
revision, config và archive SHA256. Chỉ dùng bộ exact đã ghim và đúng quyền.
CLI từ chối sai SHA, GT, hash ảnh, domain, ID, split hoặc đích đã có.
Run xuất `benchmark.json`, `metrics.csv`, `confusion.html` và `receipt.json`
trong thư mục ignored. Biểu đồ FNR/FPR và bảng gộp cũng lưu cục bộ.
M2/R1–R5 lịch sử có [lệnh riêng](../SEMINAR_ANALYSIS.md). GitHub HEAD của PR
chờ cổng review/merge hiện hành.
