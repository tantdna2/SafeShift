# InternVL3.5 grammar science qualification — 04/11/2026

**ĐỀ XUẤT ÁP DỤNG (chờ phê duyệt khoa học)** phương án
`internvl35-canonical-json-grammar-v2`, **label-only; HNLO N/A**.
This is a proposed new generation policy, not an activation or an accuracy claim.
Keep frozen C1, its official parser/HNLO and every historical INVALID unchanged.
The proposal addresses a deterministic output-format requirement; it does not
establish better hazard recognition, false-safe performance or generalization.

Authority: direct Owner task and [verified PR175 handoff](https://github.com/tantdna2/SafeShift/pull/175#issuecomment-6620752693).
Base `5ff62212434034f29123e266377f041641c09302`. CPU synthetic work and reuse of
tracked receipts only; no new Kaggle, weights, real TRAIN, private raw, GT or TEST.
One branch/one Draft PR. ChatGPT review, independent audit, scientific decision
and separately authorized merge precede any activation. No new notebook or
production integration is delivered by this science qualification.

## Specification and scientific choice

The four complete strings are exactly `{"safety_level":"Level01"}` through
`{"safety_level":"Level04"}`. A trie of their native token IDs masks all other
next tokens; EOS is allowed only after a complete string. No prompt suffix,
assistant prefill, stripping, relabelling or posthoc rescue. This preserves the
C1 text/parser, but changes generation and therefore the method/series identity.

V2 develops the immutable PR175 helper `issue173-internvl-canonical-json-trie-v1`:
retain its four paths and callback semantics, add admission of one common branch
with four distinct decision tokens/common suffix, fixed-input contextual decode,
special-token/EOS checks, bounded greedy configuration and an independent CPU
trace verifier. A tokenizer that cannot meet these checks is unsupported; never
silently replace a multi-token decision by an arbitrary single token. Token IDs
are derived from the tokenizer, never copied from another model or chosen by GT.

Only single input/single beam, deterministic greedy, maximum64 new tokens,
exactly one prefix constraint, no other processors/warpers are admitted. Ties
use the lowest token ID, matching first-index argmax; this is reproducibility,
not evidence of fairness between semantic labels. Four paths remain reachable,
but are not necessarily equally probable. New native runtime evidence is still
required before execution; earlier GPU evidence belongs to V1, not V2.

## HNLO: proof and counterexample

Current `safeshift/pilot/hnlo.py` requires no processors, actual raw greedy IDs,
independent decoder replay, strict valid JSON and four complete continuations
with exactly one distinct decision position. Its score is

`H(z,h) = log(exp(z01(h)) + exp(z02(h)) + exp(z03(h))) - z04(h)`.

For a fixed prefix h, let A contain all four decision tokens. Prefix masking
sets z outside A to minus infinity and leaves each z inside A unchanged.
With q(j|h,A)=exp(zj)/sum(k in A)exp(zk), the common denominator cancels:
`log((q01+q02+q03)/q04) = H(z,h)`. This is an algebraic equality at **one
identical prefix**, including if other allowed tokens exist. It is not a proof
that a constrained run has the same prefix as an unconstrained run.

If grammar forces an earlier token (for example `{` instead of a code fence),
the model subsequently receives hG rather than hU. There is no identity relating
z(hG) to z(hU). A synthetic witness uses [0,0,0,2] at hU and [2,2,2,0] at hG:
the scores are log(3)-2 and log(3)+2, a difference of4 and opposite signs. These
are deliberately invented logits, not measured model outputs or a claim about
the v5 image. A same-context temperature change also changes the odds; losing
one candidate invalidates the four-label argument. Sequence probabilities under
locally renormalized masks are not, in general, the original sequence likelihood
conditioned on membership in the complete JSON language.

If every constrained token equals the unconstrained raw argmax, deterministic
same-input forward computation can follow the same trajectory (assuming the
same arithmetic, cache, tie rule and termination). PR175's one synthetic grammar
call reports this special case. It cannot establish equality on unseen inputs,
and the frozen replay still correctly rejects a nonempty processor list. We do
not remove that guard, infer counterfactual logits from raw capture, or call a
processed score a raw logit. Raw capture before masking preserves evidence but
does not undo a changed prefix.

**Chosen policy:** every V2 output has numeric `hnlo=null`, status
`HNLO_NA_GRAMMAR_POLICY_V2`. No replacement metric is adopted or computed on
model evidence. A future conditional-prefix score would require a separate
estimand/version, tokenizer/capture proof and explicit comparability approval;
it is outside this proposal. N/A must never be zero, imputed HNLO, or an available
feature in HNLO-only/combined ranking.

## Evidence and boundaries

The existing [diagnostic dossier](../ISSUE173_DIAGNOSTICS.md) is inherited,
not reopened. Historical P2.1 at `31a04e6f7175cca818c63b4de0153246b3f3ecdb`
is a parser amendment, not approval of this model's grammar or score equivalence.
Its exact parser is already regression-tested against the archived function.

| Evidence | What it establishes | What it does not establish |
| --- | --- | --- |
| PR175 grammar receipt, source `25f760b711fdb7423352416fa8bd03e33de23371`, kernel142404153/version1 | One load/one procedural synthetic image;10 finite token steps including EOS; strict SUCCESS; exact prefix processor;10/10 raw argmax matches; native decoder replay PASS | New V2 live qualification, forced-prefix behavior on real images, paired gain, HNLO equivalence |
| Grammar ZIP SHA `2b4593439e76a47035a322a2842c720e5edea98feb1dcd85794ffb8f71378dac`; raw SHA `d5294de33603a583f36e2538fc66dbc52d7f154f044b9e5ae931872d1a4e8315` | Previously sealed custody, independently cross-linked with tracked ledger | New rehash/replay of private ZIP/raw in this task |
| Four native paths of length9; path digest `4c71a3235bec580cb95f78016e3138625528fccbf4b45df5d96cb39f59ff72e1` | Prior runtime tokenizer path identity | Native single-branch or fixed-context proof for V2 from a digest alone |
| Original InternVL v5 | Genuine native fence, strict INVALID, HNLO unavailable, preserved | Fixed or rerun output |
| MiniCPM diagnostic and final original TRAIN smoke receipts | Earlier synthetic INVALID and later SUCCESS; original smoke3/3 execution coverage | Three-model grammar comparison or three valid smoke labels; Mini stays HNLO N/A |
| New CPU synthetic tests | Exact language, rejection boundaries, trace integrity, mask arithmetic, counterexample, deterministic replay | Native weights/GPU behavior or statistical improvement |

The prior raw writer stores native IDs before decode, step records before parse,
pre-processor candidate logits/argmax and the actual processor list. Its sanitized
receipt is not a full-vocabulary pre/post mask trace. V2's stricter verifier must
not be declared PASS retroactively from those summaries. Historical notebooks,
source locks and receipts remain byte-identical.

The exact native processor implementation is
[Transformers4.55.4 PrefixConstrainedLogitsProcessor](https://github.com/huggingface/transformers/blob/v4.55.4/src/transformers/generation/logits_process.py#L1214).
Its additive mask preserves allowed scores and uses negative infinity outside
the permitted IDs. The independent stdlib verifier represents those masked
entries as JSON `null`; raw logits must all be finite and never null. It checks
every vocabulary entry, exact per-step input prefix, constrained greedy choice,
one final EOS, complete decoded output and independent four-path context replay.
Synthetic traces explicitly declare `SYNTHETIC/scripted_before_processors`;
native traces would require `NATIVE/forward_before_processors` plus external
custody. A self-consistent trace is not proof of authenticity or write ordering.
New native capture wiring is not implemented or claimed to have run here.

## Comparison across the three candidates

| Candidate/method | Label comparison | Score comparison |
| --- | --- | --- |
| Qwen3 frozen native generation, historical P2.1 exception | Retain exact method and acceptance metadata | HNLO only where its existing replay qualifies |
| InternVL3.5 proposed grammar V2 | New method/series; strict C1 parser; report forced-prefix/format coverage separately | HNLO N/A for every grammar output |
| MiniCPM-V-4 adopted FP32 resampler, original generation | Preserve label-only method and INVALID | HNLO N/A; investigation remains closed |

There is **no three-model HNLO comparison** under this proposal. Qwen's available
score can remain a model-specific feature under separately approved rules; it
does not license filling peer N/A. Label disagreement and downstream peer-only
comparisons need O2/O3 approval identifying heterogeneous generation/acceptance
policies. They measure complete systems, not isolated checkpoint quality. A
common decoding policy for all three would be another scientific intervention,
not something this PR silently introduces.

For the approved fresh-campaign direction, all selected models must eventually
cover the same3763 original TRAIN IDs/order/hashes, with a complete status ledger.
Intern grammar must use its own new all-cohort series; no grammar-only repair of
the25 old INVALIDs, no union with135 old successes, no smoke/backfill/Recovery224
pooling. Historical baselines remain separate. All planned IDs, technical errors,
truncation, INVALID and NOT_ATTEMPTED stay in denominators. Forced JSON removes
some ways of expressing off-language uncertainty; it can turn an otherwise
INVALID response into a wrong canonical label. Scientific evaluation must retain
that distinction and assess false-safe behavior before claiming usefulness.

## Exact decision requested and stop conditions

Approve or reject this version as an **InternVL label-only generation policy**,
explicitly accepting HNLO N/A and the system-level comparison limits above. This
is the definite proposal, not a request for another open-ended investigation.
If preserving comparable InternVL HNLO is mandatory, **reject V2 and retain C1**.
No numerical quality threshold is invented here.

Before activation: direct ChatGPT review of final HEAD; independent scientific/
generation audit; Owner/Research Lead decision bound to implementation and
descriptor hashes, N/A policy and exact-series comparison; separate merge
permission; then separately scoped final-runtime/tokenizer/capture verification
and O2–O6/execution authority. CPU PASS does not authorize any of these. Under
the present task there are zero new model calls, and the official method stays
C1. No claim of READY FOR OWNER or full-cohort scientific qualification.

## Reproduction and audit

Commands, source hashes, environment, test counts and receipt are added after
CPU verification in this same PR. All new fixture tokens/logits are handwritten
synthetic data. No model raw, images, dataset or credentials are committed.
