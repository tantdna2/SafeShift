# Dataset Manifest Builder — W1, Bước 2

Builder thực thi schema đã khảo sát trong `notes/dataset_schema.md`, mục 1–11.
Phạm vi là inventory các triplet ảnh/JSON/TXT; không chọn ground truth domain,
không đổi split/nhãn và không thực hiện thí nghiệm.

## Tái lập

Yêu cầu Python 3.11 trở lên, chỉ dùng standard library, không cần cài dependency.
Chạy từ repository root:

```console
python -m unittest discover -v
python scripts/build_manifest.py --dataset-root data/raw/InspecSafe-V1 --output data/manifests/dataset_manifest.csv
```

Không truyền tham số cũng sử dụng hai đường dẫn mặc định trên. CLI giải quyết
đường dẫn theo repository root, kể cả khi gọi script từ thư mục khác. Các đường
dẫn nằm ngoài repository và output nằm trong dữ liệu raw đều bị từ chối.

Artifacts local:

- `data/manifests/dataset_manifest.csv`: một row cho mỗi sample, 21 fields theo schema.
- `data/manifests/dataset_manifest.provenance.json`: run ID, UTC, command/config,
  runtime, Git revision/status, checksum code/schema, fingerprint đầu vào,
  checksum CSV, summary và discrepancies.

Exit code: `0` khi validation và đối chiếu audit đều khớp; `1` khi validation/I/O
lỗi; `2` khi xuất được manifest hợp lệ nhưng có discrepancy so với audit W1.
Khi validation lỗi, CLI liệt kê lỗi, không xuất manifest một phần và giữ nguyên
CSV cũ nếu đã tồn tại. Summary lúc lỗi chỉ thống kê các row hợp lệ; số candidate
đã duyệt được báo riêng. Consumer cần kiểm tra exit code để tránh dùng nhầm CSV
cũ sau một lần chạy thất bại.

## Quy ước xử lý và serialization

- Duyệt đúng `{split}/DATA_PATH/{split}/Annotations/{data_type}/{point_folder}`.
  Kiểm kê hợp tất cả stem trong mỗi folder để bắt cả JSON/TXT không có ảnh.
  Folder/file lạ, thiếu nhánh, điểm rỗng và sample ID trùng đều được báo lỗi.
- `sample_id` là stem đầy đủ. `point_id` và `instance_id` là chuỗi, giữ số 0 đầu.
  Khi đọc bằng công cụ tự suy luận kiểu CSV, cần khai báo hai cột này là string.
- TXT decode UTF-8 trực tiếp từ bytes, giữ BOM, CRLF/LF/CR, khoảng trắng, dấu câu
  và newline cuối. CSV cần đọc bằng `csv.DictReader` với `encoding="utf-8"`,
  `newline=""` để roundtrip đúng. Một record CSV có thể chứa nhiều dòng vật lý.
- `text_domain` chỉ khớp chính xác, phân biệt hoa/thường, với các mệnh đề mở đầu
  `In the ... ,` được dẫn chứng tại mục 6, 7, 11 của schema. Danh sách explicit
  nằm trong `TEXT_OPENINGS` của `safeshift/data/manifest.py`. Không strip/lowercase
  văn bản, không tìm keyword trong phần mô tả thiết bị, không suy domain từ folder.
  Biến thể chưa được dẫn chứng hoặc không khớp chính xác nhận `null`.
- Hai domain được giữ song song. Mismatch là `null` khi text domain không xác định;
  các trường hợp khác dùng so sánh trực tiếp. Không có field ground truth cuối cùng.
- `object_labels` là JSON array trong một cell CSV, giữ nguyên Unicode, thứ tự và
  duplicate của `shapes[].label`. Dùng `json.loads(cell)` để đọc lại.
  Null ghi literal `null`; boolean ghi `true`/`false`, cũng đọc bằng `json.loads`.
- `num_shapes = len(shapes)`; `imageWidth`/`imageHeight` phải là integer dương,
  không chấp nhận boolean, float, string, null hoặc thiếu field.
- Chỉ giải mã một JSON mỗi lần, bỏ `imageData` ngay sau parse và chỉ giữ dimensions,
  labels, shape count. Standard-library JSON decoder vẫn tạm đọc toàn bộ một file;
  đây không phải streaming JSON parser. Không cache base64 toàn bộ dataset.
- Format ảnh lấy từ signature JPEG/PNG, độc lập với đuôi `.jpg`. Builder không
  giải mã pixel hay kiểm tra ảnh hỏng sâu bên trong; dimensions lấy từ JSON được
  kiểm tra kiểu/giá trị, không thực hiện lại đối chiếu dimensions với binary header.
