# SafeShift — Kế hoạch tổng thể Seminar và Khóa luận

Ngày: **25/10/2026**, Asia/Bangkok. Base main: `3bcd3535ea51e023de77417ed5f2077607d49c93`.

**Một đề tài xuyên suốt:** SafeShift: Đánh giá và cải thiện độ tin cậy của quyết định nguy cơ an toàn công nghiệp bằng mô hình ngôn ngữ–thị giác. [Tài liệu chốt hướng](SEMINAR_THESIS_DIRECTION_LOCK_20261025.md) định nghĩa RQ, HNLO, phương pháp, bằng chứng và giới hạn. Kế hoạch này là đề xuất quản lý dự án để duyệt, không cấp quyền chạy hoặc sửa quyết định cũ.

Seminar bàn giao đánh giá hồi cứu nhãn–HNLO–lỗi/bất đồng, tận dụng TRAIN đã lưu. Khóa luận bàn giao và kiểm chứng bộ xếp ưu tiên kiểm tra nhẹ từ HNLO+bất đồng, giữ VLM cố định. Không huấn luyện VLM từ đầu, không mở một nhánh kiến trúc khác.

## 1. Cách dùng kế hoạch và chuỗi phụ thuộc

Không có deadline chính thức, ngân sách GPU, số nguồn độc lập hoặc số mẫu bảo đảm được xác nhận. Vì vậy dùng **mốc sản phẩm/gate** (điều kiện chuyển bước), không gán tuần giả. Sau khi hướng được duyệt, người phụ trách điền ngày mục tiêu và tài nguyên cho từng work package (gói việc) dựa trên lịch học và pilot thực tế.

| Học kỳ | Giai đoạn | Mốc bàn giao | Phụ thuộc bắt buộc |
| --- | --- | --- | --- |
| Chuẩn bị HK1 | 1. Khóa phạm vi/quyết định | M1: quyết định khoa học mới được duyệt | Review/merge hồ sơ theo quy trình Owner; hiện mới là Draft |
| HK1 | 2. Thiết kế thực nghiệm Seminar | M2: giao thức hồi cứu và hợp đồng phân tích | M1 |
| HK1 | 3. Tổ chức project | M3: nền tảng phân tích CPU đã review | M2 + nhiệm vụ setup riêng |
| HK1 | 4. Phân tích Seminar | M4: gói kết quả và lỗi có thể tái lập | M3 + quyền artifact/CPU cụ thể |
| HK1 | 5. Báo cáo/bảo vệ Seminar | M5: báo cáo, slide, hồ sơ giới hạn | M4 + tiêu chí học phần được giảng viên xác nhận |
| Chuyển HK1→HK2 | 6. Chuẩn bị dữ liệu/phương pháp Khóa luận | M6: gate dữ liệu và protocol xác nhận | M5; có thể chuẩn bị hồ sơ nguồn sớm sau M2 với nhiệm vụ/quyền riêng |
| HK2 | 7. Xây dựng/kiểm chứng cải tiến | M7: bộ triage, đối chứng, ablation, đánh giá khóa | M6 PASS + authority phát triển/chạy đúng phạm vi |
| HK2 | 8. Tổng hợp/bảo vệ Khóa luận | M8: báo cáo, gói tái lập, kết luận có giới hạn | M7 hoặc quyết định thu hẹp claim được duyệt nếu gate dữ liệu thất bại |

Luồng chuẩn là **M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8**. Chuẩn bị nguồn sớm không được trở thành quyền đọc target/chạy inference trước M6. Không chờ dữ liệu Khóa luận để hoàn thành gói Seminar hồi cứu.

Người chịu trách nhiệm cần được xác nhận ở M1: **Research Lead/giảng viên** phê duyệt khoa học và tiêu chí học phần; **Owner/người thực hiện** quản lý artifact, code và tiến độ; **người giữ target** kiểm soát truy cập; **chuyên gia nhãn** tạo chuẩn độc lập; **người review/audit** kiểm tra bằng chứng. Đây là vai trò dự kiến, chưa tự giao công việc cho người cụ thể.

PASS nghĩa đạt tiêu chí bằng chứng của gate, không nghĩa mô hình tốt hơn. FAIL chặn việc phụ thuộc; phải ghi lý do, việc có thể hoàn thành độc lập và điều kiện mở lại. Không tích lũy checkbox hoàn thành từ số test lịch sử hoặc lời hứa dữ liệu.

