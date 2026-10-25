# Nhật ký nguồn và tìm kiếm — 25/10/2026

Phục vụ [báo cáo](NEW_MODEL_FEASIBILITY_20261025.md) và [bản đồ bằng chứng](NEW_MODEL_EVIDENCE_20261025.md). Đây là khảo sát định hướng quyết định, **không phải systematic review (tổng quan hệ thống) đầy đủ** và không chứng nhận tính mới toàn cục.

## Phạm vi và cách chọn

- Câu hỏi: có cơ chế học mới nào cho ảnh an toàn công nghiệp, đủ khác tiền lệ và khả thi với dữ liệu/tài nguyên SafeShift để đáng xem xét Seminar→Khóa luận?
- Mốc tài liệu: công trình có thể xác minh đã xuất hiện đến **25/10/2026**; ưu tiên 2024–2026, bổ sung nền tảng trực tiếp cần thiết.
- Truy xuất bằng công cụ tìm web, mở arXiv HTML/PDF, CVF/ECVA/OpenReview/PMLR, trang nhà xuất bản/tác giả; đọc repo qua GitHub connector. Không tải dataset/model hay thực thi code ngoài.
- Giữ 25 công trình chính trong bảng; 13 hồ sơ đọc sâu. Phiên bản preprint/kỷ yếu hoặc phần mở rộng cùng họ không được đếm như tái lập độc lập.
- Điều kiện giữ: liên quan trực tiếp bài toán, cơ chế cạnh tranh, baseline tiết kiệm tài nguyên hoặc tính hợp lệ đánh giá. Không chọn bằng số trích dẫn hay chỉ bằng kết quả tốt.
- Đọc sâu ưu tiên phương pháp, thông tin được phép dùng khi học/đánh giá, phần chia, tài nguyên, ablation và giới hạn; định vị cụ thể nằm trong hồ sơ. Metadata/code chưa truy cập được ghi rõ.
- Không có tổng số kết quả truy vấn hay coverage toàn bộ chỉ mục được công cụ bảo đảm. Không dựng sơ đồ PRISMA, tỷ lệ sàng lọc, hay nói “không có công trình nào” từ các trang kết quả hữu hạn.

## Kỹ năng được tham khảo theo yêu cầu

Các skill (hướng dẫn công việc) là hướng dẫn quy trình, **không phải bằng chứng khoa học** cho mô hình.

