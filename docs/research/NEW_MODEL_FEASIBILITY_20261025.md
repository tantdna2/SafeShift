# Khả thi đề xuất mô hình AI mới cho SafeShift — 25/10/2026

**Trạng thái: tài liệu nghiên cứu để review; không phải quyết định đổi đề tài.**

**Kết luận — SUY LUẬN:** **NO-GO (chưa nên triển khai mô hình mới hoặc chuyển Seminar lúc này).** Chưa có phương án đồng thời vượt qua ba điều kiện: khác biệt phương pháp có thể bảo vệ, nhãn phù hợp để học, và đánh giá độc lập ngoài TRAIN đã phơi nhiễm. Giữ **D9R22** là phạm vi chính thức. Có thể nghiên cứu tiếp hai câu hỏi P1/P3 bên dưới; đây không phải lựa chọn kiến trúc.

Báo cáo dựa trên main `3bcd3535ea51e023de77417ed5f2077607d49c93`, kiểm tra ngày 25/10/2026, trùng mốc tham chiếu ban đầu. [Bản đồ 25 công trình và bảng đọc sâu](NEW_MODEL_EVIDENCE_20261025.md) cung cấp nguồn gốc; [nhật ký tìm kiếm](NEW_MODEL_SEARCH_20261025.md) ghi phạm vi, kỹ năng tham khảo và giới hạn truy cập.

Quy ước: **ĐÃ KIỂM CHỨNG** = đã đối chiếu nguồn được nêu, không có nghĩa tự tái lập thí nghiệm; **SUY LUẬN** = đánh giá của người viết từ bằng chứng; **GIẢ THUYẾT** = cơ chế chưa thử; **CẦN XÁC MINH** = thiếu bằng chứng có thể làm đổi kết luận. Số liệu paper là tác giả báo cáo; số SafeShift kế thừa mức kiểm chứng của hồ sơ, không nâng thành kiểm toán mới.

## 1. SafeShift thực sự đang có gì?

### Phạm vi và kết quả

**ĐÃ KIỂM CHỨNG:** D9R22 gồm phân loại zero-shot (không học từ ví dụ của tác vụ đích) qua năm miền; phân tích lỗi nghiêm trọng theo 12 hazard atoms (đơn vị nguy cơ), tổng hợp thành bảy nhóm; và đồng thuận/bất đồng dùng lại dự đoán. Grounding (định vị bằng chứng trong ảnh) dành cho mở rộng Khóa luận. HNLO — Hazard–Normal Label Log-Odds (điểm chênh lệch log-odds nhãn nguy cơ/bình thường) — thuộc DEC-PA3-011 **PROPOSED**. Hướng A/C chưa được phê duyệt. Bốn mô hình trong roster (danh sách bắt buộc) vẫn là Qwen2.5-VL-3B-Instruct, Qwen3-VL-8B-Instruct, InternVL3-2B-hf, Moondream2. [Nguồn: tổng quan hiện hành](../RESEARCH_OVERVIEW.md).

| Mô hình/cohort (tập mẫu được xét) | Bằng chứng hiện có | Giới hạn kết luận |
| --- | --- | --- |
| Qwen2.5 | 3.763/3.763 TRAIN; AUROC 0,826656 | Raw audit PASS Linux là lịch sử kế thừa; nhiệm vụ này không đọc lại raw output (đầu ra thô). |
| InternVL3 | 3.763/3.763; AUROC 0,886182 | Kiểm chứng saved score (điểm đã lưu), không có raw audit mới. |
| Qwen3 V4 gốc | 3.539 SUCCESS/3.763 planned = 94,0473%; 1 lỗi kỹ thuật, 223 chưa chạy; AUROC 0,952793 | S2 gốc đã tìm lại và xác minh ngày 25/10; đây là kiểm chứng archive/điểm đã lưu, chưa phải raw PASS. |
| Qwen3 Recovery224 | 224/224; AUROC 0,954519 | Cohort/cấu hình riêng; không ghép với V4 để làm baseline (mốc so sánh). |
| Moondream2 | Có kiểm tra CPU ánh xạ token 28/28 | Chưa có kết quả HNLO TRAIN tương thích đã kiểm toán để so bốn mô hình. |

