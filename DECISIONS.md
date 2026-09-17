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
    *Trade-off:* Đúng định nghĩa học thuật truyền thống của DG; tuy nhiên phương án này chỉ khả thi một phần về nguyên lý nhưng không được khuyến nghị làm giao thức chính cho Seminar 8 tuần (`PARTIALLY_FEASIBLE, BUT NOT RECOMMENDED AS PRIMARY SEMINAR PROTOCOL`) do: cần huấn luyện/tinh chỉnh (training/tuning), chính sách phân nhóm nguồn/đích (grouping source/target) chưa được chốt, hiện tượng nhiễu nền tảng robot (platform confounding), miền Luyện kim bị thiếu hụt dữ liệu bất thường nghiêm trọng (*severely under-supported*), và gánh nặng thực nghiệm lớn hơn nhiều.
  - *Phương án B — Thuần túy Replicate Test Chính thức (P1 Only):* Đánh giá zero-shot trên tập test 1.250 mẫu của InspecSafe-V1.  
    *Trade-off:* Đơn giản, an toàn, có khả năng đối chiếu trực tiếp cao nhất với bài báo gốc cho phân loại an toàn và tương đồng ngữ nghĩa, với điều kiện tái lập được prompt, preprocessing, model/version, decoding settings và API snapshot nếu có (ghi nhận hiện tượng trôi dạt API/model drift có thể khiến kết quả số học không trùng tuyệt đối). Tuy nhiên, bỏ qua 75% dữ liệu quan sát được, hoàn toàn không đánh giá được phát hiện bất thường của miền Luyện kim (0 mẫu test Anomaly), và thiếu đóng góp nghiên cứu mới ngoài việc chạy lại baseline.
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
      - Mục tiêu chính: Trả lời các câu hỏi nghiên cứu trung tâm về độ bền vững xuyên miền (*Cross-Domain Robustness*) của SafeShift Seminar; giảm bớt hạn chế của official test đối với metallurgy bằng cách đưa toàn bộ 9 anomaly samples trong full dataset vào evaluation pool (*mitigates but does not resolve the metallurgy limitation*). Ghi nhận rõ: $N_{\text{anomaly}} = 9$ vẫn là cỡ mẫu quá nhỏ (*severely under-supported*), 8/9 mẫu mang khẳng định văn bản `text_domain = oil_chemical`, và sự mơ hồ nhãn miền vẫn tồn tại (*domain ambiguity remains*).
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
  5. Giao thức P2 là cần thiết để tạo đóng góp nghiên cứu vượt ra ngoài việc chỉ tái lập (*replicate*), đồng thời giảm bớt hạn chế của official test đối với metallurgy bằng cách đưa toàn bộ 9 anomaly samples trong full dataset vào evaluation pool (dù vẫn còn tồn tại hạn chế $N_{\text{anomaly}} = 9$ severely under-supported và domain ambiguity).
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

## DEC-W2-D2-002 — Split, Evaluation Pool, and Grouping Policy

- **ID:** DEC-W2-D2-002
- **Ngày:** 2026-09-17
- **Trạng thái:** ĐƯỢC CHẤP THUẬN
- **Vấn đề cần quyết định:**
  - Xác lập chính sách phân chia dữ liệu và không gian đánh giá cho các giao thức thực nghiệm P1 (Baseline Replication), P2 (Primary Research Protocol) và P3 (Sensitivity Protocol Candidate).
  - Phân định rạch ròi giữa đơn vị dự đoán của mô hình VLM (Prediction Unit) và đơn vị phân tích thống kê / lấy mẫu lại (Resampling / Grouping Unit).
  - Xác định tín hiệu gom nhóm ứng viên ưu tiên (preferred candidate grouping signal) cho dữ liệu Bình thường (`Normal_data`) và bản chất phụ thuộc của dữ liệu Bất thường (`Anomaly_data`).
  - Phê duyệt các tập con phân tích độ nhạy phụ trợ kiểm soát hiện tượng lặp lại ảnh nội bộ test và tái sử dụng ảnh exact xuyên split.
