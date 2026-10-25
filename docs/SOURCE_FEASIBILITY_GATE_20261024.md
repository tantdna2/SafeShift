# SafeShift — Hồ sơ quyết định khả thi Seminar

Khởi tạo 24/10/2026, cập nhật bằng chứng S2 gốc **25/10/2026**, Asia/Bangkok.
**BASE_SHA / main của PR:**
`2810bee6f404a1c41cca4a2bbe45baf5ac48358a`.
Tiếp tục branch PR #131 từ `c492a0b546248f1e9496dfa0248450548ace5ba1`.
Cập nhật 25/10 tiếp tục từ `bb31ef749fc0e31627f550a16188f82ac59fe6e2`.
Các nguồn lịch sử bên dưới đều ở snapshot bất biến
`31a04e6f7175cca818c63b4de0153246b3f3ecdb`.

## 1. Đề xuất quyết định

**Ưu tiên trình duyệt C làm trọng tâm Seminar: kiểm toán đơn vị đánh giá và
độ nhạy của kết luận VLM trước ảnh lặp/cách nhóm. Giữ A cho Khóa luận với điều
kiện có nguồn chứa cả hai trạng thái và dữ liệu độc lập.** Đây là đề xuất, chưa
thay D9R22, DEC-PA3-011 hoặc cấp quyền thực nghiệm.

Hồ sơ đã thực hiện phân tích CPU từ saved scores và metadata đủ điều kiện,
thay cho nhận định trước đó rằng khả dụng artifact local chưa rõ:

- Đối soát đủ **3.763/3.763 ID–nhãn–miền** giữa Qwen2.5, InternVL3 và TRAIN
  metadata đúng checksum; tính AUROC theo ảnh và 9 biến thể độ nhạy.
- Nối riêng saved reports Qwen3 S0/S1/S3 qua result → archive → manifest → CSV
  và eligible IDs. So ba model trên **2.822 ID chung**; phân tích **Recovery224
  riêng**, không ghép vào V4.
- **25/10: đã khép S2 V4 gốc** từ ZIP Owner cung cấp: đúng hash/size, CRC,
  sidecars, config và 941 ID/trạng thái. Bốn shard có 3.763 planned, **3.539
  SUCCESS (94,0473%)**, 1 TECHNICAL_ERROR/223 NOT_ATTEMPTED. AUROC Q3 gốc tính
  lại **0,9527927338600111**; thêm 10 biến thể trên cùng 3.539 ID của ba model.
  Đây là **saved-score verification PASS**, không raw audit hoặc V4 execution
  hoàn tất 100%. Recovery224 vẫn riêng.
- Exact TRAIN có 44 cặp; score/nhãn đồng nhất trong mỗi cặp ở các model/cohort
  đã kiểm. Mỗi nhóm tổng trọng số 1 làm AUROC Qwen2.5 đổi **0,826656 → 0,825397**,
  InternVL3 **0,886182 → 0,885748**. Ranking gộp giữ nguyên trong mọi kịch bản
  đã tính của từng cohort.
- Mâu thuẫn `002875/002660` rộng hơn một ID: **0/7 cặp** trong bảng exact của
  visual note khớp đầy đủ pair table đúng hash. Đã tách catalog này khỏi mapping
  dùng để tính; không sửa lịch sử hoặc đổi nhãn.

**C hồi cứu: khả thi, đã có kết quả thăm dò PROPOSED. C với suy luận thống kê
theo nguồn độc lập: NO-GO hiện tại. A matched hazard–normal/transfer độc lập:
NO-GO hiện tại.** Chưa có map nguồn thật đủ tin cậy, CI phù hợp hoặc bằng chứng
cùng nguồn nhưng khác trạng thái nguy cơ. Ranking ổn định trong một số giả định
chưa chứng minh ưu thế thống kê hoặc hazard validity.

Số chính xác, checksum, coverage và kết quả gộp **40 kịch bản** (giữ 30 ngày
24/10, thêm 10 V4-success gốc ngày 25/10) nằm trong
[receipt tổng hợp](SOURCE_FEASIBILITY_RECEIPT_20261024.json).
Receipt Git không chứa per-image scores, raw output, ảnh hoặc annotation.

## 2. Nguồn, mức bằng chứng và kiểm kê artifact

**VERIFIED_ARTIFACT:** kiểm lại bytes/checksum và tính từ artifact được phép,
không đồng nghĩa raw-logit audit. **INHERITED_AUDIT:** kế thừa audit lịch sử,
chưa kiểm lại ảnh/annotation. **REPORTED:** có báo cáo nhưng chưa khép xác minh
tương ứng. **PROPOSED_EXPLORATORY:** thăm dò chưa thành metric/protocol benchmark
được duyệt. **BLOCKED/UNKNOWN:** thiếu đầu vào/quyền, không thay bằng số 0.

Đã đọc tài liệu main được yêu cầu, chọn lọc audit [D][D], [V][V], [F][F], [I][I],
báo cáo/receipt [M3][M3], [R3][R3], runbook [P90][P90] và verdict 90 ảnh liên
quan. Chỉ xem nguồn phân tích cũ và receipt/hợp đồng cần thiết, không đọc lại
toàn bộ 693 file hoặc nghiên cứu lại 14 bài báo.

Hai đánh giá 23/10 được tận dụng: báo cáo khoa học trong Git [M3][M3] và báo
cáo độc lập **chỉ có local** `notes/independent_research_review_20261023.md`
ở workspace gốc, SHA-256
`b2d191e481378792a4a83fa1009611eab068c1273e665208f0d7bf35ab28d6e1`.
File local không có tại snapshot; không tạo Git link giả. Bản tổng hợp do Lead
cung cấp [S3][S3] cũng được đối chiếu qua receipt. Đánh giá độc lập ưu tiên A
khi có matched/independent data, C khi thiếu; gate 24/10 trước đó trong PR này
đã chỉ ra A chưa đạt điều kiện dữ liệu. Phân tích mới kiểm phần có thể tính,
giữ phản biện về novelty/validity. Không tìm thấy kết luận phản biện 24/10
riêng khác trong các notes/worktree quyết định đã kiểm; không khẳng định file
đó vắng ở mọi nơi hoặc tự coi file local đã có trên Git.

