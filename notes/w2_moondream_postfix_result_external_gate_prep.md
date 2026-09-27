# D9R2M — Moondream post-fix smoke result and external gate PREP

Base main: `9bc5509ecffcb9d7b2faa4a023cd76bd358e2723`.
Task: `W2.6-D9R2M-MOONDREAM-POSTFIX-SMOKE-RESULT-AND-EXTERNAL-GATE-PREP`.
One documentary result + one gate preparation change; **NO REAL RUNTIME
EXECUTION in this task**. Gate **PREPARED_NOT_RUN**, grounding qualification
**PENDING**, protocol freeze **PENDING**.

## Post-fix smoke: Research Lead archive audit

Source: Research Lead's explicit 2026-09-27 task report, after checking the
archive. These are reported, audited observations, not a new run or an
independent archive rehash by this PR. No archive path or archive checksum was
supplied; none is invented. Large raw/runtime artifacts remain outside Git.

| Observation | Reported value |
|---|---|
| Run ID | `moondream-postfix-smoke-20260927T022150Z-1b8def87` |
| Execution commit | `9bc5509ecffcb9d7b2faa4a023cd76bd358e2723` |
| Status / exit | `RUNTIME_INTERFACE_PASS` / `0` |
| Model load / query / detect counts | `1 / 1 / 1` |
| State audits | `5/5 VALID` |
| Image boundaries | `bridge_cpu, transfer, vision_consumption` repeated twice |
| Process-visible GPU | Exactly one Tesla T4, CC 7.5, `15636037632` bytes |
| Host inventory / process mask | T4 x2 / `CUDA_VISIBLE_DEVICES=0` |
| Venue Internet | Disabled |
| Peak CUDA allocated / reserved | `4436097536` / `4513071104` bytes |
| Recorded SHA-256 evidence checks | `13/13` verified by Research Lead |

Query raw native answer:

> A solid red square is centered on a white background.

Detect native bbox after lossless decode, in
`[x_min, y_min, x_max, y_max]` order:

```json
[0.2885258048772812, 0.24949130415916443, 0.7114741951227188, 0.7505086958408356]
```

For **both** native calls, bridge runtime evidence is CPU FP16 -> CUDA FP16 ->
vision consumption FP16. Thus post-fix runtime interface **PASS**, native
query/detect feasibility **PASS**, and the approved bridge was exercised
successfully in this smoke. This does **not** establish grounding qualification,
dataset performance, general numerical equivalence, or protocol freeze.

Historical official smoke `kaggle-t4-moondream-smoke-20260926T070217Z-4c2d43`
remains **FAIL**, `attempt_consumed=true`, `superseded=false`. Neither historical
ledger nor historical result changes. Earlier PREP notes and immutable runtime
plan status fields describe their original milestones; this result is the current
documentary overlay, without editing protected runtime/bridge bytes.

## Frozen gate architecture and adaptation

[Plan](../configs/pre_freeze/moondream_external_gate.v1.json) and
[harness](../scripts/w2_moondream_external_gate.py) reuse `Moondream2Runner`,
`FileRawStore`, `load_cases`, canonical `bbox`, and `evaluate_gate` unchanged.
This is a gate-only adapter; the production pending adapter and model roles are
unchanged. No Qwen runtime/decoder or text-query grounding is used.

- Exactly eight cases: `A_1/A_2/B_1/B_2/C_1/C_2/D_1/D_2` (A1…D2 in the brief).
- Manifest: `configs/pre_freeze/external_gate_cases.v1.json`, SHA-256
  `fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379`.
- Provenance: `configs/pre_freeze/external_gate_cases.v1.provenance.json`, SHA-256
  `0b16be7408784c35bc3dc1a541f008b8086c4fa250957082a236d71ed3fe2e96`.
- Suite `synthetic-v1`, `NO_INSPECSAFE_CONTENT_USED`; all eight existing image
  hashes, paths, dimensions and reciprocal swaps verified before runtime.

The native detect query is **verbatim `case.target_query`**; no noun extraction,
prompt variants, added instruction, target/distractor coordinates or labels enter
the query. Keep existing detect settings `max_objects=50, variant=null`; do not
force one output object to evade ambiguity.

After each native return, the unchanged runner serializes all native fields,
types, order and IEEE float bits losslessly. The harness fsyncs `response.raw`
and provenance `metadata.json`, verifies persisted size/bytes/SHA-256, and only
then deserializes the persisted bytes and adapts them. Completed native returns
exposed by a later runner failure are preserved as partial raw, without adaptation.

Frozen rule: `objects` must be a list of **exactly one** dictionary containing
numeric finite `x_min/y_min/x_max/y_max` (int/float; no bool/string). Zero or
multiple objects produce `SCHEMA_ERROR`, never a chosen box. Extra native fields
are preserved losslessly but not interpreted. No point-to-box, GT/IoU selection,
target-dependent correction, endpoint sorting or label repair.

Canonical D8 `bbox(coords, "xyxy_1")` interprets normalized xyxy, clamps each
coordinate to [0,1], and requires strict increasing geometry. Every finite
four-coordinate candidate records `raw_coordinates`, `normalized_coordinates`
and `clamped` separately. Invalid geometry leaves normalized coordinates null;
malformed/nonfinite values stay available in lossless raw, rather than being
coerced into JSON numbers. No clamp is hidden.

