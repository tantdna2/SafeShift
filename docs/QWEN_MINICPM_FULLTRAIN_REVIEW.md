# Qwen3 / MiniCPM full TRAIN technical review — 12 November 2026

BASE: `341ab626ff2af7ef79ced0d9c3119794eea4a820`, verified against the GitHub
main branch API and `git fetch origin main`. Scope: CPU synthetic engineering,
one branch and one Draft PR. No Kaggle submit, GPU, real inference, TEST, private
image/raw access or production-ledger writes. `operator-asus-win` is outside scope.

The supplied untracked notebook, test and generator were found in the original
workspace and preserved under the ignored task evidence directory before edits.
They are not main-branch deliverables. The notebook has no model load or native
inference loop, yet counts scheduled ordinals as completed. Its FP32 wrapper only
increments counters; its parser accepts prose/bare labels; history ZIP discovery
trusts filenames and ordinals, ignores series/checksums and continues on corruption.
The tests duplicate these implementations rather than exercising the runner.
RAM falls back to 32 GiB on observation failure; reported free VRAM is total VRAM;
the suggested 160-call/7,200-second batch has no measured or authorized basis.
Claims of faculty approval and READY_FOR_OWNER are unsupported.

Implementation will reuse the reviewed fresh171 native pipeline and exact
MiniCPM numerical adapter, retain strict C1 and HNLO N/A, package a reproducible
notebook, and exercise the actual controller/history/archive and failure paths.
The immutable fresh171 release fence stays closed. This task does not manufacture
an execution grant, source activation or final-source Kaggle evidence.

Qwen V4 ORIGINAL remains 3,539 SUCCESS + 1 TECHNICAL_ERROR + 223 NOT_ATTEMPTED.
Recovery224 remains 224 SUCCESS in its own series. Neither is fresh171 completion.
MiniCPM official Candidate160 FP32 remains 155 SUCCESS + 5 INVALID; it cannot be
imported into fresh171. Detailed Inputs, test evidence and operating instructions
will be recorded here with the implementation.
