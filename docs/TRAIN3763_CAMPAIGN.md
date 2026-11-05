# TRAIN3763 campaign contract — Issue180, 05/11/2026

## Current capsule HTTP302 repair and Attempt1 recovery

[Owner task / ChatGPT diagnosis](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6662845867)
starts at BASE `2484095e7b29c3c1d5ad79f18523cfa8dd6a0cac` (PR181 merged).
The original [Owner O2–O6 scoped decision](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6657871236)
and authentic PR181 campaign grant remain the execution authority inside their
unchanged science/rights/caps/deadline. This repair issues no authority and runs
no Kaggle operation, including read-only provider probes, uploads or smoke.
The earlier no-grant/CPU acceptance paragraphs below are historical PR181 snapshots.

### Transport contract

`bounded_http()` is unchanged: metadata, auth, logs, POST/kernel submission and
legacy traffic never gain automatic redirects. Only `verify_execution_input`
wraps the pinned SDK `DownloadDataset` RPC for the exact owner/slug/version/file.
Its POST body is checked against the SDK serialization; an HTTP302 may produce
exactly one **new GET** to `https://storage.googleapis.com` with a nonempty query.
No POST body, Kaggle Authorization/cookies/headers, netrc, proxy credentials or
client certificates reach storage. Other schemes/hosts/ports/userinfo/fragments,
relative URLs, control characters, further redirects and non200 storage responses
fail closed. A new storage host requires a reviewed explicit allowlist change.
TLS verification stays enabled. The signed URL is used opaquely and is never
recorded; download exceptions are replaced without a chained sensitive traceback.

Both requests retain zero adapter retries and10s connect/30s read timeouts.
The writer has no retry/resume loop, caps streamed bytes at64MiB and checks a90s
monotonic budget before every64KiB write and after completion. A blocked read is
additionally bounded by its30s timeout; the90s check is not a hard subprocess kill.
It fsyncs the create-only `download.part` and preserves it on failure. File type
is detected from bytes, never an untrusted URL/filename. Plain JSON must match
the exact size/bytes; a ZIP must have exactly the named capsule, exact uncompressed
size and valid CRC. SHA256 and exact request/intent proof precede PUSH_INTENT and
the only `kernels_push`. The SDK's separate default five-retry file writer is
not called. SDK verbose logging is forbidden during this download.

### Preserve, reconcile, then stage separately

Read-only local inspection in this task found matching root/mirror/guard and one
INTENT, no PUSH_INTENT: job `safeshift-train3763-ivl35-train3763-1`, source
`b571c356361f428eb69278c569bf52a90f362f562b7a3837937dad76f77c1e9c`,
intent `15528ad3f88997fa19416a8dfc8e214eb04a887ff93aaa5c536de287aae8f8f6`.
Attempt1 reserves1 call,1 job and3600 physical GPU-seconds. Its local capsule is
5,630,833 bytes. These are local custody observations, **not provider job absence**.
Nothing in the actual campaign ledger, guard, grant, context or capsule was changed.

Keep the same Antigravity operations session and canonical ledger/mirror paths
from its existing registration. Preserve every existing `submission/`, download
partial, handoff event, report, original private capsule/version and all journals.
An existing submission directory now stops with an explicit preservation error;
never delete/rename it to make an old attempt runnable. `plan` also rejects an
existing handoff before reserving budget. Every attempt requires a new capsule
dataset slug; neither an old capsule nor its newer version can replace Attempt1.

This patch changes operator/campaign source SHA and therefore requires a new
committed runtime, rebuilt PREP/execution notebooks, notebook/code hashes and
technical revision on **this repair PR**. The exact merged HEAD check and source
checks remain enforced. After real ChatGPT review, independent Antigravity audit,
separately authorized merge and verification, retain the PR181 grant locator and
obtain authentic `SAFESHIFT_TRAIN3763_AUDIT_V1` / `TECHNICAL_V1` records for this
new source/regression/runtime/notebook identity. Synthetic test attestations are
not operational evidence. Old Attempt1/context/technical attestations stay frozen.
Science SHA must still equal
`ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`.