| Artifact / dữ liệu | Hiện trạng đã kiểm tra | Đủ dùng cho việc gì / giới hạn |
| --- | --- | --- |
| Raw InspecSafe-V1 | Thư mục `data/raw/InspecSafe-V1/` tồn tại ở workspace gốc; không duyệt nội dung | Không mở ảnh, TEST hoặc annotation khóa; counts dataset kế thừa W1. Không tạo dataset parser. |
| `duplicate_metadata_audit.json` | **16.747.562 bytes**, hash `16039f2302027ffe53f3bcdbfc80c762c88e823fbf303d5672030587cd9602d6`, khớp D/R3; complete=true, exit=0 | Trích TRAIN metadata/hashes/quan hệ có sẵn, không mở raw paths. Fingerprint dataset ghi trong artifact: `1a52f9078d53bddcdcd8400486a6e22f7688c8c20dc85b481b128f94c723399c`; chưa rehash dataset. |
| Qwen2.5 `qwen25_samples.csv` | **645.103 bytes**, hash `59023ddd838a6e2d2b6bda66c58a2a49e77c5d9557ac7f89308d12db65330911`, khớp R3; 3.763 SUCCESS | Saved-score recomputation và exact join. Raw PASS Linux là **kế thừa**, không raw audit mới; giới hạn Shard 1 outer receipt/Windows 1-ULP giữ nguyên [Q25][Q25]. |
| `InterVL3_Output.zip` | **76.261.594 bytes**, hash `5400bfefef38372cd42d17223f59ef7a4ea97fd7415c9d6c234ed9b309161e90`; đủ 4 tar duy nhất và 4 CSV đúng member hash R3 | 3.763 SUCCESS; chỉ đọc `evidence/report/samples.csv` mỗi tar. Không replay raw hoặc xác minh lại runtime/token alignment. |
| Qwen3 S0/S1/S3 | 3 result đúng hash R3; archive hash/size, manifest hash, CSV hash/size, eligible IDs và AUROC từng shard khớp | **2.822 saved rows được kiểm chứng mới**, cohort đúng ba shard khả dụng; không phải toàn 3.539 V4-success gốc. Hash đầy đủ ở receipt mới. |
| Qwen3 Recovery224 | Result đúng R3; archive hash `da56ff98a6504faff7f3bff73b9797a25c8b36cadd87d8a3be056379f785c673`, manifest/CSV/224 IDs khớp | Cohort bổ sung riêng, 49 A/175 N; không pooling V4, không chứng minh nguyên nhân OOM hoặc hết selection bias. |
| Qwen3 S2 gốc | **Đã tìm được và xác minh 25/10** từ `Qwen3-Shard2-V4.zip`; TAR 12.031.765 bytes, hash `2dc356fcba9fe2ce5dfc4e3dc9a45286fe5382f574c02d38d7517580e38cd920` | 941 planned: 717 SUCCESS/1 TECHNICAL_ERROR/223 NOT_ATTEMPTED; AUROC saved score 0,9526425641148669. Blocker thiếu S2 gốc đã khép ở cấp archive/saved-score; không raw PASS. |
| S2 cùng basename đang có | Hash lại **12.038.105 bytes**, `508a2e122ee999da728e8d09c66f5157331e6fe1a40adaa82e2869a30c6e0147`, khác hash gốc | **SECOND_DUPLICATE_S2_DIAGNOSTIC**, consistency-only. Không lấy score để lấp 717 S2 gốc hoặc tính baseline. |
| `InternVL3_V4_full_output_audit.json` local | 5.069 bytes, hash `95dd157338f1f5758bf6c981a9a32bff2252a08991f06c8e33439213720ef170`; tuyên bố integrity/raw replay | **REPORTED audit summary**: task không replay raw và chưa xác lập source/command/env của receipt local này; không nâng thành raw PASS mới. |
| Moondream2 | Có hồ sơ T1/capture PREP [M3][M3], chưa có TRAIN HNLO tương thích đủ điều kiện trong gói kiểm | Giữ roster bắt buộc. T1/capture CPU không là TRAIN PASS; không tự bỏ model/đổi endpoint. |
| Map site/video/camera/session, matched hazard–normal | Không có map chính thức xác minh đủ sample/cohort trong các artifact trên | Cần upstream provenance/adjudication và quyền nếu cần ảnh/nhãn mới. Hash family/point/platform không thay source identity. |

Bản dùng để tính đã stage vào `data/processed/seminar_feasibility_20261024/inputs/`
trong worktree PR, được ignore. Quyền CPU hồi cứu từ yêu cầu hiện tại áp dụng
metadata/saved reports hợp lệ; không kế thừa grant inference. Với Qwen3 chỉ
đọc manifest inventory, binding/result metadata và CSV, không mở raw logit/
journal payload. Quan hệ
xuyên split trong audit có sẵn được dùng đối soát ID; không truy cập dataset
TEST hoặc tính endpoint TEST.

## 3. Mâu thuẫn ID và mapping

Artifact đúng hash ghi `metallurgy-Level01-SuspendedRail-002660-001`, basename
`hand_frame_000067.jpg`, byte hash
`cbf22f0f8fadbcd42c70bc46ae50dacf91366b3b75ba81f1293bc7d984043f05`.
Đối tác exact là `oil_chemical-Level01-Wheeled-002353-001`. Qwen2.5 saved report
có đúng TRAIN ID `002660`, Level01/miền metallurgy; InternVL3 khớp qua exact join.

ID **đầy đủ** `metallurgy-Level01-SuspendedRail-002875-001` trong V không có
trong TRAIN audit. Point `002875` thực có ID
`oil_chemical-Level01-Wheeled-002875-001`, byte hash khác. Không join bằng đuôi
số hoặc tự đổi domain/platform. P90 dùng `002660`, nhất quán với artifact,
nhưng không xác nhận toàn bộ visual narrative.

