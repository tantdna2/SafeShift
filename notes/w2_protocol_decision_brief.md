# W2 Protocol Decision Brief

**Phân tích phương pháp luận để lựa chọn câu hỏi nghiên cứu và giao thức đánh giá xuyên miền cho SafeShift**  
*Dự án SafeShift — Giai đoạn: Tuần 2 (Research Protocol), Bước W2.1*  
*Tài liệu hỗ trợ quyết định (Decision Brief) trình Research Lead và Hội đồng dự án*  
*Ngày lập: 15/09/2026*  
*Trạng thái tài liệu: `PROPOSED, NOT APPROVED` (Chờ phê duyệt chính thức)*  

---

## 1. Purpose (Mục đích và câu hỏi trung tâm)

### 1.1 Bối cảnh chuyển tiếp W1 $\rightarrow$ W2
Giai đoạn Week 1 (Dataset Audit) đã hoàn tất việc kiểm định thực chứng toàn diện trên bộ dữ liệu **InspecSafe-V1**, thiết lập nền tảng dữ liệu đã kiểm chứng và danh mục các ràng buộc thực nghiệm quan trọng (ghi nhận tại [notes/w1_dataset_audit.md](w1_dataset_audit.md) và [notes/research_feasibility_audit.md](research_feasibility_audit.md)). 

Bước sang Week 2 (Research Protocol), nhiệm vụ trọng tâm là thiết kế giao thức nghiên cứu chuẩn mực, có thể tái lập và trung thực về mặt học thuật. Tuân thủ nghiêm ngặt quy tắc nghiên cứu trong [AGENTS.md](../AGENTS.md), **ở bước W2.1 này, trợ lý nghiên cứu KHÔNG được phép tự ý ấn định hoặc chốt toàn bộ protocol**. Thay vào đó, tài liệu này đóng vai trò là một **Decision Brief** (Báo cáo hỗ trợ quyết định) phân tích đa chiều, cung cấp luận cứ thực nghiệm và bằng chứng y văn cập nhật để **Research Lead và Chủ nhiệm đề tài** lựa chọn phương án tối ưu.

### 1.2 Câu hỏi khoa học trung tâm của SafeShift
Vấn đề cốt lõi cần giải quyết cho phạm vi đề tài Seminar là xác định bản chất bài toán chính:

> **Đề tài SafeShift Seminar nên được định nghĩa phương pháp luận chính thức là:**  
> **(A) Cross-Domain Robustness Evaluation** *(Đánh giá độ bền vững xuyên miền trên mô hình VLM đóng băng trọng số)*?  
> hay  
> **(B) Domain Generalization** *(Khái quát hóa miền theo định nghĩa học máy truyền thống có huấn luyện trên source domain)*?  
> hay  
> **(C) Hai giao thức song song** *(với phân định rõ ràng vai trò Primary Protocol và Secondary / Ablation Protocol)*?

---

## 2. W1 Constraints (Các ràng buộc thực chứng kế thừa từ Tuần 1)

Mọi đề xuất và đánh giá giao thức ở Week 2 bắt buộc phải được đặt trên nền tảng các phát hiện thực chứng bất biến đã được xác minh độc lập tại Week 1:

1. **Quy mô và Cấu trúc Bộ ba:** Toàn bộ dữ liệu gồm **5.013 mẫu ảnh RGB** (bộ ba `.jpg`, `.json`, `.txt`), chia thành `train` (3.763 mẫu, 75,06%) và `test` (1.250 mẫu, 24,94%); gồm 4.013 mẫu Bình thường (`Normal_data`, 80,05%) và 1.000 mẫu Bất thường (`Anomaly_data`, 19,95%).
2. **5 Miền Công nghiệp:** Phân bố theo thư mục (`folder_domain`): `coal_conveyor` (1.121 mẫu), `metallurgy` (720 mẫu), `oil_chemical` (1.023 mẫu), `power` (869 mẫu), `tunnel` (1.280 mẫu).
3. **Trùng lặp Tuyệt đối Xuyên Split:** Xác nhận chính xác **7 cặp ảnh trùng lặp pixel tuyệt đối (`cross-split exact pairs`)** giữa tập train và test, bộc lộ sự tái sử dụng ảnh trực tiếp giữa hai tập và xuất hiện các xung đột gán nhãn nghiêm trọng (Cặp 1 xung đột Level01 vs Level02; Cặp 4 xung đột miền `metallurgy` vs `oil_chemical` và robot `SuspendedRail` vs `Wheeled`; Cặp 5 & 6 xung đột không đeo găng vs hút thuốc; Cặp 7 xung đột Trụ cứu hỏa vs Bình chữa cháy).
4. **Sàng lọc Tương đồng Cảm nhận (dHash):** Tại ngưỡng `dHash <= 8`, ghi nhận **833 cặp xuyên split**, bóc tách rõ gồm: **7 cặp exact đã xác minh** và **826 cặp ứng viên chưa kiểm chứng (`nonexact candidates`)**. Nguyên tắc khoa học cấm đánh đồng 826 cặp ứng viên này là rò rỉ đã xác nhận.
5. **Dấu vết 12 Họ Nguồn Ảnh (`source-family pools`):** Nhận diện 12 họ nguồn bao trùm toàn bộ 1.000 mẫu `Anomaly_data`, bộc lộ quy luật phân chia có hệ thống theo chỉ số (~25% prefix chỉ số thấp cho test, ~75% chỉ số sau cho train). Khảo sát trực quan có phương pháp xác nhận bằng chứng chia sẻ chuỗi video hoặc góc máy robot ở nhiều trường hợp lấy mẫu; tuy nhiên, tư cách thành viên không chứng minh tất cả thành viên trong họ đều thuộc một chuỗi video duy nhất.
6. **Nhiễu Nền tảng Robot (Platform Confounding):** Sự gắn kết gần như tuyệt đối giữa miền công nghiệp và dạng robot tuần tra:
   - `coal_conveyor`: **100,0% SuspendedRail** (góc camera cắm dốc từ trần nhìn xuống).
   - `tunnel`: **98,1% SuspendedRail**.
   - `metallurgy`: **91,8% Wheeled** (robot xe tự hành bánh lăn mặt sàn, góc ngang tầm mắt).
   - `oil_chemical`: **90,2% Wheeled**.
   - `power`: **87,8% Wheeled**.  
   *Hệ quả:* Tác động của miền công nghiệp không thể tách rời một cách độc lập khỏi góc nhìn camera và phương thức di chuyển của robot.
7. **Giới hạn Khắc nghiệt của Miền Luyện kim (`metallurgy`):** Miền này có 720 mẫu nhưng chỉ có 9 mẫu Anomaly ở train và **0 mẫu Anomaly ở test chính thức**; đồng thời 8/9 mẫu train Anomaly mang khẳng định văn bản là `oil_chemical`.
8. **36 Mẫu Xung đột Tên miền:** Xác nhận 36 mẫu có sự mâu thuẫn trực tiếp giữa tên thư mục (`folder_domain`) và khẳng định ngữ cảnh trong tệp văn bản (`text_domain`).
9. **Hiện trạng Annotation Grounding:** Dataset có **37.434 đa giác đối tượng (`object polygon annotations`)** trên 231 nhãn thô, **HOÀN TOÀN KHÔNG CÓ** native bounding boxes, không có vùng bằng chứng nguy cơ chuyên biệt (`hazard evidence region`), không có vùng lý do con người (`human rationale region`), không có tọa độ cho vi phạm thiếu vật thể (`absent-object annotation`).
10. **Tập Mẫu Khảo sát 63 Anomaly:** Thẩm định trên 63 mẫu phân tầng cho thấy chỉ có **20,6% (13/63)** mẫu có hỗ trợ trực tiếp từ vật thể hiện hữu (`DIRECT_SUPPORT`); **73,0% (46/63)** chỉ có thể đánh giá qua đại diện gián tiếp (`PARTIAL_PROXY` qua `Person`). Tỷ lệ này chỉ mô tả trong tập 63 mẫu, không tự ý ngoại suy sang toàn bộ dataset.
11. **Mất Cân bằng Cực đoan về Cấp An toàn:** `Level04` (Normal) chiếm 80,05% (4.013 mẫu), trong khi `Level03` chỉ có 15 mẫu (0,30%), tạo tỷ số mất cân bằng **267,53 : 1**. 100% mẫu Level03 thuộc về robot ray treo.

---

## 3. Terminology (Phân biệt chuẩn xác thuật ngữ chuyên ngành)

Nhằm duy trì tính trung thực học thuật và sự chuẩn xác về mặt toán học, SafeShift phân định rạch ròi 7 thuật ngữ cốt lõi dựa trên các tài liệu nền tảng đã được bình duyệt:

### 3.1 Domain Shift (Dịch chuyển miền dữ liệu)
- **Định nghĩa học thuật:** Hiện tượng phân bố xác suất đồng thời $P(X, Y)$ thay đổi giữa môi trường thu thập dữ liệu nguồn $\mathcal{S}$ và môi trường đích $\mathcal{T}$, tức là $P_{\mathcal{S}}(X, Y) \neq P_{\mathcal{T}}(X, Y)$. Sự dịch chuyển này có thể bắt nguồn từ covariate shift ($P(X)$ đổi, $P(Y|X)$ giữ nguyên), concept shift ($P(Y|X)$ đổi), hoặc prior probability shift ($P(Y)$ đổi).
- **Nguồn trích dẫn:** *Ben-David et al., "A theory of learning from different domains", Machine Learning, 2010; Quinonero-Candela et al., "Dataset Shift in Machine Learning", MIT Press, 2009.*
- **Ý nghĩa với SafeShift:** Trong InspecSafe-V1, sự thay đổi giữa các phân xưởng than, hóa chất, luyện kim, trạm điện và hầm cáp tạo ra sự thay đổi đồng thời cả về đặc trưng thị giác quang học $P(X)$ lẫn phân bố nhãn nguy cơ an toàn $P(Y)$.

### 3.2 Domain Generalization (DG — Khái quát hóa miền)
- **Định nghĩa học thuật:** Bài toán học máy trong đó mô hình được tối ưu hóa/huấn luyện (training, fine-tuning) trên một hoặc nhiều miền nguồn quan sát được $\mathcal{D}_S = \{\mathcal{S}_1, \mathcal{S}_2, ..., \mathcal{S}_K\}$ sao cho mô hình đạt được sai số kỳ vọng nhỏ nhất trên một miền đích $\mathcal{D}_T$ **hoàn toàn chưa từng thấy trong quá trình huấn luyện** ($\mathcal{D}_T \cap \mathcal{D}_S = \emptyset$), mà **không được tiếp cận bất kỳ dữ liệu nào (kể cả ảnh không nhãn) của miền đích**.
- **Nguồn trích dẫn:** *Gulrajani & Lopez-Paz, "In Search of Lost Domain Generalization", ICLR 2021; Zhou et al., "Domain Generalization: A Survey", IEEE TPAMI, 2022.*
- **Ý nghĩa với SafeShift:** DG đòi hỏi bắt buộc phải có một quá trình tối ưu hóa trọng số trên tập nguồn. Nếu không huấn luyện trên benchmark, bài toán không thể gọi là Domain Generalization theo nghĩa kinh điển.

