# SafeShift Research Feasibility Audit

**Đánh giá khả năng nghiên cứu Cross-Domain Generalization và Evidence Grounding trên InspecSafe-V1**  
*Dự án SafeShift — Tuần 1 (Dataset Audit), Bước 8*  
*Ngày audit: 15/09/2026*  
*Trạng thái: Hoàn thành kiểm định khả thi (Research Feasibility Verified)*  

---

## 1. Scope (Phạm vi và mục tiêu kiểm định)

Tài liệu này tổng hợp và đánh giá toàn diện cơ sở thực chứng nhằm trả lời hai câu hỏi nghiên cứu cốt lõi của SafeShift đối với bộ dữ liệu **InspecSafe-V1**:

1. **Câu hỏi A (Cross-Domain Feasibility):**  
   *InspecSafe-V1 có đủ cơ sở thực nghiệm để nghiên cứu **Cross-Domain Generalization** (khái quát hóa xuyên miền) hay chỉ đủ điều kiện cho **Cross-Domain Robustness** (độ bền vững xuyên miền)?*
2. **Câu hỏi B (Evidence Grounding Feasibility):**  
   *InspecSafe-V1 có đủ dữ liệu annotation để đánh giá **Evidence Grounding** (mức độ mô hình bám sát bằng chứng thị giác phục vụ quyết định an toàn) hay chỉ hỗ trợ một dạng **Proxy / Subset Grounding** (đại diện gián tiếp / tập con)?*

**Nguyên tắc toàn vẹn nghiên cứu:**  
- Không thiên vị, không cố tình chứng minh đề tài khả thi bằng mọi giá. Mọi kết luận đều xuất phát trực tiếp từ bằng chứng thực nghiệm đã được kiểm chứng chéo trong Tuần 1 (W1).
- Nếu dữ liệu cho thấy một giả thuyết hoặc một nhánh nghiên cứu gặp trở ngại cấu trúc hoặc rủi ro gây nhiễu (confounding), tài liệu phải chỉ rõ giới hạn đó để chuẩn bị cho các quyết định phương pháp luận tại Tuần 2 (W2).
- Tuyệt đối không can thiệp sửa đổi raw data, không tự ý gán nhãn mới, không tạo split chính thức và không chạy suy luận VLM trong bước kiểm toán này.

---

## 2. Evidence Base from W1 (Cơ sở thực chứng từ Tuần 1)

Báo cáo khả thi này kế thừa trực tiếp các kết quả kiểm định độc lập đã thực hiện xuyên suốt W1 (Bước 1 đến Bước 7):

1. **Cấu trúc dữ liệu và Schema ([dataset_schema.md](dataset_schema.md), [manifest_builder.md](manifest_builder.md)):**  
   - Tổng cộng **5.013 mẫu** (triplets `.jpg`, `.json`, `.txt`), chia thành `train` (3.763 mẫu) và `test` (1.250 mẫu).
   - 100% mẫu có đầy đủ bộ ba tệp; 44 ảnh PNG bị đặt sai phần mở rộng thành `.jpg` (đều thuộc `Anomaly_data`).
   - 3.234 thư mục điểm tuần tra logic (`point_id` từ `000001` đến `003234`); độ trùng lặp `point_id` giữa `train` và `test` bằng 0.
2. **Xác thực dữ liệu & Tính nhất quán ([dataset_validation.md](dataset_validation.md)):**  
   - 100% kích thước ảnh nhị phân khớp metadata `imageWidth`/`imageHeight` trong JSON; 309 đa giác có tọa độ vượt nhẹ biên ảnh (được giữ nguyên).
   - Xác nhận 36 mẫu có sự xung đột giữa tên thư mục (`folder_domain`) và câu mở đầu mô tả ngữ nghĩa (`text_domain`).
3. **Trùng lặp và Rò rỉ phân tách ([duplicate_leakage_audit.md](duplicate_leakage_audit.md)):**  
   - Phát hiện **53 cặp trùng lặp pixel tuyệt đối** (`CONFIRMED_PIXEL_EXACT`), trong đó có **7 cặp trùng lặp xuyên split (`cross-split exact pairs`)**.
   - Phát hiện **833 cặp ứng viên dHash $\le 8$ xuyên split** (gồm 7 cặp exact và 826 cặp near candidates).
   - Nhận diện **12 họ nguồn ảnh suy luận (`source families`)** bao trùm toàn bộ 1.000 mẫu `Anomaly_data`.
4. **Kiểm tra nguồn gốc thị giác ([visual_provenance_review.md](visual_provenance_review.md)):**  
   - 7 cặp exact bộc lộ xung đột gán nhãn trực tiếp: Cấp 1 vs Cấp 2, miền luyện kim vs miền hóa chất, không đeo găng vs hút thuốc.
   - Cả 12 source families đều bị phân chia cứng theo chỉ số thứ tự (`~25% test` với index đầu, `~75% train` với index sau), dẫn đến rò rỉ chuỗi video liên tục (temporal sequence leakage) và dùng chung góc máy camera robot xuyên split.
5. **Phân bố và Mất cân bằng ([distribution_imbalance_audit.md](distribution_imbalance_audit.md)):**  
   - Tỷ lệ mất cân bằng an toàn cực đoan: Level04 (4.013 mẫu) so với Level03 (15 mẫu) đạt tỷ số **267,5:1**.
   - Miền `metallurgy` có 720 mẫu nhưng chỉ có 9 mẫu Anomaly ở train và **0 mẫu Anomaly ở test**; 8/9 mẫu Anomaly này có text mô tả `oil_chemical`.
   - Có **231 chuỗi nhãn đối tượng thô duy nhất** trên 37.434 đa giác (207 ở train, 166 ở test; 65 nhãn chỉ có ở train, 24 nhãn chỉ có ở test).
6. **Nguồn gốc và Pháp lý ([source_license_audit.md](source_license_audit.md)):**  
   - Dataset phát hành dưới giấy phép **CC-BY-4.0** (hợp lệ cho nghiên cứu học thuật của SafeShift).
   - Bài báo chính thức trên *Scientific Data* (Liu et al., 2026; DOI: 10.1038/s41597-026-07796-x) công bố 2.239 inspection sites và 234 categories, tạo ra khoảng cách cần đối soát với 3.234 point folders và 231 raw labels cục bộ.

---

## 3. Domain Metadata Inventory (Kiểm kê siêu dữ liệu miền và nguồn)

Để đánh giá khả năng thiết lập bài toán cross-domain, toàn bộ các trường dữ liệu có liên quan đến ngữ cảnh miền, nguồn thu thập và thiết bị được lập bảng và phân loại theo mức độ tin cậy:

| Tên trường (Metadata Field) | Nguồn trích xuất (Source) | Định nghĩa & Ý nghĩa | Độ phủ (Coverage) | Độ tin cậy (Reliability) | Xung đột đã biết (Known Conflicts) | Được dùng làm Domain Ground Truth? | Phân loại (Classification) |
|---|---|---|---|---|---|:---:|---|
| `folder_domain` | Đường dẫn thư mục điểm tuần tra (`Annotations/.../{domain}-...`) | Tên miền công nghiệp của thư mục lưu trữ (`coal_conveyor`, `metallurgy`, `oil_chemical`, `power`, `tunnel`). | 5.013/5.013 (100%) | Trung bình | Xung đột với `text_domain` ở 36 mẫu (8 metallurgy, 24 tunnel, 4 power). | **KHÔNG** (Chỉ là tên thư mục phân loại thô) | **DETERMINISTIC_DERIVED_METADATA** |
| `text_domain` | Câu mở đầu tệp `.txt` (`"In the <setting> scene..."`) | Ngữ cảnh công nghiệp được khẳng định trong câu mô tả ngôn ngữ của annotator. | 5.013/5.013 (100%) | Trung bình - Cao | Lệch với `folder_domain` ở 36 mẫu; dùng nhiều biến thể từ vựng (`coal conveying trestle`, `oil and gas chemical plant`). | **KHÔNG** (Chỉ là semantic claim, không có metadata gốc) | **DETERMINISTIC_DERIVED_METADATA** |
| `robot_platform` | Token thứ 3 trong tên thư mục (`SuspendedRail` / `Wheeled`) | Dạng robot tuần tra: ray treo trên cao (`SuspendedRail`) hoặc xe tự hành bánh lăn mặt đất (`Wheeled`). | 5.013/5.013 (100%) | Cao (theo quy ước đặt tên) | Cặp exact duplicate cross-split số 4 bị gán lệch: Train gán `SuspendedRail`, Test gán `Wheeled`. | **KHÔNG** (Là thuộc tính robot, không phải nhãn miền) | **DETERMINISTIC_DERIVED_METADATA** |
| `point_id` | Chuỗi 6 chữ số trong tên thư mục (`000001`–`003234`) | Mã định danh điểm dừng tuần tra logic của robot. | 5.013/5.013 (100%) | Cao (về mặt cú pháp) | Không trùng lặp train/test (overlap = 0), nhưng cùng một bối cảnh vật lý có thể được gán nhiều point ID khác nhau. | **KHÔNG** (Chỉ là mã định danh điểm logic) | **DETERMINISTIC_DERIVED_METADATA** |
| `split` | Đường dẫn thư mục gốc (`train/` hoặc `test/`) | Phân chia tập huấn luyện và kiểm thử chính thức của tác giả. | 5.013/5.013 (100%) | Tuyệt đối (về vị trí đĩa) | Bị rò rỉ 7 cặp exact và hàng trăm cặp near-duplicate chia sẻ chuỗi/góc máy. | **KHÔNG** (Chỉ là phân vùng split của tác giả) | **DETERMINISTIC_DERIVED_METADATA** |
| `data_type` | Tên thư mục cấp 2 (`Normal_data` / `Anomaly_data`) | Phân loại nhị phân trạng thái an toàn: Bình thường (4.013) vs Bất thường (1.000). | 5.013/5.013 (100%) | Tuyệt đối | Khớp 100% với `Level04` vs `Level01-03`. | **KHÔNG** (Là nhãn an toàn, không phải domain) | **DETERMINISTIC_DERIVED_METADATA** |
| `safety_level` | Token thứ 2 trong tên thư mục (`Level01`–`Level04`) | Cấp độ rủi ro an toàn 4 mức từ Cấp 1 (nguy hiểm nhất) đến Cấp 4 (bình thường). | 5.013/5.013 (100%) | Cao (về mặt cú pháp) | Xung đột ở Cặp Exact 1 (Train gán Level 1, Test gán Level 2). | **KHÔNG** (Là nhãn an toàn mục tiêu) | **DETERMINISTIC_DERIVED_METADATA** |
| JSON `imagePath` | Trường `imagePath` trong tệp `.json` | Tên tệp gốc từ hệ thống thu thập upstream trước khi tác giả đổi tên chuẩn hóa. | 5.013/5.013 (100%) | Cao (chỉ thị provenance) | Tên tệp phản ánh thư mục thu thập ban đầu (`hand_frame_...`, `phone_frame_...`). | **KHÔNG** (Chỉ dùng để truy vết nguồn gốc) | **OBSERVED_ORIGINAL_METADATA** |
| `source-family` (Heuristic Bước 4) | Regex prefix trên `imagePath`: `(?P<family>.+)_frame_...` | Họ nguồn ảnh suy luận gom nhóm theo hành vi/thiết bị (12 họ Anomaly). | 1.000/1.000 Anomaly (100% Anomaly) | Trung bình (quy tắc kinh nghiệm) | Không phải video ID chính thức; cùng prefix có thể gộp nhiều cảnh quay độc lập. | **KHÔNG** (Chỉ là heuristic gom nhóm rủi ro rò rỉ) | **HEURISTIC_INFERRED_METADATA** |
| `inspection site` / `waypoint` chính thức | Khai báo trong paper *Scientific Data* (2.239 sites) | Vị trí trạm tuần tra vật lý thực tế tại các nhà máy. | Chỉ có con số tổng trong paper; không có metadata map trực tiếp. | Không thể kiểm chứng trực tiếp | Không có trường `site_id` tường minh trong từng JSON hay manifest gốc. | **KHÔNG** (Thiếu dữ liệu ánh xạ chi tiết) | **UNAVAILABLE** |
| `camera_viewpoint` / `angle` | Góc đặt camera tuần tra (góc nhìn từ trên xuống, ngang tầm mắt) | Góc quan sát hình học của cảm biến quang học trên robot. | Không có trường metadata số đo góc | Suy từ kiểm tra ảnh (visual inspection) | Phụ thuộc chặt chẽ vào nền tảng robot (ray treo cố định góc cao vs xe bánh lăn tầm thấp). | **KHÔNG** | **VISUALLY_INFERRED** |
| `multimodal source presence` | Sự tồn tại của thư mục `Other_modalities` tương ứng | Đánh dấu điểm tuần tra có kèm video nhiệt, âm thanh, LiDAR, khí gas hay không. | 2.233/3.234 waypoints (chỉ có cho `Normal_data`) | Tuyệt đối (về sự hiện diện tệp) | 100% mẫu `Anomaly_data` hoàn toàn KHÔNG có đa phương thức khác. | **KHÔNG** | **DETERMINISTIC_DERIVED_METADATA** |

> **Quy tắc bất biến:** Không được tự ý nâng các trường suy luận hoặc heuristic (`folder_domain`, `text_domain`, `source-family`) thành Ground Truth tuyệt đối của miền. Mọi phân tích cross-domain đều phải ghi nhận rõ bản chất xuất xứ của các trường này.

---

## 4. Đánh giá 5 Industrial Domains (Đối chiếu với tài liệu chính thức)

Năm miền công nghiệp trong cấu trúc thư mục local tương ứng chặt chẽ với 5 kịch bản công nghiệp được công bố trong bài báo chính thức trên *Scientific Data* (Liu et al., 2026):

| Thuật ngữ chính thức trong Paper (*Scientific Data*) | Thuật ngữ thư mục Local (`folder_domain`) | Mức độ tương ứng (Correspondence) | Sai lệch & Mơ hồ nhận diện được (Mismatch / Ambiguity) |
|---|---|:---:|---|
| **Coal conveyor trestles** | `coal_conveyor` | **Trùng khớp trực tiếp** | Bối cảnh hành lang băng chuyền tải than kín. Có 4 mẫu Normal trong thư mục `power` nhưng TXT ghi nhận bối cảnh `coal conveyor bridge`. |
| **Sintering equipment / Metallurgy** | `metallurgy` | **Trùng khớp trực tiếp** | Khu vực máy thiêu kết, làm nguội và xử lý phôi kim loại. **Mơ hồ nghiêm trọng:** 8/9 mẫu Anomaly trong thư mục này có TXT mô tả nhà máy hóa chất (`oil_chemical`). |
| **Oil & gas plants** | `oil_chemical` | **Trùng khớp trực tiếp** | Khu vực tháp chưng cất, cụm van công nghiệp, bồn chứa hóa chất. Nhận thêm 24 mẫu Normal từ thư mục `tunnel` và 8 mẫu Anomaly từ `metallurgy` theo khẳng định của TXT. |
| **Power facilities** | `power` | **Trùng khớp trực tiếp** | Trạm biến áp, phòng điều khiển điện phân phối, dàn pin quang điện. 4 mẫu Normal có TXT ghi nhận băng tải than. |
| **Tunnels** | `tunnel` | **Trùng khớp trực tiếp** | Hầm cáp kỹ thuật đô thị, hầm giao thông ngầm. Có 24 mẫu Normal (12 cặp) lưu ở thư mục `tunnel` nhưng TXT ghi rõ `"In the oil, gas, and chemical plant scene..."`. |

**Đánh giá sự cố 36 mẫu Domain Mismatch:**  
Hiện tượng 36 mẫu xung đột giữa `folder_domain` và `text_domain` không làm sụp đổ toàn bộ khái niệm 5 miền, nhưng chứng minh quy trình tổ chức thư mục ban đầu của tác giả thượng nguồn có sự nhầm lẫn giữa các đợt gán nhãn. SafeShift không tự ý "sửa chữa" tên thư mục hay văn bản; trong các phân tích cross-domain, các mẫu này phải được gắn cờ cảnh báo hoặc tách riêng khi đánh giá độ nhạy.

---

## 5. Cross-Domain Feasibility Matrix (Ma trận khả thi xuyên miền)

Bảng tổng hợp năng lực thực tế của từng miền công nghiệp trong InspecSafe-V1 dựa trên các số liệu kiểm định đã xác minh:

| Miền (`Domain`) | Tổng số mẫu | Mẫu Normal | Mẫu Anomaly | Mẫu Train | Mẫu Test | Độ phủ Safety-level | Phân bố Platform Robot | Xung đột Domain Mismatch | Nguy cơ Rò rỉ / Nguồn | Tính khả thi làm Source Domain | Tính khả thi làm Held-out Target | Hạn chế cốt lõi (Main Limitation) |
|---|:---:|:---:|:---:|:---:|:---:|---|---|:---:|---|:---:|:---:|---|
| **`coal_conveyor`** | 1.121 | 865 | 256 | 822 | 299 | Đầy đủ (L1: 169, L2: 83, L3: 4, L4: 865) | 100% SuspendedRail (1.121/1.121) | 0 | Rò rỉ chuỗi `cigarette`, `hand`, `phone` xuyên split; 3 cặp Exact | **CAO** | **TRUNG BÌNH** | 100% gắn chặt với robot ray treo; góc nhìn từ trên cao cố định. |
| **`metallurgy`** | 720 | 711 | **9** | 543 | 177 | L4: 711, L1: 8, L2: **0**, L3: 1 | 91,8% Wheeled (661), 8,2% Rail (59) | **8 mẫu** Anomaly có text `oil_chemical` | Cặp Exact số 4 rò rỉ sang `oil_chemical`; chỉ số frame index ~25/75 | **RẤT THẤP** (Thiếu Anomaly) | **KHÔNG KHẢ THI** (cho Anomaly) | **Test Anomaly = 0**. 8/9 Anomaly ở Train thực chất là ảnh bối cảnh hóa chất. Không thể đo F1/Recall bất thường trên target này. |
| **`oil_chemical`** | 1.023 | 662 | **361** | 778 | 245 | L1: 304, L2: 57, L3: **0**, L4: 662 | 90,2% Wheeled (923), 9,8% Rail (100) | Nhận 32 mẫu từ domain khác theo TXT | 3 cặp Exact rò rỉ xuyên split (`phone`, `hand`); rò rỉ chuỗi video liên tục | **CAO** | **CAO** | Không có mẫu Level03 nào; tỷ lệ Anomaly cao áp đảo (35,3%) tạo chênh lệch phân bố lớn. |
| **`power`** | 869 | 767 | 102 | 656 | 213 | L1: 33, L2: 68, L3: 1, L4: 767 | 87,8% Wheeled (763), 12,2% Rail (106) | 4 mẫu Normal có text `coal_conveyor` | Rò rỉ chuỗi `others`, `fire`; dHash candidates cao | **TRUNG BÌNH** | **TRUNG BÌNH** | Test chỉ có 2 mẫu Level01 (0,94%); chủ yếu là lỗi đóng/mở tủ và người ngã; ít đa dạng nguy cơ. |
| **`tunnel`** | 1.280 | 1.008 | 272 | 964 | 316 | Đầy đủ nhất (L1: 145, L2: 118, L3: 9, L4: 1.008) | 98,1% SuspendedRail (1.256), 1,9% Wheeled (24) | 24 mẫu Normal có text `oil_chemical` | 1 cặp Exact; rò rỉ tuyệt đối chuỗi video `nonmobile` (người đi xe đạp 40 giây) | **CAO** | **CAO** | Chiếm 60% tổng số mẫu Level03 của toàn bộ dataset (9/15 mẫu); gần như thuần túy robot ray treo. |

