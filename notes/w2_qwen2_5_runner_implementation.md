# W2.6-D9R2A — pinned Qwen2.5-VL-3B offline runner

Status: **IMPLEMENTED / OFFLINE_TESTED**. Real T4 runtime: **PENDING / NOT_RUN**.
Resource status remains **T4_FEASIBILITY_CANDIDATE**. No T4/FP16/Colab/Kaggle
runtime validation is claimed. Base main:
`92545ff4071c7055f7003995379b4af8993b6840`.
Branch: `implementation/d9-qwen2_5-runner`.

## Identity and documentary review

`Qwen2_5VLRunner(LocalRunner)` and `Qwen2_5VLAdapter` represent only
`Qwen/Qwen2.5-VL-3B-Instruct@66285546d2b821cf421d4f5eb2576359d3770cd3`.
Provenance remains
`configs/pre_freeze/local_model_provenance.d9.json#qwen2_5_vl_3b_instruct`.
No roster/revision/provenance/config changes. The pinned weights retain the Qwen
Research License documented in D9R1; a library source license does not replace it.

Documentary inspection completed before implementation/tests, 2026-09-24 UTC.
Only public source text, model documentation and the small qwen-vl-utils source
wheel were read; no package installation, imported ML backend or model weights.

| Source | Verified interface / evidence |
|---|---|
| [Exact model card](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/blob/66285546d2b821cf421d4f5eb2576359d3770cd3/README.md) | Qwen2_5_VLForConditionalGeneration, AutoProcessor, qwen-vl-utils 0.0.8, text-only chat formatting then process_vision_info and processor call; input-prefix trimming and batch_decode. Access 14:14:01Z; raw card SHA-256 `0b6da5a154b923da4dc66e416140c9b7f235f9b08fbbcc27fd9df7b586e3150d`. |
| [Exact generation config](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/blob/66285546d2b821cf421d4f5eb2576359d3770cd3/generation_config.json) | Checkpoint has its own sampling defaults; runner never replaces them with invented decoding defaults. Access 14:14:01Z; SHA-256 `533f191cc257b7de37a4fccd0a7a1706d75e1aa660f93efaa54e5a2a9f9aace9`. |
| [Native Qwen2.5 source](https://github.com/huggingface/transformers/blob/5f4ecf2d9f867a1255131d2461d75793c0cf1db2/src/transformers/models/qwen2_5_vl/modeling_qwen2_5_vl.py) | Transformers v4.51.3 resolved through GitHub tag metadata to immutable commit `5f4ecf2d9f867a1255131d2461d75793c0cf1db2`. Constructor stores outer `self.rope_deltas`; forward updates it. Access 14:13:59Z; SHA-256 `72bdd5615b7527543ea7e6d69fbe194c40bddd94cab13e2e83696ff1cfb10719`. |
| [Native processor source](https://github.com/huggingface/transformers/blob/5f4ecf2d9f867a1255131d2461d75793c0cf1db2/src/transformers/models/qwen2_5_vl/processing_qwen2_5_vl.py) | Official image/token expansion and BatchFeature fields; batch_decode delegates to tokenizer. Access 14:14:00Z; SHA-256 `95ec1231f8123e6949dd328e3035e104a335a0701488949aec444410071474cd`. |
| [GenerationMixin source](https://github.com/huggingface/transformers/blob/5f4ecf2d9f867a1255131d2461d75793c0cf1db2/src/transformers/generation/utils.py) | Dynamic cache is call-local model kwargs; setup-cache paths can retain `self._cache`. Decoder-only sequences append to input IDs. Access 14:14:00Z; SHA-256 `dc9044d10c00abe7d341f2e777fb623925ff59dda2c1d814ecc7d6a685ad2ee1`. |
| [qwen-vl-utils 0.0.8 release metadata](https://pypi.org/pypi/qwen-vl-utils/0.0.8/json) | Read `qwen_vl_utils/vision_process.py` from published wheel without installation/execution. PIL input avoids its URL/path branches. Official utility owns smart resizing; still-image calls return one image list and no videos. Wheel SHA-256 verified against PyPI: `2988aa08256f3d7ee6f08d7b27b004e840608b61ed36d0b32d1775be56a1639d`, accessed 14:14:02Z. |

These source versions are documentary audit references, not a runtime environment
freeze. Exact package versions and byte verification remain runtime-prep work.
Local capture and source hashes are under ignored `data/processed/d9r2a_documentary/`;
the table supplies immutable URLs/hashes for independent repeat review.

## Lifecycle and resource contract

The native backend lazily imports torch, Transformers, Pillow, accelerate and
qwen-vl-utils. Injection supplies factories, torch dtype/inference context,
process_vision_info and software versions; unit tests supply fakes only.
Both from_pretrained calls use exact ID/SHA, `local_files_only=True` and
`trust_remote_code=False`. Missing cache entries fail; the runner has no provisioning.

Resource qualification candidate: FP16, NONE quantization, batch 1, one T4 16 GB.
Loader explicitly passes `torch_dtype=torch.float16`, `device_map={"": "cuda:0"}`,
and `attn_implementation="eager"`. Eager is an explicit implementation candidate
that needs no FlashAttention; it is not a claim of T4 fit. Accelerate participates
in this device-map loader path and its actual version is mandatory metadata.
Auto placement, other device requests, extra offload options, mixed parameter
dtypes/devices, CPU/disk buffers, quantized models and multi-device maps fail closed.
Floating buffers may retain native higher precision (e.g. rotary math); FP16 checks
apply to model dtype and parameters. No automatic cast/quantization fallback occurs.
No physical GPU capability/memory probe is performed in this task.

Initialize/load are idempotent under one execution condition. Version mismatches
and incomplete software metadata fail before loading. Processor/model/config are
published only after the whole load validates. Failure permits a later explicit
retry; there is no internal retry, cached exception or partial resource publication.
Execution condition includes ID/revision, runner version, dtype, quantization,
placement, preprocessing, software versions and caller decoding. Any change requires
a new lifecycle; run/call IDs and image/prompt may change between sequential calls.
The runner is for sequential use, not concurrent calls sharing one model.

## Input, generation and independent calls

Exactly one still image is decoded from request bytes with Pillow, fully loaded
and converted to RGB. Malformed/multiframe/decompression-bomb images fail. No URL,
dataset path, temporary image, manual resize or EXIF transpose is used. The only
message is a user message containing the in-memory image and unchanged prompt.
The runner inserts no system/grounding instructions or conversation history;
formatting belongs to the pinned official chat template.

The Qwen2.5 path is `apply_chat_template(tokenize=False, add_generation_prompt=True)`,
then `process_vision_info(messages)`, then
`processor(text=[text], images=..., videos=None, padding=True, return_tensors="pt")`.
No min_pixels/max_pixels overrides. Official utility/processor defaults may resize;
the runner does not implement a second resize policy. Validate one nonempty input
token row, one still-image grid and only the documented image input fields. No
past_key_values, cache_position, video or extra generation fields may enter from
preprocessing. Revalidate prefix and placement immediately before generate.

Independent state policy: `RESET_TOP_LEVEL_ROPE_DELTAS_AND_NATIVE_CACHE_PER_CALL`.
The reviewed Qwen2.5 source has outer `model.rope_deltas`, unlike Qwen3's inner
layout. It is reset before and after each call, including failure; an existing
`_cache` is cleared. Unknown/ambiguous state layouts fail at load. Static/offloaded/
quantized cache configurations and expanded output/beam modes are rejected.
No native KV cache is supplied by the caller or retained by the runner. A future
runtime with a different source layout needs explicit review, not a guessed reset.

Caller decoding supports only temperature, do_sample, top_p, top_k,
max_new_tokens and repetition_penalty with strict types/ranges; no bool-as-int,
nonfinite numbers or unknown keys. Positive temperature is required when supplied;
no zero-to-epsilon rewrite. No defaults are invented. An unapplied seed is rejected.
Checkpoint generation config is snapshotted at load and deep-copied for each call;
native mutation of a call-local config cannot change later calls. Generation runs
inside torch.inference_mode(). Effective config means the inspectable checkpoint
snapshot plus caller overrides **before dispatch**, not an assertion about every
internal library-derived field. Runtime environment/decoding remain unfrozen.

## Raw preservation and adapters

Success envelope: `safeshift-qwen2-5-vl-raw-v1`, strict UTF-8 JSON bytes, containing
backend, exact ID/revision, input token count/IDs, full generated IDs, continuation
IDs, both decoded strings, generation kwargs/effective config, software versions,
input/model devices, actual device map, dtype, runner version and attention backend.
The additional input-token evidence lets the adapter independently validate prefix.

Exactly one generated row of nonnegative integer IDs is required. Its entire
input prefix must match before slicing at input length. Both special-token-preserving
and parser decodes use `clean_up_tokenization_spaces=False`; only
`decoded_for_parser` reaches the existing canonical classification parser.

Failure envelope: `safeshift-qwen2-5-vl-failure-v1`. After native IDs/text become
observable, plain JSON observations are snapshotted before validation/decoding.
Later failures retain available observations in `GenerationFailure(partial_raw=...)`,
including malformed rows, first-decode success or final serialization failure.
No exception message, repr of opaque runtime objects or invented output is included.
If blocking generate raises before observable output, or token materialization
fails without observable IDs/text, partial_raw is None. There is no streamer or
promise to recover native internal tokens that were never returned. Lone-surrogate
text can be preserved losslessly via JSON escapes in the failure envelope.

`execute_call` and `FileRawStore` are unchanged: raw bytes plus provenance must be
persisted before adapter invocation. Preservation failure prevents parsing;
generation failure partial raw is preserved without semantic parsing.
The adapter validates the success envelope and identity/runtime/token consistency.
Classification delegates to `parse_text(text, "classification")`: SUCCESS or INVALID,
without correction, scoring or label selection.

Grounding always returns UNSUPPORTED, SpatialKind.NONE, no canonical value:

```json
{
  "interface_status": "DOCUMENTED_BOX_AND_POINT_PENDING_SYNTHETIC_GATE",
  "d5_box_qualification": "NOT_YET_QUALIFIED",
  "reason": "COORDINATE_OUTPUT_ADAPTER_NOT_YET_FROZEN"
}
```

Raw decoded grounding text remains in the stored envelope. No point-to-box,
coordinate normalization/range assumption, IoU, capability PASS or D5 qualification.
The separate coordinate adapter requires documentary/spatial review first.

## Verification and remaining work

Run using the existing environment, Python 3.11.9 / Pillow 12.3.0:

```powershell
$env:PATH = (Join-Path (Get-Location) '.venv\Scripts') + ';' + $env:PATH
python -m unittest tests.test_qwen2_5_runner -v
python -m unittest discover -s tests
python -m py_compile safeshift/runners/qwen2_5_vl.py
git diff --check
```

Validation: **71/71 runner tests PASS; 654/654 full-suite tests PASS**.
`python -m py_compile safeshift/runners/qwen2_5_vl.py` and `git diff --check`: PASS.
Tests prohibit network and real ML imports; images/output are tiny synthetic fixtures and fakes, with no
random sampling or seed. Native factory selection is tested with mocked imports.
No new dependency is installed. No JSON file changes.

The one extra file beyond the five requested implementation/docs files is
`tests/test_d9_t4_roster_revision.py`: its historical no-new-runner assertion now
permits exactly this authorized D9R2A runner. The 64 protected baseline file hashes,
roster/provenance, old runners/evidence, D5, P1, schema and synthetic assets remain
unchanged. This does not weaken historical file-content checks.

Next steps are separately authorized runtime preparation: select/audit exact package
versions and source layout, provision and verify the pinned snapshot separately,
then a real T4 smoke under pre-specified FP16/NONE/no-offload conditions. Grounding
coordinate review and adapter qualification remain separate pending tasks.
InternVL/Moondream runners remain pending. Checklist #2 overall and #3–#8 PENDING;
`protocol_freeze_commit_sha: PENDING`; **NO_INSPECSAFE_INFERENCE**.

This task performs no model/weight download, GPU, Colab, Kaggle, real model inference,
synthetic gate, InspecSafe inference, performance measurement, prompt tuning, backup
activation or protocol freeze. Census remains untracked/untouched, SHA-256
`cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`.