Only after those technical gates may Antigravity run the existing CLI below.
`abort-pre-submit` now authenticates the original grant and checks complete owned
provider inventory, exact absence of the old job, all prior campaign jobs and
zero GPU reservation **under the ledger lock**, before appending mirrored
ABORTED_PRE_SUBMIT with the hash-bound inventory proof. Timeout, existing/unknown
job, pagination/history drift, nonterminal prior job, unknown consumption or any
PUSH_INTENT stops read-only; no abort/refund/new intent follows. It checks the old
request for custody without pretending its source is valid at the new HEAD.

```powershell
# AFTER review/audit/authorized merge only; uses existing operator/session/paths.
$OperatorPython = './data/processed/operator-venv/Scripts/python.exe'
$Ledger = 'data/processed/train3763-campaign/ledger'
& $OperatorPython -B -m scripts.train3763_campaign abort-pre-submit --directory $Ledger
# Success is a new ABORTED_PRE_SUBMIT; original INTENT and all charges remain.
# Prepare context-attempt2.json separately with authentic new technical_revision
# and a unique private capsule slug/version. Keep the original context untouched.
& $OperatorPython -B -m scripts.train3763_campaign plan --directory $Ledger --grant data/processed/train3763-campaign/grant-locator.json --template data/processed/train3763-campaign/context-attempt2.json --cohort data/processed/train3763-campaign/cohort.json --handoff data/processed/train3763-campaign/attempt-2 --mode initial --calls 1 --seconds 1800
```

With no native job/history, Attempt2 is initial qualification on ordinal0, not
repair of a consumed image. Both attempts retain3763 IDs/order and immutable
lineage; combined reservation is2 calls,2 jobs,7200 GPU-s, with no refund for
Attempt1. Full shards remain blocked until new-source native measurements.
No renewed Owner grant is needed for this technical fix inside existing caps.
This task does not execute either command or close the real Attempt1: provider
absence, final-source live verification and real technical attestations remain
BLOCKED / NOT_RUN pending the permitted operations workflow.

### Checkpoint discrepancy

Attempt1's stored request, the frozen runtime descriptor and #173's saved marker
all identify `OpenGVLab/InternVL3_5-4B-HF`, revision
`6bd4487402110ef9889ba50eb7aefeb302526fed`, mounted from
`nguynanhtn/safeshift-prepare-internvl35/1`. The approved lock and
[actual historical byte receipt](research/evidence/issue173/checkpoint-bytes-v1.json)
agree on both shards: `337d6d5bea97956480a1560c3a88e4e6c4455c3954b94ed468c367cf4b500f20`
(4,954,007,064 bytes) and `343234927f41c7d3a4aa8a2280864f477b1f77795463feb6b26910fa2e4921d3`
(4,511,078,400 bytes); index `4f5f24a16dc7fcba6edeb8df8482f633b369c284685f92c6e3d6069ee3b323e1`.
There is no `InternVL-Chat-V1-5` configuration in this campaign. The reported old
name conflicts with the stored request and verified historical bytes. A current
exact private provider source snapshot is not available in this task, so calling
it a proven report typo would overstate the evidence. Antigravity must reconcile
that label against retained exact source/version/marker/shards before submit;
unresolved identity or different bytes means STOP, never silently change model.

### Repair validation

The regression suite uses installed official SDK0.1.38/requests2.34.2 with a
requests HTTP adapter stub and actual file/ZIP streaming. Sockets are prohibited.
Run it in the existing operator environment, then the campaign/controller/
execution/handoff suites and deterministic notebook rebuild tests. The updated
`scripts.qualify_internvl3763` includes `test_internvl3763_capsule`; a skipped SDK
suite is not HTTP302 proof. [New repair receipt and logs](research/evidence/train3763_capsule302_20261105/summary.json)
record189/189 CPU tests PASS, zero skips/failures/errors, including13 transport
tests; notebook3/3 PASS. Clean tested HEAD is
`d961d3c04f0b36f110ff5954f23e60e9ee021829`, runtime
`216e94bc1a57d7a6715183300ed8088496868417`, source
`649102f0a4c2a13d87044f3a4c9a7316d9b6d9dee71ebc3ddbacfd196c816934`.
All84 inherited runtime files and shared transport match BASE. Repo-wide smoke
is incomplete (600s stop requested, sandbox denial delayed verified process stop
to about703s); official-FP329 tests with1 failure/9 errors and Candidate160-
notebook4 tests with1 failure/1 error reproduce identically on pristine BASE and
this branch. No whole-repo or CI PASS: GitHub Actions has0 configured workflows.
PR181's historical receipt remains unchanged. Live recovery/source qualification,
independent audit and authorized merge remain separate pending gates.

