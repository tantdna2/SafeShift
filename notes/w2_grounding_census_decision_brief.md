# W2.3 Grounding Scope & Hazard Census Decision Brief

- **Tài liệu:** Báo cáo căn cứ quyết định phạm vi bám bằng chứng và tổng điều tra nguy cơ (W2.3 Grounding Scope & Hazard Census Decision Brief)
- **Dự án:** SafeShift: Benchmarking Cross-Domain Generalization and Evidence Grounding in Vision-Language Models for Industrial Safety Assessment
- **Bộ dữ liệu:** InspecSafe-V1 (5.013 mẫu ảnh: 4.013 Normal, 1.000 Anomaly)
- **Trạng thái:** BÁO CÁO CĂN CỨ KỸ THUẬT (TECHNICAL EVIDENCE BRIEF) — ĐỀ XUẤT CHO D4, D6, D7 (CHƯA PHÊ DUYỆT)
- **Ngày lập:** 2026-09-17
- **Phiên bản:** 1.0.0

---

## 1. Mục đích văn bản (Purpose)

Văn bản này thiết lập cơ sở thực chứng phương pháp luận độc lập và toàn diện cho giai đoạn Week 2.3 của dự án SafeShift, chuẩn bị căn cứ khoa học cho ba quyết định then chốt:

1. **Quyết định D4 — Giao diện đầu ra bám bằng chứng của mô hình (Model Grounding Output Interface):** Chuẩn hóa định dạng biểu diễn không gian mà mô hình thị giác-ngôn ngữ (VLM) cần xuất ra để đánh giá khả năng định vị bằng chứng nguy cơ một cách công bằng và có khả năng so sánh xuyên mô hình.
2. **Quyết định D6 — Tổng điều tra đầy đủ tập bất thường (Full Direct-Support Census):** Thực hiện cuộc tổng điều tra thực chứng trên 100% (1.000 / 1.000) mẫu Bất thường (`Anomaly_data`), bóc tách chi tiết ở cả cấp độ mẫu (`Sample-level`) và cấp độ nguy cơ nguyên tử (`Hazard-atom level`), xác minh chính xác quy mô các tập con có hỗ trợ trực tiếp (`Direct-Support`), hỗ trợ đại diện yếu (`Weak-Proxy`) và hoàn toàn chưa có nhãn không gian (`No-Current-Spatial-GT`).
3. **Quyết định D7 — Chiến dịch gán nhãn vùng lý do bổ sung (Optional Rationale Annotation Campaign):** Phân tích sự cần thiết, tính khả thi, chi phí thời gian và rủi ro phương pháp luận của việc tự tạo thêm nhãn vùng lý do của con người (`Human Rationale Regions`) cho một tập con nhỏ trong phạm vi Seminar 8 tuần.

> [!IMPORTANT]
> **Giới hạn phạm vi Week 2.3:** Báo cáo W2.3 **tuyệt đối không chốt quyết định D5 (Metrics & Statistical Evaluation)**. Toàn bộ công thức toán học của các chỉ số (Macro-F1, Balanced Accuracy, ngưỡng IoU, bán kính Pointing Game, công thức suy giảm hiệu năng xuyên miền) cùng quy trình kiểm định thống kê (Bootstrap, CI, Permutation Test) được chuyển giao nguyên vẹn cho **bước W2.4 giải quyết**. Mọi đề xuất trong tài liệu này ở trạng thái `PROPOSED, NOT APPROVED` cho đến khi có phê duyệt chính thức từ Research Lead.

---

## 2. Các quyết định đã khóa D1–D3 (Locked Decisions D1–D3)

Quá trình điều tra tại W2.3 kế thừa và tuân thủ tuyệt đối các quyết định đã được phê duyệt chính thức tại [DECISIONS.md](../DECISIONS.md):

- **DEC-W2-D1-001 (Research Framing & Protocol Hierarchy):**
  - Bản chất bài toán của Seminar: **Cross-Domain Robustness Evaluation trên Frozen Pretrained VLMs**. Tuyệt đối không gọi là Domain Generalization theo nghĩa học máy chuẩn có huấn luyện trên miền nguồn.
  - Phân tầng giao thức:
    - **P1 (Baseline Replication):** Đánh giá zero-shot trên đúng **1.250 mẫu test chính thức**. Grounding trên P1 là SafeShift extension, không phải upstream baseline.
    - **P2 (Primary Research Protocol):** Đánh giá trên toàn bộ **5.013 mẫu** (toàn bộ không gian quan sát), báo cáo phân rã theo 5 miền công nghiệp, bảo lưu nguyên vẹn metadata `split: train/test`.
    - **P3 (Candidate Sensitivity Protocol):** Đánh giá có xét nhóm, duy trì trạng thái candidate, không phải clean benchmark.
    - **P4 (Thesis LODO DG):** Dành cho Luận văn tốt nghiệp sau này.
  - Khung câu hỏi nghiên cứu: Phê duyệt **RQ1** (biến thiên xuyên miền & đồng biến thiên robot platform), **RQ2** (tập trung lỗi theo cấp an toàn & hazard strata), **RQ3** (tính nhất quán giữa phân loại và bám bằng chứng).
- **DEC-W2-D2-002 (Split, Evaluation Pool, and Grouping Policy):**
  - P1 giữ nguyên 1.250 mẫu test, không lọc duplicate.
  - P2 dùng 5.013 ảnh, bảo lưu metadata split gốc.
  - Đơn vị dự đoán duy nhất là **Ảnh (`Image`)**. Mọi raw model output phải được lưu trữ ở cấp độ từng ảnh kèm prompt, model version và decoding settings.
  - Trường `point_id` là tín hiệu gom nhóm ứng viên ưu tiên cho Normal data; 1.000 mẫu Anomaly không được giả định là 1.000 sự kiện độc lập về mặt thống kê. `source-family` chỉ là heuristic signal, không phải true video ID.
  - Phê duyệt hai phân tích độ nhạy phụ trợ cho P1: 1.248 mẫu (loại 2 mẫu lặp nội bộ test) và 1.241 mẫu (loại thêm 7 mẫu tái sử dụng exact xuyên split).
- **DEC-W2-D3-003 (Operational Domain Definition and Mismatch Policy):**
  - Sử dụng trường **`folder_domain` làm Nhãn miền thao tác chính (`Primary Operational Domain Label`)**. Tuyệt đối không gọi là physical ground truth.
  - Duy trì chính sách báo cáo độ nhạy kép (`Dual-Report Sensitivity Policy`) với 36 mẫu xung đột (`folder_domain != text_domain`): Primary theo folder_domain; Sensitivity A loại bỏ 36 mẫu; Sensitivity B tái phân bổ theo text_domain.
  - Miền Luyện kim (`metallurgy`) có 720 mẫu nhưng lớp bất thường bị thiếu hụt dữ liệu nghiêm trọng ($N_{\text{anomaly}} = 9$, test có 0 mẫu, 8/9 mẫu ở train có `text_domain = oil_chemical`). Tuyệt đối không tuyên bố $N=9$ là đủ cho suy luận thống kê.
  - Sử dụng thuật ngữ chuẩn mực: "đồng biến thiên với nền tảng robot" (`co-variation with robot platform`) hoặc "nhiễu nền tảng robot" (`platform confounding`). Tuyệt đối không đưa ra khẳng định nhân quả (`causal claim`).

---

## 3. Các sự thật thực chứng về Grounding từ W1 (W1 Grounding Facts)

Kiểm toán độc lập tại Tuần 1 ([notes/w1_dataset_audit.md](w1_dataset_audit.md), [notes/dataset_schema.md](dataset_schema.md) và [notes/research_feasibility_audit.md](research_feasibility_audit.md)) đã xác lập các sự thật thực chứng bất biến sau:

1. **Quy mô và thành phần nhãn an toàn:** Bộ dữ liệu có đúng **5.013 mẫu ảnh**, gồm **4.013 Normal** (`Level04`) và **1.000 Anomaly** (chia thành 659 `Level01`, 326 `Level02`, 15 `Level03`).
2. **Kiểm kê đa giác:** Toàn bộ dữ liệu chứa **37.434 đa giác đối tượng (`polygon`)**, biểu diễn phân vùng phiên bản AnyLabeling/LabelMe thông thường, bao phủ **231 nhãn đối tượng thô** (230 tiếng Anh, 1 tiếng Trung `"出口"`).
3. **Hiện trạng thiếu hụt nhãn Grounding chuyên biệt:** Bộ dữ liệu InspecSafe-V1 **hoàn toàn KHÔNG có sẵn**:
   - Vùng bằng chứng chuyên biệt cho nguy cơ (`hazard-specific evidence regions`).
   - Vùng lý do do con người gán (`human rationale regions`).
   - Ánh xạ giữa cụm từ và vùng ảnh (`phrase-to-region alignment`).
   - Ánh xạ giữa bằng chứng và mức độ an toàn (`evidence-to-safety mapping`).
   - Vùng không gian chính thức cho đối tượng bị vắng mặt (`official absent-object regions`).
4. **Bản chất của Bounding Box:** Hộp bao tọa độ (`Bounding Box`) **không phải là chú thích gốc (`not native annotation`)**. BBox chỉ có thể được suy biến toán học (`DERIVED`) từ tập tọa độ cực biên của đa giác khép kín: $[x_{\min}, y_{\min}, x_{\max}, y_{\max}]$.
5. **Giới hạn của Pilot Review 63 mẫu Anomaly ở W1:**
   - Tại W1, một tập con gồm 63 mẫu Anomaly đã được thẩm định chuyên sâu với kết quả: 13 mẫu `DIRECT_SUPPORT` (20,6%), 46 mẫu `PARTIAL_PROXY` (73,0%), 3 mẫu `NO_DIRECT_SUPPORT` (4,8%), 1 mẫu `AMBIGUOUS` (1,6%).
   - **CẢNH BÁO PHƯƠNG PHÁP LUẬN:** Tập 63 mẫu này là **tập thẩm định phân tầng có chủ đích (`targeted / stratified audit subset`)** nhằm kiểm tra tối đa các góc cạnh khó (bao phủ 100% mẫu Anomaly của metallurgy, 100% mẫu Level03, 100% các cặp exact duplicate xuyên split, và 12 họ nguồn). Tập này **KHÔNG phải là mẫu ngẫu nhiên đại diện thống kê (`representative random sample`)**.
   - Do đó: **Tuyệt đối không được ngoại suy tỷ lệ 20,6% Direct Support hay 73,0% Partial Proxy sang toàn bộ 1.000 mẫu Anomaly**. Mục tiêu cốt lõi của D6 là thực hiện cuộc tổng điều tra chính xác trên toàn thể 1.000 mẫu.

