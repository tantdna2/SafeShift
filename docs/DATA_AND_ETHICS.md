# Dữ liệu, provenance và giới hạn sử dụng

Foundation V1 không đọc InspecSafe thật. Các thông tin dưới đây kế thừa audit
lịch sử tại `31a04e6`, không phải kiểm kê hoặc thẩm định license mới.

## Nguồn và snapshot

Theo [audit W1](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/w1_dataset_audit.md),
InspecSafe-V1 được truy về
[Hugging Face Tetrabot2026/InspecSafe-V1](https://huggingface.co/datasets/Tetrabot2026/InspecSafe-V1/tree/f3cb7d3e7827c1afc1c5bfd0524257984bba46ab),
commit `f3cb7d3e7827c1afc1c5bfd0524257984bba46ab`, Zenodo
[v1.0.1](https://doi.org/10.5281/zenodo.19885643) và
[repository tác giả](https://github.com/liuzy0708/InspecSafe).
Snapshot local của audit được khôi phục từ backup nội bộ; không coi backup đó
là archive thượng nguồn đã xác minh byte-for-byte. Phân biệt checksum archive,
fingerprint nội dung và checksum artifact của từng run.

Audit ghi 5.013 triplet ảnh/JSON/TXT, 3.763 TRAIN + 1.250 TEST, ở năm miền công
nghiệp. Nhãn an toàn là mức ảnh, lấy từ token thư mục theo hợp đồng lịch sử;
37.434 object polygons không tự trở thành vùng giải thích nguy cơ. Không suy
safety label từ việc có/không có một object polygon hoặc từ output VLM.
Nguồn: [dataset schema](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/dataset_schema.md)
và [feasibility audit](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/research_feasibility_audit.md).

## Raw bất biến và dữ liệu ngoài Git

- Giữ nguyên dữ liệu gốc tại `data/raw/`; không sửa, ghi đè, tái gán nhãn hoặc
  di chuyển mẫu giữa split để làm code chạy được.
- Artifact dẫn xuất local nằm dưới `data/processed/`, có lệnh tái tạo, input
  checksum/version, Git commit, môi trường/dependency versions, cấu hình, seed
  nếu có ngẫu nhiên và provenance đầu ra. Không dùng path riêng của máy.
- Toàn bộ `data/`, dataset archives, ảnh/video, checkpoints, raw outputs lớn,
  `outputs/`, `runs/`, `artifacts/`, cache và secrets bị loại khỏi Git. Không dùng
  Git LFS hoặc `git add -f` để vượt chính sách.
- Chỉ thêm fixture tổng hợp nhỏ hoặc tài liệu/manifest/figure được phép chia sẻ
  sau review; không chứa ảnh thật, full annotation/text, dữ liệu nhúng, credential
  hoặc đường dẫn tuyệt đối. Tests và demo hiện chỉ có bản ghi viết tay trong code.
- Khi có quyền VLM trong tương lai, lưu raw từng mẫu/lần gọi trước parse; giữ ID,
  prompt, model/version, generation config, run/attempt, lỗi và lần chạy dở.
  Contract tham chiếu artifact hiện tại chưa thực hiện việc lưu hay kiểm checksum.

## TRAIN, TEST và nguy cơ leakage

TRAIN trong các báo cáo HNLO đã được quan sát và phân tích; không phải holdout,
dù mô hình được gọi zero-shot hoặc không fine-tune trên dataset. TEST là split
gốc riêng, không phải quyền truy cập tự động. Foundation V1 không mở TEST,
ảnh/annotation hay dữ liệu bị khóa; không tạo split hoặc chọn ngưỡng mới.

Audit W1 ghi 7 cặp exact xuyên split, các ứng viên near-duplicate và bằng chứng
phụ thuộc chuỗi/góc máy. Point ID không trùng giữa split không bảo đảm cảnh/nguồn
độc lập. Có 36 xung đột folder/text domain, Level03 chỉ có 15 ảnh toàn dataset
và TEST metallurgy không có Anomaly. Vì vậy accuracy, AUROC hay recall gộp không
đủ xác nhận độ tin cậy ở mọi miền hoặc lớp hiếm. Nguồn:
[duplicate audit](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/duplicate_leakage_audit.md),
[distribution audit](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/distribution_imbalance_audit.md).

Mọi đề xuất proxy người/thiết bị, cluster theo nguồn, holdout, threshold hoặc
thay đổi metric phải được duyệt và ghi quyết định mới trước áp dụng. Không sửa
dataset/split/nhãn hiện hữu hoặc dùng ngưỡng tốt nhất trên TEST/target.

## Chính sách chia sẻ và kết luận an toàn

[License audit lịch sử](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/source_license_audit.md)
ghi dataset CC-BY-4.0 và phân biệt với quyền của bài báo/figures, code tác giả
và model weights. Chính sách SafeShift vẫn là nghiên cứu học thuật phi thương
mại, không phân phối lại raw dataset; mọi asset thật muốn chia sẻ cần review
nguồn/quyền và bảo vệ định danh cá nhân. Không suy quyền từ license dataset
sang figures bài báo hoặc weights.

SafeShift hiện không cung cấp hệ thống ra quyết định an toàn đã được xác nhận.
Không xem HNLO là xác suất tai nạn, AUROC là calibration hoặc không có false
negative là bảo đảm an toàn. Hạn chế bằng chứng và khác biệt cohort phải đi kèm
mọi trình bày kết quả; xem [RESULTS_AND_LIMITATIONS](RESULTS_AND_LIMITATIONS.md).