## Historical PR181 implementation contract and acceptance

Design recorded before implementation. BASE: `300fc4e305ffa6f1fed9b86ebfedbc996bc9dde2`.
This PR authorizes code and synthetic CPU checks only. No live Kaggle, GPU,
private raw, TEST, campaign grant or numerical execution budget is issued here.

One authentic Owner campaign record will bind the original3763 projection,
master/Input/checkpoint/method/rights, one operator machine, finite calls/jobs/
physical-GPU seconds/deadline, per-job ceilings, stop rules and technical-fix
policy. Attempts are derived locally inside those caps; no per-job Owner
comment is required. Scientific and third-party decisions remain separate.
The old per-attempt/HTTPS route remains a historical compatibility route;
its grants and consumed claims cannot migrate into a new campaign.

The new route has one serial operator and two create-only journal copies on
separate local custody directories. Every intent is fsynced to both before
the single provider push. Partial writes, divergent copies, unknown submission,
missing ledger/history, provider identity drift, active jobs, corrupt export or
unreconciled calls stop scheduling. Locks cover all mutations. No automatic
POST retry, reclaim, refund or takeover. A full coordinated rollback of both
copies cannot be detected offline; retain independent provider/ZIP/checkpoint
custody. This design does not claim global exactly-once against another machine,
manual notebook replay, administrator tampering or lost custody. Cross-machine
takeover is blocked until the previous operator is fenced and its complete
hash-checked journals and provider history are reconciled read-only.

Resume schedules only NOT_ATTEMPTED from complete sealed lineage. Repair is a
separate action with exact error record hashes, diagnosis, fix and regression
hashes; SUCCESS is never repaired. Technical source versions require reviewed,
merged source and independent audit evidence under campaign-selected reviewer
identities, not renewed Owner execution approval. Frozen scientific bytes and
method identity must match. Every attempt retains its own3763 records; operational
coverage is not scientific output selection, pooling or a claim of100% SUCCESS.

First authorized final-source qualification is ordinal0/one call. Later shard
caps require measured final-source duration, GPU/RAM and archive/raw sizes from
that sealed job. Conservative local storage gates remain in force. Historical
941/941/941/940 is precedent, never a hardcoded shard size or new result input.

Antigravity uses the existing official SDK and foreground conversation handoff.
Monitor at most15 minutes, save RUNNING_UNVERIFIED and exit; Kaggle continues.
On the next user message resume the saved conversation, inspect exact terminal
version, collect ZIP/sidecar/log and validate custody. Preserve FAIL/BLOCKED and
give Codex a bounded diagnostic handoff. No background AI or automatic submit
from a collection operation. The runbook and acceptance receipt are completed
in this same PR after tests.

## Authority records and migration

`internvl3763_campaign.load` authenticates one UTF-8/SHA-pinned Owner GitHub
comment on this merged implementation PR, marker
`SAFESHIFT_TRAIN3763_CAMPAIGN_V1`, followed by one fenced JSON object. The strict
schema is `safeshift-train3763-campaign-v1`:

| Fields | Required meaning |
| --- | --- |
| campaign_id, operator_id, operator_root_sha256 | Safe IDs and hash of canonical ledger location plus machine identity. `identity` prints the hash without publishing personal paths. Another directory/host cannot initialize the same grant. |
| authorization | `GRANTED_FOR_BOUNDED_CAMPAIGN`, issued by the Owner after real decisions. |
| implementation_pr, reviewed_head, merged_sha | This merged PR, exact reviewed HEAD and actual merge SHA on main. No PR177–179 grant reuse. |
| science_sha256, cohort_sha256, input_marker_sha256 | Frozen science fingerprint, original3763 projection and exact original `master_manifest.json` bytes SHA (the locked MASTER_SHA, not a newly invented fulltrain marker). No labels/GT are embedded in plans. |
| inputs | Exact immutable `dataset_sources` and `kernel_sources`, including existing original data/master/checkpoint mounts. New small execution capsules may be added only under the existing Owner account. |
| rights | O2–O6, each with actual `status`, HTTPS `ref`, content `sha256`. Accepted statuses are APPROVED or NOT_REQUIRED_WITH_BASIS. No automatic waiver or PENDING-to-approved conversion. A reference is an attestation, not a forged third-party signature. |
| review_logins, audit_logins | Principals allowed to attest technical review and independent audit. These roles cannot issue more campaign budget. |
| issued_unix, expires_unix | Finite campaign window, maximum366 days. Collection remains possible after expiry. |
| caps | Positive integers: total_calls, total_jobs, total_gpu_seconds, job_calls, job_seconds, archive_bytes, physical_gpus=2, max_repairs_per_image; machine_shape=NvidiaTeslaT4. Job <=43200s, archive <=7GiB. The Owner supplies actual values; this PR supplies no executable budget default. |
| policy | Exactly serial=true; resume=NOT_ATTEMPTED_ONLY; repair=DIAGNOSED_TECHNICAL_ONLY; technical_fixes=REVIEWED_MERGED_SCIENCE_UNCHANGED; ambiguous=STOP_READ_ONLY; refund=false; test=false; scientific_selection=PENDING; pooling=false. |

Technical source qualification is separate from execution permission. A comment
by a campaign-authorized reviewer on the merged source PR uses marker
`SAFESHIFT_TRAIN3763_TECHNICAL_V1`, with campaign_sha256, science_sha256,
implementation_pr, reviewed_head, merged_sha, runtime_commit, source_sha256,
notebook_sha256, notebook_code_sha256, regression_sha256 and an `audit` locator
(`comment_id`, `body_sha256`). The independent audit comment on that same PR uses
`SAFESHIFT_TRAIN3763_AUDIT_V1` with campaign_sha256, reviewed_head, source_sha256,
regression_sha256, status=PASS and independent=true. Both comments are authenticated
by author/ID/body hash and exact merged PR. These are recorded attestations of
actual reviews, not proof generated by the runner that an audit happened. Initial
and subsequent technical versions use this same route; no new Owner campaign
comment is needed. Semantic source changes fail the frozen science fingerprint.

Old release V1 and SQLite/HTTPS witness code remain unchanged in purpose and
retain compatibility tests. The published execution notebook now uses campaign
admission; the builder's legacy `--execute` without `--campaign` only reproduces
the former route. A legacy grant cannot activate campaign mode. Old source locks,
consumed markers and historical result series are never rewritten or imported.

## PowerShell runbook (after review/audit/authorized merge only)

Run from the exact reviewed merged source checkout. Reuse the existing isolated
operator environment and Antigravity account connection. Do not create a new
environment or reauthenticate merely because a new shard is starting. If the
environment is absent, the existing `prepare_train3763_operator.ps1` provisions
the approved pins in a new ignored directory; it does not authenticate or submit.
No command below is executed against Kaggle by this implementation PR.

```powershell
$OperatorPython = './data/processed/operator-venv/Scripts/python.exe'
$Ledger = 'data/processed/train3763-campaign/ledger'
$Mirror = 'data/processed/train3763-campaign-custody/mirror'
$GrantLocator = 'data/processed/train3763-campaign/grant-locator.json'
$Cohort = 'data/processed/train3763-campaign/original-projection.json'
$Context = 'data/processed/train3763-campaign/context.json'
& $OperatorPython -B -c 'from safeshift.internvl3763_operator import check_sdk; print(check_sdk())'
& $OperatorPython -B -m scripts.train3763_campaign identity --directory $Ledger
```

