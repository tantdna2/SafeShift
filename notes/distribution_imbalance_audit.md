# Data Distribution & Imbalance Audit — W1, Bước 6

## 1. Objective

Kiểm tra phân bố/mất cân bằng InspecSafe-V1, khác biệt train/test, độ phủ anomaly và raw object labels; xác định yếu tố gây nhiễu cần mang sang W2. Đơn vị đếm dataset là sample/triplet; đơn vị tần suất object label là shape instance. Giữ nguyên split, nhãn và raw dataset. Không chạy VLM, train model, resize ảnh hoặc tạo taxonomy.

## 2. Data version/fingerprint

Nguồn: bản local `data/raw/InspecSafe-V1/`, schema tại [dataset_schema.md](dataset_schema.md), parser tại [manifest.py](../safeshift/data/manifest.py). Upstream URL/release và checksum archive chưa được xác minh; provenance ghi null. Không có `data/manifests/dataset_manifest.csv` khi bắt đầu run; metadata được đọc lại trực tiếp từ toàn bộ triplets.

Run `distribution-20260915T025423175983Z`, UTC `2026-09-15T02:54:23.175983+00:00`; parent Git `ab0f1f6cbdf2be7f485337e3a6c4197f3edfbc2c` cùng implementation chưa commit. Source SHA-256 và Git source status được lưu trong JSON. Python 3.11.9, Pillow 12.3.0, Windows; runtime 126.488 giây, không gồm publication. Không dùng ngẫu nhiên, seed=null.

Input fingerprint: `7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`. Dùng đúng serialization của manifest Bước 2: SHA-256 các ASCII JSON lines `[repo-relative path, full-file SHA-256]` cho jpg/json/txt từng sample, tiếp theo `[sample_id, has_other_modalities]`; thứ tự train/test, Normal_data/Anomaly_data, folder/stem sorted. Bao phủ toàn bộ bytes triplet và modality presence; không bao phủ archive, Parameters hoặc modality contents. Không so trực tiếp với fingerprint Bước 3–4 vì hai bước đó không có modality flag.

Local artifact: `data/manifests/distribution_imbalance_audit.json` (433,209 bytes), SHA-256 `2dbb706c3975dc633d12d4a0ac71f48731b1fcb3e9885c752142d09eab1d5492`. Full JSON được ignore, không commit. Vị trí `data/manifests/` theo deliverable cụ thể của task. Không xuất raw TXT, embedded imageData hoặc pixel content.

**Full audit: exit 0; 5,013 samples; 26 regression comparisons; 0 discrepancies.** Fingerprint khớp manifest Bước 2 được ghi tại [manifest_builder.md](manifest_builder.md).

## 3. Methods

Implementation: [distribution.py](../safeshift/data/distribution.py), CLI: [audit_distribution.py](../scripts/audit_distribution.py), tests: [test_distribution.py](../tests/test_distribution.py).

```powershell
.venv\Scripts\Activate.ps1
python -m unittest discover -v
python scripts/audit_distribution.py --dataset-root data/raw/InspecSafe-V1 --output data/manifests/distribution_imbalance_audit.json
```

Dependencies dùng lại `requirements-validation.txt` (Pillow==12.3.0), Python >=3.11. CLI resolve paths từ repository root; output JSON phải trong repository và ngoài raw/dataset root, kể cả sau resolve symlink. Ghi atomically. Exit 0 khi hoàn tất và regression khớp; 2 khi hoàn tất có discrepancy; 1 khi lỗi input/runtime/output. Lỗi input không xuất report một phần; report cũ nếu có là stale. Expected counts chỉ dùng sau aggregation để đối chiếu, không điều khiển count.

- Dùng `collect_manifest` hiện có: kiểm kê union stems, kiểm tra triplet và schema, hash toàn bộ file. Không sửa vocabulary text-domain.
- Đọc actual width/height bằng Pillow `Image.open().size` cho mọi external image; đối chiếu JSON dimensions và giữ mismatch riêng. Không lặp full pixel validation.
- Cross-table: field cuối là cột; mọi field trước cùng tạo hàng. `row_percentage = 100 × count / row_total`. Giữ Cartesian product các category đã biết, gồm ô 0; category lạ/null quan sát được cũng được giữ. Hàng N=0 có percentage=null.
- TVD = `0.5 × sum(|p_train(k) − p_test(k)|)` trên hợp categories; mỗi p dùng N của split tương ứng. Báo thêm chênh lệch tuyệt đối theo điểm phần trăm (pp); không hypothesis test, p-value hoặc threshold good/bad.
- Quartiles nội suy tuyến tính tại `(n−1)×p`, p=0.25/0.75; median và mean theo samples. Annotation density ở đây là `num_shapes/sample`, không phải diện tích polygon hoặc shapes/pixel.
- Aspect ratio dùng phân số tối giản chính xác (gcd); 16:9, 4:3 và other. Không tolerance khiến biến thể gần 16:9 bị gộp.
- Cờ chẩn đoán `count=0`, `<10`, `<30` có thể overlap; không phải statistical rule chính thức. Test labels very rare dùng 1–5 instances; báo thêm 1–10; count=0 tách riêng.
- Raw labels giữ nguyên Unicode, spelling, casing, whitespace và synonym; duplicate trong một sample vẫn tăng instance count. Top-frequency ties sắp theo raw string; aggregate ordering deterministic với cùng inputs.

**Validation:** `python -m unittest discover -v`: **143/143 pass, 0 failed** (36 distribution, 29 manifest, 37 validation, 41 duplicate). Fixtures đều synthetic; kiểm tra count/denominator/zero cells, flags, TVD endpoints/partial/empty, dimensions, quartiles, long tail, Unicode/duplicate labels, split/domain coverage, metadata, mismatch, deterministic output, raw immutability, fingerprint, relative paths, CLI errors và atomic-write failure. Không có required check bị bỏ qua.

Sau full run, đối chiếu độc lập bằng Counter trên sample metadata của `data/manifests/dataset_validation.json`: cả 10 cross-tables và các TVD khớp; 66 actual resolutions cùng tần suất của toàn bộ 231 raw labels khớp Bước 3. Kiểm tra tổng từng nhóm annotation, tổng train/test label instances, mismatch, source checksums và scan output không có absolute path/raw TXT/imageData đều pass. Đây là reconciliation với artifact trước đó, không chạy lại validation hay perceptual duplicate audit.

## 4. Cross-tables

Tất cả ô dưới đây là **count (row %)** và có **Row N**. Bảng 3 chiều dùng split+domain làm hàng; 10 bảng full precision nằm tại `cross_tables` trong JSON.

