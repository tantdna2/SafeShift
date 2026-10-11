# PA3 — Đề xuất kiểm tra tín hiệu phân biệt trong điểm nhãn chưa hiệu chỉnh

Ngày: 2026-10-11 (Asia/Bangkok). Trạng thái: **PROPOSED / PENDING**.
Nguồn được đọc tại `main`, BASE `6cebc709647e6988f6fa83692f8655c7f3ec9e54`.
Đây là đề xuất phương pháp để review, không phải protocol có hiệu lực, kết quả
thí nghiệm, thay thế RQ3 hay quyền thực thi. PA3 là tên phương án trong task này,
**không phải P3** (sensitivity protocol của D2), cũng không phải P2/P2.1.

## 1. Câu hỏi, bằng chứng và giả thuyết

Câu hỏi: với checkpoint frozen `Qwen/Qwen2.5-VL-3B-Instruct`, liệu điểm trực tiếp
của bốn nhãn có xếp ảnh Anomaly cao hơn ảnh Normal, dù nhãn sinh ra tập trung vào
Level03? “Nguy hiểm” ở đây chỉ là GT Anomaly = Level01/02/03 của benchmark;
Normal = Level04. Đây không phải xác nhận nguy hiểm thực tế ngoài annotation.

| Thông tin | Nguồn và phạm vi tin cậy |
| --- | --- |
| Qwen2.5 P2: 5.013 ảnh, 4.976 SUCCESS, 37 INVALID, không dự đoán Level04 | Bối cảnh kiểm toán hiện vật cục bộ đã xác minh do Research Lead cung cấp cho TASK 2; không tái mở archive trong PR này; chưa phải báo cáo chính thức từ evaluator của repo |
| InternVL3 P2.1 shard 0: 1.254 SUCCESS, không dự đoán Level04 | Cùng handoff; không suy ra kết quả toàn bộ InternVL3 hoặc gộp hai cohort |
| LS1 calibration chưa có lợi ích được chứng minh trên bằng chứng hạn chế; 10 ảnh TRAIN đã bị quan sát, GT trước đây chưa được authority xác minh | [Phân tích LS1](ls1_calibration_failure_analysis.md), DEC-LS1-002 trong [decision log](../DECISIONS.md) |
| Level03 có 15 ảnh trong audit toàn bộ 5.013 ảnh | [TASKS, W1 mục 4](../TASKS.md); không suy ra số ảnh hay số nhóm Level03 trong holdout mới |

H1 đề xuất: AUROC của điểm nguy hiểm chưa hiệu chỉnh trên cohort TRAIN-holdout
được duyệt, có điểm hợp lệ, lớn hơn 0,5 theo chiều đã định trước. H0: AUROC ≤ 0,5.
Không suy từ việc thiếu dự đoán Level04 rằng điểm Level04 không biến thiên.
Không suy H1 đúng từ calibration thất bại. Điểm đo ở đầu ra nhãn cũng không
đại diện cho mọi thông tin trong hidden states của mô hình.

Thiết kế này **được thúc đẩy sau khi đã quan sát kết quả**, gồm TEST. Không dùng
các kết quả đó để chọn công thức, đổi dấu điểm, prompt, threshold, calibration,
checkpoint, cách lọc mẫu hoặc phương án “thắng”. Không gọi TEST còn độc lập hoàn
toàn, không dùng TEST để chọn PA3 thay RQ3, và không đọc thêm TEST trong PA3.

## 2. Tính khả thi từ mã LS1 hiện có

Kết luận kiểm tra tĩnh: **có các primitive phù hợp; chưa có đường chạy PA3 trên
dữ liệu thật được phê duyệt, và chưa xác minh runtime Qwen LS1 ở task này**.

