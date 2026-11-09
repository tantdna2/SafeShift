# Owner UI Kaggle collection — 09/11/2026

Authority: [ChatGPT directive6736965547](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6736965547).
Implementation is **CPU SOFTWARE PREPARATION**, one Draft PR. ChatGPT must review
the exact GitHub diff/tests, then authorize an independent Antigravity audit and
separately authorize merge; ChatGPT verifies that merge. This document supplies
no execution release, audit PASS, merge permission or scientific qualification.

## Source and authority boundaries

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
to 256 outputs with no pagination ambiguity; the exact ZIP pair and provider log
are required. Downloads use anonymous HTTPS to `storage.googleapis.com`, no
redirect, credentials, retries or resume, at most the attested ZIP length/4096-byte
sidecar and 240 seconds of streaming, with finite connection/read timeouts.
Any other storage host is BLOCKED pending reviewed transport support. Originals,
partial downloads and failures remain untouched. Identity/inventory are observed
again before the single append; authority/source/handoff are also rechecked.

## Owner UI-first operations

1. Antigravity prepares the exact source-bound request, reserves the finite
   INTENT once, and prepares the private per-attempt capsule/notebook/Input
   checklist under the current release. Keep original Inputs and source pins.
   Create a BLOCKED handoff report with reason `OWNER_UI_RUN_REQUIRED` for a
   deliberate UI handoff; do not call `operate(..., "start")` or SDK push.
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
   AI. Keep the original handoff BLOCKED snapshot unchanged during collection.
   Resume the same conversation on Owner's next message for terminal collection.
4. Antigravity collects and pins the Owner factual attestation, then runs the
   reviewed companion using the existing isolated official SDK. Example **only
   after the review/audit/merge gates** (paths relative to the original repo):

   ```powershell
   $repo = (Get-Location).Path
   $tool = Join-Path $repo 'data/processed/reviewed-tools/reconcile_train3763_manual.py'
   & data/processed/operator-venv/Scripts/python.exe -B $tool `
     --approved-repo $repo `
     --ledger data/processed/train3763-campaign/ledger `
     --handoff data/processed/train3763-campaign/attempt-8 `
     --archive data/processed/manual-run-20261109-notebook4e07cfa2d0/ivl35-train3763-8-6123c4cb8b134abe98dbf857286ff4e1.zip `
     --owner-locator data/processed/manual-collection-owner-locator.json `
     --tool-locator data/processed/manual-collection-tool-locator.json `
     --evidence data/processed/manual-collection-attempt8-verified
   ```

5. On PASS, `COLLECTED` contains actual Owner provenance and the verified provider
   ZIP path. Run the **unchanged** `Ledger.measure` on that exact ZIP from the
   original clean approved checkout. The normal CLI is:

   ```powershell
   & data/processed/operator-venv/Scripts/python.exe -B -m scripts.train3763_campaign measure `
     --directory data/processed/train3763-campaign/ledger `
     --archive data/processed/manual-collection-attempt8-verified/ivl35-train3763-8-6123c4cb8b134abe98dbf857286ff4e1.zip `
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
