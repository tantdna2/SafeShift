# SafeShift — Source Feasibility Gate

Ngày 24/10/2026. **BASE_SHA:** `2810bee6f404a1c41cca4a2bbe45baf5ac48358a`,
khớp `refs/heads/main` trên GitHub khi kiểm tra bằng `git ls-remote`.
Nguồn lịch sử dưới đây đều tại **`31a04e6f7175cca818c63b4de0153246b3f3ecdb`**.
Đây là đánh giá điều kiện khả thi, không phê duyệt hướng hoặc thực nghiệm.

## 1. Executive summary

Trong báo cáo này, **C** là phân tích ảnh hưởng của lặp ảnh/phụ thuộc nguồn lên
diễn giải kết quả; **A** là kiểm định hazard validity bằng đối chứng cùng nguồn,
khác trạng thái Anomaly–Normal và đánh giá độc lập. Không dùng các chữ A/C này
để chỉ các mục grounding trùng tên trong feasibility audit W1.

| Cấp | Phán quyết kỹ thuật | Căn cứ và giới hạn công bố |
| --- | --- | --- |
| 1. C: mô tả và độ nhạy hồi cứu | **CONDITIONAL GO** | Có thể tổng hợp bằng chứng đã báo cáo ngay; phân tích số mới chỉ sau khi xác minh quyền dùng, checksum và phép nối score–ID–group. Chưa có kết quả độ nhạy theo nhóm. [M3][M3], [R3][R3]. |
| 2. C: kết luận thống kê điều chỉnh theo nguồn đáng tin | **NO-GO hiện tại** | Chưa có mapping nguồn độc lập được xác minh; receipt ghi `source_groups_verified_independent=false`. CI, ưu thế thống kê hoặc thứ hạng sau điều chỉnh: **NOT_VERIFIABLE**. [R3][R3]. |
| 3. A: cặp cùng nguồn–khác nguy cơ và dữ liệu độc lập | **NO-GO hiện tại** | Chưa có cặp Anomaly–Normal cùng nguồn đáng tin trong hồ sơ đã đọc; TRAIN đã phơi nhiễm không phải holdout. Đây là thiếu bằng chứng, không phải bằng chứng A bất khả thi. [V][V], [P90][P90], [M3][M3]. |

Các phán quyết trên là **PROPOSED** để trình duyệt. **VERIFIED (hồ sơ):** D9R22
vẫn có hiệu lực, DEC-PA3-011 vẫn **PROPOSED**, A/C chưa được phê duyệt; yêu cầu
bốn mô hình vẫn giữ nguyên. Không thay protocol, metric, split hay authority.
[Phạm vi hiện tại][B-SCOPE], [roadmap hiện tại][B-ROADMAP].

## 2. Phân cấp bằng chứng nguồn

**VERIFIED:** trực tiếp đối chiếu văn bản/receipt trong Git, không hàm ý kiểm tra
lại dữ liệu. **INHERITED_AUDIT:** kế thừa audit lịch sử, không tái mở ảnh hoặc
rehash dataset. **REPORTED:** có báo cáo nhưng chuỗi xác minh chưa khép.
**UNKNOWN:** thiếu thông tin. **PROPOSED:** phương án/đánh giá chờ duyệt.
`NOT_VERIFIABLE` là trạng thái câu trả lời khi đầu vào chưa đủ, không phải số 0.