| Điều kiện | Đã thấy trực tiếp trong source tại BASE | Điều kiện còn phải chứng minh trước một thí nghiệm sau này |
| --- | --- | --- |
| Danh tính mô hình/tokenizer | [tokenizer.py](../safeshift/ls1/tokenizer.py), `MODELS`, `plan`, `verify_snapshot`: Qwen revision `66285546d2b821cf421d4f5eb2576359d3770cd3`, runtime plan và file hashes được pin | Snapshot đúng byte, đúng phiên bản thư viện; T1 Qwen thực tế PASS có artifact. Runbook ghi local T1 BLOCKED; không chuyển SKIP/BLOCKED thành PASS |
| Nhánh nhãn một token | `probe` kiểm tra 28 biến thể; [core.py](../safeshift/ls1/core.py), `candidates` thay nhãn trong toàn bộ response, yêu cầu cùng prefix/suffix, đúng một vị trí khác và bốn token ID khác nhau, decode round-trip | Phải kiểm tra lại từng response thực tế. Nhãn đầy đủ không nhất thiết là một token; chỉ vị trí phân nhánh phải là một token. Không hard-code token IDs, không dùng approximate sequence likelihood khi thất bại |
| Vị trí token thật | `locate_decision` đối chiếu continuation IDs, cho bỏ tối đa một EOS cuối; `score_decision` kiểm tra generated label token và full-vocabulary summaries | Sai alignment, token thiếu, escaped/ambiguous label hoặc multi-token branch là technical failure; không sửa response để cứu điểm |
| Raw/processed khác nhau | [runtime.py](../safeshift/ls1/runtime.py), `generate`, `capture_output` yêu cầu `output_logits=True`, `output_scores=True`; `validate_trace` kiểm tra mọi bước, generated token bằng processed global argmax | Chỉ **raw logits** đi vào điểm nghiên cứu. Phải lưu và giải thích raw/processed disagreement; không giả định raw argmax luôn bằng greedy label |
| Điều kiện suy luận | `NativeScorer`: C1 qua `render_prompt`, native chat/image processing, Qwen pixel bounds 200704–1003520, 256–1280 visual tokens, FP16, SDPA, `cuda:0`, batch 1, greedy, 32-token cap, fresh cache/rope | Kiểm chứng snapshot/runtime/preprocessing chính xác và synthetic qualification riêng sau phê duyệt. Không tự gọi GPU để kiểm chứng trong PR này |
| Tính toàn vẹn | [experiment.py](../safeshift/ls1/experiment.py), `run`, và [artifacts.py](../safeshift/ls1/artifacts.py): lưu raw, fsync/checksum, đọc lại trước parse/score; mỗi attempt là artifact mới | Cần giữ prompt/model/source/run/sample identity, raw text/IDs, per-step candidate raw/processed values, full-vocab summaries, score eligibility và failure receipts |
| Khóa thực thi | `authorize` chặn cả `train`/`test` bằng `LS1_SPLIT_EXECUTION_LOCKED_PENDING_DEC_LS1_001`; `dataset_samples` cũng luôn chặn. [kaggle.py](../safeshift/ls1/kaggle.py) gọi `authorize` | Receipt, checksum, biến môi trường hay quyền P2/P2.1 không mở LS1. Chỉ quyết định mới và implementation review riêng mới có thể tạo đường thực thi |

“Constrained scoring” ở đây là chuẩn hóa/xếp hạng **bốn ứng viên tại nhánh nhãn
của một response được sinh tự do và hợp lệ**. Source hiện tại không ép generation
chỉ sinh bốn nhãn, không ép canonical prefix cho mọi ảnh và không chấm mọi
INVALID. Prefix được sinh có thể khác nhau giữa ảnh; đây là một giới hạn của
phép đo, không phải score độc lập với formatting context.

`core.score_decision` và `distribution` đã tính điểm chưa hiệu chỉnh. Tuy nhiên
`experiment.run` luôn gọi `reference_scores` rồi `calibrate`; `evaluate.report`
duyệt cả `uncalibrated` lẫn `calibrated`. **Không có switch hiện hành để chạy
PA3 chỉ lấy điểm raw và bỏ các reference calls.** Phương án tương lai cần một
implementation PR riêng, được duyệt, chỉ dùng các primitive đã kiểm tra; không
gọi helper trực tiếp để vòng qua khóa. Không sửa những file đó trong PR này.

Không thể khôi phục bốn logits từ nhãn cuối, raw text hoặc histogram P2.
Chỉ có thể tái phân tích một artifact nếu audit chứng minh nó chứa đúng raw
candidate logits, IDs, step, prefix, cấu hình và provenance cần thiết, với quyền
tái sử dụng được duyệt. Task này không kiểm tra archive để khẳng định có các
trường đó. Nếu thiếu, phải có inference mới trong nghiên cứu riêng; không đưa
chi phí này vào RQ3 hiện tại vốn cấm thêm inference.

## 3. Endpoint chính: AUROC nguy hiểm so với bình thường

