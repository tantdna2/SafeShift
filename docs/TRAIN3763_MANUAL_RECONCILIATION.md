# Owner UI Kaggle collection — 09/11/2026

## Current: bounded complete output pagination, same Attempt9 → Attempt10 task

[Directive6792693343](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6792693343)
requires one focused corrective Draft PR after PR193 MERGED at
`630fa486af8a418c644859b0c7280b56489be8ab`. The original Operator checkout stays
at `4407dc939e045d115f4147e2d1d49605ec8b2f7a`; do not edit its source or any
already released reviewed-tools file in place. Codex uses a separate branch/
worktree, edits only the external collector/tests/current documents and stops
for direct ChatGPT review. No production collection/measurement, GPU/submit,
new notebook/runtime/Inputs or science change occurs in this code phase.

The previous single-page guard `MANUAL_OUTPUT_LIST_BOUND` correctly stopped the
Operator-reported 34-page / 8,470-file listing before provider ZIP download or
ledger append. The reported listing has 8,468 unpacked files and one exact ZIP
plus its SHA sidecar on page1. This is supplied operational evidence, not newly
verified provider evidence from this programming session.

### Listing contract before any output download

- Use the existing pinned official `kagglesdk==0.1.38` request, fixed
  `page_size=256`, exact owner/slug and constant `version_label="v1"` on every
  page. Pass each returned token unmodified as the next request's `page_token`.
- Exhaust the terminal response within **64 pages / 16,384 metadata entries**;
  do not hardcode the observed 34 pages as a production maximum. A continuation
  on page64 fails closed without requesting page65. Every page must contain
  1..256 files. A missing/null/empty file list is ambiguous and blocks.
- Continuation tokens must be strings of at most4096 printable ASCII characters
  without whitespace, repeated tokens or cycles. Official absent/null/empty
  terminal tokens mean exhaustion; empty intermediate pages are never accepted.
  The pinned SDK getters use `value or ""`, so the collector validates the
  underlying optional token/log storage before normalization; counterfeit
  falsy nonstrings cannot silently become terminal tokens or empty logs.
- File names are bounded to4096 characters and canonical relative slash paths
  with `[A-Za-z0-9_~.-]+` segments; empty/dot/parent/absolute/Windows paths block.
  All names must be unique across all pages, including unselected detail files.
  Check all pages before choosing the exact expected ZIP and sidecar. Any extra
  `.zip`/`.zip.sha256.json` (case-insensitive detection), duplicate or conflicting
  name blocks, even when page1 already contains the expected pair.
- Retain the first nonempty provider log, at most16MiB. Later absent/null/empty
  logs or byte-identical repeated logs are valid; any different nonempty log or
  wrong log type blocks. Missing nonempty log across the complete listing blocks.
- Collect metadata only. Only the two selected URLs are used for downloads;
  both pass the existing exact HTTPS origin/path/token/name allowlist before
  **either** anonymous GET. Never download the thousands of unpacked detail
  files. No provider log/output file is created until listing and URL checks pass.
- SDK errors, partial/malformed response, page timeout or any bound/ambiguity
  blocks without output GET or ledger append. Keep the existing sanitized
  BLOCKED receipt in its fresh evidence directory. No overwrite, redirect,
  ambient credentials or automatic retry. Existing per-request10/30-second
  bounds, download240-second deadline, disk/byte/SHA/sidecar checks and immutable
  raw/native/trace/ordinal/source/authority/provider/Input/capsule/ledger guards
  remain unchanged. V1 Attempt8 single-page collection remains supported.

### Required review/release and immediate operational continuation

PR193's [V2 release6792239710](https://github.com/tantdna2/SafeShift/pull/193#issuecomment-6792239710)
is immutable, pins script `900b2ff80d4120ba59ba72e9bbfb0df8c47ca88f72e346eff60780fba76f49a8`
and **cannot authorize these modified bytes**. Use direct ChatGPT HEAD/diff/test
review, a new independent Antigravity audit session separate from
`operator-asus-win`, separately authorized normal merge in that audit session,
then ChatGPT verification of main/parents/tree/files and a new exact V2 reviewer
release tied to unchanged authentic Owner record6790846059. Codex does not issue
audit/merge/release or production-admission authorization.

Then original `operator-asus-win` deploys the newly released tool separately and
runs a fresh genuine `SAME_SCHEDULED_SLUG_V2 --check-only` against the original
Attempt9 ZIP/ledger/handoff/provider. After actual READ_ONLY_VERIFIED and proof
that ledger bytes did not change, ChatGPT gives one separate exact production-
admission authorization. Repeat all gates into a fresh directory for exactly
one COLLECTED and separately unchanged `Ledger.measure`. Preserve all original
29 journals/mirrors and evidence; never promote a check-only receipt or rerun9.

Immediately continue within this same task to genuine Attempt10 plan/INTENT/
private version1 capsule and untouched approved notebook, all five exact
versioned Inputs, and verified private URL or actual ready-to-import `.ipynb`.
Start at ordinal203; aim200 images through402 only if measured safe calls/time/
quota/caps permit, otherwise the actual maximal contiguous safe batch. Deliver
the four Vietnamese UI steps below with verified artifacts. Owner alone presses
**Save Version > Save & Run All once**. Antigravity never GPU-submits. GitHub
403/rate-limit means immediate simple Owner UI guidance, not needless waiting
or invented readiness. Attempt9 COLLECTED+MEASURED and the real Attempt10 Owner-
run handoff remain required for integrated DONE; no additional research task/PR.

