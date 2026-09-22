# W2.6B0 — Model Provenance & Runner Specification

Base main: `73fd0b3d112464755fe8c473db107bfff8e1e642` (PR #21 merged).
Branch: `implementation/d9-model-provenance-spec`. Documentary audit: **2026-09-22 UTC**.
Authority: Project Owner's W2.6B0 request under the unchanged D9 roster.
**No model execution. `protocol_freeze_commit_sha: PENDING`.**

The machine-readable record is
[local_model_provenance.d9.json](../configs/pre_freeze/local_model_provenance.d9.json).
Its `sources` dictionary resolves every section's `evidence` identifiers. Evidence
applies to the fields in that section; statements of absence are limited to the
reviewed sources. The requirements below are SafeShift engineering requirements,
not claims that a backend has already passed validation.

## Documentary completion versus freeze

D9 checklist **#1 COMPLETE**: all four primary candidates and both ordered backups
have exact D9 IDs, full repository commit SHAs, UTC access times, official revision
verification, separate license/access/caveat records and published weight-file
metadata. Completion records provenance, including unresolved usage/access caveats;
it does **not** certify Project Owner access, clear every training dataset's rights,
verify downloaded weight bytes, or qualify any capability.

Checklist **#2–#8 remain PENDING**. In particular, W2.6A scaffolding and these
documentary specifications are not real runner validation. `VERIFIED_DOCUMENTARY`
is not `PROTOCOL_FROZEN`. Existing `frozen_components` entries remain `PENDING`:
they describe the eventual approved protocol, while the new provenance reference
records today's evidence. Decoding, preprocessing, precision, adapters, environment,
final roles and protocol freeze remain separate approvals/validation milestones.

## Repository and weight provenance

| D9 position / exact model ID | Immutable Hugging Face revision | API verification UTC | Published weight files |
|---|---|---|---|
| Primary 1: `Qwen/Qwen3-VL-8B-Instruct` | `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` | 2026-09-22T03:05:39.422487+00:00 | 4 safetensors shards |
| Primary 2: `AIDC-AI/Ovis2.5-9B` | `d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd` | 2026-09-22T03:05:39.787159+00:00 | 4 safetensors shards |
| Primary 3: `allenai/Molmo2-O-7B` | `784410650d12be9bc086118fdefa32d2c3bced86` | 2026-09-22T03:05:38.979890+00:00 | 7 safetensors shards |
| Primary 4: `google/gemma-4-12B-it` | `707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7` | 2026-09-22T03:05:38.980891+00:00 | 1 safetensors file |
| Backup 1: `google/paligemma2-10b-mix-448` | `b26d16fb4251090ba4a4aa5af9fca1f8248ed5b6` | 2026-09-22T03:05:39.595255+00:00 | 4 safetensors shards |
| Backup 2: `openbmb/MiniCPM-V-4.6` | `36f34a661a4bd35d0dc2294cb044d2584646c7d3` | 2026-09-22T03:05:39.064891+00:00 | 1 safetensors file |

Method: unauthenticated HTTPS GET `https://huggingface.co/api/models/{model_id}`,
read `sha`, then GET `https://huggingface.co/api/models/{model_id}/revision/{sha}?blobs=true`
and require the returned SHA to match. The JSON records both API evidence URLs,
returned repository ID, access timestamps, response SHA-256 fingerprints, and
each weight file's relative name, byte size and published LFS SHA-256. These hashes
are **server metadata**, not locally verified weight checksums. No weight endpoint
was requested. Small README/config/source files were read at the recorded revisions;
no downloaded Python source was imported or executed.

Ovis's requested D9 ID redirects to `ATH-MaaS/Ovis2.5-9B`. Both API requests resolve
to that repository and the same SHA. Preserve `model_id=AIDC-AI/Ovis2.5-9B`, record
`resolved_repository_id` separately, and require the future loader to check the
redirect/revision. This is an observed repository move, not a roster substitution.
Evidence: `ovis2_5_9b.api` and `ovis2_5_9b.revision_api`.

## License and access findings

| Model | Repository license / gate | Separate model-card conditions and open issues |
|---|---|---|
| Qwen | Apache-2.0; ungated | No additional use restriction or training-data license warning identified in the reviewed exact card. This does not establish clearance for all upstream data. |
| Ovis | Apache-2.0; ungated | Card's disclaimer does not guarantee absence of copyright issues or improper content despite compliance checks. |
| Molmo | Apache-2.0; ungated | Card specifies research/education and Ai2 Responsible Use Guidelines. Third-party training data have academic/non-commercial research conditions. Retain this caveat; use-case review remains unresolved. |
| Gemma 4 12B | Apache-2.0; ungated | Exact card links the Gemma 4 Apache license, discusses intended uses, bias, accuracy, misuse and privacy risks. Do not inherit older Gemma gated terms. |
| PaliGemma2 | `gemma`; gated (`manual` in API) | Google usage terms require acceptance. Exact card also describes this BF16 release as for research purposes. Record both; do not relabel Apache-2.0 or infer unrestricted use. |
| MiniCPM-V 4.6 | Apache-2.0; ungated | Exact card applies Apache to weights/code and includes misuse/security/liability and generated-content disclaimers. |

These entries are documentary findings from each pinned README and API (the JSON
contains the exact links), including the
[Molmo license/use section](https://huggingface.co/allenai/Molmo2-O-7B/blob/784410650d12be9bc086118fdefa32d2c3bced86/README.md#license-and-use),
[PaliGemma2 card](https://huggingface.co/google/paligemma2-10b-mix-448/blob/b26d16fb4251090ba4a4aa5af9fca1f8248ed5b6/README.md),
[Gemma terms](https://ai.google.dev/gemma/terms) and
[Gemma 4 license](https://ai.google.dev/gemma/docs/gemma_4_license).

PaliGemma2 is **ACCESS_REQUIRES_USER_ACCEPTANCE**. Project Owner acceptance is
`NOT_VERIFIED`; no account credentials were inspected and no terms accepted on
their behalf. Unauthenticated raw README/config requests returned HTTP 401. Public
revision metadata and the public rendered README at the immutable revision provide
documentary evidence. The latter's recorded content hash fingerprints HTML, not
the raw Markdown. Lack of accepted access is an execution prerequisite, not a
model failure and not authorization to activate a backup. API `manual` and the
gate text's immediate-processing statement describe different parts of the access
process; no owner-specific access conclusion follows from either.

## Official runtime path (not installed or validated)

All six specifications use the documented PyTorch/Transformers path. Model,
processor, tokenizer and any remote code must load from the recorded model revision;
future code must not fall back to a mutable alias or another repository. Remote-code
files need pinned review before execution. Runtime versions must be resolved per
model; Ovis's 4.51.3 recipe is not assumed compatible with the newer native models.

| Model | Loading classes | Remote code | Documented dtype/device | Input → generation |
|---|---|---|---|---|
| Qwen | `Qwen3VLForConditionalGeneration`; `AutoProcessor` → `Qwen3VLProcessor` | No | `dtype="auto"`; optional BF16; `device_map="auto"` | `processor.apply_chat_template` → `model.generate` |
| Ovis | `AutoModelForCausalLM` → `Ovis2_5`; model-owned text/visual tokenizers | **Yes** | BF16 and `.cuda()`; multi-device mapping not established for this wrapper | `model.preprocess_inputs` → custom `model.generate` |
| Molmo | `AutoModelForImageTextToText` → `Molmo2ForConditionalGeneration`; `AutoProcessor` → `Molmo2Processor` | **Yes** | `dtype="auto"`; published F32/config float32; `device_map="auto"` | `processor.apply_chat_template` → `model.generate` |
| Gemma 4 | `AutoModelForMultimodalLM` → **`Gemma4UnifiedForConditionalGeneration`**; `Gemma4UnifiedProcessor` | No | `dtype="auto"`; BF16 config; `device_map="auto"` | `apply_chat_template` → `generate`; response parsing belongs after preservation |
| PaliGemma2 | `PaliGemmaForConditionalGeneration`; `PaliGemmaProcessor` | No | BF16; `device_map="auto"` | `processor(text=..., images=...)` → `generate` |
| MiniCPM-V 4.6 | `AutoModelForImageTextToText` → `MiniCPMV4_6ForConditionalGeneration`; `AutoProcessor` | No | `torch_dtype="auto"`; optional BF16; `device_map="auto"` | `apply_chat_template` → `generate`, with matching `downsample_mode` |

Official package guidance, inventoried rather than installed:

- Qwen card recommends source Transformers and mentions then-unreleased 4.57.0.
  That historical comment is not a present-day minimum-version assertion.
  Flash Attention 2 is optional. Exact runner environment remains pending.
- Ovis card: torch 2.4.0, Transformers 4.51.3, NumPy 1.25.0, Pillow 10.3.0,
  moviepy 1.0.3 and flash-attn 2.7.0.post2. Preserve this recipe as evidence;
  an image-only dependency subset and platform compatibility need future validation.
- Molmo: Python 3.11, Transformers 4.57.1, torch, Pillow, einops, torchvision,
  accelerate; full video recipe adds decord2 and molmo_utils.
- Gemma: current Transformers, torch, torchvision and accelerate per image recipe;
  config reports `5.10.0.dev0`, which is not a proven minimum version.
- PaliGemma2: native PaliGemma 2 support, torch and auto device mapping;
  exact card does not specify a minimum Transformers version.
- MiniCPM: `transformers[torch]>=5.7.0`, torchvision; torchcodec for video with
  documented CUDA compatibility caveats and an `av` alternative. Do not reuse
  a prior MiniCPM model's `trust_remote_code=True` / `model.chat` interface.

Sources: the six pinned README/config evidence sets; `hf_gemma_unified` and
`hf_pali`. No family-only runtime claim is promoted to exact-checkpoint validation.

## Spatial interface inventory

| Model | Documentary class | Native representation and coordinates | D5 box status |
|---|---|---|---|
| Qwen | `UNCERTAIN_REQUIRES_EXTERNAL_GATE` | Exact 8B card claims spatial grounding; full grammar not established. Family cookbook uses a different checkpoint and has a bbox ordering conflict below. | `NOT_YET_QUALIFIED` |
| Ovis | `DOCUMENTED_BOX_AND_POINT` | `<point>(x,y)</point>`; `<box>(x1,y1),(x2,y2)</box>`; `[0,1)`, top-left origin, top-left then bottom-right box corners. Lists allowed. | `NOT_YET_QUALIFIED` |
| Molmo | `DOCUMENTED_NATIVE_POINT` | Card shows `<points>` / `<tracks>` with `coords`, image/frame and point IDs, x/y scaled by 1000. No documented generic box. | `NOT_YET_QUALIFIED` |
| Gemma 4 | `UNCERTAIN_REQUIRES_EXTERNAL_GATE` | Card makes broad object detection/pointing claims but no exact generic bbox grammar, scale, origin or ordering was identified. | `NOT_YET_QUALIFIED` |
| PaliGemma2 | `DOCUMENTED_NATIVE_BOX` | Location tokens `<loc0000>`…`<loc1023>`, 1024 discrete bins. Reference encoder uses y-min, x-min, y-max, x-max. | `NOT_YET_QUALIFIED` |
| MiniCPM | `NO_DOCUMENTED_GENERIC_SPATIAL_INTERFACE` | Exact card/config reviewed do not specify generic box/point grammar or coordinate convention. Benchmark mentions do not establish a contract. | `NOT_YET_QUALIFIED` |

The [Ovis pinned README](https://huggingface.co/AIDC-AI/Ovis2.5-9B/blob/d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd/README.md)
directly confirms the requested point/box syntax, scale and origin. Its sample
prompt suffixes and `<ref>` usage are documentation evidence only: this task adds
no new SafeShift prompt, thinking suffix or semantic task text.

**Qwen exact interface and source conflict: UNRESOLVED.** The
[official cookbook at commit 96588727e44c78b25ba03ea03b8e12f7e64fd0da](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/cookbooks/2d_grounding.ipynb),
examples call `qwen3-vl-235b-a22b-instruct`, not this roster's exact 8B checkpoint.
They document family-reference JSON `bbox_2d` / `point_2d`, relative `[0,1000]`
coordinates and point `[x,y]`; these are not asserted as the exact 8B interface.
Additionally, `plot_bounding_boxes`'s docstring describes y-first, whereas its
indexing and explicit JSON example use x-first. Both are recorded without choosing
one. Top-left origin is an inference scoped to that plotting code. Its coordinate
sorting and malformed-JSON repair helpers must not enter SafeShift's strict parser.
The exact card's broad spatial-grounding claim does not establish that entire
grammar. The D9 roster policy remains unchanged; exact serialization and adapter
qualification stay open.

Molmo's card extraction scales integer x/y values by 1000 and accepts image-bounded
points. Image/frame-indexed examples do not establish every single-image spelling;
the origin inference and remaining serialization question are explicit in JSON.
Native points remain raw evidence. No point-to-box conversion, point-only D5 track,
grounding score, capability PASS/FAIL or final role is created.

PaliGemma2's exact card explicitly supports box output. The reference
[tokenizer documentation](https://github.com/google-research/big_vision/blob/main/big_vision/configs/proj/paligemma/README.md)
and [processor source](https://github.com/huggingface/transformers/blob/v4.57.1/src/transformers/models/paligemma/processing_paligemma.py)
define the location tokens. The reviewed
[segmentation encoder](https://github.com/google-research/big_vision/blob/main/big_vision/pp/proj/paligemma/segmentation.py)
uses `round(bbox*1023)` and y-first image slicing; this is specifically reference
segmentation evidence. Exact mix-checkpoint detection dequantization/serialization
still needs qualification. No universal divide-by-1000/1024 adapter is invented.

## Classification integration and raw preservation

For every primary, the future runner must implement:

```text
image + frozen prompt
  -> native model input
  -> native generated raw output
  -> W2.6A raw preservation
  -> model-specific adapter
  -> existing canonical SafeShift schema
```

The caller supplies the independently constructed C1/A2 request after Benchmark
Firewall checks. A model-specific adapter ends at
`safeshift.protocol.schema.parse_text(text, "classification")` and the existing
`Classification(safety_level)` / `schemas/canonical.schema.json`. No schema or
label change, semantic repair, output-driven prompt choice, or new prompt is made.

| Primary | Native output to preserve | Post-preservation extraction contract |
|---|---|---|
| Qwen | Returned token IDs, input token length and uncleaned decoded text | Continuation after input length; `processor.batch_decode`, no whitespace cleanup; parser sees classification text. |
| Ovis | Every returned ID and decoded output, including two-phase thinking/budget output if enabled | Decode with `model.text_tokenizer`; custom inputs-embeds generation returns generated IDs, so do not apply Qwen's input-length subtraction. Thinking/final-answer extraction must be qualified separately. |
| Molmo | Full IDs, input length and full decoded output, including any point/track text | Continuation after input length; `processor.tokenizer.decode`; then classification parser. Point data do not become boxes. |
| Gemma 4 | Full IDs, input prefix/length, decode with `skip_special_tokens=False`, including control/thinking channels | After persistence, `processor.parse_response(response, prefix=input_ids)` may select final answer text for the canonical parser. Channel selection remains unqualified. |

All raw envelopes must have a versioned, lossless serialization of exposed token
IDs and text; retain special/control tokens before any cleanup. Preserve any
backend-provided native text bytes as well. Decoding for lossless serialization
is distinct from answer extraction or schema parsing. Record generated versus
backend-inserted content when distinguishable, especially Ovis budget messages;
do not label an inserted budget string as sampled output. For PaliGemma and
MiniCPM, prospective extraction is also documented in JSON, without activation.

Use existing `execute_call` and `FileRawStore`. Raw bytes **and** metadata must be
durable before adapter invocation; any storage failure stops parsing. Each attempt
gets a new call ID. Run records must include the immutable model/code revision,
prompt ID/text/hash, sample/input/run IDs, processor and generation configuration,
precision/quantization, device, library/driver versions, seed controls, Git commit,
command, timestamp and artifact-relative paths. Save final errors/results separately
without rewriting raw evidence. Do not put credentials or personal absolute paths
in manifests.

## Decoding support inventory — not a policy

Every model has `SUPPORTED_DECODING_INVENTORY` with an empty
`selected_parameters` object and `policy_status=PENDING`. Transformers documents
`temperature`, `do_sample`, `top_p`, `top_k`, `max_new_tokens` and
`repetition_penalty`; the exact card/config or forwarding source is linked per
model. Ovis forwards these to `self.llm.generate` under its documented 4.51.3
runtime. Other paths use the documented model `generate` interface. This is API
support inventory, not proof that every combination works on an eventual device.

Sampling controls require an appropriate sampling mode. No numeric temperature,
token budget, penalty or seed is selected. Published `generation_config.json`
defaults are evidence, not a SafeShift policy; future runners must record their
effective configuration including inherited defaults. Qwen's card also lists
`presence_penalty` for serving guidance: support by a particular Transformers
release must be checked before accepting it as a runner argument.

Ovis additionally documents `enable_thinking`, `enable_thinking_budget` and
`thinking_budget`; those change the model condition and remain unselected.
Gemma's `enable_thinking` belongs to the chat template. MiniCPM's matching
`downsample_mode` belongs to preprocessing, not score-based decoding selection.
`transformers.set_seed` / `enable_full_determinism` are runtime controls, **not**
`generate(seed=...)`; seed and determinism settings remain pending, with no
cross-version/device bitwise guarantee. Sources: `hf_generation`,
`hf_generation_451`, `hf_seed` and model evidence in JSON. D9 #3 stays PENDING;
historical hosted `temperature=0` is not copied.

## Preprocessing inventory — not a selected transform

All entries are `DOCUMENTED_NOT_RUNTIME_VALIDATED`; use the official processor,
with its exact revision and config, instead of reimplementing image transforms.

| Model | Official behavior/config documented | Integration boundary |
|---|---|---|
| Qwen | Dynamic resolution; processor pixel-budget fields 65536/16777216; patch 16, temporal patch 2, merge 2; image ID 151655 | Use model chat template and processor-owned image expansion; do not interpret pixel-budget fields as fixed dimensions. |
| Ovis | NaViT variable resolution; wrapper bounds 448²–1792² pixels and aligns dimensions to patch×stride | `preprocess_inputs` computes actual resize and overrides static Siglip 512×512 size. Preserve `pixel_values`, `grid_thws`, `<image>` processing and thinking config. |
| Molmo | Config 378×378 crop size, up to 8 crops, overlap margins [4,4], patch 14/pooling [2,2], RGB and mean/std 0.5 | Processor expands `<\|image\|>` into high/low-resolution image tokens and returns grid/pooling metadata. |
| Gemma 4 | Unified image patches; variable resolution/aspect ratio, RGB/rescale 1/255, no image normalization; patch 16, pooling 3, 280 soft tokens | Use `Gemma4UnifiedProcessor` and its template, not another Gemma architecture's preprocessing. |
| PaliGemma2 | Exact card specifies 448×448 input; processor expands image prefix plus BOS, prompt and newline | Raw gated preprocessing config/interpolation/exact token count not verified; plain text+image interface. |
| MiniCPM | Slice mode, resolution scale 448, patch 14, image IDs; config max slices 9; example overrides to 36; 4x/16x compression | Keep processor/generate downsample mode equal. Example override and config default are different conditions, neither selected here. |

Sources are the per-model `preprocessing.evidence` entries (pinned configs and
official implementation source). No images were processed to compare alternatives.
The Ovis static-size versus dynamic override and MiniCPM default versus explicit
override are explained by their call paths, not silently collapsed into one setting.

## Precision and quantization inventory

The JSON explicitly inventories **FP32, BF16, FP16, 8-bit, 4-bit, AWQ, GPTQ and GGUF**
for each model. Published tensor metadata is BF16 for Qwen/Ovis/Gemma/PaliGemma/MiniCPM
and F32 for Molmo; it is not a measurement of execution memory or hardware support.

BF16 loading is directly documented for five models; Molmo's exact card uses
`dtype="auto"` with float32 config. Other FP32/FP16/BF16 combinations are only
runtime dtype API possibilities where explicitly labelled, not exact-model support
claims. The [Transformers dtype API](https://huggingface.co/docs/transformers/main_classes/model)
does not establish numerical stability or kernel support on the eventual GPU.

[Bitsandbytes documentation](https://huggingface.co/docs/transformers/quantization/bitsandbytes)
offers conditional 8/4-bit runtime paths requiring Accelerate support, suitable
linear modules and supported hardware. Compatibility of each exact model remains
unverified; Ovis's custom device behavior especially must not be assumed. HF's
PaliGemma torchao int4 example uses a different checkpoint and is labelled as
runtime evidence only. MiniCPM's exact 4.6 card advertises BNB/AWQ/GPTQ/GGUF variants
and a Q4_K_M deployment example; no alternate weight repository is selected,
downloaded, revision-pinned or added to the D9 roster. Other AWQ/GPTQ/GGUF entries
are `NOT_VERIFIED_FOR_EXACT_REVISION`, not claims that these formats are impossible.

`selected_precision` and `selected_quantization` are PENDING for all six. No
hardware-derived candidate is selected in this task, and no benchmark results
inform the inventory. A future hardware-based proposal must be labelled
`PRE_FREEZE_CANDIDATE_NOT_VALIDATED` until its prescribed validation is complete.

## Mandatory W2.6B acceptance criteria from PR #21

**AC-A — Idempotent initialize/load.** `execute_call` invokes both methods for each
request. Repeated `initialize(context)` and `load(context)` for the same valid
condition must reuse the initialized backend and loaded model; they must not reload
weights, duplicate VRAM allocations or mutate the model condition. Define the cache
identity using model/revision/code, dtype/quantization, device placement and runtime
configuration. A different condition must fail explicitly or require an explicit
new runner lifecycle; never silently reuse incompatible resources. A failed load
must clean up incomplete allocations and must not mark the model loaded.

Cached weights/processors are runtime optimizations only. Keep eval/inference mode;
no training, adaptive state or generation history survives a call. Reset per-call
messages, generated IDs, stream buffers, KV/past-key-value caches, recurrent state
(where applicable), image features and error state. Call 1 and Call 2 remain
independent. Record and apply seed policy per eventual frozen run contract; do not
let lifecycle caching silently change the random-state policy.

Future acceptance tests must instrument factory/load calls: two independent
requests with one condition cause one successful initialization/load, while changed
conditions and failed loads cannot contaminate later calls. Real runner validation
must additionally verify stable resource allocation; dummy tests cannot establish
VRAM behavior. These tests are requirements for W2.6B, not runtime tests run here.

**AC-B — Partial generation evidence.** If generation raises after emitting native
output, the backend wrapper must raise `GenerationFailure(partial_raw=...)` with
only the losslessly serialized tokens/text/bytes actually observed. W2.6A then
persists that evidence and reports generation failure with parsing NOT_ATTEMPTED.
If the backend exposes nothing, use `partial_raw=None`; never invent output from
an error message, retry, prompt echo or presumed token sequence.

| Backend / models | Documentary partial-output boundary |
|---|---|
| Blocking `generate` for all six | No partial-return guarantee on exception. Do not claim intermediate IDs are available merely because the backend generated internally. |
| Transformers streamer candidate: Qwen, Molmo, Gemma, PaliGemma, MiniCPM | Runtime `streamer` API can expose emitted tokens/text; model-specific exception propagation and flushing remain **NOT_RUNTIME_VALIDATED**. Capture only what reached the callback; timeout/worker exceptions must terminate collection without hanging or marking success. |
| Ovis custom generator | Card explicitly says ordinary `TextIteratorStreamer` is incompatible with budgeted two-phase generation. Its `BudgetAwareTextStreamer` / `manual_end()` path can expose emitted text. Preserve both phases and identify backend-inserted budget text. Error-path flush must not create unobserved tokens. |

Text-only streamers may buffer partial words; do not claim un-emitted text was
captured. An eventual token-capturing callback may preserve observed token IDs in
the raw envelope, subject to qualification. A hard process/device failure may
prevent an in-process handler from running; document that limitation and preserve
any already durable evidence. No backend is certified here to recover every failure.
Sources: `hf_generation`, `hf_streaming`, pinned Ovis README/source, pinned Molmo
GenerationMixin source and each model card's generation path.

Future tests must inject an error after an observed chunk and prove exact partial
preservation, no parser invocation and separate failure status; also test an error
before any output (`None`), preservation failure, streamer timeout and independent
later calls. Ovis tests must cover both generation phases. Qualification may not
silently discard partial output because a blocking convenience call returned none.

## Unresolved items and handoff

1. Qwen exact 8B spatial grammar remains unestablished: the family cookbook runs
   a different checkpoint and also has an UNRESOLVED bbox docstring/example order conflict.
2. Ovis repository redirect works for documentary metadata; exact runtime resolution,
   custom remote code and automatic device mapping still need validation.
3. Molmo third-party data and research-use caveats require owner review; its
   single-image point grammar and box eligibility remain unqualified.
4. PaliGemma owner acceptance, gated preprocessing config and use-scope review remain
   open. Exact detection-token conversion requires qualification.
5. Gemma generic box/point interface is uncertain. MiniCPM has no documented generic
   spatial contract in the reviewed exact material. Neither status is a failure.
6. All real runners, environments, partial-output paths, decoding/thinking policies,
   precision/quantization, preprocessing, adapters, qualitative giant-box procedure,
   applicable external gate, final roles and protocol freeze remain pending.

No backup is activated. Grounding-only incompatibility cannot trigger replacement
of a classification-valid model; D9 continues to govern later role decisions.
D1–D9, canonical schema, D5 and prompts are unchanged.

## Offline validation

Use the existing Python 3.11.9 / Pillow 12.3.0 environment from repository root;
no dependencies installed and no random sampling:

```powershell
.venv/Scripts/python.exe -m unittest tests.test_model_provenance -v
.venv/Scripts/python.exe -m unittest discover -s tests
git diff --check
```

Validation: **297/297 tests passed**, including **26/26 provenance tests**.
`git diff --check` passed. All pre-freeze JSON parsed strictly and cross-config
invariants passed. Protected protocol/code files and SYNTHETIC V1 assets were
compared with the required base; no changes. Only the seven intended documentation,
configuration and test files are included; no weights/checkpoints or new dataset
assets are included. All protocol freeze fields remain PENDING.
The suite uses handcrafted/synthetic fixtures only. Checking SYNTHETIC V1 hashes
and existing fixture tests is not running a model or the model capability gate.
Census is compared by SHA-256 and file metadata only, never parsed or staged.
Its initial SHA-256 is
`cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`,
length 762487 bytes, last-write UTC `2026-09-17T03:55:10`; these remain unchanged.

NO_MODEL_WEIGHTS_DOWNLOADED. NO_MODEL_INFERENCE. SYNTHETIC_GATE_NOT_RUN.
NO_INSPECSAFE_INFERENCE. CENSUS_UNTRACKED_UNTOUCHED.
`protocol_freeze_commit_sha = PENDING`.
