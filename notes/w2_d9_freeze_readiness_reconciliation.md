# D9R15 — freeze-readiness reconciliation

Task: `W2.6-D9R15-FIVE-MODEL-ROSTER-AND-EXPLORATORY-GROUNDING`, 2026-09-30.
Base main: `9948570820b5ed8a774b8e226b80e24055e705cf`.

Current overlay through D9R18 (membership and exploratory policy remain D9R15); historical milestone text, model/source evidence,
runtime plans and original result artifacts keep their recorded meanings.
The current machine-readable per-model status is
[local_models.d9.json](../configs/pre_freeze/local_models.d9.json).
The freeze-template `current_status_overlay` points there; its five entries now
separate current primary RQ3 and exploratory participation from final D9R18
classification participation and pending production adapters/frozen components. All model/source documentary
provenance records retain historical runtime/license/runner/spatial facts; only
the current `roster_revision` overlay is reconciled to D9R15 active membership.
The historical Qwen3 gate plan still pins the old provenance bytes; historical
gate tests use that snapshot, while live membership tests compare the current
active key lists with the live roster. The frozen verifier is unchanged and
still rejects the revised provenance file; no gate rerun is authorized.
D9R15 adds a reporting policy only; no executable
metric/gate/parser/runner/schema/prompt change.

## Readiness matrix

| # | Prerequisite | Current readiness | Evidence and exact remaining blocker |
|---|---|---|---|
| 1 | Model provenance | COMPLETE | Five primaries and one unactivated backup match current active key lists in [provenance](../configs/pre_freeze/local_model_provenance.d9.json). Historical model/source documentary records, including roster_group/order, remain unchanged. This is not use clearance or implementation freeze. |
| 2 | Runners | COMPLETE | All five offline runners COMPLETE, runtime PASS_VALIDATED. Qwen3 retains its T4×2 anchor exception; Qwen2.5, Moondream, InternVL3 and PaliGemma have single-T4 evidence. PaliGemma exact runtime verified=true from D9R9. Production adapters remain separate under #4. |
| 3 | Decoding | PENDING | Every primary still has `decoding_policy_id`, `precision_or_quantization` and `preprocessing_id` PENDING in the freeze template; `research_precision_decoding_prompts_frozen=false`. Final per-task low-variance decoding, output limits, supported sampling/thinking controls, seed/determinism policy and exact preprocessing/precision/software condition have not been approved and frozen. Smoke/gate settings are bounded qualification conditions, not the final research configuration. |
| 4 | Adapters/parsers | PENDING | D9R18 participation is decided separately from production adapter qualification. D9R17 qualification verdicts remain unchanged, including PaliGemma interface/format FAIL. Existing production adapters remain unqualified; Moondream and PaliGemma retain NOT_QUALIFIED, classification INVALID / grounding UNSUPPORTED. No parser rescue or qualification override. |
| 5 | External gate / interface eligibility | COMPLETE | Qwen3 GATE_FAIL (5/8 valid), Qwen2.5 GATE_FAIL and PaliGemma FAIL / grounding qualification FAIL (6/8 SUCCESS) → primary NOT_PARTICIPATING. InternVL3 has no qualifying native generic box interface → NOT_PARTICIPATING / gate NOT_RUN. Moondream PASS → gate eligibility only. All five eligibility decisions resolved, not all gates passed. |
| 6 | Final roles | ROLE_DECISION_COMPLETE_ADAPTER_QUALIFICATION_PENDING | D9R18 final classification: Qwen3, Qwen2.5, InternVL3, Moondream PARTICIPATING; PaliGemma NOT_PARTICIPATING for interface/format failure. Five-member roster unchanged; SmolVLM2 unactivated. Primary/exploratory grounding unchanged. Role decisions complete; remaining production adapter qualification dependency belongs to #4. |
| 7 | Implementation freeze | PENDING | Freeze exact prompts/task policy, schema, adapters/parsers, runners, preprocessing, precision/quantization, decoding, software and unchanged D5 engine after qualification. Exploratory reporting needs separate implementation and approval/freeze before InspecSafe. All `frozen_components` remain PENDING. |
| 8 | Protocol freeze | PENDING | #3, #4 and #7 remain unresolved; #6 retains the production adapter qualification dependency under #4. No approved freeze commit exists. protocol_freeze_commit_sha=PENDING; inspecsafe_inference_authorized=false. |

Current decision: [D9R18 participation](w2_d9r18_final_participation_decision.md).
Legacy CANDIDATE / PENDING_FINAL_GATE / PENDING_QUALIFICATION fields retain
pre-D9R18 meanings only; explicit classification_participation and qualification
verdict/reference fields are current. Frozen components remain PENDING.