Antigravity first checks existing versioned `inspecsafe-v1-kaggle`,
`safeshift-pilot-input` and the checkpoint Input from #173 read-only, account job
state/quota and local output custody. Reuse exact existing bytes/mounts; never
reupload images/checkpoints merely to match a new slug. #173 and PR177 identify
both checkpoint shard hashes and the successful runtime, not authority for this
new source. Reuse #173's private `ordered-projection.json` as `$Cohort` after
checking its recorded SHA, rather than regenerate metadata from annotations.
The campaign worker discovers the existing `master_manifest.json`, checks its
locked original MASTER_SHA, then calls the unchanged #173 `verify_train` against
`inspecsafe-v1-kaggle/InspecSafe-V1-Kaggle/train/DATA_PATH`. Only original
master-listed `train/Annotations/*.jpg` locators are hashed/opened; TEST and
annotation sidecars are never enumerated. This route needs no
fresh_fulltrain_input.json, opaque images/ copy or new3763-image upload. The
legacy candidate route retains its packed-Input contract. Only already permitted
original TRAIN metadata may supply `$Cohort`.
The one campaign grant is issued after the remaining real rights/budget/stop-rule
questions are settled. Missing rights outside Owner authority require that actual
authority; the runner cannot infer them. Save its authentic locator privately.

`context.json` has exactly `technical_revision` (comment_id/body_sha256 of the
technical qualification above) and `execution_input` with `kind` equal to
dataset_sources and `ref` equal to the planned immutable
Owner-private capsule Input version, e.g. `nguynanhtn/<capsule-slug>/1`. It contains
no grant override or budget. Commit/runtime/notebook/source/plan/job IDs are derived
by the staging command. Use a unique small capsule slug/version per attempt;
it is separate from all existing data and checkpoint Inputs.

```powershell
# Once per campaign. Use the exact operator_id chosen in the authentic grant.
$ApprovedCampaign = & $OperatorPython -B -c 'import json,sys; from safeshift.internvl3763_campaign import load; from safeshift.pilot.artifacts import read; print(json.dumps(load(read(sys.argv[1]))))' $GrantLocator | ConvertFrom-Json
& $OperatorPython -B -m scripts.train3763_campaign init --directory $Ledger --mirror $Mirror --grant $GrantLocator --operator-id $ApprovedCampaign.operator_id
$JobSeconds = $ApprovedCampaign.caps.job_seconds
$Handoff = 'data/processed/train3763-campaign/attempt-1'
& $OperatorPython -B -m scripts.train3763_campaign plan --directory $Ledger --grant $GrantLocator --template $Context --cohort $Cohort --handoff $Handoff --mode initial --calls 1 --seconds $JobSeconds
```

Staging writes a durable mirrored intent and `$Handoff/package/` containing only
`safeshift_train3763_execution.json`. It does **not** upload or submit. The capsule
binds exact grant/request/source/history/limits and intent. Keep the whole handoff,
mirror and initialization guard; do not upload the handoff directory, CLI logs,
raw ZIPs, credentials or ledger. Prior archives remain in checked local custody
and their original Kaggle Outputs; every local archive/sidecar is revalidated
before admission. The worker trusts this sole operator's hash-bound scheduling
lineage rather than reuploading every historical raw ZIP. Each new ZIP still
contains all3763 status rows. History projection omits only NOT_ATTEMPTED rows to
bound capsule size; those remain pending in the full cohort.

Antigravity uses the existing official private Input upload procedure with the
exact version in context. For a **new** small capsule dataset, put matching
dataset-metadata.json (`id`, `title`, one actual license descriptor for this
Owner-controlled capsule) in package/ and use the pinned official CLI:

```powershell
# Default is private. Never add --public; never change existing dataset privacy.
& $OperatorPython -m kaggle datasets create -p "$Handoff/package" --keep-tabular
# Inspect the actual version/files read-only; mismatch or ambiguous upload is NO-GO.
./scripts/kaggle_handoff.ps1 -Python $OperatorPython -Action handoff -Directory $Handoff
```

The operator checks pinned SDK, clean merged source/notebook, original Input refs,
complete ledger/raw custody, all known campaign jobs terminal and exact private
versions/code, absence of unexpected campaign jobs, and zero reserved quota plus
enough available quota before its only push site. It also checks capsule privacy,
owner, exact version/file/size and downloads only that small metadata capsule to
compare every byte against the current request/intent before PUSH_INTENT. This
prevents a stale otherwise-valid capsule replaying prior images on a fresh VM;
no image, raw or checkpoint download is needed for this check. Server timeout reserves both
physical T4s without refund; native worker remains GPU0. Do not issue another
submit after timeout. Inspect the exact target job/version read-only instead.

