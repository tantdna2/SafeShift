# W2.6-D9R14-PALIGEMMA-EXTERNAL-GATE-RESULT-RECORD

**External gate FAIL; grounding qualification FAIL.** Research Lead inspected
`d9r13_result_bundle.zip` and independently recomputed all 87 artifacts in
`checksums.json`: 87/87 SHA-256 and sizes match. This task transcribes those
supplied findings; the recording agent did not independently receive, inspect or
rehash the bundle. Bundle/raw bytes remain outside Git. The two decoded excerpts
below are supplied audit transcriptions, not reconstructed raw envelopes.

The [machine-readable result](../configs/pre_freeze/paligemma_external_gate_result.v1.json)
is the current result overlay on the historical
[D9R13 preparation](w2_paligemma_production_interface_freeze_prep.md).
Frozen plans and earlier evidence retain their historical pending statuses.

| Field | Research Lead-verified value |
|---|---|
| Bundle SHA-256 | `68271facab4e9b272eb4cf5b19e0a5e0c5767e5b008bdfe09ae0ae43c8332ecd` |
| Execution commit | `bcc7b7be62891c887e9509dd39688d686a1b6020` |
| Qualification plan SHA-256 | `c3b5fb2a1df79f3476e3775fccefbe2f767edab453ba2a238742c4c5f89d4387` |
| Frozen manifest SHA-256 | `fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379` |
| Frozen provenance SHA-256 | `0b16be7408784c35bc3dc1a541f008b8086c4fa250957082a236d71ed3fe2e96` |
| Model | `google/paligemma-3b-mix-448` |
| Revision | `ead2d9a35598cb89119af004f5d023b311d1c4a1` |

Recording base: `0b5d5b77106920738569d3b80b982ed231f3b645`; it does not
replace the execution commit. Runtime: one Tesla T4, model_load_count=1,
native_generate_calls=8, classification_calls=0, Internet OFF,
raw-before-parser VERIFIED. The unchanged
[plan](../configs/pre_freeze/paligemma_external_gate.v1.json) specifies
`detect {BARE_TARGET_LABEL}`, FP16/NONE and 32-token greedy generation.
No additional runtime telemetry is inferred.

## Completed execution and strict results

| Case | Canonical parse status | Observation |
|---|---|---|
| A_1 | SUCCESS | Canonical success |
| A_2 | SCHEMA_ERROR | PARSER_FAIL_NO_REPAIR; two detections |
| B_1 | SUCCESS | Canonical success |
| B_2 | SUCCESS | Canonical success |
| C_1 | SUCCESS | Canonical success |
| C_2 | SCHEMA_ERROR | PARSER_FAIL_NO_REPAIR; two detections |
| D_1 | SUCCESS | Canonical success |
| D_2 | SUCCESS | Canonical success |

Six SUCCESS and two SCHEMA_ERROR. The six successful cases have diagnostic IoU
approximately **0.921–0.977**. Individual IoUs, exact successful boxes/native
strings, per-case raw hashes, run ID and execution date were not supplied and
are not invented. IoU remains diagnostic only: no threshold, aggregate score
or artificial zero IoU is assigned to failures.

Exact supplied native outputs:

```text
A_2: <loc0386><loc0639><loc0639><loc0895> red square ; <loc0384><loc0134><loc0634><loc0390> red square<eos>
C_2: <loc0634><loc0641><loc0895><loc0895> yellow triangle ; <loc0124><loc0128><loc0382><loc0384> yellow triangle<eos>
```

Both are real model outputs with two detections, violating the frozen single-box
schema. They are schema/parser failures, not runtime errors. No first-box
selection, second-box removal, grammar/parser change or output repair is allowed.
The existing D4 mapping stays native `[y_min,x_min,y_max,x_max]` in 0..1023 to
canonical `[x_min/1024.0,y_min/1024.0,x_max/1024.0,y_max/1024.0]`:
no /1023, clamp or repair.

