# W2.4 Metrics & Statistical Protocol Decision Brief

- **Tài liệu:** Báo cáo căn cứ quyết định chỉ số đánh giá và giao thức thống kê (W2.4 Metrics & Statistical Evaluation Protocol Decision Brief)
- **Dự án:** SafeShift: Benchmarking Cross-Domain Generalization and Evidence Grounding in Vision-Language Models for Industrial Safety Assessment
- **Bộ dữ liệu:** InspecSafe-V1 (5.013 mẫu ảnh: 4.013 Normal, 1.000 Anomaly)
- **Trạng thái:** BÁO CÁO CĂN CỨ KỸ THUẬT (TECHNICAL EVIDENCE BRIEF) — ĐỀ XUẤT CHO QUYẾT ĐỊNH D5 (CHƯA PHÊ DUYỆT)
- **Ngày lập:** 2026-09-17
- **Phiên bản:** 1.2.0 (Methodology Qualified Edition)

---

## 1. Purpose

Văn bản này thiết lập cơ sở lý thuyết, bằng chứng thực nghiệm và phân tích phương pháp luận cho bước **W2.4 — Metrics & Statistical Evaluation Protocol** của dự án SafeShift, chuẩn bị căn cứ khoa học cho **Quyết định D5 — Giao thức chỉ số và thống kê đánh giá (Metrics & Statistical Evaluation Protocol)**.

Báo cáo giải quyết toàn diện 7 câu hỏi phương pháp luận cốt lõi:
1. **Chỉ số phân loại (Classification Metrics):** Lựa chọn và chuẩn hóa các chỉ số đo lường năng lực phân loại mức độ an toàn công nghiệp (`Level01`–`Level04`) trong bối cảnh mất cân bằng dữ liệu cực đoan.
2. **Suy giảm hiệu năng xuyên miền (Cross-Domain Robustness Drop):** Đặt phân tích theo từng lớp (`Class-Conditional Domain Analysis`) làm mỏ neo chính để giảm thiểu nhiễu tỷ lệ nhãn, đồng thời định vị đúng vai trò của các chỉ số chẩn đoán tổng hợp.
3. **Đánh giá bám bằng chứng trực tiếp (Direct Grounding Evaluation):** Xác lập chỉ số liên tục (`Continuous IoU`) làm thước đo định vị chính, đi kèm các ngưỡng nhạy được xác định trước khi xem kết quả mô hình (`pre-specified before model-result inspection`: `Hit@0.25`, `Hit@0.50`) và thuật toán ghép cặp tối ưu hai phía (`Optimal Bipartite Matching`).
4. **Phân rã Direct Object-Support và Weak Proxy:** Phân định phương pháp đo lường và cách diễn giải riêng biệt giữa bằng chứng trực tiếp và vùng đại diện thân người (`Identity-Agnostic Proxy Localization Consistency`), sử dụng đa giác gốc cho Pointing Hit và kiểm soát mập mờ nhiều người qua tập con đơn người (`Single-Person Proxy Subset`).
5. **Định lượng bất định và khoảng tin cậy (Uncertainty & Confidence Intervals):** Xây dựng quy trình `Domain-Stratified Point-Cluster Bootstrap` kiểm soát phụ thuộc cụm thư mục điểm logic (`point_id`), loại bỏ phân tầng theo nhãn an toàn để tránh hiện tượng tạo phương sai 0 giả tạo trên các tầng đơn mẫu (`singleton strata`).
6. **Chính sách miền luyện kim và dữ liệu thưa (Metallurgy & Sparse-Support Policy):** Xử lý trung thực các miền có mẫu số nhỏ ($N_{\text{anomaly}}=9$, $N_{\text{Level03}}=15$) thông qua công bố mẫu số và khoảng tin cậy, loại bỏ quy tắc ngưỡng $N \ge 30$ tùy ý.
7. **So sánh đa mô hình VLM (Model Comparison):** Thiết lập khoảng tin cậy hiệu số theo cặp (`Paired Bootstrap Difference CI`) trên cùng tập replicate làm thước đo hướng phân hóa chính, coi trọng độ lớn hiệu ứng và không kết luận tương đương khi khoảng tin cậy chứa 0.

> [!IMPORTANT]
> **Giới hạn và tính độc lập của W2.4:**
> - Tài liệu này là **Báo cáo căn cứ kỹ thuật (Decision Brief)** nhằm đề xuất các phương án ứng viên. Toàn bộ các đề xuất ở trạng thái **`PROPOSED, NOT APPROVED`** cho đến khi có sự phê chuẩn chính thức từ Project Owner / Research Lead.
> - Báo cáo này **tuyệt đối KHÔNG tự ý ghi hay sửa đổi `DECISIONS.md`**.
> - Không triển khai bộ chấm sản xuất (`production evaluator`) trong `safeshift/` trước khi Quyết định D5 được phê duyệt chính thức.
> - Tuyệt đối không chạy suy luận mô hình VLM, không gọi API thương mại trả phí, và không sửa đổi dữ liệu thô.

---

## 2. Locked Decisions D1-D4/D6/D7

Báo cáo W2.4 kế thừa tuyệt đối và không thay đổi các quyết định đã được phê chuẩn tại [DECISIONS.md](../DECISIONS.md):

- **DEC-W2-D1-001 (Research Framing & Protocol Hierarchy):**
  - Seminar được định hình là **Cross-Domain Robustness Evaluation trên Frozen Pretrained VLMs**. Tuyệt đối không gọi là Domain Generalization theo nghĩa học máy truyền thống có huấn luyện trên miền nguồn.
  - Phân tầng giao thức:
    - **P1 (Baseline Replication):** 1.250 mẫu test chính thức; grounding trên P1 là SafeShift extension, không phải upstream baseline.
    - **P2 (Primary Research Protocol):** Toàn bộ 5.013 mẫu ảnh; báo cáo phân rã 5 miền công nghiệp; bảo lưu nguyên vẹn metadata `split: train/test`.
    - **P3 (Candidate Sensitivity Protocol):** Đánh giá có xét nhóm, duy trì trạng thái candidate, không phải clean benchmark.
    - **P4 (Thesis DG Candidate):** Bảo lưu cho Luận văn tốt nghiệp sau này.
  - Phê chuẩn 3 câu hỏi nghiên cứu hoạt động: RQ1 (biến thiên xuyên miền & đồng biến thiên robot platform), RQ2 (tập trung lỗi theo cấp an toàn & hazard strata), RQ3 (tính nhất quán giữa phân loại và bám bằng chứng).
- **DEC-W2-D2-002 (Split, Evaluation Pool, and Grouping Policy):**
  - Đơn vị dự đoán duy nhất của mô hình VLM là **Ảnh (`Image`)**. Mọi phản hồi thô (`raw model outputs`) phải được lưu trữ ở cấp độ từng ảnh kèm định danh mẫu, prompt ID, model/version và decoding settings.
  - Trường `point_id` là tín hiệu gom nhóm ứng viên ưu tiên (`preferred candidate grouping signal`) cho dữ liệu Bình thường (`Normal_data`) để kiểm soát phụ thuộc đa khung hình nội bộ điểm.
  - 1.000 mẫu Anomaly không được giả định là 1.000 sự kiện độc lập về mặt thống kê. Trường `source-family` chỉ là tín hiệu kinh nghiệm (heuristic), không phải là ID video thật (`not true video ID`).
  - Phê duyệt hai tập con phân tích độ nhạy phụ trợ cho P1: 1.248 mẫu (loại 2 mẫu lặp nội bộ test) và 1.241 mẫu (loại thêm 7 mẫu exact cross-split).
- **DEC-W2-D3-003 (Operational Domain Definition and Mismatch Policy):**
  - Sử dụng trường **`folder_domain` làm Nhãn miền thao tác chính (`Primary Operational Domain Label`)**. Tuyệt đối không gọi là danh tính thực địa vật lý chuẩn (`physical site ground truth`).
  - Duy trì chính sách báo cáo độ nhạy kép (`Dual-Report Sensitivity Policy`) với 36 mẫu xung đột: Phân tích chính theo `folder_domain`; Sensitivity A loại bỏ 36 mẫu; Sensitivity B tái phân bổ theo `text_domain`.
  - Miền Luyện kim (`metallurgy`) có 720 mẫu (711 Normal, 9 Anomaly; test có 0 Anomaly). Tuyệt đối không tuyên bố $N=9$ là đủ cho suy luận thống kê mạnh.
  - Chuẩn hóa thuật ngữ: "đồng biến thiên với nền tảng robot" (`co-variation with robot platform`) hoặc "nhiễu nền tảng robot" (`platform confounding`). Tuyệt đối không đưa ra khẳng định nhân quả (`causal claim`).
- **DEC-W2-D4-004 (Canonical Grounding Output Interface):**
  - Xác lập định dạng hộp bao nội bộ chuẩn mực duy nhất:
    $$\mathbf{b}_{\text{canonical}} = [x_{\min}, y_{\min}, x_{\max}, y_{\max}] \in [0.0, 1.0]$$
    với thứ tự tọa độ $x$-first, chuẩn hóa trên thang $[0, 1]$.
  - Bắt buộc lưu trữ chuỗi phản hồi thô nguyên văn (`Raw Model Response`) trước khi phân tích cú pháp. Bộ adapter/parser chuyển đổi tất định từ native format sang canonical format.
  - Áp dụng chính sách phân tầng theo năng lực (Capability-Aware Policy B): Track grounding chỉ chạy trên các mô hình có năng lực xuất tọa độ; không phạt lỗi grounding đối với mô hình chỉ phân loại thuần túy.
- **DEC-W2-D6-006 (Hazard Taxonomy & Grounding Census):**
  - Phê duyệt Hệ phân loại 12 Nguy cơ Nguyên tử (`Hazard Atoms`) giải thích trọn vẹn 1.000 mẫu Anomaly (1.788 hazard atoms).
  - Phê chuẩn 3 trạng thái hỗ trợ: `DIRECT_OBJECT_SUPPORT` (781 atoms / 721 mẫu), `WEAK_PROXY_SUPPORT` (947 atoms / 608 mẫu), `NO_CURRENT_SPATIAL_GT` (60 atoms / 59 mẫu).
  - Đẳng thức kiểm tra toàn vẹn tập hợp: $721 + 608 - 347 = 982$ mẫu có GT đánh giá được; $982 + 18 (\text{Unsupported Only}) = 1.000$ mẫu Anomaly.
  - Phân rã RQ3 thành RQ3-A (Direct Object-Support Grounding) và RQ3-B (Weak Proxy Grounding), báo cáo tách biệt bắt buộc.
  - Phê chuẩn 7 tầng nguy cơ gom nhóm (`Candidate Grouped Hazard Strata`) cho RQ2; chuẩn hóa thuật ngữ "Classification-Grounding Inconsistency relative to available object-support annotation".
- **DEC-W2-D7-007 (Rationale Annotation Policy):**
  - Chọn Phương án D7-A: Không tạo nhãn rationale mới trong giai đoạn Seminar 8 tuần.
  - Không phê duyệt Tỷ lệ Ảo giác Đối tượng (`Object Hallucination Rate`) trên toàn bộ dataset vì chú thích đối tượng gốc không triệt để (`annotation is not exhaustive`); cấm ngụy biện $\text{missing JSON label} = \text{object absent}$. Bảo lưu D7-C cho Luận văn tốt nghiệp.

---

## 3. Dataset Support Constraints

Trước khi thiết kế bất kỳ công thức thống kê nào, giao thức đánh giá bắt buộc phải xem xét các ràng buộc phân bố mẫu không thể thay đổi của bộ dữ liệu InspecSafe-V1.

### 3.1 Phân bố an toàn tổng thể và tập kiểm thử chính thức

| Phân vùng | Level 01 (Nguy hiểm cấp 1) | Level 02 (Nguy hiểm cấp 2) | Level 03 (Nguy hiểm cấp 3) | Level 04 (Bình thường) | Tổng số mẫu ($N$) | Tỷ lệ Anomaly |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **P2 — Toàn bộ Dataset** | 659 (13,15%) | 326 (6,50%) | 15 (0,30%) | 4.013 (80,05%) | **5.013** | 1.000 (19,95%) |
| **P1 — Tập Test Chính thức** | 169 (13,52%) | 75 (6,00%) | 7 (0,56%) | 999 (79,92%) | **1.250** | 251 (20,08%) |
| **Tập Huấn luyện Gốc (Train)** | 490 (13,02%) | 251 (6,67%) | 8 (0,21%) | 3.014 (80,10%) | **3.763** | 749 (19,90%) |

### 3.2 Ma trận hỗ trợ dữ liệu theo 5 miền công nghiệp (P2 Primary)

Phân bổ chi tiết số lượng mẫu thực tế theo miền thao tác `folder_domain` trên toàn bộ không gian P2 ($N=5.013$):