Với ảnh `x` có nhánh hợp lệ, đặt `z1,z2,z3,z4` là raw logits ứng với
Level01–Level04 tại cùng decision step; `LSE` là log-sum-exp tính ổn định:

```text
ell_k(x) = z_k(x) - LSE(z1(x), z2(x), z3(x), z4(x))
p_k(x)   = exp(ell_k(x))
s(x)     = LSE(z1(x), z2(x), z3(x)) - z4(x)
         = LSE(ell_1(x), ell_2(x), ell_3(x)) - ell_4(x)
y(x)     = 1 nếu GT ∈ {Level01, Level02, Level03}; 0 nếu GT = Level04
```

**Điểm càng lớn nghĩa là càng nghiêng về Anomaly.** `s` là log odds của tổng
khối lượng ba nhãn Anomaly so với Level04, đơn điệu theo `1-p4`. Dùng miền log
để tránh underflow/saturation của `1-p4`; không dùng riêng `z4`, vì offset
logits khác nhau giữa ảnh. Không chọn `max(z1,z2,z3)-z4` thay thế sau khi xem
kết quả. Không trừ bias, học temperature, đặt ngưỡng hay bật Level01 guard.
`p_k` chỉ có điều kiện trên bốn token và prefix, **không phải xác suất nguy hiểm
đã được hiệu chỉnh**.

Công thức trùng primitive `anomaly_log_odds` và `auc` trong
[evaluate.py](../safeshift/ls1/evaluate.py). Binary AUROC dùng được decision
scores không cần threshold, theo [tài liệu chính thức scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_auc_score.html)
(tham khảo định nghĩa, không thêm dependency hay thay evaluator).

Gọi `C` là cohort holdout đã khóa trước inference, `N=|C|`; `E` là những ảnh
trong `C` có GT chuẩn, response LS1 parse-valid và raw score hữu hạn, đủ mọi
technical checks. `n=|E|`, `n+`, `n-` là số Anomaly/Normal trong `E`:

```text
AUROC_E = sum_{a∈E,y(a)=1; b∈E,y(b)=0}
          [1{s(a)>s(b)} + 0.5*1{s(a)=s(b)}] / (n+ * n-)
```

Mỗi ảnh có trọng số như nhau; ties được 0,5 (average ranks), không jitter hoặc
làm tròn để phá ties. Không dùng ordinal predicted label hay confidence bằng
lời làm endpoint. `n+=0` hoặc `n-=0` ⇒ `NA` kèm lý do, không 0/0,5. Một điểm
hằng trên cohort đủ hai lớp có AUROC đúng 0,5. Không đảo dấu khi AUROC < 0,5.

### INVALID, missing và mẫu số

- Báo cáo flow `N planned → attempted → raw persisted → parse-valid → scored`,
  với `N`, `n`, `N-n`, `n+`, `n-`, pair denominator `n+*n-`, số nhóm và GT counts.
  Phân tách format INVALID, tokenizer/alignment/nonfinite failure, runtime failure
  và not-attempted; không cộng các loại chồng nhau.
- Format INVALID không có score trong phương pháp này. Không ép thành Level04,
  không điền score 0, không parse lại bằng regex để cứu nhãn. Technical failure
  hiện làm LS1 dừng không retry; một run dừng giữa chừng không được báo là
  completed-cohort AUROC. Partial-run audit chỉ mô tả, không dùng quyết định H1.
- Kiểm tra unique sample IDs và exact GT join. GT thiếu/sai không được lọc im
  lặng: dừng evaluation và giải quyết provenance theo quyền riêng. Không dùng
  tên file làm authoritative GT.
- Endpoint là **score-conditional AUROC**, không phải full-cohort AUROC khi
  `n<N`. Báo coverage `n/N`, riêng từng GT level, binary class, domain và nhóm
  prefix/format; missingness có thể liên quan đến độ khó và tạo selection bias.
- Các confusion/recall/FPR/FNR của nhãn là báo cáo khác: giữ cột INVALID và
  failure-aware denominators theo D9R24, không áp quy tắc “INVALID là FN” để bịa
  continuous score. Khi so các nhánh, dùng cùng IDs hợp lệ cho paired comparison,
  đồng thời công bố availability trên toàn `C`.
- Các 37 INVALID trong P2 không tự động là LS1 INVALID; P2.1 parser được dùng
  trong LS1 là acceptance rule riêng. Không tái gán trạng thái lịch sử.