| Bằng chứng / đơn vị | Mức | Điều đã biết và giới hạn |
| --- | --- | --- |
| External byte-exact và decoded RGB-exact | **INHERITED_AUDIT** | 53 nhóm, mỗi nhóm 2 ảnh: 44 cặp trong TRAIN, 2 trong TEST, 7 xuyên split. Cả 53 byte-exact cũng pixel-exact; không có cặp pixel-exact bổ sung khác bytes. 38 cặp Normal–Normal, 15 Anomaly–Anomaly; 7 xuyên split đều Anomaly–Anomaly, khác point ID. Đây là identity của ảnh, chưa phải identity của site/video. [D, “Exact external image identity”][D]. |
| Định danh 7 cặp exact xuyên split | **INHERITED_AUDIT**, membership cần đối soát | Catalog có full sample IDs ở [V §2.1][V]: ba cặp `phone→phone`, một `hand→hand`, một `hand→nonmask`, hai `hand→cigarette`. Có xung đột Level01/02 và domain/platform; không có cặp Anomaly–Normal. Danh sách đầy đủ 53 nhóm nằm ở artifact local, không có trong note aggregate. |
| dHash ≤8 xuyên split | **INHERITED_AUDIT** | 833 cặp = 7 exact + 826 nonexact candidates. Không gọi 826 candidates là confirmed leakage; dHash=0 cũng không đủ xác nhận. [D, “Near pool”][D]. |
| Visual review 50 cặp nonexact được chọn có chủ đích | **INHERITED_AUDIT** | 22 cặp Anomaly–Anomaly cùng cảnh/khung gần; 7 Anomaly–Anomaly cùng góc máy nhưng khác hazard; 21 Normal–Normal cùng góc máy. Không ngoại suy tỷ lệ này sang 826 cặp hoặc coi 50 cặp là 50 nguồn độc lập. [V §4][V]. |
| 12 regex source-family pools xuyên split | **INHERITED_AUDIT** | Bao phủ 1.000 Anomaly (749 TRAIN/251 TEST), không có Normal. Là pool tên nguồn/chủng loại hazard, không phải 12 video hay site đã xác minh. Chỉ số frame thấp/cao phân chia có hệ thống theo family không tự chứng minh thời gian quay liên tục. [D][D], [V §3][V]. |
| Bằng chứng chuỗi/góc máy cụ thể | **INHERITED_AUDIT** | V §3 ghi ví dụ mạnh ở `nonmobile`, `phone`, `cigarette`, `fire`, `others`, `nonmask`, `liquid`, `hand`, `head`; `smog` chỉ PLAUSIBLE; `fall`/`dooropen` không có shared-source evidence trong mẫu được review. Riêng `nonmobile` được audit mô tả 100 frame của một clip khoảng 40 giây; chưa có original-video ID/receipt để xác minh lại ở gate này. Không nâng nhãn family thành identity của mọi thành viên. [V §3.2–3.3][V]. |
| Site/video/camera/session thật | **UNKNOWN** về mapping đầy đủ | Hồ sơ không cung cấp official map tới từng sample; 2.239 sites được paper báo cáo chưa nối được với 3.234 point folders. Visual timestamps/viewpoints là bằng chứng cục bộ kế thừa, không phải camera/session registry được xác thực. [F §3, §17.1][F], [V][V]. |
| Point ID, platform, domain | **INHERITED_AUDIT** | Point-ID overlap TRAIN/TEST bằng 0 vẫn đi cùng exact reuse và shared viewpoints; `robot_platform` là token loại robot, không phải camera ID. Receipt TRAIN ghi 2.424 point groups, 12 anomaly/1.710 normal regex keys và independence=false. [D][D], [I §15][I], [R3][R3]. |
| Cặp cùng nguồn Anomaly–Normal | **UNKNOWN — NOT_VERIFIABLE** | Các cặp exact và visual được catalog ở trên đều cùng trạng thái nhị phân. `DIFFERENT_HAZARD` trong V là Anomaly–Anomaly; khác Level01/02 cũng không tạo Normal control. Không có bằng chứng đủ cho matched controls của A. [D][D], [V §2, §4][V]. |

**VERIFIED (đối chiếu tài liệu):** V §2.1 nêu TRAIN
`metallurgy-Level01-SuspendedRail-002875-001`, còn P90 §2 nêu
`metallurgy-Level01-SuspendedRail-002660-001` thuộc bảy TRAIN ID exact với TEST.
Hai ghi chép chưa thống nhất membership; không tự sửa hoặc chọn một bản làm
chuẩn. **UNKNOWN:** ID nào khớp artifact gốc là **NOT_VERIFIABLE** từ notes.
Cần đối soát pair table đúng hash trước mọi join/exclusion; aggregate “7 cặp”
vẫn chỉ được kế thừa ở mức audit đã báo cáo. [V][V], [P90][P90].

## 3. Ma trận phép phân tích khả thi

**VERIFIED (receipt):** lần phân tích 23/10 ghi 3.763 ID/label/domain khớp giữa
Qwen2.5 và InternVL3, có tái tính saved-score AUROC; đây không phải raw audit
mới. Qwen2.5 kế thừa raw audit CPU lịch sử; InternVL3 ở mức saved-score.
Qwen3 có `complete_member_level_validation=false`, `qwen3_pooled_auroc_recomputed=false`;
S2 duplicate diagnostic chỉ dùng consistency, không chứng minh S2 V4 gốc.
[R3][R3], [M3, “Nguồn và mức kiểm chứng”][M3].

