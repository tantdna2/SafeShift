# Independent eight-image resource pilot PREP — 2026-10-19

BASE `1b2a2bdafdcc30c2144637829ab04396821f5e73`; branch
`prep/hnlo-resource-pilot8-20261019`. PREP only: no dataset images/annotations,
checkpoint download, GPU, Kaggle, self-grant, Antigravity or merge in this task.
Stop after one independent Draft PR. PR #117 stays HOLD, OPEN/Draft; its F1
`b2c381045f06b567a9cb89793dff6b4b0cacc097` is unchanged.

Authority for this preparation is the user request and the
[Lead directional decision](https://github.com/tantdna2/SafeShift/pull/117#issuecomment-6261386722).
That decision accepts raw-summary design in principle and two historical test
exceptions conditionally. It grants no execution. DEC-PA3-011 and PR #117's
DEC-PA3-016 remain PROPOSED for execution; D9R22 remains EFFECTIVE.
Moondream2 remains required for the longer-term four-model study, outside pilot.

## Cohort, independence and immutable source

Each model uses **ordinals 0–7 of original TRAIN shard 0**, without replacement,
sorting, selection by speed, dropped hard cases or TEST access: 8 images/model,
16 planned model-image attempts. The existing tracked inference manifest
`data/manifests/pa3_full_train_shard0.v1.json` is documentary identity evidence,
not a newly opened dataset/annotation. Its exact SHA-256 is
`37b9fae412db374c54b79bbb83aad1d0ba3029d06fe836b71952763550054f70`.
`cohort.planned` verifies the entire original shard's bytes before taking its
first eight rows. `IMAGE_SHA256` pins all eight hashes in ordinal order; the
worker validates against this constant and cannot substitute another valid hash.
Canonical ID/order/image hash remain in supervisor binding only. No full/GT
manifest is opened by the pilot or its CPU auditor.

Only **five** upstream modules are selectively transferred: capture, backend,
bootstrap, worker and the small tokenizer verifier. The provenance JSON records
each upstream commit/path and SHA-256 of exact Git blob bytes, verified before
adaptation. Changes are visible by comparing those pinned blobs against the new
paths: independent scope/imports/bootstrap paths, complexity and load/sync
observations, pilot engine invocation. Tokenizer verifier is byte-identical.
No `hnlo_train` package import, full-package copy, cherry-pick or dependency on
unmerged #117 at runtime. New lifecycle, authority, sampling, custody, audit and
notebook builder are independently reviewed. Existing main runtime/driver/
capture/formula/parser/source-lock/authority files are unchanged.

New authority `configs/diagnostics/resource_pilot_authority.v1.json` has
`grant=null`. Two independent run/attempt identities:

| Model | Run ID | Attempt ID |
| --- | --- | --- |
| Qwen3 | `hnlo-pilot8-v1-qwen3-s0-a1` | `resource-pilot8-qwen3-20261019-a1` |
| InternVL3 | `hnlo-pilot8-v1-internvl3-s0-a1` | `resource-pilot8-internvl3-20261019-a1` |

One immutable implementation F1 must directly descend from BASE. Future F2 may
change **only** the new pilot authority file, with F1's source-payload digest and
implementation SHA, this pilot PR's decision/audit URLs, exact selected model
units and all explicit approvals. Standard merge must have BASE/F2 as ordered
parents and F2's exact tree. Bootstrap discovers that fixed branch's one PR,
requires merged/non-Draft state, clones Git source and checks out its exact
detached merge, validates full tracked byte inventory. Draft/old grants/changed
source/squash/rebase/wrong parent/tree/dirty source block before setup/data/GPU.
Any source amendment requires new independent review and grant, never a reused
attempt. Old PR #112/#116/#117 authority is neither changed nor inherited.

## Two one-click notebooks and guarded runtime

- `notebooks/SafeShift_HNLO_RESOURCE_PILOT8_qwen3.ipynb`
- `notebooks/SafeShift_HNLO_RESOURCE_PILOT8_internvl3.ipynb`

Each has one Markdown and one code cell, empty outputs, fixed model and embedded
source-payload digest. Null grant/unmerged source blocks Run All. **Future only,
after release and separate approval:** upload unchanged; attach exactly one
private, unpacked approved TRAIN mount; select T4 x2; Internet ON for pinned
software/checkpoint provisioning; Save & Run All once. Owner edits no code/SHA/
path. One model environment/cache per notebook/VM. The inherited conservative
host preflight requires Linux x86_64, two T4, >=24 GiB available RAM, >=50 GiB
scratch; output preflight requires >=2 GiB. InternVL3 exposes and uses **GPU 0
only**, leaving host GPU 1 unused. These are admission guards, not measured peaks.

Qwen3 revision `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`: Python
3.12.13, torch 2.10.0+cu128, Transformers 4.57.1, CUDA 12.8, explicit audited
two-T4 FP16/NONE/SDPA placement: embedding CPU, visual GPU 1, layers 0–20 GPU 0,
layers 21–35/head/norm GPU 1; pinned allocator. Documentary technical evidence:
[PR #112 result](https://github.com/tantdna2/SafeShift/pull/112#issuecomment-6259305190).

InternVL3 revision `cb57a075cb75a2e6d1b668b128d48bb00ae321d2`: Python
3.11.11, torch 2.6.0+cu124, Transformers 4.52.4, CUDA 12.4, visible GPU 0,
FP16/NONE/SDPA, original native tiling max 12 + thumbnail. The unchanged PR #115
`DriverSession` runs **after** seccomp/Python guards and retains handles through
final observation; PR #116 boundary/monitoring and pinned generation-source checks
are reused. Documentary technical evidence:
[PR #116 result](https://github.com/tantdna2/SafeShift/pull/116#issuecomment-6259226428).
Those synthetic probes do not validate real TRAIN resources. Monitoring is
PARTIAL and local-peer relay UNOBSERVABLE; never claim SECURITY_PASS or NO_LEAK.

Order: source/authority → consume local ledger → resource preflight → build one
pinned software environment → fresh guarded CUDA admission **before weights** →
CPU-only pinned checkpoint provision/verification → exact eight JPEG staging →
fresh guarded inference → raw custody seal → separate offline CPU HNLO replay →
failure-preserving export. No annotation/GT access even after seal in this pilot.
CPU replay disables CUDA/torch/TF/Flax and verifies only pinned tokenizer files.
Worker rechecks executable/config/prompt source bytes without opening label-bearing
data manifests; supervisor verifies the full source lock first. This reviewed
data-flow boundary is not an OS filesystem sandbox against malicious replacement
code. Internet denial is not a proof of filesystem nonaccess or relay absence.

## Capture and failure behavior

C1, greedy, batch 1, <=32 new tokens, original raw HNLO formula; no clamp,
calibration, threshold, retry, resume, forced prefix or altered generation.
At every returned step retain four exact raw label logits in Level01–04 order,
generated-token value, full-vocabulary argmax/value/logsumexp/nonfinite counts;
processed score summaries are separate. Native input/output IDs, tensor layout,
actual empty processor list, EOS/MaxLength criteria, generation kwargs/config,
runtime T1, model/revision/checkpoint inventory and placement remain linked to
ordinal/image hash/run/source. Persist/fsync/read-back raw summaries before any
decode. Seal each sample before parser/alignment/HNLO; seal raw custody before
independent CPU replay. **`full_vocab_replay=false`** on scope, results, audit and
export; discarded vocabulary vectors cannot be reconstructed. Hash integrity
does not authenticate an honest/correct GPU reduction. The summary evidence
limit requires final model-unit approval despite in-principle methodological
acceptance. No accuracy/AUROC or research-HNLO claim is produced by this pilot.

One model load and at most one native generation per original ordinal. **Stop
on the first failed sample, including INVALID**; no skip-to-next after failure,
no failed-sample retry. All eight receive explicit SUCCESS/INVALID/TECHNICAL_ERROR/
INTERRUPTED/NOT_ATTEMPTED accounting. Resource admission and model-load failure
retain all eight denominators. Staging hash failure stops immediately; remaining
images are not opened. Torn journal bytes are retained and custody-inventoried,
never repaired or converted to valid samples. Per-sample timing sidecars persist
before proceeding, so prior completed timings survive worker death. A killed
in-flight sample may have no end time: report null/censored, never invented zero.
CPU-audit/export failure leaves FAILED/PARTIAL status and raw files. Whole-VM loss
can defeat export entirely; no persistence guarantee after hard venue teardown.

## Resource measurements and extrapolation

| Quantity | Evidence and definition |
| --- | --- |
| Source/environment setup | `bootstrap-timing.json` covers clone/release proof; `environment_setup-timing.json` covers pinned software build. `guarded_cuda_admission-timing.json` is separate. Failed phases have terminal timing too. |
| Checkpoint / model load | `checkpoint_provision-timing.json` includes download + byte verification, no inference. `raw/model-load-timing.json` covers tokenizer/processor/model construction; `raw/index/native-load-timing.json` isolates native `from_pretrained`, including failures and successful CUDA synchronization. |
| Each image | Staging `.read-start/.hash/.timing` receipts plus worker `.attempt/.timing/.result`; worker wall includes prepare, native generate, raw durability, decode/seal/replay. No failed timing is silently omitted. Staging and processing are distinct. |
| GPU VRAM / RAM | PyTorch allocated/reserved peaks per visible device reset before model load; observations per image are cumulative since reset, final memory retained on failure where observable. Supervisor also samples `nvidia-smi` total memory used on the selected physical devices, including driver/runtime overhead; this is device occupancy, not exclusively worker attribution. Worker self `ru_maxrss` plus supervisor process-tree sampled RSS include setup/provision/worker/audit/export children. RSS is summed, so shared pages can overcount. |
| Image complexity | Native `pixel_values.shape[0]`; InternVL is 448x448 tiles including thumbnail; Qwen3 is native grid patches, with exact `image_grid_thw` and all input shapes. These are different units; do not compare as identical tiling. Input token count and native output steps are recorded, including available pre-error observations. |
| Disk / journals / export | Sampler waits 0.5 s between observations through archive creation; query/scan time lengthens the actual interval. Initial/peak filesystem used and min-free bytes are separate for scratch/output roots. Roots may share a filesystem; occupancy includes unrelated users and misses short spikes. Exact raw journal bytes and uncompressed copied bundle bytes, verified archive size, export wall time (copy + archive + verification) and export-metadata hash are retained. Scratch also contains model/env/staged images, which are excluded from evidence archive. Bundle copying temporarily doubles evidence occupancy and is included by sampling. |
| CPU audit | `cpu-audit-timing.json` and log/report outside immutable raw custody. CPU only, no labels; independently recompute HNLO from four retained raw decision logits. |

Report mean/median successful seconds/image and corresponding images/s, attempted
time/failure count separately, sample SD and observed min/max. The 941-image
estimate uses one measured setup/checkpoint/admission/model-load cost plus 941
times mean per-image processing; observed min/max scenarios are **not confidence
or prediction intervals**. Export sidecar additionally gives illustrative linear
941/8 staging/CPU-audit/export scaling. Include source-clone time separately when
budgeting a venue session; no duplicated model load in per-image time. Partial
pilots are explicitly censored and cannot certify feasibility. Fixed first eight
are nonrandom, not worst-case; patch/token tails, warmup, thermal drift, archive
compression, nonlinear disk growth, hardware/account/session quotas and setup
variance preclude a completion guarantee. No numerical real throughput/peak/
941-duration claim exists until an authorized run. Missing observations remain
null/partial. Short spikes and total VM failure remain measurement limitations.

`package()` independently hashes actual archive members and writes archive,
manifest and SHA receipt. Retain the full exported archive **and** `_export.json`
and `_export_sha256.json`, which contain timing/peaks measured through export and
therefore are outer sidecars. The archive's result precedes export; export failure
is authoritative in the outer sidecar and return value, never silently a PASS.

## Proposed exposure/overlap policy — disposition still requires Lead

Record both models' full eight-image plans before any reads, then separately
ledger supervisor image-read-start/hash/staging and actual native-call ordinals,
including unsuccessful or interrupted calls. All eight can be staged even when
only a prefix reaches the model: do not conflate those exposure sets. Tie every
entry to canonical ID/hash/ordinal, model revision, run/attempt, source and raw
receipts. Conservative proposal: treat any model-call-start as model exposure,
including error; ambiguous hard kills remain POSSIBLY_EXPOSED, not unseen. A local
exclusive attempt directory prevents repeat in the same output; an **external
Lead/Owner ledger** must reserve/consume the identity across fresh Kaggle VMs.
No local code can prevent resetting the VM or deleting that ledger externally.

Before execution Lead must approve recording/exposure risk and the external
ledger. **No baseline disposition is selected here.** Before a future full 941
unit, Lead must decide in a new recorded decision/grant how those eight repeated
IDs are counted: repeated exposure with lineage, approved exact-artifact reuse
only after source/contract compatibility review, or a scientifically approved
scope change. This pilot does not remove IDs, silently reuse outputs, or authorize
repeat inference. Existing 941 IDs/order and metric definitions remain unchanged.
No cherry-picking based on pilot speed/output; no tuning from pilot responses.

## Historical exceptions and count reconciliation

Lead conditionally accepted these exact unchanged historical tests:

1. `tests.test_internvl3_hnlo_probe.ContractTests.test_null_exact_scope_and_new_attempt`
   asserts the old PR #116 grant is null; it already fails on BASE because valid
   F2's consumed grant is nonnull. Preserve historical grant and test.
2. `tests.test_internvl3_hnlo_probe.NotebookTests.test_single_cell_source_lock_and_bootstrap_failure_export`
   verifies old PR #116 full-tree lock against today's tree; appending this
   task's DECISIONS.md/TASKS.md changes conflicts. Verify historical release on
   its exact detached merge/F1 source commitments, never rewrite lock/test.

The unfiltered old suite must remain **FAIL WITH DOCUMENTED EXCEPTIONS** if these
are its only failures. The prior filtered 95-case/9-skip selection is not a clean
unfiltered PASS. Old `257 OK, 6 SKIP` wording refers to unittest's **257 discovered/
run including six skips**, i.e. **251 passed + 6 skipped**, if that raw `Ran 257`
summary is accurate. It does not mean 257 executed passes plus six skips. The
audit's `256/257` cannot be resolved from the summaries alone: no original
Antigravity raw test log is available here. Do not invent the missing identity.
This task records fresh exact run/pass/skip/fail/error counts below; the old
Antigravity numerator remains an explicitly unresolved historical provenance
discrepancy pending its log, and must not be relabeled as a clean old PASS.

## Validation record and remaining approval

Actual host: Python 3.11.9 / Windows 10.0.26200. No real tokenizer/model/native
GPU runtime provisioning is performed. CPU tests use generated vectors/bytes and
tracked inference identity metadata only. All GPU queries in the new sampler
suite are mocked; no real CUDA or nvidia-smi call is made by these tests.

| Check actually run | Exact result |
| --- | --- |
| `python -m unittest tests.test_resource_pilot -q` (same suite loaded by the count-preserving runner) | **37 run, 37 PASS, 0 SKIP, 0 FAIL/ERROR**, 184.281 s including loader/runner overhead. Covers null/old/wrong grant, exact ordinals/hashes, wrong image bytes, no GT, native guard/driver order and early gate/finalization failures, raw-before-decode/seal-before-parse, separate/nonfinite summaries, CPU HNLO, OOM/low-resource/load failure, INVALID/interrupt/torn bytes, no retry/resume, one-use ledger, all-eight accounting/export, mocked RSS/device VRAM/disk sampling, uncertain projections, real temporary Git F1/F2/merge faults and source/notebook/provenance bytes. |
| Eight baseline/native/runner modules below | **257 run = 251 PASS + 6 SKIP, 0 FAIL/ERROR**, 272.859 s. Six are optional pinned-tokenizer/CPU-ML cases; no GPU claim. This directly reconciles unittest count semantics behind the old `257 OK, 6 SKIP` wording. |
| Four historical capture/release modules below, unfiltered | **97 run = 86 PASS + 9 SKIP + 2 FAIL, 0 ERROR**, 270.906 s. Exactly the two Lead-accepted historical identities above. **FAIL WITH DOCUMENTED EXCEPTIONS**, not clean PASS. No historical source lock or test edited. |
| Same two historical identities at exact BASE/PR116 detached merge | **2 run = 1 PASS + 1 FAIL**, 0.190 s: stale null-grant assertion fails; historical full-tree notebook lock passes. |
| Historical release source verification | Original PR112 F1 **534/534**, PR115 F1 **572/572**, PR116 F1 **588/588** Git-blob hashes PASS. PR116's unchanged `verify_topology()` and full payload verification also PASS on its exact detached merge `1b2a2bd...`, with original F1/F2/merge tree/parents and nonnull grant preserved. No historical bootstrap is actually executed with network/model privileges. |
| Compile and document/source checks | 13 package modules + builder + test compile; both notebooks JSON/AST compile, empty outputs and fixed units; 609 source-file hashes/normalized notebook digests; append-only DECISIONS/TASKS; scoped staged file/size/path and diff checks. Final generated-payload checks are rerun after documentary updates. |

Reproducible regression module lists (repository root):

```text
python -m unittest tests.test_ls1 tests.test_pa3_native tests.test_pa3_full_train tests.test_pa3_r2 tests.test_qwen_runner tests.test_qwen3_runtime_placement tests.test_internvl3_prep tests.test_internvl3_runtime_result -q
python -m unittest tests.test_hnlo_capture tests.test_hnlo_t1_cpu tests.test_hnlo_one_click tests.test_internvl3_hnlo_probe -q
python -m compileall -q safeshift/diagnostics/resource_pilot scripts/build_resource_pilot.py tests/test_resource_pilot.py
python scripts/build_resource_pilot.py
```

Detailed raw CPU logs/count JSON remain local under ignored
`data/processed/pilot8_validation/` (`baseline`, `historical`, `pilot_release`).
They contain no real model/dataset outputs. An initial 33-case development run
correctly rejected a test file edited after source-lock generation; regenerate
rather than relax the check. Intermediate 35/36-case checks and the final 37-case
suite pass. The historical local release clone initially had Windows CRLF/stat
cache differences; restoring exact Git archive bytes and refreshing its local
index (empty staged diff) allowed the unchanged 588-file verifier to pass.
Neither historical source nor its lock was modified. Full repository discovery,
Linux native guards in this new worker, real tokenizer revalidation and Kaggle
runtime are NOT RUN; Windows mocks do not establish those behaviors.

Before any Kaggle run: direct GitHub review, separately requested independent
audit; Research Lead approval for each exact selected model unit, TRAIN-image
reads, pinned software/checkpoint provisioning, GPU and descriptive TRAIN
exception, summary evidence limit/raw provenance/retention, security boundary and
AF_UNIX local relay residual risk, resource/interruption/venue limits, prospective
exposure/overlap recording and external no-retry ledger; source-bound authority-
only F2; standard merge; independent merge/source proof. No post-seal GT approval
is requested or used by this pilot. Full baseline label access needs its own
future authority. Current grant is null and this task stops at Draft PR.

Unverified Kaggle conditions: actual host/account limits and scratch/output
availability; pinned environment builds and checkpoint network availability;
post-guard driver/CUDA behavior in this new worker; native multi-image backend,
real-image preprocessing patches/tokens, VRAM/RAM/disk peaks, CPU replay/export
portability and storage retention; 941-image feasibility. Prior synthetic
technical validation and new CPU tests do not establish any of these.
