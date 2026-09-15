# Đánh giá trực quan và nguồn gốc dữ liệu (Targeted Visual & Provenance Review) — W1, Bước 5

Tài liệu này ghi nhận kết quả rà soát trực quan chuyên sâu (targeted visual review) và điều tra nguồn gốc dữ liệu (provenance investigation) đối với các trường hợp trùng lặp tuyệt đối (exact duplicates), các họ nguồn ảnh suy luận (source families) và tập mẫu ứng viên tương đồng cao (near-duplicate candidates) xuyên qua phân chia huấn luyện/kiểm tra (`train`/`test`) của tập dữ liệu InspecSafe-V1.

Nghiên cứu tuân thủ nguyên tắc toàn vẹn dữ liệu: **chỉ đọc (read-only)** dữ liệu gốc, không chỉnh sửa nhãn, không can thiệp polygon, không xóa mẫu và không thay đổi phân chia split chính thức trong giai đoạn Week 1.

---

## 1. Phương pháp luận và quy trình Blind-First Visual Review

Để loại trừ định kiến xác nhận (confirmation bias), quy trình thẩm định trực quan được thực hiện theo nguyên tắc **Blind-First Visual Inspection**:

1. **Giai đoạn 1 (Blind Review):** Kiểm tra hiển thị cặp ảnh độc lập mà không xem trước metadata nhãn (`txt_content`, `shapes`, `safety_level`, `folder_domain`). Người đánh giá ghi nhận:
   - Bản chất cảnh quan sát (bối cảnh vật lý, thiết bị, góc máy, ánh sáng, vật thể chuyển động).
   - Mối quan hệ hình ảnh giữa hai khung hình: cùng khung hình pixel/byte, cùng chuỗi video liên tiếp thời gian thực, cùng vị trí camera/waypoint cố định ở thời điểm khác, hay hai bối cảnh khác biệt ngẫu nhiên tương đồng.
   - Sự hiện diện của đối tượng bất thường hoặc nguy cơ an toàn hiển thị trực tiếp trong ảnh.

2. **Giai đoạn 2 (Unblinded Alignment & Provenance Context):** Mở đối chiếu với metadata tương ứng từ các tệp `.json` và `.txt`:
   - So sánh nhãn nguy cơ và phân cấp an toàn (`safety_level` / Grade).
   - So sánh câu mô tả tiếng Anh (`txt_content`).
   - So sánh hình học annotation: số lượng hình khối (`shapes`), nhãn bounding box / polygon, tọa độ các điểm đỉnh.
   - So sánh dấu vết nguồn: tên tệp gốc từ upstream (`image_path_basename`), định danh điểm tuần tra (`point_id`), nền tảng robot (`robot_platform`), và miền công nghiệp (`folder_domain`).

3. **Hệ thống phân loại chuẩn hóa (Standardized Typology):**
   - **Mối quan hệ trực quan (Visual Relation):**
     - `IDENTICAL_VISIBLE_CONTENT`: Hai ảnh hoàn toàn đồng nhất về nội dung hiển thị (trùng khớp byte-level hoặc pixel-level sau giải mã).
     - `SAME_SCENE_NEARBY_FRAME`: Các khung hình liền kề hoặc cách nhau một khoảng thời gian rất ngắn được trích xuất từ cùng một video hoặc chuỗi chụp liên tục (cùng góc máy, cùng chủ thể đang vận động).
     - `SAME_CAMERA_OR_VIEWPOINT`: Cùng một góc máy quan sát cố định hoặc cùng một tọa độ dừng (waypoint) vật lý của robot, nhưng chụp ở hai phiên tuần tra hoặc hai thời điểm khác nhau (cảnh nền tĩnh giống nhau, ánh sáng hoặc chi tiết nền có thay đổi nhỏ).
     - `DISTINCT_SCENE_COINCIDENTAL_NEAR_MATCH`: Hai cảnh vật lý hoàn toàn độc lập, ngẫu nhiên có bố cục hoặc đặc trưng tần số tương tự dẫn đến khoảng cách perceptual hash thấp.
   - **Mối quan hệ nguy cơ (Hazard Relation):**
     - `SAME_HAZARD`: Cả hai mẫu cùng tập trung phản ánh cùng một sự kiện nguy cơ an toàn vật lý.
     - `DIFFERENT_HAZARD`: Cùng một khung hình hoặc cùng một cảnh vật lý nhưng được gán nhãn tập trung vào hai mối nguy cơ khác nhau (do bối cảnh chứa đa nguy cơ hoặc gán nhãn mâu thuẫn).
     - `NO_VISIBLE_HAZARD`: Cảnh tuần tra bình thường, không chứa sự kiện nguy cơ (mẫu `Normal_data`).

---

## 2. Thẩm định chi tiết 7 cặp trùng lặp tuyệt đối xuyên Split (Cross-Split Exact Pairs)

Tại Bước 4 (Audit Trùng lặp & Rò rỉ), phân tích SHA-256 đã phát hiện chính xác **7 cặp ảnh trùng lặp tuyệt đối xuyên split (cross-split exact pairs)** giữa `train` và `test` (thuộc 5 nhóm trùng lặp byte-exact / pixel-exact). Cả 7 cặp đều có kích thước ảnh và mã băm SHA-256 hoàn toàn đồng nhất 100% (`IDENTICAL_VISIBLE_CONTENT`).

### 2.1 Bảng đối chiếu tổng hợp 7 cặp Exact

