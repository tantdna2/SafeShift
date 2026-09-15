# Source & License Audit: InspecSafe-V1

Tài liệu này ghi nhận kết quả xác minh toàn diện nguồn gốc, giấy phép bản quyền, điều kiện pháp lý và tài liệu phát hành chính thức của tập dữ liệu **InspecSafe-V1** trong khuôn khổ Week 1 (Dataset Audit — Bước 7) của dự án SafeShift. 

Tất cả các thông tin được kiểm chứng chéo trực tiếp từ các nguồn chính thống: arXiv, Hugging Face Hub API, Zenodo DOI API, GitHub repository chính thức của tác giả và hệ thống tệp siêu dữ liệu cục bộ.

---

## 1. Scope (Phạm vi xác minh)

Phạm vi của đợt audit này bao gồm:
1. **Định danh chính thức:** Tên gọi chuẩn, các tổ chức và nhóm nghiên cứu đứng sau InspecSafe-V1.
2. **Bài báo khoa học gắn liền:** Xác định bài báo gốc công bố benchmark, tác giả, nơi xuất bản và định danh học thuật (arXiv / DOI).
3. **Kênh phát hành chính thức:** Xác minh project page, GitHub repo, Hugging Face dataset repo và kho lưu trữ trường tồn Zenodo.
4. **Phân tích giấy phép (License Audit đa tầng):** Bóc tách độc lập giấy phép của mã nguồn (Code License), dữ liệu thị giác & cảm biến (Dataset License), và ấn phẩm học thuật (Paper Copyright).
5. **Ma trận quyền hạn sử dụng (Rights Matrix):** Đánh giá các hoạt động học thuật của SafeShift (seminar, luận văn, công bố manifest, huấn luyện mô hình, sử dụng ảnh minh họa).
6. **Truy nguyên nguồn gốc cục bộ (Local Acquisition Provenance):** Tách bạch giữa bản sao lưu cục bộ (`SafeShift.zip`), dấu vân tay nội bộ (`fingerprint`), và tệp nén phát hành chính thức của tác giả.
7. **Quyền riêng tư và độ nhạy cảm công nghiệp:** Rà soát các tuyên bố đạo đức, ẩn danh hóa (anonymization) và an ninh cơ sở hạ tầng.

---

## 2. Official Dataset Identity (Định danh chính thức)

- **Tên chính thức:** `InspecSafe-V1` (viết tắt của *Inspection Safety Benchmark - Version 1*).
- **Mục đích thiết kế:** Bộ tiêu chuẩn đa phương thức đầu tiên phục vụ đánh giá mức độ an toàn và xây dựng mô hình thế giới (world model) trong các kịch bản kiểm tra an toàn công nghiệp bằng robot tự hành.
- **Quy mô khảo sát:**
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

Bài báo chính thức gắn liền trực tiếp với InspecSafe-V1:

