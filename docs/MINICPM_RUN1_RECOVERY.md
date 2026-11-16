# MiniCPM Run1 recovery and one Codex launch — V3

[Owner directive6914854993](https://github.com/tantdna2/SafeShift/pull/198#issuecomment-6914854993)
starts this new session from merged PR198/main
`507e9817b91054fa7af324c6a915c35d56b5acf1`. One branch/Draft PR covers the complete
fix and its deployment gates. Continue this same Codex session after review,
independent Antigravity audit, authorized merge and ChatGPT postmerge verification.
No additional standalone smoke or scientific cohort is introduced.

## Verified observations and unresolved history

The local original journal uses grant6911429335; its PUBLISHED reservation holds
1000 calls/28800 GPU-s. Run1's retained sealed supervisor and admit failure say
`UNIQUE_ORIGINAL_MOUNT_REQUIRED`. The selected direct TRAIN/master mount strings
do not match Kaggle's nested layout. No local native call is reported.

Two V2 release comments exist:6912703004 has an incompatible sizing object;
6912724858 has the required export/first-call/safety policy and is registered in
`minicpm-v2-2-journal`. Its ticket is also PUBLISHED/1000 calls/28800 GPU-s. The
retained V2 notebook log fails `MINICPM_STALE_PROVIDER_BEFORE_LAUNCH`. V3 grant
6913569723 is registered in `minicpm-v3-journal`, with a third RESERVED ticket
for1000 calls/28800 GPU-s and no publication event. No grant is assumed unused.

All three local journal/mirror byte pairs match. Their reservation total is
3000 calls/3 jobs/86400 physical GPU-seconds; old project cap72000. Native failures
and expiry do **not** refund reservations. Existing total_calls4500 also cannot
reserve another3763 calls after3000 held calls. No numerical replacement caps
are invented, and account quota is a separate provider constraint.

Read-only official SDK at this session observed account GPU quota
26745 used/0 reserved/108000 total, and189 owned notebooks across complete pages.
The exact three production slugs are absent; their direct status reads deny
`kernels.get`. Local downloaded logs therefore lack fresh authenticated terminal
provider custody. **BLOCKED** until the exact original notebook id/slug/version,
code/Inputs/output and account facts reconcile. A missing published job could
have run or changed/deleted its slug; absence is not a zero-call proof.

Local observations are preserved under ignored
`data/processed/minicpm-run1-recovery-20261116/`. Earlier failed read-only proxy
and empty-token diagnostics are not counted as provider success. SDK supports
empty terminal tokens and classic page fallback; repeated pages/tokens, wrong
account or incomplete inventory still STOP. No provider write was performed.

## Five nested Inputs

| Input | Pinned ref/version | Exact mount below `/kaggle/input` |
| --- | --- | --- |
| TRAIN | `nguynanhtn/inspecsafe-v1-kaggle/1` | `datasets/nguynanhtn/inspecsafe-v1-kaggle` |
| Master | `nguynanhtn/safeshift-pilot-input/1` | `datasets/nguynanhtn/safeshift-pilot-input` |
| Checkpoint | `nguynanhtn/safeshift-prepare-minicpm4/1` | `notebooks/nguynanhtn/safeshift-prepare-minicpm4` |
| Python | `nguynanhtn/safeshift-cpython3119-20240726/1` | `datasets/nguynanhtn/safeshift-cpython3119-20240726` |
| New capsule | exact signed `.../safeshift-minicpm-capsule-mcpm4-train3763-v3-4/1` | `datasets/nguynanhtn/safeshift-minicpm-capsule-mcpm4-train3763-v3-4` |

TRAIN/master bind the exact nested strings; capsule/Python/checkpoint markers
must uniquely resolve to their signed nested roots before admit. All original
master/projection/3763 ordered IDs/JPG SHA, model checkpoint, isolated Python/ABI,
storage/RAM/T4/CUDA, child authority, raw-before-parse and ZIP gates remain active.
TEST is closed. No image/checkpoint/Python reupload is needed.

## Authority and no-refund recovery

V2 `OWNER_MINICPM_TRAIN3763_SERIAL_UI_ONLY` stays UI-only. New record marker
`SAFESHIFT_MINICPM_FULLTRAIN_RECOVERY_RELEASE_V3`, schema
`safeshift-minicpm-fulltrain-recovery-release-v3`, authorizes
`OWNER_MINICPM_TRAIN3763_CODEX_SUBMIT_ONCE` only on the new reviewed implementation
PR. It binds final runtime/reviewed/merged source trees, original science/Input
scope, host/public key, finite caps/window and separate authentic approval
locators for source_review, independent_audit, merge, postmerge and O2–O6.
Root and approvals must be authentic Owner records on that new implementation PR.
Expired authority is usable only for terminal collection, never a new launch.

The required `recovery` snapshot binds **all three** original registered
journal/mirror paths/heads, original live grant locators, full signed old tickets,
publication states, resource sums and exact terminal/absence evidence hashes.
The old public key and science must agree; only source provenance and nested
mount layout can differ. No fourth campaign is accepted. Original/V2/V3 grants,
keys, raw and journals are not rewritten. A new reservation is appended to the
existing V3 pair, with global serial4 and all3000 calls/86400 GPU-s carried forward.

`FAILED_PRE_NATIVE` requires exact remote notebook/version/Private/Inputs,
terminal provider state, full bounded output inventory, intact supervisor ZIP/
sidecar/request/ticket/claims, no native/load/call/attempt and a recorded failure.
The source-bound pre-launch expiry exception has no supervisor ZIP; it requires
the exact terminal provider log/code and expiry-before-launch error. Native,
partial attempt, unknown claims, extra ZIP, missing sidecar or ambiguous provider
remains STOP. All received partial bytes/logs are retained. These receipts are
operational classifications, never scientific results or budget credits.

`EXPIRED_UNPUBLISHED` additionally requires original journal state RESERVED
without a PUBLISH_INTENT, expired ticket and authenticated complete job absence.
PUBLISH_INTENT/PUBLISHED plus missing job always needs read-only reconciliation.

The current86400 reservation already exceeds72000. An actual Owner budget
amendment is required before any positive remaining budget can exist. Its separate
PR198 Owner record uses marker `SAFESHIFT_MINICPM_PROJECT_BUDGET_AMENDMENT_V1` and
an exact object with `previous_gpu_seconds:72000`, explicitly decided
`total_gpu_seconds`, complete `reserved` totals, ordered `journal_heads`, and
`refund:false`. The new release binds its locator. This code does not issue that
decision. O5/new release also binds finite calls/jobs and coverage capacity; no
old cap is reset and no new campaign makes resources available.

## Operations after the internal review/merge gates

Use the existing pinned operator venv (kaggle2.2.5/kagglesdk0.1.38/requests2.34.2).
All commands are repository-relative. `inspect` is offline, read-only and explicitly
unauthenticated. `reconcile` reads official provider/Owner records and preserves
new local evidence only; it does not reserve/upload/submit or repair old journals.

```powershell
$py = 'data/processed/operator-venv/Scripts/python.exe'
& $py -B -m scripts.minicpm_fulltrain_recovery inspect
& $py -B -m scripts.minicpm_fulltrain_recovery reconcile --output data/processed/<new-reconciliation>
```

After genuine reconciliation, `prepare-spec --initial-spec <old-spec> --calls
<approved-calls> --seconds <approved-seconds> --output <new-spec>` preserves the
original3763 metadata, explicitly versions current source and sets five nested
bindings. No calls/time defaults. `release-template --spec <new-spec> --snapshot
<snapshot> --runtime-ref <exact-commit> --implementation-pr <new-PR> --output
<proposal>` writes an **unsigned proposal**, with authority/caps/approvals unset.
Authentic final-source approval and cap evidence must be supplied externally.
Never upload private keys or credentials in a grant, capsule, notebook or PR.

After all gates, in this same Codex session:

```powershell
& $py -B -m scripts.minicpm_fulltrain_recovery stage --locator <release-locator> --spec <new-spec> --private-key <local-key> --reconciliation <verified-directory> --output data/processed/<new-package>
& $py -B -m scripts.minicpm_fulltrain_recovery publish
& $py -B -m scripts.minicpm_fulltrain_recovery submit-once
& $py -B -m scripts.minicpm_fulltrain_recovery observe --output data/processed/<new-observation>
```

Stage requires clean exact merged checkout and genuine final-source release;
fresh provider/Input/version/Private/quota/no-outstanding-VM checks precede sign
and append-only reservation. Capsule publication has a durable intent and
`publish --verify-only` reconciles one ambiguous create without retrying it.
The SDK's POST retry decorator is disabled. Notebook byte reproduction and
capsule/ticket identity are rechecked immediately before the only kernel push.
`CODEX_PUSH_INTENT` is fsynced into both journal copies **before** that POST.
Timeout, error or ambiguous return retains intent/reservation and blocks every
second submit; no forced version2, expired-ticket refresh or overwrite.

## Native-start PASS and Antigravity continuation

`observe` performs one bounded read-only provider observation, then exits.
It checks exact latest v1 kernel id/Private/T4/Inputs/code, quota and full live
provider log, then rechecks job status. Mere QUEUED/RUNNING returns
`RUNNING_UNVERIFIED`. No indefinite poller, resubmit or cancellation exists.

Parent emits positive `stage_returned` only after verified child process success
and returned stage binding for admit/setup/cpu/gpu. The native child persists
the ordered signed-ticket call claim, then observes the unchanged backend at
its actual `model.generate` entry after model load/image preprocessing/transfer.
It writes/fsyncs the generate observation before emitting a bounded structured
`native_generate_started` stdout event. Supervisor forwards only these public
receipt lines while keeping complete original child logs. JSON provider stdout
chunks are reassembled; stderr/entry/load-only events cannot establish PASS.

PASS requires all positive ordered stages, exact source/request/ticket and first
scheduled ordinal/TRAIN ID/JPG SHA, genuine claim/model-loaded observation and
provider still RUNNING. No successful output or job completion is required.
`CODEX_NATIVE_HANDOFF` records URL/version/kernel id, runtime/merge commit,
notebook/capsule/ticket SHA and grant refs, all five Inputs, finite calls/time/
physical GPUs, live quota/log proof and before/after journal heads. Leave the
kernel running and stop Codex monitoring. No claim that actual live events can
be read is made before testing the real provider; unavailable logs mean UNVERIFIED.

Antigravity resumes its SAME historical Operator conversation and journal:

```powershell
& $py -B -m scripts.minicpm_fulltrain_recovery collect --output data/processed/<new-terminal-collection>
& $py -B -m scripts.minicpm_fulltrain_recovery stage-pending --private-key <local-key> --output data/processed/<next-package>
& $py -B -m scripts.minicpm_fulltrain_recovery publish-pending
```

Collection reuses PR198's two sealed ZIP/sidecar/raw/native/C1/history/provider
verifiers and verifies generate observations against the ticket/native markers.
Only verified terminal collection permits next signed serial5+ capsules. These
carry every immutable same-source ancestor, full cumulative reservation and only
NOT_ATTEMPTED IDs; SUCCESS/INVALID/errors remain consumed. Later launches retain
the existing Owner UI flow under signed finite caps; this task grants no second
Codex API submission. Ambiguity or technical failures STOP for reconciliation.

## Validation and limits

CPU synthetic acceptance is recorded alongside the PR. Test boundaries mock
Owner/provider/model IO; signatures, mirrored append-only events, history/C1/
archive/claim validators and single-submit state transitions execute normally.
Linux process-group streaming verifies live receipt visibility before child exit.
No code test authenticates real GPU/model-fit, provider run or academic rights.
Final-source native execution is NOT_RUN; DONE is not claimed at Draft PR.