Trên đúng **3.539 SUCCESS IDs chung**, AUROC lần lượt Qwen2.5/InternVL3/Qwen3 = **0,824382/0,882868/0,952793**. AUROC (diện tích dưới đường ROC) đo khả năng xếp hạng, không xác nhận ngưỡng ra quyết định tốt. Qwen2.5 và InternVL3 sinh nhãn Anomaly cho cả 3.014 ảnh Normal; accuracy (độ chính xác) bốn mức chỉ 3,45%/4,36%. Không suy “đã giải quyết nhận diện an toàn” từ điểm xếp hạng. [Nguồn: kết quả và mức kiểm chứng](../RESULTS_AND_LIMITATIONS.md), [đối soát S2 và cohort chung](../SOURCE_FEASIBILITY_GATE_20261024.md).

**SUY LUẬN:** Những kết quả này hữu ích để tìm lỗi và xây baseline, nhưng chưa là đánh giá mô hình mới trên dữ liệu chưa thấy. So sánh kiến trúc còn bị nhiễu bởi độ phân giải, wrapper (lớp gọi mô hình), cấu hình và coverage (tỷ lệ mẫu có kết quả).

### Dữ liệu và độc lập nguồn

**ĐÃ KIỂM CHỨNG qua hồ sơ audit:** InspecSafe-V1 có 5.013 ảnh, TRAIN 3.763 và TEST 1.250. Support (số mẫu) Level01/02/03/04 toàn bộ là 659/326/15/4.013; TRAIN là **490/251/8/3.014**. Nhóm Anomaly gồm Level01–03: 749 TRAIN, so với 3.014 Normal. Các số tổng/TEST ở đây chỉ trích báo cáo có sẵn; nhiệm vụ không mở TEST.

| Miền theo thư mục TRAIN | Tổng | Anomaly | Normal |
| --- | ---: | ---: | ---: |
| coal_conveyor — băng tải than | 822 | 172 | 650 |
| metallurgy — luyện kim | 543 | 9 | 534 |
| oil_chemical — dầu/hóa chất | 778 | 287 | 491 |
| power — điện | 656 | 81 | 575 |
| tunnel — đường hầm | 964 | 200 | 764 |
| **Tổng** | **3.763** | **749** | **3.014** |

Có 36 trường hợp miền trong thư mục khác văn bản. Audit ghi 37.434 polygon (đa giác chú thích đối tượng), 231 nhãn thô địa phương, khác con số 234 loại trong paper. **Polygon đối tượng không mặc nhiên là vùng chứng minh nguy cơ.** Level03 chỉ tám ảnh TRAIN; metallurgy TEST không có Anomaly theo bảng lịch sử, nên không có AUROC hai lớp cho lát cắt ấy. Không đổi nhãn/miền để sửa các vấn đề này. [Nguồn: audit phân bố tại commit lưu trữ, §4](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/distribution_imbalance_audit.md).

Audit ghi **53 cặp exact duplicate (trùng chính xác)** toàn bộ, trong đó bảy cặp xuyên split (phần chia dữ liệu), 44 cặp TRAIN. dHash ≤ 8 chỉ tạo ứng viên gần trùng. Đối soát mới cho thấy **0/7 cặp ID** trong bảng “exact” của ghi chú quan sát cũ khớp bảng cặp xác minh bằng hash; không dùng câu chuyện nguồn cũ như chứng cứ độc lập. Chưa có ánh xạ đáng tin cậy sample→site/video/camera/session. Point ID khác nhau và không trùng byte không chứng minh độc lập nguồn. Các biến thể trọng số hiện có giữ thứ hạng điểm; chúng không chứng minh hết leakage (rò rỉ dữ liệu). [Nguồn: cổng khả thi, phần identity reconciliation và sensitivity](../SOURCE_FEASIBILITY_GATE_20261024.md).

