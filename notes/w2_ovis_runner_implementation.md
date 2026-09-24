# W2.6B2A — Ovis2.5-9B offline runner

Base main: `9995f6d6247c3b506ee995ed993ee57e339b0dbf` (PR #24).
Branch: `implementation/d9-ovis-runner`. This is an offline implementation and
fake-backend validation only. Checklist #2 stays PENDING overall; Ovis real runtime
validation, decoding/precision freeze and grounding qualification remain pending.
Research Lead reviewed the fix diff from `6f7b4d1` to `641c869` and returned
`PASS_WITH_GOVERNANCE_CLEANUP`, with no remaining technical blockers. Ovis offline
runner implementation is **COMPLETE**; real runtime validation is **PENDING**.
Grounding remains `DOCUMENTED_BOX_AND_POINT / NOT_YET_QUALIFIED`.
`protocol_freeze_commit_sha: PENDING`.

## Pinned source and identity

The requested D9 model ID is `AIDC-AI/Ovis2.5-9B`; its repository redirect is
`ATH-MaaS/Ovis2.5-9B`, recorded separately. Both refer to immutable revision
`d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd`. The loader resolves that exact revision
of the **resolved** repository locally, then passes the validated local path to
`AutoModelForCausalLM` with `trust_remote_code=True`, the same `revision`, and
`local_files_only=True`. Research identity and raw provenance retain both IDs.
Tests inject both a fake resolver and a fake model factory; no remote code executes.
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

Ovis image `input_ids` contain model-internal negative visual sentinel IDs, distinct
from generated tokenizer IDs. In the pinned still-image preprocessing path,
`_merge_inputs` replaces the `IMAGE_PLACEHOLDER_ID = -200` with image indicators
`-301` / `-302` and `VISUAL_ATOM_ID = -300`. The input validator accepts exactly
a list of integers (excluding booleans), with nonnegative text IDs or those three
negative values. It rejects arbitrary negatives, leftover `-200`, and the video
placeholder/indicators `-201`, `-303`, `-304`. The separate generated-ID validator
accepts only nonnegative integers, excluding booleans. The adapter uses the same
two distinct validators. Input sentinel values are preserved without conversion.

## Exact local snapshot and nested assets

The backend lazily imports `huggingface_hub.snapshot_download` and resolves only
`repo_id="ATH-MaaS/Ovis2.5-9B"`, `revision=REVISION`, `local_files_only=True`.
The returned path must be an existing absolute directory with the full cache suffix
`models--ATH-MaaS--Ovis2.5-9B/snapshots/d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd`.
Both the supplied and resolved directory paths must match that suffix; checking
only the final basename would not establish repository identity. A wrong repo,
wrong commit, mutable ref, missing directory or incompatible directory alias fails
before model construction. Resolver errors map to `MODEL_LOAD_FAILURE` through
the existing executor, and a failed attempt publishes no model.

This is necessary because the pinned Ovis constructor calls
`AutoTokenizer.from_pretrained(self.config.name_or_path)`, and its VisualTokenizer
loads the image processor using that same model-local path. Those nested calls
do not inherit the outer revision/local-only arguments. Loading the custom model
from the exact local snapshot makes `config.name_or_path` local during construction,
so the tokenizer and image processor resolve from that snapshot. The runner also
checks that the returned model config retains the same exact snapshot before
publishing the resource. The absolute cache path is runtime-local and is not placed
in the raw envelope, versioned configuration or manifest.

The injected test resolver returns empty synthetic directory trees in temporary
storage; no real snapshot is downloaded or loaded. Layout and call-boundary tests
are **not local byte verification**. Snapshot completeness, code/asset/weight hashes,
and actual nested-loader behavior still require real provisioning and runtime
validation. This task neither runs nor claims those checks.

## Execution condition and lifecycle

Import is lazy. `initialize` constructs the backend once and checks recorded
torch/Transformers/Pillow/Hugging Face Hub versions. `load` runs once for one condition; an altered
model ID, revision, backend, runner version, precision, quantization, device,
preprocessing, software version, loader policy, or thinking condition requires a
new runner. Failed loads do not publish a model and can be retried. No fallback,
pipeline, `model.chat`, backup activation or automatic reload is present.

The documented BF16 single-CUDA path is the only implemented placement candidate:
`BF16`, `NONE`, `{"placement":"cuda:0"}`. Loading calls `.cuda(0)` and `.eval()`;
input IDs, pixel values and grid metadata also use `.cuda(0)`, independent of the
current CUDA device. Fake model/tensor objects record and assert all four arguments.
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
evidence helper recognizes exactly one point or box tag, or a square-bracketed
comma-separated list, with finite coordinates in `[0,1)` and x-first top-left
box ordering, and returns diagnostic candidates only. It does not convert points
to boxes, clamp coordinates, calculate IoU or produce a D5 canonical result.
Multiple unbracketed tags, prose extraction, missing list commas, trailing commas,
malformed tags and arbitrary four-number strings are rejected.

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

Validation of the review fix: **32/32 Ovis tests** and **445/445 repository tests**
PASS; `git diff --check` passes. The tests use fake torch/Transformers/model
behavior and tiny in-memory images;
no model weights, GPU, Hugging Face cache, network access during tests, real
inference, SYNTHETIC V1 gate or InspecSafe data are used. Exact test counts and
commit/PR identifiers are recorded in the implementation report after validation.
Tests reject socket connections and real torch/Transformers/Hub imports; the fresh
module-import subprocess applies the same guards. Ten added regression tests cover
sentinel preservation/rejection, generated-ID rejection, snapshot repo/revision and
path checks, resolver failures/retry, returned config locality, explicit CUDA 0,
and documented multi-result spatial syntax. Existing lifecycle, raw preservation,
classification, thinking and grounding-firewall tests continue to run.
