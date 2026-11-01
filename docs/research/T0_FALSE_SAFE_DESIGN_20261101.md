# SafeShift — T0: Đề xuất Khóa luận về phát hiện false-safe

Ngày: **01/11/2026, Asia/Bangkok**. BASE: `89d886356c15064b5f1cc2021aa5d614e7e7f53f`.
**PROPOSED / O1–O5 PENDING / CONFIRMATORY EXPERIMENT BLOCKED.**
Đây là hồ sơ để Owner trình giảng viên, không phải protocol mới, final roster,
quyền thực nghiệm hoặc quyết định khoa học. HEAD cuối và kết quả kiểm tra ở Draft PR.

## 1. Đề nghị trình giảng viên

**Tên tiếng Việt đề xuất:** SafeShift: Phát hiện quyết định an toàn sai và ưu
tiên kiểm tra bằng kiểm tra chéo các mô hình ngôn ngữ–thị giác trong môi trường
công nghiệp.

**Tên tiếng Anh đề xuất:** SafeShift: Detecting False-Safe Decisions and
Prioritizing Review through Cross-Model Checking of Vision–Language Models in
Industrial Environments.

Một VLM có thể trả lời Normal cho ảnh có nhãn tham chiếu nguy hiểm. Câu hỏi
nghiên cứu là: thông tin từ các VLM bổ sung có đưa **thêm bao nhiêu quyết định
false-safe tới người kiểm tra với cùng sức chứa review**, so với tín hiệu của
chính mô hình chính hoặc một tín hiệu đơn mạnh nhất? Agreement không là GT;
đưa vào review chưa có nghĩa đã sửa đúng nhãn hoặc ngăn được tai nạn.

Đề xuất một focal cố định có điều kiện là **Qwen3-VL-8B-Instruct**, cùng hai
peers ứng viên **InternVL3.5-4B-HF** và **MiniCPM-V-4 resampler FP32** đúng
identity ở §4. Peers tự phân loại cùng ảnh, không xem câu trả lời của nhau hay
focal. Giữ raw/prediction gốc; phương pháp tạo thứ tự kiểm tra, không tự ghi đè
nhãn bằng voting. Ưu tiên kiểm phương án không học trước; logistic nhỏ là
phương án có điều kiện về dữ liệu, không fine-tune VLM.

Đóng góp kỳ vọng là thực nghiệm có đối chứng về giá trị tăng thêm, shared
errors, missingness và chi phí. Logistic, voting, disagreement và reject/review
không được nhận là thuật toán mới. Chưa có bằng chứng phương pháp sẽ thắng.

Nguồn tư vấn chính là báo cáo Owner đính kèm
`SafeShift_Bao_cao_tham_dinh_Codex_20261101.md`, đối chiếu với main. Nguồn của
thầy là bản chép từ ảnh do Owner cung cấp, chưa phải xác nhận học vụ. [Hồ sơ
bằng chứng](T0_FALSE_SAFE_EVIDENCE_20261101.md) lưu hash, nguồn, số đếm và giới
hạn; không đưa đường dẫn máy cá nhân hay toàn bộ báo cáo chưa làm sạch lên Git.

## 2. Khác kế hoạch hiện tại ở đâu?

| Nội dung | Kế hoạch bốn model trên main | T0 đề nghị để xét |
| --- | --- | --- |
| Phương pháp | Bốn VLM ngang hàng, bốn focal luân phiên, strict-majority/abstain | Một focal có điều kiện + tối đa hai peers; ưu tiên lỗi focal |
| Primary đề xuất | Macro-F1 ensemble so với single mạnh nhất chọn D/V | False-safe capture tại cùng budget so với baseline đơn tín hiệu mạnh nhất chọn D/V |
| Nhãn phân loại | Hợp nhất có thể đổi quyết định cuối | Giữ nhãn focal; review là đầu ra riêng |
| HNLO | Optional ở từng model đủ điều kiện | Combo chỉ cần HNLO focal hợp lệ; MiniCPM có thể chỉ cung cấp nhãn |
| Compute panel đầy đủ | Khoảng 4N model-image calls | Tối đa khoảng 3N, có thể ít hơn nếu policy gọi peer chỉ trên focal-Normal được khóa trước |
| Vai trò classification | Endpoint chất lượng chính | Baseline/guardrail và phân tích phụ, không suy capture gain thành Macro-F1 gain |
| Đầu ra người dùng | Viewer và study có điều kiện | Chỉ yêu cầu về case review trong thiết kế; task T0 không làm UI |

