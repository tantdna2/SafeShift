# TRAIN3763 — nối lượt offline và đối soát cuối chiến dịch

Owner [6816197123](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6816197123)
chỉ giao triển khai. **Chưa READY, chưa kích hoạt**: cần ChatGPT review đúng HEAD,
kiểm toán Antigravity độc lập, merge được cho phép riêng, xác minh hậu merge và
release mới cho route này. Không dùng release một Attempt của PR194 thay release
campaign. [Bản quyết định và provenance](research/evidence/train3763_deferred_20261112/owner-export-provenance.json)
được Owner xuất; Codex không truy vấn dịch vụ bên ngoài trong task lập trình.

## Điểm xuất phát đã kiểm local

BASE `341ab626ff2af7ef79ced0d9c3119794eea4a820` (main local sau PR194).
Operator checkout vẫn là `4407dc939e045d115f4147e2d1d49605ec8b2f7a`.
35 journals/mirrors; INTENT35 có digest
`f16a75b01e7a0ad1550e17cc4fdaeaacdc3abd9e99329e562c9d7d16de147b18`.
**Không có journal36/37**. 323 ảnh đã được ledger thu nhận; ZIP Attempt11 local
có 200 SUCCESS ordinal323..522, 200 calls, 8264 members, SHA256
`a06f6714e4755a084af66312d06cf06fe7ea04456e807c71daaa875b07969ea0`.
Đã kiểm full runtime bundle/native claims/sealed history bằng CPU và kiểm
quick/Input/checkpoint/Python/handoff; lineage khớp. Đây là kiểm local, không phải
Kaggle/API verification hoặc COLLECTED. [Receipt](research/evidence/train3763_deferred_20261112/baseline-inspection.json).

Đã giữ chỗ **528 calls / 11 jobs / 72000 physical GPU-seconds**, không refund.
O5 hiệu lực là430000, còn **3972 calls / 89 jobs / 358000 GPU-seconds**.
MEASURED34 đúng source `f062f170c38f2f70c21c6f7462d9408e5a5ea6862b923a40cf9e58b75489239d`:
safe_calls200, overhead2192s, per_call25s, job_seconds<=7200.
Sau baseline11 hợp lệ:3240 ảnh, 16×200 +40 =17 jobs; nếu reserve7200s mỗi job,
244800 GPU-s mới, tổng316800;3768 calls và28 jobs. Đây là dự báo kỹ thuật có
điều kiện, không bảo đảm độ trễ cả quần thể, quota tuần hoặc lịch hoàn thành.

## Ranh giới công cụ và trạng thái

Chạy external companion [train3763_continuation.py](../scripts/train3763_continuation.py)
và hai file cùng thư mục `owner_verify_train3763_continuation.py`,
`reconcile_train3763_manual.py` từ tools checkout đã review. Imports runtime luôn
từ `--approved-repo` gốc; **không overlay hoặc rebuild notebook/runtime**.
`tool_manifest()` khóa cả ba file. Code/model/weights/prompt/grammar/parser/HNLO,
Input gốc và scientific selection giữ nguyên. Notebook được xuất là bản sao
byte-for-byte của notebook đã duyệt; capsule mới chứa đúng request và intent.

| Bản ghi | Ý nghĩa |
| --- | --- |
| OFFLINE_CONTINUATION_ADMISSION | Một append mới vào ledger gốc, khóa đúng registration/baseline/release; không đóng INTENT35 |
| RESERVED_OFFLINE | Reservation mới trong journal riêng, charged trước khi xuất capsule; chưa phải SUBMITTED |
| OFFLINE_VERIFIED_PROVISIONAL | ZIP/sidecar/CRC/manifest/ordinal/raw custody/Input/Owner receipt đã kiểm local; provider và numerical replay cuối còn pending |
| STOPPED | Giữ nguyên mọi partial/raw/error/reservation, dừng schedule và chỉ đối soát đọc |
| OFFLINE_CONTINUATION_RECONCILED | Append tổng hợp chính thức sau mọi gate; giữ từng Attempt và thời điểm thực tế theo thứ tự trong manifest |

