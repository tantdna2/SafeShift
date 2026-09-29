# D9R12 — D9R11 evidence record and offline adapter contract

Base: `da7a3b8098eb40edba8858791d01d30b564bcc78`. This is a new D9R12 task,
not a continuation of D9R10. The
[result record](../configs/pre_freeze/paligemma_interface_runtime_result.v1.json)
separates `OBSERVED_EVIDENCE` from `RESEARCH_LEAD_INTERPRETATION`.
Research Lead independently inspected the owner-run bundle and verified size
and SHA-256 for 76/76 checksummed artifacts, then supplied the approved evidence.
Codex did not inspect raw bundle bytes or independently rehash those artifacts.
Tests check transcription against supplied facts, not the unavailable raw bytes.

Bundle SHA-256: `058770516daf94a6d12501d33998ae52c7051cdab199f7973b01f59da3d1105f`.
Execution commit: `ceb56d5174a387362e3ef6a5af3b6618123bc8a7`.
Qualification plan SHA-256: `05e1f8f8f56af2abfd8f6fe8fb66a5f820faa3508506072adf5b850fdcdcc2fd`.
The immutable plan/harness, historical source audit and D9R9 runtime result retain
their original scope. Unreported run IDs, raw paths, timings and full generated
sequences are not inferred. The approved grounding strings include EOS; no
additional decoded_text observation is invented.

## Evidence and interpretation

The approved model/revision is `google/paligemma-3b-mix-448` /
`ead2d9a35598cb89119af004f5d023b311d1c4a1`. Supplied runtime: Python 3.11.11,
torch 2.6.0+cu124, transformers 4.57.1, one visible Tesla T4 / CC 7.5 / cuda:0,
FP16 / NONE, owner Internet-OFF attestation true, one model load, eight native
generations, raw-before-parser PASS. D9R11 generated and preserved raw envelopes
before the observer; the parser candidates below are introduced only in D9R12.

Classification answers were `yes`, `yes`, `no`, `yes` for cls_a..cls_d, with EOS
and token IDs preserved in the result record. Research Lead interpretation is
`STABLE_YES_NO_EVIDENCE`. Production class vocabulary and safety semantics remain
unqualified; multi-label and abstention remain untested.

All four grounding outputs have four adjacent loc tokens + `red square` + EOS.
Positive cases support that native grammar. On the negative blue-circle fixture,
`grd_d` still returned `<loc0359><loc0366><loc0662><loc0659> red square<eos>`.
Research Lead identifies semantic hallucination / target-selectivity failure.
Its syntax is parseable. No no-detection grammar is established.

## Offline candidate API

[Parser module](../safeshift/runners/paligemma_interface_candidate.py) exposes
two pure string functions. Each requires its exact approved caller prompt as a
keyword argument. Inputs must come from decoded fields after raw preservation;
the module neither fetches raw artifacts nor claims to authenticate them.
It is not registered in a runner or gate and does not change the production
`PendingPaliGemmaAdapter`. `CandidateParseResult` is separate from production
`AdaptedOutput`; success expresses syntax only and grants no evaluation eligibility.

| Function | Accepted input | Candidate value | Failure |
| --- | --- | --- | --- |
| `parse_presence_answer_candidate` | Exact decoded_text `yes` or `no`, prompt `answer en Is there a red square in the image?` | `PresenceAnswer(answer, present)` under `PRESENCE_QUERY_CANDIDATE`; yes=true, no=false | INVALID / INVALID_CLASSIFICATION_OUTPUT |
| `parse_grounding_candidate` | Exact decoded_with_special_tokens: four ASCII `<locNNNN>` tokens, one space, `red square<eos>`, prompt `detect red square` | Existing `Evidence(bbox, label)` under `SINGLE_RED_SQUARE_GROUNDING_CANDIDATE` | INVALID / PARSER_FAIL_NO_REPAIR |

Common production `Classification` requires Level01..Level04. No presence-to-safety
mapping is defined. Similarly, `red square` is preserved as an evidence label;
it is not mapped to a production hazard. Full-string matching rejects arbitrary
labels, multiple detections, extra text, missing EOS and altered whitespace/case.
Empty/EOS-only responses fail closed with value=null, never an empty prediction.

The existing D9R7 helper validates four integer values in 0..1023 and strict
positive-area geometry, then maps native `[y_min,x_min,y_max,x_max]` to
`[x_min/1024.0,y_min/1024.0,x_max/1024.0,y_max/1024.0]`.
The common schema's clamping helper is not used. There is no /1023, clamping,
1023-to-1 rescaling, rounding, point-to-box, invented box or heuristic repair.
The fixed label match only admits the observed label; it never corrects a label.

`grd_d` returns `Evidence((366/1024,359/1024,659/1024,662/1024), 'red square')`.
There is no fixture/expected-answer argument that could erase the prediction.
Semantic failure stays in the Research Lead interpretation for later gate
evaluation; no scoring or artificial zero IoU is performed here.

## Status and validation

D9R11 evidence collection COMPLETE. REAL_RUNTIME_STATUS=RUNTIME_SMOKE_PASS,
EXACT_RUNTIME_VERIFIED=true. Classification interface, grounding and external gate
all remain PENDING_QUALIFICATION. PaliGemma remains BACKUP_1, four primaries,
protocol freeze BLOCKED, InspecSafe authorized=false, promotion=false.
Separate Research Lead decisions are required for qualification and promotion.

Local static/fake checks use Python 3.11.9, not the supplied D9R11 runtime.
No new dependencies, GPU/model execution, provisioning, Kaggle execution,
synthetic-v1 gate or InspecSafe access is required. Unit tests use supplied
string observations and small invalid/boundary strings; historical harness
regressions inject fake backends. Fake bundle logs are temporary test outputs,
not the approved D9R11 bundle or new runtime evidence.

Validation command:

```text
python -m unittest tests.test_paligemma_interface_candidate tests.test_paligemma_interface_qualification tests.test_paligemma_d9r11_notebook tests.test_paligemma_runtime_result tests.test_paligemma_d9r9_notebook tests.test_paligemma_prep tests.test_local_runners tests.test_internvl3_prep tests.test_internvl3_runtime_result tests.test_d9r6_paligemma_primary_expansion_precommit tests.test_d9r7_paligemma_source_api_audit tests.test_d9_t4_roster_revision tests.test_model_provenance -q
git diff --check
```

Results: **267/267 static/fake tests PASS**, including 12 D9R12 tests with
parameterized malformed/boundary cases; all **31 pre-freeze JSON files PASS**
using `safeshift.protocol.schema.strict_json`; `git diff --check` PASS.
Secret-pattern scan of all eight scoped changed files PASS (provider token
prefixes, private-key headers, AWS access keys, credential assignments and
authorization headers; no gitleaks installation available). The roster source
allowlist adds only the new offline candidate module.

Result-record byte SHA-256:
`555701224f8b745391c65e75c5ff876bc039648fa1f4da02bc96403a3112e736`.
Its Git attribute enforces LF for checksum stability across checkouts.
Real execution and raw-bundle rehashing are not performed in this task.
No dataset/split/label/metric, roster, gate asset or production schema change is made.
