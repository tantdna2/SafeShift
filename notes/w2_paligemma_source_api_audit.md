# W2.6-D9R7 PaliGemma source/API audit

Date: 2026-09-28. Same session, branch and draft PR #55.
Base: `d1ff06d506240df60a19cb094333c9c32e461c73`;
continuation starts at `e73da240771402ab768eb84688f5bea78ef2d833`.
Model: `google/paligemma-3b-mix-448` at
`ead2d9a35598cb89119af004f5d023b311d1c4a1`.
The [audit record](../configs/pre_freeze/paligemma_source_api_audit.v1.json)
contains URLs, versions, locators, hashes, access dates and evidence limits.

## Access recheck and exact provenance

Owner explicitly confirmed in this session that they accepted Gemma usage terms
and configured a local Hugging Face credential. Codex did not accept terms.
The initial unauthenticated HTTP 401 observations remain historical evidence.
After owner configuration, authenticated reads of all five requested files
returned HTTP 200. No credential was printed or written to a file/repository.
Only these five metadata files were fetched after credential confirmation.

| Exact pinned file | Bytes | Revision binding |
| --- | ---: | --- |
| config.json | 1,053 | Git blob SHA-1 and X-Repo-Commit match |
| preprocessor_config.json | 700 | Git blob SHA-1 and X-Repo-Commit match |
| tokenizer_config.json | 39,968 | Git blob SHA-1 and X-Repo-Commit match |
| special_tokens_map.json | 607 | Git blob SHA-1 and X-Repo-Commit match |
| tokenizer.json | 17,549,604 | LFS SHA-256 matches exact revision API |

The redirected tokenizer response has no revision header; its full byte hash
matches the pinned API's LFS SHA-256. All five byte sizes also match that API.
No files remain blocked. Acceptance is owner-attested, not inferred from HTTP
success or independently inspected account-consent records. Audit access status
is `OWNER_CONFIRMED_TERMS_ACCEPTED_EXACT_FILES_READABLE`. D9R6 precommit and
historical provenance access fields remain untouched as explicitly requested.

## Exact loader, processor and tokenizer

- Config declares `model_type=paligemma`, architecture
  `PaliGemmaForConditionalGeneration`; text/vision types are `gemma` and
  `siglip_vision_model`. Checkpoint metadata records Transformers `4.41.0.dev0`;
  the documentary library-source audit uses `v4.57.1`, not a frozen environment.
- Both processor/tokenizer config identify `PaliGemmaProcessor`; tokenizer class
  is `GemmaTokenizer`. Transformers has native class/AutoProcessor support.
  None of those three configuration files contains `auto_map`. Remote code is
  not required by this documentary contract; SafeShift keeps
  `trust_remote_code=false`. No loading or runtime verification was performed.
- Exact preprocessing is resize to 448 x 448, resample 3 (bicubic), rescale by
  1/255, then normalize with per-channel mean/std 0.5. Audited slow SigLIP source
  has no crop stage. `do_convert_rgb` is null; no preprocessing override is added.
  Image sequence length is 1,024; `<image>` has ID 257152 and is added/special.
- Exhaustive JSON inspection verifies exactly 1,024 location vocabulary entries:
  `<loc0000>` through `<loc1023>`, with `id = 256000 + integer` (256000..257023).
  They are ordinary BPE `model.vocab` entries, absent from `added_tokens`,
  `added_tokens_decoder` and the special-token declarations. Vocabulary membership
  alone does not prove generated coordinate order or normalization.
- Saved tokenizer flags have BOS=true, EOS=false. Audited PaliGemmaProcessor
  disables automatic BOS/EOS and constructs its own BOS/image prefix and trailing
  newline. The family task forms remain `answer en {question}\n` and
  `detect {object}\n`; no final SafeShift classification prompt is designed.

The exact card/API weight facts are unchanged: 2,924,351,216 F32 parameters,
three safetensors shards, 11,697,486,320 published bytes. Explicit FP16 loading
has library API support; no converted revision or weights were fetched.

