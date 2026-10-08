# P2 Qwen3 owner runbook - superseding execution authority v2

PR #85 merged the runtime fix at
`92ef9179f23ca7c58ffb425512d239b12b26f832`. The runtime amendment is historical
and unchanged; `configs/frozen/p2_execution_authority.v2.json` separately
supersedes execution authority ONLY for the four Qwen3 runs below.
The old v1 authority, D9R25 contract and D9R26 candidate remain immutable.

These are future owner instructions. Do not execute from a Draft PR. F1 contains
all executable/config/test/document changes and the frozen execution plan;
F2 is its sole authority-file child. Activation requires independent audit,
Research Lead / ChatGPT review, Standard Merge Commit into main and final
post-merge Git verification. The first merge parent must be the exact PR #85
base above, the second must be F2, and the merge tree must equal F2's tree.
Any code, config, test or document drift after F1 requires a new reviewed freeze.
Squash, rebase, intermediate commits and tracked local changes fail closed.
Local Git structure checks do not attest that governance reviews occurred.

After those external gates, first run metadata-only preflight:

```sh
.venv-p2-qwen3/bin/python -m safeshift.runners.p2_owner preflight
```

Exit 2 / `FINAL_MERGE_REQUIRED` is expected on the Draft branch. Valid final
preflight lists only Qwen3 and its exact four-run plan; it reads no dataset and
loads no model/GPU. Never edit guards locally to enable execution.

## Exact source and condition

Model: `Qwen/Qwen3-VL-8B-Instruct`; immutable revision: `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`.
Native source: `safeshift.runners.qwen3_vl.Qwen3VLRunner` (`qwen3-vl-runner-v2`).
Orchestrator: `d9r26-production-runner-bridge-v1`;
registry: `d9r26-native-runner-registry-v1`.
Historical validated condition sources: `configs/pre_freeze/qwen_kaggle_smoke.v1.json`, `safeshift/qualification/runtime.py#condition`, `configs/pre_freeze/qwen_kaggle_smoke_result.v1.json`.
D9R26 does not rerun that runtime evidence or claim new runtime qualification.

The immutable semantic/software contract remains
`configs/pre_freeze/production_classification_policy.d9r23.v1.json#/classification/qwen3`.
Prospective runtime changes are versioned separately in
`configs/pre_freeze/qwen3_runtime_placement_amendment.v1.json`, runtime ID
`qwen3-t4x2-embedding-cpu-v1`. P2 registry/bridge/preflight explicitly load this
amended runtime view; historical policy readers retain the original view.
Hardware: Linux x86_64, NVIDIA T4 CC 7.5, **2 visible GPU(s)**,
CUDA runtime 12.8. Exact explicit placement:

- CPU: `model.language_model.embed_tokens` only.
- GPU0: `model.language_model.layers.0` through `.20`.
- GPU1: `model.visual`, `model.language_model.layers.21` through `.35`,
  `model.language_model.norm`, `model.language_model.rotary_emb`, `lm_head`.

FP16, quantization NONE; `disk_offload=false`, `automatic_fallback=false`.
The runner passes this exact map to `from_pretrained`; the runner and bridge
reject any different `hf_device_map`, including an additional CPU module or
a single language layer on the wrong GPU. Default SDPA remains required; no
attention override is sent to the loader.

Allocator: `PYTORCH_ALLOC_CONF=expandable_segments:True` before torch import or
CUDA allocator initialization. The Qwen3 owner CLI sets a missing value at
startup before entering the production harness. It rejects a conflicting value
and refuses to set a missing value if torch is already imported. Direct Python
API/native-runner callers must set it before starting their process; runtime
preflight checks it before importing torch or probing CUDA. A conflicting legacy
`PYTORCH_CUDA_ALLOC_CONF` alias is rejected.

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
A managed interpreter with the wrong zlib must be rejected; do not relax the pin.
Keep both T4s visible and the exact explicit map above.

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

## Restore the prior failed shard0 artifact

Before shard0, restore the owner's unmodified failed bundle into:
`data/processed/benchmark/p2/qwen3/qwen3-p2-shard0-first/`.
Use the trusted owner backup/export, preserving its original bytes and layout.
At minimum its `run_manifest.json` must exist at that exact relative location.
Do not regenerate or reserialize the manifest. No old predictions are consumed;
the old manifest verifies lineage only. New shard0 executes all 1254 samples,
including the two previous SUCCESS samples, under the same amended runtime as
shards1-3. Keep the historical failed bundle; do not overwrite its run ID.