**SUY LUẬN:** Năm ngành là năm miền ngữ nghĩa, chưa phải năm cơ sở độc lập. Mô hình có thể học nền ảnh/ngành thay vì nguy cơ vì tỷ lệ Anomaly chênh mạnh. Chia ngẫu nhiên TRAIN hoặc loại ảnh trùng chính xác chưa đủ để chứng minh domain generalization (khái quát hóa sang miền mới).

### Tài nguyên và phần tái sử dụng

**ĐÃ KIỂM CHỨNG:** Hồ sơ Qwen3 từng dùng T4×2, hai mô hình kia T4×1; Qwen3 có lỗi hết bộ nhớ và lượt chạy dở. Đây là kinh nghiệm inference (suy luận), không phải bằng chứng đủ bộ nhớ huấn luyện. Foundation V1 hiện có record/validation (bản ghi/kiểm tra hợp lệ), đếm phân loại cơ bản, model transport interface (giao diện vận chuyển yêu cầu) và demo CPU tổng hợp; chưa có production parser/backend (bộ đọc dữ liệu/bộ thực thi dùng thật). [Kết quả](../RESULTS_AND_LIMITATIONS.md), [lộ trình](../ROADMAP.md).

Có thể tái sử dụng hợp đồng nhãn/INVALID, quy tắc lưu raw, đối soát ID/coverage, kiểm thử tổng hợp, danh mục nguy cơ và bài học audit. Code lịch sử phải được đọc tại ref lưu trữ và review riêng trước khi đưa trở lại; không coi nó đã hoạt động trên main mới.

**CẦN XÁC MINH:** GPU/VRAM thực sự được cấp hiện tại, số giờ sử dụng, hạn Seminar, thời gian chuyên gia gán nhãn, quyền lấy thêm ảnh và nguồn ngoài. Không có căn cứ hứa hoàn thành huấn luyện trong một số ngày cụ thể.

## 2. Từ khảo sát rộng đến khoảng trống có thể kiểm tra

Bản đồ đi qua sáu nhánh: nhận diện an toàn, bất thường hình ảnh, VLM (mô hình ngôn ngữ–thị giác), khái quát hóa miền, định vị bằng chứng và mô hình tiết kiệm tính toán. Không bắt đầu bằng Qwen/CLIP hoặc hướng A/C.

**ĐÃ KIỂM CHỨNG trong các nguồn đọc sâu:** mô hình nhẹ đã có EfficientAD/AnomalyDINO; học prompt (vector lời nhắc) đã có AnomalyCLIP/AdaCLIP; so tham chiếu và học phần sai khác đã có InCTRL/IDEAL; biểu diễn đối tượng/quan hệ đã có ObjectCore/LayoutAD; suy luận có vùng chứng cứ đã có EGVLR/O-VAD; chọn vùng ảnh thích ứng đã có CF-GAP. [Bảng so sánh và vị trí đọc](NEW_MODEL_EVIDENCE_20261025.md).

**SUY LUẬN:** Khoảng trống đáng hỏi là liệu một cơ chế cụ thể giảm **bỏ sót nguy cơ nhìn thấy được** trên nguồn mới trong giới hạn tính toán hay không. “Độ hiếm của hình ảnh”, “bố trí khác thường”, “khuyết tật sản phẩm” và “nguy cơ an toàn” không tương đương. Không dùng điểm cao trên MVTec/VisA làm bằng chứng trực tiếp cho InspecSafe.

Báo cáo giữ ba phương án để so sánh, kể cả phương án bị loại. Chúng lần lượt thay đổi **cách biểu diễn quan hệ**, **cách so sánh với tham chiếu**, và **cách phân bổ quan sát**. Chưa phương án nào được xác nhận là đóng góp mới.

