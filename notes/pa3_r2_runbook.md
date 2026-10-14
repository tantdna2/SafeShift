# PA3-R2 full TRAIN preparation (2026-10-14)

Status: implementation for Draft review; **GPU execution NOT AUTHORIZED**.
BASE `486b4af7ad1f402395b60b0c36ebfd80a74cf4de`; independent of PR #102.
Stop after ChatGPT GitHub review handoff. Antigravity audit requires a later request.

## Evidence and limits

Source: Research Lead's task report dated 2026-10-14 and the candidate reviewed at
[PR #102](https://github.com/tantdna2/SafeShift/pull/102), HEAD
`78b45b688abe609edcfa27b9bcf9874d42ed984a` (`nan_probe.py`, `nan_probe_run.py`, CPU tests).
The Lead reports four completed Tesla T4 / FP16 / SDPA diagnostic passes with
Qwen2.5-VL-3B-Instruct, Transformers 4.51.3:

- `power-Level04-Wheeled-001764-002`: without clamp, 151,936/151,936 first-step
  logits NaN; block 31 output and merger input contain one -Inf; RMSNorm creates NaN.
- With pre-merger clamp: zero NaN/Inf in first-step logits; clamp activates.
- `metallurgy-Level04-Wheeled-001232-001`: clamp on/off logits are bitwise identical.
- ChatGPT checked 14/14 SHA-256 receipts, **as reported by the Lead**. Those GPU
  receipts were not independently downloaded/reverified in this preparation task.

This confirms the observed boundary and candidate mitigation on the two images.
The exact operation producing -Inf inside block 31 is **UNRESOLVED**. No full-model
32-token T4 run or full TRAIN success is claimed. No new GPU/model-weight access,
TRAIN image/annotation access, TEST access, or downloaded dependencies in this task.

## Implementation and experiment identity

DEC-PA3-010 implements the Lead's choice to rerun **all 3,763 original TRAIN IDs**
as a new experiment. No repair/resume of original Shard 0; no pooling with it.
The official `QwenRawScorer` installs a scoped `visual.merger` pre-hook only for
`full-train-r2`. Original modes retain their original generation behavior and grants.
Qwen revision `66285546d2b821cf421d4f5eb2576359d3770cd3`, FP16, SDPA, C1, tokenizer,
preprocessing, max_new_tokens=32, decoding and PA3 formula are unchanged.

Exact PR #102 candidate semantics: an entirely finite tensor is returned unchanged
(including FP16 extrema); otherwise clamp the tensor to ±(65504 - 1000), rounded
to ±64512 in FP16. NaNs remain NaNs. On a triggered tensor, large finite values
can also be clipped, as in the GPU-tested candidate; their count is recorded.
The hook does not clamp logits, change precision or rescue outputs. Invalid raw
logits are saved then rejected. The normal parser/scorer still records INVALID or
TECHNICAL_ERROR; technical failures stop the shard, with no retry or skip-ahead.

Run IDs: `pa3-qwen-r2-train-shard-0` through `pa3-qwen-r2-train-shard-3`.
Sizes 941/941/941/940; original deterministic seed/order and all image SHA-256s retained.
Results live under `data/processed/pa3_qwen/<R2-run-id>` with separate report,
telemetry, exposure, tickets, staging and export siblings. Mixing R2/old modes is
explicitly rejected by CPU merge. TRAIN remains previously exposed exploratory
data; this rerun does not establish an independent evaluation cohort.

`data/manifests/pa3_r2_full_train.v1.json` is a small content-addressed manifest:
it pins the existing full metadata manifest and four original GT-free manifests,
and specifies the new IDs and SHA-256s of their canonical R2 projections.
Projection changes only experiment/schema/run/clamp identity, never sample rows.
Runtime verifies the original bytes, projection bytes and authority binding.
R2 manifest SHA-256: `e842c9e08f7fa28f72fa8536bc35fd7b5e2ad751481cb812c73e9f201f95afcf`.
`r2.load_full` also validates the complete original 3,763-ID disjoint universe.
No raw TRAIN files are needed to reproduce this preparation:

```sh
python -m safeshift.pa3.native.r2_prepare --output data/processed/pa3_r2_manifest_check.json
```

The output must match the committed R2 manifest byte-for-byte. At execution,
the unchanged per-shard checksum preflight verifies actual attached TRAIN images.

## Authority and release (Research Lead, later)

`configs/pa3/r2_authority.v1.json` has `grant: null`, `implementation: null`.
The old full-TRAIN/technical/90-image authorities remain byte-identical to BASE;
none can authorize R2. Null grant denies parent, child, direct scorer and dataset
helpers. DECISIONS text, manifest generation and receipts do not grant rights.

After ChatGPT review and a separately requested Antigravity audit, Lead must approve
the exact R2 technical/execution scope. Release follows the existing B -> single F1
-> authority-only F2 -> standard merge M rule. F2 sets implementation=audited F1
and grant with decision `DEC-PA3-010`, explicit approval text, R2 full-manifest hash,
four exact R2 shard IDs/counts/projection hashes, runtime inventory hash and prior
technical seal/source-bundle hashes. No self-referential SHA: M/bundle hashes go
only into the generated release notebooks after merge. Git topology proves source
integrity, not human approval; Lead independently checks M on audited main and
maintains the external per-shard attempt ledger across Kaggle sessions.

The original four-image technical audit is reused as prior evidence only. It does
**not** prove R2 32-token T4 safety. If Lead requires an additional GPU qualification
before R2, it needs its own explicit scope/grant; this PR does not add hidden calls.

After actual approval and M, a release maintainer runs this CPU-only command once:

```sh
python -m safeshift.pa3.native.r2_prepare --release --output data/processed/pa3_r2_release
```

It denies on this Draft. On an authorized source it checks authority/manifests,
creates a Git source bundle/receipt and **four filled notebooks**, one per shard.
Upload this release as a private Kaggle Input. Do not hand-edit grants or notebook
hashes. The tracked template deliberately has empty source pins and cannot run.

## Minimal Kaggle owner steps (only after release)

1. Import the generated `PA3_R2_SHARD_0.ipynb`. Attach the new R2 release, existing
   approved Model Prep, Runtime Prep/inventory, original technical source bundle,
   extracted technical qualification journal, and TRAIN dataset. Select T4,
   Internet OFF. The resolver discovers unique paths and checks authority-bound
   hashes; ambiguous/missing Inputs fail closed. It prunes DATA_PATH/TEST trees.
   Model discovery is a locator only; pinned snapshot bytes are checked on restore.
2. Record the shard/version in the external attempt ledger; **Save Version -> Save
   & Run All once**. Download `PA3_R2_TRAIN_SHARD_0_OUTPUT.tar.gz` and its receipt.
   A saved Version is not proof of a successful run; inspect failure/audit records.
3. Import notebooks 1, 2 and 3 with the same Inputs/settings, one recorded attempt
   each. Preserve every Output, including failures. Never rerun a failed notebook.
   CPU-reverify the four packages before pooling results; any new attempt needs
   Lead authorization and a distinct reviewed identity.

No manually entered attachment paths, 17-field settings dictionary or source/hash
edits are required in generated notebooks. No GPU execution by Codex.

## Per-image persistence and recovery

Before each image: `.attempt` with sample ID/path/hash. Before merger execution:
`.clamp-00` with triggered flag, +Inf/-Inf/NaN counts, overflow count, finite clipped
count, shape/dtype/policy. After generation: `.native`, each of up to 32 `.step-NN`
records, `.raw`, then `.result` or `.error`. The run manifest/model evidence binds
prompt, source, revision, generation config, runtime and run ID. CPU audit joins
clamp evidence to each status; CSV exposes clamp/overflow/NaN columns. Null means
unobserved (not attempted or interrupted before the hook), never false.

R2 uses PR #102's durable staging -> fsync -> atomic no-overwrite hard link pattern
for every raw-run record and SHA-256 receipt. Files are durable after each image;
packaging/reporting is not required to retain earlier images. A torn last receipt
is detectable; no journal is repaired, overwritten or resumed. Generation interrupted
mid-call may lack the current image's full raw output; this remains INCOMPLETE.
If Output survives a killed process, use CPU-only recovery on its retained journal:

```sh
python -m safeshift.pa3.native.durable --run data/processed/pa3_qwen/pa3-qwen-r2-train-shard-0 --output data/processed/pa3_r2_recovery_0
```

Recovery classifies COMPLETE/ERROR/INCOMPLETE/CORRUPT_OR_TORN/NOT_ATTEMPTED and
reports leftover staging files without changing raw files or loading a tokenizer.
It is an integrity report, not an independent score audit. Final sealed runs use:

```sh
python -m safeshift.pa3.native.train_report --snapshot <pinned-tokenizer-directory> --runs <R2-shard-0> <R2-shard-1> <R2-shard-2> <R2-shard-3> --output data/processed/pa3_r2_report
```

Host deletion/timeout can still remove Kaggle working storage; local fsync cannot
guarantee platform Output retention. Download saved artifacts promptly. No automatic
restart, cross-session resume, remote upload or claim of zero possible data loss.

## CPU verification

Existing pinned environment: torch `2.6.0+cpu`, Transformers `4.51.3`.
`python -m unittest tests.test_pa3_r2 -v` covers manifest identity, closed authority,
real synthetic Git release topology, Input discovery, exact official-runner 32-step
FP16/SDPA generation using a tiny random Qwen (no pretrained weights), last-block
overflow mitigation, bitwise identity of all 32 raw logit tensors without overflow,
earlier NaN rejection/raw retention, hook removal, four-shard workflow/CPU merge,
hard process exits after images 1/2/3, torn receipts and no overwrite/retry.
Tiny architecture has two vision blocks; it tests integration, not the real block
31 operation or real Qwen weights. CPU measurements are not T4 performance evidence.

Validation: 17 distinct R2 tests PASS (the 16 in the broad run plus the added
release-generation test); final workflow audit changes rechecked, 2/2 PASS.
Native/full-TRAIN/boundaries regression: 67/67 PASS. Broader pinned CPU command:

```sh
python -m unittest tests.test_pa3_r2 tests.test_pa3_native tests.test_pa3_full_train tests.test_pa3_boundaries tests.test_pa3_synthetic tests.test_pa3_feasibility tests.test_pa3_runtime_prep tests.test_pa3_seminar_direction -q
```

That run executed 195 tests: 190 PASS, 4 platform/opt-in SKIP, 1 inherited FAIL
(`test_committed_grant_is_null_and_prior_authority_untouched`). The same failure
was reproduced from `git archive 486b4af7ad1f402395b60b0c36ebfd80a74cf4de`: the old
90-image grant is already populated, contrary to the old test's null assertion.
No authority was changed to satisfy this test. No other failures/errors.
`compileall`, notebook cell compilation and `git diff --check` PASS.
T4 32-token generation, full 3,763-image results, Kaggle wall-time/VRAM and platform
hard-kill Output retention remain unverified. Scope/metrics/data are unchanged.
