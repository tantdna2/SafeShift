# Task 6 — Runtime Prep repair and separate ONLINE source

Date: 2026-10-12 (Asia/Bangkok). BASE and retained OFFLINE source:
`13ea2fba67f36883518db8a2add1b249c951e48e` (PR #96 merge).
This is a Runtime Prep change only, awaiting ChatGPT review then Antigravity
audit. Stop at Draft PR. It grants no new technical or dataset rights.
No GPU, model weights, tokenizer/T1, InspecSafe or Qwen generation was used.

## Status at Draft handoff

| Check | Venue | Result |
| --- | --- | --- |
| Original `ensurepip` call fails with `externally-managed-environment`, marker unchanged | Real Linux (WSL), real uv 0.6.14 + Python 3.11.11 | PASS (reproduced) |
| Fixed install: 43 packages, all ten pins, `pip check` | Real Linux | PASS |
| 1. Imports/versions/origins after moving the built tree | Real Linux | PASS (`3a40b46`) |
| 2. Archive created | Real Linux | PASS (`3a40b46`) |
| 3. Strict extract to a new path after deleting the built tree | Real Linux | PASS (`3a40b46`) |
| 4. Unchanged OFFLINE path: `verify_runtime_input` + `runtime_interpreter(archive)` + child-module import | Real Linux | PASS (`3a40b46`) |
| Same OFFLINE path again, from a fresh process | Real Linux | PASS (`3a40b46`) |
| Unit, negative and mocked sequence tests | Windows CPU (+ Linux CPU) | PASS (see below) |
| Kaggle CPU Runtime Prep with the reviewed prep commit | Kaggle | NOT RUN — owner step after review/audit |
| Qwen load, T1, GPU/T4, technical run | — | NOT RUN, not in scope |

WSL is not Kaggle. Kaggle's host Python (3.13), disk and network can still
fail; only the owner's Kaggle receipt is Kaggle evidence. Kaggle's
`/kaggle/working` capacity for the ~8.3 GiB peak was not verified here.

Code, notebook and test bytes were last changed in `3a40b46` (tested
`prep.py` SHA-256 `66c581d3df7d6e277d9d2ba7fa4645d639d34118aea7f9133f77b13d10164bdb`);
later commits on this branch change documentation only.

## Observed failure and root causes

The Research Lead reports a **real Kaggle CPU / Internet ON failure**: checkout
of BASE, uv 0.6.14 installation and Python 3.11.11 download succeeded, then
`python -m ensurepip` failed with `externally-managed-environment`. The former
code asked ensurepip to install pip into uv's managed interpreter, which PEP 668
forbids. This was reproduced on real Linux (log retained, see below).

Review of the handoff found a **second, latent BASE defect** on the same path:
`runtime()` wrote `pa3_runtime_inventory.json` beside `pa3_runtime.tar.gz`, but
the unchanged `ls1.kaggle.inventory_runtime` refuses an inventory inside the
archive's directory (`WRITE_RUNTIME_INVENTORY_OUTSIDE_PREP_INPUT`). The earlier
Codex Linux log shows exactly this error **after** a successful archive and
restore check (the handoff described that run as a WSL disconnect while
writing the archive; the retained log says otherwise). On Kaggle it would have
failed after the multi-GB build. The archive now lives in `runtime-archive/`.

## Fix

uv 0.6.14 `pip install --python <managed> --target <separate dir> --link-mode copy`.
The target is outside the interpreter's installation scheme, so the
EXTERNALLY-MANAGED marker stays and is shipped intact. No
`--break-system-packages`, marker deletion, version substitution or skipped
dependency check. All ten pins are unchanged (Python 3.11.11, torch
2.6.0+cu124, torchvision 0.21.0+cu124, transformers 4.51.3, …). Torch and
torchvision come as exact cp311 Linux x86_64 CUDA 12.4 wheels from the official
PyTorch index; everything else resolves from PyPI in the same transaction under
the original constraints, wheels only.

Archive layout (no venv, no `pyvenv.cfg`, no activation, no host Python):

```text
runtime/python/bin/python3.11               # full uv-managed standalone interpreter
runtime/python/lib/python3.11/...           # its stdlib + EXTERNALLY-MANAGED
runtime/packages/site-packages/...          # separately installed libraries
```

The unchanged `ls1.kaggle.runtime_interpreter` finds the interpreter and the
one `site-packages` that satisfies all pins; the unchanged PA3 launcher then puts
that directory on the child's PYTHONPATH. Keep `runtime_site_packages` empty.
Console entry points (install-time shebangs) are kept out of the archive in
`excluded-console-scripts/`; the OFFLINE child only uses `python -m`.

Prep sequence (`safeshift/pa3/native/prep.py`, `runtime()`):

1. Install, then move the whole interpreter + packages payload to `relocated/`.
   Probe it with the real child interpreter (`-B -s`, PYTHONPATH = selected
   packages only): every pinned version, every module **and** its distribution
   metadata, the interpreter, `sys.prefix` and `sys.base_prefix` must resolve
   inside the runtime root; the Qwen2.5-VL class imports (no weights); torch
   CUDA build is 12.4 and CUDA is not initialised. Host `pip --python … check`.
   All symlinks must exist and stay inside the root.
2. Pack the archive (contained relative links only).
3. **Delete** `relocated/` and `build/`, so no earlier path or file can mask a
   broken archive. Extract with the unchanged strict `safe_extract` to
   `archive-roundtrip/`, repeat step 1's checks, compare link map and versions,
   then delete it.
4. Write the inventory, run the launcher's own `verify_runtime_input`, then let
   the unchanged `runtime_interpreter` restore the **archive** itself to
   `data/processed/ls1/runtime/` (exactly as the OFFLINE launcher does), repeat
   the checks, and import `safeshift.pa3.native.workflow` with the launcher's
   PYTHONPATH (source + selected packages), `-s` and OFFLINE env (CPU only:
   `CUDA_VISIBLE_DEVICES` stays empty). Then delete that restore.

`runtime_prep.json` (status `CPU_RELOCATION_ARCHIVE_ROUNDTRIP_IMPORT_PASS_GPU_NOT_RUN`,
with four `checks: PASS`) is written only after all of this succeeds. Any failure
leaves the intermediate directories in place as evidence. Peak disk is roughly
one expanded runtime (≈5.4 GiB) + archive (≈3.0 GiB) after the downloaded
wheels are installed; deleting trees between stages keeps it at that level.
Transitive versions are observed in `resolved-requirements.txt`, not
prospectively locked; each rebuild is a new artifact to audit.

Mechanism references: [uv 0.6.14 CLI reference](https://github.com/astral-sh/uv/blob/0.6.14/docs/reference/cli.md),
[PEP 668 specification](https://packaging.python.org/en/latest/specifications/externally-managed-environments/),
[pip's `--python` option](https://pip.pypa.io/en/stable/topics/python-option/).
These document mechanisms, not evidence that our runtime passed.

## Two source releases, never one substituted for the other

| Purpose | Source commit | Kaggle Dataset (private) | Bundle |
| --- | --- | --- | --- |
| ONLINE CPU prep (runtime/model) | reviewed Task 6 commit `P` | **new** `pa3-reviewed-prep-source` | `pa3_prep_source.bundle` + `pa3_prep_source_release.json` |
| OFFLINE technical run (later, separately authorised) | `13ea2fba67f36883518db8a2add1b249c951e48e` | existing `pa3-reviewed-source` (**do not delete or change**) | `pa3_source.bundle` + `pa3_source_release.json` |

Why this cannot be swapped: the unchanged authority
(`safeshift/pa3/native/access.py`) accepts only HEAD == `source_commit` == the
standard merge whose parents are BASE `747171e…` and the authority-only F2.
Checked read-only: `13ea2fb` is accepted (`pa3-qwen-technical-first`,
`pilot: null`); the Task 6 commit is rejected with
`PA3_STANDARD_MERGE_REQUIRED_DRAFT_LOCKED`. A later merge of Task 6 into main
would be rejected the same way. No authority, scorer, tokenizer, model revision,
precision, run budget or dataset gate is changed.

Guards on the prep side:

- `bundle-source` refuses a dirty tree, a commit that does not descend from
  `13ea2fb`, or any change since `13ea2fb` to OFFLINE execution inputs
  (`safeshift/`, `configs/`, `prompts/`, `notebooks/pa3_qwen2_5_kaggle.ipynb`)
  other than `safeshift/pa3/native/prep.py`. The receipt lists every changed
  path and has `execution_authority: false`. The prep CLI repeats the scope
  check before `runtime`/`model`, so pins come from configs identical to the
  OFFLINE source.
- The prep notebook verifies the bundle SHA-256 you type in, then the receipt
  (schema, prep commit, bundle hash, fixed OFFLINE commit,
  `execution_authority: false`, bundle name `pa3_prep_source.bundle` — the
  OFFLINE `pa3_source.bundle` is refused), then the checked-out commit. It
  records `prep_source_input.json`.
- A checksum is integrity evidence, not approval: ChatGPT/Antigravity audit `P`.

## Owner steps (Windows + Kaggle; no Linux needed)

Prerequisites: Windows with Git and Python 3.11 (the setup already used for
this repository), a Kaggle account with phone verification (needed for
Internet ON). Run steps only after ChatGPT review and the separately requested
Antigravity audit name the exact reviewed commit `P` (full 40-character SHA).

### Step 1 — build the prep-source release on Windows

In PowerShell or Git Bash, in a **fresh** clone (keep it outside any synced folder):

```text
git -c core.autocrlf=false clone https://github.com/tantdna2/SafeShift.git safeshift-prep
cd safeshift-prep
git fetch origin pull/<PR number>/head
git -c core.autocrlf=false checkout --detach P
git rev-parse HEAD
python -m safeshift.pa3.native.prep bundle-source --output data/processed/pa3_prep_release --execute-online-owner-prep
git bundle verify data/processed/pa3_prep_release/pa3_prep_source.bundle
```

`git rev-parse HEAD` must print `P`. Then hash the bundle independently:

```text
PowerShell:  Get-FileHash -Algorithm SHA256 data\processed\pa3_prep_release\pa3_prep_source.bundle
cmd:         certutil -hashfile data\processed\pa3_prep_release\pa3_prep_source.bundle SHA256
```

Open `data/processed/pa3_prep_release/pa3_prep_source_release.json` and check:
`prep_source_commit` = `P`; `offline_source_commit` =
`13ea2fba67f36883518db8a2add1b249c951e48e`; `bundle_sha256` = the hash above
(compare case-insensitively; certutil prints spaces/uppercase on some versions);
`execution_authority` = `false`; `changed_paths_since_offline_source` lists only
Task 6 files. Write the hash in your run ledger. Any mismatch: stop.

On Kaggle: **Datasets → New Dataset**, title `pa3-reviewed-prep-source`,
visibility **Private**, upload exactly these two files (no folder):
`pa3_prep_source.bundle` and `pa3_prep_source_release.json`. Do not upload the
clone, `data/` or caches. Do not touch the existing `pa3-reviewed-source`.

### Step 2 — Runtime Prep notebook on Kaggle (CPU, Internet ON)

1. **Create → New Notebook**, then **File → Import Notebook** and upload
   `notebooks/pa3_inputs_prep_kaggle.ipynb` **from your checkout of `P`**
   (not from BASE/main: the BASE notebook still contains the failing flow).
2. Session options: Accelerator **None**, Internet **On**.
3. **Add Input → Your Datasets → `pa3-reviewed-prep-source`**. Attach nothing
   else (no InspecSafe, no model, no `pa3-reviewed-source`).
4. Find the bundle path in the right-hand **Input** panel (copy file path). Kaggle
   may show `/kaggle/input/datasets/<owner>/pa3-reviewed-prep-source/pa3_prep_source.bundle`
   or `/kaggle/input/pa3-reviewed-prep-source/pa3_prep_source.bundle`. Use the
   path Kaggle actually shows, **without** the leading `/kaggle/input/`.
5. Fill only the SETTINGS cell:

   ```python
   KIND = "runtime"
   PREP_SOURCE_COMMIT = "P"  # full reviewed SHA
   PREP_SOURCE_BUNDLE_INPUT = "datasets/<owner>/pa3-reviewed-prep-source/pa3_prep_source.bundle"
   PREP_SOURCE_BUNDLE_SHA256 = "<hash from Step 1, lowercase>"
   OFFLINE_SOURCE_COMMIT = "13ea2fba67f36883518db8a2add1b249c951e48e"  # leave as is
   ```

6. **Run All once.** Expect several minutes for downloads and archive
   compression (the real Linux run below took about 17 minutes).

The last cell prints `STATUS`, the four `CHECKS` (all must be `PASS`),
`INVENTORY_SHA256`, the folder to download from, and one line per file:
`<sha256> <bytes> <name>`.

### Step 3 — download, verify, and upload the runtime input

Folder (inside `/kaggle/working`):
`data/processed/pa3-prep-runtime/data/processed/pa3-runtime-prep/`.
Download exactly these **seven files** from the notebook's Output panel, plus
the notebook log (**File → Download** / the version log):

```text
runtime-archive/pa3_runtime.tar.gz
pa3_runtime_inventory.json
runtime_prep.json
resolved-requirements.txt
constraints.txt
commands.json
prep_source_input.json
```

On Windows, hash `pa3_runtime.tar.gz` and `pa3_runtime_inventory.json` with
`Get-FileHash`/`certutil` and compare with the notebook's printed lines and with
`runtime_prep.json` (`archive_sha256`, `inventory_sha256`). Also check in
`runtime_prep.json`: `status`, all four `checks`, `software` equals the ten
pins, `offline_source_commit` = `13ea2fb…`, `prep_source_commit` = `P`,
`prep_tracked_dirty` = `false`. Record `inventory_sha256` in the run ledger
separately from the Dataset.

Create a **new private Dataset** `pa3-runtime-input` (if that name already
exists, use a new name such as `pa3-runtime-input-t6`; never overwrite earlier
evidence) and upload all seven files **flat** (the archive at the Dataset's top
level, next to the inventory). Do not upload `build`, `relocated`,
`install-temp`, `archive-roundtrip`, `excluded-console-scripts` or anything
under `data/processed/ls1/`.

Model Prep, if still needed, is the same notebook in another fresh CPU
notebook with `KIND = "model"` and the same prep-source Dataset; it downloads
`pa3_model.tar.gz`, `model_prep.json`, `prep_source_input.json`. Model
revision, file list and checks are unchanged by this task.

### If anything fails

Do not re-run in the same session (the notebook refuses a reused folder by
design), do not edit pins/code, do not add `--break-system-packages`, do not
attach other sources. Download `commands.json`, whatever receipts exist and the
full notebook log; note the last printed stage and error in the run ledger; report
it for review. Intermediate directories are kept on failure as evidence. A
failed, skipped or partial run is not PASS.

### Later: OFFLINE technical run (not part of Task 6)

Only when separately authorised: import `notebooks/pa3_qwen2_5_kaggle.ipynb`
from **`13ea2fb`** (unchanged by Task 6), GPU T4, Internet **Off**. Attach the
existing `pa3-reviewed-source`, the model input and the new runtime input —
**not** `pa3-reviewed-prep-source`. In SETTINGS, `source_commit` stays
`13ea2fba67f36883518db8a2add1b249c951e48e` with the original
`pa3_source.bundle` hash; set `runtime_input` to the archive path,
`runtime_inventory_input` to `pa3_runtime_inventory.json` and
`runtime_inventory_sha256` to the ledger value (paths without `/kaggle/input/`,
as Kaggle shows them, e.g. `datasets/<owner>/pa3-runtime-input/pa3_runtime.tar.gz`);
leave `runtime_site_packages` empty. All Task 5 prerequisites (model input,
ledger, one run, four images, no retry, approvals) still apply.

## Validation evidence

### CPU tests (Windows, host Python 3.11.9)

```text
python -m unittest tests.test_pa3_runtime_prep -v
```

**29 run: 26 PASS, 3 SKIP, 0 failures/errors.** Skips: the two opt-in real
Linux tests and the Windows-only symlink limitation.

```text
python -m unittest tests.test_pa3_runtime_prep tests.test_pa3_feasibility tests.test_pa3_native tests.test_pa3_boundaries tests.test_pa3_synthetic tests.test_ls1
```

**203 run: 197 PASS, 6 SKIP, 0 failures/errors** (216 s, final code `3a40b46`).
Skips: the three above, two pre-existing real-tokenizer tests and one
pre-existing Windows skip.

Linux CPU (WSL, host Python 3.14.4, disposable venv), same commit:

```text
python -m unittest tests.test_pa3_runtime_prep tests.test_pa3_feasibility.PrepTests
```

**36 run: 34 PASS, 2 SKIP** (only the opt-in real tests), symlink cases
included. Against the previous candidate `prep.py` (`071b7e3`) the mocked
sequence test fails with `RUNTIME_ROUNDTRIP_CHANGED`, i.e. it reproduces
the real attempt-1 defect below.

Full discovery (`python -m unittest discover -s tests -t .`): see
"Full-suite comparison with BASE" below.

What the new tests cover:

- real child interpreter + synthetic packages: modules from an old/host path
  (`MODULE_OUTSIDE_RUNTIME`), metadata from outside (`METADATA_OUTSIDE_RUNTIME`),
  missing library, wrong version, host interpreter (`INTERPRETER_OUTSIDE_RUNTIME`),
  plus a positive control;
- mocked `runtime()` sequence: old trees deleted before each restore, consumer
  probe runs from `data/processed/ls1/runtime`, inventory accepted by
  `verify_runtime_input`, no PASS receipt on failure, evidence kept, refusal if
  the consumer path already exists, no absolute paths in `commands.json`;
- inventory placement (BASE defect), tampered archive, wrong trusted inventory
  hash, roundtrip link/version change, selection outside root;
- dangling/escaping symlinks (skipped on Windows, run on Linux);
- prep source: wrong descent, protected-path change, dirty tree, distinct
  bundle name, no authority, CLI order;
- prep notebook: missing receipt, wrong prep commit, wrong OFFLINE commit,
  wrong checksum, wrong schema/authority, OFFLINE bundle name, absolute and
  `..` paths, `datasets/<owner>/<dataset>` path accepted — all before any clone.

### Full-suite comparison with BASE (Windows)

`python -m unittest discover -s tests -t .` on a clean BASE `13ea2fb` worktree
and on Task 6 `3a40b46`, same machine and session:

| Source | Run | Failures | Errors | Skipped | Failing IDs |
| --- | --- | --- | --- | --- | --- |
| BASE `13ea2fb` | 1934 | 36 | 13 | 5 | 49 |
| Task 6 `3a40b46` | 1963 | 35 | 13 | 8 | 48 |

No failing ID exists only in Task 6. All 48 also fail on BASE — **historical
failures**, not touched here: grounding relock G5/G6 (30), multicategory runtime/
interface (6), D9 roster/participation/scope/freeze checks, classification
qualification, the
**D9R23 scope-allowlist** test `test_exact_scope_history_and_append_only`,
PaliGemma/Qwen/Ovis frozen-result checks, P2.1 authority, and an import failure of
`tests.test_moondream_precision`. The one BASE-only failure is a D9R27 topology
test that depends on whether HEAD is a merge commit.

### Real Linux evidence

Host: Ubuntu on WSL 2, Linux x86_64, ext4 Linux filesystem (`/var/tmp`, not a
Windows mount), 7 GiB RAM, Internet. Prep host: Python 3.14.4 in a disposable
venv (Kaggle's host is 3.13 — not identical). Runtime: real uv 0.6.14 and
real downloaded CPython **3.11.11**. No mocks. Clean detached checkout of the
Task 6 commit; prep module SHA-256
`66c581d3df7d6e277d9d2ba7fa4645d639d34118aea7f9133f77b13d10164bdb`.

```text
python3 -m venv data/processed/pa3-prep-host
SAFESHIFT_PA3_LINUX_PREP=1 data/processed/pa3-prep-host/bin/python -m unittest tests.test_pa3_runtime_prep.RealLinuxRuntimeTests -v
```

**Final run on `3a40b46`: 2/2 PASS, EXIT=0** (1115.7 s; 16:29–16:48 +07:00):

- the original `python -m ensurepip` on the managed interpreter fails with
  `externally-managed-environment` / "This Python installation is managed by
  uv and should not be modified"; the EXTERNALLY-MANAGED marker is unchanged;
- fixed install: 43 packages resolved and installed (~2 min download), all ten
  pins, `No broken requirements found.`;
- `runtime_prep.json`: status `CPU_RELOCATION_ARCHIVE_ROUNDTRIP_IMPORT_PASS_GPU_NOT_RUN`,
  checks 1–4 PASS, `prep_tracked_dirty: false`, no `.pth` files,
  `relocated/`, `build/`, `archive-roundtrip/` and `data/processed/ls1/runtime`
  absent afterwards;
- archive 3,150,381,108 bytes (~9 min gzip), 23,493 members, 5,723,318,036
  expanded bytes, 1,048 contained relative symlinks (mostly terminfo and
  `bin/python*` aliases), 0 hard links, 0 absolute/`..` names, no console
  scripts; archive SHA-256 `24b8b47cac6318feb9964be220d7c617b4256ca1460b435bd251c9c7d9d85bd2`,
  inventory SHA-256 `6c7e17633fbd6cd7d3c2127cb44a6d33db8f031c5f6ec357058f7b1102d1c49f`
  (WSL test artifacts only — **not** for Kaggle use; the owner builds and
  audits their own on Kaggle);
- second test, in a fresh process after prep exited: launcher
  `verify_runtime_input` with the trusted inventory hash, unchanged
  `runtime_interpreter(archive)` restore, all probes, identical link map and
  versions, then `import safeshift.pa3.native.workflow` with the launcher's
  PYTHONPATH and `-s`: PASS.

Earlier real attempts, retained as failures (none repaired by changing pins or
bypassing PEP 668):

- Codex, Windows-mounted checkout: out of space in WSL's 3.9 GiB `/tmp`, then a
  rename PermissionError on the Windows mount.
- Codex, `/var/tmp/safeshift-pa3-task6` (prep SHA-256 `66db2c2a…`): install,
  relocation probe, 3.0 GB archive, strict restore and probe all ran, then
  `WRITE_RUNTIME_INVENTORY_OUTSIDE_PREP_INPUT` (the BASE defect above). Log:
  `data/processed/linux-runtime.log` in that checkout.
- Attempt 1 of this session, `071b7e3`: stages 1–3 PASS and the consumer probe
  itself passed from `data/processed/ls1/runtime/part-0/runtime`, then the run
  failed closed with `RUNTIME_ROUNDTRIP_CHANGED` because the link map was keyed
  relative to `data/processed/ls1/runtime` instead of the restored runtime
  directory. Fixed in `3a40b46`. Evidence kept under
  `data/processed/attempt1-071b7e3/` of `/var/tmp/safeshift-pa3-task6-claude`.

All Linux artifacts stay in ignored `data/processed/` on the WSL filesystem;
nothing is committed. WSL did not disconnect during these runs.

## Remaining gates

1. ChatGPT GitHub review, then the separately requested Antigravity audit of `P`.
2. Owner Kaggle CPU Runtime Prep with the reviewed `P` (Steps 1–3). Kaggle
   evidence does not exist yet.
3. Model Prep / technical run requirements from Task 5 are unchanged and still
   pending; no Qwen, T1, GPU or TEST result is claimed.
