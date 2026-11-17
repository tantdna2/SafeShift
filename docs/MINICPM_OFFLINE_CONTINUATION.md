# MiniCPM nối nhiều job offline — Issue #202

**SOURCE CANDIDATE / OWNER RUN BLOCKED.** Task lập trình ngày 17/11/2026 từ
main `e713d56d62a5a649a2078f2c2376fde6d025b978` sau PR201. Một branch mới,
một Draft PR; dừng để ChatGPT review trực tiếp, audit Antigravity độc lập,
quyền merge riêng trong cùng session audit, xác minh hậu merge và release thật.
Không có GPU, Kaggle/API thật, TEST, production journal, ký vé thật hoặc xuất
notebook production trong task này.

[Issue202](https://github.com/tantdna2/SafeShift/issues/202) áp dụng cách nối job
của InternVL sau Attempt11. Nguồn đã đọc: [quyết định6816197123](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6816197123),
[release PR196](https://github.com/tantdna2/SafeShift/pull/196#issuecomment-6820247354),
[Owner acknowledgment6889246677](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6889246677),
[runbook InternVL](TRAIN3763_DEFERRED_RECONCILIATION.md), code continuation,
Owner verifier và official reader của PR196. InternVL là
`OWNER_ATTESTED_3763_SUCCESS_COMPLETE`; formal final reconciliation vẫn pending.
Không chuyển throughput, grant, khóa, session hoặc kết quả InternVL sang MiniCPM.

## Quyền mới được đề xuất

Giữ schema release recovery V4 và repair V5/RAM V6, thêm **bắt buộc** record
`offline` versioned; marker mới `SAFESHIFT_MINICPM_OFFLINE_RELEASE_V1`.
Marker cũ không kích hoạt quyền offline. Mọi source_review/independent_audit/
merge/postmerge phải là record mới, subject hash chứa toàn bộ delegation này.
Quyền O2–O6 gốc, retirement, hai failed closures và chữ ký cũ vẫn được kiểm.

```text
offline.schema = safeshift-minicpm-offline-continuation-v1
offline.decision_issue = 202
offline.operator_session = UUID MiniCPM Operator gốc, được xác nhận thật
offline.base_journal_head_sha256 = exact head trước Serial6 = repair.journal_head_sha256
offline.tools_sha256 = digest(tools_manifest())
offline.tool_blobs = Git blob SHA1 của đúng 11 scripts, kiểm mọi reviewed/merged tree
offline.unmeasured_calls = số nguyên hữu hạn do release thật khóa, 1..3762
offline.review_logins = tài khoản được phép admission cuối
```

Không có giá trị mặc định cho `unmeasured_calls`, session, private key, thời hạn
hoặc approval. Đây là cap bảo thủ được review, không phải tốc độ đã đo. Module
`minicpm_offline.py` nằm trong runtime manifest; source tree của runtime,
reviewed HEAD và merged SHA còn phải khóa cả 11 tools trong `tools_manifest()`.
Notebook V7 sinh từ **runtime commit có cùng bytes**, khóa source/capsule/code
và locator. Dùng cùng entrypoint/child/controller PR201; không có vòng model mới.

`release-template` chỉ xuất proposal chưa ký từ proposal V6 đã chuẩn bị:

```powershell
python -B -m scripts.minicpm_offline_continuation --directory data/processed/minicpm-offline release-template --v6-proposal data/processed/<unsigned-v6>.json --output data/processed/<new-unsigned-offline>.json
```

Các trường merge/HEAD/approvals/session/cap đầu còn trống; proposal bị từ chối
bởi verifier. Không sửa release V5 đã ký hoặc tự đặt APPROVED. Reviewer/Owner
cấp quyền một lần sau source gates, không vòng GitHub release từng job.

**BLOCKED hiện tại:** chưa xác định MiniCPM Operator gốc; không dùng
`a5fa95c9-bbc0-4df2-bdc7-ecb56b098bbc` (InternVL Attempt4). Chưa xác nhận khóa
riêng gốc/host, chưa có authentic exact-source offline release/expiry/initial
cap, chưa có quota/Input proof hiện tại. Không tạo Operator thay thế, key mới,
fake signature hoặc tự xem task này là quyền chạy thí nghiệm.

## Khởi tạo sau phát hành — chưa được chạy ở đây

Owner một lần tự lấy closure GitHub thật bằng tool online, dùng môi trường
Operator có official SDK đã pin, không cài lại hoặc gửi key qua chat:

```powershell
python -B -m scripts.owner_verify_minicpm_offline --authority-locator data/processed/<new-locator>.json --output data/processed/<new-authority-export> --owner-performs-network
```

Antigravity ở **session MiniCPM Operator gốc** chỉ làm offline trên máy Owner:

```powershell
python -B -m scripts.minicpm_offline_continuation --directory data/processed/minicpm-offline init --mirror data/processed/minicpm-offline-mirror --locator data/processed/<new-locator>.json --exports data/processed/<new-authority-export>/github-exports.json --initial data/processed/<serial6-spec>.json --closure data/processed/<v5-custody> --operator-session <confirmed-original-UUID>
python -B -m scripts.minicpm_offline_continuation --directory data/processed/minicpm-offline forecast
```

`init` kiểm clean merged checkout, source/tools/host/session, exact V3 prefix10
events, original retirement, V4-4 và V5 supervisor closure; giữ nguyên mọi bytes
cũ. Serial6 vẫn ordinal0/history=[]/không dự đoán kế thừa. Journal mới ở hai
thư mục riêng, create-only/fsync/OS single-owner lock. Registration/fence viết
trước; khởi tạo dở thì STOP, không xóa guard hoặc đoán bù journal.
Legacy writer bị fence; journal gốc không có COLLECTED/MEASURED/migration giả.

Holds trước Serial6 luôn **10526 calls / 5 jobs / 144000 physical GPU-seconds**.
Trần derived vẫn **14163169 calls / 3766 jobs / 108460800 GPU-seconds**; không
thay ngân sách, reset hoặc refund. Mỗi reservation mới cộng toàn cap calls và
2×job seconds, dù job dừng sớm. Reservation khác native calls, billing và quota
tuần. Không switching account để né quota. Không migration lại hoặc double-count.

## Một lượt Owner chuẩn bị và một lượt Run, mỗi lượt tối đa ba thao tác

Ở lượt chuẩn bị, Owner cung cấp proof thật về quota/UI và không có VM đang chạy,
đúng job mới/version1, bốn Input cố định và capsule slug dự kiến từ `forecast`.
Điền `owner_gate_template` thành JSON với observed Unix time, quota vật lý,
`owner_checked/no_active_job/job_absent=true` chỉ khi đã kiểm thật, và SHA256
file proof. Đây là **Owner UI observation**, chưa phải authenticated provider.
Sau upload, Owner còn phải kiểm capsule và đủ năm Input trước Run.

Antigravity kiểm local rồi chuẩn bị bằng khóa riêng gốc (đường dẫn local,
không copy/log/commit khóa):

```powershell
python -B -m scripts.minicpm_offline_continuation --directory data/processed/minicpm-offline stage --private-key <existing-private-key-path> --owner-gate data/processed/<fresh-owner-gate>.json --proof data/processed/<fresh-ui-proof-file>
```

Fresh gate phải còn trong provider_max_age_seconds của grant. Ticket có schema
riêng `safeshift-minicpm-offline-ticket-v1`, RSA3072/SHA256 thật, grant/value/
notebook/capsule hashes, serial6+, previous-event hash, đủ lineage/holds, limit và
start-before. Chỉ tạo tuần tự trên host/session được quyền gốc ủy nhiệm. Không
ký khi thiếu key, có active/STOP, sai history hoặc hết cap/quota/expiry. Runtime
kiểm root release thật; không yêu cầu approval/release mới từng job.

`handoffs/<serial>/notebook.ipynb`, `dataset/` (Private capsule) và
`owner-steps.json` có đúng job slug, version1, năm Inputs, ordinals/caps/expiry.
Trạng thái **OFFLINE_PREPARED_NOT_UPLOADED_NOT_SUBMITTED**, chưa publish/Run.

Owner trong lượt Run chỉ làm:

1. Upload **toàn bộ nội dung dataset/** thành Dataset mới Private đúng slug/v1;
   import notebook đúng job/v1. Capsule có ticket, request và mọi ancestor/sidecar.
2. Gắn đúng năm Inputs trong owner-steps.json; kiểm Private/Python/Internet On/
   T4×2, quota tuần thật, expiry và không VM trùng. Hết cửa sổ thì STOP, không Run.
3. Save Version → Save & Run All **một lần**. Sau terminal thật, tải attempt ZIP,
   supervisor ZIP và cả hai sidecar; lưu proof terminal/download và receipt thật.

Receipt terminal có chính xác: job, version1, kernel_id, state COMPLETE,
archive_sha256, supervisor_sha256, owner_downloaded_unix,
no_other_job_or_version, no_api_submission, proof_sha256. Có version2/job khác,
không biết đã submit/calls hay thiếu proof thì không tự điền true/COMPLETE.
Antigravity không chạy gh/API/SDK/Owner verifier hoặc live observer thay Owner.

```powershell
python -B -m scripts.minicpm_offline_continuation --directory data/processed/minicpm-offline accept --attempt data/processed/<download>/<run>.zip --supervisor data/processed/<download>/<32hex>.zip --owner-receipt data/processed/<owner-terminal-receipt>.json --proof data/processed/<terminal-proof-file>
python -B -m scripts.minicpm_offline_continuation --directory data/processed/minicpm-offline forecast
```

SHA/CRC/manifest, mỗi ordinal, ID/image SHA, strict raw-before-parse/4 nhãn,
native/load/generate claims, source/ancestor, sealed retention, RAM/reclaim/group
receipts và proof bytes đều phải PASS. SUCCESS và INVALID là durable completion;
INVALID giữ nguyên, không nhận là nhãn khoa học hợp lệ. TECHNICAL_ERROR, orphan,
partial, zero progress hoặc unknown calls ⇒ STOP; giữ cả input evidence xấu,
reservation và error type, không tự repair/skip/rerun. Chỉ append
**OFFLINE_VERIFIED_PROVISIONAL**; không giả COLLECTED/MEASURED/provider-verified.

Sizing dùng MiniCPM telemetry kiểm từ ZIP/claims cùng source: overhead thực,
max call latency×safety, first-call/export margin, pending thật, caps, quota và
expiry. Lượt đầu dùng cap hữu hạn đã review, không mặc định3763. Không mượn
13.42s/200/174 của InternVL, không hứa số job. Runtime tiếp tục kiểm thời gian,
ZIP/disk/RAM trước từng call; adaptive stop giữ completed outputs và pending.
Telemetry offline giúp ước lượng, không giả event MEASURED hay population bound.

## Backup và gián đoạn

Hai mirror có thể cùng thiết bị, không phải backup phần cứng độc lập hoặc global
exactly-once. Owner giữ nguyên download gốc và backup cả hai custody/guard/exports
ra thiết bị riêng. Mất cả hai bản không thể phục hồi bằng phỏng đoán; không takeover.
`status` kiểm lại chain/mirror/originals và full local custody. `export-active`
chỉ hoàn tất missing file của **cùng** intent/ticket; không reserve lại. Existing
bytes phải khớp tuyệt đối. Copy hoàn chỉnh trước crash được tái dùng; copy partial,
torn event/mirror hoặc source/original drift STOP/read-only. Không truncate/xóa/sửa
history. `accept` chỉ có thể thử lại cùng active nếu chưa có STOP/torn event;
khi có STOP cần đối soát/authority sửa riêng, không cấp lượt mới tự động.

## Đối soát cuối một lần

`manifest --output <new.json>` chỉ khi đủ3763 contiguous ordinal, không active/STOP.
Manifest khóa từng attempt/ticket/Owner receipt/ZIP/sidecar/native/raw/lineage,
mọi historical failure và reservations. Không chọn best output hoặc tính metric/GT.

Owner có tối đa ba thao tác ở lượt final:

1. Tự chạy `python -B -m scripts.owner_verify_minicpm_offline --directory
   data/processed/minicpm-offline --output data/processed/<fresh-final-provider>
   --owner-performs-network`. Tool GET GitHub thật, official SDK read-only từng
   job/version/latest/private/notebook/source/5 Inputs; tải/so mọi capsule member
   (kể cả ancestors), cả hai ZIP/sidecar và full local replay. Kiểm lại hai failed
   technical jobs và account inventory/quota; retired provider uncertainty giữ
   nguyên, không suy absence hiện tại thành deletion/terminal trong quá khứ.
2. Sau report thật, Owner đăng lên Issue202 marker
   `SAFESHIFT_MINICPM_OFFLINE_FINAL_V1` với `{manifest_sha256, report_sha256,
   status:"APPROVED_FOR_FINAL_ADMISSION"}`. Reviewer kiểm originals rồi cấp một
   comment riêng marker+`_ADMISSION` với `{manifest_sha256,report_sha256,
   owner:{comment_id,body_sha256},status:"RELEASED_FOR_FINAL_ADMISSION"}`.
3. Owner export hai comment thật; Antigravity hợp vào **bản copy exports mới**
   (không sửa bản gốc) rồi chạy `reconcile --report <report.json> --exports
   <final-exports.json> --owner-locator <json> --admission-locator <json>`.

`reconcile` append đúng một `MINICPM_OFFLINE_CAMPAIGN_RECONCILED` trong journal
mới, giữ mọi thời điểm/reservations gốc. Event chỉ khóa hash; manifest/report/
exports đầy đủ nằm trong `final/` ở cả hai mirror, create-only. Nhờ đó số job
nhiều không làm event chứa lặp mọi cumulative history vượt envelope128MiB.
Từng final document vẫn có bound8GiB; thiếu RAM/disk phải STOP, không bỏ custody.
Duplicate bị chặn. `official-report`
chỉ PASS sau kiểm lại certificate/manifest/Owner/reviewer/every-job report,
xuất3763 rows/history/lineage/budget. Trước đó official analysis BLOCKED.
Legacy summary/collector không biết schema mới và không được dùng làm kết quả
chính thức. Provider exception giữ partial/BLOCKED và không log signed URL.

## RAM và giới hạn còn lại

[PR201 RAM repair](MINICPM_V5_RAM_REPAIR.md) giữ nguyên: admit→setup→reclaim→cpu→
gpu→native, signed16384MiB, snapshot/cgroup/OOM/RSS/process group, chỉ advise
job-owned venv; không advise shared Input/checkpoint, không đổi native source.
Original TRAIN3763 (3724 JPEG+39 PNG tại đuôi .jpg), checkpoint, năm pinned
Input, model/FP16 weights/FP32 resampler/C1/strict parser/HNLO N/A/TEST đóng.
`KAGGLE_VENV_LAYOUT_UNVERIFIED`, `FAIL_CLOSED_BUT_OWNER_RUN_CAN_STILL_ABORT`.
Fail-closed vẫn có thể tiêu quota; CPU/mock không là Kaggle/model-fit PASS.
Tăng custody theo lineage vẫn bị giới hạn request/archive/disk hiện có; thiếu
dung lượng dừng, không xóa bớt ancestor hoặc bỏ verifier để đi tiếp.