### 4.1. split × data_type

| split | Row N | Anomaly_data | Normal_data |
| --- | --- | --- | --- |
| test | 1250 | 251 (20.08%) | 999 (79.92%) |
| train | 3763 | 749 (19.90%) | 3014 (80.10%) |

### 4.2. split × safety_level

| split | Row N | Level01 | Level02 | Level03 | Level04 |
| --- | --- | --- | --- | --- | --- |
| test | 1250 | 169 (13.52%) | 75 (6.00%) | 7 (0.56%) | 999 (79.92%) |
| train | 3763 | 490 (13.02%) | 251 (6.67%) | 8 (0.21%) | 3014 (80.10%) |

### 4.3. split × folder_domain

| split | Row N | coal_conveyor | metallurgy | oil_chemical | power | tunnel |
| --- | --- | --- | --- | --- | --- | --- |
| test | 1250 | 299 (23.92%) | 177 (14.16%) | 245 (19.60%) | 213 (17.04%) | 316 (25.28%) |
| train | 3763 | 822 (21.84%) | 543 (14.43%) | 778 (20.67%) | 656 (17.43%) | 964 (25.62%) |

### 4.4. split × folder_domain × data_type

| split | folder_domain | Row N | Anomaly_data | Normal_data |
| --- | --- | --- | --- | --- |
| test | coal_conveyor | 299 | 84 (28.09%) | 215 (71.91%) |
| test | metallurgy | 177 | 0 (0.00%) | 177 (100.00%) |
| test | oil_chemical | 245 | 74 (30.20%) | 171 (69.80%) |
| test | power | 213 | 21 (9.86%) | 192 (90.14%) |
| test | tunnel | 316 | 72 (22.78%) | 244 (77.22%) |
| train | coal_conveyor | 822 | 172 (20.92%) | 650 (79.08%) |
| train | metallurgy | 543 | 9 (1.66%) | 534 (98.34%) |
| train | oil_chemical | 778 | 287 (36.89%) | 491 (63.11%) |
| train | power | 656 | 81 (12.35%) | 575 (87.65%) |
| train | tunnel | 964 | 200 (20.75%) | 764 (79.25%) |

### 4.5. split × folder_domain × safety_level

| split | folder_domain | Row N | Level01 | Level02 | Level03 | Level04 |
| --- | --- | --- | --- | --- | --- | --- |
| test | coal_conveyor | 299 | 60 (20.07%) | 21 (7.02%) | 3 (1.00%) | 215 (71.91%) |
| test | metallurgy | 177 | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 177 (100.00%) |
| test | oil_chemical | 245 | 65 (26.53%) | 9 (3.67%) | 0 (0.00%) | 171 (69.80%) |
| test | power | 213 | 2 (0.94%) | 18 (8.45%) | 1 (0.47%) | 192 (90.14%) |
| test | tunnel | 316 | 42 (13.29%) | 27 (8.54%) | 3 (0.95%) | 244 (77.22%) |
| train | coal_conveyor | 822 | 109 (13.26%) | 62 (7.54%) | 1 (0.12%) | 650 (79.08%) |
| train | metallurgy | 543 | 8 (1.47%) | 0 (0.00%) | 1 (0.18%) | 534 (98.34%) |
| train | oil_chemical | 778 | 239 (30.72%) | 48 (6.17%) | 0 (0.00%) | 491 (63.11%) |
| train | power | 656 | 31 (4.73%) | 50 (7.62%) | 0 (0.00%) | 575 (87.65%) |
| train | tunnel | 964 | 103 (10.68%) | 91 (9.44%) | 6 (0.62%) | 764 (79.25%) |

### 4.6. folder_domain × safety_level

| folder_domain | Row N | Level01 | Level02 | Level03 | Level04 |
| --- | --- | --- | --- | --- | --- |
| coal_conveyor | 1121 | 169 (15.08%) | 83 (7.40%) | 4 (0.36%) | 865 (77.16%) |
| metallurgy | 720 | 8 (1.11%) | 0 (0.00%) | 1 (0.14%) | 711 (98.75%) |
| oil_chemical | 1023 | 304 (29.72%) | 57 (5.57%) | 0 (0.00%) | 662 (64.71%) |
| power | 869 | 33 (3.80%) | 68 (7.83%) | 1 (0.12%) | 767 (88.26%) |
| tunnel | 1280 | 145 (11.33%) | 118 (9.22%) | 9 (0.70%) | 1008 (78.75%) |

### 4.7. folder_domain × data_type

| folder_domain | Row N | Anomaly_data | Normal_data |
| --- | --- | --- | --- |
| coal_conveyor | 1121 | 256 (22.84%) | 865 (77.16%) |
| metallurgy | 720 | 9 (1.25%) | 711 (98.75%) |
| oil_chemical | 1023 | 361 (35.29%) | 662 (64.71%) |
| power | 869 | 102 (11.74%) | 767 (88.26%) |
| tunnel | 1280 | 272 (21.25%) | 1008 (78.75%) |

### 4.8. robot_platform × folder_domain

| robot_platform | Row N | coal_conveyor | metallurgy | oil_chemical | power | tunnel |
| --- | --- | --- | --- | --- | --- | --- |
| SuspendedRail | 2642 | 1121 (42.43%) | 59 (2.23%) | 100 (3.79%) | 106 (4.01%) | 1256 (47.54%) |
| Wheeled | 2371 | 0 (0.00%) | 661 (27.88%) | 923 (38.93%) | 763 (32.18%) | 24 (1.01%) |

### 4.9. robot_platform × data_type

| robot_platform | Row N | Anomaly_data | Normal_data |
| --- | --- | --- | --- |
| SuspendedRail | 2642 | 639 (24.19%) | 2003 (75.81%) |
| Wheeled | 2371 | 361 (15.23%) | 2010 (84.77%) |

### 4.10. folder_domain × text_domain

| folder_domain | Row N | coal_conveyor | metallurgy | oil_chemical | power | tunnel |
| --- | --- | --- | --- | --- | --- | --- |
| coal_conveyor | 1121 | 1121 (100.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) |
| metallurgy | 720 | 0 (0.00%) | 712 (98.89%) | 8 (1.11%) | 0 (0.00%) | 0 (0.00%) |
| oil_chemical | 1023 | 0 (0.00%) | 0 (0.00%) | 1023 (100.00%) | 0 (0.00%) | 0 (0.00%) |
| power | 869 | 4 (0.46%) | 0 (0.00%) | 0 (0.00%) | 865 (99.54%) | 0 (0.00%) |
| tunnel | 1280 | 0 (0.00%) | 0 (0.00%) | 24 (1.88%) | 0 (0.00%) | 1256 (98.12%) |

