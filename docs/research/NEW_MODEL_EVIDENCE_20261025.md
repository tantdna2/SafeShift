# Bản đồ bằng chứng cho mô hình mới — 25/10/2026

Đọc cùng [báo cáo khả thi](NEW_MODEL_FEASIBILITY_20261025.md) và [nhật ký tìm kiếm](NEW_MODEL_SEARCH_20261025.md).

**25 công trình chính**, không tính phiên bản arXiv và bản hội nghị thành hai nghiên cứu. **13 hồ sơ đọc sâu** bên dưới đã đối chiếu phần phương pháp, thiết lập và kết quả/giới hạn trong bản gốc; ba hồ sơ gần khác ghi riêng mức đọc chưa đầy đủ. “Đọc sâu” không có nghĩa kiểm tra mọi chứng minh, code hoặc tái lập. Với nguồn chỉ đọc tóm tắt/trang tác giả, không dùng để kết luận sâu.

Các số là **tác giả báo cáo**, chưa chạy lại. AUROC đo khả năng xếp hạng; AP là average precision (độ chính xác trung bình theo đường precision–recall); IoU là intersection over union (giao trên hợp vùng). Không gộp số khác tác vụ, supervision (quyền dùng nhãn), cohort, backbone (mạng nền), hoặc đơn vị ảnh/pixel/video.

## Bản đồ và liên kết gốc

