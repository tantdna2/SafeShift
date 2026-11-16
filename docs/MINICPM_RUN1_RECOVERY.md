# MiniCPM Full-TRAIN Owner UI restart ? V4

[Owner decision6918902424](https://github.com/tantdna2/SafeShift/pull/199#issuecomment-6918902424)
supersedes PR199's one-Codex-submit proposal. SAME session/branch/Draft PR199,
BASE main507e981. No new PR, smoke round or repeated budget-approval loop.
This document describes code pending fresh review/audit/merge, not a live release.

## Old attempts: retired results, immutable evidence and uncertainty

Run1 local sealed supervisor records `UNIQUE_ORIGINAL_MOUNT_REQUIRED` at admit;
V2 local log records `MINICPM_STALE_PROVIDER_BEFORE_LAUNCH`; V3-1 has a reserved,
expired ticket. The Owner reports no usable image results and reportedly deleted
old jobs. Old account observations found no matching slugs and denied reads.
These facts are kept separate: **not** independently verified deletion, terminal
remote custody or measured zero native calls. New classification is
`RETIRED_NO_USABLE_RESULTS`, with
`historical_status=PROVIDER_UNAVAILABLE_NOT_VERIFIED_DELETED` and
`native_calls_evidence=OWNER_REPORTED_LOCAL_LOGS_NOT_PROVIDER_VERIFIED`.

All three original journal/mirror heads, PUBLISHED mismatch, tickets, signatures,
source/notebook locks, logs and local supervisor ZIP/sidecar hashes remain.
Their original3000 calls/3 jobs/86400 physical GPU-second reservations remain
recorded. Retirement excludes predictions; it does not refund or rewrite holds.
The named three are covered by this exact Owner decision; future ambiguous jobs
cannot silently be retired by copying this report.

## New execution and finite budget

The new execution id is `mcpm4-restart-v1`; MiniCPM series is
`fresh171-minicpm4-owner-restart-v1`. First plan contains all original3763 TRAIN
IDs/order/JPG hashes from ordinal0, empty prediction history, no old SUCCESS or
INVALID inheritance. FP16/eager, exact FP32 resampler, strict C1, labels, HNLO N/A,
cohort and TEST closure stay unchanged. One create-only binding appends to the
same historical V3 journal; first new job is global serial4. Serial numbers and
budget provenance do not restart at zero.

The implementation derives one auditable finite policy from the Owner directive:

| Quantity | Formula / bound |
| --- | --- |
| New job ceiling | 3763 serial jobs |
| Each job | at most3763 pending-ID reservations,14400 seconds,2 physical T4s,1 load |
| Inclusive reserved calls | 3000 + 3763?3763 =14163169 |
| Inclusive jobs | 3 + 3763 =3766 |
| Inclusive reserved GPU-s | 86400 + 3763?2?14400 =108460800 |
| Actual new native image calls | at most3763 under unchanged NOT_ATTEMPTED-only histories |

The four-hour job envelope reuses the existing approved job limit. The job/call
products bound the actual scheduler even if reserved image slots are unused by
short/aborted jobs; no hold is refunded. This conservative mathematical ceiling
is **not** a request to execute millions of images, a model-throughput claim, a
guarantee of success, weekly provider quota or numbers quoted from Owner. It
covers a finite scheduler capable of all3763 original calls without granting
infinite retries. Exhausted jobs/technical ambiguity still stop for reconciliation.

Every job separately reads the legitimate account's real current quota. At most
the smaller of per-job time, remaining project reservation and provider available
GPU-seconds/2 can be held. Account reserved time must be zero before a new launch;
current new-series inventory and visible retired-job states are also checked.
Provider quota resets do not change cumulative project reservations. No account
switching or multi-account quota circumvention exists. If quota is insufficient,
wait for reset or use separately authorized different compute; do not ask for the
same project-budget consent again.

## Exact-source release and current tickets

Marker `SAFESHIFT_MINICPM_OWNER_UI_RESTART_RELEASE_V4`, schema
`safeshift-minicpm-owner-ui-restart-release-v4`, authorization
`OWNER_MINICPM_TRAIN3763_RESTART_SERIAL_UI_ONLY`. It binds exact runtime/reviewed/
merged trees, original scope, host/key, finite expiry, retirement hashes and the
precise derived numerical policy. Live authentic Owner records on PR199 still
bind source_review/independent_audit/merge/postmerge. Existing original O2?O6
rights/scope records are authenticated from the historical V3 grant; the new
budget basis is this Owner decision plus the reviewed formula, not a fabricated
APPROVED numerical amendment or repeated O5 comments. No new third-party or
academic authority is claimed. Missing/tampered authority/source/rights stays shut.

Do not use the old V3 CODEX_SUBMIT_ONCE authorization, old notebook/capsule or an
expired ticket. The CLI has no submit or live-observe action. F1's terminal-output
helper is not used to watch RUNNING jobs. F2's accelerator check remains enforced
by the existing strict terminal verifier and source-bound two-T4 GPU preflight;
wrong/unknown machine shapes are rejected in regression tests. Terminal output
inventory remains strict. The runtime still writes durable native generate-entry
claims/logs, which Antigravity can inspect through the official live logs/UI.

## Five nested Inputs

Paths below are relative to `/kaggle/input`; actual versions/Private/bytes are
gated, not assumed from the table.

| Input / pinned ref | Mount |
| --- | --- |
| `nguynanhtn/inspecsafe-v1-kaggle/1` | `datasets/nguynanhtn/inspecsafe-v1-kaggle` |
| `nguynanhtn/safeshift-pilot-input/1` | `datasets/nguynanhtn/safeshift-pilot-input` |
| `nguynanhtn/safeshift-prepare-minicpm4/1` | `notebooks/nguynanhtn/safeshift-prepare-minicpm4` |
| `nguynanhtn/safeshift-cpython3119-20240726/1` | `datasets/nguynanhtn/safeshift-cpython3119-20240726` |
| New signed `.../safeshift-minicpm-capsule-mcpm4-restart-v1-4/1` | `datasets/nguynanhtn/safeshift-minicpm-capsule-mcpm4-restart-v1-4` |

Original master/projection/JPG SHA, checkpoint, isolated Python/ABI, scratch/RAM,
GPU/driver/CUDA, child release, raw-before-parse, signed load/call claims and
ZIP/sidecar gates remain. No data/checkpoint/Python reupload or GT/parser rescue.
Preflight is integrated in the same production job, not a separate smoke loop.

## Antigravity operations after source review/audit/merge/postmerge

Use the SAME old Operator session and existing pinned venv
(kaggle2.2.5/kagglesdk0.1.38/requests2.34.2). All paths are repository-relative.
CPU preparation below writes ignored derived files only; it is not a release.

```powershell
$py = 'data/processed/operator-venv/Scripts/python.exe'
& $py -B -m scripts.minicpm_fulltrain_recovery retire --directive-locator <authentic-6918902424-locator.json> --output data/processed/<retirement-snapshot.json>
& $py -B -m scripts.minicpm_fulltrain_recovery prepare-spec --initial-spec <retained-original-spec.json> --output data/processed/<new-spec.json>
& $py -B -m scripts.minicpm_fulltrain_recovery release-template --spec <new-spec.json> --snapshot <retirement-snapshot.json> --runtime-ref <exact-current-runtime-commit> --output data/processed/<unsigned-proposal.json>
```

The proposal labels numbers as derived, leaves dates/key/approval/merge evidence
unset, and cannot authorize execution. After a genuine final-source V4 release:

```powershell
& $py -B -m scripts.minicpm_fulltrain_recovery bind --locator <current-release-locator.json> --spec <new-spec.json>
& $py -B -m scripts.minicpm_fulltrain_recovery stage --private-key <local-operator-key> --output data/processed/<fresh-package>
& $py -B -m scripts.minicpm_fulltrain_recovery publish
```

Bind rechecks untouched retired evidence, source and authentic release; create-only
restart guard prevents reinitialization or alternate-root budget resets. Stage
checks current account/no active sessions/quota/new job absence, then signs and
records full cumulative reservations before publication. Private capsule create
has a durable mirrored intent and no POST retry. Timeout remains ambiguous;
`publish --verify-only` verifies exact existing bytes/version without recreating.
Never put the local private key or credentials in GitHub, Kaggle or the capsule.

Only successful provider capsule-v1 verification plus fresh Input/quota and
unexpired ticket yields local downloadable `notebook.ipynb` and
`owner-handoff.json` with `RELEASED_FOR_OWNER_UI`, all hashes/versions/mounts,
source/release/ticket refs, cumulative vs historical reservations and
`start_before_local` in Asia/Ho_Chi_Minh. Missing evidence remains BLOCKED; no
publication or Owner Run has happened merely because these commands exist.

Owner receives at most three actions:

1. Upload the exact notebook, use the exact job slug in the handoff, and attach its five pinned Input versions.
2. Select Private / Python / Internet On / GPU T4x2.
3. Before the signed expiry, Save Version ? Save & Run All ONCE and send the exact version URL to Antigravity.

Do not run cells manually/restart/submit another version. Expired new tickets
need read-only reconciliation and fresh valid release handling, never source-lock
edits, replay or overwritten old artifacts. RUNNING alone is not native-start
proof. Antigravity observes durable model.generate-entry proof after positive
admit/setup/cpu/gpu and model load, keeps the kernel running, then collects when
terminal in the same Operator session:

```powershell
& $py -B -m scripts.minicpm_fulltrain_recovery collect --output data/processed/<fresh-collection>
& $py -B -m scripts.minicpm_fulltrain_recovery stage --private-key <local-operator-key> --output data/processed/<next-package>
& $py -B -m scripts.minicpm_fulltrain_recovery publish
```

Only genuine COMPLETE provider/code/T4/Inputs, both sealed ZIP/sidecar pairs,
raw/native/C1/claims/history and timings permit a next plan. All new-series
ancestors and reservations carry forward; only NOT_ATTEMPTED IDs are scheduled.
INVALID/errors stay preserved and consumed; technical/unknown output STOPs.
No Codex API submit or automatic account/compute switch exists.

Current [V4 acceptance and limitations](research/MINICPM_OWNER_UI_RESTART_20261116.md)
and [machine receipts/logs](research/evidence/minicpm_owner_ui_restart_20261116/index.json)
cover the current Owner UI source. Historical initial PR199 acceptance remains at
[the earlier V3 receipt](research/MINICPM_RUN1_RECOVERY_20261116.md), scoped to its
old source only. New V4 acceptance is recorded separately in this same PR. No
live GPU/model-fit/inference/Owner Run or scientific qualification is claimed.