## 2. Giai đoạn 1 — Khóa phạm vi nghiên cứu và quyết định

**Mục tiêu:** chuyển lựa chọn duy nhất trong hồ sơ thành quyết định có thẩm quyền, không tự thay phạm vi đang hiệu lực.

**Đầu vào:** hai tài liệu PR này; D9R22; DEC-PA3-011 PROPOSED; nguồn main và receipt đã dẫn; ba tài liệu PR #132 và hậu kiểm. Main không có root TASKS/ROADMAP mới; giữ lịch sử theo AGENTS.

**Công việc chính:**

- ChatGPT kiểm tra trực tiếp BASE/HEAD/diff và kết luận; sau đó Antigravity audit theo quy trình Owner. Không sửa/merge PR #132 trong task này.
- Trình giảng viên tên đề tài, mục tiêu Seminar, ba S-RQ tích hợp HNLO, đóng góp thực nghiệm Khóa luận và chấp nhận kết quả âm.
- Quyết định rõ ngoại lệ Seminar: bảng bốn model, định lượng ba model, Moondream2 HNLO TRAIN N/A; các ô hazard/control thiếu cần xử lý hoặc được chấp nhận minh bạch. Không bỏ roster.
- Phê duyệt estimand hồi cứu, so sánh cùng ảnh, sensitivity nhóm, giới hạn TRAIN; không mặc định HNLO là probability hoặc thay D9R22-RQ3 bằng AUROC.
- Ghi quyết định mới append-only dưới `docs/` sau phê duyệt, dẫn quyết định cũ và nêu phần thay thế. Không sửa D9R22/DEC-PA3-011 để giả như đã duyệt từ trước.

**Bàn giao M1:** văn bản quyết định có người duyệt/ngày/phạm vi; bảng nội dung được duyệt/chưa duyệt; danh sách authority cần cho M2–M4; xác nhận mức sản phẩm tối thiểu của hai học kỳ.

**PASS:** quyết định mới đủ tên đề tài, RQ, vai trò HNLO, xử lý bốn model/N/A và loại kết luận cho phép. **FAIL:** chỉ merge Markdown hoặc đồng ý tên chung nhưng chưa duyệt điều chỉnh/ngoại lệ. Chưa M1 thì D9R22 tiếp tục hiệu lực; không thực nghiệm HNLO mới theo hồ sơ này.

**Chuyển bước:** M1 PASS mới giao thiết kế chi tiết M2. Rủi ro giảng viên yêu cầu bốn kết quả đầy đủ: xin task/quyền/tài nguyên hoàn tất Moondream2 và điều chỉnh mốc, không tự coi ba model là đủ. Phụ thuộc ngoài: lịch review, tiêu chí học phần, người có quyền duyệt; không tự hứa ngày phê duyệt.

## 3. Giai đoạn 2 — Chuẩn hóa thiết kế thực nghiệm Seminar

**Mục tiêu:** khóa hợp đồng hồi cứu đủ cụ thể để code và báo cáo không đổi câu hỏi theo kết quả.

**Đầu vào:** M1; metadata/receipt đã lưu; hợp đồng run lịch sử; danh mục 12 hazard atoms/7 nhóm và chính sách miền D3. Chỉ đọc artifact nằm trong quyền mới; chưa mở dataset TEST.

**Công việc chính:**

1. Lập bảng model/revision/run/attempt/prompt/preprocessing/precision/decoding/parser và mức audit. Tách saved-score, raw replay, receipt/runtime; ghi phần chưa khép của Q25/IVL3/Q3.
2. Khóa mẫu phân tích: 3.763 Q25/IVL3; chính ba model cùng 3.539 V4-success gốc; Recovery224 riêng; 2.822 cũ chỉ truy vết. Q3 planned 3.763, không đổi mẫu số coverage. Phân bố ID/nhãn/miền và hash phải khớp receipt.
3. Đặc tả S-RQ1–3, positive class (lớp dương), tử/mẫu số, INVALID/lỗi/chưa chạy, ties, metric undefined, cohort chung và bảng bốn model có N/A. Tách score hazard với score lỗi.
4. Kiểm map hazard có thể tái dùng; nếu không đủ thì trình trạng thái blocker/N/A, không lấy tên file hoặc lời VLM làm nhãn. Chốt continuous controls nào thật sự khả dụng; phần không đủ chỉ để giới hạn kết luận.
5. Khóa sensitivity theo ảnh/exact/heuristic, không chọn biến thể theo gap; không CI nguồn khi chưa xác minh source. Hợp đồng risk–coverage chỉ mô tả, không lựa chọn ngưỡng triển khai trên TRAIN.
6. Chốt ma trận đầu ra bắt buộc, danh sách điều chưa đo và phép kiểm tra độc lập bằng fixture tổng hợp. Ghi rõ mọi metric mới vẫn cần phê duyệt, không suy metric family trong D9R22 là hợp đồng đã hoàn tất.