## 3. Ba phương án và phản biện

### P1 — Học quan hệ nguy cơ với trạng thái “chưa quan sát được”

**Vấn đề:** Không thấy vật bảo vệ trong ảnh có thể do thật sự thiếu, bị che, ngoài khung hoặc không áp dụng. Gộp các trường hợp này dễ tạo báo động giả hoặc kết luận an toàn quá tự tin.

**GIẢ THUYẾT kiến trúc:** ảnh → bộ mã hóa/đề xuất vùng có sẵn → các nút đối tượng với vai trò → các cạnh quan hệ có hai biến riêng: trạng thái nguy cơ và khả năng quan sát. Một bộ cập nhật quan hệ học cách truyền bằng chứng “có/không/chưa biết” theo vai trò, kết hợp bộ dự đoán điều kiện áp dụng. Bộ đọc ra quyết định phải giữ bất định khi bằng chứng bắt buộc chưa được quan sát. Ví dụ minh họa giả định: “người–vùng hoạt động máy–rào chắn”, không tự gán đây là nhãn chính thức mới.

**Kế thừa:** detector (bộ phát hiện), encoder (bộ mã hóa), graph neural network (mạng nơ-ron đồ thị), concept bottleneck (nút thắt khái niệm) và hiệu chỉnh xác suất đều đã có. **Phần muốn đề xuất:** cơ chế cập nhật bằng chứng theo khả năng quan sát và điều kiện áp dụng, tách khỏi trạng thái nguy cơ; phải đặc tả toán học và chỉ ra khác biệt với mô hình đồ thị bất định hiện hữu. Thêm nhãn “unknown” hay thêm một loss (hàm mất mát) riêng chưa đủ.

**Học và dữ liệu:** giữ cố định encoder; học đầu vai trò, quan hệ, khả năng quan sát và bộ cập nhật từ chú thích được chuyên gia xác nhận. Cần vùng chứng cứ, quan hệ, “không áp dụng/không nhìn rõ”, cùng ảnh bình thường tương ứng và ID nguồn. InspecSafe có polygon đối tượng và nhãn ảnh, nhưng chưa xác nhận có đủ các nhãn này. Không lấy lời giải thích VLM làm ground truth (nhãn chuẩn).

**Đối thủ gần:** LayoutAD, ObjectCore, LogicQA, EGVLR, concept bottleneck; PowerXGraph++ là đầu mối rất gần cần đọc đầy đủ. Xem R03/R05/R11–13/R22. **Phản biện:** chỉ thêm đồ thị hoặc diễn giải luật an toàn là tích hợp; cấu trúc đồ thị có thể ghi nhớ ngành. Ảnh 2D không cho biết chắc điện áp, nồng độ khí, trạng thái máy hay khoảng cách vật lý.

**Thực nghiệm tối thiểu được đề xuất, chưa thực hiện:** một nhóm nguy cơ nhìn thấy được, nguồn tách biệt, cùng encoder và cùng nhãn cho mọi đối chứng. So bộ phân loại đặc trưng cố định, bộ luật quan hệ, đồ thị thông thường và P1. Ablation (loại bỏ từng thành phần): bỏ trạng thái quan sát; bỏ điều kiện áp dụng; thay cập nhật học bằng quy tắc cố định. So cả cùng tỷ lệ được trả lời để tránh cải thiện giả bằng từ chối nhiều hơn. Hoán đổi nền ảnh chỉ là kiểm tra chẩn đoán, phải kiểm tra ảnh sửa còn hợp lệ.

**Bác bỏ:** lợi ích mất khi tách nguồn, không hơn đồ thị thường khi cùng ngân sách nhãn, hoặc chỉ đạt nhờ từ chối nhiều ca khó. Không gọi kết quả không có ý nghĩa thống kê là tương đương nếu khoảng bất định còn rộng.