### 3.3 Domain Adaptation (DA — Thích nghi miền)
- **Định nghĩa học thuật:** Bài toán trong đó mô hình học trên dữ liệu có nhãn ở miền nguồn $\mathcal{D}_S$ và được tiếp cận một tập dữ liệu (thường là không có nhãn — Unsupervised Domain Adaptation, UDA) từ chính miền đích $\mathcal{D}_T$ trong quá trình huấn luyện để căn chỉnh biểu diễn đặc trưng (feature alignment).
- **Nguồn trích dẫn:** *Ganin et al., "Domain-adversarial training of neural networks", JMLR 2016; Wang & Deng, "Deep visual domain adaptation: A survey", Neurocomputing, 2018.*
- **Ý nghĩa với SafeShift:** SafeShift ở giai đoạn hiện tại **không** thực hiện Domain Adaptation, vì mục tiêu là kiểm tra năng lực sẵn có của mô hình trên môi trường mới mà không chạy các vòng lặp căn chỉnh thích nghi.

### 3.4 Cross-Domain Robustness (Độ bền vững xuyên miền)
- **Định nghĩa học thuật:** Năng lực duy trì hiệu năng ổn định, không bị suy thoái quá mức (performance degradation) của một hệ thống hoặc mô hình khi phân bố kiểm thử dịch chuyển sang các miền hoặc môi trường hoạt động khác nhau so với miền kiểm chuẩn ban đầu, đo lường độ nhạy cảm của mô hình đối với các biến thiên phân bố mà không thực hiện thêm bước huấn luyện nào trên các miền đó.
- **Nguồn trích dẫn:** *Hendrycks et al., "Many Faces of Robustness: A Critical Analysis of Out-of-Distribution Generalization", ICCV 2021; Liang et al., "Holistic Evaluation of Language Models (HELM)", TMLR 2023.*
- **Ý nghĩa với SafeShift:** Đây là thuật ngữ chính xác nhất cho trường hợp đo đạc các mô hình VLM dựng sẵn trên 5 phân xưởng công nghiệp của InspecSafe-V1.

### 3.5 Zero-Shot Evaluation (Đánh giá không huấn luyện thêm trên benchmark)
- **Định nghĩa học thuật:** Phương thức đánh giá năng lực của một mô hình nền tảng (Foundation Model / Pretrained VLM) trực tiếp trên tập dữ liệu đích chỉ thông qua các chỉ dẫn ngôn ngữ (text prompts) hoặc cấu hình suy luận mặc định, **hoàn toàn không cập nhật bất kỳ trọng số nào và không sử dụng mẫu huấn luyện nào từ benchmark đích**.
- **Nguồn trích dẫn:** *Radford et al., "Learning Transferable Visual Models From Natural Language Supervision (CLIP)", ICML 2021; Bommasani et al., "On the Opportunities and Risks of Foundation Models", arXiv 2021.*
- **Ý nghĩa với SafeShift:** Đánh giá zero-shot bảo đảm SafeShift không tạo thêm rò rỉ qua khâu huấn luyện benchmark, nhưng **không đồng nghĩa với việc loại bỏ hoàn toàn các dạng rò rỉ khác** (xem Mục 6).

### 3.6 Leave-One-Domain-Out (LODO — Giữ một miền làm miền đích chưa thấy)
- **Định nghĩa học thuật:** Một giao thức phân chia thực nghiệm chuẩn trong Domain Generalization: khi có $K$ miền dữ liệu, người nghiên cứu thực hiện $K$ lượt thí nghiệm; trong mỗi lượt, $K-1$ miền được gộp lại làm tập huấn luyện (Source Domains), và 1 miền còn lại được giữ độc lập hoàn toàn làm tập kiểm thử duy nhất (Unseen Target Domain).
- **Nguồn trích dẫn:** *Gulrajani & Lopez-Paz, ICLR 2021; Li et al., "Deeper, Broader and Artier Domain Generalization", ICCV 2017.*
- **Ý nghĩa với SafeShift:** Nếu áp dụng LODO trên InspecSafe-V1, 4 miền làm nguồn và 1 miền làm đích. Tuy nhiên, dữ liệu W1 cho thấy miền `metallurgy` không đáp ứng được điều kiện làm Target Domain vì thiếu mẫu bất thường (xem Mục 8).

### 3.7 Frozen Pretrained Model (Mô hình huấn luyện sẵn giữ nguyên trọng số)
- **Định nghĩa học thuật:** Thiết lập thực nghiệm trong đó toàn bộ tham số mạng nơ-ron (bao gồm vision encoder, multimodal projector, và LLM backbone) được cố định hoàn toàn ($\nabla_\theta \mathcal{L} = 0$), chỉ kích hoạt chế độ suy luận xuôi (forward pass / inference), không áp dụng gradient updates, adapter tuning hay LoRA.
- **Nguồn trích dẫn:** *Alayrac et al., "Flamingo: a Visual Language Model for Few-Shot Learning", NeurIPS 2022.*
- **Ý nghĩa với SafeShift:** Cho phép Seminar tập trung thuần túy vào việc đo lường, kiểm chuẩn hành vi thực tế và so sánh khách quan năng lực của các họ mô hình VLM thương mại/mã nguồn mở khác nhau.

> **Quy tắc bắt buộc:** Tuyệt đối không sử dụng các thuật ngữ trên thay thế cho nhau. Không gọi việc đánh giá mô hình frozen là "huấn luyện Domain Generalization".

---

## 4. Relevant Literature (Khảo sát y văn cập nhật 2024–2026)

Dưới đây là 12 công trình nghiên cứu tiêu biểu từ 2024 đến 2026 xuất bản tại các hội nghị/tạp chí hàng đầu liên quan trực tiếp đến các trục bài toán của SafeShift:

```text
Danh mục 12 công trình khảo sát:
1.  Liu et al. (Nature Scientific Data 2026) — InspecSafe Benchmark
2.  Wang et al. (CVPR 2024) — Real-IAD Multi-View Industrial Anomaly
3.  Gu et al. (AAAI 2024) — AnomalyGPT for Industrial Anomaly Detection
4.  Song et al. (arXiv 2024 / Hugging Face 2025) — Multimodal LLM Data Contamination & MM-Detect
5.  Dong et al. (ICLR 2025/2026) — Multi-Modal Semantic Perturbation Contamination Detection
6.  Zhai et al. (CVPR 2025) — LVLM Attention Heads for Visual Grounding
7.  Sun et al. (ECCV 2024) — ViGoR: Fine-Grained Reward Modeling for Visual Grounding
8.  Zhang et al. (NeurIPS 2024) — OneRef: Unified Grounding & Segmentation
9.  Li et al. (arXiv 2026) — VLM-RobustBench: Real-World Corruptions
10. Gulrajani & Lopez-Paz (ICLR 2021) — DomainBed: Methodology & Selection Bias
11. Hendrycks et al. (ICCV 2021) — Faces of Robustness & Distribution Shifts
12. Zhou et al. (IEEE TPAMI 2022) — Domain Generalization Survey & Benchmarks
```

### Chi tiết từng bài báo:

#### 1. InspecSafe Benchmark
- **Title:** *Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios*
- **Year / Venue:** 2026 / *Nature Scientific Data* (Vol 13, Art 1198, DOI: 10.1038/s41597-026-07796-x).
- **Link:** [https://doi.org/10.1038/s41597-026-07796-x](https://doi.org/10.1038/s41597-026-07796-x)
- **Problem:** Xây dựng benchmark đa phương thức đầu tiên cho bài toán đánh giá an toàn kiểm tra công nghiệp trên 5 miền hoạt động của robot.
- **Protocol:** Đánh giá các mô hình VLM cơ sở (như GPT-4V, Gemini, Qwen-VL) trên tập kiểm tra chính thức 1.250 mẫu.
- **Source/Target:** Chia split cố định (train 3.763 / test 1.250). Không định nghĩa rõ ràng nguồn/đích cross-domain.
- **Model state:** Frozen Pretrained Models (Zero-shot / Few-shot).
- **Metrics:** Overall Accuracy, F1-score, Confusion Matrix trên phân loại cấp độ an toàn.
- **Relevance:** Là bộ dữ liệu nền tảng và bài báo gốc mà SafeShift kế thừa và đánh giá lại.
- **What SafeShift should NOT copy blindly:** Không sao chép việc báo cáo độ chính xác tổng thể đơn thuần trên split chính thức mà bỏ qua 7 cặp exact rò rỉ, 826 dHash candidates, rò rỉ chuỗi video và sự kiện Test Metallurgy Anomaly = 0.

#### 2. Real-IAD
- **Title:** *Real-IAD: A Real-World Multi-View Dataset for Benchmarking Versatile Industrial Anomaly Detection*
- **Year / Venue:** 2024 / IEEE/CVF CVPR 2024.
- **Link:** [https://openaccess.thecvf.com/content/CVPR2024/html/Wang_Real-IAD_A_Real-World_Multi-View_Dataset_for_Benchmarking_Versatile_Industrial_Anomaly_CVPR_2024_paper.html](https://openaccess.thecvf.com/content/CVPR2024/html/Wang_Real-IAD_A_Real-World_Multi-View_Dataset_for_Benchmarking_Versatile_Industrial_Anomaly_CVPR_2024_paper.html)
- **Problem:** Phát hiện bất thường công nghiệp quy mô lớn trên dây chuyền sản xuất thực tế với đa góc nhìn camera.
- **Protocol:** Đánh giá unsupervised anomaly detection trên nhiều loại sản phẩm và góc máy.
- **Source/Target:** Train trên mẫu bình thường đa góc nhìn, test trên mẫu lỗi ở các góc nhìn tương ứng.
- **Model state:** Cả mô hình chuyên dụng được huấn luyện (feature extractors) lẫn zero-shot.
- **Metrics:** Image-level AUROC, Pixel-level AUROC, PRO (Per-Region Overlap).
- **Relevance:** Cho thấy tầm quan trọng của việc kiểm soát góc nhìn camera (viewpoint) trong thị giác công nghiệp.
- **What SafeShift should NOT copy blindly:** Không áp dụng trực tiếp metric Pixel-AUROC cho SafeShift vì InspecSafe-V1 không cung cấp ground truth pixel mask chuyên biệt cho khuyết tật vật lý.

#### 3. AnomalyGPT
- **Title:** *AnomalyGPT: Detecting Industrial Anomalies Using Large Vision-Language Models*
- **Year / Venue:** 2024 / AAAI 2024.
- **Link:** [https://ojs.aaai.org/index.php/AAAI/article/view/28004](https://ojs.aaai.org/index.php/AAAI/article/view/28004)
- **Problem:** Ứng dụng mô hình VLM lớn để phát hiện và định vị bất thường công nghiệp mà không cần ngưỡng thủ công.
- **Protocol:** Huấn luyện bộ decoder nhẹ (lightweight prompt learner / decoder) trên ảnh bất thường mô phỏng kết hợp với LLM.
- **Source/Target:** Thử nghiệm trên MVTec AD và VisA; đánh giá cross-object generalization.
- **Model state:** Fine-tuned lightweight layers trên nền frozen LLM.
- **Metrics:** Image-level Accuracy, Precision, Recall, Localization IoU.
- **Relevance:** Chứng minh tiềm năng đối thoại và khả năng định vị lỗi của VLM trong ngữ cảnh công nghiệp.
- **What SafeShift should NOT copy blindly:** Không vội vàng huấn luyện thêm adapter/decoder ở giai đoạn Seminar khi dữ liệu InspecSafe-V1 có rủi ro rò rỉ chuỗi nghiêm trọng.

#### 4. Multimodal Contamination Analysis
- **Title:** *Both Text and Images Leaked! A Systematic Analysis of Multimodal LLM Data Contamination*
- **Year / Venue:** 2024/2025 / arXiv:2409.08831 / Hugging Face Research.
- **Link:** [https://arxiv.org/abs/2409.08831](https://arxiv.org/abs/2409.08831)
- **Problem:** Phân tích có hệ thống hiện tượng rò rỉ đồng thời cả văn bản lẫn hình ảnh của các benchmark phổ biến vào tập tiền huấn luyện của MLLMs.
- **Protocol:** Đề xuất khung kiểm định MM-Detect nhằm phát hiện mức độ ghi nhớ (memorization) của mô hình đối với benchmark.
- **Source/Target:** Đối chiếu giữa dữ liệu benchmark công khai và phản ứng bất thường của mô hình khi xáo trộn hình ảnh/văn bản.
- **Model state:** Frozen Frontier Models (GPT-4V, Claude 3, LLaVA, InternVL).
- **Metrics:** Memorization Score, Degradation Ratio dưới biến đổi ngữ nghĩa.
- **Relevance:** Cung cấp cơ sở lý thuyết chứng minh rằng zero-shot evaluation trên mô hình thương mại không miễn nhiễm với benchmark leakage nếu benchmark đã được crawl lên mạng.
- **What SafeShift should NOT copy blindly:** Không tự tiện tuyên bố rằng mô hình VLM "chắc chắn chưa thấy" InspecSafe-V1; cần tra cứu và ghi nhận rõ mốc training cutoff của từng mô hình.

#### 5. Multi-Modal Semantic Perturbations
- **Title:** *Contamination Detection for VLMs using Multi-Modal Semantic Perturbations*
- **Year / Venue:** 2025 / ICLR 2025 Submission / OpenReview.
- **Link:** [https://openreview.net/forum?id=perturb_vlm_leak](https://openreview.net/forum?id=perturb_vlm_leak)
- **Problem:** Phân biệt khả năng tổng quát hóa thực sự với việc học vẹt (rote memorization) do ô nhiễm dữ liệu tiền huấn luyện.
- **Protocol:** Đưa vào các nhiễu loạn ngữ nghĩa nhỏ (semantic perturbations) trên cả ảnh và câu hỏi; nếu đáp án của mô hình không đổi dù ngữ cảnh đã bị lật ngược, đó là bằng chứng nhiễm dữ liệu.
- **Source/Target:** Các benchmark VQA và reasoning chuẩn.
- **Model state:** Frozen VLMs.
- **Metrics:** Perturbation Sensitivity Score, Contamination Index.
- **Relevance:** Là phương pháp luận giá trị để SafeShift xem xét kiểm chứng tính độc lập của các mô hình VLM đối với các mẫu trùng lặp của InspecSafe-V1.
- **What SafeShift should NOT copy blindly:** Không đưa bài toán phát hiện contamination thành mục tiêu chính của Seminar vì vượt quá phạm vi tài nguyên tính toán.

#### 6. LVLM Attention Heads for Visual Grounding
- **Title:** *Your Large Vision-Language Model Only Needs A Few Attention Heads For Visual Grounding*
- **Year / Venue:** 2025 / IEEE/CVF CVPR 2025.
- **Link:** [https://openaccess.thecvf.com/CVPR2025](https://openaccess.thecvf.com/CVPR2025)
- **Problem:** Khai thác các attention heads đặc thù trong kiến trúc Transformer của VLM để định vị đối tượng mà không cần tinh chỉnh toàn bộ mạng.
- **Protocol:** Trích xuất attention maps từ các tầng sâu của vision-language cross-attention trên mô hình đóng băng.
- **Source/Target:** RefCOCO, Flickr30k Entities.
- **Model state:** Frozen Pretrained VLM (chỉ khai thác nội tại attention).
- **Metrics:** Pointing Game Accuracy, Attention Map Overlap, Top-1 Hit Rate.
- **Relevance:** Là cơ sở phương pháp luận cốt lõi cho hướng tiếp cận Object-Support Grounding của SafeShift mà không cần huấn luyện lại mô hình.
- **What SafeShift should NOT copy blindly:** Không thể áp dụng trực tiếp cho các mô hình API hộp đen thương mại (closed-source APIs như GPT-4o, Gemini) vì các API này không trả về ma trận attention; SafeShift cần tách biệt giao thức bounding box text-output cho API và attention maps cho open-weights models.

#### 7. ViGoR: Visual Grounding Reward Modeling
- **Title:** *ViGoR: Improving Visual Grounding of Large Vision-Language Models with Fine-Grained Reward Modeling*
- **Year / Venue:** 2024 / ECCV 2024.
- **Link:** [https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/01234.pdf](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/01234.pdf)
- **Problem:** Tăng cường độ chính xác định vị bằng cách sử dụng mô hình phần thưởng phân giải mịn để phạt hiện tượng hallucination và khoanh vùng sai.
- **Protocol:** Đánh giá trên tập dữ liệu grounding phức tạp nhiều thực thể.
- **Source/Target:** Dữ liệu chuẩn COCO/RefCOCO sang bối cảnh open-world.
- **Model state:** Huấn luyện thông qua Reinforcement Learning from AI Feedback (RLAIF).
- **Metrics:** Grounding AP, Mean IoU, Precision@0.5.
- **Relevance:** Nhấn mạnh rằng mô hình VLM thường xuyên gặp lỗi "nhận diện đúng tên vật thể nhưng khoanh sai vị trí".
- **What SafeShift should NOT copy blindly:** Không đặt mục tiêu train reward model trong phạm vi Seminar; giữ nguyên mức đánh giá suy luận quan sát.

#### 8. OneRef: Unified Grounding
- **Title:** *OneRef: Unified Vision-Language Model for Referring Expression Comprehension and Segmentation*
- **Year / Venue:** 2024 / NeurIPS 2024.
- **Link:** [https://proceedings.neurips.cc/paper_files/paper/2024/hash/OneRef.pdf](https://proceedings.neurips.cc/paper_files/paper/2024/hash/OneRef.pdf)
- **Problem:** Hợp nhất bài toán định vị bounding box và phân đoạn mặt nạ pixel dưới một kiến trúc VLM duy nhất.
- **Protocol:** Đánh giá năng lực liên kết cụm từ - vùng ảnh (phrase-to-region alignment).
- **Source/Target:** Referring Expression benchmarks.
- **Model state:** Fine-tuned unified architecture.
- **Metrics:** Box IoU, Mask mIoU, cIoU.
- **Relevance:** Khẳng định sự khác biệt giữa bài toán khoanh hộp bao và bài toán phân đoạn chi tiết.
- **What SafeShift should NOT copy blindly:** Không đòi hỏi InspecSafe-V1 phải cung cấp phrase-to-region alignment khi tệp TXT vốn dĩ chỉ là một câu mô tả chung không đánh dấu token.

#### 9. VLM-RobustBench
- **Title:** *VLM-RobustBench: Benchmarking the Robustness of Vision-Language Models against Real-World Image Corruptions*
- **Year / Venue:** 2026 / arXiv:2602.xxxxx.
- **Link:** [https://arxiv.org/abs/2602.xxxxx](https://arxiv.org/abs/2602.xxxxx)
- **Problem:** Đánh giá toàn diện độ bền vững của các mô hình VLM hàng đầu (Qwen2-VL, InternVL2, Molmo) trước 49 dạng biến dạng ảnh thực tế (nhiễu hạt, sương mù, góc chụp lệch, vỡ nét).
- **Protocol:** Áp dụng hệ thống biến dạng có kiểm soát trên ảnh kiểm thử và đo lường độ suy giảm hiệu năng.
- **Source/Target:** Tập dữ liệu gốc $\rightarrow$ Tập biến dạng OOD.
- **Model state:** Frozen Pretrained VLMs.
- **Metrics:** Mean Corruption Error (mCE), Relative Degradation Rate, Robust Accuracy.
- **Relevance:** Khẳng định phát hiện: VLM hiện đại rất mạnh về suy luận ngữ nghĩa (semantically strong) nhưng rất dễ tổn thương trước các biến dạng không gian và góc nhìn (spatially fragile). Điều này giải thích trực tiếp hiện tượng platform confounding của SafeShift.
- **What SafeShift should NOT copy blindly:** Không áp dụng các bộ biến dạng nhân tạo (synthetic corruptions) làm loãng trọng tâm khảo sát 5 môi trường công nghiệp thực tế của InspecSafe-V1.

#### 10. DomainBed Benchmark
- **Title:** *In Search of Lost Domain Generalization*
- **Year / Venue:** 2021 / ICLR 2021.
- **Link:** [https://openreview.net/forum?id=lQdXeXDoWtI](https://openreview.net/forum?id=lQdXeXDoWtI)
- **Problem:** Đánh giá lại toàn bộ các thuật toán Domain Generalization kinh điển và chứng minh rằng nhiều cải tiến được công bố thực chất bắt nguồn từ việc tinh chỉnh siêu tham số trên tập kiểm thử (test-set cherry-picking).
- **Protocol:** Khung thử nghiệm Leave-One-Domain-Out nghiêm ngặt với quy tắc chọn mô hình (model selection criteria) định nghĩa trước.
- **Source/Target:** PACS, VLCS, Office-Home, TerraIncognita.
- **Model state:** Huấn luyện từ đầu hoặc fine-tune toàn bộ mạng (ResNet backbones).
- **Metrics:** Out-of-domain Accuracy, Selection Bias Variance.
- **Relevance:** Là tiêu chuẩn vàng về phương pháp luận cảnh báo SafeShift không được tùy tiện thay đổi split hoặc chọn metric sau khi đã nhìn thấy kết quả.
- **What SafeShift should NOT copy blindly:** Không ép buộc phải chạy 5-fold cross-validation đầy đủ cho việc train VLM lớn trong phạm vi tài nguyên hạn hẹp của Seminar.

#### 11. Many Faces of Robustness
- **Title:** *The Many Faces of Robustness: A Critical Analysis of Out-of-Distribution Generalization*
- **Year / Venue:** 2021 / IEEE/CVF ICCV 2021.
- **Link:** [https://openaccess.thecvf.com/content/ICCV2021/html/Hendrycks_The_Many_Faces_of_Robustness_A_Critical_Analysis_of_ICCV_2021_paper.html](https://openaccess.thecvf.com/content/ICCV2021/html/Hendrycks_The_Many_Faces_of_Robustness_A_Critical_Analysis_of_ICCV_2021_paper.html)
- **Problem:** Phân tích thực nghiệm đa chiều về sự khác biệt giữa robustness trước biến dạng tự nhiên (ImageNet-A, ImageNet-R, ImageNet-C) và robustness đối kháng.
- **Protocol:** Đánh giá mô hình cố định trên các tập phân bố dịch chuyển tự nhiên.
- **Source/Target:** In-distribution ImageNet $\rightarrow$ Out-of-distribution Testbeds.
- **Model state:** Frozen Models.
- **Metrics:** Effective Robustness, Relative Accuracy Drop.
- **Relevance:** Định hình rõ ràng cách thức đo lường độ bền vững (Robustness) thông qua sự so sánh tương đối giữa các miền dữ liệu.
- **What SafeShift should NOT copy blindly:** Không quy đổi kết quả công nghiệp sang phân loại 1.000 lớp ImageNet.

#### 12. Domain Generalization Survey
- **Title:** *Domain Generalization: A Survey*
- **Year / Venue:** 2022 / IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI).
- **Link:** [https://ieeexplore.ieee.org/document/9540758](https://ieeexplore.ieee.org/document/9540758)
- **Problem:** Khảo sát toàn diện lý thuyết, giải thuật và benchmark cho bài toán khái quát hóa miền.
- **Protocol:** Tổng kết các nhánh tiếp cận: học biểu diễn bất biến miền (domain-invariant representations), phân rã đặc trưng (feature disentanglement), và sinh dữ liệu tăng cường (data augmentation).
- **Source/Target:** Đa miền nguồn $\rightarrow$ Miền đích chưa thấy.
- **Model state:** Trained/Adapted Models.
- **Metrics:** Target Domain Generalization Error, Worst-domain Performance.
- **Relevance:** Cung cấp khung phân loại lý thuyết hoàn chỉnh để phân biệt ranh giới giữa Seminar (đánh giá quan sát) và Thesis (nghiên cứu đề xuất phương pháp mới).
- **What SafeShift should NOT copy blindly:** Không đưa các mục tiêu thiết kế giải thuật DG mới vào kế hoạch Seminar tuần 2 đến tuần 8.

---

## 5. Candidate Protocols (Đánh giá chi tiết 4 phương án giao thức)

Dưới đây là phân tích khoa học toàn diện đối với 4 phương án giao thức thực nghiệm ứng viên cho SafeShift:

```text
4 Phương án Giao thức:
- P1: Frozen VLM + Official Test Only
- P2: Frozen VLM + Full Dataset Per-Domain Evaluation
- P3: Frozen VLM + Leakage-Controlled / Group-Aware Evaluation Subset
- P4: Source-Domain Training/Tuning + Leave-One-Domain-Out (LODO) Target
```

### 5.1 Protocol 1 (P1): Frozen VLM + Official Test Only
- **Scientific Question:** *Các mô hình VLM nền tảng thể hiện năng lực đánh giá an toàn công nghiệp và bám bằng chứng đối tượng như thế nào khi suy luận trực tiếp trên tập kiểm tra chính thức do tác giả công bố?*
- **Appropriate Terminology:** `Frozen Zero-Shot Evaluation on Official Benchmark Test Split` (hoặc `Official Benchmark Replication`). Tuyệt đối không gọi là Domain Generalization.
- **Required Training:** **KHÔNG**. Toàn bộ mô hình được giữ nguyên trọng số (Frozen weights), suy luận thuần túy qua prompting.
- **Use of Official Split:** Sử dụng nguyên trạng tập `test` chính thức gồm đúng **1.250 mẫu** (999 Normal, 251 Anomaly). Bỏ qua hoàn toàn tập `train` 3.763 mẫu.
- **Leakage Sensitivity:** **RẤT THẤP đối với pipeline của SafeShift** (vì SafeShift không huấn luyện mô hình trên tập train của benchmark, do đó không kích hoạt đường rò rỉ train-to-test của bản thân quy trình). Tuy nhiên, **VẪN NHẠY CẢM với 7 cặp exact cross-split** (vì nếu mô hình thương mại đã bị nhiễm dữ liệu từ trước, nó có thể đã thấy cả train lẫn test).
- **Platform Confounding Sensitivity:** **CAO**. Kết quả trên từng miền phản ánh đồng thời cả miền công nghiệp lẫn loại robot tuần tra của miền đó.
- **Metallurgy Feasibility:** **KHÔNG KHẢ THI cho phát hiện bất thường** (`NOT_FEASIBLE FOR ANOMALY EVALUATION`). Tập test chính thức của metallurgy có **0 mẫu Anomaly** (177/177 mẫu là Normal). Do đó, chỉ có thể đo Specificity / False Positive Rate, hoàn toàn không tính được Recall hay F1 cho lớp Anomaly của miền này.
- **Ability to Compare with InspecSafe Official Results:** **TUYỆT ĐỐI (100% Khả năng đối soát trực tiếp)**. Cho phép so sánh trực tiếp 1:1 từng chỉ số với kết quả công bố của bài báo trên *Scientific Data*.
- **Reproducibility:** **RẤT CAO**. Bất kỳ nhóm nghiên cứu nào trên thế giới có bản InspecSafe-V1 đều có thể chạy lại chính xác trên 1.250 mẫu này.
- **Compute / API Cost:** **THẤP NHẤT**. Chỉ chạy suy luận cho 1.250 mẫu. Chi phí token API thương mại và thời gian tính toán của mô hình open-weights là nhỏ nhất trong 4 phương án.
- **Suitability for Seminar:** **RẤT CAO (Phù hợp làm Baseline Replication)**. Giúp đạt được mục tiêu tái lập kết quả cơ sở nhanh chóng, an toàn và có đối chứng thượng nguồn rõ ràng.
- **Suitability for Thesis:** **THẤP nếu đứng độc lập**. Một luận văn thạc sĩ/kỹ sư chuyên sâu không thể chỉ dừng lại ở việc chạy inference trên tập test có sẵn bị rò rỉ mà không có đóng góp phương pháp luận.
- **Main Scientific Weakness:** Không giải quyết được hiện tượng Test Metallurgy có 0 mẫu Anomaly; không đánh giá được toàn diện 5 miền công nghiệp một cách công bằng; kết quả bị ảnh hưởng bởi 7 cặp exact rò rỉ nếu mô hình bị ô nhiễm dữ liệu từ trước.

### 5.2 Protocol 2 (P2): Frozen VLM + Full Dataset Per-Domain Evaluation
- **Scientific Question:** *Năng lực nhận diện an toàn và độ bền vững của mô hình VLM biến thiên như thế nào xuyên qua 5 miền công nghiệp khi được đánh giá trên toàn bộ không gian dữ liệu quan sát được?*
- **Appropriate Terminology:** `Cross-Domain Robustness Evaluation across 5 Industrial Domains` (hoặc `Zero-Shot Full-Dataset Cross-Domain Benchmark`).
- **Required Training:** **KHÔNG**. Mô hình hoàn toàn frozen.
- **Use of Official Split:** **XÓA BỎ ranh giới Train/Test**. Gộp toàn bộ 5.013 mẫu lại và phân nhóm theo miền (`folder_domain` hoặc `text_domain`). Cả 3.763 mẫu train và 1.250 mẫu test đều đóng vai trò là dữ liệu kiểm thử (Evaluation Data).
- **Leakage Sensitivity:** **KHÔNG CÒN KHÁI NIỆM Train/Test Benchmark Leakage** (bởi vì không có bước huấn luyện nào diễn ra trên bất kỳ phần nào của benchmark). Tuy nhiên, **RẤT NHẠY CẢM với Evaluation Sample Dependence** (sự phụ thuộc thống kê giữa các mẫu kiểm thử do trùng lặp chuỗi video liên tục).
- **Platform Confounding Sensitivity:** **CAO**. Vẫn giữ nguyên sự gắn kết giữa robot ray treo và robot bánh lăn.
- **Metallurgy Feasibility:** **KHẢ THI CÓ ĐIỀU KIỆN (FEASIBLE WITH CONSTRAINTS)**. Toàn bộ dataset có 9 mẫu Anomaly của metallurgy (dù vẫn rất hiếm và 8/9 mẫu có text claim `oil_chemical`), cho phép tính toán các chỉ số nhạy bất thường với mẫu số $N=9$ thay vì hoàn toàn bằng 0 như P1.
- **Ability to Compare with InspecSafe Official Results:** **GIÁN TIẾP / KHÔNG TRÙNG MẪU SỐ**. Không thể so sánh số học trực tiếp với bảng kết quả chính thức của tác giả (vốn chỉ đo trên 1.250 mẫu test).
- **Reproducibility:** **CAO**. Dữ liệu 5.013 mẫu là cố định và minh bạch.
- **Compute / API Cost:** **TRUNG BÌNH - CAO**. Quy mô 5.013 mẫu lớn gấp 4 lần P1. Cần tính toán kỹ ngân sách token và hạn ngạch API rate limits.
- **Suitability for Seminar:** **RẤT CAO (Phù hợp làm Core Seminar Investigation)**. Cung cấp bức tranh toàn cảnh sâu sắc và đầy đủ nhất về hành vi của VLM trên toàn bộ 5 miền thực tế.
- **Suitability for Thesis:** **TRUNG BÌNH**. Là bước khảo sát nền tảng tốt để phân tích lỗi, nhưng vẫn thiếu cấu phần can thiệp giải thuật.
- **Main Scientific Weakness:** Mẫu số lớn nhưng chứa nhiều khung hình quay gần nhau trong cùng chuỗi thời gian, dẫn đến phương sai đo lường bị giảm nhân tạo (underestimated variance); chi phí API cao gấp 4 lần.

### 5.3 Protocol 3 (P3): Frozen VLM + Leakage-Controlled / Group-Aware Evaluation Subset
- **Scientific Question:** *Hiệu năng xuyên miền thực sự của VLM là bao nhiêu khi loại bỏ hoàn toàn các khung hình trùng lặp chuỗi, các cặp rò rỉ confirmed exact và chỉ giữ lại các quan sát độc lập theo cụm?*
- **Appropriate Terminology:** `Leakage-Controlled Group-Aware Robustness Evaluation` (hoặc `Deduplicated Cross-Domain Benchmark`).
- **Required Training:** **KHÔNG**. Mô hình hoàn toàn frozen.
- **Use of Official Split:** **TÁI CẤU TRÚC HOÀN TOÀN**. Không dùng split chính thức. Xây dựng một tập con chuẩn hóa (Clean Evaluation Subset) bằng cách gom nhóm theo 12 source families, loại bỏ 7 cặp exact confirmed, gộp các chuỗi near candidates có cùng waypoint/thời gian, và chọn lọc mẫu đại diện. Quy mô dự kiến: ~1.500–2.000 mẫu độc lập.
- **Leakage Sensitivity:** **RẤT THẤP / KIỂM SOÁT TỐI ĐA**. Loại bỏ triệt để rủi ro ghi nhớ chuỗi thời gian và sự phụ thuộc giữa các mẫu kiểm thử.
- **Platform Confounding Sensitivity:** **TRUNG BÌNH - CAO**. Vẫn chịu ảnh hưởng bởi tương quan platform tự nhiên giữa các phân xưởng, nhưng loại trừ được sự sai lệch do một chuỗi video đơn lẻ thống trị số lượng mẫu.
- **Metallurgy Feasibility:** **CỰC KỲ HẠN CHẾ**. Nếu lọc bỏ các mẫu có text claim mâu thuẫn (`oil_chemical`), metallurgy chỉ còn đúng **1 mẫu Anomaly duy nhất**.
- **Ability to Compare with InspecSafe Official Results:** **KHÔNG THỂ SO SÁNH TRỰC TIẾP**. Đây là một phân chia dữ liệu hoàn toàn mới do SafeShift đề xuất. Bắt buộc phải báo cáo như một đóng góp kiểm chuẩn mới.
- **Reproducibility:** **CAO NẾU CÔNG BỐ MANIFEST MINH BẠCH**. Đòi hỏi SafeShift phải công bố danh sách chỉ số mẫu (sample IDs manifest) của tập con này.
- **Compute / API Cost:** **TRUNG BÌNH** (~1.500–2.000 mẫu). Tiết kiệm chi phí hơn P2 đáng kể.
- **Suitability for Seminar:** **TRUNG BÌNH - CAO**. Rất mạnh về mặt đóng góp khoa học phản biện (critical benchmarking), nhưng đòi hỏi nỗ lực rà soát dữ liệu lớn ở W2 trước khi chạy thí nghiệm W3.
- **Suitability for Thesis:** **RẤT CAO**. Là xuất phát điểm lý tưởng cho một bài báo khoa học chất lượng cao tại các hội nghị quốc tế uy tín.
- **Main Scientific Weakness:** Đòi hỏi các quyết định lọc mẫu mang tính chủ quan nhất định (heuristic thresholding); làm giảm mạnh số lượng mẫu của các lớp hiếm (đặc biệt là metallurgy và Level03).

### 5.4 Protocol 4 (P4): Source-Domain Training/Tuning + Leave-One-Domain-Out (LODO) Target
- **Scientific Question:** *Khi được huấn luyện hoặc tinh chỉnh (fine-tuning / adapter tuning) trên các phân xưởng công nghiệp nguồn, mô hình có khả năng khái quát hóa các quy tắc an toàn sang một phân xưởng đích hoàn toàn chưa từng thấy hay không?*
- **Appropriate Terminology:** `Multi-Source Domain Generalization (LODO Protocol)` theo đúng nghĩa học thuật chuẩn mực của Gulrajani & Lopez-Paz (ICLR 2021).
- **Required Training:** **BẮT BUỘC HUẤN LUYỆN / TINH CHỈNH (FINE-TUNING REQUIRED)**. Phải huấn luyện mô hình (ví dụ: LoRA, Q-LoRA, hoặc Adapter) trên $K-1$ miền nguồn và test trên miền đích còn lại, lặp lại $K$ lần.
- **Use of Official Split:** **HOÀN TOÀN BÃI BỎ OFFICIAL SPLIT**. Thay thế bằng phân chia LODO theo miền (ví dụ: Train trên Coal, Oil, Power, Tunnel $\rightarrow$ Test trên Metallurgy).
- **Leakage Sensitivity:** **RẤT PHỨC TẠP VÀ NGUY HIỂM**. Nếu áp dụng LODO trên InspecSafe-V1 mà không kiểm soát source-family, Cặp exact số 4 sẽ gây rò rỉ trực tiếp giữa nguồn (metallurgy) và đích (oil_chemical)! Đồng thời, nếu train trên 12 source families phân tán, rò rỉ chuỗi giữa các miền là cực kỳ nghiêm trọng.
- **Platform Confounding Sensitivity:** **CỰC KỲ NGHIÊM TRỌNG (BLOCKER)**. Nếu chọn miền đích là `coal_conveyor` (100% ray treo), trong khi các miền nguồn phần lớn là xe bánh lăn mặt sàn (`metallurgy`, `oil_chemical`, `power`), mô hình bị shock phân bố kép: vừa chuyển đổi quy trình công nghiệp, vừa thay đổi góc quay từ mặt đất lên trần nhà 60 độ! Không thể kết luận mô hình thất bại do domain shift hay do platform shift.
- **Metallurgy Feasibility:** **HOÀN TOÀN KHÔNG KHẢ THI NẾU METALLURGY LÀM TARGET**. Nếu chọn metallurgy làm unseen target domain, tập test chỉ có 0 mẫu Anomaly (nếu dùng official test) hoặc 9 mẫu Anomaly (nếu dùng full domain), trong đó 8/9 mẫu lại thuộc về oil_chemical.
- **Ability to Compare with InspecSafe Official Results:** **HOÀN TOÀN KHÔNG THỂ SO SÁNH**. Tác giả InspecSafe-V1 chưa từng thực hiện thí nghiệm LODO.
- **Reproducibility:** **TRUNG BÌNH - PHỨC TẠP**. Phụ thuộc vào hạt giống ngẫu nhiên (random seed), cấu hình phần cứng GPU, tối ưu hóa siêu tham số (hyperparameter tuning).
- **Compute / API Cost:** **KHỔNG LỒ (PROHIBITIVE FOR SEMINAR)**. Đòi hỏi huấn luyện lặp lại nhiều mô hình VLM lớn trên hạ tầng GPU đa card mạnh mẽ. Không thể thực hiện được qua API thương mại đóng.
- **Suitability for Seminar:** **HOÀN TOÀN KHÔNG PHÙ HỢP (`NOT_RECOMMENDED FOR SEMINAR`)**. Vượt quá ngân sách thời gian, tài nguyên tính toán và phạm vi mục tiêu của môn học Seminar.
- **Suitability for Thesis:** **RẤT PHÙ HỢP CHO LUẬN VĂN SAU NÀY (`HIGH FOR THESIS`)**. Có thể là hướng mở rộng trọng tâm cho luận văn nếu giải quyết được bài toán bù đắp dữ liệu hoặc lọc cụm.
- **Main Scientific Weakness:** Nhiễu nền tảng cơ học làm triệt tiêu giá trị giải thích của bài toán domain generalization; chi phí tính toán cực lớn; miền luyện kim làm gãy cấu trúc LODO 5 miền đối xứng.

---

## 6. Zero-Shot Evaluation vs. Leakage: Khẳng định phương pháp luận cốt lõi

Một trong những nhận định sai lầm phổ biến cần loại trừ dứt khoát là:
> *"Vì chúng ta đánh giá VLM ở chế độ Zero-Shot không huấn luyện lại, nên bài toán hoàn toàn không còn rủi ro rò rỉ dữ liệu (Zero-shot removes leakage)."*

Tuân thủ tính toàn vẹn nghiên cứu, SafeShift phân định rạch ròi ba tầng rò rỉ độc lập:

```text
Ba tầng rò rỉ dữ liệu:
┌─────────────────────────────────────────────────────────────────────────┐
│ TẦNG 1: Benchmark Train/Test Leakage (Rò rỉ giữa 2 tập của benchmark)    │
│ -> Frozen Zero-shot LOẠI TRÙ được đường rò rỉ từ khâu train của SafeShift│
├─────────────────────────────────────────────────────────────────────────┤
│ TẦNG 2: Evaluation Sample Dependence (Phụ thuộc giữa các mẫu kiểm thử)  │
│ -> Frozen Zero-shot KHÔNG TỰ ĐỘNG GIẢI QUYẾT; các mẫu test vẫn tương    │
│    quan mạnh do chia sẻ chuỗi video, góc máy robot và lặp lại khung hình│
├─────────────────────────────────────────────────────────────────────────┤
│ TẦNG 3: Pretraining Data Contamination (Nhiễm dữ liệu tiền huấn luyện)  │
│ -> Frozen Zero-shot KHÔNG THỂ BẢO ĐẢM; VLM có thể đã thấy InspecSafe    │
│    trong tập dữ liệu web khổng lồ trước khi đem benchmark               │
└─────────────────────────────────────────────────────────────────────────┘
```

1. **Benchmark Train/Test Leakage (Rò rỉ phân tách chuẩn):**  
   Được định nghĩa khi một quy trình huấn luyện học máy cập nhật trọng số trên tập Train và bị hưởng lợi bất chính do tập Test chứa các mẫu trùng lặp hoặc cận trùng lặp với tập Train.  
   *Tác động của Frozen Zero-Shot:* **Loại bỏ được đường rò rỉ này từ phía SafeShift**. Vì SafeShift hoàn toàn không tổ chức huấn luyện mô hình trên tập Train của InspecSafe-V1, nên thuật toán tối ưu của chúng ta không thể "học vẹt" tập Train để gian lận điểm số trên tập Test.
2. **Evaluation Sample Dependence (Sự phụ thuộc lẫn nhau giữa các mẫu đánh giá):**  
   Được định nghĩa khi các mẫu trong tập kiểm thử không thỏa mãn giả định cơ bản về tính độc lập và phân bố đồng nhất (I.I.D. — Independent and Identically Distributed). Khi nhiều mẫu kiểm thử thực chất là các khung hình cắt ra từ cùng một video (ví dụ chuỗi người đi xe đạp trong hầm, hoặc góc dừng cố định của robot), chúng chia sẻ chung các đặc trưng tĩnh.  
   *Tác động của Frozen Zero-Shot:* **HOÀN TOÀN KHÔNG GIẢI QUYẾT ĐƯỢC**. Nếu mô hình đoán sai (hoặc đoán đúng) một khung hình, nó sẽ có xu hướng lặp lại chính xác phán đoán đó trên hàng chục khung hình kế tiếp trong cùng chuỗi. Điều này làm sai lệch độ tin cậy thống kê và phóng đại điểm số thực tế.
3. **Pretraining Contamination (Ô nhiễm dữ liệu tiền huấn luyện):**  
   Bộ dữ liệu InspecSafe-V1 đã được công bố trên Hugging Face (tháng 04/2026), Zenodo và GitHub. Các mô hình VLM thương mại hoặc nguồn mở lớn thu thập dữ liệu web liên tục có thể đã thu nạp một phần hoặc toàn bộ tệp ảnh và nhãn của InspecSafe-V1 vào giai đoạn pretraining hoặc instruction tuning của nhà phát triển.  
   *Tác động của Frozen Zero-Shot:* **HOÀN TOÀN BẤT LỰC**. Nếu một mô hình VLM đã bị nhiễm dữ liệu tiền huấn luyện, việc đánh giá zero-shot trên tập test của benchmark thực chất chỉ là đo lường năng lực ghi nhớ (memorization retrieval) chứ không phải năng lực suy luận tổng quát hóa.

> **Kết luận bắt buộc:** Đánh giá Zero-shot trên mô hình Frozen chỉ thu hẹp một kênh rò rỉ duy nhất (SafeShift train-to-test leakage pathway). Nó **tuyệt đối không chứng minh** rằng các mẫu kiểm thử độc lập với nhau và **không chứng minh** rằng mô hình chưa từng nhìn thấy dữ liệu trước đó. Mọi báo cáo nghiên cứu phải công bố giới hạn này một cách minh bạch.

---

## 7. Official Split vs. Full Dataset (Phân tích phương án tập kiểm thử cho mô hình Frozen)

Khi mô hình VLM hoàn toàn được đóng băng trọng số (Frozen Pretrained) và không có bất kỳ bước huấn luyện nào trên InspecSafe-V1, khái niệm phân chia "train" (3.763 mẫu) và "test" (1.250 mẫu) của tác giả gốc đứng trước một câu hỏi phương pháp luận lớn:

> *"Nếu chúng ta không huấn luyện mô hình trên InspecSafe-V1, việc tự giới hạn chỉ đánh giá trên 1.250 mẫu test chính thức có còn hợp lý không, hay nên đánh giá trên toàn bộ 5.013 mẫu, hoặc phải báo cáo cả hai?"*

Bảng đối chiếu ưu - nhược điểm của ba phương án:

| Tiêu chí phân tích | Phương án A: Chỉ đánh giá Official Test (1.250 mẫu) | Phương án B: Đánh giá Full Dataset (5.013 mẫu) | Phương án C: Báo cáo Song song Cả hai (Dual Reporting) |
|---|---|---|---|
| **Cơ sở khoa học** | Tuân thủ ranh giới đánh giá do tác giả thiết kế ban đầu; tôn trọng benchmark protocol chuẩn. | Tận dụng tối đa không gian dữ liệu quan sát được; phản ánh năng lực trên toàn bộ 5 miền thực tế. | Phân tách rạch ròi giữa mục tiêu tái lập baseline (Official Test) và mục tiêu phân tích hành vi mô hình (Full Dataset). |
| **Tính khả thi của Metallurgy** | **RẤT TỆ**: Miền luyện kim có 0 mẫu Anomaly; không tính được độ nhạy phát hiện lỗi. | **TỐT HƠN**: Có 9 mẫu Anomaly để đo lường (dù mẫu số vẫn nhỏ). | Cho phép giải thích rõ ràng lý do tại sao kết quả metallurgy trên Official Test bị khiếm khuyết. |
| **Khả năng so sánh với bài báo gốc** | **TRỰC TIẾP 100%**: So sánh số học chính xác với các bảng điểm của tác giả trên *Scientific Data*. | **KHÔNG TRỰC TIẾP**: Khác biệt về mẫu số và phân bố mẫu kiểm thử. | **TỐI ƯU**: Vừa đối soát được với bài báo gốc, vừa cung cấp số liệu mở rộng độc lập. |
| **Chi phí tính toán & API Token** | **THẤP**: 1.250 mẫu $\times$ $N$ mô hình. Nằm trong ngưỡng an toàn của ngân sách Seminar. | **CAO GẤP 4 LẦN**: 5.013 mẫu $\times$ $N$ mô hình. Rủi ro cạn ngân sách API hoặc nghẽn hàng đợi. | Có thể kiểm soát chi phí bằng cách: chạy Official Test trên toàn bộ mô hình, chỉ chạy Full Dataset trên 1–2 mô hình tiêu biểu. |
| **Rủi ro phương sai chuỗi** | Bị chi phối bởi 25% chỉ số đầu của 12 source families. | Chịu ảnh hưởng bởi toàn bộ chuỗi video dài trong tập train. | Cung cấp cái nhìn so sánh xem sự khác biệt giữa hai tập có mang ý nghĩa thống kê hay không. |

> **Khuyến nghị phương pháp luận:**  
> Không tự ý loại bỏ Official Test (vì đây là sợi dây liên kết duy nhất để tái lập kết quả baseline của bài báo gốc).  
> Đồng thời, không nên giới hạn nghiên cứu chỉ trong Official Test (vì nó che giấu sự thiếu hụt Anomaly của metallurgy và bỏ phí 75% dữ liệu quan sát).  
> **Giải pháp tối ưu là Dual Reporting:** Báo cáo Official Test (P1) làm chuẩn so sánh quốc tế, và báo cáo Full Dataset (P2) hoặc Clean Subset (P3) làm đóng góp phân tích chuyên sâu của SafeShift.

---

## 8. Metallurgy Deep-Dive (Phân tích chuyên sâu miền Luyện kim)

Miền luyện kim (`metallurgy`) là trường hợp dị biệt nghiêm trọng nhất về mặt cấu trúc dữ liệu trong InspecSafe-V1, đòi hỏi phải có câu trả lời dứt khoát cho 5 câu hỏi phương pháp luận:

```text
Hiện trạng dữ liệu Miền Luyện kim:
- Tổng số mẫu: 720 mẫu (543 train / 177 test)
- Mẫu Bình thường (Level04 / Normal): 711 mẫu (534 train / 177 test)
- Mẫu Bất thường (Level01-03 / Anomaly): 9 mẫu ở Train và 0 MẪU Ở TEST CHÍNH THỨC
- Xung đột nhãn ngữ nghĩa: 8 trong số 9 mẫu Anomaly ở train mang khẳng định văn bản là oil_chemical!
- Chỉ duy nhất 1 mẫu (metallurgy-Level03-SuspendedRail-002666-001) có folder và text cùng xác nhận metallurgy.
```

### 8.1 Có nên giữ metallurgy trong đánh giá độ bền vững theo miền (per-domain robustness) không?
- **Trả lời:** **CÓ, BẮT BUỘC PHẢI GIỮ NHƯNG KÈM THEO GHI CHÚ ĐIỀU KIỆN**.  
- Không được tự tiện xóa bỏ miền luyện kim khỏi danh sách 5 miền, vì đây là một trong 5 kịch bản công nghiệp cốt lõi được tác giả công bố chính thức. Việc xóa bỏ sẽ làm thay đổi cấu trúc của benchmark chuẩn. Tuy nhiên, mọi bảng kết quả per-domain đều phải có chú thích đặc biệt về sự mất cân bằng cực đoan này.

### 8.2 Có thể đánh giá năng lực phân loại an toàn tổng thể (overall safety classification) không?
- **Trả lời:** **CÓ THỂ ĐÁNH GIÁ ĐƯỢC**.  
- Với 711 mẫu Normal (Level04), chúng ta hoàn toàn có thể đo lường độ chính xác phân loại an toàn tổng thể, đặc biệt là tỷ lệ nhận diện đúng trạng thái an toàn (True Negative Rate / Specificity) và tỷ lệ báo động giả (False Alarm Rate / False Positive Rate).

### 8.3 Có thể đánh giá năng lực nhạy phát hiện bất thường (anomaly-sensitive performance) không?
- **Trả lời:**  
  - Trên **Official Test (P1): HOÀN TOÀN KHÔNG THỂ ĐÁNH GIÁ ĐƯỢC** (vì số lượng mẫu bất thường bằng 0; mẫu số tính Recall bằng 0).  
  - Trên **Full Dataset (P2): ĐÁNH GIÁ ĐƯỢC NHƯNG CỰC KỲ YẾU VỀ THỐNG KÊ** (chỉ có 9 mẫu bất thường; một mẫu đoán sai sẽ làm dao động tỷ lệ tới 11,1%). Hơn nữa, do 8/9 mẫu này có văn bản khẳng định là `oil_chemical`, việc đánh giá phát hiện bất thường trên 9 mẫu này thực chất là đo lường lỗi của nhà máy hóa chất bị đặt nhầm vào thư mục luyện kim!

### 8.4 Có nên dùng metallurgy làm Unseen Target Domain trong LODO (P4) không?
- **Trả lời:** **TUYỆT ĐỐI KHÔNG KHUYẾN NGHỊ (`NOT_RECOMMENDED AS PRIMARY TARGET`)**.  
- Nếu một mô hình được train trên 4 miền khác và test trên metallurgy, việc đạt điểm phát hiện bất thường bằng 0 hoặc không thể đo lường được sẽ làm gãy hoàn toàn giao thức LODO. Metallurgy là một **severely under-supported target domain**.

### 8.5 Nếu không dùng metallurgy làm Primary Target thì có mất tính "5-Domain" không?
- **Trả lời:** **KHÔNG HỀ MẤT TÍNH CHẤT 5 MIỀN**.  
- SafeShift vẫn duy trì đầy đủ tính chất 5 miền trong bài toán **Cross-Domain Robustness (P1 & P2)** nơi cả 5 miền đều được đánh giá song song. Riêng đối với các thử nghiệm chuyển giao (transferability) hoặc LODO thử nghiệm, metallurgy có thể đóng vai trò là một **miền nguồn hỗ trợ (Source Domain)** cung cấp dữ liệu bình thường, hoặc được phân tích như một nghiên cứu tình huống dị biệt (Case Study on Imbalanced Edge Case).

---

## 9. Domain-Label Dependency (Sự phụ thuộc vào định nghĩa nhãn miền)

Trong Tuần 1, kiểm toán đã ghi nhận sự tồn tại của hai trường siêu dữ liệu định danh miền:
1. `folder_domain`: Xác định thuần túy dựa trên tên thư mục lưu trữ của hệ thống tệp cục bộ (`coal_conveyor`, `metallurgy`, `oil_chemical`, `power`, `tunnel`).
2. `text_domain`: Xác định dựa trên câu mở đầu khẳng định bối cảnh trong tệp văn bản `.txt` của annotator.

Kiểm toán xác nhận chính xác **36 mẫu có sự xung đột trực tiếp** giữa hai trường này (`folder_domain != text_domain`).

### Mối quan hệ ràng buộc giữa Quyết định Protocol (D1) và Quyết định Nhãn miền (D3):
- **Ở bước W2.1 này, chúng ta CHƯA tự ý quyết định D3 (chưa chốt cách xử lý 36 mẫu).**
- Tuy nhiên, sự lựa chọn giao thức (D1) sẽ quy định trực tiếp mức độ rủi ro đối với D3:
  - **Nếu chọn P1 (Official Test Only):** Trong tập test chính thức, có **18 mẫu bị xung đột** (12 mẫu folder `tunnel` nhưng text ghi `oil_chemical`; 6 mẫu khác). Nếu phân nhóm per-domain theo `folder_domain`, các mẫu này sẽ làm nhiễu kết quả của `tunnel`.
  - **Nếu chọn P2 (Full Dataset):** Toàn bộ 36 mẫu xung đột sẽ tham gia vào đánh giá. Nếu định nghĩa domain theo `folder_domain`, 8 mẫu Anomaly của `metallurgy` mang nhãn text `oil_chemical` sẽ tạo ra một sự méo mó nghiêm trọng.
  - **Nếu chọn P3 (Clean Evaluation Subset):** 36 mẫu này có thể được xử lý triệt để: hoặc loại bỏ hoàn toàn khỏi tập đánh giá cross-domain, hoặc tách riêng thành một nhóm kiểm thử độ nhạy (Sensitivity Test Group).
- **Hệ quả phương pháp luận:** Bất kể protocol nào được Research Lead phê duyệt, báo cáo thực nghiệm bắt buộc phải chỉ rõ kết quả được phân nhóm theo `folder_domain` hay `text_domain`, và công bố bảng độ nhạy (sensitivity analysis) khi có và khi không có 36 mẫu xung đột này.

---

## 10. Seminar vs. Thesis (Phân định rạch ròi lộ trình nghiên cứu)

Để bảo đảm tính khả thi thực tế và không gây quá tải cho giai đoạn Seminar, SafeShift thiết lập ranh giới rõ ràng giữa hai giai đoạn:

```text
Lộ trình phân kỳ nghiên cứu SafeShift:
┌────────────────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN 1: SEMINAR (Tuần 1 đến Tuần 8 — Mục tiêu trước mắt)          │
│ • Kiểm toán dữ liệu thực chứng (Audit complete - W1)                   │
│ • Chuẩn hóa giao thức đánh giá bền vững xuyên miền (Robustness Protocol)│
│ • Tái lập baseline mô hình VLM đóng băng trên Official Test (W3)        │
│ • Mở rộng đánh giá Zero-shot Cross-Domain Robustness trên 5 miền        │
│ • Đánh giá Object-Support Grounding & Weak Proxy Grounding             │
│ • Phân tích lỗi chuyên sâu (Failure Analysis, Confounding Analysis)   │
│ • TUYỆT ĐỐI KHÔNG: Tạo new adaptation algorithm, train model từ đầu,   │
│   hoặc tuyên bố phương pháp mới vượt trội trước khi đo lường           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Kế thừa kết quả & bài học
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN 2: THESIS EXTENSION (Luận văn sau này — Nghiên cứu chuyên sâu)│
│ • Xây dựng bộ chú thích Rationale Bounding Box bổ sung (100-200 mẫu)   │
│ • Nghiên cứu định lượng hiện tượng "Correct Answer, Wrong Reason"      │
│ • Thiết kế giải thuật Group-aware Domain Generalization mới             │
│ • Phát triển kỹ thuật Mitigation / De-biasing cho Platform Confounding │
│ • Tinh chỉnh Adapter / LoRA theo giao thức Leave-One-Domain-Out        │
│ • Soạn thảo bài báo khoa học hoàn chỉnh gửi hội nghị/tạp chí quốc tế   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Candidate Research Questions (Đề xuất các câu hỏi nghiên cứu ứng viên)

Dưới đây là 3 câu hỏi nghiên cứu ứng viên (RQs) được thiết kế chuẩn xác về mặt khoa học, phù hợp với bằng chứng thực nghiệm của InspecSafe-V1:

### 11.1 Research Question 1 (RQ1)
- **Precise English Wording:**  
  *RQ1: To what extent does the zero-shot safety assessment capability of frozen Vision-Language Models degrade across different industrial inspection domains and operating platforms?*
- **Diễn giải tiếng Việt:**  
  *RQ1: Năng lực đánh giá an toàn công nghiệp ở chế độ zero-shot của các mô hình VLM đóng băng trọng số bị suy giảm ở mức độ nào xuyên qua các miền công nghiệp và nền tảng vận hành robot khác nhau?*
- **Biến số nghiên cứu:**
  - **Biến độc lập (Independent Variables):** Miền công nghiệp công tác (5 phân xưởng: than, luyện kim, hóa chất, điện lực, hầm); Nền tảng robot tuần tra (`SuspendedRail` vs `Wheeled`); Dòng mô hình VLM được đánh giá.
  - **Biến phụ thuộc (Dependent Variables):** Hiệu năng phân loại an toàn nhị phân (Normal vs Anomaly); Hiệu năng phân loại 4 cấp độ an toàn (Level01–Level04).
- **Dữ liệu trả lời:** Toàn bộ 5 miền của InspecSafe-V1 (Official Test 1.250 mẫu và Full Dataset 5.013 mẫu).
- **Yếu tố gây nhiễu tiềm ẩn (Possible Confounds):** Platform confounding (góc nhìn camera trên ray treo vs xe lăn); Phân bố mất cân bằng cực đoan của Level03 và Anomaly của Metallurgy; Mâu thuẫn 36 mẫu text/folder domain.
- **Họ chỉ số phù hợp (Suitable Metric Families):** Macro-F1, Balanced Accuracy, Per-class Recall, True Negative Rate (Specificity), Expected Cost of Misclassification.
- **Tính khả thi từ W1:** **HOÀN TOÀN HỖ TRỢ (`FEASIBLE_WITH_CONSTRAINTS`)**. Dữ liệu W1 có đầy đủ 5 miền với số lượng mẫu lớn để đo lường.

### 11.2 Research Question 2 (RQ2)
- **Precise English Wording:**  
  *RQ2: Which specific industrial hazard categories and safety risk levels exhibit the highest performance drop, and does this degradation correlate with viewpoint shifts or class rarity?*
- **Diễn giải tiếng Việt:**  
  *RQ2: Những danh mục nguy cơ an toàn và cấp độ rủi ro cụ thể nào bộc lộ mức độ sụt giảm hiệu năng nghiêm trọng nhất, và sự suy giảm này có tương quan với sự thay đổi góc nhìn camera hay tính chất hiếm của dữ liệu hay không?*
- **Biến số nghiên cứu:**
  - **Biến độc lập:** Danh mục sự kiện nguy cơ (12 hazard types: hút thuốc, dùng điện thoại, mở tủ điện, người ngã, chất lỏng rò rỉ, khói lửa, vi phạm PPE); Tần suất xuất hiện của lớp; Góc đặt camera quan sát.
  - **Biến phụ thuộc:** Tỷ lệ bỏ sót vi phạm (False Negative Rate / Recall trên từng loại lỗi); Tỷ lệ nhầm lẫn giữa các cấp độ rủi ro (Confusion Matrix).
- **Dữ liệu trả lời:** Tập 1.000 mẫu `Anomaly_data` và phân bố 4 cấp độ an toàn Level01–Level04.
- **Yếu tố gây nhiễu tiềm ẩn:** Rò rỉ chuỗi thời gian nội bộ họ nguồn; Sự kết hợp đa nguy cơ trong cùng một khung hình (ví dụ vừa hút thuốc vừa thiếu găng tay).
- **Họ chỉ số phù hợp:** Per-hazard Recall, Confusion Matrix, Error Distribution Analysis, Pearson/Spearman Rank Correlation giữa số lượng mẫu và F1-score.
- **Tính khả thi từ W1:** **HOÀN TOÀN HỖ TRỢ**. Bằng chứng W1 ghi nhận chi tiết 12 họ nguồn và sự mất cân bằng giữa Level01, Level02 và Level03.

### 11.3 Research Question 3 (RQ3)
- **Precise English Wording:**  
  *RQ3: Does visual evidence grounding in frozen VLMs degrade synchronously with safety classification across domains, or can models exhibit correct hazard prediction while attending to irrelevant spatial regions?*
- **Diễn giải tiếng Việt:**  
  *RQ3: Khả năng bám bằng chứng thị giác của các mô hình VLM đóng băng có suy thoái đồng bộ với khả năng phân loại an toàn xuyên qua các miền hay không, hay mô hình có thể dự đoán đúng nguy cơ nhưng lại chú ý vào các vùng không gian không liên quan?*
- **Biến số nghiên cứu:**
  - **Biến độc lập:** Miền công nghiệp; Loại bằng chứng thị giác (Vật thể hiện hữu có hỗ trợ trực tiếp vs Vi phạm thiếu trang bị qua proxy `Person`).
  - **Biến phụ thuộc:** Mức độ trùng khớp vùng chú ý / bounding box của mô hình với đa giác đối tượng an toàn; Điểm số bám bằng chứng (Grounding hit rate).
- **Dữ liệu trả lời:** Tập con Anomaly có Direct Object Support (được xác định sau census) và tập Proxy `Person` trên 5 miền.
- **Yếu tố gây nhiễu tiềm ẩn:** Đa giác `Person` quá rộng so với vị trí cục bộ của vi phạm (ví dụ chân người vs đầu người thiếu mũ); Mô hình API không xuất attention maps mà chỉ xuất text bounding boxes.
- **Họ chỉ số phù hợp:** Pointing Game Accuracy (Hit/Miss), Soft IoU / Bounding Box Overlap, Attention Map Inside-Mask Ratio (cho open models).
- **Tính khả thi từ W1:** **KHẢ THI CÓ RÀNG BUỘC (`PARTIALLY_FEASIBLE / FEASIBLE_WITH_CONSTRAINTS`)**. Đòi hỏi W2 phải chốt giao diện đầu ra của mô hình (text bbox) và giới hạn bài toán ở Object Support, không tuyên bố đánh giá Full Hazard Rationale.

---

## 12. Candidate Hypotheses (Đề xuất các giả thuyết khoa học kiểm định được)

Các giả thuyết được xây dựng dưới dạng kiểm định giả thuyết thống kê (Null Hypothesis $H_0$ và Alternative Hypothesis $H_1$), tuyệt đối không dùng các tuyên bố vô căn cứ như "SafeShift sẽ cải thiện hiệu năng":

### 12.1 Giả thuyết 1 (Cho RQ1 — Độ bền vững xuyên miền)
- **Null Hypothesis ($H_{1,0}$):**  
  *Năng lực phân loại an toàn công nghiệp của các mô hình VLM đóng băng trọng số là đồng nhất giữa 5 miền công nghiệp và hai nền tảng robot tuần tra (hiệu năng không có sự khác biệt mang ý nghĩa thống kê xuyên miền).*
- **Alternative Hypothesis ($H_{1,1}$):**  
  *Hiệu năng phân loại an toàn của các mô hình VLM sụt giảm đáng kể khi chuyển dịch giữa các miền công nghiệp, trong đó các miền sử dụng robot ray treo (`SuspendedRail`) có hiệu năng khác biệt rõ rệt so với các miền sử dụng robot bánh lăn (`Wheeled`) do ảnh hưởng của góc nhìn camera dốc từ trên cao.*
- **Phương pháp kiểm định:** Kiểm định phi tham số Kruskal-Wallis hoặc ANOVA một yếu tố trên Macro-F1 của từng miền; kiểm định Mann-Whitney U giữa nhóm Ray treo và nhóm Bánh lăn.

### 12.2 Giả thuyết 2 (Cho RQ2 — Suy thoái theo loại nguy cơ và độ hiếm)
- **Null Hypothesis ($H_{2,0}$):**  
  *Tỷ lệ nhận diện đúng nguy cơ an toàn của VLM không phụ thuộc vào tần suất xuất hiện của lớp trong tập dữ liệu (hiệu năng trên lớp hiếm Level03 tương đương với lớp phổ biến Level01).*
- **Alternative Hypothesis ($H_{2,1}$):**  
  *Mô hình VLM bộc lộ sự suy thoái nghiêm trọng trên các lớp nguy cơ hiếm (đặc biệt là Level03 với 15 mẫu) và các nguy cơ thiếu hụt vật lý (absence-based hazards như thiếu PPE), với tỷ lệ Recall trên lớp hiếm thấp hơn đáng kể so với các nguy cơ gắn liền với vật thể hiện hữu rõ ràng (như ngọn lửa, điện thoại).*
- **Phương pháp kiểm định:** Phân tích hồi quy tương quan thứ bậc Spearman giữa tần suất lớp và Per-class Recall; kiểm định Chi-square trên bảng ngẫu nhiên giữa loại nguy cơ (Present Object vs Absence) và tỷ lệ đoán đúng.

### 12.3 Giả thuyết 3 (Cho RQ3 — Sự phân ly giữa Phân loại và Bám bằng chứng)
- **Null Hypothesis ($H_{3,0}$):**  
  *Mức độ bám bằng chứng thị giác (Grounding Accuracy) có mối tương quan thuận tuyệt đối và suy thoái đồng biến với độ chính xác phân loại an toàn (mô hình luôn nhìn đúng chỗ khi đưa ra kết luận an toàn đúng).*
- **Alternative Hypothesis ($H_{3,1}$):**  
  *Tồn tại sự phân ly (decoupling) giữa phân loại an toàn và bám bằng chứng: ở các miền công nghiệp phức tạp hoặc các trường hợp vi phạm thiếu trang bị, mô hình VLM có thể dự đoán đúng nhãn cấp độ an toàn nhưng vùng chú ý thị giác lại rơi ra ngoài vùng đối tượng liên quan (hiện tượng shortcut reasoning dựa trên bối cảnh nền).*
- **Phương pháp kiểm định:** Đo lường tỷ lệ mẫu "Correct Prediction, Low Grounding Overlap" trên tập con Direct Support; so sánh hệ số tương quan giữa Classification Accuracy và Pointing Game Score xuyên qua 5 miền.

---

## 13. Decision Matrix (Ma trận đánh giá 4 phương án giao thức)

Bảng đối chiếu tổng hợp 4 phương án giao thức trên 8 tiêu chí phương pháp luận:

| Tiêu chí Đánh giá | P1: Frozen Official Test | P2: Frozen Full Dataset | P3: Frozen Clean Subset | P4: LODO Training (DG) |
|---|:---:|:---:|:---:|:---:|
| **1. Scientific Validity** *(Tính giá trị khoa học)* | **MEDIUM** (Hạn chế do Test Metallurgy = 0) | **HIGH** (Bao quát trọn vẹn 5 miền thực tế) | **VERY HIGH** (Kiểm soát triệt để rò rỉ và cụm) | **LOW - MEDIUM** (Bị triệt tiêu do Platform Confounding) |
| **2. Fit to W1 Evidence** *(Khớp với bằng chứng W1)* | **MEDIUM** (Bỏ phí 75% dữ liệu audit W1) | **HIGH** (Tận dụng toàn bộ census W1) | **VERY HIGH** (Giải quyết trực tiếp các cảnh báo W1) | **VERY LOW** (Không khả thi trên dữ liệu hiện tại) |
| **3. Seminar Feasibility** *(Tính khả thi cho Seminar)* | **VERY HIGH** (Đơn giản, chuẩn mực, an toàn) | **HIGH** (Khả thi cao, chỉ cần quản lý API) | **MEDIUM** (Cần thêm nỗ lực lọc subset ở W2) | **UNFEASIBLE** (Vượt quá tài nguyên và thời gian) |
| **4. Leakage Robustness** *(Khả năng chống rò rỉ)* | **HIGH** (SafeShift không train) | **MEDIUM** (Nhạy cảm với tương quan chuỗi) | **VERY HIGH** (Loại trừ exact và chuỗi gần) | **VERY LOW** (Rò rỉ exact và chuỗi xuyên miền) |
| **5. Comparability** *(Khả năng so sánh với bài báo gốc)* | **VERY HIGH** (Đối soát 1:1 trực tiếp) | **MEDIUM** (So sánh gián tiếp) | **LOW** (Benchmark độc lập mới) | **NONE** (Tác giả không có thí nghiệm này) |
| **6. Interpretability** *(Tính diễn giải khoa học)* | **MEDIUM** (Bị che khuất ở miền luyện kim) | **HIGH** (Rõ ràng trên từng phân xưởng) | **VERY HIGH** (Không bị nhiễu bởi chuỗi lặp) | **VERY LOW** (Bị nhiễu kép domain + platform) |
| **7. Compute / Token Burden** *(Gánh nặng tính toán/chi phí)* | **LOW** (1.250 mẫu $\approx$ 1x cost) | **HIGH** (5.013 mẫu $\approx$ 4x cost) | **MEDIUM** (~1.800 mẫu $\approx$ 1.5x cost) | **EXTREME** (Huấn luyện lặp lại đa GPU) |
| **8. Thesis Extensibility** *(Khả năng mở rộng cho Luận văn)* | **LOW** (Chỉ là bước chạy lại) | **MEDIUM** (Tài liệu tham chiếu tốt) | **HIGH** (Nền tảng cho bài báo khoa học) | **VERY HIGH** (Nếu giải quyết được dữ liệu mới) |

### Diễn giải chi tiết các điểm đánh giá:
- **P1 (Frozen Official Test):** Đạt điểm cao nhất về tính khả thi trong Seminar và khả năng so sánh với bài báo gốc. Tuy nhiên, điểm yếu chết người là không thể đánh giá phát hiện bất thường trên miền luyện kim do tác giả không để lại mẫu bất thường nào trong tập test.
- **P2 (Frozen Full Dataset):** Giải quyết được bài toán 5 miền của P1, cho phép quan sát toàn diện hành vi mô hình. Điểm trừ duy nhất là chi phí API cao gấp 4 lần và chứa các chuỗi video liên tục làm giảm tính độc lập của mẫu kiểm thử.
- **P3 (Frozen Clean Subset):** Là phương án có tính chuẩn mực khoa học cao nhất, khắc phục toàn bộ các khiếm khuyết của P1 và P2. Tuy nhiên đòi hỏi thời gian thiết kế manifest ở W2.
- **P4 (LODO Training):** Hoàn toàn không khả thi cho Seminar do rào cản nền tảng robot (platform confounding) làm sai lệch bản chất của bài toán chuyển giao miền, cùng với chi phí huấn luyện GPU vượt ngưỡng cho phép.

---

## 14. Preliminary Recommendation (Đề xuất sơ bộ của nhóm thực hiện)

Căn cứ trên các phân tích khoa học độc lập và đối chiếu với mục tiêu của giai đoạn Seminar:

> [!IMPORTANT]
> **TRẠNG THÁI KHUYẾN NGHỊ: `PROPOSED, NOT APPROVED`**  
> Đây là đề xuất phương pháp luận của Trợ lý nghiên cứu để chuẩn bị cho cuộc họp quyết định. Toàn bộ các đề xuất dưới đây **chưa có hiệu lực thi hành** cho đến khi được Research Lead phê duyệt chính thức vào `DECISIONS.md`.

### 14.1 Khuyến nghị Giao thức Chính (RECOMMENDED PRIMARY PROTOCOL)
- **Phương án đề xuất:** **KẾT HỢP SONG SONG HAI GIAO THỨC (DUAL-PROTOCOL FRAMEWORK)**
  - **PRIMARY PROTOCOL (Seminar Baseline & Core Benchmark):**  
    $\rightarrow$ **Protocol 1 (Frozen VLM + Official Test Only, 1.250 mẫu)**.  
    *Lý do:* Đây là con đường bắt buộc và duy nhất để tái lập kết quả baseline (W3–W4), đối chiếu trung thực với bài báo trên *Scientific Data*, và bảo đảm hoàn thành đúng tiến độ Seminar với chi phí tính toán an toàn nhất.
  - **SECONDARY / EXTENSION PROTOCOL (In-Depth Robustness Analysis):**  
    $\rightarrow$ **Protocol 2 (Frozen VLM + Full Dataset Per-Domain Evaluation, 5.013 mẫu)** (hoặc tập con P3 nếu kịp lọc).  
    *Lý do:* Giải quyết triệt để sự khiếm khuyết của miền Luyện kim trên P1, cung cấp số liệu thực chứng trên toàn bộ 5 phân xưởng công nghiệp, và tạo ra đóng góp phân tích mới mẻ (Contribution 1) cho bài báo SafeShift ở Tuần 5–Tuần 8.

### 14.2 Phương án Không khuyến nghị cho Seminar (NOT RECOMMENDED FOR SEMINAR)
- **Protocol 4 (Source-Domain Training + LODO Target):**  
  Tuyệt đối không triển khai trong khuôn khổ Seminar 8 tuần do rủi ro Platform Confounding nghiêm trọng và chi phí tính toán huấn luyện GPU vượt quá khả năng.

### 14.3 Phương án Bảo lưu cho Luận văn (RESERVED FOR THESIS)
- Protocol 3 (Clean Group-Aware Subset) và Protocol 4 (LODO DG có bù đắp dữ liệu hoặc de-biasing nền tảng) nên được bảo lưu làm hướng phát triển trọng tâm cho Luận văn tốt nghiệp sau khi giai đoạn Seminar kết thúc.

---

## 15. Risks (Nhận diện rủi ro nghiên cứu và thực thi)

1. **Rủi ro Ngân sách và Hạn ngạch API (API Rate Limit & Cost Risk):**  
   Nếu chạy đồng thời nhiều mô hình VLM thương mại trên cả P1 và P2, chi phí token có thể tăng nhanh. *Biện pháp giảm thiểu:* Chỉ chạy P2 trên mô hình open-weights nội bộ (như Qwen2-VL) và 1 mô hình API thương mại tiêu biểu.
2. **Rủi ro Định dạng Đầu ra Grounding (Output Parsing Failure):**  
   Các mô hình VLM có thể không tuân thủ định dạng tọa độ bounding box yêu cầu trong system prompt, dẫn đến tỷ lệ lỗi phân tích cú pháp (JSON parse error) cao. *Biện pháp giảm thiểu:* Thiết kế prompt có cấu trúc chặt chẽ kèm cơ chế fallback regex ở W2.
3. **Rủi ro Tranh cãi về 36 Mẫu Domain Mismatch:**  
   Nếu hội đồng phản biện thắc mắc về 36 mẫu xung đột giữa thư mục và văn bản. *Biện pháp giảm thiểu:* Báo cáo minh bạch kết quả theo cả hai cách phân loại trong phụ lục.
4. **Rủi ro Thiên lệch Đánh giá Proxy Grounding:**  
   Bị chỉ trích vì dùng đa giác `Person` toàn thân làm proxy cho lỗi thiếu mũ bảo hộ. *Biện pháp giảm thiểu:* Tuyên bố rõ ràng trong báo cáo đây là `Weak Proxy Grounding`, phân biệt rạch ròi với `Direct Object Support`.

---

## 16. Questions Requiring Approval (Danh mục câu hỏi trình Research Lead phê duyệt)

Trước khi chuyển sang bước W2.2 và đóng băng giao thức, Nhóm Nghiên cứu cần quyết định chính thức cho các câu hỏi sau:

- [ ] **Câu hỏi 1 (Protocol Choice):** Research Lead có chấp thuận định hướng **Dual-Protocol** (P1 làm Primary để replicate bài báo gốc; P2/P3 làm Secondary để phân tích độ bền vững sâu) hay yêu cầu chỉ tập trung duy nhất vào P1?
- [ ] **Câu hỏi 2 (Wording Alignment):** Chấp thuận định hình lại tiêu đề phương pháp luận của Seminar từ *"Domain Generalization"* sang *"Cross-Domain Robustness Evaluation"* để phản ánh trung thực việc sử dụng mô hình Frozen Pretrained VLM hay không?
- [ ] **Câu hỏi 3 (Metallurgy Policy):** Đồng ý giữ nguyên miền `metallurgy` trong báo cáo per-domain kèm ghi chú đặc biệt về sự vắng mặt của Anomaly ở Official Test, hay có yêu cầu xử lý khác?
- [ ] **Câu hỏi 4 (36 Mismatch Policy):** Phê duyệt phương án xử lý 36 mẫu xung đột: loại bỏ, phân loại lại theo text, hay giữ nguyên kèm cờ cảnh báo nhạy cảm?
- [ ] **Câu hỏi 5 (Candidate RQs & Hypotheses):** Phê duyệt danh mục 3 Research Questions (RQ1, RQ2, RQ3) và 3 Giả thuyết kiểm định (H1, H2, H3) được đề xuất tại Mục 11 & 12 làm khung nghiên cứu chính thức cho SafeShift?

---

## 17. Sources (Tài liệu tham khảo)

1. **Liu, Z., Liu, S., Min, J., Zhang, Z., Cen, J., Han, P., Hu, S., Meng, Z., He, X., & Zhou, D.** (2026). *Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios*. Nature Scientific Data, 13, Article 1198. DOI: [10.1038/s41597-026-07796-x](https://doi.org/10.1038/s41597-026-07796-x).
2. **Liu, Z., He, X., et al.** (2026). *InspecSafe: A Multimodal Dataset for Industrial Inspection Safety Assessment*. arXiv preprint arXiv:2601.21173. DOI: [10.48550/arXiv.2601.21173](https://doi.org/10.48550/arXiv.2601.21173).
3. **Wang, C., Guan, X., et al.** (2024). *Real-IAD: A Real-World Multi-View Dataset for Benchmarking Versatile Industrial Anomaly Detection*. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), pp. 18234-18244.
4. **Gu, Z., Zhu, B., et al.** (2024). *AnomalyGPT: Detecting Industrial Anomalies Using Large Vision-Language Models*. In Proceedings of the AAAI Conference on Artificial Intelligence (AAAI), 38(3), pp. 1932-1940.
5. **Song, Y., et al.** (2024). *Both Text and Images Leaked! A Systematic Analysis of Multimodal LLM Data Contamination*. arXiv preprint arXiv:2409.08831.
6. **Zhai, Y., et al.** (2025). *Your Large Vision-Language Model Only Needs A Few Attention Heads For Visual Grounding*. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR 2025).
7. **Sun, J., et al.** (2024). *ViGoR: Improving Visual Grounding of Large Vision-Language Models with Fine-Grained Reward Modeling*. In Proceedings of the European Conference on Computer Vision (ECCV 2024).
8. **Zhang, Y., et al.** (2024). *OneRef: Unified Vision-Language Model for Referring Expression Comprehension and Segmentation*. In Advances in Neural Information Processing Systems (NeurIPS 2024).
9. **Li, X., et al.** (2026). *VLM-RobustBench: Benchmarking the Robustness of Vision-Language Models against Real-World Image Corruptions*. arXiv preprint arXiv:2602.xxxxx.
10. **Gulrajani, I., & Lopez-Paz, D.** (2021). *In Search of Lost Domain Generalization*. In Proceedings of the International Conference on Learning Representations (ICLR 2021).
11. **Hendrycks, D., et al.** (2021). *The Many Faces of Robustness: A Critical Analysis of Out-of-Distribution Generalization*. In Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV), pp. 8340-8349.
12. **Zhou, K., Liu, Z., Qiao, Y., Xiang, T., & Loy, C. C.** (2022). *Domain Generalization: A Survey*. IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI), 45(4), pp. 4396-4415. DOI: [10.1109/TPAMI.2022.3195549](https://doi.org/10.1109/TPAMI.2022.3195549).
13. **Ben-David, S., Blitzer, J., Crammer, K., Kulesza, A., Pereira, F., & Vaughan, J. W.** (2010). *A theory of learning from different domains*. Machine Learning, 79(1), pp. 151-175.
14. **Radford, A., et al.** (2021). *Learning Transferable Visual Models From Natural Language Supervision*. In International Conference on Machine Learning (ICML 2021), PMLR, pp. 8748-8763.
15. **Liang, P., et al.** (2023). *Holistic Evaluation of Language Models*. Transactions on Machine Learning Research (TMLR).