So cả bảng V §2.1: **0/7 unordered ID pairs khớp pair table**. Danh sách đúng
hash dưới đây là metadata đã lưu, không phải review lại ảnh TEST:

| TRAIN ID trong audit đúng hash | TEST ID trong cùng pair table |
| --- | --- |
| `coal_conveyor-Level01-SuspendedRail-002589-001` | `coal_conveyor-Level02-SuspendedRail-002314-001` |
| `coal_conveyor-Level02-SuspendedRail-002654-001` | `coal_conveyor-Level02-SuspendedRail-002313-001` |
| `coal_conveyor-Level02-SuspendedRail-002653-001` | `coal_conveyor-Level02-SuspendedRail-002315-001` |
| `metallurgy-Level01-SuspendedRail-002660-001` | `oil_chemical-Level01-Wheeled-002353-001` |
| `oil_chemical-Level01-Wheeled-002757-001` | `oil_chemical-Level01-Wheeled-002321-001` |
| `oil_chemical-Level01-Wheeled-002758-001` | `oil_chemical-Level01-Wheeled-002322-001` |
| `tunnel-Level02-SuspendedRail-003148-001` | `tunnel-Level02-SuspendedRail-002465-001` |

**Hệ quả:** không dùng catalog visual làm map join/exclusion hoặc chứng cứ
nhãn đối tác. Các quan sát chuỗi/góc máy trong V còn là **lời audit lịch sử**
với membership chưa khép; cần người giữ evidence đối soát receipt/contact-sheet
gốc khi được phép. Chưa biết nguyên nhân là phiên bản dữ liệu, ánh xạ hay biên
soạn; không chọn một giả thuyết thành sự thật, không sửa snapshot. Aggregate
exact từ D khớp artifact; không lấy khớp aggregate để xác nhận ID/narrative V.

## 4. Phân tích C đã thực hiện

HNLO đã lưu giữ nguyên chiều lớn hơn là Anomaly; nhãn Level01–03 vs Level04.
Kiểm ID duy nhất, cùng nhãn/miền, SUCCESS, parsed/persisted, score hữu hạn;
lỗi/cohort thiếu làm STOP, không tự lấy giao rồi giấu mất mẫu. Không forward
model, tính lại logits, fit threshold hoặc sửa nhãn.

**Mọi weighting/grouping mới là PROPOSED_EXPLORATORY.** Với nhóm g(i), đặt
`w_i = 1 / |g(i)|`; ảnh giữ nguyên score/nhãn. AUROC là tổng
`w_pos × w_neg × concordance` trên cặp khác lớp, chia tổng trọng số cặp;
concordance=1/0/0,5 cho đúng/sai/tie. Đây là AUROC toàn cohort có trọng số,
không mean/max score nhóm, majority label hoặc trung bình AUROC nội nhóm.
Nhóm mixed có thể đóng góp cặp trong nhóm lẫn ngoài nhóm.

Tám giả định: mỗi ảnh riêng; exact-byte; point-only; regex-family-only; hợp
exact+point; exact+point+family; exact+point+dHash≤8; hợp cả bốn loại cạnh.
Union là connected components có bắc cầu; không suy đầu/cuối component giống
nhau hoặc cùng nguồn. dHash≤8 là cutoff audit cũ, chưa xác nhận precision cho
source grouping. Hai biến thể thêm chọn đại diện exact theo full ID đầu/cuối
thứ tự từ điển, không nhìn score để chọn.

Dựng nhóm lại chỉ trên ID từng cohort, không nối qua ảnh ngoài cohort. Khi
chia miền, **giữ trọng số tính trên toàn cohort**; group cross-domain có khối
lượng trong mỗi miền nhỏ hơn 1, không âm thầm chuẩn hóa lại. Group count không
được gọi là số nguồn độc lập hoặc cỡ mẫu độc lập hiệu dụng.

### TRAIN đầy đủ: coverage, support, nhóm một lớp

Qwen2.5/InternVL3 cùng **3.763 SUCCESS**, 749 A/3.014 N;
Level01/02/03/04 = 490/251/8/3.014. Coverage so metadata TRAIN là 100% mỗi model;
không phát hiện ID/nhãn/miền lệch hoặc score nonfinite.

| Giả định | Nhóm | A-only / N-only / mixed | Singleton | Lớn nhất |
| --- | ---: | ---: | ---: | ---: |
| Ảnh | 3.763 | 749 / 3.014 / 0 | 3.763 | 1 |
| Exact | 3.719 | 741 / 2.978 / 0 | 3.675 | 2 |
| Point | 2.424 | 749 / 1.675 / 0 | 1.394 | 4 |
| Family | 1.722 | 12 / 1.710 / 0 | 715 | 81 |
| Exact+point | 2.403 | 741 / 1.662 / 0 | 1.373 | 8 |
| Exact+point+family | 1.670 | 8 / 1.662 / 0 | 640 | 300 |
| Exact+point+near8 | 1.715 | 366 / 1.346 / 3 | 736 | 340 |
| Exact+point+family+near8 | 1.350 | 3 / 1.346 / 1 | 491 | 973 |

Có 3.636 cạnh TRAIN trong near-pool cũ, không gọi là confirmed duplicates.
Exact TRAIN có **44 nhóm size=2 = 88 ảnh**, gồm 8 cặp A và 36 cặp N. Byte/pixel
partitions khớp; 44/44 không xung đột severity/domain. Score và generated label
trong từng cặp đồng nhất ở cả hai model.

AUROC nội nhóm **undefined ở mọi nhóm exact, point, family và exact+point+family**
vì đơn lớp. Near graph có 3 mixed groups, hợp tất cả còn 1; đây là heuristic,
không phải matched sources cho A. Số nhóm nội AUROC undefined tương ứng
1.712/1.715 và 1.349/1.350. AUROC toàn cohort vẫn xác định vì còn hai lớp.
Không CI/resampling trong task; không có draw undefined bị loại âm thầm.

### TRAIN đầy đủ: AUROC và khoảng cách hai model

Mọi dòng weighting giữ 3.763 ảnh. Khối lượng là mẫu số trọng số, khác support
ảnh. Kết quả làm tròn 6 chữ số:

| Giả định | Khối lượng A / N | Qwen2.5 | InternVL3 | IVL3 − Q2.5 |
| --- | ---: | ---: | ---: | ---: |
| Ảnh, weight=1 | 749 / 3.014 | 0,826656 | 0,886182 | +0,059527 |
| Exact | 741 / 2.978 | 0,825397 | 0,885748 | +0,060351 |
| Point | 749 / 1.675 | 0,802368 | 0,889588 | +0,087220 |
| Family | 12 / 1.710 | 0,792265 | 0,858658 | +0,066393 |
| Exact+point | 741 / 1.662 | 0,801119 | 0,888861 | +0,087742 |
| Exact+point+family | 8 / 1.662 | 0,764951 | 0,835500 | +0,070550 |
| Exact+point+near8 | 367,018627 / 1.347,981373 | 0,784612 | 0,887747 | +0,103135 |
| Exact+point+family+near8 | 3,672148 / 1.346,327852 | 0,733765 | 0,791959 | +0,058195 |

Đại diện exact đầu **hoặc** cuối giữ **3.719 ảnh = 741 A/2.978 N** và cho đúng
AUROC dòng exact vì score/nhãn mỗi cặp giống nhau. Đây là sensitivity subcohort,
không xóa mẫu hoặc thay split chính thức.

**Diễn giải:** exact weighting đổi Q2.5 −0,001258805 và IVL3 −0,000434389 AUROC;
gap tăng +0,000824416. Tác động exact nhỏ trong hai vector này. Group heuristic
thay đổi lớn hơn, đồng thời thay thành phần domain/hazard mỗi lớp; chưa xác
định đó là giảm “leakage inflation”. Ranking gộp không đảo trong giả định đã
thử, chưa chứng minh bền với mọi mapping hoặc ưu thế thống kê. Không có TEST
scores để đo mức tăng hiệu năng TEST do bảy cặp xuyên split.

Theo ảnh, IVL3 hơn Q2.5 ở coal/metallurgy/oil, kém ở power/tunnel; dấu gap mỗi
miền giữ nguyên qua tám weighting. Ví dụ power: IVL3 0,706377 < Q2.5 0,872142.
Đây chưa là kiểm định chuyển miền độc lập.

### Ba model trên phần Qwen3 có provenance saved-score đủ điều kiện

**S0/S1/S3: 2.822/3.763 ảnh TRAIN (74,99%)**, 554 A/2.268 N;
L01/02/03/04 = 371/176/7/2.268. Ba model khớp đúng ID/nhãn/miền. Không gồm S2
duplicate, S2 gốc hoặc Recovery224. Không gọi là “V4-success 3.539 đã audit”;
cohort theo archive khả dụng, không chọn theo score tốt. Weighting giữ 2.822 ảnh:

| Giả định | Nhóm | Qwen2.5 | InternVL3 | Qwen3 | Q3 − IVL3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ảnh | 2.822 | 0,826860 | 0,885591 | 0,952823 | +0,067232 |
| Exact | 2.792 | 0,824970 | 0,885039 | 0,952443 | +0,067404 |
| Point | 2.012 | 0,811672 | 0,887481 | 0,945480 | +0,057999 |
| Family | 1.494 | 0,795573 | 0,845459 | 0,942726 | +0,097266 |
| Exact+point | 1.994 | 0,809827 | 0,886774 | 0,945192 | +0,058418 |
| Exact+point+family | 1.455 | 0,769489 | 0,833079 | 0,942127 | +0,109048 |
| Exact+point+near8 | 1.520 | 0,797508 | 0,881723 | 0,942639 | +0,060916 |
| Exact+point+family+near8 | 1.213 | 0,732620 | 0,770464 | 0,933619 | +0,163155 |

30 exact pairs trong cohort đồng score/nhãn ở ba model. Đại diện đầu/cuối giữ
2.792 ảnh (548 A/2.244 N), khớp exact weighting. Gộp cohort luôn Q3 > IVL3 > Q2.5
trong 10 biến thể; theo ảnh Q3 vẫn kém IVL3 ở coal/metallurgy. Không suy cohort
này đại diện phần S2 hoặc dân số mới; phân tích V4-success gốc đầy đủ ở dưới.

**Recovery224 riêng:** 224/224 SUCCESS, tương ứng 5,95% TRAIN;
L01/02/03/04 = 30/19/0/175, 49 A/175 N. Đối chiếu cùng 224 ID Q2.5/IVL3:

| Giả định | Qwen2.5 | InternVL3 | Qwen3 | Q3 − IVL3 |
| --- | ---: | ---: | ---: | ---: |
| Ảnh | 0,856093 | 0,933819 | 0,954519 | +0,020700 |
| Exact | 0,855501 | 0,933439 | 0,954492 | +0,021053 |
| Hợp exact+point+family+near8 | 0,862730 | 0,888199 | 0,956342 | +0,068143 |

Receipt có đủ 10 recovery variants. Ranking gộp vẫn Q3 > IVL3 > Q2.5. Có 1
exact pair Normal, đại diện giữ 223 ảnh (49 A/174 N). **Metallurgy recovery có
26 Normal, 0 Anomaly:** mọi AUROC/gap miền này undefined/null ở mọi biến thể.
Không có Level03 recovery. Không điền 0,5 cho thiếu mẫu số; các nhóm point,
family, exact trong recovery cũng đơn lớp.

Q3 recovery saved AUROC khớp số báo cáo 0,954519, không cấp quyền pooling.
**25/10 đã tái tính riêng V4-success gốc 3.539**, như mục kế tiếp. Bản ghép
3.763 V4+Recovery ở [RESULTS_AND_LIMITATIONS](RESULTS_AND_LIMITATIONS.md) vẫn
**REPORTED**, chưa được dùng làm baseline chính thức. Không so gap giữa các
cohort 2.822/224/3.539 như hiệu ứng của recovery hay của việc tìm lại S2.

### Khép Qwen3 V4 gốc — cập nhật 25/10/2026