**Bàn giao M2:** protocol hồi cứu version/hash; manifest hợp lệ không chứa dữ liệu nhúng/đường dẫn máy cá nhân; bảng model/coverage; đặc tả metric/control; danh sách artifact và quyền đọc; acceptance checklist (tiêu chí nghiệm thu) để dùng trực tiếp cho task setup.

**PASS:** người review truy được mỗi ô dự kiến đến nguồn/metric/cohort/quyền; mọi N/A có lý do và phạm vi claim; thông tin chưa khép không bị nâng audit. **FAIL:** trộn V4/recovery, không khóa mẫu số, thiếu map nhưng vẫn báo hazard analysis đầy đủ, hoặc cần inference mới ngoài quyền mà gói tối thiểu không nêu.

**Chuyển bước:** M2 được duyệt + giao riêng task tổ chức project mới sang M3. Rủi ro dữ liệu summary thiếu field: giảm phạm vi claim theo M1/duyệt bổ sung, không tạo logit giả. Phụ thuộc ngoài: người giữ artifact và quyền CPU/raw summaries; raw replay là task riêng nếu cần, không kéo thành điều kiện bắt buộc cho mọi kết luận saved-score.

## 4. Giai đoạn 3 — Thiết lập cấu trúc project phù hợp

**Mục tiêu:** mở rộng Foundation V1 vừa đủ cho giao thức đã duyệt, bảo toàn lịch sử.

**Đầu vào:** M2, task setup riêng, [kiến trúc hiện hành](../ARCHITECTURE.md), [lịch sử/ref bất biến](../HISTORY.md). Không nhập lại 693 file cũ hoặc tạo pipeline GPU cho đủ cấu trúc.

**Công việc chính:** rà khả năng tái sử dụng records/validation/exact join/INVALID; bổ sung reader saved artifact có quyền, schema version và provenance; triển khai metric được duyệt; tests tổng hợp và lệnh CPU tái lập. Chỉ thêm adapter dataset/model khi có chức năng được giao riêng. Thiết kế nhóm thành phần ở §10 là gợi ý tổ chức, không lệnh tạo mọi folder.

**Bàn giao M3:** PR kỹ thuật riêng phạm vi nhỏ; code phân tích CPU với fixtures tổng hợp, lock dependency tối thiểu nếu thực sự cần; hợp đồng input/output; hướng dẫn chạy từ root; report schema và kiểm checksum/coverage; kế hoạch lưu artifact ngoài Git.

**PASS:** test có giá trị cho ID trùng/thiếu, nhãn sai, INVALID, zero denominator, score nonfinite, ties, groups bắc cầu, recovery bị trộn và provenance không hợp lệ; tính mẫu nhỏ được đối chiếu bằng oracle khác cách triển khai. **FAIL:** test chỉ khớp chính code, demo tổng hợp bị đưa thành kết quả thật, đọc dữ liệu khóa hoặc chuyển quyền legacy sang main.

**Chuyển bước:** review/merge PR kỹ thuật + protocol/source version khóa + authority CPU cụ thể mới sang M4. Rủi ro khác schema lịch sử: adapter riêng có kiểm hợp đồng; không sửa artifact gốc. Phụ thuộc ngoài: review kỹ thuật và quyền thay đổi repo; môi trường/dependency mới chỉ thiết lập trong nhiệm vụ setup, không trong PR tài liệu này.

## 5. Giai đoạn 4 — Hoàn thiện thực nghiệm và phân tích Seminar

**Mục tiêu:** trả lời S-RQ1–3 ở mức hồi cứu được duyệt bằng sản phẩm có thể kiểm tra lại.

**Đầu vào:** M3, artifact được phép đúng hash, protocol M2, ngoại lệ/N/A M1. Không có quyền GPU chỉ vì code/interface tồn tại.

