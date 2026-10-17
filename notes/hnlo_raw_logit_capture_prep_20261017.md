# Three-model raw-logit capture PREP (2026-10-17)

Base: `main@90aac7ba48cf8480a10cc93113e5947781a55af3`, including PR #110.
Scope: independent diagnostic library and CPU fake-backend tests only. No model
construction, weights, GPU, inference, InspecSafe, TEST, annotation or GT access.
**HNLO VERIFIED: NO. HNLO remains N/A in all diagnostic review results.**
DEC-PA3-011 remains PROPOSED; this PR does not approve it or release any authority.

## Changed files and reuse

| File | Purpose |
|---|---|
| `safeshift/diagnostics/__init__.py` | Independent namespace; no production wiring. |
| `safeshift/diagnostics/hnlo_capture.py` | Provenance, durable native tensor capture, CPU reopening/review. |
| `safeshift/diagnostics/hnlo_hf.py` | Qwen3 composition and InternVL3 NativeScorer composition. |
| `safeshift/diagnostics/hnlo_moondream.py` | Verified binding, read-only hook, post-mask observation and native-answer checks. |
| `tests/test_hnlo_capture.py` | Synthetic CPU tensors/modules, success and injected failures. |
| This note; `TASKS.md` | Evidence, limits and current task status. |

Reused without editing: PA3 `Journal` (exclusive writes, flush/fsync, SHA-256,
reread, seal/inventory and torn-write detection); LS1 `probe`, `capture_output`,
`summarize_vector`, `locate_decision`, `score_decision`; native Starmie adapter;
Qwen3 loader/placement/preparation/cache cleanup; InternVL3 NativeScorer pinned
loader, image preparation and state validator; Moondream exact-source and
bytecode verifier, native runner's vision bridge, state audit and native serializer.
No HNLO formula or Qwen2.5 baseline code changed. No calibration, forced prefix,
Level01 guard, prompt repair, textual confidence or multi-token surrogate score.

## Persistence and CPU replay

Each call uses a fresh `hnlo-*` run ID below ignored
`data/processed/hnlo_capture/`. Required metadata includes sample ID, prompt and
its checksum, input checksum, immutable model/tokenizer revisions, tokenizer file
checksums, source commit/file checksums, software, command, configuration and seed.
Source/tokenizer file paths are relative. The future caller supplies and verifies
these receipts; a metadata assertion alone is neither authenticity nor authority.

HF capture saves full native sequence/input IDs, checkpoint config, effective
kwargs, raw/processed step counts, then each full-vocabulary tensor's original
scalar values, shape, dtype and device in separate checksummed files. Only after
these writes does reused `capture_output` decode/reduce. Missing scores, malformed
prefix, decode, reduction or later state errors retain all earlier files. Blocking
HF generation that raises without returning an output cannot supply invented
partial tensors/IDs. Torn writes are retained and rejected, never repaired.

Full vectors deliberately remain local: this is a one-case diagnostic, not a
proposed benchmark artifact policy. JSON retains represented FP16/FP32 scalar
values, including nonfinite classification; it is not a tensor-memory/NaN-payload
bit dump. No raw/processed equality or VRAM-overhead claim follows from this PREP.

`Capture.open(Path('.'), run_id)` reopens the journal without generating anything.
`review_trace(capture, verified_runtime_tokenizer)` is read-only by default and
works on sealed runs. It recomputes every summary from original persisted vectors
on CPU, then uses existing strict parsing, single-decision-token proof, EOS and
generated/processed selection checks. It exposes exactly four raw logits from
one decision and separately reports the four processed scores and equality.
INVALID, wrong alignment, nonfinite raw or a failed capture cannot pass review;
HNLO is N/A even if technical alignment passes. Optional `persist=True` writes a
review before sealing. `journal.read(name)` also reads individually completed
partial evidence; `inventory/verify` detects incomplete or tampered runs.

## Model-specific source and evidence levels

| Model | Proved by this PR | Still unproved |
|---|---|---|
| Qwen3 | Injected backend reuses exact loader, placement and input preparation; only diagnostic output flags differ; raw/scores stay distinct; decode failures preserve tensors. | Actual pinned-model `output.logits`, processor effects, real response alignment, memory and state behavior. |
| InternVL3 | Calls NativeScorer `prepare(image, ())` and native `model.generate` directly; durable boundary precedes reused `capture_output`; decode/post-state failures retain evidence. Never calls NativeScorer.generate. | Real checkpoint raw-logit capture, actual tiles/response and GPU audit. |
| Moondream2 | Fake module proves immediate clone survives in-place mask, separate post-mask observation, hook returns None/removes in finally, ordered calls, EOS/native-answer reconciliation, failure/state evidence. | Real hook identity/timing, native state/answer preservation and equivalence; hook strategy requires separate approval. |

PR #110 already supplies T1 PASS for all three pinned tokenizers; historical T1
blockers in the phase-2 note are superseded by that evidence. This task does not
rerun their real tokenizers. Before a real probe, verify their exact resource
hashes again. Qwen3 requires a separately verified reference tokenizer and compares
its 28-case probe with the loaded processor tokenizer. InternVL compares scorer
and processor tokenizers. Moondream reprobes the actual pinned native tokenizer.
These comparisons are prerequisites, not permission to execute.