**S2_ORIGINAL_IDENTITY=PASS; S2_SAVED_SCORE_VERIFICATION=PASS;
V4_ORIGINAL_COHORT_VERIFICATION=PASS. RAW_AUDIT=NOT_PERFORMED.**

ZIP **12.618.750 bytes**, SHA-256
`e77199b0818c45e2a15be2815485493fa4a78d064f82288d497fd8d82ecd4f0d`;
CRC toàn ZIP PASS, đúng một thư mục và sáu file cần thiết, không thiếu/thừa/
trùng member. TAR hash/size đúng giá trị gốc nêu ở inventory. Export checksum,
result hash `fcf70c6c6a8915f858cf95583ec40f02003379fd85c3f8681da2ec9c4500a1c6`,
sidecar manifest và manifest trong TAR cùng hash
`b5c5b3dfb6e9ad270174d364a7544ed93e4d47f8518e372ecdd106b862b33ae1`.
Các metadata/report member được kiểm hash/size với inventory. Không kiểm lại
hash từng raw payload hoặc replay logits; checksum receipt lịch sử tuyên bố
54.221 evidence members được đối soát với số entry của inventory, không biến
thành raw audit mới.

Bốn unit có model `Qwen/Qwen3-VL-8B-Instruct`, revision
`0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`, Python 3.12.13/CUDA 12.8/T4×2
theo metadata. Run IDs `hnlo-train-v4-qwen3-s{0..3}-a1`, attempt IDs
`hnlo-train-v4-qwen3-s{0..3}-20261019-a1`. Config scope khớp toàn bộ hợp đồng
[V4 contract][V4C] tại snapshot, gồm prompt hash, batch=1, max_new_tokens=32,
do_sample=false, threshold=null và retry/resume=false. Đây là xác minh metadata
cấu hình đã lưu, không tái xác minh runtime thật.

Binding samples khớp **đúng thứ tự, ID, image hash và locator** của bốn inference
manifests lịch sử đã khóa hash [cohort contract][V4M]. Sample journal trong
result, CSV và eligible IDs nhất quán; nhãn/miền khớp audit TRAIN đúng hash.
Không mở image locator. Common source metadata: implementation `a6e08ce…`,
authority `1ad2c1cb…`, merge/release `c9e22792…`, source payload `7817f431…`;
đầy đủ hashes/sizes và quan hệ binding ở receipt. S2 internal result trong TAR
khớp external result sau loại riêng trường export phát sinh sau đóng archive.

| Shard gốc | Planned | SUCCESS | TECHNICAL_ERROR | NOT_ATTEMPTED | SUCCESS A / N | AUROC saved score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| S0 | 941 | 941 | 0 | 0 | 173 / 768 | 0,958062380 |
| S1 | 941 | 941 | 0 | 0 | 192 / 749 | 0,957366767 |
| S2 gốc | 941 | 717 | 1 | 223 | 146 / 571 | 0,952642564 |
| S3 | 940 | 940 | 0 | 0 | 189 / 751 | 0,942757100 |
| V4 gốc | **3.763** | **3.539** | **1** | **223** | **700 / 2.839** | **0,952792734** |

Không overlap/thiếu ID ngoài các trạng thái đã ghi; union planned khớp đúng
3.763 ID TRAIN. SUCCESS support L01/02/03/04 = **460/232/8/2.839**. AUROC gộp
được tính trực tiếp từ vector 3.539 score với **700×2.839=1.987.300 cặp**,
không trung bình AUROC shard. Khớp giá trị lịch sử chính xác
`0.9527927338600111`; S2 có 83.366 cặp. Coverage **3.539/3.763 = 94,047302684%**,
không đổi mẫu số thành 3.539 để gọi 100%. Run V4 vẫn PARTIAL vì lỗi và phần
chưa chạy; xác minh cohort PASS không chứng minh hết selection bias.

### Ba model trên cùng 3.539 V4-success gốc

Exact join đủ 3.539 ID–nhãn–miền và score hữu hạn giữa Q2.5, IVL3, Q3. Các
model khác được giới hạn đúng SUCCESS IDs của Q3 gốc, không lấy giao tùy ý
hoặc thêm Recovery224. Weighting giữ đủ 3.539 ảnh; tất cả vẫn **PROPOSED_EXPLORATORY**.

| Giả định | Nhóm | Qwen2.5 | InternVL3 | Qwen3 | Q3 − IVL3 | IVL3 − Q2.5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Ảnh | 3.539 | 0,824382 | 0,882868 | 0,952793 | +0,069924 | +0,058487 |
| Exact | 3.499 | 0,823171 | 0,882282 | 0,952347 | +0,070065 | +0,059111 |
| Point | 2.332 | 0,803151 | 0,886062 | 0,942010 | +0,055948 | +0,082911 |
| Family | 1.677 | 0,790105 | 0,854154 | 0,940724 | +0,086569 | +0,064049 |
| Exact+point | 2.311 | 0,801857 | 0,885257 | 0,941696 | +0,056439 | +0,083400 |
| Exact+point+family | 1.627 | 0,762804 | 0,831761 | 0,940537 | +0,108776 | +0,068957 |
| Exact+point+near8 | 1.670 | 0,787269 | 0,884096 | 0,936447 | +0,052350 | +0,096828 |
| Exact+point+family+near8 | 1.322 | 0,723678 | 0,783838 | 0,933677 | +0,149840 | +0,060159 |

Hai đại diện exact đầu/cuối giữ **3.499 ảnh = 692 A/2.807 N**, cho cùng AUROC
dòng exact. Có 40 exact pairs (8 A, 32 N), score/nhãn đồng nhất cả ba model.
Nhóm exact/point/family/hợp exact+point+family đều một lớp; nội nhóm AUROC
undefined. Near8 union có 3 mixed groups, 1.667/1.670 nhóm undefined; hợp cả
bốn còn 1 mixed, 1.321/1.322 undefined. Group summary, khối lượng A/N, support
và mọi pairwise model gap của 10 biến thể đều có trong receipt.