The unchanged evaluator requires systematic tracking, schema validity, predicted
center inside target, predicted box excluding distractor center, no full-image
box and no `GIANT` review. IoU/area remain **diagnostics only**, without new
thresholds. Automatic status is `GATE_FAIL` or `GATE_PENDING_REVIEW`; there is
no automatic PASS or `NO_GIANT`. Schema failures complete all remaining scheduled
cases without retries; runtime/persistence failures stop the suite.

## Runtime and one-attempt procedure (future execution only)

Linux x86_64, Python **3.11.11**, exact dependency pins in the existing
`requirements-moondream-t4.txt` / runtime plan, exactly one process-visible T4
CC 7.5 via launch mask `CUDA_VISIBLE_DEVICES=0`, FP16/NONE/batch 1/PILLOW_ONLY.
Precision bridge, upstream, runner, no-offload and no-fallback policy unchanged.
The unchanged runner verifies software, GPU, both cached snapshots and state;
the harness requires one load, zero query, eight detect calls, 17 VALID state
audits and eight ordered bridge/transfer/consumption triples. No seed/randomness
is introduced; native detect settings remain frozen.

Before any runtime construction, require exact 40-character execution SHA and a
clean tracked **and untracked** checkout, fixed source hashes, frozen suite,
existing `data/processed/moondream_hf/`, and venue Internet OFF attestation.
Use a fresh OS process; no `%run` or reused notebook kernel. Venue networking
must actually be disabled; the flag records the operator's attestation, not an
independent network measurement. The runner's permanent Python network/child
process denial remains defense in depth. No provision/download route is exposed.

The fixed ledger is
`data/processed/external_gate/w2_moondream/ATTEMPT.json`, exclusively created and
fsynced **before constructing the runner/backend**. All run IDs share it. Once
reserved, failure, interruption or hard kill consumes the attempt; no reset,
retry, force, reload or fallback exists. Preflight rejection before reservation
does not dispatch a runtime attempt. Preserve the entire namespace across venue
sessions; deleting/replacing it is prohibited. A local ledger cannot enforce
policy against deliberate deletion or execution in another checkout.

Runtime failure stops immediately, records `completed_gate=false` and all
remaining IDs under `not_attempted_case_ids` (status **NOT_ATTEMPTED**). No gate
evaluation occurs for an incomplete suite. On an uncatchable process death, a
ledger plus empty/absent final result is an incomplete consumed attempt, never a
completed gate. Native raw/metadata already written remain available.

After a separate execution authorization for the reviewed commit, from a clean
checkout with the verified cache already present and venue Internet OFF:

```bash
CUDA_VISIBLE_DEVICES=0 python scripts/w2_moondream_external_gate.py --execute-frozen-gate --venue-network-disabled --expected-commit APPROVED_EXECUTION_SHA --run-id moondream-external-gate-UNIQUE_ID
```

Exit 0 means completed automatic checks awaiting human review, **not gate PASS**;
exit 1 means gate or execution failure. Exceptions before reservation also stop.
No command above was executed during this PREP.

Review artifacts stay under the fixed namespace: ledger; `result.json` with
exact command/commit/runtime evidence, frozen input/GT references and per-case
diagnostics; eight per-case JSON records; raw bytes and metadata; SHA-256/size
inventory; `giant_review.template.json` with all eight reviews `PENDING`.
Research Lead can inspect each frozen image beside raw/normalized bbox coordinates
and diagnostics, record reviewer/rationale for each verdict in a separate review
artifact, and re-evaluate the preserved predictions via canonical `evaluate_gate`.
Human review must not modify raw bytes, normalized boxes, the original result,
case suite, or attempt ledger. No new inference is needed for review.

## Validation

**285/285 tests PASS**, including **26 new fake gate/adaptation tests**, on
Windows / Python 3.11.9. Compilation and diff checks PASS. The historical source
allowlist adds only the newly authorized gate script; protected hashes stay fixed.

```powershell
.venv/Scripts/python.exe -m unittest tests.test_moondream_external_gate tests.test_moondream_postfix_smoke tests.test_moondream_runner_smoke tests.test_moondream_load_diagnostic tests.test_moondream_binding tests.test_moondream_function_identity_diagnostic tests.test_moondream_prep_audit tests.test_d9_t4_roster_revision tests.test_external_gate_cases tests.test_pre_freeze tests.test_qwen3_external_gate -q
.venv/Scripts/python.exe -m py_compile scripts/w2_moondream_external_gate.py tests/test_moondream_external_gate.py
git diff --check
```

New tests use the real runner orchestration with a handcrafted fake native
backend/tensors, block ML imports and benchmark file access, and store outputs
only in temporary repositories. Coverage includes exact frozen suite/order,
exactly-one/zero/multiple/malformed/nonfinite adaptation, visible clamp and no
endpoint repair; raw/metadata/checksum before deserialize/evaluation; canonical
tracking/target/distractor/full-image checks; diagnostic-only IoU/area; PENDING
review; fixed ledger across IDs; exact commit/clean checkout/mask/cache/software/
GPU/snapshot rejection; partial raw, corruption, mid-suite failure and interruption.
Existing D9 roster regression also checks the SHA-256 of the pre-existing local
census manifest when present; this is a read-only historical integrity check,
not dataset access for case/rule selection. That manifest remains untouched and
excluded from this PR.

Full repository suite and CPU tensor bridge tests were not rerun: this change
adds a harness and documentary overlay; runner, precision bridge, canonical
evaluator and dataset tooling are unchanged. Future Linux 3.11.11/T4 execution
remains untested here. No real GPU/model execution, download, gate, InspecSafe
inference, training, selection or merge occurred.
