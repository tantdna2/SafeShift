# D9R26 P2 moondream owner runbook — freeze candidate only

Current state: PROTOCOL_FREEZE_REQUIRED; InspecSafe NOT_RUN and unauthorized.
These are future owner instructions, not commands executed in D9R26.
First run metadata-only preflight; stop while authority is absent:

```sh
python -m safeshift.runners.p2_owner preflight
```

Exit 2 is expected for this candidate. No dataset, model or GPU is inspected.
Never change the guard locally to enable a run. Independent audit, merged release,
final post-merge freeze/authorization PR and Research Lead authority are still required.

## Exact source and condition

Model: `vikhyatk/moondream2`; immutable revision: `9a7d4024050840e001defacec2b00727e89149e6`.
Native source: `safeshift.runners.moondream2.Moondream2Runner` (`moondream2-offline-v1`).
Orchestrator: `d9r26-production-runner-bridge-v1`;
registry: `d9r26-native-runner-registry-v1`.
Historical validated condition sources: `configs/pre_freeze/moondream_t4_runtime.v1.json`, `safeshift/qualification/runtime.py#condition`, `configs/pre_freeze/d9r17b_e_classification_qualification_results.v1.json#/runs/moondream`, `notes/w2_moondream_runner_prep.md (native API table, query reasoning=False/stream=False)`.
D9R26 does not rerun that runtime evidence or claim new runtime qualification.

Authority is `configs/pre_freeze/production_classification_policy.d9r23.v1.json#/classification/moondream`.
Hardware: Linux x86_64, NVIDIA T4 CC 7.5, **1 visible GPU(s)**,
CUDA runtime 12.4; placement `cuda:0`.
FP16, quantization NONE; no CPU/disk offload, automatic fallback or precision change.
Python exactly 3.11.11; torch 2.6.0+cu124;
transformers 4.52.4. Every software pin below is measured
before loading; mismatch fails, including Python.

Do not assume Kaggle/Colab host Python matches. Provision the pinned interpreter
separately. The repository's managed-Python pattern is documented in
`notebooks/w2_paligemma_d9r9_kaggle.ipynb`; using that environment tooling does
not make PaliGemma a P2 participant. This new provisioning recipe has not been
executed by Codex. It does not depend on a venv having pip:

```sh
uv --no-config venv --managed-python --python 3.11.11 .venv-p2-moondream
uv pip install --python .venv-p2-moondream/bin/python \
  --extra-index-url https://download.pytorch.org/whl/cu124 \
  torch==2.6.0+cu124 \
  transformers==4.52.4 \
  tokenizers==0.21.2 \
  numpy==1.26.4 \
  pillow==11.2.1 \
  huggingface-hub==0.30.2 \
  safetensors==0.5.3 \
  filelock==3.18.0 \
  fsspec==2025.3.2 \
  jinja2==3.1.6 \
  markupsafe==3.0.2 \
  mpmath==1.3.0 \
  networkx==3.4.2 \
  sympy==1.13.1 \
  typing-extensions==4.13.2 \
  packaging==25.0 \
  pyyaml==6.0.2 \
  regex==2024.11.6 \
  requests==2.32.3 \
  charset-normalizer==3.4.2 \
  idna==3.10 \
  urllib3==1.26.20 \
  certifi==2025.4.26 \
  tqdm==4.67.1 \
  nvidia-cuda-nvrtc-cu12==12.4.127 \
  nvidia-cuda-runtime-cu12==12.4.127 \
  nvidia-cuda-cupti-cu12==12.4.127 \
  nvidia-cudnn-cu12==9.1.0.70 \
  nvidia-cublas-cu12==12.4.5.8 \
  nvidia-cufft-cu12==11.2.1.3 \
  nvidia-curand-cu12==10.3.5.147 \
  nvidia-cusolver-cu12==11.6.1.9 \
  nvidia-cusparse-cu12==12.3.1.170 \
  nvidia-cusparselt-cu12==0.6.2 \
  nvidia-nccl-cu12==2.21.5 \
  nvidia-nvtx-cu12==12.4.127 \
  nvidia-nvjitlink-cu12==12.4.127 \
  triton==3.2.0
```

