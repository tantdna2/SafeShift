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