Registration/journal riêng nằm trong `data/processed/`, mirrored create-only,
OS lock trên ledger gốc và journal mới. Mỗi write flush/fsync và sync directory
khi OS hỗ trợ. Hai thư mục có thể cùng ổ đĩa: đây không phải backup độc lập phần
cứng hoặc global exactly-once. Owner giữ nguyên downloads và backup ra thiết bị
khác khi cần; không chuyển máy vận hành. Mất cả hai bản không thể được code khôi
phục bằng suy đoán. Journal không ký số; trust boundary là máy Owner và authenticated
Owner export, không phải bằng chứng mật mã về nguồn gốc JSON.

INTENT35 **luôn giữ nguyên**, kể cả sau đối soát cuối. Nó cố ý tiếp tục chặn
`Ledger.reserve()` cũ. Không chạy staging/collector/measure cũ sau admission.
Route mới đọc reservations và aggregate record của chính nó; công cụ cũ sẽ báo
open INTENT và counts lịch sử, không được dùng làm status toàn chiến dịch.
Không giả COLLECTED/MEASURED/PUSH_INTENT/SUBMITTED. Journal36 dự kiến là admission,
không phải COLLECTED11; chỉ sử dụng nếu ledger vẫn đúng35. Nếu36/37 thật đã xuất
hiện, STOP để thiết kế transition tương ứng, không xóa hoặc sửa chúng.

## Authority mới — một lần cho route, một lần admission cuối

Không có release được tự phát hành trong task. Reviewer đăng một record
`SAFESHIFT_TRAIN3763_CONTINUATION_RELEASE_V1` kèm fenced JSON, trên PR mới đã merge.
Các trường **chính xác**:

```text
campaign_sha256: original grant digest
decision_body_sha256: 50e416ea2d77606bbbdad7e1bc660be36af4d979720d47234ac22e234c03d5f8
implementation_pr, reviewed_head, merged_sha: PR/HEAD/merge thật
script_sha256: SHA256 train3763_continuation.py
tools_sha256: digest(tool_manifest()) của ba file đã review
audit: {comment_id, body_sha256}
source_sha256, notebook_sha256: source/notebook gốc của Attempt11
scope: OFFLINE_SERIAL_DEFERRED_RECONCILIATION
base_head_sha256: exact INTENT35 digest
start_ordinal: 323
```

Start323 chỉ để tiếp nhận baseline11 vào custody tạm; Attempt12 bắt đầu523 sau
quick PASS11. Audit marker là release marker + `_AUDIT`, nội dung chính xác
`{reviewed_head, script_sha256, tools_sha256, status:"PASS", independent:true}`,
author trong audit_logins, comment khác reviewer, cùng PR. Code kiểm PR merged
main, toàn bộ hash, Owner ID246929698/association/Issue180/body pinned và các
authority original grant/technical/O5. Không có `approved:true` bypass.

Một lần sau release, **Owner tự chạy** exporter `--authority-only` để lấy closure
các comment/PR thật. Antigravity chỉ dùng `github-exports.json`, không fallback
network và không giả là đã tự xác thực API. Source/budget/expiry/old exports
drift, thiếu record hoặc quyết định bị sửa đều BLOCKED. Reviewer phải kiểm các
link gốc trên GitHub độc lập trước cấp release.

## Khởi tạo sau review/audit/merge/release — chưa được chạy trong task này

Các lệnh dưới dùng PowerShell từ repo root. Điều chỉnh `$tools` về tools checkout
đã merge được xác minh; **không thay HEAD checkout Operator gốc**.

```powershell
$tools = '.worktrees/train3763-offline-continuation/scripts'
$operatorPython = 'data/processed/operator-venv/Scripts/python.exe'
$common = @('--approved-repo', '.', '--ledger', 'data/processed/train3763-campaign/ledger', '--directory', 'data/processed/train3763-deferred')
```

Owner làm tối đa ba bước trong lượt kích hoạt:

1. Chạy bằng tài khoản của mình (có network thật; không giao Antigravity chạy):

```powershell
& $operatorPython -B "$tools/owner_verify_train3763_continuation.py" --approved-repo . --ledger data/processed/train3763-campaign/ledger --authority-only --release-locator data/processed/continuation-release-locator.json --output data/processed/continuation-authority-export --owner-performs-network
```

