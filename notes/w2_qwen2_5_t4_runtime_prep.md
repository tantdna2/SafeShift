# W2.6-D9R2B-PREP — Qwen2.5 single-T4 qualification preparation

Base: `ae3d440195507acee1112d7fb445af8ad82c475f`.
Branch: `validation/d9-qwen2_5-t4-prep`. Status: **PREPARED_NOT_RUN**.
Model: `Qwen/Qwen2.5-VL-3B-Instruct`, revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`.

## Pre-freeze resource qualification revision

This append-only milestone supersedes the eager attention and default processor
candidate in [D9R2A](w2_qwen2_5_runner_implementation.md). That earlier record
remains historical evidence. Reason: **PRE_FREEZE_RESOURCE_QUALIFICATION_REVISION**.
The changes precede real T4 smoke, protocol freeze and all InspecSafe inference.
No InspecSafe results were used. This is a resource feasibility choice, not
performance tuning or benchmark optimization.

Qualification targets one NVIDIA T4 16GB, FP16, quantization NONE, batch size 1,
all parameters and buffers on cuda:0. CPU/disk offload, model substitution,
automatic precision/quantization changes and attention fallback are forbidden.
No free-VRAM threshold is invented. T4 OOM risk remains unresolved until real
smoke; artifact size and source compatibility do not establish runtime fit.

## Documentary/source verification

The exact [Transformers 4.51.3 source](https://github.com/huggingface/transformers/blob/5f4ecf2d9f867a1255131d2461d75793c0cf1db2/src/transformers/models/qwen2_5_vl/modeling_qwen2_5_vl.py)
declares `_supports_sdpa = True` and maps `sdpa` to both
`Qwen2_5_VLVisionSdpaAttention` and `Qwen2_5_VLSdpaAttention`. Both use PyTorch
scaled-dot-product attention. No FlashAttention2 package is required. The local
audited source SHA-256 is
`72bdd5615b7527543ea7e6d69fbe194c40bddd94cab13e2e83696ff1cfb10719`.
Language attention has an eager branch for `output_attentions=True`; the runner
rejects that flag in generation defaults and model config. The harness checks
actual vision/language attention module classes after load. A failure ends the
run; there is no retry using another attention implementation. PyTorch's internal
SDPA kernel dispatch remains native SDPA, not a Transformers eager fallback.

The exact [pinned Qwen model card](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/blob/66285546d2b821cf421d4f5eb2576359d3770cd3/README.md)
documents a default 4–16384 visual tokens per image and the 256–1280 example.
This candidate passes `min_pixels=200704`, `max_pixels=1003520` to AutoProcessor.
The explicit context is:

```json
{"mode":"official_processor_capped","min_pixels":200704,"max_pixels":1003520}
```

The runner decodes the single in-memory image to RGB, uses the documented
`process_vision_info` path, then the capped processor. Qwen utility preprocessing
can perform its own upstream resizing before the processor applies these caps;
the runner adds no manual resize or per-image override. No `resized_height`,
`resized_width`, adaptive policy or InspecSafe-specific resolution rule is used.
Empty/default-only contexts and mismatched caps fail closed. Loaded processor
attributes are checked, and the attention/caps enter both the execution condition
and raw runtime metadata.

Successful raw envelopes are now `safeshift-qwen2-5-vl-raw-v2`; runner/adapter
versions are v2 because strict metadata now includes the preprocessing policy.
The partial failure schema remains v1. Existing raw files are not rewritten.
Raw-before-parser, canonical classification parsing, independent-call state reset,
exact identity, FP16/NONE and grounding UNSUPPORTED semantics are unchanged.

## Software candidate (documentary resolution, 2026-09-25)

The [environment manifest](../configs/pre_freeze/qwen2_5_t4_runtime.v1.json)
records each official metadata URL, exact wheel filename/URL, published SHA-256,
Python requirement and compatibility rationale. No package was installed for this
task and no weight bytes were downloaded. Published wheel hashes are documentary
metadata, not a claim of local artifact verification.

| Package | Candidate | Python 3.11 Linux x86_64 wheel / compatibility |
|---|---|---|
| Python | 3.11.11 | [Official release](https://www.python.org/downloads/release/python-31111/); CPython 3.11 ABI, separately provisioned interpreter |
| torch | 2.6.0+cu124 | cp311 Linux x86_64; [official CUDA 12.4 index](https://download.pytorch.org/whl/cu124/torch/); Transformers requires >=2.0 |
| torchvision | 0.21.0+cu124 | cp311 Linux x86_64; [paired official wheel](https://download.pytorch.org/whl/cu124/torchvision/); imported by qwen utility even for still images |
| transformers | 4.51.3 | py3-none-any; [PyPI metadata](https://pypi.org/pypi/transformers/4.51.3/json); source commit `5f4ecf2d9f867a1255131d2461d75793c0cf1db2` |
| qwen-vl-utils | 0.0.8 | py3-none-any; [PyPI metadata](https://pypi.org/pypi/qwen-vl-utils/0.0.8/json); exact card version |
| accelerate | 1.6.0 | py3-none-any; [PyPI metadata](https://pypi.org/pypi/accelerate/1.6.0/json); exceeds Transformers >=0.26.0; participates in explicit device_map loader |
| Pillow | 11.2.1 | cp311 manylinux2014; [PyPI metadata](https://pypi.org/pypi/pillow/11.2.1/json); meets Transformers/torchvision image requirements |
| huggingface-hub | 0.30.2 | py3-none-any; [PyPI metadata](https://pypi.org/pypi/huggingface-hub/0.30.2/json); Transformers >=0.30.0,<1.0 |
| tokenizers | 0.21.1 | cp39-abi3 manylinux2014, usable on CPython 3.11; [PyPI metadata](https://pypi.org/pypi/tokenizers/0.21.1/json); Transformers >=0.21,<0.22 |
| safetensors | 0.5.3 | cp38-abi3 manylinux2014, usable on CPython 3.11; [PyPI metadata](https://pypi.org/pypi/safetensors/0.5.3/json); Transformers/accelerate >=0.4.3 |

qwen-vl-utils wheel SHA-256:
`2988aa08256f3d7ee6f08d7b27b004e840608b61ed36d0b32d1775be56a1639d`.
The [exact dependency table](https://github.com/huggingface/transformers/blob/5f4ecf2d9f867a1255131d2461d75793c0cf1db2/src/transformers/dependency_versions_table.py)
and release PyPI metadata support the listed ranges. These are core qualification
pins, not a complete transitive dependency lock. Future environment installation
must satisfy package dependencies (including qwen utility's av/requests/packaging)
and pass `python -m pip check`; the harness records all installed distributions.
No claim is made that stock Colab/Kaggle currently supplies this exact environment.

[PyTorch's official version matrix](https://pytorch.org/get-started/previous-versions/)
offers torch 2.6.0 / torchvision 0.21.0 builds for CUDA 11.8, 12.4 and 12.6.
We select **12.4 only**: an official matched cp311 pair, native SDPA support,
without requiring the newer 12.6 build. CUDA 11.8 is a documentary alternative,
not a fallback in this plan. [NVIDIA compatibility documentation](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)
describes CUDA 12.x driver compatibility and feature limitations; the actual host
driver and working CUDA context must be observed during future smoke. A mismatch
or failure requires review, not an automatic package/CUDA change. Python patch,
package local build suffixes and `torch.version.cuda == 12.4` are exact gates.

## Future owner-run workflow — not executed in PREP

Use a reviewed Linux x86_64 environment with the pins above and exactly one T4
visible. If Kaggle exposes two GPUs, select one using `CUDA_VISIBLE_DEVICES=0`
before starting Python. Neither rented GPUs nor dual-GPU placement qualify this
model. Install dependencies and check the environment while network is allowed;
do not use mutable latest pins. Accept the pinned Qwen Research License obligations.

From the repository root, provision the pinned snapshot in a separate process:

```sh
export HF_HUB_CACHE="$PWD/data/processed/qwen2_5_hf_cache"
python -m pip check
python scripts/provision_qwen2_5_snapshot.py --provision --cache-dir data/processed/qwen2_5_hf_cache --manifest data/processed/qwen2_5_provision_01.json
```

Provisioning restricts files to the exact model repository/revision. The
[authoritative pinned file metadata](https://huggingface.co/api/models/Qwen/Qwen2.5-VL-3B-Instruct/revision/66285546d2b821cf421d4f5eb2576359d3770cd3?blobs=true)
is embedded in the plan. Verification streams all relevant files: SHA-256 for
LFS weights, Git blob SHA-1 for ordinary repository files, plus observed SHA-256
for every file in the output manifest. Both shards and all loader/tokenizer/config
files must match; a directory named with the revision alone is insufficient.
Unexpected files are rejected except `.gitattributes`, which is not loader input.
The manifest records repo/revision, relative snapshot path, file list, byte sizes,
hashes, total bytes and UTC time. Existing manifests are never overwritten.

Then start a new process with offline variables already set:

```sh
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_ENABLE_HF_TRANSFER=0 CUDA_VISIBLE_DEVICES=0
python scripts/provision_qwen2_5_snapshot.py --verify-only --cache-dir data/processed/qwen2_5_hf_cache --manifest data/processed/qwen2_5_verify_01.json
python scripts/w2_qwen2_5_t4_smoke.py --run-id qwen2_5_t4_01 --cache-dir data/processed/qwen2_5_hf_cache
```

The custom cache must match `HF_HUB_CACHE` before process start so snapshot
verification and native loaders use the same cache. Verify-only denies network
and uses local-only snapshot resolution. Smoke requires offline environment flags,
blocks Python socket connection/DNS/datagram paths during loading/calls and keeps
both native factories local-only. It performs no subprocess/network download.
An externally network-disabled runtime is recommended as defense in depth; Python
socket guards are not an operating-system sandbox for arbitrary native extensions.

## Smoke and evidence contract

Exactly two 64x64 in-memory drawings (blue rectangle, green circle) are generated
inside the harness. Both calls are classification-only, with a fixed interface
prompt and `do_sample=false, max_new_tokens=32`. These are smoke settings, not
frozen research decoding/prompt values. No ground truth, hazard content, scoring,
synthetic V1 asset, grounding or InspecSafe data is accessed.

The same runner/model lifecycle serves both requests; fresh inputs and cleared
top-level rope deltas/native cache are checked. No eager retry or OOM fallback.
GPU memory is observational: allocated/reserved before and after load, reset
per-call peak allocated/reserved, GPU name, total VRAM, CUDA version and driver
when available. Every parameter/buffer must be cuda:0 and every parameter FP16;
non-floating/floating buffers need only satisfy placement. Quantization is NONE.

PASS requires exact plan/environment/snapshot, T4, one visible/used GPU, native
vision/language SDPA, exact processor caps, placement, two completed independent
calls, persisted raw bytes with matching hashes, and no runtime/parser exception.
As in the existing Qwen smoke policy, canonical classification INVALID is an
interface observation; no content correctness or accuracy is measured. OOM at
load/input preparation/generate is `RUNTIME_RESOURCE_FAILURE`. Other errors are
`RUNTIME_INTERFACE_FAILURE`; sensitive exception messages are excluded.

Each new run ID exclusively creates a directory below
`data/processed/runtime_validation/w2_qwen2_5_t4_smoke/` containing:

```text
run_metadata.json
environment.json
snapshot_manifest.json
case_01/response.raw
case_01/metadata.json
case_01/result.json
case_02/response.raw
case_02/metadata.json
case_02/result.json
summary.json
summary.json.sha256
```

`FileRawStore` still preserves raw before the adapter; the harness only specializes
its directory mapping to fixed case IDs. Summary hashes cover all preceding
artifacts, with a separate summary hash to avoid self-reference. Failure bundles
retain available evidence and never fabricate absent raw output. Early failures
may lack case artifacts and mark the snapshot unverified. Retrying needs a new
run ID; review failures before planning another run.

## Status and validation

Qwen2.5 offline runner COMPLETE; runtime prep PREPARED_NOT_RUN; real runtime
**NOT_RUN**; **T4_FEASIBILITY_CANDIDATE**, not T4_VALIDATED. Grounding remains
DOCUMENTED_BOX_AND_POINT / NOT_YET_QUALIFIED. Checklist #2 overall PENDING
(InternVL/Moondream implementation remains outstanding), #3–#8 PENDING;
`protocol_freeze_commit_sha: PENDING`; InspecSafe authorization false.

No model/weight download, GPU, Colab/Kaggle runtime, real inference, synthetic gate,
InspecSafe inference, performance scoring, prompt tuning, grounding qualification
or protocol freeze occurred. D5 metrics, canonical contracts/storage, P1 policy,
roster/provenance identity, synthetic assets and historical runtime evidence are
unchanged. D9R1's source allowlist test only adds the two newly authorized scripts;
its historical protected hashes remain fixed. Census stays untracked and untouched.

Offline validation (2026-09-25): **71 runner tests**, **41 PREP tests**, and
**695 full-suite tests PASS**. All three requested `py_compile` checks, the new
manifest's `python -m json.tool` validation and `git diff --check` PASS. Tests use
fake backends and network/import guards; no native ML libraries or GPU are loaded.
An initial fixture byte-count assertion was corrected from 17 to 18; final runs
passed. The existing local test venv is independent of the proposed Linux runtime
pins. No unplanned existing JSON file was modified.

The plan gate hashes canonical JSON (sorted keys, compact separators, UTF-8), so
Windows CRLF conversion cannot invalidate the candidate; changed values still
fail closed. Evidence source hashes separately preserve actual on-disk bytes.
Census SHA-256 remains
`cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`;
it was never staged or committed.

## D9R2B-OBS — Runtime visual-token observability

Base: `801d892ede91c1538f48d002b8704aaeae95ab0c`.
Qwen2.5 T4 observability: **IMPLEMENTED / OFFLINE_TESTED**. Real runtime remains
**PENDING / NOT_RUN**; no actual runtime grid or visual-token count exists yet.
This patch runs no GPU, model inference or snapshot provisioning.

For each case, the harness wraps the existing `runner.prepare_input` once and
reads `PreparedInput.inputs["image_grid_thw"].tolist()`. It accepts exactly one
row of three positive Python integers (bool/float/coercions are rejected) and
stores a fresh nested list, never a tensor or repr. The unchanged runner also
enforces temporal size 1 for the single still image.

Merge size is read independently from
`model.config.vision_config.spatial_merge_size` and
`processor.image_processor.merge_size`. Both must exist, be exact positive ints
and agree. The harness does not hardcode the currently expected value 2.
After checking height and width are divisible by the observed merge size:

```text
observed_visual_token_count = t * (h // spatial_merge_size) * (w // spatial_merge_size)
```

The computed count must be within **256–1280 inclusive**. This is validation of
the existing qualification preprocessing contract, not accuracy scoring. Counts
are derived from prepared grid values, never inferred from min/max pixel caps.

Source reverified: Transformers **4.51.3**, exact commit
`5f4ecf2d9f867a1255131d2461d75793c0cf1db2`:

- [Model grid calculation](https://github.com/huggingface/transformers/blob/5f4ecf2d9f867a1255131d2461d75793c0cf1db2/src/transformers/models/qwen2_5_vl/modeling_qwen2_5_vl.py#L1570)
  reads the model's vision merge size; lines 1632–1636 use `t`, `h // merge`,
  `w // merge`. Source SHA-256:
  `72bdd5615b7527543ea7e6d69fbe194c40bddd94cab13e2e83696ff1cfb10719`.
- [Processor expansion](https://github.com/huggingface/transformers/blob/5f4ecf2d9f867a1255131d2461d75793c0cf1db2/src/transformers/models/qwen2_5_vl/processing_qwen2_5_vl.py#L160)
  repeats the image token by grid product divided by processor merge size squared
  before tokenization. Source SHA-256:
  `95ec1231f8123e6949dd328e3035e104a335a0701488949aec444410071474cd`.
- [Native image-token equality check](https://github.com/huggingface/transformers/blob/5f4ecf2d9f867a1255131d2461d75793c0cf1db2/src/transformers/models/qwen2_5_vl/modeling_qwen2_5_vl.py#L1758)
  requires `input_ids == model.config.image_token_id` count to equal image features.
  Therefore the harness enables the same equality preflight for its single-image,
  fixed-prompt calls: count actual prepared input IDs matching the runtime image
  token ID and require equality with the computed visual-token count. No token ID
  is hardcoded; invalid IDs/input rows and mismatches fail closed before generate.

Each `summary["calls"]` entry now includes `case_id` plus:

```text
observed_image_grid_thw
observed_spatial_merge_size
observed_visual_token_count
observed_image_token_placeholder_count
```

Observations belong to a per-run dictionary keyed by case ID. Unknown/mismatched
case IDs and duplicate prepare attempts fail closed. Each case starts with null
observation fields; valid primitive observations are retained if a later check
fails. A failed second preparation never inherits the first case's values.
Successful cases still perform exactly one preparation and one native generate,
using the same runner lifecycle. Failures stop before generation when possible.
Observation contract failures are `RUNTIME_INTERFACE_FAILURE`; genuine CUDA OOM
retains the existing `RUNTIME_RESOURCE_FAILURE` classification.

Runner raw v2, raw-before-parser, FileRawStore, rope/cache resets, placement,
memory instrumentation, network firewall and snapshot verification are unchanged.
Model/revision, SDPA, FP16/NONE/batch 1, single T4, preprocessing caps and all ten
software pins remain unchanged. No full transitive lock was introduced.
The plan file is untouched; canonical PLAN_SHA256 before and after is:
`aa4fcff85d670d844025a540d85f10514919c60f6709de8be8f6be0922fd63fb`.

T4 status remains **T4_FEASIBILITY_CANDIDATE**. Grounding remains unqualified,
InspecSafe authorization false, checklist #2–#8 PENDING and protocol freeze SHA
PENDING. No weights download, snapshot provisioning, Colab/Kaggle runtime, real
inference, synthetic gate, InspecSafe, prompt tuning or scoring occurred.

OBS offline validation: **58 PREP tests PASS** (17 added), **71 runner tests PASS**,
**712 full-suite tests PASS**. Smoke harness `py_compile`, unchanged plan JSON
validation and `git diff --check` PASS. Fake tests exercise distinct per-case grids,
exactly two prepares/native generates, no carryover on second-case failure, runtime
merge values other than 2, malformed/bool/non-divisible inputs, both cap boundaries,
placeholder mismatches and CUDA OOM classification. No network in tests.
Census remains untracked/untouched with SHA-256
`cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`.
