# CT1 — Pilot Evidence-based Reasoning

Triển khai CPU và chuẩn bị notebook theo yêu cầu Owner. Xem [runbook native
Kaggle 48 ảnh](THESIS_CT1_NATIVE_RUNBOOK.md) cho phần triển khai nối tiếp.
Trạng thái chạy
native là **BLOCKED**. Gói audit 16 ảnh và annotation đã đối chiếu thuộc
development đã quan sát. Giữ nguyên các artifact và không dùng gói đó
làm dữ liệu xác nhận hoặc đưa vào cohort pilot này.

## Nhánh và contrast

| Arm | Prompt và đầu ra | Câu hỏi |
| --- | --- | --- |
| A | Đúng bytes C1 gốc, parser P2.1 của Qwen. Một trường mức. | Baseline ghép cặp. |
| E | Giữ toàn bộ tiêu chí C1. Yêu cầu ghi dấu hiệu và kiểm điều kiện trước khi quyết định. JSON bằng chứng và mức. | E−A đo hiệu ứng gộp của hướng bằng chứng. |
| S | Cùng tiêu chí, schema và parser với E. Yêu cầu chấm theo cách C1 thông thường trước rồi mới ghi dấu hiệu. | E−S kiểm khác biệt chỉ dẫn. S−A kiểm tác động của định dạng kèm yêu cầu ghi chép. |

E và S chỉ thay câu trả lời cuối của C1, giữ cùng vùng bằng chứng,
quy tắc và định dạng. Các đối chiếu không xác minh thứ tự suy luận nội tại.
Chốt độ dài prompt với tokenizer được ghim và `max_new_tokens` chung đủ
cho cả A/E/S trước freeze, kiểm truncation. Giữ cùng Qwen3-VL-8B-Instruct
revision `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`, ảnh, processor,
precision, map thiết bị và cấu hình decode. Chỉ dùng baseline đã lưu nếu
khớp toàn bộ điều kiện này. A/B/C precedence vẫn là thí nghiệm riêng.

## CPU và hợp đồng dữ liệu

Từ đúng checkout. Đặt TEMP/TMP/TMPDIR và output dưới D trên Windows.

```text
python -B -m unittest discover -s tests -p test_ct1_pilot.py -v
python -B -m scripts.build_ct1_evidence_notebooks --check
python -B -m scripts.ct1_pilot prepare --with-control --output data/processed/ct1-prep-v1
```

`prepare` xuất byte prompt, JSON Schema Draft 2020-12 và SHA-256 của các
file xuất. E/S nhận tối đa ba dấu hiệu, mỗi dấu hiệu có vùng thô, độ nhìn thấy,
điều kiện và trạng thái, nguồn quy tắc C1, tiêu chí và mức theo tiêu chí.
`NO_VISIBLE_HAZARD` yêu cầu mức 4 và mảng rỗng. `INSUFFICIENT` giữ riêng
trạng thái thiếu căn cứ trong khi vẫn xuất một trong bốn mức để so với A.
Parser dùng như nhau cho E/S. JSON thừa, khóa trùng, giá trị lạ và cấu trúc
không khớp là INVALID. Một khối mã đúng chuẩn theo cơ chế P2.1 vẫn được nhận
và đếm riêng. Parser kiểm hình thức, không tự xem ảnh hoặc xác nhận lời giải.

Các gói JSON được lưu riêng.