Verify raw bytes before execution (the harness repeats this check):

```sh
.venv-p2-qwen3/bin/python - <<'PY'
from hashlib import sha256
from pathlib import Path
p = Path('data/processed/benchmark/p2/qwen3/qwen3-p2-shard0-first/run_manifest.json')
expected = 'd4dd6ee9790dcc3c99c73e9404b52f71268fc7285ead41797dcf828261cd1500'
assert sha256(p.read_bytes()).hexdigest() == expected, 'STOP: prior manifest mismatch'
print('PRIOR_MANIFEST_VERIFIED')
PY
```

## Exact authorized production commands after merge verification

On the owner's Kaggle runtime select **T4 x2** and **Internet OFF**. Use the
reviewed clean final merge checkout and the pinned production interpreter.
Restore already provisioned exact model bytes before disabling Internet; do not
use production commands for provisioning. Set the following environment before
any torch import or CUDA probe. The three input variables must name the owner's
verified original dataset, W1 CSV and provenance JSON; use repo-relative paths.

```sh
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_ENABLE_HF_TRANSFER=0 HF_HUB_DISABLE_XET=1
export CUDA_VISIBLE_DEVICES=0,1
export PYTORCH_ALLOC_CONF=expandable_segments:True
unset PYTORCH_CUDA_ALLOC_CONF
export P2_DATASET_ROOT=OWNER_DATASET_ROOT
export P2_MANIFEST_PATH=OWNER_MANIFEST.csv
export P2_PROVENANCE_PATH=OWNER_PROVENANCE.json

.venv-p2-qwen3/bin/python -m safeshift.runners.p2_owner run \
  --model qwen3 --run-id qwen3-p2-shard0-rerun1 --shard-count 4 --shard-index 0 \
  --dataset-root "$P2_DATASET_ROOT" --manifest-path "$P2_MANIFEST_PATH" \
  --provenance-path "$P2_PROVENANCE_PATH"

.venv-p2-qwen3/bin/python -m safeshift.runners.p2_owner run \
  --model qwen3 --run-id qwen3-p2-shard1-first --shard-count 4 --shard-index 1 \
  --dataset-root "$P2_DATASET_ROOT" --manifest-path "$P2_MANIFEST_PATH" \
  --provenance-path "$P2_PROVENANCE_PATH"

.venv-p2-qwen3/bin/python -m safeshift.runners.p2_owner run \
  --model qwen3 --run-id qwen3-p2-shard2-first --shard-count 4 --shard-index 2 \
  --dataset-root "$P2_DATASET_ROOT" --manifest-path "$P2_MANIFEST_PATH" \
  --provenance-path "$P2_PROVENANCE_PATH"

.venv-p2-qwen3/bin/python -m safeshift.runners.p2_owner run \
  --model qwen3 --run-id qwen3-p2-shard3-first --shard-count 4 --shard-index 3 \
  --dataset-root "$P2_DATASET_ROOT" --manifest-path "$P2_MANIFEST_PATH" \
  --provenance-path "$P2_PROVENANCE_PATH"
```

Shard0 is the sole authorized rerun. Shards1-3 are first attempts (1253 samples
each). The harness derives shard0's exact `rerun_of` from the committed plan;
there is no operator-selectable rerun CLI flag. Wrong IDs, indices, counts or
references fail before dataset access. Missing/mutated prior manifest fails
before dataset access. Existing run directories cannot resume; hidden reruns
still fail the existing attempt checks. Failure of any new run requires a new
Research Lead decision; v2 grants no further reruns.

**Do not run Qwen2.5 again.** Its existing completed result remains outside this
plan. This authority grants no Qwen2.5, InternVL3 or Moondream execution/rerun
permission and changes none of their runtime contracts.

P2 is exactly 5013 image samples; fingerprint
`7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`;
source manifest SHA `3025edb985d947cbcfe3e397b37aed505e2305b32ece46663d46115c28568577`.
Authorization precedes dataset access; dataset identity/count/schema/image validation
precedes backend resolution/load. Shards sort sample IDs then index modulo count.
Never choose shards using labels, hazards or previous results.

