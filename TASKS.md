# W1 — Dataset Audit

Mục tiêu: khảo sát, kiểm tra và hiểu InspecSafe-V1 trước bất kỳ thí nghiệm VLM nào. Các checkbox chưa đánh dấu là việc cần làm, không phải kết quả đã có.

## 0. Khởi tạo repository

- [x] Tạo cấu trúc thư mục và tài liệu nền tảng.
- [x] Thiết lập quy tắc quản lý dữ liệu, reproducibility và `.gitignore`.

## 1. Xác minh nguồn và quyền sử dụng

- [x] Xác định nguồn phát hành chính thức và tài liệu đi kèm InspecSafe-V1; ghi URL, ngày truy cập và version/release nếu có. Đã xác minh: Hugging Face (`Tetrabot2026/InspecSafe-V1`, commit `f3cb7d3e`), Zenodo (`10.5281/zenodo.19885643`, v1.0.1), GitHub (`liuzy0708/InspecSafe`), ấn phẩm tạp chí chính thức Scientific Data (Vol 13, Art 1198, DOI: 10.1038/s41597-026-07796-x) và bản thảo lưu trữ arXiv:2601.21173 (Zeyi Liu, Xiao He et al., 2026). Tài liệu chi tiết: `notes/source_license_audit.md`.
- [x] Đọc license, điều kiện truy cập, quyền dùng/chia sẻ ảnh, annotation và ví dụ trong paper; ghi lại các ràng buộc hoặc thông tin chưa rõ. Đã xác minh: Dataset phát hành dưới CC-BY-4.0 (cho phép học thuật và thương mại với attribution; SafeShift policy giới hạn phi thương mại); paper tách riêng license (Scientific Data: CC BY-NC-ND 4.0, arXiv: Non-exclusive); sample images từ dataset (CC-BY-4.0) phân biệt với figures bài báo (CC BY-NC-ND 4.0); raw dataset bị cấm redistribute theo policy SafeShift; model weights là NOT_SPECIFIED / separate review. Rights Matrix và reconciliation 2239 vs 3234 sites, 234 vs 231 nhãn: `notes/source_license_audit.md`.
- [x] Ghi cách lấy dữ liệu local, tên archive và checksum nếu có; không đưa archive hoặc credentials lên Git. Đã ghi rõ: dữ liệu máy hiện tại khôi phục từ backup `D:\SafeShift.zip` vào `data/raw/InspecSafe-V1/`; fingerprint SHA-256 nội bộ `1a52f907...` khớp bản audit cũ; tệp nén local nhất quán với bản phát hành Hugging Face (kích thước `train.tar.gz` 17.886.855.594 bytes và `test.tar.gz` 5.748.799.871 bytes) nhưng tính toàn vẹn byte-level độc lập chưa được hash đối soát trực tiếp; toàn bộ archives được ignore, không đưa lên Git.

## 2. Kiểm kê dữ liệu local

- [x] Đặt dữ liệu trong `data/raw/InspecSafe-V1/` theo `data/README.md`; giữ nguyên cấu trúc gốc.
- [x] Khảo sát cây thư mục, tài liệu, định dạng ảnh và annotation thực tế; ghi nhận encoding, quy tắc đặt tên và liên kết ảnh–annotation.
- [x] Kiểm đếm file, kích thước, sample ID, ảnh và annotation theo split/nhãn/domain nếu các trường này tồn tại; ghi mẫu số rõ ràng cho từng thống kê.
- [x] Xây dựng Dataset Manifest Builder với validation và tests synthetic; tạo CSV/checksum local dùng relative path, không nhúng ảnh. Đã hoàn thiện 24 opening theo audit bổ sung; kiểm chứng 5.013 rows và 29 tests pass, unknown_text_domain = 0, domain_mismatch = 36, ma trận domain khớp audit và full run exit 0, không có discrepancy. Lệnh, kết quả và giới hạn: `notes/manifest_builder.md`. CSV chứa toàn văn TXT nên giữ local, không commit.

## 3. Hiểu schema và ý nghĩa nhãn

