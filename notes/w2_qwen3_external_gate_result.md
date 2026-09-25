# W2.6-D9R2D-QWEN3-GATE-RESULT — Audited frozen box-interface gate failure

**GATE_FAIL: real execution completed with five canonical valid boxes out of
eight cases.** Research Lead directly inspected the bundle and rehashed its
artifacts. This task transcribes the supplied audit findings; the recording agent
did not independently receive/rehash the bundle or rerun the model. Bundle/raw
bytes remain outside Git. Small supplied decoded excerpts below are audit
transcriptions, not reconstructed raw envelopes.

The [machine-readable result](../configs/pre_freeze/qwen3_external_gate_result.v1.json)
records every exact raw hash, strict status, supplied bbox/geometry observation,
resource contract and role outcome.

| Field | Audited value |
|---|---|
| Run ID | `kaggle-t4x2-qwen3-external-gate-20260925T175057Z-08fe69` |
| Execution commit / recording base | `23556cf3f0adc93b76075a3247a18dd4686ff87a` |
| Bundle SHA-256 | `4d7429ef729c22889af7763e6d9b5c3fd753169c51b9d8c0999d81da9a23a97c` |
| Original summary.json SHA-256 | `e2f77bebbd5b79674b608f748e5987feec3f0f0381f8aea9be38630db4814f24` |
| Gate plan SHA-256, exact bytes | `c7510570f553f3267e65f751b56193a337d3c370dd5c4db45da4d746711888c4` |
| Runtime smoke plan SHA-256, LF bytes | `ecd34ba5a8880458734e26f2bf0932f5f820607c2b9f3233b4e092980bf79ef9` |
| Frozen manifest SHA-256 | `fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379` |
| Frozen provenance SHA-256 | `0b16be7408784c35bc3dc1a541f008b8086c4fa250957082a236d71ed3fe2e96` |

The execution commit identifies the real run; the recording commit does not
replace it. The original summary hash is not a hash of this transcription.
Model: `Qwen/Qwen3-VL-8B-Instruct`, revision
`0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`. The unchanged pinned condition is
KAGGLE / T4_X2 / FP16 / NONE / placement `auto` / `official_processor` /
attention `native_default` / Transformers 4.57.1. No additional hardware telemetry
is inferred from the supplied findings. Prompt version remains
`external-target-draft-v1`; decoding remains `do_sample=false, max_new_tokens=32`.

## Completed execution and strict results

One initialize, one load and exactly eight sequential native generations completed
in the frozen order below. Native errors and unattempted-case lists are empty.
Execution failure: **NONE**. No runtime failure or resource failure; OOM:
**NOT_OBSERVED**. The result is **GATE_FAIL**, automatic status **FAIL**, not
PENDING_REVIEW. `systematic_tracking=false`; gate error:
`predictions do not track systematic target positions`.

| Case | Strict status | Canonical parsed bbox | IoU diagnostic |
|---|---|---|---:|
| A_1 | COORDINATE_ERROR | None | Not supplied |
| A_2 | SUCCESS | [0.5, 0.25, 0.75, 0.75] | 0.2 |
| B_1 | SUCCESS | [0.37, 0.12, 0.63, 0.38] | 0.9245562130177516 |
| B_2 | SUCCESS | [0.35, 0.62, 0.65, 0.92] | 0.6944444444444443 |
| C_1 | SUCCESS | [0.0, 0.0, 0.33, 0.33] | 0.3248309178743962 |
| C_2 | SCHEMA_ERROR | None | Not supplied |
| D_1 | SUCCESS | [0.44, 0.07, 0.81, 0.25] | 0.22750252780586458 |
| D_2 | COORDINATE_ERROR | None | Not supplied |

Counts: **5 SUCCESS / canonical valid boxes, 2 COORDINATE_ERROR,
1 SCHEMA_ERROR, 0 JSON_ERROR**. All five valid cases have
`center_in_target=true` and `excludes_distractor_center=true` per the audit.
IoU remains **DIAGNOSTIC ONLY**: no threshold rescues or fails a case. Area also
remains diagnostic only. No aggregate score or artificial zero IoU is assigned.
The tracking flag is the existing gate outcome with three invalid cases; it is
not a separate measured tracking-accuracy claim.

