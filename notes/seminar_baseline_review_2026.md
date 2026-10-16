# Nội dung chuẩn bị FORM REVIEW KẾT QUẢ BASELINE ĐỀ TÀI NGHIÊN CỨU 2026

Trạng thái: **DRAFT INPUT — chưa phải form đã điền**. Tài liệu này chỉ tổng hợp
thông tin đã có bằng chứng để ChatGPT/người dùng chuyển sang sáu mục của form sau
khi PR được review và merge. Các trường `[CẦN ĐIỀN]` và `N/A` không được suy đoán.

## 1. Thông tin đề tài và dữ liệu

- **Tên đề tài đề xuất:** *SafeShift: Evaluating the Validity and Cross-Domain
  Reliability of Internal Hazard Scores in Vision-Language Models*.
- **Trạng thái quyết định:** `DEC-PA3-011 PROPOSED`; D9R22 vẫn có hiệu lực cho đến
  khi Research Lead phê duyệt đề xuất qua quy trình PR.
- **Dataset:** InspecSafe-V1. Baseline hiện có dùng toàn bộ **3.763 ảnh TRAIN**
  gốc; 749 Anomaly (Level01–03), 3.014 Normal (Level04), năm miền công nghiệp.
- **Giới hạn dữ liệu:** TRAIN đã phơi nhiễm và có phụ thuộc/rò rỉ lịch sử; không
  đại diện cho generalization. Không đọc hoặc đánh giá TEST trong nhiệm vụ này.
- **Thông tin hành chính:** Họ tên `[CẦN ĐIỀN]`; MSSV `[CẦN ĐIỀN]`; nhóm/lớp
  `[CẦN ĐIỀN]`; giảng viên hướng dẫn `[CẦN ĐIỀN]`; ngày nộp `[CẦN ĐIỀN]`.

## 2. Property và mục tiêu nghiên cứu

- **Property chính:** tính hợp lệ phân biệt nguy cơ của điểm nội tại — điểm liên
  tục có xếp hạng Anomaly cao hơn Normal tốt hơn các mốc từ đầu ra sinh ra trên
  cùng dữ liệu và cùng tập ID hợp lệ hay không.
- **Property phụ:** độ bền của tín hiệu sau khi kiểm soát human presence/domain/
  provenance; coverage/INVALID; FNR/FPR và giới hạn chuyển miền; ảnh hưởng của
  phụ thuộc theo point/source sequence, duplicate history và domain/platform.
- **RQ1:** so sánh công bằng internal-score AUROC với generated-output baselines.
- **RQ2:** định lượng mức tín hiệu còn lại sau các kiểm soát gây nhiễu đã duyệt.
- **RQ3:** báo cáo miss/false-alarm theo miền sau quy tắc ngưỡng được duyệt trước;
  đây là đánh giá thực nghiệm, không phải bảo đảm thống kê về an toàn.
- **Đóng góp dự kiến:** giao thức so sánh công bằng; phân tích gây nhiễu/tính hợp
  lệ; đánh giá độ tin cậy và giới hạn chuyển miền. PA3 không phải thuật toán mới.

## 3. Baseline đã setup và chạy

| Hạng mục | Giá trị đã kiểm chứng |
| --- | --- |
| Model / checkpoint | `Qwen/Qwen2.5-VL-3B-Instruct` @ `66285546d2b821cf421d4f5eb2576359d3770cd3` |
| Vai trò | Baseline; một trong bốn mô hình bắt buộc |
| Dataset / split | InspecSafe-V1 original full TRAIN, 3.763 ảnh, đã phơi nhiễm |
| Prompt / generation | C1; greedy, `do_sample=false`, batch 1, tối đa 32 token |
| Inference stack | Transformers 4.51.3; FP16; SDPA; không quantization; một Tesla T4; native processor 200704–1003520 pixels; PA3-R2 pre-merger clamp |
| Raw artifact policy | Raw output/decision logits lưu trước parse và được liên kết sample/run/config |
| CPU audit stack | Python 3.11.11, Linux x86_64/WSL2; Transformers 4.51.3, tokenizers 0.21.1, huggingface-hub 0.30.2; không torch/GPU/weights trong audit |
| T1 / recomputation | T1 28/28 PASS; 3.763/3.763 SUCCESS; coverage 100%; official `train_report` exit 0; bốn shard sealed và disjoint |
| Windows/Linux status | Windows strict audit từng BLOCKED/failed vì sai khác 1 ULP ở xác suất trung gian; cùng scorer trên CPU Linux PASS mà không đổi tolerance hay kết quả lưu |
| Reproducibility | Lệnh, pins, hashes và small aggregate JSON được version-control; raw output/tokenizer/weights/log lớn giữ local theo policy |
| Provenance limitation | Shard 1 thiếu outer download receipt; internal journal/package checks vẫn PASS, nhưng không suy ra external authenticity |

Bốn mô hình cuối cùng vẫn bắt buộc:

| Mô hình | Internal-score/PA3 status hiện có | Hành động trước thí nghiệm |
| --- | --- | --- |
| Qwen2.5-VL-3B-Instruct | **VERIFIED** cho PA3-R2 baseline trên TRAIN; không phải generalization | Dùng làm baseline với đúng revision/config và giới hạn đã audit |
| Qwen3-VL-8B-Instruct | **NOT VERIFIED** cho PA3 tương thích | Audit decision step, tokenizer/raw logits hoặc đại lượng model-native tương đương |
| InternVL3-2B-hf | **NOT VERIFIED** cho PA3 tương thích | Audit interface/token mapping/raw evidence; không tái dùng công thức Qwen ngầm |
| Moondream2 | **NOT VERIFIED** cho PA3 tương thích | Audit score interface và khả năng tính lại; nếu không hỗ trợ thì trình fallback/N/A |

