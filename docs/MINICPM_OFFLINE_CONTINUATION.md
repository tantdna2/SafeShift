# MiniCPM nối nhiều job offline — Issue #202

## Serial 8 GPU-stage closure and Serial 9 / 19 November 2026

The Serial 8 journal reserved `nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-8`.
The Owner reported running `nguynanhtn/notebook1358a4d09b`. The two slugs are
retained separately. Local replay of both signed journal copies and
`data/processed/inspect_run_8` verifies successful admit/setup/reclaim/CPU,
a supervised GPU failure (`nvidia-smi` exit 12), zero native loads and calls,
and only the supervisor ZIP and sidecar. Exit 12 records the failed command.
Kaggle metadata is required to confirm the CPU-only setting.

**Pending Owner provider verification and fresh source release.** Use the
original MiniCPM Operator checkout and custody for the following transition.

1. After merge and postmerge verification, the Owner personally runs
   `python -B -m scripts.owner_verify_minicpm_offline --serial8-closure --output data/processed/<new-serial8-export> --owner-performs-network`.
   The read-only verifier checks actual private kernel v1 and latest, terminal
   status, explicitly disabled GPU, notebook code, the five attached Input
   slugs, published private capsule v1 bytes, paginated Output inventory and
   the exact supervisor pair. It checks that the reserved slug is absent in
   the current Owner inventory. A missing accelerator field, unknown version,
   conflicting slug or extra Output blocks closure. Preserve the original
   download and the new provider export.
2. Prepare the unsigned spec and proposal with the continuation CLI.
   `serial9-spec --output <initial>` derives the plan from the original 3,763
   TRAIN IDs. `serial9-release-template --initial <initial> --serial8-closure <export>/serial8-closure.json --output <proposal>`
   pins the verified closure. Use the same global `--directory` argument as
   other commands. The fresh `SAFESHIFT_MINICPM_OFFLINE_RELEASE_V5` release
   binds the reviewed/merged source, tools, historical authority and closure.
   The Owner proof workflow accepts `--serial9-proof-proposal` followed by
   `--authority-locator` after publication.
3. The original Operator initializes new primary/mirror directories with the
   existing `init` arguments and `--serial8-closure <export>/serial8-closure.json`.
   This creates a new fence and records `FAILED_PRE_NATIVE_NO_USABLE_RESULTS`
   in the successor registration. All originals remain in place. The first
   forecast has ordinal 0, 3,763 `NOT_ATTEMPTED`, and **10,826 calls / 8 jobs /
   230,400 physical GPU-seconds reserved**. After the fresh quota, Inputs,
   no-active-job and expiry checks, `stage` issues only a new Serial 9 ticket
   for `nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-9` and private capsule
   `nguynanhtn/safeshift-minicpm-capsule-mcpm4-restart-v1-9/1`. The original
   Operator publishes the handoff for the Owner to run once with T4 ?2.

The failed run contributes zero imported results and zero refunds. Successful
result ingestion still requires an attempt ZIP. The final Owner reconciliation
rechecks the Serial 8 closure alongside the earlier technical failures.

## Serial 8 source transition / 19 November 2026

Serial 7 stopped during CPU-stage GitHub authority verification. Local custody
confirms zero native loads or calls and 3,763 `NOT_ATTEMPTED`. The versioned
transition carries all seven holds forward with verified provider custody
and a separately released source. Each stage keeps live GitHub release and PR
checks and verifies the supporting proof pinned by that release.
[Incident and transition runbook](MINICPM_SERIAL8_AUTHORITY.md).

## Serial 7 transition / 18 November 2026

The V3 offline delegation starts with **10,626 reserved calls, six jobs and
172,800 physical GPU-seconds**. The first three holds account for 3,000 calls,
Serials 4 and 5 for 3,763 each, and Serial 6 for 100. Serial 7 begins at
ordinal 0 with all 3,763 original TRAIN IDs NOT_ATTEMPTED and empty history.
No prediction or reservation is imported as a scientific result.

