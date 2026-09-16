# W2.2 Domain & Split Policy Decision Brief

**Phân tích phương pháp luận để xác lập chính sách chia/gom dữ liệu (D2) và định nghĩa miền công nghiệp (D3) cho SafeShift**  
*Dự án SafeShift — Giai đoạn: Tuần 2 (Research Protocol), Bước W2.2*  
*Tài liệu hỗ trợ quyết định (Decision Brief) trình Research Lead và Hội đồng dự án*  
*Ngày lập: 16/09/2026*  
*Trạng thái tài liệu: `PROPOSED, NOT APPROVED` (Chờ xem xét và phê duyệt chính thức từ Research Lead)*  

---

## 1. Purpose (Mục đích và phạm vi nhiệm vụ)

Tài liệu này được biên soạn nhằm chuẩn bị cơ sở thực chứng, phân tích phương pháp luận đa chiều và cung cấp ma trận đánh giá toàn diện để **Project Owner / Research Lead** đưa ra hai quyết định kỹ thuật cốt lõi tiếp theo của giai đoạn Tuần 2:
1. **Quyết định D2 — Split / Grouping Policy (Chính sách chia và gom nhóm dữ liệu):** Xác định quy tắc phân định không gian đánh giá cho các giao thức P1, P2, P3; phân tách rạch ròi giữa đơn vị dự đoán (prediction unit) và đơn vị phân tích thống kê / lấy mẫu lại (statistical / resampling unit); thiết kế các phương án ứng viên kiểm tra độ nhạy (sensitivity analysis) có kiểm soát tương quan chuỗi và trùng lặp ảnh.
2. **Quyết định D3 — Domain Definition / Mismatch Policy (Định nghĩa miền công nghiệp và chính sách xử lý mẫu xung đột):** Xác lập siêu dữ liệu thao tác (operational metadata) định nghĩa 5 miền công nghiệp cho SafeShift; thiết lập quy tắc xử lý minh bạch đối với 36 mẫu dữ liệu xung đột giữa tên thư mục và khẳng định ngữ cảnh văn bản; và xác định chính sách báo cáo đặc thù cho miền Luyện kim (`metallurgy`).

> [!IMPORTANT]
> **Nguyên tắc toàn vẹn nghiên cứu và phân quyền theo [AGENTS.md](../AGENTS.md):**  
> Tài liệu này là một **Decision Brief** (Báo cáo hỗ trợ quyết định kỹ thuật), **TUYỆT ĐỐI KHÔNG TỰ Ý GHI NHẬN QUYẾT ĐỊNH ĐÃ PHÊ DUYỆT VÀO [DECISIONS.md](../DECISIONS.md)**. Toàn bộ các đề xuất, ma trận lựa chọn và ước tính quy mô tập dữ liệu trong báo cáo này đều mang trạng thái `PROPOSED, NOT APPROVED`. Mọi thay đổi về định nghĩa dữ liệu chỉ có hiệu lực sau khi Research Lead chính thức phê chuẩn và ghi vào nhật ký quyết định dự án.

---

## 2. Locked D1 Context (Bối cảnh phương pháp luận đã chốt từ D1)

