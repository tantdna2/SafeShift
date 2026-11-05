# InternVL grammar V2 TRAIN3763 preparation and Antigravity operations

## Current operations — Issue180 campaign route

PR179 merged at `300fc4e305ffa6f1fed9b86ebfedbc996bc9dde2`.
[Campaign runbook](TRAIN3763_CAMPAIGN.md) now governs admission and technical
continuation. One Owner grant, one serial operator, mirrored durable intents,
reviewed source and finite budgets replace per-attempt Owner permission and the
HTTPS requirement on this route. Resume only pending; repair is explicit and
diagnosed. Existing SDK/connection and foreground conversation lifecycle are
reused. No live Kaggle/GPU/TEST is authorized in the implementation PR.

Use the saved handoff directory with `kaggle_handoff.ps1 -Action resume` after
the next user message. Collection never launches another job. An intact FAIL
archive can close an intent, preserving failed outcomes for Codex diagnosis;
BLOCKED/corrupt/missing custody cannot. Initial monitoring <=15 minutes ends at
RUNNING_UNVERIFIED with no AI background process and no provider cancellation.
Include request/intent/source hashes, provider version/state, ZIP/SHA/log paths,
counts/error stage and remaining caps in the Codex handoff. No private raw or
credentials in GitHub. These operational reports are not independent audit.

The remainder is historical PR178/179 preparation guidance. Per-attempt/new
release requirements there do not apply to the campaign route; no old release
or result can be reused as a campaign grant or new prediction.

PR178 is MERGED at `1d161546b93fdf1ae3f80d6baebccdf0d6a6106d`.
The new execution-candidate task is specified in
[INTERNVL3763_EXECUTION.md](INTERNVL3763_EXECUTION.md); that document supersedes
the PREP-only implementation status below for the new candidate route.
This file retains PR178's design, operational lifecycle and historical evidence.
Neither PR178 nor its merge grants a new Kaggle submission or native call.

Owner task 05/11/2026, Asia/Bangkok. Base main
`7633dca168f7bb9fdff84f38a3d374cdbaff5b5a` (PR177 merged).
This is one new task/branch/Draft PR. PR177 and its successful ordinal0
technical series are closed history, never reused for production permission.

## Scope and execution fence

Prepare a new complete-cohort InternVL3.5 grammar V2 series using the original
3763 TRAIN IDs/order/image SHA256. Preserve the approved descriptor and grammar
implementation, C1, strict parser, FP16/eager, checkpoint/revision and full raw
capture. Every HNLO is null / HNLO_NA_GRAMMAR_POLICY_V2. No historical prediction
inheritance, smoke backfill, repair by ordinary resume, GT rescue or TEST.

Authority is the direct Owner preparation/delegation task and
DEC-20261104-OWNER-APPROVE-INTERNVL-GRAMMAR-V2-LABEL-ONLY, which approves a method,
not a full-cohort execution. O2–O6, per-attempt caps, data/Input custody and a
fresh execution release remain separate. Public native/submit paths in this
preparation must fail before private data, GPU, weights or credentials. CPU
synthetic coverage and CLI conversation tests do not establish live readiness.

## Design recorded before implementation

Use a separate preparation module/controller, reusing the approved V2 capture,
tokenizer/trace verifier and original full-cohort planning/history checks.
Every attempt has its own immutable ledger, call markers before invocation,
raw before parse, complete status denominator and ZIP/SHA256 export. Resume
only schedules NOT_ATTEMPTED within the exact selected series/identity. INVALID
is durable completion. Repair requires a specific future release and diagnosis.

Codex prepares exact commit/runtime/notebook/data/checkpoint/rights/bounds.
Antigravity CLI1.5.0 owns authorized submission, initial observation (at most
900 seconds), then later terminal collection. Persist request, conversation ID,
job ID/version, reports and evidence on disk below ignored data/processed.
Never rely on --continue, the latest conversation or an in-memory terminal.
Reserve before handing off a potentially submitting turn. Unknown outcome
blocks resubmission; later turns are read-only reconciliation/collection.

Use --conversation and JSON envelopes, retain failures, and require matching
job/version/source bindings plus a contract verifier before operational PASS.
Check sidecar SHA256, ZIP CRC/members, runtime/source, calls, raw-before-parse and
per-sample statuses. Reports do not replace independent pre-merge audit.
No AI/background process is needed while waiting for the user's completion
message. Never cancel a Kaggle job or restart an ambiguous submission.

