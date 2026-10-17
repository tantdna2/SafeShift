# InternVL3 CUDA admission and one-attempt recovery PREP — 2026-10-17

BASE: `cb6ae2041e71c74fa1b4943e5986158f5e1b6d83` (main, merged PR #112).
This is a proposed implementation and security scope, not an execution grant or
a demonstrated Kaggle CUDA repair. No GPU, model weights or dataset are used in
Codex. Stop after one Draft PR. ChatGPT reviews GitHub first; Antigravity requires
a subsequent explicit request. No merge in this task.

## Evidence and causal limits

The Owner reports Kaggle T4 x2 / driver 580.178.04, Python 3.11.11,
torch 2.6.0+cu124, Transformers 4.52.4, CUDA_VISIBLE_DEVICES=0, checksum-verified
weights and `pip check` PASS. InternVL3 stopped in `environment()` at
EXACT_CUDA_BUILD_AND_VISIBLE_GPU_COUNT_REQUIRED, load_calls=0, generate_calls=0,
T1=NOT_RUN, HNLO=N/A. This task has not independently examined that raw Kaggle
package; these observations are attributed to the Owner's task report.
The old combined expression short-circuits and does not reveal which of its three
conditions failed. Matching torch package metadata does not independently prove
the runtime value of `torch.version.cuda`.

Owner reports Qwen3 TECHNICAL_VALID, T1=PASS_28_OF_28,
technical HNLO=-24.86805299156391. No Qwen3 rerun is prepared or authorized here;
no new Qwen3 result or independent audit is claimed.

Proven by source and Linux CPU regression: the old seccomp filter returns EPERM
for syscall 42 (`connect`) regardless of family. AF_UNIX creation succeeds but
AF_UNIX connect fails. The old Python guard independently blocks AF_UNIX
connect/connect_ex. The old test proved only AF_UNIX creation. These are concrete
IPC restrictions/test gaps. They do **not** establish the cause of the CUDA failure.

## Pinned PyTorch and NVIDIA call analysis

Primary sources inspected:

- [torch 2.6.0 cuda Python source](https://github.com/pytorch/pytorch/blob/v2.6.0/torch/cuda/__init__.py),
  `is_available()` and `device_count()`.
- [torch 2.6.0 C++ CUDAFunctions](https://github.com/pytorch/pytorch/blob/v2.6.0/c10/cuda/CUDAFunctions.cpp),
  `GetDeviceCount`, `device_count_impl`, `device_count`.
- [NVIDIA CUDA 12.4 release notes](https://docs.nvidia.com/cuda/archive/12.4.0/cuda-toolkit-release-notes/index.html),
  driver compatibility and Tables 2/3.
- [NVIDIA persistence daemon](https://docs.nvidia.com/deploy/driver-persistence/persistence-daemon.html),
  device-file attachment and RPC. Its existence does not prove this Kaggle
  driver initialization requires a local socket.
- [Linux seccomp](https://man7.org/linux/man-pages/man2/seccomp.2.html),
  argument inspection, no_new_privs, TSYNC and inheritance.

Default `torch.cuda.is_available()` calls `_cuda_getDeviceCount()`; the source
documents CUDA Runtime `cudaGetDeviceCount` -> driver `cuInit`. In the C++ path,
initialization exceptions become warnings and count zero. Python socket method
patches do not intercept the native driver call; seccomp intercepts its syscalls.
Setting PYTORCH_NVML_BASED_CUDA_CHECK=1 would change this assessment and is **not**
used. `device_count()` can instead use NVML, mask CUDA_VISIBLE_DEVICES and fall
back to the runtime when NVML fails. It may therefore return 1 while availability
is false. `torch.version.cuda` describes the compiled torch build, not the
driver's maximum advertised CUDA version.

The reported 580 driver exceeds CUDA 12.4 GA's documented Linux minimum
550.54.14. This rules out only the simple below-minimum-version explanation;
it does not prove device nodes, user-space libcuda linkage, driver initialization,
seccomp compatibility or the runtime state. The filter does not block ordinary
open/ioctl/mmap access to NVIDIA device nodes, but would block any native local
connect and sendmsg/sendto. No syscall trace of the reported failure is available.
Do not label AF_UNIX blocking the established CUDA root cause.

## Minimal behavior changes

`one_click.worker.environment` now evaluates all three CUDA checks separately,
captures warnings and per-check exceptions, and durably writes
`cuda-admission.json` before rejecting admission. Error/result logs include
is_available, device_count, torch_version_cuda, expected values, visibility and
all failure reasons. A successful admission still requires the same pins,
one visible T4/CC7.5 and free VRAM. No version or placement substitution.

Two small composition hooks let recovery reuse the existing orchestration and
capture: configurable worker module/single-model contract and an explicit source
lock for capture provenance. Defaults preserve the original behavior. No change
to model generation, C1, tokenizer mapping, scoring, HNLO, raw capture or replay.
Historical regression checks now validate released F1 source bytes and authority
contract instead of incorrectly expecting a released grant to still be null.

## Proposed security boundary — REQUIRES SEPARATE RESEARCH LEAD APPROVAL

The original `one_click/network.py` and production Python guard are unchanged.
Recovery uses its own filter and Python guard **only after** validating the new
authority in both parent and child. Default grant=null. The new mandatory flag
is `security_boundary_change_approved=true`; all original approval flags are
also mandatory. This Draft PR does not grant that approval.

The proposed change permits local AF_UNIX connect/connect_ex. Classic seccomp
cannot dereference sockaddr or discover a descriptor's socket family. Simply
deleting syscall 42 from the deny list would be insufficient. The candidate:

1. Requires a fresh single-threaded Linux x86_64 worker with **no socket fds**,
   including stdio. Parent uses close_fds and log files; inherited sockets or
   an existing extra thread reject installation before torch import.
2. Applies irreversible no_new_privs + seccomp TSYNC, fails closed on install
   failure, checks architecture, denies x32, and permits only AF_UNIX in both
   socket and socketpair. New threads and executable descendants inherit it.
3. Retains denial of sendto/sendmsg/sendmmsg, io_uring and unshare/setns.
   Adds denial of recvmsg/recvmmsg (SCM_RIGHTS descriptor import), pidfd_getfd
   and ptrace, so an IP socket cannot be imported through these paths.
4. Retains Python denial of INET/INET6 connect/connect_ex, DNS/create_connection,
   sendto/sendmsg and descriptor receipt. Performs an actual AF_UNIX connect
   self-test after installation, before torch.

This preserves tested direct IP egress restrictions under a fresh worker and
trusted pinned native libraries. It is not a general malicious-code/container
sandbox. **Local AF_UNIX peers can proxy/relay traffic**; neither BPF nor this
Python guard can prove what a peer does. Lead must explicitly approve this
expanded local IPC scope and residual relay risk, process-level networking with
the Kaggle venue Internet toggle ON, and the additional syscall restrictions.
If this scope is unacceptable, do not release a grant. A separately designed
venue or peer-isolation mechanism would be required; do not disable guards.

No sendmsg/sendto relaxation, pre-guard CUDA initialization, NVML-only admission,
Internet inference, fallback placement, dependency replacement or security PASS
for Kaggle is provided. A driver that needs additional blocked IPC still fails
closed; the next failure is evidence, not permission to broaden the filter.

## Independent one-click release and owner handoff

Notebook: `notebooks/SafeShift_InternVL3_RECOVERY_ONE_CLICK.ipynb`.
Build: `python scripts/build_internvl3_recovery.py` (maintainer only).
New authority/source lock: `configs/diagnostics/internvl3_recovery_*.v1.json`.
Original PR #112 notebook, source lock, authority and runbook remain byte-identical.
Its pinned build/checkpoint provisions are reused without modifying them.

Research Lead/reviewer release sequence, all in this same PR:

1. Review F1, CPU evidence, proposed boundary and exact payload; request the
   independent audit separately. Resolve DEC-PA3-011 research/probe exception
   as in PR #112, plus the new boundary decision; no implied grant inheritance.
2. After approval, add an authority-only F2 child of the single reviewed F1.
   Grant binds F1 and payload, fresh decision/audit URLs (PR #112 references are
   rejected), all original approval fields plus security_boundary_change_approved,
   and a unique `internvl3-recovery-...` attempt ID (at most 36 characters).
   Never reuse `hnlo-synthetic-probe-20261017-01` or the PR #112 grant.
3. Standard merge M parents must be `[BASE,F2]`, with exactly F2's tree.
   Notebook discovers only this fixed recovery branch's single merged PR,
   checks main inclusion and immutable F1/F2/M/source bytes before downloaded
   imports. Each worker repeats source/authority checks. No owner SHA/path edits.

Owner uploads the reviewed recovery notebook unchanged, selects T4 x2 and
Internet ON for preparation, then one Save & Run All **after release**. It compiles
the same Python 3.11.11, installs the pinned InternVL3 environment, provisions
only its immutable checkpoint, finishes online prep, inspects guarded CUDA and
then permits at most one load and one native generate. Inspect does not load or
generate; probe is a fresh process; CPU replay hides all GPUs. Conservative
original resource admission remains to avoid an unverified capacity change.

The same full raw/processed vectors/native IDs, runtime T1, prompt/config/source,
durable invocation/return markers, warnings/errors/resources, sealed journal,
CPU replay, manifest and independently rehashed tar SHA-256 are retained.
CUDA failure now exports the three independent observed values. Failed preflight
or null authority does not become a CUDA PASS. HNLO_RESEARCH_VERIFIED stays false.
Local attempt claims reject a second Run All in the same Output. Global single-use
across fresh Kaggle filesystems still requires Lead/Owner accounting; no offline
filesystem can guarantee it. Hard host kill can interrupt final packaging;
already-written evidence remains in Output, as in PR #112.

## CPU validation and remaining risk

All test model/CUDA objects and outputs are explicitly synthetic CPU doubles;
never Kaggle evidence. Final measured CPU regressions:

| Platform / scope | Run | Outcome |
| --- | ---: | --- |
| Linux / recovery + one-click + capture + T1 | 92 | OK; 1 Windows junction test skipped |
| Linux / related LS1, native PA3, Qwen runner/placement, InternVL3 prep/runtime | 222 | OK; 2 opt-in real-tokenizer tests skipped |
| Windows / recovery + one-click final rerun | 50 | OK; 8 Linux-only tests skipped |
| Windows / related regression, same six modules | 222 | OK; same 2 opt-in real-tokenizer skips |

Linux includes all seven native network tests (3.655 seconds in the standalone
run), all 24 new recovery tests, actual Git topology/source tampering negatives,
actual uploaded-cell Run All simulation with CPU doubles, new/old/null grants,
each worker mode's reauthorization, three CUDA-condition failures, guard order,
one-call counters, raw/processed retention, real CPU replay from synthetic saved
vectors, failed/partial captures, kill/OOM/checksum failures and no retry/reuse.
Windows also ran the earlier 90-case capture/T1/recovery suite successfully
before the final two added recovery cases (11 skip events: 8 Linux-only plus
3 inherited unprivileged symlink subcases); the final Linux 92 covers all cases.

Commands (from the repository root; no opt-in tokenizer variables set):

```text
python -m unittest tests.test_internvl3_recovery tests.test_hnlo_one_click tests.test_hnlo_capture tests.test_hnlo_t1_cpu -q
python -m unittest tests.test_ls1 tests.test_pa3_native tests.test_qwen_runner tests.test_internvl3_prep tests.test_internvl3_runtime_result tests.test_qwen3_runtime_placement -q
python -m unittest tests.test_internvl3_recovery tests.test_hnlo_one_click -q
python scripts/build_internvl3_recovery.py
```

Windows CPU interpreter: Python 3.11.9 / Pillow 11.3.0. Linux WSL CPU interpreter:
Python 3.14.4 / Pillow 12.3.0 (repository validation requirement), with nbformat
5.11.1 for schema validation. These are unit-test hosts, not substitutions for
the pinned Kaggle inference environment. Linux has no torch/model installed by
this task; CUDA_VISIBLE_DEVICES is empty for test processes. The temporary Linux
environment and local validation checkout are ignored under `data/processed/`.
Native network tests ran directly from the worktree; the full suite uses a
byte-identical local checkout because Linux Git cannot resolve the Windows
worktree's `D:/...` metadata. The first direct-worktree Linux full run had exactly
two Git-path errors; the local checkout rerun passed all 92. An initial Windows
test assertion used the wrong JSON field order; corrected before final runs.

Notebook JSON/AST checks bind the exact embedded stdlib bootstrap and every
locked file. Python compilation, nbformat schema validation and full lock/index
byte validation are part of the final handoff checks. Protected PR #112 files,
model/checkpoint/build pins, original guards, C1/capture/token mapping/HNLO
implementations have empty diffs against BASE. Full unrelated repository suite
and real tokenizer/model/GPU tests were not run: only affected/reused CPU scopes
are needed, and model/GPU/data execution is prohibited by this task.

Real Kaggle: **NOT RUN**. CUDA availability/call path under driver 580.178.04,
TSYNC availability, additional driver IPC requirements, build/ABI, memory,
load/generate/capture and valid response remain unverified. Readiness is PREP
for external review; GPU release is BLOCKED until new security/probe approval,
independent audit, authority-only release and verified merge. This does not claim
to have fixed the unknown Kaggle CUDA cause.