Tại bước W2.1, Quyết định **DEC-W2-D1-001** đã được Project Owner / Research Lead chính thức phê duyệt và hợp nhất vào nhánh `main` (thông qua PR #11). Toàn bộ nội dung của Quyết định D1 là **bất biến và đã được khóa cứng**, bước W2.2 tuyệt đối không thay đổi hay điều chỉnh các nguyên tắc nền tảng sau:

1. **Seminar Research Framing:**  
   Bản chất bài toán khoa học của SafeShift Seminar (8 tuần) được xác định duy nhất là:  
   **Cross-Domain Robustness Evaluation (Đánh giá độ bền vững xuyên miền) trên Frozen Pretrained Vision-Language Models (Mô hình thị giác-ngôn ngữ đã huấn luyện sẵn và giữ nguyên trọng số)**.  
   *Quy tắc chuẩn hóa:* Tuyệt đối không gọi giao thức chính của Seminar là *Domain Generalization (Khái quát hóa miền)* theo nghĩa học máy chuẩn có học tập biểu diễn trên miền nguồn.
2. **Phân tầng giao thức thực nghiệm (Protocol Hierarchy):**
   - **P1 — Baseline Replication Protocol (Giao thức tái lập baseline):** Đánh giá zero-shot trên tập kiểm thử chính thức (**Official Test**) gồm đúng **1.250 mẫu**. Mô hình frozen. Mục tiêu: Tái lập và đối chiếu trực tiếp với các nhiệm vụ an toàn và tương đồng văn bản công bố trong bài báo gốc InspecSafe (*Scientific Data* 2026). Đánh giá định vị bằng chứng (Grounding) trên 1.250 mẫu test là phần mở rộng độc lập của SafeShift (*SafeShift extension*), không phải baseline gốc.
   - **P2 — Primary Research Protocol (Giao thức nghiên cứu chính):** Đánh giá zero-shot trên toàn bộ không gian dữ liệu quan sát được (**Full Dataset Evaluation Pool**) gồm đúng **5.013 mẫu**. Báo cáo phân rã chi tiết theo **5 miền công nghiệp**. Bắt buộc **bảo lưu nguyên vẹn siêu dữ liệu phân tách gốc (`split: train/test`)** trong mọi manifest và báo cáo để bảo toàn nguồn gốc và phục vụ phân tích độ nhạy.
   - **P3 — Sensitivity Protocol Candidate (Ứng viên giao thức phân tích độ nhạy):** Đánh giá có xét nhóm (*Group-aware evaluation*). Hiện tại chỉ ở trạng thái ứng viên phân tích độ nhạy, **chưa được coi là clean benchmark (benchmark sạch)**, và phụ thuộc hoàn toàn vào việc W2.2 có xác lập được chính sách gom nhóm có cơ sở khoa học hay không.
   - **P4 — Thesis / Later DG Candidate (Hướng DG cho luận văn sau):** Huấn luyện/tinh chỉnh trên miền nguồn kết hợp kiểm thử trên miền đích giữ lại (*Leave-One-Domain-Out — LODO*). Dành cho giai đoạn Luận văn tốt nghiệp sau này; không thuộc phạm vi Seminar.
3. **Khung câu hỏi nghiên cứu hoạt động (Working Research Questions):**  
   Khóa 3 câu hỏi nghiên cứu: **RQ1** (Biến thiên hiệu năng zero-shot xuyên miền và đồng biến thiên với nền tảng robot tuần tra — *không đưa ra khẳng định nhân quả*), **RQ2** (Tập trung lỗi theo cấp an toàn và phân tầng nguy cơ — *chờ kết quả điều tra D6 ở W2.3*), và **RQ3** (Tính nhất quán phân loại - bám bằng chứng không gian — *không tự ý gán nhãn "đúng đáp án, sai lý do"*).
4. **Các nội dung D1 chuyển giao cho W2.2 giải quyết:**  
   Chính sách nhãn miền cuối cùng; phương án xử lý 36 mẫu xung đột tên miền; quy tắc gom nhóm mẫu; và tập con/phân chia phân tích ứng viên cho P3.

---

## 3. Dataset Facts (Các sự thật thực chứng bất biến của bộ dữ liệu)

Mọi phân tích trong Decision Brief này được xây dựng trên hệ thống số liệu kiểm toán thực chứng độc lập đã hoàn tất tại Tuần 1 ([notes/w1_dataset_audit.md](w1_dataset_audit.md), [notes/duplicate_leakage_audit.md](duplicate_leakage_audit.md), [notes/visual_provenance_review.md](visual_provenance_review.md), [notes/distribution_imbalance_audit.md](distribution_imbalance_audit.md), [notes/research_feasibility_audit.md](research_feasibility_audit.md)), tuyệt đối không được suy diễn sai khác:

1. **Tổng thể quy mô:** Bộ dữ liệu gồm đúng **5.013 mẫu** ảnh RGB (bộ ba `.jpg`, `.json`, `.txt`), chia thành `train` (**3.763 mẫu**, 75,06%) và `test` (**1.250 mẫu**, 24,94%); gồm **4.013 mẫu** Bình thường (`Normal_data`, 80,05%) và **1.000 mẫu** Bất thường (`Anomaly_data`, 19,95%).
2. **5 Miền phân loại theo thư mục (`folder_domain`):**  
   - `coal_conveyor`: 1.121 mẫu (train 822, test 299; Normal 865, Anomaly 256)
   - `metallurgy`: 720 mẫu (train 543, test 177; Normal 711, Anomaly 9)
   - `oil_chemical`: 1.023 mẫu (train 778, test 245; Normal 662, Anomaly 361)
   - `power`: 869 mẫu (train 656, test 213; Normal 767, Anomaly 102)
   - `tunnel`: 1.280 mẫu (train 964, test 316; Normal 1.008, Anomaly 272)
3. **Cấu trúc thư mục điểm tuần tra (`point_id`):**  
   Toàn bộ dataset có **3.234 thư mục điểm logic** (`point_id` từ `000001` đến `003234`). Độ trùng lặp `point_id` giữa tập `train` và `test` bằng đúng **0** (train/test point overlap = 0):
   - Mẫu `Normal_data` (4.013 mẫu) được tổ chức trong **2.234 điểm tuần tra**, mỗi điểm chứa từ **1 đến 4 khung hình liền kề (adjacent frames)**: 861 điểm có 1 khung hình, 1.118 điểm có 2 khung hình, 104 điểm có 3 khung hình, và 151 điểm có 4 khung hình ($861 \times 1 + 1.118 \times 2 + 104 \times 3 + 151 \times 4 = 4.013$).
   - Mẫu `Anomaly_data` (1.000 mẫu) được tổ chức trong **1.000 điểm tuần tra riêng biệt**, mỗi điểm chỉ chứa đúng **1 khung hình duy nhất** và hậu tố định danh luôn là `-001` (1.000 điểm $\times 1 = 1.000$).
   - Toàn bộ 3.234 điểm logic trong dataset đều sở hữu một khung hình mang mã số `-001`.
4. **Hiện trạng Trùng lặp Tuyệt đối (Exact Duplicates):**  
   - Có chính xác **53 nhóm trùng lặp pixel tuyệt đối** (`CONFIRMED_PIXEL_EXACT`), tất cả đều có quy mô nhóm là 2 mẫu (`group size = 2`), bao gồm tổng cộng **106 mẫu**.
   - Phân bố 53 cặp: **38 cặp Normal–Normal** (tất cả 38 cặp đều nằm nội bộ tập `train`), và **15 cặp Anomaly–Anomaly** (trong đó **8 cặp** nằm nội bộ tập `train`, và đúng **7 cặp** nằm xuyên qua split giữa `train` và `test`).
   - Cả **7 cặp trùng lặp xuyên split (`cross-split exact pairs`)** đều là các mẫu Bất thường (`Anomaly–Anomaly`). Có 1 cặp xuyên cả miền công nghiệp (`metallurgy` ở train vs `oil_chemical` ở test).
5. **Sàng lọc Tương đồng Cảm nhận (Perceptual Hash Screening):**  
   - Tại ngưỡng sàng lọc `dHash <= 8` xuyên split, ghi nhận tổng cộng **833 cặp ứng viên**.
   - Bóc tách cấu trúc: gồm đúng **7 cặp exact** đã xác minh và **826 cặp ứng viên phi exact (`nonexact candidates`)**.
   - *Quy tắc bắt buộc:* Tuyệt đối **KHÔNG ĐƯỢC GỌI** 826 cặp ứng viên này là "826 confirmed near duplicates" (826 cặp trùng lặp gần đã xác nhận), vì khảo sát Bước 4 và Bước 5 cho thấy dHash là bộ lọc sàng lọc thô, có va chạm băm và khoảng biến thiên MAE rất rộng.
6. **12 Họ Nguồn Ảnh Suy luận (`source-family pools`):**  
   - Toàn bộ 1.000 mẫu `Anomaly_data` thuộc về **12 họ nguồn** được suy luận từ tiền tố của trường siêu dữ liệu `imagePath` trong tệp JSON (`nonmobile`, `phone`, `cigarette`, `fire`, `others`, `nonmask`, `liquid`, `hand`, `head`, `smog`, `fall`, `dooropen`).
   - Toàn bộ 12 họ đều có sự phân chia chỉ số có hệ thống (**systematic index partition ~25/75**): chỉ số thấp rơi vào `test` (tổng 251 mẫu), chỉ số cao rơi vào `train` (tổng 749 mẫu).
   - *Quy tắc bắt buộc:* `source-family` **KHÔNG PHẢI LÀ TRUE VIDEO ID**. Một family thực chất là một thư mục gom nhóm theo chủng loại sự cố/nguồn ban đầu của tác giả upstream, có thể chứa nhiều cảnh quay, nhiều video clip và nhiều góc máy khác nhau. Thẩm định trực quan có mục tiêu (B5 Targeted Visual Review) xác nhận bằng chứng chia sẻ chuỗi/góc máy ở nhiều trường hợp lấy mẫu ranh giới, nhưng **KHÔNG chứng minh rằng mọi thành viên trong họ đều thuộc một video thời gian duy nhất**.
7. **Nhiễu Nền tảng Robot (Platform Confounding):**  
   Tồn tại sự gắn kết gần như tuyệt đối giữa miền công nghiệp và nền tảng robot tuần tra:
   - `coal_conveyor`: **100,0% SuspendedRail** (1.121/1.121 mẫu, robot ray treo trên cao nhìn dốc).
   - `tunnel`: **98,1% SuspendedRail** (1.256/1.280 mẫu).
   - `metallurgy`: **91,8% Wheeled** (661/720 mẫu, robot xe bánh lăn mặt sàn ngang tầm mắt).
   - `oil_chemical`: **90,2% Wheeled** (923/1.023 mẫu).
   - `power`: **87,8% Wheeled** (763/869 mẫu).  
   *Quy tắc bắt buộc:* Tuyệt đối không tuyên bố "tác động miền bằng tác động nền tảng" (`domain effect = platform effect`) hoặc "nền tảng robot gây ra suy giảm hiệu năng" (`platform causes drop`). Mối quan hệ này chỉ được mô tả chuẩn xác là **hiện tượng gây nhiễu / đồng biến thiên quan sát được (`confounding / co-variation`)**.
8. **36 Mẫu Xung đột Tên miền (`domain_mismatch`):**  
   Có chính xác **36 mẫu** có tên thư mục khác với khẳng định văn bản (`folder_domain != text_domain`), gồm 32 mẫu ở tập `train` và 4 mẫu ở tập `test`. Các hướng xung đột cụ thể:
   - `power` $\rightarrow$ `coal_conveyor`: 4 mẫu (đều ở `train`, `Normal_data`, `Level04`).
   - `metallurgy` $\rightarrow$ `oil_chemical`: 8 mẫu (đều ở `train`, `Anomaly_data`, `Level01`).
   - `tunnel` $\rightarrow$ `oil_chemical`: 24 mẫu (gồm 20 mẫu ở `train` và 4 mẫu ở `test`, đều là `Normal_data`, `Level04`).
   Tuyệt đối không tự bịa thêm các trường hợp xung đột khác ngoài 36 mẫu này.
9. **Hiện trạng đặc thù của Miền Luyện kim (`metallurgy`):**  
   Tổng số mẫu: 720 (711 Normal, 9 Anomaly). Tập kiểm thử chính thức (**Official Test**) có **177 Normal và đúng 0 Anomaly**. Trong 9 mẫu Anomaly ở tập `train`, có tới **8/9 mẫu mang khẳng định văn bản là `oil_chemical`** (`carry a text_domain = oil_chemical claim`).  
   *Quy tắc bắt buộc:* Không được viết 8/9 mẫu này "thực chất là ảnh hóa dầu", mà chỉ được khẳng định chính xác rằng: **khẳng định văn bản / text_domain của chúng là oil_chemical**.

---

## 4. Available Grouping Signals (Kiểm kê tín hiệu gom nhóm dữ liệu)

Để thiết kế chính sách gom nhóm và phân định đơn vị thống kê, toàn bộ các tín hiệu nhận diện có thể trích xuất từ InspecSafe-V1 được phân loại và đánh giá độ tin cậy khoa học trong bảng dưới đây:

| Tín hiệu gom nhóm (`Grouping Signal`) | Nguồn trích xuất (`Source`) | Độ bao phủ (`Coverage`) | Độ tin cậy (`Reliability`) | Dùng cho Primary (P1/P2)? | Dùng cho Sensitivity (P3)? | Hạn chế cốt lõi (`Main Limitation`) | Phân loại phương pháp luận (`Methodological Status`) |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| `sample_id` | Tên tệp định danh chuẩn hóa | 5.013/5.013 (100%) | Tuyệt đối | **CÓ** (Prediction Unit) | **CÓ** | Đơn vị mẫu ảnh đơn lẻ, không phản ánh tương quan chuỗi và trùng lặp bối cảnh. | **DETERMINISTIC** |
| `point_id` | Chuỗi số 6 ký tự trong tên thư mục | 5.013/5.013 (100%) | Cao | **CÓ** (Resampling Unit cho Normal) | **CÓ** (Gom nhóm Normal) | Chỉ gom được 1–4 khung hình liền kề của Normal (2.234 điểm); với Anomaly, mỗi điểm chỉ có 1 ảnh nên không gom được chuỗi sự cố. | **DETERMINISTIC** |
| `official split` | Thư mục gốc `train/` vs `test/` | 5.013/5.013 (100%) | Tuyệt đối (về vị trí đĩa) | **CÓ** (P1 Test; P2 Metadata tracking) | **CÓ** (Đối chứng rò rỉ) | Bị rò rỉ 7 cặp exact Anomaly và chia cắt chuỗi video theo chỉ số ~25/75. | **DETERMINISTIC** |
| `folder_domain` | Thư mục cấp 1 lưu trữ dữ liệu | 5.013/5.013 (100%) | Trung bình - Cao | **CÓ** (Operational Primary Domain) | **CÓ** | Xung đột ngữ nghĩa với văn bản ở 36 mẫu; phản ánh cách đóng gói tệp hơn là trạm địa lý. | **DETERMINISTIC** |
| `text_domain` | 24 câu mở đầu tệp văn bản `.txt` | 5.013/5.013 (100%) | Trung bình | **KHÔNG** (Dự phòng cho phân tích độ nhạy) | **CÓ** (Sensitivity Mismatch) | Bắt nguồn từ chú thích ngôn ngữ tự nhiên, có nguy cơ lỗi sao chép/template của người gán nhãn. | **DETERMINISTIC** |
| `robot_platform` | Token trong tên thư mục | 5.013/5.013 (100%) | Cao | **KHÔNG** (Chỉ làm biến kiểm soát / phân tầng) | **CÓ** (Phân tầng quan sát) | Đồng biến thiên (co-varying) gần như tuyệt đối với miền công nghiệp; xung đột ở Cặp Exact 4. | **DETERMINISTIC** |
| `Exact SHA/Pixel Hash` | Mã băm SHA-256 byte & raw RGB | 5.013/5.013 (100%) | Tuyệt đối | **CÓ** (Nhận diện bản sao) | **CÓ** (Loại trừ bản sao P3-A) | Chỉ phát hiện trùng lặp pixel 100% (53 cặp), không nhận diện được biến đổi góc máy hoặc khung hình kế tiếp. | **OBSERVED** |
| `dHash candidate relation` | Khoảng cách Hamming $\le 8$ | 5.041 cặp toàn tập (833 cross-split) | Sàng lọc thô | **KHÔNG** | **CÓ** (Tập mẫu kiểm tra trực quan) | Không phải quan hệ tương đương (không có tính bắc cầu); có va chạm băm; không đại diện cho near duplicate thật. | **HEURISTIC** |
| `source-family heuristic` | Regex prefix trên JSON `imagePath` | 1.000/1.000 Anomaly (100% Anomaly) | Trung bình (Kinh nghiệm) | **KHÔNG** (Không dùng làm cluster chính) | **CÓ** (Phân tầng độ nhạy thô) | Không phải true video ID; một họ chứa nhiều video/cảnh quay khác nhau; gom quá thô (12 cụm). | **HEURISTIC** |
| `imagePath provenance` | Đường dẫn gốc trong JSON | 5.013/5.013 (100%) | Cao (chỉ thị nguồn) | **KHÔNG** | **CÓ** (Truy vết xuất xứ) | 100% chuỗi đường dẫn là duy nhất; không trực tiếp cung cấp nhãn nhóm có cấu trúc. | **OBSERVED** |
| `Visual shared-viewpoint` | Đánh giá trực quan Blind-First B5 | 50 cặp mẫu phân tầng | Rất cao trên tập mẫu | **KHÔNG** | **CÓ** (Luận cứ định tính) | Chỉ bao phủ 50 cặp mẫu phân tầng, không thể quét toàn bộ 12,5 triệu cặp của dataset. | **VISUALLY_INFERRED** |
| `True Video ID` | Định danh video quay ban đầu | 0/5.013 (0%) | Không tồn tại | **KHÔNG THỂ DÙNG** | **KHÔNG THỂ DÙNG** | Tác giả upstream không công bố metadata video gốc trong bản phát hành InspecSafe-V1. | **UNAVAILABLE** |
| `Physical Factory / Site ID` | Định danh nhà máy vật lý thực tế | Chỉ có tổng số trong paper (2.239) | Không thể ánh xạ | **KHÔNG THỂ DÙNG** | **KHÔNG THỂ DÙNG** | Không có trường ánh xạ tường minh từ sample sang trạm vật lý thực tế. | **UNAVAILABLE** |

---

## 5. P1 Split Policy (Phân tích chính sách cho giao thức P1)

### 5.1 Khẳng định nguyên tắc bất biến của P1
Giao thức **P1 (Baseline Replication Protocol)** đã được Quyết định D1 ấn định phục vụ mục tiêu cốt lõi: **tái lập và đối chiếu trực tiếp với bài báo gốc InspecSafe (*Scientific Data* 2026)**. 

Do đó, chính sách phân chia dữ liệu cho P1 bắt buộc phải tuân thủ nghiêm ngặt:
- **Tập kiểm thử:** Sử dụng nguyên trạng tập kiểm thử chính thức (**Official Test Only**) gồm đúng **1.250 mẫu**.
- **Không can thiệp tập dữ liệu chính:** Tuyệt đối **KHÔNG ĐƯỢC LỌC BỎ** bất kỳ mẫu nào (kể cả 7 mẫu rò rỉ exact cross-split hay 2 cặp trùng lặp nội bộ test) khỏi tập đánh giá chính của P1. 
- **Lập luận khoa học:** Một bài báo nghiên cứu nếu tự ý lọc bỏ mẫu từ benchmark chính thức đã công bố rồi vẫn gọi kết quả đó là "kết quả tái lập baseline upstream" sẽ vi phạm nghiêm trọng tính trung thực khoa học và phá vỡ khả năng so sánh số học trực tiếp với các số liệu đã công bố trong bài báo gốc.

### 5.2 Đề xuất phương án bổ trợ: P1-Sensitivity (Phân tích độ nhạy P1)
Mặc dù baseline chính của P1 phải giữ nguyên 1.250 mẫu, việc phát hiện 7 cặp exact cross-split (và 2 cặp trùng lặp nội bộ test) tạo ra nhu cầu khoa học chính đáng để kiểm tra mức độ ảnh hưởng của hiện tượng trùng lặp lên điểm số tái lập. SafeShift đề xuất thiết kế **P1-Sensitivity (Báo cáo độ nhạy song song)**:
- **Báo cáo chính (P1 Primary Baseline):** Công bố kết quả zero-shot của các mô hình VLM trên toàn bộ **1.250 mẫu official test nguyên trạng**.
- **Báo cáo độ nhạy (P1 Exact-Deduplicated Sensitivity):** Đo lường và báo cáo thêm hiệu năng trên tập con kiểm thử đã được kiểm soát trùng lặp exact:
  - *Phương án lọc nhẹ (Chỉ xử lý trùng lặp nội bộ test):* Loại bỏ 1 mẫu đại diện trong mỗi cặp thuộc 2 cặp trùng lặp nội bộ test $\rightarrow$ Tập con gồm **1.248 mẫu**.
  - *Phương án lọc nghiêm ngặt (Xử lý cả trùng lặp nội bộ lẫn rò rỉ train):* Loại bỏ 2 mẫu trùng lặp nội bộ test và loại bỏ tiếp 7 mẫu test có bản sao exact 100% trong tập train $\rightarrow$ Tập con gồm **1.241 mẫu**.
- **Giá trị học thuật:** Cách tiếp cận này giúp SafeShift vừa bảo toàn 100% khả năng đối chiếu với upstream, vừa thể hiện sự minh bạch phương pháp luận cao nhất khi chỉ rõ cho cộng đồng nghiên cứu thấy: liệu việc loại bỏ các mẫu trùng lặp đã xác minh có làm thay đổi thứ hạng hay làm suy giảm đáng kể độ chính xác của mô hình hay không.

---

## 6. P2 Evaluation-Pool Policy (Phân tích chính sách cho giao thức P2)

### 6.1 Giữ toàn bộ 5.013 mẫu làm Primary Evaluation Pool
Giao thức **P2 (Primary Research Protocol)** là đóng góp nghiên cứu chính của SafeShift nhằm trả lời các câu hỏi về độ bền vững xuyên miền (Cross-Domain Robustness). Báo cáo khuyến nghị mạnh mẽ giữ **toàn bộ 5.013 mẫu** làm không gian đánh giá (Primary Evaluation Pool) vì các luận cứ sau:
1. **Tối đa hóa quy mô mẫu cho từng miền:** InspecSafe-V1 là bộ dữ liệu tương đối nhỏ (5.013 mẫu chia cho 5 miền). Việc sử dụng toàn bộ dữ liệu giúp tăng cường lực lượng thống kê cho từng phân xưởng (đặc biệt là các phân xưởng có số mẫu khiêm tốn như `metallurgy`: 720 mẫu, hay `power`: 869 mẫu).
2. **Cứu vãn đánh giá bất thường cho Miền Luyện kim (`metallurgy`):** Trong tập kiểm thử chính thức của P1, `metallurgy` hoàn toàn không có bất kỳ mẫu bất thường nào ($N_{\text{anomaly}} = 0$). Bằng cách mở rộng evaluation pool ra toàn bộ 5.013 mẫu, P2 thu nạp được toàn bộ **9 mẫu Anomaly** của miền này vào diện quan sát. Mặc dù $N=9$ vẫn là cỡ mẫu rất nhỏ và còn chịu sự mơ hồ nhãn văn bản (8/9 mang text claim `oil_chemical`), nhưng đây là giải pháp khả dĩ duy nhất để có thể quan sát hành vi của VLM đối với các sự cố luyện kim trong bộ dữ liệu này.
3. **Bảo tồn siêu dữ liệu phân tách gốc (`split: train/test`):** Toàn bộ 5.013 mẫu khi đưa vào P2 bắt buộc phải được gắn kèm cờ siêu dữ liệu `split = train` hoặc `split = test`. Điều này cho phép phân tích bóc tách hành vi của mô hình trên hai nửa phân chia của tác giả mà không làm mất đi nguồn gốc dữ liệu (data provenance).

### 6.2 Phân biệt rạch ròi: Evaluation Pool vs Statistical / Resampling Unit
Một trong những nhầm lẫn phương pháp luận nguy hiểm nhất trong đánh giá thị giác máy học là đồng nhất **tập dữ liệu chạy suy luận (Evaluation Pool)** với **đơn vị quan sát độc lập về mặt thống kê (Statistical Unit)**. SafeShift thiết lập nguyên tắc phân định minh định:

1. **Prediction Unit (Đơn vị dự đoán) $\equiv$ Image (Từng khung hình ảnh đơn lẻ):**  
   Mô hình VLM luôn nhận đầu vào là một ảnh RGB độc lập kèm câu prompt chỉ dẫn để sinh ra dự đoán an toàn và tọa độ bounding box. Toàn bộ 5.013 raw outputs phải được lưu trữ chi tiết ở cấp độ ảnh.
2. **Đối với mẫu Normal (`Normal_data`):**  
   Do 4.013 mẫu Normal được trích xuất từ 2.234 điểm tuần tra (trong đó có 1.373 điểm chứa từ 2 đến 4 khung hình liền kề với góc máy gần như bất biến), các khung hình trong cùng một `point_id` có tương quan quang học và bối cảnh rất cao.  
   *Giải pháp:* Vẫn thực hiện suy luận trên toàn bộ các khung hình để đo lường độ ổn định của mô hình, nhưng khi tính toán độ bất định thống kê (Statistical Uncertainty) và khoảng tin cậy (Confidence Intervals — CI), **đơn vị lấy mẫu lại (Resampling Unit) phải là `point_id` (Cluster Bootstrap)**. Việc lấy mẫu lại theo cụm điểm sẽ phản ánh đúng mức độ biến thiên giữa các vị trí vật lý độc lập thay vì phóng đại kích thước mẫu giả tạo.
3. **Đối với mẫu Anomaly (`Anomaly_data`):**  
   Cả 1.000 mẫu Anomaly đều có mã điểm riêng biệt (1.000 point folders với instance `-001`). Mặc dù 12 họ nguồn bộc lộ dấu vết chuỗi ở một số trường hợp, nhưng vì không có true video ID, **không được gán ép toàn bộ một họ nguồn thành một cụm thống kê duy nhất**. Đối với phân tích chính của P2, đơn vị phân tích cho Anomaly vẫn được giữ ở cấp độ mẫu (`sample-level`), kết hợp kiểm tra độ nhạy phân tầng theo họ nguồn ở P3.

---

## 7. P3 Sensitivity Designs (Phân tích các phương án thiết kế ứng viên cho P3)

Giao thức **P3 (Sensitivity Protocol Candidate)** đóng vai trò là công cụ kiểm chứng độ bền vững của các kết luận rút ra từ P1 và P2. Dưới đây là phân tích chi tiết 4 phương án thiết kế ứng viên:

### 7.1 Phương án P3-A: Exact-Duplicate Sensitivity (Kiểm soát bản sao tuyệt đối)
- **Cơ chế:** Dựa trên 53 nhóm trùng lặp pixel tuyệt đối (`CONFIRMED_PIXEL_EXACT`) đã được chứng minh bằng hàm băm SHA-256.
  - Trong mỗi nhóm 2 ảnh trùng lặp tuyệt đối, chỉ giữ lại đúng 1 mẫu đại diện (deterministic representative).
  - Đối với 7 cặp trùng lặp xuyên split giữa train và test: loại bỏ mẫu phía test nếu coi train là dữ liệu tham chiếu đã thấy, hoặc loại bỏ cả hai.
- **Quy mô tập con ứng viên (Simulated Size):**  
  Trên toàn bộ dataset: giảm đúng 53 mẫu $\rightarrow$ Tập con gồm **4.960 mẫu duy nhất** (khớp chính xác với con số 4.960 unique hashes trong kiểm toán Bước 4).  
  Trên tập test chính thức: giảm 2 mẫu trùng nội bộ và 7 mẫu rò rỉ $\rightarrow$ **1.241 mẫu**.
- **Đánh giá khoa học:**  
  *Ưu điểm:* Cơ sở toán học và dữ liệu rõ ràng 100% (tính đẳng trị băm); hoàn toàn có thể tái lập; không chứa định kiến chủ quan.  
  *Nhược điểm:* Chỉ giải quyết được lớp vỏ bề mặt là các bản sao pixel giống hệt nhau, chưa xử lý được hiện tượng các khung hình liền kề nhau vài giây trong video.  
  *Cảnh báo bắt buộc:* **Tuyệt đối không tuyên bố tập con 4.960 mẫu này là "leakage-free benchmark"**, vì các chuỗi video tương quan cao vẫn còn tồn tại.

### 7.2 Phương án P3-B: Point-Aware Normal Sensitivity (Gom nhóm Normal theo điểm tuần tra)
- **Cơ chế:** Tận dụng cấu trúc 2.234 điểm tuần tra logic của `Normal_data`. Có hai cách triển khai:
  - *Cách 1 — Đại diện tất định (Deterministic Representative Subsampling):* Trong mỗi thư mục điểm tuần tra Normal có nhiều khung hình (001, 002, 003, 004), chỉ chọn duy nhất khung hình đầu tiên `-001` làm đại diện.  
    *Quy mô tập con ứng viên (Simulated Size):* Normal giảm từ 4.013 mẫu xuống còn đúng **2.234 mẫu**. Kết hợp với 1.000 mẫu Anomaly (mỗi mẫu vốn đã là `-001`), tạo ra một tập dữ liệu rút gọn gồm đúng **3.234 mẫu** (mỗi điểm tuần tra đóng góp đúng 1 ảnh). Trên tập test: 559 Normal + 251 Anomaly = **810 mẫu**.
  - *Cách 2 — Tổng hợp cấp điểm (Point-Level Prediction Aggregation):* Vẫn chạy suy luận VLM trên toàn bộ 4.013 ảnh Normal. Sau đó, kết quả dự đoán của các khung hình trong cùng một `point_id` được gộp lại theo quy tắc: điểm tuần tra chỉ được coi là dự đoán đúng nếu đa số khung hình đúng (*majority voting*) hoặc giá trị xác suất trung bình đạt ngưỡng (*mean probability pooling*).
- **Đánh giá khoa học:**  
  *Ưu điểm:* Triệt tiêu hoàn toàn sự thiên lệch do một số điểm tuần tra có tới 4 ảnh trong khi điểm khác chỉ có 1 ảnh; đưa tỷ số Normal/Anomaly từ 4:1 về 2,23:1, giảm bớt mất cân bằng lớp.  
  *Nhược điểm:* Cách 1 làm giảm 35,5% tổng số mẫu quan sát được ($1.779$ ảnh bị loại bỏ); Cách 2 làm tăng độ phức tạp khi giải thích chỉ số đánh giá.

### 7.3 Phương án P3-C: Source-Family-Aware Anomaly Sensitivity (Độ nhạy phân tầng họ nguồn Anomaly)
- **Cơ chế:** Sử dụng 12 họ nguồn ảnh suy luận (`source-family pools`) để kiểm soát tương quan giữa 1.000 mẫu Anomaly.
- **Phân tích rủi ro phương pháp luận:**  
  Nếu coi toàn bộ một họ nguồn là một "cụm thống kê duy nhất" (single cluster) hoặc loại bỏ dữ liệu để mỗi họ chỉ giữ một đại diện, chúng ta sẽ phạm phải sai lầm nghiêm trọng:
  - 12 họ nguồn bao trùm 1.000 mẫu $\rightarrow$ quy mô trung bình lên tới ~83 mẫu/họ (họ lớn nhất như `phone` có 108 mẫu, `fire` có 104 mẫu).
  - Bằng chứng thực nghiệm ở Bước 5 khẳng định: trong cùng họ `phone`, có những ảnh chụp tại trạm van dầu khí, có ảnh chụp tại băng tải than, và có ảnh chụp tại tủ điện cao thế. Đây là các sự kiện hoàn toàn độc lập được tác giả gom chung vào danh mục vi phạm dùng điện thoại.
  - Việc coi toàn bộ 108 mẫu này là một video duy nhất là **sai sự thật thực chứng**.
- **Đánh giá khoa học:**  
  Phương án gom nhóm thô cấp family bị **BÁC BỎ (NOT RECOMMENDED AS PRIMARY GROUPING)**. Tín hiệu source-family chỉ được phép sử dụng dưới dạng **biến phân tầng để báo cáo độ nhạy (Stratified Sensitivity Factor)** nhằm kiểm tra xem mô hình VLM có bị sụt giảm hiệu năng bất thường trên các họ có bằng chứng chuỗi liên tục cao (như `nonmobile`) so với các họ phân tán (như `fall`, `dooropen`) hay không.

### 7.4 Phương án P3-D: Hybrid Sensitivity (Thiết kế ứng viên độ nhạy lai ghép được khuyến nghị)
- **Cơ chế:** Kết hợp có chọn lọc các tín hiệu gom nhóm có độ tin cậy khoa học cao nhất:
  1. *Đối với Normal:* Áp dụng cơ chế **Point-Aware** (chạy inference toàn bộ nhưng tính bootstrap CI theo cụm 2.234 `point_id`, hoặc báo cáo đối chứng với tập con 2.234 ảnh đại diện `-001`).
  2. *Đối với Anomaly:* Áp dụng cơ chế **Exact-Duplicate Control** (loại bỏ ảnh hưởng của 7 cặp cross-split exact duplicates) kết hợp **Source-Family Stratification** (báo cáo phân tầng hiệu năng trên 12 họ nguồn).
- **Đánh giá khoa học:**  
  Đây là phương án có **tính khoa học và khả năng bảo vệ cao nhất (Scientifically Defensible)**. Nó tôn trọng sự thật dữ liệu: gom nhóm chặt chẽ ở nơi có cấu trúc rõ ràng (`point_id` của Normal), xử lý triệt để các bản sao đã chứng minh toán học (exact duplicates), và thận trọng với các suy luận heuristic (không biến source-family thành video ID giả mạo).

---

## 8. Statistical Unit vs Prediction Unit (Đơn vị thống kê, cấu trúc đồ thị và lấy mẫu lại)

### 8.1 Logic Đồ thị và Thành phần Liên thông (Graph & Cluster Logic)
Khi xử lý các quan hệ tương đồng cặp (pairwise relationships), một câu hỏi kỹ thuật lớn đặt ra là: *Nếu có quan hệ giữa cặp $(A, B)$ và cặp $(B, C)$, có nên dùng thuật toán thành phần liên thông (Connected Components) để gộp chúng thành một cụm $(A, B, C)$ hay không?*

Phân tích toán học và cấu trúc dữ liệu cho thấy sự khác biệt bản chất giữa hai loại quan hệ:

1. **Đối với Trùng lặp Pixel Tuyệt đối (Exact Duplicates):**  
   - Quan hệ đồng nhất giá trị băm SHA-256 là một **quan hệ tương đương (Equivalence Relation)** hoàn hảo: có tính phản xạ ($A \equiv A$), đối xứng ($A \equiv B \Rightarrow B \equiv A$), và bắc cầu ($A \equiv B \land B \equiv C \Rightarrow A \equiv C$).
   - Do đó, việc tìm các thành phần liên thông trong đồ thị exact duplicate là hoàn toàn chặt chẽ về mặt toán học.
   - *Thực chứng InspecSafe-V1:* Toàn bộ 53 thành phần liên thông exact trong dataset đều có kích thước đúng bằng 2 (`group size = 2`). Không có bất kỳ chuỗi liên thông bậc cao nào ($N \ge 3$).
2. **Đối với Tập ứng viên Tương đồng Cảm nhận (`dHash <= 8` Candidates):**  
   - Quan hệ khoảng cách Hamming $d(A, B) \le 8$ **KHÔNG PHẢI LÀ QUAN HỆ TƯƠNG ĐƯƠNG** vì nó **hoàn toàn không có tính chất bắc cầu**. Theo bất đẳng thức tam giác:
     $$d(A, C) \le d(A, B) + d(B, C) \le 8 + 8 = 16$$
     Khoảng cách giữa $A$ và $C$ có thể lên tới 16 — một khoảng cách mà hai bức ảnh có thể hoàn toàn khác biệt nhau về mặt thị giác.
   - Nếu áp dụng thuật toán Connected Components một cách cơ học lên 833 cặp ứng viên cross-split (hoặc 5.041 cặp toàn tập), đồ thị sẽ tạo ra hiện tượng **bắc cầu giả tạo (chaining effect)**: một chuỗi các ảnh hơi giống nhau sẽ bị kéo vào một "siêu cụm" khổng lồ, nối từ bối cảnh này sang bối cảnh khác hoàn toàn xa lạ.
   - Hơn nữa, 826 cặp ứng viên phi exact chưa từng được xác minh là bản sao thực sự (trong 50 cặp lấy mẫu ở B5, có tới 21 cặp chỉ là robot chụp cùng vị trí ở ngày khác nhau).
   - *Kết luận bắt buộc:* **Tuyệt đối KHÔNG tự động biến 826 cặp ứng viên dHash thành các cụm dữ liệu (clusters) thật bằng Connected Components**. Việc gom nhóm theo perceptual hash là phi khoa học và làm méo mó cấu trúc dữ liệu.

### 8.2 Phân định Đơn vị Phân tích và Lấy mẫu lại (Candidate Units of Analysis)
Để chuẩn bị cho bước W2.4 (Metrics and Statistical Protocol), W2.2 đề xuất cấu trúc phân tầng các đơn vị phân tích:

| Mục tiêu phân tích (`Analysis Scope`) | Đơn vị dự đoán (`Prediction Unit`) | Đơn vị tổng hợp chỉ số (`Metric Aggregation Unit`) | Đơn vị lấy mẫu lại độ bất định (`Resampling / Uncertainty Unit`) | Ghi chú phương pháp luận |
| :--- | :---: | :---: | :---: | :--- |
| **Chỉ số tổng thể (Overall Metrics)** | Image (5.013) | Sample / Image | **Hybrid Block/Cluster Bootstrap:**<br>- Normal: lấy mẫu lại theo `point_id` (2.234 cụm)<br>- Anomaly: lấy mẫu lại theo `sample_id` (1.000 mẫu) | Phản ánh đúng tính độc lập không gian của Normal mà không gán ép cluster giả cho Anomaly. |
| **Chỉ số theo miền (Per-Domain Metrics)** | Image (Từng miền) | Sample / Image | **Stratified Cluster Bootstrap:**<br>Lấy mẫu lại có phân tầng theo từng miền, cụm theo `point_id` nội bộ miền. | Đảm bảo kích thước mẫu từng miền được bảo toàn trong mỗi lượt bootstrap. |
| **So sánh cặp giữa các mô hình (Paired Model Comparison)** | Image (5.013) | Paired Sample Differences | **Paired Cluster Bootstrap / McNemar test:**<br>So sánh hiệu năng của hai mô hình trên cùng một đơn vị ảnh và cùng cụm điểm. | Kiểm soát phương sai ghép cặp, tăng lực phát hiện sai khác thực chất giữa các kiến trúc VLM. |

> [!NOTE]
> Bảng trên đóng vai trò là **đề xuất ứng viên kỹ thuật** từ góc độ cấu trúc dữ liệu của W2.2. Các công thức toán học chi tiết, số lượng lượt bootstrap ($B$), mức ý nghĩa thống kê ($\alpha$) và các bài kiểm định giả thuyết chính thức (như McNemar, Permutation test) sẽ do **bước W2.4 chính thức quyết định và chuẩn hóa**.

---

## 9. Domain Label Candidates (Phân tích các chính sách định nghĩa nhãn miền D3)

Quyết định D3 cần xác định metadata nào sẽ đóng vai trò là nhãn miền thao tác (Operational Domain Label) cho SafeShift. Bốn chính sách ứng viên được đưa ra phân tích:

### 9.1 Chính sách D3-A: `folder_domain` làm Primary Operational Domain Label
- **Nội dung:** Lấy trường `folder_domain` (tên thư mục lưu trữ cấp 1) làm nhãn miền chính thức cho mọi phân tích phân rã 5 miền.
- **Xử lý 36 mẫu mismatch:** Giữ nguyên 36 mẫu này tại miền thư mục của chúng, đồng thời kích hoạt cờ cảnh báo `domain_mismatch = True` trong manifest để phục vụ truy vết.
- **Ưu điểm:** Khớp 100% với cách tổ chức dữ liệu vật lý trên đĩa và khớp với bảng số liệu tổng quan của bài báo gốc InspecSafe; hoàn toàn tất định và có độ bao phủ 5.013/5.013 mẫu; bảo toàn số lượng mẫu nguyên bản của từng miền (đặc biệt giữ được 9 mẫu Anomaly cho `metallurgy`).
- **Nhược điểm:** Chấp nhận sự tồn tại của 36 mẫu có khẳng định ngữ cảnh trong tệp văn bản mâu thuẫn với tên thư mục.

### 9.2 Chính sách D3-B: `text_domain` làm Primary Operational Domain Label
- **Nội dung:** Lấy trường `text_domain` (suy từ câu mở đầu tệp `.txt`) làm nhãn miền chính thức.
- **Xử lý 36 mẫu mismatch:** Tái phân bổ 36 mẫu sang miền được khẳng định trong câu mô tả văn bản: 4 mẫu từ `power` chuyển sang `coal_conveyor`; 8 mẫu từ `metallurgy` chuyển sang `oil_chemical`; 24 mẫu từ `tunnel` chuyển sang `oil_chemical`.
- **Ưu điểm:** Thống nhất tuyệt đối giữa nhãn miền và nội dung văn bản mô tả bối cảnh mà mô hình VLM đọc được; giải quyết mâu thuẫn ngữ nghĩa bề mặt.
- **Nhược điểm:** Làm biến dạng cấu trúc phân bố của dataset; dựa vào chú thích ngôn ngữ tự nhiên vốn có thể chứa lỗi sao chép của annotator; và **gây ra hậu quả cực đoan cho miền Luyện kim** (triệt tiêu 8/9 mẫu Anomaly của `metallurgy`, đẩy miền này vào tình trạng gần như hoàn toàn không có bất thường: chỉ còn đúng 1 mẫu).

### 9.3 Chính sách D3-C: Exclude Mismatch khỏi Per-Domain Analysis
- **Nội dung:** Loại bỏ toàn bộ 36 mẫu xung đột khỏi các bảng đánh giá phân rã theo miền công nghiệp (per-domain analysis), nhưng **vẫn giữ lại toàn bộ 36 mẫu này trong tập đánh giá tổng thể gộp (Pooled Overall Evaluation - P2)**.
- **Ưu điểm:** Loại bỏ hoàn toàn sự mơ hồ nhãn miền khỏi các so sánh đối đầu giữa các phân xưởng; bảo đảm tính thuần khiết của từng miền khi đánh giá RQ1.
- **Nhược điểm:** Làm giảm số lượng mẫu phân tích miền xuống còn 4.977 mẫu; tạo ra sự chênh lệch giữa tổng số mẫu của 5 miền ($1.121 + 712 + 1.023 + 865 + 1.256 = 4.977$) và quy mô của pooled overall (5.013 mẫu); đồng thời vẫn khiến `metallurgy` chỉ còn đúng 1 mẫu Anomaly trong bảng miền.

### 9.4 Chính sách D3-D: Dual-Report / Sensitivity Policy (Chính sách báo cáo kép song song)
- **Nội dung:** Kết hợp D3-A làm báo cáo chính và D3-C/D3-B làm báo cáo kiểm tra độ nhạy:
  - **Báo cáo phân tích chính (Primary Analysis):** Áp dụng **D3-A** (`folder_domain`), giữ nguyên 5.013 mẫu với đầy đủ 5 miền để đối chiếu chuẩn mực và bảo toàn tối đa dữ liệu. Mọi mẫu mismatch đều được đánh dấu cờ rõ ràng.
  - **Báo cáo độ nhạy (Sensitivity Analysis):** Trình bày một bảng đối chứng phụ trong phần thảo luận hoặc phụ lục kỹ thuật, thể hiện sự thay đổi của các chỉ số khi loại bỏ 36 mẫu mismatch (D3-C) hoặc khi tái gán nhãn theo văn bản (D3-B).
- **Ưu điểm:** Đạt điểm tối đa về tính minh bạch học thuật; không che giấu khiếm khuyết của dữ liệu; cung cấp câu trả lời trọn vẹn cho người phản biện bài báo rằng: *"Kết quả đánh giá độ bền vững xuyên miền có bị thao túng bởi 36 mẫu xung đột tên miền hay không?"*.

---

## 10. Domain Mismatch Analysis (Bảng dữ liệu chi tiết và phân tích sâu 36 mẫu xung đột)

### 10.1 Bảng dữ liệu chính xác 36 mẫu Domain Mismatch
Qua kiểm toán độc lập tại Bước 3 và Bước 6, toàn bộ 36 mẫu xung đột giữa thư mục và văn bản được tái hiện chính xác không sai lệch trong bảng sau:

| STT | Phân chia (`split`) | Miền thư mục (`folder_domain`) | Khẳng định văn bản (`text_domain`) | Cấp độ an toàn (`safety_level`) | Loại dữ liệu (`data_type`) | Nền tảng Robot (`robot_platform`) | Số lượng mẫu (`count`) | Tỷ lệ trong nhóm 36 mẫu (%) |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | `test` | `tunnel` | `oil_chemical` | `Level04` | `Normal_data` | `Wheeled` (24 mẫu Wheeled duy nhất trong tunnel) | **4** | 11,11% |
| **2** | `train` | `metallurgy` | `oil_chemical` | `Level01` | `Anomaly_data` | `SuspendedRail` (8 mẫu) | **8** | 22,22% |
| **3** | `train` | `power` | `coal_conveyor` | `Level04` | `Normal_data` | `Wheeled` (4 mẫu) | **4** | 11,11% |
| **4** | `train` | `tunnel` | `oil_chemical` | `Level04` | `Normal_data` | `Wheeled` (tiếp nối nhóm 1) | **20** | 55,56% |
| **Tổng** | — | — | — | — | — | — | **36** | **100,00%** |

### 10.2 Phân tích hướng xung đột và tác động dịch chuyển dữ liệu
Tổng hợp theo 3 hướng dịch chuyển cụ thể:
1. **Hướng `power` $\rightarrow$ `coal_conveyor` (4 mẫu):**  
   Cả 4 mẫu đều thuộc tập `train`, trạng thái bình thường (`Normal_data`, `Level04`). Tệp văn bản bắt đầu bằng cụm từ: *"In the coal conveyor bridge scene..."*.
2. **Hướng `tunnel` $\rightarrow$ `oil_chemical` (24 mẫu):**  
   Gồm 20 mẫu ở `train` và 4 mẫu ở `test`, đều là trạng thái bình thường (`Normal_data`, `Level04`). Đáng chú ý, đây chính là **toàn bộ 24 mẫu robot bánh lăn (`Wheeled`) duy nhất nằm trong thư mục `tunnel`** (chiếm đúng 1,88% của tunnel). Tệp văn bản khẳng định: *"In the oil, gas, and chemical plant scene..."*.
3. **Hướng `metallurgy` $\rightarrow$ `oil_chemical` (8 mẫu):**  
   Toàn bộ 8 mẫu đều thuộc tập `train`, cấp nguy hại cao nhất (`Anomaly_data`, `Level01`). Tệp văn bản khẳng định: *"In the oil, gas, and chemical plant scene..."*.

### 10.3 Tác động thay đổi quy mô miền khi chuyển đổi nhãn
Bảng đối chiếu quy mô 5 miền giữa việc sử dụng `folder_domain` (D3-A) so với `text_domain` (D3-B):

| Miền công nghiệp (`Domain`) | Quy mô theo `folder_domain` (D3-A) | Quy mô theo `text_domain` (D3-B) | Chênh lệch tuyệt đối ($\Delta$) | Mẫu Normal (D3-A $\rightarrow$ D3-B) | Mẫu Anomaly (D3-A $\rightarrow$ D3-B) | Tác động phương pháp luận cốt lõi |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `coal_conveyor` | 1.121 | 1.125 | +4 | $865 \rightarrow 869$ | $256 \rightarrow 256$ (Không đổi) | Nhận thêm 4 mẫu Normal từ `power`. |
| `metallurgy` | 720 | 712 | -8 | $711 \rightarrow 711$ (Không đổi) | **$9 \rightarrow 1$ (-88,89%)** | **Tác động cực đoan:** Mất 8/9 mẫu Anomaly duy nhất của toàn miền. |
| `oil_chemical` | 1.023 | 1.055 | +32 | $662 \rightarrow 686$ (+24) | $361 \rightarrow 369$ (+8) | Nhận 24 mẫu Normal từ `tunnel` và 8 mẫu Anomaly từ `metallurgy`. |
| `power` | 869 | 865 | -4 | $767 \rightarrow 763$ (-4) | $102 \rightarrow 102$ (Không đổi) | Chuyển 4 mẫu Normal sang `coal_conveyor`. |
| `tunnel` | 1.280 | 1.256 | -24 | $1.008 \rightarrow 984$ (-24) | $272 \rightarrow 272$ (Không đổi) | Chuyển 24 mẫu Normal sang `oil_chemical`. |
| **Tổng cộng** | **5.013** | **5.013** | **0** | **4.013** | **1.000** | Tổng thể dataset bảo toàn 100%. |

### 10.4 Chuẩn hóa ngôn ngữ học thuật cho RQ1 và Bài báo
Câu hỏi nghiên cứu **RQ1** đặt vấn đề về sự biến thiên hiệu năng zero-shot của VLM giữa các miền công nghiệp. Vì vậy, định nghĩa miền trong SafeShift cần được chuẩn hóa từ ngữ nhằm tránh gây hiểu lầm rằng bộ dữ liệu đã được xác thực địa lý thực địa:

> [!TIP]
> **Khuyến nghị cách dùng từ (Paper Wording Guidelines):**  
> 1. Sử dụng thuật ngữ: **"Operational domain label"** (Nhãn miền thao tác) hoặc **"Folder-assigned industrial domain"** (Miền công nghiệp phân bổ theo thư mục).  
> 2. **TUYỆT ĐỐI KHÔNG DÙNG:** *"Physical site ground truth"* (Danh tính thực địa vật lý chuẩn) hoặc *"Verified factory environment"* (Môi trường nhà máy đã kiểm chứng).  
> 3. Khi trình bày về nền tảng robot, sử dụng thuật ngữ: **"Platform co-variation"** (Sự đồng biến thiên của nền tảng robot) hoặc **"Platform confounding"** (Yếu tố gây nhiễu nền tảng); tuyệt đối không khẳng định *"Robot platform causes performance gap"* (Nền tảng robot là nguyên nhân gây tụt giảm hiệu năng).

---

## 11. Metallurgy Implications (Đánh giá chuyên sâu và chính sách cho Miền Luyện kim)

Miền Luyện kim (`metallurgy`) là trường hợp biên nhạy cảm và phức tạp nhất của bộ dữ liệu InspecSafe-V1:

```
Thực trạng Metallurgy:
Tổng số: 720 mẫu (711 Normal, 9 Anomaly)
Official Test: 177 Normal, 0 Anomaly  ===>  Hoàn toàn không thể đo Anomaly Detection trên P1!
Full Dataset: 711 Normal, 9 Anomaly   ===>  8/9 Anomaly mang text_domain = oil_chemical!
```

### 11.1 Các lựa chọn chính sách xử lý cho Metallurgy
SafeShift xây dựng 3 phương án ứng viên cho việc báo cáo kết quả của miền Luyện kim:

- **Phương án M1 (Bảo toàn và Cảnh báo mất cân bằng — Recommended Baseline):**  
  Giữ nguyên `metallurgy` trong các bảng tổng hợp kết quả 5 miền của P2 (với 720 mẫu theo D3-A). Tuy nhiên, tại tất cả các bảng và biểu đồ, bắt buộc phải đánh dấu cờ cảnh báo đặc biệt: `Severely Under-Supported Anomaly Class` (Lớp bất thường bị thiếu hụt mẫu trầm trọng).
- **Phương án M2 (Triệt tiêu hoặc Đánh dấu Không đáng tin cậy cho Anomaly Metrics):**  
  Vẫn báo cáo các chỉ số chung (như Overall Accuracy, Normal Specificity), nhưng đối với các chỉ số phụ thuộc trực tiếp vào mẫu số bất thường (như Anomaly Recall, Anomaly Precision, F1-Score Anomaly, AUROC), hệ thống sẽ **triệt tiêu (suppress)** hoặc ghi chú rõ: `UNRELIABLE / INSUFFICIENT_SAMPLE` do mẫu số quá nhỏ ($N_{\text{anomaly}} = 9$).
- **Phương án M3 (Báo cáo Phân tích Độ nhạy Mismatch):**  
  Báo cáo riêng một mục phân tích độ nhạy: nếu chấp nhận khẳng định văn bản của 8 mẫu mismatch (chuyển chúng sang `oil_chemical`), miền `metallurgy` chỉ còn đúng **1 mẫu Anomaly duy nhất** (mẫu `Level03` ray treo `metallurgy-Level03-SuspendedRail-002874-001`). Khi đó, bài toán phát hiện bất thường trên miền này hoàn toàn mất ý nghĩa thống kê định lượng và phải chuyển sang đánh giá trường hợp định tính (qualitative case study).

### 11.2 Nguyên tắc bắt buộc đối với Metallurgy
1. **Tuyệt đối KHÔNG tự ý xóa bỏ miền Metallurgy:** Việc tùy tiện loại bỏ 720 mẫu của miền Luyện kim khỏi benchmark sẽ làm thay đổi cấu trúc 5 miền đã công bố của InspecSafe, phá vỡ tính bao quát công nghiệp của đề tài.
2. **Tuyệt đối KHÔNG tuyên bố $N=9$ là đủ lực thống kê:** Cần thừa nhận trung thực trong bài báo rằng InspecSafe-V1 chưa cung cấp đủ dữ liệu bất thường đáng tin cậy cho miền luyện kim, và đây là một phát hiện kiểm toán (audit finding) quan trọng đóng góp cho cộng đồng.

---

## 12. D2 Decision Matrix (Ma trận đánh giá các phương án phân chia và gom nhóm D2)

Bảng so sánh đa chiều giữa 5 phương án ứng viên cho Quyết định D2:
- **Phương án 1 (Naive Image-Level):** Coi toàn bộ 5.013 ảnh là các quan sát độc lập IID thuần túy trong mọi khâu tính toán và kiểm định.
- **Phương án 2 (Point-Level Clustered Resampling):** Chạy suy luận trên 5.013 ảnh; nhưng tính khoảng tin cậy thống kê bằng cluster bootstrap theo `point_id` cho Normal.
- **Phương án 3 (P3-A Exact-Deduplicated Subset):** Chỉ đánh giá trên tập con đã loại bỏ 53 mẫu trùng lặp pixel tuyệt đối (4.960 mẫu).
- **Phương án 4 (P3-B Point-Deterministic Subset):** Rút gọn Normal về đúng 1 ảnh đại diện `-001` cho mỗi điểm tuần tra (tập con 3.234 mẫu).
- **Phương án 5 (Hybrid Protocol Hierarchy — Khuyến nghị):** Kết hợp phân tầng: P1 giữ nguyên 1.250 mẫu (+ P1-sensitivity); P2 dùng toàn bộ 5.013 mẫu với Point-Cluster Uncertainty; P3 duy trì ở trạng thái Candidate Sensitivity (P3-D Hybrid).

| Tiêu chí đánh giá (`Evaluation Criteria`) | Phương án 1 (Naive Image-Level) | Phương án 2 (Point Clustered) | Phương án 3 (P3-A Deduplicated) | Phương án 4 (P3-B Point Subset) | Phương án 5 (Hybrid Hierarchy - Đề xuất) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tính vững chắc khoa học (`Scientific Defensibility`)** | Rất thấp (Bỏ qua tương quan chuỗi) | **Cao** (Kiểm soát tương quan điểm) | Trung bình (Chỉ lọc pixel exact) | Cao (Triệt tiêu lặp frame) | **RẤT CAO** (Toàn diện, đa tầng, có đối chứng) |
| **Kiểm soát rò rỉ & lặp ảnh (`Leakage Sensitivity`)** | Không kiểm soát | Kiểm soát một phần (ở Normal) | Kiểm soát tốt bản sao pixel | Kiểm soát tốt lặp Normal | **RẤT TỐT** (Bóc tách rõ từng loại rò rỉ) |
| **Khả năng tái lập (`Reproducibility`)** | Tuyệt đối | Tuyệt đối | Tuyệt đối (với SHA-256 list) | Tuyệt đối (chọn `-001`) | **TUYỆT ĐỐI** (Mọi tập con đều có mã manifest) |
| **Sử dụng siêu dữ liệu đã xác minh (`Verified Metadata`)** | Có | **Có** (Dùng `point_id` đã audit) | **Có** (Dùng mã băm đã audit) | **Có** (Dùng `point_id` đã audit) | **CÓ** (Chỉ dùng deterministic metadata) |
| **Rủi ro gom nhóm heuristic (`Heuristic Grouping Risk`)** | Không có | **Rất thấp** (Không dùng source-family) | Không có | Không có | **RẤT THẤP** (Cách ly source-family vào sensitivity) |
| **Bảo toàn quy mô mẫu (`Sample Retention`)** | 100% (5.013) | **100%** (5.013) | 98,9% (4.960) | 64,5% (3.234 — mất 1.779 ảnh) | **100% ở P2** (Bảo tồn toàn bộ mẫu) |
| **Tương thích với P1 Baseline (`Compatibility with P1`)** | Cao | Cao | Kém (Nếu ép sửa P1) | Kém (Nếu ép sửa P1) | **HOÀN HẢO** (P1 giữ nguyên 1.250 mẫu) |
| **Tương thích với P2 Research (`Compatibility with P2`)** | Cao | **Hoàn hảo** | Kém (Bỏ bớt mẫu) | Kém (Bỏ bớt mẫu) | **HOÀN HẢO** (Được thiết kế chuẩn hóa cho P2) |
| **Độ phức tạp Seminar (`Seminar Complexity`)** | Rất thấp | Vừa phải | Thấp | Vừa phải | **HỢP LÝ** (Phân định rõ primary vs sensitivity) |

---

## 13. D3 Decision Matrix (Ma trận đánh giá các chính sách định nghĩa miền D3)

Bảng so sánh 4 chính sách ứng viên cho Quyết định D3:
- **D3-A:** `folder_domain` làm nhãn chính; 36 mismatch giữ nguyên theo thư mục, gắn cờ cảnh báo.
- **D3-B:** `text_domain` làm nhãn chính; 36 mismatch tái phân bổ theo câu mở đầu văn bản.
- **D3-C:** Loại bỏ 36 mismatch khỏi phân tích từng miền; giữ trong pooled overall (4.977 mẫu cho miền).
- **D3-D (Khuyến nghị):** Dual-report / Sensitivity policy: Báo cáo chính theo D3-A; báo cáo độ nhạy đối chứng theo D3-C và D3-B.

| Tiêu chí đánh giá (`Evaluation Criteria`) | D3-A (`folder_domain` Primary) | D3-B (`text_domain` Primary) | D3-C (Exclude Mismatch) | D3-D (Dual-Report Sensitivity - Đề xuất) |
| :--- | :---: | :---: | :---: | :---: |
| **Khả năng tái lập (`Reproducibility`)** | **Tuyệt đối** (Dựa vào đường dẫn đĩa) | Cao (Dựa vào 24 câu mở đầu) | Tuyệt đối (Danh sách 36 mẫu cố định) | **TUYỆT ĐỐI** (Đầy đủ mã nguồn và danh sách cờ) |
| **Đối chiếu Upstream (`Upstream Comparability`)** | **Hoàn hảo** (Khớp số liệu paper gốc) | Kém (Lệch số lượng từng miền) | Trung bình (Tổng miền thiếu 36 mẫu) | **HOÀN HẢO** (Bảng chính khớp 100% upstream) |
| **Tính hợp lý ngữ nghĩa (`Semantic Plausibility`)** | Trung bình (Chấp nhận 36 ca lệch) | **Cao** (Khớp câu mô tả) | Cao (Loại bỏ các ca tranh chấp) | **RẤT CAO** (Báo cáo cả hai góc nhìn) |
| **Tác động tới Metallurgy (`Effect on Metallurgy`)** | **Tốt nhất** (Giữ được 9 Anomaly) | **Cực đoan** (Chỉ còn 1 Anomaly) | Kém (Chỉ còn 1 Anomaly) | **TOÀN DIỆN** (Giữ 9 ở chính, mổ xẻ 1 ở độ nhạy) |
| **Rủi ro gán nhãn tùy tiện (`Risk of Arbitrary Shifts`)** | **Rất thấp** (Giữ nguyên hiện trạng) | Cao (Tin tưởng tuyệt đối annotator) | Thấp (Loại trừ an toàn) | **RẤT THẤP** (Không tự ý sửa nhãn dữ liệu gốc) |
| **Tính minh bạch học thuật (`Transparency`)** | Cao (Nếu có gắn cờ) | Trung bình (Che giấu lỗi thư mục) | Cao | **TỐI ĐA** (Công khai toàn bộ 36 ca xung đột) |
| **Độ thuận tiện khi báo cáo (`Ease of Reporting`)** | Rất cao (1 bảng duy nhất) | Cao | Vừa phải (Phải giải thích tổng 4.977) | **CAO** (Bảng chính chuẩn hóa + Bảng độ nhạy phụ) |

---

## 14. Preliminary Recommendation (Khuyến nghị sơ bộ trình Research Lead)

> [!IMPORTANT]
> **TRẠNG THÁI KHUYẾN NGHỊ: `PROPOSED, NOT APPROVED`**  
> Dưới đây là phương án khuyến nghị tối ưu được tổng hợp từ các phân tích thực chứng, chờ Research Lead và Project Owner xem xét, phê duyệt chính thức:

### 14.1 Khuyến nghị cho Quyết định D2 (Split & Grouping Policy)
1. **P1 Baseline Replication Protocol:**
   - Giữ nguyên trạng tập kiểm thử chính thức (**Official Test**) gồm đúng **1.250 mẫu**, không lọc bỏ duplicate trong nhánh chạy baseline chính nhằm đảm bảo tính so sánh 1:1 với bài báo gốc *Scientific Data*.
   - Phê duyệt phương án bổ trợ **P1-Sensitivity**: Báo cáo thêm kết quả trên tập con đã loại bỏ trùng lặp exact (**1.241 mẫu**) như một phân tích độ nhạy đi kèm.
2. **P2 Primary Research Protocol:**
   - Giữ nguyên toàn bộ **5.013 mẫu** làm Primary Evaluation Pool; bắt buộc duy trì siêu dữ liệu `split: train/test` trên mọi bản ghi.
   - **Prediction Unit:** Xác lập là từng khung hình ảnh độc lập (**Image-level**).
   - **Uncertainty & Resampling Candidate:** Phê chuẩn nguyên tắc **Cluster Bootstrap theo `point_id` cho Normal_data** (2.234 cụm điểm) để ước lượng khoảng tin cậy 95% CI; giữ `sample-level` cho Anomaly_data trong phân tích chính.
3. **P3 Sensitivity Protocol Candidate:**
   - Tiếp tục duy trì P3 ở trạng thái **Ứng viên phân tích độ nhạy (Candidate Sensitivity Protocol)**, không nâng cấp thành clean benchmark.
   - Cấu trúc thiết kế P3 theo hướng **Hybrid Sensitivity (P3-D)**: Kiểm soát ảnh hưởng của 7 cặp exact duplicate cross-split và đánh giá phân tầng theo 12 họ nguồn `source-family`, không biến source-family thành cluster chính thống.

### 14.2 Khuyến nghị cho Quyết định D3 (Domain Definition & Mismatch Policy)
1. **Primary Operational Domain Label:**  
   Phê chuẩn **Chính sách D3-A kết hợp D3-D**: Sử dụng trường `folder_domain` làm **Nhãn miền thao tác chính thức (Operational Domain Label)** cho phân tích phân rã 5 miền và kiểm chứng RQ1.
2. **Chính sách xử lý 36 mẫu Domain Mismatch:**  
   Áp dụng cơ chế **Dual-Report**:
   - Trong bảng kết quả chính: Giữ 36 mẫu tại miền thư mục của chúng, đánh dấu cờ tường minh `domain_mismatch = True`.
   - Trong phần phân tích độ nhạy: Báo cáo đối chứng kết quả khi loại bỏ 36 mẫu này (D3-C) hoặc khi tái phân bổ theo văn bản (D3-B), nhằm chứng minh tính bền vững của các kết luận khoa học.
3. **Chính sách đặc thù cho Miền Luyện kim (`metallurgy`):**  
   Áp dụng kết hợp **M1 + M2 + M3**: Giữ `metallurgy` trong bảng 5 miền với cờ cảnh báo mất cân bằng cực đoan; triệt tiêu hoặc đánh dấu `UNRELIABLE` đối với các chỉ số nhạy với anomaly (Recall, F1-Anomaly); và phân tích định tính riêng ca biên khi loại bỏ 8 mẫu mismatch ($N_{\text{anomaly}} = 1$).
4. **Chuẩn hóa thuật ngữ khoa học:**  
   Thống nhất sử dụng cụm từ *"Operational domain label"* và *"Co-variation with robot platform"*; không sử dụng *"Physical site ground truth"* hay khẳng định quan hệ nhân quả của robot platform.

### 14.3 Phản biện độc lập đối với phương án khuyến nghị (Devil's Advocate Analysis)
Để đảm bảo tính khách quan tối đa, trợ lý nghiên cứu tự đặt ra các luận điểm phản biện lại chính phương án khuyến nghị trên:
- *Phản biện 1 (Về việc giữ folder_domain ở D3-A):* Liệu việc giữ 24 mẫu trong `tunnel` khi văn bản ghi rõ ràng là bồn chứa hóa dầu (`oil_chemical`) có khiến người đọc đánh giá SafeShift chấp nhận dữ liệu sai sót một cách thụ động?  
  *Đáp biện:* Không thụ động, vì SafeShift đã phát hiện và gắn cờ cảnh báo độc lập; việc giữ folder_domain là để bảo toàn tính toàn vẹn của cách đóng gói nguyên bản, đồng thời báo cáo độ nhạy D3-D đã trả lời trực tiếp sai khác số học nếu chuyển nhãn.
- *Phản biện 2 (Về việc inference toàn bộ 5.013 ảnh ở P2):* Liệu việc chạy inference toàn bộ ảnh Normal có làm tăng chi phí tính toán/API không cần thiết khi nhiều ảnh trong cùng điểm chỉ cách nhau vài góc quay?  
  *Đáp biện:* Sự biến thiên góc quay vi mô giữa các frame liền kề là cơ hội thực nghiệm tuyệt vời để đo lường độ ổn định dự đoán (Prediction Consistency / Robustness) của VLM trước các biến đổi góc nhìn nhỏ.
- *Phản biện 3 (Về sự bất đối xứng giữa Normal và Anomaly trong Bootstrap):* Tại sao Normal được gom cụm theo `point_id` còn Anomaly lại lấy mẫu lại theo từng mẫu riêng lẻ?  
  *Đáp biện:* Vì Normal có cấu trúc thư mục điểm rõ ràng với 1–4 ảnh liền kề đã xác minh; trong khi Anomaly không có true video ID, và việc gộp 1.000 mẫu vào 12 họ nguồn thô sẽ phá vỡ tính đa dạng của các sự cố độc lập.

---

## 15. Risks and Limitations (Rủi ro và Giới hạn nghiên cứu)

1. **Rủi ro nhiễm dữ liệu tiền huấn luyện (Pretraining Data Contamination):**  
   InspecSafe-V1 được phát hành công khai dưới giấy phép CC-BY-4.0 từ đầu năm 2026. Do đó, các mô hình VLM thương mại hoặc mã nguồn mở mới nhất có thể đã thu thập một phần hoặc toàn bộ hình ảnh của bộ dữ liệu này vào tập tiền huấn luyện. Ngay cả khi SafeShift thực hiện zero-shot, nguy cơ mô hình đạt điểm cao nhờ ghi nhớ (memorization) thay vì năng lực suy luận vẫn tồn tại. Vấn đề này sẽ được phân tích sâu ở bước W2.5.
2. **Giới hạn của việc thiếu True Video ID:**  
   Việc tác giả upstream không công bố định danh video gốc khiến việc xây dựng một benchmark sạch hoàn toàn (tránh 100% rò rỉ chuỗi thời gian) là bất khả thi nếu không can thiệp dán nhãn thủ công lại toàn bộ 1.000 mẫu bất thường — một công việc vượt quá phạm vi của Seminar 8 tuần.
3. **Mất cân bằng lớp cực đoan tại Level03 và Metallurgy:**  
   Cỡ mẫu 15 mẫu cho `Level03` và 9 mẫu Anomaly cho `metallurgy` là các điểm nghẽn cấu trúc không thể khắc phục bằng thủ thuật thuật toán. Mọi kết luận suy diễn trên các phân lớp này đều phải được diễn giải với sự thận trọng tối đa.

---

## 16. Questions Requiring Approval (Danh mục câu hỏi trình phê chuẩn)

Nhằm chuẩn bị cho việc ban hành các quyết định chính thức, danh mục các câu hỏi kỹ thuật được phân định rạch ròi theo thẩm quyền phê duyệt:

### READY FOR D2 APPROVAL (Chính sách chia và gom nhóm dữ liệu)
1. **Phê chuẩn P1 Baseline Test:** Research Lead có chấp thuận giữ nguyên vẹn tập kiểm thử chính thức gồm đúng **1.250 mẫu** (không lọc bỏ duplicate) cho nhánh tái lập baseline chính, và phê duyệt báo cáo phụ trợ **P1-Sensitivity** trên tập con **1.241 mẫu** hay không?
2. **Phê chuẩn P2 Primary Evaluation Pool:** Research Lead có chấp thuận sử dụng toàn bộ **5.013 mẫu** làm không gian đánh giá cho giao thức nghiên cứu chính P2, với yêu cầu bắt buộc bảo lưu siêu dữ liệu gốc `split: train/test` hay không?
3. **Phê chuẩn Prediction Unit & Resampling Unit:** Research Lead có nhất trí xác lập **Prediction Unit là từng ảnh đơn lẻ (Image-level)**, và phê chuẩn ứng viên **Resampling Unit là `point_id` cho Normal_data** trong các phép tính khoảng tin cậy / cluster bootstrap hay không?
4. **Phê chuẩn Trạng thái P3:** Research Lead có chấp thuận duy trì P3 ở trạng thái **Giao thức phân tích độ nhạy ứng viên (Candidate Sensitivity Protocol)** với thiết kế lai ghép Hybrid (kiểm soát exact duplicate + phân tầng source-family), không nâng cấp thành clean benchmark hay không?

### READY FOR D3 APPROVAL (Định nghĩa miền và chính sách xử lý mismatch)
1. **Phê chuẩn Primary Operational Domain Label:** Research Lead có chấp thuận phê chuẩn **`folder_domain`** làm nhãn miền thao tác chính thức cho SafeShift phục vụ trả lời câu hỏi RQ1 và các bảng báo cáo 5 miền hay không?
2. **Phê chuẩn Chuẩn mực Thuật ngữ (Paper Wording):** Research Lead có phê duyệt việc sử dụng thuật ngữ chuẩn hóa *"Operational domain label"* và *"Co-variation with robot platform"*, tuyệt đối không gọi là *"Physical site ground truth"* hay khẳng định quan hệ nhân quả hay không?
3. **Phê chuẩn Chính sách Mismatch (D3-D):** Research Lead có chấp thuận chính sách Dual-Report: giữ 36 mẫu mismatch theo `folder_domain` trong bảng chính kèm cờ cảnh báo `domain_mismatch = True`, đồng thời báo cáo đối chứng trong phân tích độ nhạy hay không?
4. **Phê chuẩn Quy tắc Báo cáo Miền Luyện kim (Metallurgy):** Research Lead có phê chuẩn việc giữ `metallurgy` trong bảng 5 miền với cờ cảnh báo mất cân bằng cực đoan, đồng thời triệt tiêu hoặc đánh dấu `UNRELIABLE` cho các chỉ số anomaly-sensitive khi $N_{\text{anomaly}} \le 9$ hay không?

---

## 17. Evidence Sources (Nguồn tài liệu và bằng chứng thực chứng tham chiếu)

1. **Văn bản pháp quy và Quyết định dự án:**
   - [AGENTS.md](../AGENTS.md) — Nguyên tắc toàn vẹn nghiên cứu và phân quyền tác tử.
   - [ROADMAP.md](../ROADMAP.md) — Lộ trình tổng thể SafeShift Seminar.
   - [DECISIONS.md](../DECISIONS.md) — Quyết định DEC-W2-D1-001 (Research Framing & Protocol Hierarchy).
2. **Báo cáo kiểm toán và thẩm định phương pháp luận Tuần 1:**
   - [notes/w1_dataset_audit.md](w1_dataset_audit.md) — Tổng hợp kiểm định thực chứng toàn diện bộ dữ liệu InspecSafe-V1.
   - [notes/dataset_schema.md](dataset_schema.md) — Đặc tả schema bộ ba tệp (`.jpg`, `.json`, `.txt`) và 24 câu mở đầu văn bản.
   - [notes/manifest_builder.md](manifest_builder.md) — Báo cáo xây dựng manifest và kiểm tra tính toàn vẹn 5.013 mẫu.
   - [notes/dataset_validation.md](dataset_validation.md) — Báo cáo xác thực dữ liệu và kiểm tra 36 mẫu domain mismatch.
   - [notes/duplicate_leakage_audit.md](duplicate_leakage_audit.md) — Báo cáo kiểm toán 53 cặp exact duplicate, 833 cặp dHash $\le 8$ và 12 họ nguồn.
   - [notes/visual_provenance_review.md](visual_provenance_review.md) — Thẩm định trực quan Blind-First trên 7 cặp exact và 50 cặp candidates.
   - [notes/distribution_imbalance_audit.md](distribution_imbalance_audit.md) — Kiểm kê phân bố, mất cân bằng an toàn 267,5:1 và platform confounding.
   - [notes/research_feasibility_audit.md](research_feasibility_audit.md) — Đánh giá tính khả thi nghiên cứu Cross-Domain và Evidence Grounding.
   - [notes/w2_protocol_decision_brief.md](w2_protocol_decision_brief.md) — Báo cáo hỗ trợ quyết định D1 (Protocol Hierarchy & Seminar Framing).
3. **Mã nguồn và tệp cấu trúc cục bộ:**
   - [safeshift/data/manifest.py](../safeshift/data/manifest.py) — Parser trích xuất manifest và chuẩn hóa schema.
   - [safeshift/data/distribution.py](../safeshift/data/distribution.py) — Module tính toán phân bố và kiểm tra hồi quy chéo.
   - `data/manifests/dataset_validation.json` — Bằng chứng xác thực nhị phân và phân bố điểm tuần tra logic (3.234 điểm).
   - `data/manifests/duplicate_leakage_audit.json` — Bằng chứng băm SHA-256 của 53 nhóm exact duplicate và 833 cặp dHash.
   - `data/manifests/distribution_imbalance_audit.json` — Bằng chứng phân rã 10 bảng chéo và chi tiết 36 mẫu domain mismatch.