## Historical D9R15 reconciliation

The narrative below records D9R15; the D9R18 matrix above supersedes its pending
classification-role wording without changing grounding history or adapter status.

D9R15 resolves the D9R6 sole-candidate expansion as roster design, before freeze
and InspecSafe, without performance-based selection. PaliGemma is PRIMARY_5;
this supersedes the old all-contracts-pass membership requirement only. D9R14
PALIGEMMA_PROMOTION=NO remains historical, and its gate/grounding FAIL is current.
The runtime, interface and gate result bytes are unchanged; D9R11 target-absent
hallucination remains a finding. Classification and production adapter qualification
are still pending; runtime PASS does not qualify them.

The [exploratory policy](../configs/pre_freeze/local_models.d9.json) includes
exactly Moondream, Qwen3 and PaliGemma, excluding Qwen2.5 and InternVL3. It cannot
override gates, qualify/promote a model, change the roster after InspecSafe or
tune prompt/parser/threshold. It is not rescue, lowered gate or primary RQ3
participation. Separate tables and a separate implementation/freeze are required.
D5 is unchanged: primary nonparticipants get no synthetic zero; the external
gate has no artificial zero IoU. Future exploratory formulas may reuse D5 only
with the existing D5 end-to-end failure policy and pre-InspecSafe freeze.

Global gate status now reads RESOLVED_CAPABILITY_AWARE (five eligibility
decisions), not all PASS or production ready. Checklist #5's machine key is
renamed to `5_synthetic_gate_primary_models`. Roster membership is resolved;
#3/#4/#6/#7/#8 and protocol freeze remain PENDING, authorization=false.

Current giant-box procedure is RESOLVED_PER_MODEL_SEE_MODEL_EVIDENCE in both
roster and template. Moondream's eight human NO_GIANT reviews support its PASS.
Qwen3/Qwen2.5/PaliGemma automatic FAIL records retain
NOT_REQUIRED_AFTER_AUTOMATIC_GATE_FAILURE; InternVL3 gate NOT_RUN reflects
interface ineligibility. This reconciliation invents no review and changes no gate.

## D9R15 validation

Consistency follow-up from audited head
`98d8c642f3722d426779539c423504e50defa09a`, same branch and Draft PR #62:

- Current provenance active lists now match the LIVE roster (five primaries,
  SmolVLM2-only backup). Tests verify exact D9R15 metadata and unchanged retired
  keys, every model/source record and all other provenance fields; documentary
  content before roster_revision is also compared byte-for-byte with LF normalization.
- Both current giant-review procedure fields are RESOLVED_PER_MODEL_SEE_MODEL_EVIDENCE.
  Tests preserve existing Moondream NO_GIANT reviews, automatic-failure review
  exemptions and InternVL3 gate NOT_RUN. No review was invented or rerun.
- D9R15 tests: **12/12 PASS**. Focused regression below: **215 tests, 214 PASS,
  one existing D9R1 allowlist failure**. Historical Qwen3 gate tests use the old
  pinned provenance in their temporary fake repository; a new test confirms the
  unmodified verifier still rejects the current overlay. Moondream's historical
  provenance hash assertion likewise uses the pinned snapshot; its pre-existing
  live-roster hash failure remains visible in the full suite.
- Full suite: **1232 tests, 4 failures / 24 errors**, same 28 failing/error test
  identities as the exact BASE full run (1219 tests) earlier in this session.
  No new regression; no full-suite PASS. Initial combined focused discovery also
  reproduced notebook fresh-kernel errors when importing the CPU torch test;
  final focused run keeps that module in the full suite only.
- Strict JSON **3/3 PASS**; diff check PASS. Only the three current config overlays
  differ under protected execution/config roots. Historical model/source evidence,
  gate results, plans, metrics, gate/parser/runner code, prompts, schemas and frozen
  fixtures remain unchanged. D9R14 byte SHA-256 remains
  `15aa6943f30115a8c7630132c72512b5372462ef6d3f96b3270f39760dc79fb4`.

Windows / Python 3.11.9, existing `.venv`, static/fake checks only:

```text
.venv/Scripts/python.exe -m unittest tests.test_d9r15_five_model_roster_exploratory_grounding tests.test_d9_t4_roster_revision tests.test_model_provenance tests.test_qwen3_external_gate_result tests.test_qwen3_external_gate tests.test_qwen2_5_external_gate_result tests.test_paligemma_external_gate_result tests.test_paligemma_external_gate tests.test_d9r6_paligemma_primary_expansion_precommit tests.test_d9r7_paligemma_source_api_audit
.venv/Scripts/python.exe -m unittest discover -s tests
git diff --check
```

