# D9R16 — five-model classification qualification PREP

Base: `ecab4cfa6fd844fbada232975ed4494ea719a90b`. Research Lead/user-authorized
PREP only on 2026-10-01. REAL_MODEL_EXECUTION=NO; CLASSIFICATION_RESULTS=NOT_RUN;
INSPECSAFE=NOT_RUN / unauthorized; NO_MODEL_REMOVAL; PROTOCOL_FREEZE=PENDING.
Five primary models remain classification CANDIDATE / PENDING_QUALIFICATION;
production classification is not qualified. No protocol freeze or merge.

## Qualification contract

This checks image + explicit artificial C1 policy -> native output -> deterministic
candidate adapter -> canonical `Classification` -> Level01..04. It is not an
accuracy benchmark or a model ranking. No InspecSafe images, labels, hazards,
distribution or other dataset content informs the fixtures, prompts or adapters.
The suite is independent of the existing grounding gate and its history.

- [Manifest](../configs/pre_freeze/classification_qualification_cases.v1.json):
  eight small RGB PNGs, 256x256, two per level, image SHA-256 and policy text/hash.
- [Plan](../configs/pre_freeze/classification_qualification_plan.v1.json): five
  exact model revisions, runtime plan references, verdict/review/rerun boundaries.
- [Deterministic generator](../scripts/generate_classification_qualification_cases.py):
  integer geometry, no OCR/fonts, no Internet images, no randomness (seed=null).
  Each image has exactly one colored policy marker; variant two adds a gray square.
  PNG encoding uses Python stdlib zlib; byte regeneration is checked locally.
- [Candidate/harness](../safeshift/qualification/classification.py) and
  [runtime registry](../safeshift/qualification/runtime.py): shared code, five thin
  native runner selections, no five copied execution scripts.

| Marker | Canonical value | Cases |
| --- | --- | --- |
| RED TRIANGLE | Level01 | cq_01, cq_02 |
| BLUE DIAMOND | Level02 | cq_03, cq_04 |
| YELLOW CIRCLE | Level03 | cq_05, cq_06 |
| GREEN SQUARE | Level04 | cq_07, cq_08 |

Every prompt carries all four mappings. The prompt builder takes only a model
key, never a case, expected label or marker. IDs are neutral and paths are not
passed as prompt text. Expected levels exist only in the manifest/evaluator.

## Candidate adapters and sources

| Model | Predeclared candidate contract | Production status |
| --- | --- | --- |
| Qwen3 | Existing native-envelope validator + strict single-field JSON classification | Unchanged; research qualification pending |
| Qwen2.5 | Existing native-envelope validator + strict single-field JSON classification | Unchanged; research qualification pending |
| InternVL3 | Exact model/revision/envelope/token/image/decoding validation, then strict JSON | PendingInternVL3Adapter remains NOT_QUALIFIED / INVALID |
| Moondream | Exact lossless native query envelope containing only `answer: str`, then strict JSON | PendingMoondreamAdapter remains NOT_QUALIFIED / INVALID |
| PaliGemma | Exact native model/revision/envelope/token/image/runtime/EOS boundaries, then exact `Level01`..`Level04` | PendingPaliGemmaAdapter remains PENDING_QUALIFICATION / INVALID |

All candidates are PREPARED_NOT_RUNTIME_QUALIFIED. Candidate success cannot
register or promote a production adapter. PaliGemma has no JSON, yes/no,
safe/unsafe or presence-to-level mapping. No regex/substring rescue, trimming,
markdown removal, synonym mapping or heuristic repair exists. JSON whitespace
per the existing strict JSON grammar is valid; PaliGemma level strings have no
whitespace normalization. Standard native tokenizer decoding remains unchanged;
both decoded forms and all native token IDs remain in raw evidence.

Source review on 2026-10-01:

