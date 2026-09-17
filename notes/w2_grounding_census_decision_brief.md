# W2.3 Grounding Scope & Hazard Census Decision Brief

- **Tài liệu:** Báo cáo căn cứ quyết định phạm vi bám bằng chứng và tổng điều tra nguy cơ (W2.3 Grounding Scope & Hazard Census Decision Brief)
- **Dự án:** SafeShift: Benchmarking Cross-Domain Generalization and Evidence Grounding in Vision-Language Models for Industrial Safety Assessment
- **Bộ dữ liệu:** InspecSafe-V1 (5.013 mẫu ảnh: 4.013 Normal, 1.000 Anomaly)
- **Trạng thái:** BÁO CÁO CĂN CỨ KỸ THUẬT (TECHNICAL EVIDENCE BRIEF) — ĐỀ XUẤT CHO D4, D6, D7 (CHƯA PHÊ DUYỆT)
- **Ngày lập:** 2026-09-17
- **Phiên bản:** 1.2.0 (Final Patched Edition)

---

## 1. Mục đích văn bản (Purpose)

Văn bản này thiết lập cơ sở thực chứng phương pháp luận độc lập và toàn diện cho giai đoạn Week 2.3 của dự án SafeShift, chuẩn bị căn cứ khoa học cho ba quyết định then chốt:

1. **Quyết định D4 — Giao diện đầu ra bám bằng chứng của mô hình (Model Grounding Output Interface):** Chuẩn hóa định dạng biểu diễn không gian nội bộ chuẩn mực (`Internal Canonical Representation`) mà mô hình thị giác-ngôn ngữ (VLM) cần được chuyển đổi về sau khi parse, nhằm đánh giá khả năng định vị bằng chứng nguy cơ một cách công bằng và có khả năng so sánh xuyên mô hình.
2. **Quyết định D6 — Tổng điều tra đầy đủ tập bất thường (Full Direct-Support Census):** Thực hiện cuộc tổng điều tra thực chứng trên 100% (1.000 / 1.000) mẫu Bất thường (`Anomaly_data`), bóc tách chi tiết ở cả cấp độ mẫu (`Sample-level`) và cấp độ nguy cơ nguyên tử (`Hazard-atom level`), xác minh chính xác quy mô các tập con có hỗ trợ thực thể trực tiếp (`Direct-Support`), hỗ trợ đại diện yếu (`Weak-Proxy`) và hoàn toàn chưa có nhãn không gian (`No-Current-Spatial-GT`).
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

## 4. Phương pháp tổng điều tra 1.000 mẫu Anomaly (Census Method & Reproducibility)

Để trả lời chính xác và minh bạch 100% cấu trúc nguy cơ của InspecSafe-V1, SafeShift thực hiện quy trình điều tra tất định, không dựa trên lấy mẫu ngẫu nhiên hay gán nhãn tự do bằng LLM:

- **Phạm vi điều tra:** Đúng **1.000 / 1.000 mẫu Anomaly** (749 mẫu thuộc `train`, 251 mẫu thuộc `test`).
- **Nguồn dữ liệu trích xuất:**
  - Tệp văn bản chú thích gốc (`.txt`): Khảo sát toàn văn mệnh đề nguy cơ.
  - Tệp chú thích hình học gốc (`.json`): Bóc tách 100% đa giác và nhãn danh mục trong trường `shapes[].label`.
  - Siêu dữ liệu đường dẫn đã audit: `folder_domain`, `safety_level`, `robot_platform`, `point_id`, `split`.
- **Hồ sơ Tái lập Cục bộ (Local Census Traceability & Provenance):**
  - **Môi trường:** Python 3.11.9 (thư viện chuẩn: `pathlib`, `json`, `re`, `collections`, `hashlib`), Windows 11 x64, workspace `d:\SafeShift`.
  - **Thời điểm thực thi:** `2026-09-17 03:55:00 UTC`.
  - **Lệnh thực thi:** `python scratch/full_census_engine.py`
  - **Dấu vân tay mật mã dữ liệu đầu vào (Input Cryptographic Fingerprint):**  
    `7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`  
    *(Lưu ý phương pháp luận: Đây là mã băm SHA-256 đã kiểm chứng tại W1 cho **toàn bộ 5.013 mẫu ảnh của bộ dữ liệu InspecSafe-V1**. Cuộc điều tra W2.3 lựa chọn tập con xác định tất định — `deterministic subset` — gồm đúng 1.000 mẫu Anomaly từ bộ dữ liệu có dấu vân tay này. Đây không phải là mã băm tính riêng cho tập con Anomaly — `not an Anomaly-only cryptographic hash`).*
  - **Mã nguồn script điều tra cục bộ:** `scratch/full_census_engine.py` (Mã băm SHA-256: `348860eabbe06c7908b3f4b198804033b3bd61917da4dbf8d6ec06e9cc4b5c03`).
  - **Artifact kết quả chi tiết cấp mẫu cục bộ:** `data/manifests/w2_grounding_census.json` (Dung lượng: 762.487 bytes, mã băm SHA-256: `cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`).
  - *Ghi chú bảo vệ dữ liệu:* Do script nằm trong thư mục scratch và artifact chứa bản ghi chi tiết từng mẫu, tài liệu này có **tính chất truy vết và có thể tái lập cục bộ thông qua mã băm của script và artifact đã ghi nhận (`traceable and locally reproducible with the recorded script/artifact hashes`)**. Bản thân artifact chi tiết không được commit vào Git repository theo đúng quy tắc bảo vệ dữ liệu thô/dẫn xuất lớn.
- **Quy trình bóc tách cú pháp văn bản tất định (Deterministic Text Decomposition):**
  1. *Khử mệnh đề mở đầu ngữ cảnh:* Đối chiếu với danh mục **24 mệnh đề mở đầu duy nhất** đã được kiểm toán toàn diện tại `notes/dataset_schema.md` (Mục 15). Kết quả: 1.000 / 1.000 mẫu khớp 100% mệnh đề mở đầu chuẩn mực (0 mẫu lỗi mở đầu).
  2. *Khử mệnh đề kết luận mức độ an toàn:* Nhận diện và loại bỏ các biến thể cú pháp kết luận cấp an toàn (`Therefore, the safety level is...`, `The safety level is...`, `are classified as Level One safety`). Toàn bộ 1.000 mẫu được bóc tách sạch sẽ phần thân nguy cơ cốt lõi (`hazard body clause`).
  3. *Số lượng mệnh đề không ánh xạ được (`Hazard-clause unmapped count`):* Đúng **0 mệnh đề** (100% hội tụ về 187 mệnh đề nguy cơ duy nhất và bao phủ bởi 12 atoms).
  4. *Số lượng ánh xạ hỗ trợ mơ hồ/chưa giải quyết (`Support-mapping ambiguous/unresolved count`):* Đúng **0 trường hợp** (theo bộ quy tắc ánh xạ tất định hiện tại — *0 according to current deterministic mapping rules*; điều này phản ánh tính nhất quán nội bộ của quy tắc, không có nghĩa hệ taxonomy là chân lý phổ quát tuyệt đối).

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

Khảo sát toàn bộ 187 mệnh đề nguy cơ duy nhất trên 1.000 mẫu Anomaly xác nhận hệ phân loại gồm đúng **12 Hazard Atoms**, giải thích trọn vẹn 100% mẫu mà không có bất kỳ trường hợp nào bị bỏ sót:

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

### 6.2 Phân biệt rạch ròi Hai Tập Mẫu Đánh giá và Giao thoa Tập hợp (Pool Overlap Analysis)

Hai tập mẫu đánh giá Direct-Support Pool và Weak-Proxy Pool **KHÔNG PHẢI LÀ HAI TẬP RỜI NHAU (`THEY ARE NOT DISJOINT`)**. Việc phân tích giao thoa giữa hai tập hợp là bắt buộc để tránh sai lầm thống kê:

1. **Direct-Support Sample Pool Candidate ($\ge 1$ Direct Atom):**
   - **Quy mô:** Đúng **721 mẫu ảnh (72,1%)**.
   - **Thành phần:** 367 `ALL_DIRECT` + 323 `MIXED_DIRECT_PROXY` + 31 mẫu có direct atom trong `HAS_UNSUPPORTED`.
2. **Weak-Proxy Sample Pool Candidate ($\ge 1$ Weak-Proxy Atom):**
   - **Quy mô:** Đúng **608 mẫu ảnh (60,8%)**.
   - **Thành phần:** 251 `PROXY_ONLY` + 323 `MIXED_DIRECT_PROXY` + 34 mẫu có proxy atom trong `HAS_UNSUPPORTED`.
3. **Phần Giao thoa giữa Hai Tập Mẫu (Intersection $N = 347$):**
   - Có chính xác **347 mẫu ảnh** thuộc đồng thời cả hai pool trên:
     $$\text{Intersection} = 323 (\text{MIXED\_DIRECT\_PROXY}) + 24 (\text{Direct + Proxy + Unsupported}) = \mathbf{347\text{ mẫu}}$$
4. **Đẳng thức Kiểm tra Toàn vẹn Tổng thể (Sanity Identity):**
   - Số mẫu có ít nhất một nguy cơ đánh giá được (Direct hoặc Weak-Proxy):
     $$\text{Pool}_{\text{Direct}} \cup \text{Pool}_{\text{Proxy}} = 721 + 608 - 347 = \mathbf{982\text{ mẫu}}$$
   - Số mẫu hoàn toàn không có ground truth không gian (`Unsupported Only`): đúng **18 mẫu** (1,8%).
   - Tổng thể mẫu Anomaly được giải thích trọn vẹn:
     $$982 + 18 = \mathbf{1.000\text{ mẫu}}$$

> [!CAUTION]
> **Cảnh báo tính cộng gộp:** **TUYỆT ĐỐI KHÔNG ĐƯỢC CỘNG $721 + 608$** để suy ra tổng số mẫu ảnh, vì phép cộng cơ học này sẽ đếm lặp 347 mẫu giao thoa. Ở cấp độ Nguy cơ Nguyên tử, các số lượng atom mới có tính cộng rời hoàn toàn: **781 Direct atoms + 947 Weak-Proxy atoms + 60 Unsupported atoms = 1.788 atoms**.

### 6.3 Tổng hợp ở cấp độ Nguy cơ Nguyên tử (Hazard-Atom Level Support Status)

Phân loại trạng thái hỗ trợ trên toàn bộ 1.788 hazard atoms:

| Trạng thái hỗ trợ của Atom | Bản chất phương pháp luận | Số lượng Atom (`Atom Count`) | Tỷ lệ phần trăm |
|---|---|:---:|:---:|
| **`WEAK_PROXY_SUPPORT`** | Không có chú thích trực tiếp cho phát biểu nguy cơ; chỉ có thể định vị qua đa giác thực thể đại diện (`Person` cho thiếu PPE, tư thế người ngã, xe thô sơ lấn làn). | **947** | **53,0%** |
| **`DIRECT_OBJECT_SUPPORT`** | Dataset chứa đa giác chú thích trực tiếp thực thể hỗ trợ cho phát biểu nguy cơ (`Mobile Phone`, `Cigarette`, `Open Flame`, `Smoke`, `Liquid`, `Oil`, `Plastic Bag`, `Bicycle`, ...). | **781** | **43,7%** |
| **`NO_CURRENT_SPATIAL_GT`** | Hoàn toàn không có đa giác nào trong tệp JSON hỗ trợ cho phát biểu nguy cơ (cửa tủ điện mở bất thường, hoặc các ca thiếu sót chú thích đối tượng). | **60** | **3,4%** |
| **Tổng cộng** | **Toàn bộ Hazard Atoms** | **1.788** | **100,0%** |

### 6.4 Bảng chéo: Hazard Atom $\times$ Trạng thái Hỗ trợ (Atom $\times$ Support Status)

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

### 6.5 Bảng chéo: Hazard Atom $\times$ Cấp độ An toàn (Atom $\times$ Safety Level)

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

### 6.6 Bảng chéo: Hazard Atom $\times$ Miền Thao tác Thư mục (Atom-Level Counts $\times$ Folder Domain)

*Lưu ý quan trọng:* Bảng dưới đây thể hiện **Số lượng theo Nguy cơ Nguyên tử (`Atom-level counts`)**, không phải số lượng mẫu ảnh:

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

### 6.7 Bảng chéo: Hazard Atom $\times$ Phân chia Gốc (Atom $\times$ Split)

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

---

## 7. Bảng ánh xạ nhãn đối tượng hỗ trợ (Object-Support Mapping Table)

Bảng đối chiếu minh bạch giữa phát biểu nguy cơ nguyên tử và các nhãn đối tượng hình học có sẵn trong tệp JSON:

| Hazard Atom | Nhãn đối tượng hỗ trợ ứng viên (`Candidate Object Labels`) | Loại hỗ trợ (`Support Type`) | Quy tắc ánh xạ tường minh (`Mapping Rule`) | Trường hợp biên & Điểm chưa giải quyết (`Ambiguities / Edge Cases`) | Số lượng Atom |
|---|---|:---:|---|---|:---:|
| `USE_MOBILE_PHONE` | `Mobile Phone` | DIRECT | Mẫu có đa giác nhãn `Mobile Phone`. | 165 mẫu có `Mobile Phone`. Có **2 mẫu** thiếu nhãn này (`002777` và `003015`), chỉ có `Person` $\rightarrow$ phân loại là `WEAK_PROXY_SUPPORT`. | 167 |
| `SMOKING` | `Cigarette` | DIRECT | Mẫu có đa giác nhãn `Cigarette`. | 118 mẫu có `Cigarette`. Có **2 mẫu** thiếu nhãn này (`002489` và `002765`), chỉ có `Person` $\rightarrow$ phân loại là `WEAK_PROXY_SUPPORT`. | 120 |
| `OPEN_FLAME` | `Open Flame` | DIRECT | Mẫu có đa giác nhãn `Open Flame`. | **117 / 117 mẫu (100%)** có đa giác `Open Flame`. Độ nhất quán tuyệt đối. | 117 |
| `SMOKE` | `Smoke` | DIRECT | Mẫu có đa giác nhãn `Smoke`. | 103 mẫu có `Smoke`. Có **5 mẫu** hoàn toàn thiếu nhãn `Smoke` trong JSON (`002846`, `002851`, `002871`, `002977`, `002330`) $\rightarrow$ `NO_CURRENT_SPATIAL_GT`. | 108 |
| `LIQUID_ON_GROUND` | `Liquid`, `Oil`, `Water Droplet` | DIRECT | Mẫu có đa giác nhãn `Liquid` (87) hoặc `Oil` (34) hoặc `Water Droplet` (1). | 122 mẫu có direct label. Có **12 mẫu** mô tả nước/dầu tràn nhưng hoàn toàn không có đa giác chất lỏng nào $\rightarrow$ `NO_CURRENT_SPATIAL_GT`. | 134 |
| `FOREIGN_OBJECT` | `Plastic Bag`, `Toilet Paper`, `Water Bottle`, `Cardboard Box`, `White Paper`, `Iron Barrel`, `Shovel`, `Iron Wire`, `Mineral Water`, `Paper Shell`, `Plastic Bottle` | DIRECT | Mẫu có ít nhất một đa giác đại diện cho dị vật/rác thải vật lý cụ thể. | 109 mẫu có direct object polygon (gồm rác sinh hoạt và dị vật công nghiệp). Có **6 mẫu** (`002564`, `002655`, `002410`, `002445`, `002446`, `002447`) hoàn toàn thiếu đa giác dị vật $\rightarrow$ `NO_CURRENT_SPATIAL_GT`. | 115 |
| `NONMOTORIZED_VEHICLE` | `Bicycle`, `Electric Vehicle`, `Tricycle` (Direct Vehicle Entity); `Person` (Weak Proxy) | DIRECT / PROXY | Mẫu có đa giác phương tiện thô sơ cụ thể (47 atoms) $\rightarrow$ DIRECT; mẫu chỉ có đa giác người điều khiển `Person` (54 atoms) $\rightarrow$ PROXY. | **Nguy cơ mang bản chất quan hệ/lấn làn (`relational / lane violation`). Đa giác xe hay người đều KHÔNG encode quan hệ vi phạm làn đường; tuy nhiên phương tiện là thực thể vật lý trực tiếp hiện hữu (`direct object/entity support`, không phải full relational grounding).** | 101 |
| `NO_HELMET` | `Person` | WEAK_PROXY | Mẫu vi phạm không đội mũ; dùng đa giác toàn thân `Person` làm vùng đại diện gián tiếp. | **229 / 229 mẫu (100%)** đều có đa giác `Person`. Hoàn toàn không có phân vùng vùng đầu (`Head`) hay vùng mũ bị thiếu. | 229 |
| `NO_GLOVES` | `Person` | WEAK_PROXY | Mẫu vi phạm không đeo găng; dùng đa giác toàn thân `Person` làm vùng đại diện gián tiếp. | 451 mẫu có `Person`. Có **2 mẫu** (`002893` và `002288`) hoàn toàn thiếu đa giác `Person` trong JSON $\rightarrow$ `NO_CURRENT_SPATIAL_GT`. Không có phân vùng bàn tay (`Hands`). | 453 |
| `NO_MASK` | `Person` | WEAK_PROXY | Mẫu vi phạm không đeo khẩu trang; dùng đa giác `Person` làm vùng đại diện gián tiếp. | 199 mẫu có `Person`. Có **1 mẫu** (`002288`) hoàn toàn thiếu đa giác `Person` trong JSON $\rightarrow$ `NO_CURRENT_SPATIAL_GT`. Không có phân vùng khuôn mặt (`Face`). | 200 |
| `PERSON_FALLEN` | `Person` | WEAK_PROXY | Mẫu có người nằm/ngã trên sàn; dùng đa giác `Person` làm vùng đại diện. | **10 / 10 mẫu (100%)** đều có đa giác `Person`. Đa giác chỉ khoanh người, không khoanh trạng thái ngã/bất tỉnh. | 10 |
| `DOOR_OPEN` | *Không có nhãn phù hợp* | NO_GT | Khẳng định cửa tủ mở bất thường. | Toàn bộ **34 / 34 mẫu (100%)** không có bất kỳ đa giác nào khoanh vùng cánh cửa tủ hay khe hở cửa bị mở $\rightarrow$ `NO_CURRENT_SPATIAL_GT`. 12 mẫu ở tunnel có nhãn `Distribution Box` nhưng không phản ánh trạng thái cửa mở. | 34 |

---

## 8. Làm rõ Ngữ nghĩa của Hỗ trợ Trực tiếp (Direct Object Support Semantics)

SafeShift xác lập định nghĩa phương pháp luận bắt buộc cho khái niệm `DIRECT_OBJECT_SUPPORT`:

> [!IMPORTANT]
> **Định nghĩa bắt buộc của `DIRECT_OBJECT_SUPPORT`:**  
> Thuật ngữ `DIRECT_OBJECT_SUPPORT` có nghĩa duy nhất là:  
> **"Bộ dữ liệu chứa một chú thích không gian cho một vật thể/thực thể trực tiếp hỗ trợ cho phát biểu nguy cơ (`Dataset contains a spatial annotation for an object/entity that directly supports the hazard claim`)."**  
> Thuật ngữ này **TUYỆT ĐỐI KHÔNG CÓ NGHĨA** là:
> - Đa giác đó chứng minh trọn vẹn mệnh đề nguy cơ (`polygon proves the complete hazard proposition`).
> - Đa giác đó là nhãn chuẩn về lý do của con người (`human rationale ground truth`).

### Minh chứng cụ thể từ dữ liệu thực tế:
1. **Trường hợp Hút thuốc (`SMOKING` $\rightarrow$ `Cigarette`):** Đa giác `Cigarette` định vị chính xác điếu thuốc lá. Tuy nhiên, bản thân đa giác điếu thuốc không tự chứng minh hành vi "đang hút" hay trạng thái đang cháy của điếu thuốc.
2. **Trường hợp Dùng điện thoại (`USE_MOBILE_PHONE` $\rightarrow$ `Mobile Phone`):** Đa giác `Mobile Phone` định vị chiếc điện thoại trên tay công nhân. Đa giác không trực tiếp mã hóa hành vi vi phạm quy tắc an toàn.
3. **Trường hợp Xe thô sơ lấn làn (`NONMOTORIZED_VEHICLE` $\rightarrow$ `Bicycle`/`Electric Vehicle`/`Tricycle`):** Có **47 hazard atoms** có đa giác phương tiện thô sơ cụ thể. Các đa giác này hỗ trợ định vị chính thực thể phương tiện (`direct object/entity support`). Tuy nhiên, **đa giác phương tiện hoàn toàn không mã hóa mối quan hệ không gian vi phạm làn đường (`does NOT encode lane-occupation relation`)**. Do đó, 47 atoms này là hỗ trợ thực thể trực tiếp, **KHÔNG PHẢI là full relational-hazard grounding**.
4. **Quy tắc diễn giải:** Tuyệt đối không được gọi **781 hazard atoms** hay **721 mẫu** thuộc Direct-Support Pool là "nhãn chuẩn lý do nguy cơ đầy đủ" (*Full Hazard Rationale Ground Truth*).

---

## 9. Phân tích Tập con Hỗ trợ Đại diện Yếu (Weak-Proxy Subset & Pool Analysis)

1. **Phân biệt hai khái niệm mẫu Weak-Proxy:**
   - **Tập mẫu Thuần túy Đại diện (`PROXY_ONLY samples`):** Đúng **251 mẫu ảnh (25,1% tổng Anomaly)**. Đây là các mẫu mà 100% các hazard claims chỉ có thể bám vào đa giác đại diện yếu `Person`.
   - **Tập mẫu Có Hỗ trợ Đại diện (`Weak-Proxy Sample Pool`):** Đúng **608 mẫu ảnh (60,8% tổng Anomaly)** sở hữu ít nhất một hazard atom thuộc diện `WEAK_PROXY_SUPPORT` (gồm 251 `PROXY_ONLY`, 323 `MIXED_DIRECT_PROXY`, và 34 mẫu `HAS_UNSUPPORTED` có chứa proxy atom).
   - **Tổng số Hazard Atoms Thuộc diện Weak Proxy:** Đúng **947 hazard atoms (53,0% tổng số atoms)**.
2. **Bản chất phương pháp luận của Weak Proxy:**
   - Đa giác `Person` bao trùm toàn bộ cơ thể người từ đầu đến chân.
   - Đối với vi phạm *"không đội mũ"* (`NO_HELMET`), vùng bằng chứng chân thực phải là vùng đầu trần (`bare head`).
   - Đối với vi phạm *"không đeo găng tay"* (`NO_GLOVES`), vùng bằng chứng chân thực phải là hai bàn tay trần (`bare hands`).
   - Nếu chấp nhận `Person` làm ground truth: Một mô hình VLM tập trung vào đôi ủng bảo hộ của công nhân nhưng nằm lọt trong hộp bao `Person` vẫn được thuật toán tính là "bám bằng chứng chính xác" ($IoU > \text{threshold}$).
   - Do đó, SafeShift **chỉ coi đây là Đại diện Yếu (`WEAK_PROXY_SUPPORT`)**, bắt buộc phải phân tách rạch ròi với `DIRECT_OBJECT_SUPPORT` trong mọi bảng báo cáo kết quả thực nghiệm của RQ3.

