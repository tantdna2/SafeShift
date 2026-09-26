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

## Future invocation (not executed in this PREP)

Use a fresh dedicated process in the existing pinned Linux/T4 environment with
previously provisioned local snapshots, clean tracked checkout at the reviewed
commit, and repository-relative cache under data/processed. No download command
is part of this diagnostic. From the repository root:

```sh
python scripts/w2_moondream_load_diagnostic.py --execute-load-diagnostic --expected-commit <exact-reviewed-40-character-sha> --cache-dir data/processed/moondream_cache --run-id moondream-load-diagnostic-<unique-id>
```

Preserve the separate report for review; do not remove the old official ledger,
alter its FAIL or proceed into any inference/gate as a consequence of this report.

## Validation

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
