# W2.6-D9R2H-MOONDREAM-LOAD-DIAGNOSTIC-PREP

Status: **PREPARED_NOT_RUN**. Root cause **NOT_UNIQUELY_IDENTIFIED**.
Base main: `e52d9bd05a50c54b13675ed73ff0230efed3d841` (fetched 2026-09-26).

## Evidence and static analysis

The Research Lead supplied the previous run ID
`kaggle-t4-moondream-smoke-20260926T070217Z-4c2d43` and findings:
FAIL_T4_RUNTIME_INTERFACE / FAIL, stage load, ValueError, cause_type null,
zero query/detect calls, empty state_audits/image_boundaries, zero peak CUDA memory;
model/tokenizer snapshot verification, GPU condition and dependencies PASS.
These are supplied observations; the original Kaggle artifact bundle was not
independently inspected here. Its execution SHA was not supplied. This analysis
uses the current base code, not a claim of byte identity with that execution.
The original FAIL is retained; this diagnostic is not a retry or qualification.

Sources read before implementation: [smoke](../scripts/w2_moondream_t4_smoke.py),
[runner](../safeshift/runners/moondream2.py),
[binding](../safeshift/runners/moondream_binding.py),
[snapshot verifier](../safeshift/runners/moondream_snapshot.py),
[frozen plan](../configs/pre_freeze/moondream_t4_runtime.v1.json), and direct
Moondream runner/smoke, audit and precision tests.

| Location in current code | Explicit ValueError candidates / interpretation |
| --- | --- |
| `load_plan`, `_condition` (initialize and load) | FROZEN_RUNTIME_PLAN_CHANGED, PROTECTED_BRIDGE_PLAN_CHANGED, PINNED_PLAN_OR_BRIDGE_MISMATCH, RUNNER_INVALID_OR_IDENTITY_MISMATCH, EXACT_RUNTIME_CONDITION_REQUIRED_NO_FALLBACK, EXACT_SOFTWARE_REQUIRED, RUNTIME_CONDITION_CHANGED. Initialize PASS and unchanged context make these less plausible at load, but load rechecks them. JSON decoding/serialization can also raise ValueError subclasses. |
| `NativeBackend.__init__`, `initialize`, `validate_device` | PINNED_LINUX_X86_64_ENVIRONMENT_REQUIRED, INSTALLED_SOFTWARE_MISMATCH, EXACTLY_ONE_NVIDIA_T4_16GB_CC75_REQUIRED. In the current harness these precede stage load; supplied initialization evidence excludes them as the reported load failure. |
| `artifact_rows`, `verify_snapshot`, `verified_source` | IMMUTABLE_IDENTITY_REQUIRED, PROTECTED_SOURCE_AUDIT_CHANGED, EXACT_HF_SNAPSHOT_REQUIRED, MISSING_OR_UNREVIEWED_SNAPSHOT_FILE, SNAPSHOT_FILE_ESCAPES_CACHE_REPOSITORY, PINNED_ARTIFACT_MISMATCH, REMOTE_SOURCE_HASH_MISMATCH. Initial PASS does not prove all subsequent repeated checks passed; checks recur inside the verified loader and Starmie redirect. |
| `require_pillow` | PILLOW_ONLY_REQUIRED, CROP_BACKEND_IDENTITY_MISMATCH. Both occur before model construction and are compatible with zero CUDA allocation. |
| `verify_function` / Starmie redirect | AUDITED_FUNCTION_IDENTITY_REQUIRED, AUDITED_BYTECODE_REQUIRED, ORIGINAL_TOKENIZER_IDENTITY_REQUIRED, UNEXPECTED_TOKENIZER_REQUEST, STARMIE_LOAD_NOT_OBSERVED; backend also checks ACTUAL_STARMIE_INSTANCE_MISMATCH. Multiple distinct pre-transfer failures remain possible. |
| Native/dependency calls inside `NativeBackend.load` | Verified source imports, HfConfig.from_pretrained, HfMoondream.from_pretrained, tokenizer.from_file, model.to/eval and _setup_caches are propagation boundaries. Without the original traceback, a ValueError from source or installed dependencies cannot be assigned to one of them. No particular Transformers/config error is asserted as fact, and no downloaded source is executed for this analysis. |
| `VisionBinding.__init__` / `check` | Function/source checks above plus INSTANCE_BINDING_IDENTITY_MISMATCH and Pillow checks. These follow transfer/cache setup and precede the runner state audit; zero CUDA peak makes them less consistent with the report, but memory alone is not proof of a unique earlier failure. |
| `_audit_state` / `audit_model_state` | MODEL_STATE_DEVICE_OR_DTYPE_MISMATCH, EMPTY_MODEL_STATE_AUDIT, UNREGISTERED_RUNTIME_STATE_MISMATCH, OFFLOAD_HOOK_FORBIDDEN, QUANTIZATION_FORBIDDEN, KV_CACHE_DTYPE_OR_DEVICE_MISMATCH. The runner appends a FAILED audit record before calling audit_model_state, so empty state_audits excludes these for the reported failure under current code. |

