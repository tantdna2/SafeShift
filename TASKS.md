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

**D9R1 supersession (2026-09-24):** Current roster/resource policy is in
[W2.6-D9R1](notes/w2_d9_t4_roster_revision.md). The B0/B2/B3 milestones below
remain historical evidence; Ovis, Molmo and Gemma are no longer current primaries.

- [x] Synchronize the D9 decision ledger, checklist, implementation note and two
  configuration templates; preserve historical D8 evidence and SYNTHETIC V1 assets.
- [x] **1. Model provenance:** COMPLETE (W2.6B0 documentary scope): exact D9 IDs,
  immutable repository SHAs, official revision/weight metadata and separate
  license/access/caveat records for all four primaries and both ordered backups.
  `VERIFIED_DOCUMENTARY` is not protocol freeze, runtime validation or use clearance.
  PaliGemma access acceptance and documented usage caveats remain execution
  prerequisites. See [provenance and runner specification](notes/w2_model_provenance_runner_spec.md)
  and `configs/pre_freeze/local_model_provenance.d9.json`.
- [ ] **2. Runners:** Implement and validate local/self-hosted runners with explicit
  preprocessing, precision/quantization, device/software versions and raw-output
  preservation before parsing. W2.6A generic contracts/scaffolding and dummy unit
  tests are complete. Qwen offline runner implementation is **COMPLETE**;
  real Kaggle T4×2 runtime smoke is **PASS / VALIDATED** for run
  `kaggle-t4x2-20260923T012029667885Z`, per Research Lead's evidence-bundle audit.
  Ovis W2.6B2A offline runner implementation is **COMPLETE** after Research Lead
  review (`PASS_WITH_GOVERNANCE_CLEANUP`). Its W2.6B2B real single-A40 GPU runtime
  smoke is **PASS / VALIDATED** for run `ckey-a40-ovis-20260924T042034999220552Z`,
  per Research Lead's evidence-bundle audit; execution commit is
  `c2a5d97945b27d16425f82592a352722ee935118`.
  Ovis grounding is `DOCUMENTED_BOX_AND_POINT / NOT_YET_QUALIFIED`.
  Molmo W2.6B3A offline runner implementation is **COMPLETE** with fake-backend
  tests; real runtime remains **PENDING** for separate B3B validation.
  Molmo grounding is `DOCUMENTED_NATIVE_POINT / NOT_YET_QUALIFIED`;
  box/IoU participation is `NOT_PARTICIPATING`. Local weight bytes are not verified.
  Gemma runner/runtime work remains **PENDING**.
  See [W2.6A implementation](notes/w2_local_runner_contracts.md) and
  [Qwen offline implementation](notes/w2_qwen_runner_implementation.md).
  See the [audited smoke result](notes/w2_qwen_kaggle_smoke_result.md).
  See the [Ovis offline runner implementation](notes/w2_ovis_runner_implementation.md).
  See the [Ovis single-GPU BF16 smoke runbook](notes/w2_ovis_gpu_smoke_runbook.md).
  See the [audited Ovis runtime result](notes/w2_ovis_gpu_smoke_result.md).
  See the [Molmo offline runner implementation](notes/w2_molmo_runner_implementation.md).
  Qwen FP16 is a validated smoke runtime candidate only. Ovis BF16 / NONE / `cuda:0`
  is a validated smoke runtime candidate only. Neither status establishes Ovis
  capability, grounding, accuracy, or research precision/decoding/thinking freeze.
  Checklist #2 remains **PENDING overall**; #3–#8 remain **PENDING**.
- [ ] **3. Decoding:** Pin one supported low-variance configuration per model;
  no selection from InspecSafe outputs and no automatic reuse of hosted settings.
- [ ] **4. Adapters/parsers:** Validate deterministic native-output conversion to the
  unchanged canonical box schema. Preserve point-only outputs as raw evidence, never
  fabricate boxes; native-point-only grounding is not an approved D5 track.
- [ ] **5. External gate:** Resolve interface eligibility for all four primary
  candidates and run the unchanged eight-case SYNTHETIC V1 gate on qualifying box
  interfaces. Fix the qualitative giant-box review procedure before execution;
  record point-only incompatibility as nonparticipation, not PASS or a zero score.
  Any activated backup must meet the same prerequisites and applicable gate before
  freeze; a spatial-gate pass is required only for grounding participation.