**VERIFIED (inventory Git/receipt):** thư mục evidence M3 không chứa bộ score
per-image và group map đầy đủ để chạy lại từ Git. R3 khóa metadata audit bằng
SHA-256 `16039f2302027ffe53f3bcdbfc80c762c88e823fbf303d5672030587cd9602d6`;
phải lấy đúng artifact được phép và kiểm tra phép nối, không tái tạo từ dữ liệu
bị khóa. Khả dụng hiện tại của các file local: **UNKNOWN**. [R3][R3], [D][D].

**REPORTED:** AUROC Qwen3 V4/Recovery/bản ghép và membership gốc chưa được kiểm
chứng lại đầy đủ. Archive S2 đầu tiên cần hash
`2dc356fcba9fe2ce5dfc4e3dc9a45286fe5382f574c02d38d7517580e38cd920`;
receipt chỉ nói chưa tìm thấy ở các vị trí đã kiểm tra, không chứng minh mất ở
mọi nơi. Giữ `baseline_pooling_allowed=false`. [M3][M3], [R3][R3].

| Phép phân tích | Có thể làm từ hồ sơ nào / cần thêm gì | Trạng thái và kết luận tối đa |
| --- | --- | --- |
| Mô tả exact/candidate/family, imbalance, coverage và mức audit | D/V/F/I, M3/R3; không cần mở dataset | **INHERITED_AUDIT / REPORTED — GO** cho tóm tắt có dẫn nguồn; không tạo hiệu năng mới. |
| Nhắc AUROC/gap/thứ hạng theo ảnh đã báo cáo | M3/R3; giữ tách cohort và mức xác minh từng model | **REPORTED — GO** cho mô tả cũ; thứ hạng quan sát không phải ưu thế thống kê. |
| So theo ảnh với exact-group weighting hoặc một đại diện/nhóm | Saved score, nhãn, ID, group map hash-verified của cùng TRAIN cohort; chốt quy tắc đại diện/trọng số trước tính | **PROPOSED — CONDITIONAL GO** cho độ nhạy lặp ảnh; kết quả hiện **NOT_VERIFIABLE**. Exact identity không gom hết cùng video/góc máy. Không đổi split chính thức. |
| So theo ảnh với point-only, regex-family hoặc graph có cạnh dHash | Cùng đầu vào trên, thêm loại cạnh, coverage, singleton, xung đột và quy tắc tạo component | **PROPOSED — chỉ sensitivity giả định**. Point/family có thể tách cùng nguồn hoặc gộp khác nguồn; không gọi đây là source-adjusted estimate đáng tin. |
| Thống kê score/lỗi trong từng nhóm | ID–score/prediction–label–group đã nối; cần nhãn sinh ra cho phân tích lỗi | **PROPOSED — CONDITIONAL GO** mô tả. Nhóm chỉ Anomaly có thể mô tả recall/FNR của nhãn, nhóm chỉ Normal có FPR; không tính AUROC nội nhóm một lớp. |
| AUROC/gap/CI theo nguồn đáng tin, paired cluster uncertainty | Map nguồn được review, đủ nguồn độc lập mỗi lớp, score cùng ID và cohort, protocol được duyệt | **UNKNOWN — NO-GO hiện tại**. Group count từ metadata không phải số nguồn độc lập đã xác minh. [M3, “Khoảng tin cậy”][M3]. |
| Lượng hóa ΔAUROC, thay đổi model gap hoặc đảo thứ hạng do grouping | Vector điểm từng ảnh + mapping; so model trên cùng giao ID hợp lệ, giữ lỗi/coverage; Qwen3 cần đúng S2 gốc | **UNKNOWN — NOT_VERIFIABLE** cho cả tác động lẫn chiều tác động. Qwen2.5/InternVL3 có tiền đề saved-score, nhưng chưa xác minh lại phép nối group trong gate này; không suy ra tác động từ aggregate AUC. |
| Dùng diagnostic 90 ảnh làm kết quả nhóm | P90 có thiết kế/exposure; V90 ghi NOT_EXECUTED, mọi tiêu chí NOT_EVALUATED | **VERIFIED (hồ sơ) — NO-GO** cho hiệu năng/CI từ lượt này. Component bảo thủ lớn nhất là giả định quan hệ, không phải nguồn thật. [P90][P90], [V90][V90]. |
| A: matched hazard–normal / kiểm tra chuyển nguồn độc lập | Cặp xác minh cùng site/camera/view, khác trạng thái; cohort độc lập và authority mới | **UNKNOWN — NO-GO hiện tại**; cần bằng chứng mới và phê duyệt trước truy cập/thực hiện. [F][F], [M3][M3]. |