The old PR177 notebook needs live nonce/permit coordination. It is not a
detachable TRAIN3763 notebook. A route needing a coordinator after900 seconds
must be BLOCKED before submit; preparation does not remove those old locks.

Acceptance: synthetic RUNNING -> RUNNING_UNVERIFIED -> process exit -> same
conversation/recovery -> terminal check -> collection -> PASS/FAIL/BLOCKED;
also crash/unknown, duplicate submission, drift, missing/invalid evidence and
terminal ERROR. Real Kaggle execution is NOT_AUTHORIZED in this task. Stop at
one Draft PR for ChatGPT review, then independent audit and separate merge.

## Implemented paths and limits

`safeshift/internvl3763.py` defines the distinct configuration/source identity,
full-cohort initial/resume plan, shared controller, separate guarded native
adapter and archive/history verifier. It reuses the unchanged original-master
projection and V2 full-vocabulary capture/grammar/replay. The native controller
has a supervised setup/worker path in `scripts/internvl3763.py`; the guard is
closed before any actual preflight/worker/load/call. No flag or manifest field
opens it. Future activation needs a reviewed source change and exact authority.

`scripts/build_internvl3763.py` builds only a committed-source PREP notebook,
which exports BLOCKED readiness and reads no Input. It is not a released
production notebook or a live diagnostic. Final-source environment/native smoke,
data projection custody, caps and source release are absent; do not submit it.
The dormant preflight reuses pinned setup, isolated CPU processor, actual
checkpoint streaming/advice and the unchanged16GiB floor; its actual execution
is NOT_RUN here. All source/config/hash bindings must be reviewed again before
activation, without inheriting PR177 grants.

Full raw and masked vectors are large. The controller conservatively reserves
sample+ZIP space before each call and stops before the existing8GiB archive
verifier limit, retaining export margin and NOT_ATTEMPTED tails. It does not
promise that all3763 fit a single job or Output. Future attempt/time/call caps
and storage/retention constraints need explicit release/measurements; a bounded
attempt's PASS never means complete-cohort scientific completion. Attempt reports
remain separate; sealed history schedules resume without scientific pooling.

`safeshift/kaggle_handoff.py` persists immutable request/event/report files,
hash links and two OS locks (operator and AI turn). Locks release on process
exit; reservations remain. Windows PowerShell wrapper:
`scripts/kaggle_handoff.ps1`. No service or background AI stays alive between
turns. Retain the worktree and its ignored `data/processed/` directory when
closing Terminal/VS Code. Deleting them would delete local custody.

The current real adapter deliberately refuses start before SDK authentication.
An eventual exact release must implement authorized submission and remote
cross-VM reservation; the local intent lock alone is not global exactly-once.
Existing create-only historical permit records remain unchanged. An old
permit-coordinated route cannot be detached or reused as the new route.
The official-SDK read-only adapter validates private job/current version/code,
queries version-specific status and collects exports only after terminal.
SDK pins remain those of the reviewed operator; no dependency is installed.

## Hướng dẫn ngắn (PowerShell, tại repository root của branch mới)

Rehearsal không truy cập Kaggle, không ảnh/weights/predictions:

```powershell
python -B -m scripts.rehearse_kaggle_handoff prepare --directory data/processed/agy-demo-new
./scripts/kaggle_handoff.ps1 -Action handoff -Directory data/processed/agy-demo-new
```

Sau `RUNNING_UNVERIFIED`, có thể đóng Terminal/VS Code. Chỉ provider giả lập
được chuyển trạng thái bằng lệnh dưới đây để mô phỏng thông báo “đã chạy xong”:

```powershell
python -B -m scripts.rehearse_kaggle_handoff advance --directory data/processed/agy-demo-new --state COMPLETE
./scripts/kaggle_handoff.ps1 -Action resume -Directory data/processed/agy-demo-new
./scripts/kaggle_handoff.ps1 -Action report -Directory data/processed/agy-demo-new
```

`resume` dùng `--conversation` đã lưu; không dùng `--continue`. Nếu mất session
CLI, thêm `-Recover` để mở lượt mới **chỉ đọc/thu chứng từ**, không submit.
Khi người dùng báo xong mà provider vẫn RUNNING, report vẫn
RUNNING_UNVERIFIED và không download. ERROR giữ archive/log và báo FAIL;
evidence thiếu/sai/partial hoặc trạng thái unknown báo BLOCKED. Không xóa
intent/lock/history để chạy lại. Lượt chạy mới sau sửa lỗi cần source/release,
scope/caps và handoff ID riêng; không tự tái kích hoạt bằng report FAIL.

