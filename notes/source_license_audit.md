# Source & License Audit: InspecSafe-V1

Tài liệu này ghi nhận kết quả xác minh toàn diện nguồn gốc, giấy phép bản quyền, điều kiện pháp lý và tài liệu phát hành chính thức của tập dữ liệu **InspecSafe-V1** trong khuôn khổ Week 1 (Dataset Audit — Bước 7) của dự án SafeShift (cập nhật trạng thái ngày 15/09/2026).

Tất cả các thông tin được kiểm chứng chéo trực tiếp từ các nguồn chính thống: Tạp chí Scientific Data (Nature Publishing Group), máy chủ bản thảo arXiv, Hugging Face Hub API, Zenodo DOI API, GitHub repository chính thức của tác giả và hệ thống tệp siêu dữ liệu cục bộ.

---

## 1. Scope (Phạm vi xác minh)

Phạm vi của đợt audit này bao gồm:
1. **Định danh chính thức:** Tên gọi chuẩn, các tổ chức và nhóm nghiên cứu đứng sau InspecSafe-V1.
2. **Bài báo khoa học gắn liền:** Xác định ấn phẩm chính thức (Version of Record) trên tạp chí chuyên ngành và bản thảo lưu trữ (Preprint).
3. **Kênh phát hành chính thức:** Xác minh project page, GitHub repo, Hugging Face dataset repo và kho lưu trữ trường tồn Zenodo.
4. **Phân tích giấy phép (License Audit đa tầng):** Bóc tách độc lập giấy phép của mã nguồn (Code License), dữ liệu thị giác & cảm biến (Dataset License), và ấn phẩm học thuật (Paper Copyright cho cả bản tạp chí và bản preprint).
5. **Ma trận quyền hạn sử dụng (Rights Matrix):** Đánh giá các hoạt động học thuật của SafeShift (seminar, luận văn, công bố manifest, huấn luyện mô hình, sử dụng ảnh minh họa), phân định rạch ròi giữa quyền pháp lý (legal permissions) và chính sách nội bộ dự án (project policies).
6. **Truy nguyên nguồn gốc cục bộ (Local Acquisition Provenance):** Tách bạch giữa bản sao lưu cục bộ (`SafeShift.zip`), dấu vân tay nội bộ (`fingerprint`), và mức độ đối soát với tệp phát hành chính thức của tác giả.
7. **Quyền riêng tư và độ nhạy cảm công nghiệp:** Rà soát các tuyên bố đạo đức, ẩn danh hóa (anonymization) và an ninh cơ sở hạ tầng.
8. **Đối soát sai lệch tài liệu (Reconciliation):** Nhận diện khoảng cách giữa tài liệu công bố chính thức và kết quả kiểm toán cục bộ về số lượng waypoint và danh mục nhãn.

---

## 2. Official Dataset Identity (Định danh chính thức)

- **Tên chính thức:** `InspecSafe-V1` (viết tắt của *Inspection Safety Benchmark - Version 1*).
- **Mục đích thiết kế:** Bộ tiêu chuẩn đa phương thức đầu tiên phục vụ đánh giá mức độ an toàn và xây dựng mô hình thế giới (world model) trong các kịch bản kiểm tra an toàn công nghiệp bằng robot tự hành.
- **Quy mô khảo sát theo tài liệu công bố:**
  - 41 robot tuần tra (dạng bánh lăn Wheeled và ray treo Suspended-Rail).
  - 2.239 điểm kiểm tra thực tế (inspection waypoints/sites) tại hiện trường.
  - 5.013 phiên bản mẫu quan sát (inspection instances) với ảnh RGB, mặt nạ phân vùng đa giác pixel-level, mô tả ngôn ngữ và nhãn mức độ an toàn (Level I đến Level IV).
  - 5 kịch bản công nghiệp đại diện: Đường hầm (tunnels), cơ sở lưới điện (power facilities), khu vực thiêu kết / luyện kim (sintering equipment), nhà máy dầu khí hóa chất (oil & gas plants), và hành lang băng tải than (coal conveyor trestles).
  - 7 phương thức cảm biến đồng bộ: Video ánh sáng khả kiến (Visible-light RGB), video hồng ngoại nhiệt (Infrared/Thermal), âm thanh môi trường (Audio .wav), đám mây điểm 3D (Depth / LiDAR .bag), nồng độ khí gas, nhiệt độ và độ ẩm (.txt).
- **Tổ chức chủ quản / Tác giả phát hành:**
  - **Khoa Tự động hóa & Viện Trí tuệ Hiện thân và Robot, Đại học Thanh Hoa** (*Department of Automation & Institute for Embodied Intelligence and Robotics, Tsinghua University*), Bắc Kinh, Trung Quốc.
  - **Công ty TNHH Trí tuệ TetraBOT** (*TetraBOT Intelligence Co., Ltd.*) — đơn vị tài trợ, cung cấp nền tảng robot tuần tra công nghiệp và phối hợp thu thập dữ liệu.
  - **Viện Đạt Ma, Tập đoàn Alibaba** (*DAMO Academy, Alibaba Group*).
  - **Đại học Đông Nam** (*Southeast University*), Nam Kinh, Trung Quốc.
