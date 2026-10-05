# D9R20 — prospective three-candidate PREP

BASE: `668aae839bbde91b67686d143259e07c8a89608c`, fetched and verified on
2026-10-05 before edits. This task supplies source audit, strict parser candidates,
isolated future runtime paths and synthetic qualification preparation. No model,
GPU, weights or InspecSafe execution. No candidate is an RQ3 participant.

| Model | classification interface | box grounding interface | Call2 compatibility | T4/FP16 | license/access | PREP verdict |
|---|---|---|---|---|---|---|
| Ovis2.5-2B | Conversational/VQA; strict JSON candidate, untested | ref/box; multiple boxes; source-backed strict subset | CALL2_ORCHESTRATION_BLOCKER | Unverified; official BF16; prospective FP16 smoke | Apache-2.0; public | SOURCE_READY_CALL2_BLOCKED |
| PLaMo 2.1-2B-VL | Instruction-tuned VQA; strict JSON candidate, untested | Bare xyxy / repeated exact-label detection lines | CALL2_ORCHESTRATION_BLOCKER | Unverified FP16, Mamba/Triton and memory | ACCESS_REQUIRES_OWNER_ACCEPTANCE | ACCESS_BLOCKED |
| Kosmos-2 | Official VQA/instruction evidence; strict JSON candidate, untested | Official phrase/object/location-token arithmetic | CALL2_ORCHESTRATION_BLOCKER | Plausible, unverified; upstream FP16 path is not T4 proof | MIT; public | SOURCE_READY_CALL2_BLOCKED |

Verdict priority here is access blocker before orchestration blocker; resource
uncertainty is retained independently. None of these verdicts asserts resource
PASS or a production-compatible interface. `SOURCE_READY` refers to the bounded
single-target native subset, not full 12-category production readiness.

## Exact source identity and audit method

| Candidate | immutable HF revision | safetensors bytes (metadata only) |
|---|---|---:|
| ATH-MaaS/Ovis2.5-2B | 393c932b2a03e28eb9aaa503e3c4ab3ad384d958 | 5,140,960,552 |
| pfnet/plamo-2.1-2b-vl | 3d32366444f1ab36e5df4bf7a4c0c0bbe2a56027 | 11,518,321,192 |
| microsoft/kosmos-2-patch14-224 | 1f66d913fde5307936383dc9460b12ccb82f2133 | 6,658,052,808 |

[Source manifest](../configs/pre_freeze/d9r20_sources.v1.json) contains exact URLs,
access date, filename/function locators, SHA256 and byte length of downloaded
small official texts. HF API file records preserve Git blob IDs and LFS
SHA256/size; this is documentary metadata, not local weight-byte verification.
The read-only network audit requests only API metadata and bounded source text,
never model weights, tokenizer payloads, media or remote-code execution.
Downloaded text remains in ignored `.cache/d9r20_sources/`; no upstream source
copies are committed. `scripts/audit_d9r20_sources.py` documents regeneration;
API response hashes are access-time records, because counters/comments may change.

Official implementation pins, separately from checkpoint revisions:

- Transformers **4.57.1**: `8cb5963cc22174954e7dca2c0a3320b7dc2f4edc`.
- Microsoft unilm: `31c5b904ca1bf2afb4c234a6675c683a4e5fc7cd`.
- Mamba **2.3.0**: `f1493ff6e9335160eb134eb67e59f8e4d9adefd6`.
- causal-conv1d **1.6.0**: `da6dbaa9fd5a919967f14d3fd031da1288ad5025`.

## Ovis source contract and limits

