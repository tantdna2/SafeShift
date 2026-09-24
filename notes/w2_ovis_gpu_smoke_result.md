# W2.6B2B — audited real Ovis GPU runtime smoke result

**RUNTIME_SMOKE_PASS / VALIDATED — RUNTIME_INTERFACE_ONLY.** Research Lead
directly audited the real-run evidence bundle and supplied the verdict and values
recorded here through the Project Owner's instruction. This recording task
transcribes that audit; the recording agent did not independently receive, inspect
or re-hash the ZIP, contact the model host, download weights or rerun inference.
The [machine-readable summary](../configs/pre_freeze/ovis_gpu_smoke_result.v1.json)
contains summary facts and hashes, not the raw runtime report or model envelope.

## Evidence and immutable execution identity

| Field | Audited value |
|---|---|
| RUN_ID | `ckey-a40-ovis-20260924T042034999220552Z` |
| Evidence ZIP | `ovis_gpu_smoke_evidence.zip` |
| Evidence ZIP SHA-256 | `f6b4756d3e57a213e6302f3170de10c46d334865aed5735ea906647ede46ce76` |
| B2B_PREP_HEAD / EXECUTION_COMMIT | `c2a5d97945b27d16425f82592a352722ee935118` |
| Actual git_commit / execution_pin | `c2a5d97945b27d16425f82592a352722ee935118` |
| execution_identity_verified | `true` |
| Smoke config SHA-256 | `52fc7a3a10fb47124bf51883de8017d39fde8c906ad6a150fdc880106478cb75` |
| Prompt SHA-256 | `681fb3f051871bd9dd52a8100816f864ceb82ea0b5ac332bb2c7a22aed6bda48` |

