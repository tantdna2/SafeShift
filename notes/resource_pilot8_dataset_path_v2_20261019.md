# Eight-image resource pilot: original Kaggle Dataset path V2 (2026-10-19)

PREPARATION ONLY; `grant=null`; no Kaggle execution, checkpoint download, GPU,
self-grant, independent audit invocation or merge. Stop at one new Draft PR.
BASE: `a65a706d3110995537e500137a4e889a8ff66b07` (main / PR #118 merge).
Branch: `prep/hnlo-pilot8-dataset-path-20261019`.

## Evidence and bounded repair

The Owner reports PR #118's Qwen3 attempt passed setup/CUDA/checkpoint and then
failed `image_staging` with ValueError, 0/8 processed. Original Kaggle artifacts
were not supplied or independently inspected in this task. Source inspection
confirms that the old discovery omits the Owner's reported Dataset layout.
This is a path compatibility repair, not a claim of new Kaggle runtime success.

Only these roots relative to each immediate `/kaggle/input/<dataset-mount>/`
are accepted (each must contain `DATA_PATH/train/Annotations/`):

| Root | Status |
| --- | --- |
| mount itself | Retained |
| `InspecSafe-V1/` | Retained |
| `InspecSafe-V1-Kaggle/train/` | Added for the existing original Dataset |

No recursion or searching arbitrary descendants; no archive extraction, PREP V2,
new Dataset, re-upload, auxiliary notebook or Owner code/path edits. Exactly one
root across all mounts/layouts must exist; duplicates fail closed. Canonical
containment checks reject traversal, symlinks, junction/realpath aliases at input,
mount, root, Annotations, image directory and file. JPEG hardlink aliases are also
rejected. Checks assume the approved read-only Kaggle Dataset remains immutable;
these pathname checks do not provide a sandbox against a malicious mutable host.
Only eight committed inference-manifest locators are inspected/opened. TEST,
JSON/TXT annotations, GT/full manifests and arbitrary JPEGs are not opened.

## Early checks, attempt and exposure

The actual released single-cell bootstrap verifies a new merged release and
source inventory before entering the supervisor. Order after source proof:

1. Validate new model-specific authority; exclusively consume its new attempt.
2. Verify unchanged shard-0 manifest and bind all eight ordinals/IDs/image hashes.
3. `train_preflight`: uniquely resolve TRAIN root; metadata-check all eight
   distinct JPEGs, safe paths and regular files. No image-byte reads here.
4. Host preflight and resource sampling; `image_staging`: existing append-only
   read-start/hash/timing journal, hash and copy exactly eight images. Stop on
   first mismatch; untouched tail remains unread. No decode or inference.
5. Pinned environment setup, fresh guarded CUDA admission, checkpoint provisioning,
   fresh guarded inference, raw seal, offline CPU replay and failure-preserving export.

Thus missing/unsafe paths stop before any image bytes or provisioning. Wrong SHA
stops before software/checkpoint/worker calls, retaining actual staging exposure.
Metadata checks are not counted as image-byte exposure. All-eight accounting,
attempt consumption on failure, no retry/resume and external cross-session ledger
requirements remain unchanged. No separate attempt or implicit second chance is
created by preflight. If raw model evidence does not exist, skip the unavailable
tokenizer/environment CPU replay and export the supervisor/staging evidence; do
not install software to audit an input failure.

## Independent V2 release and pending authority

V1 notebook/authority/source/provenance/runbook bytes are preserved. The current
Python entrypoints/builder use these new artifacts and cannot execute old grants:

- `configs/diagnostics/resource_pilot_authority.v2.json` (`grant=null`)
- `configs/diagnostics/resource_pilot_source.v2.json`
- `notebooks/SafeShift_HNLO_RESOURCE_PILOT8_qwen3_DATASET_PATH_V2.ipynb`
- `notebooks/SafeShift_HNLO_RESOURCE_PILOT8_internvl3_DATASET_PATH_V2.ipynb`

| Model | New run ID | New attempt ID |
| --- | --- | --- |
| Qwen3 | `hnlo-pilot8-v2-qwen3-s0-a1` | `resource-pilot8-v2-qwen3-20261019-a1` |
| InternVL3 | `hnlo-pilot8-v2-internvl3-s0-a1` | `resource-pilot8-v2-internvl3-20261019-a1` |

Owner reports Qwen3's old attempt consumed; InternVL3 V1 has not run. Neither
PR #118 model grant transfers. Each selected V2 unit needs its own explicit new
approval after this PR's source audit. Reject decision/audit URLs from PR <=118.
The existing exact F1 directly from BASE -> authority-only F2 -> standard merge
contract remains. Both notebooks discover only the new fixed release branch,
carry the new full source-payload digest and require its immutable merge/tree.
No F2/grant is produced here. PR #117 and historical releases remain unchanged.

Scientific scope remains byte-for-byte equivalent: first eight shard-0 ordinals,
image SHA-256, C1, HNLO formula, model revisions/environments/GPU placement,
post-guard driver security, raw-summary contract (`full_vocab_replay=false`),
no GT/TEST, no retry, one load/eight maximum generate calls. Existing exposure,
retention, resource projection and incomplete monitoring limitations remain in
[the historical pilot runbook](resource_pilot8_20261019.md). Dataset definition,
split, labels, metrics and future baseline exposure disposition are unchanged.

## CPU validation

Fixtures are eight small generated RGB JPEGs, never real Dataset bytes.
Notebook tests execute declarations from both released cells with only external
source fetch/runtime boundaries replaced; they exercise real supervisor discovery,
metadata checks, attempt consumption and export on a missing eighth image.
No real Kaggle/model/checkpoint/GPU operation is performed.

| Actual check | Result |
| --- | --- |
| Linux `python3 -m unittest tests.test_resource_pilot tests.test_resource_pilot_dataset_path -q` | **54 run, 54 PASS, 0 SKIP/FAIL/ERROR**, 14.507 s. Includes real symlinks at mount/input/TRAIN/Annotations/image-parent/file, hardlinks, duplicate mounts/layouts, all three supported layouts, invalid paths, eight generated JPEGs, wrong SHA, no GT/TEST image reads, null/old authority, actual notebook early stop, consumed ledger, staging exposure, existing guard order/raw-summary/HNLO/export and Git release tests. |
| Windows `python -m unittest tests.test_resource_pilot -q` | **37 run, 37 PASS**, 201.680 s. |
| Windows `python -m unittest tests.test_resource_pilot_dataset_path -q` | **17 run = 13 PASS + 4 SKIP**, 10.078 s. Host cannot create symlinks; the same four tests pass on Linux above. |
| Windows eight-module baseline/native/runner regression command below | **257 run = 251 PASS + 6 SKIP**, 186.527 s. Optional tokenizer/ML checks skipped; no GPU result. |
| Linux four-module capture/release regression command below, unfiltered | **97 run = 89 PASS + 6 SKIP + 2 FAIL, 0 ERROR**, 32.227 s. Exactly the two old PR #116 null-grant/full-tree-lock assertions listed below. |
| Linux monitor/recovery/driver command below, unfiltered | **64 run = 58 PASS + 4 SKIP + 2 FAIL, 0 ERROR**, 20.302 s. Exactly the analogous old PR #115 null-grant/full-tree-lock assertions below. |
| All four historical failure identities rerun on unchanged BASE | **4 run, 4 FAIL, 0 ERROR**, 0.077 s; same grant assertions and DECISIONS.md lock mismatches already fail before this change. |
| Compile/diff checks | Resource-pilot package, builder and both test modules compile; `git diff --check` PASS. Both new notebook ASTs compile, outputs remain empty, fixed models/ordinals and normalized payload hashes verified by the 54-test suite. V1 artifact Git-blob bytes and scientific scope equivalence verified. |

Environments actually used: Windows Python **3.11.9**, Pillow **11.3.0**;
WSL Ubuntu Linux Python **3.14.4**, Pillow **13.0.0** (existing installations;
not claims of validation under the pinned Kaggle environments). The newly created
worktree's local `.git` descriptor was made relative so both Git implementations
can read its history; initial Linux runs with the Windows absolute descriptor
had Git lookup errors. Reruns above have no Git errors. No tracked Git metadata,
historical lock/test, dependency pin or security code was changed to obtain PASS.

Reproduce the additional regression groups from repository root:

```text
python -m unittest tests.test_ls1 tests.test_pa3_native tests.test_pa3_full_train tests.test_pa3_r2 tests.test_qwen_runner tests.test_qwen3_runtime_placement tests.test_internvl3_prep tests.test_internvl3_runtime_result -q
python3 -m unittest tests.test_hnlo_capture tests.test_hnlo_t1_cpu tests.test_hnlo_one_click tests.test_internvl3_hnlo_probe -q
python3 -m unittest tests.test_internvl3_monitor tests.test_internvl3_recovery tests.test_internvl3_driver -q
python -m compileall -q safeshift/diagnostics/resource_pilot scripts/build_resource_pilot.py tests/test_resource_pilot.py tests/test_resource_pilot_dataset_path.py
python scripts/build_resource_pilot.py
```

The unfiltered historical groups are **FAIL WITH BASELINE FAILURES**, not clean
PASS. Preserve these exact failure identities:

- `tests.test_internvl3_hnlo_probe.ContractTests.test_null_exact_scope_and_new_attempt`
- `tests.test_internvl3_hnlo_probe.NotebookTests.test_single_cell_source_lock_and_bootstrap_failure_export`
- `tests.test_internvl3_driver.ContractTests.test_null_old_grants_missing_flags_and_changed_scope_rejected`
- `tests.test_internvl3_driver.NotebookTests.test_generated_notebook_and_every_locked_source_byte`

The old authorities are already granted, while their PREP tests assert null;
their historical whole-tree locks already conflict with BASE's DECISIONS.md.
This PR preserves those bytes and records the mismatch instead of rewriting old
releases or filtering failures into a PASS claim. The first two were documented
as historical exceptions in the V1 pilot runbook; the latter two were independently
confirmed against BASE here and are not treated as a newly approved exception.

Full repository discovery, actual Kaggle filesystem/runtime, pinned environment
installation, CUDA/GPU/model/checkpoint, real Dataset JPEG verification and
independent audit are **NOT RUN**. The path is Owner-provided and exercised using
synthetic fixtures; actual mounted Dataset contents remain unverified. The Draft
notebooks remain blocked pending independent review and new per-model grants.
