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

## DEC-20261031-CANDIDATE160-RECOVERY

Owner trực tiếp yêu cầu bỏ One-Shot/No-Retry cho hai notebook Candidate160
InternVL3.5/MiniCPM-V-4; có thể retry/resume sau lỗi/load/ngắt Kaggle và khôi
phục từ Outputs mà không approval thủ công từng lần trong phạm vi đã giao.
[Quyết định vận hành đầy đủ](CANDIDATE160_RECOVERY_DECISION_20261031.md) ghi
attempt/series/lineage bất biến, migration trạng thái cũ, bounded calls/khóa
tiến trình và giới hạn cross-VM. Bổ sung append-only; không sửa quyết định cũ.

Giữ160 TRAIN/order/revisions/checkpoint/source hashes/C1/HNLO/metric/nhãn/
protocol/raw-before-parse/quyền dữ liệu. **Scientific result selection PENDING;
không pooling hoặc chọn kết quả thuận lợi.** Chỉ task CPU synthetic; một Draft
PR chờ ChatGPT kiểm GitHub và Antigravity audit độc lập trước merge. Không GPU,
attempt thực nghiệm, tự phê duyệt khoa học hoặc merge.

## DEC-20261031-KAGGLE-TECHNICAL-VERIFICATION

[Owner directive PR156](https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6539523161)
và task trực tiếp cùng ngày yêu cầu Codex kiểm mọi notebook Kaggle trên Kaggle
thật trước bàn giao, có bounded inference trên đúng TRAIN/Input/model/config
đã được phép. Quy tắc này được ghi append-only trong AGENTS; mở rộng task CPU
cũ sang kiểm kỹ thuật thật trong phạm vi Owner, không duyệt khoa học/học vụ,
TEST/bên thứ ba hoặc quyền merge. Owner vẫn chạy full experiment sau review.

Candidate160 thêm technical_smoke riêng: manifest160 nguyên bytes/order,
ordinal0,1 call,1 load,3600 giây/setup; không production reservation/history,
retry loop, scientific metrics hoặc pooling. Dùng cùng supervisor/worker,
source/checkpoint/C1/precision/parser/HNLO và admission. Giữ evidence FAIL/PASS,
receipt/hash của source/notebook cuối; chưa có actual weights/inference/export
đạt thì BLOCKED/NOT VERIFIED. [Hồ sơ](CANDIDATE160_KAGGLE_VERIFICATION_20261031.md).
Scientific result selection vẫn PENDING; không thay quyết định recovery trước.

## FINDING-20261031-MINICPM-FP16-NUMERICS — BLOCKED / proposed change PENDING

Real Kaggle smoke và hai bounded diagnostics trên đúng ảnh0/model/checkpoint/
FP16/eager đã khóa xác nhận weights/Q/K/V hữu hạn, mask không fully masked;
native resampler FP16 baddbmm sinh60.522 +Inf, softmax sinh569.800 NaN. Không
OOM, không lỗi archive/Path. Các ZIP/raw/log/hash được giữ; xem
[hồ sơ bằng chứng](CANDIDATE160_KAGGLE_VERIFICATION_20261031.md).

[Đề xuất numerical policy riêng cho attention](MINICPM4_NUMERICS_PENDING_DECISION_20261031.md)
là **PENDING, chưa áp dụng/chưa được phê duyệt**. Task Owner mục9 khóa precision/
source; bounded smoke authority không tự là ngoại lệ thay các trường đó. Không
upcast, đổi source lock, đổi precision/model/ảnh/prompt/parser hoặc tắt validation
để vượt lỗi. Cần quyết định Owner cụ thể trước triển khai exception/effective
implementation mới; teacher/third-party authority và quyền merge vẫn riêng.
Không thay scientific result selection=PENDING, không pooling hoặc chạy full160.

## DEC-20261031-OWNER-HOLD-MINICPM-NUMERICS

Owner trực tiếp chọn **phương án1: giữ BLOCKED** sau
[đánh giá sơ bộ GitHub của ChatGPT](https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6540368755)
tại HEAD `51f6eec3be1e1c3eb6a69346e9bd1571be7c87d1`. Chưa cho phép thay đổi
precision/effective source; ngoại lệ FP32 trong resampler vẫn **PENDING,
NOT AUTHORIZED, NOT APPLIED**. Không coi đánh giá này là final review PASS,
Antigravity audit, phê duyệt khoa học hoặc quyền merge.

Giữ nguyên Draft PR156, toàn bộ bằng chứng Kaggle và lỗi FP16. Không merge,
không chạy lại cấu hình MiniCPM chưa sửa, không chạy160 ảnh chính thức. Chỉ
tiếp tục triển khai/kiểm số học khi có quyết định Owner riêng về phạm vi thay
đổi, trong đúng session Codex/branch/PR156. Giữ scientific selection=PENDING,
pooling_allowed=false và toàn bộ model/checkpoint/source/precision locks.
Đây là xác nhận HOLD, không phê duyệt hoặc phủ nhận hồi tố đề xuất số học.

## DEC-20261031-MINICPM-RESAMPLER-FP32-TECHNICAL-EXCEPTION

