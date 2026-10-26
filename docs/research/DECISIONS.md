# SafeShift — Quyết định nghiên cứu (append-only)

Không sửa mục đã ghi để đổi lịch sử. Quyết định kế tiếp phải có ID, ngày, người
quyết định, nguồn, phạm vi thay thế và điều kiện hiệu lực riêng.

## DEC-20261026-M1 — Phạm vi Seminar–Khóa luận do Owner quyết định

- Ngày quyết định: **26/10/2026, Asia/Bangkok**; nguồn GitHub tạo lúc
  `2026-10-26T02:17:17Z` (09:17:17 giờ Bangkok).
- Người quyết định: **SafeShift Owner / Research Lead theo xác nhận của Owner**,
  GitHub `tantdna2`. Codex ghi hồ sơ, không phải người cấp quyền khoa học.
- Nguồn: [chỉ thị Owner tại PR #134](https://github.com/tantdna2/SafeShift/pull/134#issuecomment-6406751802),
  cùng yêu cầu M1+M2 của Owner ngày 26/10/2026 trong task hiện tại.
- Phát biểu Owner được ChatGPT chuyển vào GitHub:
  **“thầy tôi cho tự làm chứ không cần phải thầy duyệt nên là tiếp tục bước tiếp theo đi, tôi duyệt là được rồi”**.
  Đây là phát biểu trực tiếp của Owner được thuật lại, **không phải chữ ký hoặc
  văn bản phê duyệt của giảng viên**, cũng không phải ủy quyền học vụ được kiểm chứng.
- Base kiểm chứng: `a425ab04695319a42bfdd2f89192717dddbb891b`;
  [PR #134 đã MERGED](https://github.com/tantdna2/SafeShift/pull/134).
- Trạng thái M1: **OWNER_PROJECT_SCOPE_APPROVED / RECORDED**. Việc ghi nhận có
  nguồn thật; GitHub review/merge hồ sơ vẫn riêng. M2 chưa được phê duyệt từ đây.

### Nội dung A1–A8 và giới hạn của quyết định

| ID | Quyết định trong quyền dự án | Phần chưa được cấp/xác minh |
| --- | --- | --- |
| A1 | Chọn **SafeShift: Đánh giá và cải thiện độ tin cậy của quyết định nguy cơ an toàn công nghiệp bằng mô hình ngôn ngữ–thị giác**. Seminar hồi cứu; Khóa luận nghiên cứu xếp ưu tiên kiểm tra trên VLM cố định theo PR #133. “Cải thiện” là mục tiêu cần kiểm chứng. | Không xác nhận tên/chuẩn học phần đã được nhà trường thay đổi. |
| A2 | Chấp nhận ba S-RQ bên dưới và HNLO là đối tượng kiểm chứng Seminar, feature ứng viên Khóa luận. | Công thức metric/đối chứng/N/A chi tiết mới của M2 cần review độc lập và quyết định đúng version trước code M3. |
| A3 | Chọn cohort Qwen2.5/InternVL3 đủ 3.763 ảnh TRAIN; so ba model trên đúng 3.539 SUCCESS Qwen3 V4 gốc. Coverage Q3 trên 3.763 planned; Recovery224 tách riêng. Per-image mô tả; exact/heuristic là sensitivity hồi cứu, không nguồn độc lập. | Không cho quyền đọc artifact mới, không giả định missing-at-random, không công nhận CI nguồn hoặc generalization. |
| A4 | Chấp nhận ở **phạm vi báo cáo định lượng Seminar của dự án**: bảng đủ bốn model, định lượng ba; Moondream2 HNLO TRAIN **N/A do thiếu bằng chứng tương thích**. Giữ Qwen2.5-VL-3B-Instruct, Qwen3-VL-8B-Instruct, InternVL3-2B-hf, Moondream2 trong roster. | Không khẳng định giảng viên đã duyệt ngoại lệ học phần; không tự chuyển ngoại lệ sang feature roster Khóa luận; không thay bằng textual confidence. |
| A5 | Giữ 12 hazard atoms, 7 nhóm A–G phụ và D3. Chấp nhận chính sách báo thiếu bằng chứng, giới hạn claim, không tự tạo hazard map/continuous controls. | **Không duyệt trọn gói mọi N/A chưa định danh**. N/A hazard/control cụ thể ở M2 cần người review/Lead chấp nhận; thiếu mapping chặn đúng bảng hazard. |
| A6 | Owner chọn đóng góp **nghiên cứu thực nghiệm**: logistic có regularization dùng HNLO+bất đồng, giữ Q3 predictor cố định, so baseline mạnh cùng budget và báo toàn bộ chi phí VLM phụ; chấp nhận kết quả âm hợp lệ ở cấp dự án. Không cam kết kiến trúc/thuật toán mới. | Tính đủ chuẩn học phần Khóa luận, nghiệm thu/bảo vệ và việc chấp nhận phạm vi giảm **chưa được xác minh độc lập**; không tự gọi APPROVED học vụ. |
| A7 | Khóa luận xác nhận phải có nguồn công nghiệp tương thích được phép, tách development/calibration/target theo nguồn thật, nhãn chuyên gia mù VLM, target giữ kín, đủ nguồn/sự kiện theo precision plan khóa trước target. | Chưa có nguồn/nhãn/custodian/precision/tài nguyên được cấp. Thiếu gate thì NO-GO xác nhận; TRAIN đã phơi nhiễm/chia lại không thay target độc lập, TEST vẫn đóng. |
| A8 | Owner là người quyết định phạm vi khoa học dự án; cho thực hiện **tài liệu M1/M2 và một Draft PR** trong task này. Reviewer độc lập kiểm M2, Owner quyết định version sau review. | Chưa chỉ định cá nhân reviewer/custodian/chuyên gia hoặc deadline/ngân sách. Không cấp setup M3, reanalysis M4, raw replay, ảnh/annotation, GPU/inference, TEST hay tài nguyên bên thứ ba. |

Ba câu hỏi Seminar được Owner chọn:

1. **S-RQ1:** Nhãn sinh ra và HNLO biểu hiện khác nhau thế nào về phân loại và
   xếp hạng nguy cơ qua năm miền trên cùng ảnh?
2. **S-RQ2:** Lỗi nghiêm trọng tập trung ở đâu và kết luận thay đổi thế nào khi
   xét mẫu thiếu, ảnh trùng và các giả định nhóm?
3. **S-RQ3:** Bất đồng liên mô hình và HNLO có liên hệ với quyết định sai, đặc
   biệt false-safe, hay chỉ phản ánh thiên lệch nhãn chung?

Khóa luận kiểm giả thuyết H-T về giá trị tăng thêm của HNLO+bất đồng trong xếp
ưu tiên false-safe, cùng predictor/cohort/ngân sách review, baseline đơn tín
hiệu mạnh nhất khóa trên development, đủ ablation và chi phí toàn bộ model.
HNLO không là xác suất nguy cơ đã hiệu chuẩn; hazard AUROC không chứng minh
khả năng phát hiện quyết định sai. Kết quả âm khác lỗi thiết kế/thực thi.

### Quan hệ với D9R22 và thời điểm hiệu lực

Nguồn bất biến: [D9R22](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/configs/pre_freeze/d9r22_seminar_scope.v1.json),
[DEC-PA3-011 lịch sử](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/DECISIONS.md#dec-pa3-011--proposed-seminar-internal-hazard-score-direction-2026-10-16),
[hướng PR #133](SEMINAR_THESIS_DIRECTION_LOCK_20261025.md),
[A1–A8 trong Execution Plan](../EXECUTION_PLAN.md#2-hồ-sơ-m1-sẵn-để-trình-research-leadgiảng-viên).

| Hợp đồng | Kế thừa / bổ sung / thay thế có giới hạn |
| --- | --- |
| Nhãn/dataset/split/roster | **Kế thừa** nguyên bản; bốn mô hình, năm miền, Level01–04. Không thêm model thứ năm hoặc relabel. |
| D9R22 RQ1 | **Kế thừa** lõi phân loại xuyên miền/D3; **bổ sung** HNLO và đối chứng nhãn/ordinal. |
| D9R22 RQ2 | **Kế thừa** lỗi nghiêm trọng, 12 atoms/7 nhóm phụ, chồng lấp không cộng; **bổ sung** sensitivity coverage/ảnh trùng có định danh. |
| D9R22 RQ3 | **Kế thừa** tái dùng prediction RQ1/RQ2 và các họ bất đồng; **bổ sung** liên hệ HNLO với lỗi, không biến hazard AUROC thành error AUROC. |
| Title/estimand Seminar | **Thay thế trong phạm vi này** title/framing benchmark prospective bằng đánh giá hồi cứu TRAIN đã phơi nhiễm và S-RQ tích hợp trên; không gọi saved HNLO runs là benchmark D9R22 production. |
| Moondream2 | **Bổ sung ngoại lệ báo cáo cấp dự án** A4; không xóa nghĩa vụ roster hoặc thay yêu cầu bên ngoài. |
| DEC-PA3-011 và hướng A/C | **Chấp thuận các phần HNLO được liệt kê** của hướng tích hợp PR #133; không phê duyệt toàn bộ đề xuất DEC-PA3-011 hoặc các dự án A/C độc lập. Log cũ giữ PROPOSED như lịch sử. |
| Grounding/training/threshold/rights | **Kế thừa giới hạn**: grounding ngoài Seminar chính, không inference mới cho RQ3, không fine-tune, không tuning threshold trên TRAIN/TEST; quyền cấp theo task/run riêng. |

Ý chí Owner có từ nguồn ngày 26/10; **hiệu lực successor trên repository chỉ
bắt đầu sau khi hồ sơ này được kiểm chứng và merge**, không hồi tố cho run cũ.
Trong Draft, D9R22 vẫn là phạm vi đang có hiệu lực. Sau merge, mục này chỉ thay
những phần đã liệt kê; các phần D9R22 khác giữ nguyên. Merge không tự freeze M2.

### Những phần còn chặn và cách đóng M2

[SEMINAR_PROTOCOL v1](SEMINAR_PROTOCOL.md) và
[config v1](seminar_analysis_config.v1.json) là **hợp đồng mới soạn,
DOCUMENTATION_DONE / SCIENTIFIC_REVIEW_PENDING**. Chưa có review độc lập hoặc
phê duyệt đúng nội dung/version; không có quyết định M2 APPROVED trong log này.
Reviewer phải kiểm metric/denominator/eligibility, hợp đồng run, các N/A cụ thể
B01–B06 và Owner ghi quyết định append-only tiếp theo, liên kết hash protocol
và config đã review. Không cần task/PR khảo sát hay soạn kế hoạch lại.

Quyền học vụ, quyền dữ liệu/tài nguyên và phê duyệt M2 tách biệt. Thiếu một quyền
không tự phủ định A1–A8 trong thẩm quyền Owner, cũng không được gán quyền đó
APPROVED để khép milestone. **M3-01 chỉ bắt đầu sau M1 có hiệu lực, M2 khoa học
PASS và giao task triển khai CPU riêng**; task hiện tại dừng ở một Draft PR.
