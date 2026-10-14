# PA3 TRAIN Shard 0: NaN diagnosis and guarded-continuation candidate

2026-10-14, Asia/Bangkok. BASE/source M:
`486b4af7ad1f402395b60b0c36ebfd80a74cf4de`. Preparation and CPU fault injection
only; **real continuation BLOCKED**. No GPU, model load, image read, TEST access,
retry, authority change or merge. This note records the user's diagnostic task;
recommendations inside the supplied audit were treated as evidence/context,
not as independent execution instructions.

## Verified evidence

Sources: supplied `SafeShift_PA3_Shard0_Audit_2026-10-14.md`, original local
`PA3_TRAIN_SHARD_0_OUTPUT.tar.gz`, and code at M. Archive SHA-256:
`2b3a12dcca12320622aa4e71641506f95565426bacbe1b78804d4acdacd0e293`.
Read selected records and CSV directly from the archive in memory; no extraction,
overwrite or dataset read. Independently verified all **1,363 JSON/receipt pairs**
and all **six exact journal inventories/seals**. This is integrity, not a signature
or proof of numerical correctness. `bootstrap/source.json` identifies M and bundle
SHA-256 `2416fe409dcb7109352d031b2e6df7eb678ca432cd646b9cd3e33c115aabff3d`.

- Original planned/byte-verified set: 941. Results: 84 SUCCESS, one TECHNICAL_ERROR,
  856 NOT_ATTEMPTED. Score coverage 84/941 = 8.9267%; `completed=false`.
- Index 84 / image 85: `power-Level04-Wheeled-001764-002`, image SHA-256
  `c11429a2c00fde564fe7e909c3f8d24f1a6cec6775087d52c0cc4c476bd4cb65`.
  All 151,936 raw logits are NaN at each of 32 recorded steps. IDs are 32 zeros;
  text is 32 exclamation marks. Result is `RAW_NAN_OR_INF`, score null.
- Index 83 is valid with the same `input_ids=[1,1782]`,
  `pixel_values=[4888,1176]`, `image_grid_thw=[[1,52,94]]`. Shape/token count
  alone cannot explain failure; equal shapes do not imply equal pixel values.
- Recomputed AUROC from `samples.csv` by all Anomaly/Normal pairs, tie credit 0.5:
  PA3 **0.7748987854251013**, generated binary label **0.5**, on the same
  19 Anomaly and 65 Normal SUCCESS IDs. Descriptive partial results only, not a
  full-TRAIN baseline, improvement claim, PA3 threshold metric or TEST result.
- Failure record: `ValueError`, `F_ONE_PASS`, `retry_permitted=false`.
  No model-state baseline/fingerprint was retained in the old archive.

Local CPU-check summary (ignored, not committed):
`data/processed/pa3_shard0_diagnosis/archive_cpu_check.json` in this worktree.
Reproduction procedure: stream the archive with Python `tarfile`, verify SHA-256
and byte length against every sibling `.sha256.json`; compare each `seal.json`
with its exact JSON record inventory; select SUCCESS CSV rows and compute
`sum((a > n) + 0.5*(a == n))/(19*65)` for PA3 and generated binary labels.
Use the retained original archive, never a reconstructed run.

## Diagnosis: established versus unresolved

At M, `QwenRawScorer.generate` saves native IDs and raw/processed summaries before
scoring. `native_score.score` validates the raw trace; all-vocabulary NaN is
rejected independently of the decoded label. `workflow.infer` then unconditionally
raises on any TECHNICAL_ERROR. `execute_train` seals the partial run and exports
all planned IDs; the remaining 856 are NOT_ATTEMPTED. Thus the **whole-shard stop
is a verified orchestration policy**, not loss of the 84 prior results.

The **root cause of NaN remains unknown**. Plausible alternatives include
image-dependent FP16 activation overflow/nonfinite preprocessed values, persistent
model state corruption, or a runtime/kernel issue. There are no saved layer/input
value probes or before/after state measurements that distinguish these. Byte
checksum PASS establishes image identity, not numerical safety. All later decode
steps being NaN can follow a poisoned within-call KV cache; that alone does not
prove cross-image contamination. The temperature warning is not evidence of the
numerical cause; generation is explicitly greedy.