---

## 10. Các trường hợp Chưa có GT Không gian (Unsupported Cases Analysis)

Cuộc tổng điều tra D6 phát hiện chính xác **60 hazard atoms** nằm trong **59 mẫu ảnh** thuộc nhóm **`NO_CURRENT_SPATIAL_GT`** (hoàn toàn không có ground truth không gian):

1. **Nhóm Cửa tủ điện mở bất thường (`DOOR_OPEN`):**
   - Đúng **34 hazard atoms** (34 mẫu ảnh).
   - Kiểm tra trực tiếp trên 5.013 tệp JSON xác nhận: **Hoàn toàn không tồn tại bất kỳ nhãn nào tên `Cabinet Door Open` hay `Door`**.
   - Có 12 mẫu tại hầm (`tunnel`) có nhãn `Distribution Box`, nhưng đa giác chỉ khoanh bao quát cả chiếc tủ điện, hoàn toàn không chỉ định vị trí cánh cửa mở hay khe hở bất thường. 22 mẫu còn lại hoàn toàn không có bất kỳ đa giác nào liên quan đến tủ hay cửa $\rightarrow$ `DOOR_OPEN` hiện tại là **Unevaluable for Grounding**.
2. **Nhóm Thiếu sót Chú thích Chất lỏng (`Missing Liquid Annotation`):**
   - Đúng **12 hazard atoms** có khẳng định văn bản rõ ràng về dầu/nước tràn trên mặt đất (ví dụ: `oil_chemical-Level01-Wheeled-002745-001`, `002798-001`, `002872-001`), nhưng annotator gốc hoàn toàn quên không vẽ đa giác nhãn `Liquid` hay `Oil`.
3. **Nhóm Thiếu sót Chú thích Dị vật (`Missing Foreign Object Annotation`):**
   - Đúng **6 hazard atoms** mô tả dị vật trên băng chuyền than hoặc sứ cách điện (`002564-001`, `002655-001`, `002410-001`, `002445`–`002447`), nhưng JSON chỉ khoanh các thiết bị nền (`Switchgear`, `Bus Bar`, `Belt`, `Idler Roller`) mà không có đa giác dị vật.
4. **Nhóm Thiếu sót Chú thích Khói (`Missing Smoke Annotation`):**
   - Đúng **5 hazard atoms** mô tả có khói (`002846-001`, `002851-001`, `002871-001`, `002977-001`, `002330-001`), nhưng JSON hoàn toàn thiếu nhãn `Smoke`.
5. **Nhóm Thiếu sót Chú thích Đối tượng Người (`Missing Person Annotation`):**
   - Đúng **3 hazard atoms** mô tả vi phạm PPE (`002893-001` và `002288-001`) nhưng JSON hoàn toàn không có cả đa giác `Person`.
6. **Phân rã 59 mẫu `HAS_UNSUPPORTED`:**
   - 24 mẫu chứa đồng thời Direct + Proxy + Unsupported.
   - 7 mẫu chứa Direct + Unsupported (không có Proxy).
   - 10 mẫu chứa Proxy + Unsupported (không có Direct).
   - 18 mẫu thuần túy Unsupported (`Unsupported Only`, không có Direct, không có Proxy).

---

## 11. Các tầng nguy cơ gom nhóm ứng viên cho RQ2 (Candidate Grouped Hazard Strata)

Câu hỏi nghiên cứu RQ2 yêu cầu phân tích sự tập trung lỗi của mô hình VLM theo các phân tầng nguy cơ. Dựa trên 12 verified hazard atoms, SafeShift đề xuất **7 Phân tầng Nguy cơ Gom nhóm Ứng viên (`Candidate Grouped Hazard Strata`)**:

> [!WARNING]
> **Quy tắc diễn giải số lượng mẫu giữa các tầng:**  
> **Số lượng mẫu giữa các tầng nguy cơ KHÔNG CÓ TÍNH CỘNG GỘP (`Sample counts across strata are NOT additive`)**, bởi vì một mẫu ảnh đa nguy cơ (multi-hazard sample) có thể thuộc về đồng thời nhiều tầng nguy cơ khác nhau. Các con số phân bổ theo miền trong bảng dưới đây được tính ở **Cấp độ Nguy cơ Nguyên tử (`Atom-level counts`)**.

| Mã Tầng Nguy cơ Ứng viên | Thành phần Hazard Atoms cấu thành | Số mẫu liên quan (`Sample N`) | Số lượng Atom (`Atom N`) | Phân bố theo Miền (`Atom-level Counts`) | Phân bố Cấp An toàn | Trạng thái Hỗ trợ chính | Yếu tố gây nhiễu lớn (`Major Confounders`) | Đánh giá Mức độ Phù hợp cho RQ2 |
|---|---|:---:|:---:|---|---|:---:|---|:---:|
| **Strata A: `FIRE_AND_SMOKE`** | `OPEN_FLAME` + `SMOKE` | 200 | 225 | `oil_chem` (110), `tunnel` (42), `power` (19), `coal_con` (53), `metallur` (1) | 100% Level01 (225) | DIRECT (97,8%) | Đi kèm vi phạm PPE trong các mẫu phức tạp. | **RẤT PHÙ HỢP (HIGHLY SUITABLE)**. Tín hiệu thị giác trực tiếp rõ ràng. |
| **Strata B: `PPE_ABSENCE`** | `NO_GLOVES` + `NO_HELMET` + `NO_MASK` | 545 | 882 | `coal_con` (297), `oil_chem` (264), `tunnel` (196), `power` (108), `metallur` (17) | Level01 (538), Level02 (334), Level03 (10) | WEAK_PROXY (99,7%) | Đa giác toàn thân `Person` gây thiên lệch diện tích lớn. | **RẤT PHÙ HỢP (HIGHLY SUITABLE)**. Phân tầng quy mô lớn nhất, đại diện cho an toàn lao động. |
| **Strata C: `UNAUTHORIZED_BEHAVIOR`** | `USE_MOBILE_PHONE` + `SMOKING` | 247 | 287 | `oil_chem` (124), `coal_con` (124), `tunnel` (16), `power` (17), `metallur` (6) | Level01 (216), Level02 (71) | DIRECT (98,6%) | Thường đồng xuất hiện với vi phạm không đeo găng tay. | **RẤT PHÙ HỢP (HIGHLY SUITABLE)**. Direct support rất cao (`Mobile Phone`, `Cigarette`). |
| **Strata D: `ENVIRONMENTAL_SLIP_HAZARD`** | `LIQUID_ON_GROUND` | 134 | 134 | `oil_chem` (126), `tunnel` (4), `coal_con` (3), `metallur` (1), `power` (0) | Level01 (73), Level02 (55), Level03 (6) | DIRECT (91,0%) | **Nhiễu miền nghiêm trọng (Domain Confounder):** 94,0% atom nằm ở hóa chất dầu khí. | **PHÙ HỢP CÓ ĐIỀU KIỆN (CONDITIONALLY SUITABLE)**. Cần kiểm soát biến miền khi phân tích. |
| **Strata E: `OBSTRUCTION_AND_FOREIGN_OBJECT`** | `FOREIGN_OBJECT` + `NONMOTORIZED_VEHICLE` | 211 | 216 | `tunnel` (135), `coal_con` (64), `power` (17) | Level01 (141), Level02 (75) | DIRECT (72,2%) / PROXY (25,0%) | Nonmotorized vehicle tập trung 100% tại tunnel. | **PHÙ HỢP (SUITABLE)**. Cần tách rã giữa dị vật tĩnh và phương tiện giao thông. |
| **Strata F: `EQUIPMENT_STATE_ANOMALY`** | `DOOR_OPEN` | 34 | 34 | `tunnel` (30), `oil_chem` (3), `power` (1) | Level01 (8), Level02 (26) | NO_CURRENT_SPATIAL_GT (100%) | **Hoàn toàn không có ground truth không gian.** | **CHỈ PHÙ HỢP CHO PHÂN LOẠI (Classification Only)**, loại khỏi Grounding. |
| **Strata G: `PERSONNEL_FALLEN`** | `PERSON_FALLEN` | 10 | 10 | `power` (8), `coal_con` (2) | 100% Level01 (10) | WEAK_PROXY (100%) | Cỡ mẫu quá nhỏ ($N=10$), thiếu lực thống kê. | **KHÔNG KHUYẾN NGHỊ LÀM TẦNG ĐỘC LẬP (NOT RECOMMENDED ALONE)**. |

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
  - Cấp độ Mẫu: Thực hiện trên **251 mẫu thuần túy đại diện (`PROXY_ONLY`)**, hoặc mở rộng sang **608 mẫu thuộc `Weak-Proxy Sample Pool`** khi đánh giá phân rã theo từng hazard atom đại diện.
  - Cấp độ Hazard Atom: Thực hiện trên **947 hazard atoms** (chủ yếu là `NO_GLOVES`, `NO_HELMET`, `NO_MASK`, `PERSON_FALLEN` và xe thô sơ không có nhãn xe).