### Marginal distributions

| Field | Category | Count / total | % |
| --- | --- | --- | --- |
| split | test | 1250 / 5013 | 24.9352 |
| split | train | 3763 / 5013 | 75.0648 |
| data_type | Anomaly_data | 1000 / 5013 | 19.9481 |
| data_type | Normal_data | 4013 / 5013 | 80.0519 |
| folder_domain | coal_conveyor | 1121 / 5013 | 22.3619 |
| folder_domain | metallurgy | 720 / 5013 | 14.3627 |
| folder_domain | oil_chemical | 1023 / 5013 | 20.4069 |
| folder_domain | power | 869 / 5013 | 17.3349 |
| folder_domain | tunnel | 1280 / 5013 | 25.5336 |
| text_domain | coal_conveyor | 1125 / 5013 | 22.4417 |
| text_domain | metallurgy | 712 / 5013 | 14.2031 |
| text_domain | oil_chemical | 1055 / 5013 | 21.0453 |
| text_domain | power | 865 / 5013 | 17.2551 |
| text_domain | tunnel | 1256 / 5013 | 25.0549 |
| safety_level | Level01 | 659 / 5013 | 13.1458 |
| safety_level | Level02 | 326 / 5013 | 6.5031 |
| safety_level | Level03 | 15 / 5013 | 0.2992 |
| safety_level | Level04 | 4013 / 5013 | 80.0519 |
| robot_platform | SuspendedRail | 2642 / 5013 | 52.7030 |
| robot_platform | Wheeled | 2371 / 5013 | 47.2970 |

## 5. Safety imbalance

Largest/smallest safety class ratio = Level04/Level03 = 4013/15 = **267.533333:1**. Đây là thống kê mô tả, không phải benchmark metric. Level03 chỉ có **15 samples (0.2992%)**. Overall/train/test/per-domain safety distributions nằm ở §4.2, §4.5, §4.6 và marginals.

### Level03 theo domain và split

| folder_domain | Row N | test | train |
| --- | --- | --- | --- |
| coal_conveyor | 4 | 3 (75.00%) | 1 (25.00%) |
| metallurgy | 1 | 0 (0.00%) | 1 (100.00%) |
| oil_chemical | 0 | 0 (undefined) | 0 (undefined) |
| power | 1 | 1 (100.00%) | 0 (0.00%) |
| tunnel | 9 | 3 (33.33%) | 6 (66.67%) |

| split | Count | Level03 N | % |
| --- | --- | --- | --- |
| test | 7 | 15 | 46.67 |
| train | 8 | 15 | 53.33 |

| robot_platform | Count | Level03 N | % |
| --- | --- | --- | --- |
| SuspendedRail | 15 | 15 | 100.00 |
| Wheeled | 0 | 15 | 0.00 |

Class imbalance cho thấy plain accuracy (độ chính xác tổng thể đơn thuần) có nguy cơ che khuất hiệu năng class hiếm; metric chính thức sẽ được chốt W2.

## 6. Domain imbalance

Độ phủ train/test × Normal/Anomaly đầy đủ ở §4.4. Các ô có ít hơn 30 samples được liệt kê dưới đây; ô 0 vẫn có denominator train/test-domain, không biến thành missing sample.

| split | folder_domain | data_type | count | row N | =0 | <10 | <30 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| test | metallurgy | Anomaly_data | 0 | 177 | true | true | true |
| test | power | Anomaly_data | 21 | 213 | false | false | true |
| train | metallurgy | Anomaly_data | 9 | 543 | false | true | true |

Metallurgy kiểm chứng lại: **train Normal 534, train Anomaly 9, test Normal 177, test Anomaly 0**, tổng 720. Official test metallurgy có 0 anomaly, nên anomaly-sensitive evaluation (đánh giá nhạy với mẫu bất thường) trong domain này bị hạn chế. 8/9 train anomaly có text_domain=oil_chemical; 1/9 có text_domain=metallurgy theo mismatch audit, không chọn nguồn nào làm ground truth.

## 7. Train/test differences

| Field | Train N | Test N | TVD |
| --- | --- | --- | --- |
| folder_domain | 3763 | 1250 | 0.020757268 |
| safety_level | 3763 | 1250 | 0.008458783 |
| data_type | 3763 | 1250 | 0.001756683 |
| robot_platform | 3763 | 1250 | 0.015147276 |

### folder_domain

| Category | Train count / N | Train % | Test count / N | Test % | Absolute Δ pp |
| --- | --- | --- | --- | --- | --- |
| coal_conveyor | 822 / 3763 | 21.8443 | 299 / 1250 | 23.9200 | 2.0757 |
| metallurgy | 543 / 3763 | 14.4300 | 177 / 1250 | 14.1600 | 0.2700 |
| oil_chemical | 778 / 3763 | 20.6750 | 245 / 1250 | 19.6000 | 1.0750 |
| power | 656 / 3763 | 17.4329 | 213 / 1250 | 17.0400 | 0.3929 |
| tunnel | 964 / 3763 | 25.6179 | 316 / 1250 | 25.2800 | 0.3379 |

### safety_level

| Category | Train count / N | Train % | Test count / N | Test % | Absolute Δ pp |
| --- | --- | --- | --- | --- | --- |
| Level01 | 490 / 3763 | 13.0215 | 169 / 1250 | 13.5200 | 0.4985 |
| Level02 | 251 / 3763 | 6.6702 | 75 / 1250 | 6.0000 | 0.6702 |
| Level03 | 8 / 3763 | 0.2126 | 7 / 1250 | 0.5600 | 0.3474 |
| Level04 | 3014 / 3763 | 80.0957 | 999 / 1250 | 79.9200 | 0.1757 |

### data_type

| Category | Train count / N | Train % | Test count / N | Test % | Absolute Δ pp |
| --- | --- | --- | --- | --- | --- |
| Anomaly_data | 749 / 3763 | 19.9043 | 251 / 1250 | 20.0800 | 0.1757 |
| Normal_data | 3014 / 3763 | 80.0957 | 999 / 1250 | 79.9200 | 0.1757 |

### robot_platform

| Category | Train count / N | Train % | Test count / N | Test % | Absolute Δ pp |
| --- | --- | --- | --- | --- | --- |
| SuspendedRail | 1969 / 3763 | 52.3253 | 673 / 1250 | 53.8400 | 1.5147 |
| Wheeled | 1794 / 3763 | 47.6747 | 577 / 1250 | 46.1600 | 1.5147 |

