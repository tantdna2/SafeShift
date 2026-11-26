# MiniCPM-V-4 numerical blocker — decision required

**PENDING; no precision/source/configuration change applied or authorized here.**
PR #156 stays Draft/BLOCKED. This is an engineering finding and a proposed
next scope, not scientific approval, a new result-selection rule or permission
to run the full Owner experiment.

The Owner's current task section9 locks precision, inference configuration and
model/source identity. Section6 also prohibits changing those settings to make
a smoke test pass. The existing Owner authorization permits bounded diagnostic
execution; it does not itself approve the change proposed below.

## Verified on the actual locked Kaggle execution

Same first TRAIN image, original2336x1752 bytes/hash, same model revision,
checkpoint, C1, FP16/eager and pinned runtime as the production notebook:

- All4,059,533,040 loaded FP16 parameters are finite.
- Native resampler projected Q/K/V and scaled Q are finite. Both attention
  masks are finite zeros; fully masked rows=0.
- Immediately after native `torch.baddbmm`, attention scores in FP16 contain
  **60,522 positive infinities**,0 NaNs; the largest remaining finite value
  is65,504 (the FP16 finite maximum).
- The following native softmax produces **569,800 NaNs**; those propagate
  through the value product and `resampler.attn.out_proj`, then to LLM logits.
- No weights, image, prompt, processor, source byte, dtype or operation was
  changed by these observers. No alternate precision/attention run was made.

Source `resampler.py` SHA256:
`6f4f91977fd409b15fe7d2e7ab2ee3f88b544e71a1209026a937eece6c6c582e`.
Native lines543–547 compute scores/softmax; line551 mixes values. The measured
failure is at the FP16 score operation, before softmax, with valid finite
operands and masks. It is not an archive/path/tokenizer/import/OOM failure.
The precise dot products were not recomputed under a different precision;
this evidence does not distinguish every possible CUDA accumulation detail.

Diagnostic version2 ZIP SHA256:
`f4c27ff30bc9eb9132a5d9d736b18bbce45f42464d91ca38a943ffe3335c3b5c`.
The first diagnostic and failed full smoke remain retained separately; see the
[evidence directory](evidence/candidate160_kaggle_20261031).

## Concrete proposed next scope — not applied

Approve a separate, explicit numerical implementation policy for **only the
MiniCPM resampler attention score/softmax/value computation**, retaining FP16
model weights, eager attention, placement, exact model/checkpoint, inputs,
preprocessing, C1, generation, strict parser and HNLO definition. The candidate
to review is FP32 computation inside this attention boundary, then cast its
result back to the existing dtype before output projection. Illustrative
operation-level change, **not executed or installed**:

```python
scores = torch.baddbmm(attn_mask.float(), q_scaled.float(), k.transpose(-2, -1).float())
probabilities = torch.softmax(scores, dim=-1)
attn_output = torch.bmm(probabilities, v.float()).to(q.dtype)
```

Implementation would need a separately declared effective adapter/source hash
and versioned execution configuration. Preserve the original public snapshot,
checkpoint/source locks and historical records; do not silently monkeypatch or
claim the effective implementation is unchanged. Review how a newly approved
configuration starts a separate series and retains incompatible old evidence
without importing old completion/results as if they used the same numerics.
Scientific result selection remains PENDING; no pooling or favorable output
selection follows from this proposal.

Before applying it, obtain an explicit Owner decision on this narrow exception
to section9 and record the approved scope in the decision log. Then implement
CPU native regression/admission/custody tests and rerun the minimum real Kaggle
smoke on the final changed notebook/source. FP32 computation may solve this
overflow, but has not been tested on the real model here and is not promised
to satisfy the whole pipeline or all160 images. ChatGPT and independent
Antigravity review remain required before any merge.