- **Nguyên tắc đối sánh:** Hộp bao dự đoán của mô hình được đối chiếu với hộp bao của đối tượng đại diện **`Person`**.
- **Quy tắc báo cáo bắt buộc:** Kết quả của RQ3-A và RQ3-B **PHẢI ĐƯỢC BÁO CÁO TÁCH BIỆT TRONG HAI CỘT / BẢNG RIÊNG**. Tuyệt đối không tính điểm trung bình gộp (`pooled average`) giữa Direct và Proxy thành một chỉ số duy nhất mà không ghi chú.
- **Về Full Hazard Rationale Grounding:** Vẫn tiếp tục được xác định là **NOT CURRENTLY FEASIBLE** trên InspecSafe-V1 nếu không triển khai chiến dịch gán nhãn D7.

---

## 13. Phân tích các lựa chọn Giao diện Đầu ra Grounding D4 (D4 Output-Interface Options)

Đánh giá 4 phương án biểu diễn đầu ra bám bằng chứng của mô hình VLM:

### Phương án D4-A: Textual Normalized Bounding Box (Ứng viên Giao diện Chuẩn hóa)
- *Lý do được đề xuất làm ứng viên chuẩn mực (`Canonical Interface Candidate`):*
  - Định dạng gọn gàng (`compact`), dễ biểu diễn trong chuỗi sinh văn bản của VLM.
  - Khả năng parse tự động (`parseable`) cao và ổn định bằng biểu thức chính quy.
  - Tương thích tự nhiên với ground truth hình học có sẵn: Đa giác có thể suy biến toán học tất định sang hộp bao (`GT polygons can derive boxes`).
  - Lưu giữ đầy đủ thông tin không gian hơn điểm tâm (`retains more spatial information than a point`: vị trí, diện tích, tỷ lệ khung hình).
- *Làm rõ về năng lực thực tế của mô hình:*
  - Tài liệu chính thức của Google Gemini hiện tại có công bố chính thức hỗ trợ xuất normalized bounding box. Tuy nhiên, SafeShift **không ngoại suy điều này cho mọi mô hình VLM thương mại khác**.
  - Textual Bounding Box được đề xuất như một **ứng viên giao diện chuẩn hóa (`canonical interface candidate`)**, **KHÔNG PHẢI là năng lực được bảo đảm (`not a guaranteed capability`)** trên toàn bộ các mô hình. Năng lực định vị thực tế của từng mô hình/phiên bản/giao diện (`actual model localization capability`) bắt buộc phải được kiểm chứng thực nghiệm tại bước **W2.5**.

### Phương án D4-B: Pointing Point (Điểm trỏ tâm / Tọa độ điểm)
- *Định dạng chuẩn:* Mô hình xuất một cặp tọa độ duy nhất: `[x, y]`.
- *Ưu điểm:* Cú pháp cực kỳ ngắn gọn; phù hợp với độ đo Pointing Game.
- *Hạn chế:* Bị mất hoàn toàn thông tin về quy mô kích thước (scale) và ranh giới không gian của đối tượng; không thể tính toán chỉ số giao thoa diện tích (IoU).

### Phương án D4-C: Polygon / Segmentation Mask (Đa giác phân vùng / Mặt nạ nhị phân)
- *Định dạng chuẩn:* Mô hình xuất danh sách các điểm tọa độ đa giác khép kín `[[x1, y1], [x2, y2], ...]` hoặc chuỗi mã hóa RLE.
- *Ưu điểm:* Khớp 1:1 với định dạng đa giác gốc của bộ dữ liệu InspecSafe-V1.
- *Hạn chế:* Chi phí token khổng lồ; tỷ lệ parse thất bại (cú pháp lỗi, đa giác tự cắt) rất cao trên các mô hình tổng quát.

### Phương án D4-D: Attention Map / Visual Heatmap (Bản đồ chú ý thị giác / Bản đồ nhiệt)
- *Định dạng chuẩn:* Trích xuất ma trận trọng số chú ý (Cross-attention weights) từ các tầng transformer của mô hình.
- *Hạn chế chí mạng:*
  - **Nhìn chung không hỗ trợ trên các giao diện Closed-API ứng viên (`Generally unavailable / not exposed for candidate closed-API interfaces`):** Các nhà cung cấp API thương mại (OpenAI, Google Gemini, Anthropic) nhìn chung không expose attention maps; hiện trạng này bắt buộc phải được xác minh theo từng provider/phiên bản cụ thể tại bước **W2.5**.
  - **Không phản ánh suy luận nhân quả:** Nhiều nghiên cứu đã chứng minh attention weights không đồng nhất với giải thích nhân quả. Khác biệt kiến trúc giữa các mô hình triệt tiêu tính so sánh công bằng.

---

## 14. Định dạng Chuẩn hóa Nội bộ và Bảo toàn Đầu ra Thô (Canonical Schema & Raw Preservation)

SafeShift thiết lập quy trình xử lý dữ liệu đầu ra hai lớp với định dạng chuẩn hóa nội bộ duy nhất:

1. **Lớp 1: Raw Model Response (Bảo toàn Phản hồi Thô Nguyên gốc):**
   - **Bắt buộc lưu trữ nguyên văn 100% chuỗi văn bản trả về của mô hình**, không ghi đè hay cắt xén.
   - Đi kèm siêu dữ liệu bắt buộc: `sample_id`, `run_id`, `model_name`, `model_version`, `prompt_template_id`, `decoding_parameters` (temperature, top_p, seed), `timestamp_utc`.
2. **Lớp 2: Internal Canonical Grounding Representation (Định dạng Chuẩn hóa Nội bộ Duy nhất):**
   - Đề xuất một định dạng chuẩn hóa nội bộ duy nhất cho mọi phép tính toán hình học:
     $$\mathbf{b}_{\text{canonical}} = [x_{\min}, y_{\min}, x_{\max}, y_{\max}] \quad \text{với} \quad x_{\min}, y_{\min}, x_{\max}, y_{\max} \in [0.0, 1.0]$$
   - *Nguyên tắc chuyển đổi của Adapter:*
     - Định dạng gốc của mô hình có thể khác nhau (ví dụ: mô hình xuất theo quy ước `[ymin, xmin, ymax, xmax]` trong thang `[0, 1000]`).
     - Bộ adapter/parser có trách nhiệm chuyển đổi tất định từ raw format của từng mô hình về định dạng chuẩn hóa nội bộ `[x_min, y_min, x_max, y_max]` trong thang `[0.0, 1.0]`.
     - Raw format được bảo lưu nguyên vẹn; phê duyệt D4 sau này sẽ phê chuẩn canonical internal format này chứ không giả định native format của các mô hình là giống nhau.
