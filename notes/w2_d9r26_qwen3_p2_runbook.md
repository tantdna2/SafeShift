# D9R26 P2 qwen3 owner runbook — freeze candidate only

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

Model: `Qwen/Qwen3-VL-8B-Instruct`; immutable revision: `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`.
Native source: `safeshift.runners.qwen3_vl.Qwen3VLRunner` (`qwen3-vl-runner-v2`).
Orchestrator: `d9r26-production-runner-bridge-v1`;
registry: `d9r26-native-runner-registry-v1`.
Historical validated condition sources: `configs/pre_freeze/qwen_kaggle_smoke.v1.json`, `safeshift/qualification/runtime.py#condition`, `configs/pre_freeze/qwen_kaggle_smoke_result.v1.json`.
D9R26 does not rerun that runtime evidence or claim new runtime qualification.

Authority is `configs/pre_freeze/production_classification_policy.d9r23.v1.json#/classification/qwen3`.
Hardware: Linux x86_64, NVIDIA T4 CC 7.5, **2 visible GPU(s)**,
CUDA runtime 12.8; placement `auto`.
FP16, quantization NONE; no CPU/disk offload, automatic fallback or precision change.
Python exactly 3.12.13; torch 2.10.0+cu128;
transformers 4.57.1. Every software pin below is measured
before loading; mismatch fails, including Python and zlib 1.2.11.

Do not assume Kaggle/Colab host Python matches. Provision the pinned interpreter
separately. The repository's managed-Python pattern is documented in
`notebooks/w2_paligemma_d9r9_kaggle.ipynb`; using that environment tooling does
not make PaliGemma a P2 participant. This new provisioning recipe has not been
executed by Codex. It does not depend on a venv having pip:

```sh
uv --no-config venv --managed-python --python 3.12.13 .venv-p2-qwen3
uv pip install --python .venv-p2-qwen3/bin/python \
  --extra-index-url https://download.pytorch.org/whl/cu128 \
  torch==2.10.0+cu128 \
  transformers==4.57.1 \
  accelerate==1.11.0 \
  huggingface_hub==0.36.0 \
  safetensors==0.6.2 \
  pillow==11.3.0
```

Use `.venv-p2-qwen3/bin/python` for EVERY following `python` command,
including snapshot provisioning, verify-only and the production child.
Do not install the CPU-only Moondream test requirements as a production runtime.
A managed interpreter with the wrong zlib must be rejected; do not relax the pin. Keep both T4s visible and native auto placement; do not change to a single GPU.

Preprocessing (exact): `{"mode":"official_processor"}`.
Decoding (exact): `{"do_sample":false,"max_new_tokens":32}`.
Batch size 1; output cap 32; seed null means no seed sent; no sampling/repair/retry.

C1 prompt `p2-classification-c1-v1`, SHA-256
`816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3`.
Adapter `qwen3-classification-adapter-d9r23-v1`; parser `d9r23-native-strict-classification-v1`;
durable harness adapter `d9r25-durable-d9r23-native-adapter-v1`.
No domain, split, point_id, GT, hazards or other predictions enter prompt/image.
Operational RunContext is separate and never interpolated into C1.

## Future snapshot provisioning and offline transition

Only after owner permission for provisioning, use the existing pinned source
verifier; it must not run inference. Use a fresh manifest filename:
```sh
python -m scripts.provision_qwen3vl_snapshot --report data/processed/p2-provision/qwen3-new.json
```
Qwen uses the default HF cache. If selecting a custom cache for provisioning, set HF_HUB_CACHE to that same absolute owner-controlled cache BEFORE both provision and runtime child processes. Native loaders and offline verifier must resolve the same snapshot.
Do not use mutable revisions or download a replacement on verification failure.
Then disable networking at the host, export offline flags, and verify local bytes:
```sh
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_ENABLE_HF_TRANSFER=0 HF_HUB_DISABLE_XET=1
python -m scripts.provision_qwen3vl_snapshot --verify-only --report data/processed/p2-provision/qwen3-verified-new.json
```
Runtime also uses the existing Python network guard; this is not an OS sandbox.
Never commit snapshot files, credentials, local dataset manifests or run artifacts.

## Future authorized production command placeholder

Run from the reviewed source checkout using its pinned interpreter.
These relative placeholders MUST be replaced by explicit owner-authorized inputs.
No force/unsafe flag exists. This candidate still rejects the command before reading data:

```sh
CUDA_VISIBLE_DEVICES=0,1 .venv-p2-qwen3/bin/python -m safeshift.runners.p2_owner run \
  --model qwen3 --run-id OWNER_UNIQUE_RUN_ID \
  --dataset-root OWNER_DATASET_ROOT --manifest-path OWNER_MANIFEST.csv \
  --provenance-path OWNER_PROVENANCE.json --shard-count 1 --shard-index 0
```

P2 is exactly 5013 image samples; fingerprint
`7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`;
source manifest SHA `3025edb985d947cbcfe3e397b37aed505e2305b32ece46663d46115c28568577`.
Authorization precedes dataset access; dataset identity/count/schema/image validation
precedes backend resolution/load. Shards sort sample IDs then index modulo count.
Never choose shards using labels, hazards or previous results.

Artifacts: `data/processed/benchmark/p2/qwen3/OWNER_UNIQUE_RUN_ID/`.
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
