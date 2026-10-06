# D9R24 disagreement-aware reliability metrics

Task `W2.6-D9R24-DISAGREEMENT-RELIABILITY-METRICS` is a prospective,
classification-only implementation stacked on PR B at
`6e205a53a9ceeebbc258d3ad0be6a7ddb865501e`. The machine-readable contract is
[`configs/pre_freeze/d9r24_metric_contract.v1.json`](../configs/pre_freeze/d9r24_metric_contract.v1.json).

The implementation consumes in-memory parsed records and has no dataset, image,
weight, model, GPU, or InspecSafe access. RQ1 preserves D5 balanced accuracy,
Macro-F1, raw accuracy, parse-conditional anomaly/normal and Level01 metrics,
failure-aware metrics, critical downgrade diagnostics, and folder-domain
diagnostics. RQ2 remains image-level, with the 12 Hazard Atoms as primary
overlapping strata and seven A-G groups as secondary exploratory summaries.

RQ3 uses only the four D9R18 classification participants (`qwen3`, `qwen2_5`,
`internvl3`, `moondream`). Its primary denominator is `JOINT_VALID_4`; invalid
outputs are reported in availability and failure tables and never become a
safety level. The engine reports unanimous agreement, six pairwise Cohen
kappas, normalized vote entropy, normalized ordinal disagreement, deterministic
vote patterns, shared blind spots, ordered-pair error complementarity,
disagreement/error association, and a deterministic selective risk-coverage
curve. Ties and invalid records abstain; the rank uses only ordinal
disagreement, vote entropy, and lexical sample ID, so ground truth cannot tune
coverage.

Risk-coverage reports both eligible-relative and overall coverage. Exact and
ordinal risks use the accepted-prefix denominator; the safety-critical
anomaly-to-Level04 risk uses only accepted anomalies in each prefix, with an
undefined value before the first accepted anomaly. AURC is explicitly
`aurc_eligible_cohort` over eligible-relative coverage.

Bootstrap metadata follows the approved domain-stratified policy: `B=2000`,
seed `42`, percentile 95% intervals, explicit `point_id` clusters for Normal
records, and shared draws for paired comparisons. Normal records without
`point_id` hard-fail bootstrap. Current anomaly records resample at sample level
with an explicit dependence limitation; arbitrary point-like metadata and
source-family are ignored. Missing class support yields `NA` (`null`), never an
imputed zero. The report serializer is deterministic and rejects NaN or
Infinity.

This is offline synthetic-test evidence only. It is not runtime qualification
on InspecSafe, does not reactivate historical grounding, and does not freeze the
implementation or protocol. `inspecsafe_inference_authorized=false`,
`MODEL_GPU_EXECUTION=NO`, `INSPECSAFE=NOT_RUN`, and `PROTOCOL_FREEZE=PENDING`.

## Methodology correction record (2026-10-06)

The correction in PR #81 supersedes the earlier implementation details above
where they conflicted with the approved methodology. Focused D9R22/D9R23/D9R24
and relevant classification qualification regression tests pass (`106/106`).
The corrected full suite has 1556 tests with 5 historical failures, 25
historical errors and 2 skips. The exact PR B baseline log has 1540 tests with
the same 5 failure and 25 error identities; `NEW_FAILURE_IDENTITIES_VS_BASE=0`.
The unchanged failures are historical roster/allowlist, stale main-identity,
precision and checklist guards; notebook errors are fresh-kernel barriers.
No model, GPU or InspecSafe execution occurred.
