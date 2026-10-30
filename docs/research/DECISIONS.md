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

## DEC-20261026-M2

### Người quyết định, bằng chứng và trạng thái

- Người quyết định: **SafeShift Owner / Research Lead**, theo xác nhận Owner
  trong cuộc trò chuyện và [comment phê duyệt M2 v1](https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6408943462).
  Comment do ChatGPT chuyển phát biểu Owner vào GitHub `tantdna2`; không phải
  chữ ký/văn bản phê duyệt của giảng viên, nhà trường hoặc chủ dữ liệu bên ngoài.
- Ngày phê duyệt: **26/10/2026 (Asia/Bangkok)**; comment tạo lúc
  `2026-10-26T05:28:35Z` (12:28:35 giờ Bangkok).
- **Trạng thái: OWNER_APPROVED_FOR_PROJECT_SEMINAR** cho chính xác hai file
  dưới đây và các giới hạn đã chấp nhận; không thay metric/cohort/model/dữ liệu.
- B04: báo cáo kiểm toán độc lập Antigravity được ghi nhận **PASS /
  READY_FOR_OWNER_FREEZE** tại HEAD `6c78973f715c814735a51c871d2fac5de697b20b`;
  [ChatGPT đối chiếu độc lập PASS](https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6408340899)
  xác nhận đã đọc báo cáo, kiểm GitHub và tái tính hai hash. Comment phê duyệt
  Owner nêu trên xác nhận quyết định khoa học theo đúng version sau đối chiếu.
  Đây là bằng chứng kế thừa được dẫn nguồn, không phải Codex tự nhận đã thực
  hiện kiểm toán độc lập mới hoặc chứng minh implementation M3 đã tồn tại.
- PR #135 vẫn **OPEN / DRAFT**, chưa merge. Phê duyệt khoa học dự án đã có;
  **khóa khoa học có hiệu lực trên repository chỉ sau khi PR #135 được merge
  và ChatGPT xác minh hậu merge**. Chưa có merge authorization trong quyết định
  này, không đánh dấu M1/M2 COMPLETE hoặc bắt đầu M3 khi còn Draft.

### Hai nội dung bất biến được phê duyệt

| Nội dung | File | SHA-256 của chính bytes được duyệt |
| --- | --- | --- |
| Protocol v1 | [SEMINAR_PROTOCOL.md](SEMINAR_PROTOCOL.md) | `54c5be6b67e768f8d4819193c5d06867edf02e2008db258731f6e5947ed06dc1` |
| Config v1 | [seminar_analysis_config.v1.json](seminar_analysis_config.v1.json) | `dd3b86660f0795dba099abac0d8a3b8bd3498e625e49b128aa9c50e72639e5ff` |

Không sửa hai file, kể cả cờ `frozen=false`, `scientific_status` PENDING,
`approval_ref=null`, các acceptance refs null và trạng thái quyền lúc soạn.
Những giá trị này cùng lời chờ duyệt trong bản gốc là **snapshot trước phê
duyệt**; không được đọc riêng để phủ định quyết định mới, cũng không được sửa
chúng để tạo hash mới. Trạng thái approval/freeze có hiệu lực xác định bằng
**quyết định append-only này + hai hash + bằng chứng đủ điều kiện hiệu lực**.

Mục này bổ sung quyết định M1, hoàn tất phần review/phê duyệt M2 còn chờ trong
M1 và các snapshot tài liệu trước phê duyệt; không sửa hoặc hồi tố nội dung M1,
D9R22/DEC-PA3-011. Giới hạn còn thiếu bằng chứng không trở thành dữ liệu đã có.

### Các giới hạn Owner đã chấp nhận

