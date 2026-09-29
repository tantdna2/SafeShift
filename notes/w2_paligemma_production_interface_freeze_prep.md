# W2.6-D9R13-PALIGEMMA-FROZEN-EXTERNAL-GATE-PREP

Latest Research Lead decision supersedes D9R13's discovery and seven-case C1/B2
proposals in the same Draft PR #60. PREP only; no runtime or merge by Codex.
Production classification remains PENDING_QUALIFICATION and does not block this
external object-localization gate.

## Authority and previous-model path

Reuse the existing eight cases A_1, A_2, B_1, B_2, C_1, C_2, D_1, D_2:
- Manifest: `configs/pre_freeze/external_gate_cases.v1.json`.
- Provenance: `configs/pre_freeze/external_gate_cases.v1.provenance.json`.
- Images: `tests/fixtures/pre_freeze/frozen_external_gate/`.
- Loader/scorer: `safeshift/protocol/gate.py:load_cases/evaluate_gate`.
- Provenance generator only: `scripts/generate_external_gate_cases.py`.
  No runtime fixture regeneration.
- Previous-model execution: `scripts/w2_moondream_external_gate.py`,
  `scripts/w2_qwen2_5_external_gate.py`, `scripts/w2_qwen3_external_gate.py`
  load the frozen suite, preserve native response before adaptation, then use
  the same evaluator. Their gate is an external single-object probe, not
  production C1 or B2 qualification.

Use manifest image_path, target_query, target_gt_bbox and distractor_gt_bbox
unchanged. No new GT, metrics, thresholds, acceptance criteria, C1 policy,
Level01–04 scenes, B2 hazards or target-absent case. The paired positions are
required for systematic target tracking, so all eight cases are retained.

## Candidate and runtime

Plan: `configs/pre_freeze/paligemma_external_gate.v1.json`.
Harness: `scripts/w2_paligemma_external_gate.py`.
Parser: `safeshift/runners/paligemma_external_probe.py`.
Notebook: `notebooks/w2_paligemma_d9r13_external_gate_kaggle.ipynb`.

Literal native prompt is `detect {case.target_query}`. Manifest queries are
`Locate the red square.`, `Locate the green circle.`,
`Locate the yellow triangle.`, `Locate the cyan rectangle.`; e.g. the actual
prompt is `detect Locate the red square.`. No noun extraction or prompt tuning.

Parser candidate supports only those four exact returned labels and one
`<locNNNN><locNNNN><locNNNN><locNNNN> LABEL<eos>` response.
D9R7 source-backed loc-token grammar/mapping and D9R11 red-square evidence remain
the basis; green circle/yellow triangle/cyan rectangle are candidates to observe,
not claimed runtime successes. Require EOS/token boundary and loc-ID/text
agreement. Wrong label preserves native text, label and diagnostic box, but has
no canonical prediction and fails the gate. No arbitrary labels or multiple boxes.

Native yxyx maps to canonical probe xyxy:
`[x_min/1024.0, y_min/1024.0, x_max/1024.0, y_max/1024.0]`.
No /1023, clamp, repair, fabricated box, point-to-box or semantic correction.
This candidate is not a production hazards/evidence adapter.

Reuse the unchanged audited runner, snapshot/provisioner, storage and D9R11
persist_verified helper. Checkpoint `google/paligemma-3b-mix-448`, revision
`ead2d9a35598cb89119af004f5d023b311d1c4a1`; single visible T4, FP16,
quantization NONE, one model load, eight native calls, zero classification calls.
Keep 32-token greedy decoding. Incomplete/malformed output fails closed with no
retry or generation-budget increase. The audited runner's legacy
HANDCRAFTED_RUNTIME_SMOKE source-kind tag stays unchanged; every input separately
records actual frozen synthetic provenance and original manifest path/hash.

Preflight hashes the plan, manifest, provenance, generator source, images and
D9R11 negative record. Raw native bytes are exclusively written, flushed/fsynced,
reread and SHA/size verified before parsing. Parser failures finish the eight
independent fixed calls; runtime/storage failures stop immediately, retaining
partial evidence. Fixed run directory refuses retries/overwrites.

Notebook pins execution-source commit (BASE)
`23243484b5874394c7db96604e1580fe6f38d974`. It provisions with HF_TOKEN
only in the provisioning child environment, then requires manual Internet OFF.
Runtime has no tokens, offline environment flags and socket denial. No model
load during provisioning. Run All stops at the manual barrier by default.

## Scoring, human review and bundle

Use unchanged evaluate_gate: valid schema, predicted center inside target,
distractor center excluded, target-position tracking, no full-image prediction,
and explicit qualitative giant-box review. IoU and area are diagnostics only.

Automatic failure yields FAIL; otherwise runtime yields PENDING_REVIEW, not an
invented automatic PASS. Notebook completion is EVIDENCE_COLLECTION_COMPLETE or
STOP_AND_RESEARCH_LEAD_REVIEW_REQUIRED. The original scorer requires human
NO_GIANT/GIANT plus reviewer/rationale for each case before final PASS/FAIL.

Bundle includes frozen authority and D9R11 finding, eight input images, raw bytes
and SHA/size references, native text, parser errors/status, predicted box and both
GT boxes per case, gate metrics/tracking, snapshot and source evidence, timing,
memory, review template and checksums. Raw is never sanitized/rewritten; export
refuses secret-like raw content. No weights/tokens are included.

Follow notebook instructions to fill a separate human-review JSON. Then run
`scripts/w2_paligemma_external_gate.py --expected-commit <BASE> --review-file <relative-review-json>`
on the exact clean source checkout and restored runtime evidence. This is offline
CPU-only revalidation/reparsing/scoring, with zero new model calls. It writes
exclusive final_gate_review.json plus SHA sidecar, retaining the original runtime
report. Submit those two files with the original bundle. PASS does not promote
PaliGemma or qualify production classification.

## D9R11 negative finding and boundaries

`configs/pre_freeze/paligemma_interface_runtime_result.v1.json`, case grd_d:
the target-absent image elicited a parseable red-square detection. Preserve this
negative finding unchanged; Research Lead must consider it in the final model
decision regardless of gate PASS. Do not reinterpret it as successful abstention
or add a PaliGemma-only negative case to the shared frozen gate.

Classification PENDING_QUALIFICATION; grounding/external qualification awaits
actual run and Research Lead review; BACKUP_1; four primaries; freeze BLOCKED;
InspecSafe authorized=false. Missing production C1 policy/qualified scenes does
not block this gate and has not been filled with invented artifacts.

## Verification

Only CPU/static/fake tests and read-only frozen-input verification run by Codex.
Validation: 253 existing related regression tests plus 27 D9R13 tests pass;
33 pre-freeze JSON/notebook files parse strictly; scoped secret scan and diff
checks pass. Execution-source tests match the runtime files to the pinned commit.
Tests exercise all four labels, axes/bounds, closed grammar, label mismatch,
raw-before-parser, failed fsync/hash reread, partial generation failure, fixed
budget/no retry, unchanged frozen sources/scorer, explicit human reviews,
notebook offline barrier, secret refusal and bundle integrity.
No GPU, model, Kaggle, provisioning, actual gate or InspecSafe execution.