**Công việc chính:** chạy saved-report analysis CPU; xuất bảng coverage trước bảng metric; tách nhãn/score/lỗi, cohort đầy đủ/chung/phụ. Phân tích miền, 12 atoms khi map hợp lệ, Level01/Level03 và false-safe; kiểm đồng thuận suy biến. Tái lập sensitivity được duyệt từ gate; ghi tất cả biến thể, không chỉ cái có lợi. Review định tính ảnh chỉ khi có quyền riêng, không cần mở ảnh để tái tính bảng saved score.

**Bàn giao M4:** bộ bảng/figure nhỏ được kiểm; local artifact có command/env/seed/commit/hash; bảng từng S-RQ với kết luận/giới hạn/không xác định; bảng lỗi/coverage và checklist chống pooling. Ghi rõ số nào mới tái tính và số nào kế thừa; không gọi raw audit nếu chỉ đọc CSV.

**PASS:** đối soát mẫu số và ID; output tái tạo được; phân loại mức bằng chứng đúng; đủ bảng tối thiểu M2 và các ô N/A được duyệt. Không yêu cầu HNLO thắng, bất đồng có ích hoặc ranking đảo. **FAIL:** AUROC tốt được trình thành quyết định an toàn, thiếu Moondream2 bị giấu, nhãn Q3 ghép được dùng cho cohort gốc, CI ảnh được gọi độc lập nguồn.

**Chuyển bước:** nghiệm thu M4 mới chốt nội dung M5. Rủi ro checksum/cohort không khớp: STOP nhánh tính liên quan, tìm đúng artifact, giữ nguyên phần khác đã xác minh; không lấp bằng recovery. Phụ thuộc ngoài: quyền artifact, reviewer đối soát; inference bổ sung không thuộc đường hoàn thành tối thiểu đã đề nghị.

## 6. Giai đoạn 5 — Hoàn thiện báo cáo và bảo vệ Seminar

**Mục tiêu:** trình bày một kết quả khoa học hoàn chỉnh về đánh giá độ tin cậy với giới hạn trung thực.

**Đầu vào:** M4, tiêu chí học phần và lịch bảo vệ do giảng viên xác nhận. Tên đề tài xuyên hai kỳ giữ nguyên; phụ đề Seminar nêu rõ “đánh giá hồi cứu”.

**Công việc chính:** viết câu hỏi → thiết kế → kết quả → phản biện; phân biệt hazard AUROC/nhãn/nhận diện lỗi; thể hiện số mẫu/coverage trên bảng và hình. Kiểm nguồn, provenance và mọi claim độc lập nguồn. Chuẩn bị trả lời vì sao HNLO không là xác suất, vì sao chưa đủ bốn kết quả và vì sao audit/negative result có giá trị. Nối hạn chế Seminar với H-T của Khóa luận, không thêm hướng mới.

**Bàn giao M5:** báo cáo, slide, phụ lục truy nguồn/định nghĩa metric, bản kết luận S-RQ1–3, danh sách việc tiếp nối H-T. Chỉ ở nhiệm vụ slide sau này mới áp dụng skill làm slide của repo.

**PASS:** nội dung khớp M4 và quyết định M1; giảng viên chấp nhận phạm vi/kết quả tối thiểu, không đánh dấu đã bảo vệ trước khi xảy ra. **FAIL:** hứa generalization, kiến trúc mới, đã hiệu chuẩn hoặc bốn model hoàn tất không có bằng chứng.

**Chuyển bước:** bản nghiệm thu Seminar và giả thuyết nối tiếp được ghi nhận mới đóng M5. Rủi ro kết quả “không cải thiện”: trình bằng chứng và giới hạn có thể bác bỏ, không tìm grouping/model khác để có hiệu ứng. Phụ thuộc ngoài: lịch, chuẩn báo cáo, hội đồng/giảng viên; kế hoạch không tự đặt ngày nộp/bảo vệ.

## 7. Giai đoạn 6 — Chuẩn bị điều kiện dữ liệu và phương pháp Khóa luận

**Mục tiêu:** đủ điều kiện kiểm nghiệm bộ xếp ưu tiên HNLO+bất đồng với dữ liệu tách nguồn, trước khi nhìn kết quả target.