| Nguồn SKILL.md đã đọc | Git blob SHA của file tại lúc đọc | Phần áp dụng |
| --- | --- | --- |
| [LIU-31415/codex-research](https://github.com/LIU-31415/codex-research/blob/main/SKILL.md) | `ad8ec0a3eca79dd8824bb102f3b7e54e478a49d1` | Tìm theo khoảng trống; đối chiếu bản gốc; tách truy cập thiếu khỏi bằng chứng âm; gắn nhận định với nguồn. |
| [scientific-brainstorming](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-brainstorming/SKILL.md) | `487a1a0e31c6bf270b3e80818798bab9b4ebc0b9` | Phát triển phương án cơ chế khác nhau; tìm đối thủ gần trước khẳng định tính mới. |
| [scientific-critical-thinking](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-critical-thinking/SKILL.md) | `2a2fc151b5b13e4e11ece7410f21a14d5b25e30d` | Phản biện giả thuyết, nhiễu nguồn/nhãn, phân biệt tương quan và nhân quả, không nâng mức kiểm chứng. |
| [experimental-design](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/experimental-design/SKILL.md) | `ee14f9ed795c791ac80e3ea946858d97d09c3e50` | Xác định đơn vị độc lập, nhóm nguồn, đối chứng công bằng, điều kiện bác bỏ và nguy cơ pseudoreplication (đếm mẫu phụ thuộc như độc lập). |

Chỉ đọc thêm tài liệu cần thiết của codex-research: [source-safety](https://github.com/LIU-31415/codex-research/blob/main/references/source-safety.md), [search-strategy](https://github.com/LIU-31415/codex-research/blob/main/references/search-strategy.md), [fulltext-reading](https://github.com/LIU-31415/codex-research/blob/main/references/fulltext-reading.md), [evidence-reasoning](https://github.com/LIU-31415/codex-research/blob/main/references/evidence-reasoning.md), [synthesis-and-research-design](https://github.com/LIU-31415/codex-research/blob/main/references/synthesis-and-research-design.md), [academic-writing](https://github.com/LIU-31415/codex-research/blob/main/references/academic-writing.md). Không cài skill/dependency, chạy script kèm skill hoặc thiết lập dịch vụ. Ghi nhận nguồn thư viện theo hướng dẫn K-Dense: [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents, preprint 2026](https://arxiv.org/abs/2609.00065); chỉ là attribution (ghi công) phương pháp làm việc.

## Chuỗi tìm kiếm

Bảng sau là các **nhóm truy vấn định hướng** và kết quả đưa vào bản đồ, không phải bản chép toàn bộ lịch sử công cụ:

| Nhóm | Từ khóa/phạm vi | Kết quả chính |
| --- | --- | --- |
| An toàn công nghiệp | industrial safety recognition, industrial inspection VLM, 2024/2025/2026 | InspecSafe, SteelBench, O-VAD; mở sang đồ thị an toàn và grounding |
| Bất thường hình ảnh | visual anomaly detection, few-shot, logical anomaly, CLIP, DINO, CVPR/ECCV/WACV | EfficientAD, AnomalyCLIP, AdaCLIP, AnomalyDINO, INP-Former, ObjectCore, LayoutAD, LogicQA |
| So tham chiếu | in-context residual learning, normal references, nuisance variation | InCTRL; truy vấn cơ chế bổ sung tìm được IDEAL, làm yếu P2 |
| Miền và mô hình nhỏ | domain generalization, vision-language distillation, MobileCLIP | VL2V-ADiP, DomainBed, Forgotten DG, MobileCLIP |
| Định vị và khái niệm | visual grounding, local alignment, concept bottleneck | Grounding DINO, LaZSL, CBM, EGVLR |
| Chọn quan sát | token sparsification, coarse-to-fine, active perception, budget | DynamicViT, CF-GAP; kiểm tra danh sách ECCV 2026 |

Các truy vấn đối chiếu cơ chế **nguyên văn đã chạy**, ngày 25/10/2026:

1. `"visibility" "missing evidence" "scene graph" anomaly detection safety`
2. `"anomaly detection" "reference" "nuisance" correspondence normal 2025 2026`
3. `"safety" "scene graph" "uncertainty" industrial visual 2024 2025 2026`
4. `"anomaly" "active perception" "budget" glimpse 2025 2026`
5. `"PowerXGraph++" "github"`
6. `"CF-GAP" "code" Kolner`
7. `"LogicQA" "github" anomaly`
8. `"VL2V-ADiP" github`

Truy vấn tác giả/venue bổ sung gồm `AnomalyGPT AAAI 2024 github author`, `PromptAD CVPR 2024 Learning Prompts Only Normal Samples github`, `In Search of Lost Domain Generalization ICLR 2021 DomainBed github`, `Domain Generalization in CLIP via Learning with Diverse Text Prompts 2025 github`. Tìm code không có kết quả đúng không đồng nghĩa tác giả không công bố code.

Không dùng nội dung diễn giải của blog/DeepWiki/trang tổng hợp làm bằng chứng phương pháp. Một số repo bên thứ ba mô tả VL2V-ADiP như giám sát ở thời điểm kiểm định; bản gốc Algorithm1 cho thấy học căn chỉnh/chuyển tri thức trước, nên không sử dụng diễn giải đó.

## Đầu mối bổ sung và giới hạn truy cập

- [PromptAD, CVPR 2024](https://arxiv.org/abs/2404.05231): đã thấy bảng kết quả/ablation PDF được lập chỉ mục, [code tác giả](https://github.com/FuNz-0/PromptAD); thêm lời nhắc học từ normal không được coi là ý tưởng mới. Không mở thêm thành hồ sơ chính vì đã có đủ đối thủ trực tiếp.
- [Scene Graph-Guided Generative AI Framework for Synthesizing and Evaluating Industrial Hazard Scenarios](https://arxiv.org/abs/2511.13970): preprint 2025, chỉ tóm tắt; không lấy tính hợp lý ảnh sinh làm bằng chứng tăng nhận diện nguy cơ thực.
- [Dynamic Risk Inference Method for Chemical Industrial Inspection Based on Spatio-Temporal Scene Graphs](https://doi.org/10.3390/s26134082): đầu mối 2026; toàn văn lỗi 429, chưa đánh giá cơ chế/GPU.
- [Data-driven safety management of worker-equipment interactions using visual relationship detection and semantic analysis](https://doi.org/10.1016/j.autcon.2025.106181): Automation in Construction 2025, đầu mối từ trang nhà xuất bản; chưa đọc đủ để kết luận kỹ thuật. Cần bổ sung nếu tiếp tục P1.
- [L-PromptCTRL, Digital Signal Processing 2026](https://www.sciencedirect.com/science/article/abs/pii/S1051200425008577): đầu mối gần học tham chiếu; chưa đọc toàn văn, không dùng để khẳng định cơ chế cụ thể.
- Một số PDF CVF trả 403: tìm bản arXiv/tác giả hợp pháp. LayoutAD đọc được PDF tác giả; ObjectCore chỉ có đoạn mở đầu được lập chỉ mục và trang lab. EGVLR đọc được phụ lục nhưng chưa đủ main PDF. Không coi những trường hợp này là đã đọc toàn văn.
- Tạp chí InspecSafe lỗi chuyển hướng đăng nhập; metadata được đối chiếu arXiv/repo tác giả và hồ sơ nguồn SafeShift. Số nguồn/cơ sở tác giả nêu không được biến thành số nhóm độc lập của bộ ảnh local.
- Các tài liệu về điều khiển robot, hành động/lái xe, ảnh y tế được xét để phân biệt cơ chế, không nhận làm bằng chứng trực tiếp cho an toàn ảnh tĩnh. Chưa khảo sát toàn bộ văn liệu kỹ thuật an toàn ngoài CV/ML hoặc mọi bài ra tháng 10/2026.

## Truy xuất SafeShift và giới hạn thực thi

Main được xác minh trực tiếp qua GitHub là `3bcd3535ea51e023de77417ed5f2077607d49c93`. Đã đọc AGENTS/README/docs ROADMAP của main và bốn tài liệu người dùng chỉ định; đọc DATA_AND_ETHICS để giữ phạm vi dữ liệu. ROADMAP/TASKS ở worktree cũ được đọc để tuân thủ hướng dẫn ban đầu; chúng không thay tài liệu main sau reset. Main AGENTS nêu hai file root này thuộc lịch sử, không tạo lại.

Chỉ tra lịch sử phân bố tại `31a04e6f7175cca818c63b4de0153246b3f3ecdb` để lấy bảng lớp/miền. Kết quả hiện hành và đối soát nguồn lấy từ các tài liệu main đã dẫn trong báo cáo. Không đọc toàn bộ repo, không mở TEST, không chạy GPU/inference, không tự tính lại kết quả mô hình.

Tài liệu được soạn ở `data/processed/independent_model_research_20261025/` để giữ nguyên worktree đang có thay đổi ngoài phạm vi; bản đưa lên nhánh nghiên cứu nằm ở `docs/research/`. Không mang file local khác sang branch mới. Không sửa D9R22, quyết định, roadmap, dữ liệu, metric hoặc trạng thái nghiên cứu chính thức.

Kiểm tra phù hợp trước giao: danh sách file/diff chỉ ba Markdown; liên kết nội bộ đích main; 25 ID duy nhất, 13 hồ sơ đọc sâu; phân biệt preprint/phạm vi đọc; số lớp/miền/cohort đối chiếu nguồn. Không chạy unit test (kiểm thử đơn vị) của phần mềm vì chỉ thêm tài liệu; không có tuyên bố tái lập thí nghiệm. Trạng thái branch/Draft PR và kết quả kiểm tra cuối được ghi ở mô tả PR.
