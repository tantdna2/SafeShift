# D9R26 P2 qwen2_5 owner runbook — freeze candidate only

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

Model: `Qwen/Qwen2.5-VL-3B-Instruct`; immutable revision: `66285546d2b821cf421d4f5eb2576359d3770cd3`.
Native source: `safeshift.runners.qwen2_5_vl.Qwen2_5VLRunner` (`qwen2-5-vl-runner-v2`).
Orchestrator: `d9r26-production-runner-bridge-v1`;
registry: `d9r26-native-runner-registry-v1`.
Historical validated condition sources: `configs/pre_freeze/qwen2_5_t4_runtime.v1.json`, `safeshift/qualification/runtime.py#condition`, `configs/pre_freeze/qwen2_5_classification_qualification_result.v1.json`.
D9R26 does not rerun that runtime evidence or claim new runtime qualification.

Authority is `configs/pre_freeze/production_classification_policy.d9r23.v1.json#/classification/qwen2_5`.
Hardware: Linux x86_64, NVIDIA T4 CC 7.5, **1 visible GPU(s)**,
CUDA runtime 12.4; placement `cuda:0`.
FP16, quantization NONE; no CPU/disk offload, automatic fallback or precision change.
Python exactly 3.11.11; torch 2.6.0+cu124;
transformers 4.51.3. Every software pin below is measured
before loading; mismatch fails, including Python.

Do not assume Kaggle/Colab host Python matches. Provision the pinned interpreter
separately. The repository's managed-Python pattern is documented in
`notebooks/w2_paligemma_d9r9_kaggle.ipynb`; using that environment tooling does
not make PaliGemma a P2 participant. This new provisioning recipe has not been
executed by Codex. It does not depend on a venv having pip:

```sh
uv --no-config venv --managed-python --python 3.11.11 .venv-p2-qwen2_5
uv pip install --python .venv-p2-qwen2_5/bin/python \
  --extra-index-url https://download.pytorch.org/whl/cu124 \
  torch==2.6.0+cu124 \
  torchvision==0.21.0+cu124 \
  transformers==4.51.3 \
  qwen-vl-utils==0.0.8 \
  accelerate==1.6.0 \
  pillow==11.2.1 \
  huggingface-hub==0.30.2 \
  tokenizers==0.21.1 \
  safetensors==0.5.3
```

Use `.venv-p2-qwen2_5/bin/python` for EVERY following `python` command,
including snapshot provisioning, verify-only and the production child.
Do not install the CPU-only Moondream test requirements as a production runtime.
Apply CUDA_VISIBLE_DEVICES=0 before starting the child interpreter on a T4x2 host; the child must observe exactly one T4. A notebook cell changing visibility after torch import is insufficient.

Preprocessing (exact): `{"mode":"official_processor_capped","min_pixels":200704,"max_pixels":1003520}`.
Decoding (exact): `{"do_sample":false,"max_new_tokens":32}`.
Batch size 1; output cap 32; seed null means no seed sent; no sampling/repair/retry.

C1 prompt `p2-classification-c1-v1`, SHA-256
`816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3`.
Adapter `qwen2_5-classification-adapter-d9r23-v1`; parser `d9r23-native-strict-classification-v1`;
durable harness adapter `d9r25-durable-d9r23-native-adapter-v1`.
No domain, split, point_id, GT, hazards or other predictions enter prompt/image.
Operational RunContext is separate and never interpolated into C1.

## Future snapshot provisioning and offline transition

Only after owner permission for provisioning, use the existing pinned source
verifier; it must not run inference. Use a fresh manifest filename:
```sh
python -m scripts.provision_qwen2_5_snapshot --provision --manifest data/processed/p2-provision/qwen2_5-new.json
```
Qwen uses the default HF cache. If selecting a custom cache for provisioning, set HF_HUB_CACHE to that same absolute owner-controlled cache BEFORE both provision and runtime child processes. Native loaders and offline verifier must resolve the same snapshot.
Do not use mutable revisions or download a replacement on verification failure.
Then disable networking at the host, export offline flags, and verify local bytes:
```sh
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_ENABLE_HF_TRANSFER=0 HF_HUB_DISABLE_XET=1
python -m scripts.provision_qwen2_5_snapshot --verify-only --manifest data/processed/p2-provision/qwen2_5-verified-new.json
```
Runtime also uses the existing Python network guard; this is not an OS sandbox.
Never commit snapshot files, credentials, local dataset manifests or run artifacts.

## Future authorized production command placeholder

Run from the reviewed source checkout using its pinned interpreter.
These relative placeholders MUST be replaced by explicit owner-authorized inputs.
No force/unsafe flag exists. This candidate still rejects the command before reading data:

```sh
CUDA_VISIBLE_DEVICES=0 .venv-p2-qwen2_5/bin/python -m safeshift.runners.p2_owner run \
  --model qwen2_5 --run-id OWNER_UNIQUE_RUN_ID \
  --dataset-root OWNER_DATASET_ROOT --manifest-path OWNER_MANIFEST.csv \
  --provenance-path OWNER_PROVENANCE.json --shard-count 1 --shard-index 0
```

P2 is exactly 5013 image samples; fingerprint
`7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`;
source manifest SHA `3025edb985d947cbcfe3e397b37aed505e2305b32ece46663d46115c28568577`.
Authorization precedes dataset access; dataset identity/count/schema/image validation
precedes backend resolution/load. Shards sort sample IDs then index modulo count.
Never choose shards using labels, hazards or previous results.

Artifacts: `data/processed/benchmark/p2/qwen2_5/OWNER_UNIQUE_RUN_ID/`.
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