- [x] Đọc annotation mẫu và tài liệu; mô tả field, kiểu dữ liệu, giá trị thiếu và đơn vị.
- [x] Xác minh định nghĩa nhãn an toàn/nguy cơ, multi-label nếu có, và đơn vị annotation thực tế: ảnh, đối tượng, vùng hoặc đơn vị khác.
- [x] Xác minh sample ID, split và quy tắc ánh xạ ảnh–annotation; ghi ví dụ nhỏ chỉ khi được phép chia sẻ.
- [x] Ghi mọi trường hợp mơ hồ cần hỏi người phụ trách; không tự diễn giải thành định nghĩa chính thức.

## 4. Kiểm tra chất lượng và nguy cơ leakage

- [x] Kiểm tra file hỏng/không đọc được, ảnh thiếu annotation, annotation thiếu ảnh, ID trùng và giá trị không hợp lệ. Validation W1 Bước 3: 66/66 tests synthetic pass; full 5.013 samples, verify/decode ảnh và kiểm tra imageData, exit 0, không ERROR. Có 309 polygon vượt bounds, 5.013 imagePath mismatch và 94 imageData byte mismatch được giữ WARNING; không sửa/loại mẫu. Kết quả, provenance và discrepancies tài liệu: `notes/dataset_validation.md`; JSON chi tiết giữ local.
- [x] Kiểm tra exact duplicates và near-duplicates trong/giữa split; ghi phương pháp, ngưỡng và hạn chế nếu sử dụng đối sánh gần đúng. W1 Bước 4: full 5.013 samples, exit 0, fingerprint khớp validation; 107/107 tests pass. Có 53 byte/pixel-exact pairs, gồm 7 cross-split; dHash <=8 có 833 cross-split pairs (7 exact + 826 nonexact candidates). Methods, MAE/consecutive calibration, limitations và W2 review: `notes/duplicate_leakage_audit.md`; full pair report giữ local, không sửa/loại mẫu.
- [x] Kiểm tra khả năng cùng cảnh, nguồn, video hoặc chuỗi ảnh xuất hiện ở nhiều split nếu metadata cho phép. Đã audit toàn bộ 5.013 imagePath strings/basenames và strict embedded imageData; point-ID overlap = 0, imagePath/basename duplicate groups = 0, có 12 cross-split source-family candidate groups theo regex hẹp. Targeted visual & provenance review (Bước 5) xác nhận STRONG EVIDENCE rò rỉ chuỗi video và góc máy robot xuyên split; tài liệu chi tiết: `notes/duplicate_leakage_audit.md` và `notes/visual_provenance_review.md`.
- [x] Thống kê phân bố nhãn, độ phân giải, thiếu metadata và mất cân bằng; không sửa hoặc loại mẫu khỏi dữ liệu gốc. W1 Bước 6: full 5.013 samples, 26 regression checks khớp, fingerprint khớp manifest Bước 2, exit 0; 143/143 tests synthetic pass. Có 66 resolutions, 37.434 shapes/231 raw labels, 15 Level03, metallurgy test 0 anomaly, 65 train-only/24 test-only labels, 36 folder/text mismatch. Cross-tables, TVD mô tả, metadata và giới hạn W2: `notes/distribution_imbalance_audit.md`; full JSON giữ local. Chưa chốt metric/protocol hoặc đánh dấu research feasibility/W1 complete.

## 5. Đánh giá khả năng nghiên cứu SafeShift

