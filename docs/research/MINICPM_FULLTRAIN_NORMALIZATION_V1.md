# MiniCPM-V-4 Full-TRAIN Normalization V1

Ngày 26/11/2026 (Asia/Bangkok), Owner trực tiếp cho phép chuyển đúng 205 đầu
ra đã lưu bằng CPU. MiniCPM trả object JSON có một khóa `safety_level` với
giá trị chính xác `no abnormalities observed`. V1 áp dụng ánh xạ sang `Level04`
đã định nghĩa trong prompt C1, giữ cả trạng thái và dự đoán gốc để đối chiếu.
[Quyết định Owner](DECISIONS.md#dec-20261126-owner-minicpm-fulltrain-normalization-v1),
[prompt C1](../../configs/pilot/classification_c1.txt).

## Kết quả thực tế trên TRAIN

| Chỉ tiêu | C1 gốc | Normalization V1 |
| --- | ---: | ---: |
| Tổng ID | 3.763 | 3.763 |
| SUCCESS | 3.558 | 3.763 |
| INVALID | 205 | 0 |
| TECHNICAL_ERROR | 0 | 0 |
| NOT_ATTEMPTED | 0 | 0 |
| Level01 | 145 | 145 |
| Level02 | 206 | 206 |
| Level03 | 286 | 286 |
| Level04 | 2.921 | 3.126 |
| Độ phủ nhãn hợp lệ | 94,55% | 100% |

Fast `status` đã chạy lại ở checkout Operator của PR #212
`5f12a752acd636878fb6044c00185e7af5e2ae63`. Trạng thái gốc là
`PENDING_FINAL_RECONCILIATION`, `next_ordinal=3763` và `active=null`.
V1 dùng đúng snapshot đã được đối chiếu ở PR #213. Công cụ kiểm SHA256
registration và chuỗi 30 event trong hai journal, digest của cohort, SHA256
của 13 ZIP attempt ở cả hai bản và digest của danh sách 205 raw SHA256 theo
ordinal. Nó kiểm SHA256 và danh tính của từng raw member trong 205 ca chuyển
đổi. Đối chiếu riêng trên toàn bộ 3.763 record xác nhận đúng thứ tự, duy nhất
từng ID, giữ mọi trường gốc của 3.558 `SUCCESS`, và chỉ đổi `status`/`label`
trong các trường gốc của 205 `INVALID`. Hai lần chạy cho artifact giống từng
byte. Kiểm SHA256 trước và sau trên 90 tệp nguồn gồm hai registration, 60
event, 26 ZIP và hai tệp prompt/parser cho kết quả giống nhau. Phép đối chiếu
dùng metadata TRAIN và dự đoán đã lưu, không đọc ảnh hoặc nhãn gốc.
[Parent và cách tái kiểm Fast](MINICPM_FULLTRAIN_INVALID_REVIEW_20261126.md),
[xác minh hậu merge PR #213](https://github.com/tantdna2/SafeShift/pull/213#issuecomment-7184395149).

## Artifact cục bộ và SHA256

Thư mục trong checkout chạy công cụ là
`data/processed/minicpm-fulltrain-normalization-v1/`. Toàn bộ artifact ở trong
thư mục Git-ignored. `samples.csv` dùng `sample_id`, `split`, `status` và
`generated_label` theo cách đặt tên của bảng phân tích hiện tại. Cột
`original_status` và `original_label` cho phép so sánh cặp trên cùng ID.
`predictions.json` giữ định dạng trường `label` của record Fast, thêm provenance
của từng completion và thông tin nối về record, raw và attempt gốc.

| Tệp | Nội dung | SHA256 |
| --- | --- | --- |
| `predictions.json` | 3.763 dự đoán theo ordinal, parent và nguồn Fast | `eb25d716306eccd3fe3211f7c6f1a7b56941556730dcd46ca21fa94c00a27bb9` |
| `samples.csv` | Bảng dự đoán để ghép theo `sample_id` | `5c5560050909292f06c113c5f576e3c56875a74f88056fd0bb6e683a89366c88` |
| `conversions.csv` | 205 ID đã chuyển, nhãn trước/sau, attempt, ZIP, raw member và SHA256 | `0ea12aee203e5be11af0c86732ce0782da52762ab7904d3bc699ba1cc90aa936` |
| `summary.csv` | Số đếm và độ phủ trước/sau | `1ec42d11574b4ad81d19542f34a84059e914f4b490aa9b00a07a208ea1556946` |
| `receipt.json` | Hash và kích thước bốn artifact, tổng hợp, quyết định, quy tắc và các hash nguồn | `385ceddb799e735e3eecea04457f3a178996e29992e69265762a5031a6cb1fbd` |

## Tạo và tái kiểm

Chạy từ root của checkout chứa công cụ với Python 3.11 trở lên, chỉ dùng
thư viện chuẩn. Cung cấp hai thư mục journal đã được Fast kiểm. Cùng lệnh
đối chiếu từng byte nếu đích đã tồn tại. Có thể chọn một đích mới bên dưới
`data/processed/` bằng `--output`. Công cụ dừng nếu hash, ID, thứ tự hoặc
response của nhóm `INVALID` sai. Công cụ chỉ chấp nhận thư mục đích sẵn có
khi đủ đúng bộ tệp và khớp byte. Receipt được ghi cuối cùng.

```console
python -B -m scripts.normalize_minicpm_fulltrain --primary <minicpm-offline-s9> --mirror <minicpm-offline-s9-mirror>
```

Đối chiếu SHA256 của `receipt.json` với bảng trên, rồi dùng bảng `files` trong
receipt để kiểm SHA256 và kích thước của từng tệp. Bản ghi parent ghim
registration, event 30, cohort, prompt, digest của 205 raw SHA256, commit Fast
và BASE của PR. SHA256 công cụ trong receipt ràng buộc byte nguồn của lần chạy.

## Kiểm thử và phạm vi sử dụng

Trên Windows/Python 3.11.9, 17 kiểm thử V1 đều PASS. Các ca gồm C1 canonical,
cụm Normal chính xác, JSON ngoài quy tắc, sai ID/thứ tự/SHA256, nguồn bất biến,
xung đột tại đích và khả năng tái lập từng byte. Kiểm tra dữ liệu thật chạy
riêng theo quy trình ở trên. [Kiểm thử V1](../../tests/test_minicpm_fulltrain_normalization.py).

Regression `test_pilot`, `test_fulltrain` và `test_qwen_composite` đạt
96/96 PASS. `test_minicpm_serial22_recovery` đạt 5 PASS và 4 SKIP theo điều kiện
Linux của bộ test timeout.

V1 là bản dẫn xuất label-only trên TRAIN đã quan sát, HNLO N/A. Độ phủ ở bảng
trên đo số nhãn canonical. Khả năng so sánh và quyền đưa V1 vào phân tích khoa
học chính thức vẫn chờ quyết định theo O2, và mọi truy cập bổ sung hoặc chia
sẻ ngoài phạm vi hiện có cần quyền O4 tương ứng. Bản gốc vẫn chờ Owner đối
soát provider, phê duyệt gắn hash, final certificate và `official-report`.
Scientific Qualification và phê duyệt học vụ giữ trạng thái riêng.
Draft PR chờ ChatGPT kiểm tra trực tiếp rồi Antigravity kiểm toán độc lập.
[Quy trình Final Admission](../MINICPM_OFFLINE_CONTINUATION.md),
[giao thức Seminar](SEMINAR_PROTOCOL.md).