## Interpretation and parser boundary

Approved interpretation: **Qwen3-VL-8B failed the frozen SafeShift qualifying
box-interface external gate under the pre-specified prompt, decoding and existing
parser.** Five of eight cases produced canonical valid boxes. This does not
establish a general inability to localize or absence of grounding capability.

Exact supplied `decoded_for_parser` for the three invalid cases:

```text
A_1: {"bbox": [36, 125, 168, 468]}
C_2: {"bbox": [0.5, 0.6, 1.0, 0.9], "label": "yellow triangle"}
D_2: {"bbox": [36, 537, 260, 771]}
```

A_1 and D_2 contain bbox values outside the required [0,1] interface convention.
They may resemble another coordinate scale; no native convention is inferred,
and no post-hoc conversion is justified or performed. The frozen production
parser retains **xyxy_1 -> clamp [0,1] -> geometry validation**. Those values
clamp to degenerate geometry and yield COORDINATE_ERROR under that existing
behavior. There is no switch to xyxy_1000, division by 1000, coordinate repair,
or replay with another convention.

C_2 is otherwise bbox-like but has an extra root `label` field, which violates
the frozen external_probe schema. The field is not removed or newly allowed.
Success-case decoded strings were not supplied and are not invented from parsed
boxes. No prompt/target_query/schema/parser/coordinate convention, output limit,
decoding, placement, precision, production adapter or plan is changed. No stripping,
repair, model/gate rerun, output-based tuning or adapter promotion occurred.

## Role policy and review boundary

The Qwen3 roster grounding role changes from
**DOC_SUPPORTED_PENDING_SYNTHETIC_GATE** to **NOT_PARTICIPATING**, reason
**SPATIAL_GATE_FAILURE**, with the audited result linked. Classification remains
**CANDIDATE** and continues; resource role remains
**KAGGLE_T4X2_VALIDATED_ANCHOR**, runtime **PASS_VALIDATED**, offline runner
**COMPLETE**, and anchor role **ANCHOR_REPRODUCTION_BRIDGE**.

The current `local_models.d9.json#replacement_policy` explicitly includes
SPATIAL_GATE_FAILURE in grounding-only nonparticipation. No backup substitution
and no artificial zero IoU. The policy's valid-classification condition is not a
capability claim established by this spatial run; Research Lead's instruction
explicitly retains classification CANDIDATE. No policy, metric, dataset or split
definition is changed.

**GIANT_BOX_REVIEW: NOT_REQUIRED_AFTER_AUTOMATIC_GATE_FAILURE.** Automatic gate
criteria already failed, so no human giant-box review is performed and no
NO_GIANT review is fabricated. This applicability status does not extend the
production GiantBoxReview enum.

Global D9 synthetic gate remains **PENDING** because other primary candidates
are unresolved. Checklist #2–#8 and `protocol_freeze_commit_sha` remain
**PENDING**. InspecSafe remains **NOT_RUN**, authorization **false**. Immutable
plans and the PREP note retain their historical pre-execution milestones.

Recording only: no GPU, model load/inference/download, gate rerun, human review,
InspecSafe, protocol freeze, prompt/decoding tuning, coordinate conversion,
parser repair or adapter promotion.

## Recording-task validation

Relevant result/roster/smoke-result checks: **64 PASS**, including **13 new result
tests**. Full suite: **863/863 PASS** with
`.venv/Scripts/python.exe -m unittest discover -s tests`.
Both changed JSON configs validate with the existing strict JSON loader;
`git diff --check` PASS. All 24 protected source/config/fixture paths are unchanged
against exact recording base. Census remains untracked/untouched with SHA-256
`cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`.
Offline checks validate transcription/immutability; they do not independently
audit unavailable bundle bytes or establish remote CI_PASS.