Recorded gate: `status=FAIL`, `systematic_tracking=false`, error
`predictions do not track systematic target positions`. This is the existing
gate outcome, not a separate measured tracking-accuracy claim. PaliGemma failed
this frozen qualifying external box-interface gate under the pre-specified
prompt, decoding and parser; this does not establish a general inability to localize.

## Research Lead result resolution and scope

| Decision field | Recorded value |
|---|---|
| PALIGEMMA_EXTERNAL_GATE_STATUS | FAIL |
| GROUNDING_QUALIFICATION | FAIL |
| RERUN_REQUIRED | NO |
| HUMAN_GIANT_BOX_REVIEW_REQUIRED_FOR_DECISION | NO |
| PALIGEMMA_PROMOTION | NO |
| CLASSIFICATION_INTERFACE_STATUS | PENDING_QUALIFICATION |

Automatic gate failure already decides FAIL. Human giant-box review is
`NOT_REQUIRED_AFTER_AUTOMATIC_GATE_FAILURE`; none was performed or fabricated.
No gate/model rerun or token-budget increase is required or performed.

Preserve D9R11 [grd_d evidence](../configs/pre_freeze/paligemma_interface_runtime_result.v1.json):
the target-absent negative case generated a **parseable red-square detection**.
This remains a semantic hallucination/target-selectivity failure; it is neither
successful abstention nor parser failure. It is not added to the frozen gate.

PaliGemma remains **BACKUP_1** under the existing role policy, with **four primary
models**. The roster receives result fields and an evidence link only; its role,
classification candidacy, grounding role and expansion-precommit policy remain
unchanged. Classification interface qualification remains pending. No exploratory
grounding participation, roster expansion or new policy is introduced. Any such
proposal is a separate PR after this result record is merged. Protocol freeze
remains blocked and InspecSafe inference authorization remains false.

Result record only: no protocol, D5 metric, parser, runner, harness, notebook,
prompt, threshold, gate logic or exploratory policy changes; no GPU/model/gate
rerun, InspecSafe inference, output repair, human review or merge.

## Recording-task validation

Focused checks: **104 PASS**, including **10 new result-record tests**:

```text
.venv/Scripts/python.exe -m unittest tests.test_paligemma_external_gate_result tests.test_paligemma_external_gate tests.test_paligemma_runtime_result tests.test_paligemma_interface_candidate tests.test_d9r6_paligemma_primary_expansion_precommit tests.test_d9r7_paligemma_source_api_audit tests.test_qwen3_external_gate_result tests.test_qwen2_5_external_gate_result
```

Strict JSON validation of both changed JSON records with the existing
`safeshift.protocol.schema.strict_json`: **2/2 PASS**. `git diff --check`: PASS.
Scoped secret-pattern, text-only and size checks: **8/8 files PASS**; no archive,
raw bundle bytes, credentials or model weights staged. The existing untracked
`data/manifests/w2_grounding_census.json` remains untouched and excluded.

Full suite was run with `.venv/Scripts/python.exe -m unittest discover -s tests`:
**1219 tests, FAILED (4 failures, 24 errors)**. No full-suite PASS is claimed.
The four failures are existing historical assertions: D9R1's source allowlist
omits `paligemma_external_probe.py`; Moondream's old roster hash differs; Ovis
and Qwen smoke tests still require runner checklist PENDING instead of COMPLETE.
The 24 notebook errors report `STOP: use a fresh notebook kernel before any
backend import` after the suite imports torch. A read-only control replayed these
28 tests with roster reads substituted by `git show` bytes at the exact recording
BASE: the same four failures and 24 errors remain. This is a targeted baseline
control, not a claim that the full suite was run in a separate clean BASE checkout.
These unrelated historical/import-order issues are left outside this result PR.

The D9R13 immutability test now delegates the live roster to the new result test,
which compares the entire roster against BASE plus only the eight authorized
result fields. All production code, frozen contracts, fixtures, plans and earlier
evidence remain unchanged. Existing harness tests use fake outputs only; none of
these checks reruns the real model/gate or independently audits unavailable bundle bytes.
