# W2.5 Model, Prompt & Interface Decision Brief

- **ID ứng viên:** DEC-W2-D8-008 (Candidate Decision Brief — D8)
- **Giai đoạn:** Week 2 — Research Protocol (W2.5) — Methodology Patch 2
- **Ngày audit / cập nhật:** 2026-09-18
- **Trạng thái:** **PROPOSED, NOT APPROVED** (Chờ Project Owner xem xét và phê duyệt; chưa ghi vào `DECISIONS.md`)
- **Phạm vi áp dụng:** Giao thức mô hình, câu lệnh chỉ dẫn (prompt), phân lập quy tắc nhiệm vụ (task policy), kiến trúc lệnh gọi (call architecture), từ điển nguy cơ (hazard vocabulary), giao diện đầu ra (interface), bộ chuyển đổi (adapter), cấu hình suy luận, tường lửa kiểm chuẩn (benchmark firewall), cổng năng lực không gian ngoài benchmark (external spatial capability gate), cơ chế đóng băng giao thức (protocol freeze), và quản lý truy vết nguồn gốc cho Giao thức Tái lập Baseline (P1) và Giao thức Nghiên cứu Chính (P2) của SafeShift Seminar.

---

## 1. Purpose (Mục đích)

Mục đích của báo cáo thẩm định phương pháp luận W2.5 là:
1. **Thiết lập giao thức thực nghiệm chuẩn mực** kết nối các quyết định nền tảng đã khóa từ D1 đến D7 vào kiến trúc thực thi cụ thể của các mô hình Vision-Language Models (VLM).
2. **Thiết lập Tường lửa Bộ kiểm chuẩn (Benchmark Firewall)**: bảo đảm toàn bộ 5.013 ảnh của InspecSafe-V1 được bảo vệ ở chế độ thuần túy đánh giá (EVALUATION-ONLY); giảm thiểu nguy cơ thích nghi benchmark nội sinh (researcher benchmark adaptation) qua việc cấm dùng ảnh benchmark cho thăm dò năng lực, tinh chỉnh prompt hay gỡ lỗi parser có quan sát output.
3. **Phân rã Độc lập giữa Kiến trúc Lệnh gọi và Từ điển Nguy cơ (Orthogonalization of Architecture and Vocabulary)**: tách bạch rõ ràng giữa hai trục quyết định phương pháp luận (Trục A: Call Architecture; Trục B: Hazard Vocabulary), loại bỏ các nhận định đồng nhất hóa sai lệch.
4. **Bảo toàn Định nghĩa Nhiệm vụ Phân loại (Task Policy Specification)**: phân biệt rạch ròi giữa việc công khai Quy tắc Nhiệm vụ An toàn Ngành (*Task Policy Disclosure* — cần thiết để bài toán phân loại có đầy đủ ngữ nghĩa) và việc công khai Từ điển Nguy cơ Định vị (*Grounding Vocabulary Disclosure*), ngăn ngừa nguy cơ phân loại bị thiếu đặc tả (under-specified).
5. **Thiết lập Cổng Năng lực Không gian Ngoài Benchmark (External Spatial Capability Gate)**: phân định rạch ròi giữa năng lực vận hành giao diện cú pháp (*Format Operability*) và năng lực định vị không gian thực chất (*Spatial Localization Capability*); cho phép dùng ảnh bên ngoài có ground truth tọa độ khách quan để kiểm chứng năng lực định vị cho các mô hình Prompt-Only mà không vi phạm Benchmark Firewall.
6. **Khảo sát và kiểm toán độc lập năng lực thực tế** của các họ mô hình VLM ứng viên (OpenAI, Google Gemini, Qwen-VL, Anthropic Claude, Grok, v.v.) dựa trên tài liệu kỹ thuật chính thức cập nhật đến ngày **2026-09-17**, phân định rõ ràng giữa năng lực phân loại an toàn tổng quát và năng lực định vị không gian nguyên bản.
7. **Phân tích chi tiết quy trình tái lập baseline chính thức của InspecSafe-V1 (P1)**: phục hồi chính xác prompt, cấu hình giải mã, đường dẫn API và logic đánh giá văn bản của bài báo gốc (*Scientific Data* 2026); loại bỏ tiêu chí dung sai sai số tùy tiện ($\pm 1–2\%$).
8. **Thiết lập Chính sách Đóng băng Giao thức (Protocol Freeze)** và Kiểm soát Thay đổi Sau Đóng băng (Post-Freeze Change Control) với commit SHA cố định trước khi thực hiện bất kỳ lệnh suy luận nào trên dữ liệu InspecSafe.

---

## 2. Locked Decisions D1-D7 (Các quyết định đã khóa D1–D7)

Mọi đề xuất trong W2.5 phải tuân thủ nghiêm ngặt và không được làm thay đổi hệ thống quyết định đã được Project Owner phê chuẩn:

| Quyết định | Tên quyết định | Nội dung ràng buộc cốt lõi đối với W2.5 |
| :--- | :--- | :--- |
| **DEC-W2-D1-001 (D1)** | Research Framing & Protocol Hierarchy | Bài toán là **Cross-Domain Robustness Evaluation** trên mô hình VLM đóng băng trọng số (*Frozen Pretrained VLMs*), **tuyệt đối không gọi là Domain Generalization**. Phân tầng: **P1** (1.250 mẫu test chính thức tái lập baseline upstream) và **P2** (5.013 mẫu toàn thể đánh giá độ bền xuyên 5 miền). Khung 3 câu hỏi nghiên cứu: RQ1 (Cross-domain & platform confounding), RQ2 (Error concentration across strata), RQ3 (Classification-grounding consistency). |
| **DEC-W2-D2-002 (D2)** | Split, Evaluation Pool & Grouping Policy | **Đơn vị dự đoán (Prediction Unit) là ẢNH (Image)**. Mỗi ảnh suy luận độc lập. Lưu trữ raw model outputs ở cấp độ từng ảnh. `point_id` là tín hiệu gom nhóm Normal cho bootstrap; Anomaly dependence chưa giải quyết. P3 là Candidate Sensitivity Protocol (không phải clean benchmark). |
| **DEC-W2-D3-003 (D3)** | Operational Domain & Mismatch Policy | Nhãn miền chính là `folder_domain`. 36 mẫu mismatch (`folder_domain != text_domain`) được gắn cờ và đánh giá độ nhạy đối chứng theo Dual-Report (Sensitivity A: Exclude, Sensitivity B: Reassign). Miền Luyện kim (`metallurgy`) có $N_{\text{anomaly}}=9$ ở P2 và $N_{\text{anomaly}}=0$ ở P1; số liệu bất thường của metallurgy chỉ mang tính mô tả (`[Sparse-Support / Descriptive-Only]`). Thuật ngữ nền tảng robot: "đồng biến thiên / platform confounding", không phát biểu nhân quả. |
| **DEC-W2-D4-004 (D4)** | Canonical Grounding Output Interface | Biểu diễn không gian chuẩn nội bộ: $\mathbf{b}_{\text{canonical}} = [x_{\min}, y_{\min}, x_{\max}, y_{\max}] \in [0.0, 1.0]$, thứ tự **$x$-first**. Toàn bộ Raw Model Response bắt buộc phải lưu trữ nguyên văn kèm metadata đầy đủ trước khi parse. Bộ chuyển đổi (Adapter) chuyển đổi tất định từ native format. **Capability-Aware Policy B**: Classification chạy trên toàn bộ mô hình; Spatial Grounding chỉ chạy trên mô hình có năng lực định vị được kiểm chứng; mô hình không hỗ trợ xuất tọa độ không bị coi là lỗi grounding và không bị xếp hạng trong grounding benchmark. Không tùy biến prompt ngữ nghĩa riêng. |
| **DEC-W2-D5-005 (D5)** | Metrics & Statistical Evaluation Protocol | Phân loại: Balanced Accuracy + Macro-F1 song hành; Raw Accuracy chỉ dùng mô tả. Sai số trọng yếu: Track A (Binary Anomaly FNR/FPR) và Track B (Level01 OvR: Recall, FNR, Critical Miss Rate, Critical Downgrade Rate). Dual-Layer Support-Aware Policy cho miền thiếu lớp. RQ1 anchor: Class-Conditional Domain Analysis. RQ2: 4 chỉ số trên 7 tầng nguy cơ gom nhóm (cảnh báo số đếm không cộng dồn, 512 mẫu đa nguy cơ). RQ3-A: Mode A (gán ghép liên tục không ngưỡng: Mean IoU, Median IoU) vs Mode B (ghép hai phía phân ngưỡng: Hit@0.25, Hit@0.50, Evidence P/R/F1, CGI@tau). Canonical Pointing Hit trên đa giác gốc. RQ3-B: Identity-Agnostic PLC (Center-in-Proxy primary, Box Containment diagnostic, Single-Person Proxy subset 410 mẫu). Parse failure: tính là IoU = 0.0 trong End-to-End. Loại trừ 60 unsupported atoms khỏi mẫu số không gian. Domain-Stratified Point-Cluster Bootstrap ($B=2.000$, seed=42, 95% Percentile CI). So sánh mô hình bằng Paired Bootstrap Difference CI 95%. Calibration phụ thuộc năng lực, cấm dùng textual confidence. Không phê duyệt Object Hallucination trên toàn bộ dataset. |
| **DEC-W2-D6-006 (D6)** | Hazard Taxonomy & Grounding Census | 12 Hazard Atoms giải thích 100% 1.000 mẫu Anomaly (1.788 atoms). 3 trạng thái hỗ trợ không gian: Direct (781 atoms / 721 mẫu), Weak-Proxy (947 atoms / 608 mẫu, giao thoa 347 mẫu), No-Current-Spatial-GT (60 atoms / 59 mẫu). RQ3 phân rã độc lập RQ3-A và RQ3-B. 7 tầng nguy cơ gom nhóm A–G cho RQ2. Đẳng thức toàn vẹn: $721 + 608 - 347 = 982$; $982 + 18 = 1.000$. |
| **DEC-W2-D7-007 (D7)** | Rationale Annotation Policy | Chọn **D7-A**: Không tạo nhãn rationale mới trong Seminar 8 tuần. Dùng Direct Object-Support và Weak Proxy có sẵn. Không gọi đa giác vật thể là human rationale GT. Không tính Object Hallucination Rate trên full dataset. Bảo lưu D7-C cho Khóa luận tốt nghiệp. |

---

## 3. Benchmark Firewall & Blind Development Rule (Tường lửa Kiểm chuẩn & Quy tắc Phát triển Mù)

Để giảm thiểu nguy cơ thích nghi benchmark do người nghiên cứu (Researcher Benchmark Adaptation) và bảo vệ tính độc lập của quy trình đánh giá SafeShift:

### 3.1. Quy tắc Tường lửa Kiểm chuẩn (Benchmark Firewall Policy)
1. **EVALUATION-ONLY cho Toàn bộ 5.013 Ảnh:** Toàn bộ 5.013 mẫu ảnh của InspecSafe-V1 được xác lập tình trạng phương pháp luận duy nhất là **TẬP ĐÁNH GIÁ THUẦN TÚY (EVALUATION-ONLY)** cho Giao thức P2 (và 1.250 ảnh cho P1).
2. **Các Hành vi Bị Cấm trên Dữ liệu InspecSafe:**
   - **CẤM THĂM DÒ NĂNG LỰC (No Capability Probing):** Không sử dụng bất kỳ ảnh nào trong InspecSafe để thử nghiệm xem mô hình có xuất được bounding box hay không.
   - **CẤM GỠ LỖI CÂU LỆNH (No Prompt Debugging / Engineering):** Không chạy thử prompt trên ảnh InspecSafe rồi điều chỉnh câu từ dựa trên phản hồi của mô hình.
   - **CẤM GỠ LỖI PARSER QUAN SÁT OUTPUT (No Output-Conditioned Parser Debugging):** Không quan sát output của mô hình trên ảnh InspecSafe để viết regex hoặc tinh chỉnh logic bóc tách.
   - **CẤM LỰA CHỌN MÔ HÌNH DỰA TRÊN ĐIỂM (No Output-Driven Model Selection):** Không chạy thử các mô hình trên một vài ảnh InspecSafe để "chọn model cho điểm cao nhất".
   - **CẤM TINH CHỈNH NGƯỠNG (No Threshold Tuning):** Không dùng dữ liệu InspecSafe để điều chỉnh các ngưỡng quyết định (IoU threshold, confidence threshold, detection cutoff).