The execution SHA is the exact code that ran on the GPU. The separate
`RESULT_RECORDING_COMMIT`, published in [PR #26's body](https://github.com/tantdna2/SafeShift/pull/26),
only records the audited result. It must never replace the historical
`B2B_PREP_HEAD`, `execution_pin` or `EXECUTION_COMMIT`. Its own SHA is referenced
through the PR body to avoid a self-referential commit hash. No rerun is required
or authorized by this recording task.

Research Lead audited exactly ten ZIP members: the two `response.raw` and
`metadata.json` pairs under `calls/RUNTIME_SMOKE_01/` and
`calls/RUNTIME_SMOKE_02/`, plus `case_manifest.json`,
`critical_file_verification.json`, `environment.json`, `runtime_report.json`,
`snapshot_verification.json` and `weight_verification.json`. Research Lead's scan
reported no GitHub token, password, AWS key or secret-like credential. The ZIP and
all raw runtime artifacts stay outside Git.

## Model, condition and environment

Research identity remains `AIDC-AI/Ovis2.5-9B`, with resolved repository
`ATH-MaaS/Ovis2.5-9B`, immutable revision
`d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd` and runner
`ovis2-5-runner-v2`. The run used BF16 / NONE / explicit `cuda:0`, thinking
`false / false`, and `do_sample=false, max_new_tokens=32`. These are validated
smoke runtime conditions only; precision, thinking and decoding are not frozen.

Actual hardware was one **NVIDIA A40**, logical GPU 0, 47,708,110,848 VRAM bytes
(nvidia-smi: 46,068 MiB), compute capability 8.6, BF16 supported, driver
`570.195.03`, MIG `N/A`. This run satisfied the capability-based
`NVIDIA_SINGLE_GPU_BF16_MIN_40GB` gate; A100 is not required.

| Software observation | Exact version |
|---|---|
| Python | 3.11.16 |
| torch distribution | 2.4.0 |
| torch.__version__ | 2.4.0+cu121 |
| torch CUDA runtime | 12.1 |
| Transformers | 4.51.3 |
| NumPy | 1.25.0 |
| Pillow | 10.3.0 |
| flash-attn | 2.7.0.post2 |
| MoviePy | 1.0.3 |
| huggingface_hub | 0.36.2 |

Python 3.11 is the SafeShift-selected smoke environment candidate. The host used
CUDA toolkit 12.4 to build the environment; this is separate from the observed
**torch CUDA runtime 12.1**.

Attention is a nonblocking observation: `FLASH_ATTN_PACKAGE_INSTALLED`, but
`EFFECTIVE_ATTENTION_OBSERVED_EAGER`. Both `model.config._attn_implementation` and
`model.llm.config._attn_implementation` reported `eager`. The plan remains
`DOCUMENTED_FLASH_ATTN_RECIPE` and `runner_override=false`. Installation of
flash-attn is not evidence that FlashAttention actually executed.

## Local snapshot and source verification

`LOCAL_SNAPSHOT_VERIFIED=true`, `SNAPSHOT_PATH_VERIFIED=true`, with suffix
`models--ATH-MaaS--Ovis2.5-9B/snapshots/d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd`.
Runtime reverification used `local_files_only=true`, an enabled network firewall
and zero violations. All four component verdicts passed: snapshot path, weight
bytes, critical provenance hashes and required local assets.

`LOCAL_WEIGHT_BYTES_VERIFIED=true`: all four shards matched the exact sizes and
SHA-256 values retained in the result JSON and unchanged documentary provenance.
This is **run-scoped verification**, not a global promotion of documentary
`local_bytes_verified` to true. Weight bytes total 18,349,727,512.

`CRITICAL_PROVENANCE_HASHES_VERIFIED=true` and
`REQUIRED_LOCAL_ASSETS_PRESENT=true`. README, config, preprocessor config,
generation config and `modeling_ovis2_5.py` matched their five documentary hashes.
The remaining required configuration/tokenizer/index assets remain
`RECORDED_LOCAL_HASH_ONLY`. Their individual local hashes were not supplied in
the audit instruction and are not invented in this summary or promoted to
`VERIFIED_AGAINST_PROVENANCE`.

## Two classification calls and raw preservation

One runner instance, one model load lifecycle and two sequential native generate
calls completed. Both final parse statuses were `SUCCESS`, with `error=null`.
`blocker=null`, `runtime_check_failure=null`, `notes=[]`, `native_errors=[]`,
`network_violation_count=0`; no fallback or online retry. `rerun_of` and
`rerun_reason` were both null.

| Evidence | call_01 / RUNTIME_SMOKE_01 | call_02 / RUNTIME_SMOKE_02 |
|---|---|---|
| Input image SHA-256 | `eafc937f391461f0b29816f3a69654041ec77d543860705cc49a19941785a7bb` | `91b0fc7fd00e1d279c10218c4a54d922302e369ac5c5afdfa35cae618451e73a` |
| Metadata SHA-256 | `5c64dcbe4cb05b1cd2b9cc06a731fee7ae761bd246607f5a86c73d878738bf5a` | `6cbf46a19ee5462369fe16ba4bcb353f438f1883ee24e2b42fa87d2b5b1dfd4f` |
| Metadata size | 2778 bytes | 2778 bytes |
| Raw size | 4156 bytes | 4156 bytes |

Both raw SHA-256 values were
`d3d0b69070ddbd8628e5a90792f1e9b5d43643837c996c85fc87aaad91b20021`.
Pre-adapter metadata retained `parse_status=NOT_ATTEMPTED`,
`source_kind=HANDCRAFTED_RUNTIME_SMOKE` and `task=classification`.
Both decoded to the single safety-level value `Level01`, followed by
`<|im_end|>` in the special-token representation. These compact observations do
not reproduce the full raw envelope.

Distinct input hashes and identical raw outputs are an observation only. They do
not establish that the model ignored the image, semantic correctness, capability
pass/failure or accuracy pass/failure.

## Placement, dtype and memory diagnostics

Placement validation passed: all 840 parameter tensors (9,174,807,784 elements,
18,349,615,568 bytes) were on `cuda:0`, with no violations, CPU offload, meta
parameters or multi-GPU placement. Floating dtype validation passed with
`EXPECTED_BF16_ONLY`: the same census was entirely `torch.bfloat16`, deviations
`{}`, with no silent cast.

All memory values below are bytes. Before load, total VRAM was 47,708,110,848.
Peak fields not supplied for the before-load observation are left unreported.

| Stage | Free | Allocated | Reserved | Max allocated | Max reserved |
|---|---:|---:|---:|---:|---:|
| before_load | 47428993024 | 0 | 0 | not supplied | not supplied |
| after_load | 28976152576 | 18359789568 | 18452840448 | 18359789568 | 18452840448 |
| after_call_1 | 28598665216 | 18368309248 | 18763218944 | 18511427584 | 18763218944 |
| after_call_2 | 28598665216 | 18368309248 | 18763218944 | 18511427584 | 18763218944 |

No OOM. Reported allocator values did not increase from call 1 to call 2. This is
a two-call diagnostic, not a performance benchmark or long-run stability claim.

## Claim boundary and status

`RUNTIME_SMOKE_PASS` means the exact checkpoint, runner, verified local snapshot,
BF16 single-GPU path and recorded environment completed runtime/interface smoke.
All eight claims remain false: capability, grounding, accuracy, benchmark,
precision freeze, decoding freeze, thinking freeze and protocol freeze.

Ovis grounding remains `DOCUMENTED_BOX_AND_POINT / NOT_YET_QUALIFIED`. No
`Task.GROUNDING`, canonical grounding SUCCESS, IoU, point-to-box conversion,
SYNTHETIC V1 gate, final role assignment or InspecSafe inference is recorded.

Checklist #1 is documentary COMPLETE; #2 remains **PENDING overall**. Qwen and
Ovis offline implementations are COMPLETE and their real runtime smoke results
are PASS / VALIDATED. Molmo and Gemma remain PENDING. Checklist #3–#8 and
`protocol_freeze_commit_sha` remain PENDING.

Offline result tests check the supplied audit values and their consistency with
tracked plan/provenance and execution-commit Git blob bytes. They do not access
the runtime ZIP, GPU, weights, network or model host. No runtime code, smoke plan,
documentary provenance, D5 or canonical schema is changed by result recording.

Recording validation, using the existing local `.venv` (Python 3.11.9 / Pillow
12.3.0): **16/16 result tests**, **39/39 smoke-harness tests**, **32/32 Ovis-runner
tests**, and **500/500 full-suite tests PASS**; `git diff --check` PASS. These local
test versions are separate from the audited GPU environment above. Commands:

```text
python -m unittest tests.test_ovis_gpu_smoke_result -v
python -m unittest tests.test_ovis_gpu_smoke_harness -v
python -m unittest tests.test_ovis_runner -v
python -m unittest discover -s tests
git diff --check
```

The execution config hash matches Git blob bytes at the execution commit,
independently of checkout line endings. This is repository consistency checking,
not another audit of the external runtime bundle. Census remains untracked and
untouched; no runtime artifacts are committed and PR #26 remains Draft.
