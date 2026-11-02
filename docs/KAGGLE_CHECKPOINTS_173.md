# Issue173 — reuse original TRAIN and real checkpoint verification

Date: 02/11/2026 (Asia/Bangkok). BASE/main:
`33e9f3cc4daf00c37a31b2347c143444d6add0bb` (PR174 merged).
Authority: [Owner's continuation](https://github.com/tantdna2/SafeShift/issues/173#issuecomment-6580770922)
and the direct task in this session. One branch `verify/issue173-real-checkpoints`,
[Draft PR #175](https://github.com/tantdna2/SafeShift/pull/175), no merge.
Historical fresh171 production fences remain intact.

## Final handoff — 03/11/2026

**Actual TRAIN bytes and all8 checkpoint shards verified. Two native calls total;
no call replay; MiniCPM remains BLOCKED.**

| Model | Actual weights verification | Load/inference | Classification / HNLO |
| --- | --- | --- | --- |
| Qwen3 | PASS,4 shards/index/source/marker | PASS, one call in v2/sourceae5b488 | Strict SUCCESS; HNLO_VALIDATED |
| InternVL3.5 | PASS,2 shards/index/source/marker | PASS, one call in v5/source1e744d9 | Strict INVALID preserved; raw logits unaligned, no numeric HNLO |
| MiniCPM-V-4 | PASS,2 shards/index/source/marker | BLOCKED before load/call: HOST_OR_CGROUP_RAM | NOT_ATTEMPTED; label-only policy unchanged |

[Final receipt](research/evidence/issue173/final-native-evidence.json) independently
checks all5 attempts, outer sidecars/CRC/member hashes, actual native markers,
loaded environments, raw/result checksum, strict parser replay and independent
decoder evidence. All calls use the same original first TRAIN image; per-image
identities/hashes/raw remain private. All5 jobs are terminal and GPU reservation0.
No checkpoint weights or images were downloaded/copied in the verification campaign.

V5 source `1e744d991613f48d81ccf0046bc35c5fdab9d1e2`, private Kaggle
`safeshift-issue173-native-smoke-v5/1` (kernel142340475), exported78 members:
SHA256 `035c4d9b0216378e23ecc812e1221d68fe451ec25a9cbc3fd8977b5794690619`.
The scoped NVML utility path and explicit mounted CUDA driver binding passed
real driver/T4x2/CUDA FP16/isolated pinned-runtime checks for InternVL. It loaded
actual weights and produced14 tokens; its strict INVALID is durable, with no
parser relaxation, prompt change, label rescue or rerun. InternVL HNLO remains
RAW_LOGITS_AVAILABLE_BUT_UNALIGNED/NO_VALID_GENERATED_LABEL.

MiniCPM setup/software and original image decode passed. Its subsequent RAM
gate blocked before a load reservation or native call. Last measured available
RAM after advisory cache reclamation:13,950,664,704 bytes (about12.99 GiB), below
the unchanged16 GiB floor; the exact later imported-worker value was not
captured. Advisory scanning reached50,000 files and records partial coverage;
it does not prove all cache was reclaimed. No absent model-load/inference/fit
evidence is inferred. A future separately reviewed continuation should isolate
MiniCPM in a fresh single-model VM or establish a bounded, measured resource
lifecycle, retain all prior attempts, and use only its unused one-call budget.
Do not rerun Qwen/InternVL or restart this submitted notebook. No more jobs are
launched in this handoff; production/full TRAIN/TEST remain blocked.

Final runtime CPU checks on immutable1e744d9: **39/39 Issue173 +55/55 fulltrain
PASS**, no skips/errors, including Linux process/log tests and all six historical
PREP notebook payloads. Receipts retain the earlier proposed source's payload
FAIL and interrupted broad Windows invocation; neither is relabeled PASS.
Reporting-only regeneration against all private ZIPs reproduces the final
public JSON exactly. Source cell bytes of all submitted notebooks match their
staged versions despite Kaggle JSON normalization.

Reproduce sanitized evidence without exposing raw payload:

```console
python -B -m scripts.report_kaggle173_evidence --artifact-root data/processed/issue173-verification --output data/processed/issue173-verification/new-review-receipt.json
```

The artifact root must contain the five original `smoke-output-v1` through
`smoke-output-v5` directories with ZIPs and sidecars. Do not commit those files.
The complete private attempts are not pooled into scientific outputs; the
technical summary only accounts for their distinct calls and failures.

One Draft PR for ChatGPT's direct review and decision on Antigravity audit.
No merge, audit PASS, READY FOR OWNER, full-cohort qualification or scientific
result selection is claimed. The remaining sections preserve the implementation
and failed-attempt history supporting these final outcomes.

## Rights and reused evidence

**RIGHTS_VERIFIED_FOR_THIS_SCOPE**: private, noncommercial SafeShift TRAIN
integrity checks and bounded technical smoke on Owner-controlled Kaggle resources;
no public raw redistribution, TEST reads, new labeling, or scientific release.
This combines the Owner's explicit confirmation of control/data rights with the
historical source/rights record in [THESIS_DATA_PROTOCOL](research/THESIS_DATA_PROTOCOL.md#2-registry-mức-hồ-sơ-nguồn-số-lượng-quyền-và-hdvt),
the original private Input and prior authorized execution receipts, and a fresh
read of the official dataset card at the **exact pinned revision**:
[Tetrabot2026/InspecSafe-V1](https://huggingface.co/datasets/Tetrabot2026/InspecSafe-V1/raw/f3cb7d3e7827c1afc1c5bfd0524257984bba46ab/README.md).
Its bytes SHA256 is `3b667d549cb8612b044a2642da06e66fbcb6d86c321cca4ad9c65bc40f0be203`.
Both YAML and License section declare CC BY 4.0; the card reports 3,763 TRAIN.
No cloud-specific prohibition was found in that card or the inherited project
record. The private Kaggle copies report license `unknown` in upload metadata;
this is not a replacement license or proof of a contrary restriction. Their
bytes must independently match the source locks before use.

Attribution: **Tetrabot2026 / TetraBOT, InspecSafe-V1**, revision
`f3cb7d3e7827c1afc1c5bfd0524257984bba46ab`,
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Images and existing labels remain unchanged; only a derived integrity projection
is generated privately if no suitable seal exists. This scope finding is not
a new certificate about industrial sites, people or other third-party rights.
No specific conflicting restriction has been identified requiring a new Owner
confirmation. New data, redistribution and scientific release remain separate.

Reused rather than rerun: [PR174 software v2](KAGGLE_PREFLIGHT_173.md#version-2-all-pinned-softwareprocessor-checks-passed),
all three exact processor/ABI/CUDA tensor results and the 4.21 GB Qwen software
archive. Historical MiniCPM official160 and InternVL official recovery admission
receipts match the tracked checkpoint identities; these are inherited evidence,
not a fresh byte check. No historical predictions are imported.

## Read-only verification design

Existing private Inputs: original `inspecsafe-v1-kaggle` plus
`safeshift-pilot-input` (which already contains the original 2,488,945-byte master).
The local original master's SHA matches
`a35e91fb431752dbf3b6c161f227d953d5748d69ef9f39aef613019faca33008`.
TRAIN160 alone is not evidence for the complete original TRAIN image bytes.

Existing checkpoint Outputs: `safeshift-prepare-internvl35/1`,
`safeshift-prepare-minicpm4/1`, and
`safeshift-qwen3-m1-model-provision-kaggle` (exact version resolved at submission).
All three are COMPLETE. Downloaded real JSON indices match their expected sizes;
the Qwen historical manifest identifies the four expected shards. The Kaggle
SDK `kernels_list_files` size field returned values around 900 for these objects,
including multi-GB shards. Those listing sizes are **not** accepted as physical
file sizes or integrity evidence; mounted `stat` and streamed SHA256 are required.

`verification173.py` checks the exact flat inventories, source/marker identity,
index bytes, every shard's size and streamed SHA256, bounded safetensors headers,
unique JSON keys, shapes/dtypes, contiguous byte spans, complete tensor-to-shard
membership and total tensor bytes. It imports no tensor/model libraries. The
historical layouts are verified in place; no source lock or revision directory is
renamed to make an old release executable.

`verify_kaggle173_inputs.py` reads only JPG paths from the SHA-verified original
master under the original TRAIN subtree. It does not open annotation sidecars or
TEST files, copy images, change ordering or decode images. Original master label
fields are validated by the existing integrity contract, never exported or used
to repair predictions. A private ordered projection/mapping seal records the
common three-model cohort. It does not activate a fresh171 Input or campaign.

CPU notebook: private, Internet OFF, no GPU, 3,000-second internal alarm and
3,600-second job ceiling. Read-only mounts avoid duplicating 17.53 GB Qwen weights,
9.47 GB InternVL or 8.12 GB MiniCPM and avoid reinstalling software. A small
Output reserve is required. No downloader exists in this verification route.
The storage helper rejects a Qwen download plus software archive and reserve on
the previously observed 19.5 GiB Output filesystem.

Two separate exports: sanitized checkpoint/environment/count receipts; and
**PRIVATE-TRAIN-SEAL.zip**, containing private per-image metadata/failure traces.
Keep the latter outside Git/GitHub. Every invocation creates a new evidence
directory, never an inference attempt or production reservation. Byte PASS does
not imply weights loaded, GPU fit, smoke PASS or scientific qualification.

Build from committed bytes:

```console
python -B -m unittest discover -s tests -p test_kaggle173_verification.py -v
python -B -m scripts.build_kaggle173_verification --source-commit <exact40hex> --output notebooks/SafeShift_ISSUE173_CHECKPOINTS.ipynb
```

## Actual existing-file verification

Private CPU notebook `nguynanhtn/safeshift-issue173-existing-bytes/1`, kernel ID
142313709, is **COMPLETE**. Executed source
`964ee5e9e348f0c5ccedf79b37f4a8131e5216d6`; every remote cell source matches.
Kaggle normalizes notebook JSON: submitted bytes SHA
`5dee3f8762975f42b5628ef78f79c213020aa180bece7a820be94e3a55d8ff2f`,
normalized remote SHA `0354ffd4a54c32bcdf61682deefd53081b4a4fdb55ed654614b085f2d406cc31`.
The [sanitized receipt](research/evidence/issue173/checkpoint-bytes-v1.json)
contains actual file sizes, full SHA256s, header/tensor counts and model revisions.

| Model | Actual shard bytes | Tensors | Checkpoint bytes/header/index | Loaded / inference |
| --- | ---: | ---: | --- | --- |
| Qwen3 | 17,534,339,512 | 750 | PASS, 4 shards, 16 exact snapshot files | NOT_RUN / 0 |
| InternVL3.5 | 9,465,085,464 | 841 | PASS, 2 shards, source and marker | NOT_RUN / 0 |
| MiniCPM-V-4 | 8,119,153,016 | 741 | PASS, 2 shards, source and marker | NOT_RUN / 0 |

**TRAIN_BYTES_PASS**: all 3,763 original JPG bytes checked; 0 missing, 0 changed,
0 duplicate IDs; original order and common projection for all three models.
This matches the frozen original master, not a new upstream archive comparison.
No image was rewritten and no annotation sidecar/TEST file was opened. An early
bounded dataset-listing operation included filenames across splits; no TEST
payload was downloaded/read and those private listings stay outside Git.

Runtime: CPython3.13.15 stdlib-only verifier, cgroup limit30 GiB, about19.50 GiB
Output free and 1.02 TiB scratch free on different devices. No GPU was requested.
Verification took797.37s. Download/copy bytes=0; model calls=0; weight loads=0.
Public evidence ZIP SHA256
`9f4e56e31b83b8e845318c7bc48620f927111072c7eae4691b88d6a15692b7f2`:
5 members independently checked with CRC/member SHA and sidecar. Separate
private seal:4 verified members, including the original ordered projection,
locator mapping and three-model binding; no private IDs/image hashes are in Git.

The initial manual log-stream endpoint returned HTTP error; the official
`api.kernels_logs_stream` worked and preserved all model progress. A bounded
dataset-listing helper reached its page ceiling; it was stopped, not silently
treated as complete. The verifier uses exact original locators, not listing
order or a directory walk. A local regex/glob mismatch stopped before download
and was corrected to the Kaggle CLI's regex syntax. All operational evidence is
retained privately. None caused a model call or checkpoint download.

## Separate one-call smoke route

`scripts/smoke_kaggle173.py` is independent of production authorization and
does not call its internal worker/factory/controller. A committed proof pin
requires the actual CPU ZIP above, complete TRAIN and all three real checkpoint
PASS results. Parent and direct child rederive ordinal0 from the original master;
arbitrary images, model scopes, source drift, changed budgets and extra calls
cannot be admitted by an `approved` flag. Exclusive per-model load reservations
block repeat load/call in the same workspace, including after errors. External
Kaggle history/terminal/quota checks enforce a single submitted smoke version;
no global cross-VM exactly-once guarantee is claimed.

The fixed smoke campaign/series namespace is `issue173-smoke-*`, never fresh171.
Max1 image/model,3 calls total,1 load/model,3300s internal/3600s job. Technical
resource budgets only: driver580.178.04 from PR174,13,000 MiB free on each physical
T4,16 GiB available RAM,24 GiB scratch and1 GiB Output; 1 MiB physical/fsync probes
on scratch/Output. These are not scientific O5 thresholds or full TRAIN release.
Pinned new-VM interpreter/venv installation is necessary; the completed software
preparation is not repeated. Qwen consumes the previously verified offline
archive; no model weights or replacement datasets are downloaded.

The Qwen smoke constructor explicitly admits the old verified flat layout and
inherits the unchanged QwenBackend generation/decoder/parser/HNLO methods. Its
own constructor identity/hash is recorded, not misrepresented as the previous
constructor. The exact model public code, snapshot files, numerical settings,
device map, max32/SDPA/C1 stay locked. Peers use unchanged CandidateBackend;
MiniCPM installs only the already adopted resampler FP32 exception and remains
label-only. No source lock is rewritten, path aliased or large weight copy made.

Raw/native evidence is fsynced before strict parsing and HNLO; INVALID stays
durable. HNLO failure preserves classification and stops further model work.
Every failure/partial Output is retained with no automatic retry. A consumed
call can never be retried under this scope. Final live smoke results will be
appended here; checkpoint verification alone is not an inference PASS.

```console
python -B -m unittest discover -s tests -p test_kaggle173_smoke.py -v
python -B -m scripts.build_kaggle173_verification --smoke --source-commit <exact40hex> --output notebooks/SafeShift_ISSUE173_SMOKE.ipynb
```

## Preserved first smoke failure and controlled pre-load repair

`safeshift-issue173-native-smoke/1` (kernel142318016) exported successfully;
**model smoke BLOCKED**, not PASS. [Sanitized failure](research/evidence/issue173/native-smoke-v1-failure.json)
binds executed source `d14218b4df956721e5d32dfc3ce226b40be8048c` and ZIP
`a296d13984e179a2087acc25a6f45c58f4e15eeb4e32a4efdc46ce8b2a8fac17`.
All22 members/CRC/checksums/sidecar and remote cell sources checked. Qwen setup
completed in303.83s; its exact pinned software/ABI/source and first-image decode
passed. The unchanged16 GiB available RAM gate then raised `HOST_OR_CGROUP_RAM`,
before hardware/CUDA checks, a load reservation, weights or any native call.
No load reservation/native marker/loaded environment exists. All3 calls remain
unused; peers are NOT_ATTEMPTED. The failing numeric available RAM was not
captured by v1 and is **unknown**, not invented.

The owned offline wheel extraction and compiled build cache are a plausible
contributor to the cgroup charge; this is a diagnostic hypothesis until new
before/after measurements are available. A controlled source repair keeps the
16 GiB floor and every model/prompt/parser/HNLO/precision/source lock unchanged:
under a separate300s CPU child, remove only this attempt's redundant public
wheel/build copies and request advisory cache eviction for large regular files
in its retained runtime (fsync + POSIX_FADV_DONTNEED). Runtime binaries remain
intact. No global cache operation, weight/Input/history/raw deletion or RAM
reinterpretation is used. Source paths resolve strictly within the named owned
scratch root; retained files and resource/source checks are revalidated before
load. Advisory success itself is not a RAM PASS.

The next smoke uses a new `issue173-smoke-20261102-v2` identity and private
notebook, attaches the sealed v1 failure, and requires its exact SHA/source and
**zero native markers, load reservations and verified loads**. Unknown or consumed
history blocks; no consumed call is retried. The original CPU byte verification
is reused, not rerun. Total authorization remains3 model-image calls across both
attempts, max1/model. No result is imported into fresh171 or official history.

Final-source Linux CPU evidence before the first smoke:31/31 PASS, no skips,
on immutable `d14218b`, [receipt](research/evidence/issue173/linux-checkpoint-smoke-d14218b.json).
The broad Windows invocation was interrupted without a suite verdict; it is not
reported as PASS ([record](research/evidence/issue173/windows-broad-interrupted.json)).
Its partial log remains private. Focused tests include bad/truncated shard/index,
bounded headers, missing/duplicate images, combined storage budget, immutable
payloads, raw-before-parse, durable INVALID, no-retry reservations, forged direct
worker requests and preserved HNLO failures. New repair regressions cover exact
owned cleanup/runtime retention, unchanged RAM floor, and refusal to reinterpret
a zero summary containing a prior call/load reservation.

## Qwen actual inference PASS; remaining peer continuation

[Attempt v2](research/evidence/issue173/native-smoke-v2-result.json), private
`safeshift-issue173-native-smoke-v2/1` (kernel142325818), source `ae5b488`,
exported65 verified ZIP members, SHA256
`f1f4fefabff4a6fc80f8863bcc314a13949c53815f9b535170cceda1ccd7117d`.
Qwen loaded the actual four pinned shards and completed exactly **one native
TRAIN image call**, strict classification SUCCESS and native HNLO status
HNLO_VALIDATED. Raw/result/trace/request/native marker and loaded environment
remain private. This is technical inference evidence, not a scientific result.

The repair is now measured: cgroup-constrained available RAM4,555,481,088 bytes
before and18,531,954,688 after cleanup/advice;45 retained runtime files totaling
7,185,237,076 bytes advised, no advice errors. The unchanged16 GiB gate passed;
Qwen setup305.38s, reclaim2.28s, native198.58s. Actual isolated cu128/T4x2 and
resource/software receipts are included. No weight/Input/history bytes changed.

InternVL then failed **before a load reservation or call**: the new supervisor
opened setup.log, while the unchanged peer provisioner requires the same filename
with exclusive creation. MiniCPM was not attempted. Distinct *-supervisor.log
files correct the collision, matching the successful PR174 diagnostic. A real
Linux child integration regression opens its own exclusive setup.log under the
supervisor. No protected provisioner changed.

Continuation v3 is **peer-only**: two calls remain. It requires both previous
sealed archives, reconciles Qwen's sole marker/load/raw and rejects any peer
reservation or unknown consumption. Parent/direct worker reject Qwen before
private reads/load. Current-run Qwen status is PRIOR_SMOKE_CONSUMED_NOT_REPLAYED;
its PASS remains attributed to v2/sourceae5b488, not copied into v3 as a new call
or imported into scientific series. The original image identity must match.
Peer runtime caches are advised before/after calls under the same owned-root
and unchanged measured RAM rules. A bounded advisory scan is recorded as partial
if its limit is reached; it cannot substitute for the actual RAM gate.

The first v2 save request was rejected409 because the staging title still
resolved to v1's slug. Inventory, unchanged v1/current-version1 and zero GPU
reservation proved no v2 job was created. The corrected title/slug was submitted
once, with identical source. Both intents/reconciliation remain private.

## V3 driver gate and final bounded diagnostic continuation — 03/11/2026

[V3 receipt](research/evidence/issue173/native-smoke-v3-blocked.json): source
`5139775`, private `safeshift-issue173-native-smoke-v3/1`, kernel142332987,
26 checked ZIP members, SHA256
`4b74106fe476858bceffa0ce3ec50d940af0e707ecf05456370a56c6101f35c5`.
InternVL setup/log isolation, pinned software/ABI, image decode, storage probe
and RAM checks passed. Native hardware observation then failed: nvidia-smi with
the exact GPU index/name/free-memory/driver query returned12 before CUDA, a load
reservation or inference. [NVIDIA's return-code definition](https://docs.nvidia.com/deploy/nvidia-smi/index.html)
identifies12 as NVML library not found/loaded. It does not prove corrupt weights.
The precise failing stdout/stderr was not captured in v3 and is unknown.
MiniCPM was not attempted; total remains one Qwen call, zero peer calls/loads.

V4 adds a no-model kernel driver observation and preserves command/exit/stdout/
stderr plus bounded loader-path diagnostics in the actual pinned child. It
keeps the same hardware/driver/CUDA/RAM gates and does not install drivers,
change loader settings or treat Torch tensors as a replacement for NVML.
It admits the sealed v3 zero-peer history as well as v1/v2. Only if real gates
pass can the two remaining peer calls occur; Qwen remains blocked at dispatch.
A persistent driver failure remains BLOCKED, not READY or a need for blanket
Owner permission. No automatic/infinite retry is implemented.

## Measured loader isolation and scoped driver binding — 03/11/2026

[V4 evidence](research/evidence/issue173/nvml-loader-v4.json): kernel physical
driver PASS (two T4s,580.178.04), while the isolated worker's nvidia-smi exits12.
The same mounted `/usr/local/nvidia/lib64/libnvidia-ml.so.1` exists in both.
Kernel LD_LIBRARY_PATH includes that directory; the clean worker has no loader
path and find_library returns null. The utility's captured output confirms NVML
cannot be found. Thus the issue is loader isolation, not a missing checkpoint or
a need to lower a hardware gate. V4 sealed28 members, SHA256
`2ae1b33411e93c3b9c9a43f9e1d05d9368704d43795a1e7052bf8c12dcf4aaee`;
zero peer reservations/loads/calls. Qwen's single v2 call remains untouched.

V5 binds the existing fixed host `libcuda.so.1` explicitly in the pinned worker
before importing Torch, with ELF/path/hash/size evidence and a retained handle.
It changes no Python LD_LIBRARY_PATH. For nvidia-smi only, the subprocess receives
the fixed mounted NVIDIA directory. The final implementation keeps
`environment.py` byte-identical to BASE and uses an explicitly identified
smoke-local utility check with the same original validation. No LD path is added globally or passed to Torch, no driver is installed,
and no model/library pin, precision, parser/HNLO, image or metric changes.
Software/compiled ABI, NVML driver/count/memory and actual same-worker CUDA FP16
must all pass again before a load reservation. The binding is explicitly
identified as issue173-explicit-host-cuda-driver-v1, not hidden as unchanged
execution. V5 also requires the sealed zero-call v4 lineage. Only two peer calls
remain; this is a technical source revision, never scientific adoption/pooling.

Final integration keeps `safeshift/verification173.py` outside the historical
fulltrain source glob. The earlier proposed optional utility environment change
caused the six historical PREP payload integrity checks to fail (55 tests,
one test with six subcase errors); that failed receipt is retained. The shared
environment file was restored exactly to BASE; no old notebook or source lock
is rewritten. The #173 builder explicitly embeds the separate verifier.
