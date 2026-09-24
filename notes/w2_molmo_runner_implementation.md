# W2.6B3A — Molmo2-O-7B offline runner

Base main: `8f121eda1485c5984e8f9cde6944388ac7b7c351`.
Branch: `implementation/d9-molmo-runner`.
Offline implementation and fake-backend tests: **COMPLETE**. Real runtime:
**PENDING**, reserved for B3B. This note records implementation verification,
not an independent Research Lead approval or runtime qualification.

## Documentary basis

Identity is exactly `allenai/Molmo2-O-7B` at immutable revision
`784410650d12be9bc086118fdefa32d2c3bced86`; provenance is
`configs/pre_freeze/local_model_provenance.d9.json#molmo2_o_7b`.
No model substitution, backup activation or performance selection occurs.
The following official files were read as text on 2026-09-24; no source was executed:

- [Pinned README](https://huggingface.co/allenai/Molmo2-O-7B/blob/784410650d12be9bc086118fdefa32d2c3bced86/README.md)
- [Pinned processor](https://huggingface.co/allenai/Molmo2-O-7B/blob/784410650d12be9bc086118fdefa32d2c3bced86/processing_molmo2.py)
- [Pinned model](https://huggingface.co/allenai/Molmo2-O-7B/blob/784410650d12be9bc086118fdefa32d2c3bced86/modeling_molmo2.py)
- [Pinned model config](https://huggingface.co/allenai/Molmo2-O-7B/blob/784410650d12be9bc086118fdefa32d2c3bced86/config.json),
  [processor config](https://huggingface.co/allenai/Molmo2-O-7B/blob/784410650d12be9bc086118fdefa32d2c3bced86/processor_config.json)
  and [generation config](https://huggingface.co/allenai/Molmo2-O-7B/blob/784410650d12be9bc086118fdefa32d2c3bced86/generation_config.json)
- [Transformers 4.57.1 ProcessorMixin](https://github.com/huggingface/transformers/blob/v4.57.1/src/transformers/processing_utils.py)

The README specifies Python 3.11 / Transformers 4.57.1, AutoProcessor and
AutoModelForImageTextToText with trusted custom code and automatic placement.
Its image example uses a text-first user message with PIL images. This runner
uses that path for exactly one image. It supplies explicit dtype instead of
the README's automatic dtype; this is a caller-selected execution contract,
not a research precision choice. It adds local-only restrictions to the recipe.

The pinned model inherits GenerationMixin and constructs its text/vision modules
from configuration, without separate pretrained backbone loads in its constructor.
The processor declares image processor, video processor and tokenizer components;
ProcessorMixin forwards the same local path and kwargs to these sub-loaders.
Still-image use can therefore still require the processor's video-related source
and dependencies at load time. Their actual import/load behavior awaits B3B.

## Snapshot, imports and lifecycle

`safeshift/runners/molmo2_o.py` provides `Molmo2ORunner` version
`molmo2-o-runner-v1`, `Molmo2OAdapter`, and an injectable `MolmoBackend`.
Importing the module does not import torch, Transformers, Hugging Face Hub or
Pillow, execute custom code, load weights, access a GPU or access the network.

The native backend requires `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` and
`HF_HUB_DISABLE_TELEMETRY=1` before ML imports. It checks cached library flags,
fails if the process imported HF before enabling offline mode, and rechecks
offline policy at lifecycle entry points. It checks the documentary Python and
Transformers target and records actual Python/torch/Transformers/Pillow/Hub
versions. Fake modules exercise this wiring without importing installed ML.

The lazy injectable resolver calls `snapshot_download` **only** with the exact
repo/revision and `local_files_only=True`. It resolves an existing cache entry;
it cannot provision missing assets. Both supplied and resolved directory paths
must end in `models--allenai--Molmo2-O-7B/snapshots/<exact revision>`.
Both factories receive that same local directory, revision,
`trust_remote_code=True`, `local_files_only=True`, explicit dtype and
`device_map="auto"`. The returned model config must retain that snapshot path.
Runtime absolute cache paths are not written into raw envelopes or manifests.

Tests use empty temporary directories with the expected layout. This verifies
resolver/loader contracts, **not asset completeness or weight-byte integrity**.
B3B must verify local bytes and actual nested-loader behavior separately.

Initialization validates versions before publishing state; loading validates both
resources, generation interface/configuration and `model.eval()` before publishing
them together. Both operations are idempotent and retryable after failure. The
condition key includes identity, runner version, precision, quantization, device,
software versions, preprocessing and loader policy; changes fail explicitly.

FP32, BF16 and FP16 are explicit supported contract values; quantization is NONE
only. The implemented placement is exactly `{"placement":"auto"}`. There is no
custom sharding, platform-specific placement, OOM fallback or bitsandbytes.
No precision, GPU, CPU-offload or multi-GPU behavior is runtime validated here.

## Inputs, generation and evidence

The runner opens request bytes in memory, rejects multi-frame images, decodes and
converts to RGB without image temporary files or manual resizing. One fresh user
message contains the unchanged request prompt and image. `apply_chat_template`
uses tokenization, a generation prompt, PyTorch tensors and dictionary output;
each returned tensor moves to `model.device`, matching the README.
Empty/malformed input IDs and incoming past-key-value history are rejected.

`torch.inference_mode()` surrounds `model.generate`. Generation settings come
from RunContext: only do_sample, temperature, top_p, top_k, max_new_tokens and
repetition_penalty are accepted. Boolean/integer distinctions, finite numeric
values and ranges are checked; a positive integer max_new_tokens is required.
Temperature/repetition penalty must be positive, top_p is in (0,1], and top_k is
a nonnegative integer. No decoding setting is selected or frozen by this task.
Non-null seeds fail because seed application is not implemented.

Each call passes an isolated copy of native generation defaults and records the
effective configuration. Multiple output rows, structured generation outputs,
auxiliary output payloads and persistent/static cache configurations are not
supported. One loaded model serves sequential independent calls; the runner
keeps no prompt history, generated output or past-key-values between calls.

The success envelope records schema/backend/model/revision/runner identities,
input IDs, input length, full generated IDs, continuation IDs, both continuation
decodes (with special tokens and for the parser), exact decoding kwargs,
effective native configuration and runtime condition/software metadata.
Generated IDs must be nonnegative integers excluding bool. The complete input
prefix must match before slicing at its exact length; short/mismatched output
fails rather than being silently truncated. Decoding uses
`processor.tokenizer.decode` with token-space cleanup disabled.

Before generate returns, failure has `partial_raw=None`. After return, observations
are captured before validation/decoding. Any later exception produces a separate
failure envelope with stage, exception type, identities and observations retained
so far. Its serializer is independent of the success serializer. NaN/Inf or
non-JSON malformed observations get explicitly labelled diagnostic trees, never
repaired token sequences. A tensor that fails `tolist()` still produces a return
marker, native type and input/generation metadata; unavailable token values are
not invented. There is no streaming guarantee for native generate exceptions.

The existing `execute_call` and FileRawStore persist raw bytes plus request/run
provenance before calling the adapter; partial failures persist without parsing.
Classification delegates to unchanged `parse_text(text, "classification")`.
PARSER_VERSION, canonical schema, label mapping and D5 are unchanged.

Native point syntax is retained verbatim in both decodes and raw tokens. No point
helper or coordinate extraction is added. On fake grounding envelopes the adapter
reports DOCUMENTED_NATIVE_POINT / NOT_YET_QUALIFIED and NOT_PARTICIPATING for
box/IoU, with no canonical value. It makes no sample-level point-validity claim.
There is no point-to-box conversion, fabricated box, IoU or Pointing Hit
qualification. Grounding status does not suppress classification participation.

## Validation and remaining work

From repository root, place the existing `.venv/Scripts` first on PATH:

```powershell
$env:PATH = (Join-Path (Get-Location) '.venv/Scripts') + ';' + $env:PATH
python -m unittest tests.test_molmo_runner -v
python -m unittest discover -s tests
python -m py_compile safeshift/runners/molmo2_o.py tests/test_molmo_runner.py
git diff --check
```

2026-09-24: **51/51 Molmo tests PASS; 551/551 full-suite tests PASS**;
compilation and `git diff --check` PASS. Local environment: Python 3.11.9,
Pillow 12.3.0, Windows; no dependencies installed. Default Python lacked Pillow,
so validation used the existing `.venv`. No random sampling or seed was used.
Tests deny sockets and actual ML imports, using handcrafted memory images and
fake outputs only; temporary raw artifacts are cleaned up. The versioned branch
commit identifies the implementation, not a runtime or protocol-freeze commit.

Checklist #1: COMPLETE documentary. #2: PENDING overall. Qwen and Ovis offline:
COMPLETE; their previously audited runtime: PASS / VALIDATED. Molmo offline:
COMPLETE; runtime: PENDING. Gemma: PENDING. #3–#8: PENDING.
`protocol_freeze_commit_sha: PENDING`.

No model/weights download, online snapshot resolution, real inference, GPU,
Kaggle, RunPod/CKEY, SYNTHETIC V1 gate, InspecSafe inference or real grounding call
was performed. Source-text retrieval was documentary only. No runtime harness,
notebook or provisioner was created; B3B remains a separate task.
The census stays untracked and untouched, SHA-256
`cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`.