---

## 4. Phương pháp tổng điều tra 1.000 mẫu Anomaly (Census Method)

Để trả lời chính xác và minh bạch 100% cấu trúc nguy cơ của InspecSafe-V1, SafeShift thực hiện quy trình điều tra tất định, không dựa trên lấy mẫu ngẫu nhiên hay gán nhãn tự do bằng LLM:

- **Phạm vi điều tra:** Đúng **1.000 / 1.000 mẫu Anomaly** (749 mẫu thuộc `train`, 251 mẫu thuộc `test`).
- **Nguồn dữ liệu trích xuất:**
  - Tệp văn bản chú thích gốc (`.txt`): Khảo sát toàn văn mệnh đề nguy cơ.
  - Tệp chú thích hình học gốc (`.json`): Bóc tách 100% đa giác và nhãn danh mục trong trường `shapes[].label`.
  - Siêu dữ liệu đường dẫn đã audit: `folder_domain`, `safety_level`, `robot_platform`, `point_id`, `split`.
- **Môi trường thực thi & Tính tái lập:**
  - Python 3.11.9, sử dụng thư viện chuẩn (`pathlib`, `json`, `re`, `collections`, `hashlib`).
  - Đường dẫn manifest cục bộ đầy đủ: `data/manifests/w2_grounding_census.json` (dung lượng: 762.487 bytes, mã băm SHA-256: `cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`).
  - Manifest cục bộ này được lưu giữ trên máy trạm cục bộ để kiểm chứng tái lập, không commit lên Git repository nhằm tuân thủ quy tắc bảo vệ dữ liệu dẫn xuất chi tiết của dự án.
- **Quy trình bóc tách cú pháp văn bản tất định (Deterministic Text Decomposition):**
  1. *Khử mệnh đề mở đầu ngữ cảnh:* Đối chiếu với danh mục **24 mệnh đề mở đầu duy nhất** đã được kiểm toán toàn diện tại `notes/dataset_schema.md` (Mục 15). Kết quả: 1.000 / 1.000 mẫu khớp 100% mệnh đề mở đầu chuẩn mực (0 mẫu lỗi mở đầu).
  2. *Khử mệnh đề kết luận mức độ an toàn:* Nhận diện và loại bỏ các biến thể cú pháp kết luận cấp an toàn (`Therefore, the safety level is...`, `The safety level is...`, `are classified as Level One safety`). Toàn bộ 1.000 mẫu được bóc tách sạch sẽ phần thân nguy cơ cốt lõi (`hazard body clause`).
  3. *Kết quả trích xuất:* Toàn bộ 1.000 mẫu Anomaly hội tụ về đúng **187 mệnh đề nguy cơ duy nhất (`187 unique hazard clauses`)**.

---

## 5. Hệ phân loại nguy cơ nguyên tử (Hazard Atom Taxonomy)

### 5.1 Khái niệm then chốt: Sample-level vs Hazard-atom level

Một sai lầm phổ biến là gộp toàn bộ một mẫu ảnh thành một nhãn nguy cơ duy nhất. Trong thực tế công nghiệp, một mẫu ảnh thường chứa đồng thời nhiều hành vi và vi phạm khác nhau:
- *Ví dụ mẫu `coal_conveyor-Level01-SuspendedRail-002486-001`:* Văn bản mô tả *"personnel smoking and not wearing gloves"*.
  - Nếu chỉ phân loại ở cấp mẫu, mẫu này bị xung đột giữa một nguy cơ có vật thể hiện hữu (`smoking` $\rightarrow$ điếu thuốc) và một vi phạm dạng vắng mặt (`not wearing gloves` $\rightarrow$ thiếu găng tay).
- **Quy tắc chuẩn hóa của SafeShift:**
  - **Đơn vị nguy cơ nguyên tử (`Hazard Atom`):** Là một phát biểu nguy cơ đơn lẻ, độc lập, có thể đánh giá trạng thái hỗ trợ không gian một cách riêng biệt.
  - **Mẫu số thống kê:** Bắt buộc phân biệt rạch ròi **Số lượng theo Mẫu (`Sample-Level Counts`, tổng cố định = 1.000)** và **Số lượng theo Nguy cơ Nguyên tử (`Hazard-Atom Counts`, tổng > 1.000)**. Tuyệt đối không đánh đồng hai mẫu số này.

### 5.2 Danh mục 12 Nguy cơ Nguyên tử được kiểm chứng thực tế

Khảo sát toàn bộ 187 mệnh đề nguy cơ duy nhất trên 1.000 mẫu Anomaly xác nhận hệ phân loại gồm đúng **12 Hazard Atoms**, giải thích trọn vẹn 100% mẫu mà không có bất kỳ trường hợp nào bị bỏ sót (`unmapped count = 0`):

| STT | Mã Nguy cơ Nguyên tử (`Hazard Atom`) | Định nghĩa ngữ nghĩa trong văn bản InspecSafe-V1 | Từ khóa nhận diện đặc trưng trong TXT | Số lượng Atom (`Atom Count`) |
|:---:|---|---|---|:---:|
| 1 | `NO_GLOVES` | Công nhân vi phạm quy định an toàn: không mang găng tay bảo hộ lao động. | `not wearing gloves`, `do not wear gloves`, `without gloves` | **453** |
| 2 | `NO_HELMET` | Công nhân vi phạm quy định an toàn: không đội mũ bảo hộ lao động. | `not wearing safety helmets`, `do not wear safety helmets`, `not wearing helmets` | **229** |
| 3 | `NO_MASK` | Công nhân vi phạm quy định an toàn: không đeo khẩu trang bảo hộ. | `not wearing masks`, `do not wear masks` | **200** |
| 4 | `USE_MOBILE_PHONE` | Công nhân thực hiện hành vi mất tập trung nguy hiểm: sử dụng điện thoại di động / gọi điện thoại. | `using mobile phones`, `use mobile phones`, `making phone calls`, `using phones` | **167** |
| 5 | `LIQUID_ON_GROUND` | Tồn tại chất lỏng đọng bất thường trên sàn/tường/thiết bị (nước đọng, rò rỉ dầu, dầu nhỏ giọt). | `standing water`, `water accumulation`, `oil leak`, `oil spill`, `oil dripping`, `liquid on ground` | **134** |
| 6 | `SMOKING` | Công nhân thực hiện hành vi cấm: hút thuốc lá trong phân xưởng sản xuất. | `smoking`, `personnel smoking`, `smoking personnel`, `a person is smoking` | **120** |
| 7 | `OPEN_FLAME` | Xuất hiện ngọn lửa trần nguy hiểm trong môi trường công nghiệp có nguy cơ cháy nổ cao. | `open flame`, `there is an open flame`, `an open flame in the image` | **117** |
| 8 | `FOREIGN_OBJECT` | Tồn tại dị vật / rác thải bất thường trên băng tải than, sàn hầm, sứ cách điện, thiết bị đường ray. | `foreign object on the belt`, `foreign objects`, `plastic bag`, `bottles on ground`, `foreign matter` | **115** |
| 9 | `SMOKE` | Xuất hiện khói bất thường bốc lên từ thiết bị hoặc môi trường làm việc. | `there is smoke`, `smoke` | **108** |
| 10 | `NONMOTORIZED_VEHICLE` | Xe thô sơ (xe đạp, xe điện, xe ba bánh) di chuyển trái phép lấn vào làn đường xe cơ giới trong hầm. | `non-motorized vehicle occupying motor vehicle lane`, `enter motor vehicle lane` | **101** |
| 11 | `DOOR_OPEN` | Cửa tủ điện phân phối / tủ điều khiển bị mở bất thường trong quá trình vận hành. | `cabinet door is abnormally open`, `cabinet doors are abnormally open`, `abnormal opening` | **34** |
| 12 | `PERSON_FALLEN` | Công nhân ngã gục / nằm bất động trên mặt sàn (sự cố y tế hoặc tai nạn lao động). | `person on the ground`, `person lying on the ground` | **10** |
| **Tổng** | **12 Hazard Atoms** | **Bao phủ 100% (1.000 / 1.000) mẫu Anomaly của bộ dữ liệu InspecSafe-V1** | — | **1.788 atoms** |

### 5.3 Phân bố số lượng Hazard Atoms trên mỗi mẫu ảnh

- **Mẫu chứa 1 atom:** **488 mẫu (48,8%)** — Phần lớn là các sự cố đơn lẻ như chỉ có khói, ngọn lửa trần, xe thô sơ lấn làn, hoặc nước đọng.
- **Mẫu chứa 2 atoms:** **287 mẫu (28,7%)** — Phổ biến là kết hợp vi phạm PPE (ví dụ: không đội mũ + không đeo găng) hoặc hành vi vi phạm kèm thiếu PPE (dùng điện thoại + không đeo găng).
- **Mẫu chứa 3 atoms:** **181 mẫu (18,1%)** — Thường là vi phạm đồng thời 3 loại PPE (không đội mũ + không đeo khẩu trang + không đeo găng), hoặc hút thuốc + dùng điện thoại + không đeo găng.
- **Mẫu chứa 4 atoms:** **37 mẫu (3,7%)** — Các ca vi phạm phức tạp kết hợp dị vật/cháy và thiếu toàn bộ PPE.
- **Mẫu chứa 5 atoms:** **7 mẫu (0,7%)** — Tổ hợp đa nguy cơ cực đoan trong phân xưởng.
- *Số nguy cơ trung bình trên mỗi mẫu:* **1.788 atoms / 1.000 mẫu = 1,79 atoms/mẫu**.

---

## 6. Kết quả tổng điều tra 1.000 mẫu Anomaly (Full 1,000-Anomaly Census)

### 6.1 Tổng hợp ở cấp độ Mẫu ảnh (Sample-Level Support Status)

Phân loại tổng hợp trạng thái hỗ trợ không gian trên toàn thể 1.000 mẫu Anomaly:

