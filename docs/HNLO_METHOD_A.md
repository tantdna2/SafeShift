# MiniCPM HNLO Method A — CPU synthetic engineering

**Trạng thái hiện hành — 02/11/2026:** theo
[quyết định Owner](https://github.com/tantdna2/SafeShift/pull/166#issuecomment-6567502211)
và [đối chiếu ChatGPT](https://github.com/tantdna2/SafeShift/pull/166#issuecomment-6568226996),
Owner đã dừng tìm HNLO cho MiniCPM-V-4. Cuộc điều tra kết thúc với kết quả âm:
**HNLO hợp lệ theo Method A: 0/155**; MiniCPM giữ vai trò **label-only peer candidate
cho Khóa luận**. **AUDIT_HOLD=NO**, đang chờ kiểm toán cuối;
**MERGE_AUTHORIZED=NO** cho đến khi ChatGPT cấp quyền. O2/source selection và L1–L4
vẫn pending; công thức và hợp đồng Method A giữ nguyên. Xem
[trạng thái dự án hiện hành](PROJECT_STATE.md).

## Snapshot trước quyết định dừng điều tra

Phần dưới ghi trạng thái lịch sử; audit hold cũ đã được quyết định Owner trên thay thế.

**Cập nhật Issue #165:** [kiểm chứng archive thật](MINICPM_SAVED_HNLO_165.md)
bổ sung CPU read-only bridge, scope riêng, structural cache và independent
negative proof. Điều tra tiếp nối: **HARD_BLOCKED_EXISTING_ARCHIVE, 0/155**;
[native evidence](MINICPM_HNLO_NATIVE_INVESTIGATION_165.md), numeric goal chưa hoàn
thành, **audit hold**, chờ ChatGPT kiểm GitHub. Phần dưới là hợp đồng/bằng chứng synthetic gốc của PR164; các câu
"chưa đọc dữ liệu thật" mô tả task163, không phủ nhận lượt kiểm Issue165.

Scope: [Owner authorization, issue #163](https://github.com/tantdna2/SafeShift/issues/163#issuecomment-6555995581),
following the [technical proposal](https://github.com/tantdna2/SafeShift/issues/163#issuecomment-6555913422).
BASE: `c2fb0fadef0cfc855c3f164ed1f662e9de623d58`.
This is a separate in-memory proof/evaluation API, not production activation,
a new metric, a raw archive reader, or qualification of a public tokenizer.
MiniCPM remains **peer label-only**. Feasibility for the reported 155 SUCCESS
is **UNVERIFIED**; no real record was opened or changed for this task.

## Source correspondence

The tracked [release receipt](research/evidence/minicpm_fp32_official_adoption_20261031/release.json)
identifies runtime `c3c223bc69edd253d57bbba9344e0633b65b3de4` and source payload
`b1d6d8210b9b5b03c52b59cd339c75a4ec60f0dafb1fc0106623a9e25a2ec2a3`.
Git comparison at BASE found **identical bytes** in runtime and BASE for
`safeshift/pilot/hnlo.py`, `safeshift/candidates/backend.py` and
`safeshift/candidates/train_run.py`. These files remain unchanged.

- `CandidateBackend.generate/capture`: saves sparse raw candidate logits from
  the outer LLM forward before processors, at every actual generated step.
  This is not a saved full-vocabulary vector. A missing decision logit cannot
  be recovered from argmax or a finite flag.
- `persist_ids`: MiniCPM `inputs_embeds` returns continuation-only IDs; there
  is no prompt-length subtraction. Tokenizer serialization precedes replay.
- `train_run.native_custody/validate_raw_configuration`: separate native/step
  artifacts, input and execution/configuration binding belong to original
  custody. Method A does not replace these checks with a new self-issued hash.
- `pilot.hnlo.replay`: retains the original canonical continuation proof and
  rejects a different ID path. The new test demonstrates that this rejection
  remains while a synthetic Method A proof can qualify the actual path.

The [T4 dossier §3.2](research/T4_O2_SELECTION_DOSSIER_20261101.md#32-hai-official-train160)
records the original MiniCPM identity: revision
`6f69a8235885be89608f3a71ffd40695b379e1e7`, implementation
`minicpm4-resampler-attention-fp32-v1`, descriptor
`2fe992725df4340f910934b5846278e34968196a9dff3fc4171fb4279bfaf5da`,
effective configuration
`5b85504ff24ff42d4d629dbf00feb0c484022cfef3a7d57b571eaae99d1c8b00`.
These are inherited tracked identities, not newly audited private execution.
No model weights, real tokenizer serialization or private outputs were read.

## API and trust boundary

Implementation: [hnlo_method_a.py](../safeshift/evaluation/hnlo_method_a.py).
Working examples: [synthetic tests](../tests/test_hnlo_method_a.py), particularly
`fixture()` and `test_all_labels_noncanonical_path_and_independent_numeric`.

```python
from safeshift.evaluation.hnlo_method_a import evaluate, build_proof, verify_proof

receipt = evaluate(packet, native_decoder, independent_decoder, seal)
# receipt['hnlo'] is None on every rejection.
# Optional: proposal = build_proof(packet, native_decoder, seal)
# verify_proof(packet, proposal, independent_decoder, seal)
```

The three entrypoints receive in-memory objects only. `evaluate` returns
`PASS`, `UNAVAILABLE` or `FAIL`; the lower-level builder/verifier raise
`Refusal` on failed proof obligations. `evaluate(..., proof=proposal)` also
requires that a supplied proposal equals the recomputed proof. No entrypoint
loads a model, opens files, downloads, runs processes or writes artifacts.

`Decoder` carries immutable serialized bytes, a tuple of **all** vocabulary
IDs including added tokens, special IDs, and a pure `decode(ids, skip)` callable
with cleanup disabled. Two separate adapters must implement the same pinned
runtime semantics. Tests use deliberately different handwritten algorithms;
they do not execute MiniCPM's public or runtime tokenizer. No encoder is used.

`Seal` contains independently held SHA256 of the packet, serialized tokenizer
bytes and the canonical `{ids: sorted(vocabulary), special_ids: sorted(...)}`.
Packet/vocabulary/receipt hashing reuses `pilot.contract.digest`: sorted-key,
ASCII JSON, compact separators, no NaN, final newline. These are derived object
hashes, **not hashes of original archive member bytes**.

The seal and decoder implementations are **trusted injected inputs**. The
module checks consistency with them; it cannot authenticate their custody,
prove a callable was constructed from the supplied serialization, or infer
that a declared vocabulary is complete. Creating a new seal from a tampered
packet is not verification. Test helpers self-seal handwritten fixtures only.
Two different callable identities do not themselves prove independence.
Later real use needs reviewed adapters and independently verified seals; this
version accepts only `scope="CPU_SYNTHETIC_ONLY"` and always reports
`qualification="REAL_MINICPM_UNVERIFIED"`. A dishonest scope string is not a
data-access guard: the caller is responsible for supplying synthetic input.
There is no file reader or automatic path from this API to T2/T3 or production.

The packet is an explicitly **new synthetic transport**, not a rewrite of the
old raw schema. Required fields:

| Field | Required content |
| --- | --- |
| `schema`, `scope`, `label` | `safeshift-hnlo-method-a-v1`, `CPU_SYNTHETIC_ONLY`, strict parsed Level01–04. |
| `provenance` | model ID, model revision/runtime commit, implementation/sample/run/series/attempt IDs; source, descriptor, input, prompt, tokenizer and configuration hashes. |
| `config` | Exactly the frozen `GENERATION` fields plus EOS IDs, pad=0, repetition penalty=1, min-new-tokens=null; unknown controls are refused. Its digest equals the synthetic provenance configuration hash. |
| `raw` | actual input/generated IDs, unchanged response, EOS IDs, capture boundary/error/finite state, actual processors, tokenizer hash, and ordered sparse raw steps. |
| `native` | separately bound input/generated IDs and `continuation_only_inputs_embeds` semantics. |
| `rendered_prompt_ids` | tokenized rendered prompt for the existing last-min(32, lengths), at-least-8 token boundary check. |

Each step requires consecutive integer `step`, integer `argmax`, literal
`all_finite=True`, exact `origin=outer_forward_output_before_generate_processors`
and a map of canonical decimal token-ID keys to finite raw numbers (no bool or
string coercion). If the generated token has a saved logit, any larger saved
competitor contradicts the argmax and is rejected. Absence of a full vocabulary
vector means the full argmax/finite assertion ultimately depends on original
capture custody; it is not recomputed from sparse logits.

The synthetic `config` hash is **not** a substitute for the official candidate
configuration hash quoted above. A future authorized bridge must verify the
full effective configuration and separately bind its generation projection,
original member hashes and derived packet. That bridge is not implemented or
authorized here. Provenance SHA syntax alone never establishes authenticity.

## Proof obligations

1. Verify bounded JSON, externally supplied seals, model/provenance structure,
   tokenizer identity, full vocabulary identity, frozen generation settings,
   request/native path agreement, fixed input boundary, step count/order,
   raw origin, greedy alignment, finite evidence and empty processors.
2. Recognize exactly one final EOS, or a no-EOS output reaching the frozen
   64-token cap. Reject internal special tokens, repeated EOS, post-EOS padding
   and unexplained early termination. Preserve EOS and its step in the trace;
   remove it only from the structural candidate body.
3. Decode actual IDs with and without special-token skipping and compare with
   the saved response. Reuse the unchanged strict C1 parser. Reject INVALID,
   fences, duplicate keys and extra text. Locate one literal canonical label;
   escaped-label variants are conservatively unsupported. Preserve every byte
   outside that label, including allowed JSON whitespace.
4. For every body position `d` and every non-special vocabulary ID `t`, form
   `G[:d] + (t,) + G[d+1:]`. Never encode the response, canonicalize a token,
   replace a prefix alias or use a hypothetical prefix's logits. Compare full
   standalone decoding, fixed native-context decoding, and decoding with the
   original EOS framing. Token text may cross a label/punctuation boundary if
   all complete-sequence obligations still hold.
5. Require one and only one position with exactly one candidate for each of
   four label surfaces. All four sequences have equal length, common actual
   prefix/suffix, distinct decision tokens; the actual body equals its label's
   branch. Extra token aliases at a qualifying step or additional qualifying
   steps reject the proof. An alias at a different position that cannot form
   a full four-label family is not substituted into the actual path.
6. The verifier independently reconstructs the divergence from all four
   sequences, checks the actual path, and enumerates the **entire sealed
   vocabulary again** with the second decoder. It does not trust the builder's
   saved step or candidate list. An alias missing from the sparse logit capture
   still makes the mapping ambiguous; sparse capture is not the search domain.
7. Only after proof, fetch the four raw logits from exactly `steps[d]`, ordered
   by Level01–04. Missing one key means UNAVAILABLE, even if another step has
   that logit. No averaging, alias sum, imputation or metric-dependent selection.

The arithmetic calls the **unchanged** `pilot.hnlo.hnlo` and Decimal precision60
`oracle`, retaining `rel_tol=abs_tol=1e-10` and finite-result checks:

`HNLO = logsumexp(z01, z02, z03) - z04`.

This is a same-step four-logit quantity conditional on the actual prefix. A
shared token suffix does **not** prove equal suffix probabilities or turn it
into complete-response sequence likelihood. Tests additionally use a direct
Decimal precision90 exponent/sum/log oracle, deterministic random vectors,
shift invariance, extremes and deliberate oracle disagreement.

## Bounds, refusals and receipts

Bounds are engineering resource caps, not new numerical/scientific thresholds:
64 generated tokens, 32,768 input/rendered tokens, 131,072 vocabulary IDs,
2,000,000 position×vocabulary trials **per enumeration**, 2,048 saved keys/step,
32 MB tokenizer serialization, bounded JSON depth16/nodes150,000/text2,000,000.
At most three decoder calls/trial plus bounded preparation; decode execution
time itself is the trusted adapter's responsibility. Work is O(length×vocab),
not a model forward. Large/unsupported proofs fail instead of truncating search.
No performance or completeness claim is made for the real tokenizer.

| Category / example reason | Meaning |
| --- | --- |
| `UNAVAILABLE / MISSING_EVIDENCE:*` | Required evidence was not supplied. |
| `UNAVAILABLE / NO_SINGLE_TOKEN_FAMILY` | No complete one-token family under the proven surfaces/context. |
| `UNAVAILABLE / AMBIGUOUS_TOKEN_BRANCH`, `AMBIGUOUS_DECISION_STEP` | Multiple interpretations; no score-based selection. |
| `UNAVAILABLE / MISSING_DECISION_LOGITS` | At least one required raw coordinate absent at the observed step. |
| `UNAVAILABLE / NO_VALID_GENERATED_LABEL`, `MISSING_TERMINAL_EOS` | Parser/framing prerequisite not established. |
| `UNAVAILABLE / SEARCH_RESOURCE_BOUND`, `DECODER_FAILURE` | Bounded proof could not be completed. |
| `FAIL / EVIDENCE_SEAL_MISMATCH`, `TOKENIZER_HASH_MISMATCH`, `CONFIGURATION_HASH_MISMATCH` | Integrity/configuration inconsistency. |
| `FAIL / STEP_INDEX_MISMATCH`, `NATIVE_PATH_CUSTODY_MISMATCH`, `PROOF_*` | Contradictory path/step/proof. |
| `FAIL / NONFINITE_EVIDENCE`, `CPU_ORACLE_FAIL` | Unacceptable numeric evidence or independent disagreement. |

Every rejection has `hnlo=null`, a reason, schema/scope and real qualification
UNVERIFIED; it has no raw-logit/value fallback. PASS contains decision step,
four token IDs/logits, generated label, numeric/oracle agreement and evidence,
tokenizer, vocabulary, proof and receipt hashes. No receipt authenticates itself.
Caller inputs are not mutated; receipts are fresh objects. Determinism does not
depend on input vocabulary or logit-map ordering.

## Evidence required for a later authorized inspection

Review/audit/merge and a **separate Owner authorization** for exact private
artifacts are still required. A custodian would need to provide, without
images, GT or TEST:

1. Exact original run/series/attempt/sample/input binding, execution release,
   model revision, source/config/descriptor hashes and original source bytes
   or reviewed immutable references. Preserve the original FP32 identity.
2. Independently held archive/member manifest hashes and custody links for
   request, native, processors, every step, raw response, existing result and
   runtime tokenizer; original bytes must be verified before deriving a packet.
   Matching a newly generated packet hash is insufficient.
3. Full original input/generated IDs, rendered prompt/boundary proof, sequence
   return semantics, termination/configuration, consecutive raw-step origins,
   actual processor list, argmax/finite evidence, and all four necessary sparse
   logits at the discovered observed step. Missing values stay unavailable.
4. Exact runtime tokenizer serialization plus added/special tokens, runtime
   tokenizers/Transformers versions and decoder/cleanup settings. Public
   tokenizer JSON is not a substitute for runtime serialization. Independently
   reconstruct and validate decoder semantics and complete vocabulary, including
   contextual aliases. No weights are needed if all saved evidence suffices.
5. A reviewed, authorized bridge binding those original artifacts to derived
   receipts, with original results retained, all failures reported and no
   automatic backfill. Report denominators over planned160 and SUCCESS155;
   keep five INVALID without trying to rescue labels. Coverage may be zero.

No such private inspection, bridge, backfill or coverage calculation occurred.
The reported 155 SUCCESS / 5 INVALID / 0 validated HNLO remain inherited,
unchanged. O2/O3/O4/O5 and L1–L4 are not advanced by this engineering task.

## Reproduction and validation

From repository root, standard library only:

```console
python -B -m unittest discover -s tests -p test_hnlo_method_a.py -v
python -B -m unittest discover -s tests -p test_pilot.py -k HNLOTests -v
python -B -m unittest discover -s tests -p "test_triage*.py" -v
python -B -m unittest discover -s tests -v
```

The new fixtures are handwritten, deterministic; random arithmetic tests use
seed163. They contain no real samples, labels/GT, tokenizer snapshot or logits.
The token IDs 4788/10354 deliberately model the reported surface ambiguity,
not a claim of executing the real tokenizer. Native opt-in tests require
separate public-source/dependency stacks and remain skipped if absent.
See [PROJECT_STATE](PROJECT_STATE.md) and the PR for exact executed results,
environment, checksums and known Windows full-suite limitations.
