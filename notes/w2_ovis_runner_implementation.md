# W2.6B2A — Ovis2.5-9B offline runner

Base main: `9995f6d6247c3b506ee995ed993ee57e339b0dbf` (PR #24).
Branch: `implementation/d9-ovis-runner`. This is an offline implementation and
fake-backend validation only. Checklist #2 stays PENDING overall; Ovis real runtime
validation, decoding/precision freeze and grounding qualification remain pending.
`protocol_freeze_commit_sha: PENDING`.

## Pinned source and identity

The requested D9 model ID is `AIDC-AI/Ovis2.5-9B`; its repository redirect is
`ATH-MaaS/Ovis2.5-9B`, recorded separately. Both refer to immutable revision
`d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd`. The loader uses the requested ID,
exact revision, `trust_remote_code=True`, `local_files_only=True`, and
`AutoModelForCausalLM`. Tests inject a fake factory and never execute remote code.
The checked source is the [pinned model implementation](https://huggingface.co/ATH-MaaS/Ovis2.5-9B/blob/d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd/modeling_ovis2_5.py)
and [pinned README](https://huggingface.co/ATH-MaaS/Ovis2.5-9B/blob/d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd/README.md),
read as source text on 2026-09-23. Provenance inventory remains in
`configs/pre_freeze/local_model_provenance.d9.json`.

The pinned `preprocess_inputs` takes messages, `min_pixels`, `max_pixels`,
`add_generation_prompt`, and `enable_thinking`, and returns `input_ids`,
`pixel_values`, `grid_thws`. The pinned `generate` merges multimodal embeddings,
forwards generation to `self.llm.generate`, and returns generated IDs. When a
thinking budget is enabled it may concatenate two generated phases and insert
early-stopping text IDs. The README decodes `outputs[0]` directly. Therefore the
runner records `input_ids` and `native_generated_ids` separately and never assumes
an input prefix in generated output.

## Execution condition and lifecycle

Import is lazy. `initialize` constructs the backend once and checks recorded
torch/Transformers/Pillow versions. `load` runs once for one condition; an altered
model ID, revision, backend, runner version, precision, quantization, device,
preprocessing, software version, loader policy, or thinking condition requires a
new runner. Failed loads do not publish a model and can be retried. No fallback,
pipeline, `model.chat`, backup activation or automatic reload is present.

The documented BF16 single-CUDA path is the only implemented placement candidate:
`BF16`, `NONE`, `{"placement":"cuda:0"}`. Loading calls `.cuda()` and `.eval()`.
No FP16/FP32 or automatic device mapping support is asserted for this wrapper.
This path is **not runtime validated**. Qwen's FP16 Kaggle smoke result is not
transferred to Ovis.

Input bytes are decoded to one RGB still image in memory; animated and malformed
images fail preprocessing. The caller's exact `Request.prompt` enters one native
user message after the image. Native preprocessing owns resize; the runner passes
and records the pinned default bounds `448²` and `1792²` pixels. It does not add a
grounding suffix or `<ref>` tags.

Decoding and thinking settings come from `RunContext.decoding`, with explicit
`enable_thinking`, `enable_thinking_budget` and `max_new_tokens`. If budgeting is
enabled, `thinking_budget` must be a positive integer, thinking must be enabled,
and `max_new_tokens > thinking_budget + 25`, as stated in the pinned README.
Allowed generation keys are validated for type/range. No values are selected as
research decoding defaults. The runner does not add EOS/PAD overrides; native
model/tokenizer defaults remain part of future runtime qualification. A non-null
seed is rejected because seed application is not implemented.

## Raw output, errors and adapters

`generate_raw` emits sorted strict UTF-8 JSON bytes containing model/revision
identity, both token sequences, both decodes (including special tokens for one),
exact generation kwargs, execution condition and software versions. Reasoning and
native spatial tags are not stripped or repaired. `execute_call` persists those
bytes with `FileRawStore` before invoking the adapter.
The envelope snapshots the pinned custom wrapper's `llm.generation_config` before
each call, since `self.llm.generate` owns defaults; an uninspectable native config
fails explicitly.

The blocking `generate` interface provides no guaranteed observable partial
output on an exception: `GenerationFailure(partial_raw=None)`. Once it returns,
token-row validation, token validation, either decode, or serialization failure
produces a deterministic failure envelope with all JSON-serializable observations
obtained up to that stage and the exception **type**, never its message. The core
persists that envelope without parsing it. As with the pinned source, custom
two-phase generation might produce internal tokens before raising without returning;
the blocking interface cannot recover those tokens. A future qualified streamer
would need to preserve each actually emitted phase and any backend-inserted text.

Classification adaptation validates the raw envelope and delegates unchanged to
`parse_text(text, "classification")`. Invalid text is
`INVALID_CLASSIFICATION_OUTPUT`; structural adapter failure is `PARSER_FAILURE`.
Grounding remains `UNSUPPORTED_GROUNDING_INTERFACE` / `NOT_YET_QUALIFIED` with
`SpatialKind.NONE`, even when native box tags are present. The optional native
evidence helper recognizes only complete documented point/box tag sequences or
bracketed comma-separated lists, finite coordinates in `[0,1)`, x-first top-left
box ordering, and returns diagnostic candidates only. It does not convert points
to boxes, clamp coordinates, calculate IoU or produce a D5 canonical result.

No persistent per-call state mutation was found in the pinned
`preprocess_inputs`/`generate` path: `NO_DOCUMENTED_PERSISTENT_CALL_STATE`.
The runner retains only backend, immutable condition and loaded model. Each call
creates fresh messages, token IDs, decoded text and envelope. Fake-backend tests
check that two calls reuse one load without keeping output or prompt history.

## Validation and limits

Run from repository root using the existing virtual environment:

```powershell
.venv/Scripts/python.exe -m unittest tests.test_ovis_runner -v
.venv/Scripts/python.exe -m unittest discover -s tests
git diff --check
```

Validation on 2026-09-23: **22/22 Ovis tests** and **435/435 repository tests**
PASS; `git diff --check` passes. The tests use fake torch/Transformers/model
behavior and tiny in-memory images;
no model weights, GPU, Hugging Face cache, network access during tests, real
inference, SYNTHETIC V1 gate or InspecSafe data are used. Exact test counts and
commit/PR identifiers are recorded in the implementation report after validation.