Các TVD này mô tả marginal distributions; không chứng minh hai split độc lập về ảnh, nguồn, sequence hoặc viewpoint. Marginal gần nhau cũng có thể che ô domain×anomaly bằng 0 và class hiếm. Không suy dataset-shift về pixel/semantics chỉ từ categorical TVD.

Khác biệt marginal lớn nhất trong bốn biến là folder_domain (TVD 0.020757); coal_conveyor tăng từ 822/3763 (21.8443%) train lên 299/1250 (23.9200%) test, chênh 2.0757 pp. Khi giữ domain cố định, khác biệt anomaly rõ hơn: coal_conveyor 172/822 (20.92%) train so với 84/299 (28.09%) test; oil_chemical 287/778 (36.89%) so với 74/245 (30.20%). Power test chỉ có 2/213 Level01 (0.94%), so với 31/656 (4.73%) train. Đây là các khác biệt mô tả cần xét ở W2, không gán threshold “shift tốt/xấu”.

## 8. Resolution

Đọc actual dimensions **5013/5013** images; unavailable=0; actual/JSON mismatch=0. Có **66 unique resolutions**. Ba resolution kỳ vọng được đếm lại; other variants là tổng còn lại, không ép khớp.

Ba resolution đầu chiếm 4822/5013 ảnh; **other variants = 191/5013 (3.8101%)**, khớp regression reference.

| Resolution | Count | N images | % |
| --- | --- | --- | --- |
| 2560x1440 | 2576 | 5013 | 51.3864 |
| 1920x1080 | 2124 | 5013 | 42.3698 |
| 1280x720 | 122 | 5013 | 2.4337 |
| 960x540 | 39 | 5013 | 0.7780 |
| 1920x1088 | 27 | 5013 | 0.5386 |
| 2688x1520 | 26 | 5013 | 0.5187 |
| 1944x1200 | 9 | 5013 | 0.1795 |
| 960x544 | 9 | 5013 | 0.1795 |
| 704x576 | 6 | 5013 | 0.1197 |
| 2336x1752 | 5 | 5013 | 0.0997 |
| 720x405 | 5 | 5013 | 0.0997 |
| 940x540 | 4 | 5013 | 0.0798 |
| 2304x1440 | 3 | 5013 | 0.0598 |
| 938x540 | 3 | 5013 | 0.0598 |
| 1278x720 | 2 | 5013 | 0.0399 |
| 720x404 | 2 | 5013 | 0.0399 |
| 720x408 | 2 | 5013 | 0.0399 |
| 1252x703 | 1 | 5013 | 0.0199 |
| 1258x703 | 1 | 5013 | 0.0199 |
| 1266x705 | 1 | 5013 | 0.0199 |
| 1274x720 | 1 | 5013 | 0.0199 |
| 1277x719 | 1 | 5013 | 0.0199 |
| 1440x1080 | 1 | 5013 | 0.0199 |
| 1544x867 | 1 | 5013 | 0.0199 |
| 1547x875 | 1 | 5013 | 0.0199 |
| 1549x871 | 1 | 5013 | 0.0199 |
| 1551x874 | 1 | 5013 | 0.0199 |
| 1553x873 | 1 | 5013 | 0.0199 |
| 1555x874 | 1 | 5013 | 0.0199 |
| 1898x1076 | 1 | 5013 | 0.0199 |
| 1905x1077 | 1 | 5013 | 0.0199 |
| 1906x1073 | 1 | 5013 | 0.0199 |
| 1906x1081 | 1 | 5013 | 0.0199 |
| 1906x1082 | 1 | 5013 | 0.0199 |
| 1907x1063 | 1 | 5013 | 0.0199 |
| 1908x1077 | 1 | 5013 | 0.0199 |
| 1909x1072 | 1 | 5013 | 0.0199 |
| 1909x1077 | 1 | 5013 | 0.0199 |
| 1910x1075 | 1 | 5013 | 0.0199 |
| 1910x1079 | 1 | 5013 | 0.0199 |
| 1912x1076 | 1 | 5013 | 0.0199 |
| 1912x1079 | 1 | 5013 | 0.0199 |
| 1913x1081 | 1 | 5013 | 0.0199 |
| 1914x1073 | 1 | 5013 | 0.0199 |
| 1914x1078 | 1 | 5013 | 0.0199 |
| 1914x1081 | 1 | 5013 | 0.0199 |
| 1915x1062 | 1 | 5013 | 0.0199 |
| 1915x1074 | 1 | 5013 | 0.0199 |
| 1915x1079 | 1 | 5013 | 0.0199 |
| 1915x1080 | 1 | 5013 | 0.0199 |
| 1915x1083 | 1 | 5013 | 0.0199 |
| 1916x1067 | 1 | 5013 | 0.0199 |
| 1916x1076 | 1 | 5013 | 0.0199 |
| 1916x1080 | 1 | 5013 | 0.0199 |
| 1916x1082 | 1 | 5013 | 0.0199 |
| 1917x1078 | 1 | 5013 | 0.0199 |
| 1917x1080 | 1 | 5013 | 0.0199 |
| 1917x1081 | 1 | 5013 | 0.0199 |
| 1918x1075 | 1 | 5013 | 0.0199 |
| 1919x1073 | 1 | 5013 | 0.0199 |
| 1919x1080 | 1 | 5013 | 0.0199 |
| 2553x1431 | 1 | 5013 | 0.0199 |
| 720x377 | 1 | 5013 | 0.0199 |
| 720x406 | 1 | 5013 | 0.0199 |
| 720x407 | 1 | 5013 | 0.0199 |
| 932x540 | 1 | 5013 | 0.0199 |

| Variable | N | Min | Q1 | Median | Mean | Q3 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| width | 5013 | 704 | 1920.0000 | 2560 | 2221.5121 | 2560.0000 | 2688 |
| height | 5013 | 377 | 1080.0000 | 1440 | 1250.6946 | 1440.0000 | 1752 |
| aspect_ratio_numeric | 5013 | 1.2222 | 1.7778 | 1.7778 | 1.7760 | 1.7778 | 1.9098 |

| Aspect group | Count | N images | % |
| --- | --- | --- | --- |
| 16:9 | 4866 | 5013 | 97.0676 |
| other | 141 | 5013 | 2.8127 |
| 4:3 | 6 | 5013 | 0.1197 |

