# SafeShift — Chốt hướng Seminar và Khóa luận

Ngày: **25/10/2026**, Asia/Bangkok. Base main đã kiểm tra: `3bcd3535ea51e023de77417ed5f2077607d49c93`.

**Quyết định đề xuất duy nhất để Research Lead/giảng viên phê duyệt:** nghiên cứu độ tin cậy của nhận diện nguy cơ bằng VLM, từ kiểm chứng nhãn và điểm HNLO trong Seminar đến kiểm chứng một lớp lựa chọn ca cần người kiểm tra trong Khóa luận. Không mở lại vòng chọn P1/P2/P3. Đây là khóa lựa chọn của hồ sơ đề xuất, **chưa phải quyết định khoa học có hiệu lực hoặc quyền thực thi**.

Tên tiếng Việt: **SafeShift: Đánh giá và cải thiện độ tin cậy của quyết định nguy cơ an toàn công nghiệp bằng mô hình ngôn ngữ–thị giác**.

Tên tiếng Anh: **SafeShift: Evaluating and Improving the Reliability of Industrial Safety Hazard Decisions with Vision–Language Models**.

“Cải thiện” là mục tiêu cần kiểm chứng, không là kết quả đã đạt. Đọc cùng [kế hoạch tổng thể](SEMINAR_THESIS_MASTER_PLAN_20261025.md). PR này chỉ thêm hai tài liệu; không sửa D9R22, DEC-PA3-011, PR #132 hoặc hồ sơ lịch sử.

## 1. Bài toán trung tâm và lý do chọn

**Khi VLM đưa ra nhãn an toàn cho một ảnh công nghiệp, những tín hiệu nào thực sự giúp nhận diện quyết định dễ sai, đặc biệt ca nguy hiểm bị kết luận bình thường, và có thể dùng chúng để phân bổ một lượng kiểm tra hữu hạn hay không?**

Seminar xác định bằng chứng và giới hạn của tín hiệu trên kết quả đã có. Khóa luận dùng chính giới hạn đó để thiết kế và kiểm chứng bộ xếp ưu tiên kiểm tra, giữ cố định VLM nền. Hai học kỳ cùng nghiên cứu chuỗi **ảnh → nhãn/điểm → sai lầm → quyết định chấp nhận hoặc chuyển kiểm tra**; không phải hai đề tài độc lập.

Giá trị khoa học nằm ở tách ba vấn đề thường bị nhập làm một: xếp hạng ảnh nguy hiểm, dự đoán đúng nhãn và phát hiện một dự đoán sai. Giá trị thực tiễn là đo ca nguy hiểm còn bị bỏ qua và lượng việc phải chuyển cho người, thay vì chỉ tối đa hóa điểm trung bình. Không nghiên cứu xác suất tai nạn ngoài hiện trường hoặc thay chuyên gia an toàn.

Lựa chọn này dựa trên hiện tượng đã quan sát, không chỉ vì đã đầu tư vào HNLO: Qwen2.5 và InternVL3 có điểm phân biệt nhưng sinh cảnh báo cho toàn bộ Normal; Qwen3 có coverage chưa đầy đủ; nhóm nguồn chưa xác minh. Một bộ phân loại hoàn toàn mới chưa giải quyết được tính hợp lệ của phép đánh giá và sẽ thêm gánh nặng nhãn/tài nguyên. Bộ quyết định nhỏ cho phép kiểm chứng riêng giá trị tăng thêm của HNLO và bất đồng, kể cả kết quả phủ định.

## 2. Bằng chứng chi phối quyết định

### 2.1. Nguồn có thẩm quyền và mức kiểm chứng

Nguồn hiện hành: [tổng quan](../RESEARCH_OVERVIEW.md), [kết quả và giới hạn](../RESULTS_AND_LIMITATIONS.md), [roadmap](../ROADMAP.md), [source feasibility gate](../SOURCE_FEASIBILITY_GATE_20261024.md), [receipt](../SOURCE_FEASIBILITY_RECEIPT_20261024.json). Tài liệu main ở base trên đã được đọc; `ROADMAP.md`/`TASKS.md` tại root thuộc lịch sử trước reset, không được tạo lại.

Đã đọc ba hồ sơ PR #132 tại HEAD **`57c4377e44105bfc52bd1cc1f9f291371dc982ea`**: [khả thi mô hình mới](https://github.com/tantdna2/SafeShift/blob/57c4377e44105bfc52bd1cc1f9f291371dc982ea/docs/research/NEW_MODEL_FEASIBILITY_20261025.md), [bằng chứng](https://github.com/tantdna2/SafeShift/blob/57c4377e44105bfc52bd1cc1f9f291371dc982ea/docs/research/NEW_MODEL_EVIDENCE_20261025.md), [nhật ký tìm kiếm](https://github.com/tantdna2/SafeShift/blob/57c4377e44105bfc52bd1cc1f9f291371dc982ea/docs/research/NEW_MODEL_SEARCH_20261025.md), cùng [hậu kiểm ChatGPT](https://github.com/tantdna2/SafeShift/pull/132#issuecomment-6395383076). Hồ sơ này là khảo sát, không là quyết định chọn đề tài. Chỉ tra thêm nguồn lịch sử để xác nhận phân bố, D9R22 và đại số HNLO; không tái audit artifact hoặc inference trong nhiệm vụ này.

