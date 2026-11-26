# SafeShift — Benchmark First trên Full-TRAIN

## Trạng thái

`safeshift-full-train-benchmark-v1` so sánh ba sản phẩm nhãn đã được Owner
chọn trên cùng cohort TRAIN đã phơi nhiễm. Qwen3 là phần đã tái tính từ dữ liệu
thật trong phạm vi quyết định riêng. Với InternVL và MiniCPM, bảng dưới dùng
độ phủ/phân bố đã ghi và các cận điều kiện. Đánh giá ghép GT của hai sản phẩm
này, benchmark ba bên, ca ảnh cụ thể và kết luận nguyên nhân thị giác đang chờ
bằng chứng quyền/truy xuất. Hệ thống có nguồn, cấu hình và xử lý đầu ra khác
nhau. [Quyết định và phạm vi](DECISIONS.md#dec-20261127-owner-benchmark-first),
[bản ghi Owner](https://github.com/tantdna2/SafeShift/pull/136#issuecomment-7199181963).

| Sản phẩm | Hợp lệ / planned | Dự đoán Level01 / 02 / 03 / 04 | Accuracy | Macro-F1 | Balanced Accuracy |
| --- | ---: | --- | ---: | ---: | ---: |
| Qwen3-VL Composite V1 | 3.763/3.763 | 269 / 653 / 232 / 2.609 | 77,92% | 45,32% | 64,49% |
| InternVL3.5 Grammar V2 | 3.763/3.763 | 245 / 598 / 1.418 / 1.502 | Chờ ghép GT | Chờ ghép GT | Chờ ghép GT |
| MiniCPM-V-4 Normalization V1 | 3.763/3.763 | 145 / 206 / 286 / 3.126 | Chờ ghép GT | Chờ ghép GT | Chờ ghép GT |
| MiniCPM strict C1, sensitivity | 3.558/3.763 | 145 / 206 / 286 / 2.921 và 205 INVALID | Chờ ghép GT | Chờ ghép GT | Chờ ghép GT |

[Qwen3, quyết định và niêm phong](QWEN3_FULL_TRAIN_COMPOSITE_V1.md),
[InternVL, bằng chứng thực thi](../PROJECT_STATE.md#hiện-hành--internvl35-full-train-đã-hoàn-thành--19112026),
[MiniCPM, C1 và V1](MINICPM_FULLTRAIN_NORMALIZATION_V1.md).

## Qwen3-VL Composite V1

Đã tái tính từ sản phẩm niêm phong có manifest SHA256
`7e7793073eb639a2d0bd22e84c11cd773be7fdb86e7e1f5f59e3baf0dd0c98de`, trên mã
main `c238f841`, Python 3.11.9. Bộ kiểm số học riêng xác nhận 980 đối chiếu
trên 15 strata, 3.763 dòng. Số liệu đếm mọi ID. Mỗi hàng trong confusion là GT,
mỗi cột là nhãn dự đoán. Tỷ lệ tính trên 3.763 bản ghi, gồm 3.719 hash ảnh phân
biệt. [Hồ sơ và oracle tái lập](QWEN3_FULL_TRAIN_COMPOSITE_V1.md).

| GT | Level01 | Level02 | Level03 | Level04 | INVALID | Support | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Level01 | 163 | 303 | 10 | 14 | 0 | 490 | 60,59% | 33,27% | 42,95% |
| Level02 | 2 | 193 | 32 | 24 | 0 | 251 | 29,56% | 76,89% | 42,70% |
| Level03 | 0 | 3 | 5 | 0 | 0 | 8 | 2,16% | 62,50% | 4,17% |
| Level04 | 104 | 154 | 185 | 2.571 | 0 | 3.014 | 98,54% | 85,30% | 91,45% |

Hazard là Level01–03, Normal là Level04. TP 711, FN 38, FP 443, TN 2.571.
Hazard Recall **94,93%** (711/749), Hazard Precision **61,61%** (711/1.154),
Binary F1 **74,72%** (1.422/1.903), FNR **5,07%** (38/749), FPR **14,70%**
(443/3.014), severe miss **2,86%** (14/490, Level01 → Level04). Normal chiếm
80,10% GT, nên phương án luôn đoán Normal có accuracy cao hơn accuracy bốn
lớp của Qwen3 và Hazard Recall bằng 0. Accuracy riêng lẻ dễ che mức độ an toàn.

| Folder domain | N | Accuracy | Macro-F1 | Bal. Acc. | Hazard Recall | FNR | FPR | Severe miss |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| coal_conveyor | 822 | 73,48% | 45,13% | 75,42% | 171/172 | 1/172 | 135/650 | 1/109 |
| metallurgy | 543 | 76,43% | 29,12% | 25,91% | 8/9 | 1/9 | 119/534 | 1/8 |
| oil_chemical | 778 | 71,72% | 54,40% | 54,83% | 272/287 | 15/287 | 38/491 | 12/239 |
| power | 656 | 93,14% | 81,45% | 76,47% | 62/81 | 19/81 | 16/575 | 0/31 |
| tunnel | 964 | 77,18% | 48,78% | 66,98% | 198/200 | 2/200 | 135/764 | 0/103 |

- **Down-grading mức nặng.** 303/490 Level01 thành Level02, nhầm lẫn lớn nhất
  bên trong nhóm Hazard. Đây là pattern của nhãn đầu ra. Cần đối chiếu rubric,
  các lớp giáp ranh và ảnh được cấp quyền để phân biệt mapping, ngữ cảnh thị
  giác và hạn chế của prompt.
- **False-safe.** Power có FNR cao nhất và chứa một nửa số Hazard → Normal
  (19/38) dù accuracy cao nhất. Oil/chemical có 12/14 severe misses. Metallurgy
  có Macro-F1 và Balanced Accuracy thấp nhất, FPR cao nhất và tỷ lệ severe
  miss cao nhất trên chỉ tám ca Level01. Ưu tiên đếm ca và báo support cạnh
  tỷ lệ. Folder domain dùng để phân tầng và nguồn độc lập còn chưa xác minh.
- **Báo động giả và lớp hiếm.** 443 Normal bị cảnh báo, gồm 185 dự đoán Level03.
  Chỉ 5/232 dự đoán Level03 đúng. GT Level03 có tám ca. Phân bố gợi ý kiểm tra
  rubric và mô hình dùng dấu hiệu nền/thiết bị làm shortcut; ảnh, bằng chứng
  vùng và review có đối chứng chưa được kiểm tra, nên nguyên nhân còn mở.

## InternVL và MiniCPM từ bằng chứng hiện có

- **InternVL3.5** dự đoán Hazard 2.261/3.763 và riêng Level03 1.418/3.763.
  Nếu đủ 3.763 ID khớp chính xác GT tổng hợp ở trên, phải có ít nhất 1.512
  false alarm (FPR ≥50,17%, Hazard Precision ≤33,13%) và precision Level03
  ≤8/1.418 = 0,56%. Các cận lấy trường hợp thuận lợi nhất về phần giao giữa
  hai tập. Độ lệch phân bố là quan sát. Nguyên nhân như ranking token bị grammar
  khuếch đại, nhầm rubric hoặc shortcut còn cần kiểm trên bản lưu có quyền.
- **MiniCPM V1** dự đoán Hazard 637/3.763, Normal 3.126/3.763. Với cùng điều kiện
  khớp cohort, phải có ít nhất 112 false-safe (FNR ≥14,95%, Hazard Recall
  ≤85,05%) và recall Level01 ≤145/490 = 29,59%. Nguồn đã xác minh một lỗi
  định dạng: 205 object điền cụm mô tả Normal vào `safety_level`, khiến C1
  trả INVALID theo hợp đồng. V1 ánh xạ chính xác sang Level04 và giữ mọi
  prediction canonical gốc. Cần GT để biết bao nhiêu conversion thành TN
  hoặc false-safe, bao nhiêu là Level01. Tăng valid rate từ 94,55% lên 100%
  chỉ xác nhận độ phủ của bản dẫn xuất.
  Tăng đúng bao nhiêu ca Normal thực trong nhóm chuyển đổi sẽ làm Accuracy
  tăng bấy nhiêu/3.763. Mỗi ca Hazard trong nhóm thêm một false-safe, trong
  khi TP, FP, Hazard Recall và FPR giữ nguyên. Việc tra GT từng ID thực hiện
  sau khi khóa nhóm conversion.
- Cận trên/cận dưới dùng đúng marginal, có điều kiện trên cohort chung.
  Confusion matrix, domain, severe miss và quan hệ từng ID của hai sản phẩm
  vẫn chờ so khớp trực tiếp. Chưa thể kết luận ensemble sẽ giúp. Mọi kết quả
  cặp cần đủ ID và phân biệt disagreement với phần bù lỗi thực tế.

## Điểm và bất định

AUROC mô tả của Qwen3 V4 gốc là 0,952793 trên 3.539 SUCCESS
(700 Hazard/2.839 Normal), Recovery 0,954519 trên 224 (49/175). AUROC và AUPRC
pooled, FNR@fixed FPR, calibration và risk–coverage của Composite là **N/A**
vì chưa chứng minh tương thích thang điểm, token và quyết định giữa nguồn.
InternVL và MiniCPM **N/A** với các endpoint điểm chung vì chưa có HNLO/điểm
hợp lệ đúng hợp đồng. Không dùng nhãn dự đoán làm xác suất hoặc fitting trên
TRAIN. Các domain dùng support đã đo. CI suy rộng giữa nguồn là **N/A** vì
đây là toàn cohort cố định, ảnh trùng và cluster nguồn chưa xác minh. Nếu có
nguồn độc lập và quyền, chốt đơn vị cluster/precision trước khi đánh giá.
[Giới hạn điểm và nguồn](QWEN3_FULL_TRAIN_COMPOSITE_V1.md#separate-hnlo-compatibility-gate).

## Từ vấn đề đến câu hỏi cải tiến

| Ưu tiên điều tra | Bằng chứng và kiểm tra tiếp | Ứng viên, định hướng | Metric chính và guardrail cần chốt |
| --- | --- | --- | --- |
| 1. False-safe, hạ severity và đánh đổi false alarm | Qwen3: Power 19/81 FN, oil/chemical 12/239 severe, 303 Level01 → Level02. Kiểm case theo rubric, domain, ảnh trùng và source. Đối chiếu InternVL/MiniCPM trên ID trước so ngang. | CV-B/D, CT1. So baseline theo lớp/miền. Nếu rubric/mapping xác nhận, cân nhắc grounding/prompt hoặc can thiệp vào quyết định có đối chứng. | Severe miss/FNR và recall Level01; guardrail FPR, valid rate, Macro-F1, số ca review, chi phí. |
| 2. Phân bố dự đoán lệch và bất đồng | InternVL nhiều Hazard/Level03, MiniCPM nhiều Normal. Xác minh cùng đúng, cùng sai và lỗi riêng, đặc biệt ca nặng. Kiểm ngẫu nhiên ca đúng cùng strata để tránh chỉ chọn ca minh họa lỗi. | CV-B/C, CT2. Domain-balanced sampling hoặc ensemble chỉ đáng thử nếu có bằng chứng theo miền hoặc bổ trợ cặp. Đồng thời khảo sát CV-A nếu truy nguyên cho thấy vấn đề nằm ở dữ liệu/nguồn. | Worst-domain và paired severe misses; guardrail precision, false alarm, chi phí mỗi ảnh và budget review. |
| 3. Độ tin cậy | Qwen3 nguồn có score riêng, hai hệ còn lại thiếu score hợp lệ. | CV-B/C, CT2. Calibration hoặc threshold tuning khi có score đúng nghĩa, protocol tách validation và quyền tương ứng. So đối chứng cùng dữ liệu; đóng góp nằm ở bằng chứng chênh lệch theo domain và an toàn. | Brier/reliability, AUPRC hoặc FNR tại FPR khóa theo estimand; kiểm coverage, severe miss, phân bố miền và chi phí. |
| 4. Truy xuất chứng cứ | 205 MiniCPM conversion có lineage và cơ chế định dạng đã kiểm. Qwen3 có lỗi nguy hiểm cần case review; chưa có căn cứ gán vùng bằng chứng. | CV-C/D, CT3. Cân nhắc evidence audit viewer nếu có quyền giữ chứng cứ, rubric và đánh giá người dùng. | Tỷ lệ truy đúng provenance, độ chính xác và thời gian review. Guardrail quyền dữ liệu, độ đầy đủ, lỗi truy xuất và workload. |

Các thứ tự trên ưu tiên **điều tra**. Việc chốt phương pháp, tính mới và
ngưỡng cần phản biện sau khi đủ benchmark. Có thể dùng E1 để khóa baseline,
E2 đối chứng phương pháp đã chốt, E3 ablation, E4 đánh giá độc lập theo quyền
và E5 đo usefulness nếu có rubric/reviewer. Tuning/grounding có thể cần model
calls và thí nghiệm mới, ensemble có thể tăng chi phí thu dự đoán nhiều lần,
viewer cần bằng chứng và nhân lực review. Gói CPU hiện tại chỉ phân tích kết
quả đã lưu. [Kế hoạch E1–E5](THESIS_EXECUTION_PLAN_2026.md).

Temperature scaling và selective classification đã có đối chứng trong
nghiên cứu trước. Muốn đánh giá một hướng tương tự, SafeShift cần score cùng
định nghĩa, dữ liệu validation đủ quyền và một đơn vị chi phí review khóa
trước. Kết quả nghiên cứu về dataset shift củng cố lý do đo calibration và
false-safe theo domain. Tính mới nếu có nằm ở thiết kế đối chứng và bằng chứng
an toàn công nghiệp theo miền. Với viewer, đo riêng truy xuất lineage và khả
năng giải thích trung thực, vì một mô tả hợp lý chưa xác nhận vùng ảnh thực
sự chi phối dự đoán. [Guo và cộng sự](https://proceedings.mlr.press/v70/guo17a.html),
[Geifman và El-Yaniv](https://proceedings.neurips.cc/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html),
[Ovadia và cộng sự](https://proceedings.neurips.cc/paper/2019/hash/8558cb408c1d76621371888657d2eb1d-Abstract.html),
[Jacovi và Goldberg](https://aclanthology.org/2020.acl-main.386/).

Các tệp tổng hợp Qwen3 được lưu ở
`data/processed/seminar/qwen3-benchmark-first/` gồm bảng JSON/CSV và heatmap
`qwen3_confusion.html`. Oracle ghi 980 phép kiểm trong
`data/processed/seminar/qwen3-benchmark-first-oracle.json`.

## Hợp đồng và tái lập CPU

Chạy từ root với Python 3.11+. Với Qwen3, dùng reader đã merge và manifest
SHA256 ở trên để tái tính. Lệnh sau chạy trên bản sản phẩm đã lưu có quyền
và không cần tải dataset, ảnh hay archive raw.

```console
python -B -m scripts.build_qwen3_composite --output data/processed/qwen3-composite-v1/release-v1 --verify-manifest-sha256 7e7793073eb639a2d0bd22e84c11cd773be7fdb86e7e1f5f59e3baf0dd0c98de
python -B -m scripts.check_qwen3_composite_metrics --product-dir data/processed/qwen3-composite-v1/release-v1 --output data/processed/seminar/qwen3-oracle.json
python -B -m unittest discover -s tests -p test_full_train_benchmark.py -v
```

Sau khi có thẩm quyền và review, custodian cung cấp bốn JSON tư nhân có
SHA256/kích thước độc lập, cùng ref quyền đánh giá TRAIN, chứng từ nguồn,
review nguồn và source seal chính xác của InternVL. Cấu hình được version
control ghim các chứng từ và member. Giá trị `release: null` hiện hành làm
CLI trả mã 2 trước khi mở bất kỳ projection. Chỉ tích hợp bằng chứng đã có
thẩm quyền theo quy trình hiện hành. Final Admission và M4 lịch sử có phạm
vi riêng. Công cụ không suy quyền từ các tệp tìm thấy trên máy.

- `cohort.json`, schema `safeshift-full-train-benchmark-v1-cohort`, có `samples`
  gồm đúng thứ tự cohort gốc, mỗi dòng có `sample_id`, `split=TRAIN`,
  `image_sha256`, `true_level`, `domain`. Tập ID và các hash phải từ master
  được custodian xác minh. Hash so khớp metadata đã niêm phong. CLI không đọc ảnh.
- `qwen3.json`, `internvl35.json`, `minicpm.json` có schema
  `safeshift-full-train-benchmark-v1-product`, `product_id`,
  `source_seal_sha256`, `sources` và `samples`. Mỗi dòng có cùng năm trường
  identity, `source_id`, `status` và `generated_label`. Nguồn tham chiếu có
  `run_id`, `attempt_id`, `model_id`, `revision`, `config_sha256`,
  `artifact_sha256`. MiniCPM giữ thêm `original_status`, `original_label`
  (JSON null khi INVALID). Custodian đối chiếu projection với bản gốc đã niêm
  phong theo từng run/attempt và giữ mapping bên ngoài Git. GT của cohort chỉ
  thêm sau khi chọn và khóa nguồn theo lineage. CLI từ chối mismatch niêm
  phong, split, ID, hash, GT, domain, lineage và nhãn.
- `benchmark.json` chứa metric overall/domain, 4×5, binary, worst domain,
  paired outcomes, disagreement trên giao nhãn hợp lệ và đúng/sai trên planned.
  Strict C1 giữ INVALID trong mẫu số, tách U_A/U_N khỏi FN/FP. Macro tính trên
  các lớp có GT support, báo danh sách lớp và `null` khi mẫu số bằng 0.
  Giữ GT gốc cho từng ID kể cả khi hai ảnh trùng hash có GT khác nhau và đếm
  các nhóm xung đột để kiểm toán riêng.
  `metrics.csv`, `confusion.html`, `receipt.json` cung cấp bảng số, heatmap
  và toàn vẹn đầu vào/đầu ra. Folder output phải mới, dưới `data/processed/`.
  Dữ liệu, GT từng ID, raw và artefact riêng tư nằm ngoài Git.

```console
python -B -m scripts.benchmark_full_train --input-dir data/processed/full-train-benchmark-v1/inputs --output-dir data/processed/full-train-benchmark-v1/run-01
```

Bằng chứng còn cần gồm quyền O4 cho đúng mục đích đọc và ghép saved labels với
TRAIN GT, phạm vi xuất số liệu và case review nếu có, projection/receipt xác
thực cho InternVL, MiniCPM và cohort, cùng review/audit trên chính HEAD. Chưa
cần thay lựa chọn sản phẩm, lấy thêm split hoặc yêu cầu chạy lại model. M3 R1–R5
synthetic và M2 lịch sử có [lệnh và mẫu số riêng](../SEMINAR_ANALYSIS.md).

## Đối chiếu qua Orca

- Codex sửa ba nhóm lỗi lineage ở R3/R4. Lượt kiểm từng dòng xác nhận
  11.032 row ID, giá trị, tử số, mẫu số, trạng thái và lý do vẫn khớp trước
  và sau. So dòng lineage dùng oracle fixture riêng. Lượt đó kiểm 78 test
  và đủ 12 tệp từ CLI M2. Receipt của lượt worker ghi source có thay đổi
  chưa commit. [Nguồn yêu cầu audit](https://github.com/tantdna2/SafeShift/pull/136#issuecomment-6412563251).
- Antigravity Hydrogen Medium chạy các test extension và tính lại metric
  Qwen3 cùng cận hai sản phẩm từ bảng tổng hợp. Review ghi bốn mục nhỏ
  về kiểm kiểu đầu vào, danh sách trong CSV, SHA256 nguồn trong receipt và
  kiểm đường đi CLI/export. Các mục đã được sửa, test bổ sung xác nhận
  receipt và refusal khi dùng lại thư mục đích. Review này dùng dữ liệu
  tổng hợp/công khai và fixture.
- Review trực tiếp trên GitHub và audit độc lập theo cổng merge của chính
  HEAD vẫn cần ghi nhận. Các kiểm tra CPU của PR xác nhận phần mềm và phép
  tính trong đúng phạm vi đầu vào đã sử dụng.