RUNNING_UNVERIFIED is the expected handoff checkpoint. End the AI turn; the
Kaggle job continues independently. When Owner reports completion or asks for
status, resume the same conversation:

```powershell
./scripts/kaggle_handoff.ps1 -Python $OperatorPython -Action resume -Directory $Handoff
./scripts/kaggle_handoff.ps1 -Python $OperatorPython -Action report -Directory $Handoff
./scripts/train3763_campaign.ps1 -Python $OperatorPython -Action status -Directory $Ledger
```

Use `-Recover` only when the conversation is unavailable; it permits read-only
collection, never submission. Terminal collection requires the exact provider
version/private notebook/Inputs/GPU identity, provider log, ZIP+sidecar, SHA/CRC/
members, raw vectors/masks/trace/counts, source/plan and local native claims.
Successful collection closes the intent even when an intact archive reports
technical FAIL; evidence corruption/missing raw/unknown calls stays BLOCKED.
Recollection is idempotent. It does not refund budget or schedule another job.
Collection checks the job's notebook from its pinned Git commit, so a later
reviewed operator update cannot silently substitute its own notebook. Keep the
original Git objects and all local artifact paths available.

Before shards, use the exact collected final-source archive:

```powershell
& $OperatorPython -B -m scripts.train3763_campaign measure --directory $Ledger --archive $CollectedArchive --seconds $JobSeconds
# safe_calls/minimum_seconds come from this sealed native telemetry, within grant caps.
# Update context to the next private capsule Input; preserve its earlier versions.
& $OperatorPython -B -m scripts.train3763_campaign plan --directory $Ledger --grant $GrantLocator --template $Context --cohort $Cohort --handoff $NextHandoff --mode resume --calls $MeasuredSafeCalls --seconds $JobSeconds
```

Measure records setup/load/sample latency, GPU peaks, process/cgroup/RAM, float32
raw bytes and ZIP/sample sizes. The bound uses twice observed latency, conservative
uncompressed capture sizes and export margin. This is engineering planning;
one image cannot prove worst-case fit. The existing per-call time/storage gates
still stop before the next call. A source revision must be qualified/measured
again before a larger shard. There is no hardcoded941 or throughput claim here.

After an intact technical failure, Antigravity gives Codex the exact request/
intent/source/archive hashes, terminal provider identity, log paths, error stage,
all status counts and remaining caps. Codex diagnoses and tests the fix, keeps
the same science and obtains technical review/independent audit/merge. Refresh
context's technical_revision and notebook/source identity. A `repair.json` has
exactly targets (sample ID -> failed record SHA256), fix_sha256 (reviewed source
spec digest), regression_sha256 (reviewed regression receipt) and diagnosis.
Only errors are eligible; stale targets or SUCCESS are rejected. Then:

```powershell
& $OperatorPython -B -m scripts.train3763_campaign plan --directory $Ledger --grant $GrantLocator --template $Context --cohort $Cohort --handoff $RepairHandoff --mode repair --repair $RepairRecord --calls $RepairCalls --seconds $JobSeconds
```

The same campaign grant remains valid inside its caps. No Owner reapproval for
this technical repair, next shard or continuation. Never expand science, TEST,
budget or rights to get PASS. Archive every new attempt separately; repair does
not decide scientific output selection. Report actual coverage/INVALID/errors
and all lineage, not a fabricated3763/3763 SUCCESS total.

## GO/NO-GO and recovery

| Condition | Required action |
| --- | --- |
| No campaign grant, unknown real rights, budget absent/exhausted, expired execution window | STOP; settle only the actual missing campaign/authority decision. Read-only collection is still allowed after expiry. |
| Known current job RUNNING/QUEUED | Save RUNNING_UNVERIFIED, exit AI; resume the same conversation later. No next job. |
| Push timed out/crashed or provider state/version unknown | Keep intent/PUSH_INTENT/reservations; read-only exact-job reconciliation. Never retry, switch slug or create version2. |
| ZIP download partial/corrupt/missing sidecar/raw/log | Keep all partials; later collection uses a fresh directory. No next attempt until custody verifies. Hard-kill without recoverable evidence stays BLOCKED. |
| Source/runtime/Input/package mismatch | Fix/qualify the technical cause; do not change scientific pins. If PUSH_INTENT exists, reconcile before another attempt. |
| Staging/provision preparation failed before any PUSH_INTENT | `abort-pre-submit` can close only a proved never-pushed local intent; it does not refund calls/GPU/job budget. Stage a new attempt under the same campaign. |
| One journal rolled back, diverged, missing guard or lost ZIP custody | STOP. Restore exact original files from independent retained custody and reconcile provider history. Never init an empty replacement ledger. |
| Both journals/guard lost, unknown older jobs, or cross-machine takeover | STOP/read-only recovery. Fence the old machine/worker, obtain all original custody and review the concrete migration; this version supplies no automatic takeover command. No claim of global exactly-once. |

