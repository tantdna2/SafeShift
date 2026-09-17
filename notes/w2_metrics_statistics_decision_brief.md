# W2.4 Metrics & Statistical Protocol Decision Brief

- **Tài liệu:** Báo cáo căn cứ quyết định chỉ số đánh giá và giao thức thống kê (W2.4 Metrics & Statistical Evaluation Protocol Decision Brief)
- **Dự án:** SafeShift: Benchmarking Cross-Domain Generalization and Evidence Grounding in Vision-Language Models for Industrial Safety Assessment
- **Bộ dữ liệu:** InspecSafe-V1 (5.013 mẫu ảnh: 4.013 Normal, 1.000 Anomaly)
- **Trạng thái:** BÁO CÁO CĂN CỨ KỸ THUẬT (TECHNICAL EVIDENCE BRIEF) — ĐỀ XUẤT CHO QUYẾT ĐỊNH D5 (CHƯA PHÊ DUYỆT)
- **Ngày lập:** 2026-09-17
- **Phiên bản:** 1.1.0 (Exact Schema Edition)

---

## 1. Purpose

Văn bản này thiết lập cơ sở lý thuyết, bằng chứng thực nghiệm và phân tích phương pháp luận cho bước **W2.4 — Metrics & Statistical Evaluation Protocol** của dự án SafeShift, chuẩn bị căn cứ khoa học cho **Quyết định D5 — Giao thức chỉ số và thống kê đánh giá (Metrics & Statistical Evaluation Protocol)**.

Báo cáo giải quyết toàn diện 7 câu hỏi phương pháp luận cốt lõi:
1. **Chỉ số phân loại (Classification Metrics):** Lựa chọn và chuẩn hóa các chỉ số đo lường năng lực phân loại mức độ an toàn công nghiệp (`Level01`–`Level04`) trong bối cảnh mất cân bằng dữ liệu cực đoan.
2. **Suy giảm hiệu năng xuyên miền (Cross-Domain Robustness Drop):** Định nghĩa công thức toán học đo lường độ phân tán và suy giảm hiệu năng giữa các phân xưởng công nghiệp mà không bị nhiễu bởi thành phần nhãn.
3. **Đánh giá bám bằng chứng (Grounding Evaluation):** Xác lập tiêu chuẩn định lượng cho đường đua định vị hộp bao không gian trên tập đối tượng hỗ trợ trực tiếp.
4. **Phân rã Direct Object-Support và Weak Proxy:** Phân định phương pháp đo lường và cách diễn giải riêng biệt giữa bằng chứng trực tiếp và vùng đại diện thân người.
5. **Định lượng bất định và khoảng tin cậy (Uncertainty & Confidence Intervals):** Xây dựng quy trình bootstrap kiểm soát cấu trúc phụ thuộc cụm đa khung hình của dữ liệu tuần tra.
6. **Chính sách miền luyện kim và lớp hiếm (Metallurgy & Rare-Class Policy):** Xử lý mẫu số nhỏ ($N_{\text{anomaly}}=9$, $N_{\text{Level03}}=15$) và các trường hợp lớp thiếu nhằm tránh ngụy biện thống kê.
7. **So sánh đa mô hình VLM (Model Comparison):** Thiết lập nguyên tắc so sánh theo cặp (paired comparisons) và kiểm định thống kê tối thiểu cho Seminar 8 tuần.

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
- *Nhược điểm:* Cực kỳ nhạy cảm và trừng phạt rất nặng khi một lớp hiếm có $N_c$ rất nhỏ bị $\text{TP}_c = 0$ (khi đó $\text{F1}_c = 0$, kéo tụt toàn bộ Macro-F1 xuống 25%).

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
SafeShift đề xuất áp dụng **Balanced Accuracy** và **Macro-F1** làm **hai chỉ số chính song hành (Primary Co-Metrics)** cho bài toán phân loại 4 lớp. Sự kết hợp này bù trừ hoàn hảo cho nhau: Balanced Accuracy đo lường năng lực bao quát an toàn không phụ thuộc tần suất xuất hiện, trong khi Macro-F1 bảo đảm mô hình duy trì độ đặc hiệu và không tạo ra tỷ lệ báo động giả mất kiểm soát.

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
     - So sánh `Recall(Level01, d)` trên 4 miền có hỗ trợ mạnh ($N \ge 33$); riêng `metallurgy` ($N=8$) chỉ mang tính mô tả.
     - So sánh Binary Anomaly Recall / FNR trên các miền có dữ liệu bất thường.
3. **Quy tắc cấm tuyệt đối:** Không bao giờ sử dụng chỉ số tổng hợp của một miền thiếu lớp ($K < 4$) để xếp hạng hay tuyên bố miền đó là "tốt nhất" hoặc "tệ nhất".

---

## 7. Cross-Domain Robustness Metrics

Giảng viên hướng dẫn yêu cầu báo cáo chỉ số **Cross-Domain Drop** (Mức suy giảm hiệu năng xuyên miền). Tuy nhiên, việc áp dụng máy móc các công thức truyền thống sẽ dẫn đến kết luận sai lệch do hiện tượng nhiễu thành phần nhãn (label composition confounding).

### 7.1 Phân tích ba công thức ứng viên

#### Định nghĩa A — Pooled-to-Domain Gap (Độ lệch gộp - miền):
$$\Delta_{\text{drop}}(M, d) = M_{\text{pooled}} - M_d \quad (\text{đơn vị: điểm phần trăm — percentage points, pp})$$
Trong đó $M_{\text{pooled}}$ là chỉ số tính trên toàn bộ 5.013 mẫu gộp của P2, và $M_d$ là chỉ số của miền $d$.

- *Phê phán phương pháp luận:* Phân bố lớp giữa các miền bị lệch cực độ:
  - `metallurgy`: 98,75% là Normal (`Level04`).
  - `oil_chemical`: 35,29% là Anomaly (trong đó 29,7% là `Level01`).
  - `coal_conveyor`: 22,84% là Anomaly.
  Nếu một mô hình VLM có xu hướng dự đoán thiên lệch về `Level04` (ví dụ: Recall Level04 = 95%, Recall Level01 = 30%), Raw Accuracy của mô hình ở `metallurgy` sẽ đạt $\approx 94\%$, trong khi ở `oil_chemical` chỉ đạt $\approx 72\%$. Nếu lấy $M_{\text{pooled}} - M_d$, ta sẽ thấy `oil_chemical` có "drop" rất lớn (+10pp) còn `metallurgy` có "gain" (-12pp). Sự chênh lệch này **hoàn toàn do tỷ lệ nhãn gây ra, không phản ánh độ bền vững thị giác của mô hình**!

#### Định nghĩa B — Worst-Domain Gap (Khoảng cách tới miền kém nhất):
$$\Delta_{\text{worst}}(M) = M_{\text{pooled}} - \min_{d \in \mathcal{D}_{\text{eligible}}} M_d$$
Hoặc biên độ dao động giữa miền cao nhất và miền thấp nhất (Peak-to-Trough Domain Spread):
$$\text{Range}(M) = \max_{d \in \mathcal{D}_{\text{eligible}}} M_d - \min_{d \in \mathcal{D}_{\text{eligible}}} M_d$$

#### Định nghĩa C — Class-Conditional Domain Spread (Độ phân tán xuyên miền theo từng lớp — ĐƯỢC CHỌN LÀM PRIMARY DIAGNOSTIC):
Đo lường độ phân tán của hiệu năng trên một lớp an toàn cố định $c$, chỉ xét trên các miền có đủ dữ liệu hỗ trợ cho lớp đó:
$$\text{Spread}(M_c) = \max_{d \in \mathcal{D}_c} M_c(d) - \min_{d \in \mathcal{D}_c} M_c(d)$$
Ví dụ đối với độ thu hồi nguy cơ nghiêm trọng `Level01 Recall`:
$$\text{Spread}(\text{Recall}_{\text{L01}}) = \max_{d \in \mathcal{D}_{\text{L01}}} \text{Recall}_{\text{L01}}(d) - \min_{d \in \mathcal{D}_{\text{L01}}} \text{Recall}_{\text{L01}}(d)$$
với $\mathcal{D}_{\text{L01}} = \{\text{coal\_conveyor, oil\_chemical, power, tunnel}\}$ (loại `metallurgy` vì $N=8$ quá nhỏ).

- *Ưu điểm vượt trội:* Loại bỏ hoàn toàn yếu tố gây nhiễu của tỷ lệ pha trộn lớp giữa các miền. Phản ánh trung thực: khi đối mặt cùng một loại nguy cơ `Level01`, khả năng nhận biết của mô hình biến thiên bao nhiêu giữa các môi trường phân xưởng khác nhau.

