# W2.6-D9R2B-DIAG — Safe Qwen2.5 load diagnostics

Base: `323288943e2cdcc606f11d7eed32604796b82571`.
Branch: `validation/d9-qwen2_5-t4-load-diagnostics`.
Scope: diagnostic patch only; no runtime fix or new real execution.

## Historical real attempt: supplied evidence facts

The Research Lead supplied the following facts in the DIAG task brief. This patch
records them without importing, modifying or committing the real bundle. Its hash
is recorded as supplied, not independently recomputed from bundle bytes here.

| Field | Reported fact |
|---|---|
| Run ID | `kaggle-t4-qwen25-20260925T004019Z-21794d` |
| Bundle SHA-256 | `41cade7b0b3d600c28bddf485055043e1f46b7f6d312e8556bcbe8d7b23ecb82` |
| Status | `RUNTIME_INTERFACE_FAILURE` |
| Failure stage | `LOAD` |
| Error type | `ValueError` |
| Native generate calls | `0` |
| Calls | `[]` |
| Before-load allocated / reserved | `0 / 0` bytes |
| Before-load peak allocated / reserved | `0 / 0` bytes |
| OOM | **NOT_OBSERVED** |
| GPU | Tesla T4; one visible GPU; compute capability 7.5 |
| Total VRAM | `15636037632` bytes |
| Torch CUDA | `12.4` |
| Snapshot | Exact revision verified |
| Offline variables | Valid |

Valid reported environment:

| Software | Version |
|---|---|
| Python | 3.11.11 |
| torch | 2.6.0+cu124 |
| torchvision | 0.21.0+cu124 |
| transformers | 4.51.3 |
| qwen-vl-utils | 0.0.8 |
| accelerate | 1.6.0 |
| Pillow | 11.2.1 |
| huggingface-hub | 0.30.2 |
| tokenizers | 0.21.1 |
| safetensors | 0.5.3 |

The supported scientific statement is **REAL T4 ATTEMPT EXECUTED;
RUNTIME_INTERFACE_FAILURE AT LOAD; NO OOM OBSERVED**. These facts do not identify
the failing operation or establish model quality, VRAM fit or T4 qualification.
The previous LOAD label also covered initialization and post-load checks, so its
ValueError cannot be attributed to a particular validation from that label alone.

## Diagnostic contract

`Qwen2_5LoadDiagnosticFailure` carries exactly two application fields:
`diagnostic_stage` and `underlying_error_type`. Its args are empty. The runner raises
it `from exc`, preserving the original in-memory cause for the existing `is_oom`
traversal. The cause is never serialized. No original message, repr, exception
args, traceback, private path, allocator text, HTTP/auth text or model output is
copied into the wrapper's diagnostic fields or evidence.

The existing load operations keep their order, arguments and validations:

| Substage | Existing operation labeled |
|---|---|
| PROCESSOR_LOAD | AutoProcessor.from_pretrained |
| PROCESSOR_VALIDATE | Existing processor validation |
| MODEL_LOAD | Native model.from_pretrained |
| MODEL_EVAL | model.eval |
| MODEL_VALIDATE | Existing model validation |
| GENERATION_CONFIG_VALIDATE | Existing generation config validation |
| GENERATION_CONFIG_SNAPSHOT | deepcopy of generation config |
| CALL_STATE_CLEAR | Existing rope/native-cache clearing |
| RESOURCE_PUBLISH | Final `_resources` tuple assignment |

Precondition checks and the already-loaded idempotent return remain outside the
new wrapper. No retry, fallback or corrective action is added. Processor/model
resources remain unpublished until the final assignment. Ordinary attribute
assignment has no additional fallible hook; a fake-only test injects failure
before assignment to exercise RESOURCE_PUBLISH without adding a production hook.
Existing explicit retry and idempotent-success semantics remain intact.

Harness initialization now uses stage INITIALIZE; stage LOAD begins immediately
before `runner.load`. A diagnostic load failure produces:

```json
{
  "stage": "LOAD",
  "error_type": "Qwen2_5LoadDiagnosticFailure",
  "load_substage": "MODEL_VALIDATE",
  "underlying_error_type": "ValueError"
}
```

This is a schema example, not attribution of the historical failure. An initialize
failure has stage INITIALIZE and the original error type, without load_substage.
Other failure paths retain the existing stage/error-type summary. No extra
diagnostic event stream is introduced.

Wrapped CUDA OutOfMemoryError remains `RUNTIME_RESOURCE_FAILURE`, including at
MODEL_LOAD, MODEL_VALIDATE or any other load substage. Wrapped contract errors
remain `RUNTIME_INTERFACE_FAILURE`. Evidence contains only allowlisted stage/type
fields; it never stringifies the original exception or its cause. Direct callers
must also avoid logging the cause chain: normal Python traceback rendering could
expose original messages, so the harness catches and serializes only these fields.

