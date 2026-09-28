# W2.6-D9R7 PaliGemma source/API audit

Date: 2026-09-28. Base: `d1ff06d506240df60a19cb094333c9c32e461c73`.
Scope: documentary audit only of `google/paligemma-3b-mix-448` at
`ead2d9a35598cb89119af004f5d023b311d1c4a1`.
The [audit record](../configs/pre_freeze/paligemma_source_api_audit.v1.json)
contains source URLs, versions, locators, access dates, response hashes and limits.

## Result and stop conditions

`ACCESS_EVIDENCE_BLOCKED`. Unauthenticated exact-revision requests for
`config.json`, `preprocessor_config.json`, `tokenizer_config.json`,
`special_tokens_map.json` and `tokenizer.json` returned HTTP 401. Their dependent
audit work stopped. Public README and revision metadata returned HTTP 200.
No credentials, terms acceptance, alternate checkpoint or weights were used.
Access remains `GATED_USAGE_TERMS_ACCEPTANCE_REQUIRED`; owner acceptance remains
`NOT_VERIFIED` in the reviewed context.

**Grammar is not established. Runner preparation is not authorized next.**
Research Lead review is required for the apparent normalization conflict below,
and lawful access to the exact metadata is needed to finish the blocked checks.
No D4 mapping or divisor is selected. The D9R6 precommit remains unchanged,
including `PENDING_DOCUMENTARY_VERIFICATION` and all qualification statuses.

## Exact checkpoint evidence

- The [pinned card](https://huggingface.co/google/paligemma-3b-mix-448/resolve/ead2d9a35598cb89119af004f5d023b311d1c4a1/README.md)
  identifies mix training at 448 x 448 and 512-token text sequences. It describes
  mix models as directly usable for interactive testing. Its code examples
  explicitly use mix-224; they do not verify exact-448 API behavior.
- The [pinned revision API](https://huggingface.co/api/models/google/paligemma-3b-mix-448/revision/ead2d9a35598cb89119af004f5d023b311d1c4a1?blobs=true)
  confirms the SHA, manual gate, Gemma license and architecture
  `PaliGemmaForConditionalGeneration`. It publishes 2,924,351,216 F32 parameters
  in three safetensors shards totaling 11,697,486,320 bytes. These are metadata
  facts, not inspected weight bytes or GPU memory measurements.

## Family/API evidence, not exact-checkpoint qualification

- Official [Google task syntax](https://ai.google.dev/gemma/docs/paligemma/prompt-system-instructions)
  supports `answer en {question}\n`, `detect {object}\n` and the multi-object
  form `detect {object} ; {object}\n`. The pinned upstream
  [big_vision README](https://raw.githubusercontent.com/google-research/big_vision/0127fb6b337ee2a27bf4e54dea79cff176527356/big_vision/configs/proj/paligemma/README.md)
  includes mix-448 in its directly usable mix-family guidance. This supports
  interface feasibility, not a final SafeShift prompt or accuracy claim.
- Transformers v4.57.1 has built-in `PaliGemmaForConditionalGeneration`,
  `GenerationMixin` and `AutoProcessor` mapping to `PaliGemmaProcessor`.
  Model and processor APIs support a local directory and `local_files_only=True`.
  `trust_remote_code=false` remains the required SafeShift boundary, while the
  exact checkpoint's full configuration/overrides remain unverified.
- The [processor source](https://raw.githubusercontent.com/huggingface/transformers/v4.57.1/src/transformers/models/paligemma/processing_paligemma.py)
  adds the trailing newline. A caller should distinguish the documented task
  sequence from processor input text: supplying a newline there adds another.
  It inserts image tokens before BOS/text, using the configured image sequence
  length. Exact length, tokenizer IDs and effective preprocessing are blocked.
- SigLIP source defaults and resize/rescale/normalization stages are catalogued
  only as family evidence. No preprocessing override or crop is selected.
  Explicit FP16 loading is supported by the audited library API (`dtype`, with
  deprecated `torch_dtype` alias); converted FP16 revisions are not selected.

## Coordinate evidence and Research Lead escalation

Family sources construct four-digit tokens `<loc0000>` through `<loc1023>`.
Google's tutorial interprets four coordinates in y-min, x-min, y-max, x-max order
and associates a following label with each regex match, separated by a semicolon.
This does not establish the exact checkpoint's output contract. Empty/no-detection
output is `NOT_DOCUMENTED`; zero regex matches cannot be treated as a documented
empty response.

The [pinned training source](https://raw.githubusercontent.com/google-research/big_vision/0127fb6b337ee2a27bf4e54dea79cff176527356/big_vision/pp/proj/paligemma/segmentation.py)
uses `round(bbox * 1023)` with integer clipping in RefCOCO segmentation encoding.
The official [Google decoding tutorial](https://ai.google.dev/gemma/docs/paligemma/inference-with-keras)
uses division by 1024.0. The tutorial now loads **PaliGemma2/Keras mix-3b-224**;
it is family support only, never a replacement for the selected model. These
different scopes prevent declaring either operation the exact detection mapping.
The apparent mismatch is left unresolved for Research Lead review, as requested.
Token count does not determine a divisor. Training clipping does not authorize
clamping predictions. Malformed output would require parser failure, without
heuristic repair, fabricated boxes, point-to-box conversion or artificial zero IoU.

## Preserved boundaries and validation

PaliGemma remains `BACKUP_1`; the primary roster count remains four. Runtime,
classification, grounding and external gate remain `PENDING_QUALIFICATION`.
Protocol freeze and InspecSafe remain unauthorized. No runner, model import,
GPU, inference, synthetic gate, quantization, offload or fallback was executed.
`DECISIONS.md` and the precommit are unchanged; no new research semantics adopted.

Static validation commands (repository root):

```text
python -m unittest discover -s tests -p test_d9r7_paligemma_source_api_audit.py
python -m unittest discover -s tests -p test_d9r6_paligemma_primary_expansion_precommit.py
python -m unittest discover -s tests -p test_model_provenance.py
python -m unittest discover -s tests -p test_d9_t4_roster_revision.py
git diff --check
```

Validation passed with Python 3.11.9: 12 new audit tests, 10 D9R6 tests, 26 model
provenance tests and 35 current-roster/provenance tests (83 total). All 27
`configs/pre_freeze/*.json` parsed with the repository's stdlib-only `strict_json`
helper; `git diff --check` passed. Runtime checks were intentionally not run
because this task authorizes only documentary/static work.
