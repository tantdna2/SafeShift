# W2.6B1A — Qwen3-VL-8B offline runner implementation

Base main: `f86771d1006d93d99375fe74701215e8d8f601ee` (PR #22 / W2.6B0).
Branch: `implementation/d9-qwen-runner`. Date: 2026-09-22.
Authority: Project Owner's W2.6B1A request under unchanged D9.

**Implementation contract is structurally correct** is the tested claim.
**Qwen runtime works on GPU** is NOT established. All outputs in these tests are
handcrafted fake outputs; there are no model observations or capability results.

## Identity and integration

`safeshift/runners/qwen3_vl.py` implements `Qwen3VLRunner(LocalRunner)` and
`Qwen3VLAdapter` without changing W2.6A contracts, storage, labels or schema.
`ModelIdentity` locks `Qwen/Qwen3-VL-8B-Instruct` at
`0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`, with evidence in
`configs/pre_freeze/local_model_provenance.d9.json#qwen3_vl_8b_instruct`.
No revision lookup, alternate checkpoint, provider transport or replacement exists.

The [pinned official card](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct/blob/0c351dd01ed87e9c1b53cbc748cba10e6187ff3b/README.md)
documents `AutoProcessor` / `Qwen3VLForConditionalGeneration`, native chat-template
processing, `generate`, continuation slicing and batch decode. The implementation
follows that path. Both factories receive the exact revision,
`trust_remote_code=False` and `local_files_only=True`. Missing cached resources
fail; future authorized execution requires separately provisioned exact files.
This task never provisions or downloads them.

PyTorch and Transformers import only in the default backend factory called by
`initialize`. `QwenBackend` accepts injected processor/model factories and a torch
facade. Offline tests exercise the same runner code, including a default-factory
test with synthetic import modules; no real `from_pretrained` is called. Network
socket calls and real ML imports are blocked during each test. A fresh subprocess
also verifies importing/constructing the module with ML imports forbidden.

## Lifecycle, state and caller configuration

One instance supports sequential independent calls. The cache key is a deterministic
snapshot of model ID/revision, runner/backend version, precision, quantization,
device metadata/placement, software versions, preprocessing and fixed loader flags.
Changed conditions fail explicitly even after initialization; construct a new
instance. Call/sample/prompt IDs and per-call decoding are not weight-cache keys.
Repeated `initialize`/`load` under one condition call each factory once. Resources
are published only after load/eval/config validation; failed attempts retain no
processor/model or error on the runner. A later explicit call may retry under the
same condition. There is no automatic retry or unload/reload/fallback loop.

The caller must record actual `torch`, `transformers` and `pillow` versions in
`RunContext.software_versions`; initialization checks them against the backend.
Additional caller versions (driver, torchvision, accelerate, etc.) are retained
by W2.6A and the condition key. The raw envelope adds observed backend versions,
model dtype, input device, resolved device map and runner version. A real environment
and all its relevant dependency/kernel/driver versions still need qualification.

Supported implementation inputs, **not selected research settings**:

- `precision`: `FP32`, `BF16`, `FP16`, mapped to torch dtypes. Other values, including
  `PENDING` and `auto`, fail explicitly; hardware support remains unvalidated.
- `quantization`: only explicit `NONE`. Quantized loading is not implemented.
- `device`: caller chooses `placement` = `cpu`, `cuda:N` or `auto`; additional keys
  are recorded metadata. No GPU is implicitly selected. Inputs move to the loaded
  model's actual device; sharding/device dispatch remains runtime-unvalidated.
- `preprocessing`: `{}` or `{"mode":"official_processor"}`. No custom resize,
  pixel budget, prompt suffix or undocumented override is accepted.
- `decoding`: only `temperature`, `do_sample`, `top_p`, `top_k`, `max_new_tokens`,
  `repetition_penalty`; supported numeric types/ranges are checked and values passed
  unchanged. Unsupported keys fail before generation. Sampling compatibility still
  follows the runtime's validation. No temperature, sampling mode or budget is added.
- `seed`: only `None` at this milestone; an explicit seed fails instead of recording
  a seed the runner did not apply. Seed/determinism policy remains future work.

A per-call copy of the checkpoint `generation_config` is passed with caller kwargs.
The envelope records the resulting configuration snapshot (inherited defaults plus
overrides), including inherited stop tokens. It is not a frozen decoding policy or
a measurement of runtime-derived stopping length. Checkpoint configs requesting
multiple sequences, dictionary outputs, logits/scores/attention/hidden-state outputs,
or persistent cache implementations are explicitly rejected, not silently rewritten.
Only default/dynamic per-call KV caching is accepted; no caller KV/cache object is
accepted. The implementation adds no generation-policy defaults.
Supported controls are documented in the
[Transformers generation reference](https://huggingface.co/docs/transformers/v4.57.1/en/main_classes/text_generation).

Model evaluation and `torch.inference_mode()` wrap generation. Messages, prepared
inputs, token IDs, decoded strings and copied generation config remain call-local.
The [native Qwen implementation](https://github.com/huggingface/transformers/blob/v4.57.1/src/transformers/models/qwen3_vl/modeling_qwen3_vl.py)
stores image-dependent `rope_deltas` on the inner model. The runner checks that
layout and clears it plus any generation `_cache` before/after generation, including
exceptions. No KV/image/token/parse/error history is stored on the runner.
This source review does not certify every Transformers release or stable VRAM
allocation. Concurrent use of one runner is outside this sequential contract.

## Input and raw preservation

Pillow decodes `Request.input_bytes` through `BytesIO`; decompression-bomb warnings
become errors and multi-frame inputs fail. A detached RGB image is passed directly
to the official processor and closed after processing. There is no filesystem image
copy, local-path assumption, hand-resize or dataset access. Native messages contain
one user turn with that image and exactly `Request.prompt`.
`apply_chat_template` uses `tokenize=True`, `add_generation_prompt=True`,
`return_dict=True`, `return_tensors="pt"`.

Raw schema `safeshift-qwen3-vl-raw-v1` is deterministic strict UTF-8 JSON bytes:

| Fields | Meaning |
|---|---|
| `schema_version`, `backend`, `model_id`, `model_revision` | Exact serialization/runtime/checkpoint identity |
| `input_token_count` | This single input's token length |
| `generated_ids_full` | Exact full integer sequence returned by backend, including input prefix |
| `continuation_ids` | Full sequence sliced at the input length; prefix consistency is checked |
| `decoded_with_special_tokens` | Continuation decode with `skip_special_tokens=False` |
| `decoded_for_parser` | Continuation decode with `skip_special_tokens=True` |
| `generation_kwargs`, `effective_generation_config` | Caller overrides and inherited configuration snapshot |
| `runtime` | Observed backend versions, dtype/device/map and runner version |

Both decodes use `clean_up_tokenization_spaces=False`; no string stripping, JSON
repair, reasoning extraction or spatial interpretation occurs. Full token IDs remain
the lossless token evidence. Sorted keys, compact separators and `allow_nan=False`
make serialization deterministic for identical native evidence/configuration.

Use the unchanged `execute_call(runner, adapter, FileRawStore(...), request, context)`.
The core durably preserves raw bytes **and** metadata before calling `adapt`; storage
failure prevents parsing. The adapter validates envelope fields, identity, types and
continuation consistency, then passes the preserved parser text directly to existing
`parse_text(text, "classification")`. It never owns a SafeShift prompt.
Valid text yields existing `Classification`; invalid text yields `INVALID`.

Grounding yields `UNSUPPORTED`, `SpatialKind.NONE`, and diagnostic
`interface_status=NOT_YET_QUALIFIED` / `UNCERTAIN_REQUIRES_EXTERNAL_GATE` regardless
of whether text resembles points, boxes or malformed JSON. This reports interface
qualification, not absence of spatial ability or a malformed qualified box. No
point-to-box conversion, coordinate convention, IoU, score, gate verdict or role
assignment is introduced. Invalid envelope structure still reports parser failure.

## Errors and partial generation

Existing W2.6A stage mapping is unchanged:

| Failure | Error code |
|---|---|
| Import/initialization/version or cached-condition mismatch at initialize | `RUNNER_INITIALIZATION_FAILURE` |
| Processor/model loading or unsupported load condition | `MODEL_LOAD_FAILURE` |
| Image decode, input processing, unsupported decoding/seed at prepare | `PREPROCESSING_FAILURE` |
| Blocking generate or native output serialization failure | `GENERATION_RUNTIME_FAILURE` |
| Invalid classification text | `INVALID_CLASSIFICATION_OUTPUT` |
| Grounding interface not qualified | `UNSUPPORTED_GROUNDING_INTERFACE` |
| Invalid raw envelope/adapter exception | `PARSER_FAILURE` |
| Evidence write failure | `RAW_PRESERVATION_FAILURE` |

**BLOCKING_GENERATE_NO_PARTIAL_GUARANTEE**: when blocking `model.generate` raises,
the wrapper raises `GenerationFailure(partial_raw=None)`. It cannot observe internal
partial tokens; error messages never become output and the parser never runs.
No streamer is implemented. B1B/B1C may evaluate observed streaming evidence if
needed. Process/device crashes and runtime-specific partial recovery remain
unqualified.

### PR #23 blocking review fix: post-generation evidence

Reviewed HEAD: `b4a7e34ab54408a7dae3f24204d6b4de4f337e11`.
Runner version is now `qwen3-vl-runner-v2`; success-envelope schema and its required
fields remain unchanged. The previous implementation lost returned native IDs when
prefix validation or decoding failed. Observation is now separated from structural
validation, decoding and semantic parsing: each serializable observation is captured
as immutable JSON bytes immediately, before later steps can fail or mutate it.

Failures use `safeshift-qwen3-vl-failure-v1` with exact backend/model/revision,
`generation_observation_status=RETURNED_NATIVE_OUTPUT`, input token count, failing
stage and exception **type only**. Native evidence fields are present only when
observed and losslessly representable:

- `observed_generated_ids`: exact `.tolist()` result, including invalid row shapes;
  capture occurs before row/token/prefix validation.
- `generated_ids_full`: validated single token sequence, captured before prefix checks.
- `continuation_ids`: recorded only after prefix validation and slicing succeed.
- `observed_special_decode` / `observed_parser_decode`: returned decode representation,
  captured before validating it as a single string.
- `decoded_with_special_tokens` / `decoded_for_parser`: each completed valid decode,
  independently retained if the following decode or success serialization fails.

The failure serializer assembles those already captured fragments independently
of success metadata/serialization. It produces deterministic strict UTF-8 JSON;
Unicode escaping preserves even an observed lone surrogate without invalid UTF-8.
Only plain JSON values are accepted, without object/string coercion, non-finite
values, output repair, exception messages or semantic parsing. An unrepresentable
later observation does not erase earlier evidence. If `.tolist()` itself fails
before any token representation is obtained, `partial_raw=None`; no token sequence
is inferred from the returned opaque object. A blocking `generate()` exception
before return likewise retains its existing no-output behavior.

After a post-generation failure, `GenerationFailure(partial_raw=...)` routes this
envelope through unchanged W2.6A storage: raw plus metadata are preserved, status
stays `NOT_ATTEMPTED`, error is `GENERATION_RUNTIME_FAILURE`, and no adapter runs.
Storage failure maps to `RAW_PRESERVATION_FAILURE`. The adapter also rejects this
separate envelope if called directly. Native cache cleanup still runs on errors,
and a later independent call can succeed using the already loaded resources.

## Validation and boundaries

Environment: existing Python 3.11.9 / Pillow 12.3.0, Windows x64; no installation,
dependency changes or stochastic test sampling. Tests generate tiny 2x3 PNGs in
memory (plus a tiny animated-image rejection fixture); none use SYNTHETIC V1 images
as model inputs. Fake output IDs/text/config values are contract fixtures only.
Temporary raw-store artifacts are under a temporary repository's relative
`data/processed/local_runs/` and cleaned after tests. No inference run is claimed.
The implementation commit on this branch identifies reproducible code; it is not
the protocol freeze commit.

Run from repository root:

```powershell
.venv/Scripts/python.exe -m unittest tests.test_qwen_runner -v
.venv/Scripts/python.exe -m unittest discover -s tests
git diff --check
```

Results after the review fix: **63/63 Qwen tests PASS; 360/360 full-suite tests PASS**,
no failures/errors. The fix adds 10 tests and updates 2 existing tests (prefix
failure and first-decode failure); the reviewed baseline had 53 Qwen tests.
Coverage includes AC-A and AC-B, exact factory pins, lazy imports, image and prompt
packaging, caller decoding, raw-before-adapter persistence, strict envelopes,
canonical classification, unqualified grounding, failure recovery, and state cleanup.
`git diff --check`: PASS. No tracked JSON changed; envelope strict-JSON tests pass.
Protected files (DECISIONS, D5/schema, SYNTHETIC V1, B0 revisions/configuration) are
unchanged from base. The only five changed files are runner, test and these task/notes
files. No weights, checkpoints, Hugging Face cache, model artifacts or new dataset
assets were produced or staged.

Census remains untracked and untouched: SHA-256
`cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`,
762487 bytes, last-write UTC `2026-09-17T03:55:10`. Verification uses hash/stat only.

Checklist #1: COMPLETE documentary. **#2: PENDING** — Qwen runner code + offline
contract tests implemented; real runtime validation and remaining model runners
pending. **#3–#8: PENDING**. Exact environment, VRAM stability, real preprocessing/
generation behavior, decoding/seed, precision/quantization, grounding grammar and
adapter qualification, external gate, final roles and full freeze remain unresolved.
No backup is activated. No D9 config/provenance edit was needed.

NO_MODEL_WEIGHTS_DOWNLOADED. NO_REAL_MODEL_INFERENCE. SYNTHETIC_GATE_NOT_RUN.
NO_INSPECSAFE_INFERENCE. CENSUS_UNTRACKED_UNTOUCHED.
`protocol_freeze_commit_sha = PENDING`.
