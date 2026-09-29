# D9R10 - PaliGemma interface qualification PREP

Base: `93a8f32ad8c7d10a28cb3e4b62232cd3697bd0e1` (merged D9R9 PR #57).
This task prepares a separate future D9R11 evidence run. No GPU, model,
provisioning, synthetic-v1, InspecSafe, promotion or protocol freeze is executed.

## Predeclared observation matrix

The byte-pinned [plan](../configs/pre_freeze/paligemma_interface_qualification.v1.json)
defines four deterministic Pillow fixtures and exactly eight sequential calls:

| Cases | Prompt (exact caller text) | Fixture purpose |
| --- | --- | --- |
| cls_a / cls_b | `answer en Is there a red square in the image?` | Obvious class / smaller instance |
| cls_c | same classification prompt | Blue circle; red square absent |
| cls_d | same classification prompt | Independent repeat of cls_a |
| grd_a / grd_b / grd_c | `detect red square` | One square / translated / smaller |
| grd_d | same grounding prompt | Blue circle; red square absent |

The processor supplies its audited image/BOS prefix and newline. Raw input token
IDs record that boundary; caller text is preserved exactly in per-case provenance.
The fixtures are generated in memory, then saved under the run's `data/processed/`
directory with a manifest of half-open pixel extents, RGB, PNG and pixel SHA256.
No randomness, dataset or binary fixture is committed. Geometry describes the
input only; it never supplies a model answer or a predicted box. PNG reproducibility
uses the pinned runtime Pillow; pixel identity is recorded separately.

One classification presence prompt and one documentary detection prompt are
predeclared. No adaptive prompt tuning, retry, altered token budget, model reload
or alternative wording is allowed after outputs are observed. The repeated call
is planned in advance and runs even when the first answer is unexpected.
This small matrix observes native behavior; it does not establish production
label vocabulary, case/whitespace policy, multi-label behavior or abstention.
Those remain unresolved, with multi-label and abstention explicitly untested.

## Evidence and interpretation

[D9R9](w2_paligemma_single_t4_runtime_qualification.md) qualifies runtime only;
`blue<eos>` and `green<eos>` are OBSERVED_ONLY, not grammar evidence.
[D9R7](w2_paligemma_source_api_audit.md) supplies documentary native y/x/y/x
integers 0..1023 and selected D4 `/1024.0`. The existing mapping helper is retained
and tested: no clamp, 1023-to-1 rescale, heuristic repair or point-to-box conversion.
Malformed candidate input is `PARSER_FAIL_NO_REPAIR`.

No output grammar parser is implemented or run in D9R11. The post-persistence
observer deserializes the runner envelope and inventories loc IDs in continuation
order and loc-looking text with character offsets; it produces no boxes or labels.
Its candidate field is `NOT_YET_QUALIFIED`, executed=false, canonical_output=null.
This is deliberately separate from the pending production adapters.
Text, EOS, empty text, malformed tokens and hallucinated boxes are preserved
verbatim, including on the negative case. There is no canonical no-detection
assumption or conversion to an empty list. A genuinely zero-token generation
violates the unchanged runner transport contract: available full native IDs are
preserved as partial evidence and the run stops; no empty answer is invented.

The [harness](../scripts/w2_paligemma_interface_qualification.py) calls the audited
runner's initialize/load once and prepare/generate for each independent input.
The runner source-kind string remains `HANDCRAFTED_RUNTIME_SMOKE` to preserve its
allowlist; the new plan and per-case fixture provenance identify the qualification
scope. It uses unchanged greedy max_new_tokens=32/no-cache generation. Token count,
EOS presence and reaching the cap are observations, not automatic validity labels.

Ordering is native generation -> exclusive raw/envelope write -> flush/fsync ->
re-read -> size/SHA check -> observer. Native decoding is part of runner envelope
serialization, never text normalization or a grammar parser. Raw bytes and full
and continuation IDs are retained, including partial envelopes on native failure.
No arbitrary exception text or environment dump enters harness evidence.
Per-case timing includes generation, runner audits, persistence and synchronization;
it is explicitly not pure GPU generation latency. Failed spans are not fabricated.

Only `EVIDENCE_COLLECTION_COMPLETE` or
`STOP_AND_RESEARCH_LEAD_REVIEW_REQUIRED` is emitted as collection outcome.
The Research Lead must review raw evidence before deciding any interface grammar.
Malformed/unexpected model content alone is an observation, not a retry trigger.
Transport, persistence, audit or environment failure stops subsequent cases and
exports available evidence. Kernel termination/disk failure can prevent complete
export; preserve the workspace for review rather than retrying.

REAL_RUNTIME_STATUS=RUNTIME_SMOKE_PASS and EXACT_RUNTIME_VERIFIED=true remain.
Classification, grounding and external gate stay PENDING_QUALIFICATION;
PaliGemma BACKUP_1; four primaries; protocol freeze BLOCKED; InspecSafe unauthorized.
The existing runtime plan/result, roster, D9R6/D9R7 artifacts and production runner
are unchanged. Fixture qualification is not the synthetic-v1 gate and has no score.

## Future Kaggle run

Use the new D9R11 notebook only after separate Research Lead review/authorization.
The [notebook](../notebooks/w2_paligemma_d9r11_interface_qualification_kaggle.ipynb)
pins harness commit `ceb56d5174a387362e3ef6a5af3b6618123bc8a7`, descended from the
exact base; notebook delivery is a later commit. Tests compare executed code/plan
bytes against that snapshot. No dynamic branch/main execution is allowed.
The notebook itself remains unexecuted in D9R10.

Reuse D9R9 setup: anonymous public clone, dedicated pip --target uv==0.8.22 bootstrap,
CPython 3.11.11 and exact requirements, physical T4 inventory, process-visible
single T4 with PCI_BUS_ID/CUDA_VISIBLE_DEVICES=0, FP16/NONE/cuda:0/batch 1.
Only the explicit future provision child receives HF_TOKEN from Kaggle Secrets.
Exact 14-file snapshot verification occurs online and again after a manual
Internet-OFF attestation; the runtime child has offline variables and socket denial.
No credentials enter runtime, command lines or the result bundle.

The fixed attempt ID and exclusive directories prohibit runtime reruns. Future
output is `/kaggle/working/d9r11_result_bundle.zip`: positive-allowlisted setup logs,
snapshot manifests, exact plan bytes, fixture manifest/images, per-case prompts,
raw envelopes/hashes, IDs/decodes/loc observations, timings, execution commit,
hardware/software/offline evidence, summary and checksums. File and total size
limits exclude weights/cache. Suspected credentials cause export refusal, never
rewriting native evidence.

## Validation

CPU/fake tests exercise real runner lifecycle with fake backend, deterministic
fixtures, all eight calls, no retry, raw ordering, corruption/fsync/decode failure,
offline/mask/plan guards, and unchanged documentary mapping. Notebook tests check
bootstrap pins, secret isolation, barrier, export allowlist and no promotion.
Validation commands and final results are recorded in this task's PR.
No real GPU/model/provision/runtime qualification is part of these checks.

Local validation: **255/255 focused and related regression tests PASS** with
Python 3.11.9 (fake backend only; not the future pinned runtime environment).
All **30** pre-freeze JSON files pass `strict_json`; notebook JSON and all three
code cells parse/compile, with execution_count=null and no outputs.
Secret scan of the nine scoped changed files and `git diff --check`: PASS.
The roster source allowlist test adds only the newly authorized D9R10 harness.

```text
python -m unittest tests.test_paligemma_interface_qualification tests.test_paligemma_d9r11_notebook tests.test_paligemma_runtime_result tests.test_paligemma_d9r9_notebook tests.test_paligemma_prep tests.test_local_runners tests.test_internvl3_prep tests.test_internvl3_runtime_result tests.test_d9r6_paligemma_primary_expansion_precommit tests.test_d9r7_paligemma_source_api_audit tests.test_d9_t4_roster_revision tests.test_model_provenance -q
git diff --check
```