| ID | Công trình, năm và tình trạng công bố | Paper / code | Vai trò và mức tiếp cận |
| --- | --- | --- | --- |
| R01 | **Multimodal Benchmark for Safety Assessment in Industrial Inspection Scenarios** — InspecSafe, Scientific Data 2026; arXiv cùng họ | [Tạp chí](https://www.nature.com/articles/s41597-026-07796-x), [arXiv](https://arxiv.org/abs/2601.21173); [repo tác giả](https://github.com/liuzy0708/InspecSafe) | Dữ liệu an toàn trực tiếp liên quan; truy cập tạp chí lỗi chuyển hướng. Phân bố SafeShift dựa audit repo, không suy từ abstract (tóm tắt). |
| R02 | **SteelBench: Evaluating Vision-Language Models in Real-World Industrial Environments** — preprint (bản chưa xác minh công bố phản biện), 2026 | [Bản gốc v1](https://arxiv.org/html/2607.05264v1); code riêng chưa xác minh | Đọc sâu: an toàn, nguồn nhãn và video thực địa. |
| R03 | **PowerXGraph++: Regulation-Constrained Spatiotemporal Evidence Graphs with Counterfactual Explanations for Power-Worksite Safety Monitoring** — Electronics 15(18):4117, 2026, trang nhà xuất bản | [Paper](https://www.mdpi.com/2079-9292/15/18/4117); code chưa xác minh | Đầu mối rất gần P1; chỉ metadata/trích đoạn chỉ mục, toàn văn lỗi 429. Chưa kết luận về cơ chế/hiệu quả. |
| R04 | **O-VAD: Industrial Video Anomaly Detection through Object-Centric Tracking and Reasoning** — ECCV 2026, đối chiếu danh sách hội nghị | [Bản gốc v1](https://arxiv.org/html/2607.18142v1), [trang tác giả](https://o-vad.github.io/); [code](https://github.com/o-vad/O-VAD) | Đọc sâu: bằng chứng theo đối tượng và thời gian. |
| R05 | **EGVLR: Evidence-Grounded Vision–Language Reinforcement for Anomaly Reasoning** — ECCV 2026 | [Hội nghị](https://eccv.ecva.net/virtual/2026/poster/4683), [trang tác giả](https://leolin65.github.io/EGVLR-project/), [phụ lục](https://leolin65.github.io/EGVLR-project/supplementary.pdf); [code](https://github.com/leolin65/EGVLR-project) | Đọc phương pháp/kết quả trang tác giả và phụ lục; chưa đọc đầy đủ main PDF. |
| R06 | **EfficientAD: Accurate Visual Anomaly Detection at Millisecond-Level Latencies** — WACV 2024 | [Bản gốc v2](https://arxiv.org/html/2303.14535v2); [triển khai cộng đồng](https://github.com/nelson1425/EfficientAD), **không xác nhận là code tác giả** | Đọc sâu: mô hình nhỏ và tốc độ. |
| R07 | **AnomalyCLIP: Object-agnostic Prompt Learning for Zero-shot Anomaly Detection** — ICLR 2024 | [Hội nghị](https://proceedings.iclr.cc/paper_files/paper/2024/hash/d7b50b8ac2c781a12f26155f48310d8d-Abstract-Conference.html), [bản gốc v4](https://arxiv.org/html/2310.18961v4); [code](https://github.com/zqhang/AnomalyCLIP) | Đọc sâu: prompt học với nhãn bất thường phụ trợ. |
| R08 | **AdaCLIP: Adapting CLIP with Hybrid Learnable Prompts for Zero-Shot Anomaly Detection** — ECCV 2024 | [Hội nghị](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/05096.pdf), [bản gốc v1](https://arxiv.org/html/2407.15795v1); [code](https://github.com/caoyunkang/AdaCLIP) | Đọc sâu: prompt tĩnh/động. |
| R09 | **AnomalyDINO: Boosting Patch-Based Few-Shot Anomaly Detection with DINOv2** — WACV 2025 | [Hội nghị](https://openaccess.thecvf.com/content/WACV2025/html/Damm_AnomalyDINO_Boosting_Patch-Based_Few-Shot_Anomaly_Detection_with_DINOv2_WACV_2025_paper.html), [bản gốc v3](https://arxiv.org/html/2405.14529v3); [code](https://github.com/dammsi/AnomalyDINO) | Đọc sâu: baseline đặc trưng thị giác cố định. |
| R10 | **Exploring Intrinsic Normal Prototypes within a Single Image for Universal Anomaly Detection** — INP-Former, CVPR 2025 | [Bản gốc v1](https://arxiv.org/html/2503.02424v1), [phụ lục hội nghị](https://openaccess.thecvf.com/content/CVPR2025/supplemental/Luo_Exploring_Intrinsic_Normal_CVPR_2025_supplemental.pdf); [code](https://github.com/luow23/INP-Former) | Đọc sâu; INP-Former++ là mở rộng cùng họ, không tính thành nghiên cứu độc lập ở đây. |
| R11 | **ObjectCore — Efficient Few-shot Logical Anomaly Detection using Object Representations** — WACV 2026 | [Paper](https://openaccess.thecvf.com/content/WACV2026/papers/Fucka_ObjectCore_-_Efficient_Few-shot_Logical_Anomaly_Detection_using_Object_Representations_WACV_2026_paper.pdf), [lab tác giả](https://vicos.si/publications/fucka2026objectcore/); [code được paper công bố](https://github.com/MaticFuc/ObjectCore) | Trích đoạn PDF mở đầu + trang lab; PDF trực tiếp lỗi 403, README chưa lấy được. |
| R12 | **LayoutAD: Exploring Semantic-Geometric Misalignment Reasoning for Scene Layout Anomaly Detection** — CVPR 2026 | [Paper trên trang tác giả](https://michale-z.github.io/LayoutAD/static/pdfs/paper.pdf), [CVF](https://openaccess.thecvf.com/content/CVPR2026/html/Zeng_LayoutAD_Exploring_Semantic-Geometric_Misalignment_Reasoning_for_Scene_Layout_Anomaly_Detection_CVPR_2026_paper.html); [code](https://github.com/IMU-Group/LayoutAD) | Đọc sâu: đồ thị ngữ nghĩa–hình học. |
| R13 | **LogicQA: Logical Anomaly Detection with Vision Language Model Generated Questions** — ACL 2025, Industry Track (nhánh ứng dụng) | [Kỷ yếu](https://aclanthology.org/2025.acl-industry.29/), [bản đọc sâu v1](https://arxiv.org/html/2503.20252v1); code đúng công trình chưa xác minh | Đọc sâu: kiểm tra logic bằng câu hỏi. Tránh nhầm với dự án cùng tên khác. |
| R14 | **Toward Generalist Anomaly Detection via In-context Residual Learning with Few-shot Sample Prompts** — InCTRL, CVPR 2024 | [Bản gốc v2](https://arxiv.org/html/2403.06495v2); [code](https://github.com/mala-lab/InCTRL) | Đọc sâu: học sai khác với tham chiếu. |
| R15 | **Beyond Normal References: Discriminative Few-Shot Anomaly Detection** — IDEAL, preprint 2026; venue chưa xác minh | [Bản gốc v2, 30/05/2026](https://arxiv.org/html/2605.23231v2); [code được công bố sẽ cung cấp](https://github.com/mala-lab/IDEAL), chưa audit nội dung | Đọc sâu: đối thủ trực tiếp của P2. |
| R16 | **AnomalyGPT: Detecting Industrial Anomalies Using Large Vision-Language Models** — AAAI 2024 | [Paper](https://arxiv.org/abs/2308.15366), [trang tác giả](https://anomalygpt.github.io/); [code](https://github.com/CASIA-IVA-Lab/AnomalyGPT) | Định hướng VLM cho phát hiện/giải thích; đọc trang tác giả, chưa đọc sâu. |
| R17 | **Leveraging Vision-Language Models for Improving Domain Generalization in Image Classification** — VL2V-ADiP, CVPR 2024 | [Bản gốc v2](https://arxiv.org/html/2310.08255v2); [code](https://github.com/val-iisc/VL2V-ADiP) | Đọc sâu: chuyển tri thức sang mạng thị giác. |
| R18 | **In Search of Forgotten Domain Generalization** — ICLR 2025 | [Paper](https://openreview.net/forum?id=Fk3eod9aaD); [trang tác giả có liên kết code](https://brendel-group.github.io/clip-dg/) | Đọc trang tác giả: nhiễm miền trong tiền huấn luyện; chưa đọc sâu PDF. |
| R19 | **In Search of Lost Domain Generalization** — ICLR 2021, nền tảng | [Paper](https://openreview.net/pdf?id=lQdXeXDoWtI); [DomainBed](https://github.com/facebookresearch/DomainBed) | Nền tảng lựa chọn mô hình/đối chứng; định hướng, không nhập kết quả số vào kết luận. |
| R20 | **Grounding DINO: Marrying DINO with Grounded Pre-Training for Open-Set Object Detection** — ECCV 2024 | [Paper](https://arxiv.org/abs/2303.05499); [code](https://github.com/IDEA-Research/GroundingDINO) | Công cụ định vị đối tượng bằng văn bản; đọc metadata/repo. Box đối tượng không tự chứng minh nguy cơ. |
| R21 | **Interpretable Zero-Shot Learning with Locally-Aligned Vision-Language Model** — LaZSL, ICCV 2025 | [Paper](https://openaccess.thecvf.com/content/ICCV2025/html/Chen_Interpretable_Zero-Shot_Learning_with_Locally-Aligned_Vision-Language_Model_ICCV_2025_paper.html); [code](https://github.com/shiming-chen/LaZSL) | Định hướng căn chỉnh vùng–thuộc tính; abstract/trang hội nghị, không khẳng định giải thích nhân quả. |
| R22 | **Concept Bottleneck Models** — ICML 2020, nền tảng | [Paper và liên kết software](https://proceedings.mlr.press/v119/koh20a.html) | Định hướng dự đoán qua khái niệm và can thiệp khái niệm; chưa đọc sâu. |
| R23 | **MobileCLIP: Fast Image-Text Models through Multi-Modal Reinforced Training** — CVPR 2024 | [Paper/trang tác giả](https://machinelearning.apple.com/research/mobileclip); [code](https://github.com/apple-aiml-research/ml-mobileclip) | Mạng triển khai nhỏ; trang tác giả/repo. MobileCLIP2 cùng repo ghi TMLR 2025, không tách để tăng số lượng. |
| R24 | **DynamicViT: Efficient Vision Transformers with Dynamic Token Sparsification** — NeurIPS 2021, nền tảng | [Paper](https://arxiv.org/abs/2106.02034); [code](https://github.com/raoyongming/DynamicViT) | Định hướng chọn token theo đầu vào; chưa đọc sâu toàn văn. |
| R25 | **Task-driven Processing with Coarse-to-Fine Glimpse-based Active Perception** — CF-GAP, ECCV 2026 | [Bản gốc v1](https://arxiv.org/html/2609.09025v1), [kỷ yếu, tr.421–439](https://link.springer.com/book/10.1007/978-3-032-37435-6?page=2); code chưa xác minh | Đọc sâu: đối thủ bắt buộc của P3. |

Tình trạng ECCV 2026 của R04/R05/R25 còn được đối chiếu với [danh sách video hội nghị](https://eccv.ecva.net/Conferences/2026/Videos). “Code” ở bảng là liên kết gốc/được tác giả công bố, **không có nghĩa đã kiểm tra đầy đủ, đúng phiên bản paper hoặc chạy được**.

## 13 hồ sơ đọc sâu

Mỗi hồ sơ giữ phương pháp, dữ liệu, đánh giá/tài nguyên và giới hạn cùng vị trí kiểm tra. **SUY LUẬN về SafeShift** được tách khỏi mô tả tác giả.

### R02 — SteelBench

**ĐÃ KIỂM CHỨNG:** §2–4, Tables 3–4, Appendix E.7: 1.345 clip/149 giờ từ một nhà máy thép, 64 camera, 16 vùng; đánh giá VLM và nguồn gốc nhãn. Các lát cắt nhãn blind/anchored (người gán nhãn chưa/đã thấy gợi ý mô hình) có cỡ mẫu khác nhau. Appendix E.7 báo khác biệt cùng chiều qua chín mô hình.

**SUY LUẬN:** hữu ích để thiết kế gán nhãn độc lập; không coi tương phản giữa lát cắt là hiệu ứng nhân quả thuần nếu chưa xác nhận ghép cùng clip. Một nhà máy không chứng minh chuyển sang cơ sở mới. GPU/chi phí tổng chưa xác minh; không mượn video làm nhãn ảnh InspecSafe.

### R04 — O-VAD

**ĐÃ KIỂM CHỨNG:** §3, §4.1–4.2, Tables 1–2: VLM/SAM3 tìm đối tượng; CropFormer/SAM2 theo dõi; suy luận trạng thái rồi kiểm tra lại bằng hình ảnh. Phys-AD, LiquidAD, IPAD; đánh giá mức video/frame/type. GPT-5 và H200 141 GB; không huấn luyện riêng. Phys-AD AUROC trung bình theo loại 0,584, không phải mức gần hoàn hảo.

**SUY LUẬN:** cho thấy tổ chức bằng chứng quan trọng nhưng chưa tách được toàn bộ lợi ích từng mô-đun/chi phí dịch vụ. Đánh giá tên bất thường có LLM làm giám khảo; cần kiểm tra độ độc lập. Không chuyển kết quả động theo thời gian sang ảnh tĩnh.

### R06 — EfficientAD

**ĐÃ KIỂM CHỨNG:** §3, §4, Tables 1–2: teacher–student (thầy–trò) với mạng đặc trưng cục bộ nhỏ; autoencoder (mạng tái tạo) bổ sung ngữ cảnh cho bất thường logic. MVTec AD, VisA, MVTec LOCO; AUROC và PRO (độ chồng lấp vùng); lặp năm lần. Độ trễ bản nhỏ 2,2 ms tại 256×256 trên RTX A6000 là số tác giả đo.

**SUY LUẬN:** baseline nhẹ cần xét, không loại vì “chỉ phát hiện texture”. Normality (mẫu bình thường) của sản phẩm kiểm soát không tương đương an toàn công trường. Không suy độ trễ/bộ nhớ T4 từ A6000; code cộng đồng phải kiểm tra độ trung thành.

### R07 — AnomalyCLIP

**ĐÃ KIỂM CHỨNG:** §3–4, Table 1, Appendix A.1: prompt không phụ thuộc tên đối tượng, tối ưu toàn ảnh/vùng; encoder CLIP cố định, học từ tập phụ trợ có nhãn bất thường/mask. 17 bộ công nghiệp/y tế; RTX3090 24 GB, 518 pixel, 15 epoch (lượt qua dữ liệu). Bảng MVTec image AUROC không hơn WinCLIP ở mọi ô.

**SUY LUẬN:** “zero-shot ở tập đích” không phải không học và không dùng nhãn. Thiếu nhãn vùng nguy cơ làm việc chuyển cách học sang SafeShift chưa hiển nhiên; điểm defect (khuyết tật) không bảo đảm nhận biết nguy cơ ngữ nghĩa.

### R08 — AdaCLIP

**ĐÃ KIỂM CHỨNG:** §4–5 và thiết lập: prompt tĩnh học được kết hợp prompt động theo ảnh, tổng hợp ngữ nghĩa; học phụ trợ, đánh giá 14 bộ. RTX A6000 48 GB, ảnh 518 pixel, năm epoch. Dùng MVTec/ClinicDB phụ trợ và thay nguồn khi đánh giá chính các tập đó.

**SUY LUẬN:** thích nghi theo ảnh đã có tiền lệ. So với AnomalyCLIP phải đối chiếu tập huấn luyện/protocol; paper ghi sự khác biệt thời điểm/code ở phép so phụ lục. Ít epoch không đồng nghĩa vừa VRAM Seminar. Chưa có kiểm tra nguy cơ đa ngành độc lập nguồn.

### R09 — AnomalyDINO

**ĐÃ KIỂM CHỨNG:** §3–4, Appendix C, Figure 13 caption: đặc trưng DINOv2, ghép patch gần nhất với bộ nhớ ảnh normal; lọc nền/PCA và biến đổi xoay. MVTec/VisA, image/pixel AUROC. ViT-S 21M, 448/672 pixel; khoảng 60 ms ở cấu hình 448 trên A40. Ba lần chọn tham chiếu theo thứ tự tập, không tự gọi là ba seed ngẫu nhiên.

**SUY LUẬN:** baseline mạnh ít huấn luyện. Bất biến xoay có thể xóa lỗi bố trí; tác giả minh họa trường hợp transistor. Hiệu quả bộ nhớ phụ thuộc normal tham chiếu tương thích, không xác nhận độc lập nguồn.

### R10 — INP-Former

**ĐÃ KIỂM CHỨNG:** §3–4, bảng ablation và phụ lục limitation: truy vấn học được trích prototype (mẫu đặc trưng đại diện) bình thường trong ảnh, decoder (bộ giải mã) tái tạo với ràng buộc nhất quán. DINOv2-R ViT-B/14; sáu prototype, tám lớp decoder, 200 epoch; README ghi RTX4090 24 GB. MVTec/VisA/Real-IAD.

**SUY LUẬN:** normal prototype không phải phát minh mới cho SafeShift. Phụ lục thừa nhận bất thường logic có thể được coi là prototype bình thường; zero-shot phân loại ảnh không luôn thắng. 200 epoch trên benchmark không phải dự toán cho ảnh công nghiệp mới.

### R12 — LayoutAD

**ĐÃ KIỂM CHỨNG:** PDF tác giả §3–4, Tables 1 và ablation: đồ thị ngữ nghĩa/hình học, GATv2, tương tác chéo và mật độ Gaussian có điều kiện để chấm lệch thuộc tính/quan hệ. COCO-AD có 1.033 ảnh bất thường sinh bằng Qwen-Image từ COCO; RTX4090, ảnh 640, 30 epoch. Image AUROC 0,586 so baseline tốt nhất 0,573; pixel AUROC 0,871.

**SUY LUẬN:** đã có kiến trúc học quan hệ để phát hiện bố trí bất thường. Điểm pixel cao không làm image discrimination mạnh; dữ liệu sinh về bố trí không xác nhận nguy cơ công nghiệp. P1 phải khác cơ chế này, không chỉ đổi tên nút/cạnh.

### R13 — LogicQA

**ĐÃ KIỂM CHỨNG:** §3, §5.1–5.2, Table 1: mô tả ba ảnh normal cùng định nghĩa normality cho trước; sinh câu hỏi, phân rã câu hỏi và tổng hợp trả lời. Đánh giá logical anomaly trên MVTec LOCO và SEM riêng; GPT-4o, Gemini1.5-Flash, InternVL2.5-38B; lặp ba lần.

**SUY LUẬN:** “annotation-free” không có nghĩa không cần tri thức chuẩn. Sinh bộ câu hỏi/luật rồi bỏ phiếu đã có; chưa thành đóng góp kiến trúc học mới. SEM riêng và API gây hạn chế tái lập; GPU/chi phí đầy đủ chưa xác minh. Không dùng câu trả lời tự sinh làm nhãn chuẩn của P1.

### R14 — InCTRL

**ĐÃ KIỂM CHỨNG:** §3, §4.1–4.3, Table 3: học sai khác toàn ảnh và patch so với ảnh normal tham chiếu, kết hợp nhánh văn bản; encoder CLIP cố định, huấn luyện phụ trợ có nhãn. Chín bộ công nghiệp/y tế/ngữ nghĩa; RTX3090, 10 epoch, batch48 (48 mẫu mỗi bước). Ablation tách nhánh text/patch/image.

**SUY LUẬN:** “so với normal rồi học residual” đã được làm. Few-shot tham chiếu đích không cùng điều kiện với zero-shot không ảnh đích. Dữ liệu và ảnh tham chiếu cần cân bằng khi so P2; hiệu quả trên bệnh học/defect không tự chuyển sang quan hệ nguy cơ.

### R15 — IDEAL

**ĐÃ KIỂM CHỨNG:** §4.1–4.4, §5.1–5.3, Eq.1–6, Table3, Appendix D: normal và anomaly tham chiếu; PCA cục bộ loại biến thiên normal, cross-attention (chú ý chéo) học hướng sai khác. Dùng cả mask anomaly; encoder ViT-S/14 cố định, 448 pixel, 20 epoch, batch16, RTX3090. Tám bộ; ba lượt, “Hard” loại kiểu anomaly đã chọn làm tham chiếu. Có ablation NVE/IDE.

**SUY LUẬN:** chặn trực tiếp tính mới đơn giản của P2. Không coi hơn baseline normal-only là thuần lợi ích kiến trúc vì được thêm nhãn anomaly. Preprint; chưa audit code hay chuyển sang nguy cơ cùng nguồn.

### R17 — VL2V-ADiP

**ĐÃ KIỂM CHỨNG:** §4–6, Appendix B–C, Algorithm1/Table7: căn chỉnh projection (lớp chiếu), cố định nó để distill (chuyển tri thức) sang encoder thị giác, dự đoán bằng biểu diễn nhãn văn bản. OfficeHome, TerraIncognita, VLCS, PACS, DomainNet; độ chính xác ngoài miền, có ba lượt bổ sung ngoài seed0 của bảng chính.

**SUY LUẬN:** distillation từ VLM sang mô hình nhỏ và giữ khả năng ngoài miền đã có tiền lệ. Năm benchmark không chứng minh transfer (chuyển giao) an toàn công nghiệp. GPU/giờ huấn luyện chưa xác minh; không đề xuất “VLM teacher + student nhỏ” như kiến trúc mới chỉ vì đổi dữ liệu.

### R25 — CF-GAP

**ĐÃ KIỂM CHỨNG:** §3–5, Tables 1–4: bản đồ tìm kiếm thô theo ảnh mẫu đối tượng, quan sát log-polar (tọa độ cực logarit) để tinh chỉnh, rồi detector. HR-InsDet/Robotools; AP/khả năng tìm đối tượng, có ablation vị trí và quan sát tinh. Đối chứng quét lưới dùng 165 vùng so 30 vùng CF-GAP; không phải so bằng ngân sách. GPU/code chưa xác minh.

**SUY LUẬN:** phóng to chủ động đã có, không đủ mới cho P3. Tác vụ tìm một vật thể có mẫu khác tìm nguy cơ chưa biết. P3 cần đối chứng cùng ngân sách và lý do cơ chế ngoài attention/chọn crop thông thường.

## Ba công trình gần nhưng phạm vi đọc còn giới hạn

| Công trình | Điều đã kiểm tra | Phần chưa thể dùng làm kết luận sâu |
| --- | --- | --- |
| R05 EGVLR | Trang tác giả và Supplement §1–3/Table S1: Qwen3-VL-8B; học định vị bằng ảnh tổng hợp, học hỏi–đáp tri thức, ưu tiên theo phần thưởng hình học/ngữ nghĩa; mask ngoài để hiển thị. Bảng trang tác giả MMAD trung bình 81,35 vs 74,62, nhưng anomaly discrimination 66,66 vs 69,75. | Không suy mọi tác vụ cải thiện từ trung bình. Chưa đọc đủ main PDF, xác minh tài nguyên huấn luyện hoặc khoảng cách paper–code; “GS-DPO” trong phụ lục mô tả tối ưu kiểu GRPO, không tự đồng nhất với DPO chuẩn. |
| R11 ObjectCore | Phần mở đầu PDF được lập chỉ mục và trang lab: biểu diễn đối tượng, bộ nhớ cấu trúc/logic, ghép đối tượng; LOCO/CAD-SD, 4-shot. | Tài nguyên, chi tiết huấn luyện detector, ablation và code thực thi chưa xác minh. Dùng làm đối thủ phải kiểm tra, không làm chứng cứ rằng đồ thị P1 chắc chắn thất bại. |
| R03 PowerXGraph++ | Trang nhà xuất bản xác nhận tiêu đề, ngày 11/09/2026 và chủ đề đồ thị bằng chứng/giải thích phản thực cho an toàn công trường điện. | Toàn văn chưa lấy được; dataset, GPU, split, định nghĩa phản thực và đóng góp riêng chưa xác minh. Đây là blocker kiểm tra tính mới P1, không phải chứng cứ kết quả đã tái lập. |

## So sánh các cơ chế gần nhất

**SUY LUẬN từ các hồ sơ trên; không phải xếp hạng số điểm.**

| Câu hỏi SafeShift | Đã có | Khác biệt còn phải chứng minh | Đối chứng tối thiểu |
| --- | --- | --- | --- |
| P1: thiếu vật bảo vệ hay không quan sát được? | Quan hệ/bố trí, quy tắc hỏi–đáp, căn cứ vùng | Biến quan sát và điều kiện áp dụng thật sự thay đổi truyền bằng chứng, vượt mô hình quan hệ thông thường | Đặc trưng cố định; luật; đồ thị cùng nhãn/encoder; P1 bỏ từng thành phần |
| P2: khác nền hay khác trạng thái nguy cơ? | So normal, khử biến thiên normal, học hướng residual | Tính so sánh được/ghép vai trò có lợi ích ngoài IDEAL/InCTRL | Cùng nhãn và tham chiếu; ghép gần nhất; IDEAL; bỏ bộ lọc |
| P3: cần đọc thêm vùng nào? | Chọn token, tìm vùng thô–tinh theo mục tiêu | Chính sách theo thiếu bằng chứng hơn saliency/entropy/ngẫu nhiên tại cùng chi phí | Lưới; ngẫu nhiên; saliency; CF-GAP thích nghi; oracle |

Không có paper nào trong tập đã đọc cung cấp bằng chứng trực tiếp rằng một trong ba phương án sẽ thắng trên InspecSafe với nguồn độc lập. Các tiền lệ làm yêu cầu tính mới cao hơn; chúng không chứng minh bài toán không thể giải được.
