# D9R13 — PaliGemma canonical SafeShift compatibility runtime PREP

Draft PR #60, same branch/session; not merged. Research Lead correction replaces
the earlier nine-case production-interface discovery proposal. The canonical C1,
A2/B2 and D4 contracts are already decided. This patch prepares one direct
compatibility evidence collection, not an accuracy benchmark or contract redesign.

## Concrete preparation and remaining input blocker

The harness, qualification adapter and Kaggle notebook are implemented. Budget:
**4 classification + 3 grounding = 7 calls, one model load**. Actual runtime
fixtures/policy are **not ready in this checkout**. The checked-in plan has explicit
null references, so input validation stops before provisioning/model loading.

Repository evidence, not a claim that the Research Lead has not approved a policy:

- `classification_request` requires caller-supplied industry policy. Tracked
  callers are unit tests; they pass `SYNTHETIC_POLICY_MARKER`, `synthetic policy`
  or an explicitly nonproduction marker.
- `notes/pre_freeze_implementation.md` under Implemented contracts records that
  exact industry policy text still needs a pin. There is no tracked policy file.
- `git ls-files tests/fixtures` lists dummy predictions, geometric external-probe
  cases and a red-rectangle smoke fixture. There are no scene images annotated
  Level01–04 or approved hazard/no-hazard C1/B2 runtime fixtures.
- `configs/pre_freeze/external_gate_cases.v1.json` contains eight geometric
  single-target probes, not safety-policy classification cases. Its SHA-256 stays
  `fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379`.

Needed to complete runnable preparation: paths/source/version/checksums for the
already approved production C1 policy and four approved level images, plus two
distinct approved hazard images and one no-hazard image. The positive slots are
SMOKE and OPEN_FLAME (existing D6 IDs). These are requested coverage slots, not
fabricated annotations or claims that images exist. Do not populate them with
test-only marker policies, shape images, embedded answer cards or InspecSafe.

After those artifacts are supplied, pin their relative paths/checksums/approval
references in the plan and update the plan hash/source pin in a reviewed patch.
No mutable external input, runtime prompt choice or ad hoc local file replacement
is accepted. No change to dataset definitions, split, labels or metrics is made.

## Canonical paths and minimal case set

Classification: `safeshift/protocol/prompts.py:classification_request` →
`safeshift/runners/contracts.py:Request` → unchanged native PaliGemma runner →
verified raw storage → qualification adapter →
`safeshift/protocol/schema.py:parse_text` / `Classification`.

Grounding: `safeshift/protocol/prompts.py:grounding_request` → the same native/raw
path → qualification adapter → canonical `Grounding/Hazard/Evidence`.
All three grounding calls receive exactly the same complete twelve-ID prompt.
No `detect red square`, target hint, predicted class, expected annotation or
previous call output is passed to the model.

| Call | Coverage slot (input still required) |
| --- | --- |
| C_LEVEL01 | Canonical Level01 under the supplied production policy |
| C_LEVEL02 | Canonical Level02 under the same policy |
| C_LEVEL03 | Canonical Level03 under the same policy |
| C_LEVEL04 | Canonical Level04 under the same policy |
| G_SMOKE | One positive SMOKE hazard |
| G_OPEN_FLAME | One positive OPEN_FLAME hazard |
| G_NONE | No listed hazard |

Seven is minimal for four levels, two distinct hazard labels and one negative.
No multiple-hazard runtime case: the frozen gate consumes one `ProbePrediction`
per target case and does not require multiple hazards. No sixth/seventh gate
shape-label exploration or repeated position/size matrix is added.

## Fail-closed adapter and runtime

`safeshift/runners/paligemma_compatibility.py` is qualification-only; the production
`PendingPaliGemmaAdapter` remains unchanged.

- Classification accepts exact canonical JSON with a single `safety_level`.
  Bare levels, yes/no, case changes, fuzzy labels and extra fields fail closed.
- Grounding accepts exact canonical hazards/evidence JSON, with a strict bounds
  check before the generic canonical validator so its D8 clamp cannot run on
  out-of-range PaliGemma coordinates. No correction of box geometry.
