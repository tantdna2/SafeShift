# D9R19G3 positive-guaranteed multicategory grounding PREP

Date: 2026-10-04. Task:
`W2.6-D9R19G3-POSITIVE-GUARANTEED-MULTICATEGORY-GROUNDING-PREP`.
Fetched origin/main equals exact required BASE
`775e5eee4cade340e0156f97f2af50f7c98e1551`.
Branch: `w2.6-d9r19g3-positive-multicategory-grounding-prep`.

This prepares `grounding-multicategory-candidate-v3.0` and
`external-grounding-multicategory-v3`, with 12 positive synthetic cases.
It establishes source-backed candidate interfaces, not exact-checkpoint
conformance, qualification PASS, production readiness or promotion.

## Source evidence

The [source manifest](../configs/pre_freeze/grounding_multicategory_sources.v1.json)
records seven directly inspected official sources with URL, SHA256, size,
access date and locator. Sources were fetched as bytes and read as text/JSON;
no downloaded source or notebook was executed. No upstream images, model
weights, historical raw outputs or InspecSafe content were used as fixtures.

Qwen model: `Qwen/Qwen3-VL-8B-Instruct`, revision
`0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`. Official family source pin:
`QwenLM/Qwen3-VL@96588727e44c78b25ba03ea03b8e12f7e64fd0da`.