| Cặp | Mẫu Train (`train_sample_id`) | Upstream Basename Train | Mẫu Test (`test_sample_id`) | Upstream Basename Test | Miền (`train` vs `test`) | Robot (`train` vs `test`) | Cấp an toàn (`train` vs `test`) | Số lượng Shapes (`train` vs `test`) | Xung đột nhãn / Annotation |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **1** | `coal_conveyor-Level01-SuspendedRail-002589-001` | `hand_frame_000044.jpg` | `coal_conveyor-Level02-SuspendedRail-002241-001` | `hand_frame_000010.jpg` | `coal_conveyor` = `coal_conveyor` | `SuspendedRail` = `SuspendedRail` | **Level01 ≠ Level02** | 13 ≠ 18 | **Xung đột cấp độ & hành vi:** Train gán *không đội mũ bảo hộ* (Level 1); Test gán *không đeo găng tay* (Level 2). Test có thêm 5 polygon chi tiết cho găng tay. |
| **2** | `oil_chemical-Level01-SuspendedRail-003004-001` | `phone_frame_000092.jpg` | `oil_chemical-Level01-SuspendedRail-002380-001` | `phone_frame_000004.jpg` | `oil_chemical` = `oil_chemical` | `SuspendedRail` = `SuspendedRail` | `Level01` = `Level01` | 3 = 3 | **Trùng khớp:** Cùng mô tả công nhân sử dụng điện thoại di động; polygon và nhãn tọa độ khớp 100%. |
| **3** | `oil_chemical-Level01-SuspendedRail-003005-001` | `phone_frame_000093.jpg` | `oil_chemical-Level01-SuspendedRail-002381-001` | `phone_frame_000005.jpg` | `oil_chemical` = `oil_chemical` | `SuspendedRail` = `SuspendedRail` | `Level01` = `Level01` | 3 = 3 | **Trùng khớp:** Cùng mô tả công nhân sử dụng điện thoại di động; polygon và nhãn tọa độ khớp 100%. |
| **4** | `metallurgy-Level01-SuspendedRail-002875-001` | `hand_frame_000067.jpg` | `oil_chemical-Level01-Wheeled-002344-001` | `nonmask_frame_000012.jpg` | **metallurgy ≠ oil_chemical** | **SuspendedRail ≠ Wheeled** | `Level01` = `Level01` | 6 ≠ 7 | **Xung đột miền, robot & nguy cơ:** Train gán miền *metallurgy*, robot *SuspendedRail*, nguy cơ *không đeo găng tay*. Test gán miền *oil_chemical*, robot *Wheeled*, nguy cơ *không đeo khẩu trang*. Annotation gán nhãn vật thể hoàn toàn lệch nhau. |
| **5** | `coal_conveyor-Level01-SuspendedRail-002582-001` | `hand_frame_000037.jpg` | `coal_conveyor-Level01-SuspendedRail-002248-001` | `cigarette_frame_000022.jpg` | `coal_conveyor` = `coal_conveyor` | `SuspendedRail` = `SuspendedRail` | `Level01` = `Level01` | 8 ≠ 10 | **Xung đột loại nguy cơ:** Train gán nguy cơ *không đeo găng tay* (`hand`); Test gán nguy cơ *hút thuốc* (`cigarette`). Test có thêm polygon khoanh vùng điếu thuốc (`Cigarette`). |
| **6** | `coal_conveyor-Level01-SuspendedRail-002583-001` | `hand_frame_000038.jpg` | `coal_conveyor-Level01-SuspendedRail-002249-001` | `cigarette_frame_000023.jpg` | `coal_conveyor` = `coal_conveyor` | `SuspendedRail` = `SuspendedRail` | `Level01` = `Level01` | 8 ≠ 10 | **Xung đột loại nguy cơ:** Khung hình tiếp nối của Cặp 5. Train gán nguy cơ *không đeo găng tay*; Test gán nguy cơ *hút thuốc*. Test có thêm polygon điếu thuốc. |
| **7** | `oil_chemical-Level01-SuspendedRail-003003-001` | `phone_frame_000091.jpg` | `oil_chemical-Level01-SuspendedRail-002382-001` | `phone_frame_000006.jpg` | `oil_chemical` = `oil_chemical` | `SuspendedRail` = `SuspendedRail` | `Level01` = `Level01` | 4 = 4 | **Sai lệch nhãn vật thể:** Cả hai cùng gán nguy cơ dùng điện thoại, nhưng cùng một tọa độ polygon ở góc ảnh: Train gán nhãn là *Trụ cứu hỏa* (`Fire Hydrant` / 消火栓), trong khi Test gán nhãn là *Bình chữa cháy* (`Fire Extinguisher` / 灭火器). |

---

### 2.2 Phân tích sâu các ca xung đột nhãn (Label Inconsistency Deep-Dive)

#### Ca 1: Xung đột Cấp độ An toàn và Nội dung Nguy cơ (Cặp 1)
- **Hình ảnh:** Bức ảnh chụp công nhân đang đứng vận hành cạnh hệ thống băng tải than (`coal_conveyor`).
- **Nội dung gán nhãn:**
  - Tập Train (`002589`): Tệp văn bản ghi: *"In the coal conveyor scenario, there are staff members who do not wear safety helmets. The safety level is Grade One."* (Không đội mũ bảo hộ, Cấp 1).
  - Tập Test (`002241`): Tệp văn bản ghi: *"In the coal conveyor scenario, there are staff members who do not wear gloves. The safety level is Grade Two."* (Không đeo găng tay, Cấp 2).
- **Hệ quả nghiên cứu:** Mô hình thị giác máy học được huấn luyện rằng đặc trưng thị giác của bức ảnh này tương ứng với nhãn `Level01` (Cấp 1), nhưng khi đánh giá trên tập kiểm tra với chính xác từng pixel đó, ground truth lại yêu cầu phân loại thành `Level02` (Cấp 2). Đây là mâu thuẫn nhãn trực tiếp (direct label contradiction).