No model/GPU/gate/InspecSafe execution. Protocol freeze PENDING; independent
audit pending; same Draft PR #62, NOT MERGED.

## D9R15 initial validation (before consistency follow-up)

Windows / Python 3.11.9, existing `.venv`; static/fake tests only. No dependency
installation, GPU/model/gate rerun or InspecSafe inference. The optional existing
local census is only checksum-checked by existing tests, never used as model input
or committed. Test output logs remain local outside Git.

Focused core: **152/152 PASS**, including **10 new D9R15 tests**. Extended focused
run adding `tests.test_d9_t4_roster_revision`: **187 tests, 186 PASS / 1 existing
failure** (`test_23_only_explicitly_authorized_post_d9r1_runner_source`, historical
allowlist missing `paligemma_external_probe.py`). This failure is not hidden or fixed
by expanding this task's scope.

```text
.venv/Scripts/python.exe -m unittest tests.test_d9r15_five_model_roster_exploratory_grounding tests.test_d9r6_paligemma_primary_expansion_precommit tests.test_d9r7_paligemma_source_api_audit tests.test_model_provenance tests.test_qwen3_external_gate_result tests.test_qwen2_5_external_gate_result tests.test_paligemma_external_gate_result tests.test_paligemma_external_gate tests.test_paligemma_runtime_result tests.test_paligemma_interface_candidate tests.test_internvl3_runtime_result tests.test_moondream_prep_audit -q
.venv/Scripts/python.exe -m unittest discover -s tests -q
git diff --check
```

Full suite before configuration/test edits at exact BASE
`9948570820b5ed8a774b8e226b80e24055e705cf`: **1219 tests, 4 failures / 24 errors**.
Full suite after D9R15: **1229 tests, the same 4 failures / 24 errors**.
All 28 failing/error test identities match; **no new regression, no full PASS**.
The other three failures are the historical Moondream roster hash and Ovis/Qwen
smoke checklist assertions requiring PENDING instead of COMPLETE. The 24 errors
are notebook fresh-kernel guards after torch is imported by full-suite discovery.
This comparison ran both full suites in the same environment, not a substituted
roster-only control. D9R6/D9R7/D9R14 historical assertions now explicitly read the
pre-D9R15 Git snapshot; dedicated D9R15 tests protect live state and evidence.

