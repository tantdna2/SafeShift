# D9R19 implementation, before protocol freeze

Task: `W2.6-D9R19-PRODUCTION-IMPLEMENTATION-ADAPTERS-DECODING-D5-REPORTING`.
Date: 2026-10-02. Exact fetched BASE:
`5538064e6ea015f8c15475d488064cae95461cd0`.

`NO_INSPECSAFE_INFERENCE`. No model/GPU execution, downloads, external gate rerun,
dataset images or predictions. Fixtures are handcrafted records and fake native
envelopes. The existing untracked census is not changed or committed; existing
full-suite checks may read its structural metadata under their prior authority.

## Implemented scope

- Machine-readable prospective classification policy:
  [production_execution_policy.d9r19.v1.json](../configs/pre_freeze/production_execution_policy.d9r19.v1.json).
  Four exact immutable revisions; original validated preprocessing, FP16/NONE,
  no-sampling decoding, 32 output tokens, batch one, exact software/runtime,
  prompt and adapter/parser versions. Seed remains null, as in the merged native
  conditions; no cross-hardware bitwise determinism claim. No setting was chosen
  using semantic qualification counts. C1 still requires explicit industry policy.
  Runtime evidence supports these conditions, not claims of benchmark accuracy.
- Qwen3/Qwen2.5 adapters remain byte-for-byte unchanged. Both validate native
  envelopes and pass unchanged `decoded_for_parser` to `strict-json-v1`.
- New closed classification registry exposes only Qwen3, Qwen2.5, InternVL3 and
  Moondream. The latter two reuse D9R16 `CandidateAdapter` native validators
  without changing historical qualification code, prompts or results. InternVL3
  uses exact identity/decoding/token/image boundaries and `decoded_text`;
  Moondream requires the exact lossless dictionary with one string `answer`.
  No strip, casing changes, aliases, marker mapping or repair. Historical
  `Pending*Adapter` classes remain historical, separate from this registry.
- D5 classification co-metrics, safety rates, support and confusion matrices;
  class-conditional RQ1 gaps/spreads/observed minima; IMAGE-level RQ2 with all
  twelve atoms and separately labeled A-G union summaries. Missing GT classes
  are NA. Macro summaries report K and support comparability warnings.
- Direct Mode A uses threshold-free maximum-weight assignment; Mode B maximizes
  cardinality then IoU at .25/.50. Polynomial Hungarian implementation tested
  against exhaustive small graphs. Same-class edges, one-to-one matching,
  candidate-region max IoU, unmatched/failed E2E atoms zero. CGI sample/atom
  denominators use explicit independent classification correctness.
- Pointing Hit and PLC use original polygons (boundary included), converting
  original pixels explicitly by image size. Containment uses polygon area per
  **approved D5 decision section 12**, which takes precedence over the older
  decision brief's bbox expression. AtomSize uses polygon area; no size bins.
  Weak Proxy and Direct stay separate; single-person sensitivity is explicit.
- PSR_response measures response syntax and PSR_box valid/attempted items.
  Parse-conditional IoU retains unmatched parsed boxes at zero. Failed response
  diagnostics can carry separately typed hazard identities; never guess them
  from free-text labels. E2E never consumes diagnostic boxes. If an old record
  loses those identities, the diagnostic metric is NA with missing count.
  Unknown failed-response box counts similarly produce NA precision/F1, rather
  than silently removing boxes. Unsupported GT atoms are explicitly excluded;
  predicted claims are never filtered by observed GT membership.
- Domain-stratified point-cluster bootstrap: B=2000, seed=42, 95% percentile CI,
  stable sorted IDs, Python MT19937, linear order-statistic interpolation. B=5000
  is available only as D5's convergence option. No safety-level stratification.
  Original support is fixed for classification macro replicates; missing-class
  replicate NA. Pair callbacks receive identical draws, preserving multiplicity;
  valid paired/B and draw digest reported. No p-value matrix. Caller must supply
  approved logical point/anomaly cluster IDs; source-family is never inferred.
- Deterministic JSON reporting separates classification/RQ1, primary RQ2 atoms,
  grouped exploratory RQ2, primary Direct, primary Weak Proxy, exploratory
  grounding, bootstrap metadata and participation. Nonparticipants have null
  metrics and `NOT_PARTICIPATING`, never artificial zero.

## Exact blockers (no inferred authority)

1. **MOONDREAM_CALL2_ORCHESTRATION_BLOCKER**.
   `DECISIONS.md`, DEC-W2-D8-008 sections 4-5 (A2/B2), and
   `safeshift/protocol/prompts.py::grounding_request` require one independent
   closed-12-hazard response. `notes/w2_moondream_runner_prep.md` native API table
   and `safeshift/runners/moondream2.py::generate_raw` expose
   `detect(image, object: str, settings)` for one object query.
   No approved mapping of 12 hazards to multiple native calls exists. Production
   grounding adapter/orchestration is stopped: no twelve-call loop, point-to-box,
   fabricated box, giant-box rescue, tuning, or arbitrary hazard tagging.
   The PASS external gate (`scripts/w2_moondream_external_gate.py::adapt_native`)
   accepts exactly one object on its synthetic target query; it does not authorize
   generalizing that gate parser to benchmark orchestration.
