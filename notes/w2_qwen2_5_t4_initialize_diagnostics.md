# D9R2B-INIT-DIAG — Initialize diagnostics and init-only probe

Current status: **D9R2B-T4-QUAL resource PASS / PASS_VALIDATED**. See the final
section below; earlier attempt and pending statements are historical milestones.

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

## D9R2B-INIT-FIX — PyTorch version metadata normalization

This update supersedes the earlier unidentified-cause / unexecuted-probe status.
Research Lead-supplied evidence (bundle not independently verified in this task):

```text
REAL_INIT_PROBE: EXECUTED
RUN_ID: kaggle-t4-qwen25-init-20260925T063601Z-962127
BUNDLE_SHA256: 738489f5e41a729826029ffdf5579a9f9ff55af65e17b6dfc8a9c2027846f05a
STATUS: RUNTIME_INTERFACE_FAILURE
STAGE: INITIALIZE
ERROR_TYPE: Qwen2_5InitializeDiagnosticFailure
OBSERVED_SUBSTAGE: SOFTWARE_VERSION_VALIDATE
UNDERLYING_ERROR_TYPE: ValueError
MODEL_LOAD_REACHED: false
NATIVE_GENERATE_CALLS: 0
CALLS: []
OOM: NOT_OBSERVED
ROOT_CAUSE: IDENTIFIED
ROOT_CAUSE_STATUS: IDENTIFIED
ROOT_CAUSE_CODE: PYTORCH_VERSION_METADATA_NOT_NORMALIZED_TO_BUILTIN_STR
FIX: str(torch.__version__)
REAL_INIT_PROBE_AFTER_FIX: NOT_RUN
T4_STATUS: T4_FEASIBILITY_CANDIDATE / NOT_YET_VALIDATED
```

ROOT_CAUSE_DETAIL: PyTorch 2.6.0 exposes `torch.__version__` as `TorchVersion`,
a `str` subclass. `_native_backend` stored it without normalization, so the strict
`type(version) is str` requirement rejected it. The sole production change converts
this metadata to builtin `str` at collection. Strict validation remains unchanged,
including rejection of non-string values and unnormalized subclasses injected by
a backend. No model-fit or performance conclusion follows from this failure.

The fake-import regression
`test_native_torch_version_subclass_normalized_and_initialize_succeeds` reproduces
the initialization failure before the fix and passes after it, confirming the
exact builtin type and unchanged version value without loading a model. The
companion strictness test rejects non-string metadata and an unnormalized subclass.
Offline validation: **73 runner**, **58 PREP**, **15 load-diagnostic**, **20
initialize/probe**, and **749 full-suite tests PASS**. Runner/probe/smoke
`py_compile`, plan JSON validation and `git diff --check` PASS.
No real torch import, GPU, init probe, model/weight download, provisioning, inference,
synthetic gate, InspecSafe or protocol freeze was performed for this patch.

Model/revision, loader arguments, diagnostics, resource policy and software pins
remain unchanged. Plan JSON is untouched; canonical SHA before/after:
`aa4fcff85d670d844025a540d85f10514919c60f6709de8be8f6be0922fd63fb`.

## D9R2B-T4-QUAL — Successful real single-T4 runtime qualification

Research Lead-supplied real-run findings are transcribed in the
[machine-readable result](../configs/pre_freeze/qwen2_5_t4_smoke_result.v1.json).
The recording agent did not receive, inspect or rehash the bundle and performed
no new GPU run, download, provisioning or inference. The bundle/raw outputs remain
outside Git. The supplied identity is:

| Field | Value |
|---|---|
| Run ID | `kaggle-t4-qwen25-smoke-after-initfix-20260925T073925Z-bb567e` |
| Bundle SHA-256 | `0b04a616a71aa0b063711f2b403c536b7d096f9c758c31c9ac21709e9583c105` |
| Execution commit | `3124b1f7c2bd8d2311d1a1db6474950e200a689f` |
| Plan SHA-256 | `aa4fcff85d670d844025a540d85f10514919c60f6709de8be8f6be0922fd63fb` |
| Runtime status | `RUNTIME_INTERFACE_PASS` |
| Model load / native generation | PASS / PASS; exactly 2 calls, no native errors |
| OOM | `NOT_OBSERVED` |

The prior root cause was
`PYTORCH_VERSION_METADATA_NOT_NORMALIZED_TO_BUILTIN_STR`, fixed by
`str(torch.__version__)`. **REAL_INIT_REPROBE: INITIALIZE_INTERFACE_PASS** is
reported by the Research Lead; no separate reprobe ID/hash was supplied here.
The full smoke now records progress through initialize, load and native generation.
Its execution commit above is separate from this evidence-recording commit.

Exactly one visible Tesla T4 (compute capability 7.5, VRAM 15,636,037,632 bytes)
ran FP16 / SDPA / NONE / batch 1. All parameters and buffers were on cuda:0,
parameter dtype FP16, device map `{"": "cuda:0"}`, with
`Qwen2_5_VLSdpaAttention` and `Qwen2_5_VLVisionSdpaAttention`. The unchanged
processor caps were 200704/1003520 pixels. Both cases observed grid `[[1,32,32]]`,
merge size 2, 256 visual tokens and 256 image placeholders, within 256–1280.

The result records verified snapshot total 7,520,918,095 bytes and both exact
shard hashes. Before load, allocated/reserved memory was zero. After load:
allocated 7,509,421,568; peak allocated 8,131,575,808; reserved and peak reserved
8,212,447,232 bytes. Each case peak allocated was 7,638,978,560 bytes.
These are observations for this smoke, not guarantees for other inputs.

Both raw outputs contained `{"safety_level": "Level01"}` inside Markdown JSON
code fences. The unchanged strict parser returned **INVALID** /
**INVALID_CLASSIFICATION_OUTPUT** for each. The existing RUNTIME_INTERFACE_ONLY
harness permits this observation alongside SUCCESS; it is not a runtime failure
or a classification accuracy result. Raw output remains primary evidence: no
fence stripping, JSON repair, parser relaxation or output-driven prompt changes.

The active roster now uses **PASS_VALIDATED**, reusing the existing Qwen3 runtime
and historical Ovis runtime term in `local_models.d9.json`. It means only
**single-T4 load + generation feasibility**, not classification/grounding capability,
synthetic gate success or InspecSafe performance. The documentary provenance file
retains its historical pre-runtime observations, including false download/verification
flags; this run's local-byte verification is scoped separately in the linked result.
The immutable PREP plan similarly records its original pre-execution state.

**RESOURCE_QUALIFICATION: PASS. SYNTHETIC_CAPABILITY_GATE: PENDING.
INSPECSAFE: NOT_RUN. protocol_freeze_commit_sha: PENDING.** Classification remains
CANDIDATE; grounding remains DOCUMENTED_BOX_AND_POINT / NOT_YET_QUALIFIED.
Checklist #2 overall and #3–#8 remain PENDING. The next separate task after merge
is exactly **8 external handcrafted synthetic capability cases**; none executed
or newly authorized by this evidence/status recording task. Runtime code, parser,
adapter, prompt, pins, resource policy and plan JSON are unchanged.

Offline recording-task validation: runner **73**, PREP **58**, load diagnostics
**15**, initialize diagnostics **20**, roster/evidence **33**, full suite **750**
tests PASS (one new bounded-evidence regression). Plan, roster and result JSON
validation plus `git diff --check` PASS. Plan SHA before/after matches the value
above; census remains untracked/untouched with its expected hash.
