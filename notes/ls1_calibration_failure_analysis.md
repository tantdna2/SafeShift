# LS1 ls1-v1 calibration: failure analysis and controlled next steps

Date: 2026-10-11 (Asia/Bangkok). BASE main:
`281b697346fdc3f70ccdfe351a4d6b65b7753177` (merge of PR #90). Branch:
`claude/ls1-calibration-diagnosis`. DEC-LS1-001 stays **PENDING**; train/test stay
**LOCKED** (`LS1_SPLIT_EXECUTION_LOCKED_PENDING_DEC_LS1_001`). This note grants
no execution right and claims no accuracy improvement.

## Evidence used and its limits

| Evidence | Source | Status |
| --- | --- | --- |
| `ls1-internvl3-technical-first`: T1 PASS, 4/4 synthetic SUCCESS, raw 4x Level03, calibrated 3x Level01 + 1x Level04 | Research Lead handoff | Sealed artifacts **not available here**; per-call logits not inspected |
| 10 InspecSafe **train** images via standalone `ls1_exploratory10.py` | Research Lead handoff | **Not authorized under LS1**; GT inferred from file names, not verified against the W1 manifest/provenance |
| Cross-check of the 10 sample IDs with historical P2 Qwen2.5 manifests | P2 run archives inspected read-only in an earlier task | All 10 appear as `train` with a matching `Normal_data`/`Anomaly_data` locator. This is consistency, not authoritative GT. One ID overlaps InternVL3 P2.1 shard 0 and matches the LS1 generated label (Level03) |
| LS1 code at BASE | `safeshift/ls1/*.py`, `configs/experiments/ls1.v1.json` | Read in full for core/runtime/experiment/tokenizer/evaluate/audit/artifacts |

No GPU, model weights, Kaggle session or InspecSafe image was used for this work.

## (A) Code and mathematics: no defect found in the reviewed scope

The checks below are code-reading checks plus CPU tests on synthetic data. They
are not GPU verification.

- **Parser/INVALID:** a label is located only after a P2.1 strict-parse success
  (`core.candidates`). INVALID is never rescued.
- **Token alignment:** the whole response is re-tokenized for the four labels.
  It must differ at exactly one position, align to the generated IDs (at most
  one terminal EOS) and round-trip through decode.
- **Raw vs processed:** probabilities use raw `output_logits`. Processed
  `output_scores` are used only for the greedy argmax invariant at every step
  (`validate_trace`).
- **Decision position:** `continuation_ids[step]` must equal the generated
  label's token. The label logits must not exceed the recorded full-vocabulary
  maximum.
- **Reference forced prefix:** for every reference, the sample's exact generated
  prefix is appended to the same C1 chat template (`NativeScorer.prepare`), with
  one generated step. References are cached by SHA-256 of the prefix IDs, and
  the candidate IDs must stay identical.
- **Four-label conditional probability:** stable log-softmax over the four raw
  logits. Full-vocabulary mass is reported separately.
- **Bias:** `b = mean_reference(log_softmax(z_ref))`. Calibrated logits are
  `z - b`. Shift invariance makes this equal to subtracting `b` from log
  probabilities.
- **Integrity:** exclusive fsynced writes, checksum inventory, raw-before-parse,
  and CPU recomputation in `audit.py`.

New tests (`tests/test_ls1_diagnostics.py`) pin the bias to the official
`calibrate()` bit-for-bit. They also check an algebraic identity on 3,000
synthetic cases: calibrated Level04 holds exactly when, for every other class
`i`, `z4 - zi > b4 - bi`.

## (B) Why the method fails even if the code is correct

1. **The references are not label-neutral for this task.** Contextual
   calibration assumes a content-free input carries no information about the
   label. For a hazard task, a uniform gray/black/white image is the most
   hazard-free input possible. It is strong evidence *for* "no abnormality" and
   against Level01/Level02. Subtracting `b` therefore removes the "safe" signal
   itself, not just a format prior.
2. **Level04 becomes structurally unreachable.** By the identity above, a sample
   is calibrated to Level04 only if its Level04 log-odds over every hazard class
   exceed those of the blank references (`b4 - bi`). Any real industrial scene
   contains structure, people or equipment, so it looks *less* hazard-free than
   a blank image. That makes 0/4 Level04 after calibration the expected outcome,
   not a numerical accident.
3. **Hazard classes are amplified most.** Blank references give very low
   Level01/Level02 log-probabilities. `-b_i` is therefore largest for Level01, so
   small increases of Level01 evidence over a blank image dominate the decision.
   This matches the technical run: hazard-free drawings were calibrated to
   Level01 (3/4). In the 10-image run, all four presumed-normal scenes went to
   Level01/Level02.
4. **Tie policy.** An input whose logits equal the reference mean becomes
   uniform after calibration, and the tie rule picks **Level01**. The decision for
   near-blank inputs is then driven by tiny differences. The `FakeScorer`
   integration fixture already reproduces this three-way tie.
5. **Context mismatch.** References are 448x448: one InternVL3 tile (256 image
   tokens) and the Qwen2.5 minimum (256 tokens). Historical InspecSafe inputs use
   9 InternVL3 tiles (2,304 tokens) or about 1,222 Qwen2.5 tokens, so the bias
   is measured in a different input regime. This is a second, independent
   validity limit. Its size is unmeasured.
6. **What was not changed.** Coefficient, mean type, reference pixels and tie
   rule are untouched. Changing them after seeing these 10 images would be
   tuning on observed data.

Label-free technical gate added as a diagnostic (`diagnostics.hazard_free_sanity`):
a correction must not raise a hazard-free synthetic input to Level01/Level02 or
increase its severity. Applied to the reported technical pattern, it returns
**FAIL** (3 alarms, 3 escalations). This rule was declared after observing the
technical run and is disclosed as post hoc.

## 10-image exploratory table (descriptive only, n=10, already observed)

GT is the provisional file-name label. 95% intervals are Wilson intervals per
image, not cluster-adjusted.

| Metric | Uncalibrated LS1 | Calibrated LS1 |
| --- | --- | --- |
| Accuracy | 2/10 (0.06-0.51) | 3/10 (0.11-0.60) |
| Balanced accuracy | 0.25 | 0.375 |
| Level01 recall | 0/2 (0-0.66) | 0/2 (0-0.66) |
| Level04 recall | 0/4 (0-0.49) | 0/4 (0-0.49) |
| True normals predicted Level01/Level02 | 0/4 | **4/4 (0.51-1.0)** |
| Level01 misses | to Level02: 1, to Level03: 1 | to Level02: 2 |
| Prediction distribution | L02=1, L03=9 | L01=3, L02=5, L03=2 |

Only one image moved from wrong to correct (tunnel Level02, Level03 → Level02).
No image moved from correct to wrong. With a single discordant pair, the
improvement is indistinguishable from chance. Every presumed-normal image was
escalated. Status: **NO_DEMONSTRATED_BENEFIT**, with a **safety regression
signal** (false Level01 alarms). These 10 images must not be used to choose or
tune any successor method.

## What remains open or blocked

- Actual reference log-probabilities `b` for the InternVL3 C1 prefix. Run the
  new CPU command on the sealed technical run directory:
  `python -m safeshift.ls1.diagnostics --run data/processed/ls1/runs/ls1-internvl3-technical-first --output <new file>`.
  It verifies checksums and recomputation first, then prints `b`, the
  per-reference predictions, the required Level04 log-odds and the hazard-free
  sanity result. No GPU is needed.
- Authoritative GT and SHA-256 for the 10 images (W1 manifest/provenance):
  BLOCKED pending permission.
- T1 for Qwen2.5 and any Qwen2.5 LS1 run: not reported.
- Whether uncalibrated four-label scores discriminate normal from anomalous
  images (AUROC): unmeasured on any authorized data.

## Proposed controlled path (requires Research Lead decision; nothing implemented)

1. **Suspend ls1-v1 calibrated predictions as a decision rule.** Keep ls1-v1
   uncalibrated scoring as a measurement of discrimination (score-conditional
   AUROC) and as a reproduction of greedy decisions.
2. **At most two successor candidates, versioned separately and predeclared
   before any run:**
   - *ls1-v2-threshold* (label-using, supervised condition): a single
     anomaly/normal operating threshold on the uncalibrated anomaly log-odds,
     selected on train-dev under a predeclared constraint (Level01 failure-aware
     recall not below uncalibrated). This is InspecSafe threshold tuning, which
     needs an explicit D9R22 exception. It must be reported as a supervised
     condition, not zero-shot.
   - *ls1-v2-matched-null* (label-free): a per-image null reference at the
     sample's own resolution/tiling (for example a fixed heavy blur), removing
     the context mismatch. Risk: blurred images can read as smoke/fog, which
     would bias towards Level01. Not validated.
3. **Prospective evaluation on train only; official test untouched.**
   - Clusters: normal `point_id`, per D2.
   - Exclude the 10 observed exploratory IDs and every image sharing their
     clusters.
   - Assign clusters to train-dev or train-holdout by SHA-256(predeclared salt ‖
     cluster ID), stratified by domain × anomaly status.
   - Freeze salt, sizes, candidates, endpoints and success rule in DECISIONS
     **before** any LS1 output is read.
   - Use train-dev for the single selection step; evaluate train-holdout once.
4. **Endpoints, all reported for both arms on the same images:**
   - Level01 and Level04 recall (failure-aware).
   - Balanced accuracy and macro-F1.
   - 4x4 confusion and prediction distribution.
   - INVALID count and denominators.
   - Normal→Level01/Level02 alarm counts and Level01 misses.
   - Paired transitions.
   - Uncertainty: D9R24 domain-stratified point-cluster bootstrap. The Wilson
     intervals here are exploratory only.
   - Success requires a predeclared improvement **and** no increase in
     normal→Level01 alarms **and** no decrease in Level01 recall.
5. **Approval procedure:** Research Lead decision entry (rights, split, sizes,
   salt, candidates) → ChatGPT/Antigravity review of a separate implementation
   PR → owner run → sealed artifacts → CPU audit/diagnostics → report. If the
   evidence does not support a candidate, close LS1 with
   `NO_DEMONSTRATED_BENEFIT`.

## Validation of this change

See the PR handoff for exact commands and counts. The change adds
`safeshift/ls1/diagnostics.py`, additive LS1 reporting keys in
`safeshift/ls1/evaluate.py`, `tests/test_ls1_diagnostics.py`, this note and
append-only DECISIONS/TASKS entries. `experiment.run`, `core`, `runtime`,
`tokenizer`, `kaggle`, the config, the notebooks, C1, the production code and
authority files are byte-identical to BASE.