`cause_type=null` only means no explicit `__cause__` was recorded; it does not
exclude an implicit `__context__`. The smoke stores no message or traceback.
Empty image boundaries and zero native calls exclude inference/bridge-consumption
checks, but cannot distinguish the remaining load candidates. There is therefore
no justified unique diagnosis and no justified runtime fix.

## Separate diagnostic contract

[Harness](../scripts/w2_moondream_load_diagnostic.py) constructs the existing
Moondream2Runner and calls initialize once, then load once if initialization
succeeds. No Request, input image, input preparation, generation, query, detect,
bridge invocation, gate or dataset access is introduced. Runner code, precision
bridge, model source, plan, revisions, prompts, decoding, PILLOW_ONLY, FP16/NONE,
batch 1 and single cuda:0 condition remain unchanged.

Reports are created exclusively at
`data/processed/moondream_load_diagnostic/<diagnostic-run-id>/report.json`.
IDs cannot contain paths; existing diagnostic directories are rejected before
runtime entry. The fixed output namespace has no official smoke ledger access.
The script neither imports the smoke harness nor reads/writes ATTEMPT.json or its
result. Existing aliases/junctions are rejected by the existing FileRawStore path
checks. Artifacts remain ignored and local.

After reserving writable output, success and caught failures (including interrupt)
write a report: stage, exception type/message, cause/context type/message, complete
formatted traceback with filenames/line numbers and no locals, runner evidence,
exact git SHA, context/command, actual installed distribution versions, expected
software pins, model/tokenizer pins, plan hash, UTC times and GPU metadata already
observed by runner.initialize. GPU is null with NOT_REACHED if initialization fails
before that observation. No extra CUDA probing/reset is added. Known environment
secret values and common token/auth/URL credential forms are redacted throughout
the report; local diagnostic paths remain. Redaction is best effort, not a claim
that arbitrary unlabeled secrets can be recognized.

Git provenance and installed distribution metadata are gathered before initialize.
The runner still installs its irreversible offline/network denial before backend
creation/model load; all existing local-only loads and snapshot checks remain.
No fallback or Hugging Face download is added. For this separate diagnostic the
Research Lead explicitly does not require Kaggle venue Internet OFF, so no venue
flag is required. The frozen official smoke network policy is untouched. The
existing Python audit hook is not an OS firewall for arbitrary native code.

LOAD_ONLY_PASS is solely a completed diagnostic load, not official smoke PASS,
resource qualification, full runtime/precision validation or capability success.
The script exits 0 for that outcome and 1 for a captured failure. Argument/path
rejection, unwritable storage and uncatchable process termination cannot guarantee
a report; those fail before runtime or leave a reserved partial artifact. There
is no retry loop and the runner's one-load-per-process guard is unchanged.

## D9R2I Kaggle execution preparation — two diagnostic-only amendments

