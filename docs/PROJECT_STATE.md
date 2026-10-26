# SafeShift — PROJECT STATE

Cập nhật: **26/10/2026 (Asia/Bangkok)**. Snapshot, không phải quyền thực nghiệm.
Main đã đối chiếu GitHub: `28fdf82512577f2ed0fb435fb2c12b88e82baf2f`.
Khi mở chat mới phải kiểm GitHub lại.

## PROJECT IDENTITY

- SafeShift — Đánh giá và cải thiện độ tin cậy của quyết định nguy cơ an toàn công nghiệp bằng VLM.
- Seminar hồi cứu nhãn sinh ra, HNLO, lỗi nguy hiểm và bất đồng trên TRAIN phơi nhiễm.
- Khóa luận: logistic có regularization, HNLO+bất đồng, predictor Q3 cố định; lợi ích chưa được chứng minh.
- HNLO không là xác suất nguy cơ đã hiệu chuẩn; TRAIN không là holdout.

## CURRENT STATUS

- **PR #135 MERGED**, commit `28fdf82512577f2ed0fb435fb2c12b88e82baf2f`, ngày 26/10/2026.
- [ChatGPT hậu merge PASS](https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6409830030) xác minh commit/parents/tree/hashes và giao M3-01.
- **M1 EFFECTIVE** trong phạm vi khoa học dự án; successor chỉ thay phần liệt kê ở [DECISIONS](research/DECISIONS.md).
- **M2 v1 EFFECTIVE / FROZEN BY SHA-BOUND DECISION DEC-20261026-M2**; giữ nguyên bytes protocol/config, kể cả `frozen=false`/PENDING/refs null lúc soạn.
- **M3-01 IN_PROGRESS / DRAFT**: reader, metrics, R1–R5, CLI và tests CPU synthetic trong một PR; chưa COMPLETE, chưa review/merge được xác minh.
- **M4 NOT_OPENED / NO_REAL_ARTIFACT_AUTHORITY**. Không đọc payload nghiên cứu thật, ảnh/nhãn/TEST hoặc chạy GPU/inference/raw replay.

## LAST VERIFIED COMPLETE

| Sản phẩm | Bằng chứng |
| --- | --- |
| Foundation V1 và saved-score CPU lịch sử | [ARCHITECTURE](ARCHITECTURE.md), [receipt #131](SOURCE_FEASIBILITY_RECEIPT_20261024.json) |
| Hướng và Master Plan | [#133](https://github.com/tantdna2/SafeShift/pull/133), merge `bffc6032e65b38cb04b33520275a089d87d0d37f` |
| Execution Plan | [#134](https://github.com/tantdna2/SafeShift/pull/134), merge `a425ab04695319a42bfdd2f89192717dddbb891b` |
| M1/M2 khoa học dự án | [#135](https://github.com/tantdna2/SafeShift/pull/135), merge và biên bản hậu merge ở trên |

## ACTIVE WORK

- Branch `implement/m3-01-seminar-cpu`, BASE bằng main đã xác minh ở đầu file.
- Đúng một Draft PR cho toàn M3; BASE/HEAD và validation cuối ở PR để tránh hash tự tham chiếu.
- [SEMINAR_ANALYSIS](SEMINAR_ANALYSIS.md): lệnh, schema, authority, exit codes, C01–C10 và giới hạn.
- [Authority receipt M3](research/m3_cpu_authority.v1.json) chỉ ghi nguồn grant đã kiểm, không tạo quyền mới.
- CLI sinh fixture viết tay, không nhận đường dẫn artifact thật; output ở `data/processed/seminar/` ignored.
- R5 luôn `PENDING_ANALYST_M4`. Số synthetic không dùng cho kết luận khoa học.

## KEY DECISIONS

- Bốn model: Qwen2.5-VL-3B-Instruct, Qwen3-VL-8B-Instruct, InternVL3-2B-hf, Moondream2.
- Moondream2 giữ roster, định lượng TRAIN N/A cấp dự án; ngoại lệ học vụ chưa xác minh.
- Q25/IVL3 full 3.763; common ba model đúng 3.539 SUCCESS Q3 V4 gốc. Q3 planned 3.763 gồm 1 lỗi/223 chưa chạy ngoài SUCCESS.
- Recovery224 riêng, reference-only; không lấy composite FN/score thay V4-only.
- INVALID, missing score, TECHNICAL_ERROR, NOT_ATTEMPTED khác nhau; không lấp bằng Normal.
- M2 authority + đúng hashes + hậu merge/task grant quyết định hiệu lực, không sửa config snapshot.
- H-T cần predictor/cohort/budget nhất quán, baseline Q3-HNLO-only và toàn chi phí model phụ; không mở triage trong M3.

## KNOWN BLOCKERS

- B01: 12 atoms/7 nhóm BLOCKED, đúng 19 placeholders; thiếu map vẫn chưa khắc phục.
- B02: continuous logit controls N/A; không claim HNLO vượt control chưa có hoặc đã loại confounding.
- B03: giới hạn saved-report/native attempt provenance; không raw PASS mới; recovery reference-only.
- B05: mismatch/proxy BLOCKED; giữ năm folder_domain D3, không suy nguồn thật/nhân quả.
- B04 khoa học đã duyệt đúng version; implementation M3 cần ChatGPT review/audit theo rủi ro và quyền merge riêng.
- B06: M3 chỉ CPU SYNTHETIC; M4 payload thật và GPU/inference/raw/TEST/ảnh/nhãn/Khóa luận chưa cấp.
- Chuẩn học vụ, nguồn độc lập, chuyên gia nhãn, target custodian, precision-events và tài nguyên M6/M7 chưa xác minh.

## NEXT TASK

**M4-01 — toàn bộ gói kết quả Seminar hồi cứu**, chỉ sau M3 merge được xác minh,
source/config/protocol khóa và có grant riêng cho từng artifact/hash/member.
Chưa mở M4, chưa có kết quả thật từ M3. Không cần khảo sát/lập kế hoạch mới.

## REFERENCES AND BOUNDARIES

- [Execution Plan](EXECUTION_PLAN.md), [protocol bất biến](research/SEMINAR_PROTOCOL.md), [config bất biến](research/seminar_analysis_config.v1.json).
- [AGENTS](../AGENTS.md), [README](../README.md), [ARCHITECTURE](ARCHITECTURE.md), [ROADMAP](ROADMAP.md), [HISTORY](HISTORY.md).
- Giữ dataset/split/nhãn/metric/roster và lịch sử; dữ liệu, raw, checkpoint và secrets ngoài Git.
- Không sửa/merge PR cũ hoặc legacy refs. Receipt/hash/path không là quyền đọc artifact.
- Mỗi task cập nhật file này trong cùng PR; tách sản phẩm, kiểm toán/merge và khoa học/thực nghiệm.
- Codex dừng ở một Draft PR; không tự merge, không mở task tiếp theo.