2. Cung cấp exports và local completion receipt11 cho Antigravity. Receipt có
đúng `{job, version:1, kernel_id, state:"COMPLETE", archive_sha256,
no_other_job_or_version:true, no_api_submission:true, owner_downloaded_unix}`.
Các thông tin phải từ Owner/download thật; không tự điền COMPLETE hoặc timestamp.
3. Antigravity chạy offline `init`, rồi `accept`11, `forecast`, `stage`12 dưới đây;
chỉ giao Owner upload/Run khi mọi gate PASS và đúng quyền đã phát hành.

```powershell
python -B "$tools/train3763_continuation.py" @common init --mirror data/processed/train3763-deferred-mirror --github-exports data/processed/continuation-authority-export/github-exports.json --release-locator data/processed/continuation-release-locator.json
python -B "$tools/train3763_continuation.py" @common accept --archive data/processed/attempt11-collection/ivl35-train3763-11-3636b26e657a426ca44d0785c6255b01.zip --owner-receipt data/processed/attempt11-local-owner-receipt.json
python -B "$tools/train3763_continuation.py" @common forecast
python -B "$tools/train3763_continuation.py" @common stage --calls 200 --seconds 7200
```

`init` từ chối mọi thay đổi baseline, missing handoff, ambiguous API submission,
mirror/guard/source/hash/caps/authority drift. Nó không chạy Kaggle, không thu
nhận chính thức11. `accept` kiểm SHA và archive limits; CRC/checksum toàn bộ
members; 3763 rows; đúng planned range/one native call mỗi ảnh; raw-before-parse
bindings, vector dimensions/hashes và trace receipt; unchanged Inputs/checkpoint/
Python bytes receipts; native claims; exact Owner completion receipt. Numerical
mask/greedy replay độc lập để cuối chiến dịch; không claim đã kiểm ở quick stage.
SUCCESS và INVALID đều là durable completion. TECHNICAL_ERROR, thiếu ảnh, raw lỗi,
partial output hoặc FAIL khiến STOP, không tự repair/resume bỏ qua.

Stage chỉ resume contiguous NOT_ATTEMPTED, <=MEASURED34, grant expiry/time window
và tổng caps. Không đo lại hay cấp lại release từng lượt. Tail tự giảm calls còn40
nếu yêu cầu200; có thể dùng3192s cho tail theo envelope, nhưng mặc định7200s là
bảo thủ. Tổng chi phí không refund dù dừng sớm. Không mở quyền repair, model
khác, TEST hoặc khoa học mới từ route này.

## Mỗi lượt Owner chỉ ba bước

`stage` tạo `handoffs/<id>/notebook.ipynb`,
`capsule/safeshift_train3763_execution.json`, `owner-steps.json` ở cả hai custody.
Đây là **OFFLINE_PREPARED_NOT_UPLOADED_NOT_SUBMITTED**, chưa chứng minh Input tồn tại.

1. Upload **chỉ capsule JSON** thành Dataset mới Private version1 đúng slug đã
   giao; import notebook thành **job mới đúng `job` trong owner-steps.json**,
   version1. Không dùng slug tự sinh khác hoặc tạo version2.
2. Gắn đúng năm Input/version trong `owner-steps.json`; kiểm Private, Python,
   Internet On, T4×2, batch/time limit, Input khả dụng và quota tuần đủ trên UI.
3. Save Version → Save & Run All **một lần**. Sau terminal thật, tải ZIP + sidecar
   nguyên bản, giữ output/completion proof và local receipt; báo Antigravity.

Antigravity offline: `accept --archive <download> --owner-receipt <json>` rồi
`stage`. Không GitHub comment/release/COLLECTED/MEASURED mỗi lượt. Không chạy
exporter online hoặc bất kỳ gh/API/SDK network nào thay Owner. Không hủy job hoặc
submit lại khi máy mất mạng/tắt; pending reservation tiếp tục chặn schedule.

## Khôi phục sau gián đoạn

`status` kiểm chain/mirror/base/handoff/custody; sau một reservation đã ghi nhưng
chưa xuất đủ file, `export-active` chỉ xuất lại **cùng intent**. File đã hoàn chỉnh
phải byte-identical; không ghi đè hoặc reserve lại. Nếu copy ZIP/sidecar đã hoàn
chỉnh trước mất điện nhưng chưa publish receipt, `accept` có thể tái kiểm cùng
active intent và dùng các bản copy khớp hash. Copy partial/sai hash giữ nguyên,
STOP. Event/mirror torn, initialization torn, mất history hoặc source drift:
STOP/read-only, không tự lấp journal, truncate, delete, reset hay init route khác.
Các bản còn nguyên phục vụ đối soát có kiểm soát; không thể hứa phục hồi bytes
chưa từng được tải xuống hoặc ghi bền.