### 7.2 Đề xuất chuẩn hóa của SafeShift

1. **Primary Metric cho RQ1 (Cross-Domain Robustness):**
   - Áp dụng **Balanced Accuracy Domain Spread** trên các miền đủ điều kiện ($K_d = 4$):
     $$\text{Spread}(\text{BalAcc}) = \max_{d \in \{\text{coal, power, tunnel}\}} \text{BalAcc}_d - \min_{d \in \{\text{coal, power, tunnel}\}} \text{BalAcc}_d$$
   - Đi kèm với **Binary Anomaly Recall Domain Spread** trên 4 miền có $N_{\text{anom}} \ge 30$:
     $$\text{Spread}(\text{Recall}_{\text{anom}}) = \max_{d} \text{Recall}_{\text{anom}}(d) - \min_{d} \text{Recall}_{\text{anom}}(d)$$
2. **Sensitivity Metric:** Báo cáo bảng Pooled-to-Domain Gap $\Delta_{\text{drop}}$ cho Balanced Accuracy và Macro-F1, nhưng **bắt buộc phải đặt cạnh bảng phân bố nhãn của từng miền** để người đọc không bị dẫn dắt sai lệch.
3. **Chuẩn hóa thuật ngữ:** Bắt buộc sử dụng cụm từ **"Cross-Domain Robustness Drop / Gap"** (Độ suy giảm / độ lệch bền vững xuyên miền). **TUYỆT ĐỐI KHÔNG DÙNG** thuật ngữ **"Domain Generalization Drop"** vì Seminar không thực hiện huấn luyện trên miền nguồn.

---

## 8. Worst-Domain Reporting Policy

Giảng viên đặc biệt quan tâm tới hiệu năng ở "miền kém nhất" (`worst-domain performance`). Tuy nhiên, việc tự động lấy giá trị cực tiểu $\min_d M_d$ mà không xét đến quy mô mẫu sẽ dẫn đến những kết luận ngụy tạo tai hại.

### 8.1 Bài học cảnh giác từ Miền Luyện kim (`metallurgy`)

Trong P2, miền `metallurgy` chỉ có đúng **9 mẫu Anomaly**:
- 8 mẫu `Level01`
- 0 mẫu `Level02`
- 1 mẫu `Level03`
- 711 mẫu `Level04`

Nếu một mô hình dự đoán sai 4 trên 9 mẫu Anomaly này, tỷ lệ Anomaly Recall của `metallurgy` sẽ là $5 / 9 = 55,6\%$.
Nếu mô hình đoán đúng thêm đúng 1 mẫu, tỷ lệ vọt lên $6 / 9 = 66,7\%$ (bước nhảy $11,1\%$ chỉ vì 1 mẫu duy nhất!).
Đặc biệt, theo phân tích độ nhạy Sensitivity B (tái phân bổ theo văn bản), `metallurgy` chỉ còn đúng **1 mẫu Anomaly duy nhất**. Nếu mô hình đoán sai mẫu này, Recall lập tức rơi về **0,0%**!
Nếu hệ thống tự động quét và tuyên bố: *"Luyện kim là miền có hiệu năng phát hiện nguy cơ kém nhất với độ thu hồi 0%"*, kết luận đó hoàn toàn là một ảo ảnh thống kê bắt nguồn từ cỡ mẫu cực tiểu, không mang bất kỳ giá trị khoa học nào.

### 8.2 Quy trình 4 bước báo cáo Worst-Domain chuẩn mực

SafeShift xác lập chính sách 4 điều kiện nghiêm ngặt:

```
┌─────────────────────────────────────────────────────────────────────────┐
│              QUY TRÌNH XÁC LẬP VÀ BÁO CÁO WORST-DOMAIN                  │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
     ┌───────────────────────────────────────────────────────────────┐
     │ 1. BỘ LỌC ĐỦ ĐIỀU KIỆN (ELIGIBILITY FILTER)                   │
     │    - Đánh giá 4 lớp: Yêu cầu đủ 4 lớp GT (K_d = 4).           │
     │    - Đánh giá Anomaly: Yêu cầu N_anom >= 30 mẫu.              │
     │    => Metallurgy (N=9) BỊ LOẠI KHỎI XẾP HẠNG TỰ ĐỘNG.         │
     └───────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
     ┌───────────────────────────────────────────────────────────────┐
     │ 2. CÔNG BỐ MẪU SỐ BẮT BUỘC (DENOMINATOR DISCLOSURE)           │
     │    Mọi ô số liệu phải kèm theo mẫu số thực tế (k / N).        │
     └───────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
     ┌───────────────────────────────────────────────────────────────┐
     │ 3. GẮN CỜ CẢNH BÁO DỮ LIỆU THƯA (SPARSE-SUPPORT WARNING)      │
     │    Gắn cờ [*] hoặc [Descriptive] nếu N < 30.                  │
     └───────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
     ┌───────────────────────────────────────────────────────────────┐
     │ 4. PHÂN HẠNG MIỀN CHỈ MÔ TẢ (DESCRIPTIVE-ONLY DESIGNATION)    │
     │    Metallurgy được trình bày đầy đủ nhưng dán nhãn            │
     │    DESCRIPTIVE-ONLY, không tham gia tranh giải worst-domain.  │
     └───────────────────────────────────────────────────────────────┘
```

1. **Điều kiện đủ để tham gia xếp hạng (Eligibility Filter):**
   - Để được xét vào danh sách ứng viên "Worst Domain" cho các chỉ số Anomaly (Anomaly Recall, Anomaly FNR), miền công nghiệp bắt buộc phải có quy mô mẫu bất thường tối thiểu:
     $$N_{\text{anomaly}, d} \ge N_{\text{min}} = 30\text{ mẫu}$$
   - Theo tiêu chuẩn này: `coal_conveyor` ($N=256$), `oil_chemical` ($N=361$), `power` ($N=102$), và `tunnel` ($N=272$) là **đủ điều kiện (`ELIGIBLE`)**.
   - Miền `metallurgy` ($N=9$ ở P2, $N=0$ ở P1) **không đủ điều kiện tham gia xếp hạng cạnh tranh (`INELIGIBLE FOR RANKING`)**.
2. **Minh bạch mẫu số bắt buộc (Denominator Disclosure):** Mọi bảng báo cáo hiệu năng từng miền bắt buộc phải ghi rõ mẫu số thực nghiệm trong tiêu đề cột hoặc trong từng ô số liệu dưới dạng $(k / N_d)$.
3. **Cảnh báo hỗ trợ thưa thớt (Partial-Support Warning):** Mọi ô có mẫu số $N < 30$ hoặc số lớp $K_d < 4$ phải được gắn ký hiệu cảnh báo rõ ràng.
4. **Phân hạng miền chỉ mang tính mô tả (Descriptive-Only Designation):** Miền `metallurgy` được báo cáo số liệu đầy đủ và trung thực trong bảng chi tiết, nhưng được chú thích rõ ràng là **"Chỉ mang tính mô tả (Descriptive-Only)"** cho các chỉ số bất thường.

---

## 9. Direct Grounding Metrics

Đường đua **RQ3-A — Direct Object-Support Grounding** đánh giá năng lực của VLM trong việc khoanh vùng chính xác đối tượng vật lý trực tiếp làm bằng chứng cho khẳng định nguy cơ.

### 9.1 Cơ sở dữ liệu và định dạng hộp bao

- **Quy mô tập đánh giá:** Theo Quyết định D6, toàn bộ tập dữ liệu có đúng **781 Direct atoms** phân bố trên **721 mẫu ảnh** thuộc `Direct-Support Sample Pool`.
- **Định dạng hộp bao chuẩn mực (D4):**
  $$\mathbf{b} = [x_{\min}, y_{\min}, x_{\max}, y_{\max}] \in [0.0, 1.0]$$
  với gốc tọa độ $(0, 0)$ ở góc trên bên trái, chuẩn hóa theo kích thước ảnh thực tế $(W, H)$.
- **Hộp bao Ground Truth:** Được suy biến toán học tất định (`derived`) từ đa giác cực biên của các đối tượng trực tiếp:
  $$x_{\min} = \frac{\min_i x_i^{\text{poly}}}{W}, \quad y_{\min} = \frac{\min_i y_i^{\text{poly}}}{H}, \quad x_{\max} = \frac{\max_i x_i^{\text{poly}}}{W}, \quad y_{\max} = \frac{\max_i y_i^{\text{poly}}}{H}$$

### 9.2 Các chỉ số định vị không gian ứng viên