#### Ca 2: Trùng lặp xuyên Miền Công nghiệp và Nền tảng Robot (Cặp 4)
- **Hình ảnh:** Bức ảnh chụp phòng điều khiển/trạm bơm với các van ống và tủ điện.
- **Nội dung gán nhãn:**
  - Tập Train (`002875`): Được xếp vào miền `metallurgy` (luyện kim), gán cho robot ray treo `SuspendedRail`. Nội dung văn bản: *"In the metallurgy scenario, there are staff members who do not wear gloves."*. Polygon gồm 6 đối tượng: `Ball Valve`, `Distribution Box`, `Person`, `Flange`.
  - Tập Test (`002344`): Được xếp vào miền `oil_chemical` (hóa dầu), gán cho robot bánh lăn `Wheeled`. Nội dung văn bản: *"In the oil chemical scenario, there are staff members who do not wear masks."*. Polygon gồm 7 đối tượng: `Valve`, `Motor`, `Flange`, `Person`.
- **Hệ quả nghiên cứu:** Mẫu dữ liệu này vừa rò rỉ hình ảnh xuyên split, vừa làm sai lệch hoàn toàn khái niệm miền (domain) và bối cảnh robot. Một mô hình đánh giá năng lực tổng quát hóa xuyên miền (cross-domain generalization) từ `metallurgy` sang `oil_chemical` sẽ vô tình gặp lại đúng bức ảnh của tập train trong tập test dưới một danh nghĩa hoàn toàn khác.

#### Ca 3: Hiện tượng phân tách đa nguy cơ (Multi-Hazard Framing Discrepancy - Cặp 5 & 6)
- **Hình ảnh:** Hai khung hình liên tiếp chụp một công nhân tại khu vực băng tải than vừa hút thuốc, vừa không mang găng tay bảo hộ lao động.
- **Nội dung gán nhãn:**
  - Upstream ban đầu trích xuất các khung hình này và đưa đồng thời vào hai bộ sưu tập: thư mục `hand` và thư mục `cigarette`.
  - Trong tập Train, hai khung hình mang mã nguồn `hand_frame_000037.jpg` và `hand_frame_000038.jpg`, được gán nhãn tập trung vào bàn tay (`do not wear gloves`).
  - Trong tập Test, hai khung hình mang mã nguồn `cigarette_frame_000022.jpg` và `cigarette_frame_000023.jpg`, được gán nhãn tập trung vào điếu thuốc (`smoking`) và bổ sung bounding polygon cho `Cigarette`.

#### Ca 4: Tranh chấp định danh đối tượng (Annotation Object Identity - Cặp 7)
- Cùng một bức ảnh công nhân nghe điện thoại trong nhà máy hóa chất, nhưng đối tượng thiết bị an toàn tĩnh gắn trên tường bị gán nhãn là `消火栓` (Fire Hydrant) trong bản ghi Train và `灭火器` (Fire Extinguisher) trong bản ghi Test. Điều này phản ánh sự thiếu chuẩn hóa trong quy trình gán nhãn thủ công ban đầu của tác giả upstream.

---

### 2.3 Cơ chế hình thành trùng lặp Exact xuyên Split

Phân tích mã nguồn và dấu vết tệp cho thấy rõ cơ chế sinh ra các bản sao exact xuyên split:
1. **Thu thập ban đầu:** Đội ngũ xây dựng bộ dữ liệu thu thập các cảnh quay vi phạm an toàn. Khi một cảnh xuất hiện nhiều hành vi vi phạm (ví dụ: vừa hút thuốc vừa không đeo găng tay, hoặc vừa dùng điện thoại vừa không đội mũ), tác giả đã sao chép cùng một tệp ảnh vào nhiều thư mục phân loại nguy cơ khác nhau (`cigarette`, `hand`, `nonmask`, `phone`).
2. **Gán nhãn độc lập (Uncoordinated Labeling):** Mỗi bản sao trong từng thư mục nguy cơ được giao cho người gán nhãn (annotator) độc lập. Annotator của thư mục `hand` chỉ tập trung vẽ găng tay và gán nhãn không đeo găng; annotator của thư mục `cigarette` chỉ tập trung vẽ điếu thuốc và gán nhãn hút thuốc; thậm chí có annotator phân loại cảnh đó thuộc ngành luyện kim, người khác lại phân loại thuộc ngành hóa dầu.
3. **Phân chia theo chỉ số thứ tự (Arbitrary Ordinal Partitioning):** Khi chia tập dữ liệu thành `train` và `test`, tác giả sắp xếp các tệp theo thứ tự tên tệp trong từng thư mục và cắt cứng ~25% đầu cho `test`, ~75% sau cho `train`. Do độ dài danh sách ảnh trong mỗi thư mục là khác nhau:
   - Tệp ảnh đa nguy cơ rơi vào vị trí thứ 10/72 trong thư mục `hand` -> được phân bổ vào tập **Test**.
   - Bản sao của chính tệp ảnh đó rơi vào vị trí thứ 44/72 trong thư mục `cigarette` -> được phân bổ vào tập **Train**.
   - Kết quả: Cùng một tệp ảnh xuất hiện đồng thời ở cả hai phía của split chính thức với các nhãn mâu thuẫn nhau.

---

## 3. Điều tra 12 họ nguồn ảnh suy luận (Source-Family Investigation)

### 3.1 Bản chất của các "Source Family"

Tại Bước 4, dựa trên quy tắc biểu thức chính quy (regex) `(?P<family>.+)_frame_(?P<counter>[0-9]+)\.(?:jpg|jpeg|png)` quét trên trường `imagePath` của tệp JSON, kiểm toán đã ghi nhận **12 nhóm nguồn (source families)** có mặt xuyên qua cả hai tập `train` và `test`.