Exact reduced fractions: 16:9: 4866; 30:17: 38; 168:95: 26; 81:50: 9; 11:9: 6; 4:3: 6; 47:27: 4; 469:270: 3; 71:40: 3; 8:5: 3; 180:101: 2; 1252:703: 1; 1277:719: 1; 1544:867: 1; 1549:871: 1; 1551:874: 1; 1553:873: 1; 1555:874: 1; 1906:1073: 1; 1906:1081: 1; 1907:1063: 1; 1909:1072: 1; 1909:1077: 1; 1910:1079: 1; 1912:1079: 1; 1913:1081: 1; 1914:1081: 1; 1915:1062: 1; 1915:1074: 1; 1915:1079: 1; 1915:1083: 1; 1916:1067: 1; 1917:1078: 1; 1917:1081: 1; 1918:1075: 1; 1919:1073: 1; 1919:1080: 1; 221:125: 1; 233:135: 1; 34:19: 1; 360:203: 1; 382:215: 1; 383:216: 1; 422:235: 1; 478:269: 1; 479:269: 1; 479:270: 1; 635:359: 1; 636:359: 1; 637:360: 1; 66:37: 1; 720:377: 1; 720:407: 1; 851:477: 1; 87:49: 1; 949:538: 1; 953:541: 1; 958:541: 1. Width/height frequency histograms và numeric aspect summary có trong JSON; không biến aspect/resize thành quy định preprocessing W2.

## 9. Annotation density

| Group | Category | N | Shapes | Min | Q1 | Median | Mean | Q3 | Max | Zero-shape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| overall | all | 5013 | 37434 | 1 | 3.0000 | 6 | 7.4674 | 10.0000 | 49 | 0 |
| data_type | Anomaly_data | 1000 | 10960 | 1 | 6.0000 | 9.0000 | 10.9600 | 15.0000 | 49 | 0 |
| data_type | Normal_data | 4013 | 26474 | 1 | 3.0000 | 6 | 6.5971 | 9.0000 | 49 | 0 |
| safety_level | Level01 | 659 | 7453 | 1 | 6.0000 | 10 | 11.3096 | 16.0000 | 49 | 0 |
| safety_level | Level02 | 326 | 3419 | 1 | 5.0000 | 8.0000 | 10.4877 | 14.0000 | 43 | 0 |
| safety_level | Level03 | 15 | 88 | 2 | 3.0000 | 6 | 5.8667 | 8.0000 | 12 | 0 |
| safety_level | Level04 | 4013 | 26474 | 1 | 3.0000 | 6 | 6.5971 | 9.0000 | 49 | 0 |
| folder_domain | coal_conveyor | 1121 | 9091 | 1 | 5.0000 | 7 | 8.1097 | 10.0000 | 47 | 0 |
| folder_domain | metallurgy | 720 | 6832 | 1 | 7.0000 | 8.5000 | 9.4889 | 12.0000 | 49 | 0 |
| folder_domain | oil_chemical | 1023 | 8351 | 1 | 3.0000 | 7 | 8.1632 | 11.0000 | 49 | 0 |
| folder_domain | power | 869 | 4727 | 1 | 2.0000 | 4 | 5.4396 | 7.0000 | 38 | 0 |
| folder_domain | tunnel | 1280 | 8433 | 1 | 2.0000 | 4.0000 | 6.5883 | 10.0000 | 25 | 0 |
| split | test | 1250 | 8737 | 1 | 3.0000 | 6.0000 | 6.9896 | 9.0000 | 49 | 0 |
| split | train | 3763 | 28697 | 1 | 3.0000 | 7 | 7.6261 | 10.0000 | 47 | 0 |

Normal mean=6.5971, median=6; Anomaly mean=10.9600, median=9.0. Chênh mean Anomaly−Normal=4.3629 shapes/sample. Đây là khác biệt mô tả, không kết luận statistical significance hoặc mức độ đầy đủ/chính xác của annotation. Density không đo số hazard, diện tích evidence, độ khó ảnh hoặc independent observations.

## 10. Object-label long tail

Đếm lại **37,434 shape instances**, **231 unique raw labels**, label lists có mặt ở 5013/5013 samples. Không normalize nhãn; `出口` được giữ nguyên.

| Threshold (overlapping) | Labels | N unique labels | % labels |
| --- | --- | --- | --- |
| singleton | 10 | 231 | 4.3290 |
| le5 | 65 | 231 | 28.1385 |
| le10 | 93 | 231 | 40.2597 |
| ge100 | 59 | 231 | 25.5411 |

Top 20 labels chiếm **25837/37434 instances (69.02%)**. Kết hợp tỷ trọng head này và các label ít instances cho thấy long tail trong raw vocabulary; không fit power law hay đặt threshold chính thức cho “strong long tail”.

| Raw label | Instances | N shapes | % shapes |
| --- | --- | --- | --- |
| Pipeline | 4837 | 37434 | 12.9214 |
| Traffic Cone | 3345 | 37434 | 8.9357 |
| Stent | 2656 | 37434 | 7.0952 |
| Idler Roller | 2096 | 37434 | 5.5992 |
| Bolt | 1816 | 37434 | 4.8512 |
| Person | 1244 | 37434 | 3.3232 |
| Belt | 1092 | 37434 | 2.9171 |
| Window | 1015 | 37434 | 2.7114 |
| Gooseneck Tube | 981 | 37434 | 2.6206 |
| Protective Net | 922 | 37434 | 2.4630 |
| Flange | 752 | 37434 | 2.0089 |
| Valve Switch | 721 | 37434 | 1.9261 |
| Valve | 672 | 37434 | 1.7952 |
| Distribution Box | 635 | 37434 | 1.6963 |
| Railing | 574 | 37434 | 1.5334 |
| Lamp | 545 | 37434 | 1.4559 |
| Fire Alarm System | 519 | 37434 | 1.3864 |
| Guardrail | 509 | 37434 | 1.3597 |
| Indicator Light | 461 | 37434 | 1.2315 |
| Bellows | 445 | 37434 | 1.1888 |

Singleton labels: `Ammonia Torch Combustion Device`, `Cabinet`, `Dry Absorption Tower`, `Lane Indicator Control Box`, `Rope`, `Seal Pot`, `Strong Magnetic Equipment`, `Switch Five Prevention Lock`, `Tail Drum`, `出口`.

Full frequencies và danh sách <=5/<=10/>=100 nằm trong `labels` của JSON.

## 11. Split label coverage

| Coverage | Labels | N unique labels |
| --- | --- | --- |
| train_only | 65 | 231 |
| test_only | 24 | 231 |
| both | 142 | 231 |
| very_rare_in_test_1_to_5 | 61 | 231 |
| rare_in_test_1_to_10 | 91 | 231 |

