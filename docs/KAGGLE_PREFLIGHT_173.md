# Issue173 bounded Kaggle verification

Authority: [Issue173](https://github.com/tantdna2/SafeShift/issues/173).
Base `50d0c910319a6e93354a3d27887418aeb320709f`;
branch `feat/issue173-kaggle-preflight`. Date: 02/11/2026, Asia/Bangkok.

Kaggle authentication was verified through the official CLI in the repository's
existing virtual environment. The system PATH Python lacks Kaggle; that is not
a connector outage. Read-only quota reports 6202.527/108000 GPU seconds used,
zero reserved. Twelve recent relevant notebooks inspected were COMPLETE;
this is a bounded observation, not proof of account-wide absence of running jobs.

Initial task will submit a private, no-Input environment notebook, with no model
loader or inference route. It records Python/platform, installed package versions,
driver/GPU memory, a small CUDA FP16 tensor probe, RAM/cgroup and simultaneous
scratch/output allocation/fsync/cleanup. Each execution exports unique receipts
and ZIP/SHA256. Kernel probes are observations, not pinned-worker qualification.
No credentials, dataset inventory, GT, checkpoint or private raw is exported.

Public Qwen software preparation must preserve CPython3.12.13/zlib1.2.11,
torch2.10.0+cu128/torchvision0.25.0+cu128 and the remaining source pins in
`configs/fulltrain/qwen3.json`. A failed source/hash/dependency check blocks the
processor check; alternate versions are not an acceptable repair.

Fresh TRAIN rights/cloud-purpose and independently sealed projection/mapping
are NOT VERIFIED by the existing tracked dossier. Historical Input access or
past160 execution is not a new custody seal. Therefore the initial notebook
attaches zero datasets/checkpoints. Model-specific checkpoint admission and
smoke stay BLOCKED until those prerequisites are established. The three-call
ceiling is unused. Production authorization remains unchanged.

Final measurements, commands, tests and continuation conditions will be appended
in this same branch/PR. No READY FOR OWNER or scientific PASS claim.

## Verified live observation

The first private no-Input notebook completed on Kaggle, version 1. Its source
is `dd152630877c29faf9f4439d902e55720e823378`; the
[sanitized receipt](research/evidence/issue173/environment-observation-v1.json)
binds submitted notebook bytes, source bytes, output ZIP and internal checksums.
CRC, member hashes, outer SHA256 and embedded source binding were rechecked locally.

Observed kernel: CPython3.13.15, Linux x86_64/glibc2.39, torch2.11.0+cu128,
torchvision0.26.0+cu128, transformers5.16.1, numpy2.1.3, Pillow13.0.0.
These are **not** the locked model stacks. Both Tesla T4 devices were visible,
driver580.178.04, capability7.5; a 2x2 FP16 matrix multiplication succeeded on
each. This is kernel-only evidence, not a worker/model-load/inference PASS.
Cgroup memory limit 30 GiB; output free space about 19.5 GiB, scratch on a different
device. Two simultaneous 1 MiB writes were physically allocated, fsynced and
removed. This small probe does not prove full-campaign storage quota/capacity.
Observation took 10.82 seconds; job startup/export GPU quota is additional.

No checkpoint was attached, read, hashed or loaded. No model calls, production
reservation, attempt or fresh171 history were created. Dataset rights/fresh
manifest custody remain unverified, and all three smoke images are NOT_ATTEMPTED.

## Public software preflight and reproducibility

`scripts/qualify_kaggle173_software.py` is a separate diagnostic entrypoint with
no call to production launch, authorization, native factory, generate or data
admission. It uses the existing source verifier, peer runtime provisioning,
CPU native processor/meta checks, MiniCPM numerical installation and Linux
process-group supervisor. All original `safeshift/` and model/config lock bytes remain
unchanged. Explicit setup/CPU/GPU stages retain failed logs and sealed evidence;
only a successful CPU stage permits that model's pinned-worker tensor probe.
The whole job is capped 3600 seconds, with a 3300 second internal deadline.
Qwen setup has at most 1800 seconds; each peer setup 600 seconds; each CPU/GPU
stage 180 seconds subject to the global deadline. These are diagnostic resource
bounds, not scientific O5/full TRAIN grants.

Qwen sources were acquired from the exact Python/zlib URLs and both SHA256s
matched the existing config. A Windows cross-target pip dry-run was also tried:
it is **not a Linux dependency closure**, because platform environment markers
can still use the host. Its original receipt/log are retained locally; the
diagnostic now labels this limitation explicitly. The live software notebook
builds the actual CPython3.12.13/zlib1.2.11 interpreter. Version 1 resolved on that
Linux interpreter; version 2 uses the exact 48 URLs/versions/hashes sealed in
`configs/issue173/qwen_linux_cp312_wheels.json`, without re-resolution. It records
every wheel URL/name/version/size/SHA, validates the existing
`provision.software_input` contract, installs with `--no-index --no-deps`, runs
`pip check`, verifies the complete installed distribution set, native ABI and
the pinned Transformers source files before invoking the real processor.
No change to top-level pins is permitted. Resolution of previously unsealed
transitive dependencies is recorded as a new candidate lock, not scientific
approval or an automatic production activation.

Software/checkpoints are distinct: only hash-locked public processor/tokenizer/
model source metadata is downloaded, never any `.safetensors` shard. Qwen uses
one synthetic 448x448 image; peers use the existing eight synthetic shapes with
empty/meta weights. This is processor and code-path validation, not inference.
Version 2 exports the actual Qwen offline software Input as a separate ZIP/SHA256,
outside the small evidence ZIP. It contains public wheels and source archives
only. It remains outside Git and is not automatically attached to production.

Build notebooks from an exact committed source (never `HEAD`/branch names):

```console
python -B -m scripts.build_kaggle173_notebook --source-commit <40hex> --output notebooks/SafeShift_ISSUE173_ENVIRONMENT.ipynb
python -B -m scripts.build_kaggle173_notebook --software --source-commit <40hex> --output notebooks/SafeShift_ISSUE173_SOFTWARE.ipynb
python -B -m unittest discover -s tests -p test_kaggle173.py -v
python -B -m scripts.check_fresh_fulltrain_cpu --pattern "test_fresh_fulltrain*.py" --output data/processed/issue173/new-cpu-run
```

The builder requires byte-for-byte equality with Git objects, includes no output
cells, and writes stable UTF-8 bytes across Windows/Linux. The public notebook
payload hash covers the new diagnostic scripts and all required runtime source;
`source-manifest.json` in the output describes the reused runtime package.
The initial builder referenced a nonexistent `scripts/__init__.py`; local
integration caught this before any software notebook was submitted. The scripts
directory is a namespace package; the builder and regression were corrected.

For Kaggle CLI staging, copy only the generated notebook plus
`kernel-metadata.json` into a fresh ignored directory. Require `is_private=true`,
empty dataset/kernel/model/competition source lists and T4x2. Internet OFF for
environment-only observation; ON for public software acquisition. Submit with
`kaggle kernels push -p <staging> --accelerator NvidiaTeslaT4 -t 600` for the
environment, or `-t 3600` for software. Check status and retain each version's
Outputs using `kaggle kernels output <ref/version> -p <new-output>`.
Never overwrite earlier output directories or treat notebook COMPLETE as PASS:
read every model's `result.json`, CPU/GPU receipts, failure logs and ZIP seal.

## First software result and controlled correction

[Version 1 summary](research/evidence/issue173/software-preflight-v1.json): both
peers passed their exact CPython3.11.9/cu124 software checks, native processor/
empty-meta loader on eight synthetic image shapes and a CUDA tensor check in
the isolated worker. MiniCPM installed the existing FP32 resampler implementation;
strict C1 and label-only policy were not changed. Transformers' warning about
uninitialized model weights is expected in this empty/meta-only test; no model
predictions or training are performed.

Qwen source build completed and the
[native resolver receipt](research/evidence/issue173/qwen-linux-resolver-v1.json)
records CPython3.12.13/Linux/x86_64 and 48 packages. Setup then failed with
`PUBLIC_WHEEL_HOST`: the initial downloader allowed only `download.pytorch.org`
and PyPI, while the official [PyTorch torch index](https://download.pytorch.org/whl/cu128/torch/)
links to `download-r2.pytorch.org`, and its
[CUDA package index](https://download.pytorch.org/whl/cu128/nvidia-cublas-cu12/)
links to `pypi.nvidia.com`. The correction admits those exact official hosts
with package/path restrictions, preserves every artifact hash/version, rejects
spoofed hosts/credentials/non-HTTPS paths, and exports the sealed offline bundle.
No fallback package, source/hash relaxation, prompt/parser change or inference
retry is involved. Version 1 FAIL and every Output remain intact.
