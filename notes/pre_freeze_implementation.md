# Pre-freeze implementation

## W2.6B2B — audited Ovis real GPU runtime result

Research Lead directly audited the evidence bundle for
`ckey-a40-ovis-20260924T042034999220552Z` and concluded **RUNTIME_SMOKE_PASS /
VALIDATED**, scope `RUNTIME_INTERFACE_ONLY`. The [result note](w2_ovis_gpu_smoke_result.md)
and [machine-readable summary](../configs/pre_freeze/ovis_gpu_smoke_result.v1.json)
record the supplied audit findings; the recording agent did not independently
inspect the ZIP, reverify the model host or rerun inference.

`B2B_PREP_HEAD` / `EXECUTION_COMMIT` remain immutable at
`c2a5d97945b27d16425f82592a352722ee935118`, the code that actually ran. PR #26's
separate `RESULT_RECORDING_COMMIT` identifies the later summary/docs/tests commit
and must not replace that execution pin. Evidence ZIP SHA-256:
`f6b4756d3e57a213e6302f3170de10c46d334865aed5735ea906647ede46ce76`.

One NVIDIA A40 (47,708,110,848 bytes VRAM, CC 8.6, BF16 supported) passed the
capability-based single-GPU gate. The run used BF16 / NONE / `cuda:0`, explicit
thinking false/false and greedy 32-token decoding. One load and two sequential
classification calls succeeded, with raw-before-parse preserved, zero network
violations/native errors, BF16-only parameters on `cuda:0`, and no OOM. All four
weight shards and five critical source files passed run-scoped local verification;
other required assets remain `RECORDED_LOCAL_HASH_ONLY`. Documentary provenance
is unchanged.

Torch distribution was 2.4.0, runtime version 2.4.0+cu121 and torch CUDA runtime
12.1; host build toolkit 12.4 is separate. Python 3.11.16 instantiates SafeShift's
Python 3.11 candidate. flash-attn 2.7.0.post2 was installed, but both observed
attention config fields reported `eager` with no runner override. This is a
nonblocking observation, not evidence of actual FlashAttention execution.
Identical raw outputs on distinct geometry inputs carry no accuracy/capability
conclusion. Stable call-1/call-2 allocator values are diagnostic only.

Checklist #1 remains documentary COMPLETE; #2 remains PENDING overall. Qwen and
Ovis offline work is COMPLETE and real runtime smoke PASS / VALIDATED; Molmo,
Gemma and #3–#8 remain PENDING. Ovis grounding stays
`DOCUMENTED_BOX_AND_POINT / NOT_YET_QUALIFIED`; all research claims remain false
and `protocol_freeze_commit_sha` remains PENDING. No rerun, GPU, download,
SYNTHETIC V1 gate, InspecSafe inference or merge occurs in this recording task.
Only summary/hashes, notes, status docs and offline tests are committed; runtime
artifacts remain outside Git and the census remains untracked and untouched.

Recording validation: **16/16 result tests**, **39/39 smoke-harness tests**,
**32/32 Ovis-runner tests**, **500/500 full-suite tests PASS**;
`git diff --check` PASS. The existing local `.venv` was used without dependency
changes. Result tests also match the supplied config hash against Git blob bytes
at the immutable execution commit; no external evidence was rehashed.

## W2.6B2B-PREP — Ovis single-GPU BF16 runtime harness (2026-09-24)

Historical PREP milestone below: its NOT_RUN status describes preparation only;
the audited runtime result above is the current status. Execution pin
`c2a5d97945b27d16425f82592a352722ee935118` is retained after result recording.

