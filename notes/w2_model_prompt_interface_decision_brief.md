# W2.5 Model, Prompt & Interface Decision Brief

- **ID ứng viên:** DEC-W2-D8-008 (Candidate Decision Brief — D8)
- **Giai đoạn:** Week 2 — Research Protocol (W2.5)
- **Ngày audit / lập báo cáo:** 2026-09-17
- **Trạng thái:** **PROPOSED, NOT APPROVED** (Chờ Project Owner xem xét và phê duyệt; chưa ghi vào `DECISIONS.md`)
- **Phạm vi áp dụng:** Giao thức mô hình, câu lệnh chỉ dẫn (prompt), giao diện đầu ra (interface), bộ chuyển đổi (adapter), cấu hình suy luận và cơ chế bảo toàn dữ liệu cho Giao thức Tái lập Baseline (P1) và Giao thức Nghiên cứu Chính (P2) của SafeShift Seminar.

---

## 1. Purpose (Mục đích)

Mục đích của báo cáo thẩm định phương pháp luận W2.5 là:
1. **Thiết lập giao thức thực nghiệm chuẩn mực** kết nối các quyết định nền tảng đã khóa từ D1 đến D7 vào kiến trúc thực thi cụ thể của các mô hình Vision-Language Models (VLM).
2. **Khảo sát và kiểm toán độc lập năng lực thực tế** của các họ mô hình VLM ứng viên (OpenAI, Google Gemini, Qwen-VL, Anthropic Claude, Grok, v.v.) dựa trên tài liệu kỹ thuật chính thức cập nhật đến ngày **2026-09-17**, phân định rõ ràng giữa năng lực phân loại an toàn tổng quát và năng lực định vị không gian (bounding-box localization).
3. **Phân tích chi tiết quy trình tái lập baseline chính thức của InspecSafe-V1 (P1)**: phục hồi chính xác prompt, cấu hình giải mã, đường dẫn API và logic đánh giá văn bản của bài báo gốc (*Scientific Data* 2026).
4. **Xác lập nguyên tắc công bằng ngữ nghĩa (Prompt Fairness)** cho Giao thức Nghiên cứu Chính (P2): bảo đảm mọi mô hình được đánh giá trên cùng một nội dung nhiệm vụ ngữ nghĩa, nghiêm cấm việc tối ưu prompt riêng lẻ (performance prompt-tuning) cho từng mô hình.
5. **Định hình cấu trúc giao diện chuẩn hóa (Canonical Output Schema)** và đặc tả kỹ thuật cho các bộ điều hợp (Adapters) chuyển đổi tất định từ định dạng gốc của nhà cung cấp (provider native format) sang định dạng chuẩn hóa nội bộ của SafeShift theo Quyết định D4.
6. **Xác định tiêu chí đủ điều kiện (Eligibility Criteria)** cho các đường đua: phân loại an toàn 4 lớp, bám bằng chứng trực tiếp (Direct Grounding), bám bằng chứng đại diện yếu (Weak Proxy Grounding) và hiệu chỉnh xác suất (Calibration).
7. **Lập kế hoạch quản lý chi phí, kiểm soát phần cứng cục bộ, phòng ngừa nhiễm dữ liệu tiền huấn luyện và bảo toàn nguồn gốc dữ liệu (provenance)** phục vụ chuẩn bị triển khai thực nghiệm tại Week 3.

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

## 3. Upstream Baseline Audit (Kiểm toán Baseline Nghiên cứu Gốc)

Dựa trên việc kiểm tra trực tiếp mã nguồn phát hành chính thức của InspecSafe-V1 tại `data/raw/InspecSafe-V1/` và kho lưu trữ GitHub `liuzy0708/InspecSafe`:

### 3.1. Phân tích Script Sinh Kết quả (`model_api_generate_results.py`)
- **Provider & Tuyến API:**
  - Script sử dụng `BASE_URL = "https://www.dmxapi.cn/"` và `API_ENDPOINT = BASE_URL + "v1/chat/completions"`. Đây là một dịch vụ tổng hợp API proxy bên thứ ba tại Trung Quốc, sử dụng giao diện tương thích hoàn toàn với OpenAI Chat Completions API.
- **Model Name được hard-code:**
  - `MODEL_NAME = "claude-opus-4-5-20251101"`.
  - Đây là một dated snapshot của Anthropic Claude Opus (hoặc tên định danh ánh xạ nội bộ của proxy DMX). Cần lưu ý rằng trong tài liệu chính thức của Anthropic, dòng Claude Opus được định danh theo các mốc phát hành cụ thể (ví dụ `claude-3-opus-20240229`). Tên định danh `claude-opus-4-5-20251101` phản ánh cấu hình thực nghiệm tại thời điểm nhóm tác giả thu thập số liệu (cuối năm 2025).
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

### 3.2. Phân tích Script Đánh giá Tương đồng Văn bản (`model_benchmark_evaluation.py`)
- **Mô hình nhúng (Embedding Model):**
  - Sử dụng mô hình `bge-m3` (BAAI/bge-m3) chạy cục bộ thông qua máy chủ Ollama: `http://localhost:11434/api/embeddings`.
- **Model đối chiếu được cấu hình sẵn trong script:**
  - `MODEL_NAME = "grok-4.1-fast"`. Điều này chứng minh tác giả đã chạy nhiều mô hình VLM khác nhau chứ không chỉ riêng Claude Opus.
- **Quy trình tính toán:**
  - Đọc nội dung tệp `.txt` sinh bởi mô hình và tệp chú thích `.txt` chuẩn trong `test/Annotations/`.
  - Gọi Ollama embedding endpoint để lấy vector nhúng 1024 chiều.
  - Tính toán độ tương đồng Cosine: $\text{CosineSim}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2}$.
  - Tính trung bình cộng độ tương đồng trên toàn bộ các cặp tệp hợp lệ.

### 3.3. Phân tích Script Phân loại và Ma trận Nhầm lẫn (`model_confusion_matrix.py`)
- **Tập nhãn phân loại:**
  - `classes = ["level one", "level two", "level three", "no abnormalities observed", "unrecognizable"]`.
  - Gắn nhãn hiển thị: `["level Ⅰ", "level Ⅱ", "level Ⅲ", "level Ⅳ", "unrecognizable"]`.
- **Logic phân tích cú pháp (Parsing Regex / Logic):**
  - Script lấy dòng cuối cùng của tệp: `last_line = lines[-1].strip()`.
  - Nếu có dấu ngoặc đơn `(`, cắt bỏ phần sau ngoặc đơn: `last_line.split('(')[0]`.
  - Tách từ cuối cùng: `last_word = last_line.split()[-1]`.
  - Làm sạch dấu câu và ký tự thừa: `last_word.rstrip('.').strip().lower().replace('level]', '').replace(']', '')`.
  - Ánh xạ từ khóa về nhãn chuẩn qua từ điển:
    - `"observed"` $\rightarrow$ `"no abnormalities observed"`
    - `"one"` $\rightarrow$ `"level one"`
    - `"two"`, `"ii"`, `"2"` $\rightarrow$ `"level two"`
    - `"three"` $\rightarrow$ `"level three"`
    - `"unrecognizable"` $\rightarrow$ `"unrecognizable"`
  - **Xử lý từ khóa không nhận diện được:** Nếu từ cuối cùng không khớp với từ điển trên, script in cảnh báo `Warning: Unknown prediction label keyword` và mặc định gán mẫu đó vào lớp `"unrecognizable"`.
- **Đặc điểm Ground Truth đối chiếu:**
  - Ground truth thực tế trong tập test chỉ gồm 4 lớp chuẩn: Level one, Level two, Level three, no abnormalities observed. Lớp `"unrecognizable"` thuần túy là cột lỗi dự đoán của mô hình.

### 3.4. Bằng chứng Trọng yếu về Bám Bằng chứng Không gian (Grounding)
- **Kiểm toán khẳng định:** Trong toàn bộ 3 script phát hành chính thức, cũng như trong các phụ lục và bảng kết quả của bài báo InspecSafe, **HOÀN TOÀN KHÔNG CÓ BẤT KỲ PROMPT, CODE, HAY BASELINE NÀO DÀNH CHO NHIỆM VỤ GROUNDING / LOCALIZATION**.
- Toàn bộ kết quả công bố của bài báo gốc thuần túy là:
  1. *Safety Accuracy* (Phân loại 4 cấp độ an toàn).
  2. *BGE-M3 Text Similarity* (Độ tương đồng ngữ nghĩa văn bản miêu tả hiện trường).
- Do đó, **nhiệm vụ Grounding (RQ3) là đóng góp nghiên cứu mở rộng hoàn toàn độc lập và mới của SafeShift**, kế thừa đúng tinh thần Quyết định D1.

---

## 4. Current Model Landscape (Toàn cảnh Mô hình Hiện hành tính đến 2026-09-17)

Để tránh thiên kiến danh tiếng và đảm bảo tính khả thi thực chứng, cuộc kiểm toán tài liệu kỹ thuật chính thức (Official Documentation Audit) được thực hiện vào ngày **2026-09-17** trên 5 họ mô hình VLM tiêu biểu:

### 4.1. Họ Google Gemini (Google AI / Vertex AI)
- **Tài liệu kiểm toán:** Google Cloud Vertex AI & Google AI Studio official documentation, mục *"Object detection and spatial understanding with Gemini"* và *"Structured Outputs guide"*.
- **Đặc điểm năng lực:**
  - Hỗ trợ chính thức khả năng **Object Detection / 2D Spatial Grounding** dạng nguyên bản (Native Capability, **LEVEL 1 — DOC-VERIFIED**).
  - Quy chuẩn tọa độ hộp bao của Google:
    $$\mathbf{b}_{\text{gemini}} = [y_{\min}, x_{\min}, y_{\max}, x_{\max}]$$
    với tọa độ được chuẩn hóa nguyên trong thang đo $[0, 1000]$.
  - Hỗ trợ cơ chế đầu ra có cấu trúc chặt chẽ thông qua tham số `response_schema` và `response_mime_type: "application/json"` tuân thủ chuẩn JSON Schema.
  - Cung cấp các phiên bản sản xuất có định danh cố định (ví dụ dòng Flash tối ưu chi phí và dòng Pro tối ưu suy luận sâu).
  - Hỗ trợ tham số cấu hình suy luận mở rộng (Thinking mode) có thể kiểm soát linh hoạt.

