# MiniCPM V5 RAM failure and source-bound V6 replacement

## Serial 6 local custody and Serial 7 source candidate / 18 November 2026

The signed reservation for `nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-6`
and its downloaded supervisor `2f26e8db607d47f180feff588f840639.zip` agree on
the request, source and stage claims. The supervisor returned BLOCKED at
`reclaim` with `ValueError("HOST_OR_CGROUP_RAM")`. The signed floor was
17,179,869,184 bytes. Both snapshots bracketing the failed check recorded
14,420,357,120 bytes available. The local disposition is
**FAILED_PRE_NATIVE_NO_USABLE_RESULTS**, with zero native loads and calls.
Online provider re-verification is pending.

| Reclaim observation | Bytes |
| --- | ---: |
| memory.current | 17,791,897,600 |
| file / active_file / inactive_file | 17,153,515,520 / 10,821,332,992 / 6,332,178,432 |
| anon / kernel | 299,859,968 / 337,985,536 |
| File cache decrease across owned advice | 4,241,870,848 |
| File sizes covered by the original 30 advice calls | 5,293,230,375 |

Repeated reads of all TRAIN images and both weight shards, together with the
old 8 MiB threshold, explain the pressure identified by the independent audit.
The counters measure aggregate file cache. They do not identify individual
inodes or guarantee how many pages Linux will reclaim.

The candidate uses read-only regular-file descriptors to stream each SHA256
with an 8 MiB block limit, aligned range advice and a final whole-file hint.
The original Master is read once into its bounded parse buffer. Original
projection rows carry the frozen SHA and no size field. The reader additionally
binds the observed regular-file size and compares descriptor and path identity.
PIL decode, base64 transport and every native generation release their file
pages. The native stage passes its in-process checkpoint binding to its worker.
The loader independently hashes actual shard bytes immediately before
deserialization. After loading, it records `native/post-weight-load-advice.json`
before sampling RAM again. Returned native raw survives an advice error.

After setup and CPU checks, two directory-FD passes cover nonempty, single-link
regular files under the owned venv lib/bin, pip bootstrap, extracted CPython and
its pinned archive. Only symlink entries *inside* venv bin and extracted CPython
are skipped. Unexpected aliases in lib, special files, cross-device traversal,
identity changes, deadline and inventory overflow stop the stage. Each owned
file receives fsync and DONTNEED. Input files receive read-only advice, with no
fsync. Admission still verifies bytes in each separate stage. The signed fresh
16 GiB cgroup/host floor and disk gates determine whether the next step runs.

Read-only replay from the repaired checkout, with the private evidence present:

```console
python -B -c "from pathlib import Path; from safeshift.fulltrain.minicpm_serial6 import verify_local; print(verify_local(Path('data/processed'))[0])"
```

### PR205 audit follow-up / 19 November 2026

- Native cache advice runs after raw, result, elapsed call time and the
  cumulative call checkpoint have been recorded. A failed advice gets a
  separate per-call receipt and stops the run before another sample. A model
  failure remains the primary failure when advice also fails. At the call
  deadline the controller records an advisory skip and keeps the completed
  sample. File syscalls remain in the hard-supervised native process and
  before the signed export reserve.
- CPU and native reuse the original admission from their own stage. The
  process-local binding covers the request, source directory, deadline,
  bundle, cohort and ordered image mapping. Each file's opened descriptor
  must match the identity checked during SHA256 verification, and its
  identity is checked again after PIL decode. The native reservation check
  rechecks the scheduled files by identity. Each selected image still gets
  SHA256 verification immediately before its model call. Independent
  callers verify all bytes before decode.
