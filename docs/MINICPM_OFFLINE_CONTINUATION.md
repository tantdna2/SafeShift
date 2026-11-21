# MiniCPM nối nhiều job offline — Issue #202

## Tiếp nối nhanh sau Serial 11 — 21/11/2026

`scripts.minicpm_offline_fast` là companion cho Operator trên journal V5 đã
đăng ký. Runtime, grant V5, schema ticket/event, notebook, checkpoint, năm Input,
C1 và trình đối soát cuối dùng mã PR #209. Việc chuyển tiếp cần release
Operator riêng. [Snapshot local và trạng thái GitHub](PROJECT_STATE.md).

### Quy trình sau khi companion được cấp quyền

Dùng tiền tố lệnh dưới đây tại repo root của Operator đã hậu kiểm, với primary
hiện hành và locator/export được Owner giao qua custody.

```text
python -B -m scripts.minicpm_offline_fast --directory <primary> --operator-release <locator.json> --owner-exports <github-exports.json>
```

1. **Sau khi Kaggle hoàn tất**, Owner giao hai ZIP, sidecar, terminal proof và
   Owner receipt đúng job/version. Operator chạy `accept --attempt <zip>
   --supervisor <zip> --owner-receipt <json> --proof <file> --private-key
   <original-key>` rồi `forecast`. Companion kiểm CRC, raw/C1 và native claims
   của lượt mới. Operator dùng khóa hiện hành ký chứng từ xác minh local, ghi
   create-only vào hai mirror trước event tạm thời. Khóa vẫn nằm tại chỗ.
2. **Chuẩn bị lượt tiếp theo.** `forecast` trả ordinal, ảnh còn lại,
   reservation, telemetry, trần thời gian và số job tối thiểu theo trần call.
   Quota và kích cỡ được cấp xác định tại `stage`. Owner kiểm tra quota tuần,
   không job đang chạy, slug/version đích chưa tồn tại và năm Input theo template.
   Operator chạy `stage --private-key <original-key> --owner-gate <json>
   --proof <file>`. Lệnh reserve đúng một lượt rồi xuất notebook/capsule.
3. **Bàn giao notebook.** Operator chuyển đúng capsule Private, notebook và
   `owner-steps.json` theo luồng Owner UI V5. Owner xác minh slug, năm Input,
   T4 ×2, quota và hạn ticket, rồi tự bấm **Save Version > Save & Run All** đúng
   một lần. Tệp xuất local chỉ xác nhận bước chuẩn bị.

**STOP.** Dừng khi mirror thiếu, hash lệch, job/capsule bất định, hết hạn, thiếu
proof hoặc raw/native lỗi. `status` cho biết active serial và ticket digest.
Nếu cả hai event `accept` đã ghi và `forecast` bị ngắt, chạy `status` rồi
`forecast` khi active rỗng. Nếu mới ghi custody hoặc seal, tiếp tục `accept`
với đúng ticket và chứng cứ đã giữ. Event chỉ có ở một mirror cần đối chiếu
chỉ đọc. Nếu `stage` đã reserve mà thông báo bị ngắt, giữ ticket hiện có và
kiểm tra Owner UI trước khi `export-active` hoặc bàn giao. `export-active` cần
ticket còn hạn và dừng nếu đã bắt đầu `accept`. Mọi hold được giữ nguyên.

### Hai tầng xác minh

InternVL gọi `quick_bundle` qua `verify_local(full=False)`, kiểm CRC, SHA,
C1, native custody và lịch sử. Numeric vector replay thuộc
`validate_reconciliation`, cùng đối chiếu từng job, capsule và output qua
Owner verifier. [Runbook InternVL](TRAIN3763_DEFERRED_RECONCILIATION.md).

V5 MiniCPM gọi `recheck` cho mỗi completion trong mọi `state`.
`verify_claims` và `verify_results` giải nén hai ZIP. `restore_history` nhập
từng tổ tiên, replay trước/sau cài scratch. `export-active` làm lại trên cả
hai capsule. Companion dùng prefix đã được audit và chứng từ có chữ ký cho
completion về sau. Mỗi lệnh kiểm event/mirror, ký số, lineage, gate, file gốc
và SHA256 từ byte hiện tại trong cả hai bản custody/capsule. ZIP đã xác minh
được đối chiếu hash cho các bước vận hành. Các closure pre-native tiếp tục
qua trình xác minh hiện hành.

Dùng `manifest`, `reconcile`, `official-report` của
`scripts.minicpm_offline_continuation` và
`scripts.owner_verify_minicpm_offline` để đối soát cuối. Owner tự lấy provider
proof. V5 replay mọi attempt, capsule và closure, đủ thứ tự 3.763 ID,
raw/parser/native, provenance, chữ ký, holds/budget và Owner final approval.
`OFFLINE_VERIFIED_PROVISIONAL` tiếp tục là tạm thời.