### 4.2. Họ Qwen-VL (Alibaba Cloud / Open-Weight Community)
- **Tài liệu kiểm toán:** Qwen official GitHub repository (`QwenLM/Qwen2.5-VL` / `Qwen3-VL`), Model Cards trên Hugging Face, và tài liệu Alibaba Cloud DashScope API.
- **Đặc điểm năng lực:**
  - Mô hình mã nguồn mở trọng số công khai (Open-weight), phát hành dưới giấy phép cho phép nghiên cứu học thuật (Apache 2.0 / Qwen License).
  - Kiến trúc tích hợp bộ mã hóa thị giác tiên tiến hỗ trợ phân giải động (dynamic resolution) và định vị không gian 2D nguyên bản (**LEVEL 1 — DOC-VERIFIED**).
  - Quy chuẩn tọa độ: Hỗ trợ sinh trực tiếp các token định vị tọa độ hoặc xuất cấu trúc JSON với tọa độ chuẩn hóa $[0, 1000]$ dạng $[x_{\min}, y_{\min}, x_{\max}, y_{\max}]$ hoặc $[y_{\min}, x_{\min}, y_{\max}, x_{\max}]$ tùy phiên bản chat template.
  - Có các kích thước mô hình phù hợp nghiên cứu: 7B/8B (cỡ nhỏ) và 32B/72B (cỡ trung/lớn).
  - Khả dụng thông qua cả việc triển khai tự host (self-hosted via vLLM / SGLang) và các cổng Hosted API chính thức (Alibaba Cloud DashScope, OpenRouter).

### 4.3. Họ OpenAI Multimodal (OpenAI API)
- **Tài liệu kiểm toán:** OpenAI official documentation, mục *"Vision / Images"*, *"Structured Outputs"*, và *"Model lifecycle / snapshots"*.
- **Đặc điểm năng lực:**
  - Hỗ trợ tiếp nhận đầu vào đa phương thức (Text + Image URL / Base64) với độ phân giải cao (`detail: "high"` hoặc `"auto"`).
  - Khả năng phân loại an toàn và phân tích ngữ cảnh công nghiệp xuất sắc (**LEVEL 1 — DOC-VERIFIED** cho Classification).
  - Hỗ trợ cơ chế **Structured Outputs** nghiêm ngặt (`response_format: {"type": "json_schema", "strict": true}`).
  - **Tình trạng định vị không gian (Spatial Grounding):** Tài liệu chính thức của OpenAI **KHÔNG** công bố hợp đồng API định vị đối tượng nguyên bản (không có native detection head hay bảo đảm định dạng box). Mô hình chỉ xuất tọa độ khi được yêu cầu thông qua câu lệnh văn bản (**LEVEL 3 — PROMPT-ONLY**). Độ tin cậy và độ trôi dạt tọa độ cần được kiểm chứng thực nghiệm trước khi đưa vào đường đua grounding.
  - Hỗ trợ cố định phiên bản thông qua các dated model snapshots.

### 4.4. Họ Anthropic Claude (Anthropic API)
- **Tài liệu kiểm toán:** Anthropic official documentation, mục *"Vision capabilities"*, *"Extended Thinking"*, và *"Model retirement / release dates"*.
- **Đặc điểm năng lực:**
  - Là họ mô hình được sử dụng trong script phát hành chính thức của InspecSafe (`claude-opus-4-5-20251101`).
  - Hỗ trợ đầu vào ảnh Base64 với khả năng lập luận ngữ cảnh phức tạp (**LEVEL 1 — DOC-VERIFIED** cho Classification).
  - Hỗ trợ cơ chế trích xuất JSON thông qua prompt hoặc Tool Use (Function Calling).
  - **Tình trạng định vị không gian (Spatial Grounding):** Tương tự OpenAI, Anthropic không công bố hợp đồng định vị bounding box chính thức (**LEVEL 3 — PROMPT-ONLY**).
  - Cơ chế Extended Thinking cho phép điều chỉnh ngân sách token suy luận (`budget_tokens`).

### 4.5. Các họ mô hình mở rộng khác (Grok / xAI, InternVL, GLM-V)
- **Grok (xAI):** Xuất hiện trong mã nguồn đánh giá văn bản của bài báo gốc (`grok-4.1-fast`). Hỗ trợ multimodal input qua API tương thích OpenAI. Năng lực định vị không gian ở mức Prompt-only.
- **InternVL / GLM-V:** Các mô hình học thuật nguồn mở hàng đầu trong các bảng xếp hạng thị giác ngôn ngữ, có khả năng định vị tọa độ tốt, nhưng đòi hỏi tài nguyên tính toán lớn khi tự host hoặc qua các cổng API khu vực.

---

## 5. Capability Evidence Levels (Các Cấp độ Bằng chứng Năng lực)

Để bảo đảm tính nghiêm ngặt về phương pháp luận và tuân thủ Quyết định D4 (Capability-Aware Policy B), SafeShift phân định 4 cấp độ bằng chứng kỹ thuật:

| Cấp độ Bằng chứng | Định danh | Định nghĩa phương pháp luận | Ý nghĩa đối với SafeShift |
| :--- | :--- | :--- | :--- |
| **LEVEL 1** | **DOC-VERIFIED** | Năng lực được nhà cung cấp/tác giả mô hình công bố chính thức trong tài liệu kỹ thuật (official API docs, developer guides, model cards) kèm theo cam kết định dạng, hợp đồng API và ví dụ chuẩn. | Đủ điều kiện tiên quyết (Eligible) để tham gia đường đua tương ứng mà không cần suy đoán. |
| **LEVEL 2** | **MICROTEST-VERIFIED** | Năng lực không được ghi thành hợp đồng chính thức trong docs nhưng đã được nhóm nghiên cứu SafeShift kiểm chứng thực nghiệm độc lập thông qua bộ kiểm tra vi mô (Microtest Probe) trên tập mẫu kiểm chuẩn xác định. | Chuyển trạng thái từ CONDITIONALLY_ELIGIBLE sang ELIGIBLE cho đường đua tương ứng. |
| **LEVEL 3** | **PROMPT-ONLY** | Mô hình có thể xuất dữ liệu (ví dụ xuất tọa độ `[xmin, ymin, xmax, ymax]`) thuần túy do làm theo hướng dẫn ngữ nghĩa của câu prompt, nhưng nhà cung cấp không có cơ chế bảo đảm tính hợp lệ hình học hay độ chính xác không gian. | Mặc định xếp diện **DOC-UNVERIFIED / MICROTEST-REQUIRED**. Không được tự ý đưa vào đường đua Grounding nếu chưa đạt Level 2. |
| **LEVEL 4** | **UNVERIFIED** | Năng lực chưa được xác minh tài liệu, chưa có kiểm chứng thực nghiệm, hoặc tài liệu cảnh báo không hỗ trợ. | Xếp diện **INELIGIBLE** cho đường đua liên quan. |

---

## 6. Model Candidate Matrix (Bảng Ma trận Mô hình Ứng viên)

Bảng ma trận tổng hợp đánh giá sơ bộ các ứng viên VLM đại diện theo 10 tiêu chí kỹ thuật:

| Model Family / ID đại diện | Provider | Open / Closed | P1 Repro Role | P2 Class. Status | RQ3-A Direct Grounding | RQ3-B Proxy Grounding | Structured Output | BBox Evidence Level | Calibration Access | Version Pinning | Hardware Local Feas. | Trạng thái tổng quát |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `claude-opus-4-5-20251101` | DMX / Anthropic | Closed API | Primary Reference | ELIGIBLE | UNVERIFIED | UNVERIFIED | Prompted / Tool | LEVEL 3 (Prompt-Only) | INELIGIBLE (No logprobs) | Pinned Snapshot (20251101) | Cloud API Only | **ELIGIBLE (P1) / CONDITIONAL (P2 Grounding)** |
| `claude-3-7-sonnet` / `claude-3-5-sonnet` | Anthropic | Closed API | Alternate Reference | ELIGIBLE | CONDITIONALLY ELIGIBLE | CONDITIONALLY ELIGIBLE | Native Tool Use / Prompted | LEVEL 3 (Prompt-Only) | INELIGIBLE (No logprobs) | Pinned Dated IDs | Cloud API Only | **ELIGIBLE (Class.) / MICROTEST-REQ (Grounding)** |
| `gemini-2.5-flash` | Google | Closed API | Cross-Model Eval | ELIGIBLE | **ELIGIBLE** | **ELIGIBLE** | Native JSON Schema | **LEVEL 1 (Doc-Verified, [0,1000])** | INELIGIBLE (No norm logprobs) | Pinned Model IDs | Cloud API Only | **ELIGIBLE (All P2 Tracks)** |
| `gemini-2.5-pro` | Google | Closed API | Cross-Model Eval | ELIGIBLE | **ELIGIBLE** | **ELIGIBLE** | Native JSON Schema | **LEVEL 1 (Doc-Verified, [0,1000])** | INELIGIBLE (No norm logprobs) | Pinned Model IDs | Cloud API Only | **ELIGIBLE (All P2 Tracks)** |
| `qwen3-vl-8b-instruct` | Alibaba / Open | Open-Weight | Cross-Model Eval | ELIGIBLE | **ELIGIBLE** | **ELIGIBLE** | Native Chat / JSON | **LEVEL 1 (Doc-Verified, Spatial)** | **ELIGIBLE** (Self-hosted logprobs) | Git Commit / HF Hash | **LOCAL_NOT_FEASIBLE** (Hosted API Req.) | **ELIGIBLE (All P2 Tracks via Hosted API)** |
| `qwen3-vl-32b-instruct` | Alibaba / Open | Open-Weight | Extended Eval | ELIGIBLE | **ELIGIBLE** | **ELIGIBLE** | Native Chat / JSON | **LEVEL 1 (Doc-Verified, Spatial)** | **ELIGIBLE** (Self-hosted logprobs) | Git Commit / HF Hash | **LOCAL_NOT_FEASIBLE** (Hosted API Req.) | **CONDITIONALLY ELIGIBLE (Cost/Compute Scope)** |
| `gpt-4o-2024-08-06` / `gpt-5.6` candidate | OpenAI | Closed API | Cross-Model Eval | ELIGIBLE | CONDITIONALLY ELIGIBLE | CONDITIONALLY ELIGIBLE | Native JSON Schema (`strict`) | LEVEL 3 (Prompt-Only) | PARTIALLY (Token logprobs only) | Pinned Dated IDs | Cloud API Only | **ELIGIBLE (Class.) / MICROTEST-REQ (Grounding)** |
| `grok-4.1-fast` | xAI | Closed API | Secondary Reference | ELIGIBLE | UNVERIFIED | UNVERIFIED | Prompted JSON | LEVEL 3 (Prompt-Only) | INELIGIBLE (No logprobs) | API Model String | Cloud API Only | **OPTIONAL (Extended Set)** |
| `bge-m3` (Text Embedding) | BAAI | Open-Weight | P1 Text Similarity | N/A (Text-only) | N/A | N/A | Dense Vector (1024d) | N/A | N/A | HF Commit / Ollama Tag | **FEASIBLE** (Ollama Local / CPU) | **ELIGIBLE (P1 Metric Tool Only)** |

*Ghi chú quy ước trạng thái:*
- `ELIGIBLE`: Đủ điều kiện tham gia đường đua dựa trên tài liệu chính thức đã kiểm chứng (Level 1).
- `CONDITIONALLY_ELIGIBLE` / `MICROTEST-REQ`: Đủ điều kiện tham gia phân loại, nhưng cần kiểm chứng thực nghiệm vi mô (Level 2) trước khi đưa vào đường đua bám bằng chứng không gian.
- `INELIGIBLE`: Không đủ điều kiện tham gia đường đua cụ thể (ví dụ mô hình văn bản thuần túy hoặc không hỗ trợ trích xuất xác suất).
- `UNVERIFIED`: Chưa có tài liệu xác nhận và chưa thực hiện kiểm tra vi mô.