- [ODinW dataset_utils.py](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/ODinW-13/dataset_utils.py#L153)
  joins the dataset's complete class list with comma-space and interpolates it
  into one prompt for each image. It does not choose categories from image GT.
- [ODinW README](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/ODinW-13/README.md)
  documents the category-list prompt and JSON detection array.
- [ODinW runner](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/ODinW-13/run_odinw.py#L215)
  iterates detections and converts xyxy by /1000. Its label lowercasing,
  malformed-box skipping, permissive parsing and exception-to-empty are not adopted.
- [2D cookbook](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/cookbooks/2d_grounding.ipynb)
  cells 0/4/8-10/12 support normalized coordinates, multicategory detection and
  omission of negative categories. Executable x-first conversion and cell 12
  agree; the stale y-first plotting docstring is not followed. API examples use
  a different model size, so family evidence is not pinned-8B execution evidence.

PaliGemma model: `google/paligemma-3b-mix-448`, revision
`ead2d9a35598cb89119af004f5d023b311d1c4a1`.
[Google task syntax](https://ai.google.dev/gemma/docs/paligemma/prompt-system-instructions#prompt-task-syntax)
specifies `detect {object} ; {object}\n` for locating listed objects and returning
boxes, and permits referring expressions as objects. The accessed mutable page
snapshot has 141966 bytes and SHA256
`ec775881189968513d17b6624a52f4b5d28254b287d930114e15272c854f9b56`.
Access date is 2026-10-04; no immutable page URL is available. This is a separate
observed snapshot from G2, not a rewrite of its hash or an immutable release claim.

The pinned [official HF demo](https://huggingface.co/spaces/big-vision/paligemma-hf/blob/d914d4446a6ff8c5b3110411abca69887f035c41/app.py#L280)
and [companion parser](https://huggingface.co/spaces/big-vision/paligemma/blob/b19d492be08ec5e8aad190a522db919d4444f529/paligemma_parse.py#L132)
iterate multiple loc-token detections, with yxyx /1024. Their hashes match G1/G2.
The demo names mix-448 but does not pin its runtime revision. Exact processor,
tokenizer and whole-image preprocessing evidence is inherited by explicit
reference to the unchanged G1 source manifest. PaliGemmaProcessor owns the final
newline. No generic no-match behavior establishes valid absence.

## Restricted scope and prospective production compatibility

[Approved D6](../DECISIONS.md#dec-w2-d6-006--hazard-taxonomy-and-grounding-support-census)
and the [census brief](w2_grounding_census_decision_brief.md) define Direct-Support
pool membership by >=1 Direct atom and Weak-Proxy membership by >=1 Proxy atom:
`721 + 608 - 347 = 982` unique Anomaly samples. `982 + 18 = 1000` Anomaly samples;
the 18 Unsupported-Only samples and all Normal images are outside this primary
execution scope. Verification uses the approved census record, not a fresh
dataset scan or new inference. Dataset/census recorded hashes are in the plan.
The guarantee concerns supported atoms under D6, not full hazard rationale truth.

```text
POSITIVE_GUARANTEED_EVALUABLE_POOL=982
QWEN3_ABSENCE_SEMANTICS_BLOCKER=UNRESOLVED
PALIGEMMA_ABSENCE_SEMANTICS_BLOCKER=UNRESOLVED
ALL_TARGET_ABSENT_SEMANTICS=NOT_APPLICABLE_TO_POSITIVE_GUARANTEED_PRIMARY_SCOPE
```

Every prospective image receives the same full 12-query set, in canonical
HAZARDS order. The exact model-independent map is recorded in the
[v3 plan](../configs/pre_freeze/grounding_interface_qualification_plan.v3.json)
and [candidate](../safeshift/protocol/grounding_multicategory_candidate.py).
It comes from this Research Lead instruction and canonical taxonomy, before
InspecSafe inference; query-to-hazard binding is exact, with no synonym/alias.
There is no GT-selected query, per-image hazard filtering or Call-1 conditioning.

Qwen3: one image -> one logical Call 2 -> one all-12 category prompt -> ordered
JSON detections -> exact hazard binding -> canonical D4 xyxy /1000.
PaliGemma: one image -> one logical Call 2 -> `detect obj1 ; ... ; obj12` ->
ordered loc detections -> exact hazard binding -> canonical D4 yxyx /1024.
The same native templates are used for the four-label synthetic vocabulary.
Moondream's native single-object detect may need backend fan-out; G3 does not
change its policy, implementation or blocker.

Production execution is not implemented or authorized. A prospective synthetic
ceiling of 512 new tokens per call is fixed for both models, chosen for up to five
synthetic detections without looking at model responses. Greedy FP16/no quantization
and all other settings are fixed in the plan. There is no in-run budget increase.
The full-12 production environment/context/token budget still needs separate
pre-execution freezing and qualification; synthetic PASS alone cannot authorize it.

## Parsing and failure semantics

Qwen accepts only a JSON array of objects with exactly `bbox_2d` and `label`.
Coordinates are finite values in 0..1000 with strictly increasing axes; /1000
is unconditional. Pali accepts four adjacent ASCII loc tokens in 0..1023,
one space and an exact queried label, with `; ` or ` ; ` between detections.
The native grammar is a deliberately strict full-consumption subset of the
official parser. Tokenizer continuation decoding skips special tokens with
cleanup disabled; full IDs and special-token decode must also be preserved.

Both parsers preserve every detection, label and native order, including repeated
labels and identical boxes. No first/best box, deduplication, clamp, scale guessing,
fuzzy labels, aliases, repair, segmentation, point-to-box or unmatched-text salvage.
One malformed detection or unknown label invalidates the whole response;
failure returns detections=null, never a salvaged subset.

Qwen `[]` (including JSON whitespace), completely empty Qwen text, or completely
empty Pali decoded continuation yields `POSITIVE_GUARANTEE_MISS`, never SUCCESS.
Whitespace-only/prose/null/invalid grammar remains INVALID, also a failure.
This is a scope-specific failure rule, not valid native zero-detection semantics.
Future D5 end-to-end handling must retain grounding failure / zero matched evidence
for an eligible executed positive sample, without rescue. It must not score a
NOT_PARTICIPATING model as a failure. No D5 production executor is added here.

V3 does not suffice for Normal images, full 5,013 execution, the 18 Unsupported-Only
images or full-dataset Object Hallucination Rate. Those expansions make the
historical absence blockers mandatory again. General v2/G2 remain unchanged;
their mandatory all-absent case is neither removed nor waived by this new scope.

## Synthetic qualification declaration

The [manifest](../configs/pre_freeze/external_grounding_interface_cases.v3.json)
has 12 deterministic 256x256 RGB cases. Every prompt asks red square, green circle,
yellow triangle, cyan rectangle in that order, regardless of expected presence.

| Cases | Composition |
| --- | --- |
| A_1/A_2 | One red square and blue-square distractor; horizontal swap |
| B_1/B_2 | One green circle and orange-circle distractor; vertical swap |
| C_1/C_2 | One yellow triangle and purple-triangle distractor; diagonal swap |
| D_1/D_2 | One cyan rectangle and gray-rectangle distractor; diagonal swap |
| E_red_green | Red + green, with blue-square distractor |
| F_two_red | Two red squares, with orange-circle distractor |
| G_multi | Two red + two green + one yellow |
| H_all_four | All four queried categories, with purple-triangle distractor |

Every case has >=1 queried target; there is no all-target-absent case. All four
expected label counts are explicit, including zero for absent queried categories.
The generator reuses only historical drawing primitives, never alters v2 fixtures.
Its code and dependencies are locked; PNG hashes/sizes are in the manifest.
Images stay ignored under `data/processed/external_grounding_multicategory_v3/`.
Regenerate with `python scripts/prepare_grounding_multicategory_v3.py`; mismatching
manifest or existing image bytes cause failure, not overwrite. No random seed.

PASS rules are predeclared in the plan. All 12 calls must complete, with the same
prompt/parser/config and raw bytes persisted and verified before parsing. Every
expected instance requires one same-label prediction whose center lies inside
its GT box, with exact per-label counts and a bijection. Absent queried labels
must have zero predictions. Every predicted box excludes all unqueried distractor
centers. All four reciprocal pairs track displacement on each moved axis;
multi-instance cases preserve all predictions. No exact full-image box is allowed.
Human NO_GIANT review must cover every detection, with reviewer and rationale.
IoU is diagnostic only. Empty response fails. No partial PASS, retry, repair,
alternate prompt, parser change, GT-selected query or response-dependent tuning.

The geometry module reports observations only; it cannot award PASS or substitute
for durable-storage/runtime checks or human review. Future integration must enforce
these plan obligations and record run/sample/call IDs, prompt, model/revision,
raw bytes/hash/size, token boundaries, environment, generation config and commit.

Primary scoring remains separate RQ3-A Direct / RQ3-B Weak Proxy. Unsupported
spatial atoms remain excluded under D5 even when present alongside supported atoms.
DOOR_OPEN is still queried in the all-12 interface; it does not acquire spatial GT.
No D5 metric policy changes and no full-dataset Object Hallucination Rate.

## Validation and protected history

Environment: Python 3.11.9, Pillow 11.3.0, zlib 1.3.1; stdlib unittest/hashlib.
Offline tests use handcrafted strings and generated synthetic images only.

```text
python -m unittest tests.test_grounding_multicategory_v3 tests.test_grounding_interface_v2 tests.test_grounding_absence_semantics_audit -q
python -m unittest tests.test_qwen3_external_gate tests.test_qwen3_external_gate_result tests.test_paligemma_external_gate tests.test_paligemma_external_gate_result tests.test_paligemma_interface_candidate tests.test_external_gate_cases tests.test_d9r7_paligemma_source_api_audit tests.test_d9r15_five_model_roster_exploratory_grounding tests.test_qwen_runner tests.test_paligemma_prep -q
git diff --check
```

77 focused tests PASS (34 new + 43 v2/G2); 267 relevant regression tests PASS:
344 total. The first new-test run found a test-only binary comparison error
(text newline normalization applied to PNG bytes); the assertion now preserves
binary bytes exactly. No protected file was changed. Full suite was not run;
no full-suite PASS is claimed. The old D9R18 task-specific diff allowlist is
outside this regression selection, as already documented by G1/G2.

The [v3 lock](../configs/pre_freeze/grounding_interface_lock.v3.json) binds v3
code/artifacts and shared helpers and protects 73 existing files by Git blob.
Tests verify text with Git-normalized LF and binary fixtures byte-for-byte;
the retained v2 tests additionally verify their contract working-tree hashes.
DECISIONS/TASKS preserve their BASE prefix and append G2 closure and G3 only.
G2 merged as PR #69 at `775e5eee4cade340e0156f97f2af50f7c98e1551`;
historical G2 MERGE=NO remains intact.

Historical Qwen3 gate GATE_FAIL (5/8) and PaliGemma gate FAIL (6/8) remain unchanged.
Both primary grounding roles remain NOT_PARTICIPATING. Future v3 qualification
PASS still needs a separate Research Lead promotion decision. PR #67 was read
only, OPEN/DRAFT at `e85300ab3ec122f819a2685613332578f7e203d8`.

QUALIFICATION_EXECUTION=NOT_RUN; execution_authorized=false; MODEL_GPU_EXECUTION=NO;
INSPECSAFE=NOT_RUN; PROMOTION=NO; MERGE=NO. No qualification result is fabricated.