| Phân loại tổng hợp cấp Mẫu | Định nghĩa logic của tập hợp | Số lượng mẫu (`Sample Count`) | Tỷ lệ phần trăm |
|---|---|:---:|:---:|
| **`ALL_DIRECT`** | 100% các hazard atoms trong mẫu đều sở hữu đa giác đối tượng hỗ trợ trực tiếp (`DIRECT_OBJECT_SUPPORT`). | **367** | **36,7%** |
| **`MIXED_DIRECT_PROXY`** | Mẫu chứa ít nhất một hazard atom có hỗ trợ trực tiếp VÀ ít nhất một hazard atom chỉ có hỗ trợ đại diện (`WEAK_PROXY_SUPPORT`), không có atom unsupported. | **323** | **32,3%** |
| **`PROXY_ONLY`** | 100% các hazard atoms trong mẫu chỉ có thể đánh giá qua đa giác đại diện yếu (`Person`). | **251** | **25,1%** |
| **`HAS_UNSUPPORTED`** | Mẫu chứa ít nhất một hazard atom hoàn toàn không có ground truth không gian (`NO_CURRENT_SPATIAL_GT`). | **59** | **5,9%** |
| **Tổng cộng** | **Toàn bộ tập Anomaly của InspecSafe-V1** | **1.000** | **100,0%** |

> [!IMPORTANT]
> **Định nghĩa Tập con Hỗ trợ Trực tiếp (Direct-Support Sample Pool Candidate):**  
> Một mẫu ảnh được tính vào *Direct-Support Sample Pool* nếu **có ít nhất một hazard atom được xác minh là `DIRECT_OBJECT_SUPPORT`**.  
> Quy mô tập con này trên toàn dataset là: **$367 (\text{ALL\_DIRECT}) + 323 (\text{MIXED\_DIRECT\_PROXY}) + 31 (\text{HAS\_UNSUPPORTED có chứa direct atom}) = \mathbf{721\text{ mẫu}}$ (72,1%)**.  
> Để bảo toàn tính trung thực khoa học, SafeShift **bắt buộc phải công bố phân rã nội bộ của tập 721 mẫu này** (gồm 367 mẫu thuần túy trực tiếp và 354 mẫu có pha trộn proxy/unsupported), tuyệt đối không tuyên bố 721 mẫu này có nhãn giải thích lý do hoàn chỉnh cho toàn bộ bức ảnh.

### 6.2 Tổng hợp ở cấp độ Nguy cơ Nguyên tử (Hazard-Atom Level Support Status)

Phân loại trạng thái hỗ trợ trên toàn bộ 1.788 hazard atoms:

| Trạng thái hỗ trợ của Atom | Bản chất phương pháp luận | Số lượng Atom (`Atom Count`) | Tỷ lệ phần trăm |
|---|---|:---:|:---:|
| **`WEAK_PROXY_SUPPORT`** | Không có chú thích trực tiếp cho phát biểu nguy cơ; chỉ có thể định vị qua đa giác thực thể đại diện (`Person` cho thiếu PPE, tư thế người ngã, xe thô sơ lấn làn). | **947** | **53,0%** |
| **`DIRECT_OBJECT_SUPPORT`** | Có một hoặc nhiều đa giác đối tượng chú thích trực tiếp chính thực thể nguy cơ trong ảnh (`Mobile Phone`, `Cigarette`, `Open Flame`, `Smoke`, `Liquid`, `Oil`, `Plastic Bag`, `Bicycle`, ...). | **781** | **43,7%** |
| **`NO_CURRENT_SPATIAL_GT`** | Hoàn toàn không có đa giác nào trong tệp JSON hỗ trợ cho phát biểu nguy cơ (cửa tủ điện mở bất thường, hoặc các ca thiếu sót chú thích đối tượng). | **60** | **3,4%** |
| **Tổng cộng** | **Toàn bộ Hazard Atoms** | **1.788** | **100,0%** |

### 6.3 Bảng chéo: Hazard Atom $\times$ Trạng thái Hỗ trợ (Atom $\times$ Support Status)

| Mã Nguy cơ Nguyên tử (`Hazard Atom`) | DIRECT_OBJECT_SUPPORT | WEAK_PROXY_SUPPORT | NO_CURRENT_SPATIAL_GT | Tổng số Atom |
|---|:---:|:---:|:---:|:---:|
| `NO_GLOVES` | 0 | 451 | 2 | 453 |
| `NO_HELMET` | 0 | 229 | 0 | 229 |
| `NO_MASK` | 0 | 199 | 1 | 200 |
| `USE_MOBILE_PHONE` | 165 | 2 | 0 | 167 |
| `LIQUID_ON_GROUND` | 122 | 0 | 12 | 134 |
| `SMOKING` | 118 | 2 | 0 | 120 |
| `OPEN_FLAME` | 117 | 0 | 0 | 117 |
| `FOREIGN_OBJECT` | 109 | 0 | 6 | 115 |
| `SMOKE` | 103 | 0 | 5 | 108 |
| `NONMOTORIZED_VEHICLE` | 47 | 54 | 0 | 101 |
| `DOOR_OPEN` | 0 | 0 | 34 | 34 |
| `PERSON_FALLEN` | 0 | 10 | 0 | 10 |
| **Tổng cộng** | **781** | **947** | **60** | **1.788** |

### 6.4 Bảng chéo: Hazard Atom $\times$ Cấp độ An toàn (Atom $\times$ Safety Level)

| Mã Nguy cơ Nguyên tử (`Hazard Atom`) | Level01 (High Risk) | Level02 (Moderate Risk) | Level03 (Minor Hazard) | Tổng số Atom |
|---|:---:|:---:|:---:|:---:|
| `NO_GLOVES` | 303 | 147 | 3 | 453 |
| `NO_HELMET` | 126 | 103 | 0 | 229 |
| `NO_MASK` | 109 | 84 | 7 | 200 |
| `USE_MOBILE_PHONE` | 96 | 71 | 0 | 167 |
| `LIQUID_ON_GROUND` | 73 | 55 | 6 | 134 |
| `SMOKING` | 120 | 0 | 0 | 120 |
| `OPEN_FLAME` | 117 | 0 | 0 | 117 |
| `FOREIGN_OBJECT` | 40 | 75 | 0 | 115 |
| `SMOKE` | 108 | 0 | 0 | 108 |
| `NONMOTORIZED_VEHICLE` | 101 | 0 | 0 | 101 |
| `DOOR_OPEN` | 8 | 26 | 0 | 34 |
| `PERSON_FALLEN` | 10 | 0 | 0 | 10 |
| **Tổng số atoms** | **1.211** | **561** | **16** | **1.788** |

*Ghi chú:* 15 mẫu Anomaly thuộc `Level03` chứa tổng cộng 16 hazard atoms (gồm 7 `NO_MASK`, 6 `LIQUID_ON_GROUND`, 3 `NO_GLOVES`).

### 6.5 Bảng chéo: Hazard Atom $\times$ Miền Thao tác Thư mục (Atom $\times$ Folder Domain)

| Mã Nguy cơ Nguyên tử (`Hazard Atom`) | coal_conveyor | metallurgy | oil_chemical | power | tunnel | Tổng cộng |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `NO_GLOVES` | 145 | 7 | 181 | 59 | 61 | 453 |
| `NO_HELMET` | 79 | 5 | 24 | 32 | 89 | 229 |
| `NO_MASK` | 73 | 5 | 59 | 17 | 46 | 200 |
| `USE_MOBILE_PHONE` | 77 | 6 | 57 | 11 | 16 | 167 |
| `LIQUID_ON_GROUND` | 3 | 1 | 126 | 0 | 4 | 134 |
| `SMOKING` | 47 | 0 | 67 | 6 | 0 | 120 |
| `OPEN_FLAME` | 46 | 1 | 23 | 13 | 34 | 117 |
| `FOREIGN_OBJECT` | 64 | 0 | 0 | 17 | 34 | 115 |
| `SMOKE` | 7 | 0 | 87 | 6 | 8 | 108 |
| `NONMOTORIZED_VEHICLE` | 0 | 0 | 0 | 0 | 101 | 101 |
| `DOOR_OPEN` | 0 | 0 | 3 | 1 | 30 | 34 |
| `PERSON_FALLEN` | 2 | 0 | 0 | 8 | 0 | 10 |
| **Tổng số atoms** | **543** | **25** | **627** | **170** | **423** | **1.788** |

*Phát hiện thực chứng then chốt về sự lệch miền:*
- Nguy cơ `NONMOTORIZED_VEHICLE` (xe thô sơ lấn làn) **tập trung 100% tại miền `tunnel`** (101 / 101 atoms).
- Nguy cơ `LIQUID_ON_GROUND` (nước/dầu tràn sàn) **tập trung tới 94,0% tại miền `oil_chemical`** (126 / 134 atoms).
- Nguy cơ `DOOR_OPEN` (cửa tủ mở bất thường) **tập trung tới 88,2% tại miền `tunnel`** (30 / 34 atoms).
- Nguy cơ `PERSON_FALLEN` (người ngã) **chỉ xuất hiện tại `power` (8) và `coal_conveyor` (2)**.
- Miền `metallurgy` chỉ có tổng cộng 25 atoms (phân bố trên 9 mẫu Anomaly; trong đó 8/9 mẫu mang khẳng định text là `oil_chemical`).

### 6.6 Bảng chéo: Hazard Atom $\times$ Phân chia Dữ liệu Gốc (Atom $\times$ Split)

| Mã Nguy cơ Nguyên tử (`Hazard Atom`) | train | test | Tổng cộng | Tỷ lệ Test / Total |
|---|:---:|:---:|:---:|:---:|
| `NO_GLOVES` | 344 | 109 | 453 | 24,1% |
| `NO_HELMET` | 177 | 52 | 229 | 22,7% |
| `NO_MASK` | 149 | 51 | 200 | 25,5% |
| `USE_MOBILE_PHONE` | 137 | 30 | 167 | 18,0% |
| `LIQUID_ON_GROUND` | 110 | 24 | 134 | 17,9% |
| `SMOKING` | 88 | 32 | 120 | 26,7% |
| `OPEN_FLAME` | 90 | 27 | 117 | 23,1% |
| `FOREIGN_OBJECT` | 90 | 25 | 115 | 21,7% |
| `SMOKE` | 78 | 30 | 108 | 27,8% |
| `NONMOTORIZED_VEHICLE` | 76 | 25 | 101 | 24,8% |
| `DOOR_OPEN` | 22 | 12 | 34 | 35,3% |
| `PERSON_FALLEN` | 8 | 2 | 10 | 20,0% |
| **Tổng số atoms** | **1.369** | **419** | **1.788** | **23,4%** |