The read-only verifier checks the two copies of the prior registration and
event, the old signed ticket, the exact downloaded inventory, supervisor ZIP,
sidecar, extracted receipts and loose claims. The local SHA256 pins are

| Object | SHA256 |
| --- | --- |
| Serial 6 source | `cc0141cb3800898398d32d8114c275e0c89773a41affcd3dcd2ca2a8b86b2f95` |
| Historical signed ticket | `99085ce10341106b99e8470cc30ff25f0e5c041008436d0b6511a5f975c653b2` |
| `data/processed/minicpm-offline/event-000001.json` | `b32b8728b5848ca94c9b883c1718969aeb2891d4e3d2d3e2b950cc7c4394b200` |
| Supervisor under `data/processed/inspect_run_6/` | `3d92d80065e89fe2abd22e81b4f64462121e0f0a8b2d03be986c4f5bfdd93a5c` |

**Release pending.** After direct HEAD review, independent audit, separate
merge authorization and postmerge verification, prepare the initial spec using
`prepare-spec --page-cache-repair` and the existing original spec. Use the
repaired checkout and its exact runtime ref to construct the unsigned RAM-repair
proposal over that new spec, then the offline `release-template`. New source
authority must bind the two Serial 6 evidence hashes, the reviewed tools and
the new runtime. The release marker is `SAFESHIFT_MINICPM_OFFLINE_RELEASE_V3`.

The original Operator uses separate, fresh primary/mirror directories for
`init` (e.g. `data/processed/minicpm-offline-s7` and its `-mirror`) with the
original V5 closure. Keep the original offline directories, registration and
fence in place. Following source release and current quota/Input/expiry checks,
the first fresh ticket binds `mcpm4-restart-v1-7`. The Operator publishes at
most three Owner steps. The Owner alone runs. The provider verifier separately
rechecks Serial 6 during final reconciliation. No fresh release, ticket, job
or provider observation was issued by this source repair.

### Historical Serial 6 route (PR204)

The following commands, schemas and initial balances describe that earlier release.

**SOURCE CANDIDATE / OWNER RUN BLOCKED.** Task lập trình ngày 17/11/2026 từ
main `0f598f1f4f67619edbf8948492ac9b12af119edd` sau PR203. Một branch mới,
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
`offline` versioned; marker mới `SAFESHIFT_MINICPM_OFFLINE_RELEASE_V2`.
Marker cũ không kích hoạt quyền offline. Mọi source_review/independent_audit/
merge/postmerge phải là record mới, subject hash chứa toàn bộ delegation này.
Quyền O2–O6 gốc, retirement, hai failed closures và chữ ký cũ vẫn được kiểm.

```text
offline.schema = safeshift-minicpm-offline-continuation-v2
offline.decision_issue = 202
offline.operator_session = 0b1d115c-c002-44e8-b22e-087226f6dc73
offline.base_journal_head_sha256 = exact head trước Serial6 = repair.journal_head_sha256
offline.tools_sha256 = digest(tools_manifest())
offline.tool_blobs = Git blob SHA1 của đúng 11 scripts, kiểm mọi reviewed/merged tree
offline.unmeasured_calls = 100 (trần job đầu; signed max_calls có thể thấp hơn)
expires_unix = issued_unix + 30*24*3600 (tại thời điểm phát hành thật)
```

