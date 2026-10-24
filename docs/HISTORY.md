# Lịch sử SafeShift và ranh giới clean reset

Ngày bảo toàn: **24/10/2026**. Clean reset chỉ thay cấu trúc repository để chuẩn
bị nghiên cứu tiếp theo; main mới **không phải release tương đương thực nghiệm
cũ** và không tự cấp quyền thực thi.

## Snapshot trước reset đã xác minh trên GitHub

| Thành phần | Giá trị |
| --- | --- |
| Main trước dọn | [`31a04e6f7175cca818c63b4de0153246b3f3ecdb`](https://github.com/tantdna2/SafeShift/commit/31a04e6f7175cca818c63b4de0153246b3f3ecdb) |
| Nhánh lưu trữ bất biến | [`legacy/pre-reset-20261024`](https://github.com/tantdna2/SafeShift/tree/legacy/pre-reset-20261024) |
| Annotated tag bất biến | [`safeshift-pre-reset-20261024`](https://github.com/tantdna2/SafeShift/tree/safeshift-pre-reset-20261024) |
| Tag object | `52ead86662be0084aaa50a4e2edc4c64590d9f93` |
| Tree của commit | `8e6a268146ea0a171402ac81b12017dd8331c409` |
| Inventory Git | **693 file, 46 thư mục** không tính root |

Hai ref đã được push cùng nhau, đọc lại từ remote và fetch vào ref kiểm chứng
trước khi xóa file. Cả hai resolve về đúng commit, cùng tree và đủ inventory.
Không force-push, ghi đè ref có sẵn hoặc viết lại lịch sử.

Snapshot giữ nguyên các file đã được Git theo dõi và lịch sử tổ tiên của main.
Dataset, raw outputs/checkpoint và file local ngoài Git tiếp tục ở nơi lưu trữ
cũ; chúng không được đưa vào snapshot hay main mới. Các nhánh PR chưa merge
vẫn có lịch sử riêng và không thuộc tree 693 file này.

## Tra cứu code, notebook và bằng chứng cũ

Tất cả liên kết sau trỏ đến đúng commit trước reset, không phụ thuộc main mới:

| Cần tìm | Nguồn bất biến |
| --- | --- |
| Code/package, script, notebook, test/fixture, môi trường cũ | [Toàn bộ tree](https://github.com/tantdna2/SafeShift/tree/31a04e6f7175cca818c63b4de0153246b3f3ecdb), [hướng dẫn cũ](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/REPOSITORY_GUIDE.md) |
| Quyết định, roadmap, task và log thực nghiệm | [DECISIONS](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/DECISIONS.md), [ROADMAP](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/ROADMAP.md), [TASKS](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/TASKS.md), [EXPERIMENTS](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/EXPERIMENTS.md) |
| Audit dữ liệu W1, license và giới hạn dataset | [Báo cáo W1](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/w1_dataset_audit.md), [license audit](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/source_license_audit.md) |
| Audit raw Qwen2.5 trên CPU Linux và các hạn chế còn lại | [CPU completion PA3-R2](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_r2_cpu_completion_20261015.md) |
| Phân tích ba mô hình và mức kiểm chứng từng kết quả | [Báo cáo 23/10](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/reports/three_model_scientific_analysis_20261023.md), [receipt/evidence nhỏ](https://github.com/tantdna2/SafeShift/tree/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/evidence/three_model_20261023) |
| Runbook TRAIN V4 và Recovery224 | [TRAIN V4](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/hnlo_train_v4_20261019.md), [Recovery224](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/qwen3_s2_recovery224_20261022.md) |
| Phạm vi tổ chức giai đoạn 2 trước clean reset | [Báo cáo PR #128](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/reports/repository_organization_phase2_20261024.md) |

Đọc file lịch sử từ repository root, không checkout đè workspace đang làm việc:

```console
git fetch origin tag safeshift-pre-reset-20261024
git show safeshift-pre-reset-20261024:DECISIONS.md
git ls-tree -r --name-only safeshift-pre-reset-20261024
```

Tag này là snapshot bảo toàn, **không phải một execution release mới**. Khi cần
kiểm tra phiên bản thực nghiệm, tìm đúng source/release commit trong runbook,
authority và receipt của lần chạy, rồi dùng checkout riêng tại commit đó với
đúng môi trường và artifact gốc. Ví dụ CPU audit PA3-R2 dùng execution source
[`c1527713ca7175b3d71248d51f1715693795e6e8`](https://github.com/tantdna2/SafeShift/commit/c1527713ca7175b3d71248d51f1715693795e6e8),
theo CPU completion đã dẫn. Không chạy notebook từ snapshot tài liệu hoặc main
mới, sửa source lock hay tái tạo kết quả cũ để làm chúng tương thích HEAD.
Quyền cũ chỉ áp dụng cho đúng source/release/run/attempt; không chuyển sang main mới.

## Quyết định có hiệu lực và hướng đề xuất

- **D9R22 vẫn có hiệu lực** trong hồ sơ nghiên cứu. Clean reset không hủy hoặc
  sửa quyết định đó; tra nội dung gốc trong decision log và config của snapshot.
- **DEC-PA3-011 vẫn PROPOSED**, chờ Research Lead phê duyệt cuối. Hướng **A/C
  chưa được phê duyệt**; reset không chọn hướng nghiên cứu, tạo protocol hay mô hình mới.
- Yêu cầu Seminar đủ Qwen2.5-VL-3B-Instruct, Qwen3-VL-8B-Instruct,
  InternVL3-2B-hf và Moondream2 được giữ trong
  [hồ sơ phạm vi bốn mô hình](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_four_model_seminar_scope.md).
  Không suy từ reset rằng đã bỏ hoặc thay một mô hình.
- Kết quả/AUROC và trạng thái audit cũ giữ nguyên tại nguồn gốc. TRAIN đã phơi
  nhiễm không trở thành holdout; kiểm tra saved score/sidecar không trở thành raw
  audit. Qwen3 V4 và Recovery224 giữ ranh giới cohort, `baseline_pooling_allowed=false`;
  giới hạn về bằng chứng S2 gốc và outer receipt Shard 1 Qwen2.5 vẫn còn.
- Mọi hướng, protocol, metric/split/nhãn và quyền thực nghiệm mới cần được duyệt
  riêng. Reset không chạy GPU/inference, không đọc TEST/dữ liệu bị khóa và không
  cấp thêm quyền từ các grant lịch sử.

## Main mới và ảnh hưởng khi hợp nhất

Cấu trúc mới có **7 file, 3 thư mục** không tính root: bốn file root
`README.md`, `AGENTS.md`, `.gitignore`, `.gitattributes`, cùng `docs/HISTORY.md`,
`safeshift/__init__.py`, `tests/test_smoke.py`. Năm đường dẫn có sẵn được viết lại;
hai đường dẫn mới được thêm; 688 đường dẫn cũ được xóa khỏi tree hiện tại.
Không chuyển file cũ vào `archive/` trên main.

Giữ tài liệu giới thiệu/quy tắc, bảo vệ dữ liệu/line endings, hướng dẫn tìm lại
lịch sử, package Python không phụ thuộc và smoke test bằng thư viện chuẩn.
Chưa cần dependency, config hoặc CI cho nghiên cứu mới. Các workflow notebook,
inference/GPU, dataset audit/parser, PA3/HNLO/LS1, tổng hợp/replay kết quả và bộ
test lịch sử không còn chạy trực tiếp trên main mới; chúng thuộc source lịch sử.

Sáu PR dưới đây được xác minh **OPEN/DRAFT** trước reset; không sửa hoặc đóng:

| PR | HEAD được bảo toàn |
| --- | --- |
| [#67](https://github.com/tantdna2/SafeShift/pull/67) | `e85300ab3ec122f819a2685613332578f7e203d8` |
| [#99](https://github.com/tantdna2/SafeShift/pull/99) | `6effffea024b664b68366e05c8df1d7ad50de8af` |
| [#101](https://github.com/tantdna2/SafeShift/pull/101) | `0e40bd8fd364ea6a2585f2704b0eb65fe3003728` |
| [#102](https://github.com/tantdna2/SafeShift/pull/102) | `78b45b688abe609edcfa27b9bcf9874d42ed984a` |
| [#117](https://github.com/tantdna2/SafeShift/pull/117) | `b2c381045f06b567a9cb89793dff6b4b0cacc097` |
| [#121](https://github.com/tantdna2/SafeShift/pull/121) | `81ae8b10aa002128d601fcd01d78297a87a69237` |

Sau merge reset, các PR này có thể xung đột sửa/xóa, thiếu dependency hoặc đưa
code cũ trở lại nếu merge nguyên nhánh. Source lock và authority của chúng
không áp dụng cho scaffold mới. Research Lead cần quyết định riêng về từng PR;
không tự rebase, cập nhật lock, đóng hoặc merge chúng trong task reset.
Giữ reset ở Draft PR để ChatGPT kiểm tra GitHub và phê duyệt merge sau.
