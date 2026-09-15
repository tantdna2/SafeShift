# W1 Dataset Audit — InspecSafe-V1

**Báo cáo tổng hợp kiểm toán dữ liệu và rà soát điều kiện chuyển giai đoạn W1 → W2**  
*Dự án SafeShift — Tuần 1 (Dataset Audit), Bước 9*  
*Ngày audit: 15/09/2026*  
*Trạng thái cổng kiểm soát (W1 Gate Status): `READY_FOR_REVIEW`*

---

## 1. Executive Summary

Báo cáo này tổng hợp toàn bộ các kết quả kiểm toán thực chứng (**verified findings**) đã được kiểm chứng chéo độc lập xuyên suốt Week 1 (Bước 1 đến Bước 8) trên bộ dữ liệu **InspecSafe-V1**, đóng vai trò là tài liệu nhập môn và căn cứ phương pháp luận chính thức để chuyển sang Week 2:

1. **Quy mô và Cấu trúc Bộ Ba (Triplets):** Khảo sát 100% tệp dữ liệu xác nhận toàn bộ tập dữ liệu gồm **5.013 mẫu ảnh RGB** hoàn chỉnh, mỗi mẫu là một bộ ba tệp (`.jpg`, `.json`, `.txt`) có stem tên tệp trùng khớp tuyệt đối, không có tệp mồ côi.
2. **Phân chia Chính thức:** Tập dữ liệu phân bổ thành **3.763 mẫu huấn luyện (`train`, 75,06%)** và **1.250 mẫu kiểm thử (`test`, 24,94%)**; phân loại nhị phân gồm **4.013 mẫu Bình thường (`Normal_data`, 80,05%)** và **1.000 mẫu Bất thường (`Anomaly_data`, 19,95%)**.
3. **Phạm vi Miền Công nghiệp:** Bao phủ **5 miền công nghiệp** theo tên thư mục: `coal_conveyor` (1.121 mẫu), `metallurgy` (720 mẫu), `oil_chemical` (1.023 mẫu), `power` (869 mẫu) và `tunnel` (1.280 mẫu).
4. **Đối tượng và Nhãn thô:** Chứa tổng cộng **37.434 đa giác gán nhãn đối tượng** (`shapes`, 100% `polygon`) với **231 chuỗi nhãn đối tượng thô duy nhất** (230 nhãn tiếng Anh và 1 nhãn tiếng Trung `"出口"`).
5. **Cơ sở Pháp lý & Giấy phép:** Dataset được phát hành chính thức dưới giấy phép mở **CC-BY-4.0** (cho phép nghiên cứu học thuật và thương mại kèm ghi công; chính sách SafeShift là phi thương mại và `DO_NOT_REDISTRIBUTE_RAW_DATA`). Bài báo trên *Scientific Data* có bản quyền riêng biệt (**CC BY-NC-ND 4.0**).
6. **Trùng lặp Tuyệt đối Xuyên Split:** Kiểm định SHA-256 xác nhận **53 cặp trùng lặp pixel tuyệt đối** trong dataset, trong đó có **7 cặp trùng lặp tuyệt đối xuyên split (`cross-split exact pairs`)**, bộc lộ sự tái sử dụng ảnh trực tiếp giữa train và test trên các point ID khác nhau.
7. **Sàng lọc Độ tương đồng Cảm nhận (dHash):** Sàng lọc perceptual hash ghi nhận **833 cặp có dHash $\le 8$ xuyên split**, bóc tách chính xác gồm **7 cặp exact đã xác minh** và **826 cặp ứng viên chưa kiểm chứng (nonexact candidates)**; không đánh đồng 826 cặp ứng viên này là rò rỉ đã xác nhận.
8. **Dấu vết Nguồn và Họ Nguồn (Source Families):** Phát hiện **12 họ nguồn ảnh suy luận (`source-family pools`)** bao trùm toàn bộ 1.000 mẫu `Anomaly_data`, tất cả đều thể hiện quy luật phân chia có hệ thống theo chỉ số (~25% prefix chỉ số thấp cho test, ~75% chỉ số sau cho train). Khảo sát trực quan có phương pháp xác nhận bằng chứng chia sẻ chuỗi video hoặc góc máy robot ở nhiều trường hợp lấy mẫu; tuy nhiên, không suy diễn rằng toàn bộ 1.000 mẫu Anomaly đều là một chuỗi video duy nhất.
9. **Xung đột Nhãn Miền:** Xác nhận chính xác **36 mẫu có sự xung đột** giữa tên thư mục (`folder_domain`) và khẳng định ngữ cảnh trong câu mô tả văn bản (`text_domain`).
10. **Mất Cân bằng Cực đoan về Cấp độ An toàn:** `Level04` (Normal) chiếm **80,05% (4.013 mẫu)**, trong khi `Level03` chỉ có vỏn vẹn **15 mẫu (0,30%)** trên toàn bộ dataset, tạo ra tỷ số mất cân bằng **267,53 : 1**.
11. **Giới hạn Trầm trọng của Miền Luyện kim (`metallurgy`):** Miền này có 720 mẫu nhưng chỉ có 9 mẫu Anomaly ở train và **0 mẫu Anomaly ở test chính thức**; đồng thời 8/9 mẫu train Anomaly mang khẳng định văn bản là `oil_chemical`.
12. **Phán quyết Khả thi Xuyên Miền (Cross-Domain Verdict):** Phân tích so sánh xuyên miền là **`FEASIBLE_WITH_CONSTRAINTS`**; tuy nhiên, bài toán Domain Generalization chuẩn trên split chính thức là **`NOT_CURRENTLY_FEASIBLE / NOT SUITABLE AS-IS`** do rò rỉ chuỗi và platform confounding nghiêm trọng (custom group-aware split là `PARTIALLY_FEASIBLE`).
13. **Phán quyết Khả thi Bám Bằng chứng (Grounding Verdict):** Toàn bộ 37.434 đa giác là **object polygon annotations**, không phải **hazard evidence annotations**. Thẩm định chuyên sâu trên 63 mẫu Anomaly cho thấy chỉ 20,6% có Direct Support từ vật thể hiện hữu trong tập này; do đó Grounding với nhãn hiện tại là **`PARTIALLY_FEASIBLE`** (khả thi ở mức Object Support và Weak Proxy), trong khi Full Hazard-Rationale Grounding là **`NOT_CURRENTLY_FEASIBLE`** nếu không có nhãn bổ sung.
14. **Sẵn sàng Chuyển Giai đoạn (W1 $\rightarrow$ W2 Readiness):** Toàn bộ 145/145 unit tests pass, toàn bộ số liệu đã được kiểm chứng và đối soát nhất quán; gói tài liệu audit W1 đã sẵn sàng cho bước rà soát độc lập (`READY_FOR_REVIEW`) trước khi mở giao thức W2.

---

## 2. Dataset Identity, Publication, and License

### 2.1 Định danh và Kênh phát hành chính thức