2. **EXPLORATORY_BENCHMARK_EXECUTION_CONTRACT_BLOCKER** (Qwen3, Moondream,
   PaliGemma). D9R15 policy in `configs/pre_freeze/local_models.d9.json`,
   `exploratory_grounding_track`, explicitly requires separate implementation
   and freeze. It does not specify benchmark prompts, native-call multiplicity,
   hazard mappings or output budgets. Qwen3's gate uses `external_probe`/single
   bbox (`scripts/w2_qwen3_external_gate.py`); PaliGemma's parser uses closed
   synthetic `QUERY_LABELS` and one detection
   (`safeshift/runners/paligemma_external_probe.py`). These are not a closed-12
   benchmark execution contract. Reporting is implemented in a separate namespace;
   execution remains fail-closed. Gate FAILs and primary nonparticipation stay.
3. **CLASSIFICATION_PARSE_FAILURE_POLICY_BLOCKER** (only failed Call-1 rows).
   DEC-W2-D5-005 section 2 defines anomaly FNR by predicted Level04 and
   `1 - recall`; section 14 assigns parse-failure zero only for **grounding**.
   `safeshift/protocol/schema.py::ParseResult` represents classification failure
   with no canonical level. Mapping that failure to Level04, dropping it, or
   changing the binary denominator would invent a metric policy. Classification
   metrics on valid canonical predictions are implemented. On failed Call-1
   inputs, label-dependent summary metrics return explicit NA/blocker; exact
   error counts, support, INVALID-column confusion and parse counts remain.
   Research Lead must resolve this case before claiming complete production D5.

No execution policy is invented for blocked grounding tracks. Classification
policy IDs in current overlays have explicitly classification-only scope.

## Checklist after D9R19

| # | State | Scope |
|---|---|---|
| 1 | COMPLETE | Existing provenance retained |
| 2 | COMPLETE | Existing runtime/runners retained |
| 3 | PENDING | Classification policy implemented; grounding contract blocked |
| 4 | PENDING | Four classification adapters implemented; grounding blocked |
| 5 | COMPLETE | Gate decisions unchanged |
| 6 | ROLE_DECISION_COMPLETE_ADAPTER_QUALIFICATION_PENDING | Decisions resolved, #4 dependency retained |
| 7 | PENDING | Implementation freeze not performed |
| 8 | PENDING | Protocol freeze not performed |

Every `frozen_components` value remains PENDING.
`inspecsafe_inference_authorized=false`; PaliGemma classification
NOT_PARTICIPATING; SmolVLM2 `activated=false`; MERGE=NO.

The D9R18 historical statement “Independent Draft PR review and merge remain
pending” is preserved. This task starts from its merged exact BASE and supersedes
only current implementation status, not historical qualification results.

## Validation

Validation commands, BASE/HEAD comparison and publication are appended below
after execution. Full-suite PASS must not be claimed if historical failures remain.

### Final validation, 2026-10-03 (Asia/Bangkok)

Environment: existing Windows / Python 3.11.9 `.venv`; no package installation.
All new evaluation checks use synthetic records/fake runners, never model or
GPU inference. The existing CPU torch tests account for the known notebook
fresh-kernel errors in full discovery.

- New focused tests: **44/44 PASS** (metrics/geometry/statistics/reporting,
  adapters/policy, current overlays/protected history).
- Expanded focused: **437/437 PASS**.
- Exact BASE before edits: **1316 tests, 4 failures / 24 errors**.
- Final HEAD working tree: **1360 tests, 4 failures / 24 errors**.
  All **28 failure/error identities are identical**; no new regression. Full
  suite is **not PASS**. Existing failures: D9R1 source allowlist, Moondream
  historical roster hash, Ovis and Qwen smoke checklist status assertions.
  The unchanged source-allowlist assertion also lists the newly authorized files;
  it is deliberately not weakened. The 24 notebook fresh-kernel errors remain.
- Strict JSON **3/3 PASS**; `git diff --check` PASS. Exact Git blob checks preserve
  historical qualification plans/cases/results, gate/runtime artifacts, native
  runners, schema and prompts. DECISIONS/TASKS prefixes remain byte-identical.
- Updated historical assertions distinguish the D9R16/D9R18 milestone from
  D9R19-authorized implementation. Current exact overlay delta, role exclusions,
  source bytes and frozen components are independently guarded by new tests.
  No known BASE failure was removed or changed into a skip.

Commands (repository-relative; logs are local, not committed):

```text
.venv/Scripts/python.exe -m unittest tests.test_d9r19_metrics tests.test_d9r19_adapters_policy tests.test_d9r19_overlay -q
.venv/Scripts/python.exe -m unittest tests.test_d9r19_metrics tests.test_d9r19_adapters_policy tests.test_d9r19_overlay tests.test_classification_qualification tests.test_qwen_runner tests.test_qwen2_5_runner tests.test_local_runners tests.test_moondream_external_gate tests.test_d9r18_final_participation_decision tests.test_d9r15_five_model_roster_exploratory_grounding tests.test_internvl3_runtime_result tests.test_model_provenance tests.test_paligemma_external_gate tests.test_pre_freeze tests.test_qwen3_external_gate_result -q
.venv/Scripts/python.exe -m unittest discover -s tests -q
git diff --check
```

BASE full suite ran before any code/config edits in this checkout. HEAD used the
same interpreter, environment and optional census state. Initial HEAD testing
exposed obsolete historical pending-implementation assertions; those assertions
now target their exact milestone or the authorized current state. Final counts
above supersede intermediate validation attempts.

Model/runtime integration on benchmark data is intentionally **not tested**:
NO_INSPECSAFE_INFERENCE and the grounding/Call-1 policy blockers prohibit it.
Implementation/protocol freeze and independent review remain pending.