**Đầu vào:** M5; giả thuyết H-T và phương pháp logistic ở tài liệu hướng §6; quyền dùng TRAIN phát triển; đầu mối dữ liệu/chuyên gia/tài nguyên thực tế. Có thể chuẩn bị giấy tờ nguồn sớm sau M2 bằng task riêng; chưa thu thập hoặc gán nhãn khi thiếu quyền.

**Công việc chính:**

- Xác minh đường lấy cohort công nghiệp mới, license/quyền dùng và sự tương thích định nghĩa nhãn; không mặc định dataset khác là kiểm định thay thế. Giữ InspecSafe nguyên bản và TEST đóng.
- Xác minh nguồn, duplicate, camera/video/session; lập manifest nghiên cứu riêng theo quyền. Tách development, calibration và target theo nguồn; target có người giữ kín. TRAIN chia lại chỉ là phát triển đã phơi nhiễm.
- Đề xuất quy trình nhãn độc lập VLM, kiểm bất đồng, adjudication và chi phí thực. Không yêu cầu nhãn vùng mới cho phương pháp không grounding; nguồn có cả hai trạng thái cần nếu muốn kiểm chứng hazard validity ngoài utility triage.
- Pilot trên development để biết số nguồn, số lỗi false-safe, chi phí raw capture và inference; không xem target để xác định có đủ lỗi hay không. Dự toán độ chính xác/khả năng phát hiện hiệu ứng theo cụm, không đếm frame như mẫu độc lập.
- Khóa Q3 predictor, Q25/IVL3 phụ trợ; quyết định vai trò Moondream2 trước target. Bảo đảm raw capture và token alignment đủ cho các baseline liên tục; duyệt ba-model feature set nếu Moondream2 chưa tương thích.
- Chốt `b` (ngân sách review), `δ` (lợi ích tối thiểu có ý nghĩa), giới hạn chi phí/workload/suy giảm nhóm, mẫu số, primary contrast (so sánh chính), CI, ties/INVALID/overload, ablation và search budget. Giá trị số phải dựa tài nguyên/chuyên gia/pilot, được duyệt trước target.
- Kiểm paper LMN/SGR/ConfBench đúng phạm vi; quyết định khả thi baseline LMN thích nghi, không tự nhận tái lập nếu thiếu embedding tương ứng. Không cần vòng khảo sát rộng mới.

**Bàn giao M6:** hồ sơ quyền/nguồn/nhãn; manifest development–calibration–target đã khóa; người giữ target; protocol Khóa luận version/hash; dự toán calls/VRAM/giờ annotation từ pilot; điều kiện dừng và mức claim được duyệt.

**PASS cho nghiên cứu xác nhận:** nguồn tách thật và đủ số nhóm/sự kiện lỗi theo precision plan; target chưa dùng chọn phương pháp; đủ baseline/raw contract; tài nguyên và execution scope được cấp. **FAIL:** chỉ có heuristic groups, target đã dùng chọn feature, không có error events đủ ước lượng, hoặc chưa có quyền/nguồn. Không sửa chuẩn PASS cho vừa dữ liệu.

**Xử lý FAIL:** vẫn hoàn thiện đặc tả và kiểm nghiệm phát triển được phép; ghi rõ H-T ngoài nguồn chưa kiểm định, không tự chạy M7-target. Trình giảng viên quyết định mức đóng góp hồi cứu có đáp ứng Khóa luận hoặc cần thêm thời gian/nguồn. Đây là giảm mức kết luận trong cùng đề tài, không mở lại danh sách hướng. Thiếu dữ liệu độc lập không làm mất kết quả Seminar.

**Chuyển bước:** M6 PASS mới mở M7 xác nhận; từng run còn cần quyền đúng model/revision/source/release/run/attempt. Phụ thuộc ngoài: đối tác/giấy phép dữ liệu, người gán nhãn, GPU, người giữ target, tiêu chí Khóa luận. Không có lời hứa chắc rằng các điều kiện này đã sẵn.

## 8. Giai đoạn 7 — Xây dựng và kiểm chứng phương pháp cải tiến

**Mục tiêu:** kiểm định H-T bằng lớp logistic HNLO+bất đồng, giữ predictor và điều kiện so sánh.

**Đầu vào:** M6 PASS cho phần xác nhận; code/protocol được review; quyền inference và artifact; development/calibration/target đúng vai trò.

**Công việc chính:**