*Ghi chú:* Tỷ lệ phân bổ atom ở tập test là 23,4%, hoàn toàn tương thích với tỷ lệ mẫu Anomaly ở tập test (251 / 1.000 = 25,1%).

### 6.7 Bảng chéo: Phân loại cấp Mẫu $\times$ Miền Thao tác & Phân chia Split

**Theo Miền Thao tác Thư mục (`folder_domain`):**

| Phân loại cấp Mẫu | coal_conveyor | metallurgy | oil_chemical | power | tunnel | Tổng cộng |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `ALL_DIRECT` | 80 | 2 | 159 | 31 | 95 | **367** |
| `MIXED_DIRECT_PROXY` | 131 | 6 | 146 | 16 | 24 | **323** |
| `PROXY_ONLY` | 42 | 1 | 36 | 52 | 120 | **251** |
| `HAS_UNSUPPORTED` | 3 | 0 | 20 | 3 | 33 | **59** |
| **Tổng cộng mẫu** | **256** | **9** | **361** | **102** | **272** | **1.000** |

**Theo Phân chia Gốc (`split`):**

| Phân loại cấp Mẫu | train | test | Tổng cộng |
|---|:---:|:---:|:---:|
| `ALL_DIRECT` | 272 | 95 | **367** |
| `MIXED_DIRECT_PROXY` | 261 | 62 | **323** |
| `PROXY_ONLY` | 175 | 76 | **251** |
| `HAS_UNSUPPORTED` | 41 | 18 | **59** |
| **Tổng cộng mẫu** | **749** | **251** | **1.000** |

---

## 7. Bảng ánh xạ nhãn đối tượng hỗ trợ (Object-Support Mapping Table)

Bảng đối chiếu minh bạch giữa phát biểu nguy cơ nguyên tử và các nhãn đối tượng hình học có sẵn trong tệp JSON, tuân thủ nguyên tắc không âm thầm gộp nhãn (`no silent merging`) và giữ nguyên nhãn thô (`raw labels`):

| Hazard Atom | Nhãn đối tượng hỗ trợ ứng viên (`Candidate Object Labels`) | Loại hỗ trợ (`Support Type`) | Quy tắc ánh xạ tường minh (`Mapping Rule`) | Trường hợp biên & Điểm chưa giải quyết (`Ambiguities / Edge Cases`) | Số lượng Atom |
|---|---|:---:|---|---|:---:|
| `USE_MOBILE_PHONE` | `Mobile Phone` | DIRECT | Mẫu có đa giác nhãn `Mobile Phone`. | 165 mẫu có `Mobile Phone`. Có **2 mẫu** thiếu nhãn này (`002777` và `003015`), chỉ có `Person` $\rightarrow$ phân loại là `WEAK_PROXY_SUPPORT`. | 167 |
| `SMOKING` | `Cigarette` | DIRECT | Mẫu có đa giác nhãn `Cigarette`. | 118 mẫu có `Cigarette`. Có **2 mẫu** thiếu nhãn này (`002489` và `002765`), chỉ có `Person` $\rightarrow$ phân loại là `WEAK_PROXY_SUPPORT`. | 120 |
| `OPEN_FLAME` | `Open Flame` | DIRECT | Mẫu có đa giác nhãn `Open Flame`. | **117 / 117 mẫu (100%)** có đa giác `Open Flame`. Độ nhất quán tuyệt đối. | 117 |
| `SMOKE` | `Smoke` | DIRECT | Mẫu có đa giác nhãn `Smoke`. | 103 mẫu có `Smoke`. Có **5 mẫu** hoàn toàn thiếu nhãn `Smoke` trong JSON (`002846`, `002851`, `002871`, `002977`, `002330`) $\rightarrow$ `NO_CURRENT_SPATIAL_GT`. | 108 |
| `LIQUID_ON_GROUND` | `Liquid`, `Oil`, `Water Droplet` | DIRECT | Mẫu có đa giác nhãn `Liquid` (87) hoặc `Oil` (34) hoặc `Water Droplet` (1). | 122 mẫu có direct label. Có **12 mẫu** mô tả nước/dầu tràn nhưng hoàn toàn không có đa giác chất lỏng nào $\rightarrow$ `NO_CURRENT_SPATIAL_GT`. | 134 |
| `FOREIGN_OBJECT` | `Plastic Bag`, `Toilet Paper`, `Water Bottle`, `Cardboard Box`, `White Paper`, `Iron Barrel`, `Shovel`, `Iron Wire`, `Mineral Water`, `Paper Shell`, `Plastic Bottle` | DIRECT | Mẫu có ít nhất một đa giác đại diện cho dị vật/rác thải vật lý cụ thể. | 109 mẫu có direct object polygon (gồm rác sinh hoạt và dị vật công nghiệp). Có **6 mẫu** (`002564`, `002655`, `002410`, `002445`, `002446`, `002447`) hoàn toàn thiếu đa giác dị vật $\rightarrow$ `NO_CURRENT_SPATIAL_GT`. | 115 |
| `NONMOTORIZED_VEHICLE` | `Bicycle`, `Electric Vehicle`, `Tricycle` (Direct Vehicle); `Person` (Weak Proxy) | DIRECT / PROXY | Mẫu có đa giác phương tiện thô sơ cụ thể (47 atoms) $\rightarrow$ DIRECT; mẫu chỉ có đa giác người điều khiển `Person` (54 atoms) $\rightarrow$ PROXY. | Nguy cơ mang bản chất quan hệ/lấn làn (`relational / lane violation`). Đa giác xe hay người đều không bao trùm hành vi vi phạm làn đường; tuy nhiên phương tiện là vật thể trực tiếp hiện hữu. | 101 |
| `NO_HELMET` | `Person` | WEAK_PROXY | Mẫu vi phạm không đội mũ; dùng đa giác toàn thân `Person` làm vùng đại diện gián tiếp. | **229 / 229 mẫu (100%)** đều có đa giác `Person`. Hoàn toàn không có phân vùng vùng đầu (`Head`) hay vùng mũ bị thiếu. | 229 |
| `NO_GLOVES` | `Person` | WEAK_PROXY | Mẫu vi phạm không đeo găng; dùng đa giác toàn thân `Person` làm vùng đại diện gián tiếp. | 451 mẫu có `Person`. Có **2 mẫu** (`002893` và `002288`) hoàn toàn thiếu đa giác `Person` trong JSON $\rightarrow$ `NO_CURRENT_SPATIAL_GT`. Không có phân vùng bàn tay (`Hands`). | 453 |
| `NO_MASK` | `Person` | WEAK_PROXY | Mẫu vi phạm không đeo khẩu trang; dùng đa giác `Person` làm vùng đại diện gián tiếp. | 199 mẫu có `Person`. Có **1 mẫu** (`002288`) hoàn toàn thiếu đa giác `Person` trong JSON $\rightarrow$ `NO_CURRENT_SPATIAL_GT`. Không có phân vùng khuôn mặt (`Face`). | 200 |
| `PERSON_FALLEN` | `Person` | WEAK_PROXY | Mẫu có người nằm/ngã trên sàn; dùng đa giác `Person` làm vùng đại diện. | **10 / 10 mẫu (100%)** đều có đa giác `Person`. Đa giác chỉ khoanh người, không khoanh trạng thái ngã/bất tỉnh. | 10 |
| `DOOR_OPEN` | *Không có nhãn phù hợp* | NO_GT | Khẳng định cửa tủ mở bất thường. | Toàn bộ **34 / 34 mẫu (100%)** không có bất kỳ đa giác nào khoanh vùng cánh cửa tủ hay khe hở cửa bị mở $\rightarrow$ `NO_CURRENT_SPATIAL_GT`. 12 mẫu ở tunnel có nhãn `Distribution Box` nhưng không phản ánh trạng thái cửa mở. | 34 |

---

## 8. Tập con Hỗ trợ Trực tiếp (Direct-Support Subset Analysis)

Quy mô thực tế của tập con có hỗ trợ trực tiếp được làm rõ dứt điểm qua cuộc tổng điều tra D6:

1. **Tập con Mẫu Thuần túy Trực tiếp (`ALL_DIRECT`):**
   - Đúng **367 mẫu ảnh (36,7% tổng Anomaly)**.
   - 100% các nguy cơ trong các mẫu này đều có đa giác đối tượng cụ thể tương ứng (`Open Flame`, `Smoke`, `Mobile Phone`, `Cigarette`, `Liquid`, `Plastic Bag`, ...).
   - Đây là tập con duy nhất mà mô hình có thể được đánh giá bám bằng chứng không gian ở mức độ đối tượng mà **không cần viện dẫn bất kỳ nhãn đại diện gián tiếp (`proxy`) nào**.
2. **Tập con Mẫu Hỗn hợp (`MIXED_DIRECT_PROXY`):**
   - Đúng **323 mẫu ảnh (32,3% tổng Anomaly)**.
   - Đây là các trường hợp đa nguy cơ kết hợp giữa một đối tượng vật lý hiện hữu và một vi phạm thiếu trang bị PPE (ví dụ: công nhân vừa hút thuốc vừa không đeo găng tay; có ngọn lửa trần và công nhân không đội mũ bảo hộ).
   - *Chính sách xử lý:* Trong mẫu hỗn hợp, nguy cơ trực tiếp (`smoking`) có thể đánh giá độc lập qua `Cigarette`, trong khi vi phạm PPE (`no gloves`) chỉ có thể đánh giá qua `Person`. Việc phân rã ở cấp Hazard Atom giúp cứu vãn 323 mẫu này khỏi việc bị loại bỏ một cách lãng phí.
3. **Tổng số Hazard Atoms Hỗ trợ Trực tiếp:**
   - Đạt **781 atoms (43,7% tổng số hazard atoms)**, phân bố rộng khắp trên 721 mẫu ảnh.

---

## 9. Tập con Hỗ trợ Đại diện Yếu (Weak-Proxy Subset Analysis)

1. **Tập con Mẫu Thuần túy Đại diện (`PROXY_ONLY`):**
   - Đúng **251 mẫu ảnh (25,1% tổng Anomaly)**.
   - 100% các nguy cơ trong nhóm này là các vi phạm vắng mặt trang thiết bị bảo hộ (`ABSENCE_BASED`: không đội mũ, không đeo găng, không đeo khẩu trang) hoặc tư thế người nằm trên sàn (`PERSON_FALLEN`) hoặc xe thô sơ chỉ có nhãn `Person`.
   - Vùng ground truth duy nhất có thể sử dụng là hộp bao toàn thân của đối tượng **`Person`**.
