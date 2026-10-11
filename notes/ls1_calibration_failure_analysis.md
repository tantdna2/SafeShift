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
| Reference log bias `[-2.7034712, -1.2868045, -0.7555545, -1.7347212]` in Level01–Level04 order; technical yellow-lines selected calibrated Level04 | [ChatGPT review of PR #91](https://github.com/tantdna2/SafeShift/pull/91#issuecomment-6103428447) | Reported values/outcome; raw artifact **not independently audited** |
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
`i`, `z4 - zi > b4 - bi` (the unguarded argmax, as used in technical mode).
Indeed, the calibrated pairwise log-odds are
`log(q4/qi) = (z4 - zi) - (b4 - bi)`. Softmax preserves ordering, and ties
with any earlier canonical class lose for Level04. Also,
`b4 - bi = mean_reference(z_ref4 - z_refi)`: the log-softmax normalizers cancel.
These are score identities, not statements about an image's actual safety.

## (B) Observed behavior, bias effects and unverified explanations

**Level04 remains reachable.** For any finite `b`, the synthetic score vector
`z = b + [0, 0, 0, delta]`, `delta > 0`, has a unique calibrated Level04
maximum. The inequality imposes no upper bound on a real sample's margins.
It therefore cannot prove that real scenes almost never select Level04 or
that the exploratory 0/4 outcome was inevitable. The reported technical
yellow-lines case already selected calibrated Level04. That is reported
runtime evidence, separate from the CPU proof and synthetic regression tests.

**The four labels receive different corrections.** Conditional on the bias
reported in the review, the additive logit shifts are:

| Label | Reported `b_i` | Shift `-b_i` | Boost rank |
| --- | ---: | ---: | ---: |
| Level01 | -2.7034712 | +2.7034712 | 1 |
| Level02 | -1.2868045 | +1.2868045 | 3 |
| Level03 | -0.7555545 | +0.7555545 | 4 |
| Level04 | -1.7347212 | +1.7347212 | 2 |

Level03 has the highest mean reference log-probability, followed by Level02,
Level04 and Level01. This does not give the individual reference predictions;
those require the raw per-reference artifacts. Subtraction boosts Level01
most, **then Level04**, then Level02, then Level03. Absolute logit boosts
do not mean every class probability increases after softmax normalization.
The Level04-vs-Level01 log-odds decrease by `0.9687500`; Level04-vs-Level02
increase by `0.4479167`; Level04-vs-Level03 increase by `0.9791667`.
Equivalently, Level04 needs raw margins greater than `+0.9687500`,
`-0.4479167` and `-0.9791667` against Level01, Level02 and Level03, respectively.
Whether Level04 wins depends on all the sample margins. This pattern is not
a uniform boost of hazard labels or a uniform penalty on Level04.

**Reference semantics are a hypothesis.** Uniform images contain no depicted
industrial hazard, but that does not establish how the model interprets them
under C1 and the sample's forced assistant prefix. They may carry a task- or
prefix-dependent bias rather than a useful neutral prior. The reported bias
favours Level03, so it does not verify the earlier explanation that references
strongly favour Level04 and calibration removes a "safe signal". The actual
mechanism and its effect on unseen industrial scenes remain unconfirmed.

**Tie policy is proven only for a score pattern.** If `z = b + c` for a common
scalar `c`, calibrated scores are equal and the canonical tie rule selects
**Level01**. The `FakeScorer` integration fixture reproduces a three-way tie.
Neither fact establishes that real or near-blank images have those logits.

**Context mismatch is a possible validity limit.** Fixed 448x448 references
use one InternVL3 tile (256 image tokens) and the Qwen2.5 minimum (256 tokens).
The earlier handoff reports historical InspecSafe inputs with 9 InternVL3
tiles (2,304 tokens) or about 1,222 Qwen2.5 tokens. These are input-regime
differences, not proof of their causal effect on calibration. That effect has
not been measured here, and no Qwen2.5 LS1 outcome was reported.

Coefficient, mean type, reference pixels and tie rule remain unchanged.
Changing them after seeing these 10 images would be tuning on observed data.

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
observations cannot establish a prospective benefit. Every presumed-normal image was
escalated. Status: **NO_DEMONSTRATED_BENEFIT**, with a **safety regression
signal** (false Level01 alarms), scoped to this limited reported evidence;
it is not proof of universal method failure. These 10 images must not be used to choose or
tune any successor method.

## What remains open or blocked

- Independent verification of the reported reference log bias `b` and the
  per-reference logits/predictions for the InternVL3 C1 prefix. The vector
  reported above does not replace an artifact audit. Run the
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

Review correction source:
[ChatGPT review at original HEAD 616b605](https://github.com/tantdna2/SafeShift/pull/91#issuecomment-6103428447).
The change adds
`safeshift/ls1/diagnostics.py`, additive LS1 reporting keys in
`safeshift/ls1/evaluate.py`, `tests/test_ls1_diagnostics.py`, this note and
append-only DECISIONS/TASKS entries. `experiment.run`, `core`, `runtime`,
`tokenizer`, `kaggle`, the config, the notebooks, C1, the production code and
authority files are byte-identical to BASE.

### PR #91 review correction validation (2026-10-11)

Environment: Windows x86_64, Python 3.11.9; existing dependencies, no installation.
The focused suite was run in the existing PR worktree and a separate clean
detached worktree at exact BASE, using the same host and environment:

```powershell
python -m unittest tests.test_ls1 tests.test_d9r23_classification_contract tests.test_d9r24_metrics tests.test_d9r25_harness tests.test_d9r26_bridges tests.test_p21_classification tests.test_p21_harness_evaluation tests.test_p21_kaggle tests.test_qwen2_5_runner tests.test_internvl3_prep -v
```

On the corrected branch, also include `tests.test_ls1_diagnostics` in that
command (the module does not exist at BASE).

| Focused regression | Run | PASS | FAIL | ERROR | SKIP | Seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Exact BASE | 306 | 303 | 1 | 0 | 2 | 39.265 |
| Corrected PR #91 | 325 | 322 | 1 | 0 | 2 | 40.939 |

All 19 diagnostics cases PASS, including three added cases covering preserved
or newly selected Level04, exact ties versus positive margins, and the distinct
pairwise bias effects. The original LS1 module runs 68 cases: 66 PASS, 2 SKIP
on both revisions. Skips remain missing pinned real tokenizer snapshots;
they do not count as T1 PASS.

Both revisions fail exactly
`tests.test_d9r23_classification_contract.ContractTests.test_exact_scope_history_and_append_only`.
Its historical phase allowlist already rejects files at BASE. The test is
unchanged; this PR's three new paths also fall outside that old allowlist.
There are no new failing/error identities in the selected regression, which
remains **not green**. Full discovery was not rerun for this documentation and
synthetic-test correction; earlier full-suite counts in the original PR handoff
are historical, not validation of this revision.

`git diff --check` PASS. BASE byte prefixes of DECISIONS/TASKS are preserved;
the exploratory metric table is identical to original HEAD `616b605`.
Diagnostics changes affect only explanatory text/comments, with unchanged
executable AST; `evaluate.py` is unchanged from the original PR HEAD.
Ignored logs and comparison receipts remain in each validation worktree under
`data/processed/ls1_pr91_review/`. The corrected commit's exact SHA is recorded
in the PR handoff. Independent ChatGPT review and Antigravity audit are pending.