## Narrow PaliGemma 1 object-detection pass

Before credential setup, the authorized source pass inspected pinned official
Space sources and big_vision preprocessing ops as text only. The exact card's
How to Use section links the [Transformers demo source](https://huggingface.co/spaces/big-vision/paligemma-hf/blob/d914d4446a6ff8c5b3110411abca69887f035c41/app.py).
It names `google/paligemma-3b-mix-448`, includes a `detect bee` example and uses
`extract_objs`: four location integers in y-min, x-min, y-max, x-max order,
divided by 1024, then scaled/rounded to image pixels for visualization.
The model revision is **not pinned** in that demo. This is official PaliGemma 1
detection evidence, not an execution result or exact-checkpoint binding.
The companion [big_vision demo parser](https://huggingface.co/spaces/big-vision/paligemma/blob/b19d492be08ec5e8aad190a522db919d4444f529/paligemma_parse.py)
agrees; its model configuration covers PaliGemma 1 mix-224/mix-448 JAX models.
These were inspected only as supporting source; no checkpoint was substituted.

No corresponding bbox-to-location **detection encoder** was found in the narrow
pass (demo detection paths, PaliGemma preprocessing ops and repository tree).
This is a bounded negative finding, not a claim that no such source exists.
The [RefCOCO encoding source](https://github.com/google-research/big_vision/blob/0127fb6b337ee2a27bf4e54dea79cff176527356/big_vision/pp/proj/paligemma/segmentation.py)
uses `round(bbox * 1023)` and clipping, with scope **SEGMENTATION_ONLY**.
The earlier [Google tutorial](https://ai.google.dev/gemma/docs/paligemma/inference-with-keras)
uses division by 1024 but currently demonstrates PaliGemma2/Keras; it remains
family evidence only. PaliGemma 1's /1024 decoding is now independently sourced.

Normalization outcome: **UNRESOLVED_SCOPE_CONFLICT**. The detection visualization
rule is verified, but its training encoder and linkage to this immutable model
revision are not. It cannot establish an inverse of segmentation encoding or
silently settle the requested end-to-end conversion. `selected_divisor=null`;
canonical conversion is **BLOCKED** pending Research Lead resolution. No mapping,
clamp or heuristic repair is proposed. Training clipping does not permit repairing
predictions; malformed output would require parser failure.

Multi-box parsing remains **FAMILY_LEVEL_ONLY**: the demo regex associates each
four-token box with its following label, with optional semicolon-space separation.
It is permissive and permits unrelated text; it is not a strict output contract.
Empty/no-detection behavior remains **NOT_DOCUMENTED**. No-match parser behavior
is not evidence of a valid empty model response.

## Preserved boundaries and static validation

Runner preparation is **not authorized next**, independently of documentary
progress. PaliGemma stays BACKUP_1; primary count stays four. Runtime,
classification, grounding and external gate remain PENDING_QUALIFICATION.
D9R6 precommit, DECISIONS, roster and provenance are unchanged. No weights,
model import/load, GPU, inference, synthetic gate, InspecSafe, protocol freeze
or merge. The only changes are this note, audit JSON, tests and TASKS.

Static commands (repository root):

```text
python -m unittest discover -s tests -p test_d9r7_paligemma_source_api_audit.py
python -m unittest discover -s tests -p test_d9r6_paligemma_primary_expansion_precommit.py
python -m unittest discover -s tests -p test_model_provenance.py
python -m unittest discover -s tests -p test_d9_t4_roster_revision.py
git diff --check
```

Validation passed with Python 3.11.9: 15 D9R7 tests, 10 D9R6 regression tests,
26 provenance tests and 35 roster tests (86 total). All 27 pre-freeze JSON files
parsed with the stdlib-only `strict_json` helper; `git diff --check` passed.
Runtime checks are intentionally not run because only documentary/static work
is authorized.
