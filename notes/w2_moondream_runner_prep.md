# W2.6-D9R2E-MOONDREAM-PREP — source audit STOP

**Outcome: FP16 prerequisite blocked; report to Research Lead.** The requested
unchanged-source, no-BF16 runtime cannot be prepared from this audit. Per task
sections 5/8/9, dependent runner, provisioner, adapter and T4 harness implementation
stopped. This is a documentary Draft PR, not a completed runtime PREP. No remote
code patch, model execution, weights download, GPU, external eight-case gate or
InspecSafe access occurred. No resource or grounding promotion.

Base: `62fc3e0507d0187cdd309f611f11bfb6d3f34f99`.
Branch: `implementation/d9-moondream2-runner-prep`.
The requested `safeshift/runners/base.py` does not exist at this base;
`safeshift/runners/contracts.py` defines `LocalRunner` and `execute_call`.
Existing Qwen runners, protocol, prompts, gate and storage were read, not changed.

## Evidence and immutable identities

[Machine-readable audit](../configs/pre_freeze/moondream_prep_audit.v1.json)
records source URLs, capture UTC timestamps, SHA-256, byte sizes and pinned API
Git blob IDs. Small downloaded bytes were independently checked against those Git
blob IDs. Captures stay ignored under `data/processed/moondream_prep/`; no downloaded
third-party code/tokenizer is vendored. Capture timestamps are the actual UTC clock
readings (2026-09-25 UTC, 2026-09-26 local), not inferred dates.

* Model: `vikhyatk/moondream2`, release `2025-06-21`, commit
  `9a7d4024050840e001defacec2b00727e89149e6`; Apache-2.0 per pinned card/API.