Owner trực tiếp cho phép **triển khai và thử kỹ thuật ngoại lệ số học hẹp**
trong cùng session/branch/Draft PR156, sau HOLD tại HEAD25d3ec8. Phạm vi duy
nhất: MiniCPM resampler attention score, softmax và phép nhân với value dùng
FP32, kết quả về dtype gốc trước output projection. Weights giữ FP16; model/
checkpoint/revision/source lock gốc, TRAIN160/order, C1, eager, parser, HNLO và
mọi quyết định khoa học giữ nguyên. Không áp dụng precision toàn mô hình.

Khai báo effective implementation/configuration/ID/hash mới; giữ nguyên tất
cả evidence FP16 FAIL. Kiểm regression số học/finite/load/history/isolation,
rồi Codex tự chạy technical smoke trên Kaggle thật, trước tiên đúng ảnh0 của
TRAIN160,1 call có giới hạn. Phiên bản thử kỹ thuật riêng không resume/pool
với FP16 cũ hoặc production; chưa cấp quyền chạy160 ảnh/full experiment/TEST.

Quyền này chỉ là **AUTHORIZED_FOR_BOUNDED_TECHNICAL_TRIAL**, không phê duyệt
baseline/phương pháp khoa học, result selection, audit PASS hoặc merge. Smoke
chưa PASS phải BLOCKED; nếu PASS giữ Draft để ChatGPT review GitHub rồi quyết
định Antigravity audit độc lập. Ngoại lệ hẹp này thay HOLD chỉ trong phạm vi
trên; mọi thay đổi rộng hơn vẫn chưa được cấp quyền. Không sửa quyết định cũ.

## RESULT-20261031-MINICPM-RESAMPLER-FP32-TECHNICAL

Trial được phép ở trên đã **TECHNICAL_SMOKE_PASS** trên Kaggle thật với đúng
notebook/runtime/effective config được khóa:1 ảnh0 TRAIN160 gốc/1 load/1 call,
weights FP16, resampler score/softmax/value FP32, output về FP16;11/11 raw
logit steps hữu hạn, parser SUCCESS, raw/custody/ZIP/SHA256/cleanup PASS.
[Báo cáo/receipts](MINICPM4_FP32_ATTENTION_TECHNICAL_20261031.md) giữ đủ hashes
và evidence FP16 FAIL cũ nguyên trạng. HNLO unaligned, numeric HNLO chưa chứng
minh. Đây là kết quả kỹ thuật, không APPROVED baseline/model quality/science.

Giữ **Draft PR156 / READY FOR REVIEW trial kỹ thuật** để ChatGPT kiểm exact
GitHub HEAD rồi quyết định audit Antigravity độc lập. Scientific result selection
vẫn PENDING/pooling=false; không official160/TEST/merge hoặc đổi locks ngoài
ngoại lệ. Không suy PASS của1 ảnh sang toàn cohort, runtime dài hoặc các model/
notebook chưa được kiểm lại sau đổi embedded source. Owner chưa cấp quyền
production cho numerical policy này qua quyết định technical trial.

## DEC-20261031-CANDIDATE160-PRODUCTION-ENGINEERING

Nguồn: [Owner follow-up directive](https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6540904325)
và task trực tiếp trong session mới. Cho phép hoàn thiện và tự kiểm kỹ thuật
hai đường production dự kiến bàn giao, cùng branch/Draft PR156. Chuẩn bị
đường MiniCPM FP32 với effective ID/config/source/hash và history riêng;
**không phê duyệt baseline khoa học hoặc activation official160 FP32**.
Scientific result selection vẫn PENDING, pooling=false; TEST vẫn đóng.

Profile vận hành riêng `train160-production-engineering-v1` dùng đúng manifest
TRAIN160, không đổi order/nhãn/split/C1/parser/HNLO/model/checkpoint. Ba ordinal
được chốt trước inference mới theo metadata kích thước đã xác minh:0 (đầu),
15 (diện tích nhỏ nhất, tie ordinal đầu),111 (height/width lớn nhất, tie đầu).
Không dùng prediction/GT để chọn. Đây là bounded engineering scope, không
cohort nghiên cứu mới.1 load/≤3 native calls/3600 giây mỗi attempt; không retry
nội bộ. Dùng cùng production supervisor/worker/controller/raw/history/export.
Resume/rerun kỹ thuật chỉ trong scope này, không trở thành lịch sử official.
Sau PASS, import sealed ZIP vào workspace mới để kiểm resume zero-load/zero-call.

InternVL fence/INVALID và MiniCPM alternative native token segmentation phải
được giữ đúng parser/continuation contract hiện hành. Không tạo numeric HNLO
bằng thay token, decode gần đúng hoặc đổi surfaces. Không hồi tố sửa raw hoặc
receipts cũ. Trước Owner full run: final-source Kaggle evidence, fresh ChatGPT
exact-HEAD review, Antigravity audit độc lập và merge được cấp quyền riêng.
Quyết định khoa học còn thiếu: Owner/Lead chấp thuận hay từ chối
`minicpm4-resampler-attention-fp32-v1` làm effective baseline cho official
TRAIN160, cùng identity/config đã kiểm; selection/pooling vẫn cần quyết định
riêng trước phân tích khoa học. Không thể mở gate bằng notebook flag/approval giả.

