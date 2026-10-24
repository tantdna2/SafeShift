# SafeShift — Hồ sơ quyết định khả thi Seminar

Ngày 24/10/2026, Asia/Bangkok. **BASE_SHA / main đã xác minh:**
`2810bee6f404a1c41cca4a2bbe45baf5ac48358a`.
Tiếp tục branch PR #131 từ `c492a0b546248f1e9496dfa0248450548ace5ba1`.
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

Số chính xác, checksum, coverage và mọi kết quả gộp của 30 kịch bản nằm trong
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
| Qwen3 S2 gốc | Cần archive hash `2dc356fcba9fe2ce5dfc4e3dc9a45286fe5382f574c02d38d7517580e38cd920`; chưa có tại các vị trí đã kiểm | Blocker cho vector V4 gốc đầy đủ, AUROC/gap/ranking toàn V4 gốc. Không tuyên bố mất ở mọi kho Owner. |
| S2 cùng basename đang có | Hash lại **12.038.105 bytes**, `508a2e122ee999da728e8d09c66f5157331e6fe1a40adaa82e2869a30c6e0147`, khác hash gốc | **SECOND_DUPLICATE_S2_DIAGNOSTIC**, consistency-only. Không lấy score để lấp 717 S2 gốc hoặc tính baseline. |
| `InternVL3_V4_full_output_audit.json` local | 5.069 bytes, hash `95dd157338f1f5758bf6c981a9a32bff2252a08991f06c8e33439213720ef170`; tuyên bố integrity/raw replay | **REPORTED audit summary**: task không replay raw và chưa xác lập source/command/env của receipt local này; không nâng thành raw PASS mới. |
| Moondream2 | Có hồ sơ T1/capture PREP [M3][M3], chưa có TRAIN HNLO tương thích đủ điều kiện trong gói kiểm | Giữ roster bắt buộc. T1/capture CPU không là TRAIN PASS; không tự bỏ model/đổi endpoint. |
| Map site/video/camera/session, matched hazard–normal | Không có map chính thức xác minh đủ sample/cohort trong các artifact trên | Cần upstream provenance/adjudication và quyền nếu cần ảnh/nhãn mới. Hash family/point/platform không thay source identity. |

Bản dùng để tính đã stage vào `data/processed/seminar_feasibility_20261024/inputs/`
trong worktree PR, được ignore. Quyền CPU hồi cứu từ yêu cầu hiện tại áp dụng
metadata/saved reports hợp lệ; không kế thừa grant inference. Với Qwen3 chỉ
đọc manifest inventory và CSV, không mở raw logit/journal payload. Quan hệ
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
này đại diện S2 thiếu hoặc dân số mới.

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
**Không tính** AUROC toàn V4 gốc 3.539 hoặc bản ghép 3.763. Các số Q3
0,952793/0,952935 ở [RESULTS_AND_LIMITATIONS](RESULTS_AND_LIMITATIONS.md) vẫn
**REPORTED**. Không so gap 2.822 với gap 224 như hiệu ứng của recovery.

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
| **Đã kiểm chứng** | 3.763 Q2.5/IVL3 ID–GT–domain/saved AUROC; Q3 S0/S1/S3/recovery archive–manifest–CSV–IDs; 44 exact TRAIN pairs | Artifact/saved-score verification mới; raw PASS Q2.5 kế thừa, không raw PASS mới Q3/IVL3. |
| **Mới là thăm dò** | 10 biến thể × 3 cohort; AUROC/gaps, weighting/đại diện, support/undefined | Đã tính thật; **PROPOSED**, không metric/protocol/split chính thức. |
| **Chưa thực hiện được** | Toàn vector Q3 V4 gốc; CI/kiểm định theo nguồn; TEST leakage impact; causal hazard validity; threshold safety | Blocker data/mapping/authority, không lấy số báo cáo/heuristic thay đầu vào. |
| **Phải xin quyền hoặc thêm data** | Raw replay còn thiếu; source/visual adjudication, proxy/annotation, matched/independent cohort; inference/TEST nếu cần sau này | Artifact và authority cụ thể; Draft PR không cấp quyền. |

