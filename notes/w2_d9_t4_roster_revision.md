# W2.6-D9R1 — T4 resource feasibility roster revision

This revises DEC-W2-D9-009 before protocol freeze and before any InspecSafe
inference, under the Research Lead's explicit D9R1 instruction. Reason:
`PRE_FREEZE_RESOURCE_CONSTRAINT`. No InspecSafe performance informed selection.
Base main: `36b934b37ff064bb097860f0a0aef43897938a64`.
Branch: `decision/d9-t4-roster-revision`. Decision/config/provenance scope only.

The practical target is free Colab single NVIDIA T4 16 GB, with Kaggle T4-class
fallback allowed. Paid GPU rental is not required by policy. Qwen3 alone retains
its already audited Kaggle T4×2 exception. Published parameter/file sizes below
are documentary metadata, not evidence of runtime memory fit.

## Current primary roster

| Key / model | Immutable revision | Role | Documentary / offline runner / real runtime |
|---|---|---|---|
| `qwen3_vl_8b_instruct` — `Qwen/Qwen3-VL-8B-Instruct` | `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` | `ANCHOR_REPRODUCTION_BRIDGE`; `KAGGLE_T4X2_VALIDATED_ANCHOR` | COMPLETE / COMPLETE / PASS_VALIDATED, historical Kaggle T4×2 smoke |
| `qwen2_5_vl_3b_instruct` — `Qwen/Qwen2.5-VL-3B-Instruct` | `66285546d2b821cf421d4f5eb2576359d3770cd3` | `RESOURCE_EFFICIENT_QWEN_CONTRAST` | COMPLETE / PENDING / PENDING |
| `internvl3_2b_hf` — `OpenGVLab/InternVL3-2B-hf` | `cb57a075cb75a2e6d1b668b128d48bb00ae321d2` | `INDEPENDENT_INTERNVL_FAMILY` | COMPLETE / PENDING / PENDING |
| `moondream2_2025_06_21` — `vikhyatk/moondream2` | `9a7d4024050840e001defacec2b00727e89149e6` | `INDEPENDENT_SMALL_VLM_WITH_NATIVE_SPATIAL_APIS` | COMPLETE / PENDING / PENDING |

All three new primaries remain classification `CANDIDATE` and
`T4_FEASIBILITY_CANDIDATE`; none is T4/Colab/Kaggle validated. Their validation
targets are `COLAB_T4_1X16GB_PRIMARY` and `KAGGLE_T4_FALLBACK_ALLOWED`.
Qwen3 retains the link to the upstream/original benchmark; Qwen2.5 is a
resource-efficient contrast, not the upstream baseline replacement. P1 reproduction
policy remains unchanged. SafeShift extended metrics must not be attributed to
the original paper unless that paper reports them.

## Exact documentary evidence and limits

Resolved via unauthenticated Hugging Face model/revision API, then compared with
the immutable revision API (`?blobs=true`). Per-request UTC timestamps, URLs and
response SHA-256 are in [provenance](../configs/pre_freeze/local_model_provenance.d9.json).
Only small cards, licenses, metadata and source text were retrieved. No remote code
was imported or executed; no weight response body was fetched. Qwen's 13 required
files resolved with HTTP HEAD 200, including both weight shards; HEAD is metadata
verification, not local weight-byte verification.

- **Qwen2.5:** the [pinned LICENSE](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/blob/66285546d2b821cf421d4f5eb2576359d3770cd3/LICENSE)
  is **Qwen Research License**, with non-commercial research/evaluation conditions.
  Later Apache metadata is not transferred to this revision. The
  [exact card](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/blob/66285546d2b821cf421d4f5eb2576359d3770cd3/README.md)
  documents box/point coordinate JSON: `DOCUMENTED_BOX_AND_POINT`,
  `PENDING_SYNTHETIC_GATE`. Coordinate grammar/adapter remain to be qualified.