[Kế hoạch bốn model](THESIS_EXECUTION_PLAN_2026.md) vẫn là **PROPOSED**; merge
tài liệu không phê duyệt O1–O5. [M1/M2](DECISIONS.md) có hiệu lực lịch sử đúng
phạm vi dự án, gồm lựa chọn triage tại M1; điều đó không duyệt panel/metric mới
ở T0. Roster Seminar lịch sử Qwen2.5/Qwen3/InternVL3-2B/Moondream2 giữ nguyên.
InternVL3.5 không kế thừa kết quả InternVL3-2B. Không sửa hồi tố bất kỳ quyết
định, protocol/config đã duyệt hoặc kế hoạch cũ nào trong PR này.

**Điểm cần xác nhận rõ nhất:** giảng viên có chấp nhận chuyển mục tiêu chất
lượng chính từ tăng Macro-F1 nhãn hợp nhất sang phát hiện false-safe/ưu tiên
review hay không? Nếu chưa, hướng này chưa thể coi là đáp ứng CT1. Không triển
khai fusion, thấy thua rồi mới đổi primary.

## 3. Mục tiêu và câu hỏi kiểm chứng

| RQ đề xuất | So sánh hoặc đầu ra có thể bác bỏ |
| --- | --- |
| RQ1 — giá trị chính | Combo HNLO focal + peers có bắt thêm false-safe ở cùng K so với baseline đơn tín hiệu mạnh nhất khóa trên D/V không? Báo cả chênh số ca, capture, uncertainty và guardrails. Nếu HNLO focal không đủ điều kiện, RQ1-combo BLOCKED; phương án peer-only cần O1/O2 xác nhận riêng trước target. |
| RQ2 — thành phần | Peer-only khác HNLO-only thế nào? Peer thứ hai có thêm ích lợi khi đã có InternVL? Bỏ từng peer, bỏ HNLO, đổi ordinal sang binary có làm mất ích lợi không? |
| RQ3 — giới hạn | Shared false-safe, miền/nguồn ít sự kiện, peer INVALID, thiếu score và overload có làm mất gain hoặc gây harm/chi phí quá mức không? |
| RQ4 — con người, phụ có điều kiện | Nếu sau này có reviewer/rubric/quyền, việc hiển thị hàng đợi và provenance có cải thiện quyết định/thời gian kiểm tra không? Capture của máy không trả lời RQ này. |

Primary chỉ một contrast/một budget được chốt trước target. Các RQ2/RQ3 là
secondary hoặc exploratory, ghi family/multiplicity ở O2/O5; không tìm focal,
budget hoặc subset thắng trên target. Không cam kết calibration, grounding
vùng, correct-answer-wrong-reason hoặc chất lượng user study khi thiếu evidence.

## 4. Điều kiện sử dụng ba mô hình

| Mô hình / pin kế thừa | Đã có bằng chứng gì? | Điều kiện còn thiếu cho vai trò đề xuất |
| --- | --- | --- |
| `Qwen/Qwen3-VL-8B-Instruct` @ `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` | V4 gốc 3.763 planned, 3.539 SUCCESS, 1 TECHNICAL_ERROR/223 NOT_ATTEMPTED; saved-score verification, không raw audit mới. HNLO hazard AUROC ≈0,95279 trên SUCCESS chỉ là mô tả TRAIN. | O3 chốt focal trước target; qualification đúng source/env/prompt/parser/cohort mới; raw/logit/native decision alignment/replay, coverage, cost và đủ error events trên D. Không mặc định tốt nhất trên dữ liệu mới. |
| `OpenGVLab/InternVL3_5-4B-HF` @ `6bd4487402110ef9889ba50eb7aefeb302526fed` | Official TRAIN160: 135 SUCCESS/25 INVALID, HNLO số 135; technical receipt có replay. Không phải custom Instruct hoặc InternVL3-2B. | Phân tích utility đối với **Qwen3**, gồm 25 INVALID và tải review; dữ liệu paired cùng source/image/version, qualification phạm vi mới. Không yêu cầu peer phải có HNLO để dùng nhãn. |
| `openbmb/MiniCPM-V-4` @ `6f69a8235885be89608f3a71ffd40695b379e1e7` | Official TRAIN160: 155 SUCCESS/5 INVALID; 160 HNLO null dù 1.760 bước logits hữu hạn. #157 đã audit/merge/postmerge xác minh kỹ thuật, selection/pooling vẫn PENDING. | Chỉ dùng đúng effective implementation bên dưới; bổ sung ích lợi vượt focal+InternVL trên D/V với chi phí/missingness thật. Không bắt có score HNLO, không đổi token/parser để lấy score. |