3. **Tính Hợp lệ của Kiểm toán W1–W2:**
   - Các công việc kiểm toán cấu trúc dữ liệu, metadata, nhãn ground-truth, phát hiện duplicate và cuộc tổng điều tra D6 Census thực hiện ở Week 1 và Week 2 duy trì tính hợp lệ phương pháp luận vì **hoàn toàn không có hành vi nhìn trước kết quả dự đoán của mô hình (no model-output peeking)** được ghi nhận trước khi đóng băng giao thức.
4. **Giới hạn Nhận thức luận của Tường lửa:**
   - Cần ghi nhận rõ ràng: Benchmark Firewall là biện pháp kỷ luật nội sinh giúp giảm thiểu rủi ro tinh chỉnh chủ quan từ phía người nghiên cứu, **nhưng không thể chứng minh sự vắng mặt tuyệt đối của việc nhiễm dữ liệu tiền huấn luyện ngoại sinh (cannot prove absence of pretraining contamination)**, cũng như không thể tuyên bố mọi dạng thức thiên lệch đã bị loại trừ triệt để.

### 3.2. Quy tắc Phát triển Mù (Blind Development Rule)
Khi các kỹ sư và nghiên cứu viên xây dựng mã nguồn (pipeline, parser, adapter) trước khi chạy benchmark:
1. **Kiểm thử Parser & Adapter:** Chỉ được sử dụng:
   - Các phản hồi giả định tự tạo (handcrafted dummy responses / synthetic JSON).
   - Dữ liệu cấu trúc tổng hợp nhân tạo (synthetic payloads).
   - Các ví dụ minh họa chính thức trong tài liệu kỹ thuật của nhà cung cấp (provider documentation examples).
2. **Kiểm thử Pipeline Xử lý Ảnh (Image Pipeline / Preprocessing):**
   - Chỉ được sử dụng các hình ảnh bên ngoài (external images) có giấy phép công cộng rõ ràng hoặc ảnh tổng hợp.
   - Tuyệt đối không nạp ảnh InspecSafe vào các script kiểm thử tạm thời.

---

## 4. Freeze Policy & Change Control (Chính sách Đóng băng và Kiểm soát Thay đổi)

### 4.1. Đóng băng Tuyệt đối Trước Lần Chạy Đầu tiên (Protocol Freeze Policy)
**TRƯỚC lần chạy suy luận đầu tiên** trên bất kỳ ảnh InspecSafe nào ở Week 3, toàn bộ các thành phần phương pháp luận sau đây bắt buộc phải được đóng băng hoàn toàn (FROZEN):
1. Danh sách rút gọn mô hình P2 (P2 Model Shortlist) và mã định danh cố định (Pinned Model IDs).
2. Cấu trúc câu lệnh chỉ dẫn chuẩn (Prompt Template & System Instructions).
3. Quy tắc nhiệm vụ phân loại (Task Policy Specification) và Từ điển nguy cơ (Hazard Vocabulary).
4. Cấu trúc đầu ra chuẩn hóa (Output JSON Schema).
5. Quy tắc chuyển đổi tọa độ của bộ điều hợp (Adapter Coordinate Conversion Rules).
6. Cấu hình chế độ suy luận (Reasoning / Thinking Policy).
7. Cấu hình giải mã và lấy mẫu (Decoding & Temperature Parameters).
8. Phân định vai trò mô hình (Model Roles: Classification-Only vs Grounding-Eligible).
9. Logic phân tích cú pháp (Parser Implementation & Fail-Safe Handling).
10. Phiên bản mã nguồn tính toán metric (Metric Engine Version).

*Thủ tục ghi nhận bắt buộc:* Ghi lại chính xác mã băm Git commit đóng băng giao thức (**`protocol_freeze_commit_sha`**) vào tài liệu dự án trước khi thực thi bất kỳ lệnh gọi API benchmark nào.

### 4.2. Kiểm soát Thay đổi Sau Đóng băng (Post-Freeze Change Control)
Sau khi đã khởi chạy bất kỳ mô hình nào trên dữ liệu InspecSafe:
1. **NGHIÊM CẤM SỬA PROMPT THEO HIỆU NĂNG:** Tuyệt đối không sửa đổi prompt, không bổ sung ví dụ, không chỉnh sửa hướng dẫn dựa trên:
   - Điểm số cao/thấp quan sát được.
   - Mô hình phân loại sai ở một số mẫu.
   - Suy giảm hiệu năng ở một miền công nghiệp cụ thể.
   - Mô hình trượt bounding box (grounding misses).
2. **Quy trình Xử lý Sự cố Kỹ thuật (Parser Bug / API Incompatibility / Malformed Schema):**
   Nếu phát hiện lỗi lập trình khách quan (như parser bị vỡ do API đổi định dạng bao bọc, hoặc adapter tính sai tỷ lệ ảnh):
   - **Bước 1:** Lập biên bản sự cố, ghi nhận chi tiết nguyên nhân kỹ thuật khách quan và commit hash bị ảnh hưởng.
   - **Bước 2:** Nâng phiên bản giao thức (Bump Protocol Version, ví dụ `P2.0` $\rightarrow$ `P2.1`).
   - **Bước 3:** **TUYỆT ĐỐI KHÔNG SỬA RIÊNG CHO MỘT MÔ HÌNH YẾU**. Không được có hành vi "thấy mô hình A lỗi cú pháp nên thêm prompt riêng cho mô hình A".
   - **Bước 4:** **CHẠY LẠI TOÀN BỘ (FULL RERUN)** toàn bộ các mô hình bị ảnh hưởng trên toàn bộ tập mẫu đánh giá liên quan, bảo đảm tính so sánh công bằng trên cùng một phiên bản giao thức đã sửa.

---

## 5. Model Selection Policy (Chính sách Lựa chọn Mô hình Nghiên cứu)

Để bảo đảm tính khách quan khoa học, các mô hình tham gia SafeShift được lựa chọn dựa trên 6 nguyên tắc phương pháp luận:

1. **Tài liệu Chính thức (Official Documentation):** Có tài liệu kỹ thuật công khai xác nhận khả năng tiếp nhận ảnh và giao diện tương tác.
2. **Tính Khả dụng và Truy cập (Accessibility):** Có thể truy cập thông qua API thương mại hoặc hạ tầng điện toán đám mây ổn định.
3. **Tính Khả thi về Chi phí (Cost Feasibility):** Chi phí thực thi trên 5.013 mẫu nằm trong ngân sách nghiên cứu cho phép của Seminar.
4. **Tính Đa dạng Kiến trúc và Nhà cung cấp (Provider & Architecture Diversity):** Bao gồm cả mô hình thương mại đóng (Closed API) và mô hình mở (Open-weight); bao gồm các gia đình công nghệ khác nhau (Google, Alibaba, OpenAI, Anthropic).
5. **Khả năng Tái lập và Cố định Phiên bản (Reproducibility & Pinning):** Hỗ trợ dated model snapshots hoặc commit hash bất biến.
6. **Bằng chứng Năng lực Định vị Không gian (Localization Evidence):** Có bằng chứng tài liệu (Level 1) hoặc kiểm chứng vi mô trên ảnh ngoài có ground truth tọa độ (Level 2A).

### Nguyên tắc Cấm Tuyệt đối:
- **TUYỆT ĐỐI KHÔNG CHỌN MÔ HÌNH DỰA TRÊN HIỆU NĂNG TRÊN INSPECSAFE:** Không thử nghiệm để chọn ra mô hình "đạt điểm cao nhất".
- **Sử dụng Kết quả Bài báo Gốc:** Các mô hình đã xuất hiện trong bài báo InspecSafe 2026 (như Claude Opus 4.5, Grok 4.1 Fast) chỉ được xem xét như **Mốc tham chiếu lịch sử (Historical Reference)** để phục vụ tái lập P1. Bảng xếp hạng trong bài báo gốc không được dùng để khẳng định trước "mô hình chiến thắng" trong SafeShift.

---

## 6. Upstream Baseline Audit (Kiểm toán Baseline Nghiên cứu Gốc)

Dựa trên việc kiểm tra trực tiếp mã nguồn phát hành chính thức của InspecSafe-V1 tại `data/raw/InspecSafe-V1/` và kho lưu trữ GitHub `liuzy0708/InspecSafe`:

### 6.1. Phân tích Script Sinh Kết quả (`model_api_generate_results.py`)
- **Provider & Tuyến API:**
  - Script sử dụng `BASE_URL = "https://www.dmxapi.cn/"` và `API_ENDPOINT = BASE_URL + "v1/chat/completions"`. Đây là một dịch vụ tổng hợp API proxy bên thứ ba tại Trung Quốc, sử dụng giao diện tương thích hoàn toàn với OpenAI Chat Completions API.
- **Model Name được hard-code:**
  - `MODEL_NAME = "claude-opus-4-5-20251101"`.
  - Đây là một dated snapshot của Anthropic Claude Opus (hoặc tên định danh ánh xạ nội bộ của proxy DMX). Tên định danh `claude-opus-4-5-20251101` phản ánh cấu hình thực nghiệm tại thời điểm nhóm tác giả thu thập số liệu (cuối năm 2025).
- **Cấu hình giải mã (Decoding settings):**
  - `temperature = 0.1`.
  - `timeout = 60` giây.
  - Không thiết lập `top_p`, `seed` hay `max_tokens` rõ ràng trong payload.
- **Quy trình đóng gói đầu vào:**
  - Ảnh cục bộ được mã hóa Base64 chuỗi văn bản UTF-8: `data:image/png;base64,{image_data}`.
  - Payload gửi ảnh trong trường `image_url` chuẩn OpenAI format cùng với nội dung prompt văn bản trong một user message đơn lẻ.
- **Đầu ra thô và lưu trữ:**
  - Toàn bộ nội dung chuỗi văn bản của `choices[0].message.content` được lưu nguyên văn vào tệp văn bản riêng biệt: `{OUTPUT_DIR}/{img_name}.txt`.
  - Mỗi ảnh tương ứng 1 tệp `.txt`.

### 6.2. Phân tích Script Đánh giá Tương đồng Văn bản (`model_benchmark_evaluation.py`)
- **Mô hình nhúng (Embedding Model):**
  - Sử dụng mô hình `bge-m3` (BAAI/bge-m3) chạy cục bộ thông qua máy chủ Ollama: `http://localhost:11434/api/embeddings`.
- **Model đối chiếu được cấu hình sẵn trong script:**
  - `MODEL_NAME = "grok-4.1-fast"`. Chứng minh tác giả đã chạy nhiều mô hình VLM khác nhau.
- **Quy trình tính toán:**
  - Đọc nội dung tệp `.txt` sinh bởi mô hình và tệp chú thích `.txt` chuẩn trong `test/Annotations/`.
  - Gọi Ollama embedding endpoint để lấy vector nhúng 1024 chiều.
  - Tính toán độ tương đồng Cosine: $\text{CosineSim}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2}$.