#### A. Chỉ số giao thoa trên diện tích hợp (Intersection over Union — IoU)
Với hộp bao dự đoán $\mathbf{b}_{\text{pred}}$ và hộp bao chuẩn $\mathbf{b}_{\text{gt}}$:
$$\text{IoU}(\mathbf{b}_{\text{pred}}, \mathbf{b}_{\text{gt}}) = \frac{\text{Area}(\mathbf{b}_{\text{pred}} \cap \mathbf{b}_{\text{gt}})}{\text{Area}(\mathbf{b}_{\text{pred}} \cup \mathbf{b}_{\text{gt}})}$$
Trong đó diện tích phần giao được tính:
$$\text{Area}(\mathbf{b}_{\text{pred}} \cap \mathbf{b}_{\text{gt}}) = \max\left(0, \min(x_{\max}^p, x_{\max}^g) - \max(x_{\min}^p, x_{\min}^g)\right) \times \max\left(0, \min(y_{\max}^p, y_{\max}^g) - \max(y_{\min}^p, y_{\min}^g)\right)$$

#### B. Mean IoU (mIoU) và Median IoU
- **Overall Mean IoU:** Trung bình IoU trên toàn bộ 781 Direct atoms đánh giá được. Những trường hợp mô hình không dự đoán hộp bao hoặc phân tích cú pháp thất bại được gán $\text{IoU} = 0.0$.
- **Conditional Mean IoU:** Trung bình IoU chỉ tính trên các cặp dự đoán đã khớp thành công với GT atom ($\text{IoU} > 0$). Phản ánh độ chặt chẽ của việc bao ranh giới khi mô hình đã nhìn đúng vật thể.
- **Median IoU:** Trung vị IoU, kháng ảnh hưởng của các giá trị ngoại lai cực đoan.

#### C. Localization Hit@$\tau$ (Tỷ lệ định vị trúng đích theo ngưỡng)
Một nguyên tử nguy cơ GT được coi là định vị trúng đích nếu tồn tại ít nhất một hộp bao dự đoán tương ứng đạt:
$$\text{Hit}@\tau = \mathbb{I}(\text{IoU}(\mathbf{b}_{\text{pred}}, \mathbf{b}_{\text{gt}}) \ge \tau)$$
Tỷ lệ trúng đích trên toàn tập:
$$\text{Localization Hit Rate}@\tau = \frac{1}{N_{\text{evaluable\_atoms}}} \sum_{j=1}^{N_{\text{evaluable\_atoms}}} \text{Hit}_j@\tau$$

#### D. Pointing Hit (Tọa độ tâm dự đoán nằm trong vùng GT)
Đo lường năng lực định hướng thị giác thô (Pointing Game). Xác định tọa độ điểm tâm của hộp bao dự đoán:
$$\mathbf{c}_{\text{pred}} = \left(\frac{x_{\min}^p + x_{\max}^p}{2}, \frac{y_{\min}^p + y_{\max}^p}{2}\right)$$
Pointing Hit đạt giá trị 1 nếu điểm tâm rơi vào bên trong hộp bao GT $\mathbf{b}_{\text{gt}}$ (hoặc bên trong đa giác gốc $\text{Polygon}_{\text{gt}}$):
$$\text{PointingHit} = \mathbb{I}(\mathbf{c}_{\text{pred}} \in \mathbf{b}_{\text{gt}})$$

### 9.3 Phân tích ngưỡng IoU (IoU Threshold: 0.25 vs 0.50 vs Continuous)

Việc lựa chọn ngưỡng $\tau$ cho chỉ số $\text{Hit}@\tau$ trong SafeShift đòi hỏi sự phân tích phương pháp luận sâu sắc, tuyệt đối không được sao chép cơ học ngưỡng $\tau = 0.50$ từ các bài toán phát hiện đối tượng truyền thống (Object Detection / COCO):
1. **Bản chất hộp bao trong InspecSafe-V1 là Bounding Box phái sinh:**
   Các đối tượng nguy cơ như vũng chất lỏng đọng trên sàn (`LIQUID_ON_GROUND`), vệt khói bốc lên (`SMOKE`), ngọn lửa trần (`OPEN_FLAME`) có hình học phi lồi và ranh giới phức tạp. Hộp bao chữ nhật cực biên bao quanh một đa giác ngoằn ngoèo thường chứa nhiều diện tích nền trống. Do đó, một mô hình VLM định vị đúng lõi của vệt dầu có thể chỉ đạt IoU khoảng $0.30 - 0.40$ so với hộp bao cực biên. Việc áp đặt $\tau = 0.50$ sẽ loại bỏ oan các trường hợp mô hình định vị chính xác về mặt thị giác.
2. **Năng lực định vị của mô hình ngôn ngữ - thị giác đóng băng trọng số:**
   Các VLM tổng quát không được huấn luyện chuyên biệt về hồi quy tọa độ pixel chính xác như Faster R-CNN hay YOLO. Chúng thực hiện định vị thô thông qua sinh token văn bản. Y văn quốc tế về Grounding trên VLM (như RefCOCO loose evaluation) thừa nhận ngưỡng $\tau = 0.25$ phân tách ranh giới rõ ràng giữa việc mô hình thực sự chú ý vào thực thể so với việc phỏng đoán ngẫu nhiên.
3. **Mô phỏng xác suất đoán ngẫu nhiên:**
   Một hộp bao dự đoán ngẫu nhiên có kích thước trung bình 20% khung hình chỉ có xác suất $\text{IoU} \ge 0.25$ với một vật thể nhỏ dưới **0,5%**, trong khi xác suất đạt $\text{IoU} \ge 0.10$ là đáng kể. Do đó, $\tau = 0.25$ hoàn toàn đảm bảo tính nghiêm ngặt về mặt thống kê.

- **Khuyến nghị chuẩn hóa:**
  - **Primary Thresholded Metric:** **$\text{Hit}@0.25$**.
  - **Continuous Benchmark Metric:** **Mean IoU** (báo cáo đồng thời Overall mIoU và Conditional mIoU).
  - **Secondary Sensitivity Threshold:** **$\text{Hit}@0.50$** (đối chiếu với chuẩn CV truyền thống).
  - **Diagnostic Metric:** **Pointing Hit**.

### 9.4 Ghép cặp nhiều GT / nhiều dự đoán (Multiple GT / Multiple Prediction Matching)

Để tính toán các chỉ số Evidence Precision và Evidence Recall một cách chặt chẽ, SafeShift đề xuất quy trình ghép cặp tham lam một-đối-một (Greedy One-to-One Matching) trong cùng phân loại nguy cơ:
1. *Bước 1:* Tính ma trận IoU kích thước $M \times K$ giữa $M$ hộp bao dự đoán và $K$ GT atoms.
2. *Bước 2:* Lọc các cặp ứng viên có $\text{IoU} \ge \tau$ (với $\tau = 0.25$).
3. *Bước 3:* Sắp xếp tập cặp ứng viên theo giá trị IoU giảm dần.
4. *Bước 4:* Lặp qua từng cặp: nếu dự đoán $p_i$ chưa ghép VÀ GT atom $g_j$ chưa ghép, xác lập ghép đôi và tăng $\text{TP} \mathrel{+}= 1$.
5. *Bước 5:* Các dự đoán dư thừa tính là False Positives ($\text{FP} = M - \text{TP}$); các GT atom bị bỏ sót tính là False Negatives ($\text{FN} = K - \text{TP}$).

Quy trình này triệt tiêu hoàn toàn hiện tượng "một hộp bao khổng lồ ăn nhiều GT" hoặc "nhiều hộp bao trùng lặp ăn một GT".

---

## 10. Weak-Proxy Metrics

Đường đua **RQ3-B — Weak Proxy Grounding** xử lý **947 Weak-Proxy atoms** trên **608 mẫu ảnh** (chủ yếu là các vi phạm thiếu trang bị bảo hộ lao động: `NO_GLOVES`, `NO_HELMET`, `NO_MASK`, hành vi `SMOKING`, hoặc `PERSON_FALLEN`).

### 10.1 Bản chất ngụy biện nếu áp dụng IoU cho Weak Proxy