### Tái lập bài đo CPU

```text
python -B -m scripts.benchmark_minicpm_offline
python -B -m scripts.benchmark_minicpm_offline --case 808
```

Bài đo tạo cohort 3.763 ID tổng hợp, ticket RSA fixture và ZIP có raw/claims
tổng hợp. V5 và companion nhận cùng snapshot journal/mirror và cùng hai
ZIP mới. Mỗi trường hợp đo `state → accept → forecast → stage → export-active`
khi lượt mới đưa tổng lên 808, 2.000 hoặc 3.763. Ở 3.763, các bước chuẩn bị
lượt mới phải dừng. Chỉ số `zip_file_bytes` đếm byte ZIP nén qua đọc tệp
bao gồm copy, SHA và ZIP reader. `zip_member_bytes` đếm byte thành viên
sau giải nén. `sha256` đếm khởi tạo SHA256 trong Python, `file_sha256` là phần gọi
helper đọc tệp để băm. `historical_replays` đếm số lượt replay nội dung
lịch sử. Thời gian tạo fixture và bản sao nằm ngoài số đo.

### Chuyển tiếp trên cùng chiến dịch

- V5 có thể tiếp tục theo release, gate và giới hạn hiện hành. Khi chuyển
  tiếp, Operator chốt head sau khi đối chiếu active/reservation với Owner.
  Giữ nguyên thư mục, khóa và mọi hold. Các Serial 9–11 được tiếp nhận từ
  chứng cứ có sẵn.
- Sau review trực tiếp, audit Antigravity độc lập, merge được phép riêng và
  hậu kiểm, đối chiếu prefix thực tế bằng V5 đầy đủ. Prefix có thể kết thúc
  ở một reservation đã xác minh. Owner phát hành record
  `SAFESHIFT_MINICPM_OFFLINE_OPERATOR_FAST_V1` trên PR companion với
  `status=RELEASED_OPERATOR_FAST_PATH`, `implementation_pr`, `reviewed_head`,
  `merged_sha`, `grant_sha256`, `registration_sha256`, `prefix_event_number`,
  `prefix_head_sha256`, `tool_sha256` và `approvals`. Bốn approval riêng
  `source_review`, `independent_audit`, `merge`, `postmerge` dùng marker
  `SAFESHIFT_MINICPM_FULLTRAIN_APPROVAL_V2` và `subject_sha256` của record
  canonical bỏ trường `approvals`. Job tiếp tục dùng cap và expiry V5.
- Owner chuyển locator (`comment_id`, `body_sha256` của body UTF-8) và JSON
  mapping response GitHub gốc từ phiên xác thực. Gồm `/issues/comments/<id>`
  của release và bốn approval, `/pulls/<pr>`, cùng
  `/git/trees/<ref>?recursive=1` của reviewed HEAD và merge SHA. Companion
  kiểm SHA256 và Git blob trong hai tree theo custody Owner exports V5.
- Companion mở cùng registration, mirror và lock. Mỗi thời điểm chỉ có một
  Operator ghi. V5 có thể đọc kết quả do companion ghi. Nếu V5 ghi thêm
  completion sau prefix đã duyệt, cần review lại prefix trước khi chuyển lại
  companion. Mất đồng thời cả hai bản phần đuôi cùng toàn bộ custody phải
  đối chiếu với chứng cứ bên ngoài.

## Serial 8 GPU-stage closure and Serial 9 / 20 November 2026

The Serial 8 journal reserved `nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-8`.
The Owner reported running `nguynanhtn/notebook1358a4d09b`. The two slugs are
retained separately. Local replay of both signed journal copies and
`data/processed/inspect_run_8` verifies successful admit/setup/reclaim/CPU,
a supervised GPU failure (`nvidia-smi` exit 12), zero native loads and calls,
and only the supervisor ZIP and sidecar. Exit 12 records the failed command.
Read-only GetKernel v1 and latest returned the reserved slug with ID
`145987007`, version 1, private, COMPLETE, `enableGpu=true` and
`machineShape=NvidiaTeslaT4`. The versioned notebook code hash was
`ccb3f0485f34cd4218cf1ef1840d59a5d580ed903b04e88510f1df402273eda5`.
The versioned Output had 246 files. Its log SHA256 was
`aa64813972c708e1ab581ae1df0b5a5cdb46b3a3769c2da207b79c6211987fad`
and the downloaded supervisor SHA256 was
`3b5f95188943d5af6dc4abf9b6c9431586503c77075b0fe3c311d2360d563ec8`.
Only the UI-supplied standalone notebook log was extra in the local download.
The run's own receipts record the failed GPU command. The API fields describe
the saved configuration. Actual device allocation and the loader error text
inside this container remain unknown.

