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
  - Có 53 cặp trùng lặp pixel tuyệt đối (106 ảnh), gồm 44 cặp within-train, 2 cặp within-test (4 ảnh) và 7 cặp cross-split (14 ảnh, đều là Anomaly). Không có ID video thật (`true video ID`) hay ID trạm vật lý (`physical site ID`) trong metadata phát hành công khai; quan hệ ánh xạ giữa 3.234 thư mục điểm logic (*logical point folders*) và 2.239 điểm/trạm kiểm tra hợp lệ (*valid inspection sites/waypoints*) được tài liệu upstream công bố vẫn chưa được giải quyết (`unresolved mapping`), và không suy diễn 2.239 điểm này là các vị trí vật lý độc lập (*independent physical locations*).
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
      - `point_id` là mã định danh điểm logic (*logical point identifier*); 3.234 point folders là logical point folders.
      - `point_id` **KHÔNG phải là ID địa điểm/nhà máy vật lý (*physical site ID*)**; hoàn toàn không có sample-level physical site ID trong metadata công khai.
      - `point_id` **không chứng minh tính độc lập giữa các điểm (*between-point independence*)**.
      - Mối quan hệ ánh xạ (*mapping*) giữa 3.234 logical point folders và **2.239 điểm/trạm kiểm tra hợp lệ (*valid inspection sites/waypoints*) được tài liệu upstream công bố** vẫn **chưa được giải quyết (*unresolved mapping*)**; không được gọi 2.239 điểm đó là confirmed physical sites hay suy diễn chúng là các vị trí vật lý độc lập (*independent physical locations*).
  - **5. Anomaly Dependence (Sự phụ thuộc của dữ liệu Bất thường):**
    - Đối với dữ liệu Bất thường (`Anomaly_data`): đơn vị dự đoán (*prediction unit*) vẫn là từng ảnh đơn lẻ (*image-level*).
    - Mặc dù 1.000 mẫu Anomaly được tổ chức trong 1.000 thư mục điểm logic riêng biệt, nhưng **KHÔNG được coi đây là bằng chứng rằng 1.000 mẫu Anomaly là 1.000 sự kiện độc lập về mặt thống kê (*1,000 independent events*)**.
    - *Lý do:* Tồn tại bằng chứng thực chứng về chia sẻ chuỗi/góc máy quan sát (*shared-sequence / shared-viewpoint evidence*); định danh video thật (*true video IDs*) hoàn toàn không tồn tại trong siêu dữ liệu công khai.
    - Họ nguồn suy luận (*`source-family`*) **KHÔNG được dùng như cụm video thật (*true video cluster*)** vì tư cách thành viên trong cùng một family không đủ để chứng minh tất cả thành viên thuộc cùng một video hay temporal sequence. Một family CÓ THỂ chứa nhiều scene/video/viewpoint, trong khi một số family hoặc subset lại có bằng chứng chuỗi liên tục mạnh (*strong shared-sequence evidence*). `source-family` chỉ là tín hiệu kinh nghiệm (*heuristic signal*), **không phải là true video ID**.
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
  - **Dataset:** Tuyệt đối không sửa đổi tên thư mục hoặc nhãn văn bản gốc trong dữ liệu thô. Cờ `domain_mismatch = True` phải được bảo toàn trong manifest/metadata phái sinh khi triển khai. Đường dẫn artifact cụ thể tuân theo convention của dự án (`data/manifests/` hoặc `data/processed/` tùy loại artifact) và không được D3 khóa cứng. Ghi rõ: bước W2.2 chưa tạo production split hay production manifest mới.
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

## DEC-W2-D4-004 — Canonical Grounding Output Interface

- **ID:** DEC-W2-D4-004
- **Ngày:** 2026-09-17
- **Trạng thái:** ĐƯỢC CHẤP THUẬN
- **Vấn đề cần quyết định:**
  - Chuẩn hóa định dạng biểu diễn không gian nội bộ chuẩn mực (Internal Canonical Representation) cho đầu ra bám bằng chứng (Grounding Output) của các mô hình Vision-Language Models (VLM).
  - Thiết lập chính sách bảo toàn phản hồi thô của mô hình (Raw Model Response Preservation) và các trường siêu dữ liệu tối thiểu bắt buộc lưu trữ trước khi phân tích cú pháp (parse).
  - Xác lập vai trò và nguyên tắc chuyển đổi tất định (deterministic conversion) của bộ điều hợp / phân tích cú pháp (Adapter / Parser) từ định dạng gốc của từng mô hình (native format) sang định dạng chuẩn hóa nội bộ.
  - Thiết lập chính sách phân tầng theo năng lực mô hình (Capability-Aware Policy B) cho đường đua định vị không gian (Spatial Grounding Benchmark) so với phân loại an toàn (Classification Benchmark).
  - Phân định rõ các nội dung kỹ thuật mà D4 chưa chốt và chuyển giao cho W2.4 và W2.5.
