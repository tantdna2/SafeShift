# D9R9 — PaliGemma single-T4 runtime qualification

**Research Lead decision: REAL_RUNTIME_STATUS=RUNTIME_SMOKE_PASS;
EXACT_RUNTIME_VERIFIED=true.** This qualifies only the two-call handcrafted
runtime smoke. The [small result record](../configs/pre_freeze/paligemma_t4_runtime_result.v1.json)
records the Research Lead's direct review of the owner-run Kaggle result bundle.
Codex did not inspect bundle/raw bytes and did not rerun, provision, load a model
or execute GPU work to record this decision.

## Evidence provenance

- Bundle SHA256: `093b03cae9e654a26268fd2f7d474f3b9de40c2b6fa98d98c5f15d0bb586ba74`.
- Execution commit: `180c0623149bbc7d64f5b659f6c044c39b1e1cd0`.
- Model: `google/paligemma-3b-mix-448`.
- Revision: `ead2d9a35598cb89119af004f5d023b311d1c4a1`.
- Canonical plan SHA256: `4138071ff3fcbcf2cb16d456c01a2b3dbc42a628b0faa0d04dd6a635803b0ab7`.
- Snapshot: 14/14 files verified online and offline.
- Software: all exact D9R8 plan pins matched, per Research Lead review.
- Hardware: one process-visible Tesla T4, CC 7.5, 15,636,037,632 VRAM bytes,
  CUDA runtime 12.4, cuda:0; FP16/NONE/batch 1.
- Owner venue Internet-OFF attestation=true; offline environment PASS.

The bundle and raw artifacts remain outside Git. The supplied decision did not
include a run ID, raw paths, full generated IDs, summary checksum, before-load
memory or after-load reserved memory; this transcription does not invent them.
All supplied software, hardware, checksum and timing fields are in the result.
The pinned plan remains historical PREP evidence and is not modified to record
runtime status: changing it would break the audited plan digest.

## Runtime and raw evidence

The independent D9R8 summary reports RUNTIME_INTERFACE_PASS,
model_load_count=1, native_generate_calls=2 and runner_state=GENERATED.
Both raw metadata records have parse_status=NOT_ATTEMPTED before adapter
dispatch; Research Lead accepted raw-before-adapter PASS. The classification
adapter returns INVALID as EXPECTED_PENDING; this does not indicate runtime failure.

| Call | Native text with special tokens | Continuation IDs | Raw SHA256 |
| --- | --- | --- | --- |
| case_01 | `blue<eos>` | `[8796, 1]` | `d40f43c73e9dc2139cee0f32f6db0db8cc012062ef96ffad07cefe90b5706bcc` |
| case_02 | `green<eos>` | `[9740, 1]` | `86629348e4c3b4fbe8513d20afebb9f49b3ef46fe7b7dc55a0a3322708bd80d5` |

These are **OBSERVED_ONLY** color-question outputs. Neither contains a loc token.
They do not freeze a production classification grammar, qualify grounding, test
multiple-box separators or establish/freeze no-detection behavior.

Memory in bytes: after-load allocated 5,860,761,600; peak allocated 5,997,785,600;
peak reserved 6,161,432,576. Harness wall time: 72.795738743 seconds.

## Timing instrumentation finding and correction

The supplied profiler observations, in order, are:

| Scope | Seconds | Interpretation |
| --- | ---: | --- |
| runner_load_including_snapshot_and_transfer | 55.543600983 | Actual initial load span, including snapshot verification and device transfer |
| runner_load_including_snapshot_and_transfer | 0.000652138 | Idempotent/no-op load re-entry |
| native_generate | 1.893213143 | case_01 generation |
| runner_load_including_snapshot_and_transfer | 0.000536080 | Idempotent/no-op load re-entry |
| native_generate | 0.571769282 | case_02 generation |

observer_errors=[] and unfinished_spans=0. The former notebook validator required
exactly `load, generate, generate`, so it incorrectly rejected valid instrumentation.
Research Lead classifies this as NOTEBOOK_INSTRUMENTATION_BUG_NOT_RUNTIME_FAILURE
and accepts runtime PASS without rerunning.

Source corroboration: D9R8 contracts execute `runner.load()` before each call;
PaliGemmaRunner.load returns immediately when resources already exist. Thus load
method entries are not checkpoint reloads. The model load count remains the
independent runner summary's 1, not the profiler's 3 load spans. No duration
threshold or sum of no-op durations defines that count.

The notebook now requires a successful one-load/two-call summary, no observer
errors or unfinished spans, an initial load observation and exactly two native
generate spans. It retains the first load separately from all later idempotent
load re-entries and obtains per-call generation times by filtering generation
spans. It still rejects actual reload counts, failed summaries, incomplete or
invalid timing evidence. Original profiler observations are preserved. This
patch changes post-run evidence validation only, not inference, raw persistence,
the observer, scientific contract, execution pin, software or resource settings.
No rerun is requested or performed. Timings are instrumented wall times, not
an optimization benchmark or a pure checkpoint-deserialization measurement.

## Qualification boundary and validation

Grounding, classification interface and external gate stay PENDING_QUALIFICATION.
Grounding has not run; its pending adapter remains UNSUPPORTED. PaliGemma stays
BACKUP_1, primary roster count=4, promotion=false, protocol freeze PENDING/BLOCKED,
and InspecSafe authorized=false. Synthetic-v1 and InspecSafe were not executed.

Related static/fake suite: **233 tests PASS**, including the supplied five-span
sequence, no-op classification without a duration heuristic, rejection of actual
reloads/observer failures and an end-to-end fake notebook export with re-entries.
The suite covers result transcription, notebook orchestration, PaliGemma and
InternVL3 preparation, runner contracts, source audits, roster and provenance.
All pre-freeze JSON files parse; notebook code compiles; secret and diff checks
pass. No real GPU/model/provisioning or gate execution is part of these checks.

```text
python -m unittest tests.test_paligemma_runtime_result tests.test_paligemma_d9r9_notebook tests.test_paligemma_prep tests.test_local_runners tests.test_internvl3_prep tests.test_internvl3_runtime_result tests.test_d9r6_paligemma_primary_expansion_precommit tests.test_d9r7_paligemma_source_api_audit tests.test_d9_t4_roster_revision tests.test_model_provenance -q
git diff --check
```
