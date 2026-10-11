# Task 3B — PA3 synthetic-only CPU preparation

Authority: DEC-PA3-001, **APPROVED_PREPARATION_ONLY** (2026-10-11).
BASE: `a7146bbb2c44eb26160f26716af23a8b70260dee`, verified on GitHub main.
Implementation/review **PENDING**. This is not model qualification or a study result.

From the repository root, with the existing Python 3.11 environment:

```powershell
python -m unittest tests.test_pa3_synthetic tests.test_pa3_boundaries -v
$pa3Source = git rev-parse HEAD
python -m safeshift.pa3 run --mode synthetic --run-id pa3-synthetic-demo-001 --source-commit $pa3Source
python -m safeshift.pa3 audit --mode synthetic --run-id pa3-synthetic-demo-001 --source-commit $pa3Source
```

No installation, network, Pillow, tokenizer, torch, transformers or GPU is
needed for PA3. Run and audit require the same source SHA and ordered case
list. Use a new run ID for each synthetic run; existing runs cannot be resumed
or overwritten. `--cases` selects only names in `safeshift/pa3/policy.py`.
Examples: `constant_anomaly constant_normal`, `reversed_anomaly reversed_normal`,
or `anomaly interrupt normal`. Exit 0 means a completed synthetic journal;
exit 2 after a run/audit means partial/stopped, not model failure or qualification.

The implementation accepts only built-in deterministic traces and a declared
2x2 RGB mock object. GT is an arbitrary test mapping, not inferred from pixels
or filenames. The ASCII mock tokenizer is not Qwen's tokenizer. Qwen2.5 revision
`66285546d2b821cf421d4f5eb2576359d3770cd3` is recorded as a future target only.
No prompt is executed; C1 and P2/P2.1 remain unchanged.

All execution/storage/audit/evaluation entrypoints validate synthetic settings.
Unknown fields, real modes, dataset/image/model paths, caller backends,
tokenizers, receipts and guard/calibration options are refused. The CLI reads
no settings file and accepts no dataset/archive/snapshot/output-path switch.
Artifacts are confined to `data/processed/pa3_synthetic/<run-id>/`; symlink and
junction aliases are refused. Direct raw-writer/scoring calls also require
exact catalog evidence. Primitive pure math/serialization functions are not
loaders or execution paths. These restrictions are API boundaries, not a
sandbox against an operator modifying Python source or the process itself.

`pa3-synthetic-raw-v1` stores a manifest, ordered cohort, mock-input pixel hash,
method/target/source identity, implementation-source SHA-256 hashes, Python/OS,
deterministic configuration, and per-sample attempt/raw/result files. Source SHA
is caller-declared provenance, never permission; source-byte hashes disambiguate
uncommitted code. Every write is exclusive, fsynced, SHA-256 checked and reread.
Raw response/IDs and both raw/processed step vectors/summaries precede parsing.
Nonfinite mock values use explicit JSON tags so failed evidence remains readable.
There is no `reference_key`, reference artifact or artificial calibrated branch.

CPU scoring reuses LS1 validity, single-token branch, round-trip/alignment,
trace and distribution primitives. `s=LSE(z1,z2,z3)-z4` is evaluated through
the algebraically equivalent normalized-raw log probabilities to preserve a
large common offset; this is not fitted calibration. Processed scores are
audited but never used for `s`. Technical faults stop without retry; format
INVALID stays unscored. Failure/remaining cohort entries are explicit.

The independent reader verifies receipts/inventory, identities, attempt order,
catalog provenance and recomputes results from saved raw, then compares saved
results. An intact journal lacking a final seal is partial/descriptive only;
an attempt without raw or raw without a result remains UNPROCESSED. Torn files,
missing receipts and checksum failures are hard errors and are never repaired.
Checksums are consistency evidence, not signed authenticity or execution rights;
deletion of an entire unsealed tail cannot be proven absent from local hashes.
Storage/process failures can prevent a final seal; preserve the directory for
investigation and do not reuse its ID. No automatic recovery or retry is provided.

Reports use exact unique IDs and the built-in GT join. They include planned,
attempted, persisted (raw/error receipts), parsed (schema-valid even if later
alignment fails), scored, statuses, score-conditional AUROC, eligible IDs/pairs,
and coverage `scored/planned` overall, by level and binary class. Ties earn 0.5;
missing scored classes produce null/NA plus a reason. Scores are never reversed,
and missing scores never become zero or a full-cohort AUROC. Constant-score,
always-Level03 and generated-binary-label controls use the same eligible IDs.

Validation uses only synthetic fixtures. PA3 tests include fresh-process import,
file-access, socket and forbidden-call tripwires; profiling observes ordering
without replacing LS1 functions. LS1 regression itself exercises its historical
calibration functions on synthetic inputs; the no-calibration claim applies to
PA3 run/audit/evaluation, not those unchanged LS1 tests.

```powershell
$env:LS1_QWEN_SNAPSHOT = ''
$env:LS1_INTERNVL_SNAPSHOT = ''
python -m unittest tests.test_ls1 tests.test_ls1_diagnostics tests.test_p21_classification tests.test_p21_harness_evaluation tests.test_d9r23_classification_contract tests.test_d9r24_metrics -v
git diff --check
```

Validation on Windows / Python 3.11.9, unchanged dependencies:

- PA3: **44/44 PASS**, including all 26 built-in cases under fresh-process
  forbidden-operation tripwires, actual KeyboardInterrupt after raw persistence,
  junction rejection, checksum/resealed-result tamper and guarded direct APIs.
- Relevant regression command above: **149 run, 146 PASS, 1 FAIL, 2 SKIP**
  on both the candidate and an isolated checkout of exact BASE. The same failure
  is `tests.test_d9r23_classification_contract.ContractTests.test_exact_scope_history_and_append_only`:
  its historical change allowlist rejects later repository work already at BASE.
  No new failing identity; regression is **NOT wholly PASS**. Historical test
  remains unchanged. Both SKIP are real LS1 tokenizer tests with snapshots
  intentionally unset; they are BLOCKED, never T1 PASS.
- CLI synthetic run and separate audit: **PASS**, exit 0, flow 5 planned /
  5 attempted / 5 raw persisted / 4 parsed / 4 scored. Local ignored artifacts:
  `data/processed/pa3_synthetic/pa3-synthetic-task3b-smoke-001/`. This pre-commit
  smoke declares BASE plus the exact implementation-byte hashes in its manifest;
  its fixture metrics are not research outcomes.
- Protected LS1/frozen/protocol/runner Git bytes, exact append-only original
  prefixes of DECISIONS/TASKS, data-output ignore rule and `git diff --check`: PASS.

Full repository discovery,
real T1/runtime, GPU, model inference, real data and historical result archives
are not run/read in Task 3B. No dependencies are downloaded.

Still blocked: independent implementation review/audit; real Qwen T1, full
snapshot/runtime verification and raw-only technical qualification; separately
approved metadata/image rights, authoritative GT/exposure ledger/dependency graph,
cohort allocation/blinding and TRAIN-dev/holdout execution. Grouped bootstrap,
domain/group inference, CI/decision thresholds and real-data splits are neither
implemented nor frozen here. TRAIN/TEST and DEC-LS1-001/002 stay locked/pending.
No result here establishes PA3 discrimination or Qwen T1/runtime PASS.
