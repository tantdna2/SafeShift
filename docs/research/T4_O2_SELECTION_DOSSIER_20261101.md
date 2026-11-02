# T4 — hồ sơ quyết định lựa chọn kết quả O2

## Issue169 successor full TRAIN

Ngày **02/11/2026, Asia/Bangkok**. `T4-O2-FULLTRAIN-SELECTION-REPAIR-v2`:
**PROPOSED_FOR_OWNER_REVIEW; SCIENTIFIC_SELECTION=PENDING; EXECUTION=BLOCKED**.
[Issue #169](https://github.com/tantdna2/SafeShift/issues/169) chỉ cho lập hồ sơ
và kiểm metadata tracked. BASE `afc932b2a43cf829db12f53d6ac3d578c6123eec`,
[PR168 hậu merge](https://github.com/tantdna2/SafeShift/pull/168#issuecomment-6570735120)
đã được đối chiếu GitHub; engineering #167 hoàn tất đúng CPU synthetic scope.
Phần này nối tiếp T4-v1/TRAIN160, không hồi tố các snapshot §1–8 bên dưới.
Đây là **một hồ sơ lựa chọn nguồn**, chưa là ledger cho phép chạy hoặc protocol
frozen. [Receipt Issue169](evidence/issue169_source_checks.md) ghi phép kiểm,
hash và giới hạn; các giá trị đầy đủ dùng lại [receipt T4](evidence/t4_o2_metadata_20261101.json).

### S1. Nguồn đề nghị và mức kiểm hiện tại

`VERIFIED_169_METADATA` chỉ nghĩa bytes/identity/counts giữa tài liệu tracked
đã đối chiếu trong task này. `INHERITED` là kiểm archive/raw/custody của task
trước; `REPORTED` là lời handoff chưa có binding độc lập; `UNKNOWN` là thiếu
chứng từ. Không nâng mức kiểm lịch sử vì hash tài liệu khớp. Không mở HANDOFF
local, manifest private, ZIP, per-image report/GT/raw hoặc tab Downloads.

| Nguồn được đề nghị | Pin phải giữ / bằng chứng | Kế thừa có điều kiện và phần thiếu |
| --- | --- | --- |
| Qwen3 focal candidate | Đúng model/revision, bốn V4 ORIGINAL run/attempt, implementation `a6e08ce…`, payload/authority/planned manifest/archive/report/result/binding SHA ở §3.1 và `qwen_original_shards` T4. So chéo T0/source receipt: VERIFIED_169_METADATA. | Giữ 3.539 SUCCESS, 1 TECHNICAL_ERROR, 223 NOT_ATTEMPTED trong 3.763. Archive/member và ordered membership INHERITED; series ID và standalone effective-config SHA UNKNOWN. Không biến authority SHA thành config SHA; xem S3/L2. |
| InternVL3.5 peer candidate | Đúng `OpenGVLab/InternVL3_5-4B-HF` revision, RECOVERY run/series/attempt, archive/receipt/manifest SHA tại §3.2; khớp projection T0: VERIFIED_169_METADATA. Source/config vẫn REPORTED handoff trong T4; đối chiếu literal không chứng minh execution binding. | 135 SUCCESS/25 INVALID, 0 error/0 pending trong160. Hai historical run IDs chỉ là danh sách; ordered ancestor graph/hash UNKNOWN. Implementation ID riêng và report-member SHA UNKNOWN; L3 chưa khép. Không lấy predictions từ ancestors. |
| MiniCPM label-only peer candidate | Đúng `openbmb/MiniCPM-V-4` revision, FP32 INITIAL run/series/attempt, source/config/descriptor/archive/manifest ở §3.2. Receipt #165 khớp T4: VERIFIED_169_METADATA; runtime `c3c223bc69edd253d57bbba9344e0633b65b3de4`, environment SHA `59ee1406a67cd79987956c8f06c649ab355444876974537c1ab084e0a9ff3194`. | 155 SUCCESS/5 INVALID trong160; HNLO Method A **0/155**, giữ label-only theo [Owner](https://github.com/tantdna2/SafeShift/pull/166#issuecomment-6567502211). Archive validation #165 INHERITED; public receipt không cung cấp report-member seal nên L3 còn BLOCKED. |

MiniCPM weights FP16/eager, chỉ resampler attention score/softmax/value product
FP32 rồi trả dtype gốc. Không đổi thành toàn model FP32. `verification_sha256`
trong receipt #165 là chứng từ derivation khác với `receipt_sha256` technical160
ở T4; không so chúng như cùng một file. Runtime/hash #165 định danh execution
cũ, không phải qualification HEAD #169. InternVL runtime commit gắn riêng với
selected execution chưa được public T4/T0 receipt chứng minh: UNKNOWN, không
lấy runtime của MiniCPM hoặc smoke để điền.

Đề nghị nguồn dựa trên provenance official đã định danh, **không theo metric,
số SUCCESS hoặc thời gian mới nhất**. Qwen Recovery224/composite/S2 diagnostic,
peer smoke/engineering/FP16/attempt khác giữ EXCLUDED khỏi nguồn predictions;
ancestor evidence vẫn cần cho custody. Không lấy legacy InternVL3-2B thay 3.5.

### S2. Quy tắc kế thừa và repair được trình duyệt

1. **Một planned cohort:** custodian phải seal đúng ordered 3.763 TRAIN IDs và
   image-hash mapping từ master đã khóa, đối chiếu bốn Qwen shards cùng
   manifest160. Các planned-manifest hashes và manifest160 đã có ở T4;
   **successor full-cohort projection SHA/order mapping hiện UNKNOWN**. Tổng
   3.763 không chứng minh exact membership. Không tạo manifest từ counts;
   mọi model được O3 chọn dùng cùng projection sau L4/O4. Không đổi split/GT.
2. **Hai lớp bản ghi:** lịch sử gốc bất biến; successor ledger riêng trỏ
   archive/member/row reference, source/config/run/series/attempt, outcome SHA,
   operation và approval ref. Lớp vận hành phục vụ scheduling khác lớp
   scientific selection. Một candidate đã chạy160 có **3.603 ngoài phạm vi
   pilot**, không được sửa report160 thành 3.763 NOT_ATTEMPTED. Chỉ sau mapping
   và custody mới khởi tạo pending cho phần chưa chạy của successor. Thiếu
   history/mâu thuẫn là UNKNOWN/BLOCKED, không mặc nhiên chưa chạy.
3. **Kế thừa có điều kiện:** đề nghị xét 3.539 Qwen SUCCESS, 135 InternVL
   SUCCESS và 155 MiniCPM SUCCESS làm immutable reference outputs; giữ cả
   1/25/5 lỗi và 223 pending. Dùng chúng trong bảng full TRAIN **còn BLOCKED**
   đến khi O2 duyệt exact bridge + comparability + selection ledger. Mở rộng
   peer160 sang3763 là campaign/cohort mới, không gọi là resume Candidate160.
   Không tự ghép inherited SUCCESS với các lượt mới để tuyên bố baseline3763.
4. **Selection rule đề nghị cho successor:** khóa nguồn từng ID trước chạy;
   chỉ tiếp nối đúng series đã chỉ định. Sau khi bridge được duyệt, một ID
   chưa chạy lấy outcome của lần được schedule có quyền; một ID failed chỉ
   có thể có successor outcome qua repair được chỉ định trước, kể cả outcome
   mới vẫn INVALID/error. Không chọn best/latest successful trong nhiều
   attempts. Mỗi repair bổ sung cần quyết định phạm vi trước lượt đó, liên kết
   outcome cha và giữ cả trước/sau. Không dùng GT/metric chọn ID sửa hoặc
   attempt. Bảng original vẫn riêng; bảng successor phải công bố số inherited,
   newly attempted, repaired, unresolved và mọi deviation. Quy tắc này chưa
   có hiệu lực cho kết quả thật và không cho completion union giữa series.
5. **Nếu không chứng minh comparability:** giữ nguồn cũ làm historical
   reference, trình rerun toàn3763 trong series mới; không backfill từ series
   cũ, không tự chạy rerun. Failure không sửa hợp lệ phải giữ negative result,
   nguyên nhân/giới hạn và trình scope O1/O3; không bỏ khỏi planned denominator.

| Chế độ đề nghị | Eligibility / evidence trước lượt chạy | Ranh giới |
| --- | --- | --- |
| `resume` fulltrain | Chỉ NOT_ATTEMPTED trong đúng successor series/cohort; kiểm đủ ancestors, identity, reservations/partial raw và grant | SUCCESS/INVALID/consumed error không tự gọi lại. Không đổi recovery160 lịch sử. |
| `repair` có mục tiêu | Chỉ INVALID/TECHNICAL_ERROR được khóa bằng outcome hash; diagnosis + root-cause evidence, fix SHA, regression receipt, identity diff, cap/stop và approval binding | Không retry ngầm. Raw/attempt mới append-only; phân biệt thay đổi vận hành với scientific replacement. Unknown cause hoặc partial consumption chưa đối soát → BLOCKED. |
| `rerun` | Tất cả3763, series mới, attempts có giới hạn và grant mới; giữ liên kết reference cũ | Không completion từ series cũ; không so metric để quyết định giữ run nào. |

Counts để lập kế hoạch, **không phải lịch thực thi đã duyệt**: Qwen223 pending
và1 error; InternVL3603 ngoài pilot và25 INVALID; MiniCPM3603 ngoài pilot và5
INVALID. `3539+1+223=3763`, `135+25+3603=3763`, `155+5+3603=3763`.
Không cộng các model thành số ảnh độc lập hoặc suy coverage thành accuracy.

Diagnosis cần phân biệt load/environment, OOM/resource, timeout/interrupted,
raw-write/export/pipeline, token/parse alignment và hành vi sinh không đúng
C1. Hiện **không đủ chứng từ công khai để kết luận nguyên nhân từng ca lỗi**;
nhất là25/5 INVALID không được coi mặc định là parser bug. Custodian cung cấp
projection chẩn đoán theo quyền; lưu FAIL và negative regression. MiniCPM HNLO
null đã được chấp nhận label-only, không phải target repair để ép có score.

Thay prompt/parser/generation/processor/preprocessing/model/revision/weights,
precision/numerical implementation phải có identity/version/series mới và O2
comparability trước dùng chung; không dùng parser lax/bóc fence hay GT chữa
nhãn. Sửa môi trường/storage hoặc source/runtime dù dự kiến giữ semantics
vẫn cần identity diff, regression, review và G0–G6/O6 đúng release; hash đổi
không được giả là runtime cũ. Theo contract #167, identity đổi không tiếp nối
cùng series. Không có tolerance, equivalence threshold hay quyền run được
suy từ sửa lỗi kỹ thuật.

### S3. Qwen legacy và ma trận thẩm quyền hiện hành

Đề nghị representation Qwen: giữ `series_id=null` và
`standalone_effective_configuration_sha256=null`, kèm lý do UNKNOWN và exact
authority bytes SHA đã có. Định danh source bằng tuple bốn immutable
run/attempt/archive/report/planned-manifest bindings ở T4. Có thể tạo **ID
ledger successor mới sau duyệt**, nhưng không gọi ID đó là series lịch sử;
không bịa historical parent. Custodian cần xác nhận field có tồn tại trong
nguồn được phép hay không và ký projection binding; O2 phải chấp nhận rõ
representation legacy và giới hạn. Không lấy `a1`, ngày hoặc hash archive
làm series. Nếu contract native cần field không chứng minh được: BLOCKED
bridge, trình rerun series mới; không thay lock V4 hoặc nhập code legacy.

| Quyết định | Trạng thái / bằng chứng | Người có thẩm quyền và điều kiện GO | Blockers liên quan |
| --- | --- | --- | --- |
| O1 — hướng/đóng góp | **OWNER_DIRECTION_ACCEPTED**, [01/11](DECISIONS.md#dec-20261101-t1-owner-false-safe-direction), [full TRAIN02/11](DECISIONS.md#dec-20261102-owner-thesis-fulltrain-repair). Học vụ/negative route **PENDING**. | Owner quyết phạm vi dự án; giảng viên/người duyệt học vụ phải xác nhận đóng góp/endpoint/negative route. Không coi Owner là chữ ký học vụ. | B5; không mở L1 từ hướng đã chọn. |
| O2 — source/series/comparability và phương pháp | **PENDING/BLOCKED**; T4-v1 và v2 đều đề nghị. Issue169/merge168 chỉ cho hồ sơ/engineering. | Owner/Research Lead trong thẩm quyền được chứng minh duyệt exact version/hash, Qwen legacy, riêng InternVL RECOVERY, FP32 INITIAL label-only, inheritance/repair và phạm vi. Protocol/ranking/estimand cần phê duyệt riêng; không đóng toàn O2 bằng lựa chọn nguồn. | L1–L4, B5/B6. |
| O3 — final roles/qualification | **PENDING**; Qwen focal có điều kiện + hai peers ứng viên, dừng tuyển thứ tư đã có quyết định. | Owner/Research Lead chốt exact roles sau evidence quality/coverage/utility/cost có quyền; nếu Qwen không đạt thì STOP và trình lại, peer không đạt thì trình giảm scope. Không tự chọn roster. | L3/L4, B6; B5 về khả thi. |
| O4 — rights/custody/nguồn/GT | **PENDING/BLOCKED cho successor access và V/T**; TRAIN H/D đã phơi nhiễm, T1 rights/source audit kế thừa. | Chủ dữ liệu/người được ủy quyền cấp đúng processing/cloud/export; custodian seal mapping/exposure; chuyên gia/người có quyền nhãn xác nhận rubric/GT. Owner không cấp thay quyền bên thứ ba. | L2–L4; B1–B4. |
| O5 — ngân sách/stop/precision | **PENDING**; T1 §5 là quy trình chọn giá trị, không approval. | Owner và người duyệt khoa học chốt caps/time/resources/retries/stop, review K/b, gain/severe margin, events/sources/uncertainty từ evidence khả thi. Không lấy caps160 hoặc fixture #167 làm quyền3763. | B5, B2/B3/B4 cho precision; L1 cho repair selection. |
| O6 — từng run | **BLOCKED/NOT_GRANTED** trong Issue169. Grant V4/TRAIN160 không chuyển sang fulltrain. | Người có quyền dữ liệu/tài nguyên cấp exact source/runtime/notebook/Input/model/config/cohort/run/attempt/expiry/limits sau O2–O5 và release checks; ChatGPT review/audit/merge riêng không thay grant. | B1/B6, L1–L4; G0–G6 chưa final live verification. |

Đây là ma trận O1–O6 dùng cho successor này; bảng four-peer cũ trong kế hoạch
là snapshot đề xuất đã bị thay ở phạm vi hướng, **không được dùng mở lại bốn
model ngang hàng**. Không sửa M1/M2, không suy O7 reviewer/user-study đã duyệt.

| Gate | Hiện tại và chứng từ còn thiếu để đóng | Phạm vi bị chặn |
| --- | --- | --- |
| L1 | PENDING: quyết định exact v2/hash/ref/time và người duyệt hợp lệ; bao gồm riêng InternVL RECOVERY, Qwen legacy, rule repair | Selection thật; direction/merge không đóng L1. |
| L2 | BLOCKED: custodian xác nhận Qwen series/config representation và archive→authority→report binding; O2 chấp nhận giới hạn | Native legacy bridge/kế thừa; không bịa field. |
| L3 | BLOCKED: report-member name/SHA cho từng peer, selected execution→source/config/implementation/manifest binding; InternVL ordered ancestor graph + snapshot hashes, không predictions từ ancestors | Kế thừa hai peers. Receipt #165 bổ sung MiniCPM runtime/env nhưng không đóng toàn gate. |
| L4 | BLOCKED: paired160 ledger vẫn thiếu; successor cần exact3763 projection/order/hash chung,160 subset mapping, row provenance, access receipt và ngoại lệ/missing counts | Join/analysis full TRAIN. Không sửa yêu cầu160 cũ thành giả chứng từ3763 đã có. |
| B1 | BLOCKED cho phạm vi mới: release/rights/custody đúng dữ liệu, cloud, storage/export/retention và người cấp; license kế thừa không là chứng nhận mới | Access/run successor; không mở private vì thấy đường dẫn. |
| B2 | BLOCKED: source owner/site/video/session registry, duplicate/dependence certificate và unknown coverage | Xác nhận độc lập/CI theo nguồn; không cấm lập hồ sơ H/D metadata đang được cấp. |
| B3 | BLOCKED: exposure ledger, independent V/T seals/custodian/access và overlap certificate | V/T; TRAIN chia lại không thành holdout, TEST tiếp tục đóng. |
| B4 | BLOCKED: quyền/rubric nhãn tương thích, blinded experts/adjudication/uncertainty plan đã duyệt cho nguồn mới | GT/annotation xác nhận; không sửa nhãn InspecSafe hay dùng VLM làm GT. |
| B5 | BLOCKED: O2/O5 version/numerical register, nguồn lực examiner/compute và học vụ/negative route | Protocol freeze, precision và claim hiệu quả; không có giá trị mặc định. |
| B6 | BLOCKED: exact release/model qualification, selection/paired outputs/cost/coverage và grant | Full native execution và scientific qualification; technical160 không chứng minh3763. |

B2–B4 chưa khép không ngăn hoàn thành **hồ sơ metadata** #169. Muốn phân tích
H/D hoặc chạy TRAIN cần scope/task/rights riêng; xác nhận trên V/T cần toàn bộ
chứng từ độc lập tương ứng. Không yêu cầu mở TEST để gỡ bất kỳ blocker nào.

### S4. False-safe và câu hỏi O2 để quyết định

Giữ [T0 §§6–10](T0_FALSE_SAFE_DESIGN_20261101.md): false-safe là focal sinh
Level04 hợp lệ trong khi GT Level01–03; severe là GT Level01. Planned P chung,
C focal-Normal không dùng GT, F false-safe trong C có GT hợp lệ; F không đổi
theo missing peers. `found=|F∩R|`, capture=found/|F| với cùng K giữa arms;
F rỗng → undefined. INVALID/missing không là Normal/hazard; GT unresolved vẫn
ở workload. Mandatory/overload và null HNLO giữ riêng, không điền score0.
Đưa ca vào queue chỉ là **capture-at-review**, không tự sửa nhãn, tăng
Accuracy/Macro-F1, giảm tai nạn hoặc xác nhận độc lập. Không tính bảng thật
trong #169; primary endpoint/ranking cụ thể vẫn O2 PENDING.

E1 baseline cùng planned/focal outputs/F/K và cost; E2 bỏ HNLO/từng peer,
learned arm chỉ nếu được cấp; E3 shared error/missing/overload/shift; E4 ca tốt
hơn/tệ hơn/không đổi; E5 exact provenance, raw-before-parse và mọi failure.
Đây là yêu cầu thiết kế, chưa kết quả E1–E5. Bảng original và successor có thể
có focal outputs/F khác sau repair: không so capture giữa hai bảng rồi gọi
là cùng estimand, không chọn bảng tốt hơn. O2 phải khóa focal snapshot cho
mỗi comparison trước phân tích; không học/chọn policy trên V/T đã xem.
20% review,10 điểm phần trăm gain,CI95%,power80% **chưa được duyệt**; không
đặt giá trị thay thế. Full TRAIN là H/D, không đáp ứng độc lập chỉ nhờ đủ3763.

**Câu hỏi trình Owner/Research Lead:** Có chấp thuận có điều kiện
`T4-O2-FULLTRAIN-SELECTION-REPAIR-v2` làm quy tắc nguồn cho H/D full TRAIN:
chỉ bốn Qwen V4 ORIGINAL, đúng InternVL RECOVERY và MiniCPM FP32 INITIAL
label-only ở §3, giữ legacy fields UNKNOWN theo S3, inheritance/repair theo S2,
không pooling/best-run; chỉ kích hoạt sau L1–L4, comparability, O3–O6 và release
gates phù hợp — hay từ chối? Quyết định phải ghi ref, người/vai trò/thẩm quyền,
ngày/timezone, exact dossier version/SHA và điều kiện; mọi ô approval hiện
**PENDING**, không tự điền signer. Có thể quyết định **nguyên tắc nguồn có điều
kiện** từ hồ sơ này, chưa thể duyệt unconditional bridge/run khi còn thiếu seal.
Nếu từ chối, giữ negative decision, dừng và trình lại scope, không đổi nguồn.

Docs/metadata DONE FOR DRAFT REVIEW khác science/authority PASS. Dừng đúng
một Draft PR cho Issue #169 để ChatGPT review GitHub và quyết định audit Antigravity
độc lập trước merge được cấp riêng. Sau decisions/chứng từ đầy đủ mới giao
task native fulltrain/history bridge/final-source preflight riêng; không mở
task đó hoặc chạy Kaggle trong hồ sơ này.

## Owner successor scope — full TRAIN 3.763, 02/11/2026

Theo [Issue #167](https://github.com/tantdna2/SafeShift/issues/167) và [quyết định mới](DECISIONS.md#dec-20261102-owner-thesis-fulltrain-repair), mỗi mô hình cuối cùng phải được đánh giá trên **cùng đủ 3.763 TRAIN IDs**, có cơ chế xử lý INVALID/error/pending, phấn đấu nhãn hợp lệ thật. **T4-O2-SELECTION-v1 dưới đây là hồ sơ PROPOSED về lựa chọn nguồn gốc đã lưu và TRAIN160**, không phải phê duyệt triển khai full TRAIN, không cho quyền ghép/rerun series, không chứng minh phương pháp đã hiệu quả trên toàn TRAIN. Giữ các số và lineage lịch sử nguyên vẹn. Cần quyết định successor về lựa chọn series/repair và O2/O3/O4/O5/O6 trước thí nghiệm; MiniCPM vẫn label-only và HNLO=0/155.

Ngày 01/11/2026, Asia/Bangkok. **T4-O2-SELECTION-v1: PROPOSED; kích hoạt phân
tích BLOCKED; O2 chưa được phê duyệt.** BASE/main kiểm trực tiếp GitHub:
`f10bac7dea054c8e199a807dadd768517579e164`. Đây là task/nhánh T4 mới sau T3.
[Owner START T4](https://github.com/tantdna2/SafeShift/pull/161#issuecomment-6554558701)
chỉ cấp quyền lập hồ sơ và kiểm metadata, không cấp quyền phân tích dự đoán thật.

## 1. Một quyết định được khuyến nghị

**Khóa chính xác bốn shard Qwen3 V4 ORIGINAL và đúng một official attempt của
mỗi peer nêu ở §3 trước mọi phân tích hiệu quả ghép đôi tiếp theo; giữ nguyên
planned membership, lỗi, INVALID và kết quả thiếu. Không tự thay thế hoặc hợp
nhất các lần chạy.** Đây là lựa chọn hồi cứu trên TRAIN đã phơi nhiễm, không
được mô tả như preregistration trước khi từng xem bất kỳ kết quả nào.

InternVL official được đề nghị là **RECOVERY** đã định danh, không phải INITIAL.
Khuyến nghị O2 phải chấp nhận rõ **riêng attempt này**, với lineage còn nguyên,
chứ không mở quyền dùng mọi recovery hoặc completion union. Lý do đề nghị là
danh tính official TRAIN160 đã được T0/T1 ghi nhận, không phải 135 SUCCESS,
thời gian chạy, Accuracy/AUROC hay lợi ích dự kiến. MiniCPM là official FP32
INITIAL; bốn shard Qwen là các phần planned của cùng V4 gốc, không ghép reruns.

Nếu không chứng minh được identity/custody hoặc người có thẩm quyền từ chối:
giữ vai trò tương ứng **BLOCKED**, bảo toàn evidence âm; không lấy nguồn khác
lấp chỗ trống. Qwen không đạt thì dừng panel; peer không đạt thì trình quyết
định O3 về phạm vi, không tự loại peer, thay model hoặc tìm model thứ tư.

## 2. Mức bằng chứng và nguồn

| Ký hiệu | Ý nghĩa trong hồ sơ này |
| --- | --- |
| VERIFIED_T4 | Bytes/hash hoặc trường metadata thực sự được kiểm trong T4; không đồng nghĩa nội dung raw đã được audit lại. |
| INHERITED | Kết luận kiểm archive/report/replay của T0/T1/source receipt hoặc review trước, giữ nguyên giới hạn. |
| REPORTED | Nội dung handoff/attestation được đọc; hash handoff chỉ nhận dạng văn bản, không chứng minh mọi claim bên trong. |
| UNKNOWN | Không có bằng chứng đủ trong nguồn đã kiểm; `null` không phải zero, N/A hoặc giá trị được suy ra. |
| PROPOSED / APPROVED | Trạng thái quyết định tách khỏi bằng chứng. APPROVED phải có quyết định thật, đúng người/phạm vi/version; hiện selection chưa có. |

Nguồn chính: [T0 evidence §§3–4](T0_FALSE_SAFE_EVIDENCE_20261101.md),
[T0 projection](evidence/t0_false_safe_20261101/summary.json),
[T1 receipt](evidence/t1_feasibility_20261101.json),
[source receipt](../SOURCE_FEASIBILITY_RECEIPT_20261024.json),
[recovery decision](CANDIDATE160_RECOVERY_DECISION_20261031.md),
[FP32 adoption](DECISIONS.md#dec-20261031-owner-minicpm-fp32-official-train160).
[Receipt T4](evidence/t4_o2_metadata_20261101.json) chứa các giá trị đầy đủ,
nguồn và kết quả kiểm, không chứa vector ID ảnh/predictions. Các receipt T0/T1
và source receipt khớp bytes BASE; hai receipt private khớp hash T0/T1.

Các source/revision/implementation trong bảng là danh tính đã ghi, không có
việc tải lại weights hoặc kiểm source thực thi VLM tại T4. Các snapshot
`NOT_MERGED`/`NOT_RUN` trong receipt/adoption cũ giữ nguyên; sự kiện sau đó ở
[review hậu merge #157](https://github.com/tantdna2/SafeShift/pull/157#issuecomment-6546464187)
là bằng chứng kế thừa qua T0, không audit mới hay approval O2.

## 3. Ma trận ứng viên và danh sách lựa chọn đề xuất

| Vai trò / model / revision | Artifact chính xác đề nghị | Coverage giữ nguyên | Bằng chứng và thiếu sót |
| --- | --- | --- | --- |
| Focal: `Qwen/Qwen3-VL-8B-Instruct` @ `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` | Bốn archive V4 ORIGINAL tại §3.1, member `evidence/report/samples.csv`, đúng run/attempt của từng shard | 3.763 planned = 3.539 SUCCESS + 1 TECHNICAL_ERROR + 223 NOT_ATTEMPTED | VERIFIED_T4 đối chiếu source/T0 receipt, authority và hash manifest lịch sử; archive/member binding INHERITED. Series ID UNKNOWN; không suy `a1` là series. |
| Peer: `OpenGVLab/InternVL3_5-4B-HF` @ `6bd4487402110ef9889ba50eb7aefeb302526fed` | `internvl35-8e1c745ca0864e07b17af13e37b8b909.zip`, đúng RECOVERY attempt ở §3.2 | 160 planned = 135 SUCCESS + 25 INVALID; 0 TECHNICAL_ERROR/NOT_ATTEMPTED; 135 numeric HNLO theo receipt, không dùng peer score làm feature | Receipt bytes/identity VERIFIED_T4; lineage/replay INHERITED, source/config REPORTED handoff. Không phải InternVL3-2B Seminar. Hash member báo cáo riêng UNKNOWN. |
| Peer label-only: `openbmb/MiniCPM-V-4` @ `6f69a8235885be89608f3a71ffd40695b379e1e7` | `minicpm4-0074f8bb22c4466ea33e0c5619ffc576.zip`, đúng official FP32 INITIAL ở §3.2 | 160 planned = 155 SUCCESS + 5 INVALID; 0 TECHNICAL_ERROR/NOT_ATTEMPTED; **0 numeric HNLO**, 160 unaligned/null | Receipt bytes/identity/source hash VERIFIED_T4; adoption đúng implementation đã có, raw/replay INHERITED. Hash member báo cáo riêng UNKNOWN. |

### 3.1. Qwen3 V4 — bốn nguồn bất biến

| Shard | Run ID | Attempt ID | Archive TAR SHA256 | Planned / SUCCESS / TECHNICAL_ERROR / NOT_ATTEMPTED |
| --- | --- | --- | --- | --- |
| 0 | `hnlo-train-v4-qwen3-s0-a1` | `hnlo-train-v4-qwen3-s0-20261019-a1` | `bcaaa0b09dd664a39d0a1059d442e6eac2ed7352634e18dc0525926bb25e0dcc` | 941 / 941 / 0 / 0 |
| 1 | `hnlo-train-v4-qwen3-s1-a1` | `hnlo-train-v4-qwen3-s1-20261019-a1` | `af4e05c3d8b63e552166a8f7eb671ae3ec4836fef32ec4e534b0563cc13017c2` | 941 / 941 / 0 / 0 |
| 2 | `hnlo-train-v4-qwen3-s2-a1` | `hnlo-train-v4-qwen3-s2-20261019-a1` | `2dc356fcba9fe2ce5dfc4e3dc9a45286fe5382f574c02d38d7517580e38cd920` | 941 / 717 / 1 / 223 |
| 3 | `hnlo-train-v4-qwen3-s3-a1` | `hnlo-train-v4-qwen3-s3-20261019-a1` | `07abe1551e51b9194dcd1a32b79a93940a435a6567b61275d887c6d0878a5273` | 940 / 940 / 0 / 0 |

S0/S1/S3 được định vị qua các receipt `qwen3_shard0.json`,
`qwen3_shard1.json`, `qwen3_shard3.json` của nguồn T0 §3. S2 là
`Qwen3-Shard2-V4.zip`, outer ZIP SHA256
`e77199b0818c45e2a15be2815485493fa4a78d064f82288d497fd8d82ecd4f0d`;
hash TAR trong bảng khác hash ZIP. Không dùng S2 diagnostic.

Implementation commit `a6e08ce96ff8e3bb2256401ab8ecc230c36b2543`, source
payload SHA256 `7817f4311a6aabad6c1ce6be15b35b2cfe0dcede1b3c428cfb5c896e3857d91a`.
Configuration được ràng buộc bởi
[`hnlo_train_authority.v4.json` tại lịch sử](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/configs/diagnostics/hnlo_train_authority.v4.json),
SHA256 bytes `b1b2bda93074a1f7b9c83df6a9e80934c11c5ce40e25f2702ff70cf1e95ef492`:
prompt SHA `816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3`,
max_new_tokens32, batch1, do_sample=false, seed=null, runtime PR112 hai T4/
CUDA12.8/Python3.12.13. Không gọi hash authority là hash effective config độc
lập; trường hash config độc lập và series ID vẫn UNKNOWN.

Receipt T4 `qwen_original_shards` khóa riêng planned TRAIN manifest hash,
archive manifest hash, report/result/binding member hashes. **Hai loại
manifest không cùng đối tượng**; không coi khác hash là mâu thuẫn. Bốn planned
manifest lấy đúng commit lịch sử `31a04e6f7175cca818c63b4de0153246b3f3ecdb`;
T4 chỉ hash bytes metadata, không đọc report hoặc nội dung archive.

### 3.2. Hai official TRAIN160

| Trường | InternVL3.5 | MiniCPM-V-4 |
| --- | --- | --- |
| Run | `owner_internvl35_55badcf1d55d44d98b74324c58b552bf` | `owner_minicpm4_f52026d3c3bf49dbab2e3a8e33402f36` |
| Attempt | `owner_internvl35_55badcf1d55d44d98b74324c58b552bf_a1` | `owner_minicpm4_f52026d3c3bf49dbab2e3a8e33402f36_a1` |
| Series | `65302bed5bfea25eb5b21169a53e59b789a852b2251bdb7378e03849802958c1` | `owner_minicpm4_f52026d3c3bf49dbab2e3a8e33402f36` |
| Kind | RECOVERY | INITIAL |
| Archive SHA256 | `e1f9c50cb162e6d14f0f5ca42927799e8d3595ccf6dab8d72d0ac90840ebbaf6` | `46a41359c3ab2978b9ee4ac010518e49a74141641d9334c29035bdc0c8eac877` |
| Receipt nguồn | `data/processed/official160-20261031/verification-result.json` | `data/processed/m160/verification.json` |
| Receipt SHA256 | `854a22f18de3741ae803c53504ce3a392f43c2a956758ea1656a5d9b04c62a8b` | `551d109a99ed8296312cc0619dd019687b0b090f34ec025cc4f83aeb6895eeca` |
| Source SHA256 | `09d94fd27a6a5260526c981a55854e8217536e0499824400ea9df5d213fb2d08` | `b1d6d8210b9b5b03c52b59cd339c75a4ec60f0dafb1fc0106623a9e25a2ec2a3` |
| Config SHA256 | `71dcd6b934fed7bae76ce6bb4cbeeefe2ad0c7e570889f9cf33bb5e9858d7206` | `5b85504ff24ff42d4d629dbf00feb0c484022cfef3a7d57b571eaae99d1c8b00` |

Hai manifest cùng SHA256
`f1ec6a202c3bba05d91cb3c507d5aa16d9aa3ded2418fa84bd62e77c05522995`,
160 unique TRAIN, quota Level01/02/03/04 = 48/24/8/80, không supplement.
Đây là metadata chung, không tự chứng minh từng report dùng đúng input.

MiniCPM implementation `minicpm4-resampler-attention-fp32-v1`, descriptor SHA256
`2fe992725df4340f910934b5846278e34968196a9dff3fc4171fb4279bfaf5da` đã được
Owner nhận cho official TRAIN160: weights FP16/eager; chỉ attention score/
softmax/value product trong resampler FP32 rồi trả dtype gốc. Không gọi toàn
model FP32; 1.760 finite steps không tạo numeric HNLO. Adoption không duyệt O2.

InternVL: HF native, ID implementation tách riêng **UNKNOWN** trong receipt
được kiểm; không đặt một ID mới giả như lịch sử. Source/config ở handoff khớp
[production engineering](CANDIDATE160_PRODUCTION_ENGINEERING_20261031.md).
Receipt báo hai historical runs
`owner_internvl35_72007bc672f5406ebfbadc7e4848c24d` và
`owner_internvl35_a8b5bf157d2a4f5fa2c0fb27a62a9f16`, history/markers verified.
Đây là danh sách lịch sử, **không đủ để tự suy ordered ancestor graph hoặc
hash từng ancestor**. MiniCPM receipt có historical_runs rỗng trong official
scope, không có nghĩa không tồn tại technical/FP16 histories.

### 3.3. Giữ riêng, không đưa vào phân tích đề nghị

| Nguồn | Xử lý |
| --- | --- |
| Qwen S2 diagnostic; Recovery224 (`hnlo-qwen3-s2-recovery224-v1-20261022`); V4+recovery composites; pilot cũ | EXCLUDED khỏi lựa chọn này, giữ evidence; không thay 1 lỗi/223 chưa chạy hoặc 12 chưa chạy trong panel. |
| InternVL hai historical runs, technical smoke/qualification, các resume khác và FULL_RERUN | EXCLUDED khỏi nguồn predictions của panel; ancestor evidence vẫn bắt buộc. Chỉ attempt RECOVERY cụ thể ở §3.2 được đề nghị, không union. |
| MiniCPM FP16 cũ, technical FP32 smoke, profile engineering3, recovery/no-op kiểm kỹ thuật, FULL_RERUN hoặc attempt khác | EXCLUDED; không dùng smoke thay official, không coi no-op là bộ predictions mới. |
| InternVL3-2B Seminar và các model ngoài panel | Không thuộc quyết định này; không sửa roster Seminar/M1/M2 hoặc tự chốt final roster Khóa luận. |

## 4. Selection ledger và các trường chưa đủ

Đây là **contract đề xuất**, không authorization JSON vận hành. Receipt T4
điền được evidence đã biết; mọi approval/signature/time vẫn `null`/PENDING.
Mỗi giá trị phải kèm `evidence_state`, `source_ref`, `source_sha256`, phép kiểm
và giới hạn; trạng thái quyết định không được suy từ status PASS kỹ thuật.

| Nhóm trường bắt buộc | Nội dung / trạng thái hiện có |
| --- | --- |
| Decision | selection_id/version; rule nguyên văn §1; proposed_at; decision_status; inclusion/exclusion reason từng source. `T4-O2-SELECTION-v1`, PROPOSED. |
| Model identity | role/model/revision; implementation ID/source commit/payload hash; config/descriptor/prompt/parser/HNLO/env references và hash theo convention đã ghi. Không lấp field còn UNKNOWN bằng tên model. |
| Cohort | split/exposure; manifest ref/SHA256/ordered membership; planned count; **private** opaque mapping tới ID/image hash; mapping seal và custody. Không commit ID/hash từng ảnh hoặc GT. |
| Execution | run/series/attempt/kind; ancestors và hash snapshot/history; phần nào cung cấp predictions, phần nào chỉ là custody. Không chọn completion union. |
| Artifact | archive/report/member/receipt refs và SHA256 **bytes**, size nếu có; kiểm CRC/member/hash kế thừa hay kiểm mới; không nhầm archive hash với report hash. |
| Accounting | planned, SUCCESS, INVALID, TECHNICAL_ERROR, NOT_ATTEMPTED, MISSING/unresolved, score availability; lỗi giữ nguyên, thiếu chứng từ không tự đổi thành NOT_ATTEMPTED. |
| Access/custody | custodian, quyền đối với đúng artifacts và task, người đã xem/đã phân tích, thời điểm, giới hạn export/retention. Scope hiện tại metadata-only; quyền phân tích mới chưa có. |
| Authority | signer/name, role và căn cứ thẩm quyền, approval ref/time/timezone, exact ledger hash/version, approved scope/exceptions, rejected/withdrawn reason. **Tất cả approval O2 hiện UNKNOWN/PENDING**, không điền tên Owner vào ô đã ký. |

Những chứng từ sau cần có trước kích hoạt; Owner/custodian cung cấp projection
metadata của evidence đã có, không yêu cầu tạo lại inference hoặc gửi raw:

| Mã | Thiếu gì / ai có quyền cung cấp | Điều kiện khép |
| --- | --- | --- |
| L1 | O2 selection decision — Owner trong quyền dự án; Research Lead/người duyệt khoa học; giảng viên nếu dùng cho chuẩn học vụ | Quyết định có ref/thời điểm/phạm vi/version/hash và chấp nhận rõ InternVL RECOVERY. Owner task T4 không là chữ ký này; không giả vai trò độc lập. |
| L2 | Qwen legacy series/config representation — custodian outputs và người duyệt selection | Metadata source/attempt ở §3.1 đã có; cần xác nhận field series có tồn tại hay không, mapping legacy được duyệt và authority/config binding. Hiện UNKNOWN/BLOCKED cho ledger đủ trường; không tạo series ID để thỏa T3. Hash effective config độc lập chỉ dùng nếu thực sự tồn tại, nếu không cần chấp nhận representation legacy tường minh. |
| L3 | Hai peer report-member/config/implementation binding và InternVL ancestor seal — custodian official outputs | Projection gắn exact archive→report member SHA→run/attempt/config/source/manifest; InternVL graph/ancestor hashes, evidence không lấy predictions từ technical/failed histories. Report SHA và ancestor hashes hiện UNKNOWN, không bịa expected hash. Expected outer archive/receipt hashes đã khóa tại §3.2. |
| L4 | Paired ledger/access receipt — custodian dữ liệu và người giao task phân tích TRAIN | Đúng manifest160 SHA nêu trên, identity từng source, mapping/checks §5 và quyền task cụ thể; hash paired ledger hiện UNKNOWN. Không yêu cầu thêm dataset hay cấp quyền TEST. |

Không ghi đè ledger sau quyết định: amendment mới phải trỏ version cũ, lý do,
exposure đã có và người duyệt. Ngoại lệ khác phải được quyết định trước khi
áp dụng; không chọn latest, nhiều SUCCESS hơn, metric tốt hơn hoặc bảng đẹp hơn.

## 5. Khả thi ghép ba model và điều kiện task TRAIN tương lai

TRAIN160 đã dùng cho chọn mẫu/engineering/xem outputs: **H**, chỉ D thăm dò
có điều kiện; không V/T độc lập. T0 kế thừa Qwen trên đúng160: **148 SUCCESS,
12 NOT_ATTEMPTED, 67 Normal, 4 false-safe (1 severe)**. Không dùng toàn35
false-safe V4 làm số lỗi có predictions hai peer; chưa chứng minh cả4 có đủ
nhãn peer hợp lệ. Không bỏ12 khỏi planned workload. Lỗi riêng của peers hay
số peer cảnh báo không chứng minh họ phát hiện lỗi Qwen.

Trước một task phân tích TRAIN riêng: (1) đóng L1–L4 và khóa ledger; (2) kiểm
exact join planned160/opaque ID/image hash, không duplicate/extras, report
membership/status và model/revision/config/attempt nhất quán; (3) đối chiếu
GT/split theo quyền, giữ GT unresolved và mọi failure, không dùng GT chọn
run/feature/tie; (4) báo số paired valid/missing và HNLO eligibility đúng nguồn,
MiniCPM label-only; (5) ghi exposure, quyền reader và parser/HNLO qualification,
checksum custody. T4 không thực hiện join predictions này.

Chỉ sau task/approval phù hợp mới kiểm queue/gain; cùng planned workload,
focal outputs và error denominator cho các arms. Common complete-case chỉ là
bảng phụ, không thay bảng workload160. T3 hiện chỉ nhận fixtures tổng hợp;
O2 approval không tự bật [adapter thật](../TRIAGE_ADAPTER.md#điều-kiện-trước-tiếp-nhận-saved-reports-thật-trong-tương-lai).
Không CI/power/source independence claim từ160 hay4 sự kiện. O4/B1–B4 về
nguồn/quyền/custody/GT V/T; B5 về O2/O5 và B6 về model/run qualification
vẫn theo [T1 §§2–5](THESIS_DATA_PROTOCOL.md).

## 6. GO / BLOCKED / NO-GO

| Phạm vi | Verdict hiện tại | Bằng chứng và cách xử lý |
| --- | --- | --- |
| Hoàn thành hồ sơ để Owner quyết định | **GO** | Có danh sách exact sources và kết quả kiểm metadata §7, thiếu gì được ghi rõ; không cần xây thêm engine. |
| Qwen original focal vào phân tích mới | **BLOCKED** | Archive/run/attempt/manifest đã định danh; L1/L2/L4 chưa khép. Không dùng recovery thay thế. |
| InternVL official RECOVERY peer | **BLOCKED** | Receipt đúng hash/135+25; còn L1 chấp nhận cụ thể RECOVERY, L3/L4. Từ chối attempt thì giữ evidence và trình O3, không chọn run khác. |
| MiniCPM FP32 official label-only peer | **BLOCKED** | Adoption đúng identity/155+5 có; selection không được adoption phê duyệt. Còn L1/L3/L4. Không lấy smoke hoặc phiên bản khác. |
| MiniCPM numeric HNLO arm với artifacts này | **NO-GO** | 0 HNLO số; không tự tạo, suy từ finite logits hoặc đổi parser/token. |
| Auto-pool/replacement/best/latest/SUCCESS-only; TRAIN gọi là TEST hoặc independent target | **NO-GO** | Trái scope/selection rule, exposure và recovery decision. Không chữa bằng đổi tên cohort. |
| Xác nhận hiệu quả trên V/T hoặc learned ranker | **BLOCKED, ngoài T4** | O2 phần còn lại/O3/O4/O5, B1–B6 chưa đủ; không tính cải thiện thật trong task này. |

GO phân tích chỉ có thể được đánh giá lại khi đóng evidence/authority đúng
phạm vi; **không phải GO mặc định sau merge hồ sơ**. NO-GO là cách dùng không
hợp lệ, không phải kết quả thực nghiệm thất bại; BLOCKED là thiếu chứng từ/quyền.

## 7. Kiểm tra đã chạy và tái lập

Windows AMD64, CPython3.11.9, standard library, seed=null. Local artifacts
ignored tại `data/processed/t4-o2-20261101/`; không raw/archive/images/predictions.

- **PASS 18**: chạy nguyên checker nhúng ở [T1 §6](THESIS_DATA_PROTOCOL.md#6-tái-lập-kiểm-tra-đã-chạy-và-giới-hạn), SHA256 source
  `4fecbcd2c3ab68861a9743b33e83c6cdc1e803969d4cf5f76ee02f901b3d0ea8`.
  Lưu thành `t1_check.py` tại thư mục local trên; chạy từ repo root:
  `python -B data/processed/t4-o2-20261101/t1_check.py --artifact-root . --output data/processed/t4-o2-20261101/t1_recheck.json`.
  Không overwrite output; dùng tên output mới nếu kiểm lại. Thiếu/hash sai
  phải dừng; không thay artifact để đạt PASS.
- **PASS 10** bổ sung: 3 receipt bytes so BASE; 4 đối chiếu shard unit/source/
  report-hash/counts giữa T0, source receipt, historical authority và hash
  historical planned manifest; 2 source/config literals trong handoff; 1
  MiniCPM source hash trong receipt. Danh sách và toàn giá trị ở receipt T4.
  Các phép này là metadata consistency, không raw audit hoặc metric recount.
- **SKIP**: full unit/native/GPU suite (chỉ tài liệu/receipt); archive rehash/
  raw replay/per-image saved-report recount (ngoài scope); TEST/ảnh/new data;
  paired performance/triage/ranker/CI/power. Không gọi Kaggle hoặc audit độc lập.

Tái lập10 checks bằng stdlib: so bytes ba paths trong `input_sha256` có tiền
tố `docs/` với `git show BASE:path`; đọc `original_qwen3_v4.shards` của source
receipt, so `unit` với Qwen unit trong historical authority, so archive/report
hash/counts với `saved_report_recount.shards` T0 và payload với authority grant;
hash bytes `git show HISTORY:data/manifests/pa3_full_train_shard{k}.v1.json`
so `unit.inference_sha256`. So hai literal source/config đã khóa với handoff
đã đo hash; so MiniCPM source với receipt. Không mở archive/report/GT để làm
các bước này. Hash handoff T4 là pin lần đọc này, không pin độc lập có từ T1.

**PASS kiểm tài liệu:** UTF-8, 14 local links, bảng/fences, privacy, các literal
identity/hash giữa dossier và receipt; DECISIONS append-only, PROJECT_STATE
giữ snapshot byte-for-byte, `git diff --check`. Phạm vi cuối ghi ở PR.
Kết quả T0/T1 trước đây không được cộng thành tests T4. GitHub network trong
sandbox ban đầu bị proxy chặn; Git branch bị chặn ghi index; cả hai đã thực
hiện được qua quyền công cụ. Không có metadata check FAIL trong lượt T4.
Checker tài liệu lần đầu nhận nhầm URL HTTPS thành drive path và dừng;
đã sửa ranh giới regex, không sửa dữ liệu để vượt kiểm tra.

## 8. Câu trả lời Owner cần đưa ra — một bước tiếp theo

**Owner có chấp thuận trong phạm vi dự án quy tắc T4-O2-SELECTION-v1: chỉ bốn
Qwen3 V4 ORIGINAL và hai official attempts ở §3 (bao gồm rõ InternVL RECOVERY
đã định danh, MiniCPM FP32 INITIAL label-only), giữ mọi failure/missing,
không pooling/thay thế, và chỉ cho phép xét task TRAIN thăm dò tiếp theo sau
khi L1–L4 được khép — hay từ chối phương án này?**

Bước tiếp theo duy nhất: **Owner/người duyệt có thẩm quyền ghi quyết định có
ref, phạm vi, version/hash và thời điểm cho câu hỏi trên sau ChatGPT review
Draft PR**. Chấp thuận có điều kiện không biến evidence UNKNOWN thành PASS;
không ký thay Research Lead/giảng viên hoặc chủ dữ liệu. Nếu từ chối, giữ
REJECTED/negative record và dừng, không tự chọn phương án thay thế.

Quyết định này chỉ là thành phần selection của O2, không đóng toàn O2 hoặc
duyệt công thức/ranking/budget; O3 final roster/qualification, O4 quyền nguồn/
V/T, O5 thresholds/precision/stopping, quyền học vụ và task đọc predictions
vẫn riêng. Không đổi M1/M2/dataset/split/nhãn/metric/HNLO; không khóa review20%,
gain10 điểm, CI95% hay power80%. Dừng ở một Draft PR, không merge/Antigravity.
