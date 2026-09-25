# W2.6-D9R2C-GATE-RESULT — Audited frozen box-interface gate failure

**GATE_FAIL: eight cases completed, zero valid canonical boxes.** Research Lead
directly inspected and rehashed the real bundle. This task records those supplied
audit findings; the recording agent did not independently receive/rehash the
bundle or rerun the model. Bundle and raw bytes remain outside Git.

The [machine-readable result](../configs/pre_freeze/qwen2_5_external_gate_result.v1.json)
contains the eight exact raw hashes, strict statuses, resource condition and pins.

| Field | Audited value |
|---|---|
| Run ID | `kaggle-t4-qwen25-external-gate-20260925T092550Z-c1c1d8` |
| Execution commit / recording base | `c08fe8420fe0189b8776741eaa5cc2fb945a77fa` |
| Bundle SHA-256 | `1cea70eaa173efeb594a5c5159b7661362d45fe1f87007b51a9957d16643e6e8` |
| Original summary.json SHA-256 | `bf2b4a96d9cfb1fb4a89972c155cf0f026f0d213d61c9e4ee9be1144e6ed7155` |
| Gate plan canonical SHA-256 | `d7e09c1400e23a534b97e91aa432d87108ece137ff60f8a918e3c0f977f2bb4b` |
| Runtime plan canonical SHA-256 | `aa4fcff85d670d844025a540d85f10514919c60f6709de8be8f6be0922fd63fb` |
| Manifest SHA-256 | `fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379` |
| Provenance SHA-256 | `0b16be7408784c35bc3dc1a541f008b8086c4fa250957082a236d71ed3fe2e96` |

The execution commit identifies the code that ran; this result-recording commit
does not replace it. The original summary hash does not hash the new transcription.
The model remains `Qwen/Qwen2.5-VL-3B-Instruct`, revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`, under the pinned single Tesla T4 /
FP16 / SDPA / NONE / batch 1 / cuda:0 condition, no CPU/disk offload, pixel caps
200704/1003520. No additional hardware telemetry is inferred for this gate run.

## Complete execution and strict results

Exactly eight native generations completed in order A_1, A_2, B_1, B_2, C_1,
C_2, D_1, D_2. Native errors and unattempted-case lists are empty. Execution
failure: **NONE**; OOM: **NOT_OBSERVED**. This is a completed gate failure,
not a runtime/resource failure or pending-review result.

| Cases | Strict parse status | Count |
|---|---|---:|
| A_1, B_1 | SCHEMA_ERROR | 2 |
| A_2, B_2, C_1, C_2, D_1, D_2 | JSON_ERROR | 6 |
| None | SUCCESS / valid canonical bbox | 0 |

`gate.status=FAIL`, `systematic_tracking=false`, with error
`predictions do not track systematic target positions`. With no valid canonical
boxes, this evaluator result is not evidence of a separate measured tracking
accuracy. No numeric grounding score or artificial zero IoU is assigned.

Approved interpretation: **Qwen2.5 failed the frozen SafeShift qualifying
box-interface external gate under the pre-specified prompt, decoding and strict
parser.** Some native outputs appear to contain spatial coordinates, but use a
schema/coordinate convention that does not meet the frozen canonical contract.
A_1 used bbox_2d + label; B_1 used bbox_2d. This does not establish a general
inability to localize. Raw outputs remain primary evidence; none is repaired.

Some calls reached 32 continuation tokens and were truncated (no per-case counts
were supplied). This does not authorize increasing the output limit after seeing
results. `do_sample=false, max_new_tokens=32`, target queries, prompt/version,
coordinate instructions, strict parser and production adapter remain unchanged.
No fence stripping, bbox_2d renaming, label removal, coordinate normalization or
reordering, native-coordinate adapter, decoding reselection or rerun occurred.

## Role policy and review boundary

The active roster changes Qwen2.5 grounding from
`DOCUMENTED_BOX_AND_POINT_PENDING_SYNTHETIC_GATE` to **NOT_PARTICIPATING**,
reason **SPATIAL_GATE_FAILURE**, with this evidence linked. Documentary box/point
support remains historical evidence. Resource status remains **PASS_VALIDATED**;
classification remains **CANDIDATE**, without a capability pass or failure claim.

This follows the existing D9 grounding/nonparticipation vocabulary and no
grounding-only substitution policy in [DEC-W2-D9-009](../DECISIONS.md) and
`local_models.d9.json#replacement_policy`. The policy's valid-classification
condition is not claimed proven by this spatial run. This task's explicit
Research Lead instruction retains classification CANDIDATE. No backup substitution
and no artificial zero IoU; no metric, dataset or policy definition changes.

**GIANT_BOX_REVIEW: NOT_REQUIRED_AFTER_AUTOMATIC_GATE_FAILURE.** Automatic checks
already failed with 0/8 canonical boxes, so no human giant-box review is performed.
No equivalent workflow term was found; this records review applicability without
extending `GiantBoxReview`'s NO_GIANT/GIANT/PENDING enum or fabricating reviews.

The global D9 gate status is **PENDING**, not COMPLETE: other primaries remain
unresolved. Its old NOT_RUN_FOR_D9_MODELS label is superseded by this first recorded
model gate result. Checklist #2–#8 and `protocol_freeze_commit_sha` stay PENDING;
InspecSafe remains **NOT_RUN**, authorization **false**. Earlier PREP/qualification
notes and immutable plans preserve their historical milestone states.

Recording only: no GPU, model load/download/inference, gate rerun, human review,
InspecSafe, protocol freeze, prompt/decoding tuning, parser repair or adapter promotion.

## Recording-task validation

Offline result/roster/provenance tests: **67 PASS** (including **8 new result
tests**). Full suite: **794 PASS**. Both changed JSON files validate;
`git diff --check` PASS. Gate/runtime canonical plan hashes match the pins above;
all protected production files and frozen assets are unchanged against exact base.
Census remains untracked/untouched with SHA-256
`cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`.
These are local checks; remote CI status is **NOT_VERIFIED**, not CI_PASS.
