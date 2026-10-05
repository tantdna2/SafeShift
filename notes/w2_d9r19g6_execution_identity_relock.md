# G6 PaliGemma execution identity relock PREP

Date: 2026-10-04. Task:
`W2.6-D9R19G6-PALIGEMMA-EXECUTION-IDENTITY-RELOCK`.

## Scope and base

This PREP starts from the required exact BASE
`069d780b6590a32a19cbe6e341ffa19cedbcd712`, the merge commit after G5 PR #72
and G5R PR #73. The branch is
`w2.6-d9r19g6-paligemma-execution-identity-relock`. The versioned G6 artifacts
are `grounding_multicategory_runtime_lock.v3.json`,
`grounding_multicategory_execution_plan.v2.json`, and the inert authorization
template v2. Historical runtime lock v2, execution plan v1, authorization
template v1, G5 runner/CLI, and all prior evidence remain available and are not
rewritten.

G6 is intentionally PaliGemma-only. Its runner wrapper exposes no Qwen3 model
or run ID and rejects Qwen3 before preflight. The historical Qwen3 record is
protected as `QWEN3_G5_QUALIFICATION=FAIL`,
`QWEN3_PRIMARY_GROUNDING_ROLE=NOT_PARTICIPATING`, `RERUN=NO`,
`PROMOTION=NO`. This task does not reinterpret or rerun that result and does
not change PR #67.

## Fixed PaliGemma identity

| field | value |
| --- | --- |
| model | `google/paligemma-3b-mix-448` |
| revision | `ead2d9a35598cb89119af004f5d023b311d1c4a1` |
| hardware | Kaggle T4 x1 |
| transformers | `4.57.1` |
| precision / quantization | FP16 / NONE |
| decoding | greedy; `do_sample=false`, `num_beams=1`, `num_return_sequences=1`, `max_new_tokens=512` |
| run ID | `g6-paligemma-v3-001` |

The run ID follows the existing `g<generation>-<model>-v3-001` convention and
is predeclared in the plan and lock before any output. No alternative name was
needed.

## Scientific and authority boundaries

The synthetic v3 plan, 12 cases/images, expected geometry, parser grammar,
prompt, gate thresholds/rules, no-retry/no-repair policy and raw-before-parse
ordering are frozen. The G6 wrapper delegates the existing runtime flow and
does not alter parser, geometry or prompt behavior. The tracked authorization
template has `execution_authorized=false`; it contains no signed authority,
observed environment, HEAD or environment hash.

The Draft PR must remain OPEN/DRAFT through environment observation,
independent audit, Research Lead authorization, qualification execution and
human review. A merge changes `origin/main` and invalidates any authority;
there is no merge in this task. Any changed exact HEAD, main, environment hash
or runtime-lock hash requires a new audit and authorization.

## Observation-before-load contract

The future operator must fetch and compare `origin/main` to the exact BASE,
checkout the exact audited Draft PR HEAD, and verify a clean tree before model
load. The observation command records, before loading the model:

- exact HEAD and exact `origin/main`;
- model ID, processor/tokenizer/model revision;
- Python, torch/CUDA, transformers, tokenizers, Pillow, accelerate,
  huggingface-hub and safetensors versions;
- one visible Tesla T4 with compute capability `[7, 5]`;
- every local snapshot file's SHA-256 and byte size;
- G6 code/contract hashes from runtime lock v3; and
- the fixed generation configuration.

Observation writes an ignored artifact under
`data/processed/grounding_v3_g6_review/` with authorization false. It does not
instantiate a processor/model, call `generate`, run GPU inference, run
InspecSafe, promote a model or change the synthetic contract.

## Validation and status

The focused G6 tests cover exact BASE/run/model scope, false authorization,
main/HEAD identity, observation-before-load, historical lock preservation and
Qwen3 rejection. Relevant frozen-runtime/parser/geometry regressions and
`git diff --check` are required. The full suite is not claimed unless it is
actually run. Current status is:

```text
PALI_EXECUTION_AUTHORIZED=NO
MODEL_GPU_EXECUTION=NO
INSPECSAFE=NOT_RUN
PROMOTION=NO
MERGE=NO
```

## G6 qualification result and closure overlay (2026-10-05)

This append-only section records the supplied independently audited result. The
PREP text above, including its historical `NOT_RUN`, `BLOCKED` and `MERGE=NO`
states, remains unchanged.

Execution identity:

- model: `google/paligemma-3b-mix-448`
- revision: `ead2d9a35598cb89119af004f5d023b311d1c4a1`
- run ID: `g6-paligemma-v3-001`
- execution HEAD: `b8a8a40c1d632c4609302daffee52543fe13b39d`
- execution MAIN/BASE: `069d780b6590a32a19cbe6e341ffa19cedbcd712`
- environment SHA-256: `5eedbff47f5a4288f785bba8cb1dfe205c5403411295780b06af8bf09c2a909b`
- runtime lock SHA-256: `237143b33405bc0d03e3c911cf042e9874a089a48cc95d7691883c83e79ce0ad`

Execution recorded `QUALIFICATION_EXECUTION=EXECUTED`, one model load, 12
native calls, `failure=null`, 12/12 EOS, complete artifact audit,
raw-before-parse verification and parser SUCCESS for all 12 calls. Geometry
passed 1/12 and failed 11/12; only `H_all_four` had `geometry_ok=true`.
`tracking_result=false`, `final_verdict=FAIL`, and the independent artifact
audit was PASS.

The failure was frequent extra detection for queried labels with
`expected_count=0`: `A_1` emitted an extra green circle and cyan rectangle;
`E_red_green` an extra cyan rectangle; `F_two_red` an extra green circle,
yellow triangle and cyan rectangle; and `G_multi` an extra cyan rectangle.
`H_all_four` matched exact counts and passed geometry. Because parsing
succeeded 12/12, this is not a parser failure. Extra boxes were not dropped and
outputs were not reinterpreted.

Governance closure:

```text
PALIGEMMA_G6_QUALIFICATION=FAIL
PALIGEMMA_PRIMARY_GROUNDING_ROLE=NOT_PARTICIPATING
RERUN=NO
HUMAN_NO_GIANT_REVIEW_REQUIRED_FOR_DECISION=NO
PROMOTION=NO
INSPECSAFE=NOT_RUN
```

The automated geometry/tracking gate failed, so human review cannot rescue the
decision. No parser, prompt, geometry or gate change was made; no model rerun
or new candidate model task was started; PR #67 is unchanged. PR #74 remains
OPEN/DRAFT and is not merged.
