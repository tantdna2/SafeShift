# SafeShift: bằng chứng ba mô hình cho RQ1–RQ3

Ngày 23/10/2026; BASE `main@4774f02e84507811243cc587ba877f582614b051`.
**RQ1 được hỗ trợ ở mức mô tả TRAIN; RQ2 chưa được kiểm soát; RQ3 mới có khác biệt theo miền.**
Chưa có bằng chứng khái quát hóa, ngưỡng PA3 an toàn hay hoàn tất nghiên cứu bốn mô hình.
RQ trong báo cáo theo [DEC-PA3-011, vẫn PROPOSED](../../DECISIONS.md#dec-pa3-011--proposed-seminar-internal-hazard-score-direction-2026-10-16), không thay thế quyết định D9R22 đang có hiệu lực.

## Nguồn và mức kiểm chứng

- Ba bản tổng hợp do Research Lead cung cấp được giữ nguyên bytes tại
  [thư mục đầu vào](../evidence/three_model_20261023). [JSON](../evidence/three_model_20261023/SafeShift_three_model_comparison_20261023.json)
  là nguồn các số Qwen3 dưới đây; CSV và Markdown được đối chiếu với JSON.
- **Qwen2.5:** kế thừa [CPU audit Linux chính thức](../pa3_r2_cpu_completion_20261015.md).
  Lần này chỉ đối chiếu summary, `samples.csv` và [confusion.csv](../evidence/three_model_20261023/qwen25_official_confusion.csv)
  có SHA-256 khớp receipt chính thức; tái tính AUROC từ **saved score**, không chạy lại raw audit.
- **InternVL3:** đọc duy nhất CSV báo cáo trong bốn tar của `InterVL3_Output.zip`;
  tái tính AUROC gộp/từng miền từ saved score và ma trận nhầm lẫn, khớp tổng hợp.
  Hai cách tính cho AUROC `0.8861824613751756` và `0.8861824613751758` khác khoảng `2.2e-16`, không phải khác biệt thực nghiệm.
- **Qwen3 — sửa provenance theo [review PR #126](https://github.com/tantdna2/SafeShift/pull/126#issuecomment-6355755837):**
  `qwen3_shard2.json` có SHA-256 `6e72dd81401381de36678163a26d890e492961ad3edf8e43b8e4b0f388089708`,
  thuộc **lượt chạy lại Shard 2 trùng attempt**, không phải lượt V4 đầu tiên, như
  [hồ sơ OOM](../qwen3_s2_oom_20261022.md#source-and-evidence-boundary) đã ghi.
  Ba sidecar V4 S0/S1/S3 + sidecar S2 **duplicate diagnostic** + Recovery224 tạo tổ hợp
  3.763 ID không chồng lặp, support và confusion khớp tổng hợp, nhưng đây **chỉ là kiểm tra nhất quán**.
  Không dùng kết quả đó xác nhận độc lập 717 ảnh S2 gốc hay toàn bộ 3.539 V4-success gốc.
  Archive lượt đầu cần SHA-256 `2dc356fcba9fe2ce5dfc4e3dc9a45286fe5382f574c02d38d7517580e38cd920`;
  chưa tìm thấy trong các vị trí bằng chứng đã kiểm tra. Archive local cùng basename được hash lại là
  `508a2e122ee999da728e8d09c66f5157331e6fe1a40adaa82e2869a30c6e0147`, cũng là lượt chạy lại.
  Vì thiếu saved-score vector gốc đầy đủ, **chưa tái tính độc lập AUROC gộp Qwen3**.
  Mọi số Qwen3 gốc/ghép trong bảng vẫn **dẫn từ tổng hợp/hồ sơ được cung cấp**, không được nâng thành
  member-level audit mới nhờ sidecar chạy lại. Tuyên bố raw replay/integrity vẫn thuộc nguồn cung cấp.

[Receipt CPU và hash đầu vào](../evidence/three_model_20261023/verification_20261023.json)
ghi chính xác phạm vi. Không đọc mới ảnh/annotation, không chạy GPU, không sửa kết quả lịch sử.

**Coverage phải tách cohort:** Qwen2.5 và InternVL3 có 3.763/3.763 saved SUCCESS.
Theo tổng hợp/hồ sơ được cung cấp, Qwen3 V4 gốc chỉ **3.539/3.763 (94,05%)**, còn 1 TECHNICAL_ERROR
và 223 NOT_ATTEMPTED; task này chưa xác nhận độc lập membership/coverage toàn lượt đầu.
Recovery224 được báo cáo có 224/224 SUCCESS, gồm 49 Anomaly/175 Normal, không trùng 3.539 SUCCESS trước đó.
Đối chiếu sidecar duplicate cho kết quả nhất quán nhưng không chứng minh lại tính không chồng lặp với S2 gốc.
Bản ghép đủ 3.763 là **phân tích mô tả xuyên cohort**, không biến V4 thành một baseline chạy hoàn tất.
V4-success AUROC được cung cấp là 0,952793; Recovery là 0,954519; bản ghép là 0,952935.
Không lấy trung bình hai AUROC và không diễn giải sự gần nhau thành bằng chứng recovery không gây selection bias.
[Issue #125, mục CONSUMED](https://github.com/tantdna2/SafeShift/issues/125#issuecomment-6354355448)
vẫn giữ `baseline_pooling_allowed=false`; báo cáo này không đổi trạng thái đó.

## RQ1: điểm xếp hạng và nhãn sinh ra

Chung 3.763 ảnh TRAIN đã được quan sát: **749 Anomaly / 3.014 Normal**;
Level01/02/03/04 = **490/251/8/3.014**. Anomaly là Level01–03, score cao hơn là nguy cơ cao hơn.
Trong các bảng, Q3 là bản ghép mô tả nói trên. Mọi accuracy/FNR/FPR là từ **nhãn sinh ra**, không phải ngưỡng PA3.

| Chỉ số | Qwen2.5 | Qwen3 (ghép) | InternVL3 |
| --- | ---: | ---: | ---: |
| PA3/HNLO AUROC gộp | 0,826656 | 0,952935¹ | 0,886182 |
| AUROC nhãn nhị phân | 0,500000 | 0,901142 | 0,500000 |
| Chênh PA3 − nhãn, cùng cohort ID | +0,326656 | +0,051793 | +0,386182 |
| Accuracy bốn mức | 130/3.763 = 3,45% | 2.932/3.763 = 77,92% | 164/3.763 = 4,36% |
| Accuracy nhị phân | 749/3.763 = 19,90% | 3.282/3.763 = 87,22% | 749/3.763 = 19,90% |
| Balanced accuracy bốn mức | 30,92% | 64,49% | 34,60% |
| Macro-F1 bốn mức | 0,0963 | 0,4532 | 0,1394 |

¹ Dẫn từ tổng hợp, chưa tái tính từ vector điểm gốc đầy đủ trong task này.
AUROC gộp dùng 749 × 3.014 = **2.257.486 cặp**; không phải số quan sát độc lập hay trung bình AUROC shard/miền.

**Kết luận hẹp của RQ1:** cả ba có AUROC PA3 cao hơn đối chứng nhãn nhị phân được cung cấp.
Qwen2.5 và InternVL3 vẫn giữ thông tin xếp hạng khi nhãn nhị phân suy biến thành luôn Anomaly.
Qwen3 hơn Qwen2.5 0,126279 và InternVL3 0,066753 AUROC quan sát được.
Chưa có CI/kiểm định để gọi các chênh lệch là có ý nghĩa thống kê. AUROC của hard label bằng
balanced accuracy nhị phân với tie credit 1/2; đối chứng này mất nhiều thông tin so với score liên tục.
Do đó chưa chứng minh PA3 vượt mọi đối chứng từ generation, hay thay đổi ngưỡng sẽ cải thiện quyết định an toàn.

Ma trận đầy đủ: **hàng = nhãn thật**, mỗi vector theo thứ tự dự đoán **[L01, L02, L03, L04]**.

| Nhãn thật (N) | Qwen2.5 | Qwen3 | InternVL3 |
| --- | --- | --- | --- |
| Level01 (490) | [66, 158, 266, 0] | [163, 303, 10, 14] | [60, 201, 229, 0] |
| Level02 (251) | [1, 57, 193, 0] | [2, 193, 32, 24] | [1, 97, 153, 0] |
| Level03 (8) | [0, 1, 7, 0] | [0, 3, 5, 0] | [0, 1, 7, 0] |
| Level04 (3.014) | [18, 286, 2.710, 0] | [104, 154, 185, 2.571] | [20, 15, 2.979, 0] |

| Nhãn | Qwen2.5 recall / precision | Qwen3 recall / precision | InternVL3 recall / precision |
| --- | ---: | ---: | ---: |
| Level01 | 13,47% / 77,65% | 33,27% / 60,59% | 12,24% / 74,07% |
| Level02 | 22,71% / 11,35% | 76,89% / 29,56% | 38,65% / 30,89% |
| Level03 | 87,50% / 0,22% | 62,50% / 2,16% | 87,50% / 0,21% |
| Level04 | 0% / N/A | 85,30% / 98,54% | 0% / N/A |

N/A precision vì không có dự đoán Level04. Recall Level03 chỉ có 8 ảnh; một ảnh đổi 12,5 điểm phần trăm.
Recall 87,5% của Qwen2.5/InternVL3 đi kèm precision dưới 0,23%, do dự đoán Level03 tràn sang lớp khác.
Chưa có AUROC PA3 riêng Level01-vs-Normal/Level02-vs-Normal/Level03-vs-Normal đủ ba mô hình;
không thay thế chúng bằng recall bốn mức.

## Lỗi nghiêm trọng và mất cân bằng nhãn

| Quyết định nhị phân | TP / FN / FP / TN | Recall Anomaly / Normal | Precision Anomaly / Normal | F1 Anomaly / Normal |
| --- | --- | --- | --- | --- |
| Qwen2.5 và InternVL3 (mỗi mô hình) | 749 / 0 / 3.014 / 0 | 100% / 0% | 19,90% / N/A | 0,3320 / 0 |
| Qwen3 | 711 / 38 / 443 / 2.571 | 94,93% / 85,30% | 61,61% / 98,54% | 0,7472 / 0,9145 |
| Luôn Level04 | 0 / 749 / 0 / 3.014 | 0% / 100% | N/A / 80,10% | 0 / 0,8895 |

Luôn Level04 đạt **80,10% accuracy cả bốn mức và nhị phân**, AUROC/BA nhị phân 0,5,
BA bốn mức 25% và Macro-F1 bốn mức 0,2224. Qwen3 thấp hơn đối chứng này về accuracy bốn mức
2,18 điểm phần trăm nhưng cao hơn 7,12 điểm về accuracy nhị phân và có recall Anomaly thực tế.
Luôn Anomaly cho đúng endpoint nhị phân của Qwen2.5/InternVL3: BA 50%, FPR 100%; FN=0 không đủ chứng minh an toàn.
Prevalence Anomaly 19,90% cần được giữ khi diễn giải precision/PR; chưa có AUPRC đủ ba mô hình.
Mất cân bằng không tự làm AUROC tăng, nhưng làm accuracy dễ gây hiểu nhầm và giảm bằng chứng cho lớp hiếm.

- **Qwen3:** 14/490 Level01 → Level04 = **2,86%**, khác với lỗi sai mức Level01
  327/490 = 66,73%; 313 ảnh còn lại bị hạ xuống Level02/03. Trong 14 lỗi nguy hiểm,
  **12 ở oil_chemical**, 1 coal_conveyor, 1 metallurgy; riêng oil_chemical là 12/239 = 5,02%.
  Level02 → Level04 là 24/251 = 9,56%, gồm **19 ảnh ở power**. Tổng FN là 38/749 = 5,07%.
- **Qwen3 báo động giả:** 443/3.014 = **14,70%**, gồm 104 → L01, 154 → L02, 185 → L03.
  Trong 1.154 cảnh báo Anomaly, 443 (38,39%) là Normal. Không được suy mọi lỗi này là hallucination:
  task chưa xem ảnh hay tái thẩm định nhãn.
- **Qwen2.5/InternVL3:** không có L01 → L04 vì không sinh L04; nhưng lần lượt
  424/490 và 430/490 Level01 bị hạ xuống L02/03. Tất cả 3.014 Normal đều bị cảnh báo;
  lần lượt 2.710 và 2.979 bị gọi L03. Cần kiểm tra riêng lỗi semantic/prompt/decision-context
  bằng bằng chứng đã lưu, chưa thể quy nguyên nhân cho ánh xạ token hoặc năng lực nhận thức.

## RQ3: khác biệt miền, chưa kiểm tra chuyển miền

PA3 / nhãn là hai AUROC; FNR/FPR bên phải chỉ thuộc **nhãn Qwen3**.
Qwen2.5 và InternVL3 có AUROC nhãn 0,5, FNR=0%, FPR=100% ở cả năm miền.

| Miền | Anomaly / Normal | Q2.5 PA3 | Q3 PA3 / nhãn | IVL3 PA3 | Q3 FN/N Anomaly | Q3 FP/N Normal |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| coal_conveyor | 172 / 650 | 0,8953 | 0,9319 / 0,8932 | **0,9893** | 1/172 = 0,58% | 135/650 = 20,77% |
| metallurgy | 9 / 534 | 0,8404 | 0,8752 / 0,8330 | **0,9415** | 1/9 = 11,11% | 119/534 = 22,28% |
| oil_chemical | 287 / 491 | 0,7549 | **0,9747** / 0,9352 | 0,9568 | 15/287 = 5,23% | 38/491 = 7,74% |
| power | 81 / 575 | 0,8721 | **0,9854** / 0,8688 | 0,7064 | 19/81 = 23,46% | 16/575 = 2,78% |
| tunnel | 200 / 764 | 0,8635 | **0,9836** / 0,9066 | 0,7273 | 2/200 = 1,00% | 135/764 = 17,67% |

Không có mô hình đứng đầu mọi miền. InternVL3 hơn Qwen2.5 ở AUROC gộp nhưng kém tại power
và tunnel; thứ hạng gộp che khuất suy giảm cục bộ. Qwen3 power AUROC rất cao nhưng nhãn bỏ sót
23,46% Anomaly, chủ yếu L02. Chưa có PA3 threshold để nói score sẽ tạo cùng các tỷ lệ đó.
Metallurgy chỉ có 9 Anomaly, không có L02; oil_chemical/power không có L03 TRAIN.
Cần giữ mẫu số và khác biệt thành phần mức độ khi so miền. AUROC phụ thuộc phân phối score có điều kiện,
nên khác biệt theo miền không tự xác định tác động domain, nguồn, platform hay mức nguy hiểm.

Để kiểm tra chuyển miền: cần phê duyệt source/development và target độc lập theo nguồn/chuỗi,
kiểm soát duplicate/exposure, chọn ngưỡng **chỉ trên development** theo mục tiêu đã chốt,
rồi giữ nguyên score direction/threshold/preprocessing khi đo FNR/FPR, coverage và uncertainty ở target.
Không chọn ngưỡng tối ưu trên TRAIN hay riêng mỗi target. [Audit W1](../research_feasibility_audit.md)
đã ghi official TEST metallurgy không có Anomaly; không thể ước lượng AUROC/FNR ở miền đó bằng split hiện hữu.
Task này không mở TEST, tạo split hay thực hiện thiết kế tương lai.

## RQ2: metadata có thật và đối chứng cần phê duyệt

Nguồn: [schema](../dataset_schema.md), [audit metadata](../research_feasibility_audit.md#3-domain-metadata-inventory-kiểm-kê-siêu-dữ-liệu-miền-và-nguồn),
[distribution](../distribution_imbalance_audit.md), và census lại **metadata TRAIN từ audit cũ** trong receipt.

| Yếu tố | Bằng chứng hiện có | Phân tích đề xuất, chưa thực hiện |
| --- | --- | --- |
| Người | LabelMe polygon có raw label `Person`; 1.244 **polygon instances trên cả 5.013 ảnh**, không phải số ảnh có người. Chưa có biến human-presence đã duyệt/join với kết quả. | Duyệt định nghĩa proxy “có ≥1 Person polygon”, kiểm tra coverage/missingness và annotation absence; không gọi phần còn lại là chắc chắn không có người. So score, FNR/FPR trong từng lớp thật × miền × proxy. |
| Thiết bị | Có object labels thiết bị; `robot_platform` suy từ tên thư mục là nền tảng robot thu ảnh, không phải equipment/site/camera identity. | Chốt taxonomy thiết bị từ labels hiện có trước khi lập strata; không tạo equipment ID hoặc hazard rationale từ tên vật thể. |
| Miền/platform | TRAIN: rail/wheeled = coal 822/0; metallurgy 47/496; oil 71/707; power 85/571; tunnel 944/20. Folder/text domain có 36 xung đột toàn dataset, **32 thuộc TRAIN**. | So trong miền và vùng platform có overlap; đối chứng metadata-only/điều chỉnh theo miền × platform × nhãn. Coal không có đối chứng wheeled, nên không thể tách độc lập hai tác động ở miền này. Sensitivity giữ nguyên nhãn/miền chính, gắn cờ xung đột. |
| Nguồn/chuỗi | JSON `imagePath`, 2.424 point IDs TRAIN; regex family keys gồm 12 ở Anomaly và 1.710 ở Normal. Keys là heuristic tên file, **không phải video/site độc lập**. Không có official site/video/camera map. | Join source/duplicate graph với score; báo phân bố mức nhãn, domain, platform và lỗi trong nhóm. Source family toàn một lớp không cho phép AUROC nội nhóm; không diễn giải predictor “nguồn” như phát hiện nguy cơ. |

Các đề xuất trên là phân tích liên hệ/sensitivity, chưa xác định nhân quả.
Không suy người xuất hiện từ prefix `hand`/`phone`, không xem polygon thiết bị là vùng giải thích an toàn.
RQ2 hiện **chưa có kết quả sau kiểm soát**; metadata chỉ xác lập các confounder có thể kiểm tra và vùng thiếu overlap.

## Khoảng tin cậy và hạn chế khoa học

**Chưa tính CI phù hợp phụ thuộc nguồn cho AUROC, chênh AUROC, recall hoặc FPR.**
Có per-image report Qwen2.5/InternVL3 và ID Qwen3, nhưng thiếu vector điểm Qwen3 S2 gốc;
point ID và regex family chưa chứng minh đủ để gom mọi chuỗi/góc máy phụ thuộc.
Không coi 3.763 ảnh hay 2.257.486 cặp là độc lập, không đưa Wilson/i.i.d. bootstrap làm CI theo nguồn.
Sau khi có mapping được review, dùng cùng cluster draws cho các model/method trên giao ID hợp lệ,
giữ toàn cluster/duplicate component, kiểm tra số cluster và support hai lớp ở từng miền;
báo tỷ lệ resample đơn lớp/undefined, seed và số lần lặp. Point-only bootstrap nếu làm phải ghi là sensitivity
với giả định hẹp, chưa xử lý mọi phụ thuộc nguồn.

TRAIN đã phơi nhiễm; lịch sử duplicate xuyên split, label/domain conflict và ít Level03/metallurgy giới hạn suy luận.
Qwen3 có OOM/recovery và duplicate exposure lịch sử; kết quả 224 thành công không chứng minh nguyên nhân OOM.
Prompt C1 cùng ý định nhưng native wrappers, tokenizer/revision, preprocessing, precision/runtime không đồng nhất;
Qwen2.5 R2 **clamp kích thước không gian trước vision merger**, kích hoạt 24/3.763 ảnh,
không phải giới hạn số ảnh/khung hình như bản tổng hợp ghi. Qwen3 T4×2, hai model kia T4×1;
không quy mọi chênh lệch cho kiến trúc, không so raw-score scale hay tốc độ như một thí nghiệm kiểm soát.
Thiếu Shard 1 outer receipt Qwen2.5 và giới hạn Windows 1-ULP được giữ nguyên theo audit chính thức.

## Những gì đã chứng minh được

Trong phạm vi kiểm chứng nêu đầu báo cáo: tổng hợp nhất quán về số học; PA3 xếp hạng tốt hơn hard-label endpoint
trên các cohort được báo cáo; nhãn suy biến ở hai mô hình; Qwen3 còn lỗi bỏ sót và báo động giả rõ ràng.
Ma trận, mẫu số và khác biệt miền hỗ trợ các kết luận mô tả này, không nâng thành raw-audit PASS mới cho ba model.

## Những gì chưa chứng minh được

Chưa có ưu thế thống kê/độc lập của PA3, causal hazard validity sau kiểm soát người/nguồn,
calibration, ngưỡng vận hành, FNR/FPR của PA3, khả năng chuyển miền hoặc hoàn tất Seminar bốn mô hình.
“RQ grounding” trong bản tổng hợp không phải RQ2/RQ3 theo DEC-PA3-011; task này không đo grounding.

## Các phát hiện đáng đưa vào Seminar

1. **Score và nhãn tách rời:** Qwen2.5/InternVL3 AUROC 0,8267/0,8862 nhưng cảnh báo cả 3.014 Normal.
2. **AUROC tốt vẫn còn lỗi nguy hiểm:** Qwen3 0,9529 nhưng 14 L01 → L04, tập trung oil_chemical;
   power bỏ sót 19/81 Anomaly dù AUROC 0,9854.
3. **Accuracy không đủ:** luôn Normal đạt 80,10%; cần confusion, precision/recall và BA cạnh accuracy 77,92% của Qwen3.
4. **Không có người thắng mọi miền:** InternVL3 dẫn coal/metallurgy, Qwen3 dẫn ba miền còn lại;
   chưa gọi đây là bằng chứng domain shift.

## Phạm vi Moondream2 và việc tiếp theo theo ưu tiên

[README](../../README.md), [ROADMAP](../../ROADMAP.md), [DEC-PA3-011](../../DECISIONS.md#dec-pa3-011--proposed-seminar-internal-hazard-score-direction-2026-10-16)
và [yêu cầu bốn mô hình](../pa3_four_model_seminar_scope.md) vẫn bắt buộc Moondream2.
Không xóa mô hình vì bảng này chỉ có ba model. [T1 ngày 17/10](../hnlo_t1_cpu_results_20261017.md)
đã PASS 28/28 cho Starmie; [smoke/vision bridge](../w2_moondream_postfix_result_external_gate_prep.md)
đã có bằng chứng interface T4. Vì vậy “còn BF16 không tương thích T4” trong form review local
không đủ làm blocker duy nhất hiện tại. Còn thiếu real raw-logit hook/decision alignment/state-preservation validation
và kết quả TRAIN tương thích đã audit; [capture PREP](../hnlo_raw_logit_capture_prep_20261017.md) chỉ có bằng chứng CPU giả lập.

1. **Khép provenance hiện có:** tìm archive Qwen3 S2 đầu tiên/CSV đúng hash, giữ riêng rerun và Recovery;
   kiểm tra raw/score theo đúng hợp đồng từng model, tái tính Qwen3 gộp và cùng 3.539 V4-success IDs cho cả ba.
   Giữ coverage gốc; không lấy recovery thay lịch sử lỗi.
2. **Lead chốt protocol và Moondream2:** giữ yêu cầu bốn model; review đường native capture và validation còn thiếu.
   Nếu chưa khả thi, trình lựa chọn giữ model với PA3 N/A + generated baseline, hoặc hoãn/thu hẹp phạm vi
   qua quyết định append-only được phê duyệt. Không tự áp dụng phương án nào trong PR này.
3. **Kiểm tra lỗi có mục tiêu:** ưu tiên 14 L01 → L04, 24 L02 → L04, 443 Normal bị cảnh báo của Qwen3;
   rồi lỗi L04 → L03 và hạ mức L01 của hai model còn lại. Join source/point/platform và raw decision context,
   review ảnh/annotation chỉ sau quyền phù hợp; phân biệt annotation conflict, prompt/parse và semantic error.
4. **RQ2 và CI:** duyệt human/equipment proxies, hoàn thiện source/duplicate clusters, kiểm tra overlap;
   phân tích điều kiện và paired cluster uncertainty. Các ô không đủ hai lớp phải N/A.
5. **RQ3 độc lập:** duyệt cohort development/target và quy tắc ngưỡng trước khi dùng holdout/TEST;
   giữ nguyên ngưỡng khi chuyển miền, báo FNR/FPR/coverage, không sửa split/nhãn hiện hữu.

## Tái lập CPU và kiểm tra PR

Từ repository root, Python 3.11.9; kiểm tra aggregate chỉ dùng standard library, export AUROC tái dùng
`safeshift.ls1.evaluate.auc` nguyên trạng. Không ngẫu nhiên, seed=null. Đầu ra mới nằm trong `data/processed/`:

```powershell
python -m scripts.analyze_three_model_summaries --output data/processed/three_model_analysis_20261023/recheck.json
python -m unittest tests.test_three_model_summaries tests.test_ls1.EvaluationTests.test_auc_ranking_survives_probability_saturation tests.test_ls1.EvaluationTests.test_auc_ties_and_absence -v
git diff --check
```

Để kiểm tra export bổ sung, stage vào `data/processed/three_model_analysis_20261023/inputs/`:
`qwen25_samples.csv` đúng receipt chính thức, `InterVL3_Output.zip`, ba V4 result S0/S1/S3 đổi tên
`qwen3_shard0.json`, `qwen3_shard1.json`, `qwen3_shard3.json`; **duplicate S2** có đúng hash `6e72dd…`
giữ tên `qwen3_shard2.json`, recovery result đổi tên `recovery.json`.
Script phân vai S2 bằng hash bytes, từ chối nhận duplicate làm original-V4 và từ chối digest chưa có provenance.
Receipt tách `qwen3_original_v4` (supplied, member-level validation=false) khỏi
`qwen3_available_sidecars_consistency` và `qwen3_s2_diagnostic`; tên file hay các count bằng nhau không xác nhận lượt đầu.
Copy audit metadata cũ `data/manifests/duplicate_leakage_audit.json` sang
`data/processed/three_model_analysis_20261023/duplicate_metadata_audit.json`; không tạo lại từ dataset.
Thêm `--local-evidence data/processed/three_model_analysis_20261023/inputs --metadata-audit data/processed/three_model_analysis_20261023/duplicate_metadata_audit.json`
và dùng output filename mới. Receipt versioned lưu hash các inputs và script; không chứa ID mẫu, raw outputs hay đường dẫn máy cá nhân.

Kết quả F1: 13/13 CPU tests PASS. Sau sửa provenance: aggregate arithmetic PASS;
saved-report/duplicate-diagnostic consistency PASS; **16/16 CPU tests PASS**
(14 synthetic, gồm ba kiểm thử provenance mới, + 2 AUROC regression hiện có).
Lần thử đầu với `python -P` thiếu repository trên import path, chưa chạy test; lệnh module ở trên đã chạy thành công.
Không chạy toàn repo suite, raw-logit auditor, inference/GPU hoặc TEST evaluation vì không đổi production/runtime/protocol.
Kiểm tra whitespace, liên kết local, hash các bản sao đầu vào và phạm vi diff được thực hiện trước Draft PR.
