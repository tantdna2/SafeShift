# Tìm tài liệu SafeShift

Mục lục chọn lọc tại `main@934575e1c5064e37dc76a42e5267a639eb20dbbc`, ngày 24/10/2026.
Bắt đầu bằng [hướng dẫn repository](../REPOSITORY_GUIDE.md).
Tài liệu được phân theo vai trò; ngày mới hơn không tự thay thế quyết định đã duyệt.

[Báo cáo tổng hợp](reports/README.md) tập trung tại reports; đường dẫn cũ của hai
báo cáo đã chuyển vẫn giữ trang dẫn và anchor. [Giai đoạn 2](reports/repository_organization_phase2_20261024.md)
ghi kiểm tra phụ thuộc, phân loại file và kế hoạch dọn tiếp.

## Kết quả và trạng thái cần đọc trước

| Tài liệu | Vai trò và giới hạn |
| --- | --- |
| [Phân tích ba mô hình 23/10](reports/three_model_scientific_analysis_20261023.md) | Tổng hợp hiện tại trên TRAIN; phân biệt raw audit, saved-score recomputation và kết quả được cung cấp. |
| [Receipt kiểm tra ba mô hình](evidence/three_model_20261023/verification_20261023.json) | Hash đầu vào, phạm vi tái tính và giới hạn S2 gốc; không có raw audit mới. |
| [Gói aggregate của Research Lead](evidence/three_model_20261023/) | Đầu vào giữ nguyên bytes. Đọc diễn giải trong báo cáo khoa học và receipt trước khi dùng số. |
| [Qwen2.5 CPU completion](pa3_r2_cpu_completion_20261015.md), [summary](pa3_r2_cpu_completion_20261015.summary.json) | Bằng chứng raw recomputation PASS trên Linux; giới hạn outer receipt Shard 1 và Windows 1-ULP được giữ nguyên. |
| [Baseline review](seminar_baseline_review_2026.md) | Hồ sơ trình bày baseline Qwen2.5; không phải bảng cập nhật đủ bốn mô hình. |
| [Phạm vi bốn mô hình](pa3_four_model_seminar_scope.md) | Giữ Qwen2.5, Qwen3, InternVL3 và Moondream2; không suy ba mô hình thành nghiên cứu hoàn tất. |

HNLO/PA3 theo [DEC-PA3-011](../DECISIONS.md#dec-pa3-011--proposed-seminar-internal-hazard-score-direction-2026-10-16)
vẫn là hướng **PROPOSED**; [D9R22](w2_d9r22_seminar_scope_redesign.md) vẫn có hiệu lực.
Xem [ROADMAP](../ROADMAP.md), [TASKS](../TASKS.md), [DECISIONS](../DECISIONS.md)
và [EXPERIMENTS](../EXPERIMENTS.md) cùng nhau; checkbox/NOT_RUN trong mục cũ không
phải kết luận về bằng chứng được bổ sung sau đó.

## Hồ sơ kỹ thuật gắn với kết quả gần đây

- [PA3-R2 runbook](pa3_r2_runbook.md) và [CPU handoff trước completion](pa3_r2_cpu_audit_20261015.md).
- [TRAIN V4](hnlo_train_v4_20261019.md): thiết kế, source lock, kiểm tra và lịch sử thay thế PR; trạng thái PREP phải đọc theo release tương ứng.
- [Qwen3 S2 OOM](qwen3_s2_oom_20261022.md): tách lượt đầu với duplicate diagnostic; nguyên nhân OOM chưa xác định.
- [Recovery224](qwen3_s2_recovery224_20261022.md): cohort bổ sung, không tự ghép thành baseline.
- [Capability audit](hnlo_phase2_capability_audit.md), [T1 CPU](hnlo_t1_cpu_results_20261017.md), [raw-logit capture PREP](hnlo_raw_logit_capture_prep_20261017.md): kiểm tra nguồn/token/capture có phạm vi riêng, không đồng nghĩa GPU hoặc TRAIN PASS.
- [One-click](hnlo_one_click_runbook_20261017.md), [CUDA recovery](internvl3_cuda_recovery_20261017.md), [driver diagnostic](internvl3_cuda_diagnostic_20261018.md), [driver loading](internvl3_driver_loading_20261018.md), [HNLO probe](internvl3_hnlo_gpu_probe_20261019.md): tuyến chẩn đoán, không phải kết quả phân loại đầy đủ.

Đối chiếu [notebook index](../notebooks/README.md) và [config index](../configs/README.md)
để tìm đúng notebook/authority. Không dùng quyền của một tuyến cho tuyến khác.

## Nền tảng dữ liệu còn cần dùng

- [Audit W1](w1_dataset_audit.md), [nguồn và license](source_license_audit.md), [schema](dataset_schema.md).
- [Manifest builder](manifest_builder.md), [validation](dataset_validation.md), [phân bố](distribution_imbalance_audit.md).
- [Duplicate/leakage](duplicate_leakage_audit.md), [visual provenance](visual_provenance_review.md), [research feasibility](research_feasibility_audit.md).

Các báo cáo này cung cấp giới hạn dataset, phụ thuộc nguồn và hỗ trợ miền/lớp;
không sửa dữ liệu hoặc thiết kế split trong task tổ chức repository.

## Lịch sử và hợp đồng cần giữ

| Nhóm | Điểm vào |
| --- | --- |
| W2/D9: roster, qualification, grounding | [Protocol brief](w2_protocol_decision_brief.md), [D9R18 roles](w2_d9r18_final_participation_decision.md), [D9R19G5 identity](w2_d9r19g5_execution_identity_relock.md), [D9R19G6 identity](w2_d9r19g6_execution_identity_relock.md) |
| D9R22–27, P2/P2.1 | [D9R22 scope](w2_d9r22_seminar_scope_redesign.md), [D9R27 freeze/authority](w2_d9r27_final_freeze_authority.md), [P2.1 amendment](w2_p21_protocol_amendment.md) |
| LS1 trước PA3 | [Runbook](ls1_runbook.md), [calibration failure](ls1_calibration_failure_analysis.md); code đánh giá có phần vẫn được dùng lại. |
| PA3 synthetic/pilot/full TRAIN đời đầu | [Đề xuất protocol](pa3_research_protocol_proposal.md), [synthetic](pa3_synthetic_runbook.md), [full TRAIN cũ](pa3_full_train_kaggle_runbook.md) |
| Resource pilot và sửa mount V1–V3 | [Pilot8](resource_pilot8_20261019.md), [V2](resource_pilot8_dataset_path_v2_20261019.md), [V3](resource_pilot8_dataset_path_v3_20261019.md) |

“Lịch sử” chỉ vai trò đọc. Giữ nguyên tên, nội dung, hash và các kết quả FAIL/
blocker; nhiều tài liệu thuộc source lock. Các file khác trong thư mục vẫn được
giữ để truy vết, không bị coi là dư thừa vì vắng trong mục lục này.

[Báo cáo tổ chức giai đoạn 1 và kế hoạch giai đoạn 2](reports/repository_organization_phase1_20261024.md)
ghi kiểm kê, phụ thuộc và các Draft PR cần người dùng xử lý riêng.