Task: **W2.6-D9R2I-MOONDREAM-DIAGNOSTIC-KAGGLE-EXECUTION-PREP**.
Authority: Research Lead's task instruction, 2026-09-26, after PR #44 merged.
Base main: `65b8836e11cdc399d26543f17a15412d0da2e3f4`.
Branch: `prep/d9-moondream-diagnostic-kaggle-execution`.
Status: **PREPARED_NOT_RUN**; real load diagnostic **NOT_RUN**;
`protocol_freeze_commit_sha: PENDING`.

The Research Lead reports that the old Kaggle session was shut down and its local
`data/processed/moondream_hf` cache no longer exists. This is supplied context,
not a cache inspection or execution result from this PREP. Only the following two
pre-freeze amendments are authorized, solely for the separate load-only diagnostic.
They supersede the earlier diagnostic instruction to reuse the old cache without
downloading. They do not amend the historical official smoke procedure or assert
that the old smoke ran with these conditions in a frozen repository. The old
**FAIL_T4_RUNTIME_INTERFACE / FAIL** and its run ID above remain unchanged.

### A. EPHEMERAL CACHE REPROVISION

When a new Kaggle session has lost the old cache, recreate only
`data/processed/moondream_hf` using the existing
[`scripts/provision_moondream_snapshot.py`](../scripts/provision_moondream_snapshot.py)
with `--provision`, in a separate process before the diagnostic. Its immutable
allowlist remains authoritative:

| Repository | Exact revision |
| --- | --- |
| `vikhyatk/moondream2` | `9a7d4024050840e001defacec2b00727e89149e6` |
| `moondream/starmie-v1` | `35192e10a54e36eabe0a7cc57a2c1aab371cafc5` |

Do not change revisions, add snapshot files, use an alternative downloader/cache,
or repair a failed verification. If the cache exists, reuse it with verify-only;
do not delete it to trigger reprovision. A partial/invalid cache is a STOP condition.
After provisioning, run `--verify-only` in a fresh process. Both complete manifests
must match, including every filename, size, SHA-256, immutable identity,
`local_bytes_verified: true` and `manifest_sha256`. The existing provisioner emits
deterministic JSON, so byte comparison checks the complete provision/verify pair.
Both operations independently enforce the unchanged audited hashes/allowlist.
No old local manifest is claimed to have survived the terminated session.

The diagnostic continues to reverify the same snapshots and enforce local-only
loading plus permanent Python network/child-process denial. No download during
initialize/load, fallback, retry loop or new inference path is authorized. The
diagnostic-only venue Internet policy from PR #44 remains unchanged; Internet may
be enabled for the separate provisioning process. This does not relax the official
smoke's venue-network-disabled requirement.

### B. SINGLE-T4 PROCESS VISIBILITY

The Kaggle host may expose more than one Tesla T4 (for example T4x2). Launch the
diagnostic as a new OS process with **`CUDA_VISIBLE_DEVICES=0` set by the shell
before Python starts**. Setting it inside an already running notebook/Python
kernel, using `%run`, or changing visibility after CUDA initialization is not this
procedure. In Kaggle, run the Bash block below in one `%%bash` cell from the repo
root, using the pinned Python environment; do not split its shell state across cells.

The existing runner must observe exactly one CUDA GPU at logical `cuda:0`:
Tesla T4 (the existing validator also accepts its `NVIDIA T4` name), compute
capability `[7, 5]`, and total VRAM **15,032,385,536–17,179,869,184 bytes inclusive
(14–16 GiB)**. All other host GPUs must be inaccessible as CUDA devices to this
diagnostic process. Evidence is the startup mask plus the same process's
`report.json.gpu.gpu_count == 1` and the remaining validated GPU fields, not host
`nvidia-smi` count alone. No second CUDA ordinal is visible/usable under this
condition. This is CUDA process visibility isolation, not an OS security sandbox
or multi-GPU execution; host inventory may still enumerate physical devices.
Do not switch to GPU 1 or launch another worker if GPU 0 fails.

