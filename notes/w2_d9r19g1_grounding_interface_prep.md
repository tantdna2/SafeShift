# D9R19G1 — prospective grounding-interface qualification PREP

Date: 2026-10-03. Exact fetched main BASE:
`5538064e6ea015f8c15475d488064cae95461cd0`.
Separate branch `w2.6-d9r19g1-qwen3-paligemma-grounding-prep`;
no continuation of D9R19 and no changes to PR #67.

Research objective: determine whether Qwen3 and PaliGemma can support a
source-backed, production-compatible grounding interface before protocol freeze.
No PASS is promised. This is PREP, not a new qualification result or promotion.

```text
EXECUTION_STATUS=NOT_RUN
MODEL_GPU_EXECUTION=NO
QUALIFICATION_EXECUTION=NOT_RUN
INSPECSAFE=NOT_RUN
PROTOCOL_FREEZE=PENDING
MERGE=NO
```

## Source audit and evidence boundaries

The [source audit](../configs/pre_freeze/grounding_interface_sources.v2.json)
pins URLs, access dates, byte sizes, SHA256 and exact source locators. Only source
text was downloaded/read. The notebook was decoded as JSON, never executed;
its embedded examples/assets remain in ignored `data/processed/` and are not
qualification images. No model weights, GPU library initialization, historical
raw bundle, benchmark image or credential was needed.

| Candidate | Exact model/revision | Documentary basis | Remaining limitation |
| --- | --- | --- | --- |
| Qwen3 | `Qwen/Qwen3-VL-8B-Instruct` / `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` | Official Qwen3 family cookbook | Its API examples use 235B; exact local 8B conformance is not established by source evidence |
| PaliGemma | `google/paligemma-3b-mix-448` / `ead2d9a35598cb89119af004f5d023b311d1c4a1` | Official PaliGemma 1 decoder plus merged D9R7 accepted normalization and exact metadata audit | Decoder is model-ID-level, not exact-revision runtime evidence |

Qwen's [2D cookbook at `9658872`](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/cookbooks/2d_grounding.ipynb)
provides independent evidence: zero-based cell 0 states relative `0..1000`;
cell 4's executable `plot_bounding_boxes` indexes x at 0/2, y at 1/3, divides
each by 1000 and scales by the displayed image's width/height. Cell 12's
`[x1,y1,x2,y2]` example agrees. The plotting function's y-first docstring is
inconsistent with that code; this audit records the discrepancy rather than
silently assuming its order. Cell 8's saved official example shows an array of
objects with `bbox_2d` and `label`, and cells 8–10 request every instance.
None of these are historical SafeShift failed outputs.