Qwen3 uses Transformers **4.57.1**. Inspected official
[generation source](https://github.com/huggingface/transformers/blob/v4.57.1/src/transformers/generation/utils.py)
and [processor source](https://github.com/huggingface/transformers/blob/v4.57.1/src/transformers/generation/logits_process.py):
greedy generation stores separate logits/scores streams. It passes logits through
the processor list before storing them; runtime processor/config effects must
still be audited before calling returned logits demonstrably pre-processor raw.
There is no assumption that the two streams are equal or that equality proves
raw provenance. Diagnostic source checks pin the installed files below; a CPU
file-only check passed against the existing PR #110 environment, without importing
Transformers/PyTorch or loading any model:

| Relative installed source | Bytes | SHA-256 |
|---|---:|---|
| `transformers/generation/utils.py` | 210102 | `a20024b1e82ed5361a524d238d2197be5407abc91297dd9888c57e8284d63fef` |
| `transformers/generation/logits_process.py` | 152357 | `6481506629ff6f021157e893fc64c4e7b5b06a72072771809d679387cb54a4b1` |

InternVL3 retains its audited Transformers **4.52.4** NativeScorer loader and
existing source checks. No Qwen3 runtime pin is applied to InternVL3.

Moondream source was read as text, never imported/executed. Existing ignored
`moondream.py` and `text.py` audit-cache bytes matched committed metadata hashes
`52e8d0357eb12fdc1be36de13b3a53b225b970cc47fe7798783f177cf2262e59` and
`9ec56dd5f1a78c9116c8f60e83db90c887034e0183ec3acb6245a91b493ce352`.
Exact [answer loop](https://huggingface.co/vikhyatk/moondream2/blob/9a7d4024050840e001defacec2b00727e89149e6/moondream.py)
and [head source](https://huggingface.co/vikhyatk/moondream2/blob/9a7d4024050840e001defacec2b00727e89149e6/text.py)
show an unmasked prefill and later in-place `answer_id` masking. Before hook
installation, code verifies source bytes, bound methods, global head function,
HF query property, native Linear head, EOS=0 and answer_id=3. Compiled/replaced
methods fail closed. Events record the predicted token position: prefill prompt
end; decode consumed `pos_ids + 1`.

Post-mask argmax IDs are explicitly **inferred**, until all steps match the native
answer and its exact encoding, with exactly one terminal EOS. The loop can compute
an extra unconsumed lookahead at the token limit: this is retained and rejected,
never trimmed into a fake success. Stable layout/device/dtype audits are compared
before/after, including on native exceptions. KV values naturally change; these
audits do not establish bytewise weight/cache identity or an unhooked-answer
comparison. No control generation is scheduled by default.

## CPU validation

Environment: CPython 3.11.9 on Windows, Pillow 11.3.0; no PyTorch installed in the
test interpreter. New tests explicitly deny sockets and real ML imports.

```text
python -m unittest tests.test_hnlo_capture -v
python -m unittest tests.test_hnlo_t1_cpu -v
python -m unittest tests.test_ls1 tests.test_pa3_native tests.test_qwen_runner tests.test_qwen3_runtime_placement tests.test_moondream_binding -v
git diff --check
```

New fake suite: 28 tests PASS. Related regression suite: 196 tests, 194 PASS /
2 SKIP (opt-in real InternVL3 and Qwen2.5 tokenizer snapshots absent).
T1 helper suite: 7 tests complete successfully with 3 skipped symlink subcases
because Windows lacks link-creation privilege; these are not tokenizer failures.
The initial new-suite failure was a missing EOS declaration in the Qwen CPU fake;
the fixture was corrected. No final assertion FAIL/ERROR remains. No real-model,
GPU, fresh tokenizer execution or end-to-end runtime qualification was run.

## Minimum future synthetic probes — approval required, NOT RUN

One exact synthetic RGB input, one load, one native call, new run ID per model;
unchanged C1 prompt, greedy/batch 1/max 32. No retry or default control generation.

| Model | Smallest proposed probe |
|---|---|
| Qwen3 | One existing committed synthetic RGB fixture; audited 2×T4 plus embedding CPU placement; capture three diagnostic flags, per-step tensors, actual processor effects, IDs/EOS and CPU alignment. |
| InternVL3 | One deterministic 448×448 solid-gray RGB input, hashed before use; 1×T4, existing dynamic-tiling path; record actual tile/input shapes and perform the same durable/alignment checks. |
| Moondream2 | One deterministic synthetic RGB input; 1×T4 with unchanged audited vision bridge; one nonstreaming/nonreasoning native query and temporary verified head hook; check all phases/positions, masking, native answer, EOS, hook removal and stable-state audit. |

Record actual peak VRAM/host memory/time for each proposed probe; capture overhead
has not been measured and no guaranteed increase is asserted. INVALID/misaligned
outputs remain HNLO=N/A, without changing the prompt to obtain PASS.

Before merge: Research Lead reviews capture/source/persistence contracts and the
pending Moondream hook strategy; independent audit/reconciliation remains a
separate requested step. Before GPU: approve the research/protocol decision,
specific model/revision/runtime/source/input/run ID/one-attempt scope, artifact
retention, raw-provenance criteria and numerical tolerance. Provisioning and any
dataset/TEST/metric/inference authority require their own explicit approvals.

Suggested tolerance for Lead consideration only: preserve saved scalar values
exactly, recompute stable reductions in CPU float64, and compare a future scalar
HNLO recomputation from the **same saved four logits** using
`abs(delta) <= 1e-6 + 1e-6*abs(reference)`; separately report every deviation and
maximum error. Do not demand GPU and CPU intermediate probabilities be bitwise
equal. This rule is not adopted/implemented by this PR; it must be approved before
a real comparison. No new HNLO or substitute metric is implemented here.

Stop at one Draft PR. No merge, Antigravity invocation or model execution.