File chính: `request.json`, `event-*.json`, `agy-*.json`,
`agy-*.stderr.log`, `agy-*.settings.json`, `report-*.json`, `collection-*/`.
`report` kiểm lại hash các file được trả về; không tải lại hoặc tái phân tích
toàn bộ raw khi không có bất thường. Báo cáo ops luôn ghi audit chưa thực hiện
và scientific_qualified=false. Chỉ summary đã làm sạch được đưa lên GitHub;
không commit/upload private ZIP/raw/log/credentials hoặc cả thư mục handoff.

## CLI permissions and actual local evidence

Observed agy1.5.0 supports JSON and explicit conversation continuation. Headless
can soft-deny RunCommand while emitting SUCCESS/exit0; the wrapper rejects
`denied_actions` and SUCCESS without a fresh operation report. This account
does not support --mode auto. The wrapper uses --settings with one anchored
exact-command allow-rule for the current step and preserves global deny/ask
precedence. It never changes global settings, uses command(*) or enables
--dangerously-skip-permissions. Unrelated commands are still denied. See the
official [headless permissions](https://antigravity.google/docs/cli/headless/)
and [CLI matching rules](https://antigravity.google/docs/permissions/).

Local v1–v3 rehearsals preserved CLI/sandbox/permission failures. The exact-rule
v4 executed start -> RUNNING_UNVERIFIED, then blocked an additional import probe.
After tightening the prompt to end after the operation, the same conversation
was resumed, confirmed simulated COMPLETE, collected ZIP/log/sidecar and returned
PASS with SHA256/CRC/bindings verified. No Kaggle job or real-data/model action
occurred. Final clean-source rehearsal/validation hashes are in this PR's
sanitized receipt; full CLI envelopes/conversation IDs remain local and ignored.

CPU reproduction (no install or network):

```powershell
python -B -m scripts.qualify_internvl3763 --output data/processed/train3763-check-new
python -B -m scripts.internvl3763 --mode prepare --output data/processed/train3763-readiness-new.json
```

This preparation is ready for source review only. It is not a final-source
Kaggle GPU/model-fit, full-cohort or scientific PASS.

## Final source verification — 05/11/2026

Runtime `8bff3f3d7f2dff326091e62954e5e81e83716685`; PREP notebook
`notebooks/SafeShift_INTERNVL35_GRAMMAR_V2_TRAIN3763_PREP.ipynb` SHA256
`69e2bb152608a3451ef84ae844761f45f297b0e7ed4391fdd0dbb27c36fa2bd6`.
Rebuild/compile/empty-output tests2/2 PASS. Source manifest's84 inherited files
match exact base main; approved grammar/descriptor/C1 and old notebooks unchanged.

Final focused stdlib87:84 PASS/3 optional native skips; pinned CPU-native87/87
PASS, no skips (torch2.6.0+cpu, torchvision0.21.0+cpu, transformers4.55.4,
tokenizers0.21.4). These overlap; do not add them as distinct cases. Additional
old V2 regression160:138 PASS/22 optional/native/Linux skips. No failure/error
in these selected checks. Final clean-source v5 ran through the PowerShell
wrapper and real agy1.5.0: first turn RUNNING_UNVERIFIED, no live AI between
turns, same conversation resumed, simulated COMPLETE checked, ZIP/log/sidecar
collected and SHA/CRC/membership/bindings PASS, no denied_actions. One simulated
submission, zero Kaggle submissions/model calls. Full evidence stays ignored.

Broad repository smoke was interrupted after historical errors; it is not a
full-suite PASS or a final-HEAD full-suite claim. Isolated
`test_candidate160_official_fp32` reproduces identically on this branch and a
pristine detached checkout of exact main:9 tests,1 failure/9 errors, including
OFFICIAL_FP32_CONFIGURATION_DRIFT and an old fixed-digest assertion. Those
sources/locks/tests were not changed. No historical gate was weakened.

[Sanitized machine receipt](research/evidence/internvl3763_agy_20261105/summary.json)
records source/notebook/log/CLI receipt hashes, dependencies, limits and remaining
BLOCKED live/execution/audit gates. This is operational rehearsal plus code
preparation, not independent audit or real Kaggle verification.
