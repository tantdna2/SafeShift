# W2.6B1B — audited real Kaggle runtime smoke result

**RUNTIME_SMOKE_PASS — runtime/interface validation only.** On 2026-09-23,
the Project Owner supplied the Research Lead's conclusion after direct audit of
the evidence bundle downloaded from Kaggle. This record transcribes that authorized
audit summary; the recording agent did not receive or independently inspect the ZIP,
re-hash its contents, download weights, or rerun inference. The machine-readable
[result summary](../configs/pre_freeze/qwen_kaggle_smoke_result.v1.json) contains
summary fields and hashes only, not a copied runtime report or embedded raw response.

## Evidence and execution identity

| Field | Audited value |
|---|---|
| Run ID | `kaggle-t4x2-20260923T012029667885Z` |
| Evidence bundle SHA-256 | `ae3e9e1002ce94bf78bb0ac856f1a7f54a48283d64db51cdb8d5eed37f6b8a69` |
| EXECUTION_COMMIT | `784c465cae5188ed6ede5673140a4a281f2ffb52` |
| Smoke config SHA-256 | `ecd34ba5a8880458734e26f2bf0932f5f820607c2b9f3233b4e092980bf79ef9` |
| Prompt SHA-256 | `681fb3f051871bd9dd52a8100816f864ceb82ea0b5ac332bb2c7a22aed6bda48` |
| Exact model | `Qwen/Qwen3-VL-8B-Instruct` |
| Immutable revision | `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` |

The execution commit is immutable historical evidence. The separate
`RESULT_RECORDING_COMMIT` is published in [PR #24's body](https://github.com/tantdna2/SafeShift/pull/24)
after committing this record; it must not replace `EXECUTION_COMMIT` or
`B1B_PREP_HEAD`. No self-referential commit SHA is embedded in its own source.
The config hash was also checked against Git blob bytes at the execution commit
(independent of Windows working-tree line endings); this is a repository consistency
check, not a new audit of the external evidence bundle.

## Local bytes and runtime condition

`LOCAL_WEIGHT_BYTES_VERIFIED = TRUE`: all four local shards matched both published
SHA-256 and byte size in this run. Exact hashes and sizes are retained in the result
JSON and agree with the unchanged documentary provenance. This is **run-scoped
local-byte verification**, not global/frozen verification of every cache or run.

FP16 / quantization NONE / requested device placement auto; observed attention
`sdpa`. Official processor and smoke-only `do_sample=false, max_new_tokens=32`
remain unchanged. FP16 is now a **validated smoke runtime candidate** for this
execution; no research precision, decoding or software environment is frozen.

Kaggle exposed two Tesla T4 GPUs, each 15360 MiB and compute capability 7.5.
Driver: `580.159.04`; torch CUDA runtime: `12.8`. The audited placement summary
places the visual encoder on cuda:0, language layers 0–13 predominantly on cuda:0,
layers 14–35 predominantly on cuda:1, and lm_head on cuda:1. No CPU or disk offload.
This is the supplied summary, not an invented full module-level `hf_device_map`.

| Software | Exact observed version |
|---|---|
| Python | 3.12.13 |
| torch | 2.10.0+cu128 |
| transformers | 4.57.1 |
| accelerate | 1.11.0 |
| huggingface_hub | 0.36.0 |
| safetensors | 0.6.2 |
| Pillow | 11.3.0 |
| zlib | 1.2.11 |

`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`.

## Two independent classification calls and preservation

One `Qwen3VLRunner` instance, `load_lifecycles=1`, `native_generate_calls=2`,
`native_errors=[]`; no OOM or native exception. Both `RUNTIME_SMOKE_01` and
`RUNTIME_SMOKE_02` returned `SUCCESS` with `cache_state_cleared=true`.
Their distinct image SHA-256 values are recorded in the summary JSON.

For both calls, Research Lead verified `response.raw` and `metadata.json` existed
and matched their runtime-report hashes. Preserved pre-adapter metadata has
`parse_status=NOT_ATTEMPTED`; the post-adapter runtime report has `SUCCESS`.
Per-call metadata hashes and the shared raw hash are retained in the summary JSON.
No raw file or runtime metadata file is committed here.

The two raw outputs were identical and both decoded to a JSON object containing
the single `safety_level` value `Level01`. This is only an observation of this
interface smoke. Distinct input hashes with identical outputs establish neither
that the model ignored the images nor that either prediction is correct/incorrect.
No semantic capability, accuracy or good/bad capability conclusion follows.

## Memory diagnostics

All numbers below are bytes; allocator values are reported peaks, not throughput
or a performance benchmark.

| Observation | GPU 0 | GPU 1 |
|---|---:|---:|
| Before load: free | 15526068224 | 15526068224 |
| After load: max allocated | 7800528384 | 9735371264 |
| After call 1: max allocated | 7845763584 | 9777359360 |
| After call 2: max allocated | 7845763584 | 9777359360 |

The reported allocation peaks did not increase between calls 1 and 2. There is no
large memory growth signal in these observations; two calls do not establish
long-run memory stability.

## Status boundary and repository checks

Checklist #1 remains COMPLETE documentary. Checklist #2 remains **PENDING overall**:
Qwen offline implementation COMPLETE; real Kaggle T4×2 smoke PASS / VALIDATED;
Ovis, Molmo and Gemma runner/runtime work remains pending. Checklist #3–#8 and
`protocol_freeze_commit_sha` remain PENDING.

Only `Task.CLASSIFICATION` ran. Qwen grounding remains
`UNCERTAIN_REQUIRES_EXTERNAL_GATE` / `NOT_YET_QUALIFIED`; no bbox qualification,
grounding PASS, capability PASS, accuracy result or benchmark result is claimed.
No SYNTHETIC V1 gate or InspecSafe inference, prompt tuning, backup activation,
final role assignment, precision/decoding/protocol freeze or merge is performed.

Offline summary tests check the supplied identities/hashes, documentary consistency,
hardware/lifecycle/raw evidence summary, memory and limits. They do not revalidate
external GPU execution or inspect the bundle. Run from repository root with the
existing `.venv/Scripts` first on PATH:

```text
python -m unittest discover -s tests
git diff --check
```

Recording validation: **413/413 full-suite tests PASS**, including **10/10 new
summary tests**; `git diff --check` PASS. Existing local environment used; no new
dependencies installed and no model/GPU execution performed by this task.

Evidence ZIP, runtime report, response.raw, runtime metadata, weights and HF cache
stay outside this commit. No execution code, smoke plan, D9 provenance, D5, schema
or SYNTHETIC V1 asset is changed; the census stays untracked and untouched.
