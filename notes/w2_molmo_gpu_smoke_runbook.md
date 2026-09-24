# W2.6B3B-PREP — Molmo runtime/interface smoke

**PREPARED / NOT_RUN.** Base main is
`36b934b37ff064bb097860f0a0aef43897938a64`; branch is
`validation/d9-molmo-gpu-smoke`. The Draft PR records **B3B_PREP_HEAD**, the exact
commit to execute later. No GPU, model download or real inference was used in PREP.
This platform-neutral runbook prepares one later owner-run smoke, not a benchmark.

## Identity and candidate

Model: `allenai/Molmo2-O-7B` at
`784410650d12be9bc086118fdefa32d2c3bced86`.
Runner: `safeshift.runners.molmo2_o.Molmo2ORunner`, `molmo2-o-runner-v1`.
The B3A runner remains unchanged. There is no backup activation.

The sole technical candidate is **FP32 / NONE / `{"placement":"auto"}`**.
The [pinned README](https://huggingface.co/allenai/Molmo2-O-7B/blob/784410650d12be9bc086118fdefa32d2c3bced86/README.md)
uses automatic dtype; the
[pinned config](https://huggingface.co/allenai/Molmo2-O-7B/blob/784410650d12be9bc086118fdefa32d2c3bced86/config.json)
specifies float32 and B0 weight metadata records F32. FP32 therefore follows the
documentary default without a reduced-precision conversion. No accuracy or
benchmark comparison informed this choice. BF16/FP16 support in B3A is not selected
for this attempt. `precision_frozen=false`; `decoding_frozen=false`.

The seven published shards total **31,043,241,424 bytes**. This is storage evidence,
not a minimum-VRAM estimate: allocator overhead, activations, image crops, generation
cache and automatic placement need observation. The gate is explicitly
**OBSERVATIONAL_MEMORY_GATE**, with no invented minimum memory threshold.

Preflight requires at least one visible CUDA device, CUDA availability, positive
reported memory, FP32 support, and driver information. FP32 is a fundamental CUDA
type; this check does not allocate a test tensor. GPU names are observations only.
Record every visible GPU's VRAM, compute capability, FP32/BF16 support, compiled CUDA
architectures, driver versions and the torch CUDA runtime. The pinned CUDA build
must work with the host driver; the smoke fails if it cannot execute. No additional
unverified compute-capability/driver-number threshold is asserted.

`device_map="auto"` is passed unchanged. The chosen smoke placement contract requires
all parameters on visible CUDA devices and model.device on a visible CUDA device.
CPU/disk/meta placement blocks before generation; observations are retained.
This is a harness gate, not a device-map override or CPU fallback. Automatic placement
may use one GPU or several; no multi-GPU validation or general hardware sufficiency
is claimed. An OOM ends the attempt without retry, cast, sharding adjustment or fallback.

## Source/dependency audit and exact software

Sources were read as text on 2026-09-24. No snapshot custom code was executed.
The [model source](https://huggingface.co/allenai/Molmo2-O-7B/blob/784410650d12be9bc086118fdefa32d2c3bced86/modeling_molmo2.py)
uses torch and Transformers, including GenerationMixin and SDPA-related interfaces.
The [processor](https://huggingface.co/allenai/Molmo2-O-7B/blob/784410650d12be9bc086118fdefa32d2c3bced86/processing_molmo2.py)
imports both image and video processor classes and loads tokenizer/image/video assets
through ProcessorMixin, even though this task sends only a PIL still image.
The [image source](https://huggingface.co/allenai/Molmo2-O-7B/blob/784410650d12be9bc086118fdefa32d2c3bced86/image_processing_molmo2.py)
imports NumPy, einops, torch and torchvision. The
[video source](https://huggingface.co/allenai/Molmo2-O-7B/blob/784410650d12be9bc086118fdefa32d2c3bced86/video_processing_molmo2.py)
also imports requests; optional video decoders are dynamically imported inside video
functions. No molmo_utils import occurs in these custom modules. README video examples
use molmo_utils/decord2, but the still-image path does not invoke them. They are not
installed for this candidate. No flash-attn, torchaudio, moviepy or bitsandbytes is added.

Python **3.11** and Transformers **4.57.1** are documentary targets; the exact Python
patch is recorded at execution. Remaining pins are technical environment choices,
not upstream Molmo package-version recommendations or an already validated environment.

| Package | Exact target | Reason |
|---|---|---|
| torch | 2.8.0+cu128 | Model runtime; CUDA 12.8 build |
| torchvision | 0.23.0+cu128 | Direct image/video imports; matching torch release |
| transformers | 4.57.1 | Pinned README/source API target |
| numpy | 2.2.6 | Direct processing imports |
| pillow | 12.3.0 | Input decoding and geometry generation |
| huggingface_hub | 0.36.0 | Snapshot resolution and offline policy |
| accelerate | 1.10.1 | Official automatic device-map loading |
| einops | 0.8.1 | Direct image/video imports |
| requests | 2.32.5 | Direct video module import; network use remains denied |
| safetensors | 0.6.2 | Checkpoint loading |
| tokenizers | 0.22.1 | Fast tokenizer assets |
| jinja2 | 3.1.6 | Official chat template |

The torch/torchvision pairing and CUDA 12.8 wheel route are listed in
[official PyTorch release instructions](https://pytorch.org/get-started/previous-versions/#v280).
Version existence, Python constraints and declared dependency compatibility were
checked against version-specific PyPI JSON metadata, including
[Transformers](https://pypi.org/pypi/transformers/4.57.1/json),
[torchvision](https://pypi.org/pypi/torchvision/0.23.0/json),
[Accelerate](https://pypi.org/pypi/accelerate/1.10.1/json) and
[Tokenizers](https://pypi.org/pypi/tokenizers/0.22.1/json).
This is a direct/runtime package pin set, not a complete transitive lockfile.
Every installed distribution's name/version is included in the runtime evidence;
no package URLs, credentials or pip configuration are collected.

## Snapshot and provenance verification

`scripts/provision_molmo2_o_snapshot.py` owns online provisioning, then hashes raw
local file bytes without loading torch or the model. `--verify-only` denies/counts
TCP/UDP/DNS calls throughout local resolution and byte verification. Both path and
resolved path must have this exact cache suffix:

```text
models--allenai--Molmo2-O-7B/snapshots/784410650d12be9bc086118fdefa32d2c3bced86
```

`EXPECTED_WEIGHT_FILES` contains all seven exact filenames, byte sizes and LFS
SHA-256 values, cross-checked against unchanged B0 provenance and the
[revision API](https://huggingface.co/api/models/allenai/Molmo2-O-7B/revision/784410650d12be9bc086118fdefa32d2c3bced86?blobs=true)
on 2026-09-24. No weight bytes were fetched during that metadata check.

`CRITICAL_PROVENANCE_FILES` records URL, retrieval date, exact response-byte size
and SHA-256 for 14 pinned assets: README, model config, generation config, processor
config, image/video preprocessor configs, tokenizer config, configuration/model/
processing/image/video Python source, chat_template.jinja and weight index.
Six hashes match existing B0 source records. Eight additional source hashes were
actually computed from the pinned HTTP text responses in PREP and are documented
in the script; B0 itself remains unchanged. These are documentary expectations,
not a claim that the owner's local model bytes are already verified.

On the execution host, a matching critical source or weight file is labelled
`VERIFIED_AGAINST_PROVENANCE`. The remaining five required tokenizer assets
(`tokenizer.json`, `vocab.json`, `merges.txt`, `special_tokens_map.json`,
`added_tokens.json`) have no documentary SHA-256 pin here. Their existence and
local hashes are recorded as `RECORDED_LOCAL_HASH_ONLY`, with `verified=false`.
Missing assets, wrong source hash, wrong shard size/hash or wrong cache identity
block. Verification does not promote unchecked assets or alter documentary records.

## Fixed prompt and cases

Smoke config: `configs/pre_freeze/molmo_gpu_smoke.v1.json`, exact LF UTF-8 SHA-256:
`05c3be0334a15c3b592a5fd0dbf4d9deaedfc055ecadbbee45df65c2b16b425c`.

The generic classification prompt is byte-identical to the Qwen/Ovis smoke prompt.
SHA-256: `681fb3f051871bd9dd52a8100816f864ceb82ea0b5ac332bb2c7a22aed6bda48`.
It requests one safety_level JSON value, without point/box instructions or model hints.
Technical decoding is `do_sample=false`, `max_new_tokens=32`, no temperature and no
seed. This makes token selection greedy; it does not promise bitwise determinism
across hardware. Native checkpoint defaults remain recorded by the runner.

Exactly two 224×192 RGB geometry images are generated in memory, with the same
rectangle/ellipse and triangle/rectangle pixel design as previous smoke cases.
`runtime-smoke-geometry-v2-stored-png` explicitly encodes PNG filter-0 rows and
DEFLATE stored blocks to avoid compression-library byte drift. No PNG is saved.
These byte pins are new and are not substituted into historical Qwen/Ovis evidence.

| Case | PNG SHA-256 |
|---|---|
| RUNTIME_SMOKE_01 | `3a0b33888342ac3008b8fefe76b4f2c9cbc4908d2200e5f592e1cd948da8184e` |
| RUNTIME_SMOKE_02 | `44e1e4bc6391cab8b9187a46d18cf293ae5507832bba6503a2a22aa1e9a36c05` |

These handcrafted inputs have no ground-truth safety labels. No industrial images,
SYNTHETIC V1, InspecSafe or grounding calls participate. Output equality on distinct
inputs is only `RUNTIME_OBSERVATION`, with no semantic interpretation.

## Later owner execution: online preparation

The commands below are instructions for a later authorized execution, not commands
run during PREP. Use a fresh Python 3.11 environment on a CUDA-capable host. Run
from repository root. Obtain the reviewed B3B_PREP_HEAD from the Draft PR, check
out that exact commit, and keep tracked files clean. Do not use mutable branch HEAD
as the execution pin. Preserve config LF bytes (a CRLF conversion fails its hash).

```bash
python -m pip install torch==2.8.0+cu128 torchvision==0.23.0+cu128 --index-url https://download.pytorch.org/whl/cu128
python -m pip install transformers==4.57.1 numpy==2.2.6 pillow==12.3.0 huggingface_hub==0.36.0 accelerate==1.10.1 einops==0.8.1 requests==2.32.5 safetensors==0.6.2 tokenizers==0.22.1 jinja2==3.1.6
python -m pip check
python scripts/provision_molmo2_o_snapshot.py --report-dir data/processed/runtime_validation/molmo-provision-01
```

The provisioner accepts no alternate repo/revision or download filter. Use the
same HF cache environment in all phases. Optional `--cache-dir` must be a
repository-relative directory under data/processed; set the corresponding HF cache
environment for the later runner as well. Keep report/cache directories disjoint.
The default cache avoids needing this optional configuration. Reports must use
new paths; neither failed nor successful evidence is overwritten.

## Offline transition and exactly one smoke

Start a fresh process with all three variables set before any HF imports:

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1
export B3B_PREP_HEAD='<exact reviewed 40-character lowercase SHA-1 from the Draft PR>'
python scripts/provision_molmo2_o_snapshot.py --verify-only --report-dir data/processed/runtime_validation/molmo-verify-01
python scripts/w2_molmo_gpu_smoke.py --run-id molmo-runtime-01
```

Use the equivalent environment-setting syntax in other shells. The harness requires
the supplied execution pin to equal `git rev-parse HEAD`, rejects tracked worktree
changes and verifies config bytes against both the embedded SHA-256 and Git blob.
Missing/malformed/mismatched pin blocks before software/GPU preflight, snapshot
resolution or runner construction. The report separates `git_commit`,
`execution_pin`, and `execution_identity_verified`.

The smoke process rehashes the exact local snapshot and all required shards/sources.
It verifies software pins and observes hardware under a counting firewall denying
`socket.socket.connect`, `connect_ex`, `sendto`, `socket.create_connection` and
`socket.getaddrinfo`. Any attempt blocks, even if a backend catches the exception.
The native runner additionally enforces HF offline flags and local-only loaders.
The socket firewall covers these Python entry points; it is not an OS sandbox for
arbitrary native extensions. No unaudited custom source is allowed into this run.

One runner instance initializes once and performs one load lifecycle. The harness
then permits exactly two sequential native generate calls with independent requests.
A third native call is refused before invoking the model. No prompt/history is
carried between requests. Each raw envelope is hashed and written, then metadata
is written, before the unchanged adapter runs. SUCCESS and INVALID with
INVALID_CLASSIFICATION_OUTPUT are permitted runtime outcomes; parser failure,
generation failure, native exception and preservation failure all block.

After load, record model.device, hf_device_map (or null), per-device parameter
counts/numel/bytes, CPU/meta counts, per-GPU counts, buffers and detectable disk
offload. Every floating parameter dtype is counted with numel/bytes. Any value
other than torch.float32 blocks; no silent cast occurs. Memory snapshots cover
before_load, after_load, after_call_1 and after_call_2, for every visible GPU,
including free/total, allocated/reserved and both peaks. Failed attempts retain
whatever stages were reached; no unavailable measurement is fabricated.

Stop after that one attempt. Do not automatically rerun, change precision, adjust
placement, activate a backup or tune the prompt. A later reviewed rerun needs a
new run ID and explicit `--rerun-of` plus `--rerun-reason`; the original artifacts
remain untouched. The script requires that linkage once a prior report exists.

## Evidence and Research Lead review

Artifacts are local under
`data/processed/runtime_validation/w2_molmo_gpu_smoke/<run-id>/`.
The CLI creates `molmo_gpu_smoke_evidence.zip` and
`molmo_gpu_smoke_evidence.zip.sha256`. A passing bundle must contain exactly:

```text
runtime_report.json
environment.json
snapshot_verification.json
weight_verification.json
critical_file_verification.json
case_manifest.json
calls/RUNTIME_SMOKE_01/metadata.json
calls/RUNTIME_SMOKE_01/response.raw
calls/RUNTIME_SMOKE_02/metadata.json
calls/RUNTIME_SMOKE_02/response.raw
```

Early-failure bundles contain only available allowlisted evidence. No weights,
HF cache, source snapshot, PNGs, tokens or arbitrary logs are included. Bundle
creation checks raw/metadata hashes, path containment, duplicate entries and
member-size limits; failure to create a bundle makes the CLI fail.

Download/copy only the ZIP and sidecar through the owner's normal file-transfer
route. Verify SHA-256 again after transfer (`sha256sum -c
molmo_gpu_smoke_evidence.zip.sha256` on systems providing sha256sum, or compare
PowerShell Get-FileHash with the sidecar). Give both files and the execution pin
to the Research Lead. Their audit must check exact commit/config/snapshot/software,
placement/dtype/memory, network count, one load/two calls, and both raw/metadata
pairs. PREP alone never records a real runtime PASS.

`RUNTIME_SMOKE_PASS` is limited to the recorded checkpoint/runner/bytes/condition/
software/hardware path completing this interface test. All claims remain false:
capability_pass, grounding_pass, accuracy_pass, benchmark_pass, precision_frozen,
decoding_frozen, thinking_frozen, protocol_frozen. There is no performance or
long-run stability claim. Molmo grounding remains DOCUMENTED_NATIVE_POINT /
NOT_YET_QUALIFIED, box/IoU NOT_PARTICIPATING: no point parsing qualification,
point-to-box, IoU, Pointing Hit or canonical grounding success.

## PREP validation and status

Use the existing local `.venv` for offline tests; no new dependencies are needed:

```text
python -m unittest tests.test_molmo_gpu_smoke_harness -v
python -m unittest tests.test_molmo_runner -v
python -m unittest discover -s tests
python -m py_compile scripts/provision_molmo2_o_snapshot.py scripts/w2_molmo_gpu_smoke.py tests/test_molmo_gpu_smoke_harness.py
git diff --check
```

Validation on 2026-09-24: **59/59 harness tests**, **51/51 Molmo runner tests**,
**610/610 full-suite tests PASS**. Python compilation and `git diff --check` PASS.
Tests ran in the existing `.venv`, Python 3.11.9 / Pillow 12.3.0 on Windows;
no packages were installed, no random sampling was used, and no seed is applicable.
Tests use fake ML/GPU objects and tiny temporary files, with real network and ML imports denied. No
model download, real inference, GPU, SYNTHETIC gate or InspecSafe inference is run.

Checklist #1 COMPLETE documentary; #2 PENDING overall. Qwen/Ovis offline COMPLETE
and previously audited runtime PASS / VALIDATED. Molmo offline COMPLETE, runtime
PREPARED / NOT_RUN. Gemma and checklist #3–#8 remain PENDING.
`protocol_freeze_commit_sha: PENDING`.
Census remains untracked and untouched, SHA-256
`cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`.