Base main: `609964fe04024d51a6f329ec78f1e578dfeb227c` (PR #25 merge).
Branch: `validation/d9-ovis-gpu-smoke`. This milestone prepares the
[single-GPU BF16 runbook](w2_ovis_gpu_smoke_runbook.md), immutable smoke plan, exact
snapshot provisioner, local-byte verification and offline evidence harness. It does
not execute the model. **Ovis runtime status is PREPARED / NOT_RUN**, and actual
runtime validation remains PENDING.

The plan preserves requested identity `AIDC-AI/Ovis2.5-9B`, resolved download
repository `ATH-MaaS/Ovis2.5-9B` and immutable revision
`d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd`. It fixes a smoke-only BF16 / NONE /
explicit `cuda:0` condition, official `preprocess_inputs` bounds, thinking disabled
explicitly and greedy `max_new_tokens=32` before any output exists. These are
technical PREP candidates, not research precision, thinking or decoding freeze.
Python 3.11 is a SafeShift-selected smoke environment candidate, not an Ovis
provider-documented requirement. The Ovis documentary package recipe pins torch 2.4.0,
Transformers 4.51.3, NumPy 1.25.0, Pillow 10.3.0, MoviePy 1.0.3 and flash-attn
2.7.0.post2; the future report records the resolver-selected huggingface_hub version.
No attention override is added to the existing runner.

The hardware requirement is `NVIDIA_SINGLE_GPU_BF16_MIN_40GB`: one visible NVIDIA
CUDA GPU with at least 40,000,000,000 bytes of VRAM, logical device `cuda:0`,
compute capability at least 8.0 and BF16 support. GPU names are evidence only;
there is no A100 name gate or GPU whitelist. A qualifying MIG logical device may
pass; undersized partitions fail the VRAM gate. Kaggle T4 x2 is not used: the
checkpoint weight bytes are approximately 18.35 GB while each T4 is approximately
16 GB, and the Ovis runner has explicit single-device placement with
no supported multi-GPU sharding; two T4s cannot pool VRAM into one device.
Preflight, package, snapshot, weight, critical-file,
placement and dtype failures all stop before generation or before later calls as
applicable; no FP16, quantized, CPU-offload, automatic-map or multi-GPU rescue exists.

Provisioning is the only online phase and uses the resolved repository plus exact
revision in the native Hugging Face cache layout. A separate `--verify-only` pass is
local-only and verifies all four weight shard sizes/hashes, the five critical files
with documentary hashes, and existence plus locally recorded hashes for required
assets that have no provenance hash. Such assets are explicitly
`RECORDED_LOCAL_HASH_ONLY`, not falsely verified against provenance. The later smoke
requires `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` and
`HF_HUB_DISABLE_TELEMETRY=1`, denies socket `connect`, `connect_ex`, `sendto`,
`create_connection` and `getaddrinfo` through the same counting firewall, and fails
on any network violation. Regression attempts originate inside `run_smoke` from the
fake model and prove that production denial, not the outer test guards, blocks them.

The harness also requires exported `B2B_PREP_HEAD` to contain exactly 40 lowercase
hexadecimal characters and equal actual `git rev-parse HEAD`. Missing, invalid or
mismatched pins fail before software/GPU preflight, snapshot verification or runner
creation. The report keeps `git_commit`, `execution_pin` and
`execution_identity_verified` separately. Before real execution, PR #26 published
the reviewed execution pin after each code fix. Following the audited run, that
historical pin is immutable and result-recording commits do not update it.

One `Ovis2_5Runner` instance serves exactly two sequential
`Task.CLASSIFICATION` cases, `RUNTIME_SMOKE_01` and `RUNTIME_SMOKE_02`, generated as
deterministic local geometry. They are not SYNTHETIC V1 inputs, are not InspecSafe
inputs and do not execute grounding. A PASS candidate requires one underlying model
load lifecycle, two native generate calls, two preserved raw/metadata pairs, no
native exception or blocker, and final adapter statuses only `SUCCESS` or
`INVALID`, with the latter paired only to `INVALID_CLASSIFICATION_OUTPUT`. Parser
failure and every other error block. The
harness records actual parameter/buffer placement, an exact floating-parameter dtype
census, four GPU-memory stages, software/driver evidence and raw-before-parse
metadata. Any non-BF16 floating parameter is a blocking review deviation; it is not
silently cast.

The future run creates an allowlisted `ovis_gpu_smoke_evidence.zip` and SHA-256 with
small reports, case manifest and the two raw/metadata pairs only. Weights, snapshot,
HF cache, secrets, generated images and arbitrary logs are excluded. Failures are
preserved without automatic rerun; a reviewed rerun requires a new run ID plus
explicit `rerun_of` and `rerun_reason`. Even a future `RUNTIME_SMOKE_PASS` keeps
capability, grounding, accuracy, benchmark and all precision/decoding/thinking/
protocol-freeze claims false.

Offline validation for this PREP uses fake runtime/CUDA objects only. Commands:
`python -m unittest tests.test_ovis_gpu_smoke_harness -v`,
`python -m unittest tests.test_ovis_runner -v`,
`python -m unittest discover -s tests`, and `git diff --check`.
Validation after PR #26 review fixes, from the existing `.venv` (Python 3.11.9 /
Pillow 12.3.0): **39/39 smoke-harness tests PASS**, **32/32 Ovis-runner tests PASS**,
and **484/484 full-suite
tests PASS**; `git diff --check` PASS. No dependency was installed or changed.
The tests use fake runtime/CUDA objects, block network entry points, and use no real
model, GPU or weights. Python compilation checks for the provisioner, harness and
new test module also pass.

Checklist #1 remains documentary COMPLETE. Checklist #2 remains PENDING overall:
Qwen offline is COMPLETE and its real Kaggle smoke is PASS / VALIDATED; Ovis offline
is COMPLETE and runtime is PREPARED / NOT_RUN; Molmo and Gemma remain PENDING. Ovis
grounding remains `DOCUMENTED_BOX_AND_POINT / NOT_YET_QUALIFIED`. Checklist #3–#8
and `protocol_freeze_commit_sha` remain PENDING. The D9 roster, D5, canonical schema,
Qwen evidence and SYNTHETIC V1 assets are unchanged. The census remains untracked and
untouched (SHA-256
`cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`).
CENSUS_UNTRACKED_UNTOUCHED. NO_MODEL_DOWNLOAD. NO_REAL_INFERENCE.
SYNTHETIC_GATE_NOT_RUN. NO_INSPECSAFE_INFERENCE.

## W2.6B2A — Ovis2.5-9B offline runner (2026-09-23)

The [Ovis implementation note](w2_ovis_runner_implementation.md) records the
pinned custom-code path, separate requested/resolved repository identities,
BF16 single-device candidate, native generated-ID semantics, raw/failure envelopes,
classification adapter, and unqualified grounding evidence. Fake-backend tests
cover the lifecycle and post-generation preservation; no real model runtime or
external gate is claimed. Checklist #1 remains documentary COMPLETE; #2 stays
PENDING overall (Qwen offline implementation COMPLETE and real Kaggle smoke PASS /
VALIDATED; Ovis offline runner implementation COMPLETE after Research Lead review,
real runtime PENDING; Molmo/Gemma PENDING). Ovis grounding is
`DOCUMENTED_BOX_AND_POINT / NOT_YET_QUALIFIED`. #3–#8 and
`protocol_freeze_commit_sha` remain PENDING. D5, canonical
schema, D9 roster, Qwen records and SYNTHETIC V1 assets are unchanged.

## W2.6B1B — real Kaggle smoke recorded (2026-09-23)

**Qwen real runtime smoke PASS / VALIDATED**, per Research Lead's direct audit
reported by the Project Owner. The [result note](w2_qwen_kaggle_smoke_result.md)
and [summary JSON](../configs/pre_freeze/qwen_kaggle_smoke_result.v1.json) record
run `kaggle-t4x2-20260923T012029667885Z` at execution commit
`784c465cae5188ed6ede5673140a4a281f2ffb52`. Bundle SHA-256:
`ae3e9e1002ce94bf78bb0ac856f1a7f54a48283d64db51cdb8d5eed37f6b8a69`.
The recording agent transcribes the supplied audit; no independent bundle inspection
or new model execution is claimed. The separate RESULT_RECORDING_COMMIT is in PR #24;
B1B_PREP_HEAD stays pinned to the exact code executed, not the new PR head.

All four local weight shards matched hash and size for this run. Two T4s used
both GPUs without CPU/disk offload; FP16 / NONE / auto with observed sdpa.
One runner lifecycle completed two classification calls with SUCCESS, preserved
raw/metadata and cleared cache state, without OOM/native exception. Identical
raw outputs for distinct images are runtime observations only, not accuracy or
semantic capability evidence. Recorded memory peaks were unchanged between calls.