2. **Cảnh báo bản chất phương pháp luận của Weak Proxy:**
   - Đa giác `Person` bao trùm toàn bộ cơ thể người từ đầu đến chân.
   - Đối với vi phạm *"không đội mũ"* (`NO_HELMET`), vùng bằng chứng chân thực phải là vùng đầu trần (`bare head`).
   - Đối với vi phạm *"không đeo găng tay"* (`NO_GLOVES`), vùng bằng chứng chân thực phải là hai bàn tay trần (`bare hands`).
   - Nếu chấp nhận `Person` làm ground truth: Một mô hình VLM tập trung vào đôi ủng bảo hộ của công nhân nhưng nằm lọt trong hộp bao `Person` vẫn được thuật toán tính là "bám bằng chứng chính xác" ($IoU > \text{threshold}$).
   - Do đó, SafeShift **chỉ coi đây là Đại diện Yếu (`WEAK_PROXY_SUPPORT`)**, bắt buộc phải phân tách rạch ròi với `DIRECT_OBJECT_SUPPORT` trong mọi bảng báo cáo kết quả thực nghiệm của RQ3.

---

## 10. Các trường hợp Chưa có GT Không gian và Mơ hồ (Unsupported & Ambiguous Cases)

Cuộc tổng điều tra D6 phát hiện chính xác **60 hazard atoms** nằm trong **59 mẫu ảnh** thuộc nhóm **`NO_CURRENT_SPATIAL_GT`** (hoàn toàn không có ground truth không gian):

1. **Nhóm Cửa tủ điện mở bất thường (`DOOR_OPEN`):**
   - Đúng **34 hazard atoms** (34 mẫu ảnh).
   - Kiểm tra trực tiếp trên 5.013 tệp JSON của bộ dữ liệu gốc xác nhận: **Hoàn toàn không tồn tại bất kỳ nhãn nào tên `Cabinet Door Open` hay `Door`**.
   - Có 12 mẫu tại hầm (`tunnel`) có nhãn `Distribution Box`, nhưng đa giác chỉ khoanh bao quát cả chiếc tủ điện, hoàn toàn không chỉ định vị trí cánh cửa mở hay khe hở bất thường. 22 mẫu còn lại hoàn toàn không có bất kỳ đa giác nào liên quan đến tủ hay cửa.
   - *Kết luận:* `DOOR_OPEN` hiện tại là **Unevaluable for Grounding** (hoàn toàn không thể đánh giá bám bằng chứng không gian nếu không bổ sung nhãn mới).
2. **Nhóm Thiếu sót Chú thích Chất lỏng (`Missing Liquid Annotation`):**
   - Đúng **12 hazard atoms** có khẳng định văn bản rõ ràng về dầu/nước tràn trên mặt đất (ví dụ: `oil_chemical-Level01-Wheeled-002745-001`, `002798-001`, `002872-001`), nhưng annotator gốc hoàn toàn quên không vẽ đa giác nhãn `Liquid` hay `Oil`.
3. **Nhóm Thiếu sót Chú thích Dị vật (`Missing Foreign Object Annotation`):**
   - Đúng **6 hazard atoms** mô tả dị vật trên băng chuyền than hoặc sứ cách điện (`002564-001`, `002655-001`, `002410-001`, `002445`–`002447`), nhưng JSON chỉ khoanh các thiết bị nền (`Switchgear`, `Bus Bar`, `Belt`, `Idler Roller`) mà không có đa giác dị vật.
4. **Nhóm Thiếu sót Chú thích Khói (`Missing Smoke Annotation`):**
   - Đúng **5 hazard atoms** mô tả có khói (`002846-001`, `002851-001`, `002871-001`, `002977-001`, `002330-001`), nhưng JSON hoàn toàn thiếu nhãn `Smoke` (ví dụ `002846` chỉ khoanh 6 đa giác `Stent`).
5. **Nhóm Thiếu sót Chú thích Đối tượng Người (`Missing Person Annotation`):**
   - Đúng **3 hazard atoms** mô tả vi phạm PPE (`002893-001` và `002288-001`) nhưng JSON hoàn toàn không có cả đa giác `Person`.
6. **Tổng số mẫu ảnh bị ảnh hưởng:** Đúng **59 mẫu** chứa ít nhất một hazard atom thiếu nhãn không gian (gồm 31 mẫu có chứa cả hazard atom khác có direct support, và 28 mẫu hoàn toàn không có bất kỳ atom trực tiếp nào). Toàn bộ 59 mẫu này được gán nhãn trạng thái mẫu là **`HAS_UNSUPPORTED`**.

---

## 11. Các tầng nguy cơ ứng viên cho RQ2 (RQ2 Hazard-Strata Candidates)

Câu hỏi nghiên cứu RQ2 yêu cầu phân tích sự tập trung lỗi của mô hình VLM theo các phân tầng nguy cơ đã được kiểm chứng (`verified hazard strata`). Dựa trên kết quả tổng điều tra D6, SafeShift đề xuất **7 Phân tầng Nguy cơ Ứng viên (`Candidate Hazard Strata`)**:

| Mã Tầng Nguy cơ | Định nghĩa & Thành phần Atom | Số mẫu (`Sample N`) | Số Atom (`Atom N`) | Độ bao phủ Miền (`Domain Coverage`) | Phân bố Cấp An toàn | Trạng thái Hỗ trợ chính | Yếu tố gây nhiễu lớn (`Major Confounders`) | Đánh giá Mức độ Phù hợp cho RQ2 |
|---|---|:---:|:---:|---|---|:---:|---|:---:|
| **Strata A: `FIRE_AND_SMOKE`** | Nguy cơ hỏa hoạn và khói (`OPEN_FLAME` + `SMOKE`) | 200 | 225 | Bao phủ 5 miền (trừ metallurgy chỉ có 1 atom) | 100% Level01 (225) | DIRECT (97,8%) | Đi kèm vi phạm PPE trong các mẫu phức tạp. | **RẤT PHÙ HỢP (HIGHLY SUITABLE)**. Direct support mạnh, tín hiệu thị giác rõ ràng. |
| **Strata B: `PPE_ABSENCE`** | Vi phạm thiếu trang bị bảo hộ cá nhân (`NO_GLOVES` + `NO_HELMET` + `NO_MASK`) | 545 | 882 | Đầy đủ 5 miền công nghiệp | Level01 (538), Level02 (334), Level03 (10) | WEAK_PROXY (99,7%) | Đa giác toàn thân `Person` gây thiên lệch diện tích lớn. | **RẤT PHÙ HỢP (HIGHLY SUITABLE)**. Phân tầng quy mô lớn nhất, đại diện xuất sắc cho bài toán an toàn lao động. |
| **Strata C: `UNAUTHORIZED_BEHAVIOR`** | Hành vi vi phạm quy tắc tập trung (`USE_MOBILE_PHONE` + `SMOKING`) | 247 | 287 | Đầy đủ 5 miền công nghiệp | Level01 (216), Level02 (71) | DIRECT (98,6%) | Thường đồng xuất hiện với vi phạm không đeo găng tay. | **RẤT PHÙ HỢP (HIGHLY SUITABLE)**. Direct support rất cao (`Mobile Phone`, `Cigarette`). |
| **Strata D: `ENVIRONMENTAL_SLIP_HAZARD`** | Nguy cơ trơn trượt / rò rỉ chất lỏng (`LIQUID_ON_GROUND`) | 134 | 134 | **Lệch miền cực đoan:** 126/134 nằm tại `oil_chemical` | Level01 (73), Level02 (55), Level03 (6) | DIRECT (91,0%) | **Nhiễu miền nghiêm trọng (Domain Confounder):** 94% mẫu nằm ở hóa chất dầu khí. | **PHÙ HỢP CÓ ĐIỀU KIỆN (CONDITIONALLY SUITABLE)**. Cần kiểm soát biến miền khi phân tích. |
| **Strata E: `OBSTRUCTION_AND_FOREIGN_OBJECT`** | Dị vật cản trở và phương tiện lấn làn (`FOREIGN_OBJECT` + `NONMOTORIZED_VEHICLE`) | 211 | 216 | `tunnel` (135), `coal_conveyor` (64), `power` (17) | Level01 (141), Level02 (75) | DIRECT (72,2%) / PROXY (25,0%) | Nonmotorized vehicle tập trung 100% tại tunnel. | **PHÙ HỢP (SUITABLE)**. Cần tách rã giữa dị vật tĩnh và phương tiện giao thông. |
| **Strata F: `EQUIPMENT_STATE_ANOMALY`** | Trạng thái thiết bị mở bất thường (`DOOR_OPEN`) | 34 | 34 | `tunnel` (30), `oil_chemical` (3), `power` (1) | Level01 (8), Level02 (26) | NO_CURRENT_SPATIAL_GT (100%) | **Hoàn toàn không có ground truth không gian.** | **CHỈ PHÙ HỢP CHO PHÂN LOẠI (Classification Only)**, không dùng cho Grounding. |
| **Strata G: `PERSONNEL_FALLEN`** | Tai nạn ngã bất động trên sàn (`PERSON_FALLEN`) | 10 | 10 | Chỉ có tại `power` (8) và `coal_conveyor` (2) | 100% Level01 (10) | WEAK_PROXY (100%) | Cỡ mẫu quá nhỏ ($N=10$), thiếu lực thống kê. | **KHÔNG KHUYẾN NGHỊ LÀM TẦNG ĐỘC LẬP (NOT RECOMMENDED ALONE)**. Nên gộp vào phân tích sự cố người. |

---

## 12. Định nghĩa phạm vi đánh giá RQ3 (RQ3 Grounding Scope)

Để tránh ngộ nhận phương pháp luận và bảo đảm tính so sánh công bằng, câu hỏi nghiên cứu RQ3 bắt buộc phải được phân rã thành hai phạm vi đánh giá độc lập:

### 12.1 RQ3-A: Direct Object-Support Grounding (Đánh giá Bám vùng Đối tượng Trực tiếp)