Đề xuất sensitivity cho score thiếu (chưa được triển khai): nếu GT toàn `C`
đã hợp lệ và run đã hoàn tất, đặt `N+`, `N-` là supports toàn cohort,
`W=AUROC_E*n+*n-`, `U=N+*N- - n+*n-`. Khoảng biên hoàn thành score là
`[W/(N+*N-), (W+U)/(N+*N-)]`, coi các cặp chưa biết lần lượt đều thua/thắng.
Nếu `n+*n-=0`, đặt `W=0` vì không có cặp quan sát được (không nhân NA với 0);
nếu `N+*N-=0`, cả hai biên là NA.
Đây là **biên worst/best-case**, không phải một AUROC đo được, không phải CI;
không giả định missing-at-random. Không dùng nó để chứng minh cohort sạch.

### Bất định và domain

Primary là pooled image-level AUROC trên `E`; báo riêng từng `folder_domain`
đủ hai lớp, supports và coverage. Domain một lớp ⇒ NA. Trung bình đều các
domain có hỗ trợ chỉ là secondary, ghi `K_domain`; không so macro của hai tập
domain khác nhau như cùng estimand. Không đổi D3 mismatch semantics.

Đề xuất CI percentile 95%, `B=2000`, seed 42, shared draws cho paired contrasts.
D9R24 hiện quy định domain-stratified Normal `point_id` clusters, Anomaly
sample-level với dependence limitation, Normal thiếu `point_id` hard-fail.
**Không gọi bootstrap theo nhóm quan hệ mới là D9R24 nguyên bản.** PA3 cần duyệt
một phụ lục thống kê riêng: resample nguyên nhóm bảo vệ ở mục 6, trong strata
domain; nhóm xuyên domain giữ nguyên, đặt vào stratum mixed-domain riêng, không
xé nhóm. Mỗi draw mang cả nhãn/điểm/eligibility của nhóm; metric vẫn image-weighted.
Trong cùng draw tính endpoint và các contrasts trên cohort tương ứng.

Báo số draw đủ hai lớp và lý do draw NA. Đề xuất ít nhất 95% draw hợp lệ, ít
nhất 20 nhóm đóng góp mỗi binary class (có thể cùng nhóm mixed-label), CI width
≤ 0,20 cho quyết định chính; nếu không đạt, chỉ mô tả/chưa đủ bằng chứng.
Đây là **ngưỡng chất lượng đề xuất để duyệt**, không phải định lý về power hay
ngưỡng lấy từ kết quả. Trước inference phải đánh giá precision/power bằng giả
định mô phỏng và số nhóm được phép kiểm kê, không xem scores để đổi cỡ mẫu.
Không coi bootstrap ảnh độc lập hay Wilson recall intervals là CI AUROC.

Nếu chưa xác minh đủ dependency metadata để dùng phụ lục, kết quả theo bootstrap
D9R24 chỉ có tính exploratory với giới hạn Anomaly; chưa đạt điều kiện xác nhận
độc lập. `point_id` không chứng minh độc lập giữa địa điểm; strata theo domain
cũng không loại confounding do robot/cảnh. Pooled AUROC cao có thể chỉ phản ánh
domain prevalence: kết quả within-domain và leave-one-group-out sensitivity
phải đi kèm, không tuyên bố mô hình nhận biết hazard bằng quan hệ nhân quả.

## 4. Phân tích phụ bốn mức an toàn

Tất cả secondary/exploratory, không dùng chọn công thức hay cứu một H1 thất bại:

1. One-vs-rest cho từng `k`: positive = GT Level0k, score = `ell_k`, càng cao
   càng nghiêng về lớp k; mẫu số `n_k*(n-n_k)`, cùng tie/NA/eligibility rules.
   Gọi binary `auc` riêng từng lớp; không truyền log-probabilities vào API
   multiclass đòi probabilities. Macro OVR = trung bình đúng bốn AUROC, chỉ có
   khi cả bốn xác định; không bỏ Level03 rồi vẫn gọi “four-class macro”.
2. Ba cặp Level01-vs-Level04, Level02-vs-Level04, Level03-vs-Level04: subset
   đúng hai GT, score `z_k-z4`, chiều cao = Level0k, mẫu số `n_k*n_4`. Báo đủ
   cả ba, không chọn cặp đẹp nhất. Không suy các cặp này là phân biệt severity
   giữa các loại Anomaly.