1. Kiểm adapter và raw-before-parse, cả lỗi/chưa chạy; qualification kỹ thuật nhỏ trên dữ liệu được phép trước chạy lớn. Không ghép run thất bại/recovery thành baseline khác cấu hình.
2. Trích feature từ output frozen; chuẩn hóa/fit trong development, validation theo nguồn để chọn regularization. Không dùng ID chứa Level, ground truth hay source ID làm feature. Source weighting là nhánh chính đã duyệt; image weighting là ablation.
3. Fit baseline và mô hình chính cùng supervision/search budget; chạy đủ ablation: bỏ HNLO, bỏ bất đồng, chỉ Q3, bỏ source weighting, đổi target lỗi chung. Khóa artifact/model/source SHA trước target.
4. Calibration dùng riêng theo protocol; batch triage giữ cùng số ca review giữa các arm, ưu tiên lỗi kỹ thuật theo hợp đồng. Không chọn `b` sau thấy đường target đẹp. Đồng thời tính toàn bộ call cost của model phụ trợ.
5. Người giữ target cho chạy một lượt xác nhận đã khóa; giữ mọi raw output trước parse, liên kết sample/prompt/model/version/config/run/attempt/commit. Thay đổi sau khi xem target phải ghi exploratory và cần cohort mới để xác nhận.
6. Tính capture false-safe, số bỏ sót còn trong phần tự xử lý, severe miss, workload/coverage, FP và chi phí; CI ghép theo nguồn nếu đủ nhóm. Báo từng miền/nguồn, undefined và overload, không giả người review luôn đúng.

**Bàn giao M7:** implementation lớp quyết định nhỏ và test; immutable (bất biến) run manifests; bảng chính/đối chứng/ablation; hình trade-off (đánh đổi) lỗi–review–chi phí; verdict H-T = ủng hộ/bác bỏ lợi ích tối thiểu/chưa đủ bằng chứng; hồ sơ sai lệch protocol và nghiên cứu âm.

**PASS thực hiện nghiên cứu:** đúng protocol, đủ đối chứng, output truy vết/tái lập và kết luận theo tiêu chí §6.5 tài liệu hướng. **PASS lợi ích phương pháp** là tiêu chí riêng: cận dưới chênh capture vượt `δ`, cùng ngân sách và thỏa ràng buộc. Không thắng vẫn PASS thực hiện nghiên cứu. **FAIL thiết kế/thực thi:** rò target, bỏ baseline mạnh, thay predictor giữa các arm hoặc giấu chi phí/lỗi.

**Chuyển bước:** M7 kiểm toán được → M8 dù kết quả âm. Rủi ro model cùng thiên lệch/đầu logistic overfit: báo kết quả ablation và giới hạn, không fine-tune VLM hoặc đổi hướng trái scope. OOM: dừng và xin run/config mới; không sửa ngầm precision/crop rồi pooling. Phụ thuộc ngoài: GPU, target custodian, expert review, raw capture của model và audit độc lập.

## 9. Giai đoạn 8 — Tổng hợp nghiên cứu, viết và bảo vệ Khóa luận

**Mục tiêu:** trình bày chuỗi nghiên cứu từ bằng chứng Seminar đến phương pháp/kiểm nghiệm Khóa luận, đủ tái lập và trung thực về mức kết luận.

**Đầu vào:** M5, M7 và mọi quyết định protocol; hoặc quyết định giảm claim được giảng viên duyệt sau M6 FAIL. Không coi gói hồi cứu là đã hoàn thành phần đánh giá độc lập.

**Công việc chính:** nối S-RQ với H-T; trình nguồn/nhãn/exposure, tiên nghiệm và phân tích hậu nghiệm; so công trình gần, chỉ rõ logistic/triage là kỹ thuật có sẵn; nêu bằng chứng tăng thêm hoặc bác bỏ. Kiểm figure/metric/mẫu số, bổ sung reproducibility appendix và hạn chế chi phí/người review. Chọn artifact nhỏ có quyền chia sẻ, dữ liệu/raw/checkpoint giữ ngoài Git.

**Bàn giao M8:** luận văn, slide bảo vệ, gói code/fixture/protocol/manifest nhỏ, hướng dẫn tái lập, bảng đóng góp/giới hạn, hồ sơ kết quả âm hoặc chưa đủ bằng chứng. Không hứa bài báo được nhận; xuất bản là việc sau, nếu có.