**Khả thi/rủi ro — SUY LUẬN:** phần đầu nhỏ có thể vừa một GPU phổ thông khi đặc trưng đã lưu, nhưng trích đặc trưng, detector và số vùng có thể chi phối chi phí. Chưa đo VRAM. Nút nghẽn chính là nhãn quan hệ/quan sát và đủ nguồn có cả hai trạng thái. Nếu không cải thiện, vẫn có thể báo cáo kiểm tra khả năng quan sát và giới hạn đồ thị trên nguồn mới; đó là đóng góp đánh giá, không tự động là “mô hình mới”.

### P2 — Học sai khác nguy cơ từ tham chiếu có kiểm tra tính tương đồng

**Vấn đề:** So ảnh truy vấn với ảnh bình thường sai loại máy/góc nhìn dễ chấm nền khác nhau thành bất thường.

**GIẢ THUYẾT kiến trúc:** encoder cố định → ghép đối tượng/vùng giữa truy vấn và tham chiếu → bộ học biến thiên bình thường từ cặp normal–normal → bộ tách phần sai khác liên quan nguy cơ → đầu đánh giá. Một nhánh học “có đủ tương đồng để so không” có thể từ chối tham chiếu ngoài hỗ trợ. Bộ nhớ tham chiếu loại cùng nguồn khi đánh giá.

**Kế thừa và tính mới:** patch matching (ghép mảnh đặc trưng), memory bank (bộ nhớ tham chiếu), residual learning (học phần sai khác) đã có trong AnomalyDINO/InCTRL/ObjectCore. **IDEAL còn trực tiếp loại bỏ biến thiên bình thường bằng không gian con PCA và học hướng sai khác.** Vì vậy “triệt nhiễu rồi học sai khác” không còn là luận điểm mới. Phần còn giả định là học tính so sánh được cùng phép ghép có vai trò; chưa có chứng minh nó hơn một bộ lọc tham chiếu thông thường. [R09/R11/R14/R15](NEW_MODEL_EVIDENCE_20261025.md).

**Học/dữ liệu:** học bộ ghép và phần sai khác từ cặp bình thường/nguy cơ được xác nhận tương ứng, có nhãn vùng và nguồn; cần trường hợp tương đồng ngoại hình nhưng khác trạng thái. Hiện chưa có manifest cặp phù hợp đã xác minh. Nhãn nhị phân ảnh không đủ để xác nhận phần nào là nhiễu. Nếu lấy normal ở miền đích làm tham chiếu, phải gọi đó là few-shot adaptation (thích nghi với ít ví dụ), không gọi khái quát hóa hoàn toàn chưa thấy miền đích.

**Kiểm tra bác bỏ:** so nearest-neighbor (láng giềng gần nhất), InCTRL, IDEAL dưới **cùng quyền dùng nhãn/tham chiếu**, cùng encoder và độ phân giải. Loại bộ lọc tương đồng, loại bộ triệt biến thiên, thay tham chiếu ghép bằng ngẫu nhiên, tách cùng/khác nguồn. Lợi ích mất trên nguồn mới hoặc bằng IDEAL sau cân bằng thông tin đầu vào sẽ bác bỏ lý do tạo mô hình riêng. Không so phương án được xem anomaly đích với baseline chỉ được xem normal rồi quy chênh lệch cho kiến trúc.

**Khả thi/rủi ro — SUY LUẬN:** head (đầu học) nhỏ và bộ nhớ có thể khả thi, nhưng ghép dày nhiều ảnh tăng RAM/VRAM; biến thiên bình thường có thể chứa chính tín hiệu nguy cơ và bị xóa mất. Thu cặp đúng nguồn khó hơn huấn luyện. **NO-GO cho phương án này ở thời điểm hiện tại:** trùng cơ chế rất gần và thiếu dữ liệu quyết định. Kết quả âm chỉ có giá trị nếu chỉ ra khi nào so tham chiếu thất bại dưới protocol hợp lệ.