Ranking gộp **Q3 > IVL3 > Q2.5** trong cả 10 biến thể; Q3−IVL3 từ khoảng
0,052350 đến 0,149840. Không chọn grouping theo gap; thay đổi estimand/mixture
của các nhóm một lớp vẫn hạn chế diễn giải. Theo ảnh, IVL3 dẫn coal/metallurgy,
Q3 dẫn oil/power/tunnel; metallurgy chỉ 9 A. Không có CI/source identity mới.

**Kết luận thay đổi:** số V4-success gốc trước chỉ REPORTED nay được kiểm
chứng ở cấp archive/metadata/saved-score. Blocker thiếu S2 gốc đã được gỡ.
**Kết luận giữ nguyên có căn cứ:** source-independent validity, A matched
hazard–normal, calibration/threshold và generalization vẫn chưa chứng minh;
khuyến nghị C cho Seminar, A mở rộng có điều kiện vẫn phù hợp. Không suy ưu thế
thống kê từ thứ hạng quan sát, không pooling V4+Recovery thành baseline 3.763.

## 5. Đánh giá cuối hướng A

**Chưa có bằng chứng đủ mạnh về cùng nguồn nhưng khác trạng thái nguy cơ.**
D ghi 53 exact pairs đều cùng trạng thái nhị phân; TRAIN exact vừa đối soát
cũng không đổi nhãn. Point/family TRAIN đều đơn lớp. V ghi DIFFERENT_HAZARD
nhưng Anomaly–Anomaly, không phải Anomaly–Normal; ID catalog còn mâu thuẫn.
Mixed components do dHash không phải source identity đã xác minh. Thiếu bằng
chứng không chứng minh A bất khả thi; hiện chưa nhận dạng hazard contrast khi
giữ nguồn cố định.

| Thành phần A | Làm được trên bằng chứng hiện tại | Phần còn đợi |
| --- | --- | --- |
| Đại số/đối chứng HNLO | Phân biệt score với generated label/calibrated risk; saved-score và dependence sensitivity; yêu cầu đối chứng công bằng | Continuous baselines khác cần raw summary được phép. Can thiệp prompt/label encoding cần inference mới được duyệt; quyền CPU này không cho chạy. |
| Hazard so với nuisance/source | Xác định thiếu overlap; ID/prefix/Level/TXT mang nhãn, không làm feature đối chứng | Map source đáng tin, matched hazard–normal, nuisance controls và proxy người/thiết bị được chuyên gia duyệt; quyền ảnh/annotation nếu cần. |
| Transfer/quyết định an toàn | Mô tả giới hạn, coverage, endpoint chưa có threshold | Dữ liệu độc lập theo nguồn/exposure, development/target, protocol/ngưỡng duyệt trước quan sát target và authority riêng. TRAIN phơi nhiễm không đổi tên thành holdout. |

**Tính mới:** đánh giá 23/10 đã chỉ ra công trình gần R12 có cả generative scorer
control. VLM, continuous score, log-odds hoặc đổi CLIP sang Qwen không đủ là
đóng góp mới. Khả năng vượt phần đã khảo sát nằm ở **bằng chứng mới** về
label/decision-token invariance kết hợp matched natural hazards, source controls
và external cohort; hiện chưa có. C có giá trị Seminar ở phân tích tái lập và
giới hạn diễn giải, chưa tự đạt novelty paper chỉ nhờ lỗi dataset/thêm model.

**Giữ A làm hướng Khóa luận có điều kiện**, không cam kết full A. Trước hết
phải xác minh đường tiếp cận nguồn có hai trạng thái, quyền dùng, gán nhãn
chuyên gia và cohort độc lập. Nếu thiếu tại mốc chốt thiết kế do giảng viên
ấn định, dừng claim construct validity/transfer và tiếp tục C/replication hẹp.
Không tự đặt N/power, deadline hay ngưỡng thành công khi chưa có effect,
số nguồn và ngân sách.

## 6. Bảng trạng thái và blocker

| Phân loại | Việc / bằng chứng | Trạng thái thực tế |
| --- | --- | --- |
| **Đã hoàn thành** | Inventory/checksum, phân cấp evidence, đối soát 002875/002660 và 7 visual pairs, code CPU, hồ sơ/brief, tự review | Hoàn thành trong phạm vi PR; không sửa lịch sử. |
| **Đã kiểm chứng** | 3.763 Q2.5/IVL3 ID–GT–domain/saved AUROC; Q3 đủ bốn shard V4 gốc/3.763 planned và 3.539 SUCCESS; recovery riêng; 44 exact TRAIN pairs | Archive/metadata/saved-score verification; raw PASS Q2.5 kế thừa, không raw PASS mới Q3/IVL3. |
| **Mới là thăm dò** | 10 biến thể × 4 cohort; AUROC/gaps, weighting/đại diện, support/undefined | Đã tính thật; **PROPOSED**, không metric/protocol/split chính thức. |
| **Chưa thực hiện được** | Raw replay Q3/IVL3 trong task; CI/kiểm định theo nguồn; TEST leakage impact; causal hazard validity; threshold safety | Saved-score S2/V4 đã khép, các blocker còn lại về evidence/mapping/authority không được thay bằng heuristic. |
| **Phải xin quyền hoặc thêm data** | Raw replay còn thiếu; source/visual adjudication, proxy/annotation, matched/independent cohort; inference/TEST nếu cần sau này | Artifact và authority cụ thể; Draft PR không cấp quyền. |

