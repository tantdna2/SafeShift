# InternVL3 P2 authority v3 owner runbook

Draft authority is NOT EFFECTIVE. Codex performs only offline static/synthetic
checks; no dataset/model/GPU, provisioning, production or Antigravity execution.
No production notebook is introduced here.

## Release verification before owner runtime work

BASE: `e46e98ed0c53f6c189f4069cc5f2f5d7d4295e5e`.
F1 is its direct child and freezes code, plan, tests and this runbook. F2 is F1's
sole-parent child and adds only `configs/frozen/p2_execution_authority.v3.json`.
The Draft PR handoff records exact F1/F2 hashes; they cannot be embedded here
because this document itself is part of F1. The new authority pins F1/tree and
canonical F2 commit encoding pins the exact parent2 without a self-reference.

After independent audit and Research Lead / ChatGPT review, require a Standard
Merge Commit with parent1=exact BASE, parent2=exact reviewed F2, tree=exact F2 tree.
Record that final production commit SHA from GitHub after merge, fetch and check
out that exact SHA on Kaggle T4. A clean tracked checkout and all protected
hashes are required. Static preflight fails closed for missing/mutated authority,
Draft, squash, rebase, intermediate commit, wrong parents or tree drift.

```sh
.venv-p2-internvl3/bin/python -m safeshift.runners.p2_owner preflight
```

This command is metadata-only: no dataset/snapshot/model/GPU/network operation.
Draft returns exit 2 and effective_authorization=false. After final verification,
require exit 0, effective_authorization=true and models=["internvl3"]. This local
Git proof does not attest that external reviews were completed.

Authority v1/v2 and Qwen3 plan/runtime amendment remain historical, byte-for-byte.
v3 supersedes v2 by exact path/SHA-256. Qwen3 is paused following the owner-reported
new production failure; v3 grants no Qwen3 production/rerun. No new failure
artifact is claimed/read here. Qwen2.5 completed production is not rerun;
Moondream is not yet authorized. v3 authorizes only these first attempts:

| run_id | shard index/count | samples | rerun_of |
| --- | --- | --- | --- |
| internvl3-p2-shard0-first | 0/4 | 1254 | null |
| internvl3-p2-shard1-first | 1/4 | 1253 | null |
| internvl3-p2-shard2-first | 2/4 | 1253 | null |
| internvl3-p2-shard3-first | 3/4 | 1253 | null |

Hash-pinned qualification evidence reports one Tesla T4, CUDA 12.4, FP16/NONE,
snapshot bytes verified, runtime_failure=null, model_loads=1,
classification_calls=8, parse success=8/8, semantic expected exact=6/8.
These are descriptive prior results, not a new run or a production accuracy
claim. Semantic 6/8 is no reason to tune model, prompt or protocol. Production
must measure the frozen model. Runtime/source evidence is pinned in v3's
preserved_sha256 alongside the unchanged D9R22/23/24/25/26 and C1 contracts.

## Exact source and condition

Model: `OpenGVLab/InternVL3-2B-hf`; immutable revision: `cb57a075cb75a2e6d1b668b128d48bb00ae321d2`.
Native source: `safeshift.runners.internvl3.InternVL3Runner` (`internvl3-runner-v1`).
Orchestrator: `d9r26-production-runner-bridge-v1`;
registry: `d9r26-native-runner-registry-v1`.
Historical validated condition sources: `configs/pre_freeze/internvl3_t4_runtime.v1.json`, `safeshift/qualification/runtime.py#condition`, `configs/pre_freeze/d9r17b_e_classification_qualification_results.v1.json#/runs/internvl3`.
D9R26 does not rerun that runtime evidence or claim new runtime qualification.

Execution condition: `configs/pre_freeze/production_classification_policy.d9r23.v1.json#/classification/internvl3`. Effective authority requires `configs/frozen/p2_execution_authority.v3.json` and the exact final merge gate.
Hardware: Linux x86_64, NVIDIA T4 CC 7.5, **1 visible GPU(s)**,
CUDA runtime 12.4; placement `cuda:0`.
FP16, quantization NONE; no CPU/disk offload, automatic fallback or precision change.
Attention is SDPA. No quantization fallback or model substitution is permitted.
Python exactly 3.11.11; torch 2.6.0+cu124;
transformers 4.52.4. Every software pin below is measured
before loading; mismatch fails, including Python.

Do not assume Kaggle/Colab host Python matches. Provision the pinned interpreter
separately. The repository's managed-Python pattern is documented in
`notebooks/w2_paligemma_d9r9_kaggle.ipynb`; using that environment tooling does
not make PaliGemma a P2 participant. This new provisioning recipe has not been
executed by Codex. It does not depend on a venv having pip:

```sh
uv --no-config venv --managed-python --python 3.11.11 .venv-p2-internvl3
uv pip install --python .venv-p2-internvl3/bin/python \
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
  triton==3.2.0 \
  torchvision==0.21.0+cu124
```

Use `.venv-p2-internvl3/bin/python` for EVERY following `python` command,
including snapshot provisioning, verify-only and the production child.
Do not install the CPU-only Moondream test requirements as a production runtime.
Apply CUDA_VISIBLE_DEVICES=0 before starting the child interpreter on a T4x2 host; the child must observe exactly one T4. A notebook cell changing visibility after torch import is insufficient.