- [Google PaliGemma prompt syntax](https://ai.google.dev/gemma/docs/paligemma/prompt-system-instructions)
  documents `answer {lang} {question}` and natural language support for mix models.
  The candidate uses `answer en` + the full artificial policy + a level question.
- [Exact model family/card](https://huggingface.co/google/paligemma-3b-mix-448)
  describes image+text input, generated text output and single-turn use.
  [Transformers 4.57.1](https://huggingface.co/docs/transformers/v4.57.1/en/model_doc/paligemma)
  and existing pinned runner provide the native processor/model API. The processor
  owns image/BOS/newline tokens; no chat template or new API is invented.
- These sources support the wrapper, **not** successful artificial-policy following
  or four-level generation. That remains the question for future qualification.
  D9R11 yes/no observations and the D9R12 presence parser do not establish this
  new classification contract and are not reused as its semantic parser.
- Moondream's pinned query signature and `{"answer": str}` return are recorded in
  [the source audit](w2_moondream_runner_prep.md#native-interfaces-and-candidate-mapping).
  Existing current runner/precision bridge remain unchanged; the audit's old FP16
  STOP is historical, superseded by the later bridge/runtime records.

Only InternVL3 and PaliGemma source whitelists change: HANDCRAFTED_RUNTIME_SMOKE
or EXTERNAL_CLASSIFICATION_QUALIFICATION. No other runner condition changes.
Existing revision/precision/quantization/preprocessing/software/hardware/offline,
native generation, raw persistence and lifecycle code remains intact.

## Run verdict is separate from research role

PASS requires eight completed calls, eight verified raw outputs before parsing,
eight parse successes and exact expected levels, with all four levels covered.
No retries, repair, prompt/parser/policy edits or output-budget increases.
Seven completed case records without a runtime cause are FAIL. A runtime failure
on the eighth call makes the incomplete attempt INCONCLUSIVE if prior valid
model outputs contain no semantic/format failure; it can never PASS.

Infrastructure, dependency, load, hardware, storage or generation failure is
INCONCLUSIVE, not capability FAIL. Partial native bytes are retained without
parsing. Format/interface or semantic classification failure is FAIL/PENDING_REVIEW.
If valid model failure precedes a later runtime failure, retain FAIL and both
causes. The harness continues the remaining fixed cases after a parse/semantic
failure, but stops on runtime/persistence failure without retry.

Every verdict carries MODEL_ROLE_AFTER_RUN=PENDING_RESEARCH_LEAD_REVIEW.
It never removes a model, alters either classification roster or research role,
activates a backup, assigns NOT_PARTICIPATING, or promotes production. A separate
Research Lead decision alone may assign PARTICIPATING / NOT_PARTICIPATING later.

No automatic rerun. Research Lead must record a separate decision and reason.
Infrastructure reruns keep prompt/parser/policy unchanged. A source-supported
new interface/adapter requires a separate prospective task/PR before another run;
never fit a parser to rescue a particular observed output, silently rerun, or
use InspecSafe for adapter design. The fixed per-model attempt directory blocks
reuse even with another run ID. Do not delete the ledger; a reviewed future
rerun task must preserve and link the earlier attempt.

## Future owner execution — only after PREP merge and separate authorization

Each model uses its own fresh dedicated process/environment, one actual model
load, eight independent classification calls, zero grounding calls:
Qwen3 validated T4x2 FP16 condition; Qwen2.5/InternVL3 single T4; Moondream single
T4 with the current precision bridge; PaliGemma single T4 FP16/exact revision.
All retain their current 32-token output cap and decoding, including Moondream's
query settings. These are qualification settings, not frozen research settings.
Qwen3 software is pinned to the existing validated smoke result; other software
pins are read from the unchanged existing runtime plans.

1. Research Lead reviews/merges PREP separately, then records execution approval
   naming the exact clean checkout commit and per-model environment. This PR does
   not authorize runtime. Independent audit and merge are not performed here.
2. Prepare existing exact model/software caches through their existing reviewed
   provisioning procedures, outside this harness. It only verifies local bytes;
   missing/invalid caches stop. No fallback/download occurs inside qualification.
   Qwen caches use HF_HUB_CACHE set before process start. For Moondream supply a
   repository-relative existing cache under data/processed; InternVL3/PaliGemma
   default to their existing cache roots (optional relative --cache-dir).
3. Disable venue Internet and set offline environment before launching Python:
   HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1, HF_HUB_DISABLE_TELEMETRY=1,
   HF_HUB_ENABLE_HF_TRANSFER=0, HF_HUB_DISABLE_XET=1. Keep each existing device
   visibility condition: Qwen3 two visible T4s, other models one visible T4.
4. Future command template, **not executed in PREP**, from repository root:

   ```text
   python -m scripts.w2_classification_qualification --model MODEL_KEY --expected-commit APPROVED_SHA --research-lead-authorization DECISION_ID --venue-internet-off --run-id UNIQUE_RUN_ID
   ```

   MODEL_KEY is qwen3, qwen2_5, internvl3, moondream or paligemma. Moondream also
   requires `--cache-dir data/processed/EXISTING_CACHE`. Do not pass --cache-dir
   for Qwen; its existing HF cache selection is unchanged.
5. Retain the entire ignored `data/processed/classification_qualification_v1/MODEL_KEY/`
   directory: exclusive attempt.json; per-call response.raw, metadata.json and
   result.json; eight-case qualification_result.json; runtime_evidence.json;
   top-level result.json. Top-level result.json is authoritative if final evidence
   persistence fails after the inner report. Do not report an inner PASS alone.
   Interruption without a final report is incomplete evidence, never PASS; stop
   for Research Lead review, do not restart the process or erase its attempt.

Raw bytes are fsynced and re-read for size/hash, then metadata is verified before
candidate dispatch. Metadata retains model/revision, sample/call/run IDs, exact
prompt/hash, input/policy/plan/manifest hashes, source kind, generation config,
preprocessing, precision, software, device, seed=null, command and Git commit.
Runner snapshot/state evidence stays local. No runtime bundle/raw output is committed.

## PREP validation

Fake/static checks only; existing Windows Python 3.11.9 / Pillow 12.3.0 / zlib 1.3.1
environment. No dependency
installation, weights, model/GPU/Kaggle/Colab/InspecSafe or real grounding gate run.

```text
.venv/Scripts/python.exe -m scripts.generate_classification_qualification_cases --check
.venv/Scripts/python.exe -m unittest tests.test_classification_qualification -q
.venv/Scripts/python.exe -m unittest tests.test_classification_qualification tests.test_qwen_runner tests.test_qwen2_5_runner tests.test_internvl3_prep tests.test_paligemma_prep tests.test_moondream_runner_smoke tests.test_local_runners tests.test_d9r15_five_model_roster_exploratory_grounding tests.test_paligemma_d9r11_notebook tests.test_paligemma_external_gate tests.test_paligemma_external_gate_result -q
.venv/Scripts/python.exe -m unittest discover -s tests -q
git diff --check
```

Validation results: D9R16 **31/31 PASS**; expanded focused **376/376 PASS**.
Generator byte-for-byte reproduction, fixture SHA-256/shape/color checks, CLI
help without runtime, strict JSON, scoped staged secret-pattern scan and staged
diff check PASS. Eight fixtures total 6,628 bytes. No runtime output is evidence
of model capability here; all successful qualification runs in tests use fakes.

BASE full suite: **1232 tests, 4 failures / 24 errors**. D9R16 full suite:
**1263 tests, 4 failures / 24 errors**, the same 28 failing/error test identities.
No new regression and **no full-suite PASS**. Existing failures are the D9R1
runner-source allowlist, historical Moondream protected roster hash, and Ovis/Qwen
smoke checklist assertions expecting PENDING instead of COMPLETE. The 24 errors
are existing notebook fresh-kernel guards after full discovery imports CPU torch.
These unrelated baseline issues were not repaired or hidden.

Historical D9R15 scope is tested against its merged commit. Separate D9R16 tests
compare live protected roots with BASE, allowing only the two exact source-kind
replacements; current roster and production pending states are tested directly.
Historical PaliGemma notebook/gate runner comparisons similarly use the unchanged
pre-D9R16 snapshot; all original pins, plans, notebook cells, gate criteria and
result bytes are preserved. Existing tests requiring smoke-only source text now
assert the exact two-member whitelist and D9R16 tests reject all other sources.
The pre-existing untracked census manifest is untouched and excluded from staging.