- **Phạm vi đánh giá:** Thực hiện độc quyền trên các cặp mẫu - nguy cơ thuộc diện **`DIRECT_OBJECT_SUPPORT`**.
- **Không gian đánh giá:**
  - Cấp độ Mẫu: Thực hiện trên **367 mẫu thuần túy trực tiếp (`ALL_DIRECT`)** làm tập chuẩn sạch nhất, hoặc mở rộng sang **721 mẫu thuộc `Direct-Support Sample Pool`** khi đánh giá phân rã theo từng hazard atom trực tiếp.
  - Cấp độ Hazard Atom: Thực hiện trên **781 hazard atoms** có đa giác đối tượng trực tiếp (`Open Flame`, `Smoke`, `Mobile Phone`, `Cigarette`, `Liquid`, `Oil`, `Plastic Bag`, `Bicycle`, ...).
- **Nguyên tắc đối sánh:** Hộp bao dự đoán của mô hình được đối chiếu trực tiếp với hộp bao phái sinh từ đa giác của chính thực thể nguy cơ.

### 12.2 RQ3-B: Weak Proxy Grounding (Đánh giá Bám vùng Đại diện Yếu)

- **Phạm vi đánh giá:** Thực hiện trên các mẫu - nguy cơ thuộc diện **`WEAK_PROXY_SUPPORT`**.
- **Không gian đánh giá:**
  - Cấp độ Mẫu: **251 mẫu thuần túy đại diện (`PROXY_ONLY`)**.
  - Cấp độ Hazard Atom: **947 hazard atoms** (chủ yếu là `NO_GLOVES`, `NO_HELMET`, `NO_MASK`, `PERSON_FALLEN` và xe thô sơ không có nhãn xe).
- **Nguyên tắc đối sánh:** Hộp bao dự đoán của mô hình được đối chiếu với hộp bao của đối tượng đại diện **`Person`**.
- **Quy tắc báo cáo bắt buộc:** Kết quả của RQ3-A và RQ3-B **PHẢI ĐƯỢC BÁO CÁO TÁCH BIỆT TRONG HAI CỘT / BẢNG RIÊNG**. Tuyệt đối không tính điểm trung bình gộp (`pooled average`) giữa Direct và Proxy thành một chỉ số duy nhất mà không ghi chú.
- **Về Full Hazard Rationale Grounding:** Vẫn tiếp tục được xác định là **NOT CURRENTLY FEASIBLE** trên InspecSafe-V1 nếu không triển khai chiến dịch gán nhãn D7.

---

## 13. Phân tích các lựa chọn Giao diện Đầu ra Grounding D4 (D4 Output-Interface Options)

Đánh giá 4 phương án biểu diễn đầu ra bám bằng chứng của mô hình VLM:

### Phương án D4-A: Textual Normalized Bounding Box (Hộp bao tọa độ chuẩn hóa dạng văn bản)
- *Định dạng chuẩn:* Mô hình xuất tọa độ 4 điểm cực biên dưới dạng văn bản có cấu trúc: `[ymin, xmin, ymax, xmax]` hoặc `[x1, y1, x2, y2]`, chuẩn hóa trong thang đo `[0, 1000]` hoặc `[0.0, 1.0]`.
- *Ưu điểm:*
  - Được hỗ trợ bản địa hoặc tuân thủ chỉ dẫn prompt xuất sắc bởi hầu hết các dòng VLM hàng đầu thương mại (Gemini 1.5/2.0, GPT-4o, Claude 3.5 Sonnet) và mã nguồn mở (Qwen2-VL, InternVL-2.5).
  - Tương thích tự nhiên với việc suy biến tọa độ từ đa giác ground truth (`polygon` $\rightarrow$ `bbox`).
  - Dễ dàng parse tự động bằng biểu thức chính quy (regex) với tỷ lệ lỗi cú pháp thấp.
  - Lưu giữ đầy đủ thông tin về vị trí trung tâm, quy mô kích thước và tỷ lệ khung hình của đối tượng.
- *Hạn chế:* Không nắm bắt được đường biên hình học uốn lượn phức tạp của vết tràn dầu hay ngọn lửa.

### Phương án D4-B: Pointing Point (Điểm trỏ tâm / Tọa độ điểm)
- *Định dạng chuẩn:* Mô hình xuất một cặp tọa độ duy nhất: `[x, y]`.
- *Ưu điểm:* Cú pháp cực kỳ ngắn gọn; dễ yêu cầu mô hình nhắm vào trung tâm vật thể; phù hợp với độ đo Pointing Game.
- *Hạn chế:* Bị mất hoàn toàn thông tin về quy mô kích thước (scale) và ranh giới không gian của đối tượng; không thể tính toán chỉ số giao thoa diện tích (IoU).

### Phương án D4-C: Polygon / Segmentation Mask (Đa giác phân vùng / Mặt nạ nhị phân)
- *Định dạng chuẩn:* Mô hình xuất danh sách các điểm tọa độ đa giác khép kín `[[x1, y1], [x2, y2], ...]` hoặc chuỗi mã hóa Run-Length Encoding (RLE).
- *Ưu điểm:* Khớp 1:1 với định dạng đa giác gốc của bộ dữ liệu InspecSafe-V1.
- *Hạn chế:* Chi phí token khổng lồ; tỷ lệ parse thất bại (cú pháp lỗi, đa giác tự cắt, không khép kín) cực kỳ cao trên các mô hình tổng quát thương mại; chỉ một số ít mô hình chuyên biệt (như Kosmos-2, Florence-2) mới hỗ trợ mask tốt.

### Phương án D4-D: Attention Map / Visual Heatmap (Bản đồ chú ý thị giác / Bản đồ nhiệt)
- *Định dạng chuẩn:* Trích xuất ma trận trọng số chú ý (Cross-attention weights) từ các tầng transformer của mô hình.
- *Ưu điểm:* Không đòi hỏi mô hình phải sinh tọa độ bằng văn bản.
- *Hạn chế chí mạng:*
  - **Closed APIs hoàn toàn không cung cấp:** Toàn bộ các mô hình thương mại qua API (OpenAI, Google Gemini, Anthropic) đều không expose attention weights.
  - **Không phản ánh suy luận nhân quả:** Nhiều nghiên cứu học thuật đã chứng minh attention weights không đồng nhất với giải thích nhân quả (Attention is not Explanation).
  - **Khác biệt kiến trúc:** Các mô hình khác nhau có độ phân giải patch, cơ chế pooling và số lượng head khác nhau, triệt tiêu tính so sánh công bằng.

---

## 14. Phân định Raw Model Output và Canonical Parsed Record

Để bảo đảm tính toàn vẹn nghiên cứu và khả năng tái lập theo quy định tại `AGENTS.md`, SafeShift thiết lập quy trình xử lý dữ liệu đầu ra hai lớp:

1. **Lớp 1: Raw Model Response (Phản hồi Thô Nguyên gốc):**
   - **Bắt buộc lưu trữ nguyên văn 100% chuỗi văn bản trả về của mô hình**, không thực hiện bất kỳ thao tác cắt xén, chuẩn hóa hay ghi đè nào.
   - Đi kèm siêu dữ liệu bắt buộc: `sample_id`, `run_id`, `model_name`, `model_version`, `prompt_template_id`, `decoding_parameters` (temperature, top_p, seed), `timestamp_utc`.
   - Lưu trữ cục bộ tại: `outputs/raw_predictions/{run_id}/{sample_id}.json`.
2. **Lớp 2: Canonical Parsed Grounding Record (Bản ghi Bám bằng chứng Chuẩn hóa):**
   - Là sản phẩm phái sinh sau khi chạy bộ parser có kiểm soát trên Raw Response.
   - Schema ứng viên gồm các trường:
     - `sample_id` (`string`): Định danh mẫu.
     - `predicted_safety_level` (`string` | `null`): Nhãn an toàn parse được (`Level01`..`Level04`).
     - `parsed_hazard_claims` (`list[string]`): Danh sách các nguy cơ mô hình phát hiện.
     - `raw_bbox` (`list[float]` | `null`): Hộp bao thô parse được từ văn bản.
     - `canonical_bbox` (`list[float]` | `null`): Hộp bao đã chuẩn hóa về thang `[0, 1]` tương đối so với kích thước ảnh gốc (`[ymin, xmin, ymax, xmax]`).
     - `derived_center_point` (`list[float]` | `null`): Điểm tâm tọa độ suy biến từ bbox: $[(xmin+xmax)/2, (ymin+ymax)/2]$.
     - `parse_status` (`string`): Trạng thái parse cú pháp (`SUCCESS`, `SYNTAX_ERROR`, `OUT_OF_BOUNDS`, `NO_BOX_GENERATED`).
     - `grounding_evaluable` (`boolean`): Cờ đánh dấu mẫu có thuộc tập con đánh giá được hay không.

---

## 15. Khả thi của Chỉ số Ảo giác Đối tượng (Object Hallucination Metric Feasibility)

Giảng viên hướng dẫn đã gợi ý xem xét chỉ số Đo lường Ảo giác Đối tượng (`Object Hallucination Rate`). SafeShift đã thực hiện đánh giá tính khả thi thực chứng trên bộ dữ liệu:

1. **Bản chất của Annotation Completeness:**
   - Để đo lường khách quan tỷ lệ ảo giác của mô hình trên toàn dataset (ví dụ: mô hình nhắc đến vật thể $X$, nếu $X \notin \text{Annotations}$ thì kết luận mô hình bị ảo giác), bộ dữ liệu bắt buộc phải đạt điều kiện: **Chú thích đầy đủ triệt để mọi đối tượng trong ảnh (`Exhaustive Object Annotation`)**.
2. **Hiện trạng thực tế của InspecSafe-V1:**
   - Kiểm toán thực tế khẳng định: **InspecSafe-V1 KHÔNG PHẢI là bộ dữ liệu chú thích triệt để**.
   - *Bằng chứng:* Nhiều ảnh phân xưởng chứa rất nhiều vật thể nền có thật (như bóng đèn, công tắc, thanh ray, đường ống thứ cấp, sàn gạch, cửa sổ, vết ố nhỏ) nhưng annotator chỉ chọn lọc vẽ một số đối tượng tiêu biểu.
   - Điển hình tại Mục 10: Có 12 mẫu có vết dầu/nước tràn rõ ràng trong ảnh và được khẳng định trong TXT, nhưng annotator không vẽ đa giác `Liquid`; có 5 mẫu có khói rõ ràng nhưng không vẽ đa giác `Smoke`.