---

## 6. Confounding Analysis (Phân tích các yếu tố gây nhiễu)

### 6.1 Platform Confounding (Nhiễu nền tảng Robot & Góc nhìn cảm biến)

Phân tích chéo ma trận `robot_platform × folder_domain` bộc lộ sự gắn kết gần như tuyệt đối:

- **Robot ray treo (`SuspendedRail`):** Chiếm **100%** mẫu của `coal_conveyor` (1.121/1.121) và **98,1%** mẫu của `tunnel` (1.256/1.280). 24 mẫu `Wheeled` duy nhất trong thư mục `tunnel` thực chất là các mẫu bị xung đột nhãn có text mô tả `oil_chemical`.
- **Robot bánh lăn (`Wheeled`):** Chiếm **91,8%** mẫu của `metallurgy` (661/720), **90,2%** mẫu của `oil_chemical` (923/1.023) và **87,8%** mẫu của `power` (763/869).

> [!WARNING]
> **Rủi ro gây nhiễu phương pháp luận:** Nếu một mô hình VLM có hiệu năng suy luận an toàn vượt trội trên `coal_conveyor` so với `oil_chemical`, **chúng ta hoàn toàn KHÔNG THỂ phân tách một cách độc lập** rằng sự khác biệt đó bắt nguồn từ:
> 1. Bản chất ngữ cảnh công nghiệp (than đá vs hóa chất),
> 2. Nền tảng cơ học của robot (ray treo trên trần vs xe lăn mặt sàn),
> 3. Góc nhìn hình học của camera (góc cắm dốc 45–60 độ nhìn xuống vs góc chụp ngang tầm mắt công nhân), hay
> 4. Phong cách thu thập dữ liệu (robot ray chạy dọc tuyến cố định vs robot bánh lăn dừng tại các góc cua).
> SafeShift **tuyệt đối không đưa ra tuyên bố quan hệ nhân quả (causal claim)** về năng lực thích ứng miền công nghiệp thuần túy mà không chú thích yếu tố nhiễu nền tảng robot này.

### 6.2 Safety-label Confounding (Nhiễu phân bố nhãn an toàn theo miền)

Sự phân bố các cấp độ an toàn (`safety_level`) giữa các miền là cực kỳ bất đối xứng:

1. **Hiếm mẫu Level03:** Toàn bộ 5.013 mẫu chỉ có **15 mẫu Level03 (0,299%)**. Đáng chú ý, **100% mẫu Level03 (15/15) đều được thu thập bởi robot ray treo `SuspendedRail`** (9 ở tunnel, 4 ở coal_conveyor, 1 ở power, 1 ở metallurgy, 0 ở oil_chemical).
2. **Metallurgy gần như thuần khiết Normal:** 98,75% mẫu là Level04 (711/720). Trong 9 mẫu bất thường, có 8 mẫu Level01 nhưng cả 8 mẫu đều mang text mô tả `oil_chemical`.
3. **Oil & Gas là tâm điểm Anomaly:** Chiếm tới 36,1% tổng số mẫu bất thường của toàn bộ dataset (361/1.000) và 46,1% tổng số mẫu Level01 (304/659).
4. **Hệ quả nghiên cứu:** Nhận diện miền và dự đoán an toàn bị liên kết chặt (confounded). Một mô hình học máy có thể chỉ cần ghi nhớ shortcut: *"Nếu thấy khung cảnh nhà máy dầu khí hoặc góc nhìn bánh lăn -> khả năng cao là Level01; nếu thấy khung cảnh luyện kim -> luôn đoán Level04"*. Điều này tạo ra rủi ro shortcut learning nghiêm trọng.

### 6.3 Source / Sequence Confounding (Nhiễu nguồn và chuỗi thời gian)

1. **Rò rỉ xuyên Split:** Kiểm định Bước 4–5 đã xác nhận 7 cặp ảnh trùng khớp từng pixel và 833 cặp tương đồng perceptual cao xuyên qua `train` và `test`.
2. **Phân chia theo thứ tự chỉ số nội bộ họ nguồn (~25/75 partition):** Cả 12 họ nguồn Anomaly đều bị chia cắt cơ học (khung hình đầu cho test, khung hình sau cho train). Điển hình như họ `nonmobile`, khung hình thứ 25 (`test`) và khung hình thứ 26 (`train`) chỉ cách nhau một phần giây trong cùng một đoạn video ngắn 40 giây ghi cảnh một người đi xe đạp trong hầm.
3. **Ý nghĩa đối với Split chính thức:** Phân chia `train`/`test` chính thức của tác giả **không bảo đảm tính độc lập về mặt ngữ cảnh và chuỗi thời gian**. Dù `point_id overlap = 0`, các điểm logic này thực chất chia sẻ chung chuỗi quay và góc máy. Sử dụng nguyên trạng split chính thức để tuyên bố năng lực tổng quát hóa sẽ khiến kết quả bị thổi phồng do hiện tượng ghi nhớ chuỗi (sequence memorization).

---

## 7. Đánh giá tính khả thi của các Protocol ứng viên (Candidate Protocols)

Dưới đây là phân tích khoa học đối với các giao thức thử nghiệm cross-domain có thể cân nhắc cho W2:

| Protocol ứng viên | Ý nghĩa khoa học (Scientifically Meaningful?) | Dữ liệu InspecSafe-V1 có hỗ trợ? (Supported?) | Rào cản cốt lõi (Major Blocker) | Thuật ngữ khuyến nghị sử dụng |
|---|:---:|:---:|---|---|
| **A. Official split + Per-domain reporting** | Thấp - Trung bình | **CÓ** (Dùng nguyên trạng) | Bị rò rỉ chuỗi thời gian xuyên split; miền `metallurgy` có Test Anomaly = 0 nên không đo được khả năng phát hiện lỗi. | *Per-Domain In-Distribution Evaluation* (Đánh giá theo miền trên phân chia chính thức) |
| **B. Leave-One-Domain-Out (LODO)** | Rất cao (Chuẩn mực của Domain Generalization) | **MỘT PHẦN** | Không thể dùng `metallurgy` làm target độc lập (vì không có Anomaly ở test, và tổng anomaly chỉ có 9 mẫu bị nghi ngờ về domain). | *Cross-Domain Generalization (Sub-benchmark on 4 domains)* |
| **C. Train on Source Domains $\rightarrow$ Evaluate Unseen Target** | Cao | **CÓ** (Ngoại trừ target `metallurgy`) | Bị nhiễu nghiêm trọng bởi platform: nếu train trên các miền dùng `Wheeled` (oil, power) rồi test trên miền `SuspendedRail` (coal, tunnel), mô hình chịu đồng thời cả domain-shift lẫn platform/viewpoint-shift. | *Cross-Domain & Platform Transfer Evaluation* |
| **D. Frozen Pretrained VLM Per-Domain Evaluation** | **CAO NHẤT (Thực tế nhất)** | **HOÀN TOÀN HỖ TRỢ** | Không cần train/tune nên loại trừ được rủi ro rò rỉ tập train vào tập test; đánh giá được zero-shot robustness thuần túy của các foundation models hiện đại. | **Cross-Domain Robustness Evaluation** hoặc **Zero-shot Cross-Domain Evaluation** |
| **E. Group-aware / Site-aware Domain Split** | Cao | **MỘT PHẦN** (Đòi hỏi thiết kế split mới ở W2) | Khó tái lập hoàn toàn ranh giới video nếu không gom nhóm triệt để 12 source families; đòi hỏi sự đồng thuận và phê duyệt chính thức trong `DECISIONS.md`. | *Leakage-Free Grouped Domain Split* |

---

## 8. Domain Generalization vs. Robustness: Chuẩn hóa thuật ngữ

SafeShift cần phân định rạch ròi giữa hai khái niệm dễ bị đánh đồng trong các báo cáo khoa học:

1. **Domain Generalization (DG — Khái quát hóa miền):**
   - **Định nghĩa học thuật:** Mô hình được tối ưu hóa/huấn luyện (training, fine-tuning, adapter tuning) trên một hoặc nhiều miền nguồn (source domains $\mathcal{D}_S$) với mục tiêu tối thiểu hóa rủi ro trên một miền đích hoàn toàn chưa từng thấy ($\mathcal{D}_T \notin \mathcal{D}_S$).
   - **Điều kiện trên InspecSafe-V1:** Chỉ áp dụng được nếu SafeShift tiến hành huấn luyện/tinh chỉnh mô hình trên một tập con các miền và kiểm thử trên miền còn lại.
2. **Cross-Domain Robustness (Độ bền vững xuyên miền):**
   - **Định nghĩa học thuật:** Đánh giá mức độ suy giảm hoặc biến thiên hiệu năng của một mô hình cố định (ví dụ mô hình nền tảng đa phương thức **Frozen Pretrained VLM**) khi đưa qua các miền dữ liệu công nghiệp khác nhau mà không thực hiện bất kỳ bước huấn luyện hay thích ứng tham số nào trên dữ liệu nguồn của benchmark.
   - **Khuyến nghị cho SafeShift Seminar:** Nếu phạm vi Seminar tập trung vào đánh giá các mô hình VLM thương mại hoặc mã nguồn mở có sẵn (như GPT-4o, Gemini 1.5 Pro, Qwen2-VL, InternVL2) ở chế độ **Zero-shot / Few-shot không huấn luyện lại**, thuật ngữ chuẩn xác và trung thực nhất phải là:  
     > **"Cross-Domain Robustness Evaluation"** hoặc **"Zero-Shot Cross-Domain Evaluation of VLMs"**.