### 6.3. Phân tích Script Phân loại và Ma trận Nhầm lẫn (`model_confusion_matrix.py`)
- **Tập nhãn phân loại:**
  - `classes = ["level one", "level two", "level three", "no abnormalities observed", "unrecognizable"]`.
  - Gắn nhãn hiển thị: `["level Ⅰ", "level Ⅱ", "level Ⅲ", "level Ⅳ", "unrecognizable"]`.
- **Logic phân tích cú pháp (Parsing Regex / Logic):**
  - Script lấy dòng cuối cùng của tệp: `last_line = lines[-1].strip()`.
  - Tách từ cuối cùng và ánh xạ từ khóa về nhãn chuẩn qua từ điển (`"observed"` $\rightarrow$ `"no abnormalities observed"`, `"one"` $\rightarrow$ `"level one"`, v.v.). Nếu không khớp, mặc định gán vào `"unrecognizable"`.
- **Đặc điểm Ground Truth đối chiếu:**
  - Ground truth thực tế chỉ gồm 4 lớp chuẩn: Level one, Level two, Level three, no abnormalities observed. Lớp `"unrecognizable"` thuần túy là cột lỗi dự đoán của mô hình.

### 6.4. Bằng chứng Trọng yếu về Bám Bằng chứng Không gian (Grounding)
- **Kiểm toán khẳng định:** Trong toàn bộ 3 script phát hành chính thức, cũng như trong các phụ lục và bảng kết quả của bài báo InspecSafe, **HOÀN TOÀN KHÔNG CÓ BẤT KỲ PROMPT, CODE, HAY BASELINE NÀO DÀNH CHO NHIỆM VỤ GROUNDING / LOCALIZATION**.
- Toàn bộ kết quả công bố của bài báo gốc thuần túy là:
  1. *Safety Accuracy* (Phân loại 4 cấp độ an toàn).
  2. *BGE-M3 Text Similarity* (Độ tương đồng ngữ nghĩa văn bản miêu tả hiện trường).
- Do đó, **nhiệm vụ Grounding (RQ3) là đóng góp nghiên cứu mở rộng hoàn toàn độc lập và mới của SafeShift**, kế thừa đúng tinh thần Quyết định D1.

---

## 7. Current Model Landscape (Toàn cảnh Mô hình Hiện hành tính đến 2026-09-17)

Kiểm toán tài liệu kỹ thuật chính thức (Official Documentation Audit) được thực hiện vào ngày **2026-09-17** trên 5 họ mô hình VLM tiêu biểu:

### 7.1. Họ Google Gemini (Google AI / Vertex AI)
- **Tài liệu kiểm toán:** Google Cloud Vertex AI & Google AI Studio official documentation, mục *"Object detection and spatial understanding with Gemini"* và *"Structured Outputs guide"*.
- **Đặc điểm năng lực:**
  - Hỗ trợ chính thức khả năng **Object Detection / 2D Spatial Grounding** dạng nguyên bản (Native Capability, **LEVEL 1 — DOC-VERIFIED SPATIAL CAPABILITY**).
  - Quy chuẩn tọa độ hộp bao của Google: $\mathbf{b}_{\text{gemini}} = [y_{\min}, x_{\min}, y_{\max}, x_{\max}]$, tọa độ chuẩn hóa nguyên trong thang đo $[0, 1000]$.
  - Hỗ trợ `response_schema` và `response_mime_type: "application/json"` tuân thủ chuẩn JSON Schema.
  - Cung cấp định danh cố định (Flash tối ưu chi phí, Pro tối ưu suy luận sâu).

### 7.2. Họ Qwen-VL (Alibaba Cloud / Open-Weight Community)
- **Tài liệu kiểm toán:** Qwen official GitHub repository (`QwenLM/Qwen2.5-VL` / `Qwen3-VL`), Model Cards trên Hugging Face, và tài liệu Alibaba Cloud DashScope API.
- **Đặc điểm năng lực:**
  - Mô hình mã nguồn mở trọng số công khai (Open-weight), phát hành dưới giấy phép học thuật (Apache 2.0 / Qwen License).
  - Kiến trúc tích hợp bộ mã hóa thị giác hỗ trợ định vị không gian 2D nguyên bản (**LEVEL 1 — DOC-VERIFIED SPATIAL CAPABILITY**).
  - Quy chuẩn tọa độ: Hỗ trợ sinh token định vị tọa độ hoặc xuất cấu trúc JSON với tọa độ chuẩn hóa $[0, 1000]$.
  - Khả dụng qua Hosted API chính thức (Alibaba Cloud DashScope, OpenRouter) do hạn chế VRAM cục bộ.

### 7.3. Họ OpenAI Multimodal (OpenAI API)
- **Tài liệu kiểm toán:** OpenAI official documentation, mục *"Vision / Images"*, *"Structured Outputs"*, và *"Model lifecycle / snapshots"*.
- **Đặc điểm năng lực:**
  - Tiếp nhận đầu vào đa phương thức chất lượng cao; phân loại an toàn xuất sắc (**LEVEL 1 — DOC-VERIFIED** cho Classification).
  - Hỗ trợ cơ chế **Structured Outputs** nghiêm ngặt (`response_format: {"type": "json_schema", "strict": true}`).
  - **Tình trạng định vị không gian (Spatial Grounding):** Tài liệu chính thức **KHÔNG** công bố hợp đồng API định vị đối tượng nguyên bản. Mô hình chỉ xuất tọa độ khi được yêu cầu thông qua câu lệnh văn bản (**LEVEL 3 — PROMPT-ONLY / UNVERIFIED SPATIAL**). Bắt buộc phải qua External Spatial Capability Probe (Mục 28) để xác minh năng lực thực tế.

### 7.4. Họ Anthropic Claude (Anthropic API)
- **Tài liệu kiểm toán:** Anthropic official documentation, mục *"Vision capabilities"*, *"Extended Thinking"*, và *"Model retirement / release dates"*.
- **Đặc điểm năng lực:**
  - Là họ mô hình được sử dụng trong script phát hành chính thức của InspecSafe (`claude-opus-4-5-20251101`).
  - Phân loại và lập luận ngữ cảnh phức tạp (**LEVEL 1 — DOC-VERIFIED** cho Classification).
  - Hỗ trợ Tool Use (Function Calling) để trích xuất JSON.
  - **Tình trạng định vị không gian (Spatial Grounding):** Không công bố hợp đồng định vị bounding box chính thức (**LEVEL 3 — PROMPT-ONLY / UNVERIFIED SPATIAL**). Cần External Spatial Capability Probe để xác minh.

### 7.5. Các họ mô hình mở rộng khác (Grok / xAI, InternVL, GLM-V)
- **Grok (xAI):** Xuất hiện trong mã nguồn đánh giá văn bản của bài báo gốc (`grok-4.1-fast`). Hỗ trợ multimodal input qua API tương thích OpenAI. Năng lực định vị ở mức Prompt-only.
- **InternVL / GLM-V:** Mô hình học thuật nguồn mở có khả năng định vị tọa độ tốt, nhưng đòi hỏi tài nguyên tính toán lớn khi tự host hoặc qua các cổng API khu vực.

---

## 8. Capability Evidence Levels & Grounding Gate (Phân tầng Bằng chứng Năng lực & Cổng Tham gia Grounding)

Để bảo đảm tính nghiêm ngặt về phương pháp luận và tuân thủ Quyết định D4 (Capability-Aware Policy B), SafeShift phân định 5 cấp độ bằng chứng kỹ thuật:

| Cấp độ Bằng chứng | Định danh | Định nghĩa phương pháp luận | Quyền Tham gia Grounding (RQ3) |
| :--- | :--- | :--- | :--- |
| **LEVEL 1** | **DOC-VERIFIED SPATIAL CAPABILITY** | Năng lực định vị không gian được nhà cung cấp công bố chính thức trong tài liệu kỹ thuật (official API docs, model cards) kèm theo cam kết định dạng, hợp đồng API và ví dụ chuẩn. | **ĐỦ ĐIỀU KIỆN (ELIGIBLE)** trực tiếp. Không bắt buộc phải qua empirical probe. |
| **LEVEL 2A** | **EXTERNAL SPATIAL-PROBE VERIFIED** | Năng lực định vị không gian thực chất được nhóm nghiên cứu kiểm chứng thực nghiệm độc lập trên **ảnh bên ngoài benchmark có ground truth tọa độ khách quan** (External Spatial Probe), chứng minh mô hình thực sự định vị đúng vị trí vật thể. | **ĐỦ ĐIỀU KIỆN (ELIGIBLE)**. (Không được tự ý nâng cấp thành DOC-VERIFIED). |
| **LEVEL 2B** | **FORMAT-OPERABILITY VERIFIED ONLY** | Mô hình chỉ mới được kiểm chứng là có khả năng xuất định dạng JSON và tọa độ số hợp lệ về mặt cú pháp trên ảnh kiểm thử, nhưng **chưa chứng minh được độ chính xác không gian thực chất** (hộp bao có thể đặt sai vị trí hoặc ngẫu nhiên). | **KHÔNG ĐỦ ĐIỀU KIỆN (NOT ELIGIBLE)** cho Grounding track. Chỉ chứng minh tính tương thích của parser/interface. |
| **LEVEL 3** | **PROMPT-ONLY / UNVERIFIED SPATIAL** | Mô hình có thể xuất tọa độ theo hướng dẫn ngữ nghĩa của câu prompt, nhưng chưa có tài liệu cam kết và chưa trải qua External Spatial Probe. | **CHƯA ĐỦ ĐIỀU KIỆN (CONDITIONALLY ELIGIBLE / PROBE-REQUIRED)**. Bắt buộc phải qua probe đạt Level 2A mới được tham gia Grounding. |
| **LEVEL 4** | **INELIGIBLE** | Mô hình thuần văn bản hoặc không có khả năng xuất tọa độ. | **HOÀN TOÀN KHÔNG THAM GIA (INELIGIBLE)**. |

---

## 9. Model Candidate Matrix (Bảng Ma trận Mô hình Ứng viên)

Bảng ma trận tổng hợp đánh giá sơ bộ các ứng viên VLM đại diện theo 10 tiêu chí kỹ thuật:

| Model Family / ID đại diện | Provider | Open / Closed | P1 Repro Role | P2 Class. Status | RQ3-A Direct Grounding | RQ3-B Proxy Grounding | Structured Output | Spatial Capability Level | Calibration Access | Version Pinning | Hardware Local Feas. | Trạng thái tổng quát |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `claude-opus-4-5-20251101` | DMX / Anthropic | Closed API | Primary Reference | ELIGIBLE | UNVERIFIED | UNVERIFIED | Prompted / Tool | LEVEL 3 (Prompt-Only) | INELIGIBLE (No logprobs) | Pinned Snapshot (20251101) | Cloud API Only | **ELIGIBLE (P1) / CONDITIONAL (P2 Grounding)** |
| `claude-3-7-sonnet` / `claude-3-5-sonnet` | Anthropic | Closed API | Alternate Reference | ELIGIBLE | CONDITIONALLY ELIGIBLE | CONDITIONALLY ELIGIBLE | Native Tool Use / Prompted | LEVEL 3 (Prompt-Only) | INELIGIBLE (No logprobs) | Pinned Dated IDs | Cloud API Only | **ELIGIBLE (Class.) / PROBE-REQ (Grounding)** |
| `gemini-2.5-flash` | Google | Closed API | Cross-Model Eval | ELIGIBLE | **ELIGIBLE** | **ELIGIBLE** | Native JSON Schema | **LEVEL 1 (Doc-Verified, [0,1000])** | INELIGIBLE (No norm logprobs) | Pinned Model IDs | Cloud API Only | **ELIGIBLE (All P2 Tracks)** |
| `gemini-2.5-pro` | Google | Closed API | Cross-Model Eval | ELIGIBLE | **ELIGIBLE** | **ELIGIBLE** | Native JSON Schema | **LEVEL 1 (Doc-Verified, [0,1000])** | INELIGIBLE (No norm logprobs) | Pinned Model IDs | Cloud API Only | **ELIGIBLE (All P2 Tracks)** |
| `qwen3-vl-8b-instruct` | Alibaba / Open | Open-Weight | Cross-Model Eval | ELIGIBLE | **ELIGIBLE** | **ELIGIBLE** | Native Chat / JSON | **LEVEL 1 (Doc-Verified, Spatial)** | **ELIGIBLE** (Self-hosted logprobs) | Git Commit / HF Hash | **LOCAL_NOT_FEASIBLE** (Hosted API Req.) | **ELIGIBLE (All P2 Tracks via Hosted API)** |
| `qwen3-vl-32b-instruct` | Alibaba / Open | Open-Weight | Extended Eval | ELIGIBLE | **ELIGIBLE** | **ELIGIBLE** | Native Chat / JSON | **LEVEL 1 (Doc-Verified, Spatial)** | **ELIGIBLE** (Self-hosted logprobs) | Git Commit / HF Hash | **LOCAL_NOT_FEASIBLE** (Hosted API Req.) | **CONDITIONALLY ELIGIBLE (Cost/Compute Scope)** |
| `gpt-4o-2024-08-06` / `gpt-5.6` candidate | OpenAI | Closed API | Cross-Model Eval | ELIGIBLE | CONDITIONALLY ELIGIBLE | CONDITIONALLY ELIGIBLE | Native JSON Schema (`strict`) | LEVEL 3 (Prompt-Only) | PARTIALLY (Token logprobs only) | Pinned Dated IDs | Cloud API Only | **ELIGIBLE (Class.) / PROBE-REQ (Grounding)** |
| `grok-4.1-fast` | xAI | Closed API | Secondary Reference | ELIGIBLE | UNVERIFIED | UNVERIFIED | Prompted JSON | LEVEL 3 (Prompt-Only) | INELIGIBLE (No logprobs) | API Model String | Cloud API Only | **OPTIONAL (Extended Set)** |
| `bge-m3` (Text Embedding) | BAAI | Open-Weight | P1 Text Similarity | N/A (Text-only) | N/A | N/A | Dense Vector (1024d) | N/A | N/A | HF Commit / Ollama Tag | **FEASIBLE** (Ollama Local / CPU) | **ELIGIBLE (P1 Metric Tool Only)** |

---

## 10. Local Hardware Feasibility (Kiểm toán Khả thi Phần cứng Cục bộ)

Kết quả kiểm toán thực chứng cấu hình phần cứng máy trạm phát triển SafeShift (thực hiện lúc 16:22:00 ngày 2026-09-17):
- **Hệ điều hành:** Windows 11 x64.
- **Môi trường lập trình:** Python 3.11.9.
- **Card đồ họa (GPU):** NVIDIA GeForce GTX 1650 Ti (Laptop GPU).
- **Bộ nhớ đồ họa (VRAM):** **4.096 MiB (4 GB)**, Driver Version: 555.97, CUDA Version: 12.5.
- **Bộ nhớ hệ thống (System RAM):** 16.559.304 KB (~16 GB), Khả dụng thực tế: ~4,6 GB.
- **Không gian lưu trữ đĩa (Free Disk):** Ổ `C:` trống 97,39 GB; Ổ `D:` trống 113,19 GB.

### Đánh giá Tính Khả thi Suy luận Cục bộ (Local Inference Feasibility):
1. **Mô hình VLM Open-Weight (Qwen3-VL-8B, Qwen2.5-VL-7B, InternVL):**
   - VRAM 4 GB **HOÀN TOÀN KHÔNG ĐỦ** để chạy suy luận cục bộ cho các mô hình VLM 7B–8B (trọng số int4 cần ~5 GB, Vision Encoder và activation cache cần thêm ~2–3 GB VRAM).
   - **Kết luận:** Trạng thái suy luận cục bộ là **`LOCAL_NOT_FEASIBLE`**.
   - **Giải pháp bắt buộc:** Sử dụng **Hosted API thương mại (Alibaba Cloud DashScope, OpenRouter)** hoặc dịch vụ điện toán đám mây theo phiên (RunPod / vLLM server).
2. **Mô hình Nhúng Văn bản Cục bộ (`bge-m3` cho P1):**
   - Hoàn toàn có thể chạy mượt mà trên CPU hoặc tải lên 4 GB VRAM qua Ollama cục bộ (`http://localhost:11434`). Trạng thái: **`LOCAL_FEASIBLE`**.

---

## 11. Upstream P1 Prompt (Câu lệnh Chỉ dẫn Upstream P1)

### 11.1. Trích xuất Cấu trúc Nguyên bản
Câu prompt được trích xuất nguyên văn từ dòng 80–105 của `data/raw/InspecSafe-V1/model_api_generate_results.py`:

```text
Please analyze the input industrial scene image according to the following criteria:

Task Objectives:
1. Describe key visual elements in the image (e.g., personnel behavior, environmental conditions, object distribution, hazard sources, etc.).
2. Assess the safety level of the scene into one of four categories:
   - Level one: High-risk hazards present that could lead to severe incidents (e.g., open flame, smoke, personnel collapse, oil leakage, etc.);
   - Level two: Moderate risks present that may cause safety issues or violations (e.g., using a mobile phone, oil accumulation, foreign objects, missing required PPE, etc.);
   - Level three: Minor hazards present that require attention but are not urgent (e.g., water pooling, small foreign objects, missing face mask, etc.);
   - no abnormalities observed: No obvious abnormalities or risk factors.

Assessment Criteria (by industry):
| Safety Level | Oil & Gas / Chemical | Coal Conveyor Gallery | Tunnel | Power | Metallurgy |
|--------------|----------------------|------------------------|--------|-------|------------|
| Level one    | Open flame, smoke, no hard hat, no gloves, no mask, smoking, personnel collapse, oil leakage | Open flame, smoke, no hard hat, smoking, personnel collapse | Open flame, smoke, non-motorized vehicles in fast lane, wood, metal, personnel collapse | Open flame, smoke, smoking, personnel collapse | Open flame, smoke, no hard hat, personnel collapse |
| Level two    | Water pooling, using mobile phone | Using mobile phone, no gloves, no mask, foreign objects (plastic bags, bottles, foam, metal, paper) | Foam, plastic bags, plastic bottles, no hard hat, cabinet door open | Water pooling, oil accumulation, using mobile phone, foreign objects (plastic bags, bottles, foam, metal, paper), no hard hat, no gloves, cabinet door open | No gloves, no mask, smoking |
| Level three  | Foreign objects | Water pooling | Water pooling, oil accumulation, using mobile phone, no gloves, no mask, smoking | No mask | Water pooling, oil accumulation, using mobile phone, foreign objects (plastic bags, bottles, foam, metal, paper) |

Notes:
- If the image cannot be clearly recognized, output 'Unrecognizable' and explain the reason in the [Image Description].
- If the scene exhibits characteristics of multiple industries, prioritize the most relevant industry category.
- If no risk factors are present, assign the safety level as 'no abnormalities observed'.

Output Format Requirements:
Strictly follow the structure below (do not add extra content,only include Image Description and Safety Level):

[Image Description]
[Detailed description of the scene, human actions, environmental features, visible objects, etc.]

[Safety Level]
[Level one / Level two / Level three / no abnormalities observed]
```

### 11.2. Phân tích Phương pháp luận về Cấu trúc Prompt Upstream
1. **Sự hiện diện của Bảng Quy tắc Ngành (Industry Rule Table):**
   - Prompt cung cấp tường minh một bảng ma trận ánh xạ giữa Cấp độ An toàn và các loại vi phạm/nguy cơ cụ thể theo 5 ngành công nghiệp.
   - Bảng này là **Quy chuẩn Định nghĩa Nhiệm vụ (Task Specification / Policy)**, không phải rò rỉ dữ liệu (Data Leakage).
2. **Chính sách Tái lập P1:**
   - Trong Giao thức P1, để bảo đảm tính so sánh công bằng với kết quả công bố trong bài báo gốc, **SafeShift bắt buộc phải giữ nguyên vẹn 100% ngữ nghĩa của câu prompt này**.

---

## 12. Task Policy Disclosure vs Grounding Vocabulary Disclosure (Phân định Quy tắc Nhiệm vụ và Từ điển Định vị)

Một điểm nghẽn phương pháp luận quan trọng cần được giải quyết dứt điểm: **Làm thế nào để phân loại an toàn mà không làm bài toán bị thiếu đặc tả (under-specified), đồng thời không gây nhiễu gợi ý nhãn định vị?**

### 12.1. Phân biệt Hai Khái niệm Khác nhau
1. **Công khai Quy tắc Nhiệm vụ (Task Policy Disclosure):**
   - Trong bộ dữ liệu InspecSafe, các cấp nhãn `Level01`–`Level04` được định nghĩa thông qua ma trận quy chuẩn an toàn lao động cụ thể của từng ngành (ví dụ: ở ngành Hóa chất thì không đeo găng tay là Cấp 1, nhưng ở Luyện kim lại là Cấp 2).
   - Nếu một prompt phân loại hoàn toàn tước bỏ quy tắc này và chỉ yêu cầu "chọn Level01 đến Level04", bài toán phân loại sẽ trở nên **thiếu đặc tả ngữ nghĩa (under-specified)** vì mô hình không có căn cứ để biết quy ước đánh giá an toàn của nhà máy.
   - Do đó, việc cung cấp bảng quy chuẩn ngành cho bài toán phân loại là **hoàn toàn chính đáng và cần thiết**, tuyệt đối không được đánh đồng với "rò rỉ nhãn".
2. **Công khai Từ điển Nguy cơ Định vị (Grounding Hazard Vocabulary Disclosure):**
   - Đây là hành động cung cấp danh sách tên các đối tượng mục tiêu cần tìm và khoanh vùng hộp bao (ví dụ: `OPEN_FLAME`, `SMOKING`, `NO_HELMET`).
   - Việc công khai từ điển này trong cùng một lượt gọi phân loại có thể tạo ra hiệu ứng điều kiện hóa tìm kiếm (search/label conditioning), khiến mô hình quét ảnh tìm từ khóa trước rồi mới suy đoán cấp an toàn.

### 12.2. Đánh giá 3 Phương án Prompt Phân loại An toàn (Classification Prompt Candidates)
- **Phương án C1: Upstream Policy-Aware Classification (ĐƯỢC KHUYẾN NGHỊ CAO):**
  - Prompt cung cấp: hình ảnh, định nghĩa 4 cấp an toàn, và bảng quy chuẩn an toàn ngành nguyên bản; yêu cầu xuất duy nhất nhãn `safety_level`.
  - Hoàn toàn KHÔNG yêu cầu xuất bounding box, không yêu cầu bóc tách 12 hazard atoms của D6.
  - *Ưu điểm:* Bài toán được đặc tả trọn vẹn ngữ nghĩa, sát nhất với chuẩn mực gán nhãn ground-truth của InspecSafe, công bằng cho mọi mô hình.
- **Phương án C2: Abstract Level-Definition Classification:**
  - Chỉ mô tả ý nghĩa trừu tượng chung (Level 1: nguy hiểm cao, Level 2: trung bình, Level 3: nhỏ, Level 4: bình thường) mà không đưa bảng quy tắc ngành.
  - *Rủi ro:* Không đủ ngữ nghĩa để mô hình tái tạo đúng chính sách nhãn ground-truth (vốn phân hóa mạnh giữa 5 ngành công nghiệp).
- **Phương án C3: No-Policy Classification (Chỉ yêu cầu chọn nhãn):**
  - *Đánh giá:* **LOẠI BỎ (NOT RECOMMENDED)** vì bài toán bị thiếu đặc tả nghiêm trọng (under-specified).

---