| Bằng chứng kế thừa | Điều hỗ trợ | Điều không hỗ trợ |
| --- | --- | --- |
| Qwen2.5-VL-3B-Instruct: 3.763/3.763 SUCCESS; HNLO AUROC 0,8266558463706973 | Có tín hiệu xếp hạng trên TRAIN; raw audit CPU Linux lịch sử PASS | Không có raw audit mới; giữ giới hạn outer receipt shard 1 và Windows 1-ULP |
| InternVL3-2B-hf: 3.763/3.763; AUROC 0,8861824613751756 | Saved-score verification (kiểm chứng điểm đã lưu) | Không nâng thành raw-logit audit PASS |
| Hai model trên sinh Anomaly cho cả 3.014 Normal; accuracy bốn mức 130/3.763 và 164/3.763 | Nhãn sinh ra và khả năng xếp hạng là hai đầu ra khác nhau | Không chứng minh HNLO tốt hơn mọi đối chứng liên tục hoặc có ngưỡng an toàn |
| Qwen3-VL-8B-Instruct V4 gốc: 3.539/3.763 SUCCESS, 1 TECHNICAL_ERROR, 223 NOT_ATTEMPTED | Coverage 94,047302684%; bốn shard/S2 gốc đã khép archive và saved score ngày 25/10 | Run V4 vẫn PARTIAL; không phải raw PASS hoặc đủ 3.763 kết quả |
| Cùng 3.539 ID: Q2.5/IVL3/Q3 AUROC = 0,8243818245861219 / 0,88286846475117 / 0,9527927338600111 | So sánh ghép đúng ảnh; Q3 cao hơn ở mức gộp quan sát được | Chưa có CI theo nguồn, chưa xác lập ưu thế thống kê/kiến trúc |
| Qwen3 Recovery224: 224 SUCCESS, 49 Anomaly/175 Normal | Bằng chứng bổ sung riêng với cấu hình/cohort riêng | Không ghép V4, không lấy trung bình AUROC hai cohort |
| Moondream2: chưa có HNLO TRAIN tương thích đã audit | Một khoảng trống kỹ thuật/bằng chứng phải báo cáo | Không tự bỏ model, đổi endpoint hoặc gọi CPU token test là kết quả TRAIN |
| Exact weighting (giảm trọng số ảnh trùng) làm Q2.5/IVL3 AUROC đổi 0,826656→0,825397 / 0,886182→0,885748 | Có thể lượng hóa độ nhạy hồi cứu | Không chứng minh leakage đã hết hoặc nguồn độc lập |

Receipt xác nhận `raw_audit_performed=false`, `source_identity_verified=false`, `ci_computed=false`. Cả 40 biến thể độ nhạy đã có vẫn **PROPOSED_EXPLORATORY**. Thứ hạng không đảo cũng là kết quả khoa học hợp lệ; không chọn nhóm vì làm AUROC giảm mạnh.

### 2.2. Dataset, nhãn và sửa nhận định audit

Giữ InspecSafe-V1, năm miền, Level01–Level04; Level01 nguy hiểm nhất, Level04 Normal. TRAIN có **3.763 ảnh, 749 Anomaly/3.014 Normal**, support bốn mức **490/251/8/3.014**. Anomaly = Level01–03 là ánh xạ đã có, không là relabel mới. TEST 1.250 ảnh chỉ được nhắc từ báo cáo lịch sử; không mở TEST.

| Miền TRAIN theo thư mục | Anomaly | Normal | Tổng |
| --- | ---: | ---: | ---: |
| coal_conveyor | 172 | 650 | 822 |
| metallurgy | 9 | 534 | 543 |
| oil_chemical | 287 | 491 | 778 |
| power | 81 | 575 | 656 |
| tunnel | 200 | 764 | 964 |
| Tổng | 749 | 3.014 | 3.763 |

Đối chiếu trực tiếp [audit phân bố gốc §4](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/distribution_imbalance_audit.md). Các số oil_chemical 116/662, power 237/419 và tunnel 215/749 trong audit Antigravity là sai; tổng khớp không xác nhận từng ô. Bảng đúng vốn đã có trong PR #132, không sửa bảng đó.

Chưa có map sample→site/video/camera/session đáng tin cho toàn cohort. Có 44 cặp exact TRAIN; point/family không là nguồn thật. Cổng khả thi phát hiện **0/7 cặp ID** của catalog visual cũ khớp pair table đúng hash: không dùng catalog làm mapping. Giữ phân tích miền theo chính sách D3 của D9R22 và sensitivity mismatch cũ; không đổi 36 mismatch toàn dataset để làm đẹp bảng. Tám Level03 TRAIN và chín Anomaly metallurgy không đủ cho kết luận chắc chắn ở nhóm hiếm. Polygon đối tượng không mặc nhiên là nhãn vùng chứng cứ nguy cơ.

### 2.3. Kết luận phản biện

Kế thừa hậu kiểm: IDEAL đã được liệt kê ở **NeurIPS 2026**, không tiếp tục mô tả venue chưa xác minh; ObjectCore là WACV 2026. PowerXGraph++ có tiền lệ cơ chế yêu cầu bổ sung chứng cứ và định tuyến chuyên gia theo hình học, theo hậu kiểm đọc §3.7; lần truy cập nhà xuất bản trong task này gặp 429 nên không tự nhận đã đọc toàn văn. Không suy mọi cơ chế quan sát mới là bất khả thi. SteelBench báo chênh lệch tới 17 **điểm phần trăm** trong đánh giá nhãn của chính nó, không là sai số mặc định của SafeShift. TRAIN đã phơi nhiễm **vẫn có thể dùng phát triển/học có giám sát sau phê duyệt**; không được giả làm kiểm định xác nhận độc lập.

## 3. Công trình gần và khoảng trống được chọn

Đây là xác minh có mục tiêu đến 25/10/2026, kế thừa khảo sát đã có, không phải khảo sát rộng hoặc chứng nhận “đầu tiên”. Chỉ mở thêm nguồn có thể làm thay đổi lựa chọn phương pháp/đóng góp.