### P3 — Bộ chọn vùng học theo bằng chứng còn thiếu dưới ngân sách

**Vấn đề:** Thu nhỏ ảnh công nghiệp có thể làm mất nguy cơ nhỏ; quét mọi ô ảnh tốn chi phí. Chỉ chọn vùng nổi bật có thể bỏ qua nguy cơ không gây chú ý.

**GIẢ THUYẾT kiến trúc:** một encoder nhỏ xem toàn cảnh độ phân giải thấp; bộ chọn vùng tuần tự nhận đặc trưng, lịch sử vùng đã xem và bản đồ bằng chứng còn thiếu; encoder cục bộ đọc crop (ảnh cắt) độ phân giải cao; bộ tổng hợp cập nhật quyết định. Bộ chọn phải phân bổ một phần ngân sách cho vùng chưa đủ chứng cứ trước khi kết luận bình thường. Cơ chế trọng tâm là cập nhật “thiếu bằng chứng gì” để chọn lần quan sát tiếp; không bắt buộc dùng đồ thị P1.

**Kế thừa và tính mới:** DynamicViT đã chọn/bỏ token (đơn vị đặc trưng); CF-GAP đã định hướng quan sát từ thô đến tinh. CNN/Transformer nhỏ và attention (cơ chế chú ý) cũng không mới. Phần đề xuất phải cho thấy việc biểu diễn thiếu bằng chứng dẫn đến chính sách chọn vùng khác và tốt hơn entropy/saliency (độ bất định/độ nổi bật), không chỉ thêm phạt ngân sách hoặc đổi prompt. Chưa chứng minh được điều này. [R24–25](NEW_MODEL_EVIDENCE_20261025.md).

**Học/dữ liệu:** giữ encoder cục bộ cố định ban đầu; học bộ chọn và tổng hợp từ vùng chứng cứ chuyên gia, cùng mức cải thiện dự đoán khi xem thêm vùng trên dữ liệu phát triển. Có thể học bắt chước thứ tự quan sát từ các crop ứng viên; không cần mặc định reinforcement learning (học tăng cường) cho VLM 8B. Nhãn ảnh chỉ là giám sát yếu, khó phân biệt “crop vô ích” với “crop chứa nguy cơ mà encoder không đọc được”. Cần nhãn chứng cứ và kích thước nguy cơ; polygon đối tượng chưa đáp ứng.

**Thực nghiệm tối thiểu đề xuất:** nhóm nguy cơ nhỏ nhưng nhìn được, độ phân giải gốc tương đương, nguồn độc lập. So toàn cảnh thu nhỏ, lưới crop đều, chọn ngẫu nhiên, saliency, chính sách CF-GAP thích nghi hợp lệ, và P3. Giữ cùng encoder, tổng pixel/token được đọc và báo thêm latency (độ trễ) thực; không coi giảm FLOPs (số phép tính) đồng nghĩa giảm thời gian.

**Ablation/bác bỏ:** bỏ trạng thái bằng chứng thiếu; thay phần ngân sách dự phòng bằng ngẫu nhiên; bỏ lịch sử crop; đối chứng oracle (biết trước vùng chứng cứ) để biết trần lợi ích. Nếu oracle còn không hơn toàn cảnh thì dừng; nếu P3 chỉ bằng chọn ngẫu nhiên/lưới tại cùng chi phí hoặc lợi ích mất khi tách nguồn thì bác bỏ. Phải ghi riêng nguy cơ nhỏ, ảnh bình thường và trường hợp không nhìn thấy; không dùng crop để suy thông tin ngoài ảnh.

**Khả thi/rủi ro — SUY LUẬN:** mô hình học có thể nhỏ, nhưng nhiều crop, tiền xử lý và truy cập bộ nhớ có thể xóa lợi ích. Có thể học camera/bố cục thay cho nguy cơ; ít ca hiếm khiến chính sách chọn vùng sụp về nền. Nếu không hơn, đường đánh đổi độ trễ–bỏ sót với baseline công bằng là kết quả kiểm chứng được, chưa đủ bảo đảm đóng góp kiến trúc.