Artifacts: `data/processed/benchmark/p2/qwen3/<exact-authorized-run-id>/`.
Native bytes are atomically published, hashed, sized, reread and verified before
any semantic parser. Calls are immutable, with sample-derived call IDs.
A raw-write failure prevents parsing. Generation failure preserves partial bytes
if present, stops the shard and leaves remaining samples NOT_ATTEMPTED.
INVALID stays null, never Level04. No semantic retries, output repair, alternate
prompt, seed, precision or model. Do not resume an existing run ID.
A rerun requires a new ID, exact prior manifest hash and explicit Research Lead
authorization. Authority v1 keeps `reruns=[]` byte-for-byte. Authority v2 binds exactly
shard0 rerun1 to the failed manifest above and becomes effective only after the
reviewed final merge. A failed run cannot be exported as completed.

After all shards complete, use `p2_evaluation.export_predictions` and
`align_four_models`; only then `join_evaluation` introduces GT and memberships.
D9R24 consumes those in-memory records. Hazard counts overlap; P1 is separate.
See `w2_d9r26_freeze_candidate.md` for readiness, hashes and the synthetic command.

## Owner diagnostic evidence (2026-10-08)

Source: Research Lead task statement accompanying this amendment; owner-reported
Kaggle T4 x2 results, not independently rerun by Codex. Old production exhausted
CUDA memory. Pure GPU placement with visual + embedding on GPU1 and language
split 22/14 OOMed on GPU0 at 4581 input tokens; split 21/15 OOMed on GPU1.
The exact embedding-only CPU placement above with expandable segments generated
successfully for the 4581-token sample and the 4149-token control.
These are generation/resource checks, not semantic benchmark scores or evidence
of completing all 5013 samples. Raw diagnostic artifacts/notebooks were not
provided in this task and are not committed.

Semantic protocol, C1 prompt, official processor (no image resize or input-token
reduction), greedy decoding, FP16/NONE, model/revision, software pins, dataset
fingerprint/count and metric contract remain unchanged. Historical smoke and
qualification conditions remain historical; the new P2 runtime uses the explicit
map and permits CPU placement only for the embedding.

## Amendment validation in Codex

Offline Python 3.11.9 checks use fake runtime state and synthetic inputs; this
test interpreter does not replace the pinned production Python 3.12.13.
Nested Git commands use `core.autocrlf=false` to match this LF checkout.

- Placement/native Qwen3/D9R22-26 contracts, harness, bridge and candidate:
  182 tests PASS, including 19 new placement/allocator tests.
- Qwen2.5, InternVL3, Moondream and historical Qwen3 native/smoke/gate checks:
  275 test identities PASS. The frozen Qwen3 gate fixture/result checks now read
  the historical runner blob; the 13 result tests and 2 scope checks were
  revalidated after this adjustment. No gate plan/hash was repinned.
- D9R27 authority: 12 tests PASS using real temporary Git histories, including
  original valid merge acceptance and changed/wrong/dirty tree rejection.
- `git diff --check` and staged diff checks PASS; all frozen identity artifacts
  are unchanged. No dataset/weights/raw outputs/notebook are staged.

Full discovery and real GPU generation were not run for this scoped amendment.
The 4581/4149 diagnostic results above remain owner-reported evidence.

## Superseding authority evidence and validation

Source: Research Lead task statement for this authority (original failed bundle
not read in Codex). Exact failed run: `qwen3-p2-shard0-first`; production commit
`031958a5ce668057f763973a722a3506d73f39f0`; raw run_manifest SHA-256
`d4dd6ee9790dcc3c99c73e9404b52f71268fc7285ead41797dcf828261cd1500`.
Shard count/index/count: 4/0/1254. Owner-reported result: STATUS=FAILED,
FAILURE_STAGE=GENERATION, FAILURE_CAUSE=GENERATION_FAILURE, SUCCESS=2,
FAILED=1, NOT_ATTEMPTED=1251. CUDA OOM was confirmed by diagnostics outside the
artifact. These observations are supplied evidence, not independently rerun.

Static authority tests use local temporary Git histories, synthetic artifacts,
SHA checks, exact four-run binding and guarded fresh-process preflight. Success
of raw prior-manifest hashing is exercised with synthetic bytes; the exact old
production manifest bytes were not supplied. Exact production rerun identity,
missing file and wrong local bytes are checked independently. No real dataset,
model, GPU or network is accessed by authority/static tests. Git/GitHub network
access is limited to publishing the requested Draft PR.

Run the scoped suite before F1 and again on final F2; the actual-release
structure assertion activates only after F2 exists. Validation totals and final
F1/F2 SHAs belong in the Draft PR handoff, because editing this document after
F1 would invalidate the freeze. Full discovery and real execution are outside
this scoped authority task.
