# D9R2B-INIT-DIAG — Initialize diagnostics and init-only probe

Base: `e3b2571f941ffa91167e9d65cf5df7eb56609822`.
Branch: `validation/d9-qwen2_5-initialize-diagnostics`.
Diagnostic-only: no runtime repair or real execution in this patch.

## Second real attempt (Research Lead-supplied facts)

```text
SECOND_REAL_T4_ATTEMPT: EXECUTED
RUN_ID: kaggle-t4-qwen25-diag-20260925T053007Z-bd011d
BUNDLE_SHA256: 9d4d3cefff6606a7d52f73da83fb7a4b26848929152225df6b666aaf7d10a200
STATUS: RUNTIME_INTERFACE_FAILURE
STAGE: INITIALIZE
ERROR: ValueError
CALLS: []
NATIVE_GENERATE_CALLS: 0
MODEL_LOAD_REACHED: NO
OOM: NOT_OBSERVED
ROOT_CAUSE: NOT_YET_IDENTIFIED
T4_STATUS: T4_FEASIBILITY_CANDIDATE / NOT_YET_VALIDATED
```

These facts and hash are recorded as supplied; this task does not import, modify,
commit or independently hash the real bundle. They do not identify the specific
initialize check that raised. No cause, model-fit or performance conclusion is made.

## Minimal diagnostic contract

`Qwen2_5InitializeDiagnosticFailure` contains only `diagnostic_stage` and
`underlying_error_type`, with empty args. It is raised `from exc` so the existing
in-memory cause-chain traversal still recognizes CUDA OOM. The harness and probe
persist only explicit stage/type fields, never original messages, repr, args,
tracebacks, paths or cause contents. Load diagnostics from PR #33 remain unchanged.

| Initialize substage | Existing operation |
|---|---|
| CONDITION_VALIDATE | `_check_condition(context)`, then existing idempotent return |
| BACKEND_CONSTRUCT | `_backend_factory()` |
| SOFTWARE_METADATA_COPY | `deepcopy(backend.software_versions)` |
| SOFTWARE_REQUIRED_KEYS_VALIDATE | Required software keys check |
| SOFTWARE_VERSION_VALIDATE | Existing per-version type/value comparison |
| BACKEND_PUBLISH | Existing Qwen2_5Backend construction and backend/condition assignments |

No conversion, altered comparison, fallback, retry or changed publication order
is introduced. `_key`, `_check_condition`, `_native_backend`, load/validation and
resource policy remain unchanged. Failure summaries use `stage=INITIALIZE`,
`error_type=Qwen2_5InitializeDiagnosticFailure`, `initialize_substage`, and
`underlying_error_type`; they do not use `load_substage`. True CUDA OOM remains
RUNTIME_RESOURCE_FAILURE; ordinary contract errors remain RUNTIME_INTERFACE_FAILURE.

## Future init-only probe — NOT_RUN

`scripts/w2_qwen2_5_t4_init_probe.py` checks the canonical plan, an explicitly
supplied exact 40-character Git commit, clean tracked files, Linux x86_64, exact
software pins, one visible T4 with compute capability 7.5, CUDA build 12.4 and the
same offline environment flags as smoke. It reuses the smoke hardware/software
checks and socket-denial firewall. Untracked census/cache artifacts are permitted.

It creates the smoke's initial RunContext fields (case_01, decoding, preprocessing,
precision, quantization, device, software metadata and source kind). Run ID and
command identify the probe invocation; the execution condition is identical.
Then it calls `runner.initialize(context)` and stops. It never calls load,
from_pretrained, prepare, generate, snapshot resolution/verification/provisioning
or inference. Native library imports are still part of backend construction.

For a separately authorized future probe, in the already prepared pinned Linux
environment, select one T4 and set the offline flags before starting Python:

```sh
export CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_ENABLE_HF_TRANSFER=0
python scripts/w2_qwen2_5_t4_init_probe.py --run-id init-probe-01 --expected-commit <reviewed-40-character-commit>
```

`--expected-commit` must be the reviewed implementation/merge commit containing
this probe, not the pre-patch base, a branch name or a mutable ref. No model cache
or weights are required. A success is INITIALIZE_INTERFACE_PASS only, never T4
runtime qualification. A failure records the sanitized initialize substage.

Exclusive evidence under
`data/processed/runtime_validation/w2_qwen2_5_t4_init_probe/<run_id>/` contains only
run_metadata.json, environment.json, summary.json and summary.json.sha256.
Summary hashes the preceding artifacts. There are no case directories, raw/model
outputs, result.json or snapshot manifest. Existing run IDs cannot be overwritten.

Model `Qwen/Qwen2.5-VL-3B-Instruct`, revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`, FP16, SDPA, NONE quantization,
single cuda:0, caps 200704/1003520 and all software pins are unchanged. Plan JSON
is untouched; canonical SHA before/after:
`aa4fcff85d670d844025a540d85f10514919c60f6709de8be8f6be0922fd63fb`.

REAL_INIT_PROBE_STATUS: **NOT_RUN**. No weights download, snapshot provisioning,
GPU, real inference, synthetic gate or InspecSafe execution in this task. No
protocol freeze; root cause remains unidentified; T4 remains a feasibility
candidate. Earlier real-attempt records are retained as historical evidence.

Offline validation: **71 runner**, **58 PREP**, **15 load-diagnostic**, **20
initialize/probe**, and **747 full-suite tests PASS**. All three requested
`py_compile` checks, plan JSON validation and `git diff --check` PASS. Tests deny
network/native ML imports and assert no load/from_pretrained/prepare/generate or
snapshot activity, safe evidence, cause-chain OOM classification and intact smoke
success behavior. Existing assertions now require the wrapper plus original cause.
The source allowlist adds only the newly authorized probe; historical hashes remain.
AST comparison against exact base confirms initialize operations are identical
after removing diagnostic labels/wrapper, with all protected runner functions
unchanged. Census remains untracked/untouched with its expected SHA-256.