Use `.venv-p2-moondream/bin/python` for EVERY following `python` command,
including snapshot provisioning, verify-only and the production child.
Do not install the CPU-only Moondream test requirements as a production runtime.
Apply CUDA_VISIBLE_DEVICES=0 before starting the child interpreter on a T4x2 host; the child must observe exactly one T4. A notebook cell changing visibility after torch import is insufficient.

Preprocessing (exact): `{"resize_backend":"PILLOW_ONLY","bridge_version":"moondream-post-normalization-fp16-v1"}`.
Decoding (exact): `{"query":{"temperature":0,"top_p":1,"max_tokens":32,"variant":null}}`.
Batch size 1; output cap 32; seed null means no seed sent; no sampling/repair/retry.
Native API query only, stream=False, pinned native default reasoning=False, spatial_refs=None. Reuse the existing post-normalization FP16/Pillow vision bridge. Tokenizer moondream/starmie-v1 revision 35192e10a54e36eabe0a7cc57a2c1aab371cafc5.
C1 prompt `p2-classification-c1-v1`, SHA-256
`816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3`.
Adapter `moondream-classification-adapter-d9r23-v1`; parser `d9r23-native-strict-classification-v1`;
durable harness adapter `d9r25-durable-d9r23-native-adapter-v1`.
No domain, split, point_id, GT, hazards or other predictions enter prompt/image.
Operational RunContext is separate and never interpolated into C1.

## Future snapshot provisioning and offline transition

Only after owner permission for provisioning, use the existing pinned source
verifier; it must not run inference. Use a fresh manifest filename:
```sh
python -m scripts.provision_moondream_snapshot --provision --cache-dir data/processed/moondream_hf_cache --manifest data/processed/p2-provision/moondream-new.json
```
The fixed repository-relative cache is `data/processed/moondream_hf_cache`. Do not change its meaning or copy snapshots into Git.
Do not use mutable revisions or download a replacement on verification failure.
Then disable networking at the host, export offline flags, and verify local bytes:
```sh
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_ENABLE_HF_TRANSFER=0 HF_HUB_DISABLE_XET=1
python -m scripts.provision_moondream_snapshot --verify-only --cache-dir data/processed/moondream_hf_cache --manifest data/processed/p2-provision/moondream-verified-new.json
```
Runtime also uses the existing Python network guard; this is not an OS sandbox.
Never commit snapshot files, credentials, local dataset manifests or run artifacts.

## Future authorized production command placeholder

Run from the reviewed source checkout using its pinned interpreter.
These relative placeholders MUST be replaced by explicit owner-authorized inputs.
No force/unsafe flag exists. This candidate still rejects the command before reading data:

```sh
CUDA_VISIBLE_DEVICES=0 .venv-p2-moondream/bin/python -m safeshift.runners.p2_owner run \
  --model moondream --run-id OWNER_UNIQUE_RUN_ID \
  --dataset-root OWNER_DATASET_ROOT --manifest-path OWNER_MANIFEST.csv \
  --provenance-path OWNER_PROVENANCE.json --shard-count 1 --shard-index 0
```

P2 is exactly 5013 image samples; fingerprint
`7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`;
source manifest SHA `3025edb985d947cbcfe3e397b37aed505e2305b32ece46663d46115c28568577`.
Authorization precedes dataset access; dataset identity/count/schema/image validation
precedes backend resolution/load. Shards sort sample IDs then index modulo count.
Never choose shards using labels, hazards or previous results.

Artifacts: `data/processed/benchmark/p2/moondream/OWNER_UNIQUE_RUN_ID/`.
Native bytes are atomically published, hashed, sized, reread and verified before
any semantic parser. Calls are immutable, with sample-derived call IDs.
A raw-write failure prevents parsing. Generation failure preserves partial bytes
if present, stops the shard and leaves remaining samples NOT_ATTEMPTED.
INVALID stays null, never Level04. No semantic retries, output repair, alternate
prompt, seed, precision or model. Do not resume an existing run ID.
A rerun requires a new ID, exact prior manifest hash and explicit Research Lead
authorization; the package API accepts that relation, this minimal CLI does not
manufacture it. A failed run cannot be exported as completed.

After all shards complete, use `p2_evaluation.export_predictions` and
`align_four_models`; only then `join_evaluation` introduces GT and memberships.
D9R24 consumes those in-memory records. Hazard counts overlap; P1 is separate.
See `w2_d9r26_freeze_candidate.md` for readiness, hashes and the synthetic command.
