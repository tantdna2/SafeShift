# D9R23 classification production contract

Task `W2.6-D9R23-CLASSIFICATION-PRODUCTION-CONTRACT`, 2026-10-05.
Stacked BASE: `b28e4665904ecd0ab5057a1bc92e263a81c3e8c7` on
`w2.6-d9r22-seminar-rq3-disagreement-redesign` (PR #79). PR B targets that branch,
not main. Authority is the Research Lead's Prompt B and preceding Git correction.

Current implementation: [policy](../configs/pre_freeze/production_classification_policy.d9r23.v1.json),
[prompt](../prompts/p2_classification_c1_v1.txt),
[contract loader](../safeshift/protocol/classification_policy.py),
[adapters](../safeshift/runners/production_classification.py),
[failure accounting](../safeshift/protocol/classification_failure_policy.py).
The D9R23 decision at the end of DECISIONS.md precedes these implementations.
D9R22 research scope and config are byte-unchanged. This overlay updates only
classification implementation readiness, not research questions or participation.

## C1 policy and provenance

Version `p2-classification-c1-v1`; UTF-8/LF SHA-256:
`816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3`.
`prompts/.gitattributes` preserves exact LF checkout bytes across platforms.
Industry table version `upstream-industry-rule-table-section-11.1-v1` copies
the exact five-industry table and four definitions already recorded in
[upstream prompt brief, section 11.1](w2_model_prompt_interface_decision_brief.md).
Tests compare its rows/definitions directly to that source. No new hazard table
or dataset observation is used. Oil & Gas / Chemical, Coal Conveyor Gallery,
Tunnel, Power and Metallurgy retain their industry-specific level assignments.

The renderer returns identical prompt text for all four models and accepts no
GT, domain, sample metadata, other-model output or caller-supplied policy.
Native chat wrapping remains model-specific. Level one/two/three and no
abnormalities observed map to Level01/02/03/04 only as canonical output vocabulary;
this changes no ground truth. P2 requests only a single-field JSON object.
P1's original descriptive/Unrecognizable output format is not imported into
P2; an emitted Unrecognizable or any noncanonical response is INVALID, never
forced to Level04. Existing P1 artifacts remain unchanged.

## Conditions and selective PR #67 reuse

Source-only PR #67 branch `w2.6-d9r19-production-implementation-d5`, exact HEAD
`e85300ab3ec122f819a2685613332578f7e203d8`, remains OPEN/DRAFT and unmodified.
Reviewed its diff, execution-policy JSON/loader, production adapters and tests.
Reused the four-model registry concept and existing strict native validators,
plus conditions independently matched to merged runtime/qualification evidence.
No merge, rebase, cherry-pick, whole-diff copy or PR #67 modification occurred.
Its grounding orchestration, D5 engine/reporting and current overlays are excluded.

| Model | Retained condition | Merged evidence |
|---|---|---|
| Qwen3 | Exact D9R18 revision; FP16/NONE; T4 x2, CUDA 12.8; native processor, auto GPU placement; greedy 32 tokens | qwen_kaggle_smoke.v1.json and qwen_kaggle_smoke_result.v1.json; D9R17 qualification |
| Qwen2.5 | Exact revision; FP16/NONE; single T4, CUDA 12.4, cuda:0; 200704–1003520 pixel cap; greedy 32 tokens | qwen2_5_t4_runtime.v1.json; qwen2_5_classification_qualification_result.v1.json |
| InternVL3 | Exact revision; FP16/NONE; single T4, CUDA 12.4; native 448px dynamic tiles, min 1/max 12 patches, image sequence 256, input cap 4096; unchanged greedy/cache options, 32 tokens | internvl3_t4_runtime.v1.json; internvl3_t4_runtime_result.v1.json; D9R17 results |
| Moondream | Exact model/tokenizer revisions; FP16/NONE; single T4, CUDA 12.4; Pillow and existing post-normalization FP16 bridge; query temperature 0/top_p 1/max_tokens 32, stream=false, native default reasoning=false | moondream_t4_runtime.v1.json; moondream_precision_bridge.v1.json; D9R17 results; native API table in w2_moondream_runner_prep.md |

Full software pins, revisions, preprocessing, hardware, precision, decoding,
prompt hash and adapter/parser versions are explicit in each policy entry.
All choices follow merged runtime conditions, not semantic qualification scores.
Qwen3's old smoke did not record tokenizers separately; no missing version is
invented. The new C1 prompt has not been run with the 32-token output budget;
rehearsal remains necessary, and no budget is increased based on outputs.
Moondream production decoding has only `query`; its historical runner's combined
query/detect context is not a D9R23 runtime transport. No runner is changed here.
New classification-only harness wiring remains a later task. No assumption that
the longer C1 prompt satisfies every model input limit has been runtime-tested.

## Stored-envelope boundary

`persist_response` takes already obtained native bytes and explicit provenance,
validates the recorded execution contract, writes exclusive/fsynced raw bytes
and metadata through FileRawStore, then verifies reread bytes/hash/size/metadata.
The adapter accepts only a StoredEnvelope receipt and verifies storage again
before any native JSON parsing. `persist_and_adapt` composes those steps without
calling a model. Storage/provenance failure raises and prevents parser dispatch;
partial artifacts are retained and cannot be silently overwritten/retried.
Use repository-relative `data/processed/` for artifacts. The local filesystem
is trusted, as with FileRawStore; concurrent hostile filesystem mutation is not
an attested storage service guarantee.

Native envelope validation reuses D9R16 CandidateAdapter and the unchanged Qwen
validators. InternVL3 validates model/revision, run/call IDs and token boundaries;
Qwen validates native identity, exact call decoding/software and token limits.
Moondream's lossless query envelope contains no native model ID, so identity is
bound by the persisted provenance, not falsely claimed to be embedded upstream.
Malformed envelopes/strict JSON, extra/missing keys, invalid labels, prose,
fences, lowercase and substring answers yield INVALID/null canonical output.
No normalization, rescue or free-text mapping. Only qwen3/qwen2_5/internvl3/
moondream are registered; PaliGemma raises CLASSIFICATION_NOT_PARTICIPATING.

## Failure policy

`classification-invalid-d9r23-v1` implements small deterministic accounting
examples for the approved consumer contract; this is not the full D5/RQ3 engine.
For four-class BA/Macro-F1 inputs, INVALID adds FN to its true class and no
canonical FP. Binary anomaly FNR/FPR and Level01 recall/FNR use canonical-only
decisions and are explicitly parse-conditional, with their valid denominators.
All GT anomalies contribute to failure-aware anomaly non-detection: Level04 or
INVALID is failure. All GT Level01 samples contribute to failure-aware Level01
protection failure: non-Level01 or INVALID is failure. These are not canonical
FNR. Reports expose total/valid/invalid counts, parse rates and separate metric
families; empty denominators yield null, never fabricated zero. Runtime or
missing-attempt failures need separate harness accounting and are not silently
converted into canonical predictions by this module.

Example: GT Level01 predictions [INVALID, Level04, Level01] give canonical
parse-conditional FNR 1/2 and failure-aware protection failure 2/3. Invalid
normal outputs are not silently added to a canonical FPR denominator. No
threshold, model selection, training or new inference is introduced.

## Current readiness

C1 policy and exact decoding/preprocessing/precision conditions:
IMPLEMENTED / FREEZE_CANDIDATE. Production classification adapters/parsers:
IMPLEMENTED / TESTED_WITH_FAKE_OR_EXISTING_SYNTHETIC_ONLY. This is offline
implementation evidence, not runtime-qualified on InspecSafe. The full metric
engine, production harness and end-to-end rehearsal remain PENDING.
Implementation freeze=PENDING; protocol freeze=PENDING;
inspecsafe_inference_authorized=false. D9R22 grounding deferral stays in force.
No model/GPU/InspecSafe execution, PR A/B merge, Antigravity or task C.

## Validation

Windows, existing CPython 3.11.9 `.venv`, Pillow 12.3.0 and torch 2.6.0+cpu.
Only static/fake/synthetic envelope tests; no dependency installs. Exact BASE
checkout and ignored logs are under `data/processed/d9r23/`. Tests check prompt
source/hash, all four conditions, raw-before-parse ordering and error paths,
strict output rejection, failure accounting, preserved historical bytes,
append-only logs and a narrow B file allowlist.

Validation on Windows CPython 3.11.9 with the existing `.venv`:

- Focused D9R23 plus relevant existing classification/runner tests: **255/255 PASS**.
- Exact BASE full discovery at A_HEAD `b28e466...`: **1521 tests, 5 failures,
  25 errors, 2 skips**.
- D9R23 HEAD full discovery: **1540 tests, 5 failures, 25 errors, 2 skips**.
  The 30 failure/error identities match exact BASE; the count increase is the
  19 D9R23 tests/additional checks. `NEW_FAILURE_IDENTITIES_VS_BASE=0`.
  Full suite is NOT PASS because the same pre-existing A_BASE failures/errors
  remain. No historical test was edited to hide them.
- `git diff --check` and `git diff --cached --check`: PASS.

The existing 5 BASE failures are historical source/scope/hash/checklist guards;
the 25 errors are the stale G4 identity guard plus notebook fresh-kernel guards
after CPU torch import. They are outside D9R23 and unchanged. No model/GPU,
InspecSafe or prompt runtime execution occurred. Logs are local and ignored;
no dataset, weights or raw model output is staged.
