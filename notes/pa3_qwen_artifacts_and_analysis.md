# PA3 native artifacts, CPU audit and candidate analysis

Operational steps: [owner runbook](pa3_qwen_runbook.md).

## Artifacts, CPU audit and failure handling

Artifacts live beneath the restored source's `data/processed/pa3_qwen/`:
`RUN-launch`, `RUN-qualification`, `RUN`, and for TRAIN `RUN-report`.
Each has an exclusive JSON journal, SHA-256 sidecars, inventory seal and a
separate `.tar.gz` + SHA-256. Notebook bootstrap evidence is under
`data/processed/pa3_bootstrap/`. Download all these outputs and retain the
exact source bundle, model/runtime inventories and approved plan/ledger.
The technical top-level RUN is an orchestration summary; audit its
`RUN-qualification` sample journal.

Each sample retains attempt identity/input hash, original native sequence and
input IDs, generation config/overrides, image-grid/shape evidence, every step's
raw and processed candidate values plus full-vocabulary summaries, original
decoded response, timestamp and parser/mapping/results. Native IDs and step
summaries are saved before decode; full raw is saved/reread before parser.
Full vocabulary tensors are not retained (per Task 3A evidence contract).
Errors before full raw still retain any native/step records already written.
There is no forced-prefix reference, calibration call or score tuning.

Independent CPU recomputation uses the exact release and pinned tokenizer-only
snapshot/libraries (Transformers/tokenizers/hub); it does **not** need torch,
GPU or model weights. Example from the restored repo:

```text
python -m safeshift.pa3.native.native_audit --run data/processed/pa3_qwen/RUN-qualification --snapshot TOKENIZER_SNAPSHOT_RELATIVE_PATH
```

The snapshot directory must retain the pinned revision name. The auditor
rechecks T1, source membership/bytes, native/raw/step consistency, generation
contract, token alignment, processed greedy selection and saved results.
Partial intact journals stay partial; missing/torn/tampered records fail.
Checksums do not prove external authenticity, authorization, or independence.
CPU audit of returned summaries cannot reconstruct unretained full tensors.

Any failed stage or interrupt stops and packages the available evidence, with
no fallback/retry/resume/overwrite. A hard process kill or storage exhaustion
can prevent sealing/packaging; retain the entire directory. A failed attempt
does not authorize another run ID. Report/audit failure after raw sealing
leaves raw unchanged and records a separate report failure. No failed or
partial run may support confirmatory conclusions.

## Evaluation and candidate cohort/statistics

`native/analysis.py` reports score-conditional AUROC, exact IDs/pair supports,
planned/attempted/persisted/parsed/scored flow, missing statuses and coverage by
level/binary class/domain/prefix. It includes OVR, three level-vs-Level04
margins, generated-Level03 subgroup, four-class macro only when all four are
defined, domain macro with K, score/log-mass distributions, separate generated
and raw-label confusion/safety counts, constant/always-Level03/generated-label
controls on the same IDs, and leave-one-group-out sensitivity. Completed-run
missing-score bounds are labelled bounds, never measured AUROC or CI.

Pure candidate metadata tools require provenance for GT/exposure/test links,
join transitive exact/Normal-point/reviewed relationships, quarantine whole
observed/unknown/unresolved components, and reject duplicate IDs, bad GT and
partition overlap. No near-duplicate threshold is selected. Allocation takes
explicit salt/fraction; it is never a frozen or independently certified split.
See the original [proposal](pa3_research_protocol_proposal.md) for limitations
from previous P2/LS1 exposure. No real rows were inspected to devise this schema.

`grouped_bootstrap` is a pure **proposed exploratory** engine: explicit draws,
seed and confidence; whole groups, domain strata plus mixed-domain stratum,
shared draws for paired contrasts, invalid-draw/support reporting. No default
quality thresholds or H1 decision rule are frozen; `confirmatory=True` is
unconditionally blocked. The notebook makes no automatic bootstrap or
confirmatory claim. Any approved future statistics must be bound to the
reviewed protocol, not operator-picked after holdout.

CPU checks and exact BASE comparison are recorded in
[validation](pa3_qwen_validation.md). Real T1, runtime qualification, GPU,
InspecSafe reads/TRAIN/TEST and full repository discovery were not run here.