## RESULT-20261031-CANDIDATE160-PRODUCTION-ENGINEERING

Hai notebook PRODUCTION cuối đã được Codex tự kiểm trên Kaggle private với
đúng source `09d94fd27a6a5260526c981a55854e8217536e0499824400ea9df5d213fb2d08`,
3 ordinal đã chốt0/15/111 mỗi model,1 load/3 native calls; finite logits/raw/
native tokenizer/parser/HNLO handling/cleanup/ZIP/SHA PASS. Resume sealed ZIP
vào workspace mới thực sự0 loads/0 calls, giữ INVALID là durable completion.
[Báo cáo và receipts](CANDIDATE160_PRODUCTION_ENGINEERING_20261031.md).

InternVL có38/38 finite steps, INVALID/SUCCESS/INVALID; case15 HNLO thực
7.301041903017601 với native branch/Decimal oracle khớp. Hai INVALID do code
fence thật, không sửa parser. MiniCPM33/33 finite steps,3 SUCCESS, HNLO vẫn
unaligned do alternative native segmentation ngoài continuations đã prove.
Không đổi arithmetic implementation đã PASS, checkpoint/TRAIN160/C1/parser/
HNLO/metric; không chọn theo output hoặc nâng trạng thái khoa học.

**READY_FOR_TECHNICAL_REVIEW**, không READY_FOR_OWNER. Official MiniCPM FP32
vẫn BLOCKED_PENDING_SCIENTIFIC_DECISION; decision adoption baseline còn thiếu.
Giữ Draft PR156, fresh ChatGPT review và Antigravity audit độc lập trước merge.
Không full160/TEST, không coi3 ảnh là kiểm đủ12 giờ/all160 hoặc global lock.

## DEC-20261031-OWNER-MINICPM-FP32-OFFICIAL-TRAIN160

Source: [Owner decision relay](https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6544285481),
read directly through GitHub REST in this task, plus the Owner's current task.
The relay explicitly transcribes the Owner; it is not an independent Research
Lead, faculty or auditor signature. Status: **OWNER_ADOPTED_FOR_PROJECT_TRAIN160**;
activation requires a separately reviewed, independently audited, authorized
merge and live postmerge verification. No official execution before that sequence.

The Owner adopts `minicpm4-resampler-attention-fp32-v1` for the original official
160-image TRAIN campaign. Effective configuration SHA256:
`5b85504ff24ff42d4d629dbf00feb0c484022cfef3a7d57b571eaae99d1c8b00`;
numerical descriptor SHA256:
`2fe992725df4340f910934b5846278e34968196a9dff3fc4171fb4279bfaf5da`.
FP16 weights/eager remain; only resampler scores, softmax and value product
compute FP32, with native dtype restored before output projection. Keep original
model/revision/checkpoint/public-source/manifest/order/C1/generation/parser/HNLO/
labels/metrics unchanged. Preserve INVALID and unaligned HNLO as observed.

Trusted source policy `safeshift/candidates/train_official.py` binds only these
identities and the original TRAIN160 manifest. Supervisor checks actual hashes
before Inputs; direct workers check the immutable expected Owner adoption record
and complete execution scope before software/data/GPU/load. Notebook metadata is
informational, not approval. The frozen numerical descriptor's original technical
scope/authority text remains historical bytes; the new policy supplies official
project adoption separately, without relabeling old evidence or changing its hash.
Source identity changes and must be recorded and requalified on final bytes.

One new Draft PR contains activation, tests, deterministic notebooks, documents
and small sanitized receipts. Codex performs bounded final-source technical
Kaggle verification separately; stop for ChatGPT's direct GitHub review and an
independent Antigravity audit. The audit waiver for PR156 does not apply here.
Do not assert an audit, merge or academic approval that has not happened.

After ChatGPT verifies the authorized merge, the Owner authorizes Codex in this
same task/session to operate Kaggle `resume`, attach original private bundle,
checkpoint and verified official historical Outputs, and finish pending TRAIN160
within160 native calls/43200 seconds per attempt. Serialize jobs, verify history
before resume; never erase markers or automatically retry unexplained failures.
Keep technical/FP16 histories separate from official FP32 completion and preserve
all raw/errors/ZIPs/sidecars/lineage privately under `data/processed/`.

This decision supersedes the earlier FP32 adoption BLOCKED status and personal
Owner operator requirement only within this exact original TRAIN160 campaign.
Scientific selection/pooling remains **PENDING**; TEST, new protocols/metrics/
roster, thesis D/V/T, Accuracy/Macro-F1 analysis and model choice are outside scope.
No external academic acceptance is claimed. If independent authority outside the
Owner is established as required, report BLOCKED with that requirement's source.


## DEC-20261101-T1-OWNER-FALSE-SAFE-DIRECTION