Trong dữ liệu InspecSafe-V1, khi công nhân vi phạm không đội mũ bảo hộ (`NO_HELMET`), annotator gốc **chỉ khoanh đa giác toàn thân người (`Person`)**, hoàn toàn không có hộp bao vùng đầu hay chiếc mũ vắng mặt.
- Hộp bao `Person` bao trùm toàn bộ cơ thể từ đầu đến chân.
- Diện tích vùng đầu của một công nhân thông thường chỉ chiếm khoảng **$10\% - 15\%$** diện tích toàn thân.
- Nếu một mô hình VLM thông minh định vị chính xác vùng đầu của người công nhân (nơi thiếu chiếc mũ bảo hộ), diện tích giao nhau giữa hộp bao đầu và hộp bao toàn thân chính bằng diện tích đầu, trong khi diện tích hợp bằng diện tích toàn thân. Khi đó:
  $$\text{IoU}(\mathbf{b}_{\text{head}}, \mathbf{b}_{\text{person}}) \approx \frac{0,12 \times \text{Area}_{\text{person}}}{\text{Area}_{\text{person}}} = \mathbf{0,12}$$
- **Hậu quả thảm họa về phương pháp luận:** Nếu áp dụng máy móc tiêu chí $\text{IoU} \ge 0.25$ hay $\ge 0.50$, một mô hình định vị chính xác hoàn hảo vào vùng đầu người sẽ bị chấm là **THẤT BẠI (FAIL)**! Ngược lại, một mô hình lười biếng chỉ khoanh bừa một chiếc hộp bao khổng lồ trùm lên cả người công nhân lại đạt $\text{IoU} \ge 0.80$ và được chấm là **THÀNH CÔNG**!

### 10.2 Các chỉ số ứng viên cho Weak Proxy

Để phản ánh trung thực bài toán, SafeShift loại bỏ hoàn toàn IoU làm thước đo chất lượng chính cho Weak Proxy, và thay thế bằng các chỉ số tương thích vùng:

#### 1. Point-in-Proxy / Center-in-Proxy
Kiểm tra xem tọa độ tâm của hộp bao dự đoán $\mathbf{c}_{\text{pred}}$ có nằm gọn bên trong vùng đại diện $\mathbf{b}_{\text{proxy}}$ hay không:
$$\text{Center-in-Proxy} = \mathbb{I}(\mathbf{c}_{\text{pred}} \in \mathbf{b}_{\text{proxy}})$$

#### 2. Predicted Box Containment (Tỷ lệ hộp dự đoán nằm trong Proxy)
Đo lường tỷ lệ phần trăm diện tích của hộp bao dự đoán nằm gọn bên trong vùng đại diện của con người:
$$\text{Containment}(\mathbf{b}_{\text{pred}}, \mathbf{b}_{\text{proxy}}) = \frac{\text{Area}(\mathbf{b}_{\text{pred}} \cap \mathbf{b}_{\text{proxy}})}{\text{Area}(\mathbf{b}_{\text{pred}})}$$
Một dự đoán đạt chuẩn nhất quán nếu:
$$\text{ProxyHit}@\tau_{\text{contain}} = \mathbb{I}\left(\text{Containment}(\mathbf{b}_{\text{pred}}, \mathbf{b}_{\text{proxy}}) \ge \tau_{\text{contain}}\right), \quad \text{với } \tau_{\text{contain}} = 0,50$$
(Nghĩa là ít nhất 50% diện tích chiếc hộp mà mô hình khoanh ra phải nằm trên cơ thể của người công nhân vi phạm).

#### 3. Any-Overlap (Giao thoa diện tích dương)
$$\text{Any-Overlap} = \mathbb{I}\left(\text{Area}(\mathbf{b}_{\text{pred}} \cap \mathbf{b}_{\text{proxy}}) > 0\right)$$

### 10.3 Chuẩn hóa tên gọi và quy tắc báo cáo tách biệt

- **Chuẩn hóa tên gọi bắt buộc:** Chỉ số này được gọi chính thức là:
  **"Proxy Localization Consistency" (PLC — Mức độ nhất quán định vị với vùng đại diện)**.
- **Quy tắc cấm tuyệt đối:**
  - **TUYỆT ĐỐI KHÔNG GỌI** chỉ số này là "True Evidence Grounding Accuracy" (Độ chính xác bám bằng chứng thật).
  - **TUYỆT ĐỐI KHÔNG ĐƯỢC GỘP** điểm số của Direct Track và Proxy Track thành một điểm trung bình duy nhất. Hai đường đua này bắt buộc phải báo cáo ở hai cột/bảng riêng biệt.

---

## 11. Evidence Precision/Recall

Chỉ số **Evidence Precision** và **Evidence Recall** đánh giá toàn diện khả năng của mô hình: vừa nhận diện đúng bản chất nguy cơ, vừa chỉ ra đúng vị trí bằng chứng trên ảnh.

### 11.1 Đơn vị đánh giá (Evaluation Unit)

- Đơn vị đánh giá chuẩn mực được xác lập ở cấp độ: **Nguy cơ Nguyên tử (`Hazard-Atom Level`)** trên tập **Direct Object-Support Track**.
- Tổng số nguyên tử có thể đánh giá: $N_{\text{evaluable\_direct}} = 781\text{ atoms}$.

### 11.2 Công thức toán học định nghĩa

Đối với từng loại nguy cơ nguyên tử $h \in \mathcal{H}_{\text{direct}}$:
- $\text{TP}_h$: Số cặp dự đoán ghép thành công với một GT atom loại $h$ và đạt $\text{IoU} \ge \tau$.
- $\text{FP}_h$: Số hộp bao mô hình gán nhãn nguy cơ $h$ nhưng không ghép được với GT atom nào của loại $h$ (do định vị sai vị trí hoặc đoán mò nguy cơ không có thật).
- $\text{FN}_h$: Số GT atoms loại $h$ không có hộp bao dự đoán nào ghép trúng.

$$\text{Evidence Recall}_h = \frac{\text{TP}_h}{\text{GT}_h} = \frac{\text{TP}_h}{\text{TP}_h + \text{FN}_h}$$
$$\text{Evidence Precision}_h = \frac{\text{TP}_h}{\text{Pred}_h} = \frac{\text{TP}_h}{\text{TP}_h + \text{FP}_h}$$
$$\text{Evidence F1}_h = \frac{2 \cdot \text{Evidence Precision}_h \cdot \text{Evidence Recall}_h}{\text{Evidence Precision}_h + \text{Evidence Recall}_h}$$

Tổng hợp toàn cục:
- **Macro Evidence Metrics:** Trung bình số học không trọng số trên các loại nguy cơ nguyên tử trực tiếp.
- **Micro Evidence Metrics:** Tính tổng $\sum \text{TP}$, $\sum \text{FP}$, $\sum \text{FN}$ trên toàn bộ 781 atoms trực tiếp.

### 11.3 Phân rã sai số: Nhận diện sai vs Định vị sai

Một thất bại bám bằng chứng có thể bắt nguồn từ hai nguyên nhân hoàn toàn khác nhau:
1. **Lỗi nhận diện ngữ nghĩa (Hazard Recognition Error):** Mô hình không nhận ra có nguy cơ, hoặc nhận diện sai loại nguy cơ.
2. **Lỗi định vị không gian (Spatial Localization Error):** Mô hình gọi đúng tên nguy cơ trong văn bản, nhưng xuất tọa độ hộp bao lệch hoàn toàn khỏi vật thể ($\text{IoU} < \tau$).

Do đó, SafeShift đề xuất chỉ số phân rã bổ trợ:
$$\text{Localization Recall | Correct Hazard} = \frac{\text{TP}_{\text{grounded}}}{\text{TP}_{\text{hazard\_classified}}}$$
Chỉ số này đo lường thuần túy chất lượng định vị hình học khi mô hình đã hiểu đúng bài toán ngữ nghĩa.

---

## 12. Parse-Failure Policy

Quyết định D4 yêu cầu toàn bộ phản hồi dạng chuỗi thô của VLM phải được lưu trữ nguyên văn và chuyển đổi qua bộ điều hợp/phân tích cú pháp (`Adapter / Parser`). Trong thực tế, VLM có thể gặp lỗi phân tích cú pháp (`Parse Failure`): không xuất tọa độ, xuất định dạng JSON/chuỗi bị vỡ, hoặc xuất tọa độ nằm ngoài dải hợp lệ.

### 12.1 Nguyên tắc báo cáo song song bắt buộc

SafeShift từ chối việc chỉ chọn một trong hai cách xử lý cực đoan (hoặc bỏ qua lỗi cú pháp, hoặc phạt ngầm mà không giải thích). Thay vào đó, giao thức bắt buộc phải báo cáo đồng thời bộ ba chỉ số:

```
                               ┌─────────────────────────────────────────┐
                               │       PHẢN HỒI THÔ CỦA MÔ HÌNH VLM      │
                               └─────────────────────────────────────────┘
                                                    │
                                     ┌──────────────┴──────────────┐
                                     ▼                             ▼
                        ┌────────────────────────┐    ┌────────────────────────┐
                        │ PARSE THÀNH CÔNG       │    │ PARSE THẤT BÀI         │
                        │ (Valid Coordinates)    │    │ (Syntax/Format Error)  │
                        └────────────────────────┘    └────────────────────────┘
                                     │                             │
                                     │                             ▼
                                     │               ┌───────────────────────────┐
                                     │               │ Parse Success Rate (PSR)  │
                                     │               │     bị ghi nhận giảm      │
                                     │               └───────────────────────────┘
                                     │                             │
                     ┌───────────────┴───────────────┐             │
                     ▼                               ▼             ▼
       ┌───────────────────────────┐   ┌─────────────────────────────────────────┐
       │ CONDITIONAL LOCALIZATION  │   │ END-TO-END GROUNDING (PRIMARY)          │
       │ (Chỉ tính trên mẫu parse) │   │ - Parse Failure tính là MISS (IoU = 0)  │
       │ Phản ánh năng lực thị giác│   │ - Phản ánh năng lực triển khai thực tế  │
       └───────────────────────────┘   └─────────────────────────────────────────┘
```

#### 1. Tỷ lệ phân tích cú pháp thành công (Parse Success Rate — PSR):
$$\text{PSR} = \frac{N_{\text{parsed\_successfully}}}{N_{\text{total\_samples}}}$$
Phản ánh mức độ tuân thủ mệnh lệnh cấu trúc (`instruction following`) của mô hình.

#### 2. End-to-End Grounding (Chỉ số bám bằng chứng đầu - cuối — PRIMARY):
Mọi trường hợp lỗi parse hoặc không xuất tọa độ **được tính là THẤT BẠI HOÀN TOÀN ($\text{IoU} = 0.0$, False Negative)**.
- *Lý do:* Trong một hệ thống an toàn công nghiệp tự động, nếu mô hình không xuất ra được tọa độ hợp lệ để hệ thống camera an ninh hướng tới, việc phân tích không thể diễn ra và nguy cơ bị bỏ sót hoàn toàn trong thực tế.

#### 3. Conditional Localization Quality (Chất lượng định vị có điều kiện — DIAGNOSTIC):
Tính toán Mean IoU, Hit@0.25, Evidence Precision/Recall **chỉ trên tập các mẫu parse thành công**.
- *Lý do:* Giúp phân tách rõ ràng: mô hình thất bại do không biết xuất định dạng chuẩn hay do năng lực hiểu biết thị giác kém.

---

## 13. Unsupported-Atom Policy

Cuộc tổng điều tra D6 đã xác định chính xác có **60 nguyên tử nguy cơ thuộc trạng thái `NO_CURRENT_SPATIAL_GT`** (chiếm 3,4% trong tổng số 1.788 atoms), phân bố trên 59 mẫu ảnh:
- Toàn bộ **34 atoms `DOOR_OPEN`**: Annotator gốc chỉ phân loại mức an toàn và mô tả văn bản, hoàn toàn không có nhãn đa giác cánh tủ điện mở trong tệp JSON.
- **26 atoms bị annotator bỏ sót đa giác**: 12 ca vệt dầu/nước tràn, 5 ca khói bất thường, 6 ca dị vật rác thải, 3 ca khác.

### 13.1 Chính sách loại trừ minh bạch (Transparent Exclusion)

1. **Loại khỏi mẫu số của đường đua định vị không gian:** 60 nguyên tử này **TUYỆT ĐỐI KHÔNG ĐƯỢC ĐƯA VÀO MẪU SỐ** của các chỉ số IoU, Hit@$\tau$, hay Evidence Grounding (cả Direct và Weak Proxy). Việc đưa chúng vào mẫu số sẽ phạt oan mô hình vì không thể khớp với một ground truth không hề tồn tại.
2. **Giữ nguyên trong bài toán phân loại an toàn:** 59 mẫu ảnh này vẫn là các mẫu kiểm thử hoàn toàn hợp lệ cho bài toán phân loại cấp độ an toàn (`Level01`–`Level04`) và phát hiện bất thường nhị phân.
3. **Cấm loại bỏ ngầm (No Silent Drop):** Toàn bộ 60 nguyên tử này phải được liệt kê minh bạch trong bảng kiểm kê loại trừ: công bố rõ sample ID, loại nguy cơ và lý do không đánh giá không gian.

---

## 14. Calibration Feasibility

Độ hiệu chỉnh xác suất (Probability Calibration) đo lường mức độ tin cậy của xác suất dự đoán so với tần suất xuất hiện thực tế (thông qua Expected Calibration Error — ECE, Brier Score).

### 14.1 Đánh giá tính khả thi thực nghiệm trên các họ mô hình VLM

1. **Rào cản từ giao diện Closed-API:**
   Các mô hình thương mại hàng đầu (Google Gemini, OpenAI GPT-4o, Anthropic Claude) không mở phân bố xác suất hậu nghiệm (posterior class probabilities) trên giao diện API cho bài toán đa lớp sinh văn bản tự do. Một số API chỉ cung cấp `logprobs` cho một vài token rời rạc ở vị trí đầu tiên, không tương đương với một phân bố xác suất chuẩn hóa trên toàn bộ 4 cấp độ an toàn.
2. **Sự ngụy tạo của độ tự tin tự thuật (Self-Reported Confidence):**
   Nếu yêu cầu mô hình tự phát biểu độ tự tin bằng văn bản (ví dụ: *"Tôi chắc chắn 90% đây là Level01"*), y văn đã chứng minh các con số này bị thiên lệch ngôn ngữ cực nặng (linguistic overconfidence), phụ thuộc vào cách mớm lời (prompting), và hoàn toàn không phải là xác suất thống kê có thể dùng để tính ECE.

### 14.2 Quyết định của SafeShift

- **Chỉ số chung xuyên mô hình:** **KHÔNG DÙNG calibration làm chỉ số chính bắt buộc** cho bảng so sánh tổng thể các mô hình.
- **Phân tích năng lực chuyên biệt (Capability-Specific Sub-Analysis):** Calibration chỉ được xem xét như một phân tích thăm dò phụ trợ đối với các mô hình nguồn mở có trọng số công khai (ví dụ Qwen2-VL) nơi phân bố xác suất softmax trên 4 token nhãn có thể trích xuất trực tiếp và có kiểm soát nhiệt độ giải mã cố định ($T=1.0$).

---

## 15. Object Hallucination Decision

Giảng viên gợi ý đo lường **Object Hallucination Rate** (Tỷ lệ ảo giác đối tượng: mô hình tuyên bố nhìn thấy vật thể nguy cơ nhưng thực tế không có).

### 15.1 Rào cản phương pháp luận từ Quyết định D7

Quyết định D7 đã khẳng định một sự thật thực chứng bất biến: **Bộ chú thích đối tượng gốc của InspecSafe-V1 không mang tính triệt để (`annotation is not exhaustive`)**.
- Kiểm toán W1 và điều tra W2.3 phát hiện nhiều trường hợp vũng nước tràn, điếu thuốc, hoặc thiết bị có thật trong ảnh nhưng annotator gốc không gắn nhãn đa giác trong tệp JSON.
- Do đó, phép suy diễn logic:
  $$\text{Không có nhãn trong JSON} \implies \text{Đối tượng không tồn tại trong ảnh}$$
  là **hoàn toàn SAI LẦM VỀ MẶT PHƯƠNG PHÁP LUẬN**.
- Nếu tính Tỷ lệ Ảo giác trên toàn bộ dataset bằng cách so sánh đầu ra của VLM với tệp JSON gốc, ta sẽ phạt oan một mô hình có thị lực sắc bén phát hiện ra một vệt dầu có thật mà người gán nhãn ban đầu bỏ sót!

### 15.2 Quyết định của SafeShift

- **Giao thức chính Seminar:** **LOẠI BỎ (EXCLUDE) chỉ số Object Hallucination Rate trên toàn bộ dataset** khỏi danh sách các chỉ số chính thức của Seminar 8 tuần.
- **Phân tích thăm dò tùy chọn (Optional Exploratory Probe):** Nếu có nhu cầu đo lường ảo giác, chỉ được phép thực hiện trên một tập con nhỏ (ví dụ 30–50 ảnh) đã được thẩm định thủ công độc lập (`manually verified subset`) với một từ điển nguy cơ đóng (`closed vocabulary`), hoặc bảo lưu cho giai đoạn Luận văn tốt nghiệp.

---

## 16. Classification-Grounding Inconsistency

Trong văn bản hướng dẫn ban đầu, có đề cập đến chỉ số "Correct Answer, Wrong Reason" (Đoán đúng mức an toàn nhưng định vị sai bằng chứng).

### 16.1 Chuẩn hóa thuật ngữ khoa học

