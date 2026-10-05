# Seminar freeze-readiness reconciliation

## D9R22 current Seminar readiness

Prospective Research Lead scope decision, 2026-10-05; authority:
[D9R22 scope](../configs/pre_freeze/d9r22_seminar_scope.v1.json) and
[decision](../DECISIONS.md#d9r22--prospective-seminar-rq3-disagreement-redesign-2026-10-05).
This section supersedes the [historical D9R18/D9R15 readiness matrix](w2_d9_freeze_readiness_reconciliation.md) for
the current classification-only Seminar, without changing its historical text.
RQ1/RQ2 unchanged; RQ3 is cross-model disagreement and disagreement-aware
reliability from the same classification predictions, with no extra inference.

| Requirement | Current readiness | Meaning / remaining work |
|---|---|---|
| Model provenance | COMPLETE | Recorded provenance for the four D9R18 classification participants; immutable identities unchanged. |
| Runtime runners | COMPLETE | Existing runtime evidence retained; no new model/GPU execution or production qualification implied. |
| Classification participation | COMPLETE | Qwen3, Qwen2.5, InternVL3, Moondream; PaliGemma NOT_PARTICIPATING; SmolVLM2 inactive. |
| External gate history | COMPLETE | Recorded outcomes preserved, including FAIL; does not mean all gates PASS. Grounding gates are not active Seminar blockers. |
| Exact classification production contract | PENDING | Exact prompt, output schema, parse/error and raw-output contract must be specified. |
| Production classification adapters/parsers | PENDING | Implement and qualify against the production contract; runtime evidence alone is insufficient. |
| Exact decoding/preprocessing/precision freeze | PENDING | Freeze model-specific settings and software identities; smoke/gate conditions are not production settings. |
| RQ1/RQ2/RQ3-new metric implementation | PENDING | Preserve D5 classification/statistics; specify exact RQ3 contract and implement all active metrics. |
| Production benchmark harness | PENDING | Reproducible classification-only orchestration, raw-before-parse persistence and artifact linkage. |
| End-to-end rehearsal | PENDING | Validate production path on permitted non-InspecSafe fixtures under separate task authority. |
| Implementation freeze | PENDING | Exact reviewed code/config/artifacts after the above work. |
| Protocol freeze | PENDING | No freeze SHA or inference authority issued by D9R22. |

`PRIMARY_SEMINAR_GROUNDING=DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE` applies to
primary and exploratory grounding. It is a future thesis extension, not a
scientific FAIL, a deleted research history or a promotion. Grounding is no
longer a prerequisite for Seminar freeze or a blocker to RQ1/RQ2/new-RQ3.
`CALL2_ORCHESTRATION_BLOCKER`, `MOONDREAM_CALL2_ORCHESTRATION_BLOCKER` and
exploratory grounding blockers are `NOT_ACTIVE_SEMINAR_FREEZE_BLOCKER`.
Their underlying historical results, including Qwen3 G5 FAIL, PaliGemma G6 FAIL
and Moondream external gate PASS, keep their original meanings.

The historical D9 config/template, A2 Call 2 requirements and earlier briefs
must be interpreted through this overlay for Seminar scope; no executable
production contract or frozen component is updated in this task.
`inspecsafe_inference_authorized=false`; protocol_freeze_commit_sha=PENDING.
No model/GPU execution, InspecSafe inference or merge. Full validation:
[D9R22 note](w2_d9r22_seminar_scope_redesign.md).