3. Phân bố `s`, `ell_k`, margins `z_k-z4`, four-label mass và prediction counts
   theo GT/domain; confusion 4×(4+INVALID) cho nhãn sinh và raw argmax; nhấn mạnh
   Level01 misses, Normal→Level01/02 alarms, availability. Không học cutpoint.
4. Riêng subgroup **generated Level03**: AUROC `s` cùng chiều trong subgroup đó,
   ghi supports/coverage riêng. Đây mới trực tiếp kiểm tra biến thiên điểm giữa
   các ảnh nhận cùng nhãn Level03, nhưng conditioning trên output tạo selection
   bias. Không thay endpoint toàn `E` bằng subgroup sau khi xem kết quả.

Level03 cực ít mẫu: 15 là tổng lịch sử, holdout có thể ít hơn hoặc bằng 0.
Không oversample, duplicate, augmentation hay chuyển mẫu giữa dev/holdout để
tăng support; không gộp nhãn hoặc coi hàng nghìn bootstrap draws là hàng nghìn
ca độc lập. Level03 luôn báo exploratory, image/group counts, NA và interval
nếu ước lượng được; không đưa kết luận xác nhận riêng về lớp này. Macro OVR dù
tính được vẫn dễ dao động vì Level03; binary AUROC tốt có thể hoàn toàn do
Level01/02, không chứng minh phân biệt cả bốn mức. Không cần multiplicity claim
cho các mô tả; nếu muốn kiểm định xác nhận secondary phải có kế hoạch điều
chỉnh đa kiểm định được duyệt trước, không báo các p-value chọn lọc.

## 5. Đối chứng để tách lỗi format, chọn nhãn và tín hiệu điểm

| Đối chứng/báo cáo bắt buộc được đề xuất | Câu hỏi nó giải quyết | Điều nó không chứng minh |
| --- | --- | --- |
| Raw response → parser hiện hành của từng protocol; riêng LS1 dùng P2.1 acceptance | Format INVALID hay response hợp lệ nhưng sai GT? Báo error categories, không repair | P2 SUCCESS/INVALID không được sửa theo parser LS1 |
| Cùng LS1 trace: nhãn sinh, processed global argmax từng bước, raw global argmax, raw four-label argmax và tie counts | Có mismatch trong pipeline/score processor hay chỉ argmax ưu tiên một lớp? Technical invariant sai ⇒ dừng | Raw argmax trùng greedy nhưng AUROC cao chỉ cho thấy ordering có ích; không chứng minh nguyên nhân “prior bias” |
| Constant score/always-Level03 baseline, trên cùng eligible IDs; binary score từ nhãn sinh cũng báo riêng | Nếu tất cả nhãn là Level03, hard-label ranking không phân biệt; continuous score có thể khác | Không gọi AUROC cao hơn hard-label score là cải thiện accuracy hoặc safety |
| Coverage và score distributions theo prefix/format/full-vocab four-label mass | Tín hiệu có đi kèm formatting context hoặc label tokens rất ít probability mass? | Subset softmax không thành posterior calibrated. Không chọn mass cutoff sau khi xem kết quả; lưu log-mass để tránh underflow |
| Within-domain, grouped uncertainty và sensitivity bỏ lần lượt từng nhóm | Tín hiệu pooled có phụ thuộc một domain/nhóm lớn? | Không loại hết scene/robot confounding hoặc chứng minh hazard reasoning |
| Synthetic technical qualification, raw-before-parse và CPU recomputation audit sau này | Pipeline có trích đúng token, giữ đúng raw/processed và tái tính được không? | Synthetic không chứng minh độ chính xác trên ảnh công nghiệp; PR này không chạy qualification |

Binary hard-label control dùng `h=1` khi nhãn sinh là Level01/02/03, `h=0`
khi Level04, cùng chiều và tie policy với `s`, chỉ trên cùng eligible IDs.
Đây là đối chứng mất thông tin do rút điểm thành nhãn, không là endpoint chính.

So với P2/P2.1 lịch sử chỉ dùng matched IDs và condition/provenance đã audit,
báo cả giao và phần thiếu; không so 5.013 với 1.254 như paired cohorts. InternVL3
có thể là replication được duyệt riêng với cùng endpoint, không là điều kiện
để chọn model thắng hoặc đưa LS1 vào ensemble RQ3.