---

## 7. Local Hardware Feasibility (Kiểm toán Khả thi Phần cứng Cục bộ)

Kết quả kiểm toán thực chứng cấu hình phần cứng của máy trạm phát triển SafeShift (thực hiện lúc 16:22:00 ngày 2026-09-17):
- **Hệ điều hành:** Windows 11 x64.
- **Môi trường lập trình:** Python 3.11.9.
- **Card đồ họa (GPU):** NVIDIA GeForce GTX 1650 Ti (Laptop GPU).
- **Bộ nhớ đồ họa (VRAM):** **4.096 MiB (4 GB)**, Driver Version: 555.97, CUDA Version: 12.5.
- **Bộ nhớ hệ thống (System RAM):** 16.559.304 KB (~16 GB), Khả dụng thực tế: ~4,6 GB.
- **Không gian lưu trữ đĩa (Free Disk):** Ổ `C:` trống 97,39 GB; Ổ `D:` trống 113,19 GB.

### Đánh giá Tính Khả thi Suy luận Cục bộ (Local Inference Feasibility):
1. **Mô hình VLM Open-Weight (Qwen3-VL-8B, Qwen2.5-VL-7B, InternVL):**
   - Bộ nhớ VRAM 4 GB **HOÀN TOÀN KHÔNG ĐỦ** để tải và chạy suy luận cục bộ cho các mô hình VLM 7B–8B, ngay cả khi lượng tử hóa 4-bit (AWQ / GPTQ) vì:
     - Trọng số mô hình 8B int4 cần tối thiểu ~4,5–5,5 GB VRAM.
     - Bộ mã hóa hình ảnh (Vision Encoder / ViT) xử lý ảnh độ phân giải gốc của InspecSafe cần thêm ~1,5–3 GB VRAM cho bộ nhớ đệm ngữ cảnh và kích hoạt (activation cache).
     - Tổng dung lượng tối thiểu an toàn để chạy mượt mà một mô hình 8B VLM là **12–16 GB VRAM**.
   - **Kết luận:** Trạng thái suy luận cục bộ đối với VLM mã nguồn mở là **`LOCAL_NOT_FEASIBLE`**.
   - **Giải pháp bắt buộc:** Toàn bộ các mô hình open-weight được lựa chọn vào benchmark (như Qwen3-VL) phải được thực thi thông qua **Hosted API thương mại (Alibaba Cloud DashScope, OpenRouter)** hoặc dịch vụ điện toán đám mây theo phiên (RunPod / vLLM rented GPU server). Tuyệt đối không cố gắng ép tải trọng số lớn gây tràn bộ nhớ máy trạm.
2. **Mô hình Nhúng Văn bản Cục bộ (`bge-m3` cho P1):**
   - Mô hình `bge-m3` có kích thước ~2,2 GB (FP16) hoặc ~1,2 GB (Q4), hoàn toàn có thể chạy mượt mà trên CPU hoặc tải lên 4 GB VRAM thông qua Ollama cục bộ (`http://localhost:11434`).
   - **Kết luận:** Chạy BGE-M3 cục bộ cho P1 là **`LOCAL_FEASIBLE`**.

---

## 8. Upstream P1 Prompt (Câu lệnh Chỉ dẫn Upstream P1)

### 8.1. Trích xuất Cấu trúc Nguyên bản
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

### 8.2. Phân tích Phương pháp luận về Cấu trúc Prompt Upstream
1. **Sự hiện diện của Bảng Quy tắc Ngành (Industry Rule Table):**
   - Prompt cung cấp tường minh một bảng ma trận ánh xạ giữa Cấp độ An toàn và các loại vi phạm/nguy cơ cụ thể theo 5 ngành công nghiệp.
   - *Phân tích rò rỉ (Leakage Analysis):* Bảng này **KHÔNG PHẢI là rò rỉ dữ liệu (Data Leakage)** theo nghĩa học máy, mà chính là **Quy chuẩn Định nghĩa Nhiệm vụ (Task Specification / Domain Policy)**. Trong bối cảnh công nghiệp thực tế, hệ thống AI giám sát an toàn bắt buộc phải được nạp quy chuẩn an toàn lao động của từng phân xưởng để có thể xếp loại chính xác.
2. **Yêu cầu Mô tả Văn bản tự do:**
   - Mục `[Image Description]` yêu cầu mô tả tự do, đóng vai trò tạo ngữ cảnh sinh trước khi đưa ra nhãn `[Safety Level]` (tương tự một dạng chain-of-thought tiềm ẩn).
3. **Định dạng Đầu ra dạng Thẻ văn bản (Bracket Tags):**
   - Định dạng sử dụng các thẻ `[Image Description]` và `[Safety Level]`. Không sử dụng định dạng JSON hay XML.
4. **Chính sách Tái lập P1:**
   - Trong Giao thức P1, để bảo đảm tính so sánh công bằng với kết quả công bố trong bài báo gốc, **SafeShift bắt buộc phải giữ nguyên vẹn 100% ngữ nghĩa của câu prompt này**. Tuyệt đối không chỉnh sửa bảng quy tắc, không ép chuyển sang JSON, và không xóa bỏ phần Image Description khi chạy P1.

---

## 9. SafeShift P2 Prompt Candidates (Các Phương án Prompt P2 cho SafeShift)

Giao thức Nghiên cứu Chính (P2) đặt mục tiêu đánh giá toàn diện cả Phân loại An toàn (RQ1, RQ2) và Bám Bằng chứng Không gian (RQ3). Cần một cấu trúc prompt chuẩn mực hỗ trợ đầu ra có cấu trúc (Structured Output).

### Phương án P2-A: Kế thừa Bảng Quy tắc Upstream + Mở rộng Bounding Box (Upstream-Derived)
- Giữ nguyên toàn bộ Bảng Quy tắc 5 ngành của Upstream, nhưng thay thế phần Output Format bằng yêu cầu xuất JSON chứa `safety_level`, danh sách `hazards` và tọa độ `evidence`.
- *Ưu điểm:* Giữ tính liên tục ngữ nghĩa cao nhất với nghiên cứu gốc.
- *Nhược điểm:* Token prompt rất dài (~650 tokens văn bản), làm tăng chi phí API trên 5.013 mẫu; cấu trúc bảng Markdown phức tạp có thể gây nhiễu cho bộ giải mã JSON của một số mô hình.

### Phương án P2-B: Prompt Chuẩn hóa Gọn gàng (Simplified Canonical SafeShift Prompt — ĐƯỢC ĐỀ XUẤT)
- Chuyển tải bản chất định nghĩa 4 cấp độ an toàn và 12 nguyên tử nguy cơ thành hướng dẫn rõ ràng, cô đọng, kèm đặc tả JSON Schema trực tiếp.
- Cấu trúc đề xuất:
  1. *Role:* Chuyên gia giám sát an toàn công nghiệp độc lập.
  2. *Context & Guidelines:* Định nghĩa ngắn gọn 4 cấp độ an toàn (Level 01: Nguy cơ nghiêm trọng/thảm khốc; Level 02: Vi phạm an toàn mức trung bình; Level 03: Nguy cơ nhỏ cần lưu ý; Level 04: Hoàn toàn bình thường).
  3. *Instruction:* Yêu cầu nhận diện cấp độ an toàn tổng thể, liệt kê các nguy cơ quan sát được và định vị tọa độ hộp bao chứng cứ trực quan.
  4. *Schema Contract:* Yêu cầu xuất duy nhất một khối JSON hợp lệ theo schema chuẩn.
- *Ưu điểm:* Gọn gàng (~250–300 tokens), tiết kiệm 50% chi phí input token, giảm thiểu sai sót cú pháp, công bằng giữa các mô hình.

### Phương án P2-C: Giao thức Hai Lệnh gọi Độc lập (Two-Stage / Two-Call Protocol)
- Lệnh gọi 1: Chỉ yêu cầu phân loại an toàn và nhận diện nguy cơ (Classification & Hazard Recognition).
- Lệnh gọi 2: Đưa ra danh sách nguy cơ và yêu cầu định vị tọa độ trên ảnh (Spatial Grounding Only).
- *Ưu/Nhược điểm chi tiết được phân tích tại Mục 10 và 11.*

---

## 10. Hazard Vocabulary Policy (Chính sách Từ điển Nguy cơ)

Việc quy định cách thức mô hình gọi tên các nguy cơ trong P2 ảnh hưởng trực tiếp đến tính tự động và độ tin cậy của thuật toán ghép cặp Mode A/Mode B theo Quyết định D5:

| Phương án | Cơ chế hoạt động | Ưu điểm phương pháp luận | Nhược điểm / Rủi ro | Đánh giá Khả thi |
| :--- | :--- | :--- | :--- | :--- |
| **OPTION A: Open Vocabulary** (Từ vựng Mở) | Mô hình tự do dùng ngôn ngữ tự nhiên để mô tả nguy cơ (ví dụ: *"worker without safety hat"*, *"oil slick"*). Sau đó dùng LLM judge hoặc regex để ánh xạ về 12 hazard atoms. | Phản ánh khả năng giao tiếp mở tự nhiên của mô hình; không cung cấp gợi ý nhãn (no label hints). | Quá trình ánh xạ ngữ nghĩa (semantic mapping) tiềm ẩn tranh cãi chủ quan; tỷ lệ không nhất quán giữa các mô hình cao; khó bảo đảm tính tái lập toán học 1:1. | **KHÔNG KHUYẾN NGHỊ** cho P2 chính. (Phù hợp cho nghiên cứu định tính mở rộng). |
| **OPTION B: Closed 12-Hazard Vocabulary** (Từ điển Đóng 12 Nguy cơ) | Prompt cung cấp danh sách cố định đúng 12 định danh chuẩn đã census ở D6: `NO_GLOVES`, `NO_HELMET`, `NO_MASK`, `USE_MOBILE_PHONE`, `LIQUID_ON_GROUND`, `SMOKING`, `OPEN_FLAME`, `FOREIGN_OBJECT`, `SMOKE`, `NONMOTORIZED_VEHICLE`, `DOOR_OPEN`, `PERSON_FALLEN`. Yêu cầu mô hình chọn từ danh sách này. | **Tương thích 100% với D6 Census và D5 Metrics**. Bộ parser hoạt động tất định hoàn toàn, loại bỏ hoàn toàn mơ hồ ánh xạ; bảo đảm tính công bằng tuyệt đối trong thuật toán ghép cặp bipartite matching Mode A/B. | Cung cấp danh sách nhãn có thể đóng vai trò gợi ý (hints), làm bài toán nhận diện dễ hơn so với quan sát mù hoàn toàn. | **KHUYẾN NGHỊ CAO NHẤT CHO P2**. |
| **OPTION C: Hybrid Policy** (Chính sách Lai) | Prompt yêu cầu mô hình xuất trường `hazard_type` bắt buộc chọn từ 12 nhãn đóng, kèm trường `description` tự do giải thích ngữ cảnh chi tiết. | Kết hợp sự chặt chẽ toán học của từ điển đóng với khả năng giải thích phong phú của văn bản tự do. | Tiêu tốn thêm token đầu ra, nhưng không ảnh hưởng đến độ tất định của parser. | **ỨNG VIÊN KHẢ DĨ THAY THẾ CHO OPTION B**. |