[Quyết định Owner6954626555](https://github.com/tantdna2/SafeShift/issues/202#issuecomment-6954626555)
thay yêu cầu tài khoản Reviewer thứ hai của PR203 bằng **một comment GitHub thật
của Owner** trên Issue202, sau đối soát đủ3763 ảnh và từng job/provider gốc.
Schema V2 từ chối grant V1 hoặc trường `review_logins`; không sửa grant/ticket cũ.
Bốn source-stage approvals vẫn giữ nguyên theo `minicpm_release.load`, mỗi record
ràng buộc `subject_sha256` chứa schema, cap và thời hạn mới; chúng không yêu cầu
thêm người GitHub. Source mới phải có review/audit/merge/postmerge và release mới.

Proposal để trống `issued_unix/expires_unix`; chỉ điền thời điểm phát hành thật,
không kế thừa hoặc hồi tố ngày cũ. Verifier bắt buộc đúng30 ngày, không phải cam
kết hoàn tất trong30 ngày. Trần đầu100 không phải tốc độ đã đo hoặc cam kết hoàn
tất100 ảnh trong2–2,5 giờ; quota/time/export có thể giảm signed max_calls. Mỗi job
tối đa4 giờ; adaptive pre-call/export guards vẫn chặn khi thiếu thời gian.
Không có approval/private key mặc định. Module
`minicpm_offline.py` nằm trong runtime manifest; source tree của runtime,
reviewed HEAD và merged SHA còn phải khóa cả 11 tools trong `tools_manifest()`.
Notebook V7 sinh từ **runtime commit có cùng bytes**, khóa source/capsule/code
và locator. Dùng cùng entrypoint/child/controller PR201; không có vòng model mới.

`release-template` chỉ xuất proposal chưa ký từ proposal V6 đã chuẩn bị:

```powershell
python -B -m scripts.minicpm_offline_continuation --directory data/processed/minicpm-offline release-template --v6-proposal data/processed/<unsigned-v6>.json --output data/processed/<new-unsigned-offline>.json
```

Các trường merge/HEAD/approvals/issued_unix/expires_unix còn trống; proposal bị từ chối
bởi verifier. Không sửa release V5 đã ký hoặc tự đặt APPROVED. Owner
cấp quyền một lần sau source gates, không vòng GitHub release từng job.

**BLOCKED hiện tại:** giữ Operator gốc `0b1d115c-c002-44e8-b22e-087226f6dc73`; không dùng
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
riêng `safeshift-minicpm-offline-ticket-v2`, RSA3072/SHA256 thật, grant/value/
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
expiry. Lượt đầu dùng trần100 đã review; signed max_calls có thể thấp hơn. Không mượn
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
2. Sau kiểm đầy đủ report/originals, Owner đăng **một** comment thật lên Issue202:
   marker `SAFESHIFT_MINICPM_OFFLINE_FINAL_V2` với `{manifest_sha256,
   report_sha256, status:"APPROVED_FOR_FINAL_ADMISSION"}`. Hash phải khớp manifest
   có thứ tự đủ3763 ảnh và report xác thực từng job/ZIP/sidecar/capsule/source,
   cùng mọi bằng chứng cũ. Không cần tài khoản Reviewer thứ hai.
3. Owner export comment thật; Antigravity hợp vào **bản copy exports mới**
   (không sửa bản gốc) rồi chạy `reconcile --report <report.json> --exports
   <final-exports.json> --owner-locator <json>` với locator `{comment_id,body_sha256}`.

`reconcile` append đúng một `MINICPM_OFFLINE_CAMPAIGN_RECONCILED` trong journal
mới, giữ mọi thời điểm/reservations gốc. Event chỉ khóa hash; manifest/report/
exports đầy đủ nằm trong `final/` ở cả hai mirror, create-only. Nhờ đó số job
nhiều không làm event chứa lặp mọi cumulative history vượt envelope128MiB.
Từng final document vẫn có bound8GiB; thiếu RAM/disk phải STOP, không bỏ custody.
Duplicate bị chặn. `official-report`
chỉ PASS sau kiểm lại certificate/manifest/Owner/every-job report,
xuất3763 rows/history/lineage/budget. Trước đó official analysis BLOCKED.
Legacy summary/collector không biết schema mới và không được dùng làm kết quả
chính thức. Provider exception giữ partial/BLOCKED và không log signed URL.

`official-report` kiểm lại cùng quy tắc ID/login khi đọc certificate, không chỉ
tin event từng được append. Exports là response GitHub do Owner lấy thật; sửa
offline JSON có thể giả nguồn gốc, nên Owner custody của exports và kiểm originals
trực tiếp trên GitHub vẫn là trust boundary đã công bố. Không nhận một
`approved:true` hay proof tổng quát thay comment Owner và từng provider.
Owner verifier online chỉ xuất report/template PENDING, không tạo final approval
hoặc admission; một comment Owner thật vẫn cần ở bước sau.

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
