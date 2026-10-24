# Tìm notebook đúng phạm vi

Tại BASE `cf6d4d633fd8bf5179672733211061686c7af6e9` có **32 notebook được Git theo dõi**.
Mục lục này phục vụ truy vết. File nằm trên main hoặc tên có ONE_CLICK không tự
cấp quyền chạy; dùng đúng release/source, authority và run/attempt trong runbook.
Không thực thi notebook ở giai đoạn dọn repository.

## Notebook cần giữ cho kết quả gần đây

| Nhóm | File / mẫu tên | Hồ sơ cần đọc |
| --- | --- | --- |
| Qwen2.5 PA3-R2 | [pa3_r2_full_train_kaggle.ipynb](pa3_r2_full_train_kaggle.ipynb) | [R2 runbook](../notes/pa3_r2_runbook.md), [CPU completion](../notes/pa3_r2_cpu_completion_20261015.md). Kết quả gắn với source lịch sử, không phải lần chạy mới. |
| TRAIN V4, hai mô hình × bốn shard | `SafeShift_HNLO_TRAIN_{qwen3,internvl3}_SHARD{0,1,2,3}_V4.ipynb` — 8 file | [TRAIN V4](../notes/hnlo_train_v4_20261019.md), [phân tích kết quả](../notes/three_model_scientific_analysis_20261023.md). Qwen3 V4 chưa hoàn tất cohort gốc. |
| Qwen3 Recovery224 | [SafeShift_QWEN3_S2_RECOVERY224_V1.ipynb](SafeShift_QWEN3_S2_RECOVERY224_V1.ipynb) | [Recovery runbook](../notes/qwen3_s2_recovery224_20261022.md). Cohort bổ sung, `baseline_pooling_allowed=false`. |

## Notebook hỗ trợ kỹ thuật cần giữ

| Nhóm | File / mẫu tên | Giới hạn |
| --- | --- | --- |
| Synthetic HNLO hai mô hình | [SafeShift_HNLO_Qwen3_InternVL3_ONE_CLICK.ipynb](SafeShift_HNLO_Qwen3_InternVL3_ONE_CLICK.ipynb) | [One-click runbook](../notes/hnlo_one_click_runbook_20261017.md); không phải kết quả TRAIN. |
| InternVL3 recovery / CUDA / driver / probe | [RECOVERY_ONE_CLICK](SafeShift_InternVL3_RECOVERY_ONE_CLICK.ipynb), [CUDA_DIAGNOSTIC](SafeShift_InternVL3_CUDA_DIAGNOSTIC.ipynb), [DRIVER_CHECK](SafeShift_InternVL3_DRIVER_CHECK.ipynb), [HNLO_GPU_PROBE](SafeShift_InternVL3_HNLO_GPU_PROBE.ipynb) | 4 notebook có authority riêng; [config index](../configs/README.md) dẫn tới các hợp đồng. |
| Resource pilot8 V3 | [qwen3 V3](SafeShift_HNLO_RESOURCE_PILOT8_qwen3_DATASET_PATH_V3.ipynb), [internvl3 V3](SafeShift_HNLO_RESOURCE_PILOT8_internvl3_DATASET_PATH_V3.ipynb) | [V3 runbook](../notes/resource_pilot8_dataset_path_v3_20261019.md); pilot 8 ảnh không thay đầu ra TRAIN. |

## Notebook lịch sử

| Nhóm | File / mẫu tên | Số file |
| --- | --- | ---: |
| Resource pilot V1/V2 | `SafeShift_HNLO_RESOURCE_PILOT8_{qwen3,internvl3}.ipynb`, các bản `_DATASET_PATH_V2.ipynb` | 4 |
| LS1 | [ls1_qwen2_5_kaggle.ipynb](ls1_qwen2_5_kaggle.ipynb), [ls1_internvl3_kaggle.ipynb](ls1_internvl3_kaggle.ipynb) | 2 |
| PA3 trước R2 | [inputs prep](pa3_inputs_prep_kaggle.ipynb), [native Qwen](pa3_qwen2_5_kaggle.ipynb), [full TRAIN cũ](pa3_qwen_full_train_kaggle.ipynb), [seminar diagnostic](pa3_seminar_direction_kaggle.ipynb) | 4 |
| P2.1 InternVL3 | [source prep](w2_internvl3_p21_source_prep_kaggle.ipynb), [shard0](w2_internvl3_p21_shard0_kaggle.ipynb) | 2 |
| PaliGemma qualification/gate | [D9R9](w2_paligemma_d9r9_kaggle.ipynb), [D9R11](w2_paligemma_d9r11_interface_qualification_kaggle.ipynb), [D9R13](w2_paligemma_d9r13_external_gate_kaggle.ipynb) | 3 |

Tổng các nhóm: 10 notebook gắn kết quả gần đây + 7 hỗ trợ + 15 lịch sử = 32.
Phân nhóm không thay trạng thái qualification, FAIL hoặc quyền thực thi.
Toàn bộ 32 notebook đều xuất hiện trong source lock Recovery224; chưa chuyển vào
`archive/`. [Kế hoạch giai đoạn 2](../notes/repository_organization_phase1_20261024.md)
nêu điều kiện trước mọi thay đổi đường dẫn.

Các script `build_*` trong [scripts](../scripts/) có thể ghi lại notebook,
authority và source lock. Không chạy generator để “làm mới” hồ sơ lịch sử.
Notebook local chưa được Git theo dõi không nằm trong kiểm kê này và không được
đưa vào PR dọn repository.