train_only: `Ammonia Sphere`, `Ash Discharge Pipe`, `Bus Tie Switch`, `Cabinet`, `Camera`, `Cardboard Box`, `Chair`, `Cigarette Pack`, `Circuit Breaker`, `Communication Box`, `Condenser`, `Current Indication`, `Cutting Machine`, `Electronic Control Box`, `Fabric`, `Field Power Automatic Switching Device`, `Flow Control Valve`, `Garbage`, `Gas Canister`, `Gearbox`, `Hemp Rope`, `High-Pressure Nitrogen Main Valve`, `High-Voltage Metering Cabinet`, `Hook`, `Inspection Robot`, `Iron Barrel`, `Knob`, `Level Transmitter`, `Lighter`, `Lighting Standby Box`, `Liquefied Petroleum Gas`, `Liquefied Petroleum Gas Cylinder`, `Main Transformer Secondary Switch`, `Main Transformer Secondary Switch Control Cabinet`, `Molecular Sieve Adsorber`, `No Trespassing in Magnetic Separator Area Sign`, `Non-Motorized Vehicle`, `Outdoor Fire Hydrant`, `Power Meter`, `Power Supply Box`, `Primary Control Cabinet of the Main Transformer`, `Robot Room`, `Rope`, `Schoolbag`, `Screwdriver`, `Seal Pot`, `Signage`, `Slurry Furnace Head Valve`, `Spacer-Type Bus Bar`, `Speed Limit Sign`, `Stick`, `Storage Box`, `Strong Magnetic Equipment`, `Tail Drum`, `Telephone`, `Tietong`, `Toxic Gas Alarm`, `Transformer Furnace Supply Gas Pipe`, `Transformer Over-Temperature Protection Link Plate`, `Vent`, `Voltage Indication`, `Water Bottle`, `Water Cooler`, `White Paper`, `出口`.

test_only: `Ammonia Torch Combustion Device`, `Ammonia Torch Flame Arrester`, `Controller Display Screen`, `Dry Absorption Tower`, `Electronic Control Cabinet`, `Iron Basin`, `Iron Wire`, `Isolator Switch`, `Ladder`, `Lane Indicator Control Box`, `Lighting Distribution Box`, `Low-Voltage Distribution Box`, `Paper`, `Photovoltaic Panel`, `Plastic Stool`, `Power Box`, `Preheater`, `Sandbox`, `Separator`, `Static Electricity Indicator Light`, `Sulfur Protector`, `Switch Five Prevention Lock`, `Thus, By Identification`, `Traffic Light`.

very_rare_in_test_1_to_5: `AP3`, `Ammonia Torch Combustion Device`, `Ammonia Torch Flame Arrester`, `Belt Conveyor`, `Broom`, `Capacitor Control Cabinet`, `Central Oxygen Regulating Valve`, `Computer`, `Control Cabinet`, `Controller Display Screen`, `Counter`, `Dry Absorption Tower`, `Electric Scooter`, `Electric Vehicle`, `Electrical Control Box`, `Fault Display`, `Filter`, `Flusher`, `Foam`, `Gloves`, `Iron Basin`, `Iron Wire`, `Isolator Switch`, `Ladder`, `Lane Indicator Control Box`, `Level`, `Lighting Distribution Box`, `Mineral Water`, `Monitoring`, `Multifunction Meter`, `No Trespassing Over Belt Sign`, `Outdoor Unit of the Air Conditioner`, `Oxygen Air Valve`, `Petrochemical Storage Tanks`, `Photovoltaic Panel`, `Plank`, `Plastic Bottle`, `Plastic Bucket`, `Plastic Stool`, `Pliers`, `Power Box`, `Preheater`, `Safety Warning Signs`, `Sandbox`, `Shovel`, `Static Electricity Indicator Light`, `Street Lamp`, `Sulfur Protector`, `Switch Five Prevention Lock`, `Switchgear`, `Three-Phase Voltage Detector`, `Thus, By Identification`, `Trash Can`, `Tricycle`, `Trolley`, `Tunnel Emergency Alarm Button`, `Water`, `Water Droplet`, `Wire`, `Wood`, `Work Boots`.

`labels.split_coverage` lưu từng raw label với appears_train/appears_test, train_count, test_count và domains. Train-only/test-only/both là các tập loại trừ nhau trên official splits; very-rare-test có thể overlap test-only hoặc both. Độ phủ không đồng nhất có thể tạo open-vocabulary challenge, nhưng W1 chỉ report dữ liệu; đây chưa phải official open-vocabulary benchmark. Shape count không đồng nghĩa số ảnh độc lập có label.

## 12. Domain-label coverage

| Folder domain | Unique labels | Shape instances |
| --- | --- | --- |
| coal_conveyor | 60 | 9091 |
| metallurgy | 37 | 6832 |
| oil_chemical | 112 | 8351 |
| power | 102 | 4727 |
| tunnel | 79 | 8433 |

Labels chỉ thuộc một domain: **156/231**; thuộc nhiều domain: **75/231**. Mỗi domain có vocabulary và tỷ trọng objects riêng, là yếu tố gây nhiễu cần xét khi diễn giải cross-domain results.

### Top 20 — coal_conveyor

| Raw label | Instances | Domain shape N | % |
| --- | --- | --- | --- |
| Idler Roller | 2072 | 9091 | 22.7918 |
| Stent | 1080 | 9091 | 11.8799 |
| Belt | 1077 | 9091 | 11.8469 |
| Protective Net | 881 | 9091 | 9.6909 |
| Window | 829 | 9091 | 9.1189 |
| Pipeline | 535 | 9091 | 5.8849 |
| Lamp | 530 | 9091 | 5.8299 |
| Railing | 476 | 9091 | 5.2359 |
| Person | 311 | 9091 | 3.4210 |
| Radiator | 260 | 9091 | 2.8600 |
| Guardrail | 146 | 9091 | 1.6060 |
| Mobile Phone | 103 | 9091 | 1.1330 |
| Electrical Box | 87 | 9091 | 0.9570 |
| Liquid | 84 | 9091 | 0.9240 |
| Stairs | 83 | 9091 | 0.9130 |
| Plastic Bag | 63 | 9091 | 0.6930 |
| Safety Helmet | 58 | 9091 | 0.6380 |
| Cigarette | 55 | 9091 | 0.6050 |
| Open Flame | 50 | 9091 | 0.5500 |
| Fire Cabinet | 42 | 9091 | 0.4620 |

### Top 20 — metallurgy