Preprocessing (exact): `{"mode":"official_dynamic_tiles","size":{"height":448,"width":448},"crop_to_patches":true,"min_patches":1,"max_patches":12,"image_seq_length":256,"max_input_tokens":4096}`.
Decoding (exact): `{"do_sample":false,"max_new_tokens":32,"num_beams":1,"num_return_sequences":1,"use_cache":true,"cache_implementation":"dynamic","return_dict_in_generate":false,"output_scores":false,"output_logits":false,"output_attentions":false,"output_hidden_states":false}`.
Batch size 1; output cap 32; seed null means no seed sent; no sampling/repair/retry.

C1 prompt `p2-classification-c1-v1`, SHA-256
`816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3`.
Adapter `internvl3-classification-adapter-d9r23-v1`; parser `d9r23-native-strict-classification-v1`;
durable harness adapter `d9r25-durable-d9r23-native-adapter-v1`.
No domain, split, point_id, GT, hazards or other predictions enter prompt/image.
Operational RunContext is separate and never interpolated into C1.

## Future snapshot provisioning and offline transition

After final merge verification, the owner on Kaggle T4 uses the existing pinned source
verifier; it must not run inference. Use a fresh manifest filename:
```sh
python -m scripts.provision_internvl3_snapshot --provision --manifest data/processed/p2-provision/internvl3-new.json
```
The fixed repository-relative cache is `data/processed/internvl3_hf_cache`. Do not change its meaning or copy snapshots into Git.
Do not use mutable revisions or download a replacement on verification failure.
Then disable networking at the host, export offline flags, and verify local bytes:
```sh
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_ENABLE_HF_TRANSFER=0 HF_HUB_DISABLE_XET=1
python -m scripts.provision_internvl3_snapshot --verify-only --manifest data/processed/p2-provision/internvl3-verified-new.json
```
Runtime also uses the existing Python network guard; this is not an OS sandbox.
Never commit snapshot files, credentials, local dataset manifests or run artifacts.

## Owner four-shard execution after final merge verification

The owner supplies repository-relative dataset/manifest/provenance paths below.
Use the exact final production merge commit, never Draft F2, F1, a rebased,
squashed or later commit. With Internet OFF, run metadata preflight from that
clean checkout with the pinned interpreter; require effective_authorization=true,
models=["internvl3"] and exactly the four runs listed below.

```sh
CUDA_VISIBLE_DEVICES=0 .venv-p2-internvl3/bin/python -m safeshift.runners.p2_owner run \
  --model internvl3 --run-id internvl3-p2-shard0-first \
  --dataset-root OWNER_DATASET_ROOT --manifest-path OWNER_MANIFEST.csv \
  --provenance-path OWNER_PROVENANCE.json --shard-count 4 --shard-index 0
```

```sh
CUDA_VISIBLE_DEVICES=0 .venv-p2-internvl3/bin/python -m safeshift.runners.p2_owner run \
  --model internvl3 --run-id internvl3-p2-shard1-first \
  --dataset-root OWNER_DATASET_ROOT --manifest-path OWNER_MANIFEST.csv \
  --provenance-path OWNER_PROVENANCE.json --shard-count 4 --shard-index 1
```

```sh
CUDA_VISIBLE_DEVICES=0 .venv-p2-internvl3/bin/python -m safeshift.runners.p2_owner run \
  --model internvl3 --run-id internvl3-p2-shard2-first \
  --dataset-root OWNER_DATASET_ROOT --manifest-path OWNER_MANIFEST.csv \
  --provenance-path OWNER_PROVENANCE.json --shard-count 4 --shard-index 2
```

```sh
CUDA_VISIBLE_DEVICES=0 .venv-p2-internvl3/bin/python -m safeshift.runners.p2_owner run \
  --model internvl3 --run-id internvl3-p2-shard3-first \
  --dataset-root OWNER_DATASET_ROOT --manifest-path OWNER_MANIFEST.csv \
  --provenance-path OWNER_PROVENANCE.json --shard-count 4 --shard-index 3
```

P2 is exactly 5013 image samples; fingerprint
`7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`;
source manifest SHA `3025edb985d947cbcfe3e397b37aed505e2305b32ece46663d46115c28568577`.
Authorization precedes dataset access; dataset identity/count/schema/image validation
precedes backend resolution/load. Shards sort sample IDs then index modulo count.
Never choose shards using labels, hazards or previous results.

Artifacts: `data/processed/benchmark/p2/internvl3/internvl3-p2-shard{0,1,2,3}-first/`.
Native bytes are atomically published, hashed, sized, reread and verified before
any semantic parser. Calls are immutable, with sample-derived call IDs.
A raw-write failure prevents parsing. Generation failure preserves partial bytes
if present, stops the shard and leaves remaining samples NOT_ATTEMPTED.
INVALID stays null, never Level04. No semantic retries, output repair, alternate
prompt, seed, precision or model. Do not resume an existing run ID.
All four runs are FIRST ATTEMPT, rerun_of=null; reruns=[]. On any failure,
stop and preserve the complete failed run artifacts. Do not reuse any ID, resume,
rename a run to conceal a repeat, rerun qualification or grant a new retry.
A separate future Research Lead decision is required for any new attempt.

After all shards complete, use `p2_evaluation.export_predictions` and
`align_four_models`; only then `join_evaluation` introduces GT and memberships.
D9R24 consumes those in-memory records. Hazard counts overlap; P1 is separate.
The historical D9R26 candidate/runbook remains unchanged; v3 supplies the execution authority without rewriting that history.