## 13. Orthogonalization: Call Architecture vs Hazard Vocabulary (Tách bạch Trục Lệnh gọi và Trục Từ điển)

Để tránh ngộ nhận rằng "One-Call đồng nghĩa với Closed Vocabulary" hoặc "Two-Call tự động giải quyết mọi vấn đề", SafeShift phân định thành **HAI TRỤC ĐỘC LẬP HOÀN TOÀN**:

```
                         TRỤC B: HAZARD VOCABULARY
                 Open (B1)       Closed (B2)       Hybrid (B3)
             +---------------+----------------+----------------+
One-Call (A1)|  A1 + B1      |    A1 + B2     |    A1 + B3     |
             +---------------+----------------+----------------+
Two-Call (A2)|  A2 + B1      |    A2 + B2     |    A2 + B3     |
             +---------------+----------------+----------------+
Condition(A3)|  A3 + B1 (X)  |    A3 + B2 (X) |    A3 + B3 (X) |
             +---------------+----------------+----------------+
```

### 13.1. Trục A: Kiến trúc Lệnh gọi (Call Architecture)
- **A1. One Combined Call:** Gửi 1 request duy nhất: Image $\rightarrow$ trích xuất đồng thời `safety_level` và mảng `hazards` kèm `evidence`.
  - Tiết kiệm 50% chi phí API. Nếu đi kèm từ điển đóng, có thể tạo ra điều kiện hóa tìm kiếm (search conditioning).
- **A2. Two Independent Calls (ĐƯỢC ĐỀ XUẤT ĐÁNH GIÁ NGHIÊM TÚC):**
  - **Call 1 (Safety Classification):** Gửi Image + Task Policy (C1) $\rightarrow$ chỉ xuất `safety_level`. Áp dụng cho 100% mô hình.
  - **Call 2 (Hazard & Grounding):** Gửi Image + Grounding Prompt $\rightarrow$ phát hiện nguy cơ và xuất tọa độ hộp bao. **HOÀN TOÀN KHÔNG TRUYỀN DỰ ĐOÁN CỦA CALL 1 SANG CALL 2**. Chỉ áp dụng cho các mô hình Grounding-Eligible.
  - *Ưu điểm:* Giảm thiểu sự phụ thuộc trực tiếp (reduces direct conditioning) giữa quyết định phân loại và việc bám bằng chứng; bảo đảm phân loại an toàn được đo lường không bị chi phối bởi cấu trúc hộp bao.
- **A3. Two Conditioned Calls:** Call 2 nhận kết quả của Call 1. **LOẠI BỎ HOÀN TOÀN** do tạo ra thiên lệch điều kiện hóa nhân tạo, phá vỡ tính độc lập của RQ3.

### 13.2. Trục B: Từ điển Nguy cơ Định vị (Hazard Vocabulary)
- **B1. Open Vocabulary (Từ vựng Mở):** Mô hình tự do miêu tả nguy cơ bằng ngôn ngữ tự nhiên. Đo lường năng lực thị giác mở không gợi ý, nhưng gặp thách thức lớn về tính tất định khi ánh xạ sang 12 atoms của D6 để tính metric Mode A/Mode B.
- **B2. Closed 12-Hazard Vocabulary (Từ điển Đóng 12 Nguy cơ):** Mô hình chọn trực tiếp trong 12 nhãn D6. Khớp toán học 100% với D5/D6; bảo đảm parser hoạt động tất định hoàn toàn. Cần lưu ý: việc công khai không gian nhãn đóng có thể làm thay đổi độ khó của nhiệm vụ (may alter task difficulty).
- **B3. Hybrid Vocabulary (Từ điển Lai):** Kết hợp mô tả văn bản tự do với trường nhãn chuẩn hóa.

### 13.3. Đánh giá Trade-off khi Phân rã Độc lập (Decoupled Advantage)
Khi **Call 1 đã được phân lập hoàn toàn khỏi Call 2** (sử dụng kiến trúc A2 - Independent Two-Call):
- Từ điển đóng 12 nguy cơ (B2) trong Call 2 **KHÔNG CÒN TÁC ĐỘNG TRỰC TIẾP LÊN QUYẾT ĐỊNH PHÂN LOẠI CỦA CALL 1**.
- Điều này giải tỏa rủi ro lớn nhất của từ điển đóng (label hinting đối với safety level), đồng thời tận dụng triệt để ưu thế của từ điển đóng trong Call 2: **tính tất định tuyệt đối cho thuật toán ghép cặp bipartite matching Mode A / Mode B của Quyết định D5**.
- *Đề xuất Tổ hợp Ứng viên Hàng đầu (Top Candidate):* **A2 (Independent Two-Call) kết hợp C1 (Policy-Aware Classification) cho Call 1 và B2 (Closed 12-Hazard Grounding) cho Call 2**. *(Trạng thái: PROPOSED, NOT APPROVED)*.

---

## 14. RQ3 Consistency Semantics in Decoupled Evaluation (Ngữ nghĩa Tính Nhất quán RQ3 trong Đánh giá Phân rã)

Khi áp dụng phương án Hai Lệnh gọi Độc lập (Independent Two-Call Protocol):
1. **Định nghĩa Đánh giá Nhất quán:**
   Chỉ số Không nhất quán Phân loại – Bám bằng chứng ($\text{CGI}@\tau$) theo Quyết định D5 sẽ so sánh:
   $$\text{Dự đoán Cấp An toàn từ Call 1} \quad \longleftrightarrow \quad \text{Bằng chứng Tọa độ Khách quan từ Call 2}$$
2. **Loại bỏ Thiên lệch Điều kiện hóa Trực tiếp (Unconditioned Consistency):**
   Do Call 2 hoàn toàn không biết mô hình đã dự đoán cấp an toàn nào ở Call 1, việc mô hình phân loại đúng ở Call 1 nhưng lại không tìm thấy hoặc trượt hộp bao ở Call 2 phản ánh sự **không nhất quán nội tại thực chất giữa khả năng gán nhãn an toàn và khả năng định vị bằng chứng thị giác**.
3. **Giới hạn Diễn giải Khoa học Bắt buộc:**
   Theo Quyết định D1, D4 và D5: Sự không nhất quán này được gọi chính xác là:
   **"Classification-Grounding Inconsistency relative to available object-support annotation"**.
   Tuyệt đối **không tuyên bố đây là bằng chứng chứng minh mô hình "suy luận sai" (proof of wrong reasoning)** hay "đoán mò", vì bộ dữ liệu chưa có nhãn chuẩn về lý do con người (human rationale GT).

---

## 15. Canonical Output Schema (Cấu trúc Đầu ra Chuẩn hóa Nội bộ)

