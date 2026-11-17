# MiniCPM V5 RAM repair evidence — 17/11/2026

Base merged main `006105080fc9b240e6ffff31618d325adac41522`.
Scope and remaining gates: [runbook](../MINICPM_V5_RAM_REPAIR.md).
[Draft PR201](https://github.com/tantdna2/SafeShift/pull/201). Runtime/test commit
`02ddbf487f8c065eadc062f186179290579abdcf`; later delivery commit60d010b adds
the blocked V6 candidate, collection tests and evidence, with identical84-file
runtime SHA256 `20c2440e2048830f9143ba5548c20b54637c277e6f9e9246f9602f699a6bc5b8`.
No GPU/model-fit/scientific PASS or production transition is asserted.

Authenticated V5 provider custody, immutable original reservation and missing
memory breakdown are described in the runbook. Private verification receipt:
`data/processed/minicpm-v5-ram-repair/operator/custody-2/verification.json`.
The task has not written a production close/rebind event or released serial6.

The official SDK exhausts **170 provider Output entries** for exact V5/1,
authenticates notebook code SHA256
`32a825dbad91202dad63a18e06503fb9f515b6265d9b26d679de27c9f2cece24`, five
Input bindings and the strict supervisor ZIP. See sanitized
[custody](evidence/minicpm_v5_ram_20261117/v5-custody.json) and
[new-serial prerequisite read](evidence/minicpm_v5_ram_20261117/replacement-provider-read-only.json).
Current account quota and both exact V4-4/V5 terminal predecessors were verified
read-only. No new release is inferred from these historical observations.

V5's initial21102653440-byte headroom and HOST_OR_CGROUP_RAM failure are actual;
cache/anon/RSS/event breakdown at failure is absent. New tests replay actual
Issue173 sanitized numeric snapshots into synthetic proc/cgroup files and
separately exercise low RAM, zero-effective recovery, missing/malformed/negative
cgroup counters, OOM, alias/hardlink/FIFO/incomplete scan, interrupt, actual Linux
success/timeout descendant cleanup and simulated live/unknown cleanup. They
assert stopping before processor/weight/native calls at unsafe boundaries.
The tests do not rename Issue173's observations as V5 telemetry.

Windows CPython3.11.9 focused19 cases: **16 PASS /3 Linux-only skips**, no errors
or failures; [receipt](evidence/minicpm_v5_ram_20261117/windows-final.json).
Linux collection checks on delivery commit60d010b: **4/4 PASS**, no skips,
[receipt](evidence/minicpm_v5_ram_20261117/linux-v6-collection.json). These verify
shared original controller/archive/history reconstruction and V6's additional
reclaim, RAM and process-group receipts; missing/unsafe evidence blocks promotion.
The seven pinned-SDK transport cases skipped on Linux also ran in the existing
Windows pinned Operator venv: **7/7 PASS**, no skips or network calls (HTTP adapter
fixtures), [receipt](evidence/minicpm_v5_ram_20261117/windows-sdk-final.json).
Linux broad run on02ddbf4: **173 run /165 PASS /7 SDK skips /1 fixture error**,
[original receipt](evidence/minicpm_v5_ram_20261117/linux-final.json) and
[complete original log](evidence/minicpm_v5_ram_20261117/linux-final-tests.txt).
The old scripted native-worker fixture did not pass the newly required explicit
RAM-evidence output directory. Runtime correctly refused it. Test-only fix
`888dd15b6c13f62eb912445e9af8f5d0cbab29b6` passes that directory and explicitly
mocks/asserts the resource boundary; the **entire23-case worker/controller module
reran23/23 PASS**, [receipt](evidence/minicpm_v5_ram_20261117/linux-worker-fixed.json).
No runtime bytes changed. The initial failed log is preserved and is not called
a broad-suite PASS. All **177 distinct cases** across the broad run, corrected
module, V6 collection and Windows SDK/focused checks are now covered with no
unresolved errors; [case-by-case aggregate](evidence/minicpm_v5_ram_20261117/aggregate.json).
The Linux broad run's full3763 scripted controller/export/import and complete
resume no-call regression passed. These are synthetic results, not model output.

[Real Input rehearsal](evidence/minicpm_v5_ram_20261117/real-input-rehearsal.json)
rehashes and decodes all3763 authentic original copies,3724 JPEG/39 PNG at their
unchanged `.jpg` locators; zero copies/TEST body/model calls. Local CPU Pillow is
11.3.0; V5's actual pinned CPU worker verified Pillow10.4.0, CPython3.11.9,
torch2.6.0+cu124 and transformers4.51.3. The receipt was produced at863d410 before
the later RAM-ownership/pipeline metadata tightening; original Input verifier
bytes are identical at final runtime02ddbf4. It does not claim new3763 remote
downloads; PR200's documented73 remote images plus3690 original local bytes and
full pinned provider name/size listing remain the byte-custody basis. Current
checkpoint weight load/rehash was not performed locally; V5's sealed actual
checkpoint verification preceded its CPU failure. No model-fit guarantee.

[Candidate reproduction](evidence/minicpm_v5_ram_20261117/candidate-reproduction.json)
verifies the new V6 candidate notebook at02ddbf4 twice in isolated stdlib-only
subprocesses with heavy/provider imports and network forbidden. Both create
distinct sealed BLOCKED/zero-call preparation receipts, and cells compile with
no outputs/execution counts. Actual executable V6 creation still requires the
Operator's authentic source-bound release and fresh signed ticket.

[Preservation](evidence/minicpm_v5_ram_20261117/preservation.json) confirms the
production mirrored V3 journal remains its exact10-event prefix/head
`f6d2887394f36433b587cb56ef32eca4c952bbc4e8c35c9ba4c8185006d7102e`.
No candidate adapter/loading/numerical/parser/source-lock/checkpoint/requirements
or historical notebook bytes differ from base. All scientific identity fields
match V5 except implementation SHA, which is intentionally new. Reservation
still10526 calls/5 jobs/144000 physical GPU-seconds. Serial6 spec/release proposal
under ignored data/processed are unsigned; no approval, key, ticket or activation
is fabricated. The actual original MiniCPM Operator session ID remains missing;
the resumed recorded CLI session explicitly holds InternVL Attempt4 only.