| Gói | Dữ liệu |
| --- | --- |
| Plan | `kind` là SYNTHETIC hoặc TRAIN_DEVELOPMENT, `arms` là [A,E] hoặc [A,E,S], `cases` là các cặp `case_id` dạng p- theo sau bởi 12 ký tự hex và `image_sha256`. ID phải phát ngẫu nhiên, không suy ra nhãn hay thư mục. |
| Exclusions | `exclusions` đọc bảng khóa 16 ca và biên nhận ảnh mù đã có, chỉ xuất 32 hash của ảnh gốc và bản mù. `validate-plan` kiểm tập loại trừ đúng seal và từ chối cùng byte. Người giữ dữ liệu phải kiểm riêng nguồn/cụm gần trùng và xác minh TRAIN. Hash tự nó không chứng minh split. |
| Runs | `plan_sha256`, `model_id`, `revision`, `runtime_sha256`, `prompt_sha256` theo arm, `records` mỗi cặp case/arm một dòng gồm `case_id`, `arm`, `attempt_status` và `raw_text`. RETURNED phải có raw, TECHNICAL_ERROR hoặc NOT_ATTEMPTED có raw null. Vắng record được tính NOT_ATTEMPTED. Gói phải xuất từ sổ lượt chạy đã niêm phong khi có release. CPU ghi SHA-256 để tái lập và không kiểm chữ ký grant. |
| Truth | `plan_sha256` và `cases` gồm đúng mỗi `case_id` planned một lần với `true_level`. Gói này ở môi trường chấm. Runner tương lai chỉ nhận ảnh qua ID mù, không mount GT, annotation, tên thư mục nhãn, mô tả TXT hoặc file map nguồn. |

Sau khi có raw đã niêm phong, dùng `scripts.ct1_pilot blind --plan ... --runs ...
--review-key ... --output ...`. Dùng `--exclusions` cho plan TRAIN.
`review-key` là tối thiểu 32 byte ngẫu nhiên, lưu ngoài bộ phiếu. Bộ phiếu
dùng token HMAC, mã ảnh mù, dấu hiệu và mã/mức quy tắc mà model viện dẫn.
Nó không chứa arm, mức cuối, GT hoặc locator gốc. Một dấu hiệu hay mã quy
tắc có thể gợi mức cuối, nên chốt chấm ảnh độc lập trước khi cho xem claim.

Hai reviewer đủ quyền chấm ảnh và ghi mức độc lập (null nếu không đủ căn cứ),
sau đó chấm từng claim theo cue/vị trí, điều kiện và quy tắc mức. Dùng
SUPPORTED, CONTRADICTED hoặc UNVERIFIABLE cho mỗi chiều và cho căn cứ toàn
ảnh. Căn cứ toàn ảnh xét cả dấu hiệu quan trọng bị bỏ sót và sự biện minh
cho `NO_VISIBLE_HAZARD`. Khi `INSUFFICIENT` và điều kiện quyết định chưa
kiểm được, giữ UNVERIFIABLE thay vì xem một mức đoán là có căn cứ. Ghi mã
reviewer, rubric, bất đồng và giờ chấm trong nhật ký riêng. Khóa hai phiếu rồi
phân xử ngoài chương trình. Xuất phiếu đã phân xử với `packet_sha256`,
`cases` gồm `review_id`, `basis`, `visual_level` và mảng `evidence`
theo đúng thứ tự claim, mỗi claim có `cue`, `condition`, `rule`
là verdict. Công cụ chấp nhận subset đã định trước và báo độ phủ. Gọi
`scripts.ct1_pilot score --plan ... --runs ... --truth ... --reviews ...
--review-key ... --output ...`. Xem `--help` của từng lệnh.

## Endpoint và cỡ pilot trình Owner

- Primary E−A là recall Level01 trên toàn support planned. Báo E−S nếu có S,
  số cặp chỉ một phía đúng để chuẩn bị khoảng tin cậy theo nhóm nguồn,
  Macro-F1 trên các lớp có support, FNR là Hazard→Normal, FPR là Normal→Hazard.
  Báo kèm Hazard không có mức hợp lệ và cận FNR nếu xem chúng là miss.
- Guardrail precision Level01, 02→01, 01→02, 01→04, tỷ lệ nâng nhầm trên
  mọi GT Level02–04, tỷ lệ hợp lệ và phân rã INVALID, TECHNICAL_ERROR,
  NOT_ATTEMPTED. Precision dùng trên số dự đoán mức 1. Kết quả riêng của
  02→01 có mẫu số GT Level02. Mẫu số bằng 0 trả null.
