# Eight-image resource pilot: Kaggle dataset discovery V3 (2026-10-19)

Implementation/review only; `grant=null`. Stop at one new Draft PR. No Kaggle
execution, checkpoint download, GPU/model load, grant, F2, Antigravity or merge.
BASE: `6d345fe11426a3c01815439081dca0a8983dd33c` (main / PR #119 merge).
Branch: `fix/hnlo-pilot8-dataset-path-v3-20261019`.

## Evidence and scope

Source: Owner's task request on 2026-10-19, reporting direct Kaggle checks after
PR #119. Qwen3 V2 failed `train_preflight`, 0/8 images, before image-byte reads,
checkpoint provisioning and model load. Owner found exactly one TRAIN root:

```text
/kaggle/input/datasets/nguynanhtn/inspecsafe-v1-kaggle/InspecSafe-V1-Kaggle/train
```

Owner reports `ROOT_EXISTS=True`, `ROOT_ALIAS=False`, all eight files existing
with `nlink=1`, `alias=False`, `ok=True`, and `METADATA_OK=8/8`. This is supplied
Kaggle evidence, not an independent Kaggle execution or artifact inspection here.
Code inspection confirms V2 examines only immediate input mounts and therefore
misses `datasets/<owner>/<slug>`. This repair does not diagnose CUDA or relax
metadata/path safety. Synthetic CPU fixtures reproduce the exact directory shape.

## Explicit discovery boundary

Accepted mount prefixes are `/kaggle/input/<mount>/` (retained) and exactly
`/kaggle/input/datasets/<owner>/<slug>/` (added). Each prefix accepts only:

| TRAIN root relative to prefix | Required child |
| --- | --- |
| prefix itself | `DATA_PATH/train/Annotations/` |
| `InspecSafe-V1/` | `DATA_PATH/train/Annotations/` |
| `InspecSafe-V1-Kaggle/train/` | `DATA_PATH/train/Annotations/` |

No recursive glob/walk or arbitrary descendants. Discovery lists the input
directory and, only for its literal `datasets` child, owners and their slugs.
The total enumeration budget across those directories is **512 entries**, files
included; exceeding it fails closed. It never lists inside the candidate TRAIN
roots or reads image/annotation bytes while discovering. Zero safe matching roots
fails `TRAIN_ROOT_NOT_FOUND`; multiple matching roots fail `MULTIPLE_TRAIN_ROOTS`
with their paths relative to input. Ambiguity is never resolved by picking the
first root or preferring whichever has the eight images. Unsafe aliases anywhere
in the examined prefixes/paths fail, including dangling symlinks.

The existing `no_alias`/`safe_path` containment, canonical-path, symlink/junction
and traversal checks remain. Images must be regular files with exactly one hard
link. As before, this assumes an immutable read-only Kaggle mount; pathname checks
are not a defense against a malicious host mutating files between checks.

## Failure evidence and unchanged execution order

Authority/source proof and exclusive new-attempt consumption still precede
discovery and image metadata. All eight image locators are checked before any
image-byte reads. The existing staging journal then records read-start, hashes,
copies and exposure before software/checkpoint setup or any model worker.
Metadata failure reads zero images; SHA failure retains the actual read prefix
and stops before later images. No retry, resume, skip or second attempt is added.

Controlled `TrainInputError` diagnostics add fields to the existing error objects,
without changing result/evidence schemas, packaging, custody or raw-summary
contracts. `result.json` and `supervisor.json` retain `phase` and `reason` plus
relative root paths, or the first failing image's `ordinal`/`image_locator`.
Preflight failures also populate the existing `train-preflight.json` with the
same error and explicit no-image-byte/no-GT-read flags. Existing staging failure
receipts retain the same error on a staging failure; hash errors include expected
and actual SHA-256. No arbitrary exception text or machine-local absolute root
is copied into these diagnostics.

| Case | Reason |
| --- | --- |
| No root | `TRAIN_ROOT_NOT_FOUND` |
| More than one root | `MULTIPLE_TRAIN_ROOTS` |
| Enumeration exceeds budget | `TRAIN_DISCOVERY_ENTRY_LIMIT_EXCEEDED` |
| Root/prefix alias or unsafe path | `UNSAFE_TRAIN_DISCOVERY_PATH` |
| Discovery metadata cannot be read | `TRAIN_DISCOVERY_METADATA_UNREADABLE` |
| Missing image | `TRAIN_IMAGE_MISSING` |
| Non-regular image metadata | `TRAIN_IMAGE_NOT_REGULAR_FILE` |
| Image metadata cannot be read | `TRAIN_IMAGE_METADATA_UNREADABLE` |
| Image hardlink alias | `TRAIN_IMAGE_HARDLINK_ALIAS_FORBIDDEN` |
| Image alias/traversal | `UNSAFE_TRAIN_IMAGE_PATH` |
| Wrong original SHA | `TRAIN_IMAGE_HASH_MISMATCH_NO_SKIP` |
| Wrong copied SHA | `STAGED_COPY_HASH_MISMATCH` |

## New notebooks and null authority

These are the two fixed-model pilot Run All notebooks, reading the original
Dataset directly; no Dataset PREP notebook or upload is introduced:

- `notebooks/SafeShift_HNLO_RESOURCE_PILOT8_qwen3_DATASET_PATH_V3.ipynb`
- `notebooks/SafeShift_HNLO_RESOURCE_PILOT8_internvl3_DATASET_PATH_V3.ipynb`
- Authority: `configs/diagnostics/resource_pilot_authority.v3.json` (`grant=null`).
- Source lock: `configs/diagnostics/resource_pilot_source.v3.json`.

| Model | New run ID | New attempt ID |
| --- | --- | --- |
| Qwen3 | `hnlo-pilot8-v3-qwen3-s0-a1` | `resource-pilot8-v3-qwen3-20261019-a1` |
| InternVL3 | `hnlo-pilot8-v3-internvl3-s0-a1` | `resource-pilot8-v3-internvl3-20261019-a1` |

Owner reports Qwen3 V2 consumed; InternVL3 V2 has not run. Neither V2 grant
transfers. PR #118/#119 grants, old units even grafted into a new scope, and
decision/audit URLs at PR <=119 are rejected. New selected per-model Lead
approvals must bind the new implementation and payload after review/audit.
The existing exact BASE -> single F1 -> authority-only F2 -> standard merge
verification remains required. The notebooks cannot run a Draft/unmerged source.
No authority-only child is prepared in this task.

V1/V2 notebook/authority/source-lock/provenance/runbook bytes remain unchanged.
Both earlier scopes match V3 except run/attempt identity and BASE binding.
Models, C1, eight ordinals/hashes, HNLO/raw-summary/CPU replay, software/checkpoint
pins, guard/driver/security code, GT/TEST isolation, exposure/retention, artifact
contract and retry/resume policy remain unchanged. PR #117 remains untouched.
DEC-PA3-011 remains PROPOSED and D9R22 remains EFFECTIVE. No dataset, split,
label, metric or future baseline reuse/exclusion decision changes.

## Validation

Only generated eight-image JPEG fixtures are used; no real Dataset bytes or model
checkpoints are opened. The released notebook declarations are executed with
external source/runtime boundaries replaced by CPU doubles; real discovery,
metadata, staging, consumed-attempt, custody and archive paths are exercised.

| Actual check | Result |
| --- | --- |
| Linux pilot/path suite (command below) | **70 run, 70 PASS, 0 SKIP/FAIL/ERROR**, 21.507 s. All three layouts at both prefixes, exact Owner tree in both notebook cells, one/zero/multiple roots, wrong prefixes/depth, enumeration budget boundary, missing images, nonregular/hardlink/unreadable metadata, SHA mismatch, real/dangling symlinks, traversal, early stop, raw-summary/CPU replay and release tests. |
| Windows path suite | **33 run = 24 PASS + 9 SKIP**, 18.630 s; host symlink creation is unavailable. Those symlink cases PASS on Linux above. |
| Linux eight-module baseline/native/runner regressions | **257 run = 251 PASS + 6 SKIP**, 39.409 s; optional tokenizer/ML dependencies skipped. |
| Linux seven-module capture/release/security regressions, unfiltered | **161 run = 147 PASS + 10 SKIP + 4 FAIL**, 41.309 s; exactly the four historical failures listed below, no errors. This group is FAIL WITH BASELINE FAILURES. |
| Same four historical identities on unchanged BASE | **4 run, 4 FAIL**, 0.188 s; original checkout HEAD exactly BASE and no tracked changes. Same null-grant assertions and old DECISIONS.md source-lock mismatches. |
| Static/source checks | Package/builder/tests compile; diff whitespace checks pass. Both V3 cells compile with empty outputs and the new source payload. Tests compare V1/V2 release artifacts against BASE Git blobs and scientific scope against both authorities. Final builder/source-lock verification also runs after documentation updates. |

The initial combined Windows/Linux check exposed one new test-fixture mistake:
the notebook bootstrap uses its own session directory rather than `work/`.
The test's evidence lookup was corrected; the final suites above pass. No runtime
policy was changed to fix that assertion. A further CPU case covers unreadable
image metadata and the exact enumeration-budget boundary.

Actual environments: WSL Linux Python **3.14.4**, Pillow **13.0.0**; Windows Python
**3.11.9**, Pillow **11.3.0**, all preinstalled. The isolated worktree's local Git
descriptor uses a relative path so both Git implementations can access history;
that descriptor is not tracked. These are CPU validations, not installation or
validation of the pinned Kaggle/model environments.

Reproduce from repository root (use `python` for Windows):

```text
python3 -m unittest tests.test_resource_pilot tests.test_resource_pilot_dataset_path -q
python -m unittest tests.test_resource_pilot_dataset_path -q
python3 -m unittest tests.test_ls1 tests.test_pa3_native tests.test_pa3_full_train tests.test_pa3_r2 tests.test_qwen_runner tests.test_qwen3_runtime_placement tests.test_internvl3_prep tests.test_internvl3_runtime_result -q
python3 -m unittest tests.test_hnlo_capture tests.test_hnlo_t1_cpu tests.test_hnlo_one_click tests.test_internvl3_hnlo_probe tests.test_internvl3_monitor tests.test_internvl3_recovery tests.test_internvl3_driver -q
python -m compileall -q safeshift/diagnostics/resource_pilot scripts/build_resource_pilot.py tests/test_resource_pilot.py tests/test_resource_pilot_dataset_path.py
python scripts/build_resource_pilot.py
git diff --check
```

Historical failure identities, reproduced separately on unchanged BASE:

- `tests.test_internvl3_hnlo_probe.ContractTests.test_null_exact_scope_and_new_attempt`
- `tests.test_internvl3_hnlo_probe.NotebookTests.test_single_cell_source_lock_and_bootstrap_failure_export`
- `tests.test_internvl3_driver.ContractTests.test_null_old_grants_missing_flags_and_changed_scope_rejected`
- `tests.test_internvl3_driver.NotebookTests.test_generated_notebook_and_every_locked_source_byte`

The old authorities are already granted but PREP assertions expect null; the old
whole-tree locks already mismatch BASE's DECISIONS.md. No old authority, source
lock, test or release bytes are rewritten to obtain a PASS claim. These failures
are disclosed, not newly waived. See the V2 runbook for earlier history.

Full repository discovery, actual Kaggle runtime, pinned environment installation,
CUDA/GPU/model/checkpoint, real Dataset JPEG/hash validation and independent
audit are **NOT RUN**. Actual post-repair Kaggle success is not claimed. The two
V3 notebooks remain blocked pending review and new per-model grants.

## Changed files

- `safeshift/diagnostics/resource_pilot/orchestrate.py`: bounded discovery and
  controlled input diagnostics in existing evidence.
- `safeshift/diagnostics/resource_pilot/bootstrap.py`,
  `safeshift/diagnostics/resource_pilot/contract.py`: V3 source/authority identity.
- `scripts/build_resource_pilot.py`: generate the two V3 pilot notebooks/lock.
- `tests/test_resource_pilot_dataset_path.py`: synthetic layout, early-failure,
  evidence, alias and historical-release preservation checks.
- `configs/diagnostics/resource_pilot_authority.v3.json`,
  `configs/diagnostics/resource_pilot_source.v3.json`: new null authority/lock.
- Both `notebooks/SafeShift_HNLO_RESOURCE_PILOT8_*_DATASET_PATH_V3.ipynb` files.
- `DECISIONS.md`, `TASKS.md`, this runbook: scope, evidence and actual validation.