## Một đối soát tập trung cuối chiến dịch

`manifest --output <new.json>` chỉ chạy khi đủ3763 contiguous ordinals, mọi
Attempt đã local-complete, không active job/STOP. Manifest gồm baseline custody,
từng original request/intent/ZIP/sidecar/receipt/time và toàn bộ ngân sách, INVALID
giữ nguyên. Không pooling/select kết quả hay Accuracy/Macro-F1/AUROC mới.

Owner làm ba bước, có thể trải qua nhiều lượt trao đổi:

1. Tự chạy `owner_verify_train3763_continuation.py --approved-repo . --ledger
   data/processed/train3763-campaign/ledger --directory data/processed/train3763-deferred
   --output data/processed/continuation-final-provider --owner-performs-network`.
   Công cụ đọc GitHub thật, SDK official pinned thật; kiểm **từng** historical
   job và future job, version1/latest1/private/kernel/code/five Inputs, capsule
   bytes, tải lại chính ZIP/sidecar từ provider và so hash, log, full raw/vector/
   numerical trace replay, lịch sử và account inventory hoàn chỉnh. V1 Attempt8
   giữ actual distinct slug. Không upload/submit. Mất GitHub/Kaggle, drift hoặc
   thiếu proof → BLOCKED.json, giữ partial, không admission. Fresh output directory
   khi được xử lý kỹ thuật; không re-run GPU hoặc sửa evidence.
2. Sau xem report, Owner đăng marker `SAFESHIFT_TRAIN3763_CONTINUATION_FINAL_V1`
   lên Issue180, fenced JSON đúng `{manifest_sha256, report, status:
   "APPROVED_FOR_AGGREGATE_ADMISSION"}` từ report thật. Template local chưa phải
   approval. Reviewer kiểm từng bằng chứng, rồi cấp **một** marker final +
   `_ADMISSION` với `{manifest_sha256, owner:{comment_id,body_sha256},
   report_sha256, status:"RELEASED_FOR_AGGREGATE_ADMISSION"}`. Hai comment riêng,
   reviewer thuộc review_logins; không có dependency hash vòng tròn.
3. Owner xuất hai comment thật bằng `gh api ... | Out-File -Encoding utf8 <file>`.
   Antigravity offline hợp bằng `merge-exports --base <github-exports.json>
   --comment <owner-comment.json> --comment <reviewer-comment.json> --output
   <new-exports.json>`, không sửa exports gốc; sau đó chạy `reconcile
   --github-exports <json> --final-locator <json> --admission-locator <json>`.
   Nó kiểm full local lần cuối, exact report/manifest/Owner/reviewer/hash, rồi
   append một `OFFLINE_CONTINUATION_RECONCILED` qua Ledger.append create-only/fsync/
   mirror. Payload chứa từng reservation/completion theo thời điểm thực tế;
   append time tách khỏi actual times, không backdate hoặc giả lịch sử legacy.

Resource report giữ setup/worker/load/peak RAM GPU/ZIP/calls và conservative GPU
reservations của từng Attempt. Billing/session GPU-seconds thật nếu chưa có nguồn
thì **NOT_OBSERVED**, không lấy reservation làm số đã dùng. Formal status route
mới được tách khỏi legacy COLLECTED. Reconcile lần hai bị chặn. Write/mirror lỗi
không báo success và không tự retry. Một aggregate approval không thay thế từng
provider original; Owner-executed verifier và GitHub exports là trust boundary
được khai báo, reviewer/auditor phải kiểm nguồn thật độc lập.

Online verifier phải dùng interpreter venv Operator đã pin ở trên, có sẵn
official SDK; không cài lại dependencies hoặc tự probe account trong task này.
Các lượt aborted trước submit vẫn giữ reservation và original abort evidence;
final account inventory kiểm absence hiện tại, không dùng absence hiện tại để
suy đoán lại quá khứ. Các FAIL lịch sử vẫn được đối soát, telemetry thiếu ghi
NOT_OBSERVED. Local receipt lưu thời điểm kiểm offline và thời điểm Owner tải;
không gán chúng thành thời điểm Kaggle hoàn tất.