---

## 11. Canonical Output Schema (Cấu trúc Đầu ra Chuẩn hóa Nội bộ)

Để phục vụ phân tích tự động và bảo đảm tính tương thích với Quyết định D4, SafeShift xác lập Cấu trúc Đầu ra Chuẩn hóa Nội bộ (Canonical Logical JSON Schema) cho Giao thức P2:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SafeShiftCanonicalP2Output",
  "type": "object",
  "required": ["safety_level", "hazards"],
  "properties": {
    "safety_level": {
      "type": "string",
      "enum": ["Level01", "Level02", "Level03", "Level04"],
      "description": "Canonical 4-class industrial safety assessment level."
    },
    "hazards": {
      "type": "array",
      "description": "List of observed hazard claims. Must be empty if safety_level is Level04.",
      "items": {
        "type": "object",
        "required": ["hazard_type", "evidence"],
        "properties": {
          "hazard_type": {
            "type": "string",
            "enum": [
              "NO_GLOVES",
              "NO_HELMET",
              "NO_MASK",
              "USE_MOBILE_PHONE",
              "LIQUID_ON_GROUND",
              "SMOKING",
              "OPEN_FLAME",
              "FOREIGN_OBJECT",
              "SMOKE",
              "NONMOTORIZED_VEHICLE",
              "DOOR_OPEN",
              "PERSON_FALLEN"
            ],
            "description": "Standardized hazard atom identifier from D6 census."
          },
          "evidence": {
            "type": "array",
            "description": "List of bounding boxes localizing the visual evidence. Empty if model is classification-only or cannot localize.",
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

### Nguyên tắc Phân định Rạch ròi giữa Raw Response và Parsed Output
- **Raw Model Response (Phản hồi Thô):** Toàn bộ chuỗi ký tự UTF-8 nguyên văn nhận về từ API (kể cả khối markdown ````json ... ````, khoảng trắng thừa, hoặc lỗi cú pháp) bắt buộc phải được ghi nguyên trạng vào đĩa trước khi gọi parser.
- **Parsed Canonical Output (Đầu ra Chuẩn hóa Đã phân tích):** Đối tượng dữ liệu cấu trúc Python/JSON sau khi bộ điều hợp (Adapter) đã bóc tách, chuẩn hóa nhãn và chuyển đổi hệ tọa độ.

---

## 12. Model-Specific Adapters (Các Bộ Chuyển đổi Đặc thù theo Mô hình)

Theo Quyết định D4, không bắt buộc nhà cung cấp phải xuất đúng quy chuẩn tọa độ nội bộ của SafeShift nếu mô hình của họ có quy ước bản địa (native convention) khác. Việc chuẩn hóa là trách nhiệm của **Adapter tất định**:

### 12.1. Google Gemini Adapter
- **Native Convention:** Google Gemini xuất mảng tọa độ 4 phần tử theo thứ tự:
  $$\mathbf{b}_{\text{gemini}} = [y_{\min}, x_{\min}, y_{\max}, x_{\max}], \quad \text{với } y, x \in [0, 1000] \text{ (số nguyên)}$$
- **Công thức chuyển đổi tất định sang Canonical:**
  $$x_{\min} = \text{clamp}\left(\frac{\mathbf{b}_{\text{gemini}}[1]}{1000.0}, 0.0, 1.0\right), \quad y_{\min} = \text{clamp}\left(\frac{\mathbf{b}_{\text{gemini}}[0]}{1000.0}, 0.0, 1.0\right)$$
  $$x_{\max} = \text{clamp}\left(\frac{\mathbf{b}_{\text{gemini}}[3]}{1000.0}, 0.0, 1.0\right), \quad y_{\max} = \text{clamp}\left(\frac{\mathbf{b}_{\text{gemini}}[2]}{1000.0}, 0.0, 1.0\right)$$
  *(Kèm kiểm tra tính hợp lệ hình học: $x_{\max} \ge x_{\min}$ và $y_{\max} \ge y_{\min}$)*.

### 12.2. Qwen-VL Adapter
- **Native Convention:** Tùy thuộc vào chế độ gọi API (Chat format hoặc Function format), Qwen-VL có thể xuất thẻ đặc biệt `<|box_start|>(ymin,xmin),(ymax,xmax)<|box_end|>` hoặc đối tượng JSON với tọa độ $[0, 1000]$.
- **Công thức chuyển đổi:** Adapter sử dụng biểu thức chính quy (Regex) tất định để trích xuất 4 số nguyên, hoán đổi vị trí $y \leftrightarrow x$ nếu ở dạng $y$-first, và chia cho $1000.0$ để đưa về đoạn $[0.0, 1.0]$.

### 12.3. OpenAI / Claude Adapter
- **Native Convention:** Mô hình được yêu cầu trực tiếp qua prompt xuất định dạng JSON với mảng `[xmin, ymin, xmax, ymax]` trong đoạn $[0.0, 1.0]$.
- **Nhiệm vụ của Adapter:** Kiểm tra tính hợp lệ của mảng 4 số thực, kẹp giá trị (clamp) vào đoạn $[0.0, 1.0]$, và xác minh $x_{\min} \le x_{\max}, y_{\min} \le y_{\max}$. Nếu tọa độ không hợp lệ, gắn cờ lỗi parse hộp bao (`box_parse_error = True`).

### 12.4. Yêu cầu Kiểm thử Đơn vị (Unit Test Contract)
Mọi Adapter khi được cài đặt ở Week 3 bắt buộc phải vượt qua bộ kiểm thử đơn vị với các ca kiểm thử cố định:
1. Chuyển đổi đúng tọa độ cực biên ($[0, 0, 1000, 1000] \rightarrow [0.0, 0.0, 1.0, 1.0]$).
2. Hoán vị chính xác thứ tự $y$-first sang $x$-first.
3. Xử lý an toàn các giá trị vượt biên nhẹ do làm tròn (ví dụ $1001 \rightarrow 1.0$).
4. Báo lỗi tất định khi mảng tọa độ bị thiếu phần tử hoặc chứa chuỗi không phải số.

---

## 13. Grounding Eligibility (Tiêu chuẩn Đủ Điều kiện Tham gia Bám Bằng chứng)

Tuân thủ Quyết định D4 (Capability-Aware Policy B), việc xác lập quyền tham gia đường đua bám bằng chứng không gian được phân định như sau:

1. **Đủ điều kiện trực tiếp (Eligible):**
   - Mô hình có tài liệu kỹ thuật chính thức xác nhận hỗ trợ xuất tọa độ hộp bao định vị đối tượng với hợp đồng cụ thể (LEVEL 1 — DOC-VERIFIED).
   - *Ứng viên hiện tại:* **Google Gemini** (Gemini 2.5 Flash / Pro) và **Qwen-VL** (Qwen3-VL-8B / 32B).
2. **Đủ điều kiện có điều kiện (Conditionally Eligible / Microtest-Required):**
   - Mô hình hỗ trợ nhập ảnh và có thể xuất tọa độ theo prompt nhưng tài liệu không có API contract chuyên trách (LEVEL 3 — PROMPT-ONLY).
   - *Ứng viên hiện tại:* **OpenAI** (GPT-4o / GPT-5.6 candidate) và **Anthropic Claude** (Claude 3.5 / 3.7 Sonnet).
   - *Điều kiện mở khóa:* Bắt buộc phải vượt qua bài kiểm tra vi mô thăm dò năng lực (Capability Probe Microtest trên 5–10 ảnh kiểm chuẩn, xem Mục 24) với tỷ lệ parse tọa độ hợp lệ $\text{PSR}_{\text{box}} \ge 80\%$.
3. **Không đủ điều kiện (Ineligible):**
   - Các mô hình thuần văn bản hoặc các mô hình thị giác không có khả năng xuất tọa độ.

---

## 14. Classification-Only Policy (Chính sách Mô hình Chỉ Tham gia Phân loại)

Để bảo đảm tính công bằng khoa học và bảo vệ các mô hình có thế mạnh phân loại nhưng không được huấn luyện chuyên sâu cho định vị không gian:
1. **Tham gia trọn vẹn Track Phân loại:** Mô hình chỉ tham gia phân loại vẫn được đánh giá đầy đủ trên toàn bộ 5.013 mẫu của P2 cho các chỉ số phân loại an toàn 4 lớp (Balanced Accuracy, Macro-F1), sai số an toàn trọng yếu (Track A, Track B), và phân tầng nguy cơ RQ2.
2. **Trạng thái chính thức trong Track RQ3 (Grounding):**
   - Trạng thái được ghi nhận là: **`NOT PARTICIPATING` (Không tham gia)**.
   - **Tuyệt đối không gán nhãn:** `GROUNDING_FAILURE` (Thất bại bám bằng chứng) hay `IoU = 0.0`.
   - Các mô hình này bị loại hoàn toàn khỏi mẫu số và bảng xếp hạng của RQ3-A (Direct Grounding) và RQ3-B (Proxy Grounding).
   - Tuyệt đối không tính điểm trung bình tổng hợp gộp cả phân loại lẫn grounding để xếp hạng chung cuộc giữa các mô hình khác nhau về bản chất năng lực.

---

## 15. Reasoning / Thinking Policy (Chính sách Chế độ Suy luận / Thinking)

Các họ mô hình VLM hiện đại sở hữu các cơ chế suy luận mở rộng (Extended Thinking / Reasoning) rất đa dạng. Cần một chính sách kiểm soát để bảo đảm tính công bằng:

| Phương án | Mô tả cơ chế | Ưu điểm phương pháp luận | Nhược điểm / Rủi ro | Đánh giá Khả thi |
| :--- | :--- | :--- | :--- | :--- |
| **Phương án 1: Tắt hoàn toàn Thinking** (`thinking_budget = 0` / disable) | Ép tất cả các mô hình tắt chế độ suy luận mở rộng, chỉ thực hiện giải mã trực tiếp (direct greedy/sampling). | Giảm chi phí token tối đa; tạo điểm xuất phát đồng nhất cho bài toán suy luận zero-shot nhanh. | Một số mô hình suy luận chuyên sâu (như dòng OpenAI o-series) không cho phép tắt hoàn toàn reasoning; có thể làm suy giảm nghiêm trọng năng lực đọc hiểu các bảng quy tắc an toàn phức tạp. | **KHẢ THI VỚI MÔ HÌNH HỖ TRỢ**, nhưng không áp dụng đồng nhất được cho mọi họ mô hình. |
| **Phương án 2: Sử dụng Cấu hình Mặc định của Nhà cung cấp** (Provider Default) | Sử dụng cấu hình mặc định (default thinking / standard reasoning) do nhà cung cấp tối ưu hóa cho từng model snapshot. | Phản ánh đúng năng lực nguyên bản của mô hình theo khuyến nghị của nhà sản xuất; không can thiệp cưỡng bức vào cơ chế nội tại. | Mức độ nỗ lực suy luận (reasoning effort) có thể không đồng đều giữa các mô hình (ví dụ một mô hình "suy nghĩ" 1.000 tokens trong khi mô hình khác không có). | **KHUYẾN NGHỊ CAO NHẤT (Thực tế và minh bạch)**. |
| **Phương án 3: Chuẩn hóa Ngân sách Suy luận Cố định** (Fixed Token Budget) | Ép một mức ngân sách token suy luận cố định (ví dụ `budget_tokens = 1024`) cho mọi mô hình hỗ trợ. | Kiểm soát đồng nhất về mặt tài nguyên suy luận. | Các nhà cung cấp định nghĩa token suy luận và phân bổ nỗ lực khác nhau; nhiều API không hỗ trợ tham số này. | Không khả thi trên diện rộng. |

### Lưu ý Đặc thù về Google Gemini Object Detection
- Tài liệu kỹ thuật của Google Gemini lưu ý rằng đối với tác vụ phát hiện đối tượng (Object Detection), việc kích hoạt quá nhiều token suy luận văn bản đôi khi có thể làm suy giảm độ chính xác tọa độ do hiện tượng trôi dạt chú ý không gian.
- Do đó, nếu tài liệu chính thức của Google khuyến nghị cấu hình thinking tối ưu cho tác vụ định vị (ví dụ `thinking_budget = 0` hoặc low effort), SafeShift coi đây là **Cấu hình Wrapper Cần thiết theo Khuyến cáo Kỹ thuật (Capability-Required Wrapper Configuration)**, hoàn toàn không phải là hành vi tinh chỉnh prompt thiên vị (no performance prompt-tuning). Mọi cấu hình này phải được ghi nhận công khai trong run metadata.

---

## 16. Decoding Policy (Chính sách Giải mã và Nhiệt độ)

### 16.1. Đối với Giao thức Tái lập P1
- Bắt buộc tuân thủ đúng cấu hình đã được ghi nhận trong mã nguồn phát hành chính thức của bài báo gốc:
  - `temperature = 0.1`.
  - Không truyền các tham số lấy mẫu ngẫu nhiên không có trong script gốc.

### 16.2. Đối với Giao thức Nghiên cứu Chính P2
- Mục tiêu phương pháp luận của SafeShift là đánh giá năng lực bền vững nội tại, do đó ưu tiên giải mã tất định hoặc có phương sai thấp nhất (**Low-Variance / Deterministic Decoding**):
  - **Khuyến nghị chính:** Thiết lập `temperature = 0.0` (hoặc mức tối thiểu mà API cho phép, ví dụ `0.0` trên OpenAI/Anthropic/Google).
  - Khóa giá trị `seed` nếu API hỗ trợ (ví dụ `seed = 42` trên OpenAI API).
  - *Cảnh báo phương pháp luận bắt buộc:* **Tuyệt đối không tuyên bố `temperature = 0` đồng nghĩa với tính tất định số học tuyệt đối 100%**, vì các hạ tầng phục vụ mô hình ngôn ngữ lớn sử dụng thuật toán song song hóa trên GPU (non-deterministic floating-point summation / mixture-of-experts routing) có thể tạo ra biến thiên ngẫu nhiên nhỏ ở mức bit.
  - Mọi tham số giải mã thực tế (`temperature`, `top_p`, `top_k`, `seed`, `max_output_tokens`) bắt buộc phải được ghi nhận đầy đủ trong metadata của từng lệnh gọi.

---

## 17. Structured Output & Parse Policy (Chính sách Đầu ra Có Cấu trúc và Phân tích Cú pháp)

### 17.1. Phân loại Cơ chế Xuất Cấu trúc
1. **Native JSON Schema Mode:** API hỗ trợ tham số cấu trúc cấp hệ thống (OpenAI `response_format: json_schema`, Gemini `response_schema`). Đây là cơ chế bền vững nhất, bảo đảm đầu ra tuân thủ 100% cú pháp JSON hợp lệ.
2. **Tool / Function Calling Mode:** Mô hình xuất cấu trúc thông qua cơ chế gọi hàm giả định (Anthropic Tools). Độ bền cú pháp cao.
3. **Prompted JSON Mode:** Mô hình thuần túy làm theo hướng dẫn xuất JSON trong câu prompt văn bản. Dễ gặp lỗi cú pháp (thiếu dấu ngoặc, xuất thừa khối markdown ````json ... ````).

### 17.2. Chính sách Xử lý Lỗi Phân tích Cú pháp (Parse-Failure Policy)
Kế thừa Quyết định D5, SafeShift xử lý lỗi phân tích cú pháp theo nguyên tắc minh bạch hai lớp:
1. **Lớp Đo lường Độ bền Cú pháp (Diagnostic PSR):**
   - Báo cáo **Tỷ lệ Phân tích Phản hồi Thành công:**
     $$\text{PSR}_{\text{response}} = \frac{\text{Số phản hồi parse thành công JSON và có trường safety\_level hợp lệ}}{N_{\text{total\_requests}}}$$
   - Báo cáo **Tỷ lệ Phân tích Tọa độ Hộp bao Hợp lệ:**
     $$\text{PSR}_{\text{box}} = \frac{\text{Số hộp bao có đúng 4 tọa độ thực hợp lệ trong } [0.0, 1.0]}{\text{Tổng số hộp bao mô hình sinh ra}}$$
2. **Lớp Đánh giá Hiệu năng Thực nghiệm:**
   - **End-to-End Grounding:** Mọi phản hồi lỗi cú pháp không trích xuất được tọa độ, hoặc tọa độ vượt biên không thể sửa chữa, đều được gán điểm $\text{IoU} = 0.0$ cho toàn bộ các nguy cơ liên quan trong mẫu đó.
   - **Parse-Conditional Diagnostic:** Báo cáo phụ trợ chỉ số IoU trung bình tính riêng trên các trường hợp parse thành công để phân lập giữa năng lực hiểu cú pháp và năng lực định vị không gian.

---

## 18. Calibration Eligibility (Tính Đủ Điều kiện Đánh giá Độ Hiệu chỉnh Xác suất)

Theo Quyết định D5, độ hiệu chỉnh xác suất (Calibration: ECE, Brier Score) là chỉ số phụ thuộc năng lực đặc thù (`Capability-Specific`):

### 18.1. Kiểm toán Khả năng Truy cập Xác suất
1. **Closed-API Models (OpenAI, Google Gemini, Anthropic Claude):**
   - Các API thương mại hiện nay nhìn chung **KHÔNG cung cấp phân bố xác suất phân loại chuẩn hóa (Normalized Softmax Probabilities)** trên toàn bộ không gian 4 lớp an toàn.
   - OpenAI chỉ cung cấp `logprobs` cho một số token hàng đầu tại vị trí sinh, nhưng giá trị này phụ thuộc vào chuỗi token hóa (tokenization artifacts) và tiền điều kiện của toàn bộ văn bản sinh trước đó, không tương đương với $P(\text{Level} \mid \text{Image})$.
   - Google Gemini và Anthropic Claude không cung cấp logprobs đầy đủ cho tác vụ sinh JSON có cấu trúc.
2. **Open-Weight Models (Qwen-VL tự host):**
   - Có thể trích xuất trực tiếp logit của các token tương ứng với các lớp an toàn để tính softmax chuẩn xác.

### 18.2. Quy tắc Cấm Tuyệt đối
- **TUYỆT ĐỐI CẤM SỬ DỤNG ĐỘ TỰ TIN TỰ THUẬT (Self-Reported Textual Confidence):** Nghiêm cấm việc yêu cầu mô hình tự viết ra câu văn như `"confidence: 95%"` hoặc `"probability: 0.9"` để làm đại diện cho xác suất hiệu chuẩn. Hiện tượng tự tin thái quá (overconfidence) và ảo giác số học trong văn bản tự sinh đã được y văn chứng minh là không có giá trị thống kê.
- **Phán quyết:** Ngoại trừ trường hợp có mô hình mở tự trích xuất logit, toàn bộ các mô hình Closed-API được phân loại là **`CALIBRATION_INELIGIBLE`**. Calibration không tham gia vào bảng chỉ số so sánh chính xuyên mô hình của SafeShift Seminar.

---

## 19. Version Pinning & Provenance (Cố định Phiên bản và Truy vết Nguồn gốc)

Để ngăn chặn hiện tượng trôi dạt mô hình (Model Drift) làm phá vỡ tính tái lập của nghiên cứu khoa học, mọi lần chạy thực nghiệm ở Week 3 bắt buộc phải tuân thủ chính sách cố định phiên bản nghiêm ngặt:

### 19.1. Bảng Siêu dữ liệu Bắt buộc Lưu trữ (Mandatory Execution Metadata)
Mỗi tệp kết quả thực nghiệm (cho từng mẫu ảnh hoặc từng batch) bắt buộc phải gắn kèm đối tượng siêu dữ liệu:
- `protocol_id`: `"P1_BASELINE_REPLICATION"` hoặc `"P2_PRIMARY_RESEARCH"`.
- `run_id`: Định danh duy nhất của lần chạy (UUIDv4 kèm timestamp ISO 8601).
- `sample_id`: Định danh mẫu ảnh chuẩn (ví dụ `oil_chemical-Level01-SuspendedRail-000101-001`).
- `image_sha256`: Mã băm SHA-256 của tệp ảnh đầu vào để bảo đảm toàn vẹn dữ liệu.
- `provider`: Tên nhà cung cấp dịch vụ (`google`, `openai`, `anthropic`, `alibaba`, `local_ollama`).
- `model_family`: Tên họ mô hình (`gemini`, `gpt`, `claude`, `qwen`).
- `requested_model_id`: Chuỗi định danh mô hình được gửi trong API request.
- `resolved_model_version`: Phiên bản cụ thể thực tế được nhà cung cấp phản hồi trong header/body (nếu có).
- `api_endpoint_url`: Đường dẫn endpoint thực tế (che giấu secret).
- `sdk_version`: Phiên bản thư viện client sử dụng (ví dụ `google-genai==1.2.0`, `openai==1.50.0`).
- `prompt_template_id`: Mã định danh mẫu prompt (ví dụ `P1_UPSTREAM_V1`, `P2_CANONICAL_V1`).
- `prompt_sha256`: Mã băm SHA-256 của toàn văn chuỗi prompt gửi đi.
- `decoding_parameters`: Từ điển tham số (`temperature`, `top_p`, `seed`, `thinking_config`, v.v.).
- `request_timestamp_utc`: Thời điểm gửi request chuẩn UTC.
- `latency_seconds`: Thời gian phản hồi tính bằng giây.
- `raw_response_id`: Định danh duy nhất của response từ nhà cung cấp (ví dụ `chatcmpl-...`).
- `adapter_version`: Phiên bản bộ chuyển đổi được sử dụng để parse.

### 19.2. Chính sách đối với Bí danh Động (Moving Aliases)
- Nghiêm cấm việc sử dụng các bí danh động không cố định thời gian (như `gpt-4o-latest`, `claude-3-5-sonnet-latest`, `gemini-flash`).
- Bắt buộc phải sử dụng các định danh có gắn ngày hoặc phiên bản cố định (dated snapshot, ví dụ `gpt-4o-2024-08-06`, `gemini-2.5-flash-001`, `claude-3-5-sonnet-20241022`).
- Nếu nhà cung cấp chỉ hỗ trợ bí danh động, bắt buộc phải ghi lại `resolved_model_version` trả về trong response header và đánh dấu cờ cảnh báo `moving_alias = True`.

---

## 20. Cost & Runtime Feasibility (Phân tích Chi phí và Thời gian Thực thi)

Bảng ước tính chi phí và thời lượng tính toán dựa trên biểu giá công khai của các nhà cung cấp (cập nhật ngày 2026-09-17) cho hai giao thức thực nghiệm:

### 20.1. Giả định Kỹ thuật Ước tính
- **Kích thước đầu vào:** 1 ảnh trung bình của InspecSafe tương đương ~1.000–1.600 visual tokens (tùy thuộc vào tile resolution của từng nhà cung cấp) + ~300 tokens prompt văn bản $\approx$ **1.500 input tokens / request**.
- **Kích thước đầu ra:** JSON phản hồi gồm cấp an toàn, danh sách nguy cơ và tọa độ hộp bao $\approx$ **200–400 output tokens / request**.
- **Quy mô mẫu:**
  - P1 Replication: **1.250 ảnh** $\approx$ ~1,9 triệu input tokens + ~0,4 triệu output tokens.
  - P2 Primary Protocol: **5.013 ảnh** $\approx$ ~7,5 triệu input tokens + ~1,5 triệu output tokens.

### 20.2. Bảng Ước tính Ngân sách Chi phí (Đơn vị: USD)

| Mô hình Ứng viên | Biểu giá Input (USD/1M tokens) | Biểu giá Output (USD/1M tokens) | Chi phí Ước tính P1 (1.250 ảnh) | Chi phí Ước tính P2 (5.013 ảnh) | Thời gian chạy ước tính (ở tốc độ 2 req/s) | Khả thi Ngân sách Seminar |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Google Gemini 2.5 Flash** | \$0.10 | \$0.40 | ~\$0.35 | ~\$1.35 | ~42 phút | **CỰC KỲ KHẢ THI** (< \$5) |
| **Google Gemini 2.5 Pro** | \$1.25 | \$5.00 | ~\$4.35 | ~\$16.80 | ~60 phút | **RẤT KHẢ THI** (< \$20) |
| **Qwen3-VL-8B** (Hosted API) | ~\$0.20 | ~\$0.60 | ~\$0.60 | ~\$2.40 | ~45 phút | **CỰC KỲ KHẢ THI** (< \$5) |
| **OpenAI GPT-4o** (Snapshot) | \$2.50 | \$10.00 | ~\$8.75 | ~\$33.75 | ~50 phút | **KHẢ THI** (~ \$35) |
| **Claude 3.5 / 3.7 Sonnet** | \$3.00 | \$15.00 | ~\$11.70 | ~\$45.00 | ~55 phút | **KHẢ THI** (~ \$45) |
| **Claude Opus 4.5** (P1 Ref) | ~\$15.00 | ~\$75.00 | ~\$58.50 | N/A (Chỉ chạy P1) | ~60 phút | **KHẢ THI TRONG P1** (~ \$60) |
| **BGE-M3 (Ollama Local)** | \$0.00 (Local) | \$0.00 (Local) | \$0.00 | N/A (Chỉ chạy P1) | ~15 phút | **HOÀN TOÀN MIỄN PHÍ** |

### 20.3. Nhận định Tổng quát về Ngân sách
- Một bộ thí nghiệm tối thiểu gồm **4 mô hình đại diện cho P2** (ví dụ: Gemini 2.5 Flash + Gemini 2.5 Pro + Qwen3-VL-8B + GPT-4o) chỉ tiêu tốn tổng ngân sách khoảng **\$50 – \$60 USD** cho toàn bộ 5.013 ảnh.
- Toàn bộ ngân sách hoàn toàn nằm trong khả năng hỗ trợ nghiên cứu của đề tài Seminar, không có rào cản tài chính nghiêm trọng.

---

## 21. Pretraining Contamination Caveat (Cảnh báo Nhiễm Dữ liệu Tiền Huấn luyện)

### 21.1. Bối cảnh Thực tế về Thời gian
- Bộ dữ liệu InspecSafe-V1 được tải lên Hugging Face và xuất bản bản thảo arXiv:2601.21173 vào **tháng 01/2026**; bài báo chính thức xuất bản trên *Scientific Data* vào **tháng 03/2026**.
- Ngày audit hiện tại là **2026-09-17**. Đã có khoảng thời gian ~8 tháng kể từ khi dữ liệu được công khai trên Internet.

### 21.2. Bảng Đánh giá Nguy cơ Nhiễm Dữ liệu cho Từng Họ Mô hình

| Model Family | Mốc Kiến thức Công bố (Knowledge Cutoff) | Ngày Phát hành Snapshot | Tình trạng Nhiễm Dữ liệu Tiền Huấn luyện | Bằng chứng / Cơ sở Đánh giá |
| :--- | :--- | :--- | :--- | :--- |
| **Claude Opus 4.5** (`20251101`) | Tháng 10/2025 (hoặc cuối 2025) | 2025-11-01 | **UNLIKELY (Ít khả năng)** | Snapshot mang ngày 2025-11-01, trước thời điểm dataset InspecSafe-V1 được đưa lên Hugging Face và arXiv (tháng 01/2026). |
| **OpenAI GPT-4o** (`2024-08-06`) | Tháng 10/2023 | 2024-08-06 | **UNLIKELY (Rất ít khả năng)** | Snapshot được đóng băng vào tháng 08/2024, cách thời điểm công bố dữ liệu hơn 1 năm. |
| **Google Gemini 2.5 Series** | Giữa năm 2025 – đầu 2026 | Đầu/Giữa 2026 | **PLAUSIBLE (Có thể xảy ra)** | Các mô hình huấn luyện hoặc cập nhật vào năm 2026 có khả năng đã thu thập các tệp dữ liệu hoặc bài báo công khai từ Zenodo/GitHub/Hugging Face. |
| **Qwen3-VL Series** | Đầu/Giữa 2026 | Năm 2026 | **PLAUSIBLE (Có thể xảy ra)** | Tương tự, dữ liệu web công khai năm 2026 có thể chứa một phần hình ảnh hoặc tài liệu liên quan đến InspecSafe. |
| **Các mô hình đóng khác** | Không công bố chi tiết | Liên tục cập nhật | **UNKNOWN (Không xác định)** | Nhiều nhà cung cấp không công bố chi tiết danh sách URL web scrape trong tập huấn luyện. |

### 21.3. Quy tắc Phát biểu Khoa học Bắt buộc
1. **Tuyệt đối không đưa ra khẳng định chắc chắn:** Không bao giờ tuyên bố trong báo cáo rằng *"mô hình A chắc chắn chưa từng nhìn thấy dữ liệu InspecSafe"* hoặc ngược lại *"mô hình B đã học vẹt toàn bộ dữ liệu"*.
2. **Bản chất của SafeShift:** SafeShift được định nghĩa là **Benchmark Đánh giá Thực nghiệm (Empirical Benchmark Evaluation)** trên các mô hình đóng băng trọng số có sẵn trên thị trường. Nhiễm dữ liệu tiền huấn luyện là một biến số ngoại sinh không thể kiểm soát tuyệt đối đối với các mô hình thương mại đóng. Mọi báo cáo kết quả bắt buộc phải công bố mục giới hạn này.

---

## 22. P1 Reproduction Plan (Kế hoạch Thực hiện Giao thức Tái lập Baseline P1)

### 22.1. Mục tiêu
Tái lập trung thực và kiểm chứng các số liệu baseline công bố trong bài báo gốc của InspecSafe trên đúng **1.250 mẫu test chính thức**.

### 22.2. Các Bước Triển khai Chi tiết
1. **Bước 1: Chuẩn bị Môi trường Cục bộ:**
   - Khởi chạy dịch vụ Ollama cục bộ với mô hình `bge-m3`: `ollama run bge-m3`.
   - Kiểm tra kết nối endpoint: `http://localhost:11434/api/embeddings`.
2. **Bước 2: Chuẩn bị Dữ liệu Đầu vào:**
   - Sử dụng đúng 1.250 ảnh thuộc `test/Annotations/` (gồm 999 Normal và 251 Anomaly).
   - Kiểm tra mã băm xác thực tính toàn vẹn của tập test.
3. **Bước 3: Thực thi Sinh Kết quả Phân loại:**
   - Sử dụng nguyên văn câu prompt Upstream P1 (Mục 8.1).
   - Gửi yêu cầu tới mô hình tham chiếu upstream (`claude-opus-4-5-20251101` hoặc mô hình thay thế tương thích nếu snapshot gốc không thể truy cập).
   - Cấu hình giải mã: `temperature = 0.1`.
   - Lưu toàn bộ 1.250 tệp phản hồi văn bản thô vào `data/raw/p1_reproduction/{model_name}/`.
4. **Bước 4: Đánh giá Điểm số Baseline:**
   - Chạy script tính toán tương đồng ngữ nghĩa văn bản BGE-M3 (so sánh với tệp mô tả chuẩn của tác giả).
   - Chạy script phân loại an toàn và tính toán Safety Accuracy, Macro-F1, và ma trận nhầm lẫn theo logic parsing gốc.
5. **Bước 5: Phân loại Trạng thái Tái lập:**
   - Báo cáo rõ ràng kết quả theo 3 cấp độ:
     - `REPRODUCIBLE`: Nếu kết quả số học sai khác trong phạm vi dung sai ngẫu nhiên ($\pm 1–2\%$).
     - `PARTIALLY_REPRODUCIBLE`: Nếu xu hướng tương đồng nhưng có sự sai lệch đáng kể do trôi dạt phiên bản API.
     - `NOT_EXACTLY_REPRODUCIBLE`: Nếu mô hình tham chiếu gốc không thể gọi được và phải dùng mô hình tương thích thay thế (`Compatibility Reproduction`).

---

## 23. P2 Research Run Plan (Kế hoạch Thực hiện Giao thức Nghiên cứu Chính P2)

### 23.1. Mục tiêu
Thực thi đánh giá độ bền vững xuyên miền (RQ1), phân tầng nguy cơ (RQ2), và tính nhất quán phân loại – bám bằng chứng không gian (RQ3) trên toàn bộ **5.013 mẫu ảnh** của SafeShift.

### 23.2. Quy trình Thực thi Chuẩn hóa
1. **Bước 1: Nạp Manifest Dữ liệu Chuẩn:**
   - Nạp `data/manifests/dataset_manifest.csv` (5.013 mẫu) kèm đầy đủ siêu dữ liệu `folder_domain`, `split`, `point_id`, và cờ `domain_mismatch`.
2. **Bước 2: Gói Payload Đồng nhất:**
   - Sử dụng Mẫu Prompt Chuẩn hóa P2 (Canonical SafeShift Prompt) với từ điển đóng 12 nguy cơ (Option B).
   - Mã hóa ảnh theo yêu cầu kỹ thuật của từng API (Base64 hoặc Image URL).
3. **Bước 3: Thực thi Suy luận theo Lô (Batching & Rate-Limiting):**
   - Thiết lập cơ chế kiểm soát tốc độ (Rate-limiter) và thử lại khi gặp lỗi mạng (Exponential Backoff Retry) để tránh lỗi hạn chế lưu lượng (HTTP 429).
   - Thiết lập `temperature = 0.0` (hoặc provider minimum).
4. **Bước 4: Lưu trữ Raw Outputs Bất biến:**
   - Ghi nhận nguyên văn phản hồi thô vào cấu trúc lưu trữ:
     `outputs/raw_runs/P2/{model_id}/{run_id}/{sample_id}.json`
     kèm toàn bộ siêu dữ liệu truy vết quy định tại Mục 19.
5. **Bước 5: Chuyển đổi Tất định qua Adapter:**
   - Áp dụng Adapter đặc thù cho từng mô hình để trích xuất `safety_level`, chuẩn hóa nhãn `hazard_type`, và chuyển đổi tọa độ hộp bao về hệ chuẩn nội bộ $[x_{\min}, y_{\min}, x_{\max}, y_{\max}] \in [0.0, 1.0]$.
6. **Bước 6: Tính toán Chỉ số và Thống kê:**
   - Nạp các tệp kết quả chuẩn hóa vào động cơ đánh giá metric đã được phê chuẩn tại Quyết định D5:
     - Tính Balanced Accuracy, Macro-F1, FNR/FPR Track A & B.
     - Tính Class-Conditional Domain Analysis cho RQ1.
     - Tính 4 chỉ số an toàn trên 7 tầng nguy cơ gom nhóm cho RQ2.
     - Tính End-to-End Mean IoU, Median IoU (Mode A) và Hit@0.25, Hit@0.50, Evidence F1 (Mode B) cho RQ3-A (Direct Grounding trên 781 atoms).
     - Tính Identity-Agnostic PLC cho RQ3-B (Proxy Grounding trên 947 atoms).
     - Tính toán chỉ số không nhất quán $\text{CGI}@\tau$.
   - Thực thi Domain-Stratified Point-Cluster Bootstrap ($B=2.000$ lượt) để xuất khoảng tin cậy 95% và chạy Paired Bootstrap Difference CI 95% so sánh giữa các mô hình.

---

## 24. Capability Probe Plan (Kế hoạch Thử nghiệm Vi mô Năng lực Sơ bộ)

Để xác minh thực nghiệm các mô hình ở diện `LEVEL 3 (Prompt-Only)` (như OpenAI GPT-4o hoặc Claude 3.5 Sonnet) có đủ điều kiện tham gia đường đua Grounding hay không, một quy trình thử nghiệm vi mô (Capability Probe) được thiết kế sẵn:

### 24.1. Quy tắc Tuyệt đối
- **KHÔNG CHẠY TRÊN PAID API TRƯỚC KHI ĐƯỢC PHÊ DUYỆT:** Kế hoạch này là tài liệu thiết kế phương pháp luận; tuyệt đối không tự ý gọi API có tính phí trong bước W2.5.
- Chỉ thực hiện sau khi Project Owner phê chuẩn và cấp phép rõ ràng.

### 24.2. Thiết kế Tập Mẫu Thử nghiệm Vi mô (Microtest Probe Set)
Chọn một tập con cực nhỏ gồm đúng **8 mẫu ảnh đại diện** từ tập dữ liệu (bao phủ các đặc trưng không gian và mức độ phức tạp khác nhau):
1. *Mẫu 1 (Vật thể nhỏ đơn lẻ):* `USE_MOBILE_PHONE` (Điện thoại di động trên tay công nhân).
2. *Mẫu 2 (Vật thể phát sáng/nhiệt):* `OPEN_FLAME` (Ngọn lửa trần).
3. *Mẫu 3 (Khói lan tỏa, ranh giới mờ):* `SMOKE` (Khói bốc lên từ thiết bị).
4. *Mẫu 4 (Vùng bề mặt phẳng):* `LIQUID_ON_GROUND` (Vũng nước / dầu tràn trên sàn).
5. *Mẫu 5 (Dị vật cơ học):* `FOREIGN_OBJECT` (Chai nhựa / túi rác trên băng chuyền).
6. *Mẫu 6 (Xe cộ kích thước lớn):* `NONMOTORIZED_VEHICLE` (Xe ba bánh / xe đạp trong hầm).
7. *Mẫu 7 (Đa đối tượng đồng thời):* Mẫu Anomaly chứa cả `NO_HELMET` và `USE_MOBILE_PHONE`.
8. *Mẫu 8 (Đa người trong ảnh):* Mẫu Anomaly thuộc Weak-Proxy chứa $\ge 3$ công nhân.

### 24.3. Tiêu chí Đánh giá Vượt qua (Pass Criteria)
Một mô hình được coi là **Đạt chuẩn Năng lực Bám bằng chứng (Grounding Eligible)** nếu trên 8 mẫu thử nghiệm:
1. Tỷ lệ phản hồi đúng định dạng JSON đạt 100% (8/8).
2. Tỷ lệ hộp bao có 4 tọa độ số thực hợp lệ trong $[0.0, 1.0]$ đạt $\ge 87,5\%$ (ít nhất 7/8 mẫu có tọa độ hợp lệ).
3. Không xảy ra hiện tượng đảo ngược tọa độ nghiêm trọng ($x_{\min} > x_{\max}$ hoặc $y_{\min} > y_{\max}$).
4. Có khả năng xuất nhiều hơn 1 hộp bao khi hiện trường có nhiều vật thể nguy cơ.

---

## 25. Model Shortlists (Các Danh sách Mô hình Đề xuất)

Để phục vụ nghiên cứu Seminar trong thời gian 8 tuần mà không làm phân tán tài nguyên, SafeShift đề xuất cơ cấu 3 danh sách mô hình có định hướng khoa học rõ ràng:

### 25.1. Danh sách Tái lập Upstream (Upstream Reproduction Set)
Dành riêng cho Giao thức P1 (1.250 mẫu test):
1. **`claude-opus-4-5-20251101`** (hoặc Claude 3.5/3.7 Sonnet làm mô hình thay thế tương thích nếu snapshot gốc không truy cập được trực tiếp từ Anthropic API).
2. **`grok-4.1-fast`** (Mô hình đối chiếu trong mã nguồn đánh giá văn bản của bài báo gốc).
3. **`bge-m3`** (Mô hình cục bộ qua Ollama dùng để tính điểm tương đồng ngữ nghĩa văn bản).

### 25.2. Danh sách Nghiên cứu Cốt lõi Tối thiểu (Minimal SafeShift Research Set — 4 Mô hình)
Dành cho Giao thức Chính P2 (5.013 mẫu toàn thể). Đáp ứng trọn vẹn tiêu chí đa dạng kiến trúc, cân bằng mã nguồn mở và dịch vụ đóng, bao phủ cả năng lực phân loại chuyên sâu lẫn định vị không gian nguyên bản:

1. **Google Gemini 2.5 Flash (`gemini-2.5-flash-001`):**
   - *Vai trò:* Đại diện mô hình thương mại đóng tốc độ cao, chi phí cực thấp, hỗ trợ **Object Detection nguyên bản (Doc-Verified)** với hệ tọa độ $[0, 1000]$.
   - *Tham gia:* P2 Classification, RQ3-A Direct Grounding, RQ3-B Proxy Grounding.
2. **Google Gemini 2.5 Pro (`gemini-2.5-pro-001`):**
   - *Vai trò:* Đại diện mô hình thương mại cao cấp với năng lực suy luận bối cảnh phức tạp và định vị không gian chính xác cao.
   - *Tham gia:* P2 Classification, RQ3-A Direct Grounding, RQ3-B Proxy Grounding.
3. **Qwen3-VL-8B-Instruct (chạy qua Hosted API):**
   - *Vai trò:* Đại diện tiêu biểu của cộng đồng **mã nguồn mở (Open-weight)**, kiến trúc tích hợp nhận thức không gian 2D chuyên sâu, minh bạch về trọng số và giấy phép học thuật.
   - *Tham gia:* P2 Classification, RQ3-A Direct Grounding, RQ3-B Proxy Grounding.
4. **OpenAI GPT-4o (`gpt-4o-2024-08-06`):**
   - *Vai trò:* Đại diện tiêu chuẩn vàng (Golden standard) về phân loại và lập luận thị giác tổng quát của ngành công nghiệp VLM; đóng vai trò mỏ neo đối sánh phân loại đa mô hình.
   - *Tham gia:* P2 Classification (Chắc chắn); Tham gia RQ3 Grounding nếu vượt qua Microtest Probe.

### 25.3. Danh sách Mở rộng Tùy chọn (Optional Extended Set)
Nếu có thêm tài nguyên tính toán và được phê duyệt:
1. **Claude 3.7 Sonnet:** Bổ sung góc nhìn về lập luận an toàn với cơ chế Extended Thinking.
2. **Qwen3-VL-32B-Instruct:** Đánh giá ảnh hưởng của quy mô tham số (model scaling) trong dòng họ mô hình mở.
3. **InternVL-2.5-8B / GLM-4V:** Mở rộng đại diện cho các kiến trúc thị giác nguồn mở khác từ giới học thuật.

---

## 26. D8 Decision Matrix (Ma trận Quyết định D8)

Tổng hợp các phương án kỹ thuật then chốt của Quyết định D8 để xin ý kiến chỉ đạo từ Project Owner:

| Chiều Kỹ thuật | Phương án 1 (Option A) | Phương án 2 (Option B) | Phương án 3 (Option C) | Phương án Đề xuất của SafeShift |
| :--- | :--- | :--- | :--- | :--- |
| **A. Quy mô Mô hình P2** | 3 Mô hình (Gemini Flash, Qwen-VL-8B, GPT-4o) | 4 Mô hình (Gemini Flash, Gemini Pro, Qwen-VL-8B, GPT-4o) | Mở rộng $\ge 6$ mô hình | **Phương án 2 (4 Mô hình)**: Đạt cân bằng tối ưu giữa độ đa dạng khoa học và chi phí kiểm soát (~ \$60). |
| **B. Từ điển Nguy cơ P2** | Open Vocabulary (Mô tả tự do, ánh xạ sau) | Closed 12-Hazard Vocabulary (Chọn trong 12 nhãn D6) | Hybrid (Nhãn đóng + Mô tả mở) | **Phương án 2 (Closed 12-Hazard)**: Bảo đảm tính tất định và tương thích toán học 100% với D5/D6. |
| **C. Kiến trúc Prompt P2** | Kế thừa nguyên vẹn bảng quy tắc Upstream | Simplified Canonical SafeShift Prompt | Hai giai đoạn (Phân loại rồi mới Định vị) | **Phương án 2 (Simplified Canonical)**: Giảm 50% chi phí token, cấu trúc JSON sạch, công bằng ngữ nghĩa. |
| **D. Cơ chế Gọi API P2** | One Combined Call (Chung 1 request lấy cả nhãn và box) | Two Separate Calls (Call 1: Classify; Call 2: Grounding) | Independent Grounding Call với fixed GT query | **Phương án 1 (One Combined Call)**: Tiết kiệm chi phí, phản ánh tính đồng thời giữa nhận thức nguy cơ và bằng chứng thị giác. |
| **E. Chế độ Suy luận (Thinking)** | Cưỡng bức tắt hoàn toàn (`budget=0`) | Sử dụng cấu hình mặc định (Provider Default) | Chuẩn hóa nỗ lực cố định cho mọi mô hình | **Phương án 2 (Provider Default)**: Tôn trọng thiết kế nguyên bản của nhà cung cấp; ghi nhận chi tiết trong metadata. |
| **F. Đầu ra Có cấu trúc** | Chỉ dùng Prompted JSON văn bản thuần | Ép buộc Native JSON Schema chặt chẽ | Kết hợp linh hoạt theo API hỗ trợ + Adapter | **Phương án 3 (Linh hoạt + Adapter)**: Tối ưu theo từng API nhưng bảo đảm đầu ra được chuẩn hóa tất định qua Adapter. |
| **G. Điều kiện Tham gia Grounding** | Chỉ tin tài liệu chính thức (Doc-verified only) | Tài liệu chính thức + Kiểm chứng Vi mô (Microtest) | Cho phép mọi mô hình tham gia bình đẳng | **Phương án 2 (Doc + Microtest)**: Tuân thủ nghiêm ngặt D4 Policy B, không phạt oan mô hình không hỗ trợ box. |
| **H. Quản lý Phiên bản** | Dùng bí danh động mới nhất (Moving latest) | Bắt buộc ghim phiên bản cố định (Dated Pinned IDs) | Chấp nhận hỗn hợp có gắn cờ cảnh báo | **Phương án 2 (Dated Pinned IDs)**: Bảo đảm tính tái lập khoa học lâu dài. |

---

## 27. Preliminary D8 Recommendation (Đề xuất Sơ bộ cho D8)

Nhóm nghiên cứu trân trọng đề xuất phương án tổng thể cho Quyết định D8 với trạng thái **PROPOSED, NOT APPROVED**:

1. **Về Giao thức P1 (Baseline Replication):**
   - Giữ nguyên 100% câu prompt Upstream và Bảng Quy tắc 5 ngành.
   - Chạy trên 1.250 mẫu test chính thức với mô hình tham chiếu `claude-opus-4-5-20251101` (hoặc mô hình thay thế tương thích nếu cần), thiết lập `temperature = 0.1`.
   - Sử dụng `bge-m3` cục bộ qua Ollama để tái lập chỉ số Semantic Similarity; tính Safety Accuracy theo đúng logic parsing của upstream.
2. **Về Giao thức P2 (Primary Research Protocol):**
   - Áp dụng **Một Prompt Ngữ nghĩa Thống nhất (Same Semantic Task Prompt)** cho toàn bộ mô hình để bảo đảm nguyên tắc công bằng (Prompt Fairness). Tuyệt đối không tối ưu câu chữ riêng cho bất kỳ mô hình nào.
   - Sử dụng **Từ điển Đóng 12 Nguy cơ Nguyên tử (Closed 12-Hazard Vocabulary)** đồng bộ với D6 Census.
   - Sử dụng **Cơ chế Một Lệnh gọi Tích hợp (One Combined Call)** trích xuất đồng thời `safety_level` và mảng `hazards` chứa tọa độ `evidence`.
   - Cấu hình giải mã: Ưu tiên `temperature = 0.0` (hoặc mức tối thiểu của nhà cung cấp) để tối đa hóa tính tất định; chế độ suy luận sử dụng mặc định của nhà cung cấp (Provider Default).
3. **Về Danh sách Mô hình Nghiên cứu (4 Mô hình):**
   - `gemini-2.5-flash-001` (Google)
   - `gemini-2.5-pro-001` (Google)
   - `qwen3-vl-8b-instruct` (Alibaba / Open-weight qua Hosted API)
   - `gpt-4o-2024-08-06` (OpenAI)
4. **Về Phân tầng Năng lực Grounding:**
   - Gemini và Qwen-VL đủ điều kiện tham gia trực tiếp đường đua Grounding (LEVEL 1 — DOC-VERIFIED).
   - GPT-4o tham gia đầy đủ Phân loại; chỉ tham gia Grounding nếu vượt qua bài kiểm tra vi mô (Microtest Probe). Nếu không tham gia, ghi nhận trạng thái `NOT PARTICIPATING`, không phạt điểm lỗi grounding theo D4.
5. **Về Bộ chuyển đổi và Lưu trữ:**
   - Cài đặt các Adapter tất định để đưa tọa độ bản địa ($y$-first, thang đo $[0, 1000]$) về chuẩn nội bộ $[x_{\min}, y_{\min}, x_{\max}, y_{\max}] \in [0.0, 1.0]$.
   - Lưu trữ nguyên văn Raw Model Response cho 100% mẫu ảnh trước khi phân tích cú pháp.

---

## 28. Risks & Limitations (Rủi ro và Giới hạn Phương pháp luận)

1. **Rủi ro Không khả dụng của Snapshot Upstream:** Tên định danh `claude-opus-4-5-20251101` trong mã nguồn phát hành có thể là định danh nội bộ của cổng proxy DMX. Nếu không thể gọi trực tiếp từ Anthropic API chính thức, việc tái lập P1 sẽ phải chuyển sang chế độ *Compatibility Reproduction* với một phiên bản Claude hiện hành, điều này có thể dẫn đến sai lệch số học nhất định so với bảng kết quả gốc.
2. **Hạn chế Phần cứng Cục bộ:** Việc GPU cục bộ chỉ có 4 GB VRAM buộc SafeShift phải phụ thuộc vào Hosted API cho mô hình nguồn mở Qwen-VL. Điều này phát sinh chi phí mạng và phụ thuộc vào tính sẵn sàng của nhà cung cấp dịch vụ đám mây.
3. **Nguy cơ Thay đổi API Của Bên Thứ Ba (API Deprecation):** Các nhà cung cấp dịch vụ đám mây có thể thay đổi chính sách hỗ trợ các dated snapshot trong tương lai. Cần lưu trữ đầy đủ toàn bộ raw response và request payload để phục vụ thẩm định độc lập mà không cần gọi lại API.
4. **Sự Không Hoàn hảo của Định vị Bằng chứng:** Nhắc lại cảnh báo từ Quyết định D6 và D7: việc bám bằng chứng không gian dựa trên các đa giác vật thể có sẵn không tương đương với việc chứng minh lý do vi phạm an toàn đầy đủ của con người. Mọi chỉ số IoU và PLC phải được diễn giải thận trọng trong phạm vi chú thích hiện hữu.

---

## 29. Questions Requiring Approval (Các Câu hỏi Cần Xin Ý kiến Phê duyệt)

Để hoàn thiện và chính thức khóa Quyết định D8 tại Week 2, nhóm nghiên cứu kính trình Project Owner xem xét và cho ý kiến về **16 câu hỏi then chốt**:

1. **Phê chuẩn Mô hình Tham chiếu P1:** Chấp thuận phương án sử dụng Claude Opus (hoặc phiên bản Claude tương thích khả dụng trên official API) và `bge-m3` cục bộ để tái lập P1 hay có chỉ đạo khác?
2. **Phê chuẩn Danh sách Mô hình P2 Cốt lõi:** Chấp thuận danh sách 4 mô hình đề xuất (`Gemini 2.5 Flash`, `Gemini 2.5 Pro`, `Qwen3-VL-8B`, `GPT-4o`) hay muốn rút gọn xuống 3 mô hình hoặc mở rộng thêm?
3. **Chính sách Mô hình Nguồn mở:** Đồng thuận việc sử dụng Hosted API thương mại (DashScope / OpenRouter) cho Qwen3-VL do hạn chế VRAM cục bộ 4 GB của máy trạm?
4. **Phê chuẩn Từ điển Nguy cơ P2:** Chấp thuận **Option B (Closed 12-Hazard Vocabulary)** để đồng bộ tuyệt đối với D6 Census và D5 Bipartite Matching?
5. **Phê chuẩn Cấu trúc Câu lệnh P2:** Đồng ý áp dụng Mẫu Prompt Chuẩn hóa Gọn gàng (Simplified Canonical SafeShift Prompt) cho toàn bộ mô hình trong P2?
6. **Cơ chế Lệnh gọi:** Phê duyệt cơ chế **Một Lệnh gọi Kết hợp (One Combined Call)** trích xuất đồng thời phân loại và tọa độ chứng cứ?
7. **Phê chuẩn Cấu trúc Đầu ra Chuẩn hóa:** Đồng thuận với đặc tả JSON Schema nội bộ và nguyên tắc chuyển đổi tọa độ của Adapter theo Quyết định D4?
8. **Tiêu chuẩn Tham gia Grounding:** Chấp thuận quy trình kiểm chứng vi mô (Microtest Probe trên 8 mẫu) đối với các mô hình ở diện Prompt-Only (như GPT-4o) trước khi cho phép tham gia track Grounding?
9. **Chính sách Mô hình Chỉ Phân loại:** Tái khẳng định chính sách phân loại thuần túy: mô hình không tham gia grounding được ghi nhận `NOT PARTICIPATING`, không bị gán lỗi $\text{IoU} = 0.0$?
10. **Chính sách Chế độ Suy luận (Thinking):** Chấp thuận việc sử dụng cấu hình suy luận mặc định của nhà cung cấp (Provider Default) và cho phép áp dụng khuyến nghị kỹ thuật của Google đối với Gemini Object Detection?
11. **Chính sách Giải mã và Nhiệt độ:** Đồng thuận thiết lập `temperature = 0.0` (hoặc giá trị tối thiểu của API) cho toàn bộ các lượt chạy của P2?
12. **Chính sách Đầu ra Có Cấu trúc:** Đồng ý sử dụng Native JSON Schema trên các API hỗ trợ và kết hợp kiểm tra tính hợp lệ bằng Adapter tất định?
13. **Chính sách Cố định Phiên bản:** Bắt buộc sử dụng các định danh mô hình có gắn ngày/phiên bản cố định (Dated Pinned IDs)?
14. **Chính sách Hiệu chỉnh Xác suất (Calibration):** Xác nhận xếp diện `CALIBRATION_INELIGIBLE` cho các mô hình Closed-API và cấm sử dụng độ tự tin tự thuật bằng văn bản?
15. **Hạn mức Ngân sách Thực nghiệm:** Phê chuẩn hạn mức ngân sách thực nghiệm ước tính khoảng \$60 – \$100 USD cho toàn bộ quá trình chạy baseline ở Week 3?
16. **Tuyên bố về Nhiễm Dữ liệu Tiền Huấn luyện:** Chấp thuận phát biểu khoa học tiêu chuẩn: SafeShift là benchmark đánh giá thực nghiệm trên mô hình đóng băng trọng số, không thể chứng minh sự vắng mặt tuyệt đối của rò rỉ dữ liệu tiền huấn luyện?

---

## 30. Evidence Sources (Nguồn Bằng chứng và Tài liệu Tham chiếu)

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