- Pass 1 inventories the entire allowed scratch tree with entry and depth
  bounds. Pass 2 walks only that inventory via open directory descriptors,
  rechecking each file and directory. The Linux regression with 300 files
  under 20 nested directories observes 45 explicit directory opens across
  both passes, including the root and the two venv ancestors. Reproduce with
  \`PYTHONPATH=tests python -B -m unittest test_minicpm_fulltrain_memory.MemoryTests.test_owned_pass_two_reuses_directories_for_a_wide_deep_tree -v\`.
  This fixture measures opens on Linux. Kaggle I/O latency, cache eviction
  effectiveness and RAM headroom still need release-bound evidence.

The remaining sections document the V5 incident and the earlier Serial 6 design.

Owner [6937169950](https://github.com/tantdna2/SafeShift/pull/200#issuecomment-6937169950),
17/11/2026. New Codex branch from merged PR200
`006105080fc9b240e6ffff31618d325adac41522`; one Draft PR, then STOP for direct
ChatGPT review. No Kaggle submission, GPU smoke, model inference, production
journal append, signature, publication, audit approval or merge in this task.
Delivery: [Draft PR201](https://github.com/tantdna2/SafeShift/pull/201).

## What the actual V5 evidence proves

Official pinned SDK read-only verification authenticated
`nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-5/1`, kernel **145520728**,
provider COMPLETE, exact normalized notebook code, SafeShift metadata and five
Input bindings. Exhaustive provider inventory and a newly downloaded supervisor
ZIP/sidecar verify an admit PASS, setup PASS and CPU `HOST_OR_CGROUP_RAM` failure.
The ZIP is `72640aec4640447e9e6392bc0a59b229.zip`, SHA256
`6b0e122f9e0b3c1595d58604dd4e9910292cf188b100f722c2c9f867de110963`.
There is no GPU/native stage, load/call claim, attempt or result archive.
Disposition is **FAILED_PRE_NATIVE_NO_USABLE_RESULTS**, zero native calls by
authenticated pre-native custody; it is never COLLECTED or a refund. The remote
file listing, log and signed ticket are retained privately under
`data/processed/minicpm-v5-ram-repair/operator/custody-2/`.

Admit recorded **21,102,653,440 bytes** available (about19.65 GiB), constrained
by cgroup headroom. CPU failure records the failed16 GiB guard but **no exact
failure-time available number, memory.stat/events, RSS or survivor snapshot**.
The original leader exited with code1 and group SIGKILL was sent. That is weaker
than an observed empty group; no historical survivor telemetry is invented.
RAM after setup was reported lower by the Operator; the retained V5 log cannot
separate cache, anonymous process allocations or other pressure at that time.
**CACHE_VS_ANON_UNRESOLVED**, not "PyTorch occupied RAM".

Historical quota read: used27490/reserved0/total108000 physical GPU-seconds.
It is neither project reservations nor a current release guarantee. V5 consumed
provider resources despite zero native calls. Refresh before issuing any ticket.

Original V5 process durations: admit366.088s/setup232.322s/cpu87.438s. The signed
launch timestamp is1794884755.7507646; CPU claim1794885374.2916322 (about618.54s
after launch), followed by the failed child. These are actual stage receipts,
distinct from the approximate elapsed timestamps in the Owner's incident report.
V5's CPU software receipt verifies CPython3.11.9, torch2.6.0+cu124,
transformers4.51.3 and Pillow10.4.0. Checkpoint receipts follow the frozen actual
source/weight-byte verifier before the RAM failure; no weights were deserialized.
Storage allocation receipts show two separate devices and1MiB written/fsynced/
removed on each. This is not a full-output capacity or T4 model-fit proof.
Provider notebook T4 selection was authenticated; no V5 GPU-stage CUDA/hardware
receipt exists. V6 still measures actual T4s/driver/CUDA and disk before native.

The recorded historical CLI conversation
`a5fa95c9-bbc0-4df2-bdc7-ecb56b098bbc` was explicitly resumed for read-only
coordination. After an initial permission denial and180-second timeout, a
status-only response explicitly identified this as the **InternVL Attempt4
session, without MiniCPM V5 operations in its history**; it knows no existing
MiniCPM Operator conversation ID. Responses are retained in `operator-ack.json`.
This is not the required confirmed MiniCPM Operator session; no operations were
delegated after that finding. The custody above was independently fetched by
Codex using the official SDK. The actual original MiniCPM Operator conversation
ID remains missing and must be supplied/recovered from its existing handoff before
later operations. It must acknowledge this dossier in that same session; never
start a replacement Operator or use `--continue` to guess the session.

## Actual code compared

The downloaded successful one-image and three-image Kaggle version1 sources
were opened again: `exact-loading.py`, `exact-train_runtime.py`, `exact-train_route.py`
and `exact-train_inputs.py` in the private reference-source directory recorded in
[PR200 comparison](research/MINICPM_V44_REFERENCE_COMPARISON_20261117.md).
They use the unchanged CPython3.11.9/torch2.6.0+cu124/transformers4.51.3 stack,
FP16 eager weights, exact source/weights hashes, PIL/RGB, strict C1, FP32 resampler,
raw-before-parse and sealed ZIP recovery. Their Candidate160 ordinals and model
fit evidence do not establish Full-TRAIN final-source fit.

Actual successful InternVL Full-TRAIN notebook payload code
`internvl3763.NativeBackend` and `internvl3763_campaign` was opened: its weight
verifier retains actual hash reads, checks resources again after loader hashing,
and serial histories bind every predecessor and preserve reservations. The
current `internvl_v2_memory.py`, `scripts/internvl_v2.py` and
`internvl_v2_runtime.py` were also read. No InternVL grammar, model or precision
is substituted for MiniCPM.

[Issue173 repair](ISSUE173_REVIEW_REPAIR.md) and the actual
`scripts/minicpm173_preflight.py::memory/advise_owned_runtime/launch/worker`
prove the relevant MiniCPM precedent: same-VM owned runtime advice after the
setup child exits, then fresh actual unchanged RAM admission. Its real receipt
records available RAM17,761,562,624→25,173,176,320 bytes, file memory
13,711,212,544→6,502,432,768 bytes, nearly stable anon and24,321,982,464 bytes
before weights. That observation supports file-cache pressure **in Issue173**;
it is not a causal reconstruction of V5 or a transferable model-fit guarantee.

## Integrated resource safety

`fulltrain/memory.py` reuses the actual InternVL snapshot primitive and validates
nonnegative cgroup current/max/stat/events, host MemAvailable and process RSS.
Missing/malformed diagnostics and observed oom/oom_kill stop execution. Each
resource gate rereads `environment.resources`; signed **16384 MiB** remains
unchanged. No "reclaimable" bytes are added to available RAM.

Pipeline is **admit → setup → reclaim → cpu → gpu → native**. All stages use
the same signed request, source verification and hard supervisor. Reclaim runs
in the copied isolated worker only after successful setup returns and its group
has no live members. It does not reread Inputs or import torch before advice.
The parent records the initially empty scratch's device/inode/request binding.
Reclaim checks that binding, setup runtime receipt and actual worker prefix.

Two bounded directory-FD passes inspect only this job's `venv3119/lib`, reject
symlinks, hardlinks, junctions, special files, filesystem changes, changed inode
identities, scan overflow and deadline failure. Only regular single-link files
>=8 MiB receive read-only fsync/POSIX_FADV_DONTNEED. No file is deleted; no global
drop_caches, shared-cache advice, Input/checkpoint/raw/ticket/journal modification
or package/version change. Advice failure or no effective headroom recovery
stops before CPU/GPU/native; no retry loop.

Receipts survive ordinary exceptions, timeout and interrupts where the parent
can still run its finally block. Parent snapshots bracket every stage; children
record entry/exit, before setup, after admission, post-advice and before CPU
processor checks. Native loader uses scoped wrappers around the unchanged
CandidateBackend processor and the existing `weight_verifier` seam: before/after
processor, immediately after actual weight hashing/before deserialization,
after weight load, before every controller call and immediately before actual
model.generate after image packing. Process RSS and cgroup anon/file counters
remain distinct. Scoped wrappers restore on every exit and change no native
model argument, dtype, generation config, prompt or parser.

Supervisor kills the process group even after success, reaps the leader, then
observes all remaining group members. Live survivors or unobserved cleanup block
the next stage and are recorded. Zombies are recorded but cannot execute work.
Workers do not daemonize; hostile process-group escape or container-wide SIGKILL
cannot be repaired by Python finally blocks. The checkpoint source/weight hashes
are still checked on actual bytes at every original boundary; there is no cached
"verified" shortcut and no Input page advice. Resource gates can still reject a
later VM or load; CPU acceptance cannot guarantee GPU fit or full completion.

## V5 closure and fresh serial6

`scripts/minicpm_v5_incident.py` is read-only. It authenticates the exact public
V5 release and signed ticket, exact notebook/Inputs/provider terminal identity,
exhaustive Output inventory and strict31-member supervisor payload. CPU failure,
returned admit/setup receipts, leader reaping, claim order/expiry and absence of
native/partial evidence must all agree. Unexpected ZIP, raw/attempt files,
unknown claim, wrong source/ticket, provider ambiguity or changed custody STOP.
The V4-4 closure remains separately verified; its historical bytes are untouched.

Only a new reviewed/merged source-bound release can bind the versioned
`safeshift-minicpm-v5-ram-repair-v1` transition. It authenticates the original
Owner incident, previous V5 authority, inherited V4-4 authority, unchanged science,
public key, caps and recovery policy. A create-only RAM_REPAIR_BOUND event in the
**same mirrored journal** binds both prior failures and the exact current head.
It never fabricates COLLECTED or imports old predictions. Duplicate binding,
unknown history, changed prefix or mirror divergence stop. This coding task
prepares the path but appends no such production event.

Serial6 starts ordinal0 with all3763 NOT_ATTEMPTED and no old predictions. Before
it, conservative holds remain **10526 calls /5 jobs /144000 physical GPU-seconds**.
Reserving3763 calls/14400 seconds adds3763/1/28800, yielding
**14289 /6 /172800**. Existing finite derived project ceilings remain
14163169 calls/3766 jobs/108460800 GPU-seconds. These are ceilings on reservation
slots, not actual calls, billing, available weekly quota or a completion promise.
Every new serial separately checks finite remaining coverage, no active job,
exact predecessor custody, fresh quota and expiry/export reserve. No fake budget
approval, cap reset/refund, account switching or serial5 ticket reuse.

After genuine new results, shared collection validates the additional reclaim
stage/process-group/RAM receipts for V6 and continues only NOT_ATTEMPTED using
full verified new-series ancestry. Native ambiguity or partial raw stops ordinary
continuation; this V5 closure cannot close a later failure automatically.

## Reproduce and later Owner handoff

CPU commands (synthetic except the explicitly named read-only real-file check):

```console
python -B -m unittest discover -s tests -p test_minicpm_fulltrain_memory.py -v
python -B -m unittest discover -s tests -p test_minicpm_v5_incident.py -v
python -B -m scripts.minicpm_v5_incident --output data/processed/<new-read-only-custody>
python -B -m scripts.check_minicpm_original_inputs --inputs <authentic-copied-mounts> --spec <private-spec> --output data/processed/<new-rehearsal>.json
python -B -m scripts.minicpm_fulltrain_recovery prepare-spec --initial-spec <private-original-spec> --ram-repair --output data/processed/<new-serial6-spec>.json
python -B -m scripts.minicpm_fulltrain_recovery release-template --spec <new-serial6-spec> --snapshot <preserved-retirement> --runtime-ref <exact-reviewed-runtime> --implementation-pr <new-PR> --ram-repair --repair-closure <V5-custody-directory> --repair-directive <authentic-locator> --output data/processed/<unsigned-proposal>.json
```

Last two commands prepare unsigned material only. New direct source review,
independent Antigravity audit, separately authorized merge, verified postmerge
and authentic final-source release precede production rebind/signing/publication.
The SAME original Operator later performs that authorized work and supplies the
current signed notebook/private capsule with at most three concrete Owner steps.
Owner personally Save Version > Save & Run All once before expiry. Codex neither
submits nor watches a live job. No old notebook or ticket is edited.

Acceptance and real Input/evidence hashes are recorded in the linked
[repair evidence](research/MINICPM_V5_RAM_EVIDENCE_20261117.md).

The new [V6 candidate notebook](../notebooks/SafeShift_FULLTRAIN_MINICPM4_RAM_V6_CANDIDATE.ipynb)
contains no authentic release locator/ticket and remains CPU-preparation-only.
Its two bounded CPU executions forbid provider/heavy imports and network; both
export distinct BLOCKED/zero-call receipts. The later authentic executable V6
notebook must be generated by the Operator from this reviewed runtime and its
fresh final release, never by editing the candidate's cells or an old notebook.