---

## 9. Evidence Annotation Inventory (Kiểm kê chú thích bằng chứng)

Khảo sát toàn diện 100% tệp JSON và TXT xác minh danh mục các dạng chú thích thực sự tồn tại trong InspecSafe-V1:

| Loại Annotation | Tình trạng thực tế trong InspecSafe-V1 | Định dạng lưu trữ | Ý nghĩa đối với bài toán Grounding |
|---|:---:|---|---|
| **Polygon annotations** | **CÓ** (37.434 đa giác) | Tọa độ điểm thực tế `points: [[x, y], ...]` trong trường `shapes[]` của LabelMe JSON. | Là chú thích đối tượng hình học (Object Bounding Polygons), không phải nhãn lý do an toàn. |
| **Raw Object Labels** | **CÓ** (231 nhãn duy nhất) | Chuỗi văn bản trong trường `label` (tiếng Anh, trừ 1 nhãn tiếng Trung `"出口"`). | Danh mục định danh vật thể (ví dụ: `Person`, `Cigarette`, `Pipeline`, `Motor`). |
| **One-line Text Descriptions** | **CÓ** (5.013 tệp) | Chuỗi văn bản tiếng Anh một dòng trong tệp `.txt`. | Mô tả ngữ nghĩa tổng quát bối cảnh và kết luận cấp độ an toàn; **không chứa tọa độ**. |
| **Safety Level Ground Truth** | **CÓ** (4 cấp độ) | Token `Level01`–`Level04` trong tên thư mục điểm. | Nhãn mục tiêu phân loại mức độ an toàn cấp hình ảnh (Image-level Safety Classification). |
| **Bounding Boxes (BBox)** | **KHÔNG CÓ SẴN (DERIVED)** | Không có trường `bbox` độc lập trong schema JSON. | Có thể suy ra hộp bao ngoại tiếp (axis-aligned bounding box) từ tọa độ đa giác, nhưng là dữ liệu dẫn xuất. |
| **Official Binary Masks** | **KHÔNG CÓ SẴN (DERIVED)** | Không phân phối tệp ảnh mask nhị phân (`.png`). | Có thể rasterize đa giác thành mask, nhưng dataset không chứa ground truth mask chính thức. |
| **Hazard-Specific Evidence Region** | **KHÔNG CÓ** | Không có trường khoanh vùng riêng cho "vùng bằng chứng gây mất an toàn". | Không có nhãn phân định vùng nào là vùng nguy cơ chính giải thích cho quyết định xếp cấp an toàn. |
| **Human Rationale Region** | **KHÔNG CÓ** | Không có trường ghi nhận vùng chú ý của chuyên gia an toàn con người. | Không thể khẳng định chuyên gia đã dựa vào đâu để ra quyết định nếu không suy đoán từ nhãn vật thể. |
| **Phrase-to-Region Alignment** | **KHÔNG CÓ** | Không có liên kết (linking pointer / index) từ từ ngữ trong TXT sang polygon trong JSON. | Không thể làm bài toán Phrase Grounding chuẩn (ví dụ RefCOCO) vì thiếu ánh xạ giữa cụm từ và đa giác. |
| **Evidence-to-Safety-Level Mapping**| **KHÔNG CÓ** | Không có trọng số hoặc cờ liên kết giữa đa giác và cấp an toàn. | Không biết đa giác nào trong số hàng chục đa giác của ảnh là nguyên nhân trực tiếp dẫn tới Level 1 hay Level 2. |
| **Object-to-Hazard Mapping** | **KHÔNG CÓ** | Không có taxonomy chính thức quy định nhãn nào cấu thành nguy cơ. | Phải dựa vào heuristic (ví dụ `Cigarette` $\rightarrow$ nguy cơ hút thuốc). |
| **Absent-Object Annotation** | **KHÔNG CÓ** | Không có tọa độ cho "vị trí thiếu vật thể". | Các lỗi như "không đội mũ", "không đeo găng" hoàn toàn không có bounding box cho "mũ bị thiếu". |
| **Relation / Interaction Annotation**| **KHÔNG CÓ** | Trường `kie_linking: []` và `group_id: null` trên 100% shapes. | Không có chú thích quan hệ không gian hoặc tương tác giữa người và thiết bị. |
| **Action Annotation** | **KHÔNG CÓ** | Toàn bộ 231 nhãn đều là danh từ hoặc cụm danh từ. | Không có nhãn hành động (action verbs) như `calling`, `smoking`, `falling`, `opening`. |

---

## 10. Phân biệt then chốt: Polygon Annotation $\neq$ Hazard Evidence Grounding

Một sai lầm phương pháp luận phổ biến là mặc định xem các đa giác phân vùng đối tượng có sẵn trong dataset là Ground Truth cho bài toán giải thích an toàn. Cần phân định rõ ràng hai khái niệm:

1. **Object Annotation (Chú thích đối tượng):**  
   - Trả lời câu hỏi: *"Vật thể X nằm ở đâu trong ảnh?"*  
   - Ví dụ: Trong ảnh có một người và một chiếc điện thoại, annotator khoanh vùng đa giác nhãn `Person` và đa giác nhãn `Mobile Phone`.
2. **Evidence Grounding (Chú thích bằng chứng quyết định an toàn):**  
   - Trả lời câu hỏi: *"Vùng thị giác nào chứng minh và giải thích cho việc ảnh này bị xếp vào mức nguy cơ Cấp 1?"*  
   - Ví dụ 1: Với hành vi *"công nhân sử dụng điện thoại di động"*, đa giác `Mobile Phone` có thể đóng vai trò là một **vùng bằng chứng đại diện (evidence proxy)** hợp lý.
   - Ví dụ 2: Với hành vi vi phạm *"công nhân không đội mũ bảo hộ lao động"* (`worker not wearing safety helmet`), đối tượng bị thiếu là chiếc mũ. Đa giác `Person` hiện có chỉ bao quanh toàn bộ cơ thể công nhân. **Đa giác `Person` không trực tiếp chú thích sự vắng mặt của chiếc mũ**. Nếu coi `Person` là ground truth tuyệt đối, một mô hình tập trung vào đôi giày của công nhân nhưng rơi vào trong hộp bao `Person` vẫn được tính là "grounding chính xác", dẫn đến đánh giá sai lệch bản chất.

---

## 11. Evidence Type Taxonomy (Phân loại bằng chứng phục vụ kiểm toán)

Để đánh giá tính khả thi một cách định lượng, 6 loại hình bằng chứng nguy cơ được thiết lập phục vụ quá trình audit:

| Mã loại bằng chứng | Tên phân loại (Evidence Type) | Bản chất sự kiện nguy cơ | Ví dụ thực tế trong InspecSafe-V1 | Khả năng Grounding bằng Annotation hiện có |
|---|---|---|---|:---:|
| **A** | `PRESENT_OBJECT_LOCALIZABLE` | Nguy cơ gắn liền với một vật thể vật lý hiện hữu cụ thể có thể khoanh vùng. | Hút thuốc (`Cigarette`), Dùng điện thoại (`Mobile Phone`), Ngọn lửa trần (`Open Flame`), Dầu/nước rò rỉ (`Liquid`), Dị vật rác (`Plastic Bag`). | **Khả thi trực tiếp (DIRECT_SUPPORT)** nếu vật thể đó được gán nhãn đa giác riêng. |
| **B** | `PERSON_OR_OBJECT_STATE` | Nguy cơ phụ thuộc vào tư thế, trạng thái cơ học hoặc tình trạng của người/thiết bị. | Người nằm trên sàn/ngã (`Person on ground`), Cửa tủ điện bị mở bất thường (`Cabinet door abnormally open`). | **Chỉ hỗ trợ Proxy gián tiếp (PARTIAL_PROXY)** qua đối tượng mang trạng thái; không có vùng riêng cho bản thân trạng thái. |
| **C** | `RELATIONAL_OR_INTERACTION` | Nguy cơ phát sinh từ mối quan hệ không gian hoặc tương tác vi phạm quy định giữa nhiều thực thể. | Xe thô sơ di chuyển lấn vào làn đường xe cơ giới trong hầm (`Non-motorized vehicle occupying motor vehicle lane`). | **Chỉ hỗ trợ Proxy gián tiếp (PARTIAL_PROXY)** qua các đối tượng thành phần (`Person`, `Bicycle`, `Car`); thiếu quan hệ vi phạm. |
| **D** | `ABSENCE_BASED` | Nguy cơ xuất phát từ sự thiếu vắng trang thiết bị bảo hộ cá nhân (PPE) bắt buộc. | Không đội mũ bảo hộ (`no helmet`), Không đeo găng tay (`no gloves`), Không đeo khẩu trang (`no mask`). | **Chỉ hỗ trợ Proxy yếu (PARTIAL_PROXY)** qua đa giác `Person` toàn thân; hoàn toàn thiếu vùng cục bộ cho vị trí bị thiếu. |
| **E** | `SCENE_OR_CONTEXT_LEVEL` | Nguy cơ mang tính khuếch tán diện rộng hoặc phụ thuộc toàn cảnh môi trường. | Khói bụi mờ mịt bao trùm phân xưởng (`Smog/Smoke in scene`), Ánh sáng không đạt chuẩn. | **Không có hỗ trợ trực tiếp (NO_DIRECT_SUPPORT)** nếu khói lan tỏa toàn cảnh không tạo ranh giới đa giác rõ ràng. |
| **F** | `AMBIGUOUS_OR_UNMAPPABLE` | Mô tả mơ hồ, dùng thuật ngữ chung chung không thể ánh xạ nhất quán sang đa giác nào. | "Có dị vật bất thường" (`There is a foreign object`), "Thiết bị bất thường". | **Hoàn toàn không thể đánh giá (AMBIGUOUS / UNMAPPABLE)** nếu thiếu quy ước giải thích của con người. |