| Blocker | Đầu vào để mở lại | Phần độc lập đã hoàn thành |
| --- | --- | --- |
| S2 gốc: **ĐÃ KHÉP 25/10** | Đã có đúng ZIP/TAR, binding/941 trạng thái/717 SUCCESS; raw replay vẫn ngoài scope | Thêm V4-success 3.539; giữ 30 biến thể cũ và Recovery224 riêng; không diagnostic thay thế. |
| Visual catalog không khớp | Receipt/contact-sheet/ID map/version dataset gốc và người review; mở ảnh/annotation sau quyền | Dùng TRAIN metadata audit đúng hash; narrative visual vẫn kế thừa, membership chưa khép. |
| Thiếu source identity/overlap | Upstream map sample→site/video/camera/session hoặc adjudication có provenance/coverage; hai trạng thái/nuisance phù hợp | C thăm dò; không gọi group count là source count. |
| Raw audit chưa khép | Raw artifacts, execution source/hợp đồng audit và quyền replay; Q25 còn giới hạn outer receipt | Saved-score validity; receipt local tuyên bố replay không là PASS của task. |
| Moondream2 thiếu HNLO TRAIN | Raw-hook/decision/state validation và kết quả tương thích được phép; hoặc Lead duyệt N/A/fallback/hoãn | Giữ bốn model trong scope, không giả có kết quả thứ tư. |
| A/transfer/threshold thiếu data/protocol | Cohort độc lập, nhãn hazard đáng tin, source/exposure controls, phê duyệt trước đánh giá | Câu hỏi/giới hạn; không mở TEST hoặc tự tạo split/ngưỡng. |

## 7. Hai phương án và khuyến nghị

| Tiêu chí | C trọng tâm Seminar; A mở rộng có điều kiện | Giữ D9R22, thu hẹp kết luận |
| --- | --- | --- |
| Câu hỏi | Kết luận score nhạy thế nào với đơn vị/trọng số đánh giá, vì sao chưa suy độc lập nguồn? | Phân loại zero-shot, lỗi nghiêm trọng và bất đồng theo D9R22, với giới hạn dữ liệu phụ thuộc. |
| Có ngay | Sensitivity đã tính, identity reconciliation, coverage/undefined | Qualification/hợp đồng lịch sử và generated labels; chưa đồng nghĩa xong D9R22 bốn model. |
| Cần thêm | Lead duyệt hướng/estimand, PROPOSED và roster; source review nếu muốn claim mạnh | Production/metric/freeze, predictions/coverage đủ roster, authority chạy nếu thiếu; HNLO không thay RQ3 disagreement. |
| Claim bảo vệ được | Audit/độ nhạy hồi cứu exposed TRAIN, không source-independent AUROC/causal validity/novel method | Phân loại/lỗi/bất đồng mô tả theo scope duyệt; không transfer/reliability guarantee nếu chưa kiểm định độc lập. |
| Rủi ro | Heuristic mang nhãn, thiếu nguồn thật, novelty một dataset hẹp | Chi phí bốn model/protocol; disagreement có thể suy biến, không confidence đã hiệu chuẩn. |
| Seminar thực tế | Gói CPU/lập luận dùng ngay sau duyệt scope | Phụ thuộc nhãn/coverage và thời gian hoàn tất hợp đồng, không hứa từ baseline HNLO hiện có. |

**Ưu tiên C**: đã lượng hóa độ nhạy trên evidence hiện hữu, có đầu ra Seminar
không phụ thuộc inference mới, xử lý điểm yếu chung mọi hướng. Exact effect
nhỏ/ranking không đảo vẫn là kết quả hợp lệ; không chọn grouping theo mức giảm
AUROC hoặc gọi heuristic là nguồn thật. Đề xuất khác ưu tiên A dài hạn ngày
23/10 ở **mốc Seminar và data thực có**, không phủ nhận A.

**Thành công C:** giảng viên chấp nhận đóng góp audit/sensitivity; input/cohort
traceable; grouping, endpoint, coverage/undefined và mức kiểm chứng đầy đủ;
roster/N/A rõ. Không đòi AUROC giảm hoặc ranking đảo. Nếu Seminar bắt buộc
claim độc lập nguồn, matched hazard validity hoặc kết quả đầy đủ bốn model
ngay, **gói C hiện chưa đáp ứng**: cần bổ sung hoặc duyệt thu hẹp.

**Dừng:** checksum/ID/provenance sai → dừng phép tính liên quan; thiếu source
map → dừng source inference/CI; thiếu matched/independent data → dừng claim
A/transfer. Chưa có quyết định đổi scope thì **D9R22 tiếp tục có hiệu lực**;
D9R22 không tự khắc phục phụ thuộc nguồn hoặc cấp inference. Không lập protocol
chính thức trong hồ sơ này.

## 8. Bản ngắn trình giảng viên

**Tên làm việc đề xuất:** “SafeShift: Độ nhạy của đánh giá VLM nhận diện nguy
cơ công nghiệp trước ảnh lặp và phụ thuộc nguồn”. Chưa đổi tên/protocol dự án.

- **Nghiên cứu gì, vì sao cần?** Bảng điểm cao có thể phản ánh nguy cơ, bối
  cảnh và cách đếm ảnh. Kiểm tra kết luận khi giảm ảnh hưởng ảnh trùng và thử
  các giả định nhóm minh bạch.
- **Khác trước ở đâu?** Đóng góp Seminar là evidence reconciliation và độ
  nhạy định lượng trên saved predictions, kể cả ranking không đổi. Chưa nhận
  thuật toán mới/“đầu tiên”; Khóa luận cần matched/source/external và label
  invariance vượt phần đã nghiên cứu.
- **Data đáp ứng không?** Đủ hồi cứu hai model/3.763 ảnh và ba model trên
  **3.539 SUCCESS V4 gốc đã xác minh**; giữ 2.822 cũ và recovery/224 riêng để
  truy vết. Q3 còn 1 lỗi/223 chưa chạy trong planned 3.763; chưa đủ source
  identity, matched hazard–normal hoặc TRAIN HNLO model thứ tư.
- **Seminar xong gì?** Công cụ CPU có tests, coverage/ID conflicts, AUROC/gap/
  sensitivity đã tính và giới hạn. Chưa xong CI theo nguồn, ngưỡng an toàn,
  transfer hoặc raw audit mới.
- **Khóa luận mở rộng?** A có điều kiện: nguồn hai trạng thái, nhãn chuyên gia,
  nuisance/mã hóa nhãn controls, cohort độc lập; thiếu data thì C/replication.
- **Cần duyệt gì?** C hay D9R22; mức đóng góp, roster/N/A, estimand/grouping,
  artifact/source-review permissions, nguồn/annotation độc lập, nguồn lực.

## 9. Quyết định còn chờ phê duyệt