MiniCPM identity bắt buộc: `minicpm4-resampler-attention-fp32-v1`; effective
config SHA256 `5b85504ff24ff42d4d629dbf00feb0c484022cfef3a7d57b571eaae99d1c8b00`;
descriptor SHA256 `2fe992725df4340f910934b5846278e34968196a9dff3fc4171fb4279bfaf5da`.
Weights vẫn FP16/eager; chỉ resampler score/softmax/value product FP32, output
về dtype gốc. Owner adoption đúng TRAIN160 không tự duyệt final thesis roster,
nguồn D/V/T, metric hoặc grant mới. Nguồn: [quyết định](DECISIONS.md),
[adoption](MINICPM4_FP32_OFFICIAL_ADOPTION_20261031.md),
[hậu merge #157](https://github.com/tantdna2/SafeShift/pull/157#issuecomment-6546464187).

Qualification tách bốn điều kiện: (a) runtime/rights/custody đúng identity;
(b) nhãn/INVALID/support không suy biến không giải thích được; (c) score chỉ
khi alignment đủ bằng chứng; (d) utility/cost theo vai trò. Technical PASS
không miễn (b)–(d). Các caps/tiêu chí nhận do O3/O5 chốt trên D trước target.

Giữ đủ ba **chỉ khi** focal đủ điều kiện và mỗi peer có giá trị tăng thêm được
đo trên D/V theo rule đã duyệt, coverage/chi phí khả thi. Nếu peer thứ hai
không thêm utility hoặc vượt caps: trình O3 giảm còn focal+một peer trước
freeze. Nếu Qwen3 không đạt: dừng, giữ negative qualification, trình O1/O3;
không chọn focal khác thuận lợi sau xem target và không tìm model thứ tư.

## 5. Phương pháp theo ba mức

Mọi định nghĩa ở đây là đề xuất O2, không thay công thức M2. GT giữ
Level01–04, hazard = Level01–03, Normal = Level04. HNLO không là xác suất lỗi.

| Mức | Không huấn luyện trọng số bằng nhãn lỗi | Có ranker học từ dữ liệu — optional |
| --- | --- | --- |
| Baseline | Nhãn Qwen3 không review; random review cùng K; raw-HNLO focal xếp giảm dần khi hợp lệ; review-all chỉ là biên trần workload | Logistic chỉ h, cùng regularization/search budget với full, để tách lợi ích fit khỏi peer information |
| Chỉ kiểm tra chéo | Xếp theo tỷ lệ peer cảnh báo hazard khi focal Normal; so một peer/hai peers; ordinal là ablation | Logistic chỉ d; fit target lỗi false-safe trên D trong focal-Normal, không dùng hazard toàn P như target lỗi |
| HNLO hợp lệ + kiểm tra chéo | Rule minh bạch đề nghị: ưu tiên d-bin giảm dần, trong mỗi mức dùng h giảm dần; thứ tự ưu tiên này chờ O2, không học weights | Logistic L2 với h và d theo báo cáo tư vấn; VLM frozen. Không thêm features/search tự do khi thấy V/T |

Trước ranking, báo classification của **từng single model** trên cùng planned
P/GT: confusion, false-safe/severe, INVALID/missing, miền và cost. Joint
complete-case chỉ là bảng phụ có mẫu số hiện rõ; không lấy cohort dễ hơn để
so trực tiếp. Q3 không tự được miễn điều kiện vì ranking lịch sử cao hơn.

Với hai peer hợp lệ, đề xuất `d_bin = (I(peer1 hazard) + I(peer2 hazard))/2`.
Ordinal thay thế: `d_ord = ((4-level_peer1)+(4-level_peer2))/6`, mã hóa
Level01=1,…,Level04=4. Với một peer, dùng mẫu số 1 và 3 tương ứng để vẫn nằm
trong [0,1]. Đây là mã hóa thứ bậc, chưa chứng minh khoảng cách nguy cơ bằng
nhau. Score từ peer không là feature bắt buộc; không trung bình raw HNLO giữa
model, không thay bằng textual confidence.

Ranker học: fit trên D có GT hợp lệ và focal-Normal; mọi normalization,
imputation được cho phép, feature selection và regularization nằm **trong
training fold theo nguồn**. V chọn phiên bản theo rule trước target, không fit
lại toàn feature pipeline rồi tiếp tục coi V là xác nhận độc lập. Không tự
dùng rule “10 events/feature”; nếu thiếu positive/negative events hoặc sources
cho fold, bỏ nhánh learned/ghi BLOCKED. Điểm logistic là điểm ưu tiên, chưa gọi
là xác suất đã hiệu chuẩn. Không cần huấn luyện lại VLM ở bất kỳ mức nào.

Baseline chính `B*` là baseline **đơn tín hiệu** mạnh nhất trên D/V theo cùng
metric, budget, policy chọn và giới hạn cost; bao gồm raw h, h-only learned nếu
cho phép, và d-only. B* được khóa trước T; peer-only mạnh hơn h phải được báo,
không chỉ so full với random. Nhánh không học và learned được báo riêng; chọn
nhánh chính trước T với cùng tuning budget, không chọn winner hậu nghiệm.

## 6. Tập mẫu, thiếu kết quả và ngân sách

Đề xuất cho mỗi batch khóa membership trước predictions:

- `P`: toàn planned IDs, `N = len(P)`; `S`: IDs có GT hợp lệ để đánh giá. GT
  unresolved vẫn ở workload/coverage, không ép thành Normal.
- `C`: IDs focal sinh Level04 hợp lệ, xác định **không dùng GT**.
- `F`: IDs trong C và S có GT Level01–03. F cố định chung mọi arm, kể cả thiếu
  peer/score; không đổi denominator theo complete-case.
- `M_a`: focal INVALID/missing/technical/not-attempted, cộng các ca trong C
  thiếu feature bắt buộc của arm a. Không tự coi peer INVALID là hazard hoặc
  Normal; h null không điền 0. `E_a = C` bỏ các ca thuộc `M_a`.
- `K = floor(b*N)`: tổng capacity, không chỉ phần ca có score. b chưa chốt.
  Khi `len(M_a) <= K`, queue `R_a` chứa M_a và tối đa
  `min(K-len(M_a), len(E_a))` ca đứng đầu E_a. Nếu E hết, báo capacity chưa dùng,
  không tự lấp bằng cohort khác.
- Khi `len(M_a) > K`: **OVERLOAD**, chỉ có thể xử lý K ca theo thứ tự mandatory
  đã định trước và báo phần tồn; không claim budget b phục vụ toàn M hoặc PASS
  vận hành. Thiếu output chưa review luôn là unresolved risk, không biến thành
  một dự đoán Normal hoặc một false-safe đã phát nhãn.

Tie-break và thứ tự mandatory dùng keyed hash ID làm mờ + seed khóa trước;
không dùng filename chứa Level/domain, GT, mức nguy hiểm thật hay thứ tự tiện
chọn lỗi. Secret key riêng không commit; custodian giữ để tái lập có quyền.

Hai bảng bắt buộc: **signal comparison** dùng cùng E/M là giao eligibility và
hợp mandatory của các arms để cô lập giá trị features; bảng này có workload
nhân tạo và không đại diện baseline đơn khi vận hành. **Operational comparison**
dùng M_a/E_a và chi phí đúng từng arm, cùng P/C/F/K; đây là bảng chính để đưa
ra khuyến nghị. Báo riêng false-safe vào mandatory do thiếu feature và
false-safe do score xếp ưu tiên, tránh coi mọi failure là phát hiện bằng tín hiệu.

Full panel có thể cần 3N calls; nếu chỉ gọi peers trên C thì khoảng N+2C, với
policy đã freeze và đo thực tế. Ablation tái dùng outputs; h-only không phải
chịu tiền peers. Mọi loads, failed/rejected qualification, recovery/rerun,
wall-time, GPU-time, storage và human review đều báo riêng rồi tổng hợp, không
dùng cached ablation để gọi full inference miễn phí. Chưa chọn result giữa
series/attempts khi scientific selection còn PENDING.

## 7. Cách đo chính và diễn giải

Với cùng F, K và queue R của mỗi arm:

```text
found_a = len(F intersect R_a)
Capture_FS_a(b) = found_a / len(F)
additional_found = found_full - found_B*
Delta_capture = Capture_FS_full - Capture_FS_B*
gained = len(F intersect (R_full minus R_B*))
lost   = len(F intersect (R_B* minus R_full))
additional_found = gained - lost
```

Báo cả tử/mẫu và số ca gained/lost; F rỗng thì capture/Delta undefined, không
ghi 100% hoặc PASS. Thay đổi metric chính từ Macro-F1 sang capture vẫn chờ O1/O2.

| Báo cáo bắt buộc | Định nghĩa/giới hạn |
| --- | --- |
| Cảnh báo nhầm của triage | Số ca R giao C giao S có GT Normal; kèm tỷ lệ trên ca review trong C có GT và trên Normal trong C. Không lẫn với focal false alarm trên toàn S. |
| Precision review false-safe | found / số ca R giao C giao S; báo thêm workload toàn R, các ca không thuộc C và GT unresolved. |
| Bỏ sót còn lại | Số F không ở R; severe Level01 trong phần đó; chia cho F/severe-F và báo risk trên C giao S chưa review khi mẫu số khác 0. |
| Thiếu kết quả | Planned/status từng model, GT unresolved, h null, peer missing, mandatory còn tồn, số slot dùng; breakdown theo GT khi GT được phép. |
| Xếp hạng lỗi | Error AP trên E giao S, positive = F trong E; khóa xử lý nhóm tied scores; báo positive support và coverage. Không thay bằng hazard AUROC/AP toàn P. |
| Phân loại | Confusion 4×5, Accuracy/Macro-F1/BA, hazard false-safe / hazard support, Level01→04 / Level01 support, Normal→hazard / Normal support. INVALID/missing giữ trong support/FN theo contract đề xuất; thiếu lớp báo support và giới hạn bốn lớp. |
| Chi phí | Calls, loads, time/latency p50/p95, GPU/RAM peaks, bytes, quota/cost và phút review; hiệu quả trên cùng budget review khác hiệu quả cùng tổng chi phí. |
| Theo nhóm | Domain/source, rare severe, unknown nguồn; nhóm không có F hoặc thiếu support hiện undefined; không chỉ báo miền đẹp. |

Đề xuất uncertainty cho chênh lệch là paired cluster resampling theo **nguồn
đã xác minh**, giữ cùng ảnh/outputs/arms trong draw và tính lại queue theo
batch policy đã khóa. Ít nguồn/zero-event draws quá nhiều thì CI unavailable
hoặc chỉ sensitivity; không bootstrap ảnh để giả precision. Quy tắc số draw,
undefined, CI level, multiplicity và precision chờ O5. Không báo power đã tính.

**Review 20%, gain 10 điểm phần trăm, CI 95% và power 80% trong tư vấn chỉ là
phương án cần cân nhắc, không phải tiêu chí đã duyệt.** Dùng ký hiệu b, delta,
CI level, cost/harm margins chờ O5; chốt từ workload examiner, source/event
pilot và nguồn lực trước T. Cả biên severe noninferiority cũng chưa được tự khóa.

Sau freeze: có thể kết luận benefit nếu độ bất định và guardrails đáp ứng
rule đã duyệt; thiếu precision là inconclusive; hiệu quả không đạt/harm là kết
quả âm phải giữ; thiếu data/authority là BLOCKED, khác với thực nghiệm thất bại.
Không đổi primary/margins sau thấy T hoặc gọi CI chứa 0 là tương đương.

## 8. Dữ liệu hiện có và khả năng tách D/V/T

Nguồn gốc InspecSafe-V1: HF `Tetrabot2026/InspecSafe-V1` revision
`f3cb7d3e7827c1afc1c5bfd0524257984bba46ab`, Zenodo v1.0.1 theo
[audit kế thừa](../DATA_AND_ETHICS.md); backup local chưa tự là archive upstream
byte-identical. Không mở dataset hoặc TEST trong T0; số TEST chỉ trích tài liệu.

| Hiện có | Vai trò có thể bảo vệ | Không đủ để làm gì? |
| --- | --- | --- |
| TRAIN 3.763, 749 hazard/3.014 Normal; levels 490/251/8/3.014 | Lịch sử H, D thăm dò sau phạm vi được duyệt | TRAIN đã phơi nhiễm không là V/T độc lập dù chia lại theo group |
| Qwen3 V4 gốc: 3.539 SUCCESS, 700 hazard/2.839 Normal | Recount saved reports đúng hash/membership; nguồn motivation/counts | Không ghép Recovery224, không dùng cohort complete-case che 224 thiếu kết quả |
| TRAIN160: 48/24/8/80 theo Level01/02/03/04, cùng manifest hai peers | Engineering/development exploratory; paired candidate diagnostics | Hazard 50%, chọn có phân tầng và envelope kích thước; không prevalence vận hành hoặc 160 nguồn độc lập |
| Source metadata lịch sử | Domain/point/family/exact/dHash để screening/sensitivity | Chưa có registry xác minh site/video/camera-session đủ coverage; năm domain không là năm nguồn |
| TEST 1.250 theo audit lịch sử | **LOCKED / NOT ACCESSED** | Không dùng như T thay thế; không mở để kiểm overlap trong task này |

Các tập cần bổ sung bằng chứng, **chưa tạo hoặc thu thập**:

| Vai trò | Yêu cầu để có thể dùng | Trạng thái hiện tại |
| --- | --- | --- |
| D | TRAIN/H có quyền cho thăm dò; nếu muốn CV theo nguồn phải xác minh groups; cần paired focal/peer outputs và đủ errors | Có H và hai peer TRAIN160; xem giới hạn ghép metadata ở evidence. Chưa có D nguồn mới đã duyệt. |
| V | Nguồn tách D/H, quyền và GT rubric tương thích; chọn policy/baseline/regularization trước target | Chưa định danh cohort/source registry/custodian đủ bằng chứng → BLOCKED cho validation xác nhận |
| T | Nguồn tách H/D/V, manifest/checksum/custody giữ kín, natural sampling, đủ source/error events; không phải TEST khóa | Chưa có target độc lập được phép và đủ support → BLOCKED |
| U nếu cần | Case/reviewers/rubric/consent/rights riêng, không làm lộ T trước freeze | Chưa có, RQ4 PENDING; T0 không xây viewer |

Custodian tương lai cần source registry gồm owner/license/version, site,
sequence/video, camera-session, acquisition/exposure, image checksum, GT version
và mức xác minh/unknown. Connected components liên kết nguồn đã kiểm cùng
duplicate review không được cắt qua H/D/V/T. Domain chỉ covariate. Thiếu map
không thể chứng nhận tách nguồn; không suy từ point ID/dHash hoặc bootstrap.

GT mới: rubric tương thích Level01–04, người có chuyên môn mù predictions,
đề nghị hai annotator độc lập và adjudication; exact reviewer/rights/agreement
criteria chờ O4/O5. Không dùng VLM làm GT, không sửa raw labels InspecSafe.
Custodian có quyền có thể cung cấp certificate overlap phù hợp mà không mở
TEST cho nhóm phát triển; khi chưa có thì giữ unknown, không tuyên bố độc lập.

## 9. False-safe và nguồn có đủ không?

Recount T0 hash-bound saved reports tìm **35 false-safe / 2.455 Qwen3-Normal**
trong 3.539 SUCCESS V4 gốc; 13 Level01, 22 Level02, 0 Level03. Phân bố false-safe
theo folder_domain: coal 1, metallurgy 1, oil_chemical 14, power 17, tunnel 2.
Nguồn độc lập chứa các sự kiện này **chưa xác định**. Đây là GT báo cáo lịch sử,
không adjudication ảnh mới. Số 38/14 của composite không dùng thay 35/13.

35 lỗi cho phép mô tả và thiết kế pilot, **không chứng minh đủ** học ranker hoặc
ước lượng gain xác nhận theo nguồn. Một ca làm capture toàn tập thay đổi
1/35 ≈2,86 điểm phần trăm; severe 1/13 ≈7,69 điểm; miền chỉ một lỗi nhảy
100 điểm. Đây là độ phân giải đếm, không CI/power. Chia nhỏ D/V/T chỉ làm ít
sự kiện hơn và không xóa exposure. 8 Level03 TRAIN không đủ hứa đánh giá rộng
về lớp hiếm.

Đối chiếu metadata của cùng TRAIN160 với V4 gốc có **148 SUCCESS/12
NOT_ATTEMPTED**, **67 Qwen3-Normal/4 false-safe**, trong đó 1 Level01; mỗi
error làm capture trên tập này nhảy 25 điểm phần trăm. Đây là saved-report
join đúng ID/hash, chưa chứng minh utility ba model/protocol tương đương,
không sửa trường `qwen_verified` rỗng trong manifest. Không dùng 30 false-safe
MiniCPM hoặc 2 false-safe InternVL làm số lỗi Qwen3.

**Feasibility verdict:** đủ căn cứ đặt câu hỏi và chuẩn bị development hồi cứu;
**BLOCKED cho thực nghiệm xác nhận/khẳng định cải thiện**. Chưa chứng minh đủ
nguồn, sự kiện độc lập, V/T kín, paired utility của panel hoặc precision.

| Blocker | Bằng chứng cần bổ sung để mở gate, không thực hiện trong T0 |
| --- | --- |
| B-DATA: độc lập nguồn | Cohort/source registry/rights/exposure/custodian và overlap certificate thích hợp; D/V/T assignment trước outcomes, không chia lại TRAIN để giả holdout |
| B-EVENT: đủ false-safe | Pilot D có quyền: số focal-Normal, FS/severe theo source, cỡ cluster và dependence; paired simulation cho b/delta/precision O5 với cả khoảng event rates, không extrapolate 35/N như prevalence mới |
| B-PAIR: paired utility | Ledger ID/image/config/run/status của Q3 + peers, mọi missingness và source; policy selection/series được duyệt; net gain/loss so single signal và one-peer trên D/V |
| B-SCORE: HNLO focal | Qualification native decision/candidates/logits/replay trên đúng protocol; thiếu chỉ chặn combo/score arm, không tự cấm label-only |
| B-SCOPE: khoa học/học vụ | O1–O5 và xác nhận giảng viên về CT1/đóng góp/negative route; review tài liệu không là approval |

O5 cần precision/power plan theo nguồn: giữ joint errors và missingness mọi arm
trong mô phỏng, đo cả gain/loss discordance, K bị mandatory chiếm, class support,
cluster imbalance và cost. Chọn số nguồn/sự kiện cần thiết từ độ rộng uncertainty
và minimum useful gain được chấp nhận. Hiện **chưa tính** cỡ mẫu/power hoặc đặt
min sources/events. Không có số ảnh nào tự bảo đảm đủ ý nghĩa.

## 10. Thí nghiệm E1–E5 đề xuất

Tất cả các hàng là NOT_RUN trong T0; chỉ mở sau quyết định/gate/quyền tương ứng.

| Yêu cầu | Thiết kế kiểm chứng/bác bỏ | Bằng chứng bàn giao sau này |
| --- | --- | --- |
| E1 trước/sau công bằng | Cùng P/S/C/F, Q3 output/config, batch/K; no-review/random/raw h/h-only learned/d-only/full; B* chọn D/V. Bảng signal và operational riêng, same tuning budget, cost thực | Số found/gained/lost, capture và uncertainty theo nguồn; false alerts/missed severe/missing/overload/cost, before=baseline queue, after=proposed queue, không sửa prediction |
| E2 bỏ thành phần | Full bỏ h; bỏ InternVL; bỏ MiniCPM; chỉ một peer; binary thay ordinal; không học so learned khi được phép | Hiệu quả biên từng peer/score, Δ/cost/missingness; không chỉ báo best subset hoặc chạy lại VLM cho ablation |
| E3 ca khó | Shared Normal sai, code-fence/INVALID, h null/service failure/overload; imbalance, severe/ít mẫu, domain/source shift; LODO D purge source liên quan; mapping/parser synthetic negative checks | Báo cả âm/undefined, worst-domain đủ support và mọi nhóm thiếu; challenge enrichment tách natural T, không crop/occlusion tự tạo GT |
| E4 lỗi | Ít nhất 3 nhóm và 3 ví dụ trước–sau: FS có tín hiệu peer; shared FS; focal đúng bị peer cảnh báo sai; thêm missingness nếu có | Rank/queue trước/sau ở K đã freeze, GT/provenance/source, examiner outcome nếu có; ca worse/unchanged phải hiện; nguyên nhân đã quan sát tách hypothesis |
| E5 tái lập | Exact Git/model/processor/tokenizer/config/env/prompt/parser/HNLO/seed, raw trước parse, checksums/run/attempt, planned ledger | Recompute từ saved outputs được phép, counts/queue/cost/CI/tests/deviations; giữ FAIL/INVALID/NOT_ATTEMPTED/series, không commit raw/ảnh/weights |

Negative evidence gồm peer không thêm utility, false alerts, shared misses và
ca không được review; không cần tạo vùng giả. Mapping synthetic checks chỉ
kiểm parser/token contracts, không chứng minh mapping thật đang sai. Nguyên
nhân model bỏ sót PPE/đối tượng cần ảnh và expert evidence, hiện chưa được suy ra.

CT3 nếu giảng viên yêu cầu sau này: task-based label-only vs evidence/queue
view, case tương đương, random/counterbalance thứ tự, tránh một reviewer xem
lại cùng case ở hai điều kiện; phân tích reader×case/source dependence. Đo đúng,
time và unsafe acceptance; không có reviewer/region GT thì usefulness/grounding
BLOCKED. Không làm giao diện hoặc user study trong T0.

## 11. Quyết định O1–O5 và câu hỏi giảng viên

Đây là **đề nghị nội dung cần chốt** đối với các ID O1–O5 trong kế hoạch cũ,
không phải đổi nghĩa quyết định đã duyệt. Tất cả năm hàng **PENDING**.

| ID | Owner/Research Lead cần quyết định | Nội dung cần giảng viên xác nhận / chứng cứ |
| --- | --- | --- |
| O1 | Tên và scope triage chính thay primary Macro-F1/four-peer proposal; empirical contribution/negative route | Capture false-safe có đáp ứng CT1/chuẩn Khóa luận không? Có chấp nhận không tăng nhãn focal, không kiến trúc mới, audit-only nếu thiếu T? |
| O2 | Protocol tương lai: primary combo vs B*, policy không học/learned, cohorts/queue/missingness/overload/metric families/freeze | Baseline/ablation E1–E5 và ranh giới error detection/classification/user utility; không bắt MiniCPM có score, không tự cộng thêm calibration/fusion |
| O3 | Q3 focal có điều kiện; exact hai peers/roles; rule giữ ba/giảm hai/STOP, caps và final selection trước T | Ba model có phù hợp phạm vi mới? Mọi thay đổi phải bằng quyết định riêng, không xóa roster Seminar hoặc ép đủ ba |
| O4 | Nguồn/rights/registry/GT/exposure/custodian và assignment D/V/T; tài nguyên annotate | Chấp nhận GT rubric và nguồn độc lập nào; hiện chưa có V/T đủ bằng chứng. Owner không cấp thay quyền bên thứ ba |
| O5 | b/delta/CI/precision/min sources-events/multiplicity/ties/seeds/cost/severe margins và stop rules từ pilot | Giá trị thực tế đủ ý nghĩa, nguồn lực examiner/GPU, kế hoạch uncertainty; 20%/10 điểm/95%/80% chỉ options chưa duyệt |

O6 run/data authority và O7 reviewers/user study trong kế hoạch cũ vẫn riêng;
T0 không cấp chúng hoặc tự mở O8/PR lịch sử. Sau quyết định thật mới ghi
append-only dưới docs/research/DECISIONS.md với người quyết định, nguồn, version,
phạm vi thay thế/điều kiện hiệu lực; task này **không sửa log quyết định**.

## 12. Mốc tiếp theo và dự phòng

1. Owner trình gói này, nhận câu trả lời O1–O5/CT1; chốt GO/NO-GO về scope và
   đường tiếp cận nguồn trước mở rộng hệ thống. Draft PR chỉ hoàn thành hồ sơ.
2. Nếu scope được chấp nhận: T1 kiểm quyền/nguồn/custody. Chưa có đường khả thi
   cho V/T độc lập → dừng xác nhận sớm, không chạy panel lớn để bù dữ liệu.
3. Khi có task/quyền riêng: bounded qualification/pilot trên D; khóa numerical
   feasibility từ source/events/cost. T3 paired development/ablation, final roster,
   rồi T4 freeze trước T5 target; T6 luận văn. Không khóa lịch tuần khi chưa biết
   nguồn/annotators/quota, không inference mới trong PR này.

**Nếu peers không đủ utility/coverage:** ưu tiên giảm một peer sau O3, hoặc
phương án dự phòng có điều kiện là **Qwen3 HNLO threshold cho hazard/Normal**:
so generated label với threshold-only chọn trên V tại FPR mục tiêu do O2/O5
duyệt; sang T báo FNR và FPR thực đạt theo miền, coverage/severe/cost. Calibration
chỉ thêm nếu đủ score/data và mục tiêu xác suất riêng. HNLO nhị phân không tự
giải quyết severity bốn lớp. Cần O1/giảng viên chấp nhận đóng góp hẹp trước T.

**Nếu không có dữ liệu độc lập:** cả hướng chính và dự phòng đều BLOCKED cho
xác nhận. Chỉ còn hồi cứu/audit/sensitivity với claim thu hẹp, cần chấp nhận
học vụ riêng; không đổi TRAIN thành holdout, mở TEST hoặc thu thập mới trong T0.

## 13. Bàn giao và trạng thái DONE

Hồ sơ gồm đề xuất này, evidence/reproduction note, JSON số gộp đã làm sạch và
PROJECT_STATE cập nhật. Kiểm tra ở evidence/PR; không sửa code thuật toán,
notebook, protected decisions/protocol/config hoặc dataset/split/labels.

**DOCUMENTATION_DONE** khi các kiểm tra và một Draft PR hoàn tất;
**SCIENCE_APPROVAL=PENDING**, **FINAL_ROSTER=PENDING**,
**CONFIRMATORY_FEASIBILITY=BLOCKED**. Không có hiệu quả/cỡ mẫu/CI thực nghiệm
mới được chứng minh từ việc hoàn thành T0. Dừng tại một Draft PR để ChatGPT
kiểm tra; không merge, tự phê duyệt hoặc chạy Kaggle/GPU/TEST.