Checklist #1 COMPLETE documentary; #2 PENDING overall (Qwen offline implementation
COMPLETE and Kaggle smoke VALIDATED; Ovis/Molmo/Gemma runners/runtime PENDING).
#3–#8 and `protocol_freeze_commit_sha` remain PENDING. FP16 is a validated smoke
candidate, not frozen research precision. Grounding stays NOT_YET_QUALIFIED /
UNCERTAIN_REQUIRES_EXTERNAL_GATE. No gate, InspecSafe, new downloads, rerun, tuning,
backup activation, final roles, D5/schema changes, protocol freeze or merge.
No ZIP/raw/runtime metadata/weights/cache are committed.

Recording checks: 413/413 full-suite tests PASS, including 10 summary tests;
`git diff --check` PASS. Existing local `.venv` used without dependency changes.

The PREP entry below retains the historical 2026-09-22 state and test counts;
its pending-execution statements are superseded by this audited result.

## W2.6B1B-PREP — Kaggle runtime harness (2026-09-22)

Base main: `bd18a64bc76653893abaf5d36a3d9d6dd2665073` (PR #23 / W2.6B1A).
Branch: `validation/d9-qwen-kaggle-smoke`.
The [runbook](w2_qwen_kaggle_smoke_runbook.md) provides ten copy-ready Kaggle
cells: exact PREP checkout, dependency candidate installation preserving Kaggle
torch/CUDA, pinned snapshot provisioning and local shard verification, offline
execution, report summary and a small allowlisted evidence bundle.

Prepared scripts separate online provisioning from offline smoke. The new
`qwen_kaggle_smoke.v1.json` is a **PRE_RUNTIME_VALIDATION_PLAN**, with FP16 / NONE /
auto / official processor / native attention, Transformers 4.57.1, and smoke-only
`do_sample=false, max_new_tokens=32`. One literal prompt serves exactly two
deterministic geometric images, distinct from all eight SYNTHETIC V1 hashes.
These settings are locked before output, not a protocol precision/decoding freeze.

The existing Qwen runner/executor/storage/adapter are unchanged. Diagnostic hooks
observe its actual model lifecycle, device map, native exception type and memory;
two independent sequential requests reuse one runner. Raw+metadata are preserved
before parsing. INVALID classification is a note, not a runtime failure. GPU/count,
weight mismatch, load/generation/OOM, storage and disk-offload failures stop;
CPU offload is a Research Lead review note. Every attempt uses an exclusive run ID;
reruns require prior ID and reason. No automatic retry, fallback or tuning.

Offline validation: **41/41 harness tests and 401/401 full-suite tests PASS**.
Commands from repository root, with existing `.venv/Scripts` first on PATH:
`python -m unittest tests.test_qwen_kaggle_smoke_harness -v`,
`python -m unittest discover -s tests`, `git diff --check` (PASS).
The first system-Python attempt could not import Pillow; no dependency was installed.
Tests use tiny fake shard bytes and the real runner with injected fake backends,
blocked network/real ML imports, and temporary repositories. No fake runtime report
or generated fixture/artifact is committed. Notebook Python cells are syntax-checked;
their pip installation, weights, CUDA and real inference are **not executed**.

**W2.6B1B Kaggle T4×2 runtime-validation harness prepared; real Kaggle execution
pending.** Checklist #1 COMPLETE documentary; #2–#8 PENDING;
`protocol_freeze_commit_sha=PENDING`. Protected D9 configs, SYNTHETIC V1, decisions,
D5 and canonical schema are unchanged. Census remains untracked and untouched
(SHA-256 `cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`).
NO_MODEL_WEIGHTS_DOWNLOADED. NO_REAL_MODEL_INFERENCE. SYNTHETIC_GATE_NOT_RUN.
NO_INSPECSAFE_INFERENCE. No grounding, final roles, backup activation or merge.

## D9 transition and active P2 checklist (2026-09-20)

[DEC-W2-D9-009](../DECISIONS.md#dec-w2-d9-009--p2-open-weight-self-hosted-model-roster)
supersedes **only D8's P2 commercial-hosted-provider roster/backend assumptions**.
The active P2 path is open-weight self-hosted/user-controlled GPU execution, using
the four candidates and ordered backups in the [D9 brief](w2_open_weight_self_hosted_model_roster_decision_brief.md).
Local workstations, Colab, Kaggle and rented GPU hosts are execution venues; a venue
change is equivalent only if all frozen model/runtime conditions remain equivalent
and recorded. No model capability, access, license clearance or run success is
established by adding a candidate to the roster.

The **active checklist** is [TASKS.md's D9 checklist](../TASKS.md#w2--active-d9-pre-freeze-checklist-2026-09-20),
with pending fields mirrored in [local_models.d9.json](../configs/pre_freeze/local_models.d9.json)
and [freeze_manifest.d9.template.json](../configs/pre_freeze/freeze_manifest.d9.template.json):

| # | Active D9 prerequisite | Current status |
|---|---|---|
| 1 | Exact IDs/revisions, access/license evidence and weight provenance for primaries/backups | COMPLETE: W2.6B0 documentary records for all six; not access/use clearance or protocol freeze |
| 2 | Local/self-hosted runners, preprocessing/device/precision/software and raw-output provenance | PENDING; W2.6A contracts and W2.6B1A Qwen code/offline tests implemented; real runtime validation and remaining model runners pending |
| 3 | One supported low-variance decoding policy per model | PENDING; hosted settings do not transfer automatically |
| 4 | Deterministic native-output adapters compatible with the existing canonical box schema | PENDING; point-only compatibility unresolved |
| 5 | Interface eligibility review for four primaries and unchanged SYNTHETIC V1 gate for qualifying box interfaces | PENDING; no model execution; qualitative giant-box review procedure still pending |
| 6 | Final classification/grounding roles and any permitted pre-freeze backup substitutions | PENDING; only evidenced classification blockers permit substitution; activated backups require the same prerequisites and applicable gate |
| 7 | Freeze exact prompts/task policy, schema, adapters/parsers, runners/environment and full D5 engine | PENDING |
| 8 | Approved protocol freeze commit | PENDING; `protocol_freeze_commit_sha: PENDING` |

The original D8 checklist and every D8/Qwen section below are preserved as historical
evidence. Their status statements describe those milestones. The current P2 overlay is:

| Historical provider requirement | Current P2 status |
|---|---|
| Qwen Singapore workspace endpoint | `SUPERSEDED_FOR_P2_BY_D9` |
| Qwen hosted decoding configuration | `SUPERSEDED_FOR_P2_BY_D9` |
| GPT/Claude hosted capability gates | `SUPERSEDED_FOR_P2_BY_D9` |
| Commercial provider billing/access setup | `SUPERSEDED_FOR_P2_BY_D9` |
| Provider live-route verification | `SUPERSEDED_FOR_P2_BY_D9` |

`providers.json`, the original `freeze_manifest.template.json`, hosted adapter
skeletons and `scripts/validate_qwen_config.py` retain their historical scope. Their
offline success is not D9 runner validation or permission to execute a model.
Provider requirements are superseded for P2 only; P1's upstream reproduction policy,
including `temperature = 0.1` and compatibility reporting, is unchanged.

D9 preserves Benchmark Firewall, Protocol Freeze, C1, A2, B2, the canonical schema,
raw-output preservation before parsing, capability-aware grounding, D5 metrics and
statistics, and post-freeze change control. Seminar remains frozen zero-shot
cross-domain robustness evaluation; no training or fine-tuning is introduced.
D1–D7, evaluation pools, domain policy and the RQ2 hierarchy erratum remain binding.

Consistency review found that the original D9 wording implied a native-point D5
track. D5 Pointing Hit actually uses a predicted box's center on original polygons;
the current schema and external gate require boxes. The D9 brief/templates now leave
Molmo's box compatibility unresolved. Preserve native points in raw outputs, never
fabricate boxes. A point-only model may participate in classification after validation
but remains `NOT PARTICIPATING` in current grounding unless a qualifying box interface
is verified. Adding a point-only schema/gate/metric track requires a separate approved
decision and is not part of D9. Nonparticipants receive no artificial zero score.

Backup clarification after the audit of `864b61f5e70296c3d1a1e9faeeb055fc571766b7`:
valid classification execution and parseable classification output require continued
classification participation, even after spatial-gate failure or native-point-only
incompatibility. Grounding role is `NOT_PARTICIPATING`; no backup substitution or
artificial zero IoU is allowed. Full-model substitution requires an objective,
pre-specified blocker preventing classification, with evidence recorded before freeze
and before any InspecSafe inference, following the D9 brief's replacement policy.
InspecSafe scores are forbidden as a selection basis. The same rule applies to
activated backups; a spatial-gate pass is required only for grounding participation.

Cleanup validation: **233/233 existing tests PASS** with
`.venv/Scripts/python.exe -m unittest discover -s tests`; D9 JSON parse/consistency,
SYNTHETIC V1 manifest/generator hashes and `git diff --check` (including the full
diff from base main) PASS. The four trailing-whitespace lines in the D9 brief were
cleaned. No model validation or inference was run; all freeze prerequisites remain pending.

The SYNTHETIC V1 manifest, provenance, generator and eight PNG assets remain unchanged.
Manifest SHA-256 remains
`fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379`;
generator SHA-256 remains
`c5fc2140d1bd2ce9ef323884834911c1e3ef4234172cd3d37c0e6ba4341f4f6c`.
Frozen assets do not imply a completed model gate or protocol freeze.

This task synchronizes documentation/configuration only. No runners, model weight
downloads, model/provider API calls, InspecSafe image inspection or inference.
**NO_INSPECSAFE_INFERENCE**. All eight execution prerequisites remain pending.

### D9 synchronization validation

Full existing suite: **233/233 tests PASS**, zero failures/errors, with
`.venv/Scripts/python.exe -m unittest discover -s tests`. Environment: existing
Python 3.11.9 / Pillow 12.3.0; no dependency changes. `git diff --check`: **PASS**.
Tests use synthetic fixtures and temporary outputs, not InspecSafe images.
Additional offline checks parsed both D9 JSON files and compared roster/backup order,
shared policies, pending freeze fields and gate metadata. SHA-256 verification matched
all eight synthetic images, the manifest and generator to the existing provenance.
Comparison with the parent revision confirmed that the D1–D8 ledger text and the
entire historical implementation text below remain unchanged.

The synchronization commit on `protocol/d9-local-open-weight-roster` identifies this
documentation revision; it is not a protocol freeze commit. No benchmark run or new
run artifact exists. Not run: model gates, runner validation, weight/access validation,
model/provider API calls, full D5 evaluation or InspecSafe inference, because this
task authorizes protocol/documentation synchronization only. Model facts in the D9
brief retain their prior documentary-review provenance; this check does not establish
live availability or finalize immutable revisions and license/access records.

## W2.6B1A — Qwen runner offline implementation (2026-09-22)

The [Qwen implementation note](w2_qwen_runner_implementation.md) records the exact
8B checkpoint runner, injected native factories, idempotent lifecycle, in-memory
image processing, deterministic raw envelope and classification adapter. All
63 contract tests and 360 full-suite tests pass using fake runtime objects.
No ML runtime, weights or GPU were used. This proves **implementation contract is
structurally correct**, not **Qwen runtime works on GPU**.

Qwen grounding remains `UNCERTAIN_REQUIRES_EXTERNAL_GATE`; the adapter reports
`UNSUPPORTED` / `NOT_YET_QUALIFIED` without interpreting boxes or points. Generation
kwargs are caller-supplied, with inherited configuration recorded; no decoding,
precision or quantization policy is selected. Blocking generation has
`BLOCKING_GENERATE_NO_PARTIAL_GUARANTEE`. W2.6A core, canonical schema, D5 and D9
configuration/provenance records are unchanged.

PR #23 review fix preserves observed native IDs and any completed decode in a
separate versioned failure envelope when post-generation validation, decoding or
serialization fails. W2.6A stores it through `GenerationFailure.partial_raw` with
parsing NOT_ATTEMPTED; the adapter is never invoked. An exception before any
serializable native observation still has `partial_raw=None`.

Checklist #1 remains COMPLETE documentary; #2–#8 remain PENDING. Real runtime
validation, remaining runners, interface qualification, external gate, final roles
and freeze are outstanding. No SYNTHETIC V1 model gate or InspecSafe inference ran.
`protocol_freeze_commit_sha: PENDING`.

## W2.6B0 — Model Provenance & Runner Specification (2026-09-22)

The [documentary audit and runner specification](w2_model_provenance_runner_spec.md)
records full immutable Hugging Face revisions and official source evidence for all
four D9 primary candidates and both ordered backups. The machine-readable record
is [local_model_provenance.d9.json](../configs/pre_freeze/local_model_provenance.d9.json);
the existing roster and freeze template now reference it and carry matching SHAs.
Published weight file names/sizes/LFS hashes are metadata only: no weight bytes
were downloaded or checked. D9 #1 is COMPLETE in this documentary scope; #2–#8
remain PENDING, including all `frozen_components` in the eventual freeze template.

Ovis's official repository redirect is recorded separately without changing its D9
ID. Molmo's Apache license and academic/non-commercial training-data caveat both
remain visible. PaliGemma remains gated under Gemma terms with owner acceptance
NOT_VERIFIED / ACCESS_REQUIRES_USER_ACCEPTANCE, not a model failure. Qwen's official
family cookbook uses a different checkpoint and has contradictory bbox-order
text/code; the exact 8B spatial grammar remains UNRESOLVED. No adapter choice or
model eligibility follows from these records.

The spec inventories official runtime, spatial and classification interfaces,
supported decoding controls, preprocessing and precision/quantization. All are
DOCUMENTED_NOT_RUNTIME_VALIDATED; no final decoding/precision setting is selected.
PR #21's idempotent initialize/load and partial-generation preservation notes are
mandatory W2.6B acceptance criteria. No real runners, prompts, D1–D9 decisions,
canonical schema, D5 definitions, final roles or backup ordering were changed.
Validation counts and exact commands are in the linked specification.
No model weights, GPU/model/provider inference, InspecSafe images or synthetic
model gate were used. Census remains untracked/untouched.
`protocol_freeze_commit_sha: PENDING`.

## W2.6A — Local Runner Contracts (2026-09-21)

The [W2.6A implementation note](w2_local_runner_contracts.md) records the generic
runner lifecycle, raw-before-parse storage, independent task/participation status,
native box/point/no-spatial/malformed distinction, error taxonomy and seven dummy
cases. This completes infrastructure contracts/scaffolding only. Active D9 checklist
#2 and all model-specific prerequisites remain **PENDING**; the unchanged D9 JSON
templates still correctly describe the pending execution/freeze prerequisites.
No real runner validation, model provenance completion, decoding freeze, adapter
qualification, synthetic gate, final roles or protocol freeze is claimed.
The earlier D9 synchronization and D8 records describe their historical milestones.

## Historical D8 implementation record

Historical bases (each names a different milestone):

- `D8_APPROVAL_BASE`: `ec40d9080f8c6847355ec22cc5bad54ea1dda876`.
- `PRE_FREEZE_INFRASTRUCTURE_MERGE`: `d6350cea7ff7dadc2bbd444f37ed8c81766b7195`.
- `SYNTHETIC_EXTERNAL_CASES_MERGE`: `9dcf157d5026d11755a4f1e3f9e075da8f5fe747`,
  the starting `main` for steps 1–2 on `implementation/qwen-route-decoding`.

Original infrastructure branch: `implementation/pre-freeze`. D8 is approved; **D8 approval != protocol freeze**.
`protocol_freeze_commit_sha: PENDING`.

Scope follows [D8](../DECISIONS.md#dec-w2-d8-008),
[D5](w2_metrics_statistics_decision_brief.md), and
[D6 vocabulary/support definitions](w2_grounding_census_decision_brief.md).
No dataset, split, label or D5 formula was changed. The original infrastructure task
used no web/provider calls. Steps 1–2 read public Alibaba documentation only; no model
API calls, model-output inspection, InspecSafe inference or prompt tuning occurred.
No API credentials are required for configuration validation.

## Approved eight-item checklist

These are the eight prerequisites in [D8 section 34](w2_model_prompt_interface_decision_brief.md#34-pre-freeze-implementation-checklist-danh-sách-kiểm-tra-triển-khai-trước-đóng-băng-giao-thức).
An implemented interface is not evidence that its freeze prerequisite is complete.

| # | Approved prerequisite | Status | Evidence / remaining work |
|---|---|---|---|
| 1 | Exact Qwen Singapore workspace endpoint | PENDING_USER_CONFIGURATION | Documented workspace route pinned; neither `QWEN_WORKSPACE_ENDPOINT` nor `QWEN_WORKSPACE_ID` is set in the local process environment. No actual WorkspaceId invented. |
| 2 | One supported Qwen decoding configuration | DONE | Frozen P2 policy `qwen-singapore-instruct-temperature-zero-v1`: `{"temperature": 0}` only; other sampling controls omitted. Documentation verified; no empirical comparison. |
| 3 | Prepare and freeze external Target+Distractor cases | DONE | **SYNTHETIC V1**: 8 tracked PNGs, 4 reciprocal swap groups, frozen manifest and SHA-256 provenance. Deterministic regeneration and existing validator passed; see evidence below. |
| 4 | Execute external capability gates for Level-3 models | PENDING | GPT gate **NOT RUN**; Claude gate **NOT RUN**. Dummy geometry tests are not provider capability evidence. |
| 5 | Assign final grounding eligibility and model roles | PENDING | Preserve D8 evidence assignments: Gemini/Qwen Level 1; GPT/Claude Level 3, grounding `NOT PARTICIPATING` pending a qualifying gate. |
| 6 | Verify exact model IDs and serving routes on live APIs | PENDING | IDs are copied from approved D8. Availability, wire formats and routes have not been checked live. |
| 7 | Freeze prompts, schema, adapters, parsers and metric engine | PENDING | Offline interfaces, schemas, adapter/parser tests **DONE**. Prompt drafts and metric contracts are versioned; final policies, live route integration and full D5 engine remain pending. |
| 8 | Record protocol freeze commit | PENDING | `protocol_freeze_commit_sha: PENDING`. Implementation commit is not a freeze commit. |

No item is marked BLOCKED: the remaining work is intentionally outside this offline task.

## Implemented contracts

- `safeshift/protocol/prompts.py`: Call 1 accepts image path + caller-supplied industry safety policy and requests only `safety_level`. Call 2 accepts image path + exactly the D6 closed 12-hazard vocabulary; its signature has no Call 1 output/history argument. Call 1 likewise has no Call 2 input. Exact industry policy text must still be pinned before freeze; no substitute safety policy was invented.
- `schemas/canonical.schema.json` and `schema.py`: canonical x-first `[xmin, ymin, xmax, ymax]`, normalized `[0,1]`, top-left origin. Python enforces strict coordinate inequalities in addition to JSON Schema. Extra task fields, unknown hazard IDs, duplicate JSON keys, non-finite values, string/bool coordinates and malformed JSON are rejected. Empty hazard/evidence arrays are retained as valid explicit outputs; missing evidence does not imply localization success.
- `adapters.py`: Gemini, Qwen DashScope, OpenAI and Anthropic offline skeletons. `prepare()` renders the provider coordinate convention; `extract_text()` supports explicitly selected handcrafted envelope contracts. Gemini y-first/1000 and Qwen x-first/1000 are reordered/scaled deterministically. OpenAI/Anthropic use canonical coordinates. There is no inference transport: every `send()` raises `OFFLINE_ONLY`. Qwen's compatible-chat route is now documentation verified; the adapter still has no live verification.
- `records.py`: `preserve_and_parse()` writes unchanged response bytes and metadata before extracting provider text or parsing. Metadata links run/sample/call IDs, image checksum, exact rendered prompt/hash, provider/model/version, endpoint, SDK, generation configuration, Git SHA and environment. Artifacts are local under `data/processed/`; existing call directories cannot be overwritten. Persistence failures abort parsing. This pre-freeze entrypoint accepts only `handcrafted_dummy` provenance.
- `metrics.py`: D5 interfaces for image-level classification, GT RQ2 atom lookups, complete Call 2 predictions, Direct/Weak Proxy candidate original polygons, explicit unsupported atoms and parse metadata. A missing membership raises an error; it is not treated as an empty/normal sample. Direct and Proxy support stay separate. Nonparticipants have no synthetic zero-score result. No metric formulas or tuned thresholds are implemented.
- `configs/pre_freeze/providers.json` and `freeze_manifest.template.json`: model/route policy and explicit pending freeze state. API key and endpoint environment variable **names** only; credentials are never loaded or embedded. Qwen decoding is documented compatible-chat configuration, still untested on a live workspace. `qwen_config.py` resolves the actual endpoint in memory from environment only.

Implementation follows approved D8 section 16 deterministic coordinate normalization:
provider-native reorder/scale, then clamp each coordinate to `[0,1]`, then strict
geometry validation (`xmin < xmax`, `ymin < ymax`). This applies to `xyxy_1`,
`xyxy_1000` and `yxyx_1000`. Clamping does not modify the stored raw response.
No sorting, coordinate-convention inference or semantic repair is performed;
reversed boxes and boxes that become degenerate after clamping remain invalid.
Mixed valid/invalid boxes yield `COORDINATE_ERROR`, with no successful canonical
response. Valid items survive only in `diagnostic_evidence`. `response_schema_valid`,
`boxes_attempted` (unknown = `null`) and `boxes_valid` support separate D5 response/box
parse diagnostics. End-to-end consumers must not promote diagnostics into success.

For future offline integration, build each request independently, call its adapter's
`prepare()` once, then pass that exact prepared request, unmodified dummy response
bytes and `CallMetadata` to `preserve_and_parse()`. Each attempt needs a new call ID.
The low-level `parse_text()` is a pure parser for already-persisted dummy strings;
future live ingestion must preserve the full raw response before calling it.

## External capability harness and firewall

`schemas/external_cases.schema.json` defines case ID, repository-relative image path,
target/distractor GT bboxes, target query, source provenance and swap group.
`tests/fixtures/pre_freeze/external_cases.example.json` is a small handcrafted format
example. It contains no embedded images or benchmark data. Format validation does
not assert that placeholder images exist, have verified licensing/checksums, or are
ready for a live gate; those checks belong to final case preparation.

`gate.py` validates separated target/distractor geometry, unique case IDs, fixed query
within each group and reciprocal target/distractor swaps on distinct image paths.
Every supplied case must pass: valid single-box schema, predicted center inside
target, exclusion of distractor center, movement following target positions, and no
giant/full-image behavior. Boundaries count as inside, including distractor exclusion.
Missing/malformed responses fail; unknown case IDs raise rather than being dropped.
IoU and predicted area are descriptive fields only, never pass/fail thresholds.

Full-image boxes are automatically rejected. Because D8 gives no numeric definition
of "near full-image / giant", a separate `GiantBoxReview` records `NO_GIANT`, `GIANT`
or `PENDING`, reviewer and rationale. Automated checks passing without that review
return `PENDING_REVIEW`, never PASS. This preserves the qualitative approved criterion
without inventing an area cutoff. The actual cases are now frozen as SYNTHETIC V1;
the qualitative review procedure still needs to be fixed before the live gate.
A harness result does not update model roles.

`firewall.py` guards every new development CLI input, embedded case image path,
request builder, adapter preparation and artifact path before reading/writing inputs.
It rejects raw-dataset paths, case/separator variants, absolute paths, parent traversal
and resolved symlink/junction aliases into raw data or outside the repository.
The protected repository root is application-supplied, not manifest-controlled.
This detects paths, not copied/relabelled benchmark content; external provenance
review remains required. Existing W1 audit commands are unchanged and are not
pre-freeze capability/development entrypoints.

## Frozen external cases: SYNTHETIC V1 (2026-09-19)

Step 3 base: `main` at `d6350cea7ff7dadc2bbd444f37ed8c81766b7195`.
Branch: `implementation/external-gate-cases`. External frozen cases: **SYNTHETIC V1**.
Case count: **8**; swap groups: **4**, two images each. This freezes only the external
case assets, not the overall protocol or any provider capability result.

The [manifest](../configs/pre_freeze/external_gate_cases.v1.json) uses the existing
external case schema and contains fixed target queries, canonical normalized GT
boxes and repository-relative PNG paths. Images are tracked in
`tests/fixtures/pre_freeze/frozen_external_gate/`; the existing synthetic fixture
exception in `.gitignore` already permits them. No benchmark image is stored there.

| Group | Target / distractor | Target movement (reciprocal) |
|---|---|---|
| A | Red square / blue square | Left to right |
| B | Green circle / orange circle | Top to bottom |
| C | Yellow triangle / purple triangle | Top-left to bottom-right |
| D | Cyan rectangle / dark gray rectangle | Top-right to bottom-left |

The [generator](../scripts/generate_external_gate_cases.py), version `synthetic-v1`,
draws fixed integer primitives on a white 256 x 256 RGB canvas using the existing
Pillow 12.3.0 / Python 3.11.9 environment. There is no randomness, seed, resampling,
antialiasing, text, external source image or network access. PNG compression is fixed
and no optional metadata is added. Pixel-edge boxes use inclusive minima and exclusive
maxima; dividing x by width and y by height gives canonical coordinates. Pixel tests
independently verify the tight colored-object bounds against manifest GT.

[Provenance](../configs/pre_freeze/external_gate_cases.v1.provenance.json) records each
image SHA-256, dimensions, coordinates, RGB colors, movement, generator version/hash,
manifest hash, generation command, Python/Pillow/zlib versions and generation Git HEAD.
The recorded Git SHA is the base HEAD during generation with the new generator in the
working tree; its separate SHA-256 identifies the exact script used. No self-referential
claim that the base commit already contained the generator is made.
Source kind: `synthetic`. **NO_INSPECSAFE_CONTENT_USED**. No COCO, Open Images,
web-downloaded images or copyrighted external assets were used.

- Manifest SHA-256: `fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379`.
- Generator SHA-256: `c5fc2140d1bd2ce9ef323884834911c1e3ef4234172cd3d37c0e6ba4341f4f6c`.
- Deterministic regeneration: **PASS**. A second generation into a fresh temporary
  directory reproduced all 8 PNG hashes and the manifest hash exactly. This is verified
  only in the recorded environment, not a guarantee across dependency versions.
- Existing gate validation: **PASS**, output `FORMAT_VALID`, case count 8,
  `live_gate: NOT RUN`. `gate.py` and the approved schema are unchanged.
- Full repository tests: **217/217 PASS**, including 12 frozen-suite tests covering
  hashes, paths, pixel GT, all motion patterns, reciprocal swaps, invalid cases,
  unsafe output rejection, regeneration and existing validator acceptance.

Reproduce from repository root (the generator writes only the fixed assets and
provenance; `--output-dir` stages a copy under a repository-relative directory):

```powershell
.\.venv\Scripts\python.exe scripts/generate_external_gate_cases.py
.\.venv\Scripts\python.exe scripts/pre_freeze.py validate-cases --manifest configs/pre_freeze/external_gate_cases.v1.json
.\.venv\Scripts\python.exe -m unittest discover -s tests
git diff --check
```

Each generator invocation also rerenders into a temporary directory and checks hashes
before recording PASS. Provenance describes the current invocation, so its own bytes
can change with Git HEAD or the command; only images and manifest are frozen outputs.
Narrow `.gitattributes` entries preserve LF bytes for the generator, manifest and
provenance across Git checkouts. The freeze template pins the actual manifest hash
and suite version `synthetic-v1`.

Checklist #3: **DONE** in this commit with the manifest and images. Checklist #4 and
later remain **PENDING**. GPT capability gate: **NOT RUN**; Claude capability gate:
**NOT RUN**; provider API calls: **NO**; InspecSafe content used: **NO**.
`final_model_roles: PENDING`; `protocol_freeze_commit_sha: PENDING`.
Approved D1-D8 decisions and existing audit notes are unchanged.

## Qwen route and decoding: steps 1–2 (2026-09-19)

Scope: offline configuration verification for P2. This implements the authorized D8
prerequisites without changing P1's upstream `temperature = 0.1` reproduction policy.
The historical D8 approval record retains its original pending wording; this section
records the implementation resolution. Full protocol freeze remains pending.

### Official documentation evidence

All sources below are official Alibaba Cloud Model Studio documentation, accessed
**2026-09-19**. Public documentation availability does not demonstrate access by a
specific workspace/API key. Evidence is `DOC_VERIFIED_AVAILABLE_IN_REGION` and route
`DOC_VERIFIED`; `LIVE_ROUTE_VERIFIED` / `live_route_verified` remains **false**.

| Official title / URL | Evidence used |
|---|---|
| [Regions and endpoints](https://www.alibabacloud.com/help/en/model-studio/regions) (updated 2026-09-17) | Singapore is `ap-southeast-1`; dedicated host is `{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com`. Alibaba recommends workspace-dedicated domains; the existing DashScope domain is also listed. Singapore's service deployment scope is International. |
| [qwen3-vl-8b-instruct](https://www.alibabacloud.com/help/en/model-studio/qwen3-vl-8b-instruct) (updated 2026-09-11) | Exact model ID and Instruct variant; the Singapore model-capability section lists text/image/video input and text output. Official Singapore availability: **YES**. |
| [OpenAI compatible - Chat](https://www.alibabacloud.com/help/en/model-studio/qwen-api-via-openai-chat-completions) | Singapore compatible base URL and POST chat URL; `temperature` supports `[0,2)`, lower values reduce diversity, and only one of `temperature`/`top_p` should be set. |
| [Alibaba Cloud Model Studio model pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing) | Qwen-VL open-source Singapore table explicitly lists `qwen3-vl-8b-instruct` as non-thinking only. No price or performance comparison is used. |

Frozen route templates:

```text
Base: https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
POST https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions
```

The legacy Singapore base `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
may remain functional for existing integrations. SafeShift selects the recommended
workspace-dedicated route and rejects legacy/trial endpoints; it never silently
substitutes them. No claim of successful legacy or workspace access is made.

### Frozen decoding rationale

Policy: **`qwen-singapore-instruct-temperature-zero-v1`**, **`{"temperature": 0}`**,
for both P2 calls. The compatible-chat reference does not specify a separate
`do_sample=false` switch. Its documented lower-temperature guidance supports choosing
the allowed lower bound for reduced output variability. This is SafeShift's
pre-specified protocol choice, not a claim that Alibaba recommends this exact setting
for every task or guarantees deterministic hosted execution. No outputs were compared.

Only `temperature` is explicitly set. `top_p`, `top_k`, seed, penalties and other
sampling controls remain provider defaults by omission; no numeric defaults are
copied into request settings. The model is Instruct/non-thinking only. No
`enable_thinking`, `thinking`, `thinking_budget` or reasoning controls are sent,
including through `extra_body`. `thinking_enabled: false` is policy metadata, not an
additional API argument. The explicit sampling override is fixed before any model call.

Retained limitations: `precision: UNDISCLOSED_BY_PROVIDER` and
`hosted_reproducibility: HOSTED_BACKEND_NOT_FULLY_PINNABLE`. Temperature zero does not
establish bit-for-bit reproducibility or live request acceptance. Future authorized
route verification remains checklist #6; transport and SDK integration are absent.

### Environment-only resolution and validation

Set `QWEN_WORKSPACE_ENDPOINT` in the local process environment to the actual base URL
copied from the Singapore workspace's API Host. Alternatively set `QWEN_WORKSPACE_ID`
to the actual ID: derivation uses exactly the frozen template above. An explicit
endpoint takes precedence; an invalid/empty explicit endpoint fails without falling
back to the ID. No endpoint/ID is accepted from CLI flags, inline JSON or dotenv files.

`validate_workspace_endpoint()` accepts only the exact lowercase HTTPS base URL with
one ASCII DNS label (1–63 characters, alphanumerics and internal hyphens) before the
Singapore suffix. This is a local URL-safety rule, not a provider allocation rule or
proof that the ID exists. Wrong regions, trial/legacy hosts, malformed labels,
userinfo, ports, query/fragment, whitespace and extra paths are rejected. Use the
base URL without a trailing slash. Errors do not include supplied values.

`resolve_qwen_configuration()` validates the pinned model/decoding policy, reads only
the two route variables, and retains a validated endpoint in memory. It does not read
`DASHSCOPE_API_KEY`, contact a provider, write files, or change tracked checklist state.
Its report omits the endpoint; the committed template uses `ENVIRONMENT_ONLY`.
No variables were set locally at this verification, so checklist #1 stays
**PENDING_USER_CONFIGURATION**. A future local `RESOLVED` result means syntactic route
validation only, with checklist #1 `DONE` and live verification still **false**.

From repository root:

```powershell
.\.venv\Scripts\python.exe scripts/validate_qwen_config.py
.\.venv\Scripts\python.exe -m unittest discover -s tests
git diff --check
```

The validator exits 0 for a valid policy (including an explicitly reported pending
endpoint), and 2 for invalid configuration. It prints only safe policy/status fields.
It does not freeze the protocol or authorize inference. Synthetic DNS labels in tests
are fixtures only, never workspace allocation or access evidence.

Validation: **233/233 repository tests PASS**, including 16 new configuration tests.
The offline validator reports checklist #1 `PENDING_USER_CONFIGURATION`, checklist
#2 `DONE`, and live route false. `git diff --check`: **PASS**. Environment: Python
3.11.9, Pillow 12.3.0, existing `.venv`; no dependency changes or random sampling.
The branch's Git revision identifies the implementation; no run artifacts are created.
SYNTHETIC V1 manifest SHA-256 remains
`fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379`.
GPT gate: **NOT RUN**; Claude gate: **NOT RUN**; InspecSafe inference: **NO**;
paid inference calls: **NO**; `final_model_roles: PENDING`;
`protocol_freeze_commit_sha: PENDING`.

## Offline verification and reproduction

Run from repository root using the existing environment (Python 3.11.9, Pillow 12.3.0;
no new dependency). No random sampling is used in the new tests; seed is not applicable.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe scripts/pre_freeze.py validate-cases --manifest tests/fixtures/pre_freeze/external_cases.example.json
.\.venv\Scripts\python.exe scripts/pre_freeze.py replay-dummy-gate --manifest tests/fixtures/pre_freeze/external_cases.example.json --responses tests/fixtures/pre_freeze/dummy_predictions.json
git diff --check
```

Validation on 2026-09-18: **199/199 repository tests passed**, including **54 new
offline tests**. Coverage includes independent inputs, all four handcrafted provider
envelopes, native coordinate conversion, malformed/partial/empty outputs, preservation
before parsing, write failures and overwrite rejection, gate tracking/distractor/full-image
behavior, qualitative-review pending state, firewall paths and D5 consumer contracts.
Initial `python` invocation lacked Pillow and produced four test-import errors;
rerunning with the existing `.venv` resolved this without installation/network access.
Dummy CLI replay is explicitly labelled `handcrafted_dummy`, `live_gate: NOT RUN`.
Temporary test artifacts are synthetic and cleaned up; no benchmark artifacts are read.

D8 normalization correction verified on 2026-09-19: **205/205 repository tests
passed** using the same `.venv`, including six added regression tests for clamping
and invalid coordinates. Raw-preservation tests also cover clamped provider outputs.
`git diff --check` passed. Approved D8 and all other protocol policies are unchanged.

Not run: GPT/Claude live gates, live provider/model availability verification, InspecSafe
inference, paid API calls, complete D5 metric evaluation and protocol freeze. These
are outside this task. The versioned source tree identifies the implementation commit;
when materializing the freeze template later, fill `git_commit_sha` from the reviewed
implementation revision while keeping the separate freeze SHA pending until approval.