Cấu trúc Đầu ra Chuẩn hóa Nội bộ (Canonical Logical JSON Schema) cho Call 2 (hoặc One-Call nếu được chọn) theo Quyết định D4:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SafeShiftCanonicalP2Output",
  "type": "object",
  "required": ["hazards"],
  "properties": {
    "safety_level": {
      "type": "string",
      "enum": ["Level01", "Level02", "Level03", "Level04"],
      "description": "Optional in Call 2; mandatory in Call 1 or One-Call mode."
    },
    "hazards": {
      "type": "array",
      "description": "List of observed hazard claims. Empty if no abnormalities present.",
      "items": {
        "type": "object",
        "required": ["hazard_type", "evidence"],
        "properties": {
          "hazard_type": {
            "type": "string",
            "description": "Hazard atom identifier (standardized 12 atoms in B2, or text in B1)."
          },
          "evidence": {
            "type": "array",
            "description": "List of bounding boxes localizing visual evidence.",
            "items": {
              "type": "object",
              "required": ["bbox"],
              "properties": {
                "bbox": {
                  "type": "array",
                  "items": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
                  "minItems": 4,
                  "maxItems": 4,
                  "description": "Internal canonical bounding box: [xmin, ymin, xmax, ymax] normalized in [0.0, 1.0]."
                },
                "label": {
                  "type": "string",
                  "description": "Optional object description or class name."
                }
              }
            }
          }
        }
      }
    }
  }
}
```

---

## 16. Model-Specific Adapters (Các Bộ Chuyển đổi Đặc thù theo Mô hình)

Theo Quyết định D4, việc chuẩn hóa tọa độ về hệ quy chiếu nội bộ là trách nhiệm của **Adapter tất định**:

### 16.1. Google Gemini Adapter
- **Native Convention:** $\mathbf{b}_{\text{gemini}} = [y_{\min}, x_{\min}, y_{\max}, x_{\max}]$ với $y, x \in [0, 1000]$.
- **Công thức chuyển đổi tất định:**
  $$x_{\min} = \text{clamp}\left(\frac{\mathbf{b}_{\text{gemini}}[1]}{1000.0}, 0.0, 1.0\right), \quad y_{\min} = \text{clamp}\left(\frac{\mathbf{b}_{\text{gemini}}[0]}{1000.0}, 0.0, 1.0\right)$$
  $$x_{\max} = \text{clamp}\left(\frac{\mathbf{b}_{\text{gemini}}[3]}{1000.0}, 0.0, 1.0\right), \quad y_{\max} = \text{clamp}\left(\frac{\mathbf{b}_{\text{gemini}}[2]}{1000.0}, 0.0, 1.0\right)$$

### 16.2. Qwen-VL Adapter
- **Native Convention:** Xuất token `<|box_start|>(ymin,xmin),(ymax,xmax)<|box_end|>` hoặc JSON với tọa độ $[0, 1000]$.
- **Công thức chuyển đổi:** Biểu thức chính quy trích xuất số nguyên, hoán vị $y \leftrightarrow x$ nếu là $y$-first, và chia cho $1000.0$.

### 16.3. OpenAI / Claude Adapter
- **Native Convention:** Xuất mảng 4 số thực `[xmin, ymin, xmax, ymax]` trong đoạn $[0.0, 1.0]$.
- **Nhiệm vụ:** Kiểm tra tính hợp lệ số học, kẹp giá trị $[0.0, 1.0]$, và xác minh $x_{\min} \le x_{\max}, y_{\min} \le y_{\max}$.

### 16.4. Yêu cầu Kiểm thử Đơn vị (Unit Test Contract)
Mọi Adapter bắt buộc phải vượt qua unit tests với dữ liệu tổng hợp trước khi sử dụng:
1. Chuyển đổi đúng tọa độ cực biên ($[0, 0, 1000, 1000] \rightarrow [0.0, 0.0, 1.0, 1.0]$).
2. Hoán vị chính xác thứ tự $y$-first sang $x$-first.
3. Xử lý an toàn các giá trị vượt biên nhẹ do làm tròn (ví dụ $1001 \rightarrow 1.0$).
4. Báo lỗi tất định khi mảng tọa độ bị thiếu phần tử hoặc chứa chuỗi không phải số.

---

## 17. Grounding Eligibility & Gate Criteria (Tiêu chuẩn và Cổng Tham gia Bám Bằng chứng)

Tuân thủ Quyết định D4 (Capability-Aware Policy B), quyền tham gia đường đua Grounding (RQ3) được kiểm soát nghiêm ngặt:

1. **Nhóm Đủ Điều Kiện Trực Tiếp:**
   - Các mô hình đạt **LEVEL 1 (DOC-VERIFIED SPATIAL CAPABILITY)**: **Google Gemini** (Gemini 2.5 Flash / Pro) và **Qwen-VL** (Qwen3-VL-8B / 32B).
   - Được phép tham gia trực tiếp đường đua Grounding mà không cần probe thực nghiệm.
2. **Nhóm Cần Kiểm Chứng Qua Cổng Năng Lực:**
   - Các mô hình ở diện **LEVEL 3 (PROMPT-ONLY / UNVERIFIED SPATIAL)**: **OpenAI** (GPT-4o) và **Anthropic** (Claude 3.5 / 3.7 Sonnet).
   - Bắt buộc phải trải qua **External Spatial Capability Probe** (Mục 28) và đạt chuẩn **LEVEL 2A (EXTERNAL SPATIAL-PROBE VERIFIED)** mới được tham gia Grounding.
   - Nếu mô hình chỉ đạt **LEVEL 2B (FORMAT-OPERABILITY VERIFIED ONLY)**: **KHÔNG ĐƯỢC THAM GIA GROUNDING**.

---

## 18. Classification-Only Policy (Chính sách Mô hình Chỉ Tham gia Phân loại)

Để bảo đảm tính công bằng khoa học và tuân thủ Quyết định D4:
1. **Tham gia trọn vẹn Track Phân loại:** Mô hình chỉ tham gia phân loại vẫn được đánh giá đầy đủ trên toàn bộ 5.013 mẫu của P2 cho các chỉ số phân loại an toàn 4 lớp (Balanced Accuracy, Macro-F1), sai số an toàn trọng yếu (Track A, Track B), và phân tầng nguy cơ RQ2.
2. **Trạng thái chính thức trong Track RQ3 (Grounding):**
   - Trạng thái được ghi nhận là: **`NOT PARTICIPATING` (Không tham gia)**.
   - **Tuyệt đối không gán nhãn:** `GROUNDING_FAILURE` (Thất bại bám bằng chứng) hay `IoU = 0.0`.
   - Các mô hình này bị loại hoàn toàn khỏi mẫu số và bảng xếp hạng của RQ3-A (Direct Grounding) và RQ3-B (Proxy Grounding).
   - Tuyệt đối không tính điểm trung bình tổng hợp gộp cả phân loại lẫn grounding để xếp hạng chung cuộc giữa các mô hình khác nhau về bản chất năng lực.

---

## 19. Reasoning / Thinking Policy (Chính sách Chế độ Suy luận / Thinking)

| Phương án | Mô tả cơ chế | Ưu điểm phương pháp luận | Nhược điểm / Rủi ro | Đánh giá Khả thi |
| :--- | :--- | :--- | :--- | :--- |
| **Phương án 1: Tắt hoàn toàn Thinking** (`thinking_budget = 0`) | Ép tất cả mô hình tắt suy luận mở rộng, chỉ giải mã trực tiếp. | Tiết kiệm chi phí token tối đa; tạo điểm xuất phát đồng nhất cho suy luận zero-shot nhanh. | Một số mô hình suy luận chuyên sâu không cho phép tắt hoàn toàn reasoning; có thể làm giảm năng lực đọc hiểu quy tắc an toàn. | Khả thi có điều kiện. |
| **Phương án 2: Sử dụng Cấu hình Mặc định của Nhà cung cấp** (Provider Default) | Sử dụng cấu hình mặc định do nhà cung cấp tối ưu cho từng snapshot. | Tôn trọng thiết kế nguyên bản của mô hình; không can thiệp cưỡng bức vào cơ chế nội tại. | Mức độ nỗ lực suy luận có thể không đồng đều giữa các mô hình. | **KHUYẾN NGHỊ CAO NHẤT (Minh bạch, ghi rõ metadata)**. |

*Lưu ý về Google Gemini Object Detection:* Nếu tài liệu chính thức của Google khuyến nghị cấu hình thinking tối ưu cho tác vụ phát hiện đối tượng (ví dụ `thinking_budget = 0` hoặc low effort), đây được coi là **Cấu hình Wrapper Cần thiết theo Khuyến cáo Kỹ thuật (Capability-Required Wrapper Configuration)**, không phải là tinh chỉnh prompt thiên vị.

---

## 20. Decoding Policy (Chính sách Giải mã và Nhiệt độ)

### 20.1. Đối với Giao thức Tái lập P1
- Bắt buộc tuân thủ đúng cấu hình ghi nhận trong script phát hành chính thức: `temperature = 0.1`.

### 20.2. Đối với Giao thức Nghiên cứu Chính P2
- Ưu tiên giải mã có phương sai thấp nhất (**Low-Variance / Deterministic Decoding**):
  - **Khuyến nghị chính:** Thiết lập `temperature = 0.0` (hoặc mức tối thiểu của API). Khóa giá trị `seed = 42` nếu API hỗ trợ.
  - *Cảnh báo bắt buộc:* Không tuyên bố `temperature = 0` đồng nghĩa với tính tất định số học tuyệt đối 100% do đặc thù tính toán song song dấu phẩy động trên GPU.
  - Mọi tham số giải mã thực tế bắt buộc phải được ghi nhận đầy đủ trong run metadata.

---

## 21. Structured Output & Parse Policy (Chính sách Đầu ra Có Cấu trúc và Phân tích Cú pháp)

Kế thừa Quyết định D5, SafeShift đo lường độ bền cú pháp và xử lý lỗi phân tích cú pháp theo hai lớp minh bạch:
1. **Lớp Chẩn đoán Cú pháp (Diagnostic PSR):**
   - Báo cáo **Tỷ lệ Phân tích Phản hồi Thành công ($\text{PSR}_{\text{response}}$)** và **Tỷ lệ Phân tích Tọa độ Hộp bao Hợp lệ ($\text{PSR}_{\text{box}}$)**.
2. **Lớp Đánh giá Hiệu năng Thực nghiệm:**
   - **End-to-End Grounding:** Mọi phản hồi lỗi cú pháp không trích xuất được tọa độ hợp lệ đều nhận điểm $\text{IoU} = 0.0$ cho toàn bộ các nguy cơ liên quan trong mẫu đó.
   - **Parse-Conditional Diagnostic:** Báo cáo phụ trợ chỉ số IoU trung bình tính riêng trên các trường hợp parse thành công.

---

## 22. Calibration Eligibility (Tính Đủ Điều kiện Đánh giá Độ Hiệu chỉnh Xác suất)

Theo Quyết định D5:
1. Các mô hình Closed-API (OpenAI, Google Gemini, Anthropic Claude) không cung cấp phân bố xác suất phân loại chuẩn hóa (Normalized Softmax Probabilities) trên 4 lớp an toàn, do đó được phân loại là **`CALIBRATION_INELIGIBLE`**.
2. **TUYỆT ĐỐI CẤM SỬ DỤNG ĐỘ TỰ TIN TỰ THUẬT (Self-Reported Textual Confidence):** Nghiêm cấm việc yêu cầu mô hình tự viết ra câu văn như `"confidence: 95%"` để làm đại diện cho xác suất hiệu chuẩn.
3. Calibration không tham gia vào bảng chỉ số so sánh chính xuyên mô hình của SafeShift Seminar.

---

## 23. Version Pinning & Provenance (Cố định Phiên bản và Truy vết Nguồn gốc)

Mỗi tệp kết quả thực nghiệm bắt buộc phải lưu kèm đối tượng siêu dữ liệu:
- `protocol_id`, `protocol_version`, `protocol_freeze_commit_sha`.
- `run_id` (UUIDv4 kèm ISO 8601 UTC timestamp), `sample_id`, `image_sha256`.
- `provider`, `model_family`, `requested_model_id`, `resolved_model_version`, `api_endpoint_url`, `sdk_version`.
- `prompt_template_id`, `prompt_sha256`, `decoding_parameters`, `latency_seconds`, `raw_response_id`, `adapter_version`.
- Nghiêm cấm dùng moving aliases; bắt buộc dùng dated pinned snapshots.

---

## 24. Cost & Runtime Feasibility (Phân tích Chi phí và Thời gian Thực thi)

| Mô hình Ứng viên | Biểu giá Input (USD/1M) | Biểu giá Output (USD/1M) | Chi phí P1 (1.250 ảnh) | Chi phí P2 One-Call (5.013 ảnh) | Chi phí P2 Two-Call (5.013 ảnh) | Khả thi Ngân sách Seminar |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Google Gemini 2.5 Flash** | \$0.10 | \$0.40 | ~\$0.35 | ~\$1.35 | ~\$2.50 | **CỰC KỲ KHẢ THI** (< \$5) |
| **Google Gemini 2.5 Pro** | \$1.25 | \$5.00 | ~\$4.35 | ~\$16.80 | ~\$30.00 | **RẤT KHẢ THI** (< \$35) |
| **Qwen3-VL-8B** (Hosted API) | ~\$0.20 | ~\$0.60 | ~\$0.60 | ~\$2.40 | ~\$4.50 | **CỰC KỲ KHẢ THI** (< \$5) |
| **OpenAI GPT-4o** (Snapshot) | \$2.50 | \$10.00 | ~\$8.75 | ~\$33.75 | ~\$60.00 | **KHẢ THI** (~ \$60) |
| **Claude 3.5 / 3.7 Sonnet** | \$3.00 | \$15.00 | ~\$11.70 | ~\$45.00 | ~\$80.00 | **KHẢ THI** (~ \$80) |
| **Claude Opus 4.5** (P1 Ref) | ~\$15.00 | ~\$75.00 | ~\$58.50 | N/A (Chỉ P1) | N/A | **KHẢ THI TRONG P1** (~ \$60) |
| **BGE-M3 (Ollama Local)** | \$0.00 | \$0.00 | \$0.00 | N/A | N/A | **HOÀN TOÀN MIỄN PHÍ** |

- Tổng chi phí cho minimal shortlist 4 mô hình P2: ~\$55 USD (nếu One-Call) hoặc ~\$95 USD (nếu Two-Call). Toàn bộ nằm gọn trong ngân sách Seminar.

---

## 25. Pretraining Contamination vs Researcher Adaptation (Phân định Nhiễm Tiền Huấn luyện và Thích nghi Benchmark)

1. **Nhiễm Dữ liệu Tiền Huấn luyện (Pretraining Contamination — UNKNOWN):**
   - Biến số ngoại sinh đối với các mô hình đóng; không thể kiểm soát hay khẳng định chắc chắn. Báo cáo SafeShift sẽ công bố đây là hạn chế khách quan không thể loại bỏ của phương pháp luận benchmark trên mô hình thương mại.
2. **Thích nghi Benchmark do Người Nghiên cứu (Researcher Benchmark Adaptation — CHỦ ĐỘNG NGĂN NGỪA):**
   - Biến số nội sinh được SafeShift chủ động kiểm soát bằng: Benchmark Firewall (5.013 ảnh là Evaluation-Only), Protocol Freeze (trước lần chạy đầu tiên), và External Spatial Capability Probe (chỉ thử nghiệm trên dữ liệu ngoài).

---

## 26. P1 Reproduction Plan & Tolerance Policy (Kế hoạch Tái lập Baseline P1 & Chính sách Sai số)

### 26.1. Quy trình Thực hiện
1. Dùng đúng 1.250 ảnh thuộc `test/Annotations/`.
2. Dùng nguyên văn prompt Upstream P1 (Mục 11.1), `temperature = 0.1`, mô hình tham chiếu `claude-opus-4-5-20251101` (hoặc mô hình thay thế tương thích nếu snapshot gốc không truy cập được trực tiếp).
3. Đánh giá Safety Accuracy và BGE-M3 Semantic Similarity qua Ollama cục bộ.

### 26.2. Chính sách Báo cáo Tái lập Khoa học (Loại bỏ Tiêu chí Dung sai Tùy tiện $\pm 1–2\%$)
- **LOẠI BỎ HOÀN TOÀN TIÊU CHÍ TÙY TIỆN $\pm 1–2\%$**.
- **Chính sách Chuẩn hóa:**
  1. Công bố đầy đủ giá trị số học tái lập được chính xác ($\text{Metric}_{\text{reproduced}}$).
  2. Báo cáo chênh lệch tuyệt đối so với giá trị bài báo gốc công bố: $\Delta = \text{Metric}_{\text{reproduced}} - \text{Metric}_{\text{published}}$.
  3. Phân tích nguyên nhân kỹ thuật nếu có sai lệch (trôi dạt snapshot API, cập nhật backend của nhà cung cấp).
  4. Trạng thái tái lập được xác lập dựa trên tính khả thi thực tế của quy trình kỹ thuật:
     - `REPRODUCIBLE`: Thực thi thành công trên đúng mô hình, đúng tham số, đúng dữ liệu, và kết quả nhất quán với công bố gốc.
     - `COMPATIBILITY_REPRODUCTION`: Thực thi thành công bằng một phiên bản mô hình tương thích do snapshot gốc không còn khả dụng trên API chính thức.
     - `NOT_EXACTLY_REPRODUCIBLE`: Nếu mô hình hoặc hạ tầng không thể tái lập được quy trình gốc.

---

## 27. P2 Research Run Plan (Kế hoạch Thực hiện Giao thức Nghiên cứu Chính P2)

1. **Nạp Manifest Chuẩn:** Nạp `data/manifests/dataset_manifest.csv` (5.013 mẫu, bảo toàn metadata provenance).
2. **Thực thi Suy luận:** Chạy theo lô với cơ chế exponential backoff retry; `temperature = 0.0`. Áp dụng kiến trúc lệnh gọi đã được phê duyệt.
3. **Lưu trữ Raw Outputs:** Lưu nguyên văn chuỗi phản hồi thô vào `outputs/raw_runs/P2/{model_id}/{run_id}/{sample_id}.json` trước khi parse.
4. **Chuyển đổi Tất định:** Dùng Adapter chuyển đổi tọa độ sang $[x_{\min}, y_{\min}, x_{\max}, y_{\max}] \in [0.0, 1.0]$.
5. **Tính toán Metric & Bootstrap:** Chạy động cơ D5 để tính Balanced Accuracy, Macro-F1, FNR/FPR Track A & B, Class-Conditional Domain Analysis (RQ1), 4 chỉ số trên 7 tầng nguy cơ (RQ2), Direct Grounding Mode A & B (RQ3-A), Weak Proxy PLC (RQ3-B), và $\text{CGI}@\tau$. Xuất khoảng tin cậy 95% qua Domain-Stratified Point-Cluster Bootstrap ($B=2.000$) và Paired Bootstrap Difference CI 95%.

---

## 28. External Spatial Capability Probe Plan (Kế hoạch Cổng Thử nghiệm Năng lực Không gian Ngoài Benchmark)

Để xác minh năng lực định vị thực tế cho các mô hình ở diện `LEVEL 3 (Prompt-Only)` mà không vi phạm Benchmark Firewall:

### 28.1. Nguồn Dữ liệu Thử nghiệm Hợp lệ (External Data Only)
Chỉ sử dụng hình ảnh bên ngoài InspecSafe có **Ground Truth không gian khách quan đã biết (Known Spatial Ground Truth)**:
- Tập ảnh công cộng mở (COCO, Open Images) có bounding box chuẩn.
- Các ví dụ minh họa chính thức của nhà cung cấp có tọa độ chuẩn.
- Hình ảnh tổng hợp nhân tạo có vị trí vật thể xác định trước.

### 28.2. Tiêu chí Đánh giá Cổng Năng lực Không gian (Capability Gate Criteria)
Một mô hình Prompt-Only chỉ được cấp trạng thái **`LEVEL 2A (EXTERNAL SPATIAL-PROBE VERIFIED)`** khi thỏa mãn đồng thời hai điều kiện:
1. **Tính Hợp Lệ Giao Diện Cú pháp (Format Operability):**
   - Schema JSON parse được, tọa độ dạng số, thứ tự tọa độ xác định rõ, giá trị nằm trong miền hợp lệ $[0, 1]$ hoặc $[0, 1000]$ với $x_{\min} \le x_{\max}, y_{\min} \le y_{\max}$.
   - Khả năng xuất đa hộp bao và liên kết nguy cơ – bằng chứng biểu diễn được.
   *(Nếu chỉ đạt tiêu chí 1, mô hình nhận trạng thái LEVEL 2B và KHÔNG ĐƯỢC tham gia Grounding)*.
2. **Năng lực Định vị Không gian Tối thiểu (Demonstrable Spatial Localization):**
   - Trên các ca kiểm thử ngoài benchmark có target xác định, mô hình chứng minh được khả năng khoanh vùng có ý nghĩa không gian thực chất: hộp bao dự đoán chồng lấn có ý nghĩa với vật thể mục tiêu (ví dụ $\text{IoU} > 0.0$ hoặc tâm hộp bao nằm trong vật thể) trên nhiều ca kiểm thử độc lập, loại bỏ khả năng sinh tọa độ ngẫu nhiên.
- *Quy tắc bản chất:* Đây thuần túy là **Cổng Kiểm Tra Năng Lực Vận Hành Kỹ Thuật (Technical Capability Gate)** để phân định quyền tham gia benchmark; **tuyệt đối không dùng để chấm điểm, xếp hạng hay chọn mô hình**.

---

## 29. Model Shortlists (Các Danh sách Mô hình Đề xuất)

### 29.1. Danh sách Tái lập Upstream (P1 Reproduction Set — 1.250 mẫu test)
1. **`claude-opus-4-5-20251101`** (hoặc Claude Sonnet tương thích nếu snapshot gốc không truy cập được trực tiếp).
2. **`grok-4.1-fast`** (mô hình đối chiếu văn bản trong repo upstream).
3. **`bge-m3`** (mô hình nhúng văn bản cục bộ qua Ollama).

### 29.2. Danh sách Nghiên cứu Cốt lõi Tối thiểu (Minimal SafeShift Research Set — 4 Mô hình cho P2)
1. **Google Gemini 2.5 Flash (`gemini-2.5-flash-001`):** Closed API, Object Detection nguyên bản (Level 1), chi phí cực thấp. Tham gia Phân loại và Grounding.
2. **Google Gemini 2.5 Pro (`gemini-2.5-pro-001`):** Closed API, Suy luận sâu, Object Detection nguyên bản (Level 1). Tham gia Phân loại và Grounding.
3. **Qwen3-VL-8B-Instruct (Hosted API):** Open-weight tiêu biểu, 2D Grounding nguyên bản (Level 1). Tham gia Phân loại và Grounding qua API đám mây.
4. **OpenAI GPT-4o (`gpt-4o-2024-08-06`):** Closed API, Mỏ neo phân loại tổng quát tiêu chuẩn vàng. Tham gia Phân loại (chắc chắn); tham gia Grounding nếu vượt qua External Spatial Probe đạt Level 2A.

### 29.3. Danh sách Mở rộng Tùy chọn (Optional Extended Set)
- Claude 3.7 Sonnet (Extended Thinking), Qwen3-VL-32B-Instruct (Scaling effect), InternVL-2.5-8B.

---

## 30. D8 Decision Matrix (Ma trận Quyết định D8 Toàn diện)

| Chiều Kỹ thuật | Phương án 1 (Option A) | Phương án 2 (Option B) | Phương án 3 (Option C) | Gợi ý Đánh giá của SafeShift |
| :--- | :--- | :--- | :--- | :--- |
| **A. Tường lửa Kiểm chuẩn (Benchmark Firewall)** | Bắt buộc (Required): Toàn bộ 5.013 ảnh là Evaluation-Only; cấm probe/tune trên InspecSafe | Không bắt buộc: Cho phép dùng ảnh InspecSafe để probe/tune | N/A | **Phương án 1 (Bắt buộc)**: Giảm thiểu nguy cơ thích nghi benchmark nội sinh. |
| **B. Cổng Năng lực Không gian (Spatial Capability Gate)** | Phân định Level 2A (Spatial GT verified) vs Level 2B (Format only); chỉ Level 1/2A được Grounding | Format-only probe là đủ để vào Grounding | Cho phép mọi mô hình tham gia Grounding | **Phương án 1 (Level 1 / 2A)**: Bảo đảm mô hình thực sự có năng lực không gian mới vào Grounding. |
| **C. Nguồn Dữ liệu Capability Probe** | External-Only: ảnh công cộng ngoài benchmark có known GT tọa độ, ảnh tổng hợp, doc examples | Lấy một tập con nhỏ từ InspecSafe | N/A | **Phương án 1 (External-Only)**: Bảo vệ Benchmark Firewall tuyệt đối. |
| **D. Thời điểm Đóng băng Giao thức (Protocol Freeze)** | Đóng băng tuyệt đối trước lần inference đầu tiên trên InspecSafe (ghi nhận commit SHA) | Đóng băng linh hoạt trong quá trình chạy | N/A | **Phương án 1 (Freeze trước inference đầu tiên)**: Bảo toàn tính tái lập khoa học. |
| **E. Chính sách Sửa lỗi Sau Đóng băng** | Cấm sửa prompt theo hiệu năng; lỗi kỹ thuật phải bump version & rerun toàn bộ | Cho phép sửa riêng prompt của mô hình yếu | N/A | **Phương án 1 (Strict Version Bump & Full Rerun)**: Bảo đảm tính công bằng tuyệt đối. |
| **F. Trục A: Kiến trúc Lệnh gọi P2** | A1. One Combined Call (Chung 1 request lấy cả nhãn và box) | A2. Two Independent Calls (Call 1: Classify; Call 2: Grounding độc lập, không nhận output Call 1) | A3. Two Conditioned Calls (Call 2 nhận kết quả Call 1) | **Cần Quyết định**: A1 tiết kiệm chi phí; A2 giảm thiểu điều kiện hóa trực tiếp giữa phân loại và grounding. |
| **G. Trục B: Từ điển Nguy cơ Định vị** | B1. Open Vocabulary (Mô tả tự do, ánh xạ sau) | B2. Closed 12-Hazard Vocabulary (Chọn trong 12 nhãn D6) | B3. Hybrid (Nhãn đóng + Mô tả tự do) | **Cần Quyết định**: B2 tương thích toán học cao nhất với D5/D6; đặc biệt tối ưu khi đi cùng A2. |
| **H. Quy tắc Nhiệm vụ Phân loại (Task Policy)** | C1. Upstream Policy-Aware (cung cấp bảng quy chuẩn an toàn ngành nguyên bản trong Call 1) | C2. Abstract Level-Definition (chỉ mô tả trừu tượng Level 1–4) | C3. No-Policy (chỉ yêu cầu chọn nhãn) | **Phương án C1**: Đầy đủ ngữ nghĩa, ngăn ngừa bài toán phân loại bị under-specified. |
| **I. Quy mô Mô hình P2** | 3 Mô hình (Gemini Flash, Qwen-VL-8B, GPT-4o) | 4 Mô hình (Gemini Flash, Gemini Pro, Qwen-VL-8B, GPT-4o) | Mở rộng $\ge 6$ mô hình | **Phương án 2 (4 Mô hình)**: Đạt cân bằng tối ưu giữa độ đa dạng khoa học và chi phí kiểm soát (~ \$55–\$95). |
| **J. Chế độ Suy luận (Thinking)** | Cưỡng bức tắt hoàn toàn (`budget=0`) | Sử dụng cấu hình mặc định (Provider Default) | Chuẩn hóa nỗ lực cố định cho mọi mô hình | **Phương án 2 (Provider Default)**: Tôn trọng thiết kế nguyên bản của nhà cung cấp; ghi nhận chi tiết trong metadata. |
| **K. Quản lý Phiên bản Mô hình** | Dùng bí danh động mới nhất (Moving latest) | Bắt buộc ghim phiên bản cố định (Dated Pinned IDs) | Chấp nhận hỗn hợp có gắn cờ cảnh báo | **Phương án 2 (Dated Pinned IDs)**: Bảo đảm tính tái lập khoa học lâu dài. |

---

## 31. Preliminary D8 Recommendation (Đề xuất Sơ bộ cho D8)

Nhóm nghiên cứu trân trọng đề xuất khung phương án tổng thể cho Quyết định D8 với trạng thái **PROPOSED, NOT APPROVED**:

1. **Về Tường lửa Kiểm chuẩn, Đóng băng Giao thức & Cổng Năng lực Không gian:**
   - Phê duyệt **Benchmark Firewall**: Toàn bộ 5.013 ảnh InspecSafe-V1 là Evaluation-Only.
   - Phê duyệt **Protocol Freeze**: Đóng băng toàn bộ giao thức và ghi nhận `protocol_freeze_commit_sha` trước lần chạy đầu tiên.
   - Phê duyệt **External Spatial Capability Gate**: Chỉ cấp quyền tham gia Grounding cho các mô hình đạt Level 1 (Doc-Verified) hoặc Level 2A (External Spatial-Probe Verified trên ảnh ngoài có GT tọa độ). Mô hình Level 2B (Format only) không được tham gia Grounding.
2. **Về Giao thức P1 (Baseline Replication):**
   - Giữ nguyên 100% câu prompt Upstream và Bảng Quy tắc 5 ngành.
   - Chạy trên 1.250 mẫu test chính thức với mô hình tham chiếu `claude-opus-4-5-20251101` (hoặc mô hình thay thế tương thích), thiết lập `temperature = 0.1`.
   - Loại bỏ tiêu chí dung sai tùy tiện $\pm 1–2\%$; báo cáo số liệu chính xác và chênh lệch tuyệt đối so với công bố gốc.
3. **Về Danh sách Mô hình Nghiên cứu (4 Mô hình Cốt lõi):**
   - `gemini-2.5-flash-001`, `gemini-2.5-pro-001`, `qwen3-vl-8b-instruct` (Hosted API), và `gpt-4o-2024-08-06`.
4. **Về Kiến trúc Đánh giá P2 (Đề xuất Tổ hợp Ứng viên Hàng đầu):**
   - **Tổ hợp Khuyến nghị:** **A2 (Two Independent Calls) + C1 (Policy-Aware Classification) + B2 (Closed 12-Hazard Grounding)**:
     - *Call 1 (Safety Classification):* Gửi Image + Bảng quy chuẩn an toàn ngành (C1) $\rightarrow$ chỉ xuất `safety_level`. Áp dụng cho 100% mô hình.
     - *Call 2 (Hazard & Grounding):* Gửi Image + Từ điển đóng 12 nguy cơ (B2) $\rightarrow$ xuất tọa độ hộp bao cho các mô hình Grounding-Eligible. **Call 2 hoàn toàn độc lập, không nhận kết quả từ Call 1**.
     - *Lợi ích phương pháp luận:* Bảo vệ tính khách quan của bài toán phân loại an toàn (không bị gợi ý bởi 12 nhãn nguy cơ); đồng thời tận dụng tính tất định tuyệt đối của từ điển đóng 12 nguy cơ trong Call 2 để phục vụ thuật toán ghép cặp Mode A/B của D5.
   - *Tổ hợp Thay thế (Nếu ưu tiên tối đa ngân sách):* **A1 (One Combined Call) + B2 (Closed 12-Hazard)**: Giảm chi phí từ ~\$95 xuống ~\$55 USD, nhưng chấp nhận việc công khai không gian nhãn nguy cơ trong cùng prompt phân loại.

---

## 32. Risks & Limitations (Rủi ro và Giới hạn Phương pháp luận)

1. **Rủi ro Không khả dụng của Snapshot Upstream:** Tên định danh `claude-opus-4-5-20251101` có thể là định danh nội bộ qua proxy DMX. Nếu gọi trực tiếp từ Anthropic API, cần dùng phiên bản Claude tương đương và ghi rõ trạng thái *Compatibility Reproduction*.
2. **Hạn chế Phần cứng Cục bộ:** GPU 4 GB VRAM buộc phải dùng Hosted API cho mô hình nguồn mở Qwen-VL, phát sinh chi phí mạng và phụ thuộc vào tính sẵn sàng của nhà cung cấp dịch vụ đám mây.
3. **Giới hạn Nhận thức luận về Nhiễm Dữ liệu:** Không thể chứng minh sự vắng mặt tuyệt đối của nhiễm dữ liệu tiền huấn luyện trên các mô hình Closed-API. SafeShift định vị trung thực là benchmark đánh giá thực nghiệm trên các mô hình đóng băng trọng số hiện hành.
4. **Sự Không Hoàn hảo của Chú thích Bằng chứng:** Nhắc lại cảnh báo từ Quyết định D6 và D7: các đa giác vật thể có sẵn không mã hóa trọn vẹn lý do vi phạm an toàn của con người. Mọi chỉ số IoU và PLC phải được diễn giải thận trọng trong phạm vi chú thích hiện hữu.

---

## 33. Questions Requiring Approval (Các Câu hỏi Cần Xin Ý kiến Phê duyệt)

Để hoàn thiện và chính thức khóa Quyết định D8 tại Week 2, nhóm nghiên cứu kính trình Project Owner xem xét và cho ý kiến về **18 câu hỏi then chốt**:

1. **Phê chuẩn Benchmark Firewall:** Có phê duyệt toàn bộ 5.013 ảnh của InspecSafe-V1 là **Evaluation-Only**, nghiêm cấm dùng cho thăm dò năng lực, gỡ lỗi prompt hay chọn mô hình không?
2. **Phê chuẩn Cổng Năng lực Không gian Ngoài Benchmark:** Có đồng thuận phân định giữa Level 2A (External Spatial GT verified) và Level 2B (Format only), và chỉ cho phép mô hình đạt Level 1 hoặc Level 2A tham gia Grounding không?
3. **Phê chuẩn Nguồn Dữ liệu Thử nghiệm Năng lực:** Có chấp thuận cấm dùng ảnh InspecSafe cho capability probe và bắt buộc chỉ dùng **ảnh bên ngoài benchmark có ground truth tọa độ khách quan** không?
4. **Phê chuẩn Chính sách Đóng băng Giao thức:** Có đồng ý đóng băng toàn diện giao thức (Protocol Freeze) và ghi nhận `protocol_freeze_commit_sha` trước lần inference đầu tiên trên InspecSafe không?
5. **Phê chuẩn Kiểm soát Thay đổi Sau Đóng băng:** Có chấp thuận quy tắc cấm sửa prompt theo hiệu năng và bắt buộc bump protocol version kèm rerun toàn bộ khi sửa lỗi kỹ thuật không?
6. **Chính sách Lựa chọn Mô hình:** Có phê duyệt nguyên tắc chọn mô hình hoàn toàn độc lập với điểm số trên InspecSafe không?
7. **Phê chuẩn Quy tắc Nhiệm vụ Phân loại (Task Policy):** Có chấp thuận phương án **C1 (Upstream Policy-Aware Classification)** cung cấp bảng quy chuẩn an toàn ngành trong Call 1 để bảo đảm bài toán phân loại không bị thiếu đặc tả ngữ nghĩa (under-specified) không?
8. **Lựa chọn Kiến trúc Lệnh gọi P2 (Trục A):** Project Owner lựa chọn **A2. Two Independent Calls** (tách bạch phương pháp luận cao nhất) hay **A1. One Combined Call** (tối ưu chi phí)?
9. **Lựa chọn Từ điển Nguy cơ Định vị (Trục B):** Project Owner lựa chọn phương án nào cho Grounding: **B2. Closed 12-Hazard Vocabulary** (khớp D5/D6 tất định), **B1. Open Vocabulary**, hay **B3. Hybrid**?
10. **Phê chuẩn Loại bỏ Tiêu chí Dung sai P1 Tùy tiện:** Có chấp thuận việc bỏ tiêu chí tùy tiện $\pm 1–2\%$ và thay bằng báo cáo sai số tuyệt đối kèm giải thích kỹ thuật không?
11. **Phê chuẩn Mô hình Tham chiếu P1:** Chấp thuận phương án sử dụng Claude Opus (hoặc phiên bản Claude tương thích khả dụng trên official API) và `bge-m3` cục bộ để tái lập P1 hay có chỉ đạo khác?
12. **Phê chuẩn Danh sách Mô hình P2 Cốt lõi:** Chấp thuận danh sách 4 mô hình đề xuất (`Gemini 2.5 Flash`, `Gemini 2.5 Pro`, `Qwen3-VL-8B`, `GPT-4o`) hay muốn rút gọn xuống 3 mô hình hoặc mở rộng thêm?
13. **Chính sách Mô hình Nguồn mở:** Đồng thuận việc sử dụng Hosted API thương mại (DashScope / OpenRouter) cho Qwen3-VL do hạn chế VRAM cục bộ 4 GB của máy trạm?
14. **Phê chuẩn Cấu trúc Đầu ra Chuẩn hóa:** Đồng thuận với đặc tả JSON Schema nội bộ và nguyên tắc chuyển đổi tọa độ của Adapter theo Quyết định D4?
15. **Chính sách Mô hình Chỉ Phân loại:** Tái khẳng định chính sách phân loại thuần túy: mô hình không tham gia grounding được ghi nhận `NOT PARTICIPATING`, không bị gán lỗi $\text{IoU} = 0.0$?
16. **Chính sách Chế độ Suy luận (Thinking):** Chấp thuận việc sử dụng cấu hình suy luận mặc định của nhà cung cấp (Provider Default) và cho phép áp dụng khuyến nghị kỹ thuật của Google đối với Gemini Object Detection?
17. **Chính sách Giải mã và Nhiệt độ:** Đồng thuận thiết lập `temperature = 0.0` (hoặc giá trị tối thiểu của API) cho toàn bộ các lượt chạy của P2?
18. **Chính sách Hiệu chỉnh Xác suất (Calibration):** Xác nhận xếp diện `CALIBRATION_INELIGIBLE` cho các mô hình Closed-API và cấm sử dụng độ tự tin tự thuật bằng văn bản?

---

## 34. Evidence Sources (Nguồn Bằng chứng và Tài liệu Tham chiếu)

1. **Mã nguồn và Dữ liệu Phát hành Chính thức Upstream:**
   - Kho lưu trữ Hugging Face: `https://huggingface.co/datasets/Tetrabot2026/InspecSafe-V1` (Commit `f3cb7d3e`).
   - Kho lưu trữ GitHub: `https://github.com/liuzy0708/InspecSafe`.
   - Các script kiểm toán cục bộ: `data/raw/InspecSafe-V1/model_api_generate_results.py`, `model_benchmark_evaluation.py`, `model_confusion_matrix.py`.