**Pending Owner provider verification and fresh source release.** Use the
original MiniCPM Operator checkout and custody for the following transition.

1. After merge and postmerge verification, the Owner personally runs
   `python -B -m scripts.owner_verify_minicpm_offline --serial8-closure --output data/processed/<new-serial8-export> --owner-performs-network`.
   The read-only verifier checks actual private kernel v1 and latest, terminal
   status, stable numeric ID, notebook code, the five attached Input
   slugs, published private capsule v1 bytes, paginated Output inventory and
   the exact supervisor pair after the start window closes. Both known slugs
   are candidates. If renamed again, pass the current slug via `--provider-job`.
   Inventory entries can omit the numeric ID. Exactly one candidate must resolve
   and GetKernel must return ID 145987007 for both v1 and latest. Missing
   accelerator fields are recorded as unknown. Conflicting jobs, version, code,
   Input, capsule bytes or Output block closure. Preserve the original
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
   Operator publishes the handoff for the Owner to run once with **GPU T4 ×2**.

The failed run contributes zero imported results and zero refunds. Successful
result ingestion still requires an attempt ZIP. The final Owner reconciliation
rechecks the Serial 8 closure alongside the earlier technical failures.

### Runtime and recovery on the new source

The isolated worker had no loader path for its unscoped NVIDIA utility. In
Issue173 the same symptom was reproduced with a working kernel driver and
missing worker-side NVML resolution. The successful InternVL worker explicitly
bound host libcuda and scoped the mounted driver directory to the utility.
The MiniCPM GPU and native stages now use this pattern, save driver binding
and bounded command diagnostics, then check two physical T4s and CUDA FP16 on
worker GPU0. RAM/cgroup, disk, quota and pre-load VRAM checks still run.
[Issue173 driver evidence](KAGGLE_CHECKPOINTS_173.md#measured-loader-isolation-and-scoped-driver-binding--03112026).

The Serial 8 policy required 13,000 MiB free on both devices before load.
Reapplying that threshold to GPU0 with resident FP16 weights can stop the
first call. The unsigned V5 template explicitly proposes 256 MiB of **free**
GPU0 memory after load, the per-call reserve from the MiniCPM Candidate160
route. The reviewed release must bind `offline.resident_gpu0_min_free_mib`.
Only after a successful load does the worker use that value. It checks both
NVML and CUDA free memory, the unused GPU1 reserve and a functional FP16 probe.
The value marks a stop threshold. Full-TRAIN fit, latency and completion remain
unmeasured on this source.

| Observation in a later serial | Action |
| --- | --- |
| Terminal before load or call, sealed supervisor and sidecar, closed start window | Owner runs `python -B -m scripts.owner_verify_minicpm_offline --pre-native-closure <primary> --download <original-output> --output <fresh-export> --owner-performs-network`. Supply `--provider-job <owner/current-slug>` if needed. The original Operator runs `python -B -m scripts.minicpm_offline_continuation --directory <primary> close-pre-native --download <original-output> --provider-closure <fresh-export>/pre-native-closure.json`. Preserve the original download for replay. |
| Accepted pre-native closure | Both journals append the failure. Its signed successor binds the failed ticket, closure and full hold. Run `forecast` and address the recorded failure before staging a fresh ticket. Pending starts at the previous next ordinal, including zero when history is empty. |
| Timeout, API outage, ambiguous job, missing/torn supervisor, current launch window, expired unused ticket or uncertain native activity | Keep active reservation and every partial. Recheck the same version into a fresh export when evidence becomes available. Expiry alone never closes a hold. If evidence cannot establish the outcome, further staging stays blocked for external reconciliation. |
| Attempt ZIP with a clean adaptive stop | Use ordinary `accept` with both sealed pairs and terminal proof. Replay raw/claims against the ordered IDs. Preserve SUCCESS and INVALID, schedule only NOT_ATTEMPTED. |
| Attempt ZIP with zero progress, runtime error, corrupt/missing raw or duplicated/out-of-order ordinal | Preserve the failure and originals. The result path stops for reconciliation. An uncertain attempt cannot use pre-native closure. |

Final verification re-fetches successful attempts, every pre-native closure,
each private capsule and their Output. If an Owner kernel has since moved, the
final verifier accepts `--aliases <json>` mapping its known numeric ID to the
current Owner slug. Duplicate candidates or conflicting stable identity stop
verification. The final manifest and authentic Owner approval remain required
before `official-report`. This checkout supplies code and CPU verification only.

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