1. Chọn hướng; nếu đổi D9R22/DEC-PA3-011 hoặc A/C, ghi **quyết định mới
   append-only dưới docs/** sau duyệt, không sửa log cũ.
2. Chấp nhận/sửa estimand hồi cứu, weighting/đại diện và grouping sensitivity.
   Không bỏ chữ PROPOSED để thành benchmark. CI cần source unit xác minh và
   protocol riêng.
3. Đáp ứng bốn model, gồm N/A/fallback/hoãn nếu cần; không loại theo score.
   Kết quả một phần có đủ yêu cầu Seminar hay cần bổ sung?
4. S2 gốc đã khép saved-score; còn quyền/trách nhiệm khép raw/receipt audit,
   đối soát visual IDs.
   Ảnh/annotation/TEST/inference sau này cần authority đúng phạm vi.
5. Dữ liệu A, người xác minh nguồn/nhãn, independent target, mốc GO/STOP và
   ngân sách; chốt trước quan sát target, không tạo split/ngưỡng để có số đẹp.

## 10. Tái lập, kiểm thử, bàn giao

Python **3.11.9**, Windows; standard library, không dependency mới; seed=null.
Run cũ `seminar-feasibility-20261024-analysis-v2` trên parent `c492a0b…`, source
được lưu tại `bb31ef7…`. Run mới **`seminar-feasibility-20261025-analysis-v4`**
trên parent `bb31ef7…`, implementation chưa commit, ghi source SHA-256 đúng
bytes được bàn giao. Receipt giữ riêng provenance/validation cũ và mới; HEAD
cuối lấy từ PR/Git, không nhúng hash tự tham chiếu vào tài liệu.

Stage **artifact được phép** vào thư mục ignored §2: Q25 CSV, InternVL zip,
metadata audit; tùy chọn ba Q3 result S0/S1/S3 và recovery result theo tên R3,
bốn archive S0/S1/S3/recovery theo basename trong export. ZIP S2 gốc đặt riêng
tại `data/processed/seminar_feasibility_20261025/inputs/Qwen3-Shard2-V4.zip`.
Không dùng S2 diagnostic. Tool lấy receipt và ordered inference metadata bất
biến bằng `git show`, không tải data/model hoặc mở ảnh/annotation.

```console
python -B -m scripts.analyze_source_sensitivity --input-dir data/processed/seminar_feasibility_20261024/inputs --metadata-audit data/processed/seminar_feasibility_20261024/inputs/duplicate_metadata_audit.json --include-qwen3-available --qwen3-original-s2-zip data/processed/seminar_feasibility_20261025/inputs/Qwen3-Shard2-V4.zip --output data/processed/seminar_feasibility_20261025/analysis_v4.json
python -B -m unittest discover -s tests -v
git diff --check
```

Output tồn tại thì từ chối ghi đè; rerun chọn tên mới. Receipt chứa input/member/
source hashes, môi trường, lệnh và output hash. Full output có cả các miền theo
mọi weighting nằm local `data/processed/`. Receipt Git giữ số gộp **40 kịch bản**
và các miền theo ảnh, không ID–score vector. Giữ các output cũ, không ghi đè.

**Lượt 24/10:** 40/40 unittest PASS, không FAIL/SKIP; 16 tests bằng fixture
tổng hợp: oracle cặp/ties/weights, lớp rỗng/đơn lớp, graph bắc cầu/mixed, exact
join/lỗi/flags/nonfinite, checksum, member archive trùng/thiếu/symlink, chỉ đọc
manifest/report Q3, chặn overwrite. Verification số độc lập dùng **BFS khác
implementation và liệt kê cặp positive–negative trực tiếp**, khớp **80/80 AUROC
gộp**, sai số tối đa `2.886579864025407e-15`. Đây là kiểm tra CPU cùng task,
không phải lượt kiểm toán độc lập Antigravity. Verifier/output local ở run
directory, hash/lệnh ghi trong receipt.

**Lượt 25/10:** **51/51 unittest PASS**, 0 FAIL/SKIP; thêm 11 tests tổng hợp cho
ZIP/CRC/hash, archive/manifest/export, ID thiếu/thừa/trùng/order, config/unit,
status/coverage/eligible IDs, nhãn/score nonfinite và undefined, cấm recovery
hoặc diagnostic thay V4 gốc. BFS/pairwise oracle độc lập khớp **110/110 AUROC
gộp** của 40 kịch bản, sai số tối đa `3.9968028886505635e-15`; xác nhận 30 kịch
bản cũ giữ nguyên giá trị. Đây là self-verification cùng task, không là lượt
audit độc lập Antigravity.

Kiểm tra riêng không tái dùng rank implementation: đếm hai lần concordance
bằng số nguyên, cho S2 **158.836/(2×83.366)** và V4-success gốc
**3.786.970/(2×1.987.300)**, khớp chính xác hai AUROC đã nêu. Kiểm cả S0/S1/S3
theo cách này sai khác tối đa `1.1102230246251565e-16` do float. Receipt giữ
tử số/mẫu số và kết quả, không lưu các cặp hoặc score theo ảnh vào Git.

Không chạy GPU/inference, dataset TEST/ảnh/annotation khóa, raw replay, CI,
threshold selection hoặc thí nghiệm mới vì ngoài scope/thiếu mapping/quyền.
Không sửa sáu Draft PR cũ hoặc ref lưu trữ. Dừng ở **Draft PR #131**, chờ
ChatGPT kiểm tra toàn bộ PR; **không merge, không gọi Antigravity**.

[D]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/duplicate_leakage_audit.md
[V]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/visual_provenance_review.md
[F]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/research_feasibility_audit.md
[I]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/distribution_imbalance_audit.md
[P90]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_seminar_direction_runbook.md
[M3]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/reports/three_model_scientific_analysis_20261023.md
[R3]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/evidence/three_model_20261023/verification_20261023.json
[S3]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/evidence/three_model_20261023/SafeShift_three_model_report_20261023.md
[Q25]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_r2_cpu_completion_20261015.md
[V4C]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/safeshift/diagnostics/hnlo_train/contract.py
[V4M]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/safeshift/diagnostics/hnlo_train/cohort.py