- Ngày: **01/11/2026, Asia/Bangkok**. Người quyết định: **SafeShift Owner**;
  Codex chỉ ghi lại. Nguồn: [Owner relay do ChatGPT chuyển lên GitHub](https://github.com/tantdna2/SafeShift/pull/158#issuecomment-6552710543)
  và task T1 trực tiếp của Owner cùng ngày. Đã đọc comment thật trên GitHub.
- BASE/main đã xác minh: `a113ef707970c50a7420c84e8a8e46fa2dc3db01`;
  PR158 MERGED. Merge T0 là hoàn tất hồ sơ đề xuất, không tự phê duyệt khoa học.
- Trạng thái: **OWNER_DIRECTION_ACCEPTED / T1_AUTHORIZED**. Ý chí Owner có
  hiệu lực theo nguồn nêu trên; hồ sơ này chờ review/merge vào repository.
  Không ghi chữ ký độc lập của Research Lead, giảng viên, chủ dữ liệu/custodian.

Owner chấp nhận hướng Khóa luận **phát hiện quyết định false-safe và ưu tiên
người kiểm tra lại**; Qwen3-VL-8B-Instruct là ứng viên focal có điều kiện,
InternVL3.5-4B-HF và MiniCPM-V-4 đúng resampler FP32 là hai ứng viên kiểm tra
chéo, tối đa ba mô hình; **tạm dừng tìm mô hình thứ tư**. MiniCPM giữ identity
`minicpm4-resampler-attention-fp32-v1`, config SHA256
`5b85504ff24ff42d4d629dbf00feb0c484022cfef3a7d57b571eaae99d1c8b00`,
descriptor SHA256 `2fe992725df4340f910934b5846278e34968196a9dff3fc4171fb4279bfaf5da`;
weights FP16/eager, không đổi thành toàn model FP32. Exact revisions và các
điều kiện qualification trong [T0 §4](T0_FALSE_SAFE_DESIGN_20261101.md) giữ nguyên.

Phương pháp phải có **baseline, ablation, stress test, phân tích lỗi và khả
năng tái lập (E1–E5)**. Đây là yêu cầu thiết kế được Owner nêu, không phê duyệt
công thức/rule cụ thể hoặc chứng nhận đã thực hiện E1–E5. Final model qualification,
role utility/cost và final roster vẫn PENDING; không bắt buộc giữ đủ ba bằng
mọi giá hoặc dùng HNLO không tồn tại của MiniCPM.

Quyết định bổ sung phạm vi hướng/candidate cap cho Khóa luận và dừng tuyển
model thứ tư trong kế hoạch bốn-peer PROPOSED. Không hồi tố M1/M2, roster
Seminar lịch sử, T0, dataset/split/nhãn/metric/config đã khóa. Không đóng toàn
bộ O1/O3: O1 còn chuẩn học vụ/negative route theo scope cụ thể; O3 còn final
roster/qualification/selection. **O2/O4/O5 PENDING**, gồm protocol/series policy,
nguồn/quyền/GT/D/V/T/custody, budget/gain/severe margin/coverage/CI/precision/
min sources-events/cost/stop rules. 20%/10 điểm phần trăm/95%/80% không là số
được duyệt. O6 run authority và O7 reviewer/study giữ riêng, chưa mở bởi T1.

Owner cho **T1 kiểm tài liệu, metadata TRAIN và feasibility**, ghi checklist
người có quyền cần bổ sung, một Draft PR và PROJECT_STATE. Không acquisition,
annotation, liên hệ bên thứ ba, Kaggle/GPU/inference, TEST, huấn luyện/ranker,
triage implementation, pooling hoặc chạy dữ liệu xác nhận. [Hồ sơ T1](THESIS_DATA_PROTOCOL.md)
đánh giá GO/BLOCKED/NO-GO; hoàn tất T1 không đồng nghĩa xác nhận cải tiến GO.
Dừng tại Draft PR; ChatGPT review GitHub và quyết định audit; không merge.

## DEC-20261101-T4-OWNER-O2-DOSSIER-AUTHORIZATION

Ngày01/11/2026, Asia/Bangkok. Nguồn: [Owner START T4 tại PR161](https://github.com/tantdna2/SafeShift/pull/161#issuecomment-6554558701),
đọc trực tiếp GitHub REST trong T4, và task Owner trực tiếp. BASE/main đã
kiểm `f10bac7dea054c8e199a807dadd768517579e164`. **T4_AUTHORIZED;
O2_SCIENTIFIC_SELECTION=PENDING**. Đây là chỉ thị lập hồ sơ sau T3 merge,
không chữ ký phê duyệt chính sách selection hoặc quyền phân tích predictions.

Owner cho một hồ sơ quyết định có ma trận ba model, exact source/run/series/
attempt, một quy tắc đề nghị, ledger và GO/BLOCKED/NO-GO; được kiểm receipts/
metadata TRAIN đã có trong quyền T1. [T4-O2-SELECTION-v1](T4_O2_SELECTION_DOSSIER_20261101.md)
là **PROPOSED**, kể cả đề nghị dùng riêng official InternVL RECOVERY. Không
chuyển quyền retry/resume hoặc MiniCPM FP32 adoption thành selection approval.

Không đọc ảnh/TEST/raw archives/per-image saved predictions, không Kaggle/GPU/
inference/training/ranker hoặc phân tích hiệu quả mới; không sửa T2/T3 khi
không cần. O2 phần còn lại, O3 final roster, O4/O5, quyền dữ liệu/học vụ vẫn
riêng. Không đặt thresholds hoặc giả authority ID. Cập nhật PROJECT_STATE
cùng đúng một Draft PR, dừng để ChatGPT kiểm GitHub, không merge/Antigravity.

## DEC-20261102-OWNER-THESIS-FULLTRAIN-REPAIR

**Ngày:** 02/11/2026, Asia/Ho_Chi_Minh. **Người quyết định:** Owner trong phạm vi dự án, nguồn [Issue #167](https://github.com/tantdna2/SafeShift/issues/167); main lúc ghi `0295172783dcf82426923d1af621dde9db8ed42c`. **Trạng thái:** `OWNER_SCOPE_DIRECTION_RECORDED; IMPLEMENTATION_PENDING`. Không là phê duyệt học vụ/O2–O6 hoặc quyền chạy.

**Đích phân tích TRAIN:** mọi mô hình được lựa chọn chính thức phải dùng chung **3.763 ảnh InspecSafe TRAIN** với cùng ID/manifest và 3.763 trạng thái đầy đủ. Mục tiêu kỹ thuật: cố gắng đạt **3.763 nhãn Level01–04 hợp lệ/model**; không dùng pilot160 như kết quả full TRAIN; không bảo đảm 100% SUCCESS nếu mô hình không thể được sửa hợp lệ. TRAIN đã phơi nhiễm chỉ cho phân tích development/thăm dò được phép; không thay thế V/T độc lập.

**Xử lý INVALID/lỗi/chưa chạy:** yêu cầu phân loại và sửa nguyên nhân (load/môi trường, GPU/OOM, timeout, pipeline, tokenizer/parser, định dạng sinh, hành vi mô hình); kiểm thử trước và sau sửa, lập kế hoạch chạy lại có kiểm soát cho đúng ảnh còn lỗi/chưa chạy sau quyền O6. Không gán nhãn bằng ground truth, không biến INVALID thành SUCCESS bằng suy đoán, không bỏ hoặc giấu trường hợp không sửa được; ghi NO-GO/blocked và xin quyết định scope khi cần. Quy tắc Candidate160 lịch sử coi INVALID có raw là durable vẫn đúng cho **resume cũ**; campaign sửa lỗi full TRAIN phải có cơ chế `repair` phân biệt với `resume`, không âm thầm đổi cách chọn kết quả.

**Hiện trạng kế thừa, không tự trộn:** Qwen3 V4 ORIGINAL: `3763=3539 SUCCESS+1 TECHNICAL_ERROR+223 NOT_ATTEMPTED`; InternVL3.5 TRAIN160: `135 SUCCESS+25 INVALID`, `3603` ngoài pilot; MiniCPM-V-4 FP32 TRAIN160: `155 SUCCESS+5 INVALID`, `3603` ngoài pilot, **label-only**, HNLO Method A 0/155. Mọi source/revision/config/raw/series/attempt gốc giữ nguyên. Không tự gộp Qwen Recovery224/composite, InternVL RECOVERY với lịch sử khác, MiniCPM smoke/rerun. Nếu sửa prompt/parser/model/generation ảnh hưởng semantics, phải version và đánh giá comparability; có thể cần series mới toàn cohort, không backfill từ lần chạy khác.

**Roster và khoa học:** ba mô hình trên là ứng viên, chưa là final O3; quyết định Owner ngày 01/11 tạm dừng tuyển model thứ tư còn hiệu lực. Không đổi dữ liệu/split/nhãn/metric/protocol/HNLO đã khóa hoặc tự duyệt bốn peers, H1/quorum/O2/O5. Thiếu phê duyệt thì ghi PENDING, không giả quyết định của Research Lead/giảng viên/data custodian.

**Thực hiện:** tài liệu quyết định được ghi **trước code** trong một branch; Codex tiếp tục cùng branch với CPU synthetic full-TRAIN readiness/repair/resume, notebook/preflight G0–G6, tests/runbook và PROJECT_STATE; tạo **duy nhất một Draft PR** rồi dừng. ChatGPT review GitHub thật; vì có đường thay đổi inference/selection phải xét audit Antigravity độc lập. **Không cấp** quyền Kaggle/GPU/full-TRAIN inference, TEST, ảnh/raw/GT ngoài quyền hiện hành; cần approval O2 exact-series, O3 roster, O4 dữ liệu, O5 budget/stop, O6 grant từng run trước chạy thật.

## PROPOSAL-20261102-ISSUE169-FULLTRAIN-SOURCE-REPAIR

Ngày **02/11/2026, Asia/Bangkok**. Nguồn giao việc:
[Issue #169](https://github.com/tantdna2/SafeShift/issues/169) và task Owner
trực tiếp, sau [hậu merge PR168](https://github.com/tantdna2/SafeShift/pull/168#issuecomment-6570735120).
BASE `afc932b2a43cf829db12f53d6ac3d578c6123eec`, đã đối chiếu GitHub.
**DOCUMENTATION_AUTHORIZED; PROPOSED_FOR_OWNER_REVIEW; O2–O6=PENDING/BLOCKED**.
Đây là bản ghi đề xuất của Codex, không phải Owner đã duyệt selection.
Signer/approval ref/time cho đề xuất hiện chưa có; không ký thay bất kỳ ai.

[T4 successor v2](T4_O2_SELECTION_DOSSIER_20261101.md#issue169-successor-full-train)
tận dụng nguồn T4-v1, đề nghị exact bốn Qwen V4 ORIGINAL, InternVL3.5 official
RECOVERY, MiniCPM official FP32 INITIAL label-only; kế thừa có điều kiện trên
cùng3.763 TRAIN IDs, tách resume/repair/rerun và giữ original/attempt/series.
Qwen legacy thiếu field phải có representation được duyệt; không bịa series
hoặc config hash. Không ghép Recovery224/composite/smoke hoặc chọn metric đẹp.
Thay identity/semantics cần version/series/comparability và quyền riêng.

Hướng false-safe/full TRAIN, ba ứng viên tối đa và dừng tuyển thứ tư kế thừa
quyết định Owner01/11–02/11. [Owner label-only](https://github.com/tantdna2/SafeShift/pull/166#issuecomment-6567502211)
giữ MiniCPM HNLO0/155; không mở lại tìm điểm. Ma trận O1–O6 và L1–L4/B1–B6
trong dossier chỉ rõ quyền dự án khác học vụ/quyền bên thứ ba, thiếu seal và
approval khác metadata PASS. Không chốt phương pháp, roster, thresholds hoặc
freeze M1/M2 từ Issue169. TRAIN H/D không là xác nhận V/T độc lập.

[Receipt](evidence/issue169_source_checks.md) chỉ kiểm tracked metadata và
docs; không private raw/GT/TEST, Kaggle/GPU/inference, quyền mới hoặc metrics
thật. Dừng ở một Draft PR; ChatGPT review, quyết định audit độc lập Antigravity
và merge được cấp riêng. Native integration/history bridge/preflight phải
được giao task riêng sau decisions/chứng từ; hồ sơ này không mở task/run đó.


## DEC-20261102-OWNER-FRESH-FULLTRAIN-ONLY

Date: **02/11/2026, Asia/Bangkok**. Source: [Issue #171](https://github.com/tantdna2/SafeShift/issues/171)
and the direct Owner task. BASE `1acb3ef7c0deadbbde7da0b1c63b71296e3950e5`.
**OWNER_FRESH_FULLTRAIN_ONLY / OWNER_DIRECTION_ACCEPTED**: start over for
Qwen3-VL-8B-Instruct, InternVL3.5-4B-HF and MiniCPM-V-4 with the exact FP32
resampler, label-only. Each candidate starts a separate new series on the
same original 3,763 TRAIN IDs/order/image SHA: 11,289 planned initial calls,
before repair. This is neither an executed result nor a promise of all SUCCESS.

This supersedes prediction inheritance proposed in
T4-O2-FULLTRAIN-SELECTION-REPAIR-v2 for this fresh campaign only. Preserve the
proposal and all historical evidence. No SUCCESS/INVALID/prediction imports
from Qwen V4, Recovery224/composite, InternVL RECOVERY, MiniCPM INITIAL or
smoke runs. Historical prediction bridges are not needed for new initial;
new source/checkpoint/native path and cohort projection custody remain required.

Initial plans all 3,763/model, allowing bounded attempts under approved caps.
Resume schedules only NOT_ATTEMPTED within the explicitly selected new series
with unchanged identity. Repair targets only INVALID/TECHNICAL_ERROR with
outcome hash, cause evidence, fix/regression and specific authority/caps.
Semantic/configuration changes need another series and comparability review.
No completion union, backfill or favorable-output selection. Preserve strict
C1/parser/HNLO/labels/metrics, raw-before-parse and immutable attempts/history.
MiniCPM keeps FP16 weights/eager and only resampler attention FP32; historical
HNLO 0/155 remains label-only, without reopening the score investigation.

This is Owner project direction, not academic approval, final O3 roster,
O2 science/comparability, O4 rights/custody, O5 numerical caps or O6 per-run
grant. False-safe/E1-E5 and the pause on recruiting a fourth model remain.
One new branch, first commit documents only, then native preparation,
notebooks, CPU synthetic tests/receipts/runbook and PROJECT_STATE in one
Draft PR. No Kaggle/GPU/real model load/inference, private raw/GT/images or
TEST. Live G0-G6 remain BLOCKED/NOT_VERIFIED. Stop for direct ChatGPT review
and independent Antigravity audit; merging requires separate authorization.
## DEC-20261102-ISSUE173-BOUNDED-KAGGLE-VERIFICATION

Source: [Owner Issue #173](https://github.com/tantdna2/SafeShift/issues/173)
and direct task, 02/11/2026 (Asia/Bangkok). Base main:
`50d0c910319a6e93354a3d27887418aeb320709f`.
Owner authorizes live Kaggle environment observation and exact pinned public
software preparation. This supersedes Issue171's no-Kaggle task restriction
only for this technical verification; production `contract.authorize()` stays
closed. No dataset is attached/read until rights, cloud purpose, original TRAIN
membership/custody, checkpoint identity and resource gates are verified.

Conditional smoke ceiling is one TRAIN image per model, three native calls
total, with independent run/attempt identities outside all `fresh171-*` series.
Consumed calls cannot be retried without applicable authority and remaining
budget. No full TRAIN, TEST, GT rescue, scientific qualification or O2–O6 approval.
Keep Qwen pins/semantics, peers' strict C1 and MiniCPM FP32 resampler/label-only.
One branch and one Draft PR; ChatGPT review and independent Antigravity audit,
no merge. Actual measurements and blockers belong in `KAGGLE_PREFLIGHT_173.md`.

## PROPOSAL-20261104-INTERNVL-GRAMMAR-V2-LABEL-ONLY

Date:04/11/2026, Asia/Bangkok. Authority for the work: direct Owner task and
[PR175 post-merge handoff](https://github.com/tantdna2/SafeShift/pull/175#issuecomment-6620752693).
Base `5ff62212434034f29123e266377f041641c09302`.
**PROPOSED; SCIENTIFIC_ADOPTION_PENDING; NO_EXECUTION_AUTHORITY.**

Codex recommends **ĐỀ XUẤT ÁP DỤNG (chờ phê duyệt khoa học)**
`internvl35-canonical-json-grammar-v2` as a new **label-only** method with
`HNLO_NA_GRAMMAR_POLICY_V2`, never HNLO-equivalent. The
[dossier](INTERNVL_GRAMMAR_SCIENCE_V1.md) gives the fixed-prefix cancellation
proof, changed-prefix counterexample, tested four-label method and limitations.
This is Codex's proposal, not an Owner/Research Lead approval or a metric change.
Signer/approval reference remains absent. If comparable InternVL HNLO is a
required endpoint, reject this policy and retain official C1.

Any later activation requires the descriptor/implementation hashes, explicit
acceptance of HNLO N/A and heterogeneous three-system label comparison, and
new complete-cohort InternVL series on the same3763 original IDs. No mixing
grammar repairs with old successes, prediction inheritance or favorable-output
selection. Qwen's existing score eligibility and Mini's label-only decision
remain separate. O2–O6, academic and third-party authority remain unresolved.

Current work is CPU synthetic/native tokenizer software checks and reuse of
existing Kaggle receipts only. No real images/GT/private raw/TEST/weights/GPU
or new model calls. Frozen prompt/parser/HNLO and historical evidence remain
unchanged. One branch/one Draft PR, ChatGPT direct review, mandatory independent
audit for this proposed scientific/generation change, then scientific decision
and separately authorized merge. This entry does not supersede frozen science.

## DEC-20261104-OWNER-APPROVE-INTERNVL-GRAMMAR-V2-LABEL-ONLY

- **Ngày / nguồn:** 04/11/2026 (Asia/Ho_Chi_Minh); Owner dự án SafeShift
  tuyên bố phê duyệt trực tiếp trong hội thoại và ghi nhận bằng
  [PR #176 comment #6621440702](https://github.com/tantdna2/SafeShift/pull/176#issuecomment-6621440702).
- **Người quyết định:** SafeShift Owner/Research Lead trong phạm vi dự án;
  không mạo nhận phê duyệt học vụ, bên cung cấp dữ liệu hoặc bên thứ ba.
- **Trạng thái:** `OWNER_PROJECT_METHOD_APPROVED`; hiệu lực trong repository
  sau khi PR #176 được merge và ChatGPT xác minh hậu merge.
- **Phạm vi được phê duyệt:**
  1. `internvl35-canonical-json-grammar-v2` dùng cho InternVL3.5-4B-HF
     như **một phương pháp label-only có phiên bản riêng**; giữ C1 text và
     strict parser hiện có, chỉ chấp nhận bốn chuỗi JSON chuẩn và EOS;
     không gọi phương pháp mới tương đương generation chưa ràng buộc.
  2. `hnlo=null`, `hnlo_status=HNLO_NA_GRAMMAR_POLICY_V2` cho mọi kết quả
     grammar V2; không áp dụng phép so sánh HNLO giữa cả ba mô hình,
     không điền giả điểm và không thay bộ tính HNLO đã khóa.
  3. **Chấp nhận so sánh nhãn ở mức hệ thống dị thể** của Qwen3 (chính
     sách gốc), InternVL3.5 (grammar V2) và MiniCPM-V-4 (resampler FP32,
     label-only) trên cùng tập ID; phải báo rõ chính sách sinh, tỷ lệ
     đầu ra hợp lệ và mẫu số, không quy khác biệt cho riêng checkpoint.
  4. Khi có quyền thực thi riêng, InternVL grammar V2 phải khởi tạo một
     series mới cho **toàn bộ 3.763 TRAIN IDs gốc cùng order/source hashes**;
     ghi đầy đủ SUCCESS/INVALID/TECHNICAL_ERROR/NOT_ATTEMPTED; không ghép
     135 SUCCESS/25 INVALID lịch sử, không hồi tố sửa raw, không backfill
     từ smoke, recovery hay series khác; không sử dụng GT/TEST để cứu nhãn.
- **Mã/version đóng băng trong quyết định:** PR #176 reviewed/audited HEAD
  `fd2493c00b65c3a191f5627a29bbe5a0fb4fc94c`; implementation commit
  `cfeaadefcb31c2bb29b4e59d232aa2a3ef52d702`. Descriptor
  `configs/grammar/internvl35_v2.json` SHA256
  `f6e66ee753bc9c3447aa5b33d52838c226f428b87bafbd8a070bf95edce7e99e`;
  implementation `safeshift/internvl_grammar.py` SHA256
  `a3cde12d4dbe463acc9d87bcc36c440492636d7479024876c04ef1c1645c69ca`
  (theo receipt CPU đã đối chiếu). Bản ghi duyệt không sửa byte của hai tệp này.
- **Không cấp quyền:** Kaggle/GPU, nạp trọng số hay inference mô hình thật,
  fresh/full TRAIN 3.763, TEST, quyền dữ liệu ngoài Owner, O2–O6,
  phê duyệt học vụ, thay số liệu khoa học, activation chính thức trên
  production, hoặc merge bỏ qua kiểm soát. Grammar V2 mới được audit ở
  phạm vi đề xuất/CPU synthetic, chưa có đánh giá độ chính xác/false-safe thật.
- **Quy trình merge:** Phê duyệt khoa học **khác** quyền merge.
  Sau kiểm tra GitHub trên HEAD đã bổ sung quyết định, ChatGPT cấp quyền
  merge riêng cho Antigravity trong session audit PR #176; hậu merge
  ChatGPT xác minh main/parents/tree và cập nhật task handoff.

## DEC-20261104-INTERNVL-V2-CONTINUOUS-TECHNICAL-RETRY

- Authority: [Owner6626498951](https://github.com/tantdna2/SafeShift/pull/177#issuecomment-6626498951),
  authenticated body SHA256 `03407e1981f90a7b03f7ddcd0baacdec32b0f204d7a2afaf040bb17fae76240b`.
- New operational namespace `internvl-v2-6626498951` has sequential separately
  released attempts without a fixed total count. Historical j1/j2 namespace,
  failures, charges and immutable ledger remain unchanged. No old extra slot.
- New per-job1800s timeout,3600 conservative physical GPU-seconds reservation,
  actual provider quota, exclusive submission and terminal custody reconciliation.
  Optional user quota cap; one load/call per attempt, no ambiguous replay.
- Same-job positive preflight before original TRAIN ordinal0 image read/load is
  authorized. Exact checkpoint SHA256 remains mandatory; bounded read-only cache
  advice may repair file-cache pressure, unchanged16GiB floor decides admission.
- Audit PENDING_POST_RESULT; scientific qualification NOT_ESTABLISHED. Stop on
  verified real original-image native result, then ChatGPT/Antigravity review on
  existing Draft PR177. No merge, scientific method changes, TEST/full TRAIN,
  label rescue or pooling. [Detailed contract](INTERNVL_V2_CONTINUOUS_TECHNICAL_20261104.md).

Append-only encoding correction: the authoritative Owner6626498951 UTF-8 body
SHA256 is `60090d0a0073861906e09dfc7cf3d43f0845488005aafe6c4ba855a6889b025d`.
The03407e… hash above identifies a local ASCII-substituted PowerShell rendering,
not the actual GitHub text. Exact-authority authentication rejected unused
release6626931045 before any job/ledger reservation. No Owner scope changed.

## DEC-20261105-OWNER-INTERNVL3763-AGY-PREPARATION

Source: direct Owner task05/11/2026, Asia/Bangkok, after PR177 merged at
`7633dca168f7bb9fdff84f38a3d374cdbaff5b5a`. One new branch/Draft PR combines
InternVL3.5 grammar V2 full original TRAIN3763 preparation and Antigravity CLI
delegation. First commit documents the scope; then CPU synthetic implementation,
tests/notebook preparation and durable local CLI rehearsal. This is an
operational/preparation directive, not a new scientific-method adoption.

Codex owns code, tests, fixes and Draft PR. Antigravity CLI1.5.0 owns Kaggle
operations only under a separately granted exact execution scope: submit once,
observe at most15 minutes, persist RUNNING_UNVERIFIED/job/version/conversation
and exit without cancelling the job. The user's later completion message
triggers same-session or read-only recovery, live terminal confirmation,
private evidence download/integrity/contract checks and PASS/FAIL/BLOCKED report.
Codex consumes the bound report/evidence; operations do not replace independent
audit. Unknown submission/calls never allow an automatic retry or duplicate job.

The new series covers all original3763 IDs/order/image hashes with no historical
predictions or smoke backfill. Keep approved V2/strict C1/parser/FP16/eager/
checkpoint and HNLO null/N/A. Ordinary resume excludes consumed INVALID/errors;
repair/comparability, per-attempt caps, rights/custody and execution release stay
separate. No full TRAIN3763, TEST, real Kaggle job or new model call is authorized
by this task. No historical ref/source lock/decision is changed. Final-source
live gates remain NOT_RUN/BLOCKED. Stop at the unified Draft PR for direct
ChatGPT GitHub review, then independent audit and separately authorized merge.