**PASS:** báo cáo khớp bằng chứng và scope được duyệt, đủ phần bắt buộc của học phần; bảo vệ chỉ đánh dấu hoàn thành sau xác nhận thực tế. **FAIL:** claim chuyển nguồn không có target hợp lệ, claim HNLO calibrated, nhận kiến trúc mới không đối chiếu, hoặc nói hệ thống giảm tai nạn từ routing simulation.

**Kết thúc:** đóng hồ sơ nghiên cứu, bảo toàn ref/artifact/provenance; không tự triển khai ra môi trường an toàn thật. Rủi ro kết quả yếu/âm: bảo vệ thiết kế, đối chứng và điều kiện bác bỏ; nếu protocol không hợp lệ phải ghi chưa hoàn thành, không gọi thất bại thiết kế là kết quả âm. Phụ thuộc ngoài: lịch bảo vệ, chuẩn Khóa luận, quyền chia sẻ và phản hồi giảng viên.

## 10. Kiến trúc tổ chức dự kiến cho nhiệm vụ setup sau

Đây là **nhóm trách nhiệm**, chưa tạo folder hoặc chốt tên module. Tái dùng Foundation V1 trước; chỉ thêm thành phần khi có task chức năng. Tên đường dẫn dưới đây là relative path từ root.

| Nhóm thành phần dự kiến | Đầu vào → đầu ra, lý do | Ranh giới triển khai |
| --- | --- | --- |
| Dữ liệu/nguồn, mở rộng `safeshift/data/` | Metadata/manifest có quyền → validated ID, canonical labels, domain, source status và exposure | Không suy source thật từ point/dHash; không sửa raw/split/nhãn; dẫn xuất ở `data/processed/` ignored |
| Giao diện model, `safeshift/models/` | Input transport → output gốc + model/revision/config | Backend cụ thể chỉ khi cấp task; tách qualification và quyền inference khỏi interface |
| Lưu artifact/provenance | Raw output từng sample/call → liên kết run/attempt/hash/prompt/config/status trước parse | Lưu cả lỗi/dở; không commit raw/checkpoint; không overwrite hoặc pooling recovery |
| HNLO nếu được duyệt | Raw logits/summaries đủ hợp đồng → score + token/prefix validation + audit level | Giữ scorer theo model/revision; reject alignment sai; không sinh xác suất calibrated hoặc score giả |
| Phân tích hiệu năng/lỗi/độ tin cậy, mở rộng `safeshift/evaluation/` | Cohort exact join → confusion/support/coverage, hazard ranking, error signals, sensitivity | Hợp đồng metric version; undefined đúng mẫu số; phân biệt image weight với source inference |
| Lớp triage Khóa luận | Feature hợp lệ từ frozen output → điểm ưu tiên và accept/defer status | Chỉ sau M6/authority; fit/normalization/calibration tách target; không tạo trước training pipeline trong setup Seminar |
| Tests/tái lập, `tests/` và `scripts/` | Fixtures tổng hợp nhỏ → test oracle, command receipts, bảng/figure | Không dataset thật trong tests, không mirror implementation; schema/hash/version/seed/commit đầy đủ |
| Quyết định/báo cáo, `docs/` | Quyết định duyệt và kết quả có nguồn → log mới, protocol, báo cáo | Append-only đối với quyết định; lịch sử pin SHA; không viết lại hồ sơ cũ để khớp triển khai |

Hợp đồng xuyên suốt: sample ID → dataset/version/checksum → cohort/source/exposure → model/revision/prompt/preprocess/decoding → run/attempt → raw artifact → parser/scorer version → metric/report. Mọi đường dẫn trong manifest/docs/code tương đối; chỉ artifact/figure/manifest nhỏ có quyền chia sẻ được vào Git. `data/` bị ignore; không `git add -f` hoặc Git LFS cho dataset/raw/checkpoint.

## 11. Rủi ro xuyên suốt và hành động cụ thể