- [x] Kiểm tra có domain metadata nào: nguồn, địa điểm, môi trường, camera hoặc loại ngành; tách field gốc khỏi domain suy luận/đề xuất. Đã kiểm kê và phân loại toàn diện 12 trường metadata: tách bạch giữa metadata gốc (`OBSERVED_ORIGINAL_METADATA` như JSON `imagePath`), metadata suy ra xác định (`DETERMINISTIC_DERIVED_METADATA` như `folder_domain`, `text_domain`, `robot_platform`, `point_id`), heuristic suy luận (`HEURISTIC_INFERRED_METADATA` như 12 source families), suy từ ảnh (`VISUALLY_INFERRED` như góc máy camera), và trường không có sẵn (`UNAVAILABLE` như tọa độ waypoint/inspection site thực tế); xác nhận 36 mẫu xung đột giữa thư mục và văn bản. Tài liệu chi tiết: `notes/research_feasibility_audit.md`.
- [x] Đánh giá khả năng thiết kế cross-domain split và rủi ro confounding; chưa tự tạo hoặc thay split chính thức. Đã đánh giá ma trận khả thi 5 miền công nghiệp và 5 protocol ứng viên: xác nhận rủi ro confounding nghiêm trọng giữa miền và nền tảng robot (coal_conveyor 100% ray treo, metallurgy/oil_chemical >90% bánh lăn), phân bố nhãn lệch (Level03 chỉ có 15 mẫu, metallurgy test có 0 mẫu Anomaly), và rò rỉ chuỗi video xuyên split chính thức; phán quyết Cross-domain analysis là `FEASIBLE_WITH_CONSTRAINTS`, Standard Domain Generalization trên split chính thức là `NOT_CURRENTLY_FEASIBLE / NOT SUITABLE AS-IS` (custom group-aware split là `PARTIALLY_FEASIBLE`); khuyến nghị thuật ngữ `Cross-Domain Robustness` cho mô hình frozen pretrained VLM ở W2. Chi tiết: `notes/research_feasibility_audit.md`.
- [x] Xác minh loại evidence annotation thực sự có: bounding box, mask, vùng, mô tả, hoặc không có; không mặc định dataset có nhãn grounding. Đã xác minh thực tế toàn bộ 37.434 đa giác và 231 nhãn thô là object polygon annotations (polygon instance annotations), không phải Hazard Evidence Annotations; dataset có polygon, không có native bounding-box ground truth; dataset KHÔNG có sẵn bounding boxes gốc, binary masks, hazard-specific evidence regions, human rationale regions, phrase-to-region alignments, evidence-to-safety-level mappings, hay absent-object annotations; phân biệt rạch ròi đa giác vật thể (như `Person`) không phải là ground truth trực tiếp cho nguy cơ thiếu hụt (như không đội mũ bảo hộ). Chi tiết: `notes/research_feasibility_audit.md`.
- [x] Ghi giới hạn đánh giá evidence grounding và nhu cầu annotation bổ sung nếu có; metric để chốt ở W2. Đã thẩm định chuyên sâu tập mẫu phân tầng xác định gồm 63 mẫu Anomaly: trong tập 63 mẫu này (in the reviewed subset), 13 mẫu (20,6%) có Direct Support từ vật thể hiện hữu, 46 mẫu (73,0%) hỗ trợ qua Weak Proxy (`Person`), 4 mẫu (6,3%) không có hỗ trợ trực tiếp hoặc mơ hồ; không ngoại suy sang toàn bộ dataset; phán quyết Grounding với nhãn hiện tại là `PARTIALLY_FEASIBLE` (chỉ khả thi ở Cấp độ A: Object Support subset sau census và Cấp độ B: Weak Proxy), Full Hazard Rationale Grounding là `NOT_CURRENTLY_FEASIBLE` nếu không có chiến dịch gán nhãn bổ sung; xác nhận dataset chưa đủ ground truth để kiểm tra khách quan hiện tượng "Correct Answer, Wrong Reason"; chốt các candidate metric families và 6 khuyến nghị hành động cho W2. Chi tiết: `notes/research_feasibility_audit.md`.

## 6. Khảo sát trực quan và báo cáo