On initialization/load failure, calls remain `[]`, native generates remain zero,
and no case directory, response.raw, result.json or visual-token observation is
fabricated. Successful smoke retains two preparations/two native generates,
raw-before-parser, placement, visual-token observations, classification handling,
memory observation, state clearing and evidence layout. Runner/raw versions remain
v2; the Git commit identifies this diagnostic instrumentation.

## Possible failure locations — hypotheses only

Every item below is **HYPOTHESIS_ONLY / NOT_CONFIRMED_BY_RUNTIME_EVIDENCE**:

- Initialization's execution-condition or software-metadata checks could have
  raised under the old combined LOAD label.
- Processor construction or its min/max attribute validation could have raised.
- Native model construction/eval or existing model checks (attention flag,
  device/dtype, quantization, device map, parameter/buffer placement, native state
  layout or cache configuration) could have raised.
- Generation config validation/snapshot or call-state clearing could have raised.
- Post-load placement/attention-class checks also ran while the historical stage
  label was LOAD. The current facts do not distinguish them from runner load.

No item is ranked as a diagnosis and none is addressed with a behavior change in
this PR. The next separately authorized real rerun should retain the same plan
and record INITIALIZE versus LOAD plus a safe load_substage if runner.load fails.
That new evidence, not these hypotheses, should guide any later repair task.

## Immutable boundaries and current status

Model `Qwen/Qwen2.5-VL-3B-Instruct`, revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`, SDPA, FP16/NONE, batch 1, single
NVIDIA T4 16GB, min/max pixels 200704/1003520 and visual tokens 256–1280 are
unchanged. No CPU/disk offload, automatic fallback or substitution is introduced.
Loader args and every validation body are unchanged; software pins above remain
unchanged. No transitive lock, roster/provenance, D5/P1 or synthetic asset change.

Plan JSON is untouched. Canonical PLAN_SHA256 before and after:
`aa4fcff85d670d844025a540d85f10514919c60f6709de8be8f6be0922fd63fb`.

- Offline runner: **COMPLETE**.
- Runtime prep: **COMPLETE / PREPARED**.
- Observability: **COMPLETE / OFFLINE_TESTED**.
- First real T4 attempt: **EXECUTED**.
- First real result: **RUNTIME_INTERFACE_FAILURE_AT_LOAD**.
- OOM: **NOT_OBSERVED** in the reported real attempt.
- T4 qualification: **NOT_YET_VALIDATED**; roster status **T4_FEASIBILITY_CANDIDATE**.
- Diagnostic patch: **IMPLEMENTED / OFFLINE_TESTED**.
- Next real T4 rerun: **PENDING / NOT_RUN**.
- Protocol freeze SHA: **PENDING**; InspecSafe authorization remains false.

No model/weight download, snapshot provisioning, GPU, Kaggle/Colab runtime, real
inference, synthetic gate, InspecSafe inference, performance scoring, prompt tuning,
grounding qualification, protocol freeze or backup activation occurred in DIAG.
Earlier PREP/OBS NOT_RUN milestones remain historical; the status above records
the subsequently reported first real attempt without rewriting its evidence.

## Offline validation

- `python -m unittest tests.test_qwen2_5_runner -v`: **71 PASS**.
- `python -m unittest tests.test_qwen2_5_t4_runtime_prep -v`: **58 PASS**.
- `python -m unittest tests.test_qwen2_5_t4_load_diagnostics -v`: **15 PASS**,
  including per-stage fault injection and wrapped fake CUDA OOM at all nine stages.
- `python -m unittest discover -s tests`: **727 PASS**.
- `py_compile` for runner and smoke harness, plan `json.tool` validation and
  `git diff --check`: **PASS**.

Tests use injected fakes with ML-import and network guards. Secret-like exception
arguments and exceptions whose str/repr raise are covered; no raw output is
fabricated for pre-call failures. Existing PREP assertions changed only to expect
the diagnostic wrapper while additionally checking the original ValueError cause
and exact substage. Historical runner tests remain unchanged.

AST comparison against exact base confirms identical native backend, execution
condition, initialize, processor/model/generation validators, state clearing,
preparation and generation bodies, and identical from_pretrained calls/arguments.
Canonical plan SHA matches before/after. Census is untracked and untouched with
SHA-256 `cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`;
it is excluded from staging/commit. The existing test venv is separate from the
unchanged Linux runtime candidate pins.