- `has_other_modalities` là kiểm tra tồn tại ít nhất một file đúng tên đã xác minh
  (`-visible.mp4`, `-infrared.mp4`, `-sensor.txt`, `-audio.wav`) tại thư mục điểm
  trong `Other_modalities` của cùng split. Folder rỗng hoặc chỉ có file rác không
  được xem là có modality. Không kiểm tra nội dung/độ đầy đủ của các modality này.
- `incomplete_malformed` đếm candidate stem lỗi một lần mỗi candidate;
  `structural_errors` đếm lỗi cấu trúc không quy về sample. Nếu các stem lệch nhau,
  mỗi stem mồ côi là một candidate; không đoán chúng vốn thuộc cùng sample nào.

Fingerprint SHA-256 được tính từ hash **toàn bộ bytes** từng file triplet và tên
file tương đối, cộng cờ modality từng sample. Thứ tự: train/test,
Normal_data/Anomaly_data, folder và stem sắp xếp từ điển; chi tiết serialization
ghi trong provenance. Fingerprint không phải checksum archive và không bao phủ
nội dung Other_modalities/Parameters. Nguồn phát hành, release chi tiết và checksum
archive chưa được xác minh trong task này; provenance ghi `null`, không suy đoán.
Không dùng ngẫu nhiên, seed không áp dụng.

## Kết quả kiểm chứng local — 2026-09-09

Môi trường: Windows, Python 3.11.9, standard library. Dataset: InspecSafe-V1 local
ở đường dẫn mặc định, theo nguồn cấu trúc `notes/dataset_schema.md`.
Lần kiểm chứng dùng parent Git commit `5b444b5d0ca1b2a6a0583796e66e9d9bc87333ca`
cùng code builder mới chưa commit; checksum code cụ thể và trạng thái được lưu
trong provenance local. Lệnh tái lập và artifacts như trên.

| Thống kê | Kết quả |
| --- | ---: |
| Total rows / sample IDs duy nhất | 5.013 |
| Train | 3.763 |
| Test | 1.250 |
| Normal_data | 4.013 |
| Anomaly_data | 1.000 |
| coal_conveyor | 1.121 |
| metallurgy | 720 |
| oil_chemical | 1.023 |
| power | 869 |
| tunnel | 1.280 |
| Level01 | 659 |
| Level02 | 326 |
| Level03 | 15 |
| Level04 | 4.013 |
| Domain mismatch đã xác định | 36 |
| Text domain chưa xác định | 789 |
| JPEG | 4.969 |
| PNG mang đuôi .jpg | 44 |
| Incomplete/malformed | 0 |
| Structural errors | 0 |
| Có other modalities | 4.011 |
| Tổng shapes | 37.434 |

**Đối chiếu audit:** cả 6 regression counts được yêu cầu (total/train/test/mismatch/
JPEG/PNG) đều khớp. Tuy nhiên, ma trận ở mục 11 của schema gán text domain cho cả
5.013 mẫu, trong khi tập mệnh đề explicit được schema dẫn chứng chỉ khớp 4.224 mẫu
trong bản local. 789 mẫu còn lại được giữ `text_domain=null`,
`domain_mismatch=null`: 711 metallurgy, 69 coal_conveyor, 9 oil_chemical (theo folder).
Đây là discrepancy về độ phủ, không phải mẫu bị bỏ. CLI báo
`W1 DISCREPANCY: unknown_text_domain: expected 0, observed 789` và exit `2`.
Không mở rộng rules để ép khớp audit; cần audit bổ sung và ghi bằng chứng cho các
mệnh đề chưa có trong schema trước khi đề xuất mở rộng parser.

Validation: **25 tests synthetic pass** bằng `python -m unittest discover -v`.
Kiểm tra CSV local: 5.013 IDs duy nhất; toàn bộ đường dẫn tương đối trỏ tới file
tồn tại; toàn bộ TXT roundtrip khớp nguyên văn; mỗi list labels có độ dài bằng
num_shapes. Nhãn `出口` được giữ nguyên (1 occurrence); 3.693 samples có nhãn lặp.
CSV không có field `imageData`. Không chạy VLM hoặc kiểm tra pixel/near-duplicates
vì nằm ngoài phạm vi manifest builder.

- CSV: 4.285.037 bytes.
- CSV SHA-256: `4f1b3950c963dfb3b89255546f1c41813f06c00c011a1177ad34e0aea84dd729`.
- Input fingerprint: `7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`.

CSV chứa toàn bộ TXT gốc và quyền chia sẻ chúng chưa được xác minh. Vì vậy CSV
và provenance của lần chạy được giữ local, có ignore riêng; chỉ version control
code, tests synthetic và tài liệu kết quả nhỏ. Không stage dataset/raw.