Một fixed assistant-prefix scoring arm áp dụng cả INVALID có thể tách thêm ảnh
hưởng format, nhưng **đó là phương pháp mới**, chưa được current LS1 hỗ trợ như
sample-scoring path; không phải cứu INVALID của phương pháp chính. Image-null,
image-swap hoặc blur arms cũng cần hợp đồng và inference riêng để thăm dò đóng
góp của ảnh. Chúng không bắt buộc cho claim hẹp “score có association với GT”,
nhưng thiếu chúng thì không kết luận quan hệ nhân quả do nội dung hazard.
Không đưa reference subtraction/calibrated prediction vào PA3 này.

## 6. TRAIN-dev/TRAIN-holdout và bảo vệ nhóm liên quan

Đây là **kế hoạch prospective sau phê duyệt**, chưa đọc metadata/ảnh thật, chưa
tạo cohort, manifest hay split. Giữ official `split=train/test` và P2 pool
nguyên vẹn; vai trò `pa3_role` nếu được duyệt chỉ là một overlay nghiên cứu.

1. Người quản lý dữ liệu lập exposure ledger trước khi mở LS1 scores: sample IDs,
   ảnh/GT/output nào đã xem, ai xem, mục đích và mức độ quan sát (aggregate hay
   từng mẫu), có hash/provenance. Bắt buộc gồm 10 ảnh exploratory và mọi ảnh đã
   xem trong audit/error analysis trước đó; không chỉ loại đúng 10 IDs rồi
   tuyên bố còn lại sạch. GT của 10 ảnh cần kiểm tra theo manifest được duyệt,
   không dựa tên file. Mẫu không rõ exposure được đánh dấu unknown/quarantine.
2. Tạo graph quan hệ, không dùng LS1 score: nối mọi ảnh Normal cùng `point_id`,
   exact duplicates và quan hệ cùng sequence/scene có evidence đã thẩm định;
   lấy connected components (bao gồm quan hệ bắc cầu). Anomaly không mặc định
   độc lập vì mỗi ảnh có một point folder. Near-duplicate/source-family chỉ là
   candidate links, không tự gọi true video/site IDs. Quy tắc review/link và
   bảo thủ gom nhóm/quarantine các quan hệ chưa rõ phải được duyệt trước.
3. Quarantine toàn component chứa ảnh đã xem/unknown hoặc liên kết đã biết tới
   TEST đã quan sát. Chỉ dùng ledger/quan hệ lịch sử được duyệt để bảo vệ ranh
   giới TEST, không đọc TEST mới hay dùng hiệu năng TEST để quyết định giữ nhóm.
   Nếu không xác minh được liên hệ thì không chứng nhận independence. Danh sách
   exclusion và lý do được khóa; không xóa dữ liệu gốc hay đổi nhãn/split.
4. Đề xuất tỷ lệ mục tiêu **50% nhóm dev / 50% nhóm holdout**, salt cố định
   `pa3-proposal-v1-2026-10-11` và hash `SHA256(salt || "|" || group_id)`;
   group ID lấy từ danh sách IDs sắp thứ tự, có serialization được khóa trong
   implementation sau. Trong strata domain × binary status, sort hash rồi
   giao `floor(G/2)` nhóm đầu cho dev, còn lại holdout. Component mixed-label
   hoặc mixed-domain có strata riêng; không xé nhóm để cân bằng lớp. Stratum
   singleton được quarantine khỏi confirmatory holdout, báo riêng feasibility.
   Không thử nhiều salt/tỷ lệ rồi chọn phân hoạch thuận lợi. Đây là allocation
   đề xuất, cần duyệt cả thuật toán, tỷ lệ và actual counts trước inference.
5. Dev chỉ phục vụ kiểm tra khả thi kỹ thuật của **một** công thức đã khóa;
   không dùng để chọn dấu/biến thể score hay fit calibration trong PA3. Sau khi
   source/prompt/model/metric/cohort/hash và tiêu chí được phê duyệt, chấm holdout
   một lần và seal raw trước khi join GT. Analyst không xem output/GT holdout
   trong giai đoạn dev. Nếu dev dẫn đến sửa phương pháp, phải đăng ký version
   mới trước mở holdout; một holdout đã mở không tái gọi là chưa quan sát.