- **Tiêu đề (Title):** *Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios*
- **Tác giả (Authors):** Zeyi Liu, Shuang Liu, Jihai Min, Zhaoheng Zhang, Jun Cen, Pengyu Han, Songqiao Hu, Zihan Meng, Xiao He, Donghua Zhou.
- **Tác giả liên hệ (Corresponding Author):** Giáo sư Xiao He (Khoa Tự động hóa, Đại học Thanh Hoa, Email: `hexiao@tsinghua.edu.cn`).
- **Năm công bố:** 2026.
- **Địa điểm / Phân loại (Venue):** arXiv preprint (`cs.RO` — Robotics; `cs.CV` — Computer Vision and Pattern Recognition).
- **arXiv ID:** [arXiv:2601.21173](https://arxiv.org/abs/2601.21173) (phiên bản v1 nộp ngày 27/01/2026; phiên bản v2 cập nhật ngày 29/04/2026).
- **Paper DOI:** `10.48550/arXiv.2601.21173`
- **Official PDF URL:** `https://arxiv.org/pdf/2601.21173`
- **Data Archive DOI (được trích dẫn trong bài báo [Ref 41]):** `10.5281/zenodo.19885643`
- **Liên kết mã nguồn và dữ liệu công bố trong bài báo:**
  - Code availability: `https://github.com/liuzy0708/InspecSafe`
  - Data availability: `https://huggingface.co/datasets/Tetrabot2026/InspecSafe-V1` và `https://doi.org/10.5281/zenodo.19885643`.

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
- **DOI định danh trường tồn:** `10.5281/zenodo.19885643` (Concept DOI gom phiên bản: `10.5281/zenodo.19885642`).
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
  - Kho mã nguồn GitHub và Hugging Face Hub đang ở trạng thái stable release khớp với phiên bản bài báo arXiv v2 (tháng 04/2026).
- **Quy tắc dự án:** SafeShift giữ nguyên và làm việc với bản phát hành chuẩn `InspecSafe-V1` (phiên bản snapshot commit `f3cb7d3e`), không tự ý thay đổi dữ liệu hoặc chuyển dịch phiên bản.

---

## 6. License Evidence (Bằng chứng giấy phép bản quyền)

Phân tích độc lập giấy phép theo 3 tầng tài nguyên để tránh đánh đồng phạm vi pháp lý:

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

### B. Code License (Giấy phép mã nguồn)
- **Tình trạng xác minh:** `RESTRICTED / NOT_SPECIFIED (Standalone)`
- **Bằng chứng văn bản:**
  - Trên GitHub repo `liuzy0708/InspecSafe` và trong các tệp Python (`dataset_loader.py`, `model_api_generate_results.py`,...), tác giả **không đính kèm tệp LICENSE độc lập** chuẩn OSI (như Apache-2.0 hay MIT).
  - Tuyên bố sử dụng trong mục `Usage Notes` của GitHub README ghi:
    > *"The dataset is intended for research use. Redistribution, modification, and derivative works are permitted under the dataset’s stated usage terms, with proper citation required."*
  - Trên Hugging Face, toàn bộ kho lưu trữ chứa cả code lẫn data đều được đặt dưới tag giấy phép `cc-by-4.0`.
- **Diễn giải pháp lý:** Về mặt nghiêm ngặt học thuật, mã nguồn không có giấy phép phần mềm mã nguồn mở tiêu chuẩn mà đi kèm theo gói tài nguyên nghiên cứu của bài báo. SafeShift chỉ tham khảo logic kiểm tra, không sao chép nguyên khối mã nguồn tác giả thành phần mềm độc lập khi chưa có sự cho phép.

### C. Paper Copyright (Bản quyền bài báo)
- **Tình trạng xác minh:** `VERIFIED`
- **Giấy phép bài báo:** **arXiv Non-exclusive Distribution License** (`http://arxiv.org/licenses/nonexclusive-distrib/1.0/`).
- **Bản quyền sở hữu trí tuệ:** Thuộc về nhóm tác giả (Zeyi Liu, Xiao He et al.). Tác giả cấp quyền phân phối vĩnh viễn phi độc quyền cho arXiv.

---

## 7. Rights Matrix (Ma trận quyền hạn sử dụng)

Bảng phân định quyền hạn chi tiết cho từng hạng mục hoạt động nghiên cứu của SafeShift:

| Hoạt động (Item) | Xác minh (Verified?) | Bằng chứng (Evidence) | Diễn giải quy tắc SafeShift (Interpretation) |
|---|---|---|---|
| **Academic research use** | **ALLOWED** | Tuyên bố rõ ràng trong README, Zenodo, Hugging Face và Paper: "intended for research use", CC-BY-4.0. | SafeShift được phép hoàn toàn sử dụng dữ liệu để thực hiện nghiên cứu, phân tích benchmark, phục vụ môn Seminar và Luận văn thạc sĩ/kỹ sư. |
| **Commercial use** | **RESTRICTED** | CC-BY-4.0 cho phép mục đích thương mại nếu tuân thủ ghi nhận, nhưng README GitHub ghi chú "intended for research use". | Dự án SafeShift là nghiên cứu học thuật thuần túy, tuyệt đối không dùng vào các sản phẩm thương mại để tránh xung đột với khuyến nghị của nhóm tác giả. |
| **Modification / Derivative works** | **ALLOWED** | Điều khoản CC-BY-4.0: "Adapt — remix, transform, and build upon the material for any purpose". README: "Redistribution, modification, and derivative works are permitted". | Được phép tạo dữ liệu dẫn xuất, lọc manifest, tính toán chỉ số thống kê, ánh xạ lại danh mục nhãn phân loại an toàn. |
| **Redistribution raw images** | **RESTRICTED** | Về pháp lý CC-BY-4.0 cho phép chia sẻ lại kèm attribution. Tuy nhiên, **chính sách nội bộ SafeShift cấm phân phối lại**. | SafeShift **TUYỆT ĐỐI KHÔNG** upload/redistribute tập dữ liệu ảnh thô (23+ GB) lên GitHub hay bất kỳ đám mây công cộng nào. Người dùng phải tải từ link chính thức của tác giả. |
| **Redistribution annotations** | **ALLOWED** | Thuộc phạm vi chuyển thể/phân phối phái sinh theo CC-BY-4.0 kèm ghi công tác giả. | Được phép công bố các chú thích bổ sung hoặc tập nhãn đã làm sạch do SafeShift phát triển, có dẫn nguồn InspecSafe-V1. |
| **Redistribution text descriptions** | **ALLOWED** | Thuộc phạm vi dữ liệu văn bản theo CC-BY-4.0 kèm ghi công tác giả. | Được phép sử dụng cho prompt engineering và benchmark đánh giá VLM. |
| **Publishing sample images in paper/slides** | **ALLOWED** | CC-BY-4.0 cho phép xuất bản trích dẫn minh họa. Tác giả đã xử lý làm mờ khuôn mặt người (mosaic masking). | Được phép đưa một số ít ảnh mẫu đại diện vào bài báo nghiên cứu, slide bảo vệ luận văn hoặc báo cáo Seminar, kèm chú thích bản quyền: "Images courtesy of InspecSafe-V1 (Liu et al., 2026), under CC-BY-4.0". Hạn chế tối đa đưa ảnh thô lên Git repository công khai. |
| **Publishing derived manifests** | **ALLOWED** | Tạo lập siêu dữ liệu phái sinh (CSV/JSON manifest) phục vụ tái lập nghiên cứu khoa học. | Được phép đưa vào repository nếu manifest chỉ chứa relative path, nhãn, tọa độ bounding box hoặc metadata; **tuyệt đối không nhúng chuỗi Base64 `imageData`**. |
| **Publishing aggregate statistics** | **ALLOWED** | Kết quả phân tích thống kê, phân bố dữ liệu, ma trận mất cân bằng domain là sản phẩm nghiên cứu độc lập. | Được phép công bố đầy đủ trong báo cáo khoa học SafeShift. |
| **Publishing trained model weights** | **ALLOWED** | Trọng số mô hình sau huấn luyện/fine-tune là sản phẩm dẫn xuất. | Được phép công bố mã nguồn adapter hoặc checkpoint mô hình nghiên cứu. |
| **Attribution requirement** | **ALLOWED** | Điều kiện cốt lõi của CC-BY-4.0: "You must give appropriate credit, provide a link to the license, and indicate if changes were made". | **BẮT BUỘC**: Mọi báo cáo, slide, mã nguồn hay bài báo phát sinh từ SafeShift phải trích dẫn bài báo chính thức và trang dataset InspecSafe-V1. |

---

## 8. Citation (Trích dẫn khoa học chính thức)

Trích dẫn chuẩn theo định dạng BibTeX chính thức được nhóm tác giả công bố tại kho GitHub và siêu dữ liệu arXiv:

```bibtex
@misc{liu2026inspecsafe,
  title        = {InspecSafe-V1: A Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios},
  author       = {Zeyi Liu and Shuang Liu and Jihai Min and Zhaoheng Zhang and Jun Cen and Pengyu Han and Songqiao Hu and Zihan Meng and Xiao He and Donghua Zhou},
  year         = {2026},
  eprint       = {2601.21173},
  archivePrefix= {arXiv},
  primaryClass = {cs.RO},
  url          = {https://arxiv.org/abs/2601.21173},
  doi          = {10.48550/arXiv.2601.21173}
}
```

Trích dẫn kho dữ liệu lưu trữ Zenodo có DOI:

```bibtex
@dataset{liu_2026_inspecsafe_zenodo,
  author       = {Zeyi Liu and Shuang Liu and Jihai Min and Zhaoheng Zhang and Jun Cen and Pengyu Han and Songqiao Hu and Zihan Meng and Xiao He and Donghua Zhou},
  title        = {Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios},
  month        = apr,
  year         = 2026,
  publisher    = {Zenodo},
  version      = {1.0.1},
  doi          = {10.5281/zenodo.19885643},
  url          = {https://doi.org/10.5281/zenodo.19885643}
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

- **Đối soát với tệp phát hành thượng nguồn (Upstream Archives Checksum):**
  Trong thư mục `data/raw/InspecSafe-V1`, hai tệp nén gốc đi kèm gồm:
  - `train.tar.gz`: Kích thước chính xác **17.886.855.594 bytes** (~17,89 GB).
    - Khớp tuyệt đối kích thước công bố trên Hugging Face LFS: `17.886.855.594 bytes`.
    - Khớp tuyệt đối kích thước công bố trên Zenodo API: `17.886.855.594 bytes`.
    - Checksum thượng nguồn:
      - MD5 (theo Zenodo API): `a2b84da421c32a67b025240ad4365048`
      - Git LFS SHA256 (theo HF snapshot `.cache`): `ef03b9eb2f9bd91b03f203a8e6cfcc3464cb0d9f0215349a80ad95281fa88cd6`
  - `test.tar.gz`: Kích thước chính xác **5.748.799.871 bytes** (~5,75 GB).
    - Khớp tuyệt đối kích thước công bố trên Hugging Face LFS: `5.748.799.871 bytes`.
    - Checksum thượng nguồn:
      - Git LFS SHA256 (theo HF snapshot `.cache`): `818086e696f970e036bf6a76758e4fb851fa26f771fe4eac56f8dc073b44358d`
    *(Ghi chú: Trên Zenodo, tập test được lưu dưới dạng file chưa nén `test.tar` dung lượng 6.199.326.720 bytes; tệp tại local là `test.tar.gz` được kéo trực tiếp từ Hugging Face Hub snapshot).*
- **Kết luận xuất xứ:** Dữ liệu trên máy trạm local có nguồn gốc trực tiếp từ bản phân phối Hugging Face chính thức của nhóm tác giả (commit `f3cb7d3e`), không phải bản mod trôi nổi.

---

## 10. Publication & Redistribution Implications (Hàm ý xuất bản và phân phối lại)

Dựa trên giấy phép CC-BY-4.0 và các ghi chú vận hành:

1. **Đối với báo cáo Seminar và Slide bảo vệ:**
   - Hoàn toàn hợp lệ khi trình chiếu các hình ảnh mẫu trích từ dataset để minh họa các hiện tượng: chói sáng, rò rỉ cross-split, mất cân bằng domain, hoặc lỗi suy luận của VLM.
   - Bắt buộc phải gắn kèm dòng ghi nhận nguồn (Attribution Caption) dưới mỗi hình ảnh hoặc bảng số liệu.
2. **Đối với Luận văn tốt nghiệp / Bản thảo bài báo khoa học:**
   - Được phép trích dẫn số liệu thống kê, sơ đồ phân bố nhãn, và hình ảnh trực quan hóa định tính.
   - Giấy phép CC-BY-4.0 bảo đảm quyền công bố học thuật không bị giới hạn bởi rào cản thương mại của bên thứ ba.
3. **Đối với mã nguồn SafeShift trên GitHub:**
   - **Chính sách phân phối nghiêm ngặt:** Tuyệt đối không commit tệp nén (`SafeShift.zip`, `train.tar.gz`), thư mục ảnh `data/raw/`, hoặc bản sao tệp JSON/TXT dung lượng lớn lên GitHub.
   - Khi phát hành repository SafeShift ra công chúng, hướng dẫn tái lập phải chỉ dẫn người dùng tải dữ liệu trực tiếp từ Hugging Face (`Tetrabot2026/InspecSafe-V1`) hoặc Zenodo (`10.5281/zenodo.19885643`).
   - Các tệp figure minh họa đưa vào `outputs/figures/` phải có kích thước nhỏ, chỉ chứa các trường hợp tiêu biểu đã được kiểm tra tính nhạy cảm, và có trích dẫn nguồn gốc rõ ràng.

---

## 11. Privacy & Industrial Sensitivity (Quyền riêng tư & Độ nhạy cảm công nghiệp)

Kiểm tra các phát biểu chính thức của tác giả về đạo đức và an toàn thông tin:

1. **Ẩn danh hóa khuôn mặt (Face Anonymization):**
   - Bài báo công bố rõ ràng trong mục *Data Acquisition*:
     > *"To protect personal privacy, some videos containing human subjects were processed before public release, with all visible human faces anonymized by mosaic masking."*
   - Khảo sát trực quan thực tế (W1 Bước 5) xác nhận các mẫu xuất hiện nhân sự vận hành (ví dụ hành vi hút thuốc, đi vào khu vực cấm) đều đã được áp dụng hiệu ứng làm mờ dạng mosaic che kín nhận dạng khuôn mặt.
2. **Loại bỏ nội dung nhạy cảm an ninh (Security-Sensitive Screening):**
   - Tuyên bố trong mục *Data Availability*:
     > *"All data involving privacy- or safety-sensitive content have been anonymized or removed in accordance with applicable regulations prior to release."*
   - Các cơ sở công nghiệp (nhà máy hóa chất, trạm biến áp, hầm cáp) đã được chọn lọc để không làm lộ sơ đồ bí mật quốc gia hoặc vị trí địa lý quân sự nhạy cảm.
3. **Khuyến nghị cho SafeShift:**
   - Dù tác giả đã làm mờ khuôn mặt, SafeShift vẫn cần tuân thủ nguyên tắc tôn trọng quyền riêng tư: khi trích dẫn ảnh minh họa có con người vào slide bảo vệ, kiểm tra lại để đảm bảo không có thông tin định danh cá nhân (như thẻ tên, đồng phục ghi tên riêng) bị lộ ra ngoài.

---

## 12. Unresolved Questions (Các vấn đề mở cần lưu ý cho W2)

Mặc dù giấy phép dataset đã được xác nhận là CC-BY-4.0, một số khía cạnh học thuật và kỹ thuật từ phía tác giả vẫn cần lưu tâm:

1. **Sự không đồng nhất giữa tên file test trên Zenodo và Hugging Face:**
   - Trên Zenodo: Tệp có tên `test.tar` (6.199.326.720 bytes).
   - Trên Hugging Face Hub: Tệp có tên `test.tar.gz` (5.748.799.871 bytes).
   - Cần ghi nhận đây là sự khác biệt về thuật toán đóng gói/nén của hai nền tảng, không phải phiên bản dữ liệu khác biệt về nội dung mẫu.
2. **Khuyến nghị "Research Use Only" trong README GitHub đối chiếu với CC-BY-4.0:**
   - CC-BY-4.0 về mặt pháp lý là giấy phép mở cho phép cả thương mại nếu ghi công. Tuy nhiên, câu chữ của tác giả trong README ("intended for research use") thể hiện ý đồ học thuật của nhóm nghiên cứu. SafeShift tuyệt đối tôn trọng tinh thần này và chỉ sử dụng trong nghiên cứu khoa học thuần túy.
3. **Thiếu file LICENSE mã nguồn độc lập:**
   - Script đánh giá của tác giả (`model_benchmark_evaluation.py`) chưa có header bản quyền MIT/Apache rõ ràng. SafeShift sẽ xây dựng bộ codebase riêng độc lập trong thư mục `safeshift/` và tự viết mã nguồn sạch có kiểm thử đầy đủ, chỉ tham khảo logic công thức đánh giá.

---

## 13. SafeShift Implications (Hàm ý đối với lộ trình SafeShift)

1. **Tính khả thi về mặt bản quyền (Feasibility):**
   - Việc xác minh thành công giấy phép **CC-BY-4.0** chính thức trên Hugging Face và Zenodo giúp SafeShift hoàn toàn tự tin về cơ sở pháp lý khi sử dụng InspecSafe-V1 cho đề tài Seminar và luận văn học thuật.
2. **Đảm bảo tính trung thực nghiên cứu:**
   - Tôn trọng nguyên tắc giữ nguyên dữ liệu gốc, phân biệt rạch ròi giữa bản lưu trữ local `SafeShift.zip` và bản phân phối thượng nguồn của ĐH Thanh Hoa / TetraBOT.
   - Áp dụng đầy đủ trích dẫn BibTeX chính thức trong tất cả các ấn phẩm của dự án.
3. **Chuyển giao sang giai đoạn W2:**
   - Bước 7 hoàn tất dứt điểm toàn bộ các nghi vấn về xuất xứ, giấy phép và tài liệu tác giả. Dự án sẵn sàng bước vào khâu hoàn thiện báo cáo tổng hợp W1 (`notes/w1_dataset_audit.md`) và thiết kế benchmark VLM trong Week 2.

---

## 14. Sources (Danh mục nguồn kiểm chứng)

| STT | Nguồn (Site / Org) | Tiêu đề tài liệu | URL kiểm chứng | Ngày truy cập | Dữ liệu kiểm chứng thu thập |
|---|---|---|---|---|---|
| 1 | **arXiv** (Cornell University) | *Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios* | `https://arxiv.org/abs/2601.21173` | 2026-09-15 | Định danh bài báo, danh sách tác giả, tóm tắt, ngày công bố v1/v2, quyền phân phối phi độc quyền arXiv. |
| 2 | **arXiv HTML** | *Paper Fulltext & Data/Code Availability Section* | `https://arxiv.org/html/2601.21173v2` | 2026-09-15 | Toàn văn bài báo, mô tả chi tiết phần cứng robot, giao thức phân vùng nhãn, tuyên bố ẩn danh hóa khuôn mặt, liên kết Zenodo [Ref 41] và Hugging Face. |
| 3 | **Hugging Face Hub API** | *Dataset Repository Metadata API* | `https://huggingface.co/api/datasets/Tetrabot2026/InspecSafe-V1` | 2026-09-15 | Xác minh ID kho `Tetrabot2026/InspecSafe-V1`, commit SHA `f3cb7d3e`, tag `license: cc-by-4.0`, dung lượng 41,5 GB và danh mục 7 tệp phát hành. |
| 4 | **Zenodo API** (CERN) | *Zenodo Record 19885643 API* | `https://zenodo.org/api/records/19885643` | 2026-09-15 | Xác minh DOI `10.5281/zenodo.19885643`, version 1.0.1, license CC-BY-4.0, MD5 checksum của `train.tar.gz` (`a2b84da4...`) và `test.tar` (`51890d4e...`). |
| 5 | **GitHub** | *Repository liuzy0708/InspecSafe* | `https://github.com/liuzy0708/InspecSafe` | 2026-09-15 | Cấu trúc mã nguồn tác giả, mẫu trích dẫn BibTeX, ghi chú điều kiện sử dụng nghiên cứu và liên kết tổ chức Đại học Thanh Hoa & TetraBOT. |
| 6 | **Local Dataset Metadata** | *InspecSafe-V1 Local Filesystem & Cache* | `data/raw/InspecSafe-V1/` | 2026-09-15 | Đối soát kích thước tệp nén `train.tar.gz` và `test.tar.gz`, metadata Hugging Face LFS SHA256 trong `.cache/huggingface/trees/`. |
