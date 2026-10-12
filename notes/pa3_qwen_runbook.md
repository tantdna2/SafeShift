# PA3 Qwen raw-only — owner Run All

TASK 4, 2026-10-12. BASE `540078902370c88aede1d6c30be73f29fce6722e`,
verified against GitHub main before preparation. Code candidate only: no real
T1/runtime PASS, GPU/model execution, dataset read or research result in Codex.
One Draft PR; stop for ChatGPT GitHub review, then separately requested
Antigravity audit and merge. HEAD/PR are recorded in the handoff.

| Component | Status | Meaning |
| --- | --- | --- |
| Native Qwen raw-only backend, one notebook, journal/CPU audit/evaluator | READY for code review | CPU API-double and synthetic-fixture validation; not real qualification |
| Existing PA3 mock path, LS1, P2/P2.1, RQ3 and frozen contracts | Preserved | New implementation is only in `safeshift/pa3/native/`; old entrypoints unchanged |
| Real Qwen T1, exact snapshot/runtime, technical qualification | BLOCKED | No actual supplied snapshot/runtime was read or executed here |
| GPU technical execution | CẦN RESEARCH LEAD APPROVAL | Separate decision and audited authority implementation; cannot be enabled in notebook settings |
| Metadata/images, authoritative GT, exposure ledger, reviewed dependency graph | CẦN RESEARCH LEAD APPROVAL | Separate scoped rights and custodian evidence; candidate interchange schema is not dataset discovery |
| Allocation, statistical appendix, confirmatory interpretation | CẦN RESEARCH LEAD APPROVAL | Algorithms are proposals with explicit parameters, not frozen rules or independence evidence |
| Exact TRAIN-dev / TRAIN-holdout runs | BLOCKED | Separate reviewed grants, exact cohort/source/method/owner/run identity; holdout also needs dev audit and blinding/freeze |
| TEST | BLOCKED | Remains locked; no PA3 TEST workflow |

**This revision stops at AUTHORITY.** `native/access.py` unconditionally denies
technical GPU, metadata, images, TRAIN and confirmatory statistics. It has no
receipt/env/boolean unlock, plugin grant, or alternate backend option. A later
Research Lead decision must be implemented and audited in source before owner
execution. Approval of this preparation PR or changing `mode` alone is
insufficient. LS1 locks stay unchanged. Do not edit the gate locally or
monkeypatch it; patches in tests are solely for CPU fixtures.

## One Run All after the prerequisites exist

1. Obtain the reviewed, audited execution source release and exact effective
   rights. Record source SHA, owner, unique run ID, model/method/prompt, exact
   cohort/exclusions/GT/exposure/graph/allocation hashes, attempt budget and
   artifact destination. Technical permission is separate from TRAIN rights.
   Do not derive authority from the integrity receipts below.
2. From the clean approved checkout, create the source Add Input once:

   ```text
   python -m safeshift.pa3.native.kaggle --bundle-source --output data/processed/pa3_release
   ```

   Attach `pa3_source.bundle` and preserve `pa3_source_release.json`. The bundle
   contains committed Git history, allowing exact commit/ancestor/file-byte
   checks in Kaggle. No working dataset, weights, credentials or outputs enter
   it. Record its SHA-256 independently. A Draft bundle is not execution rights.
3. Attach the existing Qwen Model Prep (exact revision directory or archive)
   and existing relocatable pinned Runtime Prep; no pip/install/download in
   this notebook. Reuse its independently verified runtime inventory, or
   inventory existing prep bytes with the existing CPU helper:

   ```text
   python -m safeshift.ls1.kaggle --inventory-runtime PREP_RELATIVE_PATH --repo . --output data/processed/pa3_runtime_inventory.json
   ```

   The inventory must be outside the prep directory. Record its SHA-256
   independently. Runtime hashes are checked before executing that Python.
4. Only when separately authorized, attach the approved cohort plan and
   read-only image root. The plan is the internal schema in
   [cohort.py](../safeshift/pa3/native/cohort.py), **not** an automatic converter
   from undocumented real InspecSafe metadata. Custodian population/provenance
   remains blocked until authorized. Image locators are relative to that root;
   no TEST discovery, scan or read. Each image is checked against its pinned
   SHA-256 before decode. Ground truth is not supplied to the model.
5. Open **only** [pa3_qwen2_5_kaggle.ipynb](../notebooks/pa3_qwen2_5_kaggle.ipynb).
   Fresh kernel, T4, Internet OFF. Fill its single SETTINGS cell with the
   approved mode (`technical`, `train-dev`, `train-holdout`), run ID, exact
   source SHA, bundle path/hash, model/runtime/inventory paths/hash, optional
   exact site-packages path; TRAIN additionally needs cohort plan path/hash
   and dataset attachment path. Paths in this cell are input-relative.
   **Run All once.** The child sees only CUDA device 0.

A verifies committed source and executable/config/prompt byte inventories.
B verifies Runtime Prep before interpreter execution, the full model snapshot
(including SHA-256), exact Linux/Python/library pins, processor and native state.
C records the actual Qwen T1 28-variant result. D executes four synthetic
drawings on real Qwen, then seals and CPU-audits; at least one valid extracted
score is required. All INVALID cannot qualify. E validates the authorized
TRAIN plan/exposure/graph/partition. F runs each planned image once with C1,
FP16, SDPA, official pixel bounds, greedy decoding and 32-token cap. G seals
raw before GT join, CPU-recomputes and exports a descriptive evaluation.
Technical mode stops after D. No data rights follow from D PASS.

## Collect and audit

Download every `data/processed/pa3_qwen/RUN*` journal/archive/hash and the
bootstrap failure package; retain the exact source bundle and input inventories.
Audit the technical `RUN-qualification` journal or the TRAIN `RUN` journal:

```text
python -m safeshift.pa3.native.native_audit --run data/processed/pa3_qwen/RUN-qualification --snapshot TOKENIZER_SNAPSHOT_RELATIVE_PATH
```

For TRAIN, add `--report data/processed/pa3_qwen/RUN-report` to recompute the
saved evaluation from its sealed metadata as well. This needs only the pinned
CPU tokenizer libraries, not torch/GPU/weights. See [artifact and analysis
contract](pa3_qwen_artifacts_and_analysis.md) for raw fields, incomplete-run
semantics, proposed cohort/bootstrap tooling and interpretation limits.

On failure, stop and download the available evidence. Never change revisions,
precision, parser or run ID to retry without new rights. A hard kill/storage
failure may leave an unsealed directory; preserve it for investigation.
CPU results and exact BASE comparison: [validation](pa3_qwen_validation.md).