Quyết định D1, D6 và D7 đã cấm việc sử dụng nhãn "Correct Answer, Wrong Reason" như một sự thật khách quan, vì InspecSafe-V1 hoàn toàn không có nhãn chuẩn về lý do suy luận của con người (`human rationale GT`). Việc mô hình khoanh trượt chiếc hộp đối tượng không chứng minh rằng mô hình suy luận sai (mô hình có thể dựa vào bối cảnh thiết bị xung quanh).

SafeShift chuẩn hóa tên gọi chính thức là:
**"Classification-Grounding Inconsistency relative to available object-support annotation" (Sự không nhất quán giữa phân loại và bám bằng chứng đối với chú thích đối tượng hiện có)**.

### 16.2 Công thức đo lường trên Direct Track

Trên tập con có hỗ trợ trực tiếp (`Direct-Support Pool`, $N=721$ mẫu):
$$\text{Inconsistency Rate} = \frac{\sum_{i \in \text{Direct}} \mathbb{I}\left(\text{Classification Correct}_i \land \text{Grounding Miss}_i\right)}{N_{\text{Direct}}}$$
Trong đó:
- $\text{Classification Correct}_i$: Mô hình dự đoán đúng cấp độ an toàn thực tế của mẫu ảnh.
- $\text{Grounding Miss}_i$: Mô hình không có bất kỳ hộp bao dự đoán nào đạt $\text{IoU} \ge 0.25$ với các đối tượng hỗ trợ trực tiếp trong ảnh.

*Ý nghĩa nghiên cứu (RQ3):* Đo lường mức độ mà các mô hình VLM hoạt động như một "hộp đen đoán mò theo bối cảnh nền" (nhận diện đúng cấp nguy hiểm nhờ nhận ra màu sắc phân xưởng nhưng không thực sự nhìn vào đối tượng gây nguy hiểm).

---

## 17. Confidence-Interval Candidates

Một sai lầm phổ biến là giả định 5.013 mẫu ảnh của InspecSafe-V1 hoàn toàn độc lập về mặt thống kê (IID). Quyết định D2 đã chỉ rõ: **Đơn vị dự đoán của mô hình là từng ảnh (`Image-level Prediction Unit`), nhưng đơn vị lấy mẫu lại thống kê phải có xét đến phụ thuộc cụm (`Resampling / Grouping Unit`)**.

### 17.1 Phân tích ba phương án Bootstrap tính khoảng tin cậy 95%

#### Phương án 1 — Naive Image-Level Bootstrap
Lấy mẫu lại có hoàn lại trực tiếp trên 5.013 ảnh đơn lẻ.
- *Nhược điểm chí mạng:* Coi các khung hình trong cùng một điểm dừng tuần tra là độc lập. Vi phạm giả định thống kê, dẫn đến đánh giá thấp phương sai thực tế và làm khoảng tin cậy bị hẹp giả tạo (artificially narrow CI).

#### Phương án 2 — Point-Cluster Bootstrap (Lấy mẫu lại theo cụm điểm logic)
Lấy mẫu lại có hoàn lại trên **3.234 cụm `point_id`** (gồm 2.234 cụm Normal và 1.000 cụm Anomaly).
- *Cơ chế:* Khi một `point_id` được chọn, **toàn bộ các khung hình thuộc point đó cùng được đưa vào mẫu bootstrap**.
- *Ưu điểm:* Bảo toàn trọn vẹn cấu trúc tương quan nội bộ điểm đã biết (known within-point dependence).
- *Nhược điểm khi áp dụng thuần túy:* Do Level03 chỉ có 15 cụm và Anomaly của Luyện kim chỉ có 9 cụm, việc lấy mẫu ngẫu nhiên không phân tầng có xác suất cao khiến các lớp hiếm này hoàn toàn biến mất trong một số lượt replicate (tại cấp miền luyện kim xác suất mất L03 lên tới $36,8\%$, gây lỗi $0/0$ khi tính Macro-F1).

#### Phương án 3 — Stratified Point-Cluster Bootstrap (Bootstrap cụm điểm có phân tầng — ĐƯỢC CHỌN)
Thực hiện lấy mẫu lại theo cụm `point_id`, nhưng **phân tầng độc lập theo từng tổ hợp: Miền công nghiệp $\times$ Cấp độ an toàn**:
$$\text{Stratum}(d, c) = \{\text{clusters} \in \text{Domain } d \text{ có nhãn } c\}$$
Lấy mẫu lại có hoàn lại $N_{\text{clusters}}(d, c)$ lần trong từng phân tầng cụ thể.

- *Ưu điểm vượt trội:*
  1. Bảo toàn cấu trúc phụ thuộc đa khung hình nội bộ điểm của dữ liệu Normal.
  2. Đảm bảo 100% các lượt replicate bootstrap đều bảo lưu chính xác số lượng cụm của từng cấp độ an toàn và từng miền công nghiệp.
  3. Loại bỏ hoàn toàn nguy cơ xuất hiện mẫu số 0 ở các lớp hiếm (`Level03`, Anomaly của `metallurgy`), giúp phân phối bootstrap của Macro-F1 và Balanced Accuracy luôn xác định và ổn định toán học.

### 17.2 Tham số và kiểm chứng thực nghiệm thời gian chạy

- **Số lượt lấy mẫu lại:** $B = 2.000$ replicates (chính thức); $B = 5.000$ (kiểm tra hội tụ).
- **Khoảng tin cậy:** Percentile Bootstrap 95% $\left[ q_{0,025}, \, q_{0,975} \right]$.
- **Khóa seed tái lập:** `seed = 42`.
- **Benchmark cục bộ:** Script kiểm chuẩn Python chuẩn trên vi xử lý x64 hoàn thành $2.000$ replicates trên 5.013 mẫu trong **3,96 giây**. Hoàn toàn khả thi và không gây nghẽn tài nguyên.

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

---

## 19. Model-Comparison Statistics

Khi so sánh hiệu năng giữa hai mô hình VLM (ví dụ: Mô hình A vs Mô hình B), mọi dự đoán đều được thực hiện trên **cùng một tập ảnh cố định**.

### 19.1 Bản chất dữ liệu theo cặp (Paired Nature of Observations)

- Các quan sát giữa các mô hình là **phụ thuộc theo cặp (paired)**.
- **Quy tắc cấm tuyệt đối:** Tuyệt đối không bao giờ sử dụng các phép kiểm định cho hai mẫu độc lập (như independent two-sample $t$-test hay Mann-Whitney $U$-test). Việc xem hai mô hình như hai mẫu độc lập vi phạm bản chất ghép cặp và làm mất hoàn toàn sức mạnh thống kê.

### 19.2 Phân tích các phương án so sánh mô hình

#### Phương án 1 — Paired Bootstrap Difference CI (Khoảng tin cậy hiệu số theo cặp — ĐƯỢC CHỌN LÀM PRIMARY)
Đối với mỗi lượt lấy mẫu lại bootstrap $b \in \{1, \dots, B\}$:
1. Rút mẫu tập dữ liệu bootstrap $\mathcal{D}^{(b)}$ theo quy trình phân tầng cụm.
2. Tính chỉ số cho cả hai mô hình trên cùng tập dữ liệu này: $M_A^{(b)}$ và $M_B^{(b)}$.
3. Tính hiệu số hiệu năng:
   $$\Delta M^{(b)} = M_A^{(b)} - M_B^{(b)}$$
4. Xác lập khoảng tin cậy 95% cho hiệu số:
   $$\text{CI}_{95\%}(\Delta M) = \left[ \Delta_{0,025}, \, \Delta_{0,975} \right]$$
- *Quy tắc kết luận khoa học:*
  - Nếu khoảng tin cậy $\text{CI}_{95\%}(\Delta M)$ **hoàn toàn không chứa giá trị 0** (ví dụ $[+1,5\text{pp}, +5,2\text{pp}]$): Kết luận mô hình A vượt trội hơn mô hình B có ý nghĩa thống kê ở mức $\alpha = 0,05$.
  - Nếu khoảng tin cậy **chứa giá trị 0** (ví dụ $[-1,2\text{pp}, +2,8\text{pp}]$): **TUYỆT ĐỐI KHÔNG TUYÊN BỐ HAI MÔ HÌNH "GIỐNG NHAU" HOẶC "TƯƠNG ĐƯƠNG NHAU"**. Chỉ được kết luận: *Dữ liệu thực nghiệm hiện tại chưa cung cấp đủ bằng chứng để khẳng định sự khác biệt giữa hai mô hình ở mức độ bất định đang báo cáo*.