| Raw label | Instances | Domain shape N | % |
| --- | --- | --- | --- |
| Pipeline | 2227 | 6832 | 32.5966 |
| Gooseneck Tube | 981 | 6832 | 14.3589 |
| Valve Switch | 686 | 6832 | 10.0410 |
| Flange | 447 | 6832 | 6.5427 |
| Bellows | 441 | 6832 | 6.4549 |
| Slag Pot | 386 | 6832 | 5.6499 |
| Sight Hole Cover | 347 | 6832 | 5.0790 |
| Hot Air Surrounding Pipe | 287 | 6832 | 4.2008 |
| Exhaust Hood | 163 | 6832 | 2.3858 |
| Smoke | 135 | 6832 | 1.9760 |
| Direct-Blow Pipe | 112 | 6832 | 1.6393 |
| Plank Road | 110 | 6832 | 1.6101 |
| Ventilation Duct | 75 | 6832 | 1.0978 |
| Liquid | 68 | 6832 | 0.9953 |
| Sintering Furnace Body | 61 | 6832 | 0.8929 |
| Window | 59 | 6832 | 0.8636 |
| Sintering Furnace Frame | 51 | 6832 | 0.7465 |
| Railing | 40 | 6832 | 0.5855 |
| Motor | 33 | 6832 | 0.4830 |
| Bolt | 26 | 6832 | 0.3806 |

### Top 20 — oil_chemical

| Raw label | Instances | Domain shape N | % |
| --- | --- | --- | --- |
| Pipeline | 1884 | 8351 | 22.5602 |
| Bolt | 1769 | 8351 | 21.1831 |
| Stent | 675 | 8351 | 8.0829 |
| Valve | 644 | 8351 | 7.7117 |
| Person | 351 | 8351 | 4.2031 |
| Guardrail | 328 | 8351 | 3.9277 |
| Motor | 276 | 8351 | 3.3050 |
| Flange | 215 | 8351 | 2.5745 |
| Ball Valve | 196 | 8351 | 2.3470 |
| Stairs | 168 | 8351 | 2.0117 |
| Liquid | 157 | 8351 | 1.8800 |
| Pressure Gauge | 139 | 8351 | 1.6645 |
| Valve Gate | 105 | 8351 | 1.2573 |
| Smoke | 86 | 8351 | 1.0298 |
| Window | 74 | 8351 | 0.8861 |
| Equipment Container | 72 | 8351 | 0.8622 |
| Mobile Phone | 71 | 8351 | 0.8502 |
| Cigarette | 68 | 8351 | 0.8143 |
| Instrumentation | 67 | 8351 | 0.8023 |
| Shutoff Valve | 56 | 8351 | 0.6706 |

### Top 20 — power

| Raw label | Instances | Domain shape N | % |
| --- | --- | --- | --- |
| Indicator Light | 445 | 4727 | 9.4140 |
| Instrumentation | 331 | 4727 | 7.0023 |
| Drainage Line | 261 | 4727 | 5.5215 |
| Surge Arrester | 245 | 4727 | 5.1830 |
| High-Voltage Insulator | 198 | 4727 | 4.1887 |
| Knob Switch | 172 | 4727 | 3.6387 |
| Stent | 168 | 4727 | 3.5541 |
| Drainage Line Fixation Device | 146 | 4727 | 3.0886 |
| Isolating Switch | 146 | 4727 | 3.0886 |
| Nameplate | 146 | 4727 | 3.0886 |
| Person | 144 | 4727 | 3.0463 |
| Pressure Gauge | 139 | 4727 | 2.9406 |
| Isolator | 131 | 4727 | 2.7713 |
| Distribution Cabinet | 121 | 4727 | 2.5598 |
| Bus Bar | 109 | 4727 | 2.3059 |
| Pipeline | 104 | 4727 | 2.2001 |
| Switch | 102 | 4727 | 2.1578 |
| Button | 99 | 4727 | 2.0944 |
| Flange | 90 | 4727 | 1.9040 |
| Intelligent Operation Device for Switchgear | 87 | 4727 | 1.8405 |

### Top 20 — tunnel

| Raw label | Instances | Domain shape N | % |
| --- | --- | --- | --- |
| Traffic Cone | 3345 | 8433 | 39.6656 |
| Stent | 715 | 8433 | 8.4786 |
| Distribution Box | 565 | 8433 | 6.6999 |
| Fire Alarm System | 519 | 8433 | 6.1544 |
| Person | 425 | 8433 | 5.0397 |
| Car | 423 | 8433 | 5.0160 |
| Fire Extinguisher | 327 | 8433 | 3.8776 |
| Fire Hydrant Cabinet | 323 | 8433 | 3.8302 |
| Lane Indicator Lights | 281 | 8433 | 3.3321 |
| Base Station | 168 | 8433 | 1.9922 |
| Mobile Phone | 109 | 8433 | 1.2925 |
| Emergency Exit | 101 | 8433 | 1.1977 |
| Emergency Phone | 98 | 8433 | 1.1621 |
| Wind Turbine | 91 | 8433 | 1.0791 |
| Pipeline | 87 | 8433 | 1.0317 |
| Fire Hydrant | 68 | 8433 | 0.8064 |
| Robot AP | 63 | 8433 | 0.7471 |
| Plastic Bag | 55 | 8433 | 0.6522 |
| Trash Can | 47 | 8433 | 0.5573 |
| Open Flame | 40 | 8433 | 0.4743 |

Full single-domain/multiple-domain label lists và membership mỗi label nằm trong JSON; không merge tên hoặc tạo taxonomy.

## 13. Missing metadata

| Field | N | Null | Empty | Whitespace-only | Unknown/unparsed |
| --- | --- | --- | --- | --- | --- |
| folder_domain | 5013 | 0 | 0 | 0 | 0 |
| text_domain | 5013 | 0 | 0 | 0 | 0 |
| safety_level | 5013 | 0 | 0 | 0 | 0 |
| robot_platform | 5013 | 0 | 0 | 0 | 0 |
| image_width | 5013 | 0 | 0 | 0 | 0 |
| image_height | 5013 | 0 | 0 | 0 | 0 |
| object_labels | 5013 | 0 | 0 | 0 | 0 |
| text_description | 5013 | 0 | 0 | 0 | 0 |

Null gồm field thiếu/None; empty là chuỗi `""` hoặc list `[]`; whitespace-only tách riêng, không strip giá trị để phân tích. Unknown/unparsed gồm category ngoài schema hoặc sai kiểu/giá trị; text_domain=None đồng thời là null và unparsed theo parser hiện có, nên không cộng các cột như các nhóm rời nhau. Không đặt heuristic “unknown text” dựa trên nội dung mô tả. Empty object_labels không tự động invalid. Builder strict sẽ từ chối malformed schema trước khi công bố full audit; bảng này mô tả typed manifest fields trên scope audit thành công, không thay thế missing/corrupt-file validation Bước 3.