**PROPOSED — quy tắc diễn giải cần duyệt:** AUROC nội nhóm/stratum chỉ có một
lớp là **undefined**, không phải 0,5; chênh AUROC cũng undefined nếu một vế
undefined. Recall/FNR thiếu Anomaly hoặc FPR thiếu Normal có mẫu số 0. Riêng
AUROC gộp giữa các nhóm đơn lớp vẫn có thể xác định nếu toàn cohort có cả hai
lớp và score, nhưng chỉ so khác nhóm, không chứng minh phân biệt hazard trong
cùng nguồn. Không gán nhãn đa số hoặc lấy mean/max score nhóm hỗn hợp để tạo
endpoint mới khi chưa duyệt. [M3, RQ2 và khoảng tin cậy][M3].

**PROPOSED — giới hạn uncertainty:** nhóm quá ít không tự làm mọi point estimate
undefined; nó làm suy luận theo nguồn thiếu cơ sở. Nếu một lớp chỉ nằm trong
một nguồn, không ước lượng được biến thiên giữa nguồn của lớp đó; resample mất
một lớp làm AUROC undefined. Phải báo support, số nguồn mỗi lớp và tỷ lệ draw
undefined, không bỏ draw âm thầm. Với mapping đáng tin mới xét paired cluster
draws giữ nguyên cluster/duplicate component cho mọi model. Hiện chưa có CI
theo nguồn đáng bảo vệ; i.i.d. image bootstrap/DeLong không giải quyết phụ
thuộc nguồn ở đây. Đây là tiêu chí khả thi, chưa chọn estimator hay chạy CI.
[M3, “Khoảng tin cậy và hạn chế khoa học”][M3].

## 4. Nguy cơ sai lệch và rò rỉ nhãn

- **INHERITED_AUDIT — nhãn lộ trực tiếp:** `safety_level`, `data_type`, token
  `Level01–04`/`Normal` trong sample ID và path mã hóa nhãn đích. ID dùng để
  join sau chấm điểm, không làm feature của đối chứng nguồn. TXT mô tả hazard
  và prefix `phone`/`hand`/`fire` mang nội dung nhãn; chúng không phải đối chứng
  provenance độc lập với nguy cơ. Hash tên family không loại bỏ rò rỉ này.
  [F §3][F], [P90 §2][P90], [V §3][V].
- **INHERITED_AUDIT — shortcut nguồn/nhãn:** tư cách thành viên 12 anomaly
  families suy trực tiếp Anomaly trong bản audit. Presence của Other_modalities
  chỉ có ở một phần Normal; có modality kéo theo Normal trong scope đó, nhưng
  thiếu modality không kéo theo Anomaly. Không dùng chúng làm kiểm chứng
  hazard validity độc lập. [F §3][F].
- **INHERITED_AUDIT — thiếu overlap/confounding:** domain/platform và mức nhãn
  không tách độc lập; coal không có wheeled, Level03 chỉ có 8 TRAIN, TEST
  metallurgy không có Anomaly. Có 36 folder/text conflicts (32 TRAIN theo M3).
  Không tự sửa domain/nhãn, không coi metadata-only performance là hazard
  recognition hoặc điều chỉnh thống kê tự khắc phục được vùng thiếu overlap.
  [I §15][I], [M3, RQ2][M3].
- **INHERITED_AUDIT / REPORTED — selection và exposure:** TRAIN đã quan sát;
  diagnostic 90 ảnh được thiết kế sau P2, có thành phần near/family bảo thủ
  chứa 48/90 ảnh (42/45 Anomaly). Qwen3 có OOM/rerun/Recovery riêng; thành công
  recovery không chứng minh vắng selection bias. Không gọi TRAIN/90 ảnh là
  independent holdout; không nâng consistency thành raw PASS. [P90][P90], [M3][M3].