- Chất lượng bằng chứng báo verdict từng chiều, tỷ lệ claim hỗ trợ đủ,
  tỷ lệ căn cứ đủ trên cả planned và đã review, coverage, bất đồng với
  mức xem ảnh độc lập và ca đúng nhãn nhưng căn cứ mâu thuẫn hoặc chưa xác
  minh. A không sinh bằng chứng nên trường này là null. Chất lượng giải
  thích không tham gia tính metric nhãn và không ghi đè nhãn nào.

Đề xuất pilot development **48 ảnh khác audit**, minh họa 20 Level01,
12 Level02, 16 Normal, cân bằng miền/nguồn khi có support. Báo lớp nào vắng.
Có thể lập stress test Level03 riêng sau kiểm đủ nguồn và quyền. Con số 48
dùng để đo độ hợp lệ, support và chi phí, không đủ cơ sở gọi là cỡ xác nhận.
Nếu 48 đủ thuận lợi, dự toán một bước development 160 ảnh. Cỡ xác nhận chỉ
đặt sau khi có tỷ lệ đổi chiều paired, số cụm độc lập, biên hiệu ứng thực
dụng, sai số cho guardrail và nguồn validation có quyền. TEST vẫn đóng.

| Cấu hình | Lượt thực nếu một call/arm/ảnh | Thời gian job minh họa |
| --- | ---: | ---: |
| 48 ảnh A/E | 96 | 0,55–1,47 giờ |
| 48 ảnh A/E/S | 144 | 0,65–1,87 giờ |
| 160 ảnh A/E hoặc A/E/S | 320 hoặc 480 | 1,04–3,33 hoặc 1,40–4,67 giờ |

Dự toán dùng **một job 2×T4 16 GiB**, theo map FP16/SDPA của Qwen lịch
sử, không cộng hai VRAM như một thiết bị. Các thời gian giả định
8–30 giây/lượt nối tiếp cộng 20–40 phút tải/thiết lập/xuất. GPU-giờ tổng
bằng hai lần thời gian job nếu cả hai T4 được giữ suốt job. Chưa có số đo
cho output E/S. Với 48 × 2 người chấm × 3–5 phút, review một arm khoảng
4,8–8 giờ-người, hoặc 9,6–16 giờ-người nếu review E và S riêng, chưa
tính phân xử. Owner chốt số lượt, trần thời gian/VRAM và nguồn validation.

## Notebook và phạm vi phát hành

- [CPU preflight](../../notebooks/SafeShift_CT1_EVIDENCE_CPU_PREFLIGHT.ipynb)
  đọc metadata môi trường, kiểm C1 và ghi/đọc/fsync/xóa scratch 64 KiB.
- [Pilot prep](../../notebooks/SafeShift_CT1_EVIDENCE_PILOT_PREP.ipynb) chạy
  fixtures và tạo bundle prompt/schema. Cả hai có thể chạy local với
  `SAFESHIFT_CT1_REPO` và `SAFESHIFT_CT1_OUTPUT_ROOT`. Đổi output root
  hoặc dùng thư mục mới trước khi chạy lại.
- Trước phát hành notebook có native runner, cần đo môi trường đích và
  kiểm input/marker, pin runtime/source, checkpoint/weights, RAM/VRAM/disk,
  ABI/CUDA/FP16, exact-scope grant và thử native first-call/export có quyền
  theo [G0–G6](../KAGGLE_FAILURES_AND_RELEASE_GATES.md). Hai notebook trong
  gói này chuẩn bị CPU và chưa nối tới native runner. Gói không cài package,
  tải model, đọc TEST, chạy GPU hoặc gửi Kaggle. Dự toán chưa tính live
  smoke có quyền riêng.
- Đa tỉ lệ giữ làm ablation thị giác kế tiếp, không lấy polygon làm crop.
  Domain-aware chỉ thử khi có thông tin ngành hợp lệ, xác minh độc lập
  và thực sự sẵn ở thời điểm suy luận.