- **Bối cảnh và bằng chứng:**
  - Kế thừa quyết định phân tầng giao thức [DEC-W2-D1-001](#dec-w2-d1-001) và các phát hiện kiểm toán độc lập tại [notes/w1_dataset_audit.md](notes/w1_dataset_audit.md), [notes/duplicate_leakage_audit.md](notes/duplicate_leakage_audit.md), [notes/visual_provenance_review.md](notes/visual_provenance_review.md), [notes/distribution_imbalance_audit.md](notes/distribution_imbalance_audit.md).
  - Bộ dữ liệu InspecSafe-V1 gồm 5.013 ảnh: tập test chính thức gồm 1.250 ảnh (999 Normal, 251 Anomaly); 4.013 ảnh Normal được phân bố trong 2.234 thư mục điểm logic (`point_id`), mỗi điểm chứa 1–4 khung hình liền kề; 1.000 ảnh Anomaly nằm trong 1.000 thư mục điểm logic riêng biệt.
  - Có 53 cặp trùng lặp pixel tuyệt đối (106 ảnh), gồm 44 cặp within-train, 2 cặp within-test (4 ảnh) và 7 cặp cross-split (14 ảnh, đều là Anomaly). Không có ID video thật (`true video ID`) hay ID trạm vật lý (`physical site ID`) trong metadata phát hành công khai; quan hệ ánh xạ giữa 3.234 thư mục điểm logic và 2.239 trạm kiểm tra thượng nguồn vẫn chưa được giải quyết (`unresolved mapping`).
  - Báo cáo phân tích phương pháp luận chi tiết tại [notes/w2_domain_split_decision_brief.md](notes/w2_domain_split_decision_brief.md).
- **Các phương án:**
  - *Phương án 1 — Naive Image-Level (IID giả định):* Coi 5.013 ảnh hoàn toàn độc lập trong mọi khâu suy luận và thống kê. Bỏ qua phụ thuộc đa khung hình và tương quan chuỗi.
  - *Phương án 2 — Rút gọn dữ liệu cơ học (Subsampling):* Chỉ lấy khung hình đại diện `-001` cho mỗi điểm Normal (giảm 1.779 ảnh Normal) hoặc loại bỏ toàn bộ các cặp trùng lặp/ứng viên dHash. Làm méo mó quy mô dữ liệu và giảm độ bao phủ quan sát.
  - *Phương án 3 — Phân tầng giao thức kết hợp tách bạch Đơn vị dự đoán và Đơn vị gom nhóm độ nhạy (Được chọn):* P1 giữ nguyên 1.250 mẫu test; P2 đánh giá toàn bộ 5.013 mẫu với đơn vị dự đoán là từng ảnh (Image-level); phê duyệt `point_id` làm tín hiệu gom nhóm ứng viên ưu tiên cho Normal; duy trì P3 ở trạng thái Candidate Sensitivity Protocol và triển khai hai phân tích độ nhạy phụ trợ (1.248 mẫu và 1.241 mẫu).
- **Quyết định:**
  - **1. P1 — Baseline Replication Protocol (Giao thức tái lập baseline):**
    - Tập kiểm thử chính thức (*Official Test*) **giữ nguyên đúng 1.250 mẫu (samples)**.
    - **Không lọc bỏ duplicate (ảnh trùng lặp)** khỏi baseline chính.
    - *Lý do:* Giữ khả năng đối chiếu trực tiếp cao nhất với upstream baseline công bố trong bài báo gốc (*Scientific Data* 2026).
    - *Cảnh báo tái lập:* Không bảo đảm tái lập số học tuyệt đối 1:1 (*numerical 1:1 reproduction*) vì còn phụ thuộc vào: câu prompt, quy trình tiền xử lý (preprocessing), phiên bản mô hình (model/version), cấu hình giải mã (decoding settings), và hiện tượng trôi dạt snapshot/drift của API nếu có.
  - **2. P2 — Primary Evaluation Pool (Tập đánh giá nghiên cứu chính):**
    - P2 sử dụng **toàn bộ 5.013 ảnh (images)** làm Tập đánh giá nghiên cứu chính (*Primary Evaluation Pool*).
    - Bắt buộc **phải giữ nguyên siêu dữ liệu phân chia gốc (`split = train/test`)** cho từng sample trong mọi manifest và báo cáo.
    - Tuyệt đối **không được xóa bỏ nguồn gốc phân chia (*provenance*)**.
  - **3. Prediction Unit (Đơn vị dự đoán):**
    - Đơn vị dự đoán (*Prediction Unit*) được xác lập duy nhất là: **ẢNH (IMAGE)**.
    - Mỗi ảnh vẫn được mô hình VLM thực hiện suy luận riêng biệt.
    - Đầu ra thô của mô hình (*Raw model outputs*) **phải được lưu trữ ở cấp độ từng mẫu/ảnh (sample/image level)** kèm định danh sample ID, prompt, model/version, cấu hình sinh (decoding settings) và run ID trước khi thực hiện bất kỳ phép parse hay tổng hợp nào. Không chỉ lưu nhãn hoặc điểm tổng hợp.
  - **4. Normal Grouping Signal (Tín hiệu gom nhóm cho dữ liệu Bình thường):**
    - Đối với dữ liệu Bình thường (`Normal_data`): trường **`point_id` được phê duyệt là tín hiệu gom nhóm / lấy mẫu lại ứng viên ưu tiên (*preferred candidate grouping/resampling signal*)**.
    - *Cơ sở:* Nhiều điểm Normal chứa từ 1 đến 4 khung hình liền kề; `point_id` nắm bắt được cấu trúc phụ thuộc đa khung hình nội bộ điểm đã biết (*known within-point dependence*).
    - *Giới hạn bắt buộc phải ghi rõ:*
      - `point_id` là mã định danh điểm logic (*logical point identifier*).
      - `point_id` **KHÔNG phải là ID địa điểm/nhà máy vật lý (*physical site ID*)**.
      - `point_id` **không chứng minh tính độc lập giữa các điểm (*between-point independence*)**.
      - Mối quan hệ ánh xạ (*mapping*) giữa 3.234 thư mục điểm logic và 2.239 trạm tuần tra vật lý upstream vẫn **chưa được giải quyết (*unresolved mapping*)**.
  - **5. Anomaly Dependence (Sự phụ thuộc của dữ liệu Bất thường):**
    - Đối với dữ liệu Bất thường (`Anomaly_data`): đơn vị dự đoán (*prediction unit*) vẫn là từng ảnh đơn lẻ (*image-level*).
    - Mặc dù 1.000 mẫu Anomaly được tổ chức trong 1.000 thư mục điểm logic riêng biệt, nhưng **KHÔNG được coi đây là bằng chứng rằng 1.000 mẫu Anomaly là 1.000 sự kiện độc lập về mặt thống kê (*1,000 independent events*)**.
    - *Lý do:* Tồn tại bằng chứng thực chứng về chia sẻ chuỗi/góc máy quan sát (*shared-sequence / shared-viewpoint evidence*); định danh video thật (*true video IDs*) hoàn toàn không tồn tại trong siêu dữ liệu công khai.
    - Họ nguồn suy luận (*`source-family`*) **KHÔNG được dùng như cụm video thật (*true video cluster*)** vì một họ nguồn chứa nhiều cảnh quay và video clip phân tán khác nhau.
  - **6. P3 Status (Trạng thái của giao thức P3):**
    - Giao thức P3 tiếp tục duy trì ở trạng thái: **Giao thức phân tích độ nhạy ứng viên (*Candidate Sensitivity Protocol*)**.
    - P3 **KHÔNG phải là benchmark sạch (*clean benchmark*)** và **KHÔNG được gọi là benchmark không rò rỉ (*leakage-free benchmark*)**.
  - **7. Exact-Reuse Sensitivity Analyses (Phân tích độ nhạy lặp/tái sử dụng ảnh exact):**
    - Phê duyệt hai phân tích độ nhạy phụ trợ đi kèm P1:
      1. *Within-test exact-repeat sensitivity (Độ nhạy với ảnh exact lặp trong nội bộ test):* Đánh giá trên tập con **1.248 mẫu (samples)** (loại bỏ 2 mẫu lặp lại trong 2 cặp within-test).
      2. *Cross-split exact-reuse sensitivity (Độ nhạy với ảnh exact tái sử dụng xuyên split):* Đánh giá trên tập con **1.241 mẫu (samples)** (loại bỏ 2 mẫu lặp nội bộ test và 7 mẫu test có bản sao exact trong train).
    - *Quy tắc bắt buộc phải ghi:*
      - Đây thuần túy là các phân tích độ nhạy (*sensitivity analyses*), không thay thế tập kiểm thử chính thức của P1 (*official baseline*).
      - Các tập con này **không chứng minh benchmark sạch rò rỉ (*leakage-free*)**.
      - 7 cặp exact xuyên split **không tạo ra rò rỉ từ train sang test do SafeShift gây ra (*SafeShift-induced train $\rightarrow$ test leakage*)**, vì trong giao thức P1 SafeShift không thực hiện huấn luyện hay tinh chỉnh trên tập train của benchmark.
  - **8. Những nội dung kỹ thuật D2 KHÔNG chốt (Deferred Items chuyển giao sang W2.4):**
    - Quyết định D2 **KHÔNG chốt**:
      - Công thức bootstrap (*bootstrap formula*).
      - Mức khoảng tin cậy (*confidence interval level*).
      - Số lượng lượt lấy mẫu lại (*number of resamples*).
      - Các bài kiểm định giả thuyết thống kê (*hypothesis test*), kiểm định McNemar, kiểm định hoán vị (*permutation test*).
      - Mức ý nghĩa $\alpha$.
    - D2 **chỉ chốt rằng**: `point_id` là tín hiệu gom nhóm ứng viên (*candidate grouping signal*) cho `Normal_data`. Toàn bộ các nội dung phương pháp thống kê trên được chuyển giao cho bước **W2.4**.
- **Lý do:**
  1. Giao thức P1 cần bảo toàn nguyên vẹn tập kiểm thử chính thức (1.250 mẫu) để đảm bảo khả năng đối chiếu trực tiếp với upstream baseline.
  2. Giao thức P2 cần toàn bộ 5.013 ảnh để tăng độ bao phủ quan sát (*observational coverage*) giữa các miền công nghiệp và các điều kiện an toàn (*safety conditions*).
  3. Khung hình ảnh (*Image*) vẫn là đơn vị mà mô hình VLM thực sự tiếp nhận và dự đoán.
  4. Các khung hình Normal trong cùng một điểm tuần tra có tương quan góc máy và bối cảnh cao, không nên mặc định là độc lập về mặt thống kê.
  5. Đối với Anomaly, siêu dữ liệu công khai không đủ để xây dựng cấu trúc gom nhóm video thật (*true video grouping*).
  6. Vì vậy, SafeShift tách biệt rõ ràng: đánh giá nghiên cứu chính (*primary evaluation*) và phân tích độ nhạy / gom nhóm thống kê (*sensitivity / grouping analysis*).
- **Ảnh hưởng tới dataset, split, metric và reproducibility:**
  - **Dataset:** Giữ nguyên dữ liệu thô và cấu trúc tệp; không tạo dataset đã khử trùng lặp (*deduplicated dataset*).
  - **Split:** P1 giữ nguyên vẹn 1.250 mẫu test chính thức; P2 dùng toàn bộ 5.013 mẫu và bắt buộc bảo lưu trường siêu dữ liệu `split: train/test` trên từng mẫu; không tạo split sản xuất mới (*production split*).
  - **Metrics:** Chưa chốt công thức metric hay quy trình thống kê (chuyển sang W2.4).
  - **Reproducibility:** Mọi raw model outputs bắt buộc phải lưu trữ ở cấp độ sample/image kèm đầy đủ siêu dữ liệu cấu hình trước khi tổng hợp; các tập con phân tích độ nhạy (1.248 và 1.241 mẫu) được xác định tất định theo mã băm SHA-256 đã kiểm toán.
- **Người chấp thuận và thời điểm:** Project Owner / Research Lead (Chủ dự án / Người phụ trách nghiên cứu), ngày 2026-09-17.
- **Task/thí nghiệm liên quan:**
  - [notes/w2_domain_split_decision_brief.md](notes/w2_domain_split_decision_brief.md) (W2.2 Decision Brief)
  - [notes/w1_dataset_audit.md](notes/w1_dataset_audit.md), [notes/duplicate_leakage_audit.md](notes/duplicate_leakage_audit.md), [notes/visual_provenance_review.md](notes/visual_provenance_review.md), [notes/distribution_imbalance_audit.md](notes/distribution_imbalance_audit.md)
  - Quyết định nền tảng [DEC-W2-D1-001](#dec-w2-d1-001)
  - Định hướng trực tiếp cho thiết kế manifest tại W2.2, điều tra nguy cơ tại W2.3, giao thức thống kê tại W2.4 và thực thi baseline tại W3.
- **Thay thế quyết định:** Không.

## DEC-W2-D3-003 — Operational Domain Definition and Mismatch Policy

- **ID:** DEC-W2-D3-003
- **Ngày:** 2026-09-17
- **Trạng thái:** ĐƯỢC CHẤP THUẬN
- **Vấn đề cần quyết định:**
  - Xác lập nhãn miền thao tác chính thức (Operational Domain Label) cho báo cáo phân rã 5 miền công nghiệp và trả lời câu hỏi nghiên cứu RQ1 (Cross-Domain Analysis).
  - Thiết lập chính sách xử lý minh bạch đối với 36 mẫu dữ liệu xung đột giữa tên thư mục và khẳng định ngữ cảnh văn bản (`folder_domain != text_domain`).
  - Xác định chính sách báo cáo kết quả đối với miền Luyện kim (`metallurgy`) trước tình trạng thiếu hụt dữ liệu bất thường nghiêm trọng và xung đột nhãn văn bản.
  - Chuẩn hóa thuật ngữ khoa học khi phân tích mối quan hệ giữa miền công nghiệp và nền tảng robot tuần tra.
- **Bối cảnh và bằng chứng:**
  - Kế thừa quyết định phân tầng giao thức [DEC-W2-D1-001](#dec-w2-d1-001) và các phát hiện kiểm toán độc lập tại [notes/w1_dataset_audit.md](notes/w1_dataset_audit.md), [notes/distribution_imbalance_audit.md](notes/distribution_imbalance_audit.md), [notes/visual_provenance_review.md](notes/visual_provenance_review.md).
  - Cấu trúc thư mục cấp 1 chia dataset thành 5 miền: `coal_conveyor` (1.121 mẫu), `metallurgy` (720 mẫu), `oil_chemical` (1.023 mẫu), `power` (869 mẫu), `tunnel` (1.280 mẫu).
  - Kiểm toán độc lập phát hiện đúng 36 mẫu có tên thư mục khác với khẳng định mở đầu trong tệp văn bản (`folder_domain != text_domain`): 4 mẫu `power` $\rightarrow$ `coal_conveyor` (train), 8 mẫu `metallurgy` $\rightarrow$ `oil_chemical` (train), 24 mẫu `tunnel` $\rightarrow$ `oil_chemical` (20 train, 4 test).
  - Miền `metallurgy` có tổng cộng 720 mẫu (711 Normal, 9 Anomaly); tập kiểm thử chính thức (Official Test) có 177 Normal và đúng 0 Anomaly; trong 9 mẫu Anomaly ở train, có tới 8/9 mẫu mang khẳng định văn bản `text_domain = oil_chemical`; chỉ duy nhất 1 mẫu mang cả folder và text là `metallurgy` (`metallurgy-Level03-SuspendedRail-002666-001`).
  - Báo cáo phân tích phương pháp luận chi tiết tại [notes/w2_domain_split_decision_brief.md](notes/w2_domain_split_decision_brief.md).
- **Các phương án:**
  - *Chính sách D3-A (`folder_domain` Primary):* Dùng tên thư mục làm nhãn chính; giữ nguyên 36 mẫu mismatch tại thư mục, gắn cờ cảnh báo. Khớp cấu trúc đĩa và số lượng upstream; bảo toàn 720 mẫu cho metallurgy.
  - *Chính sách D3-B (`text_domain` Primary):* Dùng khẳng định văn bản làm nhãn chính; chuyển 36 mẫu theo văn bản. Gây hậu quả cực đoan: metallurgy chỉ còn 1 mẫu Anomaly.
  - *Chính sách D3-C (Exclude Mismatch):* Loại bỏ 36 mẫu khỏi phân tích từng miền; giữ trong pooled overall. Miền metallurgy vẫn chỉ còn 1 Anomaly.
  - *Chính sách D3-D (Dual-Report Sensitivity — Được chọn):* Báo cáo phân tích chính theo `folder_domain` (D3-A) kèm cờ cảnh báo; đồng thời bắt buộc báo cáo độ nhạy đối chứng theo D3-C (loại bỏ mismatch) và D3-B (tái phân bổ theo text) để kiểm tra kết luận cross-domain có bị phụ thuộc vào sự mơ hồ nhãn miền hay không.
- **Quyết định:**
  - **1. Primary Operational Domain Label (Nhãn miền thao tác chính):**
    - SafeShift sử dụng trường **`folder_domain`** làm **Nhãn miền thao tác chính (*Primary Operational Domain Label*)**.
    - Áp dụng cho:
      - Báo cáo phân rã 5 miền công nghiệp (*five-domain reporting*): `coal_conveyor`, `metallurgy`, `oil_chemical`, `power`, `tunnel`.
      - Phân tích độ bền vững xuyên miền theo câu hỏi nghiên cứu **RQ1** (*cross-domain analysis*).
  - **2. Nguyên tắc chuẩn hóa — Không gọi là Physical Ground Truth:**
    - `folder_domain` **TUYỆT ĐỐI KHÔNG ĐƯỢC GỌI LÀ**:
      - Danh tính thực địa vật lý chuẩn (*physical site ground truth*).
      - Nhận diện nhà máy đã kiểm chứng (*verified factory identity*).
      - Chân lý miền tuyệt đối (*absolute domain truth*).
    - `folder_domain` chỉ là **nhãn thao tác (*operational label*)** dựa trên cấu trúc tổ chức thư mục phát hành của bộ dữ liệu.
  - **3. Vai trò của `text_domain` (Khẳng định văn bản):**
    - Trường `text_domain` được lưu giữ như một **nhãn thao tác thay thế / dùng cho phân tích độ nhạy (*alternate / sensitivity operational label*)**.
    - `text_domain` cũng **KHÔNG phải là physical ground truth**; nó phản ánh khẳng định về bối cảnh/phân xưởng (*scene/context claim*) trong chú thích văn bản (*textual annotation*).
    - **Không mặc định tệp văn bản chuẩn (ground-truth TXT) là đầu vào (input) của mô hình VLM**.
  - **4. Chính sách xử lý 36 mẫu Domain Mismatch:**
    - Có chính xác **36 mẫu** có `folder_domain != text_domain`.
    - Phân bố chi tiết không đổi:
      - `power` $\rightarrow$ `coal_conveyor`: **4 mẫu**
      - `metallurgy` $\rightarrow$ `oil_chemical`: **8 mẫu**
      - `tunnel` $\rightarrow$ `oil_chemical`: **24 mẫu**
      - Phân chia split: **Train = 32 mẫu, Test = 4 mẫu**.
    - *Trong phân tích chính (Primary Analysis):*
      - Giữ nguyên mẫu theo miền thư mục (**`folder_domain`**).
      - Bắt buộc gắn cờ thuộc tính rõ ràng: **`domain_mismatch = True`**.
      - Tuyệt đối **không tự ý sửa đổi nhãn gốc (*no editing of raw labels*)**.
  - **5. Chính sách báo cáo độ nhạy kép (Dual-Report Sensitivity Policy):**
    - Bắt buộc phải thực hiện phân tích độ nhạy theo ít nhất:
      - *Phân tích chính (Primary):* Phân bổ theo `folder_domain`.
      - *Độ nhạy A (Sensitivity A):* Loại bỏ (*exclude*) 36 mẫu mismatch khỏi các phân tích theo từng miền (*per-domain analysis*), nhưng vẫn có thể giữ lại trong tập đánh giá tổng thể gộp (*pooled overall*) nếu quy tắc metric sau này quy định.
      - *Độ nhạy B (Sensitivity B):* Tái phân bổ (*reassign*) các mẫu mismatch theo khẳng định văn bản `text_domain`.
    - *Mục đích:* Kiểm tra xem kết luận so sánh xuyên miền (*cross-domain conclusions*) có phụ thuộc mạnh vào sự mơ hồ về nhãn miền (*domain-label ambiguity*) hay không.
  - **6. Chính sách đặc thù cho Miền Luyện kim (`metallurgy`):**
    - **Giữ nguyên miền `metallurgy`** trong bảng báo cáo 5 miền công nghiệp.
    - *Các sự thật thực chứng bắt buộc ghi rõ:*
      - Tổng số mẫu (Total): **720 mẫu**.
      - Mẫu bình thường (Normal): **711 mẫu**.
      - Mẫu bất thường (Anomaly): **9 mẫu**.
      - Số mẫu bất thường trong tập test chính thức (Official test anomaly): **0 mẫu**.
      - Có **8/9 mẫu Anomaly** thuộc thư mục `metallurgy` mang khẳng định văn bản: **`text_domain = oil_chemical`**.
      - Nếu tái phân bổ theo `text_domain` (Sensitivity B), số mẫu Anomaly của `metallurgy` giảm từ **9 mẫu xuống còn đúng 1 mẫu duy nhất** ($9 \rightarrow 1$).
      - Mẫu duy nhất có cả `folder_domain` và `text_domain` cùng là `metallurgy` là: `metallurgy-Level03-SuspendedRail-002666-001`.
    - *Quy tắc diễn giải khoa học:*
      - Ghi nhận rõ ràng: lớp bất thường của miền luyện kim bị thiếu hụt dữ liệu hỗ trợ nghiêm trọng (*metallurgy anomaly class is severely under-supported*).
      - **Tuyệt đối không tuyên bố cỡ mẫu $N=9$ là đủ cho suy luận thống kê (*statistical inference*)**.
      - Nếu theo phân tích độ nhạy số mẫu chỉ còn $N=1$: mọi con số nhạy với mẫu bất thường (*anomaly-sensitive metrics*) **chỉ mang tính mô tả đơn thuần (*descriptive only*)**, hoàn toàn không đủ cho suy luận thống kê ổn định (*not sufficient for stable inference*).
      - Cách thức xử lý chỉ số định lượng cuối cùng (*final metric handling*) được chuyển giao cho **bước W2.4 quyết định**.
  - **7. Chuẩn hóa thuật ngữ nền tảng robot (Robot Platform Terminology):**
    - Khi phân tích mối liên hệ giữa miền công nghiệp và nền tảng robot tuần tra:
      - Bắt buộc sử dụng thuật ngữ: **"đồng biến thiên với nền tảng robot" (*co-variation with robot platform*)** hoặc **"nhiễu nền tảng robot" (*platform confounding*)**.
      - **Tuyệt đối KHÔNG đưa ra khẳng định nhân quả (*causal claim*)**: "nền tảng robot gây ra suy giảm hiệu năng" (*robot platform causes performance drop*).
  - **8. Những nội dung kỹ thuật D2/D3 KHÔNG chốt (Deferred Items chuyển giao sang W2.3–W2.5):**
    - Quyết định D2 và D3 **KHÔNG chốt**:
      - Các chỉ số đánh giá cuối cùng (*final metrics*).
      - Chi tiết triển khai Macro-F1 (*Macro-F1 implementation details*).
      - Chi tiết Balanced Accuracy (*Balanced Accuracy details*).
      - Định nghĩa tỷ lệ dương tính giả / âm tính giả (*FPR/FNR definitions*).
      - Công thức suy giảm hiệu năng xuyên miền (*cross-domain drop formula*).
      - Quy trình bootstrap cuối cùng (*final bootstrap procedure*).
      - Mức độ tin cậy (*confidence level*).
      - Các bài kiểm định giả thuyết thống kê (*statistical hypothesis tests*).
      - Các chỉ số bám bằng chứng không gian (*grounding metrics*).
      - Hệ thống phân loại nguy cơ (*hazard taxonomy*).
      - Danh sách mô hình baseline (*model list*).
      - Câu lệnh chỉ dẫn (*prompt*).
      - Chính sách xử lý nguy cơ nhiễm dữ liệu tiền huấn luyện (*contamination policy*).
    - Toàn bộ các mục trên thuộc về các bước tiếp theo: **W2.3, W2.4, W2.5** tùy nội dung.
- **Lý do:**
  1. Trường `folder_domain` có độ bao phủ 100% và hoàn toàn tất định theo cấu trúc phát hành của bộ dữ liệu.
  2. Nhưng 36 mẫu mismatch chứng minh thực tế rằng `folder_domain` không phải là chân lý tuyệt đối (*not absolute truth*).
  3. Trường `text_domain` cung cấp bằng chứng ngữ nghĩa (*semantic evidence*) nhưng cũng có thể chứa lỗi sao chép hoặc định dạng mẫu văn bản của annotator.
  4. Do không có danh tính trạm vật lý thực địa (*physical site ground truth*), không có nguồn siêu dữ liệu nào được coi là chân lý tuyệt đối.
  5. Cơ chế báo cáo kép (Primary + Sensitivity Dual-Report) giúp giữ vững tính tái lập (*reproducibility*) đồng thời minh bạch hoàn toàn về sự mơ hồ nhãn miền (*domain ambiguity*).
  6. Miền Luyện kim (`metallurgy`) là trường hợp nhạy cảm nhất: có 9 mẫu bất thường theo thư mục, nhưng chỉ còn đúng 1 mẫu bất thường nếu phân loại lại theo văn bản.
- **Ảnh hưởng tới dataset, split, metric và reproducibility:**
  - **Dataset:** Tuyệt đối không sửa đổi tên thư mục hoặc nhãn văn bản gốc trong dữ liệu thô. Cờ `domain_mismatch = True` được bổ sung trong manifest phái sinh tại `data/processed/`.
  - **Split:** Không làm thay đổi phân chia train/test; bảo toàn 5 miền công nghiệp.
  - **Metrics:** Chưa chốt công thức đo lường hoặc cách triệt tiêu metric cho Metallurgy (chuyển sang W2.4).
  - **Reproducibility:** Mọi báo cáo phân rã 5 miền phải công bố rõ việc sử dụng `folder_domain` làm nhãn chính và đi kèm bảng phân tích độ nhạy đối chứng theo danh sách 36 mẫu mismatch cố định.
- **Người chấp thuận và thời điểm:** Project Owner / Research Lead (Chủ dự án / Người phụ trách nghiên cứu), ngày 2026-09-17.
- **Task/thí nghiệm liên quan:**
  - [notes/w2_domain_split_decision_brief.md](notes/w2_domain_split_decision_brief.md) (W2.2 Decision Brief)
  - [notes/w1_dataset_audit.md](notes/w1_dataset_audit.md), [notes/distribution_imbalance_audit.md](notes/distribution_imbalance_audit.md), [notes/visual_provenance_review.md](notes/visual_provenance_review.md)
  - Quyết định nền tảng [DEC-W2-D1-001](#dec-w2-d1-001)
  - Định hướng trực tiếp cho thiết kế manifest tại W2.2, điều tra phân tầng nguy cơ tại W2.3, định nghĩa metric tại W2.4 và thực thi baseline tại W3.
- **Thay thế quyết định:** Không.

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