- **UNKNOWN — hiệu ứng leakage lên điểm:** exact/shared-viewpoint tồn tại
  không chứng minh mô hình đã ghi nhớ, không xác định AUROC bị tăng bao nhiêu
  hay thứ hạng sẽ đổi chiều. Cần phân tích có đầu vào phù hợp, không suy số
  hoặc nhân quả từ counts duplicate. [D, giới hạn][D], [M3][M3].

## 5. Điều kiện cho ba cấp GO/NO-GO

Các điều kiện sau đều **PROPOSED**, không cấp quyền triển khai.

| Cấp | Đầu vào bắt buộc | Đã có / còn thiếu | Điều kiện dừng | Kết luận tối đa |
| --- | --- | --- | --- | --- |
| **1 — CONDITIONAL GO** | Notes/receipt; nếu tính độ nhạy: saved per-image score, nhãn, prediction khi cần, ID, group map, provenance/checksum và quyền dùng artifact | Có audit D/V và saved-score verification Qwen2.5/InternVL3. Thiếu join được kiểm chứng ở gate; membership exact chưa thống nhất; Qwen3 gốc thiếu score/provenance đầy đủ. | STOP phần tính khi không khớp hash/ID/cohort, thiếu quyền truy cập, chưa giải quyết membership, phải mở dữ liệu khóa hoặc thay diagnostic S2 cho S2 gốc. Có thể tiếp tục phần mô tả. | Mô tả TRAIN và độ nhạy theo grouping nêu rõ giả định nếu sau này đủ đầu vào; chưa kết luận hiệu năng sau điều chỉnh lúc này. |
| **2 — NO-GO hiện tại** | Map sample→site/video/camera/session hoặc dependence cluster được xác minh, coverage/cạnh/xung đột rõ; đủ nguồn độc lập mỗi lớp; score cùng cohort và protocol thống kê được duyệt | Có exact identity và visual cases cục bộ. Thiếu map nguồn đầy đủ, số nguồn độc lập thực, overlap và score Qwen3 gốc. | STOP nếu chỉ đổi tên family/point thành nguồn thật, gộp dHash candidates thành confirmed groups, lớp thiếu support hoặc quá ít nguồn để suy uncertainty. Không thay bằng CI i.i.d. | Hiện chỉ công bố chưa đủ bằng chứng thống kê theo nguồn; mở lại gate khi mapping và đầu vào đạt yêu cầu. Không tuyên bố ưu thế/ranking bền vững. |
| **3 — NO-GO hiện tại** | Matched Anomaly–Normal xác minh cùng nguồn/view và trạng thái; nhãn hazard độc lập; đủ nguồn/cặp; dữ liệu đánh giá độc lập theo nguồn và exposure; protocol/authority được duyệt trước quan sát target | Có gợi ý cùng cảnh/chuỗi trong từng lớp; chưa có matched pair khác trạng thái đáng tin hoặc holdout độc lập được xác lập trong hồ sơ. | STOP nếu “khác hazard” chỉ đổi loại/level trong Anomaly, match bằng label-bearing prefix, thiếu đối chứng Normal, không chứng minh độc lập hoặc cần truy cập chưa được phép. | Chỉ công bố nhu cầu bằng chứng cho A. Nếu được bổ sung, mở lại gate; thiết kế quan sát matched cũng chưa tự chứng minh quan hệ nhân quả. |

**PROPOSED — đường chuyển sang A:** cần upstream mapping hoặc xác minh nguồn
mới có receipt, sample IDs và tiêu chí match về site/camera/view/session; xác
minh cả Anomaly lẫn Normal và các nuisance như người/thiết bị/ánh sáng. Nếu
phải thu thập ảnh, gán nhãn hoặc tiếp cận dữ liệu độc lập mới, trình kế hoạch
và authority trước. Matching và kế hoạch đánh giá phải chốt trước xem điểm
target; quy mô cần căn cứ số nguồn/cặp độc lập và mục tiêu ước lượng, chưa đặt
ngưỡng N tùy ý. Không mở TEST hoặc tạo split trong gate này. [F §3][F], [M3][M3].

## 6. Hai phương án trình giảng viên

