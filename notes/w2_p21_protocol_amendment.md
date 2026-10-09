# P2.1 format amendment and benchmark adaptation disclosure

The Research Lead request on 2026-10-09 authorizes this append-only Draft
implementation. P2.1 changes output-format acceptance for every participating
model to bare strict JSON or one strict JSON object in one complete Markdown
fence. The historical P2 parser is retained unchanged. INVALID remains a missing
canonical prediction and is never mapped to Level04.

The supplied incident is `internvl3-p2-shard0-first`, production commit
`f0b5ea775b3c5bbe5e8618ba1372e59b8b8e150f`: execution COMPLETED, 1254 samples,
SUCCESS=0, INVALID=1254, FAILED=0. The owner observed fenced JSON, which P2
correctly rejected. This evidence is Research Lead supplied; Codex has not
opened the historical raw outputs or manifests, or run InspecSafe/model/GPU.
Exact manifest and status hashes are frozen in
`configs/frozen/p21_protocol_amendment.v1.json`; the owner's actual files must
be verified, never reconstructed from this summary.

This amendment was proposed after observing outputs on InspecSafe. It therefore
has researcher benchmark adaptation risk and cannot be described as a fully
data-independent bug fix. Section 3 of the existing
`notes/w2_model_prompt_interface_decision_brief.md` prohibits output-conditioned
parser debugging; section 4.2 requires versioning and common rules following a
post-freeze technical incident. The Research Lead explicitly requested this
versioned exception and disclosure. Development and tests use only synthetic
responses. No performance gain is claimed before a new run is measured.

P2 results and their raw bytes remain historical evidence. P2.1 results receive
new run IDs, protocol and parser versions, raw-output references, wrapper flags
and parse statuses. The new parser reads only bytes already saved, hashed and
reread. No historical P2 output is reinterpreted or overwritten. C1, labels,
dataset, GT, weights/revision, preprocessing, decoding, FP16/NONE, placement and
the existing research metrics remain frozen.

Formal cross-model comparisons require results from the same P2.1 version on
the full relevant cohort. Completed Qwen2.5 P2 results do not become P2.1 through
renaming. Qwen3 and Moondream receive no permission from this amendment; other
affected model runs require a future explicit authority, including full P2.1
evaluation before comparisons. This PR grants only the exact four InternVL3
runs after audit, Standard Merge, ChatGPT verification and owner preflight.

Shard0 is a complete 1254-sample cross-protocol rerun of the historical P2 shard,
including every previous INVALID sample. Shards1–3 are P2.1 first attempts,
1253 samples each. Stop after shard0 if it has zero canonical yield or a
generation/runtime failure; preserve all artifacts and obtain a new decision
before continuing. No retry, partial resume or arbitrary run-ID mechanism is
introduced.