## 4. Đánh giá hợp lệ trước khi nói “cải tiến”

Toàn bộ phần này là **đề xuất nghiên cứu, chưa phê duyệt protocol/metric/split**.

1. **Đơn vị độc lập:** xác minh site/video/camera/session trước, giữ toàn bộ cùng nguồn và nhóm trùng trong cùng phần chia. Lưu quy tắc, ID và provenance (nguồn gốc) có thể kiểm tra. Nếu không xác minh được, chỉ kết luận trên nhóm heuristic (quy tắc gần đúng).
2. **Dữ liệu phát triển:** TRAIN hiện có đã được xem trong quá trình hình thành giả thuyết. Chia nội bộ để phát triển được nhưng không đổi tên thành kiểm định xác nhận chưa phơi nhiễm. Leave-one-domain-out (giữ lại một miền để đánh giá) trên TRAIN chỉ là chẩn đoán; còn phải xử lý nguồn chung và khác biệt tỷ lệ nhãn.
3. **Kiểm định ngoài TRAIN:** cần dữ liệu công nghiệp mới được phép dùng, cùng định nghĩa nguy cơ, có nhãn độc lập và nguồn tách biệt. SteelBench là video một nhà máy; MVTec/VisA là khuyết tật sản phẩm; không mặc định chúng là bộ kiểm định thay thế. **Không có dữ liệu ngoài TRAIN phù hợp thì NO-GO cho tuyên bố khái quát hóa. TEST khóa không dùng trong nhiệm vụ hoặc để chọn phương án.**
4. **Chống học lối tắt:** baseline chỉ dùng miền, nền ảnh hoặc đặc trưng toàn cảnh; bộ phân loại tuyến tính trên encoder cố định; nhãn chuẩn và dữ liệu chú thích giống nhau cho mọi mô hình. Mỗi nguồn cần đủ trạng thái để tách nguy cơ khỏi ngành; thiếu overlap (phần phân bố chồng lấp) thì thống kê không tự khắc phục được.
5. **Đích đánh giá đề xuất:** với nguy cơ được duyệt, đo tỷ lệ bỏ sót tại ngưỡng báo động giả chốt trên development (tập phát triển), kèm mẫu số, coverage/INVALID và bất định. AUROC/AUPRC (diện tích dưới đường precision–recall) chỉ bổ sung. Grounding dùng nhãn chứng cứ phù hợp, không dùng mọi polygon đối tượng. Đây không thay metric D9R22.
6. **Thực nghiệm công bằng:** baseline mạnh và đơn giản, cùng dữ liệu/độ phân giải/quyền dùng nhãn/ngân sách tìm siêu tham số. Ghép các kết quả trên đúng ảnh và nguồn; lặp seed (hạt giống ngẫu nhiên) chỉ đo biến thiên huấn luyện, không tạo thêm nguồn độc lập. Bootstrap theo nguồn (lấy mẫu lại cả cụm nguồn) chỉ hợp lý khi có đủ nguồn; báo riêng mỗi miền và trường hợp metric không xác định.
7. **Ngăn lựa chọn sau khi thấy kết quả:** chốt một giả thuyết chính, baseline, tiêu chí dừng và mức cải thiện đáng quan tâm trước đánh giá mới. Sau kiểm kê nguồn/nhãn mới tính độ chính xác hoặc power (khả năng phát hiện hiệu ứng); chưa có cơ sở nêu cỡ mẫu bảo đảm. Nếu khoảng bất định rộng, kết luận chưa đủ bằng chứng.
8. **Tái lập:** nếu sau này được phép chạy, lưu model/revision, preprocessing, seed, commit, split/source manifest, mọi raw output kể cả lỗi trước parse, thời gian/VRAM và đường dẫn artifact tương đối. Không dùng kết quả dự đoán để sửa ground truth.

