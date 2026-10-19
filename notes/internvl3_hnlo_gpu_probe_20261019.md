# InternVL3 post-driver HNLO probe PREP — 2026-10-19

PREPARATION ONLY. DEC-PA3-015 PROPOSED; grant null. No model weights, model
construction/generation, GPU API or dataset/labels/GT access in this task.
Base: `d599aa93f57e0c5cc349f090c666e908edd7475e`; branch:
`prep/internvl3-hnlo-gpu-probe-20261019`. Existing releases and production files
are preserved byte-for-byte. This dossier does not grant execution or change
DEC-PA3-011 / D9R22 / the research protocol.

The [PR #115 GitHub record](https://github.com/tantdna2/SafeShift/pull/115#issuecomment-6258186856)
reports CUDA admission in its consumed diagnostic session (81/81 evidence files,
cuInit=0, Driver and Runtime count=1, six stages without fatal failure; model
load/generate=0/0). The record was checked directly; original Kaggle artifacts
were not supplied/rehashed during this preparation. Archive SHA-256:
`aca18fb3fd29d8cf2dca01b8679bdf79fcb84f4913b15cc85dc89826f9f44a06`;
manifest SHA-256:
`a39a4c679a971ba3eff305084765ce7f163a93fe2e12b9ffa4d92c491e7b734f`.
CUDA admission there does not establish InternVL3 load/generate/HNLO success.

## Prepared execution and driver lifecycle

1. The notebook's stdlib bootstrap verifies its own source payload, complete
   tracked inventory and exact release topology before importing repo code.
   `authorize()` then requires the independent source-bound Lead grant.
2. Software-only online preparation builds the unchanged Python/dependency pins.
   A fresh inspection child starts without torch, inherits a sanitized environment
   and GPU visibility 0, installs the unchanged TSYNC seccomp filter, then the
   Python guard/monitor, and checks the pinned Linux/offline environment.
3. `DriverSession` calls the **unchanged**
   `internvl3_driver.loader.preload` from merged PR #115. Fixed root-managed
   `/usr/local/nvidia/lib64` driver 580.178.04 objects and their SONAME symlinks,
   sizes, owner/mode/ancestors, ELF architecture/SONAME/dependencies/search tags
   are checked. Both files are opened/verified before loading, and their bytes
   are hashed. Native constructors run only under guards. File descriptors pin
   verified inodes through `dlopen(RTLD_LOCAL|RTLD_NOW)`; SONAME reuse is checked.
4. Only then import PyTorch and run existing CUDA availability/count/build/T4/
   free-VRAM admission. A failed condition prevents checkpoint provisioning and
   model loading. Successful inspection exits before a CPU-only online checkpoint
   provisioning child downloads the exact pinned inventory. No online work follows
   the single offline model probe.
5. A fresh probe worker repeats source/authority/guards/environment/driver/CUDA,
   verifies installed Transformers source hashes and the checkpoint inventory,
   checks full-vector resources/T1 and invokes NativeScorer once. It calls the
   diagnostic generation adapter once, never scorer.generate/calibration.
6. The driver session retains strong references in a process-lifetime registry,
   including all SONAME handles. Procfs device/inode and RTLD_NOLOAD handle checks
   after CUDA/model-load/generate/finalization require the original driver objects.
   A second/foreign driver or host CUDA Runtime mapping stops the attempt. All
   observed torch/CUDA/NVIDIA dependency mappings are recorded; Runtime must be
   the pinned `nvidia-cuda-runtime-cu12` wheel object. This is snapshot observation,
   not tracing every transient native dlopen. Additional libraries/constructors
   remain guarded wheel-native code, not vendor-signature attestation.
7. All available native IDs and raw/processed vectors are durably written and
   reread **before** decode/parse using `hnlo_capture.persist_hf`. Existing native
   counters block second model-load/generate calls and leave start/return markers.
   Raw provenance requires the actual processor list to be empty under verified
   generation source. Actual stopping classes, max length and EOS IDs are saved.
8. After the probe exits, a CPU worker with every GPU hidden rechecks the real
   tokenizer's 28 T1 branches and canonical Level01–Level04 order, probe status,
   counts, environment and monitor status, sealed vectors/trace, exact effective
   max-length/EOS settings, decision position, argmax, finite logits and stop cause.
   Existing replay computes `anomaly_log_odds(log_softmax(four_raw_logits))`.
   All gates must pass for TECHNICAL_HNLO_VALID. INVALID remains unmodified, N/A;
   HNLO_RESEARCH_VERIFIED is always false.

No LD_LIBRARY_PATH/LD_PRELOAD restoration, startup driver preload, additional
seccomp allowance, arbitrary path/Runtime fallback, retry or output rescue.
Monitoring remains PARTIAL/UNOBSERVABLE; no SECURITY_PASS or NO_LEAK. Local peers
may relay traffic; observations do not establish absence of relay.

## Full-vector resources and evidence retention

The existing lossless JSON capture stores every native raw and processed vector
for up to 32 steps separately, including EOS. `resources.py` plans against a
**200,000 vocabulary ceiling**, not an assertion about the model vocabulary.
After checkpoint checksum verification, its actual text-config vocabulary must
fit that ceiling and the budget is recalculated; unsupported sizes stop.
The already cached, hash-verified tokenizer/config snapshot measured during this
task has text-config vocabulary 151,674; the ceiling deliberately exceeds it.

At the ceiling: 12,800,000 scalars, 51,200,000 bytes (48.83 MiB) of FP32 native
tensors. Allow 64 JSON bytes per scalar: at most 819,200,000 vector bytes per
copy. Four copies (source journal, evidence copy, uncompressed archive bound,
serialization/export headroom) plus 512 MiB require 3,813,670,912 bytes, below
the inherited 4 GiB Output admission. No compression savings are assumed.
Inherited admission remains 24 GiB available RAM, 50 GiB scratch and T4 x2 with
13 GiB free per GPU. These conservative requirements may BLOCK Kaggle; no
relaxation/truncation is used to obtain PASS. Actual model/KV-cache/RSS/VRAM,
compile/download time and Kaggle quota/retention still require GPU validation.

An opt-in CPU profiler creates 32 full raw + 32 processed synthetic FP32 arrays
at the ceiling, invokes the actual persistence path, requires all 64 saved files
at decode time, verifies/seals/copies the journal and packages/rechecks every
archive member. It records time, peak RSS and all retained bytes; no model or
real tokenizer is involved. It is a storage measurement, not GPU feasibility.

Archive + manifest + SHA-256 receipt + result JSON + report are emitted by the
reused durable exporter. Partial journals, vectors and start markers survive
ordinary worker failures/hard child exits. Disk failure can prevent completion
of export; original files and an export-failure receipt remain where possible.
Whole Kaggle-session kills and Output retention are not guaranteed by CPU tests.

## Release and Owner handoff

Maintainer regenerates with `python scripts/build_internvl3_hnlo_probe.py`.
It refuses to overwrite a non-null grant. Notebook:
`notebooks/SafeShift_InternVL3_HNLO_GPU_PROBE.ipynb` (one code cell).
Bootstrap is copied in full into the cell so no unlocked helper is executed.
The lock excludes only this new authority and itself; the notebook's payload
assignment alone is normalized to avoid a hash cycle. Historical authorities,
notebooks, drivers and source locks remain locked data, never execution grants.

Before Owner execution, independently review/audit F1 (single child of BASE),
obtain Research Lead approval of DEC-PA3-015 and every grant flag, then create
F2 changing only `configs/diagnostics/internvl3_hnlo_authority.v1.json` with exact
F1/payload/new decision and audit URLs. Require standard merge M with parents
BASE/F2, identical M/F2 trees and M on main. No squash/rebase/drift allowed.
If main advances before release, rebase/rebuild/review a new F1 rather than bypass
the exact-base gate. This task stops at Draft PR without executing that release.

Proposed new attempt: `internvl3-hnlo-probe-20261019-01`, maximum one load and
one generate. PR #112–#115 grant/reference/attempt reuse is rejected. The local
ledger prevents repeated Run All in one Output filesystem. A fresh Kaggle session
can erase that ledger: Lead/Owner accounting must enforce single use globally.

After release verification, Owner uploads unchanged, selects **GPU T4 x2**,
enables Internet for preparation and clicks **Save & Run All once**. No code,
SHA, path, revision or authority edits. The Draft currently blocks before
provisioning/GPU. Preserve every export on success or failure; do not retry.

Research Lead approval still needed: new driver-loading/model load/generation
scope; source-bound technical exception while DEC-PA3-011 remains proposed;
checkpoint/software provisioning; actual raw provenance and numerical tolerance
(existing 1e-6 absolute/relative); full-vector retention; unchanged AF_UNIX boundary
and incomplete-monitor/local-peer/root-image/native-constructor residual risks.

## CPU validation

CPU checks completed with no weights/model/GPU execution:

| Check | Observed result |
| --- | --- |
| Linux new probe + existing one-click suite | 55 cases, 55 PASS |
| Final Linux new-probe suite, including foreign Runtime rejection and final notebook/source bytes | 29 cases, 29 PASS |
| Windows same two suites | 55 cases, 49 PASS / 6 Linux-native SKIP |
| Linux initial probe/monitor/capture/T1 suite | 88 cases, 87 PASS / 1 Windows-only SKIP; subsequent changes covered by focused reruns |
| Existing LS1/native PA3/Qwen/InternVL3/placement regressions on Windows | 222 cases, 220 PASS / 2 opt-in real-tokenizer SKIP |
| Actual cached InternVL3 tokenizer/config | T1 28/28 PASS, canonical Level01–04 IDs `[16,17,18,19]` |
| Installed Transformers 4.52.4 source vs historical audit plus new official source lock | PASS; three generation files byte-matched to official source commit |
| Full 32 raw + 32 processed CPU profile | PASS, all 64 full vectors persisted/reread before decode, seal/copy/archive integrity verified |
| New notebook JSON/AST, compileall, diff whitespace | PASS; final lock/notebook regenerated after documentation updates |

New tests cover source/authority/guard order, zero model calls on any failed
early gate, driver references through guarded finalization, CUDA before checkpoint
provisioning, one native load/generate, effective stop settings, checksum/T1 mapping
failure, raw persistence before failed decode, INVALID/N/A, killed/torn/failed
evidence exports, same-filesystem reuse denial and actual notebook Run All with
CPU operations. Real Git fixtures check F1/F2/standard merge and reject drift.
An archive comparison checks **every historical tracked file** against BASE,
except the intentional TASKS/DECISIONS appends.

Linux native integration uses real compiled synthetic ELF objects and unchanged
PR #115 preload, under actual TSYNC seccomp/Python guard/monitor. Constructors
verify INET denial, SONAME lookups reuse the loaded objects, process-lifetime
references survive local-reference deletion/GC, and a synthetic foreign Runtime
mapping is rejected. These are CPU fixtures, not NVIDIA driver/CUDA API calls.
The final native/source rerun passed all 29 cases.

Profile at 200,000 columns (planning ceiling), 32 steps, both kinds:

| Quantity | Measured |
| --- | ---: |
| Full vector JSON bytes | 247,843,328 (236.362 MiB) |
| Verified archive bytes | 58,717,969 (55.998 MiB) |
| All retained source/copy/archive bytes before profile.json | 554,500,523 (528.813 MiB) |
| Peak process RSS | 613,720,064 (585.289 MiB) |
| Wall time | 167.700 seconds |

No vectors were cut. The profile uses deterministic synthetic FP32 arrays and
native persistence/export, not the model's logits distribution or CUDA allocator.
Measurements are observations of this CPU/WSL storage path, not Kaggle limits.
`profile.json` SHA-256:
`5d2f54be5df25965cfb098efc2eba0143fe18f2ec11f5a56130a2bd78aa37d55`.
The local ignored Linux checkout retains artifacts under
`data/processed/internvl3_hnlo_vector_profile/`; no large evidence is committed.
The Linux checkout is a byte-identical PREP overlay on BASE, because Linux Git
cannot use Windows worktree gitdir paths. Profile/capture/resource code is
unchanged between measurement and final F1; the final lock binds those bytes.

Linux CPU: Python 3.14.4, Pillow 12.3.0, nbformat 5.11.1. Windows synthetic CPU:
Python 3.11.9, Pillow 11.3.0. Actual-tokenizer check uses Python 3.11.9,
Transformers 4.52.4, tokenizers 0.21.2 and huggingface-hub 0.30.2, with no torch
installed. These checks do not qualify the future exact Python/CUDA environment.
T1's full local report is `data/processed/internvl3_hnlo_cpu/real_t1.json` in the
preparation worktree; cached tokenizer bytes are only read, never redownloaded.

Reproduction from the appropriate repository checkout/CPU environment:

```text
python scripts/build_internvl3_hnlo_probe.py
python -m unittest tests.test_internvl3_hnlo_probe tests.test_hnlo_one_click -q
python -m unittest tests.test_internvl3_monitor tests.test_hnlo_capture tests.test_hnlo_t1_cpu -q
python -m unittest tests.test_ls1 tests.test_pa3_native tests.test_qwen_runner tests.test_internvl3_prep tests.test_internvl3_runtime_result tests.test_qwen3_runtime_placement -q
python scripts/profile_internvl3_hnlo_vectors.py
python -m compileall -q safeshift/diagnostics/internvl3_hnlo scripts/build_internvl3_hnlo_probe.py scripts/profile_internvl3_hnlo_vectors.py tests/test_internvl3_hnlo_probe.py
git diff --check
```

Real tokenizer recheck uses the existing offline `safeshift.ls1.tokenizer.t1`
with the cached exact-revision tokenizer-only snapshot, then `ordered_t1_ids`;
`capture.verify_sources` checks the actual installed package. The new generation
lock records official HTTPS URLs, commit, sizes and SHA-256 for utils, processors
and stopping criteria; the historical source audit is not modified.

Not run: real NVIDIA driver/PyTorch CUDA coexistence, exact pinned Kaggle build,
checkpoint download/load, real model outputs/logit provenance/EOS, GPU VRAM/time,
or whole-session Output retention. Actual CUDA/PyTorch Runtime compatibility can
only be accepted after the new guarded GPU admission and probe pass. Synthetic
CPU tests and prior PR #115 admission do not establish it.

## Changed-file inventory

Only these 18 paths are part of this PREP:

```text
DECISIONS.md
TASKS.md
configs/diagnostics/internvl3_hnlo_authority.v1.json
configs/diagnostics/internvl3_hnlo_generation_sources.v1.json
configs/diagnostics/internvl3_hnlo_source.v1.json
notebooks/SafeShift_InternVL3_HNLO_GPU_PROBE.ipynb
notes/internvl3_hnlo_gpu_probe_20261019.md
safeshift/diagnostics/internvl3_hnlo/__init__.py
safeshift/diagnostics/internvl3_hnlo/bootstrap.py
safeshift/diagnostics/internvl3_hnlo/capture.py
safeshift/diagnostics/internvl3_hnlo/contract.py
safeshift/diagnostics/internvl3_hnlo/driver.py
safeshift/diagnostics/internvl3_hnlo/orchestrate.py
safeshift/diagnostics/internvl3_hnlo/resources.py
safeshift/diagnostics/internvl3_hnlo/worker.py
scripts/build_internvl3_hnlo_probe.py
scripts/profile_internvl3_hnlo_vectors.py
tests/test_internvl3_hnlo_probe.py
```
