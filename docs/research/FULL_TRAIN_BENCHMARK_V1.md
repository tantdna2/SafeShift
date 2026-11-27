# SafeShift — Benchmark First trên Full-TRAIN

## Xác minh đầu vào

Owner cấp phạm vi đọc và ghép chính xác 3.763 TRAIN ID, với kết quả
`PROVISIONAL_PRE_FINAL_ADMISSION`. Bốn projection được ghim kích thước
và SHA256 trong [cấu hình benchmark](../../configs/analysis/full_train_benchmark.v1.json).
Khi ghép phải khớp ID, split, GT, domain và SHA256 ảnh với cohort đã khóa.
[Chỉ thị Owner](https://github.com/tantdna2/SafeShift/pull/136#issuecomment-7206868367).

- **Qwen3.** Dùng lại manifest `7e779307…` và hai projection đã kiểm.
- **InternVL3.5.** Manifest continuation SHA256 `8bd91408…` khớp snapshot
  theo audit cục bộ trước đó. 23 attempt đóng góp đủ 3.763 nhãn và lineage.
  Attempt 23 lấy ZIP `217f685b…` từ event 25 theo lựa chọn đã ghi.
  Manifest bàn giao mới `6c043c75…` khóa projection, biên bản và script tái lập.
  Các kiểm tra local giữ nguyên tình trạng đối soát provider và Final Admission.
- **MiniCPM.** Tái lập từ hai bản custody đã lưu. Receipt `385ceddb…` và cả
  bốn member trùng byte với PR #214, bao gồm 205 conversion và C1 gốc.
  [Hậu kiểm PR #214](https://github.com/tantdna2/SafeShift/pull/214#issuecomment-7184951265).

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
  ≤8/1.418 = 0,56%. Accuracy bốn lớp tối đa 2.006/3.763 = 53,31% vì số đúng
  từng lớp bị chặn bởi min(support, số dự đoán). Các cận lấy trường hợp
  thuận lợi nhất về phần giao giữa hai tập. Độ lệch phân bố là quan sát.
  Nguyên nhân như ranking token bị grammar
  khuếch đại, nhầm rubric hoặc shortcut còn cần kiểm trên bản lưu có quyền.
- **MiniCPM V1** dự đoán Hazard 637/3.763, Normal 3.126/3.763. Với cùng điều kiện
  khớp cohort, phải có ít nhất 112 false-safe (FNR ≥14,95%, Hazard Recall
  ≤85,05%) và recall Level01 ≤145/490 = 29,59%. Nguồn đã xác minh một lỗi
  định dạng: 205 object điền cụm mô tả Normal vào `safety_level`, khiến C1
  trả INVALID theo hợp đồng. V1 ánh xạ chính xác sang Level04 và giữ mọi
  prediction canonical gốc. Cần GT để biết bao nhiêu conversion thành TN
  hoặc false-safe, bao nhiêu là Level01. Tăng valid rate từ 94,55% lên 100%
  tăng độ phủ đúng 205/3.763, tức 5,45 điểm phần trăm.
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

## Quyền và chứng từ để ghép đủ ba nguồn

Revision `f3cb7d3e` của InspecSafe-V1 công bố CC BY 4.0. Có thể dùng
TRAIN đã cấp phép để phân tích hồi cứu có attribution. Việc đọc projection
private và đối chiếu kết quả đã lưu phụ thuộc vào thẩm quyền của đơn vị quản
lý bản lưu, hash của chính snapshot và phạm vi đã duyệt. Việc chọn ba sản
phẩm ở cấp dự án đã chốt. V/T độc lập, raw, ảnh và dữ liệu TEST nằm ngoài
scope này. [Dataset InspecSafe-V1](https://huggingface.co/datasets/Tetrabot2026/InspecSafe-V1/tree/f3cb7d3e7827c1afc1c5bfd0524257984bba46ab),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
[bài báo dataset](https://doi.org/10.1038/s41597-026-07796-x),
[bằng chứng selection](https://github.com/tantdna2/SafeShift/pull/136#issuecomment-7199181963).

| Phần | Bằng chứng đã có | Cần để dùng trong benchmark hồi cứu |
| --- | --- | --- |
| TRAIN GT và Qwen3 | Quyết định Qwen3 riêng và manifest đã niêm phong. Đã tạo `cohort.json` và `qwen3.json` từ bản này, kiểm đúng 3.763 ID, split, GT, domain, hash ảnh, và xác thực nguồn Qwen3. | Dùng bản `cohort.json` đã kiểm làm projection ứng viên. Custodian xác nhận đây là cohort đúng phạm vi và ghim hash các member khi mở benchmark ba bên. |
| InternVL3.5 Grammar V2 | O4 của Issue180 cấp phạm vi tạo kết quả engineering và custody riêng. Báo cáo cục bộ xác nhận đủ 3.763 và các ZIP được journal trỏ tới. Owner đã chốt lý do chạy lại Attempt 23. | Cần một manifest kết quả hồi cứu có quyền và hash được custodian xác nhận cho đủ 3.763 hàng. Ghi rõ nguồn được chọn liên kết tới ZIP Attempt 23 mà event 25 đã ghi, không đổi lựa chọn theo GT. Giữ giới hạn provider, receipt mâu thuẫn và định danh/thẩm quyền journal. |
| MiniCPM Normalization V1 và C1 | PR #214 hậu kiểm kỹ thuật cho bản dẫn xuất có receipt ghim `385ceddb…`; receipt ràng buộc C1 parent và 205 conversion. | Dùng chính năm tệp đã niêm phong từ custodian, cùng projection đã kiểm ID/hash ảnh/attempt/config và cặp status/label trước–sau. Quyền tạo V1 không tự mở rộng sang ghép GT. Không cần tạo lại kết quả mô hình hoặc chọn lại C1/V1. |
| Phạm vi chạy và review | PR #136 định danh extension riêng và giữ quyền M4 lịch sử bất biến. | Một bản ghi của người có thẩm quyền với saved artifacts cho đúng bốn projection TRAIN, quyền đọc/ghép cục bộ và xuất thống kê gộp. Ghép với chứng từ nguồn đã xác minh, review và audit code theo quy trình hiện hành. |

Bản ghi O4 kỹ thuật đã được đọc lại từ GitHub. Phạm vi là original TRAIN,
run engineering và custody của một Operator, với giới hạn không dùng GT cứu
nhãn. Văn bản không cấp riêng bundle paired để đánh giá hồi cứu của PR này.
[Issue180, O4](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6657871236),
[PR #214 hậu kiểm](https://github.com/tantdna2/SafeShift/pull/214#issuecomment-7184951265),
[thẩm quyền dữ liệu](THESIS_DATA_PROTOCOL.md).

Nếu chỉ cần benchmark hồi cứu, Owner trong phạm vi custody của mình hoặc
người được đơn vị giữ dữ liệu ủy quyền có thể cung cấp **một** bản ghi xác
thực trên PR #136, kèm đường dẫn nội bộ và seal của nguồn đã lưu. Dùng seal
Qwen3 và MiniCPM đã ghim. Gắn thêm seal hoặc manifest được custodian xác nhận
cho InternVL, cùng chứng từ chọn snapshot trước khi mở GT. Coordinator chuẩn
bị và kiểm hash/kích thước bốn projection từ nguồn có quyền. Phạm vi gồm
đúng 3.763 TRAIN ID, GT mức ảnh, folder domain,
image SHA, nhãn đã lưu, status gốc và lineage. Quyền chỉ dùng để đọc, ghép,
tính CPU cục bộ và báo số gộp. Nếu một phần thuộc đơn vị khác, cung cấp căn
cứ quyền sẵn có hoặc xác nhận từ đơn vị đó. Có thể dùng master/Qwen3 đã kiểm
và chỉ bổ sung nguồn InternVL cùng bộ MiniCPM đã ghim. Giữ TRAIN hồi cứu và
ghi `PROVISIONAL_PRE_FINAL_ADMISSION` nếu authority cho phép dùng snapshot
trước admission. Không cần mở thêm thủ tục cấp phép dataset công khai.

`official-report` của hai route vận hành vẫn cần Final Admission theo runbook.
Một bản ghi phân tích hồi cứu không thay certificate, chứng từ provider,
phê duyệt học vụ hay quyền merge. Nếu yêu cầu dùng kết quả chính thức, cần
chính các chứng từ Final Admission và đường `official-report` đã duyệt.
[InternVL](../TRAIN3763_DEFERRED_RECONCILIATION.md),
[MiniCPM](../MINICPM_OFFLINE_CONTINUATION.md).

## Từ vấn đề đến câu hỏi cải tiến

| Ưu tiên điều tra | Bằng chứng và kiểm tra tiếp | Ứng viên, định hướng | Metric chính và guardrail cần chốt |
| --- | --- | --- | --- |
| 1. False-safe, hạ severity và đánh đổi false alarm | Qwen3: Power 19/81 FN, oil/chemical 12/239 severe, 303 Level01 → Level02. Kiểm case theo rubric, domain, ảnh trùng và source. Đối chiếu InternVL/MiniCPM trên ID trước so ngang. | CV-B/D, CT1. So baseline theo lớp/miền. Nếu rubric/mapping xác nhận, cân nhắc grounding/prompt hoặc can thiệp vào quyết định có đối chứng. | Severe miss/FNR và recall Level01; guardrail FPR, valid rate, Macro-F1, số ca review, chi phí. |
| 2. Phân bố dự đoán lệch và bất đồng | InternVL nhiều Hazard/Level03, MiniCPM nhiều Normal. Xác minh cùng đúng, cùng sai và lỗi riêng, đặc biệt ca nặng. Kiểm ngẫu nhiên ca đúng cùng strata để tránh chỉ chọn ca minh họa lỗi. | CV-B/C, CT2. Domain-balanced sampling hoặc ensemble chỉ đáng thử nếu có bằng chứng theo miền hoặc bổ trợ cặp. Đồng thời khảo sát CV-A nếu truy nguyên cho thấy vấn đề nằm ở dữ liệu/nguồn. | Worst-domain và paired severe misses; guardrail precision, false alarm, chi phí mỗi ảnh và budget review. |
| 3. Độ tin cậy | Qwen3 nguồn có score riêng, hai hệ còn lại thiếu score hợp lệ. | CV-B/C, CT2. Calibration hoặc threshold tuning khi có score đúng nghĩa, protocol tách validation và quyền tương ứng. So đối chứng cùng dữ liệu; đóng góp nằm ở bằng chứng chênh lệch theo domain và an toàn. | Brier/reliability, AUPRC hoặc FNR tại FPR khóa theo estimand; kiểm coverage, severe miss, phân bố miền và chi phí. |
| 4. Truy xuất chứng cứ | 205 MiniCPM conversion có lineage và cơ chế định dạng đã kiểm. Qwen3 có lỗi nguy hiểm cần case review; chưa có căn cứ gán vùng bằng chứng. | CV-C/D, CT3. Cân nhắc evidence audit viewer nếu có quyền giữ chứng cứ, rubric và đánh giá người dùng. | Tỷ lệ truy đúng provenance, độ chính xác và thời gian review. Guardrail quyền dữ liệu, độ đầy đủ, lỗi truy xuất và workload. |

Các thứ tự trên ưu tiên **điều tra**. Việc chốt phương pháp, tính mới và
ngưỡng cần phản biện sau khi đủ benchmark. Theo rubric giảng viên, E1 so sánh
cùng protocol, E2 ablation, E3 stress test, E4 error analysis có case trước–sau
và E5 tái lập. Nếu viewer được chọn, đo usefulness trong phạm vi CT3 có quyền.
Tuning/grounding có thể cần model
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
control ghim các chứng từ và member. Bản ghi release xác định `result_status`
là `PROVISIONAL_PRE_FINAL_ADMISSION` hoặc `RECONCILED_SOURCE_RETROSPECTIVE`
theo chứng từ nguồn. Giá trị `release: null` hiện hành làm
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
  `minicpm_normalization_impact` báo toàn cohort và từng miền, phân bố GT của
  các conversion, INVALID Hazard chuyển thành false-safe và INVALID Normal
  chuyển thành true negative. Mỗi delta có tử/mẫu số. FNR dùng support Hazard,
  severe miss dùng support Level01, accuracy và label validity dùng planned.
  `(FN + U_A) / support Hazard` được báo riêng để thấy chuyển đổi loại lỗi
  khi tổng Hazard bị bỏ sót hoặc INVALID giữ nguyên.
  Giữ GT gốc cho từng ID kể cả khi hai ảnh trùng hash có GT khác nhau và đếm
  các nhóm xung đột để kiểm toán riêng.
  `metrics.csv`, `confusion.html`, `receipt.json` cung cấp bảng số, heatmap
  và toàn vẹn đầu vào/đầu ra. Folder output phải mới, dưới `data/processed/`.
  Dữ liệu, GT từng ID, raw và artefact riêng tư nằm ngoài Git.

```console
python -B -m scripts.benchmark_full_train --input-dir data/processed/full-train-benchmark-v1/inputs --output-dir data/processed/full-train-benchmark-v1/run-01
```

Bằng chứng còn cần cho chế độ hồi cứu là quyền đọc/ghép scoped, nguồn đã
seal và review/audit trên chính HEAD. Dùng chế độ chính thức chỉ sau khi hai
route hoàn thành Final Admission và xuất `official-report`. Quyền payload M4
lịch sử và quyền xem ảnh/case evidence có scope riêng. Ba sản phẩm, split
và kế hoạch dùng kết quả đã lưu đã rõ.
[InternVL](../TRAIN3763_DEFERRED_RECONCILIATION.md),
[MiniCPM](../MINICPM_OFFLINE_CONTINUATION.md),
[M2 và lệnh M3 R1–R5](../SEMINAR_ANALYSIS.md).

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
- Antigravity Neon Medium phản biện độc lập từ tài liệu công khai. Phép
  tính Fraction khớp bảng Qwen3. Báo cáo bổ sung cận Accuracy của InternVL
  và xác nhận rằng conversion MiniCPM giữ TP, có thể chuyển Hazard bất
  hợp lệ thành false-safe. Neon ưu tiên kiểm ảnh trùng, ca Level03 và
  lineage, cân workload và chi phí khi thử CT2/CT3. Hai reviewer thống
  nhất về công thức, cận và phạm vi kết luận. Cả hai giữ mở nguyên nhân
  của pattern thị giác và audit chính thức của HEAD mới. Lượt Neon dùng
  main đã xác minh và hồ sơ audit lịch sử, không kiểm software mới.
- Review trực tiếp trên GitHub và audit độc lập theo cổng merge của chính
  HEAD vẫn cần ghi nhận. Các kiểm tra CPU của PR xác nhận phần mềm và phép
  tính trong đúng phạm vi đầu vào đã sử dụng.