* Nested tokenizer: `moondream/starmie-v1`, resolved commit
  `35192e10a54e36eabe0a7cc57a2c1aab371cafc5`.
  Discovery used the repository API, then independently fetched the
  [exact revision API](https://huggingface.co/api/models/moondream/starmie-v1/revision/35192e10a54e36eabe0a7cc57a2c1aab371cafc5?blobs=true)
  and exact-revision files. No moving reference is a selected dependency.
* Required nested `tokenizer.json`: 3,694,206 bytes, SHA-256
  `0512fdcac4a5f9e7746cbefce4a468dc93bf0f93f11e701b84f8b31bff199e9c`.
* `model.safetensors`: 3,854,538,968 bytes, expected LFS SHA-256
  `70a7d94c0c8349eb58ed2d9e636ef2d0916960f321ecabeac6354b8ba3d7403f`.
  **Metadata only; local weight bytes NOT_VERIFIED.** No weight body or tensor
  header was fetched. BF16 tensor publication is existing D9R1 API evidence;
  `config.json` also declares BF16.

Audited active remote-code closure: `hf_moondream.py`, `config.py`, `moondream.py`,
`vision.py`, `text.py`, `region.py`, `layers.py`, `rope.py`, `image_crops.py`,
`lora.py`, `utils.py`. Other legacy files returned by the source capture are not
claimed as audited active dependencies. `config.json` auto_map selects
`hf_moondream.HfConfig` / `hf_moondream.HfMoondream`, not legacy `modeling_phi.py`,
`vision_encoder.py`, `weights.py` or the hosted `handler.py`.

## Nested tokenizer: pin resolved, enforcement not implemented

[moondream.py L84–91](https://huggingface.co/vikhyatk/moondream2/blob/9a7d4024050840e001defacec2b00727e89149e6/moondream.py#L84)
constructs `tokenizers.Tokenizer` through
`Tokenizer.from_pretrained("moondream/starmie-v1")`. There is **no revision argument**,
local-files argument or constructor parameter for dependency injection.
The outer HF revision does not pin this nested request.

The inspected [tokenizers 0.21.2 binding L593–617](https://github.com/huggingface/tokenizers/blob/v0.21.2/bindings/python/src/tokenizer.rs#L593)
calls `huggingface_hub.hf_hub_download` for `tokenizer.json` and then the same
Rust `Tokenizer::from_file` used by `Tokenizer.from_file`. Its default revision
is `main`. This library source is version-tagged and response-hashed evidence,
**not a frozen or qualified SafeShift software environment**.

The nested JSON contains BPE vocabulary (51,200 entries), 21 added-token records,
pre-tokenizer Sequence, ByteLevel decoder, no normalizer, no post-processor,
no padding and no truncation. The native loader needs only this JSON; its BPE
merges/vocabulary and processing definitions are embedded. Starmie
`tokenizer_config.json` (3,981 bytes) and `special_tokens_map.json` (3 bytes, empty
object) are separately hashed documentary companion files, not read by this API.
No `config.json` is listed in the Starmie snapshot. Native special token IDs and
prompt templates are in model `config.py::TokenizerConfig`. Model-repository
legacy tokenizer/vocab/merges files must not substitute for Starmie.

Explicit loading design, **not implemented or runtime-proven**:

1. Provision model and Starmie using exact revisions and allowlisted artifact
   names; verify all sizes/hashes before import. Runtime must reverify them.
2. In one dedicated, sequential process, load the verified immutable remote module
   without editing source bytes. Temporarily replace only its module-global
   `Tokenizer` binding during construction with a small factory accepting exactly
   the one observed repo ID and no extra arguments. Any other request fails.
3. That factory calls the native `Tokenizer.from_file` on the verified Starmie
   file; restore the binding in `finally`. Never modify global tokenizers classes,
   vocabulary, tokens, templates, preprocessing or a shared cache `refs/main`.
4. Reject revision/hash/path mismatch before constructing anything. Check the
   model's actual tokenizer after construction. Prohibit concurrent loading,
   variant downloads and all other unreviewed dependencies.
5. Set `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`,
   `HF_HUB_DISABLE_TELEMETRY=1` before imports; model loader uses
   `local_files_only=True`, exact `revision` and `code_revision`. Reuse SafeShift
   socket denial for the whole process; disable network at the execution venue
   because Python socket patching alone is not an OS firewall.

The source supports equivalence of deserializing the same tokenizer bytes using
the same native deserializer. This design makes no vocabulary/preprocessing
change and has no alternative revision resolution path. That is a design argument,
not evidence of an implemented loader. Enforcement/tests remain pending after
Research Lead resolves FP16. Do not claim this pin alone fixes runtime readiness.

## Native interfaces and candidate mapping

[hf_moondream.py L48–76](https://huggingface.co/vikhyatk/moondream2/blob/9a7d4024050840e001defacec2b00727e89149e6/hf_moondream.py#L48)
exposes lazy properties forwarding to the inner model, setting up caches once.
The following contracts come from pinned source, not README examples.

| API | Signature excluding self | Native return |
|---|---|---|
| query | `query(image=None, question=None, reasoning=False, spatial_refs=None, stream=False, settings=None)` | `{"answer": str}` with nonstreaming, reasoning false; optional reasoning dict when enabled; generator when streaming |
| detect | `detect(image, object: str, settings=None)` | `{"objects": [{"x_min": number, "y_min": number, "x_max": number, "y_max": number}, ...]}` |
| point | `point(image, object: str, settings=None)` | `{"points": [{"x": number, "y": number}, ...]}` |

Image inputs are PIL Image or native EncodedImage; query additionally allows no
image. For SafeShift independent calls, future design uses a fresh image encoding,
no history/spatial refs/reasoning/variant. Classification would pass the unchanged
SafeShift classification prompt as `question`, preserving the entire returned
dictionary before extracting `answer` for the existing strict classification parser.
No Qwen chat template or HF `generate` assumptions transfer to this API.

[moondream.py L653–831](https://huggingface.co/vikhyatk/moondream2/blob/9a7d4024050840e001defacec2b00727e89149e6/moondream.py#L653):
detect/point encode `" " + object` between their native token template prefix and
suffix. This is an open object-description string, not an approved mapping from
SafeShift hazard IDs. Both call `_prefill_prompt(temperature=0, top_p=0)` and
`_generate_points`; **both internally perform autoregressive generation**.
Detect uses `include_size=True`; point uses false. Zero to `max_objects` outputs
(default 50), EOS termination; no confidence, sorting, NMS or uniqueness guarantee.
List order is generation order; the first item is not documented as best match.

Coordinates: center x/y = argmax of 1,024-bin logits divided by 1,024, hence
`[0, 1023/1024]`. Width/height use separate 1,024-bin size logits and
`2**((bin/1023)*10-10)`, hence `[1/1024, 1]`. Corners are center ± half-size.
Thus detections are normalized xyxy **without clamping**, possibly outside
`[0,1]`; theoretical aggregate corner range is `[-0.5, 1.4990234375]`.
The code calls these x/y and width/height but does **not explicitly declare the
top-left origin or axis direction**. This missing documentary detail must be
resolved before freezing an adapter; do not silently treat it as verified.

Candidate only: preserve every detection in list order; map fields to
`[x_min,y_min,x_max,y_max]`, then apply the unchanged canonical `bbox(...,
"xyxy_1")` rules (including existing clamp and strict geometry) after persistence.
No coordinate scale inference, regex, object selection heuristic, point-to-box,
or invented confidence. Zero/multiple detections are not automatically a single
gate prediction. Target semantics and one-box gate selection must be explicitly
pre-specified before any later gate. **No adapter implemented or gate run here.**

Spatial decoding uses argmax without sampling: deterministic algorithm given
identical logits. Numerical determinism of a future frozen CUDA runtime is
**not established by source**. Query defaults are sampling (temperature 0.5,
top_p 0.3, max_tokens 768); future greedy candidate requires explicit temperature
0 and a predeclared token limit. `encode_image` directly reads `settings["variant"]`
whenever settings is not None: future explicit settings must include
`variant: None`. Omitting that key can raise KeyError. `lora.py` can download via
urllib independently of HF offline flags when a non-null variant is supplied;
variants must be rejected. These are source findings, not observed runtime failures.

## FP16 audit and mandatory stop

| Component | Source finding | Effect of explicit model conversion |
|---|---|---|
| Parameters | `MoondreamModel` defaults BF16; HF wrapper does not pass dtype; vision/text/region constructors propagate dtype | Registered floating parameters can be cast; this alone is insufficient |
| KV caches | Registered k/v buffers; `_setup_caches` takes device and dtype from vision pos_emb; HF wrapper initializes lazily | Explicit conversion before setup can produce FP16 caches; runtime inspection still required |
| EncodedImage | Cloned per-layer k/v prefixes; `load_encoded_image` copies them back | External cached encodings must never cross calls/conditions |
| Mask | Registered bool triangular attention mask | Remains bool, must move to cuda:0; not a BF16 component |
| Text RoPE | Registered `freqs_cis` generated using FP32 in `rope.py` | Floating buffer can be cast; FP16 numerical consequences unqualified |
| Vision input | `vision.py::prepare_crops`, L25–42, explicitly casts BF16 then normalizes in-place | **Not a parameter/buffer; model.to/half cannot change this future allocation** |
| Vision first layer | `vision_encoder` passes crop patches directly to patch_emb, L64–67 | FP16 parameters receive BF16 input; no source cast reconciles them |
| Spatial generation | Coordinate division and size `.float()` use intermediate FP32; cast back to region/logit dtype | FP16 parameter policy is not a promise that every arithmetic intermediate is FP16 |
| Other BF16 paths | gaze inputs; quantized unpack code | Out of query/detect/point scope; gaze/quantization must be forbidden |

[Pinned vision source](https://huggingface.co/vikhyatk/moondream2/blob/9a7d4024050840e001defacec2b00727e89149e6/vision.py#L25)
is the decisive blocker. Query, detect and point with images all traverse this
path. The expected dtype mismatch is a source-based inference, **not a measured
T4 failure**. Converting parameters/buffers or a loader torch_dtype override cannot
remove the hard-coded crop allocation. Keeping BF16, autocast or implicit dtype
fallback violates this task's condition. Changing BF16 normalization to FP16
changes rounding/preprocessing; a hook casting after normalization still creates
BF16 intermediates and needs explicit policy review. No such workaround is applied.

`image_crops.py` additionally chooses pyvips if import succeeds, otherwise Pillow
LANCZOS. A future environment must select and pin that branch, not permit an
environment-dependent preprocessing change. `config.py` has text/region group_size
None, selecting ordinary Linear; do not use quantized code or `compile()` as a
resource fallback. Boolean/integer index tensors are not floating precision
residuals; source creates some position indices on CPU, so future no-offload
inspection must distinguish indices from model parameters/buffers/caches.

**Research Lead action required:** decide whether to authorize a separately
reviewed, explicitly versioned precision/preprocessing change (with its scientific
implications) or another documented resolution. This PR requests no implicit
exception and makes no replacement-model decision. No BF16 fallback. Until then,
FP16 plan NOT_FROZEN, runner PENDING, smoke NOT_PREPARED_NOT_RUN_FP16_BLOCKER.

## Remaining work and validation boundary

The required future resource condition is recorded, not approved as executable:
exactly one NVIDIA T4 16GB / CC 7.5, FP16, NONE, batch 1, cuda:0 for all model
parameters/buffers/caches, no CPU/disk offload, no automatic precision/quantization
fallback. One load lifecycle; handcrafted local inputs only; query and detect
callability, raw evidence and OOM checks; no accuracy evaluation. No smoke command
is offered because no harness is ready.

Every future call must preserve native query/detect/point separately with sample,
run/call IDs, prompt, model/tokenizer hashes, software, decoding, input hash and
Git commit: native return -> raw bytes -> SHA-256/store -> adaptation. Failures
must retain observable partial native output; sanitized evidence must omit
exception messages, secrets and personal absolute paths. Blocked work includes
fake tests for loading, revision mismatch, offline enforcement, residual BF16,
offload rejection, raw-before-parse, native dispatch and exact-one-load. These
tests have **not** been claimed as passing without an implementation.

Documentary tests cover immutable records, artifact evidence distinctions and
status/protected-file boundaries only. Full existing suite uses fixtures/fake
backends; it does not execute the real external gate or a model. JSON validation,
py_compile of the added documentary tests and git diff --check are required.
Validation: **869/869 full-suite tests PASS**, including **6/6** new documentary
checks, in the existing `.venv` (Python 3.11.9). All three JSON files (audit plus
unchanged roster/provenance) validate; `py_compile` on the added test and
`git diff --check` PASS. Commands from repository root:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests
python -m json.tool configs/pre_freeze/moondream_prep_audit.v1.json > $null
python -m json.tool configs/pre_freeze/local_models.d9.json > $null
python -m json.tool configs/pre_freeze/local_model_provenance.d9.json > $null
python -m py_compile tests/test_moondream_prep_audit.py
git diff --check
```

The initial full run exposed a new documentary-test regex matching `https:/` as a
Windows drive and historical Qwen freeze checks rejecting added audit links in
shared configs. The regex was corrected and shared config edits removed; no
historical test or frozen source hash was changed. Requested Moondream runtime
mock tests remain NOT_IMPLEMENTED due to the mandatory source-audit stop.

Current statuses: documentary UPDATED; nested tokenizer pin RESOLVED_DOCUMENTARY;
runtime enforcement NOT_IMPLEMENTED; classification CANDIDATE; resource
T4_FEASIBILITY_CANDIDATE; grounding
DOCUMENTED_NATIVE_DETECT_AND_POINT_PENDING_SYNTHETIC_GATE;
protocol_freeze_commit_sha PENDING. Census remains untracked and untouched,
SHA-256 `cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`.

This separate audit overlays historical pending dependency wording in the D9R1
provenance. The shared roster/provenance files remain unchanged: existing frozen
Qwen3 gate source checks include those files. Their runtime PENDING statuses remain
correct. No frozen checksum or historical test was relaxed for this documentation.
