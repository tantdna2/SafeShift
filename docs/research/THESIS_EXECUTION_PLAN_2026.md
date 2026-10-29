# SafeShift — Kế hoạch thực thi Khóa luận tốt nghiệp 2026

Cập nhật thiết kế: **29/10/2026, Asia/Bangkok**; snapshot lịch sử 27/10 giữ nguồn riêng. Trạng thái: **PROPOSED — PENDING OWNER APPROVAL**.
Repository: [tantdna2/SafeShift](https://github.com/tantdna2/SafeShift).
BASE_SHA/merge-base sau tích hợp: `67fc1ffc9519e068072644e0f891932fed28f463`; BASE gốc `28fdf82512577f2ed0fb435fb2c12b88e82baf2f`; branch: `docs/thesis-execution-plan-20261027`.
HEAD ghi trong mô tả [Draft PR #137](https://github.com/tantdna2/SafeShift/pull/137) để tránh hash tự tham chiếu; cập nhật này tiếp tục cùng branch/PR.

**Owner đã quyết định bỏ học phần Seminar riêng và chuyển thẳng sang Khóa luận trong yêu cầu ngày 27/10. Điều đó không đồng nghĩa Owner đã duyệt phương pháp, metric, dữ liệu hay quyền chạy trong bản đề xuất này.** M1/M2 lịch sử giữ nguyên hiệu lực đúng phạm vi. Theo [chỉ thị Owner qua ChatGPT 29/10](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6486252968), thiết kế bốn VLM ngang hàng dưới đây là **PROPOSED — RESEARCH_LEAD/O1–O3/T0 DECISION_REQUIRED**. Nó thay bản đề xuất Q3 cố định + tối đa một auxiliary ở HEAD `6b7b3b9` để Owner xem xét; không thay quyết định khoa học lịch sử. Tất cả công thức/ngưỡng/feature mới chờ duyệt trước áp dụng. Tài liệu không sửa protocol/config đã khóa.

## 1. Executive Summary

Đề xuất một Khóa luận thống nhất: **đánh giá bốn VLM ngang hàng, kiểm tra chéo luân phiên và hợp nhất quyết định có cơ chế chuyển người kiểm tra**. Qwen3 là mốc có bằng chứng lịch sử, không được cố định vĩnh viễn làm predictor duy nhất. Ba vị trí còn lại chưa qualified; Gemma/Phi/Smol là danh sách Owner từng chọn khảo sát, không phải ba thành viên đã được tuyển.

Thiết kế có ba tầng dùng **cùng outputs/cohort**: (1) mỗi model tự phân loại Level01–04; (2) lần lượt mỗi model làm focal, ba model khác làm peers để đo khả năng phát hiện lỗi focal; (3) rule hợp nhất đơn giản và chính sách review, hai endpoint tách nhau. Bất đồng không phải ground truth. HNLO không bắt buộc cho cả bốn, không trung bình raw scores giữa model; chỉ dùng tại model có native alignment được duyệt.

Khuyến nghị giới hạn scope: không fine-tuning, không prompt search/weighted learned ensemble/model zoo. **Một primary contrast đề xuất:** Macro-F1 bốn lớp của strict-majority ensemble so với single-model mạnh nhất chọn trên development, trên cùng planned GT-valid cohort, tính abstain/INVALID vào false negatives (§6/§8). False-safe capture của bốn focal là secondary với multiple-testing control; không chọn focal/p-value đẹp trên target. Nếu ensemble không thắng, kết quả âm và cost/coverage vẫn là sản phẩm, không tự đổi primary sang triage.

CT1 có endpoint chất lượng nhãn trực tiếp; CT2 có rule/peer ablation và stress; CT3 là viewer có đánh giá người dùng khi đủ quyền/chuyên gia. Đây là **khả năng đáp ứng**, chưa có giảng viên xác nhận hoặc bằng chứng cải thiện. Rủi ro tăng từ một predictor + auxiliary sang bốn runs/mẫu, abstention, shared errors, false-safe ít, nguồn độc lập và nhãn chuyên gia vẫn là blocker. Không ép đủ bốn nếu qualification không đạt.

Phi a6 và Smol a2 đã chạy GPU thật nhưng NO_GO_FULL_TRAIN/HNLO=0; Gemma source audit BLOCKED. [Knowledge base và release gates](../KAGGLE_FAILURES_AND_RELEASE_GATES.md) giữ nguyên evidence/attempt, bổ sung CPU acceptance bằng builder/tests hiện có. CPU PASS không cấp grant hoặc dự báo model behavior.

Lộ trình duy nhất **T0 quyết định → T1 quyền/nguồn → T2 release qualification/pilot → T3 ba tầng development → T4 freeze → T5 target/error/user study → T6 luận văn**. #148 tuyển model còn ON HOLD đến sau review/audit/phê duyệt cần thiết; #147 diagnostic riêng, #136 không sửa ở task này. Không Seminar riêng, không đánh dấu M3/M4/M5 lịch sử hoàn thành.

## 2. Trạng thái thực tế và thẩm quyền

### 2.1. GitHub đã kiểm trực tiếp

Đã fetch `origin/main`, tạo worktree riêng từ BASE gốc trên, đọc metadata PR và toàn bộ discussion #133–#136 qua GitHub connector. Trạng thái này là snapshot ngày 27/10, phải kiểm lại ở task kế tiếp. Không dùng nội dung PR body cũ ghi “DRAFT” thay trạng thái API mới.

| Thành phần | Sự kiện đã xác minh | Phân loại / giới hạn |
| --- | --- | --- |
| [PR #133](https://github.com/tantdna2/SafeShift/pull/133) | MERGED 25/10, merge `bffc6032e65b38cb04b33520275a089d87d0d37f`; [hậu merge](https://github.com/tantdna2/SafeShift/pull/133#issuecomment-6399480255) | Hai tài liệu hướng/Master Plan; merge tài liệu không phải bằng chứng triage thành công. |
| [PR #134](https://github.com/tantdna2/SafeShift/pull/134) | MERGED 26/10, merge `a425ab04695319a42bfdd2f89192717dddbb891b`; [hậu merge](https://github.com/tantdna2/SafeShift/pull/134#issuecomment-6406526361) | Execution Plan và PROJECT_STATE; [Owner directive](https://github.com/tantdna2/SafeShift/pull/134#issuecomment-6406751802) là nguồn M1. |
| [PR #135](https://github.com/tantdna2/SafeShift/pull/135) | MERGED 26/10, merge = BASE gốc; [hậu merge/giao M3](https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6409830030) | M1 EFFECTIVE cấp dự án; M2 v1 FROZEN theo quyết định + SHA + hậu merge. Không có chữ ký học vụ hoặc quyền Khóa luận. |
| [PR #136](https://github.com/tantdna2/SafeShift/pull/136) | OPEN/DRAFT, chưa merge; HEAD `b252e4cd469346c781183c69bad481ad9b69eff9`; 10 files, +2219/-230 | M3 IN_PROGRESS; [audit FAIL được đối chiếu](https://github.com/tantdna2/SafeShift/pull/136#issuecomment-6412563251). 77 tests là báo cáo local trong PR, không được nhận là kiểm toán độc lập hoặc test của task này. |
| Foundation V1 và saved-score tooling | Có trên main: records/validation/exact join, confusion, weighted AUROC, source-sensitivity CLI, transport interface | Tại snapshot 27/10 chưa có backend/raw writer hoàn chỉnh; xem cập nhật 29/10 bên dưới. Trên main mới vẫn chưa có thesis ensemble/triage/viewer engine hoàn chỉnh. [Kiến trúc](../ARCHITECTURE.md) và module hiện hữu đã đối chiếu. |

Lỗi #136 chưa được ghi nhận sửa ở HEAD đã kiểm: R4 hiểu path chứa `|`/`->` sai thành cặp model, tạo planned_n=0 và exclusions âm; R3 missing_composition lấy M224 nhưng metadata ghi T3763/success IDs; thêm lỗi không blocking ở eligibility/model của ô HNLO true×predicted. Đã đọc trực tiếp [report_rows tại exact HEAD](https://github.com/tantdna2/SafeShift/blob/b252e4cd469346c781183c69bad481ad9b69eff9/scripts/analyze_seminar.py), thấy các nhánh mapping tương ứng; không chạy counterexample hoặc tự nhận audit độc lập mới. Đây là **lỗi bằng chứng hàng báo cáo**, không chứng minh công thức HNLO sai. Task này không sửa/đóng/merge/rebase PR đó.

**Cập nhật 29/10:** main `67fc1ffc9519e068072644e0f891932fed28f463` đã có prep/storage/runtime #138–#142, Phi end-to-end #144 và Smol readiness #146. Backend/raw custody/loader/rehearsals này phải được tái sử dụng, không viết pipeline trùng. Phi a6/Smol a2 receipts là bằng chứng GPU có giới hạn (§10), không kết quả target thesis. #147 diagnostic mở; #148 tuyển mới ON HOLD. #137 đã tích hợp main bằng merge commit thông thường theo [quyền ChatGPT](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6487634755), chỉ conflict PROJECT_STATE; giữ facts main và thesis PROPOSED. Kiểm thử và wrapper phải chạy lại **exact integrated HEAD**; SHA/parents/receipts thật ghi PR body, không dùng kết quả trước tích hợp thay thế. Sources/attempts chi tiết ở [failure knowledge base](../KAGGLE_FAILURES_AND_RELEASE_GATES.md).

### 2.2. Bằng chứng nghiên cứu thật, kế hoạch và giả thuyết

Nguồn số liệu là [RESULTS_AND_LIMITATIONS](../RESULTS_AND_LIMITATIONS.md), [receipt #131](../SOURCE_FEASIBILITY_RECEIPT_20261024.json), [direction lock](SEMINAR_THESIS_DIRECTION_LOCK_20261025.md). Chỉ đối chiếu tài liệu/receipt Git, không đọc payload, tính lại score hay raw replay trong task này.

| Đối tượng | Bằng chứng kế thừa | Không được suy ra |
| --- | --- | --- |
| InspecSafe TRAIN | 3.763 ảnh; 749 Anomaly/3.014 Normal; Level01/02/03/04 = 490/251/8/3.014 | TRAIN độc lập; số site/camera độc lập; nhãn vùng nguy cơ đầy đủ. |
| Qwen2.5 | 3.763 SUCCESS; HNLO AUROC 0,8266558463706973; raw CPU Linux audit lịch sử PASS, còn giới hạn outer receipt/1-ULP | Raw audit mới hoặc ngưỡng đã hiệu chuẩn. |
| InternVL3 | 3.763 saved scores; AUROC 0,8861824613751756 | Raw-logit audit đầy đủ. |
| Nhãn Q25/IVL3 | Cả 3.014 Normal bị sinh nhãn Anomaly; accuracy bốn mức 130/3.763 và 164/3.763 | Đã biết nguyên nhân là mapping sai; phải phân biệt parser/token/prompt/priors. Cũng chưa chứng minh disagreement hằng trong mọi ca Q3-Normal. |
| Qwen3 V4 gốc | 3.539 SUCCESS/3.763 planned, 1 TECHNICAL_ERROR/223 NOT_ATTEMPTED; 700 A/2.839 N; AUROC 0,9527927338600111 | Đủ 3.763 nhãn; raw PASS; số 38 false-safe hoặc 14 severe của composite là số V4-only. |
| Common V3539 | Q25/IVL3/Q3 AUROC 0,8243818245861219 / 0,88286846475117 / 0,9527927338600111 | Ưu thế thống kê, transfer hoặc error-detection performance. |
| Recovery224 | 224 SUCCESS, 49 A/175 N, cohort/config riêng | Pool với V4 hay lấy trung bình hai AUROC. |
| Moondream2 | Có CPU/interface evidence lịch sử; HNLO TRAIN tương thích chưa có | Bị loại roster, bất khả thi kỹ thuật, hoặc N/A Seminar tự áp cho Khóa luận. |
| Source/CI | Receipt: source identity chưa xác minh, chưa CI; exact/point/family sensitivity không là source registry | Năm folder_domain là năm nguồn độc lập; bootstrap ảnh giải quyết phụ thuộc. |
| Logistic, threshold, viewer | Chưa có kết quả xác nhận trong repo | Đã tăng chất lượng, đã giảm false-safe hoặc hữu ích cho người dùng. |

### 2.3. Quyết định còn hiệu lực

[DECISIONS](DECISIONS.md) và hậu merge #135 xác định hiệu lực dù protocol/config giữ nguyên chữ PENDING và `frozen=false` của snapshot trước duyệt. Hai file bất biến:

- `docs/research/SEMINAR_PROTOCOL.md`: SHA-256 `54c5be6b67e768f8d4819193c5d06867edf02e2008db258731f6e5947ed06dc1`.
- `docs/research/seminar_analysis_config.v1.json`: SHA-256 `dd3b86660f0795dba099abac0d8a3b8bd3498e625e49b128aa9c50e72639e5ff`.

M1 successor thay đúng phần đã duyệt của D9R22; không sửa DEC-PA3-011 lịch sử PROPOSED. B01 12 atoms/7 nhóm BLOCKED, B02 continuous controls N/A, B03 provenance hạn chế, B05 mismatch/proxy BLOCKED vẫn tồn tại. Bảng bốn model giữ nguyên. Quyền M3 chỉ CPU + fixtures tổng hợp; không suy sang artifact M4, annotation, GPU hoặc target. Bản kế hoạch này không kế thừa grant run cũ.

Root ROADMAP/TASKS của workspace cũ đã được kiểm tra khi bắt đầu; main mới không có chúng. Theo AGENTS hiện hành, dùng docs/ROADMAP và docs/EXECUTION_PLAN, không nhập lại legacy. Các dòng premerge trong README/ROADMAP/EXECUTION_PLAN là snapshot cũ, được diễn giải bằng receipt GitHub; Phạm vi #137 nay gồm kế hoạch, PROJECT_STATE, knowledge base và CPU wrapper/tests theo chỉ thị 29/10; không sửa các điều hướng/protocol cũ.

## 3. CT1–CT3 và E1–E5 trong thiết kế ngang hàng

| Yêu cầu | Thiết kế đề xuất | Điều kiện và ranh giới claim |
| --- | --- | --- |
| CT1 chất lượng | Bốn single baselines cùng cohort; primary ensemble vs strongest single, Macro-F1/BA, severe/false-safe/abstain và domain CI | Chất lượng nhãn khác review capture. Threshold/calibration là nhánh optional khi score đủ bằng chứng, không ép mọi kỹ thuật |
| CT2 phương pháp | Strict-majority có abstain; focal rotation với ordinal/binary peer signals; bỏ từng peer/model, LODO có purge source | Voting/disagreement không mới tự thân; đóng góp thực nghiệm có đối chứng, novelty cần O1/giảng viên; không dùng model dự đoán làm GT |
| CT3 chức năng | Case viewer hiện bốn nhãn, focal/peers, ensemble/abstain/review, nguồn chứng cứ và confidence chỉ khi calibration hợp lệ | Không bịa vùng/reason; ≥3 tác vụ/nhóm lỗi và user study riêng. Thiếu expert/rights → usefulness BLOCKED |
| E1 công bằng | Cùng planned IDs/GT/source/batch; joint complete-case panel + toàn planned; same review budget và reported full four-model cost | Không so subset dễ hơn do model missing; single không phải chịu tiền ba peers trong operational panel |
| E2 ablation | Single best, four-vote, bốn leave-one-model-out rules; focal ordinal vs binary vs random; HNLO-only/combo chỉ khi qualified | Group CV/fit budget công bằng nếu learned diagnostic được duyệt; ablation không chọn winner bằng target |
| E3 stress | Imbalance/prevalence, source/domain shift, rare severe/khó, shared mistakes, one peer missing, ties/abstain/overload | Challenge/enriched set tách target tự nhiên; báo âm, null và mất coverage |
| E4 errors | False-safe/severe, false alarm/severity, shared error/unsupported evidence; ≥3 case trước–sau thật kể cả worse/unchanged | Có GT/provenance, nguyên nhân quan sát khác giả thuyết; triage chưa là sửa lỗi |
| E5 tái lập | Commit/env/model+processor revisions/prompt/parser/seed/config/raw-before-parse/checksum/run/attempt/CLI | G0–G6 notebook + receipt, toàn attempts/skips/failures; không raw/weights/private IDs vào Git |

Mọi metric/estimand/ensemble/review rule mới ở đây **chờ O2**, không sửa M2 hoặc thresholds của pilot đã chạy. CT1 không đòi calibration bằng mọi giá, CT2 không đòi ensemble learned, CT3 không mặc định grounding algorithm.

## 4. Lựa chọn thiết kế và đánh đổi

| Trục | A: calibration/ngưỡng một predictor | B cũ: Q3 cố định + auxiliary | Thiết kế khuyến nghị để Owner xét: bốn peers + hợp nhất/review | C độc lập: evidence audit |
| --- | --- | --- | --- | --- |
| Câu hỏi | Score tốt nhưng label kém có sửa được không? | D thêm utility so HNLO-Q3 không? | Bốn model tự phân loại, peer information và rule hợp nhất có giá trị hơn single mạnh nhất không? | Label đúng nhưng evidence sai/thiếu có phát hiện được không? |
| Tính mới | Kỹ thuật chuẩn, đóng góp domain/protocol | Logistic/disagreement chuẩn; conditional hazard ranking | Voting/focal rotation chuẩn; đóng góp paired empirical study về reliability/abstention/cost/shift, không kiến trúc mới | Audit/faithfulness đã có; cần expert evidence labels, không tự novel vì UI |
| CT1–CT3 | CT1 trực tiếp, CT2 bounded, CT3 cần viewer | CT1 phụ thuộc chấp nhận review endpoint; CT2 rõ | CT1 label trực tiếp + triage phụ tách; CT2 ablation; CT3 viewer dùng outputs chung | CT3 trực tiếp; không mặc định CT1 gain |
| Dữ liệu | Score native/GT V/T có nguồn | GT và đủ Q3 false-safe, D biến thiên | GT bốn lớp/support/nguồn, paired outputs cả bốn, nhiều focal errors; source CV/target custodian | Nhãn evidence/region/reviewers và quyền ảnh |
| Tái dùng | Q3 saved score chỉ historical | Q3/Q25/IVL3 motivation và code provenance | Foundation, pilot builders/tests/receipts, failure KB; không lấy Phi/Smol NO_GO làm qualified peers | Provenance/raw writer + review concepts |
| Compute/độ rộng | Thấp nhất nếu score đã có quyền | Q3 N + auxiliary trên C, vừa | Khoảng 4N calls/full panel, sequential peak mỗi model; cached outputs dùng cả ba tầng; rủi ro cao hơn B | Human annotation là nút thắt; crop/counterfactual ngoài core |
| Controls | Threshold-only vs calibrated; same V | HNLO/D/full cùng E,b | Strongest single dev, majority, leave-one-out, random/peer-only, cost/missing panels | Label-only vs evidence view cùng tasks |
| Leak/confound | Chọn threshold trên target | Focal selection/exposed TRAIN | Search trên nhiều model/focal, shared data errors, abstain che lỗi, subset drift, multiple testing | Model reasons dùng làm nhãn chuẩn, memory/carryover study |
| Kết quả âm | Operating point/limits | D không thêm; HNLO-only rẻ hơn | Không đủ bốn hoặc ensemble thua → feasibility/negative result và xin scope giảm | Evidence unavailable/không usefulness → rubric/demo hạn chế |

**Khuyến nghị có điều kiện:** nghiên cứu ngang hàng ba tầng với **một rule hợp nhất cố định, một primary**, CT3 nhỏ; không cộng cả A+B+C thành ba đề tài. Nó phù hợp hơn với ý định Owner mới và kiểm trực tiếp CT1, nhưng chưa có bằng chứng khoa học tốt hơn hay chắc hoàn thành hơn B cũ. O1 phải xác nhận đủ chuẩn học vụ và chấp nhận negative-result route; T1/T2 phải NO-GO sớm nếu không đủ nguồn/quota/models. A/B cũ là phương án giảm scope cần quyết định mới, không fallback âm thầm sau thấy target.

## 5. Literature review có mục tiêu và ranh giới tính mới

### 5.1. Phạm vi, cách tìm và mức tiếp cận

Kế thừa §3 của [direction lock](SEMINAR_THESIS_DIRECTION_LOCK_20261025.md) và điều kiện audit #133, chỉ kiểm nguồn có khả năng đổi lựa chọn A/B/C. Đây là **narrative update một người thực hiện**, không systematic review/PRISMA, không chứng nhận exhaustive hoặc “chưa ai làm”. Dùng web search để tìm, đọc nguồn sơ cấp tại arXiv, ICLR/NeurIPS/PMLR và ACL; không dựa bài tổng hợp bên thứ ba. Không cài/chạy code paper.

Nhật ký truy vấn ngày 27/10/2026 (giữ nguyên chuỗi để lặp lại; search engine có thể đổi thứ tự kết quả):

| Truy vấn | Quyết định sàng lọc |
| --- | --- |
| `"Revisiting Confidence Calibration for Misclassification Detection in VLMs"` | Giữ LMN; OpenReview gặp browser challenge, đọc PDF proceedings ICLR thay thế. |
| `"TrustVLM" prediction trustworthiness` | Giữ arXiv v3, kiểm Methods §3.3; không chỉ dựa abstract phiên bản cũ. |
| `"It Is Not Seeing the Hazard" vision language` | Giữ preprint và đọc protocol/limitations; không ngoại suy kết quả mô phỏng sang InspecSafe. |
| `vision language model evidence auditing correct answer wrong reason industrial hazard 2026` | Sàng lọc evidence-audit; loại kết quả không đúng VLM/công nghiệp khỏi cơ sở quyết định. |
| `site.proceedings.neurips.cc "Can You Trust Your Model's Uncertainty" dataset shift` | Giữ Ovadia làm nền tảng shift. |
| `site.openaccess.thecvf.com vision language "right" "wrong reasons" grounding` | CRG là ứng viên; ECVA full PDF timeout, không dùng kết quả định lượng/khẳng định full-text review. |
| `site.arxiv.org VLM disagreement selective prediction ensemble 2026` | Giữ ATS; theo citation đến ReCoVERR. Các ensemble thiên văn/selection khác task không là baseline bắt buộc. |

Đọc trực tiếp thêm nguồn đã có trong repo: InspecSafe publisher, Guo/PMLR, Geifman/NeurIPS, ConfBench. Phân biệt bản preprint và venue; không đếm preprint/proceedings của cùng công trình là hai nghiên cứu. Không dùng con số của paper làm prior hiệu quả SafeShift. World Models in Words chỉ kiểm abstract/metadata; có macro chưa render trong abstract, không sử dụng các số chưa kiểm hoặc chọn làm baseline cốt lõi.

### 5.2. Các công trình làm thay đổi ranh giới đóng góp

| Nguồn sơ cấp / mức đọc | Đã làm gì | SafeShift khác ở đâu; điều không còn mới; câu hỏi còn kiểm chứng |
| --- | --- | --- |
| [InspecSafe, Scientific Data 2026](https://www.nature.com/articles/s41597-026-07796-x), Data Records/Technical Validation | Benchmark kiểm tra công nghiệp với nhãn mức và annotation đa dạng | Industrial VLM/task/dataset không mới. Nguồn/mapping thực trong bản local phải theo audit; paper không xác nhận source independence của cohort SafeShift. |
| [Guo et al., ICML 2017](https://proceedings.mlr.press/v70/guo17a.html), metadata/abstract | Temperature scaling là post-hoc calibration đã có | A không mới vì dùng temperature. Cần kiểm performance/shift và threshold; calibration không đồng nghĩa tăng khả năng bắt lỗi. |
| [Geifman & El-Yaniv, NeurIPS 2017](https://papers.nips.cc/paper_files/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html), abstract; thiết lập kế thừa repo | Selective classifier giữ predictor và đánh đổi risk–coverage | Reject/review và risk–coverage đã có. Không chuyển bảo đảm của thiết lập paper sang nguồn công nghiệp phụ thuộc. |
| [Huang et al., LMN, ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/file/5393eaf0b723278738788520ec54e4b4-Paper-Conference.pdf), §4.3 và thiết lập | Meta network dùng logits, image/predicted-text embeddings để học temperature theo mẫu cho MisD | Đầu nhẹ trên frozen VLM không mới. CLIP logits/embedding không tương đương HNLO token generative; LMN chỉ baseline khi đủ contract/input. Không coi kết luận lý thuyết paper là định lý về HNLO. |
| [Dong et al., TrustVLM](https://arxiv.org/html/2505.23745v3), v3 16/10/2026, Methods §3.3 | Kết hợp image–text score với image–image similarity/prototypes để đánh giá trust | “Frozen VLM + thêm score” không mới. B kiểm D giữa generative models và e_FS; không nhận vượt TrustVLM nếu chưa chạy tương thích và cùng ngân sách nhãn/compute. |
| [Roy et al., ConfBench](https://arxiv.org/html/2608.01792v1), preprint 2026, metric/Appendix A.7 | Phân biệt calibration với error ranking, đo bắt lỗi ở review budget | Capture tại budget cố định đã có. SafeShift khác endpoint false-safe/nguồn công nghiệp và chi phí auxiliary; không mượn budget paper. |
| [Tetteh & Fleming](https://arxiv.org/html/2610.09517v1), preprint 2026, protocol/controls/limitations | Kiểm safety score bằng caption/viewpoint/geometry controls, gồm generative scorer | Token score không tự chứng minh hazard validity. B chỉ claim utility xếp hàng; C dùng evidence audit để phát hiện giới hạn, không chứng minh causal perception. |
| [Ovadia et al., NeurIPS 2019](https://proceedings.neurips.cc/paper_files/paper/2019/hash/8558cb408c1d76621371888657d2eb1d-Abstract.html), abstract | Benchmark uncertainty dưới dataset shift; post-hoc calibration có giới hạn | Không hứa global threshold/calibration chuyển miền. Đánh giá worst-domain/source bắt buộc; không suy ensemble luôn tốt. |
| [Srinivasan et al., ReCoVERR, ACL Findings 2024](https://aclanthology.org/2024.findings-acl.767/), PDF §2–3 | Thu thập chứng cứ qua hỏi thêm để giảm abstention, có confidence/relevance/entailment | Evidence-guided selection đã có. Viewer SafeShift không tái lập cơ chế này; nhiều call/VLM–LLM mới vượt scope, chưa có so sánh thực nghiệm. |
| [Yu, Niu & He, ATS](https://arxiv.org/html/2608.19807v1), preprint 2026, Methods | Giữ câu trả lời, gom tín hiệu hành vi/can thiệp để accept/reject; chỉ agreement có thể bỏ sót stable-but-wrong | Giới hạn tính mới của B/C mạnh hơn chỉ “thêm disagreement”. B phải kiểm shared errors và thêm ích lợi so HNLO; ATS là reasoning số, không trực tiếp nhãn an toàn bốn mức. |

Cập nhật 29/10: bảng literature trên giữ đối chiếu A/B/C từ lần review 27/10; các câu nói B chỉ policy review mô tả phương án cũ, không endpoint H1 mới. Suy luận áp dụng cho thiết kế ngang hàng: đóng góp khả thi là **paired empirical evaluation của phân loại, peer checking và một rule hợp nhất**, với dữ liệu/nguồn/coverage/cost và đối chứng mạnh; majority vote và disagreement tự thân không mới. Không đủ cơ sở hứa kiến trúc mới, causal grounding, uncertainty calibrated hay vị trí SOTA. Cần giảng viên xác nhận đóng góp thực nghiệm như vậy đủ chuẩn Khóa luận (O1). Không tuyên bố survey toàn bộ peer ensemble; ranh giới novelty cần audit khoa học, không mở tuyển #148 trong task này.

### 5.3. Skill thực sự dùng

Đã truy cập và đọc SKILL.md của `literature-review` v1.11 (phạm vi/tìm kiếm/nguồn sơ cấp), `experimental-design` v1.5 (đơn vị nguồn, paired controls, blocking, reviewer study), `scientific-critical-thinking` v1.5 (confounding, missingness, claim/estimand). Không thấy skill Review Agent trong catalog khả dụng và tìm kiếm local; không dùng agent review hoặc nhận tự rà soát là audit độc lập. Không cài skill mới, không dùng slide/image skills, không chạy script skill bên thứ ba; không có statistical-power skill được dùng và không báo power đã tính.

Ghi công phương pháp theo yêu cầu các skill: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065). Metadata kiểm trên arXiv ngày 27/10: bản hiện hành v2, 02/09/2026; dùng DOI không suffix. Skill giúp cấu trúc công việc, không là bằng chứng kết quả SafeShift.

## 6. Phương pháp thống nhất ba tầng — PROPOSED

### 6.1. Tên, phạm vi và đóng góp dự kiến

**Tiếng Việt:** “SafeShift: Đánh giá phân loại, kiểm tra chéo và hợp nhất quyết định của bốn mô hình ngôn ngữ–thị giác trong nhận diện nguy cơ an toàn công nghiệp”.

**English:** “SafeShift: Evaluating Classification, Cross-Model Checking and Decision Fusion of Four Peer Vision–Language Models for Industrial Hazard Recognition”.

Đối tượng sử dụng: người kiểm tra an toàn, Research Lead/reviewer; chưa là hệ thống tự xác nhận an toàn. Đóng góp dự kiến: paired benchmark có source/coverage/chi phí; phép kiểm rule hợp nhất vs strongest single; phân tích complementary/shared errors bằng focal rotation; viewer và gói tái lập. Tất cả là **dự kiến**, không claim thuật toán mới, lỗi độc lập hoặc improvement đã đạt.

### 6.2. RQ và hypotheses

| ID | Câu hỏi / giả thuyết đề xuất | Bằng chứng bác bỏ / giới hạn |
| --- | --- | --- |
| RQ1 / H1 PRIMARY | Strict-majority bốn peers tăng Macro-F1 bốn lớp trên planned GT-valid so single mạnh nhất đã chọn D/V ít nhất δ_F, đồng thời thỏa false-safe/abstain/cost guardrails | Lower CI Δ không vượt δ_F, guardrail fail/undefined hoặc ensemble thua; không thay H1 sau target |
| RQ2 / H2 SECONDARY | Với từng focal m, peer rank phát hiện thêm false-safe so random và HNLO-only nếu hợp lệ, cùng E_m/M_m/K | Peer signal hằng/shared errors, CI rộng, thiếu events, cost lớn; không lấy focal tốt nhất làm primary |
| RQ3 / H3 SECONDARY | Lợi ích/giới hạn thay đổi thế nào theo source/domain/imbalance/missingness? | Worst-domain undefined/shift harm; không suy robustness mọi miền |
| RQ4 / H4 SECONDARY | Viewer evidence giúp examiner đúng hơn hoặc giữ độ đúng và giảm thời gian theo một criterion định trước | Unsafe acceptance/time tăng, thiếu reviewers/evidence; satisfaction không thay utility |

Một H1 confirmatory contrast. Bốn H2 là family được khóa; Holm nếu kết luận xác nhận hoặc exploratory rõ ràng. H3/H4 có family riêng định trước; không chọn p-value nhỏ nhất trong focal/budget/metrics. O5 chốt δ_F/margins và precision trước target. HNLO hazard AUROC lịch sử không chứng minh bất kỳ H nào trên source mới.

### 6.3. Tầng 1: mỗi model là một classifier độc lập

Tập model đề xuất F={m1,m2,m3,m4}, m1 dự kiến Qwen3 mốc lịch sử; m2–m4 chờ qualification/tuyển sau #148. Cả bốn có quyền làm focal; không có model chính vĩnh viễn. Q25/IVL3/Moondream2 vẫn roster lịch sử, không tự loại/thay trong M1/M2. Chưa có final thesis roster được duyệt. Pin model/processor/tokenizer/code/env/dtype/attention/preprocess/generation/prompt/parser riêng từng model; cùng nội dung nhiệm vụ/nhãn, native template khác phải ghi rõ.

Mỗi sample planned phải có record cho mỗi model: canonical Level01–04 hoặc INVALID/TECHNICAL_ERROR/NOT_ATTEMPTED. Không lấy chữ Level từ prose/JSON hỏng để rescue. Bảng độc lập: confusion 4×5, counts từng failure type, support/recall/Macro-F1/BA, false-safe/severe, domain/source, cost/coverage. Predictor output không bị peers ghi đè. Qualification cho classification khác score: HNLO_m chỉ dùng sau native decision-step/prefix/candidate/logit/replay đã được review; không suy từ raw logits có sẵn, không ép đủ HNLO bốn model.

### 6.4. Tầng 2: kiểm tra chéo luân phiên và review

Đề xuất peer signals không học cho mỗi focal m: `D_ord,m = sum(j != m, abs(level_m-level_j))/9`, với Level01=1,…,Level04=4; `D_bin,m = sum(j != m, hazard(label_m) != hazard(label_j))/3`. Đây là công thức **mới chờ O2**, không là D_ord lịch sử Q3/Q25/IVL3 hoặc D_j một auxiliary. Trong focal-Normal, D_ord,m chỉ là tổng severity của ba peer labels; không là bằng chứng độc lập rằng focal sai. D_bin có thể hằng dù ordinal thay đổi; phải đo cả hai.

Trong mỗi batch P được khóa trước outcomes, N=n(P):

| Tập | Định nghĩa GT-blind / quy tắc |
| --- | --- |
| L_m | Focal có canonical label; O_m có raw output, INVALID khác no-output |
| C_m | L_m với focal=Level04; error e_FS,m chỉ khi GT hazard, severe khi GT Level01 |
| M_m | Focal INVALID/no-output/technical failure; cộng C_m thiếu bất kỳ peer label cần cho rule. Không fill Normal, không giảm mẫu số peers từ 3 xuống 2 |
| E_m | C_m trừ M_m, đủ ba peer labels; supervised metrics thêm GT-valid mask, báo riêng exclusions |
| K / k_m | K=floor(b*N), k_m=min(n(E_m),max(0,K-n(M_m))); b trên toàn planned, không trên C_m |
| Review R_m,a | M_m cộng top-k_m E_m theo arm a; n(M_m)>K là OVERLOAD, không claim same-budget feasibility |
| Ties | Opaque-ID hash+seed khóa, chung arms, không filename/GT; tie-block sensitivity theo rule định trước |

Mỗi focal là **một kịch bản vận hành riêng**, không cộng bốn queues rồi giả workload chỉ K. Báo full four-model cached diagnostic cost và thực tế single vs four; nếu muốn một queue hợp nhất cần protocol riêng, ngoài core. Batch theo verified source component; cross-source batch nếu bắt buộc phải khóa dependence/CI; không tái chia target để lợi metric. Không dùng unused budget cho ca khác universe rồi tính như bắt thêm false-safe.

Arms bắt buộc: random E_m (seeds định trước), raw D_ord,m, raw D_bin,m; no-review/all-review chỉ mốc biên. HNLO_m-only thêm **khi có native qualification**; paired comparison score-vs-peer dùng E_m,H đủ cả score và labels với cùng mandatory set, báo mất coverage. Logistic L2 hai feature (HNLO_m,D_ord,m) chỉ sensitivity được O2 duyệt nếu source/events đủ; fit/standardize trong grouped CV, bounded grid chung learned controls, không đưa GT/ID/domain prevalence target vào features. Không bắt learned arm để đủ bốn focal. HNLO unqualified → N/A, không làm model mất tư cách classification; không textual confidence thay score.

### 6.5. Tầng 3: rule hợp nhất và người kiểm tra

**Rule chính đề xuất, chờ O2:** chỉ khi đủ bốn nhãn hợp lệ và có một label đạt strict majority (≥3/4) mới phát nhãn ensemble; các 2–2, 2–1–1, 1–1–1–1 và thiếu output → **ABSTAIN**. Không favor Normal, không severity tie-break hậu nghiệm, không reduced-denominator vote khi peer missing. ABSTAIN là trạng thái quyết định, không thêm nhãn dataset. Record ensemble riêng; raw bốn model giữ bất biến. Missing/INVALID/tie reasons tách dù confusion gộp vào cột không phân loại.

Single comparator m* chọn trên development/validation theo **cùng planned Macro-F1** và guardrails/coverage, tie theo cost rồi fixed model-ID order chốt trước. Không mặc định Qwen3 thắng. Final m*, ensemble rule và mọi threshold/roster đều freeze T4; không fit/select lại target. Rule có thể thất bại vì abstain quá nhiều: đó là negative result hợp lệ, không đổi sang plurality/weighted voting sau kết quả.

Ablation bắt buộc: bốn leave-one-model-out strict-majority rules (đủ ba nhãn, ≥2/3; còn lại abstain); báo label-change, coverage và cost. Đây là ablation về information+quorum thay đổi có chủ đích, không tách thuần architecture causality. So all single models, full ensemble, leave-one-out; không biến 15 subsets thành search vô hạn. Calibration/threshold đơn model chỉ diagnostic khi được O2 duyệt và native scores đủ, chọn trên V; temperature/monotonic calibration không mặc nhiên tăng ranking.

Ensemble ABSTAIN phải hiển thị NEEDS_HUMAN_REVIEW/UNRESOLVED, không phát quyết định an toàn. Báo riêng workload bắt buộc n(ABSTAIN)/N; nếu vượt K thì OVERLOAD cho kịch bản ensemble, không giả người đã xử lý hoặc gộp vào bốn focal queues để giữ budget K. Ngoài việc xử lý abstain, một queue rank cho chính ensemble cần protocol riêng, không thuộc primary hiện tại.

Viewer chọn rõ kịch bản focal hoặc ensemble, hiển thị nhãn từng model, focal/peers, ensemble nhãn/abstain, ranking/review action và evidence provenance. Triage chuyển người xem không tự sửa nhãn hoặc tạo GT. Chất lượng nhãn ensemble, capture lỗi focal và quyết định người dùng là **ba output/endpoint riêng**.

## 7. Dữ liệu, nhãn, source và điều kiện xác nhận

### 7.1. Bốn vai trò dữ liệu

| Vai trò | Dữ liệu dự kiến / quyền còn thiếu | Dùng được / không dùng được |
| --- | --- | --- |
| H — lịch sử | Saved TRAIN T3763/V3539, REC224 riêng; chỉ docs/receipt được đọc hiện tại | Motivation/giới hạn; reanalysis cần grant artifact. Không target, không tự lấy composite để fit. |
| D — development/pilot | TRAIN đã phơi nhiễm sau quyền và/hoặc cohort công nghiệp mới được duyệt | Fit/feature diagnostics, grouped CV, cost/event pilot. TRAIN CV luôn exploratory dù chia lại. |
| V — validation/calibration | Nguồn mới tách D, độc lập với target; custodian phân bổ trước kết quả | Chọn threshold/fit calibrator và kiểm routing; không fit lại feature/model sau thấy V rồi gọi V xác nhận. Với calibration+threshold dùng V-cal/V-select tách nguồn hoặc cross-fit nội bộ đã khóa. |
| T — target xác nhận | Cohort mới nguồn tách D/V và lịch sử H, nhãn chuẩn tương thích, custodian giữ kín | Một lượt pipeline đã freeze; không chọn feature, b, δ, ngưỡng hay nguồn theo lỗi. InspecSafe TEST vẫn đóng. |

Dataset mới là **manifest nghiên cứu bổ sung chờ O4**, không đổi dataset/split/nhãn InspecSafe. Không mặc định SteelBench/MVTec/VisA là tương đương hazard severity. Nếu không chứng minh nguồn T tách H, chỉ gọi là “cohort bổ sung, independence unverified”; NO-GO cho claim source-independent. Không truy tìm ảnh TEST để xác minh: custodian có quyền cung cấp certificate/projection thích hợp, hoặc giữ giới hạn.

### 7.2. Nguồn, sampling và leakage

Registry phải gắn sample với site, video/sequence, camera/session, ngày thu thập, owner/license, checksum, exposure role và mức source-verified/unknown. Lấy connected components của **liên kết nguồn đã xác minh** và exact/near-duplicate review để phân vai trò; nhóm liên quan không cắt qua D/V/T. Domain là covariate, không đơn vị độc lập. Point/family/dHash chỉ dùng screening/sensitivity, không tự thành source identity. Nếu nhiều camera cùng site/video có phụ thuộc, đơn vị cluster là cấp cao nhất có căn cứ; ghi lý do.

Custodian lập phân bổ theo nhóm trước inference, stratify theo domain và thông tin hợp pháp được định trước, không theo score/lỗi bất kỳ focal/ensemble target. Các ca “khó” chọn từ điều kiện ảnh/nhãn do expert định trước, không chỉ cherry-pick misses. Nếu dùng enrichment theo nguy cơ để tăng events, tách challenge set khỏi target tự nhiên; chỉ claim prevalence thực khi có sampling probabilities/weights đã duyệt. Không gộp challenge vào AP/capture chính.

LODO trên D bỏ toàn bộ domain giữ lại **và mọi source component liên quan** khỏi fit/preprocessing/tuning. Nếu một source trải nhiều domain, purge cả source; số miền/folds khả dụng báo thật, fold thiếu lớp/events → undefined. Đây là stress test nội bộ, không thay T độc lập. Mọi normalization/feature selection/imputation/calibrator nằm trong training fold; không scan statistics T để chọn hyperparameters. User-study cases riêng U, không lộ T qua viewer trước khi freeze T.

### 7.3. Ground truth và evidence audit labels

Giữ canonical Level01–04 và Anomaly=Level01–03. Với cohort mới: rubric do chuyên gia xác nhận tương thích định nghĩa gốc; ảnh không đủ căn cứ → UNKNOWN/UNRESOLVED ở audit layer, không ép thành Normal hoặc tự tạo level thứ năm trong dataset. Hai người có chuyên môn gán nhãn độc lập, **mù VLM/score/routing**, sau đó adjudicator xử lý bất đồng; lưu từng nhãn, lý do, consensus và version. Nếu chỉ đủ một annotator, gọi single-rater, chưa đạt gate GT đề xuất trừ khi Owner/giảng viên phê duyệt mức claim thấp hơn.

Đo raw agreement và confusion giữa annotators, κ có denominator/support; κ undefined nếu marginals suy biến. Ngưỡng agreement, tỷ lệ unresolved tối đa, mức severity cần chuyên gia nào được khóa sau pilot rubric, trước annotation target. Không tự sửa nhãn gốc InspecSafe theo review; lưu đề xuất discrepancy riêng. Annotator không dùng VLM làm ground truth hoặc dùng chính explanation model để hợp thức nhãn.

Vùng hỗ trợ cần nhãn **liên hệ vùng–hazard claim** do người đánh giá xác nhận, có tọa độ/transform/image hash. Polygon object chỉ chứng minh vị trí đối tượng, không tự là nguyên nhân nhãn nguy cơ. Không có vùng hợp lệ → viewer hiển thị “chưa có bằng chứng vùng đã kiểm chứng”. Model không sinh reason trong frozen output → reason fidelity N/A, không bịa explanation hậu nghiệm.

Rubric audit tối thiểu: đúng nhãn/đúng sai chưa rõ; chứng cứ có nhìn thấy; liên quan hazard; đủ để hỗ trợ claim; có mâu thuẫn; source/provenance hợp lệ. “Correct-answer-wrong-reason” chỉ ghi **correct label + stated evidence unsupported/contradicted** sau adjudication, không khẳng định biết cơ chế nội tại. Nếu không có stated reason, ghi evidence unavailable. Đòi causal claim cần occlusion/counterfactual controls + quyền inference/nhãn mới, ngoài core hiện tại.

### 7.4. Cỡ mẫu/precision, không tự đặt N

T2 phải đo trên development pilot: số independent clusters, kích thước/imbalance clusters, tỷ lệ mỗi focal-Normal, e_FS,m/severe, class support, joint/marginal missing rate, peer D distinct values, ensemble abstain, annotation disagreement và chi phí. Dùng các khoảng hợp lý (không chỉ point estimate tốt nhất) để mô phỏng **paired clustered sampling** cho chênh Macro-F1 ensemble–single chính và precision phụ của từng capture tại b, theo policy/denominator thật; giữ phụ thuộc bốn model trong cùng sample/source. Với annotation study dùng mô phỏng reader×case dependence. Chọn số source/events/cases để đạt CI half-width h và power cho δ_F theo O5; không dùng quy tắc “N ảnh” hoặc “10 events/feature” như bảo đảm.

Owner chốt `b, δ_F, harm/abstain margins, α_FPR, h, power_target, min_clusters, class/event support, max_undefined_resamples, cost caps` từ workload examiner, pilot và nguồn lực. Giá trị chưa có ở đây là **TBD có chủ sở hữu**, không là mặc định cho implementer. Custodian xác nhận recruitment/sampling/roles theo tiêu chí trước target; không tìm thêm ca target vì model ít sai. Nếu adequacy assessment cần thống kê lỗi target, phải là blind curator procedure được duyệt trước, analyst không nhận score/labels/so sánh; cách xử lý không đủ events đã khóa, không tuyển lại theo outcome. Ưu tiên thiết kế theo pilot và chấp nhận T thiếu precision là inconclusive.

## 8. Metric, thống kê và ma trận thí nghiệm

### 8.1. Cohort/metric contract đề xuất — O2/O5 PENDING

P là planned IDs immutable, G là GT-valid adjudicated, S=P∩G. Label-valid L_m và L_all=∩L_m xác định **không dùng GT**. Mỗi row giữ planned/output/label-valid/score-valid/GT-valid/source-known, exact-ID digest và exclusions. Primary dùng **cùng S cho ensemble và single**, không complete-case của từng arm. Sensitivity trên S∩L_all báo riêng để phân biệt signal với failures/abstain. GT unresolved giữ ledger, không ép Normal; missingness bounds và cap được khóa trước target.

| Endpoint | Công thức/tập/mẫu số | Undefined và claim |
| --- | --- | --- |
| **Primary Macro-F1 bốn lớp** | Trên S, F1_l=2TP_l/(2TP_l+FP_l+FN_l); mean đúng bốn lớp. Prediction INVALID/no-output/ABSTAIN nằm FN của true class, không FP lớp khác; cùng confusion 4×5. Δ=ensemble−m* | Thiếu true support một lớp → standardized macro null/NO_GO xác nhận; diagnostic available-class macro ghi class-set, không thay primary. Đây là metric thesis đề xuất, không sửa M2 |
| Balanced Accuracy | Mean recall_l=TP_l/n(true l) trên cùng S, failures/abstain thuộc support | Missing class → null; binary BA phụ khi có cả hazard/Normal. Không loại invalid để làm đẹp |
| False-safe/severe | n(GT hazard & decision L04)/n(GT hazard); severe thay GT=L01. Error event cho focal e_FS,m chỉ trên L_m | Rate này không gồm unresolved prediction; luôn báo hazard abstain/missing và worst-case unresolved-hazard bound, không coi abstain là phát hiện đúng |
| FPR/FNR valid (phụ) | Trên S∩L_arm: FPR=FP/(FP+TN); FNR=FN/(TP+FN), hazard positive. Ensemble label-valid mask riêng | Class absent → null; kèm invalid hazard/normal counts; FNR_valid=0 với all-hazard model không chứng minh an toàn |
| Coverage/abstain | valid decisions/n(P), valid decisions trên S, abstain/missing reasons/n(P), theo model/domain/source | N=0 null; primary không bỏ abstain. Guardrail maximum unresolved decisions và cost cần O5 |
| Capture_FS,m(b) | Trong E_m∩G: sum(review_a*e_FS,m)/sum(e_FS,m); operational variant trên C_m∩G gồm mandatory M_m∩C_m | No errors/no eligible → null. Cùng E/M/K giữa arms mỗi focal; ghi thêm gains **và losses** so comparator, net Δ. Không so focal different C như same population |
| Workload / residual FS | n(R_m,a)/n(P); focal hazard predicted L04 chưa review/n(GT hazard) + unresolved hazard panel | n(M_m)>K → OVERLOAD, không same-budget PASS; review chưa phải correction. Không cộng bốn scenarios thành một queue |
| Shared errors / peer variation | Pairwise 4-level/binary disagreement trên common label-valid IDs; all-wrong/shared-false-safe trên joint labels+G; D histograms/variance trong C_m | Denominators/exclusions rõ; different families không chứng minh độc lập; D constant/near-constant gate O5 |
| AP/AUROC/risk–coverage phụ | Error AP trên E_m∩G, positive e_FS,m; AP=sum Δrecall*precision theo unique-score blocks; AUROC ties=0.5. Retained risk=retained errors/retained_n, coverage trên E_m | No positives/negatives → comparison null; retained_n=0 → risk null. Raw HNLO chỉ qualified m, không pooled cross-model |
| FNR@validation-FPR phụ | Nếu native HNLO_m đủ: global threshold chọn V với FPR≤α_FPR, báo FNR/FPR ở T với threshold frozen, từng miền | T không bảo đảm FPR đúng α; không tune lại domain target. Calibration/threshold arm cần O2, không primary |
| Worst-domain/source | Min F1/BA/capture, max false-safe/abstain trong nhóm đủ support đã khóa; CI recompute extrema | Hiện cả undefined groups; không bỏ rare domain rồi claim robust tất cả |
| CT3 usefulness | Task accuracy với expert GT/rubric, time, unsupported-evidence detection, unsafe acceptance/escalation | Không evidence GT/reviewers → N/A/BLOCKED; numeric confidence chỉ khi calibration có bằng chứng |

Cấu trúc records/metric M2 không sửa; report thesis phải version/tập đủ điều kiện riêng. No-output khác INVALID khác ensemble abstain trong ledger dù cột confusion thứ năm gộp; không cộng cả ba thành nhãn GT thứ năm. Population claim cần nguồn/sampling hợp lệ, không từ stratified exposed TRAIN pilot.

### 8.2. Suy luận và kiểm định trước target

Đề xuất CI 95%, α_stat=0.05 **chờ O5**; δ_F, noninferiority/harm margins về false-safe/severe, coverage/abstain và cost caps chưa có số. Chốt bằng D pilot/workload/cluster simulation trước T, không dùng thresholds 160-pilot làm ngưỡng thesis mặc định. Primary PASS chỉ khi lower CI(Δ Macro-F1)>δ_F và tất cả preregistered guardrails đạt/defined; guardrail harm rates dùng bound đã khóa thay vì chỉ point estimate. Chưa đủ precision → inconclusive. Upper CI<δ_F không đạt minimum benefit; CI dưới 0 là harm, CI chứa 0 không chứng minh tương đương.

Paired cluster bootstrap trên verified source components: cùng draw giữ tất cả ảnh/bốn outputs/ensemble/ablation, không coi 4N focal rows độc lập. Recompute metric/Δ trên draw, giữ batch/queue contract khi xét finite-batch review; không reshuffle theo GT. Cluster xuyên domain dùng joint component, không label domain thành source. Bootstrap count/seed/max undefined draws khóa O5; thiếu class/events trong draws phải báo và nếu vượt cap thì CI unavailable, không loại đến khi đẹp. Ít source → descriptive/sensitivity, không bootstrap ảnh để giả precision.

m* và rule được freeze từ D/V, bootstrap target không chọn lại model/rule/focal. Focal comparisons dùng family bốn và optional score contrasts đã khai báo; Holm nếu confirmatory, còn lại exploratory, full table kể cả âm. Không pick budget/metric/domain theo target. Source-weighted analysis là secondary estimand riêng, không đổi primary image-weighted sau xem kết quả.

User study giữ thiết kế counterbalanced interface: block theo kinh nghiệm, mỗi examiner thấy hai tập case matched nhưng không cùng case hai lần; label-only vs evidence view, cùng ảnh/thời gian. Accuracy/time/unsafe-acceptance đánh giá bằng rubric độc lập; CI xét crossed reader và case/source, không từng click độc lập. δ_U/γ_U/δ_t và số reviewer do pilot/precision/rights; ba demo không thay study.

### 8.3. Ma trận thí nghiệm E1–E5

Mỗi experiment chỉ chạy sau protocol/rights/grant; PASS implementation khác benefit PASS.

| ID / mục đích | Input / phương pháp | Controls / metric | Output / PASS / rủi ro |
| --- | --- | --- | --- |
| X0 qualification/E5 | G0–G6, source/env/config, synthetic CPU rồi small GPU được phép | Builder/native/scripted vs actual paths; exact hashes/status/shape/format/score alignment | Receipts từng gate/attempt, no lost planned rows/raw; failure/unknown không thành model PASS; không chạy lớn chỉ vì CPU PASS |
| X1 độc lập CT1/E1 | Bốn model frozen trên cùng D/V; T sau T4 | Từng single, no-output/INVALID ledger; planned và common-ID F1/BA/FS/domain | Bảng baselines + m* chọn D/V; PASS đủ masks/support/cost, không mặc định Q3 tốt nhất |
| X2 hợp nhất H1 CT1/CT2/E1 | Same four outputs + frozen majority/abstain | Ensemble vs m*, planned Macro-F1/CI + FS/abstain/cost guardrails | Primary Δ và negative verdict; PASS protocol đúng, benefit không được hứa |
| X3 peer review CT2/E1 | Bốn focal scenarios, same peer outputs và E_m/M_m/K | Ordinal/binary/random; HNLO-only/combination chỉ qualified; capture/AP/workload/net gains/losses | Bảng cả bốn focal + shared errors/cost, multiplicity; thiếu events null, không winner fishing |
| X4 ablation/stress E2/E3 | D grouped CV/LODO source purge; frozen target subset | Bỏ từng model/quorum declared, score vs peers nếu đủ; imbalance/rare/corruption/missing-peer stress | Coverage/gain/harm/worst-domain; challenge set tách natural T; không điều kiện chọn trên T |
| X5 error analysis E4 | Authorized real outputs/expert GT/evidence; taxonomy/selection rule khóa trước | ≥3 nhóm lỗi và ≥3 case before–after, cả worse/unchanged | Ca thật có provenance, verified cause vs hypothesis, cách xử lý/limits; không bịa improvement |
| X6 viewer CT3 | U riêng, reviewers có quyền; label-only/evidence task | Same task information, counterbalance, accuracy/time/unsafe acceptance | Study report/CI; thiếu người/GT → descriptive/demo, không utility PASS |
| X7 tái lập E5 | Frozen source/config/env/raw receipts có quyền | CPU replay/oracles/checksums/builder, không model forward lại mặc định | Receipt nguồn→raw→tables; deviations và SKIP hiện, không grant mới từ reproduction |

X1–X4 development trước, target chỉ arms/contrasts đã khóa. Source/config/metric chưa approved → BLOCKED phần thí nghiệm, không biến code receipt thành quyết định khoa học.

## 9. Case review và error analysis trong phạm vi C nhỏ

### 9.1. User flow dự kiến

Nhận batch/receipt hợp lệ → xem coverage/overload → hàng đợi mandatory rồi top-k → mở case (ảnh có quyền, bốn nhãn gốc, model focal/peers, ensemble/abstain, HNLO chỉ nếu qualified, điểm ưu tiên, provenance) → examiner xem evidence có trạng thái verified/model-generated/unavailable → ghi accept/escalate/đề nghị sửa kèm lý do → lưu record mới và audit log. Không ghi đè prediction/raw/GT. Khi hash/source/image mismatch, chặn hiển thị vùng/ra quyết định theo chứng cứ lỗi, báo degraded state; rollback về nhãn/ảnh gốc chỉ khi còn hợp lệ và được phép.

| Tình huống công việc cần kiểm | Luồng trước–sau dự kiến | Bằng chứng phải thu sau, chưa phải case đã có |
| --- | --- | --- |
| Ca focal-Normal thực có hazard, được peer rank ưu tiên | Baseline cùng focal không chọn ở b → peer rank chuyển review; examiner xác minh nguy cơ hoặc vẫn bỏ sót | Sample/run/GT/provenance, rank/budget của hai arm cùng focal, expert action/time; không gọi “đã cứu ca” nếu chỉ routing. |
| Nhãn hazard đúng nhưng vùng/lý do sai hoặc thiếu | Label-only dễ chấp nhận → evidence view đánh dấu unsupported, yêu cầu kiểm lại | Rubric independent evidence, claim-region relation; đúng nhãn không chứng minh đúng lý do. Không có reason → unavailable, không tự flag wrong-reason. |
| Bất đồng/thiếu output hoặc miền khó gây overload | Điểm không hợp lệ → mandatory/escalation, hiện missing/không giả confidence | Error envelope, capacity và quyết định examiner; không dùng fallback tự gán Normal. |

Ba tình huống là **thiết kế tác vụ**, không phải ba ví dụ thực nghiệm. T5 phải chọn ca thật có quyền theo rule khóa; nếu không có ví dụ được cải thiện, báo trước–sau không đổi hoặc xấu đi, không dựng minh họa giả thành kết quả. Các nhóm lỗi tối thiểu: (1) false-safe/severe miss; (2) false alarm/severity mismatch; (3) unsupported evidence/correct-label-wrong-stated-evidence; thêm technical/provenance failure và shared blind spots khi có. Ghi nguyên nhân quan sát được khác với giải thích giả định; xử lý đề nghị, hiệu quả đo được và giới hạn từng case.

Viewer tối thiểu local/offline, không cần cloud/publish. Confidence numeric chỉ hiện nếu có calibration version/target semantics/validation evidence; nếu chưa, dùng tên “điểm ưu tiên” và “HNLO tương đối”. Không có bounding-box truth thì không IoU; không dùng attention map làm bằng chứng vùng đã xác nhận. Không bật prompt-grounding/crop intervention trong core; nếu muốn cần O2/O4/O6 amendment trước chạy.

## 10. Model status, nguồn lực và P1–P4

### 10.1. Model register và thẩm quyền

| Model / vai trò | Revision và nguồn chính thức | Bằng chứng hiện có / disposition |
| --- | --- | --- |
| Qwen3-VL-8B-Instruct — mốc lịch sử, một vị trí đề xuất ngang hàng | V4 `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`, [Qwen card](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct) | 3539/3763 saved-score SUCCESS; không raw validation mới hoặc quyền rerun. New protocol qualification vẫn cần |
| google/gemma-3-4b-it — candidate cũ, chưa chiếm slot | `093f9f388b31de276ce2de164bdc2081324b9767`, [card](https://huggingface.co/google/gemma-3-4b-it) | Gemma terms/gated, 10 config/tokenizer 401, BLOCKED_SOURCE_TOKENIZER_AUDIT_INCOMPLETE; chưa GPU failure |
| microsoft/Phi-3.5-vision-instruct — candidate cũ chưa qualified | `12b77fb40b63a2c73c68243d3f767aab688a1b2a`, [card](https://huggingface.co/microsoft/Phi-3.5-vision-instruct) | MIT/remote code; a6 160 actual calls, 0 valid C1, HNLO=0, CONSUMED/NO_GO; cause UNKNOWN, #147 diagnostic riêng |
| HuggingFaceTB/SmolVLM2-2.2B-Instruct — candidate cũ chưa qualified | `482adb537c021c86670beed01cd58990d01e72e4`, [card](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct) | Apache-2.0, a2 107 valid đều L01/53 invalid, HNLO=0, CONSUMED/NO_GO; continuation mismatch observed, collapse cause UNKNOWN |
| Qwen2.5 / InternVL3 / Moondream2 | Roster M1/M2 lịch sử, §2 và [DECISIONS](DECISIONS.md) | Không tự loại/thay; vai trò thesis cần O3, không dùng lịch sử để lấp ba slot qualified |

Danh sách ba candidates **OWNER_SELECTED_CANDIDATES** ngày 27/10 là fact lịch sử, không final thesis roster. Bốn slot/peer rotation/fusion là **OWNER_CONSIDERED_DESIGN / PROPOSED**, O1–O3/T0 REQUIRED. Cả ba candidate cũ ngoài Figure 6 của [InspecSafe PDF tác giả trang 10](https://arxiv.org/pdf/2601.21173v1#page=10), không có kết quả tác giả tương ứng trong comparison gốc đó; giữ kiểm hình ngày 27/10, không đọc TEST. Không dùng benchmark figure để chọn model trên target.

**Không tự tuyển model mới ở #137.** #148 đang ON HOLD: sau review/audit và scientific decisions, mới giao nhiệm vụ tuyển ba vị trí theo scope đó; không tự bắt đầu longlist ở đây. Nếu <3 model đạt, báo số thiếu và NO-GO thiết kế full-four; giảm số model/đổi hướng cần amendment, không ép Phi/Smol/Gemma vào core, không model zoo vô hạn.

### 10.2. Kaggle compatibility và acceptance thực tế

Target hardware theo yêu cầu: 2×T4, 16 GB danh nghĩa mỗi GPU; actual reported usable VRAM tùy VM. Không 32 GB unified. Một model/environment mỗi lượt, không cần bốn model resident đồng thời; sequential chỉ giảm peak, không giảm calls/latency tổng. Sharding nếu cần phải pin/qualify placement/inter-GPU transfers riêng. Không tự lượng tử hóa/BF16/đổi crops/prompt/parser để cứu.

| Model | Source/env/preprocess đã kiểm theo receipt | Điều đã chứng minh / còn thiếu |
| --- | --- | --- |
| Gemma | Native Gemma3+SigLIP, ảnh→text, card Transformers≥4.50.0; source pilot dự kiến 4.51.3, BF16 saved weights/card, image 896/crops cần locked processor; gated | Không có access/config/tokenizer/FP16 runtime proof. [Gemma report Table 3](https://storage.googleapis.com/deepmind-media/gemma/Gemma3Report.pdf#page=3) 8 GB weights/+KV 12.7 GB không là peak FP16 multimodal T4. UNVERIFIED |
| Phi | Pilot pin Torch2.6.0+cu124/Transformers4.43.3, native shared remote-code loader; eager 32 decoder+24 CLIP layers, GPU0 FP16/16 crops, batch1/greedy64/C1 giữ nguyên | a6 actual attention/load/160 calls verified theo [aggregate](https://github.com/tantdna2/SafeShift/pull/144#issuecomment-6480224537); peak allocated12.583 GiB/reserved14.391 GiB rất sát trần phiên đó. Không gọi FP16/chạy được còn NOT_RUN; **quality/HNLO chưa đạt**, không suy T4 envelope lớn hơn chạy được |
| Smol | Native 4.51.3, Torch2.6.0+cu124, num2words/docopt pins; 24 Llama+27 vision eager, GPU0 FP16, RGB/splitting/padding size1536/tile384, image_seq_len81; weights F32 khác dtype compute | a2 actual 160 calls, allocated6,021,477,888/reserved6,746,537,984 bytes theo [aggregate](https://github.com/tantdna2/SafeShift/pull/146#issuecomment-6485519647). HNLO0/quality NO_GO, không claim mọi môi trường FP16 tương đương BF16 |

Chi tiết source/runtime/deps/tokenizer/error receipts và tất cả giới hạn ở [failure/release runbook](../KAGGLE_FAILURES_AND_RELEASE_GATES.md); không lặp pipeline hoặc chỉnh notebooks. [FlashAttention upstream](https://github.com/Dao-AILab/flash-attention#nvidia-cuda-support) FA2 CUDA thông thường không phải T4 path; effective attention kiểm native cả vision/decoder, không chỉ kwargs. CPU metadata/shape/meta tests là cần, không đủ cho model behavior/real VRAM. Snapshot source công khai không chứa trained weights; source access khác quyền inference/ảnh/target.

### 10.3. P1–P4 tuyển qualification cho mô hình ngang hàng

P1–P4 là scientific/operational proposal dùng release gates G0–G6; thresholds/counts phải O5 trước lượt screening chính, không thay pilot cũ. Không dựa duy nhất vào accuracy hay có output.

| Gate | Mục đích / đầu vào / đối chứng | Sản phẩm, PASS/NO-GO và dependency |
| --- | --- | --- |
| P1 runtime | Approved exact source/env/rights; G1–G4 CPU+Kaggle preledger; small authorized G5 image envelope | LOAD khác E2E; raw/label parse/invalid/errors/checksums, no OOM trên locked envelope. Fail dừng, no rescue/retry; GPU nhỏ vẫn tiêu attempt theo grant |
| P2 independent behavior | Authorized D panel đủ Normal/hazard/severity; strict C1, all planned records, same-ID baselines | Distribution/confusion/F1/BA/FS/FPR/invalid/repetition; staged behavioral stop chốt trước. All-Anomaly/all-Normal hoặc thấp quality không tự gọi ích lợi; no valid labels → không làm peer classifier đủ điều kiện. Dữ liệu thiếu → inconclusive |
| P3 complementarity | Qualified labels của provisional panel trên common D; focal rotation cả bốn, shared error/binary+ordinal D; ensemble vs dev m* | Incremental gain/loss/CI/cost, leave-one-out, HNLO-only khi qualified; thresholds và full-four final roster O3. Không buộc mọi peer phải cải thiện **mọi focal**, nhưng vai trò nào không thêm ích lợi phải báo. Không dùng target để tuyển |
| P4 cost/stability | Per-GPU peak, RAM/load/p50-p95/invalid/OOM/bytes/attempt cost từ P1 trở đi; planned quota/data rights | Include failed/rejected models + full4 vs single inference. Caps/benefit tradeoff O5; stop ngay nếu vượt. Không dựa weights size hoặc CPU fit để gọi T4 PASS |

T2 đo pilot/caps/shortlist technical; T3 dựng controls để kiểm P3 và finalize roster **trước full development/freeze**, không đòi P3 trước có baseline. Bounded thứ tự/number attempts/candidate-search rule do T0/O3/#148 chốt dựa access/resources trước score. Không chạy tất cả full data để chọn; sequential small qualifications, failed/blocked ghi rõ, retained negatives. Không có đủ bốn → negative feasibility + quyết định giảm scope, không tự mở GPU/longlist mới.

### 10.4. Chi phí, thời gian và quyền

| Khoản | Cách xác định từ pilot thật | Blocker |
| --- | --- | --- |
| Calls/time | Four-panel khoảng 4N model-image calls + tất cả screening/failure/retry trong grant; rotation/ensemble dùng cached outputs, **không 16N calls**. T≈ΣN_m*latency_m+load/setup; single operational N calls, không bắt single chịu peer cost | No quota reservation, exact source/model/run/attempt mới; Q3 rerun cũng phải grant |
| Memory/storage | Peak từng GPU/RAM, resolution/token/crops envelope; storage=Σraw_bytes+logs/manifests/checksums+allowed backups/cache transient | Đo thật, giữ raw trước parse, không bỏ evidence để giảm storage; sequential caches không cùng vùng nhớ |
| Annotation/GT | N*(2*t_label+disagreement_rate*t_adjudication)+evidence/QA; pilot đo thời gian, số sources và support | Independent annotators/adjudicator, use/export rights, target custody, nguồn không chỉ folder |
| User study | Readers*cases_per_reader*time + training/rest; crossed precision simulation | Reviewer expertise/consent/quyền ảnh, no automatic invitations |
| Schedule | Critical path T0 decisions→rights/source→qualification→D→freeze→T→report; effort ước lượng sau pilot & actual deadline | Không deadline/N/budget giả. Nếu resources không đủ, quyết định giảm scope trước target, không cắt hard cases |

Permission matrix: issuer/ref/time/scope/source/model/revision/data/hash/run/attempt/limits/expiry/stop, tách science/data access/run/export/merge. T0 approval không tự mở GPU, T2 không tự full run, T4 freeze không tự target release. Grant a6/a2 consumed; #137 không tạo/đọc grant private trong IDE hoặc cấp quyền mới.

## 11. Master Execution Plan duy nhất

Tất cả task sau là **PLANNED, NOT_AUTHORIZED_BY_THIS_DOCUMENT**. Mỗi task là một sản phẩm hoàn chỉnh gồm code/test/docs khi có code, cập nhật PROJECT_STATE trong cùng PR. DONE sản phẩm, PASS khoa học, PASS audit/merge và benefit PASS phải ghi riêng. Không tự merge; recheck GitHub/AGENTS trước mỗi task. Tên file **dự kiến** chưa tồn tại được ghi code span, không link giả. Tệp derived/raw/manifests nhạy cảm ở `data/processed/` hoặc storage được cấp, không Git.

### T0 — Ghi quyết định chuyển tiếp và hợp đồng ba tầng

- **Loại / mục tiêu:** quyết định khoa học + tài liệu; chuyển đề xuất thành hợp đồng có thẩm quyền, không tự cấp quyền run.
- **Điều kiện bắt đầu:** ChatGPT kiểm HEAD/diff, audit khoa học/code theo chỉ thị, Owner có quyết định cụ thể; thiếu approval giữ PENDING.
- **Phạm vi:** ghi O1–O8; ba tầng/four-peer proposal, primary H1 và family secondary, optional per-model HNLO, strict-majority/abstain, cohort/invalid/missing/budget/cost; chốt selection scope/stop và vai trò Q3, không bắt ba candidates cũ thành peers. Giữ #148 ON HOLD đến đủ review/audit/quyết định cho tuyển; #147 riêng. Numerical values chưa đo có owner/gate rõ; giữ TEST đóng.
- **File dự kiến:** append `docs/research/DECISIONS.md`, `docs/research/THESIS_PROTOCOL.md`, `docs/research/thesis_config.v1.json`, PROJECT_STATE; điều hướng README/ROADMAP/EXECUTION_PLAN khi successor được duyệt; M2 nguyên byte.
- **Bàn giao:** approval matrix có refs thật, protocol pilot-ready, unresolved register/selection bounds, xử lý M1–M8/#136 đúng lịch sử, scope phần mềm/runtime được duyệt.
- **Kiểm/bằng chứng:** trace mỗi công thức/quyền tới decision; hash M2; không TBD vô chủ/approval tự sinh; review ensemble abstention vs triage endpoints và multiplicity.
- **DONE/PASS/FAIL:** DONE khi ghi đúng quyết định; PASS phạm vi chỉ khi O1–O3 đủ; thiếu → BLOCKED phần đó, không xin lại M1/M2 cũ. Không dùng merge tài liệu làm grant.
- **Quyền thiếu / task kế:** Research Lead/Owner và học vụ O1–O3/O8; **T1**. #148 chỉ mở trong scope tuyển được duyệt, không chạy ngay bởi T0.

### T1 — Quyền, nguồn, GT và nguồn lực cho panel bốn model

- **Loại / mục tiêu:** phụ thuộc bên ngoài + acquisition protocol; đủ điều kiện trước pilot.
- **Điều kiện bắt đầu:** T0 scope PASS, đầu mối nguồn/custodian do Owner xác nhận; không đọc target chưa cấp.
- **Phạm vi:** license/use/export, source/site/session/duplicate, label compatibility, annotators/reviewers, D/V/T/U policy; access/revision/env/remote-code review từng model, khoảng 4N calls và screening cost, per-GPU memory. Dùng §10 và G0–G6, không coi Kaggle 2×T4 là pooled 32 GB. Thiết kế precision simulation/GT-blind roles; native CPU prerequisites phải có scope riêng trước chạy.
- **File dự kiến:** `docs/research/THESIS_DATA_PROTOCOL.md`, protocol/config/decision và PROJECT_STATE. Chứng từ cá nhân ngoài Git.
- **Bàn giao:** source/access/resource matrix, annotation rubric/custody, candidate qualification order/caps đã duyệt, môi trường và nguồn pin, grant nhỏ đúng model/source/data/run/attempt hoặc NO-GO report.
- **Kiểm/bằng chứng:** verified sources không chỉ folder; tách ảnh/raw/export rights; không nhãn VLM làm GT; đủ expert/time/quota; không lấy source lock thiếu file làm PASS.
- **DONE/PASS/FAIL:** hồ sơ DONE kể cả NO-GO; GO chỉ khi quyền pilot/GT/nguồn/resources đủ. Thiếu target source chặn xác nhận, không đổi TRAIN thành target.
- **Quyền thiếu / task kế:** O4/O6/O7, data owner/custodian/provider; **T2** khi GO. Không tự tải weights hoặc liên hệ ngoài bằng task giấy tờ.

### T2 — Qualification/pilot và khóa numerical gates

- **Loại / mục tiêu:** phần mềm tối thiểu + thực nghiệm được cấp; đo feasibility trước full development.
- **Điều kiện bắt đầu:** T1 GO, exact source/env/grant; release G0–G4 đã nghiệm thu trước GPU nhỏ G5. CODE_PASS khác run authorization.
- **Phạm vi:** tái dùng runtime/builder/native rehearsals/raw custody hiện có sau tích hợp main có quyền; bổ sung adapter cần thiết theo scope duyệt, không duplicate framework. Sequential qualification D-only: P1 LOAD/E2E, P2 labels/errors/repetition/support, P4 resource caps; không chạy 160/full mặc định. Source/annotation QA và cluster simulation; chốt δ_F/b/guardrails/precision/stop/support/CI/cost trước screening chính, không nhìn target. P3 chờ baseline ở T3.
- **File dự kiến:** `safeshift/pilot/` adapters/runtime hiện có, notebook builder và tests tương ứng khi được giao sửa; source registry module trong `safeshift/data/`, `docs/research/THESIS_PILOT.md`, protocol/config/state. Không sửa parser/HNLO surfaces cũ để cứu run đã fail.
- **Bàn giao:** receipts từng attempt/skips/failures, release matrix, data/source/annotation role hashes ngoài Git, provisional four-model panel hoặc thiếu vị trí rõ ràng; numerical register có approvals; HNLO qualification từng model riêng.
- **Kiểm/bằng chứng:** production native path + synthetic envelope/failure cases trước GPU; raw-before-parse, no overwrite, no target read, paired IDs/missing accounting; CPU scripted không chứng minh behavior. Current Phi/Smol NO_GO không qualified tự động.
- **DONE/PASS/FAIL:** hồ sơ DONE dù tất cả fail; GO T3 full-panel khi đủ **bốn** classification-qualified models, data/events/resources khả thi và caps duyệt. Score thiếu chỉ loại score arm, không tự loại classifier. Không đủ bốn → NO-GO design này, negative feasibility + O1/O3 scope decision, không mở longlist vô hạn.
- **Quyền thiếu / task kế:** grant từng qualification/annotation, O3 roster disposition và O5 numerical approval; **T3** khi GO. Không dùng consumed attempts để thử lại.

### R — Tái sử dụng R1–R5 có giới hạn (nhánh hỗ trợ, không cửa ải Seminar)

- **Loại / mục tiêu:** phần mềm và hồi cứu, chỉ sau O8; giữ giá trị ledger/provenance/errors, không trì hoãn dữ liệu mới để bảo vệ học phần đã bỏ.
- **Điều kiện bắt đầu:** Owner chọn hoàn tất #136 trong đúng session/PR cũ hoặc chọn dừng; **session lập kế hoạch này không thực hiện R**. Nếu tiếp tục: sửa/audit/merge #136 theo quy trình riêng rồi cấp artifact grant M4 mới.
- **Phạm vi:** ưu tiên đóng lỗi metadata đã audit và tests đúng ID hashes; sau merge/grant tái dùng R1 coverage, R2 classification/ranking, R3 missing/severe, R4 disagreement/degeneracy; R5 viết narrative giới hạn cho chương nền Khóa luận. Không thêm AP/CI/thesis fit vào M2 v1, không chạy recovery pooling.
- **File dự kiến:** đúng file #136 trong session cũ; sau khi được phép reanalysis, `docs/research/THESIS_HISTORICAL_EVIDENCE.md` và PROJECT_STATE; artifacts ignored. Không copy code draft lỗi sang nhánh mới để tránh audit.
- **Bàn giao:** một gói historical evidence có receipt/M2 trace hoặc quyết định không tái phân tích và chỉ cite số đã verify.
- **Kiểm/bằng chứng:** independent oracle exact eligible IDs/count/hash từng R3/R4 CSV; protocol/config hashes bất biến, synthetic khác real, scope artifact chính xác.
- **DONE/PASS/FAIL:** metadata còn sai → FAIL, không cite output #136 làm kết quả. Historical reanalysis chưa chạy → NOT_RUN, không M4 COMPLETE. Dừng nhánh cần quyết định Owner, không tự đóng PR hoặc đổi M3/M4/M5 lịch sử.
- **Quyền thiếu / task kế:** O8 và artifact grant, review/merge #136 riêng; tích hợp bằng chứng vào T3/T6. Không bắt buộc R hoàn tất trước T1/T2; T3 không phụ thuộc output R chưa verified.

### T3 — Ba tầng development, model selection và viewer

- **Loại / mục tiêu:** phần mềm + thực nghiệm phát triển; gói hoàn chỉnh có thể freeze.
- **Điều kiện bắt đầu:** T2 đủ bốn provisional peers, D/V/U rights, P1/P2/P4 receipts và approved metrics/rules; không T labels. Nếu R chưa xong, không phụ thuộc draft #136.
- **Phạm vi:** bốn single baselines; focal rotation/peer-only/random và HNLO/combo chỉ khi qualified; strict-majority vs dev-selected strongest single; four leave-one-out, stress/error cases; P3 complementarity và full cost P4. Chốt final four theo bounded rule/O3 trước full development, không post-target selection. Viewer read-only với log người riêng; U-development để sửa UI trước study. Không learned ensemble/15 subset search/prompt search ngoài scope.
- **File dự kiến:** `safeshift/evaluation/thesis_metrics.py`, `safeshift/evaluation/peer_review.py`, `safeshift/evaluation/decision_fusion.py`, `scripts/evaluate_thesis.py`, `scripts/review_cases.py`, tests tương ứng, `docs/THESIS_USAGE.md`, `docs/research/THESIS_DEVELOPMENT.md`, protocol/config/state. Reuse core records/validation/raw contracts.
- **Bàn giao:** runnable CLI/controls/ablation/viewer, exact cohort ledger, P1–P4 selection/negative ledger/full screening cost, O3 final roster, D/V report và freeze candidate. Không gọi chưa thử là thua, không chọn theo accuracy đơn lẻ.
- **Kiểm/bằng chứng:** independent oracle cho 4×5 confusion/undefined/abstain và quorum, peer missing/constant/ties, same K/M/E, source folds/CI, raw immutable, target-read guards; UI missing/stale evidence/rollback, actions không sửa labels gốc.
- **DONE/PASS/FAIL:** implementation PASS kể cả ensemble thua; tất cả arms có output hoặc null+reason và cost. Không đủ bốn/strong baseline/GT/source/caps → FAIL freeze; reduced scope chỉ sau O1–O3. Không đổi primary để che negative result.
- **Quyền thiếu / task kế:** development runs, image/reviewer rights, final O3/O5; **T4** sau review source/tests và evidence.

### T4 — Freeze thiết kế trước target

- **Loại / mục tiêu:** khoa học + audit; khóa một primary và mọi đường phân tích.
- **Điều kiện bắt đầu:** T3 reviewed/merged source và T2 gates còn hiệu lực, custodian chứng nhận T chưa lộ.
- **Phạm vi:** pin final four revisions/native templates/parser/generation/env/dtype/attention, cohort/GT/source roles, strongest single m*, majority/abstain/missing/quorum, four focal queues/budget/ties, score-qualified subset/optional fits, controls/ablation, δ_F/guardrails, CI/multiplicity/seeds/search/stop/cost và user study. Gắn P1–P4/G0–G6 receipts, rejected/NOT_RUN/full costs; xin quyền target riêng.
- **File dự kiến:** `docs/research/THESIS_FREEZE.md`, approved config/protocol version, append decisions, PROJECT_STATE; large/raw ngoài Git.
- **Bàn giao:** attributed freeze record theo exact SHA/hashes, no unresolved primary/target numerical values, authority matrix hoặc NO-GO.
- **Kiểm/bằng chứng:** no self-referencing hash; code/native/qualification đúng source; same four raw predictions dùng ba tầng, không rerun để đổi focal; target custody, M2 nguyên byte, score N/A rõ.
- **DONE/PASS/FAIL:** freeze PASS khác target grant; thiếu numerical/qualified four, target lộ hoặc nguồn không xác minh → NO-GO. Không nhận exploratory thành confirmatory.
- **Quyền thiếu / task kế:** O5 final numerical và O6 target/study-specific run authority, O7 consent; **T5** khi đủ cả freeze và grant.

### T5 — Đánh giá xác nhận, phân tích lỗi và usefulness

- **Loại / mục tiêu:** thực nghiệm được khóa; trả lời H1 và secondary ở đúng mức bằng chứng.
- **Điều kiện bắt đầu:** T4 frozen source/hashes + target/study grant; storage/raw writer sẵn; custodian release đúng scope, TEST vẫn đóng.
- **Phạm vi:** một lượt T theo cấu hình, lưu mọi failure/raw trước parse; X1–X4 confirmatory locked subset, paired source CI; X5 ≥3 nhóm/≥3 cases thật; X6 user study; X7 CPU reproduction và audit trace. Không tune sau kết quả; bug ảnh hưởng kết luận cần deviation/version/review, không im lặng rerun “xác nhận”.
- **File dự kiến:** `docs/research/THESIS_RESULTS.md`, figure/receipt nhỏ có quyền, PROJECT_STATE; code sửa bug chỉ nếu rõ trong cùng task và audit ảnh hưởng, outputs immutable version mới ngoài Git.
- **Bàn giao:** tables chính/ablation/worst-domain/missing/cost, Δ/CI/support/undefined, H1 benefit verdict, user study/error case report, negative results và deviations.
- **Kiểm/bằng chứng:** source/input/output/GT hashes, planned=accounted statuses, exact metric memberships, match K/M/E, errors không thành Normal, thống kê phù hợp dependence; reviewer trace mỗi claim tới row/receipt.
- **DONE/PASS/FAIL:** protocol execution PASS dù benefit FAIL/inconclusive; leakage/pooling/post-target selection là FAIL thiết kế. Usefulness chỉ PASS khi study thật đủ protocol; thiếu người/cases giữ BLOCKED phần đó, không gọi synthetic demo là CT3 hoàn tất.
- **Quyền thiếu / task kế:** run đúng source/release/attempt, expert image review/export rights; **T6** khi kết quả nghiệm thu hoặc scope giảm đã duyệt. Không sửa target hoặc bỏ baseline để mở T6.

### T6 — Luận văn, slide và gói tái lập

- **Loại / mục tiêu:** sản phẩm học vụ; một bản luận văn thống nhất, không thêm bộ Seminar riêng.
- **Điều kiện bắt đầu:** T5 evidence audited hoặc quyết định giảng viên về scope giảm sau NO-GO; format/lịch bảo vệ/quyền chia sẻ được xác nhận. Có thể viết nền tảng từ T0 nhưng chưa kết luận kết quả.
- **Phạm vi:** chương 1 bài toán/RQ; 2 related work; 3 dữ liệu/protocol/baseline độc lập; 4 peer checking, decision fusion và implementation; 5 kết quả/ablation/stress/errors; 6 case-review/usefulness/tái lập; 7 kết luận/limits. Gộp chương nếu trường yêu cầu. Slide/appendix/traceability, render QA, hướng dẫn môi trường/commands và artifacts có quyền.
- **File dự kiến:** `docs/research/THESIS_REPORT.md`, nguồn slide/appendix và figure nhỏ được duyệt, usage/protocol/results/state; binary lớn ở `data/processed/`. Không tạo bộ file trình bày trước khi có task này.
- **Bàn giao:** luận văn/deck xuất được, source/code/config/fixtures và reproduction guide, evidence-to-claim index, giới hạn/negative results, xác nhận học vụ khi xảy ra.
- **Kiểm/bằng chứng:** mọi số→receipt, mọi claim→estimand/CI, source/links và visual QA, small artifact privacy/license, fresh CPU reproduction trong quyền hoặc ghi lý do chưa chạy.
- **DONE/PASS/FAIL:** kỹ thuật DONE khi đủ gói kiểm được; học vụ DONE chỉ có nghiệm thu/bảo vệ thật. NO-GO xác nhận vẫn ghi NOT_COMPLETED, không đổi T5/M7 thành PASS. Không hứa publish/deploy hoặc kiến trúc mới.
- **Quyền thiếu / task kế:** giảng viên/hội đồng, quyền chia sẻ ảnh/figures, lịch thực; kết thúc gói Khóa luận, không tự mở deployment.

**Song song an toàn sau các gate:** T1 giấy tờ nguồn với R synthetic repair (hai scope/session riêng); T2 annotation bởi người có quyền với software synthetic qualification; trong T3 viewer synthetic với metric engine; viết nền tảng T6 từ tài liệu trước T5. Không task song song nào được đọc target, dùng nhãn của U-study để tune model, hoặc vượt grant GPU. Reviewer/custodian có thể là vai trò tách biệt dù nhân lực nhỏ; nếu không tách được phải có access controls và mức claim giảm được duyệt.

## 12. Chuyển đổi lộ trình cũ và xử lý PR #136

| Thành phần cũ | Phân loại chuyển tiếp / khuyến nghị | Hệ quả kỹ thuật/khoa học và gate |
| --- | --- | --- |
| Foundation V1, #130/#131 | **GIỮ/TÁI SỬ DỤNG** records, validation, exact join, sensitivity/oracles và receipts | Có trên main; chỉ mở rộng theo contract mới, không nhận backend đã có. |
| M1/M2 quyết định/protocol | **GIỮ NGUYÊN LỊCH SỬ** | Không sửa hash; T0 append successor cho thesis. N/A cũ không tự truyền sang thesis. |
| #133/#134 Seminar→Thesis, M5 prerequisite | **ĐIỀU CHỈNH SAU DUYỆT** thành T0–T6 | Bỏ dependency bảo vệ Seminar trong lộ trình mới theo chỉ thị Owner; không hồi tố M5 COMPLETE/VOID. |
| Báo cáo/slide/thi riêng Seminar | **KHÔNG CÒN CẦN CHO SẢN PHẨM MỚI** | Tích hợp kết quả cần thiết vào chương nền; không thực hiện deck riêng. Trạng thái M5 lịch sử chưa hoàn thành giữ rõ. |
| PR #136 / M3 | **ĐANG AUDIT FAIL/BỊ CHẶN** | Ưu tiên hoàn tất phần correctness nếu Owner O8 chọn tiếp tục; chỉ session/PR cũ sửa. Chưa dùng code/output draft làm dependency đã PASS. |
| R1 | **TẬN DỤNG ƯU TIÊN CAO** coverage/ledger/provenance | Trực tiếp ngăn sai mẫu số thesis; code reuse sau audit/merge. |
| R2 | **TẬN DỤNG MỘT PHẦN** nhãn-vs-score baseline lịch sử | Không thêm AP/calibration vào contract M2; thesis metrics phiên bản mới sau O2. |
| R3 | **TẬN DỤNG ƯU TIÊN CAO SAU SỬA** missing/severe/độ nhạy | M224 metadata phải đúng; source CI không từ heuristic; không làm đủ 19 hazard placeholders thành nghiên cứu mới. |
| R4 | **TẬN DỤNG ƯU TIÊN CAO SAU SỬA** disagreement/shared errors/variance trong B04 | Cần đếm V4-only exact IDs; không dùng 38 composite. Không gọi hồi cứu là xác nhận H1. |
| R5/M4 scientific narrative | **THU GỌN SAU DUYỆT** vào thesis historical evidence | M4 chưa có quyền/result; narrative mới phải nối bảng thật/limits, không tự điền kết luận từ fixture. |
| 40 variants lịch sử, hazard mapping thiếu, full Moondream TRAIN | **KHÔNG TỰ MỞ RỘNG** để hoàn tất hình thức | Giữ bằng chứng/roster/N/A đúng phạm vi. Bổ sung chỉ khi giúp primary endpoint và có O2/O3/quyền cụ thể. |
| M6/M7/M8 cũ | **TÁI CẤU TRÚC** thành T1–T6 sau T0 | Bỏ điều kiện M5 nhưng giữ data/precision/freeze/target gates. Không đánh dấu các milestone cũ xong từ đổi tên. |
| GPU/TEST/annotation/target | **TUYỆT ĐỐI CHƯA THỰC HIỆN** trong task kế hoạch | Grant riêng theo run; TEST không thuộc kế hoạch này, TRAIN không holdout. |

**Khuyến nghị O8 cụ thể:** giữ PR #136 OPEN/DRAFT trong lúc duyệt kế hoạch; nếu tiếp tục thiết kế thesis, ưu tiên hoàn tất audit correctness đã có trong **chính PR/session đó**, không mở rộng tính năng thesis vào #136. Sau khi review/merge thật và có grant artifact, R1–R4 tạo gói hồi cứu ngắn, R5 làm phụ lục thesis. Lý do: ledger/provenance và error eligibility là hạ tầng có giá trị; lỗi metadata hiện tại khiến reuse một phần chưa sửa vẫn rủi ro. Không buộc chạy toàn bộ Seminar hoặc bảo vệ M5 trước T1.

Nếu Owner chọn dừng #136 để giảm thời gian, ghi quyết định dừng phát triển/tái sử dụng có phạm vi; không coi PR FAIL là đã sửa, không cherry-pick/exporter lỗi vào T3. T2/T3 phải có reader/evaluator tương ứng được review mới, chi phí viết/test lại được đưa vào budget; số lịch sử chỉ cite receipt đã verified. Việc đóng PR, merge, bỏ branch hay thay authority không nằm trong task này và chưa được tự thực hiện.

## 13. Risk register, GO/NO-GO và fallback

| Rủi ro / phát hiện | Ảnh hưởng | GO cần gì / NO-GO và phương án dự phòng |
| --- | --- | --- |
| Bốn peers chưa đủ qualified; #148 chưa mở | Cao, T0–T2 | Bounded selection sau review/audit/O3; không ép Phi/Smol vào panel. Không đủ bốn → feasibility report + Owner chọn scope giảm trước target |
| Đóng góp thực nghiệm chưa đủ chuẩn học vụ | Cao, T0 | O1/giảng viên xác nhận primary và negative-result route; không gọi majority/disagreement là thuật toán mới |
| 4N calls + screening vượt quota/time/storage | Cao, T1/P4 | Sequential loading, reuse raw across tiers, all-attempt cost và caps; thiếu → NO-GO/full run chưa cấp, không giấu chi phí ba peers |
| Nguồn T không độc lập, exposed TRAIN hoặc source unknown | Cao, T1/T4 | Verified source registry/custody; thiếu → development-only, không lấy folder-domain làm independent source |
| Ít rare severe/false-safe/source clusters | Cao, T2 | Precision simulation theo H1 và secondary riêng; undefined/CI rộng báo đúng, không tự tăng N hoặc chọn focal nhiều events làm primary |
| Nhãn không tương thích/không expert | Cao, T1/T2 | Blind independent annotation/adjudication, unknown policy; thiếu → không dùng VLM labels làm GT |
| Majority shared errors/ties/abstain làm mất coverage | Cao, X2/X4 | Planned denominators/4×5 confusion, guardrails, shared-error matrix, complete-case chỉ phụ; không bỏ abstains để nâng primary |
| Tuning bốn focal/roster/many metrics | Cao, T3/T4 | Bounded selection D/V, one primary, multiplicity families; freeze m* và all rules, không chọn target winner |
| HNLO_native thiếu hoặc khác semantics giữa models | Cao, P1/X3 | Native alignment approval từng model; thiếu → score arm N/A, classification vẫn kiểm riêng, không trung bình raw HNLO |
| Phi INVALID, Smol collapse, Gemma 401 | Cao, T2 | Public evidence ở §10/KB; consumed giữ nguyên; root causes chưa chắc. #147 riêng; qualification mới chỉ grant mới, không parser/surface rescue |
| OOM/attention/env drift | Cao, G2–G5 | Shared native path/layer provenance, fixed FP16/envelope, actual per-GPU memory; CPU không dự báo FP16 activations/VRAM, stop và no implicit retry |
| Notebook embedded source drift/custody loss | Cao, G1/G3/G6 | Exact builder/hash/static CPU suite + native/VM checks, partial evidence và no overwrite. Disk full/hard kill vẫn có thể mất report, không hứa mọi lỗi đều có ZIP |
| Tích hợp main và lệch evidence giữa branches | Kiểm sau tích hợp | Quyền 29/10 cho merge main vào cùng branch; chỉ conflict PROJECT_STATE đã reconcile. Kiểm exact integrated HEAD, five-path diff, protected bytes và test skips; lỗi/out-of-scope → FAIL, không rebase/force-push |
| #136 metadata audit FAIL | Cao, R | Không reuse draft output; O8 chọn sửa riêng hoặc budget reader/evaluator mới; không thay M3/M4/M5 lịch sử |
| Viewer tạo niềm tin sai/thiếu reviewers | Cao, X6 | Verified/generated/unavailable rõ, unsafe-acceptance criterion; thiếu expert/rights → CT3 usefulness BLOCKED, synthetic demo chỉ technical |
| H1 không thắng hoặc guardrail fail | Kết quả hợp lệ, T5 | Báo negative/inconclusive và full cost/coverage; không đổi primary, bỏ domain hoặc tuyên bố review gain là Macro-F1 gain |

Không đặt tên gate khoa học G0–G6 khác runbook: **G0–G6 duy nhất là notebook release gates** trong [knowledge base](../KAGGLE_FAILURES_AND_RELEASE_GATES.md). Gates thesis dùng T0 approval, T1 rights, T2 qualification/precision, T3 development, T4 freeze+custody, T5 evidence, T6 học vụ; P1–P4 qualification utility/cost. Mỗi NO-GO ghi owner/evidence/scope/điều kiện mở lại; merge Markdown không vượt gate.

Fallback theo nguyên nhân: (1) không đủ bốn qualified → giữ negative feasibility, trình O1/O3 giảm số model hoặc trở lại A/B có scope rõ **trước target**, không tự mở tuyển vô hạn; (2) HNLO thiếu → giữ label-only peer/ensemble arms, score claims N/A; (3) ensemble không hơn single → báo single rẻ hơn và thất bại H1, secondary review không thay primary; (4) thiếu source/precision → development-only và xin chuẩn học vụ giảm; (5) thiếu evidence/reviewers → provenance viewer kỹ thuật, CT3 usefulness chưa hoàn thành. Không fallback sang TEST, GT do VLM sinh, pooling Recovery224 hoặc bỏ roster lịch sử.

## 14. Quyết định Owner cần duyệt trước triển khai

Đã có chỉ thị bỏ Seminar và danh sách ba candidates cũ để khảo sát; chỉ thị 29/10 yêu cầu **thiết kế** bốn peers để xem xét. Chưa duyệt khoa học/học vụ/final roster, chưa cấp run mới. T0 chỉ ghi approval có bằng chứng, các gate thiếu vẫn đóng.

| ID | Quyết định cụ thể | Lý do/hệ quả/bằng chứng cần | Thời điểm |
| --- | --- | --- | --- |
| O1 | Tên/phạm vi ba tầng, H1 ensemble vs dev-best single, secondary review/viewer, negative route và chuẩn học vụ | Thay **đề xuất** B cũ, không sửa M1/M2; empirical contribution chưa giảng viên duyệt; scope 4N phải khả thi | T0 trước implementation thesis |
| O2 | Protocol mới: four peers/focal rotation/D_ord,m/D_bin,m, majority/abstain/quorum, S/C_m/E_m/M_m, budget/overload, planned Macro-F1/BA/FS, review/CI/multiplicity; HNLO optional theo model | Các công thức/metric/estimand mới PROPOSED, không áp vào M2/pilot cũ; optional learned/calibration arm cần scope riêng | T0 hợp đồng, T2 số, T4 freeze |
| O3 | Final thesis roster/roles; Q3 mốc lịch sử không độc quyền focal; bounded shortlist/sequence/attempt caps/stop sau #148, P1–P4 và vai trò candidates cũ | Chọn Gemma/Phi/Smol khảo sát không = qualified. Historical Q25/IVL3/Moondream2 giữ nguyên; final four dựa D-only evidence/rights/cost, không target | T0 rule; T1 access; T2 qualification; T3 final; T4 freeze |
| O4 | Verified sources, bổ sung cohort và D/V/T/U, GT rubric/expert adjudication/custodian/exposure policy | Thêm nghiên cứu sau approval, giữ InspecSafe raw/split/labels. Owner không thay được license/data-owner authority | T1 trước acquisition/annotation |
| O5 | δ_F, false-safe/severe/abstain/missing/cost guardrails, b, support/precision/min sources, CI/α/multiplicity/seeds/search, user criterion; P1–P4/G5 envelope/counts/behavior stop | Pilot/workload/source simulation/quota thật, không cutoff tự tiện; khóa method trước pilot, exact values trước screening chính/target | T0 rule → T2 values → T4 exact freeze |
| O6 | Mỗi source/model/CPU native/qualification/development/target run grant, storage/export/budget/retry | Exact revision/source/input/run/attempt/env/limits/expiry; a6/a2 consumed, no implied new authority | Trước từng run thuộc scope |
| O7 | Evidence rubric/region labels, reviewers/consent/tasks, image export và usefulness criteria | Không có GT vùng/faithfulness mặc định; thiếu → CT3 chỉ technical demo, không kết luận hữu ích | T1/T2 trước annotation/study |
| O8 | #136/R1–R5 tiếp tục sửa trong đúng PR/session hay dừng sau quyết định; transition lịch sử | Audit FAIL chưa sửa; reuse chỉ sau đúng review/merge/grant, không milestone completed từ đổi lộ trình | T0 trước R |

Tách **quyền tích hợp main vào branch #137** khỏi O1–O8: [ChatGPT đã cho phép](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6487634755) merge main và reconcile state; phải kiểm lại integrated HEAD, không sửa lịch sử bằng rebase/force-push. Scientific approvals chỉ ghi append-only DECISIONS ở task được giao sau, không sửa file đó trong #137. Không coi approval kế hoạch là quyền target/GPU/chữ ký giảng viên.

## 15. NEXT TASK duy nhất và bàn giao

**NEXT TASK duy nhất sau review/audit và Owner duyệt kế hoạch: T0 — Ghi quyết định chuyển tiếp và hợp đồng ba tầng.** Dùng §14 và T0 card, giữ phần chưa duyệt PENDING. #148 ON HOLD cho đến scope tuyển được mở có thẩm quyền; #147 riêng. Không giao GPU/annotation/target hoặc sửa #136 từ PR này.

Gói #137 hiện gồm kế hoạch, PROJECT_STATE, knowledge base và CPU wrapper/tests: `scripts/check_notebook_release.py`, `tests/test_notebook_release.py`. Kiểm GitHub HEAD/diff/status, local links/anchors/tables, UTF-8/no BOM, scope/protected hashes, `git diff --check`, full branch unittest và exact-runtime snapshot command ở runbook; counts/skips/receipt SHA thật trong PR body. Không sửa six released notebooks, không native weights/GPU/TEST/grant. CODE_PASS của wrapper không tự là release PASS, không là audit khoa học độc lập.

**Review boundary:** PRE-AUDIT PASS cũ tại HEAD `6b7b3b9828a61440cb60733fe4640d9a237db0e0` không bao phủ cập nhật này. Theo [chỉ thị 29/10](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6486252968), ChatGPT kiểm GitHub HEAD/diff mới rồi **kiểm toán khoa học độc lập và code gate mới trước bất kỳ merge**. Nếu audit đã bắt đầu, mở rộng delta/final HEAD trong cùng session Antigravity; không tự nhận audit offline đã/chưa xong. Audit FAIL sửa trong cùng Codex session/PR. Quyền tích hợp đã có; PRE-INTEGRATION SOURCE REVIEW PASS tại `68b875b` chỉ cho xử lý conflict, không bao phủ audit integrated HEAD. Dừng đúng OPEN/DRAFT #137, không Ready for Review/merge/scientific approval.