- [x] Chọn mẫu khảo sát có phương pháp được ghi rõ (và seed nếu ngẫu nhiên), bao phủ nhãn/domain/split hiện có và các trường hợp lỗi. W1 Bước 5: chọn mẫu khảo sát có phương pháp gồm toàn bộ 7 cross-split exact pairs, 12 cross-split source families (bao trùm 1.000 mẫu Anomaly), và 50 candidate pairs phân tầng (Top 20 dHash/MAE, 15 Same-Family, 10 Different-Family, 5 Domain-Coverage). Tài liệu: `notes/visual_provenance_review.md`.
- [x] Xem ảnh cùng annotation để kiểm tra ý nghĩa nhãn, bối cảnh và tính nhất quán; chỉ lưu figure được phép chia sẻ. W1 Bước 5: hoàn thành quy trình blind-first visual review cho 7 exact pairs (phát hiện xung đột nhãn trực tiếp Cấp 1 vs Cấp 2, metallurgy vs oil_chemical, găng tay vs hút thuốc), 12 cross-split source families có systematic ~25/75 index partition; visual review xác nhận shared-sequence evidence ở nhiều sampled cases, và 50 near candidates (Normal waypoint cố định vs Anomaly video slicing ở các ca được kiểm tra). Bằng chứng đầy đủ: `notes/visual_provenance_review.md`.
- [x] Viết `notes/w1_dataset_audit.md` với nguồn dữ liệu, phương pháp, thống kê đã kiểm chứng, phát hiện chất lượng, hạn chế và câu hỏi cho W2. Đã hoàn thành báo cáo tổng hợp toàn diện Week 1 (16 mục chuẩn hóa), tích hợp toàn bộ các phát hiện đã xác minh từ Bước 1–8: 5.013 mẫu, 5 miền, 37.434 đa giác/231 nhãn, giấy phép CC-BY-4.0, 7 cặp exact rò rỉ, 833 dHash<=8 screening pairs (7 exact + 826 candidates), 36 domain mismatch, phân tích platform confounding, phán quyết feasibility cross-domain và grounding, 10 unresolved questions, 10 quyết định W2 queue; tài liệu: `notes/w1_dataset_audit.md`.
- [x] Lưu figure nhỏ được phép chia sẻ trong `outputs/figures/`; giữ artifact lớn ở local. Đã tạo 3 figure nhỏ (<35 KB mỗi file) dẫn xuất thuần túy từ số liệu thống kê đã kiểm chứng: `outputs/figures/w1_domain_distribution.png` (phân bố 5 miền Normal vs Anomaly), `outputs/figures/w1_safety_distribution.png` (mất cân bằng 4 cấp độ an toàn Level 01–04), và `outputs/figures/w1_platform_by_domain.png` (nhiễu nền tảng SuspendedRail vs Wheeled theo miền); script tái lập: `scripts/plot_w1_audit_figures.py`; toàn bộ artifact JSON/CSV lớn và raw images được giữ local theo `.gitignore`.
- [x] Ghi các lệnh, môi trường, checksum và đường dẫn artifact để người khác có thể tái lập audit; code dùng lại được bổ sung sau phải có test. Đã ghi nhận đầy đủ môi trường kiểm chuẩn (Python 3.11.9, Pillow 12.3.0, Windows x64), fingerprint đầu vào `1a52f907...`, exact CLI commands cho toàn bộ 5 công cụ kiểm toán, mã băm SHA-256 của các local artifacts đã được hash, và bổ sung test tự động `tests/test_figures.py` nâng tổng số kiểm thử lên 145/145 tests pass (0 failed); tài liệu chi tiết tại Mục 15 của `notes/w1_dataset_audit.md`.
- [x] Rà soát checklist và điều kiện chuyển giai đoạn trong `ROADMAP.md` trước khi đánh dấu W1 hoàn thành. W1 audit package ready for independent review before W2. Báo cáo tổng hợp `notes/w1_dataset_audit.md` đã đáp ứng đầy đủ điều kiện cổng kiểm soát W1 -> W2: có báo cáo audit truy vết nguồn gốc, danh sách 10 điểm chưa rõ (unresolved), phán quyết khả thi thực chứng cho cross-domain (FEASIBLE_WITH_CONSTRAINTS) và evidence grounding (PARTIALLY_FEASIBLE), cùng hàng đợi 10 quyết định W2; trạng thái cổng: READY_FOR_REVIEW.

**Ngoài phạm vi bước khởi tạo:** code parse dataset, inference VLM, chọn metric chính thức và tuyên bố kết quả nghiên cứu.

## W2 — Pre-freeze implementation (2026-09-18)

Historical D8 evidence. The original completion/pending statements below describe
their recorded milestones; the active P2 prerequisites are now the D9 checklist below.

- [x] Triển khai hạ tầng offline theo D8 đã duyệt: Call 1/Call 2 độc lập, canonical schema, raw preservation, bốn adapter skeletons, external gate harness, benchmark firewall, D5 interfaces và freeze-manifest template. Kiểm thử: 199/199 tests pass, gồm 54 tests mới. Chi tiết và 8 prerequisite: [notes/pre_freeze_implementation.md](notes/pre_freeze_implementation.md).
- [ ] Hoàn tất 8 prerequisite D8 trước protocol freeze: endpoint/decoding Qwen, external cases và gates, final roles, live model/route verification, đóng băng toàn bộ implementation và ghi freeze SHA. `protocol_freeze_commit_sha: PENDING`; chưa chạy inference InspecSafe.
- [x] Pre-freeze steps 1–2 (2026-09-19): pin Qwen Singapore workspace route policy and documented P2 `temperature = 0` configuration; checklist #2 DONE. Checklist #1 remains PENDING_USER_CONFIGURATION because neither workspace environment variable is set locally. Offline validator and full repository tests: 233/233 PASS. No live route verification, gates or inference. Evidence: [notes/pre_freeze_implementation.md](notes/pre_freeze_implementation.md).