3. **Kết luận khoa học:**
   - Nếu áp dụng quy tắc cơ học: *"Mô hình nhắc đến nhãn không có trong JSON = Ảo giác"* trên toàn bộ dataset, SafeShift sẽ phạm sai lầm phương pháp luận nghiêm trọng: **Trừng phạt mô hình VLM vì phát hiện đúng các vật thể có thật nhưng annotator bỏ sót**.
   - Do đó: **SafeShift KHÔNG triển khai chỉ số Object Hallucination Rate trên toàn bộ dataset**.
   - *Hướng thay thế khả thi (để W2.4 xem xét):* Chỉ đo lường ảo giác trong phạm vi một từ điển đóng các vật thể cấm nghiêm ngặt (`closed critical vocabulary`, ví dụ nhắc đến `Open Flame` hoặc `Cigarette` trong ảnh Normal), hoặc đánh giá trên một tập con nhỏ được kiểm tra thủ công (`manually verified subset`).

---

## 16. Giới hạn của Hiện tượng "Đúng Đáp án, Sai Lý do" (Correct-Answer-Wrong-Reason Limitation)

SafeShift tái khẳng định giới hạn phương pháp luận đã được khóa tại DEC-W2-D1-001:

1. Khi mô hình dự đoán chính xác cấp độ an toàn (`Correct Safety Prediction`) nhưng hộp bao dự đoán không trùng khớp với đa giác đối tượng (`Grounding Miss`):
   - Tuyệt đối **KHÔNG ĐƯỢC TỰ ĐỘNG KẾT LUẬN** rằng mô hình rơi vào trạng thái *"Đúng Đáp án nhưng Sai Lý do"* (`Correct Answer, Wrong Reason`).
2. **Lý do phương pháp luận:**
   - Chú thích hiện có trong JSON chỉ là **Đa giác Phân vùng Đối tượng (`Object Instance Polygons`)**, hoàn toàn không phải là **Vùng Lý do Ra Quyết định của Con người (`Human Rationale Ground Truth`)**.
   - Một mô hình có thể nhận diện đúng nguy cơ dựa vào ngữ cảnh xung quanh (ví dụ: nhìn thấy chiếc bàn làm việc công nhân để suy ra hành vi hút thuốc gần đó, hoặc nhìn thấy vũng ướt phản chiếu ánh sáng thay vì khoanh đúng trung tâm vũng dầu).
3. **Thuật ngữ chuẩn mực bắt buộc sử dụng:**
   - Trong khuôn khổ dữ liệu hiện tại, hiện tượng này bắt buộc phải được gọi chính xác là:  
     **"Sự không nhất quán giữa phân loại và bám bằng chứng đối tượng" (`Classification-Grounding Inconsistency relative to available object-support annotation`)**.
   - Thuật ngữ *"Sai lý do"* (`Wrong Reason`) chỉ có giá trị khoa học nếu có nhãn chuẩn vùng lý do con người (kết quả tiềm năng từ D7).

---

## 17. Phân tích Chiến dịch Gán nhãn Vùng Lý do D7 (D7 Rationale-Annotation Options)

SafeShift xem xét ba phương án giải quyết bài toán nhãn lý do của con người:

### Phương án D7-A: Không tạo nhãn mới trong giai đoạn Seminar (No New Annotation)
- Sử dụng nguyên trạng 100% dữ liệu gốc của InspecSafe-V1.
- Khai thác tối đa phân tầng Direct-Support (721 mẫu / 781 atoms) và Weak-Proxy (947 atoms).
- Báo cáo rõ ràng các giới hạn dữ liệu trong bài báo khoa học.
- *Đánh giá:* Tuyệt đối an toàn về tiến độ 8 tuần; không rủi ro về tính chủ quan của người gán nhãn sinh viên; tuân thủ hoàn hảo tinh thần của một benchmark kiểm toán độc lập.

### Phương án D7-B: Tạo khoảng 100 hộp bao lý do (100-Sample Rationale Campaign)
- Chọn lọc 100 mẫu Anomaly đại diện theo phân tầng có phương pháp (bao phủ 5 miền, các hazard strata và các ca yếu/thiếu nhãn như cửa mở).
- Nhóm nghiên cứu SafeShift tự vẽ hộp bao vùng lý do giải thích an toàn (`Human Rationale Boxes`).
- *Đánh giá:* Tạo thêm giá trị nhỏ cho việc đo lường "Wrong Reason" trên 100 mẫu; tuy nhiên đối mặt rủi ro phương pháp luận lớn: Nhãn do sinh viên tự gán thiếu chứng nhận chuyên gia an toàn công nghiệp (`lack of safety domain certification`), dễ bị hội đồng phản biện nghi vấn về tính chủ quan và tính chuẩn mực.

