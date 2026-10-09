## W2.6-D9R16-FIVE-MODEL-CLASSIFICATION-QUALIFICATION-PREP (2026-10-01)

- [x] Prepare independent eight-case RGB synthetic classification suite, manifest,
  policy/hash, deterministic generator and shared candidate parser/harness.
- [x] Separate run verdict from research role; preserve five-model roster,
  production pending adapters, grounding gate/history, D5 and unauthorized InspecSafe.
- [x] Prepare source-backed PaliGemma native question wrapper and exact four-level
  string parser; no reuse of yes/no presence mapping and no output rescue.
- [x] Fake/static tests cover strict parsing, runtime/incomplete runs, raw persistence,
  no retry/grounding/promotion and unchanged protected state. Validation details:
  [D9R16 PREP note](notes/w2_d9r16_classification_qualification_prep.md).
- [ ] Separate Research Lead audit/merge and subsequent authorized real qualification.
  CLASSIFICATION_RESULTS=NOT_RUN; production classification remains unqualified.
- [ ] Final classification participation decision and protocol freeze remain PENDING.

REAL_MODEL_EXECUTION=NO; NO_MODEL_REMOVAL; INSPECSAFE=NOT_RUN; KHÔNG MERGE.

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

Current authority: [D9R15](DECISIONS.md#d9r15--five-model-seminar-roster-and-exploratory-grounding-2026-09-30)
and the [readiness matrix](notes/w2_d9_freeze_readiness_reconciliation.md).

- [x] **1. Model provenance:** Five primaries and one remaining backup retain
  documentary identity/revision evidence; historical model/source evidence stays
  unchanged and current provenance active key lists match the D9R15 live roster.
- [x] **2. Runners:** All five runners COMPLETE/runtime PASS_VALIDATED; PaliGemma
  exact model/revision and single-T4 runtime verified by merged D9R9 evidence.
- [ ] **3. Decoding:** Final research conditions for all five await freeze.
- [ ] **4. Adapters/parsers:** Production classification qualification pending;
  all five CANDIDATE. PaliGemma classification interface PENDING_QUALIFICATION.
  PaliGemma/Moondream production adapters NOT_QUALIFIED.
- [x] **5. External gate / eligibility:** Five decisions resolved, not all PASS.
  Qwen3/Qwen2.5 GATE_FAIL, PaliGemma gate FAIL / grounding qualification FAIL,
  InternVL3 no qualifying native generic box interface / NOT_RUN. These four
  remain primary RQ3 NOT_PARTICIPATING; Moondream PASS gives gate eligibility only.
- [ ] **6. Final production roles:** Five-model membership is approved; production
  qualification remains pending. Exploratory includes only Moondream, Qwen3 and
  PaliGemma, separately from primary RQ3. SmolVLM2 BACKUP_1 is unactivated.
- [ ] **7. Implementation freeze:** Existing prompts/schema/adapters/runners/D5
  engine and separate exploratory reporting implementation/freeze remain pending.
- [ ] **8. Protocol freeze:** protocol_freeze_commit_sha=PENDING;
  inspecsafe_inference_authorized=false. NO_INSPECSAFE_INFERENCE.

### Historical D9–D9R4 checklist milestones

The entries below preserve earlier milestone statements; the active checklist
above and machine-readable D9R15 roster supersede their current-state wording.

Historical authority: [DEC-W2-D9-009](DECISIONS.md#dec-w2-d9-009--p2-open-weight-self-hosted-model-roster)
and the [D9 brief](notes/w2_open_weight_self_hosted_model_roster_decision_brief.md).
This is the **active P2 checklist**, mirrored in
`configs/pre_freeze/local_models.d9.json` and `configs/pre_freeze/freeze_manifest.d9.template.json`.
Documentation synchronization does not complete any execution prerequisite.

**D9R1 supersession (2026-09-24):** Current roster/resource policy is in
[W2.6-D9R1](notes/w2_d9_t4_roster_revision.md). The B0/B2/B3 milestones below
remain historical evidence; Ovis, Molmo and Gemma are no longer current primaries.

**Current D9R3 overlay (2026-09-28):** See the
[freeze-readiness matrix #1–#8](notes/w2_d9_freeze_readiness_reconciliation.md).
Qwen3/Qwen2.5/Moondream offline runners COMPLETE and runtime PASS_VALIDATED;
InternVL3 documentary COMPLETE, runner/runtime PENDING. Qwen3/Qwen2.5 gates FAIL
and grounding NOT_PARTICIPATING; Moondream external gate/grounding qualification
PASS, but its production adapter remains NOT_QUALIFIED (grounding UNSUPPORTED,
classification INVALID). InternVL3 eligibility/gate remains unresolved.
Checklist #1 COMPLETE; #2–#8 PENDING. Historical milestones below are preserved.

**Current D9R4 PREP overlay (2026-09-28):** InternVL3 offline runner COMPLETE /
OFFLINE_TESTED; exact-revision source audit, snapshot provision/verification and
single-T4 smoke harness implemented. Real runtime remains PENDING / NOT_RUN;
resource T4_FEASIBILITY_CANDIDATE, classification CANDIDATE, grounding
NOT_YET_DOCUMENTARILY_QUALIFIED. Production adapter NOT_QUALIFIED (classification
INVALID, grounding UNSUPPORTED). See [D9R4 preparation and runbook](notes/w2_internvl3_runner_smoke_prep.md).
Checklist #2–#8 remains PENDING; the D9R3 matrix above is its recorded milestone.

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

## W2.6-D9R2H-MOONDREAM-LOAD-DIAGNOSTIC-PREP

- [x] Static initialize/load analysis: old ValueError **NOT_UNIQUELY_IDENTIFIED**.
- [x] Separate load-only harness with message/cause/context/traceback, provenance
  and runner evidence; fake-only tests. **PREPARED_NOT_RUN**.
- [x] Record Research Lead-reported old smoke FAIL at load, run
  `kaggle-t4-moondream-smoke-20260926T070217Z-4c2d43`; preserve FAIL and ledger.
- [ ] Real load diagnostic **NOT_RUN**; root cause and T4 runtime validation pending.

No runner/bridge/runtime-plan change, official smoke retry, model download, GPU,
query, detect, synthetic gate or InspecSafe execution. Earlier PREP milestones
remain historical. See [analysis and diagnostic contract](notes/w2_moondream_load_diagnostic.md).

## W2.6-D9R2I-MOONDREAM-DIAGNOSTIC-KAGGLE-EXECUTION-PREP

- [x] Document the two Research Lead-authorized diagnostic-only amendments after
  PR #44: exact reprovision of a lost ephemeral cache with mandatory verify-only,
  and shell-set `CUDA_VISIBLE_DEVICES=0` before the dedicated Python process starts.
- [x] Prepare host inventory, launch transcript, existing process-visible GPU
  report, manifest comparison and evidence retention procedure; no code/config change.
- [ ] Real reprovision and load diagnostic **NOT_RUN in this task**; protocol freeze
  **PENDING**. Old official smoke **FAIL** retained; no retry or retrospective claim.

See the [D9R2I amendments and future Kaggle runbook](notes/w2_moondream_load_diagnostic.md#d9r2i-kaggle-execution-preparation--two-diagnostic-only-amendments).
No model/GPU/download/diagnostic/smoke/query/detect/gate/InspecSafe execution or merge.

## W2.6-D9R2J-MOONDREAM-FUNCTION-IDENTITY-DIAGNOSTIC-PREP

- [x] Record Research Lead-reported one-time load diagnostic FAIL at
  `AUDITED_FUNCTION_IDENTITY_REQUIRED`, execution commit
  `b8a53ca25dad354c378591bf124e73d557a38caf`; no rerun.
- [x] Prepare separate identity-only diagnostic and fake/static tests observing
  four predicates independently plus expected-code/signature comparison.
  **PREPARED_NOT_RUN**; guard and runtime behavior unchanged.
- [x] Characterize `hf_moondream.py` redaction false positive in tests;
  no redactor fix in this task; separate follow-up proposed.
- [ ] Real identity-only execution **NOT_RUN**; exact failing subcondition
  **UNKNOWN**. Runtime qualification and protocol freeze remain **PENDING**.

See [contract, evidence and validation](notes/w2_moondream_function_identity_diagnostic.md).
No real diagnostic, model construction, GPU/model execution, query/detect,
bridge, smoke, gate, InspecSafe, download or merge.

## W2.6-D9R2K-MOONDREAM-EXPECTED-CLOSURE-FIX

- [x] Research Lead reports root cause from identity run
  `moondream-function-identity-20260926T133534Z-cb4dd2cd`: audited constructor
  bytecode matches, but its single `__class__` cell violates the old blanket
  no-closure guard. This supersedes D9R2J's historical UNKNOWN subcondition.
- [x] Replace only closure validation with the expected-bytecode policy;
  synthetic/fake-only regression suite: **82 tests PASS**, Python 3.11.9.
- [ ] Real runtime after fix **NOT_RUN / NOT_VALIDATED**; qualification and
  protocol freeze remain **PENDING**.

See [exact closure policy and validation](notes/w2_moondream_function_identity_diagnostic.md#d9r2k--expected-closure-fix).
No redactor/upstream/model patch, fallback or new diagnostic. No real diagnostic,
GPU/model execution, download, smoke/query/detect/gate/InspecSafe or merge.

## W2.6-D9R2L-MOONDREAM-POSTFIX-SMOKE-PREP

- [x] Record Research Lead-reported load-only PASS at base
  `a6f5c012437bf8f404924e8dfb19a11536a92d77`; historical official smoke remains
  FAIL / consumed. Original evidence not independently inspected in this PREP.
- [x] Prepare separate post-fix wrapper with fixed namespace/one-attempt ledger,
  reusing the existing smoke lifecycle and preserving actual command provenance.
- [x] Fake/static checks: **131/131 tests PASS**; compile and diff checks PASS.
- [ ] Real post-fix smoke **NOT_RUN**; query/detect feasibility and qualification
  remain **PENDING**, protocol freeze **PENDING**.

See [contract and fake/static validation](notes/w2_moondream_postfix_smoke_prep.md).
No real runtime execution, download, external gate, InspecSafe, redaction fix or merge.

## W2.6-D9R2M-MOONDREAM-POSTFIX-SMOKE-RESULT-AND-EXTERNAL-GATE-PREP

Current documentary overlay on the historical D9R2L PREP milestone above.

- [x] Record Research Lead archive-checked post-fix smoke
  `moondream-postfix-smoke-20260927T022150Z-1b8def87`: runtime interface PASS,
  native query/detect feasibility PASS and bridge exercised for both calls.
  Historical official smoke remains FAIL / consumed / not superseded.
- [x] Prepare unchanged eight-case synthetic-v1 external gate with native detect,
  raw-before-deserialize, deterministic exactly-one-box canonical adaptation,
  canonical evaluator and PENDING human giant-box review.
- [x] Implement separate fixed one-attempt ledger, exact-commit/clean-checkout,
  cache/mask/runtime guards and stop-on-failure behavior; fake/static tests only.
- [x] Document the external-gate-only ephemeral cache exception: provision exact
  pinned snapshots only when the cache is wholly absent; separate verify-only
  and identical manifests required. Existing cache is verify-only; invalid cache
  STOP without repair/deletion. User switches Internet OFF before the gate.
- [ ] Real external gate **NOT_RUN**; grounding qualification **PENDING**.
  Protocol freeze **PENDING**; no automatic role promotion.

See [reported smoke result, gate contract and validation](notes/w2_moondream_postfix_result_external_gate_prep.md).
No real model/GPU/download/gate execution, InspecSafe, training, model selection
or merge in this task. One Draft PR contains result documentation and gate PREP.

## W2.6-D9R2N-MOONDREAM-EXTERNAL-GATE-RESULT-RECORD

Current documentary result updates D9R2M's historical gate/qualification pending
milestone above; earlier PREP and smoke records retain their original scope.

- [x] Record user-confirmed existing run
  `moondream-external-gate-20260928T013533Z-d9a1c46b`, execution commit
  `c801c899a1b63831175ea47d1d77d77f11f8e115`: completed gate, 1 load / 0 query /
  8 detect, 17/17 VALID audits, 24/24 ordered boundaries, systematic tracking true.
- [x] Record explicit human review **NO_GIANT** for A_1, A_2, B_1, B_2, C_1, C_2,
  D_1, D_2; final external gate **PASS**, grounding qualification **PASS**.
  Runtime artifact retains **GATE_PENDING_REVIEW**.
- [x] Preserve previously recorded post-fix runtime interface **PASS** and
  historical official smoke **FAIL / consumed / superseded=false**.
- [ ] Overall D9 prerequisites and protocol freeze remain **PENDING**;
  no automatic final-role promotion or InspecSafe execution authorization.

See [human review result and evidence limits](notes/w2_moondream_postfix_result_external_gate_prep.md#d9r2n--external-gate-final-human-review-record).
Documentation only; **NO REAL RUNTIME EXECUTION**. No protocol/gate/model/runner/
bridge/frozen-suite/config changes or binary artifacts.

## W2.6-D9R3-FREEZE-READINESS-RECONCILIATION

- [x] Reconcile current Moondream roster status with merged D9R2M/D9R2N evidence;
  preserve official smoke FAIL / consumed / superseded=false and classification
  CANDIDATE. Production adapter remains NOT_QUALIFIED and unchanged.
- [x] Publish [readiness matrix #1–#8 and exact blockers](notes/w2_d9_freeze_readiness_reconciliation.md);
  link current status from the unfrozen template; preserve documentary provenance.
- [ ] Checklist #2–#8 and protocol freeze remain PENDING; InternVL3 stays in
  the primary roster, no backup activation or final role assignment.

Configuration/documentary reconciliation only. **NO REAL RUNTIME EXECUTION**.

## W2.6-D9R4-INTERNVL3-RUNNER-SMOKE-PREP

- [x] Audit exact `OpenGVLab/InternVL3-2B-hf` revision
  `cb57a075cb75a2e6d1b668b128d48bb00ae321d2`; native Transformers API, no remote code,
  actual dynamic tiling/token expansion, FP16 candidate and spatial evidence limits.
- [x] Implement offline lifecycle, pinned snapshot verifier and explicit provisioner;
  preserve and re-read raw bytes/hash/size before any adapter. Pending adapters only.
- [x] Prepare one-process-visible-T4 FP16/NONE smoke with exact checkout/environment,
  one load, two independent native calls, state/VRAM/raw/failure evidence and runbook.
- [x] Fake/static focused tests and related D9 regressions; no real model execution.
- [ ] Research Lead audit and separate real single-T4 smoke: PENDING / NOT_RUN.
- [ ] Classification parser qualification and documentary spatial eligibility remain
  unresolved; no external gate executed. Checklist #2–#8/protocol freeze PENDING.

Base: `582bc1f6d15fa29dd93cd21a43fb7f8cfaa771c2`. Single Draft PR only, no merge.
No backup activation, final role assignment, InspecSafe inference or weights fetched.
**NO REAL RUNTIME EXECUTION.** Evidence and checks: [D9R4 note](notes/w2_internvl3_runner_smoke_prep.md).

## W2.6-D9R5 — InternVL3 runtime result and grounding eligibility record

- [x] Record the Research Lead-supplied and independently inspected runtime
  evidence for run `internvl3-t4-smoke-20260928-01`: runtime/resource
  `PASS_VALIDATED`, exact model/revision, one load, two native calls and eight
  stable state audits. The evidence archive and 4+ GB snapshot are not committed.
- [x] Resolve interface eligibility: the exact source/card audit documents no
  qualifying generic native bounding-box interface. Grounding is
  `NOT_PARTICIPATING`; the external gate is `NOT_RUN` with zero cases executed.
  No point-to-box conversion, prompt trick, artificial zero IoU or backup is used.
- [x] Reconcile D9 checklist #2 and #5 to `COMPLETE`; #3, #4, #6, #7 and #8
  remain `PENDING`. Classification remains `CANDIDATE`; production adapter remains
  `NOT_QUALIFIED` / `INVALID`; protocol freeze remains `PENDING` and InspecSafe
  authorization remains false.

Result record: [InternVL3 runtime result](configs/pre_freeze/internvl3_t4_runtime_result.v1.json).
This is result recording only: **NO REAL RUNTIME EXECUTION IN THIS PR**, no external
gate execution, no InspecSafe inference, no protocol freeze, final role assignment,
backup activation or merge.

## W2.6-D9R6-PALIGEMMA-PRIMARY-EXPANSION-PRECOMMIT (2026-09-28)

**Historical PaliGemma result overlay (D9R14):** External gate **FAIL**, grounding
qualification **FAIL**, rerun **NO**, human giant-box review required **NO**,
promotion **NO**; classification interface **PENDING_QUALIFICATION**.
BACKUP_1 / four primaries remain unchanged. Earlier D9R6–D9R13 pending entries
below are historical milestones, superseded only for the recorded results.
See [audited result](notes/w2_paligemma_external_gate_result.md).
Current roster membership is superseded by D9R15 below; result verdicts remain unchanged.

- [x] Record the Research Lead's sole pre-specified PaliGemma primary-expansion
  candidate, exact immutable revision and separate precommit qualification
  contract before protocol freeze and before any InspecSafe inference.
- [x] Preserve the current four-primary roster and PaliGemma's existing
  `BACKUP_1` record; link the machine-readable precommit from the local roster
  and freeze template. This is roster expansion, not backup substitution.
- [x] Preserve the existing synthetic-v1 eight-case manifest, SHA-256 and gate
  semantics while allowing the pre-specified expansion candidate to enter the
  same qualification scope.
- [x] Owner confirmed terms acceptance in D9R7 continuation; authenticated exact
  metadata access verified. Historical precommit/provenance access fields unchanged.
- [x] PaliGemma documentary source/API audit: exact config/tokenizer/processor
  verified; Research Lead selected source-backed model-ID-level detection /1024.
  Exact runtime/grounding remain pending; PR #55 independent audit PASS and merged
  at `97682b682f85ee0d9cfe646e5a69367c4d46afa6`.
  See [audit note](notes/w2_paligemma_source_api_audit.md).
- [x] Offline runner preparation: `PREPARED_NOT_RUNTIME_VALIDATED` in D9R8;
  PR #56 remains Draft, independent audit/merge pending.
- [ ] Real single-T4 FP16/NONE smoke: `PENDING_QUALIFICATION` / `NOT_RUN`.
- [ ] Deterministic external classification-interface qualification: PENDING.
- [ ] Frozen synthetic-v1 grounding gate: PENDING / NOT_RUN.
- [ ] Separate Research Lead promotion decision and independent audit: PENDING.

Governance/configuration precommit only. No model dependency installation,
weights, GPU, inference, InspecSafe performance, protocol freeze or merge was
performed in this task. Checklist #1/#2/#5 remain `COMPLETE`; #3/#4/#6/#7/#8
remain `PENDING`, and protocol freeze remains blocked until the expansion
candidate is resolved.

## W2.6-D9R7-PALIGEMMA-SOURCE-API-AUDIT (2026-09-28)

- [x] Record exact public card/metadata and versioned official API/family sources
  in `configs/pre_freeze/paligemma_source_api_audit.v1.json`; no weights/runtime.
- [x] After owner-confirmed terms acceptance and credential configuration, read
  all five exact metadata files and verify pinned Git blob/LFS hashes. Historical
  401 evidence retained; no access blockers remain, no terms accepted by Codex.
- [x] Verify native loader/processor, no remote-code requirement, exact 448
  preprocessing and 1,024 ordinary location vocabulary tokens (IDs 256000..257023).
- [x] Record Research Lead's narrow resolution: select PaliGemma 1 upstream
  model-ID-level /1024 detection decoding and deterministic D4 axis permutation;
  no clamp/repair. Maximum normalized coordinate is 1023/1024. RefCOCO *1023
  remains segmentation-training evidence only, not a detection-decoding blocker.
- [x] Record the decision in DECISIONS before runtime/gate/InspecSafe; preserve
  exact runtime_verified=false, BACKUP_1, four primaries and unchanged D9R6
  precommit/roster/provenance. Runtime, grounding and external gate remain pending.
- [x] PR #55 independent audit PASS and merged at
  `97682b682f85ee0d9cfe646e5a69367c4d46afa6`; runner-prep prerequisites complete.
  Runner prep was not part of PR #55; D9R8 preparation is tracked below.
  Exact generated grammar conformance awaits runtime qualification;
  empty-output behavior remains NOT_DOCUMENTED.

## W2.6-D9R8-PALIGEMMA-RUNNER-SMOKE-PREP (2026-09-28)

- [x] Pin exact PaliGemma runtime plan, 14-file authoritative snapshot inventory,
  separate explicit provisioner and offline full-byte verifier; no weights fetched.
- [x] Prepare native FP16/NONE/batch-1/cuda:0 runner and one-visible-T4 smoke,
  verified raw-before-adapter persistence, fail-closed lifecycle and pending adapters.
- [x] Implement/test pure D9R7 /1024 D4 conversion with NO_CLAMP/no repair;
  native model output conformance is not qualified by helper tests.
- [x] Fake/static preparation checks: see [D9R8 note](notes/w2_paligemma_runner_smoke_prep.md).
  Runner status `PREPARED_NOT_RUNTIME_VALIDATED`; exact runtime verified=false.
- [ ] Real runtime `PENDING_QUALIFICATION` / `NOT_RUN`; grounding, classification
  interface and external gate remain `PENDING_QUALIFICATION`. No gate execution.
- [ ] PR #56 remains Draft; independent audit and merge pending.
  Separately authorized owner qualification remains pending.

Current tracker overlay only: historical D9R6/D9R7 evidence artifacts unchanged.
PaliGemma remains `BACKUP_1`, four primaries; no promotion. Protocol freeze `PENDING` / `BLOCKED`,
InspecSafe authorization=false. No real model/GPU/InspecSafe execution or merge.

## W2.6-D9R9 — Kaggle notebook and Research Lead-verified runtime qualification

- [x] Prepare self-contained [Kaggle notebook](notebooks/w2_paligemma_d9r9_kaggle.ipynb)
  for owner execution after Research Lead review, pinned to execution base
  `180c0623149bbc7d64f5b659f6c044c39b1e1cd0` and unchanged D9R8 model/revision.
- [x] Automate fresh checkout, isolated pinned environment, single-T4 process
  checks, explicit provision/full verification, one manual Internet-OFF barrier,
  unchanged smoke harness, bounded evidence bundle and failure stops without retry.
- [x] Static/fake validation: 94 focused/regression tests PASS; no real download,
  GPU, model, synthetic gate or InspecSafe execution. See [prep record](notes/w2_paligemma_d9r9_notebook_prep.md).
- [x] Research Lead reviewed an owner-run failure bundle: venue/clone/checkout
  passed; notebook Python 3.12.13 failed at bootstrap venv's ensurepip, before
  weights or runtime. This is supplied evidence, not Codex runtime execution.
- [x] Patch bootstrap to dedicated pip --target uv==0.8.22 with version check;
  use anonymous public clone. 97 static/fake/regression tests PASS; pins unchanged.
- [x] Research Lead reviewed the owner-run Kaggle result bundle and approved
  REAL_RUNTIME_STATUS=RUNTIME_SMOKE_PASS; EXACT_RUNTIME_VERIFIED=true.
  Record: [runtime result](configs/pre_freeze/paligemma_t4_runtime_result.v1.json)
  and [qualification note](notes/w2_paligemma_single_t4_runtime_qualification.md).
- [x] Record exact snapshot/software/single-T4/offline evidence, one model load,
  two native calls, raw-before-adapter PASS, OBSERVED_ONLY outputs and metrics.
- [x] Correct notebook timing validator: two idempotent load re-entries are not
  reloads or runtime failure. Preserve all spans and the independent load count=1.
  233 related static/fake tests PASS. No rerun, GPU/model or provision by Codex.
- [ ] Grounding, classification interface and external gate qualification remain pending.

PaliGemma remains BACKUP_1, primary roster count=4; grounding/classification
interface/external gate PENDING_QUALIFICATION, protocol freeze BLOCKED,
promotion NO and InspecSafe authorized=false. This result overlay supersedes the
historical D9R8/PREP runtime-pending status only; immutable plan and historical
source/audit artifacts remain unchanged. D9R9 COMPLETE: PR #57 merged at
`93a8f32ad8c7d10a28cb3e4b62232cd3697bd0e1`.

## W2.6-D9R10-PALIGEMMA-INTERFACE-QUALIFICATION-PREP

- [x] PREP / implementation: predeclare separate four-classification/four-grounding
  observation matrix and deterministic geometric fixtures; no grammar inferred
  from D9R9 color observations.
- [x] Prepare one-load/sequential-call offline harness, exclusive verified raw
  persistence before observation, immutable plan and fail-closed evidence records.
- [x] Prepare unexecuted D9R11 Kaggle notebook pinned to harness commit
  `ceb56d5174a387362e3ef6a5af3b6618123bc8a7`; static/fake tests cover offline
  barrier, eight-call export, partial failure evidence and credential isolation.
- [x] D9R11 evidence collection COMPLETE per Research Lead-reviewed bundle;
  approved observations are recorded in D9R12 below. Interface qualification
  remains pending; this completion does not qualify production semantics.

See [D9R10 preparation contract](notes/w2_paligemma_interface_qualification_prep.md).
Runtime smoke remains PASS/exact verified=true; classification, grounding and
external gate PENDING_QUALIFICATION; BACKUP_1, four primaries, freeze BLOCKED and
InspecSafe authorization=false. No model/GPU/provisioning/gate/InspecSafe execution.

## W2.6-D9R12-PALIGEMMA-INTERFACE-EVIDENCE-RECORD-AND-ADAPTER-CONTRACT

D9R12 **COMPLETE**: PR #59 merged at
`a3192ddefbc28fe2997190819744e8f4796a6d85`. Production qualification remains
pending; D9R13 is a separate PREP task below.

- [x] Record Research Lead-approved D9R11 evidence: exact bundle/commit/plan,
  environment, one load/eight calls, raw-before-parser PASS and all eight exact
  outputs/IDs/raw hashes. Research Lead checked 76/76 artifact sizes and hashes;
  Codex did not inspect raw bundle bytes.
- [x] Implement offline presence-answer and single red-square grounding parser
  candidates; keep production adapters pending. Preserve negative `grd_d` as a
  parseable prediction with separately recorded semantic hallucination.
- [x] Validate 267 static/fake tests, 31 strict pre-freeze JSON parses,
  scoped secret-pattern scan and diff check: PASS. No real runtime execution.
- [ ] Classification interface, grounding and external gate:
  **PENDING_QUALIFICATION**; separate Research Lead decision required.

Base: `da7a3b8098eb40edba8858791d01d30b564bcc78`. Runtime smoke PASS / exact
verified=true; BACKUP_1, four primaries, freeze BLOCKED, InspecSafe authorized=false.
No promotion, real GPU/model/provisioning, synthetic-v1 gate or InspecSafe execution.
See [D9R12 evidence and offline contract](notes/w2_paligemma_interface_adapter_contract.md)
and [machine-readable result](configs/pre_freeze/paligemma_interface_runtime_result.v1.json).

## W2.6-D9R13-PALIGEMMA-FROZEN-EXTERNAL-GATE-PREP

Research Lead decision supersedes both discovery and seven-case C1/B2 PREP in
the same Draft PR #60. Use the exact eight frozen external cases used by Qwen/Moondream.

- [x] Prepare eight frozen grounding calls / zero classification calls / one load;
  reuse load_cases and evaluate_gate, unchanged fixtures/GT/criteria and D9R11 runtime.
- [x] Add closed four-label native loc parser; raw-before-parser and /1024;
  wrong label/grammar fails closed without clamp, repair or semantic correction.
- [x] Prepare unexecuted Kaggle notebook with provisioning-only token, offline
  barrier, exclusive attempt, source pin and review bundle; no automatic PASS.
- [x] Preserve D9R11 target-absent hallucination; no extra gate case.
- [x] Prepare separate offline finalization with explicit human giant-box review;
  automatic gate success remains PENDING_REVIEW until that review. No promotion.
- [x] Actual frozen external gate completed and Research Lead reviewed: **FAIL**;
  six SUCCESS / two SCHEMA_ERROR, recorded in D9R14 below.
- [ ] Production classification: PENDING_QUALIFICATION; no C1 artifacts invented,
  no classification calls, and missing C1 policy/cases do not block this gate.

Base: `a3192ddefbc28fe2997190819744e8f4796a6d85`; latest correction starts at
`0f07f7132e1ce7f1973ad1639f5a20725b493feb`.
BACKUP_1, four primaries, freeze BLOCKED, InspecSafe authorized=false.
See [frozen external gate preparation](notes/w2_paligemma_production_interface_freeze_prep.md).
No GPU/model/Kaggle/provisioning/gate/InspecSafe execution, promotion or merge.

## W2.6-D9R14-PALIGEMMA-EXTERNAL-GATE-RESULT-RECORD

- [x] Transcribe Research Lead-verified bundle identity, 87/87 artifact SHA/size
  matches, execution commit, frozen authority and one-T4/eight-call runtime.
- [x] Record A_1/B_1/B_2/C_1/D_1/D_2 SUCCESS and A_2/C_2 SCHEMA_ERROR /
  PARSER_FAIL_NO_REPAIR; preserve both exact two-detection native outputs.
- [x] External gate **FAIL**, systematic_tracking=false; grounding qualification
  **FAIL**. Rerun **NO**; human giant-box review required for decision **NO**;
  promotion **NO**. No artificial zero IoU or output repair.
- [x] Preserve D9R11 target-absent parseable red-square hallucination.
- [x] Run 104 focused tests (PASS), strict JSON 2/2, scoped secret/text checks
  and diff check (PASS). Full suite: 1219 tests, 4 failures / 24 errors; the same
  issues reproduce in the read-only BASE-roster control. See result-note limits.
- [ ] Classification interface remains **PENDING_QUALIFICATION**.

Current result: [note](notes/w2_paligemma_external_gate_result.md) and
[machine-readable record](configs/pre_freeze/paligemma_external_gate_result.v1.json).
BACKUP_1, four primaries, existing role/exploratory policy, blocked freeze and
InspecSafe authorization=false unchanged. No model/GPU/gate rerun, InspecSafe,
token-budget increase, giant-box review or merge in this recording task.

## W2.6-D9R15-FIVE-MODEL-ROSTER-AND-EXPLORATORY-GROUNDING

- [x] Record Research Lead's pre-freeze roster-design decision and limited
  supersession of D9R6/D9R14 membership policy, preserving all result records.
- [x] Set five primary classification candidates; PaliGemma PRIMARY_5 with
  runtime PASS_VALIDATED/exact verified=true, classification interface pending,
  gate/grounding FAIL; remove active backup duplication. SmolVLM2 unactivated.
- [x] Separate gate-aware primary RQ3 participation from exploratory policy;
  include exactly Moondream, Qwen3 and PaliGemma, with no qualification override,
  model rescue, gate lowering or post-InspecSafe selection/tuning.
- [x] Validate focused core 152/152 PASS; extended focused 187 tests with one
  BASE failure. Full suite 1229 tests, same 4 failures / 24 errors as exact BASE
  (1219 tests); no new regression. Changed JSON 2/2, diff/protected-file checks PASS.
  See [D9R15 validation](notes/w2_d9_freeze_readiness_reconciliation.md#d9r15-validation).
- [x] Commit implementation (`c3594f6`) and open [Draft PR #62](https://github.com/tantdna2/SafeShift/pull/62)
  to main after validation. Independent review pending; NOT MERGED.
- [x] Reconcile current provenance roster_revision to D9R15; retain historical
  model/source evidence and retired keys. Test active lists against LIVE roster.
- [x] Resolve current giant-box procedure field per model evidence; preserve
  Moondream NO_GIANT review and failed/ineligible-model review applicability.
- [x] Follow-up validation: D9R15 12/12 PASS; focused 215 tests, one existing
  D9R1 allowlist failure. Full suite 1232 tests, same 4 failures / 24 errors and
  same 28 failing/error identities as BASE; no new regression. Strict JSON 3/3
  and diff check PASS. Historical documentary evidence and result bytes preserved.
- [ ] Production qualification, exploratory reporting implementation/freeze and
  protocol freeze remain PENDING. InspecSafe authorization=false.

Base: `9948570820b5ed8a774b8e226b80e24055e705cf`.
NO_INSPECSAFE_INFERENCE; NO_MODEL_RERUN; no GPU/gate execution or merge.

## W2.6-D9R17A-QWEN2_5-CLASSIFICATION-QUALIFICATION-RESULT (2026-10-01)

- [x] Record Research Lead-verified completed real qualification in a separate
  [result artifact](configs/pre_freeze/qwen2_5_classification_qualification_result.v1.json)
  and [note](notes/w2_qwen2_5_classification_qualification_result.md); no independent
  Codex bundle inspection/rehash and no bundle/raw bytes committed.
- [x] Record RUN_STATUS=FAIL / SEMANTIC_CLASSIFICATION_FAILURE, runtime failure=NONE,
  parser SUCCESS 8/8 and exact_expected_count=3 of 8, descriptive only.
- [x] Preserve D9R16 manifest/plan bytes and historical classification_results=NOT_RUN;
  five-model roster, Qwen2.5 CANDIDATE, production adapters, D5 and grounding intact.
- [x] Focused 64/64 PASS. Full suite: result branch 1,276 tests vs exact BASE
  1,263 tests; both 4 failures / 24 errors, same 28 identities, no new regression.
  Existing failures are retained; validation commands/limits are in the note.
- [ ] Independent result review: PENDING_REVIEW; model role
  PENDING_RESEARCH_LEAD_REVIEW; classification participation decision PENDING.

Base/execution: `7154c6187de7d8ecc5ad4ac5d0aafb68d2d7c1ab`.
No roster removal, backup activation or production promotion. AUTOMATIC_RERUN=false;
REAL_MODEL_RERUN=NO; INSPECSAFE=NOT_RUN / unauthorized; PROTOCOL_FREEZE=PENDING.
Recording only; no model/GPU execution or merge.

## W2.6-D9R17B-E-FOUR-MODEL-CLASSIFICATION-QUALIFICATION-RESULTS (2026-10-01)

- [x] Transcribe four Research Lead-verified bundles into one
  [result artifact](configs/pre_freeze/d9r17b_e_classification_qualification_results.v1.json)
  and [note](notes/w2_d9r17b_e_classification_qualification_results.md), with exact
  execution identities, 32 per-case raw SHA256/sizes and supplied runtime evidence.
  Codex did not independently inspect/rehash bundles; no bundle/raw/weight commit.
- [x] Record InternVL3 FAIL / semantic / parse 8/8 / exact 6/8; Moondream FAIL /
  semantic / parse 8/8 / exact 2/8; PaliGemma FAIL / format / parse 0/8 / exact 0/8;
  Qwen3 PASS / parse 8/8 / exact 8/8. Descriptive only; runtime failure=null each.
- [x] Focused documentary tests 23/23 and expanded focused 67/67 PASS; protected plan/cases/roster/freeze
  byte checks and historical D9R16 NOT_RUN / unauthorized PREP checks PASS.
- [x] Same-environment full suite: BASE 1,276 tests / result branch 1,299 tests;
  both 4 failures / 24 errors, identical 28 failure/error identities, no new
  regression. Prior result guard allows only the exact new artifact path;
  unrelated historical failures remain. Commands and limits are in the note.
- [ ] Independent Research Lead review PENDING_REVIEW; all four model roles
  PENDING_RESEARCH_LEAD_REVIEW and classification participation decisions PENDING.

BASE/execution: `3ad16f48da4f9ef5910dedede9a4ba950f268b7a`.
No roster change/removal, backup activation, production promotion, model execution,
retry/repair or rerun. INSPECSAFE=NOT_RUN / unauthorized; PROTOCOL_FREEZE=PENDING.
No prompt/parser/runner/runtime/D5/grounding/exploratory-policy change or merge.

## W2.6-D9R18-FINAL-PARTICIPATION-AND-ROLES (2026-10-02)

Research Lead decision at exact BASE `93e1004de311588e94356e19edf53220de13e194`.
Current overlay resolves historical D9R17 PENDING_REVIEW / pending role and
participation decisions only; all qualification result and D9R16 plan/case bytes
remain unchanged. See [decision](configs/pre_freeze/d9r18_final_participation_decision.v1.json)
and [scope/validation note](notes/w2_d9r18_final_participation_decision.md).

- Four classification participants: Qwen3, Qwen2.5, InternVL3, Moondream.
- PaliGemma classification NOT_PARTICIPATING: objective interface/format blocker,
  0/8 parse SUCCESS, 8/8 INVALID, canonical null. No output reinterpretation,
  lowercase normalization or marker-to-level mapping.
- Qualification remains Qwen3 PASS; Qwen2.5/InternVL3/Moondream semantic FAIL;
  PaliGemma interface/format FAIL. Valid canonical output permits participation;
  synthetic semantic FAIL must not be used as benchmark ranking or performance
  filter before InspecSafe. No qualification promotion or PASS-rule change.
- Five-model primary research roster unchanged, including PaliGemma PRIMARY_5.
  ROSTER MEMBERSHIP != CLASSIFICATION PARTICIPATION. SmolVLM2 not activated:
  four participants suffice, seminar does not require exactly five, and no new
  runtime/qualification workload is needed before freeze. Not backup failure or
  model replacement; historical replacement policy unchanged.
- Grounding roles/history unchanged; Moondream remains gate-eligible with
  production adapter NOT_QUALIFIED. Exploratory includes Qwen3/Moondream/PaliGemma
  and excludes Qwen2.5/InternVL3; no exploratory qualification override.
- Checklist #1/#2/#5 COMPLETE; #3/#4/#7/#8 PENDING;
  #6 ROLE_DECISION_COMPLETE_ADAPTER_QUALIFICATION_PENDING. Decisions complete;
  remaining production adapter qualification belongs to #4, not undecided roles.
- No model/GPU execution or rerun, no prompt/parser repair, no backup activation,
  no D5 implementation. InspecSafe NOT_RUN / unauthorized; protocol freeze PENDING.
  Historical legacy candidate fields retained with explicit current field semantics.

- [x] Record final participation decision and reconcile both current overlays/readiness matrix.
- [x] Validate 17 new tests; core 96/96 PASS; extended 178 with one BASE failure.
- [x] Compare exact isolated BASE 1299 tests (8 failures / 24 errors) against D9R18
  1316 tests (4 failures / 24 errors): no new failure/error identities; four
  Windows representation failures resolved in related historical assertions.
  Full suite is not PASS. See linked D9R18 note for commands and limits.
- [ ] Independent Draft PR review and merge remain pending; no merge in this task.

## W2.6-D9R19G1-QWEN3-PALIGEMMA-GROUNDING-INTERFACE-QUALIFICATION-PREP (2026-10-03)

Exact fetched BASE `5538064e6ea015f8c15475d488064cae95461cd0`; new branch/worktree,
separate from D9R19 / PR #67. Research objective: determine whether Qwen3 and
PaliGemma can support source-backed production-compatible grounding interfaces
before protocol freeze, without promising PASS or changing historical verdicts.

- [x] Pin official Qwen3 cookbook and PaliGemma 1 detection source/checksums;
  record evidence scope, coordinate convention and preprocessing relation.
- [x] Implement isolated strict one/multiple detection parser candidates with
  deterministic D4 conversion; no historical parser/result changes or repair.
- [x] Prepare `external-grounding-interface-v2`: ten synthetic cases, fixed
  prompts, image hashes, deterministic generator and predeclared PASS rules.
- [x] Declare raw-before-parser audit contract; create no model result records.
- [x] 33 new unit tests PASS; 283 selected regression tests PASS (316 combined).
  Unfiltered 284-test regression run has one D9R18 task-specific change-allowlist
  failure; it passes at BASE but cannot admit this newly authorized task scope.
  Historical test is unchanged. Strict JSON 4/4 and diff check PASS;
  61 protected historical files byte-identical. See validation note.
- [ ] QWEN3_ABSENCE_SEMANTICS_BLOCKER: authoritative all-absent serialization
  unresolved; empty JSON array is not accepted as successful zero.
- [ ] PALIGEMMA_ABSENCE_SEMANTICS_BLOCKER: empty/no-match decoder behavior does
  not establish native zero-detection semantics.
- [ ] Independent source/contract review, future versioned absence resolution,
  runtime integration/environment lock and separate execution authorization.
- [ ] Future qualification and any separate Research Lead promotion decision.

Qwen3 historical GATE_FAIL (5/8; 2 coordinate + 1 schema error); PaliGemma FAIL
(6/8; 2 schema errors); both primary grounding roles NOT_PARTICIPATING.
PR #67 remains OPEN/DRAFT and unchanged. EXECUTION_STATUS=NOT_RUN;
MODEL_GPU_EXECUTION=NO; QUALIFICATION_EXECUTION=NOT_RUN; INSPECSAFE=NOT_RUN;
PROTOCOL_FREEZE=PENDING; MERGE=NO. No full InspecSafe/fixed-hazard executor.
Contract, source pins, evidence limits and commands:
[D9R19G1 PREP note](notes/w2_d9r19g1_grounding_interface_prep.md).


## D9R19G1 closure record (2026-10-04; append-only)

G1 merged as PR #68.
merge commit: `dd83c6231e5758cdb85ba84e293d4b462e38a696`.
Historical G1 `MERGE=NO` statements describe their original PREP state and are
preserved; this appended record supplies the subsequent closure only.

## W2.6-D9R19G2-QWEN3-PALIGEMMA-ABSENCE-SEMANTICS-RESOLUTION (2026-10-04)

Authority: explicit Research Lead task; fetched origin/main equals required
BASE `dd83c6231e5758cdb85ba84e293d4b462e38a696`. Source audit only.

Both QWEN3_ABSENCE_SEMANTICS_BLOCKER and PALIGEMMA_ABSENCE_SEMANTICS_BLOCKER
remain BLOCKED. Qwen's official evaluator conflates parse errors with empty
predictions; its COCO serialization does not establish the native all-absent
answer. PaliGemma's generic EOS/suffix pipeline does not establish that zero
matching objects produce an empty detect target. RefCOCO target construction
is for selected-object segmentation. No semantics inferred from historical
SafeShift outputs or permissive parser no-match behavior.

No new contract version: retain v2 candidate/source/plan/lock byte-unchanged.
No new qualification result or production promotion. QUALIFICATION=NOT_RUN;
QUALIFICATION_EXECUTION=NOT_RUN; execution_authorized=false;
MODEL_GPU_EXECUTION=NO; INSPECSAFE=NOT_RUN; PR67 unchanged; MERGE=NO.

Evidence, exact source pins, limits and validation:
[G2 audit note](notes/w2_d9r19g2_grounding_absence_semantics.md) and
[source manifest](configs/pre_freeze/grounding_absence_semantics_audit.v1.json).

- [x] Complete bounded official-source audit and preserve both absence blockers.
- [x] Validate 43 focused + 267 relevant regression tests (310 PASS), 29 source
  hashes, protected G1/v2 history, append-only logs and git diff --check.
- [ ] Authoritative absence resolution for each model remains pending.
- [ ] Independent G2 review; runtime integration and separate execution authority.

## D9R19G2 closure record (2026-10-04; append-only)

G2 merged as PR #69.
merge commit: `775e5eee4cade340e0156f97f2af50f7c98e1551`.
Historical G2 `MERGE=NO` remains intact; this is a subsequent closure record.

## W2.6-D9R19G3-POSITIVE-GUARANTEED-MULTICATEGORY-GROUNDING-PREP (2026-10-04)

- [x] Verify official multicategory/multi-object sources and pin URL/hash/date.
- [x] Prepare isolated v3 exact-label parsers, full ordered 12-hazard query map,
  synthetic positive suite and predeclared all-or-nothing PASS criteria.
- [x] Document D6 positive union 721 + 608 - 347 = 982; exclude Unsupported-Only
  18 and Normal. Keep both absence blockers UNRESOLVED, empty response a failure.
- [x] 77 focused tests and 267 relevant regression tests PASS (344 total);
  protected history and append-only checks PASS. Full suite not run.
- [ ] Independent Draft PR review (see note).
- [ ] Separate runtime integration/environment lock and execution authorization.
- [ ] Future qualification; separate Research Lead promotion decision if PASS.

V2/G2 history and PR #67 unchanged. Qwen3/PaliGemma historical gates FAIL;
primary grounding NOT_PARTICIPATING. D5 unchanged, RQ3-A/RQ3-B separate.
QUALIFICATION_EXECUTION=NOT_RUN; execution_authorized=false;
MODEL_GPU_EXECUTION=NO; INSPECSAFE=NOT_RUN; PROMOTION=NO; MERGE=NO.
Details: [G3 PREP note](notes/w2_d9r19g3_positive_multicategory_grounding_prep.md).

## D9R19G3 closure record (2026-10-04; append-only)

G3 merged as PR #70.
merge commit: `685021ef974cc3feef968d7e920e7720ce6349f2`.
Historical G3 `MERGE=NO` remains intact; subsequent closure only.

## W2.6-D9R19G4-MULTICATEGORY-RUNTIME-INTEGRATION-QUALIFICATION-EXECUTION-PREP (2026-10-04)

- [x] Prepare separate pinned Qwen3/PaliGemma runtime v3 and CLI, 12 positive
  synthetic calls/model, identical four-label query, greedy max_new_tokens=512.
- [x] Implement durable raw/preparse persistence, reread hash/size verification,
  continuation-prefix/EOS checks, no parser on storage/token-boundary failure.
- [x] Implement mandatory hash/identity/path/authority/environment preflight,
  result schema/writer and all-detection human NO_GIANT review gate.
- [x] Prepare prospective environment inventory contract and future commands;
  hardware targets supported by historical evidence, no v3 runtime-ready claim.
- [x] Offline validation: 103 focused (26 new) and 267 relevant regression tests
  PASS; full suite not run. See G4 note for final checks and limitations.
- [ ] External venue environment/snapshot verification and independent PR review.
- [ ] Separate Research Lead plus independent-auditor execution authorization.
- [ ] Real qualification and subsequent human review; no execution in G4.

QUALIFICATION_EXECUTION=NOT_RUN; execution_authorized=false; MODEL_GPU_EXECUTION=NO;
INSPECSAFE=NOT_RUN; both primary grounding roles NOT_PARTICIPATING; both absence
blockers UNRESOLVED; PR #67 unchanged; PROMOTION=NO; MERGE=NO.
Runtime readiness BLOCKED on unverified environment/authority; offline integration
readiness and validation: [G4 PREP note](notes/w2_d9r19g4_multicategory_runtime_prep.md).

## D9R19G4 closure record (2026-10-04; append-only)

G4 merged as PR #71.
merge commit: `b3bf4dc770c1b87a9e353a75aab759f67641c2c2`.
Historical G4 MERGE=NO and unverified/unauthorized PREP state remain unchanged.

## W2.6-D9R19G5-MULTICATEGORY-EXECUTION-IDENTITY-RELOCK (2026-10-04)

- [x] Verify fetched main at exact G4 merge; prepare separate G5 branch/worktree.
- [x] Prepare v2 runtime lock, execution identity/plan and false authorization
  template; preserve G4 v1 locks/environment and G3 scientific contract.
- [x] Prepare future observation commands for Qwen3 T4 x2 and PaliGemma T4 x1,
  with fixed run IDs g5-qwen3-v3-001 and g5-paligemma-v3-001; commands NOT RUN.
- [x] Offline validation: 113 focused + 267 relevant regression tests PASS;
  history/append-only checks and diff check PASS. Full suite not run.
  Exact pushed candidate and Draft PR delivery are recorded in the final handoff.
- [ ] Future environment observation, independent audit and Research Lead authority.
- [ ] Future qualification execution and human NO_GIANT review.

G5 Draft PR MUST REMAIN OPEN during every future step above; merging changes
main and invalidates authority. Never auto-merge. Execution BASE is
`b3bf4dc770c1b87a9e353a75aab759f67641c2c2`; authority must bind exact pushed
G5 HEAD from Git. See [G5 relock note](notes/w2_d9r19g5_execution_identity_relock.md).
ENVIRONMENT_STATUS=UNVERIFIED_EXTERNAL_VENUE_LOCK_PENDING;
QUALIFICATION_EXECUTION=NOT_RUN; EXECUTION_AUTHORIZED=NO; MODEL_GPU_EXECUTION=NO;
INSPECSAFE=NOT_RUN; QWEN3_RUNTIME_EXECUTION=BLOCKED;
PALIGEMMA_RUNTIME_EXECUTION=BLOCKED; both primary grounding roles
NOT_PARTICIPATING; both absence blockers UNRESOLVED; PR #67 unchanged;
PROMOTION=NO; MERGE=NO.

## W2.6-D9R19G5R-QWEN3-QUALIFICATION-RESULT-RECORD (2026-10-04; append-only)

Result/closure overlay after G5 PREP. [PR #72](https://github.com/tantdna2/SafeShift/pull/72)
merged at `465ec738b6a395801df06e2ef179e2bf51f8b509`, the exact BASE of this
separate documentary task. Historical PREP lines, checkboxes, NOT_RUN/BLOCKED
and keep-Draft-open instructions above retain their original historical scope.

Source: Research Lead's supplied audited execution facts for
`Qwen/Qwen3-VL-8B-Instruct`, run `g5-qwen3-v3-001`; this task records them and
does not repeat execution or independently re-audit the artifact ZIP.
Full revision/checksum identity and results: [G5 result overlay](notes/w2_d9r19g5_execution_identity_relock.md#qwen3-g5-resultclosure-overlay-2026-10-04).

- [x] Record PR #72 closure and completed Qwen3 qualification execution:
  QUALIFICATION_EXECUTION=EXECUTED; model_loads=1; native_calls=12; failure=null;
  12/12 termination_reason=EOS; raw-before-parse verified; artifact integrity PASS.
- [x] Record 12/12 parse_status=INVALID under frozen v3 strict_json parser:
  all 12 native outputs were Markdown-fenced JSON, rejected by that parser.
  E_red_green also emitted the out-of-query label "blue square".
- [x] Record tracking_result=false; final_verdict=FAIL; independent audit PASS;
  QWEN3_G5_QUALIFICATION=FAIL; RERUN=NO; INSPECSAFE=NOT_RUN.
- [x] Retain Qwen3 primary grounding NOT_PARTICIPATING; PROMOTION=NO.
- [ ] Independent review and merge of this documentary Draft PR remain pending;
  no merge in this task.

This task changes documentation only: no parser, prompt, runner, scientific
contract tests or model code changes; no model/InspecSafe execution and no G6.
Historical results are preserved without repair or reinterpretation.
## W2.6-D9R19G6-PALIGEMMA-EXECUTION-IDENTITY-RELOCK (2026-10-04)

- [x] Prepare versioned G6 runtime lock v3, execution plan v2 and inert
  authorization template v2 from exact BASE
  `069d780b6590a32a19cbe6e341ffa19cedbcd712`.
- [x] Bind G6 exclusively to PaliGemma
  (`google/paligemma-3b-mix-448`, revision
  `ead2d9a35598cb89119af004f5d023b311d1c4a1`, Kaggle T4 x1, transformers
  4.57.1, FP16, NONE, greedy max_new_tokens=512) and predeclared run ID
  `g6-paligemma-v3-001`.
- [x] Preserve synthetic v3 parser/geometry/prompt/cases/expected geometry,
  thresholds, no-retry/no-repair and raw-before-parse; retain Qwen3 G5 FAIL
  and NOT_PARTICIPATING history without rerun or authority.
- [x] Prepare observation-before-load contract for exact HEAD/main, model and
  revision, software, T4 x1, snapshot hashes/sizes, code/contract hashes and
  generation config. Keep Draft PR open through observation, audit,
  authorization, execution and human review; merge invalidates authority.
- [x] Focused G6 governance tests, relevant frozen-contract regressions and
  `git diff --check` pass; full suite not run.
- [ ] Environment observation, independent audit, Research Lead authorization,
  qualification execution and human review remain future work.

G6 is PREP only: `PALI_EXECUTION_AUTHORIZED=NO`; `MODEL_GPU_EXECUTION=NO`;
`INSPECSAFE=NOT_RUN`; `PROMOTION=NO`; `MERGE=NO`. PR #67 is unchanged.
See [G6 relock note](notes/w2_d9r19g6_execution_identity_relock.md).

## W2.6-D9R19G6-PALIGEMMA-QUALIFICATION-RESULT-CLOSURE (2026-10-05; append-only)

Result/closure overlay for the G6 execution identity. This section records the
subsequent audited execution and does not rewrite the historical PREP status,
including its `NOT_RUN`, `BLOCKED` and `MERGE=NO` lines.

- [x] Record execution identity: model
  `google/paligemma-3b-mix-448`, revision
  `ead2d9a35598cb89119af004f5d023b311d1c4a1`, run
  `g6-paligemma-v3-001`, execution HEAD
  `b8a8a40c1d632c4609302daffee52543fe13b39d`, and MAIN/BASE
  `069d780b6590a32a19cbe6e341ffa19cedbcd712`.
- [x] Record environment hash
  `5eedbff47f5a4288f785bba8cb1dfe205c5403411295780b06af8bf09c2a909b` and
  runtime lock hash
  `237143b33405bc0d03e3c911cf042e9874a089a48cc95d7691883c83e79ce0ad`.
- [x] Record `QUALIFICATION_EXECUTION=EXECUTED`: one model load, 12 native
  calls, `failure=null`, 12/12 EOS, artifact audit complete, raw-before-parse
  verified, and 12/12 parser successes.
- [x] Record geometry PASS 1/12 and FAIL 11/12; only `H_all_four` had
  `geometry_ok=true`. `tracking_result=false` and `final_verdict=FAIL`.
- [x] Record independent artifact audit PASS. The failure is semantic/spatial
  over-detection for labels with expected count zero, not parser failure:
  `A_1` had extra green circle/cyan rectangle, `E_red_green` extra cyan
  rectangle, `F_two_red` extra green circle/yellow triangle/cyan rectangle,
  and `G_multi` extra cyan rectangle. `H_all_four` matched exact counts and
  passed geometry. Extra boxes were not dropped or reinterpreted.
- [x] Close governance outcome as
  `PALIGEMMA_G6_QUALIFICATION=FAIL`,
  `PALIGEMMA_PRIMARY_GROUNDING_ROLE=NOT_PARTICIPATING`, `RERUN=NO`,
  `HUMAN_NO_GIANT_REVIEW_REQUIRED_FOR_DECISION=NO`, `PROMOTION=NO`, and
  `INSPECSAFE=NOT_RUN`.

No parser, prompt, geometry or gate change was made; no model rerun or new
candidate model task was started. PR #67 remains unchanged. PR #74 remains
OPEN/DRAFT and is not merged.

## W2.6-D9R20-RQ3-THREE-CANDIDATE-PREP (2026-10-05; append-only)

Authority: explicit Research Lead PREP request; fetched origin/main exactly
`668aae839bbde91b67686d143259e07c8a89608c`. Worktree/branch isolated from the
owner's untracked census. No main migration, historical rewrite or model run.

- [x] Verify three exact HF revisions, official small source texts/checksums,
  license/access, documentary weight metadata and native coordinate contracts.
- [x] Record prospective A interface/capability versus B synthetic-semantic
  separation; retain Qwen3 G5 and PaliGemma G6 FAIL without reinterpretation.
- [x] Prepare strict model-specific parsers and shared raw/provenance/lifecycle
  with isolated loaders/environments, fixed run IDs and no fallback/offload.
- [x] Prepare reuse of eight D9R16 classification cases and independent fixed
  single-target synthetic capability/diagnostic calls, no production fan-out.
- [x] Prepare three ordered owner runbooks, inert authorization and bounded
  artifact bundle workflow. No automatic PASS or participation decisions.
- [ ] Independent PREP review and merge; no merge performed by this task.
- [ ] Owner license acceptance for PLaMo; verified external environments,
  exact post-merge identity review and separate execution authorization.
- [ ] Real single-T4 FP16 resource smoke and synthetic qualification; human
  matched-box NO_GIANT/capability review and separate participation decision.
- [ ] CALL2_ORCHESTRATION_BLOCKER for all three remains unresolved; no RQ3_READY.

Ovis and Kosmos PREP verdict SOURCE_READY_CALL2_BLOCKED; PLaMo ACCESS_BLOCKED,
with its resource and Call2 risks also retained. FP16/T4 is not runtime verified
for any candidate. Source audit, candidate table, validation and commands:
[D9R20 PREP note](notes/w2_d9r20_three_candidate_prep.md).
MODEL_GPU_EXECUTION=NO; WEIGHTS_DOWNLOADED=NO; INSPECSAFE=NOT_RUN;
PROTOCOL_FREEZE=PENDING; HISTORICAL_G5_G6=UNCHANGED; PROMOTION=NO; MERGE=NO.

D9R20 offline validation: 50 focused + 229 selected regression tests PASS
(279 distinct); all 41 downloaded source-text/API checksums checked. Two
unfiltered historical regression failures reproduced at exact BASE and retained:
old Ovis checklist state and G4 old-main identity. Append-only/history checks and
git diff --check PASS. Full suite and model/GPU execution not run. Exact commands
and exclusions are in the linked PREP note; no historical test was edited.

## D9R20 PREP closure record (2026-10-05; append-only)

[PR #75](https://github.com/tantdna2/SafeShift/pull/75) is MERGED at
`2026-10-05T08:57:14Z`. GitHub PR identity and fetched origin/main were verified
against the exact Git merge parents before this documentary closure:

- Merge commit / new main: `7976e5c60817319481c564ca1a68f24aec270da8`.
- Parent 1 / old main: `668aae839bbde91b67686d143259e07c8a89608c`.
- Parent 2 / PR HEAD: `b86a3af6754ae238c08f9b5e727df7750fdebd61`.
- D9R20 PREP implementation/review/merge: COMPLETE.

This closes the existing PREP task only; it is not a new scientific task or
runtime result. Historical PREP text, including `MERGE=NO`, "no merge performed
by this task" and the old checkboxes, remains unchanged as its original state.

Ovis2.5-2B, PLaMo 2.1-2B-VL and Kosmos-2 remain NOT_RUNTIME_QUALIFIED.
CALL2_ORCHESTRATION_BLOCKER remains for Ovis/PLaMo/Kosmos;
participation=PENDING_RESEARCH_LEAD_DECISION; PROTOCOL_FREEZE=PENDING;
INSPECSAFE=NOT_RUN; MODEL_GPU_EXECUTION=NO. Qwen3 G5 FAIL and PaliGemma G6 FAIL
remain unchanged; no reruns or promotion.

Owner runtime is a separate step after closure, requiring its own environment
observation and separate authorization binding the exact execution identity.
The PREP merge and this record grant no runtime authority. No code, config,
parser, runtime, test or scientific contract changed; no weights downloaded,
model/GPU execution or InspecSafe run occurred in this closure.

## W2.6-D9R21-CANONICAL-SYNTHETIC-FIXTURE-PORTABILITY (2026-10-05; append-only)

Prospective PREP fix authorized by Research Lead at verified fetched BASE
`4520597a654d25f73ff1b425aa94ad27326c026f`. Owner-reported Kaggle CPython 3.11.9 /
zlib 1.2.13 cannot reproduce v3 encoded PNG hashes from zlib 1.3.1; this is a
portability blocker, not a model failure. D9R20 models have not run and protocol
freeze is PENDING. See the D9R21 decision appended to DECISIONS.md.

- [x] Add committed v4 manifest and 12 small synthetic PNGs. A-D are exact copies
  of historical frozen_external_gate bytes; E/F/G/H were drawn once using v3
  geometry/colors/drawing semantics in Python 3.11.9 / Pillow 11.3.0 / zlib 1.3.1.
- [x] Keep scientific pixels, case order, query semantics/counts/targets/distractors
  unchanged, verified against unchanged v3 build() after RGB decoding.
- [x] Move only D9R20 to committed v4 fixtures with exact SHA/size validation,
  restricted paths and existing symlink/alias rejection, without regeneration.
- [x] Replace owner renderer setup with read-only v4 verification; preserve all
  model environment pins, Internet-OFF-before-observe/run and Call2 blockers.
- [x] Offline selected tests: 228 PASS, 0 FAIL, 2 SKIP (optional downloaded source
  caches absent). Verifier PASS for 12 inputs; git diff --check PASS.
- [x] Preserve historical v3 code/manifests/plans/locks/results and old verdicts;
  logs remain append-only. No hash relaxation, fallback or mismatch warning.
- [ ] Independent review of the Draft PR; no merge in this task.
- [ ] Future venue observation, separate execution authorization and owner runs.

Validation commands (repository root; no real model/network/InspecSafe access):

```text
python scripts/verify_grounding_multicategory_v4.py
python -m unittest tests.test_grounding_multicategory_v4 tests.test_d9r20_candidates tests.test_grounding_multicategory_v3 -q
python -m unittest tests.test_grounding_interface_v2 tests.test_grounding_absence_semantics_audit tests.test_external_gate_cases tests.test_grounding_execution_relock_g5 tests.test_grounding_execution_relock_g6 -q
python -m unittest tests.test_grounding_multicategory_runtime_v3 tests.test_classification_qualification -q
git diff --check
```

The first two unittest groups ran 102 (100 PASS, 2 SKIP) and 72 (all PASS).
The unfiltered last group ran 57: 56 PASS, 1 pre-existing ERROR in
`ContractTests.test_dry_preflight_blocks_without_authority`, which demands G4's
old origin/main and raises `MAIN_IDENTITY_CHANGED_RESEARCH_LEAD_REQUIRED`.
Reproduced that exact error from a Git archive of BASE (same live origin/main),
without editing historical tests or runtime. Selected G4 rerun excluding only
that stale identity test passed 25/25. The classification group contributes
31 PASS; selected distinct total = 228 PASS + 2 SKIP. No full-suite PASS claim.

The new tests cover verifier read-only behavior, same-size tamper, wrong size,
missing/corrupt image, wrong canvas/mode, exact path/outside/traversal rejection,
real directory alias rejection, A-D byte identity, semantic/pixel equivalence,
all three candidates' unchanged 22-call order/prompts and rejection of caller
image overrides/v3 fallback. Synthetic/fake tests do not create model evidence.

v4 committed fixtures remove the owner renderer/zlib reproduction dependency;
Pillow remains for decoding in each unchanged model-specific environment.
execution_authorized=false; participation=PENDING_RESEARCH_LEAD_DECISION;
protocol_freeze=PENDING; MODEL_GPU_EXECUTION=NO; INSPECSAFE=NOT_RUN;
HISTORICAL_V3=UNCHANGED; HISTORICAL_G5_G6=UNCHANGED; MERGE=NO.

## W2.6-D9R21-CANONICAL-SYNTHETIC-FIXTURE-PORTABILITY-CLOSURE (2026-10-05; append-only)

Source: Research Lead's supplied audit and direct GitHub merge verification.
This documentary closure also checked GitHub PR identity and fetched origin/main
against the exact merge commit and ordered Git parents below.
[PR #77](https://github.com/tantdna2/SafeShift/pull/77) is MERGED at
`2026-10-05T13:14:08Z`; the merged implementation changed 24 files.

- Merge commit: `6ff60808f68d7b6f6477489827ab79e173bcee07`.
- Parent 1 / pre-merge main: `4520597a654d25f73ff1b425aa94ad27326c026f`.
- Parent 2 / PR HEAD: `55a7cb9ac4aa5055ebaf5a6fb3def529386da1d5`.
- New main = merge commit = this closure's exact BASE:
  `6ff60808f68d7b6f6477489827ab79e173bcee07`.

- [x] D9R21 portability fix implementation/review/merge: COMPLETE.
- [x] Record the Research Lead-verified new-main state: D9R20 grounding manifest
  `configs/pre_freeze/external_grounding_interface_cases.v4.json`;
  V4_FIXTURES_PRESENT=YES; HISTORICAL_V3_UNCHANGED=YES; G5_G6_UNCHANGED=YES.
- [ ] Future owner environment observation, exact execution identity review and
  separate execution authorization remain separate future work.
- [ ] Future owner model execution and subsequent human review/participation
  decision remain separate future work; none is authorized by this closure.

Historical D9R21 PREP statements, including `MERGE=NO`, "no merge in this task"
and all old checkboxes, remain unchanged as records of their original time.
Only this new closure records the subsequent completed implementation/review/merge.

Ovis2.5-2B, PLaMo 2.1-2B-VL and Kosmos-2 remain NOT_RUNTIME_QUALIFIED.
CALL2_ORCHESTRATION_BLOCKER remains for all three; execution_authorized=false;
participation=PENDING_RESEARCH_LEAD_DECISION; protocol_freeze=PENDING;
MODEL_GPU_EXECUTION=NO; INSPECSAFE=NOT_RUN. Historical v3 and G5/G6, including
Qwen3 G5 FAIL and PaliGemma G6 FAIL, are unchanged; no rerun or promotion.
Neither the PR #77 merge nor this closure grants runtime authority.

Closure scope is append-only TASKS.md and DECISIONS.md. No code, config, test
or fixture PNG changes. Validation: git diff --check and exact-base append-only /
two-file scope checks; model tests are not run because no code changes.
The separate closure PR is delivered as DRAFT; MERGE=NO for this closure task.

## W2.6-D9R22-SEMINAR-RQ3-DISAGREEMENT-REDESIGN (2026-10-05; CURRENT, append-only)

Prospective Research Lead redesign at verified remote main / BASE
`a227e18330b49fb8f848934da164a776bc9f6a50`; local main is not the base.
This is the current Seminar scope/readiness overlay; earlier checklists and
grounding blockers retain historical meanings. Authority and validation:
[D9R22 scope](configs/pre_freeze/d9r22_seminar_scope.v1.json),
[decision](DECISIONS.md#d9r22--prospective-seminar-rq3-disagreement-redesign-2026-10-05),
[readiness](notes/w2_d9r22_seminar_readiness.md)
and [note](notes/w2_d9r22_seminar_scope_redesign.md).

- [x] Record prospective title and RQ3 redesign; RQ1/RQ2 semantics unchanged.
- [x] Add versioned current scope with nine predeclared RQ3 metric families;
  reuse classification predictions only, no extra inference or implementation.
- [x] Preserve four D9R18 classification participants; PaliGemma remains
  NOT_PARTICIPATING, SmolVLM2 inactive, no fifth ensemble model.
- [x] Defer primary/exploratory grounding to future thesis extension;
  historical FAIL/PASS, artifacts and decisions are preserved.
- [x] Current evidence readiness: model provenance, runtime runners,
  classification participation and external gate history COMPLETE.
- [ ] Exact classification production contract.
- [ ] Production classification adapters/parsers.
- [ ] Exact decoding/preprocessing/precision freeze.
- [ ] RQ1/RQ2/RQ3-new metric implementation, including exact RQ3 contract.
- [ ] Production benchmark harness.
- [ ] End-to-end rehearsal.
- [ ] Implementation freeze.
- [ ] Protocol freeze.

`PRIMARY_SEMINAR_GROUNDING=DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE`;
CALL2_ORCHESTRATION_BLOCKER, MOONDREAM_CALL2_ORCHESTRATION_BLOCKER and
exploratory grounding blockers = NOT_ACTIVE_SEMINAR_FREEZE_BLOCKER.
Deferral is not a scientific FAIL or qualification promotion.
inspecsafe_inference_authorized=false; MODEL_GPU_EXECUTION=NO;
INSPECSAFE=NOT_RUN; PROTOCOL_FREEZE=PENDING; MERGE=NO.
Draft PR review is separate. Stop after PR A; wait for prompt B.

### D9R22 validation record (append-only)

- [x] New scope checks 15/15 PASS; strict JSON, participant/RQ invariants,
  protected history, exact append-only prefixes and commit allowlist verified.
- [x] Same-environment exact-BASE comparison: BASE full suite 1504 tests,
  5 failures / 25 errors / 2 skips; HEAD 1519 tests,
  6 failures / 25 errors / 2 skips. Full suite NOT PASS.
- [x] Disclose the one new failure identity:
  `test_d9r20_candidates.Contracts.test_historical_files_and_append_only_logs`
  rejects the explicitly requested README/ROADMAP changes. All 30 BASE failure/
  error identities persist; no unrelated historical tests were edited.
- [x] Extended regression: HEAD 131 tests, 128 PASS / 1 FAIL / 2 SKIP;
  BASE 116 tests, 114 PASS / 2 SKIP. Same scope-guard conflict; details in note.
- [x] Preserve the pinned old readiness note byte-for-byte; use a separate
  D9R22 readiness note. Diff checks PASS; no dataset/weights/raw outputs staged.

## W2.6-D9R23-CLASSIFICATION-PRODUCTION-CONTRACT (2026-10-05; CURRENT, append-only)

Stacked on exact PR A HEAD `b28e4665904ecd0ab5057a1bc92e263a81c3e8c7`;
Draft PR B targets `w2.6-d9r22-seminar-rq3-disagreement-redesign`, not main.
D9R22 scientific scope/config and all historical runtime/qualification artifacts
remain unchanged. Current implementation/readiness authority:
[D9R23 note](notes/w2_d9r23_classification_production_contract.md) and
[policy](configs/pre_freeze/production_classification_policy.d9r23.v1.json).

- [x] Inspect PR #67 source-only; selectively reuse classification registry,
  native validation and runtime-backed conditions, without grounding architecture.
- [x] Implement versioned exact C1 industry table prompt/hash and canonical
  output vocabulary; no GT, metadata or D6 atom-list injection.
- [x] Implement four-model conditions as FREEZE_CANDIDATE and strict adapters
  behind verified raw-before-parse storage. PaliGemma remains nonparticipating.
- [x] Record prospective INVALID accounting decision and executable examples;
  no fabricated Level04, explicit parse-conditional/failure-aware denominators.
- [ ] Complete full RQ1/RQ2/RQ3 metric engine and production benchmark harness.
- [ ] End-to-end rehearsal; new C1 prompt runtime behavior remains untested.
- [ ] Implementation freeze and protocol freeze.

MODEL_GPU_EXECUTION=NO; INSPECSAFE=NOT_RUN;
inspecsafe_inference_authorized=false; PROTOCOL_FREEZE=PENDING; MERGE=NO.
Stop after Draft PR B; wait for prompt C.

### D9R23 validation record (append-only)

- [x] Focused D9R23 plus relevant existing tests: 255/255 PASS.
- [x] Exact A_HEAD BASE full suite: 1521 tests, 5 failures / 25 errors / 2 skips.
- [x] D9R23 HEAD full suite: 1540 tests, 5 failures / 25 errors / 2 skips;
  all 30 BASE failure/error identities persist, `NEW_FAILURE_IDENTITIES_VS_BASE=0`.
- [x] Diff and staged diff checks PASS; no model/GPU/InspecSafe execution.

## W2.6-D9R24-DISAGREEMENT-RELIABILITY-METRICS (2026-10-05; CURRENT, append-only)

Stacked on exact PR B HEAD `6e205a53a9ceeebbc258d3ad0be6a7ddb865501e` with Draft
PR C targeting `w2.6-d9r23-classification-production-contract`. The prospective
metric contract is `configs/pre_freeze/d9r24_metric_contract.v1.json` and the
offline implementation note is
`notes/w2_d9r24_disagreement_reliability_metrics.md`.

- [x] Implement D5-compatible RQ1 classification, safety-critical,
  folder_domain and support diagnostics with explicit parse/failure-aware rates.
- [x] Implement image-level RQ2 metrics for 12 primary Hazard Atoms and seven
  secondary A-G summaries with non-additive multi-hazard semantics.
- [x] Implement RQ3 for exactly four models using JOINT_VALID_4, availability,
  unanimous agreement, pairwise kappa, vote entropy, ordinal disagreement,
  vote patterns, shared blind spots, error complementarity, disagreement/error
  association and deterministic risk-coverage.
- [x] Implement deterministic domain-stratified point-cluster percentile
  bootstrap (`B=2000`, seed 42) with shared paired draws and NA support policy.
- [x] Add deterministic JSON reporting and synthetic tests; no raw images,
  responses, weights or dataset artifacts are committed.
- [ ] Production benchmark harness and end-to-end rehearsal.
- [ ] Implementation freeze.
- [ ] Protocol freeze.

`PRIMARY_SEMINAR_GROUNDING=DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE`;
`inspecsafe_inference_authorized=false`; `MODEL_GPU_EXECUTION=NO`;
`INSPECSAFE=NOT_RUN`; `PROTOCOL_FREEZE=PENDING`; `MERGE=NO`.

### D9R24 methodology correction record (2026-10-06; append-only)

- [x] Correct degenerate kappa to undefined with an explicit status/reason.
- [x] Correct unanimous anomaly blind-spot denominator to joint anomaly support.
- [x] Correct safety-critical risk-coverage denominator and report eligible and
  overall coverage axes with explicitly named eligible-cohort AURC.
- [x] Restore D5 support-aware domain macro metrics, K=4 BA spread,
  anomaly-recall spread, and the explicit metallurgy sparse-support policy.
- [x] Enforce Normal point_id bootstrap metadata and anomaly sample-level
  resampling with a declared dependence limitation.
- [x] Expose explicit RQ2 stratum fields and add known-value synthetic tests.

No model/GPU/InspecSafe execution, protocol freeze, merge, or new task occurred.

## W2.6-D9R25-INSPECSAFE-PRODUCTION-EXECUTION-HARNESS (2026-10-06; CURRENT, append-only)

Stacked on exact PR C HEAD `ac8825e7d0e21e437fda044cadc3aa8b4fc8f508`;
Draft PR D targets `w2.6-d9r24-disagreement-reliability-metrics`.

- [x] Implement freeze-gated P2 entrypoint; current authority blocks before reads/load.
- [x] Verify 5013-image contract, original manifest/fingerprint, paths and image hashes.
- [x] Separate label-free inference payload/records from explicit evaluation join.
- [x] Four-model D9R23 registry, exact C1 and runtime-condition identities.
- [x] Atomic/exclusive raw storage with verified reread before strict native parsing.
- [x] Immutable attempts, no retry/repair, failure accounting, no same-run resume.
- [x] Deterministic shards, completed-shard exports and four-model cohort alignment.
- [x] Offline generated-data/scripted-backend tests; no actual dataset/model execution.
- [ ] D9R26 end-to-end rehearsal/runbooks/freeze candidate (separate authorization).
- [ ] Implementation freeze.
- [ ] Protocol freeze.

P2_PRODUCTION_HARNESS=IMPLEMENTED_OFFLINE_SYNTHETIC_ONLY;
RAW_BEFORE_PARSE=ENFORCED; NO_GT_LEAKAGE=ENFORCED_BY_CONTRACT_AND_TESTS;
DETERMINISTIC_SHARDING=IMPLEMENTED; MODEL_GPU_EXECUTION=NO;
INSPECSAFE=NOT_RUN; inspecsafe_inference_authorized=false;
PROTOCOL_FREEZE=PENDING; IMPLEMENTATION_FREEZE=PENDING; MERGE=NO.
Grounding remains deferred. Stop after Draft PR D; do not start D9R26.

### D9R25 validation record (append-only)

- [x] Focused D9R25: 40/40 PASS; relevant regression set: 219/219 PASS.
- [x] Exact C_HEAD BASE full suite: 1533 tests, 4 failures / 2 errors / 2 skips.
- [x] D9R25 full suite: 1573 tests, same 4 failure / 2 error identities / 2 skips.
  NEW_FAILURE_IDENTITIES_VS_BASE=0; full suite is NOT PASS. Exact identities and
  environment/newline controls are recorded in the D9R25 implementation note.
- [x] Diff and staged diff checks PASS; no dataset/weights/raw outputs staged.

### D9R25 backend-binding correction (2026-10-06; append-only)

- [x] Remove caller backend injection from public production_run.
- [x] Version the internal four-model registry; fail closed pending native bridges.
- [x] Keep internal/scripted test injection and generated-image-only rehearsal.
- [x] Separate Git source repo from temporary artifact storage; no provenance fallback.
- [ ] D9R26 exact source-backed bridges reusing native runners and static/fake
  integration tests (separate task; not begun; no model execution in Codex).

P2_PRODUCTION_HARNESS=IMPLEMENTED_OFFLINE_SYNTHETIC_ONLY;
PRODUCTION_BACKEND_BINDING=FAIL_CLOSED_PENDING_D9R26_SOURCE_BACKED_BRIDGES;
CALLER_BACKEND_INJECTION=FORBIDDEN; INSPECSAFE=NOT_RUN;
inspecsafe_inference_authorized=false; MODEL_GPU_EXECUTION=NO;
PROTOCOL_FREEZE=PENDING; IMPLEMENTATION_FREEZE=PENDING; MERGE=NO.

- [x] Correction focused tests 45/45 PASS; regression set 224/224 PASS.
- [x] Same-environment exact BASE/HEAD full discovery: 1533/1578 tests;
  both 4 failures, 2 errors, 2 skips, identical six failure/error identities.
  NEW_FAILURE_IDENTITIES_VS_BASE=0; full suite NOT PASS. No dependency changes.
- [x] Diff checks PASS; correction preserves active scientific contracts and
  original raw/firewall/shard/retry implementation semantics.

### D9R26 preflight/runbooks/bridges/freeze candidate (2026-10-06; append-only)

- [x] Stack on exact PR #82 HEAD a3a5fdcc0a17b920f2c15942247b6fd61d25aa2d.
- [x] Bind the exact four existing native runners through a versioned internal
  bridge; preserve production no-injection boundary and freeze-first guard.
- [x] Separate image/C1 scientific payload from operational RunContext; pin
  exact D9R23 condition, deterministic call identity and native model revisions.
- [x] Add four owner runbooks and a thin metadata preflight/production CLI.
- [x] Rehearse ScriptedBackend and fake native runner paths end to end through
  durable raw, parser, export, alignment, explicit GT join and RQ1/RQ2/RQ3 report.
- [x] Create a hash-verified FREEZE_CANDIDATE_NOT_FROZEN manifest only.
- [ ] ChatGPT GitHub verification and independent audit (not performed here).
- [ ] Merge A->E and final post-merge freeze/authorization PR, outside this task.
- [ ] Final protocol SHA and Research Lead InspecSafe authority, still pending.

Runtime observation NOT_EXECUTED_IN_CODEX; no model/download/GPU/InspecSafe
execution. A-E remain unmerged. Final SHA is unknown until audit+merge.
PROTOCOL_FREEZE=PENDING; IMPLEMENTATION_FREEZE=PENDING;
protocol_freeze_commit_sha=PENDING; INSPECSAFE_AUTHORIZED=false;
INSPECSAFE=NOT_RUN; READY_TO_RUN_INSPECSAFE=false; MERGE=NO.

### D9R26 validation record (append-only)

- [x] Focused D9R26 bridge/candidate tests: 16/16 PASS, including both full
  scripted and fake-native rehearsal paths with identical deterministic reports.
- [x] D9R22-25 + relevant native runner/manifest/firewall/storage/qualification
  regressions: 464/464 PASS. No dependency install/change during comparison.
- [x] Same-environment `python -m unittest discover -v` at exact D BASE:
  1578 tests, 4 failures / 2 errors / 2 skips; E implementation: 1594 tests,
  same 4 failures / 2 errors / 2 skips. NEW_FAILURE_IDENTITIES_VS_BASE=0.
  Full suite is NOT PASS; matching counts alone were not used as evidence.
- [x] Exact six matching failure/error identities (BASE and HEAD):
  - tests.test_d9_t4_roster_revision.D9T4RosterRevisionTests.test_23_only_explicitly_authorized_post_d9r1_runner_source
  - tests.test_d9r18_final_participation_decision.FinalParticipationTests.test_only_explicit_decision_documentation_and_test_files_change
  - tests.test_ovis_gpu_smoke_result.OvisSmokeResultTests.test_research_claims_grounding_and_checklist_remain_pending
  - tests.test_qwen_kaggle_smoke_result.SmokeResultTests.test_claims_grounding_and_checklist_boundaries
  - tests.test_grounding_multicategory_runtime_v3.ContractTests.test_dry_preflight_blocks_without_authority
  - unittest.loader._FailedTest.tests.test_moondream_precision
  These are existing historical scope/checklist expectations, the historical
  origin/main identity guard, and absent optional torch, respectively.
- [x] `git diff --check` and `git diff --cached --check` PASS. Candidate hashes
  agree with Git repository LF bytes; original checkout newline treatment is
  matched for BASE/HEAD. Only scoped code/config/docs/synthetic tests staged.
- [x] Metadata preflight reports PROTOCOL_FREEZE_REQUIRED with no dataset/model
  access. READY_FOR_INDEPENDENT_AUDIT_BEFORE_FREEZE=true;
  READY_TO_RUN_INSPECSAFE=false. No audit/merge/freeze/authorization performed.

### D9R26 freeze-candidate state reconciliation (append-only)

- [x] Verified remote PR #83 HEAD e1e9c82169a1bf1f1bca32b92ca2d3b577165ebe.
- [x] Preserve D9R22 bytes/scientific RQs; deep-copy the current candidate view
  and overlay only RQ3 metric contract/status from validated D9R24 metadata.
- [x] Reject wrong/missing schema, status, roster, metric families, grounding or
  pending-freeze state. No metric formulas or bridge/native logic changed.
- [x] D9R25 next_task=INDEPENDENT_AUDIT_BEFORE_FREEZE; existing production
  binding remains IMPLEMENTED_SOURCE_BACKED_FREEZE_CANDIDATE.
- [x] Regenerate candidate through its builder, including exact updated hashes;
  no self-hash, historical state rewriting or production-validation claim.
- [x] Focused candidate/bridge tests: 19/19 PASS; D9R22-25 regressions: 97/97 PASS.
- [x] Reran exact PR E BASE a3a5fdcc0a17b920f2c15942247b6fd61d25aa2d and
  corrected HEAD with `python -m unittest discover -v` in the same Python 3.11.9
  environment, unchanged dependencies and matched checkout newline handling:
  1578 vs 1597 tests, both 4 failures / 2 errors / 2 skips. All six identities
  match the D9R26 validation record above; NEW_FAILURE_IDENTITIES_VS_BASE=0.
  Full suite remains NOT PASS. Working/staged diff checks PASS.

FREEZE_CANDIDATE_NOT_FROZEN; PROTOCOL_FREEZE=PENDING;
protocol_freeze_commit_sha=PENDING; IMPLEMENTATION_FREEZE=PENDING;
INSPECSAFE_AUTHORIZED=false; INSPECSAFE=NOT_RUN; MODEL_GPU_EXECUTION=NO;
READY_TO_RUN_INSPECSAFE=false; no audit, Antigravity, new PR or merge.

### W2.6-D9R27-FINAL-PROTOCOL-FREEZE-AND-MERGE-GATED-AUTHORITY (2026-10-06)

- [x] Confirm exact post-A→E audited main base
  `e7628d68f87cf53b5343ea912b7e332064c285af`.
- [x] Freeze the final D9R25 contract and preserve the reviewed D9R26
  candidate byte-for-byte with its exact SHA-256 pin.
- [x] Implement fail-closed Git verification requiring the final reviewed
  two-parent Standard Merge Commit; Draft PR F2 remains pre-merge blocked.
- [x] Add focused D9R27 tests for authority pins, ancestry, merge parents/tree,
  post-F1 allowlist, dirty tracked state, static preflight and no-runtime
  behavior.
- [ ] Research Lead / ChatGPT GitHub review and independent audit.
- [ ] Standard merge into main and final Research Lead / ChatGPT verification.
- [ ] Owner preflight and later InspecSafe P2 execution, only after that
  verification.

D9R27 performs no model/GPU/InspecSafe execution, real dataset read, network,
Antigravity call or merge. `PROTOCOL_FREEZE=FROZEN` and the authority declaration
are static contract state; effective authority is false until the reviewed
merge commit exists.

### W2.6-D9R27-FINAL-AUTHORITY-GATE-CORRECTION (2026-10-06)

- [x] Verify PR #84 remote HEAD remains the expected old F2.
- [x] Enforce exact authority schema and F2 direct-child Git structure.
- [x] Expand D9R27 tests with real temporary Git repositories and synthetic
  valid/wrong-parent/wrong-tree/intermediate/multi-parent/dirty histories.
- [x] Rebuild NEW_F1 directly on the exact audited base and NEW_F2 as its sole
  authority-file child.
- [ ] Research Lead / ChatGPT review, independent audit, standard merge and
  final post-merge verification.

No model/GPU/InspecSafe execution, dataset read, network, Antigravity call or
merge occurs in this correction.

### D9R27 correction verification completion (2026-10-06; append-only)

- [x] Distinct real-Git tree, executable-drift, parent and missing/untracked
  authority checks; individual authority mutations; exact preservation checks.
- [x] Guarded fresh-process preflight and owner CLI: no dataset/model/GPU/network
  access or P2 artifact creation on either Draft or synthetic final merge.
- [x] D9R22-D9R27 regression: 128 tests PASS before final two-commit rebuild.
- [ ] Independent audit, Research Lead / ChatGPT review, standard merge and
  final post-merge verification remain external gates; no merge in this task.

Git/GitHub maintenance only updates the existing Draft PR #84. Full-suite
comparison uses exact BASE and final HEAD with matched LF checkout handling;
final hashes and results are reported in the PR handoff. The Draft PR remains
ineffective execution authority. No Antigravity, model/GPU or InspecSafe run.

### Qwen3 T4 x2 runtime placement amendment (2026-10-08; append-only)

- [x] Create isolated branch from exact BASE
  `031958a5ce668057f763973a722a3506d73f39f0`.
- [x] Version the winning explicit map and embedding-only CPU permission in a
  pending runtime amendment; preserve old frozen policy/candidate/authority.
- [x] Enforce exact native `hf_device_map`, FP16/NONE, default SDPA and allocator;
  configure the Qwen3 owner process before torch import, reject late setup.
- [x] Add fake/synthetic tests for the exact winner and required rejection cases.
- [x] Record owner-reported production OOM and 4581/4149-token diagnostic PASS
  with source and unchanged semantic/data/metric contracts in the runbook.
- [x] Focused placement/runner/contract/harness/bridge/candidate regression:
  182 tests PASS (Python 3.11.9; Git LF checkout handling).
- [x] Historical authority: 12 tests PASS, including real temporary Git
  histories and fresh-process no-dataset/model/GPU/network guards.
- [x] Native/historical model regressions: 275 test identities PASS; the
  historical Qwen3 source-hash assertion was adapted to its frozen commit and
  revalidated with all 13 result tests plus 2 scope tests PASS.
- [x] Working/staged diff checks PASS; no dataset, weights or raw output staged.
- [ ] Separate Research Lead review and superseding execution/rerun authority.

Draft PR creation is the final handoff action; its URL is reported externally.

`RERUN_AUTHORIZED=NO`; `reruns=[]` unchanged; no old run ID reuse, model/GPU or
dataset execution, Antigravity call or merge. Existing D9R27 merge/tree authority
cannot authorize the amended runtime; this remains a production blocker.

### Qwen3 superseding P2 execution authority v2 (append-only)

- [x] Prepare isolated branch from exact PR #85 merged BASE
  `92ef9179f23ca7c58ffb425512d239b12b26f832`.
- [x] Preserve historical authority v1, runtime amendment, D9R25/D9R26,
  prompt, metrics and dataset contract bytes; add Qwen3-only v2 support.
- [x] Freeze the exact four-shard plan: shard0 `qwen3-p2-shard0-rerun1` binds
  `qwen3-p2-shard0-first` / manifest SHA-256
  `d4dd6ee9790dcc3c99c73e9404b52f71268fc7285ead41797dcf828261cd1500`;
  shards1-3 use `qwen3-p2-shard{1,2,3}-first`. Full shard0 includes the two
  previous successes; no Qwen2.5, InternVL3 or Moondream rerun permission.
- [x] Derive lineage from authority without a new caller-selectable CLI flag;
  check local prior manifest before dataset access and retain hidden-rerun checks.
- [x] Add local synthetic Git tests, pin/plan/lineage/model negative cases and
  fresh-process no-dataset/model/GPU/network preflight guards.
- [x] Initial scoped regressions: 83 tests PASS; initial new authority suite:
  16 PASS plus actual F2 structure check deferred until F2 exists. Subsequent
  final validation/commit SHAs are recorded in the Draft PR handoff.
- [x] Document exact owner restore/hash/offline/T4 x2/allocator/four-run steps.
- [ ] Independent audit and Research Lead / ChatGPT review.
- [ ] Standard Merge Commit into main and post-merge Git verification.
- [ ] Future owner execution after effective authority and prior-artifact check.

F1 contains all executable/config/test/runbook changes. F2 may add only
`configs/frozen/p2_execution_authority.v2.json` as F1's direct child. The Draft
has no effective production/rerun authority. No model, GPU, real dataset,
production, Antigravity call or merge occurs in this task. Existing Qwen2.5
completed results remain outside this new Qwen3 plan. Raw failed production
manifest bytes were not supplied/read; supplied failure evidence and SHA are
documented in the Qwen3 runbook with the synthetic-test limitation.

### InternVL3 P2 superseding authority v3 (2026-10-09; append-only)

- [x] Create isolated branch from exact audited BASE
  `e46e98ed0c53f6c189f4069cc5f2f5d7d4295e5e`.
- [x] Add InternVL3-only v3 support, exact four first-attempt run plan and owner
  runbook; preserve historical v1/v2/Qwen3 and all scientific/runtime bytes.
- [x] Bind exact run ID/shard/null rerun before dataset/backend; native guard
  also rejects unauthorized IDs. Missing tracked v3 cannot fall back to v2.
- [x] Add local synthetic Git tests for Draft, valid/wrong merge structure,
  exact F2, protected pins, model/run/shard/rerun rejection and static preflight
  without dataset/model/GPU/network operations.
- [x] D9R22-26 and InternVL3 focused regressions: 150 tests PASS (Python 3.11.9).
  Two historical D9R22/23 scope-allowlist tests independently FAIL on exact BASE;
  they remain unchanged and were excluded from that focused passing set.
- [ ] Separate independent audit and Research Lead / ChatGPT review.
- [ ] Final Standard Merge Commit and post-merge production commit verification.
- [ ] Future Kaggle owner runtime/snapshot checks and the four first attempts,
  only after effective authority; no execution in Codex.

F1/F2 SHAs and final authority-test results are recorded in the Draft PR handoff
because F2 is created only after F1. No full repository suite requested/run.
Draft authority remains ineffective. `reruns=[]`; Qwen3 paused/unavailable under
v3; Qwen2.5 not rerun; Moondream not authorized. No model, GPU, real dataset,
production, provisioning, Antigravity call or merge occurs in this task.