- Alternatively, complete native four-loc groups must carry exact D6 hazard IDs
  in the output itself. Fixed grammar is four adjacent loc tokens, one ASCII
  space, the ID, optional further groups separated by ` ; `, and final EOS.
  Token IDs and loc strings must agree. This is a predeclared acceptance candidate,
  **not** a statement that PaliGemma has emitted this grammar. No native prompt
  override or new task schema is introduced.
- Native order `[y_min,x_min,y_max,x_max]` maps through the existing D9R7 helper
  to `[x_min/1024.0,y_min/1024.0,x_max/1024.0,y_max/1024.0]`.
  No /1023, clamp, repair, GT label inference, box fabrication or box selection.
- Explicit canonical `{"hazards":[]}` is accepted. Empty/EOS-only/free text stays
  INVALID. A parseable hallucination on G_NONE is retained unchanged.
- The existing 32-token greedy D9R11 cap remains fixed. Missing EOS/truncation is
  invalid; no retry, prompt adjustment or token-budget increase. This cap can
  limit canonical JSON grounding and must be visible during Lead review.

`scripts/w2_paligemma_canonical_compatibility.py` reuses the audited runner,
VerifiedRawStore and D9R11 persist_verified helper. Exact checkpoint:
`google/paligemma-3b-mix-448`,
revision `ead2d9a35598cb89119af004f5d023b311d1c4a1`.
One process-visible T4, FP16, quantization NONE, no offload/fallback, exact pinned
software/snapshot, offline socket denial, one model load, seven independent calls.
The runner's existing HANDCRAFTED_RUNTIME_SMOKE source-kind is retained solely for
the permitted external/synthetic inputs; every case carries actual provenance.

Raw bytes are exclusively written, flushed/fsynced, reread and SHA/size verified
before JSON deserialization or adapter invocation. Native IDs, decoded fields,
prompt/version/hash, sample/call/run IDs, model/revision, generation config,
software, source commit and input provenance are kept. Runtime/storage failures
stop and retain partial evidence. Invalid outputs are recorded as INVALID/null;
the remaining fixed independent calls continue without retry or repair.

## Notebook and Research Lead decision

`notebooks/w2_paligemma_d9r13_canonical_compatibility_kaggle.ipynb` reuses D9R11's
isolated environment, anonymous checkout, provisioning-only HF_TOKEN, full
snapshot manifests, manual Internet-OFF barrier, fixed attempt and bounded bundle.
It validates approved inputs before installation/provisioning. Notebook execution
source is an exact commit embedded as BASE, not a mutable branch.

Bundle: plan, input/policy provenance, exact image bytes, all seven raw outputs
and metadata, canonical outputs or INVALID/null, snapshots, timing/memory/state
audits, hash inventory and separate classification/grounding review rows.
Expected annotations are documentary coverage only; there is no accuracy score.

Only terminal statuses:
`EVIDENCE_COLLECTION_COMPLETE` or
`STOP_AND_RESEARCH_LEAD_REVIEW_REQUIRED`.
Successful syntax does not auto-PASS the model. Research Lead records
CLASSIFICATION_COMPATIBLE and GROUNDING_COMPATIBLE as YES/NO after reviewing the
raw/canonical evidence, including negative-case hallucinations. If either cannot
map fail-closed, PaliGemma does not advance to synthetic-v1. If both are compatible,
the next step is the unchanged synthetic-v1 gate, not automatic gate execution.

## Validation and boundaries

CPU/static/fake validation: 214 tests (22 D9R13 adapter/harness/notebook checks
plus 192 existing PaliGemma/pre-freeze regressions) PASS. The 33 JSON parses
(32 pre-freeze configurations and the new notebook), scoped nine-file
case-sensitive secret-pattern scan, protected source/gate comparison and diff
check PASS. Exact commands and the source-pin check are recorded in the PR.
Input-only check:
`python scripts/w2_paligemma_canonical_compatibility.py --validate-inputs`
returns STOP / APPROVED_PRODUCTION_POLICY_ARTIFACT_REQUIRED, as expected for the
actual missing inputs. This command does not import a model backend, access GPU,
provision weights, execute a gate or read InspecSafe.

Runtime, Kaggle, model, GPU, synthetic-v1 and InspecSafe were not executed.
The notebook is unexecuted. Classification/grounding qualification remains
PENDING; BACKUP_1, four primaries, protocol freeze BLOCKED, no promotion or merge.
The unrelated untracked census manifest is preserved untouched.