Không bỏ hoặc thay mô hình. Nếu một mô hình không cung cấp điểm nội tại tương
thích, Research Lead phải duyệt phương án model-native đã chứng minh, generated-
output-only comparator hoặc N/A trước khi chạy/báo cáo.

## 4. Bốn metric baseline

Mọi giá trị dưới đây dùng đúng 3.763 ID score-valid, InspecSafe-V1 TRAIN. Với cả
bốn metric, hướng tốt là **cao hơn**, nhưng chúng đo các property khác nhau.

| Metric | Giá trị audited | Hướng tốt | Điều kiện và diễn giải |
| --- | ---: | --- | --- |
| AUROC PA3 nội tại | **0,8266558463706973** | Cao hơn | Điểm `logsumexp(z1,z2,z3)-z4`, Anomaly dương; rank discrimination, không threshold/calibration/accuracy |
| AUROC nhãn Qwen nhị phân | **0,500000** | Cao hơn | Generated Level01–03=Anomaly, Level04=Normal; cùng ID; mọi nhãn sinh ra đều là Anomaly |
| Accuracy nhãn Qwen 4 mức | **3,4547%** (130/3.763) | Cao hơn | Exact Level01–Level04 generated-label accuracy; không gọi là PA3 accuracy |
| Accuracy nhãn Qwen nhị phân | **19,9043%** (749/3.763) | Cao hơn | Generated Anomaly/Normal accuracy; confusion: 749 Anomaly→Anomaly, 3.014 Normal→Anomaly |

- **Paper/Official comparator cùng điều kiện:** `N/A — chưa có kết quả paper hoặc
  official được xác minh trên cùng model revision, cohort, prompt, endpoint và
  mẫu số; không tự điền số khác điều kiện đo`.
- **Kết quả ba mô hình còn lại:** `N/A — chưa có PA3/internal-score compatible
  experimental result đã xác minh`.

## 5. Đánh giá baseline và next-step target

Baseline cho thấy PA3 có khả năng xếp hạng trên TRAIN đã phơi nhiễm trong khi
nhãn sinh ra suy biến thành toàn Anomaly. Đây là bằng chứng đủ để đặt câu hỏi về
giá trị của tín hiệu nội tại, không đủ để kết luận generalization, calibration,
khả năng quyết định an toàn hoặc hiệu năng bốn mô hình.

Không đặt target số học hậu nghiệm. Target nghiên cứu có cơ sở là:

1. **RQ1:** trên một cohort chung được duyệt, báo internal score và generated-
   output baselines với cùng chiều điểm, cùng valid-ID intersection, cùng mẫu số;
   luôn báo coverage/INVALID/failure trên toàn cohort.
2. **RQ2:** predeclare kiểm soát human presence, folder domain và provenance.
   Human presence cần định nghĩa annotation-derived và quyền đọc riêng;
   source-family chỉ là heuristic. Báo cả phân tầng và sensitivity analysis,
   không diễn giải tương quan thành nhân quả.
3. **RQ3:** chọn threshold prospectively trên cohort được duyệt tách khỏi đánh
   giá; báo FNR/FPR, coverage và denominators theo từng miền. Metallurgy thiếu
   hỗ trợ Anomaly phải được nêu, không impute hoặc gộp để che mẫu số yếu.
4. **Dependence:** dùng group/point và provenance clusters đã duyệt cho split hoặc
   uncertainty; giữ cross-split exact/near-duplicate và source-sequence risk trong
   limitations. Không tự tạo split mới.
5. **Bốn mô hình:** hoàn thành capability audit trước; khóa revision/interface/
   preprocessing/precision/prompt và raw capture theo từng mô hình. So sánh PA3
   chỉ khi semantics tương thích được chứng minh.

Mọi metric code mới, label/annotation access, threshold selection, GPU inference,
holdout và TEST cần quyết định cùng authority riêng. Advanced risk control và mọi
tuyên bố bảo đảm an toàn nằm ngoài Seminar, dành cho hướng khóa luận.

## 6. Evidence để điền form sau khi PR được duyệt

- **GitHub repository:** <https://github.com/tantdna2/SafeShift>
- **Draft PR:** <https://github.com/tantdna2/SafeShift/pull/105>
- **Quyết định đề xuất:** [DEC-PA3-011](../DECISIONS.md#dec-pa3-011--proposed-seminar-internal-hazard-score-direction-2026-10-16)
- **CPU audit hoàn thành và lệnh tái lập:** [completion report](pa3_r2_cpu_completion_20261015.md)
- **Tổng hợp nhỏ đã review:** [aggregate JSON](pa3_r2_cpu_completion_20261015.summary.json)
- **Lịch sử BLOCKED được bảo toàn:** [prior audit handoff](pa3_r2_cpu_audit_20261015.md)
- **Yêu cầu bốn mô hình:** [four-model scope](pa3_four_model_seminar_scope.md)
- **Model/runtime config:** [`qwen2_5_t4_runtime.v1.json`](../configs/pre_freeze/qwen2_5_t4_runtime.v1.json)
- **R2 authority/config:** [`r2_authority.v1.json`](../configs/pa3/r2_authority.v1.json)
- **R2 manifest:** [`pa3_r2_full_train.v1.json`](../data/manifests/pa3_r2_full_train.v1.json)
- **Prompt:** [`p2_classification_c1_v1.txt`](../prompts/p2_classification_c1_v1.txt)

Large official audit JSON/CSV, raw journals, tokenizer and dependency environment
không commit. Completion report ghi SHA-256 của các artifact local; aggregate JSON
không chứa sample ID, raw output, ảnh/annotation hoặc absolute machine path.
