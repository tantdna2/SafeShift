# Duplicate & train/test leakage audit — W1, Bước 4

Audit trả lời riêng biệt về byte identity, decoded pixel identity, perceptual
similarity và dấu vết nguồn giữa các split của InspecSafe-V1. External image trong
triplet là primary evidence; JSON `imagePath` và embedded `imageData` là secondary
provenance evidence. Chỉ đọc dữ liệu; không đổi split, domain, safety labels,
polygons, research protocol hay benchmark metrics. Không chạy VLM.

## Thuật ngữ và đơn vị đếm

| Evidence type | Ý nghĩa |
| --- | --- |
| `CONFIRMED_EXACT_BYTE` | Cùng SHA-256 toàn bộ external image bytes. |
| `CONFIRMED_PIXEL_EXACT` | Bytes khác nhưng cùng SHA-256 dimensions + decoded RGB pixels. |
| `HIGH_SIMILARITY_CANDIDATE` | Cặp trong dHash candidate pool, chưa phải duplicate/leakage đã xác nhận. |
| `METADATA_SOURCE_CANDIDATE` | Trùng metadata đường dẫn/basename hoặc source-family heuristic; không xác nhận chung video/cảnh. |

Pixel-exact totals bao gồm byte-exact khi decoded RGB cũng giống nhau. Pair record
dùng evidence type mạnh nhất, cùng `byte_equal`/`pixel_equal` để phân biệt rõ hai
loại identity. Near pool cũng bao gồm exact pairs đạt threshold; không cộng ba
totals như các tập rời nhau. Sequential reference là tập calibration riêng, có
thể overlap near pool; similarity của reference không tự trở thành leakage.

Mỗi pair là unordered combination, canonical theo `(sample_id, image_relpath)`.
Thông thường `sample_id_a < sample_id_b`; relative path phá hòa khi stem bị lặp
giữa split, để vẫn audit được same-point cross-split. Không bỏ sample có stem lặp.
Group size n đóng góp `n*(n-1)/2` pairs; cross-split đóng góp `n_train*n_test`.
Group thống kê chỉ gồm size >=2; unique hashes vẫn tính cả singleton. Group-size
distribution, largest group và spanning splits/domains/point IDs đều được lưu.

`same_point` so point ID 6 chữ số; `same_point_folder` so relative folder đầy đủ.
Point overlap kiểm tra cả giao numeric ID train/test và tên folder đầy đủ không
chứa split prefix. Domain relation chỉ so `folder_domain` quan sát, không chọn
ground truth và không coi cùng domain là cùng nguồn.

## Phương pháp có thể tái lập

Implementation: `safeshift/data/duplicates.py`; CLI: `scripts/audit_duplicates.py`.
Tái sử dụng `iter_sample_candidates`, `sample_metadata`, `repository_path` của
manifest, không sao chép parser annotation/label. Duyệt toàn bộ union stems trong
Annotations, hash đủ jpg/json/txt để fingerprint. Thiếu triplet, layout không hợp
lệ, JSON không parse/object hoặc ảnh không decode được khiến audit incomplete.

1. **Exact bytes:** SHA-256 toàn bộ file external `.jpg`, không suy codec từ suffix.
2. **Pixel exact:** Pillow decode, giữ width/height gốc, `convert('RGB')`, không
   resize/normalize resolution. SHA-256 của `struct.pack('>QQ', width, height)`
   (hai unsigned 64-bit big-endian integers), tiếp theo raw RGB bytes row-major.
   Không EXIF transpose, ICC color transform hoặc alpha compositing. Identity này
   định nghĩa trên decoded RGB representation, không phải mọi metadata/channel.
3. **dHash 64-bit:** decode external image, `convert('L')`, resize `(9,8)` bằng
   `Image.Resampling.LANCZOS`. Duyệt row-major y=0..7, x=0..7; bit = 1 khi pixel
   trái **lớn hơn** pixel phải, bằng nhau tạo 0. First comparison là bit 63.
   Hamming = `(hash_a ^ hash_b).bit_count()`. Không Python built-in `hash()`.
4. **Sweep:** brute force mọi i<j; báo cumulative <=0, <=2, <=4, <=6, <=8 cho toàn
   bộ và cross-split. Sweep luôn tính đủ các ngưỡng này; `--max-hamming` chỉ điều
   khiển candidate pool cần MAE (mặc định 8, chấp nhận integer 0..64). <=8 là
   screening pool, không phải ngưỡng xác nhận duplicate; không dùng MAE để lọc pool.
