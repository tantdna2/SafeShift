# D9R3 — freeze-readiness reconciliation

Task: `W2.6-D9R3-FREEZE-READINESS-RECONCILIATION`, 2026-09-28.
Base main: `a92f9d65e1210b4b276ff04620560d172fcc2225`.

Current overlay on D9R1–D9R2N; historical milestone text, provenance snapshots,
runtime plans and original result artifacts keep their recorded meanings.
The current machine-readable per-model status is
[local_models.d9.json](../configs/pre_freeze/local_models.d9.json).
The freeze-template `current_status_overlay` points there; its older per-model
candidate/pending fields remain template milestones, not current runtime/gate
verdicts. Provenance remains the B0/D9R1 documentary snapshot: its historical
runtime/runner/spatial fields are not later execution results (as enforced by
the existing D9 roster tests). Its bytes are protected by the historical Qwen3
gate plan and remain unchanged. No new status enum or policy is introduced.

## Readiness matrix

| # | Prerequisite | Current readiness | Evidence and exact remaining blocker |
|---|---|---|---|
| 1 | Model provenance | COMPLETE | Documentary IDs, immutable pins, license/access metadata for four primaries and two ordered backups are complete in [provenance](../configs/pre_freeze/local_model_provenance.d9.json). This is not use clearance or implementation freeze. |
| 2 | Runners | COMPLETE | Qwen3, Qwen2.5, Moondream and InternVL3 offline runners are COMPLETE; all four recorded runtime smoke statuses are PASS_VALIDATED. Qwen3 retains its T4×2 anchor exception; Qwen2.5, Moondream and InternVL3 have single-T4 evidence. Production adapters are separately blocked under #4. |
| 3 | Decoding | PENDING | Every primary still has `decoding_policy_id`, `precision_or_quantization` and `preprocessing_id` PENDING in the freeze template; `research_precision_decoding_prompts_frozen=false`. Final per-task low-variance decoding, output limits, supported sampling/thinking controls, seed/determinism policy and exact preprocessing/precision/software condition have not been approved and frozen. Smoke/gate settings are bounded qualification conditions, not the final research configuration. |
| 4 | Adapters/parsers | PENDING | Moondream production `PendingMoondreamAdapter` remains `parser_version=NOT_QUALIFIED`, grounding UNSUPPORTED and classification INVALID. Its gate-only conversion has passed the external gate; it is not wired into or qualified as the production adapter. Classification qualification/parser mapping remains outstanding; all four models remain classification CANDIDATE. InternVL3's canonical spatial interface remains unqualified. Qwen grounding nonparticipation requires no rescue or fabricated boxes. |
| 5 | External gate / interface eligibility | COMPLETE | Qwen3 FAIL → grounding NOT_PARTICIPATING; Qwen2.5 FAIL → grounding NOT_PARTICIPATING; Moondream PASS → grounding qualification PASS for the frozen external native-detect interface; InternVL3 has no qualifying native box interface → grounding NOT_PARTICIPATING and gate NOT_RUN (ineligible, zero cases). D9 eligibility is resolved for every primary, and gate execution remains limited to qualifying box interfaces. |
| 6 | Final roles | PENDING | Classification remains CANDIDATE for all primaries; final classification/grounding roles need approved qualification evidence and #4/#5 resolution. No automatic Moondream role promotion. No backup activated; PaliGemma then SmolVLM2 remain ordered backups. Grounding-only failure does not trigger substitution. |
| 7 | Implementation freeze | PENDING | Freeze exact prompts/task policy, canonical schema, adapters/parsers, runners, preprocessing, precision/quantization, decoding, software environment and full unchanged D5 engine after outstanding qualification. All `frozen_components` remain PENDING; existing code/schema is not a completed implementation freeze. |
| 8 | Protocol freeze | PENDING | #3, #4, #6 and #7 remain unresolved and no approved freeze commit exists. `protocol_freeze_commit_sha=PENDING`; `inspecsafe_inference_authorized=false` in all three D9 configs. |

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

## Validation

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
