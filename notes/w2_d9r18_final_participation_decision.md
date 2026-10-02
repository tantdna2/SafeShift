# D9R18 final participation and roles

Research Lead decision, 2026-10-02; task `W2.6-D9R18-FINAL-PARTICIPATION-AND-ROLES`.
Exact fetched main/BASE: `93e1004de311588e94356e19edf53220de13e194`.
Authority: the Research Lead's explicit D9R18 instructions.
Machine-readable authority: [decision](../configs/pre_freeze/d9r18_final_participation_decision.v1.json).

Four classification participants: Qwen3, Qwen2.5, InternVL3 and Moondream.
PaliGemma classification is NOT_PARTICIPATING due to its objective interface/format
blocker (0/8 parse SUCCESS, 8/8 INVALID, canonical null). All five remain primary
research roster members. Roster membership != classification participation.

Qualification verdicts remain unchanged: Qwen3 PASS; Qwen2.5, InternVL3 and
Moondream semantic FAIL with valid canonical output; PaliGemma format FAIL.
Synthetic semantic failure must not performance-filter or rank models before the
real benchmark. Counts, execution provenance and evidence limits remain in
[D9R17A](../configs/pre_freeze/qwen2_5_classification_qualification_result.v1.json)
and [D9R17B–E](../configs/pre_freeze/d9r17b_e_classification_qualification_results.v1.json).
Their historical PENDING_REVIEW and pending role/participation statements are
resolved by this decision overlay, without rewriting historical evidence bytes.

SmolVLM2 remains activated=false. Four classification participants suffice for the
current seminar protocol; exactly five are not required. D9R18 avoids additional
runtime/qualification workload before freeze. This is neither backup failure nor
model replacement, and does not change the historical replacement policy.

Primary and exploratory grounding roles are unchanged. Moondream retains external
gate PASS and GATE_ELIGIBLE_PRODUCTION_ADAPTER_PENDING; its production adapter
remains NOT_QUALIFIED. Exploratory includes Qwen3, Moondream and PaliGemma only;
it cannot override qualification, and PaliGemma's historical grounding FAIL remains.

Current overlays use `classification_participation` separately from
`classification_qualification_verdict` and `qualification_result_reference`.
Legacy `classification=CANDIDATE`, `classification_role=PENDING_FINAL_GATE` and
`classification_interface_status=PENDING_QUALIFICATION` are retained for historical
compatibility, explicitly superseded for current participation/qualification.
Production adapter fields remain current and are not promoted by this decision.

Checklist #1/#2/#5 COMPLETE; #3/#4/#7/#8 PENDING. Under the existing
[readiness authority](w2_d9_freeze_readiness_reconciliation.md#readiness-matrix),
#6 is ROLE_DECISION_COMPLETE_ADAPTER_QUALIFICATION_PENDING. The role decisions are
complete; the remaining production adapter qualification dependency belongs to #4.
No checklist definition or frozen component is changed to claim completion.

No model/GPU execution or rerun, qualification rerun, prompt/parser repair, alias
mapping, lowercase normalization, output reinterpretation, roster removal, backup
activation or D5 implementation. InspecSafe NOT_RUN / unauthorized; protocol freeze
PENDING. Draft PR only; no merge.

## Validation

Windows / Python 3.11.9, existing `.venv`; Pillow 12.3.0, torch 2.6.0+cpu.
No dependency installation, real model/GPU/gate/InspecSafe execution. Tests use
static/fake inputs. Existing census is only checksum-checked if present by
historical tests, never used for inference or committed. No random experiment.

- New D9R18 tests: **17/17 PASS**; core D9R16/D9R17/D9R15 regression:
  **96/96 PASS**, including the new tests.
- Extended roster/provenance/grounding regression: **178 tests, 177 PASS,
  one existing D9R1 allowlist failure**. The same failure occurs at BASE.
- Same-environment full suite: exact BASE **1299 tests, 8 failures / 24 errors**;
  D9R18 **1316 tests, 4 failures / 24 errors**. No new failure/error identities;
  all 28 remaining identities also occur at BASE. **No full-suite PASS**.
- Four BASE failure instances are Windows LF/CRLF comparisons in D9R17 tests:
  roster and freeze-template byte subtests, prior-test-patch byte assertion,
  and append-only history assertion. Historical scope tests now read the exact
  completed Git snapshot; append-only compares exact Git checkout bytes.
  Current D9R18 tests independently guard the full allowed file set and exact
  semantic overlay delta, without exempting runtime code or historical results.
- The remaining failures are the historical D9R1 source allowlist, Moondream
  roster hash, and Ovis/Qwen smoke checklist assertions. The same 24 notebook
  fresh-kernel errors occur after torch import during full-suite discovery.
- D9R17 result files retain exact BASE checkout bytes **and identical Git blob
  IDs**. D9R16 plan/cases/eight fixtures retain exact Git bytes. No result file
  was rewritten or newline-normalized. DECISIONS/TASKS retain their entire
  original checkout-byte prefixes, with additions only.

Commands from repository root (BASE full suite runs in a separate detached
worktree at the exact BASE, using the same `.venv` interpreter):

```text
.venv/Scripts/python.exe -m unittest tests.test_d9r18_final_participation_decision -q
.venv/Scripts/python.exe -m unittest tests.test_d9r18_final_participation_decision tests.test_d9r17b_e_classification_qualification_results tests.test_qwen2_5_classification_qualification_result tests.test_d9r15_five_model_roster_exploratory_grounding tests.test_classification_qualification -q
.venv/Scripts/python.exe -m unittest tests.test_d9r18_final_participation_decision tests.test_d9r17b_e_classification_qualification_results tests.test_qwen2_5_classification_qualification_result tests.test_d9r15_five_model_roster_exploratory_grounding tests.test_classification_qualification tests.test_d9_t4_roster_revision tests.test_model_provenance tests.test_qwen3_external_gate_result tests.test_qwen2_5_external_gate_result -q
.venv/Scripts/python.exe -m unittest discover -s tests -q
git diff --check
git diff --cached --check
```

Local logs/comparison remain ignored under `data/processed/d9r18/`:
`focused-tests.log`, `focused-extended.log`, `base-isolated-tests.log`,
`head-tests.log`, `test-comparison.json`. Only the isolated BASE run is used
in the comparison; the earlier overlapping working-tree run is discarded.
Strict JSON validation of the three new/updated configs and diff checks PASS.
The final task commit/PR identify the tested implementation; publication does
not authorize protocol freeze, execution or merge.