- **Bối cảnh và bằng chứng:**
  - Kế thừa quyết định phân tầng giao thức [DEC-W2-D1-001](#dec-w2-d1-001) (RQ3 Consistency), [DEC-W2-D2-002](#dec-w2-d2-002) (Image-level Prediction Unit, Raw Output Storage Requirement) và [DEC-W2-D3-003](#dec-w2-d3-003).
  - Báo cáo căn cứ kỹ thuật phương pháp luận chi tiết tại [notes/w2_grounding_census_decision_brief.md](notes/w2_grounding_census_decision_brief.md) (Mục 13, 14, 18.1, 19).
  - Bộ dữ liệu InspecSafe-V1 chứa 37.434 đa giác đối tượng gốc trong tệp JSON, hoàn toàn không có bounding box nguy cơ chuyên biệt hay nhãn rationale của con người ([notes/w1_dataset_audit.md](notes/w1_dataset_audit.md), [notes/dataset_schema.md](notes/dataset_schema.md), [notes/research_feasibility_audit.md](notes/research_feasibility_audit.md)). Bounding box chỉ có thể được suy biến toán học tất định (derived) từ tọa độ cực biên của đa giác: $[x_{\min}, y_{\min}, x_{\max}, y_{\max}]$.
  - Các họ mô hình VLM có giao diện và định dạng gốc rất khác nhau: một số mô hình tài liệu chính thức công bố hỗ trợ normalized bounding box theo thang $[0, 1000]$ và thứ tự $y$-first `[ymin, xmin, ymax, xmax]` (ví dụ Google Gemini); một số mô hình mã nguồn mở hỗ trợ `[xmin, ymin, xmax, ymax]` trên thang $[0, 1]$; trong khi các giao diện API thương mại đóng (Closed-API) nhìn chung không công bố bản đồ chú ý (attention maps). Khả năng xuất tọa độ thực tế của từng mô hình/phiên bản cần được kiểm chứng thực nghiệm tại bước W2.5.
- **Các phương án:**
  - *Phương án D4-A — Textual Normalized Bounding Box (Được chọn làm ứng viên chuẩn hóa):* Mô hình xuất hộp bao chuẩn hóa dạng chuỗi văn bản trong luồng sinh; adapter chuẩn hóa về canonical format nội bộ.  
    *Ưu điểm:* Gọn gàng, dễ parse tự động bằng biểu thức chính quy, tương thích tự nhiên với việc suy biến từ đa giác ground truth gốc, lưu giữ đầy đủ thông tin không gian (vị trí, kích thước, tỷ lệ khung hình) và có tính tái lập thực nghiệm cao.
  - *Phương án D4-B — Pointing Point (Tọa độ điểm trỏ tâm):* Mô hình xuất cặp tọa độ $[x, y]$. Cú pháp cực ngắn nhưng mất hoàn toàn thông tin về quy mô kích thước và ranh giới không gian, không thể tính toán chỉ số giao thoa diện tích (IoU).
  - *Phương án D4-C — Polygon / Segmentation Mask (Đa giác / Mặt nạ nhị phân):* Khớp 1:1 với định dạng đa giác gốc nhưng tiêu tốn token khổng lồ và tỷ lệ lỗi parse/lỗi cú pháp rất cao trên các mô hình tổng quát.
  - *Phương án D4-D — Attention Map / Visual Heatmap (Bản đồ chú ý thị giác):* Nhìn chung không được mở (not exposed) trên các giao diện Closed-API ứng viên; không phản ánh suy luận nhân quả và khác biệt kiến trúc giữa các mô hình triệt tiêu tính so sánh công bằng.
- **Quyết định:**
  - **1. Internal Canonical Bounding Box (Hộp bao chuẩn nội bộ):**
    - SafeShift xác lập định dạng biểu diễn không gian nội bộ chuẩn mực duy nhất (`Internal Canonical Representation`) cho mọi phép tính toán hình học và đánh giá bám bằng chứng:
      $$\mathbf{b}_{\text{canonical}} = [x_{\min}, y_{\min}, x_{\max}, y_{\max}]$$
      với các giá trị tọa độ được chuẩn hóa duy nhất trong đoạn:
      $$[0.0, 1.0]$$
    - Thứ tự tọa độ chuẩn hóa bắt buộc là: **$x$-first** (hoành độ trước, tung độ sau: $x_{\min}, y_{\min}, x_{\max}, y_{\max}$).
  - **2. Raw Model Response (Phản hồi thô của mô hình):**
    - Toàn bộ chuỗi văn bản phản hồi thô nguyên gốc của mô hình (`Raw Model Response`) **bắt buộc phải được lưu trữ nguyên văn trước khi thực hiện bất kỳ phép phân tích cú pháp (parse) hay tổng hợp nào**.
    - **Tuyệt đối không ghi đè (không overwrite)** tệp raw response trong bất kỳ trường hợp nào.
    - Mọi bản ghi phản hồi thô bắt buộc phải lưu trữ siêu dữ liệu tối thiểu:
      - `sample_id` (định danh mẫu ảnh)
      - `run_id` (định danh lần chạy thực nghiệm)
      - `model_name` (tên mô hình)
      - `model_version` (phiên bản cụ thể / snapshot mô hình)
      - `prompt_template_id` (định danh mẫu prompt sử dụng)
      - `decoding settings` / `decoding_parameters` (temperature, top_p, seed, v.v.)
      - `timestamp` (thời gian thực thi, ISO 8601 / UTC)
  - **3. Adapter / Parser (Bộ chuyển đổi / Phân tích cú pháp):**
    - Thừa nhận thực tế mỗi mô hình VLM có thể trả về định dạng gốc (`native format`) khác nhau.
    - Bộ điều hợp / phân tích cú pháp (`Adapter / Parser`) được phép và có nhiệm vụ chuyển đổi tất định:
      - Thứ tự tọa độ từ $y$-first sang $x$-first (ví dụ: `[ymin, xmin, ymax, xmax]` $\rightarrow$ `[xmin, ymin, xmax, ymax]`).
      - Thang đo từ $[0, 1000]$ sang $[0, 1]$ (ví dụ: chia cho 1000.0).
      - Các định dạng tọa độ đặc thù của từng mô hình (`model-specific coordinate formats`) sang định dạng chuẩn hóa nội bộ `[x_min, y_min, x_max, y_max]`.
    - Quy trình chuyển đổi (`Conversion`) bắt buộc phải **tất định hoàn toàn (deterministic)**, không dùng giải thuật ước lượng ngẫu nhiên hay heuristic không có tài liệu kỹ thuật kiểm chứng.
  - **4. Capability-Aware Policy B (Chính sách phân tầng theo năng lực mô hình):**
    - **Classification Benchmark (Benchmark phân loại an toàn):** Chạy và đánh giá trên toàn bộ danh sách các mô hình được lựa chọn tham gia thử nghiệm.
    - **Spatial Grounding Benchmark (Benchmark bám vùng không gian):** Chỉ chạy trên tập con các mô hình / giao diện thực sự có năng lực hỗ trợ đầu ra định vị (`localization output`).
    - **Tính đủ điều kiện (Eligibility) của từng mô hình / phiên bản:** Quyết định D4 **chưa tự giả định** tính đủ điều kiện của bất kỳ mô hình nào. Năng lực định vị thực tế của từng mô hình/phiên bản/giao diện bắt buộc phải được khảo sát và xác minh thực nghiệm tại bước **W2.5**.
    - **Các quy tắc cấm tuyệt đối trong đánh giá:**
      - **Tuyệt đối không được** coi việc một mô hình không tham gia track grounding (do không hỗ trợ xuất tọa độ) là một lỗi bám bằng chứng (`grounding failure`).
      - **Tuyệt đối không được** xếp hạng các mô hình không tham gia grounding track trong bảng xếp hạng năng lực bám bằng chứng (`grounding ranking`).
      - **Tuyệt đối không được** tùy biến nội dung câu lệnh ngữ nghĩa riêng (`custom semantic prompt`) cho từng mô hình để "cứu" mô hình yếu. Mọi mô hình tham gia grounding track phải sử dụng chung một cấu trúc prompt ngữ nghĩa chuẩn hóa.
  - **5. Những nội dung kỹ thuật D4 KHÔNG chốt (Deferred Items chuyển giao sang W2.4 / W2.5):**
    - Quyết định D4 **chưa quyết định và không ấn định**:
      - Ngưỡng IoU đánh giá hộp bao trúng đích (`IoU threshold`).
      - Ngưỡng / bán kính dung sai của Pointing Game (`Pointing Game threshold / tolerance radius`).
      - Các chỉ số đánh giá bám bằng chứng cuối cùng (`final grounding metrics`).
      - Danh sách các mô hình cụ thể tham gia benchmark (`final model list`).
      - Câu chữ chi tiết của câu lệnh chỉ dẫn cuối cùng (`final prompt wording`).
    - Toàn bộ các chỉ số và ngưỡng thống kê thuộc thẩm quyền của bước **W2.4 (DEC-W2-D5)**; danh sách mô hình và kiểm chứng năng lực prompt thuộc thẩm quyền của bước **W2.5**.
- **Lý do:**
  1. Chuẩn hóa định dạng nội bộ `[x_min, y_min, x_max, y_max] \in [0.0, 1.0]` tạo ra một giao diện toán học thống nhất, cho phép so sánh công bằng giữa các mô hình bất kể định dạng native của nhà cung cấp.
  2. Bắt buộc lưu trữ nguyên văn Raw Model Response là nguyên tắc sống còn của nghiên cứu tái lập, cho phép kiểm tra lại và sửa đổi bộ parser trong tương lai mà không phải chạy lại các lệnh gọi API tốn kém.
  3. Cơ chế adapter tất định tôn trọng sự đa dạng kiến trúc của VLM mà không áp đặt định dạng của một nhà cung cấp đơn lẻ thành chuẩn toàn ngành.
  4. Chính sách phân tầng Policy B ngăn ngừa thiên lệch đánh giá: không phạt oan mô hình phân loại thuần túy, không xếp hạng sai lệch, và giữ nguyên tính so sánh khoa học qua việc dùng chung cấu trúc prompt ngữ nghĩa.
- **Ảnh hưởng tới dataset, split, metric và reproducibility:**
  - **Dataset:** Giữ nguyên dữ liệu thô và các tệp JSON chú thích gốc.
  - **Split:** Không làm thay đổi phân chia train/test.
  - **Metrics:** Chưa chốt ngưỡng IoU hay công thức metric (chuyển sang W2.4).
  - **Reproducibility:** Mọi lần chạy suy luận grounding bắt buộc phải ghi lại raw output và metadata đầy đủ; adapter chuyển đổi phải có kiểm thử đơn vị bảo đảm tính tất định.
- **Người chấp thuận và thời điểm:** Project Owner / Research Lead (Chủ dự án / Người phụ trách nghiên cứu), ngày 2026-09-17.
- **Task/thí nghiệm liên quan:**
  - [notes/w2_grounding_census_decision_brief.md](notes/w2_grounding_census_decision_brief.md) (W2.3 Decision Brief, Mục 13, 14, 18.1, 19)
  - [notes/research_feasibility_audit.md](notes/research_feasibility_audit.md)
  - [notes/dataset_schema.md](notes/dataset_schema.md)
  - Quyết định nền tảng [DEC-W2-D1-001](#dec-w2-d1-001), [DEC-W2-D2-002](#dec-w2-d2-002), [DEC-W2-D3-003](#dec-w2-d3-003)
  - Định hướng trực tiếp cho định nghĩa metric tại W2.4, khảo sát mô hình tại W2.5 và thực thi baseline tại W3.
- **Thay thế quyết định:** Không.

## DEC-W2-D5-005 — Metrics & Statistical Evaluation Protocol

- **ID:** DEC-W2-D5-005
- **Ngày:** 2026-09-17
- **Trạng thái:** ĐƯỢC CHẤP THUẬN
- **Vấn đề cần quyết định:**
  - Xác lập các chỉ số phân loại an toàn chính thức (Classification Metrics) và chỉ số sai số an toàn trọng yếu (Safety-Critical Error Metrics) cho bài toán phân loại 4 cấp độ an toàn và phát hiện bất thường nhị phân.
  - Thiết lập chính sách xử lý hiện tượng thiếu hụt lớp / hỗ trợ thưa thớt ở từng miền công nghiệp (Missing-Class / Domain Support Policy) và chính sách báo cáo miền có hiệu năng thấp nhất (Worst-Domain Reporting Policy).
  - Chuẩn hóa mỏ neo so sánh chính cho độ bền vững xuyên miền (Cross-Domain Robustness Gap / Drop) phục vụ câu hỏi nghiên cứu RQ1.
  - Phê chuẩn hệ thống chỉ số phân tầng nguy cơ RQ2 trên 7 tầng nguy cơ gom nhóm (Candidate Grouped Hazard Strata) và quy tắc phương pháp luận kiểm soát hiện tượng chồng lấn đa nguy cơ (Multi-Stratum Overlap).
  - Xác lập giao thức đánh giá bám bằng chứng trực tiếp (RQ3-A Direct Grounding): định nghĩa tập vùng GT ứng viên ($R_j$), chỉ số liên tục chính (End-to-End Mean IoU, Median IoU), các ngưỡng nhạy xác định trước (Hit@0.25, Hit@0.50), chuẩn hóa Pointing Hit trên đa giác gốc, và phân định triệt để hai chế độ ghép cặp tối ưu (Mode A vs Mode B).
  - Phê chuẩn giao thức đánh giá bám bằng chứng đại diện yếu (RQ3-B Weak Proxy Grounding) qua chỉ số Identity-Agnostic Proxy Localization Consistency (PLC), phân tích độ nhạy trên tập con đơn người (Single-Person Proxy Subset), và các biến đồng biến chẩn đoán kích thước/độ hiếm.
  - Chuẩn hóa chỉ số không nhất quán phân loại – bám bằng chứng ($\text{CGI}@\tau$) theo ngưỡng phân vị xác định trước.
  - Xác định chính sách xử lý lỗi phân tích cú pháp (Parse Failure) và loại trừ các nguyên tử không có GT không gian (Unsupported Atoms).
  - Phê chuẩn phương pháp ước lượng bất định và khoảng tin cậy chính thức (Domain-Stratified Point-Cluster Bootstrap) cùng phương pháp so sánh mô hình theo cặp (Paired Bootstrap Difference CI 95%).
  - Xác định phạm vi áp dụng trên các phân tầng giao thức P1, P2, P3 và phân tích độ nhạy với 36 mẫu xung đột nhãn miền.
  - Xác lập chính sách đối với độ hiệu chỉnh xác suất (Calibration) và chỉ số ảo giác đối tượng (Object Hallucination).
- **Bối cảnh và bằng chứng:**
  - Kế thừa toàn bộ hệ thống quyết định đã khóa: [DEC-W2-D1-001](#dec-w2-d1-001) (Research Framing & Protocol Hierarchy: P1/P2/P3/P4, RQ1/RQ2/RQ3), [DEC-W2-D2-002](#dec-w2-d2-002) (Image-level Prediction Unit, Normal `point_id` Resampling Cluster, Anomaly Dependence), [DEC-W2-D3-003](#dec-w2-d3-003) (`folder_domain` Primary, 36 Mismatch Dual-Report Sensitivity), [DEC-W2-D4-004](#dec-w2-d4-004) (Canonical Bounding Box $[x_{\min}, y_{\min}, x_{\max}, y_{\max}] \in [0, 1]$, Raw Response Preservation, Capability-Aware Policy B), [DEC-W2-D6-006](#dec-w2-d6-006) (12 Hazard Atoms, 3 Support Statuses: 781 Direct / 947 Proxy / 60 Unsupported atoms, 7 Grouped Hazard Strata), và [DEC-W2-D7-007](#dec-w2-d7-007) (Chọn D7-A không tạo nhãn rationale mới, loại bỏ Object Hallucination Rate toàn bộ dataset).
  - Báo cáo căn cứ kỹ thuật phương pháp luận chi tiết tại [notes/w2_metrics_statistics_decision_brief.md](notes/w2_metrics_statistics_decision_brief.md) (W2.4 Decision Brief, branch protocol/w2-metrics-statistics, technical evidence finalized at commit a0118b44b674146e3588d4f0616ecdbe52eff089).
  - Kết quả kiểm toán thực chứng bổ sung (Provenance & Audit Evidence):
    - *Kiểm toán tập vùng GT Direct (Direct Region Audit):* Trên toàn bộ 781 Direct hazard atoms (phân bố trên 721 mẫu thuộc `Direct-Support Sample Pool`), 100% sở hữu ít nhất một đa giác GT hỗ trợ hợp lệ ($|R_j| \ge 1$, đúng 0 trường hợp rỗng); trong đó 680 atoms đơn vùng ($|R_j|=1$, 87,07%) và 101 atoms đa vùng ($|R_j|>1$, 12,93%, chứa từ 2 đến 8 đa giác hỗ trợ).
    - *Kiểm toán vùng đại diện người (Weak-Proxy Person Audit):* Trên toàn bộ 608 mẫu thuộc `Weak-Proxy Sample Pool`, có 410 mẫu đơn người ($|\text{Person}|=1$, 67,43%) và 198 mẫu đa người ($|\text{Person}|>1$, 32,57%, chứa từ 2 đến 8 người); trong 947 Weak-Proxy atoms, có 614 atoms nằm trong ảnh đơn người (64,84%) và 333 atoms nằm trong ảnh đa người (35,16%).
    - *Kiểm toán mẫu đa nguy cơ (Multi-Hazard):* Có 512 / 1.000 mẫu Anomaly (51,2%) chứa từ 2 nguyên tử nguy cơ trở lên; 7 tầng nguy cơ gom nhóm tạo ra 1.381 lượt thành viên (memberships) trên 1.000 mẫu ảnh độc nhất.
    - *Hồ sơ nguồn gốc kiểm toán (Audit Provenance):* Lệnh thực thi `python scratch/audit_gt_regions.py`, Python 3.11.9, Windows 11 x64, timestamp `2026-09-17 05:22:14 UTC`; Input Fingerprint SHA-256: `7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`; D6 Census SHA-256 (`data/manifests/w2_grounding_census.json`): `cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`; Audit Script SHA-256: `90c704af291fb34725b6a679f3bdb2a84d18297628c569497e34309ed49cee50`. (Ghi rõ: Script là local scratch script, không commit vào Git repository, không tuyên bố khả năng tái lập chỉ bằng repo thuần túy).
- **Các phương án:**
  - *Chỉ số phân loại 4 lớp:* (1) Raw Accuracy: Bị chi phối hoàn toàn bởi 80% Normal; (2) Balanced Accuracy đơn độc: Đo trực tiếp Recall không thiên vị nhưng không phạt báo động giả; (3) Macro-F1 đơn độc: Cân bằng FP và FN nhưng cực kỳ nhạy cảm với lớp hiếm $N=15$; (4) Balanced Accuracy + Macro-F1 song hành (Được chọn): Bổ sung cho nhau, đo trọn vẹn cả độ bao quát an toàn và khả năng kiểm soát báo động giả.
  - *Chỉ số sai số an toàn:* (1) FNR gộp chung: Mơ hồ và ngụy biện phương pháp luận; (2) Tách Track A (Binary Anomaly Detection) và Track B (Level01 One-vs-Rest) riêng biệt (Được chọn): Phân định rạch ròi giữa rủi ro bỏ sót bất thường tổng thể và bỏ sót sự cố nguy hiểm thảm khốc.
  - *Chính sách miền thiếu lớp:* (1) Support-only macro average: Ngụy biện so sánh các miền trên đề bài khác nhau ($K=3$ vs $K=4$); (2) Cố định 4 lớp (gán NA khi thiếu): Làm khuyết 40% số miền; (3) Dual-Layer Support-Aware Policy (Được chọn): Báo cáo mô tả có gắn cờ $K_d$ và lấy Class-Conditional Recall làm mỏ neo so sánh chính.
  - *Độ suy giảm xuyên miền (RQ1):* (1) Balanced Accuracy Spread thuần túy: Bỏ qua 2/5 miền; (2) Class-Conditional Domain Analysis (Được chọn): So sánh trên từng lớp có hỗ trợ ground truth để giảm ảnh hưởng của class-prevalence confounding (nhiễu do tỷ lệ lớp), kết hợp Balanced Accuracy Spread trên tập so sánh được ($K=4$) làm chẩn đoán phụ trợ.
  - *Báo cáo Worst-Domain:* (1) Ngưỡng cơ học $N \ge 30$: Tùy tiện, thiếu cơ sở toán học; (2) Observed numerical minimum among comparable domains (Được chọn): Minh bạch mẫu số, kèm khoảng tin cậy và gắn nhãn Sparse-Support / Descriptive-Only cho `metallurgy`.
  - *Định vị Direct Grounding:* (1) Hit@0.25 đơn độc: Dễ gây tranh cãi về ngưỡng; (2) Continuous IoU làm Primary kết hợp Threshold Sensitivity (Hit@0.25, Hit@0.50 xác định trước) và phân định 2 chế độ ghép cặp Mode A / Mode B (Được chọn).
  - *Định vị Weak Proxy:* (1) Áp dụng IoU với Person: Ngụy biện, phạt mô hình nhìn đúng vùng đầu/tay; (2) Identity-Agnostic Proxy Localization Consistency (Center-in-Proxy + Box Containment) kết hợp kiểm tra độ nhạy trên Single-Person Proxy Subset (Được chọn).
  - *Ước lượng bất định:* (1) Stratified theo Domain $\times$ Level: Gây lỗi phương sai 0 giả tạo (artificial zero resampling variance) trên các phân tầng đơn mẫu ($N=1$); (2) Domain-Stratified Point-Cluster Bootstrap (Được chọn): Phân tầng duy nhất theo miền, lấy mẫu lại theo cụm `point_id`, xử lý known within-point dependence của các frame liên quan mà không bóp méo phương sai.
  - *So sánh mô hình:* (1) Phép kiểm định 2 mẫu độc lập: Sai phương pháp luận (dữ liệu theo cặp); (2) Paired Bootstrap Difference CI 95% trên cùng tập replicate (Được chọn): Tập trung vào độ lớn hiệu ứng và hướng phân hóa thực chất.
- **Quyết định:**
  - **1. Phê duyệt Cặp Chỉ số Phân loại Chính (Classification Primary Co-Metrics):**
    - **Primary Co-Metrics (Hai chỉ số chính song hành):**
      1. **Balanced Accuracy (Độ chính xác cân bằng / Macro-Recall):**
         $$\text{Balanced Accuracy} = \frac{1}{|\mathcal{C}_{\text{eval}}|} \sum_{c \in \mathcal{C}_{\text{eval}}} \text{Recall}_c = \frac{1}{|\mathcal{C}_{\text{eval}}|} \sum_{c \in \mathcal{C}_{\text{eval}}} \frac{\text{TP}_c}{\text{TP}_c + \text{FN}_c}$$
      2. **Macro-F1 (F1 trung bình không trọng số giữa các lớp):**
         $$\text{Macro-F1} = \frac{1}{|\mathcal{C}_{\text{eval}}|} \sum_{c \in \mathcal{C}_{\text{eval}}} \text{F1}_c, \quad \text{với } \text{F1}_c = \frac{2 \cdot \text{Precision}_c \cdot \text{Recall}_c}{\text{Precision}_c + \text{Recall}_c} = \frac{2 \cdot \text{TP}_c}{2 \cdot \text{TP}_c + \text{FP}_c + \text{FN}_c}$$
         *(Quy ước kỹ thuật: Nếu $\text{TP}_c + \text{FP}_c = 0$, đặt $\text{Precision}_c = 0.0$; nếu $\text{TP}_c = 0$, đặt $\text{F1}_c = 0.0$)*.
    - **Raw Accuracy (Độ chính xác thông thường):**
      - Xếp vào diện **DESCRIPTIVE ONLY (Chỉ dùng mô tả phụ trợ / đối chiếu upstream)**.
      - **Tuyệt đối không dùng làm chỉ số chính** để so sánh hay kết luận năng lực mô hình, do bị chi phối hoàn toàn bởi 80% mẫu Normal.
    - **Báo cáo chẩn đoán bắt buộc:**
      - Bắt buộc công bố đầy đủ: **Per-Class Precision**, **Per-Class Recall**, **Per-Class F1** cho từng cấp độ an toàn (`Level01`–`Level04`).
      - Bắt buộc công bố **Row-Normalized Confusion Matrix (Ma trận nhầm lẫn chuẩn hóa theo hàng)** để phản ánh trực quan phân bố sai số theo từng cấp nhãn thực tế.
  - **2. Phê duyệt Chỉ số Sai số An toàn Trọng yếu (Safety-Critical Error Metrics):**
    - Phê duyệt cấu trúc đánh giá hai track độc lập, phản ánh tính phi đối xứng của rủi ro công nghiệp:
      - **TRACK A — Binary Anomaly Detection (Phát hiện bất thường nhị phân):**
        - Dương tính (Positive Class): $\text{Level01} \cup \text{Level02} \cup \text{Level03}$ ($N=1.000$ ở P2; $N=251$ ở P1).
        - Âm tính (Negative Class): $\text{Level04}$ ($N=4.013$ ở P2; $N=999$ ở P1).
        - Báo cáo:
          - **Anomaly FNR (Tỷ lệ bỏ sót nguy cơ bất thường):**
            $$\text{FNR}_{\text{anomaly}} = \frac{\sum_{i \in \mathcal{P}_{\text{anom}}} \mathbb{I}(\hat{y}_i = \text{Level04})}{N_{\text{anomaly}}} = 1 - \text{Recall}_{\text{anomaly}}$$
          - **Anomaly FPR (Tỷ lệ báo động nhầm):**
            $$\text{FPR}_{\text{anomaly}} = \frac{\sum_{i \in \mathcal{N}_{\text{anom}}} \mathbb{I}(\hat{y}_i \in \{\text{Level01, Level02, Level03}\})}{N_{\text{normal}}}$$
      - **TRACK B — Level01 One-vs-Rest (Phân loại nguy cơ nghiêm trọng cấp 1):**
        - Dương tính: $\text{Level01}$ ($N=659$ ở P2; $N=169$ ở P1).
        - Âm tính: $\text{Level02} \cup \text{Level03} \cup \text{Level04}$.
        - Báo cáo:
          - **Level01 Recall ($\text{Recall}_{\text{L01}}$)** và **Level01 FNR ($\text{FNR}_{\text{L01}} = 1 - \text{Recall}_{\text{L01}}$)**.
          - Phân rã bắt buộc: **Tỷ lệ bỏ sót hoàn toàn thành bình thường (`Critical Miss Rate`:** $\hat{y}_i = \text{Level04}$) và **Tỷ lệ hạ cấp nguy cơ (`Critical Downgrade Rate`:** $\hat{y}_i \in \{\text{Level02, Level03}\}$).
    - **Quy tắc cấm tuyệt đối:** Tuyệt đối không dùng một chỉ số "FNR" chung chung mà không ghi rõ mẫu số và định danh $\text{FNR}_{\text{anomaly}}$ hay $\text{FNR}_{\text{L01}}$.
  - **3. Phê duyệt Chính sách Miền thiếu lớp (Dual-Layer Support-Aware Policy):**
    - Nhằm xử lý trung thực hiện tượng miền `metallurgy` thiếu `Level02` và `oil_chemical` thiếu `Level03` ở P2:
      - **A. Chỉ số vĩ mô từng miền (Domain Macro Metrics):** Được phép báo cáo mô tả nhưng **bắt buộc phải ghi rõ số lớp ground truth thực tế $K_d$** (ví dụ: $\text{Macro-F1}_{(K=3)}$), kèm cảnh báo không so sánh trực tiếp với các miền có $K=4$.
      - **B. So sánh xuyên miền (Cross-Domain Comparison):** Xác lập **Class-Conditional Recall (Recall theo từng lớp)** làm mỏ neo chính.
      - **Quy tắc cấm kỵ:** Tuyệt đối không so sánh máy móc Macro-F1 hay Balanced Accuracy giữa các miền công nghiệp có label support khác nhau.
  - **4. Phê duyệt Mỏ neo Đánh giá Độ bền vững Xuyên miền (RQ1 Cross-Domain Robustness):**
    - **Primary Anchor (Mỏ neo chính):** **Class-Conditional Domain Analysis (Phân tích xuyên miền theo từng lớp)**:
      - Với mỗi lớp an toàn $c$ và miền $d$ có ground truth ($N_{c, d} > 0$):
        $$\text{Recall}(c, d) = \frac{\text{TP}_{c, d}}{N_{c, d}}$$
        $$\Delta(c, d) = \text{Recall}_{c, \text{pooled}} - \text{Recall}_{c, d}$$
      - Báo cáo đầy đủ: Per-class domain recall, Pooled-to-domain gap $\Delta(c, d)$, Per-class domain spread $\left(\max_d \text{Recall}(c, d) - \min_d \text{Recall}(c, d)\right)$, và Worst adverse gap.
    - **Secondary Diagnostics (Chẩn đoán phụ trợ):**
      - **Balanced Accuracy Domain Spread** trên tập các miền so sánh được có đủ 4 lớp ($K=4$, gồm `coal_conveyor`, `power`, `tunnel`).
      - **Binary Anomaly Recall Spread** trên các miền có dữ liệu bất thường.
    - **Chuẩn hóa thuật ngữ:** Bắt buộc dùng **"Cross-Domain Robustness Gap / Drop"**; tuyệt đối không dùng thuật ngữ "Domain Generalization Drop".
    - **Cảnh báo phương pháp luận bắt buộc:** Phân tích class-conditional chỉ giúp giảm thiểu nhiễu do tỷ lệ lớp (`reduces class-prevalence confounding`), **KHÔNG LOẠI BỎ ĐƯỢC** các yếu tố gây nhiễu về: thành phần nguy cơ (`hazard composition`), nền tảng robot tuần tra (`robot platform`), góc máy (`viewpoint`), điều kiện chiếu sáng/bối cảnh (`lighting/scene`), và các đặc trưng vật lý riêng biệt của từng phân xưởng.
  - **5. Phê duyệt Chính sách Báo cáo Miền có Hiệu năng Thấp nhất (Worst-Domain Policy):**
    - **Bãi bỏ quy tắc ngưỡng cơ học $N \ge 30$** làm tiêu chuẩn khoa học phân định quyền tham gia xếp hạng.
    - Báo cáo chính thức là: **"Observed numerical minimum among comparable domains" (Giá trị số học quan sát thấp nhất trong số các miền có thể so sánh được)**.
    - Mọi ô số liệu Worst-Domain bắt buộc phải công bố đi kèm: định nghĩa metric cụ thể, mẫu số thực tế ($k / N_d$), mức độ hỗ trợ nhãn, khoảng tin cậy bootstrap, và lưu ý về tính so sánh được (`comparability warning`).
    - Miền Luyện kim (`metallurgy`): Bắt buộc gắn nhãn **`[Sparse-Support / Descriptive-Only]`** cho toàn bộ các chỉ số bất thường ($N_{\text{anomaly}}=9$ ở P2; $N_{\text{anomaly}}=0$ ở P1). Tuyệt đối không đưa ra các tuyên bố xếp hạng mạnh (`strong ranking claims`) khi khoảng tin cậy rộng hoặc mức độ hỗ trợ nhãn khác nhau.
  - **6. Phê duyệt Hệ thống Chỉ số Phân tầng Nguy cơ RQ2 (RQ2 Grouped Hazard Strata Metrics):**
    - Đánh giá trên đúng **7 tầng nguy cơ gom nhóm ứng viên (Candidate Grouped Hazard Strata A–G)** đã khóa tại D6.
    - Đối với mỗi stratum $s \in \{\text{Strata A}, \dots, \text{Strata G}\}$ gồm $N_s$ mẫu, báo cáo bộ 4 chỉ số an toàn:
      1. **Exact Safety-Level Error Rate:** $\text{ErrorRate}_{\text{exact}}(s) = \frac{1}{N_s} \sum_{i \in \text{Strata}_s} \mathbb{I}(\hat{y}_i \neq y_i)$.
      2. **Anomaly-to-Normal Miss Rate:** $\text{MissRate}_{\text{anom}\rightarrow\text{norm}}(s) = \frac{1}{N_s} \sum_{i \in \text{Strata}_s} \mathbb{I}(\hat{y}_i = \text{Level04})$.
      3. **Level01 Recall & Critical Miss Rate:** $\text{Recall}_{\text{L01}}(s)$ và $\text{CriticalMissRate}_{\text{L01}\rightarrow\text{L04}}(s)$ áp dụng cho các stratum có chứa Level01.
      4. **Safety-Level Confusion Distribution:** Phân bố dự đoán 4 mức $\{\text{Level01}, \text{Level02}, \text{Level03}, \text{Level04}\}$ trên từng tầng.
    - **Cảnh báo phương pháp luận bắt buộc về Mẫu đa nguy cơ và Tính không cộng dồn (Non-Additive Counts):**
      - Bằng chứng kiểm toán thực chứng: Đúng **512 / 1.000 mẫu Anomaly (51,2%)** chứa $\ge 2$ hazard atoms; 7 tầng nguy cơ gom nhóm tạo ra tổng cộng **1.381 lượt thành viên (sample memberships)** trên 1.000 mẫu ảnh độc nhất.
      - Hệ quả bắt buộc:
        1. Số lượng mẫu giữa các tầng **KHÔNG CÓ TÍNH CỘNG DỒN (`counts are NOT additive`, $\sum N_s \neq 1.000$)**.
        2. Cùng một mẫu ảnh xuất hiện trong nhiều tầng nguy cơ khác nhau.
        3. Các ước lượng chỉ số giữa các tầng **hoàn toàn không độc lập về mặt thống kê (`strata estimates are not statistically independent`)**.
        4. **Tuyệt đối cấm cộng dồn số lượng lỗi hoặc tính trung bình gộp sai số giữa các tầng** để đại diện cho toàn bộ dataset (`do not sum error counts across strata`).
  - **7. Direct Grounding — Định nghĩa Tập Vùng GT Ứng viên (Candidate GT Region Set $R_j$):**
    - Đối với mỗi Direct hazard atom $j$, tập vùng GT ứng viên hỗ trợ $R_j$ được xác định tất định từ quy tắc ánh xạ D6:
      $$R_j = \left\{ r \in \text{Polygons}(\text{sample}) \mid \text{label}(r) \in \text{CandidateLabels}(j) \right\}$$
    - Kết quả kiểm toán thực chứng: **781 / 781 Direct atoms (100%)** sở hữu $|R_j| \ge 1$; gồm **680 atoms đơn vùng** ($|R_j|=1$) và **101 atoms đa vùng** ($|R_j|>1$, từ 2 đến 8 vùng GT).
    - Trọng số cạnh IoU giữa hộp bao dự đoán $p$ và GT atom $j$ là giá trị cực đại trên tập $R_j$:
      $$\text{IoU}(p, j) = \max_{r \in R_j} \text{IoU}\left(\mathbf{b}_{\text{pred}}^p, \text{bbox}(r)\right)$$
    - **Quy tắc phương pháp luận:** Mỗi hazard atom $j$ vẫn là **MỘT đơn vị đánh giá duy nhất (ONE evaluation unit)**; tuyệt đối không biến nhiều đa giác hỗ trợ thành nhiều hazard atoms giả tạo.
  - **8. Direct Grounding — Chỉ số Liên tục Chính và Độ nhạy Phân ngưỡng:**
    - **Primary Continuous Metrics (Chỉ số liên tục chính):**
      - **End-to-End Mean IoU:** Mẫu số là toàn bộ 781 Direct atoms; lỗi không nhận diện, lỗi parse tọa độ, hộp trượt đích đều gán $\text{IoU} = 0.0$.
      - **Median IoU:** Báo cáo kèm theo để kháng giá trị ngoại lai cực đoan.
    - **Threshold Sensitivity (Độ nhạy phân ngưỡng):**
      - Báo cáo tại hai ngưỡng: **Hit@0.25** và **Hit@0.50**.
      - Cả hai ngưỡng này được **xác định trước khi xem kết quả mô hình (`pre-specified before model-result inspection`)** và không thay đổi sau đó.
      - Tuyệt đối không tuyên bố ngưỡng $\text{IoU} = 0.25$ là "chuẩn phổ quát" (universal standard).
  - **9. Direct Grounding — Phân định Rạch ròi Hai Chế độ Ghép cặp (Two Matching Modes):**
    - Phê duyệt hai chế độ ghép cặp tối ưu hai phía độc lập, tách biệt hoàn toàn và **tuyệt đối không được trộn lẫn**:
      - **MODE A — Continuous IoU Assignment (Gán ghép liên tục không ngưỡng):**
        - Dành riêng cho: **End-to-End Mean IoU**, **Median IoU**, và **Parse-Conditional Mean IoU**.
        - Phạm vi: Ghép giữa các dự đoán $\{p\}$ và Direct GT atoms $\{j\}$ trong cùng mẫu ảnh và cùng loại nguy cơ.
        - Mục tiêu: Ghép tối ưu một-một cực đại hóa tổng điểm IoU: $\max \sum \text{IoU}(p, j)$.
        - **Tuyệt đối không áp dụng ngưỡng $\tau$**.
        - Mỗi hộp dự đoán chỉ được dùng tối đa 1 lần, không tái sử dụng hộp dự đoán (`no predicted box reuse`).
        - GT atom không có dự đoán ghép cặp: $\text{IoU} = 0.0$. Nguy cơ bị bỏ sót: $\text{IoU} = 0.0$. Lỗi cú pháp parse: $\text{IoU} = 0.0$ trong bài toán End-to-End.
      - **MODE B — Thresholded Bipartite Matching (Ghép hai phía có phân ngưỡng):**
        - Dành riêng cho: **Hit@0.25**, **Hit@0.50**, **Evidence P/R/F1 (@0.25, @0.50)**, và **$\text{CGI}@\tau$** ($\tau \in \{0.25, 0.50\}$).
        - Điều kiện cạnh hợp lệ: Chỉ đưa vào đồ thị các cạnh thỏa mãn $\text{IoU}(p, j) \ge \tau$.
        - Mục tiêu: (1) Tối đa hóa số lượng cặp ghép hợp lệ (Maximum Cardinality $|\mathcal{M}_\tau|$); (2) Tie-break: Tối đa hóa tổng điểm IoU giữa các phương án có cùng số cặp ghép cực đại.
        - Ràng buộc một-một nghiêm ngặt.
  - **10. Pointing Hit trên Đa giác GT Gốc (Canonical Pointing Hit):**
    - Điểm tâm của hộp bao dự đoán $\mathbf{c}_{\text{pred}}^p$ **bắt buộc phải nằm bên trong BẤT KỲ ĐA GIÁC GT GỐC NÀO** thuộc tập vùng ứng viên $R_j$:
      $$\text{PointingHit}(p, j) = \mathbb{I}\left(\exists r \in R_j \text{ sao cho } \mathbf{c}_{\text{pred}}^p \in \text{Polygon}(r)\right)$$
    - **Hộp bao derived bbox TUYỆT ĐỐI KHÔNG ĐƯỢC DÙNG cho Pointing Hit** để ngăn chặn việc tính điểm trúng đích vào vùng nền trống của các vật thể phi lồi.
  - **11. Phê duyệt Evidence Precision / Recall / F1:**
    - Đánh giá ở cấp độ **Nguy cơ Nguyên tử (`Hazard-Atom Level`)** trên Direct track ($N=781$), sử dụng thuật toán ghép cặp **Mode B**:
      $$\text{Evidence Recall}_h@\tau = \frac{\text{TP}_h@\tau}{N_{\text{evaluable\_GT\_atoms}, h}}$$
      $$\text{Evidence Precision}_h@\tau = \frac{\text{TP}_h@\tau}{\text{Total\_Predicted\_Boxes}_h}$$
      $$\text{Evidence F1}_h@\tau = \frac{2 \cdot \text{Evidence Precision}_h@\tau \cdot \text{Evidence Recall}_h@\tau}{\text{Evidence Precision}_h@\tau + \text{Evidence Recall}_h@\tau}$$
    - Báo cáo song song tại **@0.25** và **@0.50**.
    - **Bản chất bắt buộc phải ghi rõ:** Đây là **Chỉ số benchmark tương đối theo chú thích (`Annotation-Relative Benchmark Metric`)**, **KHÔNG PHẢI độ chính xác nguy cơ triệt để ngoài đời thực (`NOT real-world exhaustive hazard precision`)**. Dự đoán không khớp với nhãn GT **tuyệt đối không được tự động đồng nhất với ảo giác ngoài đời thực (`unmatched prediction != hallucination`)**.
  - **12. Đánh giá Bám bằng chứng Đại diện Yếu (RQ3-B Weak Proxy Grounding):**
    - Phê chuẩn chỉ số: **Identity-Agnostic Proxy Localization Consistency (Identity-Agnostic PLC — Mức độ nhất quán định vị đại diện không phụ thuộc danh tính)** trên 947 Weak-Proxy atoms (608 mẫu ảnh):
      - **PRIMARY:** **Center-in-Proxy**: Tọa độ tâm hộp dự đoán nằm bên trong **bất kỳ đa giác `Person` gốc nào** trong ảnh. Không khẳng định mô hình đã chọn đúng công nhân vi phạm cụ thể.
      - **DIAGNOSTIC:** **Predicted Box Containment** liên tục (tỷ lệ diện tích hộp dự đoán nằm trong đa giác người). Ngưỡng $\text{Containment} \ge 0.50$ chỉ là **ngưỡng heuristic kiểm tra độ nhạy (`sensitivity heuristic`)**, không phải chân lý khoa học.
      - **Bắt buộc phân tích độ nhạy trên Single-Person Proxy Subset:** Đánh giá đối chứng trên đúng **410 mẫu ảnh (chứa 614 proxy atoms)** chỉ có duy nhất 1 đối tượng `Person` ($|\text{Person}|=1$) để loại trừ ambiguity về danh tính người (nhưng không loại bỏ semantic proxy limitation).
    - **Quy tắc bắt buộc:** Direct Grounding và Weak Proxy Grounding **bắt buộc phải báo cáo tách biệt hoàn toàn**. Tuyệt đối không gọi PLC là "True Evidence Grounding Accuracy".
  - **13. Chuẩn hóa Chỉ số Không nhất quán Phân loại – Định vị ($\text{CGI}@\tau$):**
    - Tên gọi chính thức duy nhất: **"Classification-Grounding Inconsistency relative to available object-support annotation"**.
    - Bắt buộc tham số hóa theo ngưỡng: Báo cáo song song **$\text{CGI}@0.25$** và **$\text{CGI}@0.50$**; cấm dùng ký hiệu $\text{CGI}$ thiếu hậu tố ngưỡng.
    - Mẫu số cấp mẫu: Tập các mẫu Direct-support được phân loại đúng cấp độ an toàn.
    - Mẫu số cấp atom: Toàn bộ Direct atoms nằm trong các mẫu phân loại đúng.
    - **Quy tắc cấm kỵ:** Tuyệt đối không diễn giải chỉ số này là "suy luận sai" (`wrong reasoning`), "đoán mò" (`guessing`), hay "đúng đáp án sai lý do" (`correct answer wrong reason`).
  - **14. Chính sách Xử lý Lỗi Phân tích Cú pháp (Parse-Failure Policy):**
    - Báo cáo tường minh:
      - **Response-level Parse Success Rate ($\text{PSR}_{\text{response}}$):** Tỷ lệ phản hồi tuân thủ cú pháp.
      - **Evidence-item Box Parse Rate ($\text{PSR}_{\text{box}}$):** Tỷ lệ hộp bao có tọa độ hợp lệ trong $[0, 1]$.
    - **End-to-End Grounding:** Mọi lỗi parse phản hồi hoặc lỗi tọa độ đều được tính là thất bại hoàn toàn ($\text{IoU} = 0.0$).
    - **Diagnostic:** Báo cáo **Parse-Conditional Mean IoU** (chỉ tính trên các hộp parse thành công; hộp parse hợp lệ nhưng trượt định vị vẫn nhận $\text{IoU} = 0.0$).
  - **15. Chính sách Nguyên tử Nguy cơ Không có GT Không gian (Unsupported Atoms Policy):**
    - Đúng **60 nguyên tử nguy cơ `NO_CURRENT_SPATIAL_GT`** (34 atoms `DOOR_OPEN` và 26 atoms annotator gốc bỏ sót đa giác) trên 59 mẫu ảnh:
      - **Bị loại bỏ hoàn toàn khỏi mẫu số** của các chỉ số bám bằng chứng không gian (IoU, Hit, Evidence P/R, PLC, CGI).
      - **Vẫn giữ nguyên vẹn trong bài toán đánh giá phân loại an toàn**.
      - Bắt buộc công bố công khai số lượng 60 atoms này; **tuyệt đối không loại bỏ ngầm (no silent drop)**.
  - **16. Biến đồng biến Chẩn đoán Kích thước Đối tượng và Độ hiếm (Diagnostic Covariates):**
    - Định vị độc quyền là **phân tích chẩn đoán phụ trợ (DIAGNOSTIC ONLY)**, không làm thay đổi các bảng tổng hợp kết quả chính thức:
      - **Vô hướng kích thước Direct atom:** $\text{AtomSize}(j) = \max_{r \in R_j} \frac{\text{Area}(r)}{W \times H} \in [0, 1]$, giữ nguyên thang đo liên tục, hoàn toàn độc lập với đầu ra mô hình và đồng bộ với điểm cạnh IoU. **Tuyệt đối không chia thành các khoảng Small / Medium / Large cơ học** bằng các ngưỡng tùy ý trong giao thức W2.4.
      - **Biến số lượng vùng hỗ trợ ($|R_j|$ Covariate):** Báo cáo kèm theo như biến chẩn đoán rời rạc (phân biệt 87,07% đơn vùng và 12,93% đa vùng).
      - **Biến mức độ hiếm (Rarity Covariate):** Khảo sát tần suất xuất hiện liên tục $N$ của các loại nguy cơ. Không tạo ngưỡng rare/common tùy ý; tuyệt đối không suy diễn nhân quả "độ hiếm gây ra lỗi mô hình".
  - **17. Chính sách về Chỉ số Ảo giác Đối tượng (Object Hallucination Policy):**
    - **Không phê duyệt Tỷ lệ Ảo giác Đối tượng (Object Hallucination Rate) trên toàn bộ dataset**, do chú thích không mang tính triệt để. Cấm ngụy biện $\text{missing JSON label} = \text{object absent}$.
    - **Không mở thêm chiến dịch kiểm toán thủ công 30–50 ảnh** trong phạm vi cốt lõi của Seminar 8 tuần. Bảo lưu cho Luận văn tốt nghiệp sau này.
  - **18. Chính sách về Độ hiệu chỉnh Xác suất (Calibration Policy):**
    - Độ hiệu chỉnh xác suất (Calibration: ECE, Brier Score) là **đặc thù phụ thuộc năng lực mô hình/giao diện (`Capability-Specific`)**.
    - Tính đủ điều kiện (`Eligibility`) của từng mô hình/phiên bản sẽ được kiểm chứng thực nghiệm tại bước **W2.5**.
    - **Tuyệt đối không dùng độ tự tin tự thuật bằng văn bản (`self-reported textual confidence`)** làm xác suất hiệu chỉnh.
    - Calibration **không phải là chỉ số chính xuyên mô hình (cross-model primary metric)** của SafeShift Seminar.
  - **19. Phê chuẩn Phương pháp Ước lượng Bất định Chính thức (Domain-Stratified Point-Cluster Bootstrap):**
    - SafeShift chính thức phê duyệt **Domain-Stratified Point-Cluster Bootstrap** làm phương pháp ước lượng bất định chính thức (PRIMARY):
      - Đối với P2 toàn thể: **Phân tầng DUY NHẤT theo 5 miền thao tác `folder_domain`**. Trong mỗi miền, lấy mẫu lại có hoàn lại các cụm thư mục điểm logic `point_id` (đối với Normal) và các mẫu/cụm Anomaly của chính miền đó cho tới khi đạt đúng số cụm quan sát gốc của miền đó, sau đó gộp 5 miền lại thành một replicate toàn thể.
      - **TUYỆT ĐỐI KHÔNG PHÂN TẦNG THEO CẤP AN TOÀN (`NO STRATIFICATION BY SAFETY LEVEL`)** để tránh zero-resampling-variance artifact do ép phân tầng singleton theo safety level.
      - Đối với chỉ số từng miền: Lấy mẫu lại các cụm điểm logic trong nội bộ chính miền đó.
      - **Cấu hình chuẩn hóa:** $B = 2.000$ replicates (chính thức); $B = 5.000$ replicates (kiểm tra hội tụ); khóa `seed = 42`.
      - **Khoảng tin cậy:** 95% Percentile Bootstrap CI $\left[ q_{0,025}, \, q_{0,975} \right]$.
      - **Chính sách replicate khuyết lớp:** Nếu một replicate không rút trúng mẫu ground truth nào cho lớp đang đánh giá, metric của lượt đó ghi nhận là `NA`. Bắt buộc phải công bố: **Tỷ lệ Replicate Hợp lệ (`Valid Replicates / B`)**.
      - **Cảnh báo nhận thức luận bắt buộc:** `point_id` là mã định danh thư mục điểm logic (`logical point folder`), không phải ID trạm vật lý đã xác minh (`not verified physical site ID`); trường `source-family` tuyệt đối không được dùng làm cụm bootstrap chính thức.
  - **20. Phê chuẩn Phương pháp So sánh Đa Mô hình (Paired Bootstrap Difference CI 95%):**
    - Phương pháp so sánh chính thức duy nhất giữa hai mô hình: **Paired Bootstrap Difference CI 95% (Khoảng tin cậy hiệu số bootstrap theo cặp 95%)**.
    - Hai mô hình A và B **bắt buộc phải được đánh giá trên CÙNG MỘT TẬP CÁC LƯỢT DRAW REPLICATE BOOTSTRAP**: $\Delta M^{(b)} = M_A^{(b)} - M_B^{(b)}$.
    - Nếu một replicate có giá trị undefined ở bất kỳ mô hình nào, $\Delta M^{(b)}$ nhận giá trị `NA`. Bắt buộc công bố: **Tỷ lệ Replicate theo cặp Hợp lệ (`Valid Paired Replicates / B`)**.
    - **Chuẩn hóa phát biểu khoa học bắt buộc:**
      - Nếu CI 95% không chứa giá trị 0: Chỉ được kết luận là **"Chênh lệch có hướng rõ ràng dưới giao thức lấy mẫu lại đã xác định trước (`directionally clear difference under pre-specified resampling protocol`)"**. Tuyệt đối không tự động tuyên bố "có ý nghĩa thống kê ở mức $\alpha = 0,05$".
      - Nếu CI 95% chứa giá trị 0: **TUYỆT ĐỐI KHÔNG KẾT LUẬN HAI MÔ HÌNH TƯƠNG ĐƯƠNG NHAU**. Chỉ kết luận dữ liệu chưa thể hiện sự phân hóa rõ ràng.
      - **Không chạy mặc định ma trận $p$-value dày đặc giữa mọi cặp mô hình** để tránh hiện tượng săn lùng $p$-value (`p-value hunting`).
  - **21. Áp dụng trên Phân tầng Giao thức P1 / P2 / P3:**
    - **P1 — Baseline Replication Protocol (1.250 mẫu test chính thức):** Áp dụng Safety Accuracy, BGE-M3 Similarity, và Grounding extension. Do miền `metallurgy` ở P1 có đúng 0 mẫu Anomaly, mọi chỉ số Anomaly Recall và Anomaly FNR của `metallurgy` là **UNDEFINED (Không xác định)**. Tuyệt đối không tự ý gán undefined thành 0% hay 100%.
    - **P2 — Primary Research Protocol (5.013 mẫu toàn thể):** Áp dụng đầy đủ toàn bộ hệ thống chỉ số đã phê chuẩn.
    - **P3 — Sensitivity Protocol Candidate (1.248 và 1.241 mẫu):** Giữ nguyên vẹn toàn bộ định nghĩa công thức toán học của P1 khi có thể áp dụng; tuyệt đối không gọi P3 là "clean benchmark" hay "leakage-free benchmark".
  - **22. Phân tích Độ nhạy với 36 Mẫu Xung đột Nhãn Miền (Domain-Mismatch Sensitivity):**
    - Phân tích chính thức thực hiện theo `folder_domain`.
    - Phân tích độ nhạy bắt buộc: Sensitivity A (loại bỏ 36 mẫu khỏi phân tích từng miền) và Sensitivity B (tái phân bổ 36 mẫu theo `text_domain`).
    - **Công thức toán học của mọi chỉ số KHÔNG THAY ĐỔI**, sự thay đổi duy nhất là phép gán miền cho 36 mẫu ảnh.
  - **23. Hồ sơ Nguồn gốc và Kiểm toán Thực chứng (Provenance & Audit Trail):**
    - Quyết định D5 căn cứ trên [notes/w2_metrics_statistics_decision_brief.md](notes/w2_metrics_statistics_decision_brief.md).
    - Bộ dữ liệu kiểm chứng mang dấu vân tay SHA-256: `7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`.
    - Kết quả tổng điều tra D6: `data/manifests/w2_grounding_census.json` (SHA-256: `cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`).
    - Lệnh kiểm toán vùng GT và phân tầng nguy cơ: `python scratch/audit_gt_regions.py` (Script SHA-256: `90c704af291fb34725b6a679f3bdb2a84d18297628c569497e34309ed49cee50`, thực thi trên Python 3.11.9 lúc `2026-09-17 05:22:14 UTC`). Script là local scratch script, không commit vào repo và không tuyên bố tái lập chỉ bằng Git repo đơn lẻ.
  - **24. Những Nội dung Kỹ thuật D5 KHÔNG Chốt (Deferred Items chuyển sang W2.5):**
    - Quyết định D5 **tuyệt đối KHÔNG chốt**:
      - Danh sách các mô hình cụ thể tham gia thử nghiệm (`final model list`).
      - Câu chữ chi tiết của prompt chỉ dẫn (`final prompt wording`).
      - Tính đủ điều kiện về mặt năng lực của từng mô hình / API (`capability eligibility`).
      - Giao diện và wrapper cụ thể cho từng mô hình VLM.
      - Chi tiết triển khai mã nguồn của các baseline.
    - Toàn bộ các nội dung này thuộc thẩm quyền giải quyết độc quyền của bước **W2.5**.
- **Lý do:**
  1. Balanced Accuracy và Macro-F1 giảm ảnh hưởng của mất cân bằng nhãn và cung cấp hai góc nhìn bổ sung: recall theo lớp và cân bằng precision/recall.
  2. Phân lập Track A (Binary Anomaly) và Track B (Level01 OvR) phản ánh trung thực bản chất phi đối xứng của rủi ro công nghiệp, bảo vệ các sự cố đe dọa tính mạng không bị chìm lấp trong các chỉ số gộp.
  3. Chính sách hai tầng và Class-Conditional Domain Analysis cung cấp một mỏ neo so sánh khách quan, ngăn chặn ngụy biện so sánh các phân xưởng có mức độ hỗ trợ nhãn khác nhau.
  4. Phân định khắt khe hai chế độ ghép cặp Mode A (đo lường hàm liên tục không ngưỡng) và Mode B (phân định quyết định nhị phân có ngưỡng) bảo đảm tính nhất quán toán học giữa metric liên tục và metric có ngưỡng của bài toán bám bằng chứng trực tiếp.
  5. Identity-Agnostic PLC giảm ảnh hưởng của ambiguity về danh tính người, nhưng không biến Person polygon thành true hazard rationale GT; đồng thời Single-Person Proxy Subset chỉ loại identity ambiguity, không loại semantic proxy limitation.
  6. Domain-Stratified Point-Cluster Bootstrap xử lý known within-point dependence (phụ thuộc đã biết trong cùng point_id) của các frame liên quan mà không gây zero-resampling-variance artifact do ép phân tầng singleton theo safety level; đồng thời ghi nhận rõ: không chứng minh between-point independence, anomaly dependence vẫn chưa được giải quyết hoàn toàn, và source-family không phải true video ID.
  7. Paired Bootstrap Difference CI tập trung vào hướng và độ lớn hiệu ứng thực chất giữa các mô hình trên cùng một tập replicate, ngăn chặn thói quen suy diễn quá mức từ ma trận $p$-value dày đặc.
- **Ảnh hưởng tới dataset, split, metric và reproducibility:**
  - **Dataset:** Giữ nguyên dữ liệu thô và các tệp JSON/TXT gốc; không chỉnh sửa bất kỳ nhãn hay tọa độ không gian nào.
  - **Split:** P1 giữ nguyên 1.250 mẫu test; P2 sử dụng 5.013 mẫu toàn thể và bảo lưu metadata `split: train/test`; 36 mẫu mismatch được kiểm tra độ nhạy theo Sensitivity A và B.
  - **Metrics:** Xác lập và đóng băng chính thức toàn bộ công thức toán học cho phân loại 4 lớp, sai số an toàn trọng yếu, suy giảm xuyên miền RQ1, phân tầng nguy cơ RQ2, bám bằng chứng trực tiếp RQ3-A (Mode A và Mode B), đại diện yếu RQ3-B (PLC), chỉ số $\text{CGI}@\tau$, tỷ lệ parse PSR, và loại trừ 60 unsupported atoms khỏi mẫu số không gian.
  - **Reproducibility:** Mọi thuật toán ghép cặp và quy trình bootstrap được đặc tả tất định; khóa `seed = 42`; toàn bộ chuỗi phản hồi thô nguyên văn (`Raw Model Response`) bắt buộc phải lưu trữ kèm metadata đầy đủ trước khi phân tích cú pháp; các artifact kiểm toán có mã băm SHA-256 xác minh tính toàn vẹn.
- **Người chấp thuận và thời điểm:** Project Owner / Research Lead (Chủ dự án / Người phụ trách nghiên cứu), ngày 2026-09-17.
- **Task/thí nghiệm liên quan:**
  - [notes/w2_metrics_statistics_decision_brief.md](notes/w2_metrics_statistics_decision_brief.md) (W2.4 Decision Brief, branch protocol/w2-metrics-statistics, commit a0118b44b674146e3588d4f0616ecdbe52eff089)
  - [notes/w2_grounding_census_decision_brief.md](notes/w2_grounding_census_decision_brief.md) (W2.3 Decision Brief)
  - [notes/w2_domain_split_decision_brief.md](notes/w2_domain_split_decision_brief.md) (W2.2 Decision Brief)
  - [notes/w2_protocol_decision_brief.md](notes/w2_protocol_decision_brief.md) (W2.1 Decision Brief)
  - Quyết định nền tảng [DEC-W2-D1-001](#dec-w2-d1-001), [DEC-W2-D2-002](#dec-w2-d2-002), [DEC-W2-D3-003](#dec-w2-d3-003), [DEC-W2-D4-004](#dec-w2-d4-004), [DEC-W2-D6-006](#dec-w2-d6-006), [DEC-W2-D7-007](#dec-w2-d7-007).
  - Định hướng trực tiếp cho khảo sát năng lực mô hình tại W2.5 và triển khai bộ đánh giá baseline tại W3.
- **Đính chính và làm rõ thứ bậc phân tầng RQ2 (RQ2 Hierarchy Clarification / Erratum - Approved: 2026-09-18):**
  - **Phê duyệt chính thức:** Project Owner / Research Lead đã phê duyệt chính thức vào ngày 2026-09-18 với tuyên bố nguyên văn: *"Tôi phê duyệt RQ2 hierarchy clarification: 12 hazard atoms là PRIMARY RQ2 strata, còn 7 grouped A–G categories chỉ là SECONDARY EXPLORATORY summaries."* (Căn cứ chi tiết tại [notes/w2_rq2_hierarchy_erratum_brief.md](notes/w2_rq2_hierarchy_erratum_brief.md)).
  - **A. Áp dụng Bộ 4 Chỉ số An toàn cho 12 Primary Atomic Hazard Strata:**
    - Bộ 4 chỉ số an toàn đã phê duyệt tại Mục 6 ở trên được áp dụng **CHÍNH YẾU (PRIMARY)** cho từng phân tầng trong **12 atomic hazard strata**:
      1. **Exact Safety-Level Error Rate** trên từng atom.
      2. **Anomaly-to-Normal Miss Rate** trên từng atom.
      3. **Level01 Recall / Critical Miss Rate** trên các atom có hỗ trợ mẫu Level01 ($N_{a, \text{L01}} > 0$). (Nếu atom không có mẫu Level01, bắt buộc ghi nhận `NA`, tuyệt đối không gán 0.0 hay 1.0; không tự ý đặt ngưỡng cắt tối thiểu $N$).
      4. **Safety-Level Confusion Distribution** trên từng atom.
    - Với mỗi atom, bắt buộc công bố: cỡ mẫu hỗ trợ ảnh độc nhất $N_a$, phân rã theo cấp an toàn ($N_{a, \text{L01}}$, $N_{a, \text{L02}}$, $N_{a, \text{L03}}$), độ bất định/khoảng tin cậy Bootstrap 95%, và gắn nhãn cảnh báo mẫu thưa `[Sparse-Support / Descriptive-Only]` cho các atom hiếm (`PERSON_FALLEN`: $N_a=10$, `DOOR_OPEN`: $N_a=34$).
    - Bảng kiểm kê mẫu số thực chứng đã xác minh từ W2.3 Census:
      + `NO_GLOVES`: $N_a = 453$ (L01: 303, L02: 147, L03: 3)
      + `NO_HELMET`: $N_a = 229$ (L01: 126, L02: 103, L03: 0)
      + `NO_MASK`: $N_a = 200$ (L01: 109, L02: 84, L03: 7)
      + `USE_MOBILE_PHONE`: $N_a = 167$ (L01: 96, L02: 71, L03: 0)
      + `LIQUID_ON_GROUND`: $N_a = 134$ (L01: 73, L02: 55, L03: 6)
      + `SMOKING`: $N_a = 120$ (L01: 120, L02: 0, L03: 0)
      + `OPEN_FLAME`: $N_a = 117$ (L01: 117, L02: 0, L03: 0)
      + `FOREIGN_OBJECT`: $N_a = 115$ (L01: 40, L02: 75, L03: 0)
      + `SMOKE`: $N_a = 108$ (L01: 108, L02: 0, L03: 0)
      + `NONMOTORIZED_VEHICLE`: $N_a = 101$ (L01: 101, L02: 0, L03: 0)
      + `DOOR_OPEN`: $N_a = 34$ (L01: 8, L02: 26, L03: 0)
      + `PERSON_FALLEN`: $N_a = 10$ (L01: 10, L02: 0, L03: 0)
      + *Tổng lượt thành viên:* **Tổng lượt thành viên theo nguy cơ nguyên tử trên ảnh = 1.788 (`Sum of per-atom image memberships = 1788`)** phân bố trên đúng **1.000 mẫu ảnh Anomaly độc nhất (`Unique anomaly images = 1000`)**. (Với mọi atom, đã thẩm định từ census: `atom_count == unique_sample_count = N_a`).
  - **B. Báo cáo 7 Nhóm Gom A–G là SECONDARY EXPLORATORY ANALYSIS:**
    - Bộ 4 chỉ số trên cũng có thể được báo cáo trên 7 nhóm gom A–G, nhưng **chỉ với vai trò là phân tích tóm tắt khám phá phụ trợ (`Secondary Exploratory Analysis`)**.
  - **C. Duy trì tường minh Đơn vị Dự đoán là ẢNH (Image-level Prediction Unit):**
    - Đơn vị dự đoán duy nhất vẫn là **ẢNH (`Image`)** theo đúng [DEC-W2-D2-002](#dec-w2-d2-002). Một bức ảnh cho ra một dự đoán an toàn duy nhất.
    - Nếu một ảnh chứa nhiều nguy cơ nguyên tử, dự đoán an toàn của ảnh đó sẽ đóng góp đồng thời vào nhiều phân tầng nguy cơ nguyên tử RQ2.
    - Do đó: các ước lượng theo phân tầng atom có sự phụ thuộc thống kê (`statistically dependent`), số lượng mẫu/lỗi giữa các atom **KHÔNG CÓ TÍNH CỘNG DỒN (`counts/errors across atoms are NOT additive`)**, và tuyệt đối không đưa ra kết luận nhân quả từ kết quả phân loại RQ2 đơn độc nếu không kết hợp với phân tích Grounding RQ3. Tuyệt đối không định nghĩa lại đơn vị dự đoán thành hazard atom.
- **Thay thế quyết định:** Không (Bổ sung làm rõ thứ bậc phân tầng RQ2 ngày 2026-09-18).

## DEC-W2-D6-006 — Hazard Taxonomy and Grounding Support Census

- **ID:** DEC-W2-D6-006
- **Ngày:** 2026-09-17
- **Trạng thái:** ĐƯỢC CHẤP THUẬN
- **Vấn đề cần quyết định:**
  - Phê duyệt Hệ phân loại nguy cơ thao tác nghiên cứu (Operational Research Hazard Taxonomy) gồm 12 nguy cơ nguyên tử (Hazard Atoms) bao phủ trọn vẹn 1.000 mẫu Bất thường (Anomaly) của bộ dữ liệu InspecSafe-V1.
  - Phê chuẩn định nghĩa ba trạng thái hỗ trợ không gian của chú thích đối tượng đối với mệnh đề nguy cơ: `DIRECT_OBJECT_SUPPORT`, `WEAK_PROXY_SUPPORT` và `NO_CURRENT_SPATIAL_GT`.
  - Phê chuẩn kết quả cuộc tổng điều tra thực chứng (Full Census) trên 100% mẫu Anomaly ở cả cấp độ Mẫu (`Sample-level`) và cấp độ Nguy cơ Nguyên tử (`Hazard-atom level`), cùng quy mô các tập con đánh giá (Direct-Support Pool, Weak-Proxy Pool, Unsupported Only) và ranh giới giao thoa tập hợp.
  - Thiết lập cấu trúc câu hỏi nghiên cứu RQ3: phân rã độc lập thành RQ3-A (Direct Object-Support Grounding) và RQ3-B (Weak Proxy Grounding) kèm chuẩn hóa thuật ngữ khoa học.
  - Phê chuẩn 7 phân tầng nguy cơ gom nhóm ứng viên (Candidate Grouped Hazard Strata) cho câu hỏi nghiên cứu RQ2 cùng các cảnh báo về yếu tố gây nhiễu.
- **Bối cảnh và bằng chứng:**
  - Kế thừa khung câu hỏi nghiên cứu RQ1, RQ2, RQ3 tại [DEC-W2-D1-001](#dec-w2-d1-001), chính sách đánh giá P2 trên 5.013 mẫu tại [DEC-W2-D2-002](#dec-w2-d2-002), và chính sách nhãn miền tại [DEC-W2-D3-003](#dec-w2-d3-003).
  - Báo cáo tổng điều tra thực chứng phương pháp luận độc lập tại [notes/w2_grounding_census_decision_brief.md](notes/w2_grounding_census_decision_brief.md) (Mục 4–12, 19).
  - Dữ liệu InspecSafe-V1 gồm 1.000 mẫu Anomaly (749 train, 251 test; 659 Level01, 326 Level02, 15 Level03). Toàn bộ dữ liệu có 37.434 đa giác đối tượng phân vùng, hoàn toàn không có bounding box nguy cơ hay rationale annotations ([notes/w1_dataset_audit.md](notes/w1_dataset_audit.md), [notes/dataset_schema.md](notes/dataset_schema.md), [notes/research_feasibility_audit.md](notes/research_feasibility_audit.md)).
  - Cuộc điều tra W2.3 được thực hiện trên tập con xác định tất định gồm 1.000 mẫu Anomaly từ bộ dữ liệu có dấu vân tay mật mã SHA-256 đã xác minh `7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`; script điều tra `scratch/full_census_engine.py` (SHA-256: `348860eabbe06c7908b3f4b198804033b3bd61917da4dbf8d6ec06e9cc4b5c03`); artifact kết quả chi tiết cấp mẫu `data/manifests/w2_grounding_census.json` (SHA-256: `cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`).
  - Toàn bộ 1.000 mẫu Anomaly khớp 100% mệnh đề mở đầu ngữ cảnh chuẩn mực; bóc tách được 100% mệnh đề nguy cơ; số lượng mệnh đề nguy cơ không ánh xạ được (`Hazard-clause unmapped count`) là đúng **0 mệnh đề**; số lượng trường hợp ánh xạ mơ hồ (`Support-mapping ambiguous count`) là đúng **0 trường hợp** theo các quy tắc ánh xạ tất định hiện tại.
- **Các phương án:**
  - *Phương án 1 — Gán nhãn đơn lẻ cấp Mẫu (Sample-level Single Label):* Ép mỗi mẫu ảnh vào một danh mục nguy cơ duy nhất. Thất bại trước thực tế công nghiệp khi 51,2% mẫu Anomaly chứa từ 2 đến 5 nguy cơ đồng thời (đa nguy cơ / multi-hazard).
  - *Phương án 2 — Đánh đồng Đa giác Đối tượng với Vùng Lý do Con người (Object GT = Human Rationale GT):* Coi đa giác vật thể có sẵn là ground truth lý do con người. Sai lệch nghiêm trọng về phương pháp luận vì đa giác đối tượng không mã hóa hành vi, trạng thái hay quan hệ vi phạm.
  - *Phương án 3 — Phân tầng Nguy cơ Nguyên tử hai cấp độ kết hợp bóc tách trạng thái hỗ trợ (Được chọn):* Phân biệt rạch ròi cấp Mẫu ($N=1.000$) và cấp Nguy cơ Nguyên tử ($N=1.788$); phê chuẩn 12 Hazard Atoms; xác lập 3 trạng thái hỗ trợ; phân rã độc lập RQ3-A và RQ3-B; thiết lập 7 strata phân tích cho RQ2.
- **Quyết định:**
  - **1. Phê duyệt Hệ phân loại 12 Nguy cơ Nguyên tử (Hazard Atom Taxonomy):**
    - Phê duyệt danh mục đúng **12 Hazard Atoms** đã census trên 1.000 Anomaly, giải thích trọn vẹn toàn bộ 1.000 mẫu Anomaly của bộ dữ liệu InspecSafe-V1:
      1. `NO_GLOVES` (Công nhân không mang găng tay bảo hộ lao động): **453 atoms**
      2. `NO_HELMET` (Công nhân không đội mũ bảo hộ lao động): **229 atoms**
      3. `NO_MASK` (Công nhân không đeo khẩu trang bảo hộ): **200 atoms**
      4. `USE_MOBILE_PHONE` (Công nhân sử dụng điện thoại di động / gọi điện thoại): **167 atoms**
      5. `LIQUID_ON_GROUND` (Chất lỏng đọng bất thường, nước đọng, rò rỉ dầu trên sàn/thiết bị): **134 atoms**
      6. `SMOKING` (Công nhân hút thuốc lá trong phân xưởng): **120 atoms**
      7. `OPEN_FLAME` (Ngọn lửa trần nguy hiểm trong môi trường công nghiệp): **117 atoms**
      8. `FOREIGN_OBJECT` (Dị vật / rác thải bất thường trên băng chuyền than, sàn hầm, thiết bị): **115 atoms**
      9. `SMOKE` (Khói bất thường bốc lên từ thiết bị hoặc môi trường): **108 atoms**
      10. `NONMOTORIZED_VEHICLE` (Xe thô sơ / xe đạp / xe điện / xe ba bánh lấn vào làn đường xe cơ giới): **101 atoms**
      11. `DOOR_OPEN` (Cửa tủ điện phân phối / tủ điều khiển bị mở bất thường): **34 atoms**
      12. `PERSON_FALLEN` (Công nhân ngã gục / nằm bất động trên mặt sàn): **10 atoms**
    - **Tổng số lượng:** Đúng **1.788 hazard atoms** trên **1.000 Anomaly samples** (trung bình 1,79 atoms/mẫu; phân bố: 488 mẫu có 1 atom, 287 mẫu có 2 atoms, 181 mẫu có 3 atoms, 37 mẫu có 4 atoms, 7 mẫu có 5 atoms).
    - **Mệnh đề nguy cơ chưa ánh xạ (`Unmapped hazard clause`):** Đúng **0 mệnh đề** theo quy tắc ánh xạ tất định (`deterministic mapping rules`) hiện tại.
    - **Bản chất bắt buộc phải ghi rõ:** Hệ phân loại này là **Hệ phân loại nghiên cứu thao tác (`operational research taxonomy`)** được xây dựng và kiểm chứng thực nghiệm từ dữ liệu InspecSafe-V1, **KHÔNG PHẢI là hệ phân loại an toàn công nghiệp phổ quát (`universal industrial-safety taxonomy`)**.
  - **2. Phê chuẩn Ba trạng thái hỗ trợ không gian (Support Status Definitions):**
    - **A. `DIRECT_OBJECT_SUPPORT` (Hỗ trợ đối tượng trực tiếp):**
      - Định nghĩa: Có chú thích không gian (spatial annotation) của đối tượng/thực thể (object/entity) trực tiếp hỗ trợ cho khẳng định nguy cơ (hazard claim).
      - *Quy tắc chuẩn hóa bắt buộc:* `DIRECT_OBJECT_SUPPORT` **TUYỆT ĐỐI KHÔNG ĐỒNG NGHĨA VỚI**:
        - Mệnh đề nguy cơ đầy đủ đã được chứng minh (`full hazard proposition proven`).
        - Nhãn chuẩn về lý do của con người (`human rationale ground truth`).
        - Bám lý do nguy cơ đầy đủ (`full hazard rationale grounding`).
        - *(Ví dụ: Đa giác `Cigarette` khoanh điếu thuốc không chứng minh hành vi đang hút; đa giác `Bicycle` khoanh chiếc xe nhưng hoàn toàn không mã hóa mối quan hệ vi phạm làn đường cơ giới).*
    - **B. `WEAK_PROXY_SUPPORT` (Hỗ trợ đại diện yếu):**
      - Định nghĩa: Không có chú thích không gian trực tiếp cho khẳng định nguy cơ (hazard claim), nhưng có vùng đại diện yếu, chủ yếu là đối tượng `Person` (khoanh toàn thân người cho vi phạm thiếu găng tay, thiếu mũ, thiếu khẩu trang, người ngã, hoặc xe thô sơ chỉ có người lái).
    - **C. `NO_CURRENT_SPATIAL_GT` (Hiện chưa có GT không gian):**
      - Định nghĩa: Hiện hoàn toàn không có chú thích không gian phù hợp để đánh giá hazard atom đó (toàn bộ 34 atoms `DOOR_OPEN` do không có nhãn cánh cửa tủ mở; cùng 26 atoms annotator gốc bỏ sót không vẽ đa giác chất lỏng, khói, dị vật, người).
  - **3. Số liệu kiểm kê chính xác và Đẳng thức Toàn vẹn (Sanity Identity):**
    - **Cấp độ Nguy cơ Nguyên tử (Hazard-Atom Level, tổng = 1.788 atoms):**
      - Direct atoms: **781 atoms** (43,7%)
      - Weak-Proxy atoms: **947 atoms** (53,0%)
      - No-current-spatial-GT atoms: **60 atoms** (3,4%)
      - Đẳng thức rời rạc: $781 + 947 + 60 = \mathbf{1.788\text{ atoms}}$.
    - **Cấp độ Mẫu ảnh (Sample Categories, tổng = 1.000 Anomaly samples):**
      - `ALL_DIRECT` (100% atom trong mẫu là Direct): **367 mẫu** (36,7%)
      - `MIXED_DIRECT_PROXY` (Chứa cả Direct và Proxy, không có Unsupported): **323 mẫu** (32,3%)
      - `PROXY_ONLY` (100% atom trong mẫu là Proxy): **251 mẫu** (25,1%)
      - `HAS_UNSUPPORTED` (Chứa $\ge 1$ Unsupported atom): **59 mẫu** (5,9%) (gồm 24 mẫu Direct+Proxy+Unsupported, 7 mẫu Direct+Unsupported, 10 mẫu Proxy+Unsupported, 18 mẫu Unsupported Only).
      - Đẳng thức tổng thể: $367 + 323 + 251 + 59 = \mathbf{1.000\text{ mẫu}}$.
    - **Tập mẫu Đánh giá Ứng viên (Evaluation Pools) và Phần Giao thoa:**
      - **Direct-Support Sample Pool ($\ge 1$ Direct atom):** Đúng **721 mẫu** (367 `ALL_DIRECT` + 323 `MIXED_DIRECT_PROXY` + 31 mẫu có direct atom trong `HAS_UNSUPPORTED`).
      - **Weak-Proxy Sample Pool ($\ge 1$ Weak-Proxy atom):** Đúng **608 mẫu** (251 `PROXY_ONLY` + 323 `MIXED_DIRECT_PROXY` + 34 mẫu có proxy atom trong `HAS_UNSUPPORTED`).
      - **Phần Giao thoa (Intersection):** Đúng **347 mẫu** ($323 + 24 = 347$ mẫu thuộc đồng thời cả hai pool).
      - **Unsupported Only (Không có Direct, không có Proxy):** Đúng **18 mẫu** (1,8%).
    - **Cảnh báo tính cộng gộp và Đẳng thức toàn vẹn (Sanity Identity):**
      - Bắt buộc ghi rõ: **721 mẫu và 608 mẫu KHÔNG PHẢI là hai tập rời nhau!** Có chính xác **347 mẫu** nằm trong cả hai tập.
      - **TUYỆT ĐỐI KHÔNG ĐƯỢC CỘNG CƠ HỌC $721 + 608$** để suy ra tổng số mẫu ảnh.
      - Đẳng thức kiểm tra toàn vẹn bắt buộc bảo toàn:
        $$\text{Pool}_{\text{Direct}} \cup \text{Pool}_{\text{Proxy}} = 721 + 608 - 347 = \mathbf{982\text{ mẫu có GT đánh giá được}}$$
        $$982 + 18 (\text{Unsupported Only}) = \mathbf{1.000\text{ mẫu Anomaly}}$$
  - **4. Phê chuẩn Cấu trúc Đánh giá Câu hỏi Nghiên cứu RQ3:**
    - Phê duyệt tách câu hỏi nghiên cứu RQ3 thành hai track đánh giá độc lập:
      - **RQ3-A: Direct Object-Support Grounding (Bám bằng chứng đối tượng trực tiếp):** Đánh giá trên tập con có hỗ trợ thực thể trực tiếp (367 mẫu `ALL_DIRECT` hoặc 721 mẫu `Direct-Support Sample Pool` phân rã theo 781 Direct atoms).
      - **RQ3-B: Weak Proxy Grounding (Bám bằng chứng đại diện yếu):** Đánh giá trên tập con chỉ có hỗ trợ đại diện (251 mẫu `PROXY_ONLY` hoặc 608 mẫu `Weak-Proxy Sample Pool` phân rã theo 947 Weak-Proxy atoms qua `Person`).
    - **Nguyên tắc báo cáo bắt buộc:** Hai nhóm này **bắt buộc phải báo cáo riêng**, không gộp thành một điểm số duy nhất (`single pooled score`) mà không phân biệt rõ ràng.
    - **Full Hazard Rationale Grounding (Bám lý do nguy cơ đầy đủ):** Vẫn tiếp tục được xác định là **NOT CURRENTLY FEASIBLE** (hiện không khả thi) nếu không có chú thích vùng lý do (rationale annotation) mới.
    - **Chuẩn hóa thuật ngữ khoa học:** Khi mô hình phân loại an toàn đúng nhưng trượt bounding box (`Correct classification + grounding miss`), **TUYỆT ĐỐI KHÔNG TỰ ĐỘNG ĐƯỢC GỌI LÀ "Correct Answer, Wrong Reason"** (Đúng đáp án nhưng sai lý do). Hiện tượng này chỉ được phép gọi chính xác là:
      **"Classification-Grounding Inconsistency relative to available object-support annotation"** (Sự không nhất quán giữa phân loại và bám bằng chứng đối với chú thích hỗ trợ đối tượng hiện có).
  - **5. Phê duyệt 7 Candidate Grouped Hazard Strata cho RQ2:**
    - Phê chuẩn 7 tầng nguy cơ gom nhóm ứng viên (`Candidate Grouped Hazard Strata`) phục vụ phân tích tập trung lỗi của RQ2:
      - **A. `FIRE_AND_SMOKE`:** `OPEN_FLAME` + `SMOKE` (200 mẫu, 225 atoms; 100% Level01; 97,8% Direct).
      - **B. `PPE_ABSENCE`:** `NO_GLOVES` + `NO_HELMET` + `NO_MASK` (545 mẫu, 882 atoms; 99,7% Weak-Proxy).
      - **C. `UNAUTHORIZED_BEHAVIOR`:** `USE_MOBILE_PHONE` + `SMOKING` (247 mẫu, 287 atoms; 98,6% Direct).
      - **D. `ENVIRONMENTAL_SLIP_HAZARD`:** `LIQUID_ON_GROUND` (134 mẫu, 134 atoms; 91,0% Direct).
      - **E. `OBSTRUCTION_AND_FOREIGN_OBJECT`:** `FOREIGN_OBJECT` + `NONMOTORIZED_VEHICLE` (211 mẫu, 216 atoms; 72,2% Direct, 25,0% Proxy).
      - **F. `EQUIPMENT_STATE_ANOMALY`:** `DOOR_OPEN` (34 mẫu, 34 atoms; 100% No-Current-Spatial-GT).
      - **G. `PERSONNEL_FALLEN`:** `PERSON_FALLEN` (10 mẫu, 10 atoms; 100% Level01; 100% Weak-Proxy).
    - **Quy tắc bắt buộc phải ghi rõ:**
      - Đây là các **tầng phân tích gom nhóm (`grouped analytical strata`)**, **KHÔNG PHẢI là hệ phân loại chân lý tuyệt đối (`ground-truth taxonomy`)**.
      - Số lượng mẫu giữa các tầng **KHÔNG CÓ TÍNH CỘNG GỘP (`sample counts across strata are NOT additive`)**, do các mẫu đa nguy cơ có thể đồng thời thuộc về nhiều tầng khác nhau.
    - **Các cảnh báo về yếu tố gây nhiễu và hạn chế phương pháp luận:**
      - `LIQUID_ON_GROUND`: Bị nhiễu miền nghiêm trọng (`domain confounding`), 94,0% atom tập trung tại `oil_chemical`.
      - `NONMOTORIZED_VEHICLE`: Tập trung 100% tại hầm (`tunnel`).
      - `DOOR_OPEN`: 100% không có ground truth không gian, chỉ phù hợp đánh giá phân loại, loại khỏi grounding.
      - `PERSONNEL_FALLEN`: Cỡ mẫu rất nhỏ ($N=10$), thiếu lực thống kê, không khuyến nghị phân tích độc lập.
      - Miền Luyện kim (`metallurgy`): Cực kỳ thiếu dữ liệu bất thường (toàn miền chỉ có 9 mẫu Anomaly / 25 atoms).
- **Lý do:**
  1. Cuộc tổng điều tra 100% trên 1.000 mẫu loại bỏ hoàn toàn nguy cơ sai số do ngoại suy từ tập thẩm định pilot 63 mẫu ở Tuần 1.
  2. Việc bóc tách rạch ròi cấp Mẫu ($N=1.000$) và cấp Nguy cơ Nguyên tử ($N=1.788$) giải quyết trọn vẹn hiện tượng đa nguy cơ phức tạp trong sản xuất công nghiệp.
  3. Phân định khắt khe giữa Direct Object-Support và Weak Proxy bảo vệ tính trung thực khoa học, ngăn chặn việc ngộ nhận đa giác toàn thân người là vùng chứng minh vi phạm an toàn.
  4. Đẳng thức kiểm tra toàn vẹn ($721 + 608 - 347 = 982$; $982 + 18 = 1.000$) thiết lập sự minh bạch tuyệt đối về tập hợp dữ liệu thực nghiệm.
- **Ảnh hưởng tới dataset, split, metric và reproducibility:**
  - **Dataset:** Giữ nguyên dữ liệu thô và các tệp JSON/TXT gốc; không sửa nhãn hay annotations.
  - **Split:** Bảo lưu phân chia train/test và 5 miền; không tạo split mới.
  - **Metrics:** Quyết định D6 chưa chốt các công thức metric hay ngưỡng IoU (chuyển sang W2.4).
  - **Reproducibility:** Dữ liệu điều tra có mã băm SHA-256 xác minh đầy đủ; toàn bộ logic phân loại và ánh xạ nhãn được lưu trữ trong script và artifact kiểm kê có mã kiểm tra tính toàn vẹn.
- **Người chấp thuận và thời điểm:** Project Owner / Research Lead (Chủ dự án / Người phụ trách nghiên cứu), ngày 2026-09-17.
- **Task/thí nghiệm liên quan:**
  - [notes/w2_grounding_census_decision_brief.md](notes/w2_grounding_census_decision_brief.md) (W2.3 Decision Brief, Mục 4–12, 19)
  - [notes/w1_dataset_audit.md](notes/w1_dataset_audit.md), [notes/dataset_schema.md](notes/dataset_schema.md), [notes/research_feasibility_audit.md](notes/research_feasibility_audit.md)
  - [notes/distribution_imbalance_audit.md](notes/distribution_imbalance_audit.md)
  - Quyết định nền tảng [DEC-W2-D1-001](#dec-w2-d1-001), [DEC-W2-D2-002](#dec-w2-d2-002), [DEC-W2-D3-003](#dec-w2-d3-003)
  - Định hướng trực tiếp cho định nghĩa metric tại W2.4, khảo sát mô hình tại W2.5 và thực thi baseline tại W3.
- **Đính chính và làm rõ thứ bậc phân tầng RQ2 (RQ2 Hierarchy Clarification / Erratum - Approved: 2026-09-18):**
  - **Phê duyệt chính thức:** Project Owner / Research Lead đã phê duyệt chính thức vào ngày 2026-09-18 với tuyên bố nguyên văn: *"Tôi phê duyệt RQ2 hierarchy clarification: 12 hazard atoms là PRIMARY RQ2 strata, còn 7 grouped A–G categories chỉ là SECONDARY EXPLORATORY summaries."* (Căn cứ chi tiết tại [notes/w2_rq2_hierarchy_erratum_brief.md](notes/w2_rq2_hierarchy_erratum_brief.md)).
  - **A. 12 Hazard Atoms là PRIMARY RQ2 STRATA (Các tầng phân tích RQ2 chính):**
    - Danh mục 12 Hazard Atoms đã phê duyệt tại Mục 1 ở trên chính thức là **PRIMARY RQ2 STRATA** cho mọi phân tích tập trung sai số của câu hỏi nghiên cứu RQ2.
    - Bản chất phương pháp luận: Hệ phân loại này là **Hệ phân loại nghiên cứu thao tác (`Operational Research Taxonomy`)** được xây dựng và kiểm chứng thực nghiệm từ các mệnh đề nguy cơ của InspecSafe-V1; **KHÔNG PHẢI** là hệ phân loại an toàn công nghiệp phổ quát (`universal industrial safety taxonomy`) hay hệ phân loại chân lý tuyệt đối (`absolute ground-truth taxonomy`).
    - Lý do xác lập làm Primary: Bảo toàn độ phân giải chẩn đoán kỹ thuật chi tiết (`finer diagnostic granularity`), đạt độ bao phủ ánh xạ tất định 100% mẫu Anomaly, và khớp nối trực tiếp với cuộc tổng điều tra Census D6.
  - **B. 7 Grouped Categories A–G là SECONDARY EXPLORATORY SUMMARIES (Các nhóm tổng hợp phụ mang tính khám phá):**
    - 7 nhóm gom ứng viên đã nêu tại Mục 5 ở trên được chuẩn hóa thành **SECONDARY EXPLORATORY SUMMARIES**.
    - Đặc điểm: Là cấu trúc phân nhóm phái sinh cấp cao (`derived groupings`), có tính chồng chéo cao, **không có tính cộng dồn (`non-additive`)**, và không phải là taxonomy chính của giao thức đánh giá RQ2.
  - **C. Bảo toàn các sự thật thực chứng về đa nguy cơ:**
    - Đúng **512 / 1.000 mẫu ảnh Anomaly (51,2%)** chứa từ 2 nguy cơ nguyên tử trở lên ($\ge 2$ hazard atoms).
    - 7 nhóm gom A–G tạo ra **1.381 lượt thành viên (sample memberships)** trên 1.000 mẫu ảnh bất thường độc nhất.
- **Thay thế quyết định:** Không (Bổ sung làm rõ thứ bậc phân tầng RQ2 ngày 2026-09-18).

## DEC-W2-D7-007 — Rationale Annotation Policy

- **ID:** DEC-W2-D7-007
- **Ngày:** 2026-09-17
- **Trạng thái:** ĐƯỢC CHẤP THUẬN
- **Vấn đề cần quyết định:**
  - Xác lập chính sách chính thức về việc gán nhãn vùng lý do do con người xác định (Human Rationale Regions) trong khuôn khổ giai đoạn SafeShift Seminar 8 tuần: có triển khai chiến dịch tự tạo nhãn mới hay không.
  - Xác định ranh giới phương pháp luận và các tuyên bố giới hạn bắt buộc (limitations) khi sử dụng các chú thích đối tượng có sẵn của InspecSafe-V1.
  - Định hướng và tiêu chuẩn phương pháp luận cho hướng mở rộng chiến dịch gán nhãn rationale trong giai đoạn Luận văn tốt nghiệp (Thesis Extension).
  - Thiết lập chính sách phương pháp luận đối với chỉ số Tỷ lệ Ảo giác Đối tượng (Object Hallucination Rate) trên toàn bộ bộ dữ liệu.
  - Tái khẳng định các nội dung kỹ thuật mà bộ ba quyết định D4, D6, D7 không chốt và chuyển giao cho W2.4 và W2.5.
- **Bối cảnh và bằng chứng:**
  - Kế thừa các nguyên tắc phương pháp luận tại [DEC-W2-D1-001](#dec-w2-d1-001), [DEC-W2-D2-002](#dec-w2-d2-002), [DEC-W2-D3-003](#dec-w2-d3-003), [DEC-W2-D4-004](#dec-w2-d4-004) và [DEC-W2-D6-006](#dec-w2-d6-006).
  - Báo cáo căn cứ kỹ thuật phương pháp luận chi tiết tại [notes/w2_grounding_census_decision_brief.md](notes/w2_grounding_census_decision_brief.md) (Mục 15, 16, 17, 18.2, 19).
  - Bộ dữ liệu InspecSafe-V1 gồm 37.434 đa giác đối tượng gốc trong tệp JSON, hoàn toàn không có bounding box nguy cơ hay chú thích vùng lý do con người ([notes/w1_dataset_audit.md](notes/w1_dataset_audit.md), [notes/dataset_schema.md](notes/dataset_schema.md), [notes/research_feasibility_audit.md](notes/research_feasibility_audit.md)).
  - Cuộc tổng điều tra D6 khẳng định dataset đã sở hữu sẵn **781 Direct atoms** (nằm trong **721 mẫu** thuộc Direct-Support Sample Pool) có đa giác đối tượng hỗ trợ trực tiếp cho khẳng định nguy cơ, cùng **947 Weak-Proxy atoms** (nằm trong **608 mẫu** thuộc Weak-Proxy Sample Pool).
  - Bộ dữ liệu InspecSafe-V1 không phải là bộ dữ liệu chú thích đối tượng triệt để (`annotation is not exhaustive`); có nhiều trường hợp vật thể có thật trong ảnh nhưng annotator gốc không vẽ đa giác trong tệp JSON (như 12 ca nước/dầu tràn thiếu nhãn `Liquid`/`Oil`, 5 ca khói thiếu nhãn `Smoke`, 6 ca dị vật thiếu nhãn).
- **Các phương án:**
  - *Phương án D7-A — Không tạo nhãn rationale mới trong giai đoạn Seminar (Được chọn):* Sử dụng nguyên trạng các phân tầng Direct Object-Support và Weak Proxy có sẵn; công bố rõ ràng giới hạn dữ liệu.  
    *Đánh giá:* Tuyệt đối an toàn về tiến độ 8 tuần; không phát sinh thêm tính chủ quan từ việc tự gán nhãn mới; tập trung trọn vẹn tài nguyên vào việc chuẩn hóa benchmark và tái lập baseline mô hình.
  - *Phương án D7-B — Chiến dịch gán nhãn 100 mẫu đơn lẻ (100-Sample Rationale Campaign):* Nhóm nghiên cứu tự vẽ hộp bao vùng lý do giải thích cho 100 mẫu Anomaly.  
    *Đánh giá:* Phát sinh rủi ro phương pháp luận rất lớn do tính chủ quan cá nhân của người gán nhãn; chi phí thời gian ước tính sơ bộ khoảng ~20–30 giờ (ước lượng kế hoạch sơ bộ, không phải số đo thực nghiệm); có nguy cơ làm méo mó tính khách quan của benchmark.
  - *Phương án D7-C — Chiến dịch gán nhãn kép 50–100 mẫu có thẩm định chuyên gia (Double-Annotated Subset):* Gán nhãn kép độc lập bởi 2 người, đo lường độ nhất quán liên gán nhãn, trọng tài phân xử bất đồng và có chuyên gia an toàn thẩm định.  
    *Đánh giá:* Đảm bảo tính khoa học cao hơn D7-B; tuy nhiên chi phí rất lớn (~40–60 giờ planning estimate), nguy cơ cao gây vỡ tiến độ Seminar 8 tuần.
- **Quyết định:**
  - **1. Chính sách Gán nhãn trong giai đoạn Seminar (CHỌN D7-A):**
    - Trong giai đoạn Seminar, SafeShift chính thức **CHỌN D7-A: KHÔNG TẠO RATIONALE ANNOTATION MỚI**.
    - Cụ thể:
      - **Không tự vẽ Human Rationale Boxes (Hộp vùng lý do của con người)**.
      - **Không tạo 100-sample rationale campaign (Chiến dịch gán nhãn 100 mẫu)**.
      - **Không gọi object polygons hiện có là human rationale GT**.
    - SafeShift Seminar sử dụng:
      - **Direct Object-Support**
      - **Weak Proxy**
      và công bố limitation (giới hạn phương pháp luận) rõ ràng.
  - **2. Bốn Lý do Cốt lõi Lựa chọn D7-A:**
    1. *Dataset hiện đã có 781 Direct atoms* (trên 721 mẫu) đủ để xây grounding benchmark có ý nghĩa khoa học độc lập.
    2. *Tự gán rationale bởi nhóm sinh viên có rủi ro subjectivity (tính chủ quan)*, thiếu quy chuẩn an toàn công nghiệp chuẩn mực và có thể làm giảm tính khách quan của một benchmark kiểm toán độc lập.
    3. *Giai đoạn Seminar 8 tuần ưu tiên benchmark/protocol và baseline reproduction* (tái lập các baseline của mô hình VLM ở W3–W4), không nên phân tán tài nguyên.
    4. *Tạo rationale annotation sẽ làm mở rộng scope (phạm vi)* và có nguy cơ trực tiếp ảnh hưởng tiến độ hoàn thành Seminar.
  - **3. Bảo lưu Hướng mở rộng cho Luận văn Tốt nghiệp (Thesis Extension):**
    - SafeShift **bảo lưu D7-C cho Thesis (Khóa luận tốt nghiệp)**:
      - Quy mô: **50–100 samples**.
      - **Double annotation (gán nhãn kép)** độc lập bởi 2 người.
      - **Disagreement resolution (xử lý bất đồng)** có trọng tài phân xử.
      - **Domain-expert review (thẩm định chuyên gia an toàn lao động)** nếu khả thi.
    - Quy tắc xác lập trạng thái: Đây là **future thesis candidate (ứng viên nghiên cứu cho khóa luận tương lai)**, **KHÔNG PHẢI nhiệm vụ Seminar hiện tại**.
  - **4. Chính sách đối với Chỉ số Ảo giác Đối tượng (Object Hallucination Policy):**
    - **Không phê duyệt full-dataset Object Hallucination Rate (Tỷ lệ ảo giác đối tượng trên toàn bộ dataset)**, vì annotation không exhaustive (chú thích hình học không mang tính triệt để).
    - **Không dùng:**
      $$\text{missing JSON label} = \text{object absent}$$
      *(nhãn thiếu trong JSON đồng nghĩa với đối tượng không tồn tại trong ảnh)*.
    - Nếu sau này muốn đánh giá ảo giác đối tượng:
      - Sử dụng **closed critical vocabulary (từ điển đối tượng nguy cơ đóng)** KẾT HỢP VỚI **manually verified positive/negative subset (tập dương/âm kiểm tra thủ công)**, HOẶC:
      - Một cuộc **annotation-completeness audit (kiểm toán độ đầy đủ chú thích)** dành riêng cho tập từ điển đó.
      Toàn bộ các nội dung này sẽ được xem xét và quyết định tại bước **W2.4**.
  - **5. Những nội dung kỹ thuật D4, D6, D7 KHÔNG CHỐT (Deferred Items):**
    - Ba quyết định này (D4, D6, D7) **tuyệt đối KHÔNG chốt**:
      - Macro-F1 formula (Công thức Macro-F1).
      - Balanced Accuracy formula (Công thức Balanced Accuracy).
      - FPR/FNR details (Chi tiết FPR/FNR).
      - Cross-Domain Drop formula (Công thức suy giảm hiệu năng xuyên miền).
      - IoU threshold (Ngưỡng IoU).
      - Pointing Game threshold (Ngưỡng Pointing Game).
      - Confidence interval (Khoảng tin cậy).
      - Bootstrap procedure (Quy trình bootstrap).
      - Hypothesis tests (Các bài kiểm định giả thuyết thống kê).
      - Final model list (Danh sách mô hình cuối cùng).
      - Final prompt wording (Câu chữ prompt cuối cùng).
    - **D5 / statistical protocol (giao thức thống kê)** vẫn thuộc về bước **W2.4**.
    - **Model capability / model list** thuộc về bước **W2.5**.
- **Lý do:**
  1. Bảo toàn tính toàn vẹn nghiên cứu và tiến độ của Seminar 8 tuần.
  2. Tránh đưa vào nhãn tự tạo thiếu kiểm chứng khách quan làm méo mó benchmark.
  3. Minh bạch về sự không đầy đủ của chú thích đối tượng gốc, ngăn chặn việc tính toán chỉ số ảo giác sai lệch.
  4. Xác lập lộ trình phân kỳ rạch ròi: hoàn thành Seminar vững chắc trước khi mở rộng sang gán nhãn chuyên sâu ở Luận văn.
- **Ảnh hưởng tới dataset, split, metric và reproducibility:**
  - **Dataset:** Giữ nguyên dữ liệu gốc; không bổ sung nhãn rationale tự tạo vào bộ dữ liệu Seminar.
  - **Split:** Không làm thay đổi phân chia train/test hay 5 miền.
  - **Metrics:** Không tính Object Hallucination Rate trên toàn bộ dataset; toàn bộ công thức metric khác chuyển sang W2.4.
  - **Reproducibility:** Báo cáo trung thực các hạn chế dữ liệu; các kết luận thực nghiệm bám chắc vào các phân tầng đã kiểm chứng của D6.
- **Người chấp thuận và thời điểm:** Project Owner / Research Lead (Chủ dự án / Người phụ trách nghiên cứu), ngày 2026-09-17.
- **Task/thí nghiệm liên quan:**
  - [notes/w2_grounding_census_decision_brief.md](notes/w2_grounding_census_decision_brief.md) (W2.3 Decision Brief, Mục 15–19)
  - [notes/research_feasibility_audit.md](notes/research_feasibility_audit.md)
  - [notes/w1_dataset_audit.md](notes/w1_dataset_audit.md), [notes/dataset_schema.md](notes/dataset_schema.md)
  - Quyết định nền tảng [DEC-W2-D1-001](#dec-w2-d1-001), [DEC-W2-D2-002](#dec-w2-d2-002), [DEC-W2-D3-003](#dec-w2-d3-003), [DEC-W2-D4-004](#dec-w2-d4-004), [DEC-W2-D6-006](#dec-w2-d6-006)
  - Định hướng trực tiếp cho định nghĩa metric tại W2.4, khảo sát mô hình tại W2.5 và thực thi baseline tại W3.
- **Thay thế quyết định:** Không.

## DEC-W2-D8-008 — Model, Prompt & Interface Protocol

- **ID:** DEC-W2-D8-008
- **Ngày:** 2026-09-18
- **Trạng thái:** ĐƯỢC CHẤP THUẬN
- **Vấn đề cần quyết định:**
  - Thiết lập giao thức toàn diện về mô hình, câu lệnh chỉ dẫn (prompt), phân lập quy tắc nhiệm vụ (task policy), kiến trúc lệnh gọi (call architecture), từ điển nguy cơ định vị (hazard vocabulary), giao diện đầu ra chuẩn hóa (canonical interface & schema), cấu hình giải mã ít biến động theo từng nhà cung cấp (provider-supported low-variance decoding), và kiểm soát nguồn gốc (provenance).
  - Phê chuẩn Tường lửa Kiểm chuẩn (Benchmark Firewall) và Quy tắc Phát triển Mù (Blind Development Rules) để bảo vệ tính độc lập của tập dữ liệu InspecSafe-V1.
  - Thiết lập Chính sách Đóng băng Giao thức (Protocol Freeze Policy) và Quy tắc Kiểm soát Thay đổi Sau Đóng băng (Post-Freeze Change Control).
  - Lựa chọn danh sách rút gọn mô hình P2 (Core 4-Provider Shortlist) và chính sách phân tầng nhận biết năng lực định vị không gian (Capability-Aware Grounding Eligibility: Level 1, 2A, 2B, 3).
  - Xác lập chính sách tái lập baseline upstream (P1 Baseline Reproduction Policy).
- **Bối cảnh và bằng chứng:**
  - Báo cáo phân tích phương pháp luận toàn diện tại [notes/w2_model_prompt_interface_decision_brief.md](notes/w2_model_prompt_interface_decision_brief.md) (W2.5).
  - Kế thừa toàn bộ hệ thống quyết định đã khóa: [DEC-W2-D1-001](#dec-w2-d1-001) (Cross-Domain Robustness, P1/P2/P3/P4), [DEC-W2-D2-002](#dec-w2-d2-002) (Prediction Unit là ẢNH, lưu trữ raw outputs cấp ảnh), [DEC-W2-D3-003](#dec-w2-d3-003) (Domain mismatch và platform confounding), [DEC-W2-D4-004](#dec-w2-d4-004) (Canonical grounding format $x$-first, Capability-Aware Policy B), [DEC-W2-D5-005](#dec-w2-d5-005) (Hệ thống metric phân loại và định vị RQ1/RQ2/RQ3, bootstrap), [DEC-W2-D6-006](#dec-w2-d6-006) (Census 12 Hazard Atoms, 3 trạng thái hỗ trợ không gian Direct/Weak-Proxy/Unsupported), [DEC-W2-D7-007](#dec-w2-d7-007) (Chọn D7-A không tạo nhãn rationale mới, không tính Object Hallucination full-dataset).
  - Đính chính thứ bậc RQ2 đã được phê duyệt ngày 2026-09-18 (PR #15): 12 Hazard Atoms là PRIMARY RQ2 STRATA, 7 nhóm gom A–G là SECONDARY EXPLORATORY SUMMARIES ([notes/w2_rq2_hierarchy_erratum_brief.md](notes/w2_rq2_hierarchy_erratum_brief.md)).
  - Khảo sát kỹ thuật chính thức từ tài liệu các nhà cung cấp tại mốc 2026-09-18 (Google Cloud AI Studio/Vertex AI, OpenAI Platform, Anthropic Developer Docs, Alibaba Cloud DashScope / Hugging Face).
  - GPU máy trạm 4 GB VRAM áp đặt giới hạn không thể tự host mô hình cục bộ lớn, dẫn đến việc phải dùng Hosted API với các ràng buộc về tính ổn định của snapshot và giới hạn tái lập (`HOSTED_BACKEND_NOT_FULLY_PINNABLE`).
  - Phê duyệt chính thức của Project Owner vào ngày 2026-09-18 với tuyên bố nguyên văn:
    > *"Tôi phê duyệt D8 theo phương án đề xuất: Benchmark Firewall, Protocol Freeze, C1, A2, B2, shortlist 4 provider, capability-aware grounding, provider-specific low-variance decoding và P1 reproduction policy."*
- **Các phương án:**
  - *Kiến trúc Lệnh gọi (Trục A):* A1 (One Combined Call: tiết kiệm chi phí nhưng gây rủi ro search conditioning), A2 (Two Independent Calls: tách bạch độc lập Call 1 và Call 2, bảo vệ RQ3, được chọn), A3 (Two Conditioned Calls: tạo thiên lệch điều kiện hóa nhân tạo, bị loại bỏ hoàn toàn).
  - *Từ điển Nguy cơ Định vị (Trục B):* B1 (Open Vocabulary: tự do miêu tả nhưng khó ánh xạ tất định), B2 (Closed 12-Hazard Vocabulary: khớp toán học 100% với D5/D6, được chọn cho Call 2 độc lập), B3 (Hybrid Vocabulary).
  - *Quy tắc Nhiệm vụ Phân loại (Trục C):* C1 (Policy-Aware Classification: cung cấp bảng an toàn ngành, được chọn), C2 (Abstract Policy: thiếu quy tắc cụ thể), C3 (No-Policy: under-specified nghiêm trọng, bị loại bỏ).
  - *Cổng Năng lực Không gian Ngoại vi:* Loại bỏ các ngưỡng số tùy tiện ($\text{IoU} \ge 0.30$, distractor $\text{IoU} < 0.10$); thay bằng Sanity Check Gate kiểm tra tính hợp lý kỹ thuật trên dữ liệu ngoài benchmark có GT khách quan.
  - *Chính sách Giải mã:* Loại bỏ quy định áp đặt máy móc `temperature = 0.0` đồng loạt; thay bằng Provider-Supported Low-Variance Configuration phù hợp với từng API.
  - *Chính sách Tái lập P1:* Loại bỏ dung sai tùy tiện $\pm 1–2\%$; thay bằng báo cáo sai số tuyệt đối $\Delta$ và phân loại trạng thái tái lập có căn cứ kỹ thuật.
- **Quyết định:**
  - **1. Phê chuẩn Toàn văn và Tuyên bố của Project Owner:**
    Chính thức phê duyệt Quyết định D8 theo văn bản trình duyệt tại [notes/w2_model_prompt_interface_decision_brief.md](notes/w2_model_prompt_interface_decision_brief.md).
    Ghi nhận nguyên văn tuyên bố phê duyệt của Project Owner ngày 2026-09-18:
    > *"Tôi phê duyệt D8 theo phương án đề xuất: Benchmark Firewall, Protocol Freeze, C1, A2, B2, shortlist 4 provider, capability-aware grounding, provider-specific low-variance decoding và P1 reproduction policy."*
  - **2. Tường lửa Kiểm chuẩn & Quy tắc Phát triển Mù (Benchmark Firewall & Blind Development):**
    - Toàn bộ **5.013 ảnh của InspecSafe-V1 trong Giao thức P2 là EVALUATION-ONLY** (và 1.250 ảnh cho P1).
    - Các hành vi bị nghiêm cấm trước khi đóng băng giao thức:
      1. Cấm thăm dò năng lực trên ảnh InspecSafe (*No capability probing using benchmark images*).
      2. Cấm tinh chỉnh hoặc gỡ lỗi prompt dựa trên output của benchmark (*No prompt tuning/debugging using benchmark outputs*).
      3. Cấm lựa chọn mô hình dựa trên hiệu năng trên benchmark (*No model selection using benchmark performance*).
      4. Cấm phát triển parser điều kiện hóa theo output cụ thể của InspecSafe (*No output-conditioned parser development*).
      5. Cấm tinh chỉnh ngưỡng quyết định dựa trên kết quả InspecSafe (*No threshold tuning using InspecSafe results*).
    - Các hoạt động phát triển mù được phép:
      1. Phản hồi giả định tự tạo bằng tay (*Handcrafted dummy responses*).
      2. Dữ liệu JSON tổng hợp (*Synthetic JSON*).
      3. Tài liệu kỹ thuật chính thức từ nhà cung cấp (*Provider documentation*).
      4. Hình ảnh bên ngoài có giấy phép mở hoặc ảnh tổng hợp (*External openly licensed / synthetic images*) phục vụ kiểm thử pipeline ảnh và xác thực năng lực không gian.
  - **3. Chính sách Đóng băng Giao thức (Protocol Freeze Policy):**
    - Giao thức thực nghiệm bắt buộc phải được đóng băng toàn diện **TRƯỚC LẦN SUY LUẬN ĐẦU TIÊN** trên bất kỳ ảnh nào của InspecSafe-V1.
    - Nội dung đóng băng tương lai bao gồm: shortlist mô hình và model ID chính xác, tuyến phục vụ mô hình (serving routes), prompt hệ thống + người dùng, task policy, kiến trúc lệnh gọi, từ điển nguy cơ, JSON Schema đầu ra, adapter/parser, cấu hình decoding/thinking, vai trò/năng lực mô hình, công cụ tính toán metric, và phiên bản giao thức tương ứng.
    - **Trạng thái đóng băng hiện tại:**
      `protocol_freeze_commit_sha: PENDING`
      *(Lưu ý: Phê duyệt D8 chưa đồng nghĩa với Protocol Freeze; tuyệt đối KHÔNG điền mã commit SHA tại thời điểm này)*.
  - **4. Chính sách Nhiệm vụ Phân loại An toàn (Classification Task Policy):**
    - Phê chuẩn phương án **C1 — Policy-Aware Classification**.
    - Call 1 nhận: `Image` + Bảng quy chuẩn an toàn ngành / Quy tắc nhiệm vụ (Safety Policy / Task Rules).
    - Call 1 xuất: Đúng nhãn `safety_level` (`Level01`, `Level02`, `Level03`, `Level04`).
    - Quy tắc độc lập: Call 1 **TUYỆT ĐỐI KHÔNG NHẬN** kết quả dự đoán của Call 2, không nhận danh sách nguy cơ dự đoán từ Call 2, và không nhận bất kỳ đầu ra định vị nào.
  - **5. Kiến trúc Lệnh gọi (Call Architecture):**
    - Phê chuẩn phương án **A2 — Two Independent Calls** cho giao thức nghiên cứu chính P2.
      - *Call 1:* Phân loại an toàn (Safety Classification) với Task Policy C1 $\rightarrow$ xuất `safety_level`. Áp dụng cho 100% mô hình.
      - *Call 2:* Định vị nguy cơ & Bám bằng chứng (Hazard Localization / Grounding) với từ điển đóng B2 $\rightarrow$ xuất tọa độ hộp bao chuẩn hóa. Chỉ áp dụng cho các mô hình Grounding-Eligible.
    - Quy tắc phương pháp luận tối quan trọng: **Call 2 hoàn toàn độc lập, KHÔNG nhận kết quả dự đoán của Call 1**.
    - Loại bỏ hoàn toàn phương án điều kiện hóa A3. Phương án A1 (One Combined Call) bị loại bỏ khỏi giao thức chính P2.
  - **6. Từ điển Nguy cơ Định vị (Hazard Vocabulary):**
    - Phê chuẩn phương án **B2 — Closed 12-Hazard Vocabulary** CHỈ dành riêng cho Call 2 độc lập.
    - Đúng 12 Hazard Atoms của D6 được sử dụng làm **từ điển định vị nguy cơ đóng (`closed-set hazard localization vocabulary`)**.
    - Khẳng định rõ ràng: Đây **KHÔNG PHẢI là bài toán phát hiện nguy cơ từ vựng mở (`open-vocabulary hazard discovery`)**.
    - Phân định độc lập: Tuyệt đối không đánh đồng bài toán phân tích phân tầng sai số phân loại an toàn cấp ảnh của RQ2 (**RQ2: Image-level classification error stratification**) với bài toán định vị nguy cơ / bám bằng chứng không gian của RQ3 (**RQ3: Hazard localization / spatial evidence grounding**).
    - Thứ bậc RQ2 giữ nguyên vẹn theo Erratum PR #15: **12 Hazard Atoms là PRIMARY RQ2 STRATA**, **7 Grouped Categories A–G là SECONDARY EXPLORATORY SUMMARIES**.
  - **7. Chính sách Danh sách Rút gọn Mô hình P2 (Core 4-Provider Shortlist):**
    - Phê chuẩn shortlist 4 nhà cung cấp chính thức:
      1. *Google:* `gemini-3.8-flash` (Level 1 — DOC-VERIFIED SPATIAL, Grounding-Eligible).
      2. *Alibaba Cloud:* `qwen3-vl-8b-instruct` (Level 1 — DOC-VERIFIED SPATIAL, Grounding-Eligible qua các giả định tuyến DashScope Singapore đã duyệt).
      3. *OpenAI:* `gpt-5.6-terra` (Level 3 — PROMPT-ONLY / UNVERIFIED SPATIAL, Classification-Only trừ khi cổng thử nghiệm ngoại vi thăng hạng lên Level 2A).
      4. *Anthropic:* `claude-sonnet-5` / `claude-sonnet-5-20260301` (Level 3 — PROMPT-ONLY / UNVERIFIED SPATIAL, Classification-Only trừ khi cổng thử nghiệm ngoại vi thăng hạng lên Level 2A).
    - Tuyệt đối không tự ý thay đổi model ID. Lựa chọn mô hình hoàn toàn độc lập với điểm số trên InspecSafe.
    - Nếu một snapshot API cụ thể của nhà cung cấp không còn khả dụng trước thời điểm đóng băng: ghi nhận trạng thái vòng đời/tương thích (`compatibility/lifecycle status`) thay vì âm thầm thay thế.
    - *Ghi chú về tính nhất quán của cấp độ năng lực (Consistency Note):* Cấp độ năng lực (`Capability Level`) là một phân loại trạng thái bằng chứng tài liệu/thực nghiệm (`evidence-status classification`), tuyệt đối không phải là bảng xếp hạng hiệu năng mô hình (`not a benchmark performance ranking`). Level 1 có nghĩa là tài liệu kỹ thuật chính thức của nhà cung cấp có công bố và hướng dẫn năng lực không gian. Level 3 có nghĩa là năng lực không gian chưa được kiểm chứng theo tiêu chuẩn của giao thức. Tuyệt đối không suy diễn chất lượng hay trí thông minh của mô hình từ số thứ tự cấp độ.
  - **8. Định vị Nhận biết Năng lực (Capability-Aware Grounding Eligibility):**
    - Nhiệm vụ phân loại an toàn áp dụng cho 100% mô hình trong shortlist.
    - Quyền tham gia đánh giá định vị (Grounding) tuân thủ chính sách nhận biết năng lực:
      - Chỉ các mô hình đạt **LEVEL 1 — DOC-VERIFIED SPATIAL** hoặc **LEVEL 2A — EXTERNAL SPATIAL-PROBE VERIFIED** mới được tham gia vào benchmark định lượng RQ3 Grounding.
      - **LEVEL 2B — FORMAT-OPERABILITY ONLY** (chỉ biết xuất JSON hợp lệ cú pháp nhưng chưa kiểm chứng định vị không gian) **KHÔNG ĐỦ ĐIỀU KIỆN** tham gia grounding benchmark.
      - **LEVEL 3 — PROMPT-ONLY / UNVERIFIED** bắt buộc phải giữ nguyên trạng thái chỉ phân loại (`Classification-Only`), trừ khi vượt qua cổng thử nghiệm năng lực ngoại vi Target+Distractor.
      - Các mô hình không đủ điều kiện định vị được ghi nhận là **`NOT PARTICIPATING`**, tuyệt đối không bị gán lỗi giả mạo $\text{IoU} = 0.0$ và không bị tính vào bảng xếp hạng grounding.
  - **9. Cổng Thử nghiệm Năng lực Ngoại vi (External Target+Distractor Sanity Gate):**
    - Cổng kiểm tra tính hợp lý kỹ thuật ngoại vi chỉ sử dụng hình ảnh bên ngoài InspecSafe (ảnh COCO / Open Images / Synthetic) có ground-truth tọa độ khách quan.
    - Tiêu chí vượt qua (Pass logic):
      1. Xuất đúng cấu trúc JSON và tọa độ hợp lệ.
      2. Tâm hộp bao dự đoán nằm trong bounding box mục tiêu ($T$).
      3. Hộp bao dự đoán không bao trùm tâm của vật thể gây nhiễu ($D$).
      4. Bám vị trí mục tiêu có hệ thống khi hoán đổi vị trí $T$ và $D$.
      5. Không có hành vi xuất hộp bao khổng lồ bao trùm ảnh (*giant box*).
    - Điểm số IoU chỉ mang tính chẩn đoán mô tả (*descriptive diagnostic*), tuyệt đối không dùng làm ngưỡng đóng mở cổng tùy tiện.
    - **Không thực thi cổng này trong bước phê duyệt D8** (chuyển sang danh sách kiểm tra trước đóng băng).
  - **10. Chính sách Giải mã Ít Biến động Được Nhà Cung Cấp Hỗ Trợ (Provider-Supported Low-Variance Decoding Policy):**
    - Nguyên tắc: *Cùng một nhiệm vụ ngữ nghĩa, sử dụng các tham số kỹ thuật ít biến động tương thích với từng nhà cung cấp*.
    - Tuyệt đối không ép buộc `temperature = 0.0` đồng loạt cho mọi mô hình nếu API không hỗ trợ hoặc khuyến nghị khác.
    - Bảo lưu cấu hình riêng biệt đã thẩm định:
      - *Gemini 3.8 Flash:* `thinking: "low"`.
      - *GPT-5.6-Terra:* `reasoning_effort: "low"`.
      - *Claude Sonnet 5:* Adaptive thinking / supported effort policy.
    - *Tuyến phục vụ Qwen:* Giữ nguyên các trạng thái đã chốt:
      - `ROUTE_REGION_PINNED` (Alibaba Cloud DashScope, Singapore `ap-southeast-1`).
      - `WORKSPACE_ENDPOINT_TO_BE_RESOLVED_BEFORE_FREEZE`.
      - `QWEN_DECODING_PENDING_ROUTE_CONFIRMATION`.
      - `HOSTED_BACKEND_NOT_FULLY_PINNABLE`.
      - Serving precision / quantization: `UNDISCLOSED BY PROVIDER`.
      - Việc phê duyệt D8 không tự động giải quyết các trường triển khai kỹ thuật này; chúng bắt buộc phải được giải quyết tại thời điểm đóng băng giao thức.
  - **11. Chính sách Tái lập Baseline Upstream (P1 Baseline Reproduction Policy):**
    - Giao thức P1 sử dụng:
      1. Tập kiểm thử chính thức gồm đúng **1.250 ảnh**.
      2. Prompt và task policy nguyên bản của tác giả gốc.
      3. Cấu hình giải mã nguyên bản `temperature = 0.1`.
      4. Mô hình tham chiếu upstream khi truy cập được; nếu không thì dùng phiên bản Claude tương thích và ghi rõ nhãn `Compatibility Reproduction`.
      5. Pipeline tương đồng văn bản BGE-M3 cục bộ theo đúng mã nguồn gốc.
    - Loại bỏ tiêu chí dung sai tùy tiện $\pm 1–2\%$. Báo cáo:
      $$\text{Metric}_{\text{reproduced}}, \quad \text{Metric}_{\text{published}}, \quad \Delta, \quad \text{Giải thích tương thích kỹ thuật}$$
    - Chuẩn hóa hệ thống nhãn trạng thái: `REPRODUCIBLE`, `COMPATIBILITY_REPRODUCTION`, `NOT_EXACTLY_REPRODUCIBLE`.
  - **12. Quy tắc Kiểm soát Thay đổi Sau Đóng băng (Post-Freeze Change Control):**
    - Nghiêm cấm mọi hành vi sửa đổi prompt dựa trên hiệu năng (*No performance-driven prompt modification*) sau lần suy luận đầu tiên trên InspecSafe.
    - Sửa lỗi kỹ thuật (bug fix) bắt buộc phải tuân thủ: ghi nhận issue/nguyên nhân, tăng phiên bản giao thức (*protocol version bump*), vô hiệu hóa các lượt chạy bị ảnh hưởng, và chạy lại toàn bộ các evaluation pool liên quan. Nghiêm cấm tùy biến cứu điểm riêng cho một mô hình (*No one-model rescue tuning*).
- **Lý do:**
  1. Bảo đảm tính khách quan, ngăn ngừa thích nghi benchmark nội sinh thông qua Tường lửa Kiểm chuẩn và Quy tắc Phát triển Mù.
  2. Kiến trúc hai lệnh gọi độc lập A2 giải tỏa hoàn toàn thiên lệch điều kiện hóa giữa phân loại và định vị, bảo vệ tính trung thực của chỉ số nhất quán $\text{CGI}@\tau$ (RQ3).
  3. Cung cấp task policy C1 giúp bài toán phân loại an toàn có đầy đủ ngữ nghĩa, phản ánh đúng tiêu chuẩn an toàn công nghiệp gốc.
  4. Từ điển đóng 12 nguy cơ B2 trong Call 2 cho phép ánh xạ tất định 100% vào các phân tầng của D5/D6 mà không làm ảnh hưởng đến quyết định phân loại an toàn của Call 1.
  5. Chính sách nhận biết năng lực (Capability-Aware) ngăn chặn việc phạt oan mô hình không hỗ trợ xuất tọa độ hoặc cấp quyền sai cho mô hình chỉ có năng lực định dạng bề mặt (Level 2B).
  6. Tôn trọng thực tế kỹ thuật của các API thương mại hiện hành thay vì áp đặt tham số giải mã phi thực tế.
  7. Minh bạch hóa quy trình tái lập P1 và công bố trung thực các giới hạn tái lập của tuyến Hosted API Qwen.
- **Ảnh hưởng tới dataset, split, metric và reproducibility:**
  - **Dataset:** 5.013 ảnh InspecSafe-V1 là Evaluation-Only. Tuyệt đối không thay đổi dữ liệu gốc, không sửa nhãn thô.
  - **Split:** P1 (1.250 ảnh test) và P2 (5.013 ảnh full) giữ nguyên vẹn.
  - **Metrics:** Không thay đổi bất kỳ công thức nào của D5. Bảo toàn phân cấp RQ2 (12 Primary Atoms, 7 Secondary Groups).
  - **Reproducibility:** Bắt buộc ghi nhận commit SHA khi freeze (`protocol_freeze_commit_sha: PENDING`), lưu trữ nguyên văn raw outputs cấp ảnh, ghi nhận đầy đủ metadata môi trường, phiên bản API và thông số sinh cho từng mẫu.
- **Người chấp thuận và thời điểm:** Project Owner / Research Lead, ngày 2026-09-18.
- **Task/thí nghiệm liên quan:**
  - [notes/w2_model_prompt_interface_decision_brief.md](notes/w2_model_prompt_interface_decision_brief.md) (W2.5 Technical Decision Brief)
  - Quyết định nền tảng [DEC-W2-D1-001](#dec-w2-d1-001), [DEC-W2-D2-002](#dec-w2-d2-002), [DEC-W2-D3-003](#dec-w2-d3-003), [DEC-W2-D4-004](#dec-w2-d4-004), [DEC-W2-D5-005](#dec-w2-d5-005), [DEC-W2-D6-006](#dec-w2-d6-006), [DEC-W2-D7-007](#dec-w2-d7-007)
  - [notes/w2_rq2_hierarchy_erratum_brief.md](notes/w2_rq2_hierarchy_erratum_brief.md) (PR #15)
  - Cơ sở trực tiếp để triển khai mã nguồn prompt, adapters, test suite và thực thi baseline W3.
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