FP16, quantization NONE, batch size 1, cuda:0 placement, no CPU/disk offload,
no fallback, PILLOW_ONLY, software pins and the precision bridge are unchanged.
No runner, model, diagnostic harness, provisioner, runtime config or helper code
is modified: existing GPU validation/reporting already provides the required
process-visible inventory. Host inventory and the launch transcript are separate
evidence, recorded before the runner denies subprocess creation.

### Future Kaggle procedure — NOT executed in this PR

Use the clean tracked checkout at the exact reviewed execution commit and the
unchanged pinned Linux x86_64 / Python 3.11.11 environment. This PREP does not
authorize execution now. For a later authorized diagnostic, replace the two
placeholder values below. Preserve all artifacts before ending the Kaggle session.
All paths are relative to the repository root; never reuse an evidence/run ID.

```bash
set -euo pipefail
expected_commit='REPLACE_WITH_REVIEWED_40_CHARACTER_SHA'
run_id='REPLACE_WITH_UNIQUE_DIAGNOSTIC_RUN_ID'
[[ "$expected_commit" =~ ^[0-9a-f]{40}$ ]]
[[ "$run_id" != REPLACE_* && "$run_id" =~ ^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$ ]]
test "$(git rev-parse HEAD)" = "$expected_commit"
git diff --quiet HEAD
cache='data/processed/moondream_hf'
evidence="data/processed/moondream_load_diagnostic_execution/$run_id"
report="data/processed/moondream_load_diagnostic/$run_id/report.json"
test ! -e "data/processed/moondream_load_diagnostic/$run_id"
mkdir -p data/processed/moondream_load_diagnostic_execution
mkdir "$evidence"
date -u +%Y-%m-%dT%H:%M:%SZ > "$evidence/started_utc.txt"
git rev-parse HEAD > "$evidence/execution_commit.txt"
nvidia-smi --query-gpu=index,uuid,pci.bus_id,name,memory.total,driver_version --format=csv > "$evidence/host_gpu_inventory.csv" 2> "$evidence/host_gpu_inventory.stderr"

if [[ ! -e "$cache" && ! -L "$cache" ]]; then
  printf '%s\n' EPHEMERAL_CACHE_ABSENT_REPROVISION > "$evidence/cache_policy.txt"
  python scripts/provision_moondream_snapshot.py --provision --cache-dir "$cache" --manifest "$evidence/provision.json" > "$evidence/provision.log" 2>&1
else
  printf '%s\n' EXISTING_CACHE_VERIFY_ONLY > "$evidence/cache_policy.txt"
fi
python scripts/provision_moondream_snapshot.py --verify-only --cache-dir "$cache" --manifest "$evidence/verify.json" > "$evidence/verify.log" 2>&1
if [[ -f "$evidence/provision.json" ]]; then
  cmp "$evidence/provision.json" "$evidence/verify.json"
fi
printf '%s\n' VERIFIED_BEFORE_DIAGNOSTIC > "$evidence/verification_status.txt"

# Shell transcript records the exact mask and command before Python startup.
# The harness alone creates its separate report directory, exclusively.
if (
  set -x
  export CUDA_VISIBLE_DEVICES=0
  python scripts/w2_moondream_load_diagnostic.py --execute-load-diagnostic --expected-commit "$expected_commit" --cache-dir "$cache" --run-id "$run_id"
) > "$evidence/diagnostic_launch.log" 2>&1; then
  diagnostic_exit=0
else
  diagnostic_exit=$?
fi
printf '%s\n' "$diagnostic_exit" > "$evidence/diagnostic_exit_code.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$evidence/finished_utc.txt"
sha256sum "$evidence"/* > "$evidence.sha256"
if [[ -f "$report" ]]; then
  sha256sum "$report" > "$evidence.report.sha256"
fi
exit "$diagnostic_exit"
```

Stop on inventory, provisioning, verification or comparison failure; retain partial
logs and report the blocker. Do not continue to load or silently reprovision again.
The shell preserves the diagnostic exit code even on a captured load failure.
On interruption/missing report, retain the partial evidence and STOP; no automatic
retry. Shell success alone is not evidence that all audit conditions were met.

Review the future evidence bundle as follows:

- Link host inventory, launch transcript/mask, provision/verify manifests and logs,
  timestamps, exit code and checksums by the same run ID and exact execution SHA.
  Keep them under `data/processed/`, outside Git; retain the corresponding notebook
  cell/command as launch provenance without secrets.
- `report.json.gpu` and `runner_evidence.gpu` are the process-visible inventory
  observed by `runner.initialize`. Require count 1, T4, CC 7.5 and the byte range
  above. Null/NOT_REACHED is missing evidence, never assumed PASS. Unexpected
  count/name/capability/memory fails existing validation before model load.
- Compare `runner_evidence.model_manifest` and `tokenizer_manifest` to the matching
  entries in `verify.json.snapshots`, including manifest hashes and all file hashes.
  Missing evidence is NOT_VERIFIED; any mismatch is STOP, never a hash update.
- Preserve the full diagnostic exception/traceback on failure. Query/detect counts
  must remain zero and image boundaries empty. LOAD_ONLY_PASS, if later observed,
  proves only diagnostic load completion; it cannot qualify full FP16 runtime,
  change the old smoke FAIL, authorize smoke/gate, or promote model participation.

Do not delete/recreate the old smoke ledger or launch an official smoke in a new
session. Loss of its local ledger/cache does not erase the historical failed
attempt or create retry permission. No claim about the old smoke's startup mask,
physical host GPU count or frozen conditions is added.

### D9R2I PREP validation

Validation: **52/52 existing unit tests PASS**, using fake backends/device metadata
and synthetic bytes only:

```powershell
.venv/Scripts/python.exe -m unittest tests.test_moondream_load_diagnostic tests.test_moondream_runner_smoke -v
git diff --check
```

The Bash block above was extracted and passed to `bash -n` via stdin: **PASS**
(syntax only; no command in that block executed). Git Bash initially could not
create a signal pipe inside the Windows sandbox; the same syntax-only check
passed outside it. `git diff --check` **PASS**. The diff contains only this note
and `TASKS.md`; runtime/config/protected files are unchanged from the base SHA.
No new tests or helper were needed for this documentation-only amendment.
The full suite was not rerun; the direct tests cover the existing manifest,
GPU validation, load-only and official-ledger isolation contracts. The historical
D9R2H full-suite result below is not claimed as a new D9R2I run.

Real reprovision/download, GPU inventory, model execution,
diagnostic, official smoke, query/detect, gate and InspecSafe remain **NOT_RUN in
this PR**. No merge is part of this task.

## D9R2H validation (historical PR #44 evidence)

Tests use the real runner with a fake backend/model, synthetic exceptions and
mocked snapshot/network boundaries; they neither execute downloaded code nor
access a GPU. Existing bridge tests use CPU tensors. Commands and final results
are recorded below. No real diagnostic/model load, model download,
official smoke rerun, query, detect, gate or InspecSafe execution is part of PREP.

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_moondream*.py'
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe -m py_compile scripts/w2_moondream_load_diagnostic.py tests/test_moondream_load_diagnostic.py
git diff --check
```

Final results: **82/82 Moondream tests PASS** (13 new diagnostic tests),
**945/945 full-suite tests PASS**, compile and diff checks PASS. The initial full
suite found only the historical source allowlist missing the newly authorized
script; that test now adds exactly this path, retaining protected hashes and all
other restrictions. No assertion was removed. Tests cover real-runner lifecycle
with fake backend, unchanged context/pins, offline setup before backend load,
forbidden inference entrypoints, success and initialize/load failures, messages
and line-level traceback, explicit/implicit chains, credential redaction, CLI
exit/report behavior, old-ledger isolation, path traversal and no overwrite.

Environment: Windows, Python 3.11.9, torch 2.6.0+cpu. PyTorch emitted a missing
NumPy warning; all tests passed without dependency installation. Real pinned
Linux/T4/model validation remains intentionally NOT_RUN. Direct diff against base
confirmed no changes to runner modules, official smoke, frozen configs or pinned
runtime requirements. The pre-existing untracked census file is untouched and
excluded from this change.