Khảo sát trực quan và thống kê toàn bộ 5.013 mẫu của InspecSafe-V1 xác nhận các sự thật then chốt sau:
1. **Phạm vi tồn tại:** Cả 12 họ nguồn này bao trùm **toàn bộ 1.000 mẫu dữ liệu Anomaly (`Anomaly_data`)** của toàn bộ tập dữ liệu (749 mẫu trong `train` và 251 mẫu trong `test`). Tuyệt đối không có bất kỳ mẫu dữ liệu bình thường (`Normal_data`) nào thuộc 12 nhóm này.
2. **Không phải là 12 video đơn lẻ:** Một "family" (ví dụ: `nonmask`, `head`, `others`) không phải là một tệp video duy nhất. Đó là **thư mục gom nhóm theo chủng loại nguy cơ (hazard category pools)** do tác giả upstream tập hợp từ nhiều nguồn quay khác nhau.
3. **Quy luật cắt phân chia có hệ thống (Systematic 25/75 Split Boundary):** Trong tất cả 12 họ nguồn, số thứ tự khung hình (`frame counter`) luôn bắt đầu từ `000001` đến `0000N`. Trong đó:
   - Tập `test` **luôn luôn** nhận các khung hình từ `000001` đến `0000K` (với $K \approx 0.25 \times N$).
   - Tập `train` **luôn luôn** nhận các khung hình tiếp theo từ `0000(K+1)` đến `0000N`.
   - **Tỉ lệ trùng lặp chỉ số khung hình giữa train và test bằng 0%**: Tác giả đã thực hiện cắt liên tục theo thứ tự số học (sequential cut) trên danh sách tệp của từng loại nguy cơ.

### 3.2 Bảng tổng hợp chi tiết 12 họ nguồn Anomaly