---

## 12. Targeted Evidence Feasibility Review (Kiểm tra thực nghiệm trên 63 mẫu Anomaly)

### 12.1 Quy tắc lấy mẫu phân tầng xác định (Deterministic Stratified Sampling)

Để có kết luận định lượng xác thực, một tập mẫu gồm **63 mẫu Anomaly** được trích xuất có phương pháp từ 1.000 mẫu bất thường:

- **Tầng 1 (Toàn bộ Anomaly của Metallurgy):** Lấy toàn bộ **9/9 mẫu** Anomaly của miền luyện kim (8 mẫu Level01 ở train có text `oil_chemical` và 1 mẫu Level03 ở train).
- **Tầng 2 (Toàn bộ Anomaly của Level03):** Lấy toàn bộ **14 mẫu Level03 còn lại** trên toàn dataset (4 coal_conveyor, 1 power, 9 tunnel; mẫu Level03 của metallurgy đã nằm ở Tầng 1). Như vậy kiểm toán bao phủ **100% mẫu Level03 (15/15)** của dataset.
- **Tầng 3 (Các mẫu thuộc 7 cặp Exact Duplicates Cross-split):** Lấy toàn bộ **13 mẫu Anomaly còn lại** tham gia vào 7 cặp trùng lặp pixel tuyệt đối (1 mẫu đã nằm ở Tầng 1).
- **Tầng 4 (Bao phủ có hệ thống 12 Họ nguồn và 5 Miền):** Bổ sung xác định các mẫu có chỉ số nhỏ nhất (`counter` nhỏ nhất) trong từng họ nguồn chưa có đại diện ở train hoặc test, và bổ sung các mẫu đại diện cho Level01/Level02 của `power`, `oil_chemical`, `coal_conveyor`, `tunnel`.

Danh mục đầy đủ 63 mẫu kiểm toán được lưu trữ cục bộ trong artifact:  
`data/manifests/research_feasibility_sample.json` (giữ local, không commit lên Git).

### 12.2 Bảng tổng hợp kiểm định 63 mẫu thực nghiệm

| STT | Mã mẫu (`sample_id`) | Split | Miền thư mục | Cấp an toàn | Tóm tắt nguy cơ trong TXT | Nhãn đối tượng liên quan | Loại bằng chứng (`Evidence Type`) | Mức hỗ trợ của Polygon | Có thể đánh giá Grounding không cần nhãn mới? |
|:---:|---|:---:|:---:|:---:|---|---|:---:|:---:|:---:|
| 01 | `coal_conveyor-Level01-SuspendedRail-002499-001` | train | coal_conveyor | Level01 | Person lying on the ground | `Person` | `PERSON_OR_OBJECT_STATE` | `PARTIAL_PROXY` | PARTIAL |
| 02 | `coal_conveyor-Level01-SuspendedRail-002589-001` | train | coal_conveyor | Level01 | Personnel not wearing safety helmets | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 03 | `coal_conveyor-Level01-SuspendedRail-002591-001` | train | coal_conveyor | Level01 | There is smoke | `Smoke` | `PRESENT_OBJECT_LOCALIZABLE` | `DIRECT_SUPPORT` | **YES** |
| 04 | `coal_conveyor-Level02-SuspendedRail-002653-001` | train | coal_conveyor | Level02 | Personnel use mobile phones | `Mobile Phone` | `PRESENT_OBJECT_LOCALIZABLE` | `DIRECT_SUPPORT` | **YES** |
| 05 | `coal_conveyor-Level02-SuspendedRail-002654-001` | train | coal_conveyor | Level02 | Personnel use mobile phones | `Mobile Phone` | `PRESENT_OBJECT_LOCALIZABLE` | `DIRECT_SUPPORT` | **YES** |
| 06 | `coal_conveyor-Level03-SuspendedRail-002657-001` | train | coal_conveyor | Level03 | Water accumulation on the ground | `Liquid` | `PRESENT_OBJECT_LOCALIZABLE` | `DIRECT_SUPPORT` | **YES** |
| 07 | `metallurgy-Level01-SuspendedRail-002658-001` | train | metallurgy | Level01 | Open flame in oil and gas environment | `Open Flame` | `PRESENT_OBJECT_LOCALIZABLE` | `DIRECT_SUPPORT` | **YES** |
| 08 | `metallurgy-Level01-SuspendedRail-002659-001` | train | metallurgy | Level01 | Using mobile phones & not wearing PPE | `Mobile Phone`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 09 | `metallurgy-Level01-SuspendedRail-002660-001` | train | metallurgy | Level01 | Not wearing gloves, masks, helmets | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 10 | `metallurgy-Level01-SuspendedRail-002661-001` | train | metallurgy | Level01 | Making phone calls & not wearing PPE | `Mobile Phone`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 11 | `metallurgy-Level01-SuspendedRail-002662-001` | train | metallurgy | Level01 | Making phone calls & not wearing PPE | `Mobile Phone`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 12 | `metallurgy-Level01-SuspendedRail-002663-001` | train | metallurgy | Level01 | Making phone calls & not wearing PPE | `Mobile Phone`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 13 | `metallurgy-Level01-SuspendedRail-002664-001` | train | metallurgy | Level01 | Use mobile phones & not wearing PPE | `Mobile Phone`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 14 | `metallurgy-Level01-SuspendedRail-002665-001` | train | metallurgy | Level01 | Use mobile phones & not wearing PPE | `Mobile Phone`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 15 | `metallurgy-Level03-SuspendedRail-002666-001` | train | metallurgy | Level03 | Water accumulation on the ground | `Liquid` | `PRESENT_OBJECT_LOCALIZABLE` | `DIRECT_SUPPORT` | **YES** |
| 16 | `oil_chemical-Level01-Wheeled-002667-001` | train | oil_chemical | Level01 | Smoking & not wearing helmet/gloves | `Cigarette`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 17 | `oil_chemical-Level01-Wheeled-002742-001` | train | oil_chemical | Level01 | Water in picture & not wearing gloves | `Liquid`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 18 | `oil_chemical-Level01-Wheeled-002757-001` | train | oil_chemical | Level01 | Smoking & not wearing helmet/gloves | `Cigarette`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 19 | `oil_chemical-Level01-Wheeled-002758-001` | train | oil_chemical | Level01 | Smoking & not wearing helmet/gloves | `Cigarette`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 20 | `oil_chemical-Level02-Wheeled-002906-001` | train | oil_chemical | Level02 | Water accumulation on the ground | `Liquid` | `PRESENT_OBJECT_LOCALIZABLE` | `DIRECT_SUPPORT` | **YES** |
| 21 | `power-Level01-SuspendedRail-002954-001` | train | power | Level01 | Person on the ground | `Person` | `PERSON_OR_OBJECT_STATE` | `PARTIAL_PROXY` | PARTIAL |
| 22 | `power-Level01-SuspendedRail-002955-001` | train | power | Level01 | Person on the ground | `Person` | `PERSON_OR_OBJECT_STATE` | `PARTIAL_PROXY` | PARTIAL |
| 23 | `power-Level02-SuspendedRail-002985-001` | train | power | Level02 | Not wearing gloves, masks, helmets | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 24 | `power-Level02-SuspendedRail-002986-001` | train | power | Level02 | Not wearing gloves, masks, helmets | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 25 | `tunnel-Level01-SuspendedRail-003062-001` | train | tunnel | Level01 | Non-motorized vehicle occupying motor lane | `Person` | `RELATIONAL_OR_INTERACTION` | `PARTIAL_PROXY` | PARTIAL |
| 26 | `tunnel-Level02-SuspendedRail-003138-001` | train | tunnel | Level02 | Cabinet door abnormally open | *Không có BBox cửa* | `PERSON_OR_OBJECT_STATE` | `NO_DIRECT_SUPPORT` | **NO** |
| 27 | `tunnel-Level02-SuspendedRail-003148-001` | train | tunnel | Level02 | Not wearing gloves, helmets, masks | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 28 | `tunnel-Level02-SuspendedRail-003158-001` | train | tunnel | Level02 | Do not wear gloves, masks, helmets | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 29 | `tunnel-Level02-SuspendedRail-003195-001` | train | tunnel | Level02 | Plastic bags and bottles on ground | `Plastic Bag`, `Water Bottle` | `PRESENT_OBJECT_LOCALIZABLE` | `DIRECT_SUPPORT` | **YES** |
| 30 | `tunnel-Level03-SuspendedRail-003229-001` | train | tunnel | Level03 | Personnel do not wear gloves | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 31 | `tunnel-Level03-SuspendedRail-003230-001` | train | tunnel | Level03 | Personnel do not wear gloves | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 32 | `tunnel-Level03-SuspendedRail-003231-001` | train | tunnel | Level03 | Water accumulation on the ground | `Liquid` | `PRESENT_OBJECT_LOCALIZABLE` | `DIRECT_SUPPORT` | **YES** |
| 33 | `tunnel-Level03-SuspendedRail-003232-001` | train | tunnel | Level03 | Water accumulation on the walls | `Liquid` | `PRESENT_OBJECT_LOCALIZABLE` | `DIRECT_SUPPORT` | **YES** |
| 34 | `tunnel-Level03-SuspendedRail-003233-001` | train | tunnel | Level03 | Water accumulation on the walls | `Liquid` | `PRESENT_OBJECT_LOCALIZABLE` | `DIRECT_SUPPORT` | **YES** |
| 35 | `tunnel-Level03-SuspendedRail-003234-001` | train | tunnel | Level03 | Water accumulation on the walls | `Liquid` | `PRESENT_OBJECT_LOCALIZABLE` | `DIRECT_SUPPORT` | **YES** |
| 36 | `coal_conveyor-Level01-SuspendedRail-002235-001` | test | coal_conveyor | Level01 | Smoking & not wearing helmet/gloves | `Cigarette`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 37 | `coal_conveyor-Level01-SuspendedRail-002273-001` | test | coal_conveyor | Level01 | Not wearing gloves, masks, helmets | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 38 | `coal_conveyor-Level02-SuspendedRail-002295-001` | test | coal_conveyor | Level02 | Personnel are not wearing gloves | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 39 | `coal_conveyor-Level02-SuspendedRail-002313-001` | test | coal_conveyor | Level02 | Use mobile phones & not wear gloves | `Mobile Phone`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 40 | `coal_conveyor-Level02-SuspendedRail-002314-001` | test | coal_conveyor | Level02 | Use mobile phones & not wear gloves | `Mobile Phone`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 41 | `coal_conveyor-Level02-SuspendedRail-002315-001` | test | coal_conveyor | Level02 | Use mobile phones & not wear gloves | `Mobile Phone`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 42 | `coal_conveyor-Level03-SuspendedRail-002316-001` | test | coal_conveyor | Level03 | Personnel not wearing masks or gloves | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 43 | `coal_conveyor-Level03-SuspendedRail-002317-001` | test | coal_conveyor | Level03 | Personnel not wearing masks or gloves | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 44 | `coal_conveyor-Level03-SuspendedRail-002318-001` | test | coal_conveyor | Level03 | Personnel not wearing masks or gloves | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 45 | `oil_chemical-Level01-Wheeled-002321-001` | test | oil_chemical | Level01 | Smoking & not wearing helmet/gloves | `Cigarette`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 46 | `oil_chemical-Level01-Wheeled-002322-001` | test | oil_chemical | Level01 | Smoking & not wearing helmet/gloves | `Cigarette`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 47 | `oil_chemical-Level01-Wheeled-002324-001` | test | oil_chemical | Level01 | Open flame & not wearing gloves | `Open Flame`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 48 | `oil_chemical-Level01-Wheeled-002325-001` | test | oil_chemical | Level01 | Open flame & not wearing gloves | `Open Flame`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 49 | `oil_chemical-Level01-Wheeled-002329-001` | test | oil_chemical | Level01 | No gloves, smoke, liquid on ground | `Liquid`, `Person` | `PRESENT_OBJECT_LOCALIZABLE` | `PARTIAL_PROXY` | PARTIAL |
| 50 | `oil_chemical-Level01-Wheeled-002353-001` | test | oil_chemical | Level01 | Not wearing masks and gloves | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 51 | `oil_chemical-Level01-Wheeled-002369-001` | test | oil_chemical | Level01 | There is smoke | `Smoke` | `PRESENT_OBJECT_LOCALIZABLE` | `DIRECT_SUPPORT` | **YES** |
| 52 | `oil_chemical-Level02-Wheeled-002384-001` | test | oil_chemical | Level02 | Cabinet door abnormally open | *Không có BBox cửa* | `PERSON_OR_OBJECT_STATE` | `NO_DIRECT_SUPPORT` | **NO** |
| 53 | `power-Level01-SuspendedRail-002393-001` | test | power | Level01 | Person on the ground | `Person` | `PERSON_OR_OBJECT_STATE` | `PARTIAL_PROXY` | PARTIAL |
| 54 | `power-Level01-SuspendedRail-002394-001` | test | power | Level01 | Person on the ground | `Person` | `PERSON_OR_OBJECT_STATE` | `PARTIAL_PROXY` | PARTIAL |
| 55 | `power-Level02-SuspendedRail-002395-001` | test | power | Level02 | Cabinet door abnormally open | *Không có BBox cửa* | `PERSON_OR_OBJECT_STATE` | `NO_DIRECT_SUPPORT` | **NO** |
| 56 | `power-Level02-SuspendedRail-002396-001` | test | power | Level02 | Personnel are not wearing gloves | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 57 | `power-Level03-SuspendedRail-002413-001` | test | power | Level03 | Personnel are not wearing masks | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 58 | `tunnel-Level01-SuspendedRail-002420-001` | test | tunnel | Level01 | Non-motorized vehicle in motor lane | `Bicycle`, `Person` | `RELATIONAL_OR_INTERACTION` | `PARTIAL_PROXY` | PARTIAL |
| 59 | `tunnel-Level02-SuspendedRail-002465-001` | test | tunnel | Level02 | Do not wear gloves, masks, helmets | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 60 | `tunnel-Level02-SuspendedRail-002473-001` | test | tunnel | Level02 | There is a foreign object | `Plastic Bag` *(mơ hồ)* | `AMBIGUOUS_OR_UNMAPPABLE` | `AMBIGUOUS` | **NO** |
| 61 | `tunnel-Level03-SuspendedRail-002483-001` | test | tunnel | Level03 | Personnel are not wearing masks | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 62 | `tunnel-Level03-SuspendedRail-002484-001` | test | tunnel | Level03 | Personnel are not wearing masks | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |
| 63 | `tunnel-Level03-SuspendedRail-002485-001` | test | tunnel | Level03 | Personnel are not wearing masks | `Person` | `ABSENCE_BASED` | `PARTIAL_PROXY` | PARTIAL |

