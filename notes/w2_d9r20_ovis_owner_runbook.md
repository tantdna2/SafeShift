# Owner run 1 — Ovis2.5-2B (NOT RUN)

Read [shared workflow](w2_d9r20_owner_workflow.md) first. Exact checkpoint
`ATH-MaaS/Ovis2.5-2B@393c932b2a03e28eb9aaa503e3c4ab3ad384d958`.
Apache-2.0, no HF access gate observed. This is an FP16 resource feasibility
experiment, not a T4-compatible claim. Historical 9B/A40/BF16 evidence does not apply.

On a future Linux Kaggle/Colab single-T4 venue, after separate authorization:

```sh
python3.11 -m venv .cache/d9r20_envs/ovis
.cache/d9r20_envs/ovis/bin/python -m pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cu121
.cache/d9r20_envs/ovis/bin/python -m pip install -r requirements-d9r20-ovis.txt
.cache/d9r20_envs/ovis/bin/hf download ATH-MaaS/Ovis2.5-2B --revision 393c932b2a03e28eb9aaa503e3c4ab3ad384d958 --include '*.safetensors' '*.json' '*.txt' '*.py' --local-dir .cache/d9r20_snapshots/ovis/393c932b2a03e28eb9aaa503e3c4ab3ad384d958
```

Do **not** install flash-attn: this predeclares the existing native vision SDPA
branch; observation refuses a flash-attn installation. The official recipe uses
BF16 and flash-attn; this explicitly documented deviation is unvalidated. Do not
change dtype or attention path after a failure. Source max_pixels is 1344*1792,
min_pixels 448*448; thinking/budget false, greedy 512 tokens, seed 0.

Turn venue Internet off; verify committed v4 fixtures using the shared
workflow. Observe without loading:

```sh
.cache/d9r20_envs/ovis/bin/python scripts/verify_grounding_multicategory_v4.py
.cache/d9r20_envs/ovis/bin/python scripts/run_d9r20_candidate.py observe --model ovis --observation data/processed/d9r20/ovis-observation.json
```

After Research Lead audits this observation and issues the exact post-merge
authorization, run once and bundle:

```sh
.cache/d9r20_envs/ovis/bin/python scripts/run_d9r20_candidate.py run --model ovis --observation data/processed/d9r20/ovis-observation.json --authorization data/processed/d9r20/ovis-authorization.json
.cache/d9r20_envs/ovis/bin/python scripts/run_d9r20_candidate.py bundle --model ovis
```

Run ID `d9r20-ovis-fp16-001`; load/FP16/kernel/OOM failures are resource NO-GO.
Box/ref output is parsed strictly, preserving multiple boxes. Caption/prose
outside the declared subset is an interface failure, with raw retained.
`CALL2_ORCHESTRATION_BLOCKER` remains regardless of single-target observations.