#### Phương án 2 — Paired Permutation Test (Kiểm định hoán vị theo cặp)
Thực hiện tráo ngẫu nhiên dự đoán của mô hình A và B trên từng cụm điểm dưới giả thuyết vô hiệu $H_0: M_A = M_B$. Tính trị số $p$.

#### Phương án 3 — McNemar's Test
Chỉ áp dụng được cho tính đúng/sai nhị phân (0/1) trên từng mẫu đơn lẻ. Không áp dụng được cho các chỉ số phức tạp như Macro-F1 hay IoU liên tục.

### 19.3 Triết lý phương pháp luận khuyến nghị: Effect Size + CI > p-value Hunting

SafeShift lựa chọn triết lý khoa học hiện đại: **Tập trung vào độ lớn hiệu ứng (Effect Size) đi kèm khoảng tin cậy (Confidence Interval)** thay vì chạy theo việc "săn tìm $p$-value" ($p$-value hunting).
- Báo cáo rõ giá trị chênh lệch $\Delta M$ và khoảng tin cậy $\text{CI}_{95\%}$.
- Tránh việc thực hiện hàng loạt bài kiểm định giả thuyết dẫn đến vấn đề so sánh bội (multiple comparisons problem). Nếu bắt buộc phải kiểm định giả thuyết cho nhiều cặp mô hình, áp dụng hiệu chỉnh Benjamini-Hochberg False Discovery Rate (FDR).

---

## 20. P1/P2/P3 Application

| Tiêu chí | P1 — Baseline Replication | P2 — Primary Research Protocol | P3 — Candidate Sensitivity Protocol |
| :--- | :--- | :--- | :--- |
| **Quy mô mẫu** | Đúng **1.250 mẫu** (Test chính thức) | Đúng **5.013 mẫu** (Toàn bộ dữ liệu) | 1.248 mẫu (Within-test) & 1.241 mẫu (Cross-split) |
| **Vai trò nghiên cứu** | Tái lập & đối chiếu upstream baseline | Trả lời các câu hỏi nghiên cứu chính (RQ1–3) | Kiểm tra độ nhạy rò rỉ lặp ảnh |
| **Độ bao phủ miền** | 5 miền (nhưng `metallurgy` có 0 Anomaly) | 5 miền (đầy đủ 1.000 mẫu Anomaly) | Đánh giá phụ trợ theo tập con |
| **Chỉ số áp dụng** | Safety Accuracy, BGE-M3 Similarity, Extension Grounding | Balanced Accuracy, Macro-F1, FNR/FPR, Evidence Grounding | Áp dụng cùng công thức với P1 trên tập con |
| **Xử lý Metallurgy** | Anomaly metrics = **UNDEFINED** (Không tính) | Anomaly metrics = **DESCRIPTIVE-ONLY** ($N=9$) | Theo phân bố thực tế của tập con |
| **Định vị Grounding** | SafeShift extension, không phải upstream baseline | RQ3-A Direct ($N=781$) & RQ3-B Proxy ($N=947$) | Đánh giá độ nhạy trên tập con |

---

## 21. Domain-Mismatch Sensitivity

Quyết định D3 đã xác định chính xác **36 mẫu xung đột** giữa tên thư mục và khẳng định mở đầu trong tệp văn bản (`folder_domain != text_domain`):
- 4 mẫu `power` $\rightarrow$ `coal_conveyor` (train)
- 8 mẫu `metallurgy` $\rightarrow$ `oil_chemical` (train)
- 24 mẫu `tunnel` $\rightarrow$ `oil_chemical` (20 train, 4 test)

### 21.1 Quy tắc áp dụng chỉ số cho phân tích độ nhạy

1. **Công thức toán học bất biến:** Mọi công thức chỉ số (Balanced Accuracy, Macro-F1, FNR, Spread) **hoàn toàn giữ nguyên không đổi** giữa phân tích chính và phân tích độ nhạy.
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
| **Chỉ số suy giảm xuyên miền** | 1. Pooled-to-Domain Gap<br>2. Worst-Domain Gap<br>3. Class-Conditional Spread<br>4. Balanced Accuracy Spread | - Pooled-to-Domain bị nhiễu nặng bởi thành phần nhãn.<br>- Class-Conditional Spread triệt tiêu hoàn toàn nhiễu nhãn.<br>- Balanced Accuracy Spread chuẩn hóa trên miền $K=4$. | **CHỌN PHƯƠNG ÁN 3 + 4**<br>Primary: Balanced Accuracy Spread & Anomaly Recall Spread. Bổ trợ: Class-Conditional Spread. |
| **Xử lý lớp thiếu ở từng miền** | 1. Support-only macro average<br>2. Yêu cầu cố định 4 lớp (gán NA)<br>3. Dual-Layer Support-Aware Policy | - Phương án 1 so sánh trên bài toán khác nhau.<br>- Phương án 2 làm khuyết 40% số miền.<br>- Phương án 3 vừa minh bạch số lớp vừa có mỏ neo so sánh. | **CHỌN PHƯƠNG ÁN 3**<br>Descriptive macro có gắn cờ số lớp $K_d$; dùng Class-Conditional metrics làm mỏ neo so sánh. |
| **Báo cáo Worst-Domain** | 1. Tự động lấy min toàn bộ miền<br>2. 4 điều kiện: Bộ lọc $N \ge 30$, công bố mẫu số, cảnh báo thưa, Descriptive-Only | - Phương án 1 dẫn đến ngụy biện trên metallurgy N=9.<br>- Phương án 2 bảo vệ tính toàn vẹn nghiên cứu. | **CHỌN PHƯƠNG ÁN 2**<br>Miền metallurgy là Descriptive-Only, không tham gia xếp hạng worst-domain. |
| **Định vị Direct Grounding** | 1. Hit@0.50 thuần túy<br>2. Continuous IoU<br>3. Hit@0.25 + Mean IoU + Evidence P/R | - Ngưỡng 0.50 quá khắt khe với bbox phái sinh từ polygon.<br>- Hit@0.25 phân tách tốt đoán mò và phản ánh năng lực VLM.<br>- Evidence P/R đo lường toàn diện nhận diện + định vị. | **CHỌN PHƯƠNG ÁN 3**<br>Hit@0.25 làm primary thresholded; Mean IoU làm continuous; Hit@0.50 làm sensitivity đối chứng. |
| **Định vị Weak Proxy** | 1. Dùng IoU với Person<br>2. Proxy Localization Consistency (Center-in-Proxy + Containment) | - IoU với Person phạt mô hình nhìn đúng đầu người (NO_HELMET).<br>- PLC phản ánh trung thực mức độ nhất quán vị trí. | **CHỌN PHƯƠNG ÁN 2**<br>Báo cáo riêng biệt Proxy Localization Consistency. Cấm gọi là true grounding. |
| **Ước lượng bất định (CI)** | 1. Naive Image Bootstrap<br>2. Point-Cluster Bootstrap thuần túy<br>3. Stratified Point-Cluster Bootstrap | - Phương án 1 vi phạm độc lập, CI hẹp giả tạo.<br>- Phương án 2 có thể mất lớp hiếm trong replicate.<br>- Phương án 3 kiểm soát tương quan cụm và ổn định mẫu số. | **CHỌN PHƯƠNG ÁN 3**<br>Stratified Point-Cluster Bootstrap ($B=2.000$, seed=42). |
| **So sánh các mô hình** | 1. Phép thử 2 mẫu độc lập<br>2. Paired Bootstrap Difference CI<br>3. Paired Permutation Test | - Phép thử độc lập sai phương pháp luận (dữ liệu theo cặp).<br>- Paired Bootstrap Difference CI minh bạch, tập trung effect size. | **CHỌN PHƯƠNG ÁN 2**<br>Paired Difference CI 95% làm primary; ưu tiên effect size hơn săn lùng p-value. |

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
   - Miền Luyện kim (`metallurgy`) được xếp vào diện **"Chỉ mang tính mô tả (Descriptive-Only)"** cho các chỉ số bất thường; không tham gia xếp hạng tự động miền kém nhất.
4. **Suy giảm hiệu năng xuyên miền (Cross-Domain Drop):**
   - primary: **Balanced Accuracy Domain Spread** trên các miền đủ 4 lớp, kết hợp **Binary Anomaly Recall Spread**.
   - Sensitivity: Báo cáo Pooled-to-Domain Gap đi kèm tỷ lệ thành phần nhãn của từng phân xưởng.
   - Tuyệt đối không dùng thuật ngữ "Domain Generalization Drop".