| Rủi ro/điểm phát hiện | Xử lý đã chọn | Điều bị chặn, phần vẫn làm được |
| --- | --- | --- |
| Điều chỉnh HNLO/N/A chưa được duyệt ở M1 | Giữ D9R22, ghi pending; xin quyết định cụ thể | Chặn thực nghiệm thay scope; hoàn thiện hồ sơ proposal được phép |
| Moondream2 chưa có endpoint TRAIN | Bảng bốn model có N/A; xin ngoại lệ Seminar; không ghép confidence văn bản | Chặn claim bốn-model complete, không chặn hồi cứu ba model sau ngoại lệ |
| Raw audit IVL3/Q3 chưa đủ | Báo saved-score đúng cấp; raw replay task riêng nếu cần | Chặn raw PASS, không chặn số mô tả saved score |
| Q3 224 thiếu/Recovery khác config | Báo planned, missing labels và cận giả định nếu duyệt; recovery riêng | Chặn baseline pooled 3.763 và suy missing-at-random |
| Map nguồn/visual catalog sai hoặc heuristic | Dùng artifact đúng hash; adjudication riêng; không gán nguồn từ filename | Chặn CI nguồn/transfer; vẫn có sensitivity hồi cứu |
| Hazard mapping/continuous control thiếu | Kiểm hợp đồng, báo N/A, xin quyền hoàn tất nếu thật cần | Chặn claim tương ứng, không tự tạo nhãn/score |
| Ít Level03/false-safe/nguồn độc lập | Số ca/CI rộng/undefined; precision plan sau pilot development | Chặn claim cải thiện ở nhóm hiếm; không bịa power/N |
| Triage “thắng” vì chuyển nhiều hơn hoặc predictor đổi | Cùng predictor/batch/budget/mandatory errors, baseline Normal-only random | Loại phép so không công bằng; chạy lại chỉ khi quyền/protocol cho phép |
| Thêm model tăng chi phí hoặc OOM | Cache sequential, đo tổng call/latency/VRAM; cấu hình mới cần review riêng | Không hứa chi phí thấp chỉ vì đầu logistic nhỏ |
| Không có target độc lập ở M6 | NO-GO xác nhận; trình mức nghiên cứu hồi cứu với giảng viên | Giữ đề tài và gói Seminar; không gọi TRAIN mới chia là holdout |
| HNLO/bất đồng không có giá trị tăng thêm | Báo ablation/CI và kết quả âm | Không ép tìm kiến trúc mới hoặc bỏ đối chứng để cứu giả thuyết |

## 12. Việc làm ngay sau khi quyết định được phê duyệt

Thứ tự dưới đây dùng trực tiếp để giao nhiệm vụ tiếp theo; **chưa thực hiện trong PR này**:

1. Lưu quyết định mới có người duyệt, phạm vi thay đổi so D9R22, trạng thái HNLO, ngoại lệ Moondream2 và các N/A. Chốt người phụ trách, deadline học phần thật, quyền artifact và mức kết quả tối thiểu Khóa luận.
2. Giao task **M2: đặc tả giao thức Seminar hồi cứu**. Đầu ra cần là cohort/model contract, metric/denominator/control contract, source limitations và acceptance checklist; không kèm GPU/TEST.
3. Phê duyệt M2, rồi giao task **M3: kế hoạch kỹ thuật chi tiết và setup có phạm vi**. Kiểm code Foundation V1 có thể tái dùng; chỉ đề xuất module/dependency cần cho saved-report CPU trước.
4. Cấp quyền CPU đúng artifact và source version; sau review triển khai mới thực hiện M4. Xác nhận trước ai đối soát kết quả, ai viết báo cáo và tiêu chí đóng M5.
5. Mở việc chuẩn bị M6 riêng: xác minh đối tác/nguồn/nhãn/quyền và tài nguyên thực, không tải dữ liệu hay mở target theo quyền Seminar. Không trì hoãn Seminar để đợi phương pháp mới thành công.

## 13. Trạng thái tại bàn giao Draft PR

Chỉ hoàn thành **hai tài liệu định hướng/kế hoạch đề xuất**. M1 khoa học, M2–M8, project setup, protocol freeze và thực nghiệm mới đều **chưa hoàn thành/chưa được cấp quyền bởi task này**. Không sửa code, dữ liệu, model, cấu hình, D9R22, DEC-PA3-011 hoặc lịch sử; không mở TEST, chạy GPU/inference, merge PR #132 hay PR mới.

Kiểm tra phù hợp: đối chiếu cohort/số liệu/mức audit với nguồn pin SHA và receipt, kiểm tên/link tài liệu nội bộ, UTF-8, whitespace và diff chỉ hai Markdown. Không chạy unit tests phần mềm hoặc inference vì không thay code; không nhận số tests lịch sử là tests của task. BASE/HEAD, branch, PR URL và kết quả kiểm tra thực tế ghi trong mô tả Draft PR để tránh hash tự tham chiếu.
