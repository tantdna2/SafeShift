# Qwen3 / InternVL3 full TRAIN V4 ? F1 PREP, 2026-10-19

Replacement status, 2026-10-20: the original #121 description/results below are
historical. The [replacement amendment](#replacement-f1--sampled-gpu-monitoring-2026-10-20)
records the current GPU repair, branch and newly executed validation. PR #121
remains unchanged on HOLD.

PREP only. New authority `configs/diagnostics/hnlo_train_authority.v4.json` has
`grant=null`. No Kaggle, checkpoint download, real TRAIN JPEG/annotation read,
CUDA/model execution, F2, Antigravity or merge occurs here. Stop at one new Draft
PR. PR #117 remains OPEN/Draft HOLD; its branch and release artifacts are untouched.

## Source and scope

BASE_SHA: `7dd96e083a8d409355062e6087624e306e4a5b2c`, verified on GitHub main.
Branch: `prep/hnlo-train-v4-20261019`. F1_SHA and canonical source-payload SHA-256
are recorded in the Draft PR body after the single F1 commit, avoiding a circular
hash in locked source. F1 must be exactly one child of BASE. No rebase/force-push.

Selective source: [PR #117](https://github.com/tantdna2/SafeShift/pull/117), exact
head `b2c381045f06b567a9cb89793dff6b4b0cacc097`. Reuse cohort, capture, backend,
CPU audit and real-Git release tests; provenance lists the original
source hashes. Runtime has no dependency on fetching the unmerged PR. Root and
image safety are imported directly from merged PR #120/V3, with its 512-total-entry
bounded search, three explicit layouts and symlink/alias/nlink/regular-file checks.
No historical release source/authority/test is edited.

Fixed original Qwen2.5 manifest bytes, IDs, hashes and order: exactly 3,763 TRAIN
images, 941/941/941/940 shards. Full metadata SHA-256:
`a35e91fb431752dbf3b6c161f227d953d5748d69ef9f39aef613019faca33008`.
`cohort.py` pins the original four shard SHA-256s and verifies complete unique
membership and original seeded partition. No split, label, metric, filtering,
training/fine-tuning, threshold, calibration, fallback or retry/resume change.
This is a descriptive baseline on exposed TRAIN, not generalization evidence.
Moondream remains required by the long-term Seminar roster and deferred here.

## Eight fixed units

Every notebook has one executable code cell, no saved output, an embedded source
payload and automatic release/root discovery. No Owner code/SHA/path edits.
All paths below are relative to repository root.

| Notebook | Count | Run ID | Attempt ID |
| --- | ---: | --- | --- |
| `notebooks/SafeShift_HNLO_TRAIN_qwen3_SHARD0_V4.ipynb` | 941 | `hnlo-train-v4-qwen3-s0-a1` | `hnlo-train-v4-qwen3-s0-20261019-a1` |
| `notebooks/SafeShift_HNLO_TRAIN_qwen3_SHARD1_V4.ipynb` | 941 | `hnlo-train-v4-qwen3-s1-a1` | `hnlo-train-v4-qwen3-s1-20261019-a1` |
| `notebooks/SafeShift_HNLO_TRAIN_qwen3_SHARD2_V4.ipynb` | 941 | `hnlo-train-v4-qwen3-s2-a1` | `hnlo-train-v4-qwen3-s2-20261019-a1` |
| `notebooks/SafeShift_HNLO_TRAIN_qwen3_SHARD3_V4.ipynb` | 940 | `hnlo-train-v4-qwen3-s3-a1` | `hnlo-train-v4-qwen3-s3-20261019-a1` |
| `notebooks/SafeShift_HNLO_TRAIN_internvl3_SHARD0_V4.ipynb` | 941 | `hnlo-train-v4-internvl3-s0-a1` | `hnlo-train-v4-internvl3-s0-20261019-a1` |
| `notebooks/SafeShift_HNLO_TRAIN_internvl3_SHARD1_V4.ipynb` | 941 | `hnlo-train-v4-internvl3-s1-a1` | `hnlo-train-v4-internvl3-s1-20261019-a1` |
| `notebooks/SafeShift_HNLO_TRAIN_internvl3_SHARD2_V4.ipynb` | 941 | `hnlo-train-v4-internvl3-s2-a1` | `hnlo-train-v4-internvl3-s2-20261019-a1` |
| `notebooks/SafeShift_HNLO_TRAIN_internvl3_SHARD3_V4.ipynb` | 940 | `hnlo-train-v4-internvl3-s3-a1` | `hnlo-train-v4-internvl3-s3-20261019-a1` |

## Future Owner sequence ? blocked until separately approved release

1. Review this F1 and perform independent audit only when separately requested.
2. Research Lead approves only explicitly selected unit(s), evidence/audit limit,
   TRAIN reads, pilot re-exposure, post-custody CPU labels, provisioning/GPU,
   cost/time/storage, retention, cross-session ledger, interruption risk and
   residual AF_UNIX local-peer relay risk. Other units remain ungranted.
3. A later F2 may change only the authority file `grant`. The notebook verifies
   exact BASE ? F1 ? authority-only F2 ? two-parent standard merge, merge tree
   equality, ancestry on main, detached exact release and every locked file.
   Any source/main drift requires a new reviewed release; no bypass/retry.
4. Only after that separate release: upload the selected notebook unchanged,
   attach exactly one approved private unpacked InspecSafe input, choose T4 x2,
   Internet ON for source/software/official pinned checkpoint provisioning, then
   Save & Run All exactly once. InternVL3 sees GPU 0; Qwen3 sees both T4s.
5. Download archive, manifest, checksum, result and export receipt including all
   PARTIAL/FAILED/BLOCKED artifacts. A consumed attempt cannot be rerun/resumed.

Supported original input (venue path, not a local machine path):
`/kaggle/input/datasets/nguynanhtn/inspecsafe-v1-kaggle/InspecSafe-V1-Kaggle/train/DATA_PATH/train/Annotations/`.
Discovery permits direct mounts or only `datasets/<owner>/<slug>` plus the three
V3 layouts; no recursion, image enumeration, TEST lookup, dataset preparation,
repack/re-upload or manual root entry. Zero/multiple/unsafe roots fail closed.

Execution order: verify source and unit authority ? exclusively consume unit
attempt ? bind fixed manifest ? CPU root/all-image metadata ? host/output/scratch/
RAM/GPU-budget admission via stdlib and nvidia-smi (no CUDA initialization) ?
journal every source read/hash/size and verified copy for the entire shard ?
software setup ? fresh guarded CUDA admission ? CPU checkpoint provisioning ?
fresh offline inference ? raw custody seal ? separately authorized CPU-only
replay/label join ? export and independent archive-member hash verification.

Missing images, nonregular/nlink/symlink/alias metadata, unreadable metadata,
SHA mismatch, copy corruption/I/O and ENOSPC retain phase, ordinal, relative
locator and expected/actual values where applicable. No generic ValueError-only
report. All metadata checks finish before image bytes; all staging finishes
before setup. Scratch capacity is checked using the sum of observed file sizes.
A failing unit stops before provisioning and retains its consumed ledger.

## Frozen runtime and evidence

Qwen3 `Qwen/Qwen3-VL-8B-Instruct` revision
`0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`: Python 3.12.13,
torch 2.10.0+cu128, Transformers 4.57.1; explicit audited placement:
CPU embedding, visual GPU 1, layers 0?20 GPU 0 and 21?35 GPU 1, norm/head GPU 1.
InternVL3 `OpenGVLab/InternVL3-2B-hf` revision
`cb57a075cb75a2e6d1b668b128d48bb00ae321d2`: Python 3.11.11,
torch 2.6.0+cu124, Transformers 4.52.4, GPU 0, unchanged PR #115 post-guard driver
loader and PR #116 monitoring. Preserve pinned native processors/tiling, FP16,
SDPA, no quantization and no Qwen2.5 pre-merger clamp for either new model.

C1 bytes, runtime 28-case T1, label candidate order, native greedy max-32/batch-1,
empty actual logits processors and native stopping criteria are unchanged.
Four raw label logits at every returned step, generated-token value, full-vocab
argmax/logsumexp/nonfinite reductions, IDs/layout/config and processed summaries
are durable before first decode. Seal each sample before parser/alignment/HNLO.
The exact four raw decision logits support CPU HNLO replay of
`logsumexp(z01,z02,z03)-z04`; full_vocab_replay=false. Saved reductions cannot
reconstruct discarded vocabulary vectors. Local checksums prove integrity,
not authenticity/correctness of the trusted runtime's reductions.

Worker requests contain only consecutive ordinal and image SHA-256; no canonical
ID, original locator, GT, domain or label. Original filenames encode labels and
therefore remain in supervisor-only binding. Byte-identical staged images have
opaque ordinal names. Worker source verification skips reading label-bearing
manifests/historical result documents; parent source proof binds those bytes.
The CPU evaluator re-verifies custody/source/unit authority before loading the
fixed full metadata table and joins only the selected shard's labels. This is a
source/data-flow boundary, not protection against arbitrary malicious code.

INVALID persists without repair; technical failure/interruption stops the unit
and preserves NOT_ATTEMPTED tail. All planned samples are accounted for, including
staging failures. Sample primary JSON has a 2 MiB cap and failure reserve, with
no truncation/full-vocab tensor retention. Torn files remain torn, inventoried
by supervisor custody and ineligible for success. Export errors retain available
raw files, manifest, torn archive and outer failure result/receipt; no archive
retry. Complete VM loss or an unwritable output filesystem can prevent export.

## Pilot overlap and resource forecast

Owner-provided observations in the 2026-10-19 task: both PR #120/V3 pilots
completed 8/8 and CPU HNLO replay PASS. Release topology is corroborated by
[PR #120](https://github.com/tantdna2/SafeShift/pull/120#issuecomment-6268948644);
this PREP does not independently re-open the pilot raw archives.
Both models already saw original shard-0 ordinals 0..7, whose fixed hashes remain
in the manifest. Keep all 3,763 images and require new baseline calls/evidence;
never substitute pilot outputs. Each new staging read/native attempt is logged.
No new exposure permission is implied by the earlier pilot grant.

| Phase / evidence | Qwen3, 941 images | InternVL3, 941 images |
| --- | --- | --- |
| Environment/source/setup | Per-phase pilot time not supplied; measure at runtime | Same unknown |
| Checkpoint provisioning | Not separately supplied; measure at runtime | Same unknown |
| Model load | Not separately supplied; own raw timing file | Same unknown |
| Inference-only arithmetic | 941 ? 13.20 s = 12,421.2 s (~3 h 27 m) | 941 ? 2.13 s = 2,004.3 s (~33 m 24 s) |
| CPU audit / custody | Synthetic measurements below; Kaggle/TRAIN unknown | Same boundary |
| Export / archive verification | Synthetic measurements below; Kaggle unknown | Same boundary |
| Owner illustrative total | ~3 h 50 m; phase overhead not apportioned | ~53 m; phase overhead not apportioned |
| Observed pilot peak GPU use | ~13.24 / 13.44 GiB on two T4s | ~4.68 GiB on GPU 0 |

For 940 images, inference-only arithmetic is 12,408 s / 2,002.2 s respectively.
Pilot first-eight selection is nonrandom; no validated full-cohort complexity,
worst-case latency/memory, FUSE speed or Kaggle session feasibility. Do not claim
the illustrative totals are inference-only or that 941 images will finish.
Observed GPU use does not establish all-image VRAM headroom. Monetary cost,
account quotas/session duration and retention capacity require Lead/Owner review.

Admission for 941 samples: primary summaries ?1.838 GiB; reserve another 1 MiB
per sample for receipts/seals/metadata, 192 files per sample, 256 MiB run reserve,
archive at uncompressed size plus tar headers/metadata, and 1 GiB final reserve.
Total output reservation is **8,169,324,544 bytes (~7.61 GiB)** within an internal
18 GiB cap, including already existing saved output. This is a configured budget,
not a claim about the current venue quota. Scratch requires **51 GiB + all staged
image bytes**, plus the output reservation if both share a filesystem. Host
admission preserves 24 GiB available RAM, two T4s with the inherited ?13 GiB free each; Qwen3 additionally requires
?14 GiB free on both devices, above its observed ~13.44 GiB pilot peak.
InternVL3 selects GPU 0 with a separate ?6 GiB estimate while preserving the
stricter inherited host admission; only GPU 0 is visible to InternVL3. Runtime retains archive and log reserves and stops
before the next call on shortage rather than dropping evidence. Source/weights/
environments/staged JPEGs stay in external ephemeral scratch, excluded from export.
No completion or worst-case storage guarantee follows from admission estimates.

## CPU validation and reproducibility

| Check actually run | Result |
| --- | --- |
| Linux new V4 CPU suite | 56/56 PASS, no skips, 265.248 s. All eight actual cell bootstraps stage 941/941/941/940 generated JPEGs each model before fake setup. Covers original manifest/order, metadata/hash/copy/ENOSPC, wrong grants, custody/HNLO, label isolation, torn timing and failed archive retention. |
| Final Windows notebook/source/GPU-budget checks | 6/6 PASS, 0.301 s, including new Qwen3 14 GiB admission boundaries; entire 651-file payload and eight notebook cells verified. |
| Windows focused authority/capture/lifecycle/budget/exposure | 21/21 PASS, 81.997 s; separate final overlap/hash assertion 2/2 PASS, 0.041 s. |
| Linux eight-module native/baseline/runtime regression | 257 = 251 PASS + 6 SKIP, 39.434 s; optional tokenizer/ML dependencies skipped. |
| Linux nine-module capture/release/security/pilot regression, unfiltered | 231 = 214 PASS + 10 SKIP + 7 FAIL, 46.604 s; not an all-green suite. BASE comparison below. |
| Linux BASE failure comparison | Six exact identities reproduce FAIL on unchanged BASE, 1.236 s. V3 whole-tree lock identity separately PASS at BASE, 4.922 s. |

Regression failures, exact identities (historical tests/locks/authorities untouched):

- `tests.test_internvl3_hnlo_probe.ContractTests.test_null_exact_scope_and_new_attempt`
- `tests.test_internvl3_hnlo_probe.NotebookTests.test_single_cell_source_lock_and_bootstrap_failure_export`
- `tests.test_internvl3_driver.ContractTests.test_null_old_grants_missing_flags_and_changed_scope_rejected`
- `tests.test_internvl3_driver.NotebookTests.test_generated_notebook_and_every_locked_source_byte`
- `tests.test_resource_pilot.ContractTests.test_default_grant_and_exact_two_new_units`
- `tests.test_resource_pilot_dataset_path.V3ReleaseTests.test_v1_v2_artifact_bytes_and_scientific_scope_are_unchanged`

All six above fail at BASE too: four stale null-grant expectations after real F2,
plus two older whole-tree locks already mismatching BASE DECISIONS. The additional
`tests.test_resource_pilot.SourceNotebookTests.test_source_lock_all_bytes` passes
at BASE and fails here because the required append-only DECISIONS/TASKS change
bytes bound by the frozen V3 F1 lock. This is a new HEAD incompatibility of a
historical whole-tree assertion, explicitly disclosed, not BASE-reproduced and
not waived as green. V3 release bytes and its original checkout remain intact;
its frozen lock is not a rolling current-HEAD lock. New V4 gets its own lock.
No historical assertion is edited or silently excluded.

During development, the first new run found a finite fake timeout clock exhausted
by added measurement calls. Measurement now uses its own monotonic clock and
all timeout tests pass. After the 56-case run, the final GPU headroom
check was added and passed in the targeted six-case source/budget group. A subsequent overlapping source-generation run observed
stale generated null scope/source bytes; regenerating only the new untracked
null authority/lock fixed those artifacts. Final 56-case execution uses the
new matching scope. None of these fixes touches historical tests or grants.

The 941-sample synthetic profile uses deterministic fake outputs (27 steps,
1,000 vocabulary), production journal/capture/replay/custody/archive primitives
and native-call markers. It asserts 941 successful independent raw replays and
verifies every archive member. Final full-shard profile (source fingerprints and command in
[small CPU report](hnlo_train_v4_cpu_profile.json)):

| Measured synthetic quantity | Observation |
| --- | ---: |
| Samples / independent successful raw replays | 941 / 941 |
| Journal/custody files | 125,166 |
| Evidence / archive bytes | 72,352,483 / 10,334,775 |
| Creation plus online replay | 308.982 s (~405 files/s) |
| Independent CPU raw replay | 145.210 s |
| Custody seal plus verification | 51.996 s |
| Archive plus actual member verification | 31.258 s |
| Peak CPU process RSS | 586,096,640 bytes (~559 MiB) |

The profile ran on Linux temporary storage with other CPU tests active; it is a
single observed run, not a benchmark bound or Kaggle/FUSE prediction. BASE plus
working-source fingerprints are retained. All exercised primitives match final
sources; unused supervisor/export/resource-admission hardening and removal of the unused comparison
CLI occurred during the run and are explicitly identified in the report. The
full supervisor path is covered by the separate 56-case suite. No result from
this simulated shard is a baseline model output.
No GPU, real TRAIN, Kaggle, checkpoint/environment installation or independent
audit is part of these checks. Preinstalled Linux Python 3.14.4 / Pillow 13.0.0;
Windows Python 3.11.9 / Pillow 11.3.0. These CPU runtimes do not validate the
pinned Kaggle environments. Temporary synthetic artifacts are cleaned; no real
dataset fixtures or large raw outputs enter Git. Worktree Git descriptor is
relative for Windows/WSL compatibility and is not a tracked change.

Commands from repository root (Linux `python3`; Windows `python` where supported):

```text
python3 -m unittest tests.test_hnlo_train tests.test_hnlo_train_v4 -q
python3 scripts/profile_hnlo_train.py
python3 -m unittest tests.test_ls1 tests.test_pa3_native tests.test_pa3_full_train tests.test_pa3_r2 tests.test_qwen_runner tests.test_qwen3_runtime_placement tests.test_internvl3_prep tests.test_internvl3_runtime_result -q
python3 -m unittest tests.test_hnlo_capture tests.test_hnlo_t1_cpu tests.test_hnlo_one_click tests.test_internvl3_hnlo_probe tests.test_internvl3_monitor tests.test_internvl3_recovery tests.test_internvl3_driver tests.test_resource_pilot tests.test_resource_pilot_dataset_path -q
python -m compileall -q safeshift/diagnostics/hnlo_train scripts/build_hnlo_train.py scripts/profile_hnlo_train.py tests/test_hnlo_train.py tests/test_hnlo_train_v4.py
python scripts/build_hnlo_train.py
git diff --check
```

After four independently authorized successful/partial unit exports are copied
under `data/processed/`, independent CPU pooling uses the exact source checkout
and already available pinned tokenizer files (no weight loading/download):

```text
python -m safeshift.diagnostics.hnlo_train.audit --repo . --model qwen3 --tokenizer data/processed/tokenizers/0c351dd01ed87e9c1b53cbc748cba10e6187ff3b --runs data/processed/qwen3/shard0/evidence data/processed/qwen3/shard1/evidence data/processed/qwen3/shard2/evidence data/processed/qwen3/shard3/evidence --output data/processed/qwen3/pooled
python -m safeshift.diagnostics.hnlo_train.audit --repo . --model internvl3 --tokenizer data/processed/tokenizers/cb57a075cb75a2e6d1b668b128d48bb00ae321d2 --runs data/processed/internvl3/shard0/evidence data/processed/internvl3/shard1/evidence data/processed/internvl3/shard2/evidence data/processed/internvl3/shard3/evidence --output data/processed/internvl3/pooled
```

These are suggested relative artifact locations for later CPU audit, not required
Owner edits to a notebook. Pooling re-verifies every unit's source, authority and
raw custody before reading labels; it recomputes pooled image-level AUROC,
not a shard average. Coverage includes SUCCESS/INVALID/TECHNICAL_ERROR/INTERRUPTED/
NOT_ATTEMPTED, all planned IDs and domain tables. Generated-label metrics remain
separate from HNLO; no HNLO threshold/accuracy or generalization claim is added.

Remaining release gates: real all-shard JPEG/metadata/hash validation and memory/
latency distribution remain unrun; pinned Kaggle provisioning/runtime is not
installed in this task; the account/session/retention budget is not verified.
A global Owner/Lead attempt ledger is required because a local exclusive ledger
cannot prevent VM replacement/deletion. AF_UNIX relay remains PARTIAL/UNOBSERVABLE.
The sufficient-summary audit boundary, six BASE failures plus one HEAD lock
incompatibility, overlap, resource/interruption and total-loss export risks all
require explicit review; none is represented as a security or feasibility PASS.
Full repository test discovery was not run; targeted modules match this task.

## Changed files

- `safeshift/diagnostics/hnlo_train/`: new isolated full TRAIN implementation;
  cohort/capture/backend/engine, bootstrap/contract/tokenizer/worker,
  inputs/budget/orchestrate, audit/evaluate and package initializer.
- `scripts/build_hnlo_train.py`, `scripts/profile_hnlo_train.py`.
- `tests/test_hnlo_train.py`, `tests/test_hnlo_train_v4.py`.
- `configs/diagnostics/hnlo_train_authority.v4.json`,
  `hnlo_train_source.v4.json`, `hnlo_train_provenance.v4.json` in that directory.
- Eight notebook paths listed above; this runbook and small CPU-profile JSON; append-only DECISIONS/TASKS.
The exact file list and F1/source digest are in the Draft PR. Existing tracked
files other than the two append-only logs must remain byte-identical to BASE.

## Replacement F1 — sampled GPU monitoring (2026-10-20)

Source decision:
[ChatGPT disposition on #121](https://github.com/tantdna2/SafeShift/pull/121#issuecomment-6272792723).
Carry every file from old F1 `81ae8b10aa002128d601fcd01d78297a87a69237`
onto a new branch, `prep/hnlo-train-v4-gpu-monitor-20261020`, starting at the
identical BASE `7dd96e083a8d409355062e6087624e306e4a5b2c`. There will be exactly
one replacement implementation commit, with BASE as its sole parent. Its SHA
and final source payload are recorded in the new Draft PR to avoid circular
hashes. Do not append a commit to, force-push, close or otherwise alter #121.
PR #117 is also untouched. New direct review and separately requested
independent audit remain required; no previous audit approves the replacement.

Production differences from old F1:

- `hnlo_train/orchestrate.py` supplies the existing `gpu_memory` observer to
  Sampler with `interval=10`. The observer runs CPU-side
  `nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits`, with
  a five-second subprocess timeout and no torch/CUDA import. Device indices
  become string keys, and MiB readings become bytes in
  `resources.sampled_device_peak_used_bytes`. Every reported device is sampled,
  independent of the native worker's CUDA-visible placement.
- Keep the historical shared Sampler and GPU helper byte-identical to BASE.
  Initial and final observations bracket the periodic 10-second waits. Query
  duration, scheduler delays and timeout overhead affect actual cadence.
  RSS/disk tracking shares that interval; the native worker's separate PyTorch
  current/peak allocated/reserved results are unchanged.
- Existing monitoring exception capture remains nonfatal and deduplicates
  exception types in `resources.errors`. Prior successful GPU observations
  remain available after a failed poll. `coverage=PARTIAL_SAMPLED` applies even
  with no errors: short spikes, missing devices, failed polls, exited children,
  other GPU processes and shared filesystem activity limit observation. These
  are sampled maxima, never absolute device peaks or per-model attribution.
  With the inherited all-or-error sample count, failures after RSS/disk updates
  do not increment `samples`; all failed polls can yield RSS=null while disk
  observations remain. No completeness claim is inferred from that counter.
- The V4 result appends these GPU/interval limitations. It does not use sampler
  values/errors to change inference, CPU HNLO, scientific status or denominators.
- Only `bootstrap.HEAD_BRANCH` and matching `contract.BRANCH` change to the
  replacement branch for source discovery. All eight generated cells must
  discover that branch, preventing accidental selection of old #121. Authority
  template and bytes are unchanged, including `grant=null`.

The dataset manifests, all 3,763 IDs/hashes/order, four 941/941/941/940 shards,
eight run/attempt IDs in the table above, prompt C1, HNLO, raw summaries, CPU
replay, model revisions/placement, storage limits, permissions, GT/TEST isolation
and no-retry/no-resume policies remain unchanged. Builder logic and historical
tests/locks are unchanged. Regenerate the new V4 lock and eight notebook payloads
after documentation changes; cover all 653 tracked files with 651 source digests
plus the separately validated authority and lock. No source file is exempted to
make a test pass.

Validation actually completed for the replacement:

| Check | Result |
| --- | --- |
| Windows initial six GPU CPU tests | 6/6 PASS, 101.721 s; before the seventh null-grant test was added |
| Linux V4 CPU suite, including all seven GPU tests | 64/64 PASS, no skips, 255.947 s |
| Linux native/baseline/runtime group | 257 = 251 PASS + 6 SKIP, 37.079 s |
| Linux historical capture/release/security/pilot group, unfiltered | 231 = 214 PASS + 10 SKIP + 7 FAIL, 49.958 s |
| Identical historical group at unchanged BASE | 231 = 215 PASS + 10 SKIP + 6 FAIL, 49.662 s |
| V3 whole-tree lock assertion on an unmodified Git archive of old #121 F1 | 1/1 FAIL at DECISIONS.md, 0.067 s, reproducing its disclosed incompatibility |

The same six BASE failures listed earlier reproduce in this task. The seventh
identity is again
`tests.test_resource_pilot.SourceNotebookTests.test_source_lock_all_bytes`:
PASS at BASE, FAIL at old #121 F1, FAIL at replacement. It binds the historical
V3 whole tree, including DECISIONS/TASKS, which V4 appends. This is a disclosed
incompatibility introduced by original V4 relative to BASE, not a new GPU-repair
regression and not an all-green result. Historical assertions and source locks
were neither edited nor filtered out.

The seven added CPU tests exercise two GPUs with differing maxima, exact query
arguments/timeout, command failure, timeout, missing executable, malformed or
empty/partial output, prior readings after a gap, periodic wait/stop, branch
binding and null grant before polling. A six-flow comparison uses synthetic
native outputs: complete versus interrupted-tail research outcomes, each with
GPU polling disabled/successful/timed out. It compares event order, input rows,
raw vector bytes before/after audit, CPU HNLO replay, metrics, coverage and sample
journals, plus retained worker-memory results and export success. Monitoring
failure does not promote a partial research result or spoil a complete one.

CPU environments: Linux Python 3.14.4 / Pillow 13.0.0 in existing WSL Ubuntu;
Windows Python 3.11.9 / Pillow 11.3.0. No dependencies were installed. Logs and the
temporary original-F1 export stay local under
`data/processed/hnlo_gpu_monitor_validation/`, excluded from Git. The worktree
Git descriptor is relative for Windows/WSL compatibility and is untracked.

Commands from the relevant checkout root:

```text
python3 -m unittest tests.test_hnlo_train tests.test_hnlo_train_v4 -q
python3 -m unittest tests.test_ls1 tests.test_pa3_native tests.test_pa3_full_train tests.test_pa3_r2 tests.test_qwen_runner tests.test_qwen3_runtime_placement tests.test_internvl3_prep tests.test_internvl3_runtime_result -q
python3 -m unittest tests.test_hnlo_capture tests.test_hnlo_t1_cpu tests.test_hnlo_one_click tests.test_internvl3_hnlo_probe tests.test_internvl3_monitor tests.test_internvl3_recovery tests.test_internvl3_driver tests.test_resource_pilot tests.test_resource_pilot_dataset_path -q
python3 -m unittest tests.test_resource_pilot.SourceNotebookTests.test_source_lock_all_bytes -q
python scripts/build_hnlo_train.py
python -m unittest tests.test_hnlo_train.NotebookTests tests.test_hnlo_train_v4.BudgetTests tests.test_hnlo_train_v4.GPUSamplingTests.test_replacement_notebooks_discover_only_the_new_pr_branch tests.test_hnlo_train_v4.GPUSamplingTests.test_null_grant_blocks_before_gpu_polling -q
python3 -m unittest tests.test_hnlo_train.NotebookTests tests.test_hnlo_train_v4.BudgetTests tests.test_hnlo_train_v4.GPUSamplingTests tests.test_hnlo_train_v4.PreservationTests -q
python -m compileall -q safeshift/diagnostics/hnlo_train scripts/build_hnlo_train.py scripts/profile_hnlo_train.py tests/test_hnlo_train.py tests/test_hnlo_train_v4.py
git diff --check
```

The historical group runs once on BASE and once on replacement. The single
V3 assertion runs on the unmodified exported old F1. Final post-generation
source/notebook/branch checks and the committed 651-file proof are reported in
the new Draft PR. The only changes after the 64-case run are branch-constant
consistency, its assertion and documentation/regenerated artifacts; final focused
checks cover those changes. No full repository discovery, rerun of the unchanged
941-sample profiler, GPU/model validation, real TRAIN access, Kaggle, checkpoint
download, new grant, F2, Antigravity or merge is performed. The original profiler
numbers above remain historical observations, not new measurements.