- **InternVL:** the [exact HF card](https://huggingface.co/OpenGVLab/InternVL3-2B-hf/blob/cb57a075cb75a2e6d1b668b128d48bb00ae321d2/README.md)
  says MIT for the project and Qwen License for the Qwen2.5 component; metadata is
  `other / qwen`. Its upstream component-license link is mutable and is recorded
  as such. This is not an MIT-only or Apache checkpoint clearance. The native HF
  `AutoModelForImageTextToText` interface has no clearly documented coordinate
  output contract in the reviewed exact card/config, so grounding remains
  `NOT_YET_DOCUMENTARILY_QUALIFIED`. Tokens and paper benchmarks do not promote it.
- **Moondream:** the [tag-resolution API](https://huggingface.co/api/models/vikhyatk/moondream2/revision/2025-06-21?blobs=true)
  resolves `2025-06-21` to `9a7d4024050840e001defacec2b00727e89149e6`.
  The [release card](https://huggingface.co/vikhyatk/moondream2/blob/9a7d4024050840e001defacec2b00727e89149e6/README.md)
  declares Apache-2.0 and explicitly documents `model.detect(...)` and
  `model.point(...)`: `DOCUMENTED_NATIVE_DETECT_AND_POINT`, `PENDING_SYNTHETIC_GATE`.
  This does not establish D5 PASS. Pinned remote code defaults to BF16 internally
  and references an unpinned `moondream/starmie-v1` tokenizer; a future runner must
  resolve that dependency and inspect explicit FP16 conversion/cache behavior.

Qwen2.5 and InternVL publish BF16 tensors and show auto/BF16 recipes. FP16 is a
SafeShift qualification candidate via the explicit dtype interface, not documentary
proof of successful T4 execution. No automatic BF16/quantized fallback is allowed.

## Ordered backups and historical roster

1. `google/paligemma-3b-mix-448` at
   `ead2d9a35598cb89119af004f5d023b311d1c4a1`, classification candidate,
   `T4_FEASIBILITY_CANDIDATE`, `GATED_USAGE_TERMS_ACCEPTANCE_REQUIRED`.
   The [exact rendered card](https://huggingface.co/google/paligemma-3b-mix-448/blob/ead2d9a35598cb89119af004f5d023b311d1c4a1/README.md)
   and API identify Gemma terms; the card specifies research purposes. Owner
   acceptance is NOT_VERIFIED; unauthenticated raw config/card requests return 401.
   The card documents float32/BF16/FP16 formats and object detection/segmentation.
   Selected HEAD has F32 tensors; converted dtype branches are separate revisions,
   not selected here. Explicit FP16 load/cast remains a candidate. Card code uses
   the 224 variant, so it is family guidance, not exact-448 runtime validation.
   Reviewed documentation does not qualify an exact native coordinate grammar.
2. `HuggingFaceTB/SmolVLM2-2.2B-Instruct` at
   `482adb537c021c86670beed01cd58990d01e72e4`, classification candidate,
   `T4_FEASIBILITY_CANDIDATE`. The [exact card](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct/blob/482adb537c021c86670beed01cd58990d01e72e4/README.md)
   specifies Apache-2.0. API metadata reports 2,246,784,880 parameters, F32 tensors.
   Its BF16/Flash Attention example and advertised memory figure are not SafeShift
   T4 validation. Grounding is `NOT_YET_DOCUMENTARILY_QUALIFIED`.

Explicit retired records preserve the old IDs, pins and documentary status:

| Historical model | Immutable revision | Preserved work |
|---|---|---|
| `AIDC-AI/Ovis2.5-9B` | `d73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd` | Offline COMPLETE; single-A40 runtime PASS / VALIDATED; box/point documentary evidence; code/config/notes/results preserved |
| `allenai/Molmo2-O-7B` | `784410650d12be9bc086118fdefa32d2c3bced86` | Offline COMPLETE; native-point evidence; real runtime NOT_RUN; B3B-PREP exists separately on PR #28 |
| `google/gemma-4-12B-it` | `707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7` | Retired before runner/runtime completion; documentary history preserved |
| `google/paligemma2-10b-mix-448` | `b26d16fb4251090ba4a4aa5af9fca1f8248ed5b6` | Historical backup 1; license/access and grounding documentation preserved |
| `openbmb/MiniCPM-V-4.6` | `36f34a661a4bd35d0dc2294cb044d2584646c7d3` | Historical backup 2; documentary history preserved |

All five are `RETIRED_PRE_FREEZE`, reason `PRE_FREEZE_RESOURCE_CONSTRAINT`,
`replacement_selection_used_inspecsafe_results: false`; none is current primary.
Original B0 provenance records retain their historical roster_group/order and
unresolved-item wording. The revision's explicit active key lists and local roster
are authoritative for current membership; later Qwen/Ovis smoke records remain
the authoritative runtime evidence. No old runner or evidence is deleted.

[PR #28](https://github.com/tantdna2/SafeShift/pull/28) was independently observed
OPEN, draft, unmerged, at head `2d9214eda1843f34e782f25227faff586ee1afc0`.
It remains untouched. Close-as-superseded may be considered **only after** this
roster revision is merged; this task neither merges nor closes either PR.

## Qualification and unchanged protocol

New primary candidates and activated backups must qualify on **one NVIDIA T4
16 GB, FP16 candidate, no quantization, batch size 1**, with CPU/disk offload
forbidden. Automatic precision/quantization fallback is forbidden. Kaggle is an
allowed fallback venue; it does not waive the single-T4 requirement for new
primaries. Qwen3 is the sole T4×2 exception with audited evidence. Only a documented
failure of the pre-specified resource qualification permits resource-based backup
consideration before freeze and before InspecSafe, with the same prerequisites.
Other D9 objective access/classification blockers remain explicit in the unchanged
replacement policy. Grounding-only failure never triggers substitution or zero IoU.
Model substitution after InspecSafe is forbidden. Research precision, decoding
and prompts are not frozen by this qualification policy.

D5 is unchanged: Balanced Accuracy, Macro-F1, FPR/FNR policy and Level01
safety-critical metrics; Class-Conditional Recall, Pooled-to-domain Gap/Drop and
Comparable-domain diagnostics; Mean/Median IoU, Hit@0.25/0.50 and Evidence
Precision/Recall/F1. Classification-Grounding consistency policy and the term
**Classification-Grounding Inconsistency** remain unchanged. Full-dataset Object
Hallucination Rate and Correct-Answer-Wrong-Reason are not reinstated as valid metrics.
Dataset, split, labels, canonical schema and P1 reproduction policy do not change.

Checklist #1 documentary COMPLETE; #2 overall PENDING; #3–#8 PENDING.
`protocol_freeze_commit_sha: PENDING`; InspecSafe inference remains unauthorized.
SYNTHETIC V1 manifest/assets are unchanged; manifest SHA-256:
`fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379`.
Census remains untracked and untouched, SHA-256:
`cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`.

## Validation and reproducibility

Metadata capture: unauthenticated Python standard-library HTTPS GET for revision
API/cards/config/license, HEAD only for Qwen required-file resolution. No random
sampling; seed not applicable. Small source response hashes/timestamps and artifact
size/LFS metadata are versioned in provenance. Local documentary capture under
`data/processed/d9r1_documentary/` is ignored; it contains no model weights.
No dependency changes. The Git commit containing this note identifies this revision.

Offline validation commands (PowerShell uses `Out-Null` instead of `/dev/null`):

```powershell
$env:PATH = (Join-Path (Get-Location) '.venv\Scripts') + ';' + $env:PATH
python -m unittest tests.test_d9_t4_roster_revision -v
python -m unittest discover -s tests
python -m json.tool configs/pre_freeze/local_models.d9.json | Out-Null
python -m json.tool configs/pre_freeze/local_model_provenance.d9.json | Out-Null
python -m json.tool configs/pre_freeze/freeze_manifest.d9.template.json | Out-Null
git diff --check
```

Validation: **32/32 D9R1 tests PASS; 583/583 full-suite tests PASS** in the existing
`.venv` (Python 3.11.9, Pillow 12.3.0). All three JSON validations and
`git diff --check` PASS. Initial system-Python discovery could not import Pillow;
the complete suite was rerun successfully with the existing environment, without
installation or network. Protected text comparisons normalize Git checkout CRLF
to LF; image and census checks retain exact byte hashing. The 64-file baseline
fixture was generated from exact base Git blobs, not mutable metadata or weights.

No model/weight download, GPU, real inference, synthetic gate execution, InspecSafe
inference, scoring or prompt tuning occurred. Unit tests use synthetic fixtures/fake
backends; they do not execute the model qualification gate. No network was used
during the test phase. PR #28 remains historical pending work.