`safeshift/runners/qwen2_5_vl.py::_validate_model` checks placement, precision,
layout and configuration, **not parameter/buffer values**. A successful validator
therefore cannot certify state safety. `qwen.py` already clears top-level
`rope_deltas` and `_cache` before each call. It does not pass prior `past_key_values`
between images. Its `failed` flag is set on exceptions inside generation, but
the raw-scoring NaN is detected later, outside that method.

The pinned [Transformers v4.51.3 Qwen2.5 implementation](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen2_5_vl/modeling_qwen2_5_vl.py)
stores RoPE deltas at the outer model and creates a dynamic cache when none is
provided. Its forward path includes FP16 vision/linear operations. This supports
the hypotheses and the existing cache locations; it does not localize this run's
failure or establish that persistent state remained healthy.

## Minimal candidate and safety boundary

Only full-TRAIN orchestration opts into the new guard. Other PA3 modes retain
their existing stop policy. No scorer, score formula, prompt, tokenizer, revision,
precision, NaN validation, metric definition or authority/config file is changed.

1. Before the first sample, append `state-baseline`: synchronized, validator-
   checked, finite state fingerprint. Hash parameters, all buffers including
   nonpersistent ones, direct tensor attributes, module scalar metadata and model/
   generation configs. CPU transfer is bounded to 1,048,576 elements per chunk;
   no weights are persisted. Nonfinite initial state aborts before image inference.
2. Only a fully persisted/re-read result whose errors are exactly
   `["RAW_NAN_OR_INF"]` may enter the guard. Generation exceptions, OOM, interrupts,
   malformed traces, disk/checksum failures and other errors remain terminal.
3. Reverify the saved baseline, synchronize, validate, clear only the already
   reviewed top-level RoPE/KV fields, and repeat the state fingerprint. Any change,
   nonfinite tensor, unknown state, probe failure or inability to persist proof
   blocks continuation and latches the scorer failed. No repair, reload, replay,
   replacement image or canary model call is attempted.
4. Only an exact finite state match and recorded cache clearance permits the next
   manifest ID. Keep the bad sample's raw evidence, error and null score. CPU audit
   validates the proof/sample/baseline relationship and rejects an attempted tail
   after a missing/blocked/mismatched proof, even if that journal was re-sealed.
5. If every ID is attempted but any TECHNICAL_ERROR remains, write failure
   `TRAIN_EXHAUSTED_WITH_TECHNICAL_ERRORS`, seal/export, and keep `completed=false`.
   Coverage can improve without redefining completion or imputing a missing score.

**This is a fail-closed preparation candidate, not production recovery clearance.**
Opaque attributes (hooks, closures, callable native state) are deliberately
unsupported; they yield `UNAVAILABLE`, never an inferred PASS. In particular the
pinned rotary implementation has a `rope_init_fn` callable. This candidate has no
reviewed proof for that callable or installed runtime hooks, so real Qwen recovery
must remain blocked pending a narrow, source-backed state inventory/qualification.
Do not whitelist opaque state just to make a check pass. A finite unchanged tensor
fingerprint alone does not establish arbitrary native/Python state safety.

The positive continuation test proves orchestration under a controlled CPU state
model. It does **not** prove the archived Qwen instance was safe, or that the native
T4 model can recover. CPU evidence cannot promise subsequent logits will be finite.
If real runtime state cannot be certified without extra inference, keep stopping;
any such diagnostic inference needs its own explicit approval.

## Blockers and required Lead decision (not granted)

- **Scientific:** root cause is unresolved; the archive cannot retrospectively
  establish a healthy persistent-state baseline. Preserve the original incomplete
  run and its evidence. Never claim image 85 is independently/reproducibly bad.