## 14. Domain mismatch

Mismatch **36/5013 comparable samples**, unresolved=0. Folder/text matrix toàn bộ ở §4.10; ma trận dưới đây chỉ đếm mismatch, row N là số mismatch của folder đó.

| folder_domain | Row N | coal_conveyor | metallurgy | oil_chemical | power | tunnel |
| --- | --- | --- | --- | --- | --- | --- |
| coal_conveyor | 0 | 0 (undefined) | 0 (undefined) | 0 (undefined) | 0 (undefined) | 0 (undefined) |
| metallurgy | 8 | 0 (0.00%) | 0 (0.00%) | 8 (100.00%) | 0 (0.00%) | 0 (0.00%) |
| oil_chemical | 0 | 0 (undefined) | 0 (undefined) | 0 (undefined) | 0 (undefined) | 0 (undefined) |
| power | 4 | 4 (100.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) |
| tunnel | 24 | 0 (0.00%) | 0 (0.00%) | 24 (100.00%) | 0 (0.00%) | 0 (0.00%) |

| split | Mismatch count | Mismatch N | % |
| --- | --- | --- | --- |
| test | 4 | 36 | 11.11 |
| train | 32 | 36 | 88.89 |

| safety_level | Mismatch count | Mismatch N | % |
| --- | --- | --- | --- |
| Level01 | 8 | 36 | 22.22 |
| Level02 | 0 | 36 | 0.00 |
| Level03 | 0 | 36 | 0.00 |
| Level04 | 28 | 36 | 77.78 |

| data_type | Mismatch count | Mismatch N | % |
| --- | --- | --- | --- |
| Anomaly_data | 8 | 36 | 22.22 |
| Normal_data | 28 | 36 | 77.78 |

| split | folder_domain | text_domain | safety_level | data_type | Mismatch count |
| --- | --- | --- | --- | --- | --- |
| test | tunnel | oil_chemical | Level04 | Normal_data | 4 |
| train | metallurgy | oil_chemical | Level01 | Anomaly_data | 8 |
| train | power | coal_conveyor | Level04 | Normal_data | 4 |
| train | tunnel | oil_chemical | Level04 | Normal_data | 20 |

Không chọn folder_domain hay text_domain làm ground truth. Mismatch cũng không tạo samples mới hoặc tự động loại mẫu.

## 15. Implications for SafeShift

- Safety imbalance và Level03 cực ít mẫu yêu cầu W2 cân nhắc reporting cho class hiếm; plain accuracy có nguy cơ che khuất hiệu năng class hiếm, metric chính thức sẽ chốt W2.
- Metallurgy test không có anomaly và train chỉ có 9, trong đó 8 mismatch domain. Cần nêu rõ giới hạn khi thiết kế câu hỏi cross-domain.
- Platform × domain/type ở §4.8–4.9 cho thấy sampling không tách độc lập robot với domain. Không diễn giải robot token như camera/source identity đã xác minh.
- Cụ thể, coal_conveyor có 1121/1121 SuspendedRail; tunnel có 1256/1280 SuspendedRail, trong khi metallurgy có 661/720 Wheeled và oil_chemical có 923/1023 Wheeled. Toàn bộ 15/15 Level03 thuộc SuspendedRail. Các ô này hạn chế khả năng tách tác động domain, platform và safety class chỉ từ marginal results.
- Object vocabulary theo domain và long tail theo split có thể trộn object familiarity với safety/domain generalization. Annotation density khác nhau cũng có thể ảnh hưởng độ khó grounding; đây là khả năng cần kiểm tra, chưa là kết luận nhân quả.
- Resolution/aspect mix cần được xét cùng preprocessing và kích thước hazard khi chốt protocol W2, không thay ảnh ở W1.
- TVD marginal không đo leakage. Theo [duplicate_leakage_audit.md](duplicate_leakage_audit.md) và [visual_provenance_review.md](visual_provenance_review.md): có **7 cross-split exact pairs**, **12 cross-split source-family pools**, systematic index partition trong anomaly families và selected visual evidence of shared sequences/viewpoints. Family là source/hazard pool, không mặc định một video. Không suy mọi anomaly là một chuỗi. Findings này được mang vào discussion; không chạy lại perceptual audit và không cộng pairs/pools thành samples mới.
- Protocol/metric/split/label changes chỉ được áp dụng sau thảo luận, chấp thuận và ghi `DECISIONS.md`. Audit này không đưa ra benchmark metric cuối cùng.

## 16. Limitations

Đây là census mô tả của bản local, không chứng nhận sampling population hay causal/generalization properties. Safety/domain/platform dựa trên naming convention đã audit; text_domain dựa trên 24 exact openings. Không tái kiểm chứng semantic labels, hazard evidence hoặc quyền chia sẻ. Raw label frequency không phải taxonomy chuẩn; một label có nhiều polygon/cùng chuỗi vẫn được đếm nhiều instances. Missing fields bằng 0 không khẳng định metadata đúng. Actual image headers được đọc, full decode đã thực hiện ở Bước 3. Fingerprint ghi bytes đã đọc nhưng không phải filesystem snapshot chống thay đổi đồng thời; cần giữ dataset yên trong run. Reproducibility áp dụng cho inputs/code/environment đã ghi; timestamp/runtime/Git provenance thay đổi giữa runs. Không đo statistical significance, confidence interval, pixel distribution divergence hoặc độc lập giữa samples.

## 17. Questions to carry into W2

1. Chọn cách báo cáo class hiếm và giới hạn suy luận cho Level03 15 samples như thế nào, với metric nào được Research Lead chấp thuận?
2. Anomaly-sensitive evaluation của metallurgy sẽ có phạm vi gì khi official test có 0 anomaly và 8/9 train anomaly mismatch domain?
3. Xử lý 36 folder/text conflicts và metadata platform gây nhiễu như thế nào mà vẫn truy vết được hai nguồn?
4. Protocol nào kiểm soát exact reuse/shared sequences/viewpoints và reporting theo groups mà không nhầm source pool với video ID?
5. Tách ảnh hưởng của object vocabulary/label rarity khỏi safety generalization và domain shift bằng thiết kế nào?
6. Resolution/aspect preprocessing và annotation-density differences cần được ghi/kiểm soát ra sao cho grounding?
7. Có đủ bằng chứng để chốt research feasibility không? Đây vẫn là task riêng; W1 chưa được đánh dấu complete.