| Blocker | Đầu vào để mở lại | Phần độc lập đã hoàn thành |
| --- | --- | --- |
| S2 gốc thiếu/hash sai lượt | Owner cung cấp archive đúng `2dc356fc…cd920` hoặc CSV gốc có binding manifest/receipt/source/run gốc; kiểm 717 SUCCESS và failure tail | Q2.5/IVL3 đầy đủ, Q3 S0/S1/S3/recovery riêng; không diagnostic thay thế. |
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
- **Data đáp ứng không?** Đủ hồi cứu hai model/3.763 ảnh, ba model/2.822 ảnh,
  recovery riêng/224. Chưa đủ source identity, matched hazard–normal, Q3 S2
  gốc hoặc TRAIN HNLO model thứ tư.
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
4. Quyền/trách nhiệm tìm S2 gốc, khép raw/receipt audit, đối soát visual IDs.
   Ảnh/annotation/TEST/inference sau này cần authority đúng phạm vi.
5. Dữ liệu A, người xác minh nguồn/nhãn, independent target, mốc GO/STOP và
   ngân sách; chốt trước quan sát target, không tạo split/ngưỡng để có số đẹp.

## 10. Tái lập, kiểm thử, bàn giao

Python **3.11.9**, Windows; standard library, không dependency mới; seed=null.
Run `seminar-feasibility-20261024-analysis-v2` trên parent PR head `c492a0b…`
với implementation chưa commit, ghi trung thực cùng source SHA-256 ở receipt.
Commit cuối chứa đúng source bytes đó; HEAD cuối lấy từ PR/Git, không nhúng hash
tự tham chiếu vào tài liệu.

Stage **artifact được phép** vào thư mục ignored §2: Q25 CSV, InternVL zip,
metadata audit; tùy chọn ba Q3 result S0/S1/S3 và recovery result theo tên R3,
bốn archive theo basename trong export. Không dùng S2 diagnostic. Tool lấy
receipt bất biến bằng `git show`, không tải data/model.

```console
python -B -m scripts.analyze_source_sensitivity --input-dir data/processed/seminar_feasibility_20261024/inputs --metadata-audit data/processed/seminar_feasibility_20261024/inputs/duplicate_metadata_audit.json --include-qwen3-available --output data/processed/seminar_feasibility_20261024/analysis_v2.json
python -B -m unittest discover -s tests -v
git diff --check
```

Output tồn tại thì từ chối ghi đè; rerun chọn tên mới. Receipt chứa input/member/
source hashes, môi trường, lệnh và output hash. Full output có cả các miền theo
mọi weighting nằm local `data/processed/`. Receipt Git giữ số gộp 30 kịch bản
và các miền theo ảnh, không có ID–score vector. `analysis.json` (hai model) và
`analysis_v2.json` (thêm cohort Q3 riêng) giữ riêng, không ghi đè lịch sử.

**Đã chạy:** 40/40 unittest PASS, không FAIL/SKIP; 16 tests mới bằng fixture
tổng hợp: oracle cặp/ties/weights, lớp rỗng/đơn lớp, graph bắc cầu/mixed, exact
join/lỗi/flags/nonfinite, checksum, member archive trùng/thiếu/symlink, chỉ đọc
manifest/report Q3, chặn overwrite. Verification số độc lập dùng **BFS khác
implementation và liệt kê cặp positive–negative trực tiếp**, khớp **80/80 AUROC
gộp**, sai số tối đa `2.886579864025407e-15`. Đây là kiểm tra CPU cùng task,
không phải lượt kiểm toán độc lập Antigravity. Verifier/output local ở run
directory, hash/lệnh ghi trong receipt.

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