- [ ] **6. Final roles:** Assign classification/grounding roles and record any allowed
  backup substitution before protocol freeze and before any InspecSafe inference,
  only for a pre-specified objective blocker preventing classification participation,
  with validation evidence recorded. If classification runs validly and its output
  parses, grounding-only failure or incompatible native points must retain the model
  in classification with grounding role `NOT_PARTICIPATING`: no substitution and no
  artificial zero IoU. This also applies to activated backups. Never use InspecSafe scores.
- [ ] **7. Implementation freeze:** Complete and freeze exact prompts/task policy,
  canonical schema, adapters/parsers, runner environment and full unchanged D5 engine.
- [ ] **8. Protocol freeze:** Record the approved freeze commit only after all
  prerequisites are complete. **`protocol_freeze_commit_sha: PENDING`**.

Seminar remains frozen zero-shot cross-domain robustness evaluation; no training or
fine-tuning. P1 remains unchanged. D8 Benchmark Firewall, C1, A2, B2, raw preservation,
capability-aware grounding, D5 metrics/statistics and post-freeze change control remain
binding. No model/provider calls, weight downloads or InspecSafe image inspection
are part of this synchronization. **NO_INSPECSAFE_INFERENCE**.

## W2.6-D9R1 — current roster after pre-freeze resource revision

- [x] Revise decision/config/provenance before freeze for
  `PRE_FREEZE_RESOURCE_CONSTRAINT`; no InspecSafe performance used.
- [x] Documentary metadata for Qwen2.5-VL-3B, InternVL3-2B-hf, Moondream2 and
  ordered PaliGemma-3B/SmolVLM2 backups; immutable pins, exact license evidence,
  access constraints and FP16 candidate limits recorded.
- [x] Preserve Qwen3 identity/pin and `ANCHOR_REPRODUCTION_BRIDGE`, offline COMPLETE,
  historical Kaggle T4×2 PASS / VALIDATED; sole multi-T4 exception.
- [x] Preserve retired Ovis offline COMPLETE / historical runtime PASS_VALIDATED;
  retired Molmo offline COMPLETE / runtime NOT_RUN; Gemma retired before completion.
  Old backups remain explicit historical records. PR #28 PREP stays unmerged,
  open draft and untouched; any close-as-superseded review follows D9R1 merge.
- [ ] Implement separate runners and single-T4 real smoke for Qwen2.5, InternVL3
  and Moondream2. Each: documentary COMPLETE, runner PENDING, T4 runtime PENDING,
  classification CANDIDATE, `T4_FEASIBILITY_CANDIDATE` only.
- [ ] Checklist #2 overall PENDING; #3–#8 PENDING. Protocol freeze SHA PENDING.

No D5/P1 changes, new runner, model/weight download, GPU, real inference, synthetic
gate execution or InspecSafe inference. No research precision, prompt or decoding
freeze. See [D9R1 validation and evidence](notes/w2_d9_t4_roster_revision.md).

## W2.6-D9R2A — Qwen2.5 offline runner (2026-09-24)

- [x] Qwen2.5-VL-3B offline runner: **IMPLEMENTED / OFFLINE_TESTED**, exact pin
  `66285546d2b821cf421d4f5eb2576359d3770cd3`; native Transformers/official
  qwen-vl-utils preprocessing, fake-only contracts and raw-before-parser storage.
- [ ] Qwen2.5 real T4 runtime: **PENDING / NOT_RUN**; `T4_FEASIBILITY_CANDIDATE`.
  FP16/NONE/batch 1/single cuda:0 is only the qualification candidate.
- [ ] Grounding: **DOCUMENTED_BOX_AND_POINT / NOT_YET_QUALIFIED**. Adapter returns
  UNSUPPORTED; no canonical boxes, coordinate assumptions or point-to-box conversion.
- [ ] Checklist #2 overall **PENDING**: InternVL/Moondream runners remain pending.
  Checklist #3–#8 **PENDING**; `protocol_freeze_commit_sha: PENDING`.

This overlays D9R1's historical runner-PENDING milestone without changing roster,
model identity, metrics or freeze configs. See [implementation and validation](notes/w2_qwen2_5_runner_implementation.md).
No model/weight download, GPU, real inference, synthetic gate, prompt tuning or
backup activation. **NO_INSPECSAFE_INFERENCE**.

## W2.6-D9R2B-PREP ? Qwen2.5 single-T4 runtime preparation (2026-09-25)

