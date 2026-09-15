# W2 Protocol Decision Brief

**Phân tích phương pháp luận để lựa chọn câu hỏi nghiên cứu và giao thức đánh giá xuyên miền cho SafeShift**  
*Dự án SafeShift — Giai đoạn: Tuần 2 (Research Protocol), Bước W2.1*  
*Tài liệu hỗ trợ quyết định (Decision Brief) trình Research Lead và Hội đồng dự án*  
*Ngày lập: 15/09/2026 (Bản hoàn thiện: 15/09/2026)*  
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
> **(C) Hai giao thức song song** *(với phân định rõ ràng vai trò Baseline Replication Protocol và Primary Research Protocol Candidate)*?

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
   *Hệ quả:* Tác động của miền công nghiệp và nền tảng robot bị gắn liền quan sát (co-varying), hạn chế khả năng phân tách nguyên nhân độc lập.
7. **Giới hạn Khắc nghiệt của Miền Luyện kim (`metallurgy`):** Miền này có 720 mẫu nhưng chỉ có 9 mẫu Anomaly ở train và **0 mẫu Anomaly ở test chính thức**; đồng thời 8/9 mẫu train Anomaly mang khẳng định văn bản là `oil_chemical` (`carry an oil_chemical textual domain claim`).
8. **36 Mẫu Xung đột Tên miền:** Xác nhận 36 mẫu có sự mâu thuẫn trực tiếp giữa tên thư mục (`folder_domain`) và khẳng định ngữ cảnh trong tệp văn bản (`text_domain`).
9. **Hiện trạng Annotation Grounding:** Dataset có **37.434 đa giác đối tượng (`object polygon annotations`)** trên 231 nhãn thô, **HOÀN TOÀN KHÔNG CÓ** native bounding boxes, không có vùng bằng chứng nguy cơ chuyên biệt (`hazard evidence region`), không có vùng lý do con người (`human rationale region`), không có tọa độ cho vi phạm thiếu vật thể (`absent-object annotation`).
10. **Tập Mẫu Khảo sát 63 Anomaly:** Thẩm định trên 63 mẫu phân tầng cho thấy chỉ có **20,6% (13/63)** mẫu có hỗ trợ trực tiếp từ vật thể hiện hữu (`DIRECT_SUPPORT`); **73,0% (46/63)** chỉ có thể đánh giá qua đại diện gián tiếp (`PARTIAL_PROXY` qua `Person`). Tỷ lệ này chỉ mô tả trong tập 63 mẫu, không tự ý ngoại suy sang toàn bộ dataset.
11. **Mất Cân bằng Cực đoan về Cấp An toàn:** `Level04` (Normal) chiếm 80,05% (4.013 mẫu), trong khi `Level03` chỉ có 15 mẫu (0,30%), tạo tỷ số mất cân bằng **267,53 : 1**. 100% mẫu Level03 thuộc về robot ray treo.

---

## 3. Terminology (Phân biệt chuẩn xác thuật ngữ chuyên ngành)

Nhằm duy trì tính trung thực học thuật và sự chuẩn xác về mặt lý thuyết, SafeShift phân định rạch ròi 7 thuật ngữ cốt lõi dựa trên các tài liệu nền tảng đã được bình duyệt:

### 3.1 Domain Shift (Dịch chuyển miền dữ liệu)
- **Định nghĩa học thuật:** Hiện tượng phân bố xác suất đồng thời $P(X, Y)$ thay đổi giữa môi trường thu thập dữ liệu nguồn $\mathcal{S}$ và môi trường đích $\mathcal{T}$, tức là $P_{\mathcal{S}}(X, Y) \neq P_{\mathcal{T}}(X, Y)$. Sự dịch chuyển này có thể bắt nguồn từ covariate shift ($P(X)$ đổi, $P(Y|X)$ giữ nguyên), concept shift ($P(Y|X)$ đổi), hoặc prior probability shift ($P(Y)$ đổi).
- **Nguồn trích dẫn:** *Ben-David et al., "A theory of learning from different domains", Machine Learning, 2010; Quinonero-Candela et al., "Dataset Shift in Machine Learning", MIT Press, 2009.*
- **Ý nghĩa với SafeShift:** Trong InspecSafe-V1, sự thay đổi giữa các phân xưởng than, hóa chất, luyện kim, trạm điện và hầm cáp tạo ra sự thay đổi đồng thời cả về đặc trưng thị giác quang học $P(X)$ lẫn phân bố nhãn nguy cơ an toàn $P(Y)$.

### 3.2 Domain Generalization (DG — Khái quát hóa miền)
- **Định nghĩa học thuật:** Bài toán học máy trong đó mô hình được tối ưu hóa/huấn luyện (training, fine-tuning, representation learning) trên một hoặc nhiều miền nguồn quan sát được $\mathcal{D}_S = \{\mathcal{S}_1, \mathcal{S}_2, ..., \mathcal{S}_K\}$ sao cho mô hình đạt được sai số kỳ vọng nhỏ nhất trên một miền đích $\mathcal{D}_T$ **hoàn toàn chưa từng thấy trong quá trình huấn luyện** ($\mathcal{D}_T \cap \mathcal{D}_S = \emptyset$), mà **không được tiếp cận bất kỳ dữ liệu nào (kể cả ảnh không nhãn) của miền đích**.
- **Nguồn trích dẫn:** *Gulrajani & Lopez-Paz, "In Search of Lost Domain Generalization", ICLR 2021; Zhou et al., "Domain Generalization: A Survey", IEEE TPAMI, 2022.*
- **Cơ chế VLM trong DG hiện đại:** Các công trình tiêu biểu như Addepalli et al. (CVPR 2024) và Chen et al. (PracticalDG, CVPR 2024) chứng minh rằng DG đòi hỏi quá trình huấn luyện/chưng cất (training / distillation / prompt tuning) trên miền nguồn nhằm tối ưu hóa biểu diễn bất biến miền. Nếu không có khâu huấn luyện trên benchmark, bài toán không thể gọi là Domain Generalization theo nghĩa học máy chuẩn.

### 3.3 Domain Adaptation (DA — Thích nghi miền)
- **Định nghĩa học thuật:** Bài toán trong đó mô hình học trên dữ liệu có nhãn ở miền nguồn $\mathcal{D}_S$ và được tiếp cận một tập dữ liệu (thường là không có nhãn — Unsupervised Domain Adaptation, UDA) từ chính miền đích $\mathcal{D}_T$ trong quá trình huấn luyện để căn chỉnh biểu diễn đặc trưng (feature alignment).
- **Nguồn trích dẫn:** *Ganin et al., "Domain-adversarial training of neural networks", JMLR 2016; Wang & Deng, "Deep visual domain adaptation: A survey", Neurocomputing, 2018.*
- **Ý nghĩa với SafeShift:** SafeShift ở giai đoạn hiện tại **không** thực hiện Domain Adaptation, vì mục tiêu là kiểm tra năng lực sẵn có của mô hình trên môi trường mới mà không chạy các vòng lặp căn chỉnh thích nghi.

### 3.4 Cross-Domain Robustness (Độ bền vững xuyên miền)
- **Định nghĩa học thuật:** Năng lực duy trì hiệu năng ổn định, không bị suy thoái quá mức (performance degradation / gap) của một hệ thống hoặc mô hình khi phân bố kiểm thử dịch chuyển sang các miền hoặc môi trường hoạt động khác nhau so với miền kiểm chuẩn ban đầu, đo lường độ nhạy cảm của mô hình đối với các biến thiên phân bố mà không thực hiện thêm bước huấn luyện nào trên các miền đó.
- **Nguồn trích dẫn:** *Hendrycks et al., "Many Faces of Robustness: A Critical Analysis of Out-of-Distribution Generalization", ICCV 2021; Liang et al., "Holistic Evaluation of Language Models (HELM)", TMLR 2023.*
- **Ý nghĩa với SafeShift:** Đây là thuật ngữ chính xác nhất cho trường hợp đo đạc các mô hình VLM dựng sẵn trên 5 phân xưởng công nghiệp của InspecSafe-V1.

### 3.5 Zero-Shot Evaluation (Đánh giá không huấn luyện thêm trên benchmark)
- **Định nghĩa học thuật:** Phương thức đánh giá năng lực của một mô hình nền tảng (Foundation Model / Pretrained VLM) trực tiếp trên tập dữ liệu đích chỉ thông qua các chỉ dẫn ngôn ngữ (text prompts) hoặc cấu hình suy luận mặc định, **hoàn toàn không cập nhật bất kỳ trọng số nào và không sử dụng mẫu huấn luyện nào từ benchmark đích**.
- **Nguồn trích dẫn:** *Radford et al., "Learning Transferable Visual Models From Natural Language Supervision (CLIP)", ICML 2021; Zanella & Ben Ayed, "On the Test-Time Zero-Shot Generalization of Vision-Language Models: Do We Really Need Prompt Learning?", CVPR 2024.*
- **Ý nghĩa với SafeShift:** Như Zanella & Ben Ayed (CVPR 2024) phân tích, thiết lập test-time zero-shot hoàn toàn không có tham số học tập trên miền nguồn, phân biệt triệt để với các phương pháp prompt learning có huấn luyện. Đánh giá zero-shot bảo đảm SafeShift không tạo thêm rò rỉ qua khâu huấn luyện benchmark, nhưng **không đồng nghĩa với việc loại bỏ hoàn toàn các dạng rò rỉ khác** (xem Mục 6).

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

Dưới đây là các công trình nghiên cứu tiêu biểu từ 2024 đến 2026 xuất bản tại các hội nghị/tạp chí hàng đầu (CVPR, ECCV, NeurIPS, ICLR, AAAI, Nature Scientific Data) liên quan trực tiếp đến các trục bài toán của SafeShift:

```text
Danh mục công trình khảo sát:
1.  Liu et al. (Nature Scientific Data 2026) — InspecSafe Benchmark
2.  Wang et al. (CVPR 2024) — Real-IAD Multi-View Industrial Anomaly
3.  Gu et al. (AAAI 2024) — AnomalyGPT for Industrial Anomaly Detection
4.  Song et al. (Findings of EMNLP 2025 / arXiv 2024) — Multimodal LLM Data Contamination
5.  Park et al. (ICLR 2026) — Multi-Modal Semantic Perturbation Contamination Detection
6.  Kang et al. (CVPR 2025) — LVLM Attention Heads for Visual Grounding
7.  Yan et al. (ECCV 2024) — ViGoR: Fine-Grained Reward Modeling for Visual Grounding
8.  Xiao et al. (NeurIPS 2024) — OneRef: Unified One-tower Grounding & Segmentation
9.  Saxena et al. (arXiv 2026) — VLM-RobustBench: Real-World Corruptions
10. Addepalli et al. (CVPR 2024) — Leveraging VLMs for Domain Generalization
11. Chen et al. (CVPR 2024) — PracticalDG: Perturbation Distillation on VLMs
12. Zanella & Ben Ayed (CVPR 2024) — Test-Time Zero-Shot Generalization of VLMs
13. Gulrajani & Lopez-Paz (ICLR 2021) — DomainBed: Methodology & Selection Bias
14. Hendrycks et al. (ICCV 2021) — Faces of Robustness & Distribution Shifts
15. Zhou et al. (IEEE TPAMI 2022) — Domain Generalization Survey & Benchmarks
```