---

## 13. Evidence-Type Findings (Tổng kết phát hiện định lượng trên tập mẫu)

Từ bảng khảo sát 63 mẫu thực nghiệm:

### 13.1 Phân bố trạng thái hỗ trợ của Polygon (Support Status)

- **Tổng số mẫu thẩm định chuyên sâu:** **63 mẫu Anomaly** (35 train / 28 test).
- **`DIRECT_SUPPORT` (Hỗ trợ trực tiếp):** **13 mẫu (20,6%)**  
  Chỉ có khoảng 1/5 số mẫu bất thường sở hữu đa giác bao quanh chính xác thực thể nguy cơ (như `Open Flame`, `Liquid`, `Smoke`, `Mobile Phone`, `Plastic Bag`).
- **`PARTIAL_PROXY` (Hỗ trợ đại diện gián tiếp):** **46 mẫu (73,0%)**  
  Gần 3/4 số mẫu chỉ có thể đánh giá qua đối tượng đại diện: đa giác `Person` cho các vi phạm thiếu PPE (mũ, găng tay, khẩu trang) hoặc tư thế người ngã; hoặc các mẫu kết hợp đa nguy cơ (có điện thoại/thuốc lá nhưng đồng thời có vi phạm không đeo găng).
- **`NO_DIRECT_SUPPORT` (Hoàn toàn không có hỗ trợ):** **3 mẫu (4,8%)**  
  Toàn bộ các mẫu thuộc họ `dooropen` (cửa tủ mở bất thường: mẫu 26, 52, 55) hoàn toàn không có đa giác nào khoanh vùng chiếc tủ hay cánh cửa bị mở.
- **`AMBIGUOUS` (Mơ hồ / Không thể ánh xạ):** **1 mẫu (1,6%)**  
  Mẫu mô tả "foreign object" (dị vật) nhưng annotation chỉ khoanh `Plastic Bag` và `Protective Net` mà không có định nghĩa chuẩn hóa.

### 13.2 Phân bố theo 6 loại hình bằng chứng nguy cơ

- **`PRESENT_OBJECT_LOCALIZABLE`:** **31 mẫu (49,2%)**  
  (13 mẫu có direct support, 18 mẫu là ca đa nguy cơ kết hợp có proxy PPE).
- **`ABSENCE_BASED`:** **21 mẫu (33,3%)**  
  (100% thuộc nhóm này chỉ có thể đánh giá qua proxy `Person`).
- **`PERSON_OR_OBJECT_STATE`:** **8 mẫu (12,7%)**  
  (5 mẫu người ngã có proxy `Person`, 3 mẫu cửa tủ mở không có hỗ trợ).
- **`RELATIONAL_OR_INTERACTION`:** **2 mẫu (3,2%)**  
  (2 mẫu xe thô sơ đi vào làn ô tô trong hầm; có proxy `Person` và `Bicycle`).
- **`SCENE_OR_CONTEXT_LEVEL`:** **0 mẫu (0,0%)** trong tập 63 mẫu chọn lọc (do các mẫu khói trong tập này đều được vẽ đa giác `Smoke`).
- **`AMBIGUOUS_OR_UNMAPPABLE`:** **1 mẫu (1,6%)**.

### 13.3 Đánh giá khả năng thực thi Grounding không cần nhãn mới

- **`YES` (Khả thi trực tiếp không cần nhãn mới):** **13 mẫu (20,6%)**
- **`PARTIAL` (Chỉ khả thi dưới dạng Proxy / Có điều kiện hạn chế):** **46 mẫu (73,0%)**
- **`NO` (Hoàn toàn không thể đánh giá với nhãn hiện tại):** **4 mẫu (6,3%)**

> **Nhận định thực tế:** Bằng chứng cho thấy **đại đa số các sự kiện nguy cơ an toàn công nghiệp trong InspecSafe-V1 (>79%) là các nguy cơ thiếu hụt trang thiết bị (Absence-based), trạng thái bất thường (State-based), hoặc quan hệ vi phạm (Relational)**. Do đó, việc kỳ vọng bộ dữ liệu có sẵn ground truth hoàn hảo cho Evidence Grounding tổng quát là **hoàn toàn phi thực tế**.

---

## 14. Các cấp độ đánh giá Grounding khả thi (Grounding Evaluation Levels)

Để SafeShift có thể triển khai nghiên cứu một cách khoa học mà không vi phạm tính trung thực học thuật, ba cấp độ đánh giá Grounding được phân tích:

### CẤP ĐỘ A: Object-Support Grounding (Bám bằng chứng ở mức đối tượng hiện hữu)
- **Định nghĩa:** Đánh giá khả năng mô hình phát hiện và khoanh vùng các vật thể nguy cơ hiện hữu cụ thể (`Cigarette`, `Mobile Phone`, `Open Flame`, `Liquid`, `Smoke`, `Water Bottle`, `Plastic Bag`).
- **Tính khả thi hiện tại:** **FEASIBLE_WITH_CONSTRAINTS (Khả thi với tập con giới hạn)**.
- **Ràng buộc:** Phải lọc ra một **Evaluation Subset** chuyên biệt từ 1.000 mẫu Anomaly (khoảng 200–250 mẫu chứa các vật thể này). Chỉ đo IoU / Pointing Game trên tập con này.

### CẤP ĐỘ B: Weak Proxy Grounding (Bám bằng chứng qua vùng đại diện yếu)
- **Định nghĩa:** Sử dụng đa giác cơ thể người (`Person`) làm vùng proxy để kiểm tra xem mô hình VLM khi phát hiện vi phạm không đội mũ, không đeo găng, không đeo khẩu trang hay người ngã có hướng sự chú ý (attention/bounding box) vào cơ thể người đó hay không.
- **Tính khả thi hiện tại:** **FEASIBLE_WITH_CONSTRAINTS (Khả thi nhưng phải ghi rõ là Proxy)**.
- **Ràng buộc:** Bắt buộc phải tuyên bố trong mọi bài báo/báo cáo rằng đây là **Weak Proxy Evaluation**, không phải Direct Grounding. Không được phạt mô hình nếu mô hình chỉ khoanh vùng đầu người (cho lỗi no-helmet) thay vì toàn thân `Person`.

### CẤP ĐỘ C: Full Hazard Rationale Grounding (Bám bằng chứng giải thích nguy cơ đầy đủ)
- **Định nghĩa:** Đánh giá mô hình khoanh vùng chính xác lý do an toàn cấp chuyên gia (ví dụ: khoanh vùng đúng khoảng trống trên đầu công nhân để chỉ ra "thiếu mũ bảo hộ", khoanh đúng cánh cửa tủ đang hé mở kèm góc mở).
- **Tính khả thi hiện tại:** **NOT_CURRENTLY_FEASIBLE (Hiện tại không khả thi)**.
- **Rào cản:** InspecSafe-V1 hoàn toàn không có chú thích này. Để thực hiện được cấp độ này, bắt buộc phải có **quy trình gán nhãn bổ sung (new manual annotation)** do SafeShift tự thực hiện ở W2/W3 cho một tập benchmark nhỏ được chuẩn hóa.

---

## 15. Khả năng nghiên cứu hiện tượng "Correct Answer, Wrong Reason"

SafeShift từng đặt mục tiêu nghiên cứu hiện tượng mô hình VLM: **Đoán đúng cấp độ an toàn nhưng dựa trên lý do sai** (*Correct Safety Prediction, but Wrong Rationale*).

**Đánh giá khả năng thực nghiệm trên InspecSafe-V1 hiện tại:**
1. **Thiếu Ground Truth cho "Lý do đúng":** Dataset hiện tại không có human rationale annotation hay attention maps của chuyên gia.
2. **Nguy cơ đánh giá chủ quan:** Nếu mô hình dự đoán đúng `Level01` cho một ảnh công nhân vừa hút thuốc vừa không đeo găng tay, nhưng mô hình chỉ output bounding box vào điếu thuốc mà bỏ qua bàn tay, ta **không thể kết luận một cách khách quan rằng mô hình "sai lý do"**, bởi vì điếu thuốc hoàn toàn đủ điều kiện cấu thành rủi ro Cấp 1!
3. **Giới hạn của tệp TXT:** Tệp văn bản `.txt` chỉ là câu mô tả quan sát chung của annotator, **không phải Ground Truth định vị lý do**. Văn bản không có tọa độ gắn với ảnh.
4. **Kết luận:** safeShift **CHƯA THỂ** nghiên cứu hiện tượng "Correct Answer, Wrong Reason" trên toàn bộ dataset một cách tự động và khách quan. Đề tài này chỉ có thể thực hiện được nếu:
   - Thu hẹp vào tập con đối chứng có đơn nguy cơ rõ ràng (Single-Hazard Subset), hoặc
   - Bổ sung bộ chú thích Rationale Ground Truth thủ công ở W2.

---

## 16. Bối cảnh Open-Vocabulary và Thách thức nhãn hiếm

Kiểm định phân bố Bước 6 đã ghi nhận:
- Có **231 nhãn đối tượng thô duy nhất**.
- **65 nhãn chỉ xuất hiện ở tập Train** (ví dụ: `Belt Fastener`, `Slag Car`, `Trolley Wire`).
- **24 nhãn chỉ xuất hiện ở tập Test** (ví dụ: `Chemical Protective Clothing`, `Oxygen Bottle`, `Sledgehammer`).
- **142 nhãn xuất hiện ở cả hai tập**.

**Ý nghĩa nghiên cứu:**
- InspecSafe-V1 **không phải là một official open-vocabulary benchmark** được thiết kế có chủ đích bởi tác giả.
- Tuy nhiên, sự xuất hiện của 24 nhãn đối tượng mới hoàn toàn ở tập Test tạo ra một **yếu tố gây nhiễu từ vựng mở tự nhiên (natural open-vocabulary challenge/confound)**: nếu một VLM dựa vào danh mục lớp cố định của tập train, mô hình sẽ thất bại khi gặp các thực thể mới trong tập test. SafeShift có thể tận dụng đặc điểm này như một bài kiểm tra khả năng nhận biết khái niệm mới của VLM zero-shot, nhưng phải ghi chú rõ đây là thuộc tính phát sinh từ dữ liệu thô, không phải benchmark chuẩn hóa.

---

## 17. Đối soát sai lệch giữa tài liệu chính thức và dữ liệu Local (Reconciliation)

### 17.1 Đối soát 2.239 Sites vs. 3.234 Point Folders
- **Tài liệu chính thức (*Scientific Data*):** Khai báo **2.239 valid inspection sites/waypoints**.
- **Dữ liệu cục bộ kiểm toán:** Ghi nhận chính xác **3.234 thư mục điểm logic (`point_id` từ `000001` đến `003234`)**, gồm 2.424 điểm ở train và 810 điểm ở test.
- **Giải thích khoa học khả dĩ:**  
  1. *Điểm dừng vật lý vs Thư mục logic:* Con số 2.239 phản ánh các tọa độ dừng vật lý cố định của robot tại nhà xưởng công nghiệp.
  2. *Lặp lại phiên tuần tra (Repeat Visits):* Khi một điểm vật lý được robot tuần tra quay lại nhiều lần ở các thời điểm khác nhau (ví dụ ca sáng, ca tối, hoặc khi phát sinh sự cố), tác giả có thể đã sinh ra các mã point ID logic mới (từ đó tạo ra 3.234 thư mục).
  3. *Tách rời Train/Test:* Tác giả phân chia 3.234 thư mục thành hai tập train/test hoàn toàn không trùng ID số (`000001`–`003234`).
- **Kết luận:** Do upstream **không cung cấp tệp ánh xạ (mapping table)** giữa 2.239 physical sites và 3.234 point folders, SafeShift giữ nguyên trạng thái **`UNRESOLVED`** về mặt ánh xạ kỹ thuật chi tiết, nhưng xác nhận cấu trúc 3.234 điểm là hoàn toàn nhất quán trên hệ thống tệp.

### 17.2 Đối soát 234 Categories vs. 231 Unique Raw Labels
- **Tài liệu chính thức (*Scientific Data* & GitHub):** Khai báo *"covering 234 key industrial inspection object categories"*.
- **Dữ liệu cục bộ kiểm toán:** Thu được chính xác **231 chuỗi nhãn gốc duy nhất (`unique raw label strings`)** xuất hiện trong 37.434 đa giác.
- **Giải thích khoa học khả dĩ:**  
  1. Ba danh mục lớp trong taxonomy lý thuyết của tác giả có thể là các lớp cực hiếm và không có bất kỳ mẫu nào xuất hiện trong 5.013 ảnh công bố công khai.
  2. Sự gộp/tách nhãn văn bản hoặc lỗi chính tả (typo) trong quá trình gán nhãn thủ công.
- **Kết luận:** SafeShift kiên định nguyên tắc **không tự ý chuẩn hóa (normalize) hay suy đoán để ép 231 thành 234**. Trạng thái danh tính 3 lớp bị thiếu được ghi nhận là **`UNRESOLVED`** và sẽ chờ tác giả phản hồi hoặc công bố taxonomy đầy đủ.

---

## 18. Phán quyết khả thi chính thức (Feasibility Verdicts)

Căn cứ trên toàn bộ bằng chứng thực nghiệm thu thập được trong Tuần 1, SafeShift đưa ra phán quyết chính thức cho từng hướng nghiên cứu:

| Hạng mục nghiên cứu | Phán quyết khả thi (Feasibility Verdict) | Bằng chứng ủng hộ cốt lõi (Supporting Evidence) | Rào cản lớn nhất (Major Blocker) | Quyết định bắt buộc cho W2 (What W2 Must Decide) |
|---|:---:|---|---|---|
| **A. Cross-Domain Analysis (Phân tích so sánh xuyên miền)** | **`FEASIBLE_WITH_CONSTRAINTS`** | Tồn tại 5 miền công nghiệp rõ rệt với dung lượng mẫu lớn (720 đến 1.280 mẫu mỗi miền). Có sự tương đồng cao với kịch bản công bố trên *Scientific Data*. | Platform confounding nghiêm trọng (ray treo vs xe bánh lăn); 36 ca domain mismatch; phân bố nhãn an toàn bị lệch theo miền. | Quyết định cách thức báo cáo kết quả per-domain có kèm điều kiện kiểm soát platform; xử lý 36 mẫu mismatch. |
| **B. Standard Domain Generalization (Khái quát hóa miền chuẩn)** | **`NOT_CURRENTLY_FEASIBLE`** *(trên official split)*<br>**`PARTIALLY_FEASIBLE`** *(nếu tạo split mới)* | Khái niệm 5 miền công nghiệp độc lập về mặt ngữ cảnh vận hành lý thuyết. | **Miền `metallurgy` có Test Anomaly = 0** (không thể làm target); Split chính thức bị rò rỉ 7 cặp exact và hàng trăm chuỗi video liên tục; platform bị confound. | W2 phải quyết định: hoặc chuyển sang giao thức **Zero-shot Robustness** trên mô hình frozen, hoặc phải thiết kế một **Group-aware Split mới** loại trừ rò rỉ. |
| **C. Evidence Grounding with Existing Annotations (Grounding với nhãn có sẵn)** | **`PARTIALLY_FEASIBLE`** | Có sẵn 37.434 đa giác phân vùng đối tượng với 231 nhãn; có tệp TXT mô tả nguy cơ; ảnh có độ phân giải cao (Full HD, 2K). | **Không có nhãn bằng chứng nguy cơ chuyên biệt**. Đa giác chỉ khoanh đối tượng hiện hữu; không có chú thích cho vi phạm thiếu PPE (absence) hay trạng thái cơ học. | W2 phải quyết định giới hạn phạm vi bài toán Grounding: chỉ coi đây là bài toán kiểm tra sự chú ý của VLM đối với các đối tượng liên quan (Object Support). |
| **D. Evidence Grounding with Proxy Subset (Grounding trên tập con Proxy)** | **`FEASIBLE_WITH_CONSTRAINTS`** | 20,6% mẫu có Direct Support (vật thể hiện hữu: điện thoại, thuốc lá, lửa, nước); 73,0% mẫu có thể dùng `Person` làm weak proxy hợp lý. | Vẫn là proxy gián tiếp; phạt oan mô hình nếu mô hình khoanh vùng chính xác vị trí cục bộ của lỗi (ví dụ đầu người khi không có mũ). | W2 phải chuẩn hóa **Evaluation Protocol cho Proxy Subset**: chấp nhận metric Pointing Game / Soft IoU trên vùng Person, hoặc lọc riêng tập Present Objects. |
| **E. Full Hazard-Specific Rationale Grounding (Grounding lý do an toàn đầy đủ)** | **`NOT_CURRENTLY_FEASIBLE`** | Nhu cầu học thuật và thực tiễn rất cao trong an toàn công nghiệp. | **Hoàn toàn thiếu Ground Truth về vùng lý do**. Tệp TXT không có phrase-region alignment; không thể xác định "Correct Answer, Wrong Reason" một cách tự động. | W2 phải quyết định: chấp nhận hoãn mục tiêu này cho Luận văn mở rộng, hoặc phải tiến hành gán nhãn bổ sung (Annotation Campaign) cho 100–200 mẫu mẫu mực. |
| **F. SafeShift Seminar Overall (Tổng thể đề tài Seminar)** | **`FEASIBLE_WITH_CONSTRAINTS`** | Dữ liệu InspecSafe-V1 là bộ tiêu chuẩn đa phương thức công nghiệp thực tế độc nhất vô nhị; tài liệu và quyền pháp lý CC-BY-4.0 hoàn toàn vững chắc. | Không thể giữ nguyên các tuyên bố nghiên cứu lý tưởng hóa ban đầu mà không có bằng chứng; cần điều chỉnh phạm vi và ngôn từ học thuật cho chuẩn xác. | W2 chuẩn hóa lại tiêu đề, mục tiêu và metric đánh giá theo hướng tiếp cận thực chứng vững chắc. |

---

## 19. Hàm ý và Đề xuất điều chỉnh cho Seminar (Scope & Wording Implications)

### Đề xuất tinh chỉnh ngôn từ học thuật (Candidate Scope Wording)

Ban đầu, đề tài SafeShift định hướng:
> *"Benchmarking Cross-Domain Generalization and Evidence Grounding in VLMs for Industrial Safety Assessment"*

Dựa trên các rào cản thực chứng phát hiện trong Tuần 1:
1. Thiếu điều kiện cho Domain Generalization chuẩn do rò rỉ split chính thức và khiếm khuyết dữ liệu bất thường của miền luyện kim.
2. Thiếu chú thích lý do an toàn đầy đủ cho Evidence Grounding tổng quát.

SafeShift khuyến nghị nhóm nghiên cứu cân nhắc điều chỉnh ngôn từ (wording) theo hướng bảo thủ, chặt chẽ và không thể bị phản biện:

- **Phương án Khuyến nghị 1 (Tập trung vào Robustness và Object Support):**  
  > *"Benchmarking Cross-Domain **Robustness** and **Evidence Support** in Vision-Language Models for Industrial Safety Assessment"*  
  *(Đánh giá độ bền vững xuyên miền và mức độ bám bằng chứng đối tượng của các mô hình VLM trong giám sát an toàn công nghiệp).*
- **Phương án Khuyến nghị 2 (Nếu thực hiện tinh chỉnh trên tập con miền):**  
  > *"Investigating Cross-Domain **Transferability** and **Weak-Proxy Grounding** of VLMs on Industrial Inspection Benchmarks"*  
  *(Khảo sát khả năng chuyển giao xuyên miền và bám bằng chứng đại diện yếu của VLM trên bộ dữ liệu kiểm tra công nghiệp).*

*(Lưu ý: Đây chỉ là đề xuất câu chữ để đưa ra thảo luận tại cuộc họp khởi động Tuần 2; SafeShift không tự ý sửa đổi tiêu đề dự án hoặc tài liệu `ROADMAP.md` ở bước này).*

---

## 20. Danh mục khuyến nghị bắt buộc cho Tuần 2 (W2 Action Items)

Trước khi bắt đầu bất kỳ thí nghiệm VLM nào, Tuần 2 (Research Protocol & Setup) bắt buộc phải đưa ra quyết định chính thức và ghi vào `DECISIONS.md` cho 5 vấn đề cốt lõi sau:

1. **Quyết định về Giao thức Cross-Domain (Protocol Decision):**  
   - Quyết định lựa chọn giữa: (a) Giao thức Zero-shot Pretrained VLM Robustness trên 5 miền (không huấn luyện lại), hay (b) Giao thức Leave-One-Domain-Out trên 4 miền khả thi (loại trừ `metallurgy` làm target).
2. **Quyết định về Xử lý Rò rỉ và Thiết kế Split (Leakage & Split Policy):**  
   - Quyết định giữ nguyên Official Split (kèm báo cáo hạn chế) hay xây dựng một **SafeShift Clean Split** độc lập nhằm loại bỏ 7 cặp exact và cách ly các chuỗi thời gian của 12 source families.
3. **Quyết định về Định nghĩa Grounding và Metric (Grounding Scope & Metrics):**  
   - Chốt ranh giới bài toán Grounding ở **Level A (Object Support)** và **Level B (Weak Proxy)**; ban hành công thức tính metric (Pointing Game, Soft IoU, Attention Map Overlap) phù hợp với nhãn đa giác hiện có.
4. **Quyết định về 36 mẫu Domain Mismatch:**  
   - Thống nhất quy tắc xử lý: loại bỏ khỏi tập đánh giá cross-domain, hay phân loại lại theo `text_domain`, hay giữ nguyên kèm cờ cảnh báo rủi ro nhạy cảm.
5. **Quyết định về Chiến dịch Gán nhãn Bổ sung (Annotation Campaign Decision):**  
   - Đánh giá khả năng và nguồn lực có cho phép thực hiện gán nhãn thủ công vùng lý do (Rationale Bounding Box) cho một tập chuẩn hóa nhỏ (100 mẫu) phục vụ nghiên cứu sâu "Correct Answer, Wrong Reason" hay không.

---

## 21. Giới hạn của đợt Audit (Limitations of Audit)

1. **Quy mô mẫu khảo sát chuyên sâu:** Phân tích định lượng về grounding được thực hiện trên 63 mẫu Anomaly có chọn lọc phân tầng (chiếm 6,3% tổng số mẫu bất thường). Mặc dù tập mẫu bao trùm 100% miền luyện kim, 100% mẫu Level03, toàn bộ 7 cặp exact và cả 12 họ nguồn, các tỷ lệ phần trăm cụ thể không nên bị ngoại suy tuyệt đối ra toàn bộ 1.000 mẫu mà cần được xem như chỉ dấu phân bố thực nghiệm.
2. **Thiếu ánh xạ Upstream:** Không thể giải quyết triệt để sự chênh lệch giữa 2.239 trạm kiểm tra và 3.234 thư mục điểm, cũng như danh tính của 3 lớp RGB bị thiếu do không có metadata bổ sung từ phía tác giả.
3. **Chưa có dữ liệu định lượng về Attention của VLM:** Mọi phân tích về khả năng grounding ở bước này đều dựa trên sự đối chiếu tĩnh giữa câu mô tả TXT và đa giác JSON; mức độ bám bằng chứng thực tế của từng mô hình VLM cụ thể sẽ được đo đạc bằng thực nghiệm suy luận tại Tuần 3.

---

*Báo cáo được lập và lưu trữ trong repository SafeShift dưới sự giám sát của hệ thống kiểm định tự động.*  
*Liên kết tài liệu gốc: [notes/research_feasibility_audit.md](notes/research_feasibility_audit.md)*  
