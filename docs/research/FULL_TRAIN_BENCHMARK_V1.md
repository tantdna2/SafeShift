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

## Truy nguyên các nhóm lỗi A–E

Từ hai danh sách review đã chuẩn bị, chọn **24 ID riêng biệt** cho chín
nhóm đối chiếu có thể chồng lấp. Ưu tiên phủ miền rồi dùng thứ tự đã
niêm phong trong danh sách. Kiểm cả ba projection khớp TRAIN, GT mức ảnh,
folder domain và SHA256 ảnh. Qwen3 khớp nhãn và nguồn ở ledger V4/Recovery
đã chọn trên cả 24 ID. InternVL và MiniCPM khớp SHA256 và token nhãn ở
48 thành viên raw đã lưu. Cả 24 MiniCPM là nhãn C1 hợp lệ trong mẫu này.
Audit dùng ca có chủ đích để truy xuất nguồn lỗi, với mẫu số toàn cohort lấy
từ benchmark đã niêm phong. SHA256 của biên bản gộp là
`9606d6f6f4d588f3448f956490106eb256cbe6784dbca0444c2b12df2561dd1d`.

Phạm vi Owner đã cấp gồm saved outputs, GT mức ảnh, miền và hash. Các
biên bản giữ ID và đối chiếu row-level cục bộ. Kiểm SHA chứng minh đúng
danh tính ảnh theo hồ sơ và đúng bản lưu. Việc xác định vật thể, độ che khuất,
ánh sáng và người trong ảnh còn cần xem mẫu visual theo quyền riêng.
Bộ dữ liệu mô tả nhãn mức ảnh và polygon đối tượng. Polygon đối tượng
chưa tự xác định lý do cho nhãn nguy cơ hoặc cho quyết định của VLM.
[Phạm vi Owner](https://github.com/tantdna2/SafeShift/pull/136#issuecomment-7206868367),
[InspecSafe-V1 của Liu và cộng sự](https://arxiv.org/abs/2601.21173),
[quy ước nguồn/GT](../DATA_AND_ETHICS.md).

| Nhóm | Đã xác minh | Giả thuyết có căn cứ và điều chưa xác định |
| --- | --- | --- |
| **A — Hạ Level01 xuống Level02** | Qwen3 303/490, InternVL 339/490, MiniCPM 128/490. Trên shortlist rộng hơn, 15/15 dòng Qwen3 hạ Level01 cũng được InternVL trả Level02, 9/15 được cả ba trả Level02. Ba đối chiếu mỗi mô hình xác nhận nhãn đã có trong ledger Qwen3 và raw InternVL. C1 đặt thiếu PPE trong ví dụ tổng quát Level02, trong khi bảng ngành đặt một số thiếu PPE ở Level01 và thay đổi mức theo ngành. | Chồng lấn rubric là cơ chế có thể gây lẫn mức. Cần người xem ảnh có quyền xác định hazard, PPE và miền rồi thử một thay đổi duy nhất về thứ tự ưu tiên rubric. Chưa biết lỗi nào đến từ nhìn thiếu vật thể, chọn sai miền hay diễn giải severity. |
| **B — InternVL gán Level03 cho Normal** | 1.310/3.014 Normal thành Level03, chiếm 85,51% FP. Năm mẫu ở năm miền đều giữ token Level03 trong archived response. Trong shortlist rộng hơn, Qwen3 và MiniCPM cùng trả Normal ở 11/15 dòng của nhóm này. T0 ghi từ advisory TRAIN160 cũ 34 báo động giả trên Normal nơi MiniCPM đúng, trước khi áp dụng Grammar V2. | Grammar V2 chỉ cho phép bốn chuỗi canonical và có thể đổi prefix của trajectory. Xu hướng báo động giả đã được ghi ở một cohort và cấu hình khác, nên attribution riêng cho grammar chưa xác định. Cần ablation paired giữ cùng ảnh, model, prompt và mọi yếu tố còn lại. |
| **C — MiniCPM bỏ sót ở đường hầm và điện** | Đường hầm FNR 122/200, severe miss 73/103, FPR 0/764. Điện FNR 47/81. Ba ca đã kiểm ở mỗi miền phát ra Level04 canonical trong C1 gốc. 205 conversion trước đó thuộc GT Normal, khớp exact cụm mô tả có trong C1. Chúng giảm lỗi format và không đổi 272 false-safe toàn TRAIN. | Chuỗi format giải thích đúng nhóm 205. Với bỏ sót đã có token Level04, chưa cô lập nguyên nhân do tín hiệu ảnh, phân phối nguồn, prompt hay resampler. Tách audit mức ảnh khỏi mọi suy luận về precision. |
| **D — Lỗi chung cả ba** | 507/3.763 ID cùng sai bốn lớp. Trong đó 15/749 Hazard đều thành Normal, gồm một Level01. Kiểm ba ca cùng Normal ở ba miền và ba ca cùng sai dù nhãn bất đồng. Ledger và raw member khớp nhãn từng case. | Cùng sai chỉ đo giới hạn của ba sản phẩm đã lưu trên cohort này. Lỗi rubric/GT, tín hiệu chung khó quan sát hoặc dấu hiệu shortcut cần adjudication độc lập. Các case bất đồng trong nhóm cùng sai cần được giữ khi thử chuyển ca review. |
| **E — InternVL phát hiện ca Qwen3 bỏ sót** | 23/38 Hazard và 13/14 Level01 Qwen3 bỏ sót được InternVL báo Hazard. Đối chiếu ba rescue và ba cảnh báo giả bổ sung xác nhận hai hướng đều có thật trong bản lưu. Trên toàn TRAIN, quy tắc chỉ xét Qwen3-Normal và InternVL-Hazard xác định 1.133 ca, gồm 23 Hazard và 1.110 Normal. Precision của cờ là **23/1.133 = 2,03%**, workload **30,11%** của 3.763. | Có tín hiệu bổ trợ nhưng cờ phổ thông gây khoảng 48 cảnh báo giả cho mỗi Hazard phát hiện. Cần so cùng ngân sách với random trong tập đủ điều kiện, baseline đơn mô hình và ablation từng tín hiệu. Chưa chứng minh phân tầng mức InternVL hoặc dùng MiniCPM lọc báo động sẽ hạ chi phí mà giữ severe capture. |

Nguồn về logic hiện hành gồm [prompt C1 bất biến](../../configs/pilot/classification_c1.txt),
[Grammar V2 và giới hạn counterfactual](INTERNVL_GRAMMAR_SCIENCE_V1.md),
[bằng chứng T0 TRAIN160](T0_FALSE_SAFE_EVIDENCE_20261101.md#3-nguồn-dữ-liệuoutputs-thật-đã-định-danh)
và [chẩn đoán format MiniCPM](MINICPM_FULLTRAIN_INVALID_REVIEW_20261126.md).
Shortlist tổng hợp cũ có 64 dòng, 60 ID khác nhau và nhóm đối chứng toàn
Normal. Đối chiếu tiếp đã bổ sung lát cắt rescue và false alarm trong chính
union shortlist. Để kiểm nguyên nhân bằng mắt hoặc E4 trước–sau, cần thêm
đối chứng đúng Hazard ghép cùng mức/miền, reviewer xem ảnh mù với kết quả
model và đủ quyền truy cập.

Có 1.630 ID cả ba đúng bốn lớp. Đa số 2/3 không trọng số đạt tối đa
2.864/3.763 (76,11%) nếu giữ planned và tính ca không có majority là sai.
Kết hợp OR Qwen3–InternVL giữ 15 false-safe và làm tăng FP từ 443
lên 1.553/3.014 (51,53%). Hai đối chứng này được suy từ các bảng paired
đã có. Cả 20 ca InternVL bỏ sót đều bị MiniCPM bỏ sót, còn MiniCPM trả đúng
302 ca Normal mà Qwen3 báo Hazard. Mức bổ trợ bất đối xứng là căn cứ để
thiết kế đối chứng review, chưa chứng minh lợi ích của một phương pháp.

## Ba phương án trình Owner

| Ưu tiên | Phương án và giả thuyết | Metric, đối chứng và bằng chứng cần có | Tính mới, khả thi và chi phí |
| --- | --- | --- | --- |
| **1 — CT1, CV-B/D: phân biệt severity bằng rubric rõ precedence** | Kiểm độc lập cách xử lý PPE, vật thể và nhiều nguy cơ theo ngành. Giả thuyết là làm rõ ranh giới Level01–02 và Normal–Level03 sẽ giảm nhầm severity. Dữ liệu/shortcut theo CV-A chỉ bổ sung khi audit xác định vấn đề nguồn hoặc support. | Chính: recall Level01, tỷ lệ Level01→Level02 và severe miss theo miền. Guardrail: FPR, FNR, Macro-F1, coverage, độ trễ. E1 giữ cùng dữ liệu/protocol, E2 thay đúng một yếu tố rubric hoặc grammar, E3 stress nhóm hiếm và miền, E4 case trước–sau, E5 khóa prompt/config. | Câu hỏi mới có giá trị ở kiểm chứng mức độ và domain trong bối cảnh công nghiệp. Audit rubric khả thi trước với ít tài nguyên. Thử nghiệm nhân quả cần quyền ảnh, người adjudicate, validation/target phù hợp và ngân sách cho các cấu hình chạy mới sau khi Owner chốt. |
| **2 — CT2, CV-C/D: kiểm tra chéo có chọn lọc dưới ngân sách review** | Xem xét chuyển ca cho người kiểm tra bằng bất đồng và vai trò bất đối xứng của peers. Giả thuyết là chọn theo tín hiệu cải thiện số ca nguy hiểm phát hiện tại cùng K so với chọn ngẫu nhiên hoặc chỉ dùng focal. | Chính: số severe miss bắt được và precision tại cùng K, kèm denominators planned. Guardrail: overload/tồn đọng, ca bỏ sót ngoài K, số cảnh báo giả, độ trễ, chi phí tính mọi peer. E1 cùng ID và K, E2 bỏ từng peer/tín hiệu, E3 worst domain và thiếu tín hiệu, E4 shared failure, E5 tie rule/seed. | Selective review đã có cơ sở học thuật. Giá trị mới phải đến từ kiểm chứng bất đối xứng và chi phí thật của triage công nghiệp. Phân tích label-only trên dữ liệu đã lưu khả thi. Xác nhận cần cohort độc lập, K và tiêu chí tối thiểu chốt trước, nhân lực review và chi phí peer. |
| **3 — CT3, CV-C/D: viewer truy xuất bằng chứng và cờ thiếu provenance** | Dùng case C1/V1 và lỗi chung để đánh giá viewer cho phép thấy nhãn, nguồn, digest, lịch sử sửa và tình trạng thiếu bằng chứng. Giả thuyết là rút ngắn thời gian đối soát mà giữ đúng quyết định review. | Chính: tỷ lệ truy nguồn đúng và thời gian review ở cùng độ chính xác. Guardrail: tỷ lệ chấp nhận sai, lỗi truy xuất, quyền chia sẻ, workload. E1 so phiếu label-only, E2 tắt metadata/cờ, E3 lỗi thiếu/chồng lineage, E4 ca thật và E5 audit trail. | Một màn hình demo có tính mới thấp. Giá trị thực nghiệm nằm ở study đối chứng có reviewer đồng ý. Gói metadata khả thi và ít compute; chi phí chủ yếu ở rights, reviewer, adjudication và rubric. Chỉ hiển thị vùng/lý do khi có bằng chứng đủ quyền. |

Antigravity ưu tiên kiểm tra chéo vì evidence paired và chi phí thử trên
saved labels. Codex ưu tiên CT1 cho câu hỏi nguyên nhân và đề nghị CT2 đo
cùng ngân sách. Khuyến nghị là **CT1 làm trục chính**, CT2 làm nhánh ứng viên
có tiêu chí dừng riêng và CT3 thử usefulness khi đủ quyền. Các phản biện
đồng thuận về số liệu và ranh giới nhân quả. Tín hiệu site/person, calibration
hoặc threshold tuning đều cần chứng từ phù hợp trước khi thử, và các HNLO
hiện có vẫn thuộc scope theo nguồn. Điều kiện tối thiểu cho calibration là
score cùng estimand, validation đủ quyền và kiểm domain shift theo E3.
Không khóa threshold hoặc suy ra xác suất từ nhãn TRAIN đã phơi nhiễm.
[Selective classification](https://proceedings.neurips.cc/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html),
[calibration](https://proceedings.mlr.press/v70/guo17a.html),
[uncertainty dưới dataset shift](https://proceedings.neurips.cc/paper/2019/hash/8558cb408c1d76621371888657d2eb1d-Abstract.html),
[đánh giá faithfulness](https://aclanthology.org/2020.acl-main.386/),
[rubric E1–E5](THESIS_EXECUTION_PLAN_2026.md).

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
M2/R1–R5 lịch sử có [lệnh riêng](../SEMINAR_ANALYSIS.md).

## Kiểm thử và review PR #136

Đối chiếu snapshot chạy toàn repo gồm 19 FAIL và 27 ERROR với main sạch
`c238f841` và HEAD đầu lượt `22d90b4`. Tái sử dụng 12 mục Candidate160 đã
tái hiện ở cả hai checkout và đối chiếu runtime tương ứng giữ nguyên.
Antigravity Hydrogen chạy 14 test ID chọn lọc ở cả hai checkout và xác
nhận 21 mục lỗi/subtest trùng nhau. Coordinator chạy riêng 13 test O5 còn
lại trên cả hai checkout sạch, khớp tên, kiểu kết quả và exception signature
(1 FAIL, 12 ERROR). **Cả 46 mục đã được tái hiện trên main.** Chưa phát hiện
hồi quy thuộc PR. Các lỗi gắn với pin cấu hình, notebook hoặc runtime lịch sử
tiếp tục ở phạm vi riêng. Không rerun discovery toàn repo hoặc đổi pin.

Codex Sol Medium kiểm đúng GitHub HEAD đầu lượt, khớp bảy source blob và
11 SHA256 output M2 với receipt sạch đã lưu. Kiểm lại 132 dòng CSV synthetic
có oracle độc lập cho ba lỗi audit. Thành viên panel R4, nhóm thiếu M224
theo miền/mức ở R3 và ô score Qwen3 hữu hạn đều khớp. Dùng lại bằng chứng
11.032 dòng và 3.204 phép đối chiếu benchmark, với scope tương ứng. Bản sửa
hiện hành bổ sung phân tích và hồ sơ review. Cổng review trực tiếp, re-audit
theo chỉ thị lịch sử, quyền merge riêng và hậu kiểm vẫn áp dụng.
[Chỉ thị audit và merge](https://github.com/tantdna2/SafeShift/pull/136#issuecomment-6412563251).