- **Technical:** complete the pinned native state inventory and independently review
  the guard. Real state-fingerprint support, cost and CUDA behavior are unmeasured;
  no installed torch/Transformers or native model was used in this task. No real
  recovery PASS or GPU readiness is claimed. A future technical qualification
  requires separate authority; it must not silently consume a TRAIN image/call.
- **Authority:** M's one-pass Shard 0 attempt is consumed. The changed source cannot
  inherit M's exact-source authority. No new grant, F2, merge or executable recovery
  manifest is produced here. Recommend holding unused shards 1–3 pending review;
  this recommendation does not revoke or extend their existing budgets.
- **Requested Research Lead approval, if pursuing the 856 untouched images:** a
  separate prospective run ID and authority bound to reviewed source, original
  archive/run seal, original 941-ID manifest and a hash-bound GT-free subset equal
  exactly to its 856 NOT_ATTEMPTED IDs. Exclude all 85 attempted IDs (including the
  failed image); at most one new call for each of the 856, no retry/replacement or
  TEST. Preserve Qwen/C1/revision/FP16/SDPA and PA3 scoring, raw capture, seals and
  exposure history. Lead must approve the failure/continuation policy, checks and
  budget, plus any separately bounded technical qualification. Subsequent combined
  reporting must retain provenance, the failed ID and the original denominator;
  do not relabel this as DEC-PA3-007 retry or an independent holdout.

## CPU validation

Windows, Python 3.11.9, numpy 2.4.6, Pillow 11.3.0; CPU doubles only. Synthetic fixtures, no seeds
or stochastic inference. Commands from the branch worktree root:

```console
python -m unittest tests.test_pa3_state_guard -q
python -m unittest tests.test_pa3_full_train tests.test_pa3_native -q
python -m unittest tests.test_pa3_synthetic tests.test_pa3_boundaries tests.test_pa3_feasibility tests.test_pa3_runtime_prep tests.test_pa3_seminar_direction -q
git diff --check
```

Final counts and BASE comparison are recorded below. Logs are
under `data/processed/pa3_shard0_diagnosis/` (ignored). No full-repository test run,
native tokenizer recomputation of the real archive, GPU/model execution or TEST
read was performed; these are outside this CPU/code diagnosis. Real archive
verification covers bytes, recorded trace facts and CSV AUROC, not a native model
reproduction.

- Final guard + full-TRAIN suites: **29/29 PASS** (11 new guard tests, 18 TRAIN
  regressions); native + full-TRAIN command: **54/54 PASS** (36 native tests).
  Deduplicated focused coverage is **65 tests, all PASS**. Negative cases include
  finite parameter/buffer mutations, NaN/Inf state, opaque attributes, cache reset,
  CUDA-sync/validator failures, interruption, disk failure, tampered baseline,
  re-sealed invalid continuation proof, preserved raw/null score and partial exports.
- **98 protected files match exact BASE bytes**, including all configs, prompts,
  tracked manifests, native generator/scorer, LS1 runtime/core, access/train
  authority code and metric/report implementations. `compileall` and staged
  `git diff --check` PASS. No dataset/archive/raw output is staged.
- BASE comparison: the historical
  `tests.test_pa3_seminar_direction.AuthorityTests.test_committed_grant_is_null_and_prior_authority_untouched`
  fails at M because the merged 90-image grant is non-null. Reproduced on a fresh
  LF checkout of exact M; neither that test nor the authority was edited. This is
  a known unrelated regression, not permission to remove a grant. Full BASE suite
  was not repeated.
- Additional five-module PA3 regression: **125 run, 120 PASS, 4 SKIP, 1 inherited
  FAIL**, 588.705 seconds. Skips are host/platform constraints and opt-in real Linux
  runtime checks. The sole failure is the grant-null test above. Across distinct
  test identities: **190 run, 185 PASS, 4 SKIP, 1 inherited FAIL**; regression is
  explicitly not wholly green. Initial shell redirection reports unittest stderr
  as PowerShell `NativeCommandError`; the final Python-managed focused logs preserve
  the actual zero exit codes. Test-created bootstrap failure messages are synthetic
  negative cases, not execution/retry of the real Shard 0.