The [official PaliGemma 1 HF demo](https://huggingface.co/spaces/big-vision/paligemma-hf/blob/d914d4446a6ff8c5b3110411abca69887f035c41/app.py)
and [companion parser](https://huggingface.co/spaces/big-vision/paligemma/blob/b19d492be08ec5e8aad190a522db919d4444f529/paligemma_parse.py)
loop over loc-token detections and append each box with its following label.
This is the reason the new candidate supports multiple detections. The
[merged audit](w2_paligemma_source_api_audit.md) already established
`ymin,xmin,ymax,xmax`, integer `0..1023`, division by **1024**, exact tokenizer
loc vocabulary, processor-owned newline and whole-image 448x448 preprocessing.
Detection decoding is not the segmentation training encoder's `/1023` inverse.

## Candidate contracts

The new pure [candidate module](../safeshift/protocol/grounding_interface_candidate.py)
is isolated from every historical parser and runner. Its return type carries
ordered D4 `Evidence` records; `SUCCESS` is syntax only. It neither assigns
qualification status nor participates in production adapters.

Qwen prompt family (one literal target category substituted):

```text
Locate every instance that belongs to the following categories: "{label}". Report bbox coordinates in JSON format.
```

No system override; future integration uses the exact pinned processor's chat
template. The same prompt family applies to absent, single and multiple targets.
No expected count, GT box or position is included. Accepted continuation is a
strict JSON array of objects with exactly `bbox_2d` and `label`. Every label
must equal the query string exactly. Four finite JSON numbers must lie within
`0..1000` with strictly increasing x and y. Conversion is componentwise `/1000`.
Small magnitudes do not trigger a different scale. One and multiple detections
are preserved in order; no deduplication or best-box selection.

This is a deliberately strict native subset: singleton objects, code fences,
extra keys, prose, point structures, duplicate keys, NaN/Infinity and malformed
JSON fail. The official visualization helper accepts fences and repairs some
outputs; those permissive visualization operations are **not** adopted. Its
example outputs can therefore fail this stricter prospective contract; no claim
of guaranteed format compliance is made and no later output-conditioned rescue
is permitted. JSON whitespace is legal syntax, not markdown stripping.

PaliGemma processor payload is `detect {label}`; its audited
`build_string_from_input` adds the LF, producing native `detect {label}\n`.
Do not supply a second LF. Parse exact `decoded_text`, produced by the tokenizer
with `skip_special_tokens=true`, `clean_up_tokenization_spaces=false`; raw
special-token decode and full IDs remain preserved separately. Parser itself
does not remove EOS or trim whitespace.

Supported detection-only grammar is four adjacent ASCII `<locNNNN>` tokens,
one space, exact query label, repeated with separators `; ` or ` ; `. These
are explicit strict forms supported by upstream `_SEGMENT_DETECT_RE`.
Reject omitted/anonymous/wrong labels, non-ASCII digits, extra whitespace,
trailing separators, segmentation and unmatched text. The regex is a full
grammar match for every item; it does not search for recoverable substrings.
Convert native yxyx to D4 xyxy with `/1024`; 1023 stays `1023/1024`, never 1.
No clamp, rounding, axis repair, fuzzy label match or fabricated box. If any
detection is invalid, the entire canonical response is invalid (`None`);
no valid subset is silently passed to scoring. Raw still retains everything.

For both models, coordinates denote fractions of the whole image's axes.
Qwen's cookbook uses current displayed dimensions without `resized_w` recovery;
PaliGemma resizes the entire image to 448x448 without crop. Normalized fractions
therefore need no 448 divisor or aspect-ratio correction. External crop, tiles,
letterbox or inferred scale are outside this contract. Future audit records
must include original and actual processed dimensions and processor revision.

## Absence blockers — mandatory stop before execution

**QWEN3_ABSENCE_SEMANTICS_BLOCKER** — cookbook cells 8–10 say negative
categories are skipped, but do not specify the complete response when *all*
requested categories are absent. The inspected cookbook and README provide no
strict all-absent serialization. An empty array currently returns `BLOCKED`,
not successful empty detections. Blank, null, prose and no-match are invalid.

**PALIGEMMA_ABSENCE_SEMANTICS_BLOCKER** — official `extract_objs` returns no
boxes for empty/no-match text, but that permissive decoder behavior does not
document a valid target-absent model response. The official sources and merged
audit do not establish strict empty/EOS-only semantics. Empty tokenizer-decoded
text returns `BLOCKED`; EOS text, whitespace, `[]` and prose are invalid.

These are bounded source findings, not claims that no documentation can exist
elsewhere. Neither blocker may be bypassed by assuming absence, converting a
parse failure to zero boxes, dropping the absent case or granting partial PASS.
Future resolution requires additional authoritative source, a new version of
the contract/lock and independent review **before any qualification call**.

The common detection container can represent zero/one/multiple, but neither
candidate currently establishes valid zero semantics. Production compatibility
is consequently **PARTIAL / BLOCKED_ZERO_DETECTIONS**, not complete. We do not
claim deterministic zero conversion has been implemented while its semantics
are unknown.

## New suite and predeclared verdict

[Manifest](../configs/pre_freeze/external_grounding_interface_cases.v2.json):
`external-grounding-interface-v2`, ten calls per model, separate run IDs.
The eight A–D cases reuse semantic geometry and colors from the old deterministic
generator; their new paths/manifest/version are independent. No old image or
manifest is overwritten. E_absent shows a blue square and green circle while
querying a red square. F_multiple shows two separated red squares with a blue
square distractor. These are interface/spatial cases, not industrial semantics.

[Plan](../configs/pre_freeze/grounding_interface_qualification_plan.v2.json)
predeclares every required criterion and fixed controls. Positive cases require
exact cardinality, a bijection between prediction centers and separate target
boxes, and exclusion of every distractor center (boundary counts as inside).
All four pairs must track displacement with the target on each moved axis.
Multiple output order is unrestricted by scoring but fully preserved by parser;
duplicate boxes cannot replace separate target instances. E_absent requires
successful source-backed zero output. IoU/area remain diagnostics only.

Exact full-image boxes fail. Every nonempty case also needs an explicit
`NO_GIANT` human review, reviewer and rationale covering **all** detections.
No numerical giant-box cutoff is invented. The pure
[geometry helper](../safeshift/protocol/grounding_interface_geometry.py) reports
observations and tracking; it cannot issue a qualification PASS. Missing human
review yields PENDING_REVIEW only if every other mandatory check passes.
Runtime/storage/parse/semantic failures yield FAIL in a future authorized run.
Current verdict is null / NOT_RUN; preflight is BLOCKED.

One prospectively selected 256-token ceiling per call supports small detection
lists for both candidates; it was not selected from historical response lengths
or new model outputs. Greedy decoding, one sequence, one beam, FP16/no quantization;
no retry, repair, alternate prompt, parser change or budget increase during a
run. This changes neither old 32-token plans nor their verdicts. In particular,
the old PaliGemma runner fixes 32 tokens and must **not** be reused as an executor
for this plan. No new model executor, notebook or GPU entrypoint is provided.

## Raw/audit and future execution boundary

The plan is the normative prospective raw contract, not a fabricated run record.
Create an exclusive new run directory. Persist original native envelope bytes
and preparse metadata with exclusive creation, flush/fsync/close, then reread
and verify raw size/SHA256 and metadata before invoking either pure parser.
Only the persisted continuation decode may enter the parser. Keep full native
IDs, prompt input boundary, special-token decode and actual decoding config;
verify model/revision, token prefix/continuation and terminal EOS, and fail
truncated generations. Do not reconstruct raw from canonical predictions.

Each eventual record includes model/revision, run/call/case IDs, exact prompt
ID/version/text/hash, image hash, raw path/hash/size, preprocessing/dimensions,
precision/quantization/decoding, parser version/hash, parse status, all canonical
detections and geometry observations. Also record timestamp, Git commit, command,
exact dependency versions, hardware, seed, manifest/plan/source hashes. Initial
parse status is NOT_ATTEMPTED and canonical is null. Store parse/geometry as a
separate artifact. On storage failure stop without parsing; preserve partial
native evidence if available, never invent unavailable output. Audit all artifact
hashes before any verdict. No such model records are created in PREP.

Tests below validate the **declared** persistence ordering and null/failure
contract. They do not claim to have tested a real storage/execution harness;
that integration remains future work, blocked on absence resolution and separate
execution authorization. Before loading, independently lock the full runtime
environment, model/processor snapshots and adapter implementation, command and
commit. This PREP does not assert the historical runtime plans accept the new
decoding configuration.

Future Call 2 contract: one image goes through a fixed, predeclared hazard-query
list, independent of GT and Call 1. Each exact query-to-hazard binding groups all
native `Evidence` under canonical D4 `Hazard` / `Grounding`, without relabeling
native strings or selecting boxes. Query wording/mapping and fan-out orchestration
are not implemented or approved here. Valid zero would contribute no evidence;
invalid/blocked is never treated as absent. No full InspecSafe executor exists.

## Historical protection

Qwen3 remains GATE_FAIL: 5/8 canonical successes, 2 coordinate errors and 1
schema error. PaliGemma remains FAIL: 6/8, 2 schema errors under its historical
exactly-one parser. Both primary grounding roles remain NOT_PARTICIPATING.
D9R15 and D9R18 policies/results are intact. A future new PASS would require a
separate Research Lead promotion decision and could not rewrite either FAIL.

[Lock](../configs/pre_freeze/grounding_interface_lock.v2.json) pins prospective
plan/manifest/source/parser/generator/geometry hashes and BASE Git blob IDs for
historical configs, parsers, gate plans/scripts, fixtures and relevant notes.
Tests verify those blobs and append-only DECISIONS/TASKS prefixes. Git blob
comparison respects checkout EOL conversion; same-checkout byte snapshots are
also compared during this task. Prior ignored raw/results are never opened or
written. PR #67 remains OPEN/DRAFT on
`w2.6-d9r19-production-implementation-d5`, HEAD
`e85300ab3ec122f819a2685613332578f7e203d8`.

## Reproduction and validation

Input generation only, from repository root:

```text
python scripts/prepare_grounding_interface_v2.py
python -m unittest tests.test_grounding_interface_v2 -q
git diff --check
```

Python 3.11.9, Pillow 11.3.0, zlib 1.3.1. No random seed is needed for integer
geometry rendering. Images are ignored under
`data/processed/external_grounding_interface_v2/images/`; they are not committed.
The CLI reconstructs and verifies the frozen manifest, then writes only absent
identical images; it refuses changed manifest/image bytes. The source generator
hash plus BASE dependency hashes are locked. Its initial execution used BASE
HEAD with new working-tree files; the reviewed PR commit identifies the final
source state. PNG bytes are guaranteed only for the recorded renderer environment.

Validation results are recorded below after tests; no model/qualification result
is inferred from synthetic/native fake-output unit tests.

Validation on 2026-10-03:

- New focused tests: **33/33 PASS**, including malformed/native boundary cases,
  no scale guessing, all-box preservation, absence blockers, case geometry,
  byte-exact regeneration, immutable contract hashes and historical protection.
- Unfiltered historical regression selection: **284 tests, 283 PASS, 1 FAIL**.
  The sole failure is
  `tests.test_d9r18_final_participation_decision.FinalParticipationTests.test_only_explicit_decision_documentation_and_test_files_change`.
  It runs `git diff` against its old D9R18 BASE and allows only D9R18 files,
  explicitly prohibiting new parser/scripts. That scope assertion passes when
  comparing its BASE with required BASE `5538064`, but necessarily fails for
  this new authorized PREP. This is a current task-scope incompatibility, **not**
  a pre-existing BASE failure. The historical test/allowlist is not edited.
- The same regression selection, excluding exactly that old task-scope test,
  plus the 33 new tests: **316/316 PASS** (283 regression + 33 new).
- All four new JSON artifacts parse strictly. `git diff --check` PASS.
  All 61 protected existing files match BASE Git blobs and same-checkout bytes;
  DECISIONS/TASKS retain historical prefixes. Image generation writes only
  synthetic inputs, with no model calls. No new qualification verdict exists.
- Full repository suite was not run: validation is scoped to the two native
  runners, historical gate/parser/result paths, source audit, fixture generator
  and current role protection. No full-suite PASS is claimed. No GPU/model,
  real qualification or InspecSafe execution was run, as required.

Unfiltered regression command (expected old task-scope failure described above):

```text
python -m unittest tests.test_qwen3_external_gate tests.test_qwen3_external_gate_result tests.test_paligemma_external_gate tests.test_paligemma_external_gate_result tests.test_paligemma_interface_candidate tests.test_external_gate_cases tests.test_d9r7_paligemma_source_api_audit tests.test_d9r15_five_model_roster_exploratory_grounding tests.test_d9r18_final_participation_decision tests.test_qwen_runner tests.test_paligemma_prep -q
```

The combined run loads those eleven modules plus `tests.test_grounding_interface_v2`
through `unittest.defaultTestLoader.loadTestsFromNames`, recursively flattens the
suite, filters only the exact ID quoted above, and runs the remaining 316 tests.
This is an explicit validation selection, not a skip/deletion added to an old test.
