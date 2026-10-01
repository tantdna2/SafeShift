# D9R17A — Qwen2.5 classification qualification result

RUN_STATUS=FAIL; cause=SEMANTIC_CLASSIFICATION_FAILURE; runtime failure=NONE.
FORMAT/PARSER=8/8 SUCCESS; exact_expected_count=3, total_cases=8, descriptive
qualification evidence only. The predeclared PASS rule requires 8/8 exact
expected levels. This is not a benchmark accuracy measurement or model ranking.

REVIEW_STATUS=PENDING_REVIEW; MODEL_ROLE_AFTER_RUN=PENDING_RESEARCH_LEAD_REVIEW;
CLASSIFICATION_PARTICIPATION_DECISION=PENDING. Run FAIL does not remove the model.
Qwen2.5 classification remains CANDIDATE in the unchanged five-model roster.

## Authority and evidence limits

Recorded 2026-10-01 from Research Lead's supplied findings for
`W2.6-D9R17A-QWEN2_5-CLASSIFICATION-QUALIFICATION-RESULT`.
The Research Lead directly inspected the bundle, JSON records, raw envelopes,
raw SHA-256/size and metadata before assigning this recording task. Codex did
not independently inspect or rehash the bundle. Bundle/raw bytes and weights
are not committed; this record contains only the supplied compact evidence.

- Model: `Qwen/Qwen2.5-VL-3B-Instruct`.
- Revision: `66285546d2b821cf421d4f5eb2576359d3770cd3`.
- Execution commit and recording BASE: `7154c6187de7d8ecc5ad4ac5d0aafb68d2d7c1ab`.
- Run ID: `d9r17a-qwen2_5-classification`.
- Execution authorization: `DEC-W2-D9R17A-QWEN2_5-CLASSIFICATION-QUALIFICATION-EXEC-001`.
- Bundle SHA-256: `aa30fd9b19ead3889595394eb8499699233bfceb483446e05b342b15149d72e1`.
- [Machine-readable result](../configs/pre_freeze/qwen2_5_classification_qualification_result.v1.json)
  records exact per-case decoded strings, raw envelope hashes/sizes and runtime pins.

## Case evidence

All eight parse statuses are SUCCESS. Seven canonical outputs are Level01 and
one is Level03. No causal explanation or model-bias inference is established.

| Case | Expected | Observed canonical | Exact expected match |
| --- | --- | --- | --- |
| cq_01 | Level01 | Level01 | true |
| cq_02 | Level01 | Level01 | true |
| cq_03 | Level02 | Level01 | false |
| cq_04 | Level02 | Level01 | false |
| cq_05 | Level03 | Level03 | true |
| cq_06 | Level03 | Level01 | false |
| cq_07 | Level04 | Level01 | false |
| cq_08 | Level04 | Level01 | false |

Per Research Lead verification, all eight raw envelopes were persisted before
parsing, each 7,418 bytes, with SHA-256 and size matching result records.
Pre-parser metadata retains parse_status=NOT_ATTEMPTED and
source_kind=EXTERNAL_CLASSIFICATION_QUALIFICATION. No parser repair, markdown
stripping, retry or alternate prompt was used. These raw envelope hashes are
not hashes of the short decoded strings reproduced in the result artifact.

## Runtime and preserved contract

Supplied runtime evidence: one model load, eight classification calls, zero
grounding calls; one visible Tesla T4, cuda:0, compute capability [7,5],
15,636,037,632 bytes VRAM, CUDA 12.4, FP16/NONE. Exact software pins, verified
snapshot total 7,520,918,095 bytes and both weight-shard hashes are recorded in
the result JSON. No runtime failure. Venue Internet OFF is attested by the
execution attempt; existing runtime offline environment and network-denial
guards were enforced. No stronger network-isolation claim is made.

The [D9R16 manifest](../configs/pre_freeze/classification_qualification_cases.v1.json)
and [plan](../configs/pre_freeze/classification_qualification_plan.v1.json) remain
byte-unchanged. Their hashes in this record are checked against repository BASE
bytes, not independently against the external bundle. The plan deliberately
retains classification_results=NOT_RUN as its historical PREP state. This new
result supplies the completed Qwen2.5 observation only; other models are not
assigned results. The earlier Qwen2.5 smoke result is also historical and intact.

No prompt, parser, fixture, PASS rule, production adapter, backup activation,
roster, D5, grounding gate/history or D9R15 exploratory policy changes.
ROSTER_MEMBERSHIP_CHANGED=false; PRODUCTION_ADAPTER_PROMOTED=false;
AUTOMATIC_RERUN=false; REAL_MODEL_RERUN=NO; INSPECSAFE=NOT_RUN / unauthorized;
PROTOCOL_FREEZE=PENDING. Separate Research Lead participation review remains
pending. No model/GPU execution, adapter rescue, protocol freeze or merge here.

## Validation

Offline record and static/fake regression tests only, Windows Python 3.11.9 in
the existing `.venv`; no dependencies installed. The local test environment is
distinct from the supplied real T4 runtime pins above.

```text
.venv/Scripts/python.exe -m unittest tests.test_qwen2_5_classification_qualification_result tests.test_classification_qualification tests.test_qwen2_5_external_gate_result tests.test_d9r15_five_model_roster_exploratory_grounding -q
.venv/Scripts/python.exe -m unittest discover -s tests -q
git diff --cached --check
```

Focused **64/64 PASS**, including 13 new record tests. Strict JSON, exact
identity/bundle/case/raw/runtime pins, unchanged verdict calculation, prospective
manifest/plan byte equality, protected production/roster/D5/grounding state,
append-only history, pending freeze and unauthorized InspecSafe checks PASS.
The tests check the supplied transcription; they do not verify external raw bytes.

Full suite comparison uses a detached worktree at exact BASE
`7154c6187de7d8ecc5ad4ac5d0aafb68d2d7c1ab` in
`data/processed/d9r17a-base`, the same interpreter, and `unittest discover -s tests -q`
from each checkout root. BASE: **1,263 tests, 4 failures / 24 errors**; result
branch: **1,276 tests, 4 failures / 24 errors**. All 28 failure/error identities
match; no new regression, and no full-suite PASS claim.

The four existing failures are D9R1's runner-source allowlist, Moondream's
historical protected roster hash, and Ovis/Qwen smoke checklist assertions
expecting PENDING instead of COMPLETE. The 24 existing errors are notebook
fresh-kernel guards after full discovery imports CPU torch (D9R9, D9R11 and
PaliGemma external-gate tests). Both runs also report the existing missing-NumPy
warning from CPU torch. These unrelated issues were not repaired or hidden.

Ignored local logs: `data/processed/d9r17a-focused-tests.log`,
`data/processed/d9r17a-base-tests.log`, `data/processed/d9r17a-head-tests.log`.
Staged scope is only the result, this note, append-only DECISIONS/TASKS entries
and new tests. No bundle, raw output, snapshot or existing untracked census
manifest is staged. Diff whitespace checks PASS. Draft PR only; KHÔNG MERGE.