5. **Second stage:** với mọi candidate, decode external images theo nhu cầu,
   `convert('L')`, resize `(256,256)` bằng LANCZOS, tính
   `sum(abs(a-b))/(256*256*255)`. Pillow `ImageChops.difference().histogram()` cho
   tổng sai khác nguyên chính xác trước phép chia. Range [0,1]; không registration,
   không giữ aspect ratio, không RGB MAE. Ghi dimensions gốc, dHash và mọi split/
   point/domain relation. Exact pairs và sequential reference cũng được tính MAE.
6. **Consecutive calibration:** chỉ Normal samples trong cùng actual point folder,
   chỉ 001–002, 002–003, 003–004 khi cả hai tồn tại. Không nối qua gap hoặc split.
   Ghi raw reference pairs, count/min/median/mean/max, histogram dHash và 20 bins
   MAE [0,.05), ... [.95,1]. So mô tả với different-point same-split/cross-split
   candidates; những nhóm sau đã bị chọn bởi dHash, không phải đối chứng ngẫu nhiên.

Pillow/codec version là một phần provenance; hash deterministic với cùng bytes,
implementation và môi trường decode/resampling. Không suy tính bất biến qua mọi
version codec. Không EXIF transpose trong bất kỳ representation nào: đây là lựa
chọn theo yêu cầu audit decoded pixels, chưa có bằng chứng cần sửa orientation.

## Metadata và embedded audit

Đọc raw `imagePath` từng JSON, không dùng làm đường dẫn mở ảnh. So exact full string
qua SHA-256 UTF-8 không strip/casefold/normalize separator; so basename riêng sau
`replace('\\', '/').split('/')[-1]`. Do đó full-string equality và basename equality
là hai loại bằng chứng khác nhau. Báo unique/duplicate/cross-split groups cho cả hai.

Source-family chỉ dùng case-sensitive fullmatch trên basename:

```regex
(?P<family>.+)_frame_(?P<counter>[0-9]+)\.(?:jpg|jpeg|png)
```

Bỏ duy nhất suffix `_frame_<digits>.<extension>`; giữ nguyên mọi chữ số trong
prefix. Unknown pattern trả null; không suy nguồn từ domain. Key xuất ra là SHA-256
UTF-8 của family. Pattern hẹp có thể bỏ sót các convention khác; cùng prefix có
thể bị tái sử dụng ở các nguồn độc lập. Đây không phải official video ID.

Không sao chép raw full `imagePath` vào report để tránh absolute upstream/machine
paths. Report local giữ digest full string, basename, hashed family và JSON path
tương đối cho từng sample; raw full metadata vẫn nằm nguyên trong JSON local và
có thể truy xuất qua `json_relpath`. Committed notes chỉ chứa aggregate counts.

Embedded audit xử lý một JSON/Base64 mỗi lần bằng `base64.b64decode(validate=True)`
và SHA-256 decoded bytes. Không bỏ whitespace, không hỗ trợ data URI, không cache
decoded embedded payloads. Missing/null/empty/invalid type/invalid Base64 có status
và counts riêng, không gom các null thành duplicate group. `checked` nghĩa là decode
strict thành công; chỉ các mẫu này tham gia embedded hash groups. Optional secondary
evidence không hợp lệ được ghi issue, không làm mất primary samples hoặc đổi exit
code. Không decode pixel/perceptual search embedded ở bước này.

## Commands, provenance và giới hạn vận hành