Both changed JSON files pass `safeshift.protocol.schema.strict_json`;
`git diff --check` passes. Protected execution/config roots differ from BASE
only in the roster and unfrozen template at the initial head. The later consistency
follow-up also reconciles the current provenance roster_revision overlay; all
historical model/source evidence remains unchanged. Metrics, gate, parsers, runners,
prompts, schemas, frozen fixtures, historical precommit and result records are
unchanged. D9R14 result file byte SHA-256 before/after is
`15aa6943f30115a8c7630132c72512b5372462ef6d3f96b3270f39760dc79fb4`.
Staged-file review: 16 small text files, no secret-pattern matches, weights,
archives or raw bundles; untracked census excluded. Implementation commit
`c3594f6`; [Draft PR #62](https://github.com/tantdna2/SafeShift/pull/62) targets main.
This documentation follow-up records publication only. Independent review
pending; NOT MERGED.

## Historical reconciliation narrative (D9R3–D9R5)

The D9R3 and D9R4 status prose below is preserved historical milestone text;
the matrix above and the linked D9R5 result are the current overlay.

The global gate status remains PENDING, including the template's
`PENDING_D9_MODEL_EXECUTION`; this means incomplete roster-wide resolution,
not that no primary has executed. The older global giant-box procedure
placeholder does not annul Moondream's recorded eight human reviews; the D9R3
placeholder itself did not establish an InternVL3 procedure or eligibility
decision.
The historical D9R3 statement for InternVL3 was documentary COMPLETE, runner
PENDING and runtime smoke PENDING;
grounding `NOT_YET_DOCUMENTARILY_QUALIFIED`. No roster removal, substitution,
or rationale based on InspecSafe is introduced.

## Evidence and qualification boundaries

- Qwen3: [runtime result](../configs/pre_freeze/qwen_kaggle_smoke_result.v1.json)
  and [external gate result](../configs/pre_freeze/qwen3_external_gate_result.v1.json).
  Gate GATE_FAIL; grounding NOT_PARTICIPATING / SPATIAL_GATE_FAILURE.
- Qwen2.5: [single-T4 result](../configs/pre_freeze/qwen2_5_t4_smoke_result.v1.json)
  and [external gate result](../configs/pre_freeze/qwen2_5_external_gate_result.v1.json).
  Gate GATE_FAIL; grounding NOT_PARTICIPATING / SPATIAL_GATE_FAILURE.
- Moondream: [merged post-fix smoke and D9R2N human review](w2_moondream_postfix_result_external_gate_prep.md),
  [D9R2N decision](../DECISIONS.md#d9r2n-moondream-external-gate-final-result-2026-09-28),
  and [production adapter](../safeshift/runners/moondream2.py).
  Post-fix smoke `moondream-postfix-smoke-20260927T022150Z-1b8def87` at
  `9bc5509ecffcb9d7b2faa4a023cd76bd358e2723` establishes runtime interface and
  native query/detect feasibility on one visible T4. Map this to the existing
  roster terminology `resource_status=PASS_VALIDATED`,
  `runtime_smoke_status=PASS_VALIDATED`, `offline_runner_status=COMPLETE`.
  Gate `moondream-external-gate-20260928T013533Z-d9a1c46b` at
  `c801c899a1b63831175ea47d1d77d77f11f8e115` has final external gate PASS and
  grounding qualification PASS after eight explicit NO_GIANT human verdicts.
  The original runtime artifact remains GATE_PENDING_REVIEW.

- InternVL3: [Research Lead-supplied runtime result](../configs/pre_freeze/internvl3_t4_runtime_result.v1.json)
  for run `internvl3-t4-smoke-20260928-01` records runtime/resource
  `PASS_VALIDATED` at execution commit `088a7ff7f4d2c9fb6b72accc6922d02317643bdf`.
  The archive SHA256 is `e4de47ec85cc5770f97e987f282aa11eb9ea36b3cfb1c0f7e5b64ceac681a74d`;
  its summary SHA256 is `7edcd9219286bd84bde9a5453285e3e2f6cd9c7f839f2b6aa25e189f312c9edd`.
  Exact source/card audit found no qualifying generic native box interface, so
  grounding is `NOT_PARTICIPATING` with reason `NO_DOCUMENTED_GENERIC_SPATIAL_INTERFACE`;
  the external gate was not executed and no eight-case result or artificial zero
  IoU exists. The evidence archive and snapshot remain outside Git.

Moondream's historical official smoke
`kaggle-t4-moondream-smoke-20260926T070217Z-4c2d43` remains FAIL,
`attempt_consumed=true`, `superseded=false`. Post-fix success does not rewrite it.
Classification stays CANDIDATE. **External gate PASS does not mean the production
InspecSafe adapter is ready.** Its grounding UNSUPPORTED / classification INVALID
behavior is unchanged; completing and qualifying it requires a separate task.

This reconciliation uses the merged Research Lead/user reports, including the
Research Lead's independent inspection of the InternVL3 evidence archive; Codex
did not independently inspect that archive. No missing archive path, classification
evidence or gate result is inferred. Policy authority remains
DEC-W2-D9-009 with D9R1 and the D9R2N result; no new research decision is needed.

The later D9R5 result record supersedes the *current unresolved overlay* above
for InternVL3 runtime and interface eligibility only. It preserves the D9R3/D9R4
historical milestone wording and does not freeze decoding, adapters, roles,
implementation or protocol.

## Historical D9R3 validation

**88/88 tests PASS** on Windows / Python 3.11.9, including existing D9 roster,
provenance, Qwen gate-result and Moondream audit regressions. Static checks
verify current statuses, historical smoke preservation, adapter source status,
overlay links and pending freeze/authorization. The historical Qwen3 roster
test now compares its complete model entry, allowing later updates to other
primaries; protected runtime/plan/provenance hashes remain enforced unchanged.

```powershell
.venv/Scripts/python.exe -m unittest tests.test_d9_t4_roster_revision tests.test_model_provenance tests.test_qwen3_external_gate_result tests.test_qwen2_5_external_gate_result tests.test_moondream_prep_audit -q
.venv/Scripts/python.exe -c "import json,pathlib; paths=list(pathlib.Path('configs/pre_freeze').glob('*.json')); [json.loads(p.read_text(encoding='utf-8')) for p in paths]; print('JSON parse PASS:',len(paths),'files')"
git diff --check
```

JSON parse **22/22 PASS**; `git diff --check` PASS. Full repository, runtime,
smoke and live-gate suites were not run: only documentation/config status and
their static regression assertions changed.
Existing D9 roster tests include a read-only checksum of the pre-existing local
census manifest when present; it is not loaded as dataset input or committed.
**NO REAL RUNTIME EXECUTION**: no GPU/model/download, smoke, external gate,
InspecSafe, protocol freeze, final role assignment, backup substitution or merge.