| Miền công nghiệp (`folder_domain`) | Level 01 | Level 02 | Level 03 | Level 04 | Tổng mẫu ($N_d$) | Tổng Anomaly ($N_{\text{anom}, d}$) | Số lớp hiện diện ($K_d$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`coal_conveyor`** (Băng chuyền than) | 169 | 83 | 4 | 865 | **1.121** | 256 (22,84%) | 4 / 4 |
| **`metallurgy`** (Luyện kim) | 8 | **0** | 1 | 711 | **720** | **9** (1,25%) | **3 / 4** (Thiếu L02) |
| **`oil_chemical`** (Hóa dầu) | 304 | 57 | **0** | 662 | **1.023** | 361 (35,29%) | **3 / 4** (Thiếu L03) |
| **`power`** (Trạm biến áp điện) | 33 | 68 | 1 | 767 | **869** | 102 (11,74%) | 4 / 4 |
| **`tunnel`** (Hầm đường bộ) | 145 | 118 | 9 | 1.008 | **1.280** | 272 (21,25%) | 4 / 4 |
| **Toàn bộ P2 (Pooled Total)** | **659** | **326** | **15** | **4.013** | **5.013** | **1.000** (19,95%) | 4 / 4 |

### 3.3 Hạn chế đặc thù tại tập test chính thức (P1 Official Test)

| Miền công nghiệp | P1 Level 01 | P1 Level 02 | P1 Level 03 | P1 Level 04 | P1 Tổng ($N$) | P1 Anomaly ($N_{\text{anom}}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `coal_conveyor` | 42 | 21 | 2 | 216 | 281 | 65 |
| **`metallurgy`** | **0** | **0** | **0** | **177** | **177** | **0 (0,0%)** |
| `oil_chemical` | 76 | 14 | **0** | 166 | 256 | 90 |
| `power` | 8 | 17 | 1 | 192 | 218 | 26 |
| `tunnel` | 43 | 23 | 4 | 248 | 318 | 70 |

### 3.4 Các hệ quả phương pháp luận bắt buộc

1. **Lớp Level 03 cực kỳ hiếm ($N=15$ toàn bộ dataset, chiếm 0,3%):**
   - Trong P2, `oil_chemical` có đúng 0 mẫu Level03; `metallurgy` và `power` mỗi miền chỉ có đúng 1 mẫu Level03.
   - Trong P1 test, `oil_chemical` và `metallurgy` đều có 0 mẫu Level03.
   - Mọi chỉ số tính riêng cho Level03 ở cấp từng miền đều chịu phương sai cực đại hoặc không xác định.
2. **Miền Luyện kim (`metallurgy`) thiếu hụt dữ liệu bất thường trầm trọng:**
   - Tại P1 test: $N_{\text{anomaly}} = 0$. Mọi chỉ số liên quan đến phát hiện bất thường (Anomaly Recall, Anomaly FNR, L01 Recall, L02 Recall, L03 Recall) đều là **không xác định (`UNDEFINED` / $\frac{0}{0}$)**.
   - Tại P2: $N_{\text{anomaly}} = 9$, không có mẫu Level02 ($N_{\text{L02}} = 0$).
   - Nếu xét phân tích độ nhạy tái phân bổ theo văn bản (Sensitivity B): $8/9$ mẫu Anomaly chuyển sang `oil_chemical`, miền `metallurgy` chỉ còn đúng $N_{\text{anomaly}} = 1$.
3. **Cảnh báo không so sánh cơ học:**
   - Tuyệt đối không giả định các chỉ số trung bình 4 lớp (`4-class macro metrics`) giữa các miền công nghiệp có thể so sánh trực tiếp với nhau, bởi vì hai miền (`metallurgy` và `oil_chemical`) không có đủ 4 lớp hỗ trợ trong tập ground truth.

---

## 4. Classification Metrics

Nhiệm vụ phân loại an toàn trong SafeShift yêu cầu mô hình gán nhãn mỗi ảnh vào một trong 4 cấp độ an toàn: $y \in \mathcal{C} = \{\text{Level01}, \text{Level02}, \text{Level03}, \text{Level04}\}$.

### 4.1 Định nghĩa toán học các chỉ số ứng viên

Giả sử ma trận nhầm lẫn 4 lớp được biểu diễn bởi $C \in \mathbb{R}^{4 \times 4}$, trong đó $C_{i, j}$ là số lượng mẫu có nhãn chuẩn là lớp $i$ và được mô hình dự đoán là lớp $j$.
Đối với từng lớp $c \in \mathcal{C}$:
- True Positives: $\text{TP}_c = C_{c, c}$
- False Positives: $\text{FP}_c = \sum_{i \neq c} C_{i, c}$
- False Negatives: $\text{FN}_c = \sum_{j \neq c} C_{c, j}$
- Ground Truth Support: $N_c = \text{TP}_c + \text{FN}_c = \sum_{j} C_{c, j}$

#### A. Balanced Accuracy (Macro-Recall)
Balanced Accuracy là trung bình số học không trọng số của độ thu hồi (recall) trên tất cả các lớp có trong không gian đánh giá:
$$\text{Balanced Accuracy} = \frac{1}{|\mathcal{C}_{\text{eval}}|} \sum_{c \in \mathcal{C}_{\text{eval}}} \text{Recall}_c = \frac{1}{|\mathcal{C}_{\text{eval}}|} \sum_{c \in \mathcal{C}_{\text{eval}}} \frac{\text{TP}_c}{\text{TP}_c + \text{FN}_c}$$

- *Ưu điểm:* Đo lường trực tiếp khả năng bao phủ của mô hình trên từng cấp độ an toàn; hoàn toàn không bị chi phối bởi việc lớp Level04 chiếm tới 80% dữ liệu; có ý nghĩa trực quan rõ ràng đối với an toàn công nghiệp (mỗi cấp nguy cơ được đối xử bình đẳng).
- *Nhược điểm:* Không tính đến dương tính giả ($\text{FP}_c$). Nếu một mô hình thiên vị dự đoán bừa bãi một lớp hiếm, Balanced Accuracy của lớp đó tăng mà không bị phạt ở mẫu số của chính lớp đó.

#### B. Macro-F1 (Unweighted Mean of Per-Class F1)
Macro-F1 là trung bình số học không trọng số của chỉ số F1 trên từng lớp:
$$\text{Macro-F1} = \frac{1}{|\mathcal{C}_{\text{eval}}|} \sum_{c \in \mathcal{C}_{\text{eval}}} \text{F1}_c, \quad \text{với } \text{F1}_c = \frac{2 \cdot \text{Precision}_c \cdot \text{Recall}_c}{\text{Precision}_c + \text{Recall}_c} = \frac{2 \cdot \text{TP}_c}{2 \cdot \text{TP}_c + \text{FP}_c + \text{FN}_c}$$
Quy ước kỹ thuật bắt buộc: Nếu $\text{TP}_c + \text{FP}_c = 0$ (mô hình không bao giờ dự đoán lớp $c$), đặt $\text{Precision}_c = 0.0$. Nếu $\text{TP}_c = 0$, đặt $\text{F1}_c = 0.0$.

- *Ưu điểm:* Cân bằng đồng thời cả hai yếu tố: bỏ sót nguy cơ ($\text{FN}$) và báo động giả ($\text{FP}$). Ngăn ngừa mô hình "ăn gian" recall bằng cách dự đoán ồ ạt lớp hiếm.
- *Nhược điểm:* Cực kỳ nhạy cảm và trừng phạt rất nặng khi một lớp hiếm có $N_c$ rất nhỏ bị $\text{TP}_c = 0$ (khi đó $\text{F1}_c = 0$, làm giảm đáng kể Macro-F1; với 4 lớp, class đó mất toàn bộ 1/4 contribution của nó).

#### C. Per-Class Recall, Precision, và F1
Báo cáo độc lập bộ 3 chỉ số cho từng lớp:
$$\text{Recall}_c = \frac{\text{TP}_c}{N_c}, \quad \text{Precision}_c = \frac{\text{TP}_c}{\text{TP}_c + \text{FP}_c}, \quad \text{F1}_c = \frac{2 \cdot \text{Precision}_c \cdot \text{Recall}_c}{\text{Precision}_c + \text{Recall}_c}$$
- *Vai trò:* Cung cấp bức tranh giải phẫu chi tiết, giải thích nguồn gốc của sự biến động trong các chỉ số vĩ mô.

#### D. Ma trận nhầm lẫn chuẩn hóa (Normalized Confusion Matrix)
Trình bày ma trận chuẩn hóa theo hàng (chia cho $N_c$ để phản ánh tỷ lệ phần trăm dự đoán theo từng nhãn thực tế). Cung cấp thông tin trực quan về các hướng nhầm lẫn nghiêm trọng (ví dụ: Level01 bị nhầm sang Level04 so với nhầm sang Level02).

#### E. Raw Accuracy (Micro-Accuracy)
$$\text{Raw Accuracy} = \frac{\sum_{c} \text{TP}_c}{\sum_{c} N_c}$$
- *Đánh giá phản biện:* Trong bộ dữ liệu InspecSafe-V1, lớp `Level04` chiếm 80,05% ở P2 và 79,92% ở P1. Một mô hình tầm thường chỉ xuất ra nhãn `"Level04"` cho 100% trường hợp sẽ đạt Raw Accuracy lên tới **80,0%**, dù hoàn toàn thất bại trong việc phát hiện 1.000 nguy cơ an toàn.
- *Quy tắc:* **Raw Accuracy TUYỆT ĐỐI KHÔNG ĐƯỢC DÙNG LÀM CHỈ SỐ CHÍNH (PRIMARY METRIC)**. Chỉ số này chỉ được trình bày với vai trò **mô tả phụ trợ (descriptive only)** để đối chiếu với bài báo gốc.

### 4.2 Đánh giá cặp chỉ số chính: Macro-F1 và Balanced Accuracy

| Tiêu chí | Raw Accuracy | Balanced Accuracy | Macro-F1 | Per-Class Metrics |
| :--- | :---: | :---: | :---: | :---: |
| **Kháng mất cân bằng lớp (80% Normal)** | Kém (Bị bóp méo hoàn toàn) | Rất cao (Đẳng trọng số) | Rất cao (Đẳng trọng số) | Tối đa (Tách rời từng lớp) |
| **Phạt báo động giả ($\text{FP}$)** | Có (trên toàn cục) | Không (chỉ đo Recall) | Có (thông qua Precision) | Có |
| **Phạt bỏ sót nguy cơ ($\text{FN}$)** | Rất yếu với lớp hiếm | Rất mạnh (đối xử bình đẳng) | Rất mạnh | Rất mạnh |
| **Độ nhạy với lớp siêu hiếm ($N=15$)** | Không đáng kể | Cao ($\pm 6,67\%$ trên L03) | Rất cao | Khu trú tại lớp L03 |
| **Vai trò đề xuất** | **Mô tả phụ** | **Chỉ số chính 1 (Co-Primary)** | **Chỉ số chính 2 (Co-Primary)** | **Chẩn đoán bắt buộc** |

**Khuyến nghị phương pháp luận:**
SafeShift đề xuất áp dụng **Balanced Accuracy** và **Macro-F1** làm **hai chỉ số chính song hành (Primary Co-Metrics)** cho bài toán phân loại 4 lớp. Sự kết hợp này bổ sung cho nhau: Balanced Accuracy đo lường năng lực bao quát an toàn không phụ thuộc tần suất xuất hiện, trong khi Macro-F1 bảo đảm mô hình duy trì độ đặc hiệu và không tạo ra tỷ lệ báo động giả mất kiểm soát.

---

## 5. Safety-Critical FNR/FPR

Trong môi trường công nghiệp thực tế, chi phí của các dạng sai số là phi đối xứng cực đoan:
- **Âm tính giả (False Negative — Bỏ sót nguy cơ):** Một sự cố rò rỉ khí độc, ngọn lửa trần hay người ngã bị bỏ qua có thể dẫn đến tai nạn thảm khốc, tử vong và đình trệ toàn bộ nhà máy.
- **Dương tính giả (False Positive — Báo động nhầm):** Một cảnh báo sai chỉ dẫn đến việc cử người kiểm tra lại hoặc điều động robot kiểm tra xác minh.

Do đó, các chỉ số tỷ lệ sai sót an toàn trọng yếu (Safety-Critical Error Rates) phải được định nghĩa tường minh và tuyệt đối không được gộp lẫn.

```
                  ┌────────────────────────────────────────────────────────┐
                  │          PHÂN TẦNG CHỈ SỐ SAI SỐ AN TOÀN TRỌNG YẾU     │
                  └────────────────────────────────────────────────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
        ┌─────────────────────────┐                       ┌─────────────────────────┐
        │  TRACK A: BINARY ANOMALY│                       │  TRACK B: LEVEL01 OVR   │
        │    DETECTION (P/N)      │                       │  (CRITICAL HAZARD OVR)  │
        └─────────────────────────┘                       └─────────────────────────┘
          Positive: L01 + L02 + L03                         Positive: Level01 Only
          Negative: Level04 (Normal)                        Negative: L02 + L03 + L04
                     │                                                 │
          ┌──────────┴──────────┐                           ┌──────────┴──────────┐
          ▼                     ▼                           ▼                     ▼
     Anomaly FNR           Anomaly FPR                  Level01 FNR           Level01 FPR
     (Bỏ sót nguy cơ)     (Báo động nhầm)               (Bỏ sót/Hạ cấp        (Báo động nguy cơ
                                                         nguy cơ cấp 1)        cấp 1 giả)
```

### 5.1 Track A — Phát hiện bất thường nhị phân (Binary Anomaly Detection)

Hợp nhất 4 cấp độ thành bài toán nhị phân giữa Nguy hiểm và Bình thường:
- **Lớp Dương tính (Positive Class — $\mathcal{P}_{\text{anom}}$):** Gồm toàn bộ các mẫu có nguy cơ an toàn: $\text{Level01} \cup \text{Level02} \cup \text{Level03}$. ($N_{\text{pos}} = 1.000$ ở P2; $N_{\text{pos}} = 251$ ở P1).
- **Lớp Âm tính (Negative Class — $\mathcal{N}_{\text{anom}}$):** Các mẫu an toàn bình thường: $\text{Level04}$. ($N_{\text{neg}} = 4.013$ ở P2; $N_{\text{neg}} = 999$ ở P1).

Từ đó, xác lập hai chỉ số tác nghiệp chính thức:

#### 1. Anomaly False Negative Rate ($\text{FNR}_{\text{anomaly}}$ — Tỷ lệ bỏ sót nguy cơ):
Tỷ lệ các ảnh có nguy cơ thực sự nhưng mô hình lại dự đoán sai là an toàn bình thường (`Level04`):
$$\text{FNR}_{\text{anomaly}} = \frac{\text{FN}_{\text{anomaly}}}{N_{\text{pos}}} = \frac{\sum_{i \in \mathcal{P}_{\text{anom}}} \mathbb{I}(\hat{y}_i = \text{Level04})}{N_{\text{anomaly}}} = 1 - \text{Recall}_{\text{anomaly}}$$
*Ý nghĩa an toàn:* Đây là chỉ số rủi ro nguy hiểm nhất của hệ thống giám sát. $\text{FNR}_{\text{anomaly}}$ càng cao, rủi ro tai nạn thảm khốc bị bỏ lọt càng lớn.

#### 2. Anomaly False Positive Rate ($\text{FPR}_{\text{anomaly}}$ — Tỷ lệ báo động nhầm):
Tỷ lệ các ảnh bình thường (`Level04`) bị mô hình gán nhãn nhầm vào bất kỳ mức nguy hiểm nào:
$$\text{FPR}_{\text{anomaly}} = \frac{\text{FP}_{\text{anomaly}}}{N_{\text{neg}}} = \frac{\sum_{i \in \mathcal{N}_{\text{anom}}} \mathbb{I}(\hat{y}_i \in \{\text{Level01, Level02, Level03}\})}{N_{\text{normal}}}$$
*Ý nghĩa vận hành:* Phản ánh tần suất gây phiền nhiễu cho đội ngũ vận hành và chi phí điều tra không cần thiết.

### 5.2 Track B — Phân loại nguy cơ nghiêm trọng Level01 (Level01 One-vs-Rest)

Trong hệ thống phân loại của InspecSafe, `Level01` đại diện cho các sự cố nguy hiểm nghiêm trọng nhất, đe dọa trực tiếp tính mạng hoặc an toàn cháy nổ tức thì (ngọn lửa trần, khói dày đặc, người nằm bất động). Việc phân tích riêng lớp này là bắt buộc:
- **Lớp Dương tính (Positive Class):** $\text{Level01}$ ($N=659$ ở P2; $N=169$ ở P1).
- **Lớp Âm tính (Negative Class):** $\text{Level02} \cup \text{Level03} \cup \text{Level04}$ ($N=4.354$ ở P2; $N=1.081$ ở P1).

Từ đó xác lập:
#### 1. Critical Hazard Recall ($\text{Recall}_{\text{L01}}$) và Level01 FNR ($\text{FNR}_{\text{L01}}$):
$$\text{Recall}_{\text{L01}} = \frac{\text{TP}_{\text{L01}}}{N_{\text{Level01}}}$$
$$\text{FNR}_{\text{L01}} = 1 - \text{Recall}_{\text{L01}} = \frac{\sum_{i \in \text{Level01}} \mathbb{I}(\hat{y}_i \neq \text{Level01})}{N_{\text{Level01}}}$$

#### 2. Phân rã sai số Level01 (Level01 Error Decomposition):
Trong $\text{FNR}_{\text{L01}}$, cần phân định rõ hai loại sai số có mức độ nghiêm trọng khác nhau:
- **Bỏ sót hoàn toàn thành bình thường (`Critical Miss`):** $\hat{y}_i = \text{Level04}$ (nguy hiểm tột độ).
  $$\text{MissRate}_{\text{L01}\rightarrow\text{L04}} = \frac{\sum_{i \in \text{Level01}} \mathbb{I}(\hat{y}_i = \text{Level04})}{N_{\text{Level01}}}$$
- **Hạ cấp mức độ nguy cơ (`Critical Downgrade`):** $\hat{y}_i \in \{\text{Level02, Level03}\}$ (vẫn phát hiện có bất thường nhưng đánh giá thấp mức độ nghiêm trọng).
  $$\text{DowngradeRate}_{\text{L01}\rightarrow\{\text{L02, L03}\}} = \frac{\sum_{i \in \text{Level01}} \mathbb{I}(\hat{y}_i \in \{\text{Level02, Level03}\})}{N_{\text{Level01}}}$$

> [!WARNING]
> **Quy tắc cấm tuyệt đối:** Không bao giờ được cộng gộp, thay thế hoặc dùng từ viết tắt "FNR" một cách mơ hồ. Báo cáo bắt buộc phải ghi rõ: **$\text{FNR}_{\text{anomaly}}$** hoặc **$\text{FNR}_{\text{L01}}$** kèm mẫu số cụ thể.

---

## 6. Per-Domain Missing-Class Policy

Một trong những thách thức phương pháp luận lớn nhất của SafeShift là việc các miền công nghiệp trong InspecSafe-V1 không có sự hỗ trợ đầy đủ của cả 4 cấp độ an toàn:
- Miền `metallurgy` ở P2 hoàn toàn thiếu `Level02` ($N_{\text{L02}} = 0$).
- Miền `oil_chemical` ở P2 hoàn toàn thiếu `Level03` ($N_{\text{L03}} = 0$).
- Miền `metallurgy` ở P1 test hoàn toàn không có mẫu Anomaly nào ($N_{\text{anom}} = 0$).

### 6.1 So sánh ba phương án chính sách

#### Phương án A — Support-Only Macro Averaging (Chỉ tính trung bình trên các lớp hiện diện)
Công thức tính chỉ số trung bình của miền $d$ chỉ lấy mẫu số là số lớp có mẫu thật ($K_d$):
$$M_d = \frac{1}{|C_d|} \sum_{c \in C_d} M_{c, d}, \quad \text{với } C_d = \{c \in \mathcal{C} \mid N_{c, d} > 0\}$$
- *Hệ quả:* Miền `coal_conveyor`, `power`, `tunnel` được tính trên 4 lớp ($K=4$); trong khi `metallurgy` và `oil_chemical` được tính trên 3 lớp ($K=3$).
- *Phản biện khoa học:* Phương án này dẫn đến ngụy biện so sánh: các miền đang được chấm điểm trên các đề bài khác nhau! Một mô hình có thể đạt Macro-F1 cao ở `oil_chemical` đơn giản vì miền này không bị kéo tụt bởi lớp khó `Level03`.

#### Phương án B — Fixed 4-Class Requirement (Yêu cầu cố định 4 lớp, gán NA khi thiếu)
Chỉ số 4 lớp tổng hợp xuyên miền yêu cầu bắt buộc phải có đầy đủ 4 lớp. Nếu một miền thiếu bất kỳ lớp nào trong ground truth, chỉ số tổng hợp chính của miền đó được ghi là **`NA` (Not Applicable / Undefined)**.
- *Ưu điểm:* Đảm bảo tính nhất quán tuyệt đối về định nghĩa toán học của bài toán 4 lớp.
- *Nhược điểm:* Triệt tiêu khả năng tổng kết bằng một con số cho `metallurgy` và `oil_chemical` ở P2, khiến bảng tổng hợp bị khuyết 40% số miền.

#### Phương án C — Dual-Layer Support-Aware Policy (Chính sách hai tầng có kiểm soát hỗ trợ — ĐƯỢC CHỌN)
SafeShift đề xuất kiến trúc báo cáo hai tầng rõ rệt:

1. **Tầng 1 — Báo cáo mô tả có gắn cờ hỗ trợ (Support-Aware Descriptive Reporting):**
   - Vẫn cho phép tính và trình bày chỉ số vĩ mô trên các lớp hiện diện, nhưng **bắt buộc phải hiển thị rõ ký hiệu số lớp hỗ trợ** (ví dụ: $\text{Macro-F1}_{(K=3)}$ hoặc $\text{Balanced Accuracy}_{(K=3)}$).
   - Đi kèm chú thích cảnh báo phương pháp luận: *Chỉ số này không có giá trị so sánh trực tiếp với các miền có $K=4$*.
2. **Tầng 2 — Phân tích có điều kiện theo từng lớp làm mỏ neo so sánh chính (Class-Conditional Comparison as Primary Anchor):**
   - Khi so sánh giữa các miền, SafeShift căn cứ trên các chỉ số của **từng lớp cụ thể** mà các miền đều có hỗ trợ:
     - So sánh `Recall(Level04, d)` trên cả 5 miền (mẫu số đều $N \ge 662$).
     - So sánh `Recall(Level01, d)` trên các miền có hỗ trợ (công bố mẫu số thực tế, ví dụ metallurgy $N=8$).
     - So sánh Binary Anomaly Recall / FNR trên các miền có dữ liệu bất thường.
3. **Quy tắc cấm tuyệt đối:** Không bao giờ sử dụng chỉ số tổng hợp của một miền thiếu lớp ($K < 4$) để xếp hạng hay tuyên bố miền đó là "tốt nhất" hoặc "tệ nhất".

---

## 7. Cross-Domain Robustness Metrics

Giảng viên hướng dẫn yêu cầu báo cáo chỉ số **Cross-Domain Drop** (Mức suy giảm hiệu năng xuyên miền). Tuy nhiên, việc áp dụng máy móc các công thức tổng hợp sẽ dẫn đến kết luận sai lệch do hiện tượng nhiễu thành phần nhãn (label composition confounding).

### 7.1 Mỏ neo chính: Phân tích xuyên miền theo từng lớp (Class-Conditional Domain Analysis)

Thay vì dựa vào một chỉ số tổng hợp bị bóp méo bởi tỷ lệ pha trộn lớp giữa các miền, SafeShift xác lập **Class-Conditional Domain Analysis** làm **mỏ neo chính (Primary Anchor)** cho câu hỏi nghiên cứu RQ1:

1. **Độ thu hồi theo từng lớp cho từng miền (Per-Class Domain Recall):**
   $$\text{Recall}(c, d) = \frac{\text{TP}_{c, d}}{N_{c, d}}$$
   chỉ tính khi miền $d$ có ground-truth support cho lớp $c$ ($N_{c, d} > 0$).
2. **Class-Conditional Pooled-to-Domain Gap (Độ lệch gộp - miền theo từng lớp):**
   $$\Delta(c, d) = \text{Recall}_{c, \text{pooled}} - \text{Recall}_{c, d}$$
   Đo lường độ suy giảm hoặc cải thiện của mô hình trên cùng một lớp an toàn $c$ khi chuyển từ dữ liệu tổng thể sang phân xưởng cụ thể $d$.
3. **Class-Conditional Domain Spread / Range (Độ phân tán xuyên miền theo từng lớp):**
   $$\text{Spread}(c) = \max_{d \in \mathcal{D}_c} \text{Recall}(c, d) - \min_{d \in \mathcal{D}_c} \text{Recall}(c, d)$$
   với $\mathcal{D}_c = \{d \mid N_{c, d} > 0\}$. Đồng thời báo cáo khoảng cách bất lợi lớn nhất (Worst Adverse Gap per class).

> [!IMPORTANT]
> **Giới hạn phương pháp luận về loại trừ yếu tố gây nhiễu:**
> Việc phân tích theo từng lớp (`Class-Conditional Analysis`) giúp **giảm thiểu hiện tượng nhiễu do tần suất nhãn (`reduces class-prevalence confounding`)**, nhưng **KHÔNG LOẠI BỎ ĐƯỢC (`does NOT remove`)** các yếu tố gây nhiễu khác như: thành phần chủng loại nguy cơ (`hazard composition`), nền tảng robot tuần tra (`robot platform`), góc đặt camera (`viewpoint`), bối cảnh ánh sáng (`scene/lighting`), hoặc các đặc trưng vật lý riêng biệt của từng phân xưởng.

### 7.2 Các chỉ số chẩn đoán phụ trợ (Secondary / Diagnostic Metrics)

1. **Balanced Accuracy Spread trên tập miền so sánh được (Secondary / Comparable-Subset Diagnostic):**
   $$\text{Spread}(\text{BalAcc})_{K=4} = \max_{d \in \{\text{coal, power, tunnel}\}} \text{BalAcc}_d - \min_{d \in \{\text{coal, power, tunnel}\}} \text{BalAcc}_d$$
   *Vai trò:* Đây là chỉ số chẩn đoán trên tập con các miền có đủ 4 lớp hỗ trợ, **KHÔNG PHẢI là đại diện duy nhất cho toàn bộ bài toán RQ1 trên cả 5 miền**.
2. **Binary Anomaly Recall Spread (Diagnostic):**
   Đo lường độ chênh lệch Anomaly Recall giữa các miền có hỗ trợ bất thường. Đây chỉ là chỉ số chẩn đoán, bởi vì việc gộp chung Level01/Level02/Level03 thành Anomaly vẫn bị nhiễu bởi thành phần mức độ nghiêm trọng khác nhau giữa các phân xưởng.
3. **Chuẩn hóa thuật ngữ:** Bắt buộc sử dụng cụm từ **"Cross-Domain Robustness Drop / Gap"** (Độ suy giảm / độ lệch bền vững xuyên miền). **TUYỆT ĐỐI KHÔNG DÙNG** thuật ngữ **"Domain Generalization Drop"** vì Seminar không thực hiện huấn luyện trên miền nguồn.

### 7.3 Phân tích phân tầng nguy cơ theo RQ2 (RQ2 Hazard Strata Metrics & Multi-Stratum Overlap)

Câu hỏi nghiên cứu RQ2 yêu cầu làm rõ sự tập trung sai số của mô hình VLM theo từng cấp độ an toàn và từng phân tầng nguy cơ đặc thù trong công nghiệp. Kế thừa 7 Phân tầng Nguy cơ Gom nhóm Ứng viên (`Candidate Grouped Hazard Strata` A–G) đã được phê duyệt tại D6, SafeShift xác lập hệ thống chỉ số đo lường hiệu năng an toàn chuyên biệt cho từng tầng nguy cơ:

#### A. Bộ 4 chỉ số an toàn cốt lõi cho từng tầng nguy cơ
Đối với mỗi phân tầng nguy cơ $s \in \{\text{Strata A}, \dots, \text{Strata G}\}$ gồm $N_s$ mẫu ảnh:

1. **Tỷ lệ sai số cấp an toàn chính xác (Exact Safety-Level Error Rate):**
   $$\text{ErrorRate}_{\text{exact}}(s) = \frac{\sum_{i \in \text{Strata}_s} \mathbb{I}(\hat{y}_i \neq y_i)}{N_s}$$
   Đo lường tỷ lệ các mẫu trong tầng $s$ bị mô hình dự đoán lệch khỏi cấp an toàn thực tế (dù là nhầm giữa các mức nguy cơ hay nhầm sang bình thường).

2. **Tỷ lệ bỏ sót nguy cơ thành bình thường (Anomaly-to-Normal Miss Rate):**
   $$\text{MissRate}_{\text{anom}\rightarrow\text{norm}}(s) = \frac{\sum_{i \in \text{Strata}_s} \mathbb{I}(\hat{y}_i = \text{Level04})}{N_s}$$
   Chỉ số rủi ro vận hành then chốt: Đo lường tỷ lệ sự cố nguy hiểm thuộc tầng $s$ bị mô hình bỏ lọt hoàn toàn thành trạng thái an toàn bình thường (`Level04`).

3. **Độ thu hồi nguy cơ nghiêm trọng và Tỷ lệ bỏ sót thảm khốc (Level01 Recall & Critical Miss Rate):**
   Áp dụng cho các phân tầng có chứa mẫu nguy cơ cấp 1 ($N_{s, \text{L01}} > 0$, bao gồm toàn bộ các phân tầng từ A đến G):
   $$\text{Recall}_{\text{L01}}(s) = \frac{\sum_{i \in \text{Strata}_s, y_i = \text{Level01}} \mathbb{I}(\hat{y}_i = \text{Level01})}{N_{s, \text{L01}}}$$
   $$\text{CriticalMissRate}_{\text{L01}\rightarrow\text{L04}}(s) = \frac{\sum_{i \in \text{Strata}_s, y_i = \text{Level01}} \mathbb{I}(\hat{y}_i = \text{Level04})}{N_{s, \text{L01}}}$$
   Phân định rõ rủi ro bỏ sót các sự cố đe dọa tính mạng (như cháy, khói, người ngã) trong từng phân tầng cụ thể.

4. **Phân bố nhầm lẫn mức an toàn (Safety Confusion Distribution):**
   Bảng phân bố tần suất 4 mức $\{\text{Level01}, \text{Level02}, \text{Level03}, \text{Level04}\}$ của dự đoán $\hat{y}$ trên từng phân tầng nguy cơ, chỉ ra khuynh hướng hạ cấp mức rủi ro (risk downgrade).

#### B. Cảnh báo phương pháp luận: Giao thoa đa nguy cơ và Tính không cộng gộp mẫu
> [!WARNING]
> **Quy tắc không cộng gộp mẫu giữa các tầng nguy cơ (Non-Additive Sample Counts):**
> - **Cơ sở thực chứng về mẫu đa nguy cơ (Multi-Hazard Samples):** Theo kiểm toán W2.3 (D6), phân bố số lượng hazard atoms trên mỗi mẫu ảnh Anomaly là: 1 atom: 488 mẫu; 2 atoms: 287 mẫu; 3 atoms: 181 mẫu; 4 atoms: 37 mẫu; 5 atoms: 7 mẫu. Do đó, có chính xác **$287 + 181 + 37 + 7 = \mathbf{512\text{ mẫu ảnh}}$** (chiếm **$51,2\%$** tổng số 1.000 mẫu Anomaly) chứa từ 2 nguyên tử nguy cơ trở lên.
> - **Cơ chế giao thoa giữa các tầng (Multi-Stratum Overlap):** Một mẫu đa nguy cơ CÓ THỂ thuộc về đồng thời nhiều phân tầng gom nhóm nếu các atoms trong ảnh ánh xạ sang các tầng khác nhau (ví dụ: mẫu chứa đồng thời `OPEN_FLAME` và `NO_GLOVES` sẽ vừa thuộc Strata A `FIRE_AND_SMOKE` vừa thuộc Strata B `PPE_ABSENCE`).
> - **Bằng chứng số lượng thành viên phân tầng (Grouped-Strata Sample Memberships):** Tổng số lượt mẫu thành viên trên 7 phân tầng là:
>   $$200 (\text{A}) + 545 (\text{B}) + 247 (\text{C}) + 134 (\text{D}) + 211 (\text{E}) + 34 (\text{F}) + 10 (\text{G}) = \mathbf{1.381\text{ memberships}}$$
>   trên đúng 1.000 mẫu Anomaly độc nhất. Con số 1.381 này là minh chứng toán học trực tiếp xác nhận các tập mẫu của 7 phân tầng có sự giao thoa đáng kể.
> - **Các hệ quả phương pháp luận bắt buộc:**
>   1. **Counts not additive:** Số lượng mẫu giữa các tầng tuyệt đối không có tính cộng dồn ($\sum N_s \neq 1.000$).
>   2. **Trùng lặp mẫu:** Cùng một ảnh xuất hiện trong nhiều phân tầng khác nhau.
>   3. **Thiếu tính độc lập thống kê:** Các ước lượng chỉ số giữa các phân tầng không độc lập về mặt thống kê (`strata estimates are not statistically independent`).
>   4. **Cấm cộng dồn sai số:** Tuyệt đối không cộng dồn số lỗi hoặc tính trung bình gộp các chỉ số giữa 7 tầng để đại diện cho hiệu năng tổng thể của dataset (`do not sum errors across strata`). Mọi phép đo phải được tính toán độc lập trên từng tầng riêng biệt.

---

## 8. Worst-Domain Reporting Policy

Giảng viên đặc biệt quan tâm tới hiệu năng ở "miền kém nhất" (`worst-domain performance`). Tuy nhiên, việc so sánh máy móc giữa các miền có quy mô mẫu và mức độ hỗ trợ nhãn khác nhau sẽ dẫn đến ngụy biện thống kê.

### 8.1 Loại bỏ quy tắc ngưỡng $N \ge 30$ tùy ý

SafeShift chính thức **bãi bỏ việc áp dụng một quy tắc ngưỡng số học cơ học như $N_{\text{anomaly}} \ge 30$** để làm tiêu chuẩn khoa học phân định quyền tham gia xếp hạng, vì ngưỡng này không có căn cứ toán học nội tại trong bối cảnh dữ liệu quan sát.

Thay vào đó, SafeShift thiết lập quy trình báo cáo minh bạch và có điều kiện đối với Worst-Domain:
1. **Báo cáo toàn bộ các miền có chỉ số xác định toán học:** Mọi miền công nghiệp có metric tính được theo công thức toán học đều phải được trình bày đầy đủ trong bảng kết quả.
2. **Luôn công bố mẫu số thực nghiệm:** Mọi ô số liệu bắt buộc phải hiển thị rõ mẫu số $(k / N_d)$ hoặc cỡ mẫu $N_d$ tương ứng.
3. **Luôn công bố khoảng tin cậy / độ bất định:** Mọi con số hiệu năng từng miền phải đi kèm khoảng tin cậy bootstrap hoặc đánh giá độ bất định.
4. **Gắn cờ cảnh báo hỗ trợ thưa thớt (Sparse-Support Warning) cho Luyện kim:**
   - Dữ liệu thực chứng bất biến: Tại P2, `metallurgy` chỉ có $N_{\text{anomaly}} = 9$; theo phân tích độ nhạy văn bản, $N_{\text{anomaly}} = 1$; tại P1 test, $N_{\text{anomaly}} = 0$.
   - Miền `metallurgy` bắt buộc phải được gắn nhãn **`[Sparse-Support / Descriptive-Only]`** cho các chỉ số bất thường.
5. **Nguyên tắc báo cáo Worst-Domain:**
   - Chỉ được báo cáo: **"Giá trị số học quan sát thấp nhất trong số các miền có thể so sánh được" (`Observed numerical minimum among comparable domains`)**.
   - Bắt buộc phải công bố đi kèm: định nghĩa metric cụ thể, mức độ hỗ trợ nhãn, mẫu số thực tế, khoảng tin cậy, và lưu ý về tính so sánh được (`comparability caveat`).
   - **Tuyệt đối không đưa ra các tuyên bố xếp hạng mạnh (strong ranking claims)** khi các miền có mức độ hỗ trợ nhãn khác nhau hoặc khoảng tin cậy quá rộng chồng lấn nhau.

---

## 9. Direct Grounding Metrics

Đường đua **RQ3-A — Direct Object-Support Grounding** đánh giá năng lực của VLM trong việc khoanh vùng chính xác đối tượng vật lý trực tiếp làm bằng chứng cho khẳng định nguy cơ.

### 9.1 Cơ sở dữ liệu, định dạng hộp bao và Tập vùng GT ứng viên ($R_j$)

- **Quy mô tập đánh giá:** Theo Quyết định D6, toàn bộ tập dữ liệu có đúng **781 Direct atoms** phân bố trên **721 mẫu ảnh** thuộc `Direct-Support Sample Pool`.
- **Định dạng hộp bao chuẩn mực (D4):**
  $$\mathbf{b} = [x_{\min}, y_{\min}, x_{\max}, y_{\max}] \in [0.0, 1.0]$$
  với gốc tọa độ $(0, 0)$ ở góc trên bên trái, chuẩn hóa theo kích thước ảnh thực tế $(W, H)$.
- **Định nghĩa Tập vùng GT Ứng viên hỗ trợ ($R_j$ — Candidate Supporting GT Region Set):**
  Trong thực tế bối cảnh công nghiệp, một nguy cơ nguyên tử có thể tương ứng với nhiều nhãn đối tượng ứng viên, nhiều đa giác cùng nhãn, hoặc nhiều thực thể hỗ trợ phân tán trên ảnh (ví dụ: nhiều mảnh dị vật vương vãi, nhiều vũng dầu loang). Do đó, SafeShift bãi bỏ giả định ngầm cơ học "1 hazard atom = 1 GT box".
  
  Đối với mỗi Direct hazard atom $j$ trong một mẫu ảnh, tập các đa giác GT ứng viên hỗ trợ $R_j$ được xác định tất định từ bảng ánh xạ D6:
  $$R_j = \left\{ r \in \text{Polygons}(\text{sample}) \mid \text{label}(r) \in \text{CandidateLabels}(j) \right\}$$
  trong đó $\text{bbox}(r)$ là hộp bao suy biến toán học tất định $[x_{\min}, y_{\min}, x_{\max}, y_{\max}]$ của đa giác $r$.

- **Kết quả Kiểm toán Thực chứng Toàn diện trên 781 Direct Atoms:**
  - **Kiểm tra tính toàn vẹn (Sanity Check $|R_j| \ge 1$):** Đúng **781 / 781 Direct atoms (100,0%)** sở hữu ít nhất một đa giác đối tượng hỗ trợ hợp lệ trong tệp JSON gốc ($0$ trường hợp rỗng).
  - **Trường hợp Đơn vùng ($|R_j| = 1$):** Đúng **680 / 781 atoms (87,07%)** chỉ có duy nhất 1 đa giác hỗ trợ.
  - **Trường hợp Đa vùng ($|R_j| > 1$):** Đúng **101 / 781 atoms (12,93%)** chứa từ 2 đến 8 đa giác hỗ trợ độc lập trong cùng một ảnh.
  - **Phân rã chi tiết theo từng loại Hazard Atom:**
    - `FOREIGN_OBJECT` (109 atoms): 66 atoms có $|R_j|=1$; **43 atoms có $|R_j|>1$** (phân bố: 2 dị vật: 34; 3 dị vật: 1; 4 dị vật: 2; 5 dị vật: 1; 7 dị vật: 2; 8 dị vật: 3 mẫu).
    - `LIQUID_ON_GROUND` (122 atoms): 79 atoms có $|R_j|=1$; **43 atoms có $|R_j|>1$** (phân bố: 2 vũng: 32; 3 vũng: 4; 4 vũng: 5; 6 vũng: 2 mẫu).
    - `USE_MOBILE_PHONE` (165 atoms): 155 atoms có $|R_j|=1$; **10 atoms có $|R_j|>1$** (2 điện thoại: 8; 3 điện thoại: 2 mẫu).
    - `OPEN_FLAME` (117 atoms): 113 atoms có $|R_j|=1$; **4 atoms có $|R_j|>1$** (2 ngọn lửa: 4 mẫu).
    - `SMOKING` (118 atoms): 117 atoms có $|R_j|=1$; **1 atom có $|R_j|>1$** (2 điếu thuốc: 1 mẫu).
    - `SMOKE` (103 atoms): **103 / 103 atoms (100,0%)** có $|R_j|=1$.
    - `NONMOTORIZED_VEHICLE` (47 atoms direct): **47 / 47 atoms (100,0%)** có $|R_j|=1$.
  - **Hồ sơ Truy vết Nguồn gốc Kiểm toán (Direct Audit Provenance):**
    - Lệnh thực thi: `python scratch/audit_gt_regions.py`
    - Môi trường: Python 3.11.9, Windows 11 x64, workspace `d:\SafeShift`.
    - Thời điểm thực thi: `2026-09-17 05:22:14 UTC`.
    - Mã băm SHA-256 dữ liệu đầu vào: `7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`
    - Mã băm SHA-256 artifact D6 census (`data/manifests/w2_grounding_census.json`): `cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`
    - Mã băm SHA-256 script kiểm toán: `90c704af291fb34725b6a679f3bdb2a84d18297628c569497e34309ed49cee50`
    - *Ghi chú tái lập:* Script audit là tập lệnh scratch cục bộ (`local scratch script`), không commit vào Git repository. Dữ liệu audit được tính trực tiếp từ dataset thô cục bộ, không tuyên bố tái lập độc lập chỉ bằng Git repo thuần túy (`no repo-alone reproducibility claim`).

### 9.2 Trọng số cạnh và Các chỉ số định vị không gian

#### A. Trọng số cạnh IoU giữa Dự đoán và Nguy cơ Nguyên tử (Edge IoU Score)
Với một hộp bao dự đoán $\mathbf{b}_{\text{pred}}^p$ ($p \in \{1, \dots, P\}$) và một Direct hazard atom $j$ có tập vùng hỗ trợ $R_j$, điểm giao thoa trên diện tích hợp cực đại được định nghĩa là:
$$\text{IoU}(p, j) = \max_{r \in R_j} \text{IoU}\left(\mathbf{b}_{\text{pred}}^p, \text{bbox}(r)\right) = \max_{r \in R_j} \frac{\text{Area}\left(\mathbf{b}_{\text{pred}}^p \cap \text{bbox}(r)\right)}{\text{Area}\left(\mathbf{b}_{\text{pred}}^p \cup \text{bbox}(r)\right)}$$

#### B. Chuẩn hóa ba định nghĩa Mean IoU
Để đảm bảo tính nhất quán tuyệt đối trong báo cáo, SafeShift phân định rạch ròi ba định nghĩa Mean IoU:
1. **End-to-End Mean IoU (Chỉ số định vị liên tục chính — PRIMARY):**
   - Mẫu số: Toàn bộ 781 Direct atoms có thể đánh giá được.
   - Quy tắc gán điểm 0: Không nhận diện được nguy cơ = $\text{IoU} = 0.0$; không xuất hộp bao = $\text{IoU} = 0.0$; lỗi phân tích cú pháp = $\text{IoU} = 0.0$; hộp bao hợp lệ nhưng không ghép trúng GT atom = $\text{IoU} = 0.0$.
   - Phản ánh trung thực năng lực định vị tổng thể của mô hình trong thực tế.
2. **Parse-Conditional Mean IoU (Chẩn đoán theo điều kiện parse thành công):**
   - Mẫu số: Chỉ tính trên các đầu ra nguy cơ có tọa độ hộp bao parse thành công.
   - Quy tắc: Hộp bao parse thành công nhưng không giao thoa với GT **vẫn giữ nguyên $\text{IoU} = 0.0$**.
3. **Positive-Overlap Mean IoU (Chẩn đoán độ khít khi có giao thoa — DIAGNOSTIC ONLY):**
   - Mẫu số: Chỉ tính trên các cặp dự đoán đã khớp có $\text{IoU} > 0.0$.
   - Cảnh báo phương pháp luận: Chỉ mang tính chẩn đoán phụ trợ, có thiên lệch chọn mẫu (`selection bias`); tuyệt đối không gọi tập con này là "mô hình đã nhìn đúng đối tượng".
4. **Median IoU:** Báo cáo kèm theo để kháng ảnh hưởng của các giá trị ngoại lai cực đoan.

#### C. Localization Hit@$\tau$ (Độ nhạy phân ngưỡng xác định trước)
Một nguyên tử nguy cơ GT $j$ được coi là định vị trúng đích nếu tồn tại một hộp bao dự đoán $p$ được ghép cặp thành công theo Mode B đạt $\text{IoU}(p, j) \ge \tau$.
- **Hit@0.25:** Ngưỡng độ nhạy chính phản ánh định vị phân vùng có ý nghĩa.
- **Hit@0.50:** Ngưỡng độ nhạy khắt khe đối chiếu với chuẩn phát hiện đối tượng truyền thống.
- Cả hai ngưỡng này được **xác định trước khi xem kết quả mô hình (`pre-specified before model-result inspection`)** và không thay đổi sau khi quan sát kết quả. Loại bỏ mọi tuyên bố chưa được kiểm chứng về tính chuẩn mực phổ quát hay xác suất đoán ngẫu nhiên.

#### D. Pointing Hit chuẩn mực trên Đa giác GT gốc (Canonical Pointing Hit using Original Polygons)
Đo lường năng lực định hướng thị giác thô:
- Xác định điểm tâm của hộp bao dự đoán $p$:
  $$\mathbf{c}_{\text{pred}}^p = \left(\frac{x_{\min}^p + x_{\max}^p}{2}, \frac{y_{\min}^p + y_{\max}^p}{2}\right)$$
- **Định nghĩa chuẩn mực duy nhất:** Điểm tâm $\mathbf{c}_{\text{pred}}^p$ **phải nằm bên trong BẤT KỲ ĐA GIÁC GT GỐC NÀO** thuộc tập vùng ứng viên $R_j$:
  $$\text{PointingHit}(p, j) = \mathbb{I}\left(\exists r \in R_j \text{ sao cho } \mathbf{c}_{\text{pred}}^p \in \text{Polygon}(r)\right)$$
- *Căn cứ phương pháp luận:* Hộp bao derived bbox thường chứa các vùng nền trống xung quanh các vật thể phi lồi (như vũng chất lỏng loang hay ngọn lửa). Việc yêu cầu điểm tâm nằm trong đa giác gốc ngăn chặn việc tính điểm trúng đích vào vùng nền trống. Tuyệt đối không dùng derived bbox cho Pointing Hit.

### 9.3 Hai Chế độ Ghép cặp Tối ưu Hai phía Một-Một (Two Distinct Bipartite Matching Modes)

Để đảm bảo tính nhất quán toán học tuyệt đối giữa các chỉ số liên tục (Continuous Metrics) và các chỉ số phân ngưỡng (Thresholded Metrics), SafeShift xác lập **hai chế độ ghép cặp tối ưu hai phía một-một độc lập, tách biệt hoàn toàn và tuyệt đối không được trộn lẫn**:

#### Mode A — Continuous IoU Assignment (Gán ghép Liên tục Không áp ngưỡng)
Chế độ này được sử dụng độc quyền cho: **End-to-End Mean IoU**, **Median IoU**, và **Parse-Conditional Mean IoU**.
1. **Phạm vi ghép:** Chỉ ghép giữa các dự đoán $\{p\}$ và các Direct GT atoms $\{j\}$ trong cùng một mẫu ảnh và có **cùng loại nguy cơ (`within the same hazard atom class`)**.
2. **Trọng số cạnh:** Sử dụng điểm cạnh $\text{IoU}(p, j) = \max_{r \in R_j} \text{IoU}(\mathbf{b}_{\text{pred}}^p, \text{bbox}(r))$.
3. **Mục tiêu tối ưu hóa (Maximum Weight Bipartite Matching):**
   $$\max_{\mathcal{M}} \sum_{(p, j) \in \mathcal{M}} \text{IoU}(p, j)$$
   Tìm tập ghép cặp một-một $\mathcal{M}$ tối đa hóa tổng điểm IoU giữa các cạnh. **TUYỆT ĐỐI KHÔNG ÁP DỤNG BẤT KỲ NGƯỠNG $\tau$ NÀO** (mọi cạnh có $\text{IoU} > 0$ đều là ứng viên hợp lệ).
4. **Ràng buộc một-một:** Mỗi hộp bao dự đoán $p$ chỉ được gán tối đa cho 1 GT atom $j$; mỗi GT atom $j$ chỉ được nhận tối đa 1 hộp bao dự đoán $p$. Tuyệt đối không tái sử dụng hộp bao dự đoán cho nhiều GT atoms (`no predicted box reuse`).
5. **Quy tắc gán điểm 0 toán học:**
   - GT atom không có hộp bao dự đoán nào ghép cặp: Được gán $\text{IoU} = 0.0$.
   - Mô hình không nhận diện hoặc bỏ sót loại nguy cơ đó (`missing hazard prediction`): Mọi GT atom của nguy cơ đó đều nhận $\text{IoU} = 0.0$.
   - Lỗi cú pháp hoặc tọa độ parse thất bại: Toàn bộ GT atoms liên quan nhận $\text{IoU} = 0.0$ trong bài toán End-to-End.

#### Mode B — Thresholded Bipartite Matching (Ghép cặp Tối ưu Có phân ngưỡng tại $\tau$)
Chế độ này được sử dụng cho: **Hit@0.25**, **Hit@0.50**, **Evidence Precision / Recall / F1 (@0.25, @0.50)**, và **$\text{CGI}@\tau$** ($\tau \in \{0.25, 0.50\}$).
1. **Điều kiện cạnh hợp lệ:** Chỉ các cạnh thỏa mãn $\text{IoU}(p, j) \ge \tau$ mới được đưa vào đồ thị hai phía để ghép cặp.
2. **Mục tiêu tối ưu hóa cấp 1 (Maximum Cardinality):** Tối đa hóa số lượng cặp ghép hợp lệ $|\mathcal{M}_\tau|$ thỏa mãn ngưỡng $\tau$.
3. **Mục tiêu phân xử cấp 2 (Tie-break):** Trong số các phương án đạt cực đại số cặp ghép, chọn phương án tối đa hóa tổng điểm IoU: $\max \sum_{(p, j) \in \mathcal{M}_\tau} \text{IoU}(p, j)$.
4. **Ràng buộc:** Một-một nghiêm ngặt. Mọi hộp bao dự đoán vượt quá số lượng cặp ghép hoặc có $\text{IoU} < \tau$ đều tính là False Positive ($\text{FP}$). Mỗi GT atom ghép thành công tính là True Positive ($\text{TP}$).

> [!CAUTION]
> **Quy tắc phân định bắt buộc:** Mode A (đo lường hàm liên tục không ngưỡng để đánh giá độ khít tổng thể) và Mode B (phân định quyết định nhị phân có ngưỡng để đánh giá tỷ lệ trúng đích) phục vụ hai mục đích phương pháp luận hoàn toàn khác nhau. **TUYỆT ĐỐI KHÔNG ĐƯỢC TRỘN LẪN HOẶC DÙNG THAY THẾ CHO NHAU**.

---

## 10. Weak-Proxy Metrics

Đường đua **RQ3-B — Weak Proxy Grounding** xử lý **947 Weak-Proxy atoms** trên **608 mẫu ảnh** thuộc `Weak-Proxy Sample Pool`. 
- **Thành phần cấu thành chuẩn xác từ D6:** Khác với quan niệm sai lầm rằng hút thuốc hay điện thoại là proxy, `SMOKING` có tới 118 Direct (chỉ 2 Proxy) và `USE_MOBILE_PHONE` có 165 Direct (chỉ 2 Proxy). Tập Weak Proxy thực chất đại diện cho các vi phạm thiếu trang bị bảo hộ và trạng thái con người: `NO_GLOVES` (451 atoms), `NO_HELMET` (229 atoms), `NO_MASK` (199 atoms), `NONMOTORIZED_VEHICLE` (54 atoms — trường hợp JSON chỉ khoanh người điều khiển thay vì phương tiện), `PERSON_FALLEN` (10 atoms), cùng 2 atoms `USE_MOBILE_PHONE` và 2 atoms `SMOKING` bị thiếu nhãn trực tiếp.
- Đối tượng hỗ trợ không gian duy nhất có sẵn trong JSON là đa giác **`Person`**.

### 10.1 Bản chất ngụy biện nếu áp dụng IoU cho Weak Proxy

Trong dữ liệu InspecSafe-V1, khi công nhân vi phạm không đội mũ bảo hộ (`NO_HELMET`) hay không đeo găng tay (`NO_GLOVES`), annotator gốc **chỉ khoanh đa giác toàn thân người (`Person`)**, hoàn toàn không có hộp bao vùng đầu, bàn tay hay vật thể vắng mặt.
- Diện tích vùng đầu chỉ chiếm khoảng $10\% - 15\%$, và hai bàn tay chỉ chiếm khoảng $3\% - 5\%$ diện tích toàn thân người.
- Nếu mô hình VLM định vị chính xác vùng đầu hoặc bàn tay trần của người công nhân, diện tích giao nhau chỉ bằng diện tích bộ phận trong khi diện tích hợp bằng diện tích toàn thân, dẫn đến $\text{IoU} \approx 0,05 - 0,15$.
- Nếu áp dụng máy móc tiêu chí $\text{IoU} \ge 0.25$, mô hình định vị chính xác bộ phận vi phạm sẽ bị chấm là thất bại ($\text{IoU} < 0.25$), trong khi một mô hình chỉ biết khoanh bừa toàn thân người lại đạt điểm cao.

### 10.2 Hiện tượng Mập mờ Nhiều người (Multi-Person Ambiguity) và Kiểm toán Thực chứng

Một thách thức phương pháp luận nghiêm trọng trong InspecSafe-V1 là sự hiện diện của nhiều công nhân trong cùng một khung hình nhưng văn bản nguy cơ không định danh cá nhân cụ thể:
- **Kiểm toán thực chứng cấp độ Mẫu ($N=608$ Proxy Samples):**
  - **Đơn người ($|\text{Person}| = 1$):** Đúng **410 / 608 mẫu (67,43%)** chỉ có duy nhất 1 đa giác `Person`.
  - **Đa người ($|\text{Person}| > 1$):** Đúng **198 / 608 mẫu (32,57%)** chứa từ 2 đến 8 đa giác `Person` (phân bố: 2 người: 127 mẫu; 3 người: 44 mẫu; 4 người: 20 mẫu; 5 người: 1 mẫu; 6 người: 1 mẫu; 7 người: 3 mẫu; 8 người: 2 mẫu).
- **Kiểm toán thực chứng cấp độ Nguy cơ Nguyên tử ($N=947$ Proxy Atoms):**
  - Nằm trong ảnh đơn người: **614 / 947 atoms (64,84%)**.
  - Nằm trong ảnh đa người: **333 / 947 atoms (35,16%)**.
- **Hồ sơ Truy vết Nguồn gốc Kiểm toán (Weak-Proxy Audit Provenance):**
  - Lệnh thực thi: `python scratch/audit_gt_regions.py`
  - Môi trường: Python 3.11.9, Windows 11 x64, workspace `d:\SafeShift`.
  - Thời điểm thực thi: `2026-09-17 05:22:14 UTC`.
  - Mã băm SHA-256 dữ liệu đầu vào: `7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`
  - Mã băm SHA-256 artifact D6 census (`data/manifests/w2_grounding_census.json`): `cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`
  - Mã băm SHA-256 script kiểm toán: `90c704af291fb34725b6a679f3bdb2a84d18297628c569497e34309ed49cee50`
  - *Ghi chú tái lập:* Script audit là tập lệnh scratch cục bộ (`local scratch script`), không commit vào Git repository. Dữ liệu audit được tính trực tiếp từ dataset thô cục bộ, không tuyên bố tái lập độc lập chỉ bằng Git repo thuần túy (`no repo-alone reproducibility claim`).

Khi ảnh có từ 2 người trở lên, bộ dữ liệu không ghi rõ công nhân nào đang không đeo găng tay hay không đội mũ. Nếu quy ước máy móc, việc đánh giá sẽ bị tê liệt. Do đó, SafeShift thiết lập quy tắc chuẩn tắc: Một dự đoán được coi là nhất quán nếu nó trúng đích vào **bất kỳ đa giác người nào** trong ảnh, đồng thời thiết lập tên gọi chuẩn hóa và bài kiểm tra độ nhạy tương ứng.

### 10.3 Các chỉ số đo lường mức độ nhất quán vị trí

SafeShift xác lập hệ thống đo lường chuẩn mực cho Weak Proxy:

#### 1. Center-in-Proxy (Chỉ số chính — PRIMARY):
Kiểm tra xem tọa độ tâm của hộp bao dự đoán $\mathbf{c}_{\text{pred}}^p$ có nằm bên trong **BẤT KỲ ĐA GIÁC NGƯỜI GỐC NÀO** trong ảnh hay không:
$$\text{Center-in-Proxy}(p) = \mathbb{I}\left(\exists r \in \text{Polygons}_{\text{person}} \text{ sao cho } \mathbf{c}_{\text{pred}}^p \in \text{Polygon}(r)\right)$$
Ưu tiên tuyệt đối việc sử dụng đa giác `Person` thay vì derived bbox để loại trừ trường hợp điểm tâm rơi vào vùng nền trống giữa hai chân hoặc cánh tay.

#### 2. Predicted Box Containment (Chẩn đoán liên tục — DIAGNOSTIC):
Đo lường tỷ lệ diện tích của hộp bao dự đoán nằm gọn bên trong vùng đại diện cực đại của đối tượng người:
$$\text{Containment}(\mathbf{b}_{\text{pred}}^p, \mathbf{b}_{\text{person}}) = \max_{r \in \text{Polygons}_{\text{person}}} \frac{\text{Area}\left(\mathbf{b}_{\text{pred}}^p \cap \text{bbox}(r)\right)}{\text{Area}\left(\mathbf{b}_{\text{pred}}^p\right)}$$
- Ngưỡng $\text{Containment} \ge 0.50$ chỉ được xem là **ngưỡng heuristic kiểm tra độ nhạy (`sensitivity heuristic`)**, không được coi là chân lý khoa học.

### 10.4 Chuẩn hóa tên gọi và Phân tích độ nhạy Single-Person Proxy Subset

- **Chuẩn hóa tên gọi chính thức bắt buộc:** Chỉ số này được gọi chính thức là:
  **"Identity-Agnostic Proxy Localization Consistency" (Identity-Agnostic PLC — Mức độ nhất quán định vị đại diện không phụ thuộc danh tính)**.
- **Phân tích độ nhạy chuẩn mực — Single-Person Proxy Subset:**
  Để kiểm chứng xem kết quả PLC trên toàn bộ 608 mẫu có bị thổi phồng do việc mô hình dễ dàng "trúng hú họa" vào bất kỳ ai trong đám đông hay không, SafeShift thiết lập tập con phân tích độ nhạy:
  - **Single-Person Proxy Subset:** Gồm đúng **410 mẫu ảnh (chứa 614 proxy atoms)** chỉ có duy nhất 1 đối tượng `Person` ($|\text{Person}| = 1$).
  - Trên tập con này, sự mập mờ danh tính hoàn toàn bị triệt tiêu. Đây là mỏ neo đối chiếu bắt buộc để chứng minh tính vững chắc của năng lực định vị proxy.
- **Quy tắc cấm tuyệt đối:**
  - **TUYỆT ĐỐI KHÔNG GỌI** chỉ số này là "True Evidence Grounding Accuracy" (Độ chính xác bám bằng chứng thật).
  - **TUYỆT ĐỐI KHÔNG ĐƯỢC GỘP** điểm số của Direct Track và Proxy Track thành một điểm trung bình duy nhất. Hai đường đua này bắt buộc phải báo cáo tách biệt hoàn toàn trong hai bảng/cột riêng biệt.

---

## 11. Evidence Precision/Recall

Chỉ số **Evidence Precision** và **Evidence Recall** đánh giá toàn diện khả năng của mô hình: vừa nhận diện đúng bản chất nguy cơ, vừa chỉ ra đúng vị trí bằng chứng trên ảnh.

### 11.1 Giới hạn phương pháp luận về tính tương đối theo chú thích

> [!IMPORTANT]
> **Bản chất của Evidence Precision/Recall:**
> - Đây là **Chỉ số benchmark tương đối theo chú thích hiện có (`Annotation-Relative Benchmark Metric`)**, **KHÔNG PHẢI là độ chính xác nguy cơ triệt để ngoài thực tế (`NOT real-world exhaustive hazard precision`)**.
> - Định nghĩa False Positive ($\text{FP}$) hoàn toàn dựa trên danh mục tham chiếu 12 loại nguy cơ của bộ dữ liệu.
> - Do tính đầy đủ của chú thích đối với mọi nguy cơ tiềm ẩn trong ảnh chưa được chứng minh tuyệt đối, việc một dự đoán nguy cơ không khớp với nhãn GT **KHÔNG ĐƯỢC TỰ ĐỘNG DIỄN GIẢI LÀ ẢO GIÁC NGOÀI ĐỜI THỰC (`unmatched prediction != real-world hallucination`)**.

### 11.2 Công thức toán học định nghĩa

Đánh giá ở cấp độ **Nguy cơ Nguyên tử (`Hazard-Atom Level`)** trên tập Direct Track ($N=781$):
$$\text{Evidence Recall}_h@\tau = \frac{\text{TP}_h@\tau}{N_{\text{evaluable\_GT\_atoms}, h}}$$
$$\text{Evidence Precision}_h@\tau = \frac{\text{TP}_h@\tau}{\text{Total\_Predicted\_Boxes}_h}$$
$$\text{Evidence F1}_h@\tau = \frac{2 \cdot \text{Evidence Precision}_h@\tau \cdot \text{Evidence Recall}_h@\tau}{\text{Evidence Precision}_h@\tau + \text{Evidence Recall}_h@\tau}$$

SafeShift đề xuất báo cáo song song ở hai ngưỡng được xác định trước khi xem kết quả mô hình (`pre-specified before model-result inspection`): **Evidence P/R@0.25** và **Evidence P/R@0.50**.

### 11.3 Phân rã sai số: Nhận diện sai vs Định vị sai

$$\text{Evidence Recall}@\tau = \text{Hazard Recognition Recall} \times \text{Localization Recall | Correct Hazard}@\tau$$
giúp phân định rõ ràng giữa việc mô hình không hiểu ngữ nghĩa nguy cơ hay không định vị được không gian.

### 11.4 Phân tích chẩn đoán Kích thước đối tượng và Mức độ hiếm (Object Size & Rarity Diagnostic Covariates)

Để hiểu sâu bản chất cơ chế thị giác của mô hình VLM mà không làm nhiễu loạn thang đo chính, SafeShift thiết lập các phép phân tích biến đồng biến chẩn đoán (`diagnostic covariates`):

1. **Vô hướng Kích thước ở Cấp độ Nguy cơ Nguyên tử ($\text{AtomSize}(j)$):**
   - Do có 101 / 781 Direct atoms sở hữu nhiều hơn một đa giác ứng viên hỗ trợ ($|R_j| > 1$), việc tính kích thước trên từng polygon rời rạc sẽ không tạo ra một đại lượng vô hướng đơn nhất cho mỗi nguy cơ nguyên tử.
   - SafeShift xác lập đại lượng vô hướng tất định ở cấp độ nguy cơ nguyên tử:
     $$\text{AtomSize}(j) = \max_{r \in R_j} \frac{\text{Area}(r)}{W \times H} \in [0, 1]$$
   - *Căn cứ phương pháp luận:*
     - Hoàn toàn độc lập với đầu ra dự đoán của mô hình (`independent of model prediction`).
     - Một nguy cơ nguyên tử được coi là có thể bám bằng chứng thành công thông qua bất kỳ vùng hỗ trợ ứng viên nào trong $R_j$.
     - Đồng bộ và nhất quán tuyệt đối với công thức điểm cạnh $\text{IoU}(p, j)$, vốn cũng lấy giá trị cực đại trên tập vùng ứng viên tốt nhất ($\max_{r \in R_j}$).
   - *Duy trì thang đo liên tục (Continuous Scale):* SafeShift giữ nguyên giá trị $\text{AtomSize}(j)$ dưới dạng biến số thực liên tục trên dải $[0, 1]$ để phân tích tương quan và hồi quy. **Tuyệt đối không tự ý chia thành các khoảng rời rạc (như bins Small / Medium / Large cơ học)** trong giai đoạn giao thức W2.4. (Mọi nhắc đến đối tượng lớn như khói/chất lỏng hay đối tượng nhỏ như điếu thuốc/điện thoại chỉ mang tính chất minh họa trực quan — *illustrative only*, không phải là phân loại thống kê cố định của benchmark).

2. **Biến đồng biến về Số lượng Vùng Ứng viên Hỗ trợ ($|R_j|$ Covariate):**
   - Báo cáo riêng biệt số lượng đa giác ứng viên $|R_j|$ như một biến chẩn đoán phân loại rời rạc (Discrete Diagnostic Covariate) nhằm phân tích sự khác biệt về độ khó định vị giữa các nguy cơ đơn vùng ($|R_j| = 1$, chiếm 87,07%) và các nguy cơ đa vùng ($|R_j| > 1$, chiếm 12,93%).

3. **Biến đồng biến về Mức độ Hiếm (Rarity Covariate):**
   - Khảo sát mối quan hệ giữa tần suất xuất hiện $N$ của các nhãn đối tượng/hazard atoms (từ phổ biến như `NO_GLOVES` $N=453$ đến rất hiếm như `PERSON_FALLEN` $N=10$) với năng lực nhận diện của mô hình. Giữ nguyên tần suất liên tục, không áp dụng các ngưỡng phân loại cơ học hiếm/phổ biến tùy ý.

4. **Phân định vai trò phương pháp luận:**
   - Cả $\text{AtomSize}(j)$, $|R_j|$, và độ hiếm $N$ đều được định vị độc quyền là **các phân tích chẩn đoán phụ trợ (`Diagnostic Covariate Analyses`)**.
   - **TUYỆT ĐỐI KHÔNG COI ĐÂY LÀ CHỈ SỐ CHÍNH (PRIMARY BENCHMARK METRICS)**. Các phân tích này đóng vai trò làm sáng tỏ cơ chế bên trong của RQ3, không làm thay đổi các bảng tổng hợp kết quả chính thức.

---

## 12. Parse-Failure Policy

Quyết định D4 yêu cầu toàn bộ phản hồi dạng chuỗi thô của VLM phải được lưu trữ nguyên văn và chuyển đổi qua bộ điều hợp/phân tích cú pháp (`Adapter / Parser`).

### 12.1 Đơn vị đo lường Parse Success Rate tường minh

Để tránh sự mơ hồ khi một mẫu ảnh có thể chứa nhiều nguy cơ hoặc mô hình xuất nhiều hộp bao, SafeShift định nghĩa rõ hai cấp độ parse:
1. **Response-level Parse Success Rate ($\text{PSR}_{\text{response}}$):**
   $$\text{PSR}_{\text{response}} = \frac{N_{\text{responses\_with\_valid\_syntax}}}{N_{\text{total\_requests}}}$$
   Đo lường tỷ lệ phản hồi của mô hình tuân thủ cấu trúc cú pháp chung mà bộ parser đọc được.
2. **Evidence-item-level Box Parse Rate ($\text{PSR}_{\text{box}}$):**
   $$\text{PSR}_{\text{box}} = \frac{N_{\text{boxes\_with\_valid\_coordinates}}}{N_{\text{total\_predicted\_boxes}}}$$
   Đo lường tỷ lệ các tọa độ hộp bao nằm đúng dải chuẩn hóa $[0, 1]$ và thỏa mãn $x_{\min} < x_{\max}$, $y_{\min} < y_{\max}$.

### 12.2 Báo cáo song song: End-to-End vs Conditional

- **End-to-End Grounding (Primary System Metric):** Mọi lỗi parse phản hồi hoặc lỗi tọa độ đều được tính là **thất bại hoàn toàn ($\text{IoU} = 0.0$, False Negative)**. Phản ánh đúng năng lực triển khai hệ thống an toàn tự động.
- **Conditional Localization Quality (Diagnostic Metric):** Đo lường chất lượng định vị chỉ tính trên các hộp bao parse thành công. (Hộp bao parse thành công nhưng trượt mục tiêu vẫn giữ $\text{IoU} = 0.0$).

---

## 13. Unsupported-Atom Policy

Cuộc tổng điều tra D6 đã xác định chính xác có **60 nguyên tử nguy cơ thuộc trạng thái `NO_CURRENT_SPATIAL_GT`** (34 atoms `DOOR_OPEN`, 26 atoms bị annotator bỏ sót đa giác), phân bố trên 59 mẫu ảnh.

1. **Loại khỏi mẫu số của đường đua định vị không gian:** 60 nguyên tử này **TUYỆT ĐỐI KHÔNG ĐƯỢC ĐƯA VÀO MẪU SỐ** của các chỉ số IoU, Hit@$\tau$, hay Evidence Grounding.
2. **Giữ nguyên trong bài toán phân loại an toàn:** 59 mẫu ảnh này vẫn là các mẫu kiểm thử phân loại mức an toàn hợp lệ.
3. **Cấm loại bỏ ngầm (No Silent Drop):** Bắt buộc phải công bố danh sách kiểm kê 60 nguyên tử này kèm lý do kỹ thuật.

---

## 14. Calibration Feasibility

Độ hiệu chỉnh xác suất (Probability Calibration) đo lường mức độ tin cậy của xác suất dự đoán (thông qua ECE, Brier Score).

1. **Đặc thù phụ thuộc năng lực giao diện (`Capability-Specific`):**
   Khả năng trích xuất phân bố xác suất tin cậy phụ thuộc hoàn toàn vào giao diện của từng nhà cung cấp mô hình. Quyết định D5 **không đưa ra khẳng định cứng về năng lực của các API**. Tính đủ điều kiện (`Eligibility`) của từng mô hình/phiên bản/giao diện sẽ được khảo sát và xác minh thực nghiệm tại bước **W2.5**.
2. **Không dùng độ tự tin tự thuật làm xác suất:** Tuyệt đối không lấy con số độ tự tin mà mô hình tự nói bằng văn bản làm xác suất hiệu chỉnh.
3. **Vị trí trong benchmark:** Calibration **KHÔNG PHẢI là chỉ số chính xuyên mô hình** cho Seminar. Chỉ xem xét như phân tích năng lực chuyên biệt cho các mô hình mã nguồn mở trích xuất được logits token softmax chuẩn mực.

---

## 15. Object Hallucination Decision

1. **Không dùng trên toàn bộ bộ dữ liệu:** Tuân thủ Quyết định D7, do chú thích đối tượng không triệt để, không áp dụng chỉ số Object Hallucination Rate trên toàn bộ dataset; cấm ngụy biện $\text{missing JSON label} = \text{object absent}$.
2. **Khuyến nghị phạm vi Seminar 8 tuần:** SafeShift khuyến nghị **KHÔNG mở rộng thêm chiến dịch kiểm tra thủ công 30–50 ảnh** trong phạm vi cốt lõi của Seminar để bảo vệ tiến độ và tránh phân tán nguồn lực. Nội dung này được bảo lưu cho Luận văn tốt nghiệp.

---

## 16. Classification-Grounding Inconsistency ($\text{CGI}@\tau$)

Để thay thế cho khái niệm chủ quan "Correct Answer, Wrong Reason", SafeShift xác lập chỉ số hoạt động chuẩn mực:

**"Classification-Grounding Inconsistency relative to available object-support annotation" ($\text{CGI}@\tau$ — Sự không nhất quán giữa phân loại và bám bằng chứng đối với chú thích đối tượng hiện có tại ngưỡng $\tau$)**.

### 16.1 Công thức chuẩn hóa mẫu số có điều kiện và Tham số hóa ngưỡng ($\text{CGI}@\tau$)

Quy ước ký hiệu bắt buộc: **TUYỆT ĐỐI KHÔNG VIẾT KÝ HIỆU $\text{CGI}$ TRỐNG TRƠN THIẾU HẬU TỐ NGƯỠNG**. Mọi chỉ số CGI bắt buộc phải gắn kèm ngưỡng phân vị định vị $\tau$ tương ứng: SafeShift báo cáo song song **$\text{CGI}@0.25$** và **$\text{CGI}@0.50$**.

Công thức phải lấy mẫu số là **tập các trường hợp phân loại đúng**, không lấy toàn bộ tập mẫu:

#### A. Cấp độ Mẫu ảnh ($\text{CGI}_{\text{zero\_grounding}}@\tau$):
$$\text{CGI}_{\text{zero\_grounding}}@\tau = \frac{\sum_{i \in \text{Direct}} \mathbb{I}\left(\text{Classification Correct}_i \land \text{No Direct Atom Grounded}@\tau_i\right)}{\sum_{i \in \text{Direct}} \mathbb{I}\left(\text{Classification Correct}_i\right)}$$
Đo lường tỷ lệ các mẫu ảnh được mô hình phân loại đúng mức độ an toàn nhưng hoàn toàn không định vị trúng bất kỳ nguyên tử nguy cơ trực tiếp nào trong ảnh ở ngưỡng $\tau$ (tức 100% các Direct atoms trong ảnh đều có $\text{Hit}@\tau = 0$).

#### B. Cấp độ Nguy cơ Nguyên tử ($\text{CGI}_{\text{atom}}@\tau$ cho ảnh đa nguy cơ):
$$\text{CGI}_{\text{atom}}@\tau = \frac{\sum_{i \in \text{Direct, ClassifCorrect}} N_{\text{missed\_atoms}@\tau, i}}{\sum_{i \in \text{Direct, ClassifCorrect}} N_{\text{direct\_atoms}, i}}$$
trong đó $N_{\text{missed\_atoms}@\tau, i}$ là số lượng nguyên tử nguy cơ trực tiếp trong ảnh $i$ không đạt tiêu chí ghép cặp định vị ở ngưỡng $\tau$.

### 16.2 Diễn giải phương pháp luận trung thực

Chỉ số này **CHỈ PHẢN ÁNH**: hiện tượng thành công trong phân loại cấp an toàn diễn ra đồng thời với sự thất bại trong việc bám vào vùng chú thích đối tượng hiện có ở ngưỡng $\tau$ (`classification success co-occurs with failure to align with available object-support annotation at threshold` $\tau$).
- **Tuyệt đối không diễn giải:** Mô hình "đoán mò từ bối cảnh nền", "suy luận sai lý do", hay "hoạt động như hộp đen mù quáng", vì mô hình có thể đã dựa vào các đặc trưng bối cảnh hợp lệ khác chưa được khoanh vùng trong tệp JSON.

---

## 17. Confidence-Interval Candidates

Quyết định D2 xác lập: Đơn vị dự đoán là từng ảnh (`Image-level`), nhưng đơn vị lấy mẫu lại thống kê phải có xét đến phụ thuộc cụm thư mục điểm logic (`point_id`).

### 17.1 Loại bỏ phân tầng theo nhãn an toàn — Khắc phục lỗi Singleton Strata

Trong đề xuất ban đầu, phương án phân tầng theo tổ hợp `Domain × Safety Level` đã bộc lộ một khuyết tật toán học nghiêm trọng:
- Trong InspecSafe-V1, có các phân tầng chỉ có đúng 1 cụm điểm logic: ví dụ `metallurgy × Level03` chỉ có đúng **1 cluster** ($N=1$).
- Nếu phân tầng theo nhãn an toàn, việc lấy mẫu lại có hoàn lại 1 lần từ 1 phần tử duy nhất đồng nghĩa với việc cụm điểm đó **xuất hiện chính xác ở 100% các lượt replicate bootstrap**.
- **Hậu quả:** Tạo ra phương sai lấy mẫu lại bằng 0 giả tạo (`artificial zero resampling variance / fake precision`), che giấu hoàn toàn độ bất định thực tế. Việc ép giữ lớp hiếm trong mọi replicate không phải là ưu điểm mà là sự bóp méo thống kê.

### 17.2 Phương án đề xuất chính thức: Domain-Stratified Point-Cluster Bootstrap

SafeShift xác lập **Domain-Stratified Point-Cluster Bootstrap** làm phương pháp ước lượng bất định chính thức (Primary Resampling Method), dứt khoát và không mâu thuẫn:

1. **Bảo toàn cụm thư mục điểm logic (`point_id`):** Toàn bộ các khung hình thuộc cùng một thư mục điểm logic `point_id` luôn đi cùng nhau trong mọi lượt rút mẫu.
2. **Quy trình phân tầng theo miền cho P2 toàn thể (Domain-Stratified for Pooled P2):**
   - Phân tầng **DUY NHẤT theo 5 miền thao tác `folder_domain`**.
   - Trong mỗi miền công nghiệp $d$, lấy mẫu lại có hoàn lại các cụm `point_id` (đối với Normal) và các mẫu/cụm Anomaly của chính miền đó cho tới khi đạt đúng quy mô số cụm gốc của miền $d$.
   - Gộp các tập con lấy mẫu lại từ 5 miền lại thành một replicate toàn thể P2.
   - **TUYỆT ĐỐI KHÔNG PHÂN TẦNG THEO CẤP AN TOÀN (`NO STRATIFICATION BY SAFETY LEVEL`)**, qua đó loại trừ triệt để nguy cơ tạo phương sai 0 giả tạo trên các tầng đơn mẫu (`singleton strata`).
3. **Đối với chỉ số từng miền riêng biệt (Domain-specific metrics):**
   - Lấy mẫu lại có hoàn lại các cụm điểm nội bộ trong chính miền đó (`resample point clusters within domain`).
4. **Chính sách xử lý Replicate khuyết lớp ground truth (Missing Class Policy in Replicates):**
   - Nếu trong một lượt replicate bootstrap không rút trúng bất kỳ mẫu ground truth nào cho lớp hoặc phân tầng đang đánh giá (ví dụ: không có mẫu Level03 nào xuất hiện trong replicate), giá trị metric của lượt đó được ghi nhận là **`NA` (Undefined)**.
   - Bắt buộc phải công bố tường minh: **Tỷ lệ số lượt replicate hợp lệ trên tổng số lượt lấy mẫu lại (`Valid Replicates / B`)**. Tuyệt đối không thay thế giả tạo (`no artificial imputation`) hay ép buộc lớp hiếm phải xuất hiện.
5. **Đối với các phân tầng $N=1$ hoặc siêu nhỏ:**
   - Thừa nhận trung thực: Bootstrap không thể tạo ra thông tin thống kê mới từ một quan sát duy nhất.
   - Công bố: Ước lượng điểm (`point estimate`), mẫu số thực tế, cảnh báo độ bất định mô tả, và có thể xem xét khoảng tin cậy nhị thức chính xác (Wilson / Clopper-Pearson interval) cho độ thu hồi đơn giản nếu phù hợp, tuyệt đối không tạo độ chính xác giả bằng phân tầng ép buộc.

---

## 18. Dependence / Cluster Bootstrap

### 18.1 Cấu trúc phụ thuộc trong dữ liệu InspecSafe-V1

- **Dữ liệu Bình thường (`Normal_data`, 4.013 ảnh):** Phân bố trong **2.234 thư mục điểm logic (`point_id`)**. Mỗi điểm chứa từ 1 đến 4 khung hình liền kề được chụp bởi robot tuần tra ở cùng một góc máy và tọa độ. Các khung hình trong cùng một `point_id` có tương quan thị giác và bối cảnh cực cao.
- **Dữ liệu Bất thường (`Anomaly_data`, 1.000 ảnh):** Nằm trong 1.000 thư mục điểm riêng biệt, nhưng có bằng chứng chuỗi cắt khung hình từ video quan sát.

### 18.2 Các cảnh báo nhận thức luận bắt buộc (Epistemological Caveats)

1. **Bản chất của `point_id`:**
   - Trường `point_id` là mã định danh thư mục điểm logic (`logical point folder identifier`).
   - `point_id` **KHÔNG PHẢI là ID trạm/nhà máy vật lý đã xác minh (`not verified physical site ID`)**. Mối quan hệ ánh xạ giữa 3.234 thư mục điểm logic và 2.239 điểm kiểm tra hợp lệ do upstream công bố vẫn chưa được giải quyết (`unresolved mapping`).
   - Việc gom cụm theo `point_id` chỉ giải quyết **tương quan đa khung hình nội bộ điểm đã biết (`known within-point dependence`)**. Nó **KHÔNG CHỨNG MINH tính độc lập giữa các điểm khác nhau (`between-point independence`)**.
2. **Bản chất của `source-family`:**
   - 12 họ nguồn Anomaly chỉ là các tín hiệu kinh nghiệm phỏng đoán (`heuristic inferred signals`), không phải ID video thật. Tuyệt đối không sử dụng `source-family` làm đơn vị gom cụm bootstrap chính thức.

### 18.3 Tham số và lý do lựa chọn Percentile Bootstrap

- **Số lượt lấy mẫu lại:** $B = 2.000$ replicates (chính thức); $B = 5.000$ (kiểm tra hội tụ).
- **Khóa seed tái lập:** `seed = 42`.
- **Khoảng tin cậy:** Percentile Bootstrap 95% $\left[ q_{0,025}, \, q_{0,975} \right]$.
- **Lý do chọn Percentile thay vì BCa (Bias-Corrected and Accelerated):**
  - Percentile bootstrap đơn giản, minh bạch và có tính tái lập cao.
  - BCa không được chọn do độ phức tạp triển khai lớn khi lấy mẫu cụm (`cluster resampling`), và đặc biệt là sự mất ổn định toán học khi tính toán tham số gia tốc trên các chỉ số phi trơn có khả năng khuyết thiếu lớp trong một số lượt replicate.
  - SafeShift không tuyên bố Percentile bootstrap là hoàn hảo vượt trội toàn diện, mà là phương án phù hợp và minh bạch nhất cho cấu trúc dữ liệu hiện tại.

---

## 19. Model-Comparison Statistics

Khi so sánh hiệu năng giữa hai mô hình VLM (ví dụ: Mô hình A vs Mô hình B), mọi dự đoán đều được thực hiện trên **cùng một tập ảnh cố định**. Các quan sát giữa các mô hình có bản chất **phụ thuộc theo cặp (`paired observations`)**.

### 19.1 Paired Bootstrap Difference CI làm phương pháp so sánh chính

Mọi so sánh theo cặp giữa hai mô hình (hoặc hai biến thể prompt) bắt buộc phải được đánh giá trên **CÙNG MỘT TẬP CÁC LƯỢT DRAW REPLICATE BOOTSTRAP $b \in \{1, \dots, B\}$**:
Đối với mỗi lượt lấy mẫu lại $b$:
$$\Delta M^{(b)} = M_A^{(b)} - M_B^{(b)}$$

- **Chính sách Replicate theo cặp hợp lệ (Valid Paired Replicates):**
  Nếu trong lượt replicate $b$, một trong hai mô hình bị giá trị `NA` (do khuyết lớp ground truth trong lượt rút đó), hiệu số $\Delta M^{(b)}$ của lượt đó được tính là `NA`. Khoảng tin cậy theo cặp chỉ được xây dựng trên các replicate hợp lệ đồng thời cho cả hai mô hình, và **bắt buộc phải công bố tỷ lệ `Valid Paired Replicates / B`**.
- **Khoảng tin cậy:** $\text{CI}_{95\%}(\Delta M) = \left[ \Delta_{0,025}, \, \Delta_{0,975} \right]$.

> [!IMPORTANT]
> **Chuẩn hóa phát biểu kết luận khoa học:**
> - Nếu khoảng tin cậy $\text{CI}_{95\%}(\Delta M)$ không chứa giá trị 0: Được diễn đạt là **"Khoảng tin cậy bootstrap theo cặp 95% không chứa 0 cho thấy một sự chênh lệch có hướng rõ ràng dưới giao thức lấy mẫu lại đã xác định trước khi xem kết quả mô hình (`indicates a directionally clear difference under the pre-specified resampling protocol`)"**.
> - **Tuyệt đối không tự động tuyên bố:** "Có ý nghĩa thống kê ở mức $\alpha = 0,05$" như thể đã chạy một kiểm định giả thuyết chuẩn tắc (formal hypothesis test) nếu giao thức D5 chưa chạy gói kiểm định chính thức.
> - Nếu khoảng tin cậy chứa giá trị 0: **TUYỆT ĐỐI KHÔNG TUYÊN BỐ HAI MÔ HÌNH "TƯƠNG ĐƯƠNG NHAU" HAY "GIỐNG NHAU"**. Chỉ được kết luận dữ liệu chưa cho thấy sự phân hóa rõ ràng.

### 19.2 Không chạy ma trận p-value mặc định

SafeShift không khuyến nghị tạo ra các ma trận $p$-value dày đặc giữa mọi cặp mô hình nhằm tránh hiện tượng săn lùng $p$-value (`p-value hunting`). Nếu trong tương lai có thực hiện các bài kiểm định giả thuyết hình thức (như Paired Permutation Test), các cặp so sánh bắt buộc phải được xác định trước (`pre-specified`) và áp dụng quy trình hiệu chỉnh so sánh bội (như Benjamini-Hochberg FDR).

---

## 20. P1/P2/P3 Application

| Tiêu chí | P1 — Baseline Replication | P2 — Primary Research Protocol | P3 — Candidate Sensitivity Protocol |
| :--- | :--- | :--- | :--- |
| **Quy mô mẫu** | Đúng **1.250 mẫu** (Test chính thức) | Đúng **5.013 mẫu** (Toàn bộ dữ liệu) | 1.248 mẫu (Within-test) & 1.241 mẫu (Cross-split) |
| **Vai trò nghiên cứu** | Tái lập & đối chiếu upstream baseline | Trả lời các câu hỏi nghiên cứu chính (RQ1–3) | Kiểm tra độ nhạy rò rỉ lặp ảnh |
| **Độ bao phủ miền** | 5 miền (nhưng `metallurgy` có 0 Anomaly) | 5 miền (đầy đủ 1.000 mẫu Anomaly) | Đánh giá phụ trợ theo tập con |
| **Chỉ số áp dụng** | Safety Accuracy, BGE-M3 Similarity, Extension Grounding | Balanced Accuracy, Macro-F1, FNR/FPR, Evidence Grounding | Áp dụng cùng công thức với P1 trên tập con |
| **Xử lý Metallurgy** | Anomaly metrics = **UNDEFINED** (Không tính) | Anomaly metrics = **DESCRIPTIVE / SPARSE-SUPPORT** ($N=9$) | Theo phân bố thực tế của tập con |
| **Định vị Grounding** | SafeShift extension, không phải upstream baseline | RQ3-A Direct ($N=781$) & RQ3-B Proxy ($N=947$) | Đánh giá độ nhạy trên tập con |

---

## 21. Domain-Mismatch Sensitivity

Quyết định D3 đã xác định chính xác **36 mẫu xung đột** giữa tên thư mục và khẳng định mở đầu trong tệp văn bản (`folder_domain != text_domain`):
- 4 mẫu `power` $\rightarrow$ `coal_conveyor` (train)
- 8 mẫu `metallurgy` $\rightarrow$ `oil_chemical` (train)
- 24 mẫu `tunnel` $\rightarrow$ `oil_chemical` (20 train, 4 test)

1. **Công thức toán học bất biến:** Mọi công thức chỉ số hoàn toàn giữ nguyên không đổi giữa phân tích chính và phân tích độ nhạy.
2. **Sự thay đổi duy nhất là phân bổ mẫu vào các miền:**
   - *Phân tích chính (Primary):* Phân bổ theo `folder_domain`.
   - *Độ nhạy A (Sensitivity A):* Loại bỏ 36 mẫu khỏi các bảng phân tích từng miền.
   - *Độ nhạy B (Sensitivity B):* Tái phân bổ 36 mẫu theo `text_domain`.
3. **Mục tiêu khoa học:** Kiểm tra xem kết luận so sánh xuyên miền (RQ1) có bị đảo lộn khi xử lý 36 mẫu xung đột hay không. Đặc biệt quan sát miền `metallurgy` khi số mẫu Anomaly giảm từ $N=9$ xuống còn $N=1$.

---

## 22. D5 Decision Matrix

Bảng tổng hợp ma trận quyết định cho các cấu phần kỹ thuật của D5:

| Cấu phần kỹ thuật | Phương án ứng viên | Đánh giá khoa học & Trade-off | Khuyến nghị SafeShift |
| :--- | :--- | :--- | :--- |
| **Chỉ số phân loại chính** | 1. Macro-F1<br>2. Balanced Accuracy<br>3. Cả hai song hành (Both)<br>4. Raw Accuracy | - Raw Accuracy bị bóp méo bởi 80% Normal.<br>- Balanced Accuracy đo trực tiếp Recall không thiên vị.<br>- Macro-F1 phạt nặng cả báo động giả và bỏ sót. | **CHỌN PHƯƠNG ÁN 3 (CO-PRIMARY)**<br>Balanced Accuracy + Macro-F1 làm chỉ số chính song hành; Raw Accuracy chỉ mang tính mô tả. |
| **Chỉ số sai số an toàn** | 1. FNR gộp chung<br>2. Track A Anomaly FNR/FPR + Track B Level01 FNR/Recall | - FNR gộp chung gây hiểu lầm và ngụy biện.<br>- Tách Track A và Track B phân định rõ rủi ro bỏ sót nguy cơ tổng thể vs nguy cơ thảm khốc. | **CHỌN PHƯƠNG ÁN 2**<br>Báo cáo độc lập $\text{FNR}_{\text{anomaly}}$ và $\text{FNR}_{\text{L01}}$. Cấm gộp chung. |
| **Chỉ số suy giảm xuyên miền (RQ1)** | 1. Balanced Accuracy Spread thuần túy trên K=4<br>2. Class-Conditional Domain Analysis (Primary) + Chẩn đoán phụ trợ | - Chỉ số vĩ mô trên K=4 bỏ qua 2/5 miền.<br>- Class-Conditional Analysis giảm thiểu nhiễu tỷ lệ nhãn và bao quát các miền có hỗ trợ. | **CHỌN PHƯƠNG ÁN 2**<br>Primary: Class-Conditional Domain Recall & Pooled-to-Domain Gap. Diagnostic: Balanced Accuracy Spread trên K=4. |
| **Xử lý lớp thiếu ở từng miền** | 1. Support-only macro average<br>2. Yêu cầu cố định 4 lớp (gán NA)<br>3. Dual-Layer Support-Aware Policy | - Phương án 1 so sánh trên bài toán khác nhau.<br>- Phương án 2 làm khuyết 40% số miền.<br>- Phương án 3 vừa minh bạch số lớp vừa có mỏ neo so sánh. | **CHỌN PHƯƠNG ÁN 3**<br>Descriptive macro có gắn cờ số lớp $K_d$; dùng Class-Conditional metrics làm mỏ neo so sánh. |
| **Báo cáo Worst-Domain** | 1. Quy tắc ngưỡng cơ học N >= 30<br>2. Báo cáo giá trị nhỏ nhất quan sát được kèm mẫu số, CI và cảnh báo so sánh | - Ngưỡng N >= 30 tùy ý, thiếu cơ sở toán học.<br>- Phương án 2 minh bạch, giữ metallurgy là Descriptive / Sparse-Support. | **CHỌN PHƯƠNG ÁN 2**<br>Báo cáo minimum quan sát được giữa các miền so sánh được; công bố đầy đủ mẫu số và CI. |
| **Chỉ số phân tầng nguy cơ (RQ2)** | 1. Gộp chung toàn bộ dataset<br>2. Bộ 4 chỉ số trên 7 tầng nguy cơ gom nhóm (Strata A–G) + cảnh báo non-additive overlap | - Gộp chung che giấu chênh lệch sâu sắc giữa các dạng nguy cơ.<br>- Đa số mẫu Anomaly (51,2%) chứa $\ge 2$ hazard atoms, tạo 1.381 lượt thành viên trên 7 tầng khiến các tầng không độc lập. | **CHỌN PHƯƠNG ÁN 2**<br>Báo cáo bộ 4 chỉ số: Exact Safety-Level Error Rate, Anomaly-to-Normal Miss Rate, Level01 Recall & Critical Miss Rate, và Ma trận nhầm lẫn mức an toàn. Cấm tuyệt đối cộng dồn mẫu hoặc sai số giữa các tầng (non-additive counts). |
| **Định vị Direct Grounding** | 1. Hit@0.25 thuần túy<br>2. Continuous IoU (Primary) + Hit@0.25 / Hit@0.50 (Sensitivity) + Evidence P/R | - Chỉ dựa vào ngưỡng đơn độc dễ gây tranh cãi.<br>- Continuous IoU đo lường trọn vẹn dải phân bố; các ngưỡng đóng vai trò kiểm tra độ nhạy xác định trước. | **CHỌN PHƯƠNG ÁN 2**<br>End-to-End Mean IoU & Median IoU làm Primary; Hit@0.25 và Hit@0.50 làm Thresholded Sensitivity (pre-specified). |
| **Ghép cặp Direct Grounding (2 Matching Modes)** | 1. Ghép tham lam (Greedy)<br>2. Phân định rõ Mode A (Continuous IoU Assignment) và Mode B (Thresholded Bipartite Matching) | - Ghép tham lam không tối ưu toàn cục.<br>- Việc dùng lẫn lộn giữa hàm đo liên tục và quyết định nhị phân có ngưỡng gây sai lệch chỉ số. | **CHỌN PHƯƠNG ÁN 2**<br>- Mode A (Threshold-Free): Dành cho Mean/Median IoU, cực đại hóa tổng IoU cạnh $\max_{r \in R_j}$, không áp ngưỡng $\tau$, atom thiếu gán $0.0$.<br>- Mode B: Dành cho Hit@$\tau$, Evidence P/R@$\tau$, CGI@$\tau$, chỉ giữ cạnh $\text{IoU} \ge \tau$, cực đại hóa số cặp ghép, tie-break bằng tổng IoU.<br>Cấm tuyệt đối trộn lẫn 2 modes. |
| **Định vị Weak Proxy** | 1. Dùng IoU với Person<br>2. Identity-Agnostic Proxy Localization Consistency (Center-in-Proxy + Box Containment) | - IoU với Person phạt mô hình nhìn đúng đầu người (NO_HELMET).<br>- PLC phản ánh trung thực mức độ nhất quán vị trí không phụ thuộc danh tính người. | **CHỌN PHƯƠNG ÁN 2**<br>Primary: Center-in-Proxy (ưu tiên polygon gốc). Diagnostic: Box Containment (ngưỡng 0.50 là heuristic). Sensitivity: Single-Person Proxy Subset. |
| **Chẩn đoán Kích thước & Độ hiếm** | 1. Coi là Primary Benchmark và chia bin Small/Medium/Large cơ học<br>2. Biến đồng biến chẩn đoán phụ trợ liên tục $\text{AtomSize}(j)$, $|R_j|$ và Rarity $N$ | - Chia bin cơ học tùy tiện, mất thông tin liên tục.<br>- Kích thước đối tượng và độ hiếm đóng vai trò giải thích cơ chế thị giác, không phải tiêu chí xếp hạng chính. | **CHỌN PHƯƠNG ÁN 2**<br>Định vị độc quyền là Diagnostic Covariates. Sử dụng $\text{AtomSize}(j) = \max_{r \in R_j} \frac{\text{Area}(r)}{W \times H} \in [0, 1]$ độc lập với model prediction, đi kèm $|R_j|$ (87,07% single vs 12,93% multi) và $N$ liên tục; cấm chia bin cơ học. |
| **Ước lượng bất định (CI)** | 1. Stratified theo Domain x Level<br>2. Domain-Stratified Point-Cluster Bootstrap (resample theo cụm point_id trong từng miền) | - Phân tầng theo nhãn tạo phương sai 0 giả tạo trên singleton strata.<br>- Domain-Stratified Point-Cluster Bootstrap phản ánh trung thực độ bất định, không làm méo mó phương sai. | **CHỌN PHƯƠNG ÁN 2**<br>Domain-Stratified Point-Cluster Bootstrap ($B=2.000$, seed=42); replicate thiếu lớp ghi nhận NA, báo cáo valid replicates / B. |
| **So sánh các mô hình** | 1. Phép thử 2 mẫu độc lập<br>2. Paired Bootstrap Difference CI 95% | - Phép thử độc lập sai phương pháp luận (dữ liệu theo cặp).<br>- Paired Difference CI minh bạch, tập trung vào effect size có hướng trên cùng tập replicate. | **CHỌN PHƯƠNG ÁN 2**<br>Paired Bootstrap Difference CI 95% trên cùng tập replicate làm primary; báo cáo valid paired replicates / B; không tuyên bố tương đương khi CI chứa 0. |

---

## 23. Preliminary D5 Recommendation

> [!IMPORTANT]
> **Trạng thái phê duyệt:** Toàn bộ nội dung dưới đây ở trạng thái **ĐỀ XUẤT, CHƯA PHÊ DUYỆT (`PROPOSED, NOT APPROVED`)**.

SafeShift đề xuất bộ nguyên tắc thực thi chính thức cho Quyết định D5:

1. **Phân loại an toàn 4 lớp:**
   - **Primary Co-Metrics:** Balanced Accuracy và Macro-F1 được công bố song hành ở vị trí trung tâm.
   - **Descriptive Metric:** Raw Accuracy được giữ lại duy nhất cho mục đích đối chiếu với bài báo gốc upstream.
   - **Diagnostic bắt buộc:** Bắt buộc kèm theo ma trận nhầm lẫn chuẩn hóa và bảng chỉ số Per-Class (Precision, Recall, F1).
2. **Sai số an toàn công nghiệp:**
   - Báo cáo độc lập **$\text{FNR}_{\text{anomaly}}$** và **$\text{FPR}_{\text{anomaly}}$** cho bài toán nhị phân.
   - Báo cáo độc lập **$\text{FNR}_{\text{L01}}$** và **$\text{Recall}_{\text{L01}}$** cho lớp nguy cơ nghiêm trọng, có phân rã thành tỷ lệ bỏ sót hoàn toàn (`Miss`) và tỷ lệ hạ cấp (`Downgrade`).
3. **Quản lý miền thiếu lớp và miền Luyện kim:**
   - Áp dụng Chính sách hai tầng (Dual-Layer Policy): Chỉ số vĩ mô của miền thiếu lớp được gắn nhãn $K_d$; so sánh xuyên miền căn cứ trên Class-Conditional Recall của các lớp hiện diện.
   - Miền Luyện kim (`metallurgy`) được xếp vào diện **"Descriptive / Sparse-Support"** cho các chỉ số bất thường; công bố đầy đủ mẫu số và CI rộng.
4. **Suy giảm hiệu năng xuyên miền (Cross-Domain Robustness):**
   - **Primary Anchor:** **Class-Conditional Domain Analysis** (Recall theo từng lớp và Pooled-to-Domain Gap theo từng lớp $\Delta(c, d)$) nhằm giảm thiểu nhiễu tỷ lệ nhãn.
   - **Secondary Diagnostic:** Balanced Accuracy Domain Spread trên tập các miền $K=4$; Binary Anomaly Recall Spread làm chẩn đoán phụ trợ.
   - Tuyệt đối không dùng thuật ngữ "Domain Generalization Drop".
5. **Chỉ số phân tầng nguy cơ RQ2 (RQ2 Hazard Strata Metrics):**
   - Đánh giá trên 7 tầng nguy cơ gom nhóm ứng viên (Strata A–G): Báo cáo bắt buộc bộ 4 chỉ số:
     1. **Exact Safety-Level Error Rate**
     2. **Anomaly-to-Normal Miss Rate**
     3. **Level01 Recall và Critical Miss Rate** (cho các tầng có Level01)
     4. **Ma trận nhầm lẫn mức an toàn** (Safety-Level Confusion Matrix).
   - **Cơ sở thực chứng & Cảnh báo phương pháp luận bắt buộc:** Đa số mẫu ảnh bất thường (512 / 1.000 mẫu Anomaly, tức 51,2%) chứa từ 2 nguy cơ nguyên tử trở lên, tạo ra tổng cộng 1.381 lượt thành viên (memberships) trên 7 tầng. Do đó, các tầng nguy cơ **hoàn toàn không độc lập thống kê**, số lượng mẫu **không có tính cộng dồn (non-additive counts)**. Báo cáo bắt buộc phải kèm theo cảnh báo rõ ràng; **tuyệt đối cấm cộng dồn sai số hoặc tính tổng số mẫu giữa các tầng**.
6. **Đánh giá bám bằng chứng trực tiếp (RQ3-A Direct Grounding):**
   - **Tập vùng GT ứng viên ($R_j$):** Định nghĩa tường minh tập vùng $R_j$ theo D6 mapping; tính điểm cạnh IoU là cực đại trên các đa giác thuộc $R_j$: $\text{IoU}(p, j) = \max_{r \in R_j} \text{IoU}(p, \text{bbox}(r))$.
   - **Primary Metric:** **End-to-End Mean IoU** và **Median IoU** (đo lường liên tục).
   - **Thresholded Sensitivity:** **Hit@0.25** và **Hit@0.50** (xác định trước khi xem kết quả mô hình).
   - **Pointing Hit:** Bắt buộc dùng **đa giác GT gốc (`Original GT Polygon`)** thuộc tập vùng ứng viên $R_j$ để kiểm tra điểm tâm dự đoán.
   - **Phân định rạch ròi 2 chế độ ghép cặp (Matching Modes):**
     - **Mode A — Continuous IoU Assignment (Threshold-Free):** Dành riêng cho End-to-End Mean IoU, Median IoU, và Parse-Conditional Mean IoU. Ghép cặp tối ưu cực đại hóa tổng điểm IoU cạnh mà không áp ngưỡng $\tau$. Tuyệt đối không tái sử dụng hộp dự đoán. Mọi GT atom không có dự đoán tương ứng hoặc do lỗi phân tích cú pháp đều được tính là $\text{IoU} = 0.0$.
     - **Mode B — Thresholded Bipartite Matching:** Dành riêng cho Hit@0.25, Hit@0.50, Evidence P/R@$\tau$, và $\text{CGI}@\tau$. Chỉ cho phép các cạnh đạt ngưỡng $\text{IoU}(p, j) \ge \tau$. Cực đại hóa số cặp ghép hợp lệ (cardinality), tie-break bằng tổng IoU.
     - **Quy tắc cấm kỵ:** Tuyệt đối không được trộn lẫn hoặc dùng thay thế hai chế độ Mode A và Mode B cho nhau.
   - **Comprehensive Metric:** Evidence Precision, Evidence Recall, Evidence F1 ở cấp độ nguy cơ nguyên tử (báo cáo song song tại ngưỡng 0.25 và 0.50).
7. **Đánh giá đại diện yếu (RQ3-B Weak Proxy Grounding):**
   - Đo lường bằng **Identity-Agnostic Proxy Localization Consistency (Identity-Agnostic PLC)**: Primary là **Center-in-Proxy** trên bất kỳ đa giác `Person` gốc nào trong ảnh; Continuous Box Containment làm chẩn đoán.
   - **Sensitivity Analysis:** Bắt buộc kiểm tra độ nhạy chéo trên **Single-Person Proxy Subset** ($N=410$ mẫu, 614 atoms) để loại trừ triệt để nhiễu mập mờ danh tính.
   - Báo cáo tách biệt hoàn toàn khỏi Direct Grounding; cấm gọi là "bám bằng chứng thật".
8. **Chỉ số không nhất quán phân loại - định vị ($\text{CGI}@\tau$):**
   - Bắt buộc tham số hóa theo ngưỡng: Báo cáo song song **$\text{CGI}@0.25$** và **$\text{CGI}@0.50$** (cả cấp độ mẫu và cấp độ atom); cấm dùng ký hiệu CGI thiếu hậu tố ngưỡng.
9. **Xử lý lỗi phân tích cú pháp (Parse Failure):**
   - Áp dụng đồng thời: **End-to-End Grounding** (lỗi parse tính là $\text{IoU}=0.0$) làm chỉ số chính; báo cáo tường minh **$\text{PSR}_{\text{response}}$** và **$\text{PSR}_{\text{box}}$** đi kèm **Parse-Conditional Mean IoU** làm chẩn đoán.
10. **Biến đồng biến chẩn đoán kích thước và độ hiếm:**
    - **Vô hướng Kích thước ở cấp độ Direct Atom:** Sử dụng $\text{AtomSize}(j) = \max_{r \in R_j} \frac{\text{Area}(r)}{W \times H} \in [0, 1]$, hoàn toàn độc lập với mô hình dự đoán và đồng bộ với điểm cạnh IoU.
    - **Biến chẩn đoán rời rạc $|R_j|$:** Báo cáo riêng biệt số lượng đa giác ứng viên hỗ trợ (phân biệt single-region $|R_j|=1$, 87,07% và multi-region $|R_j|>1$, 12,93%).
    - **Mức độ hiếm $N$:** Khảo sát tần suất xuất hiện liên tục của hazard atoms (từ $N=453$ đến $N=10$).
    - **Duy trì thang đo liên tục:** Giữ nguyên giá trị thực liên tục trên $[0, 1]$ và tần suất $N$, tuyệt đối không chia bin Small / Medium / Large cơ học trong giao thức W2.4. (Mọi ví dụ chỉ mang tính minh họa).
    - **Phân định vai trò:** Định vị độc quyền là các biến đồng biến chẩn đoán phụ trợ (`Diagnostic Covariates`), tuyệt đối không coi là chỉ số chính (Primary Benchmark Metrics).
11. **Định lượng bất định và khoảng tin cậy:**
    - Áp dụng **Domain-Stratified Point-Cluster Bootstrap** (phân tầng theo 5 miền `folder_domain`, lấy mẫu lại theo cụm thư mục điểm logic `point_id` trong từng miền), tuyệt đối không phân tầng theo cấp an toàn.
    - Cấu hình: $B = 2.000$ replicates, khoảng tin cậy Percentile 95%, cố định `seed = 42`. Các replicate khuyết lớp ghi nhận `NA`, công bố tỷ lệ `Valid Replicates / B`.
12. **So sánh đa mô hình:**
    - Áp dụng **Paired Bootstrap Difference CI 95%** trên cùng tập draw replicate làm phương pháp so sánh chính; công bố tỷ lệ `Valid Paired Replicates / B`.
    - Nếu CI không chứa 0: kết luận chênh lệch có hướng rõ ràng; nếu CI chứa 0: không tuyên bố hai mô hình tương đương.

---

## 24. Risks & Limitations

Báo cáo W2.4 nhận diện các rủi ro và giới hạn phương pháp luận bắt buộc phải công bố minh bạch:

1. **Giới hạn của các phân tầng đơn mẫu (Singleton Strata):**
   Lớp `Level03` chỉ có 15 mẫu toàn bộ dữ liệu, trong đó `metallurgy` và `power` mỗi miền chỉ có 1 mẫu duy nhất. Bootstrap không thể tạo ra thông tin thống kê mới từ một quan sát đơn lẻ. Các ước lượng trên các lớp này chịu độ bất định rất lớn.
2. **Tính tương đối theo chú thích của Grounding Benchmark:**
   Evidence Precision/Recall và Classification-Grounding Inconsistency hoàn toàn dựa trên các chú thích đối tượng hiện có của InspecSafe-V1, không phải là chân lý an toàn triệt để ngoài đời thực. Việc mô hình dự đoán lệch nhãn không đồng nghĩa với ảo giác ngoài thực tế.
3. **Nhiễu cấu trúc đa chiều giữa các phân xưởng:**
   Việc phân tích theo từng lớp (`Class-Conditional`) chỉ giảm bớt nhiễu do tỷ lệ pha trộn lớp, hoàn toàn không loại bỏ được các yếu tố gây nhiễu về nền tảng robot (`SuspendedRail` vs `Wheeled`), góc máy quan sát, bối cảnh ánh sáng hay thành phần rủi ro cụ thể của từng ngành công nghiệp.
4. **Không có nhãn chuẩn về lý do suy luận của con người:**
   Do tuân thủ D7-A không tạo nhãn rationale mới ở Seminar, việc đánh giá bám bằng chứng dừng lại ở mức độ bám đối tượng vật lý (`Object Support`) và kiểm tra tính nhất quán (`Consistency`), chưa thể chứng minh chuỗi suy luận nhân quả nội tại của mô hình VLM.
5. **Thiếu vắng phân bố xác suất tin cậy từ các Closed-API:**
   Việc không thể trích xuất xác suất tin cậy thực sự từ các mô hình thương mại khiến việc đánh giá độ hiệu chỉnh (calibration) bị giới hạn và không thể áp dụng đồng nhất trên toàn bộ benchmark.

---

## 25. Questions Requiring Approval

Để chính thức ban hành **Quyết định D5 (DEC-W2-D5)**, SafeShift đệ trình danh sách **17 câu hỏi phương pháp luận sẵn sàng phê duyệt (`READY FOR D5 APPROVAL`)**:

1. **Chỉ số phân loại chính:** Chấp thuận sử dụng **Balanced Accuracy** và **Macro-F1** làm hai chỉ số chính song hành (Co-Primary Metrics), và xếp Raw Accuracy vào nhóm mô tả phụ trợ hay không?
2. **Định nghĩa chỉ số sai số an toàn:** Chấp thuận tách bạch độc lập **$\text{FNR}_{\text{anomaly}} / \text{FPR}_{\text{anomaly}}$** (Track A) và **$\text{FNR}_{\text{L01}} / \text{Recall}_{\text{L01}}$** (Track B), cấm dùng FNR chung chung hay không?
3. **Chính sách xử lý lớp thiếu ở từng miền:** Chấp thuận Chính sách hai tầng (Dual-Layer Support-Aware Policy C): công bố chỉ số vĩ mô có gắn cờ số lớp $K_d$ và dùng Class-Conditional Recall làm mỏ neo so sánh chính hay không?
4. **Mỏ neo chính cho suy giảm xuyên miền (RQ1):** Chấp thuận sử dụng **Class-Conditional Domain Analysis** (Recall từng lớp và Pooled-to-Domain Gap $\Delta(c, d)$) làm mỏ neo chính cho RQ1, xếp Balanced Accuracy Spread trên $K=4$ vào nhóm chẩn đoán phụ trợ, và cấm dùng thuật ngữ "Domain Generalization Drop" hay không?
5. **Chính sách xác định Worst-Domain:** Chấp thuận loại bỏ quy tắc $N \ge 30$ cơ học, chuyển sang báo cáo giá trị nhỏ nhất quan sát được kèm đầy đủ mẫu số, CI, và xếp `metallurgy` vào diện "Descriptive / Sparse-Support" hay không?
6. **Chính sách chỉ số phân tầng nguy cơ RQ2 & Hiện tượng giao thoa đa nguy cơ:** Chấp thuận đánh giá trên 7 tầng nguy cơ gom nhóm (Strata A–G) với bộ 4 chỉ số (Exact Safety-Level Error Rate, Anomaly-to-Normal Miss Rate, Level01 Recall & Critical Miss Rate cho các tầng có Level01, và Ma trận nhầm lẫn mức an toàn); đồng thời phê chuẩn nguyên tắc phương pháp luận: thừa nhận hiện tượng đa nguy cơ (512 / 1.000 mẫu Anomaly chứa $\ge 2$ hazard atoms, tạo ra 1.381 lượt thành viên trên 7 tầng), coi các tầng là không độc lập thống kê và cấm tuyệt đối việc cộng dồn sai số hoặc tính tổng số mẫu giữa các tầng (non-additive counts) hay không?
7. **Chỉ số chính cho Direct Grounding:** Chấp thuận sử dụng **End-to-End Mean IoU** và **Median IoU** làm thước đo định vị liên tục chính, đi kèm **Hit@0.25** và **Hit@0.50** làm ngưỡng độ nhạy được xác định trước khi xem kết quả mô hình (`pre-specified before model-result inspection`) hay không?
8. **Định nghĩa chuẩn mực cho Pointing Hit:** Chấp thuận quy tắc điểm tâm dự đoán bắt buộc phải nằm trong **bất kỳ đa giác GT gốc nào (`Original GT Polygon`)** thuộc tập vùng ứng viên $R_j$ để tránh tính điểm trúng vào vùng nền trống của derived bbox hay không?
9. **Định nghĩa tập vùng ứng viên $R_j$ & Phân định 2 chế độ ghép cặp Direct Grounding:** Chấp thuận định nghĩa tập vùng GT ứng viên $R_j$ cho mỗi Direct atom theo D6 mapping; đồng thời phê chuẩn việc phân định rạch ròi hai chế độ ghép cặp:
   - **Mode A (Continuous IoU Assignment / Threshold-Free)** cho End-to-End Mean IoU, Median IoU, và Parse-Conditional Mean IoU: cực đại hóa tổng điểm IoU cạnh $\text{IoU}(p, j) = \max_{r \in R_j} \text{IoU}(p, \text{bbox}(r))$ mà không áp ngưỡng $\tau$, không tái sử dụng hộp dự đoán, GT atom khuyết/lỗi parse gán $\text{IoU}=0.0$;
   - **Mode B (Thresholded Bipartite Matching)** cho Hit@$\tau$, Evidence P/R@$\tau$, và $\text{CGI}@\tau$: chỉ cho phép các cạnh $\text{IoU}(p, j) \ge \tau$, cực đại hóa số cặp ghép hợp lệ (cardinality), tie-break bằng tổng IoU;
   - và cấm tuyệt đối việc trộn lẫn hoặc dùng thay thế hai chế độ này cho nhau hay không?
10. **Chỉ số đánh giá Weak Proxy:** Chấp thuận chỉ số **Identity-Agnostic Proxy Localization Consistency (Identity-Agnostic PLC)** (Primary là Center-in-Proxy trên bất kỳ đa giác người nào; Box Containment làm chẩn đoán), kiểm soát độ nhạy qua **Single-Person Proxy Subset** (410 mẫu, 614 atoms), cấm gọi là true grounding accuracy và bắt buộc báo cáo tách biệt khỏi Direct track hay không?
11. **Bản chất của Evidence Precision / Recall:** Chấp thuận công nhận Evidence P/R là chỉ số tương đối theo benchmark hiện có (không đồng nhất unmatched prediction với ảo giác ngoài đời thực), báo cáo song song ở ngưỡng 0.25 và 0.50 hay không?
12. **Tham số hóa chỉ số không nhất quán phân loại - định vị:** Chấp thuận tham số hóa thành **$\text{CGI}@\tau$**, báo cáo song song tại $\text{CGI}@0.25$ và $\text{CGI}@0.50$, và cấm dùng ký hiệu CGI thiếu hậu tố ngưỡng hay không?
13. **Đơn vị và chính sách Parse Failure:** Chấp thuận đo lường tường minh **$\text{PSR}_{\text{response}}$** và **$\text{PSR}_{\text{box}}$**, coi lỗi parse là miss ($\text{IoU}=0.0$) trong End-to-End Grounding, và báo cáo Parse-Conditional Mean IoU làm chẩn đoán hay không?
14. **Phân tích chẩn đoán Kích thước đối tượng và Mức độ hiếm:** Chấp thuận định nghĩa đại lượng vô hướng ở cấp độ nguy cơ nguyên tử $\text{AtomSize}(j) = \max_{r \in R_j} \frac{\text{Area}(r)}{W \times H} \in [0, 1]$ độc lập với mô hình dự đoán và đồng bộ với điểm cạnh IoU, đi kèm biến số lượng vùng hỗ trợ $|R_j|$ (phân biệt 87,07% single-region vs 12,93% multi-region) và tần suất xuất hiện liên tục $N$; duy trì thang đo liên tục, cấm chia bin Small/Medium/Large cơ học trong giao thức W2.4; và định vị độc quyền các biến này là phân tích chẩn đoán phụ trợ (`Diagnostic Covariates`), không làm thay đổi các bảng tổng hợp kết quả chính thức hay không?
15. **Phạm vi chỉ số Object Hallucination:** Chấp thuận loại bỏ hoàn toàn chỉ số Object Hallucination Rate trên toàn bộ dataset trong khuôn khổ Seminar 8 tuần, và không mở thêm chiến dịch kiểm tra thủ công 30–50 ảnh trong scope cốt lõi hay không?
16. **Phương pháp Domain-Stratified Point-Cluster Bootstrap:** Chấp thuận áp dụng **Domain-Stratified Point-Cluster Bootstrap** (phân tầng theo miền, resample theo cụm `point_id` trong từng miền, không phân tầng theo nhãn an toàn để tránh lỗi singleton strata), cấu hình $B = 2.000$ replicates, seed = 42, khoảng tin cậy Percentile 95%, replicate khuyết lớp ghi nhận NA và báo cáo tỷ lệ `Valid Replicates / B` hay không?
17. **Phương pháp so sánh mô hình VLM:** Chấp thuận sử dụng **Paired Bootstrap Difference CI 95%** trên cùng tập replicate (báo cáo `Valid Paired Replicates / B`) làm công cụ so sánh chính, diễn giải CI không chứa 0 là chênh lệch có hướng rõ ràng, và không chạy ma trận $p$-value mặc định hay không?

*(Lưu ý: Danh sách mô hình thử nghiệm chi tiết và câu chữ câu lệnh prompt không thuộc thẩm quyền của D5 và sẽ được giải quyết tại bước W2.5).*

---

## 26. Evidence Sources

Báo cáo căn cứ W2.4 được xây dựng dựa trên sự tổng hợp của toàn bộ các tài liệu kiểm toán và quyết định thực chứng độc lập:

1. **Quyết định đã khóa:**
   - [DECISIONS.md — DEC-W2-D1-001](../DECISIONS.md#dec-w2-d1-001): Phân tầng giao thức và Research Framing.
   - [DECISIONS.md — DEC-W2-D2-002](../DECISIONS.md#dec-w2-d2-002): Không gian đánh giá P1/P2/P3, đơn vị ảnh và gom nhóm Normal `point_id`.
   - [DECISIONS.md — DEC-W2-D3-003](../DECISIONS.md#dec-w2-d3-003): Nhãn miền thao tác `folder_domain` và chính sách 36 mẫu mismatch.
   - [DECISIONS.md — DEC-W2-D4-004](../DECISIONS.md#dec-w2-d4-004): Chuẩn hóa hộp bao canonical $[x_{\min}, y_{\min}, x_{\max}, y_{\max}] \in [0, 1]$ và lưu trữ raw response.
   - [DECISIONS.md — DEC-W2-D6-006](../DECISIONS.md#dec-w2-d6-006): Hệ phân loại 12 Nguy cơ Nguyên tử và kiểm kê 781 Direct / 947 Proxy atoms.
   - [DECISIONS.md — DEC-W2-D7-007](../DECISIONS.md#dec-w2-d7-007): Chính sách không tự gán nhãn rationale mới và loại bỏ Object Hallucination Rate toàn bộ dataset.
2. **Báo cáo căn cứ và kiểm toán kỹ thuật:**
   - [notes/w2_grounding_census_decision_brief.md](w2_grounding_census_decision_brief.md): Báo cáo tổng điều tra thực chứng 1.000 mẫu Anomaly.
   - [notes/w2_domain_split_decision_brief.md](w2_domain_split_decision_brief.md): Báo cáo phân bổ miền và rò rỉ phân chia.
   - [notes/w2_protocol_decision_brief.md](w2_protocol_decision_brief.md): Báo cáo phương pháp luận phân tầng giao thức P1–P4.
   - [notes/w1_dataset_audit.md](w1_dataset_audit.md): Báo cáo kiểm toán tổng thể Tuần 1.
   - [notes/distribution_imbalance_audit.md](distribution_imbalance_audit.md): Kiểm toán mất cân bằng phân bố và hỗ trợ nhãn.
   - [notes/research_feasibility_audit.md](research_feasibility_audit.md): Báo cáo tính khả thi nghiên cứu và giới hạn bằng chứng.
3. **Artifacts và Script kiểm chứng:**
   - Dấu vân tay mật mã dữ liệu đầu vào (SHA-256): `7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`
   - Bảng tổng điều tra nguy cơ nguyên tử: `data/manifests/w2_grounding_census.json` (SHA-256: `cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`).
   - Script kiểm chuẩn thời gian thực thi bootstrap: `scratch/w2_4_metrics_scratch.py` ($B=2.000$ đạt thời gian 3,96s trên CPU x64).
   - Script kiểm toán vùng GT và phân tầng nguy cơ: `scratch/audit_gt_regions.py` (SHA-256: `90c704af291fb34725b6a679f3bdb2a84d18297628c569497e34309ed49cee50`). Thực thi trên Python 3.11.9, Windows 11 x64, timestamp `2026-09-17 05:22:14 UTC`; kiểm toán cấu trúc $N=781$ Direct atoms (680 single-region / 101 multi-region), $N=947$ Proxy atoms (614 single-person / 333 multi-person), và 512 mẫu đa nguy cơ với 1.381 lượt thành viên trên 7 tầng. Ghi chú: Local scratch script, không commit vào Git repo (`no repo-alone reproducibility claim`).
