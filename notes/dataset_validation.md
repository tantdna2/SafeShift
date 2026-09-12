# Dataset Validation — W1, Bước 3

Kiểm tra chất lượng triplet InspecSafe-V1 theo schema đã audit và manifest Bước 2.
Chỉ đọc `Annotations`; không sửa dữ liệu gốc, không loại sample, không thay domain,
split, safety level hoặc object labels. Không thực hiện duplicate image search,
near-duplicates, leakage, visual audit, taxonomy, metric hoặc VLM.

## Tái lập và môi trường

Repository trước bước này chưa có dependency management; manifest chỉ dùng stdlib.
Thêm `requirements-validation.txt` với **Pillow==12.3.0** để kiểm tra ảnh bằng codec
thực tế, thay vì chỉ nhận diện header. Python >=3.11; môi trường audit local dùng
Python 3.11.9 và virtual environment `.venv`. Dependency này chỉ cần cho validation
và tests validation, không cần cho manifest builder độc lập.

PowerShell, từ repository root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-validation.txt
.venv\Scripts\Activate.ps1
python -m unittest discover -v
python scripts/validate_dataset.py --dataset-root data/raw/InspecSafe-V1 --output data/manifests/dataset_validation.json --verify-image-data
```

Có thể thay `python` ở hai lệnh cuối bằng `.venv\Scripts\python.exe` mà không cần
activate. CLI giải quyết mọi path theo repository root, kể cả khi gọi từ nơi khác.
Output phải là JSON trong repository, nằm ngoài dataset root và `data/raw` sau
resolve symlink. Report được ghi atomically; không ghi vào file input.

## Method và quy tắc

- Tái sử dụng `iter_sample_candidates`, `sample_metadata`, `image_format_from_header`,
  `infer_text_domain`, `repository_path` và regression reference của manifest.
  Refactor manifest chỉ tách helper; không đổi schema, vocabulary hoặc CSV fields.
- Inventory hợp tất cả stems, kể cả annotation mồ côi. Mỗi candidate được kiểm tra
  độc lập cho cả ba file. Stem không khớp tạo candidate mồ côi riêng; không tự ghép.
  Duplicate sample ID được báo ERROR cho **mọi** occurrence, gồm occurrence đầu.
- Đọc/hash toàn bộ bytes của mỗi file. Magic JPEG/PNG độc lập với extension.
  Pillow `Image.open().size` lấy dimensions thực tế; `verify()` rồi reopen và `load()`
  để kiểm tra và decode pixels. Không bật `LOAD_TRUNCATED_IMAGES`.
  Nguồn API: [Pillow Image](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.verify),
  dependency: [Pillow 12.3.0](https://pypi.org/project/pillow/12.3.0/).
- JSON phải parse thành object; shapes là list; width/height là int dương, loại bool.
  Mỗi shape phải là object, label là string, shape_type được kiểm tra, points là
  list các list `[x, y]` chứa int/float finite, không chấp nhận bool.
- Polygon: đếm số điểm, số điểm duy nhất theo numeric equality; shoelace dùng
  rational arithmetic trên số đã parse để tránh overflow/cancellation. Zero-area
  nghĩa là diện tích đại số bằng đúng 0, không dùng epsilon. Đây là **geometric
  degeneracy check**, không phải full validity/self-intersection check. Một polygon
  có thể đồng thời có nhiều issue; `degenerate_polygon` đếm union một lần/shape.
- Bounds là miền liên tục đóng `0 <= x <= width`, `0 <= y <= height`. Dùng binary
  dimensions khi đọc được, JSON hợp lệ làm fallback. Không clamp; chưa diễn giải
  thành quy ước pixel-index hay metric. Mismatch dimensions giữ cả hai giá trị.
- Raw labels giữ nguyên Unicode, casing, whitespace; report frequency cho từng
  string, unique count và nhóm candidate khác casing/whitespace. Khóa phụ dùng
  strip/casefold chỉ để so sánh candidate, không sửa hoặc merge raw class.
- TXT decode strict UTF-8, giữ nguyên text trong quá trình kiểm tra nhưng không
  xuất text vào report. `len(text.splitlines())` là số dòng (newline cuối không tạo
  dòng rỗng thêm). Cảnh báo control Unicode Cc/Cf trừ TAB/CR/LF; NUL đếm riêng.
  Domain chỉ infer theo đúng 24 audited openings, không strip/fuzzy match, không
  parse safety level từ TXT. Domain mismatch giữ song song hai nguồn.
- `imagePath` có mặt phải là string; chỉ so basename, chấp nhận separator `/` và
  `\`. Không xuất nội dung path metadata vào report. Mismatch không rewrite JSON.
- `imageData` có thể thiếu/null; nếu có dữ liệu phải là string. Chuỗi rỗng được
  cảnh báo. `--verify-image-data` bật Base64 strict (`validate=True`, không bỏ
  whitespace, không hỗ trợ data URI), so SHA-256 decoded bytes với external image
  cùng sample. Không tìm hash trùng giữa samples. Mismatch bytes không đồng nghĩa
  mismatch pixels; external image vẫn được verify/decode độc lập.
- Xử lý một triplet/JSON/Base64 mỗi lần; không cache embedded images toàn dataset.
  Đây không phải streaming JSON/Base64 parser: peak memory vẫn phụ thuộc sample
  lớn nhất, decoded pixel buffer và report metadata. Raw text/imageData/pixels
  không đi vào report. Hash bao phủ bytes đã đọc, không phải snapshot filesystem
  chống thay đổi đồng thời; không chỉnh dataset trong lúc chạy.
- Cross-table `data_type × safety_level` là thống kê quan sát, không semantic rule.
  Point được xác định bằng relative folder path; instance IDs giữ leading zeros.
  Đo sequence bắt đầu từ `001`, missing IDs đến max observed, cả `000` bị cảnh báo;
  không suy rằng frame cuối sau max observed bị thiếu. Point ID dùng lại ở nhiều
  folder là warning, không phải bằng chứng leakage.

## Severity, counts và exit code

| Mức | Issue |
| --- | --- |
| ERROR | File thiếu/không đọc được; magic lạ, verify/decode thất bại; JSON không parse/object; dimensions, shapes, shape object, label type không hợp lệ; label rỗng/whitespace-only; points malformed/nonfinite; shape_type thiếu/rỗng/non-string; metadata tên sai; sample ID trùng; TXT không UTF-8/rỗng/whitespace-only; imagePath/imageData sai kiểu; Base64 không hợp lệ khi bật option. |
| WARNING | PNG mang đuôi .jpg, decoder warning; binary/JSON dimensions khác; non-polygon có string type; polygon <3 points/<3 unique/zero-area/out-of-bounds; label có whitespace đầu/cuối; multiline/control TXT, unknown text domain, domain mismatch; imagePath basename khác; imageData rỗng hoặc decoded bytes khác external; sequence gaps/000 hoặc point ID dùng lại. |
| Structural ERROR | Thiếu layout branch, entry lạ, empty point hoặc không có candidate; không thể xác nhận audit toàn bộ scope. |

`valid_samples` = samples không có ERROR, **bao gồm warning-only**. `clean_samples`
không có issue. `samples_with_errors` và `samples_with_warnings` có thể overlap.
`errors_count`/`warnings_count` đếm issue occurrences, không phải số samples.
`invalid_labels` là union non-string/empty/whitespace-only; padding và Unicode
được đếm riêng, Unicode tự thân không phải issue. `malformed_polygon` chỉ đếm
polygon có points sai cấu trúc, khác các polygon parse được nhưng degenerate.
`duplicate_sample_ids` đếm số occurrences bị ảnh hưởng; duplicate point count đếm IDs.
Unique points/distribution bao phủ các folder có candidate; empty folder báo structural.

`incomplete_malformed` phục vụ đối chiếu kiểm tra cơ bản của manifest, không bao
gồm các kiểm tra sâu mới như polygon geometry, full decode hoặc Base64. Đếm một
lần/candidate có lỗi thuộc nhóm manifest. Với duplicate IDs, validator đánh dấu cả
occurrence đầu, còn builder chỉ đánh dấu occurrence sau; report không giả vờ hai
count tương đương trên dataset có duplicates.

- **0:** audit hoàn tất, không ERROR. Warning-only và discrepancy-only vẫn exit 0;
  mọi discrepancy vẫn được ghi JSON và in stderr với nhãn `RESEARCH LEAD DISCREPANCY`.
- **1:** runtime/traversal/output/dependency failure hoặc structural issue khiến
  audit không đầy đủ. Structural issue có thể xuất report partial (`audit_complete=false`);
  exception runtime không xuất report mới. Report cũ nếu có phải được coi là stale.
- **2:** audit hoàn tất, có ERROR-level data issues; report vẫn chứa mọi candidate.

CLI in toàn bộ summary, issue counts, discrepancy, output path và exit code.
Không tự bỏ sample hoặc che issue để đạt exit 0.

## Provenance và artifacts

JSON có run ID/UTC, Git commit/status, source SHA-256, Python/platform, Pillow và
codec versions, command/options, dataset path tương đối, input fingerprint,
summary, detailed sample issues và point/instance inventory. Upstream release,
URL và archive checksums chưa xác minh trong bước này nên ghi null.

Input fingerprint hash JSON lines `[repo-relative path, full-file SHA-256]` cho
jpg/json/txt theo thứ tự cố định; file lỗi có marker MISSING/UNREADABLE. Chỉ bao phủ
candidate triplets, không archive/Other_modalities/Parameters. Serialization khác
manifest fingerprint (không có modality flag), nên không so trực tiếp hai digest.
Đối chiếu số liệu bằng `REGRESSION_EXPECTED` và `SCHEMA_EXPECTED`; expected values
không điều khiển traversal hoặc sửa observed counts. Không dùng random/seed.

Report chi tiết `data/manifests/dataset_validation.json` được ignore và giữ local:
có hàng nghìn sample IDs/path/nhãn, quyền chia sẻ dataset chưa được chốt. Chỉ commit
code, synthetic tests và summary trong tài liệu này; không commit raw data hoặc ảnh.

## Kết quả kiểm chứng — 2026-09-13 (UTC+07)

Full run theo lệnh trên hoàn tất với **exit 0**, `audit_complete=true`.
Run ID: `validation-20260912T173300220131Z`; UTC: `2026-09-12T17:33:00.220131+00:00`.
Git parent: `9fa0dd813d4dd192787a989cac2278a2f65a003c`, cùng implementation chưa
commit; source checksums và Git status cụ thể nằm trong report local. Platform:
`Windows-10-10.0.26200-SP0`, Python `3.11.9`, Pillow `12.3.0`, libjpeg `8.0`,
zlib `1.3.1.zlib-ng`. **66/66 tests synthetic pass**, gồm 29 manifest tests và
37 validation tests; chạy bằng `.venv\Scripts\python.exe -m unittest discover -v`.

| Kiểm tra | Kết quả đo |
| --- | ---: |
| Total / valid (không ERROR) | 5.013 / 5.013 |
| Samples có ERROR / WARNING / không issue | 0 / 5.013 / 0 |
| ERROR / WARNING issue occurrences | 0 / 5.496 |
| Train / test | 3.763 / 1.250 |
| Normal_data / Anomaly_data | 4.013 / 1.000 |
| Missing / unreadable files | 0 / 0 |
| Malformed JSON / invalid UTF-8 TXT | 0 / 0 |
| JPEG / PNG content / unknown format | 4.969 / 44 / 0 |
| Pillow verify + pixel decode pass / failure | 5.013 / 0 |
| Binary dimensions match / mismatch / unavailable | 5.013 / 0 / 0 |
| Total shapes / polygon / non-polygon | 37.434 / 37.434 / 0 |
| Malformed shapes / points / polygons | 0 / 0 / 0 |
| Polygon <3 points / <3 unique points / zero-area | 0 / 0 / 0 |
| Degenerate polygon (union) | 0 |
| Out-of-bounds polygons / affected samples | 309 / 276 |
| Invalid labels / padded labels | 0 / 0 |
| Unique raw labels / Unicode occurrences | 231 / 1 (`出口`) |
| Case/whitespace variant candidate groups | 0 |
| Empty / whitespace-only / multiline TXT | 0 / 0 / 0 |
| TXT control / NUL / unknown domain | 0 / 0 / 0 |
| TXT một dòng | 5.013 |
| Folder/text domain mismatch | 36 |
| JSON imagePath basename mismatch | 5.013 |
| imageData checked / skipped / invalid Base64 | 5.013 / 0 / 0 |
| imageData bytes match / mismatch external | 4.919 / 94 |
| imageData absent/null/empty hoặc comparison unavailable | 0 |
| Unique point folders / unique point IDs | 3.234 / 3.234 |
| Duplicate sample occurrences / reused point IDs | 0 / 0 |
| Non-consecutive instance sequences | 0 |
| Incomplete/malformed theo nhóm checks manifest / structural errors | 0 / 0 |

Tất cả 5.013 samples có WARNING vì `imagePath` khác basename của triplet trên đĩa.
Tổng 5.496 warnings = 5.013 imagePath + 309 polygon bounds + 94 imageData bytes
+ 44 PNG extension + 36 domain mismatch. Không có sample bị loại hoặc file bị sửa.

Cross-table **quan sát trên bản local này**, chưa được xác nhận là official semantic rule:

| data_type | Level01 | Level02 | Level03 | Level04 |
| --- | ---: | ---: | ---: | ---: |
| Normal_data | 0 | 0 | 0 | 4.013 |
| Anomaly_data | 659 | 326 | 15 | 0 |

Distribution số instance mỗi point, đếm point folders:

| Nhóm | 1 instance | 2 instances | 3 instances | 4 instances |
| --- | ---: | ---: | ---: | ---: |
| train/Normal_data | 645 | 836 | 79 | 115 |
| test/Normal_data | 216 | 282 | 25 | 36 |
| train/Anomaly_data | 749 | 0 | 0 | 0 |
| test/Anomaly_data | 251 | 0 | 0 | 0 |
| Tổng | 1.861 | 1.118 | 104 | 151 |

Mọi Anomaly point có `001`; Normal points có 1–4 instances liên tiếp từ `001`.
Instance IDs và per-point inventory đầy đủ nằm trong report local.

Input SHA-256: `1a52f9078d53bddcdcd8400486a6e22f7688c8c20dc85b481b128f94c723399c`.
Artifact local: `data/manifests/dataset_validation.json`, **4.834.176 bytes** ở lần
chạy này; giữ local vì kích thước và quyền chia sẻ metadata chưa xác minh.
Artifact SHA-256: `f5556fe1f48d85652577e6416d7f11639be8aa1a4797f1c4fe10c10befc62117`.

## Phát hiện và discrepancies gửi Research Lead

**Regression counts Bước 2:** khớp toàn bộ các số đã yêu cầu; không discrepancy.
Các automated numeric schema checks (shape count, raw labels, point count,
dimensions, shape type, empty/multiline TXT) cũng khớp. `schema_discrepancies=[]`
chỉ áp dụng cho tập checks này, không chứng nhận mọi câu trong tài liệu schema.

1. **imagePath không phản ánh tên triplet hiện tại:** kiểm tra lại trực tiếp JSON
   của các sample cho thấy basename là tên nguồn khác, chứa ID/tên frame dài;
   không phải lỗi xử lý separator. Ví dụ metadata của
   `coal_conveyor-Level04-SuspendedRail-000560-001` kết thúc bằng
   `_frame_000001.jpg`, thay vì basename của sample. Không suy nguồn/timestamp
   chính thức từ chuỗi đó. Điều này khác ví dụ `imagePath` bằng sample basename
   trong schema §5.1. Không đổi schema hoặc rewrite annotation; giữ WARNING vì
   triplet vẫn liên kết rõ bằng folder và stems trên đĩa.
2. **309 polygon vượt bounds trên 276 samples:** 132 train Normal, 63 train
   Anomaly, 65 test Normal, 16 test Anomaly. Kiểm tra lại coordinates của các
   sample đầu xác nhận giá trị âm thực tế (ví dụ x = -2.6422018348623855), không
   phải do mismatch dimensions. Đây là phát hiện mới ngoài header/schema audit,
   chưa có baseline count trước đó; không clamp hay tự loại polygon/sample.
3. **94 imageData khác bytes ảnh ngoài:** đều Normal_data, 72 train và 22 test.
   Base64 decode strict hợp lệ; external image đều verify/decode thành công.
   Chỉ kết luận byte mismatch, chưa kiểm tra decoded embedded pixels để kết luận
   cùng/khác nội dung hoặc nguồn nào chuẩn. Chuyển review annotation/image pairing.
4. **Sai số có sẵn trong narrative schema §11.3:** đếm từ sample metadata trong
   report cho `folder_domain=metallurgy` cho thấy train Normal = **534**, test
   Normal = **177** (tổng Normal 711), khác con số **271/90** được ghi tại §11.3.
   Train Anomaly = 9, test Anomaly = 0 vẫn khớp. Đây là discrepancy tài liệu,
   không sửa label/domain hoặc `notes/dataset_schema.md` trong task này.

Các bước review trên chỉ đọc fields cần thiết từng JSON; không xuất raw text,
embedded data hoặc tên nguồn dài vào artifact được commit. Không chạy image
hash matching giữa samples hoặc duplicate/leakage search.

## Giới hạn và chuyển bước

Verify/decode thành công chỉ nói rằng Pillow/codec đã đọc được ảnh; không chứng minh
ảnh không có mọi dạng corruption hoặc đúng nội dung ngữ nghĩa. JPEG decoder có thể
chấp nhận một số bất thường; không kiểm tra nội dung cảm biến hoặc modality khác.
Không kiểm tra self-intersection, độ đúng nhãn bằng hình ảnh hoặc spelling semantics.
Variant candidates không phải taxonomy; mọi đề xuất đổi nhãn/domain/split/metric
vẫn phải được thảo luận và ghi `DECISIONS.md` trước khi áp dụng.

Chuyển Bước 4: exact/near-duplicate và leakage cần task riêng, chưa có kết quả ở đây.
Chuyển Bước 5/visual audit và protocol: review polygon warnings, domain conflicts,
label variants và tính thích hợp của annotations cho nghiên cứu; không loại mẫu
chỉ vì warning. Chưa đóng distribution audit tổng thể, feasibility hoặc visual audit.
