# Candidate160: production path regression and real Kaggle verification

Status: IN PROGRESS / NOT VERIFIED. PR #156 remains Draft; independent ChatGPT
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

Final local and Kaggle receipts will be added here after execution. Credentials,
private images, weights, raw model outputs and full private logs stay ignored
under data/processed; only sanitized small receipts/hashes may enter Git.