Từ repository root trong PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m unittest discover -v
python scripts/audit_duplicates.py --dataset-root data/raw/InspecSafe-V1 --output data/manifests/duplicate_leakage_audit.json --max-hamming 8
```

Dependencies dùng lại `requirements-validation.txt` (Pillow==12.3.0). Python ngoài
virtual environment trên máy này chưa có Pillow; không thay dependency để chạy.

Exit **0** khi hoàn tất, kể cả có cross-split exact/candidates; **1** khi lỗi
runtime/structural/output/dependency hoặc arguments không hợp lệ. Không xuất report
partial khi primary audit lỗi; report cũ nếu có là stale. Output JSON được kiểm
tra nằm ngoài dataset và `data/raw`, trong repository sau resolve, rồi ghi atomic.

Report có version/run ID/UTC, Git commit/status, Python/platform/Pillow/codec,
command, max_hamming, definitions, relative dataset root, input fingerprint,
summary, groups, pair evidence, metadata/embedded evidence và source SHA-256.
Run-specific timestamp/runtime/provenance có thể khác giữa các lần chạy; report
body và ordering deterministic với cùng input. Không dùng random; seed=null.

Input fingerprint dùng cùng serialization successful validation Bước 3: SHA-256
các ASCII JSON lines `[repo-relative path, full-file SHA-256]`, `ensure_ascii=True`,
default separators và newline mỗi record; train/test, Normal_data/Anomaly_data,
sorted point/stem, jpg/json/txt. Không bao phủ archive, Parameters hoặc modalities.
Đây không phải manifest Bước 2 fingerprint có thêm modality flag.

Không giữ decoded images toàn dataset trong RAM: chỉ metadata/hashes và pair
records; LRU tối đa 32 grayscale 256×256 images (2 MiB pixel buffers), ngoài ảnh
đang decode và ảnh tạm. JSON/Base64 parser vẫn giữ một sample lớn trong RAM. Candidate
metadata tăng theo số pair; không phải constant-memory search. Peak RAM chưa đo.
Runtime là audit wall time, không bao gồm JSON serialization/publication. Khi đọc
lại để MAE, external bytes được hash lại để phát hiện thay đổi giữa hai giai đoạn;
không phải filesystem snapshot chống mutation đồng thời trên toàn bộ dataset.

Artifact `data/manifests/duplicate_leakage_audit.json` được ignore và giữ local theo
deliverable riêng của task: nhiều sample IDs/pairs/upstream basename. Không commit
ảnh, decoded Base64, raw dataset hoặc full metadata. Không tạo resized image files.

## Giới hạn diễn giải và W2

dHash 64-bit mất màu/chi tiết, có collision và có thể bỏ sót crop, viewpoint, rotation,
exposure hoặc re-encoding. MAE sau resize mất resolution/aspect ratio, nhạy alignment,
không chứng minh cùng nguồn và có thể bỏ qua hazard nhỏ. Hai ảnh cùng industrial
background/pipeline/tunnel/machinery không tự động là duplicate. Hash equality là
bằng chứng computational identity dưới SHA-256 (không kiểm chứng collision toán học).

Không có candidate ở một ngưỡng không chứng minh không có shared scene/source.
Point-ID disjoint cũng không chứng minh scene/sequence disjoint. Metadata trùng
cần đối chiếu provenance thực, source-family prefix không xác minh source video.
Không thực hiện visual inspection hoặc đánh dấu visual audit hoàn tất ở bước này.

Research Lead cần review cross-split exact/pixel identity nếu có, different-point
cross-split candidates (ưu tiên dHash nhỏ và MAE thấp để kiểm tra), source metadata
overlap và embedded provenance. W2 phải quyết định handling policy nếu có cross-split
exact duplicates; mọi thay đổi dataset/split/metric cần phê duyệt và `DECISIONS.md`
trước áp dụng. W1 không đề xuất xóa mẫu hoặc tự thiết kế split mới.

## Kết quả full run — 2026-09-14

Nguồn số liệu: full local report `data/manifests/duplicate_leakage_audit.json`,
run `duplicates-20260914T123549630036Z`, UTC `2026-09-14T12:35:49.630036+00:00`.
Audit hoàn tất **exit 0**, **5.013 samples**, **3.763 train / 1.250 test**;
**12.562.578 unordered dHash comparisons**. Runtime **461,814388 giây**
(7 phút 41,814 giây; không gồm JSON publication), không đo peak RAM.

Môi trường: Python **3.11.9**, Pillow **12.3.0**, platform
`Windows-10-10.0.26200-SP0`, libjpeg **8.0**, zlib **1.3.1.zlib-ng**.
Git parent tại run: `6f71447351e5d3a856a60d7df675538a3838c6c0`, cùng implementation
chưa commit trên `feat/duplicate-leakage-audit`; Git status và source checksums
trong artifact ghi đúng trạng thái đó, không giả vờ run trên commit cuối.

Input fingerprint đo độc lập:
`1a52f9078d53bddcdcd8400486a6e22f7688c8c20dc85b481b128f94c723399c`.
Khớp fingerprint validation được cung cấp; không hard-code counts để đạt kết quả.
Artifact **16.747.562 bytes**, SHA-256:
`16039f2302027ffe53f3bcdbfc80c762c88e823fbf303d5672030587cd9602d6`.
Artifact không commit vì chứa full pair table, sample IDs và upstream basenames.

### Exact external image identity

| Thống kê | Exact byte | Pixel exact |
| --- | ---: | ---: |
| Unique hashes | 4.960 | 4.960 |
| Duplicate groups | 53 | 53 |
| Samples trong duplicate groups | 106 | 106 |
| Pairs | 53 | 53 |
| Within train pairs | 44 | 44 |
| Within test pairs | 2 | 2 |
| Cross-split pairs | **7** | **7** |
| Different-point cross-split pairs | **7** | **7** |
| Same-point pairs / different-point pairs | 0 / 53 | 0 / 53 |
| Cross-domain pairs | 1 | 1 |
| Groups spanning train/test | 7 | 7 |
| Groups spanning domains | 1 | 1 |
| Groups spanning point IDs | 53 | 53 |
| Largest group size | 2 | 2 |
| Byte-different pixel-exact pairs | — | **0** |

Group-size distribution cho cả hai: **size 2 → 53 groups**. Tất cả 53 byte-exact
pairs cũng pixel-exact; không phát hiện additional pixel identity bị che bởi bytes
khác. Toàn bộ exact groups thuộc different point IDs, không thể quy chúng thành
same-point consecutive reference. Cả 7 cross-split exact pairs là Anomaly–Anomaly.
Một trong 7 cặp này còn khác folder domain. Toàn bộ 53 exact pairs gồm
38 Normal–Normal và 15 Anomaly–Anomaly; không suy lại ground truth từ chúng.

### Near pool và split relations

| Cumulative dHash threshold | Toàn bộ pairs | Cross-split pairs |
| --- | ---: | ---: |
| <=0 | 804 | 33 |
| <=2 | 1.833 | 213 |
| <=4 | 2.520 | 352 |
| <=6 | 3.493 | 540 |
| <=8 | **5.041** | **833** |

Pool <=8 gồm **53 exact + 4.988 nonexact candidates**. Cross-split pool gồm
**7 exact + 826 nonexact candidates**, tất cả 833 khác point ID; same-point
cross-split = **0**. Cụ thể `cross_split_exact_byte_pairs=7`,
`cross_split_pixel_exact_pairs=7`, `cross_split_near_candidate_pairs=833`
(near pool inclusive of exact; nonexact-only=826).

Within-train pool = 3.636; within-test = 572; cross-domain = 308. Same-point pool
= **1.049**, gồm **1.026 adjacent reference pairs + 23 non-adjacent same-point pairs**.
Different-point pool = **3.992**, gồm **3.159 same-split + 833 cross-split**.
Không gọi 4.988/826 nonexact candidates là confirmed leakage. Ngay ở dHash=0,
cross-split vẫn có **26 nonexact candidates** ngoài 7 exact pairs.

### Same-point calibration và so sánh mô tả

| Nhóm | Số pairs | dHash min / median / mean / max | MAE min / median / mean / max |
| --- | ---: | --- | --- |
| Adjacent Normal reference (không threshold filter) | **1.779** | **0 / 4 / 11,849354 / 46** | **0,000130029 / 0,034595385 / 0,072820378 / 0,374906173** |
| Different-point same-split pool <=8 | 3.159 | 0 / 6 / 4,879076 / 8 | 0 / 0,057614016 / 0,058642667 / 0,317591110 |
| Different-point cross-split pool <=8 | 833 | 0 / 5 / 4,857143 / 8 | 0 / 0,044973396 / 0,057816757 / 0,302822876 |

Histograms đầy đủ và per-pair values nằm local. Có **753 adjacent reference pairs
vượt dHash 8**: sequence adjacency không đồng nghĩa perceptual similarity nhỏ.
Reference median MAE thấp hơn hai candidate groups, nhưng range overlap rộng;
candidate groups đã qua dHash selection và bao gồm exact pairs. Không dùng sự
khác nhau này để suy statistical significance, source identity hay ngưỡng leakage.
MAE đã tính cho **5.794 unique pairs** = union candidate/exact/reference.

### Point / imagePath / source-family evidence

| Thống kê | Kết quả |
| --- | ---: |
| Train/test point-ID overlap count / IDs | **0 / []** |
| Full point folder identity overlap count / identities | **0 / []** |
| imagePath strings checked | 5.013 |
| Unique exact imagePath strings / basenames | 5.013 / 5.013 |
| Exact imagePath duplicate groups / cross-split groups | **0 / 0** |
| Basename duplicate groups / cross-split groups | **0 / 0** |
| Source-family pattern matched / unknown samples | **5.013 / 0** |
| Unique source-family keys | 2.291 |
| Source-family groups (size >=2) / member samples | **1.340 / 4.062** |
| Cross-split source-family groups / member samples | **12 / 1.000** |
| Source-family groups spanning domains / point IDs | 11 / 12 |
| Largest source-family group size | 108 |
| Source-family unordered pairs / cross-split pairs | 50.094 / 18.161 |

Source-family group-size distribution: 2→1.073; 3→104; 4→151; 10→1; 14→1;
72→1; 86→1; 96→1; 100→2; 103→2; 104→2; 108→1.
Tất cả **1.000 members trong 12 cross-split source-family groups là Anomaly_data**.
Đây là dấu vết tên nguồn cần review, chưa xác nhận cùng source video/sequence.

Trong 833 cross-split near-pool pairs, **141** có cùng source-family candidate key.
Trong 7 cross-split byte-exact pairs, **3** có cùng family key và **4** khác family
key. Metadata khác vẫn có thể đi cùng identical external image; source-family
heuristic không đủ để kết luận absence of leakage. Trùng full imagePath bằng 0
cũng không phủ định 7 cross-split exact pairs đã xác nhận độc lập.

### Embedded imageData (secondary)

| Thống kê | Kết quả |
| --- | ---: |
| Checked bằng strict Base64 decode | **5.013** |
| Unique embedded hashes | **4.960** |
| Duplicate embedded groups / member samples | **53 / 106** |
| Embedded exact pairs | 53 |
| Cross-split embedded groups / exact pairs | **7 / 7** |
| Largest group / group-size distribution | 2 / size 2→53 |
| Missing/null / empty / invalid type / invalid Base64 | 0 / 0 / 0 / 0 |
| Embedded bytes khác external cùng sample | **94** |

Count 94 được tính lại ở run này. Không thay canonical image hoặc suy từ byte
mismatch rằng embedded pixels khác. Không thực hiện embedded pixel/perceptual audit.
Đối chiếu member identities cho thấy 53 embedded duplicate groups có cùng member
pairs với 53 external exact groups; đây vẫn là nguồn bằng chứng thứ cấp riêng.

### Kiểm chứng và kết luận gửi Research Lead

**107/107 tests pass, 0 failed** bằng command trên: 41 duplicate tests synthetic,
29 manifest tests và 37 validation tests. Coverage gồm combinations sizes 2/3/4,
known dHash bits/process determinism, pixel identity với bytes khác, threshold
filter, ordering/không double-count, adjacency/gaps, point overlap, Windows/Unix
metadata, conservative family parsing, embedded invalid/missing data, MAE endpoints,
input immutability, relative paths, fingerprint equivalence và CLI/output failures.

Sau full run, kiểm tra độc lập từ artifact đã pass: recompute group combinations,
cross-split counts; scan canonical pair uniqueness/order/relations/MAE range;
recompute mọi **12.562.578** dHash comparisons bằng `itertools.combinations` để
đối chiếu sweep/pool; đối chiếu source file checksums và scan absolute path values.
Đặc biệt đọc lại **toàn bộ 53 exact pairs**, so full file bytes trực tiếp và decoded
RGB bytes/dimensions trực tiếp; xác nhận cả 7 cross-split pairs. Đây là verification
bằng bytes/pixels, không phải visual inspection. Tests raw immutability pass; full
input fingerprint khớp validation trước audit. Không có required check bị bỏ qua.

1. **Có confirmed cross-split external byte identity:** 7 pairs, 7 groups; tất cả
   khác point ID, Anomaly–Anomaly. Đây là nguy cơ evaluation leakage có bằng chứng
   exact image reuse, không thể giải thích bằng same-point consecutive frames.
2. **Có confirmed cross-split decoded pixel identity:** cùng 7 pairs; không có
   byte-different pixel-exact pairs bổ sung trên bản dataset này.
3. **Có cross-split near candidates:** 833 inclusive pool, trong đó 826 nonexact.
   Cần Research Lead review hình ảnh/provenance; chưa gọi những nonexact pairs là
   confirmed leakage và chưa xác nhận chung cảnh chỉ từ dHash/MAE.
4. **Có metadata-based source candidates:** 12 cross-split source-family groups,
   bao phủ 1.000 anomaly samples; full-string/basename equality đều không có.
   Đây là clue nguồn thứ cấp, không phải official video grouping.
5. **Trước W2:** Research Lead cần quyết định handling policy cho 7 cross-split
   exact pairs, review 826 nonexact pairs (ưu tiên dHash nhỏ/MAE thấp), 12 family
   groups và embedded provenance. Không áp dụng policy mới ở W1; mọi thay đổi cần
   phê duyệt/ghi `DECISIONS.md`. Chưa hoàn tất distribution audit tổng thể,
   feasibility, visual inspection hoặc final W1 report.