3. **Chính sách Phân tầng Năng lực (Capability-Aware Policy B Qualification):**
   - *Classification Benchmark:* Chạy trên toàn bộ danh sách mô hình tham gia thử nghiệm.
   - *Spatial Grounding Benchmark:* Chỉ chạy trên tập con các mô hình/giao diện thực sự có năng lực xuất tọa độ định vị (`grounding-capable model subset`).
   - *Quy tắc đối sánh công bằng:*
     - Danh sách các mô hình tham gia grounding track phải được báo cáo tường minh.
     - Tuyệt đối **không so sánh thứ hạng grounding (`grounding rank`) với các mô hình không tham gia grounding track**.
     - Sử dụng **cùng một cấu trúc prompt ngữ nghĩa (`same semantic grounding prompt`)** cho mọi mô hình trong grounding track, tuyệt đối không tùy biến nội dung prompt để "cứu" từng mô hình cụ thể.
     - Tiêu chuẩn xác định năng lực (eligibility) sẽ được khảo sát và xác minh tại bước **W2.5**.

---

## 15. Tính khả thi của Chỉ số Ảo giác Đối tượng (Object Hallucination Metric Feasibility)

Đánh giá tính khả thi thực chứng về việc đo lường Ảo giác Đối tượng (`Object Hallucination Rate`):

1. **Giới hạn thực tế của Annotation Completeness:**
   - Để đo lường khách quan tỷ lệ ảo giác trên toàn dataset (mô hình nhắc đến vật thể $X$, nếu $X \notin \text{Annotations}$ thì kết luận mô hình bị ảo giác), bộ dữ liệu bắt buộc phải đạt điều kiện **Chú thích đầy đủ triệt để mọi đối tượng (`Exhaustive Object Annotation`)**.
   - Kiểm toán thực tế khẳng định: **InspecSafe-V1 KHÔNG PHẢI là bộ dữ liệu chú thích triệt để**. Có nhiều trường hợp vật thể có thật trong ảnh nhưng annotator không vẽ polygon (ví dụ: 12 mẫu nước/dầu tràn thiếu nhãn `Liquid`/`Oil`, 5 mẫu khói thiếu nhãn `Smoke`).
   - **Quy tắc phương pháp luận:** Tuyệt đối không được suy diễn rằng *"nhãn thiếu trong JSON đồng nghĩa với vật thể không tồn tại trong ảnh"* (`missing JSON label does NOT imply object is absent`).
2. **Kết luận về chỉ số trên toàn dataset:**
   - Chỉ số Object Hallucination Rate trên toàn bộ dataset là **NOT CURRENTLY VALID** với bộ chú thích hiện tại.
3. **Điều kiện để triển khai phương án thay thế (Alternative Requirements):**
   - Việc chỉ giới hạn trong một từ điển đóng (`closed vocabulary ALONE`) là **CHƯA ĐỦ**.
   - Muốn đo lường ảo giác một cách khách quan và khoa học, bắt buộc phải có:
     - **Từ điển đóng các thực thể nguy cơ nghiêm ngặt (`Closed Critical Vocabulary`)** KẾT HỢP VỚI **Tập con kiểm tra thủ công đã xác minh sự tồn tại / vắng mặt (`Manually Verified Positive/Negative Subset`)**, HOẶC:
     - Một cuộc kiểm toán xác nhận độ đầy đủ chú thích (`Annotation Completeness Audit`) dành riêng cho tập từ điển đó.
   - Quyết định cuối cùng về việc có đưa chỉ số này vào giao thức hay không thuộc về bước **W2.4**.

---

## 16. Giới hạn của Hiện tượng "Đúng Đáp án, Sai Lý do" (Correct-Answer-Wrong-Reason Limitation)

SafeShift tái khẳng định giới hạn phương pháp luận đã được khóa tại DEC-W2-D1-001:

1. Khi mô hình dự đoán chính xác cấp độ an toàn (`Correct Safety Prediction`) nhưng hộp bao dự đoán không trùng khớp với đa giác đối tượng (`Grounding Miss`):
   - Tuyệt đối **KHÔNG ĐƯỢC TỰ ĐỘNG KẾT LUẬN** rằng mô hình rơi vào trạng thái *"Đúng Đáp án nhưng Sai Lý do"* (`Correct Answer, Wrong Reason`).
2. **Lý do phương pháp luận:**
   - Chú thích hiện có trong JSON chỉ là **Đa giác Phân vùng Thực thể Đối tượng (`Object Instance Polygons`)**, hoàn toàn không phải là **Vùng Lý do Ra Quyết định của Con người (`Human Rationale Ground Truth`)**.
   - Một mô hình có thể nhận diện đúng nguy cơ dựa vào ngữ cảnh xung quanh mà không cần khoanh đúng ranh giới của vật thể hỗ trợ.
3. **Thuật ngữ chuẩn mực bắt buộc sử dụng:**
   - Hiện tượng này bắt buộc phải được gọi chính xác là:  
     **"Sự không nhất quán giữa phân loại và bám bằng chứng đối tượng" (`Classification-Grounding Inconsistency relative to available object-support annotation`)**.
   - Thuật ngữ *"Sai lý do"* (`Wrong Reason`) chỉ có giá trị khoa học nếu có nhãn chuẩn vùng lý do con người (kết quả tiềm năng từ D7).

---

## 17. Phân tích Chiến dịch Gán nhãn Vùng Lý do D7 (D7 Rationale-Annotation Options)

SafeShift xem xét ba phương án giải quyết bài toán nhãn lý do của con người:

### Phương án D7-A: Không tạo nhãn mới trong giai đoạn Seminar (No New Annotation)
- Sử dụng nguyên trạng dữ liệu gốc của InspecSafe-V1.
- Khai thác tối đa phân tầng Direct-Support (721 mẫu / 781 atoms) và Weak-Proxy (608 mẫu / 947 atoms).
- Báo cáo rõ ràng các giới hạn dữ liệu trong bài báo khoa học.
- *Đánh giá:* Tuyệt đối an toàn về tiến độ 8 tuần; không làm phát sinh thêm tính chủ quan từ việc tự gán nhãn rationale mới; tuân thủ hoàn hảo tinh thần của một benchmark kiểm toán độc lập.

### Phương án D7-B: Tạo khoảng 100 hộp bao lý do đơn lẻ (100-Sample Rationale Campaign)
- Chọn lọc 100 mẫu Anomaly đại diện theo phân tầng có phương pháp. Nhóm nghiên cứu SafeShift tự vẽ hộp bao vùng lý do giải thích an toàn (`Human Rationale Boxes`).
- *Đánh giá:* Tạo thêm giá trị nhỏ cho việc đo lường "Wrong Reason" trên 100 mẫu; tuy nhiên đối mặt rủi ro phương pháp luận lớn do tính chủ quan cá nhân của người gán nhãn. Chi phí thời gian ước tính sơ bộ khoảng ~20–30 giờ *(lưu ý: đây là ước lượng kế hoạch sơ bộ, không phải số đo thực nghiệm — rough planning estimate, not empirically measured; không dùng làm bằng chứng khoa học)*.