- [x] Offline runner **COMPLETE**; SDPA-only and explicit upstream processor
  caps 200704?1003520 pixels (256?1280 visual tokens), fake-only verified.
- [x] Runtime plan, pinned environment, snapshot provision/verify script and
  two-call classification smoke harness: **PREPARED_NOT_RUN**.
- [ ] Real single-T4 runtime **NOT_RUN**; **T4_FEASIBILITY_CANDIDATE**.
- [ ] Grounding **DOCUMENTED_BOX_AND_POINT / NOT_YET_QUALIFIED**.
- [ ] Checklist #2 overall **PENDING**; #3?#8 **PENDING**.
  `protocol_freeze_commit_sha: PENDING`; InspecSafe authorization **false**.

This pre-freeze resource qualification revision supersedes only D9R2A's eager /
processor-default candidate. Model/revision, roster, D5/P1 and historical evidence
remain unchanged. No performance results were used. See the
[PREP runbook and evidence contract](notes/w2_qwen2_5_t4_runtime_prep.md).
No weights/model download, GPU, real inference, synthetic gate or InspecSafe inference.

## W2.6-D9R2B-OBS — Qwen2.5 visual-token observability

- [x] Qwen2.5 T4 observability: **IMPLEMENTED / OFFLINE_TESTED**. Per-case actual
  grid, runtime model/processor merge agreement, computed visual-token count and
  source-supported image-placeholder equality are checked before generate.
- [ ] Real runtime: **PENDING / NOT_RUN**; **T4_FEASIBILITY_CANDIDATE**.

