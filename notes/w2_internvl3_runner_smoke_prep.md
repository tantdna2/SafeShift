# D9R4 — InternVL3 runner and single-T4 smoke PREP

Task: `W2.6-D9R4-INTERNVL3-RUNNER-SMOKE-PREP`, 2026-09-28.
Base main: `582bc1f6d15fa29dd93cd21a43fb7f8cfaa771c2`.
Model: `OpenGVLab/InternVL3-2B-hf`.
Immutable revision: `cb57a075cb75a2e6d1b668b128d48bb00ae321d2`.

**NO REAL RUNTIME EXECUTION.** Implementation and fake/static verification only.
No weights downloaded, GPU/model execution, external gate, InspecSafe, D5 change,
protocol freeze, final role assignment, backup activation or merge.
The untracked local census manifest is untouched and excluded from this PR.

## Current status and evidence boundary

Offline runner COMPLETE / OFFLINE_TESTED. Real runtime PENDING / NOT_RUN;
resource `T4_FEASIBILITY_CANDIDATE`; classification `CANDIDATE`;
grounding `NOT_YET_DOCUMENTARILY_QUALIFIED`. Production adapter `NOT_QUALIFIED`:
classification INVALID and grounding UNSUPPORTED, regardless of generated text.
Checklist #2 remains PENDING overall until runtime qualification; #3–#8 remain
PENDING. `protocol_freeze_commit_sha=PENDING`, `inspecsafe_inference_authorized=false`.

This is the current InternVL overlay on the historical
[D9R3 reconciliation](w2_d9_freeze_readiness_reconciliation.md). That note,
documentary provenance snapshot, historical runner/result artifacts and freeze
template keep their recorded milestone meanings. Only the current roster entry
and task overlay are updated. No new qualification status enum is introduced.

## Exact-revision source/API audit

The [source manifest](../configs/pre_freeze/internvl3_source_audit.v1.json) records
request URLs, UTC retrieval times, response byte sizes and SHA256, including the
immutable Hub revision API. Only small card/config/source/metadata responses were
fetched. No remote source was imported or executed. Large tokenizer and checkpoint
bodies were not fetched. Source copies used for local review stay ignored under
`data/processed/internvl3_audit/`; the compact manifest is version controlled.