### Phương án D7-C: Tạo tập con nhỏ 50–100 mẫu có kiểm định kép (Double-Annotated Subset)
- Tương tự D7-B nhưng áp dụng quy trình gán nhãn chéo độc lập bởi 2 người (`double annotation`), đo lường độ đồng thuận liên gán nhãn (Inter-Annotator Agreement — Cohen's $\kappa$ hoặc Box IoU agreement), và có trọng tài giải quyết bất đồng. Sự tham gia thẩm định của chuyên gia an toàn lao động (`domain-expert review`) là điều rất mong muốn nếu triển khai.
- *Đánh giá:* Đảm bảo tính khoa học cao hơn D7-B; tuy nhiên tiêu tốn chi phí thời gian đáng kể khoảng ~40–60 giờ *(ước lượng kế hoạch sơ bộ, không phải số đo thực nghiệm — rough planning estimate, not empirically measured)*, có nguy cơ làm chậm tiến độ thực thi baseline của Seminar.

---

## 18. Ma trận Quyết định D4 & D7 (Decision Matrices)

### 18.1 Ma trận Quyết định D4 — Giao diện Đầu ra Grounding

| Tiêu chí Đánh giá | D4-A: Text Bounding Box | D4-B: Pointing Point | D4-C: Polygon / Mask | D4-D: Attention / Heatmap |
|---|:---:|:---:|:---:|:---:|
| **Khả năng hỗ trợ trên VLM thương mại** | **KHẢ THI** (Gemini documents officially; cần test model khác tại W2.5) | KHẢ THI | HẠN CHẾ | **Nhìn chung không expose trên candidate closed APIs (cần verify tại W2.5)** |
| **Khả năng hỗ trợ trên VLM mã nguồn mở** | **PHỤ THUỘC TỪNG MÔ HÌNH (MODEL-DEPENDENT) — Cần verify tại W2.5** | CAO | TRUNG BÌNH | TRUNG BÌNH (Cần can thiệp code) |
| **Tính so sánh cùng Prompt (Prompt Comparability)** | **TỐT** (Dùng chung cấu trúc JSON/coords) | TỐT | KÉM (Token tràn lan) | **KHÔNG KHẢ THI** |
| **Khả năng parse tự động (Parseability)** | **CAO** (Regex cấu trúc tốt) | RẤT CAO | RẤT KÉM (Dễ lỗi JSON/cú pháp) | N/A |
| **Tương thích với Polygon GT có sẵn** | **TỐT** (Derive chuẩn xác sang BBox) | TRUNG BÌNH (Chỉ lấy điểm tâm) | **XUẤT SẮC** (Cùng định dạng) | KÉM (Cần ngưỡng hóa heuristic) |
| **Lượng thông tin không gian giữ lại** | **ĐẦY ĐỦ** (Vị trí, kích thước, tỷ lệ) | THIẾU (Mất quy mô) | **HOÀN HẢO** (Biên đối tượng) | MƠ HỒ (Phụ thuộc ngưỡng) |
| **Tính tái lập thực nghiệm (Reproducibility)** | **RẤT CAO** (Tất định) | RẤT CAO | TRUNG BÌNH | KÉM (Khác biệt kiến trúc) |
| **Gánh nặng triển khai (Implementation Burden)** | **THẤP** (Chuẩn hóa nhẹ) | RẤT THẤP | RẤT CAO | RẤT CAO (Bế tắc trên API) |

> **Nhận định ma trận D4:** **Phương án D4-A (Textual Normalized Bounding Box)** là ứng viên giao diện chuẩn hóa cân bằng và khoa học nhất (`canonical interface candidate`), không phải năng lực được bảo đảm của mọi mô hình.

### 18.2 Ma trận Quyết định D7 — Chiến dịch Gán nhãn Rationale Bổ sung

| Tiêu chí Đánh giá | D7-A: Không tạo nhãn mới | D7-B: Gán nhãn 100 mẫu đơn lẻ | D7-C: Tập nhỏ 50–100 mẫu kiểm định kép |
|---|:---:|:---:|:---:|
| **Giá trị khoa học cho Seminar 8 tuần** | **CHUẨN MỰC** (Trung thực với benchmark gốc) | TRUNG BÌNH (Rủi ro chủ quan) | KHÁ (Có kiểm soát qua độ đồng thuận) |
| **Chi phí thời gian & Nỗ lực (Rough planning estimate, not empirical)** | **TỐI ƯU (0 giờ làm nhãn)** | ĐÁNG KỂ (~20–30 giờ planning estimate) | **RẤT LỚN (~40–60 giờ planning estimate)** |
| **Tính chủ quan của nhãn mới** | **Không phát sinh thêm tính chủ quan gán nhãn** | **RẤT CAO** (Ý kiến cá nhân) | TRUNG BÌNH (Đã kiểm soát qua 2 người) |
| **Yêu cầu thẩm định chuyên gia an toàn** | Không áp dụng | Rất mong muốn nhưng khó khả thi | Rất mong muốn nhưng khó khả thi |
| **Mức độ phù hợp với tiến độ Seminar 8 tuần** | **HOÀN TOÀN PHÙ HỢP (Kịp W3 baseline)** | NGUY CƠ TRỄ TIẾN ĐỘ | **NGUY CƠ CAO GÂY VỠ TIẾN ĐỘ** |
| **Giá trị mở rộng cho Luận văn (Thesis)** | Nền tảng kiểm toán vững chắc | Bổ sung nhỏ | **RẤT CÓ GIÁ TRỊ MỞ RỘNG** |

> **Nhận định ma trận D7:** Đối với khuôn khổ Seminar 8 tuần, **Phương án D7-A** là lựa chọn an toàn và vững chắc nhất về phương pháp luận. Việc gán nhãn rationale chuẩn mực theo D7-C nên được bảo lưu như một đóng góp mở rộng tiềm năng cho giai đoạn Luận văn tốt nghiệp (`Thesis Extension`).

---

## 19. Các Đề xuất Sơ bộ (Preliminary Recommendations — Proposed, Not Approved)

Căn cứ trên toàn bộ bằng chứng thực nghiệm của W2.3, nhóm nghiên cứu đưa ra 3 khuyến nghị sơ bộ:

### Khuyến nghị cho D4 (Model Grounding Output Interface)
- **Đề xuất lựa chọn Phương án D4-A:** Chuẩn hóa giao diện đầu ra định vị nội bộ là **Hộp bao tọa độ chuẩn hóa dạng văn bản (`Textual Normalized Bounding Box`)**, quy ước duy nhất theo chuẩn:
  $$\mathbf{b}_{\text{canonical}} = [x_{\min}, y_{\min}, x_{\max}, y_{\max}] \quad \text{trong thang đo} \quad [0.0, 1.0]$$
- **Nguyên tắc hai lớp dữ liệu:** Bắt buộc lưu trữ nguyên văn Raw Model Response trước khi parse; bộ adapter/parser có trách nhiệm chuyển đổi tất định về canonical schema.
- **Chính sách phân tầng năng lực (Capability-Aware Policy B):**
  - Benchmark Phân loại An toàn: Đánh giá trên toàn bộ các mô hình tham gia.
  - Benchmark Định vị Bằng chứng: Đánh giá trên các mô hình có năng lực xuất tọa độ, sử dụng cùng một cấu trúc prompt và canonical interface. Báo cáo minh bạch danh sách mô hình tham gia grounding track và không so sánh thứ hạng grounding với mô hình không tham gia. Xác minh năng lực mô hình tại W2.5.

### Khuyến nghị cho D6 (Full Direct-Support Census)
- **Phê chuẩn Hệ phân loại 12 Nguy cơ Nguyên tử (`12 Hazard Atoms`)** đã được kiểm chứng bao phủ 100% dữ liệu Anomaly.
- **Phê chuẩn việc phân định rạch ròi:** Sample-level counts ($N=1.000$) và Hazard-atom counts ($N=1.788$).
- **Phê chuẩn quy mô các tập con thực nghiệm và ranh giới giao thoa:**
  - *Direct-Support Sample Pool:* **721 mẫu** (gồm 367 mẫu `ALL_DIRECT`, 323 mẫu `MIXED_DIRECT_PROXY`, 31 mẫu có direct atom trong `HAS_UNSUPPORTED`).
  - *Weak-Proxy Sample Pool:* **608 mẫu** (gồm 251 mẫu `PROXY_ONLY`, 323 mẫu `MIXED_DIRECT_PROXY`, 34 mẫu có proxy atom trong `HAS_UNSUPPORTED`).
  - *Giao thoa giữa Hai Pool:* Đúng **347 mẫu** (không cộng gộp 721 + 608; $721 + 608 - 347 = 982$ mẫu).
  - *Direct Hazard Atoms:* **781 atoms**.
  - *Weak-Proxy Hazard Atoms:* **947 atoms**.
  - *Unsupported Samples:* **59 mẫu** (`HAS_UNSUPPORTED`) / **60 hazard atoms** (trong đó có 18 mẫu `Unsupported Only`).
- **Phê chuẩn Khung RQ3:** Báo cáo tách biệt hoàn toàn giữa RQ3-A (Direct Object-Support) và RQ3-B (Weak Proxy qua `Person`).

### Khuyến nghị cho D7 (Optional Rationale Annotation Campaign)
- **Đề xuất lựa chọn Phương án D7-A cho giai đoạn Seminar:** Không triển khai chiến dịch tự gán nhãn rationale mới trong giai đoạn 8 tuần này.
- Tập trung nguồn lực thực hiện chuẩn xác, nghiêm ngặt các đánh giá trên 721 mẫu Direct-Support Pool và 608 mẫu Weak-Proxy Pool.
- Bảo lưu phương án D7-C (chiến dịch gán nhãn kép có thẩm định chuyên gia) làm hướng phát triển trọng tâm cho Luận văn tốt nghiệp sau này.

---

## 20. Rủi ro và Giới hạn Phương pháp luận (Risks and Limitations)

1. **Rủi ro Đồng xuất hiện Đa nguy cơ (Multi-Hazard Confounding):** 323 mẫu thuộc diện `MIXED_DIRECT_PROXY` chứa đồng thời nguy cơ trực tiếp và vi phạm PPE. Khi mô hình dự đoán trúng hộp bao của vật thể trực tiếp (ví dụ `Mobile Phone`), rất khó khẳng định mô hình có đồng thời nhận thức được vi phạm thiếu găng tay hay không nếu không có cơ chế prompt bóc tách từng nguy cơ.
2. **Rủi ro Lệch miền trong Tầng Nguy cơ (Strata-Domain Confounding):** Nguy cơ tràn chất lỏng (`LIQUID_ON_GROUND`) tập trung 94,0% ở hóa chất dầu khí; xe thô sơ lấn làn (`NONMOTORIZED_VEHICLE`) tập trung 100% ở hầm. Hiện tượng này gắn chặt nguy cơ với bối cảnh thị giác của từng miền cụ thể, gây khó khăn cho việc phân định rạch ròi giữa khả năng khái quát hóa nguy cơ và khả năng nhận diện miền của VLM.
3. **Giới hạn của Bounding Box phái sinh:** Việc derive BBox từ Polygon làm tăng diện tích vùng chấp nhận (đặc biệt với các vật thể dài, nghiêng như đường ống, hoặc tư thế người nằm co). Cần thiết lập ngưỡng đánh giá chặt chẽ tại W2.4 để tránh dương tính giả do diện tích hộp bao quá lớn.
4. **Giới hạn của Miền Luyện kim (`metallurgy`):** Chỉ có 9 mẫu Anomaly với 25 hazard atoms; 8/9 mẫu có văn bản mô tả dầu khí. Mọi kết luận grounding trên miền luyện kim chỉ mang tính mô tả định tính cục bộ, hoàn toàn không đủ độ tin cậy thống kê.

---

## 21. Các câu hỏi cần xin ý kiến phê duyệt (Questions Requiring Approval)

Nhằm chuẩn bị phê duyệt dứt điểm các quyết định trong tuần W2, các câu hỏi sau được trình lên Research Lead:

### Nhóm câu hỏi sẵn sàng phê duyệt cho Quyết định D4:
1. *Research Lead có phê chuẩn **Định dạng Chuẩn hóa Nội bộ Duy nhất** $\mathbf{b}_{\text{canonical}} = [x_{\min}, y_{\min}, x_{\max}, y_{\max}] \in [0.0, 1.0]$ làm chuẩn biểu diễn bám bằng chứng chính thức của SafeShift không?*
2. *Research Lead có phê chuẩn quy trình bắt buộc lưu trữ nguyên văn **Raw Model Response** trước khi bóc tách và chuyển đổi thành **Canonical Parsed Record** không?*
3. *Research Lead có phê chuẩn **Chính sách phân tầng năng lực Policy B** (Classification benchmark cho mọi mô hình; Grounding benchmark chỉ cho các mô hình có năng lực xuất tọa độ trên cùng canonical prompt) không?*

### Nhóm câu hỏi sẵn sàng phê duyệt cho Quyết định D6:
1. *Research Lead có phê chuẩn **Hệ phân loại 12 Nguy cơ Nguyên tử (`Hazard Atom Taxonomy`)** và bảng ánh xạ nhãn đối tượng hỗ trợ tại Mục 5 & Mục 7 không?*
2. *Research Lead có chấp thuận định nghĩa và quy mô của **Direct-Support Sample Pool (721 mẫu)** và **Weak-Proxy Sample Pool (608 mẫu)** đi kèm việc xác nhận ranh giới giao thoa 347 mẫu và yêu cầu bắt buộc báo cáo chi tiết thành phần nội bộ không?*
3. *Research Lead có phê chuẩn việc **phân tách độc lập kết quả thực nghiệm của RQ3** thành RQ3-A (Direct Object-Support) và RQ3-B (Weak Proxy qua `Person`) không?*
4. *Research Lead có phê chuẩn danh mục **7 Tầng Nguy cơ Gom nhóm Ứng viên cho RQ2** tại Mục 11 không?*

### Nhóm câu hỏi sẵn sàng phê duyệt cho Quyết định D7:
1. *Research Lead có chấp thuận **Phương án D7-A (Không tạo nhãn rationale mới trong giai đoạn Seminar 8 tuần)** nhằm bảo toàn tính khách quan và tập trung nguồn lực tái lập baseline không?*
2. *Nếu muốn bổ sung nhãn rationale, Research Lead có yêu cầu bắt buộc phải thực hiện theo chuẩn gán nhãn kép D7-C hay chấp nhận tập con thí nghiệm nhỏ hơn?*

---

## 22. Nguồn gốc Bằng chứng Kiểm chứng (Evidence Sources)

Tất cả các kết luận và số liệu thống kê trong báo cáo này đều có thể truy vết và tái lập cục bộ (`traceable and locally reproducible with the recorded script/artifact hashes`) dựa trên các nguồn tài liệu và artifact sau trong kho lưu trữ SafeShift:

1. **Kho lưu trữ Dữ liệu Gốc & Dấu vân tay Mật mã:**
   - `data/raw/InspecSafe-V1/{train,test}/DATA_PATH/{train,test}/Annotations/Anomaly_data/` (1.000 cặp tệp `.json` và `.txt`).
   - Dấu vân tay mật mã toàn bộ bộ dữ liệu InspecSafe-V1 (5.013 mẫu) đã kiểm chứng tại W1:  
     `7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`
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
   - `scratch/full_census_engine.py` — Mã nguồn kiểm kê thực chứng cục bộ (SHA-256: `348860eabbe06c7908b3f4b198804033b3bd61917da4dbf8d6ec06e9cc4b5c03`).
   - `data/manifests/w2_grounding_census.json` — Bản ghi chi tiết 1.000 mẫu Anomaly và 1.788 hazard atoms (SHA-256: `cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`).
