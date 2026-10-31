# MiniCPM resampler attention FP32 — bounded technical trial

Status: IN PROGRESS / NOT VERIFIED. Owner authorized this narrow engineering
exception after the prior HOLD; [decision](DECISIONS.md#dec-20261031-minicpm-resampler-fp32-technical-exception)
is distinct from scientific baseline approval, result selection or merge.
Same session, branch and Draft PR156; no official160-image experiment or TEST.

The original Kaggle FP16 failure, two native diagnostics and prior source/
notebook/ZIP hashes remain unchanged in the prior evidence index. The verified
failure is score baddbmm overflow followed by softmax NaN with finite Q/K/V and
valid masks. The new implementation is `minicpm4-resampler-attention-fp32-v1`.

The effective adapter verifies the complete original resampler.py hash, reads
the actual native method, requires exactly one occurrence of each of four
declared expressions, and derives an instance-only method. Original source
files/classes/cache/checkpoint locks are not changed. Projections, normalization,
query scaling, eager mode, FP16 weights and output projection remain native.
Only masked/unmasked scores, softmax and value product compute in FP32; the
value product casts back to the native dtype before out_proj. Unsupported
training/dropout/need_weights=False paths fail closed. No SDPA/flash fallback.

The descriptor contains original file hash, adapter file hash, expression map,
dtype boundaries and an implementation digest. Native/derived method hashes
are recorded at load. A distinct effective configuration/hash is bound through
execution, raw custody and runtime. Each engineering invocation has a new run/
series and output tree; no history import/resume/scientific metrics/pooling.
No production authority is granted for this effective configuration. Original
configuration hashes remain available for legacy history, without relabeling
historical results as if they used new arithmetic.

The new notebook `SafeShift_CANDIDATE160_MINICPM4_FP32_ATTENTION_SMOKE.ipynb`
hard-codes the one-image technical route and has no full-run action. It uses
the production supervisor/CLI/child/software/checkpoint/bundle/native loader,
the unchanged first TRAIN image and original C1/parser/HNLO. Caps:1 load,
1 image/1 native call,3600 seconds including setup. GPU0 on T4x2 only.

CPU tests compare original native FP16 overflow with finite effective results,
an independent FP32 reference, mask/error paths, return dtype, unchanged weight
bytes/parameter identities/class/source, distinct config and raw recovery
rejection across implementations. Real production --check-only must additionally
load/install the native meta model in the exact3.11.9/cu124 stack before GPU.

Only an actual final-source Kaggle run with loaded weights, measured CUDA,
finite raw inference, parser/defined HNLO handling, effective counters, cleanup,
ZIP/member checksums/sidecar can establish technical smoke PASS. INVALID and
HNLO unavailable outcomes remain visible; numerical HNLO/quality/full160 are
not implied by one-image finite inference. Any failures remain in their own
immutable output directories and receipts. No alternate prompt/data/precision
outside the authorized boundary is used to obtain a favorable response.

Local and Kaggle evidence will be appended after execution; no PASS claimed yet.