The [exact config](https://huggingface.co/OpenGVLab/InternVL3-2B-hf/blob/cb57a075cb75a2e6d1b668b128d48bb00ae321d2/config.json)
declares `model_type=internvl`, architecture `InternVLForConditionalGeneration`,
Qwen2 text backbone, 448×448 vision input, patch size 14, downsample ratio 0.5,
image sequence length 256 and image token ID 151667. The config and tokenizer
config have no `auto_map` remote-code requirement; the exact inventory contains
no Python model files. `trust_remote_code=False` is explicit for both loaders.

The [exact model card](https://huggingface.co/OpenGVLab/InternVL3-2B-hf/blob/cb57a075cb75a2e6d1b668b128d48bb00ae321d2/README.md)
documents `AutoProcessor`, `AutoModelForImageTextToText`, chat templating, native
`generate`, and decoding the continuation after the input prefix. The audited
Transformers 4.52.4 auto mapping maps InternVL to the concrete
`InternVLForConditionalGeneration` class used here. This is a native Transformers
path, with no separate code revision or runtime source download.

Transformers tag 4.52.4 resolves through tag object
`a1715ed33a419b2a7f2b6a10fa6836c029824223` to commit
`51f94ea06d19a6308c61bbb4dc97c40aabd12bad`. Relevant immutable source:

- [InternVL model](https://github.com/huggingface/transformers/blob/51f94ea06d19a6308c61bbb4dc97c40aabd12bad/src/transformers/models/internvl/modeling_internvl.py):
  native vision/projector/Qwen2 forward and GenerationMixin; checkpoint conversion
  mapping for the older `language_model.model`, vision/projector and LM-head keys.
- [InternVL processor](https://github.com/huggingface/transformers/blob/51f94ea06d19a6308c61bbb4dc97c40aabd12bad/src/transformers/models/internvl/processing_internvl.py):
  chat/PIL processing and media placeholder expansion. It also loads the native
  video processor; AutoVideoProcessor resolves InternVL by model config and its
  loader supports the old `preprocessor_config.json` filename. Smoke uses no video.
- [GotOcr2 fast image processor](https://github.com/huggingface/transformers/blob/51f94ea06d19a6308c61bbb4dc97c40aabd12bad/src/transformers/models/got_ocr2/image_processing_got_ocr2_fast.py):
  aspect-ratio grid, tiles and optional thumbnail, resize/rescale/normalization.
- [Native dtype loader](https://github.com/huggingface/transformers/blob/51f94ea06d19a6308c61bbb4dc97c40aabd12bad/src/transformers/modeling_utils.py):
  `_get_torch_dtype` propagates explicit `torch.float16` to component configs.
  Both model components support SDPA; no BF16-only guard is imposed by this path.
- [Generation implementation](https://github.com/huggingface/transformers/blob/51f94ea06d19a6308c61bbb4dc97c40aabd12bad/src/transformers/generation/utils.py):
  greedy decoding, output controls and a new DynamicCache per call.
- [Qwen2 state](https://github.com/huggingface/transformers/blob/51f94ea06d19a6308c61bbb4dc97c40aabd12bad/src/transformers/models/qwen2/modeling_qwen2.py)
  and [dynamic RoPE helper](https://github.com/huggingface/transformers/blob/51f94ea06d19a6308c61bbb4dc97c40aabd12bad/src/transformers/modeling_rope_utils.py):
  cached RoPE frequencies grow only beyond 32768 positions for this checkpoint.

The published weight dtype and 2B card examples are BF16. The card's FP16 video
example is quantized **8B**, so it is not evidence that this 2B FP16 runtime passes.
Here FP16 is the explicit native loader path already allowed as a D9R1 candidate,
not a precision fallback. Numerical behavior, finite outputs and memory fit still
require the separately audited real smoke. Do not turn a failure into BF16,
quantization, CPU/disk inference, another model or another revision.

### Actual preprocessing and generation

`AutoProcessor.from_pretrained(verified_local_snapshot, revision=PIN,
local_files_only=True, trust_remote_code=False, use_fast=True)` loads
InternVLProcessor + GotOcr2ImageProcessorFast + Qwen2 tokenizer.

The exact image config says `crop_to_patches=false`, but InternVLProcessor's
image kwargs default to **true**. Runner makes that effective behavior explicit:
RGB conversion, dynamic aspect-ratio grid with 1–12 tiles of 448×448, plus one
thumbnail when the grid has more than one tile (therefore up to **13** patches).
Bicubic resize; scale 1/255; mean `[0.485,0.456,0.406]`, std
`[0.229,0.224,0.225]`. No manual crop coordinate or spatial-output conversion.

One fresh user message contains one image marker and one text prompt.
`apply_chat_template(..., tokenize=False, add_generation_prompt=True)` formats it;
`processor(text=[text], images=[local_rgb_pil], return_tensors="pt",
crop_to_patches=True, min_patches=1, max_patches=12)` does token/image processing.
This avoids URL/path media loaders. `BatchFeature.to("cuda:0", dtype=torch.float16)`
casts floating pixels and moves all tensors, retaining integer input IDs/mask.
CPU image preprocessing/deserialization is allowed; **CPU inference is not**.

The processor surrounds `256 × actual_patch_count` `<IMG_CONTEXT>` tokens with
image delimiters. Runner verifies pixel shape `[patches,3,448,448]`, actual token
expansion, batch 1, integer IDs/mask, FP16 pixels and cuda:0 for every input.
The native vision path drops CLS then downsamples 32×32 features to 16×16 = 256
features per tile. Inputs are capped at 4096 tokens for this smoke condition.

Model loading uses concrete native `InternVLForConditionalGeneration`, explicit
FP16, `use_safetensors=True`, SDPA and offline local snapshot. CPU deserialization
is followed by a complete `.to("cuda:0")` and `.eval()` before any forward.
No automatic device map or Accelerate/offload hooks are used; runtime audits
reject other devices, non-FP16 parameters, quantization and offloaded caches.
Native `output_loading_info=True` must report no missing, unexpected or mismatched
weight keys or load errors; partially/randomly initialized models cannot pass smoke.

Generation calls `model.generate(**inputs, generation_config=deepcopy(checkpoint_config),
**smoke_decoding)`. Audited supported controls selected for PREP: greedy
`do_sample=false`, 32 max new tokens, one beam/return sequence, cache enabled with
`cache_implementation=dynamic`, tensor return, scores/logits/attentions/hidden-state
returns disabled. These are qualification settings, not research decoding freeze.
Unselected sampling/thinking controls are rejected, not guessed or inherited from
another family. Decode via `processor.decode(continuation_ids, skip_special_tokens=...,
clean_up_tokenization_spaces=False)` both with and without special tokens.

### Grounding evidence

Neither exact card/config nor the audited native implementation provides a generic
box/point API with documented output grammar, coordinate frame, units or validity
rules. Tokenizer contains `<box>`, `<quad>` and `<ref>` tokens; their existence is
not an output contract. The processor docstring includes inherited OCR-oriented
wording about boxes; this is not a box-returning InternVL inference API.
Family benchmark/GUI/3D claims are not promoted to exact-checkpoint qualification.

Grounding therefore stays **NOT_YET_DOCUMENTARILY_QUALIFIED**. No spatial adapter,
point-to-box conversion, coordinate prompt trick or full external gate harness is
implemented. Pending grounding adapter always returns UNSUPPORTED with no canonical
coordinates; pending classification always returns INVALID with no canonical label.

## Software and single-T4 contract

[Requirements](../requirements-internvl3-t4.txt) pin the full existing D9/Moondream
Linux dependency closure, plus the official matching torchvision build from the
Qwen2.5 environment. No global package update. Native fast image processing needs
torchvision; Qwen-specific vision utilities and Moondream remote packages are unused.

| Component | Exact candidate | Reason/evidence |
|---|---|---|
| Python | 3.11.11 | Existing D9/T4 interpreter pin |
| torch / CUDA | 2.6.0+cu124 / 12.4 | Existing D9 pin and official torch/vision pair |
| torchvision | 0.21.0+cu124 | Existing Qwen2.5 pin; native fast image processor requires it |
| transformers | 4.52.4 | Existing Moondream pin; native InternVL source audited at immutable commit above; checkpoint config records 4.52.0.dev0, so Qwen2.5's 4.51.3 environment is not reused wholesale |
| tokenizers | 0.21.2 | Existing Moondream pin, meets Transformers >=0.21,<0.22 |
| pillow | 11.2.1 | Existing D9 pin, meets >=10.0.1,<=15.0 |
| huggingface-hub | 0.30.2 | Existing D9 pin, meets >=0.30.0,<1.0 |
| safetensors | 0.5.3 | Existing D9 pin, meets >=0.4.3 |
| numpy | 1.26.4 | Existing Moondream pin; processor requirement |

Compatibility evidence: immutable `dependency_versions_table.py` and
[4.52.4 package metadata](https://pypi.org/pypi/transformers/4.52.4/json), recorded in
source manifest; [Qwen2.5 environment evidence](w2_qwen2_5_t4_runtime_prep.md),
and existing `requirements-moondream-t4.txt`. Runtime checks every pinned
distribution, Python patch, CUDA build and audited Transformers source hashes.
Full actual distribution inventory is recorded for review. Installing/resolving
these pins in a fresh Linux venue is a future step; no GPU stack was installed here.

Exactly one process-visible NVIDIA/Tesla T4; compute capability 7.5; total VRAM
14–16 GiB; cuda:0; FP16 parameters/pixels; NONE quantization; batch 1. Registered
buffers must also be on cuda:0 (native FP32 rotary calculations/buffers are not
automatic parameter-precision fallback). No CPU/disk inference offload, precision
fallback, quantization fallback, attention fallback or model substitution.

Reuse the already documented [Qwen2.5 single-T4 process-mask policy](w2_qwen2_5_t4_runtime_prep.md#future-owner-run-workflow--not-executed-in-prep):
on a Kaggle T4×2 host, `CUDA_VISIBLE_DEVICES=0` must precede Python; PyTorch must
report exactly one visible T4. This is not Qwen3's dual-GPU placement exception.

## Snapshot contract

[Runtime plan](../configs/pre_freeze/internvl3_t4_runtime.v1.json) pins all 14 files
from the immutable Hub API: LFS SHA256/size for weights and tokenizer; Git blob
SHA1/size for regular files. The checkpoint is 4,178,013,768 bytes with published
SHA256 `8e2c302719a13916a4d276e60fad4fb1c92a57b39dd2ad51af5a63dcf7a16f4a`.
This agrees with existing D9R1 provenance. No hash is inferred from a filename or
fabricated. **Local checkpoint bytes have not been verified in this PR.**

The provisioner only downloads in explicit `--provision` mode, exact ID/SHA,
allowlisted inventory, dedicated repo-relative cache. Nonempty caches, including
interrupted provisions, are refused; no repair/overwrite/revision fallback. Use a
fresh cache path after review. `--verify-only` uses filesystem hashing with socket
denial, no Hub import/download. Runner re-verifies all files before processor/model
load, rejects missing/extra files and revision-directory mismatch. Normal HF blob
symlinks inside the model cache are allowed; escaping aliases are rejected.

Actual provision later records SHA256 of every local file, sizes, timestamp,
model/revision and plan hash. For regular files these local SHA256 values supplement
the authoritative Git blob hashes. There is no runtime provision path.

## Offline lifecycle, raw evidence and state

Network denial is entered before backend/source import, retained through the runner
lifecycle, and combined with offline environment flags, local-files-only loaders
and venue Internet OFF. Socket denial protects Python/HF networking; it is not an
OS firewall for arbitrary native processes. The owner must disable venue Internet;
CLI requires explicit attestation and records it, without claiming it independently
proves host firewall state. Native transfer/Xet downloads are disabled.

Lifecycle: NEW → INITIALIZED → LOADED → READY → GENERATED, then READY for the next
independent call. Any failure is terminal FAILED; no retry/reload/fallback in that
lifecycle. `close()` releases resources and the network guard, ending it as CLOSED.
Repeated executor initialize/load methods are idempotent; native model load count
must be one. Each call gets a fresh message, prepared input and generation config.
DynamicCache is per call; no model-attached cache is allowed. RoPE cache length,
frequency hash/scaling, model/generation config hashes and device/dtype placement
must remain stable. 4096 input + 32 generated tokens stays below the checkpoint's
32768 RoPE growth threshold. This observes stability without an invented reset path.

Native output envelope contains full generated IDs (including prefix), continuation,
both native decodes, model/revision, run/call IDs, decoding and input boundaries.
`execute_call` stores it with prompt, sample/input IDs and hashes, environment,
Git commit, command, source kind and adapter versions. `VerifiedRawStore` exclusively
writes and fsyncs raw/provenance, re-reads persisted bytes, verifies SHA256, byte size
and metadata **before returning to the executor for adapter dispatch**. Corruption
blocks adaptation. Decode/state failures after generation preserve captured token
IDs as partial raw evidence; blocking generation/OOM before return cannot promise
partial tokens. No output is turned into a coordinate or qualified label.

Failure evidence includes stage, type, message and cause chain, separating actual
CUDA OutOfMemoryError from interface failure; no message-based OOM guessing.
Evidence is local and may contain exception details; review before sharing. Counters
are attempted native loads/calls, including failed attempts, and survive failures.

## Future real smoke runbook — after Research Lead audit only

Use a clean checkout of the **exact reviewed execution commit**, in Linux x86_64
with CPython 3.11.11. Do not execute this runbook as part of PREP. Resolve license
obligations first: project MIT plus Qwen component obligations, not MIT-only.
Use a fresh dedicated environment and install while networking is enabled:

```sh
python -m pip install -r requirements-internvl3-t4.txt
python -m pip check
python scripts/provision_internvl3_snapshot.py --provision --cache-dir data/processed/internvl3_hf_cache --manifest data/processed/internvl3_provision_01.json
```

Provisioning is a separate process. Preserve its manifest. Then disable Internet
in the venue UI/container, before starting the runtime process. Set these variables
before Python/importing torch or HF libraries (restart any existing notebook kernel):

```sh
export CUDA_VISIBLE_DEVICES=0
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_ENABLE_HF_TRANSFER=0 HF_HUB_DISABLE_XET=1
python scripts/provision_internvl3_snapshot.py --verify-only --cache-dir data/processed/internvl3_hf_cache --manifest data/processed/internvl3_verify_01.json
python scripts/w2_internvl3_t4_smoke.py --run-id internvl3-t4-smoke-UNIQUE --expected-commit AUDITED_40_HEX_EXECUTION_SHA --cache-dir data/processed/internvl3_hf_cache --venue-internet-off
```

Replace the two uppercase placeholders explicitly; do not derive expected commit
from whatever checkout happens to be present. The harness requires exact HEAD and
clean tracked/untracked checkout. Ignored cache/artifacts are permitted. No input
dataset/image path is accepted: the harness generates one blue square drawing and
one green ellipse drawing locally, with differing aspect ratios. Exactly two
native calls audit independent preprocessing/state on one loaded model.

Artifacts stay under
`data/processed/runtime_validation/w2_internvl3_t4_smoke/<run_id>/`:

- `run_metadata.json`: Git/command/plan/source hashes, precision, preprocessing,
  decoding, timestamps, venue attestation.
- `environment.json`: exact software and full distribution inventory, visible T4,
  CC/VRAM/CUDA build, mask and offline variables.
- `snapshot_manifest.json`: independently verified local snapshot bytes.
- `case_01.png`, `case_02.png`: local generated fixtures; hashed per input.
- Hashed call directories: `response.raw`, pre-adapter `metadata.json`, `result.json`.
- `summary.json`, `summary.sha256.json`: counts, CUDA allocated/reserved and peaks
  (peaks include loading and both calls), state audits, raw references/hash/size,
  artifact inventory, and stage/type/message/causes on failure.

The output root and each raw attempt are exclusive; a run ID cannot overwrite an
earlier attempt. Failure writes available evidence and returns nonzero. Stop for
review on any OOM, mismatch, drift or interface error; do not repair this runtime
by changing pins/precision/offload/revision or by activating a backup.

`RUNTIME_INTERFACE_PASS` would mean only that load, native preprocessing and two
generation calls returned/persisted under this resource contract. INVALID pending
classification adaptation is expected. It is not accuracy, spatial/grounding PASS,
external gate PASS, final role assignment, production readiness or protocol freeze.

## Validation

Fake/static focused and D9 regression commands (no GPU or real model):

```powershell
.venv/Scripts/python.exe -m unittest tests.test_internvl3_prep -q
.venv/Scripts/python.exe -m unittest tests.test_d9_t4_roster_revision tests.test_model_provenance tests.test_qwen2_5_runner tests.test_qwen2_5_t4_runtime_prep tests.test_qwen3_external_gate_result tests.test_qwen2_5_external_gate_result tests.test_moondream_prep_audit -q
.venv/Scripts/python.exe -c "import json,pathlib; p=list(pathlib.Path('configs/pre_freeze').glob('*.json')); [json.loads(x.read_text(encoding='utf-8')) for x in p]; print('JSON parse PASS:',len(p))"
git diff --check
```

Checks cover exact model/revision, software/source pins, socket denial, single-T4
metadata gates, FP16/NONE/no-offload/no-fallback, snapshot hashes/inventory,
state transitions/drift, load/call counts, raw-before-adapter order and corrupt
persisted bytes, failure stages/causes/OOM, pending adapters/no coordinates,
synthetic-only input and existing roster/history. **30/30 focused tests PASS;
219/219 related D9 regressions PASS (249 total)** on Windows / Python 3.11.9.
All **24/24 pre_freeze JSON files parse**; `git diff --check` PASS. Seven retrieved
small model files also match the immutable API's Git blob hashes/sizes.
Full repository suite was not run because this change is confined to InternVL PREP;
fresh Linux environment install, snapshot provision and real runtime remain unrun
as explicitly required. Fake smoke PASS values are test assertions, not results.

Outstanding execution prerequisites: Research Lead review, fresh compatible Linux
environment and verified local checkpoint provision, then separate real single-T4
smoke. Spatial documentary eligibility and production parser qualification remain
unresolved. No evidence justifies a STOP-condition model/revision/policy change.