- **Tên bộ dữ liệu:** `InspecSafe-V1` (*Inspection Safety Benchmark - Version 1*).
- **Phiên bản chuẩn:** `v1.0.1` (theo Zenodo Record) / Git Commit Snapshot `f3cb7d3e7827c1afc1c5bfd0524257984bba46ab` (theo Hugging Face Hub).
- **Các kênh phát hành chính thức:**
  - **Hugging Face Hub:** `https://huggingface.co/datasets/Tetrabot2026/InspecSafe-V1` (Tổ chức `Tetrabot2026`, Open Access, dung lượng công bố ~41,5 GB).
  - **Kho lưu trữ trường tồn Zenodo (CERN):** DOI [10.5281/zenodo.19885643](https://doi.org/10.5281/zenodo.19885643) (Bản phát hành ngày 30/04/2026).
  - **Mã nguồn GitHub chính thức:** `https://github.com/liuzy0708/InspecSafe` (Tác giả chính Zeyi Liu).
- **Tổ chức chủ quản:** Khoa Tự động hóa & Viện Trí tuệ Hiện thân và Robot, Đại học Thanh Hoa (Tsinghua University); Công ty TNHH Trí tuệ TetraBOT; Viện Đạt Ma, Tập đoàn Alibaba (DAMO Academy); và Đại học Đông Nam (Southeast University), Trung Quốc.

### 2.2 Bài báo khoa học gắn liền

- **Ấn phẩm tạp chí chính thức (Version of Record):**  
  *Scientific Data* (thuộc Nature Portfolio / Springer Nature).  
  - Tiêu đề: *Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios*  
  - Tác giả: Zeyi Liu, Shuang Liu, Jihai Min, Zhaoheng Zhang, Jun Cen, Pengyu Han, Songqiao Hu, Zihan Meng, Xiao He, Donghua Zhou.  
  - Trích dẫn: Volume 13, Article number: 1198 (Xuất bản ngày 17/08/2026).  
  - DOI: [10.1038/s41597-026-07796-x](https://doi.org/10.1038/s41597-026-07796-x). Tác giả liên hệ: GS. Xiao He (`hexiao@tsinghua.edu.cn`).
- **Bản thảo lưu trữ (Preprint):**  
  arXiv:2601.21173 (`cs.RO`, `cs.CV`), DOI [10.48550/arXiv.2601.21173](https://doi.org/10.48550/arXiv.2601.21173). Đây là tài liệu lưu trữ quá trình phát triển, không thay thế ấn phẩm chính thức trên *Scientific Data*.

### 2.3 Phân tích Giấy phép Đa tầng (Multi-Tier License Audit)

Cần phân định rạch ròi ba tầng pháp lý độc lập:
1. **Dataset License:** Giấy phép chính thức là **Creative Commons Attribution 4.0 International (CC-BY-4.0)**. Áp dụng cho toàn bộ tệp ảnh `.jpg`, JSON đa giác, văn bản mô tả `.txt`, video `.mp4`, âm thanh `.wav` và dữ liệu cảm biến. Giấy phép này cho phép sao chép, phân phối, chuyển thể và khai thác cho mọi mục đích (kể cả thương mại) với điều kiện bắt buộc duy nhất là **Attribution (ghi công nguồn tác giả)** hợp lý. Câu chữ *"intended for research use"* trong README là thông cáo mục đích thiết kế, không cấu thành điều khoản cấm thương mại về mặt pháp lý của CC-BY-4.0.
2. **Paper Copyright & License:** Văn bản bài báo và các hình vẽ/biểu đồ (figures) xuất bản trên tạp chí *Scientific Data* chịu giấy phép **CC BY-NC-ND 4.0** (phi thương mại, cấm tác phẩm phái sinh). Bản preprint trên arXiv chịu giấy phép phân phối phi độc quyền của arXiv.
3. **Code License:** Mã nguồn script trong repository GitHub của tác giả ở trạng thái **RESTRICTED / NOT_SPECIFIED (Standalone)** do không có tệp `LICENSE` chuẩn OSI độc lập (như MIT hay Apache-2.0). SafeShift chỉ tham khảo logic kiểm tra, tự viết bộ mã nguồn độc lập trong `safeshift/` kèm kiểm thử đầy đủ.

### 2.4 Tóm tắt Ma trận Quyền hạn và Chính sách SafeShift

| Hạng mục hoạt động | Quyền pháp lý (Legal) | Chính sách SafeShift (Project Policy) | Diễn giải quy tắc SafeShift |
|---|:---:|:---:|---|
| Nghiên cứu học thuật / Seminar | **ALLOWED** | **ALLOWED** | Được phép toàn quyền sử dụng cho phân tích, đo đạc và báo cáo khoa học. |
| Khai thác thương mại | **ALLOWED** | **RESTRICTED** | SafeShift tự nguyện giới hạn trong phạm vi nghiên cứu học thuật phi thương mại. |
| Tạo dữ liệu phái sinh / Manifest | **ALLOWED** | **ALLOWED** | Được phép xuất manifest dẫn xuất, CSV thống kê, nhãn chuẩn hóa; không nhúng Base64. |
| Phân phối lại dữ liệu thô (Redistribution) | **ALLOWED** | **PROHIBITED** | Chính sách dự án: `DO_NOT_REDISTRIBUTE_RAW_DATA` — Tuyệt đối KHÔNG commit raw dataset (23+ GB) lên Git; người dùng phải tải từ kênh chính thức của tác giả. |
| Trích dẫn hình ảnh mẫu (Sample Images) | **ALLOWED** | **ALLOWED (Có kiểm soát)** | Chỉ lấy từ asset dataset (CC-BY-4.0), không chụp lại figures từ bài báo (CC BY-NC-ND 4.0). Phải che mờ định danh cá nhân. |
| Công bố trọng số mô hình (Model Weights) | **NOT_SPECIFIED** | **SEPARATE REVIEW** | Phụ thuộc vào license của base VLM và điều khoản dịch vụ API; cần xem xét riêng ở W2. |

*(Bảng ma trận quyền hạn chi tiết và trích dẫn BibTeX đầy đủ: xem [notes/source_license_audit.md](source_license_audit.md)).*

---

## 3. Local Dataset Snapshot & Provenance

### 3.1 Nguồn gốc khôi phục cục bộ

- **Vị trí dữ liệu thô cục bộ:**
  ```text
  data/raw/InspecSafe-V1/
  ```
- **Phương thức khôi phục trên máy trạm hiện tại:** Dữ liệu được giải nén từ tệp sao lưu nội bộ:
  ```text
  D:\SafeShift.zip
  ```
  *(Lưu ý phương pháp luận: `SafeShift.zip` là tệp lưu trữ nội bộ của máy trạm cá nhân, KHÔNG được coi là archive thượng nguồn chính thức từ nhà xuất bản).*

### 3.2 Dấu vân tay nội dung (Dataset Content Fingerprint)

- **Mã băm SHA-256 nội dung đã xác minh:**
  ```text
  1a52f9078d53bddcdcd8400486a6e22f7688c8c20dc85b481b128f94c723399c
  ```
- **Ý nghĩa kỹ thuật chính xác:** Giá trị băm này được tính toán theo quy tắc tuần tự hóa cố định (ASCII JSON lines `[repo-relative path, full-file SHA-256]` cho từng tệp `.jpg`, `.json`, `.txt` thuộc 5.013 mẫu). Nó **chứng minh snapshot local khớp 100% với snapshot đã audit trong phạm vi validator và duplicate auditor**.
- **Giới hạn học thuật:** Dấu vân tay nội bộ này **KHÔNG chứng minh danh tính cấp byte của archive thượng nguồn (upstream archive byte identity)**, không thay thế checksum phát hành của nhà xuất bản và không chứng minh nguồn gốc pháp lý độc lập.

### 3.3 Đối soát tệp nén cục bộ và bản phát hành thượng nguồn

Trong thư mục `data/raw/InspecSafe-V1`, hai tệp archive nén có thông số:
- `train.tar.gz` cục bộ: **17.886.855.594 bytes** (~17,89 GB).
  - Trùng khớp kích thước khai báo trên Hugging Face LFS: `17.886.855.594 bytes`.
  - Trùng khớp kích thước khai báo trên Zenodo API: `17.886.855.594 bytes` (MD5: `a2b84da421c32a67b025240ad4365048`).
- `test.tar.gz` cục bộ: **5.748.799.871 bytes** (~5,75 GB).
  - Trùng khớp kích thước khai báo trên Hugging Face LFS: `5.748.799.871 bytes`.
  - Trên Zenodo: Bản phát hành lưu dưới dạng tệp `test.tar` không nén (**6.199.326.720 bytes**, MD5: `51890d4e6c5bac6d7e22d6f655265c83`).
- **Đánh giá xác thực:** Sự khác biệt giữa `test.tar` (Zenodo) và `test.tar.gz` (Hugging Face) được xác định là **khác biệt đóng gói (packaging difference candidate)**; nội dung tương đương giữa hai kho lưu trữ này **chưa được kiểm chứng độc lập cấp byte** do chưa giải nén và hash đối chiếu chéo. Các tệp nén local nhất quán (*consistent*) với metadata của Hugging Face, nhưng chưa được hash SHA-256 toàn bộ archive độc lập để chứng minh tính toàn vẹn byte-identical upstream provenance. Toàn bộ archive được loại trừ khỏi Git theo `.gitignore`.

---

## 4. Schema and Sample Definition

### 4.1 Đơn vị mẫu (Sample Unit)

Mỗi mẫu quan sát (sample / instance) trong InspecSafe-V1 được định nghĩa bởi một bộ ba tệp (**triplet**) hoàn chỉnh:
1. **Tệp ảnh quang học (`.jpg`):** Khung hình RGB vùng ánh sáng khả kiến ghi lại hiện trường tuần tra.
2. **Tệp cấu trúc đa giác (`.json`):** Định dạng LabelMe / AnyLabeling (version 0.4.15) chứa danh sách các đa giác phân vùng đối tượng (`shapes[]`), độ phân giải ảnh và chuỗi Base64 `imageData`.
3. **Tệp mô tả văn bản (`.txt`):** Văn bản tiếng Anh một dòng mô tả các thực thể quan sát được và kết luận cấp độ an toàn.

Kiểm toán xác nhận: **100% mẫu (5.013 / 5.013) đều tạo thành triplet hợp lệ**; không có tệp mồ côi hay stem lệch nhau.

### 4.2 Cấu trúc thư mục

Cấu trúc thư mục thực tế trên đĩa do quá trình giải nén archive tạo thành dạng lồng:
```text
data/raw/InspecSafe-V1/
├── train/DATA_PATH/train/Annotations/
│   ├── Normal_data/       # 1.675 thư mục điểm (3.014 mẫu)
│   └── Anomaly_data/      # 749 thư mục điểm (749 mẫu)
├── test/DATA_PATH/test/Annotations/
│   ├── Normal_data/       # 559 thư mục điểm (999 mẫu)
│   └── Anomaly_data/      # 251 thư mục điểm (251 mẫu)
```
- Trong `Anomaly_data`: 100% thư mục điểm chỉ chứa **duy nhất 1 mẫu** (`-001`).
- Trong `Normal_data`: Một thư mục điểm chứa từ **1 đến 4 mẫu** ảnh chụp liên tiếp (`-001` đến `-004`).

### 4.3 Quy tắc đặt tên mẫu (Naming Pattern)

100% tên thư mục điểm tuần tra và tệp mẫu tuân thủ cú pháp biểu thức chính quy:
- **Tên thư mục điểm:**  
  `{domain}-Level{level:02d}-{platform}-{point_id:06d}`  
  *Ví dụ:* `coal_conveyor-Level04-SuspendedRail-000560`
- **Tên tệp mẫu:**  
  `{point_directory}-{instance_id:03d}.{ext}`  
  *Ví dụ:* `coal_conveyor-Level04-SuspendedRail-000560-001.jpg`

### 4.4 Đối soát Điểm Tuần tra: 2.239 Sites vs. 3.234 Point Folders

- **Tài liệu chính thức (*Scientific Data* & HF README):** Công bố **2.239 valid inspection sites/waypoints**.
- **Kiểm toán thực tế cục bộ:** Ghi nhận chính xác **3.234 thư mục điểm tuần tra logic** (`point_id` từ `000001` đến `003234`), gồm 2.424 điểm ở train và 810 điểm ở test. Độ trùng lặp point ID giữa train và test bằng 0.
- **Tình trạng:** **`UNRESOLVED mapping`**.
- **Nguyên tắc khoa học:** Giả thuyết cho rằng con số 2.239 là các trạm vật lý cố định và sự chênh lệch bắt nguồn từ việc robot quay lại nhiều lần (repeat visits) hoặc tách split logic **chỉ là giả thuyết thuần túy**, do tác giả không cung cấp bảng ánh xạ (mapping table). SafeShift **tuyệt đối không biến giả thuyết repeat visits thành sự thật đã chứng minh**.

---

## 5. Verified Dataset Statistics

Toàn bộ các bảng số liệu dưới đây được tổng hợp từ census thực tế trên 5.013 mẫu:

### 5.1 Thống kê Tổng thể theo Split và Loại Dữ liệu

| Split | Normal_data (Level04) | Anomaly_data (Level01–03) | Tổng số mẫu | Tỷ lệ Split (%) | Số thư mục Point ID |
|---|:---:|:---:|:---:|:---:|:---:|
| **Train** | 3.014 (80,10%) | 749 (19,90%) | **3.763** | 75,06% | 2.424 |
| **Test** | 999 (79,92%) | 251 (20,08%) | **1.250** | 24,94% | 810 |
| **Toàn bộ Dataset** | **4.013 (80,05%)** | **1.000 (19,95%)** | **5.013** | 100,00% | **3.234** |

### 5.2 Phân bố Cấp độ An toàn (Safety Level)

| Cấp độ An toàn | Ý nghĩa Quy chuẩn | Tập Train | Tập Test | Toàn bộ Dataset | Tỷ lệ (%) | Ghi chú Phân bố |
|---|---|:---:|:---:|:---:|:---:|---|
| **Level01** | Nguy cơ cao (High Risk / Vi phạm nghiêm trọng) | 490 | 169 | **659** | 13,15% | Đám cháy, hút thuốc, dùng điện thoại, người ngã |
| **Level02** | Nguy cơ vừa (Moderate Risk / Vi phạm trung bình) | 251 | 75 | **326** | 6,50% | Cửa tủ mở, thiếu găng tay, dị vật |
| **Level03** | Nguy cơ thấp (Minor Hazard / Cảnh báo nhẹ) | 8 | 7 | **15** | **0,30%** | **Cực hiếm (Rare Class)**; 100% thuộc SuspendedRail |
| **Level04** | Trạng thái bình thường (Normal / An toàn) | 3.014 | 999 | **4.013** | **80,05%** | Chiếm đa số áp đảo |
| **Tổng cộng** | | **3.763** | **1.250** | **5.013** | 100,00% | |

### 5.3 Phân bố theo 5 Miền Công nghiệp (Folder Domain)

| Miền Công nghiệp (`folder_domain`) | Mẫu Train | Mẫu Test | Mẫu Normal | Mẫu Anomaly | Tổng số mẫu | Tỷ lệ (%) | Nền tảng Robot chủ đạo |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **`coal_conveyor`** | 822 | 299 | 865 | 256 | **1.121** | 22,36% | 100% SuspendedRail |
| **`metallurgy`** | 543 | 177 | 711 | **9** | **720** | 14,36% | 91,8% Wheeled (Test Anomaly = 0) |
| **`oil_chemical`** | 778 | 245 | 662 | 361 | **1.023** | 20,41% | 90,2% Wheeled |
| **`power`** | 656 | 213 | 767 | 102 | **869** | 17,33% | 87,8% Wheeled |
| **`tunnel`** | 964 | 316 | 1.008 | 272 | **1.280** | 25,53% | 98,1% SuspendedRail |
| **Tổng cộng** | **3.763** | **1.250** | **4.013** | **1.000** | **5.013** | 100,00% | |

### 5.4 Chú thích Đối tượng (Object Annotations) và Độ phân giải Ảnh

- **Tổng số đa giác gán nhãn:** **37.434 polygons** (100% là `shape_type: "polygon"`). Trung bình 7,47 đa giác/mẫu (Normal: 6,60; Anomaly: 10,96).
- **Danh mục nhãn đối tượng thô:** **231 chuỗi nhãn duy nhất** (Train: 207; Test: 166; Giao nhau: 142; 65 chỉ có ở Train; 24 chỉ có ở Test).
  *(Lưu ý: Bài báo chính thức công bố 234 categories; khoảng cách 3 lớp là `UNRESOLVED`, SafeShift không chuẩn hóa nhãn để ép khớp).*
- **Độ phân giải hình ảnh:** Xác nhận **66 độ phân giải duy nhất**, trong đó 3 độ phân giải chuẩn chiếm 96,19%:
  - `2560 x 1440` (QHD / 1440p): **2.576 ảnh (51,39%)**
  - `1920 x 1080` (Full HD): **2.124 ảnh (42,37%)**
  - `1280 x 720` (HD): **122 ảnh (2,43%)**
  - 63 biến thể kích thước khác: **191 ảnh (3,81%)**
- **Định dạng nhị phân hình ảnh (Magic bytes):**
  - **4.969 ảnh** là chuẩn JPEG thực sự (magic bytes `FF D8 FF`).
  - **44 ảnh là PNG thực tế bị đặt sai đuôi `.jpg`** (magic bytes `89 50 4E 47`, đều thuộc `Anomaly_data`: 39 train, 5 test).

---

## 6. Data Integrity and Quality Findings

### 6.1 Tổng kết Kiểm định Tính Toàn vẹn (Integrity Summary)

Quy trình kiểm định giải mã độc lập bằng Pillow (codec thực tế) trên toàn bộ 5.013 mẫu hoàn tất với kết quả:
- **0 ảnh bị hỏng / không đọc được** (0 unreadable images).
- **0 tệp JSON sai cấu trúc cú pháp** (0 malformed JSON).
- **0 tệp TXT sai mã hóa UTF-8 hoặc rỗng** (0 malformed TXT).
- **0 lỗi cấu trúc bộ ba** (0 structural triplet errors).

### 6.2 Các Cảnh báo Kỹ thuật Được Ghi nhận (Preserved Warnings)

Kiểm toán ghi nhận 5 nhóm cảnh báo kỹ thuật với tổng cộng 5.496 lượt phát sinh, **toàn bộ đều được bảo lưu nguyên trạng, không sửa hoặc loại bỏ mẫu khỏi dataset**:

1. **309 đa giác vượt biên ảnh (Out-of-bounds polygons):** Ảnh hưởng tới **276 mẫu** (132 train Normal, 63 train Anomaly, 65 test Normal, 16 test Anomaly). Tọa độ đỉnh mang giá trị âm nhỏ (ví dụ $x = -2.64$) do thao tác chấm điểm sát mép ảnh của annotator.
2. **5.013 tệp JSON có `imagePath` không khớp basename của mẫu:** Trường `imagePath` trong toàn bộ 5.013 JSON lưu tên tệp gốc từ hệ thống trích xuất upstream (ví dụ `_frame_000001.jpg`), khác với tên triplet chuẩn hóa trên đĩa. Đây là **dấu vết nguồn gốc (provenance metadata)**, tuyệt đối không phải lỗi hỏng hóc tệp (corruption).
3. **94 trường hợp `imageData` Base64 khác mã băm tệp ảnh ngoài:** Xảy ra tại 94 mẫu Normal (72 train, 22 test). Base64 giải mã nghiêm ngặt hợp lệ; tệp ảnh ngoài cũng giải mã pixel thành công. Đây là sự sai khác cấp byte nhị phân (**byte mismatch**), chưa thể kết luận là sai lệch hình ảnh (**visual mismatch**) nếu chưa đối chiếu pixel.
4. **44 ảnh mang định dạng PNG nhưng gắn đuôi `.jpg`:** Tất cả đều nằm trong `Anomaly_data`. Các bộ giải mã tự động nhận diện magic bytes (Pillow, OpenCV) đều đọc bình thường.
5. **36 mẫu xung đột tên miền giữa thư mục và văn bản:** Ghi nhận 36 mẫu có tên thư mục khác với tên miền được khẳng định trong câu mở đầu tệp TXT.

---

## 7. Duplicate and Split-Independence Findings

### 7.1 Trùng lặp Pixel và Byte Tuyệt đối (Exact Duplicates)

- **Tổng số cặp trùng lặp tuyệt đối:** **53 cặp** (thuộc 53 nhóm kích thước 2; gồm 38 cặp Normal–Normal và 15 cặp Anomaly–Anomaly). Toàn bộ 53 cặp này đều vừa là `CONFIRMED_EXACT_BYTE` vừa là `CONFIRMED_PIXEL_EXACT` (không có cặp nào khác byte nhưng cùng pixel).
- **Trùng lặp tuyệt đối xuyên Split (`cross-split exact pairs`):** Xác nhận chính xác **7 cặp ảnh hoàn toàn đồng nhất từng byte và pixel** giữa tập `train` và tập `test`.
- **Đặc điểm của 7 cặp Exact Xuyên Split:**
  - 100% thuộc loại `Anomaly_data` $\leftrightarrow$ `Anomaly_data`.
  - 100% nằm ở các **thư mục điểm tuần tra khác nhau (`different point IDs`)**, do đó không thể giải thích bằng việc chụp liên tiếp tại cùng một điểm.
  - Khảo sát trực quan phát hiện các xung đột gán nhãn nghiêm trọng giữa hai nửa của cùng một bức ảnh:
    - *Cặp 1:* Cùng 1 ảnh nhưng Train gán nhãn **Level01** (không đội mũ bảo hộ), Test lại gán nhãn **Level02** (không đeo găng tay).
    - *Cặp 4:* Cùng 1 ảnh nhưng Train xếp vào **metallurgy** (robot SuspendedRail, không đeo găng), Test lại xếp vào **oil_chemical** (robot Wheeled, không đeo khẩu trang).
    - *Cặp 5 & 6:* Cùng 1 ảnh nhưng Train gán nhãn không đeo găng, Test gán nhãn hút thuốc.
    - *Cặp 7:* Cùng 1 đối tượng tĩnh ở góc nhưng Train gán là Trụ cứu hỏa (`Fire Hydrant`), Test gán là Bình chữa cháy (`Fire Extinguisher`).

### 7.2 Sàng lọc Độ tương đồng Cảm nhận (dHash Screening Pool)

- Thuật toán 64-bit dHash (LANCZOS resize 9x8, so sánh pixel kề) quét toàn bộ 12.562.578 phép so sánh không thứ tự.
- Tại ngưỡng sàng lọc rộng `dHash <= 8`, ghi nhận:
  - Toàn bộ dataset: 5.041 cặp (53 exact + 4.988 nonexact).
  - Xuyên split (`cross-split`): **833 cặp**, bóc tách chính xác gồm:
    $$\text{833 cross-split pairs} = \mathbf{7\text{ exact confirmed}} + \mathbf{826\text{ nonexact candidates}}$$
- **Nguyên tắc khoa học:** **Tuyệt đối KHÔNG gọi 826 cặp ứng viên này là rò rỉ đã xác nhận (confirmed leakage)**. Đây chỉ là tập ứng viên cần rà soát trực quan; ngay ở `dHash = 0` đã có 26 cặp phi exact do bố cục công nghiệp tĩnh tương tự.

### 7.3 Điều tra 12 Họ Nguồn Ảnh Suy luận (Source Families)

- Dựa trên tiền tố `imagePath` upstream, kiểm toán nhận diện **12 nhóm nguồn ảnh (`source-family pools`)** bao trùm đúng **1.000 mẫu `Anomaly_data`** (749 train / 251 test).
- **Quy luật phân chia chỉ số có hệ thống (~25/75 partition):** Cả 12 họ đều có dải frame counter từ `000001` đến `0000N`, trong đó test nhận ~25% chỉ số đầu và train nhận ~75% chỉ số sau.
- **Thẩm định trực quan có phương pháp (Bước 5):**
  - Xác nhận bằng chứng chia sẻ chuỗi video hoặc dùng chung góc máy camera robot (**shared-sequence / shared-viewpoint evidence**) ở nhiều trường hợp lấy mẫu ranh giới (ví dụ họ `nonmobile` với 100 khung hình từ một video 40 giây người đi xe đạp trong hầm, hoặc các khung hình cách nhau đúng 1 giây trong `cigarette`, `fire`).
  - **Giới hạn diễn giải:** Tư cách thành viên trong một source-family pool **KHÔNG tự động chứng minh rằng mọi thành viên trong họ đều thuộc cùng một video duy nhất**. Các family này là các hazard-category / source pools do tác giả gom góp từ nhiều trạm.
- **Kết luận:** Phân chia chính thức của InspecSafe-V1 có rủi ro rò rỉ và phi độc lập đã được kiểm chứng thực tế (**confirmed exact reuse and non-independence risk**). Tuy nhiên, **không được tuyên bố rằng official split hoàn toàn vô dụng (useless)**; split chính thức vẫn là chuẩn so sánh gốc cần được đánh giá song song với phân chia kiểm soát rò rỉ ở W2.

---

## 8. Distribution, Imbalance, and Confounding

### 8.1 Mất cân bằng Cực đoan (Extreme Class Imbalance)

- `Level04` (Normal) chiếm **80,05%** (4.013 mẫu), trong khi `Level03` chỉ chiếm **0,30% (15 mẫu)**.
- Tỷ số mất cân bằng lớp lớn nhất / nhỏ nhất là **267,53 : 1**.
- Toàn bộ 15 mẫu `Level03` đều thuộc về robot ray treo `SuspendedRail` (9 ở tunnel, 4 ở coal_conveyor, 1 ở power, 1 ở metallurgy, 0 ở oil_chemical).
- **Hệ quả:** Thước đo độ chính xác tổng thể đơn thuần (Plain accuracy) có nguy cơ che khuất hiệu năng trên các lớp hiếm. W2 bắt buộc phải cân nhắc các metric nhạy với mất cân bằng (như Macro-F1, Balanced Accuracy, Per-class Recall).

### 8.2 Giới hạn Dữ liệu của Miền Luyện kim (`metallurgy`)

- Tổng số mẫu: 720 (543 train / 177 test).
- Mẫu Normal: 711 (534 train / 177 test).
- Mẫu Anomaly: **9 mẫu ở train và 0 MẪU Ở TEST CHÍNH THỨC**.
- Trong 9 mẫu Anomaly ở train, có tới **8 mẫu mang khẳng định ngữ cảnh văn bản là `oil_chemical`**; chỉ duy nhất 1 mẫu (`metallurgy-Level03-SuspendedRail-002666-001`) có thư mục và văn bản cùng xác nhận metallurgy.
- **Hệ quả:** Miền `metallurgy` là một miền đích bị thiếu dữ liệu nghiêm trọng (**severely under-supported target domain**). Việc đánh giá năng lực phát hiện bất thường trên official split cho miền này là **không khả thi**; nếu dùng trong custom split gộp, mẫu số thống kê cũng cực kỳ yếu và danh tính miền bị mơ hồ.

### 8.3 Nhiễu Nền tảng Robot (Platform Confounding)

Khảo sát chéo giữa miền công nghiệp và nền tảng robot cho thấy sự gắn kết gần như tuyệt đối:
- **`coal_conveyor`:** **100,0% SuspendedRail** (1.121 / 1.121 mẫu).
- **`tunnel`:** **98,1% SuspendedRail** (1.256 / 1.280 mẫu).
- **`metallurgy`:** **91,8% Wheeled** (661 / 720 mẫu).
- **`oil_chemical`:** **90,2% Wheeled** (923 / 1.023 mẫu).
- **`power`:** **87,8% Wheeled** (763 / 869 mẫu).

```text
Robot Ray Treo (SuspendedRail, Góc dốc nhìn xuống):  coal_conveyor (100%), tunnel (98.1%)
Robot Bánh Lăn (Wheeled, Tầm mắt / sàn nhà xưởng):  metallurgy (91.8%), oil_chemical (90.2%), power (87.8%)
```

> [!WARNING]
> **Rủi ro phương pháp luận:** Tác động của miền công nghiệp (domain effects) **không thể tách rời một cách độc lập** khỏi nền tảng robot, góc đặt camera và phong cách thu thập dữ liệu. SafeShift **tuyệt đối không đưa ra bất kỳ tuyên bố nhân quả (causal claim)** nào về khả năng thích ứng miền công nghiệp thuần túy mà không chú thích yếu tố nhiễu nền tảng này.

### 8.4 Bối cảnh Từ vựng Mở (Open-Vocabulary Context)

- **65 nhãn chỉ xuất hiện ở tập Train** (ví dụ: `Ash Discharge Pipe`, `Circuit Breaker`, `Cutting Machine`).
- **24 nhãn chỉ xuất hiện ở tập Test** (ví dụ: `Chemical Protective Clothing`, `Oxygen Bottle`, `Traffic Light`).
- **142 nhãn xuất hiện ở cả hai tập**.
- Sự xuất hiện của 24 nhãn hoàn toàn mới ở tập test là một **thách thức / yếu tố gây nhiễu từ vựng mở tự nhiên (natural open-vocabulary challenge / confound)** phát sinh từ dữ liệu thô, **không phải một official open-vocabulary benchmark** được thiết kế có chủ đích.

---

## 9. Domain Metadata Reliability

Bảng phân loại toàn bộ 12 trường siêu dữ liệu theo mức độ tin cậy thực tế:

| Phân loại Tin cậy | Trường Siêu dữ liệu | Bản chất & Nguồn gốc | Mức độ Tin cậy | Hạn chế đã xác minh |
|---|---|---|:---:|---|
| **`OBSERVED_ORIGINAL`** | JSON `imagePath` | Chuỗi tên tệp gốc từ hệ thống trích xuất ban đầu trong JSON. | Cao (chỉ thị provenance) | 100% khác basename của mẫu trên đĩa; không phản ánh vị trí tệp hiện tại. |
| **`DETERMINISTIC_DERIVED`** | `folder_domain`<br>`text_domain`<br>`robot_platform`<br>`point_id`<br>`split`<br>`data_type`<br>`safety_level` | Các trường trích xuất xác định từ quy ước đặt tên đường dẫn và cấu trúc thư mục. | Trung bình đến Tuyệt đối (về mặt cú pháp) | - Xung đột giữa `folder_domain` và `text_domain` ở 36 mẫu.<br>- Point ID rời rạc giữa train/test nhưng chia sẻ chuỗi quay vật lý.<br>- Cặp exact 1 lệch safety level; Cặp 4 lệch platform và domain. |
| **`HEURISTIC`** | `source-family` | Tiền tố regex bóc tách từ `imagePath` gom nhóm 12 họ Anomaly. | Trung bình | Không phải video ID chính thức; cùng tiền tố có thể gộp nhiều cảnh quay độc lập. |
| **`VISUAL`** | Góc nhìn camera (`viewpoint`) | Suy luận từ kiểm tra hình ảnh trực quan (góc cắm dốc vs góc ngang sàn). | Tương đối | Gắn chặt với loại robot tuần tra; không có tọa độ camera pose bằng số. |
| **`UNAVAILABLE`** | Tọa độ GPS / site vật lý<br>Bảng map 2.239 sites<br>Video ID chính thức<br>Camera extrinsic matrix | Các thông số vật lý thực tế tại nhà máy. | **KHÔNG CÓ** | Hoàn toàn vắng mặt trong bản phát hành công khai; không thể suy đoán thành sự thật. |

> **Nguyên tắc phương pháp luận:** Cả `folder_domain` và `text_domain` đều **KHÔNG được nâng thành Domain Ground Truth tuyệt đối**. 36 mẫu xung đột giữa thư mục và văn bản được bảo lưu trạng thái chưa giải quyết (`unresolved`) và chuyển giao cho W2 đưa ra chính sách xử lý chính thức trong `DECISIONS.md`.

---

## 10. Evidence Annotation and Grounding Feasibility

### 10.1 Hiện trạng Chú thích Dữ liệu

Kiểm kê xác minh thực tế đối với khả năng hỗ trợ Evidence Grounding:
- **Tập dữ liệu CÓ:**
  - 37.434 đa giác đối tượng (`object polygon annotations`).
  - 231 chuỗi nhãn đối tượng thô (`raw object labels`).
  - 5.013 câu văn bản mô tả bối cảnh tổng quát (`one-line text descriptions`).
  - Nhãn phân loại cấp độ an toàn cấp hình ảnh (`safety_level`).
- **Tập dữ liệu HOÀN TOÀN KHÔNG CÓ:**
  - Bounding box gốc (`native bounding-box ground truth`).
  - Vùng bằng chứng nguy cơ an toàn chuyên biệt (`hazard evidence region`).
  - Vùng chú ý / giải thích lý do của con người (`human rationale region`).
  - Ánh xạ giữa cụm từ và vùng đa giác (`phrase-to-region alignment`).
  - Tọa độ cho các vi phạm thiếu vật thể (`absent-object coordinate annotation`).
  - Liên kết giữa đa giác và cấp độ an toàn (`evidence-to-safety-level mapping`).

> [!IMPORTANT]
> **Điểm mấu chốt:** Đa giác đối tượng **KHÔNG ĐỒNG NHẤT** với vùng bằng chứng nguy cơ (**Polygon Object Annotation $\neq$ Hazard Evidence GT**). Một đa giác bao quanh `Person` chỉ cho biết vị trí người đó, hoàn toàn không phải là Ground Truth trực tiếp chứng minh cho hành vi "công nhân không đội mũ bảo hộ".

### 10.2 Thẩm định Thực nghiệm trên Tập mẫu Phân tầng 63 Mẫu Anomaly

Khảo sát chuyên sâu trên tập mẫu phân tầng xác định gồm **63 mẫu Anomaly** (bao phủ 100% Anomaly metallurgy, 100% mẫu Level03, 13 mẫu exact duplicates, và đại diện 12 họ nguồn) ghi nhận:

- **Phân bố mức hỗ trợ của Polygon (Support Status):**
  - **`DIRECT_SUPPORT` (Hỗ trợ trực tiếp):** **13 / 63 mẫu (20,6% in the reviewed subset)** — Các nguy cơ gắn liền với vật thể hiện hữu có đa giác riêng (`Open Flame`, `Liquid`, `Smoke`, `Mobile Phone`, `Plastic Bag`).
  - **`PARTIAL_PROXY` (Hỗ trợ đại diện gián tiếp):** **46 / 63 mẫu (73,0% in the reviewed subset)** — Các vi phạm thiếu trang bị PPE (mũ, găng tay, khẩu trang) hoặc người ngã chỉ có thể bám gián tiếp qua đa giác `Person` toàn thân.
  - **`NO_DIRECT_SUPPORT` (Hoàn toàn không có hỗ trợ):** **3 / 63 mẫu (4,8% in the reviewed subset)** — Các mẫu cửa tủ điện mở bất thường (`dooropen`) hoàn toàn không có đa giác nào khoanh vùng chiếc tủ hay cánh cửa.
  - **`AMBIGUOUS` (Mơ hồ / Không thể ánh xạ):** **1 / 63 mẫu (1,6% in the reviewed subset)** — Mô tả "foreign object" nhưng không có quy ước nhãn rõ ràng.

*(Lưu ý bắt buộc: Mọi tỷ lệ trên chỉ có giá trị mô tả **trong tập 63 mẫu được thẩm định (in the 63-sample reviewed subset)**; tuyệt đối không tự ý ngoại suy sang toàn bộ 1.000 mẫu Anomaly của dataset).*

### 10.3 Phán quyết Khả thi về Grounding

1. **Object Support Grounding (Bám bằng chứng đối tượng hiện hữu):** **`FEASIBLE_WITH_CONSTRAINTS`** trên tập con đã xác minh. Bắt buộc W2 phải thực hiện tổng điều tra toàn diện (**full-dataset census**) trên 1.000 mẫu Anomaly để xác định quy mô chính xác của tập con có hỗ trợ đối tượng trực tiếp.
2. **Weak Proxy Grounding (Bám qua vùng đại diện yếu `Person`):** **`FEASIBLE_WITH_CONSTRAINTS`**. Khả thi nhưng bắt buộc phải công bố minh bạch đây là đánh giá qua Proxy yếu, không phạt mô hình nếu mô hình khoanh đúng vùng đầu của công nhân vi phạm không đội mũ.
3. **Full Hazard-Rationale Grounding (Bám lý do an toàn đầy đủ):** **`NOT_CURRENTLY_FEASIBLE`**. Hoàn toàn thiếu ground truth chuyên biệt trong dữ liệu gốc.
4. **Hiện tượng "Correct Answer, Wrong Reason":** **`NOT_CURRENTLY_FEASIBLE`** để đánh giá tự động và khách quan trên toàn bộ dataset nếu không có chiến dịch gán nhãn rationale bổ sung.

---

## 11. SafeShift Research Feasibility

Bảng tổng hợp phán quyết khả thi chính thức cho từng định hướng nghiên cứu của SafeShift:

| Định hướng Nghiên cứu | Phán quyết Khả thi (Verdict) | Căn cứ Thực chứng Cốt lõi (Core Reason) | Yêu cầu Bắt buộc cho W2 (W2 Requirement) |
|---|:---:|---|---|
| **Cross-Domain Analysis** *(Phân tích so sánh 5 miền)* | **`FEASIBLE_WITH_CONSTRAINTS`** | Tồn tại 5 miền công nghiệp rõ rệt với quy mô lớn (720–1.280 mẫu). | Báo cáo per-domain có kiểm soát yếu tố platform; xử lý 36 ca domain mismatch. |
| **Official Split as Clean DG Protocol** *(DG chuẩn trên split chính thức)* | **`NOT_CURRENTLY_FEASIBLE / NOT SUITABLE AS-IS`** | Official split bị rò rỉ 7 cặp exact confirmed và tương quan chuỗi; `metallurgy` có Test Anomaly = 0. | Chuyển sang Zero-shot Robustness trên mô hình frozen, hoặc dùng custom split. |
| **Custom Group-Aware DG Design** *(Thiết kế split mới kiểm soát nhóm)* | **`PARTIALLY_FEASIBLE`** | Khái niệm 5 miền độc lập về lý thuyết; có thể gom cụm cách ly 12 source families. | Thiết kế và thẩm định split mới tại W2, ghi nhận vào `DECISIONS.md`. |
| **Evidence Grounding with Existing Annotations** *(Grounding với nhãn có sẵn)* | **`PARTIALLY_FEASIBLE`** | Có 37.434 object polygon annotations (chú thích đa giác đối tượng); nhưng thiếu hoàn toàn nhãn bằng chứng lý do an toàn. | Giới hạn bài toán ở mức bám đối tượng liên quan (Object Support); không claim full grounding. |
| **Weak Proxy Grounding** *(Grounding qua vùng đại diện Person)* | **`FEASIBLE_WITH_CONSTRAINTS`** | 73,0% mẫu trong tập 63 mẫu khảo sát có thể dùng đa giác `Person` làm proxy cho lỗi PPE. | Chuẩn hóa giao thức đánh giá Proxy; ghi rõ hạn chế proxy trong báo cáo. |
| **Full Hazard-Specific Grounding** *(Grounding lý do an toàn chuyên sâu)* | **`NOT_CURRENTLY_FEASIBLE`** | InspecSafe-V1 hoàn toàn không có bounding box cho "vật thể bị thiếu" hoặc lý do chuyên gia. | Bắt buộc phải tổ chức chiến dịch gán nhãn bổ sung (Annotation Campaign) nếu muốn làm. |
| **SafeShift Seminar Overall** *(Tổng thể đề tài Seminar)* | **`FEASIBLE_WITH_CONSTRAINTS`** | Một real-world multimodal industrial safety benchmark (benchmark an toàn công nghiệp đa phương thức ngoài thực tế) phù hợp với phạm vi nghiên cứu SafeShift; giấy phép CC-BY-4.0 vững chắc. | Điều chỉnh phạm vi, mục tiêu và câu chữ học thuật phù hợp với thực chứng dữ liệu. |

---

## 12. Terminology to Carry into W2

Nhằm đảm bảo tính trung thực học thuật và sự chuẩn xác trong các báo cáo khoa học, SafeShift khuyến nghị quy chuẩn thuật ngữ mang sang W2:

1. **Giữ nguyên tiêu đề dự án:** Không tự ý thay đổi tiêu đề đề tài trong các tài liệu gốc ở Tuần 1.
2. **Quy chuẩn Thuật ngữ Đánh giá Xuyên Miền:**
   - **Nếu sử dụng mô hình VLM nền tảng cố định (Frozen Pretrained VLM)**, đánh giá Zero-shot / Few-shot không huấn luyện lại trên tập benchmark:  
     $\rightarrow$ Ưu tiên sử dụng: **`Cross-Domain Robustness Evaluation`** hoặc **`Zero-Shot Cross-Domain Evaluation`**.  
     *(Bởi vì không có quá trình tối ưu hóa trên source domain để "khái quát hóa" sang target domain theo định nghĩa học thuật chuẩn của Domain Generalization).*
   - **Nếu tiến hành huấn luyện / tinh chỉnh (fine-tuning, adapter tuning)** trên một tập hợp các miền nguồn và kiểm thử trên miền đích chưa từng thấy:  
     $\rightarrow$ Thuật ngữ **`Domain Generalization (DG)`** là hoàn toàn phù hợp.
3. **Quy chuẩn Thuật ngữ Bám Bằng chứng (Grounding):**
   - Thay vì dùng thuật ngữ rộng và lý tưởng hóa *Full Evidence Grounding*, hệ thống chú thích đối tượng hiện có của InspecSafe-V1 phù hợp nhất với các thuật ngữ:  
     $\rightarrow$ **`Evidence Support`**, **`Object-Support Grounding`**, hoặc **`Weak-Proxy Grounding`**.

---

## 13. Unresolved Questions

Các vấn đề mở chưa thể giải quyết bằng dữ liệu cục bộ và cần chuyển giao nguyên trạng sang W2:

1. **Ánh xạ 2.239 Sites chính thức vs. 3.234 Point Folders cục bộ:** Upstream không cung cấp tệp ánh xạ chi tiết; các giả thuyết về repeat visits hay tách split vẫn là phỏng đoán.
2. **Khoảng cách 234 Lớp công bố vs. 231 Nhãn thô thực tế:** 3 lớp bị thiếu trong 5.013 ảnh chưa rõ danh tính; SafeShift kiên quyết không tự chuẩn hóa để ép khớp.
3. **Chính sách xử lý 36 Mẫu Xung đột Miền (`folder_domain != text_domain`):** Cần quyết định loại bỏ, phân loại lại hay gắn cờ cảnh báo rủi ro nhạy cảm.
4. **Quy tắc Gom nhóm (Grouping Policy) tại W2:** Thống nhất cách thức gom nhóm mẫu để ngăn chặn rò rỉ khi đánh giá (gom theo point ID, hay gom triệt để theo 12 source families).
5. **Bản chất Họ Nguồn Heuristic vs. Định danh Video Thật:** Chưa có metadata video ID chính thức từ tác giả để xác định ranh giới video tuyệt đối cho toàn bộ 1.000 mẫu Anomaly.
6. **Quy mô Tập con Direct Object-Support trên Toàn bộ Dataset:** Cần một cuộc điều tra toàn diện (census) trên 1.000 mẫu Anomaly để xác định chính xác số mẫu có vật thể nguy cơ hiện hữu.
7. **Kế hoạch Gán nhãn Bổ sung (Manual Rationale Annotation):** Quyết định xem SafeShift có tự tổ chức gán nhãn bounding box lý do an toàn cho 100–200 mẫu mẫu mực hay không.
8. **Rủi ro Nhiễm Dữ liệu Tiền Huấn luyện (Pretraining Contamination):** Các mô hình VLM phát hành sau tháng 04/2026 có thể đã thấy InspecSafe-V1 trong tập huấn luyện mở rộng; cần kiểm tra training cutoff.
9. **Tính Tương đương Nội dung giữa Zenodo `test.tar` và Hugging Face `test.tar.gz`:** Chưa thực hiện hash và giải nén đối chiếu chéo giữa hai kho lưu trữ.
10. **Chính sách Xử lý Miền Luyện kim (`metallurgy`) làm Miền Đích:** Quyết định loại bỏ `metallurgy` khỏi vai trò primary target domain trong đánh giá bất thường do có 0 mẫu Anomaly ở test chính thức.

---

## 14. Required Decisions for W2 (Decision Queue)

Hàng đợi 10 quyết định phương pháp luận bắt buộc phải được Nhóm Nghiên cứu thảo luận, phê duyệt và ghi nhận chính thức vào `DECISIONS.md` trước khi tiến hành thực nghiệm ở W2:

- **[D1] Giao thức Đánh giá Xuyên Miền (Cross-Domain Protocol):** Chốt lựa chọn giữa Zero-shot Pretrained VLM Robustness (5 miền) hay Leave-One-Domain-Out DG (trên 4 miền khả thi, loại trừ target metallurgy).
- **[D2] Phân chia Dữ liệu (Split Policy):** Chốt việc giữ nguyên Official Split (kèm báo cáo hạn chế) hay ban hành SafeShift Group-aware Clean Split độc lập.
- **[D3] Định nghĩa Miền và Xử lý 36 Mẫu Mismatch:** Quy định nguồn nhãn chuẩn cho miền công nghiệp và cách thức xử lý 36 mẫu xung đột.
- **[D4] Định dạng Đầu ra Grounding của Mô hình (Model Output Interface):** Chuẩn hóa giao diện đầu ra (bounding box tọa độ văn bản `[x1, y1, x2, y2]`, điểm trỏ pointing center, hay heat map) trước khi đo đạc.
- **[D5] Lựa chọn Họ Chỉ số Đánh giá Ứng viên (Candidate Metric Selection):** Lựa chọn và phê duyệt công thức tính toán (Pointing Game, Soft IoU, Balanced Accuracy, Macro-F1).
- **[D6] Tổng Điều tra Toàn diện Tập Direct Support (Full Direct-Support Census):** Phê duyệt kế hoạch rà soát toàn bộ 1.000 mẫu Anomaly để phân lập tập Direct Support.
- **[D7] Chiến dịch Gán nhãn Rationale Bổ sung (Optional Rationale Annotation Campaign):** Quyết định có triển khai gán nhãn thủ công vùng lý do an toàn cho 100 mẫu chuẩn hay không.
- **[D8] Kiểm soát Mốc Thời gian Huấn luyện Mô hình (Pretraining Cutoff Tracking):** Thiết lập quy trình tra cứu và ghi nhận mốc cutoff dữ liệu của các mô hình VLM tham gia benchmark.
- **[D9] Danh mục Mô hình VLM Cơ sở (Baseline Model Selection):** Lựa chọn các mô hình mã nguồn mở và API thương mại cụ thể sẽ chạy thử nghiệm tại W3.
- **[D10] Giao thức Lưu trữ Đầu ra Thô (Raw Model Output Protocol):** Thiết lập cấu trúc lưu trữ và serialization cho toàn bộ raw API/model responses trước khi phân tích điểm.

*(Lưu ý: Tuân thủ quy tắc Week 1, tài liệu `DECISIONS.md` được giữ nguyên làm template và KHÔNG bị sửa đổi ở bước này).*

---

## 15. Reproducibility

### 15.1 Môi trường Kiểm toán Đã xác minh

- **Hệ điều hành:** Windows 10/11 x64 (Build 10.0.26200).
- **Python Runtime:** Python 3.11.9 (sử dụng thư viện chuẩn và môi trường ảo `.venv`).
- **Thư viện Kiểm toán Hình ảnh:** `Pillow==12.3.0` (theo `requirements-validation.txt`), libjpeg `8.0`, zlib `1.3.1.zlib-ng`.
- **Dấu vân tay dữ liệu đầu vào (Input Fingerprint):**  
  `1a52f9078d53bddcdcd8400486a6e22f7688c8c20dc85b481b128f94c723399c`

### 15.2 Các Lệnh Tái lập Kiểm toán Chính thức

Từ repository root trong PowerShell:

1. **Khởi tạo môi trường ảo và cài đặt dependency kiểm toán:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements-validation.txt
   ```
2. **Chạy bộ kiểm thử tự động (Regression Tests):**
   ```powershell
   python -m unittest discover -v
   ```
   *Kết quả thực tế đo được:* **145/145 unit tests PASS (0 failed, 0 error)** trong 4,39 giây.
3. **Xây dựng Dataset Manifest (Bước 2):**
   ```powershell
   python scripts/build_manifest.py --dataset-root data/raw/InspecSafe-V1 --output data/manifests/dataset_manifest.csv
   ```
4. **Kiểm định Tính Toàn vẹn và Schema Dataset (Bước 3):**
   ```powershell
   python scripts/validate_dataset.py --dataset-root data/raw/InspecSafe-V1 --output data/manifests/dataset_validation.json --verify-image-data
   ```
5. **Kiểm toán Trùng lặp và Nguy cơ Rò rỉ Split (Bước 4):**
   ```powershell
   python scripts/audit_duplicates.py --dataset-root data/raw/InspecSafe-V1 --output data/manifests/duplicate_leakage_audit.json --max-hamming 8
   ```
6. **Kiểm toán Phân bố và Mất cân bằng Dữ liệu (Bước 6):**
   ```powershell
   python scripts/audit_distribution.py --dataset-root data/raw/InspecSafe-V1 --output data/manifests/distribution_imbalance_audit.json
   ```
7. **Tạo các Biểu đồ Thống kê Dẫn xuất (Bước 9):**
   ```powershell
   python scripts/plot_w1_audit_figures.py --output-dir outputs/figures
   ```

### 15.3 Danh mục Artifacts Cục bộ Được Giữ Lại (Not Committed)

Theo đúng quy tắc quản trị dữ liệu của SafeShift và `.gitignore`, các artifact kiểm toán chi tiết dưới đây chứa danh sách hàng nghìn mã mẫu, văn bản TXT thô và metadata upstream nên được **lưu trữ cục bộ, không commit lên Git**:

- `data/manifests/dataset_manifest.csv` (4.290.785 bytes)  
  *SHA-256:* `3025edb985d947cbcfe3e397b37aed505e2305b32ece46663d46115c28568577`
- `data/manifests/dataset_validation.json` (4.834.176 bytes)  
  *SHA-256:* `f5556fe1f48d85652577e6416d7f11639be8aa1a4797f1c4fe10c10befc62117`
- `data/manifests/duplicate_leakage_audit.json` (16.747.562 bytes)  
  *SHA-256:* `16039f2302027ffe53f3bcdbfc80c762c88e823fbf303d5672030587cd9602d6`
- `data/manifests/distribution_imbalance_audit.json` (433.209 bytes)  
  *SHA-256:* `2dbb706c3975dc633d12d4a0ac71f48731b1fcb3e9885c752142d09eab1d5492`
- `data/manifests/research_feasibility_sample.json` (Danh mục 63 mẫu phân tầng phục vụ kiểm toán feasibility).

### 15.4 Danh mục Biểu đồ Dẫn xuất Được Phép Chia sẻ (Committed Figures)

Các biểu đồ nhỏ dạng vector/bitmap dẫn xuất từ số liệu kiểm chứng đã được lưu trong `outputs/figures/`:
1. `outputs/figures/w1_domain_distribution.png` (32,8 KB): Phân bố số lượng mẫu Normal vs. Anomaly trên 5 miền công nghiệp.
2. `outputs/figures/w1_safety_distribution.png` (32,0 KB): Biểu đồ cột thể hiện mức độ mất cân bằng cực đoan của 4 cấp độ an toàn (Level 01–04).
3. `outputs/figures/w1_platform_by_domain.png` (31,1 KB): Phân bố nền tảng robot (SuspendedRail vs. Wheeled) trên 5 miền công nghiệp, minh họa yếu tố nhiễu nền tảng.

---

## 16. W1 Gate Review Summary & Status

Đánh giá điều kiện chuyển giai đoạn W1 $\rightarrow$ W2 theo quy chuẩn tại [ROADMAP.md](../ROADMAP.md):
- [x] Có báo cáo kiểm toán dữ liệu hoàn chỉnh, có thể truy vết nguồn gốc và số liệu rõ ràng.
- [x] Có danh sách đầy đủ các vấn đề kỹ thuật chưa rõ (`Unresolved Questions`) và các hạn chế dữ liệu.
- [x] Có phán quyết thực chứng về khả năng hỗ trợ nghiên cứu Cross-Domain và Evidence Grounding của dataset.
- [x] Có hàng đợi quyết định phương pháp luận (`Decision Queue`) chuẩn bị cho Week 2.
- [x] Toàn bộ mã kiểm toán có kiểm thử tương ứng; 145/145 unit tests pass hoàn toàn.
- [x] Nguyên tắc toàn vẹn dữ liệu được bảo tồn tuyệt đối: không sửa raw data, không train model, không chạy VLM, không đổi split/nhãn ở W1.

```text
================================================================================
                    W1 GATE REVIEW STATUS: READY_FOR_REVIEW
================================================================================
Gói tài liệu kiểm toán Week 1 đã hoàn thiện đầy đủ, minh bạch và nhất quán.
Sẵn sàng cho Research Lead / Hội đồng bình duyệt độc lập trước khi mở giao thức W2.
================================================================================
```