### D9 status overlay on historical provider work

| Historical D8 item | Current P2 status | Retained evidence |
|---|---|---|
| Qwen Singapore workspace endpoint (#1) | `SUPERSEDED_FOR_P2_BY_D9` | Historical `PENDING_USER_CONFIGURATION`; route policy and offline validator retained. |
| Qwen hosted decoding (#2) | `SUPERSEDED_FOR_P2_BY_D9` | Historical `DONE`; hosted temperature-zero policy is not self-hosted validation. |
| GPT/Claude hosted capability gates (#4) | `SUPERSEDED_FOR_P2_BY_D9` | Both `NOT RUN`; D9 models require their own capability review. |
| Commercial provider billing/access setup | `SUPERSEDED_FOR_P2_BY_D9` | No paid inference or billing completion claimed; GPU access/license review remains pending under D9. |
| Provider live-route verification (#6) | `SUPERSEDED_FOR_P2_BY_D9` | Historical live route remains false; no successful API access claimed. |

The historical eight-item D8 checklist is no longer the active P2 checklist.
SYNTHETIC V1 external assets (#3) remain DONE and unchanged; final roles, full
implementation freeze and protocol freeze (#5/#7/#8) remain pending under D9.
This supersession does not change P1 upstream reproduction or its access requirements.

## W2 — Active D9 pre-freeze checklist (2026-09-20)

Authority: [DEC-W2-D9-009](DECISIONS.md#dec-w2-d9-009--p2-open-weight-self-hosted-model-roster)
and the [D9 brief](notes/w2_open_weight_self_hosted_model_roster_decision_brief.md).
This is the **active P2 checklist**, mirrored in
`configs/pre_freeze/local_models.d9.json` and `configs/pre_freeze/freeze_manifest.d9.template.json`.
Documentation synchronization does not complete any execution prerequisite.

- [x] Synchronize the D9 decision ledger, checklist, implementation note and two
  configuration templates; preserve historical D8 evidence and SYNTHETIC V1 assets.
- [ ] **1. Model provenance:** Freeze exact IDs and immutable revisions, access/license
  evidence and weight provenance for the four primary candidates and ordered backups.
- [ ] **2. Runners:** Implement and validate local/self-hosted runners with explicit
  preprocessing, precision/quantization, device/software versions and raw-output
  preservation before parsing. Deferred; no runners implemented in this task.
- [ ] **3. Decoding:** Pin one supported low-variance configuration per model;
  no selection from InspecSafe outputs and no automatic reuse of hosted settings.
- [ ] **4. Adapters/parsers:** Validate deterministic native-output conversion to the
  unchanged canonical box schema. Preserve point-only outputs as raw evidence, never
  fabricate boxes; native-point-only grounding is not an approved D5 track.
- [ ] **5. External gate:** Resolve interface eligibility for all four primary
  candidates and run the unchanged eight-case SYNTHETIC V1 gate on qualifying box
  interfaces. Fix the qualitative giant-box review procedure before execution;
  record point-only incompatibility as nonparticipation, not PASS or a zero score.
  Any activated backup must meet the same prerequisites and gate before freeze.
- [ ] **6. Final roles:** Assign classification/grounding roles and record any allowed
  backup substitution before protocol freeze and before any InspecSafe inference.
- [ ] **7. Implementation freeze:** Complete and freeze exact prompts/task policy,
  canonical schema, adapters/parsers, runner environment and full unchanged D5 engine.
- [ ] **8. Protocol freeze:** Record the approved freeze commit only after all
  prerequisites are complete. **`protocol_freeze_commit_sha: PENDING`**.

Seminar remains frozen zero-shot cross-domain robustness evaluation; no training or
fine-tuning. P1 remains unchanged. D8 Benchmark Firewall, C1, A2, B2, raw preservation,
capability-aware grounding, D5 metrics/statistics and post-freeze change control remain
binding. No model/provider calls, weight downloads or InspecSafe image inspection
are part of this synchronization. **NO_INSPECSAFE_INFERENCE**.