1. **PROPOSED — C cho Seminar, A mở rộng có điều kiện.** Seminar có thể tập
   trung kiểm toán đơn vị đánh giá, phụ thuộc và độ nhạy hồi cứu; các kết quả
   hiện chỉ là descriptive TRAIN. Phê duyệt C và artifact scope trước tính mới;
   nếu chỉ đủ hai model thì trình coverage/N/A riêng, không tự bỏ Moondream2
   hoặc nâng Qwen3. A chỉ mở sau cấp 3 đạt gate. Nếu cấp 1 không khép được đầu
   vào, thu hẹp thành phân tích giới hạn thay vì hứa số liệu sensitivity.
2. **PROPOSED — giữ D9R22, thu hẹp kết luận.** Giữ RQ phân loại xuyên miền,
   lỗi nghiêm trọng và bất đồng theo phạm vi hiện hành; dùng gate này như giới
   hạn về nguồn. Không đổi RQ thành HNLO/C, không gọi bảng TRAIN là chuyển miền
   độc lập hoặc benchmark bốn mô hình hoàn tất. Implementation/protocol freeze,
   bằng chứng bốn model và quyền chạy vẫn là các việc cần duyệt riêng.

Cả hai phương án chờ quyết định chính thức; reset repository và Draft PR này
không thay quyết định nghiên cứu. [Phạm vi][B-SCOPE], [roadmap][B-ROADMAP].

## 7. Quyết định cần giảng viên / Research Lead phê duyệt

- **PROPOSED:** chọn phương án Seminar; nếu chọn C/A hoặc thay DEC-PA3-011,
  ghi quyết định mới dưới `docs/` trước áp dụng, giữ nguyên lịch sử D9R22.
- **PROPOSED:** chốt estimand theo ảnh/nhóm, grouping nào là sensitivity,
  quy tắc trọng số/đại diện, xử lý conflicts/undefined và protocol uncertainty;
  không tự đổi metric, nhãn, split hay threshold.
- **PROPOSED:** quyền dùng đúng saved artifacts/metadata và phạm vi đối soát
  membership; tìm đúng Qwen3 S2 gốc, tách rerun/recovery, không tự pooling.
- **PROPOSED:** tiêu chí và quyền xác minh nguồn/matched controls, thu thập
  hoặc gán nhãn mới, cohort độc lập và exposure controls cho A.
- **PROPOSED:** cách đáp ứng đủ bốn model; N/A/fallback/hoãn nếu cần phải được
  duyệt riêng. Gate không cấp quyền GPU, inference, TEST hoặc dữ liệu khóa.

**VERIFIED (phạm vi kiểm tra gate):** đã đọc tài liệu main được yêu cầu và chọn
lọc bảy tài liệu lịch sử, bổ sung duy nhất receipt R3 để đối chiếu score/ID/
provenance. Không đọc ảnh, raw annotation, TEST, raw output hoặc artifact local
bị khóa; không tính số nghiên cứu mới. Kiểm tra đường dẫn/commit dẫn nguồn,
trạng thái khoa học, cấu trúc Markdown và `git diff --check` trước commit.
Không chạy tests phần mềm vì chỉ thêm tài liệu; không tái chạy audit/model.
Chỉ thêm báo cáo này, không cần sửa roadmap. Dừng ở Draft PR, chờ ChatGPT
kiểm tra GitHub trực tiếp; không merge, không gọi Antigravity.

Phương pháp rà bằng chứng dùng `scientific-critical-thinking` v1.5.
Tham chiếu công cụ: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner,
A. M. (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for
Research Agents](https://doi.org/10.48550/arXiv.2609.00065), bản arXiv hiện tại
v2 được kiểm tra ngày 24/10/2026; không dùng làm bằng chứng về dataset.

[D]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/duplicate_leakage_audit.md
[V]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/visual_provenance_review.md
[F]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/research_feasibility_audit.md
[I]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/distribution_imbalance_audit.md
[P90]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_seminar_direction_runbook.md
[V90]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/PA3_SEMINAR_DIRECTION_VERDICT.md
[M3]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/reports/three_model_scientific_analysis_20261023.md
[R3]: https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/evidence/three_model_20261023/verification_20261023.json
[B-SCOPE]: https://github.com/tantdna2/SafeShift/blob/2810bee6f404a1c41cca4a2bbe45baf5ac48358a/docs/RESEARCH_OVERVIEW.md
[B-ROADMAP]: https://github.com/tantdna2/SafeShift/blob/2810bee6f404a1c41cca4a2bbe45baf5ac48358a/docs/ROADMAP.md