### Chi tiết từng bài báo:

#### 1. InspecSafe Benchmark
- **Title:** *Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios*
- **Year / Venue:** 2026 / *Nature Scientific Data* (Vol 13, Art 1198, DOI: 10.1038/s41597-026-07796-x).
- **Link:** [https://doi.org/10.1038/s41597-026-07796-x](https://doi.org/10.1038/s41597-026-07796-x)
- **Problem:** Xây dựng benchmark đa phương thức đầu tiên cho bài toán đánh giá an toàn kiểm tra công nghiệp trên 5 miền hoạt động của robot.
- **Protocol:** Đánh giá 15 mô hình VLM đương đại trên tập kiểm tra chính thức 1.250 mẫu (tham chiếu trực tiếp Bảng và Hình trong bài báo chính thức).
- **Source/Target:** Chia split cố định (train 3.763 / test 1.250). Không định nghĩa rõ ràng nguồn/đích cross-domain.
- **Model state:** Frozen Pretrained Models (Zero-shot / Few-shot).
- **Metrics:** Official Primary Metrics gồm: **Safety-level Accuracy** (độ chính xác phân loại cấp an toàn) và **Semantic Similarity using BGE-M3** (độ tương đồng ngữ nghĩa câu mô tả văn bản). Confusion matrices đóng vai trò là phân tích bổ trợ (supplementary analysis). Paper không sử dụng F1-score làm primary metric.
- **Relevance:** Là bộ dữ liệu nền tảng và bài báo gốc mà SafeShift kế thừa và đánh giá lại.
- **What SafeShift should NOT copy blindly:** Không sao chép việc báo cáo độ chính xác tổng thể đơn thuần trên split chính thức mà bỏ qua 7 cặp exact rò rỉ, 826 dHash candidates, rò rỉ chuỗi video và sự kiện Test Metallurgy Anomaly = 0.

#### 2. Real-IAD
- **Title:** *Real-IAD: A Real-World Multi-View Dataset for Benchmarking Versatile Industrial Anomaly Detection*
- **Year / Venue:** 2024 / IEEE/CVF CVPR 2024, pp. 22883–22892.
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
- **Year / Venue:** 2024 / AAAI 2024, Vol. 38, No. 3, pp. 1932–1940 (Article 27963, DOI: 10.1609/aaai.v38i3.27963).
- **Link:** [https://ojs.aaai.org/index.php/AAAI/article/view/27963](https://ojs.aaai.org/index.php/AAAI/article/view/27963)
- **Problem:** Ứng dụng mô hình VLM lớn để phát hiện và định vị bất thường công nghiệp mà không cần ngưỡng thủ công.
- **Protocol:** Huấn luyện bộ decoder nhẹ (lightweight prompt learner / decoder) trên ảnh bất thường mô phỏng kết hợp với LLM.
- **Source/Target:** Thử nghiệm trên MVTec AD và VisA; đánh giá cross-object generalization.
- **Model state:** Fine-tuned lightweight layers trên nền frozen LLM.
- **Metrics:** Báo cáo các kết quả chủ đạo gồm: **Accuracy**, **Image-level AUC**, và **Pixel-level AUC**. (Không mô tả Precision / Recall / Localization IoU như các chỉ số chính thức nếu không được thẩm định từ paper).
- **Relevance:** Chứng minh tiềm năng đối thoại và khả năng định vị lỗi của VLM trong ngữ cảnh công nghiệp.
- **What SafeShift should NOT copy blindly:** Không vội vàng huấn luyện thêm adapter/decoder ở giai đoạn Seminar khi dữ liệu InspecSafe-V1 có rủi ro rò rỉ chuỗi nghiêm trọng.

#### 4. Multimodal Contamination Analysis (MM-Detect)
- **Title:** *Both Text and Images Leaked! A Systematic Analysis of Data Contamination in Multimodal LLM*
- **Year / Venue:** 2024/2025 / Findings of EMNLP 2025 (arXiv:2411.03823 đóng vai trò là bản lưu trữ preprint).
- **Link:** [https://arxiv.org/abs/2411.03823](https://arxiv.org/abs/2411.03823)
- **Problem:** Phân tích có hệ thống hiện tượng rò rỉ đồng thời cả văn bản lẫn hình ảnh của các benchmark phổ biến vào tập tiền huấn luyện của MLLMs.
- **Protocol:** Đề xuất khung kiểm định MM-Detect nhằm phát hiện mức độ rò rỉ dữ liệu đa phương thức.
- **Source/Target:** Đối chiếu giữa dữ liệu benchmark công khai và phản ứng của mô hình khi đưa vào biến đổi kiểm định.
- **Model state:** Frozen Frontier Models.
- **Metrics / Detection quantities:** Sử dụng các đại lượng kiểm định: **CR** (Correct Rate), **PCR** (Perturbed Correct Rate), **$\Delta$** (dataset-level performance change), **$\Phi$** (instance leakage metric), và các cấp độ ô nhiễm (**contamination degree categories**).
- **Relevance:** Cung cấp cơ sở lý thuyết chứng minh rằng zero-shot evaluation trên mô hình thương mại không miễn nhiễm với benchmark leakage nếu benchmark đã được crawl lên mạng.
- **What SafeShift should NOT copy blindly:** Không tự tiện tuyên bố rằng mô hình VLM "chắc chắn chưa thấy" InspecSafe-V1; cần tra cứu và ghi nhận rõ mốc training cutoff của từng mô hình.

#### 5. Multi-Modal Semantic Perturbations
- **Title:** *Contamination Detection for VLMs using Multi-Modal Semantic Perturbations*
- **Year / Venue:** 2026 / ICLR 2026 Conference Paper (Authors: Jaden Park, Mu Cai, Feng Yao, et al.).
- **Link:** [https://openreview.net/forum?id=gk6OC3XIZW](https://openreview.net/forum?id=gk6OC3XIZW)
- **Problem:** Phân biệt khả năng tổng quát hóa thực sự với việc học vẹt (rote memorization) do ô nhiễm dữ liệu tiền huấn luyện.
- **Protocol:** Đưa vào các nhiễu loạn ngữ nghĩa nhỏ (semantic perturbations) trên cả ảnh và câu hỏi để kiểm tra độ nhạy của mô hình dưới các thiết lập ô nhiễm có kiểm soát.
- **Source/Target:** Các benchmark VQA và reasoning chuẩn.
- **Model state:** Frozen VLMs.
- **Metrics / Evaluation:** Quy trình đánh giá so sánh hiệu năng của mô hình trên benchmark gốc so với benchmark bị nhiễu loạn ngữ nghĩa (original vs semantically perturbed benchmarks) và xem xét độ sụt giảm hiệu năng tương ứng dưới các thiết lập ô nhiễm có kiểm soát (*controlled contamination settings*).
- **Relevance:** Phương pháp luận giá trị để SafeShift nhận thức rõ về tính độc lập của các mô hình VLM đối với dữ liệu kiểm chuẩn.
- **What SafeShift should NOT copy blindly:** Không đưa bài toán phát hiện contamination thành mục tiêu chính của Seminar vì vượt quá phạm vi tài nguyên tính toán.

#### 6. LVLM Attention Heads for Visual Grounding
- **Title:** *Your Large Vision-Language Model Only Needs A Few Attention Heads For Visual Grounding*
- **Year / Venue:** 2025 / IEEE/CVF CVPR 2025, pp. 9339–9350 (Authors: Seil Kang, Jinyeong Kim, Junhyeok Kim, Seong Jae Hwang).
- **Link:** [https://openaccess.thecvf.com/content/CVPR2025/html/Kang_Your_Large_Vision-Language_Model_Only_Needs_A_Few_Attention_Heads_CVPR_2025_paper.html](https://openaccess.thecvf.com/content/CVPR2025/html/Kang_Your_Large_Vision-Language_Model_Only_Needs_A_Few_Attention_Heads_CVPR_2025_paper.html)
- **Problem:** Khai thác các attention heads đặc thù trong kiến trúc Transformer của VLM để định vị đối tượng mà không cần tinh chỉnh toàn bộ mạng.
- **Protocol:** Trích xuất attention maps từ các tầng sâu của vision-language cross-attention trên mô hình đóng băng.
- **Source/Target:** RefCOCO, Flickr30k Entities.
- **Model state:** Frozen Pretrained VLM (chỉ khai thác nội tại attention).
- **Metrics:** Pointing Game Accuracy, Attention Map Overlap, Top-1 Hit Rate.
- **Relevance:** Là cơ sở phương pháp luận cốt lõi cho hướng tiếp cận Object-Support Grounding của SafeShift mà không cần huấn luyện lại mô hình.
- **What SafeShift should NOT copy blindly:** Không thể áp dụng trực tiếp cho các mô hình API hộp đen thương mại vì các API này không trả về ma trận attention; SafeShift cần tách biệt giao thức bounding box text-output cho API và attention maps cho open-weights models.

#### 7. ViGoR: Visual Grounding Reward Modeling
- **Title:** *ViGoR: Improving Visual Grounding of Large Vision-Language Models with Fine-Grained Reward Modeling*
- **Year / Venue:** 2024 / ECCV 2024 (Authors: Siming Yan, Min Bai, Weifeng Chen, Xiong Zhou, Qixing Huang, Li Erran Li; Official ECVA Paper ID: 07792).
- **Link:** [https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/07792.pdf](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/07792.pdf)
- **Problem:** Nâng cao khả năng bám bằng chứng thị giác và giảm thiểu ảo giác (hallucination) trong các mô hình thị giác-ngôn ngữ lớn.
- **Protocol:** Xây dựng mô hình phần thưởng phân giải mịn (fine-grained reward modeling), kết hợp kỹ thuật lấy mẫu loại bỏ (rejection sampling) và tinh chỉnh mô hình (fine-tuning).
- **Source/Target:** Dữ liệu chuẩn COCO/RefCOCO sang bối cảnh open-world.
- **Model state:** Trained/Fine-tuned VLM với reward modeling.
- **Metrics:** Đánh giá trên POPE (hallucination), MME benchmark, và các bộ kiểm chuẩn factuality/grounding chuẩn. Paper không tự chế ra các chỉ số Grounding AP riêng lẻ.
- **Relevance:** Nhấn mạnh rằng mô hình VLM thường xuyên gặp lỗi bám sai vị trí đối tượng dù câu trả lời ngôn ngữ có vẻ hợp lý.
- **What SafeShift should NOT copy blindly:** Không đặt mục tiêu train reward model trong phạm vi Seminar; giữ nguyên mức đánh giá suy luận quan sát.

#### 8. OneRef: Unified Grounding
- **Title:** *OneRef: Unified One-tower Expression Grounding and Segmentation with Mask Referring Modeling*
- **Year / Venue:** 2024 / NeurIPS 2024 (Authors: Linhui Xiao, Xiaoshan Yang, Fang Peng, Yaowei Wang, Changsheng Xu).
- **Link:** [https://proceedings.neurips.cc/paper_files/paper/2024/hash/fcd812a51b8f8d05cfea22e3c9c4b369-Abstract-Conference.html](https://proceedings.neurips.cc/paper_files/paper/2024/hash/fcd812a51b8f8d05cfea22e3c9c4b369-Abstract-Conference.html) (PDF chính thức: [Paper-Conference.pdf](https://proceedings.neurips.cc/paper_files/paper/2024/file/fcd812a51b8f8d05cfea22e3c9c4b369-Paper-Conference.pdf)).
- **Problem:** Hợp nhất bài toán định vị bounding box và phân đoạn mặt nạ pixel dưới một kiến trúc tháp đơn (one-tower) với mô hình hóa tham chiếu mặt nạ.
- **Protocol:** Đánh giá năng lực liên kết cụm từ - vùng ảnh (phrase-to-region alignment).
- **Source/Target:** RefCOCO, RefCOCO+, RefCOCOg.
- **Model state:** Fine-tuned unified architecture.
- **Metrics:** Box IoU, Precision@0.5, cIoU, Mask mIoU.
- **Relevance:** Khẳng định sự khác biệt giữa bài toán khoanh hộp bao và bài toán phân đoạn chi tiết.
- **What SafeShift should NOT copy blindly:** Không đòi hỏi InspecSafe-V1 phải cung cấp phrase-to-region alignment khi tệp TXT vốn dĩ chỉ là một câu mô tả chung không đánh dấu token.

#### 9. VLM-RobustBench
- **Title:** *VLM-RobustBench: A Comprehensive Benchmark for Robustness of Vision-Language Models*
- **Year / Venue:** 2026 / arXiv preprint arXiv:2603.06148 (Authors: Rohit Saxena, Alessandro Suglia, Pasquale Minervini).
- **Link:** [https://arxiv.org/abs/2603.06148](https://arxiv.org/abs/2603.06148)
- **Problem:** Đánh giá toàn diện độ bền vững của các mô hình VLM hàng đầu trước các dạng biến dạng ảnh thực tế.
- **Protocol:** Áp dụng hệ thống biến dạng có kiểm soát trên ảnh kiểm thử và đo lường độ suy giảm hiệu năng.
- **Source/Target:** Tập dữ liệu gốc $\rightarrow$ Tập biến dạng OOD.
- **Model state:** Frozen Pretrained VLMs (arXiv preprint, chưa qua peer-review chính thức).
- **Metrics:** Mean Corruption Error (mCE), Relative Degradation Rate, Robust Accuracy.
- **Relevance:** Khẳng định phát hiện: VLM hiện đại rất mạnh về suy luận ngữ nghĩa (semantically strong) nhưng rất dễ tổn thương trước các biến dạng không gian và góc nhìn (spatially fragile). Điều này giải thích trực tiếp hiện tượng platform confounding của SafeShift.
- **What SafeShift should NOT copy blindly:** Không áp dụng các bộ biến dạng nhân tạo (synthetic corruptions) làm loãng trọng tâm khảo sát 5 môi trường công nghiệp thực tế của InspecSafe-V1.

#### 10. Leveraging VLMs for Domain Generalization (Addepalli et al.)
- **Title:** *Leveraging Vision-Language Models for Improving Domain Generalization in Image Classification*
- **Year / Venue:** 2024 / IEEE/CVF CVPR 2024, pp. 23922–23932 (Authors: Sravanti Addepalli, Ashish Ramayee Asokan, Lakshay Sharma, R. Venkatesh Babu).
- **Link:** [https://openaccess.thecvf.com/content/CVPR2024/html/Addepalli_Leveraging_Vision-Language_Models_for_Improving_Domain_Generalization_in_Image_Classification_CVPR_2024_paper.html](https://openaccess.thecvf.com/content/CVPR2024/html/Addepalli_Leveraging_Vision-Language_Models_for_Improving_Domain_Generalization_in_Image_Classification_CVPR_2024_paper.html)
- **Problem:** Khai thác đặc trưng từ các mô hình VLM lớn để tăng cường năng lực khái quát hóa miền (DG) cho các bộ phân loại hình ảnh.
- **Protocol:** Huấn luyện trên miền nguồn (source-domain learning) sử dụng thông tin ngôn ngữ đa phương thức để định hướng không gian đặc trưng bất biến miền.
- **Source/Target:** Các benchmark DG kinh điển (DomainNet, Office-Home, PACS).
- **Model state:** Trained/Adapted downstream classifier với VLM feature guidance.
- **Metrics:** Out-of-distribution Target Accuracy.
- **Relevance:** Minh chứng rõ ràng rằng Domain Generalization (DG) đòi hỏi bắt buộc phải có khâu huấn luyện/học tập trên miền nguồn (source-domain training).
- **What SafeShift should NOT copy blindly:** Không đánh đồng bài toán này với việc đánh giá VLM hoàn toàn frozen không qua huấn luyện.

#### 11. PracticalDG (Chen et al.)
- **Title:** *PracticalDG: Perturbation Distillation on Vision-Language Models for Hybrid Domain Generalization*
- **Year / Venue:** 2024 / IEEE/CVF CVPR 2024, pp. 23501–23511 (Authors: Zining Chen, Weiqiu Wang, Zhicheng Zhao, Fei Su, Aidong Men, Hongying Meng).
- **Link:** [https://openaccess.thecvf.com/content/CVPR2024/html/Chen_PracticalDG_Perturbation_Distillation_on_Vision-Language_Models_for_Hybrid_Domain_Generalization_CVPR_2024_paper.html](https://openaccess.thecvf.com/content/CVPR2024/html/Chen_PracticalDG_Perturbation_Distillation_on_Vision-Language_Models_for_Hybrid_Domain_Generalization_CVPR_2024_paper.html)
- **Problem:** Chuyển giao tri thức khái quát hóa miền thông qua chưng cất nhiễu loạn trên VLM cho bài toán DG thực tế.
- **Protocol:** Huấn luyện mô hình học sinh thông qua cơ chế chưng cất đặc trưng có định hướng từ VLM trên tập nguồn.
- **Source/Target:** Multi-source training $\rightarrow$ Unseen target domain.
- **Model state:** Trained student network thông qua distillation.
- **Metrics:** Target Domain Accuracy, Generalization Gap.
- **Relevance:** Củng cố luận điểm phương pháp luận: DG trong kỷ nguyên VLM là bài toán tối ưu hóa có dữ liệu nguồn nhằm đạt được tính bất biến miền.
- **What SafeShift should NOT copy blindly:** Không triển khai pipeline chưng cất phức tạp này vào phạm vi Seminar.

#### 12. Test-Time Zero-Shot Generalization of VLMs (Zanella & Ben Ayed)
- **Title:** *On the Test-Time Zero-Shot Generalization of Vision-Language Models: Do We Really Need Prompt Learning?*
- **Year / Venue:** 2024 / IEEE/CVF CVPR 2024, pp. 23783–23793 (Authors: Maxime Zanella, Ismail Ben Ayed).
- **Link:** [https://openaccess.thecvf.com/content/CVPR2024/html/Zanella_On_the_Test-Time_Zero-Shot_Generalization_of_Vision-Language_Models_Do_We_CVPR_2024_paper.html](https://openaccess.thecvf.com/content/CVPR2024/html/Zanella_On_the_Test-Time_Zero-Shot_Generalization_of_Vision-Language_Models_Do_We_CVPR_2024_paper.html)
- **Problem:** Khảo sát năng lực tổng quát hóa zero-shot tại thời điểm kiểm thử (test-time) của VLM và đặt câu hỏi liệu các kỹ thuật prompt learning có thực sự vượt trội hơn các giải pháp không huấn luyện hay không.
- **Protocol:** Đánh giá so sánh trực tiếp giữa frozen zero-shot inference, unsupervised test-time adaptation và source-domain prompt learning trên 15 bộ dữ liệu OOD.
- **Source/Target:** Zero-shot evaluation trên các miền phân bố dịch chuyển.
- **Model state:** Frozen Pretrained VLM (hoàn toàn training-free / zero-shot).
- **Metrics:** Top-1 Accuracy across diverse distribution shifts.
- **Relevance:** Là tài liệu bảo chứng phương pháp luận trực tiếp nhất cho SafeShift: việc đánh giá VLM đóng băng (training-free) trên các miền phân bố là một nhánh nghiên cứu độc lập, có giá trị học thuật cao và hoàn toàn tách biệt với bài toán huấn luyện DG truyền thống.
- **What SafeShift should NOT copy blindly:** Không bỏ qua việc kiểm chuẩn prompting template thích hợp cho bài toán an toàn công nghiệp.

#### 13. DomainBed Benchmark (Foundational Reference)
- **Title:** *In Search of Lost Domain Generalization* (Gulrajani & Lopez-Paz, ICLR 2021).
- **Link:** [https://openreview.net/forum?id=lQdXeXDoWtI](https://openreview.net/forum?id=lQdXeXDoWtI)
- **Relevance:** Tiêu chuẩn vàng phương pháp luận: cảnh báo thiên lệch chọn lựa (selection bias) khi thiết kế benchmark OOD/DG.

#### 14. Many Faces of Robustness (Foundational Reference)
- **Title:** *The Many Faces of Robustness: A Critical Analysis of Out-of-Distribution Generalization* (Hendrycks et al., ICCV 2021, pp. 8340–8349).
- **Link:** [https://openaccess.thecvf.com/content/ICCV2021/html/Hendrycks_The_Many_Faces_of_Robustness_A_Critical_Analysis_of_ICCV_2021_paper.html](https://openaccess.thecvf.com/content/ICCV2021/html/Hendrycks_The_Many_Faces_of_Robustness_A_Critical_Analysis_of_ICCV_2021_paper.html)
- **Relevance:** Định hình rõ ràng cách thức đo lường độ bền vững (Robustness) thông qua sự so sánh tương đối giữa các miền dữ liệu dịch chuyển tự nhiên.

#### 15. Domain Generalization Survey (Foundational Reference)
- **Title:** *Domain Generalization: A Survey* (Zhou et al., IEEE TPAMI 2022, 45(4), pp. 4396–4415).
- **Link:** [https://ieeexplore.ieee.org/document/9540758](https://ieeexplore.ieee.org/document/9540758)
- **Relevance:** Cung cấp khung lý thuyết phân định rõ ràng giữa bài toán học thích nghi có huấn luyện (DG) và bài toán kiểm thử độ bền vững (Robustness).

---

## 5. Candidate Protocols (Đánh giá chi tiết 4 phương án giao thức)

Dưới đây là phân tích khoa học toàn diện đối với 4 phương án giao thức thực nghiệm ứng viên cho SafeShift:

```text
4 Phương án Giao thức:
- P1: Frozen VLM + Official Test Only (Baseline Replication Protocol)
- P2: Frozen VLM + Full Dataset Per-Domain Evaluation (Primary Research Protocol Candidate)
- P3: Frozen VLM + Candidate Leakage-Sensitivity / Group-Aware Evaluation Subset
- P4: Source-Domain Training/Tuning + Leave-One-Domain-Out Target (Thesis DG Candidate)
```

### 5.1 Protocol 1 (P1): Frozen VLM + Official Test Only
- **Scientific Question:** *Các mô hình VLM nền tảng thể hiện năng lực đánh giá an toàn công nghiệp và bám bằng chứng đối tượng như thế nào khi suy luận trực tiếp trên tập kiểm tra chính thức do tác giả công bố?*
- **Appropriate Terminology:** `Frozen Zero-Shot Evaluation on Official Benchmark Test Split` (hoặc `Official Benchmark Replication`). Tuyệt đối không gọi là Domain Generalization.
- **Required Training:** **KHÔNG**. Toàn bộ mô hình được giữ nguyên trọng số (Frozen weights), suy luận thuần túy qua prompting.
- **Use of Official Split:** Sử dụng nguyên trạng tập `test` chính thức gồm đúng **1.250 mẫu** (999 Normal, 251 Anomaly). Bỏ qua tập `train` 3.763 mẫu trong khâu kiểm chuẩn này.
- **Leakage Sensitivity:** **RẤT THẤP đối với rò rỉ phát sinh từ quy trình huấn luyện của SafeShift (SafeShift-induced train→test leakage)** vì SafeShift không huấn luyện mô hình trên tập train của benchmark. Tuy nhiên, **sự phụ thuộc giữa các mẫu kiểm thử (evaluation sample dependence) và rủi ro ô nhiễm dữ liệu tiền huấn luyện (pretraining contamination) vẫn là các vấn đề mở**. Lưu ý: 7 cặp exact cross-split tự chúng là bằng chứng về việc tái sử dụng ảnh giữa train/test của benchmark, **không phải bằng chứng chứng minh mô hình đã bị ô nhiễm tiền huấn luyện**.
- **Platform Confounding Sensitivity:** **CAO**. Kết quả quan sát trên từng miền phản ánh đồng thời cả miền công nghiệp lẫn loại robot tuần tra của miền đó.
- **Metallurgy Feasibility:** **KHÔNG KHẢ THI cho phát hiện bất thường** (`NOT_CURRENTLY_FEASIBLE FOR ANOMALY EVALUATION`). Tập test chính thức của metallurgy có **0 mẫu Anomaly** (177/177 mẫu là Normal). Do đó, chỉ có thể đo Specificity / False Positive Rate, hoàn toàn không tính được Recall hay F1 cho lớp Anomaly của miền này.
- **Ability to Compare with InspecSafe Official Results:** **HIGHEST / DIRECTEST COMPARABILITY (Khả năng so sánh trực tiếp cao nhất)**, với điều kiện bắt buộc là phải tái lập chính xác: (1) câu prompt yêu cầu, (2) quy trình tiền xử lý ảnh, (3) phiên bản mô hình cụ thể, (4) cấu hình giải mã (temperature, top_p, seed), và (5) mốc snapshot API nếu dùng dịch vụ thương mại. Cần lưu ý rằng hiện tượng trôi dạt phiên bản API (API model drift) có thể khiến kết quả số học không trùng khớp tuyệt đối.
- **Reproducibility:** **RẤT CAO**. 1.250 mẫu cố định theo bản phát hành upstream.
- **Compute / API Cost:** **THẤP NHẤT**. Chỉ chạy suy luận cho 1.250 mẫu.
- **Suitability for Seminar:** **RẤT CAO (Vai trò: Baseline Replication Protocol)**. Giúp đạt được mục tiêu tái lập kết quả cơ sở nhanh chóng, an toàn và có đối chứng thượng nguồn rõ ràng tại W3.
- **Suitability for Thesis:** **THẤP nếu đứng độc lập**. Một luận văn chuyên sâu không thể chỉ dừng lại ở việc chạy inference trên tập test có sẵn bị khiếm khuyết mà không có đóng góp phương pháp luận.
- **Main Scientific Weakness:** Không giải quyết được hiện tượng Test Metallurgy có 0 mẫu Anomaly; không đánh giá được toàn diện 5 miền công nghiệp một cách công bằng; bỏ qua 75% dữ liệu quan sát được.

### 5.2 Protocol 2 (P2): Frozen VLM + Full Dataset Per-Domain Evaluation
- **Scientific Question:** *Năng lực nhận diện an toàn và độ bền vững của mô hình VLM biến thiên như thế nào xuyên qua 5 miền công nghiệp khi được đánh giá trên toàn bộ không gian dữ liệu quan sát được?*
- **Appropriate Terminology:** `Cross-Domain Robustness Evaluation across 5 Industrial Domains` (hoặc `Zero-Shot Full-Dataset Cross-Domain Benchmark`).
- **Required Training:** **KHÔNG**. Mô hình hoàn toàn frozen.
- **Use of Official Split:** **Coi toàn bộ 5.013 mẫu là một không gian đánh giá (evaluation pool)**, đồng thời **bảo lưu nguyên vẹn siêu dữ liệu phân tách gốc (`split: train/test`)** để phục vụ phân tích nguồn gốc và kiểm tra độ nhạy (sensitivity analysis). Tuyệt đối không xóa bỏ metadata train/test.
- **Leakage Sensitivity:** Không có rủi ro rò rỉ từ khâu huấn luyện benchmark của SafeShift (vì không có training). Tuy nhiên, **cần thận trọng với sự phụ thuộc giữa các mẫu kiểm thử (Evaluation Sample Dependence)**: các ước lượng khoảng tin cậy ngây thơ theo giả định IID (naive IID confidence estimates) có thể trở nên quá lạc quan (overconfident) nếu các khung hình có tương quan chuỗi được đối xử như các quan sát độc lập.
- **Platform Confounding Sensitivity:** **CAO**. Tương quan giữa miền và nền tảng robot vẫn tồn tại tự nhiên.
- **Metallurgy Feasibility:** **KHẢ THI CÓ RÀNG BUỘC (FEASIBLE WITH CONSTRAINTS)**. Toàn bộ dataset có 9 mẫu Anomaly của metallurgy (dù vẫn rất hiếm và 8/9 mẫu mang khẳng định văn bản là `oil_chemical`), cho phép tính toán các chỉ số nhạy bất thường với mẫu số $N=9$ thay vì hoàn toàn bằng 0 như P1.
- **Ability to Compare with InspecSafe Official Results:** **GIÁN TIẾP / KHÁC BIỆT MẪU SỐ**. Không thể so sánh số học 1:1 trực tiếp với bảng kết quả của bài báo gốc (vốn chỉ đo trên 1.250 mẫu test).
- **Reproducibility:** **CAO**. Toàn bộ 5.013 mẫu được cố định theo fingerprint đã kiểm chứng ở W1.
- **Compute / API Cost:** **TRUNG BÌNH - CAO**. Quy mô mẫu suy luận lớn gấp ~4,01 lần P1 (5.013 so với 1.250 mẫu). Chi phí token và thời gian thực thi thực tế còn phụ thuộc vào độ dài prompt, độ dài phản hồi sinh ra và bảng giá của từng mô hình.
- **Suitability for Seminar:** **RẤT CAO (Vai trò: Primary Research Protocol Candidate)**. Cung cấp dữ liệu thực chứng đầy đủ nhất để trả lời các câu hỏi nghiên cứu về độ bền vững xuyên miền của SafeShift.
- **Suitability for Thesis:** **TRUNG BÌNH**. Là bước khảo sát nền tảng tốt để phân tích lỗi, nhưng vẫn cần mở rộng thêm các đóng góp can thiệp giải thuật.
- **Main Scientific Weakness:** Chứa các chuỗi video liên tục có thể làm giảm tính độc lập của các mẫu kiểm thử; chi phí API lớn hơn P1.

### 5.3 Protocol 3 (P3): Frozen VLM + Candidate Leakage-Controlled / Group-Aware Evaluation Subset
- **Scientific Question:** *Hiệu năng xuyên miền thực sự của VLM là bao nhiêu khi đo lường trên một tập con kiểm định được kiểm soát rò rỉ và gom cụm có ý thức về nhóm quan sát?*
- **Appropriate Terminology:** `Candidate Leakage-Sensitivity / Group-Aware Evaluation Design`.  
  *Trạng thái hiện tại:* **DESIGN NOT YET DEFINED (Thiết kế chưa được định nghĩa chính thức; chờ W2.2 quyết định chính sách gom nhóm)**.
- **Required Training:** **KHÔNG**. Mô hình hoàn toàn frozen.
- **Use of Official Split:** Đề xuất một tập con đánh giá có kiểm soát nhóm (Group-aware Evaluation Subset). Với mẫu Normal: sử dụng `point_id` hoặc thông tin chuỗi ảnh chụp liền kề làm căn cứ gom nhóm ứng viên. Với mẫu Anomaly: sử dụng heuristic 12 họ nguồn làm tín hiệu tham khảo (lưu ý: heuristic này không phải là video ID chính thức). Tuyệt đối không đưa ra con số ước lượng quy mô mẫu (như 1.500–2.000 mẫu) khi manifest thực tế chưa được tạo lập và kiểm chứng. Không dùng tên gọi "Deduplicated Benchmark" như một sản phẩm đã hoàn thành.
- **Leakage Sensitivity:** **ĐƯỢC CẢI THIỆN TIỀM NĂNG / PHỤ THUỘC TÍNH HỢP LỆ CỦA QUY TẮC GOM NHÓM**. Giảm thiểu ảnh hưởng của các khung hình chụp liên tiếp và loại trừ 7 cặp exact confirmed nếu các giả định grouping được xác thực ở W2.2.
- **Platform Confounding Sensitivity:** **TRUNG BÌNH - CAO**. Vẫn chịu ảnh hưởng bởi tương quan platform tự nhiên giữa các phân xưởng.
- **Metallurgy Feasibility:** **CỰC KỲ YẾU**. Nếu loại bỏ các mẫu mang text claim `oil_chemical`, miền này chỉ còn đúng 1 mẫu Anomaly duy nhất.
- **Ability to Compare with InspecSafe Official Results:** **KHÔNG THỂ SO SÁNH TRỰC TIẾP**.
- **Reproducibility:** **TIỀM NĂNG CAO NẾU CÔNG BỐ MANIFEST MINH BẠCH Ở W2.2**.
- **Compute / API Cost:** **TRUNG BÌNH** (phụ thuộc vào quy mô manifest được chốt).
- **Suitability for Seminar:** **TRUNG BÌNH (Vai trò: Sensitivity / Supplementary Protocol Candidate)**. Chỉ nên triển khai nếu W2.2 thiết kế được quy tắc grouping vững chắc về mặt khoa học mà không làm chậm tiến độ baseline W3.
- **Suitability for Thesis:** **RẤT CAO**. Là hướng đi giàu tiềm năng cho một công bố khoa học độc lập.
- **Main Scientific Weakness:** Thiếu video ID chính thức từ phía tác giả; quy tắc lọc heuristic có thể đưa vào các định kiến chủ quan mới.

### 5.4 Protocol 4 (P4): Source-Domain Training/Tuning + Leave-One-Domain-Out Target
- **Scientific Question:** *Khi được huấn luyện hoặc tinh chỉnh (fine-tuning / adapter tuning) trên các phân xưởng công nghiệp nguồn, mô hình có khả năng khái quát hóa các quy tắc an toàn sang một phân xưởng đích hoàn toàn chưa từng thấy hay không?*
- **Appropriate Terminology:** `Multi-Source Domain Generalization (LODO Protocol)` theo định nghĩa học thuật chuẩn mực (Gulrajani & Lopez-Paz, ICLR 2021; Addepalli et al., CVPR 2024).
- **Required Training:** **BẮT BUỘC HUẤN LUYỆN / TINH CHỈNH (FINE-TUNING REQUIRED)**. Cần huấn luyện bộ thích ứng (LoRA, Adapter, hoặc prompt tuning) trên $K-1$ miền nguồn và kiểm thử trên miền đích còn lại.
- **Use of Official Split:** Thay thế bằng phân chia LODO theo miền (ví dụ: Train trên Coal, Oil, Power, Tunnel $\rightarrow$ Test trên Metallurgy).
- **Leakage Sensitivity:** Rất phức tạp. Nếu áp dụng LODO mà không cách ly 12 source families, Cặp exact số 4 sẽ gây rò rỉ trực tiếp giữa nguồn (metallurgy) và đích (oil_chemical).
- **Platform Confounding Sensitivity:** **HẠN CHẾ NGHIÊM TRỌNG TÍNH GIẢI THÍCH (LIMITS INTERPRETATION)**. Sự gắn kết giữa miền và nền tảng robot khiến chúng ta không thể khẳng định mô hình thất bại do domain shift hay do platform/viewpoint shift. Tuy nhiên, rào cản này không đồng nghĩa với việc DG là bất khả thi về mặt nguyên lý (does not make DG impossible in principle).
- **Metallurgy Feasibility:**  
  - Nếu dùng official test của metallurgy làm target: **`NOT_CURRENTLY_FEASIBLE`** (vì có 0 mẫu Anomaly).  
  - Nếu dùng toàn bộ metallurgy làm target: **`SEVERELY UNDER-SUPPORTED`** (chỉ có 9 mẫu Anomaly, trong đó 8/9 mẫu mang khẳng định văn bản là `oil_chemical`).
- **Ability to Compare with InspecSafe Official Results:** **HOÀN TOÀN KHÔNG THỂ SO SÁNH**.
- **Reproducibility:** **PHỨC TẠP**. Phụ thuộc vào seed, GPU runtime, và siêu tham số huấn luyện.
- **Compute / Resource Burden:** Đòi hỏi tài nguyên tính toán huấn luyện mô hình. Do SafeShift chưa kiểm kê cấu hình phần cứng GPU và kích thước mô hình cụ thể, không đưa ra tuyên bố võ đoán rằng giao thức này bắt buộc phải có hệ thống multi-GPU đắt đỏ; tuy nhiên, gánh nặng thực nghiệm chắc chắn vượt trội so với suy luận zero-shot.
- **Suitability for Seminar:** **`PARTIALLY_FEASIBLE, BUT NOT RECOMMENDED AS PRIMARY SEMINAR PROTOCOL`**.  
  *Lý do không chọn cho Seminar:* (1) Nằm ngoài phạm vi trọng tâm kiểm chuẩn thực nghiệm mô hình sẵn có của Seminar; (2) Đòi hỏi khâu huấn luyện/tinh chỉnh phức tạp; (3) Chính sách phân nhóm source/target chưa được giải quyết; (4) Nhiễu nền tảng robot làm mờ nhạt kết luận; (5) Dữ liệu miền luyện kim quá yếu; (6) Gánh nặng thực nghiệm lớn dễ gây trễ tiến độ 8 tuần.
- **Suitability for Thesis:** **RẤT PHÙ HỢP CHO LUẬN VĂN SAU NÀY (`HIGH FOR THESIS`)**.
- **Main Scientific Weakness:** Nhiễu nền tảng robot làm suy giảm giá trị kết luận của bài toán thích ứng miền; miền luyện kim làm mất tính cân đối của LODO 5 miền.

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
   Được định nghĩa khi các mẫu trong tập kiểm thử không thỏa mãn giả định cơ bản về tính độc lập và phân bố đồng nhất (I.I.D.). Khi nhiều mẫu kiểm thử thực chất là các khung hình cắt ra từ cùng một chuỗi video hoặc cùng một góc chụp robot cố định, chúng chia sẻ chung các đặc trưng tĩnh.  
   *Tác động của Frozen Zero-Shot:* **HOÀN TOÀN KHÔNG GIẢI QUYẾT ĐƯỢC**. Ước lượng phương sai và khoảng tin cậy ngây thơ theo giả định IID có nguy cơ trở nên quá lạc quan (overconfident).
3. **Pretraining Contamination (Ô nhiễm dữ liệu tiền huấn luyện):**  
   Bộ dữ liệu InspecSafe-V1 đã được công bố công khai trên Hugging Face (tháng 04/2026), Zenodo và GitHub. Các mô hình VLM lớn thu thập dữ liệu web liên tục có thể đã thu nạp một phần hoặc toàn bộ tệp ảnh và nhãn của benchmark vào giai đoạn tiền huấn luyện.  
   *Tác động của Frozen Zero-Shot:* **HOÀN TOÀN BẤT LỰC**. Nếu một mô hình VLM đã bị nhiễm dữ liệu tiền huấn luyện, việc đánh giá zero-shot trên tập test thực chất phản ánh năng lực ghi nhớ (memorization) hơn là năng lực suy luận tổng quát hóa.

> **Kết luận bắt buộc:** Đánh giá Zero-shot trên mô hình Frozen chỉ thu hẹp một kênh rò rỉ duy nhất (SafeShift train-to-test leakage pathway). Nó **tuyệt đối không chứng minh** rằng các mẫu kiểm thử độc lập với nhau và **không chứng minh** rằng mô hình chưa từng nhìn thấy dữ liệu trước đó.

---

## 7. Official Split vs. Full Dataset (Phân tích phương án tập kiểm thử cho mô hình Frozen)

Khi mô hình VLM hoàn toàn được đóng băng trọng số (Frozen Pretrained) và không có bất kỳ bước huấn luyện nào trên InspecSafe-V1, khái niệm phân chia "train" (3.763 mẫu) và "test" (1.250 mẫu) của tác giả gốc đứng trước một câu hỏi phương pháp luận lớn:

> *"Nếu chúng ta không huấn luyện mô hình trên InspecSafe-V1, việc tự giới hạn chỉ đánh giá trên 1.250 mẫu test chính thức có còn hợp lý không, hay nên đánh giá trên toàn bộ 5.013 mẫu, hoặc phải báo cáo cả hai?"*

Bảng đối chiếu ưu - nhược điểm của ba phương án:

| Tiêu chí phân tích | Phương án A: Chỉ đánh giá Official Test (1.250 mẫu) | Phương án B: Đánh giá Full Dataset (5.013 mẫu) | Phương án C: Báo cáo Song song Cả hai (Dual Reporting) |
|---|---|---|---|
| **Cơ sở khoa học** | Tuân thủ ranh giới đánh giá do tác giả thiết kế ban đầu; tôn trọng benchmark protocol chuẩn. | Tận dụng tối đa không gian dữ liệu quan sát được; bảo lưu metadata split gốc để phân tích độ nhạy. | Phân tách rạch ròi giữa mục tiêu tái lập baseline (Official Test) và mục tiêu nghiên cứu độ bền vững (Full Dataset). |
| **Tính khả thi của Metallurgy** | **RẤT TỆ**: Miền luyện kim có 0 mẫu Anomaly; không tính được độ nhạy phát hiện lỗi. | **TỐT HƠN**: Có 9 mẫu Anomaly để đo lường (dù mẫu số vẫn nhỏ và cần thận trọng). | Cho phép giải thích rõ ràng lý do tại sao kết quả metallurgy trên Official Test bị khiếm khuyết. |
| **Khả năng so sánh với bài báo gốc** | **TRỰC TIẾP CAO NHẤT**: Có thể so sánh trực tiếp với các bảng điểm của tác giả trên *Scientific Data*. | **KHÔNG TRỰC TIẾP**: Khác biệt về quy mô mẫu kiểm thử. | **TỐI ƯU**: Vừa đối soát được với bài báo gốc, vừa cung cấp góc nhìn kiểm chuẩn mở rộng. |
| **Chi phí tính toán & API Token** | **THẤP**: 1.250 mẫu suy luận. Nằm trong ngưỡng an toàn của ngân sách Seminar. | **CAO HƠN (~4,01x số mẫu)**: 5.013 mẫu suy luận. Chi phí token phụ thuộc prompt/output length. | Có thể kiểm soát chi phí bằng cách: chạy Official Test trên toàn bộ baseline, chạy Full Dataset trên các mô hình trọng tâm. |
| **Rủi ro phụ thuộc mẫu** | Bị chi phối bởi 25% chỉ số đầu của 12 source families. | Chứa các chuỗi video dài từ tập train; ước lượng IID có nguy cơ overconfident. | Cho phép so sánh xem sự biến thiên giữa hai tập có tạo ra sai lệch kết luận hay không. |

> **Khuyến nghị phương pháp luận:**  
> Không tự ý loại bỏ Official Test (vì đây là chuẩn đối chiếu duy nhất để tái lập kết quả baseline của bài báo gốc).  
> Đồng thời, không nên tự giới hạn nghiên cứu chỉ trong Official Test (vì nó che giấu sự thiếu hụt Anomaly của metallurgy và bỏ phí 75% dữ liệu quan sát).  
> **Giải pháp tối ưu là Dual Reporting:** Sử dụng Official Test (P1) làm Baseline Replication Protocol, và sử dụng Full Dataset (P2) làm Primary Research Protocol Candidate để trả lời các câu hỏi nghiên cứu của SafeShift.

---

## 8. Metallurgy Deep-Dive (Phân tích chuyên sâu miền Luyện kim)

Miền luyện kim (`metallurgy`) là trường hợp dị biệt nghiêm trọng nhất về mặt cấu trúc dữ liệu trong InspecSafe-V1:

```text
Hiện trạng dữ liệu Miền Luyện kim:
- Tổng số mẫu: 720 mẫu (543 train / 177 test)
- Mẫu Bình thường (Level04 / Normal): 711 mẫu (534 train / 177 test)
- Mẫu Bất thường (Level01-03 / Anomaly): 9 mẫu ở Train và 0 MẪU Ở TEST CHÍNH THỨC
- Xung đột nhãn ngữ nghĩa: 8 trong số 9 mẫu Anomaly ở train mang khẳng định văn bản là oil_chemical (carry an oil_chemical textual domain claim).
- Chỉ duy nhất 1 mẫu (metallurgy-Level03-SuspendedRail-002666-001) có folder và text cùng xác nhận metallurgy.
```

### 8.1 Có nên giữ metallurgy trong đánh giá độ bền vững theo miền (per-domain robustness) không?
- **Trả lời:** **CÓ, BẮT BUỘC PHẢI GIỮ NHƯNG KÈM THEO GHI CHÚ ĐIỀU KIỆN**.  
- Không được tự tiện xóa bỏ miền luyện kim khỏi danh sách 5 miền, vì đây là một trong 5 kịch bản công nghiệp cốt lõi được tác giả công bố chính thức. Tuy nhiên, mọi bảng kết quả per-domain đều phải có chú thích đặc biệt về sự mất cân bằng cực đoan này.

### 8.2 Có thể đánh giá năng lực phân loại an toàn tổng thể (overall safety classification) không?
- **Trả lời:** **CÓ THỂ ĐÁNH GIÁ ĐƯỢC**.  
- Với 711 mẫu Normal (Level04), chúng ta hoàn toàn có thể đo lường độ chính xác phân loại an toàn tổng thể, đặc biệt là tỷ lệ nhận diện đúng trạng thái an toàn (True Negative Rate / Specificity) và tỷ lệ báo động giả (False Alarm Rate / False Positive Rate).

### 8.3 Có thể đánh giá năng lực nhạy phát hiện bất thường (anomaly-sensitive performance) không?
- **Trả lời:**  
  - Trên **Official Test (P1): HOÀN TOÀN KHÔNG THỂ ĐÁNH GIÁ ĐƯỢC** (mẫu số tính Recall của Anomaly bằng 0).  
  - Trên **Full Dataset (P2): ĐÁNH GIÁ ĐƯỢC NHƯNG CỰC KỲ YẾU VỀ MẪU SỐ THỐNG KÊ** (chỉ có 9 mẫu bất thường; một mẫu phân loại sai làm thay đổi tỷ lệ tới 11,1%). Hơn nữa, do 8/9 mẫu này mang khẳng định văn bản là `oil_chemical`, việc đánh giá trên 9 mẫu này phải được ghi chú rõ ràng về sự mơ hồ danh tính miền.

### 8.4 Có nên dùng metallurgy làm Unseen Target Domain trong LODO (P4) không?
- **Trả lời:** **TUYỆT ĐỐI KHÔNG KHUYẾN NGHỊ (`NOT_RECOMMENDED AS PRIMARY TARGET`)**.  
- Metallurgy là một **severely under-supported target domain** cho bài toán phát hiện bất thường.

### 8.5 Nếu không dùng metallurgy làm Primary Target thì có mất tính "5-Domain" không?
- **Trả lời:** **KHÔNG HỀ MẤT TÍNH CHẤT 5 MIỀN**.  
- SafeShift vẫn duy trì đầy đủ tính chất 5 miền trong bài toán **Cross-Domain Robustness (P1 & P2)** nơi cả 5 miền đều được đo lường song song.

---

## 9. Domain-Label Dependency (Sự phụ thuộc vào định nghĩa nhãn miền)

Trong Tuần 1, kiểm toán đã ghi nhận sự tồn tại của hai trường siêu dữ liệu định danh miền:
1. `folder_domain`: Xác định thuần túy dựa trên tên thư mục lưu trữ của hệ thống tệp cục bộ (`coal_conveyor`, `metallurgy`, `oil_chemical`, `power`, `tunnel`).
2. `text_domain`: Xác định dựa trên câu mở đầu khẳng định bối cảnh trong tệp văn bản `.txt` của annotator.

Kiểm toán xác nhận chính xác **36 mẫu có sự xung đột trực tiếp** giữa hai trường này (`folder_domain != text_domain`).

### Mối quan hệ ràng buộc giữa Quyết định Protocol (D1) và Quyết định Nhãn miền (D3):
- **Ở bước W2.1 này, chúng ta CHƯA tự ý quyết định D3 (chưa chốt cách xử lý 36 mẫu; quyết định D3 được chuyển giao cho bước W2.2).**
- Tuy nhiên, sự lựa chọn giao thức (D1) sẽ quy định trực tiếp mức độ nhạy cảm đối với D3:
  - **Trên P1 (Official Test Only):** Có 18 mẫu bị xung đột (12 mẫu folder `tunnel` nhưng text ghi `oil_chemical`; 6 mẫu khác).
  - **Trên P2 (Full Dataset):** Toàn bộ 36 mẫu xung đột sẽ tham gia vào đánh giá, đặc biệt là 8 mẫu Anomaly của `metallurgy` mang text claim `oil_chemical`.
  - **Trên P3 (Group-aware Subset):** 36 mẫu này có thể được xử lý riêng biệt trong thiết kế nhóm.
- **Hệ quả phương pháp luận:** Bất kể protocol nào được lựa chọn, báo cáo thực nghiệm bắt buộc phải công bố rõ phân nhóm theo `folder_domain` hay `text_domain`, và tiến hành phân tích độ nhạy (sensitivity analysis) đối với 36 mẫu này.

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
│ • Đánh giá Zero-shot Cross-Domain Robustness trên 5 miền (P2)           │
│ • Đánh giá tính nhất quán Phân loại - Bám bằng chứng (Object Support)  │
│ • Phân tích lỗi và yếu tố đồng biến thiên (Platform Co-variation)      │
│ • TUYỆT ĐỐI KHÔNG: Tạo new adaptation algorithm, train model từ đầu,   │
│   hoặc tuyên bố phương pháp mới vượt trội trước khi đo lường           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Kế thừa kết quả & bài học
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ GIAI ĐOẠN 2: THESIS EXTENSION (Luận văn sau này — Nghiên cứu chuyên sâu)│
│ • Xây dựng bộ chú thích Rationale Bounding Box bổ sung (100-200 mẫu)   │
│ • Nghiên cứu định lượng hiện tượng "Correct Answer, Wrong Reason"      │
│ • Thiết kế giải thuật Group-aware Domain Generalization mới (P4)       │
│ • Phát triển kỹ thuật Mitigation / De-biasing cho Platform Confounding │
│ • Tinh chỉnh Adapter / LoRA theo giao thức Leave-One-Domain-Out        │
│ • Soạn thảo bài báo khoa học hoàn chỉnh gửi hội nghị/tạp chí quốc tế   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Candidate Research Questions (Đề xuất các câu hỏi nghiên cứu ứng viên)

Dưới đây là 3 câu hỏi nghiên cứu ứng viên (RQs) được thiết kế lại nhằm loại bỏ các tuyên bố nhân quả (causal claims) chưa được chứng minh, phù hợp với bằng chứng thực nghiệm của InspecSafe-V1:

### 11.1 Research Question 1 (RQ1)
- **Precise English Wording:**  
  *RQ1: How does the zero-shot safety-assessment performance of frozen Vision-Language Models vary across different industrial inspection domains, and how does this observed variation co-vary with robot inspection platforms?*
- **Diễn giải tiếng Việt:**  
  *RQ1: Năng lực đánh giá an toàn công nghiệp ở chế độ zero-shot của các mô hình VLM đóng băng trọng số biến thiên như thế nào xuyên qua các miền công nghiệp khác nhau, và sự biến thiên quan sát được này đồng biến thiên như thế nào với các nền tảng robot tuần tra?*
- **Bản chất biến số:**
  - **Yếu tố phân nhóm quan sát (Observed Grouping Factors):** Miền công nghiệp (`folder_domain` / `text_domain`); Nền tảng robot tuần tra (`SuspendedRail` vs `Wheeled`). *Lưu ý: Domain và Platform là các yếu tố quan sát bị gắn kết (confounded), không phải các biến độc lập nhân quả tách rời.*
  - **Biến đo lường (Measured Outcomes):** Hiệu năng phân loại an toàn nhị phân (Normal vs Anomaly); Hiệu năng phân loại 4 cấp độ an toàn (Level01–Level04).
- **Dữ liệu trả lời:** Toàn bộ 5 miền của InspecSafe-V1 (P1 Official Test 1.250 mẫu và P2 Full Dataset 5.013 mẫu).
- **Khái niệm so sánh:** Đo lường sự biến thiên (variation) hoặc khoảng cách hiệu năng (performance gap) giữa các miền so với hiệu năng gộp chung (pooled performance) hoặc miền tham chiếu được chọn.
- **Họ chỉ số phù hợp (Candidate Metric Families):** Macro-F1, Balanced Accuracy, Per-class Recall, True Negative Rate (Specificity). Bỏ chỉ số "Expected Cost of Misclassification" do chưa có ma trận chi phí hợp lệ.
- **Tính khả thi từ W1:** **`FEASIBLE_WITH_CONSTRAINTS`**. (Không dùng cách diễn đạt tự mâu thuẫn "HOÀN TOÀN HỖ TRỢ (FEASIBLE_WITH_CONSTRAINTS)").

### 11.2 Research Question 2 (RQ2)
- **Precise English Wording:**  
  *RQ2: Which safety levels and verified hazard strata show the largest error concentration in frozen VLM predictions, and to what extent is this error pattern associated with hazard visibility or sample scarcity?*
- **Diễn giải tiếng Việt:**  
  *RQ2: Những cấp độ an toàn và phân tầng nguy cơ đã được xác minh nào bộc lộ mức độ tập trung lỗi cao nhất trong các dự đoán của VLM đóng băng, và mức độ tập trung lỗi này liên hệ như thế nào với tính hiển hiện của nguy cơ hoặc tính chất hiếm của mẫu dữ liệu?*
- **Bản chất biến số:**
  - **Yếu tố phân tầng:** Cấp độ rủi ro quy chuẩn (Level01–Level04); Phân tầng nguy cơ đã xác minh (Verified Hazard Strata — **lưu ý: danh mục phân tầng nguy cơ chưa được chốt chính thức và chỉ được xác định sau khi hoàn thành cuộc tổng điều tra census D6 ở W2.3**).
  - **Biến đo lường:** Tỷ lệ bỏ sót vi phạm (False Negative Rate); Tỷ lệ nhầm lẫn giữa các cấp độ an toàn (Confusion Matrix).
- **Nguyên tắc phương pháp luận:** Tuyệt đối không giả định rằng mẫu hiếm trong benchmark đồng nghĩa với hiếm trong dữ liệu tiền huấn luyện của VLM; không đưa ra kết luận nhân quả từ tần suất lớp trong benchmark.
- **Dữ liệu trả lời:** Tập 1.000 mẫu `Anomaly_data` và phân bố 4 cấp độ an toàn Level01–Level04.
- **Họ chỉ số phù hợp:** Per-stratum Recall, Confusion Matrix, Error Distribution Analysis, độ bất định thống kê do mẫu số nhỏ.
- **Tính khả thi từ W1:** **`FEASIBLE_WITH_CONSTRAINTS, PENDING D6 HAZARD-STRATA CENSUS`**.

### 11.3 Research Question 3 (RQ3)
- **Precise English Wording:**  
  *RQ3: On evaluable image subsets, to what extent is correct safety classification consistent with spatial evidence localization, and how frequently do models produce correct hazard predictions while missing the annotated object-support regions?*
- **Diễn giải tiếng Việt:**  
  *RQ3: Trên các tập con ảnh có thể đánh giá được, mức độ nhất quán giữa phân loại an toàn đúng và định vị bằng chứng không gian là bao nhiêu, và tần suất mô hình đưa ra dự đoán an toàn đúng nhưng lại định vị trượt vùng chú thích đối tượng hỗ trợ là bao nhiêu?*
- **Bản chất biến số:**
  - **Tập dữ liệu đánh giá:** Tập con có hỗ trợ đối tượng trực tiếp (Direct Object-Support Subset) và tập con đại diện yếu (Weak-Proxy Subset qua `Person`), được báo cáo hoàn toàn tách biệt.
  - **Biến đo lường:** Điểm số bám vùng đối tượng hỗ trợ (Bounding Box IoU / Pointing Game Hit Rate); Tỷ lệ phân ly quan sát được (`correct safety prediction + grounding miss relative to the available object-support annotation`).
- **Nguyên tắc phương pháp luận:** Tuyệt đối không tự ý diễn giải hiện tượng này là "Correct Answer, Wrong Reason" (vì dataset không có Rationale Ground Truth); attention map không tự động được xem là lời giải thích nhân quả hoàn chỉnh, chỉ sử dụng định vị dựa trên attention cho các kiến trúc mô hình hỗ trợ trích xuất.
- **Tính khả thi từ W1:** **`FEASIBLE_WITH_CONSTRAINTS`**.

---

## 12. Candidate Hypotheses (Đề xuất các giả thuyết khoa học kiểm định được)

Các giả thuyết được thiết kế lại dưới dạng giả thuyết thống kê kiểm định được (Null Hypothesis $H_0$ và Alternative Hypothesis $H_1$), loại bỏ các nhận định nhân quả võ đoán:

### 12.1 Giả thuyết 1 (Cho RQ1 — Biến thiên hiệu năng xuyên miền)
- **Null Hypothesis ($H_{1,0}$):**  
  *Phân bố hiệu năng phân loại an toàn của mô hình VLM đóng băng là tương đương nhau giữa các phân tầng miền công nghiệp được xác định trước.*
- **Alternative Hypothesis ($H_{1,1}$):**  
  *Tồn tại ít nhất một miền công nghiệp bộc lộ sự khác biệt hiệu năng có ý nghĩa thống kê so với các miền còn lại.*  
  *(Mối liên hệ giữa hiệu năng và nền tảng robot SuspendedRail vs Wheeled sẽ được phân tích mô tả và kiểm tra độ nhạy, không quy kết nguyên nhân nhân quả).*

### 12.2 Giả thuyết 2 (Cho RQ2 — Tập trung lỗi theo phân tầng rủi ro)
- **Null Hypothesis ($H_{2,0}$):**  
  *Tỷ lệ sai số phân loại an toàn của mô hình VLM phân bố đồng đều xuyên qua các cấp độ an toàn và các phân tầng nguy cơ.*
- **Alternative Hypothesis ($H_{2,1}$):**  
  *Tỷ lệ sai số phân bố không đồng nhất xuyên qua các cấp độ an toàn và phân tầng nguy cơ đã được xác minh.*  
  *(Lưu ý: Giả thuyết có hướng về việc các nguy cơ thiếu hụt trang bị absence-based bộc lộ tỷ lệ bỏ sót cao hơn chỉ là **giả thuyết đề xuất (PROPOSED hypothesis)** có điều kiện phụ thuộc vào kết quả census và taxonomy tại W2.3).*

### 12.3 Giả thuyết 3 (Cho RQ3 — Tính nhất quán giữa Phân loại và Bám vùng)
- **Null Hypothesis ($H_{3,0}$):**  
  *Có điều kiện trên tập con Direct-Support có thể đánh giá được, tính chính xác của dự đoán an toàn và sự thành công trong định vị vùng đối tượng không có mối liên hệ đo lường được.*
- **Alternative Hypothesis ($H_{3,1}$):**  
  *Tính chính xác của dự đoán an toàn và sự thành công trong định vị vùng đối tượng bộc lộ mối liên hệ đo lường được, đồng thời xuất hiện một tỷ lệ quan sát được các trường hợp dự đoán đúng cấp an toàn nhưng định vị trượt vùng đối tượng hỗ trợ.*

> **Lưu ý bắt buộc:** Toàn bộ các kiểm định thống kê chính thức (formal statistical test selection) **CHƯA ĐƯỢC PHÊ DUYỆT Ở W2.1** và sẽ được quyết định tại bước W2.2/W2.4.

---

## 13. Candidate Statistical Approaches (Định hướng phương pháp phân tích thống kê)

Tuân thủ tính thận trọng học thuật, **ở bước W2.1 này SafeShift KHÔNG chốt cứng các công thức kiểm định thống kê** (như ANOVA trên 5 giá trị Macro-F1 hay Spearman trên các mẫu số cực nhỏ). Việc lựa chọn kiểm định chính thức phụ thuộc vào: đơn vị phân tích (unit of analysis), chính sách gom nhóm mẫu, mức độ tương quan chuỗi và định nghĩa metric cuối cùng.

Các phương pháp phân tích thống kê ứng viên được đưa vào danh mục xem xét cho W2.2/W2.4:
1. **Cluster-aware Bootstrap:** Lấy mẫu lại có hoàn lại theo cụm điểm tuần tra (`point_id`) hoặc họ nguồn để ước lượng khoảng tin cậy 95% (95% CI) cho các chỉ số tổng hợp mà không bị thiên lệch bởi tương quan chuỗi.
2. **Stratified Bootstrap:** Lấy mẫu phân tầng theo miền và cấp an toàn để kiểm soát độ lệch mẫu số giữa các lớp.
3. **Permutation Tests (Kiểm định hoán vị):** Đánh giá ý nghĩa thống kê của khoảng cách hiệu năng giữa các miền mà không đòi hỏi giả định về phân bố chuẩn của dữ liệu.

---

## 14. Decision Matrix (Ma trận đánh giá 4 phương án giao thức)

Bảng đối chiếu tổng hợp 4 phương án giao thức trên 8 tiêu chí phương pháp luận (đóng vai trò là công cụ hỗ trợ định tính, không dùng phép cộng điểm máy móc để thay thế quyết định khoa học):

| Tiêu chí Đánh giá | P1: Frozen Official Test | P2: Frozen Full Dataset | P3: Candidate Group-aware Subset | P4: LODO Training (DG) |
|---|:---:|:---:|:---:|:---:|
| **1. Scientific Validity** *(Tính giá trị khoa học)* | **MEDIUM** (Hạn chế do Test Metallurgy Anomaly = 0) | **HIGH** (Bao quát trọn vẹn 5 miền thực tế) | **QUALIFIED HIGH** (Phụ thuộc vào thiết kế grouping ở W2.2) | **QUALIFIED / CONSTRAINED** (Đúng lý thuyết nhưng bị nhiễu nền tảng làm lu mờ) |
| **2. Fit to W1 Evidence** *(Khớp với bằng chứng W1)* | **MEDIUM** (Bỏ phí 75% dữ liệu audit W1) | **HIGH** (Tận dụng toàn bộ census W1) | **HIGH** (Giải quyết trực tiếp các cảnh báo W1) | **LOW FIT FOR SEMINAR** (Metallurgy quá yếu, platform bị confound) |
| **3. Seminar Feasibility** *(Tính khả thi cho Seminar)* | **VERY HIGH** (Đơn giản, chuẩn mực, an toàn) | **HIGH** (Khả thi cao, quản lý được chi phí) | **MEDIUM** (Cần thêm nỗ lực tạo manifest ở W2) | **PARTIALLY_FEASIBLE / NOT RECOMMENDED** (Gánh nặng thực nghiệm lớn) |
| **4. Leakage Robustness** *(Khả năng chống rò rỉ)* | **HIGH ONLY AGAINST SAFESHIFT TRAIN→TEST LEAKAGE** (Evaluation dependence và pretraining contamination vẫn là rủi ro mở) | **MEDIUM** (Cần xử lý tương quan chuỗi) | **POTENTIALLY IMPROVED / CONDITIONAL ON GROUPING VALIDITY** (Phụ thuộc vào quy tắc gom nhóm ở W2.2) | **LOW** (Nguy cơ rò rỉ exact và chuỗi xuyên miền) |
| **5. Comparability** *(Khả năng so sánh với bài báo gốc)* | **DIRECTEST / HIGHEST** (Đối soát 1:1 với điều kiện cấu hình) | **INDIRECT** (Khác biệt về quy mô mẫu kiểm thử) | **LOW** (Benchmark độc lập mới) | **NONE** (Tác giả không có thí nghiệm này) |
| **6. Interpretability** *(Tính diễn giải khoa học)* | **MEDIUM** (Bị che khuất ở miền luyện kim) | **HIGH** (Rõ ràng trên từng phân xưởng) | **QUALIFIED / POTENTIALLY HIGH** (Có tiềm năng giảm phụ thuộc chuỗi nếu grouping được xác thực; true video IDs không có sẵn) | **LOW** (Bị nhiễu kép domain + platform) |
| **7. Compute / Token Burden** *(Gánh nặng tính toán/chi phí)* | **LOW** (1.250 mẫu suy luận) | **MODERATE** (~4,01x mẫu so với P1) | **MODERATE** (Phụ thuộc quy mô manifest) | **HIGH** (Đòi hỏi huấn luyện lặp lại mô hình) |
| **8. Thesis Extensibility** *(Khả năng mở rộng cho Luận văn)* | **LOW** (Chỉ là bước chạy lại) | **MEDIUM** (Tài liệu tham chiếu thực nghiệm) | **HIGH** (Nền tảng cho công bố độc lập) | **HIGH** (Hướng nghiên cứu trọng tâm sau này) |

---

## 15. Preliminary Recommendation (Đề xuất phân tầng giao thức nghiên cứu)

Căn cứ trên các phân tích khoa học độc lập và đối chiếu với mục tiêu của đề tài SafeShift:

> [!IMPORTANT]
> **TRẠNG THÁI KHUYẾN NGHỊ: `PROPOSED, NOT APPROVED`**  
> Đây là đề xuất phương pháp luận của Trợ lý nghiên cứu để chuẩn bị cho cuộc họp quyết định. Toàn bộ các đề xuất dưới đây **chưa có hiệu lực thi hành** cho đến khi được Research Lead phê duyệt chính thức vào `DECISIONS.md`.

### 15.1 Khung Phân tầng Giao thức Đề xuất (Recommended Protocol Hierarchy)
- **BASELINE REPLICATION PROTOCOL:**  
  $\rightarrow$ **Protocol 1 (Frozen VLM + Official Test Only, 1.250 mẫu)**.  
  *Vai trò:* Bắt buộc phải thực hiện tại Tuần 3 nhằm tái lập kết quả cơ sở (baseline replication) và đối chiếu trung thực với bài báo trên *Scientific Data*.
- **PRIMARY RESEARCH PROTOCOL CANDIDATE:**  
  $\rightarrow$ **Protocol 2 (Frozen VLM + Full Dataset Per-Domain Evaluation, 5.013 mẫu)**.  
  *Vai trò:* Đóng vai trò là giao thức nghiên cứu chính để trả lời các câu hỏi nghiên cứu (RQ1, RQ2, RQ3) của SafeShift Seminar, đánh giá toàn diện độ bền vững trên 5 miền và khắc phục khiếm khuyết của miền Luyện kim.
- **SENSITIVITY / LEAKAGE-CONTROLLED CANDIDATE:**  
  $\rightarrow$ **Protocol 3 (Group-Aware Evaluation Subset)**.  
  *Vai trò:* Chỉ xem xét triển khai như một phân tích độ nhạy bổ trợ nếu bước W2.2 thiết kế được quy tắc gom nhóm khoa học, khả thi mà không làm chậm tiến độ baseline.
- **THESIS / LATER DG CANDIDATE:**  
  $\rightarrow$ **Protocol 4 (Source-Domain Training + LODO Target)**.  
  *Vai trò:* Bảo lưu cho Luận văn tốt nghiệp sau khi giai đoạn Seminar kết thúc; không chọn làm giao thức chính cho Seminar 8 tuần.

---

## 16. Risks (Nhận diện rủi ro nghiên cứu và thực thi)

1. **Rủi ro Trôi dạt Mô hình và Chi phí API (API Model Drift & Token Budget):**  
   Các bản cập nhật API của nhà cung cấp có thể làm thay đổi nhẹ kết quả số học; việc chạy 5.013 mẫu cần được phân bổ ngân sách token hợp lý.
2. **Rủi ro Phân tích Cú pháp Đầu ra Grounding (Output Parsing Fragility):**  
   Mô hình VLM có thể không tuân thủ cấu trúc JSON tọa độ bounding box; cần thiết kế prompt có cấu trúc chặt chẽ kèm bộ phân tích cú pháp có khả năng phục hồi lỗi ở W2.4.
3. **Rủi ro Nhạy cảm đối với 36 Mẫu Mismatch:**  
   Sự khác biệt giữa `folder_domain` và `text_domain` có thể ảnh hưởng đến kết quả của các miền nhỏ; cần tiến hành kiểm tra độ nhạy khi có và không có 36 mẫu này.
4. **Rủi ro Diễn giải Vượt mức về Grounding (Overclaiming Grounding Meaning):**  
   Cần phân định rạch ròi giữa việc bám đúng đa giác đối tượng hỗ trợ (`Object-Support Grounding`) với việc bám lý do an toàn đầy đủ (`Full Rationale Grounding`).

---

## 17. Questions Requiring Approval (Phân nhóm câu hỏi phê duyệt)

Nhằm đảm bảo tiến độ và đúng phạm vi của từng bước, các câu hỏi được phân tách thành hai nhóm:

### Nhóm 1: Câu hỏi Trọng tâm Sẵn sàng Phê duyệt cho D1 (READY FOR D1 APPROVAL)
- [ ] **Q1.1 (Khung Định nghĩa Đề tài):** Chấp thuận định hình phương pháp luận chính của SafeShift Seminar là **`Cross-Domain Robustness Evaluation`** (thay vì Domain Generalization có huấn luyện) để phản ánh trung thực việc sử dụng mô hình VLM đóng băng trọng số?
- [ ] **Q1.2 (Vai trò Protocol 1):** Phê duyệt **Protocol 1 (Official Test Only)** làm **Baseline Replication Protocol** bắt buộc cho Tuần 3?
- [ ] **Q1.3 (Vai trò Protocol 2):** Phê duyệt **Protocol 2 (Full Dataset Per-Domain)** làm **Primary Research Protocol Candidate** cho mục tiêu nghiên cứu độ bền vững của Seminar?
- [ ] **Q1.4 (Phê duyệt Khung RQs & Giả thuyết):** Phê duyệt bộ 3 câu hỏi nghiên cứu ứng viên (RQ1, RQ2, RQ3) và 3 giả thuyết tương ứng tại Mục 11 & 12 làm khung định hướng cho đề tài?

### Nhóm 2: Các Vấn đề Chuyển giao sang Bước Kế tiếp (DEFERRED ITEMS)
- **Chuyển sang Bước W2.2 (Data Splits & Domain Definition):**
  - Quyết định D2: Chính sách gom nhóm rò rỉ và thiết kế chi tiết cho Protocol 3.
  - Quyết định D3: Chính sách xử lý chính thức đối với 36 mẫu xung đột miền giữa thư mục và văn bản.
  - Chính sách xử lý chi tiết đối với dữ liệu bất thường của miền Luyện kim.
- **Chuyển sang Bước W2.3 / W2.4 (Census, Interface & Metrics):**
  - Quyết định D4: Chuẩn hóa giao diện đầu ra bám bằng chứng của mô hình (text bounding box hay attention map).
  - Quyết định D5 & D6: Kế hoạch tổng điều tra census tập Direct Support trên 1.000 mẫu Anomaly và lựa chọn các công thức kiểm định thống kê chính thức.

---

## 18. Sources (Tài liệu tham khảo chính thức)

1. **Liu, Z., Liu, S., Min, J., Zhang, Z., Cen, J., Han, P., Hu, S., Meng, Z., He, X., & Zhou, D.** (2026). *Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios*. Nature Scientific Data, 13, Article 1198. DOI: [10.1038/s41597-026-07796-x](https://doi.org/10.1038/s41597-026-07796-x).
2. **Wang, C., Guan, X., et al.** (2024). *Real-IAD: A Real-World Multi-View Dataset for Benchmarking Versatile Industrial Anomaly Detection*. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR 2024), pp. 22883–22892. [OpenAccess](https://openaccess.thecvf.com/content/CVPR2024/html/Wang_Real-IAD_A_Real-World_Multi-View_Dataset_for_Benchmarking_Versatile_Industrial_Anomaly_CVPR_2024_paper.html).
3. **Gu, Z., Zhu, B., Zhu, G., Chen, Y., Tang, M., & Wang, J.** (2024). *AnomalyGPT: Detecting Industrial Anomalies Using Large Vision-Language Models*. In Proceedings of the AAAI Conference on Artificial Intelligence (AAAI 2024), 38(3), pp. 1932–1940. Article: 27963. DOI: [10.1609/aaai.v38i3.27963](https://doi.org/10.1609/aaai.v38i3.27963).
4. **Song, Y., et al.** (2025). *Both Text and Images Leaked! A Systematic Analysis of Data Contamination in Multimodal LLM*. In Findings of the Association for Computational Linguistics: EMNLP 2025 (Bản lưu trữ preprint: arXiv:2411.03823). [arXiv](https://arxiv.org/abs/2411.03823).
5. **Park, J., Cai, M., Yao, F., et al.** (2026). *Contamination Detection for VLMs using Multi-Modal Semantic Perturbations*. In International Conference on Learning Representations (ICLR 2026). [OpenReview](https://openreview.net/forum?id=gk6OC3XIZW).
6. **Kang, S., Kim, J., Kim, J., & Hwang, S. J.** (2025). *Your Large Vision-Language Model Only Needs A Few Attention Heads For Visual Grounding*. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR 2025), pp. 9339–9350. [OpenAccess](https://openaccess.thecvf.com/content/CVPR2025/html/Kang_Your_Large_Vision-Language_Model_Only_Needs_A_Few_Attention_Heads_CVPR_2025_paper.html).
7. **Yan, S., Bai, M., Chen, W., Zhou, X., Huang, Q., & Li, L. E.** (2024). *ViGoR: Improving Visual Grounding of Large Vision-Language Models with Fine-Grained Reward Modeling*. In Proceedings of the European Conference on Computer Vision (ECCV 2024), Paper ID: 07792. [ECVA](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/07792.pdf).
8. **Xiao, L., Yang, X., Peng, F., Wang, Y., & Xu, C.** (2024). *OneRef: Unified One-tower Expression Grounding and Segmentation with Mask Referring Modeling*. In Advances in Neural Information Processing Systems (NeurIPS 2024). [NeurIPS Abstract](https://proceedings.neurips.cc/paper_files/paper/2024/hash/fcd812a51b8f8d05cfea22e3c9c4b369-Abstract-Conference.html) / [NeurIPS PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/fcd812a51b8f8d05cfea22e3c9c4b369-Paper-Conference.pdf).
9. **Saxena, R., Suglia, A., & Minervini, P.** (2026). *VLM-RobustBench: A Comprehensive Benchmark for Robustness of Vision-Language Models*. arXiv preprint arXiv:2603.06148. [arXiv](https://arxiv.org/abs/2603.06148).
10. **Addepalli, S., Asokan, A. R., Sharma, L., & Babu, R. V.** (2024). *Leveraging Vision-Language Models for Improving Domain Generalization in Image Classification*. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR 2024), pp. 23922–23932. [OpenAccess](https://openaccess.thecvf.com/content/CVPR2024/html/Addepalli_Leveraging_Vision-Language_Models_for_Improving_Domain_Generalization_in_Image_Classification_CVPR_2024_paper.html).
11. **Chen, Z., Wang, W., Zhao, Z., Su, F., Men, A., & Meng, H.** (2024). *PracticalDG: Perturbation Distillation on Vision-Language Models for Hybrid Domain Generalization*. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR 2024), pp. 23501–23511. [OpenAccess](https://openaccess.thecvf.com/content/CVPR2024/html/Chen_PracticalDG_Perturbation_Distillation_on_Vision-Language_Models_for_Hybrid_Domain_Generalization_CVPR_2024_paper.html).
12. **Zanella, M., & Ben Ayed, I.** (2024). *On the Test-Time Zero-Shot Generalization of Vision-Language Models: Do We Really Need Prompt Learning?*. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR 2024), pp. 23783–23793. [OpenAccess](https://openaccess.thecvf.com/content/CVPR2024/html/Zanella_On_the_Test-Time_Zero-Shot_Generalization_of_Vision-Language_Models_Do_We_CVPR_2024_paper.html).
13. **Gulrajani, I., & Lopez-Paz, D.** (2021). *In Search of Lost Domain Generalization*. In Proceedings of the International Conference on Learning Representations (ICLR 2021). [OpenReview](https://openreview.net/forum?id=lQdXeXDoWtI).
14. **Hendrycks, D., et al.** (2021). *The Many Faces of Robustness: A Critical Analysis of Out-of-Distribution Generalization*. In Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV 2021), pp. 8340–8349. [OpenAccess](https://openaccess.thecvf.com/content/ICCV2021/html/Hendrycks_The_Many_Faces_of_Robustness_A_Critical_Analysis_of_ICCV_2021_paper.html).
15. **Zhou, K., Liu, Z., Qiao, Y., Xiang, T., & Loy, C. C.** (2022). *Domain Generalization: A Survey*. IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI), 45(4), pp. 4396–4415. DOI: [10.1109/TPAMI.2022.3195549](https://doi.org/10.1109/TPAMI.2022.3195549).
16. **Ben-David, S., Blitzer, J., Crammer, K., Kulesza, A., Pereira, F., & Vaughan, J. W.** (2010). *A theory of learning from different domains*. Machine Learning, 79(1), pp. 151–175.
17. **Radford, A., et al.** (2021). *Learning Transferable Visual Models From Natural Language Supervision*. In International Conference on Machine Learning (ICML 2021), PMLR, pp. 8748–8763.
18. **Liang, P., et al.** (2023). *Holistic Evaluation of Language Models*. Transactions on Machine Learning Research (TMLR).