Plan SHA, software pins, SDPA, preprocessing caps and runner raw v2 are unchanged.
No GPU, provisioning, real inference, synthetic gate or InspecSafe execution.
See [D9R2B-OBS evidence contract](notes/w2_qwen2_5_t4_runtime_prep.md#d9r2b-obs--runtime-visual-token-observability).

## W2.6-D9R2B-DIAG — Qwen2.5 safe load diagnostics

Status overlay after the Research Lead's report of the first real T4 attempt;
the earlier PREP/OBS milestones above remain historical.

- [x] Qwen2.5 offline runner **COMPLETE**; runtime prep **COMPLETE / PREPARED**;
  observability **COMPLETE / OFFLINE_TESTED**.
- [x] First real T4 attempt **EXECUTED**:
  `kaggle-t4-qwen25-20260925T004019Z-21794d`.
  Result **RUNTIME_INTERFACE_FAILURE_AT_LOAD**, error type ValueError,
  zero native generates and empty calls; OOM **NOT_OBSERVED**.
- [x] Diagnostic patch **IMPLEMENTED / OFFLINE_TESTED**: INITIALIZE split from
  LOAD, safe load substage/type fields, preserved OOM cause-chain classification.
- [ ] T4 qualification **NOT_YET_VALIDATED**; **T4_FEASIBILITY_CANDIDATE**.
  Next real T4 rerun **PENDING / NOT_RUN**.

No loader/validation repair, resource-plan or software-pin change. No real rerun,
GPU, weights download, provisioning, synthetic gate or InspecSafe in this task.
Checklist #2–#8 and protocol freeze SHA remain PENDING. See
[reported facts, diagnostic policy and hypotheses](notes/w2_qwen2_5_t4_load_diagnostics.md).

## W2.6-D9R2B-INIT-DIAG — Initialize diagnostics and init-only probe

- [x] Second real T4 attempt reported **EXECUTED**:
  `kaggle-t4-qwen25-diag-20260925T053007Z-bd011d`, INITIALIZE / ValueError,
  zero generates, no model load reached, OOM **NOT_OBSERVED**.
- [x] Initialize diagnostics and standalone init-only probe implemented with
  fake-only tests. Existing load diagnostics and qualification plan retained.
- [ ] Real init probe **NOT_RUN**; root cause **NOT_YET_IDENTIFIED**.
  T4 remains **T4_FEASIBILITY_CANDIDATE / NOT_YET_VALIDATED**.

No runtime repair or real execution in this patch. See
[initialize diagnostics](notes/w2_qwen2_5_t4_initialize_diagnostics.md).

## W2.6-D9R2B-INIT-FIX — PyTorch version metadata normalization

Status update; previous attempt and diagnostic records remain historical.

- [x] REAL_INIT_PROBE **EXECUTED** (Research Lead-supplied evidence):
  `kaggle-t4-qwen25-init-20260925T063601Z-962127`.
  Bundle SHA-256: `738489f5e41a729826029ffdf5579a9f9ff55af65e17b6dfc8a9c2027846f05a`.
  Observed substage **SOFTWARE_VERSION_VALIDATE**, underlying ValueError;
  no model load, zero generates, empty calls; OOM **NOT_OBSERVED**.
- [x] ROOT_CAUSE **IDENTIFIED**: `torch.__version__` is a `TorchVersion` str
  subclass stored without normalization; strict builtin-str validation rejected it.
  FIX: `str(torch.__version__)` at metadata collection; strict validation retained.
  Fake-only regression reproduces the failure before the fix and passes after it.
- [ ] REAL_INIT_PROBE_AFTER_FIX **NOT_RUN**.
  T4 remains **T4_FEASIBILITY_CANDIDATE / NOT_YET_VALIDATED**.

Resource plan/software pins unchanged. No GPU, downloads, provisioning, real
inference, synthetic gate or InspecSafe. Protocol freeze remains **PENDING**.
See [evidence and minimal fix](notes/w2_qwen2_5_t4_initialize_diagnostics.md#d9r2b-init-fix--pytorch-version-metadata-normalization).

## W2.6-D9R2B-T4-QUAL — Recorded single-T4 runtime qualification

Current status supersedes earlier Qwen2.5 runtime pending statements above;
all failed-attempt records remain historical evidence.

- [x] Research Lead reports **RUNTIME_INTERFACE_PASS**, run
  `kaggle-t4-qwen25-smoke-after-initfix-20260925T073925Z-bb567e`, execution commit
  `3124b1f7c2bd8d2311d1a1db6474950e200a689f`. Model load and exactly two native
  generations PASS; native errors empty; OOM **NOT_OBSERVED**.
- [x] RESOURCE_QUALIFICATION **PASS**; roster status **PASS_VALIDATED** using
  existing repository runtime terminology. Single Tesla T4 / FP16 / SDPA / NONE,
  cuda:0, unchanged processor caps; both cases observed 256 visual tokens.
- [x] Real init reprobe reported **INITIALIZE_INTERFACE_PASS** after metadata
  normalization; full smoke also reached load and generation.
- [ ] SYNTHETIC_CAPABILITY_GATE **PENDING**. Next separate task after merge:
  exactly **8 external handcrafted synthetic capability cases**.
- [ ] Classification/grounding capability not validated. Both fenced JSON
  outputs remain **INVALID_CLASSIFICATION_OUTPUT**, an allowed interface-only
  observation; parser and prompt unchanged. No accuracy claim.
- [ ] Checklist #2 overall and #3–#8 **PENDING**; InspecSafe **NOT_RUN** and
  unauthorized; `protocol_freeze_commit_sha: PENDING`.

Evidence/status only: no new GPU run, downloads, inference or gate execution.
Plan SHA unchanged. See [record and scope](notes/w2_qwen2_5_t4_initialize_diagnostics.md#d9r2b-t4-qual--successful-real-single-t4-runtime-qualification)
and [machine-readable evidence summary](configs/pre_freeze/qwen2_5_t4_smoke_result.v1.json).

## W2.6-D9R2C-GATE-PREP — Frozen eight-case external gate harness

- [x] EXTERNAL_GATE_HARNESS **PREPARED** with a separately pinned gate plan,
  exact existing smoke decoding and existing external-target-draft-v1 prompts.
  Uses the eight pre-existing frozen cases, strict raw-before-parse and unchanged
  evaluator; all automatic checks passing yields **GATE_PENDING_REVIEW**.
- [ ] EXTERNAL_8_CASE_EXECUTION **NOT_RUN**; GIANT_BOX_REVIEW **NOT_RUN**.
  Explicit qualitative reviews are required for all eight cases before gate PASS.
- [ ] Grounding **NOT_YET_QUALIFIED**; classification **CANDIDATE**.
  Resource qualification remains **PASS_VALIDATED** only.

No cases created/regenerated/tuned, no real model outputs observed and no gate
result. Runner/production adapter, parser, prompts, frozen assets and runtime plan
remain unchanged. No real GPU, model load, download, inference or InspecSafe.
Checklist #2 overall/#3–#8 and protocol freeze SHA remain **PENDING**.
See [gate PREP runbook](notes/w2_qwen2_5_external_gate_prep.md).

## W2.6-D9R2C-GATE-RESULT — Audited Qwen2.5 spatial gate failure

Current result supersedes Qwen2.5's historical gate NOT_RUN / grounding pending
statements above; all PREP and runtime evidence remains preserved.

- [x] Real gate **EXECUTED**, audited/rehashed by Research Lead: run
  `kaggle-t4-qwen25-external-gate-20260925T092550Z-c1c1d8`.
  **GATE_FAIL**, exactly 8 native calls completed, native errors/unattempted cases
  empty; **0** canonical valid boxes, **2 SCHEMA_ERROR**, **6 JSON_ERROR**.
  Execution failure NONE; OOM NOT_OBSERVED. No rerun.
- [x] Grounding **NOT_PARTICIPATING**, reason **SPATIAL_GATE_FAILURE**.
  Giant-box review **NOT_REQUIRED_AFTER_AUTOMATIC_GATE_FAILURE**; no reviews fabricated.
  Resource **PASS_VALIDATED**, classification **CANDIDATE** unchanged.
  No backup substitution and no artificial zero IoU.
- [ ] Global D9 synthetic gate/checklist #2–#8 **PENDING**, not COMPLETE.
  InspecSafe **NOT_RUN**, authorization false; `protocol_freeze_commit_sha: PENDING`.

The failure is bounded to the frozen qualifying box interface under its prescribed
prompt/decoding/strict parser. No general localization-incapability claim, output
repair or post-hoc tuning. No production code, gate/runtime plan or frozen asset
changes. See [audited result and interpretation](notes/w2_qwen2_5_external_gate_result.md)
and [machine-readable record](configs/pre_freeze/qwen2_5_external_gate_result.v1.json).

## W2.6-D9R2D-QWEN3-GATE-PREP — Qwen3 frozen external gate preparation

- [x] Qwen3 external gate harness **PREPARED**, with a separately pinned plan,
  existing eight frozen cases, unchanged smoke decoding/resource condition,
  strict raw-before-parse and existing evaluator with `reviews=None`.
- [ ] Qwen3 external gate execution and human giant-box review **NOT_RUN**.
  Grounding **PENDING_SYNTHETIC_GATE**; roster documentary status remains
  **DOC_SUPPORTED_PENDING_SYNTHETIC_GATE**, classification **CANDIDATE**.
- [x] Resource evidence retained: **PASS_VALIDATED /
  KAGGLE_T4X2_VALIDATED_ANCHOR**; offline runner **COMPLETE** unchanged.
- [ ] Checklist #2 overall/#3–#8 and protocol freeze SHA remain **PENDING**.
  InspecSafe **NOT_RUN**, authorization false.

PREP only with fake runtime tests: no GPU, weights download, provisioning, real
inference or gate execution. Qwen3 production runner/adapter, parser, prompts,
evaluator, smoke plan, generator and all frozen assets remain unchanged.
See [Qwen3 gate PREP runbook](notes/w2_qwen3_external_gate_prep.md).

## W2.6-D9R2D-QWEN3-GATE-RESULT — Audited Qwen3 spatial gate failure

Current result supersedes Qwen3's historical gate NOT_RUN / grounding pending
statements above; PREP and validated runtime evidence remain preserved.

- [x] Real gate **COMPLETED**, inspected/rehashed by Research Lead: run
  `kaggle-t4x2-qwen3-external-gate-20260925T175057Z-08fe69`, execution commit
  `23556cf3f0adc93b76075a3247a18dd4686ff87a`. **GATE_FAIL**, one initialize,
  one load, exactly eight native generations, no native errors/unattempted cases.
  Five canonical **SUCCESS**, two **COORDINATE_ERROR**, one **SCHEMA_ERROR**,
  zero **JSON_ERROR**; systematic_tracking=false. No runtime/resource failure;
  OOM **NOT_OBSERVED**. No rerun.
- [x] Grounding **NOT_PARTICIPATING**, reason **SPATIAL_GATE_FAILURE**.
  Human giant-box review **NOT_REQUIRED_AFTER_AUTOMATIC_GATE_FAILURE**;
  no review performed or fabricated. Classification **CANDIDATE**, resource
  **PASS_VALIDATED / KAGGLE_T4X2_VALIDATED_ANCHOR** unchanged.
  No backup substitution or artificial zero IoU.
- [ ] Global D9 synthetic gate/checklist #2–#8 **PENDING**. InspecSafe **NOT_RUN**,
  authorization false; `protocol_freeze_commit_sha: PENDING`.

Result recording only: no GPU, model load/download/inference, coordinate
conversion, parser repair, prompt/decoding tuning or adapter promotion.
Production files, plans and frozen assets remain unchanged. See the
[audited result](notes/w2_qwen3_external_gate_result.md) and
[machine-readable record](configs/pre_freeze/qwen3_external_gate_result.v1.json).

## W2.6-D9R2E-MOONDREAM-PREP — STOP after source audit

- [x] Exact model source/API audit and nested Starmie immutable pin resolved:
  `35192e10a54e36eabe0a7cc57a2c1aab371cafc5`; byte hashes and evidence recorded.
- [x] Report mandatory FP16 blocker: pinned vision preprocessing allocates and
  normalizes BF16 independently of model parameter conversion. Remote code unchanged.
- [ ] Runner, provisioner, native adapter and single-T4 harness remain **PENDING**;
  **NOT_PREPARED_NOT_RUN_FP16_BLOCKER**, requiring Research Lead resolution.
  No BF16 fallback or silent preprocessing patch.
- [ ] Resource **T4_FEASIBILITY_CANDIDATE**; grounding
  **DOCUMENTED_NATIVE_DETECT_AND_POINT_PENDING_SYNTHETIC_GATE**; classification
  **CANDIDATE**. Protocol freeze SHA and overall checklist remain **PENDING**.

This status overlay preserves earlier milestones. See
[source audit and stop rationale](notes/w2_moondream_runner_prep.md).
No GPU, weights, inference, gate or InspecSafe used.

## W2.6-D9R2F-MOONDREAM-PRECISION-BRIDGE — CPU bridge PREP

- [x] Research Lead authorization recorded for original upstream preprocessing
  on CPU followed by explicit post-normalization BF16-to-FP16 conversion on CPU.
  This is an intentional pre-freeze runtime condition, before inference/gate/InspecSafe.
- [x] Small helper, strict return-structure/device/dtype/finite checks, copy contract,
  deterministic CPU tests and numerical diagnostic implemented. Status:
  **PREPARED_NOT_RUNTIME_VALIDATED**. No upstream bytes/crop/resize/normalization edits.
- [x] Future call-graph integration documented; no hook/binding installed.
- [ ] Runner **PENDING**, full FP16 runtime **NOT_VALIDATED**, T4 smoke **NOT_RUN**.
  Starmie runtime enforcement **NOT_IMPLEMENTED**. Resource **T4_FEASIBILITY_CANDIDATE**,
  classification **CANDIDATE**, grounding
  **DOCUMENTED_NATIVE_DETECT_AND_POINT_PENDING_SYNTHETIC_GATE**.
- [ ] Protocol freeze SHA and remaining overall D9 prerequisites stay **PENDING**.

See [bridge implementation, evidence and remaining work](notes/w2_moondream_precision_bridge.md).
No GPU, model weights, model inference, real external gate or InspecSafe used.

## W2.6-D9R2G-MOONDREAM-RUNNER-SMOKE-PREP — offline implementation

- [x] Prepare exact pinned offline runner/provisioner; audited-source and complete
  snapshot hash verification, offline runtime boundary and exact Starmie redirect.
  Runner and Starmie enforcement: **PREPARED_NOT_RUNTIME_VALIDATED**.
- [x] Integrate unchanged post-normalization CPU precision helper with audited
  per-instance bytecode/globals binding and restoration. Pin **PILLOW_ONLY** as a
  **PRE_FREEZE_RUNTIME_CONDITION**. Integration **PREPARED_NOT_RUNTIME_VALIDATED**.
- [x] Prepare fixed separate image/hash, one-load/query/detect harness, exact
  requirements and raw/audit artifacts. Harness **PREPARED_NOT_RUN**.
- [ ] Real T4 smoke **NOT_RUN**; full FP16 runtime **NOT_VALIDATED**. Resource
  **T4_FEASIBILITY_CANDIDATE**; classification **CANDIDATE**; grounding
  **DOCUMENTED_NATIVE_DETECT_AND_POINT_PENDING_SYNTHETIC_GATE**.
- [ ] Overall D9 prerequisites and `protocol_freeze_commit_sha` remain **PENDING**.

This overlays historical D9R2E/F pending statuses without editing their audit/bridge
records. No GPU, weights download, remote model code execution, inference, real
smoke, synthetic gate or InspecSafe used. See the
[implementation, validation and future runbook](notes/w2_moondream_runner_smoke_prep.md).