## Historical PR193: one Attempt9 admission → Attempt10 Owner-run task — 11/11/2026

[Directive6791205044](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6791205044)
supersedes the narrower PR192 implementation assignment below. BASE is merged
PR192/main `01130527c341fef9f01dbe383032da0b624593a5`; branch
`fix/attempt9-prepared-handoff`. This is one integrated task, with at most one
new code PR. Codex changes only the external collector's handoff admission,
focused synthetic tests and these documents, then stops at that Draft PR.
No Kaggle submit/GPU/inference/TEST, production collection or measurement is
performed in the implementation phase. Original Operator HEAD stays at
`4407dc939e045d115f4147e2d1d49605ec8b2f7a`.

`SAME_SCHEDULED_SLUG_V2` now accepts an original **PREPARED-only handoff with no
report**: unchanged persisted request, its bound correctly chained initial
PREPARED event, exact event fields/schema, no later event, no orphan report and
no submission directory. The request/package files remain in the immutable
snapshot; original authority, Input/capsule, provider, archive/raw/trace,
200-ordinal completion, ancestor/ledger/mirror and replay checks still run.
PREPARED is a local preparation state, never a provider-completion verdict.
Do not append a fake BLOCKED report to satisfy collection. The earlier workaround
was [revoked6791113699](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6791113699).

If genuine BLOCKED reports already exist, preserve them. V2 permits PREPARED
followed by correctly chained BLOCKED report events only; each must reference
its original numbered report with matching checksum, status and request/source
bindings. Repeated genuine BLOCKED reports are retained and verified, including
earlier reports. Unknown/extra events, unreported BLOCKED events, fake status,
SUBMISSION_INTENT, submission files or unreferenced reports mean STOP. Do not
delete any event/report to make admission pass. Default `DISTINCT_SLUG_V1`
retains its existing BLOCKED requirement and historical preflight-failure
SUBMISSION_INTENT behavior; PREPARED-only is not admitted on V1.