**Giới hạn quan trọng:** Qwen P2 đã chạy toàn bộ 5.013 ảnh, tức có cả TRAIN, và
aggregate output đã được dùng để hình thành giả thuyết. “Chưa xem LS1 scores”
không đồng nghĩa “chưa từng xem ảnh, GT hay P2 predictions”. Phân hoạch mới chỉ
bảo vệ khỏi lựa chọn tiếp theo, không xóa exposure hay nguy cơ lựa chọn giả
thuyết sau kết quả. Phải gọi đây là prospective evaluation sau retrospective
motivation, với contamination disclosure. Không tuyên bố holdout hoàn toàn độc
lập nếu ledger không chứng minh được. Nếu mọi nhóm phù hợp đã bị quan sát hoặc
số nhóm độc lập còn quá ít, chỉ có exploratory reanalysis; cần cohort ngoài
đã được duyệt hoặc dữ liệu tương lai để xác nhận mạnh hơn. Không tự thu thêm
dữ liệu hoặc thay định nghĩa dataset trong task này.

## 7. Tiêu chí quyết định trước thí nghiệm (đề xuất, chưa có hiệu lực)

Các mốc dưới đây phải được Research Lead chấp thuận **trước** mở holdout.
Một endpoint chính, một model chính, một score/direction; không chọn kết luận
dựa trên endpoint phụ có kết quả đẹp.

Gate chung: đầy đủ approvals; completed run và artifact audit; GT join đúng;
T1/trace checks PASS; exposure/grouping đủ để mô tả chính xác phạm vi độc lập;
đủ cả hai lớp và điều kiện nhóm/bootstrap ở mục 3. Đề xuất coverage ≥ 95% riêng
ở mỗi binary class để đưa ra kết luận chính; thấp hơn chỉ báo conditional
estimate và chưa đủ bằng chứng cho kết luận dự kiến. Các số 95%, 20 nhóm, width
0,20 là lựa chọn protocol đề xuất, không phải thống kê đã đo.

| Kết luận | Quy tắc cố định đề xuất | Cách diễn giải |
| --- | --- | --- |
| H1 được hỗ trợ trong phạm vi đã định | Qua gates và cận dưới CI 95% của primary AUROC > 0,5 | Có tín hiệu xếp hạng theo chiều nguy hiểm trên cohort **scored** này, dưới giả định nhóm đã công bố; không chứng minh calibration, accuracy gain, safety hoặc ngoài miền |
| H1 không được hỗ trợ theo chiều định trước | Qua gates và cận trên CI 95% ≤ 0,5 | Điểm định trước không cho discrimination đúng chiều trong cohort này; AUROC < 0,5 không cho phép đảo dấu hậu nghiệm hoặc kết luận mọi hidden representation vô ích |
| Chưa đủ bằng chứng | CI có lower ≤ 0,5 < upper, hoặc bất kỳ gate nào không đạt: quá rộng, ít support/nhóm, missingness cao, run/audit/approval lỗi, independence không kiểm chứng | Không đánh đồng “không significant” với chứng minh không có tín hiệu; báo nguyên estimate/CI/coverage và blocker |

Đề xuất thêm mốc ý nghĩa thực tiễn **AUROC 0,55** (`delta=0,05` trên chance),
chưa được tối ưu từ dữ liệu: cận trên < 0,55 loại trừ hiệu ứng cỡ này trong
phạm vi CI; cận dưới > 0,55 hỗ trợ vượt mốc đó; còn lại chưa xác định. H1 có
thể được hỗ trợ thống kê nhưng hiệu ứng quá nhỏ cho mốc thực tiễn. Mốc này không
phải ngưỡng phân loại, không chứng minh operating point an toàn; nếu cần mốc
khác phải duyệt trước chấm holdout, không đổi sau kết quả.

Để nói riêng “ngay giữa các ảnh cùng bị dự đoán Level03 vẫn còn tín hiệu”, cần
subgroup Level03 có đủ support/gates và CI lower > 0,5; đây vẫn là secondary
evidence, không nâng thành primary claim. Nếu chỉ pooled AUROC dương mà
within-domain không đủ bằng chứng, giới hạn kết luận ở pooled cohort và ghi
domain confounding chưa giải quyết. Missing-score completion bounds không đủ
hỗ trợ thì không mở rộng kết luận thành full-cohort. Không có kết quả PA3 nào
tự động cho phép thay quyết định triển khai hay bỏ INVALID.

