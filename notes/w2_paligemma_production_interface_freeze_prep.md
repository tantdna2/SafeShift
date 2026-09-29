# D9R13 — PaliGemma production interface freeze preparation

Base main: `a3192ddefbc28fe2997190819744e8f4796a6d85` (PR #59 merged).
New task, PREP / implementation only. The
[machine-readable candidate](../configs/pre_freeze/paligemma_production_interface_candidate.v1.json)
is a requirements/proposal record, not an activated adapter or frozen interface.

**SYNTHETIC_GATE_READY=false. ADDITIONAL_RUNTIME_QUALIFICATION_REQUIRED=true.**
The exact checkpoint remains `google/paligemma-3b-mix-448` at
`ead2d9a35598cb89119af004f5d023b311d1c4a1`.

## Canonical authority and actual primary adapters

This audit uses tracked repository contracts at the base SHA, without inspecting
InspecSafe images/annotations or the local untracked census. The authorities are
[prompt builders](../safeshift/protocol/prompts.py),
[Python schema](../safeshift/protocol/schema.py),
[JSON Schema](../schemas/canonical.schema.json),
[runner contract](../safeshift/runners/contracts.py),
[metric consumers](../safeshift/protocol/metrics.py), and DEC-W2-D4/D5/D8/D9 in
[DECISIONS](../DECISIONS.md). Prompt versions remain drafts; no freeze is implied.

| Task | Input and semantics | Canonical output / consumer |
| --- | --- | --- |
| P2 Call 1 | C1: one image plus caller-supplied industry safety policy; no Call 2 output | Exactly `{"safety_level":"Level01"}` or Level02/03/04; `Classification(safety_level)` |
| P2 Call 2 | A2/B2: independently inspect one image for the entire fixed 12-hazard vocabulary; no Call 1 predictions or GT target selection | `{"hazards":[{"hazard_type":"<B2 ID>","evidence":[{"bbox":[xmin,ymin,xmax,ymax],"label":"<optional string>"}]}]}`; `Grounding` |
| External probe | Manifest `ExternalCase.target_query`; not Call 2 hazard discovery | Exactly `{"bbox":[xmin,ymin,xmax,ymax]}`; `ProbePrediction` |

Call 1 is four-class, single-label classification. Binary anomaly and Level01
one-vs-rest are **derived D5 metric tracks**, not native binary tasks. There is
no canonical abstention label, multilabel safety output, `safe`, or `unsafe`.
The parser rejects malformed/unknown labels with JSON_ERROR/SCHEMA_ERROR;
the runner exposes INVALID, null canonical value and INVALID_CLASSIFICATION_OUTPUT.
`ClassificationInput` carries `true_safety_level` and the parsed prediction.
The D5 metric engine is still NOT_IMPLEMENTED. The synthetic gate does not score
classification at all; C1 qualification remains a separate precommit prerequisite.

Actual primary adapters do not provide a hidden alternative classification
contract:

- `Qwen3VLAdapter` and `Qwen2_5VLAdapter` validate their native envelopes and call
  `parse_text(decoded_for_parser, "classification")`. They return
  `AdaptedOutput(SUCCESS, Classification(...))` or INVALID/null. Their production
  grounding adapters still return UNSUPPORTED.
- `PendingInternVL3Adapter` and `PendingMoondreamAdapter` return classification
  INVALID/null and grounding UNSUPPORTED/null. Moondream's separately qualified
  detect gate is not a production B2 hazard adapter.

Call 2 hazard IDs are exactly the `HAZARDS` tuple in schema.py. Multiple hazards
and evidence boxes are representable; all claims, including unmatched ones, must
reach metric consumers. Optional `Evidence.label` is string metadata, not the
closed `hazard_type`. A detected person cannot be turned into NO_HELMET merely
by naming it; no object-to-hazard mapping is established here.

D4 boxes are x-first, top-left origin, normalized to [0,1], with strict positive
width and height. Direct D5 metrics use continuous IoU and Hit@0.25/0.50 with
the already specified matching rules; weak-proxy polygon/PLC reporting remains
separate. Consumers need sample/participation/parse state, hazard IDs, every
predicted box and separate GT regions. This task computes none of these metrics.

## Classification proposal and its evidence limit

The candidate records this exact existing `classification_request` template:

```text
Classify the image using the supplied industry safety policy. Return only a JSON object with the single field "safety_level", one of ["Level01", "Level02", "Level03", "Level04"].
Industry safety policy:
{industry_safety_policy}
```

English instruction; the single variable is passed verbatim. Policy content,
language, version and hash remain **UNRESOLVED**, consistent with
[the existing implementation record](pre_freeze_implementation.md#implemented-contracts).
There is no default policy. This is the canonical target for a future qualification
proposal, not a claim that PaliGemma emits JSON/levels under it. A model-specific
native wrapper is **UNRESOLVED**; an `answer en` prefix is not silently added.

D9R11 only supports exact `yes`/`no` in `decoded_text`, for
`answer en Is there a red square in the image?`, mapping to a separate presence
boolean. It supplies no production safety mapping. Qualified production prompt,
supported production native grammar and native-to-safety mapping are null.
The semantic change to C1 necessarily requires additional runtime qualification.
Do not substitute `Is this image unsafe?`, expand to arbitrary labels/synonyms,
or derive a four-level decision from presence answers.

## Grounding proposal: production and gate stay distinct

The candidate copies the exact English `grounding_request` text and vocabulary
as the canonical requirement. There is no variable target label in this builder.
The native PaliGemma prompt that implements independent B2 discovery, and its
hazard associations, are **UNRESOLVED**. `detect {object}` is documentary detection
syntax; it does not establish that missing PPE or other hazards can be discovered
and associated with B2 IDs in the required independent Call 2. Do not replace
this task with a GT-conditioned list of objects or twelve new independent calls.

For a future external probe only, `detect {target_label}` is a concrete proposal
supported by D9R7 task syntax plus the D9R11 red-square call. The exact closed
translation table is derived from the frozen manifest, not fuzzy text extraction:

| Frozen target query | Proposed native prompt | Current runtime evidence |
| --- | --- | --- |
| Locate the red square. | `detect red square` | D9R11 only |
| Locate the green circle. | `detect green circle` | UNRESOLVED |
| Locate the yellow triangle. | `detect yellow triangle` | UNRESOLVED |
| Locate the cyan rectangle. | `detect cyan rectangle` | UNRESOLVED |

The table is disabled pending review/qualification. Caller prompts have no
trailing newline; the existing native processor supplies its own newline/BOS/
image tokens. No gate config or prompt builder is changed.

D9R7's audited family/model-ID-level visualization decoder accepts label text
and repeated matches, but explicitly is not an exact model-output contract.
That is sufficient documentary basis to propose observing the other labels,
not to enable arbitrary labels, separators or repeated groups in a parser.
Current supported grammar is the full-string match of four adjacent ASCII
four-digit loc tokens, one space, literal `red square`, and `<eos>`.

Native `[y_min,x_min,y_max,x_max]` integers 0..1023 map to
`[x_min/1024.0,y_min/1024.0,x_max/1024.0,y_max/1024.0]`. Maximum is 1023/1024.
Validate range and strict geometry before conversion. No /1023, clamp, rescale,
sorting, fabricated box, point conversion or semantic repair. The common schema
has a historical clamp for other interfaces; PaliGemma's D9R7 helper does not use
that helper to repair native output.

After separate qualification, a single gate box could become `ProbePrediction`;
the raw native label must remain in provenance. That does not make an `Evidence`
into `Grounding`, establish a hazard type or activate a runner adapter.

## Empty output, multiplicity and semantic errors

Canonical no listed hazard is `{"hazards":[]}` / `Grounding(())`.
`{"hazards":[{"hazard_type":"SMOKE","evidence":[]}]}` is also schema-valid,
but means a claimed hazard with no localized evidence. It is not the same empty
case and grants no localization success. There is no success-valued empty box
representation in `external_probe`.

No exact-checkpoint native no-detection grammar exists in the evidence. Choose
**B: additional runtime observation under the resolved production prompt**.
Do not invent empty string, EOS-only, `none`, `[]` or zero regex matches as a
native success grammar. Current candidate parsing of those strings remains
INVALID/null, never an empty canonical prediction.

The frozen eight-case [manifest](../configs/pre_freeze/external_gate_cases.v1.json)
always supplies a target and distractor. Its [evaluator](../safeshift/protocol/gate.py)
requires one `ProbePrediction.bbox` per case. Multiple boxes and target-absent
successes are not gate requirements. Unexpected multiple/empty native results
cannot be repaired by choosing, merging or fabricating a box. Conversely, full
production Call 2 must retain multiple hazards/evidence; D9R11 did not qualify
that grammar. These are separate requirements, not reasons to alter the gate.

`grd_d` stays syntactically successful with
`Evidence((366/1024,359/1024,659/1024,662/1024), "red square")` despite target
absence. Its semantic hallucination/target-selectivity failure is preserved.
Parsers receive no image truth and cannot drop the prediction. Future evaluation
must receive parseable hallucinated predictions unchanged and apply its real
criteria. D9R11 grd_d is not inserted into synthetic-v1 as a ninth case.

Gate PASS still requires valid schema/geometry, center in target, distractor
center exclusion, reciprocal-swap tracking, no full-image box, and explicit
human NO_GIANT review for all eight cases. IoU and area are diagnostic only,
with no numerical acceptance thresholds added or relaxed.

## Smallest proposed next-runtime coverage

The candidate lists nine **conditional minimum** cases, not an executable matrix:

- Four C1 cases: one independently annotated external/synthetic image per
  Level01..Level04 under a pinned policy and exact production prompt.
- Three one-target observations: green circle, yellow triangle, cyan rectangle
  using the exact proposed detect prompts on new non-gate handcrafted fixtures.
  One alternate label would not qualify the other two; red-square position/size
  tests already exist and need not be repeated.
- One production Call 2 scene with two approved hazards and two evidence
  instances for one of them, combining multiple-label/box association checks.
- One production Call 2 scene with no listed hazard under the same resolved
  prompt, observing native no-hazard behavior without coercing hallucinations.

Before those calls, Research Lead must resolve the C1 policy/native route and
B2 native route, approve gate query rendering, and predeclare fixtures, provenance,
expected annotations and generation budget. No policy or hazard mapping is
invented to make this plan executable. Nine is a lower bound for observing the
identified feature gaps, not proof of all twelve hazard IDs or automatic
qualification. If no valid empty behavior appears, that gap remains unresolved.
Native `detect` empty behavior is not required by the current positive-only gate.

Raw envelopes must be persisted and verified before parsing, linked to sample,
run/call, prompt/hash, model/revision, generation configuration, environment, Git
commit and raw path/hash/size. Preserve both decoded forms and full/continuation
IDs. The existing runner restricts source kind to HANDCRAFTED_RUNTIME_SMOKE and
32 output tokens; integration and any adequate production token budget require
separate prep/review, not silent relaxation or a longer retry here.

## Status and validation

Classification interface, grounding and external gate remain
PENDING_QUALIFICATION. BACKUP_1; four primaries; protocol freeze BLOCKED;
InspecSafe authorized=false; promotion=false. D9R12 is COMPLETE, PR #59 merged;
D9R13 is PREP / implementation awaiting Research Lead review.

Validation uses Python 3.11.9 and pure/static tests. No GPU, model loading,
inference, provisioning, Kaggle, synthetic-v1 gate or InspecSafe execution.
The unchanged parser regressions use strings; new canonical tests use synthetic
JSON and do not call the gate evaluator. Protected base-file comparisons lock
schema, metrics, runners, gate definitions/assets and historical evidence.

Validation command:

```text
python -m unittest tests.test_paligemma_production_interface_candidate tests.test_paligemma_interface_candidate tests.test_paligemma_interface_qualification tests.test_paligemma_d9r11_notebook tests.test_paligemma_runtime_result tests.test_paligemma_d9r9_notebook tests.test_paligemma_prep tests.test_local_runners tests.test_internvl3_prep tests.test_internvl3_runtime_result tests.test_d9r6_paligemma_primary_expansion_precommit tests.test_d9r7_paligemma_source_api_audit tests.test_d9_t4_roster_revision tests.test_model_provenance -q
git diff --check
```

Results: **281/281 static/fake tests PASS** (14 new contract tests, 267 existing
regressions); **32/32 pre-freeze JSON files PASS** through `strict_json`, including
duplicate-key/non-finite rejection inherited from that parser. Protected-source
and frozen-image byte comparisons against exact base PASS. Diff check PASS.
The existing fake harness tests print simulated bundle/provision messages; those
are temporary test artifacts, not new model/runtime evidence or provisioning.

Scoped secret-pattern scan of all five changed files PASS: provider token
prefixes, AWS access keys, private-key headers, literal credential assignments
and bearer authorization headers. This is a pattern scan, not an exhaustive
secret audit. No new dependency or credential is stored.

Real runtime, synthetic-v1 gate and InspecSafe checks are intentionally not run
under this PREP-only authorization. No live qualification is claimed. Artifacts
for this task are the small versioned candidate, note and tests; no derived
dataset, model output or image artifact is created for commit.