The [authentic Owner V2 record6790846059](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6790846059),
[PR192 audit6790628819](https://github.com/tantdna2/SafeShift/pull/192#issuecomment-6790628819)
and [PR192 tool release6790859119](https://github.com/tantdna2/SafeShift/pull/192#issuecomment-6790859119)
remain immutable. Do not request a replacement Owner factual record for this
code correction. Changed factual evidence requires STOP and truthful reassessment.
PR192's release cannot authorize changed script bytes. After direct ChatGPT
review, one focused independent audit in a new Antigravity auditor session
distinct from `operator-asus-win`, separately authorized ordinary two-parent
merge and ChatGPT postmerge verification, ChatGPT must publish a **new exact V2
tool release** binding this PR/merged script, its actual audit and the existing
authentic Owner V2 locator. Audit/merge/release are not issued by Codex.

### Same-task operational continuation after the review gate

The original `operator-asus-win` session retrieves the reviewed tool separately
under ignored reviewed-tools, checks its new release/hash, then rechecks original
source/authority, single open journal29 INTENT and all 29 mirror-equal journals,
no API/duplicate submission, PRIVATE v1/latest1 provider/code/five versioned
Inputs/capsule, saved ZIP/sidecar/raw/trace and ancestors. Use the V2 command below
with a **new** tool locator/path and fresh isolated `--check-only` evidence path.
Send its actual `READ_ONLY_VERIFIED` receipt to ChatGPT for the admission verdict.
Only after exact production authorization, repeat every gate in a distinct fresh
directory for one mirrored COLLECTED (normally journal30), then separately run
unchanged original `Ledger.measure` on that collected ZIP (normally journal31),
after checking that no valid MEASURED already exists. Never promote a check-only
receipt directly, fabricate submission events/measurement or rerun Attempt9.
Verify closed INTENT, sealed lineage, journal/mirror bytes, actual summary/budget
and measured `safe_calls`/`minimum_seconds`.

After actual COLLECTED+MEASURED PASS, continue this **same task** with unchanged
`scripts.train3763_campaign plan --mode resume`. Stage Attempt10 for original
NOT_ATTEMPTED ordinals203..402 only when measured safe calls are at least200
and seconds/caps/O5 quota/expiration/disk gates permit. Otherwise stage one maximal
contiguous safe batch starting at203 and report its exact count/end and limit.
Prepare one authentic new INTENT, fresh handoff, the actually created/verified
private version1 capsule `nguynanhtn/safeshift-capsule-ivl35-attempt10`, four
unchanged pinned Inputs plus that capsule, and the unchanged approved notebook.
Do not assume the candidate Attempt10 URL exists or claim a capsule was uploaded
without official pinned SDK evidence.

Antigravity may prepare/publish a private notebook only if that operation does
not execute GPU or create a completed version. Deliver its verified URL, or the
actual ready Owner-importable `.ipynb` path if publishing would execute; include
the verified capsule URL/version, all five exact Input refs, runtime Input and
notebook SHA proofs. Settings: Private, Python, Internet On, GPU T4 x2, no Auto-run.
Owner alone presses Run. Deliver these four Vietnamese UI steps with the actual
verified artifacts once ready:

1. Mở notebook Private đã xác minh, hoặc import file `.ipynb` đã bàn giao.
2. Gắn đúng năm Input/version đã liệt kê, gồm capsule Attempt10 mới đã xác minh.
3. Kiểm tra Private, Python, Internet On, GPU T4 x2 và giới hạn batch được giao.
4. Chọn **Save Version > Save & Run All đúng một lần**, rồi gửi URL/version khi xong.

On GitHub API403/rate-limit, provide the UI steps immediately; do not wait merely
to explain them, pretend missing authority/journal/capsule is ready or GPU-submit
as a substitute. **The integrated task is not DONE at code/Draft/merge:** actual
Attempt9 admission+measurement and the valid Owner-run Attempt10 handoff remain
required. A failed genuine gate means BLOCKED with evidence, no workaround or
scientific upgrade.

## Historical PR192 implementation scope and V2 contract

[Directive6789215420](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6789215420)
authorizes one code-only Draft PR from BASE
`4c68728cbcc26c0722520731d351cbe3fc23b6be`. It does **not** release collection.
Keep the original Operator checkout clean at
`4407dc939e045d115f4147e2d1d49605ec8b2f7a`, all 29 journals/mirrors, the original
request/capsule/handoff and saved ZIP/sidecar/log. No rerun, new version, Attempt10,
GPU, inference, TEST, production ledger append or measurement in this code task.

The new explicit `--mode SAME_SCHEDULED_SLUG_V2` admits a truthful Owner UI run
on `request.job`. Default `DISTINCT_SLUG_V1` retains Attempt8's V1 schemas and
distinct-slug/original-job-absent requirements. Existing Owner/tool comments,
locators and deployed files remain immutable; old releases cannot authorize the
new script bytes or V2 mode. Historical Attempt8 operational snapshots below are
not current campaign accounting or an Attempt9 release.

For Attempt9, **operator-reported, not independently verified by this code task**:

| Required reconciliation target | Reported identity |
| --- | --- |
| Original open INTENT | journal29; digest `ed136cc40da8b417399fee80bbfed6d1cf5e607f4f7898c99604c0c7ecbcf314` |
| Scheduled and actual job | `nguynanhtn/safeshift-train3763-ivl35-train3763-9` |
| Provider | kernel `144292982`, version1 and latest1, PRIVATE, COMPLETE, no failure, dual T4 |
| Saved archive | `ivl35-train3763-9-9d5c43034e8c47e08ff9acfefb2a58d5.zip` |
| ZIP bytes / SHA256 | `705975856` / `e26dcec9b26cd12554bec208d49a74616fe4f8bb5af0ab145a3351de9092c895` |
| ZIP members / calls | `8264` / `200`; exact TRAIN ordinals3..202 |
| Approved notebook executable code | `a5e5583e8739092836fed1170f9105374dee6ebf4926adbc97013c9bd1fd1a65` |
| Input references | All **five original pinned versioned refs** from the unchanged request; no substitutions |

The reported 200 SUCCESS are technical predictions, not accuracy. There are only
3 formally collected successful images until this result is admitted. The
reported 203 total / 3560 remaining are conditional; do not publish them as ledger
counts. The collector preserves every scheduled SUCCESS **or INVALID**, without
selecting by label correctness. Partial calls, TECHNICAL_ERROR or NOT_ATTEMPTED
within the scheduled shard block V2; preserve them for read-only diagnosis.

### V2 authentic Owner and reviewer records

PR192 introduced the following **factual record** schema on Issue180,
marker `SAFESHIFT_TRAIN3763_OWNER_MANUAL_V2` followed by exactly one fenced JSON
object. The authentic existing record linked above is retained for the current
task. This template is **not a posted assertion or release**. Replace every
placeholder with original authenticated values; `scheduled_ordinals` must be the
full JSON integer array `[3,4,...,202]`, never ellipsis or a string.

```json
{
  "campaign_sha256": "ORIGINAL_GRANT_SHA256",
  "intent_sha256": "ed136cc40da8b417399fee80bbfed6d1cf5e607f4f7898c99604c0c7ecbcf314",
  "request_sha256": "ORIGINAL_REQUEST_SHA256",
  "job": "nguynanhtn/safeshift-train3763-ivl35-train3763-9",
  "version": 1,
  "kernel_id": 144292982,
  "archive_sha256": "e26dcec9b26cd12554bec208d49a74616fe4f8bb5af0ab145a3351de9092c895",
  "archive_bytes": 705975856,
  "operator": "OWNER_UI_MANUAL",
  "mode": "SAME_SCHEDULED_SLUG_V2",
  "ledger_events": 29,
  "ledger_head_sha256": "ed136cc40da8b417399fee80bbfed6d1cf5e607f4f7898c99604c0c7ecbcf314",
  "plan_sha256": "ORIGINAL_PLAN_SHA256",
  "scheduled_ordinals": ["REPLACE_WITH_ALL_200_JSON_INTEGERS_3_THROUGH_202"],
  "input_sources": {
    "dataset_sources": ["ALL_ORIGINAL_VERSIONED_DATASET_REFS"],
    "kernel_sources": ["ALL_ORIGINAL_VERSIONED_KERNEL_REFS_IF_ANY"],
    "execution_request_sha256": "ORIGINAL_EXECUTION_REQUEST_SHA256"
  },
  "no_api_submission": true,
  "no_other_job_or_version": true
}
```

All fields are required; extra fields (including V1 `original_job_not_run`) fail.
Use an empty array for original empty `kernel_sources`. The Owner's exact
comment ID/body SHA locator authenticates the assertion. Request/plan/intent
digests bind original source, notebook, capsule, 200 IDs, limits and history;
the current last event must still be this INTENT. Never claim no API submission
if ledger PUSH_INTENT/SUBMITTED or handoff SUBMISSION_INTENT/submission files exist.
Any such ambiguity means STOP; do not delete events/files to obtain PASS.

Following direct ChatGPT GitHub review, an independent Antigravity audit in a
**new session separate from `operator-asus-win`**, separately authorized merge and
postmerge verification, an authenticated reviewer publishes on the new PR:
marker `SAFESHIFT_TRAIN3763_MANUAL_ADAPTER_V2` and exactly this schema:

```json
{
  "implementation_pr": "REPLACE_WITH_JSON_INTEGER_NEW_PR",
  "reviewed_head": "EXACT_40_HEX_REVIEWED_HEAD",
  "merged_sha": "EXACT_40_HEX_AUTHORIZED_MERGE",
  "script_sha256": "EXACT_MERGED_SCRIPT_SHA256",
  "audit": {"comment_id": "JSON_INTEGER_AUDIT_ID", "body_sha256": "AUDIT_COMMENT_BODY_SHA256"},
  "owner": {"comment_id": "JSON_INTEGER_EXISTING_OWNER_ID", "body_sha256": "EXISTING_OWNER_COMMENT_BODY_SHA256"},
  "scope": "SAME_SCHEDULED_SLUG_COLLECTION_ONLY"
}
```

The independent audit comment on the same PR uses marker
`SAFESHIFT_TRAIN3763_MANUAL_ADAPTER_V2_AUDIT`, with exactly `reviewed_head`,
`script_sha256`, `status: "PASS"`, `independent: true`. Reviewer/auditor logins
must belong to the original grant's respective allowlists. Audit and release
comments must differ; PR merge/head and local script hash must match. The V2
reviewer additionally pins the **exact existing Owner locator**, so another assertion
cannot silently broaden the released collection. No such records are issued here.

### V2 gates, read-only preflight and one append after release

The collector holds original ledger/handoff locks across verification and
append. Its bounded account inventory requires the scheduled slug **present**,
all known campaign refs accounted for, prior actual manual/API jobs terminal,
aborted slugs absent, and no unknown campaign job. Pinned-v1 and latest GetKernel
must agree on exact kernel/ref/privacy/code/metadata/Input attachments; COMPLETE
cannot have a failure message. Five pinned versions remain bound by the original
request, Owner record, private capsule bytes and worker Input receipts.
GetKernel's unversioned attachment list alone never proves versions.

Unchanged `verify_bundle`, `verify_native_custody`, full raw/logit/trace/selection
checks, Input byte receipts and sealed parent history all run. V2 additionally
requires one native call for every scheduled record in exact order, with no
missing/extra ordinal. Independent provider ZIP/sidecar/log download retains the
existing HTTPS/origin/path/time/disk/byte caps and no redirects/retry. Both the ZIP
SHA and **preserved sidecar bytes** must agree; a semantically similar replacement
sidecar is BLOCKED. Provider/inventory/authority/source and local history/handoff
are reobserved. Evidence is isolated and create-only. Known limits remain the
trusted local operator/mirror model, remote metadata omissions explicitly recorded
as before, OS-managed DNS and no global exactly-once or hardware attestation.

Only after the authentic release, the **existing** Operator session runs the
reviewed standalone script against the original checkout. First use a fresh
evidence directory with `--check-only`; it performs the same authenticated gates
and downloads but returns `READ_ONLY_VERIFIED`, `ledger_appended=false`, no event
digest, and no measurement. This command is future operations guidance only:

```powershell
$repo = (Get-Location).Path
$tool = Join-Path $repo 'data/processed/reviewed-tools/attempt9/reconcile_train3763_manual.py'
& data/processed/operator-venv/Scripts/python.exe -B $tool `
  --approved-repo $repo --mode SAME_SCHEDULED_SLUG_V2 --check-only `
  --ledger data/processed/train3763-campaign/ledger `
  --handoff data/processed/train3763-campaign/attempt-9 `
  --archive '<relative-path-to-preserved-Attempt9-ZIP>' `
  --owner-locator data/processed/attempt9-owner-v2-locator.json `
  --tool-locator data/processed/attempt9-tool-v2-locator.json `
  --evidence data/processed/attempt9-check-only-v2
```

On PASS, repeat **every gate**, without `--check-only`, into a different fresh
directory such as `data/processed/attempt9-collection-v2`. There is no "promote
receipt" bypass. Append exactly one mirrored `COLLECTED`, carrying
`manual.provenance=OWNER_UI_MANUAL`, `manual.mode=SAME_SCHEDULED_SLUG_V2` and actual
provider identity; no PUSH_INTENT/SUBMITTED/refund is synthesized. Existing
`Ledger.measure` may then be invoked separately on the collected provider ZIP,
using the reviewed original limits, after checking for an existing measurement.
Do not assume MEASURED or automatically stage/run another shard.

Any timeout, partial, changed authority/provider/history, wrong code/Input/capsule,
duplicate attribution or mirror failure is STOP/BLOCKED. Keep originals, partials
and sanitized failure receipts. Existing evidence directories cannot be reused;
no automatic overwrite, retry or mirror repair. If an append is torn, read-only
reconciliation must determine the true journal state before any further action.

Tests remain in `tests/test_train3763_manual.py`, including V1 regression, both
modes' orchestration/rollback/partial paths, real pinned SDK serializers with HTTP
doubles, and 200-ordinal CPU controller/raw/trace replay. This is software
evidence, not independent audit, live provider verification or scientific PASS.

## Historical Attempt8 implementation and operational snapshots

Authority: [ChatGPT directive6736965547](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6736965547).
Implementation is **CPU SOFTWARE PREPARATION**, one Draft PR. ChatGPT must review
the exact GitHub diff/tests, then authorize an independent Antigravity audit and
separately authorize merge; ChatGPT verifies that merge. This document supplies
no execution release, audit PASS, merge permission or scientific qualification.

## Source and authority boundaries

### PR191 self-review continuation — 10/11/2026

Owner's continuation keeps this same branch/Draft PR and authorizes bounded,
read-only inspection/download of the existing Attempt8 v1 outputs. No job rerun,
GPU, inference, submit or production append is authorized or performed. Unlike
the initial CPU-only snapshot below, the current tool has directly downloaded
the original ZIP/sidecar/provider log and replayed the saved provenance checks.
See [final continuation evidence](research/TRAIN3763_MANUAL_CDN_REVIEW_20261110.md).

The actual CDN token is one path segment with five dot-separated fields, the
second empty: `<header>..<iv>.<ciphertext>.<tag>`. PR191's first regex incorrectly
rejected it. The current validator supports that observed Base64url-style shape
and the earlier simple opaque token form. It never decodes/trusts token claims;
the exact origin/path/name and original archive SHA/authority gates remain.
Other unobserved token shapes and punctuation remain BLOCKED, including escapes,
`=`/`;`, slashes, traversal and noncanonical dot fields. Never publish real tokens.

### CDN companion fix — 09/11/2026 (review/audit/merge pending)

[Directive6739558259](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6739558259)
starts one collection-only Draft PR from merged PR190/main
`519cb16a8f0e66ab03d5a1b0f1ed3981261ca6f6`. Operator reports that the existing
Attempt8 output listing returns the exact `www.kaggleusercontent.com` CDN route
described below. This software task verifies sanitized CPU fixtures, not the live
URL or provider; no submit, GPU, inference, production collection or measurement.

The old [PR190 tool release6739152747](https://github.com/tantdna2/SafeShift/pull/190#issuecomment-6739152747)
pins script SHA256 `9fa7259b51e7e4caabfd1dfbfdbadd51f3cd569c0fd9f58a70b334150fcc602b`.
It cannot authorize this changed companion. Do not edit the approved Operator
checkout or run new bytes against that old locator. Direct ChatGPT GitHub review,
a focused independent Antigravity security/provenance audit of this network
allowlist change, separately authorized merge and postmerge SHA/parents/tree
verification must precede a **new authentic MANUAL_ADAPTER_V1 tool release**.
Only then may Operator replace the standalone tool using its reviewed SHA.

Keep the original `BLOCKED.json`, every partial and every prior evidence directory.
Use a **fresh create-only evidence directory** for collection of the same saved
Owner job/ZIP. Do not rerun ordinal2. The existing [Owner factual attestation6739339869](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6739339869)
remains applicable unless its factual data changed. No new scientific decision,
213-call official measurement or 200-image shard release follows from this fix.

`scripts/reconcile_train3763_manual.py` is an external collection companion,
deliberately outside `internvl3763.source_spec()`. No runtime manifest, native
code, notebook, parser, prompt, HNLO, labels, TRAIN/TEST, roster, metric or science
decision changes. The original `Ledger` implementation is unchanged. One normal
mirrored `COLLECTED` event carries an explicit `manual.provenance=OWNER_UI_MANUAL`
and the actual provider slug/version/kernel ID; no historical request is renamed.
`manual.original_job` retains the scheduled slug. No `PUSH_INTENT`, `SUBMITTED`,
refund, replacement INTENT or reconstructed submission claim is generated.

The original `histories()`, `open_intent()`, `summary()`, `measure()` and planner
already consume this event type. That compatibility is intentional; the extra
manual provenance is retained inside the event, not hidden in a side report.
The existing ledger remains one trusted local writer with an independent mirror,
create-only files, chain checks, OS lock and no global exactly-once assertion.
The companion holds both campaign and handoff locks, preserves original BLOCKED
handoff bytes, rechecks authority/source/provider/history before append and stops
on a torn mirror. Never remove a journal or repair a mirror automatically.

Before/after runtime source SHA256 must remain
`f062f170c38f2f70c21c6f7462d9408e5a5ea6862b923a40cf9e58b75489239d`;
science SHA256 must remain
`ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`.
Equal source hash alone is insufficient: the original operator checkout must
still be clean at exact technical merged commit
`4407dc939e045d115f4147e2d1d49605ec8b2f7a`, with its approved notebook/runtime
commit and authentic AUDIT_V1, TECHNICAL_V1 and O5_EXECUTION_V1 bindings.
Moving the operator HEAD to the new companion PR merge **blocks admission**.
Never loosen that check or edit the source lock to make it pass.

After authorized merge, obtain the exact reviewed companion file from a separate
tools checkout, verify its SHA against the review attestation, and execute it by
absolute file path with `--approved-repo` pointing to the original operator
checkout. It imports runtime/campaign modules from that original checkout.
Keep the registered ledger at its original canonical host/path; do not copy it
into another worktree or machine. The reviewed companion may also be kept under
an ignored private tools directory; do not overlay protected Python modules.
No checkout/deployment/production collection is performed by this software task.
If these original source/commit constraints cannot be met, **BLOCKED**: retain
ordinal2 evidence and seek exact technical requalification/new measurement for
the changed runtime. Do not transfer the one-image measurement to another source.

## Required authentic records

`campaign.record()` authenticates each locator's exact GitHub comment ID/body SHA
and rejects duplicate JSON keys/nonfinite values. Locators are private JSON files
with `comment_id` and `body_sha256`. Do not populate them with invented IDs/hashes.

After review, independent audit and authorized merge, a login allowed by the
original grant's `review_logins` publishes `SAFESHIFT_TRAIN3763_MANUAL_ADAPTER_V1`
followed by one fenced JSON record on **this PR**:

```json
{
  "implementation_pr": "INTEGER_NEW_PR_NUMBER",
  "reviewed_head": "EXACT_REVIEWED_40_HEX_HEAD",
  "merged_sha": "EXACT_AUTHORIZED_40_HEX_MERGE",
  "script_sha256": "SHA256_OF_REVIEWED_COMPANION_FILE",
  "audit": {"comment_id": "INTEGER_AUDIT_COMMENT_ID", "body_sha256": "AUDIT_BODY_SHA256"},
  "scope": "MANUAL_COLLECTION_ONLY"
}
```

The audit locator must refer to a different authentic comment on the same PR,
by a login in the original grant's `audit_logins`, with marker
`SAFESHIFT_TRAIN3763_MANUAL_ADAPTER_V1_AUDIT` and one JSON record containing
`reviewed_head`, `script_sha256`, `status: "PASS"`, `independent: true`.
The PR must actually be merged to main at those exact identities. Strings above
are template placeholders; numeric fields must be JSON integers in real records.
This is collection-tool review authority, not a new native execution qualification.

Owner records the fact of their UI run on **Issue180**, under marker
`SAFESHIFT_TRAIN3763_OWNER_MANUAL_V1`, followed by one fenced JSON object:

```json
{
  "campaign_sha256": "ORIGINAL_GRANT_SHA256",
  "intent_sha256": "EXACT_EXISTING_INTENT_SHA256",
  "request_sha256": "EXACT_ORIGINAL_REQUEST_SHA256",
  "job": "nguynanhtn/notebook4e07cfa2d0",
  "version": 1,
  "kernel_id": "INTEGER_ACTUAL_PROVIDER_KERNEL_ID",
  "archive_sha256": "3b30e0bcff7f5aa986b411c5a5d85798c7f63b7aa3e5302cc3a6d3c4867c7493",
  "archive_bytes": 5646071,
  "operator": "OWNER_UI_MANUAL",
  "original_job_not_run": true
}
```

This attests historical facts, not renewed permission for each continuation.
Only the authentic Owner login is accepted. Operator reports/ChatGPT summaries
are not substitutes. Owner may post through GitHub UI when API is rate-limited.
Publication contains identities/hashes only; never upload the private ZIP, raw,
images, checkpoint, dataset, credentials or machine paths.

## Acceptance gates and known limits

The companion requires exactly one open original INTENT, its unchanged request,
complete sealed ancestors and a checksum-verified BLOCKED handoff. A handoff-only
`SUBMISSION_INTENT` preceding failed preflight may remain, as in Attempt8; any
ledger `PUSH_INTENT`/`SUBMITTED` means possible API submission and **STOP**.
The original scheduled slug must be absent in complete bounded Owner inventory;
all known campaign jobs must be accounted for, including aborted-slug absence.
Previous actual manual slugs are checked as themselves, never as scheduled slugs.
Provider identity/terminal state/source/inputs of known predecessors are checked.

The actual Owner job must be private, current and pinned version1, correct kernel
ID, COMPLETE with no conflicting failure and exact approved notebook code. That
code embeds and hash-verifies the complete runtime payload/manifest; it binds the
source and runtime independently of display metadata. If Kaggle retains SafeShift
notebook metadata, it must match; provider omission is explicitly recorded as
`ABSENT_EXECUTABLE_CODE_BOUND`. UI changes to execution counters/output metadata
are permitted; the receipt records the actual remote notebook digest separately
from the full approved notebook digest. Accelerator must remain dual-T4
`NvidiaTeslaT4`; extra/duplicate/forged Input attachments are rejected.

GetKernel returns **unversioned attachment slugs**. The companion does not pretend
this proves exact Input version numbers. The request/Owner attestation pins the
versions; provider private versioned capsule bytes must exactly contain the
original request+INTENT. Sealed worker evidence must match original TRAIN master/
projection, 3763 verified images, zero changed/missing/duplicate IDs, locked
checkpoint metadata and both actual streamed shard SHA/length receipts, plus
pinned offline Python original and transport SHA/lengths with zero Python downloads.
No original Input/weights is reuploaded or live model preflight run. This remains
a trusted single-operator custody model, not remote hardware attestation.

The original `verify_bundle()` checks archive SHA/sidecar, bounded member paths,
full checksums/CRC, exact plan/cohort/source/configuration, raw-before-parse,
every retained full-vocabulary vector/hash, mask/greedy trace and native claims.
The companion also checks the complete sealed execution request, grant/INTENT,
launch/worker/load/call claims and original history chain. Only a verified native
PASS with at least one call is accepted by this initial manual route. Failed or
ambiguous manual outputs are retained BLOCKED for read-only reconciliation;
never resubmit them automatically.

The same ZIP and sidecar must be independently downloaded from the actual pinned
provider job and match the Owner's existing ZIP. Official SDK listing is bounded
to 256 outputs per page, with the current bounded complete-pagination contract
above; the exact ZIP pair and provider log
are required. Downloads accept exactly two HTTPS origins and canonical paths:

- `https://www.kaggleusercontent.com/kf/<positive-decimal-run>/<opaque-token>/<exact-filename>`:
  no query; token is either ASCII letters/digits/`_`/`-` or the observed five-part
  `<header>..<iv>.<ciphertext>.<tag>` form, with each nonempty field using that same
  alphabet. The ZIP or `.zip.sha256.json` filename exactly matches both the SDK
  listing and expected name.
- `https://storage.googleapis.com/<canonical-output-path>/<exact-filename>?<signed-query>`:
  existing exact GCS origin with a nonempty query; final filename is also exact.

URLs are bounded to 16384 printable ASCII characters. No userinfo, ports (even
443), apex/subdomain/suffix host variants, fragments (even empty), backslashes,
path escapes/encoded separators, empty/dot/traversal path segments or parameters
are accepted. Both URLs are validated before any output GET; no token/URL is
stored in receipts or error messages. Other origins or shapes remain BLOCKED.

GET uses a fresh anonymous session with `trust_env=False`, no Authorization,
proxy/netrc credentials, redirects, retry or resume. Connect/read timeouts are
explicitly at most 10/30 seconds and shrink to half the remaining shared budget
when needed. The 240-second monotonic budget covers both file GETs and is checked
before each GET, after headers, at each stream chunk and EOF; an overrun never
passes verification. A deadline watchdog shuts down registered TLS sockets during
slow response headers/body, including byte-by-byte trickles that defeat an idle
timeout. It is cancelled and joined on success/failure before return. Late
connection completion is rejected. Normal TLS certificate verification remains
enabled; no global urllib3 pool registry is changed. System DNS resolution remains
OS-managed; this watchdog is not a process-level kill of a blocked resolver.
SDK verbose response printing and stdlib transport diagnostics are suppressed
while credentials/bearer paths could be present; logging state is restored.
Identity content encoding is required. Declared and actual stream
bytes are capped at the attested ZIP length/4096-byte sidecar. ZIP SHA256 must
match the supplied archive, Owner attestation and downloaded sidecar. Declared
Content-Length, when present, must equal received bytes. Downloads use exclusive
`xb` and fsync retained partial bytes even on streaming failure.
No failed download appends a journal. Originals,
partial downloads and failures remain untouched. Identity/inventory are observed
again before the single append; authority/source/handoff are also rechecked.

## Owner UI-first operations

1. Antigravity prepares the exact source-bound request, reserves the finite
   INTENT once, and prepares the private per-attempt capsule/notebook/Input
   checklist under the current release. Keep original Inputs and source pins.
   Keep the genuine PREPARED-only handoff for V2; do not create a fake BLOCKED
   report, call `operate(..., "start")` or SDK push. V1's existing truthful
   BLOCKED handoff remains historical evidence, never a template for fake status.
   After previous manual collection, ordinary planning uses the original Ledger;
   **do not use the old API-submit inventory**, which expects previous scheduled
   slugs to exist. The companion inventory understands actual manual predecessors.
2. If GitHub API is throttled, retain the exact prepared package and tell Owner
   how to open the approved private notebook, attach the exact versioned Inputs
   and capsule, verify T4/settings/caps, then press Save Version/Run manually.
   Do not change privacy, Source/Input/science or bypass missing technical
   authority. If authority cannot be authenticated, preparation stays BLOCKED;
   API throttling alone is not evidence of permission. Use existing signed-off
   instructions; no newly fabricated GitHub approval.
3. Owner operates Kaggle and reports actual slug/version and completion.
   Antigravity may monitor for <=15 minutes, persist RUNNING_UNVERIFIED in a
   separate operational report, and exit without cancellation/resubmit/background
   AI. Keep the original PREPARED or truthful BLOCKED snapshot unchanged during collection.
   Resume the same conversation on Owner's next message for terminal collection.
4. Antigravity collects and pins the Owner factual attestation, then runs the
   reviewed companion using the existing isolated official SDK. Example **only
   after the review/audit/merge gates** (paths relative to the original repo):

   ```powershell
   $repo = (Get-Location).Path
   $tool = Join-Path $repo 'data/processed/reviewed-tools/pr191/reconcile_train3763_manual.py'
   & data/processed/operator-venv/Scripts/python.exe -B $tool `
     --approved-repo $repo `
     --ledger data/processed/train3763-campaign/ledger `
     --handoff data/processed/train3763-campaign/attempt-8 `
     --archive data/processed/manual-run-20261109-notebook4e07cfa2d0/ivl35-train3763-8-6123c4cb8b134abe98dbf857286ff4e1.zip `
     --owner-locator data/processed/manual-collection-owner-locator.json `
     --tool-locator data/processed/manual-collection-tool-pr191-locator.json `
     --evidence data/processed/manual-collection-attempt8-pr191
   ```

   The old `manual-collection-attempt8-verified` directory already contains BLOCKED
   evidence. Do not reuse/delete/overwrite it, the old locator or old standalone
   tool. The example uses distinct PR191 tool/locator/evidence paths, populated
   only after the new authentic release. If the new evidence directory also
   exists, preserve it and use another fresh name consistently in collection and
   measurement; never clear a directory to retry.

5. On PASS, `COLLECTED` contains actual Owner provenance and the verified provider
   ZIP path. Run the **unchanged** `Ledger.measure` on that exact ZIP from the
   original clean approved checkout. The normal CLI is:

   ```powershell
   & data/processed/operator-venv/Scripts/python.exe -B -m scripts.train3763_campaign measure `
     --directory data/processed/train3763-campaign/ledger `
     --archive data/processed/manual-collection-attempt8-pr191/ivl35-train3763-8-6123c4cb8b134abe98dbf857286ff4e1.zip `
     --seconds 7200
   ```

   Inspect current events first: if that ZIP/source already has a valid MEASURED,
   reuse it, do not append duplicate measurements. No MEASURED can be created
   before accepted COLLECTED/provider COMPLETE/verifier PASS. No automatic measure
   is bundled with append: a measurement error leaves the truthful COLLECTED and
   preserved errors available for diagnosis. Envelopes remain source-bound.
6. Recheck histories/summary: ordinal0/1 remain prior SUCCESS; legitimately
   accepted ordinal2 SUCCESS gives 3760 NOT_ATTEMPTED and resume starts ordinal3.
   No handwritten history, replay, GT/parser rescue, pooling or scientific upgrade.
   A new specific ChatGPT release is still required to prepare the first 200-image
   notebook (ordinals3..202), with measured time/disk/archive gates. No 200-image
   preparation, GPU run or submission is authorized by this implementation PR.

## Exact current Attempt8 status

Read-only local inspection confirmed 26 journals, last INTENT SHA256
`f5175dde61b7068c89e7e42c2013a72136a1cf2b271853160c1aa82866e48933`,
scheduled slug `nguynanhtn/safeshift-train3763-ivl35-train3763-8`, original
approved source/commit above and existing BLOCKED handoff. Existing 512 campaign
and supplied-output files are fingerprinted privately before/after this task.
No production ledger/mirror/handoff append or live Kaggle observation occurs here.

The supplied saved ZIP additionally passed read-only CPU `verify_bundle` and
native-claim/Input receipt checks: exact SHA, 105 members, one SUCCESS on ordinal2,
3762 NOT_ATTEMPTED in this job. This does not re-observe the provider or append
COLLECTED/MEASURED. Actual provider
identity/bytes/absence and authentic Owner/tool attestations remain **NOT_VERIFIED**
by this task. The standalone reported 213-call estimate remains provisional until
the unchanged Ledger.measure accepts the collected ZIP. A 213-call envelope is
not a 200-call release and not evidence that full 3763 will fit weekly quota.

Reservation accounting retains all Attempts1–8:25200 +3600 = **28800 physical
GPU-seconds**, leaving **401200/430000**, assuming the 26-event history and no new
reservations. Never refund Attempt8 or report 404800 after its INTENT. A separately
released 200-call/7200-second job would reserve 14400, leaving 386800. No reservation
or budget amendment is made in this programming task.

Tests: `python -B -m unittest discover -s tests -p test_train3763_manual.py -v`;
repeat in the existing `data/processed/operator-venv/Scripts/python.exe` to cover
the real pinned SDK serialization with synthetic HTTP and forbidden sockets.
The suite is also included in `scripts.qualify_internvl3763`. CPU tests are not
Antigravity's independent audit or actual provider verification.