The canonical machine/path binding prevents a second local authority. An
initialization guard outside both journal directories prevents empty reinit when
both directories disappear. Live provider inventory detects orphaned campaign
jobs after local rollback. These checks cannot prove integrity after deliberate
coordinated destruction/rollback of every local and provider evidence source.
Do not represent a local hash chain as an external immutable witness.

## Reused evidence and validation

- [#173 checkpoint custody](KAGGLE_CHECKPOINTS_173.md) and [PR177 ordinal0 report](INTERNVL_V2_VERIFIED_ORDINAL0_20261104.md): reuse checkpoint/runtime/Input and RAM-repair experience; no new-source GPU PASS claim.
- Qwen2.5 four shards941/941/941/940: [historical Linux audit at exact31a04e6](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_r2_cpu_completion_20261015.md).
- [Seminar protocol](research/SEMINAR_PROTOCOL.md) and [results/limitations](RESULTS_AND_LIMITATIONS.md): Qwen3 original3539 SUCCESS/1 error/223 pending, separate Recovery224; InternVL3 saved-score3763 rows. Only operational shard/custody precedents, no new predictions or scientific pooling.
- Inherited84 runtime files, prompt/parser/grammar/model/config/checkpoint locks are compared with exact BASE. Current notebook and PREP rebuild deterministically from committed source with empty outputs.
- CPU reproduction: `python -B -m scripts.qualify_internvl3763 --output data/processed/campaign-cpu-new`; notebook tests separately: `python -B -m unittest discover -s tests -p test_internvl3763_notebook.py -v`. Optional native/SDK CPU checks use the already installed pinned environments, no network/weights/GPU.
- Final sanitized receipt records exact tested source, environment, commands, counts, source/notebook/test/log hashes and baseline limitations. Live final-source Kaggle/Inputs/quota/weights/inference/export, independent audit and scientific qualification remain NOT_RUN/PENDING in this PR.

## Final acceptance — 05/11/2026

[Sanitized receipt](research/evidence/internvl3763_campaign_20261105/summary.json):
**172/172 CPU tests PASS, zero skips/failures/errors**, including actual installed
CPU GenerationMixin capture/replay and pinned official SDK serialization, private
capsule version/bytes, ambiguous submit, duplicate/process exclusion, rollback/
loss, quota, crash, ZIP/raw custody, original mounts, repair and source revision.
Notebook3/3 deterministic rebuild/empty-output checks PASS. PowerShell5.1 parses
all3 scripts and6 runbook blocks; actual identity and synthetic report wrappers
PASS. No new actual Antigravity AI turn was run; subprocess/conversation behavior
is covered by contract tests and prior actual CLI evidence remains historical.

Runtime commit `8a0a26e103230946f24bc3b01e69c7d244f20bb5`; source-spec SHA256
`b571c356361f428eb69278c569bf52a90f362f562b7a3837937dad76f77c1e9c`.
All84 inherited runtime files match BASE; approved generation, native backend/
image preparation, trace binding and configuration AST match BASE exactly.
The full repository smoke was bounded to600s and remains incomplete, not PASS.
Official-FP32's9-test suite independently reproduces identical1 failure/9 errors
on pristine BASE and this branch. Historical locks/configuration remain unchanged.

Only current implementation/code review is ready. No live Kaggle submit/upload,
GPU, real model/image/private raw or TEST access occurred. Campaign grant/caps/
genuinely missing rights, direct ChatGPT review, independent Antigravity audit,
authorized merge and subsequent bounded final-source qualification remain open.
