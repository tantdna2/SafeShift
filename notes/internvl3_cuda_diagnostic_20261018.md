# InternVL3 CUDA diagnostic PREP — 2026-10-18

BASE: `67d401091adfde8a17d1fa9cd89af5574dfa529a` (merged PR #113).
Branch: `codex/internvl3-driver-diagnostic-20261018`.
CUDA root cause remains UNKNOWN. This change fixes a CPU-reproduced monitor
observation defect and prepares new diagnostics; it does not claim a CUDA fix.

## Verified historical evidence

The three Owner artifacts in Downloads were read and the archive was extracted
under repository-relative
`data/processed/internvl3_cuda_analysis/internvl3-recovery-session-20261018T031136Z-d26e9893/`.
The archive SHA-256 is
`055e8c14f9aebee1af98fd52f9dfd1f253a21a79d0be8c4d0868b4aed8a812b8`;
manifest SHA-256 is
`fe3edcfa4c589499d81f8cce3d4b44e286ef9e399f369baa69e274b28228f0dd`.
All 25 evidence sizes/hashes match, with no missing/extra members. The standalone
result matches the archived result byte-for-byte. Verification/extraction used
Python 3.11.9 stdlib tarfile/hashlib, rejecting non-files, traversal and aliases.
The raw evidence is ignored and is not committed or modified.

Host: two Tesla T4, driver 580.178.04, 14,912 MiB free each. Software install and
pip check succeed with torch 2.6.0+cu124. Guard self-tests pass. Admission records
visibility `0`, CUDA build `12.4`, availability false, count zero, no Python
exceptions or warnings. Model load/generate are both zero. Inspect stdout/stderr
is empty. Four monitoring events include two procfs checkpoints reporting EBADF,
zero observed sockets and UNOBSERVABLE; no monitor stop was recorded.

The source-bound PR #113 grant was present and matched the archive. Its old PREP
text saying null is historical, not evidence that the attempt was unauthorized.
The existing attempt must not be reused even though model load did not start.

## CPU-confirmed defect and limited repair

`/proc/self/fd` enumeration can include its own directory descriptor, closed by
the time fstat examines it; target descriptors can also close during this race.
The monitor treated EBADF from the first fstat as an observation failure. A
synthetic CPU regression fails before this repair and passes afterwards.

Only EBADF at that first stat is counted as `closed_before_inspection` and skipped.
Permission errors and errors after that stat remain recorded as before. Coverage
remains PARTIAL/UNOBSERVABLE, including races, transient sockets and native
denials; no NO_LEAK or SECURITY_PASS claim. Seccomp and Python guard policy are
unchanged. This explains an observation defect, not the CUDA failure.

## Remaining hypotheses and diagnostic purposes

`child_environment()` deliberately removes LD_LIBRARY_PATH/LD_PRELOAD and host
NVIDIA configuration. CPU simulation confirms that behavior. It is not enough
to conclude this breaks Kaggle: driver libraries might already be in the linker
cache. No environment policy is changed. Container-time NVIDIA variables must
not be confused with a child environment's dynamic linker search.

| Observation | Purpose and limit |
| --- | --- |
| Static host metadata | Parent environment allowlist, linker-cache candidates, symlink/ELF dependencies and device stat/access; no library load or CUDA call |
| Guarded worker metadata | Same fields under the pinned interpreter and unchanged sanitized environment; compare host and child, not their CUDA results |
| load_cuda | CDLL(libcuda.so.1), loader error category and actual mapped library identities; no explicit initialization |
| load_nvml | CDLL(libnvidia-ml.so.1) only; no NVML initialization/count and never a substitute for Runtime |
| load_cudart | Load the exact pinned wheel's libcudart.so.12, not a host CUDA replacement |
| cuinit | Original cuInit(0) return code; only on success call cuDeviceGetCount |
| runtime_count | Original cudaGetDeviceCount return code in another fresh process, avoiding PyTorch's cached device count |

Each worker independently verifies authority, source lock and F1/F2/merge
topology, then installs unchanged TSYNC seccomp and Python guard before loading
driver libraries. Loader constructors are native code under those guards, so
loader-only means no explicit CUDA/NVML initialization API, not proof that a
vendor constructor has no side effects. Device stat/access does not prove
successful device open/ioctl or cgroup permission. Read-only ldconfig -p/readelf
are optional metadata tools; absence is explicit and is not a CUDA failure.

Missing SONAME/dependency, wrong ELF/symbol/version, stub/compat path suspicion,
driver initialization failure, and successful initialization with zero visible
devices can be distinguished. A loader failure in the sanitized worker with a
host-only library candidate supports a linker hypothesis; it is not automatic
causal proof. This tool cannot attribute a failing native syscall. If unresolved,
request a separately reviewed observation/control design. Never initialize CUDA
outside the guard, relax syscall rules, or silently restore host environment.

Direct API codes are retained numerically. `errno_after_call` is explicitly not
a syscall trace or a substitute for CUDA's return code. Initializing a driver is
a GPU diagnostic even when no kernel, tensor or inference runs. No automatic
CUDA/security/root-cause PASS is produced.

## Source, environment and evidence contract

Notebook: `notebooks/SafeShift_InternVL3_CUDA_DIAGNOSTIC.ipynb`.
Maintainer builder: `python scripts/build_internvl3_cuda_diagnostic.py`.
Owner uploads the generated notebook unchanged. One approved Save & Run All
discovers its fixed release PR branch, verifies the full source inventory and
standard merge, installs software, then runs six distinct subprocesses.
Python/CUDA/torch/Transformers and all software pins reuse the existing InternVL3
build. No model provisioning entrypoint is called and no checkpoint is fetched.
No torch import is needed to call the pinned CUDART directly. The per-worker
environment checks every pinned distribution before the diagnostic.

Safe metadata is bounded and restricted to selected library/device information.
Unknown paths are hashed; runtime paths use a relative <runtime> label. No full
environment, secrets, payloads, command line or raw dlerror/traceback is exported.
Only parsed relevant linker/dependency rows are exported, not utility output.
Monitor coverage and conservative fatal responses remain inherited from PR #113.
Functional loader/CUDA failure is an observation and does not hide independent
later stages; security/source/environment/worker/evidence failure stops them.
There is no retry. Launch-intent markers survive a child failure without claiming
that an API returned. Existing manifest/archive verification retains partial
evidence, including a dedicated export-failure receipt if packaging fails.

## Release gates — not an execution grant

The new authority's grant is null. Scope contains no weights, model load,
inference, data/labels/GT, retry, unguarded CUDA or security expansion permission.
All diagnostic calls, loader-only metadata, pinned software provisioning,
retention and the unchanged local-peer relay boundary require the exact new
Research Lead approval flags plus durable decision/audit references. PR #112/#113
references and recovery attempt IDs cannot authorize these diagnostics.

After direct ChatGPT GitHub review and a separately requested independent audit,
Lead must approve the precise F1/payload and issue a unique attempt in an
authority-only F2; M must be a standard merge with parents [BASE,F2] and F2's tree.
Owner then selects T4 x2/Internet ON for source/software preparation and runs
once. Global cross-session non-reuse still requires Owner/Lead accounting.
No F2, grant, audit invocation, merge, Kaggle or GPU run is supplied by this task.

Any future environment/loader policy change, new syscall allowance, tracing or
unguarded comparison requires separate review and approval. Current diagnostic
implementation requests no additional syscall or network capability.

## CPU validation

| Platform / scope | Result |
| --- | --- |
| Linux: diagnostic + monitor + recovery + one-click + capture + T1 | 140 cases: 139 PASS, 1 Windows-junction skip |
| Linux: related LS1/native PA3/Qwen runner-placement/InternVL3 prep-runtime | 222 cases: 220 PASS, 2 opt-in real-tokenizer skips |
| Windows: final diagnostic + EBADF regressions | 33 cases: 31 PASS, 2 Linux-native skips |
| Windows: related six-module regression | 222 cases: 220 PASS, 2 opt-in real-tokenizer skips |

All CUDA/library objects in tests are CPU doubles. Native Linux tests exercise
the guards with local synthetic sockets and one compiled synthetic shared library,
never a real driver or model. That fixture loads under an inherited library path
and fails after the unchanged child_environment removes it, both with the guards
installed. This proves conditional loader behavior, not the Kaggle root cause.
Real procfs and synthetic races cover first-fstat EBADF versus permission/later
descriptor errors. Tests also cover unchanged loader policy, missing dependencies,
ELF/symlink/required-symbol failures, original CUDA error codes, no NVML fallback,
separate subprocesses, null/old/forged-source grants, guard order, fatal stop,
failure export, no attempt reuse, actual notebook-cell Run All with CPU doubles,
and real Git F1/F2/merge/inventory/tampering negatives.

The released recovery regression now checks its historical F1 archive rather than
comparing an old lock to subsequent code; it normalizes the already issued grant
when comparing the original null template. Historical notebooks, authorities and
locks remain byte-identical. Source lock/notebook AST and nbformat 5.11.1 schema
validation, Python compilation and git diff whitespace checks pass.

Commands, from the repository root with CUDA_VISIBLE_DEVICES empty for CPU tests:

```text
python -m unittest tests.test_internvl3_cuda_diagnostic tests.test_internvl3_monitor tests.test_internvl3_recovery tests.test_hnlo_one_click tests.test_hnlo_capture tests.test_hnlo_t1_cpu -q
python -m unittest tests.test_ls1 tests.test_pa3_native tests.test_qwen_runner tests.test_internvl3_prep tests.test_internvl3_runtime_result tests.test_qwen3_runtime_placement -q
python -m unittest tests.test_internvl3_cuda_diagnostic tests.test_internvl3_monitor.CheckpointRaceTests -q
python -m compileall -q safeshift/diagnostics/internvl3_cuda scripts/build_internvl3_cuda_diagnostic.py
python scripts/build_internvl3_cuda_diagnostic.py
git diff --check
```

Test hosts: Windows Python 3.11.9/Pillow 11.3.0; WSL Linux Python 3.14.4/Pillow
12.3.0, nbformat 5.11.1. Linux uses a byte-identical local source checkout because
Linux Git cannot resolve a Windows worktree's D:/... metadata; the ignored test
venv/checkout reside in data/processed. Neither host substitutes for the pinned
Kaggle environment. No GPU, Kaggle, real tokenizer/model/weights or data test was
run. The unrelated full repository suite was not needed for this bounded change.

Primary call-path references carried forward from the completed analysis:
[PyTorch 2.6 Python CUDA](https://github.com/pytorch/pytorch/blob/v2.6.0/torch/cuda/__init__.py),
[PyTorch CUDAFunctions](https://github.com/pytorch/pytorch/blob/v2.6.0/c10/cuda/CUDAFunctions.cpp),
[NVIDIA cuInit](https://docs.nvidia.com/cuda/archive/12.4.0/cuda-driver-api/group__CUDA__INITIALIZE.html),
[NVIDIA container configuration](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html).