| Thành phần | Quyết định và phạm vi kết luận được phép |
| --- | --- |
| B01 | Chấp nhận **BLOCKED** cho 12 hazard atoms và 7 nhóm: xuất **19 placeholders** có cờ trạng thái; không kết luận theo từng atom/nhóm. Giữ các panel miền, mức nhãn và lỗi đã đặc tả. Không coi thiếu map là đã khắc phục. |
| B02 | Chấp nhận **N/A** cho continuous logit controls (entropy/margin/probability từ logits). Không tuyên bố HNLO vượt đối chứng chưa có hoặc đã loại confounding; không thay bằng entropy vote/textual confidence. |
| B03 | Chấp nhận **UNVERIFIED_DETAIL** và giới hạn phân tích trên saved reports lịch sử đúng hash; không mạo nhận raw audit mới, native attempt provenance chưa biết hoặc runtime verification đầy đủ. Recovery vẫn reference-only, không ghép vào V4 gốc. |
| B05 | Chấp nhận **BLOCKED** cho mismatch/proxy mapping; vẫn phân tích theo năm `folder_domain` của D3. Không suy nhãn người/thiết bị, site/nguồn đã xác minh hoặc kết luận nhân quả từ metadata heuristic. |
| Moondream2 / A4 | Giữ model trong roster **bốn mô hình**; HNLO TRAIN định lượng **N/A ở cấp dự án Seminar**. Không là ngoại lệ học vụ đã xác minh và không cho phép bỏ model ở công việc tương lai. |
| B04 | **Đã đáp ứng review độc lập, ChatGPT đối chiếu PASS và Owner phê duyệt M2 v1 đúng hai hash**, theo các nguồn trên. HEAD bổ sung quyết định/trạng thái vẫn phải được ChatGPT kiểm tra trước quyền merge; hiệu lực khóa chờ merge và xác minh hậu merge. |
| B06 / M3 | Chỉ cấp **phạm vi có điều kiện cho task M3 kế tiếp: CPU + fixtures hoàn toàn SYNTHETIC**. Cần M1/M2 đã merge, ChatGPT xác minh hậu merge và ChatGPT chính thức giao M3. Hiện chưa triển khai M3. Không cấp quyền payload thật/M4, GPU, inference, raw replay, TEST, ảnh/annotation/nhãn, lấy dataset development/target, tài nguyên bên ngoài hoặc quyền mới cho các giai đoạn Khóa luận. |

### Hợp đồng kiểm hiệu lực bắt buộc cho M3

M3 phải kiểm trước khi chạy fixtures: quyết định này hiện diện trong source
M1/M2 đã merge được xác minh; có nguồn ChatGPT xác minh hậu merge gắn đúng
merge commit và giao task M3; bytes protocol/config đúng hai hash dưới đây,
đồng thời config `protocol.sha256` khớp protocol. **Thiếu quyết định có hiệu
lực, thiếu bằng chứng hậu merge/task grant, hoặc sai bất kỳ hash nào → từ chối
chạy**, không fallback sang cờ PENDING/frozen của snapshot hoặc tự cập nhật hash.
Receipt synthetic phải dẫn decision ID, merge/post-merge/task refs, source SHA
và hai content hashes. Đây là yêu cầu cho M3 triển khai/test sau khi được giao,
không phải code hoặc bằng chứng runtime enforcement trong task tài liệu này.

Khối dữ liệu dưới đây là phần của quyết định append-only để M3 đối chiếu;
`effective_when` là điều kiện phải kiểm, không phải tuyên bố chúng đã xảy ra:

```json
{
  "schema_version": "safeshift-m2-owner-decision-v1",
  "decision_id": "DEC-20261026-M2",
  "status": "OWNER_APPROVED_FOR_PROJECT_SEMINAR",
  "approved_by": "SafeShift Owner / Research Lead",
  "approval_ref": "https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6408943462",
  "audit_reconciliation_ref": "https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6408340899",
  "reviewed_scientific_head_sha": "6c78973f715c814735a51c871d2fac5de697b20b",
  "protocol": {
    "path": "docs/research/SEMINAR_PROTOCOL.md",
    "sha256": "54c5be6b67e768f8d4819193c5d06867edf02e2008db258731f6e5947ed06dc1"
  },
  "config": {
    "path": "docs/research/seminar_analysis_config.v1.json",
    "sha256": "dd3b86660f0795dba099abac0d8a3b8bd3498e625e49b128aa9c50e72639e5ff"
  },
  "effective_when": [
    "PR_135_MERGED_WITH_M1_M2_DECISIONS",
    "CHATGPT_POST_MERGE_VERIFICATION_FOR_EXACT_MERGE_COMMIT"
  ],
  "m3_scope": "CPU_SYNTHETIC_FIXTURES_ONLY",
  "m3_additional_condition": "CHATGPT_FORMALLY_ASSIGNS_M3_AFTER_EFFECTIVENESS",
  "m4_real_artifact_access_granted": false,
  "gpu_inference_raw_replay_test_image_label_external_resource_access_granted": false,
  "thesis_execution_granted": false,
  "merge_authorized_by_this_decision": false
}
```

Thay đổi hai file khoa học về sau cần quyết định version/hash mới, không chuyển
phê duyệt này sang bytes khác. **NEXT TASK sau xác minh hậu merge và giao việc:
M3-01 — triển khai trọn hệ thống phân tích Seminar CPU trên fixture SYNTHETIC**.
M4 cần quyền đọc artifact thật riêng; Khóa luận/học vụ vẫn có các gate riêng.
