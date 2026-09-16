# Decision log

## DEC-W2-D1-001 — Research Framing and Protocol Hierarchy

- **ID:** DEC-W2-D1-001
- **Ngày:** 2026-09-16
- **Trạng thái:** ĐƯỢC CHẤP THUẬN
- **Vấn đề cần quyết định:**
  - Xác định bản chất bài toán khoa học (Research Framing) chính thức cho đề tài SafeShift Seminar: Định hình bài toán là Cross-Domain Robustness Evaluation trên mô hình VLM đóng băng trọng số hay Domain Generalization theo nghĩa học máy truyền thống có huấn luyện trên miền nguồn.
  - Thiết lập phân tầng vai trò giao thức thực nghiệm (Protocol Hierarchy) rõ ràng giữa 4 phương án ứng viên (P1, P2, P3, P4) để vừa bảo đảm tính so sánh với nghiên cứu gốc, vừa tạo đóng góp khoa học độc lập có ý nghĩa.
  - Phê chuẩn khung câu hỏi nghiên cứu hoạt động (Working Research Question Framework) gồm 3 câu hỏi ứng viên (RQ1, RQ2, RQ3).
- **Bối cảnh và bằng chứng:**
  - Kế thừa toàn bộ các phát hiện thực chứng bất biến đã được kiểm toán độc lập tại Tuần 1 ([notes/w1_dataset_audit.md](notes/w1_dataset_audit.md) và [notes/research_feasibility_audit.md](notes/research_feasibility_audit.md)): Bộ dữ liệu InspecSafe-V1 gồm 5.013 mẫu ảnh RGB (train 3.763, test 1.250; Normal 4.013, Anomaly 1.000); 5 miền công nghiệp; 7 cặp exact cross-split; 833 cặp dHash <= 8 xuyên split (gồm 7 exact và 826 nonexact candidates); 12 họ nguồn Anomaly bộc lộ dấu vết chuỗi; hiện tượng platform confounding gắn kết gần như tuyệt đối giữa miền và dạng robot tuần tra (`SuspendedRail` vs `Wheeled`); miền Luyện kim (`metallurgy`) có 0 mẫu Anomaly ở tập test chính thức; 36 mẫu xung đột giữa tên thư mục và khẳng định văn bản (`folder_domain != text_domain`); 37.434 đa giác đối tượng, hoàn toàn không có bounding box nguy cơ chuyên biệt hay nhãn rationale của con người.
  - Báo cáo phân tích phương pháp luận toàn diện và khảo sát y văn chuẩn mực tại [notes/w2_protocol_decision_brief.md](notes/w2_protocol_decision_brief.md) (đã hoàn thành tại bước W2.1 và được hợp nhất vào nhánh `main` qua PR #10).
- **Các phương án:**
  - *Phương án A — Thuần túy Domain Generalization (LODO Training / P4):* Huấn luyện/tinh chỉnh mô hình trên các miền nguồn và đánh giá trên miền đích chưa thấy.  
    *Trade-off:* Đúng định nghĩa học thuật truyền thống của DG nhưng đòi hỏi tài nguyên huấn luyện/tinh chỉnh lớn, bị nhiễu nền tảng robot nghiêm trọng làm lu mờ khả năng giải thích nguyên nhân dịch chuyển miền, miền Luyện kim không đủ mẫu bất thường làm target, không khả thi cho khuôn khổ Seminar 8 tuần.
  - *Phương án B — Thuần túy Replicate Test Chính thức (P1 Only):* Đánh giá zero-shot trên tập test 1.250 mẫu của InspecSafe-V1.  
    *Trade-off:* Đơn giản, an toàn, đối chiếu trực tiếp 1:1 với bài báo gốc cho phân loại an toàn và tương đồng ngữ nghĩa. Tuy nhiên, bỏ qua 75% dữ liệu quan sát được, hoàn toàn không đánh giá được phát hiện bất thường của miền Luyện kim (0 mẫu test Anomaly), và thiếu đóng góp nghiên cứu mới ngoài việc chạy lại baseline.
  - *Phương án C — Phân tầng giao thức đa cấp (Protocol Hierarchy: P1 + P2 + P3 + P4) kết hợp Research Framing chuẩn mực (Được chọn):*  
    *Trade-off:* Phân định rạch ròi bản chất bài toán khoa học (Cross-Domain Robustness cho Seminar trên frozen VLM; DG cho Thesis sau này); kết hợp song song Baseline Replication Protocol (P1 trên 1.250 mẫu test) và Primary Research Protocol (P2 trên toàn bộ 5.013 mẫu); duy trì P3 như một ứng viên kiểm tra độ nhạy (phụ thuộc vào W2.2); bảo lưu P4 cho nghiên cứu mở rộng (Thesis). Cần quản lý ngân sách tính toán/API lớn hơn (~4x so với P1) và xử lý thận trọng tương quan chuỗi trong phân tích thống kê.
- **Quyết định:**
  - **1. Framing chính của SafeShift Seminar:**  
    SafeShift Seminar được định hình phương pháp luận chính thức là:  
    **Cross-Domain Robustness Evaluation (Đánh giá độ bền vững xuyên miền) trên Frozen Pretrained Vision-Language Models (Mô hình thị giác-ngôn ngữ đã huấn luyện sẵn và giữ nguyên trọng số)**.  
    *Quy tắc chuẩn hóa:* Tuyệt đối **không gọi** giao thức chính của Seminar là **Domain Generalization (Khái quát hóa miền)** theo nghĩa học máy chuẩn có quá trình học tập/huấn luyện/tinh chỉnh trên các miền nguồn (*source domains*).
  - **2. Phân tầng giao thức thực nghiệm (Protocol Hierarchy):**
    - **P1 — BASELINE REPLICATION PROTOCOL (Giao thức tái lập baseline):**
      - Sử dụng tập kiểm thử chính thức (*official test*) gồm đúng **1.250 mẫu**.
      - Toàn bộ mô hình VLM giữ nguyên trọng số (*frozen weights*), suy luận zero-shot.
      - Mục tiêu: Tái lập và đối chiếu trực tiếp với các nhiệm vụ upstream từ bài báo gốc InspecSafe (*Scientific Data* 2026), bao gồm: (1) dự đoán cấp độ an toàn (*Safety-level prediction: Safety Accuracy*) và (2) đánh giá ngữ nghĩa mô tả văn bản (*Textual semantic evaluation: BGE-M3 Semantic Similarity*) khi có thể tái lập đúng protocol gốc.
      - Đánh giá bám bằng chứng (*Grounding*) trên 1.250 mẫu test nếu thực hiện là **SafeShift extension (phần mở rộng độc lập của SafeShift trên evaluation pool này)**, **KHÔNG PHẢI** là official upstream baseline (do bài báo gốc không công bố bất kỳ giao thức hay baseline grounding nào).
    - **P2 — PRIMARY RESEARCH PROTOCOL (Giao thức nghiên cứu chính):**
      - Sử dụng mô hình VLM đóng băng trọng số (*Frozen VLM*).
      - Đánh giá trên toàn bộ **5.013 mẫu** (toàn bộ không gian dữ liệu quan sát được).
      - Báo cáo kết quả phân rã chi tiết theo **5 miền công nghiệp** (*5 industrial domains*).
      - **Bảo lưu nguyên vẹn siêu dữ liệu phân tách gốc (`split: train/test`)** trong mọi manifest và báo cáo để bảo toàn nguồn gốc dữ liệu (*provenance*) và phục vụ phân tích độ nhạy (*sensitivity analysis*). Tuyệt đối không xóa bỏ metadata split.
      - Mục tiêu chính: Trả lời các câu hỏi nghiên cứu trung tâm về độ bền vững xuyên miền (*Cross-Domain Robustness*) của SafeShift Seminar, khắc phục khiếm khuyết thiếu mẫu bất thường của miền Luyện kim ở P1.
    - **P3 — SENSITIVITY PROTOCOL CANDIDATE (Ứng viên giao thức phân tích độ nhạy):**
      - Đánh giá có xét nhóm (*Group-aware evaluation*).
      - **Chưa được coi là clean benchmark (benchmark sạch)**.
      - Chỉ được xem xét triển khai nếu bước W2.2 xác lập được chính sách gom nhóm (*grouping policy*) có cơ sở khoa học chặt chẽ.
      - Ghi nhận thực tế: ID video thật (*true video IDs*) không tồn tại trong bản phát hành công khai của InspecSafe-V1; 12 nhóm nguồn suy luận (*12 source-family pools*) chỉ là quy tắc suy luận heuristic, **không phải là nhãn chuẩn video (*video ground truth*)**.
    - **P4 — THESIS / LATER DG CANDIDATE (Hướng DG cho luận văn sau):**
      - Huấn luyện/tinh chỉnh trên miền nguồn (*Source-domain Training/Tuning*) kết hợp kiểm thử trên miền đích giữ lại (*Leave-One-Domain-Out — LODO*).
      - Đây mới là hướng tiếp cận phù hợp với bài toán **Domain Generalization** theo định nghĩa học máy chuẩn có học tập biểu diễn trên miền nguồn.
      - **Không phải là protocol chính của giai đoạn Seminar 8 tuần**; bảo lưu cho giai đoạn Luận văn tốt nghiệp sau này.
  - **3. Khung câu hỏi nghiên cứu hoạt động (Working Research Question Framework):**  
    Phê duyệt bộ 3 câu hỏi nghiên cứu (RQs) trong `notes/w2_protocol_decision_brief.md` làm khung câu hỏi nghiên cứu hoạt động chính thức:
    - **RQ1 (Biến thiên hiệu năng zero-shot xuyên miền và đồng biến thiên với platform):** Đánh giá sự biến thiên của hiệu năng zero-shot giữa các miền công nghiệp và mô tả sự đồng biến thiên với nền tảng robot tuần tra (`SuspendedRail` vs `Wheeled`). **KHÔNG đưa ra khẳng định nhân quả (*causal claim*)** rằng nền tảng robot gây ra sự thay đổi hiệu năng.
    - **RQ2 (Tập trung lỗi theo cấp an toàn và phân tầng nguy cơ):** Phân tích sự tập trung lỗi (*error concentration*) theo cấp độ an toàn (`Level01`–`Level04`) và các phân tầng nguy cơ đã xác minh (*verified hazard strata*). **Lưu ý:** Các tầng nguy cơ (*hazard strata*) hiện tại **chưa được khóa**; RQ2 vẫn có điều kiện phụ thuộc vào cuộc tổng điều tra dữ liệu nguy cơ (D6 census) ở bước sau (W2.3).
    - **RQ3 (Tính nhất quán giữa phân loại và bám bằng chứng không gian):** Đánh giá tính nhất quán giữa phân loại và định vị bằng chứng (*classification-grounding consistency*) trên các tập con ảnh có thể đánh giá được (*evaluable subsets*: Direct-Support và Weak-Proxy qua `Person`, báo cáo tách biệt). **KHÔNG tự động gán nhãn** hiện tượng dự đoán đúng an toàn nhưng trượt vùng đối tượng (*correct prediction + grounding miss*) là *"Correct Answer, Wrong Reason"* (Đúng đáp án, sai lý do), vì bộ dữ liệu hoàn toàn chưa có nhãn chuẩn về lý do con người (*human rationale ground truth*).
  - **4. Những nội dung D1 KHÔNG chốt (Deferred Items chuyển giao sang W2.2–W2.5):**  
    Quyết định D1 **chưa quyết định và không ấn định** các nội dung kỹ thuật sau:
    - Chính sách nhãn miền cuối cùng (*final domain label policy*).
    - Phương án xử lý cụ thể đối với 36 mẫu xung đột tên miền giữa thư mục và văn bản (*36 domain-mismatch samples*).
    - Quy tắc gom nhóm mẫu cuối cùng (*final grouping rule*).
    - Tập con hoặc phân chia phân tích P3 cuối cùng (*final P3 split/subset*).
    - Chuẩn hóa giao diện đầu ra định vị bằng chứng (*final grounding interface*).
    - Định nghĩa và công thức các chỉ số đánh giá cuối cùng (*final metrics*).
    - Lựa chọn các phép kiểm định thống kê chính thức (*statistical tests*).
    - Danh sách cụ thể các mô hình baseline đánh giá (*baseline model list*).
    - Chính sách và phương pháp luận xử lý nguy cơ nhiễm dữ liệu tiền huấn luyện (*model pretraining contamination policy*).  
    *Toàn bộ các nội dung trên được chuyển giao cho các bước kỹ thuật W2.2 đến W2.5 giải quyết.*
- **Lý do:**
  1. SafeShift Seminar hoàn toàn không huấn luyện hay tinh chỉnh (*no training / fine-tuning*) các mô hình VLM trên bộ dữ liệu InspecSafe-V1.
  2. Việc gọi giao thức chính của Seminar là Domain Generalization theo nghĩa học máy chuẩn sẽ gây hiểu sai phương pháp luận học thuật.
  3. Khái niệm Cross-Domain Robustness Evaluation phản ánh trung thực và chính xác việc đánh giá một mô hình huấn luyện sẵn giữ nguyên trọng số (*frozen pretrained model*) trên nhiều phân xưởng công nghiệp khác nhau.
  4. Giao thức P1 là bắt buộc và cần thiết để đối chiếu trực tiếp với bài báo gốc trên *Scientific Data*.
  5. Giao thức P2 là cần thiết để tạo đóng góp nghiên cứu vượt ra ngoài việc chỉ tái lập (*replicate*), đồng thời khắc phục khiếm khuyết tập test của miền Luyện kim không có mẫu bất thường.
  6. Giao thức P3 có giá trị cho phân tích độ nhạy (*sensitivity analysis*), nhưng hiện tại thiếu ID video thực chứng để tạo lập benchmark sạch hoàn toàn.
  7. Giao thức P4 phù hợp hơn với Luận văn tốt nghiệp (*Thesis*) vì cần quy trình huấn luyện/tinh chỉnh và thiết kế giao thức miền nguồn/miền đích phức tạp, tránh gây rủi ro trễ tiến độ Seminar 8 tuần.
- **Ảnh hưởng tới dataset, split, metric và reproducibility:**
  - **Dataset:**
    - Không sửa đổi dữ liệu thô (*raw data*).
    - Không sửa đổi nhãn gốc (*labels*).
  - **Split:**
    - P1 giữ nguyên vẹn tập `test` chính thức gồm đúng 1.250 mẫu.
    - P2 sử dụng toàn bộ 5.013 mẫu làm không gian đánh giá (*evaluation pool*), nhưng bắt buộc phải lưu giữ nguyên trạng siêu dữ liệu phân tách gốc (`split: train/test`).
    - P3 chưa được thiết kế và chưa tạo lập tập con/split mới.
    - P4 chưa triển khai trong phạm vi giai đoạn Seminar.
  - **Metrics:**
    - Quyết định D1 chưa chốt các chỉ số đánh giá cuối cùng (*final metrics*).
  - **Reproducibility (Khả năng tái lập):**
    - Đối với P1: Bắt buộc phải ghi nhận và lưu trữ chính xác câu prompt chỉ dẫn, quy trình tiền xử lý ảnh, phiên bản mô hình chi tiết, cấu hình giải mã (temperature, top_p, seed), và mốc thời gian snapshot API (nếu dùng dịch vụ trực tuyến).
    - Đối với P2: Bắt buộc phải bảo toàn sample ID, đường dẫn tệp tương đối, nhãn gốc và metadata split gốc trong toàn bộ pipeline đánh giá và lưu trữ raw model outputs.
- **Người chấp thuận và thời điểm:** Project Owner / Research Lead (Chủ dự án / Người phụ trách nghiên cứu), ngày 2026-09-16.
- **Task/thí nghiệm liên quan:**
  - [notes/w2_protocol_decision_brief.md](notes/w2_protocol_decision_brief.md) (W2.1 Decision Brief, PR #10)
  - [notes/w1_dataset_audit.md](notes/w1_dataset_audit.md) (W1 Audit Evidence)
  - Cơ sở định hướng trực tiếp cho các bước W2.2, W2.3, W2.4, W2.5 và thực thi baseline W3.
- **Thay thế quyết định:** Không (Quyết định đầu tiên của Week 2).

## Template

- **ID:** <DEC-...>
- **Ngày:** <YYYY-MM-DD>
- **Trạng thái:** <đề xuất / được chấp thuận / bị thay thế>
- **Vấn đề cần quyết định:** <nội dung>
- **Bối cảnh và bằng chứng:** <nguồn, liên kết tài liệu hoặc artifact>
- **Các phương án:** <phương án và trade-off>
- **Quyết định:** <điền khi đã chốt>
- **Lý do:** <căn cứ>
- **Ảnh hưởng tới dataset, split, metric và reproducibility:** <nội dung>
- **Người chấp thuận và thời điểm:** <điền khi được chấp thuận>
- **Task/thí nghiệm liên quan:** <relative path hoặc ID>
- **Thay thế quyết định:** <ID nếu có>
