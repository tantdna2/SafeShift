# D9R22 prospective Seminar scope redesign

Task: `W2.6-D9R22-SEMINAR-RQ3-DISAGREEMENT-REDESIGN`, 2026-10-05.
Exact remote main / BASE: `a227e18330b49fb8f848934da164a776bc9f6a50`.
Authority: Research Lead's task A and same-session remote-main correction.
Local main may be stale; it is neither the base nor changed by this task.

Current title: SafeShift: Benchmarking Cross-Domain Robustness and Disagreement-Aware Reliability in Vision-Language Models for Industrial Safety Assessment

The [append-only decision](../DECISIONS.md#d9r22--prospective-seminar-rq3-disagreement-redesign-2026-10-05)
and [scope JSON](../configs/pre_freeze/d9r22_seminar_scope.v1.json) define the
prospective classification-only Seminar. RQ1 preserves five-domain zero-shot
classification robustness and platform co-variation without causality. RQ2
preserves Level01–Level04, 12 primary Hazard Atoms, seven secondary exploratory
A–G groups, image-level prediction and non-additive overlapping strata.

RQ3 is now Cross-Model Decision Consistency and Disagreement-Aware Reliability
under Domain Shift. It asks whether cross-model disagreement varies by domain
and hazard stratum and identifies error-prone or safety-critical cases. It
uses only the four participants' classification predictions from RQ1/RQ2;
no predictions are generated here. There is no extra inference, textual
confidence, training, fine-tuning, semantic/benchmark-score model selection,
InspecSafe threshold tuning, or fifth ensemble participant.

Nine families are predeclared in the JSON, without formulas/implementation or
arbitrary thresholds in PR A. A later contract must resolve denominators and
joint parse availability, invalid/missing outputs, ordinal distance, kappa
degeneracy, shared-error definitions, tie handling for risk–coverage, and
uncertainty under the existing dependence policy before production freeze.
High agreement does not establish correctness, calibration, causality or
independent evidence from four models; correlated errors and shared blind
spots remain explicit research limitations. No reliability benefit is claimed.

Grounding is DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE, including exploratory
grounding. It is retained for a future thesis extension, not erased or called
a scientific FAIL. Its blockers are NOT_ACTIVE_SEMINAR_FREEZE_BLOCKER;
historical FAIL/PASS and qualifications are never rewritten. D4, D5 grounding,
D6/D7/D8, G5/G6, D9R19G*, D9R20/D9R21 and all code, fixtures and source audits
remain unchanged. D6 taxonomy still applies to RQ2. No candidate is added,
PaliGemma remains NOT_PARTICIPATING and SmolVLM2 is not activated.

Sources are repository decisions and Research Lead authority, not new model
observations: D1–D3; D5 and approved RQ2 hierarchy erratum; D6/D7/D8;
[D9R18 decision](w2_d9r18_final_participation_decision.md); and preserved
G5/G6 and D9R20/D9R21 records at BASE. The old title and old RQ3 in historical
briefs remain evidence of the former research scope. The scope JSON plus
[current readiness](w2_d9r22_seminar_readiness.md)
take precedence over those old Seminar statements and the old D9 template's
grounding freeze dependencies. D9R18 continues to govern model identities and
classification participation. This is a documentary overlay; no runtime
consumer or production contract is implemented by PR A.

Current readiness has four COMPLETE evidence categories and eight PENDING
production/freeze requirements, enumerated in the JSON and readiness matrix.
COMPLETE runtime/gate history does not qualify production adapters or imply
every gate passed. Raw outputs must still be durably saved before parsing with
sample ID, prompt, model/version, generation configuration and run ID.
inspecsafe_inference_authorized=false; protocol_freeze=PENDING.

## Validation

Offline static/fake tests only. No model/GPU execution, model downloads,
InspecSafe inference or inspection of InspecSafe images. Test logs and exact
BASE checkout stay local under ignored `data/processed/d9r22/`.
Focused scope tests check strict JSON, scientific invariants, exact protected
Git blobs or Git-configured checkout bytes, append-only logs and the complete
change allowlist. The pre-existing worktree mixes LF and CRLF; protected files
are not rewritten or normalized. DECISIONS/TASKS preserve exact BASE checkout
prefixes. The old readiness note is itself a G3/G5/G6 pinned historical blob,
so current readiness is a separate versioned note; that pinned file is unchanged.

Windows, CPython 3.11.9, existing `.venv`, Pillow 12.3.0, torch 2.6.0+cpu;
no dependency changes or random experiment. Same interpreter/environment and
live origin/main for BASE and HEAD; BASE is a detached worktree at the exact
commit above, while HEAD is the final D9R22 implementation recorded by Git/PR.

| Check | Exact BASE | D9R22 HEAD |
|---|---|---|
| Focused D9R20 historical guard | PASS | PASS |
| New focused scope tests | Not present | 17/17 PASS |
| Relevant regression plus scope tests | 116 tests: 114 PASS, 2 SKIP | 133 tests: 131 PASS, 2 SKIP |
| Full discovery | 1504 tests: 5 failures, 25 errors, 2 skips | 1521 tests: 5 failures, 25 errors, 2 skips |
| Diff / staged diff checks | N/A | PASS |

`NEW_FAILURE_IDENTITIES_VS_BASE=0`. The full suites were rerun in the same
environment after correction: BASE 109.488s, HEAD 118.805s. All 30 BASE
failure/error identities below persist with no additions or removals. Full
suite remains **NOT PASS** because of those pre-existing failures/errors;
the D9R20 guard regression is resolved, not accepted as a new failure.
Focused guard + scope: 18/18 PASS. Two new scope tests account for the increase
from 1519 to 1521 total tests compared with the original PR #79 HEAD.

### Authorized historical guard scope correction

Task `W2.6-D9R22-REGRESSION-GUARD-SCOPE-CORRECTION` continues PR #79 from
`1e869440acfdfca132ab118ed589b8e6eb51edc9`, with origin/main still equal to the
exact D9R22 BASE above. This is a narrow Research Lead-authorized test correction,
not a new research decision. The earlier validation record in TASKS.md describes
the original HEAD; the corrected validation here supersedes that test status.

The original D9R20 guard used `git diff --name-only r.BASE` and live log bytes,
so future README/ROADMAP edits were incorrectly treated as D9R20 changes. The
guard is prospectively corrected to pin the historical D9R20 BASE→MERGE range:

```text
D9R20_BASE=668aae839bbde91b67686d143259e07c8a89608c
D9R20_IMPLEMENTATION_HEAD=b86a3af6754ae238c08f9b5e727df7750fdebd61
D9R20_MERGE_COMMIT=7976e5c60817319481c564ca1a68f24aec270da8
```

It verifies both ordered merge parents, compares only that explicit range and
reads both versions of DECISIONS/TASKS from Git. The historical invariant stays
enforced: D9R20 changed no pre-existing files except append-only DECISIONS/TASKS.
No skip, xfail, deleted guard, widened historical file allowlist or live-HEAD
exception for README/ROADMAP is used. Current D9R22 title/scope remains intact.

D9R22 still checks the live PR-A scope against exact BASE `a227e183...`; its
allowlist adds only the specifically authorized D9R20 test file. Two new tests
restrict that file's executable changes to the guard and three historical pins,
and exercise rejection of prohibited historical file edits, swapped merge
parents and rewritten logs. D9R20/D9R21 configs/fixtures/results, G5/G6 and
all research/runtime artifacts remain unchanged. Correction changes only the
two test files and this note; TASKS.md and DECISIONS.md are untouched.

The two skips are optional downloaded source-cache audits with caches absent.

BASE/HEAD shared failure/error identities (unittest discovery names):

```text
FAIL test_d9_t4_roster_revision.D9T4RosterRevisionTests.test_23_only_explicitly_authorized_post_d9r1_runner_source
FAIL test_d9r18_final_participation_decision.FinalParticipationTests.test_only_explicit_decision_documentation_and_test_files_change
FAIL test_moondream_precision.PrecisionBridgeTests.test_protected_files_match_exact_base_hashes
FAIL test_ovis_gpu_smoke_result.OvisSmokeResultTests.test_research_claims_grounding_and_checklist_remain_pending
FAIL test_qwen_kaggle_smoke_result.SmokeResultTests.test_claims_grounding_and_checklist_boundaries
ERROR test_grounding_multicategory_runtime_v3.ContractTests.test_dry_preflight_blocks_without_authority
ERROR test_paligemma_d9r11_notebook.FakeFlowTests.test_barrier_no_runtime_or_attempt
ERROR test_paligemma_d9r11_notebook.FakeFlowTests.test_bundle_size_and_path_guards
ERROR test_paligemma_d9r11_notebook.FakeFlowTests.test_complete_fake_run_exports_exact_raw_no_weights_cache_or_secret
ERROR test_paligemma_d9r11_notebook.FakeFlowTests.test_native_failure_stops_and_exports_partial_bundle
ERROR test_paligemma_d9r11_notebook.FakeFlowTests.test_secret_isolation_and_no_rewrite_of_suspected_raw
ERROR test_paligemma_d9r9_notebook.OrchestrationTests.test_bundle_allowlist_preserves_raw_and_excludes_weight_and_cache
ERROR test_paligemma_d9r9_notebook.OrchestrationTests.test_bundle_refuses_secret_in_raw_without_rewriting_it
ERROR test_paligemma_d9r9_notebook.OrchestrationTests.test_checkout_rejects_untracked_file
ERROR test_paligemma_d9r9_notebook.OrchestrationTests.test_command_redacts_before_log_and_raises_on_failure
ERROR test_paligemma_d9r9_notebook.OrchestrationTests.test_evidence_path_traversal_and_size_rejected
ERROR test_paligemma_d9r9_notebook.OrchestrationTests.test_fake_runtime_export_success_checksum_failure_and_native_failure
ERROR test_paligemma_d9r9_notebook.OrchestrationTests.test_missing_secret_stops_without_provider_exception
ERROR test_paligemma_d9r9_notebook.OrchestrationTests.test_online_fake_sequence_and_install_failure_no_provision
ERROR test_paligemma_d9r9_notebook.OrchestrationTests.test_research_lead_timing_sequence_accepts_noop_load_reentries
ERROR test_paligemma_d9r9_notebook.OrchestrationTests.test_runtime_attempt_cannot_be_retried
ERROR test_paligemma_d9r9_notebook.OrchestrationTests.test_runtime_attestation_is_hard_barrier
ERROR test_paligemma_d9r9_notebook.OrchestrationTests.test_runtime_environment_does_not_inherit_secrets_or_python_config
ERROR test_paligemma_d9r9_notebook.OrchestrationTests.test_timing_observer_only_records_target_spans_and_syncs
ERROR test_paligemma_d9r9_notebook.OrchestrationTests.test_timing_validator_still_rejects_reload_errors_and_missing_spans
ERROR test_paligemma_external_gate.HarnessTests.test_notebook_reviews_fake_bundle_without_auto_pass
ERROR test_paligemma_external_gate.NotebookTests.test_failure_bundle_keeps_partial_raw_exact_and_excludes_weights
ERROR test_paligemma_external_gate.NotebookTests.test_no_credential_in_offline_process
ERROR test_paligemma_external_gate.NotebookTests.test_offline_barrier_and_no_retry_precede_runtime
ERROR test_paligemma_external_gate.NotebookTests.test_secret_export_refused_without_raw_rewrite
```

The shared 25 errors comprise the stale G4 main-identity guard plus 24 notebook
fresh-kernel guards after CPU torch import during discovery. The shared five
failures are historical source/scope allowlists, the Moondream roster hash and
two outdated runtime checklist expectations. They are left outside this task.

Commands from repository root (the BASE run uses the same absolute interpreter
from its detached checkout; no machine path is committed):

```text
.venv/Scripts/python.exe -m unittest tests.test_d9r22_seminar_scope -q
.venv/Scripts/python.exe -m unittest tests.test_d9r20_candidates.Contracts.test_historical_files_and_append_only_logs tests.test_d9r22_seminar_scope -q
.venv/Scripts/python.exe -m unittest tests.test_d9r22_seminar_scope tests.test_classification_qualification tests.test_grounding_multicategory_v4 tests.test_d9r20_candidates tests.test_grounding_execution_relock_g5 tests.test_grounding_execution_relock_g6 -q
.venv/Scripts/python.exe -m unittest discover -s tests -q
git diff --check
git diff --cached --check
```

BASE regression omits only the new D9R22 module, absent at BASE. Correction logs
under `data/processed/d9r22/`: `correction-base-full.log`,
`correction-head-full.log`, `correction-regression.log`. Earlier development and
pre-correction logs are not current validation evidence.
Untracked user `.worktrees/` and the local census remain uncommitted; no data,
weights or raw model output is staged. No task B, protocol freeze, Antigravity
or merge. Draft PR delivery identifies the exact commit; it grants no execution.