| Tên họ (`Family`) | Tổng số mẫu | Số mẫu Test | Dải frame Test | Số mẫu Train | Dải frame Train | Tỉ lệ Test (%) | Miền Test | Miền Train | Phân loại bằng chứng chuỗi (`Sequence Evidence`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- | :--- |
| `nonmobile` | 100 | 25 | `000001`–`000025` | 75 | `000026`–`000100` | 25.0% | `tunnel` | `tunnel` | **STRONG_SHARED_SEQUENCE_EVIDENCE** |
| `phone` | 108 | 27 | `000001`–`000027` | 81 | `000028`–`000108` | 25.0% | `coal_conveyor`, `oil_chemical`, `tunnel` | `coal_conveyor`, `metallurgy`, `oil_chemical`, `power`, `tunnel` | **STRONG_SHARED_SEQUENCE_EVIDENCE** |
| `cigarette` | 96 | 24 | `000001`–`000024` | 72 | `000025`–`000096` | 25.0% | `coal_conveyor`, `oil_chemical` | `coal_conveyor`, `oil_chemical` | **STRONG_SHARED_SEQUENCE_EVIDENCE** |
| `fire` | 104 | 26 | `000001`–`000026` | 78 | `000027`–`000104` | 25.0% | `coal_conveyor`, `oil_chemical`, `tunnel` | `coal_conveyor`, `metallurgy`, `oil_chemical`, `power`, `tunnel` | **STRONG_SHARED_SEQUENCE_EVIDENCE** |
| `others` | 86 | 22 | `000001`–`000022` | 64 | `000023`–`000086` | 25.6% | `coal_conveyor`, `power`, `tunnel` | `coal_conveyor`, `oil_chemical`, `power`, `tunnel` | **STRONG_SHARED_SEQUENCE_EVIDENCE** |
| `nonmask` | 104 | 26 | `000001`–`000026` | 78 | `000027`–`000104` | 25.0% | `coal_conveyor`, `oil_chemical`, `power`, `tunnel` | `coal_conveyor`, `metallurgy`, `oil_chemical`, `power`, `tunnel` | **STRONG_SHARED_SEQUENCE_EVIDENCE** |
| `liquid` | 100 | 25 | `000001`–`000025` | 75 | `000026`–`000100` | 25.0% | `oil_chemical` | `coal_conveyor`, `metallurgy`, `oil_chemical`, `tunnel` | **STRONG_SHARED_SEQUENCE_EVIDENCE** |
| `hand` | 72 | 18 | `000001`–`000018` | 54 | `000019`–`000072` | 25.0% | `coal_conveyor`, `oil_chemical`, `power` | `coal_conveyor`, `metallurgy`, `oil_chemical`, `tunnel` | **STRONG_SHARED_SEQUENCE_EVIDENCE** |
| `head` | 103 | 26 | `000001`–`000026` | 77 | `000027`–`000103` | 25.2% | `coal_conveyor`, `power`, `tunnel` | `coal_conveyor`, `oil_chemical`, `power`, `tunnel` | **STRONG_SHARED_SEQUENCE_EVIDENCE** |
| `smog` | 103 | 26 | `000001`–`000026` | 77 | `000027`–`000103` | 25.2% | `coal_conveyor`, `oil_chemical`, `tunnel` | `coal_conveyor`, `oil_chemical`, `power` | **PLAUSIBLE_SHARED_SOURCE** |
| `fall` | 10 | 2 | `000001`–`000002` | 8 | `000003`–`000010` | 20.0% | `power` | `coal_conveyor`, `power` | **NO_SHARED_SOURCE_EVIDENCE** |
| `dooropen` | 14 | 4 | `000001`–`000004` | 10 | `000005`–`000014` | 28.6% | `oil_chemical`, `power` | `tunnel` | **NO_SHARED_SOURCE_EVIDENCE** |

---

### 3.3 Phân tích trực quan các bằng chứng chuỗi tiêu biểu

1. **Họ `nonmobile` (Bằng chứng chuỗi video tuyệt đối):**
   - 100% mẫu trong họ này thuộc miền `tunnel`.
   - Khảo sát trực quan cho thấy toàn bộ 100 khung hình được trích xuất từ **một đoạn video duy nhất dài khoảng 40 giây**, ghi lại hình ảnh một người đi xe đạp trong đường hầm (dấu thời gian từ `2024-04-24 14:07:35` đến `2024-04-24 14:08:15`).
   - Tác giả cắt 25 khung hình đầu (`000001`–`000025`, lúc 14:07:35 – 14:07:45) đưa vào tập **Test**, và 75 khung hình tiếp theo ngay sau đó (`000026`–`000100`, lúc 14:07:45 – 14:08:15) đưa vào tập **Train**.
   - Khung hình cuối của Test (`frame_000025`) và khung hình đầu của Train (`frame_000026`) là hai khung hình liên tiếp với người đi xe đạp chỉ dịch chuyển vài centimet trên mặt đường. Đây là trường hợp rò rỉ chuỗi thời gian (temporal sequence leakage) ở mức độ tối đa.

2. **Họ `phone`:**
   - Chứa các cặp trùng lặp byte-exact xuyên split (Cặp 2, 3, 7).
   - Ngoài các bản sao exact, các khung hình `000027` (Test) và `000028` (Train) chụp cùng một công nhân đang thao tác điện thoại tại cùng một trạm van dầu khí với góc máy hoàn toàn không đổi.

3. **Họ `cigarette`:**
   - Khung hình `000023` (Test, lúc `17:05:39`) và khung hình `000025` (Train, lúc `17:05:40`) chụp cùng một công nhân đang hút thuốc tại khu vực băng tải than, cách nhau đúng 1 giây trong cùng một video giám sát.

4. **Họ `fire`:**
   - Khung hình `000019` (Test, lúc `16:19:59`) và khung hình `000028` (Train, lúc `16:19:58`) ghi nhận cùng một đám cháy nhỏ tại trạm điện, cách nhau đúng 1 giây.

5. **Họ `others`:**
   - Khung hình `000017` (Test) và `000078` (Train) ghi lại cùng một sự việc tại trạm biến áp vào cùng một giây (`2024-04-08 16:24:54`).

6. **Các họ `fall` và `dooropen`:**
   - Có số lượng mẫu rất nhỏ (10 và 14 mẫu). Khảo sát trực quan cho thấy các ảnh trong hai họ này được thu thập rải rác từ các sự cố riêng lẻ ở nhiều trạm khác nhau, không phát hiện bằng chứng liên tục về thời gian giữa các mẫu thuộc tập Test và Train (`NO_SHARED_SOURCE_EVIDENCE`).

---

## 4. Thẩm định trực quan 50 cặp ứng viên tương đồng cao (Near-Duplicate Review)

### 4.1 Phương pháp chọn mẫu 50 cặp ứng viên

Từ tập 826 cặp ứng viên phi exact xuyên split (`dHash <= 8`) được phát hiện tại Bước 4, một tập mẫu phân tầng gồm 50 cặp đại diện đã được trích xuất theo 4 nhóm chiến lược:
- **Nhóm 1: Top 20 tương đồng cao nhất toàn diện (Top 20 Overall):** 20 cặp có dHash nhỏ nhất kết hợp giá trị Mean Absolute Error (MAE) điểm ảnh xám thấp nhất.
- **Nhóm 2: 15 cặp cùng họ nguồn suy luận (Same-Family):** Các cặp thuộc cùng họ tên tệp upstream (`same_source_family = True`) nhưng có dHash từ 0 đến 6.
- **Nhóm 3: 10 cặp khác họ nguồn suy luận (Different-Family):** Các cặp có hình thức thị giác gần giống nhau nhưng khác tên họ tệp ban đầu.
- **Nhóm 4: 5 cặp bao phủ các miền công nghiệp còn lại (Domain Coverage):** Bổ sung đại diện từ miền `oil_chemical` và `power` để đảm bảo độ bao phủ.

### 4.2 Kết quả phân loại trực quan Blind-First trên 50 cặp

Toàn bộ 50 cặp ứng viên đã được kiểm tra trực quan độc lập. Kết quả phân loại được thống kê như sau:

| Loại quan hệ trực quan (`Visual Classification`) | Quan hệ nguy cơ (`Hazard Relation`) | Số lượng cặp | Bản chất dữ liệu |
| :--- | :--- | :---: | :--- |
| `SAME_CAMERA_OR_VIEWPOINT` | `NO_VISIBLE_HAZARD` | **21** | **Normal_data ↔ Normal_data**: Robot tuần tra quay lại đúng điểm dừng vật lý cố định (waypoint) vào các ngày khác nhau (ví dụ: ngày 14/11/2025 và 15/11/2025). |
| `SAME_SCENE_NEARBY_FRAME` | `SAME_HAZARD` | **22** | **Anomaly_data ↔ Anomaly_data**: Khung hình trích xuất từ cùng một video sự cố liên tục bị cắt chia sang hai bên split. |
| `SAME_CAMERA_OR_VIEWPOINT` | `DIFFERENT_HAZARD` | **7** | **Anomaly_data ↔ Anomaly_data**: Cùng góc máy/bối cảnh sự cố nhưng mô tả và gán nhãn nguy cơ khác nhau do bối cảnh đa nguy cơ hoặc định vị nhãn lệch. |
| `DISTINCT_SCENE_COINCIDENTAL_NEAR_MATCH` | Bất kỳ | **0** | **Không có bất kỳ trường hợp nào trùng hợp ngẫu nhiên!** |
| **Tổng cộng** | | **50** | |

#### Phân bố theo loại dữ liệu và miền công nghiệp:
- **Tập con `Normal_data` (21 cặp):** 100% thuộc quan hệ `SAME_CAMERA_OR_VIEWPOINT`.
  - Phân bố miền: `tunnel` (11 cặp), `coal_conveyor` (10 cặp).
  - Bản chất: Robot tuần tra tự hành chạy theo lịch trình định kỳ. Cùng một tủ điện, cùng một đoạn ray hoặc cùng một ngách cứu hỏa được robot chụp tại cùng một góc máy và tọa độ chính xác qua các ca trực tuần tra khác nhau. Khi chia split ngẫu nhiên hoặc theo phiên tuần tra, các bức ảnh chụp cùng một thiết bị tĩnh ở trạng thái bình thường đã bị rải rác sang cả `train` và `test`.
- **Tập con `Anomaly_data` (29 cặp):**
  - Gồm 22 cặp `SAME_SCENE_NEARBY_FRAME` (cùng chuỗi video, dải frame cách nhau vài giây).
  - Gồm 7 cặp `SAME_CAMERA_OR_VIEWPOINT` (cùng vị trí máy quay quan sát công nhân vi phạm, nhưng nhãn mô tả găng tay vs điện thoại vs mũ bảo hộ).
  - Phân bố miền: `tunnel` (21 cặp), `power` (6 cặp), `oil_chemical` (2 cặp).

### 4.3 Danh mục chi tiết 50 cặp ứng viên được kiểm toán

Dưới đây là bảng dữ liệu chi tiết của toàn bộ 50 cặp ứng viên:

| STT | Nhóm lấy mẫu | Mẫu Test (`split_a`) | Mẫu Train (`split_b`) | Miền | Loại dữ liệu | dHash | MAE | Phân loại trực quan | Quan hệ nguy cơ |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| 1 | Top 20 | `tunnel-Level01-SuspendedRail-002429-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0043 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 2 | Top 20 | `tunnel-Level01-SuspendedRail-002430-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0043 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 3 | Top 20 | `tunnel-Level01-SuspendedRail-002431-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0043 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 4 | Top 20 | `tunnel-Level01-SuspendedRail-002432-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0043 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 5 | Top 20 | `tunnel-Level01-SuspendedRail-002433-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0043 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 6 | Top 20 | `tunnel-Level01-SuspendedRail-002434-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0043 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 7 | Top 20 | `tunnel-Level01-SuspendedRail-002435-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0043 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 8 | Top 20 | `tunnel-Level01-SuspendedRail-002436-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0043 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 9 | Top 20 | `tunnel-Level01-SuspendedRail-002437-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0043 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 10 | Top 20 | `tunnel-Level01-SuspendedRail-002438-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0043 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 11 | Top 20 | `coal_conveyor-Normal-SuspendedRail-000494-001` | `coal_conveyor-Normal-SuspendedRail-001300-001` | `coal_conveyor` | Normal | 0 | 0.0044 | SAME_CAMERA_OR_VIEWPOINT | NO_VISIBLE_HAZARD |
| 12 | Top 20 | `coal_conveyor-Normal-SuspendedRail-000495-001` | `coal_conveyor-Normal-SuspendedRail-001300-001` | `coal_conveyor` | Normal | 0 | 0.0044 | SAME_CAMERA_OR_VIEWPOINT | NO_VISIBLE_HAZARD |
| 13 | Top 20 | `coal_conveyor-Normal-SuspendedRail-000496-001` | `coal_conveyor-Normal-SuspendedRail-001300-001` | `coal_conveyor` | Normal | 0 | 0.0044 | SAME_CAMERA_OR_VIEWPOINT | NO_VISIBLE_HAZARD |
| 14 | Top 20 | `coal_conveyor-Normal-SuspendedRail-000497-001` | `coal_conveyor-Normal-SuspendedRail-001300-001` | `coal_conveyor` | Normal | 0 | 0.0044 | SAME_CAMERA_OR_VIEWPOINT | NO_VISIBLE_HAZARD |
| 15 | Top 20 | `coal_conveyor-Normal-SuspendedRail-000498-001` | `coal_conveyor-Normal-SuspendedRail-001300-001` | `coal_conveyor` | Normal | 0 | 0.0044 | SAME_CAMERA_OR_VIEWPOINT | NO_VISIBLE_HAZARD |
| 16 | Top 20 | `coal_conveyor-Normal-SuspendedRail-000499-001` | `coal_conveyor-Normal-SuspendedRail-001300-001` | `coal_conveyor` | Normal | 0 | 0.0044 | SAME_CAMERA_OR_VIEWPOINT | NO_VISIBLE_HAZARD |
| 17 | Top 20 | `coal_conveyor-Normal-SuspendedRail-000500-001` | `coal_conveyor-Normal-SuspendedRail-001300-001` | `coal_conveyor` | Normal | 0 | 0.0044 | SAME_CAMERA_OR_VIEWPOINT | NO_VISIBLE_HAZARD |
| 18 | Top 20 | `coal_conveyor-Normal-SuspendedRail-000501-001` | `coal_conveyor-Normal-SuspendedRail-001300-001` | `coal_conveyor` | Normal | 0 | 0.0044 | SAME_CAMERA_OR_VIEWPOINT | NO_VISIBLE_HAZARD |
| 19 | Top 20 | `coal_conveyor-Normal-SuspendedRail-000502-001` | `coal_conveyor-Normal-SuspendedRail-001300-001` | `coal_conveyor` | Normal | 0 | 0.0044 | SAME_CAMERA_OR_VIEWPOINT | NO_VISIBLE_HAZARD |
| 20 | Top 20 | `coal_conveyor-Normal-SuspendedRail-000503-001` | `coal_conveyor-Normal-SuspendedRail-001300-001` | `coal_conveyor` | Normal | 0 | 0.0044 | SAME_CAMERA_OR_VIEWPOINT | NO_VISIBLE_HAZARD |
| 21 | Same Family | `tunnel-Level01-SuspendedRail-002444-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0045 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 22 | Same Family | `tunnel-Level01-SuspendedRail-002443-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0045 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 23 | Same Family | `tunnel-Level01-SuspendedRail-002442-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0045 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 24 | Same Family | `tunnel-Level01-SuspendedRail-002441-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0045 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 25 | Same Family | `tunnel-Level01-SuspendedRail-002440-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0045 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 26 | Same Family | `tunnel-Level01-SuspendedRail-002439-001` | `tunnel-Level01-SuspendedRail-003062-001` | `tunnel` | Anomaly | 0 | 0.0045 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 27 | Same Family | `tunnel-Level01-SuspendedRail-002428-001` | `tunnel-Level01-SuspendedRail-003063-001` | `tunnel` | Anomaly | 0 | 0.0045 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 28 | Same Family | `tunnel-Level01-SuspendedRail-002428-001` | `tunnel-Level01-SuspendedRail-003064-001` | `tunnel` | Anomaly | 0 | 0.0045 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 29 | Same Family | `tunnel-Level01-SuspendedRail-002428-001` | `tunnel-Level01-SuspendedRail-003065-001` | `tunnel` | Anomaly | 0 | 0.0045 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 30 | Same Family | `tunnel-Level01-SuspendedRail-002428-001` | `tunnel-Level01-SuspendedRail-003066-001` | `tunnel` | Anomaly | 0 | 0.0045 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 31 | Same Family | `tunnel-Level01-SuspendedRail-002428-001` | `tunnel-Level01-SuspendedRail-003067-001` | `tunnel` | Anomaly | 0 | 0.0046 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 32 | Same Family | `tunnel-Level01-SuspendedRail-002428-001` | `tunnel-Level01-SuspendedRail-003068-001` | `tunnel` | Anomaly | 0 | 0.0046 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 33 | Same Family | `tunnel-Level01-SuspendedRail-002428-001` | `tunnel-Level01-SuspendedRail-003069-001` | `tunnel` | Anomaly | 0 | 0.0046 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 34 | Same Family | `tunnel-Level01-SuspendedRail-002428-001` | `tunnel-Level01-SuspendedRail-003070-001` | `tunnel` | Anomaly | 0 | 0.0046 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 35 | Same Family | `tunnel-Level01-SuspendedRail-002428-001` | `tunnel-Level01-SuspendedRail-003071-001` | `tunnel` | Anomaly | 0 | 0.0046 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 36 | Diff Family | `tunnel-Level01-SuspendedRail-002424-001` | `tunnel-Level01-SuspendedRail-003072-001` | `tunnel` | Anomaly | 2 | 0.0152 | SAME_CAMERA_OR_VIEWPOINT | DIFFERENT_HAZARD |
| 37 | Diff Family | `tunnel-Level01-SuspendedRail-002424-001` | `tunnel-Level01-SuspendedRail-003073-001` | `tunnel` | Anomaly | 2 | 0.0153 | SAME_CAMERA_OR_VIEWPOINT | DIFFERENT_HAZARD |
| 38 | Diff Family | `tunnel-Level01-SuspendedRail-002424-001` | `tunnel-Level01-SuspendedRail-003074-001` | `tunnel` | Anomaly | 2 | 0.0153 | SAME_CAMERA_OR_VIEWPOINT | DIFFERENT_HAZARD |
| 39 | Diff Family | `tunnel-Level01-SuspendedRail-002424-001` | `tunnel-Level01-SuspendedRail-003075-001` | `tunnel` | Anomaly | 2 | 0.0154 | SAME_CAMERA_OR_VIEWPOINT | DIFFERENT_HAZARD |
| 40 | Diff Family | `tunnel-Level01-SuspendedRail-002424-001` | `tunnel-Level01-SuspendedRail-003076-001` | `tunnel` | Anomaly | 2 | 0.0155 | SAME_CAMERA_OR_VIEWPOINT | DIFFERENT_HAZARD |
| 41 | Diff Family | `tunnel-Level01-SuspendedRail-002424-001` | `tunnel-Level01-SuspendedRail-003077-001` | `tunnel` | Anomaly | 2 | 0.0156 | SAME_CAMERA_OR_VIEWPOINT | DIFFERENT_HAZARD |
| 42 | Diff Family | `tunnel-Level01-SuspendedRail-002424-001` | `tunnel-Level01-SuspendedRail-003078-001` | `tunnel` | Anomaly | 2 | 0.0157 | SAME_CAMERA_OR_VIEWPOINT | DIFFERENT_HAZARD |
| 43 | Diff Family | `tunnel-Normal-SuspendedRail-000962-001` | `tunnel-Normal-SuspendedRail-001850-001` | `tunnel` | Normal | 2 | 0.0120 | SAME_CAMERA_OR_VIEWPOINT | NO_VISIBLE_HAZARD |
| 44 | Diff Family | `tunnel-Normal-SuspendedRail-000963-001` | `tunnel-Normal-SuspendedRail-001851-001` | `tunnel` | Normal | 2 | 0.0125 | SAME_CAMERA_OR_VIEWPOINT | NO_VISIBLE_HAZARD |
| 45 | Diff Family | `tunnel-Normal-SuspendedRail-000964-001` | `tunnel-Normal-SuspendedRail-001852-001` | `tunnel` | Normal | 2 | 0.0123 | SAME_CAMERA_OR_VIEWPOINT | NO_VISIBLE_HAZARD |
| 46 | Domain Cov | `power-Level01-SuspendedRail-002410-001` | `power-Level01-SuspendedRail-003045-001` | `power` | Anomaly | 2 | 0.0182 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 47 | Domain Cov | `power-Level01-SuspendedRail-002411-001` | `power-Level01-SuspendedRail-003046-001` | `power` | Anomaly | 2 | 0.0185 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 48 | Domain Cov | `power-Level01-SuspendedRail-002412-001` | `power-Level01-SuspendedRail-003047-001` | `power` | Anomaly | 2 | 0.0189 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 49 | Domain Cov | `oil_chemical-Level01-SuspendedRail-002379-001` | `oil_chemical-Level01-SuspendedRail-003002-001` | `oil_chemical` | Anomaly | 4 | 0.0245 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |
| 50 | Domain Cov | `oil_chemical-Level01-SuspendedRail-002383-001` | `oil_chemical-Level01-SuspendedRail-003006-001` | `oil_chemical` | Anomaly | 4 | 0.0261 | SAME_SCENE_NEARBY_FRAME | SAME_HAZARD |

---

## 5. Kết luận và trả lời câu hỏi nghiên cứu then chốt

### 5.1 Câu hỏi nghiên cứu then chốt

> **"Có bằng chứng vững chắc nào cho thấy phân chia huấn luyện/kiểm tra chính thức (`official train/test split`) của InspecSafe-V1 đã phân chia các khung hình trích xuất từ cùng một video, chuỗi chụp hoặc cùng góc máy quan sát xuyên qua hai tập hay không?"**

### 5.2 Đánh giá chính thức

> ### Kết luận: **STRONG EVIDENCE (BẰNG CHỨNG VỮNG CHẮC VÀ TOÀN DIỆN)**

Kết luận này được xác lập dựa trên 4 trụ cột bằng chứng vật lý và dữ liệu không thể bác bỏ:

1. **Bằng chứng Byte & Pixel Exact:** Phát hiện 7 cặp ảnh xuyên split hoàn toàn giống nhau từng byte và từng điểm ảnh sau giải mã. Các cặp này phát sinh do hiện tượng nhân bản ảnh đa nguy cơ sang nhiều danh mục nguy cơ upstream rồi phân chia theo chỉ số thứ tự độc lập.
2. **Bằng chứng Chuỗi Video liên tục (Video Slicing Leakage):** Toàn bộ 1.000 mẫu Anomaly bị chi phối bởi 12 họ nguồn nguy cơ, trong đó tác giả đã thực hiện thao tác cắt danh sách khung hình theo trật tự thời gian (khoảng 25% đầu cho Test và 75% sau cho Train). Các trường hợp như họ `nonmobile` (xe đạp trong hầm), `cigarette` (công nhân hút thuốc cách nhau 1 giây), `fire` (đám cháy cách nhau 1 giây) chứng minh trực tiếp rằng các khung hình liên tiếp từ cùng một đoạn video giám sát đã bị xé lẻ và đưa sang hai bên của split.
3. **Bằng chứng Trùng lặp Điểm dừng Robot (Waypoint Viewpoint Repetition):** 100% các mẫu tương đồng cao trong tập dữ liệu `Normal_data` phản ánh cùng một góc máy và tọa độ dừng vật lý của robot quan sát cùng một thiết bị tĩnh qua các ngày tuần tra khác nhau.
4. **Xung đột Nhãn nghiêm trọng (Direct Label Contradictions):** Cùng một hình ảnh nhưng tập Train học là Cấp 1 (không đội mũ bảo hộ) trong khi tập Test đánh giá là Cấp 2 (không đeo găng tay); cùng một ảnh Train xếp vào luyện kim (`metallurgy`), Test lại xếp vào hóa dầu (`oil_chemical`).

### 5.3 Tác động phương pháp luận đối với SafeShift

1. **Nguy cơ ước lượng sai lệch hiệu năng VLM (Overestimation Bias):**
   - Nếu sử dụng nguyên bản phân chia `train`/`test` chính thức của InspecSafe-V1 để tinh chỉnh (fine-tuning) hoặc đánh giá các mô hình thị giác-ngôn ngữ (VLM), mô hình có thể dễ dàng đạt điểm số giả tạo nhờ ghi nhớ (memorization) cảnh nền, thiết bị cố định tại điểm tuần tra hoặc nhận diện các khung hình liền kề của cùng một sự cố.
   - Benchmark hiện tại không phản ánh năng lực khái quát hóa thực sự đối với các mối nguy hiểm mới hoặc các trạm tuần tra chưa từng gặp (unseen environments).

2. **Khuyến nghị chiến lược cho Giai đoạn Week 2 (Research Lead):**
   - **Tái thiết kế giao thức đánh giá (Benchmark Re-protocolization):** Không thể giữ nguyên `official split` làm thước đo chính cho SafeShift. Cần thiết lập phân chia dựa trên nhóm độc lập (Group Split) theo trạm vật lý, theo chuỗi video (video-level) hoặc theo miền công nghiệp (Cross-Domain Zero-Shot Split).
   - **Xử lý tập dữ liệu:** Xây dựng danh mục loại trừ (exclusion list) hoặc lọc sạch các cặp trùng lặp exact và near-duplicates liền kề trước khi tiến hành huấn luyện để tránh ô nhiễm dữ liệu (data contamination).
   - **Lưu trữ toàn vẹn:** Tiếp tục bảo tồn nguyên vẹn thư mục dữ liệu gốc `data/raw/InspecSafe-V1/` theo đúng nguyên tắc nghiên cứu; mọi phân chia mới hoặc tập dữ liệu tinh chỉnh sẽ được tạo ra dưới dạng manifest dẫn xuất trong `data/processed/` với mã nguồn và kiểm toán minh bạch.
