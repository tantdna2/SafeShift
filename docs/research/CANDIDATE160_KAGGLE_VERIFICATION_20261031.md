# Candidate160: production path regression and real Kaggle verification

Status: BLOCKED — MiniCPM nonfinite native logits; diagnosis in progress. PR #156 remains Draft; independent ChatGPT
review and Antigravity audit are required before merge. No scientific approval
or result-selection decision is changed.

Authority: [Owner directive](https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6539523161)
and the Owner's direct task on 2026-10-31. This extends the previous CPU-only
task to bounded engineering inference on Owner-controlled, locked TRAIN inputs.

The retained Owner failure archive has SHA256
`aee7f4b782c6eb31c780afc8f3d7756c5f91e30a5d9eab506417c2817c818e8c`;
all28 member checksums verify. It records BLOCKED at cpu_native_and_images,
160 NOT_ATTEMPTED,0 native calls and attempt_consumed=false. No member or old
reservation/status is changed.

The new regression reproduced AttributeError(str.lstat) in both unmodified
production `python -B -m safeshift.candidates.train_runtime --check-only`
subprocesses. These ran real authorization, exact installed pins/ABI, locked
manifest160, all160 image hash/decode checks and real native/meta loaders.
There were no native_setup, verify_snapshot or worker mocks. The first local
invocation used the wrong downloaded bundle directory and failed earlier;
its separate logs are retained too. Corrected invocations reproduced the
reported bug before the fix; both passed after the path-boundary fix.

The CLI now types all filesystem arguments as Path, and the worker normalizes
all five path arguments for direct callers. Snapshot stat/verify/stage accept
str/os.PathLike without resolving aliases or weakening lstat/allowlist/hash
checks. Preflight and production use the same native CPU check and production
command constructor. Model source/revision/checkpoint locks, adapters, C1,
precision, parser/HNLO, scientific configuration hashes and original160 order
are preserved.

Technical smoke has a separate schema/run prefix/output tree, one ordinal(0),
one model load, at most one native call and3600 seconds including setup. Full
manifest admission remains mandatory. The same supervisor provisions software,
hashes weights/source, runs CPU/CUDA children and the real GPU worker, retains
raw before parse and exports checked ZIP/sidecar. A final receipt additionally
requires measured CUDA, real native model runtime/attention evidence, durable
raw/result/custody, completed controller, cleanup and verified export. Failures
produce BLOCKED_NOT_VERIFIED. Smoke emits no scientific metrics or production
reservation and cannot resume/pool into a production series.

The exact deliverable notebook defaults to technical_smoke. After all required
review/audit/merge gates, Owner changes only candidate160_action to resume (or
rerun for a new full series), retains authorized Inputs and runs the official
experiment personally. One-image engineering evidence cannot establish full160
completion, rare processor cases, sustained VRAM/time behavior or model quality.

Full exact Linux Git export `c9c2f24680e4eb21290dbf2e3b8fb308a5c8bf2e` passed354
tests:321 PASS/33 SKIP/0 failures/errors. The33 skips require separate native
opt-ins; both actual production CLI checks were also run and passed in their
pinned3.11.9/cu124 stacks. Windows notebook4/4 and smoke5/5 passed. Earlier
slow Windows recovery/WSL-on-NTFS suite invocations were interrupted, their logs
retained without a PASS claim; the replacement exact Linux export completed.

Kaggle InternVL version1 used the exact deliverable cell code/source and private
authorized Inputs on T4x2. Real weights and one inference completed; raw,
tokenizer/native custody, parser/defined HNLO handling, cleanup and archive
checks verify. ZIP SHA256 `b62204d36dc1c22c0bd6ceb40de5e2c0f899721f16788c13220a22a94bc96e5c`.
The model emitted code fences; the unchanged strict parser correctly records
INVALID and HNLO RAW_LOGITS_AVAILABLE_BUT_UNALIGNED. Numeric HNLO and scientific
quality are not established, and no output is rescued or used in research.

Kaggle MiniCPM version1 loaded the locked weights, then one actual native call
produced nonfinite logits at64/64 generation steps. Controller stopped and the
receipt is BLOCKED_NOT_VERIFIED. This is not an OOM: peak allocated9,736,494,592
bytes. ZIP SHA256 `7d9e1947e8316dd2586feaa44bcdbc52fa7dcabe52bc8aaf95050c4de333c939`;
all member checksums verify and raw/log/failure evidence is retained unchanged.
A separate one-image diagnostic observes the same FP16 weights and native
module outputs, stopping at the first nonfinite output without changing values,
precision, eager attention, prompt, processor or checkpoint. It is diagnosis,
not release qualification; production remains blocked pending actual resolution.

Credentials,
private images, weights, raw model outputs and full private logs stay ignored
under data/processed; only sanitized small receipts/hashes may enter Git.
