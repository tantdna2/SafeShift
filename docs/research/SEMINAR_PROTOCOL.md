# SafeShift — Giao thức phân tích Seminar hồi cứu v1

Ngày: **26/10/2026 (Asia/Bangkok)**. Base: `a425ab04695319a42bfdd2f89192717dddbb891b`.
Protocol ID `safeshift-seminar-retrospective-v1`; cấu hình duy nhất:
[seminar_analysis_config.v1.json](seminar_analysis_config.v1.json).

**DOCUMENTATION_DONE / SCIENTIFIC_REVIEW_PENDING; frozen=false.** Đây là hợp
đồng mới được soạn theo [DEC-20261026-M1](DECISIONS.md#dec-20261026-m1--phạm-vi-seminarkhóa-luận-do-owner-quyết-định).
Các công thức mới dưới đây là đặc tả để review, chưa tự thành metric approved.
Sau review độc lập, Owner phải ghi quyết định append-only cho đúng SHA-256 bytes
của protocol/config, N/A và giới hạn; không sửa log cũ. Config chứa hash protocol,
receipt M3/M4 chứa hash của cả hai, tránh hash tự tham chiếu. M3 chưa được mở.

## 1. Câu hỏi, estimand và phạm vi

- **S-RQ1:** Nhãn sinh ra và HNLO biểu hiện khác nhau thế nào về phân loại/xếp
  hạng nguy cơ qua năm miền trên cùng ảnh? Đầu ra R2, coverage R1.
- **S-RQ2:** Lỗi nghiêm trọng tập trung ở đâu và kết luận nhạy thế nào với mẫu
  thiếu, ảnh trùng, giả định nhóm? Đầu ra R3; hazard strata hiện BLOCKED B01.
- **S-RQ3:** Bất đồng liên mô hình/HNLO liên hệ với lỗi, đặc biệt false-safe,
  hay chỉ phản ánh thiên lệch chung? Đầu ra R4; không học ensemble/triage tại đây.

Đơn vị là **ảnh TRAIN đã phơi nhiễm**. Estimand chính là mô tả gộp từng ảnh trên
cohort cố định; bảng từng miền dùng cùng quy tắc. Không diễn giải thành đánh giá
độc lập, ưu thế thống kê, causal validity, calibration hoặc an toàn vận hành.
Không inference, raw replay, đọc ảnh/annotation/TEST, sửa nhãn/split hay tuning
ngưỡng. R5 do người phân tích viết từ R1–R4 ở M4; phần mềm M3 chỉ xuất khung trace.

## 2. Nguồn và mức bằng chứng

| Ref | Nguồn pin / vai trò được dùng |
| --- | --- |
| E01 | [D9R22 JSON lịch sử](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/configs/pre_freeze/d9r22_seminar_scope.v1.json): nhãn, roster, D3, 12 atoms/7 nhóm, họ metric; chưa có công thức chi tiết. |
| E02 | [Receipt #131](../SOURCE_FEASIBILITY_RECEIPT_20261024.json): hashes, V4 units/status/config chain, saved-score AUROC, grouping, giới hạn audit. Config khóa SHA-256 file này. |
| E03 | [Gate #131](../SOURCE_FEASIBILITY_GATE_20261024.md): provenance/grouping/không có source registry; [CLI tại base](../../scripts/analyze_source_sensitivity.py) và [weighted AUROC](../../safeshift/evaluation/sensitivity.py) là hợp đồng kỹ thuật hiện hữu, không approval khoa học. |
| E04 | [Q25 summary lịch sử](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_r2_cpu_completion_20261015.summary.json) và [note](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_r2_cpu_completion_20261015.md): revision, 4 runs, raw CPU Linux PASS và giới hạn. |
| E05 | [V4 authority lịch sử](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/configs/diagnostics/hnlo_train_authority.v4.json): unit/revision/prompt/scope; **không chuyển grant sang main mới**. |
| E06 | [Verification 23/10](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/evidence/three_model_20261023/verification_20261023.json): report/sidecar hashes; S2 diagnostic cũ đã được E02 bổ sung gốc ngày 25/10. |
| E07 | [Kết quả/giới hạn](../RESULTS_AND_LIMITATIONS.md), [Direction §5](SEMINAR_THESIS_DIRECTION_LOCK_20261025.md#5-phạm-vi-seminar-đã-chọn), [Execution C01–C10](../EXECUTION_PLAN.md#4-các-invariant-và-bằng-chứng-nghiệm-thu-bắt-buộc): số kế thừa, yêu cầu đầu ra. |

Phân loại từng dòng/bảng: `INHERITED_REPORTED`, `INHERITED_RAW_CPU_AUDIT`,
`VERIFIED_SAVED_SCORE`, `NEW_SAVED_REPORT_REANALYSIS`, `SYNTHETIC`, `N/A` hoặc
`BLOCKED`. Không tự tăng evidence level khi hash/CSV khớp. Task M1/M2 chỉ đọc
tài liệu/code/receipt Git, **không kiểm tra lại payload thật**; expected counts
và AUROC trong config là số đối soát kế thừa, không phải kết quả task này.

### 2.1. Model/revision/run/attempt

| Model / release | Revision và identity bắt buộc | Mức bằng chứng/khác biệt cần giữ |
| --- | --- | --- |
| Qwen2.5-VL-3B-Instruct / PA3-R2 | `66285546d2b821cf421d4f5eb2576359d3770cd3`; runs `pa3-qwen-r2-train-shard-0`…`-3`, counts 941/941/941/940; execution source `c1527713ca7175b3d71248d51f1715693795e6e8`; report hash E04 | Raw audit CPU Linux **lịch sử** PASS; shard 1 outer download receipt thiếu, Windows 1-ULP mismatch giữ nguyên. Attempt IDs không có trong summary đã đọc: null, không suy từ run name. B03 chặn claim full attempt provenance, không tự chặn hash-bound saved-report analysis. |
| InternVL3-2B-hf / V4 | `cb57a075cb75a2e6d1b668b128d48bb00ae321d2`; run `hnlo-train-v4-internvl3-s{k}-a1`, attempt `hnlo-train-v4-internvl3-s{k}-20261019-a1`, k=0…3; 941/941/941/940 | Saved-report verification; không raw-logit PASS mới. E05 định danh unit; E02/E06 khóa ZIP và từng samples member. |
| Qwen3-VL-8B-Instruct / V4 gốc | `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`; run `hnlo-train-v4-qwen3-s{k}-a1`, attempt `hnlo-train-v4-qwen3-s{k}-20261019-a1`, k=0…3 | E02 khóa bốn archive/manifest/binding/result/CSV, source/authority/release/unit và historical ordered manifests. Run V4 **PARTIAL**; chỉ saved-score verification. |
| Qwen3 / Recovery224 | Run `hnlo-qwen3-s2-recovery224-v1-20261022`; archive/result/samples hashes E02 `qwen3_archive_bindings/recovery.json` | Cohort/config/release riêng. Không kế thừa V4 revision/attempt nếu không có chứng cứ; B03. Chỉ phụ lục kế thừa; config v1 không tái phân tích recovery khi chưa khóa đủ contract. |
| Moondream2 | `vikhyatk/moondream2`; revision/run/attempt tương thích TRAIN: null | N/A dự án theo A4. CPU token/interface tests không thay HNLO TRAIN; không gán planned/status=0 như run đã thực hiện. |

Q25: C1, FP16, no quantization, SDPA, T4×1, batch=1, greedy, 1 beam, max 32
tokens, native min/max pixels 200704/1003520, R2 pre-merger clamp (24/3.763 ảnh).
Prompt `prompts/p2_classification_c1_v1.txt`, SHA-256
`816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3` (E04 note).
V4 E05 có cùng prompt hash, greedy/max32/batch1, không clamp score/threshold;
Q3 runtime T4×2 explicit embedding CPU/Python3.12.13/CUDA12.8 và IVL3
T4×1/Python3.11.11/CUDA12.4. Chi tiết native wrapper/preprocessing/precision/
parser phải giữ bằng reference tới binding/source đúng hash, **không mặc định
giống Q25**. Những chi tiết chưa chứng minh riêng cho IVL3 nằm B03. M3 đọc
generated_label canonical đã lưu; không viết parser lại hoặc tái sinh nhãn.

### 2.2. Artifact allowlist và quyền

Config tách **reference allowlist** với `execution_permissions`: biết hash không
phải có quyền mở file. M1/M2 không có grant payload; M3 sau approval dùng fixtures
tổng hợp; M4 cần grant ghi người cấp/ngày/task/path/hash/member/source scope.
Không tự tải hoặc dò storage để tìm input. M4 thiếu input thì STOP bảng phụ thuộc.

Allowlist đã định danh: Q25 samples CSV, IVL3 ZIP (chỉ bốn tar được khóa và
`evidence/report/samples.csv`), duplicate metadata audit chỉ projection TRAIN,
Q3 S0/S1/S3 TAR+result sidecars và S2 **ZIP gốc**. E02 cùng E06 khóa hashes từng
member; S2 phải CRC, sidecars, outer TAR hash/size, manifest, binding, result và
ordered-ID/image-hash chain như `original_s2_zip`/`verify_v4_shard` ở E03. Không
đọc raw-logit/journal **payload**; `sample_journal` metadata trong result được
dùng kiểm status. Được kiểm inventory tên/hash, không mở imageData/TXT/ảnh.
TRAIN audit container có thể nhắc ID cross-split từ lịch sử: lọc `split=train`
và cạnh TRAIN–TRAIN, không tạo endpoint TEST hay mở file TEST. Nếu cấp quyền chỉ
cho projection, custodian phải cung cấp projection có hash/binding riêng;
chưa có thì BLOCKED, không giả projection hash bằng container hash.

S2 diagnostic SHA `508a2e122ee999da728e8d09c66f5157331e6fe1a40adaa82e2869a30c6e0147`
bị cấm làm gốc. Recovery, composite V4+Recovery, visual catalog cũ, report cũ
2.822 chỉ reference/phụ lục; không là input thay thế cho bảng chính. Không có
hazard map/logits summary mới trong allowlist này.

## 3. Cohort, ledger và record chuẩn hóa cho M3

| ID | Membership | N và support kế thừa |
| --- | --- | --- |
| T3763 | Exact TRAIN metadata IDs, Q25/IVL3 cùng ID–GT–folder_domain | 3.763; levels 490/251/8/3.014, A/N=749/3.014 |
| V3539 | **Chỉ SUCCESS của V4 gốc S0–S3**; join Q25/IVL3 đúng các ID đó | 3.539; levels 460/232/8/2.839, A/N=700/2.839 |
| M224 | T3763 trừ V3539, dùng phân tích coverage, không scored cohort | 224; levels 30/19/0/175, A/N=49/175 |
| REC224 | Cohort Recovery224 riêng (E02); có thể cùng ID M224 nhưng không cùng cấu hình | 224, A/N=49/175; phụ lục reference-only v1 |

T3763 theo miền A/N: coal_conveyor 172/650; metallurgy 9/534; oil_chemical
287/491; power 81/575; tunnel 200/764. V3539 per-domain support đọc từ chính
metadata exact join, đối chiếu E02 cohort `qwen3_original_v4_success_only`; không
chia theo tỷ lệ toàn TRAIN. D3 dùng folder_domain; không sửa mismatch gốc.
Sensitivity mismatch cũ chưa đủ contract trong input đã đọc: B05.

Tạo ledger trước mọi filter/metric: một dòng mỗi `(cohort,model,sample_id)`.
Không silently intersect. Dòng normalized có `sample_id, split, true_level,
folder_domain, model_id, revision, release, run_id, attempt_id, native_status,
attempted, persisted, parsed, generated_label, hnlo_score, input_ref,
evidence_level`. Label/score null có lý do riêng; không lấy nhãn từ ID.
Mọi metric ghi `cohort_id, membership_sha256, model/run refs, stratum, eligible_n,
planned_n, excluded_by_reason, positive_n, negative_n, numerator, denominator,
value, status, reason, evidence_level`. AUROC numerator là pair concordance;
không áp trường numerator tỷ lệ ảnh vào AUROC. Không xác định → JSON null kèm
reason, không NaN/Inf, 0 hoặc 0,5 thay thế.

Membership digest quy ước mới: SHA-256 của UTF-8 mỗi full sample ID đã sort theo
Unicode codepoint, một ID mỗi dòng LF, có LF cuối; cohort rỗng là hash bytes rỗng.
Tạo digest ở M4 từ input được phép, lưu count + hash; hiện **chưa có ID digest
được kiểm chứng**, config dùng rule, không bịa hash. Hash toàn file khóa membership
nguồn, không thay digest này. Cohort khóa thất bại là FAIL, không tính trên giao nhỏ.

### 3.1. Missingness có các trục riêng

- `SUCCESS`: native contract xác nhận output persisted/parsed/score tương ứng;
  expected Q25/IVL3 3.763 mỗi model; Q3 3.539. Flags sai contract → FAIL.
- `TECHNICAL_ERROR`: có attempted nhưng không có output dùng được; Q3=1.
  Không đưa vào confusion như INVALID, không lấy output recovery lấp vào.
- `NOT_ATTEMPTED`: chưa gọi; Q3=223. Attempt coverage Q3=(3.539+1)/3.763;
  successful coverage=3.539/3.763. Không đổi planned thành số được chạy.
- `INVALID`: output có nhưng không parse nhãn canonical. Giữ cột thứ năm của
  confusion, support/recall/accuracy gồm nó; không coi là Normal hoặc cảnh báo.
- `missing_score`: nhãn có thể hợp lệ nhưng score không có/hữu hạn; không nội
  suy, không làm mất nhãn trong classification. Nonfinite supplied score là lỗi
  dữ liệu phải reject, không đổi thành missing để tiếp tục. Score có/label INVALID
  chỉ dùng khi native contract chứng minh score độc lập parse; v1 input hiện
  hữu đòi SUCCESS canonical+finite, gặp trái expected thì STOP, không nới adapter.

Gọi P là planned set, O là output có thể chấm nhãn (gồm INVALID), L⊆O là nhãn
canonical, F⊆O là score đủ contract. Báo |O|/|P|, |L|/|P|, |F|/|P|, |INVALID|/|O|;
không có output thì INVALID rate null. Confusion dùng O, AUROC HNLO dùng F;
so HNLO với nhãn dùng **J=F∩L**, công bố exclusions theo lớp/miền, không so hai
AUROC khác ID. Ở input expected, O=L=F=T3763 cho Q25/IVL3 và V3539 cho Q3.
Moondream2 không có run tương thích: các coverage này N/A, không giả 0/3.763.

## 4. HNLO, đối chứng và phân loại (R2)

`a_i=1[y_i∈{Level01,Level02,Level03}]`; Normal=Level04. HNLO cao hơn nghĩa
hazard hơn: `s=logsumexp(z1,z2,z3)-z4` tại cùng prefix/decision step/token
alignment theo model. M3 dùng **pa3_score đã lưu**, không tính logits lại, không
trung bình raw s giữa model. Sigmoid(s) tương đương thứ hạng trong số học lý
tưởng, không là đối chứng độc lập hay xác suất nguy cơ đã hiệu chuẩn.

Trên O, `C[t,p]=Σ1[y=t,ŷ=p]` với t=4 levels, p=4 levels+INVALID;
`support_t=Σ_p C[t,p]`, `recall_t=C[t,t]/support_t`, `accuracy4=Σ_t C[t,t]/|O|`.
Macro recall là mean recall của lớp support>0, ghi danh sách lớp/số lớp; không
gán recall lớp vắng=0. O rỗng hoặc support=0 → null đúng ô. Đây không là accuracy
toàn planned khi có no-output.

Nhị phân: TP=A→A, FN=A→N, FP=N→A, TN=N→N; tách U_A/U_N là INVALID.
`FNR_observed=FN/(TP+FN+U_A)`, `FPR_observed=FP/(FP+TN+U_N)`;
`recall_A=TP/(TP+FN+U_A)`, `specificity=TN/(TN+FP+U_N)`;
`accuracy_binary=(TP+TN)/|O|`. FNR này chỉ **bỏ sót thành Normal**, INVALID
không tính FN nhưng vẫn trong support; vì vậy FNR+recall_A có thể <1. Báo
U_A/U_N cạnh mọi tỷ lệ; không gọi INVALID là phát hiện đúng. Denominator=0 → null.

Với score r, label dương b và trọng số w>0, định nghĩa dùng chung:

`AUC(b,r,w)=Σ_{i:b=1}Σ_{j:b=0} w_i w_j (1[r_i>r_j]+0.5·1[r_i=r_j]) /
((Σ_{b=1}w_i)(Σ_{b=0}w_j))`.

Tie là bằng giá trị số đã parse, không epsilon/jitter; số thực finite, không
round trước tính. Không có cả hai lớp → null `EMPTY`/`ONE_CLASS` kèm support.
Per-image w=1; không mean AUROC các shard hoặc các miền thay pooled AUC.

| Control/endpoint | Dữ liệu và công thức | Trạng thái hợp đồng v1 |
| --- | --- | --- |
| HNLO hazard AUC | b=a, r=s, trên F; paired comparisons trên J | Đã có phép tính kỹ thuật; sử dụng khoa học trong protocol này chờ review. |
| Hard-label AUC | b=a, r=1[ŷ≠Level04] trên J | Comparator cùng ID; 0/1 có ties, không threshold s. |
| Ordinal-label AUC | b=a, r=4−index(ŷ), index Level01=1…Level04=4, trên J | Công thức mới cần review; không sửa taxonomy. |
| Always-N / Always-A | Nhãn nhị phân hằng 0/1 trên O; accuracy/FNR/FPR nhị phân, AUC trên J | Hai control nhị phân, không bịa mức severity cho Always-A. Khi hai lớp có mặt AUC hằng=0,5 do ties. |
| Delta AUC | AUC(HNLO,J) trừ AUC(control,J) | Chỉ mô tả cùng ảnh/miền/trọng số; null nếu một vế null, không CI/p-value. |
| Entropy4, top-two margin, generated-label probability | Cần đủ bốn raw candidate logits, token/prefix, normalization/generation semantics | **N/A B02**, chưa chứng minh input/contract. Không suy từ scalar HNLO hoặc lời confidence; không code các control này. |
| AP/AUPRC, ECE/Brier/calibration, fit threshold | Chưa được chốt làm endpoint Seminar v1 | **NOT_IN_V1**; muốn thêm cần quyết định/capture contract mới trước code; không coi thiếu AP là AUC=AP. |

Không suy HNLO tốt hơn mọi confidence liên tục khi B02 còn thiếu; khác native
wrapper/precision/preprocessing là hạn chế comparability, không quy cho kiến trúc.

## 5. Lỗi nguy hiểm, miền và missingness (R3)

Tính cho mỗi model trên O của cohort đó, ALL và từng folder_domain:
`false_safe=Σ1[a=1,ŷ=Level04]`, chia số Anomaly trong O;
`severe_miss=Σ1[y=Level01,ŷ=Level04]`, chia support Level01 trong O.
Báo Level03 support, confusion row, số lỗi/INVALID riêng; support nhỏ không
tự loại. Các tử/mẫu số 0 đều báo count thật; tỷ lệ mẫu số 0 là null.

R3 luôn có panel Q25/IVL3 T3763 và ba model V3539. **Đếm lại false-safe Q3
V4-only từ ID gốc** ở M4; không dùng số 38 hay 14 từ composite. Missing Q3
phân bố lớp/miền theo M224; 49 A thiếu gồm 30 L01/19 L02/0 L03, 175 Normal.

Cận hoàn thành giả định đề xuất (chờ review): nếu toàn bộ SUCCESS V3539 có
nhãn canonical như expected, với FN=f và severe=g quan sát, FNR full completion
nằm `[f/749,(f+49)/749]`, severe `[g/490,(g+30)/490]`. Theo miền dùng số A/L01
thiếu của chính miền, không lấy 49/30 chung. Đây **không phải FNR đo trên full
TRAIN**, không gán nhãn/score cho missing. Nếu observed có INVALID/unresolved,
không áp cận này: BLOCKED `BOUND_REQUIRES_ALL_OBSERVED_LABELS_VALID`, báo
counts và xin amendment thay vì ngầm coi INVALID là an toàn.

Hazard 12 atoms/7 nhóm phụ: **BLOCKED B01**. Không có sample→atom map đủ
hash/provenance/coverage/taxonomy binding trong input đã đọc. Không tự liệt kê
tên atom từ suy đoán, tạo từ filename/VLM/nhãn mức hoặc đọc annotation mới.
Sau map được cấp và quyết định bổ sung trước code: mỗi atom lấy tập ID thuộc
atom, mẫu số support trong tập đó, dùng các công thức trên; nhóm A–G chỉ tóm
tắt phụ theo map đã duyệt. Chồng lấp không cộng thành tổng ảnh; unknown membership
không thành negative. v1 xuất placeholder BLOCKED cho cả 12/7 ô, không chạy
metric atom. N/A/giới hạn cụ thể này chưa được Owner chấp nhận từ A5 chung.

D3 mismatch sensitivity và proxy người/thiết bị/miền-platform là B05: folder
domain panel đã đủ; mapping mismatch/annotation/proxy controls chưa đủ contract
để code. Không lấy nhãn/Level trong ID làm feature hoặc gọi tương quan là causal.

## 6. Bất đồng và tín hiệu lỗi (R4)

Panel ba model chính: C=V3539, M={Q25,IVL3,Q3}; panel cặp phụ: C=T3763,
M={Q25,IVL3}. Không pool/so trực tiếp tín hiệu hai-model với ba-model như cùng
định nghĩa. `J_M={i∈C: mọi model có nhãn canonical}`. `joint_parse=|J_M|/|C|`;
báo thêm |J_M|/3.763 cho panel V3539 và counts tổ hợp missing/INVALID. Không
coi INVALID đồng thuận là agreement. Các endpoint dưới đây dùng J_M; báo riêng
Q3 eligible Level04 `B04={i∈J_M:ŷ_Q3=Level04}` để kiểm tín hiệu triage.

| Đại lượng | Định nghĩa thực thi / undefined |
| --- | --- |
| Unanimous ordinal/binary | Fraction ảnh mọi label bằng nhau / mọi 1[ŷ≠L04] bằng nhau; denominator n_joint=số ảnh J_M. Rỗng → null. Đồng thuận không là đúng. |
| Pairwise Cohen κ | Trên J_M (mọi cặp cùng cohort): bảng 4×4 labels, p_o=Σ diagonal/n; p_e=Σ_l p_m(l)p_k(l); κ=(p_o−p_e)/(1−p_e). Binary κ dùng hai nhãn. n=0 hoặc p_e=1 → null, ghi observed agreement cạnh κ. Không weighted κ mới. |
| Vote entropy H4/H2 | p_l=count vote_l/m_count; m_count=số model trong M; H=−Σ_{p>0}p ln(p)/ln(K), K=4 hoặc 2. K cố định, không ln(số nhãn được quan sát); unanimous=0. Không có đủ M → null. |
| Ordinal disagreement D | Mean trên cặp model của abs(index(ŷ_m)−index(ŷ_k))/3; index Level01=1…04=4. Cặp không thứ tự không đếm hai lần. Không majority/average prediction mới. |
| Lỗi mỗi model e4_m | 1[ŷ_m≠y] trên J_M; binary error eb_m=1[1[ŷ_m≠L04]≠a]. False-safe eFS_m=1[a=1,ŷ_m=L04]; severe riêng. Không lẫn a (hazard thật) với e (lỗi). |
| Shared blind spots | Counts Σ∏_m e4_m và Σ∏_m eFS_m; all-error rate chia n_joint, false-safe rate chia số Anomaly trong J_M; thêm unanimous-wrong4=Σ1[unanimous4]·∏e4_m / n_joint. Zero support → null đúng tỷ lệ. |
| Error complementarity | Ordered pair m→k: Σe4_m(1−e4_k)/Σe4_m; thêm counts cùng sai Σe4_m e4_k, chỉ m sai Σe4_m(1−e4_k), chỉ k sai Σe4_k(1−e4_m). Nếu m không lỗi tỷ lệ null. Không gọi đây là oracle ensemble đạt được. |

S-RQ3 error association dùng predictor cố định **Q3 V4 gốc** trên panel chính.
Đối với H4,H2,D: error-detection AUC có **positive=e4_Q3**, negative=1−e4_Q3,
score cao hơn = nhiều bất đồng hơn; báo thêm positive=eFS_Q3 với cùng định nghĩa
và cohort. Lặp trên B04; e4 và eFS trùng nhau trong B04, ghi equivalence, không
đếm thành hai bằng chứng. Báo số distinct scores/range và support errors/nonerrors
trong **chính B04**, không suy degeneracy từ panel chung. Toàn điểm bằng nhau
và có hai lớp → AUC 0,5; không có lỗi hoặc không có nonerror → null.

HNLO-Q3 kiểm error association trên **B04∩F_Q3**: positive=eFS_Q3, score=s_Q3
cao hơn ưu tiên kiểm tra. Trong tập predictor gọi Normal, đây cũng là hazard
ranking có điều kiện; không thay hazard AUC trên cả cohort cho error-detection
AUC. Báo bảng `(true binary × predicted binary)` support và phân bố HNLO
(min/median/max, median trung bình hai giá trị giữa khi n chẵn) trên J_M∩F_Q3.
Không chọn dấu s từ kết quả để tối đa AUC. **HNLO phát hiện mọi lỗi bốn mức trên
toàn J_M: NOT_IN_V1**, chưa có direction/transform được duyệt; không giả s cao
là uncertainty. So các tín hiệu trong B04 trên giao **cùng ID** đủ mọi tín hiệu.

Đường risk–coverage hồi cứu đề xuất cho u∈{H4,H2,D} trên J_M và
u∈{H4,H2,D,HNLO_Q3} trên B04∩F_Q3, cùng ID mỗi panel: giữ các ảnh u≤t,
với t lần lượt mọi giá trị u duy nhất tăng dần; ties giữ cả block, không phá
ties theo GT/ID. Thêm điểm k=0 với risk=null. `coverage=k/n_panel`,
`risk4=Σ_retained e4_Q3/k`, `residual_FS=Σ_retained eFS_Q3 / A_panel`
(A_panel=0 → null). Báo coverage của panel so planned riêng; k=n phải khớp lỗi
panel. Không chọn t tối ưu, không random tie-break, không AURC hay ngưỡng vận hành.
Nếu mọi u bằng nhau đường chỉ có 0 và 100%; đây là kết quả hợp lệ.

## 7. Ảnh trùng và source identity (R3 sensitivity)

Kế thừa 10 variants của E03: `image`, `exact`, `point`, `family`, `exact_point`,
`exact_point_family`, `exact_point_near8`, `exact_point_family_near8`,
`exact_representative_first`, `exact_representative_last`. v1 đề nghị áp dụng đủ
10 trên T3763 và V3539; 20 rows/scenario sets, không chọn theo gap. 40 variants
lịch sử gồm thêm cohort 2.822 và Recovery224 vẫn là snapshot PROPOSED_EXPLORATORY,
không cần khôi phục/re-run chúng để có M3 hoàn chỉnh.

Exact cạnh theo byte_sha256, đối soát pixel partition; point/family từ metadata
đã lưu, null/rỗng không nối nhau. Near8 chỉ cạnh có sẵn dHash integer≤8, TRAIN–TRAIN;
không tính hash ảnh mới. Union connected components có bắc cầu, dựng lại trên
membership mỗi cohort, không nối qua ID ngoài cohort. Weight w_i=1/|component|
trên toàn cohort; bảng miền **giữ weights gốc**, không renormalize. Hai variant
đại diện dùng full ID sort đầu/cuối trong exact component, w=1; không xem score
để chọn. Tất cả chỉ tính **hazard AUC** (HNLO và paired hard/ordinal controls),
support n ảnh và class weight masses; không mở rộng weighting sang κ/error curves.

Báo số component, singleton, largest, A-only/N-only/mixed, cross-domain,
severity conflicts, score/generated-label consistency từng exact group. T3763
kế thừa 44 exact groups size2, 88 ảnh; exact pixel/byte partition phải khớp. AUROC
nội nhóm đơn lớp null, không lấy mean những nhóm xác định thay global AUC.
Không gọi point/family/dHash là site/video/camera/session thật, không CI nguồn,
bootstrap ảnh, p-value, effective independent N hoặc causal claim. Visual catalog
cũ có 0/7 ID-pair khớp pair table đúng hash nên không được dùng làm registry.

## 8. Bảng Moondream2 và đầu ra R1–R5

Mọi nhóm bảng model-level giữ hàng Moondream2:

| Model | Planned/coverage định lượng | HNLO/classification/error/disagreement TRAIN | Lý do và thẩm quyền |
| --- | --- | --- | --- |
| Moondream2 | N/A — chưa có run tương thích được khóa | N/A, không ghi 0, không đưa vào joint three-model denominator | Thiếu raw-logit capture/decision alignment/state-preservation validation và TRAIN audit; ngoại lệ **dự án** A4, học vụ chưa xác minh. |

Config không có dự đoán/điểm mẫu thật. M3 CLI dự kiến nhận `--config` và
`--output-dir`; chạy từ root, output dưới `data/processed/seminar/<run_id>/`,
refuse overwrite. Đây là yêu cầu triển khai M3, **chưa phải lệnh chạy được**.

| Output | File bắt buộc trong output dir / schema nội dung |
| --- | --- |
| R1 | `R1_evidence_coverage.csv`: mỗi model/cohort/ALL+domain, planned/status/attempted/O/L/F/INVALID/missing, exclusions levels/domains, provenance/evidence. `cohort_membership.json` + ledger CSV local; bốn model, recovery reference-only riêng. |
| R2 | `R2_classification_ranking.json` + long CSV: 4×5 confusion, support/recall/accuracy4/macro recall, binary TP/FN/FP/TN/U, observed rates, AUC/control/delta cùng ID. T3763 Q25/IVL3 và V3539 cả ba, ALL+năm miền. |
| R3 | `R3_dangerous_errors_sensitivity.json` + long CSV: false-safe/severe/Level03/miền, missing composition, completion bounds, 10 variants×2 cohorts và N/A/BLOCKED hazard/mismatch panels. |
| R4 | `R4_disagreement_errors.json` + long CSV: hai panel M, support/joint parse/agreement/κ/entropy/D/shared/complementarity; Q3 error association, B04 degeneracy, đường risk–coverage tie blocks. Không Moondream2 giả. |
| R5 | `R5_trace_limits.md` và `summary.json`: ba mục trả lời S-RQ → row IDs/input refs R1–R4; M3 placeholder `PENDING_ANALYST_M4`, M4 người phân tích viết kết luận; N/A/BLOCKED/missing/exposure/source/control/academic limits bắt buộc. |

Long CSV dùng `(output_id,row_id,cohort_id,model_or_pair,stratum,metric_id,
signal_id,variant_id,numerator,denominator,value,status,reason,membership_sha256)`;
chi tiết cấu trúc/confusion/curve arrays ở JSON. Cell null → CSV rỗng + reason,
không chuỗi số giả. Mỗi output có protocol/config/source/input hashes qua
`receipt.json`; SHA-256 output tính sau ghi. Row ID xác định từ key tuple, không
dựa thứ tự input hay outcome. Báo hết strata vắng với status UNDEFINED/N/A/BLOCKED.

## 9. Nghiệm thu C01–C10

PASS của **đặc tả**, synthetic M3 và artifact M4 là ba mức khác nhau. Không ghi
PASS artifact từ đọc tài liệu. Các check sau là nghĩa vụ M3/M4 sau review:

| Check | PASS / điều kiện chặn / outputs |
| --- | --- |
| C01 | Unique IDs, canonical GT, exact ID–GT–domain join; TRAIN-only và T3763 counts/domain ở §3 đúng E02. Reject unknown/missing/extra IDs hoặc thay domain/label. R1–R4. |
| C02 | Q3 đủ bốn V4 units đúng revision/run/attempt/source/config/ordered manifests; S2 TAR SHA `2dc356fcba9fe2ce5dfc4e3dc9a45286fe5382f574c02d38d7517580e38cd920`, size 12031765, ZIP hash/CRC/sidecars khớp E02. Planned 3763=3539+1+223; status PARTIAL. Sai → chặn Q3/common, không dùng diagnostic. R1. |
| C03 | V3539 exact SUCCESS gốc: levels460/232/8/2839; M224=30/19/0/175; Recovery baseline_pooling_allowed=false. Synthetic thử cùng ID nhưng sai config/recovery phải reject. R1–R4. |
| C04 | HNLO đọc score finite/cao=hazard, đúng hash/run; không normalize/sigmoid thành calibrated risk hoặc average cross-model. Raw logit/token tests chỉ có trong task scorer được cấp riêng, N/A cho M3 saved-report. R2/R4. |
| C05 | AUC oracle pair enumeration khác rank implementation; tolerance tuyệt đối 1e-12. Expected full Q25/IVL3=0.8266558463706973/0.8861824613751756; common=0.8243818245861219/0.88286846475117/0.9527927338600111. Giữ evidence levels/Q25 outer receipt. Sai input/estimand → STOP, không đổi expected. R2/R3. |
| C06 | O/L/F/planned tách nhau; confusion giữ INVALID; no-output ledger riêng, không fill Normal/INVALID. Empty/one-class/nonfinite/tie/missing tests; báo mỗi eligibility/exclusion. R1–R4. |
| C07 | Oracle tay false-safe/severe từ đúng V4-only; không hardcode FN composite. Error-positive khác hazard-positive; B04/all-agree/all-invalid/zero-error/missing model/κ p_e=1/entropy ties/curve endpoints đúng §6. R3/R4. |
| C08 | Exact membership/hash/byte-pixel partitions, transitive groups, null group keys, domain weights đúng §7. Không visual catalog/source CI. Hazard/control/mismatch chỉ N/A/BLOCKED B01/B02/B05, **chưa acceptance khoa học**. R3/R5. |
| C09 | Bốn hàng model với Moondream2 N/A A4 trên mọi bảng áp dụng; joint M=3 ghi rõ không phải complete four-model. Không nâng ngoại lệ thành teacher approval. R1–R5. |
| C10 | Receipt source SHA, protocol/config/input/member/output hashes, env/versions/command/seed=null(deterministic)/authority ref; reject hash tamper, archive duplicate/member type sai, path escape/symlink escape/overwrite. JSON finite; synthetic ghi SYNTHETIC. Cùng input/config cho cùng numeric outputs; timestamps riêng receipt. R1–R5. |

Ví dụ tổng hợp để kiểm công thức, **không phải số SafeShift**: y=(L01,L04,L02,L04),
ŷ=(L04,L01,INVALID,L04). O=4,L=3, accuracy4=1/4, FN=1,FP=1,TN=1,TP=0,U_A=1;
FNR=1/2,FPR=1/2,recall_A=0/2,severe=1/1. Scores hazard=(2,1,1,0) cho AUC=3,5/4=0,875;
paired J loại INVALID chỉ cho comparator cùng ID. Ba votes (L04,L01,L04):
H2=−[(2/3)ln(2/3)+(1/3)ln(1/3)]/ln2, D=2/3. Hai model luôn L04: agreement=1,
κ=null vì p_e=1; không là reliability PASS. Tests M3 cần thêm oracle độc lập
cho grouping/bounds/risk-coverage và I/O, không chỉ lặp code triển khai.

## 10. Blocker, N/A và gate trước M3

| ID | Trạng thái thành phần / quyết định còn cần | Phạm vi bị chặn |
| --- | --- | --- |
| B01 | **BLOCKED**: thiếu map sample→12 atoms/7 nhóm được khóa. Reviewer/Owner chấp nhận N/A cụ thể/claim giảm, hoặc custodian cấp map + contract trong amendment trước code. | Chỉ hazard strata và kết luận đầy đủ theo hazard; miền/Level vẫn đặc tả đủ. |
| B02 | **N/A proposed** entropy4/margin/probability từ logits, proxy controls: input/semantics chưa chứng minh. Cần chấp nhận N/A cụ thể; không lấy entropy vote thay entropy logits. | Claim HNLO vượt continuous controls/đã kiểm soát confounding; không code control mới. |
| B03 | **UNVERIFIED_DETAIL** Q25 attempt IDs, một số IVL3 native contract details và recovery revision/attempt; không suy từ model khác. Chấp nhận giới hạn hash-bound saved-report, hoặc cung cấp contract đúng hash. | Full runtime/raw provenance claims; tái phân tích recovery vẫn reference-only. Không bắt buộc raw replay để chấm saved reports. |
| B04 | **PENDING** review độc lập và Owner duyệt đúng protocol/config hashes, mọi công thức mới, completion bounds và N/A/claim. | **M2 khoa học chưa PASS, toàn bộ code M3 chưa được giao**. Không tự biến documentation checks thành approval. |
| B05 | **BLOCKED** mismatch sensitivity D3/đối chứng người-thiết bị-platform thiếu mapping/hợp đồng field trong inputs đã kiểm. Cần chấp nhận giới hạn cụ thể hoặc amendment hợp đồng trước code. | Chỉ panels đó; folder_domain vẫn D3, không sửa mismatch hoặc taxonomy cũ. |
| B06 | **NOT_GRANTED** quyền payload M4/setup M3/raw/GPU/TEST và học vụ bên ngoài chưa xác minh; nguồn/nhãn/custodian/precision Khóa luận chưa có. | M3 cần task CPU riêng sau B04; M4 cần grant từng input; M6/M7 xác nhận và học vụ không tự PASS. |

Khi review chọn chấp nhận N/A, M3 phải xuất đúng placeholder và giới hạn ở R5,
không xem câu hỏi phụ thuộc đã trả lời. Nếu chọn thêm metric/control/map,
amend protocol/config trong **cùng PR này trước M3**, ghi source/authority thật;
không để implementer tự quyết. Không tạo task khảo sát/lập kế hoạch phụ.

**NEXT TASK sau M1 có hiệu lực + M2 khoa học PASS: M3-01 — triển khai trọn hệ
thống phân tích Seminar CPU**, reader/metric/CLI/config/tests/docs theo Execution
Plan, fixtures synthetic, không artifact thật. Task M1/M2 kết thúc ở một Draft PR;
review/phê duyệt còn pending được xử lý trên cùng gói review, không tự merge.