### Phương án D7-C: Tạo tập con nhỏ 50–100 mẫu có kiểm định kép (Double-Annotated Subset)
- Tương tự D7-B nhưng áp dụng quy trình gán nhãn chéo độc lập bởi 2 người (`double annotation`), đo lường độ đồng thuận liên gán nhãn (Inter-Annotator Agreement — Cohen's $\kappa$ hoặc Box IoU agreement), và có trọng tài giải quyết bất đồng.
- *Đánh giá:* Đảm bảo tính khoa học cao hơn D7-B; tuy nhiên tiêu tốn chi phí thời gian đáng kể trong giai đoạn W2–W3, có nguy cơ làm chậm tiến độ thực thi baseline của Seminar.

---

## 18. Ma trận Quyết định D4 & D7 (Decision Matrices)

### 18.1 Ma trận Quyết định D4 — Giao diện Đầu ra Grounding

| Tiêu chí Đánh giá | D4-A: Text Bounding Box | D4-B: Pointing Point | D4-C: Polygon / Mask | D4-D: Attention / Heatmap |
|---|:---:|:---:|:---:|:---:|
| **Hỗ trợ trên VLM thương mại (Commercial APIs)** | **RẤT CAO** (Native / Promptable) | CAO | THẤP | **KHÔNG HỖ TRỢ (0%)** |
| **Hỗ trợ trên VLM mã nguồn mở (Open VLMs)** | **RẤT CAO** (Chuẩn công nghiệp) | CAO | TRUNG BÌNH | TRUNG BÌNH (Cần can thiệp code) |
| **Tính so sánh cùng Prompt (Prompt Comparability)** | **XUẤT SẮC** (Dùng chung cấu trúc) | TỐT | KÉM (Token tràn lan) | **KHÔNG KHẢ THI** |
| **Khả năng parse tự động (Parseability)** | **CAO** (Regex cấu trúc tốt) | RẤT CAO | RẤT KÉM (Dễ lỗi JSON/cú pháp) | N/A |
| **Tương thích với Polygon GT có sẵn** | **TỐT** (Derive chuẩn xác sang BBox) | TRUNG BÌNH (Chỉ lấy điểm tâm) | **XUẤT SẮC** (Cùng định dạng) | KÉM (Cần ngưỡng hóa heuristic) |
| **Lượng thông tin không gian giữ lại** | **ĐẦY ĐỦ** (Vị trí, kích thước, tỷ lệ) | THIẾU (Mất quy mô) | **HOÀN HẢO** (Biên đối tượng) | MƠ HỒ (Phụ thuộc ngưỡng) |
| **Tính tái lập thực nghiệm (Reproducibility)** | **RẤT CAO** (Tất định) | RẤT CAO | TRUNG BÌNH | KÉM (Khác biệt kiến trúc) |
| **Gánh nặng triển khai (Implementation Burden)** | **THẤP** (Chuẩn hóa nhẹ) | RẤT THẤP | RẤT CAO | RẤT CAO (Bế tắc trên API) |

> **Nhận định ma trận D4:** **Phương án D4-A (Textual Normalized Bounding Box)** vượt trội áp đảo trên 7/8 tiêu chí thực tế, là lựa chọn khả thi và khoa học duy nhất để benchmark công bằng giữa các mô hình thương mại và mô hình mở.

### 18.2 Ma trận Quyết định D7 — Chiến dịch Gán nhãn Rationale Bổ sung

| Tiêu chí Đánh giá | D7-A: Không tạo nhãn mới | D7-B: Gán nhãn 100 mẫu đơn lẻ | D7-C: Tập nhỏ 50–100 mẫu kiểm định kép |
|---|:---:|:---:|:---:|
| **Giá trị khoa học cho Seminar 8 tuần** | **CHUẨN MỰC** (Khách quan, trung thực với benchmark) | TRUNG BÌNH (Bị nghi vấn chủ quan) | KHÁ (Có độ đo đồng thuận $\kappa$) |
| **Chi phí thời gian & Nỗ lực** | **TỐI ƯU (0 giờ làm nhãn)** | ĐÁNG KỂ (~20–30 giờ) | **RẤT LỚN (~40–60 giờ)** |
| **Rủi ro tính chủ quan (Subjectivity Risk)** | **KHÔNG CÓ (0%)** | **RẤT CAO** (Ý kiến cá nhân) | TRUNG BÌNH (Đã kiểm soát qua 2 người) |
| **Yêu cầu chứng nhận chuyên môn an toàn** | Không áp dụng | CẦN THIẾT nhưng không có | CẦN THIẾT nhưng không có |
| **Mức độ phù hợp với tiến độ Seminar 8 tuần** | **HOÀN TOÀN PHÙ HỢP (Kịp W3 baseline)** | NGUY CƠ TRỄ TIẾN ĐỘ | **NGUY CƠ CAO GÂY VỠ TIẾN ĐỘ** |
| **Giá trị mở rộng cho Luận văn (Thesis)** | Nền tảng kiểm toán vững chắc | Bổ sung nhỏ | **RẤT CÓ GIÁ TRỊ MỞ RỘNG** |

> **Nhận định ma trận D7:** Đối với khuôn khổ Seminar 8 tuần, **Phương án D7-A** là lựa chọn an toàn và vững chắc nhất về phương pháp luận. Việc gán nhãn rationale chuẩn mực theo D7-C nên được bảo lưu như một đóng góp mở rộng tiềm năng cho giai đoạn Luận văn tốt nghiệp (`Thesis Extension`).

---

## 19. Các Đề xuất Sơ bộ (Preliminary Recommendations — Proposed, Not Approved)

Căn cứ trên toàn bộ bằng chứng thực nghiệm của W2.3, nhóm nghiên cứu đưa ra 3 khuyến nghị sơ bộ:

### Khuyến nghị cho D4 (Model Grounding Output Interface)
- **Đề xuất lựa chọn Phương án D4-A:** Chuẩn hóa giao diện đầu ra định vị của mô hình là **Hộp bao tọa độ chuẩn hóa dạng văn bản (`Textual Normalized Bounding Box`)**, quy ước theo chuẩn `[ymin, xmin, ymax, xmax]` hoặc `[x1, y1, x2, y2]` trong thang đo chuẩn hóa $[0, 1000]$.
- **Nguyên tắc hai lớp dữ liệu:** Bắt buộc lưu trữ nguyên văn Raw Model Response trước khi parse; bản ghi Canonical Grounding Record được trích xuất bằng bộ parser tất định.
- **Chính sách phân tầng năng lực (Capability-Aware Policy B):**
  - Benchmark Phân loại An toàn (`Classification Benchmark`): Đánh giá trên toàn bộ các mô hình VLM tham gia thử nghiệm.
  - Benchmark Định vị Bằng chứng (`Spatial Grounding Benchmark`): Đánh giá trên các mô hình/giao diện thực sự hỗ trợ đầu ra định vị không gian, sử dụng cùng một cấu trúc prompt và canonical interface. Mô hình không có năng lực xuất tọa độ sẽ được ghi nhận rõ ràng trong báo cáo năng lực, không ép buộc dẫn đến lỗi cú pháp giả tạo, và tuyệt đối không sửa đổi nội dung ngữ nghĩa của câu prompt để "cứu" mô hình yếu.

### Khuyến nghị cho D6 (Full Direct-Support Census)
- **Phê chuẩn Hệ phân loại 12 Nguy cơ Nguyên tử (`12 Hazard Atoms`)** đã được kiểm chứng bao phủ 100% dữ liệu Anomaly.
- **Phê chuẩn việc phân định rạch ròi:** Sample-level counts ($N=1.000$) và Hazard-atom counts ($N=1.788$).
- **Phê chuẩn quy mô các tập con thực nghiệm:**
  - *Direct-Support Sample Pool:* **721 mẫu** (gồm 367 mẫu `ALL_DIRECT`, 323 mẫu `MIXED_DIRECT_PROXY`, 31 mẫu có direct atom trong `HAS_UNSUPPORTED`).
  - *Direct Hazard Atoms:* **781 atoms**.
  - *Weak-Proxy Subset:* **251 mẫu** (`PROXY_ONLY`) / **947 hazard atoms**.
  - *Unsupported Subset:* **59 mẫu** (`HAS_UNSUPPORTED`) / **60 hazard atoms**.
- **Phê chuẩn Khung RQ3:** Báo cáo tách biệt hoàn toàn giữa RQ3-A (Direct Object-Support) và RQ3-B (Weak Proxy).

### Khuyến nghị cho D7 (Optional Rationale Annotation Campaign)
- **Đề xuất lựa chọn Phương án D7-A cho giai đoạn Seminar:** Không triển khai chiến dịch tự gán nhãn rationale mới trong giai đoạn 8 tuần này.
- Tập trung nguồn lực thực hiện chuẩn xác, nghiêm ngặt các đánh giá trên 721 mẫu Direct-Support và 251 mẫu Weak-Proxy.
- Bảo lưu phương án D7-C (chiến dịch gán nhãn kép có chứng nhận chuyên gia) làm hướng phát triển trọng tâm cho Luận văn tốt nghiệp sau này.

---

## 20. Rủi ro và Giới hạn Phương pháp luận (Risks and Limitations)

1. **Rủi ro Đồng xuất hiện Đa nguy cơ (Multi-Hazard Confounding):** 323 mẫu thuộc diện `MIXED_DIRECT_PROXY` chứa đồng thời nguy cơ trực tiếp và vi phạm PPE. Khi mô hình dự đoán trúng hộp bao của vật thể trực tiếp (ví dụ `Mobile Phone`), rất khó khẳng định mô hình có đồng thời nhận thức được vi phạm thiếu găng tay hay không nếu không có cơ chế prompt bóc tách từng nguy cơ.
2. **Rủi ro Lệch miền trong Tầng Nguy cơ (Strata-Domain Confounding):** Nguy cơ tràn chất lỏng (`LIQUID_ON_GROUND`) tập trung 94% ở hóa chất dầu khí; xe thô sơ lấn làn (`NONMOTORIZED_VEHICLE`) tập trung 100% ở hầm. Hiện tượng này gắn chặt nguy cơ với bối cảnh thị giác của từng miền cụ thể, gây khó khăn cho việc phân định rạch ròi giữa khả năng khái quát hóa nguy cơ và khả năng nhận diện miền của VLM.
3. **Giới hạn của Bounding Box phái sinh:** Việc derive BBox từ Polygon làm tăng diện tích vùng chấp nhận (đặc biệt với các vật thể dài, nghiêng như đường ống, hoặc tư thế người nằm co). Cần thiết lập ngưỡng đánh giá chặt chẽ tại W2.4 để tránh dương tính giả do diện tích hộp bao quá lớn.
4. **Giới hạn của Miền Luyện kim (`metallurgy`):** Chỉ có 9 mẫu Anomaly với 25 hazard atoms; 8/9 mẫu có văn bản mô tả dầu khí. Mọi kết luận grounding trên miền luyện kim chỉ mang tính mô tả định tính cục bộ, hoàn toàn không đủ độ tin cậy thống kê.

---

## 21. Các câu hỏi cần xin ý kiến phê duyệt (Questions Requiring Approval)

Nhằm chuẩn bị phê duyệt dứt điểm các quyết định trong tuần W2, các câu hỏi sau được trình lên Research Lead:

### Nhóm câu hỏi sẵn sàng phê duyệt cho Quyết định D4:
1. *Research Lead có phê chuẩn **Phương án D4-A (Textual Normalized Bounding Box)** làm giao diện đầu ra bám bằng chứng chuẩn hóa chính thức của SafeShift không?*
2. *Research Lead có chấp thuận nguyên tắc chuẩn hóa tọa độ về thang đo tương đối $[0, 1000]$ (hoặc $[0.0, 1.0]$) độc lập với độ phân giải gốc của ảnh không?*
3. *Research Lead có phê chuẩn quy trình bắt buộc lưu trữ nguyên văn **Raw Model Response** trước khi bóc tách thành **Canonical Parsed Record** không?*
4. *Research Lead có phê chuẩn **Chính sách phân tầng năng lực Policy B** (Classification benchmark cho mọi mô hình; Grounding benchmark chỉ cho các mô hình có năng lực xuất tọa độ trên cùng canonical prompt) không?*

### Nhóm câu hỏi sẵn sàng phê duyệt cho Quyết định D6:
1. *Research Lead có phê chuẩn **Hệ phân loại 12 Nguy cơ Nguyên tử (`Hazard Atom Taxonomy`)** và bảng ánh xạ nhãn đối tượng hỗ trợ tại Mục 5 & Mục 7 không?*
2. *Research Lead có chấp thuận định nghĩa và quy mô của **Direct-Support Sample Pool (721 mẫu)** đi kèm yêu cầu bắt buộc báo cáo chi tiết thành phần nội bộ (`ALL_DIRECT` 367, `MIXED_DIRECT_PROXY` 323, `HAS_UNSUPPORTED` 31) không?*
3. *Research Lead có phê chuẩn việc **phân tách độc lập kết quả thực nghiệm của RQ3** thành RQ3-A (Direct Object-Support) và RQ3-B (Weak Proxy qua `Person`) không?*
4. *Research Lead có phê chuẩn danh mục **7 Tầng Nguy cơ Ứng viên cho RQ2** tại Mục 11 không?*

### Nhóm câu hỏi sẵn sàng phê duyệt cho Quyết định D7:
1. *Research Lead có chấp thuận **Phương án D7-A (Không tạo nhãn rationale mới trong giai đoạn Seminar 8 tuần)** nhằm bảo toàn tính khách quan và tập trung nguồn lực tái lập baseline không?*
2. *Nếu muốn bổ sung nhãn rationale, Research Lead có yêu cầu bắt buộc phải thực hiện theo chuẩn gán nhãn kép D7-C hay chấp nhận tập con thí nghiệm nhỏ hơn?*

---

## 22. Nguồn gốc Bằng chứng Kiểm chứng (Evidence Sources)

Tất cả các kết luận và số liệu thống kê trong báo cáo này đều có thể truy vết và tái lập độc lập 100% dựa trên các nguồn tài liệu và artifact sau trong kho lưu trữ SafeShift:

1. **Kho lưu trữ Dữ liệu Gốc:**
   - `data/raw/InspecSafe-V1/{train,test}/DATA_PATH/{train,test}/Annotations/Anomaly_data/` (1.000 cặp tệp `.json` và `.txt`).
2. **Tài liệu Kiểm toán và Quyết định Nền tảng:**
   - [notes/w1_dataset_audit.md](w1_dataset_audit.md) — Báo cáo kiểm toán tổng thể dữ liệu Week 1.
   - [notes/dataset_schema.md](dataset_schema.md) — Đặc tả schema chi tiết và 24 mệnh đề mở đầu ngữ cảnh.
   - [notes/research_feasibility_audit.md](research_feasibility_audit.md) — Đánh giá tính khả thi nghiên cứu và kiểm định thực nghiệm trên 63 mẫu Anomaly.
   - [notes/distribution_imbalance_audit.md](distribution_imbalance_audit.md) — Kiểm toán phân bố mất cân bằng miền và nhãn.
   - [notes/w2_protocol_decision_brief.md](w2_protocol_decision_brief.md) — Báo cáo căn cứ quyết định D1.
   - [notes/w2_domain_split_decision_brief.md](w2_domain_split_decision_brief.md) — Báo cáo căn cứ quyết định D2 và D3.
   - [DECISIONS.md](../DECISIONS.md) — Nhật ký quyết định chính thức đã phê duyệt DEC-W2-D1-001, DEC-W2-D2-002, DEC-W2-D3-003.
3. **Mã nguồn và Artifact Phân tích Thực nghiệm Cục bộ:**
   - `safeshift/data/manifest.py` — Logic trích xuất cú pháp mở đầu và schema JSON.
   - `data/manifests/w2_grounding_census.json` — Bản ghi chi tiết 1.000 mẫu Anomaly và 1.788 hazard atoms (SHA-256: `cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`).
   - Mã nguồn kiểm kê thực chứng: `scratch/full_census_engine.py`.
