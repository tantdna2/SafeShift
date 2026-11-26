# T3 — bộ kết nối kết quả tổng hợp có kiểm provenance

Phạm vi: [Owner START T3](https://github.com/tantdna2/SafeShift/pull/160#issuecomment-6553995227),
BASE `7026c6fe687bada36a824b36dc1997e7ff844ae7`. CPU/standard library,
chỉ fixture tổng hợp đã khóa trong source. Không inference, file reader,
archive parser, GT, lựa chọn khoa học hoặc quyền dùng báo cáo thật.

## Chạy

Từ repository root, Python 3.11+:

```console
python -B -m scripts.demo_triage_adapter_cpu --budget 2 --tie-seed public-demo
python -B -m scripts.demo_triage_adapter_cpu --case missing_model --budget 2 --tie-seed public-demo
python -B -m unittest discover -s tests -p "test_triage*.py" -v
python -B -m unittest discover -s tests -v
```

Full suite lịch sử cần checkout có Git history và thư mục scratch
`data/processed/` tồn tại (có thể rỗng). Bản `git archive` không đủ cho các
test notebook dùng `git show`; adapter/demo không cần hai điều kiện này.

CLI chỉ có `--case`, `--budget`, `--tie-seed`; không có đường dẫn đầu vào,
`--approved`, khóa cấp quyền hoặc production switch. K/seed phải tường minh;
seed demo công khai, không secret thật. Chín case: `complete`, `missing_row`,
`missing_model`, `invalid`, `technical_error`, `not_attempted`, `focal_invalid`,
`hnlo_missing`, `hnlo_ineligible`. CLI chỉ xuất JSON stdout, không ghi file.

```python
from scripts.demo_triage_adapter_cpu import synthetic_bundle
from safeshift.evaluation.triage_adapter import adapt_synthetic_bundle
from safeshift.evaluation.triage import build_review_queue

adapted = adapt_synthetic_bundle(synthetic_bundle("complete"))
queue = build_review_queue(
    adapted.planned_ids, adapted.focal, adapted.peers,
    mode="combined", budget=2, tie_key=b"public-demo",
)
```

`adapted.focal` và `adapted.peers` là `ModelResults`/`ClassifiedResult`/`HNLOSignal`
nguyên bản T2, không hệ thống prediction thứ hai. Adapter không sửa T2 hoặc
chọn mode/budget/key. `AdaptedInputs` và receipt `VerifiedSource` bất biến;
checksum/provenance giữ riêng, không làm feature xếp hạng. Mọi nguồn input
được snapshot bằng strict JSON; lỗi không sửa input hoặc ghi đè file.

## Hợp đồng fixture v1

`adapt_synthetic_bundle` chỉ nhận `dict` thuần trong bộ nhớ. Mọi object có
đúng trường được liệt kê; field thừa/thiếu, kiểu lạ và NaN/Infinity bị từ chối.
Không parse raw model output. `source_id` và identity là reference công khai
đã làm sạch, không đường dẫn/tên file chứa nhãn. Tất cả identity trong demo
là hư cấu với tiền tố `fixture-`/`synthetic-`, không giả revision/approval thật.

| Object | Trường và kiểm tra |
| --- | --- |
| Bundle | `manifest`, `inputs`, `reports`, `selection`, `evidence`. |
| Manifest | `schema=safeshift-t3-synthetic-v1`, `planned_ids`, `samples`, `sources`. IDs opaque 32 hex thường cấp trước nhãn; unique, không suy từ filename/domain/GT. |
| Sample | `sample_id`, `input_sha256`. Exact join planned; manifest không nhúng nội dung mẫu. |
| Input fixture | `sample_id`, `content`: đoạn text viết tay; SHA256 **bytes UTF-8** phải khớp sample. Không ảnh, dữ liệu thật hoặc raw output. |
| Source | `source_id`, `role` (đúng một focal/hai peers), `identity`, `report_sha256`. Đúng ba model ID khác nhau. |
| Identity | Toàn bộ bảy trường `SourceIdentity` T2: model/revision/implementation/configuration/run/series/attempt. So chính xác ở source, report, selection và từng row. |
| Report | `source_id`, `identity`, `planned_ids`, `rows`. Plan mỗi model bằng manifest; một report đã chọn cho mỗi source, không tự chọn trong nhiều reports. |
| Row | `sample_id`, `identity`, `input_sha256`, `status`, `predicted_safety_level`, `hnlo`. Không trùng/thừa ID; input checksum phải trùng mẫu chung ba model. |
| Selection | `selection_id`, `authority_id`, `rule=EXPLICIT_FIXTURE_SELECTION_NO_POOLING`, `manifest_sha256`, `entries`. Mỗi entry gồm `source_id`, `identity`, `report_sha256` khớp đúng source/report. Authority trong fixture là hư cấu, không grant thực tế. |
| HNLO | `null` hoặc object `state`, `value`, `evidence_sha256`; chỉ focal. VALID cần số hữu hạn không coerce, SUCCESS và evidence khớp. MISSING cần value/ref null; INELIGIBLE giữ số nhưng ref null và không dùng số để rank. |
| Evidence | Object `sample_id`, `identity`, `input_sha256`, `value`, `qualification=SYNTHETIC_UPSTREAM_VALIDATED`. Hash ref phải tồn tại và object khớp toàn bộ row. Không duplicate/unreferenced evidence. Đây là mock bằng chứng upstream, không raw replay hoặc chứng nhận alignment thật. |

SUCCESS cần Level01–04; INVALID/TECHNICAL_ERROR/NOT_ATTEMPTED cần label null.
Thiếu row giữ trong `missing_ids`, T2 xuất MISSING theo planned denominator.
Thiếu toàn bộ model outputs được biểu diễn bằng report đã định danh có rows
rỗng; thiếu report/identity/selection bắt buộc thì **dừng**. Không bỏ model
khỏi mẫu số peers. Không chấp nhận HNLO ở bất kỳ peer nào, kể cả MiniCPM.
HNLO null/ineligible đi qua trạng thái thiếu của T2; HNLO sai kiểu/nonfinite
hoặc claim VALID thiếu chứng cứ bị từ chối trước ranking.

`fixture_sha256` dùng JSON canonical: sort keys, compact separators `,`/`:`,
ASCII escaping, UTF-8, không NaN/Infinity. **Tất cả arrays trong contract này
là tập hợp không có thứ tự** và được sort theo biểu diễn JSON chuẩn trước
hash; phần tử trùng vẫn giữ để validator bắt lỗi, không deduplicate. Đây là
hash nội dung canonical, không hash bytes của một file JSON tùy cách format.
Input text riêng dùng hash bytes UTF-8 chính xác. Report hash khóa cả row/
identity/plan, manifest khóa report hashes, selection khóa manifest và đúng
report/identity. Receipt giữ hash từng row, input, report, evidence, manifest,
selection và toàn bundle. Không claim đã verify image/source-code/weights thật.

Sau mọi kiểm tra cấu trúc/lineage, hash toàn bundle còn phải thuộc **chín seal
cố định trong source adapter**. Checksum tự khai báo hoặc `authority_id` đổi
thành “Owner-approved” không đủ: nội dung khác bị từ chối dù tự tính lại tất
cả hashes. Không nhận registry/seal từ caller; thêm fixture phải sửa source
và review. Permutation input không đổi seal/output. Cơ chế này khóa ví dụ
được phép, không phải sandbox chống người cố ý sửa Python source.

## Đáp án demo tổng hợp

Plan bốn mẫu `…01`–`…04`. Focal có ba Normal, một hazard; focal HNLO lần lượt
9/2/1/null. Hai peers có hazard fractions 0,5/1/0 trên ba Normal.
K=2: HNLO-only review `[ …01, …02 ]`; peer-only/combined
`[ …02, …01 ]`. M=0/E=3/slots=2/backlog=1. Đây là phép kiểm phần mềm,
không đo false-safe/human detection/correction hoặc lợi ích thực tế.

Case `missing_model`: MiniCPM thiếu cả bốn rows, coverage MISSING=4/4;
combined M=3/E=0/K=2 → OVERLOAD, mandatory backlog=1. Không biến missing
thành Normal hoặc chọn SUCCESS-only cohort. Những fixture khác kiểm lỗi
và signal missingness với đáp án độc lập trong `tests/test_triage_adapter.py`.

## Điều kiện trước tiếp nhận saved reports thật trong tương lai

T3 **không kích hoạt** đường đó. Cần task và implementation được review riêng:
quyền dữ liệu cụ thể từ người có quyền; O2/version cùng ledger lựa chọn nguồn/
run/series/attempt có thẩm quyền, xác định trước phân tích; manifest/custody/
hash và opaque mapping cấp trước predictions, độc lập GT/filename; exact
model/revision/implementation/config/parser/HNLO qualifications, raw-before-parse
và missing/error accounting theo hợp đồng đã duyệt. Nếu nhiều lượt tồn tại,
custodian phải cung cấp ledger lựa chọn đúng identity; adapter không suy
ưu tiên latest/SUCCESS/Recovery224/full rerun. Không nhập archive để tự chọn.

Nguồn V/T/quyền/custody **O4 PENDING/BLOCKED**; protocol/series selection
**O2 PENDING**; budget/gain/CI/precision/sample size **O5 PENDING**. H/TRAIN
đã phơi nhiễm không trở thành V/T bằng đổi tên. MiniCPM hiện label-only;
không sửa parser/token/HNLO để tạo score. Historical release/T0/T1 metadata
hashes không thay approval khoa học, quyền thứ ba hoặc quyền TEST.
Không đổi M1/M2/T1/nhãn/split/metric; không claim hiệu quả dữ liệu thật.

Kết quả kiểm thử và các giới hạn Windows được ghi trong
[PROJECT_STATE](PROJECT_STATE.md#t3--synthetic-provenance-adapter-01112026)
và Draft PR cùng task. Dừng để ChatGPT review trực tiếp GitHub.
