# W2.6B2B-PREP — Ovis2.5-9B single-GPU BF16 runtime smoke

**PREPARED / NOT RUN.** This task prepares a future owner-run technical
runtime/interface smoke. No Ovis snapshot or weight was downloaded, no GPU or custom
remote code was executed, and no real inference occurred while preparing this
runbook. A future `RUNTIME_SMOKE_PASS` may be recorded only from the real run evidence
after Research Lead review; this document does not record that result.

Base main: `609964fe04024d51a6f329ec78f1e578dfeb227c` (PR #25 merge).
Branch: `validation/d9-ovis-gpu-smoke`.

This smoke uses two locally generated geometric images only. It does not open or run
SYNTHETIC V1, does not use InspecSafe-V1, and does not evaluate safety accuracy or
spatial capability. Both `RUNTIME_SMOKE_01` and `RUNTIME_SMOKE_02` are
`Task.CLASSIFICATION` interface calls. They are not execution of the P2
classification-plus-grounding protocol, and no `Task.GROUNDING` call or point/box
parse is permitted here.

## Fixed smoke-only condition

The tracked plan is
[`configs/pre_freeze/ovis_gpu_smoke.v1.json`](../configs/pre_freeze/ovis_gpu_smoke.v1.json).
The harness rejects additions or changes instead of accepting opportunistic CLI
overrides.

| Field | Fixed PREP value |
|---|---|
| Requested research model ID | `AIDC-AI/Ovis2.5-9B` |
| Resolved download repository | `ATH-MaaS/Ovis2.5-9B` |
| Immutable revision | `d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd` |
| Hardware | `NVIDIA_SINGLE_GPU_BF16_MIN_40GB` |
| Precision / quantization | `BF16` / `NONE` |
| Placement | explicit `cuda:0` |
| Preprocessing | `official_preprocess_inputs`, `448*448` through `1792*1792` pixels |
| Thinking | `enable_thinking=false`, `enable_thinking_budget=false` |
| Smoke decoding | `do_sample=false`, `max_new_tokens=32`; no temperature |
| Attention plan | `DOCUMENTED_FLASH_ATTN_RECIPE`; no runner override |
| Cases | exactly `RUNTIME_SMOKE_01`, `RUNTIME_SMOKE_02` |
| Image generator | deterministic `runtime-smoke-geometry-v1` |
| Protocol freeze | `PENDING` |

The literal prompt is fixed before output inspection:

> You are performing an interface smoke test. Inspect the image and return exactly one JSON object with one key named safety_level. Its value must be one of: Level01, Level02, Level03, Level04. Do not output markdown or any other text.

Its SHA-256 is
`681fb3f051871bd9dd52a8100816f864ceb82ea0b5ac332bb2c7a22aed6bda48`.
The two image byte hashes must differ. The report records each case ID, image hash,
dimensions and generator version. The image content has no benchmark meaning, and
the outputs must not be interpreted as correct or incorrect predictions.

BF16 / NONE / `cuda:0`, disabled thinking and greedy 32-token decoding are
**smoke-only technical candidates**. They are not selected research settings and do
not freeze precision, quantization, thinking or decoding. The runner remains
unchanged and must not be given `device_map="auto"`, CPU offload, quantization,
multi-GPU sharding or an attention implementation override.

## Hardware and software prerequisites

Use one visible NVIDIA CUDA GPU with at least 40,000,000,000 bytes of VRAM.
An A100 is not required. The preflight requires
all of the following before model construction:

- CUDA is available and exactly one CUDA device is visible;
- the visible device is logical index 0, exposed as `cuda:0`;
- total memory is at least 40,000,000,000 bytes;
- compute capability is at least 8.0;
- `torch.cuda.is_bf16_supported()` is true; and
- no undersized MIG partition is exposed as the selected device.

Examples that may meet this gate are A40 48GB, RTX A6000 48GB, L40S 48GB, and
A100 40/80GB. These are examples, not a whitelist: actual runtime capabilities
determine PASS. GPU name, UUID, driver, total VRAM and MIG mode remain observed
evidence. MIG is not rejected by name; a logical MIG device may pass if every
capability check passes, while a partition below 40GB fails the VRAM check.

Do not use Kaggle T4 x2 for this run. The checkpoint weight bytes total
18,349,727,512 (approximately 18.35 GB), while
each T4 has approximately 16 GB, and the current Ovis runner implements one explicit
device, `cuda:0`, without multi-GPU sharding. Two visible T4s do not combine into a
single device's VRAM or a supported Ovis placement. A BF16-capable 24GB GPU fails
the memory gate, and two visible GPUs fail regardless of their combined VRAM.

When a host has multiple GPUs, set `CUDA_VISIBLE_DEVICES` to one qualifying physical
GPU index or UUID **before starting any Python process**. Inside the smoke process
that selected device must appear as the sole logical `cuda:0`; do not expose several
GPUs and rely on an automatic mapper.

Python 3.11 is a SafeShift-selected smoke environment candidate, not a
provider-documented Ovis requirement. Use the full Ovis documentary image/video
package recipe below:

| Package | Required smoke candidate |
|---|---|
| `torch` | `2.4.0` |
| `transformers` | `4.51.3` |
| `numpy` | `1.25.0` |
| `Pillow` | `10.3.0` |
| `moviepy` | `1.0.3` |
| `flash-attn` | `2.7.0.post2`, installed with `--no-build-isolation` |
| `huggingface_hub` | resolver-selected compatible version; record the exact installed version |

The smoke blocks before model load when a pinned package does not match. It records
Python, torch, torch CUDA runtime, NVIDIA driver, Transformers, NumPy, Pillow,
flash-attn, MoviePy and huggingface_hub exactly. Installing flash-attn does not prove
which attention implementation executed. The report records the effective
implementation when it can be inspected and otherwise records `UNKNOWN_OBSERVED`;
it never guesses and never changes the runner to force flash attention.

## Exact snapshot and local-byte gate

Online provisioning is a separate phase. The provisioner downloads the full snapshot
with `snapshot_download` from only the resolved repository and immutable revision:

```text
repo_id  = ATH-MaaS/Ovis2.5-9B
revision = d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd
```

It must retain the Hugging Face cache layout expected by the existing runner:

```text
models--ATH-MaaS--Ovis2.5-9B/
  snapshots/
    d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd/
```

Do not download via the requested redirect ID, a mutable `main`/`latest` revision,
or copy the snapshot to an arbitrary directory. Provisioning does not import the
downloaded Python source and does not run the model.

Both provisioning and the independent `--verify-only` pass check all four shard
sizes and SHA-256 values against
`configs/pre_freeze/local_model_provenance.d9.json`. They also verify the pinned
documentary hashes for `README.md`, `config.json`, `preprocessor_config.json`,
`generation_config.json` and `modeling_ovis2_5.py`. Required tokenizer/configuration
assets without a documentary expected hash must exist; their local hashes are
reported as `RECORDED_LOCAL_HASH_ONLY`, never as verified against provenance.
Any absent asset, wrong cache identity, size mismatch or hash mismatch is a stop
condition.

`--verify-only` sets `local_files_only=True`, performs no download and must not use
the network. Its exclusive report directory is separate from the provisioning
report directory so neither attempt overwrites evidence.

The future runtime report records the runner version, both model identities, exact
revision, `trust_remote_code=True`, `local_files_only=True`, snapshot-verification
result and critical source hashes. It records only the cache-layout identity of the
local snapshot in shareable evidence, not an absolute host/user path. Executing the
pinned custom code is authorized only in the later offline smoke process, after all
local verification gates pass; provisioning and PREP unit tests never import it.

## Execution procedure

Run these steps on an authorized host meeting the single-GPU capability gate. Stop
immediately on a failed checkout, install, provision, byte verification or preflight. Do not repair the
condition by switching precision, quantizing, offloading, exposing another GPU or
changing the prompt.

### 1. Check out the immutable PREP source

The Draft PR must publish `B2B_PREP_HEAD`, the exact reviewed 40-character commit
for execution. Obtain that value from the Research Lead; do not execute a moving
branch or `main`. Clone credentials, if needed, must be supplied through the host's
credential mechanism and must never be embedded in a URL, command log or report.

```bash
git clone --branch validation/d9-ovis-gpu-smoke --single-branch https://github.com/tantdna2/SafeShift.git SafeShift
cd SafeShift
export B2B_PREP_HEAD="<40-character SHA published in the Draft PR>"
git checkout --detach "$B2B_PREP_HEAD"
test "$(git rev-parse HEAD)" = "$B2B_PREP_HEAD"
git merge-base --is-ancestor 609964fe04024d51a6f329ec78f1e578dfeb227c "$B2B_PREP_HEAD"
test -z "$(git status --porcelain --untracked-files=no)"
```

Keep `B2B_PREP_HEAD` exported through the later Python smoke invocation; do not unset
it after checkout. The harness checks it again before software/GPU preflight,
snapshot verification, runner creation or model load. It requires exactly 40
lowercase hexadecimal characters and equality with `git rev-parse HEAD`. Missing,
invalid or mismatched pins fail closed with `B2B_PREP_HEAD_REQUIRED`,
`B2B_PREP_HEAD_INVALID` or `EXECUTION_COMMIT_MISMATCH` respectively.
The runtime report preserves actual `git_commit` separately from `execution_pin`
and records `execution_identity_verified`; `environment.json` also records the pin.
After a reviewed code update, the PR body must publish the new `B2B_PREP_HEAD`, and
the operator must check out and export that reviewed SHA before a new attempt.

### 2. Expose exactly one qualifying GPU and install the smoke candidate

Choose one qualifying GPU index or UUID from `nvidia-smi -L`, then set it before
the virtual environment's Python is invoked:

```bash
nvidia-smi -L
export CUDA_VISIBLE_DEVICES="<one qualifying GPU index or GPU UUID>"
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install torch==2.4.0 transformers==4.51.3 numpy==1.25.0 pillow==10.3.0 moviepy==1.0.3
python -m pip install flash-attn==2.7.0.post2 --no-build-isolation
python -m pip check
```

If this exact environment cannot be installed on the host, preserve the installation
failure and stop for Research Lead review. Do not silently upgrade Transformers or
substitute another torch, NumPy, Pillow or flash-attn version.

### 3. Provision the exact snapshot online

Internet access is allowed only for this provisioning/setup phase. Use one cache for
provisioning, verification and later offline execution:

```bash
export HF_HUB_CACHE="$(pwd)/data/processed/hf-cache"
export HF_HUB_DISABLE_TELEMETRY=1
unset HF_HUB_OFFLINE
unset TRANSFORMERS_OFFLINE
python scripts/provision_ovis2_5_snapshot.py \
  --cache-dir data/processed/hf-cache \
  --report-dir data/processed/runtime_validation/w2_ovis_gpu_smoke_setup/provision
```

This is the only step allowed to download model files. A successful exit means the
run-scoped local checks passed; it is not a protocol freeze or model capability
result.

### 4. Repeat verification with the local-only path

```bash
python scripts/provision_ovis2_5_snapshot.py \
  --verify-only \
  --cache-dir data/processed/hf-cache \
  --report-dir data/processed/runtime_validation/w2_ovis_gpu_smoke_setup/verify-only
```

Confirm that both report directories contain exactly the expected small reports:
`snapshot_verification.json`, `weight_verification.json` and
`critical_file_verification.json`. Do not continue after any nonzero exit or any
false verification result.

### 5. Make the offline transition

Only after provisioning and the independent local-only verification succeed, set all
offline controls in the parent shell so the smoke process inherits them:

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1
test "$HF_HUB_OFFLINE" = 1
test "$TRANSFORMERS_OFFLINE" = 1
test "$HF_HUB_DISABLE_TELEMETRY" = 1
```

The harness independently requires these values, resolves only the exact cached
snapshot and denies Python TCP, UDP and DNS attempts after this transition through
`socket.socket.connect`, `socket.socket.connect_ex`, `socket.socket.sendto`,
`socket.create_connection` and `socket.getaddrinfo`. Each uses the same counting
firewall and raises a controlled runtime failure. `network_violation_count` must be
zero; any positive count is a blocking failure and must not trigger an online retry.

### 6. Run one lifecycle with two sequential classification calls

Create one new run ID and invoke the harness once:

```bash
export RUN_ID="gpu-bf16-ovis-$(date -u +%Y%m%dT%H%M%S%NZ)"
python scripts/w2_ovis_gpu_smoke.py --run-id "$RUN_ID"
export SMOKE_EXIT=$?
echo "Smoke exit code: $SMOKE_EXIT"
echo "Evidence root: data/processed/runtime_validation/w2_ovis_gpu_smoke/$RUN_ID"
```

The harness creates exactly one `Ovis2_5Runner` instance. `execute_call` invokes the
runner's idempotent lifecycle for each request, but PASS requires exactly one
underlying successful native model-load lifecycle and exactly two native
`generate` calls on that same model instance. No direct parallel generation path or
second runner is allowed.

Before load, the harness verifies the execution pin, hardware, installed versions,
offline state, snapshot identity and local bytes. After load it records:

- distinct parameter devices and parameter counts/bytes by device;
- a separate buffer-device census;
- a blocker for any `meta` parameter or any floating parameter outside `cuda:0`;
- floating-parameter dtype counts/bytes, with BF16 as the required smoke dtype; and
- effective attention information when inspectable.

The expected placement is `cuda:0` only. A floating parameter dtype other than
`torch.bfloat16` is recorded in detail and cannot silently pass; the predeclared
dtype-deviation policy produces a blocking review result rather than casting the
model after load.

GPU memory evidence is recorded before load, after load, after call 1 and after call
2. Each observation includes allocator allocated/reserved/peak values and free/total
VRAM. An OOM is `RUNTIME_SMOKE_FAIL`; preserve the failure evidence and do not retry
with FP16, quantization, CPU offload or multi-GPU placement.

### 7. Inspect the report and allowlisted evidence bundle

The harness writes the run under:

```text
data/processed/runtime_validation/w2_ovis_gpu_smoke/<RUN_ID>/
```

It creates these small run-scoped reports:

- `runtime_report.json`
- `environment.json`
- `snapshot_verification.json`
- `weight_verification.json`
- `critical_file_verification.json`
- `case_manifest.json`
- one `response.raw` and `metadata.json` pair for each completed call under `raw/`
- `ovis_gpu_smoke_evidence.zip`
- `ovis_gpu_smoke_evidence.zip.sha256`

Inspect the concise status without editing any artifact:

```bash
python - <<'PY'
import json, os
from pathlib import Path
root = Path("data/processed/runtime_validation/w2_ovis_gpu_smoke") / os.environ["RUN_ID"]
report = json.loads((root / "runtime_report.json").read_text(encoding="utf-8"))
keys = ("run_id", "status", "blocker", "git_commit", "execution_pin",
        "execution_identity_verified", "load_lifecycles", "native_generate_calls",
        "network_violation_count", "claims", "calls")
print(json.dumps({key: report.get(key) for key in keys}, indent=2))
print((root / "ovis_gpu_smoke_evidence.zip.sha256").read_text(encoding="utf-8"))
PY
```

For every generated response, `response.raw` is the unchanged runner envelope and
its adjacent `metadata.json` is the pre-adapter record with
`parse_status=NOT_ATTEMPTED`. The runtime report separately records the final adapter
status and SHA-256 for both files. The raw file must never be rewritten to make a
parse succeed.

`ParseStatus.SUCCESS` and `ErrorCode.INVALID_CLASSIFICATION` are the only allowed
completed-call outcomes for a PASS candidate. Invalid classification is a
nonblocking interface observation and not an accuracy judgment. `PARSER_FAILURE`,
including a structural adapter error after native generation, is blocking. Every
other runner error, incomplete second call, wrong lifecycle/generate count, native
exception, OOM, evidence-preservation failure, placement/dtype violation or network
attempt is also blocking.

The ZIP helper uses an explicit allowlist. The archive contains the reports, case
manifest and small raw/metadata pairs listed above. It excludes weights, the HF
cache, snapshot/code assets, tokens and credentials, arbitrary logs, dataset content
and generated image binaries. The sidecar records the ZIP SHA-256. Do not add omitted
files manually.

### 8. Stop and send evidence to the Research Lead

Download `ovis_gpu_smoke_evidence.zip`, verify its sidecar hash, send the ZIP and hash
to the Research Lead, and **stop**. Do not commit the ZIP, runtime report, raw output,
metadata, images, weights or cache. Do not mark repository status PASS until the real
evidence has been audited and a separate result-recording task is authorized.

## PASS boundary and claims

`RUNTIME_SMOKE_PASS` can mean only that this exact Ovis checkpoint, exact runner,
verified local snapshot, documented BF16 single-GPU path and recorded environment
completed the two-call interface/runtime smoke. The report's `claims` object must
keep all of the following false even after a runtime PASS:

- `capability_pass`
- `grounding_pass`
- `accuracy_pass`
- `benchmark_pass`
- `precision_frozen`
- `decoding_frozen`
- `thinking_frozen`
- `protocol_frozen`

It does not qualify Ovis grounding, run SYNTHETIC V1, assign final model roles,
change D5, or authorize InspecSafe inference. Ovis grounding remains
`DOCUMENTED_BOX_AND_POINT / NOT_YET_QUALIFIED`; Checklist #2 remains PENDING overall,
Checklist #3–#8 remain PENDING, and
`protocol_freeze_commit_sha: PENDING`.

## Failure and authorized rerun

On failure, keep the original run directory and bundle. Do not overwrite evidence,
auto-rerun, change configuration, or hide a partial/fatal attempt. A rerun requires
Research Lead review and an explicit approved reason, then a new run ID linked to the
old one:

```bash
export OLD_RUN_ID="<failed run ID>"
export NEW_RUN_ID="gpu-bf16-ovis-$(date -u +%Y%m%dT%H%M%S%NZ)"
python scripts/w2_ovis_gpu_smoke.py \
  --run-id "$NEW_RUN_ID" \
  --rerun-of "$OLD_RUN_ID" \
  --rerun-reason "<explicit Research Lead-approved reason>"
```

An approved rerun is a new attempt, not a replacement for the previous evidence.
If a configuration or code change is needed, stop and obtain a reviewed update; do
not tune prompt, thinking, decoding, precision or placement after seeing output.