| Công trình và mức tiếp cận | Tiền lệ có liên quan | Hệ quả cho SafeShift |
| --- | --- | --- |
| [InspecSafe, Scientific Data 2026](https://www.nature.com/articles/s41597-026-07796-x); kế thừa hồ sơ dataset/main và PR #132 | Benchmark (bộ đánh giá) ảnh an toàn công nghiệp | Dataset/task và việc dùng VLM không phải đóng góp mới |
| [It Is Not Seeing the Hazard, Tetteh & Fleming, preprint 2026](https://arxiv.org/html/2610.09517v1), đọc §5.1–5.4 và Appendix G | Kiểm soát camera/caption; có cả Qwen2-VL-7B generative scorer (bộ chấm điểm sinh ngôn ngữ) | “Dùng token score thay CLIP” không tạo tính mới. Kết quả mô phỏng không chứng minh HNLO thất bại trên InspecSafe; cần kiểm soát nguồn và endpoint thực |
| [Selective Classification for Deep Neural Networks, NeurIPS 2017](https://papers.nips.cc/paper_files/paper/2017/file/4a8423d5e91fda00bb7e46540e2b0cf1-Paper.pdf), đọc §2–3 | Giữ predictor (bộ dự đoán) và chọn chấp nhận/từ chối; đánh đổi risk–coverage (lỗi–tỷ lệ tự xử lý) | Cơ chế từ chối và ngưỡng confidence đã có. Bảo đảm trong thiết lập i.i.d. không chuyển nguyên sang nguồn phụ thuộc/miền mới |
| [Revisiting Confidence Calibration for Misclassification Detection in VLMs, Huang và cs., ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/file/5393eaf0b723278738788520ec54e4b4-Paper-Conference.pdf), đọc §3–4.3, §5.1/Table 1 | LMN (mạng phụ nhỏ) học nhiệt độ theo mẫu từ logits và embedding của CLIP; giữ dự đoán, tối ưu phát hiện lỗi | Chặn tuyên bố “mạng phụ nhẹ trên VLM cố định là mới”. Phân biệt calibration với xếp hạng lỗi; không tự chuyển định lý CLIP sang token HNLO |
| [ConfBench, Roy và cs., preprint 2026](https://arxiv.org/html/2608.01792v1), đọc §3.1, §4.2 và A.7 | So confidence/token probability; ECARB đo bắt lỗi ở ngân sách kiểm tra cố định | Bắt lỗi tại cùng ngân sách đã có tiền lệ; ngữ cảnh trích xuất tài liệu khác nguy cơ công nghiệp. Không mượn mức ngân sách 30% của paper làm yêu cầu SafeShift |
| [Conformal Risk Control, Angelopoulos và cs., ICLR 2024](https://arxiv.org/html/2208.02814), đọc §1.1–2.1 | Kiểm soát kỳ vọng loss đơn điệu với giả định hoán đổi được | Không chọn conformal làm đóng góp trung tâm; không hứa bảo đảm từng miền dưới dịch chuyển tùy ý |
| [SteelBench](https://arxiv.org/html/2607.05264v1), kế thừa R02 PR #132 và hậu kiểm; [IDEAL/NeurIPS 2026](https://neurips.cc/Downloads/2026), xác minh danh sách; [PowerXGraph++](https://www.mdpi.com/2079-9292/15/18/4117), hậu kiểm/giới hạn truy cập nêu trên | Nhãn công nghiệp cần audit; học tham chiếu và đồ thị chứng cứ có tiền lệ gần | Không dùng nhãn VLM làm chuẩn độc lập; không triển khai P1/P2/P3 chỉ để có tên mô hình mới |

**Khoảng trống thực nghiệm được chọn:** trong các nguồn đã kiểm, chưa có bằng chứng trực tiếp cho thấy **HNLO và bất đồng liên mô hình đem lại giá trị tăng thêm trong việc chuyển đúng các ca false-safe (nguy hiểm bị kết luận bình thường) sang kiểm tra, khi giữ predictor, ngân sách kiểm tra, cohort và quyền dùng nhãn như nhau, đồng thời tách nguồn đánh giá trên ảnh InspecSafe/tập công nghiệp tương thích**. Đây là câu hỏi ứng dụng/phương pháp có thể kiểm chứng, không phải khẳng định toàn bộ văn liệu chưa ai làm. Chỉ đổi dataset hay cộng đặc trưng không đủ để tuyên bố thuật toán mới.

## 4. HNLO: đối tượng kiểm chứng và tín hiệu đầu vào

Với bốn raw label logits `z1…z4` (giá trị trước softmax cho token nhãn) tại **cùng bước quyết định/prefix hợp lệ**:

`s_HNLO = log(exp(z1) + exp(z2) + exp(z3)) - z4`.

Tính bằng log-sum-exp ổn định số. Công thức đối chiếu [anomaly_log_odds](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/safeshift/ls1/evaluate.py) và [native scorer](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/safeshift/pa3/native/native_score.py). Mỗi model phải chứng minh token alignment (căn chỉnh token), prefix, revision và raw/processed distinction; không áp công thức Qwen một cách máy móc cho Moondream2 hoặc nhãn nhiều token.

- **Câu hỏi:** thông tin tương đối giữa ba nhãn nguy hiểm và Normal còn phân biệt ảnh, hoặc nhận diện nhãn sai, khi câu trả lời sinh ra đã mất thông tin hay không?
- **Thông tin thêm:** s là số liên tục, phân biệt được hai ảnh cùng nhãn sinh ra. Nó không tự giải thích vùng nguy cơ hoặc mức độ nghiêm trọng.
- **Bằng chứng hiện tại:** có khả năng xếp hạng Anomaly–Normal trong TRAIN ở cấu hình đã lưu. Chưa chứng minh s phát hiện lỗi, có ngưỡng tốt, bất biến lời nhắc hoặc độc lập với nguồn/nền ảnh.
- **Đại số:** sigmoid(s) bằng tổng xác suất ba nhãn nguy hiểm sau chuẩn hóa trên **bốn token ứng viên**; cùng thứ hạng với `1-p4` trong số học lý tưởng. Đây là biến đổi tương đương, không phải ba thuật toán để đếm thành ba đối chứng độc lập. Không phải xác suất nguy cơ đã hiệu chuẩn, xác suất tai nạn hay xác suất dự đoán đúng.
- **Hạn chế:** phụ thuộc prompt/token/prefix, tokenizer, độ phân giải, precision và nhãn; giá trị tuyệt đối không so trực tiếp giữa model. s lớn có thể là nguy cơ rõ, không đồng nghĩa bất định cao. HNLO không loại được source confounding (nhiễu nguồn).
- **Seminar:** giữ s đã lưu và hợp đồng gốc; so với nhãn, score ordinal (điểm thứ bậc), bất đồng; audit coverage và độ nhạy cách nhóm. Không fit ngưỡng vận hành, không gọi đây là kiểm chứng calibration. Các phân tích HNLO mới chỉ chạy sau duyệt điều chỉnh.
- **Khóa luận:** đưa s vào bộ xếp ưu tiên cùng bất đồng, kiểm giá trị tăng thêm bằng ablation (loại từng thành phần) trên cùng predictor/cohort. Nếu không thêm lợi ích, kết luận HNLO không hữu ích cho endpoint đó; vẫn giữ nó làm đối tượng kiểm chứng và kết quả âm, không che kết quả.

## 5. Phạm vi Seminar đã chọn

### 5.1. Một mục tiêu và ba câu hỏi

**Mục tiêu chính:** tạo một đánh giá hồi cứu có thể tái lập về khoảng cách giữa khả năng phân loại, khả năng xếp hạng HNLO và tín hiệu nhận diện lỗi an toàn, kèm độ nhạy với coverage/ảnh lặp trên TRAIN đã phơi nhiễm. Thành công không phụ thuộc phát minh mô hình, AUROC giảm, bất đồng hữu ích hoặc thứ hạng đảo.

| RQ đề xuất | Phân tích trả lời | Đối chiếu D9R22 và điều chỉnh cần duyệt |
| --- | --- | --- |
| **S-RQ1:** Nhãn sinh ra và HNLO biểu hiện khác nhau thế nào về phân loại/xếp hạng nguy cơ qua năm miền trên cùng ảnh? | Ma trận bốn mức; lỗi nhị phân; HNLO AUROC và đối chứng nhãn cứng/ordinal; coverage và support từng miền | Giữ phần phân loại của D9R22-RQ1. Thêm endpoint HNLO và framing hồi cứu là **đề xuất điều chỉnh**, không coi benchmark D9R22 đã hoàn tất |
| **S-RQ2:** Lỗi nghiêm trọng tập trung ở đâu và kết luận thay đổi thế nào khi xét mẫu thiếu/ảnh trùng/các giả định nhóm? | Level01→Level04; Anomaly→Normal; theo 12 hazard atoms; 7 nhóm A–G chỉ phụ; sensitivity đã có | Giữ D9R22-RQ2 và taxonomy; thêm sensitivity trọng số/coverage cần duyệt. Không cộng các strata chồng lấp thành tổng ảnh |
| **S-RQ3:** Bất đồng liên mô hình và HNLO có liên hệ với các quyết định sai, đặc biệt false-safe, hay chỉ phản ánh thiên lệch nhãn chung? | Tái dùng nhãn: đồng thuận, bất đồng và shared blind spots (điểm mù chung); liên hệ lỗi với s; đường lỗi–coverage mô tả khi có đủ đầu vào | Giữ D9R22-RQ3 về bất đồng từ RQ1/RQ2; bổ sung HNLO làm tín hiệu so sánh cần duyệt. Không thay RQ3 bằng AUROC nguy cơ hoặc tự học ensemble |

D9R22 [JSON tại snapshot bất biến](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/configs/pre_freeze/d9r22_seminar_scope.v1.json) có `APPROVED_PROSPECTIVE_SCOPE`, hợp đồng metric chi tiết còn pending. **Nếu chưa duyệt**, chỉ phần thực nghiệm đúng D9R22 với hợp đồng/quyền tương ứng được thực thi; HNLO và weighting giữ vai trò bằng chứng lịch sử/đề xuất. Không gọi ba RQ tích hợp trên là đã được duyệt. Cần quyết định mới dưới `docs/`, không sửa D9R22/DEC-PA3-011 cũ.

### 5.2. Tập mẫu, model và kết quả thiếu

| Tập phân tích được đề nghị | Mục đích |
| --- | --- |
| Q2.5/IVL3: đủ 3.763 ID TRAIN | Bảng đầy đủ mỗi model và so cặp; 749 A/3.014 N |
| **Tập chính so ba model:** 3.539 SUCCESS V4 gốc | Exact join (ghép đúng ID–nhãn–miền) của Q2.5/IVL3/Q3; 700 A/2.839 N, L01/02/03/04 = 460/232/8/2.839 |
| Planned 3.763 Q3 | Bảng coverage riêng: 224 thiếu = 49 A/175 N; 1 lỗi và 223 chưa chạy. Không che bằng mẫu số 3.539 |
| Recovery224 và cohort cũ 2.822 | Chỉ phụ lục truy vết/sensitivity, tách rõ cấu hình và cohort; không pooling |
| Moondream2 | Giữ trong bảng bốn model, HNLO TRAIN = **N/A — thiếu bằng chứng tương thích**, không ghi 0 hoặc kết quả giả |

Đề nghị giảng viên **duyệt ngoại lệ sản phẩm Seminar**: kết quả định lượng ba model trong bảng bốn model, Moondream2 được báo N/A và hồ sơ kỹ thuật còn thiếu. Đây là ngoại lệ kết quả tối thiểu, không tự xóa model khỏi roster; chưa duyệt thì chưa đủ điều kiện tuyên bố hoàn tất yêu cầu Seminar bốn model. Không đặt Seminar phụ thuộc bắt buộc vào inference mới để lấp model thứ tư. Nếu ngoại lệ bị từ chối, Lead phải cấp nguồn lực/quyền hoàn tất Moondream2; không âm thầm coi thiếu dữ liệu là PASS.

Phân biệt `TECHNICAL_ERROR`, `NOT_ATTEMPTED`, `INVALID` (không parse được nhãn) và thiếu score. Classification giữ INVALID trong support/recall theo hợp đồng; trạng thái không có output phải báo riêng, không giả là nhãn Normal. AUROC chỉ tính trên score hữu hạn đủ điều kiện, luôn kèm N/planned và phân bố phần bị loại. Thiếu score không được nội suy; mọi giao cohort phải công bố membership/checksum và lý do. Tập chung có thể bị selection bias (thiên lệch do mẫu chạy thành công), không đại diện mặc định toàn TRAIN.

Có thể đề xuất cận tốt/xấu cho số bỏ sót trong 49 Anomaly thiếu: cộng từ 0 đến 49 vào FN của phần có dự đoán hợp lệ, chia 749, đồng thời báo INVALID riêng. Đây là **cận hoàn thành giả định**, không là FNR đo được; không gán score cho mẫu thiếu hoặc dùng cận này thay coverage.

### 5.3. Thiết kế đánh giá, đối chứng và giới hạn

1. **Phân loại:** ma trận 4×5 (bốn mức thật, bốn dự đoán + INVALID), support/recall; accuracy chỉ bổ sung. Tách FN Anomaly→Normal, FP Normal→Anomaly và lỗi Level01→Level04, luôn ghi tử/mẫu số. Không gọi tỷ lệ do nhãn sinh ra là FNR/FPR của HNLO chưa có ngưỡng.
2. **Xếp hạng nguy cơ:** HNLO AUROC gộp và từng miền; proposed AP (average precision, độ chính xác trung bình theo đường precision–recall) là bổ sung cần hợp đồng trước tính. Đối chứng bắt buộc: nhãn nhị phân, điểm ordinal `4-level` từ nhãn parse, luôn Normal/luôn Anomaly để thấy mất cân bằng và đánh đổi bỏ sót–báo động. Không gọi baseline luôn Normal an toàn vì accuracy cao.
3. **Tín hiệu lỗi:** giữ predictor của từng model cố định; đánh giá lỗi bốn mức và false-safe riêng. Dùng các họ metric D9R22: joint parse availability, unanimous agreement, pairwise kappa, vote entropy, ordinal disagreement, shared blind spots/error complementarity. Các định nghĩa, ties, nhóm thiếu model và risk–coverage phải được duyệt trước triển khai. Đồng thuận của hai model cùng luôn Anomaly không phải bằng chứng đúng.
4. **Đối chứng liên tục công bằng:** nếu raw summaries đủ và được cấp quyền, so entropy bốn nhãn, top-two margin (chênh hai nhãn đầu), xác suất nhãn đã sinh; không dùng lời tự tin bằng văn bản thay logits. Trước tính phải audit field/định nghĩa. Nếu không có, ghi N/A và chỉ kết luận HNLO khác nhãn cứng/ordinal, không tuyên bố thắng các score liên tục. Không chạy prompt nhị phân mới để lấp đối chứng trong gói tối thiểu.
5. **Nguy cơ/miền:** dùng 12 atoms và 7 nhóm phụ theo nguồn đã duyệt. Bảng mẫu số chỉ được tạo khi map TRAIN hợp lệ đã đối soát; không tự suy hazard từ lời giải thích VLM hoặc tên file. Nếu một map chưa đủ, ghi ô N/A/blocker và giới hạn kết luận; cần Lead chấp nhận giới hạn hoặc cấp quyền hoàn tất map trước đóng Seminar. L01/03/nhóm ít mẫu báo số ca; lớp vắng → metric không xác định, không điền 0/0,5.
6. **Độ nhạy đơn vị:** lấy per-image (theo ảnh) làm mốc mô tả; exact weighting `1/|group|` và hai đại diện exact là sensitivity. Các nhóm point/family/dHash và hợp cạnh giữ là giả định phụ từ gate, không source identity hoặc tập nguồn mới. Kiểm đối chứng chỉ dùng miền/platform bằng thống kê mô tả để thấy confounding; không đưa Level, TXT nhãn hoặc ID chứa nhãn vào feature. Kiểm người/thiết bị chỉ là phần có điều kiện annotation/quyền, không cam kết đã kiểm soát nhân quả.
7. **Bất định:** không dùng bootstrap từng ảnh như CI độc lập nguồn. Chưa đủ nguồn thì báo khoảng biến thiên giữa giả định, bảng số ca và trường hợp không xác định; không gọi đó là CI. Sau khi có map nguồn thật và đủ nhóm mới đề xuất paired cluster bootstrap (lấy mẫu lại cả cụm, ghép các phương pháp cùng cụm), ghi tỷ lệ lượt không tính được. Không dựng p-value để xác nhận thứ hạng hiện tại.

S-RQ3 là phân tích khám phá sau khi đã thấy dữ liệu; đường risk–coverage mô tả không chọn một điểm rồi gọi là ngưỡng vận hành. Các result đã công bố từ V4+Recovery chỉ trích riêng nhãn **REPORTED**, không dùng các số FN/accuracy ghép để lấp bảng chính 3.539 V4 gốc. Việc tái dùng nhãn lịch sử cũng phải kiểm hợp đồng generation/parser; không mặc định run HNLO là benchmark D9R22 production.

### 5.4. Đóng góp và sản phẩm tối thiểu

- Một gói đối soát tái lập: model/run/revision/cohort/status/evidence, exact join và coverage; không nâng saved-score thành raw PASS.
- Bộ bảng/figure phân biệt classification, hazard ranking và error signal; kết luận cho từng S-RQ với số ca, giới hạn và ô chưa xác định. Có sensitivity ảnh trùng và kết quả không đảo thứ hạng.
- Một phân tích lỗi theo miền/nhãn/nguy cơ hợp lệ, gồm điểm mù chung; bất đồng không hữu ích vẫn được báo cáo. Các thành phần N/A phải được Lead chấp nhận minh bạch, không coi câu hỏi đã được chứng minh.
- Báo cáo/slide Seminar với lập luận nối trực tiếp sang giả thuyết lớp kiểm tra của Khóa luận; mã CPU/fixture tổng hợp đủ tái lập phần phân tích được duyệt sau setup.

**Không thuộc Seminar:** học/fine-tune VLM, đề xuất kiến trúc mới, grounding nguy cơ, tạo nhãn mới, truy cập TEST, kiểm định khái quát hóa độc lập, fit ngưỡng triển khai, chứng nhận an toàn, bảo đảm conformal, hoặc tuyên bố hoàn tất bốn model khi chưa có kết quả/ngoại lệ đã duyệt.

## 6. Khóa luận: một phương pháp được chọn và cách bác bỏ

### 6.1. Mục tiêu và cấu trúc phương pháp

**Chốt phát triển một bộ xếp ưu tiên kiểm tra bằng hồi quy logistic có regularization (phạt độ phức tạp), dùng HNLO và bất đồng của các VLM cố định, ưu tiên phát hiện false-safe.** Đây là lớp hậu xử lý học có giám sát nhỏ, không huấn luyện VLM từ đầu, không thay bằng một nhánh kiến trúc P1/P2/P3 nếu kết quả không tốt.

Giữ **Qwen3-VL-8B-Instruct là predictor chính dự kiến**, theo lựa chọn thiết kế từ bằng chứng phát triển đã phơi nhiễm và khả năng sinh cả Anomaly/Normal; đây không là xác nhận Q3 ưu việt. Khóa revision/prompt/parser bằng protocol trước target. Q2.5/InternVL3 cung cấp tín hiệu bổ trợ; Moondream2 vẫn trong roster và bảng đánh giá, chỉ tham gia feature khi đã có endpoint tương thích và được duyệt trước target. Gói phương pháp chính ba model cần Lead duyệt riêng, không suy ra từ ngoại lệ Seminar.

Đơn vị dự đoán vẫn là ảnh. Sau khi predictor sinh nhãn `ŷ`, giữ nguyên `ŷ`; bộ xếp ưu tiên chỉ quyết định ca nào chuyển kiểm tra. Đích học chính `e_FS = 1[y thuộc Level01–03 và ŷ = Level04]`; trường hợp Level01→Level04 là lát cắt nghiêm trọng bắt buộc. Không thay nhãn dataset; e_FS là chỉ báo lỗi có định nghĩa cần duyệt trong protocol mới.

Đầu vào dự kiến gồm: HNLO mỗi model (chuẩn hóa bằng thống kê development riêng từng model); nhãn sinh ra; bất đồng ordinal/vote entropy và bất đồng với predictor chính. Không lấy trung bình raw HNLO giữa model. Chốt danh sách hữu hạn trước đánh giá; không đưa source ID, tên file/Level, nhãn chuẩn hoặc metadata chứa đáp án vào feature. Raw summaries không đủ thì không bịa entropy/margin. Các score bổ sung đủ hợp đồng là đối chứng, không tự mở rộng vector chính vô hạn.

Học logistic trên development có nhãn lỗi; chọn regularization bằng validation theo nhóm nguồn trong development. Dùng trọng số mỗi nguồn tổng bằng nhau nếu map nguồn thật đã được duyệt, chuẩn hóa trong từng fold. Giữ một phiên bản trọng số ảnh làm ablation. Tập calibration riêng dùng xác định ngưỡng/routing contract, không để huấn luyện đầu logistic hoặc chọn feature từ target. Logistic đầu ra là **điểm dự báo lỗi**, chưa được gọi là xác suất đã hiệu chuẩn; calibration là kiểm chứng riêng, không phải tên khác của HNLO.

Chính sách chính là **batch triage** (xếp ưu tiên trong một lô ảnh): dành trước ngân sách xử lý lỗi kỹ thuật, rồi chọn các ca có điểm dự báo e_FS cao nhất trong phần hợp lệ đến số lượng kiểm tra đã chốt. Ties xử lý bằng quy tắc có seed/ID ổn định không dùng nhãn. INVALID/lỗi thiếu tín hiệu không được tự động kết luận Normal. Nếu lỗi kỹ thuật vượt ngân sách, ghi overload (quá tải), dừng tự xử lý các ca đó; không giả đạt cùng coverage. Không mặc định người kiểm tra sửa đúng mọi ca.

Đích chính dùng thứ hạng nên không cần giả định score là xác suất calibrated; chọn top-k trên một batch target chỉ dùng score, không dùng nhãn target. Phần calibration/ngưỡng tuyệt đối là đánh giá phụ nếu được duyệt cho cách xử lý từng ảnh; khóa ngưỡng bằng calibration riêng rồi báo coverage thực tế trên target, không ép nó bằng ngân sách mong muốn. Biến đổi đơn điệu không tạo cải thiện thứ hạng cho phép so chính.

### 6.2. Thành phần kế thừa và đóng góp dự kiến

| Thành phần | Tính chất |
| --- | --- |
| Frozen VLM, HNLO/log-odds, entropy/bất đồng, logistic, regularization, weighting nguồn, từ chối dự đoán | Kỹ thuật đã có; không nhận là phát minh |
| Gói lỗi bất đối xứng, tín hiệu HNLO+bất đồng, điều kiện thiếu output và đánh giá cùng predictor/ngân sách/nguồn | Thiết kế cụ thể cho SafeShift cần kiểm chứng; kết hợp đơn thuần chưa xác lập tính mới phương pháp |
| Đo giá trị tăng thêm HNLO và bất đồng trên nguồn tách biệt; đo độ bền trước thiếu model/đổi miền; công bố ablation và thất bại | Đóng góp thực nghiệm dự kiến của Khóa luận, dù không thắng baseline |
| Thuật toán/định lý mới hoặc bảo đảm an toàn | Không thuộc cam kết; không cần để hoàn thành Seminar hay gói Khóa luận thực nghiệm được duyệt |

### 6.3. Giả thuyết, đối chứng, ablation

**Giả thuyết chính H-T:** tại cùng predictor, tập ảnh và ngân sách kiểm tra `b`, lớp HNLO+bất đồng bắt được nhiều false-safe hơn đối chứng đơn tín hiệu mạnh nhất được chọn trên development, và lợi ích còn tồn tại ở cohort đánh giá tách nguồn. Không suy H-T từ AUROC Anomaly–Normal hiện có.

Đối chứng bắt buộc, dùng cùng các đầu ra/cùng quyền nhãn và cùng số ca được chuyển:

1. Không chuyển kiểm tra và chuyển tất cả: hai mốc biên, không ứng viên thắng ngân sách.
2. Chọn ngẫu nhiên với seed, và chọn ngẫu nhiên trong các ca predictor kết luận Level04; đối chứng thứ hai ngăn “thắng” chỉ vì biết nhãn Normal.
3. HNLO của predictor chính xếp ca Level04; entropy/margin bốn nhãn và confidence nhãn đã sinh nếu hợp đồng capture cho phép. Calibration đơn điệu của cùng score không được đếm là tín hiệu xếp hạng mới.
4. Bất đồng/vote entropy/ordinal giữa các model, cùng quy tắc ưu tiên Level04; khóa chính xác định nghĩa trước run.
5. Logistic cùng nhãn huấn luyện chỉ dùng nhãn sinh ra/bất đồng; logistic HNLO-only; logistic tất cả signal theo trọng số ảnh thông thường. Đây là đối chứng học nhỏ trực tiếp, cùng search budget (ngân sách chọn siêu tham số).

LMN ICLR 2026 là công trình phương pháp gần cần đối chiếu §4.3: nó cần embedding/logits CLIP, không tương đương lấy token score từ Qwen. Đề xuất một đối chứng tái triển khai LMN thích nghi **chỉ sau** khi kiểm đủ input/hợp đồng và cùng supervision; nếu không khả thi, báo N/A và không tuyên bố vượt LMN. SelectiveNet/VL-Calibration thay quá trình học predictor nên không thay thế các đối chứng cố định predictor; chúng là tiền lệ, không bắt buộc huấn luyện lớn cho đủ tên paper.

**Ablation bắt buộc:** bỏ HNLO; bỏ bất đồng liên model; chỉ dùng Q3; bỏ source weighting; thay mục tiêu false-safe bằng lỗi phân loại bất kỳ với cùng feature/ngân sách. So sánh này tách lợi ích tín hiệu, chi phí thêm model, ảnh lặp và mục tiêu lỗi bất đối xứng. Phép đảo score/ngẫu nhiên là sanity check, không là baseline mạnh. Không chọn ablation có lợi để báo riêng.

### 6.4. Dữ liệu và đánh giá xác nhận

- TRAIN hiện hữu dùng phát triển sau quyền; chia nội bộ theo nhóm để giảm rò rỉ nhưng vẫn ghi **đã phơi nhiễm**. Không gọi leave-one-domain-out trên TRAIN là kiểm định độc lập; không đổi split chính thức.
- Trước xác nhận cần cohort công nghiệp mới được phép dùng, tương thích nhãn/định nghĩa nguy cơ và **tách nguồn khỏi development/calibration**, có người giữ kín target. Dữ liệu mới là manifest nghiên cứu riêng sau duyệt, không thay InspecSafe-V1. Không mặc định SteelBench/MVTec/VisA tương thích, không mở TEST để giải bài toán thiếu dữ liệu.
- Xác minh site/video/camera/session và nhóm trùng trước chia; nhiều frame một nguồn không tăng số nguồn độc lập. Năm miền không đồng nghĩa năm site. Cần đủ nguồn và đủ ca lỗi dương để ước lượng chênh lệch; kiểm kê/pilot development quyết định precision/power, không bịa N bảo đảm.
- Nhãn bởi người đủ chuyên môn, chưa thấy gợi ý VLM khi tạo chuẩn; kiểm bất đồng/adjudication và quyền sử dụng. Không dùng mô tả sinh làm nhãn thật. Không bắt buộc thêm nhãn vùng vì phương pháp này không grounding. Muốn claim “HNLO đo nguy cơ thay vì nguồn” phải có thêm tương phản hazard–normal trong cùng nguồn/bối cảnh; đây không là claim tối thiểu của triage.
- Fit/model selection/calibration/target phải khác vai trò; toàn bộ normalization, feature, baseline chính, `b`, effect tối thiểu có ý nghĩa `δ`, confidence level, nhóm và quy tắc dừng được Lead duyệt trước target. Không điều chỉnh khi thấy target xấu. Nhóm source chưa đủ → chỉ hồi cứu, không kết luận chuyển giao.
- Mọi phương pháp chạy trên cùng ảnh và output frozen. Chi phí toàn bộ các VLM bổ trợ phải tính vào latency/VRAM/số call, không chỉ báo thời gian logistic. Sequential inference (chạy lần lượt rồi cache) giúp giảm VRAM đồng thời nhưng không xóa chi phí gọi model; pilot mới quyết định khả thi.

### 6.5. Phép đo thành công và khả năng bác bỏ

Đề xuất metric sau phải được duyệt, không thay metric lịch sử. Với `d_i=1` khi chuyển người, `e_i` là false-safe và `a_i` là Anomaly thật:

- **Chính:** `capture_FS = Σ d_i e_i / Σ e_i` tại ngân sách `b`; so chênh lệch ghép với baseline được khóa. Mẫu số bằng 0 → không xác định, không 100%.
- **Bắt buộc kèm:** số false-safe chưa chuyển `Σ(1-d_i)e_i`, chia cả tổng Anomaly `Σa_i` và báo số tuyệt đối; Level01→Level04 riêng. Đây là lỗi còn lại trong phần tự xử lý, **không** là số ca người đã sửa.
- **Workload/coverage:** số được chuyển/tất cả planned; số có quyết định tự xử lý/tất cả planned; coverage kỹ thuật riêng với coverage do từ chối. Kèm báo động giả, tổng lỗi trong phần được chấp nhận, nhóm bị loại và overload.
- **Phụ:** đường risk–coverage, error-detection AUROC/AP (positive = lỗi, khác AUROC hazard), từng miền/nguồn có support, chi phí. Brier/reliability plot chỉ cho score dự báo đúng target được định nghĩa; không dùng sigmoid(HNLO) để tuyên bố calibration.

Estimand (đại lượng muốn ước lượng) chính đề xuất là tỷ lệ capture gộp ảnh trên cohort target được khóa, CI bằng ghép/lấy mẫu lại nguồn khi đủ nhóm; báo thêm theo từng nguồn và trung bình các nguồn đủ lỗi, kèm số nguồn bị undefined. Không gọi trung bình có điều kiện đó là hiệu năng mọi nguồn. Nếu không có đủ nhóm, báo khoảng bất định không đáng tin/không ước lượng, không chuyển sang CI ảnh để có số đẹp. Chỉ một tương phản chính xác nhận; phần khác là thứ cấp/thăm dò, điều chỉnh đa so sánh nếu dùng kiểm định.

**Ủng hộ H-T:** chênh capture có cận dưới CI vượt `δ` được duyệt, cùng ngân sách; không vượt giới hạn workload/chi phí và mức suy giảm nhóm được định trước. **Bác bỏ lợi ích tối thiểu có ý nghĩa:** cận trên chênh lệch dưới `δ`; nếu cận trên ≤0 thì không có bằng chứng lợi ích dương trong độ chính xác thiết kế. CI còn phủ `δ` → chưa đủ bằng chứng, không gọi tương đương. Nếu bỏ HNLO/bất đồng không giảm hiệu quả với độ chính xác đủ, bác bỏ đóng góp tăng thêm của thành phần đó. Lợi ích chỉ xuất hiện khi trộn nguồn, tăng review budget hoặc tăng call budget ngoài giới hạn không đạt H-T.

**Đầu ra tối thiểu Khóa luận khi cải tiến không thắng:** phương pháp đặc tả và implementation có test, bộ đối chứng/ablation công bằng, kết quả âm hoặc chưa kết luận có CI/support hợp lệ, hồ sơ nguồn và đánh giá giữ kín, phân tích chi phí/lỗi, báo cáo tái lập. Nếu không đạt gate dữ liệu độc lập, vẫn bàn giao được phương pháp và kiểm nghiệm phát triển minh bạch, nhưng **phần xác nhận còn chưa hoàn thành**; giảng viên phải duyệt mức kết quả hồi cứu này có đủ chuẩn Khóa luận hay không. Không đổi tên TRAIN để đạt gate, không cần đổi sang đề tài khác để che hạn chế.

## 7. Ranh giới phê duyệt và quyết định loại khỏi phạm vi

Trình một gói thống nhất: tên đề tài/trục hai học kỳ; ba S-RQ tích hợp HNLO; estimand và sensitivity; ngoại lệ sản phẩm Seminar cho Moondream2; map hazard/ô N/A; phương pháp triage Khóa luận và điều kiện dữ liệu. Sau chấp thuận, ghi quyết định mới **append-only** (chỉ bổ sung) dưới `docs/` theo AGENTS main. DEC-PA3-011 vẫn PROPOSED đến khi có quyết định mới; merge tài liệu không tự là protocol freeze hoặc execution grant.

Quyền thực thi cần tách rõ artifact/CPU reanalysis, raw replay, ảnh/annotation, inference GPU và target; grant lịch sử không chuyển sang main mới. Review trực tiếp của ChatGPT → audit Antigravity sau đó → xử lý findings → quy trình chấp thuận/merge → quyết định khoa học → nhiệm vụ kế hoạch kỹ thuật/setup riêng. Task hiện tại dừng ở Draft PR, không khởi động các bước sau.

**Không tiếp tục trong lộ trình này:** P1 đồ thị quan sát/quan hệ (thiếu nhãn, tiền lệ gần); P2 residual/reference mới (IDEAL/InCTRL đã gần); P3 crop chủ động (thiếu nhãn chứng cứ/ngân sách đối chứng); grounding hazard đầy đủ; fine-tune VLM nhiều tỷ tham số; ensemble làm model thứ năm; chứng minh causal hazard validity toàn diện; lý thuyết conformal mới. Audit phụ thuộc nguồn từ hướng C trở thành kiểm tra hợp lệ chung; ý tưởng A về kiểm chứng điểm trở thành ranh giới/đối chứng, không chạy A/B/C như các dự án song song. Chỉ mở lại mục đã loại bằng quyết định mới nêu bằng chứng thay đổi, không vì thấy tên paper mới.

## 8. Tự kiểm theo tiêu chí lựa chọn

| Tiêu chí | Đánh giá quyết định |
| --- | --- |
| Seminar hiện tại | Kế thừa đủ ba lõi D9R22; điều chỉnh HNLO/ngoại lệ được trình công khai, chưa có hiệu lực |
| Bằng chứng SafeShift | Tận dụng đầy đủ nhãn, 3.763/3.539 mẫu hợp lệ và audit/sensitivity đã có |
| Vai trò HNLO | Đối tượng kiểm định Seminar, feature có thể bị bác bỏ ở Khóa luận |
| Câu hỏi kiểm chứng | S-RQ1–3 và H-T có đầu ra, đối chứng, điều kiện bác bỏ |
| Khả thi Seminar | CPU và dữ liệu đã lưu là đủ cho gói hồi cứu sau duyệt; không phụ thuộc phát minh/inference mới |
| Tiếp nối Khóa luận | Chuyển từ nhận diện tín hiệu lỗi sang lựa chọn kiểm tra tại cùng ngân sách |
| Không lệ thuộc novelty | Không nhận thuật toán mới; đóng góp thực nghiệm âm vẫn có giá trị |
| Đánh giá công bằng | Cùng predictor/cohort/nhãn/ngân sách; tách recovery, thiếu output và nguồn |
| Tài nguyên | Học đầu nhỏ, cache frozen output; GPU/cost chỉ chốt sau pilot được cấp quyền |
| Dữ liệu/thẩm quyền | TRAIN không thành holdout; TEST đóng; xác nhận Khóa luận phụ thuộc nguồn mới, không chặn gói Seminar hồi cứu |

**Chốt lựa chọn nghiên cứu: YES. Quyền triển khai: NOT_GRANTED_BY_THIS_DOCUMENT.** Điều chưa chắc là dữ liệu/độ mạnh kết quả Khóa luận, không phải đề tài sẽ làm.

## 9. Ghi công quy trình và giới hạn xác minh

Đã đọc trực tiếp [codex-research SKILL.md](https://github.com/LIU-31415/codex-research/blob/main/SKILL.md), [scientific-brainstorming](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-brainstorming/SKILL.md), [scientific-critical-thinking](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-critical-thinking/SKILL.md), [experimental-design](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/experimental-design/SKILL.md). Áp dụng tách bằng chứng/giả thuyết, tìm tiền lệ phản bác, phân biệt đơn vị ảnh/nguồn, khóa đối chứng và tiêu chí bác bỏ. Không cài skill, chạy script ngoài hoặc tạo dịch vụ. Hướng dẫn skill là nguồn quy trình, không chứng minh đề tài đúng.

Ghi công: Timothy Kassis, Vinayak Agarwal, Yuhuan He, Darshil Patel, Aubrey M. Brueckner (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://arxiv.org/abs/2609.00065), preprint; metadata kiểm tra ngày 25/10, record v2 ngày 02/09/2026, không thấy journal reference. Không tuyên bố review hệ thống hoặc tính mới toàn cục. Nguồn literature mới quan trọng nhất cho quyết định là LMN ICLR 2026: nó làm thu hẹp đóng góp sang đánh giá lỗi bất đối xứng có kiểm soát, thay vì nhận mạng phụ nhẹ là sáng tạo kiến trúc.

Kiểm tra task này là đối chiếu tài liệu/JSON/code đại số và kiểm diff/liên kết; không tái tính kết quả mô hình, không đọc dataset/raw payload, không chạy GPU/inference/TEST. Những PASS lịch sử nêu trên là bằng chứng kế thừa với đúng phạm vi.
