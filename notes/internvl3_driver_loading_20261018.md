# InternVL3 NVIDIA driver lookup repair PREP — 2026-10-18

BASE_SHA: `f0613c9c38df6283f9725ed94e713091279261ec` (merged PR #114).
Preparation only. GPU initialization after this repair is **NOT VERIFIED**.
No CUDA FIXED, security PASS, model execution, old-grant reuse or merge claim.

## Original evidence and causal limits

Owner package: `internvl3-cuda-session-20261018T084058Z-10b418ec.tar.gz`.
SHA-256: `fdea5bed1b0b75edd6aee63735934c0815ad696b74bbb7de2df513de8ff017a5`;
size 240902 bytes; manifest SHA-256
`1cb450a95b8174116b97a7669bc7800a0bfdc58d88f11ad0c1800c6991b764e8`.
Independently checked archive and manifest hashes, exact member inventory,
67/67 member size/hash pairs and byte identity of the external result JSON.
Original files remain unchanged; extracted evidence is local and ignored under
`data/processed/internvl3_driver_evidence/`. No driver binary is committed.

| Evidence member | Verified observation |
| --- | --- |
| `host-metadata.json` | LD_LIBRARY_PATH contains `/usr/local/nvidia/lib64`; neither driver SONAME appears in linker cache. |
| `host-metadata.json`, `metadata/result.json` | Host and guarded worker see the same driver files: libcuda SONAME symlink to `libcuda.so.580.178.04`, 96284520 bytes, inode 20506; NVML to `libnvidia-ml.so.580.178.04`, 2291896 bytes, inode 20504. ELF magic present; only libc/libm/libdl/libpthread/librt dependencies; no recorded RPATH/RUNPATH. These are observations, not vendor authenticity proofs. |
| `metadata/result.json` | Worker LD_LIBRARY_PATH and LD_PRELOAD absent; visibility `0`; same cache without driver SONAME entries. |
| `load_cuda/result.json`, `load_nvml/result.json` | LOAD_FAILED, `cannot open shared object file`; no driver mappings. |
| `load_cudart/result.json` | LOADED from locked wheel's `nvidia/cuda_runtime/lib/libcudart.so.12`, not host CUDA. |
| `cuinit/result.json` | LOAD_FAILED; `initialization_called=false`. cuInit(0) never ran. |
| `runtime_count/result.json` | Original cudaGetDeviceCount return code 35, count null; only pinned CUDART mapped. |

It is proven that the worker cannot load the driver by SONAME. The missing search
directory explanation is very strongly supported by both metadata sets, absent
linker-cache entries, loader failures and `child_environment()` source. The old
CPU fixture establishes the mechanism conditionally, not Kaggle CUDA success.
Owner reports driver 580.178.04, consistent with both observed target filenames.
The package's path metadata `sha256` fields hash **path strings**, not driver bytes;
they must never be used as binary authenticity checksums. New workers hash bytes
for provenance after validating the image-managed path; these are not signatures.

CUDA 12.4 identifies 35 as `cudaErrorInsufficientDriver`; that numeric return alone
does not establish an old installed driver. NVIDIA documents the same result when
no driver can be loaded. No successful cuInit/Runtime count after repair exists.
`DIAGNOSTICS_COMPLETED` means six nonfatal observations, including failed CUDA
observations. It never means CUDA initialized or a model may load.

Primary sources checked 2026-10-18:
[CUDA 12.4 error types](https://docs.nvidia.com/cuda/archive/12.4.0/cuda-runtime-api/group__CUDART__TYPES.html),
[CUDA device count documented driver-load failure](https://docs.nvidia.com/cuda/archive/8.0/cuda-runtime-api/group__CUDART__DEVICE.html),
[dlopen semantics](https://man7.org/linux/man-pages/man3/dlopen.3.html),
[dynamic loader search/startup](https://man7.org/linux/man-pages/man8/ld.so.8.html).

## Selected minimal policy

No host loader variable is inherited, and `child_environment()` is byte-identical
to BASE. Restoring even only `/usr/local/nvidia/lib64` in LD_LIBRARY_PATH would
expose every object in that directory to the interpreter's startup loader before
seccomp/Python guard/monitor exist. Auditing two filenames would not constrain that
directory-wide pre-guard substitution risk. LD_PRELOAD has the same ordering risk;
ldconfig/image modification expands global scope. All three are rejected here.

Instead the new InternVL3-only worker reuses pinned provisioning, environment
verification, probes, seccomp, Python guard and monitor. After authority/source and
both guards, it verifies **both** objects before either native constructor runs:

- Exact platform directory `/usr/local/nvidia/lib64`, no arbitrary input or fallback.
  This Linux ABI location is not a personal filesystem path.
- Every ancestor is a real root-owned directory with no group/other write or
  set-ID bits. No directory symlinks, including parent aliases.
- Root-owned SONAME symlink points directly to the exact evidenced versioned name
  in that directory. Target is root-owned regular non-writable-to-group/other,
  non-set-ID, non-symlink; expected size must match the original evidence.
- ELF64 little-endian x86-64 ET_DYN, valid bounded headers/dynamic/string tables,
  matching DT_SONAME, nonempty dependencies restricted to the five evidenced
  system libraries. Embedded RPATH/RUNPATH/audit/filter/auxiliary tags are rejected.
- No already mapped CUDA driver/NVML/Runtime; no LD_LIBRARY_PATH/LD_PRELOAD/LD_AUDIT.
  O_NOFOLLOW open, fstat and change check; SHA-256 hashes actual bytes. Load via
  `/proc/self/fd/N` with RTLD_LOCAL|RTLD_NOW, keeping handles alive through probes.
  Verify SONAME reuses the same handle; no RTLD_GLOBAL or custom search path.

Both actual-byte hashes and validation records are durably written to
`driver-verified.json` before the first driver constructor. Successful handles
and their SONAME reuse are also retained in the stage result.

The fresh workers then run the same six PR #114 stages with unchanged locked
Runtime 12.4 and visibility. Failed trust/preload/guard/source checks stop the run
and retain partial evidence. Functional API codes remain original observations.
`CUDA_FIXED=false` remains explicit. This release loads no weights or model and
does no Qwen3 execution or dataset/labels/GT access. Production recovery remains
historical; applying this policy to a future model run requires separate review.

## Security limits and separate approval

This changes the **driver loading policy**, despite leaving process environment
bytes unchanged. DEC-PA3-014 is PROPOSED. Research Lead must separately approve it
and `driver_loading_policy_change_approved=true` in a new source-bound authority.
PR #112–#114 grants and review links cannot authorize this release.

Trust remains in Kaggle's root-managed image and mounts. A hostile privileged host,
or malicious code running as root (the evidence worker UID is 0), can change files,
mounts or memory. Permissions, file sizes and ELF checks cannot authenticate a
vendor binary or sandbox malicious native code. Descriptor loading pins the
opened inode through dlopen; it does not stop privileged in-place modification.
System dependencies use the unchanged loader namespace/default resolution;
guarded driver constructors and later internal loads remain native vendor code.
Unexpected required auxiliary drivers may fail; no speculative search fallback
is provided. The exact version/size allowlist deliberately blocks changed hosts.

The native seccomp policy is unchanged and inherited by descendants. The Python
guard and PARTIAL/UNOBSERVABLE monitor are unchanged. Local AF_UNIX peers may relay
traffic; absence of an observation cannot establish NO_LEAK or SECURITY_PASS.
Approval must cover this residual risk, image trust and native constructors,
software provisioning, diagnostic GPU API calls and artifact retention.

## Release and early GPU check

Maintainer builder: `python scripts/build_internvl3_driver_check.py`.
Notebook: `notebooks/SafeShift_InternVL3_DRIVER_CHECK.ipynb`.
New authority: `configs/diagnostics/internvl3_driver_authority.v1.json`, grant null.
Source lock: `configs/diagnostics/internvl3_driver_source.v1.json`.

Direct ChatGPT review first; separate independent audit only when requested;
Research Lead decisions and fresh unique `internvl3-driver-check-*` attempt;
reviewed F1 -> authority-only F2 -> exact standard merge M. Owner then uploads the
unchanged notebook and uses one Save & Run All, T4 x2, Internet ON for source and
software prep. The notebook rejects drafts/unmerged releases before provisioning.
No edits to SHA, path, configuration or code are needed by Owner. Cross-session
attempt accounting still needs Lead/Owner; no automatic retry is authorized.

**Yes, CUDA can be checked before downloading weights**: this standalone release
only provisions locked software and calls driver/Runtime APIs after guards. A
future evidence review must inspect cuInit code 0, positive driver device count,
Runtime count code 0/positive count, actual mapped identities and fatal/monitor
outcomes. Even those are a CUDA admission observation, not model/HNLO validation.
No technical probe/model execution rights are granted here.

## CPU validation

| Final validation | Result |
| --- | --- |
| Linux: driver + diagnostic + monitor + recovery + one-click + capture + T1 + related LS1/native PA3/Qwen/InternVL3 regressions | 384 cases: 381 PASS, 3 SKIP (Windows junction and two opt-in real-tokenizer tests) |
| Windows: driver + PR #114 diagnostic | 52 cases: 46 PASS, 6 SKIP (Linux native fixtures) |
| Windows: related LS1/native PA3/Qwen/InternVL3 regressions | 222 cases: 220 PASS, 2 SKIP (opt-in real tokenizers) |
| Windows: earlier full diagnostic/monitor/recovery/one-click/capture/T1 run | 161 cases: 133 PASS, 28 Linux-native SKIP; final driver-specific changes rechecked above |
| Notebook nbformat schema, code AST, compileall and whitespace | PASS |

Linux CPU host: Python 3.14.4, Pillow 12.3.0, nbformat 5.11.1. Windows CPU host:
Python 3.11.9, Pillow 11.3.0. These are test hosts, not changes to the execution
pins. Linux uses a byte-identical ignored source copy because Linux Git cannot
resolve Windows worktree metadata; all 574 source/inventory files were compared.
Root-owned native fixtures are created only in temporary private test directories.
The compiler builds tiny synthetic ELF objects with distinct SafeShift SONAMEs;
test-only private constants supply their directory, symbol names and sizes.
Production exposes no fixture path/environment/CLI override.

The final constructor fixture attempts socket(AF_INET) and observes EPERM under
the unchanged real seccomp filter. Tests also establish missing SONAME before
preload, successful same-object SONAME reuse afterward, the Python guard/monitor
stop, unknown paths, symlink escapes/directory aliases, stub/compat paths, bad ELF,
wrong SONAME/dependency/RPATH, size/owner/write violations, null/old/forged grants,
guard ordering, fatal stop/export/reuse, actual notebook Run All with CPU doubles,
and real Git F1/F2/standard-merge topology/tampering rejection. Protected Qwen3 and
PR #112–#114 executable/environment/guard/release bytes equal BASE.

Initial fixture failures were corrected and rerun: a missing fixture evidence
parent directory, a stale inventory during test edits, and the original CUDA
SONAME colliding with WSL's installed driver. The collision performed only a
guarded dlopen, no CUDA API call; final fixtures use unique synthetic SONAMEs.
The released PR #114 lock regression now checks its historical F1 archive and
normalizes the already-issued grant when comparing its original null template,
following PR #113's existing approach. No historical authority is rewritten.

Commands (repository root, Linux tests use the CPU environment above as root):

```text
python -m unittest tests.test_internvl3_driver tests.test_internvl3_cuda_diagnostic tests.test_internvl3_monitor tests.test_internvl3_recovery tests.test_hnlo_one_click tests.test_hnlo_capture tests.test_hnlo_t1_cpu tests.test_ls1 tests.test_pa3_native tests.test_qwen_runner tests.test_internvl3_prep tests.test_internvl3_runtime_result tests.test_qwen3_runtime_placement -q
python -m unittest tests.test_internvl3_driver tests.test_internvl3_cuda_diagnostic -q
python -m unittest tests.test_ls1 tests.test_pa3_native tests.test_qwen_runner tests.test_internvl3_prep tests.test_internvl3_runtime_result tests.test_qwen3_runtime_placement -q
python -m compileall -q safeshift/diagnostics/internvl3_driver scripts/build_internvl3_driver_check.py tests/test_internvl3_driver.py
python scripts/build_internvl3_driver_check.py
git diff --check
```

CPU suite results concern the final executable/test bytes; subsequent validation
documentation and its source lock are regenerated and rechecked before F1 commit.
GPU/Kaggle, model download/load, dataset access and old-grant execution are
intentionally NOT RUN. Post-repair CUDA initialization remains **UNVERIFIED**.