## 8. Quan hệ với RQ3 và phê duyệt còn thiếu

**Đề xuất giữ PA3 là nghiên cứu bổ sung, chưa thay RQ3.**
[D9R22](../configs/pre_freeze/d9r22_seminar_scope.v1.json) định nghĩa RQ3 về
consistency/disagreement giữa bốn model, chỉ tái dùng classification predictions,
không inference bổ sung. [D9R24](../configs/pre_freeze/d9r24_metric_contract.v1.json)
dùng JOINT_VALID_4 và chín metric families. PA3 đo discrimination của điểm một
model, cohort và uncertainty khác, có thể cần inference mới; nó không trả lời
error complementarity, shared blind spots hay reliability từ disagreement.
Không có dự đoán Level04 của hai model cũng không tự làm RQ3 vô nghĩa; độ biến
thiên và support cho từng metric phải được đánh giá đúng contract.

Nếu muốn thay RQ3 vì mục tiêu khoa học/thời lượng Seminar, cần quyết định scope
mới cùng kế hoạch metric/inference/cohort trước thực thi; không chọn RQ dựa
vào kết quả TEST hoặc một PA3 thuận lợi. PR này không sửa RQ, DECISIONS hay
bất kỳ contract frozen nào.

| Phê duyệt/điều kiện còn thiếu | Phạm vi cần quyết định, không được suy từ Draft PR |
| --- | --- |
| DEC-LS1-001 **PENDING**, kể cả audit correction | Research Lead duyệt nghiên cứu và exact TRAIN cohort/run rights; khóa vô điều kiện cần implementation review riêng, không receipt tự lập |
| DEC-LS1-002 **PROPOSED/PENDING** | Quyết định đề xuất ngưng calibrated decision rule, giữ uncalibrated measurement và successor study; nội dung note không tự có hiệu lực |
| Hợp đồng PA3 riêng | Endpoint, eligibility, missingness, effect-size/gates, bootstrap/grouping, salt/tỷ lệ/counts, exposure ledger, GT provenance, model/source/prompt hashes, artifacts, một lần mở holdout |
| D2/D5/D9R24 applicability | Duyệt overlay TRAIN và dependency/uncertainty riêng; không sửa grouping hoặc metric frozen bằng tài liệu đề xuất |
| Phạm vi D9R22 | Nếu bổ sung vào Seminar, duyệt scope/inference ngoài RQ3 hiện hành. Nếu sau này học threshold/temperature/calibration từ TRAIN-dev, cần **ngoại lệ D9R22 rõ ràng**, version/condition supervised riêng, không gọi zero-shot; không dùng TEST để chọn hoặc fit |
| Review và runtime prerequisites | ChatGPT kiểm tra Draft trên GitHub; các audit độc lập theo quy trình LS1; implementation PR riêng và synthetic/runtime/T1 qualification; owner-run được cấp quyền cụ thể sau đó |

Thứ tự đề xuất: quyết định khoa học và giới hạn dữ liệu → review implementation
riêng → qualification được phép → khóa cohort/protocol trước scores → owner
run có quyền → seal/audit → báo cáo theo tiêu chí đã duyệt. TEST tiếp tục locked;
quyền P2/P2.1 không chuyển sang LS1/PA3. Calibration/threshold learning không
được triển khai hoặc thử trong PR này.

Artifacts tương lai đặt dưới `data/processed/`, dùng relative paths; lưu raw
text/token traces trước parse, IDs/prompt/model revision/generation config/run
ID, input/source/method hashes, runtime versions, seeds, cohort/exclusions và
failure evidence. Không commit ảnh, raw model outputs lớn hoặc path máy riêng.

## 9. Kiểm tra của PR đề xuất

Chỉ kiểm tra tĩnh: đối chiếu source/decisions tại BASE, kiểm tra whitespace/diff,
relative Markdown links, UTF-8, allowlist đúng hai file và TASKS append-only.
Không import/chạy LS1, tokenizer, evaluator hay pipeline; không chạy unit suite
hoặc thí nghiệm vì không đổi code. Không cài dependency, không đọc InspecSafe
TRAIN/TEST thật, không GPU/model load, không tạo authority hay mở khóa dữ liệu.
Kết quả kiểm tra và exact head SHA được ghi trong Draft PR handoff. Dừng tại
Draft PR để ChatGPT kiểm tra; không merge, không đánh dấu nghiên cứu COMPLETE.