2. **Tài liệu Kỹ thuật Chính thức của Nhà cung cấp (Truy cập ngày 2026-09-17):**
   - Google Cloud Vertex AI / AI Studio: *"Object detection and spatial reasoning with Gemini Models"*, *"Structured Outputs Documentation"*.
   - Qwen Team / Alibaba Cloud: `QwenLM/Qwen2.5-VL` / `Qwen3-VL` Model Cards & Developer Documentation.
   - OpenAI Platform: *"Vision Guide"*, *"Structured Outputs Guide"*, *"Model Index & Deprecations"*.
   - Anthropic Developer Docs: *"Vision Capabilities"*, *"Extended Thinking Guide"*, *"Model Lifecycle"*.
3. **Hệ thống Văn bản Quyết định Nội bộ SafeShift:**
   - `DECISIONS.md`: Quyết định D1, D2, D3, D4, D5, D6, D7.
   - Báo cáo kiểm toán phương pháp luận: `notes/w1_dataset_audit.md`, `notes/research_feasibility_audit.md`, `notes/source_license_audit.md`.
   - Các Decision Brief đã duyệt: `notes/w2_protocol_decision_brief.md` (D1), `notes/w2_domain_split_decision_brief.md` (D2, D3), `notes/w2_grounding_census_decision_brief.md` (D4, D6, D7), `notes/w2_metrics_statistics_decision_brief.md` (D5).
