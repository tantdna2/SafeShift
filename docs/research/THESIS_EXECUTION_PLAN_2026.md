# SafeShift — Kế hoạch thực thi Khóa luận tốt nghiệp 2026

Ngày xác minh: **27/10/2026, Asia/Bangkok**. Trạng thái: **PROPOSED — PENDING OWNER APPROVAL**.
Repository: [tantdna2/SafeShift](https://github.com/tantdna2/SafeShift).
BASE_SHA: `28fdf82512577f2ed0fb435fb2c12b88e82baf2f`; branch: `docs/thesis-execution-plan-20261027`.
HEAD ghi trong mô tả [Draft PR #137](https://github.com/tantdna2/SafeShift/pull/137) để tránh hash tự tham chiếu; cập nhật này tiếp tục cùng branch/PR.

**Owner đã quyết định bỏ học phần Seminar riêng và chuyển thẳng sang Khóa luận trong yêu cầu ngày 27/10. Điều đó không đồng nghĩa Owner đã duyệt phương pháp, metric, dữ liệu hay quyền chạy trong bản đề xuất này.** M1/M2 lịch sử giữ nguyên hiệu lực đúng phạm vi. Tất cả thiết kế mới dưới đây, kể cả công thức, ngưỡng, feature set và task tương lai, đều chờ quyết định mới trước áp dụng. Tài liệu không sửa protocol/config đã khóa.

## 1. Executive Summary

Khuyến nghị **B làm trung tâm: kiểm chứng giá trị tăng thêm của HNLO và bất đồng liên mô hình trong xếp ưu tiên các ảnh bị Qwen3 kết luận Normal nhưng thực tế có nguy cơ**, tại cùng ngân sách kiểm tra. Giữ predictor Qwen3 cố định. Dùng hồi quy logistic có regularization tối giản; không nhận logistic, ensemble disagreement hay selective prediction là thuật toán mới. Đóng góp dự kiến là bằng chứng thực nghiệm có đối chứng, tách nguồn, xét lỗi bất đối xứng, missingness và chi phí toàn bộ mô hình.

Đề xuất hai phần hỗ trợ có giới hạn: **A là đối chứng chẩn đoán** dùng ngưỡng HNLO chọn trên validation cho quyết định nhị phân; **C là case-review viewer** truy nguồn và hỗ trợ người kiểm tra đánh giá chứng cứ. Không xây thêm một thuật toán grounding, hệ thống nhiều agent, VLM fine-tuning hay ensemble thay nhãn. Ba cấu hình cốt lõi là HNLO-only → disagreement-only → logistic kết hợp, đủ để kiểm CT2 mà không ghép tất cả gợi ý của giảng viên.

**Điều kiện chọn B:** giảng viên chấp nhận cải thiện chất lượng phân bổ kiểm tra là đóng góp chính của CT1, thay vì bắt buộc tăng Macro-F1 của predictor. Nếu yêu cầu học vụ là tăng trực tiếp chất lượng nhãn, A phù hợp hơn và phải được Owner chọn lại trước thực thi. Không được dùng tỷ lệ bắt lỗi của triage để báo predictor đã tăng Macro-F1. C đáp ứng CT3 bằng đánh giá tác vụ có người, không chỉ giao diện đẹp; việc đánh giá bằng chứng không được biến thành đo cơ chế suy luận nội tại của VLM.

Rủi ro quyết định không nằm ở việc fit logistic mà ở **nguồn độc lập, nhãn chuyên gia, số sự kiện false-safe, tín hiệu bất đồng có biến thiên, quyền GPU và người giữ target**. Chưa có bằng chứng đủ cho các điều kiện này. NO-GO phải được chấp nhận sớm; không thay target bằng TRAIN đã phơi nhiễm hoặc mở TEST. Nếu giả thuyết không thắng, vẫn bàn giao benchmark có giới hạn, đối chứng/ablation, phân tích lỗi và công cụ review; mức đủ chuẩn tốt nghiệp phải được giảng viên xác nhận, không được tự hứa.

Lộ trình duy nhất: **T0 quyết định và protocol → T1 quyền/nguồn → T2 dữ liệu–pilot → T3 baseline/phương pháp/development → T4 freeze → T5 xác nhận và phân tích lỗi → T6 luận văn/gói tái lập**. Viewer được hoàn thiện trong T3; đánh giá người dùng nằm T5. Nhánh tái sử dụng R1–R5 là hỗ trợ lịch sử, không còn cửa ải bảo vệ Seminar trước khi làm Khóa luận. Chưa đánh dấu M3/M4/M5 hoàn thành hoặc hủy trong lịch sử.

Owner đã chốt ba ứng viên bổ sung Gemma 3 4B, Phi-3.5 Vision và SmolVLM2 2.2B để khảo sát (§10.1–10.3). Q3 vẫn predictor; compatibility FP16/T4 và utility chưa chứng minh. Tuyển tuần tự qua P1–P4, đề xuất tối đa một auxiliary sau O3/T0; không thay roster lịch sử hoặc tự cấp quyền chạy.

## 2. Trạng thái thực tế và thẩm quyền

### 2.1. GitHub đã kiểm trực tiếp

Đã fetch `origin/main`, tạo worktree riêng từ BASE trên, đọc metadata PR và toàn bộ discussion #133–#136 qua GitHub connector. Trạng thái này là snapshot ngày 27/10, phải kiểm lại ở task kế tiếp. Không dùng nội dung PR body cũ ghi “DRAFT” thay trạng thái API mới.

| Thành phần | Sự kiện đã xác minh | Phân loại / giới hạn |
| --- | --- | --- |
| [PR #133](https://github.com/tantdna2/SafeShift/pull/133) | MERGED 25/10, merge `bffc6032e65b38cb04b33520275a089d87d0d37f`; [hậu merge](https://github.com/tantdna2/SafeShift/pull/133#issuecomment-6399480255) | Hai tài liệu hướng/Master Plan; merge tài liệu không phải bằng chứng triage thành công. |
| [PR #134](https://github.com/tantdna2/SafeShift/pull/134) | MERGED 26/10, merge `a425ab04695319a42bfdd2f89192717dddbb891b`; [hậu merge](https://github.com/tantdna2/SafeShift/pull/134#issuecomment-6406526361) | Execution Plan và PROJECT_STATE; [Owner directive](https://github.com/tantdna2/SafeShift/pull/134#issuecomment-6406751802) là nguồn M1. |
| [PR #135](https://github.com/tantdna2/SafeShift/pull/135) | MERGED 26/10, merge = BASE; [hậu merge/giao M3](https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6409830030) | M1 EFFECTIVE cấp dự án; M2 v1 FROZEN theo quyết định + SHA + hậu merge. Không có chữ ký học vụ hoặc quyền Khóa luận. |
| [PR #136](https://github.com/tantdna2/SafeShift/pull/136) | OPEN/DRAFT, chưa merge; HEAD `b252e4cd469346c781183c69bad481ad9b69eff9`; 10 files, +2219/-230 | M3 IN_PROGRESS; [audit FAIL được đối chiếu](https://github.com/tantdna2/SafeShift/pull/136#issuecomment-6412563251). 77 tests là báo cáo local trong PR, không được nhận là kiểm toán độc lập hoặc test của task này. |
| Foundation V1 và saved-score tooling | Có trên main: records/validation/exact join, confusion, weighted AUROC, source-sensitivity CLI, transport interface | Không có backend VLM, raw writer, triage, viewer hoặc thesis experiment engine hoàn chỉnh. [Kiến trúc](../ARCHITECTURE.md) và module hiện hữu đã đối chiếu. |

Lỗi #136 chưa được ghi nhận sửa ở HEAD đã kiểm: R4 hiểu path chứa `|`/`->` sai thành cặp model, tạo planned_n=0 và exclusions âm; R3 missing_composition lấy M224 nhưng metadata ghi T3763/success IDs; thêm lỗi không blocking ở eligibility/model của ô HNLO true×predicted. Đã đọc trực tiếp [report_rows tại exact HEAD](https://github.com/tantdna2/SafeShift/blob/b252e4cd469346c781183c69bad481ad9b69eff9/scripts/analyze_seminar.py), thấy các nhánh mapping tương ứng; không chạy counterexample hoặc tự nhận audit độc lập mới. Đây là **lỗi bằng chứng hàng báo cáo**, không chứng minh công thức HNLO sai. Task này không sửa/đóng/merge/rebase PR đó.

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

Root ROADMAP/TASKS của workspace cũ đã được kiểm tra khi bắt đầu; main mới không có chúng. Theo AGENTS hiện hành, dùng docs/ROADMAP và docs/EXECUTION_PLAN, không nhập lại legacy. Các dòng premerge trong README/ROADMAP/EXECUTION_PLAN là snapshot cũ, được diễn giải bằng receipt GitHub; PR này chỉ cập nhật PROJECT_STATE và kế hoạch mới.

## 3. CT1–CT3 và E1–E5: đáp ứng có điều kiện

Đã đọc cả hai trang **Cai Tien Theo 4 Huong 2026 - SafeShift.pdf**, do Owner cung cấp; SHA-256 `840612616de206b5b882309cd175bc743a129387c981822dfb0c8c271b576c0d`. Không đưa PDF vào Git hoặc ghi đường dẫn máy cá nhân. Đây là nguồn yêu cầu/gợi ý học thuật, không là lệnh cấp quyền chạy và không là phê duyệt thiết kế này. Hai ảnh đính kèm xác nhận phân loại CV-B/D, CV-B/C, CV-C/D.

| Yêu cầu | Thiết kế tối thiểu khuyến nghị | Điều kiện/ranh giới |
| --- | --- | --- |
| CT1: chất lượng | Mapping canonical bất biến; bảng AUPRC/AP, Macro-F1, Balanced Accuracy, FNR/FPR theo miền cho predictor và arm A; B đo capture false-safe cùng workload, worst-domain và CI theo nguồn | Tăng capture không tăng Macro-F1 của predictor. CT1 chỉ được coi đáp ứng theo B sau xác nhận học vụ; chưa có cải thiện. Các metric mới chờ O2. |
| CT2: phương pháp | Logistic hai feature HNLO-Q3 + disagreement ordinal; HNLO-only, disagreement-only, full; ablation supervision/weighting; LODO development nếu source cho phép | Không cần fine-tune, prompt grounding hay nhiều ensemble khác nhau. Temperature/isotonic chỉ đối chứng khi đủ input/nhãn. |
| CT3: chức năng | Viewer nhãn/điểm ưu tiên/status/provenance; ảnh/vùng hỗ trợ chỉ khi có quyền và semantics hợp lệ; ba tình huống, audit reason và task-based evaluation | Không vẽ heatmap giả; score chưa calibrated không mang nhãn confidence %. Thiếu chuyên gia/region evidence thì phần usefulness/faithfulness tương ứng chưa đạt. |
| E1 | Cùng frozen outputs, ID, labels, partition, review budget, tuning budget; báo matched-information và chi phí thực mỗi policy riêng | Không lấy arm A đổi predictor vào contrast chính của B; không coi model phụ miễn phí. |
| E2 | Bỏ từng feature, source weighting; constant/random controls; A threshold vs calibration+threshold; viewer label-only vs evidence view | Chỉ ablate thành phần thực có, không tạo thêm module để có ablation. |
| E3 | Mất cân bằng, LODO có group purge, nguồn mới, rare/khó, shared blind spots, thiếu model/overload, kết quả âm | Không đổi phân bố target để có nhiều lỗi; không gọi folder-domain holdout là nguồn độc lập. |
| E4 | Ít nhất ba nhóm lỗi và ba case trước–sau từ dữ liệu được phép; đưa cả sửa được, không sửa được hoặc gây hại | Trước–sau của B là routing/review, không đổi nhãn Q3; chưa có ba case thật trong task lập kế hoạch. |
| E5 | Commit/config/model revision/raw output/run ID/checksums/seed/env/command, audit ledger, nhỏ synthetic fixtures và hướng dẫn tái lập | Raw/dataset/weights ngoài Git; không gán kết quả synthetic thành khoa học. |

Các metric chung như mAP, BLEU/WER, Event-F1 trong khung PDF không trở thành endpoint bắt buộc của phân loại ảnh này. IoU chỉ hợp lệ nếu có ground truth vùng và bài toán localization đã duyệt. Chọn kỹ thuật theo câu hỏi, không theo số mục trong danh sách.

## 4. So sánh A, B, C và lựa chọn

| Tiêu chí | A — Ngưỡng/hiệu chuẩn quyết định | B — Xếp ưu tiên false-safe, predictor cố định | C — Kiểm toán bằng chứng làm trung tâm |
| --- | --- | --- | --- |
| Câu hỏi kiểm chứng | Ngưỡng validation có giảm FNR mà giữ FPR/quality guardrail trên nguồn mới? | Bất đồng thêm ích lợi ngoài HNLO ở cùng review budget/chi phí? | Audit có nhận diện quyết định thiếu chứng cứ và giúp examiner chính xác hơn? |
| Tính mới | Thấp nếu chỉ temperature/isotonic; giá trị nằm ở đánh giá công nghiệp/shift có kiểm soát | Logistic/triage đã có; khoảng trống hẹp ở giá trị tăng thêm trên false-safe và nguồn tách biệt | Viewer không là thuật toán mới; phương pháp audit cần rubric/ground truth về evidence riêng |
| CT1–CT3 | CT1 trực tiếp; CT2 post-processing; CT3 phải thêm viewer | CT1 ở quyết định review, CT2 trực tiếp, CT3 qua viewer nhỏ | CT3 trực tiếp; CT1/2 cần chứng minh hiệu quả quyết định, không chỉ giải thích |
| Nhãn/dữ liệu | Hazard/normal và validation nguồn tách biệt; bốn mức cần đủ support, không suy từ scalar | Nhãn chuẩn + frozen prediction để tạo e_FS; sự kiện lỗi hiếm hơn hazard | Nhãn đúng/sai + vùng/claim evidence + chuyên gia adjudication; khó nhất |
| Tận dụng hiện có | HNLO, mapping, historical score/nhãn dùng phát triển sau quyền | Tận dụng HNLO, disagreement contract, frozen Q3, R1–R4 | Chủ yếu provenance/ảnh; polygon đối tượng không đủ chứng cứ lý do |
| Model/GPU | Có thể chỉ Q3 cho phương pháp; roster vẫn giữ bốn; fit CPU | Q3 cố định + auxiliary được O3 duyệt sau P1–P4 (§10.1–10.3); ba ứng viên mới chưa qualified, roster lịch sử giữ nguyên; fit CPU nhưng thêm inference | Có thể một VLM + người, hoặc nhiều call/crop/grounder nếu mở rộng; không rẻ mặc nhiên |
| Baseline mạnh | Generated label; HNLO threshold; logistic scalar; constant controls; calibration đơn điệu | Q3-HNLO-only và learned scalar, random-Normal, disagreement-only, cùng supervision | Label-only/manual review; metadata-only; evidence view; nếu thuật toán audit: expert labels |
| Ablation | Threshold-only vs calibrated+threshold, global vs domain weights; mapping audit không relabel | Bỏ HNLO, bỏ D, bỏ weighting; feature variance/chi phí auxiliary | Tắt vùng/nguồn/cờ audit; task order/case matching; không sửa predictor giữa arm |
| Rủi ro chính | Threshold overfit, class imbalance, tuning trên target, calibration bị nhầm ranking | Ít e_FS, D suy biến, correlated errors, selection bias do missing, auxiliary cost | Rationale hợp lý nhưng không faithful; thiếu nhãn vùng, automation bias, tải gán nhãn |
| Khả thi sinh viên | Tốt nhất về triển khai; tính đủ mới phải được giảng viên chấp nhận | Có điều kiện; scope nhỏ nếu hai feature, nguồn/nhãn là critical path | Thấp hơn nếu đòi causal evidence algorithm; viewer nhỏ khả thi |
| Nếu không cải thiện | Bảng operating points/shift failure, calibration limits | Negative result về giá trị D/HNLO, trade-off, evaluator/viewer | Rubric/annotation agreement, lỗi evidence, usability limitations |

**Vì sao chọn B có điều kiện:** A rẻ hơn và phù hợp trực tiếp với chất lượng nhãn, nhưng hiệu chuẩn đơn điệu không tạo thêm thông tin xếp hạng và threshold-only phải là đối chứng mạnh trước khi nhận có phương pháp mới. C đầy đủ cần một lớp ground truth khó hơn đáng kể và thêm can thiệp/call để kiểm causal faithfulness. B đặt câu hỏi hẹp có thể bác bỏ, tận dụng tín hiệu đã có, tách lớp quyết định khỏi mô hình, đồng thời cho phép C là chức năng kiểm toán phục vụ chính hàng đợi đó. Đây là lựa chọn về phạm vi và khả năng kiểm chứng, **không dựa vào số đo cho thấy B đã tốt hơn A/C**.

**B không tự thắng:** nếu pilot không đủ events/source, D không biến thiên trong tập Q3-Normal, hoặc auxiliary cost vượt trần, B có thể không khả thi/không hữu ích. Nếu cần nhãn tốt hơn trực tiếp, chọn A qua O1/O2 mới; nếu thiếu region labels, không chuyển sang C như một lối tránh thiếu dữ liệu. Không chạy A+B+C như ba luận văn song song.

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

Suy luận từ tổng hợp: đóng góp khả thi là **kiểm định giá trị gia tăng và giới hạn của một policy review cụ thể**, có dữ liệu/nhãn/nguồn và đối chứng đủ mạnh. Không đủ cơ sở hứa kiến trúc mới, causal grounding, uncertainty calibrated hay vị trí SOTA. Cần giảng viên xác nhận đóng góp thực nghiệm như vậy đủ chuẩn Khóa luận (O1). Không mở lại P1/P2/P3 vì không có bằng chứng mới buộc đổi kiến trúc.

### 5.3. Skill thực sự dùng

Đã truy cập và đọc SKILL.md của `literature-review` v1.11 (phạm vi/tìm kiếm/nguồn sơ cấp), `experimental-design` v1.5 (đơn vị nguồn, paired controls, blocking, reviewer study), `scientific-critical-thinking` v1.5 (confounding, missingness, claim/estimand). Không thấy skill Review Agent trong catalog khả dụng và tìm kiếm local; không dùng agent review hoặc nhận tự rà soát là audit độc lập. Không cài skill mới, không dùng slide/image skills, không chạy script skill bên thứ ba; không có statistical-power skill được dùng và không báo power đã tính.

Ghi công phương pháp theo yêu cầu các skill: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065). Metadata kiểm trên arXiv ngày 27/10: bản hiện hành v2, 02/09/2026; dùng DOI không suffix. Skill giúp cấu trúc công việc, không là bằng chứng kết quả SafeShift.

## 6. Đề tài, phương pháp và giả thuyết đề xuất

### 6.1. Tên, đối tượng và đóng góp

- **Tiếng Việt:** SafeShift: Đánh giá tín hiệu HNLO và bất đồng liên mô hình để ưu tiên kiểm tra các quyết định bỏ sót nguy cơ an toàn công nghiệp.
- **English:** SafeShift: Evaluating HNLO and Cross-Model Disagreement for Prioritizing Review of False-Safe Industrial Hazard Decisions.
- **Người dùng:** người kiểm tra an toàn có chuyên môn và người phân tích nghiên cứu, trên ảnh tĩnh/lô ảnh được phép. Không triển khai điều khiển thiết bị, quyết định an toàn tự động hoặc đo giảm tai nạn.
- **Đóng góp dự kiến:** (i) protocol/evaluator phân biệt classification, hazard ranking và false-safe triage; (ii) kiểm định gia tăng HNLO+D dưới ràng buộc nguồn/workload/chi phí; (iii) case-review có provenance và bằng chứng usefulness theo tác vụ. (iii) là sản phẩm hỗ trợ, không thêm một luận án về grounding.

### 6.2. RQ và hypotheses

| RQ | Giả thuyết/estimand định trước | Bằng chứng có thể bác bỏ |
| --- | --- | --- |
| RQ1 — D có thêm ích lợi cho HNLO trong Q3-Normal? | H1: chênh capture_FS tại budget b của logistic(s3,D) so baseline mạnh nhất khóa từ development lớn hơn δ, trên target tách nguồn; thỏa cost/group guardrails | CI không vượt δ, D hằng, HNLO-only bằng/tốt hơn, hoặc auxiliary cost vượt trần. |
| RQ2 — Lợi ích giữ được dưới shift/imbalance/missingness? | H2 phụ: mức suy giảm theo miền/nguồn không vượt γ đã khóa; không overload dưới workload định trước | Nhóm không support → chưa xác định, không coi PASS; shared errors hoặc dropout phá thứ hạng là bằng chứng giới hạn. |
| RQ3 — Evidence view có ích cho examiner? | H3 phụ: tăng độ đúng của tác vụ review ít nhất δ_U hoặc giữ độ đúng trong biên γ_U và giảm thời gian ít nhất δ_t; chọn **một** tiêu chí trước pilot chính | Người dùng quá tin cờ/score, quyết định sai thêm, chậm hơn; khảo sát hài lòng không thay accuracy/time. |
| RQ-A chẩn đoán — Ngưỡng giải quyết được khoảng cách score/label? | H-A phụ: threshold chọn trên validation giảm FNR ở FPR mục tiêu α_FPR, kèm Macro-F1/BA; báo chênh và CI | FPR target vượt α_FPR, calibration không thêm so threshold-only, domain xấu/undefined. Không là H1. |

H1 là **một contrast xác nhận chính**; H2/H3/H-A phụ, có điều chỉnh đa kiểm định nếu dùng để kết luận xác nhận. HNLO hazard AUROC lịch sử không chứng minh H1. Trong tập Q3 dự đoán Normal, e_FS trùng nhãn hazard; công trình phải thừa nhận đây là hazard ranking **có điều kiện**, không gán hai endpoint đó thành hai phát hiện độc lập.

### 6.3. Predictor, feature và fit

Giữ Qwen3-VL-8B-Instruct làm predictor; revision/prompt/preprocess/precision/decoding/parser phải được khóa mới trước pilot. Muốn kế thừa revision V4 `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` phải chứng minh khả năng capture và có grant mới; không giả run V4 được phép chạy lại trên source mới. Owner đã chọn ba ứng viên auxiliary ở §10.1 để **khảo sát**, chưa chọn model dùng trong phương pháp. Q25/IVL3/Moondream2 vẫn thuộc roster lịch sử; vai trò feature/N/A Khóa luận cần O3/T0 riêng, không mặc nhiên theo ngoại lệ Seminar.

**Đề xuất vẫn chỉ hai feature:** `x=(s3_std,D_std)` trên ca Q3-Normal, với `s3=logsumexp(z1,z2,z3)-z4` đúng native decision step. Contract cũ `D_ord` là trung bình ba cặp Q3/Q25/IVL3 của `abs(index(label_m)-index(label_n))/3` (Level01=1,…,Level04=4); giữ tên/công thức đó, không đổi nghĩa kết quả lịch sử. **Biến thể đề xuất chờ O3/T0:** chọn tối đa một auxiliary mới j vượt P1–P4, dùng `D_j=abs(index(label_Q3)-index(label_j))/3`; trong C, đây là biến đổi mức hazard mà j dự đoán, không phải tín hiệu độc lập với nhãn j. Tất cả ký hiệu D phía sau là contract được O3 chọn và T4 freeze, không tự trộn D_j với D_ord hoặc cộng ba ứng viên thành thêm ba features. Contract Q3/Q25/IVL3 chỉ chạy comparator nếu có dữ liệu/quyền/ngân sách tương ứng; không bắt buộc chạy lại roster để tuyển ứng viên.

Auxiliary chỉ cần nhãn canonical hợp lệ cho D, không bắt buộc HNLO/logits phụ; vẫn phải lưu raw text trước parse. Không lấy trung bình raw HNLO khác model. Vote entropy H2/H4 chỉ diagnostic theo contract tương ứng, không đếm như feature mới. Khác họ model chỉ là lý do khảo sát, chưa chứng minh lỗi độc lập hay đóng góp mới. Việc thêm ứng viên không thay tên đề tài, RQ/H1, metric, CT1–CT3/E1–E5 hoặc kết luận ưu tiên B; P3 có thể bác bỏ utility của mọi ứng viên.

Logistic có L2: fit intercept + hai hệ số trên development, objective weighted binary log-loss + penalty hệ số (không penalty intercept), target e_FS; normalization fit trong mỗi training fold. Source weighting đề xuất mỗi verified source có tổng trọng số bằng nhau, normalize mean weight=1 trong fold; image-weighted là ablation. Không mặc nhiên class-balance/oversample vì sẽ đổi calibration/estimand. Các biến thể domain-balanced chỉ sensitivity đã duyệt; domain không thay source.

Chọn strength regularization bằng grouped cross-validation trên development, cùng grid hữu hạn và số lần fit cho các learned baselines; tối ưu capture tại b trong validation folds, tie chọn penalty mạnh hơn rồi quy tắc xác định. Grid/folds/seeds/min events được khóa T2 trước T3, không mở search không giới hạn. Nếu thiếu class trong fold → không fit mô hình đó, ghi NO-GO/giảm complexity theo quyết định; không giả score từ hằng để gọi fit PASS. Feature hằng phải báo và không chia std=0; fitted effect không nhận có bằng chứng.

**Không đưa** GT, tên file chứa Level, sample/source ID, nhãn vùng hậu kiểm, quyết định người review, domain prevalence target hoặc summary dùng target labels vào feature. Source ID chỉ dùng split/weights/CI. Logistic output gọi là **điểm ưu tiên dự báo lỗi**, không confidence đã hiệu chuẩn. Calibration của output nếu cần là phần phụ fit trên calibration riêng và đánh giá độc lập.

### 6.4. Policy, tập đủ điều kiện và ngân sách

Khóa batch formation theo đơn vị công việc examiner trước xem outcome (cỡ batch/quy tắc thời gian trong T2); đề xuất mỗi batch nằm trong một verified source component, nguồn có nhiều batch vẫn là một cluster suy luận. Nếu workflow bắt buộc trộn nguồn, phải khóa thiết kế phụ thuộc batch–source và CI tương ứng ở T2, không giả cluster độc lập khi queue liên kết chúng. Không ghép lại batch target để có lợi. Dùng n(S) hay |S| để chỉ số phần tử tập S. Định nghĩa cho mỗi batch:

| Ký hiệu | Định nghĩa đề xuất |
| --- | --- |
| P | Mọi sample planned trong batch; N=n(P), manifest bất biến, có GT adjudicated ở bước đánh giá. GT unresolved giữ ledger và tách metric eligibility. |
| O3, L3 | Có output Q3; L3⊆O3 có canonical label. INVALID khác no-output. |
| C | Ca trong L3 với Q3=Level04; tập có nguy cơ false-safe theo định nghĩa. |
| M | Mandatory review: Q3 no-output/INVALID; trong C thiếu HNLO-Q3 hữu hạn hoặc nhãn auxiliary mà contract D đã chọn yêu cầu. Không đòi output của ứng viên đã loại/chưa thử. Tập M dùng chung cho **matched-information contrast**. Thiếu input không fill Normal. |
| E | C trừ M, đủ hai feature. Eligibility không dùng GT; đánh giá supervised thêm GT-valid mask và báo exclusions riêng. |
| K, k | K=floor(b·N), b trên toàn planned, không trên riêng C; k=min(n(E), max(0,K−n(M))). |
| R_a | M cộng top-k E theo điểm arm a; nếu n(M)>K → OVERLOAD, không tuyên bố đạt cùng budget b; không tự xử lý ca M. |
| Tie | Seed + opaque pseudonymous ID hash, không filename/GT, chung giữa arms; khóa trước target. Báo tie-block sensitivity không tùy chọn theo kết quả. |

Không dùng ngân sách thừa để chuyển hazard-labeled cases rồi tính như bắt thêm false-safe; báo unused capacity nếu |E|<K−|M|. Mọi arm chính dùng cùng M/E/K, predictor/output và batch; không so complete-case score của arm này với cohort khác. Case thiếu model phụ của single-model policy không nhất thiết mandatory ở triển khai thật: **bảng policy/cost thực tế phụ** dùng failure rule riêng được khóa, có coverage/mẫu số riêng, không thay matched contrast để tạo thắng giả.

Technical failure vượt capacity là **NO-GO vận hành**; hàng đợi báo overload/escalation, không tự kết luận an toàn. Review là cơ hội phát hiện lỗi; chưa có kết quả examiner thì không coi lỗi đã sửa. Ba trạng thái nhãn gốc, routing và human adjudication luôn tách field/record.

### 6.5. Đối chứng và arm A có giới hạn

| Arm | Bắt buộc/điều kiện | Vai trò |
| --- | --- | --- |
| No-review / all-review | Bắt buộc, mốc biên; không đối chứng cùng budget | Kiểm ceiling và denominator; all-review không giả chuyên gia luôn đúng. |
| Random E, random mọi eligible | Random E bắt buộc cùng k/seed; random toàn L3 là diagnostic riêng vì universe khác | Ngăn thắng chỉ vì tập trung Q3-Normal. Repeat seeds định trước, không chọn seed tốt. |
| Q3 HNLO-only | Bắt buộc, s3 cao ưu tiên C; learned logistic(s3) cùng supervision | Đối chứng tiết kiệm inference mạnh; monotone scalar fit có thể không đổi ranking. |
| D-only | Bắt buộc raw D và logistic(D) cùng supervision | Kiểm bổ sung thông tin; H2/H4 diagnostic theo contract. |
| Full logistic(s3,D) | Phương pháp trung tâm | So cùng E, predictor, labels/search budget. |
| Full image-weighted | Bắt buộc ablation source weighting nếu full có source weights | Nếu registry không đủ thì không được gọi source-weighted full. |
| A: Q3 HNLO threshold | Bắt buộc đối chứng chẩn đoán sau O2, trên cohort có score/GT | Tạo **nhãn nhị phân phụ**, không thay label bốn mức Q3 hoặc đi vào H1. Threshold chọn validation, khóa trước target. |
| Logistic hazard scalar / isotonic | Logistic scalar có thể dùng A; isotonic chỉ khi validation support đủ qua pilot | So threshold-only vs calibration+threshold; không kỳ vọng ranking tăng do biến đổi đơn điệu. |
| Entropy4/margin/p_generated | Chỉ khi raw four-token logits, prefix/normalization semantics đã qualified | Không khôi phục từ scalar HNLO, không dùng self-reported confidence thay thế. Thiếu → N/A, claim giảm. |
| LMN/TrustVLM thích nghi | Chỉ nếu đủ input, labels, cost và task tương thích, Owner duyệt trong T0/T2 | Không bắt buộc thêm encoder/embeddings để có tên baseline. N/A không cho claim outperform. |

Baseline chính H1 chọn **một** trong các đối chứng đơn tín hiệu HNLO/raw+learned và D/raw+learned trên development theo criterion đã khóa; ghi tất cả, không chọn trên target. Đối chứng đơn model giữ chi phí thực thấp hơn, còn phép so signal dùng cùng cached input cho fairness; báo hai góc nhìn để không che phụ phí model. Ablation tối thiểu tương đương ba cấu hình PDF: s3, D, s3+D; bỏ source weighting là thứ tư nếu dùng. Hai-feature Normal-only làm “chỉ Q3” trùng HNLO-only, không đếm thành ablation độc lập. Đích mọi lỗi bốn mức cần universe L3 và contract khác, chỉ exploratory được duyệt, không thêm vào core để phình scope.

P3 lặp đúng bộ HNLO-only, D_j-only, HNLO+D_j cho từng ứng viên còn đủ điều kiện, cùng grouped folds/search budget và ID; báo chênh so **HNLO-only và baseline mạnh nhất**. Chọn model trên development là một phần search, phải tính cả số ứng viên/attempt đã thử, kể cả FAIL; không dùng target để chọn winner. Fairness xuyên ứng viên dùng panel ID chung của các finalist và bảng coverage/cost vận hành toàn planned (§10.3), không xếp hạng các complete-case cohort khác nhau.

Temperature scaling trên bốn logits không đổi argmax bốn lớp khi T>0, nhưng HNLO tính lại từ `z/T` **không đồng nhất** với `s/T` và có thể đổi thứ hạng aggregate hazard. Scalar sigmoid(a·s+c), a>0, giữ thứ hạng; isotonic có thể tạo ties. Tất cả phải khóa công thức cụ thể, không hứa tăng AUPRC qua calibration đơn điệu. A dùng một global threshold, chọn sao FPR validation≤α_FPR với recall hazard lớn nhất; tie chọn FPR nhỏ hơn rồi threshold cao hơn. Per-domain thresholds chỉ phụ khi đủ support và có O2 riêng; không fit threshold trên từng domain target.

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

Custodian lập phân bổ theo nhóm trước inference, stratify theo domain và thông tin hợp pháp được định trước, không theo score/lỗi Q3 target. Các ca “khó” chọn từ điều kiện ảnh/nhãn do expert định trước, không chỉ cherry-pick misses. Nếu dùng enrichment theo nguy cơ để tăng events, tách challenge set khỏi target tự nhiên; chỉ claim prevalence thực khi có sampling probabilities/weights đã duyệt. Không gộp challenge vào AP/capture chính.

LODO trên D bỏ toàn bộ domain giữ lại **và mọi source component liên quan** khỏi fit/preprocessing/tuning. Nếu một source trải nhiều domain, purge cả source; số miền/folds khả dụng báo thật, fold thiếu lớp/events → undefined. Đây là stress test nội bộ, không thay T độc lập. Mọi normalization/feature selection/imputation/calibrator nằm trong training fold; không scan statistics T để chọn hyperparameters. User-study cases riêng U, không lộ T qua viewer trước khi freeze T.

### 7.3. Ground truth và evidence audit labels

Giữ canonical Level01–04 và Anomaly=Level01–03. Với cohort mới: rubric do chuyên gia xác nhận tương thích định nghĩa gốc; ảnh không đủ căn cứ → UNKNOWN/UNRESOLVED ở audit layer, không ép thành Normal hoặc tự tạo level thứ năm trong dataset. Hai người có chuyên môn gán nhãn độc lập, **mù VLM/score/routing**, sau đó adjudicator xử lý bất đồng; lưu từng nhãn, lý do, consensus và version. Nếu chỉ đủ một annotator, gọi single-rater, chưa đạt gate GT đề xuất trừ khi Owner/giảng viên phê duyệt mức claim thấp hơn.

Đo raw agreement và confusion giữa annotators, κ có denominator/support; κ undefined nếu marginals suy biến. Ngưỡng agreement, tỷ lệ unresolved tối đa, mức severity cần chuyên gia nào được khóa sau pilot rubric, trước annotation target. Không tự sửa nhãn gốc InspecSafe theo review; lưu đề xuất discrepancy riêng. Annotator không dùng VLM làm ground truth hoặc dùng chính explanation model để hợp thức nhãn.

Vùng hỗ trợ cần nhãn **liên hệ vùng–hazard claim** do người đánh giá xác nhận, có tọa độ/transform/image hash. Polygon object chỉ chứng minh vị trí đối tượng, không tự là nguyên nhân nhãn nguy cơ. Không có vùng hợp lệ → viewer hiển thị “chưa có bằng chứng vùng đã kiểm chứng”. Model không sinh reason trong frozen output → reason fidelity N/A, không bịa explanation hậu nghiệm.

Rubric audit tối thiểu: đúng nhãn/đúng sai chưa rõ; chứng cứ có nhìn thấy; liên quan hazard; đủ để hỗ trợ claim; có mâu thuẫn; source/provenance hợp lệ. “Correct-answer-wrong-reason” chỉ ghi **correct label + stated evidence unsupported/contradicted** sau adjudication, không khẳng định biết cơ chế nội tại. Nếu không có stated reason, ghi evidence unavailable. Đòi causal claim cần occlusion/counterfactual controls + quyền inference/nhãn mới, ngoài core hiện tại.

### 7.4. Cỡ mẫu/precision, không tự đặt N

T2 phải đo trên development pilot: số independent clusters, kích thước/imbalance clusters, tỷ lệ Q3-Normal, e_FS/severe, missing rate, D distinct values, annotation disagreement và chi phí. Dùng các khoảng hợp lý (không chỉ point estimate tốt nhất) để mô phỏng **paired clustered sampling** cho chênh capture tại b, theo policy/denominator thật. Với annotation study dùng mô phỏng reader×case dependence. Chọn số source/events/cases để đạt CI half-width h và power cho δ theo O5; không dùng quy tắc “N ảnh” hoặc “10 events/feature” như bảo đảm.

Owner chốt `b, δ, γ, α_FPR, h, power_target, min_clusters, min_events, max_undefined_resamples, cost caps` từ workload examiner, pilot và nguồn lực. Giá trị chưa có ở đây là **TBD có chủ sở hữu**, không là mặc định cho implementer. Custodian xác nhận recruitment/sampling/roles theo tiêu chí trước target; không tìm thêm ca target vì model ít sai. Nếu adequacy assessment cần thống kê lỗi target, phải là blind curator procedure được duyệt trước, analyst không nhận score/labels/so sánh; cách xử lý không đủ events đã khóa, không tuyển lại theo outcome. Ưu tiên thiết kế theo pilot và chấp nhận T thiếu precision là inconclusive.

## 8. Metric, thống kê và ma trận bằng chứng

**Toàn bộ endpoint mới ở mục này chờ O2/O5, không bổ sung ngầm vào M2.** Report giữ planned/output/label-valid/score-valid/GT-valid/source-known và membership digest của **đúng tập từng metric**, counts exclusions theo lý do/domain/model. Null + reason thay NaN/Inf/0 giả. Hàng model thiếu là N/A, không 0 điểm.

### 8.1. Metric contract đề xuất

Đặt `a=1[y∈Level01..03]`, `e_FS=1[a=1 và Q3=Level04]` chỉ định nghĩa khi GT và label Q3 hợp lệ. `d_a=1[sample được arm a chuyển review]`; chưa phải human correction.

| Endpoint | Tập/tử số/mẫu số; hướng tốt | Undefined/giới hạn |
| --- | --- | --- |
| **Primary capture_FS(b)** | Trên E có GT: Σ(d_a·e_FS)/Σe_FS, ↑; contrast Δ=full−baseline khóa, cùng E/k | Không e_FS → null `NO_ERROR_EVENTS`; E rỗng → null. Đây là utility trong eligible candidates; không giấu ca M. |
| Operational capture | Trên C có GT, gồm mandatory M∩C: Σ(d_a·e_FS)/Σe_FS; cùng K | Báo cạnh primary để thấy tác động exclusion/mandatory. Q3 no-output không có e_FS, không xem là đúng. |
| Residual false-safe | Số ca a=1, Q3=L04 chưa review; chia tổng GT hazard trong P, ↓; severe riêng y=L01 | Tỷ lệ này chỉ phần có nhãn Q3; báo unresolved hazard do Q3 failure và cận worst-case cộng chúng. Không gọi review là sửa xong. |
| Workload/coverage | n(R_a)/n(P); n(valid Q3 không review)/n(P); mandatory, unused và overload counts | N=0 → null; overload không đưa vào bảng “đạt budget”. |
| Risk–coverage | Trên E: retained e_FS/retained_n; coverage=retained_n/n(E); thêm full L3 risk4 và planned coverage riêng | retained_n=0 → risk null. Curves ở budgets định trước/whole ties; không chọn điểm đẹp làm primary. |
| Error AP / AUROC | E GT-valid, positive=e_FS; score priority; AP=ΣΔrecall·precision ở mỗi unique-score block, không trapezoid PR-AUC; AUROC ties=0,5 | No positives hoặc no negatives → primary comparison null, báo class support; không chọn dấu từ target. AP nhạy prevalence. |
| Hazard AP/AUROC | Score-valid+GT-valid cohort, positive=a, score HNLO; cùng ID giữa arm | Không thay error AP bằng hazard AP toàn cohort. Báo prevalence và coverage. |
| Macro-F1, BA nhị phân | Trên cùng GT/label-valid S: F1_A=2TP/(2TP+FP+FN), F1_N=2TN/(2TN+FP+FN), macro mean; BA=(TP/(TP+FN)+TN/(TN+FP))/2 | Thiếu một true class → macro/BA chuẩn hai lớp null; counts vẫn báo. Confusion/INVALID/no-output trên toàn planned báo riêng, complete-case không thành toàn hệ thống. |
| Bốn mức | Confusion 4×5 và support/recall giữ M2; diagnostic F1_l=2TP_l/(2TP_l+FP_l+FN_l), INVALID nằm FN của true class; macro trên lớp support>0 ghi số lớp | Không so macro khác class-set như cùng endpoint; bốn-class standardized macro null nếu thiếu lớp. A nhị phân không có F1 bốn mức mới. |
| FNR@FPR-validation α | A chọn threshold V theo §6.5; T báo FN/A và FP/N tại **ngưỡng frozen**, ALL và từng domain | FPR T không bảo đảm bằng α. Không tune lại target để gọi “fixed FPR”; threshold per-domain chỉ nếu duyệt/đủ V support. Class absent → rate tương ứng null. |
| Worst-domain | Min capture/AP/BA; max FNR/risk trong domains đủ điều kiện đã khóa | Hiện cả miền undefined; không bỏ khỏi báo cáo rồi nói “robust mọi miền”. CI bootstrap recompute min/max, không cố định miền tệ đã chọn. |
| Calibration (phụ) | Brier mean(p−target)², reliability diagram/ECE bins khóa V, trên target đúng đối tượng a hoặc e_FS | Chỉ p có calibration contract; không Brier trực tiếp HNLO. Không gọi ECE thấp là error ranking tốt. |
| Viewer usefulness | Task decision accuracy/expert GT; tỷ lệ phát hiện unsupported evidence; median/p95 time; unsafe acceptance, escalation và missing evidence counts | Task không có GT evidence → N/A; perceived usefulness chỉ mô tả, không chứng minh safety. |

M2 observed FNR/FPR có INVALID trong support được giữ ở bảng lịch sử đúng tên; metric complete-case của Khóa luận phải mang version/tập S riêng, không overwrite số M2. Với unresolved GT, báo số và phân bố, best/worst outcome bounds theo policy đã khóa; không mặc định missing-at-random. Nếu missing/unknown vượt gate T2, kết luận xác nhận bị chặn dù subset có điểm tốt.

### 8.2. Suy luận thống kê

Đề xuất CI **95%**, mức α_stat=0,05, cần O5 duyệt; δ và guardrails chưa chọn số. Paired cluster bootstrap resample verified sources/components, giữ mọi ảnh và tất cả arms trong cùng resample; giữ batch/queue được khóa khi tính main finite-batch estimand (không tái chia lô theo GT). Dự báo khả năng chuyển sang batch mới là estimand phụ, phải resample cả batch và áp policy lại theo protocol. Stratify theo domain chỉ khi source nesting phù hợp; source xuyên domain dùng global component và mô tả marginal slices.

Mỗi bootstrap draw dùng chung nguồn cho full/baseline, tính Δ; percentile interval, số draws/seed khóa T2 và kiểm Monte Carlo stability trên development. Báo số draws undefined; vượt trần đã khóa → CI `INSUFFICIENT_EVENTS`, không chỉ xóa draws đến khi CI đẹp. Ít source không cứu bằng bootstrap ảnh, DeLong i.i.d. hoặc coi các folds là độc lập; dùng descriptive bounds/sensitivity và ghi chưa đủ xác nhận. Source-weighted analysis đổi estimand sang trung bình nguồn, báo phụ cạnh primary per-image; weights fit không tự đổi metric weights.

**H1 benefit PASS** chỉ khi lower CI(Δ)>δ và mọi cost/workload/group guardrail xác định, đạt chuẩn. Upper CI(Δ)<δ: không đạt lợi ích tối thiểu; CI chứa δ: inconclusive. CI dưới 0 là bằng chứng harm tương ứng. CI bao 0 không chứng minh hai phương pháp tương đương. Study execution PASS tách benefit PASS; kết quả âm hợp lệ vẫn DONE. Một primary contrast/budget tránh multiple searching; họ secondary confirmatory có Holm theo family khóa trước, hoặc ghi exploratory và không kết luận significance. Không dùng nhiều seeds/frames như independent N.

User study: phân bổ examiner vào hai sequence giao diện label-only/evidence-view bằng block theo kinh nghiệm; mỗi người thấy hai tập case tương đương nhưng **không cùng case hai lần** để giảm nhớ đáp án. Đảo thứ tự/counterbalance; cùng thời gian và thông tin ảnh, tách hiệu ứng hàng đợi khỏi hiệu ứng giao diện. Analyst chấm bằng rubric/adjudicated GT mù arm khi khả thi; mô hình/CI xét crossed reader và case/source, không bootstrap từng click. Số reviewer/case và δ_U/δ_t/γ_U phải do pilot/precision plan, không tự gọi ba demo là user study.

### 8.3. Ma trận thí nghiệm E1–E5

PASS ở bảng là **PASS thực hiện**, không phải bảo đảm cải thiện. Mỗi thí nghiệm có receipt và output ở `data/processed/thesis/<run_id>/`; chỉ summary nhỏ có quyền vào Git.

| ID / mục đích | Input và phương pháp | Đối chứng / metric | Output / điều kiện PASS / rủi ro |
| --- | --- | --- | --- |
| X0 — hợp lệ dữ liệu/capture, E5 | Quyền + D pilot; exact ID/source/label join, token/prefix/raw-before-parse qualification | Oracle synthetic; expected cohort/status/hashes; failure counts | Contract + pilot receipt; PASS khi không mất ID/raw, source roles đúng, unresolved trong gate. Sai alignment/provenance → NO-GO, chưa fit. |
| X1 — khoảng cách score/label, CT1/E1 | Frozen Q3 trên D/V; A threshold, scalar calibrator khi đủ | Generated binary label, always-N/A, threshold-only vs calibrated+threshold; AP/Macro-F1/BA/FNR/FPR | Operating-point table global/domain và coverage; PASS đủ mẫu số/selection V/không target tuning. A có thể thua; không sửa mapping để cứu điểm. |
| X2 — H1 primary, CT2/E1 | Cùng E và outputs, grouped fit/CV, nguồn target sau T4 | HNLO/raw+learned, D/raw+learned, random E, full; capture@b, cost | Δ/CI, operational panel, ledger; PASS đúng frozen primary, cùng k/M/search budget. Benefit theo §8.2; nguy cơ D hằng/events hiếm. |
| X3 — thành phần, E2 | Cùng partitions/predictor/cached outputs, thay đúng feature/weighting | s3 vs D vs full; image vs source weights; AP/capture/chi phí | Ablation table toàn bộ, kể cả null/âm; PASS không đổi cohort giữa arms. Nhiều runs không thành nhiều nguồn độc lập. |
| X4 — stress, E3 | D LODO group-purged, prevalence scenarios khóa D; T natural slices; rare Level03/severe/khó; synthetic feature-dropout/overload | Full và locked baseline; worst-domain AP/FNR/capture, coverage, failures | Stress matrix và support; PASS đủ scenarios kể cả undefined; source unknown không claim LODO independent. Không thay target prevalence; corruption ảnh chỉ khi quyền/label validity thêm. |
| X5 — error/evidence, E4/CT3 | Error taxonomy + random/stratified authorized case selection, 2 expert reviews | Baseline vs full routing, label-only vs evidence; reason validity, before–after và harm | ≥3 nhóm + ≥3 case thật khi có quyền; PASS trace nguồn, nguyên nhân là hypothesis nếu chưa kiểm, nêu cả không cải thiện. Không chọn chỉ case thắng. |
| X6 — usefulness, CT3/E1/E2 | U riêng, examiner đủ chuyên môn; counterbalanced study §8.2 | Cùng cases theo assignment, image+label vs image+label+evidence; accuracy/time/unsafe acceptance | Study report/CI hoặc descriptive pilot nếu ít người; PASS theo preregistered task design, không chỉ questionnaire; thiếu người → CT3 usefulness BLOCKED. |
| X7 — tái lập, E5 | Frozen source/env/config/inputs/raw hashes, clean authorized environment | Independent formula oracles, deterministic CPU regeneration từ allowed outputs | Receipt và reconciliation bảng/ID hashes; PASS reproduction trong quyền. Không yêu cầu inference lại chỉ để tái lập; stochastic/hardware tolerance khóa, limitations ghi rõ. |

X1–X4 chạy development trước; chỉ arms/contrasts đã khóa được xuất xác nhận trên T. Không có vòng “target cho biết thiếu gì rồi thêm baseline”. X5 định nghĩa taxonomy và selection rule trước target, điền case sau đánh giá; U dùng kiểm usefulness không tái sử dụng để tune H1.

## 9. Case review và error analysis trong phạm vi C nhỏ

### 9.1. User flow dự kiến

Nhận batch/receipt hợp lệ → xem coverage/overload → hàng đợi mandatory rồi top-k → mở case (ảnh có quyền, nhãn Q3 gốc, HNLO, điểm ưu tiên, nhãn auxiliary, provenance) → examiner xem evidence có trạng thái verified/model-generated/unavailable → ghi accept/escalate/đề nghị sửa kèm lý do → lưu record mới và audit log. Không ghi đè prediction/raw/GT. Khi hash/source/image mismatch, chặn hiển thị vùng/ra quyết định theo chứng cứ lỗi, báo degraded state; rollback về nhãn/ảnh gốc chỉ khi còn hợp lệ và được phép.

| Tình huống công việc cần kiểm | Luồng trước–sau dự kiến | Bằng chứng phải thu sau, chưa phải case đã có |
| --- | --- | --- |
| Ca Q3-Normal thực có hazard, được full ưu tiên | Baseline không chọn ở b → full chuyển review; examiner xác minh nguy cơ hoặc vẫn bỏ sót | Sample/run/GT/provenance, rank/budget của hai arm, expert action/time; không gọi “đã cứu ca” nếu chỉ routing. |
| Nhãn hazard đúng nhưng vùng/lý do sai hoặc thiếu | Label-only dễ chấp nhận → evidence view đánh dấu unsupported, yêu cầu kiểm lại | Rubric independent evidence, claim-region relation; đúng nhãn không chứng minh đúng lý do. Không có reason → unavailable, không tự flag wrong-reason. |
| Bất đồng/thiếu output hoặc miền khó gây overload | Điểm không hợp lệ → mandatory/escalation, hiện missing/không giả confidence | Error envelope, capacity và quyết định examiner; không dùng fallback tự gán Normal. |

Ba tình huống là **thiết kế tác vụ**, không phải ba ví dụ thực nghiệm. T5 phải chọn ca thật có quyền theo rule khóa; nếu không có ví dụ được cải thiện, báo trước–sau không đổi hoặc xấu đi, không dựng minh họa giả thành kết quả. Các nhóm lỗi tối thiểu: (1) false-safe/severe miss; (2) false alarm/severity mismatch; (3) unsupported evidence/correct-label-wrong-stated-evidence; thêm technical/provenance failure và shared blind spots khi có. Ghi nguyên nhân quan sát được khác với giải thích giả định; xử lý đề nghị, hiệu quả đo được và giới hạn từng case.

Viewer tối thiểu local/offline, không cần cloud/publish. Confidence numeric chỉ hiện nếu có calibration version/target semantics/validation evidence; nếu chưa, dùng tên “điểm ưu tiên” và “HNLO tương đối”. Không có bounding-box truth thì không IoU; không dùng attention map làm bằng chứng vùng đã xác nhận. Không bật prompt-grounding/crop intervention trong core; nếu muốn cần O2/O4/O6 amendment trước chạy.

## 10. Nguồn lực, quyền và blocker thực tế

Không xác nhận sẵn GPU, tiền, số ảnh mới, chuyên gia hoặc deadline bảo vệ. Các giá trị phải được đo/xác nhận T1–T2; không dùng cấu hình T4 lịch sử làm reservation hiện tại. Fit/metrics có thể CPU; inference Q3-8B và auxiliary là phần chi phí chính. Chạy sequential/cache giảm peak residency, không giảm tổng model calls hoặc tự làm T4 đủ VRAM.

| Khoản | Cách ước lượng/kiểm trước duyệt run | Quyền/điều kiện thiếu |
| --- | --- | --- |
| Calls/GPU time | Sau tuyển chọn: Q3 trên N ảnh + J·n(C) calls cho J auxiliary đã freeze (đề xuất J=1); thêm tổng pilot/qualification P1–P4 của mọi ứng viên đã thử, lỗi/retry đúng grant. P2 cần panel có cả Q3-Normal và Q3-Anomaly để đo classification, budget riêng; không chỉ C. Contract cũ Q25+IVL3 cần N+2·n(C), full three-model panel cần 3N nếu được duyệt. Từ pilot lấy p50/p95 latency, load time và failures; T≈ΣN_m·latency_m + load/overhead | Model license/revision/input/capture contract; GPU loại, VRAM, quota/giờ và giá thực từ người cấp. Moondream2 qualification/calls riêng nếu O3 yêu cầu. Báo cả chi phí nghiên cứu tuyển chọn và chi phí mỗi batch sau chọn; HNLO-only không chịu phí auxiliary ở bảng vận hành. |
| Memory/storage | Pilot đo peak allocated/reserved VRAM/RAM, resolution/token lengths; storage≈Σcalls·raw_bytes + immutable manifests/logs/checksums + backups theo quyền | Không lưu cả full-vocab logits nếu contract chỉ cần raw evidence nhỏ hợp lệ; lựa chọn capture phải duyệt, không bỏ bằng chứng cần audit vì tiết kiệm. |
| Annotation | H≈N·(2·t_label + disagreement_rate·t_adjudicate) + N_evidence·t_region + QA; thời gian/phút đo pilot thật | Hai annotators/adjudicator, mức chuyên môn, compensation/availability, rights và consent phù hợp. |
| User study | H≈readers·cases_per_reader·t_task + training/rest + adjudication; crossed precision simulation | Examiner recruitment, format đánh giá usefulness, consent và quy định đơn vị nếu áp dụng. Không tự gửi lời mời trong task này. |
| Software | Reuse records/validation/metrics/sensitivity; cần adapter/raw writer, scorer qualification, triage, bootstrap, viewer tối thiểu | Chỉ tạo module khi task được giao; không nhập legacy toàn bộ hoặc đổi source lock cũ. |
| Lịch | Critical path: quyền/nguồn → annotation/pilot → development → freeze → target → tổng hợp. Effort code ước lượng sau contract T0, data/inference bằng công thức pilot; ngày bảo vệ do Owner cung cấp | Thời lượng **cần xác nhận**, không hứa tuần/tháng giả. Nếu available_hours nhỏ hơn estimate+buffer do Owner chọn, giảm scope bằng quyết định trước run. |

Permission matrix phải có người cấp, thời điểm, phạm vi, source SHA/release, model revision, dataset/hash/member, run/attempt, hạn mức và expiry/stop condition. Phê duyệt khoa học, quyền truy cập, quyền chạy, quyền chia sẻ và quyền merge là năm trục riêng. T0 approval không tự mở target/GPU; T2 pilot không tự cho large run; T4 freeze không tự cho target release. Không gửi dữ liệu lên dịch vụ ngoài hoặc public viewer khi chưa có quyền.

Blocker đang mở: học vụ O1; thesis metric/protocol O2; roster/feature exception O3; data/source/GT/custodian O4; precision và ngân sách O5; hardware/run rights O6; reviewer/evidence rights O7; xử lý #136 O8. Không có blocker ngăn bàn giao **bản đề xuất tài liệu**; tất cả đều chặn bước thực thi liên quan.

### 10.1. Ba ứng viên Owner đã chọn và giới hạn thẩm quyền

**Cập nhật 27/10/2026, cùng Draft PR #137:** Owner chọn đúng ba ID dưới đây để khảo sát vì có trọng số công khai, hỗ trợ ảnh, khác họ Qwen và có triển vọng phù hợp quota T4. Đây là rationale tuyển ứng viên, không là kết quả feasibility hay bằng chứng bổ sung thông tin. Không mở rộng danh sách tự động.

| Trạng thái | Giá trị hiện tại / gate còn thiếu |
| --- | --- |
| OWNER_SELECTED_CANDIDATES | **ĐÃ CHỐT**: `google/gemma-3-4b-it`; `microsoft/Phi-3.5-vision-instruct`; `HuggingFaceTB/SmolVLM2-2.2B-Instruct`. Không xin lại lựa chọn này ở T0. |
| KAGGLE_COMPATIBILITY | **UNVERIFIED / NOT_RUN** cho cả ba; chưa load hoặc end-to-end PASS. T1 xác nhận quyền, T2/P1 đo thật. |
| SCIENTIFIC_UTILITY | **UNPROVEN / NOT_RUN**; P2 classification khác P3 incremental false-safe capture. |
| ROSTER/FEATURE CHANGE | **PENDING O3/T0**; roster bốn model lịch sử nguyên vẹn, Q3 predictor cố định; D_j chỉ là đề xuất. |
| RUN AUTHORIZATION | **NOT_GRANTED** bởi task này; không download weights/GPU/inference/annotation/target hoặc dùng grant cũ. |

**Đối chiếu InspecSafe:** cả ba là **mô hình bổ sung, không thuộc danh sách Figure 6**, chưa có kết quả InspecSafe tương ứng do tác giả công bố trong phép so sánh gốc đó. Đã xem trực tiếp Figure 6, trang 10 của [PDF tác giả arXiv v1](https://arxiv.org/pdf/2601.21173v1#page=10), cùng Appendix S2; đối chiếu [bản xuất bản, Benchmark Evaluation](https://www.nature.com/articles/s41597-026-07796-x). Figure gồm Doubao, Grok, Claude, Gemini, GPT, Yi, ba biến thể GLM và sáu biến thể Qwen3; không Gemma/Phi/SmolVLM2. Ảnh Figure trên máy chủ nhà xuất bản bị cookie challenge nên kiểm hình qua PDF tác giả, không nhận đã truy cập hình đó thành công. Không đọc TEST hoặc dùng accuracy của Figure làm điểm tuyển chọn; không suy rộng thành “chưa từng ai thử ba model này”.

### 10.2. Hồ sơ tương thích Kaggle — tài liệu khác thực thi

Snapshot metadata chính thức ngày 27/10; SHA là revision **có thể pin**, chưa phải revision run được phê duyệt. Cần pin đồng thời model/config/tokenizer/processor và remote code nếu có. API metadata không chứng minh quyền tải weights. Định dạng lưu weights, dtype khi load và dtype compute là ba trường riêng.

| Model ID / revision / nguồn chính thức | Kiến trúc, ảnh và quyền truy cập | Precision / bộ nhớ và bằng chứng còn thiếu |
| --- | --- | --- |
| [google/gemma-3-4b-it](https://huggingface.co/google/gemma-3-4b-it), [`093f9f388b31de276ce2de164bdc2081324b9767`](https://huggingface.co/google/gemma-3-4b-it/tree/093f9f388b31de276ce2de164bdc2081324b9767); [API metadata](https://huggingface.co/api/models/google/gemma-3-4b-it) | Gemma3 decoder + SigLIP vision; ảnh+text → text. Gemma license/terms, gated; API `gated=manual`. Public card đọc được nhưng config/processor tại SHA trả HTTP 401 khi không xác thực: **ACCESS BLOCKED**, chưa xác nhận tài khoản Owner được cấp. | API safetensors: 4.300.079.472 BF16 parameters. [Technical Report Table 3](https://storage.googleapis.com/deepmind-media/gemma/Gemma3Report.pdf#page=3) nêu 4B raw BF16 weights 8,0 GB; +KV 12,7 GB ở context 32.768 theo giả định của bảng, **không là peak multimodal FP16/T4**. Vision/crops/activations/cache/runtime/loading overhead phải đo; FP16 conversion ổn định và peak <16 GB **UNVERIFIED**. |
| [microsoft/Phi-3.5-vision-instruct](https://huggingface.co/microsoft/Phi-3.5-vision-instruct), [`12b77fb40b63a2c73c68243d3f767aab688a1b2a`](https://huggingface.co/microsoft/Phi-3.5-vision-instruct/tree/12b77fb40b63a2c73c68243d3f767aab688a1b2a); [API metadata](https://huggingface.co/api/models/microsoft/Phi-3.5-vision-instruct) | `Phi3VForCausalLM` + CLIP ViT-L/14-336 + HD image embedding, [config tại SHA](https://huggingface.co/microsoft/Phi-3.5-vision-instruct/blob/12b77fb40b63a2c73c68243d3f767aab688a1b2a/config.json); ảnh/text → text, hỗ trợ multi-image. MIT; API ungated, không cần xin gate weights nhưng vẫn cần license/run grant. | API safetensors 4.146.621.440 BF16 parameters; config BF16. Tính 2 bytes/parameter ≈8,29 GB chỉ là **ước lượng weights**, không số VRAM nhà phát triển hay runtime. Card đã kiểm không nêu mức peak FP16/T4 cho input SafeShift; **UNVERIFIED**. |
| [HuggingFaceTB/SmolVLM2-2.2B-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct), [`482adb537c021c86670beed01cd58990d01e72e4`](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct/tree/482adb537c021c86670beed01cd58990d01e72e4); [API metadata](https://huggingface.co/api/models/HuggingFaceTB/SmolVLM2-2.2B-Instruct) | Idefics3-derived, shape-optimized SigLIP + SmolLM2; image/multi-image/video/text → text; scope pilot chỉ ảnh. Apache-2.0, API ungated. | API safetensors **2.246.784.880 F32 parameters**, [config](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct/blob/482adb537c021c86670beed01cd58990d01e72e4/config.json) top-level float32, text_config BF16; không ghi nhầm weights là FP16/BF16 vì snippet BF16. Card nêu **5,2 GB GPU RAM cho video inference**, không cam kết cùng revision/env/input FP16/T4. FP16 image path và peak VRAM **UNVERIFIED**. |

| Model | Thư viện / attention / custom code | Xử lý ảnh và dtype cần khóa trước P1 |
| --- | --- | --- |
| Gemma 3 | Card ghi Transformers hỗ trợ từ **4.50.0**; native `Gemma3ForConditionalGeneration` + `AutoProcessor`, không cần `trust_remote_code=True` theo API này. [Docs v4.50.0](https://huggingface.co/docs/transformers/v4.50.0/en/model_doc/gemma3) là mốc tham khảo, chưa môi trường Kaggle đã test. Card dùng PyTorch, Pillow; Accelerate cho `device_map`; không pin bản torch/CUDA đầy đủ → T1/T2 phải khóa và qualification. FA2 không được card yêu cầu bắt buộc. | Card dùng ảnh 896×896, chat template và `generate`; report có adaptive crops. Processor flags/pan-and-scan theo **config pin sau khi có access**, không tự resize/cắt ảnh để cứu OOM. Snippet BF16; không thấy xác nhận đủ cho FP16 T4 tại revision này trong nguồn đã kiểm → **UNVERIFIED**, không suy dtype tương đương. |
| Phi-3.5 Vision | Card đưa stack tham khảo `torch==2.3.0`, `torchvision==0.18.0`, `transformers==4.43.0`, `accelerate==0.30.0`, `numpy==1.24.4`, `Pillow==10.3.0`, `Requests==2.31.0`, `flash_attn==2.5.8`. Model và processor dùng **trust_remote_code=True**: phải review/pin code trước grant. Card cho `_attn_implementation='eager'` khi không có flash-attn; [mã tại SHA](https://huggingface.co/microsoft/Phi-3.5-vision-instruct/blob/12b77fb40b63a2c73c68243d3f767aab688a1b2a/modeling_phi3_v.py) có optional import và eager/SDPA/FA2 dispatch. Không mặc định bản Transformers mới tương thích custom API. | Placeholder `<\|image_1\|>`, tokenizer chat template, processor ảnh rồi `generate`, decode phần generated. [Preprocessor pin](https://huggingface.co/microsoft/Phi-3.5-vision-instruct/blob/12b77fb40b63a2c73c68243d3f767aab688a1b2a/preprocessor_config.json) RGB/normalize, default num_crops=4; card khuyên 16 cho single-frame. T0/T2 chọn đúng chế độ single-image trước pilot, không đổi crops giữa arms/retry. `torch_dtype='auto'` sẽ theo BF16 config, **không là FP16**; eager có bằng chứng hỗ trợ, nhưng FP16 toàn vision+decoder và T4 runtime vẫn **UNVERIFIED**. |
| SmolVLM2 | Native `AutoModelForImageTextToText`/`SmolVLMForConditionalGeneration`, `AutoProcessor`, không cần remote code theo API. Card nói latest Transformers + num2words + flash-attn; video thêm decord (không cần cho scope ảnh). [Docs v4.50.0](https://huggingface.co/docs/transformers/v4.50.0/en/model_doc/smolvlm) có SmolVLM2 và SDPA; không lấy config serialization `4.47.1` làm minimum supported version hoặc dùng “latest” như lock. Exact torch/torchvision/Transformers/CUDA và dependency versions **chưa qualified**. | [Preprocessor pin](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct/blob/482adb537c021c86670beed01cd58990d01e72e4/preprocessor_config.json): RGB, splitting/resize/pad/normalize, longest_edge=1536, tiles max edge=384; processor image_seq_len=81. Card dùng BF16 + FA2 cho model và pixel inputs, chat template + `generate`. SDPA có trong implementation/docs không chứng minh FP16/T4 PASS. Phải kiểm chính image pipeline; không bỏ splitting, đổi resolution hoặc dùng config Transformers.js FP16 làm bằng chứng PyTorch FP16. |

**Kaggle mục tiêu:** 2 × NVIDIA T4, **16 GB mỗi GPU**; đây là cấu hình yêu cầu khảo sát, không reservation đã cấp. [NVIDIA T4](https://www.nvidia.com/en-us/data-center/tesla-t4/) có 16 GB GDDR6 và hỗ trợ FP16; không dựa vào BF16 native. [FlashAttention chính thức](https://github.com/Dao-AILab/flash-attention#nvidia-cuda-support) không hỗ trợ T4 bằng đường FA2 CUDA thông thường; backend Turing riêng không phải drop-in đã qualified cho ba model. Không cài extension khác để ngầm cứu cấu hình. P1 ưu tiên một model/1 GPU, FP16 nếu được phê duyệt như cấu hình qualification; Phi eager có tài liệu hỗ trợ, Gemma/Smol cần xác nhận backend non-FA2 cụ thể. PyTorch SDPA không đồng nghĩa flash-attn package. GPU thứ hai **không cộng thành vùng VRAM 32 GB**; chia model cần device map/sharding, placement vision+decoder, transfer/device errors, peak trên từng GPU và latency được review/pin/kiểm riêng; `device_map='auto'` không đủ làm PASS.

Không có nguồn đã kiểm nào xác nhận trọn chuỗi **pinned revision + FP16 + ảnh SafeShift + parser + T4** cho cả ba. FP16 được phần cứng hỗ trợ không bảo đảm weights/activations không overflow hoặc đầu ra tương đương BF16. Thiếu hỗ trợ chính thức: ghi UNVERIFIED và chỉ thử như qualification có grant cụ thể, không báo manufacturer-supported/PASS; nếu chính sách O3 đòi hỗ trợ chính thức thì BLOCKED đến khi có. Không tự đổi sang BF16/FP32, 4-bit/8-bit, checkpoint khác, crop nhỏ hơn hoặc GPU thuê. Mọi thay đổi cần amendment/grant mới, record mới, không pooling với attempt cũ. Không tải weights hoặc thực thi remote code trong task tài liệu này.

### 10.3. Quy trình P1–P4 và tuyển chọn có giới hạn

T0 duyệt rule/contract; T1 xác minh access/quota và code/license; **T2** qualification/P2/pilot cost, đồng thời khóa ngưỡng bằng pilot; **T3** chỉ nhận ứng viên đã qua gate kỹ thuật/hành vi/ngân sách để thực hiện P3 và chọn auxiliary. Không bắt P3 PASS trước khi có code/baseline để đo P3. P4 đo từ P1 nhưng chỉ kết luận benefit/cost khi có P3. P2 là gate khả năng đánh giá/hành vi, không đặt accuracy tối thiểu tùy ý. Final selection chỉ sau cả P1–P4 và O3; T4 khóa trước target.

| Gate / mục đích | Đầu vào, phép kiểm và đối chứng | Đầu ra / PASS / FAIL và rủi ro |
| --- | --- | --- |
| **P1 — chạy được trên Kaggle** | Grant model/revision/env/input/attempt; code synthetic reviewed; manifest ảnh development có quyền, đại diện sizes/aspect ratios và độ dài prompt/output đã khóa. Load pin model+processor; chạy ảnh qua native pipeline, frozen semantic prompt và canonical Level01–Level04 parser, decoder/max tokens/seed/dtype/attention/device map; cache riêng model. | Tách **LOAD_PASS** khỏi **END_TO_END_PASS**. Receipt phải có sample/run/config/source SHA, env/driver/GPU, input/model/config/output checksums, raw-before-parse, nhãn hoặc INVALID, mọi error. PASS e2e khi pipeline/parse đúng contract và không OOM trên toàn qualification envelope đã khóa; invalid allowance theo O5, không bắt mọi predicted label đều xuất hiện. OOM/NaN/device/library errors ghi bước và nguyên nhân đã xác minh; chưa rõ ghi UNKNOWN, dừng attempt. Không đổi prompt/parser/dtype/crops/revision giữa chừng. |
| **P2 — hành vi phân loại/bất đồng** | P1 e2e PASS, panel development có GT độc lập và cả Normal/Anomaly, Q3 outputs đúng ID; cùng prompt semantics/label mapping, native templates được ghi là khác biệt bắt buộc. Confusion 4×4 + binary; phân bố labels; Macro-F1/BA/recall/FNR theo §8/O2; technical/INVALID rate. Đếm disagreement exact paired IDs, cả bốn mức và binary; histogram/variance D_j trong C, shared errors theo source/domain. | Report planned/output/valid/GT support/exclusions và digests. Anomaly-on-Normal = FP/(FP+TN) trên GT-Normal với nhãn j hợp lệ; kèm số GT-Normal missing/INVALID riêng, không bỏ khỏi ledger. FNR=FN/(TP+FN), positive hazard=Level01–03; thiếu mẫu số → null+reason. Classification tốt chưa là utility PASS; thấp không tự loại nếu P3 có tiềm năng. Gần như mọi Normal thành Anomaly cần đánh dấu giống pathology Q25/IVL3 và xem D_j có thực sự biến thiên trong C; binary disagreement hằng chưa chứng minh ordinal D_j hằng. Ngưỡng near-constant/coverage/stability khóa trước screening chính, không tùy kết quả chọn model. |
| **P3 — tăng thêm so HNLO** | T2/P1–P2 đủ dữ liệu và caps P4; authorized D, grouped OOF CV với cùng folds/grid/labels/fit budget §6.3. HNLO-only raw+learned, D_j-only raw+learned, logistic(s3,D_j), baseline mạnh nhất chọn development. Cùng E/M/K, error e_FS, b và source weights. Đo capture_FS, Δ/CI so HNLO-only **và** baseline mạnh nhất; AP/coverage/worst-domain là phụ §8. | Paired ledger ca false-safe được full chọn mà HNLO không chọn **và ca bị mất**, net capture tại cùng budget; không chỉ đếm gain. P3 development PASS chỉ theo mức tăng tối thiểu/precision/support đã khóa O5; không là H1 xác nhận. D_j hằng, không tăng, uncertainty quá lớn → FAIL/inconclusive đúng lý do; không thêm model vào core để đủ ba. Không dùng target hoặc TRAIN phơi nhiễm làm xác nhận. |
| **P4 — chi phí/khả thi** | Đo từ P1–P3 cùng input envelope: peak allocated/reserved VRAM **từng GPU**, RAM, load/cold-start, warm p50/p95 giây/ảnh, synchronization/timing policy, số attempts, invalid/technical/OOM rates, bytes raw+metadata/cache, quota và overhead. So HNLO-only chạy thực với chi phí Q3+aux, không chỉ cached CPU fit. | Cost ledger cho từng ứng viên, tổng tuyển chọn và projected full workload theo §10; incremental benefit/cost, cost caps và uncertainty. PASS khi caps quota/storage/stability/latency đã duyệt và utility trade-off chấp nhận được, không từ “weights <16 GB”. Vượt cap dừng; không mặc định thuê GPU lớn/đổi precision hoặc bỏ raw evidence. Giá/quota chưa xác nhận → BLOCKED dự toán cuối. |

**Thử lần lượt, không chạy cả ba trên toàn dataset:** T1 lập thứ tự theo access và khả năng giải quyết stack, có thể ưu tiên SmolVLM2 vì số parameters nhỏ hơn nếu FP16/non-FA2 path được duyệt; sau đó Gemma khi gate access mở, Phi khi custom-code/eager stack đã review. Đây chỉ là thứ tự đề xuất, T0/T1 chốt trước xem score; model chưa đủ điều kiện ghi BLOCKED/NOT_RUN và chuyển sang ứng viên đã đủ quyền, không gọi model bị chặn là quality FAIL. Mỗi ứng viên: P1 nhỏ → P2 pilot có giới hạn + cost cap → P3 screening được cấp → chỉ finalist mới mở development lớn. Không có số ảnh/thời gian quota mặc định; T2 ước lượng bằng event/support/precision và input envelope, Owner khóa số/stop rules trước lượt screening chính; pilot đã xem luôn thuộc development, không gọi độc lập.

P1 fail dừng model/config đó; P2 thiếu GT/events hoặc D_j hằng dừng P3 hoặc ghi inconclusive; cost cap P4 áp dụng ngay không đợi đủ bốn gate. Có thể dừng tuyển khi đã có một ứng viên đạt **tiêu chí adequacy định trước** hoặc hết quota; những model chưa chạy giữ NOT_RUN, không tuyên bố model được chọn tốt nhất trong ba. Nếu mục tiêu là xếp hạng cả ba thì phải đủ paired screening và budget đã duyệt; không optional stopping theo p-value. Không tăng số candidates hoặc thử vô hạn configurations; số lần retry/amendment nằm trong grant, mọi attempt âm được giữ.

Đối chứng từng j dùng cùng E_j/M_j/K và Q3 output; so giữa finalist dùng **intersection ID đủ điều kiện đã khóa** và cùng source/folds, cộng bảng toàn planned với failures/coverage/cost riêng. Nếu intersection/support quá nhỏ hoặc missingness lệch nguồn, không xếp winner bằng complete cases dễ hơn; NO-GO selection hoặc thu hẹp claim sau quyết định. Final target chỉ dùng chosen contract, không bắt đủ output của cả ba ứng viên, không gộp D_j khác nhau. Baseline H1 và j được khóa từ development; V vẫn development/validation, không trở thành target độc lập sau tuyển chọn.

**Nếu không có ứng viên vượt toàn bộ gate:** bàn giao compatibility matrix, nguyên nhân FAILED/BLOCKED/INCONCLUSIVE/NOT_RUN, paired negative results và cost; HNLO-only là fallback so sánh, không tự gọi B cải thiện. Q25/IVL3 chỉ tiếp tục như auxiliary nếu O3 riêng cho phép và có bằng chứng/gate tương ứng; không tự phục hồi vì ba model mới thất bại. Đổi trung tâm sang A hoặc giảm scope cần O1/T0 amendment. Không mở rộng danh sách VLM vô hạn; roster lịch sử vẫn nguyên vẹn. E1–E5 giữ nguyên, E5 thêm tất cả attempts của model selection.

## 11. Master Execution Plan duy nhất

Tất cả task sau là **PLANNED, NOT_AUTHORIZED_BY_THIS_DOCUMENT**. Mỗi task là một sản phẩm hoàn chỉnh gồm code/test/docs khi có code, cập nhật PROJECT_STATE trong cùng PR. DONE sản phẩm, PASS khoa học, PASS audit/merge và benefit PASS phải ghi riêng. Không tự merge; recheck GitHub/AGENTS trước mỗi task. Tên file **dự kiến** chưa tồn tại được ghi code span, không link giả. Tệp derived/raw/manifests nhạy cảm ở `data/processed/` hoặc storage được cấp, không Git.

### T0 — Ghi quyết định chuyển tiếp và khóa hợp đồng Khóa luận

- **Loại / mục tiêu:** quyết định khoa học + tài liệu; một gói đủ để giao T1–T3 mà không lập lại kế hoạch hướng.
- **Điều kiện bắt đầu:** kế hoạch này đã được Owner phê duyệt hoặc có phản hồi quyết định cụ thể; ChatGPT kiểm PR/HEAD trực tiếp. Chỉ ghi approval có bằng chứng; thiếu mục ghi PENDING.
- **Phạm vi:** dùng O1–O8 ở §14 để chốt B hay A, mức CT1/CT3, phạm vi hai feature/roster, giữ TEST đóng; append quyết định chuyển tiếp M1–M8 và phương án #136; soạn `THESIS_PROTOCOL.md`/config từ §6–9 và §10.1–10.3 với tham số pilot-dependent ghi UNRESOLVED và gate không cho target. Ghi Owner đã chọn ba candidates, nhưng D_j/auxiliary cuối/roster change vẫn cần O3; duyệt rule tuyển tối đa một, thứ tự/early-stop, FP16 qualification và eligibility xuyên ứng viên. Không sửa hai file M2. Chốt trước pilot cách quyết định b/δ/precision/stop và P1–P4 caps, không cần biết các giá trị chưa đo; không cấp GPU từ selection decision.
- **File dự kiến:** `docs/research/DECISIONS.md` append-only, `docs/research/THESIS_PROTOCOL.md`, `docs/research/thesis_config.v1.json`, PROJECT_STATE; cập nhật điều hướng README/ROADMAP/EXECUTION_PLAN trong cùng task khi Owner duyệt chuyển tiếp, không xóa lịch sử.
- **Bàn giao:** decision matrix có approval refs/authority, protocol pilot-ready, unresolved numerical register có người quyết định ở T2, task scope nguồn/runner chính xác.
- **Kiểm/bằng chứng:** hash M2 bất biến; trace mỗi amendment tới decision; không TBD vô chủ, không cờ APPROVED tự sinh; kiểm link/diff/permission/schema docs.
- **DONE/PASS/FAIL:** DONE khi gói quyết định/protocol phản ánh đúng quyết định thật; gate PASS khi scope học vụ/khoa học cần thiết đủ duyệt; thiếu → BLOCKED phần tương ứng, không xin lại M1/M2 cũ. Merge không thay quyền T1/T2.
- **Quyền thiếu / task kế:** Owner/giảng viên xác nhận O1–O3/O8; giao **T1**. Có thể chuẩn bị văn bản liên hệ dữ liệu trong T1 sau scope; không tự liên hệ bên ngoài.

### T1 — Đủ quyền dữ liệu, nguồn và nguồn lực cho pilot

- **Loại / mục tiêu:** phụ thuộc bên ngoài + protocol acquisition; xác định GO/NO-GO trước xây backend/chạy GPU.
- **Điều kiện bắt đầu:** T0 scope PASS; có đầu mối thật do Owner xác nhận; chưa đọc target/data chưa cấp.
- **Phạm vi:** xác minh license/use/export, nguồn/site/video/session, tương thích nhãn, curator/annotators/reviewers, GPU/quota; thiết kế source registry và D/V/T/U split policy; chốt blind annotation rubric, unknown policy và pilot sampling/precision simulation plan. Đối chiếu §10.2: Gemma account/gate, Phi pinned custom code và eager deps, Smol FP16/non-FA2 support; pin env riêng từng model, kiểm Kaggle 2×T4/16 GB mỗi GPU thực cấp, disk/RAM/time, không cộng VRAM. Ghi UNVERIFIED/BLOCKED và grant qualification có giới hạn; không download/annotate khi chưa có grant.
- **File dự kiến:** `docs/research/THESIS_DATA_PROTOCOL.md`, bổ sung protocol/config/decision nếu được duyệt, PROJECT_STATE. Chứng từ cá nhân/hợp đồng ngoài Git; chỉ refs có quyền.
- **Bàn giao:** access/resource matrix, source acquisition plan có bằng chứng, hồ sơ compatibility/revision/dependency/remote-code review và thứ tự candidates, pilot grant đúng data/model/source/run/attempt/dtype/attention/caps, annotation assignment và target custody; NO-GO report nếu thiếu. Library API hỗ trợ không thay receipt chạy P1.
- **Kiểm/bằng chứng:** nguồn không chỉ heuristic, quyền raw/output/ảnh minh họa tách nhau, reviewer đủ chuyên môn, pilot không target, cost ceiling có người chấp nhận.
- **DONE/PASS/FAIL:** hồ sơ DONE kể cả NO-GO; GO chỉ khi dữ liệu/nhãn/nguồn và tài nguyên pilot được cấp. Không có nguồn độc lập → chặn xác nhận, xin mức claim giảm, không dùng TRAIN thành target.
- **Quyền thiếu / task kế:** owner nguồn, annotators, GPU provider/custodian O4/O6/O7; **T2** khi GO. Nhánh R hỗ trợ có thể chuẩn bị ở scope riêng nếu O8 duyệt, không chặn giấy tờ T1.

### T2 — Bàn giao dữ liệu/pilot có provenance và khóa numerical gates

- **Loại / mục tiêu:** phần mềm tối thiểu + dữ liệu/thực nghiệm được cấp; đo tính khả thi thật trước fit chính.
- **Điều kiện bắt đầu:** T1 GO, grant chi tiết; source/runner phải review và pin trước **bất kỳ GPU call**. Tách checkpoint “code synthetic accepted” với “authorized pilot run” ngay trong task, không giả code draft là run authority.
- **Phạm vi:** thêm reader/source validation, adapter cụ thể/raw writer/parser/scorer cần pilot và tests; qualification synthetic rồi GPU nhỏ trong grant; thu nhận D/V/T/U qua custodian và annotation mù; pilot **D-only**, source/duplicate/exposure checks, count false-safe đúng cohort. Thử tuần tự candidates theo §10.3: P1 load/e2e tách biệt, P2 classification/disagreement/variance trong C, P4 đo chi phí ban đầu. Cluster precision simulation; hoàn tất b/δ/α_FPR/γ/h/threshold/search/seeds/support/stop/CI/user-study criteria và ngưỡng P1–P4 theo O5 trước screening chính. Không fit/chọn j theo target; P3 ở T3 sau baseline sẵn. Target vẫn kín với analyst.
- **File dự kiến:** `safeshift/data/` modules source/manifest; `safeshift/models/` adapter/raw persistence cần dùng; `scripts/qualify_thesis.py`, `tests/test_thesis_capture.py`, `docs/research/THESIS_PILOT.md`, data protocol/thesis protocol/config/decision, PROJECT_STATE. Không tạo generic training framework.
- **Bàn giao:** code+tests+usage, qualification receipt từng candidate/attempt kể cả âm, bảng LOAD/E2E/P2/P4 tách trạng thái, source/annotation registry và role hashes ngoài Git, pilot event/cost report, numerical gate table và shortlist đủ điều kiện vào P3 đã duyệt hoặc NO-GO có lý do; chưa gọi auxiliary được chọn vào phương pháp.
- **Kiểm/bằng chứng:** raw lưu trước parse cả lỗi; alignment model-specific; no-overwrite/path/hash/partial write; ID không rò nhãn; D/V/T/U nguồn tách; adjudication agreement; minimum events/cluster precision đúng simulation; không đọc T scores/GT để chọn cỡ mẫu.
- **DONE/PASS/FAIL:** T2 GO khi predictor qualified, dữ liệu/events/sources/budget đủ và ít nhất một ứng viên P1 e2e PASS, P2 evaluable/không bị stop rule, P4 caps khả thi để vào P3. D hằng hoặc ít events báo thật, không tự thêm feature/model. Nếu tất cả fail/blocked, hồ sơ vẫn DONE nhưng B selection NO-GO; giữ negative feasibility, theo fallback §10.3/O1, không T3 fit hoặc T5 target theo tham số bịa.
- **Quyền thiếu / task kế:** grant qualification/pilot từng model/run, data/annotation rights, O3 Moondream2 disposition và O5 numerical approval; **T3** khi PASS.

### R — Tái sử dụng R1–R5 có giới hạn (nhánh hỗ trợ, không cửa ải Seminar)

- **Loại / mục tiêu:** phần mềm và hồi cứu, chỉ sau O8; giữ giá trị ledger/provenance/errors, không trì hoãn dữ liệu mới để bảo vệ học phần đã bỏ.
- **Điều kiện bắt đầu:** Owner chọn hoàn tất #136 trong đúng session/PR cũ hoặc chọn dừng; **session lập kế hoạch này không thực hiện R**. Nếu tiếp tục: sửa/audit/merge #136 theo quy trình riêng rồi cấp artifact grant M4 mới.
- **Phạm vi:** ưu tiên đóng lỗi metadata đã audit và tests đúng ID hashes; sau merge/grant tái dùng R1 coverage, R2 classification/ranking, R3 missing/severe, R4 disagreement/degeneracy; R5 viết narrative giới hạn cho chương nền Khóa luận. Không thêm AP/CI/thesis fit vào M2 v1, không chạy recovery pooling.
- **File dự kiến:** đúng file #136 trong session cũ; sau khi được phép reanalysis, `docs/research/THESIS_HISTORICAL_EVIDENCE.md` và PROJECT_STATE; artifacts ignored. Không copy code draft lỗi sang nhánh mới để tránh audit.
- **Bàn giao:** một gói historical evidence có receipt/M2 trace hoặc quyết định không tái phân tích và chỉ cite số đã verify.
- **Kiểm/bằng chứng:** independent oracle exact eligible IDs/count/hash từng R3/R4 CSV; protocol/config hashes bất biến, synthetic khác real, scope artifact chính xác.
- **DONE/PASS/FAIL:** metadata còn sai → FAIL, không cite output #136 làm kết quả. Historical reanalysis chưa chạy → NOT_RUN, không M4 COMPLETE. Dừng nhánh cần quyết định Owner, không tự đóng PR hoặc đổi M3/M4/M5 lịch sử.
- **Quyền thiếu / task kế:** O8 và artifact grant, review/merge #136 riêng; tích hợp bằng chứng vào T3/T6. Không bắt buộc R hoàn tất trước T1/T2; T3 không phụ thuộc output R chưa verified.

### T3 — Tuyển auxiliary và hoàn thiện baseline, triage, viewer trên development

- **Loại / mục tiêu:** phần mềm + phát triển thực nghiệm; một gói có thể freeze, gồm tất cả đối chứng/ablation/tests/docs cần dùng.
- **Điều kiện bắt đầu:** T2 GO với shortlist đủ P1/P2 và caps P4, quyền D/V/U; predictor/raw contract, D_j candidate contract, numerical selection rule và metric version đã duyệt; không T labels. Nếu R chưa xong, dùng adapter đã review T2 và facts kế thừa, không dùng #136 draft.
- **Phạm vi:** implement §6–9; dựng đối chứng HNLO/D_j/full và P3 screening trên D theo §10.3, hoàn tất P4 benefit/cost; chọn tối đa một auxiliary bằng rule đã khóa và ghi quyết định O3 dựa evidence, rồi mới mở full development của phương pháp. X1–X4 development, baseline selection/CV/search budget, validation threshold/calibration, all failure/overload/tie rules; viewer local read-only với annotation/review log riêng; pilot usability trên U-development để sửa UI trước user study chính; giữ scope hai feature, không thêm algorithm/model vì kết quả xấu. Không có winner → negative report + fallback đã duyệt, không ép full B.
- **File dự kiến:** `safeshift/evaluation/triage.py`, `safeshift/evaluation/thesis_metrics.py`, `scripts/fit_triage.py`, `scripts/evaluate_thesis.py`, `scripts/review_cases.py`, `tests/test_triage.py`, `tests/test_thesis_metrics.py`, viewer tests nhỏ, `docs/THESIS_USAGE.md`, `docs/research/THESIS_DEVELOPMENT.md`, protocol/config/state. Tên chỉ thêm khi có chức năng; không sửa model predictor để tăng điểm.
- **Bàn giao:** runnable code/CLI/viewer, baselines+ablation, fixtures/oracles, P1–P4 selection ledger với paired cohort/coverage/all-attempt cost và O3 final disposition, development report, candidate freeze manifest, bounded cases/rubric study-ready. Report không gọi model chưa thử là thua hoặc low accuracy là không hữu ích.
- **Kiểm/bằng chứng:** independent formulas cho capture/AP/F1/CI mechanics; exact IDs/denominators, no-input omission; fold-only normalization; no-target-read guard; random/ties/empty/no-events/overload; UI evidence missing/stale hash/rollback, user actions không sửa raw. Re-run suite phù hợp sau sửa code.
- **DONE/PASS/FAIL:** implementation PASS kể cả B thua; mọi arm/candidate có output/null lý do và chi phí; final auxiliary chỉ selected khi P1–P4 đạt rule và O3 ghi quyết định. Nếu đã đổi method sau V phải ghi và khóa lại trước T, không gọi V độc lập. Thiếu strong baseline/source contract hoặc chưa có model đủ gate → FAIL freeze full B; fallback chỉ freeze sau scope được duyệt.
- **Quyền thiếu / task kế:** development runs/annotation/UI case rights; **T4** sau code/docs review và candidate freeze.

### T4 — Khóa xác nhận trước target

- **Loại / mục tiêu:** quyết định khoa học + audit; chặn tối ưu sau thấy target.
- **Điều kiện bắt đầu:** T3 tests/development hoàn chỉnh; source merge đã kiểm, T2 data gates còn hiệu lực; target custodian chứng nhận chưa lộ.
- **Phạm vi:** pin code, predictor/aux được O3 chọn cùng revisions, processor/tokenizer/custom code, dtype/attention/device map/env, prompts/parser, exact D contract, feature normalization/coefficients, baseline chính, b/K/ties/batch policy, thresholds, seeds/grid, metric/digest/CI/multiplicity/stop, target manifest và user-study assignments; gắn P1–P4 receipts, rejected/NOT_RUN candidates và toàn selection cost; review chi phí/N/A/claims; quyết định riêng quyền một lượt T/U-study. Không xem target outcome để chọn arm/model; target không cần chạy cả ba candidates.
- **File dự kiến:** `docs/research/THESIS_FREEZE.md`, config/protocol phiên bản được duyệt, decision append-only, PROJECT_STATE; weights/output lớn ngoài Git có hash.
- **Bàn giao:** signed/attributed freeze record theo SHA và permission matrix; checklist no unresolved numerical fields ở target path, hoặc NO-GO.
- **Kiểm/bằng chứng:** chống tự tham chiếu hashes, code tests/CI đúng source, data roles và source certificate, bất biến predictor giữa B arms, M2 không đổi, từng N/A có giới hạn được chấp nhận.
- **DONE/PASS/FAIL:** PASS freeze khác grant target; chỉ khi cả hai đủ mới T5. Tham số chính TBD/target đã lộ/nguồn chưa xác minh → NO-GO; không hạ chuẩn hoặc âm thầm chuyển exploratory thành confirmatory.
- **Quyền thiếu / task kế:** O5 numerical approval và O6 target run grant, O7 study consent/authority; **T5** khi PASS + grant.

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
- **Phạm vi:** chương 1 bài toán/RQ; 2 related work; 3 dữ liệu/protocol/baseline; 4 triage/implementation; 5 kết quả/ablation/stress/errors; 6 case-review/usefulness/tái lập; 7 kết luận/limits. Gộp chương nếu trường yêu cầu. Slide/appendix/traceability, render QA, hướng dẫn môi trường/commands và artifacts có quyền.
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

**Khuyến nghị O8 cụ thể:** giữ PR #136 OPEN/DRAFT trong lúc duyệt kế hoạch; nếu chọn B, ưu tiên hoàn tất audit correctness đã có trong **chính PR/session đó**, không mở rộng tính năng thesis vào #136. Sau khi review/merge thật và có grant artifact, R1–R4 tạo gói hồi cứu ngắn, R5 làm phụ lục thesis. Lý do: ledger/provenance và error eligibility là hạ tầng có giá trị; lỗi metadata hiện tại khiến reuse một phần chưa sửa vẫn rủi ro. Không buộc chạy toàn bộ Seminar hoặc bảo vệ M5 trước T1.

Nếu Owner chọn dừng #136 để giảm thời gian, ghi quyết định dừng phát triển/tái sử dụng có phạm vi; không coi PR FAIL là đã sửa, không cherry-pick/exporter lỗi vào T3. T2/T3 phải có reader/evaluator tương ứng được review mới, chi phí viết/test lại được đưa vào budget; số lịch sử chỉ cite receipt đã verified. Việc đóng PR, merge, bỏ branch hay thay authority không nằm trong task này và chưa được tự thực hiện.

## 13. Risk register, GO/NO-GO và fallback

| Rủi ro / phát hiện tại gate | Mức ảnh hưởng | GO cần gì / NO-GO và phương án dự phòng |
| --- | --- | --- |
| Học vụ đòi tăng predictor Macro-F1, B chỉ triage | Cao, T0 | Giảng viên chấp nhận endpoint review; nếu không, Owner chọn A bằng amendment trước code, không trình B giả CT1 classification. |
| Không có nguồn T độc lập hoặc exposure không rõ | Cao, T1/T2/T4 | Source certificate và role disjoint; thiếu → dừng xác nhận, báo retrospective/development-only và xin chuẩn scope giảm. |
| Ít false-safe/cluster, D suy biến | Cao, T2/T3 | Precision plan PASS và variance có; thiếu → không fit quá tham số/không hứa H1; báo feasibility/negative D, HNLO-only là kết quả hợp lệ, đổi trung tâm cần O1. |
| Nhãn không tương thích/annotator chưa độc lập | Cao, T2 | Expert rubric/adjudication và agreement đạt chuẩn; thiếu → không dùng VLM labels, không tự remap InspecSafe. |
| #136 report metadata lỗi | Cao, nhánh R | Audit fix thật hoặc không reuse; planned/eligible/hash oracle; không nâng synthetic thành research result. |
| Missingness có liên quan hazard/source | Cao, X0–X4 | Coverage/missing composition/bounds + operational panel; vượt trần → inconclusive/NO-GO, không complete-case claim toàn hệ thống. |
| HNLO token semantics không tương đương | Cao, T2 | Native qualification đúng revision/prefix; thiếu → score N/A, không áp công thức generic hoặc logits đã xử lý như raw. |
| GPU OOM/chi phí auxiliary cao | Cao, pilot/run | Pilot resource caps; OOM dừng và grant source/config mới, không pooling. Nếu vượt budget dùng baseline rẻ để báo trade-off, không giấu chi phí. |
| Gemma access 401; BF16/FA2 example không hợp T4; Phi custom API lệch env; Smol F32 weights/BF16 snippet bị hiểu sai | Cao, T1/P1 | Access+code review+exact env/dtype/backend approved rồi e2e qualification; load PASS chưa e2e PASS. Không tự quantize/đổi crops/thuê GPU, không coi 2×16 GB là 32 GB thống nhất; thiếu → BLOCKED/UNVERIFIED. |
| Auxiliary all-Anomaly, D gần hằng, accuracy cao nhưng không thêm false-safe capture | Cao, P2/P3 | P2 đo cả ordinal/binary D trong C; P3 paired gain/loss/net so HNLO và strong baseline. Negative/inconclusive giữ; không ép chọn đủ ba hoặc bỏ model chỉ theo accuracy. |
| Tuyển winner nhờ easy complete cases, tuning nhiều model hoặc bỏ chi phí screening | Cao, P3/P4/T4 | Common-ID finalist panel + operational coverage; bounded search/stop trước score, source CV, tất cả attempts/cost; hết quota ghi NOT_RUN, không claim best-of-three. Không ứng viên đạt → §10.3 fallback/O1, không model zoo. |
| Target leakage/post-hoc tuning | Cao, T4/T5 | Custody/freeze/access log; lộ → đánh dấu exploratory, target mới cần quyền/nguồn mới, không “reset” nhãn độc lập. |
| Viewer explanation tạo niềm tin sai | Cao, T3/X6 | Phân biệt verified/generated/unavailable, task study có unsafe-acceptance; không có evidence thì N/A, không vẽ vùng giả. |
| Không có chuyên gia/user-study sample | Cao cho CT3, T1 | Có reviewer/time/rights; thiếu → usability chỉ synthetic technical demo, CT3 usefulness chưa đạt, cần giảng viên chấp nhận giảm scope. |
| H1 không thắng/CI rộng | Kết quả hợp lệ, T5 | Báo negative/inconclusive; không đổi b/δ/baseline hay bỏ domain. Giao code/protocol/ablation/limitations và luận văn theo chuẩn đã duyệt. |
| Nhóm rare/one-class hoặc CI không xác định | Giới hạn, T2/T5 | Báo support/null, worst-domain coverage; không đổi metric thành số giả. Có thể chỉ mô tả, không tuyên bố robust mọi miền. |

Các gate cứng: **G0** scope/metric/roster approved trước triển khai; **G1** quyền/source/GT trước acquisition/annotation; **G2** qualification+pilot grant trước GPU; **G3** data/event/precision/cost đủ trước fit chính; **G4** freeze và target custody trước xác nhận; **G5** raw/provenance/eligibility đúng trước công bố bảng; **G6** study thật trước usefulness claim. Mỗi NO-GO ghi ai quyết, bằng chứng, phạm vi bị chặn và điều kiện mở lại. Không “hoàn thành” gate bằng merge Markdown.

Fallback có thứ tự: (1) nếu D không thêm ích lợi, giữ báo cáo so sánh và policy HNLO-only rẻ hơn, không claim full thắng; (2) nếu thiếu target/source/precision, chỉ phát triển/hồi cứu được phép, xin mức học vụ giảm; (3) nếu học vụ bắt buộc direct classification, trình A với protocol mới; (4) nếu thiếu evidence labels/reviewers, giảm C thành provenance viewer và ghi CT3 usefulness chưa hoàn thành. Không fallback sang TEST, synthetic research results, ground truth VLM hoặc bỏ Moondream2 không duyệt.

## 14. Quyết định Owner cần duyệt trước triển khai

Các quyết định triển khai dưới đây **PENDING**; hai chỉ thị đã có là không học Seminar và **OWNER_SELECTED_CANDIDATES** đúng ba ID ở §10.1, không cần xin lại. Phần chốt ứng viên của O3 không phải final auxiliary/feature/roster approval. T0 ghi văn bản bằng chứng cho phần Owner duyệt, không đợi mọi quyền ngoại sinh rồi mới lưu quyết định; các gate thiếu vẫn đóng.

| ID | Quyết định cụ thể cần duyệt | Lý do/hệ quả/bằng chứng cần | Thời điểm bắt buộc |
| --- | --- | --- | --- |
| O1 | B trung tâm + A diagnostic + C viewer; tên/RQ/đóng góp thực nghiệm và negative-result route; bỏ M5 prerequisite ở kế hoạch mới | Cần giảng viên xác nhận CT1 review quality và đủ chuẩn thesis; nếu đòi predictor gain thì chọn A, không gán đã đồng ý | T0 trước implementation |
| O2 | Thesis protocol/version mới: hai features, Normal-only candidate E, mandatory M, b trên planned, ties/overload, AP/Macro-F1/BA/FNR/CI/user metrics; A không đổi Q3 | Đây là **bổ sung metric/protocol/estimand**, không approval M2. Mỗi biến thể calibration/grounding khác phải có amendment | T0 hợp đồng; số cụ thể T2 trước T3/T4 |
| O3 | **Owner đã chốt candidates**, còn duyệt vai trò/contract: Q3 cố định + tối đa một j từ Gemma3/Phi3.5/SmolVLM2 sau P1–P4; D_j thay hay bổ sung arm D_ord cũ; vai trò Q25/IVL3/Moondream2 và capability/N/A thesis | Roster bốn lịch sử giữ nguyên; chọn candidates không cấp quyền weights/GPU hay chứng minh utility. Cần approve rule/sequence/early-stop/FP16 qualification, common cohort, baseline/cost, negative route; không tự thêm features hoặc mặc nhiên phải thử hết/full data | T0 rule/feature proposal; T1 access/env/grant; T2 qualification/caps; T3 evidence-based final selection; T4 freeze |
| O4 | Cohort công nghiệp bổ sung, D/V/T/U theo verified sources, label rubric/expert adjudication, custodian, exposure/unknown policy | **Đề xuất thêm dữ liệu/partition nghiên cứu**, giữ InspecSafe raw/split/nhãn; cần quyền chủ nguồn, không coi Owner thay được quyền bên ngoài | T1 trước acquisition/annotation |
| O5 | b, δ, γ, α_FPR, 95% CI/α_stat, h/power/min source/events, bootstrap/ties/search/seeds, user-study margins, missing/cost caps; P1–P4 input envelope, invalid/near-constant/support/utility/stability/cost/stop thresholds | Numerical register từ pilot/workload/cluster simulation và quota thật, không nhìn target hoặc đặt cutoff tùy ý. Khóa trước screening chính; phê duyệt exact version/hash trước xác nhận | Quy tắc T0–T1; giá trị T2; freeze T4 |
| O6 | CPU artifact grant và từng qualification/development/target GPU grant, storage/export/license/budget | Cần exact source/model/revision/input/run/attempt, stop/retry policy; grant cũ không chuyển | Trước từng loại run |
| O7 | Evidence rubric/region annotation, reviewer tasks/consent, allowed images/examples và usefulness criteria | C không tự có ground truth vùng/faithfulness; thiếu → CT3 còn blocker; không gửi liên hệ/thu dữ liệu người dùng tự động | T1–T2 trước annotation/study |
| O8 | Tiếp tục sửa #136 cùng PR/session và reuse R1–R5 có giới hạn, hay dừng sau quyết định | Tiếp tục giảm viết lại nhưng còn audit FAIL; dừng phải budget reader/evaluator mới. Không tự sửa/merge/đóng trong task này | T0, trước nhánh R |

Không thay dataset/split/nhãn/metric/roster/protocol đã khóa ở PR này; các thay đổi đề xuất chỉ có hiệu lực khi được duyệt và ghi append-only trong DECISIONS ở T0/các gate sau. Không xem thông qua kế hoạch là quyền đọc target, quyền GPU hoặc chữ ký giảng viên.

## 15. NEXT TASK duy nhất và tiêu chí bàn giao kế hoạch

**NEXT TASK duy nhất sau khi kế hoạch được phê duyệt: T0 — Ghi quyết định chuyển tiếp và khóa hợp đồng Khóa luận.** Dùng ngay hồ sơ §14, công thức/experiments §6–9 và task card §11; ghi những mục thực sự được duyệt, phần chưa có evidence giữ PENDING. Không giao GPU, annotation, target evaluation hoặc sửa #136 từ task kế hoạch này.

PR kế hoạch chỉ gồm tài liệu này và [PROJECT_STATE](../PROJECT_STATE.md). Kiểm bàn giao: GitHub BASE/HEAD/PR #133–#136 trực tiếp; liên kết nội bộ/anchor; nguồn scientific/teacher và mức tiếp cận; UTF-8/no BOM/conflict/whitespace; diff đúng hai file; byte hashes M2 và DECISIONS không đổi; `git diff --check`. Unit tests/model tests không chạy vì không đổi code; không chạy GPU/inference/raw analysis hoặc đọc TEST. Kết quả kiểm thực tế và SHA/URL cuối ghi trong Draft PR, không tự tuyên bố kế hoạch đạt audit khoa học độc lập.

**Review boundary sau cập nhật candidates:** [ChatGPT PRE-AUDIT PASS](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6432171551) chỉ áp dụng HEAD `11a47c69372f64c51f6fcc8986bcc5c93eee3c17`, ghi SCIENTIFIC APPROVAL NOT GRANTED/MERGE NO và yêu cầu Antigravity audit. Bổ sung §6/§10/P1–P4/O3/T0–T4 phải được ChatGPT kiểm lại **HEAD và diff mới**; không nhận audit cũ bao phủ. Discussion đã kiểm chưa có bằng chứng Antigravity bắt đầu/kết luận, không suy offline audit chưa chạy. Nếu chưa bắt đầu, dùng HEAD mới trong PR; nếu đã bắt đầu, đối chiếu delta và audit bổ sung **cùng session Antigravity**, không mở session audit thứ hai. Codex không tự kích hoạt audit hoặc cấp PASS khoa học; dừng đúng Draft #137. Dù tài liệu được merge, scientific approval và execution gates vẫn phải ghi theo O1–O8, không đánh dấu thí nghiệm hoàn thành.