## 5. Hai câu hỏi đáng nghiên cứu tiếp và các điều kiện dừng

| Phương án | Tính mới hiện tại | Dữ liệu/tài nguyên | Đề nghị |
| --- | --- | --- | --- |
| P1: quan hệ có trạng thái quan sát | Chưa xác lập; đối thủ đồ thị/bằng chứng rất gần | Thiếu nhãn quan hệ/quan sát và nguồn; phần học nhỏ chỉ là giả định | Nghiên cứu tiếp **có điều kiện** nếu chuyên gia xác nhận loại sai lầm này đủ phổ biến và có thể gán nhãn nhất quán. |
| P2: sai khác có kiểm tra tham chiếu | Yếu; IDEAL trực tiếp chặn luận điểm triệt biến thiên bình thường | Thiếu cặp tương ứng; khó tách nhiễu khỏi nguy cơ | **NO-GO**, giữ làm đối chứng nếu sau này có bài toán phù hợp. |
| P3: chọn vùng theo bằng chứng thiếu | Chưa xác lập; CF-GAP và chọn token là đối thủ bắt buộc | Thiếu vùng chứng cứ; phải tính cả chi phí chọn/cắt ảnh | Nghiên cứu tiếp **có điều kiện** nếu mất chi tiết nhỏ là lỗi chính, và oracle cho thấy còn khả năng cải thiện. |

**SUY LUẬN:** P1 đáng hỏi vì phân biệt “không có” và “không nhìn được” có ý nghĩa với lỗi an toàn; P3 đáng hỏi vì xử lý trực tiếp giới hạn độ phân giải/tính toán. Không xếp hạng bằng tổng điểm chủ quan và không bảo đảm cái nào mới hơn. Nếu bỏ các paper 2026 còn khó truy cập khỏi lập luận, kết luận NO-GO vẫn giữ do thiếu nguồn/nhãn và các tiền lệ đã đọc; nhưng đánh giá tính mới của P1/P3 còn yếu hơn.

Các bước tiếp theo **trước khi chọn mô hình**, chưa thực hiện trong task:

- Xác nhận hạn Seminar, ngân sách GPU và giờ gán nhãn; lập bảng chi phí theo baseline × biến thể × seed × phần chia. Không chỉ tính một lần huấn luyện.
- Đọc đầy đủ PowerXGraph++ và công trình đồ thị bất định gần P1; kiểm tra chính sách chọn vùng/quan sát còn thiếu gần P3. Viết một trang “khác cơ chế ở đâu” so với từng đối thủ; nếu chỉ khác tác vụ hoặc nhãn, bỏ tuyên bố kiến trúc mới.
- Xin phạm vi audit nhãn/nguồn TRAIN phù hợp; lập mẫu phiếu chuyên gia cho nguy cơ, vùng chứng cứ và khả năng quan sát. Đo bất đồng người gán nhãn và thời gian thực tế trước mở rộng, không để họ xem gợi ý nhãn VLM khi tạo chuẩn độc lập.
- Xác minh nguồn đánh giá mới, quyền sử dụng và khả năng có cả trạng thái nguy cơ/bình thường. Chưa có thì tiếp tục D9R22 trong giới hạn bằng chứng hiện hành.
- Chỉ sau các điều kiện trên mới trình quyết định nghiên cứu và protocol riêng. Báo cáo này không ghi nhận quyết định, không cấp quyền thử GPU và không chốt encoder hay VLM.

**CẦN XÁC MINH còn lại:** tính mới toàn cục; tài nguyên thật; ánh xạ nguồn; nhãn chứng cứ/khả năng quan sát; dữ liệu ngoài TRAIN tương thích; code tái lập của các công trình chưa truy cập được; nhiễm dữ liệu tiền huấn luyện; chênh lệch thực tế của ba cơ chế. Không có kết quả mô hình đề xuất nào trong báo cáo.