- **Tài trợ nghiên cứu (Funding Grants):**
  - Quỹ Khoa học Tự nhiên Quốc gia Trung Quốc (NSFC Grants: 62525308, 624B2087, 62473223, 52172323).
  - Quỹ Khoa học Tự nhiên Thành phố Bắc Kinh (Grant: L241016).

---

## 3. Associated Paper (Bài báo khoa học gốc)

Tình trạng xuất bản khoa học gắn liền với InspecSafe-V1 tính đến ngày 15/09/2026:

### A. Version of Record (Ấn phẩm tạp chí chính thức)
- **Tạp chí (Journal):** *Scientific Data* (thuộc Nature Portfolio / Springer Nature).
- **Tiêu đề (Title):** *Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios*
- **Tác giả (Authors):** Zeyi Liu, Shuang Liu, Jihai Min, Zhaoheng Zhang, Jun Cen, Pengyu Han, Songqiao Hu, Zihan Meng, Xiao He, Donghua Zhou.
- **Tập / Số / Mã bài (Citation details):** Volume 13, Article number: 1198 (2026).
- **Ngày xuất bản chính thức:** 17/08/2026.
- **DOI bài báo chính thức:** [10.1038/s41597-026-07796-x](https://doi.org/10.1038/s41597-026-07796-x).
- **URL chính thức:** `https://www.nature.com/articles/s41597-026-07796-x`.
- **Tác giả liên hệ (Corresponding Author):** Giáo sư Xiao He (Khoa Tự động hóa, Đại học Thanh Hoa, Email: `hexiao@tsinghua.edu.cn`).

### B. Preprint Archive (Bản thảo lưu trữ)
- **Máy chủ bản thảo (Server):** arXiv (`cs.RO` — Robotics; `cs.CV` — Computer Vision and Pattern Recognition).
- **Định danh arXiv:** [arXiv:2601.21173](https://arxiv.org/abs/2601.21173) (phiên bản v1 nộp 27/01/2026; phiên bản v2 cập nhật 29/04/2026).
- **Preprint DOI:** `10.48550/arXiv.2601.21173`.
- **Vai trò:** Bản lưu trữ lịch sử phát triển của bài báo; không còn được coi là địa điểm công bố (venue) cuối cùng sau khi bài báo đã hoàn tất bình duyệt và xuất bản trên *Scientific Data*.

---

## 4. Official Release & Download Sources (Nguồn phát hành chính thức)

Dữ liệu InspecSafe-V1 được phát hành chính thức song song qua hai kênh lưu trữ mở:

### A. Hugging Face Datasets Hub
- **URL chính thức:** `https://huggingface.co/datasets/Tetrabot2026/InspecSafe-V1`
- **Chủ sở hữu / Tổ chức:** `Tetrabot2026` (TetraBOT Intelligence).
- **ID kho lưu trữ:** `Tetrabot2026/InspecSafe-V1`
- **Trạng thái truy cập:** `PUBLIC / OPEN ACCESS` (Không yêu cầu cấp phép riêng, không gated, không token bí mật).
- **Mã định danh Git Commit (Snapshot SHA):** `f3cb7d3e7827c1afc1c5bfd0524257984bba46ab` (ngày 30/04/2026).
- **Dung lượng lưu trữ công bố:** ~41,5 GB (tổng dung lượng lưu trữ kho).
- **Danh mục tệp phát hành:**
  1. `README.md` (Dataset Card theo chuẩn Hugging Face).
  2. `dataset_loader.py` (Mã nguồn PyTorch DataLoader).
  3. `model_api_generate_results.py` (Script gửi yêu cầu suy luận API đến VLM).
  4. `model_benchmark_evaluation.py` (Script đo lường cosine similarity embedding văn bản qua BGE-M3).
  5. `model_confusion_matrix.py` (Script trực quan hóa ma trận nhầm lẫn 4 cấp độ an toàn).
  6. `train.tar.gz` (Archive nén chứa dữ liệu tập huấn luyện).
  7. `test.tar.gz` (Archive nén chứa dữ liệu tập kiểm thử).

### B. Kho lưu trữ khoa học Zenodo (CERN)
- **URL chính thức:** `https://zenodo.org/records/19885643`
- **DOI định danh trường tồn:** [10.5281/zenodo.19885643](https://doi.org/10.5281/zenodo.19885643) (Concept DOI gom phiên bản: `10.5281/zenodo.19885642`).
- **Trạng thái truy cập:** `Open Access`.
- **Ngày phát hành xuất bản:** 30/04/2026.
- **Tệp công bố trên Zenodo:**
  - `train.tar.gz`: 17.886.855.594 bytes (~17,89 GB).
  - `test.tar`: 6.199.326.720 bytes (~6,20 GB).

### C. Kho mã nguồn GitHub
- **URL chính thức:** `https://github.com/liuzy0708/InspecSafe`
- **Chủ sở hữu (Owner):** `liuzy0708` (Zeyi Liu — tác giả chính).
- **Nội dung:** Chứa các tệp mã nguồn kiểm tra benchmark, hướng dẫn sử dụng và trích dẫn khoa học.

---

## 5. Version Information (Thông tin phiên bản)

- **Phiên bản hiện tại:** `InspecSafe-V1` (được gắn nhãn phiên bản `v1.0.1` trong hồ sơ siêu dữ liệu chính thức của Zenodo).
- **Khảo sát phiên bản tiếp theo:**
  - Không có bằng chứng về việc tồn tại `InspecSafe-V2` hoặc bản phát hành sửa đổi nhãn bổ sung tại thời điểm kiểm tra (tháng 09/2026).
  - Kho mã nguồn GitHub và Hugging Face Hub đang ở trạng thái stable release khớp với phiên bản bài báo chính thức trên Scientific Data (tháng 08/2026).
- **Quy tắc dự án SafeShift:** Giữ nguyên và làm việc với bản phát hành chuẩn `InspecSafe-V1` (phiên bản snapshot commit `f3cb7d3e`), không tự ý thay đổi cấu trúc dữ liệu hoặc chuyển dịch phiên bản.

---

## 6. License Evidence (Bằng chứng giấy phép bản quyền)

Phân tích độc lập giấy phép theo từng tầng tài nguyên để tránh đánh đồng hoặc suy diễn sai lệch phạm vi pháp lý:

### A. Dataset License (Giấy phép dữ liệu)
- **Tình trạng xác minh:** `VERIFIED`
- **Giấy phép chính thức:** **Creative Commons Attribution 4.0 International (CC-BY-4.0)**
- **Bằng chứng văn bản:**
  1. *Hugging Face Dataset Card Metadata (YAML Frontmatter):*
     ```yaml
     license: cc-by-4.0
     ```
  2. *Tệp README.md gốc phát hành kèm dataset:*
     > *"This dataset is released under the CC-BY-4.0 License (https://creativecommons.org/licenses/by/4.0/)."*
  3. *Zenodo Record Metadata & Rights:*
     Khai báo trường `"license": {"id": "cc-by-4.0"}` và trích dẫn điều khoản pháp lý tại `https://creativecommons.org/licenses/by/4.0/legalcode`.
- **Phạm vi áp dụng của CC-BY-4.0:** Áp dụng cho toàn bộ các tệp tài nguyên dữ liệu phân phối trong kho, bao gồm:
  - Tệp ảnh quang học RGB (`.jpg`).
  - Tệp nhãn phân vùng đa giác LabelMe JSON (`.json`).
  - Tệp mô tả ngữ nghĩa hiện trường (`.txt`).
  - Tệp video đa phương thức khả kiến và hồng ngoại nhiệt (`.mp4`).
  - Tệp dữ liệu cảm biến môi trường (`.txt`).
  - Tệp âm thanh (`.wav`) và dữ liệu đám mây điểm ROS bag (`.bag`).
  - Tệp tham số cấu hình phần cứng robot (`.json` trong thư mục `Parameters/`).
- **Lưu ý pháp lý:** CC-BY-4.0 cho phép chia sẻ (sao chép, phân phối) và chuyển thể (phối lại, biến đổi, xây dựng phái sinh) cho mọi mục đích (kể cả thương mại), với điều kiện tiên quyết duy nhất là **Attribution (Ghi nhận nguồn tác giả)** hợp lý. Câu chữ *"The dataset is intended for research use"* trong README GitHub chỉ là thông cáo về mục đích thiết kế của tác giả, **không cấu thành điều khoản cấm thương mại (NonCommercial)** về mặt pháp lý của giấy phép CC-BY-4.0.

### B. Code License (Giấy phép mã nguồn)
- **Tình trạng xác minh:** `RESTRICTED / NOT_SPECIFIED (Standalone)`
- **Bằng chứng văn bản:**
  - Trên GitHub repo `liuzy0708/InspecSafe` và trong các tệp Python (`dataset_loader.py`, `model_api_generate_results.py`,...), tác giả **không đính kèm tệp LICENSE độc lập** chuẩn OSI (như Apache-2.0 hay MIT).
  - Tuyên bố sử dụng trong mục `Usage Notes` của GitHub README ghi:
    > *"The dataset is intended for research use. Redistribution, modification, and derivative works are permitted under the dataset’s stated usage terms, with proper citation required."*
  - Trên Hugging Face, toàn bộ kho lưu trữ chứa cả code lẫn data đều được đặt dưới tag giấy phép chung `cc-by-4.0`.
- **Diễn giải pháp lý:** Mã nguồn script đi kèm không có giấy phép phần mềm độc lập. SafeShift chỉ tham khảo logic kiểm tra, không sao chép nguyên khối mã nguồn tác giả thành thư viện riêng khi chưa có license phần mềm tường minh.

### C. Paper Copyright & License (Bản quyền và giấy phép bài báo)
Cần tách biệt rạch ròi giữa bản tạp chí chính thức và bản preprint lưu trữ:

1. **Scientific Data (Version of Record):**
   - **Giấy phép:** **Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0)**.
   - **Phạm vi ràng buộc:** Áp dụng cho bài viết xuất bản trên *Scientific Data*, bao gồm văn bản bài báo, bố cục biên tập, và **các hình vẽ/biểu đồ (figures) thuộc ấn phẩm**.
   - **Hạn chế nghiêm ngặt:** Cấm sử dụng vì mục đích thương mại (NonCommercial) và cấm phân phối tác phẩm chuyển thể/sửa đổi (NoDerivatives).
2. **arXiv Preprint:**
   - **Giấy phép:** **arXiv Non-exclusive Distribution License** (`http://arxiv.org/licenses/nonexclusive-distrib/1.0/`).
   - **Bản quyền sở hữu trí tuệ:** Thuộc về nhóm tác giả. Tác giả cấp quyền phân phối vĩnh viễn phi độc quyền cho arXiv.

---

## 7. Rights Matrix (Ma trận quyền hạn sử dụng)

Bảng phân định quyền hạn chi tiết cho từng hạng mục hoạt động nghiên cứu của SafeShift, phân biệt rạch ròi giữa **Quyền pháp lý theo License** và **Chính sách nội bộ SafeShift**:

| Hoạt động (Item) | Verified? | Bằng chứng (Evidence) | Diễn giải quy tắc SafeShift (Interpretation) |
|---|---|---|---|
| **Academic research use** | **ALLOWED** | Tuyên bố rõ ràng trong README, Zenodo, Hugging Face và Paper: "intended for research use", CC-BY-4.0. | SafeShift được phép hoàn toàn sử dụng dữ liệu để thực hiện nghiên cứu, phân tích benchmark, phục vụ môn Seminar và Luận văn tốt nghiệp. |
| **Commercial use** | **ALLOWED (Legal) / RESTRICTED (Policy)** | Giấy phép Dataset chính thức là CC-BY-4.0 (cho phép thương mại với attribution). README ghi "intended for research use" nhưng không có điều khoản cấm thương mại. | **Về mặt pháp lý:** ALLOWED dưới CC-BY-4.0.<br>**Chính sách SafeShift:** RESTRICTED — Dự án SafeShift là nghiên cứu học thuật phi thương mại thuần túy, tự nguyện tuân thủ định hướng nghiên cứu của tác giả. |
| **Modification / Derivative works** | **ALLOWED** | Điều khoản CC-BY-4.0: "Adapt — remix, transform, and build upon the material for any purpose". README: "Redistribution, modification, and derivative works are permitted". | Được phép tạo dữ liệu dẫn xuất, lọc manifest, tính toán chỉ số thống kê, ánh xạ lại danh mục nhãn phân loại an toàn. |
| **Redistribution raw dataset / images** | **ALLOWED (Legal) / PROHIBITED (Policy)** | Điều khoản CC-BY-4.0 cho phép phân phối lại tài liệu ở mọi phương tiện nếu ghi công hợp lý. | **Về mặt pháp lý:** ALLOWED dưới CC-BY-4.0.<br>**Chính sách SafeShift:** `DO_NOT_REDISTRIBUTE_RAW_DATA` — Dự án SafeShift tuyệt đối KHÔNG commit/upload lại raw dataset thô (23+ GB) lên GitHub; người dùng phải tải từ kênh chính thức của tác giả. |
| **Redistribution annotations** | **ALLOWED** | Thuộc phạm vi chuyển thể/phân phối phái sinh theo CC-BY-4.0 kèm ghi công tác giả. | Được phép công bố các chú thích bổ sung hoặc tập nhãn đã làm sạch do SafeShift phát triển, có dẫn nguồn InspecSafe-V1. |
| **Redistribution text descriptions** | **ALLOWED** | Thuộc phạm vi dữ liệu văn bản theo CC-BY-4.0 kèm ghi công tác giả. | Được phép sử dụng cho prompt engineering và benchmark đánh giá VLM. |
| **Publishing sample images in paper/slides** | **ALLOWED / RESTRICTED (Tùy nguồn ảnh)** | Xem phân định nguồn chi tiết tại Mục 10. | - Nếu lấy trực tiếp từ Dataset asset: **ALLOWED** theo CC-BY-4.0 kèm attribution.<br>- Nếu sao chép / chụp lại Figures từ bài báo *Scientific Data*: **RESTRICTED** theo CC BY-NC-ND 4.0 (không thương mại, không phái sinh). |
| **Publishing derived manifests** | **ALLOWED** | Tạo lập siêu dữ liệu phái sinh (CSV/JSON manifest) phục vụ tái lập nghiên cứu khoa học. | Được phép đưa vào repository nếu manifest chỉ chứa relative path, nhãn, tọa độ bounding box hoặc metadata; **tuyệt đối không nhúng chuỗi Base64 `imageData`**. |
| **Publishing aggregate statistics** | **ALLOWED** | Kết quả phân tích thống kê, phân bố dữ liệu, ma trận mất cân bằng domain là sản phẩm nghiên cứu độc lập. | Được phép công bố đầy đủ trong báo cáo khoa học SafeShift. |
| **Publishing trained model weights** | **NOT_SPECIFIED / REQUIRES SEPARATE REVIEW** | Giấy phép dataset CC-BY-4.0 cho phép tạo dẫn xuất, nhưng việc công bố weights phụ thuộc vào nhiều yếu tố khác ngoài dataset. | **Chưa thể kết luận ALLOWED đơn thuần từ dataset license.** Việc công bố trọng số mô hình còn phụ thuộc vào: (1) Giấy phép của Base VLM (ví dụ Llama Community License, Qwen License), (2) Điều khoản dịch vụ của API/Provider nếu có chưng cất, (3) Kiến trúc huấn luyện cụ thể. Cần đánh giá riêng ở W2. |
| **Attribution requirement** | **ALLOWED (Mandatory)** | Điều kiện cốt lõi của CC-BY-4.0: "You must give appropriate credit, provide a link to the license, and indicate if changes were made". | **BẮT BUỘC**: Mọi báo cáo, slide, mã nguồn hay bài báo phát sinh từ SafeShift phải trích dẫn bài báo chính thức (*Scientific Data*) và trang dataset InspecSafe-V1. |

---

## 8. Citation (Trích dẫn khoa học chính thức)

Trích dẫn chính thức ưu tiên sử dụng ấn phẩm tạp chí chính thức (*Version of Record*):

```bibtex
@article{liu2026inspecsafe_scidata,
  title   = {Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios},
  author  = {Liu, Zeyi and Liu, Shuang and Min, Jihai and Zhang, Zhaoheng and Cen, Jun and Han, Pengyu and Hu, Songqiao and Meng, Zihan and He, Xiao and Zhou, Donghua},
  journal = {Scientific Data},
  volume  = {13},
  number  = {1},
  pages   = {1198},
  year    = {2026},
  month   = aug,
  doi     = {10.1038/s41597-026-07796-x},
  url     = {https://doi.org/10.1038/s41597-026-07796-x}
}
```

Trích dẫn bản kho lưu trữ dữ liệu Zenodo có DOI:

```bibtex
@dataset{liu_2026_inspecsafe_zenodo,
  author       = {Liu, Zeyi and Liu, Shuang and Min, Jihai and Zhang, Zhaoheng and Cen, Jun and Han, Pengyu and Hu, Songqiao and Meng, Zihan and He, Xiao and Zhou, Donghua},
  title        = {Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios},
  month        = apr,
  year         = 2026,
  publisher    = {Zenodo},
  version      = {1.0.1},
  doi          = {10.5281/zenodo.19885643},
  url          = {https://doi.org/10.5281/zenodo.19885643}
}
```

Trích dẫn bản lưu trữ Preprint (lịch sử phát triển):

```bibtex
@misc{liu2026inspecsafe_arxiv,
  title        = {InspecSafe-V1: A Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios},
  author       = {Zeyi Liu and Shuang Liu and Jihai Min and Zhaoheng Zhang and Jun Cen and Pengyu Han and Songqiao Hu and Zihan Meng and Xiao He and Donghua Zhou},
  year         = {2026},
  eprint       = {2601.21173},
  archivePrefix= {arXiv},
  primaryClass = {cs.RO},
  doi          = {10.48550/arXiv.2601.21173},
  note         = {Preprint}
}
```

---

## 9. Local Acquisition Provenance (Truy nguyên nguồn gốc dữ liệu cục bộ)

Cần phân định rạch ròi giữa tệp sao lưu nội bộ của máy trạm cá nhân và bản phát hành gốc của tác giả:

- **Phương thức khôi phục trên máy trạm hiện tại:**
  - Dữ liệu phục vụ kiểm toán được khôi phục từ tệp lưu trữ nội bộ:
    ```text
    D:\SafeShift.zip
    ```
  - Giải nén vào không gian làm việc cục bộ:
    ```text
    D:\SafeShift\data\raw\InspecSafe-V1
    ```
- **Dấu vân tay nội dung (Dataset Content Fingerprint):**
  - Giá trị băm SHA-256 đã xác minh xuyên suốt các bước kiểm định W1 (Manifest, Validation, Leakage, Distribution):
    ```text
    1a52f9078d53bddcdcd8400486a6e22f7688c8c20dc85b481b128f94c723399c
    ```
  - **Ý nghĩa kỹ thuật:** Dấu vân tay này khẳng định tính đồng nhất 100% của cấu trúc và nội dung các tệp mẫu (`.jpg`, `.json`, `.txt`) giữa lần chạy kiểm kê hiện tại và bản audit trước đó trên máy trạm.
  - **Lưu ý pháp lý & học thuật:** Dấu vân tay nội bộ **KHÔNG** chứng minh danh tính của archive thượng nguồn (upstream archive identity), không thay thế checksum phát hành của nhà xuất bản, và không chứng minh nguồn gốc pháp lý độc lập.

- **Đối soát với bản phát hành thượng nguồn (Upstream Archive Checksum Qualification):**
  Trong thư mục `data/raw/InspecSafe-V1`, hai tệp nén gốc đi kèm gồm:
  - `train.tar.gz`: Kích thước tệp cục bộ là **17.886.855.594 bytes** (~17,89 GB).
    - Khớp kích thước khai báo trên Hugging Face LFS: `17.886.855.594 bytes`.
    - Khớp kích thước khai báo trên Zenodo API: `17.886.855.594 bytes`.
    - Checksum công bố thượng nguồn:
      - MD5 (Zenodo API): `a2b84da421c32a67b025240ad4365048`
      - Git LFS SHA256 (HF cache metadata): `ef03b9eb2f9bd91b03f203a8e6cfcc3464cb0d9f0215349a80ad95281fa88cd6`
  - `test.tar.gz`: Kích thước tệp cục bộ là **5.748.799.871 bytes** (~5,75 GB).
    - Khớp kích thước khai báo trên Hugging Face LFS: `5.748.799.871 bytes`.
    - Checksum công bố thượng nguồn:
      - Git LFS SHA256 (HF cache metadata): `818086e696f970e036bf6a76758e4fb851fa26f771fe4eac56f8dc073b44358d`
    *(Ghi chú: Trên Zenodo, tập test được lưu dưới dạng file chưa nén `test.tar` dung lượng 6.199.326.720 bytes, MD5 `51890d4e6c5bac6d7e22d6f655265c83`).*
- **Đánh giá xác thực nguồn gốc:**
  > **Kết luận chuẩn xác:** Các tệp nén cục bộ hoàn toàn nhất quán (*consistent*) với bản phát hành chính thức trên Hugging Face về tên tệp, cấu trúc tệp, siêu dữ liệu cache tải về và dung lượng byte. Tuy nhiên, do chưa thực hiện tính toán hàm băm độc lập trên toàn bộ tệp nén cục bộ dung lượng lớn (17,89 GB và 5,75 GB) để đối chiếu trực tiếp từng byte với checksum nhà xuất bản, **tính đồng nhất tuyệt đối cấp byte (byte-identical upstream archive provenance) chưa được chứng minh một cách độc lập**.

---

## 10. Publication & Redistribution Implications (Hàm ý xuất bản và phân phối lại)

Cần phân định rạch ròi quyền hạn dựa trên nguồn gốc tài nguyên:

1. **Phân định quyền sử dụng hình ảnh mẫu (Sample Images):**
   - **Trường hợp A: Lấy ảnh trực tiếp từ tập dữ liệu (`data/raw/InspecSafe-V1/.../*.jpg`):**
     Áp dụng giấy phép **CC-BY-4.0**. Được phép trích dẫn, cắt xén, chú thích phục vụ bài báo nghiên cứu, slide bảo vệ luận văn hoặc báo cáo Seminar. Bắt buộc ghi nhận nguồn: *"Image source: InspecSafe-V1 dataset (Liu et al., 2026), under CC-BY-4.0"*.
   - **Trường hợp B: Sao chép/trích xuất Figures từ bài báo Scientific Data:**
     Áp dụng giấy phép **CC BY-NC-ND 4.0** của tạp chí *Scientific Data*. Chỉ được phép tái sử dụng nguyên vẹn (NoDerivatives), phi thương mại (NonCommercial), và trích dẫn bài báo gốc. **Không được tự ý coi các figure minh họa của bài báo giống hệt tài nguyên dữ liệu thô của dataset.**
2. **Đối với Luận văn tốt nghiệp / Bản thảo bài báo khoa học SafeShift:**
   - Được phép công bố các kết quả phân tích thống kê, biểu đồ phân bố nhãn, số liệu ma trận nhầm lẫn và kết quả benchmark mô hình VLM.
   - Giấy phép CC-BY-4.0 của dataset bảo đảm quyền tự do học thuật cho các công trình nghiên cứu phái sinh.
3. **Đối với mã nguồn SafeShift trên GitHub:**
   - **Chính sách phân phối nghiêm ngặt:** Tuyệt đối không đưa tệp nén dataset (`SafeShift.zip`, `train.tar.gz`), thư mục ảnh thô, hoặc các tệp JSON/TXT dung lượng lớn lên GitHub.
   - Hướng dẫn cài đặt của SafeShift sẽ chỉ dẫn người dùng tải dữ liệu trực tiếp từ kho lưu trữ chính thức của nhóm tác giả trên Hugging Face hoặc Zenodo.
   - Các hình ảnh figure đưa vào `outputs/figures/` phải có kích thước nhỏ, đại diện cho các trường hợp kiểm toán đã được rà soát nhạy cảm và có ghi công đầy đủ.

---

## 11. Privacy & Industrial Sensitivity (Quyền riêng tư & Độ nhạy cảm công nghiệp)

Kiểm tra các phát biểu chính thức của tác giả về đạo đức và an toàn thông tin:

1. **Ẩn danh hóa khuôn mặt (Face Anonymization):**
   - Ấn phẩm *Scientific Data* ghi nhận rõ ràng:
     > *"To protect personal privacy, some videos containing human subjects were processed before public release, with all visible human faces anonymized by mosaic masking."*
   - Khảo sát trực quan thực tế (W1 Bước 5) xác nhận các mẫu xuất hiện công nhân vận hành (ví dụ hành vi hút thuốc, vi phạm an hộ lao động) đều đã được áp dụng hiệu ứng làm mờ dạng mosaic che kín nhận dạng khuôn mặt.
2. **Loại bỏ nội dung nhạy cảm an ninh (Security-Sensitive Screening):**
   - Tuyên bố trong bài báo:
     > *"All data involving privacy- or safety-sensitive content have been anonymized or removed in accordance with applicable regulations prior to release."*
   - Các cơ sở công nghiệp (nhà máy hóa chất, trạm biến áp, hầm cáp) đã được kiểm duyệt trước khi phát hành để không làm lộ bí mật vận hành cơ sở hạ tầng trọng yếu.
3. **Khuyến nghị cho SafeShift:**
   - Dù tác giả đã làm mờ khuôn mặt, SafeShift vẫn cần tuân thủ nguyên tắc tôn trọng quyền riêng tư: khi trích dẫn ảnh minh họa có con người vào slide bảo vệ, kiểm tra lại để đảm bảo không có thông tin định danh cá nhân (như bảng tên nhân viên) bị lộ ra ngoài.

---

## 12. Unresolved Questions & Reconciliation (Các vấn đề mở & Đối soát sai lệch)

Đợt audit ghi nhận một số khoảng cách giữa tài liệu công bố chính thức và kết quả kiểm toán cục bộ cần được đối soát (*reconciliation*) chi tiết tại Bước 8:

1. **Đối soát số lượng điểm kiểm tra (Inspection Waypoints / Sites):**
   - **Tài liệu chính thức (*Scientific Data* & Hugging Face README):** Công bố **2.239** valid inspection sites/waypoints.
   - **Kiểm toán thực tế cục bộ (W1 Bước 1–2):** Ghi nhận **3.234** thư mục điểm kiểm tra (`Annotations/Normal_data` + `Annotations/Anomaly_data`) tương ứng với 3.234 mã point ID duy nhất (Train: 2.424; Test: 810).
   - **Nhận định sơ bộ:** Đây **không nhất thiết là mâu thuẫn đối kháng**, mà có thể bắt nguồn từ sự khác biệt về mặt định nghĩa khái niệm: tác giả định nghĩa "2.239 inspection sites" theo vị trí địa lý / tọa độ trạm tuần tra vật lý thực tế của robot tại nhà máy, trong khi 3.234 thư mục đại diện cho các phiên tuần tra, phân đoạn sequence hoặc waypoint logic sau khi chia tách tập train/test. Cần đối soát cụ thể ở Bước 8.
2. **Đối soát số lượng danh mục đối tượng (RGB Object Classes / Labels):**
   - **Tài liệu chính thức (*Scientific Data* & GitHub README):** Nêu rõ *"covering 234 key industrial inspection object categories"*.
   - **Kiểm toán thực tế cục bộ (W1 Bước 6):** Thu được chính xác **231** chuỗi nhãn gốc duy nhất (`unique raw labels`) xuất hiện trong 37.434 đa giác (Train: 207 nhãn; Test: 166 nhãn; Hợp: 231 nhãn).
   - **Nhận định sơ bộ:** Khoảng cách giữa 234 lớp công bố và 231 nhãn thực tế có thể do: (a) một số lớp hiếm có trong taxonomy chuẩn nhưng không có mẫu nào trong 5.013 ảnh công bố, hoặc (b) sự gộp/tách nhãn văn bản (ví dụ nhãn đa từ, nhãn viết hoa/thường). **SafeShift tuyệt đối không tự ý chuẩn hóa nhãn (normalize) để ép 231 thành 234**; việc này sẽ được phân tích thấu đáo ở Bước 8.
3. **Sự không đồng nhất về định dạng tệp test giữa Zenodo và Hugging Face:**
   - Trên Zenodo: Tệp có tên `test.tar` (6.199.326.720 bytes, uncompressed tar).
   - Trên Hugging Face Hub: Tệp có tên `test.tar.gz` (5.748.799.871 bytes, gzip compressed).
   - Đã xác nhận đây chỉ là khác biệt về thuật toán đóng gói nén của hai kho lưu trữ, không ảnh hưởng đến nội dung mẫu bên trong.
4. **Thiếu file LICENSE mã nguồn độc lập:**
   - Các script Python của tác giả trong repo GitHub chưa có header bản quyền MIT/Apache. SafeShift sẽ xây dựng bộ mã nguồn độc lập riêng trong `safeshift/` kèm kiểm thử đầy đủ.

---

## 13. SafeShift Implications (Hàm ý đối với lộ trình SafeShift)

1. **Tính khả thi về mặt bản quyền (Feasibility):**
   - Giấy phép dữ liệu được xác nhận vững chắc là **CC-BY-4.0** (Open Access). SafeShift hoàn toàn hợp lệ về mặt pháp lý khi sử dụng dataset cho Seminar và Luận văn học thuật.
2. **Tuân thủ đạo đức và chính sách dữ liệu:**
   - Tôn trọng nguyên tắc giữ nguyên dữ liệu gốc, không phân phối lại raw data ra cộng đồng, trích dẫn bài báo chính thức *Scientific Data* (Liu et al., 2026) trong tất cả báo cáo.
3. **Cơ sở cho Bước 8 (Synthesis & Final Report):**
   - Các phát hiện về sự chênh lệch (2.239 vs 3.234 waypoints; 234 vs 231 nhãn) cung cấp đầu vào chính xác cho việc tổng hợp báo cáo tổng kết W1 (`notes/w1_dataset_audit.md`) mà không làm méo mó bản chất dữ liệu.

---

## 14. Sources (Danh mục nguồn kiểm chứng)

| STT | Nguồn (Site / Org) | Tiêu đề tài liệu | URL kiểm chứng | Ngày truy cập | Dữ liệu kiểm chứng thu thập |
|---|---|---|---|---|---|
| 1 | **Scientific Data** (Nature Portfolio) | *Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios* | `https://doi.org/10.1038/s41597-026-07796-x` | 2026-09-15 | Ấn phẩm tạp chí chính thức (Version of Record), Vol 13, Art 1198 (17/08/2026). Giấy phép bài báo CC BY-NC-ND 4.0. Khẳng định 2.239 inspection sites và 234 categories. |
| 2 | **arXiv** (Cornell University) | *Preprint: Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios* | `https://arxiv.org/abs/2601.21173` | 2026-09-15 | Bản thảo lưu trữ (Preprint arXiv:2601.21173v2, 29/04/2026), quyền phân phối phi độc quyền arXiv. |
| 3 | **Hugging Face Hub API** | *Dataset Repository Metadata API* | `https://huggingface.co/api/datasets/Tetrabot2026/InspecSafe-V1` | 2026-09-15 | Xác minh ID kho `Tetrabot2026/InspecSafe-V1`, commit SHA `f3cb7d3e`, tag `license: cc-by-4.0`, dung lượng 41,5 GB và danh mục 7 tệp phát hành. |
| 4 | **Zenodo API** (CERN) | *Zenodo Record 19885643 API* | `https://zenodo.org/api/records/19885643` | 2026-09-15 | Xác minh DOI `10.5281/zenodo.19885643`, version 1.0.1, license CC-BY-4.0, MD5 checksum của `train.tar.gz` (`a2b84da4...`) và `test.tar` (`51890d4e...`). |
| 5 | **GitHub** | *Repository liuzy0708/InspecSafe* | `https://github.com/liuzy0708/InspecSafe` | 2026-09-15 | Cấu trúc mã nguồn tác giả, mẫu trích dẫn BibTeX, ghi chú điều kiện sử dụng nghiên cứu và liên kết tổ chức Đại học Thanh Hoa & TetraBOT. |
| 6 | **Local Dataset Metadata** | *InspecSafe-V1 Local Filesystem & Cache* | `data/raw/InspecSafe-V1/` | 2026-09-15 | Đối soát kích thước tệp nén `train.tar.gz` và `test.tar.gz`, metadata Hugging Face LFS SHA256 trong `.cache/huggingface/trees/`. |