[Exact README](https://huggingface.co/ATH-MaaS/Ovis2.5-2B/blob/393c932b2a03e28eb9aaa503e3c4ab3ad384d958/README.md),
Quick Inference and grounding paragraph: conversational image/text path,
official box suffix, `<ref>` target description, `<box>(x1,y1),(x2,y2)</box>`,
top-left origin, x-first coordinates in `[0,1)`, and comma-separated multiple
boxes inside square brackets. Native coordinates enter D4 by identity, without
clamp, reordering, pixel division or guessing. The parser accepts a bare box,
a box list, or one exact target ref immediately followed by either; it rejects
surrounding caption prose, wrong refs, points and malformed structures.
The README's narrative example is broader than this predeclared strict subset:
its prose will fail this candidate, and will not trigger parser adjustment.
Zero/absent serialization is not established.

Loader: `AutoModelForCausalLM`, exact local snapshot, `trust_remote_code=True`;
`model.preprocess_inputs` owns image handling/chat template and
`model.text_tokenizer` owns decoding. Exact revision default image bounds are
`448*448` to `1344*1792` (not the historical 9B wrapper's upper bound).
Thinking and budget are prospectively disabled. Generate returns completion IDs;
the wrapper must not strip a presumed input prefix.

The README pins torch 2.4.0, Transformers 4.51.3, NumPy 1.25.0, Pillow 10.3.0,
MoviePy 1.0.3 and flash-attn 2.7.0.post2; its example loads BF16.
[Exact implementation](https://huggingface.co/ATH-MaaS/Ovis2.5-2B/blob/393c932b2a03e28eb9aaa503e3c4ab3ad384d958/modeling_ovis2_5.py)
has a native vision SDPA branch when FlashAttention is unavailable (attention
forward around lines 269–299). The owner environment deliberately omits flash-attn
before any run; this selects that existing branch, not an exception-driven
fallback. Do not set the whole wrapper's `attn_implementation='sdpa'`: its vision
model advertises `_supports_sdpa=False` even though the local attention branch
uses the torch operation. The FP16 path remains a feasibility hypothesis.
Parameter bytes alone do not establish peak VRAM or numerical stability.

Historical 9B architecture was inspected for local nested asset resolution,
input sentinel handling and raw-before-adapter order. No 9B code/result changed,
no blind runner copy, and its A40/BF16 smoke is not evidence for this 2B/T4 path.

## PLaMo source contract and limits

[Exact README](https://huggingface.co/pfnet/plamo-2.1-2b-vl/blob/3d32366444f1ab36e5df4bf7a4c0c0bbe2a56027/README.md)
Model Description, Requirements, Usage, Visual grounding and Object detection:
instruction-tuned PLaMo base, image/text VQA, single referring-expression bbox,
and repeated `bicycle helmet[...]` lines for multiple instances. Coordinates
are normalized `[xmin,ymin,xmax,ymax]` in `[0,1]` relative to the input image;
minimum x/y denotes upper-left in its image coordinate convention.
The parser accepts either documented bare JSON array or exact target-label lines,
never fuzzy labels, unlabeled lists of lists, trailing prose or unknown lines.
Every parsed instance is retained. No documented empty/absent output contract.

Exact custom code: `modeling_plamo2.py`, `modeling_plamo2_vl.py`,
`processing_plamo2_vl.py`, `tokenization_plamo.py`; their downloaded hashes are in
the manifest. `AutoModelForCausalLM` / `AutoProcessor`, both with
`trust_remote_code=True`. Processor applies the native ja01 template and Eagle2
dynamic tiling (384 nominal tile size, max_tiles=24, tile context 3072), SigLIP
normalization; no manual crop or artificial label-dependent preprocessing.
The tokenizer uses **tokenizer.jsonl**, included in snapshot verification.

Official pins: torch 2.8.0, Transformers 4.57.1, Pillow 12.1.1, mamba_ssm 2.3.0,
causal_conv1d 1.6.0, numba 0.64.0, NumPy 1.26.4. Official config/example use BF16.
`_get_trition_dtype` passes FP16 through; CUDA paths invoke Mamba Triton kernels.
Both pinned extension setup files contain `sm_75` build targets; causal-conv1d's
README explicitly supports FP16. These facts do **not** verify the complete
PLaMo Mamba2/Triton workload on T4. Internal FP32 SSM calculations are native
algorithm behavior; the model parameters must still be FP16 on cuda:0. No dtype,
CPU reference, offload or quantization rescue is implemented. About 11.5 GB of
repository weights is not a measurement of FP16 loaded VRAM; serialized dtype,
activations, tiles, KV/state and allocator overhead all matter. Owner smoke must
measure and record load/OOM/kernel failure without semantic verdict substitution.

The model card says agree to the community license before download and embeds
its terms. API `gated=false` was observed; this does not waive owner acceptance.
No license was accepted by this task. Natural images/VQA/grounding are the stated
focus; OCR, documents, multiple-image input and specialist knowledge are limited.

## Kosmos source contract and limits

[Exact README](https://huggingface.co/microsoft/kosmos-2-patch14-224/blob/1f66d913fde5307936383dc9460b12ccb82f2133/README.md)
documents grounded VQA, phrase grounding, REC and captioning. Exact config names
`Kosmos2ForConditionalGeneration`; official Transformers implementation requires
no model-repository remote code. `AutoProcessor` provides the CLIP image transform
and location-token handling. The HF config records FP32, while the official
unilm demo has an explicit FP16 loading path. Neither establishes single-T4
runtime success; the 6.66 GB safetensors metadata makes a smoke plausible only.
The SafeShift HF environment pins are prospective choices, not an official
complete dependency lock. MIT is documented by HF license metadata and unilm LICENSE.

[Pinned processor](https://github.com/huggingface/transformers/blob/8cb5963cc22174954e7dca2c0a3320b7dc2f4edc/src/transformers/models/kosmos2/processing_kosmos2.py)
`post_process_generation`, `extract_entities_with_patch_indices`, and
`patch_index_to_coordinate`: `<phrase>...</phrase><object>` with pairs of
`<patch_index_NNNN>` tokens, 1024 locations on a 32x32 grid. Multiple pairs use
`</delimiter_of_multi_objects/>`. The pure deterministic candidate conversion
matches official arithmetic: cell centers normally; cell edges when corners
share a row/column, including same cell. Returned boxes are normalized x-first,
upper-left to lower-right. Strict D4 validation rejects invalid/reversed values.
Tokenizer special tokens, full generated IDs, prompt IDs and generation defaults
are retained; downstream processed entities are never called raw.

The strict REC subset binds the unlabelled object continuation to the exact
predeclared prompt phrase; an echoed phrase must match exactly. It does not use
the official broad caption extractor to silently discard prose/unknown entities.
The native processor's square-image preprocessing is only exercised on 256x256
synthetic images; non-square original-image coordinate correspondence is another
production issue to audit before integration, not silently assumed or inverted.

The official project author's comments in
[issue #1186](https://github.com/microsoft/unilm/issues/1186#issuecomment-1632078662)
confirm no negative examples during training/instruction tuning and unreliable
absent-object localization. A [second author comment](https://github.com/microsoft/unilm/issues/1186#issuecomment-1628617454)
reports a tendency toward whole-image boxes for absent phrases. Both comments'
API bytes, URLs, author identity and access-date hashes are recorded. Multiple
boxes have a documented representation; reliable multi-instance recall remains
an unverified performance risk, not an automatic interface rejection.

## Prospective evaluation, without historical reinterpretation

The append-only D9R20 decision implements the owner's requested split:

- A: exact identity, durable native raw before parse, deterministic source-backed
  conversion, canonical validity, target adherence and tracking on mandatory
  sanity cases, human matched-box NO_GIANT review, and production Call2 contract.
- B: classification mistakes, extra/missing boxes, omitted instances, false
  positives and localization quality are fully retained as synthetic diagnostics.
  They do not automatically disprove A. D5 will later penalize performance errors
  for an eligible production participant under its unchanged definitions.

Call1 reuses D9R16's complete policy/JSON prompt and eight exact fixtures. Kosmos
adds its documented Question/Answer wrapper; the semantic task and strict JSON
answer stay identical. No source requires a different classification response
format, and none guarantees JSON compliance. Markdown/prose causes interface failure.

Call2 audit found only a single described target/category with multiple instances
for Ovis/PLaMo, and phrase-grounded free-text entities for Kosmos. None establishes
a sufficiently clear exact multicategory 12-hazard answer mapping in one logical
Call2. Thus all retain `CALL2_ORCHESTRATION_BLOCKER`. No new hazard aliases, GT
selection, classification-conditioned queries or 12-call fan-out. The existing
ordered closed hazard map is referenced unchanged, but no production executor
or mapping is enabled by this PREP.

Owner qualification uses 22 native calls after one load: eight D9R16 cases,
then the twelve v3 synthetic images **all queried for red square**, then the
fixed H_all_four image queried for green circle and cyan rectangle. This is a
new single-target study, not a rerun of Qwen/Pali v3. Extra calls measure target
change on the same synthetic image only; they do not authorize production fan-out.
No GT or expected answer enters the backend. Target-absent B/C/D cases are
diagnostic; no empty response is upgraded to valid zero semantics.

Mandatory sanity evidence is A_1/A_2 (reciprocal position), H red/green/cyan
(changed target, fixed image). All boxes, areas, pairwise target IoUs, center
edges, deterministic one-to-one center matching, missed instances and unmatched
predictions remain in the report. A witness must center in the target, exclude
other target/distractor centers and not be exact full-image. All witness indices
are reported; none is selected as the only canonical output. Human reviewers must
identify coherent tracking witnesses and record NO_GIANT, reviewer and rationale
for the matched boxes. No numerical giant threshold or IoU eligibility threshold.
Automatic observation results never award eligibility/PASS/participation.

## Owner handoff and validation

Runbooks in order: [Ovis](w2_d9r20_ovis_owner_runbook.md),
[PLaMo](w2_d9r20_plamo_owner_runbook.md), [Kosmos](w2_d9r20_kosmos_owner_runbook.md).
Shared lifecycle and authority: [owner workflow](w2_d9r20_owner_workflow.md).
No shared mandatory model environment. Independent snapshot, module cache, run ID,
raw directory, model load and observation/authorization for each model.

Focused tests use fake backends/handcrafted strings. Historical core, Ovis,
classification and v3 parser/runtime regressions are selected separately; exact
commands/results are recorded below after execution. Full suite is not claimed.

`MODEL_GPU_EXECUTION=NO`; `INSPECSAFE=NOT_RUN`; `PROTOCOL_FREEZE=PENDING`;
`WEIGHTS_DOWNLOADED=NO`; `MERGE=NO`. Qwen3 G5 FAIL, PaliGemma G6 FAIL, Moondream,
D9R18 and PR #67 code/history are unchanged; no reruns or promotions.

### Executed offline validation (2026-10-05)

Validation interpreter: existing Python 3.11.9 / Pillow 12.3.0 environment.
The commands below use `python` to denote that interpreter, from the task worktree.
No model libraries were installed or model/GPU CLI actions executed. `--help`
was the only owner CLI invocation outside fake tests.

```text
python -m unittest tests.test_d9r20_candidates -q
python -m unittest tests.test_ovis_runner tests.test_ovis_gpu_smoke_harness tests.test_classification_qualification tests.test_grounding_multicategory_v3 tests.test_grounding_execution_relock_g5 tests.test_grounding_execution_relock_g6 tests.test_qwen2_5_classification_qualification_result tests.test_d9r17b_e_classification_qualification_results -q
python scripts/run_d9r20_candidate.py --help
git diff --check
```

Results: **50 focused PASS**, including all 41 downloaded source-text/API hashes,
official Kosmos arithmetic equivalence, fake loader/environment/snapshot checks,
strict parsers, raw persistence/corruption, bounded bundle, fixed synthetic inputs,
identity/authority, no-promotion and historical/append-only checks; **189 selected
regressions PASS**. Another **40 regressions PASS** from Ovis result + G4 runtime
modules with only the two BASE-reproduced obsolete assertions below excluded.
Total distinct passing tests: **279**. No full-suite run/PASS claim.

The first unfiltered related run had 236 tests, one failure and one error. Both
reproduced independently, unchanged, at a detached exact BASE checkout:

```text
python -m unittest tests.test_ovis_gpu_smoke_result.OvisSmokeResultTests.test_research_claims_grounding_and_checklist_remain_pending tests.test_grounding_multicategory_runtime_v3.ContractTests.test_dry_preflight_blocks_without_authority -q
```

- Ovis historical result assertion expects checklist #2 PENDING; BASE now has
  COMPLETE following later decisions. This is not a new D9R20 result change.
- G4 runtime test expects its old main identity; BASE has advanced, so it raises
  MAIN_IDENTITY_CHANGED_RESEARCH_LEAD_REQUIRED. Its guard is preserved.

The 40-test selection command explicitly names those exclusions and changes no
test file:

```python
import unittest
names = ['tests.test_ovis_gpu_smoke_result', 'tests.test_grounding_multicategory_runtime_v3']
excluded = {
    'tests.test_ovis_gpu_smoke_result.OvisSmokeResultTests.test_research_claims_grounding_and_checklist_remain_pending',
    'tests.test_grounding_multicategory_runtime_v3.ContractTests.test_dry_preflight_blocks_without_authority',
}
def flatten(suite):
    return [t for x in suite for t in (flatten(x) if isinstance(x, unittest.TestSuite) else [x])]
cases = flatten(unittest.defaultTestLoader.loadTestsFromNames(names))
result = unittest.TextTestRunner().run(unittest.TestSuite(t for t in cases if t.id() not in excluded))
raise SystemExit(not result.wasSuccessful())
```

Git diff check PASS. All BASE-tracked paths except appended DECISIONS/TASKS are
unchanged. GitHub read-only verification of PR #67: OPEN/DRAFT, HEAD
`e85300ab3ec122f819a2685613332578f7e203d8`; no update was sent to that PR.
Real T4/environment provisioning, native model outputs, GPU memory feasibility,
strict-output compliance, target tracking and participation remain **NOT RUN**.