5. **Đánh giá bám bằng chứng trực tiếp (RQ3-A Direct Grounding):**
   - **Primary Metric:** $\text{Hit}@0.25$ và **Overall Mean IoU**.
   - **Sensitivity Metric:** $\text{Hit}@0.50$ và Conditional Mean IoU.
   - **Comprehensive Metric:** Evidence Precision, Evidence Recall, Evidence F1 ở cấp độ nguy cơ nguyên tử với thuật ngữ ghép cặp Greedy One-to-One.
6. **Đánh giá đại diện yếu (RQ3-B Weak Proxy Grounding):**
   - Đo lường bằng **Proxy Localization Consistency (PLC)** thông qua Center-in-Proxy và Box Containment $\ge 0.50$.
   - Báo cáo tách biệt hoàn toàn khỏi Direct Grounding; cấm gọi là "bám bằng chứng thật".
7. **Xử lý lỗi phân tích cú pháp (Parse Failure):**
   - Áp dụng đồng thời: **End-to-End Grounding** (lỗi parse tính là $\text{IoU}=0.0$) làm chỉ số chính, và **Conditional Grounding Quality** đi kèm **Parse Success Rate (PSR)** làm chỉ số chẩn đoán.
8. **Định lượng bất định và khoảng tin cậy:**
   - Áp dụng **Stratified Point-Cluster Bootstrap** với $B = 2.000$ replicates, cố định `seed = 42`.
   - Báo cáo khoảng tin cậy Percentile 95% cho toàn bộ các chỉ số chính.
9. **So sánh đa mô hình:**
   - Áp dụng **Paired Bootstrap Difference CI 95%** làm phương pháp so sánh chính.
   - Tuân thủ triết lý: Coi trọng độ lớn hiệu ứng và khoảng tin cậy; nếu CI chứa 0 thì kết luận chưa đủ bằng chứng chứng minh khác biệt, không tuyên bố hai mô hình giống nhau.

---

## 24. Risks & Limitations

Báo cáo W2.4 nhận diện 5 rủi ro và giới hạn phương pháp luận bắt buộc phải công bố minh bạch:

1. **Mất cân bằng dữ liệu cực đoan và cỡ mẫu siêu nhỏ:**
   Lớp `Level03` chỉ có 15 mẫu trên toàn bộ 5.013 ảnh (và chỉ có 7 mẫu ở tập test P1). Bất kỳ biến động nào trong dự đoán của 1–2 mẫu cũng làm thay đổi lớn chỉ số của lớp này. Khoảng tin cậy cho `Level03` sẽ có độ rộng lớn.
2. **Nhiễu cấu trúc giữa Miền công nghiệp và Nền tảng Robot (Platform Confounding):**
   Do robot ray treo (`SuspendedRail`) tập trung 100% tại băng chuyền than trong khi robot bánh lăn (`Wheeled`) chiếm đa số ở luyện kim và hóa dầu, sự khác biệt hiệu năng giữa các miền luôn bị đồng biến thiên với góc máy tuần tra. SafeShift không đưa ra khẳng định nhân quả về nền tảng robot.
3. **Giới hạn của Hộp bao phái sinh từ Đa giác:**
   Hộp bao không phải là chú thích gốc của InspecSafe-V1. Đối với các đối tượng có hình dạng biến thiên (vệt dầu loang, khói), hộp bao chữ nhật cực biên luôn chứa diện tích nền trống, tạo ra sự bất lợi tự nhiên cho các chỉ số dựa trên diện tích giao thoa (IoU).
4. **Không có nhãn chuẩn về lý do suy luận của con người:**
   Do không tự tạo nhãn rationale mới ở Seminar (D7-A), việc đánh giá bám bằng chứng dừng lại ở mức độ bám đối tượng vật lý (`Object Support`) và kiểm tra tính nhất quán (`Consistency`), chưa thể chứng minh tính đúng đắn trong chuỗi suy luận nội tại của mô hình VLM.
5. **Thiếu vắng phân bố xác suất tin cậy từ các Closed-API:**
   Việc không thể trích xuất xác suất tin cậy thực sự từ các mô hình thương mại khiến việc đánh giá độ hiệu chỉnh (calibration) bị giới hạn và không thể áp dụng đồng nhất trên toàn bộ benchmark.

---

## 25. Questions Requiring Approval

Để chính thức ban hành **Quyết định D5 (DEC-W2-D5)**, SafeShift đệ trình danh sách **15 câu hỏi phương pháp luận sẵn sàng phê duyệt (`READY FOR D5 APPROVAL`)**:

1. **Chỉ số phân loại chính:** Chấp thuận sử dụng **Balanced Accuracy** và **Macro-F1** làm hai chỉ số chính song hành (Co-Primary Metrics), và xếp Raw Accuracy vào nhóm mô tả phụ trợ hay không?
2. **Định nghĩa chỉ số sai số an toàn:** Chấp thuận tách bạch độc lập **$\text{FNR}_{\text{anomaly}} / \text{FPR}_{\text{anomaly}}$** (Track A) và **$\text{FNR}_{\text{L01}} / \text{Recall}_{\text{L01}}$** (Track B), cấm dùng FNR chung chung hay không?
3. **Chính sách xử lý lớp thiếu ở từng miền:** Chấp thuận Chính sách hai tầng (Dual-Layer Support-Aware Policy C): công bố chỉ số vĩ mô có gắn cờ số lớp $K_d$ và dùng Class-Conditional Recall làm mỏ neo so sánh chính hay không?
4. **Công thức suy giảm hiệu năng xuyên miền:** Chấp thuận sử dụng **Balanced Accuracy Domain Spread** và **Anomaly Recall Domain Spread** làm thước đo chính cho RQ1, cấm dùng thuật ngữ "Domain Generalization Drop" hay không?
5. **Chính sách xác định Worst-Domain:** Chấp thuận điều kiện đủ $N_{\text{anomaly}} \ge 30$ để tham gia xếp hạng và chỉ định miền `metallurgy` là "Chỉ mang tính mô tả (Descriptive-Only)", không tự động chọn làm worst-domain hay không?
6. **Chỉ số chính cho Direct Grounding:** Chấp thuận bộ chỉ số gồm **$\text{Hit}@0.25$**, **Mean IoU**, và **Evidence Precision/Recall/F1** cho đường đua RQ3-A hay không?
7. **Ngưỡng IoU đánh giá định vị:** Chấp thuận chọn **$\tau = 0.25$** làm ngưỡng trúng đích chính thức cho bài toán định vị thô của VLM trên hộp bao phái sinh, và giữ $\tau = 0.50$ làm ngưỡng độ nhạy đối chiếu hay không?
8. **Chỉ số đánh giá Weak Proxy:** Chấp thuận chỉ số **Proxy Localization Consistency (PLC)** (Center-in-Proxy và Box Containment $\ge 0.50$), cấm gọi là true grounding accuracy và bắt buộc báo cáo tách biệt khỏi Direct track hay không?
9. **Công thức Evidence Precision / Recall:** Chấp thuận thuật toán ghép cặp **Greedy One-to-One theo IoU giảm dần** ở cấp độ nguy cơ nguyên tử để tính Evidence P/R hay không?
10. **Chính sách xử lý lỗi parse cú pháp:** Chấp thuận coi lỗi parse là thất bại hoàn toàn ($\text{IoU}=0.0$) trong chỉ số **End-to-End Grounding**, đồng thời báo cáo riêng **Parse Success Rate** và **Conditional Localization Quality** hay không?
11. **Phạm vi chỉ số Object Hallucination:** Chấp thuận loại bỏ hoàn toàn chỉ số Object Hallucination Rate trên toàn bộ dataset trong khuôn khổ Seminar 8 tuần theo tinh thần Quyết định D7 hay không?
12. **Tính khả thi của Calibration:** Chấp thuận không đưa chỉ số hiệu chỉnh xác suất (ECE/Brier Score) vào bảng so sánh tổng thể các mô hình do hạn chế kỹ thuật của Closed-API hay không?
13. **Phương pháp tính khoảng tin cậy chính thức:** Chấp thuận áp dụng **Stratified Point-Cluster Bootstrap** (phân tầng theo Miền $\times$ Cấp an toàn, gom cụm theo `point_id`) làm phương pháp ước lượng bất định chính thức hay không?
14. **Tham số và tính tái lập của Bootstrap:** Chấp thuận cấu hình **$B = 2.000$ replicates**, khoảng tin cậy Percentile 95%, và khóa seed ngẫu nhiên cố định **`seed = 42`** hay không?
15. **Phương pháp so sánh mô hình VLM:** Chấp thuận sử dụng **Paired Bootstrap Difference CI 95%** làm công cụ so sánh mô hình chính thức, ưu tiên Effect Size và Confidence Interval thay vì săn lùng $p$-value hay không?

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
